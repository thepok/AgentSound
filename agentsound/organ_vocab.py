"""The organist's VOCABULARY: the textures of organ music as functions that turn a melody + a chord chart into
VOICES (one contrapuntal line each, or a chord stream), ready for the organist (agentsound.organist.perform) to
play on a registration.

    from agentsound import organ_vocab as ov
    slots = ov.harmonize(melody, chart, 'F major', meter=4)                 # a chord per beat under a chorale tune
    v = ov.satb(slots, melody, 'F major')                                   # {'S','A','T','B'}: voice-led SATB
    v = ov.flow(v, slots, 'F major', per_bar=1.2, seed=3)                   # passing 8ths, a 4-3 at the cadences
    lines = ov.counterline(cantus, slots, 'F major', lo='C4', hi='G5', motif='suspirans', seed=1)
    figs = ov.toccata(slots, 'F major', figure='widor', register=('C5', 'C6'))
    exp = ov.fugue(subject, 'D minor', voices=4, seed=2)                    # an exposition: subject / answer / CS

Every function is deterministic (seeded) and returns plain (start, dur, pitch) notes in beats (the time of the
material it was given). The rules are distributions / budgets / costs, not dice per note:
  * harmonize: a dynamic program over the diatonic chords per harmony slot (the melody note a chord tone, the
    root motion's strength - down a 5th best, retrogressions dear -, the composer's chart chord preferred, phrase
    ends as cadences: authentic, half, plagal, deceptive; a cadential 6/4 before the final V);
  * satb: a beam search over voicings (S given, A / T / B in their ranges): smallest motion, no parallel 5ths /
    octaves, no crossing / overlap, spacing (S-A, A-T <= an octave), complete chords, the leading tone and a 7th
    resolved, the bass by step or a 4th / 5th;
  * flow: passing 8ths in the lower voices (a budget per bar), a 4-3 suspension into the cadence's dominant;
  * counterline: a flowing line (8ths / 16ths) against the other voices: chord tones on the beats (a beam over the
    consonances, contrary motion preferred), the beat filled with the piece's ONE motif (a Bach chorale prelude:
    one figure carries the whole piece) - steps, turns, arpeggios toward the next beat's note;
  * toccata: manual figuration per harmony slot from TOCCATA_FIGURES (Widor's oscillating 16ths, broken chords,
    a wave), the chord's tones in close position and voice-led from slot to slot;
  * fugue: subject, answer at the 5th (a tonal answer where the subject opens on the 5th), countersubject
    (a counterline against the answer), free voices, entries in the voice order drawn.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .patterns import seed_int
from .theory import ComposeError, Key, chord as _chord, note

__all__ = ['HChord', 'Slot', 'MOTIFS', 'TOCCATA_FIGURES', 'RANGES', 'diatonic', 'harmonize', 'satb', 'flow',
           'counterline', 'bass_line', 'toccata', 'fugue', 'planing', 'parallels', 'slots_from_chart',
           'chord_at', 'ornament_targets', 'sounding']

_EPS = 1e-6

RANGES = {'S': (60, 81), 'A': (55, 74), 'T': (48, 67), 'B': (38, 62)}
"""SATB ranges (MIDI): soprano C4-A5, alto G3-D5, tenor C3-G4, bass D2-D4 (the pedal at 8' pitch; a 16' stop sounds
an octave lower)."""


# ------------------------------------------------------------------------------------------------ chords

@dataclass(frozen=True)
class HChord:
    """A harmony: degree name ('V7', 'ii', 'cad64' ...), root pc, its pitch classes, the 3rd / 5th / 7th pcs, the bass
    pc when it is fixed (a cadential 6/4: the dominant), its function ('T', 'PD', 'D'), a symbol for the chart."""
    name: str
    root: int
    pcs: frozenset
    third: int
    fifth: int | None
    seventh: int | None
    bass: int | None
    func: str
    symbol: str

    @property
    def leading(self) -> int | None:
        """The 3rd of a dominant-function chord (V / V7 / vii): the leading tone that must rise."""
        return self.third if self.func == 'D' and self.name.startswith('V') else None


_SHARP_KEYS = {'major': {'G', 'D', 'A', 'E', 'B', 'F#', 'C#'}, 'minor': {'E', 'B', 'F#', 'C#', 'G#', 'D#'}}
_FLATS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
_SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def _key(key) -> Key:
    return key if isinstance(key, Key) else Key(key)


def _minor(k: Key) -> bool:
    return 3 in k.intervals and 4 not in k.intervals


def _name(pc_: int, k: Key) -> str:
    mode = 'minor' if _minor(k) else 'major'
    return (_SHARPS if k.tonic_name in _SHARP_KEYS[mode] else _FLATS)[pc_ % 12]


# degree -> (semitones above the tonic, quality, function); quality: '' major, 'm' minor, 'dim', '7', 'm7', 'dim7',
# 'ø7', 'maj7'. The minor key's V / vii are the harmonic minor's (the raised 7th).
_DIATONIC = {
    'major': {'I': (0, '', 'T'), 'ii': (2, 'm', 'PD'), 'iii': (4, 'm', 'T'), 'IV': (5, '', 'PD'), 'V': (7, '', 'D'),
              'vi': (9, 'm', 'T'), 'viio': (11, 'dim', 'D'), 'V7': (7, '7', 'D'), 'ii7': (2, 'm7', 'PD'),
              'IVmaj7': (5, 'maj7', 'PD'), 'V/V': (2, '7', 'PD'), 'V/vi': (4, '7', 'D2'), 'V/IV': (0, '7', 'T2'),
              'viio7': (11, 'dim7', 'D'), 'iv': (5, 'm', 'PD')},
    'minor': {'i': (0, 'm', 'T'), 'iio': (2, 'dim', 'PD'), 'III': (3, '', 'T'), 'iv': (5, 'm', 'PD'), 'V': (7, '', 'D'),
              'VI': (8, '', 'T'), 'VII': (10, '', 'D2'), 'viio': (11, 'dim', 'D'), 'V7': (7, '7', 'D'),
              'iiø7': (2, 'm7b5', 'PD'), 'iv7': (5, 'm7', 'PD'), 'viio7': (11, 'dim7', 'D'), 'V/V': (2, '7', 'PD'),
              'N6': (1, '', 'PD'), 'V/iv': (0, '7', 'T2'), 'I': (0, '', 'T')},
}
_QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), 'dim': (0, 3, 6), '7': (0, 4, 7, 10), 'm7': (0, 3, 7, 10),
         'dim7': (0, 3, 6, 9), 'm7b5': (0, 3, 6, 10), 'maj7': (0, 4, 7, 11)}
_SYM = {'': '', 'm': 'm', 'dim': 'dim', '7': '7', 'm7': 'm7', 'dim7': 'dim7', 'm7b5': 'm7b5', 'maj7': 'maj7'}


def _make(name: str, root: int, qual: str, func: str, k: Key, bass: int | None = None) -> HChord:
    ivs = _QUAL[qual]
    pcs = frozenset((root + i) % 12 for i in ivs)
    third = (root + ivs[1]) % 12
    fifth = (root + ivs[2]) % 12
    seventh = (root + ivs[3]) % 12 if len(ivs) > 3 else None
    sym = _name(root, k) + _SYM[qual] + (f"/{_name(bass, k)}" if bass is not None and bass != root else '')
    return HChord(name, root, pcs, third, fifth, seventh, bass, func, sym)


def diatonic(key) -> dict:
    """The key's harmony vocabulary {degree name: HChord} (+ 'cad64': the tonic over the dominant bass)."""
    k = _key(key)
    mode = 'minor' if _minor(k) else 'major'
    out = {}
    for nm, (off, q, f) in _DIATONIC[mode].items():
        out[nm] = _make(nm, (k.tonic + off) % 12, q, f, k)
    t = 'i' if mode == 'minor' else 'I'
    out['cad64'] = _make('cad64', out[t].root, 'm' if mode == 'minor' else '', 'D', k, bass=(k.tonic + 7) % 12)
    return out


