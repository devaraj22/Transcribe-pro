import time
from typing import Dict, Any, Optional

# In-memory database to track asynchronous background tasks.
# Note: In a production environment, this gets swapped for Redis or PostgreSQL.
_active_jobs: Dict[str, Dict[str, Any]] = {}

def create_job(job_id: str) -> None:
    """Initializes a new background job in the queue."""
    _active_jobs[job_id] = {
        "status": "queued",
        "progress": 0.0,
        "result": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time()
    }

def update_job_status(
    job_id: str, 
    status: Optional[str] = None,  # Made optional!
    progress: Optional[float] = None, 
    result: Optional[dict] = None,
    error: Optional[str] = None
) -> None:
    """Updates the state, progress, or results of an active job."""
    if job_id not in _active_jobs:
        # If the job isn't found, auto-create it to prevent crash loops
        create_job(job_id)

    # Only update status if one was provided
    if status is not None:
        _active_jobs[job_id]["status"] = status
        
    _active_jobs[job_id]["updated_at"] = time.time()
    
    if progress is not None:
        _active_jobs[job_id]["progress"] = progress
        
    if result is not None:
        _active_jobs[job_id]["result"] = result
        
    if error is not None:
        _active_jobs[job_id]["error"] = error

def get_job_status(job_id: str) -> dict:
    """Retrieves the current state of a background job for the frontend polling."""
    if job_id not in _active_jobs:
        create_job(job_id)
        return _active_jobs[job_id]
        
    return _active_jobs[job_id]

def clear_job(job_id: str) -> None:
    """Removes a job from memory once the client has successfully retrieved it, preventing memory leaks."""
    if job_id in _active_jobs:
        del _active_jobs[job_id]