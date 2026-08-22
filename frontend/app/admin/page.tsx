"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  GitCompareArrows,
  LoaderCircle,
  RefreshCw,
  ServerCog,
} from "lucide-react";
import { getAdminSummary } from "@/services/api";
import type { AdminSummary } from "@/types";

function number(value: number) {
  return new Intl.NumberFormat("en-GB").format(value);
}

function dateTime(value: string | null) {
  if (!value) return "In progress";
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function AdminPage() {
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getAdminSummary(controller.signal).then(setSummary).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, []);

  return (
    <div className="shell admin-page">
      <div className="admin-heading">
        <div><span className="kicker">Internal operations</span><h1>Data operations</h1><p>Monitor source health, imports and uncertain entity matches.</p></div>
        <button className="button" disabled><RefreshCw size={16} /> Run sponsor import</button>
      </div>

      {error ? (
        <div className="admin-notice"><AlertTriangle size={19} /><div><strong>Operations data unavailable</strong><p>{error}</p></div></div>
      ) : !summary ? (
        <div className="loading-state"><LoaderCircle size={22} /> Loading data operations…</div>
      ) : (
        <>
          <div className={`admin-notice ${summary.sources.healthy > 0 ? "admin-notice-success" : ""}`}>
            {summary.sources.healthy > 0 ? <CheckCircle2 size={19} /> : <AlertTriangle size={19} />}
            <div><strong>{summary.message}</strong><p>Import activity and verified record counts are shown below.</p></div>
          </div>
          <section className="admin-metrics">
            <article><span><Database size={18} /></span><div><small>Registered sources</small><strong>{summary.sources.total}</strong></div></article>
            <article><span><CheckCircle2 size={18} /></span><div><small>Healthy sources</small><strong>{summary.sources.healthy}</strong></div></article>
            <article><span><ServerCog size={18} /></span><div><small>Ingestion runs</small><strong>{summary.ingestion_runs.length}</strong></div></article>
            <article><span><GitCompareArrows size={18} /></span><div><small>Unresolved matches</small><strong>{summary.unresolved_matches}</strong></div></article>
          </section>
          <section className="admin-table-panel">
            <div className="section-heading-row"><div><span className="kicker">Pipeline activity</span><h2>Recent ingestion runs</h2></div><Link href="/sources">View source registry <ArrowRight size={15} /></Link></div>
            {summary.ingestion_runs.length ? (
              <div className="ingestion-list">
                {summary.ingestion_runs.map((run) => (
                  <article key={run.id}>
                    <span className={`run-status run-${run.status}`}>{run.status}</span>
                    <div><strong>Home Office worker sponsors</strong><small>{dateTime(run.finished_at)}</small></div>
                    <dl>
                      <div><dt>Processed</dt><dd>{number(run.records_processed)}</dd></div>
                      <div><dt>Added</dt><dd>{number(run.records_added)}</dd></div>
                      <div><dt>Removed</dt><dd>{number(run.records_removed)}</dd></div>
                      <div><dt>Changed</dt><dd>{number(run.records_changed)}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            ) : (
              <div className="admin-empty"><ServerCog size={25} /><strong>No ingestion runs yet</strong><p>Status, record counts and errors will appear here after the first manual import.</p></div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

