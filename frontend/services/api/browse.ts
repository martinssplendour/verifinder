import type { BrowseCatalogue, BrowseResponse } from "@/types";
import { apiFetch } from "./client";

export function getBrowseCatalogue(signal?: AbortSignal) {
  return apiFetch<BrowseCatalogue>("/browse", signal);
}

export function getBrowsePlaces(dataset: string, signal?: AbortSignal) {
  return apiFetch<string[]>(`/browse/${encodeURIComponent(dataset)}/places`, signal);
}

export function browseDataset(
  dataset: string,
  options: { country?: string | null; place?: string | null; page?: number } = {},
  signal?: AbortSignal,
) {
  const params = new URLSearchParams();
  if (options.country) params.set("country", options.country);
  if (options.place) params.set("place", options.place);
  if (options.page && options.page > 1) params.set("page", String(options.page));
  const query = params.toString();
  return apiFetch<BrowseResponse>(`/browse/${encodeURIComponent(dataset)}${query ? `?${query}` : ""}`, signal);
}
