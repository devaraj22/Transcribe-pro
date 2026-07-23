"""
background_worker.py
====================
Background execution handlers for Quick Capture and Meeting Mode tasks.
"""

import os
from backend.app.modules.meeting_mode.background_jobs import update_job_status
from backend.app.modules.meeting_mode.pipeline import run_meeting_mode
from backend.app.modules.quick_capture.pipeline import run_quick_capture
from backend.services.faiss_service import create_vector_index
from backend.services.history_service import append_to_history


async def process_quick_capture_async(
    job_id: str,
    audio_path: str,
    language_mode: str = "automatic",
    title: str = ""
):
    """
    Background worker task for short recordings.
    """
    try:
        print(f"👷 Background Worker picked up Quick Capture Job [{job_id}]")
        update_job_status(job_id, status="processing", progress=10.0)

        # Explicit keyword arguments with job_id included
        result = run_quick_capture(
            job_id=job_id,
            audio_path=audio_path,
            language_mode=language_mode
        )

        print("⏳ Building local vector index for RAG chat...")
        full_text = result.get("full_text", "")
        create_vector_index(job_id, full_text)

        append_to_history(job_id=job_id, title=title or "Quick Capture Recording")

        update_job_status(
            job_id,
            status="complete",
            progress=100.0,
            result={"full_text": full_text, "segments": result.get("segments", [])},
        )
        print(f"✅ Background Worker completed Quick Capture Job [{job_id}] successfully.")

    except Exception as e:
        print(f"❌ Background Worker failed on Quick Capture Job [{job_id}]: {str(e)}")
        update_job_status(job_id, status="error", progress=100.0, error=str(e))

    finally:
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as clean_err:
                print(f"⚠️ Failed to remove temporary audio file '{audio_path}': {clean_err}")


async def process_meeting_async(
    job_id: str,
    audio_path: str,
    language_mode: str = "automatic"
):
    """
    Background worker task for long meeting recordings (Diarization + Transcription).
    """
    try:
        print(f"👷 Background Worker picked up Job [{job_id}]")
        update_job_status(job_id, status="processing", progress=10.0)

        # Run heavy AI pipeline
        result = run_meeting_mode(
            job_id=job_id,
            audio_path=audio_path,
            language_mode=language_mode
        )

        print("⏳ Building local vector index for RAG chat...")
        create_vector_index(job_id, result.get("full_text", ""))

        append_to_history(job_id=job_id, title="Meeting Audio Track Analysis")

        update_job_status(job_id, status="complete", progress=100.0, result=result)
        print(f"✅ Background Worker completed Job [{job_id}] successfully.")

    except Exception as e:
        print(f"❌ Background Worker failed on Job [{job_id}]: {str(e)}")
        update_job_status(job_id, status="error", progress=100.0, error=str(e))

    finally:
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as clean_err:
                print(f"⚠️ Failed to remove temporary audio file '{audio_path}': {clean_err}")