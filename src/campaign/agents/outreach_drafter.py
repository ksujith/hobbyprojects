"""Step 3 — Outreach Drafter.

Phase 1: deterministic stub mirroring legacy `simulate_outreach_generation`.
Phase 2: real Claude call (`opus-4-7`) with persona-cached system prompt.
"""
from __future__ import annotations

from dataclasses import dataclass

from campaign.schemas import LeadAnalysisIn, LeadIn
from campaign.services import anthropic as svc


@dataclass(frozen=True)
class DraftContent:
    subject: str
    body: str
    personalization_score: int
    sentiment_score: float
    word_count: int


async def run(
    lead: LeadIn,
    analysis: LeadAnalysisIn,
    persona_name: str,
    persona_title: str,
    persona_company: str,
    company_summary: str | None,
    ea_deferral_line: str | None,
) -> DraftContent:
    try:
        await svc.create_message(
            caller="outreach_drafter",
            model="claude-opus-4-7",
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": _user_prompt(
                        lead, analysis, persona_name, persona_title, persona_company, company_summary
                    ),
                }
            ],
            max_tokens=1000,
        )
        return _stub(lead, persona_name, persona_title, persona_company, ea_deferral_line)
    except svc.DemoModeBlockError:
        return _stub(lead, persona_name, persona_title, persona_company, ea_deferral_line)


_SYSTEM = (
    "You write short, specific B2B cold outreach. Constraints: ≤150 words, one clear "
    "CTA, reference the recent milestone by name, zero generic filler. Output subject "
    "line + body."
)


def _user_prompt(
    lead: LeadIn,
    analysis: LeadAnalysisIn,
    persona_name: str,
    persona_title: str,
    persona_company: str,
    company_summary: str | None,
) -> str:
    return (
        f"From: {persona_name} · {persona_title} at {persona_company}\n"
        f"To: {lead.decision_maker} ({lead.position}) at {lead.company_name}\n"
        f"Recent milestone: {lead.milestone}\n"
        f"Priority: {analysis.priority} · fit={analysis.fit_score}\n"
        f"Pain points: {', '.join(analysis.pain_points[:3])}\n"
        + (f"Company summary: {company_summary}\n" if company_summary else "")
    )


def _stub(
    lead: LeadIn,
    persona_name: str,
    persona_title: str,
    persona_company: str,
    ea_deferral_line: str | None,
) -> DraftContent:
    subject = f"Congrats on {lead.milestone}"
    body = (
        f"Hi {lead.decision_maker.split()[0]},\n\n"
        f"Congrats on the recent {lead.milestone} at {lead.company_name} — real momentum in the "
        f"{lead.industry} space takes focus and it's clearly showing.\n\n"
        f"At {persona_company} we help {lead.industry.lower()} teams turn that kind of moment into "
        f"durable operating leverage — the kind that compounds after launch day. Worth a 15-minute "
        f"conversation to see if there's a fit?\n"
    )
    if ea_deferral_line:
        body += f"\n{ea_deferral_line}\n"
    body += f"\nBest,\n{persona_name}\n{persona_title} · {persona_company}"

    word_count = len(body.split())
    # mild sentiment estimator — not a real model; stub.
    positive_words = sum(body.lower().count(w) for w in ("congrats", "momentum", "durable", "fit"))
    sentiment = max(-1.0, min(1.0, 0.5 + 0.1 * positive_words))
    # personalization score: starts at 70, +10 for each personalization token present
    score = 70
    for tok in (lead.company_name, lead.decision_maker.split()[0], lead.milestone):
        if tok in body:
            score += 10
    score = min(score, 100)

    return DraftContent(
        subject=subject,
        body=body,
        personalization_score=score,
        sentiment_score=round(sentiment, 2),
        word_count=word_count,
    )
