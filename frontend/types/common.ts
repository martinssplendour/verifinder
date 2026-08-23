export type DataMode = "live" | "unavailable";
export type VerificationStatus =
  | "verified"
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
  suggestions: SearchResult[];
}
