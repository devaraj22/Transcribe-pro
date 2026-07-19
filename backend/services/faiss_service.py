"""
faiss_service.py
================
Local FAISS vector index for Retrieval-Augmented Generation (RAG).
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Embedding model singleton
# ---------------------------------------------------------------------------
_embedding_model: Optional[SentenceTransformer] = None
_EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_embedding_model() -> SentenceTransformer:
    """Lazy-load the sentence embedding model once per process."""
    global _embedding_model
    if _embedding_model is None:
        print(f"⏳ Loading embedding model: {_EMBED_MODEL_NAME}")
        _embedding_model = SentenceTransformer(_EMBED_MODEL_NAME)
        print("✅ Embedding model ready.")
    return _embedding_model


# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------

def _smart_chunk(transcript_text: str, max_chars: int = 800, overlap_chars: int = 120) -> List[str]:
    """Chunks transcript text intelligently with speaker-turn awareness."""
    if not transcript_text or not transcript_text.strip():
        return []

    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
    paragraphs: List[str] = []
    current: List[str] = []
    
    for line in lines:
        if re.match(r"^Speaker\s+\d+:", line, re.IGNORECASE) and current:
            paragraphs.append(" ".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))

    chunks: List[str] = []
    buffer = ""
    for para in paragraphs:
        if not para: continue
        if buffer and len(buffer) + len(para) + 1 > max_chars:
            chunks.append(buffer.strip())
            buffer = buffer[-overlap_chars:].strip() + " " + para if overlap_chars else para
        else:
            buffer = (buffer + " " + para).strip() if buffer else para

    if buffer.strip():
        chunks.append(buffer.strip())

    return [c for c in chunks if len(c) > 20]


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def create_vector_index(job_id: str, transcript_text: str) -> bool:
    """Creates a hardened, C-contiguous FAISS index."""
    if not (transcript_text or "").strip():
        return False

    chunks = _smart_chunk(transcript_text)
    if not chunks:
        return False

    print(f"📚 RAG: Indexing {len(chunks)} chunks for {job_id}…")
    model = get_embedding_model()

    # 1. Generate embeddings
    embeddings = model.encode(chunks, show_progress_bar=False, normalize_embeddings=True)
    
    # 2. Hardened conversion to 2D numpy array
    embeddings_array = np.array(embeddings, dtype="float32")
    if embeddings_array.ndim == 1:
        embeddings_array = embeddings_array.reshape(1, -1)
    
    # 3. Force C-contiguous memory layout (Mandatory for FAISS)
    embeddings_array = np.ascontiguousarray(embeddings_array)
    
    # 4. Initialize and populate
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatIP(dimension)
    
    try:
        index.add(embeddings_array)
    except Exception as e:
        print(f"❌ FAISS Critical Error: {e}")
        return False

    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(job_dir, "index.faiss"))

    with open(os.path.join(job_dir, "chunks.txt"), "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.replace("\n", "⏎") + "\n")

    return True


def search_vector_index(job_id: str, question: str, top_k: Optional[int] = None) -> List[str]:
    """Searches the index with safety checks."""
    top_k = top_k or settings.RAG_TOP_K
    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    index_path = os.path.join(job_dir, "index.faiss")
    chunks_path = os.path.join(job_dir, "chunks.txt")

    if not os.path.exists(index_path) or not os.path.exists(chunks_path):
        return []

    model = get_embedding_model()
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = [line.rstrip("\n").replace("⏎", "\n") for line in f if line.strip()]

    index = faiss.read_index(index_path)
    
    # Process question
    q_vec = model.encode([question], normalize_embeddings=True)
    q_arr = np.ascontiguousarray(np.array(q_vec, dtype="float32"))

    _, indices = index.search(q_arr, min(top_k, len(chunks)))
    
    results = [chunks[idx] for idx in indices[0] if idx != -1]
    return results

def index_exists(job_id: str) -> bool:
    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    return os.path.exists(os.path.join(job_dir, "index.faiss"))