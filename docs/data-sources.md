# Data sources

## Companies House

- Organisation: Companies House
- Integration: official company-information API
- Usage: company search, profile and officer records
- Refresh model: requested on demand
- Credential: `COMPANIES_HOUSE_API_KEY`, server-side only
- Official developer site: <https://developer.company-information.service.gov.uk/>

Each live response includes the official company URL and retrieval timestamp. When the credential is absent, the API returns an explicit unavailable state with no substitute records.

## UK Visas and Immigration

- Dataset: Register of licensed sponsors: workers
- Format: official CSV linked from GOV.UK
- Usage: sponsor search, routes, rating, company matching and sponsor changes
- Official publication: <https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers>

The loader validates semantic columns, computes SHA-256, preserves the original file, loads normalised organisations and routes, and compares successful snapshots. Company Check queries only the latest successful version. A name match remains separately labelled as a sponsor-register record until the entity-resolution evidence is sufficient to connect it to a Companies House company.

Absence must be phrased as: “We couldn't find a matching organisation in the latest sponsor-register dataset.” It is not proof that a company cannot sponsor someone.

## UK Visas and Immigration — student sponsors

- Dataset: Register of licensed sponsors: students
- Format: official CSV linked from GOV.UK
- Usage: study-provider name search, sponsor type, status, licensed routes and location
- Official publication: <https://www.gov.uk/government/publications/register-of-licensed-sponsors-students>

The current snapshot contains 952 deduplicated provider records. Study Provider Check reports only what the register establishes: permission to sponsor students on the listed route. Sponsorship is not academic accreditation, course approval or a guarantee of an individual visa outcome.

## Office for Students

- Dataset: OfS Register
- Format: official XLSX download
- Usage: legal/trading-name and UKPRN search, registration category, degree-awarding powers, university title, TEF link, fee limits and access-plan information
- Geographic scope: registered higher-education providers in England
- Official guide and download: <https://www.officeforstudents.org.uk/for-providers/registering-with-the-ofs/guide-to-the-ofs-register/>

The current Register sheet contains 426 active providers. Exact normalised names may be cross-referenced with the student-sponsor register, but the records remain separate because OfS registration and UKVI sponsorship are different legal statuses. No exact cross-match is not treated as a negative finding.

## Ofqual

- Dataset: Register of Regulated Qualifications and recognised awarding organisations
- Format: official bulk CSV extracts
- Usage: qualification-number/title search and source-attributed qualification detail
- Geographic scope: qualifications regulated by Ofqual for England; records also expose whether a qualification is offered in Northern Ireland
- Official register: <https://www.gov.uk/find-a-regulated-qualification>
- API and bulk-download documentation: <https://www.api.gov.uk/ofqual/ofqual-register-of-regulated-qualifications-api/>

The combined loader validates both files, streams 52,727 qualifications and 351 organisations, hashes the pair as one snapshot, then stores level, type, status, awarding organisation, regulatory dates, learning hours, assessment methods and specification links where supplied. A separately versioned Ofqual expansion contains 303,936 unit records and 813,834 qualification-unit mappings. Qualification details expose up to the first 100 linked units and retain the full unit count.

Qualification Check reports the register record; it does not decide equivalence, professional recognition, university acceptance or immigration eligibility. Users should confirm the awarding organisation and current status and follow the official specification where a high-stakes decision depends on it.

## Qualifications Wales

- Dataset: Qualifications in Wales (QiW), complete English-language export
- Format: official CSV
- Usage: qualification number, approval/designation number, title and awarding-body search
- Geographic scope: Wales
- Official register: <https://www.qiw.wales/>

The loader removes exact duplicate approval identities from the source export and stores 33,010 records with status, level, type, language, review type, approval/designation dates and public-funding indicator where supplied. Welsh results are grouped under Qualifications Wales rather than presented as Ofqual records.

The Scottish qualification listing is not imported. The official Scottish accreditation page currently advertises a downloadable listing, but that download link returns `404`; VeriFinder does not substitute an unofficial dataset. This limitation is shown beside Qualification Check results.

## Food Standards Agency

- Dataset: Food Hygiene Rating Scheme open data
- Format: official UK bulk CSV
- Usage: establishment-name/postcode search and source-attributed hygiene-rating detail
- Geographic scope: United Kingdom
- Official open-data page: <https://ratings.food.gov.uk/open-data>
- Official API documentation: <https://api.ratings.food.gov.uk/help>

The loader validates and streams 611,645 establishments. It records the FHRS ID, business name/type, address, postcode, local authority, published rating, rating date, scheme, new-rating-pending flag, component scores and coordinates where supplied.

