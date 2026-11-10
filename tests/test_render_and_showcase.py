from __future__ import annotations

import json

from PIL import Image

from linkedin_gif_studio.render import write_pair_package
from linkedin_gif_studio.showcase import export_showcase


def test_renderer_writes_complete_looping_pair(tmp_path, approved_draft, approved_storyboard) -> None:
    pair_dir, manifest = write_pair_package(approved_draft, approved_storyboard, tmp_path, review_complete=True)
    expected = {"post.txt", "storyboard.md", "infographic.gif", "fallback.png", "alt-text.txt", "manifest.json"}
    assert expected == {path.name for path in pair_dir.iterdir()}
    with Image.open(pair_dir / "infographic.gif") as gif:
        assert gif.size == (1080, 1080)
        assert getattr(gif, "n_frames", 1) >= 30
        assert gif.info.get("loop") == 0
    with Image.open(pair_dir / "fallback.png") as png:
        assert png.size == (1080, 1080)
    assert manifest.review_complete


def test_public_export_has_no_corpus_evidence(tmp_path, approved_profile, approved_draft, approved_storyboard) -> None:
    pair_dir, manifest = write_pair_package(approved_draft, approved_storyboard, tmp_path / "pairs", review_complete=True)
    destination = export_showcase(approved_profile, approved_draft, approved_storyboard, manifest, pair_dir, tmp_path / "public")
    payload = (destination / "showcase.json").read_text(encoding="utf-8")
    assert "SECRET HISTORICAL EXCERPT" not in payload
    assert "private-1" not in payload
    data = json.loads(payload)
    assert data["public_excerpt_ids"] == []
    assert (destination / "assets" / "infographic.gif").exists()

