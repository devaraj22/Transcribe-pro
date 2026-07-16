from pydantic import BaseModel
from typing import List, Optional

# ==========================================
# 📥 Request Schemas (Data coming FROM React)
# ==========================================
# Note: File uploads use Form data, not JSON, so we don't need a strict Pydantic model 
# for the initial /process upload, but we will use them for enhancements and RAG later.

# ==========================================
# 📤 Response Schemas (Data going TO React)
# ==========================================
class Segment(BaseModel):
    start: float
    end: float
    language: str
    speaker: str
    text: str

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
    current_chunk: int
    total_chunks: int