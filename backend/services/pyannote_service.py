import torch
from pyannote.audio import Pipeline
from backend.app.core.config import settings

_diarization_pipeline = None

def get_diarization_pipeline():
    """
    Loads the Pyannote speaker diarization pipeline into memory.
    """
    global _diarization_pipeline
    
    if _diarization_pipeline is None:
        if not settings.HF_TOKEN:
            print("⚠️ WARNING: HF_TOKEN is missing from your environment variables.")
            return None
            
        print("⏳ Loading Pyannote diarization pipeline...")
        try:
            _diarization_pipeline = Pipeline.from_pretrained(
                settings.DIARIZATION_MODEL,
                use_auth_token=settings.HF_TOKEN
            )
            
            if _diarization_pipeline and torch.cuda.is_available():
                _diarization_pipeline.to(torch.device("cuda"))
                
        except Exception as e:
            print(f"❌ Failed to load Pyannote pipeline: {e}")
            raise e
            
    return _diarization_pipeline