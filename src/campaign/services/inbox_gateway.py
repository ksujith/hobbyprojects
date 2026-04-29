"""Inbox ingest gateway.

Two paths into `InboundMessage`:
  1. Webhook-style `POST` from a provider (Postmark, SendGrid) — real production
     path. We accept a normalized payload here; the provider-specific adapter
     lives at the route layer.
  2. `simulate()` — demo helper that fabricates a canned reply for a campaign.
     Used from the dashboard "Simulate reply" button and from tests.

Both paths produce the same downstream side-effect: one `InboundMessage` row
plus a classification pass via `reply_classifier`.

Why a gateway (not a route): we want classification + persistence to be
reusable from the simulate button, the webhook, and the (future) IMAP puller
without duplicating the logic.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from campaign.agents.reply_classifier import classify_with_llm_fallback
from campaign.db import models as m
from campaign.db.session import session_scope
from campaign.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class IngestResult:
    message_id: str
    classification: str
    confidence: float
    needs_action: bool


async def ingest(
    *,
    campaign_id: str,
    from_email: str,
    subject: str,
    body: str,
    from_name: str | None = None,
) -> IngestResult:
    """Persist one inbound message + classify it. Returns the new message id
    and its classification."""
    result = await classify_with_llm_fallback(subject, body)
    needs_action = result.kind in {"positive_interest", "needs_info"}

    async with session_scope() as db:
        # Ensure the campaign exists — refuse orphan inbound.
        camp = await db.get(m.Campaign, campaign_id)
        if camp is None:
            raise ValueError(f"campaign {campaign_id} not found")

        msg = m.InboundMessage(
            campaign_id=campaign_id,
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body=body,
            classification=result.kind,
            confidence=result.confidence,
            needs_action=needs_action,
        )
        db.add(msg)
        await db.flush()

        log.info(
            "inbox.ingest",
            campaign_id=campaign_id,
            message_id=msg.id,
            classification=result.kind,
            confidence=result.confidence,
            needs_action=needs_action,
        )
        return IngestResult(
            message_id=msg.id,
            classification=result.kind,
            confidence=result.confidence,
            needs_action=needs_action,
        )


_SIMULATION_TEMPLATES: dict[str, tuple[str, str]] = {
    "positive_interest": (
        "Re: Congrats on Series B funding announcement",
        "Thanks for reaching out! We're definitely interested in learning more. "
        "Could we book a 15-minute call next Thursday or Friday to discuss?",
    ),
    "needs_info": (
        "Re: Congrats on Series B funding announcement",
        "Interesting — can you share more details on pricing and how this compares "
        "to Informatica or Talend? Also curious about deployment complexity.",
    ),
    "not_interested": (
        "Re: Congrats on Series B funding announcement",
        "Thanks but we're all set with our current tooling. Please remove me from the list.",
    ),
    "out_of_office": (
        "Automatic reply: I am out of the office",
        "I am out of the office until next Monday with limited email access. "
        "For urgent matters contact our team at contact@example.com.",
    ),
    "bounce": (
        "Mail Delivery Failure",
        "Delivery Status Notification — recipient address rejected: user unknown. "
        "SMTP 550 5.1.1 user not found.",
    ),
}


async def simulate(campaign_id: str, kind: str) -> IngestResult:
    """Inject a canned inbound of the requested classification kind."""
    if kind not in _SIMULATION_TEMPLATES:
        raise ValueError(f"unknown simulation kind: {kind}")

    subject, body = _SIMULATION_TEMPLATES[kind]

    async with session_scope() as db:
        # Derive a plausible `from` address from the campaign's lead.
        camp = await db.get(m.Campaign, campaign_id)
        if camp is None:
            raise ValueError(f"campaign {campaign_id} not found")
        lead = await db.get(m.Lead, camp.lead_id)
        if lead is None:
            raise ValueError(f"lead {camp.lead_id} not found")
        from_email = (
            lead.prospect_email
            or f"{lead.decision_maker.lower().replace(' ', '.')}@example.com"
        )
        from_name = lead.decision_maker

    return await ingest(
        campaign_id=campaign_id,
        from_email=from_email,
        from_name=from_name,
        subject=subject,
        body=body,
    )


async def needs_action_count(persona_id: str | None = None) -> int:
    """Count inbound messages that need human action (positive / needs-info)."""
    async with session_scope() as db:
        stmt = select(m.InboundMessage).where(m.InboundMessage.needs_action.is_(True))
        if persona_id is not None:
            stmt = stmt.join(m.Campaign, m.Campaign.id == m.InboundMessage.campaign_id).where(
                m.Campaign.persona_id == persona_id
            )
        rows = (await db.execute(stmt)).scalars().all()
        return len(rows)
