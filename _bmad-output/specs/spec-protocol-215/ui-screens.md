# Seven UI screens

Primary interface is operational UI, not a chatbot.

## Screen 1 — Amendment Launch

Upload old/new protocol PDFs; select AURORA scenario; start rehearsal; list recent runs. Show file names, hashes, protocol versions, `run_id`, workflow status. Primary action: `Start Amendment Preflight`.

## Screen 2 — Semantic Redline

Layout: `Old protocol | Semantic change card | New protocol`. Cards: change type, before/after, risk candidate, confidence, page/section, affected artifact/site/participant counts. Selecting a change navigates both documents to evidence.

## Screen 3 — Impact Graph

`Protocol change → operational artifacts → sites → participants → proposed actions`. Node detail: why affected, evidence, required action, execution status, approval requirement.

## Screen 4 — 215-Day Rollout Timeline

Horizontal timeline for Phoenix, Boston, Seattle: global release, local approval, training, activation, participant visits, applicable protocol version, blocked states.

Example:

```text
Phoenix  [v1]──Approval──Training──Conflict────────[v2 blocked]
Boston   [v1]──Approval────────Training pending────[v2 blocked]
Seattle  [v1]────────────Local approval pending────[v2 blocked]
```

## Screen 5 — Rehearsal Findings

Concrete findings: severity, site, participant, visit, conflict, protocol evidence, operational evidence, recommended resolution. Primary finding: Phoenix P002 courier/storage conflict.

## Screen 6 — Action Ledger and Approval

Columns: Completed automatically | Waiting for approval | Blocked. Same screen hosts approval panel for the central conflict (fields per `risk-policy.md`).

Demo Completed examples: contact updated; training tasks; kits reserved; EDC specification. Waiting: participant transition; 6h PK resolution; fasting/ECG review. Blocked: Seattle/Boston activation; policy-prohibited clinical actions.

## Screen 7 — Amendment Release Manifest

Versions, hashes, run id, changes, evidence coverage, sites/participants evaluated, actions by outcome, invariant results, final rollout status. Download JSON + print-ready HTML.
