from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


VerificationStatus = Literal[
    "verified", "match_found", "possible_match", "no_match", "data_unavailable", "stale", "unknown"
]
DataMode = Literal["live", "unavailable"]


class SourceAttribution(BaseModel):
    id: str
    organisation: str
    dataset: str
    official_url: str
    retrieved_at: datetime | None = None
    published_at: datetime | None = None
    version: str | None = None
    health: str = "unknown"


class SearchResult(BaseModel):
    company_number: str
    company_name: str
    status: str | None = None
    location: str | None = None
    company_type: str | None = None
    data_mode: DataMode


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    data_mode: DataMode
    message: str | None = None


class SponsorRecordView(BaseModel):
    id: str
    organisation_name: str
    town_city: str | None = None
    county: str | None = None
    rating: str | None = None
    routes: list[str] = Field(default_factory=list)
    source: SourceAttribution


class SponsorSearchResponse(BaseModel):
    query: str
    results: list[SponsorRecordView]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class QualificationSearchResult(BaseModel):
    id: str
    qualification_number: str
    title: str
    awarding_organisation_name: str
    awarding_organisation_acronym: str | None = None
    level: str | None = None
    qualification_type: str | None = None
    status: str | None = None
    record_type: Literal["ofqual", "qiw"] = "ofqual"
    regulator: str = "Ofqual / CCEA Regulation"
    jurisdiction: str = "England and Northern Ireland"
    source: SourceAttribution


