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

import math
from collections import Counter, namedtuple

from .patterns import Clip, as_clip
from .theory import Chord, ComposeError, Key, Progression, chord as _chord, note as _note

__all__ = ['SATB', 'STRINGS', 'WINDS', 'WINDS8', 'HORNS', 'BRASS', 'TUTTI', 'N', 'line', 'length', 'ChordInfo', 'info',
           'leading_tone', 'voice', 'satb', 'chorale', 'timeline', 'harmony_at', 'Harmony', 'Issue', 'check',
           'summary', 'arpeggiate', 'passing_eighths', 'parallel_or_rub', 'merge_ties', 'window', 'trim', 'fugue',
           'Fugue', 'imitation']

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


def window(notes, a: float, b: float | None = None) -> list:
    """The notes [(start, ...)] starting in [a, b) (nothing moves or is cut; Clip.window for tuples)."""
    hi = float('inf') if b is None else float(b)
    return [n for n in notes if a - 1e-6 <= n[0] < hi - 1e-6]


def trim(notes, a: float, b: float | None = None) -> list:
    """The notes [(start, dur, pitch, ...)] cut to the span [a, b): notes outside are dropped, notes crossing an
    edge shortened to it (a voice entering late: its line from beat a on)."""
    hi = float('inf') if b is None else float(b)
    out = []
    for n in notes:
        s, e = n[0], n[0] + n[1]
        if e <= a + 1e-6 or s >= hi - 1e-6:
            continue
        d = n[1]
        if s < a:
            s, d = a, e - a
        if s + d > hi:
            d = hi - s
        out.append((s, d) + tuple(n[2:]))
    return out


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


# --------------------------------------------------------------------------------------------------- Harmony

def _is_table(spec) -> bool:
    return (isinstance(spec, (list, tuple)) and len(spec) > 0 and isinstance(spec[0], (list, tuple))
            and len(spec[0]) >= 4 and isinstance(spec[0][0], (int, float)) and not isinstance(spec[0][0], bool))


