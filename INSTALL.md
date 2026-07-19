# Installing & Running Campaign v2 on Another Machine

Three ways to run the app elsewhere, easiest first. All serve the dashboard at
**http://localhost:8002** and store data in a local SQLite file (`campaign_v2.db`)
— no database server needed. Tables are created automatically on first start.

Without an `ANTHROPIC_API_KEY`, the app runs in **demo mode** (deterministic
stub agents — everything works, no API cost). Add a key to `.env` for real
Claude-powered drafting.

---

## Option 1 — Windows (or Mac/Linux), one-click

1. Install **Python 3.11+** from <https://python.org>
   → on Windows, tick **"Add python.exe to PATH"** during setup.
2. Copy the `Campaign` folder to the machine (zip it, or `git clone` if pushed
   to GitHub). You can leave out: `venv/`, `.venv/`, `__pycache__/`,
   `.pytest_cache/`, `.ruff_cache/`, `campaign_v2.db` (your local data),
   `outreach_campaigns.db`, and the legacy v1 scripts.
3. Double-click **`run.bat`** (Windows) or run **`./run.sh`** (Mac/Linux).

First run creates a virtualenv and installs dependencies (~2 min), then the
browser opens automatically. Later runs start in seconds. Stop with `Ctrl+C`.

## Option 2 — Docker (any OS with Docker Desktop)

No Python needed on the target machine.

```powershell
# in the Campaign folder
docker build -t campaign-v2 .

# run with SQLite persisted to a named volume (demo mode)
docker run -d --name campaign -p 8002:8002 `
  -e CAMPAIGN_DEMO_MODE=true `
  -e DATABASE_URL=sqlite+aiosqlite:////data/campaign_v2.db `
  -v campaign-data:/data `
  campaign-v2
```

(Backticks are PowerShell line-continuations; use `\` on Mac/Linux.)
Add `-e ANTHROPIC_API_KEY=sk-ant-...` for real LLM calls. The full
`docker-compose.yml` is for the production shape (Postgres + Redis) — not
needed for a single-machine install.

## Option 3 — pip install from Git (for developers)

```bash
python -m venv .venv && . .venv/bin/activate    # .venv\Scripts\activate on Windows
pip install "git+https://github.com/<you>/<repo>.git"   # or: pip install .
uvicorn campaign.main:app --port 8002
```

The web dashboard ships inside the package (`campaign/web/*`), so a wheel
install is fully self-contained.

---

## Configuration (`.env`)

| Variable | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Empty → demo mode with stub agents |
| `CAMPAIGN_DEMO_MODE` | `false` | Force demo mode even with a key |
| `DATABASE_URL` | `sqlite+aiosqlite:///campaign_v2.db` | Point at Postgres for multi-user |
| `LLM_SYNTHESIS_MODEL` | `claude-opus-4-8` | Drafting / reply workers |
| `LLM_EXTRACTION_MODEL` | `claude-sonnet-5` | Analysis / review / classify |
| `DRAFT_REVIEW_MAX_ITERATIONS` | `2` | Quality-loop bound |
| `DRAFT_REVIEW_PASS_SCORE` | `85` | Reviewer pass threshold |

## Troubleshooting

- **`python` not found (Windows)** — reinstall Python with "Add to PATH", or
  use `py -m venv .venv` in `run.bat`'s place.
- **Port 8002 busy** — edit the port in `run.bat` / `run.sh`.
- **Corporate proxy blocks pip** — use Option 2 (Docker) built on a machine
  with access, then `docker save` / `docker load` to transfer the image.
