from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.normalization import comparison_name, normalise_postcode


@dataclass(frozen=True)
class MatchDecision:
    status: str
    confidence: float
    method: str


def score_sponsor_match(
    company_name: str,
    sponsor_name: str,
    company_postcode: str | None = None,
    sponsor_postcode: str | None = None,
) -> MatchDecision:
    company = comparison_name(company_name)
    sponsor = comparison_name(sponsor_name)
    name_score = SequenceMatcher(None, company, sponsor).ratio()
    postcodes_match = bool(
        company_postcode
        and sponsor_postcode
        and normalise_postcode(company_postcode) == normalise_postcode(sponsor_postcode)
    )

    if company == sponsor and postcodes_match:
        return MatchDecision("confirmed", 0.99, "exact_name_postcode")
    if company == sponsor:
        return MatchDecision("likely", 0.94, "exact_normalised_name")
    if name_score >= 0.9 and postcodes_match:
        return MatchDecision("likely", round(min(name_score + 0.05, 0.98), 2), "fuzzy_name_postcode")
    if name_score >= 0.78:
        return MatchDecision("possible", round(name_score, 2), "fuzzy_name")
    return MatchDecision("unmatched", round(name_score, 2), "insufficient_similarity")

