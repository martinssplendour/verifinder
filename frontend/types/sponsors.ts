import type { SourceAttribution } from "./common";

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
  suggestions: SponsorRecordView[];
}
