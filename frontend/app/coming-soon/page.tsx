"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Clock3, ShieldCheck } from "lucide-react";

function ComingSoonContent() {
  const params = useSearchParams();
  const feature = params.get("feature") || "This feature";
  return (
    <div className="shell coming-soon-page">
      <span className="coming-icon"><Clock3 size={30} /></span>
      <span className="kicker">Planned integration</span>
      <h1>{feature} is coming soon.</h1>
      <p>We’ll only release this check when its official sources, freshness metadata and careful no-match states are ready.</p>
      <div className="coming-principle"><ShieldCheck size={18} /> No fake functionality or unsupported results.</div>
      <Link className="button" href="/"><ArrowLeft size={16} /> Back to VeriFinder</Link>
    </div>
  );
}

export default function ComingSoonPage() {
  return <Suspense><ComingSoonContent /></Suspense>;
}

