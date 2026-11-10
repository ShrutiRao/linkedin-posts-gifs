from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .models import DraftPackage, StoryboardSpec, VoiceProfile

T = TypeVar("T", bound=BaseModel)


class StudioStore:
    def __init__(self, path: str | Path = "data/private/studio.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    kind TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (kind, artifact_id, version)
                );
                CREATE TABLE IF NOT EXISTS revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    preserved_claim TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def save(self, kind: str, artifact_id: str, version: int, model: BaseModel) -> None:
        payload = model.model_dump_json()
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO artifacts(kind, artifact_id, version, payload) VALUES (?, ?, ?, ?)",
                (kind, artifact_id, version, payload),
            )

    def load_latest(self, kind: str, artifact_id: str, model_type: type[T]) -> T | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM artifacts WHERE kind=? AND artifact_id=? ORDER BY version DESC LIMIT 1",
                (kind, artifact_id),
            ).fetchone()
        return model_type.model_validate_json(row["payload"]) if row else None

    def save_profile(self, profile: VoiceProfile) -> None:
        self.save("voice_profile", "default", profile.version, profile)

    def latest_profile(self) -> VoiceProfile | None:
        return self.load_latest("voice_profile", "default", VoiceProfile)

    def save_draft(self, draft: DraftPackage, version: int = 1) -> None:
        self.save("draft", draft.post_id, version, draft)

    def latest_draft(self, post_id: str) -> DraftPackage | None:
        return self.load_latest("draft", post_id, DraftPackage)

    def save_storyboard(self, storyboard: StoryboardSpec, version: int = 1) -> None:
        self.save("storyboard", storyboard.post_id, version, storyboard)

    def latest_storyboard(self, post_id: str) -> StoryboardSpec | None:
        return self.load_latest("storyboard", post_id, StoryboardSpec)

    def record_revision(self, post_id: str, target: str, instruction: str, preserved_claim: str | None) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO revisions(post_id, target, instruction, preserved_claim) VALUES (?, ?, ?, ?)",
                (post_id, target, instruction, preserved_claim),
            )

    def revisions(self, post_id: str) -> list[dict[str, object]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT target, instruction, preserved_claim, created_at FROM revisions WHERE post_id=? ORDER BY id",
                (post_id,),
            ).fetchall()
        return [dict(row) for row in rows]

