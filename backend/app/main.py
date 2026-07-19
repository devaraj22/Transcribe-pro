import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.app.core.config import settings
from backend.app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager runs before the server starts accepting requests
    and cleans up when the server stops.
    """
    print("🚀 Booting up VoiceScribe AI...")
    print(f"📁 Storage directories verified at: {settings.STORAGE_DIR}")
    print(f"🧠 Whisper model config set to '{getattr(settings, 'WHISPER_MODEL', 'Unknown')}' ({getattr(settings, 'WHISPER_BACKEND', 'Unknown')} backend).")
    
    if getattr(settings, "HF_TOKEN", None):
        print("✅ HF_TOKEN is configured for diarization.")
    else:
        print("⚠️ HF_TOKEN is not configured; diarization may be unavailable.")

    # Warm the transcription model now, at startup, rather than lazily on the
    # first request. Quick Capture runs synchronously inside the HTTP
    # request/response cycle — if the first request also has to pay for
    # downloading + loading the Whisper/VAD/alignment models, that can easily
    # exceed a reverse-proxy's request timeout (e.g. Lightning AI Studio's
    # public URL proxy), producing a bare 502 even though the backend itself
    # is healthy and still working. Loading here means that cost is paid once,
    # during startup, before any request is accepted.
    try:
        from backend.services.whisper_service import get_transcriber
        print("⏳ Warming transcription model (this may take a while on first run)...")
        get_transcriber()
        print("✅ Transcription model warmed and ready.")
    except Exception as exc:
        print(f"⚠️ Model warm-up failed, will retry lazily on first request: {exc}")

    print("🟢 Startup complete.")

    yield  # Server is now running and accepting requests

    # Cleanup on Shutdown
    print("🛑 Shutting down VoiceScribe AI backend. Clearing memory...")


# Initialize the FastAPI application
app = FastAPI(
    title="VoiceScribe AI API",
    description="Unified backend for Meeting Mode and Quick Capture AI processing.",
    version="2.0.0",
    lifespan=lifespan
)

# ==========================================
# 🛡️ Security & Performance Middleware
# ==========================================

# 1. Performance: Compresses large transcription JSONs to speed up frontend loading times.
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. CORS: Allows your cloud frontend to safely communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

# ==========================================
# 🚦 API Routes
# ==========================================
# Connect all endpoints under the /api/v1 prefix
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirects the base URL to a safe API ping endpoint."""
    return RedirectResponse(url="/api/v1/ping")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Prevents browser errors when looking for a favicon."""
    return JSONResponse(status_code=204, content=None)


@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint to verify the server is alive and read config."""
    return {
        "status": "online",
        "service": "VoiceScribe AI Backend",
        "whisper_model": getattr(settings, "WHISPER_MODEL", "Unknown"),
        "whisper_backend": getattr(settings, "WHISPER_BACKEND", "Unknown"),
        "llm_target": getattr(settings, "LLM_MODEL", "Unknown"),
        "diarization_enabled": getattr(settings, "ENABLE_DIARIZATION", False),
    }


# ==========================================
# 🚀 Direct Execution block
# ==========================================
if __name__ == "__main__":
    # This allows you to start the server simply by running `python backend/app/main.py`
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)