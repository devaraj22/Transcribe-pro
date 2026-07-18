"""
benchmark/report.py
====================
Render benchmark results as a Markdown table and optionally write a CSV file.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Optional

from benchmark.metrics import BenchmarkSummary


def render_markdown(summary: BenchmarkSummary) -> str:
    """Return a Markdown-formatted report string."""
    lines = [
        "# Transcribe-Pro Benchmark Report",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Files processed | {summary.total_files - summary.failed_files} / {summary.total_files} |",
        f"| Failed files | {summary.failed_files} |",
        f"| Total audio duration | {summary.total_audio_seconds:.1f}s "
        f"({summary.total_audio_seconds / 60:.1f} min) |",
        f"| Total processing time | {summary.total_processing_seconds:.1f}s |",
        f"| **Mean RTF** | **{summary.mean_rtf:.4f}** |",
    ]

    if summary.mean_wer is not None:
        lines.append(f"| **Mean WER** | **{summary.mean_wer:.1%}** |")
    else:
        lines.append("| Mean WER | N/A (no reference transcripts) |")

    lines += [
        "",
        "## Per-File Results",
        "",
        "| File | Duration | Proc. Time | RTF | WER | Language | Status |",
        "|------|----------|------------|-----|-----|----------|--------|",
    ]

    for r in summary.per_file:
        status = "✅" if not r.error else "❌"
        wer_str = f"{r.wer:.1%}" if r.wer is not None else "N/A"
        lines.append(
            f"| {r.filename} "
            f"| {r.duration_seconds:.1f}s "
            f"| {r.processing_seconds:.1f}s "
            f"| {r.rtf:.3f} "
            f"| {wer_str} "
            f"| {r.detected_language} "
            f"| {status} |"
        )

    if any(r.error for r in summary.per_file):
        lines += [
            "",
            "## Errors",
            "",
        ]
        for r in summary.per_file:
            if r.error:
                lines.append(f"- **{r.filename}**: {r.error}")

    return "\n".join(lines) + "\n"


def write_csv(summary: BenchmarkSummary, output_path: str | Path) -> Path:
    """Write per-file results to a CSV file."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "filename", "duration_seconds", "processing_seconds",
                "rtf", "wer", "num_words_ref", "num_words_hyp",
                "detected_language", "error",
            ],
        )
        writer.writeheader()
        for r in summary.per_file:
            writer.writerow(
                {
                    "filename": r.filename,
                    "duration_seconds": round(r.duration_seconds, 3),
                    "processing_seconds": round(r.processing_seconds, 3),
                    "rtf": round(r.rtf, 4),
                    "wer": f"{r.wer:.4f}" if r.wer is not None else "",
                    "num_words_ref": r.num_words_ref,
                    "num_words_hyp": r.num_words_hyp,
                    "detected_language": r.detected_language,
                    "error": r.error or "",
                }
            )

    return target
