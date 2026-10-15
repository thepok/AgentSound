"""Judging student pieces like teacher pieces: decode -> the runner's checks (arc, breath) -> perform (no audio) ->
composer.score + every tell; novelty against the training set (melody n-grams, bars, nearest neighbour); summary
tables. CPU work runs in a process pool (torch is not imported here)."""
from __future__ import annotations

import math
import os
import statistics as st
from collections import Counter, defaultdict

from . import tokens as T


def measure_tokens(job) -> dict:
    """(tokens, genre, seed) -> {'status': 'invalid' | 'arc' | 'breath' | 'error' | 'ok', 'score', 'metrics', ...}."""
    toks, genre, seed = job
    from ..endless.composer import shape
    from ..endless.genres import get
    from .export import measure
    g = get(genre)
    try:
        tune = T.decode(toks, g, seed=seed)
    except (T.TokenError, KeyError, ValueError, IndexError) as e:
        return {'status': 'invalid', 'error': str(e)[:160]}
    out = {'header': {'mood': tune.mood, 'feel': tune.feel, 'form': tune.form, 'key': tune.key, 'tempo': tune.tempo}}
    try:
        sh = shape(tune)
    except Exception as e:                               # (a lead sheet the measures cannot read)
        return dict(out, status='error', error=f"shape: {type(e).__name__}: {e}"[:160])
    if sh['issues']:
        return dict(out, status='arc', issues=sh['issues'][:4])
    try:
        m = measure(tune, g)
    except Exception as e:
        return dict(out, status='error', error=f"perform: {type(e).__name__}: {e}"[:160])
    m.pop('song')
    return dict(out, status='breath' if m['breath'] else 'ok', score=m['score'], mean=m['mean'], hard=m['hard'],
                metrics=m['metrics'])


def lead_sheet_ok(toks, genre: str) -> bool:
    """The composer's own cheap checks on a lead sheet (no performance): it decodes, shape() finds no arc issue and
    the melody's issues (melody_issues over the parts) stay inside the score table's range - what the rule composer
    retries on internally, so a student 'retry' is the same budget, not a peek at the score."""
    from ..endless.composer import Harm, melody_issues, shape
    from ..endless.genres import SCORES, get
    from ..theory import Key
    g = get(genre)
    try:
        tune = T.decode(toks, g, seed=0)
        if shape(tune)['issues']:
            return False
        kp = set(Key(tune.key).pcs)
        mi = sum(len(melody_issues(tune.melody[p], Harm(tune.changes[p], kp), 0, 127, meter=tune.meter))
                 for p in tune.parts if tune.melody[p])
    except Exception:
        return False
    hi = SCORES[g.style].get('mel_issues', (0, 99))[1]
    return mi <= hi


_POOL = None


def cpu_pool(workers: int):
    """A spawn pool whose workers cannot see the GPU (CUDA_VISIBLE_DEVICES=-1: no device; an empty value would be
    dropped from the environment on Windows): only the parent holds the model on the
    GPU; every CUDA process costs its own context, and ten of them spilled the 16 GiB card into system RAM."""
    import multiprocessing as mp
    os.environ['PYTHONHASHSEED'] = '0'              # (perform's figure summary tie-break: TODO.md)
    old = os.environ.get('CUDA_VISIBLE_DEVICES')
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'       # the children inherit the env at spawn (Pool starts them now)
    try:
        return mp.get_context('spawn').Pool(workers)
    finally:
        if old is None:
            os.environ.pop('CUDA_VISIBLE_DEVICES', None)
        else:
            os.environ['CUDA_VISIBLE_DEVICES'] = old


def pool(workers: int | None = None):
    global _POOL
    if _POOL is None:
        _POOL = cpu_pool(workers or max(1, (os.cpu_count() or 2) - 2))
    return _POOL


def vram_line() -> str:
    """The process's peak reserved GPU memory (for the train / eval logs), '' without CUDA."""
    import sys
    torch = sys.modules.get('torch')
    if torch is None or not torch.cuda.is_available():
        return ''
    return f"GPU peak reserved {torch.cuda.max_memory_reserved() / 2**30:.2f} GiB"


