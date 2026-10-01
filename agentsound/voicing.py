"""Voicing and voice leading: chords voiced into real parts - a choir (SATB), a string section, a wind choir, a horn
quartet, any set of voices - around lines written by hand, and a check of the written result.

    from agentsound import voicing as vc
    table = [(2, 'Cm', 'G5', 'C3'), (2, 'Fm/Ab', None, 'Ab2'), (1, 'G7', 'F5', 'G2'), (1, 'Cm', 'Eb5', 'C3')]
    parts = vc.chorale(table, t0=0, voices=vc.STRINGS, key='C minor')     # {voice: [(start, dur, pitch)]}
    parts = vc.chorale(table, voices=vc.WINDS8, key='C minor')            # eight interlocked wind parts
    for issue in vc.check(parts, vc.timeline(table), voices=vc.STRINGS):  # parallels / clashes / ranges ...
        print(issue)

The voicer (`voice()`) takes, chord by chord, the voices written by hand as fixed ('fixed': {voice: pitch}) and
chooses the free ones: chord tones inside each voice's range, strictly descending from the top voice to the bass
(no crossing, no unison), adjacent upper voices at most `spacing` semitones apart (the bass up to `bass_gap` under
its neighbour), complete chords (third, seventh, root - a dim7 needs no root - and the fifth if it can), never the
leading tone or the chord's seventh doubled, the smallest total motion from the previous chord (leaps over a fifth
and over an octave cost extra), no parallel fifths / octaves between any two moving voices, the free bass on the
chord's bass note, and no free voice a semitone (or a rubbing whole tone) from the pitches in a step's 'avoid'
(the written lines it sounds against). Big sets (more than four free voices) only look `leap` semitones around each
voice's previous pitch, so a tutti of eight still voices in milliseconds.

`check()` reads any written parts back: parallel fifths / octaves between EVERY pair of voices (not only the free
ones a voicer placed), semitone clashes (minor 2nds, major 7ths, minor 9ths) between voices sounding together,
strong-beat non-chord tones against a harmony timeline, notes outside the ranges and voices crossing. It is advice:
a written suspension or an appoggiatura is a strong-beat non-chord tone on purpose.

The counterpoint helpers (`arpeggiate`, `passing_eighths`) give a fugue's free voices motion - a chord-tone leap on
the last beat of a long note, passing 8ths between notes a third or a fourth apart - only where that makes no
parallels and rubs no semitone against another voice (songs/lux-perpetua's Kyrie, songs/unbowed's fugato).

Voice sets are ordered top to bottom: {name: (lo, hi)} or {name: (lo, hi, centre)} (MIDI pitches; the centre pulls
the first chord, default the middle of the range). Presets: SATB (a choir), STRINGS (violins I / II, violas, cellos
for chords), WINDS (flutes, oboes, clarinets, bassoons, one voice each), WINDS8 (the Classical wind choir: a pair of
each, interlocked), HORNS (4 horns), BRASS (2 trumpets, 2 horns, trombone / bass), TUTTI (8 voices from the top
violins to the basses' octave).
"""

from __future__ import annotations

from collections import Counter, namedtuple

from .theory import ComposeError, Key, chord as _chord, note as _note

__all__ = ['SATB', 'STRINGS', 'WINDS', 'WINDS8', 'HORNS', 'BRASS', 'TUTTI', 'N', 'line', 'length', 'ChordInfo', 'info',
           'leading_tone', 'voice', 'satb', 'chorale', 'timeline', 'harmony_at', 'Issue', 'check', 'summary',
           'arpeggiate', 'passing_eighths', 'parallel_or_rub', 'merge_ties']

# --------------------------------------------------------------------------------------------------- voice sets

SATB = {'S': (60, 79, 70), 'A': (55, 72, 64), 'T': (48, 67, 57), 'B': (43, 62, 50)}
"""A choir: soprano C4-G5, alto G3-C5, tenor C3-G4, bass G2-D4 (centres Bb4 E4 A3 D3)."""
STRINGS = {'violins1': (64, 88, 74), 'violins2': (57, 81, 67), 'violas': (50, 74, 62), 'cellos': (36, 62, 48)}
"""A string section's chord in four real parts: violins I E4-E6, violins II A3-A5, violas D3-D5, cellos C2-D4 (the
basses double the cellos an octave lower)."""
WINDS = {'flutes': (67, 91, 79), 'oboes': (62, 84, 72), 'clarinets': (53, 79, 65), 'bassoons': (38, 65, 50)}
"""One voice per wind section, flutes on top (G4-G6), oboes D4-C6, clarinets F3-G5, bassoons D2-F4."""
WINDS8 = {'fl1': (72, 93, 81), 'fl2': (67, 88, 77), 'ob1': (64, 86, 74), 'ob2': (62, 81, 70),
          'cl1': (58, 79, 67), 'cl2': (53, 74, 62), 'bn1': (45, 67, 55), 'bn2': (36, 60, 46)}
