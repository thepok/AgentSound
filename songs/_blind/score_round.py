"""Score a blind round: the judges' answers against the KEY (nobody else reads the KEY).

    python songs/_blind/score_round.py KEY_newage.json VERDICTS_DIR [--tells] [--refs NAME,NAME]
    python songs/_blind/score_round.py KEY_newage.json VERDICTS_DIR --paired NEW,OLD   # a paired round (g14 on;
                                                       # the versions in different panels - paired_split: g15, o2)

VERDICTS_DIR holds one <judge>.md per judge in JUDGE.md's answer format. Prints per judge: right / total, the
confidence range, the misses by kind, how many packets it called generated and its '## Count' estimate (when the
brief asks for one) against the truth; per generated packet the judges it fooled (called it composed); then per
source kind the verdict counts, and every reason the judges gave for the GENERATED packets (the tells to fix) with
the judge and the packet's source folder name.
A QUALITY round (round g3 on, JUDGE_NEWAGE.md: every packet rated 1-10 per dimension, no verdict) is detected by its
'overall:' lines: per dimension the mean for the generated packets and for the references (the hidden anchors) and
the gap; per judge its means and '## Count'; per packet its mean ratings (sorted by overall); with --tells every
judge's 'fix' and 'why' per generated packet. Round g4 on, the memorable moment (JUDGE_NEWAGE.md: moment / memorable
0-3 / recurs / shared): the mean memorable for the generated packets and the references, the hit rate (the share of
the generated packets' named moments whose bars overlap a planned signature move's bars - the KEY's 'moves', from
perform._sign; the ostinato, a whole section's texture, counted apart) and the 'shared' flags (a judge naming
another generated packet with the same gesture: a template tell, want 0). The orchestra QUALITY rounds
(JUDGE_ORCH_Q.md: orchestration and life instead of performance - the dimensions are read from the answers) with two
generators in one round (the KEY's 'code'): the means per generator (groups). Round g7 on (three hidden references, the
yardstick's drift averaged): the gap again against each reference alone and, with --refs (source folder names), against
that subset only (g7: embers + tide, the g4-g6 pair).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse(text: str) -> dict:
    out = {}
    for m in re.finditer(r'^##\s+([A-Z]{4})\s*$(.*?)(?=^##\s|\Z)', text, re.M | re.S):
        body = m.group(2)
        v = re.search(r'verdict:\s*\**\s*(generated|composed)', body, re.I)
        c = re.search(r'confidence:\s*\**\s*(\d+)', body, re.I)
        reasons = re.findall(r'^\s*\d\.\s+(.*)$', body, re.M)
        if v:
            out[m.group(1)] = {'verdict': v.group(1).lower(), 'conf': int(c.group(1)) if c else None,
                               'reasons': reasons}
    return out


def count(text: str):
    """The judge's '## Count' estimate ('generated: N of M'), None when it gave none."""
    m = re.search(r'^##\s+Count\s*$(.*?)(?=^##\s|\Z)', text, re.M | re.S | re.I)
    n = re.search(r'generated:\s*\**\s*(\d+)', m.group(1), re.I) if m else None
    return int(n.group(1)) if n else None


ALL_DIMS = ('melody', 'harmony', 'form', 'development', 'performance', 'orchestration', 'life', 'overall')
DIMS = ('melody', 'harmony', 'form', 'development', 'performance', 'overall')
"""The rated dimensions: the new-age brief's (JUDGE_NEWAGE.md); a round whose answers rate others (JUDGE_ORCH_Q.md:
orchestration, life instead of performance) sets DIMS to the ones its answers hold (main: _dims)."""


def _dims(vdir: Path) -> tuple:
    """The dimensions the round's answers rate (ALL_DIMS order)."""
    seen = set()
    for f in vdir.glob('*.md'):
        for a in parse_ratings(f.read_text(encoding='utf-8'), ALL_DIMS).values():
            seen |= set(a) & set(ALL_DIMS)
    return tuple(d for d in ALL_DIMS if d in seen) or DIMS


