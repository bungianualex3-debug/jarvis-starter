#!/bin/bash
# ============================================================
#  STOP  --  closes the interface. Double-click it in Finder.
#
#  It only closes the window Start opened. It finds it by the
#  throwaway profile folder Start created, so your ordinary
#  browser windows and tabs are never touched.
# ============================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
VAULTNAME="$(basename "$DIR")"
KIOSKDIR="${TMPDIR:-/tmp}/jarvis-kiosk-$VAULTNAME"

if pkill -f -- "--user-data-dir=$KIOSKDIR" 2>/dev/null; then
  echo "  Closed."
else
  echo "  Nothing was running."
fi

# ---------------------------------------------------------------- voice
# The voice command's stop line goes here.

exit 0
