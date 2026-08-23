import type { SourceAttribution } from "./common";

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