def _from_symbol(sym: str, k: Key) -> HChord | None:
    """A chart symbol as an HChord (its pcs; triad / 7th only - extensions dropped for the four voices)."""
    try:
        c = _chord(sym)
    except ComposeError:
        return None
    ivs = set(c.intervals)
    q = '7' if {4, 10} <= ivs else 'maj7' if {4, 11} <= ivs else 'm7b5' if {3, 6, 10} <= ivs else \
        'dim7' if {3, 6, 9} <= ivs else 'm7' if {3, 10} <= ivs else 'dim' if {3, 6} <= ivs else \
        'm' if 3 in ivs else ''
    rel = (c.root - k.tonic) % 12
    fn = 'D' if rel in (7, 11) else 'PD' if rel in (2, 5, 1) else 'T'
    return _make(sym, c.root, q, fn, k, bass=c.bass if c.bass is not None and c.bass != c.root else None)


@dataclass
class Slot:
    """One harmony slot: start, dur (beats), the chord, the soprano pitch sounding at its start (None: rest),
    whether a phrase ends here ('end': the cadence's goal) and the chart chord it came from."""
    start: float
    dur: float
    chord: HChord
    sop: int | None = None
    end: bool = False
    chart: HChord | None = None


def chord_at(chart, t: float):
    """The chart entry [(start, beats, symbol)] sounding at beat t (None outside it)."""
    for a, b, s in chart:
        if a - _EPS <= t < a + b - _EPS:
            return s
    return None


def sounding(notes, t: float):
    """The pitch of a line (start, dur, pitch) sounding at beat t (the latest note started at or before t that is
    still held), else None."""
    best = None
    for st, du, p in notes:
        if st - _EPS <= t < st + du - _EPS:
            best = p if best is None else best
    return best


def slots_from_chart(chart, key, *, rate: float = 1.0, ends=()) -> list[Slot]:
    """Slots straight from a chart (a chord per `rate` beats, the chart's chords as they are - no melody to fit):
    the meditation's held harmony, a toccata's figuration."""
    k = _key(key)
    out = []
    for a, b, sym in chart:
        hc = _from_symbol(sym, k)
        if hc is None:
            continue
        t = a
        while t < a + b - _EPS:
            d = min(rate, a + b - t)
            out.append(Slot(t, d, hc, None, False, hc))
            t += d
    ends = sorted(ends)
    for s in out:
        if any(abs(s.start + s.dur - e) < _EPS for e in ends):
            s.end = True
    return out


# root motion (semitones up, mod 12) -> cost: down a 5th (= up a 4th) the strongest, then down a 3rd, up a step
_MOTION = {5: 0.0, 9: 0.35, 2: 0.45, 7: 0.75, 3: 0.95, 10: 1.25, 8: 0.6, 4: 1.0, 1: 1.6, 11: 1.4, 6: 1.8, 0: 0.55}


def _trans(a: HChord, b: HChord) -> float:
    c = _MOTION[(b.root - a.root) % 12]
    if a.name == b.name:
        return 0.55
    if a.func == 'D' and b.func == 'PD':
        c += 1.6                                    # a retrogression (V -> IV / ii)
    if a.name == 'cad64' and not b.name.startswith('V'):
        c += 50.0                                   # a cadential 6/4 resolves to V
    if b.name == 'cad64' and a.func == 'D':
        c += 3.0
    if a.func in ('D2', 'T2') and (b.root - a.root) % 12 != 5:
        c += 1.4                                    # a secondary dominant resolves down a 5th
    if a.seventh is not None and a.func == 'D' and (b.root - a.root) % 12 not in (5, 9):
        c += 1.0                                    # V7 to I / vi
    return c


