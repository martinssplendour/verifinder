import type { WatchlistAlert, WatchlistEntry } from "@/types";
import { apiFetch, apiMutation, apiPost } from "./client";

export function getWatchlist(signal?: AbortSignal) {
  return apiFetch<WatchlistEntry[]>("/watchlist", signal);
}

export function addWatchlistEntry(entityType: "company" | "area", entityId: string, label: string, signal?: AbortSignal) {
  return apiPost<WatchlistEntry>("/watchlist", { entity_type: entityType, entity_id: entityId, label }, signal);
}

export function updateWatchlistEntry(entryId: number, notificationsEnabled: boolean, signal?: AbortSignal) {
  return apiMutation<WatchlistEntry>(`/watchlist/${entryId}`, "PATCH", { notifications_enabled: notificationsEnabled }, signal);
}

export function removeWatchlistEntry(entryId: number, signal?: AbortSignal) {
  return apiMutation<{ status: string }>(`/watchlist/${entryId}`, "DELETE", undefined, signal);
}

export function getWatchlistAlerts(signal?: AbortSignal) {
  return apiFetch<WatchlistAlert[]>("/watchlist/alerts", signal);
}
