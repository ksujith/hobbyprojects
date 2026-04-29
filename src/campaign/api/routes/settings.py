"""Settings API — per-persona Executive Assistant config + style profile.

Kept as a distinct surface so the dashboard's Settings panel has a single
endpoint per persona. Style profile is read-only (derived from past drafts).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from campaign.db import models as m
from campaign.db.session import get_session
from campaign.schemas import EASettingsIn, EASettingsOut
from campaign.services import style_indexer

router = APIRouter(prefix="/api/personas/{persona_id}", tags=["settings"])


@router.get("/ea", response_model=EASettingsOut | None)
async def get_ea(persona_id: str, db: AsyncSession = Depends(get_session)):
    row = (
        await db.execute(select(m.EASettings).where(m.EASettings.persona_id == persona_id))
    ).scalars().first()
    if row is None:
        return None
    return row


@router.put("/ea", response_model=EASettingsOut)
async def put_ea(
    persona_id: str,
    body: EASettingsIn,
    db: AsyncSession = Depends(get_session),
) -> m.EASettings:
    persona = await db.get(m.Persona, persona_id)
    if persona is None:
        raise HTTPException(404, "persona not found")

    row = (
        await db.execute(select(m.EASettings).where(m.EASettings.persona_id == persona_id))
    ).scalars().first()
    if row is None:
        row = m.EASettings(persona_id=persona_id)
        db.add(row)
    row.enabled = body.enabled
    row.ea_email = str(body.ea_email) if body.ea_email else None
    if body.deferral_template is not None:
        row.deferral_template = body.deferral_template
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/style")
async def get_style(persona_id: str, db: AsyncSession = Depends(get_session)):
    persona = await db.get(m.Persona, persona_id)
    if persona is None:
        raise HTTPException(404, "persona not found")

    profile = await style_indexer.build(persona_id)
    return {
        "persona_id": profile.persona_id,
        "draft_count": profile.draft_count,
        "avg_word_count": profile.avg_word_count,
        "dominant_signoff": profile.dominant_signoff,
        "top_bigrams": [{"pair": list(p), "count": c} for p, c in profile.top_bigrams],
        "style_hint": profile.to_style_hint(),
    }
