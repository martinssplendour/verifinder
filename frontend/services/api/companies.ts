import type { CompanyProfile, SearchResponse } from "@/types";
import { apiFetch } from "./client";

export function searchCompanies(query: string, signal?: AbortSignal) {
  return apiFetch<SearchResponse>(`/search?q=${encodeURIComponent(query)}`, signal);
}

export function getCompany(companyNumber: string, signal?: AbortSignal) {
  return apiFetch<CompanyProfile>(`/companies/${encodeURIComponent(companyNumber)}`, signal);
}
