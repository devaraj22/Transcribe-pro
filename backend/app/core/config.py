import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ==========================================
    #  AI Engine & Model Configurations
    # ==========================================
    # Whisper Settings (Speech-to-Text)
    WHISPER_MODEL: str = "base"
    
    # Pyannote Settings (Speaker Diarization)
    DIARIZATION_MODEL: str = "pyannote/speaker-diarization-3.1"
    HF_TOKEN: str = os.getenv("HF_TOKEN", "") # Hugging Face token required for Pyannote
    
    # Ollama Settings (Local LLM via Qwen3:8B)
    OLLAMA_HOST: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen3:8b"
    LLM_CONTEXT_MODE: str = "native" # Can switch to "yarn" for 131k context window

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
    # Local Storage System (No Database)
    # ==========================================
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # The primary storage directory mapped to the project root
    STORAGE_DIR: str = os.path.join(BASE_DIR, "storage")
    UPLOAD_DIR: str = os.path.join(STORAGE_DIR, "uploads")
    TRANSCRIPT_DIR: str = os.path.join(STORAGE_DIR, "transcripts")
    REPORT_DIR: str = os.path.join(STORAGE_DIR, "reports")
    
    # The dedicated JSON file acting as your application's database
    HISTORY_FILE: str = os.path.join(STORAGE_DIR, "history.json")
    
    # FAISS local vector indexes
    VECTOR_DIR: str = os.path.join(BASE_DIR, "vector_store")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

# Initialize settings globally
settings = Settings()

# ==========================================
#  Startup Initialization
# ==========================================
# Automatically create all required local directories if they do not exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TRANSCRIPT_DIR, exist_ok=True)
os.makedirs(settings.REPORT_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DIR, exist_ok=True)

# Create an empty history.json array if it doesn't exist yet
if not os.path.exists(settings.HISTORY_FILE):
    with open(settings.HISTORY_FILE, 'w', encoding='utf-8') as f:
        f.write("[]")