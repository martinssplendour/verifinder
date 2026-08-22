"use client";

import {
  createContext,
  FormEvent,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  Bot,
  Check,
  CircleAlert,
  Database,
  Download,
  FileText,
  LoaderCircle,
  MessageSquareText,
  Printer,
  RefreshCw,
  Route,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { askVeriFinder, createDecisionPlan } from "@/services/api";
import { downloadPlanReport, printPlanReport } from "@/services/report";
import type { AskResponse, DecisionPlanResponse, PlanRequest } from "@/types";

type DrawerMode = "ask" | "plan";
type PlanStage = "goal" | "location" | "budget" | "priorities" | "date" | "report";
type ChatMessage = { id: number; role: "assistant" | "user"; text: string; ask?: AskResponse };
type PlanDraft = { goal: string; location: string; budget?: number; priorities: string[]; moving_date?: string };

const PRIORITIES = ["Housing cost", "Work sponsorship", "Study", "Schools", "Crime", "Planning", "Flood risk"];
const INITIAL_ASK: ChatMessage[] = [{ id: 1, role: "assistant", text: "What would you like me to check? I can query sponsorship, qualifications, study providers, food hygiene, recent property sales and exact-postcode area evidence." }];
const INITIAL_PLAN: ChatMessage[] = [{ id: 1, role: "assistant", text: "What decision are you planning? Describe the outcome you want in your own words." }];

const DecisionDrawerContext = createContext<{ openDrawer: (mode: DrawerMode) => void } | null>(null);

export function DecisionTrigger({ mode, className, children }: { mode: DrawerMode; className?: string; children: ReactNode }) {
  const context = useContext(DecisionDrawerContext);
  return <button type="button" className={className} onClick={() => context?.openDrawer(mode)} aria-haspopup="dialog">{children}</button>;
}

function AskAnswer({ answer, close }: { answer: AskResponse; close: () => void }) {
  return (
    <div className="drawer-answer">
      <div className="drawer-answer-head"><div><span>{answer.ai_mode === "gemini" ? "Gemini-interpreted query" : "Evidence-rule query"}</span><strong>{answer.headline}</strong></div><BadgeCheck size={18} /></div>
      <div className="drawer-query-chips">
        <span>{answer.interpretation.intent.replaceAll("_", " ")}</span>
        {answer.interpretation.location && <span>{answer.interpretation.location}</span>}
        {answer.interpretation.industry && <span>{answer.interpretation.industry}</span>}
        {answer.interpretation.subject && <span>{answer.interpretation.subject}</span>}
      </div>
      {answer.results.length ? <div className="drawer-result-list">{answer.results.map((result) => (
        <Link href={result.href} onClick={close} key={`${result.result_type}-${result.id}`}>
          <span>{result.rank}</span><div><strong>{result.title}</strong><small>{result.subtitle || result.result_type.replaceAll("_", " ")}</small><em><Database size={11} />{result.source.organisation}</em></div><ArrowRight size={15} />
        </Link>
      ))}</div> : <div className="drawer-no-results"><CircleAlert size={17} /><span>No records matched those interpreted filters.</span></div>}
      <div className="drawer-boundary"><strong>Boundary</strong>{answer.limitations.map((item) => <p key={item}>{item}</p>)}</div>
    </div>
  );
}

function PlanReport({ plan }: { plan: DecisionPlanResponse }) {
  return (
    <div className="drawer-report">
      <div className="drawer-report-title"><span><FileText size={17} /></span><div><small>Generated decision report</small><strong>{plan.title}</strong></div></div>
      <p className="drawer-report-summary">{plan.summary}</p>
      {plan.questions.length > 0 && <div className="drawer-report-section"><h4>Open questions</h4>{plan.questions.map((item) => <div className="drawer-report-question" key={item.id}><CircleAlert size={13} /><span><strong>{item.question}</strong><small>{item.why_it_matters}</small></span></div>)}</div>}
      <div className="drawer-report-section"><h4>Starting scenarios</h4>{plan.scenarios.length ? plan.scenarios.map((scenario) => <article className="drawer-scenario" key={scenario.id}><div><span>{scenario.location}</span><strong>{scenario.title}</strong></div><dl>{scenario.metrics.map((metric) => <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}</dd></div>)}</dl></article>) : <p>No location scenarios were available.</p>}</div>
      <div className="drawer-report-section"><h4>Evidence ledger</h4><div className="drawer-evidence-summary">{(["verified_fact", "calculated_finding", "inference", "unknown"] as const).map((kind) => <div key={kind}><strong>{plan.evidence.filter((item) => item.kind === kind).length}</strong><span>{kind.replaceAll("_", " ")}</span></div>)}</div></div>
      <div className="drawer-report-section"><h4>Action path</h4><ol className="drawer-action-path">{plan.steps.map((step) => <li key={step.position}><span>{step.position}</span><div><strong>{step.title}</strong><small>{step.description}</small></div></li>)}</ol></div>
    </div>
  );
}

