// Endless Piano / Orchester - the player.
//   compose-worker.js: Pyodide + the AgentSound composer (the endless set loop, best of N per piece)
//   engine-worker.js:  the AgentSound engine (WASM): render JSON -> streamed 16-bit PCM
//   here: the bank (natively pre-composed set openings), the pool of ready pieces, compact storage (Opus via
//   WebCodecs, else 16-bit PCM), playback with seeking, the history (recipes in localStorage).
const A = 'p11';                     // page revision (app.js / the shell only: the bank, recipes and links stay valid)
const V = 'web7-925b025c26';           // code version: recipes / links of another version are made anew with this code (noted)
const SV = 'b58083a615';                      // the content hash of samples/index.json (wasm-space/prod/asset_version.py writes it)
const PYV = '314.0.7';              // Pyodide (the compose worker loads it from the CDN; the service worker caches it)
const store = import(`./store.js?v=${V}&a=${A}`);   // Cache Storage: the samples, the bank, the composer zip stay offline
const CODE_CACHE = `endless-code-${V}`, SAMPLE_CACHE = 'endless-samples';   // (sample URLs carry each file's content hash)
// samples/index.json: {set: {file: content hash}} for beste / spar / orch / ir - every sample URL is
// samples/<set>/<file>?h=<hash>, so an update of the samples fetches only the files that changed
let HASH = null;
async function hashes() {
  if (!HASH) HASH = JSON.parse(new TextDecoder().decode((await (await store).cachedBuffer(`samples/index.json?s=${SV}`, SAMPLE_CACHE)).buf));
  return HASH;
}
const surl = (set, file) => `samples/${set}/${encodeURIComponent(file)}?h=${(HASH[set] || {})[file] || '0'}`;
const irUrl = (base) => surl('ir', base in HASH.ir ? base : 'French 18th Century Salon.wav');
const SR = 48000;
const GAP = 2.5;                    // silence between pieces (the render already ends in its reverb tail)
const AHEAD = 4;                    // seconds of decoded audio scheduled ahead
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const MUTE = params.has('mute');
const M = window.__metrics = { events: [], errors: [] };
const mark = (name, extra) => M.events.push({ name, t: +(performance.now() / 1000).toFixed(2), ...extra });
// Keep failures visible independently of the frequently refreshed transport status.
function reportError(error) {
  const detail = String(error && error.message || error);
  M.errors.push(detail);
  const box = $('error-panel');
  if (!box) return;
  box.hidden = false;
  $('error-message').textContent = detail.startsWith('buffer-underrun:')
    ? 'Der Audiopuffer ist während des Stücks leer gelaufen. Die Musik wartet auf weitere Audiodaten und läuft dann automatisch weiter. Lass die Seite möglichst im Vordergrund.'
    : /engine|encoder|decoder|sourcebuffer|mse:/i.test(detail)
    ? 'Die Audio-Berechnung oder Wiedergabe hat einen Fehler gemeldet. Falls die Musik steht, versuche „Weiter“ oder überspringe das Stück.'
    : /composer/i.test(detail)
    ? 'Das nächste Stück konnte nicht erzeugt werden. Bereits fertige Musik kann weiterlaufen.'
    : /play:|NotAllowedError/i.test(detail)
    ? 'Der Browser hat die Wiedergabe blockiert. Tippe auf Abspielen beziehungsweise Weiter.'
    : 'Es ist ein Fehler aufgetreten. Die Details unten helfen bei der Fehlersuche.';
  $('error-details').textContent = M.errors.slice(-20).join('\n');
}
window.addEventListener('error', e => reportError('Browser: ' + (e.message || 'Unbekannter Fehler')));
window.addEventListener('unhandledrejection', e => reportError('Browser: ' + String(e.reason)));


const GENRES = ['new-age', 'klassik', 'walzer', 'orchester'];
const GENRE_NAME = { 'new-age': 'New Age', klassik: 'Klassisch', walzer: 'Walzer', orchester: 'Orchester' };
const ORCH = (g) => g === 'orchester';
const PIANOS = ['beste', 'spar'];
const FEEL = { flowing: 'fließend', gentle: 'sanft', bright: 'hell', waltz: 'Walzer', nocturne: 'Nocturne',
               allegro: 'Allegro', vivace: 'Vivace', scherzo: 'Scherzo', river: 'Flusslauf', andante: 'Andante' };
const SECTION = { intro: 'Intro', coda: 'Coda', interlude: 'Zwischenspiel', climax: 'Höhepunkt', build: 'Steigerung', end: 'Ausklang',
                  t: 'Thema', t1: 'Hauptthema', t1b: 'Hauptthema', trans: 'Überleitung', t2: 'Seitenthema', t2b: 'Seitenthema',
                  close: 'Schlussgruppe', dev: 'Durchführung', false: 'Scheinreprise', retrans: 'Rückführung', recap: 'Reprise',
                  source: 'Quelle', river: 'Fluss', hunt: 'Jagd', storm: 'Sturm', fugato: 'Fugato', broad: 'Breit',
                  a: 'Refrain', b: 'Couplet', c: 'Couplet', theme: 'Thema', var: 'Variation', mid: 'Mittelteil', slow: 'Einleitung',
                  solo: 'Solo', trio: 'Trio', scherzo: 'Scherzo', episode: 'Episode', refrain: 'Refrain' };
const secName = (n) => SECTION[n] || SECTION[n.replace(/\d+$/, '')] || n;

// ---------------------------------------------------------------- capabilities and the memory budget
const mobile = matchMedia('(pointer: coarse)').matches || /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
const devMem = navigator.deviceMemory;          // Chrome only (capped at 8); undefined elsewhere
let OPUS = false;
async function probeOpus() {
  try {
    if (typeof AudioEncoder === 'undefined' || typeof AudioDecoder === 'undefined') return false;
    const cfg = { codec: 'opus', sampleRate: SR, numberOfChannels: 2, bitrate: 160000 };
    const a = await AudioEncoder.isConfigSupported(cfg);
    const b = await AudioDecoder.isConfigSupported({ codec: 'opus', sampleRate: SR, numberOfChannels: 2 });
    return !!(a.supported && b.supported);
  } catch (e) { return false; }
}
let POOL = 2, KEEP = 1;
const poolFor = (g) => (ORCH(g) ? (mobile ? 1 : 2) : POOL);   // the orchestra: ~20 MB of samples, ~0.5 GB to render

// ---------------------------------------------------------------- state
const state = {
  genre: GENRES.includes(params.get('genre')) ? params.get('genre') : 'new-age',   // (phones too: the piano is the default)
  piano: PIANOS.includes(params.get('piano')) ? params.get('piano') : 'beste',
  gen: 0, playing: false, clicked: false, session: null,
};
$('genre').value = state.genre; $('piano').value = state.piano;
function pianoUi() { $('piano').disabled = ORCH(state.genre); $('orch-note').hidden = !ORCH(state.genre); }
let ctx = null, out = null, sampleDecoder = null;
let current = null, player = null;
let pool = [];                      // the set's next pieces, in order
let played = [];                    // the last pieces played (newest first), kept for "Zurück"
let nextId = 1;
const compressed = new Map();       // Opus sample url -> ArrayBuffer (fetched once per session)
let bankIndex = null;

function audio() {
  if (ctx) return;
  if (USE_MSE) { stream = new MseStream(); ctx = mediaClock(); return; }
  ctx = new AudioContext({ latencyHint: 'playback', sampleRate: SR });
  out = ctx.createGain(); out.gain.value = MUTE ? 0 : 1; out.connect(ctx.destination);
  ctx.onstatechange = () => { if (ctx.state !== 'running' && state.playing) resumeSoon('audiocontext ' + ctx.state); };
}
function decoderCtx() { if (!sampleDecoder) sampleDecoder = new OfflineAudioContext(2, 1, SR); return sampleDecoder; }

// ---------------------------------------------------------------- compact storage of a rendered piece
class PcmStore {
  constructor() { this.kind = 'pcm'; this.chunks = []; this.starts = []; this.frames = 0; this.complete = false; this.bytes = 0; }
  add(pcm, n) { this.starts.push(this.frames); this.chunks.push(pcm); this.frames += n; this.bytes += pcm.byteLength; }
  async finish() { this.complete = true; }
  seconds() { return this.frames / SR; }
  free() { this.chunks = []; this.starts = []; this.bytes = 0; }
}
class OpusStore {
  constructor() {
    this.kind = 'opus'; this.packets = []; this.bytes = 0; this.frames = 0; this.until = 0; this.complete = false; this.cfg = null;
    this.encodeMs = 0;
    this.enc = new AudioEncoder({
      output: (chunk, meta) => {
        const d = new Uint8Array(chunk.byteLength); chunk.copyTo(d);
        this.packets.push({ ts: chunk.timestamp, dur: chunk.duration || 20000, d });
        this.bytes += d.byteLength; this.until = (chunk.timestamp + (chunk.duration || 20000)) / 1e6;
        if (meta && meta.decoderConfig && !this.cfg) this.cfg = meta.decoderConfig;
      },
      error: (e) => { this.err = e; reportError('encoder: ' + e); },
    });
    this.enc.configure({ codec: 'opus', sampleRate: SR, numberOfChannels: 2, bitrate: 128000 });   // (128k: 3 pieces fit the stream)
  }
  add(pcm, n) {
    const t = performance.now();
    const ad = new AudioData({ format: 's16', sampleRate: SR, numberOfFrames: n, numberOfChannels: 2,
                               timestamp: Math.round(this.frames * 1e6 / SR), data: pcm });
    this.enc.encode(ad); ad.close();
    this.frames += n;
    this.encodeMs += performance.now() - t;
  }
  async finish() { const t = performance.now(); await this.enc.flush(); this.flushMs = performance.now() - t; this.enc.close(); this.complete = true; }
  seconds() { return this.until; }
  free() { this.packets = []; this.bytes = 0; try { this.enc.close(); } catch (e) { /* closed */ } }
}
const newStore = () => (OPUS ? new OpusStore() : new PcmStore());

