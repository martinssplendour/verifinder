# VeriFinder

VeriFinder is a provenance-first public-data product built around one promise: **check before you decide**. It currently ships seven working checks:

- **Company Check** — Companies House records plus separately labelled Home Office sponsor-register matches.
- **Qualification Check** — Ofqual/CCEA records for England and Northern Ireland, Ofqual unit mappings, and the Qualifications Wales QiW register.
- **Food Check** — Food Standards Agency hygiene ratings across the UK, preserving the FHRS/FHIS scheme labels.
- **Area Check** — Ordnance Survey postcode points combined with Police.uk crime, Planning Data designations and Environment Agency flood warnings.
- **Property Check** — HM Land Registry 2025–2026 Price Paid transactions with postcode-level Planning Data context and Energy Performance Certificate ratings.
- **Study Provider Check** — UKVI licensed student sponsors and the Office for Students Register, kept as separate statuses with exact-name cross-links.
- **School Check** — the Department for Education's GIAS establishment register and the latest Ofsted inspection outcome, kept as separate statuses with an exact-URN cross-link.

Every imported result identifies its source, retrieval date and immutable dataset version. An unavailable source stays unavailable: the application does not insert demonstration records or treat a missing match as proof of a negative fact.

VeriFinder also ships two cross-dataset decision tools:

- **Ask VeriFinder** translates a natural-language question into a controlled query over sponsor, qualification, study, food, property and area data. Results are selected by deterministic database code and include the interpreted filters and limitations.
- **Planner** generates an evidence-backed decision report with scenarios, open questions and ordered next steps. Facts, calculated findings, inferences and unknowns are labelled separately. Decision-data access is database-enforced read-only; reports are generated and downloaded in the browser instead of being stored on the server.

Both tools work without an LLM. Setting `GEMINI_API_KEY` enables structured language interpretation and evidence-bounded plan synthesis through Google's Gemini API; the model is not allowed to query the database directly or introduce unsupported facts. `GEMINI_MODEL` controls the server-side model name and defaults to `gemini-2.5-flash`.

Accounts use Supabase passwordless email authentication. All public checks remain anonymous. Free visitors receive one Ask query of up to 20 words per rolling day and one Planner result per rolling seven days; enforcement is server-side and uses an authenticated user ID or a signed anonymous cookie plus a keyed network hash. Plus and Professional subscriptions remove those limits and enable report downloads.

## Repository layout

```text
backend/       FastAPI, source adapters, loaders, Alembic and tests
frontend/      Next.js, React and TypeScript UI
docs/          Architecture, sources and entity-resolution notes
raw-data/      Ignored local storage for preserved official input files
```

## Prerequisites

