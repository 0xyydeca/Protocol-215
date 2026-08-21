# Protocol 215: Clinical Amendment Preflight

## Document Purpose

This document is the source input for planning and building **Protocol 215** for Google’s **All Things Agentic Hackathon**.

Protocol 215 must be developed as a newly created hackathon project using only synthetic protocols, synthetic sites, synthetic participants, and simulated trial systems. It is a production-minded proof of concept, not a validated clinical system.

The final implementation must prioritize one polished, reproducible, end-to-end workflow over broad but incomplete functionality.

---

# 1. Product Name and Tagline

## Product name

**Protocol 215: Clinical Amendment Preflight**

## Short application name

**Protocol 215**

## Tagline

> **Rehearse every protocol amendment before it reaches a patient.**

## One-sentence description

Protocol 215 is an autonomous clinical-trial amendment agent that interprets protocol changes, traces their operational consequences, rehearses the rollout across synthetic sites and participants, completes low-risk administrative work, and blocks safety-sensitive changes until appropriately approved.

## Elevator pitch

Clinical-trial protocol amendments rarely affect only one document. A single added procedure can change consent requirements, visit schedules, laboratory instructions, EDC forms, site training, specimen kits, storage requirements, courier logistics, and participant-specific instructions.

Protocol 215 treats an amendment like a software release. It compiles the old and amended protocols into structured study definitions, identifies the semantic changes, traces each change through downstream operations, and rehearses the rollout against a synthetic digital representation of every site and participant.

The agent automatically completes safe administrative work, creates the necessary operational tasks and specifications, pauses participant- or safety-sensitive actions for human authorization, resumes the same workflow after approval, and produces a verified amendment release manifest.

## Judge-facing hook

> **Most tools tell you what changed. Protocol 215 shows what will break—and resolves it before the amendment reaches a patient.**

## Conceptual analogy

Protocol 215 imports software-release engineering concepts into clinical-trial operations:

| Software-release concept    | Protocol 215 equivalent                |
| --------------------------- | -------------------------------------- |
| Source code                 | Clinical-trial protocol                |
| Compiler                    | Protocol-to-structured-data extraction |
| Intermediate representation | Protocol IR                            |
| Semantic code diff          | Semantic amendment diff                |
| Dependency graph            | Downstream study-artifact graph        |
| Test environment            | Synthetic Trial Twin                   |
| Integration tests           | Operational invariants                 |
| Deployment gate             | Clinical-risk policy gate              |
| Staged rollout              | Site-by-site protocol activation       |
| Release manifest            | Amendment Release Manifest             |

---

# 2. Clinical Amendment Problem

Clinical-trial protocols are operational blueprints. When a protocol is amended, the change may affect many connected documents, systems, site activities, and participant instructions.

A change such as adding a pharmacokinetic sample may affect:

* The Schedule of Activities
* Participant consent review
* Site training
* EDC forms and edit checks
* Laboratory manuals
* Sample labels and kits
* Processing instructions
* Freezer and centrifuge requirements
* Courier pickup schedules
* Bioanalytical transfer specifications
* Participant visit duration
* Participant fasting requirements
* Site-level amendment activation

These dependencies are often reviewed across different teams and systems. Each site may receive ethics approval, complete training, obtain supplies, and activate the amendment on a different date. Participants may also be at different points in the study and may have signed different consent versions.

A 2024 study based on 950 protocols and 2,188 amendments reported that the prevalence of Phase I–IV protocols with at least one amendment had increased from 57% to 76%, while the mean number of amendments per protocol had increased to 3.3. The average period from identifying the need for an amendment through the last oversight approval was 260 days, and investigative sites operated under different versions of the same protocol for an average of 215 days.

This creates several operational risks:

1. A procedure may be activated before local approval or training is complete.
2. A participant may receive instructions inconsistent with the consent version they signed.
3. A completed visit may be incorrectly retrofitted to the new protocol.
4. A laboratory requirement may be operationally impossible at a particular site.
5. An EDC or laboratory specification may remain based on the previous protocol.
6. Sites may receive conflicting instructions from different study artifacts.
7. A document comparison may identify changed words without identifying what must happen operationally.

