"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Building2, CircleAlert, LoaderCircle, Search, ShieldCheck } from "lucide-react";
import { useCompanySponsorSuggestions } from "@/hooks/useCompanySponsorSuggestions";
import type { SearchResult, SponsorRecordView } from "@/types";

type Suggestion =
  | { kind: "company"; id: string; href: string; company: SearchResult }
  | { kind: "sponsor"; id: string; href: string; sponsor: SponsorRecordView };

export function SearchBox({ initialValue = "" }: { initialValue?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState(initialValue);
  const { companies, sponsors, companyUnavailable, loading, error } = useCompanySponsorSuggestions(query);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasFocus = useRef(false);
  const suggestions: Suggestion[] = [
    ...companies.map((company) => ({
      kind: "company" as const,
      id: `company-${company.company_number}`,
      href: `/company/${company.company_number}`,
      company,
    })),
    ...sponsors.map((sponsor) => ({
      kind: "sponsor" as const,
      id: `sponsor-${sponsor.id}`,
      href: `/sponsor/${sponsor.id}`,
      sponsor,
    })),
  ];

  useEffect(() => {
    setOpen(hasFocus.current);
    setActiveIndex(-1);
  }, [companies, sponsors]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length >= 2) {
      setOpen(false);
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  function openSuggestion(suggestion: Suggestion) {
    setOpen(false);
    router.push(suggestion.href);
  }

  function handleKeys(event: KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => Math.min(current + 1, suggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, -1));
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      openSuggestion(suggestions[activeIndex]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  function option(suggestion: Suggestion, index: number) {
    const isCompany = suggestion.kind === "company";
    const title = isCompany ? suggestion.company.company_name : suggestion.sponsor.organisation_name;
    const meta = isCompany
      ? `${suggestion.company.location || "United Kingdom"} · ${suggestion.company.status || "Status unavailable"} · ${suggestion.company.company_number}`
      : `${suggestion.sponsor.town_city || "Location unavailable"} · ${suggestion.sponsor.rating ? `${suggestion.sponsor.rating} rating` : "Rating unavailable"} · ${suggestion.sponsor.routes.length} route${suggestion.sponsor.routes.length === 1 ? "" : "s"}`;
    return (
      <button
        type="button"
        role="option"
        aria-selected={index === activeIndex}
        className={`suggestion-row ${index === activeIndex ? "is-active" : ""}`}
        id={`suggestion-${index}`}
        key={suggestion.id}
        onMouseDown={() => {
          if (blurTimer.current) clearTimeout(blurTimer.current);
          openSuggestion(suggestion);
        }}
      >
        <span className={`suggestion-icon ${isCompany ? "" : "sponsor-suggestion-icon"}`}>
          {isCompany ? <Building2 size={18} /> : <ShieldCheck size={18} />}
        </span>
        <span className="suggestion-main"><strong>{title}</strong><small>{meta}</small></span>
        <ArrowRight size={17} />
      </button>
    );
  }

  return (
    <div className="search-combobox">
      <form className="search-form" onSubmit={submit} role="search">
        <Search className="search-leading" size={21} aria-hidden="true" />
        <label className="sr-only" htmlFor="global-company-search">Search for a UK company or sponsor</label>
        <input
          id="global-company-search"
          value={query}
          onChange={(event) => {
            const value = event.target.value;
            setQuery(value);
            if (value.trim().length < 2) {
              setOpen(false);
            }
          }}
          onFocus={() => {
            hasFocus.current = true;
            if (query.trim().length >= 2) setOpen(true);
          }}
          onBlur={() => {
            blurTimer.current = setTimeout(() => {
              hasFocus.current = false;
              setOpen(false);
            }, 150);
          }}
          onKeyDown={handleKeys}
          placeholder="Search a company name or number..."
          autoComplete="off"
          aria-expanded={open}
          aria-controls="company-suggestions"
          aria-activedescendant={activeIndex >= 0 ? `suggestion-${activeIndex}` : undefined}
          role="combobox"
        />
        {loading && <LoaderCircle className="search-spinner" size={19} aria-label="Searching" />}
        <button type="submit" aria-label="Search verified sources"><Search size={20} /></button>
      </form>
      {open && (
        <div className="suggestions" id="company-suggestions" role="listbox">
          {error ? <p className="suggestion-message error-text">{error}</p> : (
            <>
              {companyUnavailable && (
                <div className="suggestion-source-note"><CircleAlert size={14} /> Companies House is not connected. Sponsor-register matches remain available.</div>
              )}
              {companies.length > 0 && (
                <>
                  <div className="suggestions-heading"><span>Companies House</span><span><Building2 size={13} /> Company records</span></div>
                  {companies.map((company, index) => option(suggestions[index], index))}
                </>
              )}
              {sponsors.length > 0 && (
                <>
                  <div className="suggestions-heading sponsor-heading"><span>UK sponsor register</span><span><ShieldCheck size={13} /> Official dataset</span></div>
                  {sponsors.map((sponsor, index) => {
                    const suggestionIndex = companies.length + index;
                    return option(suggestions[suggestionIndex], suggestionIndex);
                  })}
                </>
              )}
              {!loading && suggestions.length === 0 && <p className="suggestion-message">No matching verified record found. Check the spelling or try a company number.</p>}
            </>
          )}
          <button className="view-results" type="button" onMouseDown={() => router.push(`/search?q=${encodeURIComponent(query.trim())}`)}>
            View all Company Check results <ArrowRight size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
