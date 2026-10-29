// Endless: the persistent asset cache (Cache Storage), used by the page and both workers.
// Every asset URL is content-versioned - ?v=<code version> (engine, composer zip, bank), ?s=<its hash>
// (samples/index.json), ?h=<the file's own content hash> (samples/**) - so a cached file can never be stale:
// cache-first, the network only on a miss. GitHub Pages sends
// max-age=600 and phones evict their small HTTP cache, so without this every visit would load the sounds again.
// The page does its own caching (it works on the very first visit and without a service worker); sw.js caches the
// app shell, the engine and Pyodide, and passes these URLs through.
export const codeCache = (V) => `endless-code-${V}`;        // engine, py/repo.zip, bank/**  (the samples: 'endless-samples')
const HAS = typeof caches !== 'undefined';

// the file as an ArrayBuffer, from the cache or (on a miss) the network; only a full 200 response is stored, as a
// plain copy of its bytes (no opaque or partial responses), with its size in x-size (for the "offline" total)
const inflight = new Map();                // url -> promise (the playing piece and a prefetch asking at once: one fetch)
export function cachedBuffer(url, name, opts) {
  if (!inflight.has(url)) inflight.set(url, load(url, name, opts).finally(() => inflight.delete(url)));
  return inflight.get(url).then((r) => ({ buf: r.buf.slice(0), hit: r.hit }));   // (a copy each: callers may detach it)
}
async function load(url, name, opts) {
  let c = null;
  if (HAS) {
    try {
      c = await caches.open(name);
      const hit = await c.match(url);
      if (hit) return { buf: await hit.arrayBuffer(), hit: true };
    } catch (e) { c = null; }                 // (no storage: a private window, a full disk)
  }
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  const buf = await r.arrayBuffer();
  if (c && r.status === 200) {
    const headers = { 'content-type': r.headers.get('content-type') || 'application/octet-stream', 'x-size': String(buf.byteLength) };
    await c.put(url, new Response(buf.slice(0), { headers })).catch(() => {});   // (awaited: a closed tab loses no file)
  }
  return { buf, hit: false };
}

// the network first (a file whose URL is not versioned: bank/index.json), the cache when offline
export async function freshBuffer(url, name) {
  try {
    const r = await fetch(url, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    const buf = await r.arrayBuffer();
    if (HAS) caches.open(name).then((c) => c.put(url, new Response(buf.slice(0), { headers: { 'x-size': String(buf.byteLength) } }))).catch(() => {});
    return buf;
  } catch (err) {
    const hit = HAS && await caches.open(name).then((c) => c.match(url)).catch(() => null);
    if (hit) return hit.arrayBuffer();
    throw err;
  }
}

const ours = async () => (HAS ? (await caches.keys()).filter((k) => k.startsWith('endless-')) : []);
// bytes and files stored offline (all of this page's caches)
export async function cacheSize() {
  let bytes = 0, files = 0;
  for (const k of await ours()) {
    const c = await caches.open(k);
    for (const r of await c.matchAll()) { files++; bytes += +(r.headers.get('x-size') || r.headers.get('content-length') || 0); }
  }
  return { bytes, files };
}
// the caches of other versions go (the service worker does the same when it activates)
export async function dropOld(keep) {
  for (const k of await ours()) if (!keep.includes(k) && !k.startsWith('endless-shell-')) await caches.delete(k);
}
// the entries of a cache `keep(url)` says no to (samples an update replaced); -> how many went
export async function prune(name, keep) {
  if (!HAS || !(await caches.has(name))) return 0;
  const c = await caches.open(name);
  let n = 0;
  for (const r of await c.keys()) if (!keep(new URL(r.url))) { await c.delete(r); n++; }
  return n;
}
// "Cache leeren": everything but the app shell
export async function clearAll() {
  for (const k of await ours()) if (!k.startsWith('endless-shell-')) await caches.delete(k);
}
