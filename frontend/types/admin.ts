import type { DataMode } from "./common";

export interface SourceRegistryItem {
  id: string;
  organisation: string;
  name: string;
  official_url: string;
  source_type: string;
  refresh_frequency: string;
  health: string;
  last_successful_retrieval: string | null;
  integration_status: "connected" | "configured" | "not_configured";
}

export interface IngestionRun {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  records_processed: number;
  records_added: number;
  records_removed: number;
  records_changed: number;
  error_message: string | null;
}

export interface AdminSummary {
  data_mode: DataMode;
  sources: { total: number; healthy: number; attention: number };
  ingestion_runs: IngestionRun[];
  unresolved_matches: number;
  failed_imports: number;
  message: string;
  generated_at: string;
}
