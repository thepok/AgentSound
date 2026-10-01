// Per-frame audio features of the song (mix.wav): what the visualizer scenes react to.
// One value set per video frame of SONG time (fps from the project): smoothed log bands (attack / release),
// loudness (short + slow), spectral-flux onsets (low / high), stereo width and a vectorscope sample of L/R.
// Computed once in Node and cached next to the project (features.bin + features.json); every browser tab reads the
// same arrays, so a frame renders identically in any worker.

import { spawn } from 'node:child_process';
import fs from 'node:fs';

export const BANDS = 48;
export const SCOPE = 192;           // L/R pairs per frame for the vectorscope
const N = 2048;

function fft(re, im) {              // in place, radix 2
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = a + len / 2;
        const xr = re[b] * cr - im[b] * ci, xi = re[b] * ci + im[b] * cr;
        re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi;
        const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
      }
    }
  }
}

export function decode(ffmpeg, wav, sr = 48000) {
  return new Promise((resolve, reject) => {
    const p = spawn(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-i', wav, '-f', 'f32le', '-acodec', 'pcm_f32le',
      '-ac', '2', '-ar', String(sr), '-'], { stdio: ['ignore', 'pipe', 'pipe'] });
    const chunks = []; let err = '';
    p.stdout.on('data', (c) => chunks.push(c));
    p.stderr.on('data', (c) => { err += c; });
    p.on('close', (code) => {
      if (code !== 0) return reject(new Error(`ffmpeg decode failed: ${err}`));
      const buf = Buffer.concat(chunks);
      resolve(new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4));
    });
  });
}

