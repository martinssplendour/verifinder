import Link from "next/link";
import { Menu } from "lucide-react";
import { Logo } from "./Logo";
import { DecisionTrigger } from "./DecisionDrawer";
import { AccountActions, MobileAccountAction } from "./Account";

type NavItem = {
  label: string;
  href: string;
  mobileLabel?: string;
  mode?: "ask" | "plan";
};

const NAV_ITEMS: NavItem[] = [
  { label: "Ask", mobileLabel: "Ask VeriFinder", href: "/ask", mode: "ask" },
  { label: "Plan", mobileLabel: "Build a decision plan", href: "/plan", mode: "plan" },
  { label: "Companies", href: "/companies" },
  { label: "Sponsors", href: "/sponsors" },
  { label: "Areas", href: "/areas" },
  { label: "Qualifications", href: "/qualifications" },
  { label: "Food", href: "/food" },
  { label: "Property", href: "/property" },
  { label: "Study", href: "/study" },
  { label: "What’s changed", href: "/#changes" },
];

export function Header() {
  return (
    <header className="site-header">
      <div className="shell header-inner">
        <Logo />
        <nav className="desktop-nav" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => (
            item.mode ?
              <DecisionTrigger key={item.label} mode={item.mode}>{item.label}</DecisionTrigger> :
              <Link key={item.label} href={item.href}>{item.label}</Link>
          ))}
        </nav>
        <AccountActions />
        <details className="mobile-nav">
          <summary aria-label="Open navigation">
            <Menu size={22} />
          </summary>
          <div className="mobile-nav-panel">
            {NAV_ITEMS.map((item) => (
              item.mode ?
                <DecisionTrigger key={item.label} mode={item.mode}>{item.mobileLabel ?? item.label}</DecisionTrigger> :
                <Link key={item.label} href={item.href}>{item.mobileLabel ?? item.label}</Link>
            ))}
            <MobileAccountAction />
          </div>
        </details>
      </div>
    </header>
  );
}
