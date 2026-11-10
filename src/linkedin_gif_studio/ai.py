from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from .models import (
    DraftGeneration,
    DraftPackage,
    StoryboardFrame,
    StoryboardSpec,
    VoiceProfile,
)

T = TypeVar("T", bound=BaseModel)


class ResponsesClient(Protocol):
    responses: Any


@dataclass(frozen=True)
class DraftRequest:
    topic: str
    audience: str
    point_of_view: str
    facts: str
    source_urls: list[str]
    personal_experience: str = ""


def build_private_safe_payload(profile: VoiceProfile, request: DraftRequest) -> dict[str, object]:
    """Build the only data structure allowed to cross the model boundary.

    Voice observations and excerpts are intentionally excluded. Only rules the
    author explicitly approved are sent with new-topic material.
    """

    if not profile.is_approved:
        raise ValueError("The voice profile must be approved before drafting")
    return {
        "approved_voice_rules": profile.approved_rules,
        "prohibited_behaviors": profile.prohibited_behaviors,
        "topic": request.topic,
        "audience": request.audience,
        "point_of_view": request.point_of_view,
        "facts": request.facts,
        "source_urls": request.source_urls,
        "personal_experience": request.personal_experience,
    }


def _response_parse(client: ResponsesClient, model: str, schema: type[T], instructions: str, payload: dict[str, object]) -> T:
    input_text = json.dumps(payload, ensure_ascii=False)
    parse = getattr(client.responses, "parse", None)
    if callable(parse):
        response = parse(
            model=model,
            reasoning={"effort": "medium"},
            instructions=instructions,
            input=input_text,
            text_format=schema,
            store=False,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            return parsed if isinstance(parsed, schema) else schema.model_validate(parsed)
        return schema.model_validate_json(response.output_text)

    response = client.responses.create(
        model=model,
        reasoning={"effort": "medium"},
        instructions=instructions,
        input=input_text,
        store=False,
        text={
            "format": {
                "type": "json_schema",
                "name": schema.__name__,
                "strict": True,
                "schema": schema.model_json_schema(),
            }
        },
    )
    return schema.model_validate_json(response.output_text)


class AIStudio:
    def __init__(self, client: ResponsesClient | None = None, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-6-luna")
        if client is not None:
            self.client = client
        elif os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI

            self.client = OpenAI()
        else:
            self.client = None

    @property
    def is_demo_mode(self) -> bool:
        return self.client is None

    def generate_draft(self, post_id: str, profile: VoiceProfile, request: DraftRequest) -> DraftPackage:
        payload = build_private_safe_payload(profile, request)
        if self.client is None:
            result = self._demo_draft(request)
            model_name = "deterministic-demo"
        else:
            result = _response_parse(
                self.client,
                self.model,
                DraftGeneration,
                (
                    "Create a LinkedIn post from only the supplied facts and personal experience. "
                    "Return exactly three distinct hooks. Follow the approved voice rules. Never invent "
                    "experience, evidence, performance, people, employers, or opinions. If a factual claim "
                    "is not supported, omit it and add a warning. The main claim must be precise and sourceable."
                ),
                payload,
            )
            model_name = self.model
        return DraftPackage(
            post_id=post_id,
            hooks=result.hooks,
            selected_hook=result.hooks[0],
            post_text=result.post_text,
            main_claim=result.main_claim,
            supporting_evidence=result.supporting_evidence,
            sources=result.sources,
            warnings=result.warnings,
            voice_profile_version=profile.version,
            model_name=model_name,
        )

    def generate_storyboard(self, draft: DraftPackage) -> StoryboardSpec:
        if not draft.ready_for_visual:
            raise ValueError("Approve a warning-free post and claim before creating a storyboard")
        if self.client is None:
            return self._demo_storyboard(draft)
        payload = {
            "post_id": draft.post_id,
            "approved_post": draft.post_text,
            "approved_claim": draft.main_claim,
            "constraints": [
                "Use no facts absent from the approved post and claim.",
                "Use 2 to 4 frames and 1 to 4 seconds per frame.",
                "Animate one conceptual relationship, not decorative motion.",
                "Keep on-screen words concise and readable.",
            ],
        }
        return _response_parse(
            self.client,
            self.model,
            StoryboardSpec,
            "Design a restrained square infographic loop. Preserve the supplied claim exactly and add no facts.",
            payload,
        )

    @staticmethod
    def _demo_draft(request: DraftRequest) -> DraftGeneration:
        topic = request.topic.strip() or "AI-native work"
        claim = f"A trustworthy {topic} workflow makes its evidence and approval gates visible."
        facts = [line.strip(" -•\t") for line in request.facts.splitlines() if line.strip()]
        warnings = [] if facts or request.personal_experience.strip() else ["Add at least one supplied fact or real experience before approval."]
        hooks = [
            f"The useful part of {topic} is not the first draft.",
            f"I trust {topic} more when I can inspect how it was made.",
            f"What changes when {topic} has an approval trail?",
        ]
        evidence = facts[:3] or ([request.personal_experience.strip()] if request.personal_experience.strip() else [])
        body = [
            hooks[0],
            "",
            claim,
            "",
            "The workflow separates source material, voice rules, claims, and visual decisions. Each stage can be reviewed before the next one begins.",
        ]
        if evidence:
            body.extend(["", "What grounds this draft:", *[f"• {fact}" for fact in evidence]])
        body.extend(["", "That makes the result easier to revise—and easier to stand behind."])
        return DraftGeneration(
            hooks=hooks,
            post_text="\n".join(body),
            main_claim=claim,
            supporting_evidence=evidence,
            sources=request.source_urls,
            warnings=warnings,
        )

    @staticmethod
    def _demo_storyboard(draft: DraftPackage) -> StoryboardSpec:
        claim_words = re.sub(r"\s+", " ", draft.main_claim).strip()
        frames = [
            StoryboardFrame(
                on_screen_words="SOURCE → VOICE → CLAIM",
                visual_change="Three checkpoints appear in sequence.",
                duration_seconds=2.0,
                transition="fade",
            ),
            StoryboardFrame(
                on_screen_words="APPROVE THE WORDS",
                visual_change="The claim checkpoint becomes highlighted.",
                duration_seconds=2.0,
                transition="slide",
            ),
            StoryboardFrame(
                on_screen_words="THEN DESIGN THE MOTION",
                visual_change="The final visual node completes the loop.",
                duration_seconds=2.0,
                transition="fade",
            ),
        ]
        return StoryboardSpec(
            post_id=draft.post_id,
            concept="Approval gates turn one claim into a traceable visual.",
            frames=frames,
            total_loop_seconds=6.0,
            alt_text=f"Animated infographic showing source, voice, and claim approval before visual design. Main claim: {claim_words}",
        )

