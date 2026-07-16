import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

# Import your PDF generation service
from backend.services.reportlab_service import generate_pdf_report

router = APIRouter()

# --- Pydantic Schema for Validation ---
class ReportRequest(BaseModel):
    title: Optional[str] = "VoiceScribe Meeting Report"
    summary: Optional[str] = None
    action_items: Optional[List[str]] = []
    full_text: str

# --- Endpoints ---
@router.post("/download")
async def download_report(request: ReportRequest):
    """
    Receives meeting data, compiles it into a PDF, and returns the file 
    to be downloaded by the client.
    """
    try:
        # Generate the PDF and get the file path
        pdf_path = generate_pdf_report(
            title=request.title,
            summary=request.summary,
            action_items=request.action_items,
            full_text=request.full_text
        )
        
        # Verify the file was created
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="Failed to generate PDF file.")
            
        # Return the file as a downloadable response using FastAPI's FileResponse
        return FileResponse(
            path=pdf_path, 
            filename=os.path.basename(pdf_path),
            media_type='application/pdf'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))