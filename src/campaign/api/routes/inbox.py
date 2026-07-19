"""Inbox API — emailbox for inbound replies to outbound campaigns.

Endpoints:
  POST /api/campaigns/{id}/inbox/receive   — production webhook-shaped ingest
  POST /api/campaigns/{id}/inbox/simulate  — demo / test button (kind param)
  GET  /api/campaigns/{id}/inbox           — list inbound for one campaign
  GET  /api/inbox                          — list all inbound (needs-action first)
  POST /api/inbox/{msg_id}/suggest-reply   — synthesize a reply draft from inbound
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from campaign.agents.reply_workers import ReplyContext
from campaign.db import models as m
from campaign.db.session import get_session
from campaign.schemas import DraftOut, InboundMessageIn, InboundMessageOut
from campaign.services import inbox_gateway
from campaign.workflow.reply_graph import run_reply_graph

router = APIRouter(tags=["inbox"])


SimulationKind = Literal[
    "positive_interest", "needs_info", "not_interested", "bounce", "out_of_office"
]


# ---- Ingest (production path, webhook-shaped) ----------------------------


@router.post(
    "/api/campaigns/{campaign_id}/inbox/receive",
    response_model=InboundMessageOut,
    status_code=201,
)
async def receive(
    campaign_id: str,
    body: InboundMessageIn,
    db: AsyncSession = Depends(get_session),
) -> m.InboundMessage:
    try:
        result = await inbox_gateway.ingest(
            campaign_id=campaign_id,
            from_email=str(body.from_email),
            from_name=body.from_name,
            subject=body.subject,
            body=body.body,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    msg = await db.get(m.InboundMessage, result.message_id)
    if msg is None:
        raise HTTPException(500, "ingest succeeded but message not found")
    return msg


# ---- Simulate (demo / tests) ---------------------------------------------


@router.post(
    "/api/campaigns/{campaign_id}/inbox/simulate",
    response_model=InboundMessageOut,
    status_code=201,
)
async def simulate(
    campaign_id: str,
    kind: SimulationKind = "positive_interest",
    db: AsyncSession = Depends(get_session),
) -> m.InboundMessage:
    try:
        result = await inbox_gateway.simulate(campaign_id, kind)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    msg = await db.get(m.InboundMessage, result.message_id)
    if msg is None:
        raise HTTPException(500, "simulate succeeded but message not found")
    return msg


# ---- Reads ----------------------------------------------------------------


@router.get(
    "/api/campaigns/{campaign_id}/inbox",
    response_model=list[InboundMessageOut],
)
async def list_for_campaign(
    campaign_id: str, db: AsyncSession = Depends(get_session)
) -> list[m.InboundMessage]:
    rows = (
        await db.execute(
            select(m.InboundMessage)
            .where(m.InboundMessage.campaign_id == campaign_id)
            .order_by(m.InboundMessage.received_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/api/inbox", response_model=list[InboundMessageOut])
async def list_all(
    limit: int = 100,
    needs_action_only: bool = False,
    db: AsyncSession = Depends(get_session),
) -> list[m.InboundMessage]:
    stmt = (
        select(m.InboundMessage)
        .order_by(
            m.InboundMessage.needs_action.desc(),
            m.InboundMessage.received_at.desc(),
        )
        .limit(limit)
    )
    if needs_action_only:
        stmt = stmt.where(m.InboundMessage.needs_action.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


# ---- Suggest reply -------------------------------------------------------


@router.post(
    "/api/inbox/{message_id}/suggest-reply",
    response_model=DraftOut,
    status_code=201,
)
async def suggest_reply(
    message_id: str, db: AsyncSession = Depends(get_session)
) -> m.Draft:
    """Produce a new draft version that responds to an inbound message.

    Router → worker graph: the inbound's classification (set at ingest by
    `reply_classifier`) routes to a specialized worker — meeting_proposer,
    info_responder, objection_handler, followup_scheduler, or the generic
    fallback. The dispatch is recorded as an AgentTask so the campaign's
    workflow trace shows which node produced the reply.
    """
    msg = await db.get(m.InboundMessage, message_id)
    if msg is None:
        raise HTTPException(404, "inbound message not found")

    latest = (
        await db.execute(
            select(m.Draft)
            .where(m.Draft.campaign_id == msg.campaign_id)
            .order_by(m.Draft.version.desc())
            .limit(1)
        )
    ).scalars().first()
    if latest is None:
        raise HTTPException(400, "no prior draft on this campaign to reply to")

    camp = await db.get(m.Campaign, msg.campaign_id)
    lead = await db.get(m.Lead, camp.lead_id)
    persona = await db.get(m.Persona, camp.persona_id)

    ctx = ReplyContext(
        prospect_first=lead.decision_maker.split()[0],
        persona_name=persona.name,
        persona_title=persona.title,
        persona_company=persona.company,
        inbound_subject=msg.subject,
        inbound_body=msg.body,
        prev_subject=latest.subject,
    )
    worker_name, reply = await run_reply_graph(msg.classification, ctx)

    new = m.Draft(
        campaign_id=msg.campaign_id,
        version=latest.version + 1,
        subject=reply.subject,
        body=reply.body,
        personalization_score=latest.personalization_score,
        sentiment_score=latest.sentiment_score,
        word_count=len(reply.body.split()),
        ea_cc_applied=latest.ea_cc_applied,
        ea_cc_email=latest.ea_cc_email,
    )
    db.add(new)
    db.add(
        m.AgentTask(
            campaign_id=msg.campaign_id,
            agent_name="ReplyRouter",
            task_name=f"{msg.classification} → {worker_name}",
            status="succeeded",
            details={"worker": worker_name, "classification": msg.classification},
        )
    )
    await db.flush()

    msg.suggested_reply_draft_id = new.id
    await db.commit()
    await db.refresh(new)
    return new
