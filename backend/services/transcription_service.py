"""
transcription_service.py
========================
Whisper / WhisperX speech-to-text transcription and word alignment service.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Tuple
import torch
import whisperx
from backend.app.core.config import settings

# Cache loaded models in memory
_MODEL_CACHE: Dict[str, Any] = {}


def get_whisper_model(
    model_name: str = "medium",
    device: Optional[str] = None,
    compute_type: str = "float16"
) -> Tuple[Any, str]:
    """
    Loads and caches the WhisperX model with VAD configuration.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        compute_type = "int8"

    cache_key = f"{model_name}_{device}_{compute_type}"
    if cache_key not in _MODEL_CACHE:
        print(f"🚀 Loading WhisperX model [{model_name}] on [{device}]...")
        
        # VAD Options configured at model initialization time
        vad_options = {"vad_onset": 0.500, "vad_offset": 0.363}
        
        model = whisperx.load_model(
            model_name,
            device=device,
            compute_type=compute_type,
            vad_options=vad_options
        )
        _MODEL_CACHE[cache_key] = model

    return _MODEL_CACHE[cache_key], device


def transcribe_audio(
    audio_path: str,
    model_name: Optional[str] = None,
    language_mode: Optional[str] = "en",
    batch_size: int = 16
) -> dict:
    """
    Transcribes audio file using WhisperX.
    Defaults to English ('en') to prevent inaccurate auto-detection on short clips.
    """
    selected_model_name = model_name or getattr(settings, "WHISPER_MODEL", "medium") or "medium"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    model, device = get_whisper_model(model_name=selected_model_name, device=device, compute_type=compute_type)

    audio = whisperx.load_audio(audio_path)

    # Force English if language_mode is set to automatic/auto or empty
    if not language_mode or language_mode.lower() in ["automatic", "auto", "none", ""]:
        lang_code = "en"
    else:
        lang_code = language_mode

    result = model.transcribe(audio, batch_size=batch_size, language=lang_code)
    return result


def align_whisper_output(
    segments: list,
    audio_path: str,
    language_code: str = "en"
) -> list:
    """
    Aligns whisper transcript segments to get exact word-level timestamps.
    """
    if not segments:
        return []

    device = "cuda" if torch.cuda.is_available() else "cpu"

    try:
        model_a, metadata = whisperx.load_align_model(language_code=language_code, device=device)
        audio = whisperx.load_audio(audio_path)
        aligned_result = whisperx.align(segments, model_a, metadata, audio, device, return_char_alignments=False)
        return aligned_result.get("segments", segments)
    except Exception as exc:
        print(f"⚠️ Alignment skipped/failed for language [{language_code}]: {exc}")
        return segments


# Aliases for backward compatibility
transcribe = transcribe_audio