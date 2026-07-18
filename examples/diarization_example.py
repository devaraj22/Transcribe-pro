"""
examples/diarization_example.py
================================
End-to-end example showing transcription + speaker diarization + turn grouping.

    python examples/diarization_example.py path/to/meeting.mp3

Requires:
  - HF_TOKEN in .env (Pyannote diarization)
  - pip install -r requirements.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(audio_path: str, language: str = "automatic") -> None:
    from backend.app.core.config import settings
    from backend.app.modules.meeting_mode.pipeline import run_meeting_mode
    from backend.services.whisper_service import flush_models

    if not settings.HF_TOKEN:
        print("⚠️  HF_TOKEN is not set. Diarization will be skipped (single-speaker output).")
        print("   Add HF_TOKEN=your_token to your .env file to enable speaker diarization.")
        print()

    print(f"🎙️  Running Meeting Mode pipeline on: {audio_path}")
    print(f"   Language mode : {language}")
    print()

    # Use a fake job_id — progress updates will print to stdout
    result = run_meeting_mode(
        job_id="example_job",
        audio_path=audio_path,
        language_mode=language,
    )

    segments = result["segments"]
    print(f"\n✅ Pipeline complete — {len(segments)} speaker turns detected.\n")
    print("=" * 70)

    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)
        text = seg.get("text", "")
        print(f"[{start:6.2f}s – {end:6.2f}s]  {speaker}")
        print(f"  {text}\n")

    # Optionally save as JSON
    out_path = Path(audio_path).with_suffix(".diarized.json")
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📄 Full result saved to: {out_path}")

    flush_models()
    print("🗑️  Models flushed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/diarization_example.py <audio_file> [language]")
        sys.exit(1)

    _audio = sys.argv[1]
    _lang = sys.argv[2] if len(sys.argv) > 2 else "automatic"
    main(_audio, _lang)
