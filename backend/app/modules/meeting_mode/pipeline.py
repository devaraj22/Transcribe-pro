"""
meeting_mode/pipeline.py
========================
End-to-end pipeline for long recordings (Meeting Mode).

Steps:
  1. Transcription via WhisperX
  2. Forced alignment (word-level timestamps)
  3. Speaker diarization via Pyannote
  4. Word-level speaker assignment
  5. Grouping into speaker-turn segments (NOT per-word)
  6. Optional NLTK sentence splitting within each turn

The output segments have the schema::

    {
        "start":    float,
        "end":      float,
        "language": str,
        "speaker":  str,         # e.g. "Speaker 1"
        "text":     str,         # full turn transcript
        "words":    List[dict],  # word-level timing for frontend highlighting
    }
"""

from __future__ import annotations

import gc
from typing import Any, Dict, List, Optional, cast

import torch
import whisperx
from backend.services.denoiser_service import denoise_audio

from backend.app.core.config import settings
from backend.app.modules.meeting_mode.background_jobs import update_job_status
from backend.services.whisper_service import (
    get_transcriber,
    get_aligner,
    get_diarizer,
    get_diarizer_status,
    release_transcriber,
    release_aligner,
    release_diarizer,
    build_sentence_segments,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Gap (seconds) between consecutive words that triggers a new speaker turn,
# even if the speaker label is the same. Prevents very long monologue blocks.
_TURN_GAP_THRESHOLD: float = 3.0


def _gc_cuda() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _group_words_into_turns(
    word_segments: List[Dict[str, Any]],
    detected_language: str,
) -> List[Dict[str, Any]]:
    """
    Group a flat list of word-level dicts (from ``whisperx.assign_word_speakers``)
    into speaker-turn segments.

    Two consecutive words are merged into the same turn when:
      - They share the same speaker label, AND
      - The gap between them is less than ``_TURN_GAP_THRESHOLD`` seconds.

    Each output turn contains:
      - start / end timestamps
      - speaker label (human-readable "Speaker N")
      - text (all words joined)
      - words (list of word-level timing dicts for frontend highlighting)
    """
    if not word_segments:
        return []

    speaker_lookup: Dict[str, str] = {}

    def _human_label(raw: Optional[str]) -> str:
        """Map raw pyannote labels like SPEAKER_00 → Speaker 1, Speaker 2…"""
        key = (raw or "SPEAKER_00").strip()
        if key not in speaker_lookup:
            speaker_lookup[key] = f"Speaker {len(speaker_lookup) + 1}"
        return speaker_lookup[key]

    turns: List[Dict[str, Any]] = []
    current_words: List[Dict[str, Any]] = []
    current_speaker: Optional[str] = None
    turn_start: float = 0.0
    prev_end: float = 0.0

    for word in word_segments:
        raw_word = str(word.get("word", "")).strip()
        if not raw_word:
            continue

        raw_speaker = word.get("speaker") or "SPEAKER_00"
        human_speaker = _human_label(raw_speaker)
        word_start = float(word.get("start", prev_end))
        word_end = float(word.get("end", word_start))
        gap = word_start - prev_end

        # Start a new turn if speaker changed or there's a long silence
        if current_words and (human_speaker != current_speaker or gap >= _TURN_GAP_THRESHOLD):
            turns.append(_build_turn(current_words, current_speaker, turn_start, prev_end, detected_language))
            current_words = []
            turn_start = word_start

        if not current_words:
            turn_start = word_start
            current_speaker = human_speaker

        current_words.append(
            {
                "word": raw_word,
                "start": round(word_start, 3),
                "end": round(word_end, 3),
                "score": round(float(word.get("score", 0.0)), 4),
            }
        )
        prev_end = word_end

    # Flush the last turn
    if current_words:
        turns.append(_build_turn(current_words, current_speaker, turn_start, prev_end, detected_language))

    return turns


def _build_turn(
    words: List[Dict[str, Any]],
    speaker: Optional[str],
    start: float,
    end: float,
    language: str,
) -> Dict[str, Any]:
    """Assemble a single speaker-turn dict from accumulated word list."""
    text = " ".join(w["word"] for w in words)

    # Optionally split long turns at sentence boundaries
    if settings.NLTK_SENTENCE_SPLIT and text:
        sentences = build_sentence_segments(text)
        text = " ".join(sentences)  # re-join; individual sentence timing is handled by subtitle export

    return {
        "start": round(start, 3),
        "end": round(end, 3),
        "language": language,
        "speaker": speaker or "Speaker 1",
        "text": text,
        "words": words,
    }


def _fallback_segments(
    aligned_result: Dict[str, Any],
    detected_language: str,
) -> List[Dict[str, Any]]:
    """
    Build output segments from aligned (but un-diarized) whisperx segments.
    All segments are labelled 'Speaker 1'.
    """
    out = []
    for seg in aligned_result.get("segments", []):
        seg_text = str(seg.get("text", "")).strip()
        words = [
            {
                "word": str(w.get("word", "")).strip(),
                "start": round(float(w.get("start", 0.0)), 3),
                "end": round(float(w.get("end", 0.0)), 3),
                "score": round(float(w.get("score", 0.0)), 4),
            }
            for w in seg.get("words", [])
        ]
        out.append(
            {
                "start": round(float(seg.get("start", 0.0)), 3),
                "end": round(float(seg.get("end", 0.0)), 3),
                "language": detected_language,
                "speaker": "Speaker 1",
                "text": seg_text,
                "words": words,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Public pipeline
# ---------------------------------------------------------------------------

def run_meeting_mode(job_id: str, audio_path: str, language_mode: str = "automatic") -> Dict[str, Any]:
    """
    Run the full Meeting Mode pipeline for a long recording.

    Progress milestones reported to job status:
      5% → started
      30% → transcription done
      55% → alignment done
      80% → diarization done
      100% → complete

    Args:
        job_id:        Unique job identifier (used for status updates).
        audio_path:    Path to the pre-processed audio WAV file.
        language_mode: ``"automatic"`` (let WhisperX detect) or a BCP-47 code like ``"fr"``.

    Returns:
        Dict with keys ``full_text`` and ``segments``.
    """
    print(f"🚀 Meeting Mode pipeline started for job [{job_id}]: {audio_path}")
    update_job_status(job_id, status="processing", progress=5.0)

    audio_path = denoise_audio(audio_path)

    language = None if language_mode.lower() == "automatic" else language_mode.lower()

    # ------------------------------------------------------------------
    # Step 1: Transcription
    # ------------------------------------------------------------------
    print("⏳ [1/4] Transcribing audio...")
    transcriber = get_transcriber()
    tx_result = transcriber.transcribe(audio_path, language=language)

    # transcriber.transcribe returns (segments, info) for both adapters
    if isinstance(tx_result, tuple):
        _segs, info = tx_result
        detected_language = info.language
        # Re-build raw dict for aligner (which expects whisperx dict format)
        raw_dict: Dict[str, Any] = {
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "words": getattr(s, "words", []),
                }
                for s in _segs
            ],
            "language": detected_language,
        }
    else:
        raw_dict = tx_result  # should not happen but guard
        detected_language = raw_dict.get("language", settings.DEFAULT_LANGUAGE or "en")

    update_job_status(job_id, progress=30.0)
    release_transcriber()
    _gc_cuda()

    # ------------------------------------------------------------------
    # Step 2: Forced alignment (word-level timestamps)
    # ------------------------------------------------------------------
    print(f"⏳ [2/4] Aligning segments (language: {detected_language})...")
    aligner = get_aligner()
    aligned_result = aligner.align(audio_path, raw_dict, language=detected_language)
    update_job_status(job_id, progress=55.0)
    release_aligner()
    _gc_cuda()

    # ------------------------------------------------------------------
    # Step 3: Speaker diarization
    # ------------------------------------------------------------------
    print("⏳ [3/4] Running speaker diarization...")
    diarizer = get_diarizer()
    diarization_result = None
    diarization_note: Optional[str] = None

    if diarizer is None:
        _status = get_diarizer_status()
        diarization_note = {
            "disabled": "Speaker diarization is disabled on this server (ENABLE_DIARIZATION=False).",
            "no_token": "Speaker diarization requires a Hugging Face token (HF_TOKEN) that isn't configured on this server.",
        }.get(_status, f"Speaker diarization is unavailable: {_status}")
    else:
        try:
            diarization_result = diarizer(audio_path)
            if diarization_result is None:
                # diarizer exists but its underlying pipeline failed to load
                _status = get_diarizer_status()
                if _status.startswith("load_failed:"):
                    diarization_note = f"Speaker diarization failed to load: {_status.split(':', 1)[1]}"
        except Exception as exc:
            print(f"⚠️ Diarization skipped: {exc}")
            diarization_note = f"Speaker diarization failed while processing this recording: {exc}"

    update_job_status(job_id, progress=80.0)
    release_diarizer()
    _gc_cuda()

    # ------------------------------------------------------------------
    # Step 4: Speaker assignment + turn grouping
    # ------------------------------------------------------------------
    print("⏳ [4/4] Assigning speakers and grouping turns...")

    if diarization_result is not None:
        try:
            # whisperx.assign_word_speakers()'s declared type expects its own
            # precise AlignedTranscriptionResult/TranscriptionResult TypedDict;
            # aligned_result is a structurally compatible plain dict, so we
            # go through Any at this boundary (same pattern as whisper_service
            # .py's _align_segments) rather than fighting the type checker.
            word_level = whisperx.assign_word_speakers(diarization_result, cast(Any, aligned_result))
            # assign_word_speakers returns a dict with "segments" containing word dicts
            all_words: List[Dict] = []
            for seg in word_level.get("segments", []):
                for word in seg.get("words", []):
                    all_words.append(word)
            segments = _group_words_into_turns(all_words, detected_language)
        except Exception as exc:
            print(f"⚠️ Speaker assignment failed, falling back to unlabelled segments: {exc}")
            diarization_note = f"Speaker assignment failed: {exc}"
            segments = _fallback_segments(aligned_result, detected_language)
    else:
        print("ℹ️ No diarization result — producing unlabelled segments.")
        segments = _fallback_segments(aligned_result, detected_language)

    # Build full_text as a speaker-turn transcript
    full_text_parts = []
    for seg in segments:
        full_text_parts.append(f"{seg['speaker']}: {seg['text']}")

    result = {
        "full_text": "\n".join(full_text_parts),
        "segments": segments,
        "diarization_note": diarization_note,  # None when diarization succeeded normally
    }

    update_job_status(job_id, progress=100.0)
    print(f"✅ Meeting Mode pipeline complete for job [{job_id}]. {len(segments)} turns produced.")
    return result