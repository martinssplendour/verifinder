import type { SponsorRecordView, SponsorSearchResponse } from "@/types";
import { apiFetch } from "./client";

export function searchSponsors(query: string, signal?: AbortSignal) {
  return apiFetch<SponsorSearchResponse>(`/sponsors/search?q=${encodeURIComponent(query)}`, signal);
}

export function suggestSponsors(query: string, signal?: AbortSignal) {
  return apiFetch<SponsorSearchResponse>(`/sponsors/suggestions?q=${encodeURIComponent(query)}&limit=4`, signal);
}

export function getSponsor(recordId: string, signal?: AbortSignal) {
  return apiFetch<SponsorRecordView>(`/sponsors/${encodeURIComponent(recordId)}`, signal);
}
