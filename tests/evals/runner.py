"""Eval harness — runs every fixture lead through the pipeline and checks
structural guarantees. Baseline committed; update with --update-baseline.

We assert shape (priority, personalization ≥ N, word count ≤ N, draft
mentions lead's company + decision maker + milestone) not verbatim body
— LLM output will drift in Phase 2 but these invariants must hold.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from campaign.agents.lead_analyzer import run as analyse
from campaign.agents.outreach_drafter import run as draft_run
from campaign.schemas import LeadIn

HERE = Path(__file__).resolve().parent
FIXTURES_PATH = HERE / "fixtures.json"
BASELINE_PATH = HERE / "baseline.json"


async def _score(fixture: dict[str, Any]) -> dict[str, Any]:
    lead = LeadIn(**fixture["lead"])
    analysis = await analyse(lead)
    persona = fixture["persona"]
    draft = await draft_run(
        lead=lead,
        analysis=analysis,
        persona_name=persona["name"],
        persona_title=persona["title"],
        persona_company=persona["company"],
        company_summary=None,
        ea_deferral_line=None,
    )
    return {
        "id": fixture["id"],
        "priority": analysis.priority,
        "fit_score": round(analysis.fit_score, 3),
        "personalization": draft.personalization_score,
        "sentiment": round(draft.sentiment_score, 2),
        "words": draft.word_count,
        "mentions_company": fixture["lead"]["company_name"] in draft.body,
        "mentions_decision_maker": fixture["lead"]["decision_maker"].split()[0] in draft.body,
        "mentions_milestone": fixture["lead"]["milestone"] in draft.body,
    }


def _check(result: dict[str, Any], fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if result["priority"] != fixture["expect_priority"]:
        errors.append(f"[{result['id']}] priority: {result['priority']} != {fixture['expect_priority']}")
    if result["personalization"] < fixture["expect_min_personalization"]:
        errors.append(
            f"[{result['id']}] personalization {result['personalization']} < "
            f"{fixture['expect_min_personalization']}"
        )
    if result["words"] > fixture["expect_max_words"]:
        errors.append(
            f"[{result['id']}] words {result['words']} > {fixture['expect_max_words']}"
        )
    for key in ("mentions_company", "mentions_decision_maker", "mentions_milestone"):
        if not result[key]:
            errors.append(f"[{result['id']}] {key} = false")
    return errors


async def run(update_baseline: bool) -> int:
    fixtures = json.loads(FIXTURES_PATH.read_text())["leads"]
    results = [await _score(f) for f in fixtures]

    failures: list[str] = []
    for f, r in zip(fixtures, results, strict=True):
        failures.extend(_check(r, f))

    current = {"results": results}

    if update_baseline:
        BASELINE_PATH.write_text(json.dumps(current, indent=2) + "\n")
        print(f"baseline written: {BASELINE_PATH}")
        return 0 if not failures else 1

    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text())
        for cur, base in zip(current["results"], baseline["results"], strict=True):
            for k in ("priority", "personalization", "words", "mentions_company",
                      "mentions_decision_maker", "mentions_milestone"):
                if cur[k] != base[k]:
                    failures.append(f"[{cur['id']}] {k}: {base[k]!r} → {cur[k]!r}")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"ok · {len(results)} fixtures")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--update-baseline", action="store_true")
    args = p.parse_args()
    # uuid import kept for future scope expansion; silences lint for now.
    _ = uuid
    sys.exit(asyncio.run(run(args.update_baseline)))
