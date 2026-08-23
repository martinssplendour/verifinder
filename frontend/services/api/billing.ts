import type { AccountStatus, SubscriptionTier } from "@/types";
import { apiFetch, apiPost } from "./client";

export function getAccountStatus(signal?: AbortSignal) {
  return apiFetch<AccountStatus>("/account/me", signal);
}

export function createCheckout(tier: Exclude<SubscriptionTier, "free">, cadence: "monthly" | "annual" = "monthly", signal?: AbortSignal) {
  return apiPost<{ url: string }>("/billing/checkout", { tier, cadence }, signal);
}

export function createCoinCheckout(pack: "coins_25" | "coins_75", signal?: AbortSignal) {
  return apiPost<{ url: string }>("/billing/coins/checkout", { pack }, signal);
}

export function openBillingPortal(signal?: AbortSignal) {
  return apiPost<{ url: string }>("/billing/portal", {}, signal);
}

export function authorizeReportDownload(signal?: AbortSignal) {
  return apiPost<{ allowed: boolean }>("/billing/report-access", {}, signal);
}
