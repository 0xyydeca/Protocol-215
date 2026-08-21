import type { RehearsalFinding } from "../api/types";
import { ErrorState, LoadingState } from "../components/States";

type Props = {
  findings: RehearsalFinding[] | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
};

export function FindingsView({ findings, loading, error, onRetry }: Props) {
  if (loading && !findings) return <LoadingState label="Loading rehearsal findings…" />;
  if (error && !findings) return <ErrorState error={error} onRetry={onRetry} />;
  if (!findings?.length) return <p className="empty">No findings yet — waiting for Rehearse.</p>;

  const primary =
    findings.find((f) => f.code.includes("P002") || f.participant_id === "P002") ?? null;
  const rest = findings.filter((f) => f !== primary);

  return (
    <section className="view findings-view" aria-labelledby="findings-title">
      <header className="view-header">
        <h2 id="findings-title">Rehearsal Findings</h2>
        <p>Concrete operational conflicts from the synthetic Trial Twin.</p>
      </header>

      {primary && (
        <article className="finding-primary" aria-label="Phoenix P002 primary finding">
          <div className="finding-head">
            <span className="badge block">{primary.severity}</span>
            <h3>Phoenix · {primary.participant_id ?? "P002"}</h3>
          </div>
          <p className="finding-summary">{primary.summary}</p>
          <dl className="kv dense">
            <div>
              <dt>Participant</dt>
              <dd>{primary.participant_id ?? "P002"}</dd>
            </div>
            <div>
              <dt>Dose</dt>
              <dd>{String(primary.details?.dose_time ?? "12:00")}</dd>
            </div>
            <div>
              <dt>6-hour sample</dt>
              <dd>{String(primary.details?.sample_time ?? "18:00")}</dd>
            </div>
            <div>
              <dt>Courier departure</dt>
              <dd>{String(primary.details?.courier_departure ?? "17:30")}</dd>
            </div>
            <div>
              <dt>Overnight storage</dt>
              <dd>
                {primary.details?.overnight_storage === true
                  ? "Validated storage available"
                  : "No validated overnight storage"}
              </dd>
            </div>
            <div>
              <dt>Result</dt>
              <dd>Activation blocked for this participant under current logistics</dd>
            </div>
          </dl>
        </article>
      )}

      <div className="finding-grid">
        {rest.map((f) => (
          <article key={f.finding_id} className="finding-card">
            <div className="finding-head">
              <span className={`badge ${f.severity}`}>{f.severity}</span>
              <code>{f.code}</code>
            </div>
            <p>{f.summary}</p>
            <p className="muted">
              {[f.site_id, f.participant_id].filter(Boolean).join(" · ") || "Study-wide"}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