class Harmony(Progression):
    """ONE harmony object: chords over time, written as a progression (Progression syntax, chord lengths in bars:
    `s.prog('Cm Ab Fm G7')` returns one) or as a voicing table [(dur, chord, top, bass[, {voice: pitch}])] (beats;
    top / bass are the structural outer voices, None = free; chord None = a rest). It IS a Progression (every player
    takes it: pianist, bassist, chords(), .bass(), .at() ...) and voices itself:

        h = Harmony(T1, key='C minor', at=t1)              # a table placed at a section (or s.harmony(T1, at=t1))
        h.at(t1.start + 4)                                 # the Chord sounding there (info_at: voicing.ChordInfo)
        h.chorale(STRINGS, tie=True)                       # real parts in the table's rhythm {voice: [(s, d, p)]}
        h.under(melody, STRINGS)                           # the parts under a written line (the line is their top)
        h.under(line, 3)                                   # block harmony: 2 chord tones under each note (a Clip)
        h.voice(('G4', 'Eb5'), 2, vel=42)                  # a section's divisi share of each chord (a Clip)
        h.tutti()                                          # the full orchestra's 8-voice chord (TUTTI)
        h[3:9], h.transpose(-3), h.place(at), h.figure('oompah')

    Positions in and out of the methods are in the harmony's frame: `at` + its own beats (at=0: its own beats).
    Iterating it yields (start, dur, Chord) in its own beats, like any Progression."""

    def __init__(self, spec, key=None, *, at=0.0, bars: float = 1, beats_per_bar: float = 4):
        origin = float(getattr(at, 'start', at))
        if isinstance(spec, Harmony):
            self._init_rows(spec._rows, spec.key if key is None else Key(key), spec.beats_per_bar,
                            origin if at else spec.origin, spec._table)
            return
        if _is_table(spec):
            self._init_rows(spec, None if key is None else Key(key), float(beats_per_bar), origin, True)
            return
        super().__init__(spec, key=key, bars=bars, beats_per_bar=beats_per_bar)
        rows = [(d, None if c is None else c.symbol, None, None) for c, d in self.items]
        self._init_rows(rows, self.key, self.beats_per_bar, origin, False, chords=[c for c, _ in self.items])

    def _init_rows(self, rows, key, bpb, origin, table, chords=None):
        self._rows = [tuple(r) for r in rows]
        self._table = bool(table)
        self.key = key
        self.beats_per_bar = float(bpb)
        self.origin = float(origin)
        if chords is None:
            chords = [None if r[1] is None else (r[1] if isinstance(r[1], Chord) else _chord(r[1]))
                      for r in self._rows]
            self._rows = [(r[0], r[1].symbol if isinstance(r[1], Chord) else r[1]) + r[2:] for r in self._rows]
        self.items = [(c, float(r[0])) for c, r in zip(chords, self._rows)]
        self._tl, t = [], self.origin               # absolute (start, dur, row index) of the chords, as timeline()
        for i, r in enumerate(self._rows):
            if r[1] is not None:
                self._tl.append((t, r[0], i))
            t += r[0]

    def _new(self, rows, origin=None, table=None) -> 'Harmony':
        h = Harmony.__new__(Harmony)
        h._init_rows(rows, self.key, self.beats_per_bar, self.origin if origin is None else origin,
                     self._table if table is None else table)
        return h

    # --- as data
    @property
    def table(self) -> list:
        """The rows (dur, chord symbol, top, bass[, {voice: pitch}]) - a voicing table."""
        return list(self._rows)

    def timeline(self) -> list:
        """[(start, dur, chord symbol)] in the harmony's frame (voicing.timeline)."""
        return [(a, d, self._rows[i][1]) for a, d, i in self._tl]

    def __repr__(self) -> str:
        at = f", at={self.origin:g}" if self.origin else ''
        return f"Harmony({len(self._rows)} chords, {self.length:g} beats{at})"

    # --- queries
    def _index(self, t: float):
        if self._table:
            for a, d, i in self._tl:
                if a - 1e-6 <= t < a + d - 1e-6:
                    return i
            return None
        b = t - self.origin
        b = b % self.length if self.length else 0.0
        s = 0.0
        for i, (c, d) in enumerate(self.items):
            if s <= b + 1e-9 < s + d:
                return i
            s += d
        return len(self.items) - 1

    def at(self, beat: float):
        """The Chord sounding at `beat` (the harmony's frame; None in a rest). A progression wraps around its length
        (Progression.at), a table is None outside its span."""
        i = self._index(float(beat))
        return None if i is None else self.items[i][0]

    def symbol_at(self, beat: float) -> str | None:
        """The chord symbol written at `beat` (as in the table)."""
        i = self._index(float(beat))
        return None if i is None else self._rows[i][1]

    def info_at(self, beat: float) -> ChordInfo | None:
        """voicing.ChordInfo (root, third, fifth, seventh ...) of the chord at `beat`."""
        sym = self.symbol_at(beat)
        return None if sym is None else info(sym)

    # --- transforms (a Harmony stays a Harmony)
    def __getitem__(self, i):
        """h[3:9]: those rows, placed where they sound (the frame moves with them); h[k]: one row."""
        if isinstance(i, slice):
            if i.step not in (None, 1):
                raise ComposeError("Harmony slices take no step")
            a = 0 if i.start is None else (i.start if i.start >= 0 else len(self._rows) + i.start)
            t = self.origin
            for r in self._rows[:a]:
                t += r[0]
            return self._new(self._rows[i], origin=t)
        return self._rows[i]

    def place(self, at) -> 'Harmony':
        """The same harmony placed at `at` (a beat or Section): its frame starts there."""
        return self._new(self._rows, origin=float(getattr(at, 'start', at)))

    def transpose(self, semitones: int) -> 'Harmony':
        """Chords, tops, basses and fixed voices moved by semitones."""
        rows = []
        for r in self._rows:
            dur, sym, top, bass, *more = r + (None,) * (4 - len(r))
            if sym is None:
                rows.append(r)
                continue
            fx_ = [{v: N(p) + semitones for v, p in more[0].items()}] if more and more[0] else []
            rows.append((dur, _chord(sym).transpose(semitones).symbol, None if top is None else N(top) + semitones,
                         None if bass is None else N(bass) + semitones, *fx_))
        return self._new(rows)

    def __add__(self, other) -> 'Harmony':
        o = other if isinstance(other, Harmony) else Harmony(other, key=self.key, beats_per_bar=self.beats_per_bar)
        return self._new(self._rows + o._rows, table=self._table or o._table)

    def __mul__(self, n: int) -> 'Harmony':
        return self._new(self._rows * int(n))

    __rmul__ = __mul__

    def stretch(self, factor: float) -> 'Harmony':
        return self._new([(r[0] * factor,) + r[1:] for r in self._rows])

    # --- voicing
    def chorale(self, voices=None, *, key=None, **kw) -> dict:
        """voicing.chorale over the rows (their tops / basses / fixed voices kept), placed in the frame: real parts
        {voice: [(start, dur, pitch)]} (voices: a voice set, SATB default; key: the leading tone, default the
        harmony's key; tie=, active=, lt=, prev=, center=, spacing=, bass_gap=, leap=, unison= as chorale())."""
        return chorale(self._rows, self.origin, voices=voices, key=self.key if key is None else key, **kw)

    def under(self, melody, voices=3, *, top=None, floor=48, gap=3, vel=0.88, key=None, tie=True, **kw):
        """The harmony under a written melody.
        voices = a voice set (STRINGS, SATB, {name: (lo, hi)} ...): real parts voice-led in the harmony's rhythm with
          the melody's sounding note (else the row's top) as the top voice `top` (default the set's first) and the
          melody's other notes avoided; returns the lower voices {voice: [(start, dur, pitch)]} (tie=True holds
          repeated pitches; key / chorale options as chorale()). melody: notes or a Clip in the frame.
        voices = a count: block harmony in the melody's rhythm (a choir / brass section): each note gets `voices` - 1
          chord tones below it (of the chord at its onset), at least `gap` semitones apart, never under `floor`, at
          `vel` x its velocity; returns a Clip with the melody."""
        if isinstance(voices, int):
            lines = as_clip(melody)
            out = []
            for n in lines:
                c = self.at(n.start)
                pcs = set(c.pcs) if c is not None else set()
                out.append((n.start, n.dur, n.pitch, n.vel))
                p, got = n.pitch - gap, 0
                last = n.pitch
                while got < voices - 1 and p >= N(floor):
                    if p % 12 in pcs and last - p >= gap:
                        out.append((n.start, n.dur, p, max(1, round(n.vel * vel))))
                        last, got = p, got + 1
                        p -= gap
                    else:
                        p -= 1
            return Clip(out, length=lines.length)
        rng = _voices(voices)
        top = top or next(iter(rng))
        mel = [(n[0], n[1], n[2]) for n in melody]
        rows, t = [], self.origin
        for row in self._rows:
            dur, sym, ttop, bass, *more = row
            if sym is not None:
                now = [n[2] for n in mel if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6]
                rows.append((dur, sym, now[0] if now else ttop, bass, *more))
            else:
                rows.append(row)
            t += dur
        p = chorale(rows, self.origin, voices=voices, key=self.key if key is None else key, tie=tie, **kw)
        p.pop(top, None)
        return p

    def tutti(self, *, top_shift: int = 12, bass_shift: int = -12, key=None, voices=None, unison: bool = True) -> dict:
        """The full orchestra's chord: TUTTI voices (v1 = the row's top + top_shift, v8 = its bass + bass_shift) in
        the rows' rhythm (unison doublings allowed) -> {v1..v8: [(start, dur, pitch)]}."""
        rows = [(r[0], r[1], None if r[2] is None else N(r[2]) + top_shift,
                 None if r[3] is None else N(r[3]) + bass_shift) for r in self._rows]
        return chorale(rows, self.origin, voices=voices or TUTTI, key=self.key if key is None else key,
                       unison=unison)

    def voice(self, register, voices: int = 2, vel: float = 60, *, phrase: float = 16.0, top: float = 1.0,
              inner: float = 0.9, swing=(1.06, 0.95)):
        """A section's divisi share of each chord inside a narrow register: `voices` chord tones (the most different
        pitch classes, no seconds, the smallest movement from the chord before), held for the chord. Velocities: a
        `phrase`-beat sine arc around `vel`, every other chord x swing[0] / swing[1], the top note x top, the others
        x inner. A Clip in the frame."""
        from itertools import combinations
        lo, hi = N(register[0]), N(register[1])
        out, prev = [], None
        for i, (st, ln, c) in enumerate(self):
            if c is None:
                continue
            cand = [p for p in range(lo, hi + 1) if p % 12 in c.pcs]
            best, best_cost = None, None
            for comb in combinations(cand, min(voices, len(cand))):
                if any(b - a < 3 for a, b in zip(comb, comb[1:])):
                    continue
                cost = -12 * len({p % 12 for p in comb})
                cost += sum(min(abs(p - q) for q in prev) for p in comb) if prev else -0.05 * sum(comb)
                if best_cost is None or cost < best_cost:
                    best, best_cost = comb, cost
            best = best or tuple(cand[-voices:])
            arc = 0.84 + 0.3 * math.sin(math.pi * ((st / phrase) % 1.0 + 0.125))
            v = vel * arc * (swing[0] if i % 2 == 0 else swing[1])
            out += [(st + self.origin, ln, p, max(1, min(127, round(v * (top if p == best[-1] else inner)))))
                    for p in best]
            prev = best
        return Clip(out, length=self.length + self.origin)

    def figure(self, kind: str, **kw):
        """A chord figure of agentsound.figures ('oompah', 'alberti', 'broken', 'ostinato', 'storm16') over the
        harmony, in the frame."""
        from .figures import CHORD_FIGURES, figure
        if kind not in CHORD_FIGURES:
            raise ComposeError(f"Harmony.figure: {kind!r} repeats held notes - voice the harmony first "
                               f"(h.voice(...).figure({kind!r}) or figures.figure(parts, {kind!r})); chord figures: "
                               f"{', '.join(CHORD_FIGURES)}")
        c = figure(self, kind, **kw)
        if isinstance(c, tuple):
            return tuple(x.shift(self.origin).with_length(x.length + self.origin) if self.origin else x for x in c)
        return c.shift(self.origin).with_length(c.length + self.origin) if self.origin else c


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


