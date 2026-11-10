from __future__ import annotations

from copy import deepcopy

from linkedin_gif_studio.workflow import render_gate, visual_gate


def test_visual_is_blocked_until_claim_and_post_are_approved(approved_draft) -> None:
    draft = deepcopy(approved_draft)
    draft.claim_approved = False
    draft.post_approved = False
    gate = visual_gate(draft)
    assert not gate.allowed
    assert len(gate.reasons) == 2


def test_warnings_block_visual_even_after_approval(approved_draft) -> None:
    draft = deepcopy(approved_draft)
    draft.warnings = ["Missing source"]
    assert not visual_gate(draft).allowed


def test_render_requires_storyboard_approval(approved_draft, approved_storyboard) -> None:
    storyboard = deepcopy(approved_storyboard)
    storyboard.approved = False
    assert not render_gate(approved_draft, storyboard).allowed

