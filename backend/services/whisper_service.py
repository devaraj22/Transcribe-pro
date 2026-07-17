<<<<<<< HEAD
import gc
import os

import torch
import whisperx
from backend.app.core.config import settings

_transcriber = None
_aligner = None
_diarizer = None


def _device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_transcriber():
    global _transcriber
    if _transcriber is None:
        device = _device()
        print(f"⏳ Loading WhisperX transcriber '{settings.WHISPER_MODEL}' on {device}...")
        _transcriber = whisperx.load_model(settings.WHISPER_MODEL, device=device)
    return _transcriber


def get_aligner():
    global _aligner
    if _aligner is None:
        print("⏳ Loading WhisperX alignment model...")
        _aligner = whisperx.load_align_model(settings.WHISPER_MODEL, device=_device())
    return _aligner


def get_diarizer():
    global _diarizer
    if _diarizer is None:
        print("⏳ Loading WhisperX diarization pipeline...")
        _diarizer = whisperx.DiarizationPipeline(
            model=settings.DIARIZATION_MODEL,
            use_auth_token=settings.HF_TOKEN,
            device=_device(),
        )
    return _diarizer


def release_transcriber():
    global _transcriber
    _transcriber = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def release_aligner():
    global _aligner
    _aligner = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def release_diarizer():
    global _diarizer
    _diarizer = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
=======
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional

import torch
import whisperx

from backend.app.core.config import settings

_model = None
_align_model_cache: Dict[str, tuple] = {}

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"


class WhisperXAdapter:
    """Compatibility wrapper around WhisperX for the existing transcription pipelines."""

    def __init__(self, model):
        self._model = model

    def transcribe(self, audio_path: str | Path, language=None, beam_size=None, batch_size: int = 16):
        """Transcribe an audio path and return segments compatible with existing callers."""
        audio = whisperx.load_audio(str(audio_path))
        result = self._model.transcribe(audio, language=language, batch_size=batch_size)
        detected_language = language or result.get("language", "en")

        align_model, metadata = _align_model_cache.get(detected_language, (None, None))
        if align_model is None:
            try:
                align_model, metadata = whisperx.load_align_model(
                    language_code=detected_language,
                    device=DEVICE,
                )
                _align_model_cache[detected_language] = (align_model, metadata)
            except Exception as exc:
                print(f"⚠️ Alignment model could not be loaded for '{detected_language}': {exc}")
                aligned_segments = result.get("segments", [])
            else:
                try:
                    aligned_result = whisperx.align(
                        result["segments"],
                        align_model,
                        metadata,
                        audio,
                        DEVICE,
                        return_char_alignments=False,
                    )
                    aligned_segments = aligned_result.get("segments", [])
                except Exception as exc:
                    print(f"⚠️ Alignment failed for '{detected_language}': {exc}")
                    aligned_segments = result.get("segments", [])
        else:
            try:
                aligned_result = whisperx.align(
                    result["segments"],
                    align_model,
                    metadata,
                    audio,
                    DEVICE,
                    return_char_alignments=False,
                )
                aligned_segments = aligned_result.get("segments", [])
            except Exception as exc:
                print(f"⚠️ Alignment failed for '{detected_language}': {exc}")
                aligned_segments = result.get("segments", [])

        segments = []
        for seg in aligned_segments:
            segments.append(
                SimpleNamespace(
                    start=float(seg.get("start", 0.0)),
                    end=float(seg.get("end", 0.0)),
                    text=str(seg.get("text", "")).strip(),
                )
            )

        info = SimpleNamespace(language=detected_language)
        return segments, info


def get_whisperx_model():
    global _model
    if _model is None:
        print(f"⏳ Loading WhisperX '{settings.WHISPER_MODEL}' model...")
        _model = whisperx.load_model(settings.WHISPER_MODEL, DEVICE, compute_type=COMPUTE_TYPE)
    return _model


def get_whisper_model():
    """Return a transcription adapter compatible with the existing pipeline callers."""
    return WhisperXAdapter(get_whisperx_model())


def transcribe_with_alignment(audio_path: Path, manual_language: Optional[str] = None) -> List[Dict]:
    """
    WhisperX transcription + alignment with a single placeholder speaker label.
    """
    audio = whisperx.load_audio(str(audio_path))

    model = get_whisperx_model()
    result = model.transcribe(audio, language=manual_language, batch_size=16)
    detected_language = manual_language or result.get("language", "en")

    align_model, metadata = _align_model_cache.get(detected_language, (None, None))
    if align_model is None:
        try:
            align_model, metadata = whisperx.load_align_model(
                language_code=detected_language,
                device=DEVICE,
            )
            _align_model_cache[detected_language] = (align_model, metadata)
        except Exception as exc:
            print(f"⚠️ Alignment model could not be loaded for '{detected_language}': {exc}")
            aligned_segments = result.get("segments", [])
        else:
            try:
                aligned_result = whisperx.align(
                    result["segments"],
                    align_model,
                    metadata,
                    audio,
                    DEVICE,
                    return_char_alignments=False,
                )
                aligned_segments = aligned_result.get("segments", [])
            except Exception as exc:
                print(f"⚠️ Alignment failed for '{detected_language}': {exc}")
                aligned_segments = result.get("segments", [])
    else:
        try:
            aligned_result = whisperx.align(
                result["segments"],
                align_model,
                metadata,
                audio,
                DEVICE,
                return_char_alignments=False,
            )
            aligned_segments = aligned_result.get("segments", [])
        except Exception as exc:
            print(f"⚠️ Alignment failed for '{detected_language}': {exc}")
            aligned_segments = result.get("segments", [])

    merged_segments = []
    for seg in aligned_segments:
        merged_segments.append(
            {
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "speaker": "Speaker",
                "language": detected_language,
                "text": str(seg.get("text", "")).strip(),
            }
        )
    return merged_segments
>>>>>>> 8b919d0 (update model)
