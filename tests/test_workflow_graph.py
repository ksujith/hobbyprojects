"""Agentic patterns: draft quality loop (Code→Test→Fix) + reply router graph."""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from campaign.agents import draft_reviewer
from campaign.agents.reply_workers import ReplyContext
from campaign.workflow.reply_graph import ROUTES, route, run_reply_graph

PERSONA_PAYLOAD = {
    "name": "Alex Rivera",
    "title": "Head of Partnerships",
    "company": "AICRM",
    "tone_guidelines": "Professional, warm, no jargon.",
}

LEAD_PAYLOAD = {
    "company_name": "Greystar",
    "industry": "Real Estate",
    "decision_maker": "Jordan Price",
    "position": "VP of RevOps",
    "milestone": "Series B funding announcement",
    "prospect_email": "jordan@greystar.example",
}


async def _run_campaign(client: AsyncClient) -> str:
    persona = (await client.post("/api/personas", json=PERSONA_PAYLOAD)).json()
    camp = (
        await client.post(
            "/api/campaigns", json={"persona_id": persona["id"], "lead": LEAD_PAYLOAD}
        )
    ).json()
    for _ in range(40):
        s = (await client.get(f"/api/campaigns/{camp['id']}")).json()["status"]
        if s in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.05)
    return camp["id"]


# ---- Approach 1: draft quality loop (Code → Test → Fix → Repeat) ----------


@pytest.mark.asyncio
async def test_reviewer_passes_good_draft() -> None:
    review = await draft_reviewer.run(
        body="Hi Jordan,\n\nCongrats on the Series B. Worth a 15-minute chat?",
        word_count=90,
        personalization_score=100,
        sentiment_score=0.9,
    )
    assert review.passed
    assert review.score == 100
    assert review.critique == ""


@pytest.mark.asyncio
async def test_reviewer_flags_weak_draft() -> None:
    review = await draft_reviewer.run(
        body="word " * 200,          # too long, no CTA question
        word_count=200,
        personalization_score=40,   # generic
        sentiment_score=0.0,
    )
    assert not review.passed
    assert review.score < 85
    assert "shorter" in review.critique
    assert "call to action" in review.critique
    assert "milestone" in review.critique


@pytest.mark.asyncio
async def test_pipeline_records_workflow_trace(client: AsyncClient) -> None:
    cid = await _run_campaign(client)
    tasks = (await client.get(f"/api/campaigns/{cid}/tasks")).json()
    agents = [t["agent_name"] for t in tasks]
    assert "LeadAnalyzer" in agents
    assert "CompanyLookup" in agents
    assert "OutreachDrafter" in agents
    assert "DraftReviewer" in agents
    # Demo-mode stub draft passes review on the first iteration.
    review = next(t for t in tasks if t["agent_name"] == "DraftReviewer")
    assert review["details"]["passed"] is True
    assert review["details"]["score"] == 100


# ---- Approach 2: router → workers ----------------------------------------


def test_router_covers_every_classification() -> None:
    for kind in ("positive_interest", "needs_info", "not_interested", "out_of_office", "bounce", "other"):
        assert kind in ROUTES
    assert route("positive_interest")[0] == "meeting_proposer"
    assert route("needs_info")[0] == "info_responder"
    assert route("unknown-kind")[0] == "generic_follow_up"


@pytest.mark.asyncio
async def test_graph_dispatches_meeting_proposer() -> None:
    ctx = ReplyContext(
        prospect_first="Jordan",
        persona_name="Alex Rivera",
        persona_title="Head of Partnerships",
        persona_company="AICRM",
        inbound_subject="Re: Congrats",
        inbound_body="We're interested — let's book a call.",
        prev_subject="Congrats on Series B",
    )
    worker, reply = await run_reply_graph("positive_interest", ctx)
    assert worker == "meeting_proposer"
    assert reply.subject == "Re: Congrats on Series B"
    assert "calendar invite" in reply.body
    assert "Alex Rivera" in reply.body


@pytest.mark.asyncio
async def test_suggest_reply_routes_by_classification(client: AsyncClient) -> None:
    cid = await _run_campaign(client)

    # needs_info → info_responder wording (answers, then re-anchors to a call)
    sim = await client.post(f"/api/campaigns/{cid}/inbox/simulate?kind=needs_info")
    r = await client.post(f"/api/inbox/{sim.json()['id']}/suggest-reply")
    assert r.status_code == 201
    assert "pricing" in r.json()["body"].lower()

    # positive_interest → meeting_proposer wording (concrete slots)
    sim = await client.post(f"/api/campaigns/{cid}/inbox/simulate?kind=positive_interest")
    r = await client.post(f"/api/inbox/{sim.json()['id']}/suggest-reply")
    assert r.status_code == 201
    assert "Thursday" in r.json()["body"] or "scheduling link" in r.json()["body"]

    # Both dispatches appear in the workflow trace.
    tasks = (await client.get(f"/api/campaigns/{cid}/tasks")).json()
    routed = [t["task_name"] for t in tasks if t["agent_name"] == "ReplyRouter"]
    assert "needs_info → info_responder" in routed
    assert "positive_interest → meeting_proposer" in routed
