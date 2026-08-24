"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, CalendarDays, CircleAlert, Home, LoaderCircle, MapPin, PoundSterling, SearchX } from "lucide-react";
import { DatasetSearchForm } from "@/components/DatasetSearchForm";
import { NoExactMatch } from "@/components/NoExactMatch";
import { searchProperties } from "@/services/api";
import type { PropertySearchResponse, PropertySearchResult } from "@/types";

const money = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 });
const propertyTypes: Record<string, string> = { D: "Detached", S: "Semi-detached", T: "Terraced", F: "Flat / maisonette", O: "Other" };

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function PropertyCard({ result }: { result: PropertySearchResult }) {
  return (
    <Link href={`/property/${result.property_key}`} className="result-card property-result-card">
      <span className="result-icon property-result-icon"><Home size={22} /></span>
      <div className="result-title">
        <h2>{result.address}</h2>
        <p>{propertyTypes[result.property_type || ""] || "Property"} · {result.transaction_count} recorded sale{result.transaction_count === 1 ? "" : "s"} in snapshot</p>
      </div>
      <div className="result-meta">
        <span><PoundSterling size={14} /> {money.format(result.latest_price)}</span>
        <span><CalendarDays size={14} /> {dateLabel(result.latest_transfer_date)}</span>
        <span><MapPin size={14} /> {result.postcode || "Postcode unavailable"}</span>
      </div>
      <span className="result-open">View property <ArrowRight size={16} /></span>
    </Link>
  );
}

function PropertyResults() {
  const query = useSearchParams().get("q")?.trim() || "";
  const [data, setData] = useState<PropertySearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    queueMicrotask(() => setError(null));
    if (query.length < 2) return;
    const controller = new AbortController();
    searchProperties(query, controller.signal).then(setData).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [query]);

  const current = data?.query === query ? data : null;
  return (
    <div className="shell search-page engine-search-page property-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading"><div><span className="kicker">Property Check</span><h1>{query ? <>Recorded sales matching “{query}”</> : "Check a property sale"}</h1><p>Find recorded 2025–2026 sale prices, then inspect postcode-level planning context.</p></div><div className="search-page-box"><DatasetSearchForm action="/property" initialValue={query} label="Search property records" placeholder="Full postcode or address start…" /></div></div>
      <div className="engine-scope-note property-scope-note"><PoundSterling size={18} /><p><strong>Recent public sale records:</strong> the local snapshot covers HM Land Registry Price Paid transactions from 2025 and 2026 in England and Wales—not a valuation or complete ownership history.</p></div>

      {!query || query.length < 2 ? (
        <div className="empty-state"><SearchX size={28} /><h2>Enter a full postcode or address</h2><p>For an address, start with the flat or house number. For the broadest match, use the full postcode.</p></div>
      ) : error ? (
        <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>Property Check is unavailable</h2><p>{error}</p></div>
      ) : !current ? (
        <div className="loading-state"><LoaderCircle size={22} /> Searching recorded sales…</div>
      ) : current.results.length === 0 ? (
        <NoExactMatch
          query={query}
          hint="A no-match does not mean the property has never sold — the snapshot only covers 2025–2026 sales in England and Wales."
          label="Other recorded sales nearby"
          note="Sales recorded in the same postcode area — none is the exact address or postcode you searched."
        >
          {current.suggestions.map((result) => <PropertyCard result={result} key={result.property_key} />)}
        </NoExactMatch>
      ) : (
        <section className="result-group">
          <div className="result-group-heading"><div><span className="result-group-icon property-group-icon"><Home size={18} /></span><div><h2>HM Land Registry Price Paid Data</h2><p>Imported 2025–2026 snapshot · {current.dataset_version}</p></div></div><span>{current.total} found</span></div>
          <div className="result-list">{current.results.map((result) => <PropertyCard result={result} key={result.property_key} />)}</div>
        </section>
      )}
    </div>
  );
}

export default function PropertyPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Property Check…</div>}><PropertyResults /></Suspense>;
}
