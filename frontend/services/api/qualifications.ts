import type { QualificationRecordView, QualificationSearchResponse } from "@/types";
import { apiFetch } from "./client";

export function searchQualifications(query: string, signal?: AbortSignal) {
  return apiFetch<QualificationSearchResponse>(`/qualifications/search?q=${encodeURIComponent(query)}`, signal);
}

export function getQualification(recordId: string, signal?: AbortSignal) {
  return apiFetch<QualificationRecordView>(`/qualifications/${encodeURIComponent(recordId)}`, signal);
}
