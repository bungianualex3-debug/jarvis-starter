"""Ears — speech to text, on this machine (no cloud, no API key).

Runs on the processor by default and on an NVIDIA card when the install found
one that actually works. Both live in `config.json`; nothing here needs editing.

Worth knowing, because it is most of whatever wait is left: the model and the
device together decide the speed, and the wrong pair is brutal. Measured on one
7.8-second sentence, 2026-08-05: `base` on a processor took 1.9s, `small` 5.9s,
`medium` a miserable 17.2s — while `small` on a graphics card took 0.6s. All of
them got the words right. A heavy model on a processor buys nothing.
"""

import time

import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000


class Ears:
    def __init__(self, cfg):
        stt = cfg.get("stt", {})
        self.model_name = stt.get("model", "small")
        self.device = stt.get("device", "cpu")
        compute_type = stt.get("compute_type", "int8")
        print(f"[ears] loading Whisper '{self.model_name}' on {self.device}...")
        t0 = time.time()
        try:
            self.model = WhisperModel(self.model_name, device=self.device,
                                      compute_type=compute_type)
        except Exception as e:
            if self.device == "cpu":
                raise
            # The card was tested at install, but drivers change and machines
            # get moved. Falling back beats refusing to hear anything at all —
            # and it says so, because a silent downgrade to a 15-seconds-a-turn
            # setup is the kind of thing nobody ever works out on their own.
            print(f"[ears] {self.device} unavailable ({str(e)[:80]}); "
                  f"falling back to the processor.")
            if self.model_name == "medium":
                print("[ears] switching 'medium' to 'small' — medium on a "
                      "processor takes about 17 seconds a sentence.")
                self.model_name = "small"
            self.device = "cpu"
            self.model = WhisperModel(self.model_name, device="cpu",
                                      compute_type="int8")
        print(f"[ears] ready in {time.time() - t0:.1f}s")

    def transcribe(self, audio: np.ndarray):
        """Return (text, detected_language)."""
        # vad_filter drops silence/noise; condition_on_previous_text=False stops
        # the "no no no..." repetition loop Whisper falls into on unclear audio.
        segments, info = self.model.transcribe(
            audio,
            language=None,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = "".join(seg.text for seg in segments).strip()
        return text, info.language

    def healthy(self) -> bool:
        return self.model is not None
