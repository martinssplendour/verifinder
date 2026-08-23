import type { SchoolDetail, SchoolSearchResponse } from "@/types";
import { apiFetch } from "./client";

export function searchSchools(query: string, signal?: AbortSignal) {
  return apiFetch<SchoolSearchResponse>(`/schools/search?q=${encodeURIComponent(query)}`, signal);
}

export function getSchool(urn: string, signal?: AbortSignal) {
  return apiFetch<SchoolDetail>(`/schools/${encodeURIComponent(urn)}`, signal);
}
