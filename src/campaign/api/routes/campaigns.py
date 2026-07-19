from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from campaign.db import models as m
from campaign.db.session import get_session
from campaign.schemas import (
    AgentTaskOut,
    CampaignOut,
    DraftOut,
    LeadAnalysisOut,
    RefineDraftIn,
    StartCampaign,
)
from campaign.workflow.pipeline import refine_latest_draft, run_campaign

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignOut, status_code=status.HTTP_202_ACCEPTED)
async def start_campaign(
    body: StartCampaign,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
) -> m.Campaign:
    persona = await db.get(m.Persona, body.persona_id)
    if persona is None:
        raise HTTPException(404, "persona not found")

    lead = m.Lead(**body.lead.model_dump())
    db.add(lead)
    await db.flush()

    camp = m.Campaign(persona_id=persona.id, lead_id=lead.id, status=m.CampaignStatus.pending)
    db.add(camp)
    await db.commit()
    await db.refresh(camp)

    background.add_task(run_campaign, camp.id)
    return camp


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
) -> list[m.Campaign]:
    rows = (
        await db.execute(
            select(m.Campaign)
            .options(selectinload(m.Campaign.lead))
            .order_by(m.Campaign.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    # Denormalize the lead's company onto each row for the runs table.
    for c in rows:
        c.company_name = c.lead.company_name if c.lead else None
    return list(rows)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_session)) -> m.Campaign:
    c = await db.get(m.Campaign, campaign_id)
    if c is None:
        raise HTTPException(404, "campaign not found")
    return c


@router.get("/{campaign_id}/analysis", response_model=LeadAnalysisOut | None)
async def get_analysis(campaign_id: str, db: AsyncSession = Depends(get_session)):
    row = (
        await db.execute(select(m.LeadAnalysis).where(m.LeadAnalysis.campaign_id == campaign_id))
    ).scalars().first()
    if row is None:
        return None
    # Reshape nested BANT on the way out.
    return {
        "id": row.id,
        "campaign_id": row.campaign_id,
        "bant": {
            "budget": row.budget,
            "authority": row.authority,
            "need": row.need,
            "timeline": row.timeline,
        },
        "fit_score": row.fit_score,
        "priority": row.priority,
        "confidence": row.confidence,
        "pain_points": row.pain_points,
        "value_opportunities": row.value_opportunities,
    }


@router.get("/{campaign_id}/tasks", response_model=list[AgentTaskOut])
async def list_tasks(
    campaign_id: str, db: AsyncSession = Depends(get_session)
) -> list[m.AgentTask]:
    """Workflow trace: every agent node that ran for this campaign, in order."""
    rows = (
        await db.execute(
            select(m.AgentTask)
            .where(m.AgentTask.campaign_id == campaign_id)
            .order_by(m.AgentTask.started_at)
        )
    ).scalars().all()
    return list(rows)


@router.get("/{campaign_id}/drafts", response_model=list[DraftOut])
async def list_drafts(campaign_id: str, db: AsyncSession = Depends(get_session)) -> list[m.Draft]:
    rows = (
        await db.execute(
            select(m.Draft).where(m.Draft.campaign_id == campaign_id).order_by(m.Draft.version)
        )
    ).scalars().all()
    return list(rows)


@router.post("/{campaign_id}/drafts/refine", response_model=DraftOut, status_code=201)
async def refine_draft(
    campaign_id: str, body: RefineDraftIn, db: AsyncSession = Depends(get_session)
) -> m.Draft:
    try:
        new_id = await refine_latest_draft(campaign_id, body.critique)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    # Fetch and return the new draft.
    result = await db.execute(
        select(m.Draft).options(selectinload(m.Draft.refinements)).where(m.Draft.id == new_id)
    )
    new = result.scalars().first()
    if new is None:
        raise HTTPException(500, "refine succeeded but draft not found")
    return new
