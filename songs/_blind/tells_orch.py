"""The orchestra-symphonic blind rounds' tells (round o2's judges, songs/_blind/ROUNDS.md "Round o2") measured on the
endless pieces without audio - before / after numbers for the fixes, for ANY code version (CODE_ROOT: this repo or a
`git archive` of master; the script imports agentsound from it).

    python songs/_blind/tells_orch.py CODE_ROOT SEED [SEED ...] [--json OUT] [--o3]   # 8-piece sets
                                                                         # (composer.set_plan)

Per piece (compose + build, one candidate per slot, no render):
  motto_ok     the motto has character (o2 tell 5): at most one repeated note in a row, a leap of a fourth or more,
               one highest note; motto_rep its repeated notes
  dev_motto    share of the development's bars (the dev blocks) where a melodic part (melody / counter / voice /
               bass - no doubling) states a motto shape: 3 onsets with the motto head's rhythm ratios (any speed)
               and its interval directions (or inverted) - o2 tell 2 (want high)
  build_stock  the pre-climax build is the stock one (o2 tell 1): a timpani roll of 8+ beats in the block before
               the climax (both o2 builds kept it); build_cym a cymbal roll there
  clx_copy     the climax's melody against the first theme's: share of its notes on the same onset (relative to
               the block) and the same interval to the note before - the theme restated louder (o2 tell 3)
  clx_double   the share of the peak block's sounding roles that double its melody (the whole tutti on the tune)
  top_early    1 when a note before the climax block is as high as the climax block's highest (the top register
               spent early)
  slips        notes out of idiom (o2 tell 6): basses under E1, horns over D5, trumpets over C6, flutes under G4
Per set (o2 tell 4, the material shared ACROSS pieces - the template the judges hear):
  same_open    pairs of pieces with the same opening gesture (gesture(): the melody's role, harp arpeggios, a
               running stream in thirds, timpani / cymbal rolls, the accompaniment's figure, the tune doubled)
  same_t2      pairs with the same second-theme gesture
  t2_contour   pairs whose second themes share 5+ of their first 7 intervals
  acc_jacc     the mean Jaccard of the pieces' accompaniment cells (per ostinato / figuration / harmony part and
               bar: the onset rhythm on a 1/4-beat grid and the contour class), cells used in 4+ bars
  same_build / same_climax   pairs with the same build / climax gesture
  material     the mean of the six pair shares above: the cross-piece material similarity (want low)
Round o4 (the o3 judges' tells: songs/_blind/ROUNDS.md "Round o3"), per piece:
  row          the form's block row (kind class, song bars) - per set same_row (pairs with the same row of kind
               classes), row_sim (1 - the rows' edit distance / the longer), same_bars (the same row AND the same
               bars), same_core (the macro form: the optional blocks out, the development kinds one); mod48 the
               share of the blocks of 4 / 8 / 16 song bars (want lower), lens the distinct block lengths
  recap_mel    the recapitulation blocks' (recap / recap2) melody bars inside a copy of two exposition melody bars in
               a row (the onsets and intervals, any key) - o3 tell 2 (want low); recap_bars the recap blocks'
               role-bars (3+ notes) that copy an exposition role-bar note for note; t2_back 1 when the second theme
               returns after
               the development, t2_copy its onset + interval share against the exposition's (want low)
  build_frame  1 when the pre-climax block is the frame the judges hear (o3 tell 3: "a bare dominant pedal, a
               line climbing"): the lowest line holds the dominant half the block or more (build_pedal the share);
               build_rise 1 when the top line climbs (its bar maxima up 5+ semitones, 60 %+ of the steps not down)
  t2_cells     the second theme's distinct bar rhythms; t2_npb its notes per bar; t2_ok: 4+ cells, 2.5+ notes per
               bar, one highest note, the answer phrase in the head's rhythm (bars 5-6 = bars 1-2) - o3 tell 4
  lead_cells   distinct bar rhythms of the melody parts per 25 bars with melody
  folds        octave folds in fast lines (o3 tell 5): a jump of 10+ semitones between notes 0.5 beat or closer
               whose neighbours move by step; osti_max the longest run of bars a role's accompaniment repeats one
               pattern (rhythm + intervals), osti8 the parts that repeat one 8+ bars
  viola_over   viola notes above every violin note sounding (o3 tell 6); timp_off timpani notes off the home's
               and the block's tonic / dominant or outside D2..G3; flute_top flute notes at B6+; chamber_bare 1 when
               a chamber piece's climax has no brass; brass_flat brass tracks (16+ notes) whose velocities spread under 12
               (10-90 %) - the gate's flat_dynamics (o3 tell 7)
"""
from __future__ import annotations

import itertools
import json
import os
import statistics as st
import sys
from pathlib import Path

_EPS = 1e-6
MEL_FN = ('melody', 'counter', 'voice', 'bass')
ACC_FN = ('ostinato', 'figuration', 'harmony', 'inner')
SLIP = {'basses': ('lo', 28), 'horns': ('hi', 74), 'trumpets': ('hi', 84), 'flutes': ('lo', 67)}


def _iois(ns):
    return [b[0] - a[0] for a, b in zip(ns, ns[1:])]


def _sign(x):
    return (x > 0) - (x < 0)


def motto_shape(sym, m) -> tuple:
    """The motto head's (ratios of the first IOIs, interval directions) - 3 onsets."""
    ns = sym.motto_notes(m, 0.0, 60, {0, 2, 4, 5, 7, 9, 11})
    ns = sorted(ns)[:3]
    io = _iois(ns)
    if len(io) < 2 or min(io) <= _EPS:
        return None
    return (round(io[1] / io[0], 3), tuple(_sign(b[2] - a[2]) for a, b in zip(ns, ns[1:])))


def motto_hits(line, shape) -> list:
    """The onsets of the windows of 3 notes of a line that state the motto shape (rhythm ratio, directions or
    inverted)."""
    if not shape:
        return []
    ratio, dirs = shape
    inv = tuple(-d for d in dirs)
    ns = sorted(line)
    out = []
    for i in range(len(ns) - 2):
        w = ns[i:i + 3]
        io = _iois(w)
        if min(io) <= _EPS or io[0] > 4.0:
            continue
        if abs(io[1] / io[0] - ratio) > 0.08 * max(1.0, ratio):
            continue
        d = tuple(_sign(b[2] - a[2]) for a, b in zip(w, w[1:]))
        if d == dirs or (any(dirs) and d == inv):
            out.append(w[0][0])
    return out


def motto_character(sym, m) -> dict:
    ps = [p for _, _, p in sorted(sym.motto_notes(m, 0.0, 60, {0, 2, 4, 5, 7, 9, 11}))]
    rep = sum(1 for a, b in zip(ps, ps[1:]) if a == b)
    run = best = 0
    for a, b in zip(ps, ps[1:]):
        run = run + 1 if a == b else 0
        best = max(best, run)
    leap = max((abs(b - a) for a, b in zip(ps, ps[1:])), default=0)
    peak1 = ps.count(max(ps)) == 1 if ps else False
    return {'motto_rep': rep, 'motto_ok': int(best <= 1 and leap >= 5 and peak1), 'motto_leap': leap}


