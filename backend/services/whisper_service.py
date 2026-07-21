"""
whisper_service.py
==================
Central AI service layer for Transcribe-Pro.

Responsibilities:
  - Model lifecycle management (load / release / flush)
  - WhisperX batched transcription adapter
  - faster-whisper sequential adapter (low-VRAM fallback)
  - Per-language alignment model cache
  - Speaker diarization via Pyannote
  - Sentence-level segment splitting (NLTK)
  - Subtitle export: ASS and SRT with OpenAI-style line wrapping
"""

from __future__ import annotations

import os
import gc
import re
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, cast


def _preload_nvidia_libraries() -> None:
    """
    torch pulls in NVIDIA's CUDA/cuDNN shared libraries as pip packages
    (nvidia-cudnn-cu12, nvidia-cublas-cu12, etc.), but other libraries that
    also need them at runtime — like ctranslate2, which WhisperX's GPU
    decode path uses — don't know where to find them, and fail with errors
    like "Could not load library libcudnn_ops_infer.so.8" even though the
    .so file is sitting right there on disk.

    NOTE: setting os.environ["LD_LIBRARY_PATH"] does NOT fix this once the
    process has already started — ld.so reads that variable once, at
    process launch, not on every dlopen() call afterward. The actual fix is
    to directly preload each .so file with ctypes.CDLL(..., RTLD_GLOBAL),
    the same technique torch itself uses internally for its own CUDA deps.
    Once a library is loaded globally this way, any other library's later
    dlopen() request for that same filename resolves to the already-loaded
    copy instead of needing to search a path at all.
    """
    import ctypes
    import importlib.util

    candidate_packages = [
        "nvidia.cudnn.lib",
        "nvidia.cublas.lib",
        "nvidia.cuda_runtime.lib",
        "nvidia.cufft.lib",
        "nvidia.curand.lib",
        "nvidia.cusparse.lib",
        "nvidia.cusolver.lib",
        "nvidia.nvjitlink.lib",
    ]
    lib_dirs: list[str] = []
    for pkg in candidate_packages:
        try:
            spec = importlib.util.find_spec(pkg)
        except (ImportError, ModuleNotFoundError, ValueError):
            continue
        if spec and spec.submodule_search_locations:
            lib_dirs.extend(spec.submodule_search_locations)

    if not lib_dirs:
        print("⚠️ No bundled NVIDIA library directories found (nvidia-cudnn-cu12 etc. not installed).")
        return

    so_files: list[str] = []
    for d in lib_dirs:
        try:
            so_files.extend(str(p) for p in Path(d).glob("*.so*"))
        except OSError:
            continue

    # Load order matters — dependency libraries (cudart, cublas) generally
    # need to be resident before things that link against them (cudnn).
    # Two passes: try everything once, then retry failures once more in
    # case ordering fixed itself after the first pass loaded a dependency.
    failed: list[str] = []
    loaded_count = 0
    for so_path in so_files:
        try:
            ctypes.CDLL(so_path, mode=ctypes.RTLD_GLOBAL)
            loaded_count += 1
        except OSError:
            failed.append(so_path)

    for so_path in failed[:]:
        try:
            ctypes.CDLL(so_path, mode=ctypes.RTLD_GLOBAL)
            loaded_count += 1
            failed.remove(so_path)
        except OSError:
            pass

    print(f"✅ Preloaded {loaded_count}/{len(so_files)} NVIDIA shared libraries.")
    if failed:
        print(f"⚠️ Could not preload (may be harmless if unused): {[Path(f).name for f in failed]}")


try:
    _preload_nvidia_libraries()
except Exception as exc:
    print(f"⚠️ NVIDIA library preload failed (non-fatal): {exc}")

