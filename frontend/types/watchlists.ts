export interface WatchlistEntry {
  id: number;
  entity_type: string;
  entity_id: string;
  label: string | null;
  notifications_enabled: boolean;
  created_at: string;
}

export interface WatchlistAlert {
  id: number;
  entity_type: string;
  entity_id: string;
  summary: string;
  detail: Record<string, unknown> | null;
  email_status: string;
  created_at: string;
}
