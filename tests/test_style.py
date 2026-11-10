from __future__ import annotations

from linkedin_gif_studio.style import analyze_voice, retrieve_similar


def test_every_observation_has_existing_support(posts) -> None:
    profile = analyze_voice(posts)
    known = {post.post_id for post in posts}
    for item in profile.observations:
        if item.kind == "observation":
            assert item.supporting_post_ids
            assert set(item.supporting_post_ids) <= known
        else:
            assert item.kind == "recommendation"


def test_local_retrieval_returns_ranked_posts(posts) -> None:
    results = retrieve_similar(posts, "inspectable workflow", limit=3)
    assert len(results) == 3
    assert all(post in posts for post, _ in results)
    assert results[0][1] >= results[-1][1]