Good Clinical Practice emphasizes protecting participant rights, safety, and well-being; ensuring reliable trial results; using risk-proportionate processes; and maintaining operationally feasible protocols.

## Existing workflow

A typical amendment may require people to:

1. Compare protocol versions.
2. Interpret the scientific and operational meaning of each change.
3. Identify affected documents and systems.
4. Determine which sites and participants are affected.
5. Coordinate updates across clinical operations, data management, laboratories, supplies, regulatory operations, and site management.
6. Wait for approvals and training.
7. Activate the amendment at different sites on different dates.
8. Verify that all connected instructions remain consistent.

## Product opportunity

Protocol 215 does not attempt to replace clinical judgment or regulatory authorization.

It provides an **operational preflight and controlled execution layer** that can:

* Structure the amendment
* Trace dependencies
* Simulate consequences
* Identify contradictions
* Complete low-risk administrative actions
* Route sensitive decisions for approval
* Verify the final synthetic rollout
* Preserve an evidence-linked audit trail

---

# 3. Meaning of “215”

The name **Protocol 215** refers to the finding that investigative sites operated under different versions of the same protocol for an average of **215 days**.

The number expresses the central problem:

> A protocol amendment is not activated everywhere at once.

Different sites may be waiting for:

* Institutional review board or ethics committee approval
* Regulatory approval
* Updated informed-consent materials
* Investigator acknowledgement
* Staff training
* EDC configuration
* Laboratory supplies
* Revised manuals
* Courier or storage arrangements

Protocol 215 models that fragmented transition explicitly.

## Opening line for the demonstration

> “Clinical-trial sites can operate under different protocol versions for an average of 215 days. Protocol 215 rehearses that transition before the amendment reaches a patient.”

## Signature visual

The interface should include a **215-day rollout timeline** that displays:

* Global amendment-release date
* Site-specific approval dates
* Site-training completion
* Site activation date
* Participant visits
* Applicable protocol version at each visit
* Blocked or inconsistent states

---

# 4. Hackathon Category

## Selected category

**The Taskmaster**

The official Taskmaster category asks entrants to build a complete workflow rather than a chatbot: the agent should take action, handle a messy multi-step process, send information to the right places, and demonstrate that it completed the work.

Protocol 215 belongs in this category because it:

* Begins from an amendment event
* Continues asynchronously without repeated user prompting
* Processes complex unstructured documents
* Creates structured study representations
* Reasons about operational consequences
* Mutates synthetic trial-system state
* Executes allowed low-risk tools
* Routes sensitive actions for authorization
* Resumes after approval
* Verifies the final result
* Produces a release manifest

## Why it is not a chatbot

The primary interface is not a conversational screen.

The user initiates a rehearsal, after which the agent:

1. Interprets the amendment.
2. Determines what is affected.
3. Simulates the rollout.
4. Selects permitted actions.
5. Executes safe actions.
6. Creates visible records in synthetic systems.
7. Pauses only at an explicit authorization boundary.
8. Resumes and verifies the final state.

Human approval is not used to manually orchestrate every step. It is a narrowly scoped safety control for participant- or safety-sensitive actions.

## Bring Your Own Friction

The project is based on a genuine clinical-development problem involving:

* Clinical pharmacology procedures
* Pharmacokinetic sampling
* Trial visit schedules
* Clinical data collection
* Site operations
* Laboratory workflows
* Participant-specific applicability
* Controlled clinical-system changes

The project therefore addresses a specialized real-world friction rather than a generic productivity task.

---

# 5. Core Workflow

## High-level workflow

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

## Detailed stages

### Stage 1: Amendment intake

The system accepts:

* Previous protocol PDF
* Amended protocol PDF
* Selected synthetic study-state scenario

It then:

* Verifies supported file type
* Applies file-size and page-count limits
* Calculates a SHA-256 hash for each document
* Creates a unique run identifier
* Stores the documents in Cloud Storage
* Checks whether the same document pair was previously processed
* Publishes an amendment event to Pub/Sub

