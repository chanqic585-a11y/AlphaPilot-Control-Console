@echo off
setlocal

set "ALPHAPILOT_REPO=%~dp0"
set "ALPHAPILOT_URL=http://127.0.0.1:8766/"
set "ALPHAPILOT_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%ALPHAPILOT_PY%" (
  echo [AlphaPilot] Bundled Python was not found:
  echo %ALPHAPILOT_PY%
  echo.
  echo Please open this project from Codex once, then run this script again.
  pause
  exit /b 1
)

echo [AlphaPilot] Starting local Control Console...
echo [AlphaPilot] Repository: %ALPHAPILOT_REPO%

powershell -NoProfile -ExecutionPolicy Bypass -File "%ALPHAPILOT_REPO%scripts\start_local_console.ps1" -RepositoryPath "%ALPHAPILOT_REPO%." -PythonPath "%ALPHAPILOT_PY%" -ConsoleUrl "%ALPHAPILOT_URL%" %*

if errorlevel 1 (
  echo.
  echo [AlphaPilot] Startup failed. Keep this window open and send the error to Codex.
  pause
  exit /b 1
)

echo [AlphaPilot] Opened %ALPHAPILOT_URL%
exit /b 0
