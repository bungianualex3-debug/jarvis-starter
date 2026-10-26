"""Step 3 — where each word really starts, measured on the sound.

Whisper's word times can be a few frames late. Captions and effects that land late read as "delayed", so the
onset of every word an effect hangs on is measured here, on loudness, in the cut take.

  python onsets.py public/edit/body.wav 5.0 7.1 8.7 ...   (rough times, in seconds of the cut take)

For each rough time it prints the first moment within ±0.4 s where loudness crosses -30 dBFS after a quieter
stretch, i.e. the attack of the word. Put those numbers in timing.json.
"""
import sys, wave
import numpy as np

w = wave.open(sys.argv[1])
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels()).astype(np.float32).mean(1)
SR = w.getframerate()
hop = int(0.01 * SR)
db = np.array([20 * np.log10(np.sqrt((x[i:i + hop] ** 2).mean()) / 32768 + 1e-9) for i in range(0, len(x) - hop, hop)])
for rough in map(float, sys.argv[2:]):
    lo, hi = max(1, int((rough - 0.4) * 100)), min(len(db) - 1, int((rough + 0.4) * 100))
    hit = next((i for i in range(lo, hi) if db[i] > -30 and db[i - 1] <= -30), None)
    print(rough, "->", round(hit / 100, 3) if hit else "no attack found nearby")
