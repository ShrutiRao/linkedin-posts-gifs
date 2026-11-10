from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from linkedin_gif_studio.ai import AIStudio, DraftRequest
from linkedin_gif_studio.corpus import load_corpus
from linkedin_gif_studio.render import write_pair_package
from linkedin_gif_studio.showcase import export_showcase
from linkedin_gif_studio.style import analyze_voice


POSTS = [
    "I used to treat an AI draft as the deliverable. Now I treat it as evidence of where review should begin. The shift is simple: make the claim visible before polishing the language.",
    "A fast prototype can still leave a clear trail. I keep the source, the decision, and the output together so the next revision starts with context instead of guesswork.",
    "The most useful automation I built this week did not remove a decision. It made the decision easier to inspect. That is a better definition of leverage for my work.",
    "When a workflow feels magical, I look for the hidden handoff. Who approved the claim? Which source grounded it? What changes when the source changes? Those questions make the system real.",
    "I learn more from one correction than from ten enthusiastic generations. A correction names the mismatch. Once it becomes a rule, the next draft has a better starting point.",
    "A personal writing assistant should not flatten every topic into the same template. Voice and subject are different layers. I want stable preferences without losing the shape of the idea.",
    "Here is the practical test I use for an AI workflow: can I explain what entered, what changed, and what I approved? If not, the output may be useful, but the process is not ready.",
    "I do not want a model to invent confidence on my behalf. If a fact is missing, I would rather see the gap than read a polished sentence that hides it.",
    "The visual should explain the same claim as the post. Motion is useful when it reveals sequence, contrast, or cause. Everything else is decoration I can remove.",
    "A source link is not enough by itself. I still need to know which claim it supports and when the information was measured. Traceability is a writing tool, not just a compliance task.",
    "My favorite AI demos show the seam between human judgment and model output. The seam is where trust is built: select, correct, approve, then publish deliberately.",
    "I keep the static fallback beside every animation. It forces the concept to work without motion and makes the final asset more resilient across platforms.",
    "One clear claim beats five vague takeaways. I draft the claim first, test it against the evidence, and let the rest of the post earn its place around it.",
    "Metrics need a measurement window. Reactions collected after one day and reactions collected after one month are not the same observation, even when they sit in the same column.",
    "I want my tools to remember preferences, not manufacture biography. That boundary keeps first-person writing connected to experiences I actually supplied.",
    "The first hook is a choice, not a conclusion. I compare a direct claim, a personal observation, and a focused question before deciding how the post should open.",
    "A reusable skill becomes useful when I can read its rules. If a rule sounds like generic writing advice, I rewrite it until it describes a preference I recognize.",
    "I separate observations from recommendations. One describes what appears in the corpus. The other is an editorial decision I can accept, revise, or reject.",
    "The output folder is part of the product. Post, storyboard, animation, fallback, alt text, and manifest belong together because they are one reviewed deliverable.",
    "Nothing should publish while I am still thinking. Drafting, approval, and distribution are different actions. Keeping them separate makes experimentation safer.",
]


def main() -> None:
    demo_dir = ROOT / "data" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, text in enumerate(POSTS, start=1):
        rows.append(
            {
                "post_id": f"demo-{index:02d}",
                "date": f"2026-{((index - 1) % 9) + 1:02d}-{((index * 2 - 1) % 27) + 1:02d}",
                "text": text,
                "permalink": f"https://example.com/posts/demo-{index:02d}",
                "format": "text",
                "topic": "AI workflow",
                "audience": "AI builders",
                "impressions": 1000 + index * 73,
                "reactions": 20 + index,
                "comments": index % 7,
                "reposts": index % 4,
                "measured_at": "2026-10-31T12:00:00Z",
                "keep_as_example": index in {3, 7, 11},
                "notes": "Synthetic demonstration post; not authored by the user.",
            }
        )
    csv_path = demo_dir / "synthetic_posts.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    posts, audit, _ = load_corpus(csv_path)
    profile = analyze_voice(posts)
    profile.approved_at = datetime.now(timezone.utc)

    request = DraftRequest(
        topic="making AI-assisted writing inspectable",
        audience="AI builders and thoughtful creators",
        point_of_view="First person, grounded only in supplied workshop experience",
        facts=(
            "The workflow separates corpus audit, voice approval, claim approval, storyboard approval, and export.\n"
            "Raw historical post text remains local and is excluded from model payloads.\n"
            "Each completed pair includes a post, storyboard, GIF, fallback PNG, alt text, and manifest."
        ),
        source_urls=["Workshop requirements supplied by the project owner"],
        personal_experience="I wanted a demo that showed my judgment, not only a generated final answer.",
    )
    studio = AIStudio(client=None)
    package = studio.generate_draft("showcase-001", profile, request)
    package.claim_approved = True
    package.post_approved = True
    storyboard = studio.generate_storyboard(package)
    storyboard.approved = True
    output_dir, manifest = write_pair_package(package, storyboard, ROOT / "outputs", review_complete=True)
    manifest.review_complete = True
    (output_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    showcase_dir = export_showcase(profile, package, storyboard, manifest, output_dir, ROOT / "showcase")
    public_data = json.loads((showcase_dir / "showcase.json").read_text(encoding="utf-8"))
    public_data["label"] = "Illustrative synthetic demo"
    public_data["demo_notice"] = "The example corpus is synthetic. Replace it with an explicitly approved real run before presenting this as your personal writing profile."
    (showcase_dir / "showcase.json").write_text(json.dumps(public_data, indent=2), encoding="utf-8")

    site_dist = ROOT / "site" / "dist"
    (site_dist / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy2(showcase_dir / "showcase.json", site_dist / "showcase.json")
    for asset in ("infographic.gif", "fallback.png"):
        shutil.copy2(showcase_dir / "assets" / asset, site_dist / "assets" / asset)
    print(f"Demo corpus: {csv_path}")
    print(f"Valid posts: {audit.valid_count}; target met: {audit.target_sample_met}")
    print(f"Pair package: {output_dir}")
    print(f"Public showcase: {site_dist}")


if __name__ == "__main__":
    main()
