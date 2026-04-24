from __future__ import annotations

import pytest

from campaign.agents import (
    calendaring_detector,
    draft_refiner,
    lead_analyzer,
    outreach_drafter,
)
from campaign.schemas import LeadIn


def _lead(milestone: str = "Series B funding announcement") -> LeadIn:
    return LeadIn(
        company_name="Acme Corp",
        industry="SaaS",
        decision_maker="Sam Taylor",
        position="VP Data",
        milestone=milestone,
    )


@pytest.mark.asyncio
async def test_lead_analyzer_high_priority_on_high_signals() -> None:
    a = await lead_analyzer.run(_lead("Series B funding announcement"))
    assert a.priority == "high"
    assert a.fit_score > 0.7
    assert a.bant.timeline >= 3


@pytest.mark.asyncio
async def test_lead_analyzer_medium_priority_on_vague_signals() -> None:
    a = await lead_analyzer.run(_lead("hired a new head of engineering"))
    assert a.priority == "medium"


@pytest.mark.asyncio
async def test_outreach_drafter_personalises() -> None:
    lead = _lead()
    a = await lead_analyzer.run(lead)
    d = await outreach_drafter.run(
        lead=lead,
        analysis=a,
        persona_name="Alex Rivera",
        persona_title="Head of Partnerships",
        persona_company="AICRM",
        company_summary=None,
        ea_deferral_line=None,
    )
    assert "Acme Corp" in d.body
    assert "Sam" in d.body
    assert "Series B" in d.body
    assert d.personalization_score >= 80
    assert d.word_count < 250  # keep outreach short


@pytest.mark.asyncio
async def test_draft_refiner_shortens() -> None:
    long = "Hi Sam,\n\nP1\n\nP2\n\nP3\n\nBest,\nAlex"
    r = await draft_refiner.run(subject="s", body=long, critique="shorter")
    assert len(r.body) <= len(long)


@pytest.mark.asyncio
async def test_draft_refiner_casual_swaps_signoff() -> None:
    body = "Hi Sam,\n\nCongrats on the funding!\n\nBest,\nAlex"
    r = await draft_refiner.run(subject="s", body=body, critique="more casual please")
    assert "Cheers," in r.body or "Best," not in r.body


def test_calendaring_detector_needs_two_signals() -> None:
    assert not calendaring_detector.is_scheduling("General congrats on the milestone")
    assert calendaring_detector.is_scheduling(
        "Would a 15-minute call work later this week?"
    )
