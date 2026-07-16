from faster_whisper import WhisperModel
from backend.app.core.config import settings

_whisper_model = None

def get_whisper_model() -> WhisperModel:
    """
    Loads the faster-whisper model into memory.
    """
    global _whisper_model
    
    if _whisper_model is None:
        print(f"⏳ Loading faster-whisper '{settings.WHISPER_MODEL}' model...")
        _whisper_model = WhisperModel(
            settings.WHISPER_MODEL, 
            device="cpu", 
            compute_type="int8"
        )
        
    return _whisper_model