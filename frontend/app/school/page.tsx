"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, CircleAlert, LoaderCircle, MapPin, School, SearchX } from "lucide-react";
import { DatasetSearchForm } from "@/components/DatasetSearchForm";
import { searchSchools } from "@/services/api";
import type { SchoolSearchResponse } from "@/types";

function SchoolResults() {
  const query = useSearchParams().get("q")?.trim() || "";
  const [data, setData] = useState<SchoolSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    if (query.length < 2) return;
    const controller = new AbortController();
    searchSchools(query, controller.signal).then(setData).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [query]);

  const current = data?.query === query ? data : null;
  return (
    <div className="shell search-page engine-search-page school-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading"><div><span className="kicker">School Check</span><h1>{query ? <>Schools matching “{query}”</> : "Check a school or college"}</h1><p>Search the Department for Education's GIAS register, then see the latest Ofsted inspection outcome for the same URN.</p></div><div className="search-page-box"><DatasetSearchForm action="/school" initialValue={query} label="Search schools" placeholder="School name, URN or postcode…" /></div></div>
      <div className="engine-scope-note school-scope-note"><School size={18} /><p><strong>Two separate official registers:</strong> establishment details come from GIAS; inspection outcomes come from Ofsted's own management information and are matched by exact URN, not merged.</p></div>
      {!query || query.length < 2 ? <div className="empty-state"><SearchX size={28} /><h2>Enter a school name, URN or postcode</h2><p>URN is the Department for Education's unique reference number for the establishment.</p></div> : error ? <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>School Check is unavailable</h2><p>{error}</p></div> : !current ? <div className="loading-state"><LoaderCircle size={22} /> Searching the GIAS register…</div> : current.results.length === 0 ? <div className="empty-state"><SearchX size={28} /><h2>No matching establishment found</h2><p>Try the exact URN, or a shorter part of the school name.</p></div> : <section className="result-group"><div className="result-group-heading"><div><span className="result-group-icon school-group-icon"><School size={18} /></span><div><h2>GIAS establishment register</h2><p>Department for Education · {current.dataset_version}</p></div></div><span>{current.total} found</span></div><div className="result-list">{current.results.map((result) => <Link href={`/school/${result.urn}`} className="result-card school-result-card" key={result.urn}><span className="result-icon school-result-icon"><School size={22} /></span><div className="result-title"><h2>{result.establishment_name}</h2><p>{result.type_name || "Establishment"} · {result.phase_name || "Phase unavailable"} · {result.status_name || "Status unavailable"}</p></div><div className="result-meta"><span><MapPin size={14} /> {result.postcode || result.town || "Location unavailable"}</span><span>URN {result.urn}</span></div><span className="result-open">View school <ArrowRight size={16} /></span></Link>)}</div></section>}
    </div>
  );
}

export default function SchoolPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading School Check…</div>}><SchoolResults /></Suspense>;
}
