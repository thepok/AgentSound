// The making-of page: MO.frame(f) draws frame f (a pure function of f) and returns it as an image data URL.
// project.json (Python: agentsound/makingof) holds the timeline and the song's data; features.* the audio analysis.

import { Renderer, SCENE_IDS, mulberry } from './gl.js';
import * as U from './ui.js';

const { SERIF, SERIF_TEXT, SANS, MONO, clamp, lerp, eOut, eInOut, eBack, ramp, vis, rgba, text, measure, paragraph,
  rrect, panel, chip, icon, wrap } = U;

const MO = (window.MO = {});
window.MO_STATE = 'loading';
let P, F, R, ui, g, cover = null, pal, palHex, W, H, fps, songBeatTab, trackIndex, hookNotes;
const LW = 1920, LH = 1080;

// ------------------------------------------------------------------------------------------------ setup

async function init() {
  P = await (await fetch('/data/project.json')).json();
  const fm = await (await fetch('/data/features.json')).json();
  const fb = await (await fetch('/data/features.bin')).arrayBuffer();
  const T = { Uint8Array, Float32Array, Int8Array };
  F = { meta: fm, onsets: fm.onsets, frames: fm.frames };
  for (const l of fm.layout) {
    const C = T[l.type];
    F[l.name] = new C(fb, l.offset, l.bytes / C.BYTES_PER_ELEMENT);
  }
  W = P.width; H = P.height; fps = P.fps;
  const canvas = document.getElementById('c');
  canvas.width = W; canvas.height = H;
  R = new Renderer(canvas, W, H);
  ui = document.createElement('canvas'); ui.width = W; ui.height = H;
  g = ui.getContext('2d');
  if (P.cover) {
    cover = new Image(); cover.src = `/song/${P.cover}`;
    await new Promise((res, rej) => { if (cover.complete && cover.naturalWidth) res(); cover.onload = res; cover.onerror = () => rej(new Error('cover.png did not load')); });
    R.setCover(cover);
  }
  pal = palette(cover);
  palHex = Object.fromEntries(Object.entries(pal).map(([k, v]) => [k, U.rgb01ToHex(v)]));
  for (const f of [`40px ${SERIF}`, `40px ${SANS}`, `40px ${MONO}`, `italic 40px ${SERIF_TEXT}`]) { try { await document.fonts.load(f); } catch { /* local */ } }
  // song beats (for the synthwave grid): integrate the tempo curve
  songBeatTab = [[0, 0]];
  for (let i = 1; i < P.song.tempo.length; i++) {
    const [t0, b0] = P.song.tempo[i - 1], [t1] = P.song.tempo[i];
    songBeatTab.push([t1, songBeatTab[i - 1][1] + (t1 - t0) * b0 / 60]);
  }
  // notes for the highway: t0, dur, pitch, vel | r, g, b, flags(hook + 2*track)
  trackIndex = {};
  P.tracks.forEach((t, i) => { trackIndex[t.id] = i; });
  const occ = P.hook.occurrences;
  const inHook = (tid, t) => occ.some((o) => o.tracks.includes(tid) && t >= o.t - 0.05 && t <= o.end + 0.05);
  const arr = [];
  const pitches = [];
  const HW_SKIP = ['drums', 'fx', 'timpani', 'bass'];
  P.tracks.forEach((tr) => { if (!HW_SKIP.includes(tr.family)) for (const n of tr.notes) pitches.push(n[2]); });
  pitches.sort((a, b) => a - b);
  const pmin = pitches.length ? pitches[Math.floor(pitches.length * 0.04)] : 36;
  const pmax = pitches.length ? pitches[Math.floor(pitches.length * 0.97)] : 96;
  P.tracks.forEach((tr, ti) => {
    if (HW_SKIP.includes(tr.family)) return;
    const c = U.hexToRgb01(tr.color);
    for (const [t0, d, p, v] of tr.notes) {
      if (p < pmin - 2 || p > pmax + 2) continue;
      arr.push(t0, Math.min(d, 3.0), p, v, c[0], c[1], c[2], (inHook(tr.id, t0) ? 1 : 0) + 2 * ti);
    }
  });
  R.setNotes(new Float32Array(arr));
  R.pRange = [pmin - 3, pmax + 3];
  hookNotes = new Set();
  window.MO_STATE = 'ready';
}

init().catch((e) => { window.MO_STATE = `error: ${e.stack || e}`; });

function palette(img) {
  // dark background, the most frequent saturated hue (accent), a second hue, the light tone
  const def = { C0: [0.03, 0.035, 0.06], C1: [0.95, 0.72, 0.35], C2: [0.45, 0.25, 0.75], C3: [0.95, 0.92, 0.85] };
  if (!img) return def;
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const x = c.getContext('2d'); x.drawImage(img, 0, 0, 64, 64);
  const d = x.getImageData(0, 0, 64, 64).data;
  const hues = new Array(36).fill(0), sums = Array.from({ length: 36 }, () => [0, 0, 0, 0]);
  let dark = [0, 0, 0, 0], light = [0, 0, 0, 0];
  for (let i = 0; i < d.length; i += 4) {
    const r = d[i] / 255, gg = d[i + 1] / 255, b = d[i + 2] / 255;
    const mx = Math.max(r, gg, b), mn = Math.min(r, gg, b), l = (mx + mn) / 2, s = mx - mn;
    if (l < 0.18) { dark[0] += r; dark[1] += gg; dark[2] += b; dark[3]++; }
    if (l > 0.75 && s < 0.35) { light[0] += r; light[1] += gg; light[2] += b; light[3]++; }
    if (s > 0.18 && mx > 0.25) {
      let h = mx === r ? ((gg - b) / s) % 6 : mx === gg ? (b - r) / s + 2 : (r - gg) / s + 4;
      h = ((h * 60) + 360) % 360;
      const k = Math.floor(h / 10);
      const w = s * mx;
      hues[k] += w; sums[k][0] += r * w; sums[k][1] += gg * w; sums[k][2] += b * w; sums[k][3] += w;
    }
  }
  const avg = (a) => (a[3] ? [a[0] / a[3], a[1] / a[3], a[2] / a[3]] : null);
  const order = hues.map((v, i) => [v, i]).sort((a, b) => b[0] - a[0]);
  const pick = (k) => { const s = sums[k]; return s[3] ? [s[0] / s[3], s[1] / s[3], s[2] / s[3]] : null; };
  let C1 = order[0][0] > 0 ? pick(order[0][1]) : null;
  let C2 = null;
  for (const [v, i] of order.slice(1)) {
    if (v <= order[0][0] * 0.08) break;
    const dh = Math.min(Math.abs(i - order[0][1]), 36 - Math.abs(i - order[0][1]));
    if (dh >= 5) { C2 = pick(i); break; }
  }
  const boost = (c, k) => { const m = Math.max(...c, 1e-3); return c.map((x) => Math.min(1, x / m * k)); };
  C1 = C1 ? boost(C1, 0.98) : def.C1;
  if (!C2) {   // one hue on the cover: a deep, cooler partner for depth
    const [r, gg, b] = C1;
    C2 = [b * 0.55 + 0.1, r * 0.25 + 0.08, gg * 0.35 + 0.3];
    if (r > b && r > 0.6 && gg > 0.4) C2 = [0.55, 0.16, 0.12];   // gold -> ember red
  } else C2 = boost(C2, 0.85);
  const C0 = avg(dark) ? avg(dark).map((v) => Math.min(0.08, v * 0.9 + 0.01)) : def.C0;
  const C3 = avg(light) || [Math.min(1, C1[0] * 0.3 + 0.7), Math.min(1, C1[1] * 0.3 + 0.68), Math.min(1, C1[2] * 0.3 + 0.62)];
  return { C0, C1, C2, C3 };
}

// ------------------------------------------------------------------------------------------------ time and audio

function chapterAt(t) {
  const cs = P.chapters;
  for (let i = 0; i < cs.length; i++) if (t < cs[i].t1 || i === cs.length - 1) return cs[i];
  return cs[cs.length - 1];
}
function segAt(t, kinds) {
  for (const s of P.segments) if (s.v0 <= t && t < s.v1 && (!kinds || kinds.includes(s.kind))) return s;
  return null;
}
function envGain(env, x) {
  if (!env || !env.length) return 0;
  if (x <= env[0][0]) return env[0][1];
  for (let i = 1; i < env.length; i++) {
    if (x <= env[i][0]) { const [a, ga] = env[i - 1], [b, gb] = env[i]; return b > a ? ga + (gb - ga) * (x - a) / (b - a) : gb; }
  }
  return env[env.length - 1][1];
}
function songBeat(st) {
  const T = songBeatTab;
  let lo = 0, hi = T.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m][0] <= st) lo = m; else hi = m; }
  const [t0, b0] = T[lo];
  const bpm = P.song.tempo[Math.min(lo, P.song.tempo.length - 1)][1];
  return b0 + (st - t0) * bpm / 60;
}
function onsetsBefore(t) {   // index of the first onset after t
  const O = F.onsets; let lo = 0, hi = O.length;
  while (lo < hi) { const m = (lo + hi) >> 1; if (O[m].t <= t) lo = m + 1; else hi = m; }
  return lo;
}
function audioAt(t) {
  // the song audio playing at video time t (segments) -> features; gain = its envelope (linear)
  const seg = segAt(t, ['song', 'excerpt', 'solo', 'bed', 'act', 'clip']);
  const A = { on: false, st: null, lin: 0, bands: new Uint8Array(48), level: 0, loud: -60, slow: -40, kick: 0, onset: 0, width: 0, beat: 0, seg };
  if (!seg || seg.features === false) return A;
  const st = seg.s0 + (t - seg.v0);
  const fi = clamp(Math.round(st * fps), 0, F.frames - 1);
  const lin = Math.pow(10, envGain(seg.env, t - seg.v0) / 20);
  A.on = true; A.st = st; A.lin = lin;
  A.bands = F.bands.subarray(fi * 48, fi * 48 + 48);
  A.loud = F.loud[fi]; A.slow = F.slow[fi]; A.width = F.width[fi];
  A.level = clamp((A.loud + 44) / 32) * clamp(lin * 1.4);
  let kick = 0, on = 0;
  const O = F.onsets;
  for (let i = onsetsBefore(st) - 1; i >= 0 && st - O[i].t < 0.6; i--) {
    const e = O[i].s * Math.exp(-(st - O[i].t) * 8);
    if (O[i].kind === 'lo') kick += e; on += e;
  }
  A.kick = clamp(kick * clamp(lin * 1.5)); A.onset = clamp(on * clamp(lin * 1.5));
  A.beat = songBeat(st);
  return A;
}
function bursts(A, sceneName) {
  const out = new Float32Array(64);
  if (!A.on) return out;
  const O = F.onsets, st = A.st;
  let k = 0;
  for (let i = onsetsBefore(st) - 1; i >= 0 && k < 16 && st - O[i].t < 2.2; i--) {
    if (O[i].s < 0.3) continue;
    const r = mulberry(O[i].f * 7 + 3);
    const ring = sceneName === 'ring';
    out[k * 4] = st - O[i].t; out[k * 4 + 1] = O[i].s * clamp(A.lin * 1.5);
    out[k * 4 + 2] = ring ? 0 : (r() - 0.5) * 1.8; out[k * 4 + 3] = ring ? 0 : (r() - 0.5) * 0.9;
    k++;
  }
  return out;
}

