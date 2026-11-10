from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import BinaryIO

import pandas as pd

from .models import AuditReport, CorpusPost


ALIASES = {
    "post_id": ["post_id", "id", "share id", "post id"],
    "date": ["date", "created at", "created_at", "post date"],
    "text": ["text", "commentary", "content", "post text", "sharecommentary"],
    "permalink": ["permalink", "url", "post url", "sharelink"],
    "format": ["format", "post format", "type"],
    "topic": ["topic", "theme"],
    "audience": ["audience", "intended audience"],
    "impressions": ["impressions", "views"],
    "reactions": ["reactions", "likes"],
    "comments": ["comments", "comment count"],
    "reposts": ["reposts", "shares"],
    "measured_at": ["measured_at", "measured at", "metrics date"],
    "keep_as_example": ["keep_as_example", "keep as example", "example"],
    "notes": ["notes", "editorial notes"],
}


def _key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _rename_columns(frame: pd.DataFrame) -> pd.DataFrame:
    current = {_key(str(column)): column for column in frame.columns}
    rename: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if _key(alias) in current:
                rename[current[_key(alias)]] = canonical
                break
    return frame.rename(columns=rename)


def _optional_int(value: object) -> int | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _optional_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "keep"}


def _valid_permalink(value: str | None) -> bool:
    return value is None or bool(re.match(r"^https?://[^\s]+$", value))


def load_corpus(source: str | bytes | BinaryIO) -> tuple[list[CorpusPost], AuditReport, pd.DataFrame]:
    if isinstance(source, bytes):
        source = io.BytesIO(source)
    frame = _rename_columns(pd.read_csv(source))
    original_count = len(frame)
    for column in ALIASES:
        if column not in frame.columns:
            frame[column] = pd.NA

    parsed_dates = pd.to_datetime(frame["date"], errors="coerce", utc=True, format="mixed")
    measured_dates = pd.to_datetime(frame["measured_at"], errors="coerce", utc=True, format="mixed")
    malformed_dates = [int(i) + 2 for i, (raw, parsed) in enumerate(zip(frame["date"], parsed_dates)) if _optional_text(raw) and pd.isna(parsed)]

    posts: list[CorpusPost] = []
    invalid_rows: list[int] = []
    for idx, row in frame.iterrows():
        post_id = _optional_text(row["post_id"])
        text = _optional_text(row["text"])
        if not post_id or not text:
            invalid_rows.append(int(idx) + 2)
            continue
        post_date = None if pd.isna(parsed_dates.iloc[idx]) else parsed_dates.iloc[idx].date()
        measured_at = None if pd.isna(measured_dates.iloc[idx]) else measured_dates.iloc[idx].to_pydatetime()
        posts.append(
            CorpusPost(
                post_id=post_id,
                date=post_date,
                text=text,
                permalink=_optional_text(row["permalink"]),
                format=_optional_text(row["format"]),
                topic=_optional_text(row["topic"]),
                audience=_optional_text(row["audience"]),
                impressions=_optional_int(row["impressions"]),
                reactions=_optional_int(row["reactions"]),
                comments=_optional_int(row["comments"]),
                reposts=_optional_int(row["reposts"]),
                measured_at=measured_at,
                keep_as_example=_bool(row["keep_as_example"]),
                notes=_optional_text(row["notes"]),
            )
        )

    ids = [post.post_id for post in posts]
    duplicate_ids = sorted({post_id for post_id in ids if ids.count(post_id) > 1})
    broken = [post.post_id for post in posts if not _valid_permalink(post.permalink)]
    metric_sets = {
        "with_impressions": sum(post.impressions is not None for post in posts),
        "with_reactions": sum(post.reactions is not None for post in posts),
        "with_measurement_time": sum(post.measured_at is not None for post in posts),
    }
    with_any_metric = [post for post in posts if any(value is not None for value in (post.impressions, post.reactions, post.comments, post.reposts))]
    metrics_comparable = bool(with_any_metric) and all(post.measured_at is not None for post in with_any_metric)
    missing_by_field = {
        column: int(frame[column].isna().sum() + (frame[column].astype(str).str.strip() == "").sum())
        for column in ("post_id", "date", "text", "permalink", "format", "topic", "audience", "measured_at")
    }
    notes = [
        "Performance fields are descriptive context only; the audit does not infer causation.",
        "Raw reactions are not reported as an engagement rate because no denominator is assumed.",
    ]
    if invalid_rows:
        notes.append(f"Rows skipped for missing post_id or text: {invalid_rows}")
    if not metrics_comparable and with_any_metric:
        notes.append("Metric snapshots are not directly comparable because measured_at is incomplete.")
    report = AuditReport(
        row_count=original_count,
        valid_count=len(posts),
        target_sample_met=20 <= len(posts) <= 40,
        missing_by_field=missing_by_field,
        duplicate_ids=duplicate_ids,
        malformed_dates=malformed_dates,
        broken_permalinks=broken,
        metric_sets=metric_sets,
        metrics_comparable=metrics_comparable,
        notes=notes,
    )
    return posts, report, frame


def posts_to_frame(posts: list[CorpusPost]) -> pd.DataFrame:
    return pd.DataFrame([post.model_dump(mode="json") for post in posts])
