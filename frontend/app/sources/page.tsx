"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Database, Landmark, LoaderCircle, ShieldCheck } from "lucide-react";
import { getSources } from "@/services/api";
import type { SourceRegistryItem } from "@/types";

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceRegistryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getSources(controller.signal).then(setSources).catch((requestError) => {
      if (requestError.name !== "AbortError") setError(requestError.message);
    });
    return () => controller.abort();
  }, []);
  return (
    <div className="shell content-page">
      <div className="content-hero">
        <span className="eyebrow"><Database size={15} /> Source registry</span>
        <h1>Know where every answer came from.</h1>
        <p>VeriFinder tracks the organisation, dataset, official location and integration health behind each supported fact.</p>
      </div>
      {error ? <div className="empty-state error-state"><h2>Source registry unavailable</h2><p>{error}</p></div> : !sources ? <div className="loading-state"><LoaderCircle size={22} /> Loading source registry…</div> : (
        <div className="registry-list">
          {sources.map((source) => (
            <article className="registry-card" key={source.id}>
              <span className="registry-icon">{source.id === "companies-house" ? <Landmark size={23} /> : <ShieldCheck size={23} />}</span>
              <div className="registry-main">
                <span className="kicker">{source.organisation}</span>
                <h2>{source.name}</h2>
                <p>{source.refresh_frequency}</p>
              </div>
              <dl>
                <div><dt>Format</dt><dd>{source.source_type}</dd></div>
                <div><dt>Health</dt><dd className={`source-health health-${source.health}`}>{source.health.replaceAll("_", " ")}</dd></div>
                <div><dt>Integration</dt><dd>{source.integration_status.replaceAll("_", " ")}</dd></div>
              </dl>
              <a href={source.official_url} target="_blank" rel="noreferrer">Official source <ArrowUpRight size={14} /></a>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

