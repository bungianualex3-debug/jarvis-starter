"""Step 7 — sound design, synthesised (no downloaded samples, nothing to license).

Every effect gets a travelling whoosh in and a low impact on its word; the 20 effects of the launch video also
get their own signature sound below, in stereo, with a short room tail. With no music under the video, these
are what make each effect land — the launch video uses no music at all.

  python sfx.py public/edit/timing.json public/edit/sfx.wav

Times come from the same timing.json as the picture. An effect you renamed or dropped simply gets the
default whoosh + impact; add a signature for it by copying one of the blocks at the bottom."""
import json, sys, wave
import numpy as np

SR = 48000
FPS = 30
T = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "public/edit/timing.json"))
OUT = sys.argv[2] if len(sys.argv) > 2 else "public/edit/sfx.wav"
N = T["names"]
rng = np.random.default_rng(11)
out = np.zeros((int((T["total"] + 1) * SR), 2), np.float32)


def put(x, at, gain=1.0, pan=0.0):
    """pan -1 left .. 1 right; x mono or (n,2)"""
    if x.ndim == 1:
        x = np.stack([x * np.sqrt((1 - pan) / 2) * 1.414, x * np.sqrt((1 + pan) / 2) * 1.414], 1)
    i = int(at * SR)
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(out) - i)
    out[i:i + n] += x[:n] * gain


def lp(x, k):
    return np.convolve(x, np.ones(k) / k, mode="same")


def hp(x, k):
    return x - lp(x, k)


