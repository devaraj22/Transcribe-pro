"""
denoiser_service.py
====================
Speech denoising service using `noisereduce` (with FFmpeg fallback).
Runs directly inside the main application process with NumPy >= 2.0 compatibility.
"""

from __future__ import annotations

import os
import subprocess
from backend.app.core.config import settings


def denoise_audio(input_path: str) -> str:
    """
    Denoises an audio file directly in-process.
    """
    if not getattr(settings, "DENOISE_ENABLED", True):
        return input_path

    if not os.path.exists(input_path):
        return input_path

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_denoised{ext or '.wav'}"

    # 1. Try noisereduce library (Direct Python Execution)
    try:
        import noisereduce as nr
        import soundfile as sf

        data, rate = sf.read(input_path)
        # Softened noise reduction (0.5) to keep voice natural & improve Whisper accuracy
        reduced_noise = nr.reduce_noise(y=data, sr=rate, prop_decrease=0.5)
        sf.write(output_path, reduced_noise, rate)

        print(f"🧹 Denoised audio created via noisereduce: {output_path}")
        return output_path

    except ImportError:
        pass  # noisereduce not found, fallback to FFmpeg
    except Exception as exc:
        print(f"⚠️ noisereduce failed, attempting FFmpeg fallback: {exc}")

    # 2. Try FFmpeg FFT Denoise Filter Fallback
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-af", "afftdn=nr=12:nf=-30",
            output_path
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"🧹 Denoised audio created via FFmpeg: {output_path}")
            return output_path

    except Exception as exc:
        print(f"⚠️ FFmpeg denoising error: {exc}")

    # 3. Final Fallback to Original Audio
    print("⚠️ Denoising skipped, using original audio")
    return input_path