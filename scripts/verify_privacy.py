from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_NAMES = {".env", "normalized_posts.csv", "studio.db"}
SECRET_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_-]{16,}"), re.compile(r"OPENAI_API_KEY\s*=\s*\S+")]


def main() -> int:
    failures: list[str] = []
    for base in (ROOT / "showcase", ROOT / "site" / "dist"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.name in FORBIDDEN_NAMES or path.suffix in {".db", ".sqlite", ".sqlite3"}:
                failures.append(f"private filename: {path}")
            if path.suffix.lower() in {".json", ".html", ".js", ".css", ".txt", ".md"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for pattern in SECRET_PATTERNS:
                    if pattern.search(text):
                        failures.append(f"possible secret in {path}")
    if failures:
        print("\n".join(failures))
        return 1
    print("Public artifacts contain no known private files or API-key patterns.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

