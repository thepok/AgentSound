// The making-of frame renderer: headless Chrome draws each frame (WebGL2 scenes + a Canvas 2D overlay, page.html /
// mo.js), Node pipes the frames into ffmpeg (H.264). Deterministic: a frame is a pure function of its index, so
// N browser tabs render N contiguous ranges in parallel and the segments are concatenated.
//
//   node render.mjs --project DIR/project.json --out video.mp4 [--workers 3] [--frames A:B] [--stills 1.5,20,...]
//                   [--chrome PATH] [--ffmpeg PATH] [--gpu high|default] [--crf 18] [--quality 0.94]
//
// Needs Node >= 22 (built-in WebSocket), Chrome or Edge, ffmpeg with libx264.

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { analyse, cached, decode, save } from './analysis.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));

function args() {
  const a = process.argv.slice(2), o = {};
  for (let i = 0; i < a.length; i++) {
    if (!a[i].startsWith('--')) continue;
    const k = a[i].slice(2), v = a[i + 1] && !a[i + 1].startsWith('--') ? a[++i] : 'true';
    o[k] = v;
  }
  return o;
}

export function findChrome(explicit) {
  const c = [explicit, process.env.AGENTSOUND_CHROME,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].filter(Boolean);
  return c.find((p) => { try { return fs.statSync(p).isFile(); } catch { return false; } });
}

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.png': 'image/png', '.bin': 'application/octet-stream', '.jpg': 'image/jpeg' };

