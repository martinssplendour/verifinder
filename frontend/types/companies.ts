import type { DataMode, SourceAttribution, VerificationStatus } from "./common";

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