def parse_ratings(text: str, dims: tuple | None = None) -> dict:
    """{ID: {dimension: rating, 'fix': str, 'why': str}} of a quality round's answer."""
    out = {}
    for m in re.finditer(r'^##\s+([A-Z]{4})\s*$(.*?)(?=^##\s|\Z)', text, re.M | re.S):
        body, r = m.group(2), {}
        for d in dims or DIMS:
            x = re.search(rf'^\W*{d}\W*:\s*\**\s*(\d+(?:\.\d+)?)', body, re.I | re.M)
            if x:
                r[d] = float(x.group(1))
        for k in ('fix', 'why', 'moment', 'recurs', 'shared', 'template', 'missing'):
            x = re.search(rf'^\W*{k}\W*:\s*(.*)$', body, re.I | re.M)
            r[k] = x.group(1).strip() if x else ''
        x = re.search(r'^\W*memorable\W*:\s*\**\s*(\d+(?:\.\d+)?)', body, re.I | re.M)
        if x:
            r['memorable'] = float(x.group(1))
        # (round o11: the masterpiece question - an absolute score, 10 = canon repertoire)
        x = re.search(r'^\W*masterpiece\W*:\s*\**\s*(\d+(?:\.\d+)?)', body, re.I | re.M)
        if x:
            r['masterpiece'] = float(x.group(1))
        if 'overall' in r:
            out[m.group(1)] = r
    return out


def quality(key: dict, vdir: Path, tells: bool, refs: list | None = None) -> int:
    """The quality round's tables (the module docstring)."""
    import statistics as st
    per: dict = {i: {d: [] for d in DIMS} for i in key}
    truth = sum(v['source'] == 'generated' for v in key.values())
    print(f"judge          " + ' '.join(f"{d[:5]:>6}" for d in DIMS) + "   (gen / ref means)   count")
    fixes = []
    for f in sorted(vdir.glob('*.md')):
        text = f.read_text(encoding='utf-8')
        ans = parse_ratings(text)
        cells = []
        for d in DIMS:
            g = [a[d] for i, a in ans.items() if d in a and key.get(i, {}).get('source') == 'generated']
            r_ = [a[d] for i, a in ans.items() if d in a and key.get(i, {}).get('source') == 'composed']
            cells.append(f"{st.mean(g) if g else 0:4.1f}/{st.mean(r_) if r_ else 0:4.1f}")
        for i, a in ans.items():
            if i in per:
                for d in DIMS:
                    if d in a:
                        per[i][d].append(a[d])
                if key[i]['source'] == 'generated':
                    fixes.append((f.stem, i, Path(key[i]['path']).name, a))
        est = count(text)
        print(f"{f.stem:<14} " + ' '.join(cells) + f"   count {est} (truth {truth} of {len(key)})")
    print('\ndimension      generated  references  gap (ref - gen)')
    for d in DIMS:
        g = [x for i in key if key[i]['source'] == 'generated' for x in per[i][d]]
        r_ = [x for i in key if key[i]['source'] == 'composed' for x in per[i][d]]
        if g:
            gm, rm = st.mean(g), (st.mean(r_) if r_ else float('nan'))
            print(f"{d:<14} {gm:9.2f}  {rm:10.2f}  {rm - gm:+.2f}")
    names = sorted({Path(key[i]['path']).name for i in key if key[i]['source'] == 'composed'})
    subsets = [[n] for n in names] + ([refs] if refs else [])
    if len(names) > 1:
        print('\nthe gap against: ' + ' | '.join('+'.join(x) for x in subsets) + '   (overall: ref mean, gap)')
        g = [x for i in key if key[i]['source'] == 'generated' for x in per[i]['overall']]
        for sub in subsets:
            r_ = [x for i in key if key[i]['source'] == 'composed' and Path(key[i]['path']).name in sub
                  for x in per[i]['overall']]
            dims = []
            for d in DIMS:
                gd = [x for i in key if key[i]['source'] == 'generated' for x in per[i][d]]
                rd = [x for i in key if key[i]['source'] == 'composed' and Path(key[i]['path']).name in sub
                      for x in per[i][d]]
                if gd and rd:
                    dims.append(f"{d[:5]} {st.mean(rd) - st.mean(gd):+.2f}")
            if g and r_:
                print(f"  {'+'.join(sub):<40} {st.mean(r_):5.2f}  {st.mean(r_) - st.mean(g):+.2f}   " + ', '.join(dims))
    relative(key, vdir, refs)
    print('\npacket  source     ' + ' '.join(f"{d[:5]:>6}" for d in DIMS) + '  folder')
    rows = sorted(key, key=lambda i: -(st.mean(per[i]['overall']) if per[i]['overall'] else 0))
    for i in rows:
        print(f"{i}    {key[i]['source']:<10} " + ' '.join(
            f"{st.mean(per[i][d]) if per[i][d] else 0:6.1f}" for d in DIMS) + f"  {Path(key[i]['path']).name}")
    moments(key, vdir)
    if tells:
        for j, i, name, a in fixes:
            print(f"\n[{j}] {i} {name}: overall {a.get('overall')}\n   fix: {a['fix'][:400]}\n   why: {a['why'][:400]}")
    return 0


