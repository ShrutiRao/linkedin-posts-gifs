from __future__ import annotations

import json
import shutil
from pathlib import Path

from .models import DraftPackage, PairManifest, StoryboardSpec, VoiceProfile


PRIVATE_KEYS = {"excerpts", "supporting_post_ids", "corpus", "raw_posts", "api_key", "database"}


def _assert_sanitized(value: object, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in PRIVATE_KEYS:
                raise ValueError(f"Private field found in public export: {path}.{key}")
            _assert_sanitized(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_sanitized(child, f"{path}[{index}]")


def export_showcase(
    profile: VoiceProfile,
    draft: DraftPackage,
    storyboard: StoryboardSpec,
    manifest: PairManifest,
    pair_dir: str | Path,
    destination: str | Path = "showcase",
    approved_excerpt_ids: list[str] | None = None,
) -> Path:
    if not (profile.is_approved and draft.ready_for_visual and storyboard.approved and manifest.review_complete):
        raise ValueError("Only a fully approved and reviewed pair can be exported")
    destination = Path(destination)
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    pair_dir = Path(pair_dir)
    for name in ("infographic.gif", "fallback.png"):
        shutil.copy2(pair_dir / name, assets / name)
    public_rules = profile.approved_rules
    data = {
        "label": "Curated example",
        "privacy": "Historical post text stayed local. The model received approved derived rules and new-topic evidence only.",
        "voice_profile_version": profile.version,
        "voice_rules": public_rules,
        "public_excerpt_ids": approved_excerpt_ids or [],
        "draft": {
            "post_id": draft.post_id,
            "hooks": draft.hooks,
            "selected_hook": draft.selected_hook,
            "post_text": draft.post_text,
            "main_claim": draft.main_claim,
            "supporting_evidence": draft.supporting_evidence,
            "sources": draft.sources,
        },
        "storyboard": {
            "concept": storyboard.concept,
            "frames": [frame.model_dump() for frame in storyboard.frames],
            "alt_text": storyboard.alt_text,
        },
        "assets": {"gif": "assets/infographic.gif", "fallback": "assets/fallback.png"},
    }
    _assert_sanitized(data)
    (destination / "showcase.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return destination