The UI preserves the source scheme because interpretation differs: FHRS publishes numeric ratings in England, Wales and Northern Ireland, while Scotland's FHIS uses outcome labels. A rating is a snapshot from the latest downloaded dataset, not a prediction of present conditions.

## Ordnance Survey and Area Check live sources

- Dataset: Code-Point Open, downloaded as an official ZIP of CSV members
- Usage: exact Great Britain postcode lookup and British National Grid coordinate anchor
- Official product: <https://www.ordnancesurvey.co.uk/products/code-point-open>
- Live enrichment: Police.uk street-level crime, Planning Data designations and Environment Agency current flood warnings

Area Check aggregates the latest three Police.uk months near the postcode point and does not expose individual incident records. Police locations are anonymised and the returned count is not a crime rate. Planning Data coverage varies by local authority and currently focuses on six selected designation datasets. Environment Agency warnings are current, England-only results within 10 km. Northern Ireland is outside Code-Point Open coverage.

## HM Land Registry

- Dataset: Price Paid Data, imported annual 2025 and year-to-date 2026 CSV files
- Usage: full-postcode or address-prefix search, property sale history and postcode price summary
- Geographic scope: England and Wales
- Official downloads: <https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads>

Property Check reports recorded sale transactions from the imported two-year snapshot. It is not a valuation, title search or complete ownership history. Planning designations are joined at postcode level rather than by title number or UPRN.

## Energy Performance Certificate register

- Organisation: Ministry of Housing, Communities and Local Government (MHCLG)
- Integration: Get energy performance of buildings data developer API (the successor to the retired `epc.opendatacommunities.org` service, which stopped serving requests on 30 May 2026)
- Usage: postcode-level domestic EPC certificate search, joined onto Property Check results
- Refresh model: requested on demand
- Credential: `EPC_API_KEY`, a GOV.UK One Login bearer token, server-side only
- Official developer site: <https://get-energy-performance-data.communities.gov.uk/>
- API technical documentation: <https://get-energy-performance-data.communities.gov.uk/api-technical-documentation/search-certificates/domestic>

Certificates are matched by postcode, not by UPRN or title number, so a returned certificate may describe a nearby property rather than the exact address shown in Property Check. When the credential is absent, the response returns an explicit unavailable state with no substitute records. The field mapping (certificate number, address lines, current energy-efficiency band, registration date, UPRN) has been verified against a live authenticated response.

## Get Information about Schools (GIAS)

- Organisation: Department for Education
- Dataset: GIAS establishment register (`edubasealldata`)
- Format: official daily-refreshed bulk CSV
- Usage: School Check establishment search and detail — name, URN, type, phase, capacity, pupils, address and headteacher
- Geographic scope: England
- Official developer site: <https://www.get-information-schools.service.gov.uk/>
- Bulk download: served from the DfE-Digital-documented `ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/` endpoint; the current site's own download page is a JavaScript application and does not expose a static bulk-download link

The loader validates the URN column, streams the CSV (Windows-1252 encoded), and versions the snapshot by content hash. The current import contains 52,484 establishment records. School Check joins the GIAS record to an Ofsted inspection outcome by exact URN; it does not merge the two registers into one status.

## Ofsted

- Organisation: Ofsted
- Dataset: State-funded school inspections and outcomes: management information
- Format: official monthly CSV
- Usage: School Check inspection outcome — latest full inspection (2025 framework), legacy single-grade (OEIF) result, and latest ungraded inspection, each shown separately with its own date
- Geographic scope: England, state-funded schools only
- Official publication: <https://www.gov.uk/government/statistical-data-sets/monthly-management-information-ofsteds-school-inspections-outcomes>

The current import contains 21,957 inspection records. Because Ofsted introduced a new inspection framework in September 2025, a school's most recent graded inspection may be reported under either the current category-based framework or the earlier single-grade (Outstanding/Good/Requires improvement/Inadequate) framework; School Check displays whichever is present without treating one as an update to the other. Independent schools, newly opened schools, and schools awaiting their first inspection will not have a matching Ofsted record — this is shown as "no matching URN", not as an unrated or failing result.

## Versioning and source health

Imported datasets retain the raw file, SHA-256 hash, retrieved/published timestamps, ingestion status and record count. Search and detail endpoints resolve against the latest successful version only.

Domain health values are:

- `healthy`
- `stale`
- `unavailable`
- `ingestion_failed`
- `schema_changed`

Stale or unavailable states remain visible rather than being interpreted as negative facts.
