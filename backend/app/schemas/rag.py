from pydantic import BaseModel
from typing import List

class RAGRequest(BaseModel):
    job_id: str
    question: str

class RAGResponse(BaseModel):
    answer: str
    sources: List[str]  # We send back the exact quotes so the user knows the AI isn't hallucinating