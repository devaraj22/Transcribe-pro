import subprocess
from pathlib import Path
from typing import Optional

from .config import settings
from .utils import is_video_file


def probe_duration(path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return float(result.stdout.strip())


def extract_audio(input_path: Path, output_path: Path) -> Path:
    output_path = output_path.with_suffix(".wav")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg extraction failed: {result.stderr.strip()}")
    return output_path


def prepare_audio_file(upload_path: Path) -> Path:
    if is_video_file(upload_path):
        audio_path = upload_path.parent / f"{upload_path.stem}_extracted.wav"
        return extract_audio(upload_path, audio_path)
    return upload_path
