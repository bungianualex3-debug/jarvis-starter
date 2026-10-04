"""The voice — your assistant, out loud.

Voice in (Whisper) -> brain (the Claude already on this machine) -> voice out
(Piper), with a self-repair medic wrapping the loop and a small server feeding
the on-screen face.

This folder lives INSIDE the vault. The vault above it is the memory, and the
brain is run from there, so the spoken assistant and the typed one are the same
assistant reading the same boot file.

Hold-to-talk: hold a key (right Ctrl by default, right Option on a Mac), talk,
let go. Nothing is
recorded while the key is up — no always-on microphone. If the key listener
can't start on this machine it falls back to press-Enter, so the assistant
still works rather than refusing to run.

Hold the key again while it's talking to cut it off; it starts listening
straight away, because if you're interrupting you're about to say something.
"""

import json
import queue
import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

import face_server
import ptt
import signals
from stt import Ears, SAMPLE_RATE
from brain import Brain
from mouth import Mouth
from medic import Medic

try:
    import msvcrt                    # Windows only
except ImportError:
    msvcrt = None                    # macOS and Linux: see flush_typed_keys()

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOX = Path(__file__).parent          # the voice folder
VAULT = BOX.parent                   # the memory it belongs to
MIN_RECORDING_SECONDS = 0.3


def load_config() -> dict:
    return json.loads((BOX / "config.json").read_text(encoding="utf-8"))


def inherited_boot_file(start: Path):
    """Find a CLAUDE.md in any folder ABOVE the vault.

    Claude Code walks up the folder tree looking for a boot file. If the vault
    sits inside someone else's project, the assistant silently loads THAT
    project's identity, rules and file access — and looks completely normal
    while doing it. It is the worst kind of fault: it works, convincingly, as
    the wrong person. So we look before we start.

    The vault's own CLAUDE.md is the point and is not what we're looking for —
    hence starting from the vault's parents, not the vault itself.
    """
    for parent in start.parents:
        candidate = parent / "CLAUDE.md"
        if candidate.exists():
            return candidate
    return None


def flush_typed_keys() -> None:
    """Drop keystrokes already sitting in the console, so a stray one typed
    earlier doesn't end the recording the instant it starts."""
    if msvcrt is not None:
        while msvcrt.kbhit():
            msvcrt.getch()
        return
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass                         # no terminal attached; nothing to flush


def record_audio() -> np.ndarray:
    frames = []

    def callback(indata, *_):
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback
    )
    stream.start()
    t0 = time.time()
    flush_typed_keys()
    input("Recording... press Enter to stop.")
    stream.stop()
    stream.close()
    if time.time() - t0 < MIN_RECORDING_SECONDS or not frames:
        return np.zeros((0,), dtype=np.float32)
    return np.concatenate(frames, axis=0).flatten()


def record_while_held(talk) -> np.ndarray:
    """Record for exactly as long as the key is down, publishing the live
    input level so the face reacts while you're still speaking."""
    frames = []

    def callback(indata, *_):
        frames.append(indata.copy())
        block = indata.reshape(-1)
        signals.set_signal(min(1.0, float(np.abs(block).max()) * 3.0),
                           signals.envelope(block))

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback
    ):
        while talk.is_held():
            time.sleep(0.01)

    if not frames:
        return np.zeros((0,), dtype=np.float32)
    audio = np.concatenate(frames, axis=0).flatten()
    if audio.size / SAMPLE_RATE < MIN_RECORDING_SECONDS:
        return np.zeros((0,), dtype=np.float32)   # a tap, not a sentence
    return audio


def watch_for_barge_in(talk, mouth, brain, state: dict, typed_q) -> None:
    """While a turn is running, watch for the talk key going down.

    Holding the key mid-reply means one thing: you want it to stop and you are
    about to say something. So cut BOTH ends — the mouth, which is playing, and
    the brain, which may still be writing. Cutting only the mouth leaves it
    thinking into the void and the next answer arrives late and out of step.

    A typed message arriving mid-reply means the same thing: stop, and answer
    the new one. It stays in the queue; the main loop picks it up next.
    """
    while not state["done"]:
        if talk is not None and talk.is_held():
            state["cut_off"] = True
            mouth.interrupt()
            brain.interrupt()
            return
        if not typed_q.empty():
            state["typed_in"] = True
            mouth.interrupt()
            brain.interrupt()
            return
        time.sleep(0.02)


