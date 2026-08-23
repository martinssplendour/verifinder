import Link from "next/link";
import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="shell footer-grid">
        <div>
          <Logo />
          <p>Clear answers from official public sources.</p>
        </div>
        <div>
          <strong>Product</strong>
          <Link href="/companies">Company check</Link>
          <Link href="/sponsors">Sponsorship check</Link>
          <Link href="/areas">Area check</Link>
          <Link href="/property">Property check</Link>
          <Link href="/qualifications">Qualification check</Link>
          <Link href="/food">Food check</Link>
          <Link href="/study">Study provider check</Link>
          <Link href="/sources">Sources</Link>
          <Link href="/about">How it works</Link>
        </div>
        <div>
          <strong>Important</strong>
          <p>Public-source information only. Not legal, financial, immigration or professional advice.</p>
        </div>
      </div>
    </footer>
  );
}
