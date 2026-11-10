# LinkedIn Post and GIF Studio

A privacy-first Streamlit workflow that analyzes your LinkedIn writing locally, turns the findings into an inspectable voice guide, drafts a source-grounded post, and renders an approved branded GIF package.

## What stays private

Imported posts, excerpts, local retrieval results, SQLite state, and unapproved outputs remain under `data/private/` or `outputs/` and are ignored by Git. OpenAI requests contain only approved derived voice rules plus the topic, facts, sources, and personal experience supplied for the new draft.

## Quick start

```powershell
uv sync --extra dev
Copy-Item .env.example .env
uv run streamlit run app.py
```

Set `OPENAI_API_KEY` in `.env` for model-backed drafting. Without a key, the app uses a clearly labeled deterministic demo generator so the approval and rendering workflow can still be evaluated.

Generate the synthetic demo, artifact package, and public showcase:

```powershell
uv run python scripts/create_demo.py
uv run python scripts/build_site.py
```

Run tests:

```powershell
uv run pytest
```

## Workflow

1. Import 20–40 authored LinkedIn posts and inspect data quality.
2. Review source-backed local observations and approve the editable voice profile.
3. Supply a topic, audience, point of view, facts, sources, and real experience.
4. Generate three hooks and one draft; approve the post and main claim.
5. Generate and approve a storyboard, then render the GIF, fallback PNG, alt text, and manifest.
6. Review the pair and export a sanitized public showcase.

The app never publishes to LinkedIn.

## Repository layout

- `app.py` — Streamlit workflow.
- `src/linkedin_gif_studio/` — models, audit, analysis, AI boundary, persistence, rendering, and export.
- `scripts/create_demo.py` — creates a synthetic end-to-end example.
- `site/dist/` — static public showcase ready for Sites hosting.
- `tests/` — privacy, validation, gating, rendering, and export tests.
- `RECORDING_SCRIPT.md` — shot list for the final 2–3 minute personal walkthrough.
