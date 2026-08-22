"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, CalendarDays, CircleAlert, LoaderCircle, MapPin, SearchX, ShieldCheck, Utensils } from "lucide-react";
import { DatasetSearchForm } from "@/components/DatasetSearchForm";
import { searchFood } from "@/services/api";
import type { FoodSearchResponse } from "@/types";

function ratingClass(value: string | null) {
  if (value === "5" || value?.toLowerCase().startsWith("pass")) return "rating-good";
  if (value === "0" || value === "1" || value?.toLowerCase().includes("improvement")) return "rating-poor";
  return "rating-neutral";
}

function readableDate(value: string | null) {
  if (!value) return "Date unavailable";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function FoodResults() {
  const params = useSearchParams();
  const query = params.get("q")?.trim() || "";
  const [data, setData] = useState<FoodSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query.length < 2) return;
    const controller = new AbortController();
    searchFood(query, controller.signal).then(setData).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [query]);

  const current = data?.query === query ? data : null;
  return (
    <div className="shell search-page engine-search-page food-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading">
        <div><span className="kicker">Food Check</span><h1>{query ? <>Results for “{query}”</> : "Check a food hygiene rating"}</h1><p>Search restaurants, takeaways, cafés and other food businesses by name or postcode.</p></div>
        <div className="search-page-box"><DatasetSearchForm action="/food" initialValue={query} label="Search food hygiene ratings" placeholder="Business name or postcode..." /></div>
      </div>

      <div className="engine-scope-note food-scope-note"><Utensils size={18} /><p><strong>Official inspection data:</strong> numeric FHRS ratings are used in England, Wales and Northern Ireland; Scotland uses FHIS outcomes such as Pass.</p></div>

      {!query || query.length < 2 ? (
        <div className="empty-state"><SearchX size={28} /><h2>Enter at least two characters</h2><p>Use a business name or full postcode to distinguish establishments with similar names.</p></div>
      ) : error ? (
        <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>Food Check is unavailable</h2><p>{error}</p></div>
      ) : !current ? (
        <div className="loading-state"><LoaderCircle size={22} /> Searching Food Standards Agency records…</div>
      ) : current.results.length === 0 ? (
        <div className="empty-state"><SearchX size={28} /><h2>No matching food establishment found</h2><p>Try the trading name, postcode or a shorter spelling. Some private-address businesses omit location details.</p></div>
      ) : (
        <section className="result-group" aria-labelledby="food-results-heading">
          <div className="result-group-heading"><div><span className="result-group-icon food-group-icon"><Utensils size={18} /></span><div><h2 id="food-results-heading">Food hygiene register</h2><p>Food Standards Agency records · {current.dataset_version}</p></div></div><span>{current.total} found</span></div>
          <div className="result-list">
            {current.results.map((result) => (
              <Link href={`/food/${result.id}`} className="result-card food-result-card" key={result.id}>
                <span className={`food-rating-badge ${ratingClass(result.rating_value)}`}>{result.rating_value || "—"}</span>
                <div className="result-title"><h2>{result.business_name}</h2><p>{result.business_type || "Food business"} · FHRS ID {result.fhrs_id}</p></div>
                <div className="result-meta"><span><MapPin size={14} /> {[result.address, result.postcode].filter(Boolean).join(", ") || "Location unavailable"}</span><span><CalendarDays size={14} /> Rated {readableDate(result.rating_date)}</span>{result.new_rating_pending && <span className="pending-rating"><ShieldCheck size={13} /> New rating pending</span>}</div>
                <span className="result-open">View rating <ArrowRight size={16} /></span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default function FoodPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Food Check…</div>}><FoodResults /></Suspense>;
}
