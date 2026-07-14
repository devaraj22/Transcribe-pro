import json
from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np

from .config import settings
from .llm.client import llm_embed, llm_complete


def index_path(job_id: str) -> Path:
    return settings.VECTOR_DIR / job_id


def build_index(chunks: List[Dict], job_id: str) -> None:
    index_dir = index_path(job_id)
    index_dir.mkdir(parents=True, exist_ok=True)
    texts = [chunk["text"] for chunk in chunks]
    embeddings = [llm_embed(text) for text in texts]
    dimension = len(embeddings[0]) if embeddings else 0
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings, dtype="float32"))
    faiss.write_index(index, str(index_dir / "index.faiss"))
    metadata = [{"chunk_id": str(i), "text": texts[i], "start": chunks[i]["start"], "end": chunks[i]["end"]} for i in range(len(chunks))]
    (index_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index(job_id: str) -> Tuple[faiss.Index, List[Dict]]:
    index_dir = index_path(job_id)
    index = faiss.read_index(str(index_dir / "index.faiss"))
    metadata = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
    return index, metadata


def retrieve(job_id: str, question: str, top_k: int = None) -> Tuple[str, List[str]]:
    if top_k is None:
        top_k = settings.RAG_TOP_K
    index, metadata = load_index(job_id)
    query_vector = llm_embed(question)
    import numpy as np
    scores, ids = index.search(np.array([query_vector], dtype="float32"), top_k)
    ids = ids[0].tolist()
    selected = [metadata[i] for i in ids if i < len(metadata)]
    context = "\n\n".join([f"Chunk {item['chunk_id']} ({item['start']:.1f}-{item['end']:.1f}): {item['text']}" for item in selected])
    prompt = f"Use the following transcript context to answer the question. Cite chunk IDs in the response if possible.\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:" 
    answer = llm_complete(prompt, task="ask", max_tokens=512)
    sources = [f"chunk_{item['chunk_id']}" for item in selected]
    return answer, sources
