"use client";

/* eslint-disable react/no-unescaped-entities */

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Building2, CalendarDays, ChevronLeft, CircleAlert, Database, GraduationCap, LoaderCircle, MapPin, Phone, School, ShieldCheck, Users } from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { getSchool } from "@/services/api";
import type { SchoolDetail } from "@/types";

const oeifLabels: Record<string, string> = { "1": "Outstanding", "2": "Good", "3": "Requires improvement", "4": "Inadequate" };

function readableDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function gradeClass(value: string | null) {
  if (!value) return "";
  const lower = value.toLowerCase();
  if (["strong standard", "met", "outstanding", "good"].some((term) => lower.includes(term))) return "rating-good";
  if (["causing concern", "urgent improvement", "not met", "inadequate"].some((term) => lower.includes(term))) return "rating-poor";
  return "";
}

const newFrameworkJudgements: { key: keyof SchoolDetail["ofsted"]; label: string }[] = [
  { key: "safeguarding_standards", label: "Safeguarding standards" },
  { key: "inclusion", label: "Inclusion" },
  { key: "curriculum_and_teaching", label: "Curriculum and teaching" },
  { key: "achievement", label: "Achievement" },
  { key: "attendance_and_behaviour", label: "Attendance and behaviour" },
  { key: "personal_development_and_wellbeing", label: "Personal development and wellbeing" },
  { key: "early_years", label: "Early years" },
  { key: "post_16_provision", label: "Post-16 provision" },
  { key: "leadership_and_governance", label: "Leadership and governance" },
];

