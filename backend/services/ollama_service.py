"""
ollama_service.py
=================
In-process local LLM inference via llama-cpp-python (GGUF), used for
Summary / Action Items / RAG answer generation.

NOTE ON THE FILENAME/MODULE NAME: this used to be a thin HTTP client for a
separately-running `ollama serve` process. That setup had Ollama's own
`llama-server` child process crash with a segfault under concurrent CPU-only
load (see git history). We moved inference in-process via llama-cpp-python
instead — no separate server to manage or crash silently; failures now
surface as ordinary Python exceptions we can catch. The module keeps its
original name and all original public function signatures
(``generate_summary``, ``extract_action_items``, ``_call_ollama``) so no
caller (enhance.py, rag.py, tests) needed to change.

All public functions still return ``(result, is_error: bool)`` tuples so
callers can display helpful fallback messages without raising exceptions.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Optional

from backend.app.core.config import settings

# Serialize calls to the local model. Generation is CPU-bound and runs in a
# worker thread (see _call_ollama below); a lock keeps memory/CPU usage
# predictable by ensuring only one generation runs at a time, rather than
# letting concurrent requests pile up and exhaust RAM.
_llm_lock = asyncio.Lock()

# Lazily-loaded singleton — loading a GGUF model takes real time/memory, so
# we only do it once, on first use, not at import time.
_llm_instance: Optional[Any] = None
_llm_load_error: Optional[str] = None


def _get_llm() -> Any:
    """Load (once) and return the in-process llama-cpp-python model."""
    global _llm_instance, _llm_load_error

    if _llm_instance is not None:
        return _llm_instance
    if _llm_load_error is not None:
        # Don't retry a known-bad config on every request — fail fast.
        raise RuntimeError(_llm_load_error)

    if not settings.LOCAL_LLM_MODEL_PATH:
        _llm_load_error = (
            "LOCAL_LLM_MODEL_PATH is not configured. Download a GGUF quant of "
            "your model (e.g. a Qwen3-8B-Instruct Q4_K_M .gguf) and set "
            "LOCAL_LLM_MODEL_PATH to its path in your .env."
        )
        raise RuntimeError(_llm_load_error)

    try:
        from llama_cpp import Llama
    except ImportError as exc:
        _llm_load_error = f"llama-cpp-python is not installed: {exc}"
        raise RuntimeError(_llm_load_error) from exc

    try:
        print(f"⏳ Loading local GGUF model from {settings.LOCAL_LLM_MODEL_PATH}...")
        _llm_instance = Llama(
            model_path=settings.LOCAL_LLM_MODEL_PATH,
            n_ctx=settings.LOCAL_LLM_CONTEXT_SIZE,
            n_threads=settings.LOCAL_LLM_THREADS,
            n_gpu_layers=settings.LOCAL_LLM_GPU_LAYERS,
            verbose=False,
        )
        print("✅ Local GGUF model loaded.")
        return _llm_instance
    except Exception as exc:
        _llm_load_error = f"Failed to load GGUF model: {exc}"
        raise RuntimeError(_llm_load_error) from exc


def release_llm() -> None:
    """Release the loaded model from memory (e.g. to free RAM for other steps)."""
    global _llm_instance
    _llm_instance = None


async def _call_ollama(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant.",
    num_predict: int = 512,
    temperature: float = 0.4,
    timeout: float = 60.0,
) -> tuple[str, bool]:
    """
    Core async function to run a local in-process generation.

    Args:
        prompt:        User prompt text.
        system_prompt: System / role instruction.
        num_predict:   Maximum tokens to generate (default 512 — enough for
                       a detailed RAG answer without runaway generation).
        temperature:   Sampling temperature (lower = more factual).
        timeout:       Wall-clock budget in seconds before giving up.

    Returns:
        Tuple of ``(response_text, is_error)``  where is_error is True when
        the call failed and response_text contains a human-readable error
        message.
    """

    def _generate_blocking() -> str:
        llm = _get_llm()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        completion = llm.create_chat_completion(
            messages=messages,
            max_tokens=num_predict,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.05,
        )
        return completion["choices"][0]["message"]["content"].strip()

    async with _llm_lock:
        try:
            print(f"🤖 Local LLM: generating response…")
            result = await asyncio.wait_for(
                asyncio.to_thread(_generate_blocking), timeout=timeout
            )
            result = _strip_think_tokens(result)
            return result, False

        except asyncio.TimeoutError:
            msg = (
                f"Local model generation timed out after {timeout:.0f}s. "
                "The model may be too large for this machine, or the prompt "
                "too long — try a shorter transcript or a smaller model."
            )
            print(f"❌ Local LLM timeout: {msg}")
            return msg, True

        except RuntimeError as exc:
            # Raised by _get_llm() for config/load problems — already a
            # clear, specific message.
            msg = str(exc)
            print(f"❌ Local LLM error: {msg}")
            return msg, True

        except Exception as exc:
            msg = f"Unexpected error during local generation: {exc}"
            print(f"❌ {msg}")
            return msg, True


def _strip_think_tokens(text: str) -> str:
    """
    Remove <think>…</think> blocks emitted by Qwen3 and other reasoning models
    so only the final answer is returned.
    """
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
    return await _call_ollama(prompt, system_prompt=system, num_predict=300, timeout=180.0)


async def extract_action_items(text: str) -> tuple[list[str], bool, str]:
    """
    Extract action items / tasks from meeting transcript text.

    Returns:
        ``(action_items_list, is_error, error_detail)`` — ``error_detail`` is
        the empty string when ``is_error`` is False.
    """
    if not text or len(text.strip()) < 10:
        return [], True, "Transcript is too short to extract action items from."

    truncated = text[:6000] + ("…" if len(text) > 6000 else "")

    system = (
        "You are a strict meeting-notes extraction AI. "
        "From the transcript, extract EVERY concrete action item, task, next step, "
        "and important decision that was made. "
        "For each item, include the due date or deadline if one was explicitly "
        "mentioned in the transcript (e.g. 'by Friday', 'next week', 'March 5th'); "
        "if no date was mentioned, do not invent one — just state the item. "
        "Return ONLY a bulleted list using the '-' character, one item per line, "
        "in the form: '- <item> [Due: <date>]' (omit the [Due: ...] part entirely "
        "if no date was mentioned). "
        "Do not add any other text, headings, or introductions."
    )
    prompt = f"Meeting transcript:\n\n{truncated}\n\nAction items and key decisions (with due dates where mentioned):"

    raw, is_error = await _call_ollama(prompt, system_prompt=system, num_predict=400, timeout=180.0)
    if is_error:
        # raw already contains the real, specific reason from _call_ollama
        # (e.g. "Ollama is not running..."); don't discard it.
        return [], True, raw

    items: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith(("-", "*", "•")):
            items.append(line.lstrip("-*• ").strip())
        elif line and len(items) == 0:
            # Model didn't follow bullet format — treat non-empty lines as items
            if len(line) > 5:
                items.append(line)

    return items, False, ""