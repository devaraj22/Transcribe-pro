# Transcribe Pro

Transcribe Pro is a merged transcription application with two front-end entry points into the same processing core:

- **Quick Capture Mode**: Rapid short-note transcription, cleanup, WhatsApp sharing, and `.txt` download.
- **Meeting Mode**: Long-form audio/video processing, speaker diarization, AI-generated summaries, action items, PDF report generation, and retrieval-augmented Q&A.

## Architecture

The backend is a unified FastAPI service. A single `/api/v1/process` endpoint accepts audio or video uploads and routes short recordings to instant quick capture processing or long recordings to background meeting processing.

Core pipeline features:
- FFmpeg audio extraction for video files
- Whisper transcription and pyannote speaker diarization
- Local LLM enhancement via Ollama/Qwen3:8B
- FAISS indexing for RAG Q&A
- History tracking of the most recent 5 jobs
- PDF report generation for meeting outputs

## Frontend

The frontend is a React + Vite application with two workspace views:
- `Quick Capture Workspace`
- `Meeting Mode Workspace`

Features added:
- In-browser audio recording with MediaRecorder
- Drag-and-drop file upload
- Manual or automatic language selection
- Synchronous short capture processing and asynchronous long-form processing
- Share to WhatsApp and download transcripts
- Meeting summary, action-item extraction, PDF report generation, and vector chat
- Recent history panel populated from the backend

## Running the project

### Prerequisites
Before running the application, you need to set up **Ollama** for AI-powered meeting insights:

1. **Install Ollama**: Download from [ollama.com](https://ollama.com)
2. **Download the model**: Run `ollama pull qwen3:8b` (4.7GB)
3. **Keep Ollama running**: Run `ollama serve` in a terminal during development

See [OLLAMA_SETUP.md](OLLAMA_SETUP.md) for detailed setup instructions.

### Optional: Pyannote on Windows (advanced, opt-in)

Pyannote speaker diarization depends on `speechbrain` and, in some configurations, `k2`. These components are not reliably supported on native Windows and may fail at import time. The project disables Pyannote on Windows by default to prevent startup errors. If you still want to attempt Pyannote on Windows, follow these steps (recommended: use WSL/Ubuntu or a Linux host):

1. Use WSL (Ubuntu) or a Linux environment for best compatibility.

2. Setup Python and a virtualenv in WSL/Ubuntu:

```bash
sudo apt update && sudo apt install -y build-essential cmake git python3-dev python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

3. Install PyTorch according to your system and CUDA availability — follow the official instructions at https://pytorch.org. For a CPU-only example:

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
```

4. Install `k2` and `speechbrain` following their official guides. `k2` often requires building from source or using distribution-specific binaries — see https://k2-fsa.github.io for details. After installing `k2`, install `speechbrain` and `pyannote.audio`:

```bash
pip install speechbrain pyannote.audio
```

5. Opt-in to enabling Pyannote on Windows by adding to your `.env` (or export in WSL):

```
ENABLE_PYANNOTE_ON_WINDOWS=true
HF_TOKEN=your_hf_token_here
```

6. Restart the backend. If imports still fail, run the backend from WSL or a Linux VM where `k2` and `speechbrain` are supported.

Note: If you do not wish to enable Pyannote, the application will fall back to whisper-only transcription.

### Running the application

1. **Start the backend**:
   - Create and activate the Python virtual environment
   - Install backend dependencies from `requirements.txt`
   - Run the FastAPI app on port 8000: `uvicorn backend.app.main:app --reload`

2. **Start the frontend**:
   - From `frontend`, run `npm install` if needed
   - Run `npm run dev`

3. **Ensure Ollama is running**:
   - Open a terminal and run `ollama serve`
   - Verify: The service should be accessible at `http://localhost:11434`

The frontend expects the backend at `http://localhost:8000/api/v1`.

#VITE_API_KEY
#python3 -c "import secrets; print(secrets.token_hex(32))"

# cat /teamspace/studios/this_studio/Transcribe-pro/backend/.env
