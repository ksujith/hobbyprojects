"""PrefetchService — background enrichment on new leads.

Mirrors the mail-app `prefetch-service.ts` pattern, adapted to outbound:
  1. Auto-analyze any lead that doesn't yet have a campaign (future: opt-in)
  2. Look up the company profile for medium+ priority (7-day cached)
  3. If persona has `auto_draft_high=true` (future config), auto-draft v1

Phase 1 exposes a single `process_campaign_prefetch(campaign_id)` that can
be called via `BackgroundTasks` when a campaign is created. Phase 4 swaps
for an ARQ queue.

Kept tiny and callable so the pipeline, the API, and the (future) worker
all share one code path.
"""
from __future__ import annotations

from campaign.logging import get_logger
from campaign.tools import company_lookup

log = get_logger(__name__)


async def warm_company_cache(company_name: str) -> None:
    """Populate `company_profiles` for `company_name` if not already cached.

    Fire-and-forget — swallows exceptions so a background enrichment failure
    never breaks the calling pipeline.
    """
    try:
        await company_lookup.get_or_fetch(company_name)
        log.info("prefetch.company_warmed", company=company_name)
    except Exception:  # noqa: BLE001
        log.warning("prefetch.company_failed", company=company_name, exc_info=True)