def ts(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return rng.standard_normal(int(d * SR))


def tone(f, d, decay, wave_="sin"):
    t = ts(d)
    ph = 2 * np.pi * f * t
    w = np.sin(ph) if wave_ == "sin" else (2 * ((ph / (2 * np.pi)) % 1) - 1)
    return w * np.exp(-t * decay)


def sweep(f):
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def fade(x, a=0.003, r=0.02):
    n = len(x); e = np.ones(n)
    A_, R = int(a * SR), int(r * SR)
    e[:A_] = np.linspace(0, 1, A_); e[n - R:] *= np.linspace(1, 0, R)
    return x * e


# ---------- building blocks ----------
def impact(gain=1.0):
    t = ts(0.7)
    body = sweep(48 + 70 * np.exp(-t * 18)) * np.exp(-t * 6)
    hit = lp(noise(0.7), 10) * np.exp(-t * 45) * 0.8
    return (body + hit) * gain


def whoosh(dur=0.45, up=True):
    n = int(dur * SR); x = noise(dur)
    dark, bright = lp(x, 40), hp(x, 6)
    k = np.linspace(0, 1, n) if up else np.linspace(1, 0, n)
    return (dark * (1 - k) + bright * k * 0.6) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 0.5


def stereo(x, p):
    return np.stack([x * np.sqrt((1 - p) / 2) * 1.414, x * np.sqrt((1 + p) / 2) * 1.414], 1)


def whoosh_st(dur=0.45, l2r=True):
    """whoosh that travels across the stereo field"""
    w = whoosh(dur)
    return stereo(w, np.linspace(-0.9, 0.9, len(w)) * (1 if l2r else -1))


def riser(dur):
    t = ts(dur)
    return (sweep(200 + 700 * (t / dur) ** 2) * 0.15 + hp(noise(dur), 3) * 0.15) * (t / dur) ** 2


def ding(f=1320, d=1.0, g=0.5):
    return fade((tone(f, d, 5) + tone(f * 2.76, d, 9) * 0.35 + tone(f * 5.4, d, 16) * 0.12) * g)


def pop():
    t = ts(0.12)
    return sweep(700 * np.exp(-t * 25) + 180) * np.exp(-t * 30) * 0.8


def click(g=0.5):
    return hp(noise(0.02), 2) * np.exp(-ts(0.02) * 400) * g


def paper():
    d = 0.35
    return hp(noise(d), 3) * np.sin(np.pi * np.linspace(0, 1, int(d * SR))) * 0.35


def shutter():
    x = noise(0.12) * np.exp(-ts(0.12) * 100)
    y = np.zeros(int(0.2 * SR)); y[:len(x)] += x; y[int(0.07 * SR):int(0.07 * SR) + len(x)] += x * 0.7
    return y * 0.6


def clunk():
    t = ts(0.4)
    return (np.sin(2 * np.pi * 90 * t) * np.exp(-t * 22) + lp(noise(0.4), 3) * np.exp(-t * 60) * 0.6) * 0.9


def glitch(dur=0.3):
    n = int(dur * SR); x = np.zeros(n)
    for i in range(0, n, 900):
        L = min(900, n - i)
        x[i:i + L] = np.sign(np.sin(2 * np.pi * rng.uniform(80, 1200) * np.arange(L) / SR)) * rng.uniform(0.1, 0.5)
    return x * 0.5


def sub_drop(d=1.4):
    t = ts(d)
    return sweep(70 * np.exp(-t * 1.2) + 30) * np.exp(-t * 2.2) * 0.9


def crack():
    x = np.zeros(int(0.25 * SR))
    for _ in range(14):
        at = int(rng.uniform(0, 0.2) * SR); x[at:at + 300] += rng.standard_normal(300) * np.exp(-np.arange(300) / 40)
    return x * 0.7


def glass():
    n = int(1.2 * SR); x = np.zeros(n)
    for _ in range(90):
        at = int(abs(rng.normal(0.05, 0.25)) * SR) % (n - 4000)
        L = int(rng.integers(400, 3000)); t = np.arange(L) / SR; f = rng.uniform(2500, 9000)
        x[at:at + L] += (np.sin(2 * np.pi * f * t) * 0.5 + rng.standard_normal(L) * 0.5) * np.exp(-t * rng.uniform(20, 70)) * rng.uniform(0.2, 0.7)
    return (x + hp(noise(1.2), 4) * np.exp(-ts(1.2) * 8) * 0.8) * 0.6


def stab(freqs, d=0.9, g=0.3):
    """brassy news sting: detuned saws through a closing low-pass"""
    t = ts(d); x = np.zeros(len(t))
    for f in freqs:
        for det in (-0.6, 0.6):
            x += tone(f + det, d, 3.5, "saw")
    y = np.zeros_like(x); s = 0.0
    cut = 0.35 * np.exp(-t * 5) + 0.04
    for i in range(len(x)):  # one-pole low-pass with a closing cutoff
        s += cut[i] * (x[i] - s); y[i] = s
    return fade(y / len(freqs) * g, 0.004, 0.08)


def swirl(d=1.2):
    """orbit: a tone circling around the head, panned in a loop"""
    t = ts(d)
    x = sweep(520 + 140 * np.sin(2 * np.pi * 2.2 * t)) * 0.25 + hp(noise(d), 8) * 0.12
    x *= np.sin(np.pi * t / d) ** 1.5
    return stereo(x, np.sin(2 * np.pi * 1.6 * t))


def portal_swell(d=1.6):
    t = ts(d)
    low = sweep(40 + 25 * t / d) * 0.6
    shimmer = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (880, 1108, 1318, 1760)) * 0.06 * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t))
    return (low + shimmer + lp(noise(d), 20) * 0.3) * np.minimum(1, t / 0.15) * np.exp(-t * 1.6)


def arp_up(notes, step=0.07, g=0.35):
    x = np.zeros(int((step * len(notes) + 0.6) * SR))
    for i, f in enumerate(notes):
        p = fade(tone(f, 0.5, 9) + tone(f * 2, 0.5, 14) * 0.3)
        a_ = int(i * step * SR); x[a_:a_ + len(p)] += p
    return x * g


def hum(d, f=60):
    t = ts(d)
    x = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 7)) * 0.12
    return fade(x * np.minimum(1, t / 0.05), 0.003, 0.25)


