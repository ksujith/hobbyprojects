"""Draft quality loop as a LangGraph StateGraph.

The Coder → Reviewer → Fix loop (Code → Test → Fix → Repeat):

    START → drafter → reviewer ──approved──► END
                 ▲                │
                 └── refiner ◄──needs_fix (bounded by draft_review_max_iterations)

State routes on `next_agent` (conditional edges), mirrors the classic
planner/coder/reviewer/merger shape. Compiled with a MemorySaver checkpointer
keyed by campaign_id so a run can be resumed/inspected mid-loop.

Nodes are pure (no DB): drafts and trace events accumulate in state; the
pipeline persists them afterward. That keeps the graph unit-testable offline.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from campaign.agents import draft_refiner, draft_reviewer, outreach_drafter
from campaign.config import get_settings
from campaign.schemas import LeadAnalysisIn, LeadIn


class DraftState(TypedDict, total=False):
    # Inputs
    lead: LeadIn
    analysis: LeadAnalysisIn
    persona_name: str
    persona_title: str
    persona_company: str
    company_summary: str | None
    ea_deferral_line: str | None

    # Working draft
    subject: str
    body: str
    personalization: int
    sentiment: float
    word_count: int
    critique: str

    # Routing slots
    review_status: str            # "pending" | "approved" | "needs_fix"
    iterations: int               # refine passes so far
    next_agent: str               # "reviewer" | "refiner" | "done"

    # Accumulators (append-only across nodes)
    drafts: Annotated[list[dict], operator.add]
    trace: Annotated[list[dict], operator.add]


def _personalization_score(lead: LeadIn, body: str) -> int:
    """70 base, +10 per personalization token present — same heuristic as the drafter."""
    score = 70
    for tok in (lead.company_name, lead.decision_maker.split()[0], lead.milestone):
        if tok in body:
            score += 10
    return min(score, 100)


# ---- Nodes ----------------------------------------------------------------


async def drafter_node(state: DraftState) -> dict:
    """The "Coder": write draft v1."""
    content = await outreach_drafter.run(
        lead=state["lead"],
        analysis=state["analysis"],
        persona_name=state["persona_name"],
        persona_title=state["persona_title"],
        persona_company=state["persona_company"],
        company_summary=state.get("company_summary"),
        ea_deferral_line=state.get("ea_deferral_line"),
    )
    return {
        "subject": content.subject,
        "body": content.body,
        "personalization": content.personalization_score,
        "sentiment": content.sentiment_score,
        "word_count": content.word_count,
        "iterations": 0,
        "review_status": "pending",
        "next_agent": "reviewer",
        "drafts": [
            {
                "version": 1,
                "subject": content.subject,
                "body": content.body,
                "personalization_score": content.personalization_score,
                "sentiment_score": content.sentiment_score,
                "word_count": content.word_count,
            }
        ],
        "trace": [
            {
                "agent_name": "OutreachDrafter",
                "task_name": "draft v1",
                "details": {"word_count": content.word_count},
            }
        ],
    }


async def reviewer_node(state: DraftState) -> dict:
    """The "Tester"/Oracle: score the draft; route back to the fixer on failure."""
    review = await draft_reviewer.run(
        body=state["body"],
        word_count=state["word_count"],
        personalization_score=state["personalization"],
        sentiment_score=state["sentiment"],
    )
    version = state["iterations"] + 1
    status = "approved" if review.passed else "needs_fix"
    budget_left = state["iterations"] < get_settings().draft_review_max_iterations
    next_agent = "refiner" if (status == "needs_fix" and budget_left) else "done"
    return {
        "review_status": status,
        "critique": review.critique,
        "next_agent": next_agent,
        "trace": [
            {
                "agent_name": "DraftReviewer",
                "task_name": f"review v{version}",
                "details": {
                    "score": review.score,
                    "passed": review.passed,
                    "critique": review.critique,
                },
            }
        ],
    }


async def refiner_node(state: DraftState) -> dict:
    """The "Fixer": apply the reviewer's critique, bump the version."""
    refined = await draft_refiner.run(
        subject=state["subject"], body=state["body"], critique=state["critique"]
    )
    iterations = state["iterations"] + 1
    version = iterations + 1
    word_count = len(refined.body.split())
    personalization = _personalization_score(state["lead"], refined.body)
    return {
        "subject": refined.subject,
        "body": refined.body,
        "word_count": word_count,
        "personalization": personalization,
        "iterations": iterations,
        "next_agent": "reviewer",
        "drafts": [
            {
                "version": version,
                "subject": refined.subject,
                "body": refined.body,
                "personalization_score": personalization,
                "sentiment_score": state["sentiment"],
                "word_count": word_count,
            }
        ],
        "trace": [
            {
                "agent_name": "DraftRefiner",
                "task_name": f"auto-refine → v{version}",
                "details": {"critique": state["critique"]},
            }
        ],
    }


# ---- Graph wiring ---------------------------------------------------------


def _route(state: DraftState) -> str:
    return state["next_agent"]


def build_draft_graph():
    builder = StateGraph(DraftState)
    builder.add_node("drafter", drafter_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("refiner", refiner_node)

    builder.add_edge(START, "drafter")
    builder.add_edge("drafter", "reviewer")
    builder.add_conditional_edges("reviewer", _route, {"refiner": "refiner", "done": END})
    builder.add_edge("refiner", "reviewer")

    # Checkpointing → resumable/inspectable runs, keyed by thread_id.
    return builder.compile(checkpointer=MemorySaver())


draft_graph = build_draft_graph()


async def run_draft_graph(campaign_id: str, initial: DraftState) -> DraftState:
    """Invoke the loop; thread_id = campaign_id so checkpoints map to campaigns."""
    return await draft_graph.ainvoke(
        initial, config={"configurable": {"thread_id": campaign_id}}
    )
