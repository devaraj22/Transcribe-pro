"""
examples/subtitle_export.py
============================
Demonstrate ASS and SRT subtitle export from an audio file.

    python examples/subtitle_export.py path/to/audio.mp3

Produces:
  - audio.ass   (Advanced SubStation Alpha, for VLC/mpv/Aegisub)
  - audio.srt   (SubRip, universal compatibility)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(audio_path: str, language: str = "automatic") -> None:
    from backend.services.whisper_service import (
        transcribe_with_alignment,
        write_ass_subtitles,
        write_srt_subtitles,
        flush_models,
    )

    audio = Path(audio_path)
    print(f"🎙️  Transcribing: {audio}")

    segments = transcribe_with_alignment(
        audio_path=audio,
        manual_language=None if language == "automatic" else language,
    )
    print(f"✅ {len(segments)} segments produced.")

    # ── ASS export ─────────────────────────────────────────────────────────────
    ass_path = audio.with_suffix(".ass")
    write_ass_subtitles(segments, ass_path)
    print(f"📄 ASS subtitles  → {ass_path}")

    # ── SRT export ─────────────────────────────────────────────────────────────
    srt_path = audio.with_suffix(".srt")
    write_srt_subtitles(segments, srt_path)
    print(f"📄 SRT subtitles  → {srt_path}")

    # ── Preview first 5 entries ────────────────────────────────────────────────
    print("\n── First 5 segments preview ─────────────────────────────────────")
    for seg in segments[:5]:
        print(f"  [{seg['start']:.2f}s – {seg['end']:.2f}s]  {seg['text']}")

    flush_models()
    print("\n🗑️  Models flushed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/subtitle_export.py <audio_file> [language]")
        sys.exit(1)

    _audio = sys.argv[1]
    _lang = sys.argv[2] if len(sys.argv) > 2 else "automatic"
    main(_audio, _lang)
