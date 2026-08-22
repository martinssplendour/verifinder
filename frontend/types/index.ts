export type DataMode = "live" | "unavailable";
export type VerificationStatus =
  | "verified"
  | "match_found"
  | "possible_match"
  | "no_match"
  | "data_unavailable"
  | "stale"
  | "unknown";

export interface SourceAttribution {
  id: string;
  organisation: string;
  dataset: string;
  official_url: string;
  retrieved_at: string | null;
  published_at: string | null;
  version: string | null;
  health: string;
}

export interface SearchResult {
  company_number: string;
  company_name: string;
  status: string | null;
  location: string | null;
  company_type: string | null;
  data_mode: DataMode;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  data_mode: DataMode;
  message: string | null;
}

export interface SponsorRecordView {
  id: string;
  organisation_name: string;
  town_city: string | null;
  county: string | null;
  rating: string | null;
  routes: string[];
  source: SourceAttribution;
}

export interface SponsorSearchResponse {
  query: string;
  results: SponsorRecordView[];
  total: number;
  dataset_version: string | null;
  message: string | null;
}

export interface QualificationSearchResult {
  id: string;
  qualification_number: string;
  title: string;
  awarding_organisation_name: string;
  awarding_organisation_acronym: string | null;
  level: string | null;
  qualification_type: string | null;
  status: string | null;
  record_type: "ofqual" | "qiw";
  regulator: string;
  jurisdiction: string;
  source: SourceAttribution;
}

export interface QualificationSearchResponse {
  query: string;
  results: QualificationSearchResult[];
  total: number;
  dataset_version: string | null;
  message: string | null;
}

export interface QualificationRecordView extends QualificationSearchResult {
  sector_subject_area: string | null;
  regulation_start_date: string | null;
  operational_start_date: string | null;
  operational_end_date: string | null;
  certification_end_date: string | null;
  total_credits: number | null;
  total_qualification_time: number | null;
  guided_learning_hours: number | null;
  offered_in_england: boolean | null;
  offered_in_northern_ireland: boolean | null;
  grading_type: string | null;
  assessment_methods: string | null;
  specification_url: string | null;
  approval_number: string | null;
  languages: string[];
  review_type: string | null;
  eligible_public_funding: boolean | null;
  unit_count: number;
  units: QualificationUnit[];
}

export interface QualificationUnit {
  unit_reference: string | null;
  title: string;
  level: string | null;
  credit_value: number | null;
  guided_learning_hours: number | null;
}

export interface StudyProviderSearchResult {
  id: string;
  record_type: "student_sponsor" | "ofs";
  name: string;
  town_city: string | null;
  provider_type: string | null;
  status: string | null;
  routes: string[];
  ukprn: string | null;
  source: SourceAttribution;
}

export interface StudyProviderSearchResponse {
  query: string;
  results: StudyProviderSearchResult[];
  total: number;
  message: string | null;
}

export interface StudyProviderDetail extends StudyProviderSearchResult {
  additional_locations: string | null;
  immigration_compliance: string | null;
  trading_names: string[];
  contact_address: string | null;
  postcode: string | null;
  email: string | null;
  website: string | null;
  charity_status: string | null;
  registration_category: string | null;
  fee_limits: string | null;
  tef_rating: string | null;
  degree_awarding_powers: string | null;
  degree_awarding_powers_date: string | null;
  university_title: boolean | null;
  university_title_date: string | null;
  university_title_basis: string | null;
  access_plan: boolean | null;
  access_plan_url: string | null;
  specific_conditions: string[];
  matched_record: StudyProviderSearchResult | null;
  limitations: string[];
}

export interface FoodEstablishmentSearchResult {
  id: string;
  fhrs_id: string;
  business_name: string;
  business_type: string | null;
  address: string | null;
  postcode: string | null;
  rating_value: string | null;
  rating_date: string | null;
  local_authority_name: string | null;
  scheme_type: string | null;
  new_rating_pending: boolean | null;
  source: SourceAttribution;
}

export interface FoodSearchResponse {
  query: string;
  results: FoodEstablishmentSearchResult[];
  total: number;
  dataset_version: string | null;
  message: string | null;
}

export interface FoodEstablishmentView extends FoodEstablishmentSearchResult {
  local_authority_business_id: string | null;
  rating_key: string | null;
  hygiene_score: number | null;
  structural_score: number | null;
  confidence_in_management_score: number | null;
  longitude: number | null;
  latitude: number | null;
}

export interface PostcodePoint {
  postcode: string;
  latitude: number;
  longitude: number;
  country_code: string | null;
  admin_district_code: string | null;
  admin_ward_code: string | null;
  source: SourceAttribution;
}

