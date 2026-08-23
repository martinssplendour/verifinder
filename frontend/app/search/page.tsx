"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowRight,
  Building2,
  CircleAlert,
  Database,
  LoaderCircle,
  MapPin,
  SearchX,
  ShieldCheck,
} from "lucide-react";
import { DatasetSearchForm } from "@/components/DatasetSearchForm";
import { searchCompanies, searchSponsors } from "@/services/api";
import type { SearchResponse, SponsorSearchResponse } from "@/types";

function SearchResults() {
  const params = useSearchParams();
  const legacyQuery = params.get("q")?.trim() || "";
  const companyQuery = params.get("company")?.trim() || legacyQuery;
  const sponsorQuery = params.get("sponsor")?.trim() || legacyQuery;
  const [companies, setCompanies] = useState<SearchResponse | null>(null);
  const [sponsors, setSponsors] = useState<SponsorSearchResponse | null>(null);
  const [companyError, setCompanyError] = useState<{ query: string; message: string } | null>(null);
  const [sponsorError, setSponsorError] = useState<{ query: string; message: string } | null>(null);

  useEffect(() => {
    if (companyQuery.length < 2) return;
    const controller = new AbortController();
    searchCompanies(companyQuery, controller.signal).then((response) => {
      setCompanies(response);
      setCompanyError(null);
    }).catch((requestError) => {
      if (requestError.name !== "AbortError") setCompanyError({ query: companyQuery, message: requestError.message });
    });
    return () => controller.abort();
  }, [companyQuery]);

  useEffect(() => {
    if (sponsorQuery.length < 2) return;
    const controller = new AbortController();
    searchSponsors(sponsorQuery, controller.signal).then((response) => {
      setSponsors(response);
      setSponsorError(null);
    }).catch((requestError) => {
      if (requestError.name !== "AbortError") setSponsorError({ query: sponsorQuery, message: requestError.message });
    });
    return () => controller.abort();
  }, [sponsorQuery]);

  const companyData = companies?.query === companyQuery ? companies : null;
  const sponsorData = sponsors?.query === sponsorQuery ? sponsors : null;
  const currentCompanyError = companyError?.query === companyQuery ? companyError : null;
  const currentSponsorError = sponsorError?.query === sponsorQuery ? sponsorError : null;
  const retainedCompanyParams: Record<string, string> = sponsorQuery.length >= 2 ? { sponsor: sponsorQuery } : {};
  const retainedSponsorParams: Record<string, string> = companyQuery.length >= 2 ? { company: companyQuery } : {};

  return (
    <div className="shell search-page independent-check-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <header className="independent-check-heading">
        <span className="kicker">Company and sponsorship checks</span>
        <h1>Check each source separately</h1>
        <p>Companies House and the Home Office sponsor register are independent data sources. VeriFinder does not merge their records or infer that similar names are the same organisation.</p>
      </header>

      <div className="engine-scope-note independent-scope-note">
        <CircleAlert size={18} />
        <p><strong>Exact lookup only:</strong> results must have the same name as the query, ignoring letter case. No fuzzy, partial-name or cross-source matching is used.</p>
      </div>

      <section className="independent-search-grid" aria-label="Separate source checks">
        <article className="source-check-card" id="company-check">
          <div className="source-check-heading">
            <span className="result-group-icon"><Building2 size={19} /></span>
            <div><span>Companies House API</span><h2>Company check</h2></div>
            <small>Independent</small>
          </div>
          <p>Retrieve a legal company record by its exact registered name or company number.</p>
          <DatasetSearchForm
            key={`company-${companyQuery}`}
            action="/search"
            initialValue={companyQuery}
            label="Check Companies House"
            placeholder="Exact company name or number..."
            queryParam="company"
            retainedParams={retainedCompanyParams}
          />
          <small className="source-check-boundary"><Database size={13} /> Companies House data only; sponsorship is not added to this result.</small>
        </article>

        <article className="source-check-card sponsor-check-card" id="sponsorship-check">
          <div className="source-check-heading">
            <span className="result-group-icon sponsor-group-icon"><ShieldCheck size={19} /></span>
            <div><span>Stored Home Office list</span><h2>Sponsorship check</h2></div>
            <small>Independent</small>
          </div>
          <p>Check whether that exact organisation name appears in the latest stored worker sponsor list.</p>
          <DatasetSearchForm
            key={`sponsor-${sponsorQuery}`}
            action="/search"
            initialValue={sponsorQuery}
            label="Check the worker sponsor list"
            placeholder="Exact sponsor organisation name..."
            queryParam="sponsor"
            retainedParams={retainedSponsorParams}
          />
          <small className="source-check-boundary"><Database size={13} /> Stored sponsor data only; no Companies House entity is inferred.</small>
        </article>
      </section>

      <section className="independent-result-section" aria-labelledby="company-result-heading">
        <div className="independent-result-title">
          <div><span className="result-group-icon"><Building2 size={18} /></span><div><h2 id="company-result-heading">Company check result</h2><p>{companyQuery ? `Exact query: “${companyQuery}”` : "No query submitted"}</p></div></div>
          <span>Companies House</span>
        </div>
        {companyQuery.length < 2 ? (
          <div className="check-result-state"><SearchX size={22} /><div><strong>Enter a company name or number</strong><p>This check does not use the sponsorship query unless you enter the same value yourself.</p></div></div>
        ) : currentCompanyError ? (
          <div className="check-result-state check-result-error" role="alert"><CircleAlert size={22} /><div><strong>Company check unavailable</strong><p>{currentCompanyError.message}</p></div></div>
        ) : !companyData ? (
          <div className="check-result-state"><LoaderCircle className="spin" size={22} /><div><strong>Checking Companies House</strong><p>Looking only for the exact name or company number.</p></div></div>
        ) : companyData.data_mode === "unavailable" ? (
          <div className="check-result-state check-result-warning"><CircleAlert size={22} /><div><strong>Companies House is not connected</strong><p>{companyData.message}</p></div></div>
        ) : companyData.results.length === 0 ? (
          <div className="check-result-state"><SearchX size={22} /><div><strong>No exact Companies House record found</strong><p>Similar or partial names are intentionally not shown.</p></div></div>
        ) : (
          <div className="result-list independent-result-list">
            {companyData.results.map((result) => (
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
        )}
      </section>

      <section className="independent-result-section sponsor-independent-result" aria-labelledby="sponsor-result-heading">
        <div className="independent-result-title">
          <div><span className="result-group-icon sponsor-group-icon"><ShieldCheck size={18} /></span><div><h2 id="sponsor-result-heading">Sponsorship check result</h2><p>{sponsorQuery ? `Exact query: “${sponsorQuery}”` : "No query submitted"}</p></div></div>
          <span>Stored sponsor list</span>
        </div>
        {sponsorQuery.length < 2 ? (
          <div className="check-result-state"><SearchX size={22} /><div><strong>Enter an organisation name</strong><p>This check uses its own input and does not read the Companies House result.</p></div></div>
        ) : currentSponsorError ? (
          <div className="check-result-state check-result-error" role="alert"><CircleAlert size={22} /><div><strong>Sponsorship check unavailable</strong><p>{currentSponsorError.message}</p></div></div>
        ) : !sponsorData ? (
          <div className="check-result-state"><LoaderCircle className="spin" size={22} /><div><strong>Checking the stored sponsor list</strong><p>Looking only for the exact organisation name.</p></div></div>
        ) : sponsorData.message ? (
          <div className="check-result-state check-result-warning"><CircleAlert size={22} /><div><strong>Sponsor list unavailable</strong><p>{sponsorData.message}</p></div></div>
        ) : sponsorData.results.length === 0 ? (
          <div className="check-result-state"><SearchX size={22} /><div><strong>Exact name not found in the stored sponsor list</strong><p>No similar names are substituted. This result applies only to the name entered.</p></div></div>
        ) : (
          <div className="result-list independent-result-list">
            {sponsorData.results.map((result) => (
              <Link href={`/sponsor/${result.id}`} className="result-card sponsor-result-card" key={result.id}>
                <span className="result-icon sponsor-result-icon"><ShieldCheck size={23} /></span>
                <div className="result-title"><h2>{result.organisation_name}</h2><p>Exact stored sponsor-list record</p></div>
                <div className="result-meta">
                  <span className="dot-status is-active">Listed sponsor · {result.rating || "Rating unavailable"}</span>
                  <span><MapPin size={14} /> {[result.town_city, result.county].filter(Boolean).join(", ") || "Location unavailable"}</span>
                </div>
                <span className="result-open">View sponsor record <ArrowRight size={16} /></span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default function SearchPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading checks…</div>}><SearchResults /></Suspense>;
}
