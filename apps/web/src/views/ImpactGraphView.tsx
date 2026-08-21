import { useMemo, useState } from "react";
import type { ImpactGraph, ImpactNode } from "../api/types";
import { ErrorState, LoadingState } from "../components/States";

type Props = {
  graph: ImpactGraph | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
};

const LAYERS = [
  "protocol_change",
  "operational_artifact",
  "site",
  "participant",
  "finding",
  "proposed_action",
] as const;

const LAYER_LABELS: Record<string, string> = {
  protocol_change: "Change",
  operational_artifact: "Artifact",
  site: "Site",
  participant: "Participant",
  finding: "Finding",
  proposed_action: "Action",
};

export function ImpactGraphView({ graph, loading, error, onRetry }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const layout = useMemo(() => {
    if (!graph) return { nodes: [] as (ImpactNode & { x: number; y: number })[], width: 900, height: 420 };
    const byLayer: Record<string, ImpactNode[]> = {};
    for (const layer of LAYERS) byLayer[layer] = [];
    for (const n of graph.nodes) {
      const layer = LAYERS.includes(n.layer as (typeof LAYERS)[number])
        ? n.layer
        : "operational_artifact";
      byLayer[layer] = byLayer[layer] ?? [];
      byLayer[layer].push(n);
    }
    const colW = 140;
    const width = Math.max(900, LAYERS.length * colW + 80);
    const height = 460;
    const placed: (ImpactNode & { x: number; y: number })[] = [];
    LAYERS.forEach((layer, col) => {
      const nodes = byLayer[layer] ?? [];
      const gap = height / (nodes.length + 1);
      nodes.forEach((n, i) => {
        placed.push({
          ...n,
          x: 60 + col * colW,
          y: gap * (i + 1),
        });
      });
    });
    return { nodes: placed, width, height };
  }, [graph]);

  const selected = layout.nodes.find((n) => n.node_id === selectedId) ?? null;
  const relatedEdges =
    graph?.edges.filter(
      (e) => e.from_node_id === selectedId || e.to_node_id === selectedId,
    ) ?? [];

  if (loading && !graph) return <LoadingState label="Loading impact graph…" />;
  if (error && !graph) return <ErrorState error={error} onRetry={onRetry} />;
  if (!graph?.nodes.length) {
    return <p className="empty">Impact graph not ready yet.</p>;
  }

  const pos = Object.fromEntries(layout.nodes.map((n) => [n.node_id, n]));

  return (
    <section className="view impact-view" aria-labelledby="impact-title">
      <header className="view-header">
        <h2 id="impact-title">Impact Graph</h2>
        <p>Stable layered trace: Change → Artifact → Site → Participant → Finding → Action.</p>
      </header>

      <div className="impact-layout">
        <svg
          className="impact-svg"
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="img"
          aria-label="Layered impact graph"
        >
          {LAYERS.map((layer, i) => (
            <text
              key={layer}
              x={60 + i * 140}
              y={24}
              textAnchor="middle"
              className="layer-title"
            >
              {LAYER_LABELS[layer]}
            </text>
          ))}
          {graph.edges.map((e) => {
            const a = pos[e.from_node_id];
            const b = pos[e.to_node_id];
            if (!a || !b) return null;
            return (
              <line
                key={e.edge_id}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                className="impact-edge"
              />
            );
          })}
          {layout.nodes.map((n) => (
            <g
              key={n.node_id}
              transform={`translate(${n.x}, ${n.y})`}
              className="impact-node"
              data-selected={selectedId === n.node_id}
              tabIndex={0}
              role="button"
              aria-label={`${LAYER_LABELS[n.layer] ?? n.layer}: ${n.label}`}
              onClick={() => setSelectedId(n.node_id)}
              onKeyDown={(ev) => {
                if (ev.key === "Enter" || ev.key === " ") {
                  ev.preventDefault();
                  setSelectedId(n.node_id);
                }
              }}
            >
              <rect x={-52} y={-16} width={104} height={32} rx={2} />
              <text y={5} textAnchor="middle">
                {n.label.length > 14 ? `${n.label.slice(0, 13)}…` : n.label}
              </text>
            </g>
          ))}
        </svg>

        <aside className="impact-detail" aria-live="polite">
          <h3>Selection</h3>
          {!selected && <p className="empty">Select a node to inspect evidence and status.</p>}
          {selected && (
            <dl className="kv">
              <div>
                <dt>Label</dt>
                <dd>{selected.label}</dd>
              </div>
              <div>
                <dt>Layer</dt>
                <dd>{LAYER_LABELS[selected.layer] ?? selected.layer}</dd>
              </div>
              <div>
                <dt>Type</dt>
                <dd>{selected.artifact_type}</dd>
              </div>
              <div>
                <dt>Ref</dt>
                <dd>{selected.ref_id ?? "—"}</dd>
              </div>
              <div>
                <dt>Edges</dt>
                <dd>{relatedEdges.length}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>Confirmed by backend graph</dd>
              </div>
            </dl>
          )}
        </aside>
      </div>
    </section>
  );
}