"""The Classical wind choir, a pair of each (2 fl, 2 ob, 2 cl, 2 bn) interlocked from C5-A6 down to C2-C4."""
HORNS = {'hn1': (60, 77, 69), 'hn2': (55, 72, 64), 'hn3': (52, 69, 60), 'hn4': (43, 64, 52)}
"""Four horns (sounding): C4-F5, G3-C5, E3-A4, G2-E4 - the orchestra's pad."""
BRASS = {'tp1': (62, 81, 72), 'tp2': (57, 76, 67), 'hn1': (53, 72, 62), 'hn2': (48, 67, 57), 'tb': (36, 60, 48)}
"""2 trumpets, 2 horns, a trombone / bass voice: a fanfare chord."""
TUTTI = {'v1': (72, 96, 81), 'v2': (65, 88, 74), 'v3': (60, 81, 69), 'v4': (55, 76, 64), 'v5': (50, 71, 59),
         'v6': (45, 67, 55), 'v7': (40, 60, 48), 'v8': (28, 50, 38)}
"""Eight voices for a full tutti chord, top (C5-C7) to the basses' octave (E1-D3): distribute them over the
sections (v1 flutes / violins I, v8 basses + contrabassoon ...)."""


def _voices(voices) -> dict:
    """{name: (lo, hi, centre)} from {name: (lo, hi[, centre])} (ordered top to bottom)."""
    if not isinstance(voices, dict) or not voices:
        raise ComposeError(f"voices must be an ordered dict {{name: (lo, hi[, centre])}} top to bottom, got {voices!r}")
    out = {}
    for v, r in voices.items():
        if not isinstance(r, (tuple, list)) or len(r) not in (2, 3):
            raise ComposeError(f"voice {v!r}: a range is (lo, hi) or (lo, hi, centre), got {r!r}")
        lo, hi = N(r[0]), N(r[1])
        if hi <= lo:
            raise ComposeError(f"voice {v!r}: range {r!r} is empty (lo must be under hi)")
        out[v] = (lo, hi, float(r[2]) if len(r) == 3 else (lo + hi) / 2.0)
    return out


# --------------------------------------------------------------------------------------------------- notation

def N(p) -> int:
    """A pitch: a MIDI number or a note name ('C#4')."""
    return p if isinstance(p, int) else _note(p)


def line(spec: str, t0: float = 0.0, shift: int = 0) -> list:
    """'D4:1 A4:.5 r:1 | ...' -> [(start, dur, pitch)] from t0 (bars '|' are only for the eye; r or - is a rest;
    shift transposes in semitones)."""
    out, t = [], float(t0)
    for tok in spec.replace('|', ' ').split():
        if ':' not in tok:
            raise ComposeError(f"line(): token {tok!r} is not pitch:duration (e.g. 'C5:1.5', 'r:1')")
        p, d = tok.split(':')
        d = float(d)
        if p not in ('r', '-'):
            out.append((t, d, N(p) + shift))
        t += d
    return out


def length(spec: str) -> float:
    """The length of a line() spec in beats."""
    return sum(float(tok.split(':')[1]) for tok in spec.replace('|', ' ').split())


def merge_ties(notes: list) -> list:
    """Join repeated pitches that touch ([(start, dur, pitch)], sorted) into one held note."""
    out = []
    for n in notes:
        if out and out[-1][2] == n[2] and abs(out[-1][0] + out[-1][1] - n[0]) < 1e-6:
            out[-1] = (out[-1][0], out[-1][1] + n[1], n[2])
        else:
            out.append(tuple(n[:3]))
    return out


# --------------------------------------------------------------------------------------------------- chords

