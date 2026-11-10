from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from linkedin_gif_studio.ai import AIStudio, DraftRequest
from linkedin_gif_studio.corpus import load_corpus, posts_to_frame
from linkedin_gif_studio.models import DraftPackage, StoryboardFrame, StoryboardSpec, VoiceProfile
from linkedin_gif_studio.render import write_pair_package
from linkedin_gif_studio.showcase import export_showcase
from linkedin_gif_studio.sources import extract_public_sources
from linkedin_gif_studio.storage import StudioStore
from linkedin_gif_studio.style import analyze_voice, retrieve_similar
from linkedin_gif_studio.workflow import draft_gate, render_gate, visual_gate

load_dotenv()

st.set_page_config(page_title="LinkedIn Post + GIF Studio", page_icon="✦", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background: #f7f4e9; color: #101820; }
      [data-testid="stSidebar"] { background: #101820; }
      [data-testid="stSidebar"] * { color: #f7f4e9; }
      h1, h2, h3 { letter-spacing: -0.025em; }
      .eyebrow { color:#3157d5; text-transform:uppercase; font-weight:800; letter-spacing:.12em; }
      .gate { padding: .8rem 1rem; border-left: 5px solid #f6c900; background: #fffdf5; }
      .privacy { padding: .8rem 1rem; border-left: 5px solid #3157d5; background: #eef2ff; }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize() -> None:
    defaults = {
        "posts": [],
        "audit": None,
        "profile": None,
        "draft": None,
        "storyboard": None,
        "pair_dir": None,
        "manifest": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def gate_message(reasons: list[str]) -> None:
    st.markdown('<div class="gate"><strong>Locked</strong><br>' + "<br>".join(reasons) + "</div>", unsafe_allow_html=True)


initialize()
store = StudioStore(os.getenv("LINKEDIN_GIF_DB", "data/private/studio.db"))
ai = AIStudio()

with st.sidebar:
    st.markdown("## ✦ AI Native Studio")
    page = st.radio(
        "Workflow",
        ["Start", "1 · Corpus audit", "2 · Voice guide", "3 · Draft post", "4 · Storyboard", "5 · Review + export"],
    )
    st.divider()
    st.caption("PRIVATE BY DESIGN")
    st.write("Historical post text stays in this local app.")
    if ai.is_demo_mode:
        st.warning("Demo generator active — set OPENAI_API_KEY for model-backed drafting.")
    else:
        st.success(f"OpenAI connected · {ai.model}")


if page == "Start":
    st.markdown('<p class="eyebrow">LinkedIn post + GIF studio</p>', unsafe_allow_html=True)
    st.title("Make your writing process inspectable.")
    st.write(
        "This studio learns observable patterns from posts you authored, turns those findings into an editable voice guide, "
        "and creates a post and motion pair through explicit approval gates."
    )
    st.markdown(
        '<div class="privacy"><strong>The privacy boundary</strong><br>'
        "Raw posts, excerpts, and local retrieval results never enter the model request. Only approved derived rules and "
        "the facts you supply for a new post cross that boundary.</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(5)
    for col, number, label in zip(cols, ["01", "02", "03", "04", "05"], ["Audit", "Voice", "Draft", "Motion", "Review"]):
        with col:
            st.metric(label, number)
    st.subheader("Definition of done")
    st.write("One approved, traceable post paired with one readable GIF, static fallback, alt text, and manifest. Nothing is published automatically.")


elif page == "1 · Corpus audit":
    st.markdown('<p class="eyebrow">Step 1</p>', unsafe_allow_html=True)
    st.title("Audit the source material")
    st.write("Upload a CSV containing only posts you authored. A varied sample of 20–40 posts is ideal.")
    uploaded = st.file_uploader("LinkedIn posts CSV", type=["csv"])
    if uploaded and st.button("Run private audit", type="primary"):
        try:
            posts, audit, _ = load_corpus(uploaded.getvalue())
            st.session_state.posts = posts
            st.session_state.audit = audit
            private = Path("data/private")
            private.mkdir(parents=True, exist_ok=True)
            posts_to_frame(posts).to_csv(private / "normalized_posts.csv", index=False)
        except Exception as exc:
            st.error(f"Could not import the corpus: {exc}")
    audit = st.session_state.audit
    if audit:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows supplied", audit.row_count)
        c2.metric("Valid authored posts", audit.valid_count)
        c3.metric("20–40 target", "Met" if audit.target_sample_met else "Not yet")
        c4.metric("Metrics comparable", "Yes" if audit.metrics_comparable else "No")
        st.subheader("Coverage")
        st.dataframe(pd.DataFrame([{"field": key, "missing": value} for key, value in audit.missing_by_field.items()]), hide_index=True, use_container_width=True)
        issues = {
            "Duplicate IDs": audit.duplicate_ids,
            "Malformed date rows": audit.malformed_dates,
            "Broken permalinks": audit.broken_permalinks,
        }
        st.subheader("Issues")
        for label, values in issues.items():
            st.write(f"**{label}:** {values or 'None'}")
        for note in audit.notes:
            st.info(note)
        if st.session_state.posts:
            st.subheader("Normalized private corpus")
            visible = posts_to_frame(st.session_state.posts).drop(columns=["text"], errors="ignore")
            st.dataframe(visible, hide_index=True, use_container_width=True)


elif page == "2 · Voice guide":
    st.markdown('<p class="eyebrow">Step 2</p>', unsafe_allow_html=True)
    st.title("Draft and approve the voice guide")
    if len(st.session_state.posts) < 3:
        gate_message(["Import at least three valid posts in Corpus audit."])
    else:
        if st.button("Analyze writing locally", type="primary"):
            version = (st.session_state.profile.version + 1) if st.session_state.profile else 1
            st.session_state.profile = analyze_voice(st.session_state.posts, version=version)
        profile: VoiceProfile | None = st.session_state.profile
        if profile:
            st.caption("Observed patterns cite post IDs and local excerpts. Recommendations are labeled separately.")
            for observation in profile.observations:
                with st.expander(f"{observation.category.title()} · {observation.kind}", expanded=observation.kind == "observation"):
                    st.write(observation.pattern)
                    if observation.supporting_post_ids:
                        st.caption("Evidence: " + ", ".join(observation.supporting_post_ids))
                        for excerpt in observation.excerpts:
                            st.code(excerpt, language=None)
            rules_text = st.text_area("Approved voice rules — one per line", "\n".join(profile.approved_rules), height=220)
            prohibited_text = st.text_area("Never do — one per line", "\n".join(profile.prohibited_behaviors), height=130)
            acknowledged = st.checkbox("I reviewed these rules and corrected anything that sounded generic rather than like me.")
            if st.button("Approve voice profile", disabled=not acknowledged, type="primary"):
                profile.approved_rules = [line.strip() for line in rules_text.splitlines() if line.strip()]
                profile.prohibited_behaviors = [line.strip() for line in prohibited_text.splitlines() if line.strip()]
                profile.approved_at = datetime.now(timezone.utc)
                store.save_profile(profile)
                st.session_state.profile = profile
                st.success(f"Voice profile v{profile.version} approved and saved locally.")


elif page == "3 · Draft post":
    st.markdown('<p class="eyebrow">Step 3</p>', unsafe_allow_html=True)
    st.title("Create a source-grounded draft")
    profile = st.session_state.profile or store.latest_profile()
    gate = draft_gate(profile)
    if not gate.allowed:
        gate_message(gate.reasons)
    else:
        with st.form("draft_form"):
            topic = st.text_input("Topic", placeholder="e.g. Why approval gates make AI content more trustworthy")
            audience = st.text_input("Audience", value="AI builders and thoughtful creators")
            pov = st.text_input("Point of view", value="First person, based only on supplied experience")
            facts = st.text_area("Facts or notes", placeholder="One supported fact per line. Include enough evidence to stand behind the claim.", height=150)
            urls = st.text_area("Public source URLs — one per line", height=90)
            experience = st.text_area("Real personal experience (optional)", height=100)
            submitted = st.form_submit_button("Generate three hooks + one post", type="primary")
        if submitted:
            source_urls = [line.strip() for line in urls.splitlines() if line.strip()]
            extracted = extract_public_sources(source_urls) if source_urls else []
            failures = [item for item in extracted if item.error]
            if failures and not facts.strip():
                st.error("A source URL could not be extracted. Paste the relevant facts or notes before generating: " + "; ".join(f"{item.url}: {item.error}" for item in failures))
                st.stop()
            source_facts = "\n\n".join(f"[Public source: {item.url}]\n{item.text}" for item in extracted if item.text)
            combined_facts = "\n\n".join(part for part in (facts.strip(), source_facts) if part)
            for item in failures:
                st.warning(f"Could not extract {item.url}; using your pasted notes instead. {item.error}")
            request = DraftRequest(
                topic=topic,
                audience=audience,
                point_of_view=pov,
                facts=combined_facts,
                source_urls=source_urls,
                personal_experience=experience,
            )
            with st.spinner("Drafting from approved rules and supplied evidence…"):
                try:
                    post_id = f"post-{uuid4().hex[:8]}"
                    draft = ai.generate_draft(post_id, profile, request)
                    st.session_state.draft = draft
                    store.save_draft(draft)
                except Exception as exc:
                    st.error(f"Draft generation failed: {exc}")
        draft: DraftPackage | None = st.session_state.draft
        if draft:
            st.subheader("Choose the opening")
            selected = st.radio("Three hooks", draft.hooks, index=draft.hooks.index(draft.selected_hook))
            if selected != draft.selected_hook:
                old_hook = draft.selected_hook
                draft.selected_hook = selected
                if draft.post_text.startswith(old_hook):
                    draft.post_text = selected + draft.post_text[len(old_hook) :]
            draft.post_text = st.text_area("Editable post", draft.post_text, height=360)
            draft.main_claim = st.text_area("Main claim", draft.main_claim, height=90)
            st.write("**Supporting evidence**")
            st.write(draft.supporting_evidence or "No evidence supplied")
            st.write("**Sources**")
            st.write(draft.sources or "No external sources supplied")
            if draft.warnings:
                st.error("Resolve before approval: " + " · ".join(draft.warnings))
                if st.checkbox("I supplied evidence outside the generator and resolved these warnings."):
                    if st.button("Mark warnings resolved"):
                        draft.warnings = []
            draft.claim_approved = st.checkbox("I endorse this claim and its evidence.", value=draft.claim_approved)
            draft.post_approved = st.checkbox("This draft sounds like me and is ready for visual design.", value=draft.post_approved)
            if st.button("Save draft approvals", type="primary"):
                store.save_draft(draft)
                st.session_state.draft = draft
                st.success("Draft saved. Visual generation is unlocked when both approvals are checked and warnings are resolved.")


elif page == "4 · Storyboard":
    st.markdown('<p class="eyebrow">Step 4</p>', unsafe_allow_html=True)
    st.title("Storyboard before rendering")
    draft = st.session_state.draft
    gate = visual_gate(draft)
    if not gate.allowed:
        gate_message(gate.reasons)
    else:
        if st.button("Generate one storyboard", type="primary"):
            try:
                st.session_state.storyboard = ai.generate_storyboard(draft)
            except Exception as exc:
                st.error(f"Storyboard generation failed: {exc}")
        storyboard: StoryboardSpec | None = st.session_state.storyboard
        if storyboard:
            storyboard.concept = st.text_input("Concept", storyboard.concept)
            frame_rows = [frame.model_dump() for frame in storyboard.frames]
            edited = st.data_editor(pd.DataFrame(frame_rows), hide_index=True, use_container_width=True, num_rows="fixed")
            try:
                storyboard.frames = [StoryboardFrame.model_validate(row) for row in edited.to_dict(orient="records")]
                storyboard.total_loop_seconds = sum(frame.duration_seconds for frame in storyboard.frames)
            except Exception as exc:
                st.error(f"Fix the storyboard fields: {exc}")
            storyboard.alt_text = st.text_area("Alt text", storyboard.alt_text, height=100)
            storyboard.approved = st.checkbox("I approve this storyboard and confirm it adds no new factual claims.", value=storyboard.approved)
            if st.button("Save storyboard", type="primary"):
                store.save_storyboard(storyboard)
                st.session_state.storyboard = storyboard
                st.success("Storyboard saved.")
            brand = st.text_input("Brand name", value="AI Native Studio")
            gate = render_gate(draft, storyboard)
            if gate.allowed and st.button("Render GIF package", type="primary"):
                with st.spinner("Rendering readable 1080×1080 frames…"):
                    pair_dir, manifest = write_pair_package(draft, storyboard, brand_name=brand)
                    st.session_state.pair_dir = pair_dir
                    st.session_state.manifest = manifest
                st.success(f"Rendered {pair_dir}")
                st.image(str(pair_dir / "infographic.gif"))
            elif not gate.allowed:
                gate_message(gate.reasons)


else:
    st.markdown('<p class="eyebrow">Step 5</p>', unsafe_allow_html=True)
    st.title("Review the words and the motion")
    draft = st.session_state.draft
    storyboard = st.session_state.storyboard
    pair_dir = st.session_state.pair_dir
    manifest = st.session_state.manifest
    if not all([draft, storyboard, pair_dir, manifest]):
        gate_message(["Complete and render an approved pair first."])
    else:
        left, right = st.columns([1, 1])
        with left:
            st.subheader("Approved post")
            st.code(draft.post_text, language=None)
            st.write(f"**Claim:** {draft.main_claim}")
            st.write(f"**Sources:** {', '.join(draft.sources) if draft.sources else 'Supplied notes / experience'}")
        with right:
            st.subheader("Motion asset")
            st.image(str(Path(pair_dir) / "infographic.gif"))
            st.caption(storyboard.alt_text)
        checks = [
            "The draft sounds like me and makes a point I endorse.",
            "Factual claims have sources or supplied personal context.",
            "The post has its own matching GIF, static fallback, and alt text.",
            "The GIF opens as an animated file and the fallback remains understandable.",
            "Text is readable before the frame changes.",
            "The loop is clean and the visual does not contradict the post.",
            "Nothing was published as part of drafting.",
        ]
        values = [st.checkbox(item, key=f"review-{index}") for index, item in enumerate(checks)]
        revision = st.text_area("Targeted revision instruction (optional)", placeholder="Change one wording or visual behavior while preserving the approved claim.")
        if revision and st.button("Record revision request"):
            store.record_revision(draft.post_id, "pair", revision, draft.main_claim)
            st.info("Revision request recorded. Return to the relevant step to make the change.")
        all_reviewed = all(values)
        include_real = st.checkbox("I explicitly approve any real excerpts listed below for public display.", value=False)
        st.caption("No corpus excerpts are exported by default; this checkbox is recorded for future explicit selections.")
        if st.button("Export sanitized public showcase", disabled=not all_reviewed, type="primary"):
            manifest.review_complete = True
            (Path(pair_dir) / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
            destination = export_showcase(
                st.session_state.profile,
                draft,
                storyboard,
                manifest,
                pair_dir,
                approved_excerpt_ids=[] if not include_real else [],
            )
            st.success(f"Sanitized showcase exported to {destination}. No corpus text was included.")
        st.subheader("Required artifact package")
        st.write(sorted(path.name for path in Path(pair_dir).iterdir()))
