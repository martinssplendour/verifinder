import type { DecisionPlanResponse } from "@/types";

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function list(items: string[]): string {
  return items.length ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : "";
}

export function buildPlanReportHtml(plan: DecisionPlanResponse): string {
  const generated = new Date(plan.created_at).toLocaleString("en-GB", { dateStyle: "long", timeStyle: "short" });
  const scenarios = plan.scenarios.map((scenario) => `
    <section class="scenario">
      <span class="tag">${escapeHtml(scenario.location || "Candidate")}</span>
      <h3>${escapeHtml(scenario.title)}</h3>
      <p>${escapeHtml(scenario.description)}</p>
      <dl>${scenario.metrics.map((metric) => `<div><dt>${escapeHtml(metric.label)}</dt><dd>${escapeHtml(metric.value)}</dd></div>`).join("")}</dl>
      <div class="columns"><div><h4>Useful signals</h4>${list(scenario.strengths)}</div><div><h4>Tradeoffs</h4>${list(scenario.tradeoffs)}</div></div>
    </section>`).join("");
  const evidence = plan.evidence.map((item) => `
    <tr><td><span class="kind kind-${escapeHtml(item.kind)}">${escapeHtml(item.kind.replaceAll("_", " "))}</span></td><td><strong>${escapeHtml(item.title)}</strong><br><span>${escapeHtml(item.detail)}</span></td><td>${item.source ? `<a href="${escapeHtml(item.source.official_url)}">${escapeHtml(item.source.organisation)}</a><br><small>${escapeHtml(item.source.dataset)} · ${escapeHtml(item.source.version || "Current source")}</small>` : "—"}</td></tr>`).join("");
  const questions = plan.questions.map((item) => `<li><strong>${escapeHtml(item.question)}</strong><span>${escapeHtml(item.why_it_matters)}</span></li>`).join("");
  const steps = plan.steps.map((step) => `<li><span>${step.position}</span><div><strong>${escapeHtml(step.title)}</strong><p>${escapeHtml(step.description)}</p></div></li>`).join("");

  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(plan.title)} — VeriFinder</title><style>
  :root{--ink:#111a3a;--soft:#59657d;--brand:#2438a6;--line:#dde2eb;--green:#197645;--amber:#946000}*{box-sizing:border-box}body{margin:0;color:var(--ink);font:14px/1.5 Arial,sans-serif;background:#f5f7fb}.report{width:min(920px,calc(100% - 32px));margin:32px auto;padding:48px;background:#fff;box-shadow:0 8px 30px #1a264018}.brand{display:flex;justify-content:space-between;gap:20px;border-bottom:2px solid var(--ink);padding-bottom:18px}.brand strong{font-size:22px}.brand span{color:var(--soft);font-size:11px}.eyebrow,.tag,.kind{font-size:10px;font-weight:700;text-transform:uppercase;color:var(--brand)}h1{margin:8px 0;font-size:34px;line-height:1.12}h2{margin:34px 0 12px;font-size:20px}h3{margin:6px 0;font-size:17px}h4{margin:0 0 6px;font-size:12px}p{color:var(--soft)}.summary{font-size:16px}.meta{display:flex;gap:24px;color:var(--soft);font-size:11px}.scenario{margin:12px 0;padding:20px;border:1px solid var(--line);break-inside:avoid}.scenario dl{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.scenario dl div{padding:9px;background:#f7f8fb}.scenario dt{color:var(--soft);font-size:9px;text-transform:uppercase}.scenario dd{margin:2px 0 0;font-weight:700}.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:14px}.columns ul{margin:0;padding-left:18px;font-size:11px;color:var(--soft)}.questions{padding:16px 22px;background:#fff9eb}.questions li{margin:9px 0}.questions span{display:block;color:var(--soft);font-size:11px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left;font-size:11px}th{color:var(--soft);font-size:9px;text-transform:uppercase}.kind{display:inline-block;padding:3px 5px;background:#eef1ff}.kind-inference{color:var(--amber);background:#fff7df}.kind-unknown{color:#59657d;background:#eef0f4}.kind-calculated_finding{color:var(--brand)}.kind-verified_fact{color:var(--green);background:#eaf7ef}.timeline{padding:0;list-style:none}.timeline li{display:grid;grid-template-columns:28px 1fr;gap:10px;margin:12px 0}.timeline li>span{width:27px;height:27px;border-radius:50%;display:grid;place-items:center;color:#fff;background:var(--brand);font-size:10px;font-weight:700}.timeline p{margin:2px 0;font-size:11px}.boundary{margin-top:30px;padding:16px;border-top:1px solid var(--line);background:#f7f8fb}.boundary ul{font-size:10px;color:var(--soft)}footer{margin-top:30px;padding-top:14px;border-top:1px solid var(--line);color:var(--soft);font-size:9px}@media(max-width:650px){.report{width:100%;margin:0;padding:24px}.scenario dl,.columns{grid-template-columns:1fr}.brand{display:block}.meta{display:grid;gap:3px}}@media print{body{background:#fff}.report{width:100%;margin:0;padding:24px;box-shadow:none}.scenario{break-inside:avoid}@page{margin:14mm}}
  </style></head><body><main class="report"><header class="brand"><strong>VeriFinder</strong><span>Evidence-backed decision report<br>Check before you decide.</span></header><section><span class="eyebrow">${escapeHtml(plan.status)} decision report</span><h1>${escapeHtml(plan.title)}</h1><p class="summary">${escapeHtml(plan.summary)}</p><div class="meta"><span><strong>Goal:</strong> ${escapeHtml(plan.goal)}</span><span><strong>Generated:</strong> ${escapeHtml(generated)}</span><span><strong>Method:</strong> ${escapeHtml(plan.ai_mode === "gemini" ? "Gemini evidence synthesis" : "Evidence rules")}</span></div></section>${questions ? `<h2>Open questions</h2><ol class="questions">${questions}</ol>` : ""}<h2>Starting scenarios</h2>${scenarios || "<p>No location scenarios were available.</p>"}<h2>Evidence ledger</h2><table><thead><tr><th>Classification</th><th>Evidence</th><th>Source</th></tr></thead><tbody>${evidence}</tbody></table><h2>Action path</h2><ol class="timeline">${steps}</ol><section class="boundary"><h3>Decision boundary</h3>${list(plan.limitations)}</section><footer>Generated by VeriFinder from connected public-data sources. Re-check time-sensitive records before committing.</footer></main></body></html>`;
}

function reportFilename(plan: DecisionPlanResponse): string {
  const location = (plan.location || "decision").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `verifinder-${location || "decision"}-report.html`;
}

export function downloadPlanReport(plan: DecisionPlanResponse): void {
  const url = URL.createObjectURL(new Blob([buildPlanReportHtml(plan)], { type: "text/html;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = reportFilename(plan);
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function printPlanReport(plan: DecisionPlanResponse): void {
  const reportWindow = window.open("", "_blank");
  if (!reportWindow) return;
  reportWindow.document.open();
  reportWindow.document.write(buildPlanReportHtml(plan));
  reportWindow.document.close();
  reportWindow.focus();
  window.setTimeout(() => reportWindow.print(), 250);
}
