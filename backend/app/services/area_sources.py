from __future__ import annotations

import asyncio
from collections import Counter
import httpx

from app.schemas import CrimeCategoryCount, CrimeMonth, CrimeSummary, FloodSummary, FloodWarning, PlanningConstraint, PlanningSummary


POLICE_URL = "https://data.police.uk/docs/method/crime-street/"
PLANNING_URL = "https://www.planning.data.gov.uk/docs"
FLOOD_URL = "https://environment.data.gov.uk/flood-monitoring/doc/reference"
PLANNING_DATASETS = (
    "conservation-area",
    "listed-building",
    "green-belt",
    "flood-risk-zone",
    "article-4-direction-area",
    "tree-preservation-zone",
)


class PublicAreaDataError(RuntimeError):
    pass


def _previous_months(latest: str, count: int = 3) -> list[str]:
    year, month = (int(value) for value in latest[:7].split("-"))
    result: list[str] = []
    for _ in range(count):
        result.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return result


class PoliceDataClient:
    async def summary(self, latitude: float, longitude: float) -> CrimeSummary:
        try:
            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "VeriFinder/1.0"}) as client:
                updated = await client.get("https://data.police.uk/api/crime-last-updated")
                updated.raise_for_status()
                latest = updated.json()["date"][:7]
                months = _previous_months(latest)

                async def fetch(month: str) -> tuple[str, list[dict]]:
                    response = await client.get(
                        "https://data.police.uk/api/crimes-street/all-crime",
                        params={"lat": latitude, "lng": longitude, "date": month},
                    )
                    response.raise_for_status()
                    return month, response.json()

                payloads = await asyncio.gather(*(fetch(month) for month in months))
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise PublicAreaDataError(f"Police.uk could not be reached: {error}") from error

        month_counts = [CrimeMonth(month=month, count=len(items)) for month, items in payloads]
        category_counts = Counter(item.get("category", "other") for item in payloads[0][1])
        categories = [
            CrimeCategoryCount(category=category.replace("-", " ").title(), count=count)
            for category, count in category_counts.most_common(8)
        ]
        return CrimeSummary(
            status="live",
            latest_month=latest,
            latest_total=len(payloads[0][1]),
            months=month_counts,
            categories=categories,
            source_url=POLICE_URL,
        )


class PlanningDataClient:
    async def summary(self, postcode: str) -> PlanningSummary:
        params: list[tuple[str, str | int]] = [("q", postcode), ("limit", 50)]
        params.extend(("dataset", dataset) for dataset in PLANNING_DATASETS)
        try:
            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "VeriFinder/1.0"}) as client:
                response = await client.get("https://www.planning.data.gov.uk/entity.json", params=params)
                response.raise_for_status()
                entities = response.json().get("entities", [])
        except (httpx.HTTPError, TypeError, ValueError) as error:
            raise PublicAreaDataError(f"Planning Data could not be reached: {error}") from error
        constraints = [
            PlanningConstraint(
                dataset=str(entity.get("dataset", "planning-designation")),
                name=entity.get("name") or entity.get("reference") or "Unnamed designation",
                reference=entity.get("reference"),
                start_date=entity.get("start-date") or None,
            )
            for entity in entities
        ]
        return PlanningSummary(status="live", total=len(constraints), constraints=constraints, source_url=PLANNING_URL)


class EnvironmentAgencyClient:
    async def summary(self, latitude: float, longitude: float) -> FloodSummary:
        try:
            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "VeriFinder/1.0"}) as client:
                response = await client.get(
                    "https://environment.data.gov.uk/flood-monitoring/id/floods",
                    params={"lat": latitude, "long": longitude, "dist": 10},
                )
                response.raise_for_status()
                items = response.json().get("items", [])
        except (httpx.HTTPError, TypeError, ValueError) as error:
            raise PublicAreaDataError(f"Environment Agency flood data could not be reached: {error}") from error
        active = [item for item in items if int(item.get("severityLevel", 4)) < 4]
        warnings = [
            FloodWarning(
                severity=item.get("severity", "Flood alert"),
                severity_level=int(item.get("severityLevel", 4)),
                description=item.get("description") or item.get("message") or "Current flood warning",
                area=item.get("eaAreaName") or item.get("county"),
                time_raised=item.get("timeRaised"),
                time_message_changed=item.get("timeMessageChanged"),
            )
            for item in active
        ]
        return FloodSummary(status="live", total=len(warnings), warnings=warnings, radius_km=10, source_url=FLOOD_URL)
