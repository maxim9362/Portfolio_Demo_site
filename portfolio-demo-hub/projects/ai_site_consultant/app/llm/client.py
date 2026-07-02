# Этот файл содержит асинхронный клиент потоковой генерации ответов через Gemini API.

from collections.abc import AsyncIterator, Sequence
import logging

from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)


class LLMConfigurationError(RuntimeError):
    """Ошибка обязательных настроек Gemini-клиента."""


class LLMResponseError(RuntimeError):
    """Ошибка отсутствующего или некорректного ответа Gemini."""


class LLMClient:
    """Инкапсулирует потоковые запросы к Gemini API."""

    def __init__(
        self,
        api_key: str | Sequence[str],
        model: str,
        fallback_model: str = "",
    ) -> None:
        """Проверяет настройки и сохраняет параметры Gemini."""
        api_keys = self._normalize_api_keys(api_key)
        if not api_keys:
            raise LLMConfigurationError(
                "Переменная окружения GEMINI_API_KEY или GEMINI_API_KEYS не задана."
            )

        normalized_model = model.strip()
        if not normalized_model:
            raise LLMConfigurationError(
                "Переменная окружения GEMINI_MODEL не задана."
            )

        self._api_keys = api_keys
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

        last_error: LLMResponseError | None = None
        for model_index, model in enumerate(models):
            for key_index, api_key in enumerate(self._api_keys):
                received_text = False
                try:
                    async with genai.Client(api_key=api_key).aio as client:
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
                    can_use_fallback = exc.code == 503 and not received_text
                    if can_use_fallback:
                        logger.warning(
                            "Gemini model %s returned 503 on key #%s.",
                            model,
                            key_index + 1,
                        )
                        last_error = LLMResponseError(
                            "Сервис Gemini временно перегружен. "
                            "Повторите запрос через несколько секунд."
                        )
                        break
                    raise LLMResponseError(
                        "Сервис Gemini временно перегружен. "
                        "Повторите запрос через несколько секунд."
                    ) from exc
                except errors.ClientError as exc:
                    can_try_next_key = (
                        exc.code in {401, 403, 429}
                        and not received_text
                        and key_index + 1 < len(self._api_keys)
                    )
                    if can_try_next_key:
                        logger.warning(
                            "Gemini key #%s failed with HTTP %s; trying next key.",
                            key_index + 1,
                            exc.code,
                        )
                        last_error = self._client_error_to_response_error(exc)
                        continue
                    raise self._client_error_to_response_error(exc) from exc

                if received_text:
                    return

            if model_index + 1 < len(models):
                continue

        if last_error:
            raise last_error

        raise LLMResponseError("Gemini API не вернул текстовый ответ.")

    @staticmethod
    def _normalize_api_keys(api_key: str | Sequence[str]) -> list[str]:
        """Нормализует один ключ или список ключей Gemini."""
        if isinstance(api_key, str):
            raw_keys = api_key.split(",")
        else:
            raw_keys = api_key
        keys: list[str] = []
        seen: set[str] = set()
        for raw_key in raw_keys:
            key = raw_key.strip()
            if key and key not in seen:
                keys.append(key)
                seen.add(key)
        return keys

    @staticmethod
    def _client_error_to_response_error(exc: errors.ClientError) -> LLMResponseError:
        """Преобразует клиентскую ошибку Gemini в понятный текст для UI."""
        if exc.code == 429:
            return LLMResponseError(
                "Gemini временно ограничил количество запросов. "
                "Повторите попытку немного позже."
            )
        if exc.code in {401, 403}:
            return LLMResponseError(
                "Gemini отклонил API-ключ. Проверьте ключи и доступ к модели."
            )
        return LLMResponseError(
            "Gemini отклонил запрос. Проверьте API-ключ и модель."
        )

    @staticmethod
    def _to_gemini_role(role: str) -> str:
        """Преобразует внутреннюю роль сообщения в формат Gemini."""
        if role == "assistant":
            return "model"
        if role == "user":
            return "user"
        raise ValueError(f"Неподдерживаемая роль сообщения: {role}")
