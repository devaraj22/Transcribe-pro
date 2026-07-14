from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import settings
from .history.store import get_history
from .llm.client import llm_complete
from .llm.map_reduce import map_reduce_summary, map_reduce_action_items
from .pipeline import process_file
from .processing.jobs import complete_job, create_job, get_job_status, set_job_status
from .rag import retrieve
from .pdf_report import build_report
from .schemas import (
    ActionItemsResponse,
    AskRequest,
    AskResponse,
    EnhanceRequest,
    JobStatus,
    ProcessResponse,
    SummaryResponse,
    TitleResponse,
    TranslateRequest,
)
from .utils import ensure_storage_dirs, parse_language_mode, safe_save_upload

app = FastAPI(title="VoiceScribe AI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.BACKEND_URL == "*" else [settings.BACKEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_storage_dirs()


def process_long_job(job_id: str, upload_path: Path, language_mode: str, manual_language: Optional[str]) -> None:
    set_job_status(job_id, "processing", percent=10, current_step="preparing audio")
    result = process_file(upload_path, language_mode, manual_language, job_id=job_id)
    complete_job(job_id, result)


@app.post("/process", response_model=ProcessResponse)
async def process(upload_file: UploadFile = File(...), language_mode: str = Form(settings.LANGUAGE_MODE), manual_language: Optional[str] = Form(None), background_tasks: BackgroundTasks = None):
    if upload_file.spool_max_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the maximum supported size.")
    upload_path = settings.UPLOAD_DIR / upload_file.filename
    saved_path = safe_save_upload(upload_file, upload_path)
    language_mode = parse_language_mode(language_mode)
    if settings.LONG_RECORDING_THRESHOLD > 0:
        from .audio import probe_duration, prepare_audio_file
        audio_path = prepare_audio_file(saved_path)
        duration = probe_duration(audio_path)
        if duration > settings.LONG_RECORDING_THRESHOLD:
            job = create_job()
            set_job_status(job.job_id, "queued", percent=0, current_step="waiting")
            background_tasks.add_task(process_long_job, job.job_id, saved_path, language_mode, manual_language)
            return ProcessResponse(job_id=job.job_id, status="queued", detail="Long recording accepted; poll status.")

    result = process_file(saved_path, language_mode, manual_language)
    return ProcessResponse(job_id=None, status="complete", detail="Processed successfully.")


@app.get("/process/{job_id}/status", response_model=JobStatus)
def process_status(job_id: str):
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobStatus(job_id=job.job_id, status=job.status, percent_complete=job.percent_complete, current_step=job.current_step)


@app.get("/process/{job_id}/result")
def process_result(job_id: str):
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "complete":
        raise HTTPException(status_code=400, detail="Job is not complete yet.")
    return JSONResponse(content=job.result)


@app.post("/enhance/cleanup")
def enhance_cleanup(request: EnhanceRequest):
    prompt = f"Clean up the following transcript by restoring punctuation and removing filler words:\n\n{request.text}\n\nCleaned transcript:"
    return {"text": llm_complete(prompt, task="cleanup", max_tokens=1024)}


@app.post("/enhance/summarize", response_model=SummaryResponse)
def enhance_summarize(request: EnhanceRequest):
    summary = map_reduce_summary(request.text)
    return SummaryResponse(summary=summary)


@app.post("/enhance/action-items", response_model=ActionItemsResponse)
def enhance_action_items(request: EnhanceRequest):
    output = map_reduce_action_items(request.text)
    items = [line.strip() for line in output.splitlines() if line.strip()]
    return ActionItemsResponse(items=items)


@app.post("/enhance/translate")
def enhance_translate(request: TranslateRequest):
    prompt = f"Translate the following text to {request.target_language}, preserving meaning and speaker labels if present:\n\n{request.text}\n\nTranslated text:"
    return {"text": llm_complete(prompt, task="translate", max_tokens=1024)}


@app.post("/enhance/title", response_model=TitleResponse)
def enhance_title(request: EnhanceRequest):
    prompt = f"Generate a short, descriptive title for the following transcript or meeting notes:\n\n{request.text}\n\nTitle:"
    title = llm_complete(prompt, task="title", max_tokens=64)
    return TitleResponse(title=title)


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    answer, sources = retrieve(request.job_id, request.question)
    return AskResponse(answer=answer, sources=sources)


@app.get("/report/{job_id}")
def report(job_id: str):
    job = get_job_status(job_id)
    if not job or job.status != "complete":
        raise HTTPException(status_code=404, detail="Report not available until job completion.")
    transcript = job.result.get("transcript", "")
    summary = job.result.get("summary", "") or ""
    action_items = "\n".join(job.result.get("action_items", [])) if job.result.get("action_items") else ""
    output_path = settings.REPORT_DIR / f"report_{job_id}.pdf"
    build_report(job_id, transcript, summary, action_items, output_path)
    return FileResponse(str(output_path), media_type="application/pdf", filename=output_path.name)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/history")
def history():
    return get_history()
