"""Deterministic Protocol 215 demo reset — synthetic state only."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from protocol215.config import AppEnv, Settings
from protocol215.fixtures import fixtures_root
from protocol215.simulator.twin import load_participants, load_sites

# Run-generated objects under the local object store (fixtures/ never touched).
RUN_OBJECT_PREFIXES = ("runs/", "protocols/", "artifacts/", "demo/")


@dataclass
class DemoResetResult:
    ok: bool
    message: str
    sites_restored: int = 0
    participants_restored: int = 0
    runs_cleared: int = 0
    objects_cleared: int = 0
    fixtures_preserved: list[str] = field(default_factory=list)
    twin_snapshot: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


def fixture_inventory_paths() -> list[Path]:
    """Source PDFs and twin JSON that must survive reset."""
    root = fixtures_root()
    roots = [root / "protocols", root / "study_state", root / "gold"]
    paths: list[Path] = []
    for base in roots:
        if base.exists():
            paths.extend(sorted(p for p in base.rglob("*") if p.is_file()))
    return paths


def twin_baseline_snapshot() -> dict[str, Any]:
    """Load synthetic twin from fixtures (3 sites, 5 participants, logistics)."""
    sites = load_sites()
    participants = load_participants()
    logistics = {
        "sites": [
            {
                "site_id": s.site_id,
                "name": s.name,
                "city": s.city,
                "courier_departure_local_time": s.logistics.courier_departure_local_time,
                "overnight_storage_validated": s.logistics.validated_overnight_storage_available,
                "extra_pk_kits": s.inventory.extra_pk_kits,
                "amendment_training_complete": s.amendment_training_complete,
                "local_approval_complete": s.local_approval_complete,
            }
            for s in sites
        ],
        "participants": [
            {
                "participant_id": p.participant_id,
                "site_id": p.site_id,
                "visits": [
                    {
                        "visit_code": v.visit_code,
                        "completed": v.completed,
                        "immutable": v.immutable,
                        "planned_dose_time_local": v.planned_dose_time_local,
                    }
                    for v in p.visits
                ],
            }
            for p in participants
        ],
    }
    return {
        "site_count": len(sites),
        "participant_count": len(participants),
        "site_ids": [s.site_id for s in sites],
        "participant_ids": [p.participant_id for p in participants],
        "logistics": logistics,
    }


def require_cloud_confirmation(settings: Settings, *, confirmed: bool) -> None:
    if settings.app_env == AppEnv.CLOUD and not confirmed:
        raise PermissionError(
            "Cloud demo reset requires explicit confirmation "
            "(pass confirm=true or CONFIRM_DEMO_RESET=yes)."
        )


def clear_local_object_runs(root: Path) -> int:
    """Delete run upload artifacts under the local object store; keep directory."""
    if not root.exists():
        return 0
    cleared = 0
    for child in list(root.rglob("*")):
        if child.is_file():
            child.unlink(missing_ok=True)
            cleared += 1
    return cleared


# Firestore collections owned by Protocol 215 demo runs (never touch infra).
DEMO_FIRESTORE_COLLECTIONS = (
    "runs",
    "protocol_versions",
    "protocol_irs",
    "changes",
    "sites",
    "participants",
    "findings",
    "actions",
    "action_keys",
    "approvals",
    "approval_decisions",
    "audit_events",
    "manifests",
    "sessions",
    "processed_events",
)


def clear_firestore_demo_collections(client: Any) -> int:
    """Delete documents in Protocol 215 demo collections only."""
    deleted = 0
    for name in DEMO_FIRESTORE_COLLECTIONS:
        col = client.collection(name)
        for snap in col.stream():
            snap.reference.delete()
            deleted += 1
    return deleted
