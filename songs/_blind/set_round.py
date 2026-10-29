"""A SET-LEVEL blind round (orchestra round o20 on): per code one continuous set of N pieces from the same set plan seed
(the endless CLI's set planning - composer.set_plan - best-of-1, the same composition seeds in every code), judged as
"an evening's programme from one composer": per-piece judging cannot reward diversity across an endless stream.

    # 1. the sets: per code its own plan from SET_SEED (the code's flags applied before it is drawn), slot k composed
    #    with seed SEED0 + 10 (k - 1) + attempt; a gate reject in any code drops the attempt for all (both re-try)
    python songs/_blind/set_round.py run --code new=ROOT_A:setplan --code old=ROOT_B --set-seed 139500 --n 8 \
        --seed0 139500 --out DIR [--workers 3] [--tries 5]
    # 2. per code the packets (make_packets_paired.dump --orch in a child with the code's flags: the pieces rebuild as
    #    they were composed)
    python songs/_blind/set_round.py dump --code new=ROOT_A:setplan --code old=ROOT_B DIR
    # 3. the judges: per set pair (a DIR of step 1-2) and judge a folder with JUDGE.md (JUDGE_SET.md), set_X/ and
    #    set_Y/ (01.txt .. N.txt in programme order) and prompt.txt; the codes anonymised as X / Y and the reading order
    #    drawn per judge; the key in JUDGE_ROOT/SET_KEY.json (never in a judge's folder)
    #    --cleanse: the palate cleanser in every JUDGE.md (CLEANSE: notes on the first programme before the second);
    #    --two-pass: every judge twice, the second pass (<judge>__p2) relabelled and in the other order - score then
    #    reports the agreement and counts a judge's choice only when both passes agree (round p-div4)
    python songs/_blind/set_round.py deal ROUND JUDGE_ROOT DIR [DIR ...] [--judges 7] [--balance] [--cleanse] [--two-pass]
    # 4. the verdicts (JUDGE_ROOT/verdicts/<pair>_<judge>.md): the forced choices' win rate with its binomial 95 % CI
    #    (Wilson and exact), the strength, variety / coherence per code (paired per judge), the "same piece again"
    #    positions and the tells
    python songs/_blind/set_round.py score JUDGE_ROOT/SET_KEY.json JUDGE_ROOT/verdicts [--codes new,old]

A code is NAME=ROOT[:FLAG[,FLAG...]]: ROOT a checkout of the code (this repo, or a `git archive` of master), the
FLAGs shared_plan.py's --flag names (the code's module switches). The symphony's build ignores the set's `prev` song
(perform.build: the licks' memory is the piano soloist's), so per-slot renders are the CLI's continuous set.
The renders need the environment of a render (AGENTSOUND_SAMPLES / _VOICES / _ENGINE, TMP); JUDGE_SET.md is the
judges' brief, the lenses are judge_orch.py's quality lenses (7 judges).
"""
from __future__ import annotations

import json
import math
import random
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
GENRE = 'orchestra-symphonic'


def _code(spec: str) -> tuple:
    """NAME=ROOT[:FLAG,...] -> (name, root, [flags]) (a Windows drive letter is not a flag separator)."""
    name, _, rest = spec.partition('=')
    m = re.match(r'^(.*?)(?::([A-Za-z0-9_,]+))?$', rest)
    root, flags = m.group(1), [f for f in (m.group(2) or '').split(',') if f]
    if re.fullmatch(r'[A-Za-z]', root):              # ("D:" alone: the drive, no flags)
        root, flags = rest, []
    return name, Path(root).resolve(), flags


def _boot(root: Path, flags: list):
    """Import the code at `root` with its flags applied (shared_plan._flags)."""
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / 'songs' / '_blind'))
    import shared_plan
    shared_plan._flags([x for f in flags for x in ('--flag', f)])
    return shared_plan


# ------------------------------------------------------------------------------------------------ the children

def cmd_plan(root: Path, seed: int, n: int, out: Path, flags: list) -> int:
    _boot(root, flags)
    from agentsound.endless import composer, genres
    g = genres.get(GENRE).validate()
    p = composer.set_plan(g, n, seed)
    out.write_text(json.dumps(p, indent=1) + '\n', encoding='utf-8')
    print(composer.describe_set(p))
    return 0


