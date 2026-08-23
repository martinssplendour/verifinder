"""Near-match fallback for direct searches that return no records.

A direct search deliberately answers only with records that genuinely match, so a
miss returns nothing at all. That is correct but unhelpful on its own: the user
cannot tell a typo apart from a genuine absence. Every search service therefore
falls back to this module to offer close matches from the same official source,
which the API returns in a separate ``suggestions`` field so they are never
mistaken for verified hits.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Callable, Iterable, TypeVar

from sqlalchemy import and_, or_


T = TypeVar("T")

PREFIX_LENGTH = 4
MIN_TOKEN_LENGTH = 3
MAX_TOKENS = 3
CANDIDATE_LIMIT = 400
SUGGESTION_LIMIT = 5
SIMILARITY_FLOOR = 0.45
CONTAINMENT_SCORE = 0.95


def significant_tokens(normalised_query: str) -> list[str]:
    """The few longest words worth using as a SQL prefilter."""
    tokens = {token for token in normalised_query.split() if len(token) >= MIN_TOKEN_LENGTH}
    return sorted(tokens, key=lambda token: (-len(token), token))[:MAX_TOKENS]


def candidate_filter(column, normalised_query: str):
    """An OR condition narrowing a table to plausible near-matches, or None.

    Scoring every row of a national register is not affordable, so the database
    does a cheap first pass: an index-friendly prefix range plus a containment
    test per significant word. Ranking then happens in Python over that subset.
    """
    conditions = []
    prefix = normalised_query[:PREFIX_LENGTH]
    if len(prefix) >= 2:
        conditions.append(and_(column >= prefix, column < f"{prefix}￿"))
    conditions.extend(column.contains(token, autoescape=True) for token in significant_tokens(normalised_query))
    return or_(*conditions) if conditions else None


def similarity(normalised_query: str, candidate: str) -> float:
    if not normalised_query or not candidate:
        return 0.0
    if normalised_query in candidate or candidate in normalised_query:
        return CONTAINMENT_SCORE
    return SequenceMatcher(None, normalised_query, candidate).ratio()


def rank_near_matches(
    records: Iterable[T],
    normalised_query: str,
    key: Callable[[T], str | None],
    limit: int = SUGGESTION_LIMIT,
    floor: float = SIMILARITY_FLOOR,
) -> list[T]:
    """Order candidates by how close they are to the query, dropping weak ones."""
    normalised_query = normalised_query.lower()
    tokens = significant_tokens(normalised_query)
    scored: list[tuple[float, str, T]] = []
    for record in records:
        value = (key(record) or "").strip().lower()
        if not value:
            continue
        score = similarity(normalised_query, value)
        if score < floor and tokens and any(token in value for token in tokens):
            score = floor
        if score >= floor:
            scored.append((score, value, record))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [record for _, _, record in scored[:limit]]
