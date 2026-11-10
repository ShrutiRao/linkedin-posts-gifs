from __future__ import annotations

from datetime import datetime, timezone

import pytest

from linkedin_gif_studio.models import (
    CorpusPost,
    DraftPackage,
    StoryboardFrame,
    StoryboardSpec,
    VoiceObservation,
    VoiceProfile,
)


@pytest.fixture
def posts() -> list[CorpusPost]:
    return [
        CorpusPost(
            post_id=f"p-{index}",
            date="2026-01-01",
            text=f"I learned one concrete lesson about inspectable AI workflow number {index}. What would you verify first?",
            permalink=f"https://example.com/{index}",
            measured_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )
        for index in range(1, 7)
    ]


@pytest.fixture
def approved_profile() -> VoiceProfile:
    return VoiceProfile(
        version=1,
        observations=[
            VoiceObservation(
                category="opening",
                pattern="Uses a direct first-person observation.",
                supporting_post_ids=["private-1"],
                excerpts=["SECRET HISTORICAL EXCERPT"],
                confidence=0.9,
                kind="observation",
            )
        ],
        approved_rules=["Use a direct opening.", "Keep paragraphs short."],
        prohibited_behaviors=["Invented experience"],
        approved_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def approved_draft() -> DraftPackage:
    return DraftPackage(
        post_id="pair-1",
        hooks=["Hook one", "Hook two", "Hook three"],
        selected_hook="Hook one",
        post_text="Hook one\n\nA traceable workflow is easier to trust.",
        main_claim="A traceable workflow is easier to trust.",
        supporting_evidence=["The workflow records explicit approvals."],
        sources=["https://example.com/source"],
        warnings=[],
        voice_profile_version=1,
        model_name="test-model",
        claim_approved=True,
        post_approved=True,
    )


@pytest.fixture
def approved_storyboard() -> StoryboardSpec:
    return StoryboardSpec(
        post_id="pair-1",
        concept="Approval gates make the decision path visible.",
        frames=[
            StoryboardFrame(on_screen_words="SOURCE", visual_change="Source appears", duration_seconds=1.0),
            StoryboardFrame(on_screen_words="APPROVE", visual_change="Approval appears", duration_seconds=1.0),
            StoryboardFrame(on_screen_words="MOTION", visual_change="Motion appears", duration_seconds=1.0),
        ],
        total_loop_seconds=3.0,
        alt_text="Three-step approval workflow.",
        approved=True,
    )

