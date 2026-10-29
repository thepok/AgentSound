// Endless: the AgentSound engine (WebAssembly) renders one piece and streams it as 16-bit PCM.
// The main thread sends the render JSON with its sample paths already mapped to s/<name>.wav, the piece's samples
// (decoded from Opus into 16-bit WAVs, loop points in their smpl chunk) and its impulse responses (urls).
// One piece per worker: the page starts a fresh worker for the next one (the engine's sample caches go with it).
const Q = new URL(self.location.href).searchParams;
const V = Q.get('v') || '', A = Q.get('a') || '';   // the page's code version / revision: no stale cached engine
const store = import(`./store.js?v=${V}&a=${A}`);
let engine = null, stream = null;
const ready = import(`./engine/agentsound.js?v=${V}`).then(({ default: createEngine }) => createEngine({
  locateFile: (path, prefix) => `${prefix}${path}?v=${V}`,
  print: () => {}, printErr: (s) => { if (!/^render \d+%/.test(s)) console.warn('[engine]', s); },
  onStream: (l, r) => stream && stream(l, r),
})).then((m) => { engine = m; postMessage({ type: 'ready' }); });

function rm(p) { try { engine.FS.unlink(p); } catch (e) { /* gone */ } }
function mkdir(p) { try { engine.FS.mkdir(p); } catch (e) { /* exists */ } }
const irs = new Set();

async function render(m) {
  await ready;
  const FS = engine.FS;
  mkdir('/assets'); mkdir('/assets/s'); mkdir('/assets/ir'); mkdir('/out');
  for (const [path, url] of Object.entries(m.irs || {})) {
    if (irs.has(path)) continue;
    const { buf } = await (await store).cachedBuffer(url, m.cache);   // (the sample cache: offline next time)
    FS.writeFile('/assets/' + path, new Uint8Array(buf));
    irs.add(path);
  }
  for (const [name, buf] of Object.entries(m.files)) FS.writeFile(`/assets/s/${name}.wav`, new Uint8Array(buf));
  FS.writeFile('/song.json', m.render);
  const sr = m.sampleRate || 48000;
  rm('/out/mix.wav');
  FS.symlink('/dev/null', '/out/mix.wav');            // the stream is the output: no WAV in memory
  let frames = 0, first = null;
  const t0 = performance.now();
  stream = (l, r) => {
    if (first === null) first = (performance.now() - t0) / 1000;
    const n = l.length, pcm = new Int16Array(2 * n);
    for (let i = 0, o = 0; i < n; i++) {
      pcm[o++] = Math.max(-32768, Math.min(32767, Math.round(l[i] * 32767)));
      pcm[o++] = Math.max(-32768, Math.min(32767, Math.round(r[i] * 32767)));
    }
    frames += n;
    postMessage({ type: 'chunk', job: m.job, pcm, frames: n }, [pcm.buffer]);
  };
  engine._as_clear_sample_cache();
  const rc = engine.callMain(['render', '/song.json', '--assets', '/assets', '--out', '/out', '--no-png', '--no-analysis', '--quiet']);
  const secs = (performance.now() - t0) / 1000;
  stream = null;
  engine._as_clear_sample_cache();
  for (const name of Object.keys(m.files)) rm(`/assets/s/${name}.wav`);
  rm('/song.json');
  postMessage({ type: 'done', job: m.job, ok: rc === 0, frames, render_s: +secs.toFixed(1), first_chunk_s: +(first || 0).toFixed(2),
                realtime_x: +((frames / sr) / secs).toFixed(2), heapMB: Math.round(engine.HEAPU8.length / 1048576) });
}

let queue = Promise.resolve();
onmessage = (e) => {
  const m = e.data;
  queue = queue.then(() => render(m)).catch((err) => postMessage({ type: 'error', job: m.job, message: String(err && err.message || err) }));
};