// ------------------------------------------------------------------------------------------------ frame

MO.frame = (f, mime = 'image/jpeg', q = 0.94) => {
  draw(f);
  return document.getElementById('c').toDataURL(mime, q);
};
MO.debug = (f) => { const t = f / fps; const c = chapterAt(t); return { t, chapter: c.id, audio: audioAt(t).st }; };

function sceneFor(t, c, A) {
  // -> {SA, SB, MIXB, name, highway, dim, particles, intens}
  const base = { cold: 'nebula', team: 'nebula', blueprint: 'scope', tracks: 'nebula', performance: 'nebula', crisis: 'ink', tried: 'scope', end: 'nebula', song: 'nebula' };
  const dims = { cold: 0.55, team: 0.42, blueprint: 0.38, tracks: 0.5, performance: 0.45, crisis: 0.5, tried: 0.45, end: 0.5, song: 1 };
  if (c.kind === 'act') {
    const n = c.scene || 'nebula';
    return { SA: SCENE_IDS[n], SB: 0, MIXB: 0, name: n, highway: c.highway ? 1 : 0, dim: 1, particles: 1, intens: 0.6 };
  }
  if (c.kind !== 'song' || !A.on || c.song == null || t < c.song.v0) {
    const n = base[c.kind] || 'nebula';
    let hw = 0;
    return { SA: SCENE_IDS[n], SB: 0, MIXB: 0, name: n, highway: hw, dim: dims[c.kind] ?? 0.5, particles: 0.7, intens: 0.5 };
  }
  const st = A.st, S = P.scenes;
  let i = S.findIndex((s) => st >= s.s0 && st < s.s1);
  if (i < 0) i = st < S[0].s0 ? 0 : S.length - 1;
  const cur = S[i], X = 1.6;
  let SA = SCENE_IDS[cur.scene], SB = SA, MIXB = 0, hw = cur.highway ? 1 : 0, name = cur.scene;
  if (i + 1 < S.length && st > S[i + 1].s0 - X / 2) {
    const nx = S[i + 1]; MIXB = eInOut((st - (nx.s0 - X / 2)) / X); SB = SCENE_IDS[nx.scene];
    hw = lerp(hw, nx.highway ? 1 : 0, MIXB);
    if (MIXB > 0.5) name = nx.scene;
  } else if (i > 0 && st < cur.s0 + X / 2) {
    const pv = S[i - 1]; SB = SA; SA = SCENE_IDS[pv.scene]; MIXB = eInOut((st - (cur.s0 - X / 2)) / X);
    hw = lerp(pv.highway ? 1 : 0, hw, MIXB);
  }
  return { SA, SB, MIXB: SA === SB ? 0 : MIXB, name, highway: hw, dim: 1, particles: 1, intens: cur.intensity };
}

function draw(f) {
  const t = f / fps;
  const c = chapterAt(t);
  const u = t - c.t0, D = c.t1 - c.t0;
  const A = audioAt(t);
  const sc = sceneFor(t, c, A);
  const fadeIn = c.id === 'cold' ? 1.2 : 0.45;
  const fade = Math.min(1, clamp(u / fadeIn), clamp((c.t1 - t) / 0.45));
  // ---- UI
  g.setTransform(W / LW, 0, 0, H / LH, 0, 0);
  g.clearRect(0, 0, LW, LH);
  g.globalAlpha = 1;
  const ctx = { t, u, D, c, A, sc, f };
  const fn = CH[c.kind || c.id];
  if (fn) fn(ctx);
  if (!(c.kind === 'song' && c.song && t >= c.song.v0 - 0.2)) captions(ctx);
  // ---- GL state
  const hwRange = R.pRange || [36, 96];
  const s = {
    T: A.on ? A.st : t, BEAT: A.beat, LEVEL: ['song', 'act'].includes(c.kind) ? A.level : 0.25 + A.level * 0.9, KICK: A.kick, ONSET: A.onset,
    SLOW: clamp((A.slow + 36) / 22), WIDTH: A.width, INTENS: sc.intens, DIM: sc.dim, MIXB: sc.MIXB, SA: sc.SA, SB: sc.SB,
    SEED: 3.7, pal, bands: A.bands, highway: sc.highway, particles: sc.particles,
    hw: { now: A.on ? A.st : 0, ahead: 5.5, pmin: hwRange[0], pmax: hwRange[1], hy: 0.12, k: 1.15, d0: 1.35, spread: 2.6 },
    bursts: bursts(A, sc.name), ring: sc.name === 'ring' ? 0.27 : 0,
    BLOOM: ['song', 'act'].includes(c.kind) ? 0.45 + 0.4 * A.level : 0.45, THR: 0.62,
    CA: 0.001 + (['song', 'act'].includes(c.kind) ? 0.004 * A.kick * (0.4 + sc.intens) : 0) + (ctx.caSpike || 0),
    FADE: fade, WARM: A.on ? clamp((A.slow + 34) / 20) : 0.45, GRAIN: 0.032, FRAME: f % 997, VIG: 0.62,
  };
  s.mask = ctx.mask ? ctx.mask.map((id) => trackIndex[id]).filter((x) => x !== undefined) : null;
  R.draw(s, ui);
}

// ------------------------------------------------------------------------------------------------ shared UI

const K = {   // colours
  ink: '#f2efe8', dim: '#aab0c0', faint: '#6c7285', red: '#ff4d6a', green: '#52e0a0', amber: '#ffb347',
};
const roleColor = (r) => (P.roleColors && P.roleColors[r]) || '#f5c451';
const sevColor = (s) => ({ blocker: K.red, major: K.amber, minor: '#ffd84d' }[s] || K.dim);

function header(ctx) {
  // the chapter's title: big for 2.6 s, then a small kicker top-left
  const { u, c } = ctx;
  const numbered = P.chapters.filter((x) => !['cold', 'song', 'end'].includes(x.kind));
  const idx = numbered.indexOf(c) + 1;
  const big = 1 - ramp(u, 2.2, 3.0);
  const num = String(idx).padStart(2, '0');
  if (big > 0.001) {
    const a = vis(u, 0.15, 3.0, 0.6, 0.8);
    const x = 140, y = 520;
    text(g, num, x, y - 70, { font: SANS, size: 30, weight: 300, color: palHex.C1, track: 6, alpha: a });
    const w = eOut(ramp(u, 0.2, 1.2));
    g.save(); g.globalAlpha = a; g.fillStyle = palHex.C1; g.fillRect(x, y - 52, 90 * w, 2); g.restore();
    text(g, c.title, x - 4 + 30 * (1 - eOut(ramp(u, 0.1, 1.0))), y + 40, { font: SERIF, size: 104, color: K.ink, alpha: a });
  }
  const sm = ramp(u, 2.6, 3.4) * (1 - ramp(u, ctx.D - 0.5, ctx.D));
  if (sm > 0.001) {
    text(g, `${num}  ·  ${c.title.toUpperCase()}`, 80, 78, { font: SANS, size: 20, weight: 600, color: palHex.C1, track: 5, alpha: sm * 0.9 });
    text(g, P.title, LW - 80, 78, { font: SERIF, size: 26, color: K.dim, align: 'right', alpha: sm * 0.7 });
  }
  return big;
}

function captions(ctx) {
  const { t } = ctx;
  const cap = P.captions.find((x) => t >= x.t0 - 0.15 && t < x.t1 + 0.35);
  if (!cap) return;
  const a = Math.min(clamp((t - cap.t0 + 0.15) / 0.25), clamp((cap.t1 + 0.35 - t) / 0.3));
  const o = { font: SANS, size: 36, weight: 400, color: K.ink };
  const lines = wrap(g, cap.text, 1420, o);
  const shown = lines.slice(0, 3);
  const lh = 48, h = shown.length * lh + 34;
  const y0 = LH - 52 - h;
  const wmax = Math.max(...shown.map((l) => measure(g, l, o)));
  const x0 = LW / 2 - wmax / 2 - 36;
  g.save(); g.globalAlpha = a * 0.72;
  rrect(g, x0, y0, wmax + 72, h, 22); g.fillStyle = 'rgba(6,7,12,0.82)'; g.fill();
  g.restore();
  if (cap.voice === 'ar') chip(g, 'A&R', x0 + 14, y0 - 16, K.red, { size: 18, alpha: a });
  shown.forEach((l, i) => text(g, l, LW / 2, y0 + 17 + 36 + i * lh, { ...o, align: 'center', alpha: a }));
}

