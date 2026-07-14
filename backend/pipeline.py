import json
from pathlib import Path
from typing import Dict, List, Optional

from .audio import prepare_audio_file, probe_duration
from .config import settings
from .history.store import append_history
from .llm.map_reduce import map_reduce_summary, map_reduce_action_items
from .processing.diarize import diarize_audio
from .processing.transcribe import transcribe_segments
from .processing.chunking import chunk_segments
from .rag import build_index
from .schemas import Segment


def merge_transcript_segments(transcript_segments: List[Segment], diarization: List[Dict]) -> List[Dict]:
    merged = []
    for segment in transcript_segments:
        mid = (segment.start + segment.end) / 2
        speaker = None
        for turn in diarization:
            if turn["start"] <= mid <= turn["end"]:
                speaker = turn["speaker"]
                break
        merged.append(
            {
                "start": segment.start,
                "end": segment.end,
                "speaker": speaker or "Speaker 1",
                "language": segment.language,
                "text": segment.text,
            }
        )
    return merged


def process_file(upload_path: Path, language_mode: str, manual_language: Optional[str] = None, job_id: Optional[str] = None) -> Dict:
    audio_path = prepare_audio_file(upload_path)
    duration = probe_duration(audio_path)
    raw_segments = transcribe_segments(audio_path, manual_language if language_mode == "manual" else None)
    diarization = diarize_audio(audio_path)
    merged_segments = merge_transcript_segments(raw_segments, diarization)
    full_text = "\n".join([f"{seg['speaker']}: {seg['text']}" for seg in merged_segments])
    chunks = chunk_segments([Segment(**seg) for seg in merged_segments], settings.CHUNK_LENGTH)
    if job_id:
        build_index(chunks, job_id)
    else:
        build_index(chunks, "inline")
    title = None
    summary = None
    action_items = None
    append_history({
        "title": title,
        "timestamp": None,
        "duration_seconds": duration,
        "languages": list({seg["language"] for seg in merged_segments if seg.get("language")}),
        "transcript": full_text,
        "segments": merged_segments,
    })
    return {
        "transcript": full_text,
        "segments": merged_segments,
        "languages": list({seg["language"] for seg in merged_segments if seg.get("language")}),
        "duration_seconds": duration,
        "title": title,
        "summary": summary,
        "action_items": action_items,
    }