export function DecisionDrawerProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<DrawerMode | null>(null);
  const [askMessages, setAskMessages] = useState<ChatMessage[]>(INITIAL_ASK);
  const [planMessages, setPlanMessages] = useState<ChatMessage[]>(INITIAL_PLAN);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [planStage, setPlanStage] = useState<PlanStage>("goal");
  const [planDraft, setPlanDraft] = useState<PlanDraft>({ goal: "", location: "", priorities: [] });
  const [planReport, setPlanReport] = useState<DecisionPlanResponse | null>(null);
  const nextId = useRef(10);
  const closeButton = useRef<HTMLButtonElement | null>(null);
  const conversationEnd = useRef<HTMLDivElement | null>(null);

  const close = useCallback(() => setMode(null), []);
  const openDrawer = useCallback((nextMode: DrawerMode) => {
    setMode(nextMode);
    setInput("");
    setError(null);
  }, []);

  useEffect(() => {
    if (!mode) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const keydown = (event: KeyboardEvent) => { if (event.key === "Escape") close(); };
    window.addEventListener("keydown", keydown);
    return () => { document.body.style.overflow = previousOverflow; window.removeEventListener("keydown", keydown); };
  }, [mode, close]);

  useEffect(() => {
    conversationEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [askMessages, planMessages, loading, planReport]);

  function message(role: "assistant" | "user", text: string, ask?: AskResponse): ChatMessage {
    return { id: nextId.current++, role, text, ask };
  }

  async function submitAsk(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (question.length < 3 || loading) return;
    setInput("");
    setError(null);
    setAskMessages((current) => [...current, message("user", question)]);
    setLoading(true);
    try {
      const answer = await askVeriFinder(question);
      setAskMessages((current) => [...current, message("assistant", answer.summary, answer)]);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function resetPlan() {
    setPlanMessages(INITIAL_PLAN);
    setPlanDraft({ goal: "", location: "", priorities: [] });
    setPlanStage("goal");
    setPlanReport(null);
    setError(null);
    setInput("");
  }

  function submitPlanText(event: FormEvent) {
    event.preventDefault();
    const value = input.trim();
    if (!value || loading) return;
    setError(null);
    if (planStage === "goal") {
      if (value.length < 5) { setError("Please describe the decision in a little more detail."); return; }
      setPlanDraft((current) => ({ ...current, goal: value }));
      setPlanMessages((current) => [...current, message("user", value), message("assistant", "Which town, city, area, or full postcode should the plan cover?")]);
      setPlanStage("location");
    } else if (planStage === "location") {
      setPlanDraft((current) => ({ ...current, location: value }));
      setPlanMessages((current) => [...current, message("user", value), message("assistant", "What is your purchase budget? Enter an amount without commas, or type “skip”.")]);
      setPlanStage("budget");
    } else if (planStage === "budget") {
      const skipped = value.toLowerCase() === "skip";
      const amount = Number(value.replace(/[£,$\s]/g, ""));
      if (!skipped && (!Number.isFinite(amount) || amount <= 0)) { setError("Enter a positive amount, or type “skip”."); return; }
      setPlanDraft((current) => ({ ...current, budget: skipped ? undefined : amount }));
      setPlanMessages((current) => [...current, message("user", skipped ? "No budget supplied" : `£${amount.toLocaleString("en-GB")}`), message("assistant", "Select the priorities that should shape the comparison.")]);
      setPlanStage("priorities");
    } else if (planStage === "date") {
      const skipped = value.toLowerCase() === "skip";
      if (!skipped && !/^\d{4}-\d{2}-\d{2}$/.test(value)) { setError("Use YYYY-MM-DD, or type “skip”."); return; }
      const draft = { ...planDraft, moving_date: skipped ? undefined : value };
      setPlanDraft(draft);
      setPlanMessages((current) => [...current, message("user", skipped ? "No move date supplied" : value)]);
      setInput("");
      void generatePlan(draft);
      return;
    }
    setInput("");
  }

  function togglePriority(priority: string) {
    setPlanDraft((current) => ({ ...current, priorities: current.priorities.includes(priority) ? current.priorities.filter((item) => item !== priority) : [...current.priorities, priority] }));
  }

  function confirmPriorities() {
    const label = planDraft.priorities.length ? planDraft.priorities.join(", ") : "No priorities selected";
    setPlanMessages((current) => [...current, message("user", label), message("assistant", "When do you want to move? Use YYYY-MM-DD, or type “skip”.")]);
    setPlanStage("date");
  }

  async function generatePlan(draft: PlanDraft) {
    setLoading(true);
    setError(null);
    try {
      const request: PlanRequest = { goal: draft.goal, location: draft.location, budget: draft.budget, priorities: draft.priorities, moving_date: draft.moving_date, template: "relocation" };
      const report = await createDecisionPlan(request);
      setPlanReport(report);
      setPlanMessages((current) => [...current, message("assistant", "Your evidence-backed report is ready. Review the open questions and download it when you’re satisfied.")]);
      setPlanStage("report");
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const messages = mode === "ask" ? askMessages : planMessages;
  const planPlaceholder = planStage === "goal" ? "Describe your decision…" : planStage === "location" ? "Town, city, area or postcode…" : planStage === "budget" ? "Budget amount or skip…" : planStage === "date" ? "YYYY-MM-DD or skip…" : "";

  return (
    <DecisionDrawerContext.Provider value={{ openDrawer }}>
      {children}
      {mode && <div className="decision-drawer-layer">
        <button className="drawer-backdrop" onClick={close} aria-label="Close decision assistant" />
        <section className="decision-drawer" role="dialog" aria-modal="true" aria-labelledby="decision-drawer-title">
          <header className="drawer-header">
            <div><span className="drawer-header-icon">{mode === "ask" ? <MessageSquareText size={18} /> : <Route size={18} />}</span><div><strong id="decision-drawer-title">{mode === "ask" ? "Ask VeriFinder" : "Decision Planner"}</strong><small>Evidence-backed · database read-only</small></div></div>
            <button ref={closeButton} type="button" onClick={close} aria-label="Close"><X size={20} /></button>
          </header>
          <div className="drawer-mode-switch" role="tablist" aria-label="Decision assistant mode">
            <button role="tab" aria-selected={mode === "ask"} className={mode === "ask" ? "is-active" : ""} onClick={() => openDrawer("ask")}><MessageSquareText size={15} />Ask</button>
            <button role="tab" aria-selected={mode === "plan"} className={mode === "plan" ? "is-active" : ""} onClick={() => openDrawer("plan")}><Route size={15} />Plan</button>
          </div>
          <div className="drawer-conversation">
            {messages.map((item) => <div className={`chat-row chat-${item.role}`} key={item.id}>{item.role === "assistant" && <span className="chat-avatar"><Bot size={15} /></span>}<div className="chat-content"><p>{item.text}</p>{item.ask && <AskAnswer answer={item.ask} close={close} />}</div></div>)}
            {mode === "plan" && planStage === "priorities" && <div className="priority-conversation"><div>{PRIORITIES.map((priority) => <button type="button" className={planDraft.priorities.includes(priority) ? "is-selected" : ""} onClick={() => togglePriority(priority)} key={priority}>{planDraft.priorities.includes(priority) && <Check size={12} />}{priority}</button>)}</div><button className="button" type="button" onClick={confirmPriorities}>Continue <ArrowRight size={15} /></button></div>}
            {loading && <div className="chat-row chat-assistant"><span className="chat-avatar"><Sparkles size={15} /></span><div className="chat-thinking"><LoaderCircle className="spin" size={16} /><span>{mode === "ask" ? "Querying connected records…" : "Building the evidence report…"}</span></div></div>}
            {error && <div className="drawer-chat-error" role="alert"><CircleAlert size={15} /><span>{error}</span></div>}
            {mode === "plan" && planReport && <PlanReport plan={planReport} />}
            <div ref={conversationEnd} />
          </div>
          <footer className="drawer-composer">
            {mode === "ask" ? <form onSubmit={submitAsk}><textarea aria-label="Ask a question" rows={1} value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a verified-data question…" /><button type="submit" disabled={loading || input.trim().length < 3} aria-label="Send question"><Send size={17} /></button></form> : planStage === "report" && planReport ? <div className="report-actions"><button className="button" type="button" onClick={() => downloadPlanReport(planReport)}><Download size={16} />Download report</button><button className="drawer-secondary-action" type="button" onClick={() => printPlanReport(planReport)}><Printer size={16} />Print / save PDF</button><button className="drawer-icon-action" type="button" onClick={resetPlan} aria-label="Start a new plan"><RefreshCw size={17} /></button></div> : planStage === "priorities" ? <p className="drawer-helper"><BadgeCheck size={14} />Choose any number of priorities, then continue.</p> : <form onSubmit={submitPlanText}><textarea aria-label="Reply to planner" rows={1} value={input} onChange={(event) => setInput(event.target.value)} placeholder={planPlaceholder} /><button type="submit" disabled={loading || !input.trim()} aria-label="Send reply"><Send size={17} /></button></form>}
            <small><Database size={11} />Connected records are queried read-only. Conversation content is not saved by VeriFinder.</small>
          </footer>
        </section>
      </div>}
    </DecisionDrawerContext.Provider>
  );
}
