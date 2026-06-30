# Этот файл запускает полную индексацию Markdown-базы знаний в ChromaDB.

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.rag.embeddings import (  # noqa: E402
    EmbeddingClient,
    EmbeddingError,
)
from app.rag.ingestion import KnowledgeIngestionError, ingest_knowledge  # noqa: E402


def main() -> None:
    """Запускает полную индексацию локальной базы знаний."""
    embedding_client = EmbeddingClient(
        model_name=settings.embedding_model_name,
    )
    result = ingest_knowledge(
        knowledge_dir=settings.knowledge_dir,
        chroma_path=settings.chroma_path,
        collection_name=settings.chroma_collection,
        embedding_client=embedding_client,
    )
    print(
        "Индексация завершена: "
        f"файлов — {result.document_count}, чанков — {result.chunk_count}."
    )


if __name__ == "__main__":
    try:
        main()
    except (EmbeddingError, KnowledgeIngestionError) as exc:
        raise SystemExit(f"Ошибка индексации: {exc}") from exc
