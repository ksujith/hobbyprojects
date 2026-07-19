@echo off
REM ── Campaign v2 — one-click launcher for Windows ────────────────────────
REM Prereq: Python 3.11+ from https://python.org (check "Add to PATH" while installing)
REM First run creates a virtualenv + installs deps; later runs start instantly.

setlocal
cd /d "%~dp0"

REM -- 1. Python present and new enough? ----------------------------------
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found on PATH.
  echo         Install Python 3.11+ from https://python.org and tick
  echo         "Add python.exe to PATH" during setup, then re-run this file.
  pause
  exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.11 or newer is required. Found:
  python --version
  echo         If this printed a Microsoft Store message instead of a version,
  echo         install Python from https://python.org and re-run.
  pause
  exit /b 1
)

REM -- 2. One-time install (marker file = install completed successfully) --
if not exist ".venv\.installed" (
  echo [1/3] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 ( echo [ERROR] venv creation failed. & pause & exit /b 1 )

  echo [2/3] Installing Campaign v2 ^(one-time, ~2 min^)...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  ".venv\Scripts\python.exe" -m pip install .
  if errorlevel 1 (
    echo.
    echo [ERROR] Install failed — see messages above.
    echo         Usual causes: no internet, or a proxy blocking pip.
    pause
    exit /b 1
  )
  echo ok> ".venv\.installed"
)

if not exist ".env" (
  copy .env.example .env >nul
  echo [i] Created .env — add your ANTHROPIC_API_KEY there, or leave it
  echo     empty to run in demo mode.
)

REM -- 3. Start server; open browser only once the port is actually up ----
echo [3/3] Starting Campaign v2 at http://localhost:8002 ...
echo       ^(leave this window open — closing it stops the app^)
start "" /b cmd /c "for /l %%i in (1,1,30) do (powershell -NoProfile -Command "try{(New-Object Net.Sockets.TcpClient('127.0.0.1',8002)).Close();exit 0}catch{exit 1}" && start http://localhost:8002 && exit || timeout /t 1 >nul)"

".venv\Scripts\python.exe" -m uvicorn campaign.main:app --host 127.0.0.1 --port 8002

echo.
echo [i] Server stopped. If it crashed, the error is shown above.
pause
endlocal
