// Endless: the service worker - registered as sw.js?v=<code version>&a=<page revision>&s=<sample-set hash>&p=<pyodide>.
// It never holds up the page (the first visit plays as before) and keeps, in versioned caches:
//   endless-shell-<v>-<a>   the app shell (precached; the page itself network-first, the cache when offline)
//   endless-code-<v>        engine/* (cache-first; py/repo.zip and bank/** are cached there by the page, store.js)
//   endless-pyodide-<p>     the Pyodide runtime from the CDN (a pinned version: immutable, cache-first)
//   endless-samples         samples/** - cached by the page (store.js, each URL with its content hash), kept here
// On activate only the caches of other versions go: a new page revision keeps the samples, the code and Pyodide.
const Q = new URL(self.location.href).searchParams;
const V = Q.get('v') || 'dev', A = Q.get('a') || '0', SV = Q.get('s') || '0', P = Q.get('p') || '0';
const SHELL_CACHE = `endless-shell-${V}-${A}`, CODE = `endless-code-${V}`, PY = `endless-pyodide-${P}`;
const KEEP = [SHELL_CACHE, CODE, PY, 'endless-samples'];
const PY_URL = `https://cdn.jsdelivr.net/npm/pyodide@${P}/`;
const SHELL = ['index.html', `app.js?v=${V}&a=${A}`, `store.js?v=${V}&a=${A}`, `compose-worker.js?v=${V}&a=${A}&py=${P}`,
               `engine-worker.js?v=${V}&a=${A}`, 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
const ENGINE = [`engine/agentsound.js?v=${V}`, `engine/agentsound.wasm?v=${V}`];

// the Pyodide runtime the composer loads (pyodide.mjs and what it fetches); a file missing here is cached on its first use
const PY_FILES = ['pyodide.mjs', 'pyodide.asm.mjs', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json'].map((f) => PY_URL + f);

// install: the shell; the engine and Pyodide too (on the first visit the workers start before this worker controls
// the page, so their files would only be cached on the second visit - mostly a hit in the HTTP cache). Best effort:
// a failure here never stops the page, the files are cached on their next use.
const warm = (name, urls) => caches.open(name).then((c) => Promise.all(urls.map((u) => c.match(u).then((hit) => hit ||
  fetch(u, { mode: 'cors' }).then((r) => r.status === 200 && r.arrayBuffer().then((buf) =>
    c.put(u, new Response(buf, { headers: { 'content-type': r.headers.get('content-type') || 'application/octet-stream', 'x-size': String(buf.byteLength) } }))))
  .catch(() => {})))));
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL)).catch(() => {})
    .then(() => Promise.all([warm(CODE, ENGINE.map((u) => new URL(u, location.href).href)), warm(PY, PY_FILES)]))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith('endless-') && !KEEP.includes(k))
    .map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

// cache-first: a hit from the cache, a miss from the network, stored when it is a full 200 response (not opaque, not
// partial) - as a copy of its bytes with the size in x-size
async function cacheFirst(req, name) {
  const c = await caches.open(name);
  const hit = await c.match(req.url);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.status === 200 && (r.type === 'basic' || r.type === 'cors')) {
    const buf = await r.clone().arrayBuffer();
    const h = { 'content-type': r.headers.get('content-type') || 'application/octet-stream', 'x-size': String(buf.byteLength) };
    c.put(req.url, new Response(buf, { headers: h })).catch(() => {});
  }
  return r;
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || req.headers.has('range')) return;
  const url = req.url;
  if (url.startsWith(PY_URL)) { e.respondWith(cacheFirst(req, PY)); return; }
  const u = new URL(url);
  if (u.origin !== location.origin) return;
  const rel = u.pathname.slice(new URL('./', location.href).pathname.length) + u.search;
  if (rel === '' || rel === 'index.html' || rel.startsWith('?') || rel.startsWith('index.html?')) {
    // the page: the network first (a new version shows up at once), the cache when offline
    e.respondWith(fetch(req).then((r) => {
      if (r.ok) { const copy = r.clone(); caches.open(SHELL_CACHE).then((c) => c.put('index.html', copy)); }
      return r;
    }).catch(() => caches.open(SHELL_CACHE).then((c) => c.match('index.html'))));
    return;
  }
  if (ENGINE.includes(rel)) { e.respondWith(cacheFirst(req, CODE)); return; }
  if (SHELL.includes(rel)) e.respondWith(caches.open(SHELL_CACHE).then((c) => c.match(rel)).then((hit) => hit || fetch(req)));
  // samples/**, bank/**, py/repo.zip: the page caches them itself (store.js) - passed through
});
