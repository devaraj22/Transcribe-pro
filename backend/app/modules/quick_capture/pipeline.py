from backend.services.whisper_service import get_transcriber
from backend.services.transcription_service import normalize_speaker_label
from backend.app.core.config import settings


def run_quick_capture(audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Processes short audio clips synchronously.
    Skips speaker diarization to save computation time.
    """
    print(f"⚡ Running Quick Capture module for: {audio_path}")
    transcriber = get_transcriber()

    lang = None if language_mode == "automatic" else language_mode
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