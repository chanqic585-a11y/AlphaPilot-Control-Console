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

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "$repo = $env:ALPHAPILOT_REPO;" ^
  "$py = $env:ALPHAPILOT_PY;" ^
  "$url = $env:ALPHAPILOT_URL;" ^
  "$old = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*alphapilot_control_console.http_app*' };" ^
  "foreach ($p in $old) { Stop-Process -Id $p.ProcessId -Force };" ^
  "Start-Sleep -Milliseconds 500;" ^
  "Start-Process -FilePath $py -ArgumentList '-m','alphapilot_control_console.http_app' -WorkingDirectory $repo -WindowStyle Hidden;" ^
  "Start-Sleep -Seconds 2;" ^
  "$health = Invoke-RestMethod -UseBasicParsing ($url + 'api/health') -TimeoutSec 20;" ^
  "if ($health.ok -ne $true) { throw 'Health check failed.' };" ^
  "Write-Host ('[AlphaPilot] Control Console is running: ' + $health.version);" ^
  "Start-Process $url;"

if errorlevel 1 (
  echo.
  echo [AlphaPilot] Startup failed. Keep this window open and send the error to Codex.
  pause
  exit /b 1
)

echo [AlphaPilot] Opened %ALPHAPILOT_URL%
exit /b 0