This stage is deterministic.

### Stage 2: Protocol compilation

Gemini converts each protocol into a schema-validated **Protocol Intermediate Representation**, or Protocol IR.

The Protocol IR includes:

* Study identifier
* Protocol version and date
* Arms and cohorts
* Visits
* Procedures
* Timing windows
* PK samples
* Laboratory tests
* ECG and vital-sign assessments
* Eligibility criteria
* Treatment instructions
* Objectives and endpoints
* Participant restrictions
* Consent-relevant procedures
* Explicit operational requirements

Every extracted fact must contain:

* Source protocol version
* Source page
* Source section
* Confidence value
* Extraction status

No uncited fact may trigger an action.

### Stage 3: Semantic amendment diff

The system creates concept-level changes rather than a word-level redline.

Example:

```json
{
  "change_id": "CHG-002",
  "concept_type": "scheduled_activity",
  "operation": "ADD",
  "activity": "PK blood sample",
  "visit": "Day 1",
  "time_after_dose_hours": 6,
  "risk_candidate": "AMBER",
  "evidence": [
    {
      "protocol_version": "2.0",
      "page": 17,
      "section": "Schedule of Activities"
    }
  ],
  "confidence": 0.98
}
```

### Stage 4: Impact tracing

A deterministic dependency engine connects each change to downstream artifacts.

An added PK sample may affect:

```text
Added PK sample
   ├── Schedule of Activities
   ├── Informed-consent review
   ├── Site training
   ├── Sample kit
   ├── Sample labels
   ├── Laboratory manual
   ├── Processing window
   ├── Storage requirement
   ├── Courier schedule
   ├── EDC PK form
   ├── Edit checks
   └── Bioanalytical transfer specification
```

### Stage 5: Trial Twin rehearsal

The system loads synthetic:

* Sites
* Participants
* Approval states
* Training states
* Active protocol versions
* Consent versions
* Completed and scheduled visits
* Equipment
* Inventory
* Courier schedules
* Laboratory capabilities

The simulator evaluates every applicable combination of:

```text
Change × Site × Participant × Visit × Effective date
```

### Stage 6: Action planning

Gemini may propose actions only from a strict allowlist:

* `update_contact_directory`
* `create_site_training_task`
* `reserve_sample_kits`
* `create_lab_manual_change_request`
* `create_edc_change_specification`
* `create_courier_exception_task`
* `create_reconsent_review`
* `draft_participant_transition_plan`
* `request_human_approval`
* `generate_release_manifest`

The model cannot invent or directly execute arbitrary tools.

### Stage 7: Deterministic policy gate

Every proposed action is classified as:

* Green: may execute automatically
* Amber: requires human authorization
* Red: prohibited

The model may explain the proposed classification, but deterministic code makes the final authorization decision.

### Stage 8: Safe execution

Permitted tools mutate synthetic Firestore collections representing:

* Clinical trial management
* Site training
* EDC change control
* Laboratory operations
* Trial supplies
* Site approval status
* Amendment actions

Every write must include:

* Run identifier
* Action identifier
* Evidence reference
* Idempotency key
* Timestamp
* Tool identity
* Before state
* After state

### Stage 9: Pause and resume

When a sensitive action is reached:

* The workflow creates an approval request.
* The approval screen explains the issue and proposed resolution.
* No restricted mutation occurs.
* The workflow preserves its invocation identifier and state.
* Approval or rejection is returned to the same invocation.
* The workflow resumes from the suspended stage.

Google ADK supports human confirmation and resumable workflows. Its documentation notes that a confirmation response must use the same invocation identifier to resume the existing workflow rather than starting a new invocation.

### Stage 10: Verification

After execution, deterministic invariants confirm that:

* No site activated the amendment before approval.
* No site activated before required training.
* No completed visit was retroactively altered.
* No participant-affecting action occurred without authorization.
* Every new sample has a feasible collection, processing, storage, and shipment path.
* Every action is tied to protocol evidence.
* Duplicate event delivery did not duplicate actions.
* No prohibited action was executed.
* No unresolved operational contradiction remains.

