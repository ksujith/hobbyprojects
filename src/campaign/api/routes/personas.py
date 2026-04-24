from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from campaign.db import models as m
from campaign.db.session import get_session
from campaign.schemas import PersonaIn, PersonaOut

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("", response_model=list[PersonaOut])
async def list_personas(db: AsyncSession = Depends(get_session)) -> list[m.Persona]:
    rows = (await db.execute(select(m.Persona).order_by(m.Persona.created_at))).scalars().all()
    return list(rows)


@router.post("", response_model=PersonaOut, status_code=201)
async def create_persona(body: PersonaIn, db: AsyncSession = Depends(get_session)) -> m.Persona:
    p = m.Persona(**body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.get("/{persona_id}", response_model=PersonaOut)
async def get_persona(persona_id: str, db: AsyncSession = Depends(get_session)) -> m.Persona:
    p = await db.get(m.Persona, persona_id)
    if p is None:
        raise HTTPException(404, "persona not found")
    return p
