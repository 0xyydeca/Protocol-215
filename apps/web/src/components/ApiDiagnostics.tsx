import { apiOriginLabel, getApiConfig, type ApiConfigState } from "../api/config";

type Props = {
  config: ApiConfigState;
  healthOk: boolean | null;
  healthDetail?: string | null;
};

/** Small startup diagnostics: actual API origin (never secrets). */
export function ApiDiagnostics({ config, healthOk, healthDetail }: Props) {
  const origin = apiOriginLabel(config.ok ? config.apiBaseUrl : config.apiBaseUrl);
  const mode = config.ok ? config.mode : "misconfigured";
  return (
    <aside className="api-diagnostics" aria-label="API diagnostics">
      <p>
        <strong>API origin:</strong> <code>{origin}</code>
        <span className="api-diag-sep">·</span>
        <span>{mode}</span>
        <span className="api-diag-sep">·</span>
        <span data-health={healthOk == null ? "pending" : healthOk ? "ok" : "fail"}>
          /healthz {healthOk == null ? "…" : healthOk ? "ok" : "failed"}
        </span>
      </p>
      {!config.ok && <p className="api-diag-fail">{config.reason}</p>}
      {healthOk === false && healthDetail && <p className="api-diag-fail">{healthDetail}</p>}
      <p className="api-diag-note">
        Changing VITE_API_BASE_URL requires rebuilding the Vite app. Prefer the Cloud Run
        same-origin URL for the hackathon recording.
      </p>
    </aside>
  );
}

export function readApiConfig(): ApiConfigState {
  return getApiConfig();
}
