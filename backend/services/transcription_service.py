import re
from typing import Optional

from backend.app.modules.meeting_mode.pipeline import run_meeting_mode as run_whisperx_meeting_mode
from backend.services.whisper_service import get_transcriber
from backend.app.core.config import settings


def normalize_speaker_label(
    raw_label: str | None,
    speaker_lookup: dict | None = None,
    fallback_index: Optional[int] = None,
) -> str:
    """
    Convert diarization labels like SPEAKER_00, speaker-1, or UNKNOWN into stable
    labels such as SPEAKER_01, SPEAKER_02, etc.
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


def run_quick_capture(audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Processes short audio clips (under 10 mins) quickly.
    Skips speaker diarization to save computation time.
    """
    print(f"⚡ Running Quick Capture pipeline for: {audio_path}")
    transcriber = get_transcriber()

    # Configure language if explicitly forced
    lang = None if language_mode == "automatic" else language_mode

    # Transcribe the audio file with VAD enabled for cleaner speech boundaries
    segments, info = transcriber.transcribe(
        audio_path,
        language=lang,
    )

    full_text = []
    formatted_segments = []
    speaker_lookup = {}

    for seg in segments:
        full_text.append(seg.text)
        formatted_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "language": info.language,
            "speaker": normalize_speaker_label("SPEAKER_01", speaker_lookup),
            "text": seg.text.strip()
        })

    return {
        "full_text": " ".join(full_text),
        "segments": formatted_segments
    }


def run_meeting_mode(audio_path: str, language_mode: str = "automatic") -> dict:
    # Legacy compatibility wrapper: background worker should call meeting pipeline with a real job_id.
    # Here we create a temporary job id for synchronous usage.
    temp_job_id = "sync_meeting"
    return run_whisperx_meeting_mode(temp_job_id, audio_path, language_mode)