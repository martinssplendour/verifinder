import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.billing_models import AskConversationRecord, BillingBase
from app.schemas import AskRequest
from app.services.ask_conversations import (
    delete_ask_conversation,
    load_ask_context,
    save_ask_response,
)
from app.services.decision_intelligence import answer_question
from test_sponsor_lookup import sponsor_session


def test_server_owned_ask_context_round_trip_and_delete():
    billing_engine = create_engine("sqlite://")
    BillingBase.metadata.create_all(billing_engine)
    billing_session = Session(billing_engine)
    subject_id = "anon-conversation-owner"
    response = asyncio.run(
        answer_question(
            sponsor_session(),
            AskRequest(question="Top 5 companies with sponsorship in London", limit=10),
        )
    )

    conversation_id = save_ask_response(
        billing_session,
        subject_id=subject_id,
        subject_ids=(subject_id,),
        conversation_id=None,
        response=response,
    )
    context = load_ask_context(billing_session, conversation_id, (subject_id,))

    assert len(context) == 1
    assert context[0].question == response.question
    assert context[0].results[0].title == "Northstar Labs Ltd"
    assert load_ask_context(billing_session, conversation_id, ("different-owner",)) == []
    assert delete_ask_conversation(billing_session, conversation_id, (subject_id,)) is True
    assert billing_session.query(AskConversationRecord).count() == 0