function fmtT(s) { const m = Math.floor(s / 60), x = s - m * 60; return `${m}:${x < 10 ? '0' : ''}${x.toFixed(0)}`; }
function sectionAt(st) { return P.song.sections.find((s) => st >= s.start && st < s.end) || P.song.sections[P.song.sections.length - 1]; }
const prettyName = (n) => n.replace(/_/g, ' ').replace(/([a-z])(\d)/g, '$1 $2');
function captionAt(ctx, re) { return P.captions.find((x) => x.chapter === ctx.c.id && re.test(x.text)); }

// ------------------------------------------------------------------------------------------------ chapters

const CH = {};

CH.cold = (ctx) => {
  const { u, D } = ctx;
  const tc = Math.max(D - 7.5, 8);                 // the title card
  const q = P.wish.quote || P.title;
  const turns = q.split(/\s+->\s+/).map((s) => s.trim()).filter(Boolean);
  const total = turns.join('').length;
  const cps = Math.max(34, total / 7.0);
  const a = vis(u, 0.6, tc + 0.2, 0.8, 0.8);
  if (a > 0) {
    const o = { font: MONO, size: turns.length > 1 ? 32 : 32, color: K.ink, lineHeight: 46 };
    const bw = 1240, x = LW / 2 - bw / 2;
    const blocks = turns.map((s) => ({ s, lines: wrap(g, s, bw - 110, o) }));
    const hs = blocks.map((b) => b.lines.length * 46 + 44);
    const H = hs.reduce((p, c) => p + c, 0) + (blocks.length - 1) * 26;
    let y = Math.max(170, 470 - H / 2);
    text(g, 'THE WISH', x, y - 28, { size: 20, weight: 600, color: palHex.C1, track: 6, alpha: a });
    let typedAll = Math.floor(clamp((u - 1.0) * cps, 0, total));
    blocks.forEach((b, bi) => {
      if (typedAll <= 0 && bi > 0) return;
      const h = hs[bi];
      const appear = eOut(clamp(typedAll / 6));
      const bx = x + (bi % 2) * 60;
      panel(g, bx, y, bw - 60, h, { alpha: a * appear, border: rgba(palHex.C1, 0.4), r: 22 });
      let left = Math.min(typedAll, b.s.length);
      const typingHere = typedAll < b.s.length;
      b.lines.forEach((l, i) => {
        const s = l.slice(0, Math.max(0, left));
        left -= l.length + 1;
        if (s) text(g, s, bx + 40, y + 52 + i * 46, { ...o, alpha: a });
        if (typingHere && left < 0 && left > -l.length - 2) {
          const cx = bx + 40 + measure(g, s, o) + 4;
          if (Math.floor(u * 2.2) % 2 === 0) { g.save(); g.globalAlpha = a; g.fillStyle = palHex.C1; g.fillRect(cx, y + 26 + i * 46, 14, 32); g.restore(); }
          left = -1e9;
        }
      });
      typedAll -= b.s.length;
      y += h + 26;
    });
  }
  // title card
  const b = ramp(u, tc, tc + 1.4);
  if (b > 0) {
    const size = 520, cx = 300 + size / 2, cy = LH / 2 - 20;
    if (cover) {
      const k = 1 + 0.04 * ramp(u, tc, D);
      g.save(); g.globalAlpha = eOut(b);
      const s2 = size * k * (0.94 + 0.06 * eOut(b));
      g.drawImage(cover, cx - s2 / 2, cy - s2 / 2, s2, s2);
      g.restore();
    }
    const x = 920, a2 = eOut(ramp(u, tc + 0.5, tc + 1.8));
    text(g, 'THE MAKING OF', x, cy - 140, { size: 24, weight: 600, color: palHex.C1, track: 8, alpha: a2 });
    const tl = wrap(g, P.title, 880, { font: SERIF, size: 108 });
    tl.forEach((l, i) => text(g, l, x + 20 * (1 - a2), cy - 30 + i * 112, { font: SERIF, size: 108, color: K.ink, alpha: a2 }));
    const meta = [P.genre, fmtT(P.song.duration), `${P.song.sections.length} sections`, `${P.song.bars} bars`].filter(Boolean).join('   ·   ');
    text(g, meta, x, cy - 30 + tl.length * 112 + 20, { size: 28, color: K.dim, track: 1.5, alpha: eOut(ramp(u, tc + 1.0, tc + 2.2)) });
  }
};

CH.team = (ctx) => {
  const { u } = ctx;
  header(ctx);
  const cards = P.team;
  const n = cards.length, cols = n > 8 ? Math.ceil(n / 2) : Math.min(4, n), rows = Math.ceil(n / cols);
  const cw = Math.min(330, (LW - 200 - (cols - 1) * 26) / cols), ch = 250;
  const x0 = (LW - (cols * cw + (cols - 1) * 26)) / 2, y0 = rows > 1 ? 190 + (2 - rows) * 60 : 330;
  const cap = P.captions.filter((x) => x.chapter === 'team');
  const nowCap = cap.find((x) => ctx.t >= x.t0 && ctx.t < x.t1);
  cards.forEach((cd, i) => {
    const t0 = 3.0 + i * 0.42;
    const a = eOut(ramp(u, t0, t0 + 0.7));
    if (a <= 0) return;
    const col = i % cols, row = Math.floor(i / cols);
    const x = x0 + col * (cw + 26), y = y0 + row * (ch + 26) + 30 * (1 - a);
    const color = roleColor(cd.role);
    let hl = 0;
    if (nowCap) {
      const words = cd.title.toLowerCase().split(' ');
      if (words.every((w) => nowCap.text.toLowerCase().includes(w.replace('&', '&')))) hl = vis(ctx.t, nowCap.t0, nowCap.t1, 0.3, 0.4);
    }
    const flash = 1 - ramp(u, t0 + 0.2, t0 + 1.4);
    panel(g, x, y, cw, ch, { alpha: a, border: rgba(color, 0.35 + 0.5 * Math.max(flash, hl)), lineWidth: 1.5 + 1.5 * hl, r: 20 });
    g.save(); g.globalAlpha = a * (0.16 + 0.25 * hl); g.fillStyle = color; rrect(g, x, y, cw, 6, 3); g.fill(); g.restore();
    g.save(); g.globalAlpha = a;
    g.beginPath(); g.arc(x + 58, y + 64, 36, 0, 7); g.fillStyle = rgba(color, 0.12 + 0.15 * hl); g.fill();
    g.lineWidth = 1.5; g.strokeStyle = rgba(color, 0.7); g.stroke();
    g.restore();
    g.save(); g.globalAlpha = a; icon(g, cd.role, x + 58, y + 64, 22, color); g.restore();
    const ts = Math.min(30, 30 * (cw - 130) / Math.max(1, measure(g, cd.title, { size: 30, weight: 600 })));
    text(g, cd.title, x + 110, y + 74, { size: ts, weight: 600, color, alpha: a });
    paragraph(g, cd.line, x + 26, y + 136, cw - 48, { size: 21, color: '#cfd5e2', alpha: a, lineHeight: 28, maxLines: 4 });
  });
};

