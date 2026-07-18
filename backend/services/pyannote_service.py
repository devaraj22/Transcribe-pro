"""
pyannote_service.py — Backwards-compatibility shim.

Diarization is now fully managed through `whisper_service.get_diarizer()` which
wraps the Pyannote pipeline inside WhisperXDiarizer. This module re-exports
the public interface so any legacy callers continue to work without changes.
"""

from backend.services.whisper_service import get_diarizer as get_diarization_pipeline

__all__ = ["get_diarization_pipeline"]
