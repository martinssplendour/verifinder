"use client";

import { FileText, CircleAlert } from "lucide-react";
import type { DecisionPlanResponse } from "@/types";

export function PlanReport({ plan }: { plan: DecisionPlanResponse }) {
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
