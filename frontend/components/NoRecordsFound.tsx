import type { ReactNode } from "react";
import { Lightbulb, SearchX } from "lucide-react";

const DEFAULT_NOTE =
  "Close matches held by the same official source. None of these is a match for what you searched — check the spelling, then open one only if it is the record you meant.";

/**
 * The answer to a direct search that found nothing.
 *
 * A bare "no records" leaves the user unable to tell a typo apart from a genuine
 * absence, so near matches are offered underneath — kept visually separate from
 * verified results so they are never read as a hit.
 */
export function NoRecordsFound({
  query,
  hint,
  suggestionsLabel = "Similar results",
  suggestionsNote = DEFAULT_NOTE,
  suggestionsClassName = "result-list",
  children,
}: {
  query: string;
  hint?: string;
  suggestionsLabel?: string;
  suggestionsNote?: string;
  suggestionsClassName?: string;
  children?: ReactNode;
}) {
  const hasSuggestions = Array.isArray(children) ? children.length > 0 : Boolean(children);

  return (
    <div className="no-records">
      <div className="empty-state no-records-notice" role="status">
        <SearchX size={28} />
        <h2>No records found for “{query}”</h2>
        {hint ? <p>{hint}</p> : null}
      </div>
      {hasSuggestions ? (
        <section className="result-group suggestion-group" aria-label={suggestionsLabel}>
          <div className="result-group-heading suggestion-group-heading">
            <div>
              <span className="result-group-icon suggestion-group-icon"><Lightbulb size={18} /></span>
              <div><h2>{suggestionsLabel}</h2><p>{suggestionsNote}</p></div>
            </div>
          </div>
          <div className={suggestionsClassName}>{children}</div>
        </section>
      ) : null}
    </div>
  );
}
