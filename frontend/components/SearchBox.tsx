"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Building2, LoaderCircle, Search, ShieldCheck } from "lucide-react";
import { suggestCompanies, suggestSponsors } from "@/services/api";
import type { SearchResult, SponsorRecordView } from "@/types";

type Suggestion =
  | { kind: "company"; record: SearchResult }
  | { kind: "sponsor"; record: SponsorRecordView };

interface SuggestionState {
  query: string;
  companies: SearchResult[];
  sponsors: SponsorRecordView[];
  loading: boolean;
}

type SearchMode = "all" | "company" | "sponsor";

export function SearchBox({
  initialValue = "",
  mode = "all",
}: {
  initialValue?: string;
  mode?: SearchMode;
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialValue);
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [suggestions, setSuggestions] = useState<SuggestionState>({
    query: "",
    companies: [],
    sponsors: [],
    loading: false,
  });

  const value = query.trim();
  const current = suggestions.query === value && value.length >= 2;
  const items = useMemo<Suggestion[]>(() => {
    if (!current) return [];
    return [
      ...suggestions.companies.map((record) => ({ kind: "company" as const, record })),
      ...suggestions.sponsors.map((record) => ({ kind: "sponsor" as const, record })),
    ];
  }, [current, suggestions.companies, suggestions.sponsors]);
  const showSuggestions = focused && value.length >= 2;

  useEffect(() => {
    if (!focused || value.length < 2) return;
    const controller = new AbortController();
    let active = true;
    const timer = window.setTimeout(async () => {
      setSuggestions({ query: value, companies: [], sponsors: [], loading: true });
      const [companyResult, sponsorResult] = await Promise.allSettled([
        mode !== "sponsor" ? suggestCompanies(value, controller.signal) : Promise.resolve(null),
        mode !== "company" ? suggestSponsors(value, controller.signal) : Promise.resolve(null),
      ]);
      if (!active) return;
      setSuggestions({
        query: value,
        companies: companyResult.status === "fulfilled" && companyResult.value ? companyResult.value.results : [],
        sponsors: sponsorResult.status === "fulfilled" && sponsorResult.value ? sponsorResult.value.results : [],
        loading: false,
      });
      setActiveIndex(-1);
    }, 220);
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [focused, mode, value]);

  function resultsUrl() {
    const path = mode === "company" ? "/companies" : mode === "sponsor" ? "/sponsors" : "/search";
    return `${path}?${new URLSearchParams({ q: value }).toString()}`;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (value.length < 2) return;
    router.push(resultsUrl());
  }

  function openSuggestion(item: Suggestion) {
    if (item.kind === "company") {
      router.push(`/company/${encodeURIComponent(item.record.company_number)}`);
    } else {
      router.push(`/sponsor/${encodeURIComponent(item.record.id)}`);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!showSuggestions || items.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % items.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index <= 0 ? items.length - 1 : index - 1));
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      openSuggestion(items[activeIndex]);
    } else if (event.key === "Escape") {
      setFocused(false);
      setActiveIndex(-1);
    }
  }

  function renderCompany(record: SearchResult, index: number) {
    return (
      <Link
        className={`suggestion-row ${activeIndex === index ? "is-active" : ""}`}
        href={`/company/${encodeURIComponent(record.company_number)}`}
        id={`source-suggestion-${index}`}
        key={record.company_number}
        role="option"
        aria-selected={activeIndex === index}
        onMouseDown={(event) => event.preventDefault()}
      >
        <span className="suggestion-icon"><Building2 size={17} /></span>
        <span className="suggestion-main">
          <strong>{record.company_name}</strong>
          <small>{[record.company_number, record.location, record.status].filter(Boolean).join(" · ")}</small>
        </span>
        <ArrowRight size={16} />
      </Link>
    );
  }

  function renderSponsor(record: SponsorRecordView, index: number) {
    return (
      <Link
        className={`suggestion-row ${activeIndex === index ? "is-active" : ""}`}
        href={`/sponsor/${encodeURIComponent(record.id)}`}
        id={`source-suggestion-${index}`}
        key={record.id}
        role="option"
        aria-selected={activeIndex === index}
        onMouseDown={(event) => event.preventDefault()}
      >
        <span className="suggestion-icon sponsor-suggestion-icon"><ShieldCheck size={17} /></span>
        <span className="suggestion-main">
          <strong>{record.organisation_name}</strong>
          <small>{[record.town_city, record.rating].filter(Boolean).join(" · ")}</small>
        </span>
        <ArrowRight size={16} />
      </Link>
    );
  }

  const inputId = `${mode}-source-search`;
  const label = mode === "company"
    ? "Search Companies House"
    : mode === "sponsor"
      ? "Search the sponsor register"
      : "Search company and sponsor records";
  const placeholder = mode === "company"
    ? "Start typing a company name or number..."
    : mode === "sponsor"
      ? "Start typing a sponsor organisation..."
      : "Start typing a company or sponsor name...";

  return (
    <div className="search-combobox global-exact-search">
      <form className="search-form" onSubmit={submit} role="search">
        <Search className="search-leading" size={21} aria-hidden="true" />
        <label className="sr-only" htmlFor={inputId}>{label}</label>
        <input
          id={inputId}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(-1);
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showSuggestions}
          aria-controls="source-suggestions"
          aria-activedescendant={activeIndex >= 0 ? `source-suggestion-${activeIndex}` : undefined}
        />
        {suggestions.loading && current ? <LoaderCircle className="search-spinner" size={18} aria-label="Loading source suggestions" /> : null}
        <button type="submit" aria-label="Submit search"><Search size={20} /></button>
      </form>
      {showSuggestions ? (
        <div className="suggestions" id="source-suggestions" role="listbox" aria-label="Source record suggestions">
          {current && suggestions.companies.length > 0 ? (
            <>
              <div className="suggestions-heading"><span>Companies House suggestions</span><span>Company source</span></div>
              {suggestions.companies.map((record, index) => renderCompany(record, index))}
            </>
          ) : null}
          {current && suggestions.sponsors.length > 0 ? (
            <>
              <div className="suggestions-heading sponsor-heading"><span>Stored sponsor-list suggestions</span><span>Sponsor source</span></div>
              {suggestions.sponsors.map((record, index) => renderSponsor(record, suggestions.companies.length + index))}
            </>
          ) : null}
          {current && !suggestions.loading && items.length === 0 ? (
            <p className="suggestion-message">No suggestions found. Press search to check the full name.</p>
          ) : null}
          <button
            className="view-results"
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => value.length >= 2 && router.push(resultsUrl())}
          >
            View search results <ArrowRight size={14} />
          </button>
        </div>
      ) : null}
    </div>
  );
}
