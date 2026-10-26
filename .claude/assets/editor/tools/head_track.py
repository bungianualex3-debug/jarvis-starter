"""Step 5 (optional, needs matte.mp4) — where the head is, every frame.

Zooms, focus squares, things that orbit the head and text that hides behind it all need the head position.
It is read straight off the alpha matte: the top of the silhouette, and the middle of its upper part.

  python head_track.py public/edit/matte.mp4 public/edit/head.json

head.json: per frame [centre x, centre y, width, top], in 1080x1920 pixels, lightly smoothed.
"""
import json, subprocess, sys
import numpy as np

W, H = 1080, 1920
dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
rows = []
while True:
    buf = dec.stdout.read(W * H)
    if len(buf) < W * H:
        break
    m = np.frombuffer(buf, np.uint8).reshape(H, W) > 128
    ys = np.where(m.any(1))[0]
    if len(ys) == 0:
        rows.append(rows[-1] if rows else [540, 700, 400, 400])
        continue
    top = int(ys[0])
    band = m[top:top + 380]  # roughly the head, from the crown down
    xs = np.where(band.any(0))[0]
    cols = band.sum(0)
    cx = float((cols * np.arange(W)).sum() / max(cols.sum(), 1))
    rows.append([cx, top + 190, float(xs[-1] - xs[0]), top])
a = np.array(rows, float)
k = np.ones(5) / 5
for c in range(4):
    a[:, c] = np.convolve(np.pad(a[:, c], 2, mode="edge"), k, mode="valid")
json.dump([[round(v, 1) for v in r] for r in a], open(sys.argv[2], "w"))
print("frames", len(a), "->", sys.argv[2])