// ---------------------------------------------------------------- playback of one piece (seekable)
class Player {
  constructor(piece, offset, startAt) {
    this.p = piece; this.offset = offset; this.next = startAt; this.t0 = startAt - offset;
    this.sources = new Set(); this.dead = false; this.endTime = null; this.first = null;
  }
  ahead() { return this.next - ctx.currentTime; }
  position() { if (this.first === null) return this.offset; return Math.max(0, Math.min(ctx.currentTime - this.t0, this.p.info ? this.p.info.seconds + 10 : 1e9)); }
  play(L, R, n) {
    const now = ctx.currentTime;
    if (this.next < now + 0.02) { const s = now + 0.06 - this.next; this.next += s; this.t0 += s; }   // late data: re-anchor
    const buf = ctx.createBuffer(2, n, SR);
    buf.copyToChannel(L, 0); buf.copyToChannel(R, 1);
    const src = ctx.createBufferSource(); src.buffer = buf; src.connect(out);
    src.onended = () => { this.sources.delete(src); src.disconnect(); };
    src.start(this.next); this.sources.add(src);
    if (this.first === null) { this.first = this.next; this.onFirst && this.onFirst(this.next); }
    this.next += n / SR;
  }
  stop() {
    this.dead = true;
    for (const s of this.sources) { try { s.stop(); } catch (e) { /* stopped */ } s.disconnect(); }
    this.sources.clear();
  }
}
class PcmPlayer extends Player {
  constructor(piece, offset, startAt) { super(piece, offset, startAt); this.pos = Math.round(offset * SR); }
  pump() {
    const st = this.p.store;
    if (this.dead || !st) return;
    let guard = 0;
    while (this.ahead() < AHEAD && guard++ < 32) {
      if (this.pos >= st.frames) { if (st.complete && this.endTime === null) this.endTime = Math.max(this.next, ctx.currentTime); return; }
      let k = st.starts.length - 1;
      while (k > 0 && st.starts[k] > this.pos) k--;
      const c = st.chunks[k], from = this.pos - st.starts[k], n = Math.min(c.length / 2 - from, 24000);
      const L = new Float32Array(n), R = new Float32Array(n);
      for (let i = 0, j = 2 * from; i < n; i++) { L[i] = c[j++] / 32768; R[i] = c[j++] / 32768; }
      this.play(L, R, n); this.pos += n;
    }
  }
}
class OpusPlayer extends Player {
  constructor(piece, offset, startAt) {
    super(piece, offset, startAt);
    this.trim = offset; this.feed = -1; this.inflight = 0; this.flushing = false; this.drained = false;
    this.acc = []; this.accN = 0; this.dec = null;
  }
  open() {
    const st = this.p.store;
    if (!st.packets.length) return false;
    this.dec = new AudioDecoder({ output: (ad) => this.out(ad), error: (e) => { reportError('decoder: ' + e); } });
    this.dec.configure(st.cfg || { codec: 'opus', sampleRate: SR, numberOfChannels: 2 });
    const want = (this.offset - 0.12) * 1e6;     // a little pre-roll: the decoder settles before the seek point
    let i = 0;
    while (i < st.packets.length - 1 && st.packets[i + 1].ts <= want) i++;
    this.feed = this.offset > 0 ? i : 0;
    return true;
  }
  pump() {
    const st = this.p.store;
    if (this.dead || !st) return;
    if (!this.dec && !this.open()) return;
    while (this.feed < st.packets.length && this.ahead() + (this.inflight * 0.02) + this.accN / SR < AHEAD && this.inflight < 100) {
      const k = st.packets[this.feed++];
      this.dec.decode(new EncodedAudioChunk({ type: 'key', timestamp: k.ts, duration: k.dur, data: k.d }));
      this.inflight++;
    }
    if (st.complete && this.feed >= st.packets.length && !this.flushing) {
      this.flushing = true;
      this.dec.flush().then(() => { this.flushAcc(); this.drained = true; this.endTime = Math.max(this.next, ctx.currentTime); })
        .catch(() => {});
    }
  }
  out(ad) {
    this.inflight--;
    if (this.dead) { ad.close(); return; }
    const n = ad.numberOfFrames, t = ad.timestamp / 1e6;
    const L = new Float32Array(n), R = new Float32Array(n);
    ad.copyTo(L, { planeIndex: 0, format: 'f32-planar' });
    if (ad.numberOfChannels > 1) ad.copyTo(R, { planeIndex: 1, format: 'f32-planar' }); else R.set(L);
    ad.close();
    let a = 0;
    if (t + n / SR <= this.trim) return;
    if (t < this.trim) a = Math.min(n, Math.round((this.trim - t) * SR));
    this.acc.push([L.subarray(a), R.subarray(a)]); this.accN += n - a;
    if (this.accN >= 24000) this.flushAcc();
  }
  flushAcc() {
    if (!this.accN || this.dead) return;
    const L = new Float32Array(this.accN), R = new Float32Array(this.accN);
    let o = 0;
    for (const [l, r] of this.acc) { L.set(l, o); R.set(r, o); o += l.length; }
    this.acc = []; const n = this.accN; this.accN = 0;
    this.play(L, R, n);
  }
}
const newPlayer = (piece, offset, startAt) => (USE_MSE ? new MsePlayer(piece, offset) : piece.store && piece.store.kind === 'pcm' ? new PcmPlayer(piece, offset, startAt) : new OpusPlayer(piece, offset, startAt));

// ---------------------------------------------------------------- one continuous media stream (Android / desktop)
// The OS keeps a playing <audio> element alive with the screen off (Web Audio and timers get throttled or suspended):
// every piece's Opus packets (the pool's WebCodecs encode) go, muxed as WebM, into ONE Media Source SourceBuffer -
// the current piece, a short silence, the next ready pieces - appended as soon as they are rendered (also in the
// background, as far as the browser lets the workers run). While nothing is ready the stream plays silence, so it
// never breaks; a skip / seek / another piece cuts the stream at the playhead and appends from there.
const MSE_TYPE = 'audio/webm; codecs="opus"';
const MS = window.ManagedMediaSource || window.MediaSource;
const AHEAD_BYTES = 9e6;            // appended ahead of the playhead at most (Chrome: ~12 MB per audio SourceBuffer)
let USE_MSE = false;
let silence = null;                 // GAP seconds of encoded silence (packets)

const EB = {
  id: (n) => { const b = []; while (n > 0) { b.unshift(n & 255); n = Math.floor(n / 256); } return b; },
  size: (n) => { const b = [1, 0, 0, 0, 0, 0, 0, 0]; for (let i = 7; i > 0; i--) { b[i] = n % 256; n = Math.floor(n / 256); } return b; },
  uint: (v) => { const b = []; do { b.unshift(v % 256); v = Math.floor(v / 256); } while (v > 0); return b; },
};
function cat(parts) {
  let n = 0; for (const p of parts) n += p.length;
  const out = new Uint8Array(n); let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}
const u8 = (p) => (p instanceof Uint8Array ? p : Uint8Array.from(p));
function el(id, ...parts) {         // an EBML element: id, size (8-byte vint), the parts (byte lists or Uint8Arrays)
  const body = cat(parts.map(u8));
  return cat([Uint8Array.from(EB.id(id)), Uint8Array.from(EB.size(body.length)), body]);
}
const str = (s) => Array.from(s, (c) => c.charCodeAt(0));
function f64(v) { const b = new Uint8Array(8); new DataView(b.buffer).setFloat64(0, v); return b; }
function opusHead(cfg) {
  const d = cfg && cfg.description;
  if (d && d.byteLength >= 19) return d instanceof ArrayBuffer ? new Uint8Array(d.slice(0)) : new Uint8Array(d.buffer.slice(d.byteOffset, d.byteOffset + d.byteLength));
  const b = new Uint8Array(19), v = new DataView(b.buffer);
  b.set(str('OpusHead')); b[8] = 1; b[9] = 2; v.setUint16(10, 312, true); v.setUint32(12, SR, true); v.setInt16(16, 0, true); b[18] = 0;
  return b;
}
function webmInit(cfg) {
  const head = opusHead(cfg);
  const preskip = head[10] | (head[11] << 8);
  const ebml = el(0x1A45DFA3, el(0x4286, EB.uint(1)), el(0x42F7, EB.uint(1)), el(0x42F2, EB.uint(4)), el(0x42F3, EB.uint(8)),
                  el(0x4282, str('webm')), el(0x4287, EB.uint(4)), el(0x4285, EB.uint(2)));
  const info = el(0x1549A966, el(0x2AD7B1, EB.uint(1000000)), el(0x4D80, str('AgentSound')), el(0x5741, str('AgentSound')));
  const track = el(0xAE, el(0xD7, EB.uint(1)), el(0x73C5, EB.uint(1)), el(0x83, EB.uint(2)), el(0x86, str('A_OPUS')),
                   el(0x63A2, head), el(0x56AA, EB.uint(Math.round(preskip * 1e9 / SR))), el(0x56BB, EB.uint(80000000)),
                   el(0xE1, el(0xB5, f64(SR)), el(0x9F, EB.uint(2))));
  const segHead = Uint8Array.from([0x18, 0x53, 0x80, 0x67, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]);   // unknown size
  return cat([ebml, segHead, info, el(0x1654AE6B, track)]);
}
// packets at absolute media times (seconds) [{t, d}] -> WebM clusters (one per <= 10 s, 1 ms timecodes)
function webmClusters(list) {
  const out = [];
  for (let i = 0; i < list.length;) {
    const tc = Math.round(list[i].t * 1000);
    const blocks = [];
    while (i < list.length && Math.round(list[i].t * 1000) - tc < 10000) {
      const rel = Math.round(list[i].t * 1000) - tc;
      blocks.push(el(0xA3, Uint8Array.from([0x81, (rel >> 8) & 255, rel & 255, 0x80]), list[i].d));
      i++;
    }
    out.push(el(0x1F43B675, el(0xE7, EB.uint(tc)), ...blocks));
  }
  return cat(out);
}
async function encodeSilence() {
  const pk = [];
  const enc = new AudioEncoder({ output: (c) => { const d = new Uint8Array(c.byteLength); c.copyTo(d); pk.push({ ts: c.timestamp, d }); }, error: () => {} });
  enc.configure({ codec: 'opus', sampleRate: SR, numberOfChannels: 2, bitrate: 32000 });
  const n = Math.round(GAP * SR);
  enc.encode(new AudioData({ format: 's16', sampleRate: SR, numberOfFrames: n, numberOfChannels: 2, timestamp: 0, data: new Int16Array(2 * n) }));
  await enc.flush(); enc.close();
  return pk.filter((p) => p.ts < GAP * 1e6);
}
async function probeMse() {
  try {
    if (!OPUS || !MS || !MS.isTypeSupported(MSE_TYPE) || params.has('webaudio')) return false;
    silence = await encodeSilence();
    return silence.length > 0;
  } catch (e) { return false; }
}

