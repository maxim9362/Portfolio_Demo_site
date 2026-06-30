# Этот файл разбивает Markdown по абзацам на сбалансированные фрагменты с перекрытием.

from dataclasses import dataclass
from math import ceil
import re


@dataclass(frozen=True, slots=True)
class TextChunk:
    """Представляет текстовый фрагмент для последующей индексации."""
    content: str
    char_count: int
    chunk_index: int


def chunk_markdown(
    text: str,
    min_chars: int = 1200,
    max_chars: int = 1800,
    overlap_chars: int = 250,
) -> list[TextChunk]:
    """Разбивает Markdown по абзацам на перекрывающиеся фрагменты."""
    if min_chars < 1 or max_chars < min_chars:
        raise ValueError("Некорректные границы размера чанка.")
    if not 200 <= overlap_chars <= 300:
        raise ValueError("Перекрытие должно быть от 200 до 300 символов.")
    if overlap_chars >= min_chars:
        raise ValueError("Перекрытие должно быть меньше минимального чанка.")

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text.strip())
        if paragraph.strip()
    ]
    if not paragraphs:
        return []

    normalized_text = "\n\n".join(paragraphs)
    if len(normalized_text) <= max_chars:
        return [
            TextChunk(
                content=normalized_text,
                char_count=len(normalized_text),
                chunk_index=0,
            )
        ]

    chunk_count = ceil(
        (len(normalized_text) - overlap_chars)
        / (max_chars - overlap_chars)
    )
    while chunk_count > 1:
        represented_chars = (
            len(normalized_text) + overlap_chars * (chunk_count - 1)
        )
        if represented_chars / chunk_count >= min_chars:
            break
        chunk_count -= 1

    paragraph_ends = _paragraph_end_positions(normalized_text)
    chunks: list[TextChunk] = []
    start = 0

    for chunk_index in range(chunk_count):
        remaining_chunks = chunk_count - chunk_index
        if remaining_chunks == 1:
            end = len(normalized_text)
        else:
            remaining_chars = len(normalized_text) - start
            future_chunks = remaining_chunks - 1
            ideal_size = round(
                (
                    remaining_chars
                    + overlap_chars * (remaining_chunks - 1)
                )
                / remaining_chunks
            )
            ideal_end = start + ideal_size
            minimum_end = max(
                start + min_chars,
                len(normalized_text)
                + overlap_chars * future_chunks
                - max_chars * future_chunks,
            )
            maximum_end = min(
                start + max_chars,
                len(normalized_text)
                + overlap_chars * future_chunks
                - min_chars * future_chunks,
            )
            end = _nearest_boundary(
                boundaries=paragraph_ends,
                minimum=minimum_end,
                maximum=min(maximum_end, len(normalized_text)),
                target=ideal_end,
            )

        content = normalized_text[start:end].strip()
        chunks.append(
            TextChunk(
                content=content,
                char_count=len(content),
                chunk_index=chunk_index,
            )
        )

        if end >= len(normalized_text):
            break
        start = _word_boundary_after(
            normalized_text,
            max(end - overlap_chars, 0),
        )

    return chunks


def _paragraph_end_positions(text: str) -> list[int]:
    """Находит позиции окончаний абзацев в исходном тексте."""
    boundaries = [
        match.start()
        for match in re.finditer(r"\n\n", text)
    ]
    boundaries.append(len(text))
    return boundaries


def _nearest_boundary(
    boundaries: list[int],
    minimum: int,
    maximum: int,
    target: int,
) -> int:
    """Выбирает ближайшую подходящую границу абзаца."""
    candidates = [
        boundary
        for boundary in boundaries
        if minimum <= boundary <= maximum
    ]
    if candidates:
        return min(candidates, key=lambda boundary: abs(boundary - target))

    return min(max(target, minimum), maximum)


def _word_boundary_after(text: str, position: int) -> int:
    """Сдвигает позицию к следующей безопасной границе слова."""
    next_space = text.find(" ", position)
    next_paragraph = text.find("\n\n", position)
    candidates = [
        candidate
        for candidate in (next_space, next_paragraph)
        if candidate != -1
    ]
    if not candidates:
        return position
    return min(candidates) + 1