import torch
import whisperx

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# PyTorch 2.6 compatibility shim
# ---------------------------------------------------------------------------
# PyTorch 2.6 flipped torch.load's default from weights_only=False to True,
# which now refuses to unpickle config objects (e.g. omegaconf.ListConfig)
# that official pyannote/WhisperX checkpoints legitimately contain — raising
# "Weights only load failed ... Unsupported global: GLOBAL omegaconf...".
#
# We restore the pre-2.6 default (weights_only=False) specifically for the
# torch.load calls WhisperX/pyannote make internally when loading their own
# models. This is safe here because those checkpoints come from the official,
# trusted pyannote/WhisperX Hugging Face repos configured via settings — not
# from arbitrary/user-supplied files. Do not apply this pattern to files of
# unknown provenance.
_torch_load_original = torch.load


def _torch_load_default_unsafe(*args: Any, **kwargs: Any) -> Any:
    # Force, not just default — if a caller explicitly passes
    # weights_only=True (some pytorch_lightning versions do exactly this,
    # following PyTorch's own new recommended default), a plain
    # kwargs.setdefault(...) has no effect since the key is already present.
    kwargs["weights_only"] = False
    return _torch_load_original(*args, **kwargs)


torch.load = _torch_load_default_unsafe  # type: ignore[assignment]

# Belt-and-suspenders: the monkeypatch above only works if a library calls
# `torch.load(...)` via attribute lookup at call time. If a library instead
# does `from torch import load` (binding the original function directly),
# reassigning torch.load afterwards has no effect on that already-bound
# reference — this has been observed to vary between pytorch_lightning
# versions. Allowlisting the specific classes these checkpoints use is a
# second, independent layer that torch's unpickler consults regardless of
# how torch.load was invoked or imported.
try:
    import collections
    import typing

    import omegaconf

    _safe_globals = []
    for _mod_name, _cls_names in [
        ("omegaconf.listconfig", ["ListConfig"]),
        ("omegaconf.dictconfig", ["DictConfig"]),
        ("omegaconf.base", ["ContainerMetadata", "Metadata", "SCMode"]),
        ("omegaconf.nodes", ["AnyNode", "ValueNode", "StringNode", "IntegerNode", "BooleanNode", "FloatNode"]),
    ]:
        try:
            _mod = __import__(_mod_name, fromlist=_cls_names)
            for _cls_name in _cls_names:
                if hasattr(_mod, _cls_name):
                    _safe_globals.append(getattr(_mod, _cls_name))
        except ImportError:
            continue

    # Generic typing/collections objects these checkpoints have also been
    # observed to reference (added incrementally as new "Unsupported global"
    # errors surfaced during testing — torch.load's unpickler reports one
    # missing class at a time, so this list may need further additions if
    # a different checkpoint/library-version combination hits another one).
    _safe_globals.extend([
        typing.Any,
        collections.OrderedDict,
        collections.defaultdict,
    ])

    if _safe_globals and hasattr(torch.serialization, "add_safe_globals"):
        torch.serialization.add_safe_globals(_safe_globals)
        print(f"✅ Allowlisted {len(_safe_globals)} classes for torch.load.")
except Exception as exc:
    print(f"⚠️ Could not allowlist safe classes (non-fatal): {exc}")

# ---------------------------------------------------------------------------
# Module-level singleton state
# ---------------------------------------------------------------------------
_model: Any = None          # Raw whisperx / faster-whisper model instance
_aligner: Any = None        # WhisperXAligner singleton
_diarizer: Any = None       # WhisperXDiarizer singleton
_align_model_cache: Dict[str, Tuple[Any, Any]] = {}  # lang -> (align_model, metadata)

DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE: str = "float16" if DEVICE == "cuda" else "int8"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_language(language: Optional[str]) -> Optional[str]:
    """Normalise 'automatic' / 'auto' / None to None (auto-detect)."""
    if not language or language.lower() in {"automatic", "auto"}:
        return None
    return language.strip().lower()


def _load_alignment_model(language_code: Optional[str]) -> Tuple[Any, Any]:
    """
    Lazy-load and cache the WhisperX alignment model for *language_code*.

    The language code must be the *detected* language from transcription
    (not the user-supplied hint) so the correct wav2vec model is selected.
    Falls back to settings.DEFAULT_LANGUAGE then 'en'.
    """
    resolved = language_code or settings.DEFAULT_LANGUAGE or "en"
    resolved = resolved.strip().lower()

    if resolved not in _align_model_cache:
        try:
            align_model, metadata = whisperx.load_align_model(
                language_code=resolved,
                device=DEVICE,
            )
            _align_model_cache[resolved] = (align_model, metadata)
            print(f"✅ Loaded alignment model for language: '{resolved}'")
        except Exception as exc:
            print(f"⚠️ Alignment model could not be loaded for '{resolved}': {exc}")
            return None, None

    return _align_model_cache[resolved]