CH.blueprint = (ctx) => {
  const { u, D } = ctx;
  header(ctx);
  const S = P.song, secs = S.sections, dur = S.duration;
  const X0 = 140, X1 = LW - 140, xs = (s) => X0 + (X1 - X0) * s / dur;
  const hookCap = captionAt(ctx, /hook/i), energyCap = captionAt(ctx, /energy/i), tempoCap = captionAt(ctx, /tempo|BPM/i);
  const tHook = hookCap ? hookCap.t0 - ctx.c.t0 : D * 0.55;
  const tEnergy = energyCap ? energyCap.t0 - ctx.c.t0 : D * 0.35;
  const tTempo = tempoCap ? tempoCap.t0 - ctx.c.t0 : 6;
  // 1 the form
  const yF = 190;
  const parts = [];
  secs.forEach((s) => { const p = s.part || ''; if (!parts.length || parts[parts.length - 1].name !== p) parts.push({ name: p, a: s.start, b: s.end, key: s.key }); else parts[parts.length - 1].b = s.end; });
  const grow = eInOut(ramp(u, 3.0, 5.5));
  const xr = X0 + (X1 - X0) * grow;
  g.save(); g.beginPath(); g.rect(0, 0, xr + 2, LH); g.clip();
  parts.forEach((p, i) => {
    if (!p.name) return;
    const a = xs(p.a), b = xs(p.b);
    g.save(); g.globalAlpha = 0.9; g.strokeStyle = rgba(palHex.C1, 0.6); g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(a + 3, yF + 18); g.lineTo(a + 3, yF + 8); g.lineTo(b - 3, yF + 8); g.lineTo(b - 3, yF + 18); g.stroke(); g.restore();
    const lab = p.key ? `${p.name}  ·  ${p.key}` : p.name;
    text(g, lab, (a + b) / 2, yF - 4, { size: measure(g, lab, { size: 20, weight: 600, track: 2 }) > b - a - 10 ? 16 : 20, weight: 600, color: palHex.C1, align: 'center', track: 2 });
  });
  let lastLabel = -1e9;
  secs.forEach((s) => {
    const a = xs(s.start), b = xs(s.end), lv = s.level;
    const col = lv > 0.85 ? palHex.C3 : lv > 0.6 ? palHex.C1 : palHex.C2;
    const alpha = 0.25 + 0.6 * lv;
    g.save(); g.fillStyle = rgba(col, alpha); rrect(g, a + 1.5, yF + 26, Math.max(2, b - a - 3), 44, 6); g.fill(); g.restore();
    const w = b - a;
    const nm = prettyName(s.name);
    const light = alpha > 0.55 && col !== palHex.C2;
    if (w > measure(g, nm, { size: 16, weight: 600 }) + 10) text(g, nm, (a + b) / 2, yF + 54, { size: 16, color: light ? '#0b0c12' : K.ink, weight: 600, align: 'center' });
    else if ((a + b) / 2 - lastLabel > 34) { lastLabel = (a + b) / 2; g.save(); g.translate((a + b) / 2, yF + 84); g.rotate(-0.55); text(g, nm, 0, 0, { size: 15, color: K.dim, align: 'right' }); g.restore(); }
  });
  g.restore();
  // meter changes
  // 2 tempo
  const tA = eInOut(ramp(u, tTempo, tTempo + 3.5));
  const yT = 372, hT = 92;
  if (tA > 0) {
    const bpms = S.tempo.map((x) => x[1]);
    const lo = Math.min(...bpms), hi = Math.max(...bpms);
    const vlo = Math.max(lo, 40), vhi = hi;
    text(g, 'TEMPO', X0, yT - 18, { size: 18, weight: 600, color: K.dim, track: 4, alpha: Math.min(1, tA * 3) });
    g.save(); g.beginPath(); g.rect(0, 0, X0 + (X1 - X0) * tA, LH); g.clip();
    g.beginPath();
    S.tempo.forEach(([t, b], i) => { const x = xs(t), y = yT + hT - hT * clamp((b - vlo) / (vhi - vlo || 1)); i ? g.lineTo(x, y) : g.moveTo(x, y); });
    g.strokeStyle = palHex.C1; g.lineWidth = 3; g.stroke();
    g.restore();
    const labs = [];
    secs.forEach((s) => { if (s.bpm && (!labs.length || Math.abs(labs[labs.length - 1].bpm - s.bpm) > 6)) labs.push({ x: xs(s.start), bpm: s.bpm }); });
    let lastX = -1e9;
    labs.forEach((l) => { if (l.x < X0 + (X1 - X0) * tA && l.x - lastX > 56) { lastX = l.x; text(g, `${Math.round(l.bpm)}`, l.x + 4, yT + hT + 26, { size: 18, color: K.dim }); } });
    text(g, 'BPM', X1, yT + hT + 26, { size: 16, color: K.faint, align: 'right', alpha: tA });
  }
  // 3 energy (LUFS per bar)
  const eA = eInOut(ramp(u, tEnergy, tEnergy + 3.5));
  const yE = 560, hE = 105;
  if (eA > 0) {
    const vals = S.energy.map((x) => x[1]).filter((v) => v > -70);
    const lo = Math.max(-45, Math.min(...vals)), hi = Math.max(...vals);
    const ys = (v) => yE + hE - hE * clamp((v - lo) / (hi - lo || 1));
    text(g, 'ENERGY  ·  LUFS PER BAR', X0, yE - 22, { size: 18, weight: 600, color: K.dim, track: 4, alpha: Math.min(1, eA * 3) });
    g.save(); g.beginPath(); g.rect(0, 0, X0 + (X1 - X0) * eA, LH); g.clip();
    const grd = g.createLinearGradient(0, yE, 0, yE + hE);
    grd.addColorStop(0, rgba(palHex.C1, 0.45)); grd.addColorStop(1, rgba(palHex.C2, 0.02));
    g.beginPath(); g.moveTo(xs(S.energy[0][0]), yE + hE);
    S.energy.forEach(([t, v]) => g.lineTo(xs(t), ys(Math.max(v, lo))));
    g.lineTo(xs(S.energy[S.energy.length - 1][0]), yE + hE); g.closePath(); g.fillStyle = grd; g.fill();
    g.beginPath(); S.energy.forEach(([t, v], i) => (i ? g.lineTo(xs(t), ys(Math.max(v, lo))) : g.moveTo(xs(t), ys(Math.max(v, lo)))));
    g.strokeStyle = palHex.C3; g.lineWidth = 2; g.stroke();
    g.restore();
    const q = secs.reduce((a, b) => (a.lufs < b.lufs ? a : b)), L = secs.reduce((a, b) => (a.lufs > b.lufs ? a : b));
    const la = ramp(u, tEnergy + 2.5, tEnergy + 3.5);
    for (const [s, dy] of [[q, 34], [L, -14]]) {
      const x = xs((s.start + s.end) / 2), y = ys(s.lufs) + dy;
      text(g, `${prettyName(s.name)}  ${s.lufs.toFixed(1)}`, x, y, { size: 20, weight: 600, color: s === L ? palHex.C3 : K.dim, align: 'center', alpha: la });
    }
  }
  // 4 the hook
  const hA = ramp(u, tHook - 0.3, tHook + 0.9);
  if (hA > 0 && P.hook.motif.length) {
    const yH = 770;
    const ho = P.hook.occurrences;
    ho.forEach((o, i) => {   // occurrences flash on the form
      const at = tHook + 0.6 + i * Math.min(0.35, 6 / Math.max(1, ho.length));
      const a = ramp(u, at, at + 0.3);
      if (a <= 0) return;
      const x = xs(o.t), pulse = 1 - ramp(u, at, at + 1.2);
      g.save(); g.globalAlpha = a; g.fillStyle = palHex.C3;
      g.translate(x, yF + 22); g.rotate(Math.PI / 4); g.fillRect(-5 - 4 * pulse, -5 - 4 * pulse, 10 + 8 * pulse, 10 + 8 * pulse); g.restore();
    });
    const nOcc = ho.filter((o, i) => u > tHook + 0.6 + i * Math.min(0.35, 6 / Math.max(1, ho.length))).length;
    text(g, 'THE HOOK', X0, yH - 30, { size: 20, weight: 600, color: palHex.C1, track: 6, alpha: hA });
    text(g, P.hook.names.map((n) => n.replace('b', '♭').replace('#', '♯')).join('  ·  '), X0, yH + 40, { font: SERIF, size: 58, color: K.ink, alpha: hA });
    text(g, `× ${nOcc}`, X0, yH + 100, { font: SANS, size: 34, weight: 300, color: palHex.C3, alpha: hA });
    text(g, P.hook.source === 'written' ? 'as written in the arrangement' : 'found in the lead’s top line', X0 + 90, yH + 98, { size: 20, color: K.faint, alpha: hA });
    // the phrase as a piano roll, drawn like a pen
    const ph = P.hook.phrase;
    if (ph.length) {
      const px0 = 800, px1 = LW - 140, py0 = yH - 70, py1 = yH + 70;
      const t0 = ph[0][0], t1 = ph[ph.length - 1][0] + ph[ph.length - 1][1];
      const pl = Math.min(...ph.map((n) => n[2])) - 2, pu = Math.max(...ph.map((n) => n[2])) + 2;
      const X = (t) => px0 + (px1 - px0) * (t - t0) / (t1 - t0), Y = (p) => py1 - (py1 - py0) * (p - pl) / (pu - pl);
      const pen = ramp(u, tHook, tHook + 3.2);
      const nm = P.hook.motif.length;
      ph.forEach((n, i) => {
        const a = clamp((pen * (t1 - t0) - (n[0] - t0)) / 0.3);
        if (a <= 0) return;
        const w = Math.max(6, X(n[0] + n[1] * Math.min(1, a)) - X(n[0]) - 3);
        const inMotif = i < nm;
        const col = inMotif ? palHex.C3 : palHex.C1;
        g.save(); g.globalAlpha = hA * (0.35 + 0.65 * n[3] / 127);
        g.fillStyle = col; rrect(g, X(n[0]), Y(n[2]) - 7, w, 14, 7); g.fill(); g.restore();
        if (inMotif) text(g, P.hook.names[i].replace('b', '♭').replace('#', '♯'), X(n[0]), Y(n[2]) - 18, { size: 20, weight: 600, color: palHex.C3, alpha: hA * a });
      });
    }
  }
};

