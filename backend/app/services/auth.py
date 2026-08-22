from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.services.entitlements import COOKIE_NAME, resolve_subject_id


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class RequestIdentity:
    subject_id: str
    anonymous_subject_id: str
    network_hash: str | None
    user_id: str | None = None
    email: str | None = None

    @property
    def authenticated(self) -> bool:
        return self.user_id is not None

    @property
    def quota_subject_ids(self) -> tuple[str, ...]:
        if self.user_id and self.user_id != self.anonymous_subject_id:
            return (self.user_id, self.anonymous_subject_id)
        return (self.subject_id,)


def _client_network_hash(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for", "")
    address = forwarded.split(",", 1)[0].strip() if forwarded else None
    if not address and request.client:
        address = request.client.host
    if not address:
        return None
    settings = get_settings()
    key = (settings.subject_signing_key or "development-network-key").encode("utf-8")
    return hmac.new(key, address.encode("utf-8"), hashlib.sha256).hexdigest()


async def _verify_supabase_token(token: str) -> dict[str, object]:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Account authentication is not configured.")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError as error:
        raise HTTPException(status_code=503, detail="Account authentication is temporarily unavailable.") from error
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Your sign-in session is invalid or has expired.")
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
        raise HTTPException(status_code=401, detail="Your sign-in session could not be verified.")
    return payload


async def resolve_identity(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> RequestIdentity:
    anonymous_subject_id = resolve_subject_id(response, request.cookies.get(COOKIE_NAME))
    network_hash = _client_network_hash(request)
    if credentials is None:
        return RequestIdentity(
            subject_id=anonymous_subject_id,
            anonymous_subject_id=anonymous_subject_id,
            network_hash=network_hash,
        )
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Unsupported authentication scheme.")
    user = await _verify_supabase_token(credentials.credentials)
    user_id = str(user["id"])
    email = user.get("email")
    return RequestIdentity(
        subject_id=user_id,
        anonymous_subject_id=anonymous_subject_id,
        network_hash=network_hash,
        user_id=user_id,
        email=str(email) if email else None,
    )


async def identity_dependency(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> RequestIdentity:
    return await resolve_identity(request, response, credentials)


def require_authenticated(identity: RequestIdentity) -> RequestIdentity:
    if identity.authenticated:
        return identity
    raise HTTPException(
        status_code=401,
        detail={
            "code": "sign_in_required",
            "message": "Sign in to continue to billing.",
            "sign_in_required": True,
        },
    )