class ChordInfo:
    """A chord symbol's functions for voicing: pcs, root, bass, third, fifth, seventh (pitch classes or None),
    major, dim7."""

    def __init__(self, sym: str):
        c = _chord(sym)
        self.sym = sym
        self.pcs = set(c.pcs)
        r = self.root = c.root
        self.bass = c.bass if c.bass is not None else r
        pick = lambda cands: next((x % 12 for x in cands if x % 12 in self.pcs), None)   # noqa: E731
        self.third = pick((r + 4, r + 3)) if pick((r + 4, r + 3)) is not None else pick((r + 5, r + 2))
        self.fifth = pick((r + 7, r + 6, r + 8))
        self.seventh = next((x % 12 for x in (r + 10, r + 11, r + 9) if x % 12 in self.pcs
                             and x % 12 not in (self.third, self.fifth)), None)
        self.major = self.third == (r + 4) % 12
        self.dim7 = self.third == (r + 3) % 12 and self.fifth == (r + 6) % 12 and self.seventh == (r + 9) % 12

    def __repr__(self) -> str:
        return f"ChordInfo({self.sym!r})"


_INFO: dict = {}


def info(sym: str) -> ChordInfo:
    """ChordInfo of a chord symbol (cached)."""
    if sym not in _INFO:
        _INFO[sym] = ChordInfo(sym)
    return _INFO[sym]


def leading_tone(key) -> int:
    """The leading tone's pitch class of a key ('C minor' -> 11: B natural, also in minor)."""
    k = key if isinstance(key, Key) else Key(key)
    return (k.tonic - 1) % 12


# --------------------------------------------------------------------------------------------------- the voicer

def _score(cur: dict, prev: dict, ci: ChordInfo, lt, free_b: bool, free, avoid, order, rng, spacing: int,
           bass_gap: int, unison: bool = False) -> float:
    vs = [v for v in order if v in cur]
    ps = [cur[v] for v in vs]
    for a, b in zip(ps, ps[1:]):
        if a < b or (a == b and not unison):
            return 1e9
    sc = 0.0
    for v1, v2 in zip(order[:-2], order[1:-1]):
        if v1 in cur and v2 in cur and cur[v1] - cur[v2] > spacing:
            sc += 15 * (cur[v1] - cur[v2] - spacing)
    t_, b_ = order[-2:] if len(order) >= 2 else (None, None)
    if t_ in cur and b_ in cur and cur[t_] - cur[b_] > bass_gap:
        sc += 5
    pcs = [p % 12 for p in ps]
    have = set(pcs)
    if len(ps) >= 3:
        if ci.third is not None and ci.third not in have:
            sc += 40
        if ci.seventh is not None and ci.seventh not in have:
            sc += 25
        if ci.root not in have and not ci.dim7:
            sc += 30
        if ci.fifth is not None and ci.fifth not in have:
            sc += 4
    cnt = Counter(p for p in pcs if p in ci.pcs)
    if lt is not None and cnt.get(lt, 0) > 1:
        sc += 40
    if ci.seventh is not None and cnt.get(ci.seventh, 0) > 1:
        sc += 40
    if ci.major and cnt.get(ci.third, 0) > 1:
        sc += 6
    if len(ps) > 4:                    # big sets: double the root first, then the fifth, the third least
        sc += 2 * max(0, cnt.get(ci.third, 0) - 1)
        if ci.fifth is not None:
            sc += 1 * max(0, cnt.get(ci.fifth, 0) - cnt.get(ci.root, 0))
    if free_b and b_ in cur:
        sc += 0 if cur[b_] % 12 == ci.bass else 18
    for v, p in cur.items():
        q = prev.get(v)
        if q is not None:
            d = abs(p - q)
            sc += d + (8 if d > 7 else 0) + (20 if d > 12 else 0)
        else:
            sc += 0.15 * abs(p - rng[v][2])
    for v in free:                    # no free voice a semitone (or rubbing whole tone) from a written line's notes
        for x in avoid:
            d = abs(cur[v] - x)
            sc += 45 if d == 1 else 12 if d == 2 else 0
    moved = [v for v in cur if prev.get(v) is not None]
    for i in range(len(moved)):
        for j in range(i + 1, len(moved)):
            a, b = moved[i], moved[j]
            if cur[a] == prev[a] and cur[b] == prev[b]:
                continue
            i0, i1 = abs(prev[a] - prev[b]) % 12, abs(cur[a] - cur[b]) % 12
            if i0 == i1 and i0 in (0, 7) and cur[a] != prev[a]:
                sc += 60
    return sc


