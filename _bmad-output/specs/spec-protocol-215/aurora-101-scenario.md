# AURORA-101 synthetic fixture

All content fictitious. Single polished scenario for the hackathon vertical slice.

## Study

**AURORA-101** — A Randomized, Double-Blind Study of Synthetic Investigational Compound AUR-101 in Healthy Adult Participants.

## Protocol v1.0

Screening; Day 1 dosing; PK sampling through four hours; standard ECG; two-hour post-dose fasting; standard sample-processing docs; central lab contact; site lab/courier requirements.

## Protocol v2.0 — exactly five controlled changes

| Change | Intended classification |
| --- | --- |
| Central laboratory contact updated | Green |
| Six-hour PK sample added | Amber |
| Post-dose fasting 2h → 4h | Amber |
| EDC field for sample-processing temperature added | Green for draft specification |
| Conditional repeat ECG added | Amber for operational planning; Red/prohibited for autonomous clinical activation |

## Sites

### SITE-001 Phoenix

Local approval complete; training complete; active v1.0; courier 5:30 p.m.; validated overnight storage **unavailable**; PK kits: 2; dosing commonly noon.

### SITE-002 Boston

Local approval complete; training **incomplete**; active v1.0; courier 8:00 p.m.; overnight storage available; PK kits: 10.

### SITE-003 Seattle

Local approval **pending**; training not started; active v1.0; courier 7:00 p.m.; overnight storage available; PK kits: 6.

## Participants

| ID | Site | Key state |
| --- | --- | --- |
| P001 | Phoenix | Consent 1.0; Day 1 **completed**; next Day 8 — completed Day 1 must never be retroactively altered |
| P002 | Phoenix | Consent 1.0; Day 1 **tomorrow**; dose noon → 6h PK at 6:00 p.m.; courier 5:30 p.m.; no overnight storage — **central demo conflict** |
| P003 | Boston | Consent 1.0; Day 1 in 3 days; approval ok; training incomplete |
| P004 | Boston | Not consented; screening planned; new protocol only after training+activation |
| P005 | Seattle | Consent 1.0; Day 1 next week; amendment cannot apply while approval pending |

## Expected findings (must detect)

1. Lab contact update may auto-complete (Green).
2. EDC change specification may be drafted automatically (Green).
3. Training tasks for Boston and Seattle.
4. Additional PK kits reserved.
5. Seattle remains v1.0 (approval pending).
6. Boston remains v1.0 until training complete.
7. P001 completed Day 1 unchanged.
8. P002 cannot safely undergo new 6h PK under current courier/storage.
9. Fasting and ECG changes need participant/safety-sensitive review.
10. No site activates v2.0 merely because global amendment exists.

## Central approval prompt

```text
BLOCKED DEPLOYMENT CONDITION
Site: SITE-001 — Phoenix
Participant: P002
Visit: Day 1

The amended six-hour PK sample is scheduled for 6:00 p.m.
The site courier departs at 5:30 p.m.
The site lacks validated overnight sample storage.

Recommended resolution:
Do not activate protocol version 2.0 for this participant until an
approved sample-handling plan or feasible visit schedule is available.
```
