#!/bin/bash
# Starts the voice on macOS and Linux — the counterpart of run.bat.
# Lives in the vault's `voice` folder and finds everything relative to itself,
# so moving the vault doesn't break it.
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$HERE/.venv/bin/python" ]; then
  echo
  echo "  The voice isn't installed yet - run /jarvis-voice first."
  echo
  exit 1
fi
cd "$HERE"
exec "$HERE/.venv/bin/python" "$HERE/main.py" "$@"
