# Этот файл выполняет семантический поиск релевантных фрагментов в ChromaDB.

from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError

from app.rag.embeddings import EmbeddingClient
from app.services.lead_extractor import normalize_air_conditioner_text


class KnowledgeIndexError(RuntimeError):
    """Ошибка отсутствующего или недоступного индекса базы знаний."""


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Описывает найденный фрагмент базы знаний и его источник."""
    content: str
    source: str
    distance: float


class KnowledgeRetriever:
    """Выполняет семантический поиск по коллекции ChromaDB."""

    def __init__(
        self,
        chroma_path: Path,
        collection_name: str,
        embedding_client: EmbeddingClient,
        max_distance: float,
    ) -> None:
        """Открывает существующую коллекцию и сохраняет параметры поиска."""
        self._embedding_client = embedding_client
        self._max_distance = max_distance
        client = chromadb.PersistentClient(path=str(chroma_path))

        try:
            self._collection = client.get_collection(collection_name)
        except NotFoundError as exc:
            raise KnowledgeIndexError(
                "Индекс базы знаний не найден. "
                "Запустите python scripts/ingest_knowledge.py."
            ) from exc

    def retrieve(
        self,
        query: str,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """Возвращает от трех до пяти релевантных фрагментов."""
        if not 3 <= limit <= 5:
            raise ValueError("Количество фрагментов должно быть от 3 до 5.")

        normalized_query = normalize_air_conditioner_text(query)
        query_embedding = self._embedding_client.embed_query(normalized_query)
        available_chunks = self._collection.count()
        if available_chunks == 0:
            return []

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(limit, available_chunks),
            include=["documents", "metadatas", "distances"],
        )

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        chunks: list[RetrievedChunk] = []
        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances,
            strict=True,
        ):
            if document is None or distance is None:
                continue
            if float(distance) > self._max_distance:
                continue

            chunks.append(
                RetrievedChunk(
                    content=document,
                    source=str((metadata or {}).get("source", "unknown")),
                    distance=float(distance),
                )
            )

        return chunks
