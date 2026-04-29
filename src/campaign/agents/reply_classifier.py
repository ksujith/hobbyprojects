"""Reply classifier — inbound messages on a campaign thread.

Classifies into one of:
  positive_interest · needs_info · not_interested · bounce · out_of_office · other

Phase 1: deterministic heuristic — fast, zero-dep, explainable. Trip-wire
regex families matched in priority order. The bias is toward *not* auto-
classifying as positive: false positives burn SDRs.

Phase 2 will wire `AnthropicService` with `sonnet-4-6` and structured output
for ambiguous cases (low heuristic confidence).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from campaign.services import anthropic as svc

ReplyClass = Literal[
    "positive_interest", "needs_info", "not_interested", "bounce", "out_of_office", "other"
]


@dataclass(frozen=True)
class Classification:
    kind: ReplyClass
    confidence: float        # 0..1
    reasoning: str


# ---- Heuristic patterns (ordered by specificity) --------------------------

_BOUNCE = (
    re.compile(r"\b(mail\s*delivery\s*(failed|failure)|undeliverable|delivery\s*status\s*notification)\b", re.I),
    re.compile(r"\b(address\s*(rejected|not\s*found)|user\s*unknown|recipient\s*address\s*rejected)\b", re.I),
    re.compile(r"\b55\d\s+5\.\d\.\d\b"),               # SMTP 5xx codes
    re.compile(r"\bmailer[- ]daemon\b", re.I),
)

_OOO = (
    re.compile(r"\bout\s+of\s+(the\s+)?office\b", re.I),
    re.compile(r"\b(on\s+vacation|on\s+leave|away\s+from\s+(my\s+)?desk)\b", re.I),
    re.compile(r"\b(auto[- ]?(reply|response|generated))\b", re.I),
    re.compile(r"\bi\s+(will|am)\s+(be\s+)?(away|out)\s+until\b", re.I),
)

_NOT_INTERESTED = (
    re.compile(r"\b(not\s+interested|no\s+thanks|remove\s+me|unsubscribe|stop\s+emailing)\b", re.I),
    re.compile(r"\b(don't|do\s+not)\s+(contact|email|reach\s+out)\b", re.I),
    re.compile(r"\bwe('re| are)?\s+(happy|set|all\s+set)\s+with\b", re.I),
)

_POSITIVE = (
    re.compile(r"\binterested\s+in\b", re.I),
    re.compile(r"\b(keen|excited)\s+to\s+(chat|connect|learn|hear|talk)\b", re.I),
    re.compile(r"\bwould\s+(love|like)\s+to\s+(chat|connect|learn|hear|talk|see)\b", re.I),
    re.compile(r"\bhappy\s+to\s+(chat|connect|jump|hop|talk)\b", re.I),
    re.compile(r"\b(sounds\s+(good|great|interesting|awesome))\b", re.I),
    re.compile(r"\blet('s| us)\s+(chat|connect|talk|jump|sync|schedule|book|hop)\b", re.I),
    re.compile(r"\b(book|schedule)\s+(a|some)\s+(?:\S+\s+)?(call|time|meeting|chat|sync|demo)\b", re.I),
    re.compile(r"\b(monday|tuesday|wednesday|thursday|friday)\s+(or|works|at|next|morning|afternoon)\b", re.I),
    re.compile(r"\b(works\s+for\s+(me|us)|available\s+(next|this|at|on))\b", re.I),
    re.compile(r"\b\d+[-\s]?minute\s+(call|chat|meeting|sync)\b", re.I),
)

_NEEDS_INFO = (
    re.compile(r"\?\s*$|\?.{0,80}$", re.M),                       # question mark near end of line
    re.compile(r"\b(can\s+you\s+share|more\s+(info|details|information)|pricing|how\s+does)\b", re.I),
    re.compile(r"\b(who|what|when|where|why|how)\s+(do|does|is|are|would|will)\b", re.I),
)


def _score(patterns: tuple[re.Pattern[str], ...], text: str) -> int:
    return sum(1 for p in patterns if p.search(text))


def classify(subject: str, body: str) -> Classification:
    """Return a deterministic heuristic classification.

    Ordering matters: bounces and OOO are catch-high because they're wrong
    to treat as real replies. Positive/Needs-info patterns run last.
    """
    combined = f"{subject}\n\n{body}"

    if _score(_BOUNCE, combined) >= 1:
        return Classification("bounce", 0.95, "SMTP bounce / undeliverable markers matched.")
    if _score(_OOO, combined) >= 1:
        return Classification("out_of_office", 0.9, "Auto-reply / away markers matched.")
    if _score(_NOT_INTERESTED, combined) >= 1:
        return Classification("not_interested", 0.85, "Opt-out / unsubscribe phrasing matched.")

    pos = _score(_POSITIVE, combined)
    if pos >= 2:
        return Classification("positive_interest", 0.85, f"{pos} positive-intent signals.")
    if pos == 1:
        return Classification("positive_interest", 0.65, "Single positive-intent signal.")

    if _score(_NEEDS_INFO, combined) >= 1:
        return Classification("needs_info", 0.7, "Question / clarification requested.")

    return Classification("other", 0.35, "No dominant signal — routed to triage.")


async def classify_with_llm_fallback(subject: str, body: str) -> Classification:
    """Run heuristic; for low-confidence `other`, optionally call Claude.

    Phase 1 short-circuits when the service is demo/blocked — keeps tests
    fully deterministic offline.
    """
    heuristic = classify(subject, body)
    if heuristic.kind != "other" or heuristic.confidence >= 0.6:
        return heuristic
    try:
        await svc.create_message(
            caller="reply_classifier",
            model="claude-sonnet-4-6",
            system="Classify this B2B outreach reply into one of: "
                   "positive_interest, needs_info, not_interested, bounce, out_of_office, other.",
            messages=[{"role": "user", "content": f"Subject: {subject}\n\n{body}"}],
            max_tokens=60,
        )
        # TODO(phase-2): parse structured output.
        return heuristic
    except svc.DemoModeBlockError:
        return heuristic
