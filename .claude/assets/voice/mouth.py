"""Mouth — text to speech, a sentence at a time, cancellable mid-word.

Three rungs, best first, each one catching the one above it:

    Kokoro (only on a machine with a working graphics card)
      -> Piper (a real neural voice, offline, free — the floor everywhere)
        -> Windows SAPI via pyttsx3, so it can always speak somehow.

Kokoro runs INSIDE this process rather than as a separate server. That is
deliberate: no second thing to start, no port to collide with whatever else is
already listening on this machine, and nothing extra for the launcher to wait
for. It costs a torch install, which is why it is only offered to machines that
tested clean on CUDA — on a processor it is roughly ten times slower than the
speech is long, which is worse than no Kokoro at all.

CRITICAL pipeline shape: synthesis and playback are a TWO-STAGE pipeline with
two queues, so the NEXT sentence is being made into audio while the current one
is still playing:

    say(text) -> [synth_q] -> synth thread -> [play_q] -> play thread -> speakers

A simpler one-queue loop that synthesises a sentence and then plays it, over and
over, leaves a real audible gap at every sentence boundary — the voice keeps
stopping to think. Two stages is what makes streamed speech sound continuous.

`say()` returns immediately. That is the other half of the point: the brain can
hand over sentence one and carry straight on writing sentence two, instead of
standing still while the speakers catch up.
"""

from __future__ import annotations

import queue
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

import signals

PLAY_BLOCK = 1024          # frames per write; small enough to cut in ~50ms
DRAIN_GRACE = 0.35         # keep the output device open this long between runs
KOKORO_RATE = 24000        # kokoro always returns 24 kHz mono float

_STOP = object()