export interface CrimeSummary {
  status: DataMode;
  latest_month: string | null;
  latest_total: number | null;
  months: { month: string; count: number }[];
  categories: { category: string; count: number }[];
  source_url: string;
  message: string | null;
}

export interface PlanningSummary {
  status: DataMode;
  total: number | null;
  constraints: { dataset: string; name: string; reference: string | null; start_date: string | null }[];
  source_url: string;
  message: string | null;
}

export interface EPCCertificate {
  certificate_number: string;
  address: string;
  postcode: string | null;
  current_rating: string | null;
  lodgement_date: string | null;
  uprn: string | null;
}

export interface EPCSummary {
  status: DataMode;
  total: number | null;
  certificates: EPCCertificate[];
  source_url: string;
  message: string | null;
}

export interface FloodSummary {
  status: DataMode;
  total: number | null;
  warnings: {
    severity: string;
    severity_level: number;
    description: string;
    area: string | null;
    time_raised: string | null;
    time_message_changed: string | null;
  }[];
  radius_km: number;
  source_url: string;
  message: string | null;
}

export interface AreaCheckResponse {
  postcode: PostcodePoint;
  crime: CrimeSummary;
  planning: PlanningSummary;
  flood: FloodSummary;
  limitations: string[];
}

export interface PropertySearchResult {
  property_key: string;
  address: string;
  postcode: string | null;
  latest_price: number;
  latest_transfer_date: string;
  property_type: string | null;
  transaction_count: number;
  source: SourceAttribution;
}

export interface PropertySearchResponse {
  query: string;
  results: PropertySearchResult[];
  total: number;
  dataset_version: string | null;
  message: string | null;
}

export interface PropertyDetail {
  property_key: string;
  address: string;
  postcode: string | null;
  property_type: string | null;
  town_city: string | null;
  district: string | null;
  county: string | null;
  sales: {
    transaction_id: string;
    price: number;
    transfer_date: string;
    property_type: string | null;
    new_build: boolean | null;
    tenure: string | null;
    ppd_category: string | null;
  }[];
  nearby_sales: {
    postcode: string;
    count: number;
    median_price: number | null;
    minimum_price: number | null;
    maximum_price: number | null;
  } | null;
  planning: PlanningSummary;
  epc: EPCSummary;
  source: SourceAttribution;
  limitations: string[];
}

export interface OfstedInspectionSummary {
  status: "matched" | "data_unavailable";
  urn: string | null;
  most_recent_category_of_concern: string | null;
  full_inspection_type: string | null;
  full_inspection_start_date: string | null;
  full_inspection_publication_date: string | null;
  safeguarding_standards: string | null;
  inclusion: string | null;
  curriculum_and_teaching: string | null;
  achievement: string | null;
  attendance_and_behaviour: string | null;
  personal_development_and_wellbeing: string | null;
  early_years: string | null;
  post_16_provision: string | null;
  leadership_and_governance: string | null;
  oeif_start_date: string | null;
  oeif_publication_date: string | null;
  oeif_overall_effectiveness: string | null;
  oeif_safeguarding_effective: boolean | null;
  ungraded_inspection_date: string | null;
  ungraded_publication_date: string | null;
  ungraded_overall_outcome: string | null;
  source: SourceAttribution | null;
  message: string | null;
}

export interface SchoolSearchResult {
  urn: string;
  establishment_name: string;
  la_name: string | null;
  type_name: string | null;
  phase_name: string | null;
  status_name: string | null;
  postcode: string | null;
  town: string | null;
  source: SourceAttribution;
}

export interface SchoolSearchResponse {
  query: string;
  results: SchoolSearchResult[];
  total: number;
  dataset_version: string | null;
  message: string | null;
}

export interface SchoolDetail {
  urn: string;
  establishment_name: string;
  la_name: string | null;
  type_name: string | null;
  type_group_name: string | null;
  status_name: string | null;
  phase_name: string | null;
  statutory_low_age: number | null;
  statutory_high_age: number | null;
  gender_name: string | null;
  religious_character_name: string | null;
  school_capacity: number | null;
  number_of_pupils: number | null;
  ukprn: string | null;
  open_date: string | null;
  close_date: string | null;
  street: string | null;
  locality: string | null;
  town: string | null;
  county_name: string | null;
  postcode: string | null;
  website: string | null;
  telephone: string | null;
  head_first_name: string | null;
  head_last_name: string | null;
  region_name: string | null;
  country_name: string | null;
  source: SourceAttribution;
  ofsted: OfstedInspectionSummary;
  limitations: string[];
}

