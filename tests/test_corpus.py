from __future__ import annotations

from io import BytesIO

from linkedin_gif_studio.corpus import load_corpus


def test_import_reports_missing_duplicate_and_malformed_data() -> None:
    csv = b"post_id,date,text,permalink,impressions,measured_at\np1,not-a-date,Hello,not-a-url,100,\np1,2026-01-01,Again,https://example.com/p1,120,2026-01-02\n,2026-01-03,Missing id,https://example.com/x,,\n"
    posts, report, _ = load_corpus(csv)
    assert len(posts) == 2
    assert report.duplicate_ids == ["p1"]
    assert report.malformed_dates == [2]
    assert report.broken_permalinks == ["p1"]
    assert not report.metrics_comparable
    assert any("not directly comparable" in note for note in report.notes)


def test_reactions_are_not_converted_to_engagement_rate() -> None:
    csv = b"post_id,date,text,reactions\np1,2026-01-01,Hello,12\n"
    _, report, _ = load_corpus(csv)
    assert "engagement" not in report.metric_sets
    assert any("not reported as an engagement rate" in note for note in report.notes)

