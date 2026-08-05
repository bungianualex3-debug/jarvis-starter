@echo off
setlocal enabledelayedexpansion
title Jarvis

rem ============================================================
rem  START  --  brings up the voice (if installed) and opens the
rem  interface fullscreen.
rem
rem  This file lives in the vault, next to interface.html, and
rem  finds everything relative to itself. Move the vault and it
rem  keeps working; there are no absolute paths in here.
rem
rem  ORDER MATTERS. The voice starts FIRST, because it is also
rem  the little web server the face reads its live state from.
rem  Opened as a plain file the page cannot reach that state --
rem  it animates a demo loop forever and never reacts to your
rem  voice. So we wait for the voice to publish its address,
rem  then open THAT. No voice installed, no waiting: the page
rem  opens straight from disk, in demo mode, which is honest.
rem ============================================================

set "DIR=%~dp0"
set "PAGE=%DIR%interface.html"

rem a throwaway browser profile, named after this vault, so Stop can find
rem exactly this window later and never touch your normal browser
for %%I in ("%~dp0.") do set "VAULTNAME=%%~nxI"
set "KIOSKDIR=%TEMP%\jarvis-kiosk-%VAULTNAME%"

if not exist "%PAGE%" (
  echo.
  echo   Can't find interface.html next to this file.
  echo   Looked in: %DIR%
  echo.
  pause
  exit /b 1
)

rem the fallback: the page straight off the disk, in demo mode
set "URL=file:///%PAGE:\=/%"

rem ---------------------------------------------------------------- voice
rem Filled in by /jarvis-voice. It starts the voice, then waits for
rem voice\.bus\face.url to appear and points the browser at it instead.
rem Leave this marker here; the voice command looks for it.


rem ---------------------------------------------------------------- browser
rem Chrome first, then Edge. Edge is on every Windows machine, so this
rem works even for someone who has never installed anything.
set "BROWSER="
for %%p in (
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
) do if not defined BROWSER if exist %%p set "BROWSER=%%~p"

if not defined BROWSER (
  echo.
  echo   No Chrome or Edge found - opening your default browser.
  echo   Press F11 for fullscreen.
  echo.
  start "" "%URL%"
  rem full path on purpose: some machines have a GNU `timeout` earlier on PATH
  rem (Git for Windows, msys, coreutils), which takes different arguments and
  rem fails instantly instead of waiting. See the note in the voice section.
  "%SystemRoot%\System32\timeout.exe" /t 4 >nul
  exit /b 0
)

rem fresh profile every time: no tabs, no extensions, no restore bubble
if exist "%KIOSKDIR%" rmdir /s /q "%KIOSKDIR%" >nul 2>nul

echo.
echo   Starting. Close it with the Stop shortcut, or press Alt+F4.
echo.

start "" "%BROWSER%" ^
  --kiosk ^
  --user-data-dir="%KIOSKDIR%" ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-session-crashed-bubble ^
  --hide-crash-restore-bubble ^
  --disable-features=Translate,InfiniteSessionRestore ^
  --autoplay-policy=no-user-gesture-required ^
  "%URL%"

exit /b 0
