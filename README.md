# VoiceScribe AI

VoiceScribe AI is a self-hosted voice-note and meeting intelligence platform that runs fully locally. It combines quick capture transcription and sharing with long-form meeting analysis, speaker-aware summarization, and retrieval-augmented Q&A.

## Features
- Record or upload audio/video files
- Local transcription using faster-whisper
- Speaker diarization via pyannote.audio
- Automatic multi-language detection or manual language mode
- Local LLM enhancement through Ollama + Qwen3:8B
- Summarization, action item extraction, translation, auto-titling
- Retrieval-augmented Q&A over indexed transcript chunks
- Download transcripts as `.txt`, export meeting reports as PDF
- Share via WhatsApp deep link (`wa.me`) with no API key
- Local history capped at 5 entries

## Setup
1. Install Python 3.11+.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Ollama and pull the model:
   ```bash
   ollama pull qwen3:8b
   ```

## Backend
1. Activate the virtual environment.
2. Run the FastAPI backend from the repo root:
   ```bash
   cd D:\transcribe-pro
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
   ```

   Or activate the venv and run from the repo root:
   ```bash
   cd D:\transcribe-pro
   .\.venv\Scripts\Activate.ps1
   python -m uvicorn backend.main:app --reload --port 8000
   ```

## Frontend
1. Activate the virtual environment.
2. Run the Dash frontend from `frontend/`:
   ```bash
   cd frontend
   python app.py
   ```
3. Open the Dash app in your browser at `http://127.0.0.1:8050`.

## Important Notes
- `faster-whisper` and `pyannote.audio` download model weights on first run.
- `pyannote.audio` requires a Hugging Face access token and license acceptance for the pretrained diarization pipeline.
- `ollama` must be installed and running locally before starting the backend.
- Language modes:
  - `Automatic`: detects language per segment and transcribes each segment in its detected language.
  - `Manual`: uses a single user-selected language for the entire transcription.
- Long recordings above the configured threshold route to a background job path and return a `job_id` for polling.
- Enhancement features are optional and use the local Qwen3:8B model. Thinking-mode is used for summarization, action-item extraction, and Q&A; non-thinking-mode is used for cleanup, translation, and titling.
- Q&A uses retrieval-augmented prompting with FAISS and transcript chunk embeddings.
- History is local-only, capped at 5 entries, and never sent anywhere.

## Project Structure
- `backend/`: FastAPI backend and processing pipeline
- `frontend/`: Dash UI
- `storage/`: local storage for uploads, transcripts, reports (gitignored)
- `vector_store/`: local FAISS indexes (gitignored)
