"""Brain — the thinking, done by the Claude you already pay for.

No API key, nothing metered: this drives the Claude Code already installed on
this machine, exactly as if you had typed into it yourself.

The identity is NOT injected here. The session runs from inside the vault, and
Claude Code reads that folder's `CLAUDE.md` on its own — the same boot file the
typed sessions use. So the voice and the keyboard are the same assistant, with
one identity, and there is no second copy of the rules to drift out of step.

The only thing added on top is a spoken-reply reminder, because a reply full of
bullet points, or in the wrong language, is the one failure you can't skim past.

Why it's built this way
-----------------------
There are two ways to reach Claude Code from Python, and the difference between
them is the whole reason this file has the shape it does.

The obvious way is to run the `claude` command once per turn. It works, and it
is what this box did first — but every turn pays for a brand new process:
startup, config, and re-reading the conversation so far. Measured on this
machine on 2026-08-05, a one-word reply in a nearly empty vault took **4.8
seconds** before a microphone or a speaker was involved, and it gets worse as
the conversation grows.

So the fast path keeps ONE session open for the life of the assistant and
streams the reply as it is written. That fixes two things at once: the per-turn
startup disappears, and the mouth can start speaking the first sentence while
the rest is still being thought — which is most of what "it answers slowly"
actually was.

The slow way is still here as a fallback. If the SDK isn't installed, or the
session won't open on this machine, the assistant drops back to one process per
turn and says so out loud in the console, rather than refusing to speak. Slow
and working beats fast and missing.
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

import signals

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        StreamEvent,
        TextBlock,
    )
    SDK_AVAILABLE = True
except Exception:                      # not installed, or too old a version
    SDK_AVAILABLE = False


# A sentence ends at . ! ? … or at a blank line. Kept deliberately simple:
# over-splitting costs a slightly clipped breath, under-splitting costs silence.
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n{2,}")

_MD_PATTERNS = [
    (re.compile(r"```.*?```", re.S), " "),              # code fences
    (re.compile(r"`([^`]*)`"), r"\1"),                  # inline code
    (re.compile(r"\*\*([^*]*)\*\*"), r"\1"),            # bold
    (re.compile(r"(?<!\w)\*([^*]*)\*(?!\w)"), r"\1"),   # italic
    (re.compile(r"^\s*[-*+]\s+", re.M), ""),            # bullets
    (re.compile(r"^\s*#{1,6}\s*", re.M), ""),           # headings
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),      # links -> their text
]


def strip_markdown(text: str) -> str:
    """Markdown is for eyes. Read aloud it becomes noise, like 'star star'."""
    for pattern, replacement in _MD_PATTERNS:
        text = pattern.sub(replacement, text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


class SentenceChunker:
    """Feeds completed sentences to the mouth as they arrive.

    The first sentence ships alone, so sound starts as early as possible — that
    first moment of audio is the entire point of the streaming path. After that
    sentences ship in twos, because lone short ones played on their own sound
    clipped and breathless.
    """

    def __init__(self, emit: Callable[[str], None], breath: int = 2):
        self._emit = emit
        self._breath = breath
        self._buf = ""
        self._pending: list[str] = []
        self._first_sent = False

    def feed(self, text: str) -> None:
        self._buf += text
        while True:
            parts = _SENTENCE_END.split(self._buf, maxsplit=1)
            if len(parts) < 2:
                break
            sentence, self._buf = parts[0].strip(), parts[1]
            if sentence:
                self._push(sentence)

    def _push(self, sentence: str) -> None:
        if not self._first_sent:
            self._first_sent = True
            self._say(sentence)
            return
        self._pending.append(sentence)
        if len(self._pending) >= self._breath:
            self._say(" ".join(self._pending))
            self._pending.clear()

    def flush(self) -> None:
        """Called when a block ends and at the end of the turn."""
        tail = self._buf.strip()
        self._buf = ""
        if tail:
            self._pending.append(tail)
        if self._pending:
            self._say(" ".join(self._pending))
            self._pending.clear()
            self._first_sent = True

    def _say(self, text: str) -> None:
        clean = strip_markdown(text)
        if clean:
            self._emit(clean)


class Brain:
    """One live session, streamed a sentence at a time.

    The rest of this assistant is ordinary blocking code and the SDK is async,
    so the event loop lives on its own thread in here. Everything this class
    exposes is a normal blocking call — the async stays behind the door.
    """

    def __init__(self, cfg, vault_dir: Path):
        self.cfg = cfg
        self.vault_dir = Path(vault_dir)
        self.model = cfg.get("brain", {}).get("model", "").strip()
        self.timeout = int(cfg.get("brain", {}).get("timeout_seconds", 120))
        self.claude = self._find_claude()

        self.streaming = False          # set by start(), once it's known to work
        self._client = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._abandon = False
        self._started_cli = False       # the fallback path's --continue flag

    # ----------------------------------------------------------------- setup

    def _find_claude(self) -> str:
        found = shutil.which("claude")
        if found:
            return found
        guess = Path.home() / ".local" / "bin" / "claude.exe"
        return str(guess) if guess.exists() else "claude"

    def _system_prompt(self) -> str:
        language = self.cfg.get("reply_language", "").strip()
        spoken = (
            "You are being spoken to out loud and your reply is read aloud by a "
            "voice. Keep it short and say it the way a person would. No markdown, "
            "no bullet points, no code blocks, no file paths read out character by "
            "character."
        )
        if not language:
            return spoken
        return (
            f"{spoken} Always reply in {language}, whatever language you are "
            f"spoken to in, even if the words come through garbled."
        )

    def _options(self):
        return ClaudeAgentOptions(
            cwd=str(self.vault_dir),
            # the vault's own CLAUDE.md is the identity; load it exactly the way
            # a typed session does, so the two can never drift apart
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": self._system_prompt(),
            },
            setting_sources=["user", "project", "local"],
            # the whole point: text arrives in pieces instead of all at the end
            include_partial_messages=True,
            model=self.model or None,
            # a big tool result (a long file, a chatty command) must not kill the
            # turn by overflowing the default cap on a single message read
            max_buffer_size=10 * 1024 * 1024,
        )

    def start(self) -> None:
        """Open the live session. Falls back to one-process-per-turn if it can't."""
        if not SDK_AVAILABLE:
            print("[brain] streaming SDK not installed — using the slower "
                  "one-process-per-turn mode.")
            return
        try:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._loop.run_forever, daemon=True, name="brain-loop"
            )
            self._thread.start()
            self._run(self._connect(), timeout=60)
            self.streaming = True
            print("[brain] live session open — replies stream as they're written.")
        except Exception as e:
            print(f"[brain] could not open a live session ({e}); using the "
                  f"slower one-process-per-turn mode.")
            self.streaming = False
            self._client = None

    async def _connect(self) -> None:
        self._client = ClaudeSDKClient(options=self._options())
        await self._client.connect()

    def _run(self, coro, timeout: float | None = None):
        """Run a coroutine on the brain's loop and block until it finishes."""
        if self._loop is None:
            raise RuntimeError("brain loop not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout)

    def warmup(self) -> None:
        """Pay the first turn's start-up cost while the greeting is playing.

        The first question of a session is always the slowest one. Asking a
        throwaway question during the greeting means the person's real first
        question lands on a session that is already warm.
        """
        if not (self.streaming and self._client is not None):
            return
        try:
            self._run(self._warm(), timeout=60)
        except Exception:
            pass                        # a cold first turn is a nuisance, not a fault

    async def _warm(self) -> None:
        await self._client.query("Reply with exactly: ready")
        async for _ in self._client.receive_response():
            pass

    # ---------------------------------------------------------------- asking

    def ask(self, user_text: str, on_sentence: Callable[[str], None]) -> str:
        """Answer one turn, handing each finished sentence to on_sentence.

        Returns the whole reply as text. on_sentence is called while the answer
        is still being written — that is what lets the mouth start speaking
        before the thought is finished.
        """
        if self.streaming and self._client is not None:
            try:
                return self._run(self._ask_streaming(user_text, on_sentence),
                                 timeout=self.timeout)
            except Exception as e:
                # one bad turn must never silence the assistant for good
                print(f"[brain] live session failed this turn ({e}); "
                      f"falling back for it.")
        reply = self._ask_cli(user_text)
        if reply:
            on_sentence(strip_markdown(reply))
        return reply

    async def _ask_streaming(self, text: str,
                             on_sentence: Callable[[str], None]) -> str:
        chunker = SentenceChunker(on_sentence)
        spoken_any = False
        full: list[str] = []
        self._abandon = False

        await self._client.query(text)
        async for msg in self._client.receive_response():
            # Interrupted: say nothing more, but keep draining this turn's
            # messages so the NEXT turn starts on a clean stream instead of
            # reading this one's leftovers and staying a turn behind forever.
            if self._abandon:
                if isinstance(msg, ResultMessage):
                    break
                continue

            if isinstance(msg, StreamEvent):
                event = msg.event or {}
                etype = event.get("type")
                if etype == "content_block_delta":
                    delta = event.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        piece = delta.get("text") or ""
                        if piece:
                            full.append(piece)
                            spoken_any = True
                            chunker.feed(piece)
                elif etype == "content_block_start":
                    # a tool is being picked up: tell the panel, so a wait on
                    # screen says what is happening instead of nothing
                    block = event.get("content_block") or {}
                    if block.get("type") == "tool_use":
                        signals.set_activity(block.get("name") or "")
                elif etype == "content_block_stop":
                    chunker.flush()

            elif isinstance(msg, AssistantMessage):
                # Fallback only: if nothing streamed, speak the assembled
                # message. Never both, or every reply gets said twice.
                if not spoken_any:
                    for block in msg.content:
                        if isinstance(block, TextBlock) and block.text:
                            full.append(block.text)
                            chunker.feed(block.text)
                    chunker.flush()

            elif isinstance(msg, ResultMessage):
                break

        signals.set_activity("")            # the turn is over, whatever it was doing
        if self._abandon:
            return ""
        chunker.flush()
        return "".join(full).strip()

    def _ask_cli(self, user_text: str) -> str:
        """The old way: a fresh process per turn. Slow, but it always works."""
        args = [self.claude, "-p", user_text,
                "--append-system-prompt", self._system_prompt()]
        if self.model:
            args += ["--model", self.model]
        if self._started_cli:
            args += ["--continue"]      # same conversation, turn after turn
        result = subprocess.run(
            args, cwd=str(self.vault_dir), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=self.timeout,
        )
        self._started_cli = True
        out = (result.stdout or "").strip()
        if not out and result.returncode != 0:
            raise RuntimeError(
                f"claude exited {result.returncode}: {result.stderr[:400]}"
            )
        return out

    # ----------------------------------------------------------- interrupting

    def interrupt(self) -> None:
        """Cut this turn off — you held the key while it was still talking."""
        self._abandon = True
        if self.streaming and self._client is not None:
            try:
                self._run(self._client.interrupt(), timeout=5)
            except Exception:
                pass                    # already finishing, or already gone

    # ----------------------------------------------------------------- health

    def healthy(self) -> bool:
        return shutil.which(self.claude) is not None or Path(self.claude).exists()

    def close(self) -> None:
        if self._client is not None and self._loop is not None:
            try:
                self._run(self._client.disconnect(), timeout=10)
            except Exception:
                pass
        self._client = None
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop = None
