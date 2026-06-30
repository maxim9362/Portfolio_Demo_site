# Этот файл содержит API-маршрут переиндексации Markdown-базы знаний.

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.rag.embeddings import EmbeddingClient, EmbeddingError
from app.rag.ingestion import KnowledgeIngestionError, ingest_knowledge
from app.schemas.ingest import IngestResponse


router = APIRouter(tags=["knowledge"])


@router.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    """Переиндексирует Markdown-базу знаний в ChromaDB."""
    try:
        result = ingest_knowledge(
            knowledge_dir=settings.knowledge_dir,
            chroma_path=settings.chroma_path,
            collection_name=settings.chroma_collection,
            embedding_client=EmbeddingClient(
                model_name=settings.embedding_model_name,
            ),
        )
    except (EmbeddingError, KnowledgeIngestionError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return IngestResponse(
        status="ok",
        document_count=result.document_count,
        chunk_count=result.chunk_count,
    )
