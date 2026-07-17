"""Compatibility helpers for background job state.

This module intentionally re-exports the canonical in-memory job-state functions
from the meeting-mode background jobs module so that all API endpoints, the
worker, and any older imports share the same mutable storage.
"""

from backend.app.modules.meeting_mode.background_jobs import (
    clear_job,
    create_job,
    get_job_status,
    update_job_status,
)

__all__ = ["create_job", "update_job_status", "get_job_status", "clear_job"]