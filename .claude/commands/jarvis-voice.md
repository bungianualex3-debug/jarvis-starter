---
description: Give my assistant a voice — hold a key, talk to it, hear it answer.
---

# Give it a voice

It remembers, and it has a face. Now it listens and talks back.

Everything runs on this machine: the hearing, the speaking, and the thinking. **No API key and nothing metered** — the thinking is the Claude they already pay for, driven exactly as if they'd typed it.

Do not explain the plan. Start.

---

## Stage 0 — Refuse to start in the wrong place

Three checks, in order. Any failure: say it in one line and stop.

1. **`CLAUDE.md` in the current folder.** No file, no vault — tell them to run `/jarvis` first.
2. **No `CLAUDE.md` in any folder above.** If there is one, Claude Code reads it on the way up, so the voice would answer as *that* person, with their identity and their files. **Name the file and stop.** This is the fault that looks completely normal while being completely wrong.
3. **Python 3.10 or newer.** If it's missing, point them at python.org and stop — and tell them to tick **"Add Python to PATH"** in the installer, because that is the step everybody misses.

---

## Stage 1 — Read, don't ask

From `CLAUDE.md` and `VAULT-INDEX.md`, take the **assistant's name** and the **language**. Never ask for either — you have them, and asking is a public admission that the memory doesn't work.

---

## Stage 2 — Look at the machine before offering anything

**Do this before the questions, and tell them what you found.** Offering someone a model their laptop will choke on, and letting them discover it thirty seconds into their first conversation, is how a free thing gets remembered as broken.

Find out, using whatever works on their OS:

- **Graphics card** — `nvidia-smi` on Windows/Linux; on a Mac, whether it's Apple silicon.
- **Memory** — total RAM.
- **Processor** — core count.

### The principle: give them the best their machine can actually run

Not the safest, not the lightest — **the best it can carry.** A voice assistant that mishears you, or makes you wait, doesn't read as modest. It reads as fake, and people close it and never come back. So find out what this machine can do and use it.

### Check the card isn't already busy

Before deciding, look at what's on the card: `nvidia-smi --query-gpu=memory.total,memory.used,utilization.gpu --format=csv`.

A card with **less than ~2 GB free**, or already running hot, is a card that is doing something else — another assistant, a game, a model someone is training. Sharing it is the documented way this breaks: two things fighting for one card ends with transcription timing out, so it stops hearing them altogether, and the whole machine drags. That failure looks like a broken install, not a busy card, and nobody diagnoses it. On a card like that, use the CPU column and **say why in one line** — the card is in use, not missing.

### Test the graphics card, don't guess about it

If the card is free, **find out whether CUDA actually works** rather than assuming either way. After the environment is installed (Stage 4), run one real transcription on it:

```python
from faster_whisper import WhisperModel
import numpy as np
m = WhisperModel("small", device="cuda", compute_type="float16")
list(m.transcribe(np.zeros(16000, dtype="float32"))[0])
```

If it raises, CUDA isn't usable on this machine — say so in one line and use the CPU column. If it returns, the card works and you use it. This takes about a minute and it replaces a guess with a fact.

### Then pick the model, and say the tier out loud in one plain sentence

| What they have | Whisper model | Device |
|---|---|---|
| Working NVIDIA card | `small` | `cuda` |
| Working NVIDIA card, 8 GB+ VRAM, and they want the best accuracy | `medium` | `cuda` |
| No usable GPU, 16 GB+ RAM and 8+ cores | `small` | `cpu` |
| No usable GPU, anything less | `base` | `cpu` |

**Never `medium` on a CPU.** Measured on a real machine (RTX 3070, 32 GB, 8 cores) on 2026-08-05, transcribing one 7.8-second sentence:

| | load | transcribe |
|---|---|---|
| `base` on CPU | 1.3s | **1.9s** |
| `small` on CPU | 1.7s | **5.9s** |
| `medium` on CPU | 4.5s | **17.2s** |
| `medium` on CUDA | 2.8s | **1.0s** |
| `small` on CUDA | 1.1s | **0.6s** |

All five got the sentence right. `medium` on a CPU buys nothing and costs fifteen seconds a turn.

The old rule picked `medium` *because* the machine had a good card, then ran it on the processor anyway — so the better the hardware, the slower the assistant. That is the bug this table exists to prevent. If the card works, use the card. If it doesn't, use a model the processor can actually carry.

