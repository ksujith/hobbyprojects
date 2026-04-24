"""End-to-end campaign pipeline.

Given a `Campaign` id:
  1. Mark RUNNING.
  2. Lead analysis (BANT + priority).
  3. Company lookup (cached).
  4. Calendaring detection → optional EA CC + deferral.
  5. Generate v1 Draft.
  6. Persist everything, mark SUCCEEDED.

Invoked via FastAPI `BackgroundTasks` in Phase 1; same signature will be
called from an ARQ worker in Phase 4.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from campaign.agents import (
    calendaring_detector,
    draft_refiner,
    lead_analyzer,
    outreach_drafter,
)
from campaign.db import models as m
from campaign.db.session import session_scope
from campaign.logging import get_logger
from campaign.schemas import LeadIn
from campaign.tools import company_lookup

log = get_logger(__name__)


async def run_campaign(campaign_id: str) -> None:
    log.info("pipeline.start", campaign_id=campaign_id)

    async with session_scope() as db:
        camp = await db.get(
            m.Campaign,
            campaign_id,
            options=[
                selectinload(m.Campaign.lead),
                selectinload(m.Campaign.persona).selectinload(m.Persona.ea_settings),
            ],
        )
        if camp is None:
            log.error("pipeline.campaign_not_found", campaign_id=campaign_id)
            return
        camp.status = m.CampaignStatus.running
        camp.started_at = datetime.now(UTC)
        lead_in = LeadIn(
            company_name=camp.lead.company_name,
            industry=camp.lead.industry,
            decision_maker=camp.lead.decision_maker,
            position=camp.lead.position,
            milestone=camp.lead.milestone,
            prospect_email=camp.lead.prospect_email,
        )
        persona_name = camp.persona.name
        persona_title = camp.persona.title
        persona_company = camp.persona.company
        ea = camp.persona.ea_settings

    try:
        # --- Step 2: Lead analysis -------------------------------------
        analysis = await lead_analyzer.run(lead_in)

        async with session_scope() as db:
            db.add(
                m.AgentTask(
                    campaign_id=campaign_id,
                    agent_name="LeadAnalyzer",
                    task_name="BANT + priority",
                    status="succeeded",
                    completed_at=datetime.now(UTC),
                    details={"priority": analysis.priority, "fit_score": analysis.fit_score},
                )
            )
            db.add(
                m.LeadAnalysis(
                    campaign_id=campaign_id,
                    budget=analysis.bant.budget,
                    authority=analysis.bant.authority,
                    need=analysis.bant.need,
                    timeline=analysis.bant.timeline,
                    fit_score=analysis.fit_score,
                    priority=analysis.priority,
                    confidence=analysis.confidence,
                    pain_points=analysis.pain_points,
                    value_opportunities=analysis.value_opportunities,
                )
            )

        # --- Step 3: Company lookup ------------------------------------
        profile = await company_lookup.get_or_fetch(lead_in.company_name)

        # --- Step 4: EA scheduling detection (pre-draft heuristic) -----
        ea_line: str | None = None
        ea_email: str | None = None
        ea_applied = False
        if ea is not None and ea.enabled:
            hint = f"{lead_in.milestone} {analysis.pain_points[0] if analysis.pain_points else ''}"
            if calendaring_detector.is_scheduling(hint):
                ea_email = ea.ea_email
                ea_line = ea.deferral_template.format(ea_name=ea.ea_email or "my assistant")
                ea_applied = True

        # --- Step 5: Draft v1 ------------------------------------------
        draft_content = await outreach_drafter.run(
            lead=lead_in,
            analysis=analysis,
            persona_name=persona_name,
            persona_title=persona_title,
            persona_company=persona_company,
            company_summary=profile.summary,
            ea_deferral_line=ea_line,
        )

        async with session_scope() as db:
            db.add(
                m.Draft(
                    campaign_id=campaign_id,
                    version=1,
                    subject=draft_content.subject,
                    body=draft_content.body,
                    personalization_score=draft_content.personalization_score,
                    sentiment_score=draft_content.sentiment_score,
                    word_count=draft_content.word_count,
                    ea_cc_applied=ea_applied,
                    ea_cc_email=ea_email,
                )
            )
            # Mark succeeded.
            camp = await db.get(m.Campaign, campaign_id)
            camp.status = m.CampaignStatus.succeeded
            camp.priority = analysis.priority
            camp.completed_at = datetime.now(UTC)

        log.info(
            "pipeline.done",
            campaign_id=campaign_id,
            priority=analysis.priority,
            ea_applied=ea_applied,
        )

    except Exception as e:
        log.exception("pipeline.failed", campaign_id=campaign_id)
        async with session_scope() as db:
            camp = await db.get(m.Campaign, campaign_id)
            if camp is not None:
                camp.status = m.CampaignStatus.failed
                camp.error = repr(e)
                camp.completed_at = datetime.now(UTC)


async def refine_latest_draft(campaign_id: str, critique: str) -> str:
    """Create a new Draft version by refining the latest one. Returns new draft id."""
    async with session_scope() as db:
        latest = (
            await db.execute(
                select(m.Draft)
                .where(m.Draft.campaign_id == campaign_id)
                .order_by(m.Draft.version.desc())
                .limit(1)
            )
        ).scalars().first()
        if latest is None:
            raise ValueError(f"no drafts for campaign {campaign_id}")
        current_subject = latest.subject
        current_body = latest.body
        next_version = latest.version + 1
        latest_id = latest.id
        ea_applied = latest.ea_cc_applied
        ea_email = latest.ea_cc_email
        prev_personalization = latest.personalization_score
        prev_sentiment = latest.sentiment_score

    refined = await draft_refiner.run(
        subject=current_subject, body=current_body, critique=critique
    )

    async with session_scope() as db:
        db.add(
            m.DraftRefinement(
                draft_id=latest_id,
                critique=critique,
                refined_subject=refined.subject,
                refined_body=refined.body,
            )
        )
        new_draft = m.Draft(
            campaign_id=campaign_id,
            version=next_version,
            subject=refined.subject,
            body=refined.body,
            personalization_score=prev_personalization,
            sentiment_score=prev_sentiment,
            word_count=len(refined.body.split()),
            ea_cc_applied=ea_applied,
            ea_cc_email=ea_email,
        )
        db.add(new_draft)
        await db.flush()
        return new_draft.id
