import type { DecisionPlanResponse, SavedReport, SavedReportReady } from "@/types";
import { apiFetch, apiMutation, apiPost } from "./client";

export function savePlanReport(plan: DecisionPlanResponse, signal?: AbortSignal) {
  return apiPost<SavedReportReady>("/reports", { plan }, signal);
}

export function getSavedReports(signal?: AbortSignal) {
  return apiFetch<SavedReport[]>("/reports", signal);
}

export function getSavedReportDownload(reportId: string, signal?: AbortSignal) {
  return apiPost<{ url: string; expires_at: string }>(`/reports/${encodeURIComponent(reportId)}/download`, {}, signal);
}

export function deleteSavedReport(reportId: string, signal?: AbortSignal) {
  return apiMutation<{ status: string }>(`/reports/${encodeURIComponent(reportId)}`, "DELETE", undefined, signal);
}
