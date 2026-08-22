import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function Logo() {
  return (
    <Link className="brand" href="/" aria-label="VeriFinder home">
      <span className="brand-mark" aria-hidden="true">
        <ShieldCheck size={23} strokeWidth={2.5} />
      </span>
      <span className="brand-copy">
        <strong>VeriFinder</strong>
        <small>Check before you decide.</small>
      </span>
    </Link>
  );
}

