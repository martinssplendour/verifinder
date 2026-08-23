import type { PropertyDetail, PropertySearchResponse } from "@/types";
import { apiFetch } from "./client";

export function searchProperties(query: string, signal?: AbortSignal) {
  return apiFetch<PropertySearchResponse>(`/properties/search?q=${encodeURIComponent(query)}`, signal);
}

export function getProperty(propertyKey: string, signal?: AbortSignal) {
  return apiFetch<PropertyDetail>(`/properties/${encodeURIComponent(propertyKey)}`, signal);
}
