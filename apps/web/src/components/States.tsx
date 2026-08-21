import { ApiError } from "../api/client";

type LoadingProps = {
  label?: string;
};

export function LoadingState({ label = "Loading…" }: LoadingProps) {
  return (
    <div className="state-panel loading" role="status" aria-busy="true" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

type ErrorProps = {
  error: Error;
  onRetry?: () => void;
};

export function ErrorState({ error, onRetry }: ErrorProps) {
  const api = error instanceof ApiError ? error : null;
  const retryable = api?.retryable ?? true;
  const terminal = api != null && !api.retryable;
  return (
    <div
      className={`state-panel error ${terminal ? "terminal" : "retryable"}`}
      role="alert"
      aria-live="assertive"
    >
      <h3>{terminal ? "Terminal error" : "Something went wrong"}</h3>
      <p>{error.message}</p>
      {api && (
        <p className="error-meta">
          {api.body.error_code} · correlation {api.body.correlation_id}
        </p>
      )}
      {retryable && onRetry && (
        <button type="button" className="btn secondary" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
