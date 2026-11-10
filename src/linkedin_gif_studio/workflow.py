from __future__ import annotations

from dataclasses import dataclass

from .models import DraftPackage, StoryboardSpec, VoiceProfile


@dataclass(frozen=True)
class GateStatus:
    allowed: bool
    reasons: list[str]


def draft_gate(profile: VoiceProfile | None) -> GateStatus:
    reasons = []
    if profile is None:
        reasons.append("Create a voice profile first.")
    elif not profile.is_approved:
        reasons.append("Approve the voice profile first.")
    return GateStatus(not reasons, reasons)


def visual_gate(draft: DraftPackage | None) -> GateStatus:
    reasons = []
    if draft is None:
        reasons.append("Generate a draft first.")
    else:
        if not draft.claim_approved:
            reasons.append("Approve the main claim.")
        if not draft.post_approved:
            reasons.append("Approve the post text.")
        if draft.warnings:
            reasons.append("Resolve every factual warning.")
    return GateStatus(not reasons, reasons)


def render_gate(draft: DraftPackage | None, storyboard: StoryboardSpec | None) -> GateStatus:
    reasons = list(visual_gate(draft).reasons)
    if storyboard is None:
        reasons.append("Create a storyboard first.")
    elif not storyboard.approved:
        reasons.append("Approve the storyboard first.")
    return GateStatus(not reasons, reasons)