function serve(roots) {
  // roots: {urlPrefix: dir}; files only, no listing
  const srv = http.createServer((req, res) => {
    const u = decodeURIComponent(req.url.split('?')[0]);
    for (const [pre, dir] of Object.entries(roots)) {
      if (!u.startsWith(pre)) continue;
      const f = path.join(dir, u.slice(pre.length));
      if (!f.startsWith(path.resolve(dir))) break;
      fs.readFile(f, (err, data) => {
        if (err) { res.writeHead(404); res.end(); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
        res.end(data);
      });
      return;
    }
    res.writeHead(404); res.end();
  });
  return new Promise((r) => srv.listen(0, '127.0.0.1', () => r(srv)));
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.id && this.pending.has(m.id)) {
        const [res, rej] = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(`${m.error.message} ${m.error.data || ''}`)) : res(m.result);
      }
    };
  }
  send(method, params = {}, sessionId) {
    return new Promise((res, rej) => {
      const id = ++this.id; this.pending.set(id, [res, rej]);
      this.ws.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
}

async function launch(chrome, gpu, w, h) {
  const ud = fs.mkdtempSync(path.join(process.env.AGENTSOUND_MAKINGOF_TMP || os.tmpdir(), 'mo-chrome-'));
  const flags = ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${ud}`, '--no-first-run',
    '--no-default-browser-check', '--mute-audio', '--hide-scrollbars', `--window-size=${w},${h}`,
    '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows',
    '--ignore-gpu-blocklist', '--enable-gpu-rasterization'];
  if (gpu === 'high') flags.push('--force_high_performance_gpu');
  const proc = spawn(chrome, [...flags, 'about:blank'], { stdio: 'ignore' });
  let port;
  for (let i = 0; i < 200 && !port; i++) {
    try { port = fs.readFileSync(path.join(ud, 'DevToolsActivePort'), 'utf8').split('\n'); } catch { await new Promise((r) => setTimeout(r, 100)); }
  }
  if (!port) throw new Error('Chrome did not start (no DevToolsActivePort)');
  const ws = new WebSocket(`ws://127.0.0.1:${port[0]}${port[1]}`);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  return { proc, cdp: new CDP(ws), ud };
}

async function openTab(cdp, url, w, h) {
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false }, sessionId);
  await cdp.send('Runtime.enable', {}, sessionId);
  await cdp.send('Page.navigate', { url }, sessionId);
  const ev = async (expression) => {
    const r = await cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
    if (r.exceptionDetails) throw new Error(`page: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
    return r.result.value;
  };
  await cdp.send('Target.activateTarget', { targetId }).catch(() => {});
  for (let i = 0; i < 1800; i++) {
    let st = null;
    try { st = await ev('window.MO_STATE || null'); } catch { /* navigating */ }
    if (st === 'ready') return { ev, sessionId, targetId };
    if (st && st.startsWith && st.startsWith('error')) throw new Error(st);
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error('the page did not get ready');
}

function hasNvenc(ffmpeg) {
  return new Promise((r) => {
    const p = spawn(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=256x256:d=0.2',
      '-c:v', 'h264_nvenc', '-f', 'null', '-'], { stdio: 'ignore' });
    p.on('close', (c) => r(c === 0)); p.on('error', () => r(false));
  });
}

function encoder(ffmpeg, out, fps, crf, nvenc) {
  const codec = nvenc
    ? ['-c:v', 'h264_nvenc', '-preset', 'p6', '-tune', 'hq', '-rc', 'vbr', '-cq', String(Number(crf) + 1), '-b:v', '0',
      '-profile:v', 'high', '-bf', '2']
    : ['-c:v', 'libx264', '-preset', 'faster', '-crf', String(crf), '-tune', 'film'];
  const p = spawn(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps),
    '-c:v', 'mjpeg', '-i', '-', ...codec, '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((r, j) => p.on('close', (c) => (c === 0 ? r() : j(new Error(`ffmpeg exited ${c}`)))));
  const write = (buf) => new Promise((r) => { if (p.stdin.write(buf)) r(); else p.stdin.once('drain', r); });
  return { write, end: () => { p.stdin.end(); return done; } };
}

async function main() {
  const o = args();
  const projFile = path.resolve(o.project);
  const proj = JSON.parse(fs.readFileSync(projFile, 'utf8'));
  const dir = path.dirname(projFile);
  const ffmpeg = o.ffmpeg || 'ffmpeg';
  const chrome = findChrome(o.chrome);
  if (!chrome) throw new Error('no Chrome / Edge found (set AGENTSOUND_CHROME)');
  const W = proj.width, H = proj.height, fps = proj.fps;

  // audio features (cached)
  const st = fs.statSync(proj.mixWav);
  const stamp = { size: st.size, mtime: Math.round(st.mtimeMs), fps, v: 4 };
  if (!cached(dir, stamp)) {
    const t0 = Date.now();
    const pcm = await decode(ffmpeg, proj.mixWav, 48000);
    save(dir, analyse(pcm, 48000, fps), stamp);
    console.log(`features: ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  }

  const srv = await serve({ '/web/': HERE, '/data/': dir, '/song/': path.dirname(proj.mixWav) });
  const base = `http://127.0.0.1:${srv.address().port}/web/page.html`;
  const { proc, cdp, ud } = await launch(chrome, o.gpu || 'high', W, H);
  const quality = Number(o.quality || 0.94);
  try {
    if (o.stills) {
      const tab = await openTab(cdp, base, W, H);
      const outDir = path.resolve(o.out);
      fs.mkdirSync(outDir, { recursive: true });
      for (const s of o.stills.split(',')) {
        const f = Math.round(Number(s) * fps);
        const url = await tab.ev(`MO.frame(${f}, 'image/png')`);
        const file = path.join(outDir, `still_${String(f).padStart(6, '0')}.png`);
        fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
        console.log(file);
      }
      return;
    }
    const [fa, fb] = (o.frames || `0:${proj.frames}`).split(':').map(Number);
    const nvenc = o.encoder === 'x264' ? false : await hasNvenc(ffmpeg);
    if (o.encoder === 'nvenc' && !nvenc) throw new Error('NVENC is not available (use --encoder x264)');
    console.log(`encoder: ${nvenc ? 'h264_nvenc' : 'libx264'}`);
    const workers = Math.max(1, Math.min(Number(o.workers || 3), Math.ceil((fb - fa) / 60)));
    const size = Math.ceil((fb - fa) / workers);
    const segs = [];
    const t0 = Date.now();
    let done = 0, lastLog = 0;
    const jobs = [];
    const tabs = [];
    for (let w = 0; w < workers; w++) tabs.push(await openTab(cdp, base, W, H));
    for (let w = 0; w < workers; w++) {
      const a = fa + w * size, b = Math.min(fb, a + size);
      if (a >= b) break;
      const seg = path.join(dir, `seg_${String(w).padStart(2, '0')}.mp4`);
      segs.push(seg);
      jobs.push((async () => {
        const tab = tabs[w];
        const enc = encoder(ffmpeg, seg, fps, o.crf || 18, nvenc);
        for (let f = a; f < b; f++) {
          const url = await tab.ev(`MO.frame(${f}, 'image/jpeg', ${quality})`);
          await enc.write(Buffer.from(url.slice(url.indexOf(',') + 1), 'base64'));
          done++;
          const now = Date.now();
          if (now - lastLog > 10000) {
            lastLog = now;
            const rate = done / ((now - t0) / 1000);
            console.log(`frames ${done}/${fb - fa}  ${rate.toFixed(1)} fps  eta ${((fb - fa - done) / rate / 60).toFixed(1)} min`);
          }
        }
        await enc.end();
        await cdp.send('Target.closeTarget', { targetId: tab.targetId });
      })());
    }
    await Promise.all(jobs);
    const list = path.join(dir, 'segments.txt');
    fs.writeFileSync(list, segs.map((s) => `file '${s.replace(/\\/g, '/')}'`).join('\n'));
    await new Promise((r, j) => spawn(ffmpeg, ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0',
      '-i', list, '-c', 'copy', path.resolve(o.out)], { stdio: 'inherit' }).on('close', (c) => (c ? j(new Error('concat failed')) : r())));
    segs.forEach((s) => fs.rmSync(s, { force: true }));
    console.log(`video: ${fb - fa} frames in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  } finally {
    try { await cdp.send('Browser.close'); } catch { /* gone */ }
    setTimeout(() => { try { proc.kill(); } catch { /* gone */ } }, 500);
    srv.close();
    setTimeout(() => { try { fs.rmSync(ud, { recursive: true, force: true }); } catch { /* locked */ } }, 1500);
  }
}

main().catch((e) => { console.error(`render.mjs: ${e.stack || e}`); process.exit(1); });
