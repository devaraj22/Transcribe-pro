"""
pyannote_service.py — Backwards-compatibility shim.

Diarization is now fully managed through `whisper_service.get_diarizer()` which
wraps the Pyannote pipeline inside WhisperXDiarizer. This module re-exports
the public interface so any legacy callers continue to work without changes.
"""
