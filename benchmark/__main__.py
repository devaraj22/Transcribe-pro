"""
benchmark/__main__.py
======================
CLI entry point for the Transcribe-Pro ASR benchmarking harness.

    python -m benchmark --audio-dir /path/to/tedlium/test --model base
    python -m benchmark --audio-dir /path/to/tedlium/test --model large-v3 --max-files 10

Options:
  --audio-dir   Path to directory containing audio files + optional .txt/.stm references.
  --model       Whisper model size (tiny, base, small, medium, large-v3). Default: base.
  --language    BCP-47 language code or 'automatic'. Default: automatic.
  --max-files   Limit the number of files processed (useful for quick tests).
  --output-dir  Where to write markdown and CSV reports. Default: ./benchmark_results/
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Allow running as `python -m benchmark` from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m benchmark",
        description="Transcribe-Pro ASR benchmark (WER + RTF) against a directory of audio files.",
    )
    parser.add_argument("--audio-dir", required=True, help="Directory of audio files to benchmark.")
    parser.add_argument("--model", default="base", help="Whisper model size (default: base).")
    parser.add_argument(
        "--language", default="automatic", help="Language code or 'automatic' (default: automatic)."
    )
    parser.add_argument(
        "--max-files", type=int, default=None, help="Maximum files to process (default: all)."
    )
    parser.add_argument(
        "--output-dir",
        default="benchmark_results",
        help="Directory for markdown + CSV output (default: benchmark_results/).",
    )
    args = parser.parse_args()

    from benchmark.runner import run_benchmark
    from benchmark.metrics import aggregate
    from benchmark.report import render_markdown, write_csv

    print("=" * 60)
    print("  Transcribe-Pro ASR Benchmark")
    print("=" * 60)
    print(f"  Audio dir : {args.audio_dir}")
    print(f"  Model     : {args.model}")
    print(f"  Language  : {args.language}")
    print(f"  Max files : {args.max_files or 'all'}")
    print("=" * 60)
    print()

    results = run_benchmark(
        audio_dir=args.audio_dir,
        model_name=args.model,
        language=args.language,
        max_files=args.max_files,
    )

    summary = aggregate(results)

    # ── Print markdown to terminal ─────────────────────────────────────────
    md = render_markdown(summary)
    print("\n" + md)

    # ── Save reports to disk ───────────────────────────────────────────────
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"benchmark_{args.model}_{timestamp}.md"
    csv_path = out_dir / f"benchmark_{args.model}_{timestamp}.csv"

    md_path.write_text(md, encoding="utf-8")
    write_csv(summary, csv_path)

    print(f"\n📄 Markdown report → {md_path}")
    print(f"📊 CSV results     → {csv_path}")


if __name__ == "__main__":
    main()
