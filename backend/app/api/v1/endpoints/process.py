import os
import uuid
import shutil
from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks

from backend.app.core.config import settings
from backend.services.ffmpeg_service import extract_audio, probe_duration
from backend.services.job_manager import create_job, update_job_status, get_job_status
from backend.app.modules.quick_capture.pipeline import run_quick_capture  # noqa: F401 (kept for direct/test use)
from backend.services.background_worker import process_meeting_async, process_quick_capture_async
from backend.services.faiss_service import create_vector_index
from backend.services.history_service import append_to_history


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
    # UploadFile.filename is typed as `str | None` — guard it once here so the
    # rest of the function can safely treat it as a plain str.
    original_filename: str = file.filename or f"upload_{job_id}"
    file_extension = original_filename.split(".")[-1] if "." in original_filename else "tmp"
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
        # Persist the failure onto the job itself — without this, the job stays
        # stuck at "queued" forever and the frontend polls it in an infinite loop.
        update_job_status(job_id, status="error", progress=100.0, error=str(e))
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
        # ⚡ QUICK CAPTURE (Under 10 mins) -> Run in the background too.
        # NOTE: this used to run synchronously inside this request/response
        # cycle "for instant user feedback" — but that meant the entire
        # download-model + transcribe + align pipeline had to complete before
        # a reverse-proxy's request timeout (e.g. Lightning AI Studio's public
        # URL proxy) expired, or the client got a bare 502 even though the
        # backend was healthy and still working. Returning immediately and
        # polling (the frontend already supports this) fixes that regardless
        # of file length or model cold-start time.
        update_job_status(job_id, status="queued", progress=0.0)

        background_tasks.add_task(
            process_quick_capture_async, job_id, clean_audio_path, language_mode, original_filename
        )

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Processing in the background."
        }


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
        "data": job["result"],  # Contains full_text and segments when status is "complete"
        "error": job.get("error")  # Contains the real failure reason when status is "error"
    }