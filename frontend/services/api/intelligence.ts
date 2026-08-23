import type { AskConversationTurn, AskResponse, DecisionPlanResponse, PlanRequest } from "@/types";
import { apiMutation, apiPost } from "./client";

export function askVeriFinder(
  question: string,
  conversation: AskResponse[] = [],
  signal?: AbortSignal,
  conversationId?: string | null,
) {
  const context: AskConversationTurn[] = conversation.slice(-6).map((turn) => ({
    question: turn.question,
    headline: turn.headline,
    summary: turn.summary,
    interpretation: turn.interpretation,
    results: turn.results.slice(0, 10),
  }));
  return apiPost<AskResponse>(
    "/intelligence/ask",
    { question, limit: 10, conversation_id: conversationId || undefined, conversation: context },
    signal,
  );
}

export function clearAskConversation(conversationId: string, signal?: AbortSignal) {
  return apiMutation<{ status: string }>(
    `/intelligence/conversations/${encodeURIComponent(conversationId)}`,
    "DELETE",
    undefined,
    signal,
  );
}

export function createDecisionPlan(request: PlanRequest, signal?: AbortSignal) {
  return apiPost<DecisionPlanResponse>("/plans", request, signal);
}
