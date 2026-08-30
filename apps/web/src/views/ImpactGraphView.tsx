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

const COL_W = 168;
const NODE_H = 36;
const NODE_GAP = 12;
const NODE_W = 148;
const TOP = 48;
const LEFT = 84;

function shortLabel(label: string, max = 20): string {
  const t = label.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

export function ImpactGraphView({ graph, loading, error, onRetry }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const layout = useMemo(() => {
    if (!graph) {
      return { nodes: [] as (ImpactNode & { x: number; y: number })[], width: 960, height: 420 };
    }
    const byLayer: Record<string, ImpactNode[]> = {};
    for (const layer of LAYERS) byLayer[layer] = [];
    for (const n of graph.nodes) {
      const layer = LAYERS.includes(n.layer as (typeof LAYERS)[number])
        ? n.layer
        : "operational_artifact";
      byLayer[layer] = byLayer[layer] ?? [];
      byLayer[layer].push(n);
    }
    const maxPerCol = Math.max(
      1,
      ...LAYERS.map((layer) => (byLayer[layer] ?? []).length),
    );
    const width = Math.max(960, LAYERS.length * COL_W + 48);
    // Grow with densest column so chips never overlap (Artifact often has 20+).
    const height = TOP + maxPerCol * (NODE_H + NODE_GAP) + 28;
    const placed: (ImpactNode & { x: number; y: number })[] = [];
    LAYERS.forEach((layer, col) => {
      const nodes = byLayer[layer] ?? [];
      nodes.forEach((n, i) => {
        placed.push({
          ...n,
          x: LEFT + col * COL_W,
          y: TOP + NODE_H / 2 + i * (NODE_H + NODE_GAP),
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
        <div className="impact-canvas">
          <svg
            className="impact-svg"
            viewBox={`0 0 ${layout.width} ${layout.height}`}
            width={layout.width}
            height={layout.height}
            role="img"
            aria-label="Layered impact graph"
          >
            {LAYERS.map((layer, i) => (
              <text
                key={layer}
                x={LEFT + i * COL_W}
                y={22}
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
                <title>{n.label}</title>
                <rect x={-NODE_W / 2} y={-NODE_H / 2} width={NODE_W} height={NODE_H} rx={3} />
                <text y={4} textAnchor="middle">
                  {shortLabel(n.label)}
                </text>
              </g>
            ))}
          </svg>
        </div>

        <aside className="impact-detail" aria-live="polite">
          <h3>Selection</h3>
          {!selected && <p className="empty">Select a node to inspect evidence and status.</p>}
          {selected && (
            <dl className="kv impact-kv">
              <div>
                <dt>Label</dt>
                <dd title={selected.label}>{selected.label}</dd>
              </div>
              <div>
                <dt>Layer</dt>
                <dd>{LAYER_LABELS[selected.layer] ?? selected.layer}</dd>
              </div>
              <div>
                <dt>Type</dt>
                <dd title={selected.artifact_type ?? undefined}>
                  {selected.artifact_type ?? "—"}
                </dd>
              </div>
              <div>
                <dt>Ref</dt>
                <dd title={selected.ref_id ?? undefined}>{selected.ref_id ?? "—"}</dd>
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
