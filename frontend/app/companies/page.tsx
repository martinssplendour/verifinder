"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { CompanySponsorSearchResults } from "@/components/CompanySponsorSearchResults";
import { SearchBox } from "@/components/SearchBox";

function CompanySearch() {
  const query = useSearchParams().get("q")?.trim() || "";
  return (
    <div className="shell search-page engine-search-page source-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading compact-search-heading">
        <div><span className="kicker">Company Check</span><h1>{query ? <>Companies matching “{query}”</> : "Check a company"}</h1></div>
        <div className="search-page-box"><SearchBox initialValue={query} mode="company" /></div>
      </div>
      <CompanySponsorSearchResults query={query} mode="company" />
    </div>
  );
}

export default function CompaniesPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Company Check…</div>}><CompanySearch /></Suspense>;
}
