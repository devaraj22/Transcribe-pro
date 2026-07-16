
from fastapi import APIRouter
from backend.app.api.v1.endpoints import process, enhance, rag, report, history

# Initialize the main router
api_router = APIRouter()


# Attach the process endpoint (Speech-to-Text)
api_router.include_router(process.router, prefix="/process", tags=["Processing"])

# Attach the enhance endpoint (Ollama Summaries & Actions)
api_router.include_router(enhance.router, prefix="/enhance", tags=["Enhancement"])

# Attach the RAG endpoint (FAISS + Ollama Chat)
api_router.include_router(rag.router, prefix="/rag", tags=["RAG Document Chat"])

# Attach the Report endpoint
api_router.include_router(report.router, prefix="/report", tags=["PDF Generation"])

# Attach the History endpoint
api_router.include_router(history.router, prefix="/history", tags=["History"])

@api_router.get("/ping")
async def ping():
    """A simple test endpoint inside the v1 router."""
    return {"message": "v1 Router is active!"}