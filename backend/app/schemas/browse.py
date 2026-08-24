from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import SourceAttribution


class CountryOption(BaseModel):
    """A country the registers can be filtered to.

    Every connected source is UK public data today, so this list has one entry.
    The shape is country-then-place so a non-UK source can be added later
    without reworking the filter.
    """

    code: str
    name: str


class BrowseDataset(BaseModel):
    id: str
    label: str
    description: str
    organisation: str
    # None where the register holds no place at all, such as qualifications,
    # which are awarded nationally rather than at an address.
    place_label: str | None = None
    countries: list[str] = Field(default_factory=list)
    imported: bool = True
    message: str | None = None


class BrowseCatalogue(BaseModel):
    countries: list[CountryOption]
    datasets: list[BrowseDataset]


class BrowseRecord(BaseModel):
    id: str
    title: str
    subtitle: str | None = None
    place: str | None = None
    href: str


class BrowseResponse(BaseModel):
    dataset: str
    country: str | None = None
    place: str | None = None
    page: int
    page_size: int
    total: int
    records: list[BrowseRecord]
    dataset_version: str | None = None
    source: SourceAttribution | None = None
    message: str | None = None
