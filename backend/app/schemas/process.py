from pydantic import BaseModel
from typing import List, Optional


# ==========================================
# 📤 Response Schemas (Data going TO React)
# ==========================================

class WordTiming(BaseModel):
    """Word-level timing entry — used for karaoke-style word highlighting in the frontend."""

    word: str
    start: float
    end: float
    score: Optional[float] = None


class Segment(BaseModel):
    """A single speaker turn or subtitle block."""

    start: float
    end: float
    language: str
    speaker: str
    text: str
    # Word-level timing for frontend word-highlighting; may be empty for faster-whisper backend
    words: Optional[List[WordTiming]] = None


class PipelineResult(BaseModel):
    job_id: str
    status: str = "complete"
    full_text: str
    segments: List[Segment]
    title: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[List[str]] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    current_chunk: Optional[int] = None
    total_chunks: Optional[int] = None