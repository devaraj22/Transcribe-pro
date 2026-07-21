"""
denoise_worker.py
==================
Standalone script run INSIDE the isolated `denoise-env` virtualenv
(which has deepfilternet + its required numpy<2, kept separate from the
main app's numpy>=2.x needed by whisperx/pyannote).

Invoked as a subprocess from denoiser_service.py — never imported directly
by the main application, since importing it would pull df.enhance into the
main (incompatible) numpy environment.

Usage:
    python denoise_worker.py <input_wav_path> <output_wav_path>

Exits 0 on success, non-zero on failure (stderr has the reason).
"""

import sys
from df.enhance import enhance, init_df, load_audio, save_audio  # type: ignore[reportMissingImports]


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python denoise_worker.py <input_path> <output_path>", file=sys.stderr)
        return 1

    input_path, output_path = sys.argv[1], sys.argv[2]

    try:
        from df.enhance import enhance, init_df, load_audio, save_audio
    except ImportError as exc:
        print(f"deepfilternet not available in this environment: {exc}", file=sys.stderr)
        return 2

    try:
        model, df_state, _ = init_df()
        audio, _ = load_audio(input_path, sr=df_state.sr())
        enhanced = enhance(model, df_state, audio)
        save_audio(output_path, enhanced, df_state.sr())
        return 0
    except Exception as exc:
        print(f"Denoising failed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())