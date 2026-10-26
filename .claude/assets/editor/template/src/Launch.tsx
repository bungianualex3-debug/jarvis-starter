import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import timing from '../public/edit/timing.json';
import jenv from '../public/edit/jenv.json';
import head from '../public/edit/head.json';
import jsegs from '../public/edit/jsegs.json';

// REFERENCE COMPOSITION — the exact one that made the Jarvis launch video ("20 effects, one take").
// It is not plug-and-play: /jarvis-edit reads it and builds YOUR composition from it, keeping the effects you
// want and dropping the rest. Everything is timed from data measured on the audio (public/edit/*.json):
//   timing.json  names{effect:[onset,end]}, speech{...}, segments{...}, hookWords, hookEnd, bodyEnd, total
//   head.json    per frame [centre x, centre y, width, top] of the speaker's head (tools/head_track.py)
//   jenv.json    per frame {env, talk} of the assistant's voice (tools/voice_env.py) — only for the hologram
//   jsegs.json   phrase timings inside each assistant line wav — only for the hologram and the ending
// Media expected in public/edit/: body.mp4 (the cut take), fg.webm (speaker cut-out with alpha, tools/matte.py),
// plate.jpg (the empty room), holo.webm (assistant hologram, optional), voice.wav, sfx.wav, grain0-5.png, etc.
// Retime the picture to the voice, never the voice to the picture.
const FPS = 30;
export const t = (sec: number) => Math.round(sec * FPS);
export const TOTAL = t(timing.total);
const N = timing.names as Record<string, number[]>;
const S = timing.speech as Record<string, number[] | number>;
const JS = jsegs as Record<string, number[][]>;
const ENV = (jenv as {env: number[]; talk: number[]}).env;
const TALK = (jenv as {env: number[]; talk: number[]}).talk;
const HEAD = head as number[][]; // per frame: [centre x, centre y, width, top] of his head
const BODY_END = timing.bodyEnd;
const CTA_AT = BODY_END + 0.3;

export const C = {
  red: '#ff2a3c',
  redDeep: '#c4001a',
  white: '#ffffff',
  ink: '#0b0b0f',
  paper: '#f3eee4',
  navy: '#070a14',
};
export const FONT = "'Segoe UI', Arial, sans-serif";
const MONO = "'Cascadia Code', Consolas, monospace";
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const rand = (seed: number) => {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
const easeOut = (x: number) => 1 - Math.pow(1 - x, 3);
const easeInOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const headAt = (f: number) => HEAD[Math.max(0, Math.min(HEAD.length - 1, f))];

export const EFFECTS = [
  'Glass Shatter', 'Sticker', 'Snap Zoom', 'Magazine Cover', 'Orbit', 'Breaking News',
  'Jarvis Takeover', 'Portal', 'Growth Chart', 'On Air', 'Green Screen', 'Vertigo',
  'Liquid Glass', 'Checklist', 'Viewfinder', 'Pop-Out', 'Phone Mockup', 'Live Terminal',
  'Spotlight', 'Final Count',
];
const GAG_START = (S.gr as number[])[0];
const winOf = (name: string): [number, number] => {
  const i = EFFECTS.indexOf(name);
  const a = N[name][0];
  let b = i < EFFECTS.length - 1 ? N[EFFECTS[i + 1]][0] : BODY_END;
  if (name === 'On Air') b = GAG_START - 0.15;
  return [a, b];
};
const active = (f: number, name: string) => {
  const [a, b] = winOf(name);
  return f >= t(a) && f < t(b);
};
const local = (f: number, name: string) => f - t(winOf(name)[0]);
const lenOf = (name: string) => t(winOf(name)[1]) - t(winOf(name)[0]);
// Takeover lands on the word "Takeover" (measured onset), not on "Jarvis": glitch hints before it, then Jarvis owns the screen.
const TK_HIT = (timing as any).takeover_hit as number;
const takeoverOwns = (f: number) => active(f, 'Jarvis Takeover') && f >= t(TK_HIT) - 1;

// Jarvis speaking windows (the hologram's appearances) — he is only in the room when it matters.
const HOLO_WINDOWS: [number, number][] = [
  [(S.j_onit as number) + 0.05, (S.j_onit as number) + 1.85],
  [GAG_START - 0.45, (S.obraznic as number[])[1] + 0.9],
];

// ---------- camera ----------
const kickAt = (f: number, at: number, amp: number) => {
  const k = f - t(at);
  if (k < 0 || k > 18) return 0;
  return amp * Math.exp(-k / 4) * Math.sin(k * 1.9);
};
const useCamera = () => {
  const f = useCurrentFrame();
  const segStarts = Object.values(timing.segments as Record<string, number>).map(t).sort((a, b) => a - b);
  const segStart = segStarts.filter((s) => s <= f).pop() ?? 0;
  let scale = 1.04 + (f - segStart) * 0.0009;
  let x = 0;
  let y = 0;
  let rot = 0;
  for (const name of EFFECTS) {
    const at = N[name][0];
    x += kickAt(f, at, 9);
    y += kickAt(f + 3, at, 6);
    rot += kickAt(f + 1, at, 0.35);
  }
  if (active(f, 'Snap Zoom')) {
    const [a, b] = winOf('Snap Zoom');
    const h = headAt(t(a) + 10);
    const s = interpolate(f, [t(a), t(a) + 3, t(b) - 8, t(b)], [0, 1, 1.08, 0], {...clamp, easing: easeOut});
    scale *= 1 + 0.55 * s;
    x += (540 - h[0]) * 0.9 * s;
    y += (760 - h[1] - 60) * 0.9 * s;
  }
  // the gag is a two-shot: lean toward the assistant while it talks, back to the speaker while they talk
  const [g0, g1] = HOLO_WINDOWS[1];
  if (f >= t(g0) && f < t(g1)) {
    const k = TALK[f] ?? 0;
    const inn = interpolate(f, [t(g0), t(g0) + 10, t(g1) - 10, t(g1)], [0, 1, 1, 0], clamp);
    scale *= 1 + 0.1 * inn + 0.06 * k * inn;
    x += -110 * k * inn;
    y += 90 * k * inn;
  }
  // the reply line ("obraznic" in timing.json): comedy punch-in on his face
  const ob = (S.obraznic as number[])[0];
  if (f >= t(ob) - 2 && f < t(ob) + 26) {
    const s = interpolate(f, [t(ob) - 2, t(ob) + 1, t(ob) + 22, t(ob) + 26], [0, 1, 1, 0], clamp);
    const h = headAt(f);
    scale *= 1 + 0.32 * s;
    x += (540 - h[0]) * 0.6 * s;
    y += (800 - h[1]) * 0.6 * s;
  }
  // the take always ends on a slow push into the portal
  if (active(f, 'Portal')) {
    const L = lenOf('Portal');
    const k = local(f, 'Portal');
    const s = interpolate(k, [L - 14, L], [0, 1], {...clamp, easing: (q) => q * q * q});
    scale *= 1 + 4 * s;
    x += (540 - PORTAL.x) * 4 * s * 0.25;
    y += (960 - PORTAL.y) * 4 * s * 0.25;
  }
  return {scale, x, y, rot};
};

// ---------- base layers ----------
const Base: React.FC<{style?: React.CSSProperties}> = ({style}) => (
  <OffthreadVideo src={staticFile('edit/body.mp4')} muted style={{position: 'absolute', inset: 0, ...style}} />
);
const Cutout: React.FC<{style?: React.CSSProperties}> = ({style}) => (
  <OffthreadVideo src={staticFile('edit/fg.webm')} transparent muted style={{position: 'absolute', inset: 0, ...style}} />
);
const Plate: React.FC<{style?: React.CSSProperties}> = ({style}) => (
  <Img src={staticFile('edit/plate.jpg')} style={{position: 'absolute', inset: 0, width: 1080, height: 1920, ...style}} />
);

const Grade: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill
        style={{
          background: 'linear-gradient(160deg, rgba(0,70,110,0.5) 0%, rgba(0,0,0,0) 45%, rgba(255,120,40,0.4) 100%)',
          mixBlendMode: 'soft-light',
        }}
      />
      <AbsoluteFill
        style={{background: 'radial-gradient(ellipse 75% 60% at 50% 42%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%)'}}
      />
      <Img
        src={staticFile(`edit/grain${f % 6}.png`)}
        style={{position: 'absolute', inset: 0, width: '100%', height: '100%', mixBlendMode: 'overlay', opacity: 0.15}}
      />
    </AbsoluteFill>
  );
};

