"""Firestore StateStore adapter with transactional helpers."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from protocol215.domain.enums import ApprovalStatus
from protocol215.domain.models import (
    ActionExecution,
    AmendmentReleaseManifest,
    ApprovalDecision,
    ApprovalRequest,
    AuditEvent,
    ParticipantState,
    ProtocolArtifactRecord,
    ProtocolIR,
    RehearsalFinding,
    SemanticChange,
    SessionMetadata,
    SiteState,
    WorkflowRun,
)

T = TypeVar("T", bound=BaseModel)


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _load(model_cls: type[T], data: dict[str, Any] | None) -> T | None:
    if not data:
        return None
    # Strip Firestore-only metadata
    cleaned = {k: v for k, v in data.items() if not k.startswith("_")}
    return model_cls.model_validate(cleaned)


class FirestoreStateStore:
    """
    Cloud Firestore adapter behind StateStore.

    PDFs are never stored here — only metadata references (object keys / hashes).
    Uses Application Default Credentials; no JSON keys in code.
    """

    def __init__(
        self,
        *,
        project: str | None = None,
        database: str | None = None,
        client: Any | None = None,
        use_server_timestamps: bool = True,
    ) -> None:
        self.project = project
        self.use_server_timestamps = use_server_timestamps
        if client is not None:
            self._db = client
        else:
            from google.cloud import firestore  # lazy

            kwargs: dict[str, Any] = {}
            if project:
                kwargs["project"] = project
            if database:
                kwargs["database"] = database
            self._db = firestore.Client(**kwargs)
        self._firestore_module: Any | None = None

    def _fs(self) -> Any:
        if self._firestore_module is None:
            from google.cloud import firestore

            self._firestore_module = firestore
        return self._firestore_module

    def _server_ts(self) -> Any:
        if not self.use_server_timestamps:
            return None
        return self._fs().SERVER_TIMESTAMP

    def _with_meta(self, payload: dict[str, Any]) -> dict[str, Any]:
        ts = self._server_ts()
        if ts is not None:
            payload = {**payload, "_updated_at": ts}
        return payload

    # --- runs ---
    def save_run(self, run: WorkflowRun) -> None:
        self._db.collection("runs").document(run.run_id).set(self._with_meta(_dump(run)))

    def get_run(self, run_id: str) -> WorkflowRun | None:
        snap = self._db.collection("runs").document(run_id).get()
        return _load(WorkflowRun, snap.to_dict() if snap.exists else None)

    def list_runs(self) -> list[WorkflowRun]:
        out: list[WorkflowRun] = []
        for snap in self._db.collection("runs").stream():
            loaded = _load(WorkflowRun, snap.to_dict())
            if loaded:
                out.append(loaded)
        return sorted(out, key=lambda r: r.created_at)

    # --- protocol artifacts / versions (metadata only — no PDF bytes) ---
    def save_protocol_artifact(self, artifact: ProtocolArtifactRecord) -> None:
        doc_id = f"{artifact.run_id}__{artifact.version}"
        self._db.collection("protocol_versions").document(doc_id).set(
            self._with_meta(_dump(artifact))
        )

    def list_protocol_artifacts(self, run_id: str) -> list[ProtocolArtifactRecord]:
        out: list[ProtocolArtifactRecord] = []
        for snap in (
            self._db.collection("protocol_versions")
            .where("run_id", "==", run_id)
            .stream()
        ):
            loaded = _load(ProtocolArtifactRecord, snap.to_dict())
            if loaded:
                out.append(loaded)
        return sorted(out, key=lambda a: a.version)

    def save_protocol_ir(self, run_id: str, version: str, ir: ProtocolIR) -> None:
        doc_id = f"{run_id}__{version}"
        self._db.collection("protocol_irs").document(doc_id).set(
            self._with_meta({"run_id": run_id, "version": version, "ir": _dump(ir)})
        )

    def get_protocol_ir(self, run_id: str, version: str) -> ProtocolIR | None:
        snap = self._db.collection("protocol_irs").document(f"{run_id}__{version}").get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        return _load(ProtocolIR, data.get("ir"))

    # --- lists stored as single docs ---
    def save_changes(self, run_id: str, changes: list[SemanticChange]) -> None:
        self._db.collection("changes").document(run_id).set(
            self._with_meta({"run_id": run_id, "items": [_dump(c) for c in changes]})
        )

    def list_changes(self, run_id: str) -> list[SemanticChange]:
        snap = self._db.collection("changes").document(run_id).get()
        if not snap.exists:
            return []
        return [
            SemanticChange.model_validate(i) for i in (snap.to_dict() or {}).get("items", [])
        ]

    def save_sites(self, run_id: str, sites: list[SiteState]) -> None:
        self._db.collection("sites").document(run_id).set(
            self._with_meta({"run_id": run_id, "items": [_dump(s) for s in sites]})
        )

    def list_sites(self, run_id: str) -> list[SiteState]:
        snap = self._db.collection("sites").document(run_id).get()
        if not snap.exists:
            return []
        return [SiteState.model_validate(i) for i in (snap.to_dict() or {}).get("items", [])]

    def save_participants(self, run_id: str, participants: list[ParticipantState]) -> None:
        self._db.collection("participants").document(run_id).set(
            self._with_meta({"run_id": run_id, "items": [_dump(p) for p in participants]})
        )

    def list_participants(self, run_id: str) -> list[ParticipantState]:
        snap = self._db.collection("participants").document(run_id).get()
        if not snap.exists:
            return []
        return [
            ParticipantState.model_validate(i)
            for i in (snap.to_dict() or {}).get("items", [])
        ]

    def save_findings(self, run_id: str, findings: list[RehearsalFinding]) -> None:
        self._db.collection("findings").document(run_id).set(
            self._with_meta({"run_id": run_id, "items": [_dump(f) for f in findings]})
        )

    def list_findings(self, run_id: str) -> list[RehearsalFinding]:
        snap = self._db.collection("findings").document(run_id).get()
        if not snap.exists:
            return []
        return [
            RehearsalFinding.model_validate(i)
            for i in (snap.to_dict() or {}).get("items", [])
        ]

    # --- actions + idempotency ---
    def save_action(self, run_id: str, action: ActionExecution) -> None:
        """Non-transactional write; prefer save_action_idempotent for mutations."""
        self._db.collection("actions").document(f"{run_id}__{action.execution_id}").set(
            self._with_meta({**_dump(action), "run_id": run_id})
        )
        self._db.collection("action_keys").document(action.idempotency_key).set(
            self._with_meta(
                {
                    "run_id": run_id,
                    "execution_id": action.execution_id,
                    "idempotency_key": action.idempotency_key,
                }
            )
        )

    def get_action_by_idempotency_key(self, idempotency_key: str) -> ActionExecution | None:
        key_snap = self._db.collection("action_keys").document(idempotency_key).get()
        if not key_snap.exists:
            return None
        data = key_snap.to_dict() or {}
        run_id = data.get("run_id")
        execution_id = data.get("execution_id")
        if not run_id or not execution_id:
            return None
        snap = self._db.collection("actions").document(f"{run_id}__{execution_id}").get()
        return _load(ActionExecution, snap.to_dict() if snap.exists else None)

    def list_actions(self, run_id: str) -> list[ActionExecution]:
        out: list[ActionExecution] = []
        for snap in self._db.collection("actions").where("run_id", "==", run_id).stream():
            loaded = _load(ActionExecution, snap.to_dict())
            if loaded:
                out.append(loaded)
        return out

    def save_action_idempotent(self, run_id: str, action: ActionExecution) -> ActionExecution:
        """Transaction: return existing action if idempotency key already written."""
        firestore = self._fs()
        key_ref = self._db.collection("action_keys").document(action.idempotency_key)
        action_ref = self._db.collection("actions").document(
            f"{run_id}__{action.execution_id}"
        )

        @firestore.transactional
        def _txn(transaction: Any) -> ActionExecution:
            key_snap = key_ref.get(transaction=transaction)
            if key_snap.exists:
                existing_meta = key_snap.to_dict() or {}
                existing_ref = self._db.collection("actions").document(
                    f"{existing_meta['run_id']}__{existing_meta['execution_id']}"
                )
                existing_snap = existing_ref.get(transaction=transaction)
                loaded = _load(ActionExecution, existing_snap.to_dict())
                if loaded is not None:
                    return loaded.model_copy(update={"replayed": True})
            payload = self._with_meta({**_dump(action), "run_id": run_id})
            transaction.set(action_ref, payload)
            transaction.set(
                key_ref,
                self._with_meta(
                    {
                        "run_id": run_id,
                        "execution_id": action.execution_id,
                        "idempotency_key": action.idempotency_key,
                    }
                ),
            )
            return action

        return _txn(self._db.transaction())

    # --- approvals ---
    def save_approval_request(self, request: ApprovalRequest) -> None:
        self._db.collection("approvals").document(request.approval_id).set(
            self._with_meta(_dump(request))
        )

    def get_approval_request(self, approval_id: str) -> ApprovalRequest | None:
        snap = self._db.collection("approvals").document(approval_id).get()
        return _load(ApprovalRequest, snap.to_dict() if snap.exists else None)

    def list_approval_requests(self, run_id: str) -> list[ApprovalRequest]:
        out: list[ApprovalRequest] = []
        for snap in self._db.collection("approvals").where("run_id", "==", run_id).stream():
            loaded = _load(ApprovalRequest, snap.to_dict())
            if loaded:
                out.append(loaded)
        return out

    def save_approval_decision(self, decision: ApprovalDecision) -> None:
        self._db.collection("approval_decisions").document(decision.approval_id).set(
            self._with_meta(_dump(decision))
        )

    def get_approval_decision(self, approval_id: str) -> ApprovalDecision | None:
        snap = self._db.collection("approval_decisions").document(approval_id).get()
        return _load(ApprovalDecision, snap.to_dict() if snap.exists else None)

    def consume_approval(
        self,
        *,
        approval_id: str,
        decision: ApprovalDecision,
        expected_state_version: int,
        run_id: str,
    ) -> ApprovalRequest:
        """
        Transaction: verify pending + expected state_version, then consume.
        Raises ValueError on stale / already consumed.
        """
        firestore = self._fs()
        apr_ref = self._db.collection("approvals").document(approval_id)
        run_ref = self._db.collection("runs").document(run_id)
        dec_ref = self._db.collection("approval_decisions").document(approval_id)

        @firestore.transactional
        def _txn(transaction: Any) -> ApprovalRequest:
            apr_snap = apr_ref.get(transaction=transaction)
            if not apr_snap.exists:
                raise ValueError("approval not found")
            request = ApprovalRequest.model_validate(
                {k: v for k, v in (apr_snap.to_dict() or {}).items() if not k.startswith("_")}
            )
            if request.status != ApprovalStatus.PENDING:
                raise ValueError("approval already consumed")
            if request.expected_state_version != expected_state_version:
                raise ValueError("expected state version mismatch")
            run_snap = run_ref.get(transaction=transaction)
            if run_snap.exists:
                run = WorkflowRun.model_validate(
                    {
                        k: v
                        for k, v in (run_snap.to_dict() or {}).items()
                        if not k.startswith("_")
                    }
                )
                if run.state_version != expected_state_version:
                    raise ValueError("run state version changed")
            updated = request.model_copy(update={"status": decision.decision})
            transaction.set(apr_ref, self._with_meta(_dump(updated)))
            transaction.set(dec_ref, self._with_meta(_dump(decision)))
            return updated

        return _txn(self._db.transaction())

    # --- audit ---
    def append_audit_event(self, event: AuditEvent) -> None:
        doc_id = f"{event.run_id}__{event.sequence_number:08d}"
        self._db.collection("audit_events").document(doc_id).set(
            self._with_meta(_dump(event))
        )

    def list_audit_events(self, run_id: str) -> list[AuditEvent]:
        out: list[AuditEvent] = []
        for snap in (
            self._db.collection("audit_events").where("run_id", "==", run_id).stream()
        ):
            loaded = _load(AuditEvent, snap.to_dict())
            if loaded:
                out.append(loaded)
        return sorted(out, key=lambda e: e.sequence_number)

    # --- manifest ---
    def save_manifest(self, manifest: AmendmentReleaseManifest) -> None:
        self._db.collection("manifests").document(manifest.run_id).set(
            self._with_meta(_dump(manifest))
        )

    def get_manifest(self, run_id: str) -> AmendmentReleaseManifest | None:
        snap = self._db.collection("manifests").document(run_id).get()
        return _load(AmendmentReleaseManifest, snap.to_dict() if snap.exists else None)

    def finalize_manifest(
        self, manifest: AmendmentReleaseManifest, *, expected_state_version: int
    ) -> AmendmentReleaseManifest:
        """Transaction: write manifest only when run state_version matches."""
        firestore = self._fs()
        run_ref = self._db.collection("runs").document(manifest.run_id)
        man_ref = self._db.collection("manifests").document(manifest.run_id)

        @firestore.transactional
        def _txn(transaction: Any) -> AmendmentReleaseManifest:
            run_snap = run_ref.get(transaction=transaction)
            if not run_snap.exists:
                raise ValueError("run not found")
            run = WorkflowRun.model_validate(
                {k: v for k, v in (run_snap.to_dict() or {}).items() if not k.startswith("_")}
            )
            if run.state_version != expected_state_version:
                raise ValueError("state version mismatch during manifest finalization")
            existing = man_ref.get(transaction=transaction)
            if existing.exists:
                loaded = _load(AmendmentReleaseManifest, existing.to_dict())
                if loaded is not None:
                    return loaded
            transaction.set(man_ref, self._with_meta(_dump(manifest)))
            return manifest

        return _txn(self._db.transaction())

    # --- sessions ---
    def save_session_metadata(self, meta: SessionMetadata) -> None:
        self._db.collection("workflow_sessions").document(meta.run_id).set(
            self._with_meta(_dump(meta))
        )

    def get_session_metadata(self, run_id: str) -> SessionMetadata | None:
        snap = self._db.collection("workflow_sessions").document(run_id).get()
        return _load(SessionMetadata, snap.to_dict() if snap.exists else None)

    # --- event dedupe ---
    def record_processed_event(self, idempotency_key: str, event_id: str) -> bool:
        firestore = self._fs()
        ref = self._db.collection("processed_events").document(idempotency_key)

        @firestore.transactional
        def _txn(transaction: Any) -> bool:
            snap = ref.get(transaction=transaction)
            if snap.exists:
                return False
            transaction.set(
                ref,
                self._with_meta({"event_id": event_id, "idempotency_key": idempotency_key}),
            )
            return True

        return bool(_txn(self._db.transaction()))
