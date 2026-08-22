from datetime import datetime, timezone

import httpx

from app.schemas import CompanyProfile, SearchResult, SourceAttribution, SponsorshipSummary


BASE_URL = "https://api.company-information.service.gov.uk"


class CompaniesHouseError(RuntimeError):
    pass


class CompaniesHouseClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(base_url=BASE_URL, auth=(self.api_key, ""), timeout=12) as client:
            response = await client.get(path, params=params)
        if response.status_code == 404:
            raise KeyError(path)
        if response.is_error:
            raise CompaniesHouseError(f"Companies House returned HTTP {response.status_code}")
        return response.json()

    async def search(self, query: str, limit: int = 8) -> list[SearchResult]:
        payload = await self._get("/search/companies", {"q": query, "items_per_page": limit})
        return [
            SearchResult(
                company_number=item["company_number"],
                company_name=item["title"],
                status=item.get("company_status"),
                location=item.get("address_snippet"),
                company_type=item.get("company_type"),
                data_mode="live",
            )
            for item in payload.get("items", [])
        ]

    async def profile(self, company_number: str) -> CompanyProfile:
        item = await self._get(f"/company/{company_number}")
        address = item.get("registered_office_address", {})
        office = ", ".join(
            str(address[key])
            for key in ("address_line_1", "address_line_2", "locality", "region", "postal_code")
            if address.get(key)
        )
        now = datetime.now(timezone.utc)
        source = SourceAttribution(
            id="companies-house",
            organisation="Companies House",
            dataset="Company profile API",
            official_url=f"https://find-and-update.company-information.service.gov.uk/company/{company_number}",
            retrieved_at=now,
            health="healthy",
        )
        return CompanyProfile(
            company_number=item["company_number"],
            company_name=item["company_name"],
            company_status=item.get("company_status"),
            incorporation_date=item.get("date_of_creation"),
            registered_office=office or None,
            postcode=address.get("postal_code"),
            sic_codes=item.get("sic_codes", []),
            company_type=item.get("type"),
            accounts_next_due=item.get("accounts", {}).get("next_due"),
            verified_status="verified",
            data_mode="live",
            company_source=source,
            sponsorship=SponsorshipSummary(
                status="data_unavailable",
                label="Sponsorship data unavailable",
                explanation="No current sponsor-register dataset has been ingested in this environment.",
            ),
        )

    async def officers(self, company_number: str) -> list[dict]:
        payload = await self._get(f"/company/{company_number}/officers", {"items_per_page": 50})
        return [
            {
                "name": item["name"],
                "role": item.get("officer_role", "officer"),
                "appointed_on": item.get("appointed_on"),
                "resigned_on": item.get("resigned_on"),
            }
            for item in payload.get("items", [])
        ]

