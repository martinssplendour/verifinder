"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BadgeCheck,
  ChevronLeft,
  CircleAlert,
  Database,
  LoaderCircle,
  MapPin,
  Route,
  Search,
  ShieldCheck,
} from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { getSponsor } from "@/services/api";
import type { SponsorRecordView } from "@/types";

function readableDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

export default function SponsorPage({ params }: { params: Promise<{ recordId: string }> }) {
  const { recordId } = use(params);
  const [record, setRecord] = useState<SponsorRecordView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getSponsor(recordId, controller.signal).then(setRecord).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [recordId]);

  if (error) {
    return <div className="shell profile-error"><CircleAlert size={32} /><h1>Sponsor record unavailable</h1><p>{error}</p><Link className="button" href="/search">Back to Company Check</Link></div>;
  }
  if (!record) {
    return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Home Office sponsor record…</div>;
  }

  const location = [record.town_city, record.county].filter(Boolean).join(", ") || "Location unavailable";
  return (
    <div className="profile-page sponsor-page">
      <div className="shell">
        <Link className="back-link" href={`/search?q=${encodeURIComponent(record.organisation_name)}`}><ChevronLeft size={16} /> Back to Company Check</Link>
        <header className="company-header sponsor-header">
          <span className="company-monogram sponsor-monogram" aria-hidden="true"><ShieldCheck size={30} /></span>
          <div>
            <span className="kicker">Home Office organisation record</span>
            <h1>{record.organisation_name}</h1>
            <StatusPill status="match_found">Found on current imported register</StatusPill>
          </div>
        </header>

        <div className="language-note sponsor-identity-note">
          <CircleAlert size={18} />
          <p>This confirms that an organisation with this name and location appears in the worker sponsor register. It does not, by itself, identify a specific Companies House legal entity.</p>
        </div>

        <section className="summary-grid sponsor-summary-grid" aria-label="Sponsor record summary">
          <article className="summary-card"><span className="summary-label"><ShieldCheck size={16} /> Sponsor status</span><strong className="positive-text">Found on register</strong><small><BadgeCheck size={13} /> UK Visas and Immigration</small></article>
          <article className="summary-card"><span className="summary-label"><BadgeCheck size={16} /> Sponsor rating</span><strong>{record.rating || "Unavailable"}</strong><small>From the current imported record</small></article>
          <article className="summary-card"><span className="summary-label"><MapPin size={16} /> Listed location</span><strong>{location}</strong><small>Home Office register value</small></article>
          <article className="summary-card"><span className="summary-label"><Route size={16} /> Licensed routes</span><strong>{record.routes.length}</strong><small>{record.routes.length === 1 ? "Sponsorship route" : "Sponsorship routes"}</small></article>
        </section>

        <div className="sponsor-detail-grid">
          <article className="detail-panel">
            <div className="panel-title"><div><span className="kicker">Worker sponsorship</span><h2>Licensed routes</h2></div><Route size={21} /></div>
            <div className="sponsor-route-list">
              {record.routes.map((route) => <div key={route}><ShieldCheck size={16} /><span>{route}</span></div>)}
            </div>
            <Link className="secondary-cta" href={`/search?q=${encodeURIComponent(record.organisation_name)}`}><Search size={15} /> Find the related company record</Link>
          </article>

          <article className="detail-panel sponsor-source-panel">
            <div className="panel-title"><div><span className="kicker">Provenance</span><h2>Official source</h2></div><Database size={21} /></div>
            <dl className="detail-list">
              <div><dt>Organisation</dt><dd>{record.source.organisation}</dd></div>
              <div><dt>Dataset</dt><dd>{record.source.dataset}</dd></div>
              <div><dt>Published</dt><dd>{readableDate(record.source.published_at)}</dd></div>
              <div><dt>Retrieved</dt><dd>{readableDate(record.source.retrieved_at)}</dd></div>
              <div><dt>Version</dt><dd>{record.source.version || "Unavailable"}</dd></div>
            </dl>
            <a className="secondary-cta" href={record.source.official_url} target="_blank" rel="noreferrer">View official publication <ArrowUpRight size={15} /></a>
          </article>
        </div>

        <p className="disclaimer">Information is based on the imported public sponsor register and should not be treated as legal or immigration advice.</p>
      </div>
    </div>
  );
}
