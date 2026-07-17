import os
import re
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings

# Global variable to hold the embedding model in memory
_embedding_model = None


def get_embedding_model():
    """Lazy loads the requested embedding model once per process."""
    global _embedding_model
    if _embedding_model is None:
        print("⏳ Loading SentenceTransformer for local RAG...")
        _embedding_model = SentenceTransformer("jinaai/jina-embeddings-v3")
    return _embedding_model

def create_vector_index(job_id: str, transcript_text: str):
    """
    Chunks a long transcript, converts it to vectors, and saves it locally.
    """
    if not transcript_text.strip():
        return False
        
    model = get_embedding_model()
    
    # Simple chunking: split by paragraphs or hard limits
    # (We can wire this up to your text_chunker.py module later!)
    raw_chunks = transcript_text.split("\n\n")
    chunks = [c.strip() for c in raw_chunks if len(c.strip()) > 20]
    
    if not chunks:
        return False

    print(f"📚 Indexing {len(chunks)} chunks for Job [{job_id}]...")
    
    # Convert text chunks into a mathematical vector space
    embeddings = model.encode(chunks)
    embeddings_array = np.asarray(embeddings, dtype='float32')
    if embeddings_array.ndim == 1:
        embeddings_array = embeddings_array.reshape(1, -1)
    elif embeddings_array.ndim == 0:
        embeddings_array = embeddings_array.reshape(1, 1)
    embeddings_array = np.atleast_2d(embeddings_array)
    
    # Initialize Meta's FAISS index for high-speed similarity search
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    
    # Save the index and the raw chunks to the configured vector_store directory
    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    faiss.write_index(index, os.path.join(job_dir, "index.faiss"))
    
    # Save the text map so we know which text belongs to which vector
    with open(os.path.join(job_dir, "chunks.txt"), "w", encoding="utf-8") as f:
        for chunk in chunks:
            # We replace newlines in the chunk with spaces so each line is one chunk
            f.write(chunk.replace("\n", " ") + "\n")
            
    return True

def _keyword_fallback(chunks: list[str], question: str, top_k: int) -> list[str]:
    """Return chunks that share important words with the question."""
    if not chunks:
        return []

    terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9]+", question) if len(term) > 2]
    if not terms:
        return chunks[:top_k]

    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        chunk_text = chunk.lower()
        score = sum(1 for term in set(terms) if term in chunk_text)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def search_vector_index(job_id: str, question: str, top_k: int | None = None) -> list[str]:
    """
    Takes a user's question, searches the FAISS index, and returns the most relevant transcript chunks.
    """
    if top_k is None:
        top_k = settings.RAG_TOP_K
    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    index_path = os.path.join(job_dir, "index.faiss")
    chunks_path = os.path.join(job_dir, "chunks.txt")
    
    if not os.path.exists(index_path) or not os.path.exists(chunks_path):
        return ["No index found for this document. Please process the file first."]
        
    model = get_embedding_model()
    
    # Read the chunks back into memory
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = f.read().splitlines()
        
    # Load the FAISS index
    index = faiss.read_index(index_path)
    
    # Convert the user's question into a vector
    question_vector = model.encode([question])
    question_array = np.asarray(question_vector, dtype='float32')
    if question_array.ndim == 1:
        question_array = question_array.reshape(1, -1)
    elif question_array.ndim == 0:
        question_array = question_array.reshape(1, 1)
    question_array = np.atleast_2d(question_array)
    
    # Search the index for the closest matches
    distances, indices = index.search(question_array, top_k)
    
    # Retrieve the actual text for the winning indices
    results = []
    for idx in indices[0]:
        if idx != -1 and idx < len(chunks):
            results.append(chunks[idx])

    # Fallback to keyword overlap if semantic search returns nothing useful
    if not results:
        return _keyword_fallback(chunks, question, top_k)

    # If semantic search found only weakly related chunks, try keyword overlap too
    if len(results) < max(2, top_k):
        keyword_hits = _keyword_fallback(chunks, question, top_k)
        if keyword_hits:
            # Prefer unique chunks and keep the semantic ones first when available
            seen = {chunk for chunk in results}
            for chunk in keyword_hits:
                if chunk not in seen:
                    results.append(chunk)
                    seen.add(chunk)
                    if len(results) >= top_k:
                        break
    
    return results