def harmonize(melody, chart, key, *, meter: int = 4, rate: float = 1.0, ends=(), colour: float = 0.3,
              seed=0, avoid=None, vary: float = 0.0) -> list[Slot]:
    """A chord per harmony slot (every `rate` beats where the melody sounds) under a chorale tune: a dynamic program
    over the key's chords (diatonic(): triads, V7, ii7, secondary dominants, the minor's Neapolitan) - the soprano
    note a chord tone, the root motion's strength (_MOTION, retrogressions dear), the chart chord (the composer's
    harmony) preferred, phrase `ends` (beats where a phrase's last note starts) as cadences: the chart's goal chord
    with a dominant (or IV: plagal) before it, a cadential 6/4 now and then. colour: the share of 7ths / secondary
    dominants allowed (0 = triads only). melody: [(start, dur, pitch)], chart: [(start, beats, symbol)].
    A verse's re-harmonization: avoid {slot start: chord name} (an earlier verse's choice, from Slot.chord.name) costs
    `vary` more where the same chord would sound again (the cadences' goals stay) - a variation, not a copy."""
    k = _key(key)
    voc = diatonic(k)
    rng = random.Random(seed_int(seed))
    minor = _minor(k)
    tonic_name = 'i' if minor else 'I'
    rich = {n for n, h in voc.items() if h.seventh is not None or h.func in ('D2', 'T2') or n == 'N6'}
    ends = sorted(set(round(e, 6) for e in ends))
    mel = sorted(melody)
    if not mel:
        return []
    # the slots: every `rate` beats from the first melody note to the last one's end; the soprano at each
    t0 = math.floor(mel[0][0] / rate + _EPS) * rate
    t1 = max(s + d for s, d, _ in mel)
    slots = []
    t = t0
    while t < t1 - _EPS:
        p = sounding(mel, t + 1e-4)
        if p is None:                               # a rest in the tune: the voices breathe with it
            t += rate
            continue
        cs = chord_at(chart, t + 1e-4)
        slots.append(Slot(t, rate, voc[tonic_name], p, False, _from_symbol(cs, k) if cs else None))
        t += rate
    # a phrase end: the slot where its last note starts (the cadence goal); its length runs to the note's end
    for e in ends:
        js = [i for i, s in enumerate(slots) if s.start - _EPS <= e < s.start + s.dur - _EPS]
        if js:
            slots[js[0]].end = True
    # merge the slots under a held cadence note into the goal (the voices hold the final chord with it)
    merged = []
    for s in slots:
        if merged and merged[-1].end and s.sop == merged[-1].sop and \
                abs(merged[-1].start + merged[-1].dur - s.start) < _EPS and \
                sounding(mel, s.start - 0.01) == s.sop and not any(abs(n[0] - s.start) < _EPS for n in mel):
            merged[-1].dur += s.dur
            continue
        merged.append(s)
    slots = merged
    n = len(slots)
    names = list(voc)

    def fits(h: HChord, p: int | None) -> bool:
        return p is None or p % 12 in h.pcs

    def own_cost(i: int, nm: str) -> float:
        s, h = slots[i], voc[nm]
        if not fits(h, s.sop):
            return math.inf
        c = 0.0
        if nm in rich:
            c += 1.2 - colour                       # colour chords: spice, not habit
        if nm in ('iii',):
            c += 0.6
        if nm in ('viio', 'viio7'):
            c += 0.7
        if nm == 'I' and minor:
            c += 2.5                                # (a Picardy third: only as the final chord)
        if nm == 'cad64':
            c += 0.4
        ch = s.chart
        if ch is not None:
            if h.root == ch.root and (h.third == ch.third or ch.third is None):
                c -= 0.9
            elif h.root == ch.root:
                c -= 0.4
            elif h.pcs & ch.pcs and len(h.pcs & ch.pcs) >= 2:
                c -= 0.15
        if avoid and vary and not s.end and avoid.get(round(s.start, 3)) == nm:
            c += vary
        on_bar = abs((s.start / meter) - round(s.start / meter)) < _EPS
        if on_bar and h.func == 'D' and nm != 'cad64' and not s.end:
            c += 0.15
        if s.sop is not None and s.sop % 12 == h.fifth and s.end:
            c += 0.3                                # a phrase ending on the 5th in the soprano: weaker
        if s.end:
            goal = ch.root if ch is not None else k.tonic
            if h.root != goal:
                c += 2.0
            if h.func == 'D' and h.root != goal:
                c += 1.0
        return c

    INF = math.inf
    cost = [{nm: own_cost(0, nm) for nm in names}]
    back = [{}]
    for i in range(1, n):
        row, bk = {}, {}
        prev_end = slots[i - 1].end
        for nm in names:
            oc = own_cost(i, nm)
            if oc == INF:
                row[nm] = INF
                continue
            best, arg = INF, None
            for pn, pc_ in cost[-1].items():
                if pc_ == INF:
                    continue
                tc = _trans(voc[pn], voc[nm])
                if slots[i].end and i >= 1:
                    # the cadence: the goal chord after a dominant (authentic), IV (plagal) or a predominant (half)
                    g = voc[nm]
                    if g.func == 'T' and g.root == k.tonic:
                        tc += 0.0 if voc[pn].func == 'D' and pn != 'viio' else 0.8 if pn in ('IV', 'iv') else 2.5
                    elif g.func == 'D':
                        tc += 0.0 if voc[pn].func in ('PD',) or pn == 'cad64' else 1.0
                    elif nm in ('vi', 'VI'):
                        tc += 0.0 if pn in ('V', 'V7') else 2.0            # deceptive
                if prev_end:
                    tc *= 0.4                       # a new phrase may start anywhere
                v = pc_ + tc
                if v < best:
                    best, arg = v, pn
            row[nm] = best + oc
            bk[nm] = arg
        cost.append(row)
        back.append(bk)
    # the end: the last slot's chord (the tonic when the chart ends there)
    last = min(cost[-1], key=lambda x: (cost[-1][x], x))
    if cost[-1][last] == INF:
        raise ComposeError("harmonize: no chord fits the melody (a note outside the key's chords)")
    chosen = [last]
    for i in range(n - 1, 0, -1):
        chosen.append(back[i][chosen[-1]])
    chosen.reverse()
    for s, nm in zip(slots, chosen):
        s.chord = voc[nm]
    # a cadential 6/4 is only kept before a dominant
    for i, s in enumerate(slots):
        if s.chord.name == 'cad64' and (i + 1 >= n or not slots[i + 1].chord.name.startswith('V')):
            s.chord = voc[tonic_name]
    _ = rng
    return slots


# ------------------------------------------------------------------------------------------------ SATB

def _perfect(a: int, b: int) -> int | None:
    """7 (a 5th) / 0 (an octave / unison) when the interval a-b is perfect, else None."""
    iv = abs(a - b) % 12
    return iv if iv in (0, 7) else None


def parallels(prev, cur) -> int:
    """Parallel 5ths / octaves between two voicings (lists of pitches, voice by voice): pairs that hold the same
    perfect interval while both voices move (in the same direction)."""
    n = 0
    for i in range(len(cur)):
        for j in range(i + 1, len(cur)):
            a0, b0, a1, b1 = prev[i], prev[j], cur[i], cur[j]
            if None in (a0, b0, a1, b1):
                continue
            p0, p1 = _perfect(a0, b0), _perfect(a1, b1)
            if p0 is not None and p0 == p1 and a0 != a1 and b0 != b1 and (a1 - a0) * (b1 - b0) > 0:
                n += 1
    return n


def _cands(h: HChord, sop: int | None, k: Key, ranges, root: bool = False):
    """Every voicing (B, T, A, S) of a chord in the ranges: S given (or free), chord complete (root + 3rd; the 5th
    may go; a 7th kept), doubling preferred on the root, never the leading tone / the 7th doubled; spacing S-A and
    A-T at most an octave (+2), T-B at most a 12th (+7)."""
    lo = {v: r[0] for v, r in ranges.items()}
    hi = {v: r[1] for v, r in ranges.items()}
    pcs = h.pcs
    bass_pcs = [h.bass] if h.bass is not None else [h.root, h.third] + ([h.fifth] if h.seventh is not None else [])
    if h.name in ('viio', 'viio7'):
        bass_pcs = [h.third]                        # vii as vii6 (its root is the leading tone)
    if root and h.bass is None:
        bass_pcs = [h.root]                         # a cadence: root position
    sops = [sop] if sop is not None else [p for p in range(lo['S'], hi['S'] + 1) if p % 12 in pcs]
    out = []
    lead = h.leading
    for S in sops:
        for B in range(lo['B'], hi['B'] + 1):
            if B % 12 not in bass_pcs:
                continue
            for T in range(max(lo['T'], B), hi['T'] + 1):
                if T % 12 not in pcs or T - B > 19:
                    continue
                for A in range(max(lo['A'], T), min(hi['A'], S) + 1):
                    if A % 12 not in pcs or S - A > 12 or A - T > 12:
                        continue
                    got = [B % 12, T % 12, A % 12, S % 12]
                    if h.root not in got or h.third not in got:
                        continue
                    if h.seventh is not None and h.seventh not in got:
                        continue
                    pen = 0.0
                    if lead is not None and got.count(lead) > 1:
                        continue
                    if h.seventh is not None and got.count(h.seventh) > 1:
                        continue
                    dbl = [x for x in set(got) if got.count(x) > 1]
                    for d in dbl:
                        pen += 0.0 if d == h.root else 0.6 if d == h.fifth else 1.4
                    if h.fifth is not None and h.fifth not in got:
                        pen += 0.5
                    if B % 12 == h.third and h.func == 'D' and h.name.startswith('V') and h.seventh is None:
                        pen += 0.3
                    if B % 12 != h.root and h.bass is None:
                        pen += 0.35                 # inversions: for the line, not by default
                    out.append(((B, T, A, S), pen))
    return out


