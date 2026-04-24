# Campaign v2 — B2B Outreach Agent

Production-grade rewrite of the legacy `outreach_app.py` monolith, applying
mail-app-style patterns to outbound sales intelligence.

**Non-destructive:** the legacy app (`outreach_app.py`, `rl_campaign_agent.py`,
`outreach_campaigns.db`) is untouched. v2 lives under `src/campaign/` and uses
its own DB at `campaign_v2.db`, running on port **8002**.

## What's new vs v1

| v1 (outreach_app.py) | v2 (`src/campaign/`) |
|---|---|
| Single-file 1055-LOC monolith | Proper package — `config`, `logging`, `db`, `schemas`, `services`, `agents`, `tools`, `workflow`, `api` |
| `sqlite3.connect()` in async handlers | Async SQLAlchemy 2.0 + Alembic-ready |
| `MockAIAgent` hardcoded responses | `AnthropicService` with retry, prompt-cache, cost ledger · demo-mode stubs as fallback |
| No cost tracking | `llm_calls` table, per-caller attribution, model-aware pricing |
| No sender-context lookup | `CompanyLookup` agent with 7-day cached `company_profiles` |
| One-shot hardcoded email | `OutreachDrafter` + versioned `Draft` table + `DraftRefiner` (apply critique → v2, v3…) |
| No EA concept | `EASettings` per-persona + `CalendaringDetector` → auto-CC + deferral text in drafts |
| No logging discipline | `structlog` with redaction of `decision_maker`, `milestone`, `email_body`, `subject`, etc. |
| No tests | pytest: API lifecycle, per-agent, cost math |
| Inline HTML in Python | Single dashboard module with vanilla JS (auto-polls, BANT badges, refine box) |

## Domain model

```
  Persona (sender)  ─┐
  Lead              ─┼─►  Campaign  ─┬─►  LeadAnalysis  (BANT + fit + priority)
                     │                ├─►  CompanyProfile (cached web lookup)
                     │                └─►  Draft v1, v2, …  ─►  DraftRefinement (critique)
  AgentTask  (per-step trace)
  LLMCall    (cost ledger — cross-cutting)
  EASettings (per persona — CC + deferral template)
```

## Quick start (demo mode, no API key)

```bash
pip install -e ".[dev]"
uvicorn campaign.main:app --port 8002
```

Open http://127.0.0.1:8002, click **+ new persona**, then run a campaign.

## Flip on real Claude (Phase 2)

```bash
export ANTHROPIC_API_KEY=sk-...
export CAMPAIGN_DEMO_MODE=false
uvicorn campaign.main:app --port 8002
```

Every agent's call path is already wired through `AnthropicService`; remove
the `_stub` fallthrough in each `agents/*.py` after wiring the real
tool-use structured output.

## Commands

```bash
pytest -q                       # run tests
ruff check src tests            # lint
uvicorn campaign.main:app --port 8002          # run dev
docker compose up               # Postgres + Redis + api
```
