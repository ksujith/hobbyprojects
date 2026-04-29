"""Send API — dispatch a draft via SMTP (Phase 1: simulated only)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from campaign.services import smtp_sender

router = APIRouter(prefix="/api", tags=["send"])


@router.post("/drafts/{draft_id}/send")
async def send_draft(draft_id: str) -> dict:
    try:
        result = await smtp_sender.send(draft_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return {
        "draft_id": result.draft_id,
        "simulated": result.simulated,
        "to": result.to_address,
        "delivered_at": result.delivered_at.isoformat(),
        "preview": result.message_preview,
    }
