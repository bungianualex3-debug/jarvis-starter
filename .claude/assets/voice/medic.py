"""Medic — the self-repair ladder.

Decided safety posture: safe, reversible fixes run automatically; anything that
would edit the assistant's own code is ESCALATED for diagnosis, never applied
blind. The ladder on any fault:
  1. detect + log
  2. safe auto-fix only (restart a component, reinit the voice, etc.)
  3. escalate to Claude to DIAGNOSE (propose, never rewrite code itself)
  4. report to the owner + leave a note for the humans who built it
"""

import datetime
import subprocess
from pathlib import Path


class Medic:
    def __init__(self, cfg, box_dir: Path, brain=None):
        self.cfg = cfg
        self.box_dir = box_dir
        self.brain = brain
        self.log = box_dir / "medic.log"
        self.report = box_dir / "medic-report.txt"

    def _stamp(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write(self, path: Path, msg: str):
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def _log_msg(self, msg: str):
        self._write(self.log, f"[{self._stamp()}] {msg}")

    def health_report(self, components: dict) -> dict:
        return {name: bool(c.healthy()) for name, c in components.items()}

    def handle(self, exc: Exception, component: str, components: dict) -> str:
        self._log_msg(f"FAULT in {component}: {exc!r}")
        # Tier 2 — safe auto-fix only
        if self.try_safe_fix(component, components):
            self._log_msg(f"recovered {component} with a safe fix")
            return "recovered"
        # Tier 3 — escalate to Claude for a diagnosis (no code changes)
        diagnosis = self.escalate(exc, component)
        # Tier 4 — report to owner + leave a note for the builders
        self.report_owner(exc, component, diagnosis)
        return "escalated"

    def try_safe_fix(self, component: str, components: dict) -> bool:
        """Only reversible, non-destructive operations. Never edits code."""
        comp = components.get(component)
        if comp is None:
            return False
        try:
            if component == "mouth" and hasattr(comp, "_init_sapi"):
                comp.use_piper = comp.piper_exe.exists() and comp.model.exists()
                if not comp.use_piper:
                    comp._init_sapi()
                return comp.healthy()
            # For ears/brain, re-checking health is the safe extent of auto-repair.
            return comp.healthy()
        except Exception as e:
            self._log_msg(f"safe fix raised: {e}")
            return False

    def escalate(self, exc: Exception, component: str) -> str:
        """Ask Claude to diagnose only. Runs isolated — never touches the live
        conversation, and explicitly instructed not to rewrite code."""
        claude = getattr(self.brain, "claude", "claude") if self.brain else "claude"
        prompt = (
            "You are a support engineer for a local voice assistant. A component "
            f"named '{component}' just failed. In 3-4 short sentences, give the "
            "most likely cause and a suggested fix. Do NOT rewrite any code — "
            f"diagnose only.\n\nError: {exc!r}\n\nRecent log:\n{self._tail(40)}"
        )
        try:
            r = subprocess.run(
                [claude, "-p", prompt], cwd=str(self.box_dir),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=90,
            )
            self._log_msg("escalated to Claude for diagnosis")
            return (r.stdout or "").strip()
        except Exception as e:
            self._log_msg(f"escalation failed: {e}")
            return ""

    def report_owner(self, exc: Exception, component: str, diagnosis: str):
        text = (
            f"[{self._stamp()}] Something went wrong in the {component} and I "
            "couldn't fix it safely on my own.\n"
            f"Error: {exc!r}\n\n"
            f"Diagnosis:\n{diagnosis or '(none available)'}\n\n"
            "No code was changed automatically — this is left for a human to review."
        )
        self._write(self.report, text + "\n" + "-" * 50)
        print(f"\n[medic] {text}\n")

    def _tail(self, n: int) -> str:
        try:
            return "\n".join(self.log.read_text(encoding="utf-8").splitlines()[-n:])
        except Exception:
            return ""
