"""DraftRefiner — apply a short critique to an existing draft.

Phase 1: deterministic rule-based transformer keyed off common critiques.
Phase 2: Claude with the previous draft + critique → refined draft.
"""
from __future__ import annotations

from dataclasses import dataclass

from campaign.config import get_settings
from campaign.services import anthropic as svc


@dataclass(frozen=True)
class RefinedDraft:
    subject: str
    body: str


async def run(*, subject: str, body: str, critique: str) -> RefinedDraft:
    try:
        await svc.create_message(
            caller="draft_refiner",
            model=get_settings().llm_extraction_model,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"CRITIQUE: {critique}\n\nDRAFT:\n{body}"}],
            max_tokens=800,
        )
        return _stub(subject, body, critique)
    except svc.DemoModeBlockError:
        return _stub(subject, body, critique)


_SYSTEM = (
    "You iterate on cold-outreach drafts. Given a draft and a one-line critique, "
    "rewrite the draft to satisfy the critique while preserving the key facts "
    "(company name, milestone, signature)."
)


def _stub(subject: str, body: str, critique: str) -> RefinedDraft:
    c = critique.lower()
    new_body = body

    if "shorter" in c or "concise" in c or "tighten" in c:
        # Keep only 1st + last paragraph.
        paras = [p for p in new_body.split("\n\n") if p.strip()]
        if len(paras) > 2:
            new_body = paras[0] + "\n\n" + paras[-1]

    if "informal" in c or "casual" in c or "friendly" in c:
        new_body = new_body.replace("Best,", "Cheers,")
        new_body = new_body.replace("Congrats on", "Loved seeing")

    if "formal" in c:
        new_body = new_body.replace("Hi ", "Dear ")
        new_body = new_body.replace("Cheers,", "Best regards,")

    if ("cta" in c or "call to action" in c or "action" in c) and "15-minute" in new_body:
        new_body = new_body.replace(
            "15-minute conversation",
            "15-minute call this week — Thu or Fri work?",
        )

    # If nothing matched, normalise paragraph spacing.
    if new_body == body:
        paras = [p for p in new_body.split("\n\n") if p.strip()]
        new_body = "\n\n".join(paras)

    return RefinedDraft(subject=subject, body=new_body)
