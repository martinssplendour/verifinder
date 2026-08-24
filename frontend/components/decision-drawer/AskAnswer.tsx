"use client";

import Link from "next/link";
import { ArrowRight, BadgeCheck, CircleAlert, Database } from "lucide-react";
import type { AskResponse } from "@/types";

export function AskAnswer({ answer, close, ask }: { answer: AskResponse; close: () => void; ask: (question: string) => void }) {
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
      {(answer.suggested_questions ?? []).length > 0 && (
        <div className="drawer-suggestions">
          <span>Try instead</span>
          {answer.suggested_questions.map((suggestion) => (
            <button type="button" key={suggestion} onClick={() => ask(suggestion)}>{suggestion}<ArrowRight size={12} /></button>
          ))}
        </div>
      )}
      <div className="drawer-boundary"><strong>Boundary</strong>{answer.limitations.map((item) => <p key={item}>{item}</p>)}</div>
    </div>
  );
}
