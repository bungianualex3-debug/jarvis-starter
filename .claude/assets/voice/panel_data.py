"""What the panel shows, read from the vault.

The panel is not a second memory. Everything on it is already written down
somewhere in the vault, and this file only reads it:

    today's goal        voice/.bus/goal.json   (set with panel.py, valid today)
    waiting on you      the "blocked" section of the active-work note
    open work           the "in progress" section of the same note
    remembered today    the bullet lines of today's daily note, newest first
    what it's doing     the tool the assistant is using right now
    the stage           voice/.bus/stage.json  (set with panel.py)

A vault is written in its owner's language, so nothing here can guess a file
or heading name. `/jarvis-interface` writes them into `panel.json` at the vault
root, and that file is the only place this one looks. No `panel.json`, or a
name in it that matches nothing: that card stays empty. It never invents.

Standard library only, and nothing in here is allowed to raise: a panel that
fails to fill is cosmetic, a face server that crashes because of it is not.
"""

from __future__ import annotations

import datetime
import json
import re
import time
from pathlib import Path

DEFAULTS = {
    "active_work": "Active work.md",
    "open_heading": "In progress",
    "blocked_heading": "Blocked on me",
    "daily_folder": "",
    "working": "Working",
    "activity": {
        "Read": "Reading a note",
        "Write": "Writing a note",
        "Edit": "Editing a note",
        "Grep": "Searching the vault",
        "Glob": "Looking through the folders",
        "Bash": "Running a command",
        "PowerShell": "Running a command",
        "WebSearch": "Searching the web",
        "WebFetch": "Reading a web page",
        "Task": "Handing part of it to a helper",
        "Agent": "Handing part of it to a helper",
    },
}

MAX_ITEMS = 12
MAX_MEMORY = 30
MAX_CHARS = 180
_TTL = 2.0                         # seconds a snapshot is reused; the face polls far faster

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^\s*[-*+]\s+(?:\[( |x|X)\]\s+)?(.*\S)\s*$")
_TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
_STAMP = re.compile(r"\(?\b\d{4}-\d{2}-\d{2}[ T]([01]?\d|2[0-3]):[0-5]\d(?:\s+[A-Z]{2,5})?\)?\s*")
_LEADTIME = re.compile(r"^\s*\(?([01]?\d|2[0-3]):[0-5]\d\)?\s*[-–—:]?\s*")   # a bare "(11:05)" in front
_LINK = re.compile(r"\[\[([^\]|]*\|)?([^\]]*)\]\]")
_MDLINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")

_cache: dict = {"at": 0.0, "key": None, "value": None}


def _clean(text: str) -> str:
    text = _LINK.sub(lambda m: m.group(2), text)
    text = _MDLINK.sub(r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\s+", " ", text).strip(" -–—:·")
    return text[:MAX_CHARS]


def _config(vault: Path) -> dict:
    cfg = dict(DEFAULTS)
    cfg["activity"] = dict(DEFAULTS["activity"])
    try:
        user = json.loads((vault / "panel.json").read_text(encoding="utf-8"))
        for key, value in user.items():
            if key == "activity" and isinstance(value, dict):
                cfg["activity"].update(value)
            elif key in cfg and isinstance(value, str):
                cfg[key] = value
    except Exception:
        pass
    return cfg


def _sections(path: Path) -> dict:
    """The note as {heading (lower-case): [open bullet, ...]}. Ticked boxes are
    done, so they are left out."""
    out: dict = {}
    current = ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return out
    for line in lines:
        h = _HEADING.match(line)
        if h:
            current = _clean(h.group(1)).lower()
            out.setdefault(current, [])
            continue
        b = _BULLET.match(line)
        if b and current:
            if b.group(1) in ("x", "X"):
                continue
            text = _clean(b.group(2))
            if text:
                out[current].append(text)
    return out


def _section(sections: dict, heading: str) -> list:
    """The bullets under the heading whose text contains `heading`."""
    want = (heading or "").strip().lower()
    if not want:
        return []
    for name, items in sections.items():
        if want in name:
            return items[:MAX_ITEMS]
    return []


def _daily_note(vault: Path, folder: str):
    if not folder:
        return None
    name = datetime.date.today().isoformat() + ".md"
    base = vault / folder
    direct = base / name
    if direct.is_file():
        return direct
    try:                                    # notes sorted into month subfolders
        for found in base.rglob(name):
            return found
    except Exception:
        pass
    return None


def _memory(path) -> list:
    """Today's bullets, newest first. The time comes from the line itself when
    it carries one; a line with no time still counts, it just shows without."""
    if path is None:
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    out = []
    for line in lines:
        b = _BULLET.match(line)
        if not b:
            continue
        raw = b.group(2)
        t = _TIME.search(raw)
        text = _clean(_LEADTIME.sub("", _STAMP.sub("", raw)))
        if len(text) < 3:
            continue                        # an empty template bullet
        out.append({"t": f"{int(t.group(1)):02d}:{t.group(2)}" if t else "", "text": text})
    out.reverse()
    return out[:MAX_MEMORY]


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _mtime(path) -> float:
    try:
        return path.stat().st_mtime if path else 0.0
    except Exception:
        return 0.0


def snapshot(vault: Path, bus_dir: Path, activity=None) -> dict:
    """Everything the panel needs, as one dict. Cheap to call often."""
    try:
        vault, bus_dir = Path(vault), Path(bus_dir)
        cfg = _config(vault)
        active = vault / cfg["active_work"]
        daily = _daily_note(vault, cfg["daily_folder"])
        tool = (activity or {}).get("tool") or ""
        key = (_mtime(vault / "panel.json"), _mtime(active), str(daily), _mtime(daily),
               _mtime(bus_dir / "goal.json"), _mtime(bus_dir / "stage.json"), tool,
               datetime.date.today().isoformat())
        now = time.time()
        if _cache["key"] == key and now - _cache["at"] < _TTL:
            return _cache["value"]

        sections = _sections(active)
        value: dict = {
            "open": _section(sections, cfg["open_heading"]),
            "waiting": _section(sections, cfg["blocked_heading"]),
            "memory": _memory(daily),
            "activity": {"text": cfg["activity"].get(tool, cfg["working"]) if tool else "",
                         "busy": bool(tool)},
            "goal": {"text": "", "done": False},
        }
        goal = _json(bus_dir / "goal.json")
        if isinstance(goal, dict) and goal.get("date") == datetime.date.today().isoformat():
            value["goal"] = {"text": str(goal.get("text") or "")[:MAX_CHARS],
                             "done": bool(goal.get("done"))}
        stage = _json(bus_dir / "stage.json")
        if isinstance(stage, dict) and stage.get("kind"):
            value["stage"] = stage

        _cache.update(at=now, key=key, value=value)
        return value
    except Exception:
        return {}
