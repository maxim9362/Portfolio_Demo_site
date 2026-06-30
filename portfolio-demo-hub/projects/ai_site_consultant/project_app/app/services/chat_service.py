# Этот файл управляет сохранением диалога и потоковой генерацией ответа AI.

from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.llm.client import LLMClient
from app.models.lead import Lead
from app.rag.embeddings import EmbeddingClient
from app.rag.retriever import KnowledgeRetriever, RetrievedChunk
from app.repositories.lead_repository import get_lead_by_session_id
from app.repositories.message_repository import (
    get_all_messages,
    save_message,
)
from app.services.conversation_responder import (
    get_conversation_response,
    is_silent_post_lead_message,
    should_prioritize_business_answer,
)
from app.services.lead_dialogue import process_lead_dialogue
from app.services.lead_service import (
    add_details_to_existing_lead,
)
from app.services.lead_state import LeadState, build_lead_state
from app.services.prompt_builder import CustomerContext, build_chat_prompt
from app.services.session_service import get_or_create_session


HISTORY_LIMIT = 6
NO_KNOWLEDGE_RESPONSE = (
    "Я не нашел точной информации по этому запросу. "
    "Уточните, пожалуйста, какая именно услуга или стоимость вас интересует."
)
@dataclass(frozen=True, slots=True)
class ConversationState:
    """Содержит локальный снимок состояния заявки для одного запроса."""
    lead_created: bool
    lead: Lead | None


def stream_chat_answer(
    db: Session,
    llm_client: LLMClient,
    session_id: str,
    user_message: str,
) -> AsyncIterator[str]:
    """Обрабатывает сообщение, восстанавливает контекст и возвращает поток."""
    chat_session = get_or_create_session(db, session_id)
    saved_user_message = save_message(
        db=db,
        session_id=chat_session.session_id,
        role="user",
        content=user_message,
    )

    all_messages = get_all_messages(
        db=db,
        session_id=chat_session.session_id,
    )
    history = [
        message
        for message in all_messages
        if message.id != saved_user_message.id
    ][-HISTORY_LIMIT:]
    lead = get_lead_by_session_id(db, chat_session.session_id)
    direct_conversation_response = get_conversation_response(
        user_message,
        lead_created=lead is not None,
        customer_name=lead.name if lead else None,
        lead_status=lead.status if lead else None,
    )
    answer_with_knowledge_first = should_prioritize_business_answer(
        user_message
    )
    lead_dialogue_response = None
    if direct_conversation_response is None and not answer_with_knowledge_first:
        lead_dialogue_response = process_lead_dialogue(
            db=db,
            session_id=chat_session.session_id,
            messages=all_messages,
        )
    post_lead_update_response = None
    if lead is not None:
        post_lead_update_response = add_details_to_existing_lead(
            db=db,
            lead=lead,
            user_message=user_message,
        )
        lead = get_lead_by_session_id(db, chat_session.session_id)
    conversation_state = ConversationState(
        lead_created=lead is not None,
        lead=lead,
    )
    lead_state = build_lead_state(all_messages, lead)
    silent_response = (
        conversation_state.lead_created
        and is_silent_post_lead_message(user_message)
    )

    conversation_response = (
        direct_conversation_response
        or lead_dialogue_response
        or post_lead_update_response
    )
    knowledge_chunks = []
    if conversation_response is None and not silent_response:
        embedding_client = EmbeddingClient(
            model_name=settings.embedding_model_name,
        )
        retriever = KnowledgeRetriever(
            chroma_path=settings.chroma_path,
            collection_name=settings.chroma_collection,
            embedding_client=embedding_client,
            max_distance=settings.rag_max_distance,
        )
        knowledge_chunks = retriever.retrieve(user_message, limit=5)
        previous_user_messages = [
            message.content
            for message in history
            if message.role == "user"
        ]
        if _needs_contextual_retrieval(user_message) and previous_user_messages:
            contextual_query = (
                f"{previous_user_messages[-1]}\n"
                f"Уточнение пользователя: {user_message}"
            )
            contextual_chunks = retriever.retrieve(contextual_query, limit=5)
            knowledge_chunks = _merge_knowledge_chunks(
                knowledge_chunks,
                contextual_chunks,
                limit=5,
            )

    async def generate() -> AsyncIterator[str]:
        """Сохраняет и потоково выдает выбранный ответ пользователю."""
        if silent_response:
            return

        if conversation_response is not None:
            save_message(
                db=db,
                session_id=chat_session.session_id,
                role="assistant",
                content=conversation_response,
            )
            yield conversation_response
            return

        if not knowledge_chunks:
            response = (
                _post_lead_no_knowledge_response(conversation_state)
                if conversation_state.lead_created
                else NO_KNOWLEDGE_RESPONSE
            )
            save_message(
                db=db,
                session_id=chat_session.session_id,
                role="assistant",
                content=response,
            )
            yield response
            return

        prompt = build_chat_prompt(
            history=history,
            user_question=user_message,
            knowledge_chunks=[chunk.content for chunk in knowledge_chunks],
            customer_context=_build_customer_context(
                conversation_state,
                lead_state,
            ),
        )
        answer_parts: list[str] = []

        async for chunk in llm_client.stream_answer(
            system_prompt=prompt.system_prompt,
            messages=prompt.messages,
        ):
            answer_parts.append(chunk)
            yield chunk

        full_answer = "".join(answer_parts).strip()
        if full_answer:
            save_message(
                db=db,
                session_id=chat_session.session_id,
                role="assistant",
                content=full_answer,
            )

    return generate()


