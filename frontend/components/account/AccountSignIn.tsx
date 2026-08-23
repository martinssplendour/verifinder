"use client";

import { FormEvent } from "react";
import { LoaderCircle, Mail } from "lucide-react";

type Props = {
  email: string;
  onEmailChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  working: boolean;
};

export function AccountSignIn({ email, onEmailChange, onSubmit, working }: Props) {
  return (
    <div className="account-sign-in">
      <span className="account-hero-icon"><Mail size={22} /></span>
      <h2>No password to remember.</h2>
      <p>Enter your email and we’ll send a secure, single-use sign-in link.</p>
      <form onSubmit={onSubmit}>
        <label htmlFor="account-email">Email address</label>
        <input id="account-email" type="email" value={email} onChange={(event) => onEmailChange(event.target.value)} autoComplete="email" required placeholder="you@example.com" />
        <button className="button" type="submit" disabled={working}>{working ? <LoaderCircle className="spin" size={16} /> : <Mail size={16} />}{working ? "Sending…" : "Email me a sign-in link"}</button>
      </form>
      <small>Public record checks remain available without an account.</small>
    </div>
  );
}
