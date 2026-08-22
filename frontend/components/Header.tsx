import Link from "next/link";
import { Menu } from "lucide-react";
import { Logo } from "./Logo";
import { DecisionTrigger } from "./DecisionDrawer";

const NAV_ITEMS = [
  ["Ask", "/ask"],
  ["Plan", "/plan"],
  ["Companies", "/search"],
  ["Areas", "/areas"],
  ["Qualifications", "/qualifications"],
  ["Food", "/food"],
  ["Property", "/property"],
  ["Study", "/study"],
  ["What’s changed", "/#changes"],
];

export function Header() {
  return (
    <header className="site-header">
      <div className="shell header-inner">
        <Logo />
        <nav className="desktop-nav" aria-label="Primary navigation">
          {NAV_ITEMS.map(([label, href]) => (
            label === "Ask" || label === "Plan" ?
              <DecisionTrigger key={label} mode={label === "Ask" ? "ask" : "plan"}>{label}</DecisionTrigger> :
              <Link key={label} href={href}>{label}</Link>
          ))}
        </nav>
        <div className="account-actions">
          <Link className="text-button" href="/coming-soon?feature=Accounts">
            Sign in
          </Link>
          <Link className="button button-small" href="/coming-soon?feature=Accounts">
            Sign up
          </Link>
        </div>
        <details className="mobile-nav">
          <summary aria-label="Open navigation">
            <Menu size={22} />
          </summary>
          <div className="mobile-nav-panel">
            {NAV_ITEMS.map(([label, href]) => (
              label === "Ask" || label === "Plan" ?
                <DecisionTrigger key={label} mode={label === "Ask" ? "ask" : "plan"}>{label}</DecisionTrigger> :
                <Link key={label} href={href}>{label}</Link>
            ))}
            <Link href="/coming-soon?feature=Accounts">Sign in</Link>
          </div>
        </details>
      </div>
    </header>
  );
}
