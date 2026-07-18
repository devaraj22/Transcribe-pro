"""
benchmark/runner.py
====================
Runs the Transcribe-Pro pipeline against a directory of audio files and
optionally loads reference transcripts (.txt / .stm) for WER computation.

Usage (from project root):
    python -m benchmark --audio-dir /path/to/tedlium/test --model base

Directory layout expected:
    audio_dir/
      file1.wav
      file1.txt    ← optional reference transcript (plain text)
      file2.flac
      file2.txt
      ...

If no .txt reference is found for an audio file, WER is reported as N/A.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

from benchmark.metrics import BenchmarkResult, compute_wer, compute_rtf


AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".m4a", ".ogg", ".opus"}


def _load_reference(audio_path: Path) -> Optional[str]:
    """Look for a plain-text reference transcript next to the audio file."""
    ref = audio_path.with_suffix(".txt")
    if ref.exists():
        return ref.read_text(encoding="utf-8").strip()
    # TEDLIUM STM format: each line is <filename> <channel> <speaker> <start> <end> <label> <text>
    stm = audio_path.with_suffix(".stm")
    if stm.exists():
        parts = []
        for line in stm.read_text(encoding="utf-8").splitlines():
            tokens = line.strip().split(maxsplit=6)
            if len(tokens) == 7 and not tokens[6].startswith("<"):
                parts.append(tokens[6])
        return " ".join(parts).strip() or None
    return None


def _probe_duration(audio_path: Path) -> float:
    """Use ffprobe to get audio duration in seconds."""
    import subprocess
    import json as _json

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = _json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0.0))
    except Exception:
        return 0.0


def run_benchmark(
    audio_dir: str,
    model_name: Optional[str] = None,
    language: str = "automatic",
    max_files: Optional[int] = None,
) -> List[BenchmarkResult]:
    """
    Transcribe every audio file in *audio_dir* and collect benchmark metrics.

    Args:
        audio_dir:   Path to directory containing audio (and optionally .txt) files.
        model_name:  Override ``WHISPER_MODEL`` setting for this run.
        language:    ``"automatic"`` or BCP-47 code.
        max_files:   Cap the number of files processed (useful for quick smoke tests).

    Returns:
        List of :class:`~benchmark.metrics.BenchmarkResult` objects.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from backend.app.core.config import settings
    from backend.services.whisper_service import get_transcriber, flush_models

    if model_name:
        # Override model for this benchmark run
        settings.WHISPER_MODEL = model_name  # type: ignore[misc]

    audio_root = Path(audio_dir)
    if not audio_root.is_dir():
        raise ValueError(f"Audio directory does not exist: {audio_root}")

    audio_files = sorted(
        p for p in audio_root.rglob("*") if p.suffix.lower() in AUDIO_EXTENSIONS
    )
    if max_files:
        audio_files = audio_files[:max_files]

    if not audio_files:
        print(f"⚠️  No audio files found in {audio_root}")
        return []

    print(f"📂 Found {len(audio_files)} audio files. Loading model…")
    transcriber = get_transcriber()
    print(f"✅ Model ready ({settings.WHISPER_MODEL}, {settings.WHISPER_BACKEND} backend)")
    print()

    results: List[BenchmarkResult] = []
    lang = None if language == "automatic" else language

    for idx, audio_path in enumerate(audio_files, start=1):
        print(f"[{idx:3d}/{len(audio_files)}] {audio_path.name}", end="  ", flush=True)

        duration = _probe_duration(audio_path)
        reference = _load_reference(audio_path)

        t0 = time.perf_counter()
        try:
            segments, info = transcriber.transcribe(str(audio_path), language=lang)
            elapsed = time.perf_counter() - t0

            hypothesis = " ".join(seg.text.strip() for seg in segments)
            wer = compute_wer(reference, hypothesis) if reference else None
            rtf = compute_rtf(duration, elapsed)

            result = BenchmarkResult(
                filename=audio_path.name,
                duration_seconds=duration,
                processing_seconds=elapsed,
                rtf=rtf,
                wer=wer,
                num_words_ref=len(reference.split()) if reference else 0,
                num_words_hyp=len(hypothesis.split()),
                detected_language=info.language,
            )
            wer_str = f"WER={wer:.1%}" if wer is not None else "WER=N/A"
            print(f"RTF={rtf:.3f}  {wer_str}  lang={info.language}")

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f"❌ FAILED: {exc}")
            result = BenchmarkResult(
                filename=audio_path.name,
                duration_seconds=duration,
                processing_seconds=elapsed,
                rtf=0.0,
                error=str(exc),
            )

        results.append(result)

    flush_models()
    print("\n🗑️  Models flushed.")
    return results