def voice(steps: list, *, voices=None, lt=None, key=None, prev: dict | None = None, center: dict | None = None,
          spacing: int = 12, bass_gap: int = 19, leap: int | None = None, unison: bool = False) -> list:
    """Voice a chord sequence. steps: [{'chord': sym, 'fixed': {voice: pitch}, 'active': voices, 'lt': pc,
    'avoid': pitches}] -> one {voice: pitch} per step (fixed voices kept, the free ones chosen; only the step's
    active voices - default all - sound). voices: the ordered voice set (SATB default; STRINGS, WINDS8, HORNS ...).
    lt: the leading tone's pitch class, never doubled (or key='C minor'); a step's 'lt' overrides it. prev: the
    voicing before the first step. center: {voice: pitch} that pulls the first chord (default the ranges'
    centres). spacing: the most semitones between adjacent upper voices (bass_gap under the lowest pair). leap:
    look only this far around each voice's previous pitch (default: everything for up to four free voices, 9 above
    that). unison=True lets neighbouring voices share a pitch (orchestral doublings: oboe 2 and clarinet 1 on one
    note) - big sets voiced in a narrow span need it; still no crossing. Raises ComposeError when a step cannot be voiced (say which fixed pitches block it)."""
    rng = _voices(voices if voices is not None else SATB)
    if center:
        rng = {v: (lo, hi, float(center.get(v, c))) for v, (lo, hi, c) in rng.items()}
    order = tuple(rng)
    if lt is None and key is not None:
        lt = leading_tone(key)
    prev = dict(prev or {})
    out = []
    for st in steps:
        ci = info(st['chord'])
        active = tuple(st.get('active', order))
        unknown = [v for v in active if v not in rng]
        if unknown:
            raise ComposeError(f"voice(): unknown voice(s) {unknown} (the voice set has {', '.join(order)})")
        fixed = {v: N(p) for v, p in (st.get('fixed') or {}).items() if p is not None and v in active}
        free = [v for v in active if v not in fixed]
        win = leap if leap is not None else (9 if len(free) > 4 else None)
        cands = []
        for v in free:
            c = [p for p in range(rng[v][0], rng[v][1] + 1) if p % 12 in ci.pcs]
            q = prev.get(v)
            if win is not None and q is not None:
                near = [p for p in c if abs(p - q) <= win]
                c = near or c
            cands.append(c)
        pos = {v: i for i, v in enumerate(order)}
        best = [None]
        lt_ = st.get('lt', lt)
        avoid = st.get('avoid', ())

        def walk(i: int, known: dict, combo: list):
            if i == len(free):
                cur = dict(fixed)
                cur.update(zip(free, combo))
                sc = _score(cur, prev, ci, lt_, order[-1] in free, free, avoid, order, rng, spacing, bass_gap,
                            unison)
                if best[0] is None or sc < best[0][0]:
                    best[0] = (sc, cur)
                return
            v = free[i]
            pv = pos[v]
            for p in cands[i]:
                if any((pos[w] < pv and (q < p or (q == p and not unison)))
                       or (pos[w] > pv and (q > p or (q == p and not unison))) for w, q in known.items()):
                    continue
                known[v] = p
                combo.append(p)
                walk(i + 1, known, combo)
                combo.pop()
                del known[v]

        walk(0, dict(fixed), [])
        if (best[0] is None or best[0][0] >= 1e9) and win is not None:      # the window was too tight: look wider
            cands = [[p for p in range(rng[v][0], rng[v][1] + 1) if p % 12 in ci.pcs] for v in free]
            walk(0, dict(fixed), [])
        if best[0] is None or best[0][0] >= 1e9:
            raise ComposeError(f"voice(): cannot voice {st['chord']} with {fixed} in "
                               f"{ {v: rng[v][:2] for v in active} } (fixed voices out of order, or no chord tone "
                               f"fits a free voice's range between them)")
        out.append(best[0][1])
        for v in order:
            prev[v] = best[0][1].get(v)
    return out


def satb(steps: list, *, lt=None, key=None, ranges=None, prev=None, center=None) -> list:
    """voice() for a four-part choir (SATB), or `ranges` with the same four names."""
    return voice(steps, voices=ranges or SATB, lt=lt, key=key, prev=prev, center=center)