function laneView(ctx, st, opts) {
  // a piano roll per track around song time st: [st - back, st + ahead], playhead at px
  const { tracks, x0 = 330, x1 = LW - 110, y0 = 190, y1 = 900, back = 3.2, ahead = 5.8, hi = null, alpha = 1 } = opts;
  const n = tracks.length;
  const lh = Math.min(70, (y1 - y0) / Math.max(1, n));
  const X = (t) => x0 + (x1 - x0) * (t - (st - back)) / (back + ahead);
  const px = X(st);
  const laneY = {};
  g.save(); g.beginPath(); g.rect(x0 - 2, y0 - 30, x1 - x0 + 4, n * lh + 60); g.clip();
  tracks.forEach((tr, i) => {
    const y = y0 + i * lh;
    laneY[tr.id] = y + lh / 2;
    const isHi = !hi || hi.includes(tr.id);
    const la = alpha * (isHi ? 1 : 0.28);
    g.save(); g.globalAlpha = la * 0.5; g.fillStyle = i % 2 ? 'rgba(255,255,255,0.025)' : 'rgba(255,255,255,0.05)'; g.fillRect(x0, y + 2, x1 - x0, lh - 4); g.restore();
    const notes = tr.notes;
    let lo = 127, up = 0, act = 0;
    for (const nn of notes) if (nn[0] + nn[1] >= st - back && nn[0] <= st + ahead) { lo = Math.min(lo, nn[2]); up = Math.max(up, nn[2]); }
    if (up < lo) { lo = 60; up = 72; }
    const pr = Math.max(6, up - lo);
    for (const nn of notes) {
      const [t0, d, p, v] = nn;
      if (t0 + d < st - back || t0 > st + ahead) continue;
      const a = X(t0), b = Math.max(a + 3, X(t0 + d));
      const yy = y + lh - 8 - (lh - 16) * (p - lo) / pr;
      const on = t0 <= st && st < t0 + d;
      const fresh = on ? 1 - clamp((st - t0) / 0.35) : 0;
      if (on) act += v / 127;
      const bright = (0.25 + 0.75 * v / 127) * (t0 > st ? 0.55 : 1);
      g.save(); g.globalAlpha = la * bright * (on ? 1 : 0.75);
      g.fillStyle = on ? U.rgb01ToHex(U.hexToRgb01(tr.color).map((c) => Math.min(1, c + 0.35 * fresh + 0.1))) : tr.color;
      const hh = Math.max(3, Math.min(9, lh / 6)) + (on ? 2 * fresh : 0);
      rrect(g, a, yy - hh / 2, b - a, hh, hh / 2); g.fill(); g.restore();
    }
    // label + activity (outside the clip)
    g.restore();
    text(g, tr.id, x0 - 22, y + lh / 2 + 7, { size: Math.min(22, lh * 0.42), weight: 600, color: tr.color, align: 'right', alpha: la });
    if (tr.player) text(g, tr.player, x0 - 22, y + lh / 2 + 7 + Math.min(20, lh * 0.34), { size: Math.min(15, lh * 0.28), color: K.faint, align: 'right', alpha: la });
    g.save(); g.globalAlpha = la * 0.9; g.fillStyle = tr.color; g.fillRect(x0 - 12, y + lh - 6 - Math.min(lh - 10, act * (lh - 10)), 4, Math.min(lh - 10, act * (lh - 10))); g.restore();
    g.save(); g.beginPath(); g.rect(x0 - 2, y0 - 30, x1 - x0 + 4, n * lh + 60); g.clip();
  });
  g.restore();
  // playhead
  g.save(); g.globalAlpha = alpha * 0.9; const grd = g.createLinearGradient(px, y0, px, y0 + n * lh);
  grd.addColorStop(0, rgba(palHex.C3, 0)); grd.addColorStop(0.5, rgba(palHex.C3, 0.9)); grd.addColorStop(1, rgba(palHex.C3, 0));
  g.fillStyle = grd; g.fillRect(px - 1, y0 - 10, 2, n * lh + 20); g.restore();
  // moves: ticks ahead, a label when they happen
  const ids = new Set(tracks.map((t) => t.id));
  for (const m of P.moves) {
    if (!m.pop || !ids.has(m.track) || m.t < st - 2.6 || m.t > st + ahead) continue;
    if (hi && !hi.includes(m.track)) continue;
    const y = laneY[m.track];
    const col = roleColor(m.player);
    if (m.t > st) {
      g.save(); g.globalAlpha = alpha * 0.6; g.fillStyle = col; g.beginPath(); g.moveTo(X(m.t), y - lh / 2 + 2); g.lineTo(X(m.t) - 5, y - lh / 2 - 6); g.lineTo(X(m.t) + 5, y - lh / 2 - 6); g.fill(); g.restore();
      continue;
    }
    const age = st - m.t;
    const a = alpha * Math.min(1, age / 0.08 + 0.4) * (1 - ramp(age, 1.8, 2.6));
    const pop = eBack(ramp(age, 0, 0.22));
    const lab = m.label.toUpperCase();
    const fs = 20;
    const w = measure(g, lab, { size: fs, weight: 700, track: 2 }) + 28;
    const lx = px + 14, ly = y - 10 - 26 * eOut(ramp(age, 0, 1.6));
    g.save(); g.globalAlpha = a; g.translate(lx, ly); g.scale(0.6 + 0.4 * pop, 0.6 + 0.4 * pop);
    rrect(g, 0, -fs, w, fs * 1.6, fs * 0.8); g.fillStyle = rgba(col, 0.9); g.fill();
    g.restore();
    g.save(); g.globalAlpha = a; g.translate(lx, ly); g.scale(0.6 + 0.4 * pop, 0.6 + 0.4 * pop);
    text(g, lab, 14, 5, { size: fs, weight: 700, color: '#0a0b10', track: 2 }); g.restore();
    // flash at the hit
    if (age < 0.3) { g.save(); g.globalAlpha = alpha * (1 - age / 0.3); g.fillStyle = col; g.beginPath(); g.arc(px, y, 10 + 30 * age, 0, 7); g.fill(); g.restore(); }
  }
  return { laneY, px };
}

function tracksIn(a, b, max = 12, only = null) {
  const out = [];
  for (const tr of P.tracks) {
    if (only && !only.includes(tr.id)) continue;
    let n = 0;
    for (const x of tr.notes) if (x[0] + x[1] >= a && x[0] <= b) n++;
    if (n) out.push([tr, n]);
  }
  const fo = ['drums', 'bass', 'piano', 'organ', 'guitar', 'synth', 'strings', 'winds', 'brass', 'timpani', 'choir', 'other', 'fx'];
  out.sort((x, y) => fo.indexOf(x[0].family) - fo.indexOf(y[0].family));
  if (out.length > max) {
    const keep = new Set(out.slice().sort((x, y) => y[1] - x[1]).slice(0, max).map((x) => x[0].id));
    return out.filter((x) => keep.has(x[0].id)).map((x) => x[0]);
  }
  return out.map((x) => x[0]);
}

CH.tracks = (ctx) => {
  const { u, t, c, A } = ctx;
  header(ctx);
  const items = c.items || [];
  const first = items.length ? items[0].lead0 : c.t1;
  // intro: the hero sounds + the measured reason
  const ia = vis(t, c.t0 + 2.8, first - 0.3, 0.6, 0.5);
  if (ia > 0) {
    const heroes = P.sound.heroes;
    let x = 140;
    text(g, 'HERO SOUNDS', 140, 300, { size: 20, weight: 600, color: palHex.C1, track: 6, alpha: ia });
    heroes.forEach((h, i) => { const a = ia * eOut(ramp(u, 3.2 + i * 0.3, 3.8 + i * 0.3)); x += chip(g, h, x, 360, palHex.C1, { size: 26, alpha: a }) + 18; });
    const m = P.sound.measured[0];
    if (m) {
      const cap = captionAt(ctx, /Measured/);
      const ma = cap ? vis(t, cap.t0 - 0.2, first - 0.3, 0.6, 0.5) : 0;
      panel(g, 140, 440, LW - 280, 260, { alpha: ma, border: rgba(palHex.C1, 0.4) });
      text(g, 'MEASURED, NOT GUESSED  ·  SOUND.md', 180, 492, { size: 18, weight: 600, color: K.dim, track: 4, alpha: ma });
      // numbers in the accent colour
      const o = { font: SERIF_TEXT, size: 34, lineHeight: 50 };
      const lines = wrap(g, m, LW - 360, o).slice(0, 3);
      lines.forEach((l, i) => {
        let xx = 180;
        for (const part of l.split(/(\s+)/)) {
          const num = /[\d]/.test(part);
          text(g, part, xx, 560 + i * 50, { ...o, color: num ? palHex.C3 : '#dfe3ec', weight: num ? 600 : 400, alpha: ma });
          xx += measure(g, part, o);
        }
      });
    }
  }
  // the items
  const it = items.find((x) => t >= x.lead0 - 0.2 && t < x.v1 + 0.15);
  if (!it) return;
  const k = items.indexOf(it);
  const a = Math.min(clamp((t - it.v0 + 0.3) / 0.35), clamp((it.v1 + 0.15 - t) / 0.3));
  const st = A.on ? A.st : it.s0;
  const solo = t < it.vs;
  // progress dots
  items.forEach((x, i) => { g.save(); g.globalAlpha = 0.9; g.fillStyle = i === k ? palHex.C1 : i < k ? rgba(palHex.C1, 0.5) : 'rgba(255,255,255,0.18)'; g.beginPath(); g.arc(LW / 2 - (items.length - 1) * 14 + i * 28, 132, i === k ? 6 : 4, 0, 7); g.fill(); g.restore(); });
  // card (left)
  const cx = 110, cy = 190, cw = 700;
  const col = it.color;
  panel(g, cx, cy, cw, 690, { alpha: a, border: rgba(col, 0.55), r: 22 });
  g.save(); g.globalAlpha = a; g.fillStyle = col; rrect(g, cx, cy, 8, 690, 4); g.fill(); g.restore();
  text(g, `${k + 1} / ${items.length}`, cx + 40, cy + 54, { size: 18, color: K.faint, track: 3, alpha: a });
  text(g, it.name, cx + 40, cy + 118, { font: SERIF, size: 60, color: K.ink, alpha: a });
  if (it.ids.length > 1 || it.ids[0] !== it.name) text(g, it.ids.join(' · '), cx + 40, cy + 158, { font: MONO, size: 20, color: col, alpha: a });
  let y = cy + 214;
  const labels = { sound: 'SOUND', why: 'WHY', player: 'PLAYED', layers: 'LAYERS', stats: 'IN THE MIX', mix: 'MIX' };
  for (const [kind, line] of it.lines) {
    if (y > cy + 650) break;
    const la = a * eOut(ramp(t, it.v0 + 0.1 + (y - cy) / 1400, it.v0 + 0.6 + (y - cy) / 1400));
    text(g, labels[kind] || kind.toUpperCase(), cx + 40, y, { size: 16, weight: 600, color: K.faint, track: 3, alpha: la });
    const hgt = paragraph(g, line, cx + 40, y + 32, cw - 80, { font: kind === 'sound' ? MONO : SANS, size: kind === 'sound' ? 21 : 23, color: kind === 'why' ? '#e6e1d4' : '#cfd5e2', style: kind === 'why' ? 'italic' : '', alpha: la, lineHeight: 30, maxLines: 2 });
    y += 40 + hgt + 14;
  }
  // SOLO / + BAND
  const sa = a;
  if (solo) chip(g, 'SOLO', cx + cw - 140, cy + 58, col, { size: 22, alpha: sa * (0.7 + 0.3 * Math.sin(t * 6) ** 2) });
  else chip(g, '+ THE BAND', cx + cw - 214, cy + 58, palHex.C3, { size: 22, alpha: sa });
  // lanes (right): its tracks, the others dim when the band comes back
  const lanes = tracksIn(st - 3, st + 6, 8, it.ids);
  laneView(ctx, st, { tracks: lanes, x0: 1030, x1: LW - 90, y0: 230, y1: 230 + Math.min(640, 150 * lanes.length), back: 2.6, ahead: 4.2, alpha: a });
  ctx.mask = it.ids;
};

