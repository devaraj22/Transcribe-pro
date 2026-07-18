"""
examples/word_highlighting.py
==============================
Demonstrate word-level timing output — the data that drives the
karaoke-style word-highlighting feature in the React frontend.

    python examples/word_highlighting.py path/to/audio.mp3

Prints a rich table of words with their start/end timestamps and
alignment confidence scores.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _bar(score: float, width: int = 10) -> str:
    """ASCII confidence bar."""
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def main(audio_path: str, language: str = "automatic") -> None:
    from backend.services.whisper_service import get_transcriber, flush_models

    print(f"🎙️  Transcribing with word-level alignment: {audio_path}")
    transcriber = get_transcriber()

    segments, info = transcriber.transcribe(
        audio_path,
        language=None if language == "automatic" else language,
    )

    print(f"✅ Language: {info.language}  |  Segments: {len(segments)}\n")

    total_words = 0
    for seg_idx, seg in enumerate(segments):
        words = getattr(seg, "words", []) or []
        if not words:
            continue

        print(f"── Segment {seg_idx + 1}: [{seg.start:.2f}s – {seg.end:.2f}s] ──")
        print(f"   Text: {seg.text}")
        print()
        print(f"   {'START':>8}  {'END':>8}  {'SCORE':>6}  CONF    WORD")
        print(f"   {'─'*8}  {'─'*8}  {'─'*6}  {'─'*10}  {'─'*30}")

        for w in words:
            word_text = str(w.get("word", "")).strip()
            start = float(w.get("start", 0.0))
            end = float(w.get("end", 0.0))
            score = float(w.get("score", 0.0))
            bar = _bar(score)
            print(f"   {start:8.3f}  {end:8.3f}  {score:6.3f}  {bar}  {word_text}")
            total_words += 1

        print()

    print(f"\n📊 Total words with timing: {total_words}")
    flush_models()
    print("🗑️  Models flushed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/word_highlighting.py <audio_file> [language]")
        sys.exit(1)

    _audio = sys.argv[1]
    _lang = sys.argv[2] if len(sys.argv) > 2 else "automatic"
    main(_audio, _lang)
