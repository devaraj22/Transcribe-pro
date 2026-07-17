import os
from backend.app.modules.meeting_mode.background_jobs import update_job_status
from backend.app.modules.meeting_mode.pipeline import run_meeting_mode
from backend.services.faiss_service import create_vector_index
from backend.services.history_service import append_to_history

async def process_meeting_async(job_id: str, audio_path: str, language_mode: str):
    """
    Background worker task that runs the expensive Pyannote + Whisper steps
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
        update_job_status(job_id, status="failed", progress=0.0, result={"error": str(e)})
        
    finally:
        # 6. Cleanup: Remove the massive wav file from disk to save server storage
        if os.path.exists(audio_path):
            os.remove(audio_path)