def measure_many(seqs, genre: str, seed0: int = 0, workers: int | None = None) -> list[dict]:
    jobs = [(s, genre, seed0 + i) for i, s in enumerate(seqs)]
    return pool(workers).map(measure_tokens, jobs, chunksize=1)


# ------------------------------------------------------------------------------------------------ summaries

def unscored(style: str, metrics: dict) -> list[str]:
    """The tells score_metrics measures that the style's score table does NOT weigh (the Goodhart watch list)."""
    from ..endless.genres import SCORES
    return sorted(k for k in metrics if k not in SCORES[style])


def rates(res: list[dict]) -> dict:
    n = max(1, len(res))
    c = Counter(r['status'] for r in res)
    return {'n': len(res), 'decodable': round(1 - c['invalid'] / n, 3),
            'performable': round(1 - (c['invalid'] + c['error']) / n, 3),
            'arc_pass': round((c['breath'] + c['ok']) / n, 3), 'all_checks': round(c['ok'] / n, 3)}


def score_stats(res: list[dict]) -> dict:
    s = [r['score'] for r in res if r.get('status') == 'ok']
    if not s:
        return {'n': 0}
    q = sorted(s)
    return {'n': len(s), 'mean': round(st.mean(s), 1), 'sd': round(st.pstdev(s), 1), 'min': q[0],
            'p10': q[int(0.1 * (len(q) - 1))], 'median': q[len(q) // 2], 'max': q[-1],
            'capped': round(sum(1 for r in res if r.get('status') == 'ok' and r['hard']) / len(s), 3)}


def w1(a: list[float], b: list[float]) -> float:
    """1-D Wasserstein distance between two samples (quantile matching on 50 points)."""
    if not a or not b:
        return float('nan')
    qa, qb = sorted(a), sorted(b)
    k = 50
    return sum(abs(qa[int(i * (len(qa) - 1) / (k - 1))] - qb[int(i * (len(qb) - 1) / (k - 1))]) for i in range(k)) / k


def metric_table(student: list[dict], teacher: list[dict], keys=None) -> list[dict]:
    """Per metric: teacher mean / sd, student mean, the W1 distance in teacher sd units."""
    S = [r['metrics'] for r in student if r.get('status') == 'ok']
    Tm = [r['metrics'] for r in teacher if r.get('status') == 'ok']
    keys = keys or sorted({k for m in Tm for k in m})
    out = []
    for k in keys:
        a = [m[k] for m in Tm if k in m and m[k] is not None]
        b = [m[k] for m in S if k in m and m[k] is not None]
        if len(a) < 3 or len(b) < 3:
            continue
        sd = st.pstdev(a) or 1e-9
        out.append({'metric': k, 'teacher': round(st.mean(a), 3), 'teacher_sd': round(sd, 3),
                    'student': round(st.mean(b), 3), 'w1_sd': round(w1(a, b) / sd, 2) if sd > 1e-6 else
                    (0.0 if abs(st.mean(a) - st.mean(b)) < 1e-9 else float('inf'))})
    return out


# ------------------------------------------------------------------------------------------------ novelty

def melody_of(toks: list[str]):
    """The head melody of a token sequence: per part a list of bars, each bar a tuple of (pos, pitch, dur) tokens
    (pitches relative to the tonic: a transposed copy is a copy)."""
    parts, cur, bar, inside = [], None, None, False
    for i, t in enumerate(toks):
        if t == 'M':
            inside, cur, bar = True, [], None
            continue
        if not inside:
            continue
        if t == 'EndM':
            if bar is not None:
                cur.append(tuple(bar))
            parts.append(cur)
            inside = False
        elif t in ('Bar', 'BarPre'):
            if bar is not None:
                cur.append(tuple(bar))
            bar = []
        elif t.startswith('Pos_') and bar is not None and i + 2 < len(toks) and toks[i + 1][:2] == 'P_' and \
                toks[i + 1][2:].lstrip('-').isdigit() and toks[i + 2][:2] == 'D_':
            bar.append((t, toks[i + 1], toks[i + 2]))
    return parts


def note_line(parts) -> list[tuple]:
    """(interval, duration, position) per melody note over the head: the n-gram alphabet."""
    out, prev = [], None
    for bars in parts:
        for bar in bars:
            for pos, p, d in bar:
                pi = int(p[2:])
                out.append((0 if prev is None else pi - prev, d, pos))
                prev = pi
    return out


class Index:
    """The training set's melodies of one genre: n-gram counts, bar -> pieces, whole-melody hashes."""

    def __init__(self, seqs, n: int = 6):
        self.n = n
        self.grams = set()
        self.bar_pieces = defaultdict(set)
        self.whole = set()
        self.sizes = []
        for pid, toks in enumerate(seqs):
            parts = melody_of(toks)
            line = note_line(parts)
            self.grams.update(tuple(line[i:i + n]) for i in range(len(line) - n + 1))
            bars = {b for p in parts for b in p if b}
            for b in bars:
                self.bar_pieces[b].add(pid)
            self.sizes.append(len(bars))
            self.whole.add(hash(tuple(tuple(p) for p in parts)))

    def novelty(self, toks: list[str]) -> dict:
        parts = melody_of(toks)
        line = note_line(parts)
        grams = [tuple(line[i:i + self.n]) for i in range(len(line) - self.n + 1)]
        seen = sum(1 for g in grams if g in self.grams) / max(1, len(grams))
        bars = {b for p in parts for b in p if b}
        hits = Counter()
        for b in bars:
            ps = self.bar_pieces.get(b)
            if ps is not None and len(ps) < 4000:            # (ubiquitous bars say nothing about copying)
                hits.update(ps)
        nn = max((c / (len(bars) + self.sizes[pid] - c) for pid, c in hits.items()), default=0.0)
        bar_seen = sum(1 for b in bars if b in self.bar_pieces) / max(1, len(bars))
        return {'ngram_seen': round(seen, 3), 'bar_seen': round(bar_seen, 3), 'nn_jaccard': round(nn, 3),
                'copy': hash(tuple(tuple(p) for p in parts)) in self.whole}


def diversity(seqs) -> dict:
    """Within a set of pieces: distinct melody 6-grams / all, mean pairwise bar-set Jaccard (sampled)."""
    import random
    lines = [note_line(melody_of(s)) for s in seqs]
    grams = [tuple(l[i:i + 6]) for l in lines for i in range(len(l) - 5)]
    bars = [{b for p in melody_of(s) for b in p if b} for s in seqs]
    rng = random.Random(0)
    pairs = [(i, j) for i in range(len(bars)) for j in range(i + 1, len(bars))]
    rng.shuffle(pairs)
    js = [len(bars[i] & bars[j]) / max(1, len(bars[i] | bars[j])) for i, j in pairs[:400]]
    return {'distinct6': round(len(set(grams)) / max(1, len(grams)), 3),
            'pair_jaccard': round(sum(js) / max(1, len(js)), 3) if js else None}


def mean_or_nan(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return round(sum(xs) / len(xs), 3) if xs else float('nan')


# ------------------------------------------------------------------------------------------------ set variety

VARIETY_FIELDS = ('mood', 'feel', 'form', 'mode', 'key', 'tempo', 'climax_pos', 'climax_pitch', 'ending', 'layout',
                  'climax_kind')
"""(layout / climax_kind: the Arr block's, schema 2 - a schema-1 set has none, the fields drop out of the mean)"""
TEMPO_BAND = 5                       # BPM per tempo band
CLIMAX_BINS = 5                      # the climax position in fifths of the head


def header_of(toks) -> dict | None:
    """What a listener hears change between pieces, straight from the tokens: mood, feel, form, mode, key (the
    tonic), tempo, the climax's position in the head (0..1) and its pitch (MIDI), the ending (EndKind + the end
    chord). None when the header does not parse."""
    from ..endless.genres import FORMS
    toks = toks.split() if isinstance(toks, str) else list(toks)
    v = {}
    for t in toks[1:17]:
        pre, _, val = t.partition('_')
        v[pre] = val
    try:
        meter, tempo, tpc = int(v['Meter']), int(v['Tempo']), T.name_pc(v['Key'])
        form = v['Form']
        out = {'mood': v['Mood'], 'feel': v['Feel'], 'form': form, 'mode': v['Mode'], 'key': v['Key'],
               'tempo': tempo, 'climax_pos': None, 'climax_pitch': None}
        i = toks.index('EndChord')
        out['ending'] = ' '.join([v.get('EndKind', '?')] + [t for t in toks[i + 1:i + 4]
                                                             if t.startswith(('Root_', 'Q_', 'Bass_'))])
        if 'Climax' in toks[:i]:
            c = toks.index('Climax')
            part, bn, pos, p = toks[c + 1][5:], int(toks[c + 3][3:]), int(toks[c + 4][4:]), int(toks[c + 5][2:])
            parts = list(FORMS[form]['parts'])
            bars = FORMS[form]['bars'] * (2 if meter == 3 else 1)
            frac = min(1.0, (bn + pos / (meter * 12)) / bars)
            out['climax_pos'] = round((parts.index(part) + frac) / len(parts), 3)
            out['climax_pitch'] = p + tpc
    except (KeyError, ValueError, IndexError):
        return None
    arr = arrangement_of(toks)
    out['layout'], out['climax_kind'] = (arr['layout'], arr['climax']) if arr else (None, None)
    return out


def arrangement_of(toks) -> dict | None:
    """The Arr block's arrangement-level facts (schema 2; None without a block): the layout, the climax kind, the
    sections played (in order), each section's cadence (ACad), the swell levels (ASw, every phrase of every section)
    and the left hand's per-section styles (ALH, jazz)."""
    toks = toks.split() if isinstance(toks, str) else list(toks)
    if 'Arr' not in toks:
        return None
    a, z = toks.index('Arr'), toks.index('EndArr')
    out = {'layout': None, 'climax': None, 'sections': [], 'cadence': {}, 'swell': [], 'lh': []}
    sec = None
    for t in toks[a + 1:z]:
        pre, _, val = t.partition('_')
        if pre == 'ALayout':
            out['layout'] = val
        elif pre == 'ASec':
            sec = val
            out['sections'].append(val)
        elif pre == 'AClimax':
            out['climax'] = val
        elif pre == 'ACad':
            out['cadence'][sec] = val
        elif pre == 'ASw':
            out['swell'].append(val)
        elif pre == 'ALH':
            out['lh'].append(val)
    return out


ARR_FIELDS = ('layout', 'climax', 'climax_pos', 'cadence', 'swell', 'lh', 'form')


def arrangement_dist(seqs) -> dict:
    """A set's arrangement distributions (schema 2): per field {value: share} - the layout, the climax kind, the
    climax position (fifths of the head, from the plan), the cadences (every section's ACad), the swell levels (every
    ASw), the left hand's styles (every ALH: jazz), the form (the section names in order)."""
    vals = defaultdict(list)
    for s in seqs:
        arr, h = arrangement_of(s), header_of(s)
        if arr is None:
            continue
        vals['layout'].append(arr['layout'] or '-')
        vals['climax'].append(arr['climax'] or '-')
        vals['cadence'] += list(arr['cadence'].values())
        vals['swell'] += arr['swell']
        vals['lh'] += arr['lh']
        vals['form'].append(' '.join(arr['sections']))
        if h and h.get('climax_pos') is not None:
            vals['climax_pos'].append(min(CLIMAX_BINS - 1, int(h['climax_pos'] * CLIMAX_BINS)))
    out = {}
    for f in ARR_FIELDS:
        c = Counter(vals[f])
        n = sum(c.values())
        out[f] = {'n': n, 'share': {str(k): round(v / n, 3) for k, v in c.most_common()}} if n else {'n': 0, 'share': {}}
    return out


def tv_distance(p: dict, q: dict) -> float:
    """Total variation between two {value: share} distributions (0 the same .. 1 disjoint)."""
    return round(0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in set(p) | set(q)), 3)


def arrangement_table(student_seqs, teacher_seqs) -> dict:
    """Student vs teacher arrangement distributions: per field both distributions and their total variation."""
    s, t = arrangement_dist(student_seqs), arrangement_dist(teacher_seqs)
    return {f: {'tv': tv_distance(s[f]['share'], t[f]['share']) if s[f]['n'] and t[f]['n'] else None,
                'student': s[f], 'teacher': t[f]} for f in ARR_FIELDS}


def value_counts(genre) -> dict:
    """The number of values each variety field can take in a genre (None: unknown - the set's size bounds it)."""
    from ..endless.genres import get
    g = get(genre) if isinstance(genre, str) else genre
    forms = set(g.forms) | {f for m in g.moods.values() for f in m.get('forms', {})}
    modes = {md for m in g.moods.values() for md, w in m['modes'].items() if w > 0}
    tonics = {t for m in g.moods.values() for md in m['modes'] for t in m['keys'].get(md, [])}
    lo = min(f['tempo'][0] for f in g.feels.values())
    hi = max(f['tempo'][1] for f in g.feels.values())
    from ..endless.arrangement import values
    V = values(g) or {}                    # (the arrangement's own vocabulary; a field with one value cannot vary)
    return {'mood': len(g.moods), 'feel': len(g.feels), 'form': len(forms), 'mode': len(modes), 'key': len(tonics),
            'tempo': hi // TEMPO_BAND - lo // TEMPO_BAND + 1, 'climax_pos': CLIMAX_BINS, 'climax_pitch': 12,
            'ending': None, 'layout': len(V.get('layout') or ()) or 1, 'climax_kind': len(V.get('climax') or ()) or 1}


def norm_entropy(values: list, k: int | None) -> float | None:
    """The values' entropy over the most even spread n values can have over k bins (1 = as varied as the set size
    allows, 0 = all alike). None when the field cannot vary (k = 1, or fewer than 2 values)."""
    n = len(values)
    k = min(k or n, n)
    if n < 2 or k < 2:
        return None

    def h(counts):
        return -sum(c / n * math.log(c / n) for c in counts if c)
    q, r = divmod(n, k)
    best = h([q + 1] * r + [q] * (k - r))
    return round(min(1.0, max(0.0, h(Counter(values).values()) / best)), 3)


def variety(seqs, genre) -> dict:
    """How varied a SET of pieces is (the human verdict 2026-10-12: 'so nicht sehr abwechslungsreich' - every piece
    gentle, minor, 65-68 BPM, the climax a C6 at ~90 %): per field (VARIETY_FIELDS) the normalized entropy (1 = spread
    as evenly as the set size allows over the values the genre has, 0 = every piece alike), the distinct values and
    the most common value's share; 'variety' = the mean over the fields that can vary in the genre. Tempo in
    TEMPO_BAND-BPM bands, the climax position in CLIMAX_BINS bins of the head, its pitch as the MIDI note."""
    heads = [h for h in (header_of(s) for s in seqs) if h]
    ks = value_counts(genre)
    out = {'n': len(heads), 'fields': {}}
    vals = []
    for f in VARIETY_FIELDS:
        xs = [h[f] for h in heads if h.get(f) is not None]
        if f == 'tempo':
            xs = [x // TEMPO_BAND * TEMPO_BAND for x in xs]
        elif f == 'climax_pos':
            xs = [min(CLIMAX_BINS - 1, int(x * CLIMAX_BINS)) for x in xs]
        e = norm_entropy(xs, ks[f])
        top = Counter(xs).most_common(1)
        out['fields'][f] = {'h': e, 'distinct': len(set(xs)), 'top': top[0][0] if top else None,
                            'top_share': round(top[0][1] / len(xs), 2) if top else None}
        if e is not None:
            vals.append(e)
    out['variety'] = round(sum(vals) / len(vals), 3) if vals else None
    return out


def variety_line(v: dict) -> str:
    """One printable line: the overall number, then per field its entropy (the most common value, its share)."""
    parts = [f"{f} {d['h']:.2f} ({d['top']} {d['top_share']:.0%})" for f, d in v['fields'].items()
             if d['h'] is not None]
    return f"variety {v['variety']} (n {v['n']}): " + ', '.join(parts)
