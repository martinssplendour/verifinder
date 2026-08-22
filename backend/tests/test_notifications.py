import json

import httpx

from app.config import get_settings
from app.services.notifications import _mcp_response_payload, email_configured


def test_mcp_response_payload_accepts_json():
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        json={"jsonrpc": "2.0", "id": 1, "result": {}},
        request=httpx.Request("POST", "https://example.test/mcp"),
    )

    assert _mcp_response_payload(response)["id"] == 1


def test_mcp_response_payload_accepts_event_stream():
    payload = {"jsonrpc": "2.0", "id": 2, "result": {"isError": False}}
    response = httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        text=f"event: message\ndata: {json.dumps(payload)}\n\n",
        request=httpx.Request("POST", "https://example.test/mcp"),
    )

    assert _mcp_response_payload(response) == payload


def test_email_configured_for_zoho(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "zoho_mcp")
    monkeypatch.setenv("ZOHO_MCP_URL", "https://example.test/mcp")
    monkeypatch.setenv("ZOHO_MAIL_ACCOUNT_ID", "123")
    get_settings.cache_clear()
    try:
        assert email_configured() is True
    finally:
        get_settings.cache_clear()


def test_email_not_configured_when_selected_provider_is_incomplete(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "zoho_mcp")
    monkeypatch.delenv("ZOHO_MCP_URL", raising=False)
    monkeypatch.setenv("ZOHO_MAIL_ACCOUNT_ID", "123")
    get_settings.cache_clear()
    try:
        assert email_configured() is False
    finally:
        get_settings.cache_clear()