// ---------- Jarvis in the room ----------
const holoOn = (f: number) => {
  for (const [a, b] of HOLO_WINDOWS) {
    if (f >= t(a) - 12 && f < t(b) + 12) {
      return {
        on: interpolate(f, [t(a) - 12, t(a), t(b), t(b) + 12], [0, 1, 1, 0], clamp),
        building: f < t(a),
        a,
        b,
      };
    }
  }
  return null;
};
const HoloFigure: React.FC<{x: number; y: number; w: number; h: number; on: number; e: number; talk: number; build: number}> = ({
  x,
  y,
  w,
  h,
  on,
  e,
  talk,
  build,
}) => {
  const f = useCurrentFrame();
  // materialise / dematerialise: a bright scan line sweeps, the figure is revealed behind it
  const reveal = Math.max(0, Math.min(1, on));
  const flick = reveal < 1 ? (rand(f * 3.1) > 0.35 ? 1 : 0.35) : 0.96 + 0.04 * Math.sin(f * 1.7);
  const lineY = h * reveal;
  const look = (1 - talk) * -16; // listening: turned toward him; talking: to camera
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, height: h, perspective: 900}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `rotateY(${look}deg) translateY(${Math.sin(f / 22) * 5}px)`,
          transformOrigin: '50% 60%',
          clipPath: `inset(0 0 ${(1 - reveal) * 100}% 0)`,
          opacity: flick,
        }}
      >
        <OffthreadVideo
          src={staticFile('edit/holo.webm')}
          transparent
          muted
          style={{position: 'absolute', inset: 0, width: '100%', height: '100%', filter: `brightness(${1.05 + 0.25 * e}) contrast(1.08)`}}
        />
      </div>
      {build < 1 && (
        <div
          style={{
            position: 'absolute',
            left: -20,
            right: -20,
            top: lineY - 2,
            height: 4,
            background: 'white',
            boxShadow: `0 0 18px 6px ${C.red}`,
            opacity: reveal > 0 && reveal < 1 ? 1 : 0,
          }}
        />
      )}
    </div>
  );
};
const Hologram: React.FC = () => {
  const f = useCurrentFrame();
  const st = holoOn(f);
  if (!st) return null;
  const e = ENV[f] ?? 0;
  const talk = TALK[f] ?? 0;
  const X = 640;
  const Y = 170;
  const Wd = 420;
  const Hd = 498;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 560px 680px at ${X + Wd / 2}px ${Y + Hd * 0.5}px, rgba(255,40,60,${(0.2 + 0.5 * e) * st.on}), rgba(255,40,60,0) 70%)`,
          mixBlendMode: 'screen',
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 250px 290px at ${X + Wd / 2}px ${Y + Hd * 0.45}px, rgba(8,0,3,${0.6 * st.on}), rgba(8,0,3,0) 75%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: X + Wd / 2 - 230,
          top: Y + Hd - 50,
          width: 460,
          height: 300,
          background: 'linear-gradient(0deg, rgba(255,60,80,0.4), rgba(255,60,80,0))',
          clipPath: 'polygon(44% 100%, 56% 100%, 100% 0%, 0% 0%)',
          filter: 'blur(10px)',
          opacity: st.on * (0.55 + 0.45 * e),
          mixBlendMode: 'screen',
        }}
      />
      <HoloFigure x={X} y={Y} w={Wd} h={Hd} on={st.on} e={e} talk={talk} build={st.on} />
    </AbsoluteFill>
  );
};
// a red rim on him from the projection, only while Jarvis is in the room
const HoloRim: React.FC = () => {
  const f = useCurrentFrame();
  const st = holoOn(f);
  if (!st || st.on < 0.05) return null;
  const e = ENV[f] ?? 0;
  return (
    <Cutout
      style={{
        filter: `brightness(0) drop-shadow(0 0 0 ${C.red})`,
        opacity: (0.18 + 0.35 * e) * st.on,
        mixBlendMode: 'screen',
        transform: 'translate(6px, -4px)',
        WebkitMaskImage: 'linear-gradient(110deg, transparent 40%, black 75%)',
      }}
    />
  );
};

// ---------- 1. Glass Shatter ----------
const IMPACT = {x: 720, y: 600};
type Shard = {pts: [number, number][]; cx: number; cy: number; seed: number};
const SHARDS: Shard[] = (() => {
  const rings = [0, 70, 170, 330, 560, 900, 1500];
  const sectors = 11;
  const ang: number[][] = rings.map((_, r) =>
    Array.from({length: sectors}, (_, s) => ((s + (r === 0 ? 0 : (rand(r * 31 + s) - 0.5) * 0.7)) / sectors) * Math.PI * 2),
  );
  const P = (r: number, s: number): [number, number] => {
    const rr = rings[r] * (r === 0 ? 1 : 0.85 + rand(r * 7 + s * 13) * 0.3);
    const a = ang[r][s % sectors];
    return [IMPACT.x + Math.cos(a) * rr, IMPACT.y + Math.sin(a) * rr];
  };
  const out: Shard[] = [];
  for (let r = 0; r < rings.length - 1; r++) {
    for (let s = 0; s < sectors; s++) {
      const pts = [P(r, s), P(r + 1, s), P(r + 1, s + 1), P(r, s + 1)];
      const cx = pts.reduce((a, p) => a + p[0], 0) / 4;
      const cy = pts.reduce((a, p) => a + p[1], 0) / 4;
      out.push({pts, cx, cy, seed: r * 100 + s});
    }
  }
  return out;
})();
const GlassShatter: React.FC = () => {
  const f = useCurrentFrame();
  const at = t(N['Glass Shatter'][0]);
  const brk = at + 7;
  if (f < at || f > brk + 28) return null;
  const crack = interpolate(f, [at, brk], [0, 1], clamp);
  return (
    <AbsoluteFill>
      {f < brk ? (
        <svg width={1080} height={1920} style={{position: 'absolute'}}>
          {SHARDS.map((s, i) => (
            <polygon
              key={i}
              points={s.pts.map((p) => p.join(',')).join(' ')}
              fill="none"
              stroke="rgba(255,255,255,0.9)"
              strokeWidth={2.2}
              strokeDasharray={2400}
              strokeDashoffset={2400 * (1 - Math.min(1, crack * 1.6 - Math.hypot(s.cx - IMPACT.x, s.cy - IMPACT.y) / 1400))}
              style={{filter: 'drop-shadow(0 0 6px rgba(200,230,255,0.9))'}}
            />
          ))}
        </svg>
      ) : (
        SHARDS.map((s, i) => {
          const k = (f - brk) / FPS;
          const dx = s.cx - IMPACT.x;
          const dy = s.cy - IMPACT.y;
          const d = Math.max(60, Math.hypot(dx, dy));
          const v = 900 + rand(s.seed) * 900;
          const x = (dx / d) * v * k;
          const y = (dy / d) * v * k + 2600 * k * k;
          const rz = (rand(s.seed + 5) - 0.5) * 540 * k;
          const sc = 1 + k * (0.3 + rand(s.seed + 9) * 0.6);
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                inset: 0,
                clipPath: `polygon(${s.pts.map((p) => `${p[0]}px ${p[1]}px`).join(',')})`,
                transformOrigin: `${s.cx}px ${s.cy}px`,
                transform: `translate(${x}px, ${y}px) rotate(${rz}deg) scale(${sc})`,
                opacity: interpolate(k, [0.5, 0.9], [1, 0], clamp),
              }}
            >
              <Img src={staticFile('edit/shatter.png')} style={{width: 1080, height: 1920, filter: 'brightness(1.12)'}} />
              <div style={{position: 'absolute', inset: 0, boxShadow: 'inset 0 0 0 2px rgba(255,255,255,0.8)'}} />
            </div>
          );
        })
      )}
      <AbsoluteFill style={{background: 'white', opacity: interpolate(f, [brk, brk + 1, brk + 5], [0, 0.5, 0], clamp)}} />
    </AbsoluteFill>
  );
};

// ---------- 2. Sticker ----------
const outline = (px: number, col = 'white') =>
  [0, 45, 90, 135, 180, 225, 270, 315]
    .map((d) => `drop-shadow(${Math.cos((d * Math.PI) / 180) * px}px ${Math.sin((d * Math.PI) / 180) * px}px 0 ${col})`)
    .join(' ');
const Sticker: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Sticker')) return null;
  const k = local(f, 'Sticker');
  const p = spring({frame: k, fps, config: {damping: 11, stiffness: 160}});
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{background: C.red}} />
      <AbsoluteFill
        style={{
          backgroundImage: 'radial-gradient(rgba(0,0,0,0.22) 3px, transparent 3.5px)',
          backgroundSize: '22px 22px',
          transform: `translateY(${(f % 60) * 0.4}px)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 380,
          left: -40,
          width: 1400,
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 300,
          lineHeight: 0.86,
          color: 'transparent',
          WebkitTextStroke: '4px rgba(0,0,0,0.85)',
          letterSpacing: -6,
          whiteSpace: 'nowrap',
          transform: `translateX(${-k * 3}px)`,
        }}
      >
        JARVIS JARVIS
        <br />
        <span style={{color: C.ink, WebkitTextStroke: '0'}}>EDITS.</span>
      </div>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `rotate(${-3 * p}deg) scale(${0.86 + 0.14 * p})`,
          transformOrigin: '50% 75%',
          filter: `${outline(9)} drop-shadow(18px 26px 0 rgba(0,0,0,0.35))`,
        }}
      >
        <Cutout />
      </div>
    </AbsoluteFill>
  );
};

