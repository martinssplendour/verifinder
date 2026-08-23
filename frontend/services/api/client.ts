import { getAccessToken } from "@/services/supabase";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

export class ApiError extends Error {
  code?: string;
  upgradeRequired = false;
  signInRequired = false;
  paymentRequired = false;
  coinBalance = 0;
  resetAt?: string;

  constructor(message: string, detail?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.code = typeof detail?.code === "string" ? detail.code : undefined;
    this.upgradeRequired = detail?.upgrade_required === true;
    this.signInRequired = detail?.sign_in_required === true;
    this.paymentRequired = detail?.payment_required === true;
    this.coinBalance = typeof detail?.coin_balance === "number" ? detail.coin_balance : 0;
    this.resetAt = typeof detail?.reset_at === "string" ? detail.reset_at : undefined;
  }
}

async function requestHeaders(includeJson = false): Promise<HeadersInit> {
  const headers: Record<string, string> = {};
  if (includeJson) headers["Content-Type"] = "application/json";
  const token = await getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function responseError(response: Response, fallback: string): Promise<ApiError> {
  const payload = await response.json().catch(() => null);
  const detail = payload?.detail;
  if (typeof detail === "string") return new ApiError(detail);
  if (detail && typeof detail === "object") {
    return new ApiError(typeof detail.message === "string" ? detail.message : fallback, detail);
  }
  return new ApiError(fallback);
}

export async function apiFetch<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    signal,
    cache: "no-store",
    credentials: "include",
    headers: await requestHeaders(),
  });
  if (!response.ok) {
    throw await responseError(response, "Verified data is temporarily unavailable.");
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: await requestHeaders(true),
    body: JSON.stringify(body),
    signal,
    credentials: "include",
  });
  if (!response.ok) {
    throw await responseError(response, "VeriFinder could not complete that request.");
  }
  return response.json() as Promise<T>;
}

export async function apiMutation<T>(path: string, method: "PATCH" | "DELETE", body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: await requestHeaders(body !== undefined),
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
    credentials: "include",
  });
  if (!response.ok) throw await responseError(response, "VeriFinder could not complete that request.");
  return response.json() as Promise<T>;
}