# ---------------------------------------------------------------------------
# Subtitle helpers (OpenAI utils.py style)
# ---------------------------------------------------------------------------

def _format_ass_timestamp(seconds: float) -> str:
    """Convert a float seconds value to ASS timestamp H:MM:SS.cc format."""
    total_cs = int(round(seconds * 100))      # centiseconds
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _format_srt_timestamp(seconds: float) -> str:
    """Convert a float seconds value to SRT timestamp HH:MM:SS,mmm format."""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap_subtitle_text(
    text: str,
    max_chars: Optional[int] = None,
    max_lines: Optional[int] = None,
) -> str:
    """
    Wrap *text* to subtitle display limits (OpenAI whisper utils.py style).

    Words are never broken mid-word. Lines are joined with \\N (ASS soft-newline).
    If the wrapped result exceeds *max_lines*, excess lines are appended to the last.

    Args:
        text:       Raw segment text.
        max_chars:  Maximum characters per line (defaults to settings.MAX_LINE_CHARS).
        max_lines:  Maximum lines per event (defaults to settings.MAX_LINES_PER_SEGMENT).

    Returns:
        Wrapped string with \\N as line separator.
    """
    max_chars = max_chars or settings.MAX_LINE_CHARS
    max_lines = max_lines or settings.MAX_LINES_PER_SEGMENT

    text = text.strip()
    if not text:
        return text

    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    current_len = 0

    for word in words:
        word_len = len(word)
        # +1 for the space between words
        if current_len + (1 if current else 0) + word_len > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
            current_len = word_len
        else:
            if current:
                current_len += 1 + word_len
            else:
                current_len = word_len
            current.append(word)

    if current:
        lines.append(" ".join(current))

    # Enforce max_lines: merge overflow into last permitted line
    if len(lines) > max_lines:
        tail = " ".join(lines[max_lines - 1:])
        lines = lines[: max_lines - 1] + [tail]

    return r"\N".join(lines)


# ---------------------------------------------------------------------------
# ASS subtitle export
# ---------------------------------------------------------------------------

def write_ass_subtitles(
    segments: List[Dict[str, Any]],
    output_path: str | Path,
    max_chars: Optional[int] = None,
    max_lines: Optional[int] = None,
) -> Path:
    """
    Export subtitle segments to an Advanced SubStation Alpha (.ass) file.

    Timestamps follow the H:MM:SS.cc format required by the ASS spec.
    Text is word-wrapped using :func:`wrap_subtitle_text`.

    Args:
        segments:    List of dicts with 'start', 'end', 'text', and optionally 'speaker'.
        output_path: Destination .ass file path.
        max_chars:   Max chars per line (default from settings).
        max_lines:   Max lines per event (default from settings).

    Returns:
        Resolved :class:`pathlib.Path` to the written file.
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "[Script Info]",
        "Title: Transcript",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: None",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    events: List[str] = []
    for seg in segments:
        start = _format_ass_timestamp(float(seg.get("start", 0.0)))
        end = _format_ass_timestamp(float(seg.get("end", 0.0)))
        speaker = str(seg.get("speaker", ""))
        raw_text = str(seg.get("text", "")).strip()
        wrapped = wrap_subtitle_text(raw_text, max_chars=max_chars, max_lines=max_lines)
        events.append(f"Dialogue: 0,{start},{end},Default,{speaker},0,0,0,,{wrapped}")

    target.write_text("\n".join(header + events) + "\n", encoding="utf-8")
    print(f"📄 ASS subtitle written: {target}")
    return target


# ---------------------------------------------------------------------------
# SRT subtitle export
# ---------------------------------------------------------------------------

def write_srt_subtitles(
    segments: List[Dict[str, Any]],
    output_path: str | Path,
    max_chars: Optional[int] = None,
    max_lines: Optional[int] = None,
) -> Path:
    """
    Export subtitle segments to a SubRip (.srt) file.

    Args:
        segments:    List of dicts with 'start', 'end', 'text'.
        output_path: Destination .srt file path.
        max_chars:   Max chars per line (default from settings).
        max_lines:   Max lines per event (default from settings).

    Returns:
        Resolved :class:`pathlib.Path` to the written file.
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    blocks: List[str] = []
    for idx, seg in enumerate(segments, start=1):
        start = _format_srt_timestamp(float(seg.get("start", 0.0)))
        end = _format_srt_timestamp(float(seg.get("end", 0.0)))
        raw_text = str(seg.get("text", "")).strip()
        # SRT uses real newlines, not \N
        wrapped = wrap_subtitle_text(raw_text, max_chars=max_chars, max_lines=max_lines)
        wrapped_newlines = wrapped.replace(r"\N", "\n")
        blocks.append(f"{idx}\n{start} --> {end}\n{wrapped_newlines}")

    target.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"📄 SRT subtitle written: {target}")
    return target


