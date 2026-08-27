import { useEffect, useMemo, useState } from "react";
import type { ImpactGraph, SemanticChange } from "../api/types";
import { formatJson } from "../lib/workflow";
import { ErrorState, LoadingState } from "../components/States";

type Props = {
  changes: SemanticChange[] | null;
  impact: ImpactGraph | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
  recordingMode?: boolean;
};

function isPkSixHour(change: SemanticChange): boolean {
  const id = change.change_id.toUpperCase();
  const concept = change.concept_type.toLowerCase();
  const blob = JSON.stringify(change.after ?? {}).toLowerCase();
  return (
    id.includes("PK") ||
    id.includes("6H") ||
    concept.includes("pk") ||
    (blob.includes("6") && (blob.includes("hour") || blob.includes("pk")))
  );
}

function pages(list?: { page: number }[] | null): string {
  if (!list?.length) return "—";
  return [...new Set(list.map((e) => e.page))].sort((a, b) => a - b).join(", ");
}

function quotes(
  list?: { quote?: string | null; page: number; section_id: string }[] | null,
  highlight?: boolean,
) {
  if (!list?.length) return <p className="empty">No evidence quotes.</p>;
  return (
    <ul className="evidence-list">
      {list.map((e, i) => (
        <li
          key={`${e.page}-${e.section_id}-${i}`}
          className={highlight && e.page === 8 ? "evidence-highlight" : undefined}
          data-page={e.page}
          data-section={e.section_id}
        >
          <span className="ev-meta">
            page {e.page} / {e.section_id}
          </span>
          <q>{e.quote || "(no quote)"}</q>
        </li>
      ))}
    </ul>
  );
}

export function RedlineView({
  changes,
  impact,
  loading,
  error,
  onRetry,
  recordingMode = false,
}: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [showPkEvidence, setShowPkEvidence] = useState(false);

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
      return {
        change: c,
        sites: [...sites],
        participants: [...participants],
        artifacts: [...artifacts],
        pk: isPkSixHour(c),
      };
    });
  }, [changes, impact]);

  // Prefer selecting the 6h PK change when entering recording mode with data.
  useEffect(() => {
    if (!recordingMode || selected || !enriched.length) return;
    const pk = enriched.find((e) => e.pk);
    if (pk) setSelected(pk.change.change_id);
  }, [recordingMode, enriched, selected]);

  const active =
    enriched.find((e) => e.change.change_id === selected)?.change ?? enriched[0]?.change ?? null;
  const activeMeta = enriched.find((e) => e.change.change_id === active?.change_id);
  const newEvidence =
    active?.new_evidence?.length ? active.new_evidence : active?.evidence ?? null;

  if (loading && !changes) return <LoadingState label="Loading semantic changes…" />;
  if (error && !changes) return <ErrorState error={error} onRetry={onRetry} />;
  if (!changes?.length) {
    return <p className="empty">No semantic changes yet — waiting for Trace stage.</p>;
  }

  return (
    <section
      className="view redline-view"
      aria-labelledby="redline-title"
      data-recording={recordingMode ? "true" : "false"}
    >
      <header className="view-header">
        <h2 id="redline-title">Semantic Redline</h2>
        <p>Evidence-linked concept changes — not a word-only diff.</p>
      </header>

      <div className="change-picker change-cards-row" role="tablist" aria-label="Semantic changes">
        {enriched.map(({ change, pk }) => (
          <button
            key={change.change_id}
            type="button"
            role="tab"
            aria-selected={active?.change_id === change.change_id}
            className={`chip change-card-chip${pk ? " pk-chip" : ""}`}
            onClick={() => {
              setSelected(change.change_id);
              if (pk) setShowPkEvidence(true);
            }}
          >
            <strong className="chip-id">{change.change_id}</strong>
            <span className="chip-concept">{change.concept_type}</span>
            <span className="chip-op">{change.operation}</span>
            {pk && <span className="chip-hint">6-hour PK · click for page 8 / SEC-PK</span>}
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
            <p className="change-id-line">
              <code>{active.change_id}</code>
            </p>
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
                <dt>Source pages</dt>
                <dd>
                  old {pages(active.old_evidence)} · new {pages(active.new_evidence)}
                </dd>
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
            {activeMeta?.pk && (
              <button
                type="button"
                className="btn secondary"
                onClick={() => setShowPkEvidence(true)}
              >
                Show page 8 / SEC-PK evidence
              </button>
            )}
            {active.explanation && <p className="explain">{active.explanation}</p>}
          </article>

          <div className="col evidence-col" data-pk-open={showPkEvidence && activeMeta?.pk ? "true" : "false"}>
            <h3>New protocol evidence</h3>
            {showPkEvidence && activeMeta?.pk && (
              <p className="evidence-callout" role="status">
                6-hour PK evidence — look for <strong>page 8 / SEC-PK</strong>
              </p>
            )}
            {quotes(newEvidence, showPkEvidence && Boolean(activeMeta?.pk))}
          </div>
        </div>
      )}
    </section>
  );
}
