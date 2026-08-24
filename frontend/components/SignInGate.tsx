"use client";

import { Database, LockKeyhole } from "lucide-react";

/**
 * Stands in for Ask and Planner input while signed out.
 *
 * Both features query the connected registers per request and keep the
 * conversation with the account, so they are account-only. Saying that up front
 * beats letting someone compose a question and then refusing to send it.
 */
export function SignInGate({
  feature,
  onSignIn,
  className = "",
}: {
  feature: string;
  onSignIn: () => void;
  className?: string;
}) {
  return (
    <div className={`signin-gate ${className}`.trim()}>
      <span><LockKeyhole size={26} /></span>
      <strong>Sign in to use {feature}</strong>
      <p>
        This runs live queries against the connected official registers and keeps the
        conversation with your account, so it needs you signed in. Your first question
        each day is free.
      </p>
      <button className="button" type="button" onClick={onSignIn}>Sign in to continue</button>
      <small><Database size={11} />Signing in with your email address also creates your account.</small>
    </div>
  );
}