### Stage 11: Amendment Release Manifest

The final manifest summarizes:

* Protocol versions and document hashes
* Detected changes
* Evidence coverage
* Affected artifacts
* Sites and participants evaluated
* Actions completed automatically
* Actions approved
* Actions blocked
* Remaining unresolved items
* Verification results
* Complete audit-event references

---

# 6. Synthetic Study Scenario

## Study

**AURORA-101**

**Title:** A Randomized, Double-Blind Study of Synthetic Investigational Compound AUR-101 in Healthy Adult Participants

All data, protocol content, sites, participants, and systems are fictitious.

## Protocol version 1.0

Version 1.0 includes:

* Screening
* Day 1 dosing
* PK sampling through four hours
* Standard ECG schedule
* Two-hour post-dose fasting
* Standard sample-processing documentation
* Central laboratory contact
* Site-level laboratory and courier requirements

## Protocol version 2.0

Version 2.0 introduces exactly five controlled changes:

| Change                                                  | Intended classification                                                       |
| ------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Central laboratory contact is updated                   | Green                                                                         |
| A six-hour PK sample is added                           | Amber                                                                         |
| Post-dose fasting is extended from two to four hours    | Amber                                                                         |
| An EDC field for sample-processing temperature is added | Green for draft specification                                                 |
| A conditional repeat ECG is added                       | Amber for operational planning; prohibited for autonomous clinical activation |

## Synthetic sites

### Site 001 — Phoenix

* Local approval: complete
* Amendment training: complete
* Active protocol: version 1.0
* Courier departure: 5:30 p.m.
* Validated overnight sample storage: unavailable
* Additional PK kits: two
* Participant dosing commonly begins at noon

### Site 002 — Boston

* Local approval: complete
* Amendment training: incomplete
* Active protocol: version 1.0
* Courier departure: 8:00 p.m.
* Validated overnight sample storage: available
* Additional PK kits: ten

### Site 003 — Seattle

* Local approval: pending
* Amendment training: not started
* Active protocol: version 1.0
* Courier departure: 7:00 p.m.
* Validated overnight sample storage: available
* Additional PK kits: six

## Synthetic participants

### Participant P001 — Phoenix

* Consent version: 1.0
* Day 1 visit: completed
* Next visit: Day 8
* The completed Day 1 visit must never be retroactively altered.

### Participant P002 — Phoenix

* Consent version: 1.0
* Day 1 visit: tomorrow
* Planned dosing time: noon
* The amended six-hour PK sample would occur at 6:00 p.m.
* The courier departs at 5:30 p.m.
* The site lacks validated overnight storage.

This is the central demonstration conflict.

### Participant P003 — Boston

* Consent version: 1.0
* Day 1 visit: in three days
* Local approval exists.
* Site training remains incomplete.

### Participant P004 — Boston

* Not yet consented
* Screening planned
* May use the new protocol only after site training and activation are complete.

### Participant P005 — Seattle

* Consent version: 1.0
* Day 1 visit: next week
* The amendment cannot apply while local approval remains pending.

## Expected agent findings

Protocol 215 should determine that:

1. The laboratory contact update may be completed automatically.
2. An EDC change specification may be drafted automatically.
3. Training tasks must be created for Boston and Seattle.
4. Additional PK kits should be reserved.
5. Seattle must remain on version 1.0 because approval is pending.
6. Boston must remain on version 1.0 until training is complete.
7. P001’s completed Day 1 visit must remain unchanged.
8. P002 cannot safely undergo the new six-hour PK procedure under the current courier and storage configuration.
9. The fasting and ECG changes require participant- or safety-sensitive review.
10. No site may activate version 2.0 merely because the global amendment exists.

## Central approval scenario

The workflow pauses on this finding:

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

---

# 7. Required Google Technology

The official hackathon rules require every submission to use:

1. Gemini 3.5 or newer through the Gemini API or Vertex AI
2. At least one approved Google agent framework
3. At least one Google Cloud infrastructure service

