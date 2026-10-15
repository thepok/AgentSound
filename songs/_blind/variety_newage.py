"""How VARIED is a set of endless new-age pieces (HUMAN_FEEDBACK 2026-10-12: "nicht sehr abwechslungsreich")? No audio.

    python songs/_blind/variety_newage.py [--seeds 100-123] [--set N] [--best K] [--json OUT]

Two sets of pieces, each measured as a SET:
  teacher   compose(genre, seed) for every seed (mood rolled - what the learned generator's teacher export sees)
  set       --set N: a set plan of N slots (composer.set_plan, seed = the first seed), slot k composed from seed
            first + 100 k; --best K: each slot the best of K candidates (run.candidates, the runner's best-of-N - does
            the score collapse the set onto its safest choices?)
Per piece: mood, feel, mode, meter, tempo, layout (the arrangement's form), climax kind, register shift, the climax
pitch (the top line's highest note before the final chord) and its place (score metric climax_x), the ending (the
last return's cadence + the coda's frame / approach / line + the final chord's style), the intro (its vamp, its line,
the left hand's bars alone), the length. Per set and dimension: the distinct values, the most common one's share
(max_share: 1.0 = every piece alike) and the effective count (e^entropy: 1 = one value, k = k values evenly spread;
'variety' = their geometric mean); numbers: mean, sd, min-max; with a set plan also the share of slots repeating the
slot before (adj_same).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
import types
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import endless  # noqa: E402
from agentsound.endless import composer, genres  # noqa: E402
from agentsound.endless.composer import FRAME_SECTIONS, top_line  # noqa: E402

CATS = ('mood', 'feel', 'mode', 'meter', 'tempo_band', 'layout', 'climax_kind', 'shift', 'climax_pitch',
        'climax_x_band', 'last_return', 'coda', 'intro_line', 'intro_lh')


def _derive(r: dict) -> dict:
    """The ending / intro strings split into their dimensions: the last return (its section + cadence), the coda (its
    frame + approach), the intro's line and its left-hand-alone bars."""
    e = r.get('ending', '').split('|')
    i = r.get('intro', '').split('|')
    return dict(r, last_return=e[0] if e else None, coda='|'.join(e[1:3]) if len(e) > 2 else None,
                intro_line=i[1] if len(i) > 1 else None, intro_lh=i[2] if len(i) > 2 else None)
NUMS = ('tempo', 'climax_midi', 'climax_x', 'seconds', 'score')


def lead_variety(tunes) -> dict:
    """The learned generator's set measure (learn.evaluate.variety on the pieces' tokens: mood, feel, form, mode, key,
    tempo, climax position + pitch in the head, ending - 0 all alike .. 1 maximally even) - the headline number; the
    rows below add what the tokens do not carry (the meter, the arrangement's layout and climax kind, the frames)."""
    from agentsound.learn import evaluate as E, tokens as T
    return E.variety([T.encode(t) for t in tunes], genres.get('new-age-piano'))


