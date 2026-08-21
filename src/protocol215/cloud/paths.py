"""Deterministic Cloud Storage object key helpers."""

from __future__ import annotations


def protocol_pdf_key(run_id: str, version: str) -> str:
    return f"runs/{run_id}/protocols/v{version}.pdf"


def manifest_json_key(run_id: str) -> str:
    return f"runs/{run_id}/manifest.json"


def manifest_html_key(run_id: str) -> str:
    return f"runs/{run_id}/manifest.html"


def run_artifact_key(run_id: str, name: str) -> str:
    safe = name.replace("..", "_").lstrip("/")
    return f"runs/{run_id}/artifacts/{safe}"


def demo_artifact_key(name: str) -> str:
    safe = name.replace("..", "_").lstrip("/")
    return f"demo/{safe}"
