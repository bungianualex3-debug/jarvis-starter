@echo off
setlocal enabledelayedexpansion
title Jarvis - stop

rem ============================================================
rem  STOP  --  closes the interface.
rem
rem  It only closes the window Start opened. It finds it by the
rem  throwaway profile folder Start created, so your ordinary
rem  browser windows and tabs are never touched.
rem ============================================================

for %%I in ("%~dp0.") do set "VAULTNAME=%%~nxI"
set "KIOSKDIR=%TEMP%\jarvis-kiosk-%VAULTNAME%"

powershell -NoProfile -Command ^
  "$mark = $env:KIOSKDIR;" ^
  "$p = Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' or Name='msedge.exe'\" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($mark) };" ^
  "if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host '  Closed.' } else { Write-Host '  Nothing was running.' }"

rem ---------------------------------------------------------------- voice
rem The voice command's stop line goes here.

rem full path on purpose: a GNU `timeout` earlier on PATH takes other arguments
"%SystemRoot%\System32\timeout.exe" /t 2 >nul
exit /b 0
