import type { DataMode, SourceAttribution } from "./common";

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
