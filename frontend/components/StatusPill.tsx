import { AlertTriangle, BadgeCheck, CircleHelp, Database, SearchX } from "lucide-react";
import type { VerificationStatus } from "@/types";

const META: Record<VerificationStatus, { icon: typeof BadgeCheck; className: string }> = {
  verified: { icon: BadgeCheck, className: "status-positive" },
  match_found: { icon: BadgeCheck, className: "status-positive" },
  possible_match: { icon: CircleHelp, className: "status-warning" },
  no_match: { icon: SearchX, className: "status-neutral" },
  data_unavailable: { icon: Database, className: "status-neutral" },
  stale: { icon: AlertTriangle, className: "status-warning" },
  unknown: { icon: CircleHelp, className: "status-neutral" },
};

export function StatusPill({ status, children }: { status: VerificationStatus; children: React.ReactNode }) {
  const { icon: Icon, className } = META[status];
  return (
    <span className={`status-pill ${className}`}>
      <Icon size={14} aria-hidden="true" />
      {children}
    </span>
  );
}

