import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.services.ffmpeg_service import extract_audio, probe_duration
from backend.services.job_manager import create_job, update_job_status, get_job_status
from backend.app.modules.quick_capture.pipeline import run_quick_capture
from backend.services.background_worker import process_meeting_async
from backend.services.faiss_service import create_vector_index
from backend.services.history_service import append_to_history
from backend.services.whisper_service import (
    write_ass_subtitles,
    write_srt_subtitles,
    flush_models,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /process/  — upload & route
# ---------------------------------------------------------------------------

@router.post("/")
async def process_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language_mode: str = Form("automatic"),
):
    """
    Receives an audio/video file, standardises it via FFmpeg, checks its length,
    and routes it to either Quick Capture (sync) or Meeting Mode (async).
    """
    job_id = str(uuid.uuid4())
    create_job(job_id)
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "tmp"
    raw_file_path = os.path.join(settings.UPLOAD_DIR, f"raw_{job_id}.{file_extension}")

    # 1. Stream uploaded file to disk
    with open(raw_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. Transcode media to standard WAV and probe duration
        clean_audio_path = extract_audio(raw_file_path)
        duration = probe_duration(clean_audio_path)

        if os.path.exists(raw_file_path):
            os.remove(raw_file_path)

    except Exception as e:
        if os.path.exists(raw_file_path):
            os.remove(raw_file_path)
        return {"job_id": job_id, "status": "error", "message": f"Failed to process media file: {str(e)}"}

    # 3. Intelligent routing based on duration threshold
    if duration > settings.LONG_RECORDING_THRESHOLD:
        # 🚀 MEETING MODE (>10 min) → Background worker
        update_job_status(job_id, status="queued", progress=0.0)
        background_tasks.add_task(process_meeting_async, job_id, clean_audio_path, language_mode)
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Long recording detected. Processing asynchronously in the background.",
        }
    else:
        # ⚡ QUICK CAPTURE (<10 min) → Synchronous, immediate response
        try:
            update_job_status(job_id, status="processing", progress=0.5)
            result = run_quick_capture(clean_audio_path, language_mode)

            # Build RAG vector index for the transcript
            create_vector_index(job_id, result.get("full_text", ""))

            if os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)

            append_to_history(job_id=job_id, title=file.filename)
            update_job_status(
                job_id,
                status="complete",
                progress=1.0,
                result={"full_text": result["full_text"], "segments": result["segments"]},
            )
            return {
                "job_id": job_id,
                "status": "complete",
                "message": "Short recording processed successfully.",
                "full_text": result["full_text"],
                "segments": result["segments"],
            }
        except Exception as e:
            if os.path.exists(clean_audio_path):
                os.remove(clean_audio_path)
            update_job_status(job_id, status="failed", progress=1.0, error=str(e))
            return {"job_id": job_id, "status": "error", "message": f"AI Engine failed: {str(e)}"}


# ---------------------------------------------------------------------------
# GET /process/{job_id}  — poll job status
# ---------------------------------------------------------------------------

@router.get("/{job_id}")
async def check_job_status(job_id: str):
    """
    Frontend polls this endpoint to check background execution state.
    """
    job = get_job_status(job_id)

    if job.get("status") == "not_found":
        job = {"status": "queued", "progress": 0.0, "result": None}

    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "data": job["result"],  # full_text + segments when status == "complete"
    }


# ---------------------------------------------------------------------------
# GET /process/{job_id}/subtitle.{fmt}  — download subtitle file
# ---------------------------------------------------------------------------

@router.get("/{job_id}/subtitle.{fmt}")
async def download_subtitle(job_id: str, fmt: str):
    """
    Generate and download an ASS or SRT subtitle file for a completed job.

    - ``fmt``: ``ass`` or ``srt``

    The subtitle is built on demand from stored job segments.
    """
    fmt = fmt.lower()
    if fmt not in {"ass", "srt"}:
        raise HTTPException(status_code=400, detail="Unsupported subtitle format. Use 'ass' or 'srt'.")

    job = get_job_status(job_id)
    if job.get("status") != "complete":
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' is not complete (status: {job.get('status', 'unknown')}).",
        )

    result = job.get("result") or {}
    segments = result.get("segments", [])
    if not segments:
        raise HTTPException(status_code=404, detail="No segments found for this job.")

    subtitle_path = Path(settings.SUBTITLE_DIR) / f"{job_id}.{fmt}"

    if fmt == "ass":
        write_ass_subtitles(segments, subtitle_path)
    else:
        write_srt_subtitles(segments, subtitle_path)

    return FileResponse(
        path=str(subtitle_path),
        media_type="text/plain; charset=utf-8",
        filename=f"transcript_{job_id}.{fmt}",
    )


# ---------------------------------------------------------------------------
# POST /process/flush  — release GPU models
# ---------------------------------------------------------------------------

@router.post("/flush")
async def flush_gpu_models():
    """
    Release all loaded AI models from GPU/CPU memory.

    Useful on low-VRAM systems before starting a new heavy job.
    Equivalent to calling ``flush_models()`` in whisper_service.
    """
    flush_models()
    return {
        "status": "ok",
        "message": "All AI models have been released from memory.",
    }