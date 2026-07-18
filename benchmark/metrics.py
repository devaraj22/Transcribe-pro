"""
benchmark/metrics.py
=====================
Core metrics for ASR benchmarking:

  - WER  (Word Error Rate) via jiwer
  - RTF  (Real-Time Factor): processing_time / audio_duration
  - Word-segment IoU: intersection-over-union of predicted vs reference
    word intervals (useful when reference STM/CTM files are available)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BenchmarkResult:
    """Holds metrics for a single audio file."""

    filename: str
    duration_seconds: float
    processing_seconds: float
    rtf: float                         # processing_time / audio_duration (lower is better)
    wer: Optional[float] = None        # Word Error Rate (0–1), None if no reference
    num_words_ref: int = 0
    num_words_hyp: int = 0
    detected_language: str = "unknown"
    error: Optional[str] = None        # Set if transcription failed


@dataclass
class BenchmarkSummary:
    """Aggregated results across a test set."""

    total_files: int = 0
    failed_files: int = 0
    total_audio_seconds: float = 0.0
    total_processing_seconds: float = 0.0
    mean_rtf: float = 0.0
    mean_wer: Optional[float] = None
    per_file: List[BenchmarkResult] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Metric functions
# ─────────────────────────────────────────────────────────────────────────────

def compute_wer(reference: str, hypothesis: str) -> float:
    """
    Compute Word Error Rate using jiwer.

    Args:
        reference:  Ground-truth transcript (normalised).
        hypothesis: ASR output transcript (normalised).

    Returns:
        WER as a float in [0, inf). Values > 1.0 are possible with many insertions.

    Raises:
        ImportError: If jiwer is not installed.
    """
    try:
        import jiwer
    except ImportError as exc:
        raise ImportError(
            "jiwer is required for WER computation. Run: pip install jiwer"
        ) from exc

    transformation = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
        jiwer.RemovePunctuation(),
        jiwer.ReduceToListOfListOfWords(),
    ])

    return jiwer.wer(
        reference,
        hypothesis,
        truth_transform=transformation,
        hypothesis_transform=transformation,
    )


def compute_rtf(audio_duration_seconds: float, processing_seconds: float) -> float:
    """
    Real-Time Factor = processing_time / audio_duration.

    RTF < 1 means faster than real-time. RTF = 0.1 means 10x real-time.
    """
    if audio_duration_seconds <= 0:
        return 0.0
    return processing_seconds / audio_duration_seconds


def compute_word_iou(
    ref_words: List[dict],
    hyp_words: List[dict],
) -> float:
    """
    Compute mean word-interval IoU between reference and hypothesis word segments.

    Both *ref_words* and *hyp_words* should be lists of dicts with 'start', 'end',
    and 'word' keys. Words are matched greedily by text (case-insensitive).

    Returns:
        Mean IoU in [0, 1] across matched word pairs.
        Returns 0.0 if no matches found.
    """
    ref_map = {
        w.get("word", "").strip().lower(): (float(w["start"]), float(w["end"]))
        for w in ref_words
        if w.get("word") and "start" in w and "end" in w
    }
    if not ref_map:
        return 0.0

    ious: List[float] = []
    for hw in hyp_words:
        key = hw.get("word", "").strip().lower()
        if key in ref_map:
            r_start, r_end = ref_map[key]
            h_start = float(hw.get("start", 0.0))
            h_end = float(hw.get("end", h_start))

            inter_start = max(r_start, h_start)
            inter_end = min(r_end, h_end)
            inter = max(0.0, inter_end - inter_start)

            union_start = min(r_start, h_start)
            union_end = max(r_end, h_end)
            union = max(0.0, union_end - union_start)

            ious.append(inter / union if union > 0 else 0.0)

    return sum(ious) / len(ious) if ious else 0.0


def aggregate(results: List[BenchmarkResult]) -> BenchmarkSummary:
    """Compute a :class:`BenchmarkSummary` from a list of per-file results."""
    summary = BenchmarkSummary(
        total_files=len(results),
        per_file=results,
    )
    if not results:
        return summary

    failed = [r for r in results if r.error]
    summary.failed_files = len(failed)
    ok = [r for r in results if not r.error]

    summary.total_audio_seconds = sum(r.duration_seconds for r in ok)
    summary.total_processing_seconds = sum(r.processing_seconds for r in ok)
    summary.mean_rtf = (
        sum(r.rtf for r in ok) / len(ok) if ok else 0.0
    )

    wer_values = [r.wer for r in ok if r.wer is not None]
    summary.mean_wer = sum(wer_values) / len(wer_values) if wer_values else None

    return summary