def _cells(parts, bpb):
    """{cell: bars} of the accompaniment parts: per part and bar the onset rhythm on a 1/4-beat grid + contour."""
    out = {}
    for p in parts:
        if p.function not in ACC_FN:
            continue
        bars = {}
        for a, d, q in p.notes:
            bars.setdefault(int((a + 0.1) // bpb), []).append((a, q))
        for b, ns in bars.items():
            ns = sorted(ns)
            if len(ns) < 2:
                continue
            rh = tuple(round(((a - b * bpb) % bpb) * 4) for a, _ in ns)
            iv = [y[1] - x[1] for x, y in zip(ns, ns[1:])]
            cls = 'rep' if all(v == 0 for v in iv) else 'up' if all(v >= 0 for v in iv) else \
                'down' if all(v <= 0 for v in iv) else 'mix'
            key = (p.function, rh, cls)
            out[key] = out.get(key, 0) + 1
    return {k for k, v in out.items() if v >= 4}


def measure(sym, tune, song) -> dict:
    mat = tune.symphony
    k = float(mat['scale'])
    bpb = song.beats_per_bar
    blocks = {b['name']: b for b in mat['blocks']}
    parts = song.orchestration.parts
    sb = song.orch_score.blocks
    res = dict(motto_character(sym, mat['motto']))
    shape = motto_shape(sym, mat['motto'])
    # (the motto shape in the song's beats: the ratios are scale-free)
    dev = [b for b in mat['blocks'] if b['kind'].startswith('dev')]
    hit_bars = tot = 0
    for b in dev:
        a0, L = b['start'] * k, b['bars'] * mat['U'] * k
        bars = set()
        for p in parts:
            if p.block == b['name'] and p.function in MEL_FN:
                for x in motto_hits(p.notes, shape):
                    bars.add(int((x - a0 + 0.1) // bpb))
        n = int(round(L / bpb))
        hit_bars += len(bars)
        tot += n
    res['dev_motto'] = round(hit_bars / tot, 3) if tot else None
    # the build: the block before the peak (the retransition)
    peak = next((x for x in sb if x.peak), None)
    names = [x.name for x in sb]
    pre = sb[names.index(peak.name) - 1] if peak is not None and names.index(peak.name) > 0 else None
    if pre is not None:
        tim = [n for p in parts if p.block == pre.name and p.role == 'timpani' for n in p.notes]
        perc = [n for p in parts if p.block == pre.name and p.role == 'percussion' for n in p.notes]
        from agentsound.bandlib import orchestra as orch
        cym = orch.PERCUSSION_KEYS.get('cymbal_roll')
        res['build_stock'] = int(any(d >= 8 for _, d, _ in tim))       # (o2: both builds kept the timpani roll)
        res['build_cym'] = int(any(q == cym for _, _, q in perc))
        res['build_tex'] = pre.texture
    else:
        res['build_stock'], res['build_tex'] = 0, None
    # the climax against the first theme
    res['clx_tex'] = peak.texture if peak is not None else None
    t1 = next((b for b in mat['blocks'] if b['kind'] in ('t1', 'river')), None)
    if peak is not None and t1 is not None:
        cm = sorted(n for p in parts if p.block == peak.name and p.function == 'melody' for n in p.notes)
        cm = sorted({round(a - peak.start, 3): (a, d, q) for a, d, q in cm}.values())
        tm = sorted((a * k - t1['start'] * k, d * k, q) for a, d, q in t1['theme'])
        if len(cm) > 2 and len(tm) > 2:
            tset = {(round(b_[0], 2), b_[2] - a_[2]) for a_, b_ in zip(tm, tm[1:])}
            same = sum(1 for a_, b_ in zip(cm, cm[1:]) if (round(b_[0] - peak.start, 2), b_[2] - a_[2]) in tset)
            res['clx_copy'] = round(same / (len(cm) - 1), 3)
        roles = {p.role for p in parts if p.block == peak.name and p.notes}
        dbl = {p.role for p in parts if p.block == peak.name and p.function == 'doubling' and p.voice == 'melody'}
        mel = {p.role for p in parts if p.block == peak.name and p.function == 'melody'}
        res['clx_double'] = round(len(dbl | mel) / max(1, len(roles)), 3)
        top_peak = max((q for p in parts if p.block == peak.name for _, _, q in p.notes
                        if p.role not in ('percussion', 'timpani')), default=0)
        before = max((q for p in parts for a, _, q in p.notes if a < peak.start - _EPS
                      and p.role not in ('percussion', 'timpani')), default=0)
        res['top_early'] = int(before >= top_peak)
    slips = 0
    for p in parts:
        r = SLIP.get(p.role)
        if r:
            slips += sum(1 for _, _, q in p.notes if (q < r[1] if r[0] == 'lo' else q > r[1]))
    res['slips'] = slips
    # the cross-piece GESTURES (what the judges hear, not the texture's name)
    first = sb[0]
    res['open_sig'] = gesture(parts, first, bpb)
    t2 = next((x for x in sb if blocks.get(x.name, {}).get('kind') in ('t2', 'river')), None)
    if t2 is not None:
        res['t2_sig'] = gesture(parts, t2, bpb)
        th = sorted(blocks[t2.name]['theme'])
        res['t2_iv'] = [b_[2] - a_[2] for a_, b_ in zip(th, th[1:])][:7]
    res['build_sig'] = gesture(parts, pre, bpb) if pre is not None else None
    res['clx_sig'] = gesture(parts, peak, bpb) + [int(res.get('clx_copy', 0) >= 0.5)] if peak is not None else None
    res['acc_cells'] = sorted(map(list, _cells(parts, bpb)))
    return res


def gesture(parts, blk, bpb) -> list:
    """A block's gesture, coarse (what a reader of the score names): the melody's role, harp arpeggios, dyads in
    thirds running (the flute-thirds stream), a timpani roll of a bar+, a cymbal roll, the accompaniment's figure
    (repeated 8ths / broken chords / held / running), the melody doubled in 3+ roles."""
    ps = [p for p in parts if p.block == blk.name and p.notes]
    mel = [p for p in ps if p.function == 'melody']
    lead = mel[0].role if mel else next((p.role for p in ps if p.function in ('bass', 'voice')), None)
    harp = any(p.role == 'harp' and len(p.notes) >= 8 for p in ps)
    thirds = False
    for p in ps:
        by = {}
        for a, _, q in p.notes:
            by.setdefault(round(a, 2), []).append(q)
        dy = [v for v in by.values() if len(v) == 2 and 3 <= abs(v[0] - v[1]) <= 4]
        if len(dy) >= 12 and len(dy) >= 0.5 * len(by):
            thirds = True
    roll = any(p.role == 'timpani' and any(d >= bpb for _, d, _ in p.notes) for p in ps)
    from agentsound.bandlib import orchestra as orch
    cyms = {orch.PERCUSSION_KEYS.get(x) for x in ('cymbal_roll', 'cymbal_roll_short', 'cymbal_roll_long')}
    cym = any(p.role == 'percussion' and any(q in cyms for _, _, q in p.notes) for p in ps)
    acc = [p for p in ps if p.function in ACC_FN]
    fig = 'none'
    if acc:
        p = max(acc, key=lambda x: len(x.notes))
        ns = sorted(p.notes)
        io = [b[0] - a[0] for a, b in zip(ns, ns[1:]) if b[0] - a[0] > _EPS]
        med = st.median(io) if io else 99
        rep = sum(1 for a, b in zip(ns, ns[1:]) if a[2] == b[2]) / max(1, len(ns) - 1)
        fig = 'held' if med >= 2 else 'run' if med <= 0.3 else 'pulse' if rep >= 0.5 else 'broken'
    dbl = len({p.role for p in ps if p.function == 'doubling' and p.voice == 'melody'})
    return [lead, int(harp), int(thirds), int(roll), int(cym), fig, int(dbl >= 3)]


def pair_shares(S: list) -> dict:
    pairs = list(itertools.combinations(S, 2))
    if not pairs:
        return {}

    def share(f):
        return round(sum(1 for a, b in pairs if f(a, b)) / len(pairs), 3)
    out = {
        'same_open': share(lambda a, b: a['open_sig'] == b['open_sig']),
        'same_t2': share(lambda a, b: a.get('t2_sig') is not None and a.get('t2_sig') == b.get('t2_sig')),
        't2_contour': share(lambda a, b: a.get('t2_iv') and b.get('t2_iv') and
                            sum(1 for x, y in zip(a['t2_iv'], b['t2_iv']) if x == y) >= 5),
        'acc_jacc': round(st.mean(len({tuple(map(tuple, x)) for x in a['acc_cells']} &
                                      {tuple(map(tuple, x)) for x in b['acc_cells']}) /
                                  max(1, len({tuple(map(tuple, x)) for x in a['acc_cells']} |
                                             {tuple(map(tuple, x)) for x in b['acc_cells']}))
                                  for a, b in pairs), 3),
        'same_build': share(lambda a, b: a['build_sig'] is not None and a['build_sig'] == b['build_sig']),
        'same_climax': share(lambda a, b: a['clx_sig'] is not None and a['clx_sig'] == b['clx_sig']),
    }
    out['material'] = round(st.mean(out.values()), 3)
    return out


# ------------------------------------------------------------------------------------------------ round o4's tells

KCLASS = {'intro': 'O', 'mist': 'O', 'source': 'O', 'solo': 'O', 'slow': 'S', 't1': 'A', 't1b': 'A', 'trans': 'T',
          't2': 'B', 't2b': 'B', 'close': 'K', 'river': 'R', 'episode': 'E', 'dev_dialogue': 'D', 'dev_fugato': 'F',
          'retrans': 'P', 'recap': 'X', 'recap2': 'Y', 'coda': 'C', 'coda_soft': 'C', 'end': 'Z', 'end_soft': 'Z'}


def _edit(a, b) -> int:
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (x != y))
    return d[-1]


def _bar_sig(ns, a0, bpb, exact=False):
    ns = sorted(ns)
    if not ns:
        return None
    rh = tuple((round(a - a0, 2), round(d, 2)) for a, d, _ in ns)
    if exact:
        return rh, tuple(q for _, _, q in ns)
    return rh, tuple(b[2] - a[2] for a, b in zip(ns, ns[1:]))


def _bars_of(notes, start, end, bpb):
    out = {}
    for a, d, q in notes:
        if start - _EPS <= a < end - _EPS:
            out.setdefault(int((a - start + _EPS) // bpb), []).append((a, d, q))
    return out


def measure_o4(sym, tune, song) -> dict:
    from agentsound.theory import Key
    mat = tune.symphony
    k = float(mat['scale'])
    U = mat['U']
    bpb = song.beats_per_bar
    parts = song.orchestration.parts
    sb = {x.name: x for x in song.orch_score.blocks}
    blocks = mat['blocks']
    res = {}
    # -- the form row
    row = [(KCLASS.get(b['kind'], '?'), int(round(b['bars'] * U * k / bpb))) for b in blocks]
    res['row'] = row
    body = [n for c, n in row if c != 'Z']
    res['mod48'] = round(sum(1 for n in body if n in (4, 8, 16)) / max(1, len(body)), 3)
    res['lens'] = len(set(body))
    # -- the recapitulation against the exposition
    first_dev = next((i for i, b in enumerate(blocks) if b['kind'].startswith('dev')), len(blocks))
    expo = [b['name'] for b in blocks[:first_dev]]
    rec = [b['name'] for b in blocks[first_dev:] if b['kind'] in ('recap', 'recap2')]
    mel_expo, all_expo = set(), set()

    def msigs(p):
        x = sb[p.block]
        return {i: _bar_sig(ns, x.start + i * bpb, bpb) for i, ns in _bars_of(p.notes, x.start, x.end, bpb).items()}
    for p in parts:
        if p.block in expo and p.notes:
            x = sb[p.block]
            if p.function == 'melody':              # (two bars in a row, as the exposition had them)
                sg = msigs(p)
                mel_expo.update((sg[i], sg[i + 1]) for i in sg if i + 1 in sg)
            for i, ns in _bars_of(p.notes, x.start, x.end, bpb).items():
                if len(ns) >= 3:
                    all_expo.add((p.role, _bar_sig(ns, x.start + i * bpb, bpb, exact=True)))
    mh = mt = ah = at = 0
    for p in parts:
        if p.block in rec and p.notes:
            x = sb[p.block]
            if p.function == 'melody':
                sg = msigs(p)
                for i in sg:
                    mt += 1
                    mh += (i + 1 in sg and (sg[i], sg[i + 1]) in mel_expo) or \
                        (i - 1 in sg and (sg[i - 1], sg[i]) in mel_expo)
            for i, ns in _bars_of(p.notes, x.start, x.end, bpb).items():
                a0 = x.start + i * bpb
                if len(ns) >= 3:
                    at += 1
                    ah += (p.role, _bar_sig(ns, a0, bpb, exact=True)) in all_expo
    res['recap_mel'] = round(mh / mt, 3) if mt else None
    res['recap_bars'] = round(ah / at, 3) if at else None
    t2 = next((b for b in blocks[:first_dev] if b['kind'] in ('t2', 'river')), None)
    back = [b for b in blocks[first_dev:] if b['kind'] in ('recap2', 't2', 't2b') or
            any(e.get('theme2') and e['block'] == b['name'] for e in mat['log'])]
    res['t2_back'] = int(bool(back)) if t2 is not None else None
    if t2 is not None and back:
        tm = sorted((a - t2['start'], d, q) for a, d, q in t2['theme'])
        cm = sorted((a - back[0]['start'], d, q) for a, d, q in back[0]['theme'])
        if len(tm) > 2 and len(cm) > 2:
            tset = {(round(y[0], 2), y[2] - x[2]) for x, y in zip(tm, tm[1:])}
            res['t2_copy'] = round(sum(1 for x, y in zip(cm, cm[1:]) if (round(y[0], 2), y[2] - x[2]) in tset)
                                   / (len(cm) - 1), 3)
    # -- the build frame: the block before the peak
    order = [b['name'] for b in blocks]
    peak = next((b['name'] for b in blocks if b.get('peak')), None)
    pre = sb[order[order.index(peak) - 1]] if peak and order.index(peak) > 0 else None
    if pre is not None:
        dom = (Key(pre.key).tonic + 7) % 12
        low = [p for p in parts if p.block == pre.name and p.notes and
               (p.function in ('bass', 'pedal') or p.role in ('timpani', 'basses', 'tuba'))]
        grid = [pre.start + 0.5 * i for i in range(int(pre.length / 0.5))]
        hold = 0
        for t in grid:
            ps = [q for p in low for a, d, q in p.notes if a - _EPS <= t < a + d - _EPS]
            if ps:
                hold += min(ps) % 12 == dom
        res['build_pedal'] = round(hold / max(1, len(grid)), 3)
        tops = []
        for i in range(int(round(pre.length / bpb))):
            a0 = pre.start + i * bpb
            ps = [q for p in parts if p.block == pre.name and p.function in ('melody', 'voice', 'counter')
                  for a, d, q in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS]
            if ps:
                tops.append(max(ps))
        steps = [b_ - a_ for a_, b_ in zip(tops, tops[1:])]
        rising = len(tops) >= 3 and tops[-1] - tops[0] >= 5 and sum(1 for x in steps if x >= 0) >= 0.6 * len(steps)
        res['build_rise'] = int(rising)
        res['build_frame'] = int(res['build_pedal'] >= 0.5)
    else:
        res['build_pedal'], res['build_frame'], res['build_rise'] = None, 0, 0
    # -- the second theme as a tune
    if t2 is not None and t2['theme']:
        th = sorted(t2['theme'])
        bars = {}
        for a, d, q in th:
            bars.setdefault(int((a - t2['start'] + _EPS) // U), []).append((round((a - t2['start']) % U, 2),
                                                                            round(d, 2)))
        nb = t2['bars']
        sigs = [tuple(bars.get(i, ())) for i in range(nb - 1)]
        res['t2_cells'] = len(set(sigs))
        res['t2_npb'] = round(len(th) / max(1, nb), 2)
        ps = [q for _, _, q in th]
        answer = nb >= 8 and sigs[0:2] == sigs[4:6]
        res['t2_ok'] = int(res['t2_cells'] >= 4 and res['t2_npb'] >= 2.5 and ps.count(max(ps)) == 1 and answer)
    mb = {}
    for p in parts:
        if p.function == 'melody' and p.notes:
            x = sb[p.block]
            for i, ns in _bars_of(p.notes, x.start, x.end, bpb).items():
                if len(ns) >= 2:
                    mb[(p.block, i)] = _bar_sig(ns, x.start + i * bpb, bpb)[0]
    res['lead_cells'] = round(len(set(mb.values())) * 25.0 / max(1, len(mb)), 2)
    # -- folds and static ostinati
    folds = 0
    omax, o8 = 0, 0
    for p in parts:
        if p.role in ('percussion', 'timpani') or not p.notes:
            continue
        ns = sorted(p.notes)
        if p.function != 'doubling':
            for i in range(1, len(ns) - 2):
                a, b, c, d = ns[i - 1], ns[i], ns[i + 1], ns[i + 2]
                if c[0] - b[0] <= 0.5 + _EPS and b[0] - a[0] <= 0.5 + _EPS and d[0] - c[0] <= 0.5 + _EPS and \
                        abs(c[2] - b[2]) >= 10 and abs(b[2] - a[2]) <= 3 and abs(d[2] - c[2]) <= 3:
                    folds += 1
    acc = {}                                  # (per role over the whole piece: a pattern runs across blocks)
    for p in parts:
        if (p.function in ACC_FN or p.function == 'colour') and p.role not in ('percussion', 'timpani'):
            acc.setdefault(p.role, []).extend(p.notes)
    nbar = int(round(song.length / bpb)) + 1
    for role, ns in acc.items():
        bars = _bars_of(ns, 0.0, nbar * bpb, bpb)
        run, best, prev = 0, 0, None
        for i in range(nbar):
            sg = _bar_sig(bars[i], i * bpb, bpb) if i in bars and len(bars[i]) >= 2 else None
            run = run + 1 if sg is not None and sg == prev else (1 if sg is not None else 0)
            prev = sg
            best = max(best, run)
        omax = max(omax, best)
        o8 += best >= 8
    res['folds'], res['osti_max'], res['osti8'] = folds, omax, o8
    # -- orchestration
    K = Key(tune.key)
    vio = [n for p in parts if p.role in ('violins1', 'violins2') for n in p.notes]
    over = 0
    for p in parts:
        if p.role != 'violas':
            continue
        for a, d, q in p.notes:
            on = [y for x, dd, y in vio if x - _EPS <= a < x + dd - _EPS]
            over += bool(on) and q > max(on)
    res['viola_over'] = over
    res['timp_off'] = 0
    for p in parts:
        if p.role == 'timpani':
            kb = Key(sb[p.block].key).tonic
            tp = {K.tonic % 12, (K.tonic + 7) % 12, kb % 12, (kb + 7) % 12}
            res['timp_off'] += sum(1 for _, _, q in p.notes if q % 12 not in tp or not 38 <= q <= 55)
    res['flute_top'] = sum(1 for p in parts if p.role == 'flutes' for _, _, q in p.notes if q >= 95)
    if getattr(song, 'orch_size', None) == 'chamber' and peak:
        res['chamber_bare'] = int(not any(p.block == peak and p.notes for p in parts
                                          if p.role in ('horns', 'trumpets', 'trombones')))
    flat = 0
    for r in ('horns', 'trumpets', 'trombones'):
        tr = song.tracks.get(r)
        vs = sorted(n.vel for n in tr.notes) if tr is not None else []
        if len(vs) >= 16 and vs[int(0.9 * len(vs))] - vs[int(0.1 * len(vs))] < 12:
            flat += 1
    res['brass_flat'] = flat
    return res


def pair_shares_o4(S: list) -> dict:
    pairs = list(itertools.combinations(S, 2))
    if not pairs:
        return {}

    def cls(x):
        return [c for c, _ in x['row']]

    def core(x):                       # (the macro form: the optional blocks out, dev kinds one, runs collapsed)
        out = []
        for c in cls(x):
            c = 'D' if c == 'F' else c
            if c not in 'SKTZ' and (not out or out[-1] != c):
                out.append(c)
        return out
    return {'same_core': round(sum(1 for a, b in pairs if core(a) == core(b)) / len(pairs), 3),
            'same_row':round(sum(1 for a, b in pairs if cls(a) == cls(b)) / len(pairs), 3),
            'row_sim': round(st.mean(1 - _edit(cls(a), cls(b)) / max(len(cls(a)), len(cls(b))) for a, b in pairs), 3),
            'same_bars': round(sum(1 for a, b in pairs if a['row'] == b['row']) / len(pairs), 3)}


# ------------------------------------------------------------------------------------------------ round o5's tells

THEME_KINDS = ('t1', 't1b', 't2', 't2b', 'recap', 'recap2', 'refrain', 'trio', 'river', 'var', 'episode', 'close')
EDGE_KINDS = ('intro', 'mist', 'source', 'solo', 'slow', 'end', 'end_soft')
ACC_UNDER = ('harmony', 'inner', 'ostinato', 'colour', 'pedal')
HIGH_LEADS = ('violins1', 'flutes', 'oboes', 'clarinets', 'trumpets')
_UNP = ('percussion', 'timpani')


def _sounding(notes, t):
    return [q for a, d, q in notes if a - _EPS <= t < a + d - _EPS]


def measure_o5(sym, tune, song) -> dict:
    """Round o4's judges' tells (songs/_blind/ROUNDS.md "Round o4"): held-note themes and thin middles, figuration off
    the harmony, bare endings, the melody under the accompaniment, the 6/8 family's shared opening / coda, the brass's
    range, chamber climaxes."""
    from agentsound.theory import Key, chord
    mat = tune.symphony
    k = float(mat['scale'])
    U = mat['U']
    bpb = song.beats_per_bar
    parts = [p for p in song.orchestration.parts if p.notes]
    sb = {x.name: x for x in song.orch_score.blocks}
    kinds = {b['name']: b['kind'] for b in mat['blocks']}
    res = {}
    # -- held-note themes: theme bars with at most one melody attack (each block's last bar out)
    held = tot = 0
    for name, x in sb.items():
        if kinds.get(name) not in THEME_KINDS:
            continue
        mel = [n for p in parts if p.block == name and p.function == 'melody' for n in p.notes]
        if not mel:
            continue
        nb = int(round(x.length / bpb))
        for i in range(nb - 1):
            a0 = x.start + i * bpb
            on = {round(a, 3) for a, _, _ in mel if a0 - _EPS <= a < a0 + bpb - _EPS}
            if on or _sounding(mel, a0 + 0.5):
                tot += 1
                held += len(on) <= 1
    res['mel_held'] = round(held / tot, 3) if tot else None
    if tune.feel == 'scherzo':
        res['sch_held'] = res['mel_held']
    # -- thin bars: at most one moving line (non-doubling pitched parts with 2+ attacks), body blocks only
    one = thin = nb_all = 0
    for name, x in sb.items():
        if kinds.get(name) in EDGE_KINDS:
            continue
        ps = [p for p in parts if p.block == name and p.role not in _UNP]
        for i in range(int(round(x.length / bpb))):
            a0 = x.start + i * bpb
            nb_all += 1
            moving = sum(1 for p in ps if p.function != 'doubling' and
                         len({round(a, 3) for a, _, _ in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS}) >= 2)
            roles = {p.role for p in ps if any(a < a0 + bpb - _EPS and a + d > a0 + _EPS for a, d, _ in p.notes)}
            one += moving <= 1
            thin += len(roles) <= 3
    res['one_line'] = round(one / nb_all, 3) if nb_all else None
    res['thin_roles'] = round(thin / nb_all, 3) if nb_all else None
    # -- figuration against the chart: strong-position notes off the chord, beats that circle (range <= 3)
    off = strong = circ = beats = 0
    for p in parts:
        if p.function != 'figuration':
            continue
        x = sb[p.block]
        ch = x.chart
        by = {}
        io = sorted(b_[0] - a_[0] for a_, b_ in zip(sorted(p.notes), sorted(p.notes)[1:]) if b_[0] - a_[0] > _EPS)
        g2 = 2 * (io[len(io) // 2] if io else 0.25)          # (the strong positions: every other note of the grid)
        for a, d, q in p.notes:
            sym = next((s_ for c0, cb, s_ in ch if c0 - _EPS <= a < c0 + cb - _EPS), None)
            r_ = (a - x.start) % g2
            if sym is not None and (r_ < 1e-3 or g2 - r_ < 1e-3):
                c = chord(sym)
                strong += 1
                off += q % 12 not in {(c.root + i) % 12 for i in c.intervals}
            by.setdefault(int((a - x.start + _EPS) // 1.0), []).append(q)
        for qs in by.values():
            if len(qs) >= 3:
                beats += 1
                circ += max(qs) - min(qs) <= 3
    res['fig_off'] = round(off / strong, 3) if strong else None
    res['fig_circ'] = round(circ / beats, 3) if beats else None
    # -- the ending: the last chord's pitch classes, its third, the chord before it (a dominant / subdominant)
    last = mat['blocks'][-1]['name']
    xe = sb[last]
    pitched = [n for p in parts if p.block == last and p.role not in _UNP for n in p.notes]
    if pitched:
        # (the final chord: the last chart row's start - its notes sounding just after; the chord before it)
        tl = sorted(getattr(song, 'endless_timeline', []))
        rows = [r_ for r_ in tl if r_[0] < xe.end - _EPS]
        tf = rows[-1][0] if rows and rows[-1][0] >= xe.start - _EPS else xe.start
        fin = [q for p in parts if p.role not in _UNP for q in _sounding(p.notes, tf + 0.1)]
        pcs = {q % 12 for q in fin}
        res['end_pcs'] = len(pcs)
        K = Key(xe.key)
        third = {(K.tonic + 3) % 12, (K.tonic + 4) % 12}
        res['end_third'] = round(sum(1 for q in fin if q % 12 in third) / max(1, len(fin)), 3)
        res['end_bare'] = int(len(pcs) < 3 or not pcs & third)
        prev = next((r_[2] for r_ in reversed(rows) if r_[0] < tf - _EPS), None)     # (the chord right before)
        r = chord(prev).root % 12 if prev else None
        res['end_cad'] = int(r is not None and r in ((K.tonic + 7) % 12, (K.tonic + 5) % 12, (K.tonic + 11) % 12))
        res['end_sig'] = [kinds[last], len(pcs), res['end_cad'], sb[last].texture]
    # -- the melody under the accompaniment (a high lead), the harp over the melody
    under = mtot = hover = htot = 0
    for name, x in sb.items():
        mel = [(p.role, n) for p in parts if p.block == name and p.function == 'melody' for n in p.notes]
        acc = [n for p in parts if p.block == name and p.function in ACC_UNDER and p.role not in _UNP for n in p.notes]
        harp = [n for p in parts if p.block == name and p.role == 'harp' for n in p.notes]
        mn = [n for _, n in mel]
        for role, (a, d, q) in mel:
            if role not in HIGH_LEADS:
                continue
            s_ = _sounding(acc, a + 0.05)
            if s_:
                mtot += 1
                under += q < max(s_)
        for a, d, q in harp:
            s_ = _sounding(mn, a + 0.05)
            if s_:
                htot += 1
                hover += q > max(s_)
    res['mel_under'] = round(under / mtot, 3) if mtot else None
    res['harp_over'] = round(hover / htot, 3) if htot else None
    peak = next((x for x in sb.values() if x.peak), None)
    if peak is not None:
        res['clx_counter'] = int(any(p.block == peak.name and p.function in ('counter', 'voice') for p in parts))
    # -- the opening and the coda (the 6/8 family's shared plan): signatures for the pair shares
    first = mat['blocks'][0]
    fm = [a for p in parts if p.block == first['name'] and p.function in ('melody', 'bass') and
          not (first['kind'] == 'source' and p.function == 'bass') for a, _, _ in p.notes]
    res['open_plan'] = [first['kind'], int(round(first['bars'] * U * k / bpb)),
                        int((min(fm) - sb[first['name']].start) // bpb) if fm else -1]
    coda = next((b for b in mat['blocks'] if b['kind'] in ('coda', 'coda_soft')), None)
    if coda is not None:
        res['coda_plan'] = [coda['kind'], coda.get('plan'), sb[coda['name']].texture,
                            (Key(peak.key).tonic - Key(tune.key).tonic) % 12 if peak is not None else None]
    res['compound'] = int(mat['family'] == 'compound')
    # -- the brass's range: trumpets carrying a tune under G4, trombones over Bb4
    res['tpt_low'] = sum(1 for p in parts if p.role == 'trumpets' and
                         (p.function == 'melody' or (p.function == 'doubling' and p.voice == 'melody'))
                         for _, _, q in p.notes if q < 67)
    res['tbn_high'] = sum(1 for p in parts if p.role == 'trombones' for _, _, q in p.notes if q > 70)
    res['chamber'] = int(getattr(song, 'orch_size', None) == 'chamber')
    if res['chamber'] and peak is not None:
        res['chamber_horns'] = int(any(p.block == peak.name and p.role == 'horns' for p in parts))
    return res


def pair_shares_o5(S: list) -> dict:
    cp = [x for x in S if x.get('compound')]
    out = {}
    for key, pool in (('same_open68', cp), ('same_coda68', cp), ('same_end', S)):
        f = {'same_open68': 'open_plan', 'same_coda68': 'coda_plan', 'same_end': 'end_sig'}[key]
        pairs = list(itertools.combinations(pool, 2))
        if pairs:
            out[key] = round(sum(1 for a, b in pairs if a.get(f) is not None and a.get(f) == b.get(f)) / len(pairs), 3)
    return out


# ------------------------------------------------------------------------------------------------ round o6's tells

WIN = 4
"""The material windows (round o6): 4 notes in a row of one line - 3 intervals, 2 IOI ratios (any speed: an
augmentation matches) and whether the last note is held (1.5 x the longest IOI); a window whose IOIs are all equal
without a held last note (an ostinato, a stream of 16ths, a hymn of quarters) or whose notes are one pitch is no
material.
INDEPENDENT of the generator (the code review's 5.5 / G2, songs/_endless_orchestra/out/code_review/REPORT.md: this
file duplicated symphony.own_stats' windows and its +-1 semitone match, so it shared the score's blind spots): a scale
run (every interval a step, one way - symphony's run_to fills) is no material either, and two windows match on the
same GENERIC intervals (GENERIC: unison, step, third, fourth, fifth, sixth, seventh, octave - a tonal transposition or
the inversion), the IOI ratios within RATIO_TOL; the material is the rendered piece's lines only (no
symphony.motto_notes cell)."""
GENERIC = ((0, 0), (1, 2), (3, 4), (5, 6), (7, 7), (8, 9), (10, 11), (12, 12))
"""The generic interval (index) of a size in semitones: (lowest, highest) per class; a tritone counts as a fourth."""
RATIO_TOL = 0.03
WOODS = ('flutes', 'oboes', 'clarinets', 'bassoons')
REFS = {'stormy': {'motto': ('motto', 'A'), 'expo': ('motto', 'A', 'trans', 'B', 'closing'),
                   'dev': ('fugato', 'seq', 'storm'), 'climax': ('recap',)},
        'river': {'motto': ('source', 'stream', 'theme'), 'expo': ('source', 'stream', 'theme', 'bridge'),
                  'dev': ('hunt', 'storm'), 'climax': ('river',)},
        'scherzo': {'motto': ('intro', 'A1'), 'expo': ('intro', 'A1', 'A1b'), 'dev': ('dev',), 'climax': ('R3',)}}
"""The hand-written references' sections for the material tells (--refs): the motto / first theme, the whole
exposition, the development / episodes, the climax."""


def top_line(notes) -> list:
    """One line: the highest note per onset, sorted."""
    by = {}
    for a, d, q in notes:
        k = round(a, 3)
        if k not in by or q > by[k][2]:
            by[k] = (a, d, q)
    return [by[k] for k in sorted(by)]


def generic(semis: int) -> int:
    """The signed generic interval of a size in semitones (GENERIC: 0 unison, +-1 a step ... +-7 an octave; compound
    intervals 7 more per octave)."""
    a = abs(semis)
    g = 7 * (a // 12) + next(i for i, (lo, hi) in enumerate(GENERIC) if lo <= a % 12 <= hi)
    return g if semis >= 0 else -g


def windows(line) -> list:
    """[(onset, ratios, generic intervals)] of a line's material windows (WIN; no scale runs)."""
    out = []
    for i in range(len(line) - WIN + 1):
        w = line[i:i + WIN]
        io = _iois(w)
        long_ = int(w[-1][1] >= 1.5 * max(io))       # (a landing held: the hammer motto's 8ths into a half note)
        if min(io) <= _EPS or max(io) > 6.0 or (max(io) - min(io) < 1e-3 and not long_):
            continue
        iv = tuple(b[2] - a[2] for a, b in zip(w, w[1:]))
        if not any(iv) or max(abs(x) for x in iv) > 12:
            continue
        gv = tuple(generic(x) for x in iv)
        if all(abs(x) == 1 for x in gv) and len({_sign(x) for x in gv}) == 1:
            continue                                 # (a scale run: no material - G2 / G6)
        out.append((w[0][0], tuple(round(x / io[0], 3) for x in io[1:]) + (long_,), gv))
    return out


def _wmatch(w, mats) -> bool:
    """A window states the material: the same held-landing flag, IOI ratios within RATIO_TOL, the same generic
    intervals or all of them inverted."""
    _, r, gv = w
    inv = tuple(-x for x in gv)
    for _, r2, gv2 in mats:
        if (gv2 == gv or gv2 == inv) and r[-1] == r2[-1] and \
                all(abs(a - b) <= RATIO_TOL * max(1.0, b) for a, b in zip(r[:-1], r2[:-1])):
            return True
    return False


def own_share(target_lines, mats) -> float | None:
    """The share of the target lines' windows that state the material (mats: windows; inverted counts)."""
    ws = [w for ln in target_lines for w in windows(ln)]
    return round(sum(1 for w in ws if _wmatch(w, mats)) / len(ws), 3) if ws else None


def own_bars(lines_by_bar, mats) -> float | None:
    """The share of bars (keys) whose lines hold a window that states the material."""
    if not lines_by_bar:
        return None
    hit = sum(1 for ws in lines_by_bar.values() if any(_wmatch(w, mats) for w in ws))
    return round(hit / len(lines_by_bar), 3)


def _role_lines(parts, names, fns=None) -> dict:
    """{role: top line} of the non-doubling pitched parts in the blocks `names` (fns: those functions only)."""
    out = {}
    for p in parts:
        if p.block in names and p.notes and p.role not in _UNP + ('harp',) and p.function != 'doubling' and \
                (fns is None or p.function in fns):
            out.setdefault(p.role, []).extend(p.notes)
    return {r: top_line(ns) for r, ns in out.items()}


def _bar_windows(lines: dict, spans, bpb) -> dict:
    """{(span index, bar): [windows starting in that bar]} over the role lines, every bar of the spans a key."""
    out = {}
    for j, (a0, z) in enumerate(spans):
        for i in range(int(round((z - a0) / bpb))):
            out[(j, i)] = []
    for ln in lines.values():
        for w in windows(ln):
            for j, (a0, z) in enumerate(spans):
                if a0 - _EPS <= w[0] < z - _EPS:
                    out.setdefault((j, int((w[0] - a0 + _EPS) // bpb)), []).append(w)
    return out


DEV_KINDS = ('dev_dialogue', 'dev_fugato', 'episode', 'var')


def measure_o6(sym, tune, song) -> dict:
    """Round o5's judges' tells (songs/_blind/ROUNDS.md "Round o5"): the climax's material (clx_motto: its melody's
    windows that state the motto / the first theme; clx_own: the motto or either theme), the development's and the
    episodes' (dev_own: the share of their bars with a window of the exposition's material - dev / episode / var
    blocks, a rondo's trio), the scherzo's tune on top (buried: theme bars where a busier part moves above the line
    that carries the theme), the wind accompaniment's repeated notes (rep_wind: the longest run of bars of a woodwind
    part with half its attacks repeated notes, 4+ attacks; rep8 the parts with a run of 8+), unison filler (unison:
    body bars where 5+ roles move in one pitch-class line), and the plan a set shares (clx_turn: the climax's key
    against the home - same / parallel / relative / other -, clx_harp: harp arpeggios at the climax, end_roll: a
    timpani roll of 8+ beats in the last two blocks, coda: its kind)."""
    from agentsound.theory import Key
    mat = tune.symphony
    bpb = song.beats_per_bar
    parts = [p for p in song.orchestration.parts if p.notes]
    sb = {x.name: x for x in song.orch_score.blocks}
    blocks = mat['blocks']
    kinds = {b['name']: b['kind'] for b in blocks}
    res = {}
    first_dev = next((i for i, b in enumerate(blocks) if b['kind'].startswith('dev') or b['kind'] == 'var'),
                     len(blocks))
    expo = {b['name'] for b in blocks[:first_dev]}
    motto_names = {b['name'] for b in blocks[:first_dev] if b['kind'] in ('intro', 'mist', 'solo', 'slow', 'source',
                                                                         't1', 't1b', 'river')}
    cell = []                  # (the material: the rendered lines only - WIN)
    m_motto = cell + [w for ln in _role_lines(parts, motto_names, ('melody', 'bass', 'voice')).values()
                      for w in windows(ln)]
    m_all = m_motto + [w for ln in _role_lines(parts, expo, ('melody', 'bass', 'voice', 'counter')).values()
                       for w in windows(ln)]
    peak = next((x for x in song.orch_score.blocks if x.peak), None)
    if peak is not None:
        mel = [top_line([n for p in parts if p.block == peak.name and p.function == 'melody' for n in p.notes])]
        res['clx_motto'] = own_share(mel, m_motto)
        res['clx_own'] = own_share(mel, m_all)
        res['clx_motto_roles'] = own_share(list(_role_lines(parts, {peak.name}).values()), m_motto)
    rondo = mat['layout'] == 'rondo'
    tgt = [b['name'] for b in blocks if b['kind'] in DEV_KINDS or (rondo and b['kind'] == 'trio')]
    if tgt:
        spans = [(sb[n].start, sb[n].end) for n in tgt]
        lines = _role_lines(parts, set(tgt), ('melody', 'counter', 'voice', 'bass'))
        res['dev_own'] = own_bars(_bar_windows(lines, spans, bpb), m_all)
        res['dev_mot'] = own_bars(_bar_windows(lines, spans, bpb), m_motto)
    # -- the theme on top: theme bars where a busier part moves above the theme's line
    bur = tot = 0
    for name, x in sb.items():
        if kinds.get(name) not in THEME_KINDS:
            continue
        fn = 'bass' if orc_theme(x.texture) == 'bass' else 'melody'
        th = [n for p in parts if p.block == name and p.function == fn for n in p.notes]
        if not th:
            continue
        others = [p for p in parts if p.block == name and p.function not in (fn, 'doubling') and
                  p.role not in _UNP]
        for i in range(int(round(x.length / bpb)) - 1):
            a0 = x.start + i * bpb
            on = [q for a, _, q in th if a0 - _EPS <= a < a0 + bpb - _EPS]
            if not on:
                continue
            tot += 1
            for p in others:
                qs = [q for a, _, q in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS]
                if len(qs) >= max(2, len(on)) and sum(qs) / len(qs) > max(on):
                    bur += 1
                    break
    res['buried'] = round(bur / tot, 3) if tot else None
    if tune.feel == 'scherzo':
        res['sch_buried'] = res['buried']
    # -- repeated-note wind accompaniment, unison filler
    best, r8 = 0, 0
    for role in WOODS:
        ns = top_line([n for p in parts if p.role == role and p.function in ACC_FN + ('figuration',)
                       for n in p.notes])
        if not ns:
            continue
        bars = _bars_of(ns, 0.0, song.length + bpb, bpb)
        run = top = 0
        for i in range(int(song.length // bpb) + 2):
            qs = [q for _, _, q in sorted(bars.get(i, []))]
            rep = sum(1 for a, b in zip(qs, qs[1:]) if a == b) / max(1, len(qs) - 1)
            run = run + 1 if len(qs) >= 4 and rep >= 0.5 else 0
            top = max(top, run)
        best = max(best, top)
        r8 += top >= 8
    res['rep_wind'], res['rep8'] = best, r8
    uni = 0
    for name, x in sb.items():
        if kinds.get(name) in EDGE_KINDS:
            continue
        ps = [p for p in parts if p.block == name and p.role not in _UNP + ('harp',)]
        for i in range(int(round(x.length / bpb))):
            a0 = x.start + i * bpb
            by, roles = {}, set()
            for p in ps:
                for a, _, q in p.notes:
                    if a0 - _EPS <= a < a0 + bpb - _EPS:
                        by.setdefault(round(a, 2), set()).add(q % 12)
                        roles.add(p.role)
            if len(roles) >= 5 and len(by) >= 3 and all(len(v) == 1 for v in by.values()):
                uni += 1
    res['unison'] = uni
    # -- the plan a set shares
    K = Key(tune.key)
    if peak is not None:
        P = Key(peak.key)
        d = (P.tonic - K.tonic) % 12
        res['clx_turn'] = 'same' if d == 0 and P.minorish == K.minorish else 'parallel' if d == 0 else \
            'relative' if (P.minorish != K.minorish and d == (3 if K.minorish else 9)) else 'other'
        res['clx_major'] = int(K.minorish and not P.minorish) if K.minorish else None
        res['clx_harp'] = int(any(p.block == peak.name and p.role == 'harp' and len(p.notes) >= 8 for p in parts))
    tail = [b['name'] for b in blocks[-2:]]
    res['end_roll'] = int(any(p.block in tail and p.role == 'timpani' and any(d_ >= 8 for _, d_, _ in p.notes)
                              for p in parts))
    coda = next((b['kind'] for b in blocks if b['kind'] in ('coda', 'coda_soft')), None)
    res['coda_soft'] = int(coda == 'coda_soft') if coda else None
    res['plan_sig'] = [int(K.minorish), res.get('clx_turn'), res.get('clx_harp'), coda, res['end_roll']]
    return res


def orc_theme(texture: str):
    from agentsound.bandlib import orchestration as orc
    return orc.TEXTURES.get(texture, {}).get('theme', 'melody')


def pair_shares_o6(S: list) -> dict:
    pairs = list(itertools.combinations(S, 2))
    if not pairs:
        return {}
    return {'same_plan': round(sum(1 for a, b in pairs if a.get('plan_sig') == b.get('plan_sig')) / len(pairs), 3),
            'same_turn': round(sum(1 for a, b in pairs if a.get('clx_turn') == b.get('clx_turn') and
                                   a['plan_sig'][0] == b['plan_sig'][0]) / len(pairs), 3)}


# ------------------------------------------------------------------------------------------------ round o7's tells

END_ORDER = (('clarinets', 'bassoons'), ('horns', 'trombones'), ('trombones', 'tuba'), ('violins2', 'violas'),
             ('violas', 'cellos'), ('oboes', 'bassoons'), ('clarinets', 'trombones'))
"""The final chord's role pairs (upper, lower) in score order: the lower's top over the upper's top is an inverted
voicing (o6's orchestrators: "the bassoon an octave over the clarinet, the trombones on top")."""
END_TOP = ('violins1', 'flutes', 'oboes', 'trumpets', 'violins2')


def measure_o7(sym, tune, song) -> dict:
    """Round o6's judges' tells (songs/_blind/ROUNDS.md "Round o6"): the scherzo's tune in whole-bar notes (sch_whole:
    the share of a scherzo's theme / climax / coda melody notes held a 3/4 bar or more), the final cadence (end_top: the
    final chord's top in a high tune role; end_inv: inverted role pairs in it; end_vbass: the chord before it has its
    bass note in the lowest part; end_rows: the last block's chords - 2 = a held V - I; end_held: the last block's only
    attacks are its chords), the climax stacked in octaves (clx_mroles / clx_moct: the roles / distinct octaves on the
    melody per peak bar, mean; clx_moct_max), static inner strings (inner_static: violins II / violas body bars of 4+
    attacks on one pitch), near-empty bars (empty: body bars with 2 or fewer pitched roles sounding), the stock build
    (stock_n: of a cymbal roll in the pre-climax block, a crash in the climax's first bar, the choir at the build / the
    climax; stock3 all three) and the ending's plan a set shares (end7_sig: the last block's kind, chords, texture,
    strokes)."""
    from agentsound.bandlib import orchestra as orch
    from agentsound.theory import chord
    mat = tune.symphony
    bpb = song.beats_per_bar
    parts = [p for p in song.orchestration.parts if p.notes]
    sbl = song.orch_score.blocks
    sb = {x.name: x for x in sbl}
    blocks = mat['blocks']
    kinds = {b['name']: b['kind'] for b in blocks}
    res = {}
    # -- the scherzo's tune in whole-bar notes
    if mat['scale'] == 2:
        mel = [n for p in parts if p.function == 'melody' and kinds.get(p.block) in
               ('t1', 't1b', 'recap', 'refrain', 'close', 'coda') for n in p.notes]
        res['sch_whole'] = round(sum(1 for _, d, _ in mel if d >= bpb - 0.01) / len(mel), 3) if mel else None
    # -- the final cadence
    last = blocks[-1]
    xe = sb[last['name']]
    rows = sorted(xe.chart)
    res['end_rows'] = len(rows)
    tf = rows[-1][0] if rows else xe.start
    fin = [(p.role, q) for p in parts if p.role not in _UNP + ('harp', 'choir') for q in _sounding(p.notes, tf + 0.1)]
    if fin:
        top = max(q for _, q in fin)
        res['end_top'] = int(any(r in END_TOP for r, q in fin if q == top))
        tops = {}
        for r, q in fin:
            tops[r] = max(tops.get(r, 0), q)
        res['end_inv'] = sum(1 for a, b in END_ORDER if a in tops and b in tops and tops[b] > tops[a])
    if len(rows) >= 2:
        a5 = rows[-2][0]
        snd = [q for p in parts if p.role not in _UNP + ('harp', 'choir') for q in _sounding(p.notes, a5 + 0.1)]
        sym_ = rows[-2][2]
        bass_pc = chord(sym_.split('/')[1]).root % 12 if '/' in sym_ else chord(sym_).root % 12
        res['end_vbass'] = int(bool(snd) and min(snd) % 12 == bass_pc)
    att = sorted({round(a, 2) for p in parts if p.block == last['name'] and p.role not in _UNP for a, _, _ in p.notes})
    res['end_held'] = int(len(att) <= len(rows))
    res['end7_sig'] = [last['kind'], len(rows), xe.texture, int(bool(last.get('strokes')))]
    # -- the climax stacked in octaves
    peak = next((x for x in sbl if x.peak), None)
    if peak is not None:
        mp = [p for p in parts if p.block == peak.name and p.function == 'melody']
        dp = [p for p in parts if p.block == peak.name and p.function == 'doubling' and p.voice == 'melody']
        rl, ol = [], []
        for i in range(int(round(peak.length / bpb))):
            a0 = peak.start + i * bpb
            mq = [q for p in mp for a, _, q in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS]
            if not mq:
                continue
            ref = min(mq)
            on = {}
            for p in mp + dp:
                for a, _, q in p.notes:
                    if a0 - _EPS <= a < a0 + bpb - _EPS:
                        on.setdefault(p.role, []).append(q)
            rl.append(len(on))
            ol.append(len({round((min(qs) - ref) / 12) for qs in on.values()}))
        if rl:
            res['clx_mroles'] = round(st.mean(rl), 2)
            res['clx_moct'] = round(st.mean(ol), 2)
            res['clx_moct_max'] = max(ol)
    # -- the roles on the tune's line (any function: a bass on the melody, a doubling), the climax and the coda
    for key_, names in (('clx_follow', [peak.name] if peak is not None else []),
                        ('coda_follow', [b['name'] for b in blocks if b['kind'] in ('coda', 'coda_soft', 'end')])):
        fl, fo = [], []
        for name in names:
            x = sb[name]
            mel = top_line([n for p in parts if p.block == name and p.function == 'melody' for n in p.notes])
            others = {}
            for p in parts:
                if p.block == name and p.role not in _UNP + ('harp',):
                    others.setdefault(p.role, []).extend(p.notes)
            for i in range(int(round(x.length / bpb))):
                a0 = x.start + i * bpb
                on = [(a, q) for a, _, q in mel if a0 - _EPS <= a < a0 + bpb - _EPS]
                if len(on) < 2:
                    continue
                ref = min(q for _, q in on)
                n_, octs = 0, set()
                for role, ns in others.items():
                    hit = [r_ for a, q in on for b_, _, r_ in ns if abs(b_ - a) < 0.05 and r_ % 12 == q % 12]
                    if len(hit) >= 0.75 * len(on):
                        n_ += 1
                        octs.add(round((min(hit) - ref) / 12))
                fl.append(n_)
                fo.append(len(octs))
        if fl:
            res[key_] = round(st.mean(fl), 2)
            res[key_ + '_oct'] = round(st.mean(fo), 2)
    # -- static inner strings, near-empty bars
    stat = tot = emp = nb = 0
    for name, x in sb.items():
        if kinds.get(name) in EDGE_KINDS:
            continue
        ps = [p for p in parts if p.block == name]
        for i in range(int(round(x.length / bpb))):
            a0 = x.start + i * bpb
            for role in ('violins2', 'violas'):
                qs = [q for p in ps if p.role == role for a, _, q in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS]
                if len(qs) >= 4:
                    tot += 1
                    stat += len(set(qs)) == 1
            nb += 1
            snd = {p.role for p in ps if p.role not in _UNP and
                   any(a < a0 + bpb - _EPS and a + d > a0 + _EPS for a, d, _ in p.notes)}
            emp += len(snd) <= 2
    res['inner_static'] = round(stat / tot, 3) if tot else None
    res['empty'] = round(emp / nb, 3) if nb else None
    # -- the stock build
    if peak is not None:
        names = [x.name for x in sbl]
        pre = sbl[names.index(peak.name) - 1] if names.index(peak.name) > 0 else None
        K = orch.PERCUSSION_KEYS
        cym = pre is not None and any(p.role == 'percussion' and p.block == pre.name and
                                      any(q == K.get('cymbal_roll') for _, _, q in p.notes) for p in parts)
        crash = any(p.role == 'percussion' and p.block == peak.name and
                    any(q == K.get('crash') and a < peak.start + bpb for a, _, q in p.notes) for p in parts)
        choir = any(p.role == 'choir' and (p.block == peak.name or (pre is not None and p.block == pre.name))
                    for p in parts)
        res['stock_n'] = int(cym) + int(crash) + int(choir)
        res['stock3'] = int(cym and crash and choir)
    return res


def pair_shares_o7(S: list) -> dict:
    pairs = list(itertools.combinations(S, 2))
    if not pairs:
        return {}
    return {'same_end7': round(sum(1 for a, b in pairs if a.get('end7_sig') == b.get('end7_sig')) / len(pairs), 3)}


# ------------------------------------------------------------------------------------------------ round o8's tells

BRASS = ('trumpets', 'horns', 'trombones', 'tuba')
FIRST_THEME = ('t1', 'refrain', 'river')
LOW_BASS = ('basses', 'tuba', 'cellos', 'bassoons')
SOFT = ('pp', 'p', 'mp')


def _scale_pcs(key: str) -> set:
    """The key's scale with the raised 7th of a minor / modal key (the leading tone is diatonic voice-leading)."""
    from agentsound.theory import Key
    K = Key(key)
    pcs = set(K.pcs)
    if K.minorish:
        pcs.add((K.tonic + 11) % 12)
    return pcs


O8 = ('dev_far', 'dev_off', 'clx_brass', 'coda_mot', 'th_step', 'th_lrng', 'th_rhy', 'th_buried', 'sch_lit', 'sch_cell',
      'solo_held', 'prop_build', 'prop_peak', 'ff_soft', 'end_low', 'end_oct', 'end_rep')


def measure_o8(sym, tune, song) -> dict:
    """Round o7's judges' tells (songs/_blind/ROUNDS.md "Round o7"): the development's keys and material (dev_far: the
    share of the development / episode blocks' chart beats whose chord root is outside the home key's scale; dev_off:
    their melodic notes outside the home scale and the sounding chord), the motto at the climax in the brass and in the
    coda (clx_brass: a brass part at the peak states a motto window; coda_mot: the coda's melody / counter does), the
    first theme as a singable line (th_step: its stepwise share, th_lrng: the pitch range of its notes of a beat+,
    th_rhy: its distinct durations, th_buried: its bars with a busier part above the theme's line), the scherzo's
    literal restatements (sch_lit: melody bar-pairs that copy the dance's first two bars' rhythm and intervals; sch_cell:
    the melody bars in its first bar's rhythm) and
    held-string solos (solo_held: the longest run of song bars where one melodic role sounds over parts with at most
    one attack per bar - a tremolo moves), the proportions (prop_build / prop_peak: the build's and the climax's share of the bars;
    ff_soft: the dissolving coda after the peak starts soft - no transition), the final chord's bass (end_low: its
    lowest note; end_oct: the lowest is the tonic, another bass role an octave over it; end_rep: repeated attacks of the tuba / basses in the last
    block's final chord)."""
    from agentsound.theory import Key, chord
    mat = tune.symphony
    bpb = song.beats_per_bar
    parts = [p for p in song.orchestration.parts if p.notes]
    sbl = song.orch_score.blocks
    sb = {x.name: x for x in sbl}
    blocks = mat['blocks']
    kinds = {b['name']: b['kind'] for b in blocks}
    res = {}
    home = _scale_pcs(tune.key)
    # -- the development's keys and material
    dev = [b['name'] for b in blocks if b['kind'] in DEV_KINDS]
    far = tot = 0.0
    off = nn = 0
    for name in dev:
        x = sb[name]
        for a, d, s_ in x.chart:
            r = chord(s_.split('/')[0]).root % 12
            tot += d
            far += d * (r not in home)
        for p in parts:
            if p.block != name or p.function not in ('melody', 'counter', 'voice') or p.role in _UNP + ('harp',):
                continue
            for a, d, q in p.notes:
                sym_ = next((s_ for c0, cd, s_ in x.chart if c0 - _EPS <= a < c0 + cd - _EPS), None)
                cs = set()
                if sym_:
                    c = chord(sym_.split('/')[0])
                    cs = {(c.root + i) % 12 for i in c.intervals}
                nn += 1
                off += q % 12 not in home | cs
    res['dev_far'] = round(far / tot, 3) if tot else None
    res['dev_off'] = round(off / nn, 3) if nn else None
    # -- the motto at the climax (in the brass) and in the coda
    first_dev = next((i for i, b in enumerate(blocks) if b['kind'].startswith('dev') or b['kind'] == 'var'),
                     len(blocks))
    motto_names = {b['name'] for b in blocks[:first_dev] if b['kind'] in ('intro', 'mist', 'solo', 'slow', 'source',
                                                                         't1', 't1b', 'river')}
    cell = []                  # (the material: the rendered lines only - WIN)
    m_motto = cell + [w for ln in _role_lines(parts, motto_names, ('melody', 'bass', 'voice')).values()
                      for w in windows(ln)]
    peak = next((x for x in sbl if x.peak), None)
    if peak is not None:
        br = {r: ln for r, ln in _role_lines(parts, {peak.name}).items() if r in BRASS}
        dbl = [top_line(p.notes) for p in parts if p.block == peak.name and p.role in BRASS and
               p.function == 'doubling']
        res['clx_brass'] = int(any(_wmatch(w, m_motto) for ln in list(br.values()) + dbl for w in windows(ln)))
    coda = [b['name'] for b in blocks if b['kind'] in ('coda', 'coda_soft')]
    if coda:
        ls = [top_line(p.notes) for p in parts if p.block in coda and p.function in ('melody', 'counter', 'doubling')
              and p.role not in _UNP + ('harp',)]
        res['coda_mot'] = int(any(_wmatch(w, m_motto) for ln in ls for w in windows(ln)))
    # -- the first theme's profile
    stp, lr, rhy, bur, btot = [], [], [], 0, 0
    for name in [b['name'] for b in blocks if b['kind'] in FIRST_THEME]:
        x = sb[name]
        fn = 'bass' if orc_theme(x.texture) == 'bass' else 'melody'
        th = top_line([n for p in parts if p.block == name and p.function == fn for n in p.notes])
        if len(th) < 4:
            continue
        iv = [abs(b_[2] - a_[2]) for a_, b_ in zip(th, th[1:])]
        stp.append(sum(1 for v in iv if v <= 2) / len(iv))
        lg = [q for _, d, q in th if d >= 1.0 - _EPS]
        lr.append(max(lg) - min(lg) if len(lg) >= 2 else 0)
        rhy.append(len({round(d, 2) for _, d, _ in th}))
        others = [p for p in parts if p.block == name and p.function not in (fn, 'doubling') and p.role not in _UNP]
        for i in range(int(round(x.length / bpb))):
            a0 = x.start + i * bpb
            on = [q for a, _, q in th if a0 - _EPS <= a < a0 + bpb - _EPS]
            if not on:
                continue
            btot += 1
            for p in others:
                qs = [q for a, _, q in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS]
                if len(qs) >= max(4, len(on) + 1) and sum(qs) / len(qs) > max(on):
                    bur += 1
                    break
    if stp:
        res['th_step'] = round(st.mean(stp), 3)
        res['th_lrng'] = round(st.mean(lr), 2)
        res['th_rhy'] = round(st.mean(rhy), 2)
    res['th_buried'] = round(bur / btot, 3) if btot else None
    # -- the scherzo's literal restatements, held-string solos
    if mat['scale'] == 2:
        t1 = next((b['name'] for b in blocks if b['kind'] == 't1'), None)
        if t1:
            x = sb[t1]
            mel = top_line([n for p in parts if p.block == t1 and p.function == 'melody' for n in p.notes])
            ref = [(a - x.start, q) for a, _, q in mel if a < x.start + 2 * bpb - _EPS]

            def sig(ns):
                return (tuple(round(a - ns[0][0], 2) for a, _ in ns), tuple(b_[1] - a_[1] for a_, b_ in zip(ns, ns[1:])))
            if len(ref) >= 3:
                rs = sig(ref)
                lit = 0
                allm = top_line([n for p in parts if p.function == 'melody' for n in p.notes])
                for i in range(int(round(song.length / bpb)) - 1):
                    a0 = i * bpb
                    ns = [(a - a0, q) for a, _, q in allm if a0 - _EPS <= a < a0 + 2 * bpb - _EPS]
                    if len(ns) == len(ref) and sig(ns) == rs:
                        lit += 1
                res['sch_lit'] = lit
                r1 = tuple(round(a, 2) for a, _ in ref if a < bpb - _EPS)
                hit = tot_ = 0
                for i in range(int(round(song.length / bpb))):
                    a0 = i * bpb
                    on = tuple(round(a - a0, 2) for a, _, _ in allm if a0 - _EPS <= a < a0 + bpb - _EPS)
                    if len(on) >= 2:
                        tot_ += 1
                        hit += on == r1
                res['sch_cell'] = round(hit / tot_, 3) if tot_ else None
    run = best = 0
    nbar = int(round(song.length / bpb))
    for i in range(nbar):
        a0 = i * bpb
        mel_roles = {p.role for p in parts if p.function in ('melody', 'counter') and p.role not in _UNP and
                     any(a0 - _EPS <= a < a0 + bpb - _EPS for a, _, _ in p.notes)}
        acc = [p for p in parts if p.function not in ('melody', 'counter', 'doubling') and p.role not in _UNP + ('harp',)
               and any(a < a0 + bpb - _EPS and a + d > a0 + _EPS for a, d, _ in p.notes)]
        held = bool(acc) and all(p.art != 'tremolo' and
                                 sum(1 for a, _, _ in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS) <= 1 for p in acc)
        run = run + 1 if len(mel_roles) == 1 and held else 0
        best = max(best, run)
    res['solo_held'] = best
    # -- the proportions
    total = sum(x.length for x in sbl)
    pre = None
    if peak is not None:
        names = [x.name for x in sbl]
        i = names.index(peak.name)
        pre = sbl[i - 1] if i > 0 else None
        res['prop_peak'] = round(peak.length / total, 3)
        if pre is not None and kinds.get(pre.name) == 'retrans':
            res['prop_build'] = round(pre.length / total, 3)
        nxt = sbl[i + 1] if i + 1 < len(sbl) else None
        if nxt is not None and kinds.get(nxt.name) in ('coda_soft', 'end_soft'):
            m0 = sorted(nxt.marks)[0][1] if nxt.marks else 'mf'
            res['ff_soft'] = int(m0 in SOFT)
    # -- the final chord's bass
    last = sbl[-1]
    tf = sorted(last.chart)[-1][0] if last.chart else last.start
    low = {}
    for p in parts:
        if p.block == last.name and p.role in LOW_BASS:
            qs = _sounding(p.notes, tf + 0.1)
            if qs:
                low[p.role] = min(qs)
    if low:
        v = sorted(set(low.values()))
        res['end_low'] = v[0]
        res['end_oct'] = int(v[0] % 12 == Key(tune.key).tonic % 12 and v[0] + 12 in v)
    res['end_rep'] = sum(max(0, sum(1 for a, _, _ in p.notes if a >= tf - _EPS) - 1) for p in parts
                         if p.block == last.name and p.role in ('tuba', 'basses'))
    return res


# ------------------------------------------------------------------------------------------------ round o9's tells

O9 = ('clx_theme', 'clx_fig', 'fig_chorale', 'coda_fig', 'lit_max', 'lit_n', 'epi_own', 'static_run', 'rt_lead',
      'post_roles', 'post_light', 'end_pre', 'end_vbeats', 'choir_late')


def _runs_in(p, a0, a1, bpb) -> bool:
    """A part runs in [a0, a1): two or more onsets per beat on average (16ths / fast broken chords)."""
    n = sum(1 for a, _, _ in p.notes if a0 - _EPS <= a < a1 - _EPS)
    return n >= 2 * (a1 - a0) - _EPS and n >= 4


def measure_o9(sym, tune, song) -> dict:
    """Round o8's judges' tells (songs/_blind/ROUNDS.md "Round o8"): the climax / coda as 16ths over a brass chorale with
    the theme absent (clx_theme: the peak's bars where a melody / counter / doubling line states the motto or the first
    theme; clx_fig: the peak's bars with a running figuration part, coda_fig the coda's; fig_chorale 1: the peak or the
    coda runs figuration in half its bars or more while a brass role holds the melody - per set same_clx_tex: pairs with
    the same peak texture), literal restatements (lit_max: the most consecutive literal copies of a 1- / 2-bar unit of the
    melody's top line, lit_n their count), episodes from the theme (epi_own: the episode / trio / variation bars whose
    lines state the motto or the first theme), static stretches (static_run: the longest run of song bars without a
    counter-line and with every accompaniment part held or a literal copy of its bar before; rt_lead: the retransition's
    last bar has 2+ onsets in its melody / bass line - the motto's head as a lead-in, not one held note), the post-climax sag (post_roles: sounding roles per bar in
    the block after the peak over the piece's mean; post_light 1: that block's texture is 'light' or its first bar has 4
    or fewer pitched roles), the endings (end_pre 1: a predominant before the last block's dominant; end_vbeats: the
    dominant's beats before the final tonic) and the choir (choir_late 1: it sounds only in the last quarter)."""
    from agentsound.bandlib import orchestration as orc
    from agentsound.theory import chord, Key
    mat = tune.symphony
    bpb = song.beats_per_bar
    parts = [p for p in song.orchestration.parts if p.notes]
    sbl = song.orch_score.blocks
    blocks = mat['blocks']
    kinds = {b['name']: b['kind'] for b in blocks}
    res = {}
    nbar = int(round(song.length / bpb))
    first_dev = next((i for i, b in enumerate(blocks) if b['kind'].startswith('dev') or b['kind'] == 'var'),
                     len(blocks))
    motto_names = {b['name'] for b in blocks[:first_dev] if b['kind'] in ('intro', 'mist', 'solo', 'slow', 'source',
                                                                         't1', 't1b', 'river')}
    cell = []                  # (the material: the rendered lines only - WIN)
    mats = cell + [w for ln in _role_lines(parts, motto_names, ('melody', 'bass', 'voice')).values()
                   for w in windows(ln)]
    peak = next((x for x in sbl if x.peak), None)
    coda = next((x for x in sbl if kinds.get(x.name) in ('coda', 'coda_soft')), None)

    def lines_of(x, fns=('melody', 'counter', 'doubling')):
        out = {}
        for p in parts:
            if p.block == x.name and p.function in fns and p.role not in _UNP + ('harp',):
                out.setdefault((p.role, p.function), []).extend(p.notes)
        return {r: top_line(ns) for r, ns in out.items()}

    def fig_share(x):
        figs = [p for p in parts if p.block == x.name and p.function == 'figuration']
        n = int(round(x.length / bpb))
        hit = sum(1 for i in range(n) if any(_runs_in(p, x.start + i * bpb, x.start + (i + 1) * bpb, bpb)
                                             for p in figs))
        return hit / n if n else 0.0
    chorale = 0
    if peak is not None:
        bw = _bar_windows(lines_of(peak), [(peak.start, peak.end)], bpb)
        res['clx_theme'] = own_bars(bw, mats)
        res['clx_fig'] = round(fig_share(peak), 3)
        res['clx_tex'] = peak.texture
        brass_mel = any(p.block == peak.name and p.function == 'melody' and p.role in BRASS for p in parts)
        chorale = chorale or int(brass_mel and fig_share(peak) >= 0.5)
    if coda is not None:
        res['coda_fig'] = round(fig_share(coda), 3)
        brass_mel = any(p.block == coda.name and p.function == 'melody' and p.role in BRASS for p in parts)
        chorale = chorale or int(brass_mel and fig_share(coda) >= 0.5)
    res['fig_chorale'] = chorale
    # -- literal restatements of the melody's top line
    mel = top_line([n for p in parts if p.function == 'melody' and p.role not in _UNP for n in p.notes])
    best, cnt = 0, 0
    for u in (1, 2):
        L = u * bpb
        prev, run = None, 0
        for k in range(int(round(song.length / L))):
            x0 = k * L
            sig = tuple((round(a - x0, 2), round(d, 2), q) for a, d, q in mel if x0 - _EPS <= a < x0 + L - _EPS)
            if prev is not None and len(sig) >= 2 and sig == prev:
                run += 1
                cnt += 1
                best = max(best, run)
            else:
                run = 0
            prev = sig
    res['lit_max'], res['lit_n'] = best, cnt
    # -- episodes from the theme
    epi = [x for x in sbl if kinds.get(x.name) in ('episode', 'trio', 'var')]
    if epi:
        ls = {}
        for x in epi:
            for r, ln in lines_of(x, ('melody', 'counter', 'voice', 'bass')).items():
                ls[(x.name,) + r] = ln
        res['epi_own'] = own_bars(_bar_windows(ls, [(x.start, x.end) for x in epi], bpb), mats)
    # -- static stretches
    acc = [p for p in parts if p.function not in ('melody', 'counter', 'voice', 'doubling') and
           p.role not in _UNP]
    run = best = 0
    for i in range(int(round(sbl[-1].start / bpb))):          # (the last block's held chords are the close)
        a0 = i * bpb
        if any(p.function in ('counter', 'voice') and any(a0 - _EPS <= a < a0 + bpb - _EPS for a, _, _ in p.notes)
               for p in parts):
            run = 0
            continue
        moving = False
        for p in acc:
            sig = tuple((round(a - a0, 2), q) for a, _, q in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS)
            if len(sig) < 2 or p.art == 'tremolo':
                continue
            prv = tuple((round(a - a0 + bpb, 2), q) for a, _, q in p.notes if a0 - bpb - _EPS <= a < a0 - _EPS)
            if sig != prv:
                moving = True
                break
        run = run + 1 if not moving else 0
        if run > best:
            best, res['static_at'] = run, i + 2 - run
    res['static_run'] = best
    rt = next((x for x in sbl if kinds.get(x.name) == 'retrans'), None)
    if rt is not None:
        n_ = max((sum(1 for a, _, _ in p.notes if rt.end - bpb - _EPS <= a < rt.end - _EPS) for p in parts
                  if p.block == rt.name and p.function in ('melody', 'bass')), default=0)
        res['rt_lead'] = int(n_ >= 2)
    # -- after the climax
    if peak is not None:
        i = [x.name for x in sbl].index(peak.name)
        nxt = sbl[i + 1] if i + 1 < len(sbl) else None
        if nxt is not None and kinds.get(nxt.name) not in ('end', 'end_soft'):
            def roles_at(a0, a1, names=None):
                return {p.role for p in parts if (names is None or p.block in names) and p.role not in _UNP and
                        any(a < a1 - _EPS and a + d > a0 + _EPS for a, d, _ in p.notes)}
            per = [len(roles_at(j * bpb, (j + 1) * bpb)) for j in range(nbar)]
            nb = int(round(nxt.length / bpb))
            post = [len(roles_at(nxt.start + j * bpb, nxt.start + (j + 1) * bpb)) for j in range(nb)]
            res['post_roles'] = round(st.mean(post) / max(1e-6, st.mean(per)), 3) if post else None
            res['post_light'] = int(bool(orc.TEXTURES[nxt.texture].get('light')) or (post[0] if post else 0) <= 4)
    # -- the ending
    last = sbl[-1]
    rows = sorted(last.chart)
    K = Key(last.key)
    if len(rows) >= 2:
        vb = 0.0
        j = len(rows) - 2
        while j >= 0 and chord(rows[j][2].split('/')[0]).root % 12 == (K.tonic + 7) % 12 and '/' not in rows[j][2]:
            vb += rows[j][1]
            j -= 1
        res['end_vbeats'] = round(vb, 2)
        res['end_pre'] = int(j >= 0)
    ch_on = [a for p in parts if p.role == 'choir' for a, _, _ in p.notes]
    if ch_on:
        res['choir_late'] = int(min(ch_on) >= 0.75 * song.length)
    return res


def pair_shares_o9(S: list) -> dict:
    pairs = list(itertools.combinations(S, 2))
    if not pairs:
        return {}
    return {'same_clx_tex': round(sum(1 for a, b in pairs if a.get('clx_tex') and a.get('clx_tex') == b.get('clx_tex'))
                                  / len(pairs), 3)}


O10 = ('open_theme', 'open_silent', 'open_top', 'loud_peak', 'peak_margin', 'peak_pos', 'clx_top', 'vln_uni_hi',
       'still_run', 'trio_still', 'mot_per8', 'mot_open', 'bass_rep', 'bass_figs', 'end_bars', 'end_ratio',
       'fug_low')
LOUD_W = {'trumpets': 2.0, 'trombones': 2.0, 'tuba': 1.2, 'horns': 1.5, 'timpani': 1.0, 'percussion': 0.6}
"""The section loudness proxy's role weights (round o10; /d/tmp/o10/proxy.py: r 0.96 against the rendered reports'
section LUFS over the 16 o9 pieces, the loudest section right in 11 of 16 - within 1 LU in the rest)."""


def loud_proxy(song, P: float = 3.0) -> dict:
    """{section: proxy dB} - sum over the compiled notes of weight x (vel / 127)^P x the beats sounding, per beat;
    about twice the LUFS spread (x 0.5 ~ LU)."""
    import math
    out = {}
    for x in song.sections:
        a0, a1 = x.start, x.end
        e = 0.0
        for tid, t in song.tracks.items():
            w = LOUD_W.get(tid, 1.0)
            for n in getattr(t, '_notes', None) or ():
                if n.pitch < 21:
                    continue
                s_, z = max(a0, n.start), min(a1, n.start + n.dur)
                if z > s_:
                    e += w * (n.vel / 127.0) ** P * (z - s_)
        out[x.name] = 10 * math.log10(max(1e-9, e / max(1e-6, a1 - a0)))
    return out


def heard_top(notes) -> list:
    """The line heard on top: at every attack the highest note sounding (held or struck); a new entry where the top
    pitch changes or the top note is struck again - its duration to the next entry."""
    ns = sorted(notes)
    ons = sorted({round(a, 3) for a, _, _ in ns})
    out = []
    for t in ons:
        top = max(((q, abs(a - t) < 1e-3) for a, d, q in ns if a <= t + 1e-3 and a + d > t + 1e-3), default=None)
        if top is None:
            continue
        q, struck = top
        if not out or out[-1][2] != q or struck:
            out.append([t, 0.0, q])
    for i, x in enumerate(out):
        x[1] = (out[i + 1][0] if i + 1 < len(out) else x[0] + 1.0) - x[0]
    return [tuple(x) for x in out]


def measure_o10(sym, tune, song) -> dict:
    """Round o9's judges' tells (songs/_blind/ROUNDS.md "Round o9"), measured as the judges hear them:
    openings (open_theme: the song bar the first theme block starts - want <= 9; open_silent: bars with nothing
    sounding before the theme's 5th bar; open_top: the share of the first 12 bars whose highest sounding note at
    the bar's onsets is a melody / counter / voice / doubling line, not figuration or chords), the climax (loud_peak 1:
    the peak block the loudest by loud_proxy; peak_margin: its proxy dB over the loudest other block, x 0.5 ~ LU;
    peak_pos its centre's share of the piece; clx_top: the share of the peak's bars whose line heard on top (heard_top
    over every pitched part but the harp) states the motto / first theme; vln_uni_hi: violins I + II notes in unison
    above C6), static stretches as heard (still_run: the longest run of song bars before the last block with no
    accompaniment part of 3+ onsets in the bar and no counter / voice of 2+ - a tune over block chords; trio_still the
    same inside trio / episode blocks), the motto's ration (mot_per8: its logged statements per 8 song bars outside the
    development; mot_open: the share of the melody's 2-bar units that open on the motto's head), the bass (bass_rep: the
    share of the bass part's bars that are 4+ repeated same-pitch onsets; bass_figs: distinct bass bar rhythms per 25
    bars), the ending (end_bars: the last block's song bars; end_ratio: those over the peak + coda bars) and the
    fugato's entry (fug_low 1: the first fugato entry is in the cellos / basses alone)."""
    mat = tune.symphony
    bpb = song.beats_per_bar
    parts = [p for p in song.orchestration.parts if p.notes]
    pitched = [p for p in parts if p.role not in _UNP]
    sbl = song.orch_score.blocks
    blocks = mat['blocks']
    kinds = {b['name']: b['kind'] for b in blocks}
    nbar = int(round(song.length / bpb))
    res = {}
    LINE = ('melody', 'counter', 'voice', 'doubling')

    def sounding(a0, a1, ps):
        return [(p, n) for p in ps for n in p.notes if n[0] < a1 - _EPS and n[0] + n[1] > a0 + _EPS]
    # -- openings
    th = next((x for x in sbl if kinds.get(x.name) in ('t1', 'river')), None)
    if th is not None:
        res['open_theme'] = int(round(th.start / bpb)) + 1
        z = th.start + 4 * bpb
        res['open_silent'] = sum(1 for i in range(int(round(z / bpb))) if not sounding(i * bpb, (i + 1) * bpb, pitched))
    tops = 0
    n12 = min(12, nbar)
    for i in range(n12):
        a0 = i * bpb
        ss = [(p, n) for p, n in sounding(a0, a0 + bpb, pitched) if p.role != 'harp']
        if not ss:
            continue
        p, n = max(ss, key=lambda x: x[1][2])
        tops += p.function in LINE or p.function == 'bass' and len(ss) == 1
    res['open_top'] = round(tops / n12, 3) if n12 else None
    # -- the climax
    peak = next((x for x in sbl if x.peak), None)
    lp = loud_proxy(song)
    if peak is not None and peak.name in lp:
        oth = [v for k, v in lp.items() if k != peak.name]
        res['loud_peak'] = int(lp[peak.name] >= max(oth, default=-99))
        res['peak_margin'] = round(0.5 * (lp[peak.name] - max(oth, default=lp[peak.name])), 2)
        res['peak_pos'] = round((peak.start + peak.end) / 2 / song.length, 3)
        first_dev = next((i for i, b in enumerate(blocks) if b['kind'].startswith('dev') or b['kind'] == 'var'),
                         len(blocks))
        names = {b['name'] for b in blocks[:first_dev] if b['kind'] in ('intro', 'mist', 'solo', 'slow', 'source',
                                                                       't1', 't1b', 'river')}
        cell = []                  # (the material: the rendered lines only - WIN)
        mats = cell + [w for ln in _role_lines(parts, names, ('melody', 'bass', 'voice')).values() for w in windows(ln)]
        top = heard_top([n for p in pitched if p.block == peak.name and p.role != 'harp' for n in p.notes])
        res['clx_top'] = own_bars(_bar_windows({'top': top}, [(peak.start, peak.end)], bpb), mats)
    v1 = {(round(a, 2), q) for p in parts if p.role == 'violins1' for a, _, q in p.notes}
    res['vln_uni_hi'] = sum(1 for p in parts if p.role == 'violins2' for a, _, q in p.notes
                            if q > 84 and (round(a, 2), q) in v1)
    # -- static stretches as heard
    def still(i):
        a0 = i * bpb
        for p in pitched:
            n_ = sum(1 for a, _, _ in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS)
            if p.function in ('counter', 'voice') and n_ >= 2:
                return False
            if p.function not in LINE and p.art != 'tremolo' and n_ >= 3:
                return False
        return bool(sounding(a0, a0 + bpb, pitched))
    run = best = 0
    for i in range(int(round(sbl[-1].start / bpb))):
        run = run + 1 if still(i) else 0
        best = max(best, run)
    res['still_run'] = best
    tb = [x for x in sbl if kinds.get(x.name) in ('trio', 'episode')]
    if tb:
        bt = 0
        for x in tb:
            run = 0
            for i in range(int(round(x.start / bpb)), int(round(x.end / bpb))):
                run = run + 1 if still(i) else 0
                bt = max(bt, run)
        res['trio_still'] = bt
    # -- the motto's ration
    log = getattr(song, 'symphony_log', None) or []
    devn = {b['name'] for b in blocks if b['kind'].startswith('dev')}
    out_bars = sum(x.length for x in sbl if x.name not in devn) / bpb
    mot = [e for e in log if e['tf'] not in ('cantilena', 'theme') and e['block'] not in devn]
    res['mot_per8'] = round(8 * len(mot) / max(1.0, out_bars), 2)
    shape = motto_shape(sym, mat['motto'])
    mel = top_line([n for p in pitched if p.function == 'melody' and p.block not in devn for n in p.notes])
    hits = set(round(x, 3) for x in motto_hits(mel, shape))
    units = opens = 0
    for k in range(0, nbar, 2):
        a0, a1 = k * bpb, (k + 2) * bpb
        ns = [n for n in mel if a0 - _EPS <= n[0] < a1 - _EPS]
        if len(ns) < 3:
            continue
        units += 1
        opens += any(round(n[0], 3) in hits for n in ns[:2])
    res['mot_open'] = round(opens / units, 3) if units else None
    # -- the bass
    bass = [p for p in pitched if p.role in ('basses', 'cellos', 'tuba') and p.function in ('bass', 'ostinato')]
    bars = {}
    for p in bass:
        for a, d, q in p.notes:
            bars.setdefault(int((a + 0.1) // bpb), {}).setdefault(p.role, []).append((a, q))
    rep = tot = 0
    sigs = set()
    for i, by in bars.items():
        ns = sorted(by.get('basses') or by.get('cellos') or by.get('tuba') or [])
        if not ns:
            continue
        tot += 1
        sigs.add(tuple(round(((a - i * bpb) % bpb) * 4) for a, _ in ns))
        rep += len(ns) >= 4 and len({q for _, q in ns}) == 1
    res['bass_rep'] = round(rep / tot, 3) if tot else None
    res['bass_figs'] = round(len(sigs) * 25.0 / max(1, tot), 2)
    # -- the ending
    last = sbl[-1]
    res['end_bars'] = int(round(last.length / bpb))
    pc = sum(x.length for x in sbl if x.peak or kinds.get(x.name) in ('coda', 'coda_soft')) / bpb
    res['end_ratio'] = round(res['end_bars'] / max(1.0, pc), 3)
    # -- the fugato's first entry
    fb = next((x for x in sbl if kinds.get(x.name) == 'dev_fugato'), None)
    if fb is not None:
        vs = [p for p in pitched if p.block == fb.name and p.function == 'voice']
        if vs:
            t0 = min(min(a for a, _, _ in p.notes) for p in vs)
            first = {p.role for p in vs if min(a for a, _, _ in p.notes) < t0 + 0.5}
            res['fug_low'] = int(first <= {'cellos', 'basses', 'bassoons', 'tuba'})
            res['fug_first'] = '+'.join(sorted(first))
    return res


def pair_shares_o10(S: list) -> dict:
    pairs = list(itertools.combinations(S, 2))
    if not pairs:
        return {}
    return {'same_fug': round(sum(1 for a, b in pairs if a.get('fug_first') and a.get('fug_first') == b.get('fug_first'))
                              / len(pairs), 3)}


O11 = ('seconds', 'peak_pos', 'top_pos', 'loud_pos', 'one_summit', 'pre_peak_margin_lu', 'pre_peak_margin_semis',
       'open_loud', 'tutti_peak', 'clx_key_home', 't1_home', 't2_home', 'recap_weight', 'dev_share', 'dev_bars',
       'dev_out_key', 'seq_links_max', 'dev_shrink', 'rt_pedal', 'cadence_at_end')


def seq_links(line, unit: float, t0: float, t1: float) -> int:
    """The longest chain of `unit`-beat units in [t0, t1) each the unit before transposed unchanged (the same onsets
    in the unit, the same GENERIC intervals - a tonal or a real sequence): the links of a block sequence. Independent
    of symphony._seq_links (the code review's 5.5): generic intervals, not +-1 semitone, and measure_o11 reads the
    RENDERED role lines (melody / counter / voice of the development's blocks), not the composer's block lines."""
    units = []
    a = t0
    while a < t1 - _EPS:
        ns = sorted((round(x - a, 2), q) for x, _, q in line if a - _EPS <= x < a + unit - _EPS)
        units.append(ns)
        a += unit

    def same(u, v):
        if len(u) < 2 or len(u) != len(v) or [x for x, _ in u] != [x for x, _ in v]:
            return False
        if u[0][1] == v[0][1]:
            return False                                 # (a literal repeat is not a transposition)
        return all(generic(b[1] - a_[1]) == generic(y[1] - x[1]) for a_, b, x, y in zip(u, u[1:], v, v[1:]))
    best = run = 0
    for u, v in zip(units, units[1:]):
        run = run + 1 if same(u, v) else 0
        best = max(best, run)
    return best


O12 = ('acc_run', 'vln_peak_over', 'brass_peak', 'head_leap', 'head_scale', 'rt_drive')
_ACC_FNS = ('ostinato', 'figuration', 'colour', 'bass', 'pedal', 'harmony', 'inner')


def measure_o12(sym, tune, song) -> dict:
    """Round o12's tells (ROUNDS.md "Round o12"): acc_run the longest run of song bars whose accompaniment onsets
    (every ostinato / figuration / colour / bass / pedal / harmony / inner part, a 1/4-beat grid) repeat unchanged,
    outside the peak and the retransition / ending blocks; vln_peak_over the peak's violins I top over every line
    (melody / counter / voice / doubling) before it, semitones; brass_peak the trumpets and trombones on a line in the
    peak (0-2; 2 for the horns when the piece has neither); head_leap the motto's widest interval in its first 2 units
    and head_scale its longest run of steps (<= 2 semitones) one way; rt_drive the last bars before the peak with the
    basses / cellos / timpani re-striking the dominant (song bars)."""
    from agentsound.theory import Key
    mat = tune.symphony
    bpb = song.beats_per_bar
    sbl = song.orch_score.blocks
    kinds = {b['name']: b['kind'] for b in mat['blocks']}
    parts = [p for p in song.orchestration.parts if p.notes]
    res = {}
    acc = [p for p in parts if p.function in _ACC_FNS and p.role != 'percussion']
    sig = []
    for b in sbl:
        if b.peak or kinds.get(b.name) in ('retrans', 'end', 'end_soft'):
            sig.append(None)
            continue
        ps = [p for p in acc if p.block == b.name]
        for j in range(int(round(b.length / bpb))):
            a0 = b.start + j * bpb
            sig.append(frozenset(round((a - a0) * 4) / 4 for p in ps for a, _, _ in p.notes
                                 if a0 - _EPS <= a < a0 + bpb - _EPS))
    best = run = 0
    for i, g_ in enumerate(sig):
        run = run + 1 if g_ and i and sig[i - 1] == g_ else (1 if g_ else 0)
        best = max(best, run)
    res['acc_run'] = best
    peak = next((x for x in sbl if x.peak), None)
    if peak is not None:
        names = [x.name for x in sbl]
        before = set(names[:names.index(peak.name)])
        lf = ('melody', 'counter', 'voice', 'doubling')
        pre = max((q for p in parts if p.block in before and p.function in lf and p.role not in _UNP + ('harp',)
                   for _, _, q in p.notes), default=None)
        vt = max((q for p in parts if p.block == peak.name and p.role == 'violins1' for _, _, q in p.notes),
                 default=None)
        res['vln_peak_over'] = vt - pre if pre is not None and vt is not None else None
        on = lambda r: any(p.block == peak.name and p.role == r and p.function in lf for p in parts)  # noqa: E731
        res['brass_peak'] = (sum(1 for r in ('trumpets', 'trombones') if on(r))
                             if any(p.role in ('trumpets', 'trombones') for p in parts) else 2 * int(on('horns')))
        pi = names.index(peak.name)
        if pi:
            pre_b = sbl[pi - 1]
            dom = (Key(tune.key).tonic + 7) % 12
            low = [p for p in parts if p.block == pre_b.name and p.role in ('basses', 'cellos', 'timpani')]
            nb = int(round(pre_b.length / bpb))
            n = 0
            for i in range(nb - 1, -1, -1):
                a0 = pre_b.start + i * bpb
                hits = [q for p in low for a, _, q in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS]
                if hits and all(q % 12 == dom for q in hits) and len(hits) >= 2:
                    n += 1
                elif n:
                    break
            res['rt_drive'] = n
    ms = sorted(sym.motto_notes(mat['motto'], 0.0, 60, set(Key('C major').pcs)))
    U = mat['U']
    head = [q for a, _, q in ms if a < 2 * U - _EPS] or [q for _, _, q in ms[:4]]
    iv = [b - a for a, b in zip(head, head[1:])]
    res['head_leap'] = max((abs(x) for x in iv), default=0)
    allv = [b - a for a, b in zip([q for _, _, q in ms], [q for _, _, q in ms][1:])]
    sc = r_ = 0
    for i, x in enumerate(allv):
        r_ = r_ + 1 if 0 < abs(x) <= 2 and i and 0 < abs(allv[i - 1]) <= 2 and (x > 0) == (allv[i - 1] > 0) else             (1 if 0 < abs(x) <= 2 else 0)
        sc = max(sc, r_)
    res['head_scale'] = sc
    return res


def measure_o11(sym, tune, song) -> dict:
    """The masterpiece panel's form tells (songs/_endless_orchestra/out/masterpiece_gap/REPORT.md, ROUNDS.md "Round
    o11"): the summit (peak_pos the peak block's centre, top_pos the first highest note's, loud_pos the loudest block's
    centre - shares of the piece; one_summit 1 when the highest note, the loudest block (loud_proxy) and the most roles
    all fall in the peak block and its centre in 0.6-0.88; pre_peak_margin_lu / _semis: the peak over every block before
    it - proxy dB x 0.5 and the highest pitched note, harp and timpani out; open_loud 1 when the first block is the
    loudest; tutti_peak 1 when no block sounds more roles than the peak), the return (clx_key_home 1 when the peak
    block's key has the home tonic; t1_home 1 when the first theme (recap / refrain / river / var / the
    recomposed recap2) sounds in the home tonic at or after the peak's start; t2_home 1 when the second theme comes back
    in the home tonic - None without one; recap_weight the return blocks' bars over the exposition's theme blocks'), the
    development (dev_share its blocks' bars over the piece's, dev_bars in song bars, dev_out_key 1 when a key outside
    tonic / dominant / relative is visited, seq_links_max the longest chain of 1- / 2-bar units transposed unchanged in
    its melody / counter / voices, dev_shrink 1 when the units shorten: the last model's notes faster than the
    first's), rt_pedal the last bars of the pre-peak block over the dominant in the bass (song bars), cadence_at_end 1
    when the last chart moves V (V7, vii) - I, and the piece's seconds."""
    from agentsound.theory import Key, chord
    mat = tune.symphony
    k = float(mat['scale'])
    U = mat['U']
    bpb = song.beats_per_bar
    blocks = mat['blocks']
    sbl = song.orch_score.blocks
    parts = [p for p in song.orchestration.parts if p.notes]
    pitched = [p for p in parts if p.role not in _UNP + ('harp',)]
    res = {'seconds': round(song.seconds(song.length), 1)}
    home = blocks[0]['key'] if blocks else tune.key
    home = tune.key
    ht = Key(home).tonic
    L = song.length
    peak = next((x for x in sbl if x.peak), None)
    pi = next((i for i, x in enumerate(sbl) if x.peak), None)
    if peak is not None:
        res['peak_pos'] = round((peak.start + peak.end) / 2 / L, 3)
        allq = [(q, a) for p in pitched for a, _, q in p.notes]
        top = max(q for q, _ in allq)
        t_top = min(a for q, a in allq if q == top)
        res['top_pos'] = round(t_top / L, 3)
        lp = loud_proxy(song)
        lname = max(lp, key=lambda n: lp[n])
        lb = next(x for x in sbl if x.name == lname)
        res['loud_pos'] = round((lb.start + lb.end) / 2 / L, 3)
        before = [x.name for x in sbl[:pi]]
        res['pre_peak_margin_lu'] = round(0.5 * (lp[peak.name] - max((lp[n] for n in before if n in lp),
                                                                       default=lp[peak.name] - 20)), 2)
        ptop = max((q for p in pitched if p.block == peak.name for _, _, q in p.notes), default=0)
        btop = max((q for p in pitched if p.block in before for _, _, q in p.notes), default=0)
        res['pre_peak_margin_semis'] = ptop - btop
        res['open_loud'] = int(lname == sbl[0].name)
        roles = {}
        for p in parts:
            roles.setdefault(p.block, set()).add(p.role)
        res['tutti_peak'] = int(len(roles.get(peak.name, ())) >= max(len(v) for v in roles.values()))
        res['one_summit'] = int(peak.start - _EPS <= t_top < peak.end and lname == peak.name and res['tutti_peak']
                                and 0.6 <= res['peak_pos'] <= 0.88)
        res['clx_key_home'] = int(Key(peak.key).tonic == ht)
    # -- the return
    first_dev = next((i for i, b in enumerate(blocks) if b['kind'].startswith('dev') or b['kind'] == 'var'),
                     len(blocks))
    pb = next((i for i, b in enumerate(blocks) if b.get('peak')), None)
    T1 = ('recap', 'refrain', 'river', 'var')
    if pb is not None:
        apx = (tune.arrange or {}).get('apex')
        res['t1_home'] = int(any(Key(b['key']).tonic == ht and b['theme'] and (
            b['kind'] in T1 or (b['kind'] == 'recap2' and apx in ('combine', 'second'))) for b in blocks[pb:]))
    t2 = next((b for b in blocks[:first_dev] if b['kind'] == 't2'), None)
    if t2 is not None:
        res['t2_home'] = int(any(b['kind'] in ('recap2',) and Key(b['key']).tonic == ht for b in blocks[first_dev:]))
    expo = sum(b['bars'] for b in blocks[:first_dev] if b['kind'] in ('t1', 't1b', 't2', 't2b', 'river'))
    ret = sum(b['bars'] for b in blocks[first_dev:] if b['kind'] in ('recap', 'recap2') or
              (b['kind'] == 'river' and b.get('peak')))
    res['recap_weight'] = round(ret / expo, 3) if expo else None
    # -- the development
    total = sum(b['bars'] for b in blocks)
    dev = [b for b in blocks if b['kind'].startswith('dev')]
    db = sum(b['bars'] for b in dev)
    res['dev_share'] = round(db / max(1, total), 3)
    res['dev_bars'] = int(round(db * U * k / bpb))
    rel = {ht, (ht + 7) % 12, (ht + (3 if Key(home).minorish else 9)) % 12}
    keys = set()
    for b in dev:
        for _, _, sy in b['chart']:
            try:
                c = chord(sy.split('/')[0])
            except Exception:                            # noqa: BLE001
                continue
            if not sy.startswith(('V7', 'v')) and '7' not in sy:
                keys.add(c.root % 12)
    res['dev_out_key'] = int(bool(keys - rel)) if dev else None
    if dev:
        best = 0
        sb = {x.name: x for x in sbl}
        for b in dev:
            if b['name'] not in sb:
                continue
            x = sb[b['name']]
            for ln in _role_lines(parts, {b['name']}, ('melody', 'counter', 'voice')).values():
                best = max(best, seq_links(ln, U * k, x.start, x.end), seq_links(ln, 2 * U * k, x.start, x.end))
        res['seq_links_max'] = best
        b = max(dev, key=lambda x: x['bars'])
        mel = sorted(b['theme'] or next(iter(b['voices'].values()), []))
        if len(mel) >= 6:
            q = max(1, len(mel) // 4)
            d0 = st.mean(d for _, d, _ in mel[:q])
            d1 = st.mean(d for _, d, _ in mel[-q:])
            res['dev_shrink'] = int(d1 < 0.8 * d0)
    # -- the dominant pedal before the peak
    if pi:
        pre = sbl[pi - 1]
        dom = (Key(home).tonic + 7) % 12
        low = [p for p in parts if p.block == pre.name and p.role in ('basses', 'cellos', 'tuba', 'timpani', 'bassoons',
                                                                         'horns', 'trombones')
               and p.function in ('bass', 'pedal')]
        held = [p for p in parts if p.block == pre.name and p.function == 'pedal']   # (a high pedal counts too)
        nb = int(round(pre.length / bpb))
        run = 0
        for i in range(nb - 1, -1, -1):
            t = pre.start + i * bpb + 0.25
            ps = [q for p in low for a, d, q in p.notes if a - _EPS <= t < a + d + 0.3]
            hs = [q for p in held for a, d, q in p.notes if a - _EPS <= t < a + d + 0.3]
            if (ps and min(ps) % 12 == dom) or any(q % 12 == dom for q in hs):
                run += 1
            elif i < nb - 1 or ps:
                break
        res['rt_pedal'] = run
    # -- the last cadence
    end = blocks[-1]
    ch = [sy for _, d, sy in sorted(end['chart']) if d > _EPS]
    for b in reversed(blocks[:-1]):
        if len(ch) >= 2:
            break
        ch = [sy for _, d, sy in sorted(b['chart']) if d > _EPS] + ch
    if len(ch) >= 2:
        lk = Key(end['key'])
        try:
            r1, r2 = chord(ch[-2].split('/')[0]).root % 12, chord(ch[-1].split('/')[0]).root % 12
            res['cadence_at_end'] = int(r2 == lk.tonic and r1 in ((lk.tonic + 7) % 12, (lk.tonic + 11) % 12))
        except Exception:                                # noqa: BLE001
            res['cadence_at_end'] = 0
    return res


def measure_refs(root: Path) -> dict:
    """The material tells on the three hand-written references (REFS: their sections), every pitched role's line."""
    import runpy
    out = {}
    for name, R in REFS.items():
        folder = root / 'songs' / f'pro-orch-symphonic-{name}'
        song = runpy.run_path(str(folder / 'song.py'))['build']()
        bpb = song.beats_per_bar
        sec = {x.name: (x.start, x.end) for x in song.sections}

        def lines(names):
            res_ = {}
            for tid, tr in song.tracks.items():
                if tid in _UNP + ('harp', 'choir') or not getattr(tr, 'notes', None):
                    continue
                ns = [(n.start, n.dur, n.pitch) for n in tr.notes
                      if any(sec[x][0] - _EPS <= n.start < sec[x][1] - _EPS for x in names)]
                if ns:
                    res_[tid] = top_line(ns)
            return res_
        m_motto = [w for ln in lines(R['motto']).values() for w in windows(ln)]
        m_all = [w for ln in lines(R['expo']).values() for w in windows(ln)]
        dl = lines(R['dev'])
        spans = [sec[x] for x in R['dev']]
        cl = lines(R['climax'])
        top = [top_line([n for ln in cl.values() for n in ln])]
        out[name] = {'dev_own': own_bars(_bar_windows(dl, spans, bpb), m_all),
                     'dev_mot': own_bars(_bar_windows(dl, spans, bpb), m_motto),
                     'clx_motto': own_share(top, m_motto), 'clx_own': own_share(top, m_all),
                     'clx_motto_roles': own_share(list(cl.values()), m_motto)}
        print(name, out[name], flush=True)
    return out


def main() -> int:
    args = sys.argv[1:]
    if '--refs' in args:                    # (round o6: the material tells on the references)
        root = Path(args[0]).resolve()
        sys.path.insert(0, str(root))
        print('REFS', json.dumps(measure_refs(root)))
        return 0
    out_json = None
    if '--json' in args:
        i = args.index('--json')
        out_json = args[i + 1]
        args = args[:i] + args[i + 2:]
    o4 = '--o3' not in args                 # (--o3: the round-o3 tells only - fast, no compile)
    args = [a for a in args if a != '--o3']
    root = Path(args[0]).resolve()
    sys.path.insert(0, str(root))
    os.environ.setdefault('AGENTSOUND_SAMPLES', 'D:/Repos/AgentSound/assets/samples')
    os.environ.setdefault('AGENTSOUND_VOICES', 'D:/Repos/AgentSound/assets/voices')
    from agentsound.endless import composer, genres
    from agentsound.endless import symphony as sym
    from agentsound.endless.perform import build
    g = genres.get('orchestra-symphonic')
    sets, allp = [], []
    for s0 in map(int, args[1:]):
        plan = composer.set_plan(g, 8, s0)
        S = []
        for j, slot in enumerate(plan):
            sd = s0 + j
            t = composer.compose(g, sd, plan=slot)
            s = build(t, g)
            r = measure(sym, t, s)
            if o4:
                s.compile()                     # (the velocities: brass_flat)
                r.update(measure_o4(sym, t, s))
                r.update(measure_o5(sym, t, s))
                r.update(measure_o6(sym, t, s))
                r.update(measure_o7(sym, t, s))
                r.update(measure_o8(sym, t, s))
                r.update(measure_o9(sym, t, s))
                r.update(measure_o10(sym, t, s))
                r.update(measure_o11(sym, t, s))
                r.update(measure_o12(sym, t, s))
            r.update(seed=sd, feel=t.feel, layout=t.symphony['layout'], title=t.title, score=composer.score(s, t, g)['score'])
            S.append(r)
            print(f"{sd} {t.feel:<8} motto_ok {r['motto_ok']} dev_motto {r['dev_motto']} build_stock "
                  f"{r['build_stock']} clx_copy {r.get('clx_copy')} clx_double {r.get('clx_double')} top_early "
                  f"{r.get('top_early')} slips {r['slips']} score {r['score']:.1f}", flush=True)
            if o4:
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in (
                    'mod48', 'recap_mel', 'recap_bars', 't2_back', 't2_copy', 'build_frame', 't2_cells', 't2_npb',
                    't2_ok', 'lead_cells', 'folds', 'osti_max', 'viola_over', 'timp_off', 'flute_top',
                    'chamber_bare', 'brass_flat')) + '  ' + ''.join(c for c, _ in r['row']), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in (
                    'mel_held', 'one_line', 'thin_roles', 'fig_off', 'fig_circ', 'end_pcs', 'end_third', 'end_bare',
                    'end_cad', 'mel_under', 'harp_over', 'clx_counter', 'tpt_low', 'tbn_high', 'chamber',
                    'chamber_horns', 'open_plan', 'coda_plan')), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in (
                    'clx_motto', 'clx_own', 'clx_motto_roles', 'dev_own', 'buried', 'rep_wind', 'rep8', 'unison',
                    'plan_sig')), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in (
                    'sch_whole', 'end_rows', 'end_top', 'end_inv', 'end_vbass', 'end_held', 'clx_mroles', 'clx_moct',
                    'clx_moct_max', 'clx_follow', 'clx_follow_oct', 'coda_follow', 'coda_follow_oct', 'inner_static',
                    'empty', 'stock_n', 'stock3', 'end7_sig')), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in O8), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in O9 + ('clx_tex',)), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in O10 + ('fug_first',)), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in O11 + ('layout',)), flush=True)
                print('      ' + ' '.join(f"{x} {r.get(x)}" for x in O12), flush=True)
        ps = pair_shares(S)
        if o4:
            ps.update(pair_shares_o4(S))
            ps.update(pair_shares_o5(S))
            ps.update(pair_shares_o6(S))
            ps.update(pair_shares_o7(S))
            ps.update(pair_shares_o9(S))
            ps.update(pair_shares_o10(S))
        print(f"set {s0}: {ps}")
        sets.append(ps)
        allp += S
    num = ('motto_ok', 'motto_rep', 'dev_motto', 'build_stock', 'clx_copy', 'clx_double', 'top_early', 'slips', 'score')
    if o4:
        num += ('mod48', 'lens', 'recap_mel', 'recap_bars', 't2_back', 't2_copy', 'build_frame', 'build_pedal',
                'build_rise', 't2_cells', 't2_npb', 't2_ok', 'lead_cells', 'folds', 'osti_max', 'osti8', 'viola_over',
                'timp_off', 'flute_top','chamber_bare', 'brass_flat',
                'mel_held', 'sch_held', 'one_line', 'thin_roles', 'fig_off', 'fig_circ', 'end_pcs', 'end_third',
                'end_bare', 'end_cad', 'mel_under', 'harp_over', 'clx_counter', 'tpt_low', 'tbn_high', 'chamber',
                'chamber_horns', 'clx_motto', 'clx_own', 'clx_motto_roles', 'dev_own', 'dev_mot', 'buried', 'sch_buried',
                'rep_wind', 'rep8', 'unison', 'clx_major', 'clx_harp', 'end_roll', 'coda_soft',
                'sch_whole', 'end_rows', 'end_top', 'end_inv', 'end_vbass', 'end_held', 'clx_mroles', 'clx_moct',
                'clx_moct_max', 'clx_follow', 'clx_follow_oct', 'coda_follow', 'coda_follow_oct', 'inner_static',
                'empty', 'stock_n', 'stock3') + O8 + O9 + O10 + O11 + O12
    mean = {k: round(st.mean(x[k] for x in allp if x.get(k) is not None), 3) for k in num
            if any(x.get(k) is not None for x in allp)}
    mean.update({k: round(st.mean(s[k] for s in sets if k in s), 3) for k in sorted({k for s in sets for k in s})})
    print('MEAN', json.dumps(mean))
    if out_json:
        Path(out_json).write_text(json.dumps({'pieces': allp, 'sets': sets, 'mean': mean}, indent=1) + '\n',
                                  encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
