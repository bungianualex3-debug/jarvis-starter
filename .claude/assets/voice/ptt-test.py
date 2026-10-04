"""Proves the hold-to-talk key listener works, without starting the assistant.

    python ptt-test.py            # right Ctrl (right Option on a Mac)
    python ptt-test.py f9         # any key name from ptt.KEYS

Deliberately isolated: no Whisper, no microphone, no model loading. If this
prints sensible hold times, the key half of the voice loop is sound and any
later problem is somewhere else.

Use a key OTHER than right Ctrl if another assistant is already running on it —
two listeners on one key both fire, and both start recording.
"""

import sys
import time

import ptt

key = sys.argv[1] if len(sys.argv) > 1 else ptt.DEFAULT_KEY

if not ptt.AVAILABLE:
    print("pynput is not installed — hold-to-talk can't run on this machine.")
    raise SystemExit(1)

talk = ptt.PushToTalk(key)
try:
    talk.start()
except RuntimeError as e:
    print(f"The key listener could not start: {e}.")
    raise SystemExit(1)

print(f"Listening for: {talk.key_name.replace('_', ' ')}")
print("Hold it, count to two, let go. Do it a few times. Ctrl+C to stop.\n")

holds = 0
try:
    while True:
        if not talk.wait_for_press(timeout=0.5):
            continue
        t0 = time.time()
        while talk.is_held():
            time.sleep(0.01)
        held = time.time() - t0
        holds += 1
        if held < ptt.MIN_HOLD_SECONDS:
            print(f"  {holds}. tap ({held:.2f}s) — too short, would be ignored")
        else:
            print(f"  {holds}. held {held:.2f}s — would record {held:.1f}s of audio")
except KeyboardInterrupt:
    print(f"\n{holds} hold(s) detected. "
          f"{'Key listener works.' if holds else 'Nothing detected — the listener is not seeing that key.'}")
finally:
    talk.stop()
