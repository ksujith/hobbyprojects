"""ReplyRouter — LangGraph StateGraph: router node → specialized worker nodes.

              ┌─► meeting_proposer    (positive_interest)
              ├─► info_responder      (needs_info)
  START→router├─► objection_handler   (not_interested)   → END
              ├─► followup_scheduler  (out_of_office)
              └─► generic_follow_up   (bounce · other)

The router analyzes the inbound reply's classification (produced by
`reply_classifier` at ingest, persisted on the InboundMessage) and sets
`next_agent`; a conditional edge dispatches to exactly one worker. Each
dispatch is recorded as an AgentTask by the caller so the dashboard's
workflow trace shows which node handled the reply.
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from campaign.agents import reply_workers as w
from campaign.agents.reply_workers import ReplyContext, WorkerReply
from campaign.logging import get_logger

log = get_logger(__name__)

ROUTES: dict[str, str] = {
    "positive_interest": "meeting_proposer",
    "needs_info": "info_responder",
    "not_interested": "objection_handler",
    "out_of_office": "followup_scheduler",
    "bounce": "generic_follow_up",
    "other": "generic_follow_up",
}

_WORKERS = {
    "meeting_proposer": w.meeting_proposer,
    "info_responder": w.info_responder,
    "objection_handler": w.objection_handler,
    "followup_scheduler": w.followup_scheduler,
    "generic_follow_up": w.generic_follow_up,
}


class ReplyState(TypedDict, total=False):
    classification: str
    ctx: ReplyContext
    next_agent: str        # worker node chosen by the router
    worker: str            # recorded for the trace
    subject: str
    body: str


def route(classification: str) -> tuple[str, object]:
    """classification → (worker_name, worker fn). Unknown kinds → generic."""
    name = ROUTES.get(classification, "generic_follow_up")
    return name, _WORKERS[name]


# ---- Nodes ----------------------------------------------------------------


def router_node(state: ReplyState) -> dict:
    name, _ = route(state["classification"])
    log.info("reply_graph.route", classification=state["classification"], worker=name)
    return {"next_agent": name, "worker": name}


def _make_worker_node(name: str):
    async def node(state: ReplyState) -> dict:
        reply: WorkerReply = await _WORKERS[name](state["ctx"])
        return {"subject": reply.subject, "body": reply.body}

    node.__name__ = name
    return node


# ---- Graph wiring ---------------------------------------------------------


def build_reply_graph():
    builder = StateGraph(ReplyState)
    builder.add_node("router", router_node)
    for name in _WORKERS:
        builder.add_node(name, _make_worker_node(name))

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router", lambda s: s["next_agent"], {name: name for name in _WORKERS}
    )
    for name in _WORKERS:
        builder.add_edge(name, END)

    return builder.compile(checkpointer=MemorySaver())


reply_graph = build_reply_graph()


async def run_reply_graph(classification: str, ctx: ReplyContext) -> tuple[str, WorkerReply]:
    """Dispatch one inbound reply through the graph. Returns (worker_name, reply)."""
    state: ReplyState = await reply_graph.ainvoke(
        {"classification": classification, "ctx": ctx},
        config={"configurable": {"thread_id": f"reply-{id(ctx)}"}},
    )
    return state["worker"], WorkerReply(subject=state["subject"], body=state["body"])