export interface SponsorshipSummary {
  status: VerificationStatus;
  label: string;
  explanation: string;
  routes: string[];
  rating: string | null;
  match_confidence: number | null;
  match_method: string | null;
  source: SourceAttribution | null;
}

export interface CompanyProfile {
  company_number: string;
  company_name: string;
  company_status: string | null;
  incorporation_date: string | null;
  registered_office: string | null;
  postcode: string | null;
  sic_codes: string[];
  company_type: string | null;
  accounts_next_due: string | null;
  verified_status: VerificationStatus;
  data_mode: DataMode;
  company_source: SourceAttribution;
  sponsorship: SponsorshipSummary;
}

export interface SourceRegistryItem {
  id: string;
  organisation: string;
  name: string;
  official_url: string;
  source_type: string;
  refresh_frequency: string;
  health: string;
  last_successful_retrieval: string | null;
  integration_status: "connected" | "configured" | "not_configured";
}

export interface IngestionRun {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  records_processed: number;
  records_added: number;
  records_removed: number;
  records_changed: number;
  error_message: string | null;
}

export interface AdminSummary {
  data_mode: DataMode;
  sources: { total: number; healthy: number; attention: number };
  ingestion_runs: IngestionRun[];
  unresolved_matches: number;
  failed_imports: number;
  message: string;
  generated_at: string;
}

export type DecisionEvidenceKind = "verified_fact" | "calculated_finding" | "inference" | "unknown";
export type AiMode = "gemini" | "deterministic";

export interface AskInterpretation {
  intent: "sponsor_discovery" | "qualification_search" | "study_provider_search" | "food_search" | "property_search" | "area_check" | "general";
  subject: string | null;
  location: string | null;
  industry: string | null;
  sponsorship_route: string | null;
  limit: number;
  assumptions: string[];
}

export interface DecisionFact {
  kind: DecisionEvidenceKind;
  label: string;
  value: string;
}

export interface AskResult {
  rank: number;
  id: string;
  result_type: string;
  title: string;
  subtitle: string | null;
  href: string;
  facts: DecisionFact[];
  why_it_matches: string[];
  source: SourceAttribution;
}

export interface AskResponse {
  question: string;
  interpretation: AskInterpretation;
  headline: string;
  summary: string;
  results: AskResult[];
  total: number;
  limitations: string[];
  ai_mode: AiMode;
  generated_at: string;
}

export interface PlanRequest {
  goal: string;
  location?: string;
  budget?: number;
  priorities: string[];
  moving_date?: string;
  template: "relocation" | "study" | "employment" | "general";
}

export interface PlanQuestion {
  id: string;
  question: string;
  why_it_matters: string;
}

export interface PlanEvidence {
  id: string;
  kind: DecisionEvidenceKind;
  title: string;
  detail: string;
  source: SourceAttribution | null;
}

export interface PlanScenario {
  id: string;
  title: string;
  description: string;
  location: string | null;
  metrics: { label: string; value: string }[];
  strengths: string[];
  tradeoffs: string[];
  evidence_ids: string[];
}

export interface DecisionPlanResponse {
  id: string;
  title: string;
  goal: string;
  location: string | null;
  summary: string;
  status: string;
  questions: PlanQuestion[];
  scenarios: PlanScenario[];
  evidence: PlanEvidence[];
  steps: { position: number; title: string; description: string; status: "ready" | "needs_input" | "later"; evidence_ids: string[] }[];
  limitations: string[];
  ai_mode: AiMode;
  created_at: string;
}

export type SubscriptionTier = "free" | "plus" | "professional";

export interface FeatureAllowance {
  allowed: boolean;
  reset_at: string | null;
  word_limit: number | null;
}

export interface AccountStatus {
  authenticated: boolean;
  email: string | null;
  entitlements: {
    tier: SubscriptionTier;
    ask: FeatureAllowance;
    planner: FeatureAllowance;
    report_download: FeatureAllowance;
    watchlists: FeatureAllowance;
  };
  billing_configured: boolean;
  has_billing_account: boolean;
}

export interface SavedReport {
  id: string;
  source_report_id: string;
  report_type: string;
  title: string;
  mime_type: string;
  size_bytes: number;
  provenance_count: number;
  created_at: string;
}

export interface SavedReportReady {
  report: SavedReport;
  download_url: string;
  expires_at: string;
}

export interface WatchlistEntry {
  id: number;
  entity_type: string;
  entity_id: string;
  label: string | null;
  notifications_enabled: boolean;
  created_at: string;
}

export interface WatchlistAlert {
  id: number;
  entity_type: string;
  entity_id: string;
  summary: string;
  detail: Record<string, unknown> | null;
  email_status: string;
  created_at: string;
}
