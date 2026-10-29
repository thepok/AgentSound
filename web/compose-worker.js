// Endless: Pyodide runs the AgentSound composer (the endless set loop, best of N per piece).
const Q = new URL(self.location.href).searchParams;
const V = Q.get('v') || '', A = Q.get('a') || '';   // the page's code version / revision: no stale cached zip
const PYODIDE = `https://cdn.jsdelivr.net/npm/pyodide@${Q.get('py') || '314.0.7'}/`;   // (cached by the service worker)
let py = null;

const ready = (async () => {
  const { loadPyodide } = await import(PYODIDE + 'pyodide.mjs');
  py = await loadPyodide({ indexURL: PYODIDE });
  const { cachedBuffer, codeCache } = await import(`./store.js?v=${V}&a=${A}`);
  const { buf: zip } = await cachedBuffer(`py/repo.zip?v=${V}`, codeCache(V));   // (Cache Storage: offline next time)
  py.unpackArchive(zip, 'zip', { extractDir: '/repo' });
  py.runPython("import sys; sys.dont_write_bytecode = True; sys.path.insert(0, '/repo'); import compose_web");
  postMessage({ type: 'ready', version: py.runPython('compose_web.VERSION') });
})().catch((e) => postMessage({ type: 'error', fatal: true, message: 'Komponist konnte nicht laden: ' + e }));

let queue = Promise.resolve();
onmessage = (e) => {
  const m = e.data;
  queue = queue.then(async () => {
    await ready;
    if (m.cmd === 'start') {   // candidates: null = the genre's own (compose_web.GENRES)
      py.globals.set('ARGS', py.toPy([m.genre, m.seed | 0, m.piano, m.first || null, m.next || null, m.afterKey || null]));
      py.runPython('compose_web.start(*ARGS); del ARGS');
      return;
    }
    const t0 = performance.now();
    let out;
    if (m.cmd === 'next') {
      out = py.runPython('compose_web.next_piece()');
    } else if (m.cmd === 'recipe') {
      py.globals.set('RECIPE', JSON.stringify(m.recipe));
      out = py.runPython('compose_web.recipe_piece(RECIPE)');
      py.runPython('del RECIPE');
    }
    postMessage({ type: 'composed', job: m.job, out, ms: Math.round(performance.now() - t0) });
  }).catch((err) => postMessage({ type: 'error', job: m.job, message: String(err && err.message || err).split('\n').slice(-2).join(' ') }));
};