- Node.js 20+
- Python 3.12+
- SQLite for local ingestion, DuckDB for Parquet reads, and PostgreSQL 16+ for transactional deployment data
- A [Companies House developer API key](https://developer.company-information.service.gov.uk/) for live legal-company records
- A [GOV.UK One Login EPC API bearer token](https://get-energy-performance-data.communities.gov.uk/) for live Energy Performance Certificate data in Property Check

The backend defaults to a local SQLite public-data file. `PUBLIC_DATA_MODE=parquet` activates the production read path through DuckDB, while `TRANSACTION_DATABASE_URL` points entitlement and account writes at PostgreSQL. Copy `.env.example` to `.env` and set `COMPANIES_HOUSE_API_KEY` and `EPC_API_KEY` to enable those live sources; all private keys remain server-side.

## Production deployment

The root [`render.yaml`](render.yaml) defines one Frankfurt Starter service. A small supervisor starts FastAPI on an internal loopback port and Next.js on Render's public port. Next.js owns `verifinder.splendoure.com` and proxies `/api/*` internally, so browser requests remain same-origin without a second Render service.

The single service has a 6 GB encrypted persistent disk. On an empty disk it downloads the public, checksummed SQLite snapshot and verifies its SHA-256. The startup migration then exports every public table to a versioned, compressed Parquet snapshot, validates every table count, and atomically activates a DuckDB catalogue over those files. User, entitlement and billing writes use a separate Supabase PostgreSQL connection and never enter the public-data lake.

The databases and Parquet snapshots are never committed to Git. The recovery asset is a 649.1 MB gzip snapshot of the 3.47 GB SQLite source and has SHA-256 `4c81a7f6a2155fdece5b735c85ff74c4544048b8652ced7e6ef1b0ee4ecc457e`. Render secrets (`TRANSACTION_DATABASE_URL`, `SUBJECT_SIGNING_KEY`, `GEMINI_API_KEY`, `COMPANIES_HOUSE_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and optional `EPC_API_KEY`) remain server-side. Supabase and Stripe publishable identifiers are intentionally safe for the browser; no service-role or Stripe secret is exposed to Next.js.

Stripe Checkout and the Stripe-hosted customer portal are created only by authenticated FastAPI routes. Subscription access is synchronized exclusively from signature-verified, idempotent webhooks into `subscriptions`; the browser cannot promote its own tier. Configure `STRIPE_PLUS_PRICE_ID`, `STRIPE_PROFESSIONAL_PRICE_ID`, and the webhook endpoint `https://verifinder.splendoure.com/api/billing/webhook` before enabling checkout.

The disk-backed public-data lake keeps the requested one-service deployment and avoids an additional AWS/MinIO service. It intentionally remains single-instance; moving the same Parquet snapshots to S3-compatible storage later would remove that scaling constraint without changing the controlled query API.

## Run locally

Run the API:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m alembic -c billing_alembic.ini upgrade head
python -m uvicorn app.main:app --reload
```

Run the frontend in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. API documentation is at `http://localhost:8000/docs`.

## Public-data ingestion

Download source files from the official publishers and preserve them under `raw-data/`. The current local snapshots are:

- Ofqual: `raw-data/ofqual/20260821-organisations.csv` and `20260821-qualifications.csv`
- Food Standards Agency: `raw-data/food-standards-agency/food-hygiene/20260821-fhrs-all-en-GB.csv`
- Ordnance Survey: `raw-data/ordnance-survey/code-point-open/202608-codepo-gb.zip`
- HM Land Registry: `raw-data/hm-land-registry/price-paid/202608-pp-2025.csv` and `202608-pp-2026.csv`
- UKVI: `raw-data/home-office/student-sponsors/20260821-student-sponsors.csv`
- Office for Students: `raw-data/office-for-students/register/20260822-ofs-register.xlsx`
- Qualifications Wales: `raw-data/qualifications-wales/20260822-qiw-complete-en.csv`
- Ofqual expansion: `raw-data/ofqual/expansion/20260822-units.csv` and `20260822-qualification-units.csv`
- GIAS: `raw-data/department-for-education/gias/20260822-edubasealldata.csv`
- Ofsted: `raw-data/ofsted/inspections/20260731-latest-inspections.csv`

Import them from `backend/`:

```powershell
python -m app.cli ingest-qualifications ..\raw-data\ofqual\20260821-qualifications.csv ..\raw-data\ofqual\20260821-organisations.csv --published-at 2026-08-21
python -m app.cli ingest-food ..\raw-data\food-standards-agency\food-hygiene\20260821-fhrs-all-en-GB.csv --published-at 2026-08-21
python -m app.cli ingest-sponsors path\to\sponsor-register.csv --published-at YYYY-MM-DD
python -m app.cli ingest-postcodes ..\raw-data\ordnance-survey\code-point-open\202608-codepo-gb.zip --published-at 2026-08-01
python -m app.cli ingest-property-sales ..\raw-data\hm-land-registry\price-paid\202608-pp-2025.csv ..\raw-data\hm-land-registry\price-paid\202608-pp-2026.csv --published-at 2026-08-22
python -m app.cli ingest-study-providers ..\raw-data\home-office\student-sponsors\20260821-student-sponsors.csv ..\raw-data\office-for-students\register\20260822-ofs-register.xlsx --published-at 2026-08-21
python -m app.cli ingest-welsh-qualifications ..\raw-data\qualifications-wales\20260822-qiw-complete-en.csv --published-at 2026-08-22
python -m app.cli ingest-qualification-units ..\raw-data\ofqual\expansion\20260822-units.csv ..\raw-data\ofqual\expansion\20260822-qualification-units.csv --published-at 2026-08-22
python -m app.cli ingest-schools ..\raw-data\department-for-education\gias\20260822-edubasealldata.csv --published-at 2026-08-22
python -m app.cli ingest-ofsted-inspections ..\raw-data\ofsted\inspections\20260731-latest-inspections.csv --published-at 2026-07-31
```

Each loader validates its source schema, streams the source where applicable, computes a SHA-256 version identifier, writes an ingestion run and exposes only the latest successful version. Re-importing an identical successful snapshot is recorded as unchanged instead of duplicating records.

The current snapshots contain 52,727 Ofqual qualifications, 33,010 QiW qualifications, 303,936 Ofqual units, 813,834 qualification-unit links, 952 student sponsors, 426 OfS providers, 351 awarding organisations, 611,645 food establishments, 1,749,109 postcode points, 1,184,740 property sale records, 52,484 GIAS establishments and 21,957 Ofsted inspection records.

## Keeping bulk datasets current

`refresh-due` fetches and re-ingests only the sources whose own publish cadence has elapsed since they were last retrieved (GIAS daily, Land Registry/Ofsted monthly, OS Code-Point Open quarterly, and so on) — see [architecture.md](docs/architecture.md#keeping-bulk-datasets-current) for the per-source cadence and how each source's current file is located. Run it manually from `backend/`:

```powershell
python -m app.cli refresh-due
python -m app.cli refresh-due --source gias-establishments --force  # refresh one source regardless of cadence
```

On a Linux deployment, schedule it with cron — every source still respects its own cadence, so a nightly trigger is enough:

```cron
0 0 * * * cd /path/to/verifinder/backend && /path/to/venv/bin/python -m app.cli refresh-due >> /var/log/verifinder-refresh.log 2>&1
```

## Checks

```powershell
cd backend
python -m pytest
ruff check app tests

cd ..\frontend
npm run check
npm run build
```

## API routes

- `GET /api/search?q=`
- `GET /api/companies/{company_number}`
- `GET /api/companies/{company_number}/sponsorship`
- `GET /api/sponsors/search?q=`
- `GET /api/sponsors/{record_id}`
- `GET /api/qualifications/search?q=`
- `GET /api/qualifications/{record_id}`
- `GET /api/study/search?q=`
- `GET /api/study/{record_type}/{record_id}`
- `GET /api/food/search?q=`
- `GET /api/food/{record_id}`
- `GET /api/areas/check?postcode=`
- `GET /api/properties/search?q=`
- `GET /api/properties/{property_key}`
- `GET /api/schools/search?q=`
- `GET /api/schools/{urn}`
- `POST /api/intelligence/ask`
- `POST /api/plans`
- `GET /api/account/me`
- `POST /api/billing/checkout`
- `POST /api/billing/portal`
- `POST /api/billing/report-access`
- `POST /api/billing/webhook`
- `GET /api/changes`
- `GET /api/sources`
- `GET /api/admin/summary`

See [architecture](docs/architecture.md), [data sources](docs/data-sources.md), and [entity resolution](docs/entity-resolution.md) for implementation details.