# --------------------------------------------------------------------------------------------------- fugue

def _material(m, names: dict, at: float, shift: int) -> list:
    """An entry's notes from a name ('subject' ...), a line() spec, notation or (start, dur, pitch) notes."""
    m = names.get(m, m) if isinstance(m, str) else m
    if m is None:
        raise ComposeError("fugue: an entry names material ('subject' / 'answer' / 'counter') that was not given")
    if isinstance(m, str):
        if ':' in m and '/' not in m:
            return line(m, float(at), shift)
        from .notation import notes as _notes
        return [(float(at) + n.start, n.dur, n.pitch + shift) for n in _notes(m)]
    return [(float(at) + n[0], n[1], N(n[2]) + shift) for n in m]


def _key_spans(spans):
    fns = [(float(a), _key_fn(k)) for a, k in spans]

    def f(t):
        cur = fns[0][1]
        for a, fn in fns:
            if a <= t + 1e-9:
                cur = fn
        return cur(t)
    return f


class Fugue:
    """voicing.fugue()'s result: .parts {voice: [(start, dur, pitch)]} (song beats, sorted), .written (the entries
    as written), .free {(voice, round(start, 4))} of the voicer's notes, .harmony [(start, dur, chord)], .leads
    [(voice, start, end)] (the entries that lead: subject / answer / heads marked 'lead'), .added (the counterpoint's
    passing notes) - with lead(v, t), offset(v), emphasis(v) to perform it (the entering voice in front)."""

    def __init__(self, parts, written, free, harmony, leads, added, voices):
        self.parts, self.written, self.free, self.harmony = parts, written, free, harmony
        self.leads, self.added, self.voices = leads, added, voices

    def __getitem__(self, v):
        return self.parts[v]

    def lead(self, v, t: float) -> int:
        """1 while voice v plays a leading entry at beat t, -1 while another voice does, 0 when no one leads."""
        on = [w for w, a, b in self.leads if a - 1e-6 <= t < b - 1e-6]
        return 1 if v in on else (-1 if on else 0)

    def is_written(self, v, n) -> bool:
        """Is note n (start, ...) of voice v one of the written entries' notes (not the voicer's)?"""
        return any(abs(w[0] - n[0]) < 1e-4 for w in self.written.get(v, ()))

    def offset(self, v, lead: float = 8, other: float = -6, none: float = 0):
        """A velocity offset function note -> steps for voice v: its leading entries up, the others back."""
        return lambda n: {1: lead, -1: other, 0: none}[self.lead(v, n[0])]

    def emphasis(self, v, end: float, *, lead: float = 1.0, other: float = 0.8, none: float = 1.0,
                 ramp: float = 0.25, before: float = 0.5) -> list:
        """Expression points for voice v: `other` while another voice leads, `lead` / `none` otherwise, each change
        `ramp` beats long, from `before` the first lead to `end` (back to 1.0 there)."""
        start = min(a for _, a, _ in self.leads) if self.leads else 0.0
        bounds = sorted({a for _, a, b in self.leads} | {b for _, a, b in self.leads})
        level = {1: lead, -1: other, 0: none}
        pts = [(start - before, 1.0)]
        for b in bounds:
            x = level[self.lead(v, b + 0.01)]
            pts.append((max(pts[-1][0] + 0.01, b - ramp), pts[-1][1]))
            pts.append((b, x))
        pts.append((float(end) - before, pts[-1][1]))
        pts.append((float(end), 1.0))
        return pts

    def check(self, **kw) -> list:
        """voicing.check of the parts against the fugue's harmony."""
        return check(self.parts, self.harmony, voices=self.voices, **kw)


