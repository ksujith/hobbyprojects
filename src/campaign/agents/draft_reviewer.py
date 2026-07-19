"""DraftReviewer — the "Tester" node of the draft quality loop.

Pattern: Code → Test → Fix → Repeat, applied to outreach drafts:
  OutreachDrafter (code) → DraftReviewer (test) → DraftRefiner (fix) → repeat
until the draft passes or `draft_review_max_iterations` is exhausted.

Phase 1: deterministic rubric — length, CTA, personalization, tone. Explainable
and offline-testable. Phase 2: Claude structured-output review for nuance
(clarity, spam-trigger phrasing, subject-line strength).
"""
from __future__ import annotations

from dataclasses import dataclass

from campaign.config import get_settings
from campaign.services import anthropic as svc


@dataclass(frozen=True)
class Review:
    passed: bool
    score: int              # 0..100
    critique: str           # empty when passed; feeds DraftRefiner when not


async def run(
    *,
    body: str,
    word_count: int,
    personalization_score: int,
    sentiment_score: float,
) -> Review:
    try:
        await svc.create_message(
            caller="draft_reviewer",
            model=get_settings().llm_extraction_model,
            system=_SYSTEM,
            messages=[{"role": "user", "content": body}],
            max_tokens=300,
        )
        return _stub(body, word_count, personalization_score, sentiment_score)
    except svc.DemoModeBlockError:
        return _stub(body, word_count, personalization_score, sentiment_score)


_SYSTEM = (
    "You review B2B cold-outreach drafts against a rubric: ≤150 words, one clear "
    "CTA question, specific personalization (company + milestone by name), warm "
    "tone. Return a 0-100 score and a one-line critique for anything failing."
)


def _stub(
    body: str, word_count: int, personalization_score: int, sentiment_score: float
) -> Review:
    settings = get_settings()
    score = 100
    critiques: list[str] = []

    if word_count > 150:
        score -= 20
        critiques.append("shorter — cut to under 150 words")
    if "?" not in body:
        score -= 20
        critiques.append("end with a clear call to action question")
    if personalization_score < settings.personalization_min_score:
        score -= 25
        critiques.append("reference the company and milestone by name")
    if sentiment_score < 0.2:
        score -= 15
        critiques.append("warm up the tone")

    passed = score >= settings.draft_review_pass_score
    return Review(passed=passed, score=score, critique="; ".join(critiques))
