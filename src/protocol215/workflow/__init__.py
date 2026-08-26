"""Workflow package — resumable Google ADK 2.x amendment graph."""

from typing import Any

# Keep package import light to avoid circular imports with policy.
# Import driver/graph from their modules directly:
#   from protocol215.workflow.driver import LocalWorkflowDriver
#   from protocol215.workflow.graph import app, build_app

__all__ = [
    "APP_NAME",
    "LocalWorkflowDriver",
    "WorkflowDriveResult",
    "app",
    "build_amendment_workflow",
    "build_app",
    "root_agent",
]


def __getattr__(name: str) -> Any:
    if name in {"LocalWorkflowDriver", "WorkflowDriveResult"}:
        from protocol215.workflow import driver as _driver

        return getattr(_driver, name)
    if name in {"APP_NAME", "app", "build_amendment_workflow", "build_app", "root_agent"}:
        from protocol215.workflow import graph as _graph

        return getattr(_graph, name)
    raise AttributeError(name)
