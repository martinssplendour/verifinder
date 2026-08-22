from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.areas import EPCSummary, PlanningSummary
from app.schemas.common import SourceAttribution


class PropertySale(BaseModel):
    transaction_id: str
    price: int
    transfer_date: date
    property_type: str | None = None
    new_build: bool | None = None
    tenure: str | None = None
    ppd_category: str | None = None


class PropertySearchResult(BaseModel):
    property_key: str
    address: str
    postcode: str | None = None
    latest_price: int
    latest_transfer_date: date
    property_type: str | None = None
    transaction_count: int
    source: SourceAttribution


class PropertySearchResponse(BaseModel):
    query: str
    results: list[PropertySearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class NearbySalesSummary(BaseModel):
    postcode: str
    count: int
    median_price: int | None = None
    minimum_price: int | None = None
    maximum_price: int | None = None


class PropertyDetail(BaseModel):
    property_key: str
    address: str
    postcode: str | None = None
    property_type: str | None = None
    town_city: str | None = None
    district: str | None = None
    county: str | None = None
    sales: list[PropertySale]
    nearby_sales: NearbySalesSummary | None = None
    planning: PlanningSummary
    epc: EPCSummary
    source: SourceAttribution
    limitations: list[str] = Field(default_factory=list)