def slide_down(d=0.6):
    t = ts(d)
    return fade(sweep(1400 * np.exp(-t * 3.5) + 250) * 0.3 * (1 - t / d * 0.5), 0.01, 0.1)


def bloop(f0=300, f1=900, d=0.18):
    t = ts(d)
    return sweep(f0 + (f1 - f0) * (t / d) ** 0.5) * np.sin(np.pi * t / d) * 0.5


def beep(f=2000, d=0.07, g=0.25):
    return fade(np.sin(2 * np.pi * f * ts(d)) * g, 0.002, 0.01)


def typing(dur):
    x = np.zeros(int(dur * SR)); at = 0.0
    while at < dur - 0.05:
        i = int(at * SR); L = 500
        x[i:i + L] += hp(rng.standard_normal(L), 3) * np.exp(-np.arange(L) / 60) * rng.uniform(0.2, 0.45)
        at += rng.uniform(0.04, 0.11)
    return x


def boing():
    t = ts(0.7)
    return sweep(180 + 120 * np.sin(t * 30) * np.exp(-t * 4)) * np.exp(-t * 5) * 0.6


A = {k: v[0] for k, v in N.items()}

# ---------- hook: list ticks in, riser into the first effect ----------
for i in range(20):
    put(click(0.6), (6 + i * 2.2) / FPS, 1.0, -0.3 + 0.03 * i)
put(riser(1.6), min(A.values()) - 1.6, 0.9)

# ---------- every effect: travelling whoosh in + low impact on the word ----------
for i, (name, a) in enumerate(A.items()):
    put(whoosh_st(0.4, i % 2 == 0), a - 0.38, 0.8)
    put(impact(), a, 0.6)

# ---------- 20 signatures (each runs only if that effect is in timing.json) ----------
if "Glass Shatter" in N:
    a = A["Glass Shatter"]
    put(crack(), a, 1.0); put(glass(), a + 7 / FPS, 1.1, -0.2); put(glass(), a + 7 / FPS + 0.03, 0.8, 0.3); put(impact(1.2), a + 7 / FPS, 0.6)
if "Sticker" in N:
    a = A["Sticker"]
    put(pop(), a + 0.02, 1.1); put(paper(), a + 0.05, 0.6, 0.2); put(ding(1760, 0.5, 0.3), a + 0.1, 0.8, 0.3)
if "Snap Zoom" in N:
    a = A["Snap Zoom"]
    put(whoosh(0.18, True), a - 0.12, 1.3); put(click(1.0), a, 1.2); put(impact(1.3), a + 0.02, 0.5)
if "Magazine Cover" in N:
    a = A["Magazine Cover"]
    put(paper(), a, 1.1, -0.3); put(shutter(), a + 0.08, 1.0, 0.2); put(ding(2093, 0.6, 0.25), a + 0.12, 0.7)
if "Orbit" in N:
    a = A["Orbit"]
    put(swirl(1.3), a + 0.05, 1.0)
if "Breaking News" in N:
    a = A["Breaking News"]
    put(stab([196, 247, 294, 392], 0.9, 0.5), a, 1.0); put(stab([220, 277, 330, 440], 0.9, 0.5), a + 0.28, 0.9); put(impact(1.3), a + 0.28, 0.5)
if "Jarvis Takeover" in N:
    a, b = N["Jarvis Takeover"]
    hit = T.get("takeover_hit", b - 0.4)
    put(glitch(0.08), a + 0.45, 0.5); put(glitch(0.06), hit - 0.25, 0.6); put(glitch(0.25), hit - 0.03, 1.0); put(sub_drop(), hit + 0.02, 1.0); put(impact(1.3), hit, 0.7); put(glitch(0.15), (A["Portal"] if "Portal" in A else b + 1.2) - 0.35, 0.8)
if "Portal" in N:
    a = A["Portal"]
    put(whoosh(0.5, False)[::-1], a - 0.45, 0.9); put(portal_swell(1.6), a, 1.1)
