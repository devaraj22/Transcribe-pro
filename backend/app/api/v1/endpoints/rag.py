from fastapi import APIRouter, HTTPException
from backend.app.core.config import settings
from backend.app.schemas.rag import RAGRequest, RAGResponse
from backend.services.faiss_service import search_vector_index, index_exists
from backend.services.ollama_service import _call_ollama

router = APIRouter()


def build_context_block(relevant_chunks: list[str], max_chars: int = 4000) -> str:
    """
    Assemble retrieved chunks into a bounded context block for the LLM prompt.

    Chunks are joined with a separator. The total character budget is
    max_chars — enough to hold rich context without blowing up the LLM
    context window.
    """
    context_parts: list[str] = []
    used_chars = 0

    for chunk in relevant_chunks:
        chunk_text = chunk.strip()
        if not chunk_text:
            continue
        # Include this chunk only if it fits (always include the first one)
        if context_parts and used_chars + len(chunk_text) + 8 > max_chars:
            break
        context_parts.append(chunk_text)
        used_chars += len(chunk_text) + 8  # +8 for separator

    return "\n\n---\n\n".join(context_parts)


@router.get("/status/{job_id}")
async def rag_index_status(job_id: str):
    """
    Check whether a FAISS index is ready for a given job.

    Returns:
        ``{ "indexed": bool, "job_id": str }``
    """
    return {
        "job_id": job_id,
        "indexed": index_exists(job_id),
    }


@router.post("/ask", response_model=RAGResponse)
async def ask_question(request: RAGRequest):
    """
    Retrieve relevant transcript chunks via FAISS and generate a grounded
    answer using the local Ollama model.

    Flow:
      1. Check index exists → 404 if not.
      2. Semantic + keyword search → top-k chunks.
      3. Build bounded LLM context from chunks.
      4. Call Ollama with a strict grounding system prompt.
      5. Return answer + source chunks (for frontend citation display).
    """
    try:
        # 1. Guard: index must exist
        if not index_exists(request.job_id):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No index found for job '{request.job_id}'. "
                    "The transcript may still be processing, or this job ID is invalid."
                ),
            )

        # 2. Semantic search
        relevant_chunks = search_vector_index(
            request.job_id,
            request.question,
            top_k=max(3, settings.RAG_TOP_K),
        )

        if not relevant_chunks:
            raise HTTPException(
                status_code=404,
                detail="The index exists but returned no relevant chunks for this question.",
            )

        # 3. Build LLM context (up to 4000 chars)
        context = build_context_block(relevant_chunks, max_chars=4000)
        if not context:
            context = "No relevant transcript context found."

        # 4. Build prompt
        system_prompt = (
            "You are a meeting-assistant AI. Your ONLY source of truth is the "
            "transcript excerpts provided below. Answer the user's question "
            "concisely and accurately based solely on those excerpts. "
            "If the answer cannot be determined from the transcript, say so clearly. "
            "Do NOT invent facts or use outside knowledge."
        )

        prompt = (
            f"Transcript excerpts:\n\n{context}\n\n"
            f"---\n\n"
            f"Question: {request.question}\n\n"
            "Answer (be concise and direct, 1-4 sentences max):"
        )

        # 5. Call Ollama
        answer, is_error = await _call_ollama(prompt, system_prompt=system_prompt, timeout=180.0)

        if is_error:
            # Surface a helpful fallback instead of a raw error
            fallback = (
                "The local AI model is currently unavailable. "
                "Please ensure Ollama is running (`ollama serve`) and the model is downloaded. "
                "Here are the most relevant transcript excerpts:\n\n"
                + "\n\n".join(f"• {c[:200]}…" if len(c) > 200 else f"• {c}" for c in relevant_chunks[:3])
            )
            return RAGResponse(answer=fallback, sources=relevant_chunks)

        return RAGResponse(answer=answer, sources=relevant_chunks)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Engine Error: {str(e)}")