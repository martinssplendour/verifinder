# Entity resolution

Companies House companies and sponsor-register organisations are independent source records. A similar name is not sufficient proof that they are the same legal entity.

## Normalisation

Original source values are always retained. Search/matching copies are normalised for:

- Unicode and case;
- punctuation and repeated whitespace;
- `&` / `and`;
- `LTD` / `LIMITED` and common legal-form punctuation;
- UK postcode spacing and case.

## Match decisions

The first scoring service produces one of:

- `confirmed`: exact comparison name plus a town found in the company’s registered-office record;
- `likely`: exact normalised name without sufficient location evidence;
- `possible`: name similarity is meaningful but evidence is insufficient;
- `unmatched`: similarity is below the review threshold.

Only `confirmed` mappings should automatically support the phrase “Found on the current UK sponsor register.” A `likely` or `possible` mapping should be reviewable and must use qualified copy.

Each persisted mapping keeps confidence, method and whether a human reviewed it. Manual confirmation, rejection and remapping are intended to be permanent audit decisions.
