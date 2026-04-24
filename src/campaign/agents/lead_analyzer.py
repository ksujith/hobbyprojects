"""Step 1 — Lead Analysis (BANT + priority + fit).

Phase 1: deterministic stub that reproduces the shape of the legacy
`MockAIAgent.simulate_sales_rep_analysis` output, structured via Pydantic.
Phase 2: replace `_stub` with a Claude `sonnet-4-6` call that returns the
same `LeadAnalysisIn` schema via tool-use structured output.
"""
from __future__ import annotations

from campaign.schemas import BANTScore, LeadAnalysisIn, LeadIn
from campaign.services import anthropic as svc


async def run(lead: LeadIn) -> LeadAnalysisIn:
    try:
        await svc.create_message(
            caller="lead_analyzer",
            model="claude-sonnet-4-6",
            system=_SYSTEM,
            messages=[{"role": "user", "content": _user_prompt(lead)}],
            max_tokens=600,
        )
        # TODO(phase-2): parse tool_use block -> LeadAnalysisIn
        return _stub(lead)
    except svc.DemoModeBlockError:
        return _stub(lead)


_SYSTEM = (
    "You are a B2B sales analyst. Given a lead (company, industry, decision maker, "
    "milestone), return a BANT score, fit, priority, and specific pain points + "
    "value opportunities. Be concrete — no generic phrases."
)


def _user_prompt(lead: LeadIn) -> str:
    return (
        f"Company: {lead.company_name}\n"
        f"Industry: {lead.industry}\n"
        f"Decision maker: {lead.decision_maker} ({lead.position})\n"
        f"Recent milestone: {lead.milestone}\n"
    )


def _stub(lead: LeadIn) -> LeadAnalysisIn:
    """Deterministic BANT — mirrors legacy MockAIAgent output shape."""
    # Simple signal-based priority: big milestone keywords → high, else medium.
    ml = lead.milestone.lower()
    high_sigs = ("funding", "ipo", "acquisition", "series", "launch", "expansion")
    is_high = any(k in ml for k in high_sigs)
    priority = "high" if is_high else "medium"
    return LeadAnalysisIn(
        bant=BANTScore(budget=4, authority=5, need=4 if is_high else 3, timeline=4 if is_high else 2),
        fit_score=0.82 if is_high else 0.68,
        priority=priority,
        confidence="medium",
        pain_points=[
            "Digital transformation needs",
            "Scalability challenges across tooling",
            "Market differentiation vs incumbents",
        ],
        value_opportunities=[
            "Process automation",
            "Enhanced analytics",
            "Customer experience",
        ],
    )
