import { ArrowDown, BadgeCheck, Building2, Database, FileArchive, GitCompareArrows, ShieldCheck } from "lucide-react";

const FLOW = [
  { icon: ShieldCheck, title: "Official source", copy: "Companies House or the UK Home Office" },
  { icon: FileArchive, title: "Versioned data", copy: "Raw input retained with a file hash" },
  { icon: Database, title: "Normalised record", copy: "Original values preserved for audit" },
  { icon: GitCompareArrows, title: "Resolved entity", copy: "Matches carry method and confidence" },
  { icon: BadgeCheck, title: "Verified fact", copy: "Source metadata travels with the answer" },
];

export default function AboutPage() {
  return (
    <div className="shell content-page about-page">
      <div className="content-hero">
        <span className="eyebrow"><Building2 size={15} /> How VeriFinder works</span>
        <h1>Official data. Clear answers.</h1>
        <p>VeriFinder turns fragmented public records into decision-friendly answers without treating AI-generated text as evidence.</p>
      </div>
      <section className="evidence-flow" aria-label="Verified information flow">
        {FLOW.map(({ icon: Icon, title, copy }, index) => (
          <div className="flow-group" key={title}>
            <article><span><Icon size={22} /></span><h2>{title}</h2><p>{copy}</p></article>
            {index < FLOW.length - 1 && <ArrowDown className="flow-arrow" size={18} />}
          </div>
        ))}
      </section>
      <section className="principles-grid">
        <article><h2>No guesswork dressed as fact</h2><p>AI may help explain a result, but it cannot create the official status displayed to a user.</p></article>
        <article><h2>No-match is not a verdict</h2><p>Not finding a record is different from proving ineligibility, illegality or fraud. The product language keeps that distinction clear.</p></article>
        <article><h2>History stays intact</h2><p>Dataset versions are retained so additions, removals and meaningful changes can be traced over time.</p></article>
      </section>
    </div>
  );
}