class Mouth:
    def __init__(self, cfg, box_dir: Path):
        tts = cfg.get("tts", {})
        self.box_dir = box_dir
        self.piper_exe = box_dir / ".venv" / "Scripts" / "piper.exe"
        self.model = box_dir / tts.get("piper_model", "")
        self.use_piper = self.piper_exe.exists() and self.model.exists()
        self._sapi = None

        # Kokoro is opt-in from config and is loaded lazily on its own thread,
        # so a slow first model load overlaps the rest of the startup instead
        # of standing in front of it.
        self.kokoro_voice = tts.get("kokoro_voice", "bm_lewis")
        self.kokoro_device = tts.get("kokoro_device", "cuda")
        self.use_kokoro = (tts.get("engine") or "piper").strip().lower() == "kokoro"
        self._kokoro = None
        self._kokoro_lock = threading.Lock()
        self._kokoro_failed = False

        self._synth_q: queue.Queue = queue.Queue()
        self._play_q: queue.Queue = queue.Queue()
        self._generation = 0
        self._gen_lock = threading.Lock()
        self._playing = threading.Event()
        self._pending = 0                    # sentences in flight
        self._pending_lock = threading.Lock()
        self._stream: sd.OutputStream | None = None
        self._stream_lock = threading.Lock()
        self._closed = False

        if self.use_kokoro:
            print(f"[mouth] Kokoro voice: {self.kokoro_voice} on {self.kokoro_device}")
            threading.Thread(target=self._load_kokoro, daemon=True,
                             name="mouth-warm").start()
        elif self.use_piper:
            print(f"[mouth] Piper voice: {self.model.name}")
        else:
            print("[mouth] Piper voice not found — falling back to system voice.")
            self._init_sapi()

        threading.Thread(target=self._synth_loop, daemon=True,
                         name="mouth-synth").start()
        threading.Thread(target=self._play_loop, daemon=True,
                         name="mouth-play").start()

    # ------------------------------------------------------------------ public

    @property
    def is_speaking(self) -> bool:
        return self._playing.is_set() or self._count() > 0

    def say(self, text: str) -> None:
        """Queue a sentence. Returns immediately — it does not wait for audio."""
        text = (text or "").strip()
        if not text:
            return
        self._bump(+1)
        self._synth_q.put((self._current_gen(), text))

    def interrupt(self) -> None:
        """Stop talking right now and forget everything still queued.

        Bumping the generation is what makes this safe: work already in flight
        carries the old number, so it is discarded when it surfaces instead of
        being played after you have already started saying something else.
        """
        with self._gen_lock:
            self._generation += 1
        self._drain(self._synth_q)
        self._drain(self._play_q)
        with self._pending_lock:
            self._pending = 0
        with self._stream_lock:
            if self._stream is not None:
                try:
                    self._stream.abort()
                except Exception:
                    pass
        self._playing.clear()

    def wait_idle(self, timeout: float | None = None) -> None:
        started = time.time()
        while self.is_speaking:
            if timeout is not None and time.time() - started > timeout:
                return
            time.sleep(0.02)

    def healthy(self) -> bool:
        return self.use_kokoro or self.use_piper or self._sapi is not None

    def close(self) -> None:
        self._closed = True
        self.interrupt()
        self._synth_q.put(_STOP)
        self._play_q.put(_STOP)

    # ----------------------------------------------------------------- helpers

    def _count(self) -> int:
        with self._pending_lock:
            return self._pending

    def _bump(self, delta: int) -> None:
        with self._pending_lock:
            self._pending = max(0, self._pending + delta)

    def _current_gen(self) -> int:
        with self._gen_lock:
            return self._generation

    @staticmethod
    def _drain(q: queue.Queue) -> None:
        try:
            while True:
                q.get_nowait()
        except queue.Empty:
            pass

    def _load_kokoro(self):
        """Build the Kokoro pipeline once. Both the warm-up thread and the
        synth thread come through here, so the lock is what stops the first
        sentence ever seeing a half-built model."""
        with self._kokoro_lock:
            if self._kokoro is not None or self._kokoro_failed:
                return self._kokoro
            try:
                from kokoro import KPipeline
                # the voice name's first letter IS its language: 'b' British,
                # 'a' American. Handing the pipeline the wrong one mispronounces
                # everything while looking like it worked.
                lang = "b" if self.kokoro_voice.startswith("b") else "a"
                self._kokoro = KPipeline(lang_code=lang, device=self.kokoro_device)
                print("[mouth] Kokoro ready.")
            except Exception as e:
                print(f"[mouth] Kokoro unavailable ({e}) — using the Piper voice.")
                self._kokoro_failed = True
                self.use_kokoro = False
            return self._kokoro

    def _init_sapi(self):
        try:
            import pyttsx3
            self._sapi = pyttsx3.init()
        except Exception as e:
            print(f"[mouth] no system voice available: {e}")
            self._sapi = None

    # ------------------------------------------------------------ stage 1: TTS

    def _synth_loop(self) -> None:
        while not self._closed:
            item = self._synth_q.get()
            if item is _STOP:
                break
            gen, text = item
            if gen != self._current_gen():
                self._bump(-1)
                continue
            try:
                audio, rate = self._synthesize(text)
            except Exception as e:
                print(f"[mouth] voice failed ({e}); using system voice.")
                self.use_kokoro = False
                self.use_piper = False
                self._init_sapi()
                audio, rate = None, 0
            if audio is None or audio.size == 0 or gen != self._current_gen():
                if audio is None and gen == self._current_gen():
                    self._say_sapi(text)     # nothing to stream; speak it plainly
                self._bump(-1)
                continue
            # the text rides along with its audio so the caption can appear at
            # the exact moment this sentence starts sounding, not before
            self._play_q.put((gen, audio, rate, text))

    def _synth_kokoro(self, text: str):
        """Kokoro yields float chunks; we join them and convert once."""
        pipe = self._load_kokoro()
        if pipe is None:
            return None, 0
        chunks = []
        for result in pipe(text, voice=self.kokoro_voice, speed=1.0):
            audio = getattr(result, "audio", None)
            if audio is None:
                continue
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            chunks.append(np.asarray(audio, dtype="float32").reshape(-1))
        if not chunks:
            return None, 0
        wav = np.clip(np.concatenate(chunks), -1.0, 1.0)
        return (wav * 32767.0).astype(np.int16), KOKORO_RATE

    def _synthesize(self, text: str):
        """The one seam for the voice backend. Piper writes a wav; we read it."""
        if self.use_kokoro:
            try:
                audio, rate = self._synth_kokoro(text)
                if audio is not None and audio.size:
                    return audio, rate
            except Exception as e:
                print(f"[mouth] Kokoro failed ({e}) — dropping to the Piper voice.")
            # demote once, rather than paying the same failure every sentence
            self.use_kokoro = False

        if not self.use_piper:
            return None, 0
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name
        try:
            subprocess.run(
                [str(self.piper_exe), "-m", str(self.model), "-f", wav_path],
                input=text, text=True, encoding="utf-8",
                capture_output=True, timeout=60, check=True,
            )
            with wave.open(wav_path, "rb") as w:
                rate = w.getframerate()
                frames = w.readframes(w.getnframes())
            return np.frombuffer(frames, dtype=np.int16), rate
        finally:
            Path(wav_path).unlink(missing_ok=True)

    # -------------------------------------------------------- stage 2: playback

    def _play_loop(self) -> None:
        open_rate = 0
        last_audio = 0.0
        announced_idle = True

        while not self._closed:
            try:
                item = self._play_q.get(timeout=0.1)
            except queue.Empty:
                # nothing playing: retire the device once this run has drained,
                # so we aren't holding the speakers open all day
                if self._stream is not None and time.time() - last_audio > DRAIN_GRACE:
                    self._close_stream()
                    open_rate = 0
                if not announced_idle and self._count() == 0:
                    self._playing.clear()
                    announced_idle = True
                continue

            if item is _STOP:
                break
            gen, audio, rate, text = item
            if gen != self._current_gen():
                self._bump(-1)
                continue

            if self._stream is None or rate != open_rate:
                self._close_stream()
                try:
                    stream = sd.OutputStream(samplerate=rate, channels=1,
                                             dtype="int16", blocksize=PLAY_BLOCK)
                    stream.start()
                except Exception as e:
                    print(f"[mouth] cannot open speakers: {e}")
                    self._bump(-1)
                    continue
                with self._stream_lock:
                    self._stream = stream
                open_rate = rate

            self._playing.set()
            announced_idle = False
            # true length of this sentence's audio, so the face can sweep the
            # caption by real playback time instead of guessing from word count
            signals.set_state(signals.SPEAKING)
            signals.set_caption(text, audio.size / float(rate or 1))

            for start in range(0, audio.size, PLAY_BLOCK):
                if gen != self._current_gen():
                    break                      # interrupted mid-sentence
                block = audio[start:start + PLAY_BLOCK]
                try:
                    with self._stream_lock:
                        stream = self._stream
                    if stream is None:
                        break
                    stream.write(block)
                except Exception:
                    break
                norm = block.astype("float32") / 32768.0
                signals.set_signal(float(np.abs(norm).max()),
                                   signals.envelope(norm))
                last_audio = time.time()

            signals.set_signal(0.0, [0.0] * signals.WAVE_POINTS)
            self._bump(-1)

        self._close_stream()

    def _close_stream(self) -> None:
        with self._stream_lock:
            stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    # ----------------------------------------------------------------- fallback

    def _say_sapi(self, text: str):
        """Blocking, and it cannot be cut off mid-word. It is the last resort:
        an assistant that speaks clumsily still beats one that cannot speak."""
        if self._sapi is None:
            self._init_sapi()
        if self._sapi is None:
            print(f"[mouth] (silent) {text}")
            return
        signals.set_state(signals.SPEAKING)
        signals.set_caption(text, 0.0)
        self._sapi.say(text)
        self._sapi.runAndWait()
