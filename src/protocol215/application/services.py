"""Application services using ports only (no Google Cloud SDK)."""

from __future__ import annotations

from typing import Any

from protocol215.application.hashing import build_idempotency_key, sha256_hex
from protocol215.domain.enums import ApprovalStatus, WorkflowStatus
from protocol215.domain.models import (
    ActionExecution,
    ActionProposal,
    AmendmentReleaseManifest,
    ApprovalDecision,
    ApprovalRequest,
    DomainEvent,
    EvidenceReference,
    ParticipantState,
    ProtocolArtifactRecord,
    ProtocolIR,
    RehearsalFinding,
    SemanticChange,
    SessionMetadata,
    SiteState,
    WorkflowRun,
)
from protocol215.ports import (
    ActionPlanner,
    AuditLog,
    Clock,
    EventBus,
    IdentifierGenerator,
    ObjectStore,
    ProtocolCompiler,
    StateStore,
)
from protocol215.simulator.twin import load_participants, load_sites
from protocol215.tools.executor import ToolExecutor


class AmendmentAppService:
    """Orchestrates run lifecycle against local/cloud-agnostic ports."""

    def __init__(
        self,
        *,
        state: StateStore,
        objects: ObjectStore,
        events: EventBus,
        audit: AuditLog,
        compiler: ProtocolCompiler,
        planner: ActionPlanner,
        clock: Clock,
        ids: IdentifierGenerator,
    ) -> None:
        self.state = state
        self.objects = objects
        self.events = events
        self.audit = audit
        self.compiler = compiler
        self.planner = planner
        self.clock = clock
        self.ids = ids
        self.tools = ToolExecutor(state=state, audit=audit, clock=clock, ids=ids)

    def create_run(
        self,
        *,
        study_id: str,
        from_version: str,
        to_version: str,
        run_id: str | None = None,
    ) -> WorkflowRun:
        rid = run_id or self.ids.new_id("run-")
        now = self.clock.now()
        compiler_model = getattr(self.compiler, "model_id", None) or getattr(
            self.compiler, "model", None
        )
        run = WorkflowRun(
            run_id=rid,
            study_id=study_id,
            from_version=from_version,
            to_version=to_version,
            status=WorkflowStatus.CREATED,
            created_at=now,
            updated_at=now,
            last_checkpoint_at=now,
            correlation_id=rid,
            compiler_model=str(compiler_model) if compiler_model else None,
        )
        self.state.save_run(run)
        self.state.save_session_metadata(
            SessionMetadata(
                run_id=run.run_id,
                session_id=self.ids.new_id("sess-"),
                invocation_id=None,
                cursor="CREATED",
            )
        )
        self.audit.append(
            run_id=run.run_id,
            event_type="run.created",
            actor="system",
            decision_summary=f"Created run for {study_id} {from_version}->{to_version}",
            input_payload={
                "study_id": study_id,
                "from_version": from_version,
                "to_version": to_version,
            },
            output_payload={"run_id": run.run_id},
        )
        return run

    def register_protocol_artifact(
        self,
        *,
        run_id: str,
        version: str,
        pdf_bytes: bytes,
        object_key: str | None = None,
    ) -> ProtocolArtifactRecord:
        key = object_key or f"runs/{run_id}/protocols/v{version}.pdf"
        self.objects.put_bytes(key, pdf_bytes, content_type="application/pdf")
        digest = sha256_hex(pdf_bytes)
        artifact = ProtocolArtifactRecord(
            run_id=run_id,
            version=version,
            object_key=key,
            content_sha256=digest,
            registered_at=self.clock.now(),
        )
        self.state.save_protocol_artifact(artifact)
        ir = self.compiler.compile(pdf_bytes=pdf_bytes, version_hint=version)
        self.state.save_protocol_ir(run_id, version, ir)
        run = self.state.get_run(run_id)
        if run is not None:
            keys = dict(run.object_keys)
            keys[version] = key
            self.state.save_run(run.model_copy(update={"object_keys": keys}))
        self.audit.append(
            run_id=run_id,
            event_type="protocol.registered",
            actor="system",
            decision_summary=f"Registered protocol artifact v{version}",
            input_payload={"version": version, "sha256": digest},
            output_payload={"object_key": key},
        )
        return artifact

    def publish_run_event(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> DomainEvent | None:
        key = idempotency_key or f"{run_id}:event:{event_type}:publish"
        event_id = self.ids.new_id("evt-")
        if not self.state.record_processed_event(key, event_id):
            self.audit.append(
                run_id=run_id,
                event_type="event.replay_observed",
                actor="system",
                decision_summary=f"Duplicate event suppressed: {event_type}",
                input_payload={"idempotency_key": key, "event_type": event_type},
                output_payload={"suppressed": True},
                idempotency_key=key,
            )
            return None
        event = DomainEvent(
            event_id=event_id,
            event_type=event_type,
            run_id=run_id,
            payload=payload or {},
            created_at=self.clock.now(),
            idempotency_key=key,
        )
        self.events.publish(event)
        self.audit.append(
            run_id=run_id,
            event_type="event.published",
            actor="system",
            decision_summary=f"Published {event_type}",
            input_payload={"event_type": event_type},
            output_payload={"event_id": event_id},
            idempotency_key=key,
        )
        return event

    def load_synthetic_study_state(
        self, run_id: str
    ) -> tuple[list[SiteState], list[ParticipantState]]:
        sites = load_sites()
        participants = load_participants()
        self.state.save_sites(run_id, sites)
        self.state.save_participants(run_id, participants)
        self.audit.append(
            run_id=run_id,
            event_type="twin.loaded",
            actor="system",
            decision_summary="Loaded synthetic study state",
            output_payload={
                "sites": len(sites),
                "participants": len(participants),
            },
        )
        return sites, participants

    def save_findings(self, run_id: str, findings: list[RehearsalFinding]) -> None:
        self.state.save_findings(run_id, findings)
        self.audit.append(
            run_id=run_id,
            event_type="findings.saved",
            actor="system",
            decision_summary=f"Saved {len(findings)} findings",
            output_payload={"count": len(findings)},
        )

    def save_changes(self, run_id: str, changes: list[SemanticChange]) -> None:
        self.state.save_changes(run_id, changes)

    def propose_actions(self, run_id: str) -> list[ActionProposal]:
        run = self._require_run(run_id)
        changes = self.state.list_changes(run_id)
        findings = self.state.list_findings(run_id)
        proposals = self.planner.propose(run=run, changes=changes, findings=findings)
        self.audit.append(
            run_id=run_id,
            event_type="actions.proposed",
            actor="planner",
            decision_summary=f"Proposed {len(proposals)} actions via port",
            output_payload={"proposal_ids": [p.proposal_id for p in proposals]},
        )
        return proposals

    def execute_idempotent_action(
        self,
        *,
        run_id: str,
        proposal: ActionProposal,
        protocol_version: str,
        target_id: str,
        approved: bool = False,
        mutation: dict[str, Any] | None = None,
    ) -> ActionExecution:
        run = self._require_run(run_id)
        args = dict(proposal.args)
        if mutation:
            # Callers may pass mutation fields (e.g. email) without duplicating in args.
            for key, value in mutation.items():
                args.setdefault(key, value)
        args.setdefault("run_id", run_id)
        keyed = proposal.model_copy(
            update={
                "args": args,
                "idempotency_key": proposal.idempotency_key
                or build_idempotency_key(
                    run_id=run_id,
                    action_type=proposal.tool_name,
                    target_id=target_id,
                    protocol_version=protocol_version,
                ),
            }
        )
        result = self.tools.execute_proposal(
            proposal=keyed,
            protocol_version=protocol_version,
            approved=approved,
        )
        action = self.state.get_action_by_idempotency_key(result.idempotency_key)
        if action is None:
            # Should not happen — executor always persists
            raise RuntimeError("tool executor did not persist action")
        _ = run
        return action.model_copy(update={"replayed": result.replayed})

    def create_approval_request(
        self,
        *,
        run_id: str,
        action_ids: list[str],
        state_hash: str,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=self.ids.new_id("apr-"),
            run_id=run_id,
            action_ids=action_ids,
            status=ApprovalStatus.PENDING,
            state_hash=state_hash,
            created_at=self.clock.now(),
        )
        self.state.save_approval_request(request)
        run = self._require_run(run_id)
        self.state.save_run(run.model_copy(update={"status": WorkflowStatus.AWAITING_APPROVAL}))
        self.audit.append(
            run_id=run_id,
            event_type="approval.requested",
            actor="system",
            decision_summary="Created approval request",
            output_payload={"approval_id": request.approval_id, "action_ids": action_ids},
        )
        return request

    def record_approval(
        self,
        *,
        approval_id: str,
        decision: ApprovalStatus,
        actor: str = "synthetic_operator",
    ) -> ApprovalDecision:
        request = self.state.get_approval_request(approval_id)
        if request is None:
            raise KeyError(approval_id)
        if decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError("decision must be APPROVED or REJECTED")
        recorded = ApprovalDecision(
            approval_id=approval_id,
            decision=decision,
            decided_at=self.clock.now(),
            actor=actor,
        )
        self.state.save_approval_decision(recorded)
        self.state.save_approval_request(request.model_copy(update={"status": decision}))
        self.audit.append(
            run_id=request.run_id,
            event_type="approval.recorded",
            actor=actor,
            decision_summary=f"Approval {decision.value}",
            input_payload={"approval_id": approval_id},
            output_payload={"decision": decision.value},
        )
        return recorded

    def generate_manifest(
        self,
        *,
        run_id: str,
        study_id: str,
        from_version: str,
        to_version: str,
    ) -> AmendmentReleaseManifest:
        from protocol215.application.invariants import evaluate_all

        actions = self.state.list_actions(run_id)
        sites = self.state.list_sites(run_id)
        participants = self.state.list_participants(run_id)
        if not sites or not participants:
            loaded_sites, loaded_participants = self.load_synthetic_study_state(run_id)
            sites = sites or loaded_sites
            participants = participants or loaded_participants
        invariants = evaluate_all(sites=sites, participants=participants, actions=actions)
        manifest = AmendmentReleaseManifest(
            run_id=run_id,
            study_id=study_id,
            from_version=from_version,
            to_version=to_version,
            changes=self.state.list_changes(run_id),
            findings=self.state.list_findings(run_id),
            actions=actions,
            invariants=invariants,
            generated_at=self.clock.now(),
            sites_evaluated_count=len(sites),
            participants_evaluated_count=len(participants),
        )
        self.state.save_manifest(manifest)
        key = f"runs/{run_id}/manifest.json"
        self.objects.put_bytes(
            key,
            manifest.model_dump_json().encode("utf-8"),
            content_type="application/json",
        )
        self.audit.append(
            run_id=run_id,
            event_type="manifest.generated",
            actor="system",
            decision_summary="Generated amendment release manifest",
            output_payload={"object_key": key, "invariant_count": len(invariants)},
        )
        return manifest

    def get_protocol_ir(self, run_id: str, version: str) -> ProtocolIR | None:
        return self.state.get_protocol_ir(run_id, version)

    def _require_run(self, run_id: str) -> WorkflowRun:
        run = self.state.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return run


def evidence(page: int, section: str) -> list[EvidenceReference]:
    return [EvidenceReference(page=page, section_id=section)]
