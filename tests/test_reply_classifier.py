"""Unit tests for the heuristic classifier — the whole reason the inbox
has any trustworthy routing at all."""
from __future__ import annotations

from campaign.agents.reply_classifier import classify


def test_bounce_via_mailer_daemon() -> None:
    r = classify("Mail Delivery Failure", "mailer-daemon: user unknown")
    assert r.kind == "bounce"


def test_bounce_via_smtp_code() -> None:
    r = classify("Undeliverable", "550 5.1.1 recipient address rejected")
    assert r.kind == "bounce"


def test_out_of_office() -> None:
    r = classify(
        "Automatic reply",
        "I am out of the office until next Monday with limited email access.",
    )
    assert r.kind == "out_of_office"


def test_not_interested() -> None:
    r = classify("Re: outreach", "Not interested. Please remove me from your list.")
    assert r.kind == "not_interested"


def test_positive_two_signals() -> None:
    r = classify(
        "Re: outreach",
        "Sounds great, let's chat. Would a 15-minute call later this week work?",
    )
    assert r.kind == "positive_interest"
    assert r.confidence >= 0.8


def test_needs_info_question() -> None:
    r = classify("Re: outreach", "Can you share pricing details?")
    assert r.kind == "needs_info"


def test_other_when_nothing_matches() -> None:
    r = classify("hmm", "whatever")
    assert r.kind == "other"
