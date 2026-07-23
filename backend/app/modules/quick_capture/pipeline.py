"""
quick_capture/pipeline.py
==========================
Quick Capture Pipeline for short recordings (< 10 mins).
Executes Denoising -> WhisperX Transcription -> Word Alignment -> RAG Indexing.
"""

from __future__ import annotations

import os
import re
from typing import Optional, Dict, Any, List

from backend.app.core.config import settings
from backend.services.denoiser_service import denoise_audio
from backend.services import transcription_service

# Safe import for FAISS RAG service
try:
    from backend.services.faiss_service import create_vector_index
except ImportError:
    create_vector_index = None

# Safe import for Meeting Mode fallback
try:
    from backend.app.modules.meeting_mode.pipeline import run_meeting_mode as run_whisperx_meeting_mode
except ImportError:
    run_whisperx_meeting_mode = None


def normalize_speaker_label(
    raw_label: Optional[str],
    speaker_lookup: Optional[Dict[str, str]] = None,
    fallback_index: Optional[int] = None,
) -> str:
    """
    Convert diarization labels like SPEAKER_00, speaker-1 into stable labels (SPEAKER_01, etc.).
    """
    lookup = speaker_lookup if speaker_lookup is not None else {}
    label_key = (raw_label or "UNKNOWN").strip()
    normalized_key = re.sub(r"[^a-z0-9]+", "", label_key.lower())

    if not label_key or normalized_key in {"unknown", "speakerunknown", "speaker00", "speaker0", "speaker", "none", "null"}:
        speaker_identity = "speaker1" if not lookup else "unknown"
    else:
        speaker_identity = normalized_key
        if re.search(r"speaker", label_key, re.IGNORECASE):
            match = re.search(r"(\d+)", label_key)
            if match:
                speaker_num = int(match.group(1))
                speaker_identity = f"speaker{speaker_num if speaker_num > 0 else 1}"
            else:
                speaker_identity = "speaker1"

    if speaker_identity not in lookup:
        next_index = fallback_index if fallback_index is not None else len(lookup) + 1
        lookup[speaker_identity] = f"SPEAKER_{next_index:02d}"

    return lookup[speaker_identity]


def run_quick_capture(
    job_id: str,
    audio_path: str = "",
    language_mode: str = "automatic",
    original_filename: str = ""
) -> dict:
    """
    High-accuracy Quick Capture execution flow.
    Flexibly handles positional parameters for both Background Workers and Direct Calls.
    """
    # Flexible fallback if audio_path is passed as the first positional argument
    if os.path.exists(job_id) and not audio_path:
        audio_path = job_id
        job_id = "quick_capture_job"

    print(f"⚡ Running Quick Capture Pipeline for Job [{job_id}]...")

    # 1. Speech Denoising
    processed_audio_path = denoise_audio(audio_path)

    # 2. WhisperX Speech-to-Text Transcription
    transcribe_fn = getattr(transcription_service, "transcribe_audio", getattr(transcription_service, "transcribe", None))
    if transcribe_fn is None:
        raise ImportError("Could not find a valid transcription function in backend.services.transcription_service")

    raw_result = transcribe_fn(
        audio_path=processed_audio_path,
        model_name=getattr(settings, "WHISPER_MODEL", "medium"),
        language_mode=language_mode,
    )

    detected_language = raw_result.get("language", "en") if isinstance(raw_result, dict) else "en"
    raw_segments = raw_result.get("segments", []) if isinstance(raw_result, dict) else []

    # 3. Precise Word-Level Phoneme Alignment
    align_fn = getattr(transcription_service, "align_whisper_output", None)
    if align_fn is not None:
        aligned_segments = align_fn(
            segments=raw_segments,
            audio_path=processed_audio_path,
            language_code=detected_language
        )
    else:
        aligned_segments = raw_segments

    # Format segments & build full text
    full_text_list = []
    formatted_segments = []
    speaker_lookup = {}

    for seg in aligned_segments:
        if isinstance(seg, dict):
            text_content = seg.get("text", "").strip()
            start_time = seg.get("start", 0.0)
            end_time = seg.get("end", 0.0)
        else:
            text_content = getattr(seg, "text", "").strip()
            start_time = getattr(seg, "start", 0.0)
            end_time = getattr(seg, "end", 0.0)

        if text_content:
            full_text_list.append(text_content)
            formatted_segments.append({
                "start": round(start_time, 2),
                "end": round(end_time, 2),
                "language": detected_language,
                "speaker": normalize_speaker_label("SPEAKER_01", speaker_lookup),
                "text": text_content
            })

    full_text = " ".join(full_text_list)

    # Clean up temporary denoised audio file if created
    if processed_audio_path != audio_path and os.path.exists(processed_audio_path):
        try:
            os.remove(processed_audio_path)
        except Exception:
            pass

    # 4. RAG Vector Indexing for Instant Q&A
    if full_text.strip() and create_vector_index is not None:
        try:
            # Uses transcript_text parameter explicitly to fix parameter mismatch
            create_vector_index(job_id=job_id, transcript_text=full_text)
        except TypeError:
            try:
                create_vector_index(job_id, full_text)
            except Exception as exc:
                print(f"⚠️ RAG indexing failed for [{job_id}]: {exc}")
        except Exception as exc:
            print(f"⚠️ RAG indexing skipped/failed for [{job_id}]: {exc}")

    return {
        "job_id": job_id,
        "filename": original_filename or os.path.basename(audio_path),
        "language": detected_language,
        "full_text": full_text,
        "segments": formatted_segments,
    }


def run_meeting_mode(audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Legacy compatibility wrapper for Meeting Mode pipeline execution.
    """
    if run_whisperx_meeting_mode is not None:
        temp_job_id = "sync_meeting"
        return run_whisperx_meeting_mode(temp_job_id, audio_path, language_mode)
    raise NotImplementedError("Meeting mode pipeline service is not available.")