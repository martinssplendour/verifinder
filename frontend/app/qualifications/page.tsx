"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, Award, BadgeCheck, BookOpenCheck, CircleAlert, LoaderCircle, SearchX } from "lucide-react";
import { DatasetSearchForm } from "@/components/DatasetSearchForm";
import { NoExactMatch } from "@/components/NoExactMatch";
import { searchQualifications } from "@/services/api";
import type { QualificationSearchResponse, QualificationSearchResult } from "@/types";

function QualificationCard({ result }: { result: QualificationSearchResult }) {
  const available = result.status?.toLowerCase().includes("available") && !result.status.toLowerCase().includes("no longer");
  const tone = result.record_type === "qiw" ? "qiw-icon" : "";
  return (
    <Link href={`/qualification/${result.id}`} className="result-card qualification-result-card">
      <span className={`result-icon qualification-result-icon ${tone}`}><Award size={23} /></span>
      <div className="result-title"><h2>{result.title}</h2><p>{result.qualification_number} · {result.awarding_organisation_name}</p></div>
      <div className="result-meta">
        <span className={`dot-status ${available ? "is-active" : ""}`}><BadgeCheck size={13} /> {result.status || "Status unavailable"}</span>
        <span>{[result.level, result.jurisdiction].filter(Boolean).join(" · ")}</span>
      </div>
      <span className="result-open">View qualification <ArrowRight size={16} /></span>
    </Link>
  );
}

function QualificationGroup({ heading, description, results, tone }: {
  heading: string;
  description: string;
  results: QualificationSearchResult[];
  tone: "ofqual" | "qiw";
}) {
  if (results.length === 0) return null;
  return (
    <section className="result-group" aria-label={heading}>
      <div className="result-group-heading">
        <div><span className={`result-group-icon qualification-group-icon ${tone === "qiw" ? "qiw-icon" : ""}`}><Award size={18} /></span><div><h2>{heading}</h2><p>{description}</p></div></div>
        <span>{results.length} found</span>
      </div>
      <div className="result-list">
        {results.map((result) => <QualificationCard result={result} key={`${result.record_type}-${result.id}`} />)}
      </div>
    </section>
  );
}

function QualificationResults() {
  const params = useSearchParams();
  const query = params.get("q")?.trim() || "";
  const [data, setData] = useState<QualificationSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query.length < 2) return;
    const controller = new AbortController();
    queueMicrotask(() => setError(null));
    searchQualifications(query, controller.signal).then(setData).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [query]);

  const current = data?.query === query ? data : null;
  const ofqual = current?.results.filter((item) => item.record_type === "ofqual") || [];
  const qiw = current?.results.filter((item) => item.record_type === "qiw") || [];
  return (
    <div className="shell search-page engine-search-page qualification-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading">
        <div><span className="kicker">Qualification Check</span><h1>{query ? <>Results for “{query}”</> : "Check a regulated qualification"}</h1><p>Search qualification titles, official numbers and awarding organisations across connected national registers.</p></div>
        <div className="search-page-box"><DatasetSearchForm action="/qualifications" initialValue={query} label="Search regulated qualifications" placeholder="Qualification title, number or awarding body..." /></div>
      </div>

      <div className="engine-scope-note qualification-scope-note"><BookOpenCheck size={18} /><p><strong>Scope:</strong> Ofqual and CCEA Regulation records for England and Northern Ireland, plus Qualifications Wales records for Wales. Scotland is not included because its official downloadable listing is currently unavailable. Regulation is not degree equivalence or acceptance for a particular job or visa.</p></div>

      {!query || query.length < 2 ? (
        <div className="empty-state"><SearchX size={28} /><h2>Enter at least two characters</h2><p>Use the exact title, awarding organisation or qualification number for the strongest match.</p></div>
      ) : error ? (
        <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>Qualification Check is unavailable</h2><p>{error}</p></div>
      ) : !current ? (
        <div className="loading-state"><LoaderCircle size={22} /> Searching connected qualification registers…</div>
      ) : current.results.length === 0 ? (
        <NoExactMatch query={query} hint="Check the title or number. No match does not, by itself, prove that a qualification is invalid.">
          {current.suggestions.map((result) => <QualificationCard result={result} key={`${result.record_type}-${result.id}`} />)}
        </NoExactMatch>
      ) : (
        <>
          <QualificationGroup heading="Ofqual / CCEA Regulation" description="England and Northern Ireland regulated qualification records" results={ofqual} tone="ofqual" />
          <QualificationGroup heading="Qualifications Wales" description="Qualifications in Wales (QiW) register" results={qiw} tone="qiw" />
        </>
      )}
    </div>
  );
}

export default function QualificationsPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Qualification Check…</div>}><QualificationResults /></Suspense>;
}
