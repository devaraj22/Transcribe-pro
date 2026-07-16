from backend.services.whisper_service import get_whisper_model

def run_quick_capture(audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Processes short audio clips synchronously.
    Skips speaker diarization to save computation time.
    """
    print(f"⚡ Running Quick Capture module for: {audio_path}")
    model = get_whisper_model()
    
    lang = None if language_mode == "automatic" else language_mode
    segments, info = model.transcribe(audio_path, language=lang, beam_size=5)
    
    full_text = []
    formatted_segments = []
    
    for seg in segments:
        full_text.append(seg.text)
        formatted_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "language": info.language,
            "speaker": "SPEAKER_00",
            "text": seg.text.strip()
        })
        
    return {
        "full_text": " ".join(full_text),
        "segments": formatted_segments
    }