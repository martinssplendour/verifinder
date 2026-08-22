"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BadgeCheck,
  Building2,
  ChevronLeft,
  CircleAlert,
  Database,
  GraduationCap,
  Landmark,
  LoaderCircle,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { getStudyProvider } from "@/services/api";
import type { StudyProviderDetail } from "@/types";

function yesNo(value: boolean | null) {
  if (value === null) return "Not stated";
  return value ? "Yes" : "No";
}

export default function StudyProviderPage({ params }: { params: Promise<{ recordType: string; recordId: string }> }) {
  const { recordType, recordId } = use(params);
  const [record, setRecord] = useState<StudyProviderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getStudyProvider(recordType, recordId, controller.signal).then(setRecord).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [recordId, recordType]);

  if (error) return <div className="shell profile-error"><CircleAlert size={32} /><h1>Provider record unavailable</h1><p>{error}</p><Link className="button" href="/study">Back to Study Provider Check</Link></div>;
  if (!record) return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading provider record…</div>;

  const isSponsor = record.record_type === "student_sponsor";
  const Icon = isSponsor ? GraduationCap : Landmark;
  return (
    <div className="profile-page study-provider-page">
      <div className="shell">
        <Link className="back-link" href={`/study?q=${encodeURIComponent(record.name)}`}><ChevronLeft size={16} /> Back to Study Provider Check</Link>
        <header className="company-header study-provider-header">
          <span className={`company-monogram ${isSponsor ? "study-sponsor-monogram" : "study-ofs-monogram"}`}><Icon size={30} /></span>
          <div>
            <span className="kicker">{isSponsor ? "UKVI student-sponsor record" : "Office for Students record"}</span>
            <h1>{record.name}</h1>
            <StatusPill status="verified">{isSponsor ? "Listed as a licensed student sponsor" : "Registered with the Office for Students"}</StatusPill>
          </div>
        </header>

        <div className="language-note qualification-identity-note"><CircleAlert size={18} /><p>{record.limitations[0]}</p></div>

        <section className="summary-grid" aria-label="Provider summary">
          <article className="summary-card"><span className="summary-label"><BadgeCheck size={16} /> Register status</span><strong>{record.status || "Listed"}</strong><small>Current imported record</small></article>
          <article className="summary-card"><span className="summary-label"><Building2 size={16} /> Provider type</span><strong className="long-value">{record.provider_type || "Not stated"}</strong><small>{isSponsor ? "UKVI classification" : "OfS registration category"}</small></article>
          <article className="summary-card"><span className="summary-label"><MapPin size={16} /> Location</span><strong className="long-value">{record.town_city || record.postcode || "Not stated"}</strong><small>{record.contact_address || "Official register location"}</small></article>
          <article className="summary-card"><span className="summary-label"><ShieldCheck size={16} /> Cross-check</span><strong>{record.matched_record ? "Exact-name match" : "No exact match"}</strong><small>{record.matched_record ? `Also found in ${record.matched_record.source.organisation}` : "Registers have different coverage"}</small></article>
        </section>

        <div className="sponsor-detail-grid study-provider-detail-grid">
          {isSponsor ? (
            <article className="detail-panel">
              <div className="panel-title"><div><span className="kicker">Sponsorship permission</span><h2>Licensed routes</h2></div><GraduationCap size={21} /></div>
              <div className="sponsor-route-list">{record.routes.map((route) => <div key={route}><BadgeCheck size={16} /> {route}</div>)}</div>
              <dl className="detail-list"><div><dt>Town or city</dt><dd>{record.town_city || "Not stated"}</dd></div><div><dt>Additional locations</dt><dd>{record.additional_locations || "None stated"}</dd></div><div><dt>Immigration compliance</dt><dd>{record.immigration_compliance || "Not stated"}</dd></div></dl>
            </article>
          ) : (
            <article className="detail-panel">
              <div className="panel-title"><div><span className="kicker">Provider details</span><h2>Registration and powers</h2></div><Landmark size={21} /></div>
              <dl className="detail-list"><div><dt>UKPRN</dt><dd>{record.ukprn}</dd></div><div><dt>Registration category</dt><dd>{record.registration_category || "Not stated"}</dd></div><div><dt>Degree-awarding powers</dt><dd>{record.degree_awarding_powers || "Not stated"}</dd></div><div><dt>Right to university title</dt><dd>{yesNo(record.university_title)}</dd></div><div><dt>TEF rating</dt><dd>{record.tef_rating || "Not stated"}</dd></div><div><dt>Access and participation plan</dt><dd>{yesNo(record.access_plan)}</dd></div><div><dt>Specific conditions</dt><dd>{record.specific_conditions.length || "None stated"}</dd></div></dl>
              {record.access_plan_url && <a className="secondary-cta" href={record.access_plan_url} target="_blank" rel="noreferrer">View access plan <ArrowUpRight size={15} /></a>}
            </article>
          )}

          <article className="detail-panel">
            <div className="panel-title"><div><span className="kicker">Evidence</span><h2>Official source</h2></div><Database size={21} /></div>
            <dl className="detail-list"><div><dt>Organisation</dt><dd>{record.source.organisation}</dd></div><div><dt>Dataset</dt><dd>{record.source.dataset}</dd></div><div><dt>Snapshot</dt><dd>{record.source.version}</dd></div>{record.ukprn && <div><dt>UKPRN</dt><dd>{record.ukprn}</dd></div>}{record.website && <div><dt>Website</dt><dd>{record.website}</dd></div>}{record.email && <div><dt>Email</dt><dd>{record.email}</dd></div>}</dl>
            <a className="secondary-cta" href={record.source.official_url} target="_blank" rel="noreferrer">View official register <ArrowUpRight size={15} /></a>
          </article>
        </div>

        {record.matched_record && <article className="detail-panel study-cross-check"><span className="kicker">Exact official-name cross-check</span><h2>{record.matched_record.name}</h2><p>Also found in {record.matched_record.source.dataset}. This connects the evidence for convenience without merging the two legal statuses.</p><Link className="secondary-cta" href={`/study/${record.matched_record.record_type}/${record.matched_record.id}`}>View matched record <ArrowUpRight size={15} /></Link></article>}
        <div className="limitations-note"><CircleAlert size={18} /><div><strong>Read this result carefully</strong><ul>{record.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
        <p className="disclaimer">Public register information only. Not education, accreditation or immigration advice.</p>
      </div>
    </div>
  );
}
