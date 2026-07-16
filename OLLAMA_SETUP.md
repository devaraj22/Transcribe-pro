# Ollama Setup Guide for VoiceScribe AI

## Overview
The "Meeting insights" feature (summaries and action items) requires **Ollama** - a local LLM service. This guide explains how to set it up.

## Prerequisites
- **Ollama** installed on your system
- **qwen3:8b** model downloaded

## Installation

### Step 1: Download and Install Ollama
1. Visit [ollama.ai](https://ollama.ai) or [ollama.com](https://ollama.com)
2. Download the installer for your OS (Windows, macOS, Linux)
3. Run the installer and follow the setup wizard
4. Restart your system if prompted

### Step 2: Pull the Qwen3:8B Model
Open a terminal/command prompt and run:
```bash
ollama pull qwen3:8b
```

This will download the model (approximately 4.7GB). This only needs to be done once.

### Step 3: Verify Installation
Run:
```bash
ollama list
```

You should see `qwen3:8b` in the list of available models.

## Running Ollama

### Start the Ollama Service
Simply run:
```bash
ollama serve
```

Or on **Windows**, you can:
- Search for "Ollama" in Start Menu and click to launch
- Or run in PowerShell: `ollama serve`

The service will start on `http://localhost:11434` (default port).

You should see output like:
```
2024/07/15 14:30:45 "GET /api/tags HTTP/1.1" 200 128
```

### Verify Ollama is Running
In another terminal, run:
```bash
curl http://localhost:11434/api/tags
```

Or on Windows PowerShell:
```powershell
Invoke-WebRequest -Uri "http://localhost:11434/api/tags"
```

You should see a response containing `qwen3:8b`.

## Troubleshooting

### "Meeting insights is not working" / Summaries/Action Items not appearing

**Problem**: Ollama is not running or not accessible

**Solution**:
1. Open terminal and run: `ollama serve`
2. Wait for the message indicating the service is ready
3. Refresh your VoiceScribe app in the browser
4. Try uploading a meeting again

### "Ollama service timeout" error

**Problem**: Ollama is running but slow to respond

**Solution**:
1. Check system resources (Ollama requires significant RAM/CPU)
2. Close other applications to free up resources
3. Wait longer - first request to a model can take 30-60 seconds
4. Consider running Ollama on a machine with more resources

### Model not found

**Problem**: The qwen3:8b model hasn't been downloaded

**Solution**:
1. Run: `ollama pull qwen3:8b`
2. Wait for download to complete (5-10 minutes depending on internet speed)
3. Verify: `ollama list` should show the model

## System Requirements

Ollama requires:
- **Minimum RAM**: 4GB (for qwen3:8b)
- **Recommended RAM**: 8GB or more
- **GPU** (optional but recommended for faster performance):
  - NVIDIA CUDA 11.0+ for GPUs
  - Apple Silicon (M1/M2/M3) for native acceleration
  - AMD ROCm for AMD GPUs

## Performance Tips

1. **Close other applications** while Ollama is running to free up resources
2. **First request is slow**: The first API call loads the model into memory (30-60 seconds). Subsequent calls are much faster.
3. **Keep model in memory**: Don't restart Ollama between requests to maintain performance
4. **Use GPU if available**: Ollama automatically uses GPU if detected for faster inference

## Configuration

The app is configured in `backend/app/core/config.py`:
- `OLLAMA_HOST`: Default is `http://localhost:11434`
- `LLM_MODEL`: Default is `qwen3:8b`

To change these settings, edit the config file.

## Verification Checklist

- [ ] Ollama installed
- [ ] qwen3:8b model downloaded (`ollama list` shows it)
- [ ] Ollama service running (`ollama serve` in terminal)
- [ ] Backend running (`cd backend && uvicorn app.main:app --reload`)
- [ ] Frontend running (`cd frontend && npm run dev`)
- [ ] Upload a meeting in VoiceScribe
- [ ] Summary and Action Items appear after processing

## More Information

- [Ollama Documentation](https://ollama.ai/docs)
- [Model Library](https://ollama.ai/library)
- [Installation Guide](https://github.com/ollama/ollama)
