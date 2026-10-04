"""A very small web server, so the face has something to read.

Serves three things and nothing else:

  GET  /state       the bus file, as JSON, plus the panel's cards (panel_data.py)
  POST /say         a typed message, handed to the assistant as if spoken
  GET  /<anything>  static files from the web folder (interface.html and friends)

Standard library only — no Flask, no extra install. It binds to 127.0.0.1, so
it is reachable from this machine and from nowhere else. That matters twice
over: the file it serves says what you are saying out loud, and `/say` puts
words into your assistant's mouth. Neither should be reachable from the network.

Runs on a daemon thread inside the assistant, so closing the assistant closes
the face with it.
"""

from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import panel_data                      # the panel's cards, read from the vault
except Exception:                          # an older install without the file
    panel_data = None

DEFAULT_PORT = 8781


MAX_MESSAGE = 4000                          # a typed line, not a file upload


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, bus_file: Path, on_message=None, **kwargs):
        self.bus_file = bus_file
        self.on_message = on_message
        super().__init__(*args, **kwargs)

    def do_GET(self):                       # noqa: N802  (stdlib naming)
        if self.path.split("?")[0].rstrip("/") in ("/state", "/state.json"):
            return self._send_state()
        return super().do_GET()

    def do_POST(self):                      # noqa: N802  (stdlib naming)
        if self.path.split("?")[0].rstrip("/") != "/say":
            return self._send_json(404, {"error": "not found"})
        if self.on_message is None:
            # the face is being served without an assistant behind it
            return self._send_json(503, {"error": "nothing is listening"})
        try:
            length = min(int(self.headers.get("Content-Length") or 0), MAX_MESSAGE)
            body = self.rfile.read(length) if length else b""
            text = (json.loads(body or b"{}").get("text") or "").strip()
        except Exception:
            return self._send_json(400, {"error": "expected {\"text\": \"...\"}"})
        if not text:
            return self._send_json(400, {"error": "empty message"})
        try:
            self.on_message(text[:MAX_MESSAGE])
        except Exception as e:
            return self._send_json(500, {"error": str(e)[:200]})
        return self._send_json(200, {"ok": True})

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_state(self):
        try:
            body = self.bus_file.read_bytes()
        except Exception:
            # no bus yet, or caught mid-replace — say so honestly rather than
            # sending something that looks like real state
            body = json.dumps({"state": "idle", "level": 0.0, "wave": []}).encode()
        # The panel's cards ride along on the same poll: one request, one
        # moment in time. If reading the vault fails for any reason the state
        # still goes out exactly as it was — the face must never stall on it.
        if panel_data is not None:
            try:
                doc = json.loads(body)
                doc["panel"] = panel_data.snapshot(
                    Path(self.directory), self.bus_file.parent, doc.get("activity"))
                body = json.dumps(doc, ensure_ascii=False).encode()
            except Exception:
                pass
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass                                # the console belongs to the assistant


def start(web_dir: Path, bus_file: Path, port: int = DEFAULT_PORT, on_message=None):
    """Start serving in the background. Returns (server, url), or (None, None)
    if the port is taken — a face that won't start must never stop the voice.

    `on_message(text)` is called when someone types into the face. Leave it None
    and the box is read-only: it still shows everything, it just can't be talked
    into. Typing then reports honestly that nothing is listening.
    """
    try:
        handler = partial(_Handler, bus_file=bus_file, on_message=on_message,
                          directory=str(web_dir))
        httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError as e:
        print(f"[face] not started ({e}) — the assistant runs without it.")
        return None, None

    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{port}/interface.html"


if __name__ == "__main__":
    import sys

    here = Path(__file__).parent
    web = Path(sys.argv[1]) if len(sys.argv) > 1 else here
    bus = Path(sys.argv[2]) if len(sys.argv) > 2 else here / ".bus" / "state.json"
    server, url = start(web, bus)
    if server:
        print(f"serving {web} at {url}")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
