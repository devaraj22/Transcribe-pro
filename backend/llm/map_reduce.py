from typing import List
from .client import llm_complete

CHUNK_WORD_LIMIT = 1500


def chunk_text(text: str, max_words: int = CHUNK_WORD_LIMIT):
    words = text.split()
    chunks = []
    current = []
    for word in words:
        current.append(word)
        if len(current) >= max_words:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def map_reduce_summary(text: str) -> str:
    chunks = chunk_text(text)
    partial_summaries = []
    for chunk in chunks:
        prompt = f"Summarize the following meeting transcript chunk in a concise paragraph:\n\n{chunk}\n\nSummary:"
        partial_summaries.append(llm_complete(prompt, task="summarize", max_tokens=512))
    combined = "\n\n".join(partial_summaries)
    final_prompt = f"Combine the following partial summaries into one coherent meeting summary:\n\n{combined}\n\nFinal summary:"
    return llm_complete(final_prompt, task="summarize", max_tokens=512)


def map_reduce_action_items(text: str) -> str:
    chunks = chunk_text(text)
    partial_results = []
    for chunk in chunks:
        prompt = f"Extract a short list of action items and decisions from the following meeting transcript chunk:\n\n{chunk}\n\nOutput a numbered list:" 
        partial_results.append(llm_complete(prompt, task="action_items", max_tokens=256))
    combined = "\n\n".join(partial_results)
    final_prompt = f"Combine the extracted action items and decisions into a deduplicated numbered list:\n\n{combined}\n\nList:" 
    return llm_complete(final_prompt, task="action_items", max_tokens=256)