def fugue(entries, *, voices=None, at=0.0, subject=None, answer=None, counter=None, harmony=None,
          subject_harmony=None, key=None, lt=None, center=None, key_at=None, final=None, final_at=None,
          until=None, counterpoint: bool = True) -> Fugue:
    """A fugue / fugato: the entries as written, the free voices voiced around them chord by chord, the free voices'
    counterpoint (arpeggiate + passing_eighths).
      entries: [(voice, beat, material[, shift[, 'lead']])] - material 'subject' / 'answer' / 'counter' (the
        arguments), a line() spec ('C3:.5 Ab3:1 ...'), notation or notes; shift in semitones; subject / answer
        entries lead by default, others when marked 'lead' (or True) - the leads drive Fugue.lead / offset / emphasis.
      harmony: [(beat, dur, chord)] (or a Harmony) - or built from subject_harmony under each subject / answer
        entry, transposed by its shift. Beats are relative to `at` (a beat or Section); the result is in song beats.
      voices: the voice set (SATB default; a voice sounds from its first entry on); key / lt / center as voice()
        (lt may be a function of the beat: the local leading tone); key_at: the local key of the passing 8ths - a
        key, a function beat -> (pcs, tonic, lt) or [(beat, key), ...] spans (default: key).
      final / final_at: {voice: pitch} of the last chord from beat final_at (a bare fifth ...): the written entries
        end there. until: beats after which the counterpoint adds nothing. counterpoint=False: chords only."""
    rng = _voices(voices if voices is not None else SATB)
    order = tuple(rng)
    t0 = float(getattr(at, 'start', at))
    names = {'subject': subject, 'answer': answer, 'counter': counter}
    written = {v: [] for v in order}
    first: dict = {}
    leads, harm = [], []
    for e in entries:
        v, beat, mat = e[0], float(e[1]), e[2]
        if v not in rng:
            raise ComposeError(f"fugue: entry voice {v!r} is not in the voice set ({', '.join(order)})")
        shift = int(e[3]) if len(e) > 3 and e[3] is not None else 0
        ns = _material(mat, names, beat, shift)
        written[v] += ns
        first[v] = min(first.get(v, beat), beat)
        is_lead = (e[4] in (True, 'lead')) if len(e) > 4 else mat in ('subject', 'answer')
        if is_lead and ns:
            leads.append((v, t0 + beat, t0 + max(n[0] + n[1] for n in ns)))
        if harmony is None and subject_harmony is not None and mat in ('subject', 'answer'):
            for a, d, sym in subject_harmony:
                harm.append((beat + a, d, sym if not shift % 12 else _chord(sym).transpose(shift).symbol))
    if harmony is not None:
        if isinstance(harmony, Harmony):
            harm = [(a - harmony.origin, d, c) for a, d, c in harmony.timeline()]
        else:
            harm = list(harmony)
    if not harm:
        raise ComposeError("fugue: give harmony= (or subject_harmony= for the subject's entries)")
    fa = None if final_at is None else float(final_at)
    steps = []
    for st, du, sym in harm:
        active = [v for v in order if v in first and first[v] <= st + 1e-6]
        fx_, avoid = {}, set()
        if fa is not None and st >= fa - 1e-9:
            fx_ = {v: N(final[v]) for v in active if v in final}
        else:
            for v in active:
                for n in written[v]:
                    if n[0] - 1e-6 <= st < n[0] + n[1] - 1e-6:
                        fx_[v] = n[2]
            avoid = {n[2] for v in active for n in written[v] if st - 1e-6 <= n[0] < st + du - 1e-6}
        step = {'chord': sym, 'fixed': fx_, 'active': active, 'avoid': avoid}
        if callable(lt):
            step['lt'] = lt(st)
        steps.append(step)
    voiced = voice(steps, voices=rng, key=key, lt=None if callable(lt) else lt, center=center)
    parts = {v: [(n[0] + t0, n[1], n[2]) for n in written[v] if fa is None or n[0] < fa] for v in order}
    free: set = set()
    for (st, du, sym), stp, vc in zip(harm, steps, voiced):
        final_step = fa is not None and st >= fa - 1e-9
        for v in stp['active']:
            if v in stp['fixed'] and not final_step:
                continue
            p = vc[v]
            last = parts[v][-1] if parts[v] else None
            if (last and last[2] == p and abs(last[0] + last[1] - (st + t0)) < 1e-6 and not final_step
                    and (v, round(last[0], 4)) in free):
                parts[v][-1] = (last[0], last[1] + du, p)
            else:
                parts[v].append((st + t0, du, p))
                free.add((v, round(st + t0, 4)))
    for v in order:
        parts[v].sort()
    added = []
    if counterpoint:
        ka = key_at if key_at is not None else key
        ka = _key_spans(ka) if isinstance(ka, (list, tuple)) else ka
        added = arpeggiate(parts, free, harm, t0, voices=rng, until=until)
        if ka is not None:
            added += passing_eighths(parts, free, t0, ka, order=order, until=until)
    written_abs = {v: [(n[0] + t0, n[1], n[2]) for n in ns] for v, ns in written.items()}
    return Fugue(parts, written_abs, free, [(a + t0, d, c) for a, d, c in harm], leads, added, rng)


