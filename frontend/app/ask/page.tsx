"use client";

import { FormEvent, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  CircleAlert,
  Database,
  ExternalLink,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  Search,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import { askVeriFinder } from "@/services/api";
import type { AskResponse, DecisionEvidenceKind } from "@/types";

const EXAMPLES = [
  "Top 10 companies with worker sponsorship in Sheffield",
  "Show me technology companies with sponsorship",
  "Find cybersecurity qualifications",
  "Food hygiene records in Manchester",
];

const KIND_LABELS: Record<DecisionEvidenceKind, string> = {
  verified_fact: "Verified fact",
  calculated_finding: "Calculated",
  inference: "Inference",
  unknown: "Unknown",
};

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [data, setData] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  async function submit(event?: FormEvent, example?: string) {
    event?.preventDefault();
    const value = (example ?? question).trim();
    if (value.length < 3) return;
    if (example) setQuestion(example);
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      setData(await askVeriFinder(value, controller.signal));
    } catch (requestError) {
      if ((requestError as Error).name !== "AbortError") setError((requestError as Error).message);
    } finally {
      if (controllerRef.current === controller) setLoading(false);
    }
  }

  const interpretation = data?.interpretation;
  const filters = interpretation
    ? [
        ["Intent", interpretation.intent.replaceAll("_", " ")],
        ["Location", interpretation.location],
        ["Industry", interpretation.industry],
        ["Subject", interpretation.subject],
        ["Route", interpretation.sponsorship_route],
        ["Maximum results", String(interpretation.limit)],
      ].filter((item): item is [string, string] => Boolean(item[1]))
    : [];

  return (
    <div className="decision-page ask-page">
      <section className="shell decision-hero">
        <div className="decision-hero-copy">
          <span className="decision-icon"><MessageSquareText size={24} /></span>
          <span className="kicker">Ask VeriFinder</span>
          <h1>Ask one question across verified public data.</h1>
          <p>VeriFinder interprets your request, applies visible filters, and returns records with their source attached. It never treats an AI guess as a public-data fact.</p>
        </div>
        <div className="decision-guardrail"><BadgeCheck size={18} /><div><strong>Evidence executes the query</strong><span>Language AI can interpret your wording. The database decides which records match.</span></div></div>
      </section>

      <section className="shell ask-workspace">
        <form className="ask-composer" onSubmit={submit}>
          <label htmlFor="ask-question">What do you need to know?</label>
          <div className="ask-input-wrap">
            <Search size={20} aria-hidden="true" />
            <textarea
              id="ask-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="For example: show me licensed worker sponsors in Sheffield"
              rows={2}
              maxLength={600}
            />
            <button className="button ask-submit" disabled={loading || question.trim().length < 3} type="submit">
              {loading ? <LoaderCircle size={18} className="spin" /> : <Sparkles size={17} />}
              {loading ? "Checking…" : "Ask"}
            </button>
          </div>
          <div className="example-prompts" aria-label="Example questions">
            <span>Try:</span>
            {EXAMPLES.map((example) => <button key={example} type="button" onClick={() => submit(undefined, example)}>{example}</button>)}
          </div>
        </form>

        {error && <div className="decision-error" role="alert"><CircleAlert size={19} /><div><strong>Could not answer that question</strong><span>{error}</span></div></div>}

        {!data && !error && !loading && (
          <div className="ask-empty-grid">
            <article><Database size={21} /><h2>Six connected domains</h2><p>Sponsors, qualifications, study providers, food hygiene, recent property sales and postcode area checks.</p></article>
            <article><SlidersHorizontal size={21} /><h2>Visible interpretation</h2><p>You can see the intent, place, subject, industry signal and result limit used for every query.</p></article>
            <article><Lightbulb size={21} /><h2>Honest ranking</h2><p>Matches are ordered by relevance. VeriFinder does not invent hiring odds, quality scores or acceptance rates.</p></article>
          </div>
        )}

        {data && (
          <div className="ask-results-layout" aria-live="polite">
            <aside className="interpretation-panel">
              <div className="panel-heading"><SlidersHorizontal size={17} /><div><span className="kicker">Query receipt</span><h2>How this was interpreted</h2></div></div>
              <dl>{filters.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
              {interpretation?.assumptions.length ? <div className="assumption-box"><strong>Assumptions</strong>{interpretation.assumptions.map((item) => <p key={item}>{item}</p>)}</div> : null}
              <div className="ai-mode"><Sparkles size={14} /><span>{data.ai_mode === "gemini" ? "Gemini-interpreted query" : "Rule-based interpretation"}</span></div>
            </aside>

            <div className="ask-results-main">
              <div className="answer-heading"><div><span className="kicker">Evidence-backed answer</span><h2>{data.headline}</h2><p>{data.summary}</p></div><span>{data.total} returned</span></div>
              {data.results.length === 0 ? (
                <div className="decision-empty"><Search size={24} /><h3>No matching records</h3><p>Try a full postcode, a broader location, or a more specific public-data subject.</p></div>
              ) : (
                <div className="ask-result-list">
                  {data.results.map((result) => (
                    <article className="ask-result" key={`${result.result_type}-${result.id}`}>
                      <div className="result-rank" aria-label={`Rank ${result.rank}`}>{result.rank}</div>
                      <div className="ask-result-body">
                        <div className="ask-result-title"><div><span>{result.result_type.replaceAll("_", " ")}</span><h3>{result.title}</h3>{result.subtitle && <p>{result.subtitle}</p>}</div><Link href={result.href}>Open record <ArrowRight size={15} /></Link></div>
                        <div className="decision-facts">
                          {result.facts.map((fact) => <div key={`${fact.label}-${fact.value}`}><span className={`evidence-kind kind-${fact.kind}`}>{KIND_LABELS[fact.kind]}</span><small>{fact.label}</small><strong>{fact.value || "Not stated"}</strong></div>)}
                        </div>
                        <div className="match-reasons">{result.why_it_matches.map((reason) => <span key={reason}><BadgeCheck size={13} />{reason}</span>)}</div>
                        <a className="source-receipt" href={result.source.official_url} target="_blank" rel="noreferrer"><Database size={13} /><span>{result.source.organisation} · {result.source.dataset}{result.source.version ? ` · ${result.source.version}` : ""}</span><ExternalLink size={12} /></a>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              <div className="limitations-panel"><CircleAlert size={17} /><div><strong>What this answer does not claim</strong><ul>{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
