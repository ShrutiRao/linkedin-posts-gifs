from __future__ import annotations

import json
from types import SimpleNamespace

from linkedin_gif_studio.ai import AIStudio, DraftRequest, build_private_safe_payload
from linkedin_gif_studio.models import DraftGeneration


class CapturingResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        parsed = DraftGeneration(
            hooks=["One", "Two", "Three"],
            post_text="One\n\nSupported draft.",
            main_claim="Supported claim",
            supporting_evidence=["Fact"],
            sources=["https://example.com"],
            warnings=[],
        )
        return SimpleNamespace(output_parsed=parsed, output_text=parsed.model_dump_json())


def test_safe_payload_excludes_observations_and_excerpts(approved_profile) -> None:
    request = DraftRequest("Topic", "Audience", "POV", "New fact", ["https://example.com"], "Real experience")
    payload = build_private_safe_payload(approved_profile, request)
    serialized = json.dumps(payload)
    assert "SECRET HISTORICAL EXCERPT" not in serialized
    assert "private-1" not in serialized
    assert "observations" not in serialized
    assert "Use a direct opening" in serialized


def test_openai_request_never_contains_historical_text(approved_profile) -> None:
    responses = CapturingResponses()
    client = SimpleNamespace(responses=responses)
    studio = AIStudio(client=client, model="gpt-6-luna")
    request = DraftRequest("Topic", "Audience", "POV", "New fact", ["https://example.com"], "Real experience")
    studio.generate_draft("new-1", approved_profile, request)
    outbound = json.dumps(responses.kwargs, default=str)
    assert "SECRET HISTORICAL EXCERPT" not in outbound
    assert "private-1" not in outbound
    assert responses.kwargs["store"] is False