Protocol 215 will use the following stack.

## Runtime stack

### Gemini 3.5 or newer through Vertex AI

Gemini will perform:

* Multimodal protocol interpretation
* Protocol-to-IR extraction
* Semantic amendment comparison
* Ambiguous impact reasoning
* Restricted action planning
* Human-readable conflict explanation

The exact qualifying model identifier must be stored in an environment variable:

```text
GEMINI_MODEL=<qualifying Gemini 3.5-or-newer model>
```

Do not hard-code an unverified model identifier.

### Google Agent Development Kit

Google ADK will provide:

* Workflow orchestration
* Agent and deterministic-node composition
* Tool invocation
* Workflow state
* Human confirmation
* Pause and resume
* Event history

### Cloud Run

Cloud Run will host:

* Frontend
* API
* Asynchronous ADK worker

Minimum instances should be set to zero and maximum instances should be capped to control costs. The hackathon resources explicitly recommend scaling to zero, using instance caps, setting budget alerts, and turning off unnecessary services after recording deployment evidence.

### Pub/Sub

Pub/Sub will carry:

```text
amendment.received
```

events from the intake service to the asynchronous worker.

The system must tolerate duplicate event delivery through idempotent actions.

### Firestore

Firestore will store:

* Runs
* Protocol versions
* Changes
* Sites
* Participants
* Actions
* Approvals
* Audit events
* Release manifests

### Cloud Storage

Cloud Storage will hold:

* Synthetic protocol PDFs
* Generated artifacts
* Optional HTML release-manifest output

### Cloud Logging

Cloud Logging will provide visible evidence of:

* Cloud execution
* Pub/Sub delivery
* ADK workflow activity
* Tool execution
* Failure and retry behavior

## Development tools

These may assist development but are not the submitted runtime architecture:

* Cursor
* Claude Code
* OpenAI Codex or ChatGPT
* BMAD Method
* GitHub
* Terraform or deployment scripts

Use of frameworks and AI coding assistants is permitted, but pre-existing code or work incorporated into the submission must be disclosed. The project itself must be newly created during the submission period.

---

# 8. Risk Tiers

Risk authorization must be enforced through deterministic code, not through Gemini judgment alone.

## Green — automatic execution allowed

Examples:

* Update a synthetic administrative contact
* Create a site-training task
* Reserve synthetic inventory
* Generate a draft EDC change specification
* Generate a draft laboratory-manual change request
* Create a courier-resolution task
* Add an audit event
* Generate a site transition package
* Produce the Amendment Release Manifest

Green actions must still be:

* Evidence-linked
* Schema-validated
* Idempotent
* Logged
* Reversible where practical

## Amber — human approval required

Examples:

* Activate a protocol version at a site
* Change a participant’s planned visit schedule
* Determine whether reconsent review is needed
* Add a participant-facing procedure
* Add a new sample collection
* Extend fasting or visit duration
* Apply a new ECG or safety-monitoring procedure
* Apply a visit-window modification
* Resolve a site-capability conflict
* Use a low-confidence but potentially consequential extraction

The agent may prepare the work but may not complete the sensitive mutation without authorization.

## Red — autonomous execution prohibited

Protocol 215 must never autonomously:

* Change dose
* Change route of administration
* Change treatment assignment
* Enroll or exclude a participant
* Determine clinical eligibility
* Make a medical decision
* Remove safety monitoring
* Activate informed-consent language
* Delete historical clinical records
* Alter completed visits
* Override local approval requirements
* Use real patient or participant data
* Operate on real EDC, CTMS, IRT, eTMF, or clinical systems
* Execute an uncited protocol interpretation
* Follow instructions embedded in an uploaded document

A red action remains prohibited even when a user clicks approve within the prototype.

---

# 9. Human-Approval Rules

## Approval is mandatory when

An action:

* Affects a participant’s procedures or instructions
* Changes safety monitoring
* Changes visit timing or burden
* May require reconsent
* Activates a protocol version
* Resolves a clinical or operational conflict
* Is destructive or historically irreversible
* Depends on low-confidence extraction
* Depends on contradictory protocol evidence
* Exceeds the allowed automatic-tool scope