def cmd_render(root: Path, plan_f: Path, j: int, seed: int, out: Path, flags: list) -> int:
    """One piece: slot j (1-based) of the plan, composition seed `seed`, best-of-1 -> out/<j>-<title>/ and
    out/status/<j>_<seed>.json {pass, log, dir}; exit 0 pass, 3 rejected."""
    from argparse import Namespace
    sp = _boot(root, flags)
    from agentsound.endless import genres, run as R
    g = genres.get(GENRE).validate()
    plan = json.loads(plan_f.read_text(encoding='utf-8'))
    slot, dropped = sp.fit(plan[j - 1], g.plan.get('set') or {})
    if dropped:
        raise SystemExit(f"slot {j}: the code has no {dropped} - not this code's plan")
    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)
    out.mkdir(parents=True, exist_ok=True)
    info = None
    try:
        info = R.render_tune(g, seed, out, j, Namespace(mood=None, swing=None, engine=None, keep=False), log,
                             plan=slot)
    except Exception as e:                            # (a compose error is a reject)
        import traceback
        traceback.print_exc()
        log(f"seed {seed}: error {type(e).__name__}: {e}")
    st = out / 'status'
    st.mkdir(exist_ok=True)
    mp3 = (info or {}).get('files', {}).get('mp3', '')
    (st / f"{j:02d}_{seed}.json").write_text(json.dumps(
        {'slot': j, 'seed': seed, 'pass': bool(info), 'log': lines, 'dir': str(Path(mp3).parent) if mp3 else ''},
        indent=1), encoding='utf-8')
    return 0 if info else 3


def cmd_dump1(root: Path, folder: Path, name: str, flags: list) -> int:
    """The packets of one code's set (its pieces rebuilt by the code with its flags)."""
    _boot(root, flags)
    import make_packets_paired as mpp
    items = [f"{name}-{int(d.name[:3]):03d}={d}" for d in sorted((folder / name).iterdir())
             if d.is_dir() and re.match(r'\d{3}-', d.name)]
    return mpp.dump(folder / f"PACKETS_{name}.json", items, orch=True)


# ------------------------------------------------------------------------------------------------ the parents

def _child(args: list, log_f: Path) -> int:
    log_f.parent.mkdir(parents=True, exist_ok=True)
    with log_f.open('w', encoding='utf-8') as f:
        return subprocess.run([sys.executable, str(Path(__file__).resolve())] + args, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def cmd_run(codes: list, set_seed: int, n: int, seed0: int, out: Path, workers: int, tries: int) -> int:
    out.mkdir(parents=True, exist_ok=True)
    for name, root, flags in codes:
        pf = out / f"PLAN_{name}.json"
        if not pf.exists():
            rc = _child(['plan', str(root), str(set_seed), str(n), str(pf)] + [x for f in flags for x in ('--flag', f)],
                        out / 'logs' / f"plan_{name}.log")
            if rc:
                raise SystemExit(f"{name}: the plan failed (logs/plan_{name}.log)")

    def one(c, j, seed):
        name, root, flags = c
        _child(['render', str(root), str(out / f"PLAN_{name}.json"), str(j), str(seed), str(out / name)] +
               [x for f in flags for x in ('--flag', f)], out / 'logs' / f"{name}_{j:02d}_{seed}.log")
        st = out / name / 'status' / f"{j:02d}_{seed}.json"
        return json.loads(st.read_text(encoding='utf-8')) if st.exists() else {'pass': False, 'log': ['no status']}

    def slot(j):
        res = []
        for a in range(tries):
            seed = seed0 + 10 * (j - 1) + a
            with ThreadPoolExecutor(len(codes)) as ex:
                got = list(ex.map(lambda c: one(c, j, seed), codes))
            rec = {'slot': j, 'seed': seed, **{c[0]: g['pass'] for c, g in zip(codes, got)},
                   'fails': [m for g in got for m in g['log'] if 'REJECTED' in m or 'error' in m]}
            res.append(rec)
            print(json.dumps(rec), flush=True)
            if all(g['pass'] for g in got):
                return res
            for c, g in zip(codes, got):                # (a reject anywhere drops the attempt everywhere)
                if g['pass'] and g.get('dir'):
                    d = Path(g['dir'])
                    dst = out / 'dropped' / c[0] / f"{d.name}-{seed}"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(d), str(dst))
        return res
    with ThreadPoolExecutor(workers) as ex:
        allres = list(ex.map(slot, range(1, n + 1)))
    (out / 'attempts.json').write_text(json.dumps({str(j + 1): r for j, r in enumerate(allres)}, indent=1),
                                       encoding='utf-8')
    bad = [j + 1 for j, r in enumerate(allres) if not all(r[-1][c[0]] for c in codes)]
    print('finished' + (f" - slots without a passing attempt: {bad}" if bad else ''))
    return 1 if bad else 0


