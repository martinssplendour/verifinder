import pytest

from app.services.sponsor_ingestion import SponsorSchemaError, diff_snapshots, parse_sponsor_csv


def sponsor_csv(rows: str) -> bytes:
    return ("Organisation Name,Town/City,Type & Rating,Route\n" + rows).encode()


def test_parses_valid_dataset_and_preserves_original_record():
    snapshot = parse_sponsor_csv(sponsor_csv("Example Ltd,London,A,Skilled Worker\n"))
    record = next(iter(snapshot.records.values()))
    assert record["organisation_name"] == "Example Ltd"
    assert record["normalised_name"] == "example limited"
    assert record["routes"] == ["Skilled Worker"]
    assert record["raw_records"][0]["Organisation Name"] == "Example Ltd"


def test_missing_required_column_fails_without_partial_result():
    content = b"Organisation Name,Town/City,Route\nExample Ltd,London,Skilled Worker\n"
    with pytest.raises(SponsorSchemaError, match="rating"):
        parse_sponsor_csv(content)


def test_duplicate_organisation_rows_are_merged_without_losing_routes():
    snapshot = parse_sponsor_csv(
        sponsor_csv("Example Ltd,London,A,Skilled Worker\nExample Ltd,London,A,Global Business Mobility\n")
    )
    assert len(snapshot.records) == 1
    record = next(iter(snapshot.records.values()))
    assert record["routes"] == ["Global Business Mobility", "Skilled Worker"]
    assert len(record["raw_records"]) == 2


def test_dataset_without_usable_rows_is_rejected():
    with pytest.raises(SponsorSchemaError, match="no usable"):
        parse_sponsor_csv(sponsor_csv(",London,A,Skilled Worker\n"))


def test_unchanged_dataset_has_no_diff():
    previous = parse_sponsor_csv(sponsor_csv("Example Ltd,London,A,Skilled Worker\n"))
    current = parse_sponsor_csv(sponsor_csv("Example Ltd,London,A,Skilled Worker\n"))
    diff = diff_snapshots(previous, current)
    assert diff.added == diff.removed == diff.changed == ()


def test_detects_addition_removal_and_route_change():
    previous = parse_sponsor_csv(
        sponsor_csv("Example Ltd,London,A,Skilled Worker\nOld Ltd,Leeds,A,Skilled Worker\n")
    )
    current = parse_sponsor_csv(
        sponsor_csv("Example Ltd,London,A,Global Business Mobility\nNew Ltd,Bristol,A,Skilled Worker\n")
    )
    diff = diff_snapshots(previous, current)
    assert len(diff.added) == 1
    assert len(diff.removed) == 1
    assert len(diff.changed) == 1

