import type { SourceAttribution } from "./common";
import type { EPCSummary, PlanningSummary } from "./areas";

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
  suggestions: PropertySearchResult[];
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