def rel_scores(key: dict, vdir: Path, refs: list | None = None) -> dict:
    """The generated pieces relative to the references WITHIN each judge (round g12: the references' mean swung
    6.27-7.33 between rounds with the same three pieces - the yardstick moved as much as the generated set): per
    dimension, over the judges, the mean of
      rel  the judge's generated mean / its reference mean (1.0 = at the references' level);
      z    (generated mean - reference mean) / the sd of that judge's ratings of every packet in the round (its own
           scale: a harsh or a narrow judge counts alike; 0 = at the references, negative = under them);
      pct  the share of (generated, reference) pairs the judge rated the generated piece at least as high (a tie
           half; 0.5 = at the references).
    refs: the reference folder names to compare with (default all). -> {dimension: {'rel', 'z', 'pct', 'judges'}}."""
    import statistics as st
    out = {}
    answers = [parse_ratings(f.read_text(encoding='utf-8')) for f in sorted(vdir.glob('*.md'))]

    def is_ref(i):
        return key[i]['source'] == 'composed' and (not refs or Path(key[i]['path']).name in refs)
    for d in DIMS:
        rel, z, pct = [], [], []
        for ans in answers:
            g = [a[d] for i, a in ans.items() if d in a and key.get(i, {}).get('source') == 'generated']
            r_ = [a[d] for i, a in ans.items() if d in a and i in key and is_ref(i)]
            every = [a[d] for i, a in ans.items() if d in a and i in key]
            if not g or not r_:
                continue
            rel.append(st.mean(g) / st.mean(r_))
            sd = st.pstdev(every)
            if sd > 0:
                z.append((st.mean(g) - st.mean(r_)) / sd)
            pct.append(st.mean(1.0 if x > y else 0.5 if x == y else 0.0 for x in g for y in r_))
        if rel:
            out[d] = {'rel': st.mean(rel), 'z': st.mean(z) if z else float('nan'), 'pct': st.mean(pct),
                      'judges': len(rel)}
    return out


def relative(key: dict, vdir: Path, refs: list | None = None) -> None:
    """rel_scores printed: against all references and, with refs, that subset."""
    for sub in [None] + ([refs] if refs else []):
        r = rel_scores(key, vdir, sub)
        if not r:
            continue
        print(f"\nrelative to the references{' (' + '+'.join(sub) + ')' if sub else ''}, within each judge "
              f"({r['overall']['judges']} judges): rel = gen / ref, z = (gen - ref) / the judge's sd, pct = gen >= ref")
        for d in DIMS:
            if d in r:
                print(f"  {d:<14} rel {r[d]['rel']:.3f}   z {r[d]['z']:+.2f}   pct {r[d]['pct']:.2f}")