def cmd_dump(codes: list, folder: Path) -> int:
    rc = 0
    for name, root, flags in codes:
        rc |= _child(['dump1', str(root), str(folder), name] + [x for f in flags for x in ('--flag', f)],
                     folder / 'logs' / f"dump_{name}.log")
    return rc


# ------------------------------------------------------------------------------------------------ the judges

def _prompt(lens: str, d: Path, out: Path, first: str) -> str:
    second = 'Y' if first == 'X' else 'X'
    return (f"{lens}\n\nYou judge two evenings' PROGRAMMES now, not single pieces: imagine sitting through each "
            f"evening in order.\n\n"
            f"Your working folder is {d.as_posix()}. Read {d.as_posix()}/JUDGE.md first and follow it exactly; then "
            f"read the programme in {d.as_posix()}/set_{first}/ (01.txt to the last, in order), then the one in "
            f"{d.as_posix()}/set_{second}/ (in order). You may read ONLY those files: do not open, list or search any "
            f"other file or folder (no repository files, no KEY files, nothing outside your working folder). Take "
            f"your time; note while you read where a programme repeats itself.\n\n"
            f"Write your complete answer, in JUDGE.md's answer format (## Choice, ## Set X, ## Set Y, ## Advice), to "
            f"{out.as_posix()} with the Write tool. Reply with one line: done.")


CLEANSE = """
## The reading order (read this before you start)

Which programme you read first was drawn at random; it says nothing about which one is better. Earlier judges kept
the programme they read second about four times in five - a recency effect, not a quality signal. So:
1. After the first programme (set_{first}), BEFORE opening the second, write your notes on it to `notes_{first}.md` in
   your working folder: its best and its weakest piece, where it repeats itself, a provisional variety and coherence
   rating.
2. Read the second programme (set_{second}) and write `notes_{second}.md` the same way.
3. Before you choose, re-read `notes_{first}.md` and look again at set_{first}'s first, middle and last piece, so that both
   evenings are equally fresh.
4. Decide from the two notes. In `why`, name one concrete point where the programme you did NOT keep is the better one.
"""
"""The palate cleanser appended to a set judge's JUDGE.md (deal --cleanse; round p-div3: the programme read second
kept 23 of 28 in p-div2, 21 of 28 with it): notes on the first programme before the second, both re-read."""

P2 = '__p2'
"""A judge's second pass (deal --two-pass): its own folder and verdict `<pair>_<judge>__p2.md`, the same lens, the
programmes relabelled (the codes swap X / Y) and read in the other order (second_pass) - a fresh judge that has not
seen pass 1. score counts a judge's choice only when both passes keep the same code."""


def second_pass(asg: dict) -> dict:
    """Pass 2's assignment for pass 1's {'X', 'Y', 'first'}: the codes swap labels, the code read second in pass 1 is
    read first."""
    first_code = asg[asg['first']]
    a2 = {'X': asg['Y'], 'Y': asg['X']}
    a2['first'] = 'X' if a2['X'] != first_code else 'Y'
    return a2


def write_judge(jd: Path, sets: dict, asg: dict, brief: str, prompt: str, cleanse: bool = False) -> None:
    """One set judge's folder: set_X/ and set_Y/ (asg's codes, programme order), JUDGE.md (brief + the cleanser),
    prompt.txt."""
    if jd.exists():
        shutil.rmtree(jd)
    for lab in ('X', 'Y'):
        (jd / f"set_{lab}").mkdir(parents=True)
        for k, x in enumerate(sets[asg[lab]]):
            (jd / f"set_{lab}" / f"{k + 1:02d}.txt").write_text(x['text'], encoding='utf-8')
    first = asg['first']
    (jd / 'JUDGE.md').write_text(brief + (CLEANSE.format(first=first, second='XY'[first == 'X']) if cleanse else ''),
                                 encoding='utf-8')
    (jd / 'prompt.txt').write_text(prompt, encoding='utf-8')


