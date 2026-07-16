from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

# Import your LLM service functions (adjust the import path if needed)
from backend.services.ollama_service import generate_summary, extract_action_items

router = APIRouter()

# --- Pydantic Schemas for Validation ---
class EnhanceRequest(BaseModel):
    text: str

class SummaryResponse(BaseModel):
    summary: str

class ActionItemsResponse(BaseModel):
    action_items: List[str]

# --- Endpoints ---
@router.post("/summarize", response_model=SummaryResponse)
async def summarize_text(request: EnhanceRequest):
    """
    Takes a raw transcript and returns a concise AI-generated summary.
    """
    try:
        summary_text, is_error = await generate_summary(request.text)
        
        if is_error:
            # Return error message - client can check if it starts with "Error:"
            raise HTTPException(status_code=503, detail=summary_text)
        
        return {"summary": summary_text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/action-items", response_model=ActionItemsResponse)
async def get_action_items(request: EnhanceRequest):
    """
    Takes a raw transcript and extracts a bulleted list of tasks/action items.
    """
    try:
        items, is_error = await extract_action_items(request.text)
        
        if is_error:
            # Return error message wrapped in action items list
            raise HTTPException(status_code=503, detail="Unable to extract action items. Ollama service may not be available.")
        
        return {"action_items": items}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))