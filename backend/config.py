from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    WHISPER_MODEL: str = "base"
    DIARIZATION_MODEL: str = "pyannote/speaker-diarization"
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024
    SUPPORTED_FORMATS: str = "webm,mp3,wav,m4a,mp4,mov,avi,mkv"
    LONG_RECORDING_THRESHOLD: int = 600
    CHUNK_LENGTH: int = 300
    HISTORY_LIMIT: int = 5
    LANGUAGE_MODE: str = "automatic"
    LLM_MODEL: str = "qwen3:8b"
    LLM_THINKING_MODE_TASKS: str = "summarize,action_items,ask"
    LLM_CONTEXT_MODE: str = "native"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    RAG_TOP_K: int = 5
    BACKEND_URL: str = "http://127.0.0.1:8000"
    STORAGE_DIR: Path = Path("..", "storage").resolve()
    VECTOR_DIR: Path = Path("..", "vector_store").resolve()
    HISTORY_FILE: Path = Path("..", "storage", "history.json").resolve()
    UPLOAD_DIR: Path = Path("..", "storage", "uploads").resolve()
    REPORT_DIR: Path = Path("..", "storage", "reports").resolve()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
