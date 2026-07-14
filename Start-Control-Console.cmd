@echo off
setlocal

set "ALPHAPILOT_REPO=%~dp0"
set "ALPHAPILOT_URL=http://127.0.0.1:8766/"

echo [AlphaPilot] Starting local Control Console...
echo [AlphaPilot] Repository: %ALPHAPILOT_REPO%

powershell -NoProfile -ExecutionPolicy Bypass -File "%ALPHAPILOT_REPO%scripts\start_local_console.ps1" -RepositoryPath "%ALPHAPILOT_REPO%." -ConsoleUrl "%ALPHAPILOT_URL%" %*

if errorlevel 1 (
  echo.
  echo [AlphaPilot] Startup failed. Keep this window open and send the error to Codex.
  pause
  exit /b 1
)

echo [AlphaPilot] Opened %ALPHAPILOT_URL%
exit /b 0
