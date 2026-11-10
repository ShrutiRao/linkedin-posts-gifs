from __future__ import annotations

import re
from collections import Counter
from statistics import mean, median

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import CorpusPost, VoiceObservation, VoiceProfile


WORD = re.compile(r"\b[\w'-]+\b", re.UNICODE)
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _words(text: str) -> list[str]:
    return WORD.findall(text)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE.split(text.strip()) if part.strip()]


def _excerpt(text: str, limit: int = 140) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def _support(posts: list[CorpusPost], predicate, limit: int = 3) -> tuple[list[str], list[str]]:
    matches = [post for post in posts if predicate(post.text)][:limit]
    return [post.post_id for post in matches], [_excerpt(post.text) for post in matches]


def analyze_voice(posts: list[CorpusPost], version: int = 1) -> VoiceProfile:
    if len(posts) < 3:
        raise ValueError("At least three posts are required for voice analysis")
    word_counts = [len(_words(post.text)) for post in posts]
    sentence_lengths = [len(_words(sentence)) for post in posts for sentence in _sentences(post.text)]
    paragraph_counts = [len([p for p in post.text.splitlines() if p.strip()]) for post in posts]
    question_share = sum("?" in post.text for post in posts) / len(posts)
    first_person_share = sum(bool(re.search(r"\b(I|I'm|I've|my|me)\b", post.text, re.I)) for post in posts) / len(posts)
    hashtag_share = sum("#" in post.text for post in posts) / len(posts)

    observations: list[VoiceObservation] = []

    ids = [post.post_id for post in posts[:3]]
    excerpts = [_excerpt(post.text) for post in posts[:3]]
    observations.append(
        VoiceObservation(
            category="length",
            pattern=f"Typical posts are about {round(median(word_counts))} words across {round(median(paragraph_counts))} short paragraphs.",
            supporting_post_ids=ids,
            excerpts=excerpts,
            confidence=min(0.95, 0.55 + len(posts) / 100),
            kind="observation",
        )
    )
    observations.append(
        VoiceObservation(
            category="sentence rhythm",
            pattern=f"Sentences average {round(mean(sentence_lengths), 1) if sentence_lengths else 0} words, favoring a direct reading rhythm.",
            supporting_post_ids=ids,
            excerpts=excerpts,
            confidence=0.8,
            kind="observation",
        )
    )

    question_ids, question_excerpts = _support(posts, lambda text: "?" in text)
    observations.append(
        VoiceObservation(
            category="endings",
            pattern=f"Questions appear in {question_share:.0%} of the sample; use them only when they invite a specific response.",
            supporting_post_ids=question_ids or ids,
            excerpts=question_excerpts or excerpts,
            confidence=0.78,
            kind="observation",
        )
    )

    pov_ids, pov_excerpts = _support(posts, lambda text: bool(re.search(r"\b(I|I'm|I've|my|me)\b", text, re.I)))
    observations.append(
        VoiceObservation(
            category="point of view",
            pattern=f"First-person language appears in {first_person_share:.0%} of the sample and is tied to concrete experience.",
            supporting_post_ids=pov_ids or ids,
            excerpts=pov_excerpts or excerpts,
            confidence=0.82,
            kind="observation",
        )
    )

    tokens = [token.lower() for post in posts for token in _words(post.text) if len(token) > 3]
    stop = {"that", "this", "with", "from", "have", "your", "about", "what", "when", "they", "their", "will", "just", "into", "more", "than"}
    recurring = [word for word, count in Counter(token for token in tokens if token not in stop).most_common(8) if count >= 2]
    recurring_text = ", ".join(recurring[:5]) if recurring else "No stable recurring phrases yet"
    observations.append(
        VoiceObservation(
            category="recurring language",
            pattern=f"Recurring content language includes: {recurring_text}.",
            supporting_post_ids=ids,
            excerpts=excerpts,
            confidence=0.65,
            kind="observation",
        )
    )

    rules = [
        f"Aim for roughly {max(60, round(median(word_counts) * 0.8))}–{round(median(word_counts) * 1.2)} words unless the idea needs less.",
        "Use short paragraphs and concrete examples before abstract conclusions.",
        "Write in first person only for experience the author explicitly supplied.",
        "Make one clear claim and connect every factual statement to supplied evidence.",
        "End with a specific implication or focused question, not a generic engagement prompt.",
    ]
    if hashtag_share < 0.2:
        rules.append("Do not add hashtags unless the author requests them.")
    recommendations = [
        VoiceObservation(
            category="editorial guardrail",
            pattern=rule,
            supporting_post_ids=[],
            excerpts=[],
            confidence=1.0,
            kind="recommendation",
        )
        for rule in (
            "Do not invent personal experiences, results, clients, employers, or opinions.",
            "Remove any sentence that sounds like generic creator advice rather than this author's preference.",
        )
    ]
    observations.extend(recommendations)
    return VoiceProfile(
        version=version,
        observations=observations,
        approved_rules=rules,
        prohibited_behaviors=[
            "Invented personal experience",
            "Unsupported factual claims",
            "Attributing other people's content to the author",
            "Generic personal claims",
        ],
        preferences={
            "median_words": str(round(median(word_counts))),
            "median_paragraphs": str(round(median(paragraph_counts))),
        },
    )


def retrieve_similar(posts: list[CorpusPost], query: str, limit: int = 3) -> list[tuple[CorpusPost, float]]:
    if not posts or not query.strip():
        return []
    corpus = [post.text for post in posts] + [query]
    matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(corpus)
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:limit]
    return [(posts[index], float(score)) for index, score in ranked]

