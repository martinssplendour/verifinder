import type { StudyProviderDetail, StudyProviderSearchResponse } from "@/types";
import { apiFetch } from "./client";

export function searchStudyProviders(query: string, signal?: AbortSignal) {
  return apiFetch<StudyProviderSearchResponse>(`/study/search?q=${encodeURIComponent(query)}`, signal);
}

export function getStudyProvider(recordType: string, recordId: string, signal?: AbortSignal) {
  return apiFetch<StudyProviderDetail>(
    `/study/${encodeURIComponent(recordType)}/${encodeURIComponent(recordId)}`,
    signal,
  );
}