class MseStream {
  constructor() {
    this.audio = $('out');
    this.audio.volume = MUTE ? 0 : 1;   // (?mute=1: volume 0, not muted - browsers pause muted media in hidden pages)
    this.audio.disableRemotePlayback = true;        // (ManagedMediaSource needs it)
    this.ms = new MS();
    this.sb = null; this.ops = []; this.inited = false; this.segs = []; this.end = 0; this.full = 0; this.lastEvict = 0;
    this.audio.src = URL.createObjectURL(this.ms);
    this.ms.addEventListener('sourceopen', () => {
      this.sb = this.ms.addSourceBuffer(MSE_TYPE);
      this.sb.mode = 'segments';
      this.sb.addEventListener('updateend', () => { this.ops.shift(); this.run(); });
      this.sb.addEventListener('error', () => reportError('sourcebuffer error'));
      this.run();
      if (state.playing) this.audio.play().catch(() => {});
    });
  }
  run() {
    if (!this.sb || this.sb.updating || !this.ops.length || this.ms.readyState !== 'open') return;
    const op = this.ops[0];
    try {
      if (op.kind === 'append') this.sb.appendBuffer(op.data);
      else {
        const r = this.sb.buffered, b = Math.min(op.b, r.length ? r.end(r.length - 1) : 0);   // (remove() must stay in range)
        if (b > op.a) this.sb.remove(op.a, b); else { this.ops.shift(); this.run(); }
      }
    } catch (e) {
      if (e.name === 'QuotaExceededError') { this.full = 1; this.evict(true); return; }   // retried after the eviction
      reportError('mse: ' + e.name + ' ' + e.message); this.ops.shift(); this.run();
    }
  }
  op(o) { this.ops.push(o); this.run(); }
  append(list, cfg) {
    if (!list.length) return;
    if (!this.inited) { this.op({ kind: 'append', data: webmInit(cfg) }); this.inited = true; }
    this.op({ kind: 'append', data: webmClusters(list) });
  }
  evict(force) {
    const t = this.audio.currentTime;
    if (!force && performance.now() - this.lastEvict < 15000) return;
    this.lastEvict = performance.now();
    const b = this.sb && this.sb.buffered;
    if (t > 25 && b && b.length && b.start(0) < t - 20) {
      if (this.sb.updating) this.ops.splice(1, 0, { kind: 'remove', a: 0, b: t - 20 });
      else this.ops.unshift({ kind: 'remove', a: 0, b: t - 20 });
    }
    if (force) setTimeout(() => { this.full = 0; this.run(); }, 3000);
    this.run();
  }
  aheadBytes() { const t = this.audio.currentTime; return this.segs.reduce((s, g) => s + (g.base !== null && g.base + g.until > t ? g.bytes : 0), 0); }
  silenceAt(t0) { this.append(silence.map((p) => ({ t: t0 + p.ts / 1e6, d: p.d })), null); this.end = t0 + GAP; }
  // cut the stream at the playhead: everything after it goes, `piece` from `offset` comes next
  cut(piece, offset) {
    const T = this.audio.currentTime;
    this.ops = this.ops.filter((o, i) => i === 0 && this.sb && this.sb.updating);
    this.op({ kind: 'remove', a: T + 0.05, b: Infinity });
    const b = this.sb && this.sb.buffered;
    this.end = b && b.length && b.end(b.length - 1) > T ? T + 0.1 : T;   // (an empty stream: no gap at its start)
    this.segs = [];
    const seg = this.newSeg(piece, Math.max(0, offset - 0.1));
    seg.seekTo = offset;
    mark('stream-cut', { id: piece.id, at: +T.toFixed(2), offset: +offset.toFixed(2) });
    return seg;
  }
  newSeg(piece, from) { const s = { piece, from, base: null, n: -1, until: 0, bytes: 0, done: false, endT: null }; this.segs.push(s); return s; }
  // append what is ready, in order: chain = [current, ...the pool]
  pump(chain) {
    if (!this.sb) return;
    this.evict(false);
    const at = this.audio.currentTime;
    // the pieces appended after the playing one must be the pool's, in order: else the stream is cut behind it
    const k = this.segs.findIndex((s) => s.piece === chain[0]);
    if (k >= 0) {
      for (let i = k + 1; i < this.segs.length; i++) {
        if (this.segs[i].piece === chain[i - k]) continue;
        const prev = this.segs[i - 1];
        const from = Math.max(at + 0.1, prev.done ? prev.endT + GAP : this.end);
        this.ops = this.ops.filter((o, j) => j === 0 && this.sb.updating);   // (nothing queued for the pieces dropped)
        this.op({ kind: 'remove', a: from, b: Infinity });
        this.segs.length = i;
        if (!prev.done) { prev.done = false; }
        this.end = from;
        break;
      }
    }
    for (let guard = 0; guard < 8; guard++) {
      const last = this.segs[this.segs.length - 1];
      if (!last) return;
      const st = last.piece.store;
      if (!last.done) {
        if (!st || last.piece.dropped) return this.fill(at);
        if (last.n < 0 && !enough(last.piece)) return this.fill(at);   // (its render must stay ahead of the playback)
        if (this.full) return;
        const pk = st.packets;
        if (last.n < 0) {                              // its first packet: where the stream is now
          let i = 0;
          while (i < pk.length && pk[i].ts / 1e6 < last.from) i++;
          if (i >= pk.length) return this.fill(at);
          last.n = i;
          last.base = this.end - pk[i].ts / 1e6;
          if (last.seekTo !== undefined) { this.audio.currentTime = Math.max(at, last.base + last.seekTo); last.seekTo = undefined; }
        }
        if (last.n < pk.length) {
          const list = [];
          for (let i = last.n; i < pk.length; i++) { list.push({ t: last.base + pk[i].ts / 1e6, d: pk[i].d }); last.bytes += pk[i].d.length; }
          this.append(list, st.cfg);
          last.n = pk.length;
          last.until = (pk[pk.length - 1].ts + pk[pk.length - 1].dur) / 1e6;
          this.end = last.base + last.until;
        }
        if (!(st.complete && last.n >= pk.length)) return;
        last.done = true; last.endT = last.base + st.until;
        this.silenceAt(Math.max(this.end, last.endT));
      }
      const next = chain[chain.indexOf(last.piece) + 1];
      if (!next || !next.store || next.dropped || this.aheadBytes() > AHEAD_BYTES) return this.fill(at);
      this.newSeg(next, 0);
    }
  }
  fill(at) {                        // nothing to append yet: the stream plays silence on (never a gap)
    if (this.sb && !this.full && at > this.end - 2) {
      const last = this.segs[this.segs.length - 1];
      if (last && !last.done && last.base !== null) return;   // (a piece rendering: its data comes)
      this.silenceAt(this.end);
    }
  }
}
let stream = null;

// the player of one piece on the stream (the interface of the Web Audio players: position, pump, stop, endTime)
class MsePlayer {
  constructor(piece, offset) {
    this.p = piece; this.offset = offset; this.dead = false; this.first = null; this.endTime = null;
    const S = stream, a = S.audio;
    const seg = S.segs.find((s) => s.piece === piece);
    let keep = false;
    const idx = seg ? S.segs.indexOf(seg) : -1, prev = idx > 0 ? S.segs[idx - 1] : null;
    if (seg && offset === 0 && prev && (seg.base !== null || (prev.done && a.currentTime >= prev.endT - 0.2))) {
      keep = true;                                  // the next piece, appended after the one before (or due now)
      if (seg.base !== null && a.currentTime < seg.base - GAP - 0.5) a.currentTime = Math.max(0, seg.base - 0.05);  // (a skip)
    } else if (seg && seg.base !== null && offset >= seg.from && seg.base + offset < S.end - 0.2) {   // a seek inside it
      keep = true;
      a.currentTime = seg.base + offset;
    }
    if (keep) {
      this.seg = seg;
      S.segs.splice(0, S.segs.indexOf(seg));
    } else this.seg = S.cut(piece, offset);
    if (a.paused && state.playing) a.play().catch((e) => reportError('play: ' + e.name));
  }
  position() {
    const s = this.seg;
    if (s.base === null) return this.offset;
    return Math.max(0, Math.min(stream.audio.currentTime - s.base, this.p.info ? this.p.info.seconds + 10 : 1e9));
  }
  pump() {
    if (this.dead) return;
    stream.pump([current, ...pool]);
    const s = this.seg;
    if (s.done && this.endTime === null) this.endTime = s.endT;
    if (this.first === null && s.base !== null && stream.audio.currentTime > s.base + s.from + 0.02 && !stream.audio.paused) {
      this.first = stream.audio.currentTime; this.onFirst && this.onFirst(this.first);
    }
  }
  stop() { this.dead = true; }
}
// the clock the transport reads (ctx.currentTime, resume, suspend): the stream's media element
function mediaClock() {
  return {
    get currentTime() { return stream.audio.currentTime; },
    get state() { return stream.audio.paused ? 'suspended' : 'running'; },
    resume() { stream.audio.play().catch((e) => reportError('play: ' + e.name)); return Promise.resolve(); },   // (play() waits for data: never awaited)
    suspend() { stream.audio.pause(); return Promise.resolve(); },
  };
}