# ---------------------------------------------------------------------------
# Transcription adapters
# ---------------------------------------------------------------------------

class WhisperXAdapter:
    """
    Batched WhisperX transcription adapter.

    Uses WhisperX's CTranslate2-accelerated faster-whisper backend with
    automatic alignment immediately after transcription.
    """

    def __init__(self, model: Any):
        self._model = model

    def transcribe(
        self,
        audio_path: str | Path,
        language: Optional[str] = None,
        beam_size: Optional[int] = None,
        batch_size: int = 16,
        vad_filter: bool = False,
        vad_method: Optional[str] = None,
    ):
        """
        Transcribe *audio_path* and return ``(segments, info)`` compatible with
        the existing pipeline callers.

        Language auto-detection: when *language* is None, WhisperX detects the
        language and the detected code is used to load the correct alignment model.
        """
        audio = whisperx.load_audio(str(audio_path))

        options: Dict[str, Any] = {"batch_size": batch_size}
        if language:
            options["language"] = language
        if beam_size is not None:
            options["beam_size"] = beam_size

        # NOTE: whisperx==3.3.1's FasterWhisperPipeline.transcribe() does NOT
        # accept vad_filter / vad_method — VAD is configured once at
        # load_model() time (see get_whisperx_model) and always runs
        # internally. Passing those kwargs here raises TypeError. If you
        # upgrade whisperx to a version with a different transcribe() API,
        # revisit this.
        result = self._transcribe_safely(audio, options)

        # Use the *detected* language (not user hint) so the aligner is correct
        detected_language = result.get("language") or language or settings.DEFAULT_LANGUAGE or "en"
        aligned_segments = self._align_segments(audio, result.get("segments", []), detected_language)

        segments = [
            SimpleNamespace(
                start=float(seg.get("start", 0.0)),
                end=float(seg.get("end", 0.0)),
                text=str(seg.get("text", "")).strip(),
                words=seg.get("words", []),
            )
            for seg in aligned_segments
        ]

        info = SimpleNamespace(language=detected_language)
        return segments, info

    def _transcribe_safely(self, audio: Any, options: Dict[str, Any]) -> Any:
        """Run ``self._model.transcribe`` and surface a clear error on failure."""
        try:
            return self._model.transcribe(audio, **options)
        except Exception as exc:
            raise RuntimeError(f"WhisperX transcription failed: {exc}") from exc

    def _align_segments(
        self,
        audio: Any,
        raw_segments: List[Dict[str, Any]],
        language_code: Optional[str],
    ) -> List[Dict[str, Any]]:
        align_model, metadata = _load_alignment_model(language_code)
        if align_model is None or metadata is None:
            return raw_segments
        try:
            # whisperx.align()'s declared types (SingleSegment / AlignedTranscriptionResult)
            # are precise TypedDicts; our segments are structurally compatible plain dicts,
            # so we go through Any at this boundary rather than fighting the type checker.
            aligned: Any = whisperx.align(
                cast(Any, raw_segments),
                align_model,
                metadata,
                audio,
                DEVICE,
                return_char_alignments=False,
            )
            return cast(List[Dict[str, Any]], aligned.get("segments", raw_segments))
        except Exception as exc:
            print(f"⚠️ Alignment failed for '{language_code}': {exc}")
            return raw_segments


