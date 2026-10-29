"""Does BEST-OF-N selection (endless/run.py candidates: composer.score ranks N pre-audio candidates per set slot, only
the best is rendered) hurt diversity by preferring boring-but-correct tunes? Measurement only - no generator change.

    # 1. the candidate pools (no audio): per set seed a set plan of --n slots (composer.set_plan), per slot ALL the
    #    runner's candidates (run.candidates, seeds as the CLI walks them: set seed + seeds_for(N) per slot, the set's
    #    `prev` the chosen piece before) with the score's sub-metrics and independent interest / diversity features
    python songs/_blind/bestofn_newage.py pool --genre new-age-piano --sets 100000,101000,... --n 8 --cands 8 \
        --json OUT.json
    # 2. the selection effect: chosen best vs the pool vs the first passing candidate (= best-of-1), per feature the
    #    within-slot z shift, the variance ratio, the best's percentile, the score's discriminating metrics; across a
    #    set the pairwise similarity of the chosen tunes (best-of-N set vs best-of-1 set vs random sets)
    python songs/_blind/bestofn_newage.py analyze OUT.json [--md REPORT_PART.md]
    # 3. the blind test: per-piece packets of two rendered endless sets (endless ... --candidates 8 / 1, the same
    #    --seed: the same set plan) -> a quality panel (per piece, the masterpiece question) and set-level pairs
    #    (set_round.py's JUDGE_SET answer format, new-age brief)
    python songs/_blind/bestofn_newage.py deal ROUND JROOT --set A=DIR_best8,DIR_best1 [--set B=...] [--judges 7]
    python songs/_blind/bestofn_newage.py score JROOT
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics as st
import sys
import types
from collections import Counter
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))


# ------------------------------------------------------------------------------------------------ features

def _ent(xs) -> float:
    c = Counter(xs)
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values()) if n else 0.0


def _deg(sym: str, tonic: int) -> str:
    from agentsound.theory import chord
    c = chord(sym)
    q = 'm' if c.is_minor else ''
    if '7' in sym and 'maj7' not in sym and not c.is_minor:
        q = '7'
    return f"{(c.root - tonic) % 12}{q}"


def features(tune, song) -> dict:
    """Independent interest / diversity measures from the lead sheet and the performance (not the score's)."""
    from agentsound.endless import composer
    from agentsound.theory import chord
    key = composer.Key(tune.key)
    scale = set(key.pcs)
    bar = tune.meter
    mel = [n for p in tune.parts for n in (tune.melody.get(p) or [])]
    pitches = [n[2] for n in mel]
    ints = []
    for p in tune.parts:
        ps = [n[2] for n in (tune.melody.get(p) or [])]
        ints += [b - a for a, b in zip(ps, ps[1:])]
    ai = [abs(i) for i in ints]
    dirs = [1 if i > 0 else -1 for i in ints if i]
    on = [round((n[0] % bar) * 4) / 4 for n in mel]
    f = {
        'mel_range': max(pitches) - min(pitches) if pitches else 0,
        'head_range': (max(n[2] for n in tune.motif) - min(n[2] for n in tune.motif)) if tune.motif else 0,
        'mel_absint': st.mean(ai) if ai else 0,
        'leap5': sum(a >= 5 for a in ai) / max(1, len(ai)),
        'leap7': sum(a >= 7 for a in ai) / max(1, len(ai)),
        'step': sum(1 <= a <= 2 for a in ai) / max(1, len(ai)),
        'repeat': sum(a == 0 for a in ai) / max(1, len(ai)),
        'int_entropy': _ent(max(-12, min(12, i)) for i in ints),
        'dir_change': sum(a != b for a, b in zip(dirs, dirs[1:])) / max(1, len(dirs) - 1),
        'dur_entropy': _ent(round(n[1] * 4) / 4 for n in mel),
        'onset_entropy': _ent(on),
        'offbeat': sum(o % 1 != 0 for o in on) / max(1, len(on)),
        'pc_entropy': _ent(p % 12 for p in pitches),
        'chroma': sum(p % 12 not in scale for p in pitches) / max(1, len(pitches)),
        'mel_notes_per_bar': len(mel) / max(1, sum(sum(d for _, d in tune.changes[p]) for p in tune.parts) / bar),
    }
    chords = [s for p in tune.parts for s, _ in tune.changes[p]]
    f['chord_distinct'] = len(set(chords)) / max(1, len(chords))
    f['chord_nondiat'] = sum(not set(chord(s).pcs) <= scale for s in chords) / max(1, len(chords))
    f['chord_ext'] = sum(bool(re.search(r'(7|9|11|13|sus|add|6)', s)) for s in chords) / max(1, len(chords))
    f['chord_slash'] = sum('/' in s for s in chords) / max(1, len(chords))
    # the contrast: the B part's register / density against A1
    a1 = tune.melody.get(tune.parts[0]) or []
    others = [p for p in tune.parts[1:] if not re.match(r'A\d', p)]
    b = tune.melody.get(others[0]) if others else []
    if a1 and b:
        f['contrast_reg'] = abs(st.median(n[2] for n in b) - st.median(n[2] for n in a1))
        f['contrast_den'] = abs(math.log(len(b) / max(1, len(a1))))
    f['climax_lift_ls'] = (tune.climax or {}).get('pitch', 0) - (st.mean(n[2] for n in a1) if a1 else 0)
    # the performance
    notes = song.tracks['piano']._notes
    v = sorted(n.vel for n in notes)
    q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
    f['vel_range'] = q(0.9) - q(0.1)
    f['vel_sd'] = st.pstdev(v)
    f['pitch_span'] = max(n.pitch for n in notes) - min(n.pitch for n in notes)
    f['seconds'] = song.seconds(song.length)
    f['n_sections'] = len(song.sections)
    f['tempo'] = tune.tempo
    return f


def signature(tune) -> dict:
    """What the pairwise similarity compares: the motif's intervals and onset rhythm, the chord-degree 3-grams, the
    section plan, the categorical draws."""
    from agentsound.endless import composer
    tonic = composer.Key(tune.key).tonic % 12
    m = tune.motif or []
    degs = []
    for p in tune.parts:
        degs.append([_deg(s, tonic) for s, _ in tune.changes[p]])
    return {'motif_int': [b[2] - a[2] for a, b in zip(m, m[1:])][:12],
            'motif_on': sorted({round((n[0] - (m[0][0] if m else 0)) * 4) / 4 for n in m}),
            'motif_dur': [round(n[1] * 4) / 4 for n in m][:12],
            'deg3': sorted({' '.join(d[i:i + 3]) for d in degs for i in range(len(d) - 2)}),
            'cats': {'form': tune.form, 'meter': tune.meter, 'mode': tune.mode, 'key': tune.key, 'feel': tune.feel,
                     'mood': tune.mood, 'tempo': tune.tempo, 'parts': ' '.join(tune.parts),
                     'end_kind': tune.end_kind, 'intro': (tune.intro or {}).get('kind'),
                     'tag_frame': (tune.tag or {}).get('frame'),
                     'climax_part': (tune.climax or {}).get('part')}}


# ------------------------------------------------------------------------------------------------ 1. the pools

def cmd_pool(a) -> int:
    from agentsound.endless import composer, genres, run
    g = genres.get(a.genre).validate()
    args = types.SimpleNamespace(mood=None, swing=None)
    out = {'genre': a.genre, 'n': a.n, 'cands': a.cands, 'sets': []}
    for S in [int(x) for x in a.sets.split(',')]:
        plan = composer.set_plan(g, a.n, S)
        seed, prev, slots = S, None, []
        for k, slot in enumerate(plan):
            g_ = genres.get(slot['genre']) if slot.get('genre') else g
            cs = run.candidates(g_, seed, a.cands, args, lambda *x: None, plan=slot, prev=prev)
            tried = run.seeds_for(g_, a.cands)
            seed += tried
            if not cs:
                slots.append({'slot': k + 1, 'cands': []})
                continue
            rows = []
            for c in cs:
                sc = c['score']
                rows.append({'seed': c['seed'], 'score': sc['score'], 'hard': sc['hard'],
                             'sub': {m: v[1] for m, v in sc['parts'].items()},
                             'val': {m: v[0] for m, v in sc['parts'].items()},
                             'feat': features(c['tune'], c['song']), 'sig': signature(c['tune']),
                             'title': c['tune'].title})
            best = rows[0]['seed']
            first = min(r['seed'] for r in rows)
            slots.append({'slot': k + 1, 'best': best, 'first': first, 'tried': tried, 'cands': rows})
            prev = cs[0]['song']
            print(f"set {S} slot {k + 1}: {len(rows)} candidates, best {best} {rows[0]['score']}, first {first} "
                  f"{next(r['score'] for r in rows if r['seed'] == first)}, mean "
                  f"{st.mean(r['score'] for r in rows):.1f}", flush=True)
        out['sets'].append({'set_seed': S, 'slots': slots})
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=0, default=str), encoding='utf-8')
    return 0