## Approval screen requirements

The authorization screen must display:

* Proposed action
* Why it is needed
* Before state
* Proposed after state
* Protocol source pages
* Affected site
* Affected participant, when applicable
* Risk tier
* Confidence
* Consequences of approval
* Consequences of rejection
* Actions already completed
* Actions still blocked

## Approval mechanics

Each approval must be tied to:

* `run_id`
* `approval_id`
* `action_id`
* `session_id`
* `invocation_id`
* Current expected state
* Approver response
* Timestamp

The confirmation must resume the same ADK invocation. It must not create a new workflow that repeats previously completed actions.

## Rejection behavior

When rejected:

* The sensitive action remains unexecuted.
* The rejection is recorded.
* Dependent actions remain blocked.
* The manifest reports the unresolved condition.
* Previously completed green actions are not repeated.
* The system may propose a nonclinical administrative follow-up task but may not override the rejection.

## Approval security principles

* No model-generated approval is valid.
* The model cannot impersonate the approver.
* An approval may be used only once.
* Duplicate submissions must not duplicate execution.
* Approval must be rejected if the underlying state changed after the request was created.
* The policy gate runs again immediately before execution.
* The application records evidence and outcomes, not hidden chain-of-thought reasoning.

---

# 10. Seven User-Interface Screens

The product should not default to a chatbot interface.

## Screen 1: Amendment Launch

Purpose:

* Upload old and amended protocol PDFs
* Select the synthetic study scenario
* Start the rehearsal
* View recent runs

Visible information:

* File names
* File hashes
* Protocol versions
* Run identifier
* Workflow status

Primary action:

```text
Start Amendment Preflight
```

## Screen 2: Semantic Redline

Layout:

```text
Old protocol | Semantic change card | New protocol
```

Each change card displays:

* Change type
* Before state
* After state
* Risk candidate
* Confidence
* Supporting page and section
* Affected artifact count
* Affected site count
* Affected participant count

Selecting a change should navigate both documents to the relevant evidence.

## Screen 3: Impact Graph

The graph connects:

```text
Protocol change
    ↓
Operational artifacts
    ↓
Sites
    ↓
Participants
    ↓
Proposed actions
```

Selecting a node shows:

* Why it is affected
* Source evidence
* Required action
* Execution status
* Approval requirement

## Screen 4: The 215-Day Rollout Timeline

Display a horizontal timeline for Phoenix, Boston, and Seattle.

Show:

* Global amendment release
* Local approval
* Training
* Activation
* Participant visits
* Applicable protocol version
* Blocked states

Example:

```text
Phoenix  [v1]──Approval──Training──Conflict────────[v2 blocked]
Boston   [v1]──Approval────────Training pending────[v2 blocked]
Seattle  [v1]────────────Local approval pending────[v2 blocked]
```

## Screen 5: Rehearsal Findings

Display concrete operational findings rather than generic summaries.

Each finding includes:

* Severity
* Site
* Participant
* Visit
* Conflict
* Protocol evidence
* Operational evidence
* Recommended resolution

The Phoenix courier and storage conflict is the primary finding.

## Screen 6: Action Ledger and Approval

Three columns:

### Completed automatically

* Contact updated
* Training tasks created
* Kits reserved
* EDC specification generated

### Waiting for approval

* Participant transition plan
* Six-hour PK sample resolution
* Fasting and ECG implementation review

### Blocked

* Seattle activation before approval
* Boston activation before training
* Clinical actions prohibited by policy

The same screen contains the approval panel for the central conflict.

## Screen 7: Amendment Release Manifest

Display:

* Protocol versions
* Document hashes
* Run identifier
* Changes detected
* Evidence coverage
* Sites evaluated
* Participants evaluated
* Actions completed
* Actions approved
* Actions rejected
* Actions blocked
* Invariant results
* Final rollout status

The manifest should be downloadable as JSON and available as a print-ready HTML report.

---

# 11. Evaluation Criteria

## Hackathon scoring alignment

