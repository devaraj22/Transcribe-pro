import os
import nltk
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_secret_key: str | None = None
    # ==========================================
    #  AI Engine & Model Configurations
    # ==========================================
    # Whisper Settings (Speech-to-Text)
    WHISPER_MODEL: str = "base"
    DEFAULT_LANGUAGE: str = "en"

    # Backend selection: "whisperx" (batched, recommended) or "faster-whisper" (sequential, low-VRAM)
    WHISPER_BACKEND: str = "whisperx"

    # Pyannote Settings (Speaker Diarization)
    DIARIZATION_MODEL: str = "pyannote/speaker-diarization-3.1"
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")  # Hugging Face token required for Pyannote
    # Set to true to opt-in to attempting Pyannote on Windows (advanced, may fail)
    ENABLE_PYANNOTE_ON_WINDOWS: bool = False
    # Master switch to enable/disable diarization (useful when HF_TOKEN is absent)
    ENABLE_DIARIZATION: bool = True

    # VAD method: "pyannote" (default), "silero" (lighter, no HF token needed), "none"
    VAD_METHOD: str = "pyannote"

    # Local LLM Settings (in-process via llama-cpp-python — no external server
    # process to crash or manage). Point LOCAL_LLM_MODEL_PATH at a GGUF quant
    # of your model, e.g. a Qwen3-8B-Instruct Q4_K_M GGUF — or reuse the blob
    # Ollama already downloaded (see find_ollama_gguf.sh).
    LOCAL_LLM_MODEL_PATH: str = os.getenv("LOCAL_LLM_MODEL_PATH", "")
    LOCAL_LLM_CONTEXT_SIZE: int = int(os.getenv("LOCAL_LLM_CONTEXT_SIZE", "4096"))
    LOCAL_LLM_THREADS: int = int(os.getenv("LOCAL_LLM_THREADS", str(max(1, (os.cpu_count() or 4) - 1))))
    # 0 = CPU only (current default). When you move to a GPU box, set
    # LOCAL_LLM_GPU_LAYERS=-1 in .env to offload all layers to GPU — no code
    # change needed. Requires llama-cpp-python installed with CUDA support.
    LOCAL_LLM_GPU_LAYERS: int = int(os.getenv("LOCAL_LLM_GPU_LAYERS", "0"))

    # ==========================================
    #  Subtitle / Caption Generation
    # ==========================================
    # Max characters per subtitle line (OpenAI whisper utils.py style)
    MAX_LINE_CHARS: int = 42
    # Max lines per subtitle segment event
    MAX_LINES_PER_SEGMENT: int = 2
    # Default subtitle format returned by the download endpoint: "ass" | "srt"
    SUBTITLE_FORMAT: str = "ass"

    # ==========================================
    #  NLP & Sentence Splitting
    # ==========================================
    # Enable NLTK sentence-level splitting after alignment (improves subtitle readability)
    NLTK_SENTENCE_SPLIT: bool = True

    # ==========================================
    #  Thresholds & Processing Logic
    # ==========================================
    # 600 seconds = 10 minutes. Audio longer than this triggers Meeting Mode background jobs.
    LONG_RECORDING_THRESHOLD: float = 600.0

    # Audio chunks for processing long files (300 seconds = 5 minutes per chunk)
    CHUNK_LENGTH: float = 300.0

    # Max upload size (500 MB to accommodate 1-2 hour video files)
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024

    # Number of text chunks retrieved for RAG Q&A
    RAG_TOP_K: int = 5

    # Enforces the maximum number of recent items tracked in history.json
    HISTORY_LIMIT: int = 5

    # ==========================================
    #  Benchmarking
    # ==========================================
    # Path to TEDLIUM (or any ASR benchmark) audio directory; empty = benchmarking disabled
    BENCHMARK_AUDIO_DIR: str = ""

    # ==========================================
    # Local Storage System (No Database)
    # ==========================================
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # The primary storage directory mapped to the project root
    STORAGE_DIR: str = os.path.join(BASE_DIR, "storage")
    UPLOAD_DIR: str = os.path.join(STORAGE_DIR, "uploads")
    TRANSCRIPT_DIR: str = os.path.join(STORAGE_DIR, "transcripts")
    REPORT_DIR: str = os.path.join(STORAGE_DIR, "reports")
    SUBTITLE_DIR: str = os.path.join(STORAGE_DIR, "subtitles")

    # The dedicated JSON file acting as your application's database
    HISTORY_FILE: str = os.path.join(STORAGE_DIR, "history.json")

    # FAISS local vector indexes
    VECTOR_DIR: str = os.path.join(BASE_DIR, "vector_store")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Initialize settings globally
settings = Settings()

# ==========================================
#  Startup Initialization
# ==========================================
# Automatically create all required local directories if they do not exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TRANSCRIPT_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
os.makedirs(settings.SUBTITLE_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DIR, exist_ok=True)

# Create an empty history.json array if it doesn't exist yet
if not os.path.exists(settings.HISTORY_FILE):
    with open(settings.HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write("[]")

# Pre-download NLTK punkt tokenizer data (silent, best-effort)
if settings.NLTK_SENTENCE_SPLIT:
    try:
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
    except Exception:
        pass  # Offline / no network — NLTK will fall back gracefully