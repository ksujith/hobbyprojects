"""CalendaringDetector — does this outreach thread involve scheduling?

Phase 1: keyword + pattern match. Simple and deterministic.
Phase 2: Claude classification for ambiguous cases.
"""
from __future__ import annotations

import re

_SCHEDULING_PATTERNS = (
    re.compile(r"\b(meeting|call|sync|chat|demo|catch[- ]up)\b", re.I),
    re.compile(r"\b(schedule|calendar|book|set up|find a time)\b", re.I),
    re.compile(r"\b(15[- ]minute|30[- ]minute|half[- ]hour|quick chat)\b", re.I),
    re.compile(r"\b(availability|free next|later this week|monday|tuesday|wednesday|thursday|friday)\b", re.I),
)


def is_scheduling(text: str) -> bool:
    """Return True if `text` looks like it's proposing scheduling."""
    hits = sum(1 for p in _SCHEDULING_PATTERNS if p.search(text))
    return hits >= 2  # need ≥2 independent signals to avoid false positives
