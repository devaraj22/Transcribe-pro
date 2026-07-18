"""
faiss_service.py
================
Local FAISS vector index for Retrieval-Augmented Generation (RAG).

Pipeline:
  1. Chunk the transcript text using the existing text_chunker module
     (speaker-turn aware, with paragraph overlap).
  2. Embed chunks with a sentence-transformer model.
  3. Store index + chunk manifest on disk under VECTOR_DIR/{job_id}/.
  4. On query: embed question → FAISS search → return top-k chunks.
     Falls back to keyword overlap if semantic search returns nothing.
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

# Use a reliable, locally-runnable model that does NOT require trust_remote_code.
# all-MiniLM-L6-v2 is small (22 MB), fast, and produces strong 384-dim vectors.
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
    """
    Chunk transcript text intelligently:

    1. Split on speaker-turn boundaries (lines starting with "Speaker N:").
    2. Within each turn, further split by double-newline paragraphs.
    3. Merge short chunks together until they approach max_chars.
    4. Apply a character-level overlap between adjacent chunks for context continuity.

    Args:
        transcript_text: Full transcript string.
        max_chars:       Target maximum characters per chunk.
        overlap_chars:   Characters of overlap between consecutive chunks.

    Returns:
        List of non-empty text chunks.
    """
    if not transcript_text or not transcript_text.strip():
        return []

    # Split into lines, preserving speaker label prefixes
    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]

    # Group into "paragraphs" — each speaker turn is a paragraph
    paragraphs: List[str] = []
    current: List[str] = []
    for line in lines:
        # A new speaker turn starts a new paragraph
        if re.match(r"^Speaker\s+\d+:", line, re.IGNORECASE) and current:
            paragraphs.append(" ".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))

    # Merge short paragraphs into chunks up to max_chars
    chunks: List[str] = []
    buffer = ""

    for para in paragraphs:
        if not para:
            continue
        if buffer and len(buffer) + len(para) + 1 > max_chars:
            chunks.append(buffer.strip())
            # Overlap: carry the last overlap_chars of the previous chunk
            buffer = buffer[-overlap_chars:].strip() + " " + para if overlap_chars else para
        else:
            buffer = (buffer + " " + para).strip() if buffer else para

    if buffer.strip():
        chunks.append(buffer.strip())

    # Filter out very short artefacts
    return [c for c in chunks if len(c) > 20]


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def create_vector_index(job_id: str, transcript_text: str) -> bool:
    """
    Chunk a transcript, embed chunks, and persist a FAISS index to disk.

    Args:
        job_id:         Unique job identifier used as directory name.
        transcript_text: Full transcript string (speaker-turn format or plain).

    Returns:
        True on success, False if nothing was indexed.
    """
    if not (transcript_text or "").strip():
        print(f"⚠️ RAG: empty transcript for job [{job_id}], skipping index.")
        return False

    chunks = _smart_chunk(transcript_text)
    if not chunks:
        print(f"⚠️ RAG: no chunks produced for job [{job_id}], skipping index.")
        return False

    print(f"📚 RAG: indexing {len(chunks)} chunks for job [{job_id}]…")
    model = get_embedding_model()

    embeddings = model.encode(chunks, show_progress_bar=False, normalize_embeddings=True)
    embeddings_array = np.asarray(embeddings, dtype="float32")
    embeddings_array = np.atleast_2d(embeddings_array)
    
    # Force C-contiguous memory layout for FAISS stability
    embeddings_array = np.ascontiguousarray(embeddings_array)
    
    # IndexFlatIP works with normalised vectors → cosine similarity via inner product
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_array)

    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    faiss.write_index(index, os.path.join(job_dir, "index.faiss"))

    # Persist chunks so we can reconstruct the original text on search
    with open(os.path.join(job_dir, "chunks.txt"), "w", encoding="utf-8") as f:
        for chunk in chunks:
            # Encode newlines within a chunk so each line is exactly one chunk
            f.write(chunk.replace("\n", "⏎") + "\n")

    print(f"✅ RAG: index saved to {job_dir}")
    return True


def _keyword_fallback(chunks: List[str], question: str, top_k: int) -> List[str]:
    """Return chunks that share the most content words with *question*."""
    if not chunks:
        return []
    terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]+", question) if len(t) > 2]
    if not terms:
        return chunks[:top_k]

    scored: List[tuple] = []
    for chunk in chunks:
        lower_chunk = chunk.lower()
        score = sum(1 for t in set(terms) if t in lower_chunk)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def search_vector_index(job_id: str, question: str, top_k: Optional[int] = None) -> List[str]:
    """
    Search the FAISS index for chunks relevant to *question*.

    Args:
        job_id:   Job to search.
        question: User's natural-language question.
        top_k:    Number of results to return (defaults to settings.RAG_TOP_K).

    Returns:
        List of the most relevant transcript chunks.
        Returns a single-item list with an error message if the index is missing.
    """
    if top_k is None:
        top_k = settings.RAG_TOP_K

    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    index_path = os.path.join(job_dir, "index.faiss")
    chunks_path = os.path.join(job_dir, "chunks.txt")

    if not os.path.exists(index_path) or not os.path.exists(chunks_path):
        return []  # Caller checks for empty list

    model = get_embedding_model()

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = [line.rstrip("\n").replace("⏎", "\n") for line in f if line.strip()]

    if not chunks:
        return []

    index = faiss.read_index(index_path)

    question_vector = model.encode([question], normalize_embeddings=True)
    question_array = np.asarray(question_vector, dtype="float32")
    question_array = np.atleast_2d(question_array)
    
    # Ensure question array is also C-contiguous for search
    question_array = np.ascontiguousarray(question_array)

    k = min(top_k, len(chunks))
    distances, indices = index.search(question_array, k)

    results: List[str] = []
    for idx in indices[0]:
        if idx != -1 and idx < len(chunks):
            results.append(chunks[idx])

    # Fallback / augment with keyword overlap
    if not results:
        return _keyword_fallback(chunks, question, top_k)

    if len(results) < max(2, top_k):
        seen = set(results)
        for kw_chunk in _keyword_fallback(chunks, question, top_k):
            if kw_chunk not in seen:
                results.append(kw_chunk)
                seen.add(kw_chunk)
                if len(results) >= top_k:
                    break

    return results


def index_exists(job_id: str) -> bool:
    """Return True if a FAISS index already exists for *job_id*."""
    job_dir = os.path.join(settings.VECTOR_DIR, job_id)
    return (
        os.path.exists(os.path.join(job_dir, "index.faiss"))
        and os.path.exists(os.path.join(job_dir, "chunks.txt"))
    )