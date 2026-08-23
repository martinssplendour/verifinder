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

export function SearchBox({ initialValue = "" }: { initialValue?: string }) {
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
    if (value.length < 2) return;
    const controller = new AbortController();
    let active = true;
    const timer = window.setTimeout(async () => {
      setSuggestions({ query: value, companies: [], sponsors: [], loading: true });
      const [companyResult, sponsorResult] = await Promise.allSettled([
        suggestCompanies(value, controller.signal),
        suggestSponsors(value, controller.signal),
      ]);
      if (!active) return;
      setSuggestions({
        query: value,
        companies: companyResult.status === "fulfilled" ? companyResult.value.results : [],
        sponsors: sponsorResult.status === "fulfilled" ? sponsorResult.value.results : [],
        loading: false,
      });
      setActiveIndex(-1);
    }, 220);
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  function exactChecksUrl() {
    return `/search?${new URLSearchParams({ company: value, sponsor: value }).toString()}`;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (value.length < 2) return;
    router.push(exactChecksUrl());
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

  return (
    <div className="search-combobox global-exact-search">
      <form className="search-form" onSubmit={submit} role="search">
        <Search className="search-leading" size={21} aria-hidden="true" />
        <label className="sr-only" htmlFor="global-company-search">Company or sponsor source record</label>
        <input
          id="global-company-search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(-1);
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="Start typing a company or sponsor name..."
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showSuggestions}
          aria-controls="source-suggestions"
          aria-activedescendant={activeIndex >= 0 ? `source-suggestion-${activeIndex}` : undefined}
        />
        {suggestions.loading && current ? <LoaderCircle className="search-spinner" size={18} aria-label="Loading source suggestions" /> : null}
        <button type="submit" aria-label="Open the separate exact checks"><Search size={20} /></button>
      </form>
      {showSuggestions ? (
        <div className="suggestions" id="source-suggestions" role="listbox" aria-label="Source record suggestions">
          <div className="suggestion-source-note">
            Suggestions help you choose a source record. They do not join or verify records across sources.
          </div>
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
            <p className="suggestion-message">No source records contain that typed text. You can still run the separate exact checks.</p>
          ) : null}
          <button
            className="view-results"
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => value.length >= 2 && router.push(exactChecksUrl())}
          >
            Run two separate exact checks <ArrowRight size={14} />
          </button>
        </div>
      ) : null}
      <p className="global-search-helper">Choose a source record, or run the same exact text through two independent checks. Each name can be changed on the results page.</p>
    </div>
  );
}