CH.performance = (ctx) => {
  const { u, t, c, A } = ctx;
  header(ctx);
  const exs = c.excerpts || [];
  const ex = exs.find((x) => t >= x.v0 - 0.4 && t < x.v1 + 0.2);
  if (!ex) {
    // before the first excerpt: the players as a legend
    const pa = vis(u, 3.0, (exs[0] ? exs[0].v0 - c.t0 : ctx.D) - 0.2, 0.6, 0.4);
    const pl = P.players;
    pl.forEach((p, i) => {
      const x = LW / 2 + (i - (pl.length - 1) / 2) * 300, y = 520;
      const a = pa * eOut(ramp(u, 3.2 + i * 0.25, 3.9 + i * 0.25));
      g.save(); g.globalAlpha = a; g.beginPath(); g.arc(x, y - 40, 54, 0, 7); g.fillStyle = rgba(roleColor(p), 0.1); g.fill(); g.strokeStyle = rgba(roleColor(p), 0.8); g.lineWidth = 2; g.stroke(); g.restore();
      g.save(); g.globalAlpha = a; icon(g, p, x, y - 40, 30, roleColor(p)); g.restore();
      text(g, P.roleTitles[p] || p, x, y + 60, { size: 30, weight: 600, color: roleColor(p), align: 'center', alpha: a });
      const n = P.moves.filter((m) => m.player === p && m.pop).length;
      text(g, `${n} moves on the log`, x, y + 96, { size: 20, color: K.dim, align: 'center', alpha: a });
    });
    return;
  }
  const a = Math.min(clamp((t - ex.v0 + 0.4) / 0.4), clamp((ex.v1 + 0.2 - t) / 0.35));
  const st = A.on ? A.st : ex.s0;
  const sec = sectionAt(st);
  text(g, prettyName(sec.name).toUpperCase(), 110, 150, { font: SERIF, size: 56, color: K.ink, alpha: a });
  const sub = [fmtT(st), sec.part, sec.key, sec.bpm ? `${Math.round(sec.bpm)} BPM` : '', sec.meter].filter(Boolean).join('   ·   ');
  text(g, sub, 110 + measure(g, prettyName(sec.name).toUpperCase(), { font: SERIF, size: 56 }) + 34, 148, { size: 22, color: K.dim, alpha: a, track: 1 });
  const live = t >= ex.vs;
  if (!live) chip(g, 'LEAD-IN', LW - 250, 148, K.dim, { size: 18, alpha: a });
  else chip(g, '● LIVE', LW - 230, 148, K.red, { size: 18, alpha: a });
  const lanes = tracksIn(ex.s0 - 1, ex.s1 + 1, 13);
  laneView(ctx, st, { tracks: lanes, x0: 330, x1: LW - 100, y0: 205, y1: 880, back: 3.4, ahead: 5.6, alpha: a });
};

CH.crisis = (ctx) => {
  const { u, t, D } = ctx;
  header(ctx);
  const V = P.crisis;
  // the stamp
  const s0 = 3.2;
  const sa = ramp(u, s0, s0 + 0.25);
  if (V.verdict && sa > 0) {
    const settle = eInOut(ramp(u, s0 + 2.4, s0 + 3.4));
    const sc = lerp(3.2, 1, eBack(ramp(u, s0, s0 + 0.35)));
    const cx = lerp(LW / 2, LW - 300, settle), cy = lerp(LH / 2 - 60, 170, settle);
    const k = sc * lerp(1, 0.55, settle);
    const shake = (1 - ramp(u, s0 + 0.3, s0 + 0.9)) * 10;
    const r = mulberry(Math.floor(u * 60));
    g.save(); g.translate(cx + (r() - 0.5) * shake, cy + (r() - 0.5) * shake); g.rotate(-0.12); g.scale(k, k);
    g.globalAlpha = sa;
    const word = V.verdict.toUpperCase();
    const w = measure(g, word, { size: 120, weight: 700, track: 14 }) + 90;
    g.lineWidth = 7; g.strokeStyle = K.red; rrect(g, -w / 2, -92, w, 170, 18); g.stroke();
    g.lineWidth = 2.5; rrect(g, -w / 2 + 14, -78, w - 28, 142, 12); g.stroke();
    g.restore();
    g.save(); g.translate(cx + (r() - 0.5) * shake, cy + (r() - 0.5) * shake); g.rotate(-0.12); g.scale(k, k);
    text(g, word, 0, 34, { size: 120, weight: 700, color: K.red, align: 'center', track: 14, alpha: sa });
    text(g, 'A&R VERDICT', 0, -110, { size: 22, weight: 600, color: K.red, align: 'center', track: 6, alpha: sa });
    g.restore();
    ctx.caSpike = 0.012 * (1 - ramp(u, s0, s0 + 0.6)) * sa;
  }
  // issues
  const fixCap = captionAt(ctx, /went back|owner/i);
  const tFix = fixCap ? fixCap.t0 - ctx.c.t0 + 1.0 : D * 0.5;
  const ia = vis(u, s0 + 2.8, tFix + 0.6, 0.5, 0.6);
  if (ia > 0) {
    text(g, 'RANKED ISSUES', 120, 290, { size: 20, weight: 600, color: K.dim, track: 6, alpha: ia });
    V.issues.forEach((is, i) => {
      const a = ia * eOut(ramp(u, s0 + 3.0 + i * 0.35, s0 + 3.6 + i * 0.35));
      const y = 340 + i * Math.min(76, 520 / Math.max(1, V.issues.length));
      const cw = chip(g, is.severity.toUpperCase() || 'ISSUE', 120, y, sevColor(is.severity), { size: 18, alpha: a });
      text(g, `${is.n}`, 120 + cw + 22, y + 2, { size: 30, weight: 300, color: K.faint, alpha: a });
      paragraph(g, is.title, 120 + cw + 62, y + 2, 1280 - cw, { size: 30, color: K.ink, alpha: a, maxLines: 1 });
      if (is.owner) text(g, `owner: ${is.owner}`, 120 + cw + 62, y + 34, { size: 18, color: K.faint, alpha: a });
    });
  }
  // the revision: before -> after
  const fa = vis(u, tFix + 0.4, D, 0.6, 0.5);
  if (fa > 0) {
    text(g, 'THE REVISION  ·  BEFORE → AFTER', 120, 290, { size: 20, weight: 600, color: K.dim, track: 6, alpha: fa });
    const fx = V.fixes.slice(0, 4);
    fx.forEach((fz, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = 120 + col * 850, y = 330 + row * 300, w = 810, h = 270;
      const t0 = tFix + 0.8 + i * 1.3;
      const a = fa * eOut(ramp(u, t0, t0 + 0.6));
      if (a <= 0) return;
      panel(g, x, y, w, h, { alpha: a, border: rgba(fz.status.startsWith('fixed') ? K.green : K.amber, 0.45) });
      const st = fz.status || 'revised';
      const cw = chip(g, st.toUpperCase(), x + 28, y + 50, st.startsWith('fixed') ? K.green : st.includes('part') ? K.amber : K.dim, { size: 16, alpha: a });
      paragraph(g, fz.head, x + 40 + cw, y + 52, w - cw - 70, { size: 26, weight: 600, color: K.ink, alpha: a, maxLines: 1 });
      fz.pairs.slice(0, 3).forEach((p, j) => {
        const yy = y + 108 + j * 54;
        const m = ramp(u, t0 + 0.6 + j * 0.25, t0 + 1.8 + j * 0.25);
        const v = lerp(p.before, p.after, eInOut(m));
        const span = Math.max(Math.abs(p.before), Math.abs(p.after), 1e-6);
        const bw = 230;
        paragraph(g, p.label, x + 28, yy + 6, 300, { size: 19, color: K.dim, alpha: a, maxLines: 1 });
        const bx = x + 345;
        const zero = p.before < 0 || p.after < 0 ? (p.before > 0 || p.after > 0 ? bx + bw / 2 : bx + bw) : bx;
        const scale = (zero === bx + bw / 2 ? bw / 2 : bw) / span;
        g.save(); g.globalAlpha = a * 0.35; g.fillStyle = K.dim;
        const b0 = zero, b1 = zero + p.before * scale; g.fillRect(Math.min(b0, b1), yy - 12, Math.abs(b1 - b0), 6); g.restore();
        g.save(); g.globalAlpha = a; const c1 = zero + v * scale; g.fillStyle = K.green;
        g.fillRect(Math.min(zero, c1), yy - 2, Math.abs(c1 - zero), 12); g.restore();
        const num = (x2) => { const s2 = Math.abs(x2) >= 100 ? x2.toFixed(0) : Math.abs(x2) >= 10 ? x2.toFixed(1) : x2.toFixed(2); return s2.includes('.') ? s2.replace(/0+$/, '').replace(/\.$/, '') : s2; };
        text(g, `${num(p.before)} → ${num(v)} ${p.unit}`, x + w - 24, yy + 8, { size: 20, weight: 600, color: K.ink, align: 'right', alpha: a });
      });
    });
    // the final numbers
    const pc = captionAt(ctx, /proposal|ship/i);
    const ma = pc ? ramp(ctx.t, pc.t0, pc.t0 + 0.6) : 0;
    if (ma > 0 && V.proposal) chip(g, `VERDICT PROPOSAL: ${V.proposal.toUpperCase()}`, LW / 2 - 260, 950, K.green, { size: 24, alpha: ma });
  }
};

