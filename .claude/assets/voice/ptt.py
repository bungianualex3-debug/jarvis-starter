"""Hold-to-talk — a global key listener.

Hold the key, talk, let go. Nothing is recorded while the key is up, which is
the whole point: no always-on microphone, and it works in a noisy room or with
other people around.

On Windows this runs in an ordinary console process — no admin rights and no
OS permission prompt. (Microphone access for desktop apps still has to be
allowed under Settings > Privacy & security > Microphone.)

On a Mac the system has to be told that the app running this — normally
Terminal — may watch the keyboard: System Settings > Privacy & Security >
Accessibility AND Input Monitoring. Without that macOS raises no error at all;
the listener starts and simply never sees a key. `start()` checks for exactly
that and refuses loudly instead of leaving a deaf assistant that looks fine.

CRITICAL — the bug this file exists to avoid: Windows fires `on_press`
repeatedly while a key is held down. Without a held flag, every one of those
repeats looks like a brand new press, and the assistant cuts itself off before
it can ever answer. The `_held` flag below is the fix, and it is not optional.

If pynput isn't installed or the listener can't start, `AVAILABLE` stays False
and the caller falls back to a simpler input method rather than failing.
"""

from __future__ import annotations

import sys
import threading
import time

try:
    from pynput import keyboard
    AVAILABLE = True
except Exception:                      # not installed, or no display/session
    keyboard = None
    AVAILABLE = False


KEYS = {}
if AVAILABLE:
    KEYS = {
        "right_ctrl": keyboard.Key.ctrl_r,
        "left_ctrl": keyboard.Key.ctrl_l,
        "right_alt": keyboard.Key.alt_r,
        "right_shift": keyboard.Key.shift_r,
        "caps_lock": keyboard.Key.caps_lock,
        "f8": keyboard.Key.f8,
        "f9": keyboard.Key.f9,
        "pause": keyboard.Key.pause,
    }

MIN_HOLD_SECONDS = 0.25                # taps shorter than this are ignored

# A MacBook keyboard has no right Ctrl, so the default there is right Option.
DEFAULT_KEY = "right_alt" if sys.platform == "darwin" else "right_ctrl"

MAC_PERMISSION_HELP = (
    "macOS is not letting this app watch the keyboard. Open System Settings > "
    "Privacy & Security, add Terminal under both Accessibility and Input "
    "Monitoring, then quit Terminal completely and start again"
)


class PushToTalk:
    """Watches one key. `wait_for_press()` blocks until it goes down;
    `is_held()` is true for as long as it stays down."""

    def __init__(self, key_name: str = DEFAULT_KEY):
        if not AVAILABLE:
            raise RuntimeError("pynput is not available")
        self.key_name = key_name if key_name in KEYS else DEFAULT_KEY
        self._key = KEYS[self.key_name]
        self._held = False             # the key-repeat filter — see module docstring
        self._down_at = 0.0
        self._press_event = threading.Event()
        self._release_event = threading.Event()
        self._listener = None

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()
        self._listener.wait()          # raises if the hook could not be installed
        # macOS: an untrusted process gets a listener that never fires. pynput
        # records whether the system trusts us; no attribute means not a Mac.
        if sys.platform == "darwin" and getattr(self._listener, "IS_TRUSTED", True) is False:
            self.stop()
            raise RuntimeError(MAC_PERMISSION_HELP)

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    # -- state -------------------------------------------------------------
    def is_held(self) -> bool:
        return self._held

    def held_seconds(self) -> float:
        return time.time() - self._down_at if self._held else 0.0

    def wait_for_press(self, timeout: float | None = None) -> bool:
        """Block until the key goes down. False if it timed out instead —
        callers use the timeout so Ctrl+C still gets a look in."""
        if self._press_event.wait(timeout):
            self._press_event.clear()
            return True
        return False

    def clear_press(self) -> None:
        """Forget a press we've already acted on — used after a barge-in, so
        the same keystroke doesn't also trigger the next turn."""
        self._press_event.clear()

    def wait_for_release(self, timeout: float | None = None) -> bool:
        if self._release_event.wait(timeout):
            self._release_event.clear()
            return True
        return False

    # -- callbacks (pynput's thread) ---------------------------------------
    def _on_press(self, key) -> None:
        if key != self._key or self._held:
            return                     # not our key, or an OS repeat
        self._held = True
        self._down_at = time.time()
        self._release_event.clear()
        self._press_event.set()

    def _on_release(self, key) -> None:
        if key != self._key or not self._held:
            return
        self._held = False
        self._release_event.set()
