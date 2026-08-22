"use client";

import { useEffect, useState } from "react";
import { Heart, LoaderCircle } from "lucide-react";
import { addWatchlistEntry, getWatchlist, removeWatchlistEntry } from "@/services/api";
import { useAccount } from "@/components/Account";


export function WatchButton({ entityType, entityId, label }: { entityType: "company" | "area"; entityId: string; label: string }) {
  const { session, account, openAccount } = useAccount();
  const [entryId, setEntryId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) { queueMicrotask(() => setEntryId(null)); return; }
    const controller = new AbortController();
    getWatchlist(controller.signal).then((entries) => {
      const match = entries.find((entry) => entry.entity_type === entityType && entry.entity_id.replaceAll(" ", "").toLowerCase() === entityId.replaceAll(" ", "").toLowerCase());
      setEntryId(match?.id || null);
    }).catch(() => undefined);
    return () => controller.abort();
  }, [session, entityType, entityId]);

  async function toggle() {
    setError(null);
    if (!session) { openAccount("sign-in"); return; }
    if (!account?.entitlements.watchlists.allowed) { openAccount("plans"); return; }
    setLoading(true);
    try {
      if (entryId) {
        await removeWatchlistEntry(entryId);
        setEntryId(null);
      } else {
        const entry = await addWatchlistEntry(entityType, entityId, label);
        setEntryId(entry.id);
      }
    } catch (requestError) {
      setError((requestError as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <span className="watch-action-wrap">
      <button className={`icon-button ${entryId ? "is-watching" : ""}`} type="button" disabled={loading} onClick={() => void toggle()} aria-pressed={Boolean(entryId)} title={entryId ? "Remove from watchlist" : "Watch for official-record changes"}>
        {loading ? <LoaderCircle className="spin" size={17} /> : <Heart size={17} fill={entryId ? "currentColor" : "none"} />} {entryId ? "Watching" : "Watch"}
      </button>
      {error && <small role="alert">{error}</small>}
    </span>
  );
}
