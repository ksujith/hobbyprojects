"""End-to-end API smoke: persona → campaign → run → drafts → refine."""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

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


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_full_campaign_lifecycle(client: AsyncClient) -> None:
    # 1. Create persona.
    r = await client.post("/api/personas", json=PERSONA_PAYLOAD)
    assert r.status_code == 201
    persona = r.json()

    # 2. Start campaign.
    r = await client.post(
        "/api/campaigns",
        json={"persona_id": persona["id"], "lead": LEAD_PAYLOAD},
    )
    assert r.status_code == 202
    camp = r.json()
    assert camp["status"] == "pending"

    # 3. Wait for BackgroundTasks to finish (bounded).
    for _ in range(40):
        r = await client.get(f"/api/campaigns/{camp['id']}")
        if r.json()["status"] in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.05)
    final = r.json()
    assert final["status"] == "succeeded", final
    assert final["priority"] in ("high", "medium", "low")

    # 4. Analysis present.
    r = await client.get(f"/api/campaigns/{camp['id']}/analysis")
    assert r.status_code == 200
    a = r.json()
    assert a["bant"]["authority"] >= 1
    assert a["pain_points"]
    assert a["priority"] in ("high", "medium", "low")

    # 5. Draft v1 present, mentions lead + milestone (personalization check).
    r = await client.get(f"/api/campaigns/{camp['id']}/drafts")
    drafts = r.json()
    assert len(drafts) == 1
    d1 = drafts[0]
    assert d1["version"] == 1
    assert "Greystar" in d1["body"]
    assert "Jordan" in d1["body"]
    assert "Series B funding announcement" in d1["body"]
    assert d1["personalization_score"] >= 70
    assert d1["word_count"] > 20

    # 6. Refine — should produce v2.
    r = await client.post(
        f"/api/campaigns/{camp['id']}/drafts/refine",
        json={"critique": "make it shorter and more casual"},
    )
    assert r.status_code == 201
    d2 = r.json()
    assert d2["version"] == 2
    # "Best," → "Cheers," and length should be ≤ d1 after the shorten pass.
    assert "Cheers," in d2["body"] or "Best," not in d2["body"]
    assert len(d2["body"]) <= len(d1["body"])


@pytest.mark.asyncio
async def test_analytics_funnel(client: AsyncClient) -> None:
    # Empty state.
    r = await client.get("/api/analytics")
    assert r.status_code == 200
    assert r.json()["total_campaigns"] == 0

    # Run one campaign to completion.
    persona = (await client.post("/api/personas", json=PERSONA_PAYLOAD)).json()
    camp = (
        await client.post(
            "/api/campaigns", json={"persona_id": persona["id"], "lead": LEAD_PAYLOAD}
        )
    ).json()
    for _ in range(40):
        status = (await client.get(f"/api/campaigns/{camp['id']}")).json()["status"]
        if status in ("succeeded", "failed"):
            break
        await asyncio.sleep(0.05)

    a = (await client.get("/api/analytics")).json()
    assert a["total_campaigns"] == 1
    assert a["status_breakdown"].get("succeeded") == 1
    assert a["draft_count"] >= 1
    # Demo-mode drafts carry a personalization score, so the average is populated.
    assert a["avg_personalization"] is not None