if "Growth Chart" in N:
    a = A["Growth Chart"]
    put(riser(1.4), a - 1.3, 0.6); put(arp_up([523, 659, 784, 1047, 1319, 1568], 0.075), a + 0.1, 1.0, 0.2); put(ding(2093, 1.0, 0.4), a + 0.6, 0.9)
if "On Air" in N:
    a = A["On Air"]
    put(clunk(), a + 3 / FPS, 1.0, -0.2); put(clunk(), a + 8 / FPS, 1.0, 0.2); put(hum(1.2), a + 3 / FPS, 0.9)
if "Green Screen" in N:
    a = A["Green Screen"]
    put(slide_down(0.6), a + 0.05, 0.9); put(boing(), a + 9 / FPS, 1.0)
if "Vertigo" in N:
    a = A["Vertigo"]
    put(riser(1.6), a, 0.7); put(whoosh(1.2, False), a, 0.6)
if "Liquid Glass" in N:
    a = A["Liquid Glass"]
    put(bloop(260, 900), a + 0.02, 1.0); put(bloop(400, 1300, 0.12), a + 0.2, 0.6, 0.3); put(bloop(350, 1100, 0.1), a + 0.34, 0.4, -0.3)
if "Checklist" in N:
    a = A["Checklist"]
    for i in range(4):
        at = a + (6 + i * 7) / FPS
        put(pop(), at, 0.6); put(ding([1047, 1175, 1319, 1568][i], 0.35, 0.25), at, 0.8, -0.3 + i * 0.2)
if "Viewfinder" in N:
    a = A["Viewfinder"]
    put(beep(2600), a + 6 / FPS, 1.0); put(beep(2600), a + 9 / FPS, 1.0); put(shutter(), a + 18 / FPS, 1.1)
if "Pop-Out" in N:
    a = A["Pop-Out"]
    put(shutter(), a, 1.0); put(pop(), a + 0.12, 0.9); put(whoosh(0.3, True), a + 0.05, 0.6)
if "Phone Mockup" in N:
    a = A["Phone Mockup"]
    put(whoosh_st(0.35, False), a - 0.1, 0.6); put(ding(1568, 0.6, 0.35), a + 0.25, 1.0); put(ding(2093, 0.6, 0.3), a + 0.37, 0.9)
if "Live Terminal" in N:
    a = A["Live Terminal"]
    put(typing(1.8), a + 0.1, 0.8); put(beep(1200, 0.09, 0.3), a + 1.95, 1.0)
if "Spotlight" in N:
    a = A["Spotlight"]
    put(clunk(), a, 1.3); put(hum(1.4, 50), a, 0.6)
if "Final Count" in N:
    a, b = N["Final Count"]
    step = (b - a + 0.6) / 22
    for i in range(20):
        put(click(0.7), a + 0.13 + i * step, 1.2, -0.4 + 0.04 * i)
    put(ding(1047, 1.4, 0.45), a + 0.13 + 20 * step, 1.0)

# ---------- ending ----------
if "bodyEnd" in T:
    put(sub_drop(), T["bodyEnd"], 1.0); put(impact(1.0), T["bodyEnd"], 0.6)

# short room tail so the synth sounds sit in the same space as the voice
ir = rng.standard_normal(int(0.35 * SR)) * np.exp(-ts(0.35) * 14)
ir /= np.abs(ir).sum() / 6
for c in range(2):
    L = len(out) + len(ir)
    out[:, c] += np.fft.irfft(np.fft.rfft(out[:, c], L) * np.fft.rfft(np.roll(ir, c * 37), L), L)[: len(out)] * 0.18

peak = np.abs(out).max()
out = np.tanh(out / peak * 1.4) * 0.6
w = wave.open(OUT, "wb")
w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((out * 32767).astype(np.int16).tobytes()); w.close()
print("sfx", round(len(out) / SR, 2), "s stereo")
