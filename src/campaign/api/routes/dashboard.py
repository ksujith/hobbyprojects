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
