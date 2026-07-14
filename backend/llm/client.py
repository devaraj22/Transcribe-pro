from typing import Dict, Optional
import httpx

from ..config import settings

LLM_URL = "http://127.0.0.1:11434/v1"


def llm_complete(prompt: str, task: str, max_tokens: int = 1024) -> str:
    thinking_tasks = {task.strip() for task in settings.LLM_THINKING_MODE_TASKS.split(",")}
    is_thinking = task in thinking_tasks
    temperature = 0.6 if is_thinking else 0.7
    top_p = 0.95 if is_thinking else 0.8
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": False,
    }
    with httpx.Client(timeout=300) as client:
        response = client.post(f"{LLM_URL}/completions", json=payload)
        response.raise_for_status()
        data = response.json()
    if "choices" in data and data["choices"]:
        return data["choices"][0]["text"].strip()
    return data.get("text", "").strip()


def llm_embed(text: str) -> list:
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": text,
    }
    with httpx.Client(timeout=120) as client:
        response = client.post(f"{LLM_URL}/embeddings", json=payload)
        response.raise_for_status()
        result = response.json()
    embeddings = [item["embedding"] for item in result.get("data", [])]
    if embeddings:
        return embeddings[0]
    raise RuntimeError("Failed to generate embedding")
