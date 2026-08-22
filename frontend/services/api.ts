import type {
  AdminSummary,
  AreaCheckResponse,
  AskResponse,
  CompanyProfile,
  DecisionPlanResponse,
  FoodEstablishmentView,
  FoodSearchResponse,
  QualificationRecordView,
  QualificationSearchResponse,
  PropertyDetail,
  PropertySearchResponse,
  SchoolDetail,
  SchoolSearchResponse,
  SearchResponse,
  SourceRegistryItem,
  SponsorRecordView,
  SponsorSearchResponse,
  StudyProviderDetail,
  StudyProviderSearchResponse,
  PlanRequest,
  AccountStatus,
  SubscriptionTier,
  SavedReport,
  SavedReportReady,
  WatchlistAlert,
  WatchlistEntry,
} from "@/types";
import { getAccessToken } from "@/services/supabase";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "/api";

export class ApiError extends Error {
  code?: string;
  upgradeRequired = false;
  signInRequired = false;
  resetAt?: string;

  constructor(message: string, detail?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.code = typeof detail?.code === "string" ? detail.code : undefined;
    this.upgradeRequired = detail?.upgrade_required === true;
    this.signInRequired = detail?.sign_in_required === true;
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

async function apiFetch<T>(path: string, signal?: AbortSignal): Promise<T> {
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

async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
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

async function apiMutation<T>(path: string, method: "PATCH" | "DELETE", body?: unknown, signal?: AbortSignal): Promise<T> {
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

export function askVeriFinder(question: string, signal?: AbortSignal) {
  return apiPost<AskResponse>("/intelligence/ask", { question, limit: 10 }, signal);
}

export function createDecisionPlan(request: PlanRequest, signal?: AbortSignal) {
  return apiPost<DecisionPlanResponse>("/plans", request, signal);
}

export function searchCompanies(query: string, signal?: AbortSignal) {
  return apiFetch<SearchResponse>(`/search?q=${encodeURIComponent(query)}`, signal);
}

export function searchSponsors(query: string, signal?: AbortSignal) {
  return apiFetch<SponsorSearchResponse>(`/sponsors/search?q=${encodeURIComponent(query)}`, signal);
}

export function getSponsor(recordId: string, signal?: AbortSignal) {
  return apiFetch<SponsorRecordView>(`/sponsors/${encodeURIComponent(recordId)}`, signal);
}

export function searchQualifications(query: string, signal?: AbortSignal) {
  return apiFetch<QualificationSearchResponse>(`/qualifications/search?q=${encodeURIComponent(query)}`, signal);
}

export function getQualification(recordId: string, signal?: AbortSignal) {
  return apiFetch<QualificationRecordView>(`/qualifications/${encodeURIComponent(recordId)}`, signal);
}

export function searchStudyProviders(query: string, signal?: AbortSignal) {
  return apiFetch<StudyProviderSearchResponse>(`/study/search?q=${encodeURIComponent(query)}`, signal);
}

export function getStudyProvider(recordType: string, recordId: string, signal?: AbortSignal) {
  return apiFetch<StudyProviderDetail>(
    `/study/${encodeURIComponent(recordType)}/${encodeURIComponent(recordId)}`,
    signal,
  );
}

export function searchFood(query: string, signal?: AbortSignal) {
  return apiFetch<FoodSearchResponse>(`/food/search?q=${encodeURIComponent(query)}`, signal);
}

export function getFoodEstablishment(recordId: string, signal?: AbortSignal) {
  return apiFetch<FoodEstablishmentView>(`/food/${encodeURIComponent(recordId)}`, signal);
}

export function checkArea(postcode: string, signal?: AbortSignal) {
  return apiFetch<AreaCheckResponse>(`/areas/check?postcode=${encodeURIComponent(postcode)}`, signal);
}

export function searchProperties(query: string, signal?: AbortSignal) {
  return apiFetch<PropertySearchResponse>(`/properties/search?q=${encodeURIComponent(query)}`, signal);
}

export function getProperty(propertyKey: string, signal?: AbortSignal) {
  return apiFetch<PropertyDetail>(`/properties/${encodeURIComponent(propertyKey)}`, signal);
}

export function searchSchools(query: string, signal?: AbortSignal) {
  return apiFetch<SchoolSearchResponse>(`/schools/search?q=${encodeURIComponent(query)}`, signal);
}

export function getSchool(urn: string, signal?: AbortSignal) {
  return apiFetch<SchoolDetail>(`/schools/${encodeURIComponent(urn)}`, signal);
}

export function getCompany(companyNumber: string, signal?: AbortSignal) {
  return apiFetch<CompanyProfile>(`/companies/${encodeURIComponent(companyNumber)}`, signal);
}

export function getSources(signal?: AbortSignal) {
  return apiFetch<SourceRegistryItem[]>("/sources", signal);
}

export function getAdminSummary(signal?: AbortSignal) {
  return apiFetch<AdminSummary>("/admin/summary", signal);
}

export function getAccountStatus(signal?: AbortSignal) {
  return apiFetch<AccountStatus>("/account/me", signal);
}

export function createCheckout(tier: Exclude<SubscriptionTier, "free">, cadence: "monthly" | "annual" = "monthly", signal?: AbortSignal) {
  return apiPost<{ url: string }>("/billing/checkout", { tier, cadence }, signal);
}

export function openBillingPortal(signal?: AbortSignal) {
  return apiPost<{ url: string }>("/billing/portal", {}, signal);
}

export function authorizeReportDownload(signal?: AbortSignal) {
  return apiPost<{ allowed: boolean }>("/billing/report-access", {}, signal);
}

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
