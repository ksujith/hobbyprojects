"""SMTP sender.

Phase 1: **simulated-only**. `send()` records the outbound intent in the
`SendLog` shape (reusing `AgentTask` for now) and returns immediately without
touching the network. This is production-safe for dogfooding: a bug can't
accidentally spam a real prospect.

Phase 2: plug in `aiosmtplib` when the persona has real SMTP creds configured.
The real sender goes behind a `DRY_RUN` flag that defaults to True.

Separation of concerns: the API route hands us a `draft_id`, we load the
draft + its campaign + the persona's SMTP config, and we either simulate or
(later) hit SMTP. No route-layer logic sneaks into here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import selectinload

from campaign.db import models as m
from campaign.db.session import session_scope
from campaign.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class SendResult:
    draft_id: str
    simulated: bool
    delivered_at: datetime
    to_address: str | None
    message_preview: str


async def send(draft_id: str, *, force_real: bool = False) -> SendResult:
    """Send a draft. Always simulated in Phase 1 (regardless of `force_real`).

    We log the attempt as an `AgentTask` so the dashboard can show a send
    history without a new table until we're ready to commit to one.
    """
    async with session_scope() as db:
        draft = await db.get(
            m.Draft, draft_id, options=[selectinload(m.Draft.campaign)]
        )
        if draft is None:
            raise ValueError(f"draft {draft_id} not found")

        campaign = draft.campaign
        lead = await db.get(m.Lead, campaign.lead_id)
        to_address = lead.prospect_email if lead else None

        now = datetime.now(UTC)
        task = m.AgentTask(
            campaign_id=campaign.id,
            agent_name="SMTPSender",
            task_name=f"send draft v{draft.version}",
            status="succeeded",
            completed_at=now,
            details={
                "draft_id": draft_id,
                "to": to_address,
                "simulated": True,                # Phase 1 — always
                "force_real_requested": force_real,
                "word_count": draft.word_count,
            },
        )
        db.add(task)

        log.info(
            "smtp.send.simulated",
            draft_id=draft_id,
            campaign_id=campaign.id,
            to=to_address,
            words=draft.word_count,
        )

        return SendResult(
            draft_id=draft_id,
            simulated=True,
            delivered_at=now,
            to_address=to_address,
            message_preview=draft.body[:120],
        )