// ---------------------------------------------------------------- pieces
// piece: {id, gen, kind: 'bank'|'set'|'history', status: 'loading'|'composing'|'queued'|'samples'|'rendering'|'ready'|'failed',
//         info, recipe, hash, tune, render (text until rendered), store, verify}
function newPiece(kind, extra) {
  return { id: nextId++, gen: state.gen, kind, status: 'loading', info: null, store: null, urgent: false, ...extra };
}
function adopt(piece, o, piano) {
  piece.info = o.info; piece.recipe = o.recipe; piece.hash = o.hash; piece.tune = o.tune; piece.render = o.render;
  piece.piano = piano;
  piece.expected = Math.round((o.info.seconds + 4) * SR);
}
function freePiece(p) {
  if (!p || p === current || pool.includes(p) || played.includes(p)) return;
  if (p.store) p.store.free();
  p.store = null; p.render = null; p.dropped = true;
}

// ---------------------------------------------------------------- the bank (natively pre-composed set openings)
async function gunzipJson(url) {
  const { buf } = await (await store).cachedBuffer(url, CODE_CACHE);
  const s = new Response(buf).body.pipeThrough(new DecompressionStream('gzip'));
  return JSON.parse(await new Response(s).text());
}
async function bankPiece(genre, piano, n) {
  if (!bankIndex) bankIndex = JSON.parse(new TextDecoder().decode(await (await store).freshBuffer('bank/index.json', CODE_CACHE)));
  if (bankIndex.v !== V) throw new Error('bank of another version');
  const count = bankIndex.counts[genre] || 0;
  if (!count) throw new Error('empty bank');
  const asked = !(n === undefined || n === null || n < 0 || n >= count);
  if (!asked) n = Math.floor(Math.random() * count);
  let e;
  try { e = await gunzipJson(`bank/${genre}/${n}.json.gz?v=${V}`); }
  catch (err) {                                 // offline: a random opening that is already stored
    const c = !asked && typeof caches !== 'undefined' && await caches.open(CODE_CACHE).catch(() => null);
    const have = c ? (await c.keys()).map((r) => new URL(r.url).pathname.split(`/bank/${genre}/`)[1]).filter((x) => x && /^[0-9]+[.]json[.]gz$/.test(x)).map((x) => parseInt(x, 10)) : [];
    if (!have.length) throw err;
    n = have[Math.floor(Math.random() * have.length)];
    e = await gunzipJson(`bank/${genre}/${n}.json.gz?v=${V}`);
  }
  if (e.v !== V) throw new Error('bank entry of another version');
  if (ORCH(genre)) piano = 'beste';
  if (piano === 'spar') {                       // the mini cut: the same notes, its own zones
    const song = JSON.parse(e.render);
    for (const t of song.tracks) if (e.spar_samples[t.id]) t.instrument.params.samples = e.spar_samples[t.id];
    e.render = JSON.stringify(song); e.hash = e.hash_spar;
  }
  e.recipe = { ...e.recipe, p: piano };
  e.info = { ...e.info, piano, bank: n };
  return { e, n };
}

// ---------------------------------------------------------------- workers
let composer = null, composerReady = false, composeJob = null;
let engine = null, engineJob = null;
const composeQueue = [];            // pieces waiting for the composer, urgent first
const renderQueue = [];             // pieces waiting for the engine, urgent first

function makeComposer() {
  composer = new Worker(new URL(`./compose-worker.js?v=${V}&a=${A}&py=${PYV}`, import.meta.url), { type: 'module' });
  composerReady = false;
  composer.onerror = e => reportError('composer: ' + (e.message || 'Worker abgebrochen'));
  composer.onmessage = (e) => {
    const m = e.data;
    if (m.type === 'ready') {
      composerReady = true; mark('composer-ready', { version: m.version });
      if (m.version !== V) reportError('composer version ' + m.version);
      return pumpWork();
    }
    const p = composeJob && composeJob.id === m.job ? composeJob : null;
    composeJob = null;
    if (m.type === 'composed' && p && !p.dropped) {
      const o = JSON.parse(m.out);
      adopt(p, o, p.piano || state.piano);
      if (o.info.other_version && !(p.wantHash && p.wantHash === o.hash)) notice('Dieses Stück stammt von einer älteren Version der Seite und wurde mit der aktuellen neu erzeugt - es kann anders klingen als damals.');
      if (p.wantHash && !o.info.other_version) {
        p.verify = p.wantHash === o.hash;
        if (!p.verify) reportError(`recipe ${JSON.stringify(o.recipe)}: hash ${o.hash}, expected ${p.wantHash}`);
      }
      p.status = 'queued';
      mark('composed', { id: p.id, kind: p.kind, title: o.info.title, ms: m.ms, candidates: o.info.candidates, hash: o.hash, verify: p.verify });
      renderQueue.push(p);
    } else if (m.type === 'error') {
      reportError('composer: ' + m.message);
      if (p) { p.status = 'failed'; p.error = m.message; pool = pool.filter((q) => q !== p); }
      if (p && p === current && p.kind === 'history') { notice('Dieses Stück lässt sich mit der aktuellen Version nicht mehr erzeugen.'); advance(); }
      if (m.fatal) notice('Der Komponist konnte nicht laden. Die Musik der Bank spielt trotzdem.');
    }
    pumpWork(); ui();
  };
}
function makeEngine() {
  engine = new Worker(new URL(`./engine-worker.js?v=${V}&a=${A}`, import.meta.url), { type: 'module' });
  engine.onerror = e => reportError('engine: ' + (e.message || 'Worker abgebrochen, möglicherweise zu wenig Speicher'));
  engine.onmessage = (e) => {
    const m = e.data;
    if (m.type === 'done' && m.ok === false) { m.type = 'error'; m.message = 'Render-Vorgang fehlgeschlagen; Audio unvollständig'; }
    if (m.type === 'ready') { mark('engine-ready'); return; }
    const p = engineJob && engineJob.id === m.job ? engineJob : null;
    if (m.type === 'chunk') {
      if (p && p.store && !p.dropped) { p.store.add(m.pcm, m.frames); if (p.status !== 'rendering') p.status = 'rendering'; }
      if (player) player.pump();                 // (the stream appends the pool's pieces while they render, too)
      return;
    }
    if (p || m.job === undefined) engineJob = null;
    if (m.type === 'done' && p) {
      mark('rendered', { id: p.id, render_s: m.render_s, first_chunk_s: m.first_chunk_s, realtime_x: m.realtime_x, heapMB: m.heapMB });
      p.render = null;
      if (p.store) p.store.finish().then(() => { p.status = 'ready'; memory(); ui(); }).catch(e => { p.status = 'failed'; reportError('encoder: ' + e); ui(); });
      engine.terminate(); makeEngine();                // a fresh engine for the next piece: its memory goes
    } else if (m.type === 'error') {
      reportError('engine: ' + m.message);
      if (p) { p.status = 'failed'; pool = pool.filter((q) => q !== p); }
    }
    pumpWork(); ui();
  };
}

