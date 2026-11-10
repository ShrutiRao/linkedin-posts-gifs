from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site" / "dist"
DESTINATION = ROOT / "dist"


def main() -> None:
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    shutil.copytree(SOURCE, DESTINATION)
    required = [DESTINATION / "index.html", DESTINATION / "showcase.json", DESTINATION / "assets" / "infographic.gif"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Site build is incomplete: {missing}")
    print(f"Static Site built at {DESTINATION}")


if __name__ == "__main__":
    main()