def deal_judge(key_pair: dict, jroot: Path, pair: str, jn: str, sets: dict, asg: dict, brief: str, lens: str,
               cleanse: bool = False, two_pass: bool = False) -> None:
    """A judge's folder(s) and key entries: pass 1 as `asg`, with two_pass also P2 (second_pass)."""
    passes = [(jn, asg)] + ([(jn + P2, second_pass(asg))] if two_pass else [])
    for name, a in passes:
        jd = jroot / pair / name
        write_judge(jd, sets, a, brief, _prompt(lens, jd, jroot / 'verdicts' / f"{pair}_{name}.md", a['first']),
                    cleanse)
        key_pair['judges'][name] = a


def cmd_deal(rnd: str, jroot: Path, dirs: list, n_judges: int, balance: bool = False, cleanse: bool = False,
             two_pass: bool = False) -> int:
    """balance (round o23 - o22's programme read second was kept 21 of 28): the reading order is not drawn but
    alternated - judge i of pair p reads the first code's programme first when i + p is even - so the first code is
    read first by half of the judges (n_judges x pairs even: exactly half). cleanse: CLEANSE in every JUDGE.md;
    two_pass: every judge twice, the second pass in the other order (P2, second_pass)."""
    import judge_orch as jo
    judges = list(jo.JUDGES_Q)[:n_judges]
    jroot.mkdir(parents=True, exist_ok=True)
    (jroot / 'verdicts').mkdir(exist_ok=True)
    key = {'round': rnd, 'pairs': {}}
    for p_i, d in enumerate(dirs):
        d = Path(d).resolve()
        packs = {f.stem[len('PACKETS_'):]: json.loads(f.read_text(encoding='utf-8'))
                 for f in sorted(d.glob('PACKETS_*.json'))}
        if len(packs) != 2:
            raise SystemExit(f"{d}: two codes' PACKETS_*.json needed, found {sorted(packs)}")
        codes = sorted(packs)
        sets = {c: [packs[c][lab] for lab in sorted(packs[c])] for c in codes}
        if len({len(v) for v in sets.values()}) != 1:
            raise SystemExit(f"{d}: the sets differ in length")
        pair = d.name
        key['pairs'][pair] = {'dir': d.as_posix(), 'judges': {},
                              'sets': {c: [x['path'] for x in sets[c]] for c in codes},
                              'titles': {c: [x.get('title') for x in sets[c]] for c in codes}}
        for j_i, jn in enumerate(judges):
            rng = random.Random(f"blind-set-{rnd}:{pair}:{jn}")
            x_code = codes[rng.randrange(2)]
            first = 'XY'[rng.randrange(2)]
            if balance:
                first = ('X' if x_code == codes[0] else 'Y') if (j_i + p_i) % 2 == 0 else \
                    ('Y' if x_code == codes[0] else 'X')
            asg = {'X': x_code, 'Y': codes[1 - codes.index(x_code)], 'first': first}
            deal_judge(key['pairs'][pair], jroot, pair, jn, sets, asg,
                       (HERE / 'JUDGE_SET.md').read_text(encoding='utf-8'), jo.LENS_Q[jo.JUDGES_Q[jn]],
                       cleanse=cleanse, two_pass=two_pass)
            print(f"{pair} {jn}: X={asg['X']} Y={asg['Y']} first {first}" + (" (+ the second pass)" if two_pass
                                                                                else ''))
    (jroot / 'SET_KEY.json').write_text(json.dumps(key, indent=1) + '\n', encoding='utf-8')
    return 0


# ------------------------------------------------------------------------------------------------ the score

def _num(s, lo, hi):
    m = re.search(r'-?\d+(\.\d+)?', s or '')
    if not m:
        return None
    v = float(m.group())
    return v if lo <= v <= hi else None


