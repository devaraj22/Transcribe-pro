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
