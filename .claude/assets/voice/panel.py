"""Put something on the panel. Run by the assistant, from the vault folder.

    python voice/panel.py goal "Send the offer to the first client"
    python voice/panel.py goal --done
    python voice/panel.py goal --clear

    python voice/panel.py show text  "Offer email"  notes/offer.md
    python voice/panel.py show text  "A thought"    "Any text, straight on the stage."
    python voice/panel.py show list  "Plan for today" plan.txt      one "09:00 | what" per line
    python voice/panel.py show page  "Price page"   drafts/prices.html
    python voice/panel.py show image "The logo"     assets/logo.png

On macOS and Linux the first word is `python3`, or the vault's own
`voice/.venv/bin/python`.

It only writes two small files in `voice/.bus/`; the face reads them on its next
poll. A page or an image has to be reachable by the face's own little server,
which serves the vault folder — so a file inside the vault is shown where it
is, and one from anywhere else is copied into `voice/.bus/stage/` first.

Standard library only: this must work before, and without, the voice install.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

BOX = Path(__file__).resolve().parent          # the voice folder
VAULT = BOX.parent
BUS = BOX / ".bus"

MAX_PARAGRAPHS = 40
MAX_ROWS = 40


def _write(name: str, doc: dict) -> None:
    BUS.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(BUS), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False)
    os.replace(tmp, BUS / name)


def _text_of(arg: str) -> str:
    """A path to a file gives the file; anything else is the text itself."""
    try:
        p = Path(arg)
        if p.is_file():
            return p.read_text(encoding="utf-8")
    except (OSError, ValueError):
        pass
    return arg


def _address(arg: str) -> str:
    """The address the face can load this file from."""
    p = Path(arg).resolve()
    if not p.is_file():
        raise SystemExit(f"not a file: {arg}")
    try:
        rel = p.relative_to(VAULT)
    except ValueError:
        stage_dir = BUS / "stage"
        stage_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, stage_dir / p.name)
        rel = (stage_dir / p.name).relative_to(VAULT)
    return "/" + quote(rel.as_posix())


def goal(args: list) -> None:
    path = BUS / "goal.json"
    today = datetime.date.today().isoformat()
    if args and args[0] == "--clear":
        _write("goal.json", {"text": "", "done": False, "date": today})
        print("goal cleared")
        return
    if args and args[0] == "--done":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raise SystemExit("there is no goal set for today")
        if doc.get("date") != today or not doc.get("text"):
            raise SystemExit("there is no goal set for today")
        doc["done"] = True
        _write("goal.json", doc)
        print("goal marked done:", doc["text"])
        return
    text = " ".join(args).strip()
    if not text:
        raise SystemExit('usage: panel.py goal "the one thing for today" | --done | --clear')
    _write("goal.json", {"text": text, "done": False, "date": today})
    print("goal set:", text)


def show(args: list) -> None:
    if len(args) < 3:
        raise SystemExit('usage: panel.py show text|list|page|image "Title" <file or text>')
    kind, title, arg = args[0], args[1], " ".join(args[2:])
    item: dict = {"seq": int(time.time() * 1000), "title": title}

    if kind == "text":
        lines = _text_of(arg).replace("\r\n", "\n").strip().split("\n")
        heading = title
        if lines and lines[0].lstrip().startswith("#"):
            heading = lines.pop(0).lstrip("# ").strip() or title
        blocks = [b.strip() for b in "\n".join(lines).split("\n\n")]
        body = [" ".join(b.split()) for b in blocks if b and not b.startswith("---")]
        item.update(kind="text", heading=heading, body=body[:MAX_PARAGRAPHS])
    elif kind == "list":
        rows = []
        for line in _text_of(arg).replace("\r\n", "\n").split("\n"):
            line = line.strip().lstrip("-*+ ").strip()
            if not line:
                continue
            left, sep, right = line.partition("|")
            rows.append([left.strip(), right.strip()] if sep else ["·", line])
        item.update(kind="rows", heading=title, rows=rows[:MAX_ROWS])
    elif kind == "page":
        item.update(kind="page", src=_address(arg))
    elif kind == "image":
        item.update(kind="image", src=_address(arg))
    else:
        raise SystemExit(f"unknown kind: {kind} (use text, list, page or image)")

    _write("stage.json", item)
    print(f"on the stage: {title} ({item['kind']})")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not args or args[0] not in ("goal", "show"):
        raise SystemExit(__doc__)
    (goal if args[0] == "goal" else show)(args[1:])


if __name__ == "__main__":
    main()
