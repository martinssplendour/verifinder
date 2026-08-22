from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, PostcodeRecord, RunStatus
from app.schemas import AreaCheckResponse, CrimeSummary, FloodSummary, PlanningSummary, PostcodePoint, SourceAttribution
from app.services.area_sources import (
    FLOOD_URL,
    PLANNING_URL,
    POLICE_URL,
    EnvironmentAgencyClient,
    PlanningDataClient,
    PoliceDataClient,
)
from app.services.dataset_utils import normalise_postcode
from app.services.grid_reference import osgb36_to_wgs84
from app.services.postcode_loader import SOURCE_ID


def latest_postcode_context(session: Session) -> tuple[DataSource, DatasetVersion] | None:
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        return None
    version = session.scalar(
        select(DatasetVersion)
        .where(DatasetVersion.source_id == SOURCE_ID, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    )
    return (source, version) if version else None


def _attribution(source: DataSource, version: DatasetVersion) -> SourceAttribution:
    return SourceAttribution(
        id=source.id,
        organisation=source.organisation,
        dataset=source.name,
        official_url=source.official_url,
        retrieved_at=version.retrieved_at,
        published_at=version.published_at,
        version=version.version_identifier,
        health=source.health.value,
    )


def find_postcode(session: Session, postcode: str) -> PostcodePoint | None:
    context = latest_postcode_context(session)
    normalised = normalise_postcode(postcode)
    if context is None or not normalised:
        return None
    source, version = context
    record = session.scalar(
        select(PostcodeRecord).where(
            PostcodeRecord.dataset_version_id == version.id,
            PostcodeRecord.normalised_postcode == normalised,
        )
    )
    if record is None:
        return None
    latitude, longitude = osgb36_to_wgs84(record.easting, record.northing)
    return PostcodePoint(
        postcode=record.postcode,
        latitude=latitude,
        longitude=longitude,
        country_code=record.country_code,
        admin_district_code=record.admin_district_code,
        admin_ward_code=record.admin_ward_code,
        source=_attribution(source, version),
    )


async def get_area_check(
    session: Session,
    postcode: str,
    police_client: PoliceDataClient | None = None,
    planning_client: PlanningDataClient | None = None,
    flood_client: EnvironmentAgencyClient | None = None,
) -> AreaCheckResponse | None:
    point = find_postcode(session, postcode)
    if point is None:
        return None
    police_client = police_client or PoliceDataClient()
    planning_client = planning_client or PlanningDataClient()
    flood_client = flood_client or EnvironmentAgencyClient()
    results = await asyncio.gather(
        police_client.summary(point.latitude, point.longitude),
        planning_client.summary(point.postcode),
        flood_client.summary(point.latitude, point.longitude),
        return_exceptions=True,
    )
    crime = results[0] if isinstance(results[0], CrimeSummary) else CrimeSummary(
        status="unavailable", source_url=POLICE_URL, message="Police.uk is temporarily unavailable."
    )
    planning = results[1] if isinstance(results[1], PlanningSummary) else PlanningSummary(
        status="unavailable", source_url=PLANNING_URL, message="Planning Data is temporarily unavailable."
    )
    flood = results[2] if isinstance(results[2], FloodSummary) else FloodSummary(
        status="unavailable", source_url=FLOOD_URL, message="Environment Agency flood data is temporarily unavailable."
    )
    return AreaCheckResponse(
        postcode=point,
        crime=crime,
        planning=planning,
        flood=flood,
        limitations=[
            "Police figures are street-level incidents near the postcode point, not a crime rate; locations are anonymised.",
            "Planning designations are currently sourced for England and coverage varies by local authority.",
            "Current flood warnings cover England and are searched within 10 km of the postcode point.",
            "Code-Point Open covers Great Britain; Northern Ireland postcodes are not included.",
        ],
    )
