"""Reply workers — specialized nodes dispatched by the ReplyRouter.

Pattern: Router → Workers (LangGraph-style, dependency-free). The router
(`workflow/reply_graph.py`) analyzes the inbound reply's classification and
dispatches to exactly one worker here. Each worker owns one reply situation:

  positive_interest → meeting_proposer     (lock in a time)
  needs_info        → info_responder       (answer + keep momentum)
  not_interested    → objection_handler    (graceful close, door open)
  out_of_office     → followup_scheduler   (defer politely)
  bounce / other    → generic_follow_up    (neutral nudge / manual triage)

Phase 1: deterministic stubs per worker. Phase 2: per-worker Claude prompts —
the split is exactly why this is a graph: each node gets its own system prompt,
model tier, and eval set.
"""
from __future__ import annotations

from dataclasses import dataclass

from campaign.config import get_settings
from campaign.services import anthropic as svc


@dataclass(frozen=True)
class ReplyContext:
    prospect_first: str
    persona_name: str
    persona_title: str
    persona_company: str
    inbound_subject: str
    inbound_body: str
    prev_subject: str


@dataclass(frozen=True)
class WorkerReply:
    subject: str
    body: str


def _sig(ctx: ReplyContext) -> str:
    return f"\n\nBest,\n{ctx.persona_name}\n{ctx.persona_title} · {ctx.persona_company}"


async def _llm(caller: str, system: str, ctx: ReplyContext, stub_body: str) -> WorkerReply:
    subject = f"Re: {ctx.prev_subject}"
    try:
        await svc.create_message(
            caller=caller,
            model=get_settings().llm_synthesis_model,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": f"Subject: {ctx.inbound_subject}\n\n{ctx.inbound_body}",
                }
            ],
            max_tokens=500,
        )
        return WorkerReply(subject=subject, body=stub_body)
    except svc.DemoModeBlockError:
        return WorkerReply(subject=subject, body=stub_body)


async def meeting_proposer(ctx: ReplyContext) -> WorkerReply:
    """positive_interest → propose concrete times, zero friction."""
    body = (
        f"Hi {ctx.prospect_first},\n\n"
        "Fantastic — let's make it easy. Does Thursday 10:00am or Friday 2:00pm "
        "(your time) work for a 15-minute intro call? I'll send a calendar invite "
        "the moment you confirm.\n\n"
        "If neither slot works, here's my scheduling link so you can grab any time "
        "that suits you."
        f"{_sig(ctx)}"
    )
    return await _llm(
        "reply_worker.meeting_proposer",
        "You convert positive replies into booked meetings. Propose two concrete "
        "time slots and offer a scheduling link. Short, zero friction.",
        ctx,
        body,
    )


async def info_responder(ctx: ReplyContext) -> WorkerReply:
    """needs_info → answer the question, then re-anchor to a call."""
    body = (
        f"Hi {ctx.prospect_first},\n\n"
        "Great questions — short version: pricing scales with usage (most teams "
        "your size land in the mid-tier), deployment is cloud-native with a "
        "typical 2-week rollout, and we're regularly chosen over legacy suites "
        "for exactly that reason.\n\n"
        "Happy to walk through the details with real numbers — would a 15-minute "
        "call this week be useful?"
        f"{_sig(ctx)}"
    )
    return await _llm(
        "reply_worker.info_responder",
        "You answer prospect questions concisely (pricing, deployment, comparisons), "
        "then re-anchor to a short call. Never dodge the question.",
        ctx,
        body,
    )


async def objection_handler(ctx: ReplyContext) -> WorkerReply:
    """not_interested → confirm removal, leave the door open, no pressure."""
    body = (
        f"Hi {ctx.prospect_first},\n\n"
        "Understood — I've taken you off our outreach list, no further emails.\n\n"
        "If tooling ever comes back on the roadmap, I'm easy to find. Wishing you "
        "and the team a great quarter."
        f"{_sig(ctx)}"
    )
    return await _llm(
        "reply_worker.objection_handler",
        "You close out a not-interested reply gracefully: confirm opt-out, zero "
        "pressure, leave a positive last impression in two sentences.",
        ctx,
        body,
    )


async def followup_scheduler(ctx: ReplyContext) -> WorkerReply:
    """out_of_office → acknowledge, defer, set a follow-up marker."""
    body = (
        f"Hi {ctx.prospect_first},\n\n"
        "Thanks for the auto-reply — enjoy the time away. I'll circle back once "
        "you're back at your desk; no action needed until then."
        f"{_sig(ctx)}"
    )
    return await _llm(
        "reply_worker.followup_scheduler",
        "You respond to out-of-office auto-replies: acknowledge, defer politely, "
        "and note when to follow up. Two sentences max.",
        ctx,
        body,
    )


async def generic_follow_up(ctx: ReplyContext) -> WorkerReply:
    """bounce / other → neutral nudge; flagged for manual triage."""
    body = (
        f"Hi {ctx.prospect_first},\n\n"
        "Following up on my earlier note — happy to share more context if useful, "
        "or point you to the right person on our side."
        f"{_sig(ctx)}"
    )
    return await _llm(
        "reply_worker.generic_follow_up",
        "You write a neutral, short follow-up when the reply intent is unclear.",
        ctx,
        body,
    )
