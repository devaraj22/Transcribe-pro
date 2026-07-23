import os
import shutil
import uuid
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from backend.app.core.config import settings
from backend.app.modules.quick_capture.pipeline import run_quick_capture  # noqa: F401
from backend.services.background_worker import (
    process_meeting_async,
    process_quick_capture_async,
)
from backend.services.ffmpeg_service import extract_audio, probe_duration
from backend.services.job_manager import create_job, get_job_status, update_job_status

router = APIRouter()

ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "webm", "ogg", "flac", "aac", "mp4"}


@router.post("/")
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language_mode: str = Form("automatic"),
):
    """
    Receives an audio/video file, standardizes it via FFmpeg, checks its length, 
    and routes it to either Quick Capture or Meeting Mode.
    """
    job_id = str(uuid.uuid4())
    create_job(job_id)

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # 1. Determine safe file extension
    original_filename: str = file.filename or f"recording_{job_id}.wav"
    ext = original_filename.split(".")[-1].lower() if "." in original_filename else "wav"
    if ext not in ALLOWED_EXTENSIONS or ext == "blob":
        ext = "wav"

    raw_file_path = os.path.join(settings.UPLOAD_DIR, f"raw_{job_id}.{ext}")

    # Stream uploaded file onto disk
    try:
        with open(raw_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        update_job_status(job_id, status="error", progress=100.0, error=str(exc))
        return {"job_id": job_id, "status": "error", "message": f"Failed to save uploaded file: {str(exc)}"}

    try:
        # 2. Transcode media to standard WAV format and probe runtime duration
        clean_audio_path = extract_audio(raw_file_path)
        duration = probe_duration(clean_audio_path)

        # Cleanup raw uploaded file after conversion
        if os.path.exists(raw_file_path):
            os.remove(raw_file_path)

    except Exception as e:
        if os.path.exists(raw_file_path):
            os.remove(raw_file_path)
        update_job_status(job_id, status="error", progress=100.0, error=str(e))
        return {"job_id": job_id, "status": "error", "message": f"Failed to process media file: {str(e)}"}

    # 3. Intelligent Routing with explicit keyword arguments to avoid positional argument bugs
    if duration > settings.LONG_RECORDING_THRESHOLD:
        update_job_status(job_id, status="queued", progress=0.0)
        background_tasks.add_task(
            process_meeting_async,
            job_id=job_id,
            audio_path=clean_audio_path,
            language_mode=language_mode,
        )
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Long recording detected. Processing asynchronously in the background.",
        }
    else:
        update_job_status(job_id, status="queued", progress=0.0)
        background_tasks.add_task(
            process_quick_capture_async,
            job_id=job_id,
            audio_path=clean_audio_path,
            language_mode=language_mode,
            title=original_filename,  # Fixed: changed parameter name from original_filename to title
        )
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Processing in the background.",
        }


@router.get("/{job_id}")
async def check_job_status(job_id: str):
    """
    Frontend intervals poll this endpoint to verify background execution states.
    """
    job = get_job_status(job_id)

    if not job or job.get("status") == "not_found":
        job = {
            "status": "queued",
            "progress": 0.0,
            "result": None,
        }

    return {
        "job_id": job_id,
        "status": job.get("status", "queued"),
        "progress": job.get("progress", 0.0),
        "data": job.get("result"),  # Contains full_text and segments when status is "complete"
        "error": job.get("error"),
    }