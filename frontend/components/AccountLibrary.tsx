"use client";

import { useCallback, useEffect, useState } from "react";
import { Bell, BellOff, Download, FileText, LoaderCircle, Trash2 } from "lucide-react";
import {
  deleteSavedReport,
  getSavedReportDownload,
  getSavedReports,
  getWatchlist,
  getWatchlistAlerts,
  removeWatchlistEntry,
  updateWatchlistEntry,
} from "@/services/api";
import { downloadSignedReport } from "@/services/report";
import type { SavedReport, WatchlistAlert, WatchlistEntry } from "@/types";


type LibraryTab = "reports" | "watchlist" | "alerts";

function readableDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

export function AccountLibrary({ onError }: { onError: (message: string | null) => void }) {
  const [tab, setTab] = useState<LibraryTab>("reports");
  const [reports, setReports] = useState<SavedReport[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const [nextReports, nextWatchlist, nextAlerts] = await Promise.all([
        getSavedReports(), getWatchlist(), getWatchlistAlerts(),
      ]);
      setReports(nextReports);
      setWatchlist(nextWatchlist);
      setAlerts(nextAlerts);
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => { queueMicrotask(() => void refresh()); }, [refresh]);

  async function download(report: SavedReport) {
    setWorking(`report-${report.id}`);
    onError(null);
    try {
      const result = await getSavedReportDownload(report.id);
      downloadSignedReport(result.url);
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setWorking(null);
    }
  }

  async function removeReport(report: SavedReport) {
    if (!window.confirm(`Delete “${report.title}” from your private report library?`)) return;
    setWorking(`report-${report.id}`);
    try {
      await deleteSavedReport(report.id);
      setReports((current) => current.filter((item) => item.id !== report.id));
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setWorking(null);
    }
  }

  async function toggleAlerts(entry: WatchlistEntry) {
    setWorking(`watch-${entry.id}`);
    try {
      const updated = await updateWatchlistEntry(entry.id, !entry.notifications_enabled);
      setWatchlist((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setWorking(null);
    }
  }

  async function removeWatch(entry: WatchlistEntry) {
    setWorking(`watch-${entry.id}`);
    try {
      await removeWatchlistEntry(entry.id);
      setWatchlist((current) => current.filter((item) => item.id !== entry.id));
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setWorking(null);
    }
  }

  return (
    <div className="account-library">
      <nav aria-label="Saved account records">
        <button className={tab === "reports" ? "is-active" : ""} type="button" onClick={() => setTab("reports")}>Reports <span>{reports.length}</span></button>
        <button className={tab === "watchlist" ? "is-active" : ""} type="button" onClick={() => setTab("watchlist")}>Watchlist <span>{watchlist.length}</span></button>
        <button className={tab === "alerts" ? "is-active" : ""} type="button" onClick={() => setTab("alerts")}>Alerts <span>{alerts.length}</span></button>
      </nav>
      {loading ? <div className="account-library-loading"><LoaderCircle className="spin" size={18} />Loading your private records…</div> : tab === "reports" ? (
        reports.length ? <div className="library-list">{reports.map((report) => <article key={report.id}><span><FileText size={17} /></span><div><strong>{report.title}</strong><small>{readableDate(report.created_at)} · {report.provenance_count} official sources · {(report.size_bytes / 1024).toFixed(0)} KB</small></div><button type="button" disabled={working === `report-${report.id}`} onClick={() => void download(report)} aria-label={`Download ${report.title}`}><Download size={15} /></button><button className="danger-action" type="button" disabled={working === `report-${report.id}`} onClick={() => void removeReport(report)} aria-label={`Delete ${report.title}`}><Trash2 size={15} /></button></article>)}</div> : <div className="library-empty"><FileText size={21} /><strong>No saved reports yet</strong><p>Paid PDFs you generate are stored privately here.</p></div>
      ) : tab === "watchlist" ? (
        watchlist.length ? <div className="library-list">{watchlist.map((entry) => <article key={entry.id}><span>{entry.notifications_enabled ? <Bell size={17} /> : <BellOff size={17} />}</span><div><strong>{entry.label || entry.entity_id}</strong><small>{entry.entity_type} · added {readableDate(entry.created_at)}</small></div><button type="button" disabled={working === `watch-${entry.id}`} onClick={() => void toggleAlerts(entry)} aria-label={`${entry.notifications_enabled ? "Disable" : "Enable"} alerts for ${entry.label || entry.entity_id}`}>{entry.notifications_enabled ? <BellOff size={15} /> : <Bell size={15} />}</button><button className="danger-action" type="button" disabled={working === `watch-${entry.id}`} onClick={() => void removeWatch(entry)} aria-label={`Remove ${entry.label || entry.entity_id} from watchlist`}><Trash2 size={15} /></button></article>)}</div> : <div className="library-empty"><Bell size={21} /><strong>Your watchlist is empty</strong><p>Use Watch on a company or area result to retain it.</p></div>
      ) : alerts.length ? <div className="alert-list">{alerts.map((alert) => <article key={alert.id}><span>{alert.entity_type}</span><strong>{alert.summary}</strong><small>{readableDate(alert.created_at)} · email {alert.email_status.replaceAll("_", " ")}</small></article>)}</div> : <div className="library-empty"><Bell size={21} /><strong>No changes detected</strong><p>New official-record changes will appear after scheduled refreshes.</p></div>}
    </div>
  );
}
