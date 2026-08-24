"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowRight,
  BadgeCheck,
  Building2,
  CircleAlert,
  GraduationCap,
  Landmark,
  LoaderCircle,
  SearchX,
} from "lucide-react";
import { DatasetSearchForm } from "@/components/DatasetSearchForm";
import { NoExactMatch } from "@/components/NoExactMatch";
import { searchStudyProviders } from "@/services/api";
import type { StudyProviderSearchResponse, StudyProviderSearchResult } from "@/types";

function StudyCard({ result }: { result: StudyProviderSearchResult }) {
  const isStudentSponsor = result.record_type === "student_sponsor";
  const Icon = isStudentSponsor ? GraduationCap : Landmark;
  const iconClass = isStudentSponsor ? "study-sponsor-icon" : "study-ofs-icon";
  return (
    <Link href={`/study/${result.record_type}/${result.id}`} className="result-card study-result-card">
      <span className={`result-icon ${iconClass}`}><Icon size={23} /></span>
      <div className="result-title">
        <h2>{result.name}</h2>
        <p>{result.ukprn ? `UKPRN ${result.ukprn}` : result.routes.join(" · ") || result.provider_type || "Official register record"}</p>
      </div>
      <div className="result-meta">
        <span className="dot-status is-active"><BadgeCheck size={13} /> {result.status || "Listed"}</span>
        <span>{[result.provider_type, result.town_city].filter(Boolean).join(" · ") || "Location not stated"}</span>
      </div>
      <span className="result-open">View record <ArrowRight size={16} /></span>
    </Link>
  );
}

function ResultGroup({
  heading,
  description,
  results,
  kind,
}: {
  heading: string;
  description: string;
  results: StudyProviderSearchResult[];
  kind: "student_sponsor" | "ofs";
}) {
  if (results.length === 0) return null;
  const Icon = kind === "student_sponsor" ? GraduationCap : Landmark;
  return (
    <section className="result-group" aria-label={heading}>
      <div className="result-group-heading">
        <div>
          <span className={`result-group-icon ${kind === "student_sponsor" ? "study-sponsor-icon" : "study-ofs-icon"}`}><Icon size={18} /></span>
          <div><h2>{heading}</h2><p>{description}</p></div>
        </div>
        <span>{results.length} found</span>
      </div>
      <div className="result-list">
        {results.map((result) => <StudyCard result={result} key={`${result.record_type}-${result.id}`} />)}
      </div>
    </section>
  );
}

function StudyResults() {
  const params = useSearchParams();
  const query = params.get("q")?.trim() || "";
  const [data, setData] = useState<StudyProviderSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query.length < 2) return;
    const controller = new AbortController();
    queueMicrotask(() => setError(null));
    searchStudyProviders(query, controller.signal).then(setData).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [query]);

  const current = data?.query === query ? data : null;
  const studentResults = current?.results.filter((item) => item.record_type === "student_sponsor") || [];
  const ofsResults = current?.results.filter((item) => item.record_type === "ofs") || [];

  return (
    <div className="shell search-page engine-search-page study-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading">
        <div>
          <span className="kicker">Study Provider Check</span>
          <h1>{query ? <>Results for “{query}”</> : "Check a study provider"}</h1>
          <p>Search licensed student sponsors and registered English higher-education providers by official name or UKPRN.</p>
        </div>
        <div className="search-page-box">
          <DatasetSearchForm
            action="/study"
            initialValue={query}
            label="Search study providers"
            placeholder="Provider name or UKPRN..."
          />
        </div>
      </div>

      <div className="engine-scope-note study-scope-note">
        <Building2 size={18} />
        <p><strong>Two separate checks:</strong> UKVI confirms permission to sponsor international students. OfS registration covers higher-education providers in England. Neither result alone proves course quality, accreditation or visa eligibility.</p>
      </div>

      {!query || query.length < 2 ? (
        <div className="empty-state"><SearchX size={28} /><h2>Enter at least two characters</h2><p>Use the provider’s full official name or its eight-digit UKPRN for the strongest match.</p></div>
      ) : error ? (
        <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>Study Provider Check is unavailable</h2><p>{error}</p></div>
      ) : !current ? (
        <div className="loading-state"><LoaderCircle size={22} /> Searching both official registers…</div>
      ) : current.results.length === 0 ? (
        <NoExactMatch query={query} hint="Try the exact legal or trading name. No match is not proof that a provider is illegitimate.">
          {current.suggestions.map((result) => <StudyCard result={result} key={`${result.record_type}-${result.id}`} />)}
        </NoExactMatch>
      ) : (
        <>
          <ResultGroup heading="Student sponsor register" description="UK Visas and Immigration · licensed student sponsors" results={studentResults} kind="student_sponsor" />
          <ResultGroup heading="Office for Students Register" description="Registered higher-education providers in England" results={ofsResults} kind="ofs" />
        </>
      )}
    </div>
  );
}

export default function StudyPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Study Provider Check…</div>}><StudyResults /></Suspense>;
}
