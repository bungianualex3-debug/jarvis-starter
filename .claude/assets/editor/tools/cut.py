"""Step 2 — the cut, frame-exact.

Takes the list of keeps you decided on after reading speech.json and builds one continuous take:
  body.mp4  (video, 1080x1920, 30 fps, no audio)   body.wav  (48 kHz stereo)   timeline.json

  python cut.py <video> cuts.json [--vf "<ffmpeg filter>"] [--outdir public/edit]

cuts.json: [["hook", 1.2, 5.75], ["Glass Shatter", 12.01, 13.89], ...]   (name, start, end in source seconds)
Names matter: name each keep after what is said in it, and the composition can find it by name later.

Why frame-exact: every keep is snapped to a 1/30 s boundary and encoded with an exact frame count, and the audio
is cut from one WAV with 4 ms fades and joined in memory. Joining AAC clips instead leaves tiny gaps at every
join, and over twenty joins the picture drifts away from the voice.

--vf defaults to a centre crop to 9:16. Phone footage that is already vertical needs only the scale; add boxblur
overlays here for anything on screen that should not be readable (other monitors, other faces).
"""
import argparse, json, os, subprocess, wave
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("cuts")
ap.add_argument("--vf", default="crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=1080:1920,fps=30")
ap.add_argument("--outdir", default="public/edit")
args = ap.parse_args()

FPS, SR = 30, 48000
os.makedirs(args.outdir, exist_ok=True)
work = os.path.join(args.outdir, "_parts")
os.makedirs(work, exist_ok=True)
q = lambda t: round(t * FPS) / FPS
cuts = [(n, q(a), q(b)) for n, a, b in json.load(open(args.cuts, encoding="utf-8"))]

full = os.path.join(work, "full.wav")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", args.video, "-vn", "-ac", "2", "-ar", str(SR), full], check=True)
w = wave.open(full)
A = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32)
F = int(0.004 * SR)
fin = np.linspace(0, 1, F)[:, None]

parts, files, tl, t = [], [], [], 0.0
for i, (n, a, b) in enumerate(cuts):
    p = A[int(round(a * SR)):int(round(b * SR))].copy()
    p[:F] *= fin
    p[-F:] *= fin[::-1]
    parts.append(p)
    f = os.path.join(work, f"v{i:02d}.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.4f}", "-i", args.video, "-vf", args.vf,
                    "-frames:v", str(round((b - a) * FPS)), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", f],
                   check=True)
    files.append(f)
    tl.append({"name": n, "src_a": a, "src_b": b, "out_a": round(t, 4)})
    t += b - a

lst = os.path.join(work, "list.txt")
open(lst, "w").write("".join(f"file '{os.path.abspath(f)}'\n" for f in files))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                os.path.join(args.outdir, "body.mp4")], check=True)
body = np.concatenate(parts)
o = wave.open(os.path.join(args.outdir, "body.wav"), "wb")
o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR)
o.writeframes(np.clip(body, -32768, 32767).astype(np.int16).tobytes()); o.close()
json.dump(tl, open(os.path.join(args.outdir, "timeline.json"), "w"), indent=1)
print("body", round(t, 3), "s ->", args.outdir)
for x in tl:
    print(x)
