from fastapi import APIRouter, HTTPException
from backend.app.core.config import settings
from backend.app.schemas.rag import RAGRequest, RAGResponse
from backend.services.faiss_service import search_vector_index
from backend.services.ollama_service import _call_ollama

router = APIRouter()


def build_context_block(relevant_chunks: list[str], max_chars: int = 2500) -> str:
    """Trim the retrieved context so Ollama receives a bounded prompt."""
    context_parts: list[str] = []
    used_chars = 0

    for chunk in relevant_chunks:
        chunk_text = chunk.strip()
        if not chunk_text:
            continue
        next_len = used_chars + len(chunk_text) + 2
        if next_len > max_chars and context_parts:
            break
        context_parts.append(chunk_text)
        used_chars = next_len

    if not context_parts:
        return ""

    return "\n\n---\n\n".join(context_parts)


@router.post("/ask", response_model=RAGResponse)
async def ask_question(request: RAGRequest):
    """
    Retrieves relevant document chunks via FAISS and generates an answer using Ollama.
    """
    try:
        # 1. Retrieve a small, bounded set of relevant chunks from the local FAISS index
        relevant_chunks = search_vector_index(request.job_id, request.question, top_k=max(2, settings.RAG_TOP_K))

        # Check if the document hasn't been indexed yet
        if not relevant_chunks or "No index found" in relevant_chunks[0]:
            raise HTTPException(status_code=404, detail="Index not found. Please wait for the document to finish processing.")

        # 2. Build a bounded context for the LLM so the request stays fast
        context = build_context_block(relevant_chunks, max_chars=2400)
        if not context:
            context = "No relevant transcript context found."

        system_prompt = (
            "You are a meeting-assistant that answers from the provided transcript. "
            "Use the context first, summarise it in a short, natural answer, and if the answer is not present, "
            "say clearly that the transcript does not contain enough information to answer. "
            "Do not invent facts."
        )

        prompt = (
            f"Transcript context:\n\n{context}\n\n"
            f"Question: {request.question}\n\n"
            "Answer briefly and directly."
        )

        # 3. Generate the answer using your local Qwen/Ollama model
        answer, is_error = await _call_ollama(prompt, system_prompt=system_prompt)
        if is_error:
            fallback_answer = (
                "The local AI model is currently unavailable or timed out. "
                "Please try again after Ollama finishes loading the model."
            )
            return {
                "answer": fallback_answer,
                "sources": relevant_chunks,
            }

        return {
            "answer": answer,
            "sources": relevant_chunks
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Engine Error: {str(e)}")