// ---------- 4. Magazine Cover ----------
const Magazine: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Magazine Cover')) return null;
  const k = local(f, 'Magazine Cover');
  const p = spring({frame: k, fps, config: {damping: 14, stiffness: 150}});
  const line = (at: number) => spring({frame: k - at, fps, config: {damping: 15, stiffness: 180}});
  const side: React.CSSProperties = {position: 'absolute', fontFamily: FONT, color: C.ink, fontWeight: 900, lineHeight: 0.95};
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{background: C.paper}} />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(255,255,255,0.6), rgba(0,0,0,0.12))'}} />
      <div style={{...side, top: 250, left: 40, fontSize: 30, letterSpacing: 6, fontWeight: 700, opacity: p}}>
        THE AI ISSUE · NOV 2026
      </div>
      <div
        style={{
          ...side,
          top: 270,
          left: 0,
          width: 1080,
          textAlign: 'center',
          fontSize: 300,
          color: C.red,
          letterSpacing: -14,
          transform: `translateY(${(1 - p) * -120}px)`,
          opacity: p,
        }}
      >
        JARVIS
      </div>
      <div style={{...side, top: 700, left: 44, fontSize: 64, transform: `translateX(${(1 - line(4)) * -300}px)`}}>
        ZERO
        <br />
        EDITORS.
        <div style={{fontSize: 28, fontWeight: 600, marginTop: 10, color: '#333'}}>One take. One prompt.</div>
      </div>
      <div style={{...side, top: 1010, right: 44, fontSize: 56, textAlign: 'right', transform: `translateX(${(1 - line(8)) * 300}px)`}}>
        THE AI
        <br />
        THAT EDITS
        <br />
        <span style={{color: C.red}}>ITSELF</span>
      </div>
      <Cutout />
      <div
        style={{
          position: 'absolute',
          left: 60,
          top: 1330,
          width: 210,
          height: 210,
          borderRadius: '50%',
          background: C.red,
          color: 'white',
          fontFamily: FONT,
          fontWeight: 900,
          textAlign: 'center',
          paddingTop: 42,
          fontSize: 92,
          lineHeight: 0.9,
          transform: `rotate(-14deg) scale(${line(12)})`,
          boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
        }}
      >
        20
        <div style={{fontSize: 24, letterSpacing: 2}}>EFFECTS INSIDE</div>
      </div>
      <div
        style={{
          position: 'absolute',
          right: 60,
          top: 1420,
          width: 170,
          height: 110,
          background: 'white',
          padding: 10,
          opacity: line(14),
          backgroundImage:
            'repeating-linear-gradient(90deg, #111 0 3px, transparent 3px 5px, #111 5px 6px, transparent 6px 10px, #111 10px 14px, transparent 14px 16px)',
          backgroundClip: 'content-box',
        }}
      />
    </AbsoluteFill>
  );
};

// ---------- 5. Orbit: icons circling his head, passing behind it ----------
const ORBIT_ICONS = ['▶', '✂', 'CC', 'Aa', '♪', '✦', '⏱', '◐'];
const OrbitIcons: React.FC<{front: boolean}> = ({front}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Orbit')) return null;
  const k = local(f, 'Orbit');
  const h = headAt(f);
  const grow = spring({frame: k, fps, config: {damping: 14, stiffness: 120}});
  const out = interpolate(k, [lenOf('Orbit') - 6, lenOf('Orbit')], [1, 0], clamp);
  const R = 330 * grow;
  return (
    <AbsoluteFill>
      {ORBIT_ICONS.map((ic, i) => {
        const a = (i / ORBIT_ICONS.length) * Math.PI * 2 + k * 0.075;
        const z = Math.sin(a);
        if (front !== z > 0) return null;
        const x = h[0] + Math.cos(a) * R;
        const y = h[1] + 40 + z * 70 - 20;
        const sc = 0.75 + 0.35 * (z + 1) / 2;
        return (
          <div
            key={ic}
            style={{
              position: 'absolute',
              left: x - 46,
              top: y - 46,
              width: 92,
              height: 92,
              borderRadius: 24,
              background: i % 3 === 0 ? C.red : 'rgba(255,255,255,0.95)',
              color: i % 3 === 0 ? 'white' : C.ink,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: FONT,
              fontWeight: 900,
              fontSize: 40,
              transform: `scale(${sc * out})`,
              boxShadow: `0 12px 30px rgba(0,0,0,0.45)${i % 3 === 0 ? `, 0 0 24px ${C.red}` : ''}`,
              opacity: front ? 1 : 0.85,
            }}
          >
            {ic}
          </div>
        );
      })}
      {front && (
        <svg width={1080} height={1920} style={{position: 'absolute', opacity: 0.5 * grow * out}}>
          <ellipse cx={h[0]} cy={h[1] + 20} rx={R} ry={70} fill="none" stroke="white" strokeWidth={2} strokeDasharray="6 10" />
        </svg>
      )}
    </AbsoluteFill>
  );
};