def _bars(text: str) -> list:
    """[(a, b)] bar spans named in a 'moment' / 'recurs' answer ('bars 33-36', 'bar 41', 'bars 5-6, 49-52')."""
    out = []
    for m in re.finditer(r'(\d+)\s*(?:[-\u2013]\s*(\d+))?', text.split(':')[0] if ':' in text else text):
        a = int(m.group(1))
        out.append((a, int(m.group(2)) if m.group(2) else a))
    return out


def moments(key: dict, vdir: Path) -> None:
    """The memorable-moment tables (round g4 on; the module docstring)."""
    import statistics as st
    rows = []
    for f in sorted(vdir.glob('*.md')):
        for i, a in parse_ratings(f.read_text(encoding='utf-8')).items():
            if i in key and 'memorable' in a:
                rows.append((f.stem, i, a))
    if not rows:
        return
    gen = [a['memorable'] for _, i, a in rows if key[i]['source'] == 'generated']
    ref = [a['memorable'] for _, i, a in rows if key[i]['source'] == 'composed']
    gm, rm = (st.mean(gen) if gen else 0.0), (st.mean(ref) if ref else float('nan'))
    print(f"\nmemorable (0-3)   generated {gm:.2f}   references {rm:.2f}   gap {rm - gm:+.2f}")
    hits = hits_ost = named = 0
    by_move: dict = {}
    per: dict = {}
    for j, i, a in rows:
        if key[i]['source'] != 'generated':
            continue
        mv = key[i].get('moves') or []
        spans = _bars(a.get('moment', '')) if a.get('moment', '').lower() not in ('', 'none') else []
        if not spans:
            continue
        named += 1
        over = [m for m in mv if any(x <= m[3] + 1 and y >= m[2] - 1 for x, y in spans)]
        moves_ = sorted({m[0] for m in over if m[0] != 'ostinato'})
        hits += bool(moves_)
        hits_ost += bool(over) and not moves_
        for m in moves_:
            by_move[m] = by_move.get(m, 0) + 1
        per.setdefault(i, []).append(','.join(moves_) or ('ostinato' if over else '-'))
    print(f"hit rate: {hits} of {named} named generated moments on a planned move's bars ({hits / max(1, named):.0%})"
          f"; {hits_ost} more only inside an ostinato section; by move: "
          + (', '.join(f"{k} {v}" for k, v in sorted(by_move.items())) or 'none'))
    gen_ids = {i for i in key if key[i]['source'] == 'generated'}
    flags = []
    for j, i, a in rows:
        sh = set(re.findall(r'\b([A-Z]{4})\b', a.get('shared', ''))) & gen_ids - {i}
        if i in gen_ids and sh:
            flags.append((j, i, sorted(sh)))
    print(f"shared flags among generated packets: {len(flags)}" + ''.join(f"\n   [{j}] {i} ~ {' '.join(sh)}"
                                                                     for j, i, sh in flags))
    print('\npacket  source     memorable  moments on moves (per judge)  planned moves')
    for i in sorted(key, key=lambda i: key[i]['source']):
        ms = [a['memorable'] for _, x, a in rows if x == i]
        planned = sorted({m[0] for m in key[i].get('moves') or []})
        print(f"{i}    {key[i]['source']:<10} {st.mean(ms) if ms else 0:6.2f}     {' '.join(per.get(i, [])):<28}  "
              f"{' '.join(planned)}")