export default function SchoolDetailPage({ params }: { params: Promise<{ urn: string }> }) {
  const { urn } = use(params);
  const [record, setRecord] = useState<SchoolDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getSchool(urn, controller.signal).then(setRecord).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [urn]);
  if (error) return <div className="shell profile-error"><CircleAlert size={32} /><h1>School record unavailable</h1><p>{error}</p><Link className="button" href="/school">Back to School Check</Link></div>;
  if (!record) return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading school record…</div>;
  const ofsted = record.ofsted;
  const hasFullInspection = Boolean(ofsted.full_inspection_start_date);
  const hasOeif = Boolean(ofsted.oeif_overall_effectiveness);
  const hasUngraded = Boolean(ofsted.ungraded_overall_outcome);
  return <div className="profile-page school-detail-page"><div className="shell">
    <Link className="back-link" href={`/school?q=${encodeURIComponent(record.postcode || record.establishment_name)}`}><ChevronLeft size={16} /> Back to School Check</Link>
    <header className="company-header school-header"><span className="company-monogram school-monogram"><School size={30} /></span><div><span className="kicker">GIAS establishment record · URN {record.urn}</span><h1>{record.establishment_name}</h1><StatusPill status="verified">{record.status_name || "Status unavailable"}</StatusPill></div></header>
    <div className="language-note school-identity-note"><CircleAlert size={18} /><p>This page combines two separate official registers, matched by exact URN. GIAS establishment details and the Ofsted inspection outcome are not merged into one status.</p></div>
    <section className="summary-grid school-summary-grid" aria-label="School summary">
      <article className="summary-card"><span className="summary-label"><GraduationCap size={16} /> Type / phase</span><strong>{record.type_name || "Unavailable"}</strong><small>{record.phase_name || "Phase unavailable"}</small></article>
      <article className="summary-card"><span className="summary-label"><Users size={16} /> Pupils on roll</span><strong>{record.number_of_pupils ?? "Unavailable"}</strong><small>{record.school_capacity ? `Capacity ${record.school_capacity}` : "Capacity unavailable"}</small></article>
      <article className="summary-card"><span className="summary-label"><MapPin size={16} /> Postcode</span><strong>{record.postcode || "Unavailable"}</strong><small>{[record.town, record.la_name].filter(Boolean).join(", ")}</small></article>
      <article className="summary-card"><span className="summary-label"><ShieldCheck size={16} /> Safeguarding standards</span><strong>{ofsted.safeguarding_standards || (ofsted.oeif_safeguarding_effective === true ? "Effective (legacy framework)" : ofsted.oeif_safeguarding_effective === false ? "Not effective (legacy framework)" : "Unavailable")}</strong><small>{ofsted.status === "matched" ? "From Ofsted" : "Ofsted not matched"}</small></article>
    </section>
    <div className="school-detail-grid property-detail-grid">
      <article className="detail-panel"><div className="panel-title"><div><span className="kicker">GIAS establishment details</span><h2>Register record</h2></div><Building2 size={21} /></div><dl className="detail-list"><div><dt>Establishment type</dt><dd>{record.type_name || "Unavailable"}</dd></div><div><dt>Type group</dt><dd>{record.type_group_name || "Unavailable"}</dd></div><div><dt>Local authority</dt><dd>{record.la_name || "Unavailable"}</dd></div><div><dt>Religious character</dt><dd>{record.religious_character_name || "Unavailable"}</dd></div><div><dt>Gender</dt><dd>{record.gender_name || "Unavailable"}</dd></div><div><dt>Age range</dt><dd>{record.statutory_low_age !== null && record.statutory_high_age !== null ? `${record.statutory_low_age}–${record.statutory_high_age}` : "Unavailable"}</dd></div><div><dt>Opened</dt><dd>{readableDate(record.open_date)}</dd></div>{record.close_date && <div><dt>Closed</dt><dd>{readableDate(record.close_date)}</dd></div>}</dl></article>

      <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Contact and location</span><h2>Address and contact</h2></div><Phone size={21} /></div><dl className="detail-list"><div><dt>Address</dt><dd>{[record.street, record.locality, record.town, record.county_name, record.postcode].filter(Boolean).join(", ") || "Unavailable"}</dd></div><div><dt>Telephone</dt><dd>{record.telephone || "Unavailable"}</dd></div><div><dt>Website</dt><dd>{record.website || "Unavailable"}</dd></div><div><dt>Head / principal</dt><dd>{[record.head_first_name, record.head_last_name].filter(Boolean).join(" ") || "Unavailable"}</dd></div><div><dt>Region</dt><dd>{record.region_name || "Unavailable"}</dd></div></dl></article>

      <article className="detail-panel ofsted-detail-panel"><div className="panel-title"><div><span className="kicker">Ofsted · current framework</span><h2>Latest full inspection</h2></div><ShieldCheck size={21} /></div>
        {ofsted.status === "data_unavailable" ? <p className="panel-helper">{ofsted.message}</p> : !hasFullInspection ? <div className="inline-empty"><strong>No current-framework inspection recorded</strong><p>This school's most recent graded inspection may predate the 2025 framework — see the legacy result below.</p></div> : <>
          <p className="panel-helper">Inspected {readableDate(ofsted.full_inspection_start_date)} · Published {readableDate(ofsted.full_inspection_publication_date)}</p>
          <div className="constraint-list ofsted-judgement-list">{newFrameworkJudgements.map(({ key, label }) => { const value = ofsted[key] as string | null; return value && value !== "Not applicable" ? <div key={key}><span>{label}</span><strong className={gradeClass(value)}>{value}</strong></div> : null; })}</div>
        </>}
      </article>

      <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Ofsted · earlier framework</span><h2>Legacy and ungraded results</h2></div><Database size={21} /></div>
        {!hasOeif && !hasUngraded ? <p className="panel-helper">No legacy-framework or ungraded inspection is recorded for this URN.</p> : <dl className="detail-list">
          {hasOeif && <><div><dt>Overall effectiveness (legacy)</dt><dd>{oeifLabels[ofsted.oeif_overall_effectiveness || ""] || ofsted.oeif_overall_effectiveness}</dd></div><div><dt>Inspected</dt><dd>{readableDate(ofsted.oeif_start_date)}</dd></div></>}
          {hasUngraded && <><div><dt>Latest ungraded outcome</dt><dd>{ofsted.ungraded_overall_outcome}</dd></div><div><dt>Ungraded inspection date</dt><dd>{readableDate(ofsted.ungraded_inspection_date)}</dd></div></>}
        </dl>}
      </article>

      <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Data provenance</span><h2>Official snapshots</h2></div><CalendarDays size={21} /></div><dl className="detail-list"><div><dt>GIAS publisher</dt><dd>{record.source.organisation}</dd></div><div><dt>GIAS version</dt><dd>{record.source.version}</dd></div><div><dt>GIAS retrieved</dt><dd>{readableDate(record.source.retrieved_at)}</dd></div>{ofsted.source && <><div><dt>Ofsted publisher</dt><dd>{ofsted.source.organisation}</dd></div><div><dt>Ofsted version</dt><dd>{ofsted.source.version}</dd></div></>}</dl><a className="secondary-cta" href={record.source.official_url} target="_blank" rel="noreferrer">View GIAS source <ArrowUpRight size={15} /></a></article>
    </div>
    <div className="limitations-note"><CircleAlert size={18} /><div><strong>Coverage and matching limits</strong><ul>{record.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
  </div></div>;
}