# ------------------------------------------------------------------------------------------------ 2. the analysis

def _lev(x, y) -> float:
    if not x and not y:
        return 0.0
    d = list(range(len(y) + 1))
    for i, a in enumerate(x, 1):
        prev, d[0] = d[0], i
        for j, b in enumerate(y, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (abs(a - b) > 1))
            prev, d[j] = d[j], cur
    return d[-1] / max(len(x), len(y))


def _jac(x, y) -> float:
    x, y = set(map(str, x)), set(map(str, y))
    return len(x & y) / len(x | y) if x | y else 1.0


def sim(r1, r2, zs) -> dict:
    s1, s2 = r1['sig'], r2['sig']
    c1, c2 = s1['cats'], s2['cats']
    fz = [k for k in zs if k in r1['feat'] and k in r2['feat']]
    dist = math.sqrt(sum(((r1['feat'][k] - r2['feat'][k]) / zs[k]) ** 2 for k in fz) / max(1, len(fz)))
    return {'motif_int_sim': 1 - _lev(s1['motif_int'], s2['motif_int']),
            'motif_rhythm_sim': _jac(s1['motif_on'], s2['motif_on']),
            'harm3_sim': _jac(s1['deg3'], s2['deg3']),
            'cat_same': sum(c1[k] == c2[k] for k in c1) / len(c1),
            'feat_dist': dist}