def retro(argv: list) -> int:
    """--retro g3,g4,... --keys PATTERN --verdicts PATTERN [--refs NAME,NAME]: the raw gap and rel_scores per round
    ({g} in the patterns: the round), one row per round - the relative score retro-computed from earlier rounds."""
    import statistics as st
    rounds = argv[argv.index('--retro') + 1].split(',')
    kp, vp = argv[argv.index('--keys') + 1], argv[argv.index('--verdicts') + 1]
    refs = argv[argv.index('--refs') + 1].split(',') if '--refs' in argv else None
    print('round  judges  gen    ref   gap  | rel    z     pct  (overall, all refs)'
          + ('  | e+t: gap   rel    z     pct' if refs else '') + '  | rel / z per dimension (all refs)')
    for g in rounds:
        key = json.loads(Path(kp.format(g=g)).read_text(encoding='utf-8'))
        vdir = Path(vp.format(g=g))
        gen, ref, sub = [], [], []
        for f in sorted(vdir.glob('*.md')):
            for i, a in parse_ratings(f.read_text(encoding='utf-8')).items():
                if i in key and 'overall' in a:
                    (gen if key[i]['source'] == 'generated' else ref).append(a['overall'])
                    if key[i]['source'] == 'composed' and refs and Path(key[i]['path']).name in refs:
                        sub.append(a['overall'])
        r = rel_scores(key, vdir)
        line = (f"{g:<6} {r['overall']['judges']:>6}  {st.mean(gen):.2f}  {st.mean(ref):.2f}  {st.mean(ref) - st.mean(gen):+.2f}"
                f" | {r['overall']['rel']:.3f} {r['overall']['z']:+.2f}  {r['overall']['pct']:.2f}")
        if refs:
            rs = rel_scores(key, vdir, refs)
            line += (f"  | {st.mean(sub) - st.mean(gen):+.2f}  {rs['overall']['rel']:.3f} {rs['overall']['z']:+.2f}  "
                     f"{rs['overall']['pct']:.2f}") if sub and rs else '  | -'
        line += '  | ' + ' '.join(f"{d[:3]} {r[d]['rel']:.2f}/{r[d]['z']:+.2f}" for d in DIMS[:-1] if d in r)
        print(line)
    return 0


def paired(key: dict, vdir: Path, new: str, old: str) -> int:
    """--paired NEW,OLD (round g14 on, make_packets_paired.py): per seed slot the two codes' pieces rated by the same
    judges - per dimension the mean difference NEW - OLD over the (judge, slot) pairs, its sd and the pairs NEW won /
    tied / lost, then per slot the overall difference (the cleanest code signal: the set's luck is the same)."""
    import statistics as st
    slots: dict = {}
    for i, e in key.items():
        if e.get('code') in (new, old):
            slots.setdefault(e['slot'], {})[e['code']] = i
    if any(key[ids[new]].get('panel') != key[ids[old]].get('panel') for ids in slots.values()
           if new in ids and old in ids):
        return paired_split(key, vdir, new, old, slots)
    diffs = {d: [] for d in DIMS}
    per_slot: dict = {}
    for f in sorted(vdir.glob('*.md')):
        ans = parse_ratings(f.read_text(encoding='utf-8'))
        for s_, ids in sorted(slots.items()):
            a, b = ans.get(ids.get(new)), ans.get(ids.get(old))
            if not a or not b:
                continue
            for d in DIMS:
                if d in a and d in b:
                    diffs[d].append(a[d] - b[d])
            per_slot.setdefault(s_, []).append(a['overall'] - b['overall'])
    print(f"\npaired {new} - {old} (same judges, same seed slot): mean, sd, pairs won / tied / lost")
    for d in DIMS:
        x = diffs[d]
        if x:
            print(f"  {d:<14} {st.mean(x):+.2f}  sd {st.pstdev(x):.2f}  {sum(v > 0 for v in x)} / "
                  f"{sum(v == 0 for v in x)} / {sum(v < 0 for v in x)}   (n {len(x)})")
    print('  slot  ' + f"{new:>6} {old:>6}" + '   overall diff (judges)')
    for s_, ids in sorted(slots.items()):
        xs = per_slot.get(s_, [])
        if xs:
            print(f"  {s_}  {ids.get(new, '-'):>6} {ids.get(old, '-'):>6}   {st.mean(xs):+.2f}  "
                  f"({' '.join(f'{v:+.0f}' for v in xs)})")
    return 0


