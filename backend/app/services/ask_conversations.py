from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.billing_models import AskConversation, AskConversationRecord
from app.schemas import AskConversationTurn, AskResponse


CONTEXT_TURN_LIMIT = 6
STORED_TURN_LIMIT = 30


def _owned_conversation(
    session: Session,
    conversation_id: str,
    subject_ids: tuple[str, ...],
) -> AskConversation | None:
    return session.scalar(
        select(AskConversation).where(
            AskConversation.id == conversation_id,
            AskConversation.subject_id.in_(subject_ids),
        )
    )


def load_ask_context(
    session: Session,
    conversation_id: str | None,
    subject_ids: tuple[str, ...],
) -> list[AskConversationTurn]:
    if not conversation_id:
        return []
    conversation = _owned_conversation(session, conversation_id, subject_ids)
    if conversation is None:
        return []
    records = list(
        session.scalars(
            select(AskConversationRecord)
            .where(AskConversationRecord.conversation_id == conversation.id)
            .order_by(AskConversationRecord.created_at.desc(), AskConversationRecord.id.desc())
            .limit(CONTEXT_TURN_LIMIT)
        )
    )
    turns: list[AskConversationTurn] = []
    for record in reversed(records):
        try:
            response = AskResponse.model_validate(record.response)
            turns.append(
                AskConversationTurn(
                    question=response.question,
                    headline=response.headline,
                    summary=response.summary,
                    interpretation=response.interpretation,
                    results=response.results[:10],
                )
            )
        except ValidationError:
            continue
    return turns


def save_ask_response(
    session: Session,
    *,
    subject_id: str,
    subject_ids: tuple[str, ...],
    conversation_id: str | None,
    response: AskResponse,
) -> str:
    conversation = (
        _owned_conversation(session, conversation_id, subject_ids)
        if conversation_id
        else None
    )
    if conversation is None:
        conversation = AskConversation(subject_id=subject_id, title=response.question[:300])
        session.add(conversation)
        session.flush()
    elif conversation.subject_id != subject_id:
        # Claim an anonymous thread when its signed-cookie owner signs in.
        conversation.subject_id = subject_id
    conversation.updated_at = datetime.now(timezone.utc)
    session.add(
        AskConversationRecord(
            conversation_id=conversation.id,
            response=response.model_dump(mode="json"),
        )
    )
    session.flush()

    stale_ids = list(
        session.scalars(
            select(AskConversationRecord.id)
            .where(AskConversationRecord.conversation_id == conversation.id)
            .order_by(AskConversationRecord.created_at.desc(), AskConversationRecord.id.desc())
            .offset(STORED_TURN_LIMIT)
        )
    )
    if stale_ids:
        session.execute(delete(AskConversationRecord).where(AskConversationRecord.id.in_(stale_ids)))
    session.commit()
    return conversation.id


def delete_ask_conversation(
    session: Session,
    conversation_id: str,
    subject_ids: tuple[str, ...],
) -> bool:
    conversation = _owned_conversation(session, conversation_id, subject_ids)
    if conversation is None:
        return False
    session.execute(
        delete(AskConversationRecord).where(
            AskConversationRecord.conversation_id == conversation.id
        )
    )
    session.delete(conversation)
    session.commit()
    return True
