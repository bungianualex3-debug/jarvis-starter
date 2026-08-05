@echo off
rem Starts the voice. Lives in the vault's `voice` folder and finds everything
rem relative to itself, so moving the vault doesn't break it.
setlocal
set "HERE=%~dp0"
if not exist "%HERE%.venv\Scripts\python.exe" (
  echo.
  echo   The voice isn't installed yet - run /jarvis-voice first.
  echo.
  pause
  exit /b 1
)
title Jarvis voice
"%HERE%.venv\Scripts\python.exe" "%HERE%main.py" %*
exit /b 0
