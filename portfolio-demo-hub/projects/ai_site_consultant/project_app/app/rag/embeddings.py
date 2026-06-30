# Этот файл создает локальные embeddings с помощью sentence-transformers.

from collections.abc import Sequence
from functools import lru_cache
from threading import Lock

from sentence_transformers import SentenceTransformer


_encode_lock = Lock()


class EmbeddingError(RuntimeError):
    """Базовая ошибка локального сервиса embeddings."""


class EmbeddingConfigurationError(EmbeddingError):
    """Ошибка конфигурации локальной embedding-модели."""


class EmbeddingModelError(EmbeddingError):
    """Ошибка загрузки или запуска локальной embedding-модели."""


class EmbeddingClient:
    """Создает локальные векторные представления текста."""

    def __init__(self, model_name: str) -> None:
        """Загружает указанную sentence-transformers модель."""
        normalized_model_name = model_name.strip()
        if not normalized_model_name:
            raise EmbeddingConfigurationError(
                "Переменная окружения EMBEDDING_MODEL_NAME не задана."
            )

        try:
            self._model = _load_model(normalized_model_name)
        except Exception as exc:
            raise EmbeddingModelError(
                f"Не удалось загрузить локальную embedding-модель "
                f"{normalized_model_name!r}."
            ) from exc

    def embed_texts(
        self,
        texts: Sequence[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Кодирует набор непустых текстов в нормализованные векторы."""
        if batch_size < 1:
            raise ValueError("Размер пакета embeddings должен быть положительным.")

        normalized_texts = [text.strip() for text in texts]
        if any(not text for text in normalized_texts):
            raise ValueError("Нельзя создать embedding для пустого текста.")
        if not normalized_texts:
            return []

        with _encode_lock:
            vectors = self._model.encode(
                normalized_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Создает вектор для одного поискового запроса."""
        return self.embed_texts([query], batch_size=1)[0]


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    """Кэширует тяжелую embedding-модель внутри worker-процесса."""
    return SentenceTransformer(model_name)
