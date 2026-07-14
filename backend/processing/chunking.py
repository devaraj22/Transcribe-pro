from typing import List, Dict

from ..schemas import Segment


def chunk_segments(segments: List[Segment], chunk_duration: int) -> List[Dict]:
    chunks = []
    current = {
        "start": 0.0,
        "end": 0.0,
        "text": "",
        "segments": [],
    }
    for segment in segments:
        if current["text"] and segment.end - current["start"] > chunk_duration:
            chunks.append(current)
            current = {"start": segment.start, "end": segment.end, "text": segment.text, "segments": [segment.dict()]}
            continue
        if not current["text"]:
            current["start"] = segment.start
        current["end"] = segment.end
        current["text"] += (" " if current["text"] else "") + segment.text
        current["segments"].append(segment.dict())
    if current["text"]:
        chunks.append(current)
    return chunks