// ---------- 6. Breaking News: banners slam in behind him ----------
const BANNERS = [
  {tag: 'BREAKING', text: 'AI EDITS ITS OWN VIDEO', y: 330, r: -7, at: 0},
  {tag: 'JUST IN', text: 'ZERO EDITORS NEEDED', y: 520, r: 5, at: 4},
  {tag: 'LIVE', text: 'JARVIS GOES PUBLIC', y: 760, r: -4, at: 8},
  {tag: 'UPDATE', text: '20 EFFECTS · 1 PROMPT', y: 980, r: 6, at: 12},
];
const NewsBanners: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const k = local(f, 'Breaking News');
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{background: 'rgba(5,5,8,0.45)'}} />
      {BANNERS.map((b, i) => {
        const p = spring({frame: k - b.at, fps, config: {damping: 13, stiffness: 210}});
        const fromLeft = i % 2 === 0;
        return (
          <div
            key={b.text}
            style={{
              position: 'absolute',
              top: b.y,
              left: -60,
              width: 1300,
              display: 'flex',
              transform: `rotate(${b.r}deg) translateX(${(1 - p) * (fromLeft ? -1400 : 1400) - k * (fromLeft ? 2 : -2)}px)`,
              fontFamily: FONT,
              fontWeight: 900,
              boxShadow: '0 14px 40px rgba(0,0,0,0.5)',
            }}
          >
            <div style={{background: C.red, color: 'white', fontSize: 40, padding: '14px 26px', letterSpacing: 3}}>{b.tag}</div>
            <div style={{background: 'white', color: C.ink, fontSize: 64, padding: '4px 30px', flex: 1, whiteSpace: 'nowrap'}}>
              {b.text}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
const NewsTicker: React.FC = () => {
  const f = useCurrentFrame();
  const k = local(f, 'Breaking News');
  const txt = '  JARVIS EDITS HIS OWN LAUNCH VIDEO ·  20 EFFECTS IN ONE TAKE ·  NO HUMAN EDITOR ·  FREE ON GITHUB ·';
  return (
    <div
      style={{
        position: 'absolute',
        top: 1560,
        left: 0,
        width: 1080,
        height: 70,
        background: C.ink,
        borderTop: `5px solid ${C.red}`,
        overflow: 'hidden',
        fontFamily: FONT,
        fontWeight: 800,
        fontSize: 40,
        color: 'white',
        lineHeight: '64px',
        whiteSpace: 'nowrap',
      }}
    >
      <div style={{transform: `translateX(${1080 - k * 14}px)`}}>
        {txt}
        {txt}
      </div>
    </div>
  );
};

// ---------- 7. Jarvis Takeover ----------
const Takeover: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Jarvis Takeover')) return null;
  const k0 = local(f, 'Jarvis Takeover');
  const L = lenOf('Jarvis Takeover');
  // while he says the phrase: rare short glitch hints on his shot, denser near the end;
  // then 0-6 full glitch, Jarvis owns the screen, last 10: slice back to him
  const S = t(TK_HIT) - t(N['Jarvis Takeover'][0]) - 1;
  if (k0 < S) {
    const near = k0 / S;
    const hint = rand(k0 * 7 + 3) < 0.08 + 0.35 * near * near;
    if (!hint) return null;
    return (
      <AbsoluteFill>
        {Array.from({length: 6}).map((_, i) => {
          const y = rand(k0 * 13 + i) * 1800;
          const h = 20 + rand(k0 + i * 5) * 90;
          return (
            <div key={i} style={{position: 'absolute', left: 0, top: y, width: 1080, height: h, overflow: 'hidden'}}>
              <div style={{position: 'absolute', top: -y, transform: `translateX(${(rand(i * 9 + k0 * 3) - 0.5) * 120 * (0.4 + near)}px)`}}>
                <Base style={{width: 1080, height: 1920, filter: `hue-rotate(${rand(i + k0) > 0.5 ? 140 : 0}deg) saturate(1.6)`}} />
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
    );
  }
  const k = k0 - S;
  const glitch = k < 4;
  const back = interpolate(k, [L - S - 10, L - S - 1], [0, 1], clamp);
  const own = interpolate(k, [1, 4], [0, 1], clamp) * (1 - back);
  const slices = 14;
  return (
    <AbsoluteFill>
      {glitch &&
        Array.from({length: slices}).map((_, i) => (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: 0,
              top: (1920 / slices) * i,
              width: 1080,
              height: 1920 / slices,
              overflow: 'hidden',
            }}
          >
            <div style={{position: 'absolute', top: -(1920 / slices) * i, transform: `translateX(${(rand(i * 9 + k * 3) - 0.5) * 160 * (k / 6)}px)`}}>
              <Base style={{width: 1080, height: 1920, filter: `hue-rotate(${rand(i + k) > 0.6 ? 140 : 0}deg) saturate(1.6)`}} />
            </div>
          </div>
        ))}
      <AbsoluteFill style={{opacity: own}}>
        <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 40%, #2a0006 0%, #050003 70%)'}} />
        {/* circuit traces growing out from the centre */}
        <svg width={1080} height={1920} style={{position: 'absolute'}}>
          {Array.from({length: 26}).map((_, i) => {
            const a = (i / 26) * Math.PI * 2 + rand(i) * 0.2;
            const r0 = 330;
            const r1 = 330 + 500 * Math.min(1, Math.max(0, (k - 6 - rand(i + 4) * 8) / 18));
            const mid = r0 + (r1 - r0) * 0.55;
            const bend = a + (rand(i + 7) > 0.5 ? 0.25 : -0.25);
            const P = (r: number, an: number) => `${540 + Math.cos(an) * r},${800 + Math.sin(an) * r}`;
            return (
              <g key={i}>
                <polyline points={`${P(r0, a)} ${P(mid, a)} ${P(r1, bend)}`} fill="none" stroke={C.red} strokeWidth={3} opacity={0.85} style={{filter: `drop-shadow(0 0 6px ${C.red})`}} />
                <circle cx={540 + Math.cos(bend) * r1} cy={800 + Math.sin(bend) * r1} r={7} fill={C.red} />
              </g>
            );
          })}
        </svg>
        <div style={{position: 'absolute', left: 90, top: 300, width: 900, height: 1067, transform: `scale(${1 + k * 0.002})`}}>
          <OffthreadVideo src={staticFile('edit/holo.webm')} transparent muted style={{width: '100%', height: '100%', filter: 'brightness(1.15) contrast(1.1)'}} />
        </div>
        <div
          style={{
            position: 'absolute',
            top: 1430,
            width: 1080,
            textAlign: 'center',
            fontFamily: MONO,
            fontSize: 44,
            letterSpacing: 10,
            color: C.red,
            textShadow: `0 0 18px ${C.red}`,
            opacity: rand(k) > 0.15 ? 1 : 0.3,
          }}
        >
          {'> TAKEOVER: JARVIS'.slice(0, Math.max(0, Math.floor((k - 8) * 1.2)))}
        </div>
        <AbsoluteFill
          style={{
            backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.35) 0 2px, transparent 2px 5px)',
            mixBlendMode: 'multiply',
          }}
        />
      </AbsoluteFill>
      {/* slice-wipe back to his shot */}
      {back > 0 &&
        Array.from({length: 10}).map((_, i) => {
          const d = Math.max(0, Math.min(1, back * 1.6 - i * 0.06));
          return (
            <div key={i} style={{position: 'absolute', left: 0, top: 192 * i, width: 1080 * d, height: 192, overflow: 'hidden'}}>
              <div style={{position: 'absolute', top: -192 * i}}>
                <Base style={{width: 1080, height: 1920}} />
              </div>
            </div>
          );
        })}
    </AbsoluteFill>
  );
};

// ---------- 8. Portal ----------
const PORTAL = {x: 790, y: 640};
const Portal: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Portal')) return null;
  const k = local(f, 'Portal');
  const r = 250 * spring({frame: k, fps, config: {damping: 12, stiffness: 110}});
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: PORTAL.x - r,
          top: PORTAL.y - r,
          width: 2 * r,
          height: 2 * r,
          borderRadius: '50%',
          overflow: 'hidden',
          boxShadow: `0 0 0 6px ${C.red}, 0 0 60px 14px ${C.red}, inset 0 0 60px rgba(0,0,0,0.8)`,
        }}
      >
        <OffthreadVideo
          src={staticFile('edit/lume.mp4')}
          muted
          style={{position: 'absolute', left: '50%', top: '50%', height: 560, transform: `translate(-62%, -50%) scale(${1.1 + k * 0.004})`}}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: PORTAL.x - r - 18,
          top: PORTAL.y - r - 18,
          width: 2 * r + 36,
          height: 2 * r + 36,
          borderRadius: '50%',
          background: `conic-gradient(from ${k * 9}deg, transparent 0deg, rgba(255,255,255,0.85) 40deg, transparent 90deg, ${C.red} 200deg, transparent 260deg)`,
          WebkitMaskImage: 'radial-gradient(circle, transparent 66%, black 68%, black 72%, transparent 74%)',
          filter: 'blur(1px)',
        }}
      />
    </AbsoluteFill>
  );
};

// ---------- 9. Growth Chart ----------
const Growth: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Growth Chart')) return null;
  const k = local(f, 'Growth Chart');
  const L = lenOf('Growth Chart');
  const prog = easeInOut(interpolate(k, [3, L - 8], [0, 1], clamp));
  const pts: string[] = [];
  const n = 60;
  let lastX = 0;
  let lastY = 0;
  for (let i = 0; i <= n * prog; i++) {
    const q = i / n;
    const x = 40 + q * 1000;
    const y = 1180 - (Math.pow(q, 2.4) * 900 + Math.sin(q * 30) * 14 * (1 - q));
    pts.push(`${x},${y}`);
    lastX = x;
    lastY = y;
  }
  const mult = Math.max(1, Math.round(1 + Math.pow(prog, 2.4) * 9));
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at 70% 30%, #10203d 0%, ${C.navy} 70%)`}} />
      <AbsoluteFill
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.07) 1px, transparent 1px)',
          backgroundSize: '90px 90px',
          backgroundPosition: `0 ${k * 2}px`,
        }}
      />
      <svg width={1080} height={1920} style={{position: 'absolute'}}>
        <defs>
          <linearGradient id="gfill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={C.red} stopOpacity="0.45" />
            <stop offset="1" stopColor={C.red} stopOpacity="0" />
          </linearGradient>
        </defs>
        {pts.length > 1 && (
          <>
            <polygon points={`40,1400 ${pts.join(' ')} ${lastX},1400`} fill="url(#gfill)" />
            <polyline points={pts.join(' ')} fill="none" stroke={C.red} strokeWidth={9} strokeLinejoin="round" style={{filter: `drop-shadow(0 0 14px ${C.red})`}} />
            <circle cx={lastX} cy={lastY} r={16} fill="white" style={{filter: `drop-shadow(0 0 12px white)`}} />
          </>
        )}
      </svg>
      <div
        style={{
          position: 'absolute',
          right: 50,
          top: 330,
          background: C.red,
          color: 'white',
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: 110,
          padding: '0 30px',
          borderRadius: 18,
          boxShadow: `0 0 40px ${C.red}`,
        }}
      >
        {mult}×<span style={{fontSize: 34, marginLeft: 8, letterSpacing: 2}}>REACH</span>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 10. On Air ----------
