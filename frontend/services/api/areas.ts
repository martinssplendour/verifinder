import type { AreaCheckResponse } from "@/types";
import { apiFetch } from "./client";

export function checkArea(postcode: string, signal?: AbortSignal) {
  return apiFetch<AreaCheckResponse>(`/areas/check?postcode=${encodeURIComponent(postcode)}`, signal);
}
