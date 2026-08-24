"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  CircleAlert,
  Coins,
  Database,
  ExternalLink,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  Search,
  SlidersHorizontal,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useAccount } from "@/components/Account";
import { CoinPaywall, type CoinPack } from "@/components/CoinPaywall";
import { SignInGate } from "@/components/SignInGate";
import { ApiError, askVeriFinder, clearAskConversation, createCoinCheckout } from "@/services/api";
import type { AskResponse, DecisionEvidenceKind } from "@/types";

const EXAMPLES = [
  "Top 10 companies with worker sponsorship in Sheffield",
  "Show me technology companies with sponsorship",
  "Find cybersecurity qualifications",
  "Food hygiene records in Manchester",
];
const HISTORY_KEY = "verifinder-ask-conversation-v2";
const LEGACY_HISTORY_KEY = "verifinder-ask-conversation-v1";

const KIND_LABELS: Record<DecisionEvidenceKind, string> = {
  verified_fact: "Verified fact",
  calculated_finding: "Calculated",
  inference: "Inference",
  unknown: "Unknown",
};

type Exchange = { question: string; response: AskResponse };

function restoredConversation(): Exchange[] {
  try {
    const stored = window.localStorage.getItem(HISTORY_KEY) || window.sessionStorage.getItem(LEGACY_HISTORY_KEY) || "[]";
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item) => item?.question && item?.response?.interpretation && Array.isArray(item?.response?.results))
      .slice(-7);
  } catch {
    return [];
  }
}