export function analyse(pcm, sr, fps) {
  const frames = Math.ceil(pcm.length / 2 / sr * fps);
  const bands = new Uint8Array(frames * BANDS);
  const loud = new Float32Array(frames), slow = new Float32Array(frames), width = new Float32Array(frames);
  const fluxLo = new Float32Array(frames), fluxHi = new Float32Array(frames);
  const scope = new Int8Array(frames * SCOPE * 2);
  const win = new Float32Array(N).map((_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (N - 1)));
  const edges = [];
  for (let b = 0; b <= BANDS; b++) edges.push(30 * Math.pow(16000 / 30, b / BANDS));
  const binOf = (f) => Math.max(1, Math.min(N / 2 - 1, Math.round(f / sr * N)));
  const re = new Float32Array(N), im = new Float32Array(N);
  const sm = new Float32Array(BANDS), prev = new Float32Array(BANDS);
  let sl = -60, lastL = -60;
  const len = pcm.length / 2;
  const hop = sr / fps;
  for (let f = 0; f < frames; f++) {
    const c = Math.round(f * hop);                      // the frame's moment (window centred on it)
    for (let i = 0; i < N; i++) {
      const k = c - N / 2 + i;
      const v = k >= 0 && k < len ? (pcm[2 * k] + pcm[2 * k + 1]) * 0.5 : 0;
      re[i] = v * win[i]; im[i] = 0;
    }
    fft(re, im);
    let lo = 0, hi = 0;
    for (let b = 0; b < BANDS; b++) {
      const a = binOf(edges[b]), z = Math.max(a + 1, binOf(edges[b + 1]));
      let e = 0;
      for (let i = a; i < z; i++) e += re[i] * re[i] + im[i] * im[i];
      const db = 10 * Math.log10(e / (z - a) + 1e-12) - 20 * Math.log10(N / 4);
      const x = Math.max(0, Math.min(1, (db + 72) / 66));
      sm[b] = x > sm[b] ? sm[b] + (x - sm[b]) * 0.65 : sm[b] + (x - sm[b]) * 0.14;   // ~45 ms attack, ~230 ms release
      bands[f * BANDS + b] = Math.round(sm[b] * 255);
      const d = Math.max(0, x - prev[b]);
      if (b < 10) lo += d; else if (b > 22) hi += d;
      prev[b] = x;
    }
    fluxLo[f] = lo; fluxHi[f] = hi;
    // loudness of the frame (+-1 frame), width (side / mid)
    const a0 = Math.max(0, Math.round((f - 1) * hop)), a1 = Math.min(len, Math.round((f + 1) * hop));
    let m2 = 0, s2 = 0;
    for (let k = a0; k < a1; k++) {
      const l = pcm[2 * k], r = pcm[2 * k + 1];
      m2 += (l + r) * (l + r) * 0.25; s2 += (l - r) * (l - r) * 0.25;
    }
    const n = Math.max(1, a1 - a0);
    const ldb = 10 * Math.log10((m2 + s2) / n + 1e-12);
    lastL = ldb > lastL ? lastL + (ldb - lastL) * 0.5 : lastL + (ldb - lastL) * 0.12;
    loud[f] = lastL;
    sl += (ldb - sl) * (1 / (fps * 2.5));
    slow[f] = sl;
    width[f] = Math.sqrt(s2 / (m2 + 1e-12));
    // vectorscope: the last 2 frames of samples, decimated
    const s0 = Math.max(0, c - Math.round(2 * hop));
    const step = Math.max(1, Math.floor((c - s0) / SCOPE));
    for (let i = 0; i < SCOPE; i++) {
      let l = 0, r = 0, n = 0;          // the mean of each step: a smooth trace, not aliased spikes
      for (let k = s0 + i * step; k < Math.min(len, s0 + (i + 1) * step); k++) { l += pcm[2 * k]; r += pcm[2 * k + 1]; n++; }
      if (n) { l /= n; r /= n; }
      scope[(f * SCOPE + i) * 2] = Math.max(-127, Math.min(127, Math.round(l * 180)));
      scope[(f * SCOPE + i) * 2 + 1] = Math.max(-127, Math.min(127, Math.round(r * 180)));
    }
  }
  // onsets: flux peaks over an adaptive threshold (mean + 1.6 sd over +-0.4 s), at least 90 ms apart
  const onsets = [];
  for (const [flux, kind] of [[fluxLo, 'lo'], [fluxHi, 'hi']]) {
    const w = Math.round(0.4 * fps);
    let last = -1e9;
    for (let f = 1; f < frames - 1; f++) {
      let s = 0, s2 = 0, n = 0;
      for (let k = Math.max(0, f - w); k < Math.min(frames, f + w); k++) { s += flux[k]; s2 += flux[k] * flux[k]; n++; }
      const mean = s / n, sd = Math.sqrt(Math.max(0, s2 / n - mean * mean));
      if (flux[f] > mean + 1.6 * sd && flux[f] > 0.25 && flux[f] >= flux[f - 1] && flux[f] >= flux[f + 1]
          && f - last > 0.09 * fps) {
        onsets.push({ f, t: f / fps, s: Math.min(1, flux[f] / 3), kind });
        last = f;
      }
    }
  }
  onsets.sort((a, b) => a.f - b.f);
  return { frames, fps, bands, loud, slow, width, fluxLo, fluxHi, scope, onsets };
}

export function save(dir, feat, stamp) {
  const parts = [feat.bands, feat.loud, feat.slow, feat.width, feat.fluxLo, feat.fluxHi, feat.scope];
  const layout = []; let off = 0;
  const names = ['bands', 'loud', 'slow', 'width', 'fluxLo', 'fluxHi', 'scope'];
  parts.forEach((p, i) => { layout.push({ name: names[i], offset: off, bytes: p.byteLength, type: p.constructor.name });
    off += Math.ceil(p.byteLength / 4) * 4; });
  const buf = Buffer.alloc(off);
  parts.forEach((p, i) => Buffer.from(p.buffer, p.byteOffset, p.byteLength).copy(buf, layout[i].offset));
  fs.writeFileSync(`${dir}/features.bin`, buf);
  fs.writeFileSync(`${dir}/features.json`, JSON.stringify({ stamp, frames: feat.frames, fps: feat.fps, bands: BANDS,
    scope: SCOPE, layout, onsets: feat.onsets }));
}

export function cached(dir, stamp) {
  try {
    const meta = JSON.parse(fs.readFileSync(`${dir}/features.json`, 'utf8'));
    if (JSON.stringify(meta.stamp) === JSON.stringify(stamp) && fs.existsSync(`${dir}/features.bin`)) return meta;
  } catch { /* not cached */ }
  return null;
}