def parse(text: str) -> dict:
    """A JUDGE_SET.md answer -> {'keep', 'strength', 'why', 'X': {...}, 'Y': {...}, 'advice'}."""
    secs, cur = {}, None
    for line in text.splitlines():
        m = re.match(r'^\s*#+\s*(choice|set\s*([xy])|advice)\b', line, re.I)
        if m:
            cur = 'choice' if m.group(1).lower() == 'choice' else 'advice' if m.group(1).lower() == 'advice' \
                else m.group(2).upper()
            secs[cur] = []
            continue
        if cur:
            secs[cur].append(line)

    def fields(lines):
        out, tells, last = {}, [], None
        for ln in lines:
            m = re.match(r'^\s*\**([a-z_]+)\**\s*:\s*(.*)$', ln, re.I)
            if m and m.group(1).lower() in ('keep', 'strength', 'why', 'variety', 'coherence', 'same_again',
                                            'same_why', 'tells', 'best', 'weakest'):
                last = m.group(1).lower()
                out[last] = m.group(2).strip()
                continue
            if last == 'tells' and re.match(r'^\s*[-*\d]', ln):
                tells.append(re.sub(r'^\s*(?:[-*]|\d+[.)])\s*', '', ln).strip())
            elif last in ('why', 'same_why') and ln.strip():
                out[last] += ' ' + ln.strip()
        out['tells_list'] = [t for t in tells if t]
        return out
    ch = fields(secs.get('choice', []))
    keep = re.search(r'\b([XY])\b', ch.get('keep', '').upper())
    res = {'keep': keep.group(1) if keep else None, 'strength': _num(ch.get('strength'), 1, 5),
           'why': ch.get('why', ''), 'advice': '\n'.join(secs.get('advice', [])).strip()}
    for lab in ('X', 'Y'):
        f = fields(secs.get(lab, []))
        sa = f.get('same_again', '')
        res[lab] = {'variety': _num(f.get('variety'), 1, 10), 'coherence': _num(f.get('coherence'), 1, 10),
                    'same_again': None if re.search(r'never', sa, re.I) else _num(sa, 1, 99),
                    'same_never': bool(re.search(r'never', sa, re.I)), 'same_why': f.get('same_why', ''),
                    'tells': f.get('tells_list', []), 'best': _num(f.get('best'), 1, 99),
                    'weakest': _num(f.get('weakest'), 1, 99)}
    return res


def _binom_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple:
    if not n:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def exact(k: int, n: int, a: float = 0.05) -> tuple:
    """Clopper-Pearson by bisection on the binomial CDF."""
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if f(mid):
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    low = 0.0 if k == 0 else solve(lambda p: 1 - _binom_cdf(k - 1, n, p) >= a / 2)
    high = 1.0 if k == n else solve(lambda p: _binom_cdf(k, n, p) <= a / 2)
    return (low, high)


def _ms(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return (None, None, 0)
    m = sum(xs) / len(xs)
    se = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1) / len(xs)) if len(xs) > 1 else None
    return (m, se, len(xs))


def _f(x, nd=2):
    return '-' if x is None else f"{x:.{nd}f}"


def two_pass_lines(ch: list, a: str) -> str:
    """The two-pass report (deal --two-pass): per pass the forced choice and the order; the agreement rate (both passes
    of a judge keep the same code); THE RESULT - the agreed choices only (a judge whose passes disagree counts as
    no choice), its Wilson / exact CI."""
    out = []
    p = out.append
    p("TWO PASSES (each judge twice, the second pass in the other reading order)")
    for lab, rs in (("pass 1", [r for r in ch if not r['judge'].endswith(P2)]),
                    ("pass 2", [r for r in ch if r['judge'].endswith(P2)])):
        k, n = sum(r['keep'] == a for r in rs), len(rs)
        sec = sum(r['keep'] != r['first_code'] for r in rs)
        p(f"  {lab}: {a} kept {k} of {n}; the programme read second kept {sec} of {n}")
    by = {}
    for r in ch:
        by.setdefault((r['pair'], r['judge'][:-len(P2)] if r['judge'].endswith(P2) else r['judge']), []).append(r)
    both = [v for v in by.values() if len(v) == 2]
    agree = [v for v in both if v[0]['keep'] == v[1]['keep']]
    p(f"  agreement: {len(agree)} of {len(both)} judges keep the same code in both passes"
      f" = {len(agree) / max(1, len(both)):.3f} (by chance ~0.5; a pure order effect: 0)")
    k, n = sum(v[0]['keep'] == a for v in agree), len(agree)
    w, e = wilson(k, n), exact(k, n)
    p(f"  AGREED: {a} kept by {k} of {n} agreed judges = {k / max(1, n):.3f}; Wilson {w[0]:.3f}-{w[1]:.3f}, exact "
      f"{e[0]:.3f}-{e[1]:.3f}; the CI above 50 %: {'YES' if w[0] > 0.5 and e[0] > 0.5 else 'no'}; "
      f"of all {len(both)} judges: {k / max(1, len(both)):.3f}")
    return '\n'.join(out)


