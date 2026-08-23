export interface SavedReport {
  id: string;
  source_report_id: string;
  report_type: string;
  title: string;
  mime_type: string;
  size_bytes: number;
  provenance_count: number;
  created_at: string;
}

export interface SavedReportReady {
  report: SavedReport;
  download_url: string;
  expires_at: string;
}
