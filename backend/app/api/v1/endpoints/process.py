import os
import uuid
import shutil
from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks

from backend.app.core.config import settings
from backend.services.ffmpeg_service import extract_audio, probe_duration
from backend.services.job_manager import create_job, update_job_status, get_job_status
from backend.app.modules.quick_capture.pipeline import run_quick_capture
from backend.services.background_worker import process_meeting_async
from backend.services.faiss_service import create_vector_index
from backend.services.history_service import append_to_history
from backend.services.background_worker import process_meeting_async


router = APIRouter()

@router.post("/")
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language_mode: str = Form("automatic")
):
    """
    Receives an audio/video file, standardizes it via FFmpeg, checks its length, 
    and routes it to either Quick Capture (sync) or Meeting Mode (async).
    """
    job_id = str(uuid.uuid4())
    create_job(job_id)
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "tmp"
    raw_file_path = os.path.join(settings.UPLOAD_DIR, f"raw_{job_id}.{file_extension}")
    
    # 1. Stream uploaded file onto disk
    with open(raw_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 2. Transcode media to standard format and probe runtime duration
        clean_audio_path = extract_audio(raw_file_path)
        duration = probe_duration(clean_audio_path)
        
        if os.path.exists(raw_file_path):
            os.remove(raw_file_path)
            
    except Exception as e:
        if os.path.exists(raw_file_path):
            os.remove(raw_file_path)
        return {"job_id": job_id, "status": "error", "message": f"Failed to process media file: {str(e)}"}
    
    # 3. Intelligent Routing based on runtime threshold
    if duration > settings.LONG_RECORDING_THRESHOLD:
        # 🚀 MEETING MODE (Over 10 mins) -> Route to Background Worker Threads
        update_job_status(job_id, status="queued", progress=0.0)
        
        background_tasks.add_task(process_meeting_async, job_id, clean_audio_path, language_mode)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Long recording detected. Processing asynchronously in the background."
        }
    else:
        # ⚡ QUICK CAPTURE (Under 10 mins) -> Execute synchronously for instant user feedback
        try:
            update_job_status(job_id, status="processing", progress=0.5)
            result = run_quick_capture(clean_audio_path, language_mode)

            # Build the RAG vector index for the newly transcribed content
            create_vector_index(job_id, result.get("full_text", ""))
            
            if os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)
                
            # Log the successful transaction inside your 5-item log ceiling
            append_to_history(job_id=job_id, title=file.filename)
            update_job_status(
                job_id, 
                status="complete", 
                progress=1.0, 
                result={"full_text": result["full_text"], "segments": result["segments"]}
            )
            return {
                "job_id": job_id,
                "status": "complete",
                "message": "Short recording processed successfully.",
                "full_text": result["full_text"],
                "segments": result["segments"]
            }
        except Exception as e:
            if os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)
            update_job_status(job_id, status="failed", progress=1.0, error=str(e))
            return {"job_id": job_id, "status": "error", "message": f"AI Engine failed: {str(e)}"}


@router.get("/{job_id}")
async def check_job_status(job_id: str):
    """
    Frontend intervals poll this endpoint to verify background execution states.
    """
    job = get_job_status(job_id)

    if job.get("status") == "not_found":
        job = {
            "status": "queued",
            "progress": 0.0,
            "result": None,
        }

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "data": job["result"]  # Contains full_text and segments when status is "complete"
    }