// a decoded sample as a 16-bit WAV for the engine's file system; loop = [start, end exclusive, pingpong] and
// unity = [note, fraction] go into a 'smpl' chunk (the orchestra's sustains loop on the file's own loop points)
function wav16(ab, loop, unity) {
  const n = ab.length, sr = ab.sampleRate, ch = 2;
  const smpl = loop || unity ? 36 + (loop ? 24 : 0) : 0;
  const head = 44 + (smpl ? 8 + smpl : 0);
  const buf = new ArrayBuffer(head + n * 4), v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, head - 8 + n * 4, true); w(8, 'WAVE'); w(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, ch, true); v.setUint32(24, sr, true);
  v.setUint32(28, sr * 4, true); v.setUint16(32, 4, true); v.setUint16(34, 16, true);
  let o = 36;
  if (smpl) {
    w(o, 'smpl'); v.setUint32(o + 4, smpl, true);
    const b = o + 8;
    for (let i = 0; i < smpl; i += 4) v.setUint32(b + i, 0, true);
    v.setUint32(b + 12, unity ? unity[0] : 60, true); v.setUint32(b + 16, unity ? unity[1] : 0, true);
    if (loop) {
      v.setUint32(b + 28, 1, true);
      v.setUint32(b + 36 + 4, loop[2] ? 1 : 0, true); v.setUint32(b + 36 + 8, loop[0], true); v.setUint32(b + 36 + 12, loop[1] - 1, true);
    }
    o = b + smpl;
  }
  w(o, 'data'); v.setUint32(o + 4, n * 4, true);
  const a = ab.getChannelData(0), c = ab.numberOfChannels > 1 ? ab.getChannelData(1) : a;
  const pcm = new Int16Array(buf, o + 8);
  for (let i = 0, k = 0; i < n; i++) {
    pcm[k++] = Math.max(-32768, Math.min(32767, Math.round(a[i] * 32767)));
    pcm[k++] = Math.max(-32768, Math.min(32767, Math.round(c[i] * 32767)));
  }
  return buf;
}
const safe = (base) => base.replace(/ /g, '_').replace(/#/g, 's');
const decoders = new Map();          // sample rate -> OfflineAudioContext (decodeAudioData resamples to it)
function decoderAt(sr) { if (!decoders.has(sr)) decoders.set(sr, new OfflineAudioContext(2, 1, sr)); return decoders.get(sr); }
let orchIndex = null;                // the orchestra's samples: relpath -> [name, rate, frames, loop, unity]
async function orchestraIndex() {
  if (!orchIndex) {
    await hashes();
    const { buf } = await (await store).cachedBuffer(surl('orch', 'index.json'), SAMPLE_CACHE);
    orchIndex = JSON.parse(new TextDecoder().decode(buf));
  }
  return orchIndex;
}

// the piece's samples, loaded on demand: only the instruments (tracks) this piece plays, each file fetched once per
// visit (kept compressed), decoded for this render; the render JSON gets the engine's paths
async function samplesFor(p) {
  await hashes();
  const song = JSON.parse(p.render);
  const orch = ORCH(p.info.genre);
  const idx = orch ? await orchestraIndex() : null;
  const jobs = new Map();            // name -> {url, sr, loop, unity}
  for (const t of song.tracks) for (const z of (t.instrument.params.samples || [])) {
    let name, job;
    if (orch) {
      const e = idx[z.file.replace(/^.*?assets\//, '')];
      if (!e) throw new Error('Orchesterklang fehlt: ' + z.file.split('/').pop());
      name = e[0]; job = { url: surl('orch', name + '.opus'), sr: e[1], loop: e[3], unity: e[4] };
    } else {
      name = safe(z.file.split('/').pop().replace(/\.wav$/i, ''));
      job = { url: surl(p.piano, name + '.opus'), sr: SR };
    }
    z.file = `s/${name}.wav`;
    jobs.set(name, job);
  }
  const irs = {};
  for (const b of song.buses) for (const f of (b.fx || [])) if (f.params && f.params.ir) {
    const base = f.params.ir.split('/').pop();
    const url = irUrl(base);
    f.params.ir = 'ir/' + safe(decodeURIComponent(url.split('?')[0].split('/').pop()));
    irs[f.params.ir] = url;
  }
  const files = {}, list = [...jobs.entries()];
  let fetched = 0, bytes = 0, done = 0, cached = 0;
  const S = await store;
  const t0 = performance.now();
  p.loading = { n: list.length, done: 0, MB: 0 };
  async function one() {
    while (list.length) {
      const [name, j] = list.shift();
      let data = compressed.get(j.url);
      if (!data) {
        const got = await S.cachedBuffer(j.url, SAMPLE_CACHE);
        data = got.buf; compressed.set(j.url, data);
        if (got.hit) cached++; else { fetched++; bytes += data.byteLength; }
      }
      files[name] = wav16(await decoderAt(j.sr).decodeAudioData(data.slice(0)), j.loop, j.unity);
      p.loading = { n: jobs.size, done: ++done, MB: +(bytes / 1e6).toFixed(1) };
    }
  }
  await Promise.all(Array.from({ length: 6 }, one));
  const MB = +(bytes / 1e6).toFixed(2);
  offlineUi();
  mark('samples', { id: p.id, n: jobs.size, fetched, cached, MB, roles: song.tracks.length, s: +((performance.now() - t0) / 1000).toFixed(2) });
  return { files, irs, cache: SAMPLE_CACHE, render: JSON.stringify(song), sampleRate: song.sampleRate };
}

const byUrgency = (a, b) => (b.urgent - a.urgent);
// the engine renders a piece nobody waits for any more (skipped while it rendered), or the playing piece waits for
// the engine: that render stops - a pool piece renders again later, a piece already left behind is let go
function preemptEngine() {
  const p = engineJob;
  if (!p || p === current) return;
  const waiting = current && !current.dropped && renderQueue.includes(current);
  if (!waiting && pool.includes(p)) return;      // a pool piece renders on; a piece left behind stops
  engine.terminate(); makeEngine(); engineJob = null;
  mark('preempt', { id: p.id, for: current && current.id });
  if (p.store) p.store.free();
  p.store = null;
  if (pool.includes(p)) { p.status = 'queued'; p.urgent = false; renderQueue.push(p); }
  else { played = played.filter((q) => q !== p); p.dropped = true; p.render = null; }
}
async function pumpWork() {
  preemptEngine();
  // the engine: one piece at a time, the urgent (playing / asked for) first
  if (!engineJob) {
    renderQueue.sort(byUrgency);
    while (renderQueue.length && renderQueue[0].dropped) renderQueue.shift();
    const p = renderQueue.shift();
    if (p) {
      engineJob = p; p.status = 'samples';
      try {
        const got = await samplesFor(p);
        if (engineJob !== p) return;                   // preempted while its samples loaded
        if (p.dropped) { engineJob = null; return pumpWork(); }
        p.store = newStore(); p.status = 'rendering'; p.renderT0 = performance.now();
        engine.postMessage({ job: p.id, ...got }, Object.values(got.files));
      } catch (err) {
        reportError(String(err)); p.status = 'failed'; engineJob = null;
        notice('Die Klänge konnten nicht geladen werden: ' + err.message);
      }
    }
  }
  // the composer: one job at a time; the set's next piece only after a click and while the pool has room
  if (composerReady && !composeJob) {
    composeQueue.sort(byUrgency);
    while (composeQueue.length && composeQueue[0].dropped) composeQueue.shift();
    let p = composeQueue.shift();
    if (!p && state.clicked && state.session && state.session.ready && pool.length < POOL &&
        !renderQueue.length && pool.every((q) => q.status !== 'composing') && pool.length < poolFor(state.genre)) {
      p = newPiece('set', { piano: state.piano, status: 'composing' });
      pool.push(p);
      p.cmd = { cmd: 'next' };
    }
    if (p) {
      composeJob = p; p.status = 'composing';
      composer.postMessage({ ...p.cmd, job: p.id });
    }
  }
  ui();
}

// ---------------------------------------------------------------- sessions (a set: the bank's opening, then the composer)
async function startSession(opts = {}) {
  state.gen += 1;
  const gen = state.gen;
  for (const p of pool) { p.dropped = true; freePiece(p); }
  pool = [];
  // a job of the old set still running: restart that worker (the playing piece is never one of them)
  if (composeJob && composeJob !== current) { composeJob.dropped = true; composer.terminate(); composeJob = null; makeComposer(); }
  if (engineJob && engineJob !== current) { engineJob.dropped = true; engine.terminate(); engineJob = null; makeEngine(); }
  for (let i = composeQueue.length - 1; i >= 0; i--) if (composeQueue[i] !== current) composeQueue.splice(i, 1);
  for (let i = renderQueue.length - 1; i >= 0; i--) if (renderQueue[i] !== current) renderQueue.splice(i, 1);
  const genre = state.genre, piano = state.piano;
  state.session = { gen, genre, piano, ready: false, seed: null, bank: null };
  let first;
  if (opts.seed !== undefined && opts.seed !== null) {        // a typed seed: the composer makes the set's first piece
    state.session.seed = opts.seed;
    composer.postMessage({ cmd: 'start', genre, seed: opts.seed, piano });
    state.session.ready = true;
    first = newPiece('set', { piano, status: 'composing', cmd: { cmd: 'next' }, urgent: true });
    composeQueue.push(first);
  } else {
    first = newPiece('bank', { piano, status: 'loading', urgent: true });
    try {
      const { e, n } = await bankPiece(genre, piano, opts.bank);
      if (gen !== state.gen) return;
      adopt(first, e, piano);
      first.status = 'queued';
      state.session.seed = e.S; state.session.bank = n;
      composer.postMessage({ cmd: 'start', genre, seed: e.S, piano, first: e.n_first || null, afterKey: e.info.key });
      state.session.ready = true;
      renderQueue.push(first);
    } catch (err) {                                            // no bank: compose the opening live
      reportError('bank: ' + err.message);
      const seed = Math.floor(Math.random() * 900000) + 100000;
      state.session.seed = seed;
      composer.postMessage({ cmd: 'start', genre, seed, piano });
      state.session.ready = true;
      first.kind = 'set'; first.status = 'composing'; first.cmd = { cmd: 'next' };
      composeQueue.push(first);
    }
  }
  $('seed').value = state.session.seed;
  // before the first click the waiting opening is replaced (another genre / piano); a playing piece plays on
  if (current && !state.clicked && current.kind === 'bank') { const old = current; current = null; old.dropped = true; freePiece(old); }
  if (!current) setCurrent(first);
  else pool.unshift(first);
  mark('session', { genre, piano, seed: state.session.seed, bank: state.session.bank });
  pumpWork();
}

// ---------------------------------------------------------------- transport
function setCurrent(p, offset = 0, startAt = null) {
  if (player) player.stop();
  player = null;
  current = p;
  if (p) { p.urgent = true; resort(); }
  if (p && state.playing && ctx) startPlayer(offset, startAt);
  ui();
}
function resort() { renderQueue.sort(byUrgency); composeQueue.sort(byUrgency); }
function startPlayer(offset = 0, startAt = null) {
  if (!current || !ctx) return;
  if (player) player.stop();
  const at = startAt === null ? ctx.currentTime + 0.05 : startAt;
  const p = current;
  player = newPlayer(p, offset, at);
  player.onFirst = (when) => {
    if (!p.heard) { p.heard = true; remember(p); mark('piece-start', { id: p.id, kind: p.kind, title: p.info && p.info.title }); }
    if (state.waitClick !== undefined) {
      M.firstSound = +((performance.now() - state.waitClick) / 1000 + (when - ctx.currentTime)).toFixed(3);
      mark('first-sound', { s: M.firstSound }); state.waitClick = undefined;
    }
    if (state.skipAt !== undefined) {
      const s = +((performance.now() - state.skipAt) / 1000 + (when - ctx.currentTime)).toFixed(3);
      (M.skips = M.skips || []).push(s); mark('skip-sound', { s }); state.skipAt = undefined;
    }
  };
  if (p.store) player.pump();
}
function canPlay(p) { return p && p.store && (p.store.kind === 'pcm' ? p.store.frames > 0 : p.store.packets.length > 0); }
// a piece the engine still renders starts only when its render stays ahead of the playback to its end: with r seconds
// rendered of s and the render's speed v so far (audio seconds per second, 10 % to spare), r >= s * (1 - v) + 4 s -
// a slow device (the orchestra with choir / soloists / organ renders near real time) waits in silence before the
// piece instead of stalling inside it
function enough(p) {
  if (!canPlay(p)) return false;
  if (p.status === 'ready' || p.store.complete) return true;
  const r = p.store.frames / SR, s = (p.info && p.info.seconds) || r;
  const wall = (performance.now() - (p.renderT0 || performance.now())) / 1000;
  if (wall < 2) return false;
  const v = 0.9 * r / wall;
  return v >= 1 || r >= s * (1 - v) + 4;
}

function advance(startAt = null) {
  const old = current;
  if (old) { played.unshift(old); }
  while (played.length > KEEP) freePiece(played.pop()) || null;
  played = played.slice(0, KEEP);
  let next = pool.shift() || null;
  // an empty pool: the set's next piece is still being composed - a piece from the bank starts at once instead
  if (next && !canPlay(next) && next.status === 'composing' && bankIndex) {
    pool.unshift(next);
    next = newPiece('bank', { piano: state.piano, status: 'loading', urgent: true });
    const p = next, gen = state.gen;
    bankPiece(state.genre, state.piano).then(({ e }) => {
      if (p.dropped || gen !== state.gen) return;
      adopt(p, e, state.piano); p.status = 'queued'; renderQueue.push(p); pumpWork();
    }).catch((err) => { reportError('bank: ' + err.message); p.status = 'failed'; });
  }
  setCurrent(next, 0, startAt);
  pumpWork();
}

$('play').onclick = async () => {
  audio();
  if (wantWake) wake();
  if (!state.clicked) {
    state.clicked = true; state.playing = true; state.waitClick = performance.now();
    persistOnce();
    await ctx.resume();
    if (!current && state.session === null) await startSession();
    startPlayer(0);
    pumpWork();
  } else if (state.playing) {
    state.playing = false; state.pausing = true; await ctx.suspend(); state.pausing = false;
  } else {
    state.playing = true; state.sysPaused = false; await ctx.resume();
    if (!player && current) startPlayer(0);
  }
  ui();
};
$('skip').onclick = () => {
  if (!state.clicked) return;
  state.skipAt = performance.now();
  mark('skip', { from: current && current.id, ready: pool.filter(canPlay).length });
  advance();
};
$('back').onclick = () => {
  if (!player || !current) return;
  if (player.position() > 3 || !played.length) { seek(0); return; }
  const prev = played.shift();
  pool.unshift(current); current.urgent = false;
  setCurrent(prev);
};
function seek(t) {
  if (!current || !state.clicked) return;
  const max = Math.max(0, (current.store ? current.store.seconds() : 0) - 0.3);
  t = Math.max(0, Math.min(t, max));
  mark('seek', { to: +t.toFixed(2) });
  startPlayer(t);
}

for (const id of ['genre', 'piano']) $(id).onchange = () => {
  state.genre = $('genre').value; state.piano = $('piano').value; pianoUi();
  if (state.clicked || current) startSession();
};
$('restart').onclick = () => {
  audio();
  const s = parseInt($('seed').value, 10);
  state.clicked = true; state.playing = true; ctx.resume();
  const old = current; current = null; if (player) player.stop(); player = null;
  if (old) { played.unshift(old); played = played.slice(0, KEEP); }
  state.genre = $('genre').value; state.piano = $('piano').value; pianoUi();
  startSession(Number.isFinite(s) && s !== state.session?.seed ? { seed: Math.abs(s) % 1000000 } : {});
};

// seeking: the bar (click / drag, touch) and the form's sections
(() => {
  const bar = $('seek');
  let drag = false;
  const at = (ev) => {
    const r = bar.getBoundingClientRect();
    return Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * (current && current.info ? current.info.seconds : 0);
  };
  bar.addEventListener('pointerdown', (ev) => { if (!current || !current.info) return; drag = true; bar.setPointerCapture(ev.pointerId); state.dragT = at(ev); ui(); });
  bar.addEventListener('pointermove', (ev) => { if (drag) { state.dragT = at(ev); ui(); } });
  const end = (ev) => { if (!drag) return; drag = false; const t = at(ev); state.dragT = undefined; seek(t); };
  bar.addEventListener('pointerup', end);
  bar.addEventListener('pointercancel', () => { drag = false; state.dragT = undefined; });
  bar.addEventListener('keydown', (ev) => {
    if (!player) return;
    if (ev.key === 'ArrowRight') seek(player.position() + 10);
    if (ev.key === 'ArrowLeft') seek(player.position() - 10);
  });
  $('form').addEventListener('click', (ev) => {
    const d = ev.target.closest('div[data-start]');
    if (d && !d.classList.contains('off')) seek(+d.dataset.start);
  });
})();

// ---------------------------------------------------------------- downloads
function download(blob, name) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 20000);
}
const fileName = (p, ext) => `${(p.info.title || 'stueck').replace(/[^\w\- äöüÄÖÜß]+/g, '').trim().replace(/\s+/g, '-')}.${ext}`;
async function pcmOf(p) {
  const st = p.store;
  if (st.kind === 'pcm') {
    const outp = new Int16Array(st.frames * 2); let o = 0;
    for (const c of st.chunks) { outp.set(c, o); o += c.length; }
    return outp;
  }
  const outp = new Int16Array(Math.ceil((st.until + 1) * SR) * 2);
  let o = 0;
  await new Promise((resolve, reject) => {
    const dec = new AudioDecoder({
      output: (ad) => {
        const n = ad.numberOfFrames, L = new Float32Array(n), R = new Float32Array(n);
        ad.copyTo(L, { planeIndex: 0, format: 'f32-planar' }); ad.copyTo(R, { planeIndex: 1, format: 'f32-planar' }); ad.close();
        for (let i = 0; i < n && o < outp.length; i++) { outp[o++] = Math.max(-32768, Math.min(32767, Math.round(L[i] * 32767))); outp[o++] = Math.max(-32768, Math.min(32767, Math.round(R[i] * 32767))); }
      }, error: reject });
    dec.configure(st.cfg || { codec: 'opus', sampleRate: SR, numberOfChannels: 2 });
    for (const k of st.packets) dec.decode(new EncodedAudioChunk({ type: 'key', timestamp: k.ts, duration: k.dur, data: k.d }));
    dec.flush().then(() => { dec.close(); resolve(); }, reject);
  });
  return outp.subarray(0, o);
}
$('wav').onclick = async () => {
  const p = current;
  if (!p || p.status !== 'ready') return;
  const pcm = await pcmOf(p), n = pcm.length / 2;
  const head = new ArrayBuffer(44), v = new DataView(head);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 4, true); w(8, 'WAVE'); w(12, 'fmt ');
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 2, true); v.setUint32(24, SR, true);
  v.setUint32(28, SR * 4, true); v.setUint16(32, 4, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, n * 4, true);
  download(new Blob([head, pcm], { type: 'audio/wav' }), fileName(p, 'wav'));
};
$('notes').onclick = () => {
  const p = current;
  if (p && p.tune) download(new Blob([JSON.stringify({ recipe: p.recipe, hash: p.hash, ...p.tune }, null, 1)], { type: 'application/json' }), fileName(p, 'json'));
};

