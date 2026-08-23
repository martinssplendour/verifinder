import type { SourceAttribution } from "./common";

export type DecisionEvidenceKind = "verified_fact" | "calculated_finding" | "inference" | "unknown";
export type AiMode = "gemini" | "deterministic";

export interface AskInterpretation {
  intent: "job_search" | "sponsor_discovery" | "qualification_search" | "study_provider_search" | "food_search" | "property_search" | "area_check" | "general";
  subject: string | null;
  location: string | null;
  industry: string | null;
  sponsorship_route: string | null;
  limit: number;
  assumptions: string[];
}

export interface DecisionFact {
  kind: DecisionEvidenceKind;
  label: string;
  value: string;
}

export interface AskResult {
  rank: number;
  id: string;
  result_type: string;
  title: string;
  subtitle: string | null;
  href: string;
  facts: DecisionFact[];
  why_it_matches: string[];
  source: SourceAttribution;
}

export interface AskResponse {
  question: string;
  conversation_id: string | null;
  context_turns_used: number;
  interpretation: AskInterpretation;
  headline: string;
  summary: string;
  results: AskResult[];
  total: number;
  limitations: string[];
  suggested_questions: string[];
  ai_mode: AiMode;
  generated_at: string;
}

export interface AskConversationTurn {
  question: string;
  headline: string;
  summary: string;
  interpretation: AskInterpretation;
  results: AskResult[];
}

export interface PlanRequest {
  goal: string;
  location?: string;
  budget?: number;
  priorities: string[];
  moving_date?: string;
  template: "relocation" | "study" | "employment" | "general";
}

export interface PlanQuestion {
  id: string;
  question: string;
  why_it_matters: string;
}

export interface PlanEvidence {
  id: string;
  kind: DecisionEvidenceKind;
  title: string;
  detail: string;
  source: SourceAttribution | null;
}

export interface PlanScenario {
  id: string;
  title: string;
  description: string;
  location: string | null;
  metrics: { label: string; value: string }[];
  strengths: string[];
  tradeoffs: string[];
  evidence_ids: string[];
}

export interface DecisionPlanResponse {
  id: string;
  title: string;
  goal: string;
  location: string | null;
  summary: string;
  status: string;
  questions: PlanQuestion[];
  scenarios: PlanScenario[];
  evidence: PlanEvidence[];
  steps: { position: number; title: string; description: string; status: "ready" | "needs_input" | "later"; evidence_ids: string[] }[];
  limitations: string[];
  ai_mode: AiMode;
  created_at: string;
}