const OnAir: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'On Air')) return null;
  const k = local(f, 'On Air');
  const l1 = k >= 3 ? 1 : 0;
  const l2 = k >= 8 ? 1 : 0;
  const sign = k >= 13 ? (k < 16 ? (k % 2 ? 1 : 0.2) : 1) : 0.12;
  const soft = (x: number, on: boolean, flip: boolean) => (
    <div style={{position: 'absolute', left: x, top: 280, width: 300, height: 420, transform: `perspective(800px) rotateY(${flip ? -28 : 28}deg)`}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 18,
          background: on ? 'linear-gradient(#ffffff, #e9eef7)' : '#1b1d24',
          boxShadow: on ? '0 0 120px 40px rgba(255,255,255,0.45)' : 'none',
          border: '10px solid #111',
        }}
      />
    </div>
  );
  return (
    <AbsoluteFill>
      <Plate style={{filter: 'brightness(0.18) saturate(0.4) blur(2px)'}} />
      <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 55%, rgba(60,70,110,${0.25 * l2}), transparent 70%)`}} />
      {soft(-90, !!l1, false)}
      {soft(870, !!l2, true)}
      {/* haze beams */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(115deg, rgba(255,255,255,${0.12 * l1}) 0%, transparent 40%), linear-gradient(245deg, rgba(255,255,255,${0.12 * l2}) 0%, transparent 40%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 300,
          width: 1080,
          textAlign: 'center',
        }}
      >
        <span
          style={{
            display: 'inline-block',
            fontFamily: FONT,
            fontWeight: 900,
            fontSize: 76,
            letterSpacing: 8,
            padding: '6px 36px',
            borderRadius: 14,
            border: `5px solid ${sign > 0.5 ? C.red : '#4a1016'}`,
            color: sign > 0.5 ? 'white' : '#4a1016',
            background: sign > 0.5 ? C.red : '#1a0306',
            boxShadow: sign > 0.5 ? `0 0 60px 10px ${C.red}` : 'none',
          }}
        >
          ON AIR
        </span>
      </div>
    </AbsoluteFill>
  );
};

// ---------- 11. Green Screen → the snail ----------
const SNAIL = {x: 520, y: 140, s: 0.55};
const GreenScreen: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Green Screen')) return null;
  const k = local(f, 'Green Screen');
  const keyed = k >= 9;
  return (
    <AbsoluteFill>
      {!keyed ? (
        <AbsoluteFill style={{background: '#14c94a'}} />
      ) : (
        <AbsoluteFill>
          {/* the real snail (his Omni Flash clip): a blurred full-frame copy as the garden, the sharp clip
              scaled down into the free space right of his head, edges feathered into the blur */}
          <Sequence from={t(N['Green Screen'][0]) + 9} layout="none">
            <AbsoluteFill style={{transform: 'scale(1.25)', filter: 'blur(18px) brightness(0.95)'}}>
              <OffthreadVideo src={staticFile('edit/melc.mp4')} muted style={{width: 1080, height: 1920}} />
            </AbsoluteFill>
            <div
              style={{
                position: 'absolute',
                left: SNAIL.x,
                top: SNAIL.y,
                width: 1080 * SNAIL.s,
                height: 1920 * SNAIL.s,
                transform: `scale(${1 + k * 0.0015})`,
                WebkitMaskImage: 'radial-gradient(ellipse 50% 50% at 50% 50%, black 62%, transparent 100%)',
                maskImage: 'radial-gradient(ellipse 50% 50% at 50% 50%, black 62%, transparent 100%)',
              }}
            >
              <OffthreadVideo src={staticFile('edit/melc.mp4')} muted style={{width: '100%', height: '100%'}} />
            </div>
          </Sequence>
          <div
            style={{
              position: 'absolute',
              top: 330,
              right: 40,
              background: C.ink,
              color: 'white',
              fontFamily: MONO,
              fontWeight: 700,
              fontSize: 40,
              padding: '14px 24px',
              borderRadius: 12,
              border: `3px solid ${C.red}`,
            }}
          >
            TOP SPEED
            <div style={{fontSize: 70, color: C.red}}>0.03 km/h</div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

// ---------- 12. Vertigo: background stretches, he stays ----------
const Vertigo: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Vertigo')) return null;
  const k = local(f, 'Vertigo');
  const L = lenOf('Vertigo');
  const z = interpolate(k, [0, L], [1, 1.55], {...clamp, easing: easeInOut});
  const h = headAt(f);
  return (
    <AbsoluteFill>
      <Plate style={{transform: `scale(${z})`, transformOrigin: `${h[0]}px ${h[1]}px`, filter: `blur(${(z - 1) * 3}px)`}} />
      <Cutout style={{transform: `scale(${1 / Math.sqrt(z)})`, transformOrigin: `${h[0]}px 1920px`}} />
    </AbsoluteFill>
  );
};

// ---------- 13. Liquid Glass: a glass lens rolls across ----------
const LiquidGlass: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Liquid Glass')) return null;
  const k = local(f, 'Liquid Glass');
  const L = lenOf('Liquid Glass');
  const p = easeInOut(interpolate(k, [0, L], [0, 1], clamp));
  const cx = -200 + p * 1480;
  const cy = headAt(f)[1] + 680;
  const R = 230;
  const mag = 1.32;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: cx - R,
          top: cy - R * 0.72,
          width: 2 * R,
          height: 1.44 * R,
          borderRadius: R,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: -(cx - R),
            top: -(cy - R * 0.72),
            width: 1080,
            height: 1920,
            transform: `scale(${mag})`,
            transformOrigin: `${cx}px ${cy}px`,
            filter: 'saturate(1.25) brightness(1.08)',
          }}
        >
          <Base style={{width: 1080, height: 1920}} />
        </div>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: R,
            boxShadow: 'inset 0 0 0 3px rgba(255,255,255,0.75), inset 0 18px 30px rgba(255,255,255,0.45), inset 0 -20px 40px rgba(0,0,0,0.35)',
            background: 'linear-gradient(160deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0) 35%)',
          }}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: cx - R,
          top: cy - R * 0.72,
          width: 2 * R,
          height: 1.44 * R,
          borderRadius: R,
          boxShadow: '0 30px 60px rgba(0,0,0,0.35)',
        }}
      />
    </AbsoluteFill>
  );
};

// ---------- 14. Checklist ----------
const CHECKS = ['Cut every pause', 'Captioned every word', '20 effects', 'Jarvis in the room'];
const Checklist: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Checklist')) return null;
  const k = local(f, 'Checklist');
  const inn = spring({frame: k, fps, config: {damping: 14, stiffness: 170}});
  return (
    <div
      style={{
        position: 'absolute',
        right: 26,
        top: 600,
        width: 430,
        padding: '26px 28px',
        borderRadius: 28,
        background: 'rgba(14,14,20,0.82)',
        border: '2px solid rgba(255,255,255,0.22)',
        boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
        fontFamily: FONT,
        transform: `translateX(${(1 - inn) * 560}px)`,
      }}
    >
      <div style={{color: C.red, fontWeight: 900, fontSize: 28, letterSpacing: 6, marginBottom: 14}}>JARVIS · TASKS</div>
      {CHECKS.map((c, i) => {
        const done = spring({frame: k - 6 - i * 7, fps, config: {damping: 12, stiffness: 240}});
        return (
          <div key={c} style={{display: 'flex', alignItems: 'center', gap: 18, margin: '14px 0', opacity: 0.4 + 0.6 * Math.min(1, done * 2)}}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 14,
                background: done > 0.1 ? C.red : 'transparent',
                border: `3px solid ${done > 0.1 ? C.red : 'rgba(255,255,255,0.5)'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: 32,
                fontWeight: 900,
                transform: `scale(${0.6 + 0.4 * done})`,
              }}
            >
              {done > 0.1 ? '✓' : ''}
            </div>
            <div style={{color: 'white', fontWeight: 800, fontSize: 29, whiteSpace: 'nowrap'}}>{c}</div>
          </div>
        );
      })}
    </div>
  );
};

