"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowRight, Building2, CircleAlert, LoaderCircle, MapPin, SearchX, ShieldCheck } from "lucide-react";
import { SourceAvailabilityNotice } from "@/components/SourceAvailabilityNotice";
import { SearchBox } from "@/components/SearchBox";
import { searchCompanies, searchSponsors } from "@/services/api";
import type { SearchResponse, SponsorSearchResponse } from "@/types";

function SearchResults() {
  const params = useSearchParams();
  const query = params.get("q")?.trim() || "";
  const [companies, setCompanies] = useState<SearchResponse | null>(null);
  const [sponsors, setSponsors] = useState<SponsorSearchResponse | null>(null);
  const [error, setError] = useState<{ query: string; message: string } | null>(null);

  useEffect(() => {
    if (query.length < 2) return;
    const controller = new AbortController();
    Promise.allSettled([
      searchCompanies(query, controller.signal),
      searchSponsors(query, controller.signal),
    ]).then(([companyResult, sponsorResult]) => {
      if (controller.signal.aborted) return;
      if (companyResult.status === "fulfilled") setCompanies(companyResult.value);
      if (sponsorResult.status === "fulfilled") setSponsors(sponsorResult.value);
      if (companyResult.status === "rejected" && sponsorResult.status === "rejected") {
        setError({ query, message: "Company Check could not reach either verified source." });
      } else {
        setError(null);
      }
    });
    return () => controller.abort();
  }, [query]);

  const companyData = companies?.query === query ? companies : null;
  const sponsorData = sponsors?.query === query ? sponsors : null;
  const loaded = Boolean(companyData || sponsorData);
  const total = (companyData?.total || 0) + (sponsorData?.total || 0);
  const sponsorLive = sponsorData?.results.some((result) => result.source.health === "healthy") || false;

  return (
    <div className="shell search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading">
        <div>
          <span className="kicker">Company Check</span>
          <h1>{query ? <>Results for “{query}”</> : "Search UK companies"}</h1>
          <p>Compare legal-company records and Home Office sponsor entries. Each result is labelled by source.</p>
        </div>
        <div className="search-page-box"><SearchBox initialValue={query} /></div>
      </div>

      {!query || query.length < 2 ? (
        <div className="empty-state"><SearchX size={28} /><h2>Enter at least two characters</h2><p>Search by company name or Companies House number.</p></div>
      ) : error?.query === query ? (
        <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>We couldn’t reach the verified sources</h2><p>{error.message}</p></div>
      ) : !loaded ? (
        <div className="loading-state"><LoaderCircle size={22} /> Searching Companies House and the sponsor register…</div>
      ) : (
        <>
          {companyData?.data_mode === "unavailable" && <SourceAvailabilityNotice compact sponsorLive={sponsorLive} />}
          <div className="result-summary"><strong>{total}</strong> matching source {total === 1 ? "record" : "records"}</div>

          {(companyData?.results.length || 0) > 0 && (
            <section className="result-group" aria-labelledby="company-result-heading">
              <div className="result-group-heading">
                <div><span className="result-group-icon"><Building2 size={18} /></span><div><h2 id="company-result-heading">Companies House</h2><p>Legal company records</p></div></div>
                <span>{companyData?.results.length} found</span>
              </div>
              <div className="result-list">
                {companyData?.results.map((result) => (
                  <Link href={`/company/${result.company_number}`} className="result-card" key={result.company_number}>
                    <span className="result-icon"><Building2 size={23} /></span>
                    <div className="result-title"><h2>{result.company_name}</h2><p>Company number {result.company_number}</p></div>
                    <div className="result-meta">
                      <span className={`dot-status ${result.status === "active" ? "is-active" : ""}`}>{result.status || "Status unavailable"}</span>
                      <span><MapPin size={14} /> {result.location || "Location unavailable"}</span>
                    </div>
                    <span className="result-open">View company <ArrowRight size={16} /></span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {(sponsorData?.results.length || 0) > 0 && (
            <section className="result-group sponsor-result-group" aria-labelledby="sponsor-result-heading">
              <div className="result-group-heading">
                <div><span className="result-group-icon sponsor-group-icon"><ShieldCheck size={18} /></span><div><h2 id="sponsor-result-heading">UK sponsor register</h2><p>Home Office organisation records · {sponsorData?.dataset_version}</p></div></div>
                <span>{sponsorData?.results.length} found</span>
              </div>
              <div className="result-list">
                {sponsorData?.results.map((result) => (
                  <Link href={`/sponsor/${result.id}`} className="result-card sponsor-result-card" key={result.id}>
                    <span className="result-icon sponsor-result-icon"><ShieldCheck size={23} /></span>
                    <div className="result-title"><h2>{result.organisation_name}</h2><p>Official sponsor-register record</p></div>
                    <div className="result-meta">
                      <span className="dot-status is-active">Licensed sponsor · {result.rating || "Rating unavailable"}</span>
                      <span><MapPin size={14} /> {[result.town_city, result.county].filter(Boolean).join(", ") || "Location unavailable"}</span>
                    </div>
                    <span className="result-open">View sponsorship <ArrowRight size={16} /></span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {total === 0 && (
            <div className="empty-state"><SearchX size={28} /><h2>No matching verified record found</h2><p>Try the registered name, check the spelling, or enter an eight-character company number.</p></div>
          )}
        </>
      )}
    </div>
  );
}

export default function SearchPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading search…</div>}><SearchResults /></Suspense>;
}
