"""Campaign v2 schema.

Domain model is outbound B2B outreach:
  Persona (sender)  ─┐
  Lead              ─┼─►  Campaign  ─┬─►  LeadAnalysis (BANT + priority)
                     │                ├─►  CompanyProfile (cached web lookup)
                     │                └─►  Draft (v1, v2, ... with refinements)
                     │                    └─►  DraftRefinement (critique + diff)
  AgentTask  (per-step tracking for every run)
  LLMCall    (cost tracking ledger)
  EASettings (executive-assistant config per persona)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


class CampaignStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class Priority(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


def _uuid() -> str:
    # Stored as 36-char string — portable across sqlite and postgres without
    # the UUID type quirk.
    return str(uuid.uuid4())


# ----------------------------- Persona -------------------------------------


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(128))
    company: Mapped[str] = mapped_column(String(128))
    tone_guidelines: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaigns: Mapped[list[Campaign]] = relationship(back_populates="persona")
    ea_settings: Mapped[EASettings | None] = relationship(back_populates="persona", uselist=False)


# ----------------------------- Lead ----------------------------------------


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String(256), index=True)
    industry: Mapped[str] = mapped_column(String(128), index=True)
    decision_maker: Mapped[str] = mapped_column(String(128))
    position: Mapped[str] = mapped_column(String(128))
    milestone: Mapped[str] = mapped_column(Text)
    prospect_email: Mapped[str | None] = mapped_column(String(256))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaigns: Mapped[list[Campaign]] = relationship(back_populates="lead")


# ----------------------------- Campaign (one run per lead) -----------------


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"))
    status: Mapped[CampaignStatus] = mapped_column(String(32), default=CampaignStatus.pending, index=True)
    priority: Mapped[Priority | None] = mapped_column(String(16), index=True)
    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    persona: Mapped[Persona] = relationship(back_populates="campaigns")
    lead: Mapped[Lead] = relationship(back_populates="campaigns")
    analysis: Mapped[LeadAnalysis | None] = relationship(back_populates="campaign", uselist=False)
    drafts: Mapped[list[Draft]] = relationship(
        back_populates="campaign", order_by="Draft.version"
    )
    tasks: Mapped[list[AgentTask]] = relationship(
        back_populates="campaign", order_by="AgentTask.started_at"
    )


# ----------------------------- LeadAnalysis (BANT) -------------------------


class LeadAnalysis(Base):
    __tablename__ = "lead_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True)

    # BANT — scores on 1..5 ordinal scale
    budget: Mapped[int] = mapped_column(Integer)
    authority: Mapped[int] = mapped_column(Integer)
    need: Mapped[int] = mapped_column(Integer)
    timeline: Mapped[int] = mapped_column(Integer)

    fit_score: Mapped[float] = mapped_column(Float)         # 0..1
    priority: Mapped[Priority] = mapped_column(String(16))
    confidence: Mapped[str] = mapped_column(String(32))      # low/medium/high
    pain_points: Mapped[list] = mapped_column(JSON, default=list)
    value_opportunities: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="analysis")


# ----------------------------- CompanyProfile (cached lookup) -------------


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    website: Mapped[str | None] = mapped_column(String(512))
    size: Mapped[str | None] = mapped_column(String(64))
    recent_news: Mapped[list] = mapped_column(JSON, default=list)   # list of {title, url, date}
    summary: Mapped[str | None] = mapped_column(Text)
    last_refreshed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ----------------------------- Draft (versioned) ---------------------------


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)

    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    personalization_score: Mapped[int] = mapped_column(Integer)   # 0..100
    sentiment_score: Mapped[float] = mapped_column(Float)          # -1..1
    word_count: Mapped[int] = mapped_column(Integer)
    ea_cc_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    ea_cc_email: Mapped[str | None] = mapped_column(String(256))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="drafts")
    refinements: Mapped[list[DraftRefinement]] = relationship(
        back_populates="draft", order_by="DraftRefinement.created_at"
    )


class DraftRefinement(Base):
    __tablename__ = "draft_refinements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    draft_id: Mapped[str] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"))
    critique: Mapped[str] = mapped_column(Text)
    refined_subject: Mapped[str] = mapped_column(Text)
    refined_body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    draft: Mapped[Draft] = relationship(back_populates="refinements")


# ----------------------------- AgentTask (per-step tracking) --------------


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    agent_name: Mapped[str] = mapped_column(String(64))
    task_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))            # running/succeeded/failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    campaign: Mapped[Campaign] = relationship(back_populates="tasks")


# ----------------------------- LLMCall (cost ledger) ----------------------


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    caller: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(64), index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)


# ----------------------------- EASettings ---------------------------------


class InboundMessage(Base):
    """A reply (or bounce / OOO) received on an outbound campaign.

    Phase 1 ingest: explicit `POST /api/campaigns/{id}/inbox/receive` (test,
    demo, or downstream webhook from Postmark/SES). Phase 3+ would wire a
    background IMAP puller into `workers/inbox_puller.py`.
    """

    __tablename__ = "inbound_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    from_email: Mapped[str] = mapped_column(String(256), index=True)
    from_name: Mapped[str | None] = mapped_column(String(256))
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Classifier output
    classification: Mapped[str] = mapped_column(String(32), index=True)   # positive_interest / needs_info / not_interested / bounce / out_of_office / other
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    needs_action: Mapped[bool] = mapped_column(Boolean, default=False)

    suggested_reply_draft_id: Mapped[str | None] = mapped_column(
        ForeignKey("drafts.id"), default=None
    )


class EASettings(Base):
    __tablename__ = "ea_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    ea_email: Mapped[str | None] = mapped_column(String(256))
    deferral_template: Mapped[str] = mapped_column(
        Text,
        default="I've looped in {ea_name} on this thread — they'll coordinate scheduling with you directly.",
    )

    persona: Mapped[Persona] = relationship(back_populates="ea_settings")