def cmd_score(key_f: Path, vdir: Path, codes: list | None) -> int:
    key = json.loads(key_f.read_text(encoding='utf-8'))
    allc = sorted({c for p in key['pairs'].values() for c in p['sets']})
    a, b = codes or allc
    rows, missing = [], []
    for pair, P in sorted(key['pairs'].items()):
        for jn, asg in sorted(P['judges'].items()):
            f = vdir / f"{pair}_{jn}.md"
            if not f.exists():
                missing.append(f.name)
                continue
            v = parse(f.read_text(encoding='utf-8'))
            lab = {asg['X']: 'X', asg['Y']: 'Y'}
            rows.append({'pair': pair, 'judge': jn, 'first': asg['first'], 'first_code': asg[asg['first']],
                         'keep': asg[v['keep']] if v['keep'] else None, 'strength': v['strength'], 'why': v['why'],
                         'advice': v['advice'], **{c: v[lab[c]] for c in (a, b)}})
    out = []
    p = out.append
    p(f"SET-LEVEL ROUND {key.get('round')}: {a} vs {b}, {len(rows)} verdicts"
      + (f" ({len(missing)} missing: {', '.join(missing)})" if missing else ''))
    ch = [r for r in rows if r['keep'] in (a, b)]
    k, n = sum(r['keep'] == a for r in ch), len(ch)
    w, e = wilson(k, n), exact(k, n)
    p("")
    p(f"forced choice: {a} kept by {k} of {n} = {k / max(1, n):.3f}; 95 % CI Wilson {w[0]:.3f}-{w[1]:.3f}, "
      f"exact (Clopper-Pearson) {e[0]:.3f}-{e[1]:.3f}; two-sided binomial p (H0 0.5) = "
      f"{min(1.0, 2 * min(_binom_cdf(k, n, 0.5), 1 - _binom_cdf(k - 1, n, 0.5) if k else 1.0)):.4f}")
    p(f"  the CI lies above 50 %: {'YES' if w[0] > 0.5 and e[0] > 0.5 else 'no'} (Wilson {w[0] > 0.5}, exact "
      f"{e[0] > 0.5})")
    sw = [(r['strength'] or 0) * (1 if r['keep'] == a else -1) for r in ch]
    m, se, _ = _ms(sw)
    p(f"strength-signed (+ = {a}, 1-5): mean {_f(m)} se {_f(se)}; mean strength {_f(_ms([r['strength'] for r in ch])[0])}")
    fk = sum(r['keep'] == r['first_code'] for r in ch)
    p(f"order: the programme read first kept {fk} of {n}; {a} read first in "
      f"{sum(r['first_code'] == a for r in ch)} of {n}")
    for lab, rs_ in ((f"{a} read first", [r for r in ch if r['first_code'] == a]),
                     (f"{a} read second", [r for r in ch if r['first_code'] != a])):
        k_, n_ = sum(r['keep'] == a for r in rs_), len(rs_)
        if n_:                                  # (round o23: the result by reading order)
            w_ = wilson(k_, n_)
            p(f"  {lab}: {a} kept {k_} of {n_} = {k_ / n_:.3f}; Wilson {w_[0]:.3f}-{w_[1]:.3f}")
    if any(r['judge'].endswith(P2) for r in rows):
        p("")
        p(two_pass_lines(ch, a))
    p("")
    p(f"{'pair':<10} {'n':>2} {a + ' kept':>9}  {'variety ' + a:>11} {'variety ' + b:>11}  "
      f"{'coher. ' + a:>10} {'coher. ' + b:>10}")
    for pair in sorted(key['pairs']):
        rs = [r for r in rows if r['pair'] == pair]
        p(f"{pair:<10} {len(rs):>2} {sum(r['keep'] == a for r in rs):>9}  "
          f"{_f(_ms([r[a]['variety'] for r in rs])[0]):>11} {_f(_ms([r[b]['variety'] for r in rs])[0]):>11}  "
          f"{_f(_ms([r[a]['coherence'] for r in rs])[0]):>10} {_f(_ms([r[b]['coherence'] for r in rs])[0]):>10}")
    p("")
    for dim in ('variety', 'coherence'):
        ma, mb = _ms([r[a][dim] for r in rows]), _ms([r[b][dim] for r in rows])
        d = _ms([r[a][dim] - r[b][dim] for r in rows if r[a][dim] is not None and r[b][dim] is not None])
        p(f"{dim:<10} {a} {_f(ma[0])}  {b} {_f(mb[0])}  paired {a} - {b} {_f(d[0])} se {_f(d[1])} (n {d[2]})")
    p("")
    for c in (a, b):
        sa = [r[c]['same_again'] for r in rows if r[c]['same_again'] is not None]
        nv = sum(r[c]['same_never'] for r in rows)
        p(f"same piece again, {c}: positions {sorted(int(x) for x in sa)}; mean {_f(_ms(sa)[0])}; never {nv}")
    p(f"tells per programme: {a} {_f(_ms([len(r[a]['tells']) for r in rows])[0])}, "
      f"{b} {_f(_ms([len(r[b]['tells']) for r in rows])[0])}")
    for c in (a, b):
        best = [int(r[c]['best']) for r in rows if r[c]['best']]
        worst = [int(r[c]['weakest']) for r in rows if r[c]['weakest']]
        p(f"best / weakest piece, {c}: best {sorted(best)}; weakest {sorted(worst)}")
    p("")
    p("PER VERDICT")
    for r in rows:
        p(f"- {r['pair']} {r['judge']}: kept {r['keep']} (strength {_f(r['strength'], 0)}; read first "
          f"{r['first_code']}); variety {a} {_f(r[a]['variety'], 0)} / {b} {_f(r[b]['variety'], 0)}, coherence "
          f"{a} {_f(r[a]['coherence'], 0)} / {b} {_f(r[b]['coherence'], 0)}; same again {a} "
          f"{'never' if r[a]['same_never'] else _f(r[a]['same_again'], 0)} / {b} "
          f"{'never' if r[b]['same_never'] else _f(r[b]['same_again'], 0)}")
        p(f"    why: {r['why']}")
        for c in (a, b):
            p(f"    same again {c}: {r[c]['same_why']}")
    p("")
    p("TELLS")
    for c in (a, b):
        p(f"[{c}]")
        for r in rows:
            for t in r[c]['tells']:
                p(f"  {r['pair']} {r['judge']}: {t}")
    print('\n'.join(out))
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    flags = [rest[i + 1] for i, x in enumerate(rest) if x == '--flag']
    pos = [x for i, x in enumerate(rest) if x != '--flag' and (i == 0 or rest[i - 1] != '--flag')]
    if cmd == 'plan':
        return cmd_plan(Path(pos[0]).resolve(), int(pos[1]), int(pos[2]), Path(pos[3]), flags)
    if cmd == 'render':
        return cmd_render(Path(pos[0]).resolve(), Path(pos[1]).resolve(), int(pos[2]), int(pos[3]),
                          Path(pos[4]).resolve(), flags)
    if cmd == 'dump1':
        return cmd_dump1(Path(pos[0]).resolve(), Path(pos[1]).resolve(), pos[2], flags)

    def opt(name, default=None, cast=str):
        return cast(rest[rest.index(name) + 1]) if name in rest else default
    codes = [_code(rest[i + 1]) for i, x in enumerate(rest) if x == '--code']
    if cmd == 'run':
        return cmd_run(codes, opt('--set-seed', cast=int), opt('--n', 8, int), opt('--seed0', None, int) or
                       opt('--set-seed', cast=int), Path(opt('--out')).resolve(), opt('--workers', 3, int),
                       opt('--tries', 5, int))
    if cmd == 'dump':
        return cmd_dump(codes, Path([x for i, x in enumerate(rest) if not x.startswith('--') and
                                     (i == 0 or rest[i - 1] != '--code')][-1]).resolve())
    if cmd == 'deal':
        n_j = opt('--judges', 7, int)
        ds = [x for i, x in enumerate(rest[2:], 2) if not x.startswith('--') and rest[i - 1] != '--judges']
        return cmd_deal(rest[0], Path(rest[1]).resolve(), ds, n_j, balance='--balance' in rest,
                        cleanse='--cleanse' in rest, two_pass='--two-pass' in rest)
    if cmd == 'score':
        cs = opt('--codes')
        return cmd_score(Path(rest[0]), Path(rest[1]), cs.split(',') if cs else None)
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
