import asyncio
import csv
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DataSource, DatasetVersion, PostcodeRecord, PropertySaleRecord, RunStatus, SourceHealth
from app.schemas import CrimeMonth, CrimeSummary, EPCSummary, FloodSummary, PlanningSummary
from app.services.area_lookup import get_area_check
from app.services.epc import _map_certificate
from app.services.grid_reference import osgb36_to_wgs84
from app.services.postcode_ingestion import inspect_postcode_archive, postcode_rows
from app.services.property_ingestion import inspect_property_files, property_rows
from app.services.property_lookup import get_property, search_properties


def test_code_point_archive_is_streamed_and_mapped(tmp_path: Path):
    source = tmp_path / "code-point.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(
            "Data/CSV/n.csv",
            '"N1 0AA",10,530626,183961,"E92000001","E19000003","E18000007","","E09000019","E05013700"\n',
        )
    snapshot = inspect_postcode_archive(source)
    record = next(postcode_rows(snapshot, "postcode-version"))
    assert snapshot.record_count == 1
    assert record["normalised_postcode"] == "N10AA"
    assert record["admin_district_code"] == "E09000019"


def test_grid_conversion_places_sample_in_islington():
    latitude, longitude = osgb36_to_wgs84(530626, 183961)
    assert abs(latitude - 51.5394) < 0.001
    assert abs(longitude - -0.1179) < 0.001


def test_price_paid_files_are_mapped_and_grouped(tmp_path: Path):
    source = tmp_path / "pp.csv"
    with source.open("w", encoding="utf-8", newline="") as target:
        csv.writer(target).writerow(
            ["{tx-1}", "205500", "2026-02-05 00:00", "NG8 2DT", "D", "N", "F", "336", "", "TROWELL ROAD", "", "NOTTINGHAM", "CITY OF NOTTINGHAM", "CITY OF NOTTINGHAM", "A", "A"]
        )
    snapshot = inspect_property_files([source])
    record = next(property_rows(snapshot, "property-version"))
    assert snapshot.record_count == 1
    assert record["price"] == 205500
    assert record["normalised_postcode"] == "NG82DT"
    assert record["full_address"] == "336, TROWELL ROAD, NOTTINGHAM, CITY OF NOTTINGHAM, NG8 2DT"


def data_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    retrieved = datetime(2026, 8, 22, tzinfo=timezone.utc)
    postcode_source = DataSource(
        id="os-code-point-open", organisation="Ordnance Survey", name="Code-Point Open", source_type="ZIP/CSV",
        official_url="https://example.test/postcodes", country="GB", health=SourceHealth.HEALTHY,
        last_successful_retrieval=retrieved,
    )
    property_source = DataSource(
        id="hm-land-registry-price-paid", organisation="HM Land Registry", name="Price Paid Data",
        source_type="CSV", official_url="https://example.test/property", country="GB", health=SourceHealth.HEALTHY,
        last_successful_retrieval=retrieved,
    )
    postcode_version = DatasetVersion(
        id="postcode-version", source_id=postcode_source.id, version_identifier="2026-08", retrieved_at=retrieved,
        published_at=retrieved, file_hash="1" * 64, record_count=1, storage_location="postcodes.zip",
        processing_status=RunStatus.SUCCEEDED,
    )
    property_version = DatasetVersion(
        id="property-version", source_id=property_source.id, version_identifier="2025-2026", retrieved_at=retrieved,
        published_at=retrieved, file_hash="2" * 64, record_count=2, storage_location="pp.csv",
        processing_status=RunStatus.SUCCEEDED,
    )
    postcode = PostcodeRecord(
        dataset_version_id=postcode_version.id, postcode="N1 0AA", normalised_postcode="N10AA", postcode_area="N",
        positional_quality=10, easting=530626, northing=183961, country_code="E92000001",
        admin_district_code="E09000019", admin_ward_code="E05013700",
    )
    sales = [
        PropertySaleRecord(
            dataset_version_id=property_version.id, transaction_id=f"tx-{index}", price=price,
            transfer_date=transferred, postcode="N1 0AA", normalised_postcode="N10AA", property_type="F",
            new_build=False, tenure="L", paon="1", street="EXAMPLE STREET", town_city="LONDON",
            full_address="1, EXAMPLE STREET, LONDON, N1 0AA", normalised_address="1 example street london n1 0aa",
            property_key="property-key", ppd_category="A", record_status="A",
        )
        for index, (price, transferred) in enumerate(((500000, date(2025, 1, 1)), (550000, date(2026, 1, 1))), start=1)
    ]
    session.add_all([postcode_source, property_source, postcode_version, property_version, postcode, *sales])
    session.commit()
    return session


class FakePolice:
    async def summary(self, latitude: float, longitude: float):
        return CrimeSummary(status="live", latest_month="2026-06", latest_total=4, months=[CrimeMonth(month="2026-06", count=4)], source_url="https://example.test/crime")


class FakePlanning:
    async def summary(self, postcode: str):
        return PlanningSummary(status="live", total=0, source_url="https://example.test/planning")


class FakeFlood:
    async def summary(self, latitude: float, longitude: float):
        return FloodSummary(status="live", total=0, source_url="https://example.test/flood")


class FakeEPC:
    async def search(self, postcode: str, limit: int = 10):
        return EPCSummary(status="live", total=1, source_url="https://example.test/epc")


def test_epc_certificate_mapping_builds_address_and_rating():
    certificate = _map_certificate(
        {
            "certificateNumber": "1234-5678-9012-3456-7890",
            "addressLine1": "1 Example Street",
            "addressLine2": "Flat A",
            "postcode": "N1 0AA",
            "postTown": "LONDON",
            "currentEnergyEfficiencyBand": "C",
            "registrationDate": "2021-07-10",
            "uprn": "100023336956",
        }
    )
    assert certificate.address == "1 Example Street, Flat A"
    assert certificate.current_rating == "C"
    assert certificate.uprn == "100023336956"


def test_epc_certificate_mapping_falls_back_to_post_town_without_address_lines():
    certificate = _map_certificate({"certificateNumber": "0000", "postTown": "LEEDS"})
    assert certificate.address == "LEEDS"


def test_epc_certificate_mapping_coerces_integer_uprn():
    certificate = _map_certificate(
        {"certificateNumber": "0000", "postTown": "WITNEY", "uprn": 100120951525}
    )
    assert certificate.uprn == "100120951525"


def test_area_and_property_lookups_use_latest_snapshots():
    session = data_session()
    area = asyncio.run(get_area_check(session, "N1 0AA", FakePolice(), FakePlanning(), FakeFlood()))
    assert area is not None
    assert area.crime.latest_total == 4
    assert area.postcode.source.organisation == "Ordnance Survey"

    results, context = search_properties(session, "N1 0AA")
    assert context is not None
    assert results[0].latest_price == 550000
    assert results[0].transaction_count == 2
    detail = asyncio.run(get_property(session, "property-key", FakePlanning(), FakeEPC()))
    assert detail is not None
    assert len(detail.sales) == 2
    assert detail.nearby_sales and detail.nearby_sales.median_price == 525000
    assert detail.epc.status == "live"
    assert detail.epc.total == 1


def test_property_detail_reports_epc_as_not_connected_without_client():
    session = data_session()
    detail = asyncio.run(get_property(session, "property-key", FakePlanning()))
    assert detail is not None
    assert detail.epc.status == "unavailable"
    assert "not connected" in (detail.epc.message or "")
    assert "not connected" in detail.limitations[-1]
