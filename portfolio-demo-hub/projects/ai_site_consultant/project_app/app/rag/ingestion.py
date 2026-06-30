# Этот файл читает Markdown-файлы и пересобирает индекс базы знаний в ChromaDB.

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import chromadb

from app.rag.chunker import chunk_markdown
from app.rag.embeddings import EmbeddingClient


class KnowledgeIngestionError(RuntimeError):
    """Ошибка чтения или индексации базы знаний."""


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Содержит статистику выполненной индексации."""
    document_count: int
    chunk_count: int


def ingest_knowledge(
    knowledge_dir: Path,
    chroma_path: Path,
    collection_name: str,
    embedding_client: EmbeddingClient,
) -> IngestionResult:
    """Читает Markdown-файлы и полностью пересобирает коллекцию ChromaDB."""
    markdown_files = sorted(knowledge_dir.rglob("*.md"))
    if not markdown_files:
        raise KnowledgeIngestionError(
            f"В папке {knowledge_dir} не найдено Markdown-файлов."
        )

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []

    for file_path in markdown_files:
        source = file_path.relative_to(knowledge_dir).as_posix()
        category = source.split("/", maxsplit=1)[0]
        text = file_path.read_text(encoding="utf-8")

        for chunk in chunk_markdown(text):
            chunk_id = sha256(
                f"{source}:{chunk.chunk_index}:{chunk.content}".encode("utf-8")
            ).hexdigest()
            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append(
                {
                    "source": source,
                    "category": category,
                    "chunk_index": chunk.chunk_index,
                    "char_count": chunk.char_count,
                }
            )

    if not documents:
        raise KnowledgeIngestionError(
            "Markdown-файлы базы знаний не содержат текста."
        )

    embeddings = embedding_client.embed_texts(documents)
    chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path))

    collection_names = {
        collection.name
        for collection in client.list_collections()
    }
    if collection_name in collection_names:
        client.delete_collection(collection_name)

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return IngestionResult(
        document_count=len(markdown_files),
        chunk_count=len(documents),
    )
