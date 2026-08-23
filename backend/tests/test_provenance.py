import asyncio

import pytest
from fastapi import HTTPException

from app.api.routers.companies import _company_profile, search
from app.services.companies_house import CompaniesHouseClient


def test_unconfigured_company_search_returns_no_fixture_records(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.routers.companies.companies_house_client", lambda: None)
    response = asyncio.run(search(q="Example company", limit=8))
    assert response.data_mode == "unavailable"
    assert response.results == []
    assert response.total == 0
    assert "COMPANIES_HOUSE_API_KEY" in (response.message or "")


def test_unconfigured_company_profile_is_unavailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.api.routers.companies.companies_house_client", lambda: None)
    with pytest.raises(HTTPException) as error:
        asyncio.run(_company_profile("00000000"))
    assert error.value.status_code == 503


def test_company_search_filters_out_non_exact_api_results(monkeypatch: pytest.MonkeyPatch):
    client = CompaniesHouseClient("test-key")

    async def fake_get(path: str, params: dict | None = None):
        assert path == "/search/companies"
        assert params == {"q": "Acme Ltd", "items_per_page": 20}
        return {
            "items": [
                {"company_number": "00000001", "title": "ACME LTD", "company_status": "active"},
                {"company_number": "00000002", "title": "ACME HOLDINGS LTD", "company_status": "active"},
                {"company_number": "00000003", "title": "ACM LTD", "company_status": "active"},
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)
    results = asyncio.run(client.search("Acme Ltd", limit=8))
    assert [result.company_number for result in results] == ["00000001"]


def test_company_suggestions_return_source_search_results_without_treating_them_as_exact(monkeypatch: pytest.MonkeyPatch):
    client = CompaniesHouseClient("test-key")

    async def fake_get(path: str, params: dict | None = None):
        assert path == "/search/companies"
        assert params == {"q": "Acme", "items_per_page": 4}
        return {
            "items": [
                {"company_number": "00000001", "title": "ACME LTD", "company_status": "active"},
                {"company_number": "00000002", "title": "ACME HOLDINGS LTD", "company_status": "active"},
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)
    results = asyncio.run(client.suggestions("Acme", limit=4))
    assert [result.company_number for result in results] == ["00000001", "00000002"]