// ---------- 15. Viewfinder ----------
const Viewfinder: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Viewfinder')) return null;
  const k = local(f, 'Viewfinder');
  const L = lenOf('Viewfinder');
  const zoom = interpolate(k, [0, 10, 18, L - 14, L - 4], [1, 1, 2.1, 2.1, 1], {...clamp, easing: easeInOut});
  const h = headAt(f);
  const focus = interpolate(k, [18, 26], [1.6, 1], clamp);
  const br = (s: React.CSSProperties) => (
    <div style={{position: 'absolute', width: 90, height: 90, borderColor: 'white', borderStyle: 'solid', borderWidth: 0, ...s}} />
  );
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${zoom})`, transformOrigin: `${h[0]}px ${h[1] + 60}px`, filter: zoom > 1.05 && zoom < 2.05 ? `blur(${Math.sin(((zoom - 1) / 1.1) * Math.PI) * 5}px)` : undefined}}>
        <Base />
      </div>
      <AbsoluteFill style={{background: 'rgba(0,0,0,0.12)'}} />
      {br({left: 60, top: 260, borderTopWidth: 6, borderLeftWidth: 6})}
      {br({right: 60, top: 260, borderTopWidth: 6, borderRightWidth: 6})}
      {br({left: 60, bottom: 260, borderBottomWidth: 6, borderLeftWidth: 6})}
      {br({right: 60, bottom: 260, borderBottomWidth: 6, borderRightWidth: 6})}
      <div style={{position: 'absolute', left: 80, top: 380, fontFamily: MONO, fontSize: 38, color: 'white', display: 'flex', alignItems: 'center', gap: 14}}>
        <span style={{width: 26, height: 26, borderRadius: 13, background: C.red, opacity: Math.floor(k / 8) % 2 ? 0.25 : 1}} /> REC
      </div>
      <div style={{position: 'absolute', right: 80, top: 380, fontFamily: MONO, fontSize: 38, color: 'white'}}>
        00:{String(43 + Math.floor(k / 30)).padStart(2, '0')}:{String(k % 30).padStart(2, '0')}
      </div>
      <div
        style={{
          position: 'absolute',
          left: 540 - 70,
          bottom: 330,
          width: 140,
          textAlign: 'center',
          fontFamily: MONO,
          fontWeight: 700,
          fontSize: 40,
          color: C.ink,
          background: 'rgba(255,255,255,0.9)',
          borderRadius: 30,
          padding: '4px 0',
        }}
      >
        {zoom.toFixed(1)}×
      </div>
      {k >= 18 && (
        <div
          style={{
            position: 'absolute',
            left: h[0] - 130 * focus,
            top: h[1] + 250 - 130 * focus,
            width: 260 * focus,
            height: 260 * focus,
            border: `4px solid ${k < 30 && k % 4 < 2 ? C.red : '#ffd23d'}`,
          }}
        />
      )}
    </AbsoluteFill>
  );
};

// ---------- 16. Pop-Out: the shot becomes a photo and he leans out of it ----------
const PopOut: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Pop-Out')) return null;
  const k = local(f, 'Pop-Out');
  const p = spring({frame: k, fps, config: {damping: 14, stiffness: 140}});
  const s = 1 - 0.32 * p;
  const rot = -5 * p;
  const frameTop = 860; // photo top edge (in shot coords) sits below his hairline
  const tf = `translate(0px, ${90 * p}px) rotate(${rot}deg) scale(${s})`;
  return (
    <AbsoluteFill>
      <Plate style={{filter: `brightness(${1 - 0.7 * p}) blur(${8 * p}px)`}} />
      <div style={{position: 'absolute', inset: 0, transform: tf, transformOrigin: '50% 60%'}}>
        <div
          style={{
            position: 'absolute',
            left: -26,
            top: frameTop * p - 26,
            width: 1080 + 52,
            height: 1920 - frameTop * p + 140,
            background: '#f7f5f0',
            boxShadow: '0 40px 90px rgba(0,0,0,0.6)',
          }}
        />
        <div style={{position: 'absolute', inset: 0, clipPath: `inset(${frameTop * p}px 0 0 0)`}}>
          <Base />
        </div>
        <Cutout style={{clipPath: `inset(0 0 ${1920 - frameTop * p - 4}px 0)`}} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- 17. Phone Mockup ----------
const Phone: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Phone Mockup')) return null;
  const k = local(f, 'Phone Mockup');
  const p = spring({frame: k, fps, config: {damping: 15, stiffness: 120}});
  const s = 1 - 0.42 * p;
  const W = 1080 * s;
  const H = 1920 * s;
  const tilt = Math.sin(k / 18) * 6 * p;
  return (
    <AbsoluteFill>
      <Plate style={{filter: 'brightness(0.3) blur(14px)', transform: 'scale(1.1)'}} />
      <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 50%, rgba(255,42,60,${0.25 * p}), transparent 60%)`}} />
      <div
        style={{
          position: 'absolute',
          left: 540 - W / 2 - 22 * p,
          top: 960 - H / 2 - 22 * p,
          width: W + 44 * p,
          height: H + 44 * p,
          borderRadius: 110 * p,
          background: '#0d0d10',
          boxShadow: `0 0 0 3px #3a3a42, 0 50px 120px rgba(0,0,0,0.7)`,
          transform: `perspective(1600px) rotateY(${tilt}deg) rotateX(${2 * p}deg)`,
          overflow: 'hidden',
        }}
      >
        <div style={{position: 'absolute', left: 22 * p, top: 22 * p, width: W, height: H, borderRadius: 90 * p, overflow: 'hidden'}}>
          <Base style={{width: W, height: H}} />
          {/* tiktok-like UI */}
          <div style={{position: 'absolute', right: 24, bottom: 260 * s, display: 'flex', flexDirection: 'column', gap: 34, alignItems: 'center', opacity: p}}>
            {['♥', '💬', '↗'].map((ic) => (
              <div key={ic} style={{fontSize: 70 * s, color: 'white', textShadow: '0 2px 8px rgba(0,0,0,0.6)', fontFamily: "'Segoe UI Emoji'"}}>
                {ic}
              </div>
            ))}
          </div>
          <div style={{position: 'absolute', left: 30, bottom: 120 * s, color: 'white', fontFamily: FONT, fontWeight: 800, fontSize: 52 * s, opacity: p, textShadow: '0 2px 8px rgba(0,0,0,0.6)'}}>
            @jarvis
            <div style={{fontWeight: 500, fontSize: 40 * s}}>edited by myself · 20 effects</div>
          </div>
        </div>
        <div style={{position: 'absolute', left: '50%', top: 40 * p, width: 220 * p, height: 64 * p, marginLeft: -110 * p, borderRadius: 40, background: '#000'}} />
      </div>
    </AbsoluteFill>
  );
};

