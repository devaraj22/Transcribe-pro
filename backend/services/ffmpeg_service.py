import os
import subprocess
import uuid
from backend.app.core.config import settings

def extract_audio(input_path: str) -> str:
    """
    Takes an input media file (video or audio), standardizes it, 
    and outputs a clean 16kHz, Mono, 16-bit WAV file suitable for AI models.
    """
    # Ensure the uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    output_filename = f"clean_audio_{uuid.uuid4().hex[:8]}.wav"
    output_path = os.path.join(settings.UPLOAD_DIR, output_filename)
    
    # FFmpeg command to force: 16kHz sample rate (-ar), 1 channel/mono (-ac), 16-bit PCM (-c:a)
    command = [
        "ffmpeg",
        "-y",               # Overwrite output files without asking
        "-i", input_path,   # Input file
        "-vn",              # Strip video completely
        "-acodec", "pcm_s16le", # Convert to 16-bit uncompressed audio
        "-ar", "16000",     # 16kHz sample rate (Required by Whisper/Pyannote)
        "-ac", "1",         # Mono audio
        output_path
    ]
    
    try:
        print(f"🎬 Transcoding media to standardized WAV format...")
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path
        
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode('utf-8', errors='ignore')
        print(f"❌ FFmpeg Error: {error_message}")
        raise RuntimeError(f"Failed to extract audio. Is FFmpeg installed on your system? Error: {error_message}")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg is not installed or not added to your system PATH.")

def probe_duration(audio_path: str) -> float:
    """
    Uses ffprobe to quickly read the metadata of the media file 
    and return its total duration in seconds.
    """
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        duration_str = result.stdout.strip()
        return float(duration_str)
        
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"⚠️ Failed to probe audio duration: {e}")
        # Fallback to standard 0 if probe fails to prevent crashing
        return 0.0
    except FileNotFoundError:
        raise RuntimeError("FFprobe is not installed or not added to your system PATH.")