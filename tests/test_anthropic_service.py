from __future__ import annotations

import pytest

from campaign.services import anthropic as svc


class _FakeUsage:
    def __init__(self, in_=100, out=50, cr=0, cw=0):
        self.input_tokens = in_
        self.output_tokens = out
        self.cache_read_input_tokens = cr
        self.cache_creation_input_tokens = cw


class _FakeResponse:
    def __init__(self, **u):
        self.usage = _FakeUsage(**u)
        self.content = [{"type": "text", "text": "ok"}]


class _FakeClient:
    def __init__(self, responses):
        self._r = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        r = self._r.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.mark.asyncio
async def test_demo_mode_blocks_without_key() -> None:
    with pytest.raises(svc.DemoModeBlockError):
        await svc.create_message(
            caller="t",
            model="claude-opus-4-7",
            messages=[{"role": "user", "content": "x"}],
        )


def test_pricing_models_present() -> None:
    for m in ("claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"):
        assert m in svc.PRICING
        for k in ("input", "output", "cache_read", "cache_write"):
            assert svc.PRICING[m][k] > 0


def test_cost_calc() -> None:
    u = svc.LLMUsage(input_tokens=1000, output_tokens=500)
    # sonnet: 1000/1M * 3 + 500/1M * 15 = 0.003 + 0.0075 = 0.0105
    assert abs(u.cost_usd("claude-sonnet-4-6") - 0.0105) < 1e-6


def test_cost_unknown_model_zero() -> None:
    u = svc.LLMUsage(input_tokens=1000, output_tokens=1000)
    assert u.cost_usd("claude-mystery") == 0.0