class FasterWhisperAdapter:
    """
    Sequential (non-batched) faster-whisper adapter for low-VRAM environments.

    Does NOT perform alignment — use when GPU memory is very limited and
    word-level timestamps are not required.
    """

    def __init__(self, model: Any):
        self._model = model

    def transcribe(
        self,
        audio_path: str | Path,
        language: Optional[str] = None,
        beam_size: Optional[int] = 5,
        batch_size: int = 1,  # ignored — sequential decode only
        vad_filter: bool = False,
        vad_method: Optional[str] = None,
    ):
        effective_vad = vad_method or settings.VAD_METHOD
        use_vad = effective_vad.lower() not in {"none", "off", ""}

        fw_options: Dict[str, Any] = {
            "beam_size": beam_size or 5,
            "vad_filter": use_vad,
        }
        if language:
            fw_options["language"] = language

        raw_segs, fw_info = self._model.transcribe(str(audio_path), **fw_options)

        detected_language = fw_info.language or language or settings.DEFAULT_LANGUAGE or "en"

        segments = []
        for seg in raw_segs:
            segments.append(
                SimpleNamespace(
                    start=float(seg.start),
                    end=float(seg.end),
                    text=str(seg.text).strip(),
                    words=[],
                )
            )

        info = SimpleNamespace(language=detected_language)
        return segments, info


# ---------------------------------------------------------------------------
# Aligner adapter (used by meeting pipeline)
# ---------------------------------------------------------------------------