def paired_split(key: dict, vdir: Path, new: str, old: str, slots: dict) -> int:
    """The paired difference when the two versions of a slot went to DIFFERENT panels (round g15, the orchestra's
    o2; make_packets_paired.py deal --split): judge files <lens>_p<panel>.md; per (slot, lens) the NEW piece's
    rating by that lens in its panel minus the OLD piece's by the same lens in the other panel - raw, and
    normalised by each judge's own mean over the references (both panels rate them: a lenient panel cancels). Per
    dimension the mean, the sd and won / tied / lost; per slot the overall differences with the standard error over
    the slots (the set's luck stays the same: one set plan per code, the same seeds)."""
    import statistics as st
    rat: dict = {}
    for f in sorted(vdir.glob('*.md')):
        lens, _, pan = f.stem.rpartition('_p')
        if not lens:
            continue
        rat[(lens, pan)] = parse_ratings(f.read_text(encoding='utf-8'))
    refs = [i for i, e in key.items() if e.get('source') == 'composed']

    def ref_mean(lp, d):
        xs = [rat[lp][i][d] for i in refs if lp in rat and i in rat[lp] and d in rat[lp][i]]
        return st.mean(xs) if xs else 0.0
    lenses = sorted({lp[0] for lp in rat})
    dims = DIMS + ('memorable',) + (('masterpiece',) if any('masterpiece' in a for rs in rat.values()
                                                            for a in rs.values()) else ())
    raw = {d: [] for d in dims}
    nrm = {d: [] for d in dims}
    per_slot: dict = {}
    for s_, ids in sorted(slots.items()):
        if new not in ids or old not in ids:
            continue
        pn, po = key[ids[new]]['panel'], key[ids[old]]['panel']
        for lens in lenses:
            a, b = rat.get((lens, pn), {}).get(ids[new]), rat.get((lens, po), {}).get(ids[old])
            if not a or not b:
                continue
            for d in dims:
                if d in a and d in b:
                    raw[d].append(a[d] - b[d])
                    nrm[d].append((a[d] - ref_mean((lens, pn), d)) - (b[d] - ref_mean((lens, po), d)))
            per_slot.setdefault(s_, []).append((a['overall'] - b['overall'],
                                                (a['overall'] - ref_mean((lens, pn), 'overall'))
                                                - (b['overall'] - ref_mean((lens, po), 'overall'))))
    print(f"\npaired {new} - {old} across the panels (the same lens, the other panel; raw | normalised by each judge's"
          f" reference mean): mean, sd, won / tied / lost")
    for d in dims:
        x, y = raw[d], nrm[d]
        if x:
            print(f"  {d:<14} {st.mean(x):+.2f} sd {st.pstdev(x):.2f} {sum(v > 0 for v in x):>2} / "
                  f"{sum(v == 0 for v in x):>2} / {sum(v < 0 for v in x):>2}  |  {st.mean(y):+.2f} sd "
                  f"{st.pstdev(y):.2f}   (n {len(x)})")
    print(f"  slot  {new:>6} {old:>6}  panels   raw    norm   (raw per lens: {' '.join(lenses)})")
    sm_r, sm_n = [], []
    for s_, ids in sorted(slots.items()):
        xs = per_slot.get(s_, [])
        if not xs:
            continue
        r_, n_ = st.mean(x for x, _ in xs), st.mean(y for _, y in xs)
        sm_r.append(r_)
        sm_n.append(n_)
        print(f"  {s_}  {ids[new]:>6} {ids[old]:>6}  {key[ids[new]]['panel']} / {key[ids[old]]['panel']}   {r_:+.2f}  "
              f"{n_:+.2f}   ({' '.join(f'{x:+.0f}' for x, _ in xs)})")
    if len(sm_r) > 1:
        k = len(sm_r)
        print(f"  over the {k} slots: raw {st.mean(sm_r):+.2f} (se {st.stdev(sm_r) / k ** 0.5:.2f}), normalised "
              f"{st.mean(sm_n):+.2f} (se {st.stdev(sm_n) / k ** 0.5:.2f}); slots won / lost (raw) "
              f"{sum(x > 0 for x in sm_r)} / {sum(x < 0 for x in sm_r)}")
    print('  the panels\' reference means (overall), per lens: ' + ', '.join(
        f"{lens} {ref_mean((lens, '1'), 'overall'):.1f}/{ref_mean((lens, '2'), 'overall'):.1f}" for lens in lenses))
    # the template flags (round o2, the user: a set must not be one recipe): a judge naming other packets of its
    # panel as the same plan - per version the flags its packets drew (both ends of a flag count), the references
    # as the control
    ver = {i: v for ids in slots.values() for v, i in ids.items()}
    for i in refs:
        ver[i] = 'ref'
    tf = {v: 0 for v in (new, old, 'ref')}
    pairs = []
    for (lens, pan), rs in sorted(rat.items()):
        for i, a in rs.items():
            for j in set(re.findall(r'\b([A-Z]{4})\b', a.get('template', ''))) - {i}:
                if i in ver and j in ver:
                    tf[ver[i]] += 1
                    tf[ver[j]] += 1
                    pairs.append(f"{lens}_p{pan}: {i}({ver[i]}) ~ {j}({ver[j]})")
    n_of = {v: sum(1 for x in ver.values() if x == v) for v in tf}
    print('  template flags (packet ends, per packet of the version): ' + ', '.join(
        f"{v} {tf[v]} ({tf[v] / max(1, n_of[v]):.2f})" for v in tf))
    for p_ in pairs:
        print('     ' + p_)
    if 'masterpiece' in dims:
        # (round o11: the masterpiece means per version - the absolute bar - and each packet's "what is missing")
        mp = {v: [] for v in (new, old, 'ref')}
        for (lens, pan), rs in rat.items():
            for i, a in rs.items():
                if i in ver and 'masterpiece' in a:
                    mp[ver[i]].append(a['masterpiece'])
        print('  masterpiece (absolute, 10 = canon): ' + ', '.join(
            f"{v} {st.mean(x):.2f} (n {len(x)})" for v, x in mp.items() if x))
        per_p = {}
        for (lens, pan), rs in rat.items():
            for i, a in rs.items():
                if i in ver and 'masterpiece' in a:
                    per_p.setdefault(i, []).append(a['masterpiece'])
        print('  per packet: ' + ', '.join(f"{i}({ver[i]}) {st.mean(x):.2f}" for i, x in
                                           sorted(per_p.items(), key=lambda y: -st.mean(y[1]))))
        if '--missing' in sys.argv:
            for (lens, pan), rs in sorted(rat.items()):
                for i, a in sorted(rs.items()):
                    if i in ver and a.get('missing'):
                        print(f"     missing {i}({ver[i]}) {lens}_p{pan}: {a['missing'][:300]}")
    return 0