def _ms(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return (float('nan'), float('nan'), 0)
    m = st.mean(xs)
    se = st.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else float('nan')
    return (m, se, len(xs))


def cmd_analyze(a) -> int:
    d = json.loads(Path(a.json).read_text(encoding='utf-8'))
    lines = []
    p = lines.append
    slots = [(s['set_seed'], sl) for s in d['sets'] for sl in s['slots'] if len(sl['cands']) >= 3]
    allc = [c for _, sl in slots for c in sl['cands']]
    p(f"# {d['genre']}: {len(d['sets'])} sets x {d['n']} slots, best-of-{d['cands']}; {len(slots)} slots with 3+ "
      f"candidates, {len(allc)} candidates (mean {len(allc) / max(1, len(slots)):.1f} per slot)")
    sc = [c['score'] for c in allc]
    best = [next(c for c in sl['cands'] if c['seed'] == sl['best']) for _, sl in slots]
    first = [next(c for c in sl['cands'] if c['seed'] == sl['first']) for _, sl in slots]
    p(f"score: pool mean {st.mean(sc):.2f} sd {st.pstdev(sc):.2f} (min {min(sc)}, max {max(sc)}); chosen best mean "
      f"{st.mean(c['score'] for c in best):.2f}; first (best-of-1) mean {st.mean(c['score'] for c in first):.2f}; "
      f"within-slot score sd {st.mean(st.pstdev([c['score'] for c in sl['cands']]) for _, sl in slots):.2f}; "
      f"best - 2nd {st.mean(sl['cands'][0]['score'] - sl['cands'][1]['score'] for _, sl in slots):.2f}; "
      f"hard-capped candidates {sum(bool(c['hard']) for c in allc)} of {len(allc)}")
    # -- which score metrics discriminate: share out of range, the points they cost, how often best vs pool differs
    p("")
    capf = sum(bool(next(c for c in sl['cands'] if c['seed'] == sl['first'])['hard']) for _, sl in slots)
    capb = sum(bool(next(c for c in sl['cands'] if c['seed'] == sl['best'])['hard']) for _, sl in slots)
    p(f"hard-capped picks: first (best-of-1) {capf} of {len(slots)} slots, chosen best {capb}")
    p("")
    p("## The score's metrics on the pool (sub < 1 = outside its range)")
    p("")
    p("variance share = the metric's share of the within-slot variance of the pre-cap weighted mean (covariance "
      "decomposition: what the ranking actually selects on, the hard cap aside)")
    p("")
    p("| metric | weight | out of range (pool) | out (chosen) | mean pts lost / cand | share of within-slot score variance |")
    p("|---|---|---|---|---|---|")
    from agentsound.endless.genres import SCORES
    from agentsound.endless import genres as G
    table = SCORES[G.get(d['genre']).style]
    den = sum(v[2] for k, v in table.items())
    # within-slot variance of the score explained by each metric's lost points (covariance share)
    tot_var = []
    contrib = Counter()
    for _, sl in slots:
        cs = sl['cands']
        if any(c['hard'] for c in cs):
            pass
        s_ = [sum(100 * table[k][2] * c['sub'].get(k, 1.0) / den for k in table) for c in cs]   # (pre-cap mean)
        ms_ = st.mean(s_)
        tot_var.append(sum((x - ms_) ** 2 for x in s_))
        for k in table:
            xs = [100 * table[k][2] * c['sub'].get(k, 1.0) / den for c in cs]
            mx = st.mean(xs)
            contrib[k] += sum((x - mx) * (y - ms_) for x, y in zip(xs, s_))
    tv = sum(tot_var) or 1
    rows = []
    for k, spec in table.items():
        subs = [c['sub'].get(k) for c in allc if k in c['sub']]
        if not subs:
            continue
        bs = [c['sub'].get(k) for c in best if k in c['sub']]
        lost = st.mean(100 * spec[2] * (1 - s) / den for s in subs)
        rows.append((contrib[k] / tv, k, spec, sum(s < 1 for s in subs) / len(subs),
                     sum(s < 1 for s in bs) / max(1, len(bs)), lost))
    for share, k, spec, out_p, out_b, lost in sorted(rows, reverse=True):
        p(f"| {k} | {spec[2]}{' HARD' if spec[3] else ''} | {out_p:.2f} | {out_b:.2f} | {lost:.2f} | {share:.2f} |")
    never = [k for _, k, _, o, _, _ in rows if o == 0]
    p("")
    p(f"never out of range in the pool ({len(never)} of {len(rows)} metrics: zero selection pressure - guaranteed by "
      f"construction or the plan): {', '.join(never)}")
    # -- per feature: the within-slot selection effect
    p("")
    p("## Selection effect per feature (within slot: z = (x - slot mean) / slot sd)")
    p("")
    p("shift = mean z of the chosen (0 = no direction; + = selection raises it); |z| ratio = E|z_best| / E|z_pool| "
      "(1 = random, < 1 = pulled to the slot's middle, > 1 = toward the extremes); var ratio = mean z_best^2 / mean "
      "z_pool^2 (within-slot variance kept by the chosen); pct = the chosen one's mean percentile in its pool (0.5 = "
      "random); total-var ratio = the variance of the chosen across all slots / the first (best-of-1) picks'.")
    p("")
    p("| feature | shift (se) | abs-z ratio | var ratio | pct | total var best / first | mean best / first / pool |")
    p("|---|---|---|---|---|---|---|")
    feats = sorted({k for c in allc for k in c['feat']})
    eff = {}
    for k in feats + [f"score:{m}" for m in table]:
        zb, zall, pct, zf = [], [], [], []
        for _, sl in slots:
            get = (lambda c: c['val'].get(k[6:])) if k.startswith('score:') else (lambda c: c['feat'].get(k))
            xs = [get(c) for c in sl['cands']]
            if any(x is None for x in xs):
                continue
            m_, s_ = st.mean(xs), st.pstdev(xs)
            if s_ < 1e-9:
                continue
            xb = get(next(c for c in sl['cands'] if c['seed'] == sl['best']))
            xf = get(next(c for c in sl['cands'] if c['seed'] == sl['first']))
            zb.append((xb - m_) / s_)
            zf.append((xf - m_) / s_)
            zall += [(x - m_) / s_ for x in xs]
            pct.append((sum(x < xb for x in xs) + 0.5 * (sum(x == xb for x in xs) - 1)) / max(1, len(xs) - 1))
        if len(zb) < 8:
            continue
        sh = _ms(zb)
        ar = st.mean(abs(z) for z in zb) / max(1e-9, st.mean(abs(z) for z in zall))
        vr = st.mean(z * z for z in zb) / max(1e-9, st.mean(z * z for z in zall))
        get = (lambda c: c['val'].get(k[6:])) if k.startswith('score:') else (lambda c: c['feat'].get(k))
        xb = [get(c) for c in best if get(c) is not None]
        xf = [get(c) for c in first if get(c) is not None]
        xp = [get(c) for c in allc if get(c) is not None]
        tvr = st.pvariance(xb) / max(1e-12, st.pvariance(xf))
        eff[k] = dict(shift=sh[0], se=sh[1], n=sh[2], absz=ar, var=vr, pct=st.mean(pct), tvr=tvr,
                      mb=st.mean(xb), mf=st.mean(xf), mp=st.mean(xp))
    for k, e in sorted(eff.items(), key=lambda kv: (kv[0].startswith('score:'), -abs(kv[1]['shift']))):
        flag = ' **' if abs(e['shift']) > 2.5 * e['se'] else ''
        p(f"| {k}{flag} | {e['shift']:+.2f} ({e['se']:.2f}) | {e['absz']:.2f} | {e['var']:.2f} | {e['pct']:.2f} | "
          f"{e['tvr']:.2f} | {e['mb']:.3g} / {e['mf']:.3g} / {e['mp']:.3g} |")
    ind = [e for k, e in eff.items() if not k.startswith('score:')]
    p("")
    p(f"independent features ({len(ind)}): median |z| ratio {st.median(e['absz'] for e in ind):.2f}, median var "
      f"ratio {st.median(e['var'] for e in ind):.2f}, median total-var ratio best/first "
      f"{st.median(e['tvr'] for e in ind):.2f}; features with a significant shift (|shift| > 2.5 se): "
      f"{sum(abs(e['shift']) > 2.5 * e['se'] for e in ind)}")
    # -- within-slot similarity: do the chosen sit at the pool's centre (the "typical" candidate)?
    zs = {}
    for k in feats:
        xs = [c['feat'][k] for c in allc if k in c['feat']]
        s_ = st.pstdev(xs)
        if s_ > 1e-9:
            zs[k] = s_
    cen_b, cen_f, cen_p = [], [], []
    for _, sl in slots:
        cs = sl['cands']
        mean_d = {c['seed']: st.mean(sim(c, o, zs)['feat_dist'] for o in cs if o is not c) for c in cs}
        cen_b.append(mean_d[sl['best']])
        cen_f.append(mean_d[sl['first']])
        cen_p.append(st.mean(mean_d.values()))
    p("")
    p(f"typicality (the mean z-distance of a candidate to the other candidates of its slot over all independent "
      f"features; lower = more typical): chosen {st.mean(cen_b):.3f}, first {st.mean(cen_f):.3f}, pool "
      f"{st.mean(cen_p):.3f}; chosen - pool paired {_ms([b - q for b, q in zip(cen_b, cen_p)])[0]:+.3f} se "
      f"{_ms([b - q for b, q in zip(cen_b, cen_p)])[1]:.3f}")
    # -- across a set: the pairwise similarity of the chosen tunes
    p("")
    p("## Set-level similarity (the mean over the pairs of a set's chosen tunes; best-of-N vs best-of-1 vs random "
      "sets)")
    p("")
    p("| measure | best-of-N set | best-of-1 set | random sets (mean of 200) | best - first paired (se) | "
      "best vs random: z |")
    p("|---|---|---|---|---|---|")
    rng = random.Random(7)
    meas = ('motif_int_sim', 'motif_rhythm_sim', 'harm3_sim', 'cat_same', 'feat_dist')
    per = {m: {'b': [], 'f': [], 'r': [], 'rsd': []} for m in meas}
    for s in d['sets']:
        sls = [sl for sl in s['slots'] if sl['cands']]
        B = [next(c for c in sl['cands'] if c['seed'] == sl['best']) for sl in sls]
        F = [next(c for c in sl['cands'] if c['seed'] == sl['first']) for sl in sls]

        def setsim(T):
            ps = [sim(x, y, zs) for x, y in combinations(T, 2)]
            return {m: st.mean(q[m] for q in ps) for m in meas}
        sb, sf = setsim(B), setsim(F)
        rs = [setsim([rng.choice(sl['cands']) for sl in sls]) for _ in range(200)]
        for m in meas:
            per[m]['b'].append(sb[m])
            per[m]['f'].append(sf[m])
            per[m]['r'].append(st.mean(r[m] for r in rs))
            per[m]['rsd'].append(st.pstdev([r[m] for r in rs]))
    for m in meas:
        q = per[m]
        dd = _ms([b - f for b, f in zip(q['b'], q['f'])])
        z = st.mean((b - r) / max(1e-9, s) for b, r, s in zip(q['b'], q['r'], q['rsd']))
        p(f"| {m} | {st.mean(q['b']):.3f} | {st.mean(q['f']):.3f} | {st.mean(q['r']):.3f} | {dd[0]:+.3f} "
          f"({dd[1]:.3f}) | {z:+.2f} |")
    p("")
    p("(similarities: higher = more alike; feat_dist: higher = more different. z: the chosen set against the "
      "random sets' spread, averaged over the set seeds.)")
    # -- what varies within a slot at all (the plan pins the rest)
    p("")
    var_cats = Counter()
    for _, sl in slots:
        for k in sl['cands'][0]['sig']['cats']:
            if len({str(c['sig']['cats'][k]) for c in sl['cands']}) > 1:
                var_cats[k] += 1
    p(f"categorical draws that vary between the candidates of a slot (slots of {len(slots)}): "
      + ', '.join(f"{k} {v}" for k, v in var_cats.most_common()) + "; the others are pinned by the set plan")
    text = '\n'.join(lines)
    print(text)
    if a.md:
        Path(a.md).write_text(text + '\n', encoding='utf-8')
    if a.eff:
        Path(a.eff).write_text(json.dumps(eff, indent=1), encoding='utf-8')
    return 0


# ------------------------------------------------------------------------------------------------ 3. the judges

def _set_brief(n: int) -> str:
    src = (HERE / 'JUDGE_SET.md').read_text(encoding='utf-8')
    head = (f"# Blind judging: two evenings' programmes (solo piano)\n\n"
            f"You are a judge in a blind listening panel. You receive **two programmes**, **set X** and **set Y**. "
            f"Each is an evening's recital of **{n} solo piano pieces by one composer** in the new-age / "
            f"pop-classical style (the gentle, song-like solo piano of Yiruma or Einaudi: a singable right-hand tune "
            f"over flowing broken chords), played in the order given (piece 1 opens the evening, piece {n} closes "
            f"it). The two programmes are by two different composers.\n\n"
            f"You cannot hear the music: each piece comes as a text packet with its chord chart, its notation as "
            f"played (the right hand's top line, every left-hand attack) and an analysis of the rendered audio. All "
            f"pieces were played by the same performance model, on the same sampled piano, through the same mix "
            f"chain - so judge the **music** and its **writing for the piano**.\n\n")
    body = src[src.index('Your task is about'):]
    body = body.replace('`01.txt` ... `08.txt`', f'`01.txt` ... `{n:02d}.txt`')
    body = body.replace('after piece 8', f'after piece {n}').replace('all eight pieces', f'all {n} pieces')
    body = body.replace('all eight in order', f'all {n} in order').replace('the eight pieces', f'the {n} pieces')
    body = body.replace('one piece eight times', f'one piece {n} times').replace('(who plays what over what)',
                                                                                  '(what each hand plays)')
    body = body.replace('<2-8>', f'<2-{n}>').replace('<1-8>', f'<1-{n}>').replace('(2-8)', f'(2-{n})')
    # the packet description: the piano packet's own
    pk = src[src.index('## What a packet holds'):src.index('## Your task')]
    body = body.replace(pk, '')
    piano_pk = ("## What a packet holds\n\n- **Header**: key, meter, tempo, length, the section layout in bars (intro, "
                "A1 A2 ... = the theme's statements, B1 B2 = the chorus / contrast, inter, build, climax, coda).\n"
                "- **Chord chart**: one cell per bar per section.\n- **Notation**, bar by bar: `RH` the right hand's "
                "top line `position:note duration velocity [+n]` (+n = n more right-hand notes struck with it), `LH` "
                "every left-hand attack.\n- **Analysis** of the rendered audio: loudness, tempo, the hands' balance, "
                "density per section, the highest and lowest notes.\n\n")
    may = ("## What you may read\n\nOnly this file and the packets in `set_X/` and `set_Y/` (`01.txt` ... "
           f"`{n:02d}.txt`, in programme order). Do **not** open any other file, do not search outside this "
           "folder.\n\n")
    return head + may + piano_pk + body


PIECE_EXTRA = """
Then **the masterpiece question** - an ABSOLUTE bar, not relative to the other packets: how close is this piece to a
true masterpiece of its repertoire (the best of Yiruma, Einaudi, Sakamoto's piano pieces, the piano songs people keep
playing)?

- **masterpiece** 1-10: 10 = a piece the world keeps playing, 7 = a solid professional album track, 5 = competent
  but forgettable, 3 = a student exercise, 1 = broken.
- **missing**: one located sentence - what is missing for this piece to be a masterpiece (`bars <a-b>: ...`).
"""


def _piece_brief() -> str:
    src = (HERE / 'JUDGE_NEWAGE.md').read_text(encoding='utf-8')
    src = src.replace("At the end, a section **Count**", PIECE_EXTRA.strip() + "\n\nAt the end, a section **Count**")
    src = src.replace("shared: <IDs> | none\n", "shared: <IDs> | none\nmasterpiece: <1-10>\nmissing: bars <a-b>: ...\n")
    return src


def cmd_deal(a) -> int:
    """The packets (make_packets_paired.dump: the new-age packet), the per-piece quality panels (both versions of a
    slot in the SAME panel: a within-judge paired diff) and the set-level pairs."""
    import judge_newage as jn
    import make_packets_paired as mpp
    jroot = Path(a.jroot).resolve()
    jroot.mkdir(parents=True, exist_ok=True)
    packs = {}                                         # {setname: {'best': [items], 'first': [items]}}
    for spec in a.set:
        name, _, dirs = spec.partition('=')
        db, df = dirs.split(',')
        packs[name] = {}
        for code, folder in (('best', db), ('first', df)):
            items = [f"{code}-{int(x.name[:3]):03d}={x}" for x in sorted(Path(folder).iterdir())
                     if x.is_dir() and re.match(r'\d{3}-', x.name) and (x / 'tune.json').exists()]
            f = jroot / f"PACKETS_{name}_{code}.json"
            if not f.exists():
                mpp.dump(f, items)
            packs[name][code] = [v for _, v in sorted(json.loads(f.read_text(encoding='utf-8')).items())]
    key = {'round': a.round, 'pieces': {}, 'sets': {}}
    # (a) the per-piece quality panels: one panel per set, both codes' pieces shuffled, the IDs random
    rng = random.Random(f"bestofn-{a.round}")
    used = set()
    lens = list(jn.JUDGES)[:a.judges]
    for name, P in packs.items():
        items = [(code, k + 1, x) for code in ('best', 'first') for k, x in enumerate(P[code])]
        rng.shuffle(items)
        panel = jroot / 'pieces' / name
        for code, slot, x in items:
            while True:
                pid = ''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(4))
                if pid not in used:
                    used.add(pid)
                    break
            key['pieces'][pid] = {'set': name, 'code': code, 'slot': slot, 'path': x['path'], 'title': x.get('title')}
            x['_id'] = pid
        for j in lens:
            d = panel / j
            if d.exists():                             # (dealt before: the IDs are deterministic - kept as read)
                continue
            (d / 'packets').mkdir(parents=True)
            (d / 'JUDGE.md').write_text(_piece_brief(), encoding='utf-8')
            for code, slot, x in items:
                (d / 'packets' / f"{x['_id']}.txt").write_text(x['text'], encoding='utf-8')
            out = jroot / 'pieces' / 'verdicts' / f"{name}_{j}.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            pr = jn.prompt(j, d, out).replace("then ## Count, then ## Advice", "then ## Count, then ## Advice; "
                                                                               "every packet with its masterpiece "
                                                                               "and missing lines")
            (d / 'prompt.txt').write_text(pr, encoding='utf-8')
    # (b) the set-level pairs: per set, X / Y drawn per judge
    for name, P in packs.items():
        n = len(P['best'])
        key['sets'][name] = {'judges': {}}
        for j in lens:
            r = random.Random(f"bestofn-set-{a.round}:{name}:{j}")
            x_code = ('best', 'first')[r.randrange(2)]
            first = 'XY'[r.randrange(2)]
            asg = {'X': x_code, 'Y': 'first' if x_code == 'best' else 'best', 'first': first}
            d = jroot / 'sets' / name / j
            key['sets'][name]['judges'][j] = asg
            if d.exists():                             # (dealt before: kept)
                continue
            for lab in ('X', 'Y'):
                (d / f"set_{lab}").mkdir(parents=True)
                for k, x in enumerate(P[asg[lab]]):
                    (d / f"set_{lab}" / f"{k + 1:02d}.txt").write_text(x['text'], encoding='utf-8')
            (d / 'JUDGE.md').write_text(_set_brief(n), encoding='utf-8')
            import set_round as sr
            lens_na = jn.LENS[jn.JUDGES[j]]
            out = jroot / 'sets' / 'verdicts' / f"{name}_{j}.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            (d / 'prompt.txt').write_text(sr._prompt(lens_na, d, out, first), encoding='utf-8')
            key['sets'][name]['judges'][j] = asg
    (jroot / 'KEY.json').write_text(json.dumps(key, indent=1) + '\n', encoding='utf-8')
    print(f"dealt: {len(key['pieces'])} pieces, {sum(len(s['judges']) for s in key['sets'].values())} set verdicts "
          f"-> {jroot}")
    return 0


