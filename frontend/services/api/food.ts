import type { FoodEstablishmentView, FoodSearchResponse } from "@/types";
import { apiFetch } from "./client";

export function searchFood(query: string, signal?: AbortSignal) {
  return apiFetch<FoodSearchResponse>(`/food/search?q=${encodeURIComponent(query)}`, signal);
}

export function getFoodEstablishment(recordId: string, signal?: AbortSignal) {
  return apiFetch<FoodEstablishmentView>(`/food/${encodeURIComponent(recordId)}`, signal);
}