def chorale(table: list, t0: float = 0.0, *, voices=None, lt=None, key=None, ranges=None, prev=None,
            tie: bool = False, active=None, center=None, spacing: int = 12, bass_gap: int = 19,
            leap: int | None = None, unison: bool = False) -> dict:
    """Homophonic writing from a table of (dur, chord, top, bass[, {voice: pitch}]) rows: top / bass fix the first /
    last voice of the set (None = free), the dict fixes others; a row with chord None is a rest. Returns {voice:
    [(start, dur, pitch)]}, every voice in the table's rhythm (tie=True merges repeated pitches into held notes).
    voices: the voice set (SATB default; `ranges` is the same, kept for old calls); active: the voices that sing."""
    rng = _voices(voices if voices is not None else (ranges or SATB))
    order = tuple(rng)
    act = tuple(active) if active is not None else order
    steps, times = [], []
    t = float(t0)
    for row in table:
        dur, sym, top, bass, *more = row
        if sym is not None:
            steps.append({'chord': sym, 'fixed': {order[0]: top, order[-1]: bass, **(more[0] if more else {})},
                          'active': act})
            times.append((t, dur))
        t += dur
    voiced = voice(steps, voices=rng, lt=lt, key=key, prev=prev, center=center, spacing=spacing, bass_gap=bass_gap,
                   leap=leap, unison=unison)
    out = {v: [] for v in act}
    for (t, dur), vc in zip(times, voiced):
        for v in act:
            p = vc.get(v)
            if p is None:
                continue
            last = out[v][-1] if out[v] else None
            if tie and last and last[2] == p and abs(last[0] + last[1] - t) < 1e-6:
                out[v][-1] = (last[0], last[1] + dur, p)
            else:
                out[v].append((t, dur, p))
    return out


def harmony_at(harm: list, t: float) -> str | None:
    """harm: [(start, dur, chord)] -> the chord sounding at t."""
    for s, d, c in harm:
        if s - 1e-6 <= t < s + d - 1e-6:
            return c
    return None


def timeline(table: list, t0: float = 0.0) -> list:
    """(dur, chord, ...) rows -> [(start, dur, chord)]."""
    out, t = [], float(t0)
    for row in table:
        if row[1] is not None:
            out.append((t, row[0], row[1]))
        t += row[0]
    return out


# --------------------------------------------------------------------------------------------------- the check

Issue = namedtuple('Issue', 'kind beat voices pitches text')
"""A finding of check(): kind ('parallel_5th', 'parallel_8ve', 'clash', 'non_chord', 'range', 'crossing'), the beat,
the voices and their pitches, a sentence."""


def _sounding(notes, t):
    for n in notes:
        if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6:
            return n[2]
    return None


