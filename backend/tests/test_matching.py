from app.services.sponsor_matching import score_sponsor_match


def test_exact_name_and_postcode_is_confirmed():
    match = score_sponsor_match("Acme Ltd", "ACME LIMITED", "SW1A 1AA", "sw1a1aa")
    assert match.status == "confirmed"
    assert match.confidence == 0.99


def test_exact_name_without_postcode_is_likely_not_confirmed():
    match = score_sponsor_match("Acme Ltd", "ACME LIMITED", "SW1A 1AA", "M1 1AE")
    assert match.status == "likely"


def test_similar_name_is_possible():
    match = score_sponsor_match("Acme Technology Limited", "Acme Technologies Ltd")
    assert match.status in {"possible", "likely"}
    assert match.status != "confirmed"


def test_different_organisation_is_unmatched():
    match = score_sponsor_match("Acme Limited", "Northern Catering Group")
    assert match.status == "unmatched"

