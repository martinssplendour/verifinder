import type { ReactNode } from "react";
import { Lightbulb, SearchX } from "lucide-react";

const DEFAULT_NOTE = "Close matches from the same official source — none is an exact match for what you typed.";

/**
 * What a search renders when nothing matched the query exactly.
 *
 * Possible matches are shown as results, because results are what a search is
 * for; announcing "no records found" above a list of records only contradicts
 * itself. The group stays visually distinct from an exact hit so a near match is
 * never read as a confirmed one, and only a search with nothing at all to show
 * falls back to the empty notice.
 */
export function NoExactMatch({
  query,
  hint,
  label = "Possible matches",
  note = DEFAULT_NOTE,
  listClassName = "result-list",
  children,
}: {
  query: string;
  hint?: string;
  label?: string;
  note?: string;
  listClassName?: string;
  children?: ReactNode;
}) {
  const count = Array.isArray(children) ? children.length : Number(Boolean(children));

  if (count === 0) {
    return (
      <div className="empty-state" role="status">
        <SearchX size={28} />
        <h2>No records found for “{query}”</h2>
        {hint ? <p>{hint}</p> : null}
      </div>
    );
  }

  return (
    <section className="result-group suggestion-group" aria-label={label}>
      <div className="result-group-heading suggestion-group-heading">
        <div>
          <span className="result-group-icon suggestion-group-icon"><Lightbulb size={18} /></span>
          <div><h2>{label}</h2><p>{note}</p></div>
        </div>
        <span>{count} found</span>
      </div>
      <div className={listClassName}>{children}</div>
    </section>
  );
}