def imitation(cell, entries, *, key=None) -> dict:
    """Imitative entries of one cell: entries [(voice, beat, how)] - the cell moved by `how` semitones (an int), by
    scale steps of `key` ('+2d' / '-3d'), or onto new pitches (a tuple of pitches in the cell's rhythm) ->
    {voice: [(start, dur, pitch)]} (a voice's entries joined, sorted). cell: a line() spec, notation or notes from
    beat 0."""
    base = _material(cell, {}, 0.0, 0)
    out: dict = {}
    for v, beat, how in entries:
        b = float(getattr(beat, 'start', beat))
        if isinstance(how, (tuple, list)):
            if len(how) != len(base):
                raise ComposeError(f"imitation: {len(how)} pitches for a cell of {len(base)} notes")
            ns = [(b + n[0], n[1], N(p)) for n, p in zip(base, how)]
        elif isinstance(how, str) and how.endswith('d') and how[:-1].lstrip('+-').isdigit():
            if key is None:
                raise ComposeError("imitation: scale-step shifts ('+2d') need key=")
            k = key if isinstance(key, Key) else Key(key)
            ns = [(b + n[0], n[1], _note(k.transpose(n[2], int(how[:-1])))) for n in base]
        else:
            ns = [(b + n[0], n[1], n[2] + int(how)) for n in base]
        out.setdefault(v, []).extend(ns)
    for v in out:
        out[v].sort()
    return out