function songOverlay(ctx, opt = {}) {
  const { t, c, A } = ctx;
  const S = P.song, st = A.st;
  const sec = sectionAt(st);
  const into = st - sec.start;
  // the section title
  const ta = vis(into, 0.2, Math.min(7.5, sec.end - sec.start), 0.8, 1.0);
  if (opt.titles !== false && ta > 0 && sec.end - sec.start > 3) {
    const sl = 20 * (1 - eOut(ramp(into, 0.2, 1.2)));
    if (sec.part) text(g, sec.part.toUpperCase(), 110 + sl, 128, { size: 20, weight: 600, color: palHex.C1, track: 6, alpha: ta });
    text(g, prettyName(sec.name).replace(/^./, (x) => x.toUpperCase()), 106 + sl, 200, { font: SERIF, size: 76, color: K.ink, alpha: ta });
    const sub = [sec.key, sec.bpm ? `${Math.round(sec.bpm)} BPM` : '', sec.meter].filter(Boolean).join('   ·   ');
    text(g, sub, 110 + sl, 244, { size: 22, color: K.dim, alpha: ta, track: 1 });
    if (sec.what) paragraph(g, sec.what, 110 + sl, 296, 820, { font: SERIF_TEXT, style: 'italic', size: 27, color: '#e3dfd3', alpha: ta * eOut(ramp(into, 1.0, 2.0)), lineHeight: 38, maxLines: 2 });
  }
  // the timeline at the bottom
  const X0 = 110, X1 = LW - 110, y = 1010, dur = S.duration;
  const xs = (s) => X0 + (X1 - X0) * s / dur;
  const vals = S.energy.map((x) => x[1]).filter((v) => v > -70);
  const lo = Math.max(-45, Math.min(...vals)), hi = Math.max(...vals);
  g.save(); g.globalAlpha = 0.55;
  g.beginPath(); S.energy.forEach(([tt, v], i) => { const x = xs(tt), yy = y - 8 - 34 * clamp((Math.max(v, lo) - lo) / (hi - lo)); i ? g.lineTo(x, yy) : g.moveTo(x, yy); });
  g.strokeStyle = palHex.C3; g.lineWidth = 1.5; g.stroke(); g.restore();
  S.sections.forEach((s) => {
    const cur = s === sec;
    g.save(); g.globalAlpha = cur ? 0.95 : 0.35; g.fillStyle = cur ? palHex.C1 : '#ffffff';
    g.fillRect(xs(s.start) + 1, y, xs(s.end) - xs(s.start) - 2, cur ? 5 : 3); g.restore();
  });
  P.hook.occurrences.forEach((o) => { g.save(); g.globalAlpha = 0.8; g.fillStyle = palHex.C3; g.translate(xs(o.t), y + 14); g.rotate(Math.PI / 4); g.fillRect(-3, -3, 6, 6); g.restore(); });
  const cx = xs(st);
  g.save(); g.fillStyle = '#fff'; g.beginPath(); g.arc(cx, y + 2, 6, 0, 7); g.fill(); g.restore();
  text(g, `${fmtT(st)} / ${fmtT(dur)}`, X1, y - 16, { size: 18, color: K.dim, align: 'right' });
  // the hook badge
  const occ = P.hook.occurrences.find((o) => st >= o.t - 0.1 && st < o.end + 1.8);
  if (occ) {
    const ha = Math.min(ramp(st, occ.t - 0.1, occ.t + 0.25), 1 - ramp(st, occ.end + 1.0, occ.end + 1.8));
    const bx = LW - 560, by = 110;
    panel(g, bx, by, 450, 170, { alpha: ha * 0.9, border: rgba(palHex.C3, 0.6) });
    text(g, 'THE HOOK', bx + 28, by + 40, { size: 18, weight: 600, color: palHex.C3, track: 6, alpha: ha });
    text(g, occ.tracks.slice(0, 4).join(' · ') + (occ.tracks.length > 4 ? ` +${occ.tracks.length - 4}` : ''), bx + 28, by + 68, { size: 17, color: K.dim, alpha: ha });
    // the motif as pitched dots, lighting up with its notes
    const ps = occ.pitches || P.hook.motif, pl = Math.min(...ps), pu = Math.max(...ps);
    const span = Math.max(1e-3, occ.end - occ.t);
    ps.forEach((p, i) => {
      const x = bx + 40 + i * (370 / Math.max(1, ps.length - 1)), yy = by + 148 - 50 * (p - pl) / Math.max(1, pu - pl);
      const lit = st >= occ.t + span * i / ps.length;
      g.save(); g.globalAlpha = ha * (lit ? 1 : 0.3); g.fillStyle = lit ? palHex.C3 : '#fff';
      g.beginPath(); g.ellipse(x, yy, 11, 8, -0.4, 0, 7); g.fill(); g.restore();
    });
  }
  // moves: small pills rising bottom-right
  let k = 0;
  for (let i = P.moves.length - 1; i >= 0 && k < 5; i--) {
    const m = P.moves[i];
    if (!m.pop || m.t > st || st - m.t > 2.2) continue;
    const age = st - m.t;
    const a = Math.min(1, age / 0.08 + 0.3) * (1 - ramp(age, 1.4, 2.2)) * 0.9;
    const lab = `${m.label}`;
    const w = measure(g, lab, { size: 19, weight: 600 }) + 58;
    const x = LW - 110 - w, yy = 930 - k * 44 - 20 * eOut(ramp(age, 0, 1.5));
    g.save(); g.globalAlpha = a; rrect(g, x, yy - 24, w, 34, 17); g.fillStyle = 'rgba(8,9,14,0.7)'; g.fill(); g.strokeStyle = roleColor(m.player); g.lineWidth = 1.5; g.stroke(); g.restore();
    g.save(); g.globalAlpha = a; g.fillStyle = roleColor(m.player); g.beginPath(); g.arc(x + 20, yy - 7, 6, 0, 7); g.fill(); g.restore();
    text(g, lab, x + 36, yy, { size: 19, weight: 600, color: K.ink, alpha: a });
    k++;
  }
}

function scopeLayer(ctx, a) {
  // the vectorscope (mid / side), trails of the last frames
  const { A } = ctx;
  if (!A.on || a <= 0) return;
  const fi = clamp(Math.round(A.st * fps), 0, F.frames - 1);
  const N = F.meta.scope;
  const cx = LW / 2, cy = LH / 2 - 20, sz = 420 * (1 + 0.08 * A.kick);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (let back = 6; back >= 0; back--) {
    const f2 = Math.max(0, fi - back);
    const al = a * (1 - back / 7) * 0.8;
    g.beginPath();
    for (let i = 0; i < N; i++) {
      const l = F.scope[(f2 * N + i) * 2] / 127, r = F.scope[(f2 * N + i) * 2 + 1] / 127;
      const x = cx + (l - r) * 0.7071 * sz, y = cy - (l + r) * 0.7071 * sz;
      i ? g.lineTo(x, y) : g.moveTo(x, y);
    }
    g.strokeStyle = rgba(back ? palHex.C2 : palHex.C3, al); g.lineWidth = back ? 1.4 : 2.2; g.stroke();
    // mirrored ribbon
    g.save(); g.translate(cx, cy); g.scale(-1, 1); g.translate(-cx, -cy);
    g.strokeStyle = rgba(palHex.C1, al * 0.45); g.lineWidth = 1.2; g.stroke(); g.restore();
  }
  g.restore();
}

CH.song = (ctx) => {
  const { t, c, u, A } = ctx;
  const S = c.song;
  if (!S) return;
  // pre-roll: the cover and the title
  const pre = 1 - ramp(t, S.v0 + 0.5, S.v0 + 2.5);
  if (pre > 0) {
    const a = vis(u, 0.2, S.v0 - c.t0 + 2.5, 0.8, 2.0);
    if (cover) {
      const s = 420 * (1 + 0.03 * u);
      g.save(); g.globalAlpha = a; g.drawImage(cover, LW / 2 - s / 2, LH / 2 - s / 2 - 70, s, s); g.restore();
    }
    text(g, 'THE SONG', LW / 2, LH / 2 + 220, { size: 22, weight: 600, color: palHex.C1, align: 'center', track: 8, alpha: a });
  }
  if (!A.on || t < S.v0) return;
  const sc = ctx.sc;
  if (sc.name === 'scope' || (sc.SB === SCENE_IDS.scope && sc.MIXB > 0) || (sc.SA === SCENE_IDS.scope && sc.MIXB < 1)) {
    const w = sc.SA === SCENE_IDS.scope ? 1 - sc.MIXB : sc.MIXB;
    scopeLayer(ctx, sc.MIXB ? w : 1);
  }
  songOverlay(ctx);
};


const ROMAN = /^(I{1,3}|IV|V|VI{0,3}|IX|X)\s+(.*)$/;

CH.act = (ctx) => {
  const { u, t, c, A, D } = ctx;
  if (A.on && A.st != null) {
    const sc = ctx.sc;
    if (sc.name === 'scope') scopeLayer(ctx, 1);
  }
  const secs = P.song.sections.filter((s) => (c.sections || []).includes(s.name));
  const part = (secs[0] && secs[0].part) || c.title;
  const m = ROMAN.exec(part);
  const numeral = m ? m[1] : '', name = m ? m[2].replace(/^\((.*)\)$/, '$1').replace(/^"(.*)"$/, '$1') : c.title;
  const a = vis(u, 0.3, D, 1.0, 0.8);
  // the act card: numeral, name, key / tempo / meter, its sections
  const big = 1 - 0.35 * eInOut(ramp(u, 4.0, 5.5));
  const x = 110, y = 150 + 80 * (1 - big) * 0;
  if (numeral) text(g, `ACT ${numeral}`, x, y, { size: 24, weight: 600, color: palHex.C1, track: 10, alpha: a });
  text(g, name, x - 4, y + 40 + 90 * big, { font: SERIF, size: Math.round(64 + 56 * big), color: K.ink, alpha: a });
  const keys = [...new Set(secs.map((s) => s.key).filter(Boolean))];
  const bpms = secs.map((s) => s.bpm).filter(Boolean);
  const meters = [...new Set(secs.map((s) => s.meter).filter(Boolean))];
  const bl = bpms.length ? (Math.max(...bpms) - Math.min(...bpms) > 3 ? `${Math.round(Math.min(...bpms))}-${Math.round(Math.max(...bpms))} BPM` : `${Math.round(bpms[0])} BPM`) : '';
  const sub2 = [keys.join(' → '), bl, meters.join(' · '), secs.length ? `${fmtT(secs[0].start)}-${fmtT(secs[secs.length - 1].end)}` : ''].filter(Boolean).join('   ·   ');
  text(g, sub2, x, y + 86 + 90 * big, { size: 24, color: K.dim, track: 1, alpha: a });
  // section chips, the one playing lit
  const st = A.on ? A.st : c.act ? c.act.s0 : 0;
  let cx = x;
  const cy = y + 150 + 90 * big;
  secs.forEach((s, i) => {
    const on = st >= s.start && st < s.end;
    const ca = a * eOut(ramp(u, 0.8 + i * 0.15, 1.4 + i * 0.15));
    cx += chip(g, prettyName(s.name), cx, cy, on ? palHex.C3 : palHex.C1, { size: 20, alpha: ca, fill: on ? 0.35 : 0.1 }) + 12;
  });
  const cur = secs.find((s) => st >= s.start && st < s.end);
  if (cur && cur.what) {
    const wa = a * eOut(ramp(u, 1.5, 2.5));
    paragraph(g, cur.what, x, cy + 70, 600, { font: SERIF_TEXT, style: 'italic', size: 28, color: '#e6e1d4', alpha: wa, lineHeight: 40, maxLines: 4 });
  }
  if (A.on) songOverlay(ctx, { titles: false });
};

