import { useMemo, useState } from "react";
import type { ImpactGraph, SemanticChange } from "../api/types";
import { formatJson } from "../lib/workflow";
import { ErrorState, LoadingState } from "../components/States";

type Props = {
  changes: SemanticChange[] | null;
  impact: ImpactGraph | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
};

function pages(list?: { page: number }[] | null): string {
  if (!list?.length) return "—";
  return [...new Set(list.map((e) => e.page))].sort((a, b) => a - b).join(", ");
}

function quotes(list?: { quote?: string | null; page: number; section_id: string }[] | null) {
  if (!list?.length) return <p className="empty">No evidence quotes.</p>;
  return (
    <ul className="evidence-list">
      {list.map((e, i) => (
        <li key={`${e.page}-${e.section_id}-${i}`}>
          <span className="ev-meta">
            p.{e.page} · {e.section_id}
          </span>
          <q>{e.quote || "(no quote)"}</q>
        </li>
      ))}
    </ul>
  );
}

export function RedlineView({ changes, impact, loading, error, onRetry }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const enriched = useMemo(() => {
    if (!changes) return [];
    return changes.map((c) => {
      const sites = new Set<string>();
      const participants = new Set<string>();
      const artifacts = new Set<string>(c.affected_artifact_ids ?? []);
      if (impact) {
        for (const edge of impact.edges) {
          if (edge.change_id !== c.change_id) continue;
          const node = impact.nodes.find((n) => n.node_id === edge.to_node_id);
          if (!node) continue;
          if (node.layer === "site") sites.add(node.label);
          if (node.layer === "participant") participants.add(node.label);
          if (node.layer === "operational_artifact") artifacts.add(node.label);
        }
      }
      return { change: c, sites: [...sites], participants: [...participants], artifacts: [...artifacts] };
    });
  }, [changes, impact]);

  const active =
    enriched.find((e) => e.change.change_id === selected)?.change ?? enriched[0]?.change ?? null;
  const activeMeta = enriched.find((e) => e.change.change_id === active?.change_id);

  if (loading && !changes) return <LoadingState label="Loading semantic changes…" />;
  if (error && !changes) return <ErrorState error={error} onRetry={onRetry} />;
  if (!changes?.length) {
    return <p className="empty">No semantic changes yet — waiting for Trace stage.</p>;
  }

  return (
    <section className="view redline-view" aria-labelledby="redline-title">
      <header className="view-header">
        <h2 id="redline-title">Semantic Redline</h2>
        <p>Evidence-linked concept changes — not a word-only diff.</p>
      </header>

      <div className="change-picker" role="tablist" aria-label="Semantic changes">
        {enriched.map(({ change }) => (
          <button
            key={change.change_id}
            type="button"
            role="tab"
            aria-selected={active?.change_id === change.change_id}
            className="chip"
            onClick={() => setSelected(change.change_id)}
          >
            {change.change_id}
          </button>
        ))}
      </div>

      {active && (
        <div className="redline-columns" role="tabpanel">
          <div className="col evidence-col">
            <h3>Old protocol evidence</h3>
            {quotes(active.old_evidence?.length ? active.old_evidence : null)}
            {!active.old_evidence?.length && quotes(null)}
          </div>

          <article className="col change-card" aria-label={`Change ${active.change_id}`}>
            <h3>{active.concept_type}</h3>
            <dl className="kv">
              <div>
                <dt>Operation</dt>
                <dd>{active.operation}</dd>
              </div>
              <div>
                <dt>Before</dt>
                <dd>
                  <pre>{formatJson(active.before)}</pre>
                </dd>
              </div>
              <div>
                <dt>After</dt>
                <dd>
                  <pre>{formatJson(active.after)}</pre>
                </dd>
              </div>
              <div>
                <dt>Risk candidate</dt>
                <dd>{active.candidate_risk ?? active.expected_risk_tier ?? "—"}</dd>
              </div>
              <div>
                <dt>Review</dt>
                <dd>
                  {active.review_status ?? "—"}
                  {active.old_evidence?.[0]?.confidence != null &&
                    ` · conf ${(active.old_evidence[0].confidence * 100).toFixed(0)}%`}
                </dd>
              </div>
              <div>
                <dt>Source pages</dt>
                <dd>
                  old {pages(active.old_evidence)} · new {pages(active.new_evidence)}
                </dd>
              </div>
              <div>
                <dt>Affected artifacts</dt>
                <dd>{activeMeta?.artifacts.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt>Affected sites</dt>
                <dd>{activeMeta?.sites.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt>Affected participants</dt>
                <dd>{activeMeta?.participants.join(", ") || "—"}</dd>
              </div>
            </dl>
            {active.explanation && <p className="explain">{active.explanation}</p>}
          </article>

          <div className="col evidence-col">
            <h3>New protocol evidence</h3>
            {quotes(active.new_evidence?.length ? active.new_evidence : active.evidence)}
          </div>
        </div>
      )}
    </section>
  );
}
