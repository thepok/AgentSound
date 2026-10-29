"""Exact stage UI snapshots + fast per-cell video compositing (no browser per frame).

Dependencies: numpy, soundfile, Pillow, playwright, Edge, ffmpeg.
python render_video_fast.py TUNE_DIR --out song.mp4 --background autumn.png
--preview writes a representative PNG; --limit-seconds is useful for smoke tests.
The browser supplies all artwork, text, state effects AND the actual meter pixels.
"""
import argparse
import base64
import hashlib
import io
import json
import math
import mimetypes
import subprocess
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import soundfile as sf
from PIL import Image
from playwright.sync_api import sync_playwright

SIZE = (1920, 1080)
EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'


def audio_path(tune_dir, recorded):
    """Allow a completed tune folder to move, or WAVs to become lossless FLACs."""
    recorded = Path(recorded)
    local = tune_dir / 'stems' / recorded.name
    for path in (local, local.with_suffix('.flac'), recorded, recorded.with_suffix('.flac')):
        if path.is_file():
            return path
    raise FileNotFoundError(f'Missing stem: {recorded}')


def measure_levels(paths, mapping, frames, fps, cache):
    signature = {'fps': fps, 'frames': frames, 'mapping': mapping, 'version': 1,
                 'sources': {key: [str(p.resolve()), p.stat().st_size, p.stat().st_mtime_ns]
                             for key, p in paths.items()}}
    fingerprint = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
    if cache.is_file():
        with np.load(cache, allow_pickle=False) as saved:
            if str(saved['fingerprint']) == fingerprint:
                return {key: saved[key].copy() for key in dict.fromkeys(mapping.values())}
    power = {}
    for track, path in paths.items():
        rms = np.zeros(frames, dtype=np.float32)
        with sf.SoundFile(path) as source:
            block = round(source.samplerate / fps)
            n = min(frames, len(source) // block)
            # Same fixed-frame RMS as render_video.py, bounded memory even for long stems.
            for start in range(0, n, 240):
                count = min(240, n - start)
                samples = source.read(count * block, dtype='float32', always_2d=True)
                rms[start:start + count] = np.mean(samples.reshape(count, block, -1) ** 2, axis=(1, 2))
            if n and n < frames:
                rms[n:] = rms[n - 1]
        key = mapping[track]
        power[key] = power.get(key, 0) + rms
    levels = {key: np.clip((10 * np.log10(np.maximum(values, 1e-12)) + 60) / 48, 0, 1)
              for key, values in power.items()}
    decay = math.exp(-1 / (fps * .22))
    for values in levels.values():
        for i in range(1, len(values)):
            values[i] = max(values[i], values[i - 1] * decay)
    np.savez_compressed(cache, fingerprint=np.array(fingerprint), **levels)
    return levels


def scene_setup(page, ids, tune):
    page.evaluate('''async({ids,tune})=>{
      const {byId}=await import('./catalog.js');
      const s={title:tune.title,subtitle:`${tune.key} · ${tune.tempo} BPM · ${tune.meter}`,
        strings:[],winds:[],rear:[],extraStacks:{featured:[],rightColour:[]}};
      for(const id of ids){const d=byId[id];
        if(d.solo)s.extraStacks.featured.push(id);
        else if(d.family==='strings')s.strings.push(id);
        else if(d.family==='woodwinds')s.winds.push(id);
        else if(id==='choir')s.choir=id;else if(id==='harp')s.harp=id;
        else if(d.family==='colours')s.extraStacks.rightColour.push(id);else s.rear.push(id)}
      window.orchestraStage.setScene(s);
      document.querySelector('.legend').innerHTML='<span><i class="gold"></i>Solo active</span><span><i class="sage"></i>Active</span><span><i></i>Rest</span>';
      document.querySelector('.stage-caption').textContent='LIVE LEVELS FROM INDIVIDUAL TRACKS';
    }''', {'ids': ids, 'tune': tune})


def solo(key):
    return 'solo' in key or key in ('hero_sax', 'violin_concertmaster')


def frame_values(levels, i):
    return {key: {'level': float(v[i]), 'state': 'rest' if v[i] < .04 else
                 'melody' if solo(key) else 'active'} for key, v in levels.items()}


def screenshot(page):
    return Image.open(io.BytesIO(page.screenshot(type='png'))).convert('RGB')


def capture_cells(page, ids):
    rects = page.evaluate('''()=>Object.fromEntries([...document.querySelectorAll('.player')].map(el=>{
      const box=r=>({left:r.left,top:r.top,right:r.right,bottom:r.bottom});
      return [el.dataset.instrument,{cell:box(el.getBoundingClientRect()),
        bars:[...el.querySelectorAll('.meter i')].map(b=>box(b.getBoundingClientRect()))}]}))''')
    boxes = {}
    for key, rect in rects.items():
        r = rect['cell']
        box = (math.floor(r['left']), math.floor(r['top']), math.ceil(r['right']), math.ceil(r['bottom']))
        if box[0] < 0 or box[1] < 0 or box[2] > SIZE[0] or box[3] > SIZE[1]:
            raise ValueError(f'Cell outside stage: {key}')
        if len(rect['bars']) != 12:
            raise ValueError(f'Unexpected meter structure: {key}')
        for bar in rect['bars']:
            if bar['left'] < box[0] or bar['right'] > box[2] or bar['top'] < box[1] or bar['bottom'] > box[3]:
                raise ValueError(f'Meter outside its cell: {key}')
        boxes[key] = box
    page.evaluate('v=>window.orchestraStage.setFrame(v)',
                  {key: {'state': 'rest', 'level': 0} for key in ids})
    base = screenshot(page)
    cells = {key: [base.crop(boxes[key])] for key in ids}
    # Includes level-zero active appearance, which differs from a resting voice.
    for bars in range(13):
        page.evaluate('v=>window.orchestraStage.setFrame(v)',
                      {key: {'state': 'melody' if solo(key) else 'active', 'level': bars / 12} for key in ids})
        shot = screenshot(page)
        for key in ids:
            cells[key].append(shot.crop(boxes[key]))
    # Fractional CSS boxes can share an integer edge pixel. Such overlap is safe
    # only when that entire overlap remains static in EVERY captured state.
    for j, key in enumerate(ids):
        a = boxes[key]
        for other in ids[j + 1:]:
            b = boxes[other]
            overlap = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
            if overlap[2] <= overlap[0] or overlap[3] <= overlap[1]:
                continue
            baseline = np.asarray(base.crop(overlap))
            for owner in (key, other):
                box = boxes[owner]
                local = tuple(v - box[i % 2] for i, v in enumerate(overlap))
                if any(not np.array_equal(np.asarray(cell.crop(local)), baseline) for cell in cells[owner]):
                    raise ValueError(f'Dynamic pixels overlap between cells: {key}, {other}')
    return base, boxes, cells, rects


def compose_frame(base, boxes, cells, levels, i):
    result = base.copy()
    for key, values in levels.items():
        value = float(values[i])
        # JavaScript Math.round uses floor(x+.5), unlike Python's banker rounding.
        state = 0 if value < .04 else 1 + min(12, math.floor(value * 12 + .5))
        if state:
            result.paste(cells[key][state], boxes[key][:2])
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tune_dir', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--background', type=Path)
    ap.add_argument('--fps', type=int, default=12)
    ap.add_argument('--url', help='Optional external UI URL; default serves current local UI in-browser, offline')
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--limit-seconds', type=float, help='Short smoke-test export; default is full song')
    args = ap.parse_args()
    if args.fps <= 0 or (args.limit_seconds is not None and args.limit_seconds <= 0):
        ap.error('FPS and limit-seconds must be positive')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tune = json.loads((args.tune_dir / 'tune.json').read_text(encoding='utf-8'))
    mix = next((args.tune_dir / name for name in ('mix.wav', 'mix.flac') if (args.tune_dir / name).is_file()), None)
    if mix is None:
        raise FileNotFoundError('mix.wav or mix.flac required')
    duration = sf.info(mix).duration
    frames = math.ceil(duration * args.fps)
    paths = {key: audio_path(args.tune_dir, name) for key, name in tune['files']['stems']['tracks'].items()}
    started = time.monotonic()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=EDGE, headless=True)
        page = browser.new_page(viewport={'width': SIZE[0], 'height': SIZE[1]}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(f'JavaScript: {error}'))
        page.on('requestfailed', lambda request: errors.append(f'Request: {request.url}: {request.failure}'))
        page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}')
                if response.status >= 400 else None)
        # Disable the preview's revision polling before its inline script runs.
        # Offline frames must not depend on development reloads or a shared server.
        page.add_init_script('window.setInterval=()=>0')
        if not args.url:
            ui_root = Path(__file__).resolve().parent
            def local_asset(route):
                relative = unquote(urlparse(route.request.url).path).lstrip('/') or 'index.html'
                path = (ui_root / relative).resolve()
                if not path.is_relative_to(ui_root) or not path.is_file():
                    route.fulfill(status=404, body='Missing local UI asset: ' + relative)
                    return
                mime = 'text/javascript' if path.suffix == '.js' else mimetypes.guess_type(path)[0]
                route.fulfill(status=200, content_type=mime or 'application/octet-stream', body=path.read_bytes())
            page.route('http://orchestra-stage.local/**', local_asset)
        page.goto(args.url or 'http://orchestra-stage.local/')
        try:
            page.wait_for_function('window.orchestraStage && typeof window.orchestraStage.setFrame === "function"')
        except Exception as exc:
            state = page.evaluate('''()=>({url:location.href,ready:document.readyState,
                scripts:[...document.scripts].map(s=>s.src),
                brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.src)})''')
            raise RuntimeError(f'UI initialization failed: {errors}; document={state}') from exc
        if errors:
            raise RuntimeError(f'UI initialization errors: {errors}')
        page.evaluate('''()=>{for(let i=1;i<1000;i++)clearInterval(i);
          document.body.classList.add('clean');document.querySelector('.exit-clean')?.remove()}''')
        mapping = page.evaluate('''async(ids)=>{const {resolveInstrument}=await import('./catalog.js');
          return Object.fromEntries(ids.map(id=>[id,resolveInstrument(id)?.id]))}''', list(paths))
        if any(not key for key in mapping.values()):
            raise ValueError(f'Missing artwork: {[k for k,v in mapping.items() if not v]}')
        levels = measure_levels(paths, mapping, frames, args.fps,
                                args.tune_dir / f'stage-levels-{args.fps}fps.npz')
        scene_setup(page, list(levels), tune)
        if args.background:
            mime = mimetypes.guess_type(args.background)[0] or 'image/png'
            data = base64.b64encode(args.background.read_bytes()).decode('ascii')
            page.evaluate('url=>window.orchestraStage.setBackground(url)', f'data:{mime};base64,{data}')
        page.wait_for_function('Array.from(document.querySelectorAll("#players img,#stage-floor,#background")).every(i=>i.complete&&i.naturalWidth>0)')
        page.evaluate('()=>document.fonts.ready')
        base, boxes, cells, rects = capture_cells(page, list(levels))
        preview_i = min(frames - 1, round(60 * args.fps))
        preview = compose_frame(base, boxes, cells, levels, preview_i)
        preview.save(args.out.with_suffix('.preview.png'))
        # Actual browser frame verifies mixed states + meter pixels, including effects/clipping.
        differences = []
        for i in dict.fromkeys((0, preview_i, frames - 1)):
            page.evaluate('v=>window.orchestraStage.setFrame(v)', frame_values(levels, i))
            reference = screenshot(page)
            fast = compose_frame(base, boxes, cells, levels, i)
            diff = np.abs(np.asarray(reference).astype(np.int16) - np.asarray(fast).astype(np.int16))
            differences.append({'frame': i, 'max_channel_error': int(diff.max()),
                                'different_pixels': int(np.any(diff, axis=2).sum())})
            # Chromium can differ by two 8-bit rounding steps at antialiased edges
            # when neighbouring layers have different states. Geometry must match.
            if diff.max() > 2:
                reference.save(args.out.with_suffix('.browser.png'))
                raise RuntimeError(f'Cached cells differ from browser UI: {differences[-1]}')
            if i == preview_i:
                reference.save(args.out.with_suffix('.browser.png'))
        browser.close()
    report = {'title': tune['title'], 'duration': duration, 'fps': args.fps, 'tracks': mapping,
              'background': str(args.background) if args.background else None,
              'verification': differences, 'cells': rects,
              'meter': 'RMS dBFS, fixed -60 to -12 dB range, 220ms release; registration powers combined; tracks only',
              'snapshot_seconds': round(time.monotonic() - started, 2)}
    if not args.preview:
        output_duration = min(duration, args.limit_seconds) if args.limit_seconds else duration
        count = math.ceil(output_duration * args.fps)
        with args.out.with_suffix('.ffmpeg.log').open('w') as log:
            enc = subprocess.Popen(['ffmpeg', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                '-video_size', '1920x1080', '-framerate', str(args.fps), '-i', 'pipe:0', '-i', str(mix),
                '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-t', str(output_duration),
                '-movflags', '+faststart', str(args.out)], stdin=subprocess.PIPE, stderr=log)
            try:
                for i in range(count):
                    enc.stdin.write(compose_frame(base, boxes, cells, levels, i).tobytes())
                    if i % (args.fps * 30) == 0:
                        print(f'{i / args.fps:.0f}/{output_duration:.1f}s', flush=True)
                enc.stdin.close()
                if enc.wait():
                    raise RuntimeError(f'ffmpeg failed; see {args.out.with_suffix(".ffmpeg.log")}')
            finally:
                if enc.poll() is None:
                    enc.kill()
                    enc.wait()
        report['output_duration'] = output_duration
    report['total_seconds'] = round(time.monotonic() - started, 2)
    args.out.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'seconds': report['total_seconds'],
                      'verification': differences}), flush=True)


if __name__ == '__main__':
    main()
