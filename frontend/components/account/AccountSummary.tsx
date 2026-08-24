"use client";

import type { Session } from "@supabase/supabase-js";
import Link from "next/link";
import { BadgeCheck, CreditCard, LogOut, ShieldCheck, Sparkles } from "lucide-react";
import type { AccountStatus } from "@/types";

type Props = {
  session: Session;
  account: AccountStatus | null;
  working: boolean;
  onOpenLibrary: () => void;
  onOpenPlans: () => void;
  onManageBilling: () => void;
  onSignOut: () => void;
};

export function AccountSummary({ session, account, working, onOpenLibrary, onOpenPlans, onManageBilling, onSignOut }: Props) {
  const isAdmin = account?.is_admin === true;
  return (
    <div className="account-summary">
      <div className="account-identity"><span><BadgeCheck size={20} /></span><div><small>Signed in as</small><strong>{session.user.email}</strong></div><em>{isAdmin ? "admin" : account?.entitlements.tier || "free"}</em></div>
      <div className="account-allowances"><div><strong>Ask</strong><span>{isAdmin ? "Unrestricted admin access" : account?.entitlements.ask.allowed ? `Available · ${account.entitlements.ask.word_limit || 20}-word cap` : "Free allowance used"}</span></div><div><strong>Ask coins</strong><span>{isAdmin ? "Not required" : `${account?.coin_balance ?? 0} message${account?.coin_balance === 1 ? "" : "s"} available`}</span></div><div><strong>Planner</strong><span>{isAdmin ? "Unlimited" : account?.entitlements.planner.allowed ? "Available" : "Free allowance used"}</span></div><div><strong>Reports</strong><span>{account?.entitlements.report_download.allowed ? "Private PDFs enabled" : "£4.99 or upgrade"}</span></div><div><strong>Watchlists</strong><span>{account?.entitlements.watchlists.allowed ? "Change alerts enabled" : "Plus required"}</span></div></div>
      <div className="account-buttons">{isAdmin && <Link className="button" href="/admin"><ShieldCheck size={15} />Admin operations</Link>}<button className={isAdmin ? "button button-secondary" : "button"} type="button" onClick={onOpenLibrary}><BadgeCheck size={15} />Saved records</button>{!isAdmin && <button className="button button-secondary" type="button" onClick={onOpenPlans}><Sparkles size={15} />View plans</button>}{account?.has_billing_account && <button className="button button-secondary" type="button" disabled={working} onClick={onManageBilling}><CreditCard size={15} />Manage billing</button>}<button className="text-button" type="button" onClick={onSignOut}><LogOut size={14} />Sign out</button></div>
    </div>
  );
}
