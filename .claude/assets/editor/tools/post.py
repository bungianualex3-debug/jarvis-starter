"""Step 9 — the finish: optional trims, then loudness for the platform.

  python post.py out/video.mp4 final.mp4 [--cut 769-796] [--cut ...]   (frame ranges [start, end) to remove)

A trim here is for a pause you only notice once you watch the whole thing: cutting it after the render is far
cheaper than re-cutting the take, because every time in timing.json would shift. Put the cut on an existing
cut in the footage whenever you can, so no new jump appears.
Loudness goes to -14 LUFS, true peak -1 dB: what TikTok, Reels and Shorts normalise to anyway.
"""
import argparse, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("dst")
ap.add_argument("--cut", action="append", default=[], help="frames A-B to remove, end exclusive")
args = ap.parse_args()
FPS = 30

cuts = sorted(tuple(map(int, c.split("-"))) for c in args.cut)
keep, prev = [], 0
for a, b in cuts:
    keep.append((prev, a))
    prev = b
keep.append((prev, None))

fc = []
for i, (a, b) in enumerate(keep):
    end_v = f":end_frame={b}" if b is not None else ""
    end_a = f":end={b / FPS + 0.01}" if b is not None else ""
    start_a = max(0, a / FPS - (0.01 if i else 0))
    fc.append(f"[0:v]trim=start_frame={a}{end_v},setpts=PTS-STARTPTS[v{i}]")
    fc.append(f"[0:a]atrim=start={start_a}{end_a},asetpts=PTS-STARTPTS[a{i}]")
n = len(keep)
fc.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]")
acc = "a0"
for i in range(1, n):  # 20 ms crossfades so a removed pause leaves no click
    fc.append(f"[{acc}][a{i}]acrossfade=d=0.02[x{i}]")
    acc = f"x{i}"
fc.append(f"[{acc}]loudnorm=I=-14:TP=-1.0:LRA=9,aresample=48000[a]")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", args.src, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k",
                "-movflags", "+faststart", args.dst], check=True)
print("ok", args.dst)
