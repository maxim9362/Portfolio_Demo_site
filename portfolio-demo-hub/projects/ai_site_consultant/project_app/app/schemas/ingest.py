# Этот файл описывает ответ API после индексации базы знаний.

from pydantic import BaseModel


class IngestResponse(BaseModel):
    """Описывает результат переиндексации базы знаний."""
    status: str
    document_count: int
    chunk_count: int
