"use client";

import { FormEvent, useState } from "react";
import {
  BadgeCheck,
  CalendarDays,
  Check,
  CircleAlert,
  ClipboardCheck,
  Database,
  ExternalLink,
  HelpCircle,
  Lightbulb,
  LoaderCircle,
  MapPin,
  Route,
  Save,
  Sparkles,
  Download,
  WalletCards,
} from "lucide-react";
import { ApiError, createDecisionPlan, savePlanReport } from "@/services/api";
import { downloadSignedReport } from "@/services/report";
import type { DecisionEvidenceKind, DecisionPlanResponse, PlanRequest } from "@/types";
import { useAccount } from "@/components/Account";
import { SignInGate } from "@/components/SignInGate";

const PRIORITIES = ["Housing cost", "Work sponsorship", "Study", "Schools", "Crime", "Planning", "Flood risk"];
const KIND_LABELS: Record<DecisionEvidenceKind, string> = {
  verified_fact: "Verified fact",
  calculated_finding: "Calculated",
  inference: "Inference",
  unknown: "Unknown",
};

export default function PlanPage() {
  const { session, account, openAccount } = useAccount();
  const [goal, setGoal] = useState("I want the best relocation plan around Manchester");
  const [location, setLocation] = useState("Manchester");
  const [budget, setBudget] = useState("");
  const [movingDate, setMovingDate] = useState("");
  const [template, setTemplate] = useState<PlanRequest["template"]>("relocation");
  const [priorities, setPriorities] = useState<string[]>(["Housing cost", "Work sponsorship"]);
  const [data, setData] = useState<DecisionPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function togglePriority(priority: string) {
    setPriorities((current) => current.includes(priority) ? current.filter((item) => item !== priority) : [...current, priority]);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (goal.trim().length < 5) return;
    setLoading(true);
    setError(null);
    try {
      const response = await createDecisionPlan({
        goal: goal.trim(),
        location: location.trim() || undefined,
        budget: budget ? Number(budget) : undefined,
        priorities,
        moving_date: movingDate || undefined,
        template,
      });
      setData(response);
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function downloadReport() {
    if (!data) return;
    setError(null);
    setReportLoading(true);
    try {
      const saved = await savePlanReport(data);
      downloadSignedReport(saved.download_url);
    } catch (requestError) {
      setError((requestError as Error).message);
      if (requestError instanceof ApiError && requestError.upgradeRequired) {
        openAccount(account?.authenticated ? "plans" : "sign-in");
      }
    } finally {
      setReportLoading(false);
    }
  }

  return (
    <div className="decision-page plan-page">
      <section className="shell decision-hero plan-hero">
        <div className="decision-hero-copy">
          <span className="decision-icon"><Route size={24} /></span>
          <span className="kicker">VeriFinder Planner</span>
          <h1>Turn a difficult decision into a verifiable plan.</h1>
          <p>Describe the outcome you want. The planner finds usable evidence, exposes missing inputs, compares scenarios and orders the checks that should happen before you commit.</p>
        </div>
        <div className="decision-guardrail"><ClipboardCheck size={18} /><div><strong>Plans stay auditable</strong><span>Every conclusion is labelled as a fact, calculation, inference or unknown.</span></div></div>
      </section>

      <section className="shell plan-workspace">
        {!session ? (
          <SignInGate className="plan-signin-gate" feature="the Decision Planner" onSignIn={() => openAccount("sign-in")} />
        ) : (
        <form className="plan-brief" onSubmit={submit}>
          <div className="plan-form-heading"><div><span className="kicker">Decision brief</span><h2>What are you trying to achieve?</h2></div><span><Save size={14} /> Private PDF when saved</span></div>
          <label className="decision-field field-wide"><span>Your goal</span><textarea value={goal} onChange={(event) => setGoal(event.target.value)} rows={3} maxLength={1200} /></label>
          <div className="plan-form-grid">
            <label className="decision-field"><span><MapPin size={14} /> Target place</span><input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Town, city or full postcode" /></label>
            <label className="decision-field"><span><WalletCards size={14} /> Purchase budget</span><input type="number" min="0" value={budget} onChange={(event) => setBudget(event.target.value)} placeholder="Optional, e.g. 300000" /></label>
            <label className="decision-field"><span><CalendarDays size={14} /> Target move date</span><input type="date" value={movingDate} onChange={(event) => setMovingDate(event.target.value)} /></label>
            <label className="decision-field"><span><Route size={14} /> Plan type</span><select value={template} onChange={(event) => setTemplate(event.target.value as PlanRequest["template"])}><option value="relocation">Relocation</option><option value="employment">Employment</option><option value="study">Study</option><option value="general">General decision</option></select></label>
          </div>
          <fieldset className="priority-field"><legend>What matters most?</legend><div>{PRIORITIES.map((priority) => <button className={priorities.includes(priority) ? "is-selected" : ""} type="button" key={priority} onClick={() => togglePriority(priority)}>{priorities.includes(priority) && <Check size={13} />}{priority}</button>)}</div></fieldset>
          <button className="button plan-submit" type="submit" disabled={loading || goal.trim().length < 5}>{loading ? <LoaderCircle className="spin" size={18} /> : <Sparkles size={17} />}{loading ? "Building plan…" : "Build verified plan"}</button>
        </form>
        )}

        {error && <div className="decision-error" role="alert"><CircleAlert size={19} /><div><strong>Could not build this plan</strong><span>{error}</span></div></div>}
        {loading && !data && <div className="plan-loading"><LoaderCircle className="spin" size={22} /><div><strong>Matching your brief to the evidence</strong><span>Checking recent sales, sponsorship, study and school records…</span></div></div>}

        {data && (
          <div className="plan-output" aria-live="polite">
            <header className="plan-output-header"><div><span className="kicker">Generated decision report</span><h2>{data.title}</h2><p>{data.summary}</p><div className="standalone-report-actions"><button className="button" type="button" disabled={reportLoading} onClick={() => void downloadReport()}>{reportLoading ? <LoaderCircle className="spin" size={15} /> : <Download size={15} />}{reportLoading ? "Preparing secure PDF…" : "Save & download PDF"}</button></div></div><span className="ai-mode"><Sparkles size={14} />{data.ai_mode === "gemini" ? "Gemini evidence synthesis" : "Evidence rules"}</span></header>

            {data.questions.length > 0 && <section className="plan-questions"><div className="section-title"><HelpCircle size={18} /><div><span className="kicker">Open questions</span><h3>Answer these before calling anything “best”</h3></div></div><div className="question-grid">{data.questions.map((item) => <article key={item.id}><strong>{item.question}</strong><p>{item.why_it_matters}</p></article>)}</div></section>}

            <section className="plan-scenarios"><div className="section-title"><MapPin size={18} /><div><span className="kicker">Starting scenarios</span><h3>Evidence-backed places to investigate</h3></div></div>{data.scenarios.length ? <div className="scenario-grid">{data.scenarios.map((scenario) => <article className="scenario-card" key={scenario.id}><div className="scenario-top"><span>{scenario.location}</span><h4>{scenario.title}</h4><p>{scenario.description}</p></div><div className="scenario-metrics">{scenario.metrics.map((metric) => <div key={metric.label}><small>{metric.label}</small><strong>{metric.value}</strong></div>)}</div><div className="scenario-notes"><div><strong>Useful signal</strong>{scenario.strengths.map((item) => <p key={item}><BadgeCheck size={13} />{item}</p>)}</div><div><strong>Keep in mind</strong>{scenario.tradeoffs.map((item) => <p key={item}><CircleAlert size={13} />{item}</p>)}</div></div></article>)}</div> : <div className="decision-empty"><MapPin size={24} /><h3>No location scenarios yet</h3><p>Add a target town, city or postcode to match the property snapshot.</p></div>}</section>

            <section className="evidence-ledger"><div className="section-title"><Database size={18} /><div><span className="kicker">Evidence ledger</span><h3>What the plan knows—and how it knows it</h3></div></div><div className="evidence-list">{data.evidence.map((item) => <article key={item.id}><span className={`evidence-kind kind-${item.kind}`}>{KIND_LABELS[item.kind]}</span><div><h4>{item.title}</h4><p>{item.detail}</p>{item.source && <a href={item.source.official_url} target="_blank" rel="noreferrer">{item.source.organisation} · {item.source.dataset}<ExternalLink size={12} /></a>}</div><code>{item.id}</code></article>)}</div></section>

            <section className="plan-timeline"><div className="section-title"><Route size={18} /><div><span className="kicker">Action path</span><h3>What to do next</h3></div></div><ol>{data.steps.map((step) => <li key={step.position}><span>{step.position}</span><div><div><h4>{step.title}</h4><em className={`step-status status-${step.status}`}>{step.status.replace("_", " ")}</em></div><p>{step.description}</p></div></li>)}</ol></section>

            <div className="limitations-panel"><Lightbulb size={17} /><div><strong>Decision boundary</strong><ul>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
          </div>
        )}
      </section>
    </div>
  );
}
