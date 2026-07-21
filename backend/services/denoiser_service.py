"""
denoiser_service.py
====================
Speech denoising via DeepFilterNet, run once per recording immediately
before transcription (after FFmpeg audio extraction, before WhisperX).

IMPORTANT — why this shells out to a subprocess instead of importing
df.enhance directly:
    deepfilternet's current release hard-requires numpy<2.0, while
    whisperx and pyannote.audio both require numpy>=2.x. These cannot
    coexist in one Python environment. DeepFilterNet is installed in an
    isolated venv (DENOISE_VENV_PYTHON) and invoked as a subprocess via
    denoise_worker.py, so its numpy<2 dependency never touches the main
    app's environment.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from backend.app.core.config import settings

# Path to the python interpreter INSIDE the isolated denoise-env venv,
# e.g. "/teamspace/studios/this_studio/denoise-env/bin/python"
_DENOISE_VENV_PYTHON = getattr(settings, "DENOISE_VENV_PYTHON", None)

# denoise_worker.py lives alongside this file.
_WORKER_SCRIPT = str(Path(__file__).parent / "denoise_worker.py")


def denoise_audio(input_path: str) -> str:
    """
    Denoise an audio file via a subprocess call into the isolated
    DeepFilterNet virtualenv. Writes a new file alongside the original
    (suffix ``_denoised``) and returns its path.

    If denoising is disabled, the isolated venv isn't configured, or the
    subprocess call fails, this returns ``input_path`` unchanged so the
    pipeline can continue with the original (noisy) audio rather than
    failing the whole job over an optional enhancement step.

    Args:
        input_path: Path to the pre-processed (FFmpeg-extracted, if video)
                    audio WAV file.

    Returns:
        Path to the denoised audio file, or the original path if denoising
        was skipped or failed.
    """
    if not getattr(settings, "DENOISE_ENABLED", True):
        return input_path

    if not _DENOISE_VENV_PYTHON or not os.path.exists(_DENOISE_VENV_PYTHON):
        print(
            "⚠️ Denoising skipped: DENOISE_VENV_PYTHON is not configured or "
            "doesn't exist. Set it in .env to the isolated venv's python "
            "path, e.g. /teamspace/studios/this_studio/denoise-env/bin/python"
        )
        return input_path

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_denoised{ext or '.wav'}"

    try:
        result = subprocess.run(
            [_DENOISE_VENV_PYTHON, _WORKER_SCRIPT, input_path, output_path],
            capture_output=True,
            text=True,
            timeout=300,  # denoising a long recording shouldn't take this long; safety cap
        )
        if result.returncode != 0:
            print(f"⚠️ Denoising failed, using original audio: {result.stderr.strip()}")
            return input_path

        print(f"🧹 Denoised audio written to {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        print("⚠️ Denoising timed out, using original audio")
        return input_path
    except Exception as exc:
        print(f"⚠️ Denoising skipped, using original audio: {exc}")
        return input_path