The official judging weights are:

* **Innovation and Operational Utility: 40%**
* **Architectural Discipline and Tech Stack: 30%**
* **Demo and Production Readiness: 30%**

## Innovation and operational utility

Protocol 215 should demonstrate:

* A consequential real-world workflow
* Autonomous execution rather than document summarization
* A distinctive “clinical amendment as software release” concept
* Temporal simulation across sites and participants
* Concrete system actions
* Prevention of unsafe or infeasible rollout
* A complete beginning-to-end result

## Architectural discipline

The implementation must demonstrate:

* Event-driven decoupling
* Explicit workflow state
* Idempotent tool execution
* Schema-validated model output
* Deterministic authorization
* Strictly scoped tools
* Human approval
* Resumability
* Failure recovery
* Prompt-injection resistance
* Evidence grounding
* Immutable historical state
* Auditable mutations
* Cost controls

## Demo and production readiness

The demonstration must visibly prove:

* The application is running on Google Cloud.
* Pub/Sub triggers the workflow.
* Gemini and ADK perform the analysis and orchestration.
* Firestore records change as actions execute.
* The agent pauses for approval.
* The same invocation resumes.
* Invariants run.
* A release manifest is generated.

The rules require a demonstration no longer than four minutes, a repository, reproducible setup instructions, an architecture diagram, and visible proof that the backend ran on Google Cloud.

## Internal target metrics

These are implementation targets and must not be presented as achieved until measured:

| Metric                                                 |                       Target |
| ------------------------------------------------------ | ---------------------------: |
| Recall for five gold-standard amendment changes        | 100% in primary demo fixture |
| Recall across extended synthetic evaluation set        |                 At least 95% |
| Executable changes with source evidence                |                         100% |
| High-risk actions executed without approval            |                            0 |
| Red actions executed                                   |                            0 |
| Duplicate mutations after event replay                 |                            0 |
| Completed visits retroactively altered                 |                            0 |
| Site-version invariant violations                      |                            0 |
| Prompt-injection instructions followed                 |                            0 |
| Successful workflow resume after interruption          |      100% in controlled test |
| Unresolved contradictions in successful final manifest |                            0 |

## Required tests

The project must test:

* Duplicate Pub/Sub delivery
* Worker crash after a successful tool call
* Worker crash before event acknowledgement
* Malformed Gemini structured output
* Missing source evidence
* Contradictory protocol passages
* Prompt injection embedded in a PDF
* Model timeout
* Firestore transaction failure
* Approval submitted twice
* Approval sent with the wrong invocation identifier
* State changed after an approval request
* Site capability data missing
* Participant visit already completed
* Same amendment submitted twice
* User rejects the recommended action
* Red action proposed by the model
* Unsupported protocol concept

---

# 12. Explicitly Excluded Functionality

The hackathon version will not include:

* Real clinical-trial data
* Protected health information
* Real patient or participant information
* Employer protocols, documents, systems, or vendor data
* Real CTMS integration
* Real EDC integration
* Real IRT or RTSM integration
* Real eTMF integration
* Real ethics-committee or regulatory submission
* Medical recommendations
* Eligibility decisions
* Treatment assignment
* Dose selection
* Dose or route changes
* Automatic consent activation
* Full CDISC USDM implementation
* Formal regulatory validation
* GxP qualification
* Production deployment in a regulated trial
* Multi-tenant SaaS architecture
* Subscription billing
* Complex user authentication
* Enterprise agent registry
* Long-term cross-study memory
* A general-purpose clinical chatbot
* Support for every protocol type
* Multiple polished amendment scenarios
* Autonomous modification of generated SQL in real systems
* Autonomous external email or messaging
* Claims that the prototype is safe for real clinical use

The project will use one carefully controlled, fully synthetic scenario to demonstrate the concept.

---

# 13. Four-Minute Demonstration Sequence

The video must show one continuous, understandable execution. The official rules state that videos should not exceed four minutes and that only the first four minutes may be evaluated.

## 0:00–0:20 — Establish the problem

Visual:

