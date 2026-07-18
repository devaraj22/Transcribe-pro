"""
ollama_service.py
=================
Async client for the local Ollama inference server.

All public functions return ``(result, is_error: bool)`` tuples so callers
can display helpful fallback messages without raising exceptions.
"""

from __future__ import annotations

import httpx
from backend.app.core.config import settings


async def _call_ollama(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant.",
    num_predict: int = 512,
    temperature: float = 0.4,
    timeout: float = 60.0,
) -> tuple[str, bool]:
    """
    Core async function to communicate with the local Ollama instance.

    Args:
        prompt:        User prompt text.
        system_prompt: System / role instruction.
        num_predict:   Maximum tokens to generate (default 512 — enough for
                       a detailed RAG answer without runaway generation).
        temperature:   Sampling temperature (lower = more factual).
        timeout:       HTTP timeout in seconds.

    Returns:
        Tuple of ``(response_text, is_error)``  where is_error is True when
        the call failed and response_text contains a human-readable error
        message.
    """
    url = f"{settings.OLLAMA_HOST}/api/generate"
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "num_predict": num_predict,
            "temperature": temperature,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            # Give the model enough context to hold the full RAG prompt
            "num_ctx": 4096,
        },
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            print(f"🤖 Ollama ({payload['model']}): generating response…")
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            result = data.get("response", "").strip()
            # Strip <think> tokens emitted by reasoning models (Qwen3, etc.)
            result = _strip_think_tokens(result)
            return result, False

        except httpx.ConnectError:
            msg = (
                f"Ollama is not running. Start it with `ollama serve` "
                f"(expected at {settings.OLLAMA_HOST})."
            )
            print(f"❌ Ollama ConnectError: {msg}")
            return msg, True

        except (httpx.TimeoutException, httpx.ReadTimeout):
            msg = (
                "Ollama timed out. The model may still be loading — "
                "please wait a moment and try again."
            )
            print(f"❌ Ollama Timeout")
            return msg, True

        except httpx.HTTPStatusError as exc:
            msg = f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            print(f"❌ Ollama HTTP error: {msg}")
            return msg, True

        except Exception as exc:
            msg = f"Unexpected error communicating with Ollama: {exc}"
            print(f"❌ {msg}")
            return msg, True


def _strip_think_tokens(text: str) -> str:
    """
    Remove <think>…</think> blocks emitted by Qwen3 and other reasoning models
    so only the final answer is returned.
    """
    import re
    # Remove full <think>…</think> blocks (may span multiple lines)
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# High-level task functions
# ---------------------------------------------------------------------------

async def generate_summary(text: str) -> tuple[str, bool]:
    """
    Summarise meeting transcript text.

    Returns:
        ``(summary_text, is_error)``
    """
    if not text or len(text.strip()) < 10:
        return "Text is too short to summarise.", True

    # For long transcripts, trim to first 6000 chars to stay within context
    truncated = text[:6000] + ("…" if len(text) > 6000 else "")

    system = (
        "You are a professional executive assistant. "
        "Produce a concise, accurate summary of the meeting transcript in 3-6 sentences. "
        "Focus on key decisions, topics discussed, and outcomes."
    )
    prompt = f"Meeting transcript:\n\n{truncated}\n\nProvide a concise summary:"
    return await _call_ollama(prompt, system_prompt=system, num_predict=300)


async def extract_action_items(text: str) -> tuple[list[str], bool]:
    """
    Extract action items / tasks from meeting transcript text.

    Returns:
        ``(action_items_list, is_error)``
    """
    if not text or len(text.strip()) < 10:
        return [], True

    truncated = text[:6000] + ("…" if len(text) > 6000 else "")

    system = (
        "You are a strict task-extraction AI. "
        "Extract ALL concrete action items, tasks, and next steps from the transcript. "
        "Return ONLY a bulleted list using the '-' character, one item per line. "
        "Do not add any other text, headings, or introductions."
    )
    prompt = f"Meeting transcript:\n\n{truncated}\n\nAction items:"

    raw, is_error = await _call_ollama(prompt, system_prompt=system, num_predict=400)
    if is_error:
        return [], True

    items: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith(("-", "*", "•")):
            items.append(line.lstrip("-*• ").strip())
        elif line and not is_error and len(items) == 0:
            # Model didn't follow bullet format — treat non-empty lines as items
            if len(line) > 5:
                items.append(line)

    return items, False