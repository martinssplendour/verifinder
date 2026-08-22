# Architecture

## Product boundary

VeriFinder is a modular monolith with seven live public-data engines: Company Check, Qualification Check, Food Check, Area Check, Property Check, Study Provider Check and School Check.

## Information flow

```text
Official source
  -> immutable raw input / API response
  -> schema validation, hash and ingestion run
  -> dataset version
  -> normalised source record
  -> source-attributed API response
  -> user interface
```

Company-to-sponsor linking adds an explicit entity-resolution step between the source record and response. Study Provider Check performs only an exact normalised-name cross-reference between UKVI and OfS records; it does not merge their statuses. School Check performs an exact URN cross-reference between the GIAS establishment register and the Ofsted inspection extract, the same non-merging principle applied to a shared identifier rather than a name. Qualification, food, postcode and property records are queried directly within their latest successful dataset version. Area and property views enrich local immutable snapshots with clearly labelled on-demand official APIs.

## Frontend

The Next.js application contains:

- a homepage that routes to all seven live checks;
- source-grouped Company Check results and provenance-first company/sponsor details;
- regulator-grouped qualification search across Ofqual/CCEA and Qualifications Wales, with awarding-organisation detail and linked Ofqual units;
- study-provider search across separately labelled UKVI student-sponsor and OfS provider registers;
- food-establishment search by name or postcode, with scheme-aware rating detail;
- postcode Area Check with aggregated crime trends, selected planning designations and active flood warnings;
- recent property-sale search by full postcode or address prefix, with sale history and postcode planning context;
- school search across the GIAS establishment register, with the matching Ofsted inspection outcome shown separately by URN;
- source, retrieval date, dataset version, loading, empty and unavailable states;
- source-registry, methodology and internal-operations pages.

The interface states the boundary of each check near the result: official records support a decision, but do not replace legal, admissions, immigration or current-site verification.

## Backend

FastAPI exposes typed Pydantic responses. Source-specific services own parsing, normalisation, loading and lookup:

- `CompaniesHouseClient` handles credentialed company API requests.
- `EPCClient` handles credentialed Energy Performance Certificate register requests, joined onto Property Check by postcode.
- The sponsor loader versions Home Office CSV snapshots and computes sponsor changes.
- The qualification loader combines Ofqual's qualification and organisation extracts into one version.
- The qualification expansion loaders version the Qualifications Wales register and Ofqual unit/mapping extracts independently.
- The study loaders version the UKVI student-sponsor CSV and Office for Students XLSX independently.
- The food loader streams the national FSA bulk file in bounded chunks.
- The postcode loader streams OS Code-Point Open CSV members directly from the official ZIP.
- The property loader combines the 2025 and 2026 HM Land Registry Price Paid files as one immutable snapshot.
- The GIAS loader streams the Department for Education's daily establishment CSV; the Ofsted loader streams the monthly state-funded schools inspection CSV independently. `school_lookup` joins the two by exact URN at read time.
- Area source clients aggregate Police.uk, Planning Data and Environment Agency responses without persisting transient results.

Search uses normalised identifiers and names. Composite dataset-version/search indexes keep food name and postcode prefix lookup bounded on the current 611,645-row snapshot. All detail lookups include the current version constraint so stale records from older snapshots cannot leak into responses.

Core persistence concepts are:

- `data_sources`
- `dataset_versions`
- `ingestion_runs`
- `companies`
- `sponsor_records`
- `awarding_organisation_records`
- `qualification_records`
- `qualification_expansion_records`
- `qualification_unit_records`
- `qualification_unit_mappings`
- `student_sponsor_records`
- `ofs_provider_records`
- `food_establishment_records`
- `postcode_records`
- `property_sale_records`
- `school_records`
- `ofsted_inspection_records`
- `entity_mappings`
- `change_events`

PostgreSQL is the intended deployment database. SQLite remains the zero-configuration local-development and test default.

## Deployment boundary

The repository runs as one web frontend, one API and one relational database. Background ingestion shares the backend domain package and can be invoked from the CLI or a scheduler. Redis, workers, object storage or external search should be added only when measured load requires them.

## Keeping bulk datasets current

`python -m app.cli refresh-due` (in `app/services/refresh.py`) fetches and re-ingests every bulk source whose own refresh cadence has elapsed, then exits. It is meant to be invoked by an external scheduler (cron) rather than run as a long-lived process inside the API.

- Each source has a fixed cadence (`REFRESH_SPECS`) matching its real publication frequency — 1 day for GIAS/food/Ofqual/worker- and student-sponsors, 7 days for OfS/QiW/Ofqual units, 28 days for Land Registry/Ofsted, 90 days for OS Code-Point Open — checked against `DataSource.last_successful_retrieval`, a timestamp every loader already sets on success. Nothing new needs to stay in sync for this to work.
- Sources with a stable, always-current URL (FSA, Ofqual, Ofqual units, QiW, OS Code-Point Open, OfS, Land Registry's per-year files) are re-fetched from the same constant each time.
- Sources whose file changes location every release (Ofsted, UKVI worker and student sponsors) are resolved through `app/services/govuk_content.py`, which reads GOV.UK's Content API (`/api/content/{path}`) and takes the most recent matching CSV attachment — attachments on a content item are appended in publication order, so the last match is current. This avoids hardcoding a URL that silently goes stale, the same failure mode the original student-sponsor URL had (it carried a specific publication date in the path).
- GIAS publishes a date-stamped file daily; `refresh.py` tries today's date and steps backward up to 7 days to tolerate a not-yet-published day.
- Companies House, EPC, Police.uk, Planning Data and Environment Agency are live per-request APIs and are not part of the refresh cadence — there is nothing to re-ingest.
- A source that is fetched too early is harmless: every loader compares the new file's SHA-256 to the current `DatasetVersion.file_hash` and records an `unchanged` ingestion run instead of duplicating data. The cadence table only avoids wasted bandwidth; correctness comes from the existing hash check.
