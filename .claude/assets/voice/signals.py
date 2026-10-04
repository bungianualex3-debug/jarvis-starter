"""The bus between the assistant and its face.

One small JSON file, rewritten atomically. The face polls it a few times a
second and draws whatever it says. That's the whole contract:

    { "state":        "idle" | "listening" | "thinking" | "speaking",
      "level":        0..1,
      "wave":         [64 floats, roughly -1..1],
      "caption":      { "text": str, "seq": int, "dur": seconds },
      "conversation": [ { "role": "user"|"assistant", "text": str }, ... ],
      "activity":     { "tool": str, "ts": seconds } }

Deliberately one file rather than several: a single atomic replace means the
face can never read a half-written mixture of two moments.

Nothing in here is allowed to raise. A face that fails to update is a cosmetic
problem; an assistant that crashes because its face failed is a real one, so
every write swallows its errors.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path

IDLE = "idle"
LISTENING = "listening"
THINKING = "thinking"
SPEAKING = "speaking"

WAVE_POINTS = 64
MAX_TURNS = 20                    # what the on-screen conversation keeps
_MIN_INTERVAL = 1.0 / 20          # cap writes at 20/second

_lock = threading.Lock()
_path: Path | None = None
_last_write = 0.0
_seq = 0
_doc = {
    "state": IDLE,
    "level": 0.0,
    "wave": [0.0] * WAVE_POINTS,
    "caption": {"text": "", "seq": 0, "dur": 0.0},
    "conversation": [],
}


def configure(bus_file: Path) -> None:
    """Point the bus at a file. Until this is called, everything is a no-op,
    so the assistant runs perfectly well with no face attached."""
    global _path
    try:
        bus_file.parent.mkdir(parents=True, exist_ok=True)
        _path = bus_file
        _write(force=True)
    except Exception:
        _path = None


def _write(force: bool = False) -> None:
    global _last_write
    if _path is None:
        return
    now = time.time()
    if not force and now - _last_write < _MIN_INTERVAL:
        return
    _last_write = now
    try:
        # write next to the target so os.replace stays on one filesystem
        fd, tmp = tempfile.mkstemp(dir=str(_path.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(_doc, fh, ensure_ascii=False)
        os.replace(tmp, _path)        # atomic on Windows and POSIX
    except Exception:
        pass


def set_state(state: str) -> None:
    with _lock:
        _doc["state"] = state
        if state != SPEAKING:
            _doc["level"] = 0.0
        _write(force=True)


def settle() -> None:
    """Back to idle, but only if it is still showing `speaking`.

    For speech that happens outside a turn — the greeting at start-up. A turn
    sets idle itself when it ends; the greeting has nothing after it to do
    that, so the face would sit in its speaking state until the first real
    exchange. The check is what makes this safe to call late: if they have
    already pressed the key, the state is `listening` and is left alone.
    """
    with _lock:
        if _doc["state"] != SPEAKING:
            return
        _doc["state"] = IDLE
        _doc["level"] = 0.0
        _doc["caption"] = {"text": "", "seq": _doc["caption"]["seq"], "dur": 0.0}
        _write(force=True)


def set_signal(level: float, wave) -> None:
    """Publish how loud it is right now, and the shape of the sound."""
    with _lock:
        try:
            _doc["level"] = max(0.0, min(1.0, float(level)))
            _doc["wave"] = [round(float(v), 4) for v in wave][:WAVE_POINTS]
        except Exception:
            return
        _write()


def set_caption(text: str, dur: float = 0.0) -> None:
    """The line being spoken, and how long its audio actually lasts — the face
    uses the real duration to light words in time with the voice instead of
    guessing from how long the sentence looks."""
    global _seq
    with _lock:
        text = (text or "").strip()
        if not text:
            return
        _seq += 1
        _doc["caption"] = {"text": text, "seq": _seq, "dur": max(0.0, float(dur))}
        _write(force=True)


def clear_caption() -> None:
    with _lock:
        _doc["caption"] = {"text": "", "seq": _doc["caption"]["seq"], "dur": 0.0}
        _write(force=True)


def push_conversation(role: str, text: str) -> None:
    """Add a turn to the conversation shown on screen.

    Spoken captions vanish the moment the next sentence starts, which is right
    for a caption and useless for anyone who looked away, or who is typing
    rather than talking. This keeps the last few turns readable.
    """
    with _lock:
        text = (text or "").strip()
        if not text or role not in ("user", "assistant"):
            return
        convo = _doc.get("conversation") or []
        # The assistant answers in several sentences; append to its last turn
        # rather than stacking one bubble per sentence, which reads as stutter.
        if convo and convo[-1].get("role") == role == "assistant":
            convo[-1]["text"] = (convo[-1]["text"] + " " + text).strip()
        else:
            convo.append({"role": role, "text": text})
        _doc["conversation"] = convo[-MAX_TURNS:]
        _write(force=True)


def set_activity(tool: str) -> None:
    """Which tool the assistant is using right now, or "" when it has finished.
    The panel turns the name into a plain line ("Reading a note"), so a silent
    wait on screen reads as work rather than as a hang."""
    with _lock:
        _doc["activity"] = {"tool": (tool or "")[:40], "ts": time.time()}
        _write(force=True)


def reset() -> None:
    """Leave the face at rest on the way out, so it doesn't sit there looking
    like it's still listening to an assistant that has quit."""
    with _lock:
        _doc["state"] = IDLE
        _doc["level"] = 0.0
        _doc["wave"] = [0.0] * WAVE_POINTS
        _doc["activity"] = {"tool": "", "ts": time.time()}
        _write(force=True)


def envelope(samples, points: int = WAVE_POINTS):
    """Squash any block of audio down to `points` values in -1..1."""
    try:
        import numpy as np

        a = np.asarray(samples, dtype="float32").reshape(-1)
        if a.size == 0:
            return [0.0] * points
        if a.size >= points:
            usable = (a.size // points) * points
            out = a[:usable].reshape(points, -1).mean(axis=1)
        else:
            out = np.interp(
                np.linspace(0, a.size - 1, points), np.arange(a.size), a
            )
        peak = float(np.max(np.abs(out))) or 1.0
        if peak > 1.0:
            out = out / peak
        return [float(v) for v in out]
    except Exception:
        return [0.0] * points