// ---------------------------------------------------------------- share links
const b64u = (s) => btoa(String.fromCharCode(...new TextEncoder().encode(s))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64u = (s) => new TextDecoder().decode(Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0)));
function pieceLink(recipe, hash) {
  const u = new URL(location.href); u.search = ''; u.hash = '';
  u.searchParams.set('r', b64u(JSON.stringify(recipe)));
  if (hash) u.searchParams.set('h', hash);
  return u.toString();
}
async function copy(link, label) {
  try { await navigator.clipboard.writeText(link); $('share-out').textContent = `${label} kopiert: ${link}`; }
  catch (e) { $('share-out').textContent = link; }
}
$('share').onclick = () => {
  const u = new URL(location.href); u.search = ''; u.hash = '';
  const s = state.session;
  if (s && s.bank !== null && s.bank !== undefined) u.searchParams.set('set', String(s.bank)); else if (s) u.searchParams.set('seed', String(s.seed));
  u.searchParams.set('genre', state.genre);
  if (state.piano !== 'beste') u.searchParams.set('piano', state.piano);
  if (current && current.recipe) copy(pieceLink(current.recipe, current.hash), 'Link zu diesem Stück');
  else copy(u.toString(), 'Link');
};

// ---------------------------------------------------------------- history (recipes only, in localStorage)
const HKEY = 'endless-piano-history';
let history = [];
function loadHistory() { try { history = JSON.parse(localStorage.getItem(HKEY) || '[]'); if (!Array.isArray(history)) history = []; } catch (e) { history = []; } }
function saveHistory() {
  history.sort((a, b) => (b.fav - a.fav) || (b.at - a.at));
  while (history.length > 200) { const i = history.map((h) => !h.fav).lastIndexOf(true); if (i < 0) break; history.splice(i, 1); }
  try { localStorage.setItem(HKEY, JSON.stringify(history)); } catch (e) { /* no storage: the list lives for this visit */ }
}
function remember(p) {
  if (!p.recipe || !p.info) return;
  const old = history.find((h) => h.h === p.hash);
  if (old) { old.at = Date.now(); }
  else history.push({ h: p.hash, v: V, recipe: p.recipe, title: p.info.title, genre: p.info.genre, piano: p.recipe.p,
                      key: p.info.key, tempo: p.info.tempo, meter: p.info.meter, at: Date.now(), fav: false });
  saveHistory(); drawHistory();
}
function heldPiece(hash) { return [current, ...played, ...pool].find((q) => q && q.hash === hash && q.store && !q.dropped); }
function playRecipe(recipe, wantHash) {
  if (!GENRES.includes(recipe.g)) { notice('Dieses Stück kann diese Seite nicht erzeugen.'); return; }
  audio(); ctx.resume(); state.clicked = true; state.playing = true;
  const held = wantHash && heldPiece(wantHash);
  if (held && held === current) { mark('history-play', { from: 'memory', hash: wantHash }); startPlayer(0); return; }
  if (held) { pool = pool.filter((q) => q !== held); played = played.filter((q) => q !== held); }
  if (current) { played.unshift(current); while (played.length > KEEP) freePiece(played.pop()); }
  if (held) {
    mark('history-play', { from: 'memory', hash: wantHash });
    setCurrent(held); return;
  }
  const p = newPiece('history', { piano: recipe.p, status: 'composing', urgent: true, cmd: { cmd: 'recipe', recipe }, wantHash });
  composeQueue.unshift(p);
  mark('history-play', { from: 'compose', hash: wantHash });
  setCurrent(p);
  pumpWork();
}
function drawHistory() {
  const ul = $('history');
  ul.textContent = '';
  $('hist-empty').style.display = history.length ? 'none' : 'block';
  for (const h of history.slice(0, 200)) {
    const li = document.createElement('li');
    if (current && current.hash === h.h) li.className = 'playing';
    const what = document.createElement('div'); what.className = 'what';
    const t = document.createElement('span'); t.className = 't'; t.textContent = h.title;
    const m = document.createElement('span'); m.className = 'm';
    const when = new Date(h.at);
    m.textContent = `${GENRE_NAME[h.genre] || h.genre} · ${keyName(h.key)} · ${h.tempo} BPM · ${when.toLocaleDateString('de-DE')} ${when.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}` + (h.v !== V ? ' · ältere Version (wird neu erzeugt)' : '');
    what.append(t, m);
    what.onclick = () => playRecipe(h.recipe, h.h);
    const fav = document.createElement('button'); fav.className = 'fav' + (h.fav ? ' on' : ''); fav.textContent = '♥';
    fav.title = h.fav ? 'Favorit entfernen' : 'Als Favorit merken'; fav.setAttribute('aria-pressed', h.fav ? 'true' : 'false');
    fav.onclick = () => { h.fav = !h.fav; saveHistory(); drawHistory(); };
    const link = document.createElement('button'); link.textContent = 'Link';
    link.onclick = () => copy(pieceLink(h.recipe, h.h), 'Link');
    li.append(what, fav, link);
    ul.appendChild(li);
  }
}

