"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BadgeCheck,
  Building2,
  Check,
  ChevronLeft,
  CircleAlert,
  Clock3,
  Database,
  FileText,
  Landmark,
  LoaderCircle,
  MapPin,
  Route,
  Share2,
  ShieldCheck,
} from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { WatchButton } from "@/components/WatchButton";
import { getCompany } from "@/services/api";
import type { CompanyProfile, SourceAttribution } from "@/types";

type Tab = "overview" | "sponsorship" | "details" | "sources";

function readableDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function SourceCard({ source }: { source: SourceAttribution }) {
  return (
    <article className="source-card">
      <span className="source-card-icon">{source.id === "companies-house" ? <Landmark size={20} /> : <ShieldCheck size={20} />}</span>
      <div>
        <span className="source-org">{source.organisation}</span>
        <h3>{source.dataset}</h3>
        <dl>
          <div><dt>Retrieved</dt><dd>{source.retrieved_at ? readableDate(source.retrieved_at) : "Not connected"}</dd></div>
          <div><dt>Dataset version</dt><dd>{source.version || "Live API response"}</dd></div>
        </dl>
        <a href={source.official_url} target="_blank" rel="noreferrer">View official source <ArrowUpRight size={14} /></a>
      </div>
    </article>
  );
}

export default function CompanyPage({ params }: { params: Promise<{ companyNumber: string }> }) {
  const { companyNumber } = use(params);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getCompany(companyNumber, controller.signal).then(setProfile).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [companyNumber]);

  async function share() {
    if (navigator.share) {
      await navigator.share({ title: profile?.company_name || "VeriFinder company check", url: window.location.href });
    } else {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    }
  }

  if (error) {
    return <div className="shell profile-error"><CircleAlert size={32} /><h1>Company unavailable</h1><p>{error}</p><Link className="button" href="/search">Back to search</Link></div>;
  }
  if (!profile) {
    return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading verified company record…</div>;
  }

  const companyActive = profile.company_status === "active";
  const sponsorship = profile.sponsorship;
  return (
    <div className="profile-page">
      <div className="shell">
        <div className="profile-topline">
          <Link className="back-link" href="/search"><ChevronLeft size={16} /> Back to search</Link>
          <div className="profile-actions">
            <WatchButton entityType="company" entityId={profile.company_number} label={profile.company_name} />
            <button className="icon-button" type="button" onClick={share}><Share2 size={17} /> {copied ? "Copied" : "Share"}</button>
          </div>
        </div>
        <header className="company-header">
          <span className="company-monogram" aria-hidden="true">{profile.company_name.slice(0, 1)}</span>
          <div>
            <h1>{profile.company_name}</h1>
            <StatusPill status={profile.verified_status}><span>Verified company record</span></StatusPill>
            <p>Company number: <strong>{profile.company_number}</strong> <span>·</span> Incorporated: <strong>{readableDate(profile.incorporation_date)}</strong></p>
          </div>
        </header>

        <section className="summary-grid" aria-label="Company summary">
          <article className="summary-card">
            <span className="summary-label"><Building2 size={16} /> Company status</span>
            <strong className={companyActive ? "positive-text" : ""}>{profile.company_status || "Unavailable"}</strong>
            <small><BadgeCheck size={13} /> {profile.company_source.organisation}</small>
          </article>
          <article className="summary-card">
            <span className="summary-label"><ShieldCheck size={16} /> Visa sponsorship</span>
            <strong className={sponsorship.status === "match_found" ? "positive-text" : ""}>{sponsorship.label}</strong>
            <small>{sponsorship.source ? <><BadgeCheck size={13} /> {sponsorship.source.organisation}</> : <><Database size={13} /> Awaiting source data</>}</small>
          </article>
          <article className="summary-card">
            <span className="summary-label"><Route size={16} /> Sponsorship routes</span>
            <strong>{sponsorship.routes[0] || "Data unavailable"}</strong>
            <small>{sponsorship.routes.length > 1 ? `+ ${sponsorship.routes.length - 1} more route` : "From the latest matched record"}</small>
          </article>
          <article className="summary-card">
            <span className="summary-label"><MapPin size={16} /> Registered office</span>
            <strong className="address-value">{profile.registered_office || "Not available"}</strong>
            <small>{profile.postcode || "Postcode unavailable"}</small>
          </article>
        </section>

        <nav className="profile-tabs" aria-label="Company profile sections">
          {(["overview", "sponsorship", "details", "sources"] as Tab[]).map((tab) => (
            <button key={tab} className={activeTab === tab ? "is-active" : ""} onClick={() => setActiveTab(tab)} type="button">
              {tab === "details" ? "Company details" : tab[0].toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>

        {activeTab === "overview" && (
          <div className="profile-content-grid">
            <article className="detail-panel company-overview">
              <div className="panel-title"><div><span className="kicker">Companies House</span><h2>Company overview</h2></div><FileText size={20} /></div>
              <dl className="detail-list">
                <div><dt>Legal name</dt><dd>{profile.company_name}</dd></div>
                <div><dt>Company type</dt><dd>{profile.company_type || "Not available"}</dd></div>
                <div><dt>Company number</dt><dd>{profile.company_number}</dd></div>
                <div><dt>Next accounts due</dt><dd>{readableDate(profile.accounts_next_due)}</dd></div>
              </dl>
              <div className="fact-source"><BadgeCheck size={15} /> Source: {profile.company_source.organisation}</div>
            </article>
            <article className="detail-panel sponsorship-panel">
              <div className="panel-title"><div><span className="kicker">UK visa sponsorship</span><h2>{sponsorship.label}</h2></div><ShieldCheck size={21} /></div>
              <StatusPill status={sponsorship.status}>{sponsorship.status.replaceAll("_", " ")}</StatusPill>
              <p>{sponsorship.explanation}</p>
              {sponsorship.rating && <div className="rating-row"><span>Sponsor rating</span><strong>{sponsorship.rating}</strong></div>}
              {sponsorship.routes.length > 0 && <div className="route-list">{sponsorship.routes.map((route) => <span key={route}><Check size={14} />{route}</span>)}</div>}
            </article>
            <article className="detail-panel recent-panel">
              <div className="panel-title"><div><span className="kicker">Version history</span><h2>Recent changes</h2></div><Clock3 size={20} /></div>
              <div className="no-changes"><span><Check size={20} /></span><strong>No verified changes yet</strong><p>Changes will appear after multiple official dataset versions are stored.</p></div>
            </article>
          </div>
        )}

        {activeTab === "sponsorship" && (
          <div className="single-panel-layout">
            <article className="detail-panel wide-panel">
              <div className="panel-title"><div><span className="kicker">Sponsor-register match</span><h2>{sponsorship.label}</h2></div><ShieldCheck size={22} /></div>
              <p className="lead-copy">{sponsorship.explanation}</p>
              <div className="sponsorship-facts">
                <div><span>Match status</span><StatusPill status={sponsorship.status}>{sponsorship.status.replaceAll("_", " ")}</StatusPill></div>
                <div><span>Match confidence</span><strong>{sponsorship.match_confidence ? `${Math.round(sponsorship.match_confidence * 100)}%` : "Not available"}</strong></div>
                <div><span>Match method</span><strong>{sponsorship.match_method || "Not available"}</strong></div>
                <div><span>Routes</span><strong>{sponsorship.routes.join(", ") || "Not available"}</strong></div>
              </div>
              <div className="language-note"><CircleAlert size={18} /><p>An absent match does not prove that an organisation cannot sponsor a worker. It means only that VeriFinder could not find a sufficiently confident match in the latest available dataset.</p></div>
            </article>
          </div>
        )}

        {activeTab === "details" && (
          <div className="single-panel-layout">
            <article className="detail-panel wide-panel">
              <div className="panel-title"><div><span className="kicker">Official company record</span><h2>Registration and filing details</h2></div><Building2 size={22} /></div>
              <dl className="detail-list two-column">
                <div><dt>Status</dt><dd>{profile.company_status || "Not available"}</dd></div>
                <div><dt>Company type</dt><dd>{profile.company_type || "Not available"}</dd></div>
                <div><dt>Incorporated</dt><dd>{readableDate(profile.incorporation_date)}</dd></div>
                <div><dt>Next accounts due</dt><dd>{readableDate(profile.accounts_next_due)}</dd></div>
                <div className="full"><dt>Registered office</dt><dd>{profile.registered_office || "Not available"}</dd></div>
                <div className="full"><dt>SIC codes</dt><dd>{profile.sic_codes.join(", ") || "Not available"}</dd></div>
              </dl>
            </article>
          </div>
        )}

        {activeTab === "sources" && (
          <div className="sources-tab">
            <div className="sources-tab-intro"><span className="kicker">Audit trail</span><h2>Sources behind this profile</h2><p>Every verified fact is linked to its official source and freshness metadata.</p></div>
            <div className="source-card-grid">
              <SourceCard source={profile.company_source} />
              {sponsorship.source ? <SourceCard source={sponsorship.source} /> : <article className="source-card unavailable-source"><span className="source-card-icon"><Database size={20} /></span><div><span className="source-org">UK Visas and Immigration</span><h3>Sponsor register not ingested</h3><p>This source is unavailable in the current environment, so no negative conclusion is shown.</p></div></article>}
            </div>
          </div>
        )}

        <p className="disclaimer">Information is based on publicly available sources and should not be treated as legal, financial, immigration or professional advice.</p>
      </div>
    </div>
  );
}
