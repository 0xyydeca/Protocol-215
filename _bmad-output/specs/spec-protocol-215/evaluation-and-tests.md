# Evaluation, metrics, and required tests

## Hackathon judging weights

- Innovation and Operational Utility: 40%
- Architectural Discipline and Tech Stack: 30%
- Demo and Production Readiness: 30%

Must show: consequential workflow; autonomous execution (not summarization); amendment-as-release concept; temporal multi-site/participant simulation; concrete mutations; unsafe-rollout prevention; complete E2E result; event-driven design; workflow state; idempotent tools; schema-validated model output; deterministic auth; scoped tools; human approval; resumability; failure recovery; prompt-injection resistance; evidence grounding; immutable history; auditable mutations; cost controls; Cloud proof in ≤4 minutes.

## Internal target metrics (do not claim until measured)

| Metric | Target |
| --- | ---: |
| Recall for five gold-standard amendment changes | 100% in primary demo fixture |
| Recall across extended synthetic evaluation set | ≥95% |
| Executable changes with source evidence | 100% |
| High-risk actions executed without approval | 0 |
| Red actions executed | 0 |
| Duplicate mutations after event replay | 0 |
| Completed visits retroactively altered | 0 |
| Site-version invariant violations | 0 |
| Prompt-injection instructions followed | 0 |
| Successful workflow resume after interruption | 100% in controlled test |
| Unresolved contradictions in successful final manifest | 0 |

## Required tests

- Duplicate Pub/Sub delivery
- Worker crash after successful tool call
- Worker crash before event acknowledgement
- Malformed Gemini structured output
- Missing source evidence
- Contradictory protocol passages
- Prompt injection embedded in a PDF
- Model timeout
- Firestore transaction failure
- Approval submitted twice
- Approval sent with wrong invocation identifier
- State changed after an approval request
- Site capability data missing
- Participant visit already completed
- Same amendment submitted twice
- User rejects the recommended action
- Red action proposed by the model
- Unsupported protocol concept
