from backend.services.whisper_service import get_whisper_model
from backend.services.pyannote_service import get_diarization_pipeline
from backend.app.modules.quick_capture.pipeline import run_quick_capture

def run_meeting_mode(audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Orchestrates Pyannote and Whisper to create a speaker-mapped transcript.
    """
    print(f"🚀 Running Meeting Mode module for: {audio_path}")
    
    pipeline = get_diarization_pipeline()
    if pipeline is None:
        return run_quick_capture(audio_path, language_mode)
        
    print("⏳ Segmenting speakers via Pyannote...")
    diarization = pipeline(audio_path)
    
    model = get_whisper_model()
    lang = None if language_mode == "automatic" else language_mode
    segments, info = model.transcribe(audio_path, language=lang, beam_size=5)
    
    whisper_segments = list(segments)
    formatted_segments = []
    full_text = []
    
    print("⏳ Aligning text segments with speakers...")
    for seg in whisper_segments:
        midpoint = (seg.start + seg.end) / 2
        assigned_speaker = "UNKNOWN"
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if turn.start <= midpoint <= turn.end:
                assigned_speaker = speaker
                break
                
        full_text.append(seg.text)
        formatted_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "language": info.language,
            "speaker": assigned_speaker,
            "text": seg.text.strip()
        })
        
    return {
        "full_text": " ".join(full_text),
        "segments": formatted_segments
    }