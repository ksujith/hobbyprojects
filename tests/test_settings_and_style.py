"""Settings API (EA per persona) + style indexer."""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from campaign.services import style_indexer


async def _make_persona(client: AsyncClient) -> str:
    r = await client.post(
        "/api/personas",
        json={"name": "Alex", "title": "Head of Partnerships", "company": "AICRM"},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_ea_round_trip(client: AsyncClient) -> None:
    pid = await _make_persona(client)

    # No settings yet.
    assert (await client.get(f"/api/personas/{pid}/ea")).json() is None

    # PUT settings.
    r = await client.put(
        f"/api/personas/{pid}/ea",
        json={"enabled": True, "ea_email": "ea@aicrm.example"},
    )
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    assert r.json()["ea_email"] == "ea@aicrm.example"

    # GET persists.
    got = (await client.get(f"/api/personas/{pid}/ea")).json()
    assert got["enabled"] is True


@pytest.mark.asyncio
async def test_ea_put_404_on_missing_persona(client: AsyncClient) -> None:
    r = await client.put(
        "/api/personas/does-not-exist/ea",
        json={"enabled": True, "ea_email": "x@y.com"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_style_indexer_empty_when_no_drafts(client: AsyncClient) -> None:
    pid = await _make_persona(client)
    profile = await style_indexer.build(pid)
    assert profile.draft_count == 0
    assert profile.to_style_hint() == ""


@pytest.mark.asyncio
async def test_style_indexer_extracts_signoff_after_campaign(client: AsyncClient) -> None:
    pid = await _make_persona(client)
    r = await client.post(
        "/api/campaigns",
        json={
            "persona_id": pid,
            "lead": {
                "company_name": "Acme",
                "industry": "SaaS",
                "decision_maker": "Sam Taylor",
                "position": "VP Data",
                "milestone": "Series B funding announcement",
            },
        },
    )
    cid = r.json()["id"]
    for _ in range(40):
        s = (await client.get(f"/api/campaigns/{cid}")).json()["status"]
        if s == "succeeded":
            break
        await asyncio.sleep(0.05)

    profile = await style_indexer.build(pid)
    assert profile.draft_count >= 1
    assert profile.avg_word_count > 10
    # Our stub draft ends with "Best," — indexer should pick that up.
    assert profile.dominant_signoff == "Best"
    hint = profile.to_style_hint()
    assert "Best" in hint
