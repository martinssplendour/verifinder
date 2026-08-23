import type { SourceAttribution } from "./common";

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
  suggestions: SchoolSearchResult[];
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
