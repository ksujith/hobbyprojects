"""Inbox end-to-end: ingest, classify, list, simulate, suggest-reply."""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient


async def _setup_campaign(client: AsyncClient) -> str:
    await client.post(
        "/api/personas",
        json={"name": "Alex", "title": "Head of Partnerships", "company": "AICRM"},
    )
    personas = (await client.get("/api/personas")).json()
    r = await client.post(
        "/api/campaigns",
        json={
            "persona_id": personas[0]["id"],
            "lead": {
                "company_name": "Greystar",
                "industry": "Real Estate",
                "decision_maker": "Jordan Price",
                "position": "VP of RevOps",
                "milestone": "Series B funding announcement",
            },
        },
    )
    camp = r.json()
    for _ in range(40):
        s = (await client.get(f"/api/campaigns/{camp['id']}")).json()["status"]
        if s in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.05)
    return camp["id"]


@pytest.mark.asyncio
async def test_receive_classifies_bounce(client: AsyncClient) -> None:
    cid = await _setup_campaign(client)
    r = await client.post(
        f"/api/campaigns/{cid}/inbox/receive",
        json={
            "from_email": "mailer-daemon@greystar.example",
            "subject": "Mail Delivery Failure",
            "body": "Delivery Status Notification — recipient address rejected: user unknown.",
        },
    )
    assert r.status_code == 201
    m = r.json()
    assert m["classification"] == "bounce"
    assert m["needs_action"] is False


@pytest.mark.asyncio
async def test_simulate_positive_needs_action(client: AsyncClient) -> None:
    cid = await _setup_campaign(client)
    r = await client.post(f"/api/campaigns/{cid}/inbox/simulate?kind=positive_interest")
    assert r.status_code == 201
    m = r.json()
    assert m["classification"] == "positive_interest"
    assert m["needs_action"] is True


@pytest.mark.asyncio
async def test_suggest_reply_creates_next_draft(client: AsyncClient) -> None:
    cid = await _setup_campaign(client)
    # Baseline: v1 draft already exists from the pipeline.
    drafts_before = (await client.get(f"/api/campaigns/{cid}/drafts")).json()
    assert len(drafts_before) == 1

    sim = await client.post(f"/api/campaigns/{cid}/inbox/simulate?kind=needs_info")
    msg_id = sim.json()["id"]

    r = await client.post(f"/api/inbox/{msg_id}/suggest-reply")
    assert r.status_code == 201
    v2 = r.json()
    assert v2["version"] == 2
    assert v2["subject"].startswith("Re:")

    drafts_after = (await client.get(f"/api/campaigns/{cid}/drafts")).json()
    assert len(drafts_after) == 2


@pytest.mark.asyncio
async def test_inbox_needs_action_filter(client: AsyncClient) -> None:
    cid = await _setup_campaign(client)
    await client.post(f"/api/campaigns/{cid}/inbox/simulate?kind=bounce")
    await client.post(f"/api/campaigns/{cid}/inbox/simulate?kind=positive_interest")

    all_msgs = (await client.get("/api/inbox")).json()
    assert len(all_msgs) == 2

    needs = (await client.get("/api/inbox?needs_action_only=true")).json()
    assert len(needs) == 1
    assert needs[0]["classification"] == "positive_interest"


@pytest.mark.asyncio
async def test_receive_on_missing_campaign_404(client: AsyncClient) -> None:
    r = await client.post(
        "/api/campaigns/nope/inbox/receive",
        json={
            "from_email": "x@y.com",
            "subject": "hi",
            "body": "hi",
        },
    )
    assert r.status_code == 404