def groups(key: dict, vdir: Path) -> None:
    """Per KEY 'code' (the generator that made a generated packet, make_packets_orch: its genre) the mean rating
    per dimension and memorable - two generators judged in one round by the same judges."""
    import statistics as st
    codes = sorted({e['code'] for e in key.values() if e.get('code')})
    if len(codes) < 2:
        return
    per: dict = {c: {d: [] for d in DIMS + ('memorable',)} for c in codes + ['references']}
    for f in sorted(vdir.glob('*.md')):
        for i, a in parse_ratings(f.read_text(encoding='utf-8')).items():
            if i not in key:
                continue
            c = key[i].get('code') or ('references' if key[i]['source'] == 'composed' else None)
            if c is None:
                continue
            for d in DIMS + ('memorable',):
                if d in a:
                    per[c][d].append(a[d])
    print('\nby generator (KEY code)  ' + ' '.join(f"{d[:5]:>6}" for d in DIMS + ('memorable',)))
    for c in codes + ['references']:
        print(f"  {c:<22} " + ' '.join(f"{st.mean(per[c][d]) if per[c][d] else 0:6.2f}" for d in DIMS + ('memorable',)))
    a_, b_ = codes[0], codes[1]
    print(f"  {a_} - {b_}: " + ', '.join(f"{d[:5]} {st.mean(per[a_][d]) - st.mean(per[b_][d]):+.2f}"
                                       for d in DIMS + ('memorable',) if per[a_][d] and per[b_][d]))


