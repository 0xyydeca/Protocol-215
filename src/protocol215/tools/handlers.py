"""Synthetic-state mutation handlers for allowlisted tools."""

from __future__ import annotations

from typing import Any

from protocol215.domain.models import SiteState
from protocol215.tools.schemas import (
    CreateCourierExceptionTaskArgs,
    CreateEdcChangeSpecificationArgs,
    CreateLabManualChangeRequestArgs,
    CreateReconsentReviewArgs,
    CreateSiteTrainingTaskArgs,
    DraftParticipantTransitionPlanArgs,
    GenerateReleaseManifestArgs,
    RequestSiteActivationReviewArgs,
    ReserveSampleKitsArgs,
    UpdateContactDirectoryArgs,
)


def _site_snapshot(site: SiteState | None) -> dict[str, Any]:
    if site is None:
        return {"exists": False}
    return {
        "site_id": site.site_id,
        "training_complete": site.amendment_training_complete,
        "approval_complete": site.local_approval_complete,
        "v2_activated": site.v2_activated,
        "pk_kits": site.inventory.extra_pk_kits,
        "contacts": {},
    }


def handle_update_contact_directory(
    *,
    args: UpdateContactDirectoryArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    before = {
        "contacts": dict(scratch.get("contacts", {})),
        "email": scratch.get("contacts", {}).get(args.role),
    }
    contacts = dict(scratch.get("contacts", {}))
    contacts[args.role] = args.email
    scratch["contacts"] = contacts
    after = {"contacts": dict(contacts), "email": args.email, "role": args.role}
    return before, after, sites


def handle_create_site_training_task(
    *,
    args: CreateSiteTrainingTaskArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    site = next((s for s in sites if s.site_id == args.site_id), None)
    before = _site_snapshot(site)
    tasks = list(scratch.get("training_tasks", []))
    task = {
        "site_id": args.site_id,
        "topic": args.training_topic,
        "status": "open",
    }
    tasks.append(task)
    scratch["training_tasks"] = tasks
    after = {**before, "training_task": task}
    return before, after, sites


def handle_reserve_sample_kits(
    *,
    args: ReserveSampleKitsArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    updated: list[SiteState] = []
    before: dict[str, Any] = {"exists": False}
    after: dict[str, Any] = {}
    for site in sites:
        if site.site_id != args.site_id:
            updated.append(site)
            continue
        before = _site_snapshot(site)
        inv = site.inventory.model_copy(
            update={"extra_pk_kits": site.inventory.extra_pk_kits + args.quantity}
        )
        new_site = site.model_copy(update={"inventory": inv})
        updated.append(new_site)
        after = _site_snapshot(new_site)
        after["reserved"] = {"kit_type": args.kit_type, "quantity": args.quantity}
    if not after:
        # Site missing — still record synthetic reservation in scratch
        after = {
            "site_id": args.site_id,
            "reserved": {"kit_type": args.kit_type, "quantity": args.quantity},
            "synthetic_only": True,
        }
        scratch.setdefault("kit_reservations", []).append(after)
        return before, after, sites
    return before, after, updated


def handle_create_lab_manual_change_request(
    *,
    args: CreateLabManualChangeRequestArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    before = {"requests": list(scratch.get("lab_manual_requests", []))}
    req = {"summary": args.change_summary, "status": "draft"}
    scratch.setdefault("lab_manual_requests", []).append(req)
    after = {"requests": list(scratch["lab_manual_requests"]), "created": req}
    return before, after, sites


def handle_create_edc_change_specification(
    *,
    args: CreateEdcChangeSpecificationArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    before = {"specs": list(scratch.get("edc_specs", []))}
    spec = {"field_name": args.field_name, "unit": args.unit, "status": "draft"}
    scratch.setdefault("edc_specs", []).append(spec)
    after = {"specs": list(scratch["edc_specs"]), "created": spec}
    return before, after, sites


def handle_create_courier_exception_task(
    *,
    args: CreateCourierExceptionTaskArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    before = {"tasks": list(scratch.get("courier_tasks", []))}
    task = {
        "site_id": args.site_id,
        "participant_id": args.participant_id,
        "summary": args.conflict_summary,
        "status": "open",
    }
    scratch.setdefault("courier_tasks", []).append(task)
    after = {"tasks": list(scratch["courier_tasks"]), "created": task}
    return before, after, sites


def handle_create_reconsent_review(
    *,
    args: CreateReconsentReviewArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    before = {"reviews": list(scratch.get("reconsent_reviews", []))}
    review = {
        "participant_id": args.participant_id,
        "reason": args.reason,
        "status": "pending_review",
    }
    scratch.setdefault("reconsent_reviews", []).append(review)
    after = {"reviews": list(scratch["reconsent_reviews"]), "created": review}
    return before, after, sites


def handle_draft_participant_transition_plan(
    *,
    args: DraftParticipantTransitionPlanArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    before = {"plans": list(scratch.get("transition_plans", []))}
    plan = {
        "participant_id": args.participant_id,
        "site_id": args.site_id,
        "summary": args.transition_summary,
        "proposed_schedule": args.proposed_schedule,
        "status": "draft_approved",
    }
    scratch.setdefault("transition_plans", []).append(plan)
    after = {"plans": list(scratch["transition_plans"]), "created": plan}
    return before, after, sites


def handle_request_site_activation_review(
    *,
    args: RequestSiteActivationReviewArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    site = next((s for s in sites if s.site_id == args.site_id), None)
    before = _site_snapshot(site)
    reviews = list(scratch.get("activation_reviews", []))
    review = {
        "site_id": args.site_id,
        "target_protocol_version": args.target_protocol_version,
        "status": "pending_review",
    }
    reviews.append(review)
    scratch["activation_reviews"] = reviews
    after = {**before, "activation_review": review}
    return before, after, sites


def handle_generate_release_manifest(
    *,
    args: GenerateReleaseManifestArgs,
    sites: list[SiteState],
    scratch: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[SiteState]]:
    before = {"manifest": scratch.get("manifest")}
    manifest = {
        "study_id": args.study_id,
        "from_version": args.from_version,
        "to_version": args.to_version,
        "status": "generated",
    }
    scratch["manifest"] = manifest
    after = {"manifest": manifest}
    return before, after, sites


HANDLERS = {
    "update_contact_directory": handle_update_contact_directory,
    "create_site_training_task": handle_create_site_training_task,
    "reserve_sample_kits": handle_reserve_sample_kits,
    "create_lab_manual_change_request": handle_create_lab_manual_change_request,
    "create_edc_change_specification": handle_create_edc_change_specification,
    "create_courier_exception_task": handle_create_courier_exception_task,
    "create_reconsent_review": handle_create_reconsent_review,
    "draft_participant_transition_plan": handle_draft_participant_transition_plan,
    "request_site_activation_review": handle_request_site_activation_review,
    "generate_release_manifest": handle_generate_release_manifest,
}
