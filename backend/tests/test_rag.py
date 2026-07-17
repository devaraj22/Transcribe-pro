import io
import tempfile
from fastapi import BackgroundTasks, UploadFile
import pytest

from backend.app.api.v1.endpoints.rag import ask_question, build_context_block
from backend.app.schemas.rag import RAGRequest
from backend.app.api.v1.endpoints import process as process_endpoint


@pytest.mark.asyncio
async def test_ask_question_uses_ollama_text_response(monkeypatch):
    async def fake_call_ollama(prompt, system_prompt="You are a helpful AI assistant."):
        return "hello from ollama", False

    monkeypatch.setattr(
        "backend.app.api.v1.endpoints.rag.search_vector_index",
        lambda job_id, question, top_k=3: ["chunk one"],
    )
    monkeypatch.setattr(
        "backend.app.api.v1.endpoints.rag._call_ollama",
        fake_call_ollama,
    )

    response = await ask_question(RAGRequest(job_id="job-1", question="what happened"))

    assert response["answer"] == "hello from ollama"
    assert response["sources"] == ["chunk one"]


def test_build_context_block_truncates_long_context():
    chunks = ["A" * 300, "B" * 300, "C" * 300]
    context = build_context_block(chunks, max_chars=450)

    assert len(context) <= 450
    assert context.startswith("A")
    assert "B" not in context


@pytest.mark.asyncio
async def test_process_audio_builds_vector_index_for_short_upload(monkeypatch):
    tmp_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path.close()

    called = {}

    def fake_create_vector_index(job_id, transcript_text):
        called["job_id"] = job_id
        called["text"] = transcript_text
        return True

    monkeypatch.setattr(process_endpoint, "extract_audio", lambda raw_path: tmp_path.name)
    monkeypatch.setattr(process_endpoint, "probe_duration", lambda audio_path: 30.0)
    monkeypatch.setattr(process_endpoint, "run_quick_capture", lambda audio_path, language_mode: {"full_text": "short transcript", "segments": []})
    monkeypatch.setattr(process_endpoint, "append_to_history", lambda **kwargs: None)
    monkeypatch.setattr(process_endpoint, "create_vector_index", fake_create_vector_index)

    upload_file = UploadFile(filename="demo.wav", file=io.BytesIO(b"abc"))
    response = await process_endpoint.process_audio(
        BackgroundTasks(),
        file=upload_file,
        language_mode="automatic",
    )

    assert response["status"] == "complete"
    assert called.get("job_id") is not None
    assert called.get("text") == "short transcript"

    import os
    if os.path.exists(tmp_path.name):
        os.remove(tmp_path.name)
