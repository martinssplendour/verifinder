"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Building2, CalendarDays, ChevronLeft, CircleAlert, Database, Home, Landmark, LoaderCircle, MapPin, PoundSterling, Zap } from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { getProperty } from "@/services/api";
import type { PropertyDetail } from "@/types";

const money = new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 0 });
const propertyTypes: Record<string, string> = { D: "Detached", S: "Semi-detached", T: "Terraced", F: "Flat / maisonette", O: "Other" };
const tenures: Record<string, string> = { F: "Freehold", L: "Leasehold", U: "Unknown" };

function readableDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function datasetLabel(value: string) {
  return value.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function epcRatingClass(rating: string | null) {
  if (!rating) return "";
  if (["A", "B", "C"].includes(rating.toUpperCase())) return "rating-good";
  if (["F", "G"].includes(rating.toUpperCase())) return "rating-poor";
  return "";
}

export default function PropertyDetailPage({ params }: { params: Promise<{ propertyKey: string }> }) {
  const { propertyKey } = use(params);
  const [record, setRecord] = useState<PropertyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getProperty(propertyKey, controller.signal).then(setRecord).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [propertyKey]);
  if (error) return <div className="shell profile-error"><CircleAlert size={32} /><h1>Property record unavailable</h1><p>{error}</p><Link className="button" href="/property">Back to Property Check</Link></div>;
  if (!record) return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading recorded sales…</div>;
  const latest = record.sales[0];
  return <div className="profile-page property-detail-page"><div className="shell">
    <Link className="back-link" href={`/property?q=${encodeURIComponent(record.postcode || record.address)}`}><ChevronLeft size={16} /> Back to Property Check</Link>
    <header className="company-header property-header"><span className="company-monogram property-monogram"><Home size={30} /></span><div><span className="kicker">HM Land Registry Price Paid record</span><h1>{record.address}</h1><StatusPill status="verified">Official recorded sale data</StatusPill></div></header>
    <div className="language-note property-identity-note"><CircleAlert size={18} /><p>This page identifies an address from Price Paid text fields. It does not establish title ownership, current value or an exact UPRN match.</p></div>
    <section className="summary-grid property-summary-grid" aria-label="Property summary"><article className="summary-card"><span className="summary-label"><PoundSterling size={16} /> Latest recorded price</span><strong>{money.format(latest.price)}</strong><small>Transferred {readableDate(latest.transfer_date)}</small></article><article className="summary-card"><span className="summary-label"><Home size={16} /> Property type</span><strong>{propertyTypes[record.property_type || ""] || "Other / unavailable"}</strong><small>{tenures[latest.tenure || ""] || "Tenure unavailable"}</small></article><article className="summary-card"><span className="summary-label"><Database size={16} /> Sales in snapshot</span><strong>{record.sales.length}</strong><small>Imported 2025–2026 history</small></article><article className="summary-card"><span className="summary-label"><MapPin size={16} /> Postcode</span><strong>{record.postcode || "Unavailable"}</strong><small>{[record.town_city, record.county].filter(Boolean).join(", ")}</small></article></section>
    <div className="property-detail-grid"><article className="detail-panel"><div className="panel-title"><div><span className="kicker">Transaction history</span><h2>Recorded sales</h2></div><CalendarDays size={21} /></div><div className="sale-timeline">{record.sales.map((sale) => <div key={sale.transaction_id}><span><i /></span><div><strong>{money.format(sale.price)}</strong><small>{readableDate(sale.transfer_date)} · {sale.new_build ? "New build" : "Established property"} · {tenures[sale.tenure || ""] || "Tenure unavailable"}</small></div></div>)}</div></article>
      <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Postcode comparison</span><h2>Nearby recorded sales</h2></div><Building2 size={21} /></div>{record.nearby_sales && <dl className="detail-list"><div><dt>Records in snapshot</dt><dd>{record.nearby_sales.count}</dd></div><div><dt>Median price</dt><dd>{record.nearby_sales.median_price ? money.format(record.nearby_sales.median_price) : "Unavailable"}</dd></div><div><dt>Lowest price</dt><dd>{record.nearby_sales.minimum_price ? money.format(record.nearby_sales.minimum_price) : "Unavailable"}</dd></div><div><dt>Highest price</dt><dd>{record.nearby_sales.maximum_price ? money.format(record.nearby_sales.maximum_price) : "Unavailable"}</dd></div></dl>}<p className="panel-helper">This is a simple postcode summary, not a comparable-property valuation.</p></article>
      <article className="detail-panel planning-detail-panel"><div className="panel-title"><div><span className="kicker">Postcode-level planning context</span><h2>Selected designations</h2></div><Landmark size={21} /></div>{record.planning.status === "unavailable" ? <p className="panel-helper">{record.planning.message}</p> : record.planning.constraints.length ? <div className="constraint-list">{record.planning.constraints.map((item, index) => <div key={`${item.dataset}-${item.reference || index}`}><span>{datasetLabel(item.dataset)}</span><strong>{item.name}</strong>{item.reference && <small>Ref {item.reference}</small>}</div>)}</div> : <div className="inline-empty"><strong>No matches returned</strong><p>No match in the selected datasets does not rule out other constraints or applications.</p></div>}<a className="secondary-cta" href={record.planning.source_url} target="_blank" rel="noreferrer">View Planning Data source <ArrowUpRight size={15} /></a></article>
      <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Data provenance</span><h2>Official snapshot</h2></div><Database size={21} /></div><dl className="detail-list"><div><dt>Publisher</dt><dd>{record.source.organisation}</dd></div><div><dt>Dataset</dt><dd>{record.source.dataset}</dd></div><div><dt>Version</dt><dd>{record.source.version}</dd></div><div><dt>Retrieved</dt><dd>{readableDate(record.source.retrieved_at)}</dd></div></dl><a className="secondary-cta" href={record.source.official_url} target="_blank" rel="noreferrer">View official data notes <ArrowUpRight size={15} /></a></article>
      <article className="detail-panel epc-detail-panel"><div className="panel-title"><div><span className="kicker">Postcode-matched register</span><h2>Energy Performance Certificates</h2></div><Zap size={21} /></div>{record.epc.status === "unavailable" ? <p className="panel-helper">{record.epc.message}</p> : record.epc.certificates.length ? <div className="constraint-list">{record.epc.certificates.map((cert, index) => <div key={cert.certificate_number || index}><span className={`epc-rating-badge ${epcRatingClass(cert.current_rating)}`}>{cert.current_rating || "—"}</span><div><strong>{cert.address}</strong>{cert.lodgement_date && <small> · Lodged {readableDate(cert.lodgement_date)}</small>}</div></div>)}</div> : <div className="inline-empty"><strong>No certificates returned</strong><p>No certificate for this postcode does not mean the property lacks a valid EPC.</p></div>}<a className="secondary-cta" href={record.epc.source_url} target="_blank" rel="noreferrer">View EPC register source <ArrowUpRight size={15} /></a></article>
    </div>
    <div className="limitations-note"><CircleAlert size={18} /><div><strong>Coverage and matching limits</strong><ul>{record.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
  </div></div>;
}
