# pyright: reportAttributeAccessIssue=false
#
# This file builds fake modules with `types.ModuleType(...)` and assigns
# arbitrary attributes onto them so heavyweight real dependencies (fastapi,
# whisperx, faiss, etc.) don't need to be installed just to import and test
# the status endpoint in isolation. Pyright can't statically verify dynamic
# attribute assignment on ModuleType, but the pattern is intentional and
# correct at runtime — hence the blanket suppression above rather than
# per-line `# type: ignore` comments on every stub assignment.

import sys
import types

import pytest


# Stub heavyweight modules so we can import the status endpoint in isolation.
fastapi_stub = types.ModuleType("fastapi")


class _DummyAPIRouter:
    def __init__(self, *args, **kwargs):
        pass

    def post(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

    def get(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator


class _BackgroundTasks:
    pass


fastapi_stub.APIRouter = _DummyAPIRouter
fastapi_stub.File = lambda *args, **kwargs: None
fastapi_stub.UploadFile = object
fastapi_stub.Form = lambda *args, **kwargs: None
fastapi_stub.BackgroundTasks = _BackgroundTasks
sys.modules.setdefault("fastapi", fastapi_stub)

quick_capture_stub = types.ModuleType("backend.app.modules.quick_capture.pipeline")
quick_capture_stub.run_quick_capture = lambda *args, **kwargs: {"full_text": "", "segments": []}
sys.modules.setdefault("backend.app.modules.quick_capture.pipeline", quick_capture_stub)

ffmpeg_stub = types.ModuleType("backend.services.ffmpeg_service")
ffmpeg_stub.extract_audio = lambda *args, **kwargs: ""
ffmpeg_stub.probe_duration = lambda *args, **kwargs: 0
sys.modules.setdefault("backend.services.ffmpeg_service", ffmpeg_stub)

background_worker_stub = types.ModuleType("backend.services.background_worker")
background_worker_stub.process_meeting_async = lambda *args, **kwargs: None
background_worker_stub.process_quick_capture_async = lambda *args, **kwargs: None
sys.modules.setdefault("backend.services.background_worker", background_worker_stub)

faiss_service_stub = types.ModuleType("backend.services.faiss_service")
faiss_service_stub.create_vector_index = lambda *args, **kwargs: None
sys.modules.setdefault("backend.services.faiss_service", faiss_service_stub)

from backend.app.api.v1.endpoints.process import check_job_status
from backend.app.modules.meeting_mode import background_jobs


@pytest.mark.asyncio
async def test_check_job_status_returns_queued_placeholder_for_unknown_job():
    response = await check_job_status("missing-job")

    assert response["job_id"] == "missing-job"
    assert response["status"] == "queued"
    assert response["progress"] == 0.0


def test_get_job_status_returns_queued_placeholder_for_unknown_job():
    job = background_jobs.get_job_status("missing-job")

    assert job["status"] == "queued"
    assert job["progress"] == 0.0