Whatever you choose, tell them the two lines in `voice/config.json` that change it (`"model"` and `"device"`), so it's theirs to adjust.

---

## Stage 3 — Two questions, one at a time

1. **The talk key.** Hold it to speak, let go when done — nothing is recorded while it's up. Offer **right Ctrl** as the default and say why it's a good one: it's under your right hand and nothing else uses it. Other options: right Alt, right Shift, Caps Lock, F8, F9, Pause.

2. **The voice.** Offer only what suits the machine and their language, and describe them by sound rather than by filename:

   | Voice | Sounds like | Notes |
   |---|---|---|
   | `en_GB-alan-medium` | British man, even and calm | good default anywhere |
   | `en_US-ryan-medium` | American man, warmer | good default anywhere |
   | `en_US-ryan-high` | the same man, noticeably better | heavier — only offer on a strong machine |
   | `en_US-amy-medium` | American woman | |
   | `ro_RO-mihai-medium` | Romanian man | the only Romanian voice there is |

   If their language has no voice in this list, say so plainly rather than giving them an English voice reading their language without warning — that sounds broken, and they'll blame the whole thing.

Then build it. No confirmation step.

---

## Stage 4 — Install

Everything goes in a **`voice` folder inside the vault**. Nothing is installed system-wide and nothing touches anything they already have.

1. **Copy** every file from `.claude/assets/voice/` into `voice/`.
2. **Make a virtual environment** inside it (`python -m venv .venv`) and install `requirements.txt` into it. Say up front this takes a few minutes and downloads a few hundred megabytes — silence during a long download reads as a hang.
3. **Write `voice/config.json`** from `config.template.json`: their language, their key, the model tier you chose in Stage 2, and the voice they picked.
4. **Download the voice** into `voice/voices/` — two files per voice, the model and its `.json`:

   ```
   https://huggingface.co/rhasspy/piper-voices/resolve/main/<path><name>.onnx
   https://huggingface.co/rhasspy/piper-voices/resolve/main/<path><name>.onnx.json
   ```

   | name | path |
   |---|---|
   | `en_GB-alan-medium` | `en/en_GB/alan/medium/` |
   | `en_US-ryan-medium` | `en/en_US/ryan/medium/` |
   | `en_US-ryan-high` | `en/en_US/ryan/high/` |
   | `en_US-amy-medium` | `en/en_US/amy/medium/` |
   | `ro_RO-mihai-medium` | `ro/ro_RO/mihai/medium/` |

   **The voice files must land in `voice/voices/`, and `piper_model` must be a path relative to the `voice` folder** — `voices/<name>.onnx`, nothing else. Never an absolute path. Never a copy of one already sitting somewhere else on this machine.

   **A vault has to be complete by itself.** Download the voice even if a copy already exists elsewhere on the machine — a vault that points at a file it doesn't own breaks the day that folder moves, and breaks immediately for anyone else.

   **If they explicitly tell you not to download anything** — testing, metered connection, no patience — then reuse a local copy, but **say plainly what it costs**: this vault now only works on this computer, and copying it anywhere else will leave it mute. Write that into the vault index next to the voice entry, in those words. A limitation someone chose is fine. A limitation nobody wrote down becomes a mystery three weeks later.

   **Then check the file is real.** A failed download can save a few-hundred-byte error page under the right filename, and the first symptom is a crash much later that looks like something else entirely. Anything under a megabyte is not a voice — delete it and try again.

**Don't edit the Python.** It's tested. Everything meant to change lives in `config.json`.

---

## Stage 5 — Put it behind the button, BEFORE you let them hear it

Do this now, while nothing works yet. **Once they hear it answer, this step gets skipped** — it has been, in a real run — because a talking assistant feels like the finish line and wiring a batch file doesn't. So the wiring comes first, and the first thing they ever hear comes *out of the button*.

The launcher files from `/jarvis-interface` each have a marked, empty voice section. Fill them in, so one button starts the whole thing.

In the **Start** file, replace the voice marker comment with this. It starts the voice, then waits for it to publish the face's live address and points the browser at that instead of at the file on disk:

```
set "FACEURL=%~dp0voice\.bus\face.url"
del "%FACEURL%" >nul 2>nul
start "" /min "%~dp0voice\run.bat"

for /l %%i in (1,1,30) do (
  if exist "%FACEURL%" (
    set /p URL=<"%FACEURL%"
    goto :voice_ready
  )
  "%SystemRoot%\System32\timeout.exe" /t 1 /nobreak >nul
)
echo   The voice didn't come up - opening the face in demo mode.
:voice_ready
```

