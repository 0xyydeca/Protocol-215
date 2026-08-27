/**
 * Judge-facing scenario preview — explanatory only, not a fabricated workflow result.
 */
export function ScenarioPreview() {
  return (
    <aside className="scenario-preview" aria-label="Opening scenario preview">
      <p className="scenario-preview-label">Scenario preview · explanatory</p>
      <h3>Phoenix · P002</h3>
      <dl className="kv dense">
        <div>
          <dt>Dose</dt>
          <dd>12:00</dd>
        </div>
        <div>
          <dt>New 6-hour sample</dt>
          <dd>18:00</dd>
        </div>
        <div>
          <dt>Courier departure</dt>
          <dd>17:30</dd>
        </div>
        <div>
          <dt>Validated overnight storage</dt>
          <dd>unavailable</dd>
        </div>
      </dl>
      <p className="scenario-preview-note">
        Preview of the primary AURORA-101 conflict — not a live rehearsal result.
      </p>
    </aside>
  );
}

/**
 * Signature title for recording mode opening.
 */
export function SignatureTitle({ phase }: { phase: "problem" | "brand" }) {
  return (
    <div className="signature-opening recording-signature" data-phase={phase} aria-live="polite">
      <p className="signature-problem">
        <span className="days-215-block">215 DAYS</span>
        <span className="signature-fragment">of protocol-version fragmentation</span>
      </p>
      <div className="signature-brand">
        <p className="brand signature-brand-name">PROTOCOL 215</p>
        <h2 className="signature-tagline">Clinical Amendment Preflight</h2>
        <p className="signature-elevator">
          Rehearse every protocol amendment before it reaches a patient.
        </p>
      </div>
    </div>
  );
}
