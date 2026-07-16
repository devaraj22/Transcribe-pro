from fastapi import APIRouter, HTTPException
from backend.app.schemas.rag import RAGRequest, RAGResponse
from backend.services.faiss_service import search_vector_index
from backend.services.ollama_service import _call_ollama

router = APIRouter()

@router.post("/ask", response_model=RAGResponse)
async def ask_question(request: RAGRequest):
    """
    Retrieves relevant document chunks via FAISS and generates an answer using Ollama.
    """
    try:
        # 1. Retrieve the most relevant chunks from the local FAISS index
        relevant_chunks = search_vector_index(request.job_id, request.question, top_k=3)
        
        # Check if the document hasn't been indexed yet
        if not relevant_chunks or "No index found" in relevant_chunks[0]:
            raise HTTPException(status_code=404, detail="Index not found. Please wait for the document to finish processing.")

        # 2. Build the context for the LLM
        context = "\n\n---\n\n".join(relevant_chunks)
        
        system_prompt = (
            "You are a highly accurate meeting assistant. You must answer the user's question "
            "based STRICTLY on the context provided below. If the answer is not contained in "
            "the context, say 'I cannot find the answer to that in the transcript.' Do not hallucinate."
        )
        
        prompt = f"Context from transcript:\n\n{context}\n\nUser Question: {request.question}"
        
        # 3. Generate the answer using your local Qwen/Ollama model
        answer = await _call_ollama(prompt, system_prompt=system_prompt)
        
        return {
            "answer": answer,
            "sources": relevant_chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Engine Error: {str(e)}")