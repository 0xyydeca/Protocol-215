"""Typed Pydantic schemas for allowlisted synthetic tools only."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

from protocol215.domain.models import EvidenceReference


class BaseToolArgs(BaseModel):
    """Common fields every tool invocation must carry."""

    run_id: str
    protocol_version: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    change_ids: list[str] = Field(default_factory=list)
    site_id: str | None = None
    participant_id: str | None = None
    rationale: str = ""


class UpdateContactDirectoryArgs(BaseToolArgs):
    tool_name: Literal["update_contact_directory"] = "update_contact_directory"
    role: str = "central_lab"
    email: str


class CreateSiteTrainingTaskArgs(BaseToolArgs):
    tool_name: Literal["create_site_training_task"] = "create_site_training_task"
    site_id: str
    training_topic: str = "AURORA-101 amendment v2"


class ReserveSampleKitsArgs(BaseToolArgs):
    tool_name: Literal["reserve_sample_kits"] = "reserve_sample_kits"
    site_id: str
    kit_type: str = "pk_6h"
    quantity: int = 1


class CreateLabManualChangeRequestArgs(BaseToolArgs):
    tool_name: Literal["create_lab_manual_change_request"] = "create_lab_manual_change_request"
    change_summary: str


class CreateEdcChangeSpecificationArgs(BaseToolArgs):
    tool_name: Literal["create_edc_change_specification"] = "create_edc_change_specification"
    field_name: str
    unit: str | None = None


class CreateCourierExceptionTaskArgs(BaseToolArgs):
    tool_name: Literal["create_courier_exception_task"] = "create_courier_exception_task"
    site_id: str
    participant_id: str
    conflict_summary: str


class CreateReconsentReviewArgs(BaseToolArgs):
    tool_name: Literal["create_reconsent_review"] = "create_reconsent_review"
    participant_id: str
    reason: str


class DraftParticipantTransitionPlanArgs(BaseToolArgs):
    tool_name: Literal["draft_participant_transition_plan"] = "draft_participant_transition_plan"
    participant_id: str
    site_id: str
    transition_summary: str
    proposed_schedule: dict[str, Any] = Field(default_factory=dict)


class RequestSiteActivationReviewArgs(BaseToolArgs):
    tool_name: Literal["request_site_activation_review"] = "request_site_activation_review"
    site_id: str
    target_protocol_version: str


class GenerateReleaseManifestArgs(BaseToolArgs):
    tool_name: Literal["generate_release_manifest"] = "generate_release_manifest"
    study_id: str
    from_version: str
    to_version: str


ToolArgs = Annotated[
    Union[
        UpdateContactDirectoryArgs,
        CreateSiteTrainingTaskArgs,
        ReserveSampleKitsArgs,
        CreateLabManualChangeRequestArgs,
        CreateEdcChangeSpecificationArgs,
        CreateCourierExceptionTaskArgs,
        CreateReconsentReviewArgs,
        DraftParticipantTransitionPlanArgs,
        RequestSiteActivationReviewArgs,
        GenerateReleaseManifestArgs,
    ],
    Field(discriminator="tool_name"),
]

TOOL_ARGS_BY_NAME: dict[str, type[BaseToolArgs]] = {
    "update_contact_directory": UpdateContactDirectoryArgs,
    "create_site_training_task": CreateSiteTrainingTaskArgs,
    "reserve_sample_kits": ReserveSampleKitsArgs,
    "create_lab_manual_change_request": CreateLabManualChangeRequestArgs,
    "create_edc_change_specification": CreateEdcChangeSpecificationArgs,
    "create_courier_exception_task": CreateCourierExceptionTaskArgs,
    "create_reconsent_review": CreateReconsentReviewArgs,
    "draft_participant_transition_plan": DraftParticipantTransitionPlanArgs,
    "request_site_activation_review": RequestSiteActivationReviewArgs,
    "generate_release_manifest": GenerateReleaseManifestArgs,
}
