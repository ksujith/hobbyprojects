"""Send endpoint — Phase 1 always simulated, never touches the network."""
from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_is_simulated(client: AsyncClient) -> None:
    await client.post(
        "/api/personas",
        json={"name": "Alex", "title": "Head", "company": "AICRM"},
    )
    pid = (await client.get("/api/personas")).json()[0]["id"]
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
                "prospect_email": "sam@acme.example",
            },
        },
    )
    cid = r.json()["id"]
    for _ in range(40):
        if (await client.get(f"/api/campaigns/{cid}")).json()["status"] == "succeeded":
            break
        await asyncio.sleep(0.05)

    drafts = (await client.get(f"/api/campaigns/{cid}/drafts")).json()
    assert len(drafts) == 1

    send = await client.post(f"/api/drafts/{drafts[0]['id']}/send")
    assert send.status_code == 200
    payload = send.json()
    assert payload["simulated"] is True
    assert payload["to"] == "sam@acme.example"
    assert payload["preview"].startswith("Hi Sam,")
