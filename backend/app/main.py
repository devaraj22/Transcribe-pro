from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.app.core.config import settings

# Import the services to trigger model pre-loading
from backend.services.whisper_service import get_whisper_model
from backend.services.pyannote_service import get_diarization_pipeline

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
    
    # 1. Pre-load Machine Learning Models into RAM
    print(" Loading AI Models into memory (this may take a moment on first run)...")
    try:
        get_whisper_model()
        print(f"Whisper model '{settings.WHISPER_MODEL}' loaded.")
        
        get_diarization_pipeline()
        print(f" Pyannote diarization pipeline loaded.")
    except Exception as e:
        print(f" Warning during model initialization: {e}")
        print("Make sure your HF_TOKEN is set in the .env file for Pyannote.")

    yield # Server is now running and accepting requests

    # 2. Cleanup on Shutdown
    print(" Shutting down VoiceScribe AI backend. Clearing memory...")


# Initialize the FastAPI application
app = FastAPI(
    title="VoiceScribe AI API",
    description="Unified backend for Meeting Mode and Quick Capture AI processing.",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================
#  Security & CORS Middleware
# ==========================================
# React/Vite typically runs on localhost:5173 during development.
# This ensures the browser doesn't block frontend HTTP requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # React / Vite dev server
        "http://localhost:3000",  # Standard React fallback port
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],
)

# ==========================================
# ðŸš¦ API Routes
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
        "llm_target": settings.LLM_MODEL
    }