export default function AskPage() {
  const { session, account, openAccount, refreshAccount } = useAccount();
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [purchasing, setPurchasing] = useState<CoinPack | null>(null);
  const [historyReady, setHistoryReady] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const data = exchanges.at(-1)?.response ?? null;

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setExchanges(restoredConversation());
      setHistoryReady(true);
      const params = new URLSearchParams(window.location.search);
      if (params.get("coins") === "success") {
        setNotice("Payment received. Your coins will appear as soon as Stripe confirms the payment.");
        void refreshAccount();
        window.setTimeout(() => void refreshAccount(), 1600);
        window.setTimeout(() => void refreshAccount(), 4000);
        window.history.replaceState({}, "", "/ask");
      } else if (params.get("coins") === "cancelled") {
        setNotice("Checkout was cancelled. Your conversation is still here.");
        window.history.replaceState({}, "", "/ask");
      }
    });
    return () => { active = false; };
  }, [refreshAccount]);

  useEffect(() => {
    if (historyReady) window.localStorage.setItem(HISTORY_KEY, JSON.stringify(exchanges.slice(-7)));
  }, [exchanges, historyReady]);

  async function submit(event?: FormEvent, example?: string) {
    event?.preventDefault();
    const value = (example ?? question).trim();
    if (value.length < 3) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const response = await askVeriFinder(
        value,
        exchanges.map((exchange) => exchange.response),
        controller.signal,
        data?.conversation_id,
      );
      setExchanges((current) => [...current, { question: value, response }].slice(-7));
      setQuestion("");
      void refreshAccount();
    } catch (requestError) {
      if ((requestError as Error).name !== "AbortError") {
        setError(requestError instanceof ApiError ? requestError : new ApiError((requestError as Error).message));
      }
    } finally {
      if (controllerRef.current === controller) setLoading(false);
    }
  }

  async function buyCoins(pack: CoinPack) {
    if (!session) {
      openAccount("sign-in");
      return;
    }
    setPurchasing(pack);
    setError(null);
    try {
      const checkout = await createCoinCheckout(pack);
      window.location.assign(checkout.url);
    } catch (checkoutError) {
      setError(checkoutError instanceof ApiError ? checkoutError : new ApiError((checkoutError as Error).message));
      setPurchasing(null);
    }
  }

  function clearConversation() {
    controllerRef.current?.abort();
    const conversationId = data?.conversation_id;
    setExchanges([]);
    setError(null);
    setNotice(null);
    window.localStorage.removeItem(HISTORY_KEY);
    window.sessionStorage.removeItem(LEGACY_HISTORY_KEY);
    if (conversationId) void clearAskConversation(conversationId).catch(() => undefined);
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
  const paymentRequired = error?.paymentRequired === true;

  return (
    <div className="decision-page ask-page">
      <section className="shell decision-hero">
        <div className="decision-hero-copy">
          <span className="decision-icon"><MessageSquareText size={24} /></span>
          <span className="kicker">Ask VeriFinder</span>
          <h1>Ask questions across verified public data.</h1>
          <p>Ask a first question, then continue the conversation. Follow-ups carry the previous questions, interpretation and returned records so the answer stays in context.</p>
        </div>
        <div className="decision-guardrail"><BadgeCheck size={18} /><div><strong>Evidence executes the query</strong><span>Language AI can interpret your wording. The database decides which records match.</span></div></div>
      </section>

      <section className="shell ask-workspace">
        {exchanges.length > 1 && (
          <div className="ask-thread" aria-label="Previous conversation">
            {exchanges.slice(0, -1).map((exchange, index) => (
              <article key={`${exchange.response.generated_at}-${index}`}>
                <div className="thread-question"><span>You</span><p>{exchange.question}</p></div>
                <div className="thread-answer"><span><Sparkles size={13} />VeriFinder</span><strong>{exchange.response.headline}</strong>{exchange.response.summary && <p>{exchange.response.summary}</p>}{exchange.response.results.length > 0 && <small>{exchange.response.results.slice(0, 3).map((result) => result.title).join(" · ")}{exchange.response.results.length > 3 ? ` +${exchange.response.results.length - 3} more` : ""}</small>}</div>
              </article>
            ))}
          </div>
        )}

        {!session ? (
          <SignInGate className="ask-signin-gate" feature="Ask VeriFinder" onSignIn={() => openAccount("sign-in")} />
        ) : (
        <form className="ask-composer" onSubmit={submit}>
          <div className="ask-composer-heading">
            <label htmlFor="ask-question">{exchanges.length ? "Ask a follow-up" : "What do you need to know?"}</label>
            <div>
              {session && <span className="coin-balance"><Coins size={14} />{account?.coin_balance ?? 0} coins</span>}
              {exchanges.length > 0 && <button className="clear-conversation" type="button" onClick={clearConversation}><Trash2 size={13} />New conversation</button>}
            </div>
          </div>
          <div className="ask-input-wrap">
            <Search size={20} aria-hidden="true" />
            <textarea id="ask-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={exchanges.length ? "For example: which of those also has the Skilled Worker route?" : "For example: show me licensed worker sponsors in Sheffield"} rows={2} maxLength={600} />
            <button className="button ask-submit" disabled={loading || question.trim().length < 3} type="submit">
              {loading ? <LoaderCircle size={18} className="spin" /> : <Sparkles size={17} />}
              {loading ? "Checking…" : exchanges.length ? "Follow up" : "Ask"}
            </button>
          </div>
          {!exchanges.length && <div className="example-prompts" aria-label="Example questions"><span>Try:</span>{EXAMPLES.map((example) => <button key={example} type="button" onClick={() => void submit(undefined, example)}>{example}</button>)}</div>}
          {exchanges.length > 0 && <p className="conversation-context"><MessageSquareText size={13} />The next message will use up to 6 previous answers and their returned records.</p>}
        </form>
        )}

        {notice && <div className="ask-notice" role="status"><BadgeCheck size={18} /><span>{notice}</span></div>}

        {paymentRequired && (
          <CoinPaywall
            message={error?.message}
            isSignedIn={Boolean(session)}
            coinBillingConfigured={account?.coin_billing_configured ?? false}
            purchasing={purchasing}
            onBuy={(pack) => void buyCoins(pack)}
            onSignIn={() => openAccount("sign-in")}
            onViewPlans={() => openAccount("plans")}
          />
        )}

        {error && !paymentRequired && <div className="decision-error" role="alert"><CircleAlert size={19} /><div><strong>Could not answer that question</strong><span>{error.message}</span></div></div>}

        {!data && !error && !loading && (
          <div className="ask-empty-grid">
            <article><Database size={21} /><h2>Six connected domains</h2><p>Sponsors, qualifications, study providers, food hygiene, recent property sales and postcode area checks.</p></article>
            <article><SlidersHorizontal size={21} /><h2>Visible interpretation</h2><p>You can see the intent, place, subject, industry signal and result limit used for every query.</p></article>
            <article><Lightbulb size={21} /><h2>Context-aware follow-ups</h2><p>Each follow-up includes the earlier questions and result records, while database evidence stays in control.</p></article>
          </div>
        )}

        {data && (
          <div className="ask-results-layout" aria-live="polite">
            <aside className="interpretation-panel">
              <div className="panel-heading"><SlidersHorizontal size={17} /><div><span className="kicker">Query receipt</span><h2>How this was interpreted</h2></div></div>
              <dl>{filters.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
              {interpretation?.assumptions.length ? <div className="assumption-box"><strong>Assumptions</strong>{interpretation.assumptions.map((item) => <p key={item}>{item}</p>)}</div> : null}
              <div className="ai-mode"><Sparkles size={14} /><span>{data.ai_mode === "gemini" ? "Gemini-assisted answer" : "Rule-based interpretation"}</span></div>
            </aside>

            <div className="ask-results-main">
              <div className="current-question"><span>You asked</span><p>{data.question}</p></div>
              <div className="answer-heading"><div><span className="kicker">Evidence-backed answer</span><h2>{data.headline}</h2>{data.summary && <p>{data.summary}</p>}{data.context_turns_used > 0 && <small className="context-used"><MessageSquareText size={12} />Used {data.context_turns_used} earlier answer{data.context_turns_used === 1 ? "" : "s"}, including result records</small>}</div><span>{data.total} returned</span></div>
              {data.results.length === 0 ? (
                <div className="decision-empty"><Search size={24} /><h3>{interpretation?.intent === "job_search" ? "Vacancies need a live jobs source" : "No matching records"}</h3><p>{interpretation?.intent === "job_search" ? "Use a verified alternative below, or start a new evidence-domain question." : "Try a full postcode, a broader location, or a more specific public-data subject."}</p>{(data.suggested_questions ?? []).length > 0 && <div className="ask-suggestions" aria-label="Verified alternatives">{data.suggested_questions.map((suggestion) => <button type="button" key={suggestion} disabled={loading} onClick={() => void submit(undefined, suggestion)}>{suggestion}<ArrowRight size={13} /></button>)}</div>}</div>
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
