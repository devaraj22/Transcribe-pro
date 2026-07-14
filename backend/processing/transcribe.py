from pathlib import Path
from typing import Dict, List, Optional

from faster_whisper import WhisperModel

from ..config import settings
from ..schemas import Segment

_model = None


def get_whisper_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(settings.WHISPER_MODEL, device="cpu")
    return _model


def transcribe_segments(audio_path: Path, manual_language: Optional[str] = None) -> List[Segment]:
    model = get_whisper_model()
    language = manual_language if manual_language else None
    result = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        vad_filter=False,
        beam_size=5,
        best_of=1,
        temperature=0.0,
    )
    segments: List[Segment] = []
    detected_language = getattr(result, "language", None)
    for item in result["segments"]:
        segments.append(
            Segment(
                start=float(item["start"]),
                end=float(item["end"]),
                language=manual_language or detected_language,
                text=item["text"].strip(),
            )
        )
    return segments
