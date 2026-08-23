"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { CompanySponsorSearchResults } from "@/components/CompanySponsorSearchResults";
import { SearchBox } from "@/components/SearchBox";

function SearchResults() {
  const params = useSearchParams();
  const query = params.get("q")?.trim()
    || params.get("company")?.trim()
    || params.get("sponsor")?.trim()
    || "";

  return (
    <div className="shell search-page engine-search-page combined-source-search-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading compact-search-heading">
        <div>
          <span className="kicker">Search results</span>
          <h1>{query ? <>Results for “{query}”</> : "Search company and sponsor records"}</h1>
        </div>
        <div className="search-page-box"><SearchBox initialValue={query} /></div>
      </div>
      <CompanySponsorSearchResults query={query} />
    </div>
  );
}

export default function SearchPage() {
  return <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading results…</div>}><SearchResults /></Suspense>;
}
