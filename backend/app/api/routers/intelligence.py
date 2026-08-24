from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routers.account_billing import _entitlement_error
from app.billing_database import get_billing_db
from app.database import get_read_db
from app.schemas import AskRequest, AskResponse, DecisionPlanResponse, PlanRequest
from app.services.auth import RequestIdentity, identity_dependency
from app.services.ask_conversations import delete_ask_conversation, load_ask_context, save_ask_response
from app.services.decision_intelligence import answer_question, build_plan
from app.services.entitlements import (
    get_or_create_profile,
    refund_ask_coin,
    reserve_ask,
    reserve_planner,
)


router = APIRouter()


@router.post("/intelligence/ask", response_model=AskResponse)
async def ask_verifinder(
    request: AskRequest,
    public_session: Session = Depends(get_read_db),
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    if identity.authenticated:
        get_or_create_profile(billing_session, identity.subject_id, identity.email)
    entitlement = reserve_ask(
        billing_session,
        identity.subject_id,
        request.question,
        subject_ids=identity.quota_subject_ids,
        network_hash=identity.network_hash,
        authenticated=identity.authenticated,
        email=identity.email,
    )
    if not entitlement.allowed:
        raise _entitlement_error(entitlement)
    try:
        if request.conversation_id:
            conversation = load_ask_context(
                billing_session,
                request.conversation_id,
                identity.quota_subject_ids,
            )
        else:
            # Bounded client context keeps older deployed clients compatible.
            conversation = request.conversation[-6:]
        contextual_request = request.model_copy(update={"conversation": conversation})
        answer = await answer_question(public_session, contextual_request)
        conversation_id = save_ask_response(
            billing_session,
            subject_id=identity.subject_id,
            subject_ids=identity.quota_subject_ids,
            conversation_id=request.conversation_id,
            response=answer,
        )
        return answer.model_copy(
            update={
                "conversation_id": conversation_id,
                "context_turns_used": len(conversation),
            }
        )
    except Exception:
        billing_session.rollback()
        refund_ask_coin(
            billing_session,
            identity.subject_id,
            entitlement.coin_reservation_id,
        )
        raise


@router.delete("/intelligence/conversations/{conversation_id}")
def clear_ask_conversation(
    conversation_id: str,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    delete_ask_conversation(billing_session, conversation_id, identity.quota_subject_ids)
    return {"status": "removed"}


@router.post("/plans", response_model=DecisionPlanResponse)
async def create_plan(
    request: PlanRequest,
    public_session: Session = Depends(get_read_db),
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    if identity.authenticated:
        get_or_create_profile(billing_session, identity.subject_id, identity.email)
    entitlement = reserve_planner(
        billing_session,
        identity.subject_id,
        subject_ids=identity.quota_subject_ids,
        network_hash=identity.network_hash,
        email=identity.email,
    )
    if not entitlement.allowed:
        raise _entitlement_error(entitlement)
    return await build_plan(public_session, request)
