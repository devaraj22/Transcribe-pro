def chunk_transcript(text: str, max_chars: int = 6000, overlap: int = 500) -> list[str]:
    """
    Splits a massive meeting transcript into smaller, LLM-safe chunks.
    Uses character limits and smart paragraph boundaries to ensure the 
    local model doesn't hit its context window ceiling.
    """
    if not text or not text.strip():
        return []

    # Clean the text
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # Check if adding this paragraph exceeds our safety limit
        if len(current_chunk) + len(para) + 1 > max_chars:
            # Save the current chunk
            chunks.append(current_chunk.strip())
            
            # Start the new chunk. 
            # To maintain context, we optionally carry over the last few words (overlap)
            # but for simple paragraph boundaries, we just start fresh with the current paragraph.
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"

    # Don't forget to append the very last chunk!
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

def map_reduce_summarize_prompts(chunks: list[str]) -> list[str]:
    """
    Helper function to wrap chunks in Map-Reduce prompts.
    Useful for passing to the ollama_service.py for long meetings.
    """
    prompts = []
    for i, chunk in enumerate(chunks):
        prompt = (
            f"Part {i+1} of {len(chunks)}:\n"
            f"Please summarize the key points and decisions in this section of the meeting transcript:\n\n"
            f"{chunk}"
        )
        prompts.append(prompt)
    return prompts