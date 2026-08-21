"""Build the resumable ADK Workflow App for Protocol 215."""

from __future__ import annotations

from google.adk.apps.app import App, ResumabilityConfig
from google.adk.workflow import Workflow

from protocol215.workflow import nodes as n

APP_NAME = "protocol_215"


def build_amendment_workflow() -> Workflow:
    """ADK 2.x graph — deterministic FunctionNodes + HITL RequestInput."""
    return Workflow(
        name="AmendmentPreflightWorkflow",
        edges=[
            ("START", n.intake_validator),
            (n.intake_validator, n.register_artifacts),
            (n.register_artifacts, n.compile_old_protocol),
            (n.compile_old_protocol, n.compile_new_protocol),
            (n.compile_new_protocol, n.semantic_diff_node),
            (n.semantic_diff_node, n.impact_graph_builder),
            (n.impact_graph_builder, n.trial_twin_simulator),
            (n.trial_twin_simulator, n.action_planner),
            (n.action_planner, n.policy_gate),
            (
                n.policy_gate,
                {
                    "safe": n.safe_action_executor,
                    "blocked": n.invariant_verifier,
                },
            ),
            (n.safe_action_executor, n.approval_router),
            (
                n.approval_router,
                {
                    "awaiting": n.human_approval,
                    "skip": n.invariant_verifier,
                },
            ),
            (
                n.human_approval,
                {
                    "approved": n.approved_action_executor,
                    "rejected": n.invariant_verifier,
                },
            ),
            (n.approved_action_executor, n.invariant_verifier),
            (n.invariant_verifier, n.manifest_generator),
            (n.manifest_generator, n.complete_run),
        ],
    )


def build_app() -> App:
    """Export resumable ADK App (required for multi-step HITL)."""
    return App(
        name=APP_NAME,
        root_agent=build_amendment_workflow(),
        resumability_config=ResumabilityConfig(is_resumable=True),
    )


# Module-level exports for ADK agent loader conventions.
root_agent = build_amendment_workflow()
app = build_app()