def _vl_cost(p, c, h0: HChord, h1: HChord, k: Key) -> float:
    """The cost of moving voicing p (B, T, A, S) to c."""
    cost = 0.0
    w = (0.35, 1.0, 1.0, 0.2)
    for i in range(4):
        d = abs(c[i] - p[i])
        cost += w[i] * d
        if i in (1, 2) and d > 5:
            cost += 2.5 + 0.5 * (d - 5)             # inner voices: no leaps beyond a 4th
        if i == 0 and d > 7 and d != 12:
            cost += 1.5
    pa = parallels(p, c)
    cost += 25.0 * pa
    # hidden 5ths / octaves in the outer voices (similar motion into a perfect interval, the soprano leaping)
    if _perfect(c[0], c[3]) is not None and (c[0] - p[0]) * (c[3] - p[3]) > 0 and abs(c[3] - p[3]) > 2:
        cost += 3.0
    # overlap: a voice moving past the neighbour's previous note
    for i in range(3):
        if c[i] > p[i + 1] or c[i + 1] < p[i]:
            cost += 3.0
    # the leading tone rises to the tonic, the 7th falls (V -> I)
    lead = h0.leading
    if lead is not None:
        for i in (1, 2, 3):
            if p[i] % 12 == lead and h1.func == 'T' and c[i] - p[i] != 1 and i != 3:
                cost += 4.0
    if h0.seventh is not None:
        for i in range(4):
            if p[i] % 12 == h0.seventh and h1.name != h0.name and not (-2 <= c[i] - p[i] <= 0):
                cost += 3.5
    # a static bass over a change of chord
    if c[0] == p[0] and h0.name != h1.name:
        cost += 0.3
    return cost


def satb(slots, melody=None, key='C major', *, ranges=None, beam: int = 60, start=None) -> dict:
    """Four voices for the slots (harmonize() / slots_from_chart()): a beam search over _cands() with _vl_cost()
    (the soprano = the slot's melody note when the slots carry one, else free - the voicing's top line then moves
    least). Returns {'S', 'A', 'T', 'B': [(start, dur, pitch)]} - each voice holds its pitch across slots where it
    does not move (tied: one long note), the soprano is the given melody itself (with its own rhythm) when there is
    one. ranges: RANGES overrides per voice."""
    k = _key(key)
    R = dict(RANGES, **(ranges or {}))
    if not slots:
        return {v: [] for v in 'SATB'}
    beams = [(0.0, None, [])]
    # the tune's note sounding just before each slot (a passing note inside the slot before): no parallels from it
    pre = [sounding(melody, s.start - 0.02) if melody is not None and s.start > 0.02 else None for s in slots]
    for i, s in enumerate(slots):
        strict = s.end or (i + 1 < len(slots) and slots[i + 1].end and s.chord.func == 'D')
        cands = _cands(s.chord, s.sop, k, R, root=strict)
        if not cands:
            raise ComposeError(f"satb: no voicing of {s.chord.symbol} at beat {s.start:g} (soprano "
                               f"{s.sop}) in the ranges")
        nb = []
        for cost, prev, path in beams:
            hp = slots[i - 1].chord if i else None
            for v, pen in cands:
                if prev is None:
                    c0 = pen + (abs(v[2] - 66) + abs(v[1] - 57)) * 0.15 + (0 if start is None else
                                                                          sum(abs(a - b) for a, b in zip(v, start)))
                else:
                    c0 = pen + _vl_cost(prev, v, hp, s.chord, k)
                    if pre[i] is not None and pre[i] != prev[3]:
                        c0 += 25.0 * parallels(prev[:3] + (pre[i],), v)
                nb.append((cost + c0, v, path + [v]))
        nb.sort(key=lambda x: x[0])
        seen, beams = set(), []
        for x in nb:
            if x[1] in seen:
                continue
            seen.add(x[1])
            beams.append(x)
            if len(beams) >= beam:
                break
    best = beams[0][2]
    out = {'B': [], 'T': [], 'A': [], 'S': []}
    for vi, vn in enumerate('BTAS'):
        line = out[vn]
        for s, v in zip(slots, best):
            p = v[vi]
            if line and line[-1][2] == p and abs(line[-1][0] + line[-1][1] - s.start) < _EPS and not s.end and \
                    not _phrase_start(slots, s):
                st, du, _ = line[-1]
                line[-1] = (st, du + s.dur, p)
            else:
                line.append((s.start, s.dur, p))
    if melody is not None and any(s.sop is not None for s in slots):
        out['S'] = [tuple(n) for n in sorted(melody)]
    return out


def _phrase_start(slots, s) -> bool:
    i = slots.index(s)
    return i > 0 and (slots[i - 1].end or abs(slots[i - 1].start + slots[i - 1].dur - s.start) > _EPS)


# ------------------------------------------------------------------------------------------------ flow

def _scale(k: Key, h: HChord | None = None) -> set:
    pcs = set(k.pcs)
    if _minor(k):
        pcs |= {(k.tonic + 11) % 12}                # the raised leading tone
        if h is not None and h.func == 'D':
            pcs -= {(k.tonic + 10) % 12}
    if h is not None:
        pcs |= set(h.pcs)
    return pcs


def _step(p: int, d: int, pcs) -> int:
    """The scale step d steps from p (d = +-1, +-2 ...) in the pitch-class set pcs."""
    q, n = p, 0
    while n < abs(d):
        q += 1 if d > 0 else -1
        if q % 12 in pcs:
            n += 1
    return q


def _at(voice, t):
    return sounding(voice, t)


