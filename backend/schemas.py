from typing import List, Optional
from pydantic import BaseModel

class Segment(BaseModel):
    start: float
    end: float
    speaker: Optional[str] = None
    language: Optional[str] = None
    text: str

class TranscriptResult(BaseModel):
    job_id: Optional[str] = None
    status: str
    transcript: Optional[str] = None
    segments: Optional[List[Segment]] = None
    languages: Optional[List[str]] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    action_items: Optional[List[str]] = None
    duration_seconds: Optional[float] = None

class ProcessResponse(BaseModel):
    job_id: Optional[str]
    status: str
    detail: Optional[str] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    percent_complete: float
    current_step: Optional[str] = None

class EnhanceRequest(BaseModel):
    text: str

class SummaryResponse(BaseModel):
    summary: str

class ActionItemsResponse(BaseModel):
    items: List[str]

class TranslateRequest(BaseModel):
    text: str
    target_language: str

class TitleResponse(BaseModel):
    title: str

class AskRequest(BaseModel):
    job_id: str
    question: str

class AskResponse(BaseModel):
    answer: str
    sources: List[str]
