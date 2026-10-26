"""Step 4 (optional) — cut the person out of the background.

Many effects need the speaker on a separate layer: Green Screen, Vertigo, Pop-Out, the sticker outline, text
that sits BEHIND the head. RobustVideoMatting gives a clean alpha per frame, with no green screen.

  python matte.py public/edit/body.mp4 public/edit

Writes matte.mp4 (grey alpha) and fg.webm (the speaker with transparency, VP9 + alpha).
Needs: `pip install torch` (CUDA build if you have an NVIDIA card; CPU works, slowly). The model downloads
itself from torch.hub the first time (~100 MB).
"""
import subprocess, sys
import torch

inp, outdir = sys.argv[1], sys.argv[2]
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = torch.hub.load("PeterL1n/RobustVideoMatting", "resnet50", trust_repo=True).to(dev).eval()
W, H = 1080, 1920
dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", inp, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", "30",
                        "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", f"{outdir}/matte.mp4"], stdin=subprocess.PIPE)
rec, n = [None] * 4, 0
with torch.no_grad():
    while True:
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        x = torch.frombuffer(bytearray(buf), dtype=torch.uint8).view(H, W, 3).permute(2, 0, 1).float().div(255).unsqueeze(0).to(dev)
        fgr, pha, *rec = model(x, *rec, downsample_ratio=0.25)
        enc.stdin.write((pha[0, 0].clamp(0, 1) * 255).byte().cpu().numpy().tobytes())
        n += 1
        if n % 300 == 0:
            print("...", n, flush=True)
enc.stdin.close(); enc.wait()
# the speaker with alpha, for OffthreadVideo transparent
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", inp, "-i", f"{outdir}/matte.mp4", "-filter_complex",
                "[1:v]format=gray[m];[0:v][m]alphamerge,format=yuva420p[v]", "-map", "[v]", "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-row-mt", "1", "-auto-alt-ref", "0", f"{outdir}/fg.webm"], check=True)
print("frames", n, "->", outdir)
