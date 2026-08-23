import type { SourceAttribution } from "./common";

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
  suggestions: FoodEstablishmentSearchResult[];
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
