"use client";

import {
  createContext,
  FormEvent,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { BadgeCheck, Check, CreditCard, LoaderCircle, LogOut, Mail, Sparkles, UserRound, X } from "lucide-react";
import { createCheckout, getAccountStatus, openBillingPortal } from "@/services/api";
import { getSupabaseClient } from "@/services/supabase";
import type { AccountStatus, SubscriptionTier } from "@/types";


type AccountView = "sign-in" | "plans" | "account";
type AccountContextValue = {
  session: Session | null;
  account: AccountStatus | null;
  loading: boolean;
  openAccount: (view?: AccountView) => void;
  refreshAccount: () => Promise<void>;
};

const AccountContext = createContext<AccountContextValue | null>(null);

export function useAccount() {
  const context = useContext(AccountContext);
  if (!context) throw new Error("useAccount must be used inside AccountProvider.");
  return context;
}

export function AccountProvider({ children }: { children: ReactNode }) {
  const supabase = useMemo(() => getSupabaseClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [account, setAccount] = useState<AccountStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<AccountView | null>(null);
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  const refreshAccount = useCallback(async () => {
    try {
      setAccount(await getAccountStatus());
    } catch {
      setAccount(null);
    }
  }, []);

  useEffect(() => {
    let active = true;
    if (!supabase) {
      setLoading(false);
      void refreshAccount();
      return;
    }
    void supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setLoading(false);
      void refreshAccount();
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      queueMicrotask(() => void refreshAccount());
    });
    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, [supabase, refreshAccount]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("billing") === "success") {
      setView("account");
      setMessage("Payment received. Your access updates as soon as Stripe confirms the subscription.");
      window.setTimeout(() => void refreshAccount(), 1500);
    } else if (params.get("auth") === "complete") {
      setView("account");
    }
  }, [refreshAccount]);

  function openAccount(nextView: AccountView = session ? "account" : "sign-in") {
    setError(null);
    setMessage(null);
    setView(nextView === "sign-in" && session ? "account" : nextView);
  }

  async function sendMagicLink(event: FormEvent) {
    event.preventDefault();
    if (!supabase || !email.trim()) return;
    setWorking(true);
    setError(null);
    const { error: authError } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: { emailRedirectTo: `${window.location.origin}/?auth=complete` },
    });
    setWorking(false);
    if (authError) setError(authError.message);
    else setMessage("Check your email for your secure VeriFinder sign-in link.");
  }

  async function startCheckout(tier: Exclude<SubscriptionTier, "free">) {
    if (!session) {
      setView("sign-in");
      setMessage("Sign in first, then choose your plan.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const result = await createCheckout(tier);
      window.location.assign(result.url);
    } catch (checkoutError) {
      setError((checkoutError as Error).message);
      setWorking(false);
    }
  }

  async function manageBilling() {
    setWorking(true);
    setError(null);
    try {
      const result = await openBillingPortal();
      window.location.assign(result.url);
    } catch (portalError) {
      setError((portalError as Error).message);
      setWorking(false);
    }
  }

  async function signOut() {
    if (supabase) await supabase.auth.signOut();
    setView(null);
  }

  return (
    <AccountContext.Provider value={{ session, account, loading, openAccount, refreshAccount }}>
      {children}
      {view && (
        <div className="account-dialog-layer">
          <button className="account-dialog-backdrop" type="button" onClick={() => setView(null)} aria-label="Close account dialog" />
          <section className="account-dialog" role="dialog" aria-modal="true" aria-labelledby="account-dialog-title">
            <header>
              <div><span><UserRound size={18} /></span><div><strong id="account-dialog-title">{view === "plans" ? "Choose your access" : session ? "Your VeriFinder account" : "Sign in to VeriFinder"}</strong><small>Secure authentication by Supabase</small></div></div>
              <button type="button" onClick={() => setView(null)} aria-label="Close"><X size={19} /></button>
            </header>

            {!session && view !== "plans" ? (
              <div className="account-sign-in">
                <span className="account-hero-icon"><Mail size={22} /></span>
                <h2>No password to remember.</h2>
                <p>Enter your email and we’ll send a secure, single-use sign-in link.</p>
                <form onSubmit={sendMagicLink}>
                  <label htmlFor="account-email">Email address</label>
                  <input id="account-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required placeholder="you@example.com" />
                  <button className="button" type="submit" disabled={working}>{working ? <LoaderCircle className="spin" size={16} /> : <Mail size={16} />}{working ? "Sending…" : "Email me a sign-in link"}</button>
                </form>
                <small>Public record checks remain available without an account.</small>
              </div>
            ) : view === "plans" ? (
              <div className="account-plans">
                <div className="plan-choice-grid">
                  <article><span>Basic</span><h2>Free</h2><p>For occasional verified-data decisions.</p><ul><li><Check size={13} />One Ask query per day</li><li><Check size={13} />One plan per week</li><li><Check size={13} />All public checks</li></ul><button type="button" disabled>Current free access</button></article>
                  <article className="is-featured"><span>Plus</span><h2>Unlimited AI</h2><p>For active research and planning.</p><ul><li><Check size={13} />Unlimited Ask queries</li><li><Check size={13} />Unlimited decision plans</li><li><Check size={13} />Download reports</li></ul><button className="button" type="button" disabled={working || !account?.billing_configured} onClick={() => void startCheckout("plus")}><Sparkles size={14} />Choose Plus</button></article>
                  <article><span>Professional</span><h2>Advanced</h2><p>For repeat professional decisions.</p><ul><li><Check size={13} />Everything in Plus</li><li><Check size={13} />Professional entitlement</li><li><Check size={13} />Future saved reports</li></ul><button className="button button-secondary" type="button" disabled={working || !account?.billing_configured} onClick={() => void startCheckout("professional")}><CreditCard size={14} />Choose Professional</button></article>
                </div>
                {!session && <button className="plans-sign-in" type="button" onClick={() => setView("sign-in")}>Sign in before choosing a plan</button>}
                {account && !account.billing_configured && <p className="account-notice">Checkout is awaiting the production Stripe keys and price IDs.</p>}
              </div>
            ) : (
              <div className="account-summary">
                <div className="account-identity"><span><BadgeCheck size={20} /></span><div><small>Signed in as</small><strong>{session?.user.email}</strong></div><em>{account?.entitlements.tier || "free"}</em></div>
                <div className="account-allowances"><div><strong>Ask</strong><span>{account?.entitlements.ask.allowed ? "Available" : "Free allowance used"}</span></div><div><strong>Planner</strong><span>{account?.entitlements.planner.allowed ? "Available" : "Free allowance used"}</span></div><div><strong>Reports</strong><span>{account?.entitlements.report_download.allowed ? "Downloads enabled" : "Upgrade required"}</span></div></div>
                <div className="account-buttons"><button className="button" type="button" onClick={() => setView("plans")}><Sparkles size={15} />View plans</button>{account?.has_billing_account && <button className="button button-secondary" type="button" disabled={working} onClick={() => void manageBilling()}><CreditCard size={15} />Manage billing</button>}<button className="text-button" type="button" onClick={() => void signOut()}><LogOut size={14} />Sign out</button></div>
              </div>
            )}
            {message && <p className="account-message" role="status">{message}</p>}
            {error && <p className="account-error" role="alert">{error}</p>}
          </section>
        </div>
      )}
    </AccountContext.Provider>
  );
}

export function AccountActions() {
  const { session, account, loading, openAccount } = useAccount();
  if (loading) return <div className="account-actions"><span className="account-loading">Account</span></div>;
  if (session) {
    return <div className="account-actions"><button className="account-pill" type="button" onClick={() => openAccount("account")}><UserRound size={14} /><span>{session.user.email?.split("@")[0]}</span><em>{account?.entitlements.tier || "free"}</em></button></div>;
  }
  return <div className="account-actions"><button className="text-button" type="button" onClick={() => openAccount("sign-in")}>Sign in</button><button className="button button-small" type="button" onClick={() => openAccount("plans")}>Sign up</button></div>;
}

export function MobileAccountAction() {
  const { session, openAccount } = useAccount();
  return <button type="button" onClick={() => openAccount(session ? "account" : "sign-in")}>{session ? "Account" : "Sign in"}</button>;
}
