from backend.app.modules.meeting_mode import background_jobs
from backend.services import job_manager


def test_job_state_is_shared_between_job_manager_and_background_jobs():
    job_id = "shared-job-state-test"

    job_manager.create_job(job_id)
    job_manager.update_job_status(job_id, status="processing", progress=42.0)

    status = background_jobs.get_job_status(job_id)

    assert status["status"] == "processing"
    assert status["progress"] == 42.0
