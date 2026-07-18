from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.app.core.config import settings

# Import the centralized API router that exposes /api/v1 endpoints
from backend.app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager runs before the server starts accepting requests
    and cleans up when the server stops.
    """
    print(" Booting up VoiceScribe AI...")
    print(f" Storage directories verified at: {settings.STORAGE_DIR}")
    print(f" Whisper model config set to '{settings.WHISPER_MODEL}' ({settings.WHISPER_BACKEND} backend).")
    if settings.HF_TOKEN:
        print(" HF_TOKEN is configured for diarization.")
    else:
        print(" HF_TOKEN is not configured; diarization may be unavailable.")
    print(" Startup complete. Models will load on demand when a transcription request begins.")

    yield  # Server is now running and accepting requests

    # Cleanup on Shutdown
    print(" Shutting down VoiceScribe AI backend. Clearing memory...")


# Initialize the FastAPI application
app = FastAPI(
    title="VoiceScribe AI API",
    description="Unified backend for Meeting Mode and Quick Capture AI processing.",
    version="2.0.0",
    lifespan=lifespan
)

# ==========================================
#  Security & CORS Middleware
# ==========================================
# React/Vite typically runs on localhost:5173 during development.
# The regex form keeps local development ports flexible while still blocking unrelated origins.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)

# ==========================================
# 🚦 API Routes
# ==========================================
# Connect all the individual endpoints (process, enhance, rag, report, history) under the /api/v1 prefix
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/api/v1/ping")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return JSONResponse(status_code=204, content=None)


@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint to verify the server is alive."""
    return {
        "status": "online",
        "service": "VoiceScribe AI Backend",
        "whisper_model": settings.WHISPER_MODEL,
        "whisper_backend": settings.WHISPER_BACKEND,
        "llm_target": settings.LLM_MODEL,
        "diarization_enabled": settings.ENABLE_DIARIZATION,
    }
