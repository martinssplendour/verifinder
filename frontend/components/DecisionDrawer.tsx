"use client";

import {
  createContext,
  FormEvent,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ArrowRight,
  BadgeCheck,
  Bot,
  Check,
  CircleAlert,
  Database,
  Download,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Route,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { useAccount } from "@/components/Account";
import { CoinPaywall, type CoinPack } from "@/components/CoinPaywall";
import { SignInGate } from "@/components/SignInGate";
import { AskAnswer } from "@/components/decision-drawer/AskAnswer";
import { PlanReport } from "@/components/decision-drawer/PlanReport";
import { useAskConversation } from "@/components/decision-drawer/useAskConversation";
import { usePlanConversation } from "@/components/decision-drawer/usePlanConversation";
import { ApiError, createCoinCheckout } from "@/services/api";

type DrawerMode = "ask" | "plan";

const PRIORITIES = ["Housing cost", "Work sponsorship", "Study", "Schools", "Crime", "Planning", "Flood risk"];

const DecisionDrawerContext = createContext<{ openDrawer: (mode: DrawerMode) => void } | null>(null);

export function DecisionTrigger({ mode, className, children }: { mode: DrawerMode; className?: string; children: ReactNode }) {
  const context = useContext(DecisionDrawerContext);
  return <button type="button" className={className} onClick={() => context?.openDrawer(mode)} aria-haspopup="dialog">{children}</button>;
}

export function DecisionDrawerProvider({ children }: { children: ReactNode }) {
  const { session, account, openAccount, refreshAccount } = useAccount();
  const [mode, setMode] = useState<DrawerMode | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<ApiError | null>(null);
  const [purchasing, setPurchasing] = useState<CoinPack | null>(null);
  const closeButton = useRef<HTMLButtonElement | null>(null);
  const conversationEnd = useRef<HTMLDivElement | null>(null);

  const ask = useAskConversation({ setLoading, setError, setBlocked });
  const plan = usePlanConversation({ setLoading, setError, setBlocked, setInput, refreshAccount });
  const signedIn = Boolean(session);

  const close = useCallback(() => setMode(null), []);
  const openDrawer = useCallback((nextMode: DrawerMode) => {
    setMode(nextMode);
    setInput("");
    setError(null);
    setBlocked(null);
  }, []);

  useEffect(() => {
    if (!mode) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const keydown = (event: KeyboardEvent) => { if (event.key === "Escape") close(); };
    window.addEventListener("keydown", keydown);
    return () => { document.body.style.overflow = previousOverflow; window.removeEventListener("keydown", keydown); };
  }, [mode, close]);

  useEffect(() => {
    conversationEnd.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [ask.messages, plan.messages, loading, plan.report]);

  async function submitAsk(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (question.length < 3 || loading) return;
    setInput("");
    await ask.submit(question);
  }

  function submitPlanText(event: FormEvent) {
    event.preventDefault();
    const value = input.trim();
    if (!value || loading) return;
    setError(null);
    setBlocked(null);
    plan.submitText(value);
  }

  async function buyCoins(pack: CoinPack) {
    setPurchasing(pack);
    try {
      const checkout = await createCoinCheckout(pack);
      window.location.assign(checkout.url);
    } catch (checkoutError) {
      setError((checkoutError as Error).message);
      setPurchasing(null);
    }
  }

  const messages = mode === "ask" ? ask.messages : plan.messages;
  const needsCoins = blocked?.paymentRequired === true && signedIn;
  const planPlaceholder = plan.stage === "goal" ? "Describe your decision…" : plan.stage === "location" ? "Town, city, area or postcode…" : plan.stage === "budget" ? "Budget amount or skip…" : plan.stage === "date" ? "YYYY-MM-DD or skip…" : "";

  return (
    <DecisionDrawerContext.Provider value={{ openDrawer }}>
      {children}
      {mode && <div className="decision-drawer-layer">
        <button className="drawer-backdrop" onClick={close} aria-label="Close decision assistant" />
        <section className="decision-drawer" role="dialog" aria-modal="true" aria-labelledby="decision-drawer-title">
          <header className="drawer-header">
            <div><span className="drawer-header-icon">{mode === "ask" ? <MessageSquareText size={18} /> : <Route size={18} />}</span><div><strong id="decision-drawer-title">{mode === "ask" ? "Ask VeriFinder" : "Decision Planner"}</strong><small>Evidence-backed · database read-only</small></div></div>
            <button ref={closeButton} type="button" onClick={close} aria-label="Close"><X size={20} /></button>
          </header>
          <div className="drawer-mode-switch" role="tablist" aria-label="Decision assistant mode">
            <button role="tab" aria-selected={mode === "ask"} className={mode === "ask" ? "is-active" : ""} onClick={() => openDrawer("ask")}><MessageSquareText size={15} />Ask</button>
            <button role="tab" aria-selected={mode === "plan"} className={mode === "plan" ? "is-active" : ""} onClick={() => openDrawer("plan")}><Route size={15} />Plan</button>
          </div>
          {!signedIn ? (
            <SignInGate
              className="drawer-signin-gate"
              feature={mode === "ask" ? "Ask VeriFinder" : "the Decision Planner"}
              onSignIn={() => openAccount("sign-in")}
            />
          ) : (<>
          <div className="drawer-conversation">
            {messages.map((item) => <div className={`chat-row chat-${item.role}`} key={item.id}>{item.role === "assistant" && <span className="chat-avatar"><Bot size={15} /></span>}<div className="chat-content">{item.text && <p>{item.text}</p>}{item.ask && <AskAnswer answer={item.ask} close={close} ask={(question) => void ask.submit(question)} />}</div></div>)}
            {mode === "plan" && plan.stage === "priorities" && <div className="priority-conversation"><div>{PRIORITIES.map((priority) => <button type="button" className={plan.draft.priorities.includes(priority) ? "is-selected" : ""} onClick={() => plan.togglePriority(priority)} key={priority}>{plan.draft.priorities.includes(priority) && <Check size={12} />}{priority}</button>)}</div><button className="button" type="button" onClick={plan.confirmPriorities}>Continue <ArrowRight size={15} /></button></div>}
            {loading && <div className="chat-row chat-assistant"><span className="chat-avatar"><Sparkles size={15} /></span><div className="chat-thinking"><LoaderCircle className="spin" size={16} /><span>{mode === "ask" ? "Querying connected records…" : "Building the evidence report…"}</span></div></div>}
            {error && <div className="drawer-chat-error" role="alert"><CircleAlert size={15} /><span>{error}</span></div>}
            {needsCoins && <CoinPaywall
              message={blocked?.message}
              isSignedIn={signedIn}
              coinBillingConfigured={account?.coin_billing_configured ?? false}
              purchasing={purchasing}
              onBuy={(pack) => void buyCoins(pack)}
              onSignIn={() => openAccount("sign-in")}
              onViewPlans={() => openAccount("plans")}
            />}
            {blocked && !needsCoins && <div className="drawer-upgrade-prompt"><Sparkles size={18} /><div><strong>{signedIn ? "Upgrade to continue" : "Continue with an account"}</strong><p>{blocked.message}</p><button className="button" type="button" onClick={() => openAccount(signedIn ? "plans" : "sign-in")}>{signedIn ? "View plans" : "Sign in"}</button></div></div>}
            {mode === "plan" && plan.report && <PlanReport plan={plan.report} />}
            <div ref={conversationEnd} />
          </div>
          <footer className="drawer-composer">
            {mode === "ask" ? <form onSubmit={submitAsk}><textarea aria-label="Ask a question" rows={1} value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a verified-data question…" /><button type="submit" disabled={loading || input.trim().length < 3} aria-label="Send question"><Send size={17} /></button></form> : plan.stage === "report" && plan.report ? <div className="report-actions"><button className="button" type="button" disabled={plan.reportLoading} onClick={() => void plan.downloadReport()}>{plan.reportLoading ? <LoaderCircle className="spin" size={16} /> : <Download size={16} />}{plan.reportLoading ? "Preparing secure PDF…" : "Save & download PDF"}</button><button className="drawer-icon-action" type="button" onClick={plan.reset} aria-label="Start a new plan"><RefreshCw size={17} /></button></div> : plan.stage === "priorities" ? <p className="drawer-helper"><BadgeCheck size={14} />Choose any number of priorities, then continue.</p> : <form onSubmit={submitPlanText}><textarea aria-label="Reply to planner" rows={1} value={input} onChange={(event) => setInput(event.target.value)} placeholder={planPlaceholder} /><button type="submit" disabled={loading || !input.trim()} aria-label="Send reply"><Send size={17} /></button></form>}
            <small><Database size={11} />Connected records are queried read-only. Conversation content is not saved by VeriFinder.</small>
          </footer>
          </>)}
        </section>
      </div>}
    </DecisionDrawerContext.Provider>
  );
}