def flow(voices: dict, slots, key, *, per_bar: float = 1.0, meter: int = 4, suspensions: float = 0.4,
         which=('A', 'T', 'B'), seed=0) -> dict:
    """Passing 8ths in the lower voices of a SATB setting (Bach's flowing chorales): where a voice moves a 3rd
    between two slots, the second half of its note becomes the scale step between (a passing tone) - at most
    `per_bar` per bar on average (a budget over the piece, the voices taking turns), never into a unison with or a
    parallel 5th / octave against another voice. suspensions: the share of the cadences whose dominant gets a 4-3
    (the voice that will hold the leading tone keeps the tonic over the beat, then falls to it)."""
    k = _key(key)
    rng = random.Random(seed_int(seed))
    V = {v: [list(n) for n in voices[v]] for v in voices}
    total_bars = max(1.0, (slots[-1].start + slots[-1].dur - slots[0].start) / meter) if slots else 1.0
    budget = per_bar * total_bars
    cands = []
    for v in which:
        line = V.get(v) or []
        for i in range(len(line) - 1):
            st, du, p = line[i]
            nst, _, np_ = line[i + 1]
            if abs(st + du - nst) > _EPS or du < 0.99:
                continue
            if 3 <= abs(np_ - p) <= 4:
                cands.append((v, i))
    rng.shuffle(cands)
    used_bars: dict = {}
    added = 0
    for v, i in cands:
        if added >= budget:
            break
        line = V[v]
        st, du, p = line[i]
        nst, _, np_ = line[i + 1]
        bar = int(st // meter)
        if used_bars.get(bar, 0) >= 2:
            continue
        h = _slot_chord(slots, st + du - 0.01)
        mid_t = st + du - 0.5
        pas = _step(p, 1 if np_ > p else -1, _scale(k, h))
        if not (min(p, np_) < pas < max(p, np_)):
            continue
        others = [(u, _at(V[u], mid_t + 1e-4)) for u in V if u != v]
        if any(q == pas for _, q in others if q is not None):
            continue
        bad = False
        for u, q in others:
            q2 = _at(V[u], nst + 1e-4)
            if q is None or q2 is None:
                continue
            if _perfect(pas, q) is not None and _perfect(pas, q) == _perfect(np_, q2) and pas != np_ and q != q2:
                bad = True
        if bad:
            continue
        line[i] = [st, du - 0.5, p]
        line.insert(i + 1, [mid_t, 0.5, pas])
        # (the indices of later candidates in this voice moved by one)
        cands = [(u, j + 1 if u == v and j > i else j) for u, j in cands]
        used_bars[bar] = used_bars.get(bar, 0) + 1
        added += 1
    # 4-3 suspensions into the cadences' dominants
    for j, s in enumerate(slots):
        if not s.end or j < 1 or rng.random() >= suspensions:
            continue
        d = slots[j - 1]
        if not d.chord.name.startswith('V') or d.dur < 0.99:
            continue
        for v in ('A', 'T'):
            line = V.get(v) or []
            idx = next((i for i, n in enumerate(line) if abs(n[0] - d.start) < _EPS), None)
            if idx is None or idx == 0:
                continue
            p = line[idx][2]
            if p % 12 != d.chord.third:
                continue
            prev = line[idx - 1]
            if prev[2] - p in (1, 2) and abs(prev[0] + prev[1] - d.start) < _EPS:
                # hold the note above over the beat (tied), then resolve to the leading tone
                half = d.dur / 2
                prev[1] += half
                line[idx] = [d.start + half, line[idx][1] - half, p]
                break
    return {v: [tuple(n) for n in V[v]] for v in V}


def _slot_chord(slots, t):
    for s in slots:
        if s.start - _EPS <= t < s.start + s.dur - _EPS:
            return s.chord
    return None


# ------------------------------------------------------------------------------------------------ counterline

MOTIFS = {
    # one beat of a flowing line (fractions of the beat, a negative = a rest): which tones fill it is chosen per beat
    # (toward the next beat's note: scale steps, a turn, an arpeggio) - the RHYTHM is the piece's motif
    'eighths': (0.5, 0.5),                       # plain flowing 8ths
    'suspirans': (-0.25, 0.25, 0.25, 0.25),      # the sigh figure: a 16th rest, three 16ths (Orgelbuchlein)
    'sixteenths': (0.25, 0.25, 0.25, 0.25),      # running 16ths (a toccata's inner voice, a lively prelude)
    'dactyl': (0.5, 0.25, 0.25),                 # long-short-short (a walking, a pastoral)
    'anapaest': (0.25, 0.25, 0.5),               # short-short-long (a dance)
    'dotted': (0.75, 0.25),                      # a dotted pair (French overture, the festive postlude)
    'quarter': (1.0,),                           # a calm line (the pedal / the tenor under a busy line)
}
"""The flowing lines' one-beat rhythms (counterline motif=): a piece keeps ONE (a Bach prelude's figure), varied by
the beats where the line rests or holds (`rest` / `hold` budgets)."""


def _consonant(a: int, b: int) -> bool:
    return abs(a - b) % 12 in (0, 3, 4, 7, 8, 9)


def counterline(context, slots, key, *, lo='C4', hi='G5', motif: str = 'eighths', start=None, rest: float = 0.08,
                hold: float = 0.12, above=None, below=None, mix: float = 0.25, contrary: float = 0.6,
                meter: int = 4, seed=0) -> list:
    """A flowing contrapuntal line against `context` (the other voices: a list of note lists) over the slots'
    harmony, in lo..hi, keeping the piece's ONE `motif` rhythm (MOTIFS; `mix` of the beats take a neighbouring
    rhythm, `hold` of them a long note, `rest` a rest - never two running), a beam over the beat notes: chord tones
    of the slot, consonant with every context voice sounding on the beat, no parallel 5ths / octaves with them,
    contrary motion to the top context voice preferred (`contrary`), steps and 3rds over leaps; the beat filled from
    its note toward the next one (scale steps when the distance fits, a turn / neighbour, else chord tones).
    above / below: a voice (note list) the line stays under / over. Returns [(start, dur, pitch)]."""
    k = _key(key)
    rng = random.Random(seed_int(seed))
    lo, hi = note(lo), note(hi)
    if not slots:
        return []
    t0 = slots[0].start
    t1 = slots[-1].start + slots[-1].dur
    beats = []
    t = t0
    while t < t1 - _EPS:
        beats.append(t)
        t += 1.0
    ctx = [sorted(v) for v in context if v]

    def ch_at(tt):
        return _slot_chord(slots, tt + 1e-4)

    def cands(tt):
        h = ch_at(tt)
        if h is None:
            return []
        out = []
        for p in range(lo, hi + 1):
            if p % 12 not in h.pcs:
                continue
            if above is not None:
                a = _at(above, tt + 1e-4)
                if a is not None and p >= a:
                    continue
            if below is not None:
                b = _at(below, tt + 1e-4)
                if b is not None and p <= b:
                    continue
            ok = True
            for v in ctx:
                q = _at(v, tt + 1e-4)
                if q is not None and (q == p or not _consonant(p, q) and abs(p - q) % 12 not in (5,)):
                    ok = False
                    break
            if ok:
                out.append(p)
        return out
    beam = [(0.0, [])]
    for bi, tt in enumerate(beats):
        cs = cands(tt)
        if not cs:
            cs = [beam[0][1][-1]] if beam[0][1] else [(lo + hi) // 2]
        nb = []
        tops = [_at(v, tt + 1e-4) for v in ctx]
        tops_prev = [_at(v, tt - 1 + 1e-4) for v in ctx] if bi else tops
        for cost, path in beam:
            for p in cs:
                c = cost
                if path:
                    q = path[-1]
                    d = abs(p - q)
                    c += {0: 1.2, 1: 0.2, 2: 0.0, 3: 0.3, 4: 0.4, 5: 0.9, 7: 1.4}.get(d, 1.0 + 0.3 * d)
                    for a0, a1 in zip(tops_prev, tops):
                        if None in (a0, a1):
                            continue
                        if _perfect(q, a0) is not None and _perfect(q, a0) == _perfect(p, a1) and p != q and \
                                a0 != a1 and (p - q) * (a1 - a0) > 0:
                            c += 30.0
                    top0, top1 = tops_prev[0], tops[0]
                    if top0 is not None and top1 is not None and top1 != top0:
                        c += 0.0 if (p - q) * (top1 - top0) < 0 else contrary
                elif start is not None:
                    c += 0.4 * abs(p - note(start))
                else:
                    c += 0.1 * abs(p - (lo + hi) / 2)
                c += 0.04 * abs(p - (lo + hi) / 2)
                nb.append((c + rng.random() * 0.05, path + [p]))
        nb.sort(key=lambda x: x[0])
        beam = nb[:40]
    targets = beam[0][1]
    # fill each beat with the motif rhythm toward the next beat's note
    base = MOTIFS[motif]
    alt = [m for m in ('eighths', 'dactyl', 'anapaest', 'sixteenths') if m != motif and
           (motif != 'quarter' or m == 'eighths')]
    out = []
    last_kind = None
    for bi, tt in enumerate(beats):
        p = targets[bi]
        nxt = targets[bi + 1] if bi + 1 < len(targets) else None
        h = ch_at(tt)
        pcs = _scale(k, h)
        r = rng.random()
        if last_kind in ('rest', 'hold') or bi == 0:
            kind = 'motif'
        elif r < rest:
            kind = 'rest'
        elif r < rest + hold:
            kind = 'hold'
        elif r < rest + hold + mix:
            kind = 'mix'
        else:
            kind = 'motif'
        last_kind = kind
        if kind == 'rest' and bi + 1 < len(beats):
            continue
        if kind == 'hold':
            out.append((tt, 1.0, p))
            continue
        cell = base if kind != 'mix' else MOTIFS[rng.choice(alt)]
        notes_ = [x for x in cell if x > 0]
        n = len(notes_)
        path = _fill(p, nxt, n, pcs, h, rng)
        x = tt
        j = 0
        for d in cell:
            if d < 0:
                x += -d
                continue
            out.append((x, d, path[j]))
            x += d
            j += 1
    # the beat targets are checked against parallels above; the motif's last note before a beat is not: where it
    # moves in parallel 5ths / octaves into the next beat with a context voice, the note before it holds instead
    out = _no_parallel_fills(sorted(out), beats, ctx)
    # tie repeated pitches (a held note, not a re-strike) only where the motif asks for a long note
    return _clamp_range(out, lo, hi)


def _no_parallel_fills(out, beats, ctx) -> list:
    """Drop a fill note (off the beat) that makes parallel perfect intervals with a context voice: arriving off the
    beat it is dropped (the note before holds through); arriving on a beat, the fill before it is dropped."""
    on_beat = {round(t, 4) for t in beats}
    for _ in range(4):
        fixed = False
        i = 1
        while i < len(out):
            pv, cur = out[i - 1], out[i]
            if pv[0] + pv[1] < cur[0] - 0.3:
                i += 1
                continue
            bad = False
            for v in ctx:
                a0, a1 = _at(v, cur[0] - 0.01), _at(v, cur[0] + 1e-4)
                if None not in (a0, a1) and parallels([pv[2], a0], [cur[2], a1]):
                    bad = True
                    break
            if bad and round(cur[0], 4) not in on_beat:
                out[i - 1] = (pv[0], cur[0] + cur[1] - pv[0], pv[2])
                del out[i]
                fixed = True
                continue
            if bad and i >= 2 and round(pv[0], 4) not in on_beat:
                p2 = out[i - 2]
                if p2[0] + p2[1] >= pv[0] - _EPS:
                    out[i - 2] = (p2[0], pv[0] + pv[1] - p2[0], p2[2])
                    del out[i - 1]
                    fixed = True
                    continue
            i += 1
        if not fixed:
            break
    return out


def _clamp_range(notes, lo, hi):
    out = []
    for st, du, p in notes:
        while p < lo:
            p += 12
        while p > hi:
            p -= 12
        out.append((st, du, p))
    return out


def _fill(a: int, b: int | None, n: int, pcs, h: HChord | None, rng) -> list:
    """n notes starting on a, leading toward b (the next beat's note): a scale run when b is n steps away, a
    neighbour / turn figure when b is near, chord tones (an arpeggio) when it is far."""
    if n <= 1:
        return [a]
    if b is None:
        b = a
    steps = 0
    q = a
    dirn = 1 if b > a else -1
    while q != b and steps < 12:
        q += dirn
        if q % 12 in pcs:
            steps += 1
    if q == b and steps == n:                       # a run straight into the next note
        return [_step(a, dirn * i, pcs) for i in range(n)]
    if q == b and steps < n and steps <= 2:
        # near: a turn (upper / lower neighbour) then the step
        up = rng.random() < 0.5
        fig = [a, _step(a, 1 if up else -1, pcs), a, _step(a, -1 if up else 1, pcs)]
        return (fig * 2)[:n]
    if h is not None and abs(b - a) > 4:
        tones = sorted(p for p in range(min(a, b) - 0, max(a, b) + 1) if p % 12 in h.pcs)
        seq = [p for p in tones if (p - a) * dirn >= 0]
        seq = sorted(seq, key=lambda p: (p - a) * dirn)
        out = seq[:n]
        while len(out) < n:
            out.append(_step(out[-1], dirn, pcs))
        return out
    return [_step(a, dirn * i, pcs) for i in range(n)]


# ------------------------------------------------------------------------------------------------ the bass

def bass_line(slots, key, *, lo='C2', hi='D3', walk: float = 0.3, octave_leaps: float = 0.1, start=None,
              against=None, seed=0) -> list:
    """A pedal bass line: the slot's bass (root, or the fixed bass of an inversion / 6-4) in lo..hi, voice-led (a
    beam: steps and 4ths / 5ths, the leading tone into the tonic), every slot one note; `walk` of the beats split
    in two 8ths with a passing tone toward the next bass note when it is a 3rd away, `octave_leaps` an octave leap
    (the pedal's idiom at a cadence). against: the line above (a trio's tune) - no parallel 5ths / octaves with it.
    Returns [(start, dur, pitch)]."""
    k = _key(key)
    rng = random.Random(seed_int(seed))
    lo, hi = note(lo), note(hi)
    beam = [(0.0, [])]
    tops = [sounding(against, s.start) if against else None for s in slots]
    for si, s in enumerate(slots):
        h = s.chord
        pcs = [h.bass] if h.bass is not None else ([h.root] if s.end else [h.root, h.root, h.third])
        cs = sorted({p for p in range(lo, hi + 1) if p % 12 in pcs})
        nb = []
        for cost, path in beam:
            for p in cs:
                c = cost + (0.0 if p % 12 == h.root else 0.8)
                if path:
                    d = abs(p - path[-1])
                    c += {0: 0.8, 1: 0.1, 2: 0.1, 3: 0.4, 4: 0.4, 5: 0.2, 7: 0.3, 12: 0.9}.get(d, 1.2 + 0.1 * d)
                    if si and tops[si] is not None and tops[si - 1] is not None and \
                            parallels([path[-1], tops[si - 1]], [p, tops[si]]):
                        c += 3.0
                elif start is not None:
                    c += 0.3 * abs(p - note(start))
                nb.append((c + rng.random() * 0.05, path + [p]))
        nb.sort(key=lambda x: x[0])
        beam = nb[:30]
    ps = beam[0][1]
    out = []
    for i, (s, p) in enumerate(zip(slots, ps)):
        nxt = ps[i + 1] if i + 1 < len(ps) else None
        if nxt is not None and 3 <= abs(nxt - p) <= 4 and s.dur >= 0.99 and rng.random() < walk and not s.end:
            pas = _step(p, 1 if nxt > p else -1, _scale(k, s.chord))
            out += [(s.start, s.dur - 0.5, p), (s.start + s.dur - 0.5, 0.5, pas)]
        elif nxt is not None and s.dur >= 0.99 and rng.random() < octave_leaps and p + 12 <= hi + 7:
            out += [(s.start, s.dur / 2, p), (s.start + s.dur / 2, s.dur / 2, p + 12)]
        else:
            out.append((s.start, s.dur, p))
    return out


# ------------------------------------------------------------------------------------------------ toccata

TOCCATA_FIGURES = {
    # one harmony slot's beat in 16ths as indices into the chord's tones in close position (0 = lowest; 3 = the
    # octave of 0): Widor's oscillating figure, broken chords up / down, a wave over two octaves, a repeated-note
    # drum (Boellmann), an alternating-hands chord stab (the LH's off-beat chords are a separate stream)
    'widor': (3, 1, 2, 1),
    'broken_up': (0, 1, 2, 3),
    'broken_down': (3, 2, 1, 0),
    'wave': (0, 1, 2, 3, 4, 3, 2, 1),
    'drum': (2, 0, 1, 0),
    'zigzag': (0, 2, 1, 3),
    # the turn cell (songs/toccata-tenebrae): a chord tone, its chromatic lower neighbour, the tone, the chord tone
    # below; inverted: the diatonic upper neighbour and the chord tone above
    'turn': (1, 'c-1', 1, 0),
    'turn_down': (1, 'd+1', 1, 2),
    # the rocking figure (bariolage) around a repeated pivot: a tone, the pivot, the step below the tone, the pivot
    'rocking': (2, 0, 'd-2', 0),
    # a scale run up from the chord's lowest tone (two beats: 8 steps)
    'scale': ('s0', 's1', 's2', 's3', 's4', 's5', 's6', 's7'),
}
"""Toccata figuration per beat (16ths): an int is an index into the slot chord's close-position tones; a token
'c-<i>' the chromatic lower neighbour of tone i, 'd+<i>' / 'd-<i>' its diatonic upper / lower neighbour, 's<k>' k scale
steps above tone 0 (toccata())."""


def _fig_pitch(tok, tones: list, pcs) -> int:
    """One figure token's pitch over the close-position tones (TOCCATA_FIGURES)."""
    if isinstance(tok, int):
        return tones[min(tok, len(tones) - 1)]
    if tok[0] == 's':
        return _step(tones[0], int(tok[1:]), pcs) if int(tok[1:]) else tones[0]
    i = min(int(tok[2:]), len(tones) - 1)
    if tok[:2] == 'c-':
        return tones[i] - 1
    return _step(tones[i], 1 if tok[1] == '+' else -1, pcs)


def _fig_max(fig) -> int:
    return max([x for x in fig if isinstance(x, int)] + [int(x[2:]) for x in fig if isinstance(x, str) and x[0] != 's']
               + [0])


def _close(h: HChord, lo: int, near: int | None = None, n: int = 5) -> list:
    """The chord's tones upward from about lo (root / 3rd / 5th / 7th, repeating by octaves), n of them, the first
    one the tone nearest `near` (voice-led figures) at or above lo."""
    tones = sorted(p for p in range(lo, lo + 30) if p % 12 in h.pcs)
    if near is not None:
        i0 = min(range(min(6, len(tones))), key=lambda i: abs(tones[i] - near))
        tones = tones[i0:]
    return tones[:n]


def toccata(slots, key, *, figure: str = 'widor', register=('C5', 'C6'), lh: str | None = 'offbeat',
            lh_register=('G3', 'G4'), seed=0) -> dict:
    """Toccata figuration over the slots: the right hand runs 16ths of TOCCATA_FIGURES[figure] on each slot's chord
    (close position from register[0], the lowest tone voice-led from slot to slot, under register[1]); the left hand
    (lh='offbeat': chords on the 8th after each beat - Widor's off-beat chords; 'beat': chords on the beats; None: no
    left hand) voiced in lh_register. Returns {'rh': notes, 'lh': notes}."""
    if figure not in TOCCATA_FIGURES:
        raise ComposeError(f"toccata figure must be one of {', '.join(TOCCATA_FIGURES)}, got {figure!r}")
    k = _key(key)
    fig = TOCCATA_FIGURES[figure]
    lo, top = note(register[0]), note(register[1])
    llo, lhi = note(lh_register[0]), note(lh_register[1])
    rh, lhn = [], []
    near = None
    lh_prev = None
    grid = 0.25
    for s in slots:
        h = s.chord
        pcs = _scale(k, h)
        t = s.start
        while t < s.start + s.dur - _EPS:
            tones = _close(h, lo, near, 6)
            while tones and tones[min(len(tones) - 1, _fig_max(fig))] > top:
                tones = [p - 12 for p in tones]
            near = tones[0]
            span = min(len(fig) * grid, s.start + s.dur - t)
            for j, ix in enumerate(fig):
                x = t + j * grid
                if x >= t + span - _EPS:
                    break
                rh.append((x, grid, _fig_pitch(ix, tones, pcs)))
            if lh:                                     # a 3-note voicing in the band, the smoothest from the last
                band = sorted(p for p in range(llo, lhi + 1) if p % 12 in h.pcs)
                opts = [band[i:i + 3] for i in range(max(1, len(band) - 2))]
                ch = min(opts, key=lambda c: (sum(abs(a - b) for a, b in zip(c, lh_prev)) if lh_prev else 0,
                                              c[0])) if band else []
                lh_prev = ch or lh_prev
                if lh == 'offbeat':
                    for off in (0.5,):
                        if t + off < s.start + s.dur - _EPS:
                            lhn += [(t + off, 0.25, p) for p in ch]
                else:
                    lhn += [(t, 0.5, p) for p in ch]
            t += span
    _ = k, seed
    return {'rh': rh, 'lh': lhn}


# ------------------------------------------------------------------------------------------------ fugue

def _transpose_tonal(subject, k: Key, answer_off: int) -> list:
    """The answer: the subject a 5th up (answer_off = +7) or a 4th down (-5); a TONAL answer where the subject opens
    on the dominant (its first note answered by the tonic: the 5th -> the 4th)."""
    out = []
    dom = (k.tonic + 7) % 12
    for i, (st, du, p) in enumerate(subject):
        q = p + answer_off
        if i == 0 and p % 12 == dom:
            q = p + answer_off - 2               # the tonal answer: dominant answered by the tonic
        out.append((st, du, q))
    # keep the answer in the key (the subject's leading tone a 5th up is the dominant's: allowed; its b7 not)
    pcs = _scale(k) | {(k.tonic + 6) % 12}
    return [(st, du, q if q % 12 in pcs else q - 1) for st, du, q in out]


def fugue(subject, key, *, voices: int = 3, order=None, pedal: bool = True, motif: str = 'eighths',
          episode: bool = True, meter: int = 4, seed=0) -> dict:
    """A fugal EXPOSITION from a subject [(start, dur, pitch)] (start at 0, ~2 bars, in the alto range): the voices
    enter one by one - subject (tonic), answer (dominant: _transpose_tonal), subject, answer - in `order` (default
    drawn: alto-soprano-tenor[-bass] or tenor-alto-soprano[-bass]); the voice that has stated keeps on with the
    COUNTERSUBJECT (a counterline against the entry, in 8ths where the subject holds), the earlier ones with free
    counterpoint; the pedal enters last with the subject (pedal=True and voices == 4); an episode (the subject's head
    sequenced down by steps, 2 bars) and a cadence follow (episode=True). Returns {'voices': {name: notes},
    'length': beats, 'entries': [(voice, beat, 'subject' | 'answer')], 'chart': [(start, beats, symbol)]}."""
    k = _key(key)
    rng = random.Random(seed_int(seed))
    sub = sorted(subject)
    L = max(1.0, math.ceil((max(s + d for s, d, _ in sub)) / meter) * meter)
    names = {3: [('A', 0), ('S', 12), ('T', -12)], 4: [('A', 0), ('S', 12), ('T', -12), ('B', -24)]}[voices]
    if order is None:
        if rng.random() < 0.5 and voices == 3:
            names = [('T', -12), ('A', 0), ('S', 12)]
        elif voices == 4 and rng.random() < 0.5:
            names = [('T', -12), ('A', 0), ('S', 12), ('B', -24)]
    else:
        names = [n for n in order]
    R = {'S': (62, 81), 'A': (55, 74), 'T': (48, 67), 'B': (36, 57)}
    V = {nm: [] for nm, _ in names}
    entries = []
    chart = []
    for i, (nm, octv) in enumerate(names):
        t0 = i * L
        kind = 'subject' if i % 2 == 0 else 'answer'
        src = sub if kind == 'subject' else _transpose_tonal(sub, k, 7)
        ent = [(t0 + st, du, p + octv) for st, du, p in src]
        lo_, hi_ = R[nm]
        while ent and min(p for *_, p in ent) < lo_ - 2:
            ent = [(a, b, p + 12) for a, b, p in ent]
        while ent and max(p for *_, p in ent) > hi_ + 2:
            ent = [(a, b, p - 12) for a, b, p in ent]
        V[nm] += ent
        entries.append((nm, t0, kind))
        # the entry's implied harmony: tonic / dominant chords per half bar from the entry's notes
        chart += _implied(ent, k, t0, L, kind)
        # the others: the previous entrant plays the countersubject, the rest free counterpoint
        for j in range(i):
            on, _ = names[j]
            ctx = [V[x] for x, _ in names[:i + 1] if x != on]
            slots = slots_from_chart([c for c in chart if t0 - _EPS <= c[0] < t0 + L - _EPS], k, rate=1.0)
            lo2, hi2 = R[on]
            above = None
            line = counterline(ctx, slots, k, lo=lo2, hi=hi2, motif=motif if j == i - 1 else 'quarter',
                               start=V[on][-1][2] if V[on] else None, rest=0.04 if j == i - 1 else 0.15,
                               hold=0.1 if j == i - 1 else 0.3, mix=0.2, above=above,
                               seed=seed_int(f"{seed}:fugue:{i}:{j}"), meter=meter)
            V[on] += line
    t_end = len(names) * L
    if episode:
        # the episode: the subject's head (its first beat or two) sequenced down by scale steps in the top voice, the
        # others in counterpoint; then a cadence (V - I) over a bar
        head = [n for n in sub if n[0] < 2.0 - _EPS]
        top_nm = max(V, key=lambda x: R[x][1])
        tp = V[top_nm][-1][2] if V[top_nm] else 72
        base = head[0][2] if head else 72
        ep = []
        pcs = _scale(k)
        for r in range(3):
            shift = tp - base
            seq = [(t_end + r * 2.0 + st, du, _step(p + shift, -r, pcs) if r else p + shift) for st, du, p in head]
            ep += seq
        lo_, hi_ = R[top_nm]
        ep = _clamp_range(ep, lo_, hi_)
        V[top_nm] += ep
        e_chart = []
        for r in range(3):
            e_chart.append((t_end + r * 2.0, 2.0, _degree_sym(k, (9, 2, 7)[r] if not _minor(k) else (8, 5, 7)[r])))
        e_chart.append((t_end + 6.0, 1.0, _degree_sym(k, 5, seventh=True)))
        e_chart.append((t_end + 7.0, 1.0, _degree_sym(k, 0)))
        chart += e_chart
        sl = slots_from_chart(e_chart, k, rate=1.0)
        for nm, _ in names:
            if nm == top_nm:
                continue
            ctx = [V[x] for x, _ in names if x != nm]
            lo2, hi2 = R[nm]
            V[nm] += counterline(ctx, sl, k, lo=lo2, hi=hi2, motif='eighths' if nm != 'B' else 'quarter',
                                 start=V[nm][-1][2] if V[nm] else None, rest=0.05, hold=0.2,
                                 seed=seed_int(f"{seed}:ep:{nm}"), meter=meter)
        # the cadence's last chord in every voice
        t_end += 8.0
    return {'voices': V, 'length': t_end, 'entries': entries, 'chart': sorted(chart)}


def _degree_sym(k: Key, rel: int, seventh: bool = False) -> str:
    """A chord symbol on the scale degree `rel` semitones above the tonic (0 tonic, 5 subdominant, 7 dominant ...),
    its quality from the key (the minor's dominant major: the harmonic minor); seventh=True on the dominant: V7."""
    root = (k.tonic + rel) % 12
    if _minor(k):
        q = '' if rel in (7, 3, 8, 10) else 'dim' if rel == 2 else 'm'
    else:
        q = 'm' if rel in (2, 4, 9) else 'dim' if rel == 11 else ''
    if seventh and rel == 7:
        q = '7'
    return _name(root, k) + q


def _implied(ent, k: Key, t0: float, L: float, kind: str) -> list:
    """The harmony an entry implies, per half bar: the tonic triad or the dominant (seventh) chord - whichever holds
    more of the entry's notes in that span (the answer leans to the dominant)."""
    out = []
    tonic = _degree_sym(k, 0)
    dom = _degree_sym(k, 7)
    sub = _degree_sym(k, 5)
    syms = {tonic: _from_symbol(tonic, k), dom: _from_symbol(dom, k), sub: _from_symbol(sub, k)}
    t = t0
    while t < t0 + L - _EPS:
        ps = [p % 12 for st, du, p in ent if t - _EPS <= st < t + 2.0 - _EPS]
        best = max(syms, key=lambda s_: (sum(1 for p in ps if p in syms[s_].pcs)
                                         + (0.6 if (s_ == dom) == (kind == 'answer') else 0.0)
                                         - (0.3 if s_ == sub else 0.0)))
        out.append((t, 2.0, best))
        t += 2.0
    return out


# ------------------------------------------------------------------------------------------------ planing

def planing(melody, key, *, shape=(0, -4, -7), colours=None, lo: int = 50) -> list:
    """Parallel chords under a melody (Messiaen / Debussy / Vierne colour): every melody note gets the same chord
    shape below it (intervals under the top: default a major triad's 6-4 shape with the top note doubled at
    ... ), the inner tones nudged into the key unless `colours` lets chromatic ones stand. Returns the chord notes
    (without the melody itself)."""
    k = _key(key)
    pcs = set(k.pcs) | set(colours or ())
    out = []
    for st, du, p in melody:
        for iv in shape:
            if iv == 0:
                continue
            q = p + iv
            if q % 12 not in pcs:
                q -= 1 if (q - 1) % 12 in pcs else -1
            if q >= lo:
                out.append((st, du, q))
    return out


def ornament_targets(line, meter: int = 4, *, ends=(), min_dur: float = 0.9) -> list:
    """Indices of the notes of a line an organist would ornament: a cadence's penultimate long note (a trill), a
    held note that steps on (a mordent / a turn) - the caller draws from them by its budget."""
    out = []
    ends = sorted(ends)
    for i in range(len(line) - 1):
        st, du, p = line[i]
        nst, _, np_ = line[i + 1]
        if du < min_dur - _EPS:
            continue
        if any(abs(nst - e) < 1.0 + _EPS for e in ends):
            out.append((i, 'trill'))
        elif abs(np_ - p) <= 2 and np_ != p:
            out.append((i, 'mordent' if np_ < p else 'turn'))
    return out
