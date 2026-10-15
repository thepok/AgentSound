"""Measure the endless new-age generator against the composed references (no audio).

    python songs/_blind/measure_newage.py [--seeds 100-123] [--json OUT] [--refs] [--set2] [--metrics a,b,...]

Per seed: compose (mood rolled), build, composer.score_metrics + composer.score with the new-age table. Prints the
score distribution (mean / sd / min / max), the best-of-8 gain (per block of 8 seeds: best - mean), the mean of every
metric (or the --metrics ones) and, with --refs, the same for letters-to-the-morning and the songs/pro-newage-*
references (their score and their metric values side by side); --set2 adds the second hand-written set (REFS2:
eight pieces of other moods / meters / forms / climax places, songs/pro-newage-*/NOTES.md).
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import endless  # noqa: E402
from agentsound.endless import composer, genres  # noqa: E402

REFS = ['letters-to-the-morning', 'pro-newage-rain', 'pro-newage-hopeful', 'pro-newage-waltz']
REFS2 = ['pro-newage-skylight', 'pro-newage-morning', 'pro-newage-longing', 'pro-newage-lantern', 'pro-newage-tide',
         'pro-newage-snowfield', 'pro-newage-homecoming', 'pro-newage-embers']


def ref_song(name: str):
    """A reference's Song, its written chart as song.endless_timeline (as perform.build_piano records it)."""
    folder = ROOT / 'songs' / name
    spec = importlib.util.spec_from_file_location('mna_' + name.replace('-', '_'), folder / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(folder))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
            song = mod.build()
    finally:
        sys.path.remove(str(folder))
    m = float(song.beats_per_bar)
    song.endless_timeline = [((k - 1) * m + i * m / len(mod.LH[k].split()), m / len(mod.LH[k].split()),
                              part.split(':')[0]) for k in sorted(mod.LH) for i, part in enumerate(mod.LH[k].split())]
    return song


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='100-123')
    ap.add_argument('--json')
    ap.add_argument('--refs', action='store_true')
    ap.add_argument('--set2', action='store_true', help='also the second set (REFS2); implies --refs')
    ap.add_argument('--metrics')
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.seeds.split('-'))
    g = genres.get('new-age-piano')
    rows = {}
    for sd in range(lo, hi + 1):
        tune = composer.compose(g, sd)
        song = endless.song(tune)
        m = composer.score_metrics(song, tune, 'new-age')
        sc = composer.score(song, tune, g, metrics=m)
        rows[sd] = {'score': sc['score'], 'mood': tune.mood, 'feel': tune.feel, 'metrics': m,
                    'worst': [w['metric'] for w in sc['worst']]}
    scores = [r['score'] for r in rows.values()]
    print(f"generated: {len(scores)} tunes, score mean {st.mean(scores):.1f} sd {st.pstdev(scores):.1f} "
          f"min {min(scores):.1f} max {max(scores):.1f}")
    seeds = sorted(rows)
    gains = [max(rows[s]['score'] for s in seeds[i:i + 8]) - st.mean(rows[s]['score'] for s in seeds[i:i + 8])
             for i in range(0, len(seeds) - 7, 8)]
    if gains:
        print(f"best-of-8 gain (best - mean per block of 8): {', '.join(f'{x:.1f}' for x in gains)}")
    worst = {}
    for r in rows.values():
        for w in r['worst']:
            worst[w] = worst.get(w, 0) + 1
    print('most frequent worst offenders: ' + ', '.join(f"{k} {v}" for k, v in sorted(worst.items(),
                                                                                     key=lambda kv: -kv[1])[:10]))
    keys = sorted({k for r in rows.values() for k in r['metrics']})
    if a.metrics:
        keys = [k for k in a.metrics.split(',') if k in keys]
    refs = {}
    if a.refs or a.set2:
        for name in REFS + (REFS2 if a.set2 else []):
            if not (ROOT / 'songs' / name / 'song.py').is_file():
                continue
            try:
                song = ref_song(name)
                m = composer.score_metrics(song, None, 'new-age')
            except Exception as e:                      # (a reference still being written)
                print(f"{name}: skipped ({type(e).__name__}: {e})")
                continue
            refs[name] = {'score': composer.score(song, None, g, metrics=m)['score'], 'metrics': m}
        print('references: ' + ', '.join(f"{n} {r['score']:.1f}" for n, r in refs.items()))
    print(f"\n{'metric':<16} {'gen mean':>9} {'gen sd':>7}  " + '  '.join(f"{n.replace('pro-newage-', '')[:12]:>12}" for n in refs))
    for k in keys:
        xs = [r['metrics'][k] for r in rows.values() if k in r['metrics']]
        if not xs:
            continue
        print(f"{k:<16} {st.mean(xs):9.3f} {st.pstdev(xs):7.3f}  " + '  '.join(
            f"{refs[n]['metrics'].get(k, float('nan')):12.3f}" for n in refs))
    if a.json:
        Path(a.json).write_text(json.dumps({'rows': rows, 'refs': refs}, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
