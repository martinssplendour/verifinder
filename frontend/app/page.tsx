import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Building2,
  Check,
  GraduationCap,
  Home,
  Landmark,
  MapPin,
  RefreshCw,
  School,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  Utensils,
  MessageSquareText,
  Route,
} from "lucide-react";
import { SearchBox } from "@/components/SearchBox";
import { DecisionTrigger } from "@/components/DecisionDrawer";

const categories = [
  { icon: Building2, title: "Company Check", copy: "Verify registration, status and visa sponsorship.", href: "/search", live: true, tone: "blue" },
  { icon: MapPin, title: "Area Check", copy: "Recent crime, flood warnings and planning designations.", href: "/areas", live: true, tone: "teal" },
  { icon: GraduationCap, title: "Qualification Check", copy: "Check whether a qualification is officially regulated.", href: "/qualifications", live: true, tone: "purple" },
  { icon: Utensils, title: "Food Check", copy: "Food hygiene ratings and inspection history.", href: "/food", live: true, tone: "mint" },
  { icon: Home, title: "Property Check", copy: "Recorded 2025–2026 sale prices and postcode planning context.", href: "/property", live: true, tone: "sky" },
  { icon: BookOpen, title: "Study Check", copy: "Student sponsorship and English higher-education registration.", href: "/study", live: true, tone: "indigo" },
  { icon: School, title: "School Check", copy: "GIAS establishment details and the latest Ofsted inspection outcome.", href: "/school", live: true, tone: "amber" },
];

export default function HomePage() {
  return (
    <>
      <section className="hero shell">
        <div className="eyebrow"><ShieldCheck size={15} /> Answers backed by official sources</div>
        <h1>Check before you decide.</h1>
        <p>Search companies, areas, property sales, regulated qualifications and food hygiene records using official public data.</p>
        <div className="hero-search"><SearchBox /></div>
      </section>

      <section className="shell intelligence-entry" aria-labelledby="decision-tools">
        <div className="intelligence-entry-heading">
          <span className="kicker">Decision intelligence</span>
          <h2 id="decision-tools">Move from isolated checks to a useful answer.</h2>
          <p>Ask across connected public records, or build a plan that keeps facts, calculations, inferences and unknowns visibly separate.</p>
        </div>
        <div className="intelligence-entry-actions">
          <DecisionTrigger className="intelligence-card intelligence-card-ask" mode="ask">
            <span><MessageSquareText size={24} /></span>
            <div><strong>Ask VeriFinder</strong><small>“Show me licensed sponsors in Sheffield”</small></div>
            <ArrowRight size={19} />
          </DecisionTrigger>
          <DecisionTrigger className="intelligence-card intelligence-card-plan" mode="plan">
            <span><Route size={24} /></span>
            <div><strong>Build a decision plan</strong><small>“Help me plan a move around Manchester”</small></div>
            <ArrowRight size={19} />
          </DecisionTrigger>
        </div>
      </section>

      <section className="shell category-grid" aria-labelledby="ways-to-check">
        <h2 className="sr-only" id="ways-to-check">Ways to check</h2>
        {categories.map(({ icon: Icon, title, copy, href, live, tone }) => (
          <Link className={`category-card category-${tone}`} href={href} key={title}>
            <span className="category-icon"><Icon size={25} strokeWidth={1.9} /></span>
            <div>
              <h3>{title}</h3>
              <p>{copy}</p>
            </div>
            <span className={`category-state ${live ? "is-live" : ""}`}>{live ? "Available now" : "Coming soon"}</span>
            <ArrowRight className="category-arrow" size={18} />
          </Link>
        ))}
      </section>

      <section className="shell section-band changes-band" id="changes">
        <div className="section-heading-row">
          <div>
            <span className="kicker">Dataset intelligence</span>
            <h2>What’s changed?</h2>
          </div>
          <span className="quiet-chip"><RefreshCw size={14} /> Version tracking ready</span>
        </div>
        <div className="change-empty">
          <span className="change-empty-icon"><Sparkles size={23} /></span>
          <div>
            <h3>Change tracking begins with the first official import</h3>
            <p>Genuine additions, removals and route changes will appear after VeriFinder has collected multiple sponsor-register versions. No placeholder statistics are shown.</p>
          </div>
          <Link href="/about">How change tracking works <ArrowRight size={15} /></Link>
        </div>
      </section>

      <section className="shell section-band sources-preview">
        <div className="section-heading-row">
          <div>
            <span className="kicker">Provenance built in</span>
            <h2>Verified data from</h2>
          </div>
          <Link href="/sources">View source registry <ArrowRight size={15} /></Link>
        </div>
        <div className="source-logo-grid">
          <div className="source-logo"><span><Landmark size={22} /></span><div><strong>Companies House</strong><small>Company registration data</small></div></div>
          <div className="source-logo"><span><ShieldCheck size={22} /></span><div><strong>UK Home Office</strong><small>Licensed sponsor register</small></div></div>
          <div className="source-logo"><span><GraduationCap size={22} /></span><div><strong>Ofqual</strong><small>Regulated qualifications register</small></div></div>
          <div className="source-logo"><span><Utensils size={22} /></span><div><strong>Food Standards Agency</strong><small>Food hygiene ratings</small></div></div>
        </div>
      </section>

      <section className="shell trust-panel">
        <div className="trust-icon"><SearchCheck size={31} /></div>
        <div>
          <span className="kicker">Evidence, not guesswork</span>
          <h2>Every important answer keeps its receipt.</h2>
          <p>VeriFinder keeps source, retrieval and version information attached to the facts it presents—so “verified” always means traceable.</p>
        </div>
        <ul>
          <li><Check size={16} /> Official-source attribution</li>
          <li><Check size={16} /> Careful no-match language</li>
          <li><Check size={16} /> Historical dataset versions</li>
        </ul>
      </section>
    </>
  );
}
