from __future__ import annotations

import httpx

from app.schemas import EPCCertificate, EPCSummary


BASE_URL = "https://api.get-energy-performance-data.communities.gov.uk"
SEARCH_PATH = "/api/domestic/search"
OFFICIAL_URL = "https://get-energy-performance-data.communities.gov.uk/"
DOCS_URL = "https://get-energy-performance-data.communities.gov.uk/api-technical-documentation/search-certificates/domestic"


class EPCError(RuntimeError):
    pass


def _map_certificate(item: dict) -> EPCCertificate:
    address_parts = [
        item[key]
        for key in ("addressLine1", "addressLine2", "addressLine3", "addressLine4")
        if item.get(key)
    ]
    uprn = item.get("uprn")
    return EPCCertificate(
        certificate_number=str(item.get("certificateNumber", "")),
        address=", ".join(address_parts) or item.get("postTown") or "Address unavailable",
        postcode=item.get("postcode"),
        current_rating=item.get("currentEnergyEfficiencyBand"),
        lodgement_date=item.get("registrationDate"),
        uprn=str(uprn) if uprn is not None else None,
    )


class EPCClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, postcode: str, limit: int = 10) -> EPCSummary:
        try:
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
                response = await client.get(
                    SEARCH_PATH,
                    params={"postcode": postcode, "page_size": limit},
                    headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                )
            if response.is_error:
                raise EPCError(f"EPC register returned HTTP {response.status_code}")
            payload = response.json()
            items = payload.get("data") or []
            certificates = [_map_certificate(item) for item in items]
            pagination = payload.get("pagination") or {}
            total = pagination.get("totalRecords", len(certificates))
        except (httpx.HTTPError, TypeError, ValueError, AttributeError, KeyError) as error:
            raise EPCError(f"EPC register could not be reached: {error}") from error
        return EPCSummary(status="live", total=total, certificates=certificates, source_url=DOCS_URL)
