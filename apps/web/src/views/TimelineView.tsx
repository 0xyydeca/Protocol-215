import { useMemo, useState } from "react";
import {
  AURORA_TIMELINES,
  ROLLOUT_DAYS,
  type TimelineEvent,
  type TimelineLane,
} from "../data/auroraTimeline";
import type { RehearsalFinding } from "../api/types";

type Props = {
  findings: RehearsalFinding[] | null;
};

const KIND_CLASS: Record<string, string> = {
  global_release: "kind-release",
  local_approval: "kind-approval",
  training: "kind-training",
  activation: "kind-activation",
  visit: "kind-visit",
  protocol_version: "kind-version",
  blocked: "kind-blocked",
};

const LANE_ORDER: TimelineLane[] = ["process", "block", "visit", "version"];

const MARKERS = [
  { day: 30, label: "Phoenix v2" },
  { day: 95, label: "Boston v2" },
  { day: 180, label: "Seattle v2" },
];

function pct(day: number): number {
  return (Math.max(0, Math.min(ROLLOUT_DAYS, day)) / ROLLOUT_DAYS) * 100;
}

export function TimelineView({ findings }: Props) {
  const [selected, setSelected] = useState<TimelineEvent | null>(null);

  const blockedSites = useMemo(() => {
    const set = new Set<string>();
    for (const f of findings ?? []) {
      if (f.severity === "blocker" && f.site_id) set.add(f.site_id);
    }
    return set;
  }, [findings]);

  return (
    <section className="view timeline-view" aria-labelledby="timeline-title">
      <header className="view-header">
        <h2 id="timeline-title">215-Day Rollout Timeline</h2>
        <p className="timeline-stat" role="note">
          Sites can operate under <strong>different protocol versions for an average of 215
          days</strong>
          {" — "}
          Phoenix flips at Day 30, Boston at Day 95, Seattle at Day 180.
        </p>
        <p>
          Fragmented activation across Phoenix, Boston, and Seattle — synthetic twin only. Process
          gates and version bands are separate from rehearsal blockers.
        </p>
      </header>

      <div className="timeline-legend" aria-hidden="true">
        <span className="kind-release">Release</span>
        <span className="kind-approval">Approval</span>
        <span className="kind-training">Training</span>
        <span className="kind-activation">Activation</span>
        <span className="kind-visit">Visit</span>
        <span className="kind-version">Protocol version</span>
        <span className="kind-blocked">Blocked</span>
      </div>

      <div className="timeline-marker-rail" aria-hidden="true">
        <div className="timeline-marker-spacer" />
        <div className="timeline-marker-track">
          {MARKERS.map((m) => (
            <div key={m.day} className="timeline-marker" style={{ left: `${pct(m.day)}%` }}>
              <span className="timeline-marker-line" />
              <span className="timeline-marker-label">
                D{m.day}
                <br />
                {m.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="timeline-rows">
        {AURORA_TIMELINES.map((site) => {
          const byLane = LANE_ORDER.map((lane) => ({
            lane,
            events: site.events.filter((e) => e.lane === lane),
          })).filter((g) => g.events.length > 0);

          return (
            <div key={site.siteId} className="timeline-row">
              <div className="timeline-site">
                <strong>{site.city}</strong>
                <span>{site.name}</span>
                <span className="timeline-site-flip">v2 @ Day {site.v2ActivationDay}</span>
                {blockedSites.has(site.siteId) && (
                  <span className="badge block">Rehearsal blocker</span>
                )}
              </div>
              <div
                className="timeline-track"
                role="img"
                aria-label={`${site.city} 215-day timeline; v2.0 from day ${site.v2ActivationDay}`}
              >
                <div className="timeline-lanes">
                  {byLane.map(({ lane, events }) => (
                    <div key={lane} className={`timeline-lane lane-${lane}`}>
                      {events.map((ev) => {
                        const start = Math.max(0, ev.dayStart);
                        const end = Math.min(ROLLOUT_DAYS, Math.max(start + 1, ev.dayEnd));
                        const left = pct(start);
                        const width = pct(end) - left;
                        return (
                          <button
                            key={ev.id}
                            type="button"
                            className={[
                              "tl-event",
                              KIND_CLASS[ev.kind] ?? "",
                              ev.kind === "protocol_version" && ev.label.startsWith("v2")
                                ? "is-v2"
                                : "",
                              ev.kind === "protocol_version" && ev.label.startsWith("v1")
                                ? "is-v1"
                                : "",
                            ]
                              .filter(Boolean)
                              .join(" ")}
                            style={{
                              left: `${left}%`,
                              width: `${Math.max(width, lane === "visit" ? 1.4 : 2.2)}%`,
                            }}
                            aria-label={`${ev.label} days ${ev.dayStart}–${ev.dayEnd}`}
                            title={`${ev.label} (Day ${ev.dayStart}–${ev.dayEnd})`}
                            onClick={() => setSelected(ev)}
                          >
                            <span>{ev.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
                <div className="axis">
                  <span>Day 0</span>
                  <span>Day 215</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <aside className="timeline-detail" aria-live="polite">
        <h3>Event detail</h3>
        {!selected && (
          <p className="empty">
            Select a colored interval — version bands show when each site leaves v1.0; red bands are
            rehearsal blockers.
          </p>
        )}
        {selected && (
          <dl className="kv">
            <div>
              <dt>Label</dt>
              <dd>{selected.label}</dd>
            </div>
            <div>
              <dt>Kind</dt>
              <dd>{selected.kind.replaceAll("_", " ")}</dd>
            </div>
            <div>
              <dt>Days</dt>
              <dd>
                {selected.dayStart} → {selected.dayEnd}
              </dd>
            </div>
            {selected.detail && (
              <div>
                <dt>Detail</dt>
                <dd>{selected.detail}</dd>
              </div>
            )}
          </dl>
        )}
      </aside>
    </section>
  );
}