def _build_customer_context(
    conversation_state: ConversationState,
    lead_state: LeadState,
) -> CustomerContext:
    """Формирует контекст LLM из состояния и модели лида."""
    lead = conversation_state.lead
    return CustomerContext(
        lead_created=conversation_state.lead_created,
        service=lead_state.service,
        problem=lead_state.problem,
        city=lead_state.city,
        name=lead.name if lead else lead_state.name,
        phone=lead.phone if lead else lead_state.phone,
        email=lead.email if lead else lead_state.email,
        request_details=lead.message if lead else None,
        preferred_contact_time=(
            lead.preferred_contact_time if lead
            else lead_state.preferred_contact_time
        ),
        status=lead.status if lead else None,
    )


def _post_lead_no_knowledge_response(
    conversation_state: ConversationState,
) -> str:
    """Отвечает после лида, если база знаний не дала результата."""
    lead = conversation_state.lead
    greeting = f"{lead.name}, " if lead and lead.name else ""
    return (
        f"{greeting}ваша заявка уже оформлена, повторно оставлять данные "
        "не нужно. Уточните, пожалуйста, что еще вы хотите узнать по заявке "
        "или по обслуживанию кондиционера?"
    )


def _needs_contextual_retrieval(message: str) -> bool:
    """Определяет, нужен ли поиск с учетом предыдущего вопроса."""
    normalized_message = message.casefold()
    context_markers = (
        "с ним",
        "с ней",
        "это",
        "этот",
        "эта",
        "они",
        "там",
        "подробнее",
    )
    return len(normalized_message) <= 80 and any(
        marker in normalized_message
        for marker in context_markers
    )


def _merge_knowledge_chunks(
    primary_chunks: list[RetrievedChunk],
    contextual_chunks: list[RetrievedChunk],
    limit: int,
) -> list[RetrievedChunk]:
    """Объединяет результаты двух поисков без дубликатов."""
    chunks_by_source: dict[str, RetrievedChunk] = {}
    for chunk in [*primary_chunks, *contextual_chunks]:
        existing = chunks_by_source.get(chunk.source)
        if existing is None or chunk.distance < existing.distance:
            chunks_by_source[chunk.source] = chunk

    return sorted(
        chunks_by_source.values(),
        key=lambda chunk: chunk.distance,
    )[:limit]