class QualificationSearchResponse(BaseModel):
    query: str
    results: list[QualificationSearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class QualificationRecordView(QualificationSearchResult):
    sector_subject_area: str | None = None
    regulation_start_date: date | None = None
    operational_start_date: date | None = None
    operational_end_date: date | None = None
    certification_end_date: date | None = None
    total_credits: float | None = None
    total_qualification_time: int | None = None
    guided_learning_hours: int | None = None
    offered_in_england: bool | None = None
    offered_in_northern_ireland: bool | None = None
    grading_type: str | None = None
    assessment_methods: str | None = None
    specification_url: str | None = None
    approval_number: str | None = None
    languages: list[str] = Field(default_factory=list)
    review_type: str | None = None
    eligible_public_funding: bool | None = None
    unit_count: int = 0
    units: list[QualificationUnitView] = Field(default_factory=list)


class QualificationUnitView(BaseModel):
    unit_reference: str | None = None
    title: str
    level: str | None = None
    credit_value: float | None = None
    guided_learning_hours: int | None = None


class StudyProviderSearchResult(BaseModel):
    id: str
    record_type: Literal["student_sponsor", "ofs"]
    name: str
    town_city: str | None = None
    provider_type: str | None = None
    status: str | None = None
    routes: list[str] = Field(default_factory=list)
    ukprn: str | None = None
    source: SourceAttribution


class StudyProviderSearchResponse(BaseModel):
    query: str
    results: list[StudyProviderSearchResult]
    total: int
    message: str | None = None


class StudyProviderDetail(BaseModel):
    id: str
    record_type: Literal["student_sponsor", "ofs"]
    name: str
    town_city: str | None = None
    provider_type: str | None = None
    status: str | None = None
    routes: list[str] = Field(default_factory=list)
    additional_locations: str | None = None
    immigration_compliance: str | None = None
    ukprn: str | None = None
    trading_names: list[str] = Field(default_factory=list)
    contact_address: str | None = None
    postcode: str | None = None
    email: str | None = None
    website: str | None = None
    charity_status: str | None = None
    registration_category: str | None = None
    fee_limits: str | None = None
    tef_rating: str | None = None
    degree_awarding_powers: str | None = None
    degree_awarding_powers_date: str | None = None
    university_title: bool | None = None
    university_title_date: str | None = None
    university_title_basis: str | None = None
    access_plan: bool | None = None
    access_plan_url: str | None = None
    specific_conditions: list[str] = Field(default_factory=list)
    matched_record: StudyProviderSearchResult | None = None
    source: SourceAttribution
    limitations: list[str] = Field(default_factory=list)


class OfstedInspectionSummary(BaseModel):
    status: Literal["matched", "data_unavailable"]
    urn: str | None = None
    most_recent_category_of_concern: str | None = None
    full_inspection_type: str | None = None
    full_inspection_start_date: date | None = None
    full_inspection_publication_date: date | None = None
    safeguarding_standards: str | None = None
    inclusion: str | None = None
    curriculum_and_teaching: str | None = None
    achievement: str | None = None
    attendance_and_behaviour: str | None = None
    personal_development_and_wellbeing: str | None = None
    early_years: str | None = None
    post_16_provision: str | None = None
    leadership_and_governance: str | None = None
    oeif_start_date: date | None = None
    oeif_publication_date: date | None = None
    oeif_overall_effectiveness: str | None = None
    oeif_safeguarding_effective: bool | None = None
    ungraded_inspection_date: date | None = None
    ungraded_publication_date: date | None = None
    ungraded_overall_outcome: str | None = None
    source: SourceAttribution | None = None
    message: str | None = None


class SchoolSearchResult(BaseModel):
    urn: str
    establishment_name: str
    la_name: str | None = None
    type_name: str | None = None
    phase_name: str | None = None
    status_name: str | None = None
    postcode: str | None = None
    town: str | None = None
    source: SourceAttribution


class SchoolSearchResponse(BaseModel):
    query: str
    results: list[SchoolSearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class SchoolDetail(BaseModel):
    urn: str
    establishment_name: str
    la_name: str | None = None
    type_name: str | None = None
    type_group_name: str | None = None
    status_name: str | None = None
    phase_name: str | None = None
    statutory_low_age: int | None = None
    statutory_high_age: int | None = None
    gender_name: str | None = None
    religious_character_name: str | None = None
    school_capacity: int | None = None
    number_of_pupils: int | None = None
    ukprn: str | None = None
    open_date: date | None = None
    close_date: date | None = None
    street: str | None = None
    locality: str | None = None
    town: str | None = None
    county_name: str | None = None
    postcode: str | None = None
    website: str | None = None
    telephone: str | None = None
    head_first_name: str | None = None
    head_last_name: str | None = None
    region_name: str | None = None
    country_name: str | None = None
    source: SourceAttribution
    ofsted: OfstedInspectionSummary
    limitations: list[str] = Field(default_factory=list)


class FoodEstablishmentSearchResult(BaseModel):
    id: str
    fhrs_id: str
    business_name: str
    business_type: str | None = None
    address: str | None = None
    postcode: str | None = None
    rating_value: str | None = None
    rating_date: date | None = None
    local_authority_name: str | None = None
    scheme_type: str | None = None
    new_rating_pending: bool | None = None
    source: SourceAttribution


class FoodSearchResponse(BaseModel):
    query: str
    results: list[FoodEstablishmentSearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class FoodEstablishmentView(FoodEstablishmentSearchResult):
    local_authority_business_id: str | None = None
    rating_key: str | None = None
    hygiene_score: int | None = None
    structural_score: int | None = None
    confidence_in_management_score: int | None = None
    longitude: float | None = None
    latitude: float | None = None


class PostcodePoint(BaseModel):
    postcode: str
    latitude: float
    longitude: float
    country_code: str | None = None
    admin_district_code: str | None = None
    admin_ward_code: str | None = None
    source: SourceAttribution


class CrimeMonth(BaseModel):
    month: str
    count: int


class CrimeCategoryCount(BaseModel):
    category: str
    count: int


class CrimeSummary(BaseModel):
    status: DataMode
    latest_month: str | None = None
    latest_total: int | None = None
    months: list[CrimeMonth] = Field(default_factory=list)
    categories: list[CrimeCategoryCount] = Field(default_factory=list)
    source_url: str
    message: str | None = None


class PlanningConstraint(BaseModel):
    dataset: str
    name: str
    reference: str | None = None
    start_date: date | None = None


class PlanningSummary(BaseModel):
    status: DataMode
    total: int | None = None
    constraints: list[PlanningConstraint] = Field(default_factory=list)
    source_url: str
    message: str | None = None


class EPCCertificate(BaseModel):
    certificate_number: str
    address: str
    postcode: str | None = None
    current_rating: str | None = None
    lodgement_date: str | None = None
    uprn: str | None = None


class EPCSummary(BaseModel):
    status: DataMode
    total: int | None = None
    certificates: list[EPCCertificate] = Field(default_factory=list)
    source_url: str
    message: str | None = None


class FloodWarning(BaseModel):
    severity: str
    severity_level: int
    description: str
    area: str | None = None
    time_raised: datetime | None = None
    time_message_changed: datetime | None = None


class FloodSummary(BaseModel):
    status: DataMode
    total: int | None = None
    warnings: list[FloodWarning] = Field(default_factory=list)
    radius_km: int = 10
    source_url: str
    message: str | None = None


class AreaCheckResponse(BaseModel):
    postcode: PostcodePoint
    crime: CrimeSummary
    planning: PlanningSummary
    flood: FloodSummary
    limitations: list[str] = Field(default_factory=list)


class PropertySale(BaseModel):
    transaction_id: str
    price: int
    transfer_date: date
    property_type: str | None = None
    new_build: bool | None = None
    tenure: str | None = None
    ppd_category: str | None = None


class PropertySearchResult(BaseModel):
    property_key: str
    address: str
    postcode: str | None = None
    latest_price: int
    latest_transfer_date: date
    property_type: str | None = None
    transaction_count: int
    source: SourceAttribution


class PropertySearchResponse(BaseModel):
    query: str
    results: list[PropertySearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class NearbySalesSummary(BaseModel):
    postcode: str
    count: int
    median_price: int | None = None
    minimum_price: int | None = None
    maximum_price: int | None = None


class PropertyDetail(BaseModel):
    property_key: str
    address: str
    postcode: str | None = None
    property_type: str | None = None
    town_city: str | None = None
    district: str | None = None
    county: str | None = None
    sales: list[PropertySale]
    nearby_sales: NearbySalesSummary | None = None
    planning: PlanningSummary
    epc: EPCSummary
    source: SourceAttribution
    limitations: list[str] = Field(default_factory=list)


class SponsorshipSummary(BaseModel):
    status: VerificationStatus
    label: str
    explanation: str
    routes: list[str] = Field(default_factory=list)
    rating: str | None = None
    match_confidence: float | None = None
    match_method: str | None = None
    source: SourceAttribution | None = None


class CompanyProfile(BaseModel):
    company_number: str
    company_name: str
    company_status: str | None
    incorporation_date: date | None
    registered_office: str | None
    postcode: str | None
    sic_codes: list[str] = Field(default_factory=list)
    company_type: str | None = None
    accounts_next_due: date | None = None
    verified_status: VerificationStatus
    data_mode: DataMode
    company_source: SourceAttribution
    sponsorship: SponsorshipSummary


class Officer(BaseModel):
    name: str
    role: str
    appointed_on: date | None = None
    resigned_on: date | None = None


class ChangeItem(BaseModel):
    id: str
    change_type: str
    title: str
    detected_at: datetime
    source: SourceAttribution


class SourceRegistryItem(BaseModel):
    id: str
    organisation: str
    name: str
    official_url: str
    source_type: str
    refresh_frequency: str
    health: str
    last_successful_retrieval: datetime | None = None
    integration_status: Literal["connected", "configured", "not_configured"]


DecisionEvidenceKind = Literal["verified_fact", "calculated_finding", "inference", "unknown"]
DecisionIntent = Literal[
    "sponsor_discovery",
    "qualification_search",
    "study_provider_search",
    "food_search",
    "property_search",
    "area_check",
    "general",
]
AiMode = Literal["gemini", "deterministic"]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=600)
    limit: int = Field(default=10, ge=1, le=20)


class AskInterpretation(BaseModel):
    intent: DecisionIntent
    subject: str | None = None
    location: str | None = None
    industry: str | None = None
    sponsorship_route: str | None = None
    limit: int = Field(default=10, ge=1, le=20)
    assumptions: list[str] = Field(default_factory=list)


class DecisionFact(BaseModel):
    kind: DecisionEvidenceKind
    label: str
    value: str


class AskResult(BaseModel):
    rank: int
    id: str
    result_type: str
    title: str
    subtitle: str | None = None
    href: str
    facts: list[DecisionFact] = Field(default_factory=list)
    why_it_matches: list[str] = Field(default_factory=list)
    source: SourceAttribution


class AskResponse(BaseModel):
    question: str
    interpretation: AskInterpretation
    headline: str
    summary: str
    results: list[AskResult]
    total: int
    limitations: list[str] = Field(default_factory=list)
    ai_mode: AiMode
    generated_at: datetime


class PlanRequest(BaseModel):
    goal: str = Field(min_length=5, max_length=1200)
    location: str | None = Field(default=None, max_length=180)
    budget: int | None = Field(default=None, ge=0)
    priorities: list[str] = Field(default_factory=list, max_length=8)
    moving_date: date | None = None
    template: Literal["relocation", "study", "employment", "general"] = "relocation"


class PlanQuestion(BaseModel):
    id: str
    question: str
    why_it_matters: str


class PlanEvidence(BaseModel):
    id: str
    kind: DecisionEvidenceKind
    title: str
    detail: str
    source: SourceAttribution | None = None


class PlanMetric(BaseModel):
    label: str
    value: str


class PlanScenario(BaseModel):
    id: str
    title: str
    description: str
    location: str | None = None
    metrics: list[PlanMetric] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    position: int
    title: str
    description: str
    status: Literal["ready", "needs_input", "later"] = "ready"
    evidence_ids: list[str] = Field(default_factory=list)


class DecisionPlanResponse(BaseModel):
    id: str
    title: str
    goal: str
    location: str | None = None
    summary: str
    status: str
    questions: list[PlanQuestion] = Field(default_factory=list)
    scenarios: list[PlanScenario] = Field(default_factory=list)
    evidence: list[PlanEvidence] = Field(default_factory=list)
    steps: list[PlanStep] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    ai_mode: AiMode
    created_at: datetime


class FeatureAllowance(BaseModel):
    allowed: bool
    reset_at: datetime | None = None
    word_limit: int | None = None


class AccountEntitlements(BaseModel):
    tier: Literal["free", "plus", "professional"]
    ask: FeatureAllowance
    planner: FeatureAllowance
    report_download: FeatureAllowance
    watchlists: FeatureAllowance


class AccountStatusResponse(BaseModel):
    authenticated: bool
    email: str | None = None
    entitlements: AccountEntitlements
    billing_configured: bool
    has_billing_account: bool = False


class CheckoutRequest(BaseModel):
    tier: Literal["plus", "professional"]
    cadence: Literal["monthly", "annual"] = "monthly"


class RedirectResponse(BaseModel):
    url: str


class ReportAccessResponse(BaseModel):
    allowed: bool


class SavedReportCreate(BaseModel):
    plan: DecisionPlanResponse


class SavedReportView(BaseModel):
    id: str
    source_report_id: str
    report_type: str
    title: str
    mime_type: str
    size_bytes: int
    provenance_count: int
    created_at: datetime


class SavedReportReady(BaseModel):
    report: SavedReportView
    download_url: str
    expires_at: datetime


class SignedDownloadResponse(BaseModel):
    url: str
    expires_at: datetime


class WatchlistEntryCreate(BaseModel):
    entity_type: Literal["company", "area", "school", "food", "qualification", "property", "sponsor"]
    entity_id: str = Field(min_length=1, max_length=120)
    label: str | None = Field(default=None, max_length=300)


class WatchlistEntryView(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    label: str | None
    notifications_enabled: bool
    created_at: datetime


class WatchlistEntryUpdate(BaseModel):
    notifications_enabled: bool


class WatchlistAlertView(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    summary: str
    detail: dict | None
    email_status: str
    created_at: datetime


class OperationCheckView(BaseModel):
    check_name: str
    status: str
    detail: dict | None
    checked_at: datetime
