/** Detect judge-facing recording mode (?demo=1). */
export function isRecordingMode(search: string = window.location.search): boolean {
  const params = new URLSearchParams(search);
  const v = params.get("demo");
  return v === "1" || v === "true" || v === "yes";
}
