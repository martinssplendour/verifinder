"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BadgeCheck,
  Building2,
  ChevronLeft,
  CircleAlert,
  FileText,
  Landmark,
  LoaderCircle,
  MapPin,
  Search,
  Share2,
} from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { WatchButton } from "@/components/WatchButton";
import { getCompany } from "@/services/api";
import type { CompanyProfile, SourceAttribution } from "@/types";

type Tab = "overview" | "details" | "sources";

function readableDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function SourceCard({ source }: { source: SourceAttribution }) {
  return (
    <article className="source-card">
      <span className="source-card-icon"><Landmark size={20} /></span>
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
    return <div className="shell profile-error"><CircleAlert size={32} /><h1>Company unavailable</h1><p>{error}</p><Link className="button" href="/companies">Back to company check</Link></div>;
  }
  if (!profile) {
    return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading Companies House record…</div>;
  }

  const companyActive = profile.company_status === "active";
  return (
    <div className="profile-page">
      <div className="shell">
        <div className="profile-topline">
          <Link className="back-link" href={`/companies?q=${encodeURIComponent(profile.company_name)}`}><ChevronLeft size={16} /> Back to company check</Link>
          <div className="profile-actions">
            <WatchButton entityType="company" entityId={profile.company_number} label={profile.company_name} />
            <button className="icon-button" type="button" onClick={share}><Share2 size={17} /> {copied ? "Copied" : "Share"}</button>
          </div>
        </div>
        <header className="company-header">
          <span className="company-monogram" aria-hidden="true">{profile.company_name.slice(0, 1)}</span>
          <div>
            <span className="kicker">Companies House company record</span>
            <h1>{profile.company_name}</h1>
            <StatusPill status={profile.verified_status}><span>Retrieved from Companies House</span></StatusPill>
            <p>Company number: <strong>{profile.company_number}</strong> <span>·</span> Incorporated: <strong>{readableDate(profile.incorporation_date)}</strong></p>
          </div>
        </header>

        <div className="language-note company-source-boundary">
          <CircleAlert size={18} />
          <p>This page contains Companies House data only. It does not state whether this company offers visa sponsorship and it is not linked to a sponsor-register organisation.</p>
        </div>

        <section className="summary-grid" aria-label="Companies House summary">
          <article className="summary-card">
            <span className="summary-label"><Building2 size={16} /> Company status</span>
            <strong className={companyActive ? "positive-text" : ""}>{profile.company_status || "Unavailable"}</strong>
            <small><BadgeCheck size={13} /> {profile.company_source.organisation}</small>
          </article>
          <article className="summary-card">
            <span className="summary-label"><MapPin size={16} /> Registered office</span>
            <strong className="address-value">{profile.registered_office || "Not available"}</strong>
            <small>{profile.postcode || "Postcode unavailable"}</small>
          </article>
          <article className="summary-card">
            <span className="summary-label"><FileText size={16} /> Company type</span>
            <strong>{profile.company_type || "Not available"}</strong>
            <small>Companies House profile value</small>
          </article>
          <article className="summary-card">
            <span className="summary-label"><FileText size={16} /> Next accounts due</span>
            <strong>{readableDate(profile.accounts_next_due)}</strong>
            <small>Companies House filing data</small>
          </article>
        </section>

        <nav className="profile-tabs" aria-label="Company profile sections">
          {(["overview", "details", "sources"] as Tab[]).map((tab) => (
            <button key={tab} className={activeTab === tab ? "is-active" : ""} onClick={() => setActiveTab(tab)} type="button">
              {tab === "details" ? "Company details" : tab[0].toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>

        {activeTab === "overview" && (
          <div className="profile-content-grid company-only-content-grid">
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
            <article className="detail-panel separate-sponsor-panel">
              <div className="panel-title"><div><span className="kicker">Separate source</span><h2>Need a sponsorship check?</h2></div><Search size={21} /></div>
              <p>Run an independent exact-name lookup against the stored Home Office worker sponsor list. No result from that list will be attached to this Companies House profile.</p>
              <Link className="button button-secondary" href={`/sponsors?q=${encodeURIComponent(profile.company_name)}`}><Search size={16} /> Open sponsorship check</Link>
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
            <div className="sources-tab-intro"><span className="kicker">Audit trail</span><h2>Source behind this profile</h2><p>Only the Companies House source is used on this page.</p></div>
            <div className="source-card-grid company-source-card-grid"><SourceCard source={profile.company_source} /></div>
          </div>
        )}

        <p className="disclaimer">Information is based on the Companies House API and should not be treated as legal, financial, immigration or professional advice.</p>
      </div>
    </div>
  );
}
