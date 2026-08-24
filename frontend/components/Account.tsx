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
import Link from "next/link";
import { UserRound, X } from "lucide-react";
import { createCheckout, getAccountStatus, openBillingPortal } from "@/services/api";
import { getSupabaseClient } from "@/services/supabase";
import { AccountLibrary } from "@/components/AccountLibrary";
import { AccountPlans } from "@/components/account/AccountPlans";
import { AccountSignIn } from "@/components/account/AccountSignIn";
import { AccountSummary } from "@/components/account/AccountSummary";
import type { AccountStatus, SubscriptionTier } from "@/types";


type AccountView = "sign-in" | "plans" | "account" | "library";
type BillingCadence = "monthly" | "annual";
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
  const [billingCadence, setBillingCadence] = useState<BillingCadence>("monthly");

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
      queueMicrotask(() => {
        setLoading(false);
        void refreshAccount();
      });
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
    queueMicrotask(() => {
      if (params.get("billing") === "success") {
        setView("account");
        setMessage("Payment received. Your access updates as soon as Stripe confirms the subscription.");
        window.setTimeout(() => void refreshAccount(), 1500);
      } else if (params.get("auth") === "complete") {
        setView("account");
      } else if (params.get("account") === "watchlist") {
        setView("library");
      }
    });
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
      options: { emailRedirectTo: `${window.location.origin}${window.location.pathname}?auth=complete` },
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
      const result = await createCheckout(tier, billingCadence);
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
              <div><span><UserRound size={18} /></span><div><strong id="account-dialog-title">{view === "plans" ? "Choose your access" : view === "library" ? "Saved reports & watches" : session ? "Your VeriFinder account" : "Sign in to VeriFinder"}</strong><small>Secure authentication by Supabase</small></div></div>
              <button type="button" onClick={() => setView(null)} aria-label="Close"><X size={19} /></button>
            </header>

            {!session && view !== "plans" ? (
              <AccountSignIn email={email} onEmailChange={setEmail} onSubmit={sendMagicLink} working={working} />
            ) : view === "plans" ? (
              <AccountPlans
                billingCadence={billingCadence}
                onCadenceChange={setBillingCadence}
                working={working}
                account={account}
                isSignedIn={Boolean(session)}
                onStartCheckout={(tier) => void startCheckout(tier)}
                onRequestSignIn={() => setView("sign-in")}
              />
            ) : view === "library" && session ? (
              <AccountLibrary onError={setError} />
            ) : session ? (
              <AccountSummary
                session={session}
                account={account}
                working={working}
                onOpenLibrary={() => setView("library")}
                onOpenPlans={() => setView("plans")}
                onManageBilling={() => void manageBilling()}
                onSignOut={() => void signOut()}
              />
            ) : null}
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
    return <div className="account-actions">{account?.is_admin && <Link className="text-button" href="/admin">Admin</Link>}<button className="account-pill" type="button" onClick={() => openAccount("account")}><UserRound size={14} /><span>{session.user.email?.split("@")[0]}</span><em>{account?.is_admin ? "admin" : account?.entitlements.tier || "free"}</em></button></div>;
  }
  return <div className="account-actions"><button className="text-button" type="button" onClick={() => openAccount("sign-in")}>Sign in</button><button className="button button-small" type="button" onClick={() => openAccount("plans")}>Sign up</button></div>;
}

export function MobileAccountAction() {
  const { session, account, openAccount } = useAccount();
  return <>{account?.is_admin && <Link href="/admin">Admin</Link>}<button type="button" onClick={() => openAccount(session ? "account" : "sign-in")}>{session ? "Account" : "Sign in"}</button></>;
}
