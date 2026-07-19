@echo off
REM ── Campaign v2 — one-click launcher for Windows ────────────────────────
REM Prereq: Python 3.11+ from https://python.org (check "Add to PATH" while installing)
REM First run creates a virtualenv + installs deps; later runs start instantly.

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.11+ from https://python.org
  echo         and tick "Add python.exe to PATH" during setup.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  python -m venv .venv
  echo [2/3] Installing Campaign v2 ^(one-time, ~2 min^)...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  ".venv\Scripts\python.exe" -m pip install . --quiet
)

if not exist ".env" (
  copy .env.example .env >nul
  echo [i] Created .env from .env.example — add your ANTHROPIC_API_KEY there,
  echo     or leave it empty to run in demo mode.
)

echo [3/3] Starting Campaign v2 at http://localhost:8002 ...
start "" http://localhost:8002
".venv\Scripts\python.exe" -m uvicorn campaign.main:app --host 127.0.0.1 --port 8002

endlocal
