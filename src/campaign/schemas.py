"""Pydantic DTOs — wire types independent of ORM models."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ---- Persona ----

class PersonaIn(_Base):
    name: Annotated[str, Field(min_length=1, max_length=128)]
    title: str
    company: str
    tone_guidelines: str = ""


class PersonaOut(PersonaIn):
    id: str
    created_at: datetime


# ---- Lead ----

class LeadIn(_Base):
    company_name: Annotated[str, Field(min_length=1, max_length=256)]
    industry: str
    decision_maker: str
    position: str
    milestone: Annotated[str, Field(min_length=5)]
    prospect_email: EmailStr | None = None


class LeadOut(LeadIn):
    id: str


# ---- LeadAnalysis (BANT) ----

class BANTScore(_Base):
    budget: Annotated[int, Field(ge=1, le=5)]
    authority: Annotated[int, Field(ge=1, le=5)]
    need: Annotated[int, Field(ge=1, le=5)]
    timeline: Annotated[int, Field(ge=1, le=5)]


class LeadAnalysisIn(_Base):
    bant: BANTScore
    fit_score: Annotated[float, Field(ge=0, le=1)]
    priority: Literal["high", "medium", "low"]
    confidence: Literal["low", "medium", "high"]
    pain_points: list[str] = Field(default_factory=list)
    value_opportunities: list[str] = Field(default_factory=list)


class LeadAnalysisOut(LeadAnalysisIn):
    id: str
    campaign_id: str


# ---- CompanyProfile ----

class NewsItem(_Base):
    title: str
    url: str
    date: str | None = None


class CompanyProfileOut(_Base):
    id: str
    company_name: str
    website: str | None = None
    size: str | None = None
    summary: str | None = None
    recent_news: list[NewsItem] = Field(default_factory=list)
    last_refreshed: datetime


# ---- Draft ----

class DraftOut(_Base):
    id: str
    campaign_id: str
    version: int
    subject: str
    body: str
    personalization_score: int
    sentiment_score: float
    word_count: int
    ea_cc_applied: bool
    ea_cc_email: str | None = None
    created_at: datetime


class RefineDraftIn(_Base):
    critique: Annotated[str, Field(min_length=3, max_length=500)]


# ---- Inbound message (emailbox) ----


ReplyClass = Literal[
    "positive_interest", "needs_info", "not_interested", "bounce", "out_of_office", "other"
]


class InboundMessageIn(_Base):
    from_email: EmailStr
    from_name: str | None = None
    subject: Annotated[str, Field(min_length=1, max_length=512)]
    body: Annotated[str, Field(min_length=1)]


class InboundMessageOut(_Base):
    id: str
    campaign_id: str
    from_email: str
    from_name: str | None
    subject: str
    body: str
    received_at: datetime
    classification: ReplyClass
    confidence: float
    needs_action: bool
    suggested_reply_draft_id: str | None


# ---- EA settings ----


class EASettingsIn(_Base):
    enabled: bool
    ea_email: EmailStr | None = None
    deferral_template: str | None = None


class EASettingsOut(_Base):
    id: str
    persona_id: str
    enabled: bool
    ea_email: str | None
    deferral_template: str


# ---- AgentTask (workflow trace) ----


class AgentTaskOut(_Base):
    id: str
    agent_name: str
    task_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    details: dict


# ---- Campaign ----


class StartCampaign(_Base):
    persona_id: str
    lead: LeadIn


class CampaignOut(_Base):
    id: str
    persona_id: str
    lead_id: str
    company_name: str | None = None   # populated on list reads for the runs table
    status: Literal["pending", "running", "succeeded", "failed"]
    priority: Literal["high", "medium", "low"] | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
