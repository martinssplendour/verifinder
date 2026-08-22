from app.services.normalization import comparison_name, normalise_name, normalise_postcode


def test_normalises_legal_forms_and_punctuation():
    assert normalise_name("  Acmé & Co. LTD  ") == "acme and co limited"


def test_comparison_name_ignores_trailing_legal_form():
    assert comparison_name("Example Ltd") == comparison_name("EXAMPLE LIMITED") == "example"


def test_normalises_postcode():
    assert normalise_postcode("sw1a1aa") == "SW1A 1AA"

