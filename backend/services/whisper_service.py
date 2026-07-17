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