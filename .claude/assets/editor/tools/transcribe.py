"""Step 1 — what was said, and when.

Splits the take on silences first and transcribes each spoken stretch on its own. Transcribing a long take
in one pass makes Whisper loop on the pauses (it repeats the last line for minutes); short stretches don't.

  python transcribe.py <video> [--lang en] [--model large-v3-turbo] [--out speech.json]

Writes speech.json: [{i, a, b, text, words:[[word, start, end], ...]}] in source seconds.
Needs: ffmpeg on PATH, `pip install faster-whisper`.
"""
import argparse, json, re, subprocess, sys, tempfile, os

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--lang", default=None, help="language code; leave empty to auto-detect")
ap.add_argument("--model", default="large-v3-turbo")
ap.add_argument("--out", default="speech.json")
ap.add_argument("--noise", default="-38dB", help="silence threshold")
ap.add_argument("--gap", type=float, default=0.35, help="shortest pause that splits two stretches, in seconds")
args = ap.parse_args()
sys.stdout.reconfigure(encoding="utf-8")

tmp = tempfile.mkdtemp()
wav = os.path.join(tmp, "a.wav")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", args.video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
                           capture_output=True, text=True).stdout)
log = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=noise={args.noise}:d={args.gap}", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
speech, prev = [], 0.0
for s, e in zip(st, en + [dur] * (len(st) - len(en))):
    if s - prev > 0.15:
        speech.append((prev, s))
    prev = e
if dur - prev > 0.15:
    speech.append((prev, dur))

from faster_whisper import WhisperModel

try:
    model = WhisperModel(args.model, device="cuda", compute_type="float16")
except Exception:
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

out = []
for i, (a, b) in enumerate(speech):
    a0, b0 = max(0.0, a - 0.1), b + 0.1
    part = os.path.join(tmp, "p.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a0), "-to", str(b0), "-i", wav,
                    "-af", "apad=pad_dur=0.5", part], check=True)
    segs, _ = model.transcribe(part, language=args.lang, word_timestamps=True, condition_on_previous_text=False)
    words = [[w.word.strip(), round(a0 + w.start, 3), round(a0 + w.end, 3)] for s in segs for w in (s.words or [])]
    text = " ".join(w[0] for w in words)
    out.append({"i": i, "a": round(a, 3), "b": round(b, 3), "text": text, "words": words})
    print(f"{i:3d} {a:7.2f}-{b:7.2f} ({b - a:4.1f}s) {text}")
json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("->", args.out)