class WhisperXAligner:
    """Exposes an ``align()`` method compatible with the meeting pipeline."""

    def align(
        self,
        audio_path: str | Path,
        transcription_result: Any,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        audio = whisperx.load_audio(str(audio_path))

        if isinstance(transcription_result, dict):
            raw_segments = transcription_result.get("segments", [])
            detected_language = (
                language
                or transcription_result.get("language")
                or settings.DEFAULT_LANGUAGE
                or "en"
            )
        else:
            raw_segments = []
            detected_language = language or settings.DEFAULT_LANGUAGE or "en"

        align_model, metadata = _load_alignment_model(detected_language)
        if align_model is None or metadata is None:
            return {"segments": raw_segments}

        try:
            # See _align_segments above re: TypedDict vs plain dict at this boundary.
            aligned: Any = whisperx.align(
                cast(Any, raw_segments),
                align_model,
                metadata,
                audio,
                DEVICE,
                return_char_alignments=False,
            )
            return cast(Dict[str, Any], aligned)
        except Exception as exc:
            print(f"⚠️ Alignment failed for '{detected_language}': {exc}")
            return {"segments": raw_segments}


# ---------------------------------------------------------------------------
# Diarizer adapter
# ---------------------------------------------------------------------------

class WhisperXDiarizer:
    """Thin wrapper so the meeting pipeline can call ``diarizer(audio_path)``."""

    def __init__(self, pipeline: Any):
        self._pipeline = pipeline

    def __call__(self, audio_path: str | Path) -> Any:
        if self._pipeline is None:
            return None
        return self._pipeline(str(audio_path))


# ---------------------------------------------------------------------------
# Factory functions — module-level singletons
# ---------------------------------------------------------------------------

def get_whisperx_model() -> Any:
    """Load (or return cached) the raw WhisperX model."""
    global _model
    if _model is None:
        print(f"⏳ Loading WhisperX '{settings.WHISPER_MODEL}' on {DEVICE} ({COMPUTE_TYPE})...")
        _model = whisperx.load_model(
            settings.WHISPER_MODEL,
            DEVICE,
            compute_type=COMPUTE_TYPE,
        )
        print("✅ WhisperX model loaded.")
    return _model


def get_faster_whisper_model() -> Any:
    """Load (or return cached) a raw faster-whisper model (low-VRAM backend)."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            ) from exc

        print(
            f"⏳ Loading faster-whisper '{settings.WHISPER_MODEL}' on {DEVICE} "
            f"({COMPUTE_TYPE}, sequential mode)..."
        )
        _model = WhisperModel(
            settings.WHISPER_MODEL,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
        )
        print("✅ faster-whisper model loaded.")
    return _model


def get_transcriber() -> WhisperXAdapter | FasterWhisperAdapter:
    """
    Factory: return the transcription adapter selected by ``settings.WHISPER_BACKEND``.

    - ``"whisperx"``      → :class:`WhisperXAdapter` (batched, aligned)
    - ``"faster-whisper"`` → :class:`FasterWhisperAdapter` (sequential, low-VRAM)
    """
    if settings.WHISPER_BACKEND.lower() == "faster-whisper":
        return FasterWhisperAdapter(get_faster_whisper_model())
    return WhisperXAdapter(get_whisperx_model())


def get_aligner() -> WhisperXAligner:
    global _aligner
    if _aligner is None:
        _aligner = WhisperXAligner()
    return _aligner


_diarizer_status: str = "not_loaded"  # not_loaded | disabled | no_token | load_failed:<reason> | ready


def get_diarizer_status() -> str:
    """Human-readable reason diarization is (or isn't) available, for surfacing to the UI."""
    return _diarizer_status


def get_diarizer() -> Optional[WhisperXDiarizer]:
    global _diarizer, _diarizer_status
    if _diarizer is None:
        if not settings.ENABLE_DIARIZATION:
            print("ℹ️ Diarization is disabled via ENABLE_DIARIZATION=False.")
            _diarizer_status = "disabled"
            return None
        if not settings.HF_TOKEN:
            print("⚠️ HF_TOKEN not configured; speaker diarization will be skipped.")
            _diarizer_status = "no_token"
            return None
        try:
            from pyannote.audio import Pipeline

            print("⏳ Loading Pyannote diarization pipeline...")
            pipeline = Pipeline.from_pretrained(
                settings.DIARIZATION_MODEL,
                use_auth_token=settings.HF_TOKEN or None,
            )
            if torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
            _diarizer = WhisperXDiarizer(pipeline)
            _diarizer_status = "ready"
            print("✅ Pyannote diarization pipeline loaded.")
        except Exception as exc:
            print(f"❌ Failed to load Pyannote pipeline: {exc}")
            _diarizer_status = f"load_failed:{exc}"
            _diarizer = WhisperXDiarizer(None)
    return _diarizer


# ---------------------------------------------------------------------------
# Memory management
# ---------------------------------------------------------------------------

def _gc_and_empty_cache() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def release_transcriber() -> None:
    """Release the transcription model from memory."""
    global _model
    _model = None
    _gc_and_empty_cache()
    print("🗑️ Transcription model released.")


def release_aligner() -> None:
    """Release the aligner singleton (does NOT clear the language model cache)."""
    global _aligner
    _aligner = None
    _gc_and_empty_cache()


def release_diarizer() -> None:
    """Release the diarizer pipeline from memory."""
    global _diarizer
    _diarizer = None
    _gc_and_empty_cache()
    print("🗑️ Diarizer released.")


def flush_align_cache() -> None:
    """
    Flush only the per-language alignment model cache (lighter than a full flush).

    Useful after processing a multilingual batch when you want to reclaim VRAM
    used by wav2vec alignment models without releasing the transcription model.
    """
    global _align_model_cache
    _align_model_cache.clear()
    _gc_and_empty_cache()
    print("🗑️ Alignment model cache flushed.")


def flush_models() -> None:
    """
    Release ALL loaded models from memory (transcription, alignment cache, diarizer).

    Call this between jobs on low-VRAM systems to prevent OOM errors.
    """
    global _model, _aligner, _diarizer, _align_model_cache
    _model = None
    _aligner = None
    _diarizer = None
    _align_model_cache.clear()
    _gc_and_empty_cache()
    print("🗑️ All models flushed from memory.")


# ---------------------------------------------------------------------------
# NLP helpers
# ---------------------------------------------------------------------------

def build_sentence_segments(text: str, max_words_per_line: int = 20) -> List[str]:
    """
    Split *text* into sentence-level segments using NLTK when available,
    falling back to punctuation-based splitting with word-count wrapping.

    Args:
        text:              Raw transcript text.
        max_words_per_line: Maximum words before a hard line-break is inserted.

    Returns:
        List of sentence strings.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    # Primary: NLTK punkt tokenizer
    try:
        from nltk.tokenize import sent_tokenize

        sentences = sent_tokenize(cleaned)
        if sentences:
            return [s.strip() for s in sentences if s.strip()]
    except Exception:
        pass

    # Fallback: regex punctuation split + word-count wrapping
    segments = re.split(r"(?<=[.!?])\s+", cleaned)
    if max_words_per_line and max_words_per_line > 0:
        wrapped: List[str] = []
        for segment in segments:
            words = segment.split()
            if len(words) <= max_words_per_line:
                wrapped.append(segment)
            else:
                for i in range(0, len(words), max_words_per_line):
                    wrapped.append(" ".join(words[i : i + max_words_per_line]))
        return [s.strip() for s in wrapped if s.strip()]

    return [s.strip() for s in segments if s.strip()]


# ---------------------------------------------------------------------------
# High-level pipeline helpers
# ---------------------------------------------------------------------------

def transcribe_with_alignment(
    audio_path: Path,
    manual_language: Optional[str] = None,
) -> List[Dict]:
    """
    End-to-end WhisperX transcription + forced alignment.

    Returns a list of segment dicts::

        {
            "start": float,
            "end": float,
            "speaker": "Speaker",
            "language": str,
            "text": str,
            "words": [{"word": str, "start": float, "end": float, "score": float}],
        }

    If ``settings.NLTK_SENTENCE_SPLIT`` is True, the text within each aligned
    segment is further split at sentence boundaries to improve subtitle readability.
    """
    audio = whisperx.load_audio(str(audio_path))
    model = get_whisperx_model()

    # -- Transcription -------------------------------------------------------
    tx_options: Dict[str, Any] = {"batch_size": 16}
    if manual_language:
        tx_options["language"] = manual_language

    vad = settings.VAD_METHOD.lower()
    if vad not in {"none", "off", ""}:
        tx_options["vad_filter"] = True
        if vad == "silero":
            tx_options["vad_method"] = "silero"

    result = model.transcribe(audio, **tx_options)
    detected_language = result.get("language") or manual_language or settings.DEFAULT_LANGUAGE or "en"

    # -- Alignment -----------------------------------------------------------
    align_model, metadata = _load_alignment_model(detected_language)
    if align_model is not None and metadata is not None:
        try:
            aligned_result = whisperx.align(
                result.get("segments", []),
                align_model,
                metadata,
                audio,
                DEVICE,
                return_char_alignments=False,
            )
            aligned_segments = aligned_result.get("segments", result.get("segments", []))
        except Exception as exc:
            print(f"⚠️ Alignment failed for '{detected_language}': {exc}")
            aligned_segments = result.get("segments", [])
    else:
        aligned_segments = result.get("segments", [])

    # -- Build output --------------------------------------------------------
    output: List[Dict] = []
    for seg in aligned_segments:
        seg_text = str(seg.get("text", "")).strip()
        words = seg.get("words", [])

        if settings.NLTK_SENTENCE_SPLIT and seg_text:
            sentences = build_sentence_segments(seg_text)
        else:
            sentences = [seg_text] if seg_text else []

        # Distribute timing across sentences (proportional to character length)
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", 0.0))
        total_chars = sum(len(s) for s in sentences) or 1
        current_time = seg_start

        for sentence in sentences:
            frac = len(sentence) / total_chars
            sent_end = current_time + (seg_end - seg_start) * frac
            output.append(
                {
                    "start": round(current_time, 3),
                    "end": round(sent_end, 3),
                    "speaker": "Speaker",
                    "language": detected_language,
                    "text": sentence,
                    "words": words,  # shared; could be filtered per sentence in future
                }
            )
            current_time = sent_end

    return output