def main() -> int:
    global DIMS
    if len(sys.argv) > 2 and Path(sys.argv[2]).is_dir():
        DIMS = _dims(Path(sys.argv[2]))
    if '--retro' in sys.argv:
        return retro(sys.argv)
    if '--paired' in sys.argv:
        here = Path(__file__).resolve().parent
        new, old = sys.argv[sys.argv.index('--paired') + 1].split(',')
        return paired(json.loads((here / sys.argv[1]).read_text(encoding='utf-8')), Path(sys.argv[2]), new, old)
    here = Path(__file__).resolve().parent
    key = json.loads((here / sys.argv[1]).read_text(encoding='utf-8'))
    vdir = Path(sys.argv[2])
    if any(parse_ratings(f.read_text(encoding='utf-8')) for f in vdir.glob('*.md')):
        refs = sys.argv[sys.argv.index('--refs') + 1].split(',') if '--refs' in sys.argv else None
        quality(key, vdir, '--tells' in sys.argv, refs)
        groups(key, vdir)
        return 0
    tot_r = tot_n = comp_r = comp_n = 0
    tells = []
    fooled = {i: [] for i in key if key[i]['source'] == 'generated'}
    truth = len(fooled)
    for f in sorted(vdir.glob('*.md')):
        text = f.read_text(encoding='utf-8')
        ans = parse(text)
        right = [i for i in key if i in ans and ans[i]['verdict'] == key[i]['source']]
        miss = [i for i in key if i in ans and ans[i]['verdict'] != key[i]['source']]
        confs = [a['conf'] for a in ans.values() if a['conf'] is not None]
        kinds = {}
        for i in miss:
            k = f"{key[i]['source']} called {ans[i]['verdict']}"
            kinds[k] = kinds.get(k, 0) + 1
        called = sum(a['verdict'] == 'generated' for a in ans.values())
        est = count(text)
        print(f"{f.stem:<14} {len(right)}/{len(ans)}  confidence {min(confs) if confs else '-'}-"
              f"{max(confs) if confs else '-'}  misses: {kinds or 'none'}  called generated {called}"
              + (f"  count {est} (truth {truth})" if est is not None else ''))
        tot_r += len(right)
        tot_n += len(ans)
        if f.stem.startswith('composer'):
            comp_r += len(right)
            comp_n += len(ans)
        for i, a in ans.items():
            if key.get(i, {}).get('source') == 'generated':
                tells.append((f.stem, Path(key[i]['path']).name, a['verdict'], a['conf'], a['reasons']))
                if a['verdict'] == 'composed':
                    fooled[i].append(f.stem)
    print(f"all judges {tot_r}/{tot_n} = {tot_r / max(1, tot_n):.0%}; composers {comp_r}/{comp_n} = "
          f"{comp_r / max(1, comp_n):.0%}")
    print('generated packets - the judges it fooled (called it composed):')
    for i, js in sorted(fooled.items(), key=lambda x: (-len(x[1]), x[0])):
        print(f"  {i} {Path(key[i]['path']).name:<34} {len(js)}  {' '.join(js)}")
    print(f"fooled >= 2 judges: {sum(len(js) >= 2 for js in fooled.values())} of {len(fooled)}")
    if '--tells' in sys.argv:
        for j, p, v, c, rs in tells:
            print(f"\n[{j}] {p}: {v} {c}")
            for r in rs[:3]:
                print('   - ' + r[:400])
    return 0


if __name__ == '__main__':
    sys.exit(main())
