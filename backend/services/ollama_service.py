import httpx
from backend.app.core.config import settings


async def _call_ollama(prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> tuple[str, bool]:
    """
    Core function to communicate with the local Ollama instance asynchronously.
    Returns a tuple of (response_text, is_error) where is_error indicates if the call failed.
    """
    url = f"{settings.OLLAMA_HOST}/api/generate"
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "num_predict": 80,
            "temperature": 0.7,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "num_ctx": 2048,
        },
    }

    timeout = 20.0
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            print(f"Asking local Ollama ({payload['model']}) to process data...")
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            result = data.get("response", "").strip()
            return (result, False)  # Success

        except httpx.ConnectError:
            error_msg = f"Ollama service is not running. Please start Ollama at {settings.OLLAMA_HOST}"
            print(f"ERROR: {error_msg}")
            return (error_msg, True)  # Connection error
        except (httpx.TimeoutException, httpx.ReadTimeout):
            error_msg = "Ollama service timeout. The LLM is taking too long to respond."
            print(f"ERROR: {error_msg}")
            return (error_msg, True)  # Timeout error
        except Exception as e:
            error_msg = f"Error communicating with Ollama: {str(e)}"
            print(f"ERROR: {error_msg}")
            return (error_msg, True)  # Other errors

async def generate_summary(text: str) -> tuple[str, bool]:
    """
    Generate a summary of the provided text.
    Returns a tuple of (summary_text, is_error) where is_error indicates if generation failed.
    """
    if not text or len(text.strip()) < 10:
        return ("Error: Text is too short to summarize.", True)
    
    system = "You are a professional executive assistant. Provide a concise, highly accurate summary of the provided text."
    prompt = f"Please summarize the following meeting transcript:\n\n{text}"
    return await _call_ollama(prompt, system_prompt=system)

async def extract_action_items(text: str) -> tuple[list[str], bool]:
    """
    Extract action items from the provided text.
    Returns a tuple of (action_items_list, is_error) where is_error indicates if extraction failed.
    """
    if not text or len(text.strip()) < 10:
        return ([], True)
    
    system = "You are a strict task-extraction AI. Extract clear action items, tasks, and next steps from the text. Return ONLY a bulleted list using the '-' character. Do not include introductory text."
    prompt = f"Extract all action items from this transcript:\n\n{text}"
    
    raw_response, is_error = await _call_ollama(prompt, system_prompt=system)
    
    if is_error:
        # If there was an error communicating with Ollama, return empty list with error flag
        return ([], True)
    
    cleaned_items = []
    for line in raw_response.split("\n"):
        line = line.strip()
        if line.startswith("-") or line.startswith("*"):
            cleaned_items.append(line[1:].strip())
    
    # Check if no items were extracted (LLM didn't follow instructions)
    if not cleaned_items and raw_response:
        # Try alternative parsing: split by newlines and take non-empty lines
        for line in raw_response.split("\n"):
            line = line.strip()
            if line and len(line) > 3:  # Filter out very short lines
                cleaned_items.append(line)
    
    return (cleaned_items, is_error)