```text
215 DAYS
of protocol-version fragmentation
```

Narration:

> “Clinical-trial sites can operate under different protocol versions for an average of 215 days. A seemingly small amendment can affect consent, visits, laboratories, data collection, site training, supplies, and participant instructions.”

Then reveal:

```text
PROTOCOL 215
Clinical Amendment Preflight
```

## 0:20–0:38 — Explain the concept

Show:

```text
Compile → Trace → Rehearse → Act → Approve → Verify
```

Narration:

> “Protocol 215 treats a clinical-trial amendment like a software release. It rehearses every operational consequence before the amendment reaches a patient.”

## 0:38–1:00 — Trigger the workflow

Show:

* Cloud Run `.run` URL
* Version 1 and version 2 protocol upload
* Start Amendment Preflight
* Pub/Sub event
* Cloud Run or ADK execution log

Narration:

> “Uploading the amendment publishes an event and starts an asynchronous Google ADK workflow on Google Cloud.”

## 1:00–1:35 — Show semantic changes

Show the five change cards:

1. Laboratory contact
2. Six-hour PK sample
3. Fasting extension
4. Processing-temperature field
5. Conditional ECG

Select the PK change and show the source pages.

Narration:

> “Gemini does not merely compare words. It compiles both protocols into structured study definitions and identifies evidence-linked operational changes.”

## 1:35–2:10 — Show the Trial Twin

Open the 215-day timeline.

Show:

* Phoenix approved and trained
* Boston approved but not trained
* Seattle awaiting approval
* Participant visits and consent versions

Narration:

> “The same amendment does not apply everywhere at once. Protocol 215 rehearses it against each site’s approval, training, equipment, inventory, courier logistics, active protocol version, and every participant’s visit history.”

## 2:10–2:40 — Show autonomous action

Open the Action Ledger.

Show live completion of:

* Laboratory contact update
* Training-task creation
* PK-kit reservation
* EDC change specification
* Laboratory change request

Show Firestore mutations or backend logs.

Narration:

> “The agent completes permitted operational work rather than merely recommending it.”

## 2:40–3:10 — Reveal the central conflict

Show P002 at Phoenix.

Visual:

```text
6-hour PK sample: 6:00 p.m.
Courier departure: 5:30 p.m.
Validated overnight storage: unavailable
```

Narration:

> “For this participant, the new six-hour sample occurs after the courier leaves, and the site lacks validated overnight storage. The amendment would create an infeasible sample workflow.”

## 3:10–3:30 — Approval and resume

Show:

* Evidence-linked approval request
* Approve a synthetic operational resolution
* Same invocation identifier
* Workflow resumes

Narration:

> “Participant- and safety-sensitive actions cannot bypass the deterministic policy gate. After authorization, the same workflow resumes without repeating completed actions.”

## 3:30–3:48 — Verification

Show invariants turning green:

```text
0 unauthorized high-risk actions
0 duplicate actions
0 retroactively changed visits
0 site-version conflicts
100% executable actions evidence-linked
```

Narration:

> “Protocol 215 verifies the deployed synthetic state rather than assuming that execution succeeded.”

## 3:48–4:00 — Final release manifest

Show the Amendment Release Manifest.

Closing narration:

> “Most tools tell you what changed. Protocol 215 shows what will break, completes the safe work, and proves the amendment is ready to deploy.”

---

# Final Product Definition

Protocol 215 succeeds when one user can upload two synthetic protocol versions and then observe an autonomous Google Cloud workflow that:

1. Extracts evidence-linked semantic changes.
2. Traces their downstream operational consequences.
3. Rehearses the rollout across synthetic sites and participants.
4. Detects a real operational contradiction.
5. Completes permitted administrative actions.
6. Blocks sensitive or prohibited actions.
7. Pauses for one meaningful authorization.
8. Resumes without duplicating prior work.
9. Verifies the resulting state.
10. Produces an auditable Amendment Release Manifest.

The project must remain focused on this complete vertical slice until it works reliably, is deployed on Google Cloud, and can be demonstrated clearly in less than four minutes.
