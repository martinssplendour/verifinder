# Source separation

Companies House companies and Home Office worker-sponsor organisations are independent source records. VeriFinder does not resolve, merge or score names across these sources.

## Lookup rules

- Company Check calls the Companies House API and returns only a company whose registered name or company number exactly equals the submitted query, ignoring letter case.
- Sponsorship Check queries only the latest successfully stored worker-sponsor dataset and returns only rows whose original organisation name exactly equals the submitted query, ignoring letter case and outer whitespace.
- Homepage type-ahead is a discovery aid, not a match result. Companies House suggestions are returned by that source's search API; sponsor suggestions are rows whose stored organisation name literally contains the typed text. Selecting one opens that source record directly.
- Partial names, abbreviation expansion, punctuation normalisation, edit distance, similarity scores, location hints and fuzzy matching are not used for either check.
- A user may submit the same name to both checks, but the results remain separate and no shared identity is inferred.

## Interpretation

A sponsor result establishes only that the displayed organisation name appears in the stored sponsor list. It does not identify a Companies House legal entity. A Companies House result establishes only the legal-company information returned by that API and does not state whether the company holds a sponsor licence.

No exact sponsor-list result means only that the submitted name was not found exactly in the latest stored dataset. Similar names are not substituted and no broader negative conclusion is made.
