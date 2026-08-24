"""Browse the connected registers directly, with or without a place filter.

Search answers "is this specific thing on the register?". This answers "what is
on the register?" - the same records, listed and paginated, narrowed by country
and place when the register stores one.

Every dataset is described once in BROWSABLE and then queried generically, so
adding a source is a single entry rather than a new endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.models import (
    DataSource,
    DatasetVersion,
    FoodEstablishmentRecord,
    OfsProviderRecord,
    PropertySaleRecord,
    QualificationExpansionRecord,
    QualificationRecord,
    RunStatus,
    SchoolRecord,
    SponsorRecord,
    StudentSponsorRecord,
)
from app.schemas import BrowseRecord, CountryOption, SourceAttribution
from app.services.food_loader import SOURCE_ID as FOOD_SOURCE_ID
from app.services.gias_loader import SOURCE_ID as GIAS_SOURCE_ID
from app.services.property_loader import SOURCE_ID as PROPERTY_SOURCE_ID
from app.services.qualification_expansion_loader import QIW_SOURCE_ID
from app.services.qualification_loader import SOURCE_ID as OFQUAL_SOURCE_ID
from app.services.sponsor_loader import SOURCE_ID as SPONSOR_SOURCE_ID
from app.services.study_loader import OFS_SOURCE_ID, STUDENT_SOURCE_ID


MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25
# Place lists feed a dropdown, so they are capped rather than exhaustive.
MAX_PLACES = 400

# Every connected source is UK public data. The country level exists so the
# filter does not have to be rebuilt when a non-UK register is added.
UNITED_KINGDOM = CountryOption(code="GB", name="United Kingdom")
COUNTRIES = [UNITED_KINGDOM]


@dataclass(frozen=True)
class BrowsableDataset:
    id: str
    label: str
    description: str
    source_id: str
    model: type
    order_by: InstrumentedAttribute
    to_record: Callable[[object], BrowseRecord]
    place_column: InstrumentedAttribute | None = None
    place_label: str | None = None
    # Rows sharing a key describe one subject, as several sales of one property do.
    distinct_on: InstrumentedAttribute | None = None


def _sponsor(record: SponsorRecord) -> BrowseRecord:
    return BrowseRecord(
        id=record.id,
        title=record.organisation_name,
        subtitle=", ".join(sorted(record.routes or [])) or "Licensed worker sponsor",
        place=", ".join(filter(None, (record.town_city, record.county))) or None,
        href=f"/sponsor/{record.id}",
    )


def _food(record: FoodEstablishmentRecord) -> BrowseRecord:
    return BrowseRecord(
        id=record.id,
        title=record.business_name,
        subtitle=f"Rating {record.rating_value}" if record.rating_value else record.business_type,
        place=record.local_authority_name,
        href=f"/food/{record.id}",
    )


def _school(record: SchoolRecord) -> BrowseRecord:
    return BrowseRecord(
        id=record.urn,
        title=record.establishment_name,
        subtitle=", ".join(filter(None, (record.type_name, record.status_name))) or None,
        place=", ".join(filter(None, (record.town, record.la_name))) or None,
        href=f"/school/{record.urn}",
    )


def _student_sponsor(record: StudentSponsorRecord) -> BrowseRecord:
    return BrowseRecord(
        id=str(record.id),
        title=record.organisation_name,
        subtitle=record.status or "Licensed student sponsor",
        place=record.town_city,
        href=f"/study/student_sponsor/{record.id}",
    )


def _ofs_provider(record: OfsProviderRecord) -> BrowseRecord:
    return BrowseRecord(
        id=str(record.id),
        title=record.legal_name,
        subtitle=record.registration_category or "Registered provider",
        place=record.postcode,
        href=f"/study/ofs/{record.id}",
    )


def _property(record: PropertySaleRecord) -> BrowseRecord:
    return BrowseRecord(
        id=record.property_key,
        title=record.full_address,
        subtitle=f"Sold {record.transfer_date:%d %b %Y}" if record.transfer_date else None,
        place=", ".join(filter(None, (record.town_city, record.county))) or None,
        href=f"/property/{record.property_key}",
    )


def _ofqual(record: QualificationRecord) -> BrowseRecord:
    return BrowseRecord(
        id=record.id,
        title=record.title,
        subtitle=", ".join(filter(None, (record.qualification_number, record.awarding_organisation_name))),
        place=None,
        href=f"/qualification/{record.id}",
    )


def _qiw(record: QualificationExpansionRecord) -> BrowseRecord:
    return BrowseRecord(
        id=str(record.id),
        title=record.title,
        subtitle=", ".join(filter(None, (record.qualification_number, record.awarding_organisation_name))),
        place=None,
        href=f"/qualification/{record.id}",
    )


BROWSABLE: dict[str, BrowsableDataset] = {
    dataset.id: dataset
    for dataset in (
        BrowsableDataset(
            id="sponsors",
            label="Worker sponsor register",
            description="Organisations licensed to sponsor workers.",
            source_id=SPONSOR_SOURCE_ID,
            model=SponsorRecord,
            order_by=SponsorRecord.organisation_name,
            to_record=_sponsor,
            place_column=SponsorRecord.town_city,
            place_label="Town or city",
        ),
        BrowsableDataset(
            id="study",
            label="Student sponsor register",
            description="Organisations licensed to sponsor international students.",
            source_id=STUDENT_SOURCE_ID,
            model=StudentSponsorRecord,
            order_by=StudentSponsorRecord.organisation_name,
            to_record=_student_sponsor,
            place_column=StudentSponsorRecord.town_city,
            place_label="Town or city",
        ),
        BrowsableDataset(
            id="providers",
            label="Office for Students register",
            description="Registered higher-education providers in England.",
            source_id=OFS_SOURCE_ID,
            model=OfsProviderRecord,
            order_by=OfsProviderRecord.legal_name,
            to_record=_ofs_provider,
        ),
        BrowsableDataset(
            id="schools",
            label="GIAS establishment register",
            description="Schools and colleges recorded by the Department for Education.",
            source_id=GIAS_SOURCE_ID,
            model=SchoolRecord,
            order_by=SchoolRecord.establishment_name,
            to_record=_school,
            place_column=SchoolRecord.town,
            place_label="Town or city",
        ),
        BrowsableDataset(
            id="food",
            label="Food hygiene ratings",
            description="Food businesses rated under the Food Hygiene Rating Scheme.",
            source_id=FOOD_SOURCE_ID,
            model=FoodEstablishmentRecord,
            order_by=FoodEstablishmentRecord.business_name,
            to_record=_food,
            place_column=FoodEstablishmentRecord.local_authority_name,
            place_label="Local authority",
        ),
        BrowsableDataset(
            id="property",
            label="Price Paid sales",
            description="Recorded property sales from the imported snapshot.",
            source_id=PROPERTY_SOURCE_ID,
            model=PropertySaleRecord,
            order_by=PropertySaleRecord.full_address,
            to_record=_property,
            place_column=PropertySaleRecord.town_city,
            place_label="Town or city",
            distinct_on=PropertySaleRecord.property_key,
        ),
        BrowsableDataset(
            id="qualifications",
            label="Regulated qualifications (Ofqual)",
            description="Qualifications regulated for England and Northern Ireland.",
            source_id=OFQUAL_SOURCE_ID,
            model=QualificationRecord,
            order_by=QualificationRecord.title,
            to_record=_ofqual,
        ),
        BrowsableDataset(
            id="qualifications-wales",
            label="Qualifications in Wales",
            description="Qualifications approved by Qualifications Wales.",
            source_id=QIW_SOURCE_ID,
            model=QualificationExpansionRecord,
            order_by=QualificationExpansionRecord.title,
            to_record=_qiw,
        ),
    )
}


def latest_context(session: Session, source_id: str) -> tuple[DataSource, DatasetVersion] | None:
    row = session.execute(
        select(DataSource, DatasetVersion)
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .where(DataSource.id == source_id, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None


def attribution(context: tuple[DataSource, DatasetVersion]) -> SourceAttribution:
    source, version = context
    return SourceAttribution(
        id=source.id,
        organisation=source.organisation,
        dataset=source.name,
        official_url=source.official_url or "",
        retrieved_at=version.retrieved_at,
        published_at=version.published_at,
        version=version.version_identifier,
        health=source.health.value,
    )


def _conditions(dataset: BrowsableDataset, version_id: str, place: str | None) -> list:
    conditions = [dataset.model.dataset_version_id == version_id]
    if place and dataset.place_column is not None:
        conditions.append(func.lower(dataset.place_column) == place.strip().lower())
    if hasattr(dataset.model, "active"):
        conditions.append(dataset.model.active.is_(True))
    return conditions


def list_places(session: Session, dataset: BrowsableDataset) -> list[str]:
    """The places this register actually holds, for the filter dropdown."""
    if dataset.place_column is None:
        return []
    context = latest_context(session, dataset.source_id)
    if context is None:
        return []
    _, version = context
    rows = session.scalars(
        select(dataset.place_column)
        .where(
            *_conditions(dataset, version.id, None),
            dataset.place_column.is_not(None),
            dataset.place_column != "",
        )
        .distinct()
        .order_by(dataset.place_column)
        .limit(MAX_PLACES)
    )
    return [str(value).strip() for value in rows if str(value).strip()]


def browse_records(
    session: Session,
    dataset: BrowsableDataset,
    *,
    place: str | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[BrowseRecord], int, tuple[DataSource, DatasetVersion] | None]:
    """One page of the register, narrowed to a place when one is chosen."""
    context = latest_context(session, dataset.source_id)
    if context is None:
        return [], 0, None
    _, version = context
    conditions = _conditions(dataset, version.id, place)
    offset = (page - 1) * page_size

    if dataset.distinct_on is not None:
        # One row per subject: several recorded sales of one property are one entry.
        keys = select(dataset.distinct_on).where(*conditions).distinct().subquery()
        total = session.scalar(select(func.count()).select_from(keys)) or 0
        chosen = list(
            session.scalars(
                select(dataset.distinct_on)
                .where(*conditions)
                .distinct()
                .order_by(dataset.distinct_on)
                .offset(offset)
                .limit(page_size)
            )
        )
        rows = session.scalars(
            select(dataset.model)
            .where(*conditions, dataset.distinct_on.in_(chosen))
            .order_by(dataset.distinct_on)
        )
        seen: set[object] = set()
        records: list[BrowseRecord] = []
        for row in rows:
            key = getattr(row, dataset.distinct_on.key)
            if key in seen:
                continue
            seen.add(key)
            records.append(dataset.to_record(row))
        return records, total, context

    total = session.scalar(select(func.count()).select_from(dataset.model).where(*conditions)) or 0
    rows = session.scalars(
        select(dataset.model).where(*conditions).order_by(dataset.order_by).offset(offset).limit(page_size)
    )
    return [dataset.to_record(row) for row in rows], total, context
