from pathlib import Path
from typing import List, Dict

from pyannote.audio import Pipeline

from ..config import settings


_diary_pipeline = None


def get_diarization_pipeline() -> Pipeline:
    global _diary_pipeline
    if _diary_pipeline is None:
        _diary_pipeline = Pipeline.from_pretrained(settings.DIARIZATION_MODEL)
    return _diary_pipeline


def diarize_audio(audio_path: Path) -> List[Dict]:
    pipeline = get_diarization_pipeline()
    diarization = pipeline(str(audio_path))
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            {
                "start": float(turn.start),
                "end": float(turn.end),
                "speaker": str(speaker),
            }
        )
    if not segments:
        segments.append({"start": 0.0, "end": float(audio_path.stat().st_size), "speaker": "Speaker 1"})
    return segments