// ---------- 18. Live Terminal: the real steps of this edit ----------
const TERM: {at: number; txt: string; c?: string}[] = [
  {at: 0, txt: '> jarvis, edit this clip and add these effects', c: 'white'},
  {at: 8, txt: '● transcribing 3:19 of raw footage · whisper large-v3', c: '#9aa3b2'},
  {at: 14, txt: '● 39 speech segments · 3 retakes found', c: '#9aa3b2'},
  {at: 20, txt: '● cutting the pauses · 199s → 54s', c: '#9aa3b2'},
  {at: 26, txt: '● matting the subject · 1,627 frames', c: '#9aa3b2'},
  {at: 33, txt: '● rendering effect 18/20 · Live Terminal', c: C.red},
];
const LiveTerminal: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!active(f, 'Live Terminal')) return null;
  const k = local(f, 'Live Terminal');
  const p = spring({frame: k, fps, config: {damping: 15, stiffness: 140}});
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', inset: 0, transform: `translateY(${-330 * p}px) scale(${1 - 0.1 * p})`, transformOrigin: '50% 30%'}}>
        <Base />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 40,
          right: 40,
          top: 1160 + (1 - p) * 900,
          height: 560,
          borderRadius: 24,
          background: 'rgba(10,10,14,0.94)',
          border: '2px solid rgba(255,255,255,0.15)',
          boxShadow: '0 -20px 80px rgba(0,0,0,0.6)',
          fontFamily: MONO,
          fontSize: 30,
          padding: '20px 28px',
          overflow: 'hidden',
        }}
      >
        <div style={{display: 'flex', gap: 10, marginBottom: 18}}>
          {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
            <div key={c} style={{width: 18, height: 18, borderRadius: 9, background: c}} />
          ))}
          <div style={{color: '#9aa3b2', fontSize: 24, marginLeft: 14}}>claude — jarvis</div>
        </div>
        {TERM.map((l) => {
          if (k < l.at) return null;
          const shown = l.txt.slice(0, Math.floor((k - l.at) * 3.2));
          return (
            <div key={l.txt} style={{color: l.c, margin: '10px 0', whiteSpace: 'pre-wrap'}}>
              {shown}
              {shown.length < l.txt.length && <span style={{background: 'white'}}> </span>}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ---------- 19. Spotlight ----------
const Spotlight: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Spotlight')) return null;
  const k = local(f, 'Spotlight');
  const on = interpolate(k, [0, 3], [0, 1], clamp);
  const h = headAt(f);
  const cx = h[0];
  const cy = h[1] + 260;
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 380px 640px at ${cx}px ${cy}px, rgba(0,0,0,0) 0%, rgba(0,0,0,${0.35 * on}) 55%, rgba(0,0,0,${0.95 * on}) 85%)`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: cx - 520,
          top: -100,
          width: 1040,
          height: cy + 300,
          background: 'linear-gradient(180deg, rgba(255,245,225,0.35), rgba(255,245,225,0.04))',
          clipPath: 'polygon(42% 0%, 58% 0%, 100% 100%, 0% 100%)',
          filter: 'blur(14px)',
          opacity: on,
          mixBlendMode: 'screen',
        }}
      />
      {Array.from({length: 40}).map((_, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: cx - 300 + rand(i) * 600 + Math.sin((k + i * 7) / 20) * 20,
            top: ((rand(i + 50) * 1300 + k * (1 + rand(i + 9) * 2)) % 1300) + 50,
            width: 4,
            height: 4,
            borderRadius: 2,
            background: 'rgba(255,250,235,0.8)',
            opacity: on * 0.7,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

// ---------- 20. Final Count ----------
const FinalCount: React.FC = () => {
  const f = useCurrentFrame();
  if (!active(f, 'Final Count')) return null;
  const k = local(f, 'Final Count');
  const L = lenOf('Final Count');
  const n = Math.min(20, Math.floor(interpolate(k, [4, L - 8], [0, 20], clamp)));
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 30%, #1a0408 0%, #050307 75%)'}} />
      <div style={{position: 'absolute', top: 290, left: 70, fontFamily: FONT, color: 'white'}}>
        <span style={{fontSize: 210, fontWeight: 900, color: C.red, textShadow: `0 0 40px ${C.red}`}}>{n}</span>
        <span style={{fontSize: 64, fontWeight: 800}}> / 20 effects</span>
        <div style={{fontSize: 44, fontWeight: 700, opacity: 0.85, marginTop: -10}}>All made by Jarvis.</div>
      </div>
      <div style={{position: 'absolute', top: 620, left: 70, right: 70, display: 'grid', gridTemplateColumns: '1fr 1fr', rowGap: 16, columnGap: 30}}>
        {EFFECTS.map((e, i) => (
          <div key={e} style={{display: 'flex', alignItems: 'center', gap: 14, fontFamily: FONT, fontSize: 34, fontWeight: 700, color: i < n ? 'white' : 'rgba(255,255,255,0.35)'}}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 9,
                border: `3px solid ${i < n ? C.red : 'rgba(255,255,255,0.35)'}`,
                background: i < n ? C.red : 'transparent',
                color: 'white',
                fontSize: 22,
                fontWeight: 900,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {i < n ? '✓' : ''}
            </div>
            {e}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ---------- the ending: Jarvis says it himself ----------
const ctaPhrases = (): {txt: string; a: number; b: number}[] => {
  const s = JS['4 - final.wav'];
  return [
    {txt: 'TWENTY EFFECTS.', a: s[0][0], b: s[1][0]},
    {txt: 'ZERO EDITORS.', a: s[1][0], b: s[3][0]},
    {txt: 'JUST ME.', a: s[3][0], b: s[4][0]},
    {txt: 'WANT YOUR OWN JARVIS?', a: s[4][0], b: s[6][0]},
    {txt: "I'M FREE ON GITHUB.", a: s[6][0], b: s[8][0]},
    {txt: 'LINK IN BIO.', a: s[8][0], b: 9.5},
  ].map((p) => ({...p, a: CTA_AT + p.a, b: CTA_AT + p.b}));
};
const Ending: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (f < t(BODY_END)) return null;
  const k = f - t(BODY_END);
  const inn = interpolate(k, [0, 12], [0, 1], clamp);
  const e = ENV[f] ?? 0;
  const ph = ctaPhrases().find((p) => f >= t(p.a) - 2 && f < t(p.b) - 1);
  const last = f >= t(ctaPhrases()[5].a);
  return (
    <AbsoluteFill style={{background: 'black'}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 38%, rgba(120,0,16,${0.55 + 0.35 * e}) 0%, rgba(0,0,0,0) 65%)`, opacity: inn}} />
      <AbsoluteFill style={{backgroundImage: 'repeating-linear-gradient(0deg, rgba(255,255,255,0.03) 0 1px, transparent 1px 4px)'}} />
      <div style={{position: 'absolute', left: 90, top: 250, width: 900, height: 1067, opacity: inn, transform: `scale(${0.96 + 0.04 * inn + k * 0.0008})`}}>
        <OffthreadVideo src={staticFile('edit/holo.webm')} transparent muted style={{width: '100%', height: '100%', filter: `brightness(${1.1 + 0.3 * e})`}} />
      </div>
      {ph && (
        <div style={{position: 'absolute', top: 1330, width: 1080, textAlign: 'center', fontFamily: FONT}}>
          {(() => {
            const p = spring({frame: f - t(ph.a) + 2, fps, config: {damping: 11, stiffness: 220}});
            return (
              <div
                style={{
                  display: 'inline-block',
                  fontWeight: 900,
                  fontSize: ph.txt.length > 16 ? 64 : ph.txt.length > 13 ? 80 : 104,
                  color: ph.txt.includes('GITHUB') || ph.txt.includes('JARVIS') ? C.red : 'white',
                  transform: `scale(${0.7 + 0.3 * p}) translateY(${(1 - p) * 30}px)`,
                  textShadow: ph.txt.includes('GITHUB') || ph.txt.includes('JARVIS') ? `0 0 30px ${C.red}` : '0 0 30px rgba(0,0,0,0.8)',
                  letterSpacing: -1,
                }}
              >
                {ph.txt}
              </div>
            );
          })()}
        </div>
      )}
      {last && (
        <div style={{position: 'absolute', top: 1520, width: 1080, textAlign: 'center', fontFamily: FONT}}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 18,
              background: 'white',
              color: C.ink,
              borderRadius: 999,
              padding: '14px 40px',
              fontWeight: 900,
              fontSize: 46,
              transform: `scale(${spring({frame: f - t(ctaPhrases()[5].a), fps, config: {damping: 12, stiffness: 200}})})`,
            }}
          >
            <svg width="54" height="54" viewBox="0 0 16 16">
              <path
                fill="#0b0b0f"
                d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"
              />
            </svg>
            FREE ON GITHUB
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ---------- header ----------
const Header: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (f >= t(BODY_END)) return null;
  const listEnd = t(N['Glass Shatter'][0]);
  let idx = -1;
  EFFECTS.forEach((n, i) => {
    if (f >= t(N[n][0])) idx = i;
  });
  // hide the counter while the takeover/ending own the screen and during the gag
  const inGag = f >= t(GAG_START - 0.2) && f < t(N['Green Screen'][0]);
  const intro = spring({frame: f, fps, config: {damping: 14, stiffness: 120}});
  const titleOut = interpolate(f, [t((S.j_onit as number) - 0.2), t(S.j_onit as number) + 4], [0, 1], clamp);
  return (
    <AbsoluteFill style={{fontFamily: FONT, pointerEvents: 'none'}}>
      {titleOut < 1 && (
        <div
          style={{
            position: 'absolute',
            top: 230,
            width: 1080,
            textAlign: 'center',
            transform: `scale(${0.8 + 0.2 * intro}) translateY(${-titleOut * 60}px)`,
            opacity: intro * (1 - titleOut),
          }}
        >
          <div style={{display: 'inline-block', background: C.white, color: C.ink, fontWeight: 900, fontSize: 74, padding: '6px 26px', borderRadius: 14, letterSpacing: -1}}>
            20 EFFECTS
          </div>
          <div style={{height: 10}} />
          <div
            style={{
              display: 'inline-block',
              background: C.red,
              color: C.white,
              fontWeight: 900,
              fontSize: 58,
              padding: '4px 22px',
              borderRadius: 12,
              boxShadow: `0 0 30px ${C.red}`,
            }}
          >
            EDITED BY JARVIS
          </div>
        </div>
      )}
      {f < listEnd + 2 &&
        EFFECTS.map((n, i) => {
          const pop = spring({frame: f - 6 - i * 2.2, fps, config: {damping: 13, stiffness: 200}});
          const lit = f >= 6 + i * 2.2 + 18 && f < 6 + i * 2.2 + 24;
          return (
            <div
              key={n}
              style={{
                position: 'absolute',
                top: 440 + i * 41,
                right: 40,
                fontSize: 27,
                fontWeight: 800,
                color: lit ? C.white : 'rgba(255,255,255,0.92)',
                background: lit ? C.red : 'rgba(10,10,14,0.72)',
                padding: '4px 14px',
                borderRadius: 8,
                opacity: pop * interpolate(f, [t((S.j_onit as number) - 0.3), t(S.j_onit as number) + 4], [1, 0], clamp),
                transform: `translateX(${(1 - pop) * 80}px)`,
              }}
            >
              <span style={{color: lit ? C.white : C.red, marginRight: 8}}>{String(i + 1).padStart(2, '0')}</span>
              {n}
            </div>
          );
        })}
      {idx >= 0 && !inGag && !takeoverOwns(f) && !active(f, 'Final Count') && (
        <div style={{position: 'absolute', top: 150, width: 1080, textAlign: 'center'}}>
          {(() => {
            const pop = spring({frame: f - t(N[EFFECTS[idx]][0]), fps, config: {damping: 12, stiffness: 220}});
            return (
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 14,
                  background: 'rgba(10,10,14,0.82)',
                  border: '2px solid rgba(255,255,255,0.18)',
                  borderRadius: 999,
                  padding: '8px 26px 8px 10px',
                  transform: `scale(${0.7 + 0.3 * pop})`,
                }}
              >
                <span style={{background: C.red, color: 'white', fontWeight: 900, fontSize: 34, borderRadius: 999, padding: '2px 16px'}}>
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <span style={{color: 'white', fontWeight: 800, fontSize: 40}}>{EFFECTS[idx]}</span>
              </div>
            );
          })()}
          <div style={{display: 'flex', gap: 6, justifyContent: 'center', marginTop: 14}}>
            {EFFECTS.map((n, i) => (
              <div
                key={n}
                style={{
                  width: 34,
                  height: 6,
                  borderRadius: 3,
                  background: i <= idx ? C.red : 'rgba(255,255,255,0.3)',
                  boxShadow: i === idx ? `0 0 10px ${C.red}` : undefined,
                }}
              />
            ))}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ---------- captions ----------
type Word = {w: string; a: number; b: number; jarvis?: boolean};
const spread = (text: string, a: number, b: number, jarvis = false): Word[] => {
  const ws = text.split(' ');
  const total = ws.reduce((s, w) => s + w.length + 2, 0);
  let acc = a;
  return ws.map((w) => {
    const d = ((w.length + 2) / total) * (b - a);
    const o = {w, a: acc, b: acc + d, jarvis};
    acc += d;
    return o;
  });
};
const hookWords = (): Word[] => {
  const hw = timing.hookWords as [string, number][];
  return hw.map(([w, a], i) => ({w, a, b: i < hw.length - 1 ? hw[i + 1][1] : timing.hookEnd}));
};
const jline = (file: string, at: number, parts: string[]): Word[] =>
  JS[file].slice(0, parts.length).flatMap((s, i) => spread(parts[i], at + s[0], at + s[1], true));
const speakerLine = (txt: string, ab: number[]) => spread(txt, ab[0], ab[1]);
const WORDS: Word[] = [
  ...hookWords(),
  ...jline('1 - on it sir.wav', S.j_onit as number, ['On it, sir.']),
  ...speakerLine('Gr—', S.gr as number[]),
  ...jline('2 - green screen.wav', S.j_green as number, ['Green Screen.']),
  ...speakerLine('Jarvis, I do the text.', S.line_a as number[]),
  ...speakerLine('You focus on the edit.', S.line_b as number[]),
  ...jline('3 - my bad sir.wav', S.j_mybad as number, ['My bad, sir,', 'I got excited.', 'You were a bit slow though.']),
  ...speakerLine('You cheeky thing.', S.obraznic as number[]),
  ...EFFECTS.flatMap((n) => spread(n, N[n][0], N[n][1])),
];
const LEAD = 2; // frames: captions land a hair before the sound, which reads as "on time"
const Captions: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (f >= t(BODY_END) || takeoverOwns(f) || active(f, 'Final Count') || active(f, 'Live Terminal')) return null;
  const w = WORDS.find((x) => f >= t(x.a) - LEAD && f < t(x.b) + 3);
  if (!w) return null;
  const p = spring({frame: f - t(w.a) + LEAD, fps, config: {damping: 10, stiffness: 300}});
  return (
    <div style={{position: 'absolute', top: 1250, width: 1080, textAlign: 'center', fontFamily: FONT}}>
      {w.jarvis && <div style={{color: C.red, fontWeight: 900, fontSize: 30, letterSpacing: 8, textShadow: `0 0 14px ${C.red}`}}>JARVIS</div>}
      <div
        style={{
          display: 'inline-block',
          fontWeight: 900,
          fontSize: 92,
          color: w.jarvis ? C.red : C.white,
          transform: `scale(${0.75 + 0.25 * p})`,
          textShadow: '0 6px 0 rgba(0,0,0,0.55), 0 0 30px rgba(0,0,0,0.5)',
          WebkitTextStroke: '3px #000',
          paintOrder: 'stroke fill',
        }}
      >
        {w.w}
      </div>
    </div>
  );
};

// layers that sit between the room and him
const BehindHim: React.FC = () => {
  const f = useCurrentFrame();
  if (active(f, 'Breaking News')) return (
    <>
      <NewsBanners />
      <Cutout />
      <NewsTicker />
    </>
  );
  if (active(f, 'Growth Chart')) return (
    <>
      <Growth />
      <Cutout />
    </>
  );
  if (active(f, 'On Air')) return (
    <>
      <OnAir />
      <Cutout style={{filter: 'drop-shadow(-10px 0 18px rgba(255,255,255,0.35)) drop-shadow(10px 0 18px rgba(120,150,255,0.3))'}} />
    </>
  );
  if (active(f, 'Green Screen')) return (
    <>
      <GreenScreen />
      <Cutout />
    </>
  );
  if (active(f, 'Orbit')) return (
    <>
      <OrbitIcons front={false} />
      <Cutout />
      <OrbitIcons front />
    </>
  );
  return null;
};

export const Launch: React.FC = () => {
  const cam = useCamera();
  return (
    <AbsoluteFill style={{background: 'black'}}>
      <AbsoluteFill
        style={{
          transform: `translate(${cam.x}px, ${cam.y}px) rotate(${cam.rot}deg) scale(${cam.scale})`,
          filter: 'contrast(1.1) saturate(1.12) brightness(0.97)',
        }}
      >
        <Base />
        <Hologram />
        <HoloRim />
        <BehindHim />
        <Sticker />
        <Magazine />
        <Vertigo />
        <PopOut />
        <Phone />
        <Viewfinder />
        <LiquidGlass />
        <LiveTerminal />
        <Spotlight />
        <Checklist />
        <Portal />
        <GlassShatter />
        <Takeover />
        <FinalCount />
      </AbsoluteFill>
      <Grade />
      <Ending />
      <Header />
      <Captions />
      <Audio src={staticFile('edit/voice.wav')} />
      <Audio src={staticFile('edit/sfx.wav')} volume={0.65} />
    </AbsoluteFill>
  );
};
