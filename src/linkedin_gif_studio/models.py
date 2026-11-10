from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CorpusPost(StrictModel):
    post_id: str
    date: Date | None = None
    text: str
    permalink: str | None = None
    format: str | None = None
    topic: str | None = None
    audience: str | None = None
    impressions: int | None = None
    reactions: int | None = None
    comments: int | None = None
    reposts: int | None = None
    measured_at: datetime | None = None
    keep_as_example: bool = False
    notes: str | None = None

    @field_validator("post_id", "text")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class AuditReport(StrictModel):
    row_count: int
    valid_count: int
    target_sample_met: bool
    missing_by_field: dict[str, int]
    duplicate_ids: list[str]
    malformed_dates: list[int]
    broken_permalinks: list[str]
    metric_sets: dict[str, int]
    metrics_comparable: bool
    notes: list[str]


class VoiceObservation(StrictModel):
    category: str
    pattern: str
    supporting_post_ids: list[str]
    excerpts: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    kind: Literal["observation", "recommendation"]

    @model_validator(mode="after")
    def observations_require_evidence(self) -> "VoiceObservation":
        if self.kind == "observation" and not self.supporting_post_ids:
            raise ValueError("observations require at least one supporting post ID")
        return self


class VoiceProfile(StrictModel):
    version: int = Field(ge=1)
    observations: list[VoiceObservation]
    approved_rules: list[str]
    prohibited_behaviors: list[str]
    preferences: dict[str, str] = Field(default_factory=dict)
    approved_at: datetime | None = None

    @property
    def is_approved(self) -> bool:
        return self.approved_at is not None


class DraftGeneration(StrictModel):
    hooks: list[str] = Field(min_length=3, max_length=3)
    post_text: str
    main_claim: str
    supporting_evidence: list[str]
    sources: list[str]
    warnings: list[str]


class DraftPackage(StrictModel):
    post_id: str
    hooks: list[str] = Field(min_length=3, max_length=3)
    selected_hook: str
    post_text: str
    main_claim: str
    supporting_evidence: list[str]
    sources: list[str]
    warnings: list[str]
    voice_profile_version: int
    model_name: str
    claim_approved: bool = False
    post_approved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def selected_hook_is_known(self) -> "DraftPackage":
        if self.selected_hook not in self.hooks:
            raise ValueError("selected_hook must be one of hooks")
        return self

    @property
    def ready_for_visual(self) -> bool:
        return self.claim_approved and self.post_approved and not self.warnings


class StoryboardFrame(StrictModel):
    on_screen_words: str
    visual_change: str
    duration_seconds: float = Field(ge=1.0, le=4.0)
    transition: Literal["fade", "slide", "hold"] = "fade"


class StoryboardSpec(StrictModel):
    post_id: str
    concept: str
    frames: list[StoryboardFrame] = Field(min_length=2, max_length=5)
    total_loop_seconds: float = Field(ge=3.0, le=15.0)
    alt_text: str
    approved: bool = False

    @model_validator(mode="after")
    def duration_matches_frames(self) -> "StoryboardSpec":
        total = sum(frame.duration_seconds for frame in self.frames)
        if abs(total - self.total_loop_seconds) > 0.25:
            raise ValueError("total_loop_seconds must equal frame durations")
        return self


class PairManifest(StrictModel):
    post_id: str
    source_references: list[str]
    voice_profile_version: int
    model_name: str
    post_approved: bool
    claim_approved: bool
    storyboard_approved: bool
    review_complete: bool
    revision: int = 1
    revised_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    limitations: list[str] = Field(default_factory=list)
    files: dict[str, str]