def start_typing_in_the_console(typed_q: "queue.Queue") -> None:
    """Let someone type into the console window as well as hold the key.

    Without this, once hold-to-talk starts the console is deaf: anything typed
    there goes nowhere, which reads as "it's broken" rather than "that isn't an
    input". Both routes feed the same queue, so a typed line and a spoken one
    are the same thing by the time the loop sees them.

    Runs as a daemon on its own thread — if there is no console attached (the
    launcher starts the voice minimised) the read simply fails and we move on.
    """
    def pump():
        while True:
            try:
                line = sys.stdin.readline()
            except Exception:
                return                       # no console, or it went away
            if not line:
                return                       # stdin closed
            line = line.strip()
            if line:
                typed_q.put(line)

    threading.Thread(target=pump, daemon=True, name="console-typing").start()


def start_push_to_talk(cfg):
    """Returns a started PushToTalk, or None if this machine can't do it."""
    key = cfg.get("ptt", {}).get("key") or ptt.DEFAULT_KEY
    if not ptt.AVAILABLE:
        print("[ptt] key listener unavailable — using press-Enter instead.")
        return None
    try:
        talk = ptt.PushToTalk(key)
        talk.start()
        print(f"[ptt] hold {talk.key_name.replace('_', ' ')} to talk")
        return talk
    except Exception as e:
        print(f"[ptt] could not start the key listener ({e}) — using press-Enter.")
        return None