def check(parts: dict, harmony: list | None = None, *, voices=None, order=None, strong: float = 1.0,
          t0: float = 0.0, clashes: bool = True, span=None) -> list:
    """Read written parts back: {voice: [(start, dur, pitch, ...)]} (order: top to bottom, default the voice set's
    or the dict's order). Finds parallel fifths / octaves (also by compound intervals and between non-adjacent
    voices: both voices move, in the same direction, onto the same perfect interval class) between EVERY pair of
    voices; semitone clashes (minor 2nd, major 7th, minor 9th) between voices at every onset (clashes=False skips
    them); with harmony ([(start, dur, chord)]) strong-beat non-chord tones (notes starting on a multiple of
    `strong` beats from t0 whose pitch class is not in the chord); with voices (a voice set) notes outside the
    ranges and voices crossing (a voice under the one below it). span=(a, b) limits it to notes starting there.
    Returns [Issue] sorted by beat."""
    rng = _voices(voices) if voices is not None else None
    names = list(order or (rng.keys() if rng else parts.keys()))
    names = [v for v in names if v in parts]
    a0, b0 = (span if span is not None else (-1e18, 1e18))
    ps = {v: sorted(tuple(n[:3]) for n in parts[v]) for v in names}
    out = []

    def inside(t):
        return a0 - 1e-6 <= t < b0 - 1e-6

    onsets = sorted({round(n[0], 6) for v in names for n in ps[v]})
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            u, w = names[i], names[j]
            times = sorted({round(n[0], 6) for n in ps[u]} | {round(n[0], 6) for n in ps[w]})
            last = None
            for t in times:
                pu, pw = _sounding(ps[u], t), _sounding(ps[w], t)
                if pu is None or pw is None:
                    last = None
                    continue
                if last is not None and inside(t):
                    qu, qw = last
                    if pu != qu and pw != qw and (pu - qu) * (pw - qw) > 0:
                        i0, i1 = abs(qu - qw) % 12, abs(pu - pw) % 12
                        if i0 == i1 and i0 in (0, 7):
                            kind = 'parallel_8ve' if i0 == 0 else 'parallel_5th'
                            out.append(Issue(kind, t, (u, w), (pu, pw),
                                             f"{kind.replace('_', ' ')} {u}/{w} at beat {t:g}: "
                                             f"{qu}-{qw} -> {pu}-{pw}"))
                last = (pu, pw)
    if clashes:
        for t in onsets:
            if not inside(t):
                continue
            now = [(v, _sounding(ps[v], t)) for v in names]
            now = [(v, p) for v, p in now if p is not None]
            starting = {v for v in names for n in ps[v] if abs(n[0] - t) < 1e-6}
            for i in range(len(now)):
                for j in range(i + 1, len(now)):
                    (u, pu), (w, pw) = now[i], now[j]
                    if u not in starting and w not in starting:
                        continue
                    if abs(pu - pw) % 12 in (1, 11):
                        out.append(Issue('clash', t, (u, w), (pu, pw),
                                         f"semitone clash {u}/{w} at beat {t:g}: {pu} against {pw}"))
    if harmony:
        for v in names:
            for a, d, p in ps[v]:
                if not inside(a):
                    continue
                pos = (a - t0) / strong
                if abs(pos - round(pos)) > 1e-6:
                    continue
                sym = harmony_at(harmony, a)
                if sym is not None and p % 12 not in info(sym).pcs:
                    out.append(Issue('non_chord', a, (v,), (p,), f"{v} {p} on beat {a:g} is not in {sym}"))
    if rng:
        for v in names:
            if v not in rng:
                continue
            lo, hi, _ = rng[v]
            for a, d, p in ps[v]:
                if inside(a) and not lo <= p <= hi:
                    out.append(Issue('range', a, (v,), (p,), f"{v} {p} at beat {a:g} is outside {lo}-{hi}"))
        for i in range(len(names) - 1):
            u, w = names[i], names[i + 1]
            for t in onsets:
                if not inside(t):
                    continue
                pu, pw = _sounding(ps[u], t), _sounding(ps[w], t)
                if pu is not None and pw is not None and pu < pw:
                    out.append(Issue('crossing', t, (u, w), (pu, pw), f"{u} {pu} under {w} {pw} at beat {t:g}"))
    out.sort(key=lambda x: (x.beat, x.kind))
    return out


def summary(issues: list) -> str:
    """'parallel_5th 2, clash 1' - the issues counted by kind ('clean' when there are none)."""
    c = Counter(i.kind for i in issues)
    return ', '.join(f"{k} {n}" for k, n in sorted(c.items())) or 'clean'


# --------------------------------------------------------------------------------------------------- counterpoint

def parallel_or_rub(parts: dict, v, seq, order=None) -> bool:
    """True when the line seq [(t, pitch) ...] of voice v (its first and last entries are the notes around the new
    ones) makes parallel fifths / octaves with another voice of parts, or a new note rubs a semitone / minor ninth
    against one (at its onset or a 16th later)."""
    for w in (order or tuple(parts)):
        if w == v or w not in parts:
            continue
        for t, u in seq[1:-1]:
            if any(q is not None and abs(u - q) % 12 in (1, 11)
                   for q in (_sounding(parts[w], t), _sounding(parts[w], t + 0.25))):
                return True
        for (ta, ua), (tb, ub) in zip(seq, seq[1:]):
            wa, wb = _sounding(parts[w], ta), _sounding(parts[w], tb)
            if None in (wa, wb) or wa == wb or ua == ub or (ub - ua) * (wb - wa) <= 0:
                continue
            if abs(ua - wa) % 12 == abs(ub - wb) % 12 and abs(ua - wa) % 12 in (0, 7):
                return True
    return False


