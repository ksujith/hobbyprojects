"""Dashboard — serves the static SPA from `campaign/web/` and exposes the
tiny cost-ledger API used by the Cost tab.

Separate files (not an inline HTML blob) so UI churn doesn't need a Python
restart, `web/*` edits are isolated, and the assets can later be swapped
for a proper frontend toolchain without route changes.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc, func, select

from campaign.db import models as m
from campaign.db.session import session_scope

router = APIRouter(tags=["dashboard"])

_WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def mount_static(app) -> None:
    """Called from `main.py` to mount `/static` on the FastAPI app.

    Kept out of this router because `APIRouter.mount` isn't a thing — only
    `FastAPI.mount` is. We separate the concern so `main.py` owns the app
    lifecycle and this module owns the URL scheme.
    """
    app.mount("/static", StaticFiles(directory=str(_WEB_DIR)), name="static")


@router.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


@router.get("/api/analytics", include_in_schema=False)
async def analytics() -> JSONResponse:
    """Funnel rollup for the Analytics tab: campaign volume by status/priority,
    reply mix, average draft quality, and total spend. Read-only aggregates —
    same shape/discipline as the cost ledger below."""

    def _counts(rows: list[tuple[str, int]]) -> dict[str, int]:
        return {str(k): int(n) for k, n in rows if k is not None}

    async with session_scope() as db:
        total_campaigns = int(
            (await db.execute(select(func.count(m.Campaign.id)))).scalar() or 0
        )
        status_rows = (
            await db.execute(
                select(m.Campaign.status, func.count(m.Campaign.id)).group_by(m.Campaign.status)
            )
        ).all()
        priority_rows = (
            await db.execute(
                select(m.Campaign.priority, func.count(m.Campaign.id)).group_by(m.Campaign.priority)
            )
        ).all()
        reply_rows = (
            await db.execute(
                select(m.InboundMessage.classification, func.count(m.InboundMessage.id)).group_by(
                    m.InboundMessage.classification
                )
            )
        ).all()
        avg_personalization, avg_sentiment, draft_count = (
            await db.execute(
                select(
                    func.avg(m.Draft.personalization_score),
                    func.avg(m.Draft.sentiment_score),
                    func.count(m.Draft.id),
                )
            )
        ).one()
        total_cost = (
            await db.execute(select(func.sum(m.LLMCall.cost_usd)))
        ).scalar()

    return JSONResponse(
        {
            "total_campaigns": total_campaigns,
            "status_breakdown": _counts(status_rows),
            "priority_breakdown": _counts(priority_rows),
            "reply_breakdown": _counts(reply_rows),
            "draft_count": int(draft_count or 0),
            "avg_personalization": round(float(avg_personalization), 1) if avg_personalization is not None else None,
            "avg_sentiment": round(float(avg_sentiment), 2) if avg_sentiment is not None else None,
            "total_cost_usd": round(float(total_cost or 0), 6),
        }
    )


@router.get("/api/cost", include_in_schema=False)
async def cost() -> JSONResponse:
    async with session_scope() as db:
        rows = (
            await db.execute(
                select(
                    m.LLMCall.caller,
                    func.count(m.LLMCall.id),
                    func.sum(m.LLMCall.cost_usd),
                )
                .group_by(m.LLMCall.caller)
                .order_by(desc(func.sum(m.LLMCall.cost_usd)))
            )
        ).all()
    return JSONResponse(
        [{"caller": c, "calls": int(n), "cost_usd": round(float(s or 0), 6)} for c, n, s in rows]
    )