**Write `timeout` with its full path exactly as above.** Some machines have a GNU `timeout` earlier on PATH (Git for Windows, msys, coreutils). It takes different arguments, so it fails instantly instead of waiting — and then all 30 iterations of this loop fly past in milliseconds, the voice never gets time to start, and the face opens in demo mode looking perfectly healthy. Found on a real clean run, 2026-08-05.

**Do not skip the waiting loop, and do not open the browser before this.** Opened as a `file://` page the interface cannot reach the voice's state — its own `/state` address resolves to nothing on disk, so it runs its demo loop forever and never once reacts to a real voice. It looks alive and is not. That is the single most disappointing way this can fail, because everything appears to work.

In the **Stop** file, add a line that kills only python processes whose command line contains this vault's `voice` folder — never all Python, which would take out anything else they're running.

If they don't have launchers (they skipped `/jarvis-interface`), say so and tell them `run.bat` starts the voice on its own.

---

## Stage 6 — Land it

**Prove the key first, on its own.** `python ptt-test.py` inside `voice`, using their key. It loads nothing — no models, no microphone — so it answers in a second, and if the key works, any later problem is provably somewhere else. Have them hold it a few times and read you the numbers.

**Then the real thing — started with their button, not by you from a terminal.** This is deliberate: it's the only way to find out whether Stage 5 actually worked. **If the voice doesn't come up when they press Start, the wiring is missing — go back and fix it before doing anything else.** Never work around it by launching `run.bat` yourself; that hides the exact fault you're testing for.

Warn them the first run is slow — the hearing model is being downloaded and loaded, once. Then:

- Hold the key, say something, let go. They should see the face **listening**, then **thinking**, then **speaking**, and hear the answer.
- Have them **interrupt it**: hold the key while it's mid-sentence. It stops instantly and starts listening again, because someone who interrupts is about to talk.

If nothing is heard: microphone permission first (Windows: Settings → Privacy & security → Microphone → allow desktop apps), then whether another assistant is already listening on that same key. **Two things on one key both fire.**

### Write it into their vault

Add to `VAULT-INDEX.md`: that the voice lives in `voice/`, which key talks to it, which voice it uses, and that `config.json` is where all of that changes. A couple of sentences. No new note — the index is the home.

Then stop.

---

## Before you say you're done

Hearing it answer feels like the end. It isn't. **Check all six by actually looking — open the folder, read the file. Do not check them from memory of what you intended to do.**

1. `voice/` exists with its own `.venv`.
2. `voice/voices/` contains a file **over a megabyte**, and `config.json`'s `piper_model` reads `voices/<name>.onnx` — **a relative path inside the vault.** If it points anywhere else on the machine, either fix it, or make sure the index says the vault only works on this computer.
3. Both launcher files contain the voice lines you added in Stage 5.
4. They have **held the key and heard it answer**, having started it **with the button**.
5. They have **interrupted it mid-sentence** at least once.

*(4 and 5 are for the person installing it on their own machine. If you are testing a build whose voice path you have already proven on this same code, don't make them do it again — re-running a passed check to tick your own box wastes their time and is its own kind of dishonesty.)*
6. `VAULT-INDEX.md` mentions the voice, the key and where to change it.
7. **The face is LIVE, not in demo mode.** Ask them to look at the corner: if it still says `demo mode` while the voice is running, the Stage 5 wiring didn't take and the interface is animating to nothing. Check `voice/.bus/face.url` exists and that the browser's address starts with `http://127.0.0.1`, not `file:///`.

**2, 3, 6 and 7 are the ones that go missing** — every one of them has been skipped in a real run, and every one of them still leaves an assistant that talks. That's exactly why they need looking at rather than remembering.

---

## Rules while you do all this

- **Copy the Python, don't rewrite it.** Any bug you invent here is one they can't diagnose, in the part that's hardest to debug.
- **Everything in their language** — the questions, the explanations, and the console lines a person actually reads.
- **Never suggest an always-on microphone.** Hold-to-talk is the design: it's visible consent every time, it can't be triggered by a conversation happening near it, and it sidesteps the whole class of bugs where an assistant hears itself.
- **Don't touch anything outside the vault.**
- If `voice/` already exists, **stop and ask** before overwriting.
