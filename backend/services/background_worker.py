import os
from backend.app.modules.meeting_mode.background_jobs import update_job_status
from backend.app.modules.meeting_mode.pipeline import run_meeting_mode
from backend.app.modules.quick_capture.pipeline import run_quick_capture
from backend.services.faiss_service import create_vector_index
from backend.services.history_service import append_to_history


async def process_quick_capture_async(job_id: str, audio_path: str, language_mode: str, title: str):
    """
    Background worker task for short recordings. Quick Capture used to run
    synchronously inside the POST /process/ request/response cycle — for any
    file whose model download/transcription time exceeded a reverse-proxy's
    request timeout (e.g. Lightning AI Studio's public URL proxy), that
    produced a bare 502 with the backend itself still healthy. Running it as
    a background task, the same way Meeting Mode already works, avoids that
    entire class of failure regardless of file length or cold-start time.
    """
    try:
        print(f"👷 Background Worker picked up Quick Capture Job [{job_id}]")
        update_job_status(job_id, status="processing", progress=10.0)

        result = run_quick_capture(audio_path, language_mode)

        print("⏳ Building local vector index for RAG chat...")
        create_vector_index(job_id, result.get("full_text", ""))

        append_to_history(job_id=job_id, title=title)

        update_job_status(
            job_id,
            status="complete",
            progress=100.0,
            result={"full_text": result["full_text"], "segments": result["segments"]},
        )
        print(f"✅ Background Worker completed Quick Capture Job [{job_id}] successfully.")

    except Exception as e:
        print(f"❌ Background Worker failed on Quick Capture Job [{job_id}]: {str(e)}")
        update_job_status(job_id, status="error", progress=100.0, error=str(e))

    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


async def process_meeting_async(job_id: str, audio_path: str, language_mode: str):
    """
    Background worker task that runs the expensive Pyannote + WhisperX steps
    without blocking the user's HTTP request thread.
    """
    try:
        # 1. Update status to processing
        print(f"👷 Background Worker picked up Job [{job_id}]")
        update_job_status(job_id, status="processing", progress=10.0)

        # 2. Run the heavy AI pipeline (Diarization + Transcription)
        result = run_meeting_mode(job_id, audio_path, language_mode)

        # 3. Build local vector index for RAG chat
        print("⏳ Building local vector index for RAG chat...")
        create_vector_index(job_id, result["full_text"])

        # 4. Log to history after worker success
        append_to_history(job_id=job_id, title="Meeting Audio Track Analysis")

        # 5. Mark as complete and store the structured results
        update_job_status(job_id, status="complete", progress=100.0, result=result)
        print(f"✅ Background Worker completed Job [{job_id}] successfully.")

    except Exception as e:
        print(f"❌ Background Worker failed on Job [{job_id}]: {str(e)}")
        # NOTE: status must be "error" (not "failed") to match what the frontend's
        # useJobPolling checks for, and the message belongs in the `error` field,
        # not `result` (result is expected to hold {full_text, segments}).
        update_job_status(job_id, status="error", progress=100.0, error=str(e))

    finally:
        # 6. Cleanup: Remove the audio file from disk to save server storage
        if os.path.exists(audio_path):
            os.remove(audio_path)