import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class JobState:
    job_id: str
    status: str = "queued"
    percent_complete: float = 0.0
    current_step: Optional[str] = None
    result: Optional[Dict] = field(default_factory=dict)

_job_store: Dict[str, JobState] = {}
_lock = threading.Lock()


def create_job() -> JobState:
    job_id = str(uuid.uuid4())
    job = JobState(job_id=job_id)
    with _lock:
        _job_store[job_id] = job
    return job


def get_job_status(job_id: str) -> Optional[JobState]:
    with _lock:
        return _job_store.get(job_id)


def set_job_status(job_id: str, status: str, percent: float = 0.0, current_step: Optional[str] = None) -> None:
    with _lock:
        job = _job_store.get(job_id)
        if job:
            job.status = status
            job.percent_complete = percent
            job.current_step = current_step


def complete_job(job_id: str, result: Dict) -> None:
    with _lock:
        job = _job_store.get(job_id)
        if job:
            job.status = "complete"
            job.percent_complete = 100.0
            job.result = result
