"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Award, BadgeCheck, BookOpen, ChevronLeft, CircleAlert, Clock3, Database, GraduationCap, Languages, LoaderCircle } from "lucide-react";
import { StatusPill } from "@/components/StatusPill";
import { getQualification } from "@/services/api";
import type { QualificationRecordView } from "@/types";

function readableDate(value: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function yesNo(value: boolean | null) {
  if (value === null) return "Not stated";
  return value ? "Yes" : "No";
}

export default function QualificationPage({ params }: { params: Promise<{ recordId: string }> }) {
  const { recordId } = use(params);
  const [record, setRecord] = useState<QualificationRecordView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getQualification(recordId, controller.signal).then(setRecord).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, [recordId]);

  if (error) return <div className="shell profile-error"><CircleAlert size={32} /><h1>Qualification unavailable</h1><p>{error}</p><Link className="button" href="/qualifications">Back to Qualification Check</Link></div>;
  if (!record) return <div className="loading-state page-loading"><LoaderCircle size={22} /> Loading regulated qualification…</div>;

  const isWelsh = record.record_type === "qiw";
  return (
    <div className="profile-page qualification-page">
      <div className="shell">
        <Link className="back-link" href={`/qualifications?q=${encodeURIComponent(record.title)}`}><ChevronLeft size={16} /> Back to Qualification Check</Link>
        <header className="company-header qualification-header">
          <span className={`company-monogram qualification-monogram ${isWelsh ? "qiw-monogram" : ""}`}><Award size={30} /></span>
          <div><span className="kicker">{record.regulator} record · {record.jurisdiction}</span><h1>{record.title}</h1><StatusPill status="verified">Found on an official regulated qualifications register</StatusPill></div>
        </header>

        <div className="language-note qualification-identity-note"><CircleAlert size={18} /><p>Regulated status does not establish university-degree equivalence, immigration eligibility or acceptance by a particular employer or institution.</p></div>

        <section className="summary-grid qualification-summary-grid" aria-label="Qualification summary">
          <article className="summary-card"><span className="summary-label"><BadgeCheck size={16} /> Register status</span><strong>{record.status || "Unavailable"}</strong><small>{record.jurisdiction}</small></article>
          <article className="summary-card"><span className="summary-label"><GraduationCap size={16} /> Level</span><strong>{record.level || "Unavailable"}</strong><small>{record.qualification_type || "Type unavailable"}</small></article>
          <article className="summary-card"><span className="summary-label"><Award size={16} /> Awarding organisation</span><strong className="long-value">{record.awarding_organisation_name}</strong><small>{record.awarding_organisation_acronym || record.qualification_number}</small></article>
          {isWelsh ? <article className="summary-card"><span className="summary-label"><Languages size={16} /> Languages</span><strong>{record.languages.join(", ") || "Not stated"}</strong><small>{record.review_type || "Review type unavailable"}</small></article> : <article className="summary-card"><span className="summary-label"><BookOpen size={16} /> Linked units</span><strong>{record.unit_count}</strong><small>{record.unit_count === 1 ? "Official unit mapping" : "Official unit mappings"}</small></article>}
        </section>

        <div className="sponsor-detail-grid qualification-detail-grid">
          <article className="detail-panel">
            <div className="panel-title"><div><span className="kicker">Qualification details</span><h2>Official classification</h2></div><GraduationCap size={21} /></div>
            <dl className="detail-list">
              <div><dt>Qualification number</dt><dd>{record.qualification_number}</dd></div>
              {record.approval_number && <div><dt>Approval / designation number</dt><dd>{record.approval_number}</dd></div>}
              <div><dt>Type</dt><dd>{record.qualification_type || "Not stated"}</dd></div>
              {!isWelsh && <div><dt>Subject area</dt><dd>{record.sector_subject_area || "Not stated"}</dd></div>}
              {!isWelsh && <div><dt>Total qualification time</dt><dd>{record.total_qualification_time === null ? "Not stated" : `${record.total_qualification_time} hours`}</dd></div>}
              {!isWelsh && <div><dt>Guided learning</dt><dd>{record.guided_learning_hours === null ? "Not stated" : `${record.guided_learning_hours} hours`}</dd></div>}
              {!isWelsh && <div><dt>Credits</dt><dd>{record.total_credits ?? "Not stated"}</dd></div>}
              {!isWelsh && <div><dt>Grading</dt><dd>{record.grading_type || "Not stated"}</dd></div>}
              {isWelsh ? <div><dt>Eligible for public funding</dt><dd>{yesNo(record.eligible_public_funding)}</dd></div> : <><div><dt>Offered in England</dt><dd>{yesNo(record.offered_in_england)}</dd></div><div><dt>Offered in Northern Ireland</dt><dd>{yesNo(record.offered_in_northern_ireland)}</dd></div></>}
            </dl>
            {record.specification_url && <a className="secondary-cta" href={record.specification_url} target="_blank" rel="noreferrer">View awarding-body specification <ArrowUpRight size={15} /></a>}
          </article>

          <article className="detail-panel"><div className="panel-title"><div><span className="kicker">Dates and provenance</span><h2>Register record</h2></div><Database size={21} /></div><dl className="detail-list">{!isWelsh && <div><dt>Regulation began</dt><dd>{readableDate(record.regulation_start_date)}</dd></div>}<div><dt>Operational start</dt><dd>{readableDate(record.operational_start_date)}</dd></div><div><dt>Operational end</dt><dd>{readableDate(record.operational_end_date)}</dd></div><div><dt>Certification end</dt><dd>{readableDate(record.certification_end_date)}</dd></div><div><dt>Regulator</dt><dd>{record.regulator}</dd></div><div><dt>Source</dt><dd>{record.source.organisation}</dd></div><div><dt>Snapshot</dt><dd>{record.source.version}</dd></div><div><dt>Retrieved</dt><dd>{readableDate(record.source.retrieved_at)}</dd></div></dl><a className="secondary-cta" href={record.source.official_url} target="_blank" rel="noreferrer">View official register <ArrowUpRight size={15} /></a></article>
        </div>

        {!isWelsh && (
          <article className="detail-panel qualification-units-panel">
            <div className="panel-title"><div><span className="kicker">Qualification expansion</span><h2>Linked units</h2></div><BookOpen size={21} /></div>
            {record.units.length ? <div className="qualification-unit-list">{record.units.map((unit, index) => <div key={`${unit.unit_reference || unit.title}-${index}`}><div><strong>{unit.title}</strong><small>{unit.unit_reference || "No public unit reference"}</small></div><span>{[unit.level, unit.credit_value !== null ? `${unit.credit_value} credits` : null, unit.guided_learning_hours !== null ? `${unit.guided_learning_hours} GLH` : null].filter(Boolean).join(" · ") || "Details not stated"}</span></div>)}</div> : <div className="inline-empty"><strong>No units linked in the current Ofqual mapping</strong><p>Some qualifications do not publish unit mappings in the bulk extract.</p></div>}
            {record.unit_count > record.units.length && <p className="panel-helper">Showing the first {record.units.length} of {record.unit_count} linked units.</p>}
          </article>
        )}
        <p className="disclaimer">Public register information only. Not education, employment, equivalence or immigration advice.</p>
      </div>
    </div>
  );
}
