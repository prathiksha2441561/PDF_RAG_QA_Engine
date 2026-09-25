from fastapi import APIRouter
from backend.app.config import settings
from backend.app.services.vector_store import vector_store
from backend.app.models.database import db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint returning system status, loaded configuration,
    and indexed vector store counts.
    """
    total_docs = len(db.list_documents())
    vector_count = vector_store.count()
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "vector_store_type": settings.VECTOR_STORE_TYPE,
        "total_documents": total_docs,
        "vector_records_count": vector_count,
        "security_defense_enabled": settings.ENABLE_INJECTION_DEFENSE
    }
