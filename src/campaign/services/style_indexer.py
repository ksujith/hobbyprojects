"""Style indexer — extract brand-voice signals from a persona's past drafts.

For a given persona, scan drafts they've authored whose `personalization_score
>= threshold` and surface:
  - average word count
  - dominant signoff (last line that isn't the company line)
  - top-N bigrams across bodies (excluding stopwords)

The output is intentionally small — it's injected as a style hint into the
`OutreachDrafter` system prompt in Phase 2. No ML models, no embeddings.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select

from campaign.db import models as m
from campaign.db.session import session_scope

# Keep the stopword list small and anglo — this is a style cue, not a
# classifier. The LLM does the rest.
_STOPWORDS = frozenset(
    """
    a an and are as at be been being by for from has have he her him his i in is it its of on
    or our she that the their them there these they this to us was we were will with you your
    hi hey dear best cheers regards thanks thank
    """.split()
)

_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z'-]{1,}")


@dataclass(frozen=True)
class StyleProfile:
    persona_id: str
    draft_count: int
    avg_word_count: float
    dominant_signoff: str | None
    top_bigrams: list[tuple[str, int]]

    def to_style_hint(self) -> str:
        """Compact, LLM-readable summary for prompt injection."""
        parts: list[str] = []
        if self.draft_count == 0:
            return ""
        parts.append(f"Target ≈{int(round(self.avg_word_count))} words.")
        if self.dominant_signoff:
            parts.append(f"Sign off with: '{self.dominant_signoff}'.")
        if self.top_bigrams:
            phrases = ", ".join(f"'{a} {b}'" for (a, b), _ in self.top_bigrams[:5])
            parts.append(f"Recurring phrases to echo: {phrases}.")
        return " ".join(parts)


def _bigrams(text: str) -> Iterable[tuple[str, str]]:
    tokens = [t.lower() for t in _TOKEN.findall(text) if t.lower() not in _STOPWORDS]
    for i in range(len(tokens) - 1):
        yield tokens[i], tokens[i + 1]


def _extract_signoff(body: str) -> str | None:
    """Return the line right before the last non-empty line (i.e. the word
    before the signature — 'Best,' or 'Cheers,' etc.)."""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    # Last line is usually the persona's title line; preceding is the name;
    # before that is the signoff word.
    for candidate in reversed(lines):
        if re.fullmatch(r"(Best|Cheers|Regards|Thanks|Sincerely|Warmly),?", candidate):
            return candidate.rstrip(",")
    return None


async def build(persona_id: str, *, min_personalization: int = 80) -> StyleProfile:
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(m.Draft)
                .join(m.Campaign, m.Campaign.id == m.Draft.campaign_id)
                .where(m.Campaign.persona_id == persona_id)
                .where(m.Draft.personalization_score >= min_personalization)
            )
        ).scalars().all()

    if not rows:
        return StyleProfile(persona_id=persona_id, draft_count=0, avg_word_count=0.0,
                            dominant_signoff=None, top_bigrams=[])

    avg_wc = sum(d.word_count for d in rows) / len(rows)

    signoffs = Counter(_extract_signoff(d.body) for d in rows)
    signoffs.pop(None, None)
    dominant = signoffs.most_common(1)[0][0] if signoffs else None

    bigram_counter: Counter[tuple[str, str]] = Counter()
    for d in rows:
        bigram_counter.update(_bigrams(d.body))

    return StyleProfile(
        persona_id=persona_id,
        draft_count=len(rows),
        avg_word_count=round(avg_wc, 1),
        dominant_signoff=dominant,
        top_bigrams=bigram_counter.most_common(8),
    )