CH.tried = (ctx) => {
  const { u, t, c, D, A } = ctx;
  header(ctx);
  const eps = c.episodes || [];
  const ep = eps.find((e) => t >= e.v0 - 0.3 && t < e.v1 + 0.2);
  if (!ep) {
    const a = vis(u, 3.0, eps.length ? eps[0].v0 - c.t0 : D, 0.6, 0.5);
    const e0 = eps[0];
    if (e0 && a > 0) {
      text(g, 'THE A&R JUDGED', LW / 2, 380, { size: 22, weight: 600, color: K.dim, align: 'center', track: 6, alpha: a });
      text(g, e0.commit ? `build ${e0.commit}` : 'the judged build', LW / 2, 470, { font: SERIF, size: 72, color: K.ink, align: 'center', alpha: a });
      text(g, `${eps.length} of its issues, before and after the revision, bar for bar, loudness-matched`, LW / 2, 540, { size: 26, color: K.dim, align: 'center', alpha: a });
    }
    return;
  }
  const a = Math.min(clamp((t - ep.v0 + 0.3) / 0.4), clamp((ep.v1 + 0.2 - t) / 0.4));
  // the issue, in the A&R's words
  const cw = chip(g, `${(ep.severity || 'issue').toUpperCase()}  ·  A&R ISSUE ${ep.n}`, 110, 170, sevColor(ep.severity), { size: 20, alpha: a });
  text(g, `owner: ${ep.owner}`, 130 + cw, 170, { size: 20, color: K.faint, alpha: a });
  paragraph(g, `“${ep.issue}.”`, 110, 250, 1700, { font: SERIF, size: 50, color: K.ink, alpha: a, lineHeight: 60, maxLines: 2 });
  // A / B
  const clip = ep.clip;
  const sides = [
    { key: 'BEFORE', sub: ep.hasBefore ? `as judged${ep.commit ? ` (${ep.commit})` : ''}` : (ep.commit ? 'the judged version no longer builds' : 'no judged build on file'), v0: ep.vb, on: ep.hasBefore, col: K.amber },
    { key: 'AFTER', sub: 'the revision (today)', v0: ep.va, on: true, col: K.green },
  ];
  sides.forEach((sd, i) => {
    const x = 110 + i * 860, y = 350, w = 820, h = 230;
    const playing = sd.on && t >= sd.v0 && t < sd.v0 + clip;
    const done = t >= sd.v0 + clip;
    const pa = a * (playing ? 1 : done ? 0.75 : 0.45);
    panel(g, x, y, w, h, { alpha: pa, border: rgba(sd.col, playing ? 0.95 : 0.35), lineWidth: playing ? 3 : 1.5, r: 22 });
    text(g, sd.key, x + 40, y + 78, { size: 54, weight: 700, color: sd.col, track: 8, alpha: pa });
    text(g, sd.sub, x + 40, y + 122, { size: 22, color: K.dim, alpha: pa });
    text(g, ep.where ? `${ep.where}  ·  ${fmtT(i === 0 ? ep.before : ep.after)}  ·  ${clip.toFixed(1)} s` : '', x + 40, y + 160, { size: 20, color: K.faint, alpha: pa });
    const pr = clamp((t - sd.v0) / clip);
    g.save(); g.globalAlpha = pa * 0.35; g.fillStyle = '#fff'; g.fillRect(x + 40, y + h - 46, w - 80, 4); g.restore();
    g.save(); g.globalAlpha = pa; g.fillStyle = sd.col; g.fillRect(x + 40, y + h - 46, (w - 80) * pr, 4); g.restore();
    if (playing) {
      // the level of what plays: this mix's features for AFTER, a pulse for BEFORE
      const bars = 36;
      for (let k = 0; k < bars; k++) {
        const v = i === 1 && A.on ? A.bands[Math.floor(k * 46 / bars)] / 255 : 0.25 + 0.2 * Math.sin(t * 9 + k * 0.7) ** 2;
        const bh = 8 + 70 * v;
        g.save(); g.globalAlpha = pa * 0.8; g.fillStyle = sd.col; g.fillRect(x + w - 60 - (bars - k) * 12, y + h - 70 - bh, 7, bh); g.restore();
      }
      chip(g, '▶ PLAYING', x + w - 200, y + 60, sd.col, { size: 18, alpha: pa });
    }
  });
  // the fix and its number
  const p = ep.pairs[0];
  const fa = a * eOut(ramp(t, ep.vb + clip - 0.2, ep.vb + clip + 0.6));
  if (p && fa > 0) {
    const st = ep.status || 'revised';
    const w1 = chip(g, st.toUpperCase(), 110, 660, st.startsWith('fixed') ? K.green : K.amber, { size: 18, alpha: fa });
    paragraph(g, ep.fix, 130 + w1, 662, 1500, { size: 30, weight: 600, color: K.ink, alpha: fa, maxLines: 1 });
    const m = eInOut(ramp(t, ep.va, ep.va + 1.6));
    const v = lerp(p.before, p.after, m);
    const num = (x2) => { const s2 = Math.abs(x2) >= 100 ? x2.toFixed(0) : x2.toFixed(1); return s2; };
    text(g, p.label, 110, 722, { size: 24, color: K.dim, alpha: fa });
    text(g, `${num(p.before)}`, 110, 800, { font: SANS, size: 60, weight: 300, color: K.amber, alpha: fa });
    text(g, '→', 290, 796, { size: 50, color: K.faint, alpha: fa });
    text(g, `${num(v)} ${p.unit}`, 370, 800, { font: SANS, size: 60, weight: 600, color: m > 0.99 ? K.green : K.ink, alpha: fa });
    const span = Math.max(Math.abs(p.before), Math.abs(p.after), 1e-6);
    const bx = 820, bw = 990, zero = p.before < 0 && p.after < 0 ? bx + bw : p.before > 0 && p.after > 0 ? bx : bx + bw / 2;
    const scale = (zero === bx + bw / 2 ? bw / 2 : bw) / span;
    g.save(); g.globalAlpha = fa * 0.25; g.fillStyle = '#fff'; g.fillRect(bx, 786, bw, 2); g.fillRect(zero - 1, 752, 2, 70); g.restore();
    g.save(); g.globalAlpha = fa * 0.55; g.fillStyle = K.amber; const b1 = zero + p.before * scale; g.fillRect(Math.min(zero, b1), 758, Math.abs(b1 - zero), 12); g.restore();
    g.save(); g.globalAlpha = fa; g.fillStyle = K.green; const c1 = zero + v * scale; g.fillRect(Math.min(zero, c1), 776, Math.abs(c1 - zero), 22); g.restore();
  }
};

CH.end = (ctx) => {
  const { u, D } = ctx;
  const a = vis(u, 0.3, D, 1.0, 1.6);
  text(g, P.title, LW / 2, 210, { font: SERIF, size: 72, color: K.ink, align: 'center', alpha: a });
  text(g, 'MADE WITH AGENTSOUND', LW / 2, 262, { size: 22, weight: 600, color: palHex.C1, align: 'center', track: 10, alpha: a });
  const roles = P.team.map((x) => x.title).join('  ·  ');
  paragraph(g, roles, LW / 2, 330, 1500, { size: 22, color: K.dim, align: 'center', alpha: a * eOut(ramp(u, 1, 2)), maxLines: 2 });
  const cr = P.credits;
  let y = 430;
  const b = a * eOut(ramp(u, 1.8, 2.8));
  text(g, 'SAMPLE CREDITS', LW / 2, y, { size: 18, weight: 600, color: K.faint, align: 'center', track: 6, alpha: b });
  y += 46;
  for (const p of cr.attribution) {
    paragraph(g, `${p.name.replace(/\s*\(.*$/, '')} — ${p.license}${p.by ? ` — ${p.by.replace(/;.*$/, '')}` : ''}`, LW / 2, y, 1500, { size: 22, color: '#dfe3ec', align: 'center', alpha: b, maxLines: 1 });
    y += 36;
  }
  y += 20;
  const credited = new Set(cr.attribution.map((p) => p.id));
  const others = cr.packs.filter((p) => !credited.has(p.id)).map((p) => p.name.replace(/\s*\(.*$/, '').replace(/:.*$/, ''));
  const c2 = a * eOut(ramp(u, 3.0, 4.0));
  paragraph(g, `Also: ${others.join(' · ')}`, LW / 2, y + 10, 1560, { size: 18, color: K.faint, align: 'center', alpha: c2, lineHeight: 26, maxLines: 4 });
  const d = a * eOut(ramp(u, 4.0, 5.0));
  text(g, cr.narration, LW / 2, 900, { size: 20, color: K.dim, align: 'center', alpha: d });
  text(g, `Every text and number in this film comes from the song's own files: ${cr.files.join(', ')}.`, LW / 2, 940, { size: 17, color: K.faint, align: 'center', alpha: d });
};
