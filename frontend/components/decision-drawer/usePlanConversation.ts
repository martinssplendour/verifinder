"use client";

import { useRef, useState } from "react";
import { ApiError, createDecisionPlan, savePlanReport } from "@/services/api";
import { downloadSignedReport } from "@/services/report";
import type { DecisionPlanResponse, PlanRequest } from "@/types";
import type { ChatMessage } from "./useAskConversation";

export type PlanStage = "goal" | "location" | "budget" | "priorities" | "date" | "report";
type PlanDraft = { goal: string; location: string; budget?: number; priorities: string[]; moving_date?: string };

const INITIAL_PLAN: ChatMessage[] = [{ id: 1, role: "assistant", text: "What decision are you planning? Describe the outcome you want in your own words." }];

type Options = {
  setLoading: (value: boolean) => void;
  setError: (value: string | null) => void;
  setUpgradePrompt: (value: boolean) => void;
  setInput: (value: string) => void;
  refreshAccount: () => Promise<void>;
};

export function usePlanConversation({ setLoading, setError, setUpgradePrompt, setInput, refreshAccount }: Options) {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_PLAN);
  const [stage, setStage] = useState<PlanStage>("goal");
  const [draft, setDraft] = useState<PlanDraft>({ goal: "", location: "", priorities: [] });
  const [report, setReport] = useState<DecisionPlanResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const nextId = useRef(10);

  function message(role: "assistant" | "user", text: string): ChatMessage {
    return { id: nextId.current++, role, text };
  }

  function reset() {
    setMessages(INITIAL_PLAN);
    setDraft({ goal: "", location: "", priorities: [] });
    setStage("goal");
    setReport(null);
    setError(null);
    setUpgradePrompt(false);
    setInput("");
  }

  async function generate(nextDraft: PlanDraft) {
    setLoading(true);
    setError(null);
    try {
      const request: PlanRequest = {
        goal: nextDraft.goal,
        location: nextDraft.location,
        budget: nextDraft.budget,
        priorities: nextDraft.priorities,
        moving_date: nextDraft.moving_date,
        template: "relocation",
      };
      const result = await createDecisionPlan(request);
      setReport(result);
      setMessages((current) => [...current, message("assistant", "Your evidence-backed report is ready. Review the open questions and download it when you’re satisfied.")]);
      setStage("report");
    } catch (requestError) {
      setError((requestError as Error).message);
      setUpgradePrompt(requestError instanceof ApiError && (requestError.upgradeRequired || requestError.signInRequired));
    } finally {
      setLoading(false);
    }
  }

  function submitText(value: string) {
    if (stage === "goal") {
      if (value.length < 5) {
        setError("Please describe the decision in a little more detail.");
        return;
      }
      setDraft((current) => ({ ...current, goal: value }));
      setMessages((current) => [...current, message("user", value), message("assistant", "Which town, city, area, or full postcode should the plan cover?")]);
      setStage("location");
    } else if (stage === "location") {
      setDraft((current) => ({ ...current, location: value }));
      setMessages((current) => [...current, message("user", value), message("assistant", "What is your purchase budget? Enter an amount without commas, or type “skip”.")]);
      setStage("budget");
    } else if (stage === "budget") {
      const skipped = value.toLowerCase() === "skip";
      const amount = Number(value.replace(/[£,$\s]/g, ""));
      if (!skipped && (!Number.isFinite(amount) || amount <= 0)) {
        setError("Enter a positive amount, or type “skip”.");
        return;
      }
      setDraft((current) => ({ ...current, budget: skipped ? undefined : amount }));
      setMessages((current) => [
        ...current,
        message("user", skipped ? "No budget supplied" : `£${amount.toLocaleString("en-GB")}`),
        message("assistant", "Select the priorities that should shape the comparison."),
      ]);
      setStage("priorities");
    } else if (stage === "date") {
      const skipped = value.toLowerCase() === "skip";
      if (!skipped && !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        setError("Use YYYY-MM-DD, or type “skip”.");
        return;
      }
      const nextDraft = { ...draft, moving_date: skipped ? undefined : value };
      setDraft(nextDraft);
      setMessages((current) => [...current, message("user", skipped ? "No move date supplied" : value)]);
      setInput("");
      void generate(nextDraft);
      return;
    }
    setInput("");
  }

  function togglePriority(priority: string) {
    setDraft((current) => ({
      ...current,
      priorities: current.priorities.includes(priority)
        ? current.priorities.filter((item) => item !== priority)
        : [...current.priorities, priority],
    }));
  }

  function confirmPriorities() {
    const label = draft.priorities.length ? draft.priorities.join(", ") : "No priorities selected";
    setMessages((current) => [...current, message("user", label), message("assistant", "When do you want to move? Use YYYY-MM-DD, or type “skip”.")]);
    setStage("date");
  }

  async function downloadReport() {
    if (!report) return;
    setError(null);
    setUpgradePrompt(false);
    setReportLoading(true);
    try {
      const saved = await savePlanReport(report);
      downloadSignedReport(saved.download_url);
    } catch (requestError) {
      setError((requestError as Error).message);
      setUpgradePrompt(requestError instanceof ApiError && (requestError.upgradeRequired || requestError.signInRequired));
      await refreshAccount();
    } finally {
      setReportLoading(false);
    }
  }

  return { messages, stage, draft, report, reportLoading, reset, submitText, togglePriority, confirmPriorities, downloadReport };
}
