# Architecture diagrams

## End-to-end amendment workflow

```text
Amendment received
        ↓
Validate and register documents
        ↓
Compile old and new protocols into Protocol IR
        ↓
Generate evidence-linked semantic changes
        ↓
Build downstream impact graph
        ↓
Load synthetic site and participant state
        ↓
Rehearse amendment in the Trial Twin
        ↓
Generate restricted action plan
        ↓
Apply deterministic risk-policy gate
        ↓
Execute low-risk actions
        ↓
Pause for sensitive-action approval
        ↓
Resume the same workflow
        ↓
Run operational invariants
        ↓
Generate Amendment Release Manifest
```

## Event-driven runtime

```text
[UI / API on Cloud Run]
        │ upload PDFs + start
        ▼
[Cloud Storage]  ← protocol objects (SHA-256 keyed)
[Firestore]       ← run record
        │ publish amendment.received
        ▼
[Pub/Sub]
        │
        ▼
[ADK Worker on Cloud Run]
  Gemini (IR, semantic diff, planning)
  Deterministic nodes (intake checks, impact graph, policy gate, invariants)
  Tools → synthetic Firestore collections
  Human confirmation ←→ UI (same invocation_id)
        │
        ▼
[Cloud Logging] + Amendment Release Manifest (GCS/Firestore)
```

## Conceptual analogy (software release → clinical amendment)

| Software-release concept | Protocol 215 equivalent |
| --- | --- |
| Source code | Clinical-trial protocol |
| Compiler | Protocol-to-structured-data extraction |
| Intermediate representation | Protocol IR |
| Semantic code diff | Semantic amendment diff |
| Dependency graph | Downstream study-artifact graph |
| Test environment | Synthetic Trial Twin |
| Integration tests | Operational invariants |
| Deployment gate | Clinical-risk policy gate |
| Staged rollout | Site-by-site protocol activation |
| Release manifest | Amendment Release Manifest |
