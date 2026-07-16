import os
from backend.services.whisper_service import get_whisper_model
from backend.services.pyannote_service import get_diarization_pipeline

def run_quick_capture(audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Processes short audio clips (under 10 mins) quickly.
    Skips speaker diarization to save computation time.
    """
    print(f"⚡ Running Quick Capture pipeline for: {audio_path}")
    model = get_whisper_model()
    
    # Configure language if explicitly forced
    lang = None if language_mode == "automatic" else language_mode
    
    # Transcribe the audio file
    segments, info = model.transcribe(audio_path, language=lang, beam_size=5)
    
    full_text = []
    formatted_segments = []
    
    for seg in segments:
        full_text.append(seg.text)
        formatted_segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "language": info.language,
            "speaker": "SPEAKER_00",  # Default single speaker for quick captures
            "text": seg.text.strip()
        })
        
    return {
        "full_text": " ".join(full_text),
        "segments": formatted_segments
    }

def run_meeting_mode(audio_path: str, language_mode: str = "automatic") -> dict:
    """
    Processes long meeting files. Runs speaker diarization (Pyannote) 
    and transcription (Whisper) together to create a true script layout.
    """
    print(f"🚀 Running Full Meeting Mode pipeline for: {audio_path}")
    
    # 1. Step A: Who spoke when? (Diarization)
    pipeline = get_diarization_pipeline()
    if pipeline is None:
        print("⚠️ Diarization pipeline unavailable. Falling back to simple transcription.")
        return run_quick_capture(audio_path, language_mode)
        
    print("⏳ Segmenting speakers via Pyannote...")
    diarization = pipeline(audio_path)
    
    # 2. Step B: Extract speech text (Transcription)
    model = get_whisper_model()
    lang = None if language_mode == "automatic" else language_mode
    segments, info = model.transcribe(audio_path, language=lang, beam_size=5)
    
    # Convert generator to a list to keep it in memory
    whisper_segments = list(segments)
    
    formatted_segments = []
    full_text = []
    
    print("⏳ Aligning text segments with speakers...")
    # 3. Step C: Map Whisper's text timestamps to Pyannote's speaker timestamps
    for seg in whisper_segments:
        # Find who was speaking at the midpoint of this text segment
        midpoint = (seg.start + seg.end) / 2
        assigned_speaker = "UNKNOWN"
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if turn.start <= midpoint <= turn.end:
                assigned_speaker = speaker
                break
                
        # If midpoint alignment failed, assign the closest active speaker
        if assigned_speaker == "UNKNOWN":
            closest_dist = float('inf')
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                dist = min(abs(midpoint - turn.start), abs(midpoint - turn.end))
                if dist < closest_dist:
                    closest_dist = dist
                    assigned_speaker = speaker

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