def _parse_piece(text: str) -> dict:
    out = {}
    for m in re.finditer(r'^##\s+([A-Z]{4})\s*$(.*?)(?=^##\s|\Z)', text, re.M | re.S):
        r = {}
        for dim in ('melody', 'harmony', 'form', 'development', 'performance', 'overall', 'memorable',
                    'masterpiece'):
            x = re.search(rf'^\W*{dim}\W*:\s*\**\s*(\d+(?:\.\d+)?)', m.group(2), re.I | re.M)
            if x:
                r[dim] = float(x.group(1))
        mi = re.search(r'^\W*missing\W*:\s*(.*)$', m.group(2), re.I | re.M)
        r['missing'] = mi.group(1).strip() if mi else ''
        out[m.group(1)] = r
    return out


def cmd_score(a) -> int:
    import set_round as sr
    jroot = Path(a.jroot).resolve()
    key = json.loads((jroot / 'KEY.json').read_text(encoding='utf-8'))
    out = []
    p = out.append
    # (a) per piece: within judge, best minus first for the same set slot
    dims = ('melody', 'harmony', 'form', 'development', 'performance', 'overall', 'memorable', 'masterpiece')
    rat = {}                                            # {(set, judge): {pid: ratings}}
    for f in sorted((jroot / 'pieces' / 'verdicts').glob('*.md')):
        s, _, j = f.stem.partition('_')
        rat[(s, j)] = _parse_piece(f.read_text(encoding='utf-8'))
    p(f"## Per piece ({len(rat)} verdict files)")
    p("")
    p("| dim | best-of-8 mean | best-of-1 mean | paired diff (judge x slot) | se | n | judge-level diff se | t |")
    p("|---|---|---|---|---|---|---|---|")
    summ = {}
    for dim in dims:
        diffs, mb, mf, per_j = [], [], [], {}
        for (s, j), R in rat.items():
            by = {}
            for pid, r in R.items():
                k = key['pieces'].get(pid)
                if k and dim in r:
                    by[(k['slot'], k['code'])] = r[dim]
                    (mb if k['code'] == 'best' else mf).append(r[dim])
            for slot in {sl for sl, _ in by}:
                if (slot, 'best') in by and (slot, 'first') in by:
                    dd = by[(slot, 'best')] - by[(slot, 'first')]
                    diffs.append(dd)
                    per_j.setdefault((s, j), []).append(dd)
        m, se, n = _ms(diffs)
        jm = _ms([st.mean(v) for v in per_j.values()])
        summ[dim] = (m, se, n)
        p(f"| {dim} | {_ms(mb)[0]:.2f} | {_ms(mf)[0]:.2f} | {m:+.2f} | {se:.2f} | {n} | {jm[1]:.2f} | "
          f"{m / jm[1] if jm[1] and jm[1] == jm[1] else float('nan'):+.1f} |")
    # per slot: the panel's mean diff (overall)
    p("")
    p("per slot (overall, the panel's mean best - first; + = best-of-8 rated higher):")
    for s in sorted({k['set'] for k in key['pieces'].values()}):
        row = []
        for slot in sorted({k['slot'] for k in key['pieces'].values() if k['set'] == s}):
            ds = []
            for (s2, j), R in rat.items():
                if s2 != s:
                    continue
                by = {key['pieces'][pid]['code']: r.get('overall') for pid, r in R.items()
                      if pid in key['pieces'] and key['pieces'][pid]['slot'] == slot}
                if by.get('best') is not None and by.get('first') is not None:
                    ds.append(by['best'] - by['first'])
            row.append(f"{slot}: {_ms(ds)[0]:+.2f}")
        p(f"- set {s}: " + ', '.join(row))
    # (b) the set level: set_round's parser, its CI
    p("")
    vdir = jroot / 'sets' / 'verdicts'
    rows = []
    for s, S in key['sets'].items():
        for j, asg in S['judges'].items():
            f = vdir / f"{s}_{j}.md"
            if not f.exists():
                continue
            v = sr.parse(f.read_text(encoding='utf-8'))
            lab = {asg['X']: 'X', asg['Y']: 'Y'}
            rows.append({'set': s, 'judge': j, 'keep': asg[v['keep']] if v['keep'] else None,
                         'strength': v['strength'], 'first_code': asg[asg['first']], 'why': v['why'],
                         **{c: v[lab[c]] for c in ('best', 'first')}})
    ch = [r for r in rows if r['keep']]
    k, n = sum(r['keep'] == 'best' for r in ch), len(ch)
    w, e = sr.wilson(k, n), sr.exact(k, n)
    p(f"## Set level ({len(rows)} verdicts)")
    p("")
    p(f"forced choice: best-of-8 programme kept by {k} of {n} = {k / max(1, n):.2f}; 95 % CI Wilson {w[0]:.2f}-"
      f"{w[1]:.2f}, exact {e[0]:.2f}-{e[1]:.2f}")
    sw = _ms([(r['strength'] or 0) * (1 if r['keep'] == 'best' else -1) for r in ch])
    p(f"strength-signed (+ = best-of-8): {sw[0]:+.2f} se {sw[1]:.2f}; the programme read first kept "
      f"{sum(r['keep'] == r['first_code'] for r in ch)} of {n}")
    for dim in ('variety', 'coherence'):
        dd = _ms([r['best'][dim] - r['first'][dim] for r in rows
                  if r['best'][dim] is not None and r['first'][dim] is not None])
        p(f"{dim}: best-of-8 {_ms([r['best'][dim] for r in rows])[0]:.2f}, best-of-1 "
          f"{_ms([r['first'][dim] for r in rows])[0]:.2f}, paired {dd[0]:+.2f} se {dd[1]:.2f} (n {dd[2]})")
    for c in ('best', 'first'):
        sa = [r[c]['same_again'] for r in rows if r[c]['same_again'] is not None]
        p(f"same piece again, {c}: positions {sorted(int(x) for x in sa)}; never {sum(r[c]['same_never'] for r in rows)}"
          f"; tells per programme {_ms([len(r[c]['tells']) for r in rows])[0]:.1f}")
    for s in key['sets']:
        rs = [r for r in ch if r['set'] == s]
        p(f"- set {s}: best-of-8 kept {sum(r['keep'] == 'best' for r in rs)} of {len(rs)}")
    p("")
    p("why (per verdict):")
    for r in rows:
        p(f"- {r['set']} {r['judge']}: kept {r['keep']} ({r['strength']}): {r['why']}")
    text = '\n'.join(out)
    print(text)
    if a.md:
        Path(a.md).write_text(text + '\n', encoding='utf-8')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('pool')
    s.add_argument('--genre', default='new-age-piano')
    s.add_argument('--sets', required=True)
    s.add_argument('--n', type=int, default=8)
    s.add_argument('--cands', type=int, default=8)
    s.add_argument('--json', required=True)
    s = sub.add_parser('analyze')
    s.add_argument('json')
    s.add_argument('--md')
    s.add_argument('--eff')
    s = sub.add_parser('deal')
    s.add_argument('round')
    s.add_argument('jroot')
    s.add_argument('--set', action='append', required=True)
    s.add_argument('--judges', type=int, default=7)
    s = sub.add_parser('score')
    s.add_argument('jroot')
    s.add_argument('--md')
    a = ap.parse_args()
    return {'pool': cmd_pool, 'analyze': cmd_analyze, 'deal': cmd_deal, 'score': cmd_score}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
