from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.services.history_service import get_all_history

router = APIRouter()

class HistoryItemSchema(BaseModel):
    job_id: str
    title: str
    status: str
    timestamp: str

@router.get("/", response_model=List[HistoryItemSchema])
async def fetch_job_history():
    """
    Fetches the last 5 successful runs stored inside history.json
    to populate the frontend HistoryPanel.
    """
    try:
        logs = get_all_history()
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")