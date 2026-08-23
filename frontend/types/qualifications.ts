import type { SourceAttribution } from "./common";

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
