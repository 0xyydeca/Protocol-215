import { useMemo, useState } from "react";
import { AURORA_TIMELINES, ROLLOUT_DAYS, type TimelineEvent } from "../data/auroraTimeline";
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
        <p>
          Fragmented site activation across Phoenix, Boston, and Seattle — synthetic twin only.
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

      <div className="timeline-rows">
        {AURORA_TIMELINES.map((site) => (
          <div key={site.siteId} className="timeline-row">
            <div className="timeline-site">
              <strong>{site.city}</strong>
              <span>{site.name}</span>
              {blockedSites.has(site.siteId) && (
                <span className="badge block">Rehearsal blocker</span>
              )}
            </div>
            <div
              className="timeline-track"
              role="img"
              aria-label={`${site.city} 215-day timeline`}
            >
              <div className="axis">
                <span>Day 0</span>
                <span>Day 215</span>
              </div>
              {site.events.map((ev) => {
                const start = Math.max(0, ev.dayStart);
                const end = Math.min(ROLLOUT_DAYS, Math.max(start + 1, ev.dayEnd));
                const left = (start / ROLLOUT_DAYS) * 100;
                const width = ((end - start) / ROLLOUT_DAYS) * 100;
                return (
                  <button
                    key={ev.id}
                    type="button"
                    className={`tl-event ${KIND_CLASS[ev.kind] ?? ""}`}
                    style={{ left: `${left}%`, width: `${Math.max(width, 1.2)}%` }}
                    aria-label={`${ev.label} days ${ev.dayStart}–${ev.dayEnd}`}
                    onClick={() => setSelected(ev)}
                  >
                    <span>{ev.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <aside className="timeline-detail" aria-live="polite">
        <h3>Event detail</h3>
        {!selected && <p className="empty">Select a timeline interval.</p>}
        {selected && (
          <dl className="kv">
            <div>
              <dt>Label</dt>
              <dd>{selected.label}</dd>
            </div>
            <div>
              <dt>Kind</dt>
              <dd>{selected.kind}</dd>
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
