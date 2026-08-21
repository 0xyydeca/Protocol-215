"""Deterministic tool executor — validate, authorize, mutate, audit."""

from __future__ import annotations

from typing import Any

from protocol215.application.hashing import build_idempotency_key, hash_payload
from protocol215.domain.enums import ActionStatus, RiskTier
from protocol215.domain.models import ActionExecution, ActionProposal, EvidenceReference
from protocol215.policy.matrix import authorize_proposal, is_executable
from protocol215.ports import AuditLog, Clock, IdentifierGenerator, StateStore
from protocol215.tools.handlers import HANDLERS
from protocol215.tools.registry import ALLOWED_ACTION_NAMES
from protocol215.tools.results import ToolResult
from protocol215.tools.schemas import TOOL_ARGS_BY_NAME, BaseToolArgs


class ToolExecutionError(Exception):
    def __init__(self, message: str, *, blocked_reason: str | None = None) -> None:
        super().__init__(message)
        self.blocked_reason = blocked_reason


class ToolExecutor:
    """Runs allowlisted tools against synthetic state only."""

    def __init__(
        self,
        *,
        state: StateStore,
        audit: AuditLog,
        clock: Clock,
        ids: IdentifierGenerator,
    ) -> None:
        self.state = state
        self.audit = audit
        self.clock = clock
        self.ids = ids
        # Per-run scratch for non-site synthetic artifacts
        self._scratch: dict[str, dict[str, Any]] = {}

    def scratch_for(self, run_id: str) -> dict[str, Any]:
        return self._scratch.setdefault(run_id, {})

    def parse_args(self, tool_name: str, raw: dict[str, Any]) -> BaseToolArgs:
        if tool_name not in ALLOWED_ACTION_NAMES:
            raise ToolExecutionError(
                f"unknown tool not on allowlist: {tool_name}",
                blocked_reason="unknown_tool",
            )
        cls = TOOL_ARGS_BY_NAME[tool_name]
        payload = {"tool_name": tool_name, **raw}
        return cls.model_validate(payload)

    def execute_proposal(
        self,
        *,
        proposal: ActionProposal,
        protocol_version: str,
        approved: bool = False,
    ) -> ToolResult:
        run_id = proposal.args.get("run_id") or ""
        # Prefer explicit run_id from args; callers must set it.
        if not run_id:
            raise ToolExecutionError("run_id required in tool args")

        key = proposal.idempotency_key or build_idempotency_key(
            run_id=run_id,
            action_type=proposal.tool_name,
            target_id=proposal.site_id
            or proposal.participant_id
            or proposal.proposal_id,
            protocol_version=protocol_version,
        )

        existing = self.state.get_action_by_idempotency_key(key)
        if existing is not None:
            self.audit.append(
                run_id=run_id,
                event_type="tool.replay_observed",
                actor="tool_executor",
                decision_summary=f"Idempotent replay for {proposal.tool_name}",
                evidence=list(proposal.evidence),
                input_payload={"idempotency_key": key},
                output_payload={"execution_id": existing.execution_id},
                action_id=existing.execution_id,
                tool_id=proposal.tool_name,
                idempotency_key=key,
            )
            return ToolResult(
                tool_name=proposal.tool_name,
                status=existing.status,
                authorized_tier=existing.authorized_tier,
                executed=existing.executed,
                replayed=True,
                idempotency_key=key,
                execution_id=existing.execution_id,
                before=existing.before or {},
                after=existing.after or {},
                before_hash=hash_payload(existing.before or {}),
                after_hash=hash_payload(existing.after or {}),
                message="replayed",
            )

        # Re-run deterministic policy immediately before mutation.
        tier = authorize_proposal(proposal)
        if tier == RiskTier.RED or proposal.tool_name not in ALLOWED_ACTION_NAMES:
            return self._block(
                proposal=proposal,
                run_id=run_id,
                key=key,
                tier=RiskTier.RED,
                reason="red_or_unknown_tool",
                approved=approved,
            )

        if not proposal.evidence:
            return self._block(
                proposal=proposal,
                run_id=run_id,
                key=key,
                tier=RiskTier.RED,
                reason="uncited_action",
                approved=approved,
            )

        if not is_executable(tier, approved=approved):
            return self._block(
                proposal=proposal,
                run_id=run_id,
                key=key,
                tier=tier,
                reason="awaiting_approval" if tier == RiskTier.AMBER else "not_executable",
                approved=approved,
            )

        # Validate typed args
        raw_args = {
            "run_id": run_id,
            "protocol_version": protocol_version,
            "evidence": [e.model_dump() for e in proposal.evidence],
            "change_ids": list(proposal.change_ids),
            "site_id": proposal.site_id,
            "participant_id": proposal.participant_id,
            "rationale": proposal.rationale,
            **{k: v for k, v in proposal.args.items() if k != "run_id"},
        }
        try:
            args = self.parse_args(proposal.tool_name, raw_args)
        except Exception as exc:  # noqa: BLE001 — validation fail-closed
            return self._block(
                proposal=proposal,
                run_id=run_id,
                key=key,
                tier=tier,
                reason=f"schema_validation:{exc}",
                approved=approved,
            )

        if not args.evidence:
            return self._block(
                proposal=proposal,
                run_id=run_id,
                key=key,
                tier=RiskTier.RED,
                reason="evidence_required",
                approved=approved,
            )

        handler = HANDLERS[proposal.tool_name]
        sites = list(self.state.list_sites(run_id))
        scratch = self.scratch_for(run_id)

        # Transaction-like: mutate locally, persist together, audit last.
        before, after, new_sites = handler(args=args, sites=sites, scratch=scratch)
        before_hash = hash_payload(before)
        after_hash = hash_payload(after)

        execution_id = self.ids.new_id("act-")
        now = self.clock.now()
        action = ActionExecution(
            execution_id=execution_id,
            proposal_id=proposal.proposal_id,
            tool_name=proposal.tool_name,
            status=ActionStatus.EXECUTED,
            authorized_tier=tier,
            evidence=list(proposal.evidence),
            idempotency_key=key,
            site_id=proposal.site_id,
            participant_id=proposal.participant_id,
            before=before,
            after=after,
            approved=approved,
            executed=True,
            executed_at=now,
            replayed=False,
        )

        # Persist site updates + action atomically (best-effort transaction).
        if hasattr(self.state, "begin"):
            self.state.begin()  # type: ignore[attr-defined]
        try:
            if new_sites is not sites:
                self.state.save_sites(run_id, new_sites)
            self.state.save_action(run_id, action)
            run = self.state.get_run(run_id)
            if run is not None:
                keys = list(run.completed_idempotency_keys)
                if key not in keys:
                    keys.append(key)
                self.state.save_run(run.model_copy(update={"completed_idempotency_keys": keys}))
            if hasattr(self.state, "commit"):
                self.state.commit()  # type: ignore[attr-defined]
        except Exception:
            if hasattr(self.state, "rollback"):
                self.state.rollback()  # type: ignore[attr-defined]
            raise

        audit_event = self.audit.append(
            run_id=run_id,
            event_type="tool.executed",
            actor="tool_executor",
            decision_summary=f"Executed {proposal.tool_name}",
            evidence=list(proposal.evidence),
            input_payload={
                "proposal_id": proposal.proposal_id,
                "args": args.model_dump(mode="json"),
                "before_hash": before_hash,
            },
            output_payload={
                "execution_id": execution_id,
                "after_hash": after_hash,
                "after": after,
            },
            action_id=execution_id,
            tool_id=proposal.tool_name,
            idempotency_key=key,
        )

        return ToolResult(
            tool_name=proposal.tool_name,
            status=ActionStatus.EXECUTED,
            authorized_tier=tier,
            executed=True,
            replayed=False,
            idempotency_key=key,
            execution_id=execution_id,
            before=before,
            after=after,
            before_hash=before_hash,
            after_hash=after_hash,
            audit_event_id=audit_event.event_id,
            message="executed",
        )

    def _block(
        self,
        *,
        proposal: ActionProposal,
        run_id: str,
        key: str,
        tier: RiskTier,
        reason: str,
        approved: bool,
    ) -> ToolResult:
        execution_id = self.ids.new_id("act-")
        before: dict[str, Any] = {"blocked": False}
        after: dict[str, Any] = {"blocked": True, "reason": reason, "tier": tier.value}
        # Even if UI approved, RED stays blocked.
        if tier == RiskTier.RED and approved:
            after["approval_ignored"] = True
        action = ActionExecution(
            execution_id=execution_id,
            proposal_id=proposal.proposal_id,
            tool_name=proposal.tool_name,
            status=ActionStatus.BLOCKED,
            authorized_tier=tier,
            evidence=list(proposal.evidence),
            idempotency_key=key,
            site_id=proposal.site_id,
            participant_id=proposal.participant_id,
            before=before,
            after=after,
            approved=approved,
            executed=False,
            executed_at=None,
            replayed=False,
        )
        self.state.save_action(run_id, action)
        audit_event = self.audit.append(
            run_id=run_id,
            event_type="tool.blocked",
            actor="tool_executor",
            decision_summary=f"Blocked {proposal.tool_name}: {reason}",
            evidence=list(proposal.evidence),
            input_payload={"proposal_id": proposal.proposal_id, "reason": reason},
            output_payload=after,
            action_id=execution_id,
            tool_id=proposal.tool_name,
            idempotency_key=key,
        )
        return ToolResult(
            tool_name=proposal.tool_name,
            status=ActionStatus.BLOCKED,
            authorized_tier=tier,
            executed=False,
            replayed=False,
            idempotency_key=key,
            execution_id=execution_id,
            before=before,
            after=after,
            before_hash=hash_payload(before),
            after_hash=hash_payload(after),
            audit_event_id=audit_event.event_id,
            message="blocked",
            blocked_reason=reason,
        )


def evidence_ok(items: list[EvidenceReference] | None) -> bool:
    return bool(items)
