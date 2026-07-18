"""
quick_capture/pipeline.py
==========================
Synchronous pipeline for short recordings (< LONG_RECORDING_THRESHOLD seconds).

Skips speaker diarization to keep latency low. Uses the WhisperX (or
faster-whisper) transcriber which performs alignment internally and returns
word-level timing in each segment.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.app.core.config import settings
from backend.services.transcription_service import normalize_speaker_label
from backend.services.whisper_service import get_transcriber


def run_quick_capture(audio_path: str, language_mode: str = "automatic") -> Dict[str, Any]:
    """
    Transcribe a short audio file synchronously.

    Args:
        audio_path:    Path to the pre-processed audio file.
        language_mode: ``"automatic"`` or a BCP-47 language code (e.g. ``"fr"``).

    Returns:
        Dict with:
          - ``full_text``: joined transcript string
          - ``segments``: list of segment dicts (start, end, language, speaker, text, words)
    """
    print(f"⚡ Quick Capture pipeline: {audio_path}")
    transcriber = get_transcriber()

    language = None if language_mode.lower() == "automatic" else language_mode.lower()
    segments, info = transcriber.transcribe(audio_path, language=language)

    full_text: List[str] = []
    formatted_segments: List[Dict[str, Any]] = []
    speaker_lookup: Dict[str, str] = {}

    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue

        # Quick Capture always labels as a single speaker (no diarization)
        speaker_label = normalize_speaker_label("SPEAKER_01", speaker_lookup)
        full_text.append(text)

        # Normalise word-level timing entries from the segment
        words = [
            {
                "word": str(w.get("word", "")).strip(),
                "start": round(float(w.get("start", seg.start)), 3),
                "end": round(float(w.get("end", seg.end)), 3),
                "score": round(float(w.get("score", 0.0)), 4),
            }
            for w in (getattr(seg, "words", []) or [])
        ]

        formatted_segments.append(
            {
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "language": info.language,
                "speaker": speaker_label,
                "text": text,
                "words": words,
            }
        )

    return {
        "full_text": " ".join(full_text),
        "segments": formatted_segments,
    }