// ---------------------------------------------------------------- display
function showState(t) { $('state').textContent = t; }
function notice(t) { state.notice = t; state.noticeAt = Date.now(); showState(t); }   // shown for a minute
const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
function keyName(k) { const [n, q] = (k || '').split(' '); return `${n}-${{ major: 'Dur', minor: 'Moll' }[q] || q || ''}`; }
let shownId = null;
function progressOf(p) {
  if (!p) return '';
  if (p.status === 'failed') return 'Stück fehlgeschlagen – bitte überspringen';
  if (p.status === 'loading') return 'wird geladen…';
  if (p.status === 'composing') return composeJob === p ? 'wird komponiert…' : 'wartet auf den Komponisten…';
  if (p.status === 'samples' && p.loading && p.loading.n > 1) return `Klänge werden geladen… ${p.loading.done}/${p.loading.n}` + (p.loading.MB ? ` (${String(p.loading.MB).replace('.', ',')} MB)` : '');
  if (p.status === 'queued' || p.status === 'samples') return 'Klänge werden geladen…';
  if (p.status === 'rendering') return `wird vorbereitet… ${Math.min(99, Math.round(100 * (p.store ? p.store.frames : 0) / p.expected))} %`;
  return '';
}
function memory() {
  const all = [current, ...played, ...pool].filter(Boolean);
  const per = all.map((p) => ({ id: p.id, kind: p.kind, where: p === current ? 'current' : (pool.includes(p) ? 'pool' : 'played'),
                                 store: p.store ? p.store.kind : null, MB: p.store ? +(p.store.bytes / 1e6).toFixed(2) : 0,
                                 seconds: p.store ? +p.store.seconds().toFixed(1) : 0 }));
  M.mem = { per, totalMB: +per.reduce((s, x) => s + x.MB, 0).toFixed(2), samplesMB: +([...compressed.values()].reduce((s, b) => s + b.byteLength, 0) / 1e6).toFixed(2) };
  if (performance.memory) M.mem.jsHeapMB = Math.round(performance.memory.usedJSHeapSize / 1048576);
}
function ui() {
  session();
  $('play').textContent = state.playing ? 'Pause' : (state.clicked ? 'Weiter' : 'Abspielen');
  $('skip').disabled = !state.clicked; $('back').disabled = !state.clicked || !current;
  const p = current, i = p && p.info;
  if (!i) {
    $('title').textContent = p ? 'Das nächste Stück entsteht…' : 'Noch nichts gespielt';
    $('meta').textContent = p ? progressOf(p) : 'Drück auf Abspielen.';
  } else if (shownId !== p.id) {
    shownId = p.id;
    $('title').textContent = i.title;
    $('meta').textContent = `${GENRE_NAME[i.genre] || ''} · ${keyName(i.key)} · ${i.tempo} BPM · ${i.meter}${(FEEL[i.feel] || i.feel) !== GENRE_NAME[i.genre] ? ' · ' + (FEEL[i.feel] || i.feel) : ''}` +
      (i.candidates > 1 ? ` · bestes von ${i.candidates}` : '');
    const form = $('form'); form.textContent = '';
    for (const s of i.sections) {
      const d = document.createElement('div');
      d.style.flex = `${Math.max(0.001, s.end - s.start)} 1 0`;
      d.textContent = secName(s.name); d.title = `${secName(s.name)} ab ${fmt(s.start)}`;
      d.dataset.start = s.start; d.dataset.end = s.end;
      form.appendChild(d);
    }
    drawHistory();
  }
  const total = i ? i.seconds : 0;
  const t = state.dragT !== undefined ? state.dragT : (player && ctx && state.clicked ? player.position() : 0);
  const buf = p && p.store ? Math.min(total, p.store.seconds()) : 0;
  $('time').textContent = i ? `${fmt(Math.min(t, total))} / ${fmt(total)}` : '';
  const pct = (x) => `${total ? Math.min(100, 100 * x / total) : 0}%`;
  document.querySelector('#seek .played').style.width = pct(t);
  document.querySelector('#seek .knob').style.left = pct(t);
  document.querySelector('#seek .buf').style.width = pct(buf);
  $('form').querySelectorAll('div').forEach((d) => {
    d.classList.toggle('now', t >= +d.dataset.start && t < +d.dataset.end);
    d.classList.toggle('off', +d.dataset.start > buf - 0.3);
  });
  $('wav').disabled = !(p && p.status === 'ready'); $('notes').disabled = !(p && p.tune);
  // the pool
  const ready = pool.filter((q) => q.status === 'ready').length;
  $('dots').textContent = Array.from({ length: poolFor(state.genre) }, (_, k) => (k < ready ? '●' : (k < pool.length ? '◐' : '○'))).join('');
  const making = pool.find((q) => q.status !== 'ready');
  $('pool-text').textContent = state.clicked ? `${ready === 1 ? '1 Stück' : ready + ' Stücke'} bereit` + (making ? ` · nächstes: ${progressOf(making)}` : '') : '';
  $('upnext').textContent = pool.filter((q) => q.info).length ? 'Als Nächstes: ' + pool.filter((q) => q.info).map((q) => q.info.title).join(' · ') : '';
  if (p && !(USE_MSE ? enough(p) : canPlay(p))) showState(progressOf(p));
  else if (!state.playing && state.clicked) showState('Pausiert');
  else showState(state.notice && Date.now() - state.noticeAt < 60000 ? state.notice : '');
}

