"""CompanyLookup — Claude web_search for company context, 7-day cache.

Phase 1: returns a deterministic stub summary so the pipeline runs end-to-end.
Phase 3: real Claude call with `web_search_20250305` tool, cached in
`company_profiles` with `last_refreshed`-based TTL.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from campaign.config import get_settings
from campaign.db import models as m
from campaign.db.session import session_scope
from campaign.services import anthropic as svc


async def get_or_fetch(company_name: str) -> m.CompanyProfile:
    settings = get_settings()
    ttl = timedelta(days=settings.company_profile_ttl_days)

    async with session_scope() as db:
        existing = (
            await db.execute(select(m.CompanyProfile).where(m.CompanyProfile.company_name == company_name))
        ).scalars().first()
        if existing is not None:
            # last_refreshed may be naive when loaded from sqlite — normalise.
            last = existing.last_refreshed
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            if datetime.now(UTC) - last < ttl:
                return existing

    summary, news = await _lookup(company_name)

    async with session_scope() as db:
        row = (
            await db.execute(select(m.CompanyProfile).where(m.CompanyProfile.company_name == company_name))
        ).scalars().first()
        if row is None:
            row = m.CompanyProfile(company_name=company_name)
            db.add(row)
        row.summary = summary
        row.recent_news = news
        row.last_refreshed = datetime.now(UTC)
        await db.flush()
        return row


async def _lookup(company_name: str) -> tuple[str, list[dict]]:
    try:
        await svc.create_message(
            caller="company_lookup",
            model=get_settings().llm_extraction_model,
            messages=[{"role": "user", "content": f"Find public background on {company_name}."}],
            max_tokens=400,
            # Phase 3: add tools=[{"type": "web_search_20250305", "name": "web_search"}]
        )
        return _stub(company_name)
    except svc.DemoModeBlockError:
        return _stub(company_name)


def _stub(company_name: str) -> tuple[str, list[dict]]:
    summary = (
        f"{company_name} — stub company profile. Public overview pending real "
        f"web-search backing (Phase 3)."
    )
    news: list[dict] = [
        {
            "title": f"Sample milestone for {company_name}",
            "url": "https://example.com/news/stub",
            "date": None,
        },
    ]
    return summary, news