def main():
    cfg = load_config()
    # optional: `python main.py f9` overrides the talk key for one run, so the
    # box can be tested without fighting another assistant on the same key
    if len(sys.argv) > 1:
        cfg.setdefault("ptt", {})["key"] = sys.argv[1]

    inherited = inherited_boot_file(VAULT)
    if inherited is not None and not cfg.get("allow_inherited_boot", False):
        print(f"\n  Stopping: there is a boot file above this folder.\n"
              f"    {inherited}\n\n"
              f"  Claude Code reads that on the way up, so this assistant would\n"
              f"  start as whoever that file describes — with their identity,\n"
              f"  their rules and their files — instead of as itself.\n\n"
              f"  Move this folder somewhere that has no CLAUDE.md above it.\n"
              f"  (If this really is your own setup and you meant it, set\n"
              f"   \"allow_inherited_boot\": true in config.json.)\n")
        return
    name = cfg.get("assistant_name", "Assistant")
    owner = cfg.get("owner_name", "there")

    ears = Ears(cfg)
    brain = Brain(cfg, VAULT)        # thinks from inside the memory
    mouth = Mouth(cfg, BOX)
    components = {"ears": ears, "brain": brain, "mouth": mouth}
    medic = Medic(cfg, BOX, brain)

    # open one live thinking session for the whole run. Without this every
    # single thing you say pays for a brand new process — measured at 4.8s
    # before a microphone is even involved. Falls back on its own if it can't.
    brain.start()

    print("[health]", medic.health_report(components))

    # --- the face -------------------------------------------------------
    face_cfg = cfg.get("face", {})
    bus_file = BOX / ".bus" / "state.json"
    signals.configure(bus_file)
    web_dir = Path(face_cfg.get("web_dir") or VAULT)   # interface.html lives there
    # typed messages from the face land here and are picked up by the main loop,
    # so someone who can't or won't speak still has a way in
    typed_q: queue.Queue = queue.Queue()
    server, url = face_server.start(web_dir, bus_file,
                                    int(face_cfg.get("port", face_server.DEFAULT_PORT)),
                                    on_message=typed_q.put)
    url_file = BOX / ".bus" / "face.url"
    if url:
        print(f"[face] {url}")
        # Leave the address where the launcher can find it. This is what makes
        # the face go LIVE: opened as a file:// page, its own "/state" address
        # resolves to nothing on disk, so it animates a demo loop forever and
        # never once reacts to your voice. Served from here it is same-origin
        # and simply works — and the port can be changed in config.json without
        # the launcher having to know or parse anything.
        try:
            url_file.parent.mkdir(parents=True, exist_ok=True)
            url_file.write_text(url, encoding="utf-8")
        except Exception:
            pass                        # the launcher falls back to the file
    else:
        url_file.unlink(missing_ok=True)   # stale address is worse than none

    talk = start_push_to_talk(cfg)
    if talk is not None:
        # only when hold-to-talk owns the key: the press-Enter fallback below
        # already reads the console itself, and two readers would fight
        start_typing_in_the_console(typed_q)
        how = f"Hold {talk.key_name.replace('_', ' ')} and talk to me whenever you're ready."
    else:
        how = "Press Enter and talk to me whenever you're ready."

    greeting = f"Hey {owner}, {name} is online. {how}"
    print(f"\n{name}: {greeting}\n")
    try:
        mouth.say(greeting)
        # The first question of a session is always the slowest, so pay that
        # cost now, out loud, while the greeting is still playing. By the time
        # anyone has finished listening to it, the session is already warm.
        threading.Thread(target=brain.warmup, daemon=True).start()

        # The greeting is spoken outside any turn, so nothing after it puts
        # the face back to rest: it stayed in its speaking state until the
        # first real exchange. Wait for the audio to end, then settle.
        def rest_after_greeting():
            time.sleep(0.5)                 # let the first sentence reach the speakers
            mouth.wait_idle(timeout=180)    # a first Kokoro sentence can be slow
            signals.settle()
        threading.Thread(target=rest_after_greeting, daemon=True).start()
    except Exception as e:
        medic.handle(e, "mouth", components)

    if talk is not None:
        print("(Ctrl+C to quit)")

    carry_audio = None
    try:
        while True:
            try:
                typed = None
                if carry_audio is not None:
                    audio, carry_audio = carry_audio, None   # from a barge-in
                else:
                    # Someone typing into the face jumps the queue: there is
                    # nothing to record and nothing to transcribe, so it goes
                    # straight to thinking. Checked before the key wait so a
                    # typed line never sits there for half a second first.
                    try:
                        typed = typed_q.get_nowait()
                    except queue.Empty:
                        typed = None

                    if typed is None:
                        if talk is not None:
                            # short timeout so Ctrl+C is never swallowed
                            if not talk.wait_for_press(timeout=0.5):
                                continue
                            signals.set_state(signals.LISTENING)
                            audio = record_while_held(talk)
                        else:
                            cmd = input("Press Enter to talk (or type 'quit'): ")
                            if cmd.strip().lower() == "quit":
                                break
                            signals.set_state(signals.LISTENING)
                            audio = record_audio()

                if typed is not None:
                    text, lang = typed, "typed"
                    signals.set_state(signals.THINKING)
                else:
                    if audio.size == 0:
                        print("(nothing heard — try again)")
                        signals.set_state(signals.IDLE)
                        continue
                    signals.set_state(signals.THINKING)
                    text, lang = ears.transcribe(audio)

                print(f"You [{lang}]: {text}")
                if not text:
                    signals.set_state(signals.IDLE)
                    continue
                signals.push_conversation("user", text)
                # Speak each sentence the moment it exists rather than waiting
                # for the whole reply to be written. Most of the old wait was
                # silence with a finished thought sitting there unspoken.
                state = {"done": False, "cut_off": False, "typed_in": False}
                watcher = threading.Thread(
                    target=watch_for_barge_in,
                    args=(talk, mouth, brain, state, typed_q), daemon=True,
                )
                watcher.start()
                try:
                    def speak(sentence: str) -> None:
                        print(f"{name}: {sentence}")
                        signals.push_conversation("assistant", sentence)
                        mouth.say(sentence)

                    brain.ask(text, speak)
                    # the reply is written; the speakers are still catching up
                    while (mouth.is_speaking and not state["cut_off"]
                           and not state["typed_in"]):
                        time.sleep(0.02)
                finally:
                    state["done"] = True
                signals.clear_caption()
                cut_off = state["cut_off"]

                if cut_off:
                    # you held the key to shut it up — so you're about to talk.
                    # Record straight away instead of making you press again.
                    print("(interrupted)")
                    talk.clear_press()
                    signals.set_state(signals.LISTENING)
                    carry_audio = record_while_held(talk)
                elif state["typed_in"]:
                    # a typed message cut it off; the loop reads it next
                    print("(interrupted by a typed message)")
                    signals.set_state(signals.THINKING)
                else:
                    signals.set_state(signals.IDLE)
            except Exception as e:
                signals.set_state(signals.IDLE)
                medic.handle(e, "loop", components)
    except KeyboardInterrupt:
        print()
    finally:
        if talk is not None:
            talk.stop()
        mouth.close()
        brain.close()
        signals.reset()
        (BOX / ".bus" / "face.url").unlink(missing_ok=True)
        if server is not None:
            server.shutdown()

    print(f"{name} signing off.")


if __name__ == "__main__":
    main()