// ---------------------------------------------------------------- the phone: lock screen, screen off, interruptions
// Media Session: title / genre on the lock screen and in the notification, play / pause / next / previous / seek
const ART = [{ src: 'icon-192.png', sizes: '192x192', type: 'image/png' }, { src: 'icon-512.png', sizes: '512x512', type: 'image/png' }];
let sessionKey = '';
function session() {
  if (!('mediaSession' in navigator)) return;
  const ms = navigator.mediaSession, i = current && current.info;
  const key = i ? `${current.id}` : '';
  if (key !== sessionKey && 'MediaMetadata' in window) {
    sessionKey = key;
    ms.metadata = i ? new MediaMetadata({ title: i.title, artist: `AgentSound · ${GENRE_NAME[i.genre] || ''}`, album: `${keyName(i.key)} · ${i.tempo} BPM`, artwork: ART })
                    : new MediaMetadata({ title: 'Endless', artist: 'AgentSound', artwork: ART });
  }
  ms.playbackState = state.clicked ? (state.playing ? 'playing' : 'paused') : 'none';
  try {
    if (i && player && state.clicked) {
      const d = Math.max(1, i.seconds);
      ms.setPositionState({ duration: d, playbackRate: 1, position: Math.max(0, Math.min(d, player.position())) });
    }
  } catch (e) { /* positionState: older browsers */ }
}
if ('mediaSession' in navigator) {
  const on = (a, f) => { try { navigator.mediaSession.setActionHandler(a, f); } catch (e) { /* unsupported action */ } };
  on('play', () => { if (!state.playing) $('play').click(); });
  on('pause', () => { if (state.playing) $('play').click(); });
  on('nexttrack', () => $('skip').click());
  on('previoustrack', () => $('back').click());
  on('seekto', (d) => seek(d.seekTime));
  on('seekforward', (d) => player && seek(player.position() + (d.seekOffset || 10)));
  on('seekbackward', (d) => player && seek(player.position() - (d.seekOffset || 10)));
}
// interruptions (a call, another app's audio, the OS suspending the context): back to playing when the page returns
function resumeSoon(why) {
  if (!state.playing || !ctx) return;
  mark('interrupted', { why });
  if (document.visibilityState === 'visible') setTimeout(() => { if (state.playing && ctx.state !== 'running') ctx.resume(); }, 300);
}
$('out').addEventListener('pause', () => {
  if (!state.playing || state.pausing) return;
  if (document.visibilityState === 'visible') { resumeSoon('media paused'); return; }
  // hidden: the system paused us (another app took the audio focus): show it as paused, the lock screen's play resumes
  state.playing = false; state.sysPaused = true; mark('system-pause', { at: +$('out').currentTime.toFixed(2) }); ui();
});
$('out').addEventListener('play', () => {      // the system resumed us (after a call)
  if (!state.playing && state.sysPaused) { state.playing = true; state.sysPaused = false; mark('system-resume'); ui(); }
});
// Only diagnose missing audio after the first sound, not startup, seeking or the gap between pieces.
function reportBufferUnderrun() {
  const a = $('out'), p = player;
  if (!USE_MSE || !p || p.dead || p.first === null || !state.playing || a.paused || a.seeking || a.readyState >= 3) return;
  if (p.endTime !== null && a.currentTime >= p.endTime - 0.1) return;
  for (let i = 0; i < a.buffered.length; i++) {
    if (a.buffered.start(i) <= a.currentTime + 0.05 && a.buffered.end(i) > a.currentTime + 0.1) return;
  }
  if (p.bufferUnderrun) return;
  p.bufferUnderrun = true;
  mark('buffer-underrun', { id: p.p.id, at: +p.position().toFixed(2) });
  reportError(`buffer-underrun: ${p.p.info?.title || 'Stück'} bei ${fmt(p.position())}; Status ${p.p.status}`);
}
$('out').addEventListener('waiting', () => {
  mark('stream-waiting', { at: +$('out').currentTime.toFixed(2) });
  reportBufferUnderrun();
});
$('out').addEventListener('playing', () => {
  if (player && player.bufferUnderrun) {
    mark('buffer-recovered', { id: player.p.id });
    player.bufferUnderrun = false;
    // Keep the incident in the details, but do not keep claiming playback is waiting.
    if (M.errors[M.errors.length - 1]?.startsWith('buffer-underrun:'))
      $('error-message').textContent = 'Der Audiopuffer war kurz leer. Die Wiedergabe läuft wieder; der Vorfall steht in den Details.';
  }
});
function onVisible() {
  const vis = document.visibilityState === 'visible';
  mark(vis ? 'visible' : 'hidden', { appended: stream ? stream.segs.filter((g) => g.done).length : null, pool: pool.filter(canPlay).length });
  if (vis) {
    if (state.playing && ctx && ctx.state !== 'running') ctx.resume();
    if (wantWake) wake();
  } else if (player) player.pump();                 // (append what is ready before the browser slows the page down)
}
document.addEventListener('visibilitychange', onVisible);
window.addEventListener('pageshow', () => { if (state.playing && ctx && ctx.state !== 'running') ctx.resume(); });
// "Bildschirm anlassen": the Screen Wake Lock, taken again whenever the page becomes visible
let wantWake = false, wakeLock = null;
async function wake() {
  if (!('wakeLock' in navigator) || wakeLock) return;
  try { wakeLock = await navigator.wakeLock.request('screen'); wakeLock.addEventListener('release', () => { wakeLock = null; }); }
  catch (e) { reportError('wakelock: ' + e.name); }
}
if ('wakeLock' in navigator) {
  $('wake-row').hidden = false;
  try { wantWake = localStorage.getItem('endless-wake') === '1'; } catch (e) { /* no storage */ }
  $('wake').checked = wantWake;
  $('wake').onchange = () => {
    wantWake = $('wake').checked;
    try { localStorage.setItem('endless-wake', wantWake ? '1' : '0'); } catch (e) { /* no storage */ }
    if (wantWake) wake(); else if (wakeLock) { wakeLock.release(); wakeLock = null; }
  };
}

// ---------------------------------------------------------------- offline: what is stored, persistence, prefetch
// The samples, the bank, the composer zip (store.js) and the engine / Pyodide (sw.js) stay in Cache Storage; asked
// for persistent storage after the first play (Chrome grants it more readily to a page in use)
let sizeTimer = 0;
function offlineUi(now) {
  if (typeof caches === 'undefined') return;
  $('offline').hidden = false;
  clearTimeout(sizeTimer);
  sizeTimer = setTimeout(async () => {
    try { const { bytes } = await (await store).cacheSize(); $('offline-size').textContent = `Offline gespeichert: ${Math.round(bytes / 1e6)} MB`; }
    catch (e) { /* no storage */ }
  }, now ? 0 : 3000);
}
let persistAsked = false;
function persistOnce() {
  if (persistAsked || !navigator.storage || !navigator.storage.persist) return;
  persistAsked = true;
  navigator.storage.persisted().then((p) => p || navigator.storage.persist()).then((ok) => mark('persist', { ok })).catch(() => {});
}
// "Für offline laden": every sample of the chosen sound (the orchestra's ~59 MB, the piano's 10 / 32 MB) and the
// composer; the engine and Pyodide are kept by the service worker once they ran
$('offline-load').onclick = async () => {
  const b = $('offline-load'), S = await store;
  b.disabled = true; persistOnce();
  try {
    const set = ORCH(state.genre) ? 'orch' : state.piano, H = await hashes();
    const urls = Object.keys(H[set]).map((f) => surl(set, f)).concat(Object.keys(H.ir).filter((f) => f.endsWith('.wav')).map((f) => surl('ir', f)));
    await S.cachedBuffer(`py/repo.zip?v=${V}`, CODE_CACHE);
    let done = 0;
    const total = urls.length, list = urls.slice();
    const one = async () => { while (list.length) { await S.cachedBuffer(list.shift(), SAMPLE_CACHE); b.textContent = `Lädt … ${++done}/${total}`; } };
    await Promise.all(Array.from({ length: 6 }, one));
    b.textContent = `Offline bereit (${ORCH(state.genre) ? 'Orchester' : state.piano === 'spar' ? 'Sparklavier' : 'Flügel'})`;
    mark('offline-load', { n: total });
  } catch (e) { b.textContent = 'Für offline laden (Fehler)'; reportError('offline: ' + e.message); }
  b.disabled = false; offlineUi(true);
};
$('offline-clear').onclick = async () => {
  await (await store).clearAll().catch(() => {});
  compressed.clear(); $('offline-load').textContent = 'Für offline laden'; offlineUi(true);
};
offlineUi(true);
setTimeout(async () => {                       // the caches of other versions, the samples no index names any more
  try {
    const S = await store, H = await hashes();
    await S.dropOld([CODE_CACHE, SAMPLE_CACHE, `endless-pyodide-${PYV}`]);
    const n = await S.prune(SAMPLE_CACHE, (u) => {
      const m = u.pathname.match(/\/samples\/([^/]+)\/([^/]+)$/);
      if (!m) return u.pathname.endsWith('/samples/index.json') && u.searchParams.get('s') === SV;
      return (H[m[1]] || {})[decodeURIComponent(m[2])] === u.searchParams.get('h');
    });
    if (n) { mark('pruned', { n }); offlineUi(); }
  } catch (e) { /* no storage */ }
}, 20000);

// for tests: the page's inner state, read only
window.__dbg = { get current() { return current; }, get pool() { return pool; }, get played() { return played; }, get stream() { return stream; },
                 get player() { return player; }, get ctx() { return ctx; }, pcmOf, state };

// ---------------------------------------------------------------- the clock
setInterval(() => {
  if (USE_MSE && stream && state.playing && stream.audio.paused && !state.pausing && document.visibilityState === 'visible' &&
      performance.now() - (state.kicked || 0) > 2000) {
    state.kicked = performance.now(); stream.audio.play().catch(() => {});        // (a pause we did not ask for)
  }
  if (player && state.playing) {
    player.pump();
    if (player.endTime !== null && ctx.currentTime >= player.endTime - 0.05) advance(USE_MSE ? null : player.endTime + GAP);
  } else if (!player && current && state.playing && ctx) startPlayer(0);
  pumpWork().catch(() => {});
  memory();
  ui();
}, 200);

// ---------------------------------------------------------------- start: on load, the first piece renders silently
(async () => {
  OPUS = await probeOpus();
  USE_MSE = await probeMse();
  M.config0 = { mse: USE_MSE, managed: !!window.ManagedMediaSource && MS === window.ManagedMediaSource };
  POOL = OPUS ? (mobile ? (devMem >= 6 ? 3 : 2) : 4) : (mobile ? 1 : 2);
  KEEP = OPUS ? 2 : 1;
  if (mobile && USE_MSE) POOL = Math.max(POOL, 2);   // (two pieces appended ahead when the screen goes off)
  M.config = { opus: OPUS, mse: USE_MSE, pool: POOL, keep: KEEP, mobile, deviceMemory: devMem };
  if ('serviceWorker' in navigator && !params.has('nosw')) navigator.serviceWorker.register(`sw.js?v=${V}&a=${A}&s=${SV}&p=${PYV}`).catch((e) => reportError('sw: ' + e));
  pianoUi();
  if (mobile) $('orch-note').textContent = 'Das Orchester lädt rund 20 MB Klänge pro Stück und braucht beim Rendern rund ein halbes GB Arbeitsspeicher - auf Handys oft zu schwer (es kann stocken oder abbrechen). Das Klavier läuft überall.';
  mark('config', M.config);
  loadHistory(); drawHistory();
  makeComposer(); makeEngine();
  let shared = null;
  if (params.has('r')) {
    try { shared = JSON.parse(unb64u(params.get('r'))); } catch (e) { shared = null; }
    if (shared && !GENRES.includes(shared.g)) shared = null;
    if (shared) { state.genre = shared.g; state.piano = PIANOS.includes(shared.p) ? shared.p : 'beste'; $('genre').value = state.genre; $('piano').value = state.piano; }
  }
  const seed = params.has('seed') ? Math.abs(parseInt(params.get('seed'), 10) || 0) % 1000000 : null;
  const bank = params.has('set') ? parseInt(params.get('set'), 10) : undefined;
  if (shared) {
    const p = newPiece('history', { piano: shared.p, status: 'composing', urgent: true, cmd: { cmd: 'recipe', recipe: shared }, wantHash: params.get('h') || undefined });
    composeQueue.push(p); setCurrent(p);
    startSession({});
  } else {
    startSession(seed !== null ? { seed } : { bank });
  }
})();
