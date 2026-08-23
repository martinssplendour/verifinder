"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowUpRight, BarChart3, CircleAlert, Landmark, LoaderCircle, MapPin, SearchX, ShieldAlert, Waves } from "lucide-react";
import { DatasetSearchForm } from "@/components/DatasetSearchForm";
import { NoRecordsFound } from "@/components/NoRecordsFound";
import { WatchButton } from "@/components/WatchButton";
import { ApiError, checkArea } from "@/services/api";
import type { AreaCheckResponse } from "@/types";

type AreaError = { message: string; suggestions: string[] };

function monthLabel(value: string | null) {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat("en-GB", { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}-01T00:00:00Z`));
}

function label(value: string) {
  return value.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function AreaResults() {
  const query = useSearchParams().get("q")?.trim() || "";
  const [data, setData] = useState<AreaCheckResponse | null>(null);
  const [error, setError] = useState<AreaError | null>(null);

  useEffect(() => {
    queueMicrotask(() => setError(null));
    if (query.length < 5) return;
    const controller = new AbortController();
    checkArea(query, controller.signal).then(setData).catch((requestError) => {
      if (requestError.name === "AbortError") return;
      setError({
        message: requestError.message,
        suggestions: requestError instanceof ApiError ? requestError.suggestions : [],
      });
    });
    return () => controller.abort();
  }, [query]);

  const current = data?.postcode.postcode.replaceAll(" ", "").toLowerCase() === query.replaceAll(" ", "").toLowerCase() ? data : null;
  const maxCrime = Math.max(...(current?.crime.months.map((month) => month.count) || [1]), 1);
  return (
    <div className="shell search-page engine-search-page area-check-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading">
        <div><span className="kicker">Area Check</span><h1>{current ? current.postcode.postcode : "Understand a postcode"}</h1><p>Check recent street-level crime, active flood warnings and selected planning designations.</p>{current && <div className="area-watch-action"><WatchButton entityType="area" entityId={current.postcode.postcode} label={`Area ${current.postcode.postcode}`} /></div>}</div>
        <div className="search-page-box"><DatasetSearchForm action="/areas" initialValue={query} label="Check a postcode" placeholder="Enter a full postcode, e.g. N1C 4AB" /></div>
      </div>
      <div className="engine-scope-note area-scope-note"><MapPin size={18} /><p><strong>Postcode-level context:</strong> this combines a downloaded Ordnance Survey postcode point with current official APIs. It is not an address-level risk assessment.</p></div>

      {!query || query.length < 5 ? (
        <div className="empty-state"><SearchX size={28} /><h2>Enter a full postcode</h2><p>Area Check needs a complete Great Britain postcode to anchor the official data lookups.</p></div>
      ) : error && error.suggestions.length > 0 ? (
        <NoRecordsFound
          query={query}
          hint={error.message}
          suggestionsLabel="Nearby postcodes on the register"
          suggestionsNote="Real postcodes in the same outward area. Pick the one you meant to check."
          suggestionsClassName="suggestion-chips"
        >
          {error.suggestions.map((postcode) => (
            <Link className="suggestion-chip" href={`/areas?q=${encodeURIComponent(postcode)}`} key={postcode}>
              <MapPin size={14} /> {postcode}
            </Link>
          ))}
        </NoRecordsFound>
      ) : error ? (
        <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>We could not check that area</h2><p>{error.message}</p></div>
      ) : !current ? (
        <div className="loading-state"><LoaderCircle size={22} /> Checking official area sources…</div>
      ) : (
        <>
          <section className="summary-grid area-summary-grid" aria-label="Area summary">
            <article className="summary-card"><span className="summary-label"><ShieldAlert size={16} /> Street-level crime</span><strong>{current.crime.latest_total ?? "—"}</strong><small>{current.crime.status === "live" ? `${monthLabel(current.crime.latest_month)} · approximately one mile` : "Source temporarily unavailable"}</small></article>
            <article className="summary-card"><span className="summary-label"><Landmark size={16} /> Planning matches</span><strong>{current.planning.total ?? "—"}</strong><small>Across six selected designation datasets</small></article>
            <article className="summary-card"><span className="summary-label"><Waves size={16} /> Active flood warnings</span><strong>{current.flood.total ?? "—"}</strong><small>Within {current.flood.radius_km} km · England only</small></article>
            <article className="summary-card"><span className="summary-label"><MapPin size={16} /> Location point</span><strong className="long-value">{current.postcode.latitude.toFixed(4)}, {current.postcode.longitude.toFixed(4)}</strong><small>OS Code-Point Open · {current.postcode.source.version}</small></article>
          </section>

          <div className="area-detail-grid">
            <article className="detail-panel area-crime-panel"><div className="panel-title"><div><span className="kicker">Three-month view</span><h2>Nearby street-level incidents</h2></div><BarChart3 size={21} /></div>{current.crime.status === "unavailable" ? <p className="panel-helper">{current.crime.message}</p> : <><div className="crime-trend">{[...current.crime.months].reverse().map((month) => <div key={month.month}><span>{monthLabel(month.month)}</span><div><i style={{ width: `${Math.max((month.count / maxCrime) * 100, 3)}%` }} /></div><strong>{month.count}</strong></div>)}</div><div className="category-counts">{current.crime.categories.map((category) => <div key={category.category}><span>{category.category}</span><strong>{category.count}</strong></div>)}</div></>}<a className="secondary-cta" href={current.crime.source_url} target="_blank" rel="noreferrer">Police.uk methodology <ArrowUpRight size={15} /></a></article>

            <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Planning context</span><h2>Selected designations</h2></div><Landmark size={21} /></div>{current.planning.status === "unavailable" ? <p className="panel-helper">{current.planning.message}</p> : current.planning.constraints.length ? <div className="constraint-list">{current.planning.constraints.map((item, index) => <div key={`${item.dataset}-${item.reference || index}`}><span>{label(item.dataset)}</span><strong>{item.name}</strong>{item.reference && <small>Ref {item.reference}</small>}</div>)}</div> : <div className="inline-empty"><strong>No matches returned</strong><p>No designation was found in the six selected datasets. This does not rule out other planning constraints.</p></div>}<a className="secondary-cta" href={current.planning.source_url} target="_blank" rel="noreferrer">View Planning Data <ArrowUpRight size={15} /></a></article>

            <article className="detail-panel area-flood-panel"><div className="panel-title"><div><span className="kicker">Current conditions</span><h2>Flood warnings</h2></div><Waves size={21} /></div>{current.flood.status === "unavailable" ? <p className="panel-helper">{current.flood.message}</p> : current.flood.warnings.length ? <div className="warning-list">{current.flood.warnings.map((warning, index) => <div key={`${warning.description}-${index}`}><span>Level {warning.severity_level}</span><strong>{warning.severity}</strong><p>{warning.description}</p></div>)}</div> : <div className="inline-empty good-empty"><strong>No active warning returned</strong><p>The Environment Agency API reported no current warning within 10 km at check time.</p></div>}<a className="secondary-cta" href={current.flood.source_url} target="_blank" rel="noreferrer">Environment Agency source <ArrowUpRight size={15} /></a></article>
          </div>
          <div className="limitations-note"><CircleAlert size={18} /><div><strong>Read this result carefully</strong><ul>{current.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
        </>
      )}
    </div>
  );
}

export default function AreaPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Area Check…</div>}><AreaResults /></Suspense>;
}
