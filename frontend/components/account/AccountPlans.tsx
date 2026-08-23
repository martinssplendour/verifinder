"use client";

import { CreditCard, Sparkles, Check } from "lucide-react";
import type { AccountStatus, SubscriptionTier } from "@/types";

type BillingCadence = "monthly" | "annual";

type Props = {
  billingCadence: BillingCadence;
  onCadenceChange: (cadence: BillingCadence) => void;
  working: boolean;
  account: AccountStatus | null;
  isSignedIn: boolean;
  onStartCheckout: (tier: Exclude<SubscriptionTier, "free">) => void;
  onRequestSignIn: () => void;
};

export function AccountPlans({ billingCadence, onCadenceChange, working, account, isSignedIn, onStartCheckout, onRequestSignIn }: Props) {
  return (
    <div className="account-plans">
      <div className="billing-cadence" role="group" aria-label="Subscription billing cadence">
        <button type="button" className={billingCadence === "monthly" ? "is-selected" : ""} aria-pressed={billingCadence === "monthly"} onClick={() => onCadenceChange("monthly")}>Monthly</button>
        <button type="button" className={billingCadence === "annual" ? "is-selected" : ""} aria-pressed={billingCadence === "annual"} onClick={() => onCadenceChange("annual")}>Annual <small>Save up to 27%</small></button>
      </div>
      <div className="plan-choice-grid">
        <article><span>Explorer</span><h2>£0</h2><p>No card required.</p><ul><li><Check size={13} />Unlimited search across all 7 checks</li><li><Check size={13} />1 Ask / day, up to 20 words</li><li><Check size={13} />1 view-only plan / week</li><li><Check size={13} />No downloads or exports</li></ul><button type="button" disabled>Current free access</button></article>
        <article><span>Single report</span><h2>£4.99 <small>/ report</small></h2><p>No subscription required.</p><ul><li><Check size={13} />One entity with full provenance</li><li><Check size={13} />Server-generated downloadable PDF</li><li><Check size={13} />Moving-house bundle: £9.99</li></ul><button type="button" disabled>Offered when exporting</button></article>
        <article className="is-featured"><span>Plus</span><h2>{billingCadence === "annual" ? "£79" : "£8.99"} <small>/ {billingCadence === "annual" ? "year" : "month"}</small></h2><p>{billingCadence === "annual" ? "Save £28.88 compared with monthly." : "Or £79/year · save 27%."}</p><ul><li><Check size={13} />Unlimited Ask, 60-word cap</li><li><Check size={13} />Unlimited Planner and downloads</li><li><Check size={13} />Saved watchlist with change alerts</li></ul><button className="button" type="button" disabled={working || !account?.billing_configured} onClick={() => onStartCheckout("plus")}><Sparkles size={14} />Choose Plus</button></article>
        <article><span>Professional</span><h2>{billingCadence === "annual" ? "£349" : "£39"} <small>/ seat / {billingCadence === "annual" ? "year" : "month"}</small></h2><p>{billingCadence === "annual" ? "Save £119 per seat compared with monthly." : "Or £349/year per seat · save 25%."}</p><ul><li><Check size={13} />Everything in Plus, per seat</li><li><Check size={13} />Private persisted report library</li><li><Check size={13} />Operational retention workflow</li></ul><button className="button button-secondary" type="button" disabled={working || !account?.billing_configured} onClick={() => onStartCheckout("professional")}><CreditCard size={14} />Choose Professional</button></article>
      </div>
      <p className="pricing-extras">Subscriptions renew {billingCadence === "annual" ? "yearly" : "monthly"} until cancelled; manage or cancel in Billing. Prefer pay as you go? Ask coin packs are offered when your free message is used.</p>
      {!isSignedIn && <button className="plans-sign-in" type="button" onClick={onRequestSignIn}>Sign in before choosing a plan</button>}
      {account && !account.billing_configured && <p className="account-notice">Checkout is awaiting the production Stripe keys and price IDs.</p>}
    </div>
  );
}
