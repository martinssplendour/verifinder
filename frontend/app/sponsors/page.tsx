"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { CompanySponsorSearchResults } from "@/components/CompanySponsorSearchResults";
import { SearchBox } from "@/components/SearchBox";

function SponsorSearch() {
  const query = useSearchParams().get("q")?.trim() || "";
  return (
    <div className="shell search-page engine-search-page source-search-page sponsor-source-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading compact-search-heading">
        <div><span className="kicker">Sponsorship Check</span><h1>{query ? <>Sponsors matching “{query}”</> : "Check a sponsor"}</h1></div>
        <div className="search-page-box"><SearchBox initialValue={query} mode="sponsor" /></div>
      </div>
      <CompanySponsorSearchResults query={query} mode="sponsor" />
    </div>
  );
}

export default function SponsorsPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Sponsorship Check…</div>}><SponsorSearch /></Suspense>;
}
