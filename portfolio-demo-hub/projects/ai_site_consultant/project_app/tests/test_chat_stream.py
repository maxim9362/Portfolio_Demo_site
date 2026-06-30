# Этот файл проверяет освобождение ресурсов после завершения SSE-потока чата.

import asyncio
import unittest

from app.api.chat import _as_sse


class TrackingSession:
    """Фиксирует вызов закрытия тестовой сессии базы данных."""

    def __init__(self) -> None:
        """Создает открытую тестовую сессию."""
        self.closed = False

    def close(self) -> None:
        """Отмечает освобождение соединения."""
        self.closed = True


class ChatStreamTests(unittest.TestCase):
    """Проверяет закрытие DB-сессии после потокового ответа."""

    def test_sse_stream_closes_database_session(self) -> None:
        """Проверяет закрытие сессии после события done."""
        database_session = TrackingSession()

        async def answer_stream():
            """Возвращает один тестовый фрагмент ответа."""
            yield "Ответ"

        async def collect() -> list[str]:
            """Полностью считывает события SSE."""
            return [
                event
                async for event in _as_sse(
                    answer_stream(),
                    database_session,
                )
            ]

        events = asyncio.run(collect())

        self.assertTrue(database_session.closed)
        self.assertTrue(any("event: done" in event for event in events))


if __name__ == "__main__":
    unittest.main()
