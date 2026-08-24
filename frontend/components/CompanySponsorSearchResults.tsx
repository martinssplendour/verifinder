"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Building2,
  CircleAlert,
  LoaderCircle,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import { NoExactMatch } from "@/components/NoExactMatch";
import { searchCompanies, searchSponsors } from "@/services/api";
import type { SearchResponse, SearchResult, SponsorRecordView, SponsorSearchResponse } from "@/types";

type SearchMode = "all" | "company" | "sponsor";
type SearchError = { query: string; message: string };

function CompanyCard({ result }: { result: SearchResult }) {
  return (
    <Link href={`/company/${result.company_number}`} className="result-card">
      <span className="result-icon"><Building2 size={23} /></span>
      <div className="result-title"><h2>{result.company_name}</h2><p>Company number {result.company_number}</p></div>
      <div className="result-meta">
        <span className={`dot-status ${result.status === "active" ? "is-active" : ""}`}>{result.status || "Status unavailable"}</span>
        <span><MapPin size={14} /> {result.location || "Location unavailable"}</span>
      </div>
      <span className="result-open">View company <ArrowRight size={16} /></span>
    </Link>
  );
}

function SponsorCard({ result }: { result: SponsorRecordView }) {
  return (
    <Link href={`/sponsor/${result.id}`} className="result-card sponsor-result-card">
      <span className="result-icon sponsor-result-icon"><ShieldCheck size={23} /></span>
      <div className="result-title"><h2>{result.organisation_name}</h2><p>{result.routes.join(" · ") || "Sponsor record"}</p></div>
      <div className="result-meta">
        <span className="dot-status is-active">{result.rating || "Rating unavailable"}</span>
        <span><MapPin size={14} /> {[result.town_city, result.county].filter(Boolean).join(", ") || "Location unavailable"}</span>
      </div>
      <span className="result-open">View sponsor <ArrowRight size={16} /></span>
    </Link>
  );
}

function CompanyGroup({ data }: { data: SearchResponse }) {
  if (data.results.length === 0) return null;
  return (
    <section className="result-group" aria-label="Companies House results">
      <div className="result-group-heading">
        <div><span className="result-group-icon"><Building2 size={18} /></span><div><h2>Companies House</h2><p>Company records</p></div></div>
        <span>{data.results.length} found</span>
      </div>
      <div className="result-list">
        {data.results.map((result) => <CompanyCard result={result} key={result.company_number} />)}
      </div>
    </section>
  );
}

function SponsorGroup({ data }: { data: SponsorSearchResponse }) {
  if (data.results.length === 0) return null;
  return (
    <section className="result-group" aria-label="Sponsor register results">
      <div className="result-group-heading sponsor-result-heading">
        <div><span className="result-group-icon sponsor-group-icon"><ShieldCheck size={18} /></span><div><h2>Sponsor register</h2><p>Worker sponsor records</p></div></div>
        <span>{data.results.length} found</span>
      </div>
      <div className="result-list">
        {data.results.map((result) => <SponsorCard result={result} key={result.id} />)}
      </div>
    </section>
  );
}

export function CompanySponsorSearchResults({
  query,
  mode = "all",
}: {
  query: string;
  mode?: SearchMode;
}) {
  const [companies, setCompanies] = useState<SearchResponse | null>(null);
  const [sponsors, setSponsors] = useState<SponsorSearchResponse | null>(null);
  const [companyError, setCompanyError] = useState<SearchError | null>(null);
  const [sponsorError, setSponsorError] = useState<SearchError | null>(null);

  useEffect(() => {
    if (mode === "sponsor" || query.length < 2) return;
    const controller = new AbortController();
    searchCompanies(query, controller.signal).then((response) => {
      setCompanies(response);
      setCompanyError(null);
    }).catch((requestError) => {
      if (requestError.name !== "AbortError") setCompanyError({ query, message: requestError.message });
    });
    return () => controller.abort();
  }, [mode, query]);

  useEffect(() => {
    if (mode === "company" || query.length < 2) return;
    const controller = new AbortController();
    searchSponsors(query, controller.signal).then((response) => {
      setSponsors(response);
      setSponsorError(null);
    }).catch((requestError) => {
      if (requestError.name !== "AbortError") setSponsorError({ query, message: requestError.message });
    });
    return () => controller.abort();
  }, [mode, query]);

  if (query.length < 2) {
    return null;
  }

  const companyData = companies?.query === query ? companies : null;
  const sponsorData = sponsors?.query === query ? sponsors : null;
  const currentCompanyError = companyError?.query === query ? companyError : null;
  const currentSponsorError = sponsorError?.query === query ? sponsorError : null;
  const companyDone = mode === "sponsor" || Boolean(companyData || currentCompanyError);
  const sponsorDone = mode === "company" || Boolean(sponsorData || currentSponsorError);

  if (!companyDone || !sponsorDone) {
    return <div className="loading-state"><LoaderCircle size={22} /> Searching records…</div>;
  }

  const companyIssue = currentCompanyError?.message || (companyData?.data_mode === "unavailable" ? companyData.message : null);
  const sponsorIssue = currentSponsorError?.message || sponsorData?.message || null;
  const found = (companyData?.results.length || 0) + (sponsorData?.results.length || 0);
  const suggestions = [
    ...(companyData?.suggestions || []).map((result) => <CompanyCard result={result} key={`company-${result.company_number}`} />),
    ...(sponsorData?.suggestions || []).map((result) => <SponsorCard result={result} key={`sponsor-${result.id}`} />),
  ];

  return (
    <div className="source-search-results">
      {companyIssue ? <div className="source-result-alert" role="status"><CircleAlert size={17} /><span>{companyIssue}</span></div> : null}
      {sponsorIssue ? <div className="source-result-alert" role="status"><CircleAlert size={17} /><span>{sponsorIssue}</span></div> : null}
      {companyData ? <CompanyGroup data={companyData} /> : null}
      {sponsorData ? <SponsorGroup data={sponsorData} /> : null}
      {found === 0 && !companyIssue && !sponsorIssue ? (
        <NoExactMatch query={query} hint="These registers are matched on the exact legal name or number, so check the spelling and any suffix such as Ltd or PLC.">
          {suggestions}
        </NoExactMatch>
      ) : null}
    </div>
  );
}
