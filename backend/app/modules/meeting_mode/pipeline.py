import gc
import torch
from typing import List, Dict, Any
import whisperx

from backend.app.core.config import settings
from backend.app.modules.meeting_mode.background_jobs import update_job_status
from backend.app.modules.quick_capture.pipeline import run_quick_capture
from backend.services.whisper_service import (
    get_transcriber,
    get_aligner,
    get_diarizer,
    release_transcriber,
    release_aligner,
    release_diarizer,
)


def format_speaker_transcript(word_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    full_text = []
    segments = []
    speaker_lookup = {}

    for idx, word in enumerate(word_segments):
        speaker = word.get("speaker", "SPEAKER_01")
        spoken_text = word.get("word", "").strip()
        if not spoken_text:
            continue

        if speaker not in speaker_lookup:
            speaker_lookup[speaker] = f"Speaker {len(speaker_lookup) + 1}"

        speaker_label = speaker_lookup[speaker]
        segments.append({
            "start": round(word.get("start", 0.0), 2),
            "end": round(word.get("end", 0.0), 2),
            "language": word.get("language", "unknown"),
            "speaker": speaker_label,
            "text": spoken_text,
        })
        full_text.append(f"{speaker_label}: {spoken_text}")

    return {
        "full_text": "\n".join(full_text),
        "segments": segments,
    }


def run_meeting_mode(job_id: str, audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Runs WhisperX end-to-end for long recordings, including transcription,
    alignment, diarization, and speaker assignment.
    """
    print(f"🚀 Running Meeting Mode module for: {audio_path}")
    update_job_status(job_id, status="processing", progress=5.0)

    language = None if language_mode == "automatic" else language_mode

    # 1. Transcription
    print("⏳ Running WhisperX transcription...")
    transcriber = get_transcriber()
    transcription_result = transcriber.transcribe(audio_path, language=language)
    update_job_status(job_id, progress=25.0)
    release_transcriber()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 2. Alignment
    print("⏳ Running WhisperX alignment...")
    aligner = get_aligner()
    aligned_result = aligner.align(audio_path, transcription_result)
    update_job_status(job_id, progress=50.0)
    release_aligner()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 3. Diarization
    print("⏳ Running WhisperX diarization...")
    diarizer = get_diarizer()
    diarization_result = diarizer(audio_path)
    update_job_status(job_id, progress=75.0)
    release_diarizer()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 4. Speaker assignment
    print("⏳ Assigning speakers to word segments...")
    speaker_word_segments = whisperx.assign_word_speakers(
        aligned_result,
        diarization_result,
    )

    final_result = format_speaker_transcript(speaker_word_segments)
    update_job_status(job_id, progress=100.0)

    return final_result
