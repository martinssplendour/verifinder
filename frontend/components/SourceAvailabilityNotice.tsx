import { CircleAlert } from "lucide-react";

export function SourceAvailabilityNotice({ compact = false, sponsorLive = false }: { compact?: boolean; sponsorLive?: boolean }) {
  return (
    <div className={`source-notice ${compact ? "source-notice-compact" : ""}`} role="status">
      <CircleAlert size={18} aria-hidden="true" />
      <p>
        <strong>Companies House is not connected.</strong>{" "}
        {sponsorLive
          ? "The results below come from the current official Home Office sponsor register. Legal-company results will appear after the Companies House API key is configured."
          : "Configure the Companies House API key to enable legal-company records."}
      </p>
    </div>
  );
}
