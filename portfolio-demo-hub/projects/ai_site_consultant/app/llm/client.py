# Этот файл содержит асинхронный клиент потоковой генерации ответов через Gemini API.

from collections.abc import AsyncIterator, Sequence

from google import genai
from google.genai import errors, types


class LLMConfigurationError(RuntimeError):
    """Ошибка обязательных настроек Gemini-клиента."""


class LLMResponseError(RuntimeError):
    """Ошибка отсутствующего или некорректного ответа Gemini."""


class LLMClient:
    """Инкапсулирует потоковые запросы к Gemini API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_model: str = "",
    ) -> None:
        """Проверяет настройки и сохраняет параметры Gemini."""
        normalized_api_key = api_key.strip()
        if not normalized_api_key:
            raise LLMConfigurationError(
                "Переменная окружения GEMINI_API_KEY не задана."
            )

        normalized_model = model.strip()
        if not normalized_model:
            raise LLMConfigurationError(
                "Переменная окружения GEMINI_MODEL не задана."
            )

        self._api_key = normalized_api_key
        self._model = normalized_model
        self._fallback_model = fallback_model.strip()

    async def stream_answer(
        self,
        system_prompt: str,
        messages: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Потоково генерирует ответ с резервной моделью при сбое."""
        contents = [
            types.Content(
                role=self._to_gemini_role(message["role"]),
                parts=[types.Part.from_text(text=message["content"])],
            )
            for message in messages
        ]

        models = [self._model]
        if self._fallback_model and self._fallback_model != self._model:
            models.append(self._fallback_model)

        async with genai.Client(api_key=self._api_key).aio as client:
            for model_index, model in enumerate(models):
                received_text = False
                try:
                    response_stream = await client.models.generate_content_stream(
                        model=model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                        ),
                    )

                    async for chunk in response_stream:
                        text = chunk.text
                        if not text:
                            continue

                        received_text = True
                        yield text
                except errors.ServerError as exc:
                    can_use_fallback = (
                        exc.code == 503
                        and not received_text
                        and model_index + 1 < len(models)
                    )
                    if can_use_fallback:
                        continue
                    raise LLMResponseError(
                        "Сервис Gemini временно перегружен. "
                        "Повторите запрос через несколько секунд."
                    ) from exc
                except errors.ClientError as exc:
                    if exc.code == 429:
                        raise LLMResponseError(
                            "Gemini временно ограничил количество запросов. "
                            "Повторите попытку немного позже."
                        ) from exc
                    raise LLMResponseError(
                        "Gemini отклонил запрос. Проверьте API-ключ и модель."
                    ) from exc

                if received_text:
                    return

        raise LLMResponseError("Gemini API не вернул текстовый ответ.")

    @staticmethod
    def _to_gemini_role(role: str) -> str:
        """Преобразует внутреннюю роль сообщения в формат Gemini."""
        if role == "assistant":
            return "model"
        if role == "user":
            return "user"
        raise ValueError(f"Неподдерживаемая роль сообщения: {role}")