def arpeggiate(parts: dict, free: set, harmony: list, t0: float, *, voices=None, until: float | None = None) -> list:
    """Free voices move in quarters: a free note of 2 beats or more gives its last beat to another tone of its chord
    (a leap of a third to a fifth) that approaches the next note by step or third, where that makes no parallels or
    rubs. parts: {voice: [(start, dur, pitch)]} (song beats, sorted; the voice set's order), free: {(voice,
    round(start, 4))} of the free notes (the new ones are added), harmony: [(start, dur, chord)] from t0, until:
    beats from t0 after which nothing changes. Edits parts in place; returns [(beat, voice, pitch)]."""
    rng = _voices(voices if voices is not None else SATB)
    order = tuple(v for v in rng if v in parts)
    lim = float('inf') if until is None else float(until)
    added = []
    for v in order:
        out = []
        ns = parts[v]
        lo, hi = rng[v][0], rng[v][1]
        for i, (a, d, p1) in enumerate(ns):
            nxt = ns[i + 1] if i + 1 < len(ns) else None
            c = None
            if ((v, round(a, 4)) in free and d >= 2 - 1e-6 and nxt is not None and abs(a + d - nxt[0]) < 1e-6
                    and a + d - t0 <= lim):
                sym = harmony_at([(x + t0, y, z) for x, y, z in harmony], a + d - 1)
                pcs = set(_chord(sym).pcs) if sym else set()
                cands = [q for q in range(lo, hi + 1) if q % 12 in pcs and 3 <= abs(q - p1) <= 7
                         and 1 <= abs(q - nxt[2]) <= 4]
                for q in sorted(cands, key=lambda q: (abs(q - nxt[2]), abs(q - p1))):
                    if not parallel_or_rub(parts, v, [(a + d - 1.01, p1), (a + d - 1, q), (a + d, nxt[2])], order):
                        c = q
                        break
            if c is None:
                out.append((a, d, p1))
            else:
                out.append((a, d - 1, p1))
                out.append((a + d - 1, 1.0, c))
                free.add((v, round(a + d - 1, 4)))
                added.append((a + d - 1, v, c))
        parts[v] = out
    return added


def _key_fn(key_at):
    if callable(key_at):
        return key_at
    k = key_at if isinstance(key_at, Key) else Key(key_at)
    pcs = {p % 12 for p in k.notes(60, 71)}
    lt = (k.tonic - 1) % 12
    return lambda t: (pcs, k.tonic, lt)


def passing_eighths(parts: dict, free: set, t0: float, key_at, *, order=None, until: float | None = None) -> list:
    """Counterpoint for free voices: a free note that moves a third to the next note gives its last 8th to the step
    between, one that moves a fourth its last two 8ths (the scale of the local key; the leading tone into the
    tonic) - unless that makes parallel fifths / octaves with another voice or rubs a semitone / minor ninth against
    one. parts: {voice: [(start, dur, pitch)]} (song beats, sorted), free: {(voice, round(start, 4))} of the free
    notes, key_at: a key ('C minor' / Key) or a function of the beat from t0 -> (scale pcs, tonic pc, leading-tone
    pc); until: beats from t0 after which nothing changes. Edits parts in place; returns [(beat, voice, pitch)]."""
    kf = _key_fn(key_at)
    names = tuple(order or parts)
    lim = float('inf') if until is None else float(until)
    added = []
    for v in names:
        out = []
        ns = parts[v]
        for i, (a, d, p1) in enumerate(ns):
            nxt = ns[i + 1] if i + 1 < len(ns) else None
            gap = abs(nxt[2] - p1) if nxt is not None else 0
            k = 1 if 3 <= gap <= 4 else 2 if gap == 5 else 0
            ok = ((v, round(a, 4)) in free and k and d >= 0.5 * k + 0.5 - 1e-6 and abs(a + d - nxt[0]) < 1e-6
                  and a + d - t0 <= lim)
            xs = None
            if ok:
                p2 = nxt[2]
                tp = a + d - 0.5 * k
                pcs, tonic, lt = kf(tp - t0)
                if p2 % 12 == tonic and p2 > p1:
                    pcs = (pcs - {(tonic - 2) % 12}) | {lt}
                cands = [q for q in range(min(p1, p2) + 1, max(p1, p2)) if q % 12 in pcs]
                if len(cands) == k:
                    xs = cands if p2 > p1 else cands[::-1]
                    seq = [(tp - 0.01, p1)] + [(tp + 0.5 * j, x) for j, x in enumerate(xs)] + [(a + d, p2)]
                    if parallel_or_rub(parts, v, seq, names):
                        xs = None
            if xs is None:
                out.append((a, d, p1))
            else:
                out.append((a, d - 0.5 * k, p1))
                for j, x in enumerate(xs):
                    out.append((a + d - 0.5 * k + 0.5 * j, 0.5, x))
                    added.append((a + d - 0.5 * k + 0.5 * j, v, x))
        parts[v] = out
    return added
