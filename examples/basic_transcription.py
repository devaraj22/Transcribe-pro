"""
examples/basic_transcription.py
================================
Standalone Python script demonstrating basic transcription with Transcribe-Pro's
service layer.  No FastAPI server required — run directly:

    python examples/basic_transcription.py path/to/audio.mp3

Prerequisites:
    pip install -r requirements.txt
    export WHISPER_MODEL=base  # or set in .env
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(audio_path: str, language: str = "automatic") -> None:
    from backend.app.core.config import settings
    from backend.services.whisper_service import get_transcriber, flush_models

    print(f"🎙️  Transcribing: {audio_path}")
    print(f"   Model    : {settings.WHISPER_MODEL} ({settings.WHISPER_BACKEND} backend)")
    print(f"   Language : {language or 'auto-detect'}")
    print()

    transcriber = get_transcriber()
    segments, info = transcriber.transcribe(audio_path, language=None if language == "automatic" else language)

    print(f"✅ Detected language: {info.language}")
    print(f"   Segments produced: {len(segments)}")
    print()

    for seg in segments:
        ts = f"{seg.start:6.2f}s – {seg.end:6.2f}s"
        print(f"  [{ts}]  {seg.text}")

    # Release GPU/CPU memory when done
    flush_models()
    print("\n🗑️  Models flushed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/basic_transcription.py <audio_file> [language]")
        sys.exit(1)

    _audio = sys.argv[1]
    _lang = sys.argv[2] if len(sys.argv) > 2 else "automatic"
    main(_audio, _lang)
