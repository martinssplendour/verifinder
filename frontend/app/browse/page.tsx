"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  Globe,
  LoaderCircle,
  MapPin,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { browseDataset, getBrowseCatalogue, getBrowsePlaces } from "@/services/api";
import type { BrowseCatalogue, BrowseResponse } from "@/types";

function BrowseWorkspace() {
  const router = useRouter();
  const params = useSearchParams();
  const dataset = params.get("dataset") || "sponsors";
  const country = params.get("country") || "";
  const place = params.get("place") || "";
  const page = Math.max(1, Number(params.get("page") || 1));

  // Everything fetched is stamped with the filter it belongs to, so a stale
  // response is simply not shown rather than cleared on every filter change.
  const view = `${dataset}|${country}|${place}|${page}`;
  const [catalogue, setCatalogue] = useState<BrowseCatalogue | null>(null);
  const [placeIndex, setPlaceIndex] = useState<{ dataset: string; values: string[] } | null>(null);
  const [payload, setPayload] = useState<{ view: string; response: BrowseResponse } | null>(null);
  const [failure, setFailure] = useState<{ view: string; message: string } | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getBrowseCatalogue(controller.signal).then(setCatalogue).catch(() => undefined);
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getBrowsePlaces(dataset, controller.signal)
      .then((values) => setPlaceIndex({ dataset, values }))
      .catch(() => setPlaceIndex({ dataset, values: [] }));
    return () => controller.abort();
  }, [dataset]);

  useEffect(() => {
    const controller = new AbortController();
    browseDataset(dataset, { country, place, page }, controller.signal)
      .then((response) => setPayload({ view, response }))
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setFailure({ view, message: requestError.message });
      });
    return () => controller.abort();
  }, [dataset, country, place, page, view]);

  const places = placeIndex?.dataset === dataset ? placeIndex.values : [];
  const data = payload?.view === view ? payload.response : null;
  const error = failure?.view === view ? failure.message : null;

  const current = useMemo(
    () => catalogue?.datasets.find((item) => item.id === dataset) || null,
    [catalogue, dataset],
  );

  function apply(next: Record<string, string>) {
    const merged = new URLSearchParams(params.toString());
    Object.entries(next).forEach(([key, value]) => {
      if (value) merged.set(key, value);
      else merged.delete(key);
    });
    // Any change other than paging returns to the first page.
    if (!("page" in next)) merged.delete("page");
    router.push(`/browse?${merged.toString()}`);
  }

  const lastPage = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const filtered = Boolean(country || place);

  return (
    <div className="shell search-page browse-page">
      <Link className="back-link" href="/">← Back to home</Link>
      <div className="search-page-heading browse-heading">
        <div>
          <span className="kicker">Browse the registers</span>
          <h1>{current?.label || "Open the connected data"}</h1>
          <p>{current?.description || "Look through a whole official register, or narrow it to one place."}</p>
        </div>
        <button
          className={`browse-filter-button${filtered ? " is-applied" : ""}`}
          type="button"
          onClick={() => setFiltersOpen((open) => !open)}
          aria-expanded={filtersOpen}
        >
          <SlidersHorizontal size={17} />
          {filtered ? `Filtered: ${place || country}` : "Filter"}
        </button>
      </div>

      {filtersOpen && (
        <section className="browse-filters" aria-label="Register filters">
          <label>
            <span><Database size={13} /> Register</span>
            <select value={dataset} onChange={(event) => apply({ dataset: event.target.value, place: "" })}>
              {(catalogue?.datasets || []).map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span><Globe size={13} /> Country</span>
            <select value={country} onChange={(event) => apply({ country: event.target.value })}>
              <option value="">All countries</option>
              {(catalogue?.countries || []).map((item) => (
                <option key={item.code} value={item.code}>{item.name}</option>
              ))}
            </select>
          </label>
          <label>
            <span><MapPin size={13} /> {current?.place_label || "Place"}</span>
            <select
              value={place}
              disabled={!current?.place_label || places.length === 0}
              onChange={(event) => apply({ place: event.target.value })}
            >
              <option value="">{current?.place_label ? "Everywhere" : "This register holds no place"}</option>
              {places.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          {filtered && (
            <button className="browse-clear" type="button" onClick={() => apply({ country: "", place: "" })}>
              <X size={13} /> Clear filter
            </button>
          )}
        </section>
      )}

      {error ? (
        <div className="empty-state error-state" role="alert"><CircleAlert size={28} /><h2>That register could not be opened</h2><p>{error}</p></div>
      ) : !data ? (
        <div className="loading-state"><LoaderCircle size={22} /> Opening the register…</div>
      ) : data.message ? (
        <div className="empty-state"><Database size={28} /><h2>Not imported yet</h2><p>{data.message}</p></div>
      ) : data.records.length === 0 ? (
        <div className="empty-state"><Database size={28} /><h2>No records{place ? ` in ${place}` : ""}</h2><p>Clear the filter to see the whole register.</p></div>
      ) : (
        <>
          <section className="result-group">
            <div className="result-group-heading">
              <div>
                <span className="result-group-icon"><Database size={18} /></span>
                <div>
                  <h2>{data.source?.organisation || current?.organisation}</h2>
                  <p>{data.dataset_version ? `Version ${data.dataset_version}` : "Imported snapshot"}{place ? ` · ${place}` : ""}</p>
                </div>
              </div>
              <span>{data.total.toLocaleString("en-GB")} records</span>
            </div>
            <div className="result-list">
              {data.records.map((record) => (
                <Link className="result-card browse-result-card" href={record.href} key={`${record.id}-${record.title}`}>
                  <div className="result-title"><h2>{record.title}</h2><p>{record.subtitle || "Official record"}</p></div>
                  <div className="result-meta">{record.place && <span><MapPin size={14} /> {record.place}</span>}</div>
                  <span className="result-open">Open record <ArrowRight size={16} /></span>
                </Link>
              ))}
            </div>
          </section>
          <nav className="browse-pager" aria-label="Register pages">
            <button type="button" disabled={page <= 1} onClick={() => apply({ page: String(page - 1) })}>
              <ChevronLeft size={16} /> Previous
            </button>
            <span>Page {page.toLocaleString("en-GB")} of {lastPage.toLocaleString("en-GB")}</span>
            <button type="button" disabled={page >= lastPage} onClick={() => apply({ page: String(page + 1) })}>
              Next <ChevronRight size={16} />
            </button>
          </nav>
        </>
      )}
    </div>
  );
}

export default function BrowsePage() {
  return (
    <Suspense fallback={<div className="loading-state page-loading"><LoaderCircle size={22} /> Loading the registers…</div>}>
      <BrowseWorkspace />
    </Suspense>
  );
}
