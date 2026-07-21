from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.services.history_service import get_all_history, update_history_title # Added import

router = APIRouter()

class HistoryItemSchema(BaseModel):
    job_id: str
    title: str
    status: str
    timestamp: str

# Schema for the incoming title update request
class TitleUpdateSchema(BaseModel):
    new_title: str

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

# New PUT endpoint to handle the rename
@router.put("/{job_id}")
async def rename_job_title(job_id: str, payload: TitleUpdateSchema):
    """Updates the title of a specific history item."""
    success = update_history_title(job_id, payload.new_title)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or failed to save")
    return {"message": "Title updated successfully", "job_id": job_id, "new_title": payload.new_title}