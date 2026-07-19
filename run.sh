#!/usr/bin/env bash
# ── Campaign v2 — one-click launcher for macOS / Linux ──────────────────
# Prereq: Python 3.11+. First run creates a venv + installs; later runs start instantly.
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/3] Creating virtual environment..."
  "$PY" -m venv .venv
  echo "[2/3] Installing Campaign v2 (one-time)..."
  .venv/bin/python -m pip install --upgrade pip --quiet
  .venv/bin/python -m pip install . --quiet
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[i] Created .env — add your ANTHROPIC_API_KEY there, or leave empty for demo mode."
fi

echo "[3/3] Starting Campaign v2 at http://localhost:8002 ..."
(command -v open >/dev/null && open http://localhost:8002) || \
  (command -v xdg-open >/dev/null && xdg-open http://localhost:8002) || true
exec .venv/bin/python -m uvicorn campaign.main:app --host 127.0.0.1 --port 8002
