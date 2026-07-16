import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings

# Global variable to hold the embedding model in memory
_embedding_model = None

def get_embedding_model():
    """Lazy loads the lightweight text embedding model."""
    global _embedding_model
    if _embedding_model is None:
        print("⏳ Loading SentenceTransformer for local RAG...")
        # all-MiniLM-L6-v2 is extremely fast, accurate, and tiny (~80MB)
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
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
    
    # Initialize Meta's FAISS index for high-speed similarity search
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype('float32'))
    
    # Save the index and the raw chunks to your local vector_store directory
    job_dir = os.path.join("vector_store", job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    faiss.write_index(index, os.path.join(job_dir, "index.faiss"))
    
    # Save the text map so we know which text belongs to which vector
    with open(os.path.join(job_dir, "chunks.txt"), "w", encoding="utf-8") as f:
        for chunk in chunks:
            # We replace newlines in the chunk with spaces so each line is one chunk
            f.write(chunk.replace("\n", " ") + "\n")
            
    return True

def search_vector_index(job_id: str, question: str, top_k: int = 3) -> list[str]:
    """
    Takes a user's question, searches the FAISS index, and returns the most relevant transcript chunks.
    """
    job_dir = os.path.join("vector_store", job_id)
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
    
    # Search the index for the closest matches
    distances, indices = index.search(np.array(question_vector).astype('float32'), top_k)
    
    # Retrieve the actual text for the winning indices
    results = []
    for idx in indices[0]:
        if idx != -1 and idx < len(chunks):
            results.append(chunks[idx])
            
    return results