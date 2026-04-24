"""Central Anthropic client with retry + cost tracking + prompt caching.

Every agent call goes through `create_message`. When the API key is absent or
`CAMPAIGN_DEMO_MODE=true`, `DemoModeBlockError` is raised so callers fall
through to a deterministic stub that matches the legacy MockAIAgent output.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from campaign.config import get_settings
from campaign.logging import get_logger

log = get_logger(__name__)


PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7":   {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_write": 18.75},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-haiku-4-5":  {"input": 0.80,  "output": 4.00,  "cache_read": 0.08, "cache_write": 1.00},
}


class DemoModeBlockError(RuntimeError):
    """Raised when the service is disabled — callers fall back to stubs."""


@runtime_checkable
class _MessagesClient(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def cost_usd(self, model: str) -> float:
        p = PRICING.get(model)
        if p is None:
            return 0.0
        return (
            self.input_tokens * p["input"] / 1_000_000
            + self.output_tokens * p["output"] / 1_000_000
            + self.cache_read_tokens * p["cache_read"] / 1_000_000
            + self.cache_write_tokens * p["cache_write"] / 1_000_000
        )


_injected_client: Any = None


def _set_client_for_testing(client: Any) -> None:
    global _injected_client
    _injected_client = client


def _get_client() -> Any:
    if _injected_client is not None:
        return _injected_client
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise DemoModeBlockError("no ANTHROPIC_API_KEY set")
    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("anthropic package not installed") from e
    return AsyncAnthropic(api_key=settings.anthropic_api_key).messages


async def create_message(
    *,
    caller: str,
    model: str,
    messages: list[dict[str, Any]],
    system: str | list[dict[str, Any]] | None = None,
    max_tokens: int = 1024,
    tools: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> tuple[Any, LLMUsage, float]:
    settings = get_settings()
    if (
        settings.env == "test"
        or settings.campaign_demo_mode
        or not settings.anthropic_api_key
    ):
        raise DemoModeBlockError("llm disabled in this environment")

    client = _get_client()

    sys_blocks: list[dict[str, Any]] | None = None
    if system is not None and settings.llm_prompt_cache:
        if isinstance(system, str):
            sys_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        else:
            sys_blocks = system

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if sys_blocks is not None:
        kwargs["system"] = sys_blocks
    elif system is not None:
        kwargs["system"] = system
    if tools is not None:
        kwargs["tools"] = tools
    if extra:
        kwargs.update(extra)

    started = time.monotonic()
    resp = await _call_with_retry(client, kwargs)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    usage = _extract_usage(resp)
    cost = usage.cost_usd(model)

    log.info(
        "llm.call",
        caller=caller,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read=usage.cache_read_tokens,
        cache_write=usage.cache_write_tokens,
        cost_usd=round(cost, 6),
        elapsed_ms=elapsed_ms,
    )

    try:
        await _record_call(caller=caller, model=model, usage=usage, cost=cost, elapsed_ms=elapsed_ms)
    except Exception:
        log.warning("llm.record_failed", caller=caller, model=model, exc_info=True)

    return resp, usage, cost


def _retryable(exc: BaseException) -> bool:
    try:
        from anthropic import APIConnectionError, APIStatusError, RateLimitError  # type: ignore
    except ImportError:  # pragma: no cover
        return False
    if isinstance(exc, (RateLimitError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        return 500 <= getattr(exc, "status_code", 0) < 600
    return False


async def _call_with_retry(client: _MessagesClient, kwargs: dict[str, Any]) -> Any:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(4),
        wait=wait_exponential_jitter(initial=0.5, max=8.0),
        retry=retry_if_exception(_retryable),
        reraise=True,
    ):
        with attempt:
            return await client.create(**kwargs)
    raise AssertionError("unreachable")


def _extract_usage(resp: Any) -> LLMUsage:
    u = getattr(resp, "usage", None)
    if u is None:
        return LLMUsage(input_tokens=0, output_tokens=0)
    return LLMUsage(
        input_tokens=getattr(u, "input_tokens", 0) or 0,
        output_tokens=getattr(u, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
    )


async def _record_call(
    *, caller: str, model: str, usage: LLMUsage, cost: float, elapsed_ms: int
) -> None:
    from campaign.db import models as m
    from campaign.db.session import session_scope

    async with session_scope() as db:
        db.add(
            m.LLMCall(
                caller=caller,
                model=model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_tokens=usage.cache_read_tokens,
                cache_write_tokens=usage.cache_write_tokens,
                cost_usd=round(cost, 6),
                elapsed_ms=elapsed_ms,
            )
        )
