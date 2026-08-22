"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, CalendarDays, ChevronLeft, CircleAlert, Database, LoaderCircle, MapPin, ShieldCheck, Store, Utensils } from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { getFoodEstablishment } from "@/services/api";
import type { FoodEstablishmentView } from "@/types";

function readableDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function score(value: number | null) {
  return value === null ? "Not published" : String(value);
}

export default function FoodEstablishmentPage({ params }: { params: Promise<{ recordId: string }> }) {
  const { recordId } = use(params);
  const [record, setRecord] = useState<FoodEstablishmentView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getFoodEstablishment(recordId, controller.signal).then(setRecord).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [recordId]);

  if (error) return <div className="shell profile-error"><CircleAlert size={32} /><h1>Food establishment unavailable</h1><p>{error}</p><Link className="button" href="/food">Back to Food Check</Link></div>;
  if (!record) return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading food hygiene record…</div>;

  const location = [record.address, record.postcode].filter(Boolean).join(", ") || "Location unavailable";
  return (
    <div className="profile-page food-detail-page">
      <div className="shell">
        <Link className="back-link" href={`/food?q=${encodeURIComponent(record.business_name)}`}><ChevronLeft size={16} /> Back to Food Check</Link>
        <header className="company-header food-header"><span className="company-monogram food-monogram"><Utensils size={30} /></span><div><span className="kicker">Food Standards Agency record</span><h1>{record.business_name}</h1><StatusPill status="verified">Official published inspection outcome</StatusPill></div></header>

        <div className="language-note food-identity-note"><CircleAlert size={18} /><p>The rating reflects standards found on the inspection date. A pending, appealed or older rating may not describe conditions today.</p></div>

        <section className="summary-grid food-summary-grid" aria-label="Food hygiene summary">
          <article className="summary-card food-rating-summary"><span className="summary-label"><ShieldCheck size={16} /> Published rating</span><strong>{record.rating_value || "Unavailable"}</strong><small>{record.scheme_type || "Scheme unavailable"}</small></article>
          <article className="summary-card"><span className="summary-label"><CalendarDays size={16} /> Rating date</span><strong>{readableDate(record.rating_date)}</strong><small>{record.new_rating_pending ? "A new rating is pending" : "No pending rating shown"}</small></article>
          <article className="summary-card"><span className="summary-label"><Store size={16} /> Business type</span><strong className="long-value">{record.business_type || "Unavailable"}</strong><small>FHRS ID {record.fhrs_id}</small></article>
          <article className="summary-card"><span className="summary-label"><MapPin size={16} /> Local authority</span><strong className="long-value">{record.local_authority_name || "Unavailable"}</strong><small>Publishing authority</small></article>
        </section>

        <div className="sponsor-detail-grid food-detail-grid">
          <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Inspection details</span><h2>Food hygiene scores</h2></div><ShieldCheck size={21} /></div><p className="panel-helper">FHRS component scores are only published where available; lower scores indicate better compliance.</p><dl className="detail-list"><div><dt>Hygiene</dt><dd>{score(record.hygiene_score)}</dd></div><div><dt>Structural</dt><dd>{score(record.structural_score)}</dd></div><div><dt>Confidence in management</dt><dd>{score(record.confidence_in_management_score)}</dd></div><div><dt>New rating pending</dt><dd>{record.new_rating_pending ? "Yes" : "No"}</dd></div></dl></article>

          <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Location and provenance</span><h2>Official record</h2></div><Database size={21} /></div><dl className="detail-list"><div><dt>Address</dt><dd>{location}</dd></div><div><dt>Local business ID</dt><dd>{record.local_authority_business_id || "Not published"}</dd></div><div><dt>Source</dt><dd>{record.source.organisation}</dd></div><div><dt>Snapshot</dt><dd>{record.source.version}</dd></div><div><dt>Retrieved</dt><dd>{readableDate(record.source.retrieved_at)}</dd></div></dl><a className="secondary-cta" href={record.source.official_url} target="_blank" rel="noreferrer">View official ratings source <ArrowUpRight size={15} /></a></article>
        </div>
        <p className="disclaimer">Food hygiene information is based on published local-authority inspection data and is not a guarantee of current conditions.</p>
      </div>
    </div>
  );
}
