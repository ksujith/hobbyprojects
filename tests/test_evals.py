"""Pytest wrapper — fails on baseline drift."""
from __future__ import annotations

import pytest

from tests.evals.runner import run as eval_run


@pytest.mark.asyncio
async def test_evals_match_baseline() -> None:
    rc = await eval_run(update_baseline=False)
    assert rc == 0, "eval harness reported regressions — see stderr"
