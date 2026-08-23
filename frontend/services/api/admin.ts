import type { AdminSummary, SourceRegistryItem } from "@/types";
import { apiFetch } from "./client";

export function getSources(signal?: AbortSignal) {
  return apiFetch<SourceRegistryItem[]>("/sources", signal);
}

export function getAdminSummary(signal?: AbortSignal) {
  return apiFetch<AdminSummary>("/admin/summary", signal);
}
