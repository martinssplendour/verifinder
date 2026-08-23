"""A direct search that finds nothing should still offer close matches."""

import asyncio

import pytest
from fastapi import HTTPException

from app.api.routers.areas import area_check
from app.api.routers.sponsors import sponsor_search
from app.services.area_lookup import suggest_postcodes
from app.services.companies_house import CompaniesHouseClient
from app.services.food_lookup import search_food_establishments, similar_food_establishments
from app.services.property_lookup import search_properties, similar_properties
from app.services.qualification_lookup import search_qualifications, similar_qualifications
from app.services.school_lookup import search_schools, similar_schools
from app.services.sponsor_lookup import search_sponsor_records, similar_sponsor_records
from app.services.study_lookup import search_study_providers, similar_study_providers
from test_area_property import data_session
from test_qualification_food_lookup import public_data_session
from test_school_ofsted import _school_session
from test_sponsor_lookup import sponsor_session
from test_study_qualification_expansion import expanded_session


def test_misspelled_sponsor_name_finds_nothing_but_offers_the_real_name():
    session = sponsor_session()
    results, _ = search_sponsor_records(session, "Northstar Labbs Ltd", limit=5)
    suggestions, context = similar_sponsor_records(session, "Northstar Labbs Ltd")
    assert results == []
    assert context is not None
    assert suggestions[0].organisation_name == "Northstar Labs Ltd"


def test_sponsor_search_endpoint_returns_suggestions_alongside_an_empty_result():
    session = sponsor_session()
    response = asyncio.run(sponsor_search(q="Northstar Labbs Ltd", limit=8, session=session))
    assert response.results == []
    assert response.total == 0
    assert [item.organisation_name for item in response.suggestions] == [
        "Northstar Labs Ltd",
        "Northstar Arts CIO",
    ]


def test_exact_sponsor_match_is_not_padded_with_suggestions():
    session = sponsor_session()
    response = asyncio.run(sponsor_search(q="Northstar Labs Ltd", limit=8, session=session))
    assert [item.organisation_name for item in response.results] == ["Northstar Labs Ltd"]
    assert response.suggestions == []


def test_misspelled_food_business_offers_the_registered_establishment():
    session = public_data_session()
    results, _ = search_food_establishments(session, "Exampel Cafe")
    suggestions = similar_food_establishments(session, "Exampel Cafe")
    assert results == []
    assert [item.business_name for item in suggestions] == ["Example Cafe"]


def test_misspelled_school_name_offers_the_registered_establishment():
    session = _school_session()
    results, _ = search_schools(session, "Gospell Oak Primary School")
    suggestions = similar_schools(session, "Gospell Oak Primary School")
    assert results == []
    assert [item.establishment_name for item in suggestions] == ["Gospel Oak Primary School"]


def test_misspelled_qualification_title_offers_close_titles_from_both_registers():
    session = expanded_session()
    results, _ = search_qualifications(session, "Example Acounting Diploma")
    suggestions = similar_qualifications(session, "Example Acounting Diploma")
    assert results == []
    assert "Example Accounting Diploma" in [item.title for item in suggestions]


def test_misspelled_study_provider_offers_close_providers():
    session = expanded_session()
    results, _, _ = search_study_providers(session, "Exampel University")
    suggestions = similar_study_providers(session, "Exampel University")
    assert results == []
    assert [item.name for item in suggestions] == ["Example University", "Example University"]


def test_postcode_without_a_recorded_sale_offers_sales_in_the_same_sector():
    session = data_session()
    results, _ = search_properties(session, "N1 0AB")
    suggestions = similar_properties(session, "N1 0AB")
    assert results == []
    assert [item.postcode for item in suggestions] == ["N1 0AA"]


def test_address_without_a_recorded_sale_offers_nearby_addresses():
    session = data_session()
    results, _ = search_properties(session, "2 Example Street, London")
    suggestions = similar_properties(session, "2 Example Street, London")
    assert results == []
    assert [item.address for item in suggestions] == ["1, EXAMPLE STREET, LONDON, N1 0AA"]


def test_unknown_postcode_suggests_real_postcodes_in_the_same_outward_area():
    session = data_session()
    assert suggest_postcodes(session, "N1 0ZZ") == ["N1 0AA"]


def test_area_check_reports_no_records_with_postcode_suggestions():
    session = data_session()
    with pytest.raises(HTTPException) as error:
        asyncio.run(area_check(postcode="N1 0ZZ", session=session))
    assert error.value.status_code == 404
    assert "No records found" in error.value.detail["message"]
    assert error.value.detail["suggestions"] == ["N1 0AA"]


def test_company_search_offers_the_registers_own_near_matches_when_nothing_is_exact(
    monkeypatch: pytest.MonkeyPatch,
):
    client = CompaniesHouseClient("test-key")

    async def fake_get(path: str, params: dict | None = None):
        return {
            "items": [
                {"company_number": "00000002", "title": "ACME HOLDINGS LTD", "company_status": "active"},
                {"company_number": "00000003", "title": "ACM LTD", "company_status": "active"},
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)
    results, suggestions = asyncio.run(client.search_with_suggestions("Acme Ltd", limit=8))
    assert results == []
    assert [item.company_number for item in suggestions] == ["00000002", "00000003"]


def test_company_search_with_an_exact_match_returns_no_suggestions(monkeypatch: pytest.MonkeyPatch):
    client = CompaniesHouseClient("test-key")

    async def fake_get(path: str, params: dict | None = None):
        return {
            "items": [
                {"company_number": "00000001", "title": "ACME LTD", "company_status": "active"},
                {"company_number": "00000002", "title": "ACME HOLDINGS LTD", "company_status": "active"},
            ]
        }

    monkeypatch.setattr(client, "_get", fake_get)
    results, suggestions = asyncio.run(client.search_with_suggestions("Acme Ltd", limit=8))
    assert [item.company_number for item in results] == ["00000001"]
    assert suggestions == []
