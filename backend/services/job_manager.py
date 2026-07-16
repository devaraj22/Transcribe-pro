# In-memory database to store background job status and results
# In production, this would be replaced by Redis or a database.
_job_database = {}

def update_job_status(job_id: str, status: str, progress: float = 0.0, result: dict = None):
    """Updates the status and data of a background process."""
    _job_database[job_id] = {
        "status": status,
        "progress": progress,
        "result": result
    }

def get_job_status(job_id: str) -> dict:
    """Retrieves the current state of a background job."""
    return _job_database.get(job_id, {"status": "not_found", "progress": 0.0, "result": None})