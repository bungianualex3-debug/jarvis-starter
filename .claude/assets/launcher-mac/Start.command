#!/bin/bash
# ============================================================
#  START  --  brings up the voice (if installed) and opens the
#  interface fullscreen. Double-click it in Finder.
#
#  This file lives in the vault, next to interface.html, and
#  finds everything relative to itself. Move the vault and it
#  keeps working; there are no absolute paths in here.
#
#  ORDER MATTERS. The voice starts FIRST, because it is also
#  the little web server the face reads its live state from.
#  Opened as a plain file the page cannot reach that state --
#  it animates a demo loop forever and never reacts to your
#  voice. So we wait for the voice to publish its address,
#  then open THAT. No voice installed, no waiting: the page
#  opens straight from disk, in demo mode, which is honest.
# ============================================================

DIR="$(cd "$(dirname "$0")" && pwd)"
PAGE="$DIR/interface.html"

# a throwaway browser profile, named after this vault, so Stop can find
# exactly this window later and never touch your normal browser
VAULTNAME="$(basename "$DIR")"
KIOSKDIR="${TMPDIR:-/tmp}/jarvis-kiosk-$VAULTNAME"

if [ ! -f "$PAGE" ]; then
  echo
  echo "  Can't find interface.html next to this file."
  echo "  Looked in: $DIR"
  echo
  exit 1
fi

# the fallback: the page straight off the disk, in demo mode
URL="$PAGE"

# ---------------------------------------------------------------- voice
# Filled in by /jarvis-voice. It starts the voice, then waits for
# voice/.bus/face.url to appear and points the browser at it instead.
# Leave this marker here; the voice command looks for it.


# ---------------------------------------------------------------- browser
# Chrome first, then Edge, then Brave. They share the fullscreen flags.
BROWSER=""
for app in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
do
  if [ -z "$BROWSER" ] && [ -x "$app" ]; then BROWSER="$app"; fi
done

if [ -z "$BROWSER" ]; then
  echo
  echo "  No Chrome, Edge or Brave found - opening your default browser."
  echo "  Press Ctrl+Cmd+F for fullscreen."
  echo
  open "$URL"
  exit 0
fi

# fresh profile every time: no tabs, no extensions, no restore bubble
rm -rf "$KIOSKDIR"

echo
echo "  Starting. Close it with Stop, or press Cmd+Q."
echo

"$BROWSER" \
  --kiosk \
  --user-data-dir="$KIOSKDIR" \
  --no-first-run \
  --no-default-browser-check \
  --disable-session-crashed-bubble \
  --hide-crash-restore-bubble \
  --disable-features=Translate,InfiniteSessionRestore \
  --autoplay-policy=no-user-gesture-required \
  "$URL" >/dev/null 2>&1 &

exit 0