def piece(tune, song, sc=None) -> dict:
    g = genres.get(tune.genre)
    m = composer.score_metrics(song, tune, 'new-age')
    sc = sc or composer.score(song, tune, g, metrics=m)
    arr = getattr(song, 'endless_arrangement', None)         # (the players' record: endless.arrangement)
    drawn = arr.sections if arr is not None else {}
    body = [x for x in song.sections if x.name not in FRAME_SECTIONS]
    last = body[-1].name if body else ''
    line = top_line([(n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes])
    end_t = song.sections[-1].start if song.sections else 1e9
    pk = max((n[2] for n in line if n[0] < end_t - 0.25), default=0)
    tpc = composer.Key(tune.key).tonic % 12
    cad = (drawn.get(last) or {}).get('cadence', '-')
    climax_kind = next((d['climax'] for d in drawn.values() if 'climax' in d), '-')
    intro = drawn.get('intro') or {}
    sec = song.seconds(song.length)
    cx = m.get('climax_x')
    return {'seed': tune.seed, 'mood': tune.mood, 'feel': tune.feel, 'mode': tune.mode, 'meter': tune.meter,
            'tempo': tune.tempo, 'tempo_band': f"{tune.tempo // 8 * 8}-{tune.tempo // 8 * 8 + 7}",
            'layout': (arr.piece.get('layout') if arr is not None else None) or '-', 'climax_kind': climax_kind,
            'shift': (tune.arrange or {}).get('shift', 0) if hasattr(tune, 'arrange') else 0,
            'climax_midi': pk, 'climax_pitch': composer.note_name(pk), 'climax_rel': (pk - tpc) % 12,
            'climax_x': cx, 'climax_x_band': None if cx is None else round(cx * 20) / 20,
            'ending': f"{last}:{cad}|{tune.tag.get('frame')}|{tune.tag.get('approach')}|{tune.tag.get('line')}|"
                      f"{tune.end_kind}",
            'intro': f"{tune.intro.get('kind')}|{tune.intro.get('line')}|lh{intro.get('lh_only', '-')}",
            'sections': ' '.join(x.name for x in song.sections), 'seconds': round(sec, 1), 'score': sc['score'],
            'title': tune.title}


def summary(rows: list, ordered: bool = False) -> dict:
    rows = [_derive(r) for r in rows]
    out = {}
    for k in CATS:
        vals = [r[k] for r in rows if r.get(k) is not None]
        c = Counter(vals)
        n = len(vals)
        ent = -sum(v / n * math.log(v / n) for v in c.values()) if n else 0.0
        d = {'distinct': len(c), 'max_share': round(max(c.values()) / n, 2) if n else None,
             'eff': round(math.exp(ent), 2), 'top': c.most_common(3)}
        if ordered and n > 1:
            d['adj_same'] = round(sum(a == b for a, b in zip(vals, vals[1:])) / (n - 1), 2)
        out[k] = d
    for k in NUMS:
        xs = [r[k] for r in rows if r.get(k) is not None]
        if xs:
            out[k] = {'mean': round(st.mean(xs), 2), 'sd': round(st.pstdev(xs), 2), 'min': min(xs), 'max': max(xs)}
    # one number: the geometric mean of the effective counts (e^entropy: 1 = every piece alike, k = k values evenly
    # spread) over the categorical dimensions
    out['variety'] = round(math.exp(st.mean(math.log(out[k]['eff']) for k in CATS)), 2)
    return out


def show(name: str, s: dict) -> None:
    print(f"\n== {name}: variety (geometric mean of the effective counts) {s['variety']}")
    for k in CATS:
        d = s[k]
        adj = f"  adj_same {d['adj_same']}" if 'adj_same' in d else ''
        print(f"  {k:<14} distinct {d['distinct']:>2}  max_share {d['max_share']}  eff {d['eff']}{adj}  "
              f"top {', '.join(f'{v}:{c}' for v, c in d['top'])}")
    for k in NUMS:
        if k in s:
            d = s[k]
            print(f"  {k:<14} mean {d['mean']}  sd {d['sd']}  {d['min']}..{d['max']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='100-123')
    ap.add_argument('--set', type=int, default=0, help='also a set plan of N slots')
    ap.add_argument('--best', type=int, default=1, help='best of K candidates per set slot (run.candidates)')
    ap.add_argument('--json')
    ap.add_argument('--from', dest='src', help='re-summarize a saved --json (no composing)')
    a = ap.parse_args()
    if a.src:
        res = json.loads(Path(a.src).read_text(encoding='utf-8'))
        for name, d in res.items():
            show(name, summary(d['rows'], ordered=name == 'set'))
            if d.get('lead'):
                from agentsound.learn.evaluate import variety_line
                print('  learn.evaluate.variety: ' + variety_line(d['lead']))
        return 0
    lo, hi = (int(x) for x in a.seeds.split('-'))
    g = genres.get('new-age-piano')
    res = {}
    rows, tunes = [], []
    for sd in range(lo, hi + 1):
        tune = composer.compose(g, sd)
        tunes.append(tune)
        rows.append(piece(tune, endless.song(tune)))
    res['teacher'] = {'rows': rows, 'summary': summary(rows), 'lead': lead_variety(tunes)}
    show(f"teacher (compose, seeds {lo}-{hi})", res['teacher']['summary'])
    from agentsound.learn.evaluate import variety_line
    print('  learn.evaluate.variety: ' + variety_line(res['teacher']['lead']))
    if a.set:
        from agentsound.endless import run
        plan = composer.set_plan(g, a.set, lo)
        args = types.SimpleNamespace(mood=None, swing=None)
        rows, tunes = [], []
        for k, slot in enumerate(plan):
            seed = lo + 100 * k
            if a.best > 1:
                cs = run.candidates(g, seed, a.best, args, lambda *x: None, plan=slot)
                if not cs:
                    continue
                c = cs[0]
                tunes.append(c['tune'])
                rows.append(piece(c['tune'], c['song'], c['score']))
            else:
                tune = composer.compose(g, seed, plan=slot)
                tunes.append(tune)
                rows.append(piece(tune, endless.song(tune)))
        res['set'] = {'rows': rows, 'summary': summary(rows, ordered=True), 'lead': lead_variety(tunes)}
        show(f"set plan of {a.set} (best of {a.best})", res['set']['summary'])
        print('  learn.evaluate.variety: ' + variety_line(res['set']['lead']))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, default=str), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
