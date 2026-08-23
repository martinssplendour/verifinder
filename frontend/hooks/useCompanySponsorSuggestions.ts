"use client";

import { useEffect, useState } from "react";
import { searchCompanies, searchSponsors } from "@/services/api";
import type { SearchResult, SponsorRecordView } from "@/types";

export function useCompanySponsorSuggestions(query: string) {
  const [companies, setCompanies] = useState<SearchResult[]>([]);
  const [sponsors, setSponsors] = useState<SponsorRecordView[]>([]);
  const [companyUnavailable, setCompanyUnavailable] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query.trim().length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      const [companyResult, sponsorResult] = await Promise.allSettled([
        searchCompanies(query.trim(), controller.signal),
        searchSponsors(query.trim(), controller.signal),
      ]);
      if (controller.signal.aborted) return;
      if (companyResult.status === "fulfilled") {
        setCompanies(companyResult.value.results);
        setCompanyUnavailable(companyResult.value.data_mode === "unavailable");
      } else {
        setCompanies([]);
        setCompanyUnavailable(false);
      }
      if (sponsorResult.status === "fulfilled") setSponsors(sponsorResult.value.results);
      else setSponsors([]);
      if (companyResult.status === "rejected" && sponsorResult.status === "rejected") {
        setError("Search is temporarily unavailable. You can try again shortly.");
      }
      setLoading(false);
    }, 280);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  return { companies, sponsors, companyUnavailable, loading, error };
}
