"""Render every cue of berg.py, calibrate the loudness and export the WAVs for the audio drama.

python songs/ab-in-die-berge/render_all.py [cue ...] [--calibrate] [--export]
  (no flags)   build each cue to out/<cue>/ and print duration / LUFS / true peak / warnings
  --calibrate  after the build, set levels.json (the master limiter input gain per cue) towards TARGET LUFS and
               build again (twice at most)
  --export     copy out/<cue>/mix.wav to D:/Projekte/hoerspiele/bergurlaub/music/<cue>.wav (44.1 kHz stereo,
               24-bit) and write cues.json there
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path[:0] = [str(HERE), str(REPO)]
from berg import CUES  # noqa: E402

TARGET = -16.0                         # LUFS-I for every cue (the drama mixes them by level_db relative to speech)
DEST = Path('D:/Projekte/hoerspiele/bergurlaub/music')
MANIFEST = Path('D:/Projekte/hoerspiele/bergurlaub/manifest.json')
LOOPABLE = set()                       # no cue is cut as a seamless loop: the beds are long, with a fade-able end


def build(cue):
    env = dict(os.environ, BERG_CUE=cue)
    out = HERE / 'out' / cue
    p = subprocess.run([sys.executable, '-m', 'agentsound', 'build', str(HERE), '--out', str(out), '--no-mp3'],
                       cwd=REPO, env=env, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stdout[-3000:], p.stderr[-3000:])
        raise SystemExit(f'{cue}: build failed')
    r = json.loads((out / 'report.json').read_text(encoding='utf-8'))
    g = r['global']
    warns = [w['code'] for w in r['warnings'] if w['severity'] in ('warn', 'error')]
    return {'seconds': g['durationSec'], 'lufs': g['lufsIntegrated'], 'tp': g['truePeakDbtp'],
            'width': g['widthPct'], 'corr': g['stereoCorrelation'], 'warn': warns, 'clicks': g['clicks']}


def main(argv):
    cues = [a for a in argv if not a.startswith('--')] or list(CUES)
    lv_path = HERE / 'levels.json'
    levels = json.loads(lv_path.read_text(encoding='utf-8')) if lv_path.exists() else {}
    res = {}
    for c in cues:
        res[c] = build(c)
        if '--calibrate' in argv:
            for _ in range(2):
                d = TARGET - res[c]['lufs']
                if abs(d) < 0.4:
                    break
                levels[c] = round(min(24.0, max(-12.0, levels.get(c, 0.0) + d)), 1)
                lv_path.write_text(json.dumps(levels, indent=1, sort_keys=True), encoding='utf-8')
                res[c] = build(c)
        x = res[c]
        print(f"{c:16s} {x['seconds']:6.1f} s  {x['lufs']:6.1f} LUFS  TP {x['tp']:5.1f}  width {x['width']:4.0f}%  "
              f"corr {x['corr']:.2f}  clicks {x['clicks']}  gain {levels.get(c, 0.0):+.1f}  {' '.join(x['warn'])}",
              flush=True)
    if '--export' in argv:
        man = json.loads(MANIFEST.read_text(encoding='utf-8'))
        mode = {it['cue']: it['mode'] for it in man['items'] if it.get('type') == 'music'}
        DEST.mkdir(parents=True, exist_ok=True)
        idx_path = DEST / 'cues.json'
        idx = json.loads(idx_path.read_text(encoding='utf-8')) if idx_path.exists() else {}
        ff = shutil.which('ffmpeg') or 'C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe'
        for c in cues:
            src = HERE / 'out' / c / 'mix.wav'
            dst = DEST / f'{c}.wav'
            subprocess.run([ff, '-y', '-loglevel', 'error', '-i', str(src), '-ar', '44100', '-ac', '2',
                            '-c:a', 'pcm_s24le', str(dst)], check=True)
            idx[c] = {'file': f'{c}.wav', 'seconds': round(res[c]['seconds'], 2), 'mode': mode[c],
                      'loopable': c in LOOPABLE, 'lufs': round(res[c]['lufs'], 1)}
        order = [it['cue'] for it in man['items'] if it.get('type') == 'music']
        idx = {k: idx[k] for k in order if k in idx}
        idx_path.write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding='utf-8')
        print('exported', len(cues), 'cues ->', DEST)


if __name__ == '__main__':
    main(sys.argv[1:])
