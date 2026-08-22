import asyncio

import pytest
from fastapi import HTTPException

from app.api.routes import _company_profile, search


def test_unconfigured_company_search_returns_no_fixture_records(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.routes.companies_house_client", lambda: None)
    response = asyncio.run(search(q="Example company", limit=8))
    assert response.data_mode == "unavailable"
    assert response.results == []
    assert response.total == 0
    assert "COMPANIES_HOUSE_API_KEY" in (response.message or "")


def test_unconfigured_company_profile_is_unavailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.routes.companies_house_client", lambda: None)
    with pytest.raises(HTTPException) as error:
        asyncio.run(_company_profile("00000000", None))  # type: ignore[arg-type]
    assert error.value.status_code == 503
