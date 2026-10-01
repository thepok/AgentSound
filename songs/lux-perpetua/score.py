"""Lux Perpetua - the score as data (an original Requiem in D minor in the idiom of Mozart's K. 626, no borrowed notes).

Everything here is notes and harmony, no sounds: song.py orchestrates and performs it. Pitches are sounding pitch,
times are beats (quarter notes) from the start of each movement. The four-part choir writing is voiced by `satb()`,
a small voice-leading search (chord tones in SATB ranges, complete chords, no doubled leading tone or seventh, no
parallel fifths / octaves, smallest motion) around the lines written by hand (soprano tunes, basses, fugue subject and
countersubject).
"""
from __future__ import annotations

from collections import Counter
from itertools import product

from agentsound.theory import chord as _chord, note as _note


def N(p) -> int:
    return p if isinstance(p, int) else _note(p)


def line(spec: str, t0: float = 0.0, shift: int = 0) -> list:
    """'D4:1 A4:.5 r:1 | ...' -> [(start, dur, pitch)] from t0 (bars '|' are only for the eye)."""
    out, t = [], float(t0)
    for tok in spec.replace('|', ' ').split():
        p, d = tok.split(':')
        d = float(d)
        if p not in ('r', '-'):
            out.append((t, d, N(p) + shift))
        t += d
    return out


def length(spec: str) -> float:
    return sum(float(tok.split(':')[1]) for tok in spec.replace('|', ' ').split())


# ------------------------------------------------------------------------------------------------ chords

class ChordInfo:
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


_INFO: dict = {}


def info(sym: str) -> ChordInfo:
    if sym not in _INFO:
        _INFO[sym] = ChordInfo(sym)
    return _INFO[sym]


# ------------------------------------------------------------------------------------------------ the voicer

ORDER = ('S', 'A', 'T', 'B')
CHOIR = {'S': (60, 79), 'A': (55, 72), 'T': (48, 67), 'B': (43, 62)}          # C4-G5, G3-C5, C3-G4, G2-D4
CENTER = {'S': 70, 'A': 64, 'T': 57, 'B': 50}


def _score(cur: dict, prev: dict, ci: ChordInfo, lt: int | None, free_b: bool, free=(), avoid=()) -> float:
    vs = [v for v in ORDER if v in cur]
    ps = [cur[v] for v in vs]
    for a, b in zip(ps, ps[1:]):
        if a <= b:
            return 1e9
    sc = 0.0
    for v1, v2 in (('S', 'A'), ('A', 'T')):
        if v1 in cur and v2 in cur and cur[v1] - cur[v2] > 12:
            sc += 15 * (cur[v1] - cur[v2] - 12)
    if 'T' in cur and 'B' in cur and cur['T'] - cur['B'] > 19:
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
    if free_b and 'B' in cur:
        sc += 0 if cur['B'] % 12 == ci.bass else 18
    for v, p in cur.items():
        q = prev.get(v)
        if q is not None:
            d = abs(p - q)
            sc += d + (8 if d > 7 else 0) + (20 if d > 12 else 0)
        else:
            sc += 0.15 * abs(p - CENTER[v])
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


def satb(steps: list, *, lt: int | None = 1, ranges: dict | None = None, prev: dict | None = None) -> list:
    """Voice a chord sequence. steps: [{'chord': sym, 'fixed': {voice: pitch}, 'active': voices}] -> one
    {voice: pitch} per step (fixed voices kept, the free ones chosen). lt = the leading tone's pitch class (never
    doubled; C# in D minor)."""
    rng = ranges or CHOIR
    prev = dict(prev or {})
    out = []
    for st in steps:
        ci = info(st['chord'])
        active = tuple(st.get('active', ORDER))
        fixed = {v: N(p) for v, p in (st.get('fixed') or {}).items() if p is not None and v in active}
        free = [v for v in active if v not in fixed]
        cands = [[p for p in range(rng[v][0], rng[v][1] + 1) if p % 12 in ci.pcs] for v in free]
        best = None
        for combo in product(*cands):
            cur = dict(fixed)
            cur.update(zip(free, combo))
            sc = _score(cur, prev, ci, st.get('lt', lt), 'B' in free, free, st.get('avoid', ()))
            if best is None or sc < best[0]:
                best = (sc, cur)
        if best is None or best[0] >= 1e9:
            raise ValueError(f"cannot voice {st['chord']} with {fixed}")
        out.append(best[1])
        for v in ORDER:
            prev[v] = best[1].get(v)
    return out


def chorale(table: list, t0: float = 0.0, *, lt: int | None = 1, ranges=None, prev=None, tie: bool = False,
            active=ORDER) -> dict:
    """Homophonic writing from a table of (dur, chord, S, B[, {voice: pitch}]) rows (S / B None = free; a row with
    chord None is a rest): {voice: [(start, dur, pitch)]}, every voice in the table's rhythm (tie=True merges
    repeated pitches)."""
    steps, times = [], []
    t = float(t0)
    for dur, sym, s_, b_, *more in table:
        if sym is not None:
            steps.append({'chord': sym, 'fixed': {'S': s_, 'B': b_, **(more[0] if more else {})}, 'active': active})
            times.append((t, dur))
        t += dur
    voiced = satb(steps, lt=lt, ranges=ranges, prev=prev)
    out = {v: [] for v in active}
    for (t, dur), vc in zip(times, voiced):
        for v in active:
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


# ================================================================================================ I. INTROITUS
# 4/4, Adagio (q = 56). intro: 6 bars of orchestra (syncopated string pulse over a chromatic lament bass, bassoons
# then basset horns sighing), requiem: 10 bars of choir (staggered entry, the turn to F major 'lux', the Neapolitan
# back to D minor, the lament bass again, a half cadence on A).

INTRO = [  # (dur, chord, top voice, bass) - the strings' harmony
    (2, 'Dm', 'F4', 'D3'), (2, 'A7/C#', 'G4', 'C#3'),
    (2, 'Dm7/C', 'F4', 'C3'), (2, 'G/B', 'G4', 'B2'),
    (2, 'Gm/Bb', 'G4', 'Bb2'), (1, 'Dm/A', 'F4', 'A2'), (1, 'A', 'E4', 'A2'),
    (2, 'Bb', 'F4', 'Bb2'), (2, 'Em7b5/G', 'E4', 'G2'),
    (2, 'Eb/G', 'G4', 'G2'), (2, 'Dm/A', 'F4', 'A2'),
    (4, 'A7', 'E4', 'A2'),
]
INTRO_BASSOON = 'r:1 A3:1 E4:1 G4:1 | F4:1 E4:.5 D4:.5 D4:1.5 C4:.5 | Bb3:1 D4:1 A3:2'
INTRO_BASSET1 = 'r:8 | r:2 D5:1 C#5:1 | D5:1.5 C5:.5 Bb4:2 | Bb4:1 Eb5:1 D5:2 | C#5:3 r:1'
INTRO_BASSET2 = 'r:8 | r:2 A4:1 A4:1 | F4:2 G4:2 | G4:2 F4:2 | E4:3 r:1'

REQUIEM = [  # (dur, chord, soprano (structural), bass) - the choir's harmony, 10 bars
    (4, 'Dm', 'D5', 'D3'),
    (1, 'A7/E', 'C#5', 'E3'), (1, 'Dm', 'D5', 'D3'), (2, 'A7', 'E5', 'A2'),
    (2, 'Dm', 'F5', 'D3'), (1, 'Bb', 'D5', 'Bb2'), (1, 'C7', 'C5', 'C3'),
    (1, 'F', 'C5', 'F3'), (1, 'F', 'A4', 'F3'), (1, 'Gm7', 'Bb4', 'G3'), (1, 'C7', 'Bb4', 'C3'),
    (1, 'F', 'A4', 'F3'), (1, 'F', 'C5', 'F3'), (2, 'F/A', 'F5', 'A2'),
    (1, 'Bb', 'D5', 'Bb2'), (1, 'Gm7', 'G5', 'G2'), (1, 'F/C', 'F5', 'C3'), (1, 'C7', 'E5', 'C3'),
    (1, 'F', 'F5', 'F3'), (1, 'Dm/F', 'D5', 'F3'), (2, 'Eb/G', 'Eb5', 'G2'),
    (1, 'Dm/A', 'D5', 'A2'), (1, 'A7', 'C#5', 'A2'), (1, 'Dm', 'D5', 'D3'), (1, 'Dm7/C', 'F5', 'C3'),
    (1, 'G/B', 'D5', 'B2'), (1, 'Gm/Bb', 'D5', 'Bb2'), (1, 'Dm/A', 'D5', 'A2'), (1, 'A7', 'C#5', 'A2'),
    (2, 'Asus4', 'D5', 'A2'), (2, 'A', 'C#5', 'A2'),
]
# bar 1: the choir enters voice by voice, B T A S a beat apart, each on 'Re-qui-em' (a note, its upper neighbour,
# back); the soprano's pickup lands on the leading tone of bar 2
REQUIEM_ENTRY = {
    'B': 'D3:1 E3:.5 D3:2.5',
    'T': 'r:1 A3:1 Bb3:.5 A3:1.5',
    'A': 'r:2 F4:1 G4:.5 F4:.5',
    'S': 'r:2.5 A4:.5 D5:1',
}
REQUIEM_SOPRANO = ('r:4 | C#5:1 D5:1 E5:2 | F5:1.5 E5:.5 D5:1 C5:1 | C5:1 A4:1 Bb4:2 | '
                   'A4:1 C5:1 F5:1.5 E5:.5 | D5:1 G5:1 F5:1 E5:1 | F5:1 D5:1 Eb5:1.5 D5:.5 | '
                   'D5:1 C#5:1 D5:1 F5:1 | D5:2 D5:1 C#5:1 | D5:2 C#5:2')      # the lament bass under a held D, 4-3

# ================================================================================================ KYRIE (fugue)
# 4/4, Allegro moderato (q = 88), 19 bars. Subject (a rising fifth, the sigh on the sixth, a falling scale into the
# leading tone) and a chromatic countersubject, entries bass - tenor (answer) - alto - soprano (answer), an
# episode (the head in imitation over a circle of fifths into F major), a middle entry in F major (tenors), the
# bass and the alto a bar apart, the Adagio cadence (iv6 - N6 - V7) onto a bare fifth.

SUBJECT = 'D4:1 A4:1 Bb4:1.5 A4:.5 G4:.5 F4:.5 E4:.5 D4:.5 C#4:1 D4:1'
# the answer is tonal: the head's fifth D-A is answered by the fourth A-D, the rest in A minor
ANSWER = 'A3:1 D4:1 F4:1.5 E4:.5 D4:.5 C4:.5 B3:.5 A3:.5 G#3:1 A3:1'
COUNTER = 'F3:2 E3:2 Eb3:1 D3:1 E3:1 F3:1'
SUBJECT_F = 'F4:1 C5:1 D5:1.5 C5:.5 Bb4:.5 A4:.5 G4:.5 F4:.5 E4:1 F4:1'
H_D = [(0, 2, 'Dm'), (2, 2, 'Em7b5'), (4, 2, 'A7'), (6, 1, 'A7'), (7, 1, 'Dm')]   # beat 6: the voicer sees the C#
H_A = [(0, 1, 'Am'), (1, 1, 'Dm7'), (2, 2, 'Bm7b5'), (4, 2, 'E7'), (6, 1, 'E7'), (7, 1, 'Am')]   # the answer's D: iv7
H_F = [(0, 2, 'F'), (2, 2, 'Gm7'), (4, 2, 'C7'), (6, 1, 'C7'), (7, 1, 'F')]


def _at(h, t0):
    return [(s + t0, d, c) for s, d, c in h]


KYRIE_HARMONY = (_at(H_D, 0) + _at(H_A, 8) + _at(H_D, 16) + _at(H_A, 24)
                 + [(32, 2, 'Dm'), (34, 2, 'Gm7'), (36, 2, 'C7'), (38, 2, 'F'),
                    (40, 2, 'Bb'), (42, 2, 'Gm7'), (44, 2, 'C7sus4'), (46, 2, 'C7')]
                 + _at(H_F, 48) + _at(H_D, 56)[:2]
                 + [(60, 1, 'Gm'), (61, 1, 'A7'), (62, 1, 'C#dim7'), (63, 1, 'Dm'),
                    (64, 3, 'A7'), (67, 1, 'Dm'),
                    (68, 1, 'Gm/Bb'), (69, 1, 'Eb/G'), (70, 2, 'A7'),
                    (72, 4, 'D5')])
KYRIE_LT = {**{t: 1 for t in range(0, 76)}, **{t: 8 for t in list(range(8, 16)) + list(range(24, 32))},
            **{t: 4 for t in range(36, 56)}}
KYRIE_FIXED = {  # voice -> [(start, dur, pitch)]: the subject / countersubject entries and the episode's head motifs
    'B': line(SUBJECT, 0, -12) + line(COUNTER, 8, -5) + line(SUBJECT, 56, -12)
         + line('D3:1 A2:1 G2:1 Bb2:1 C3:1 E3:1 F3:1 A2:1 Bb2:1 D3:1 G2:1 Bb2:1 C3:2 C3:1 Bb2:1', 32),  # the walk
    'T': line(ANSWER, 8) + line(COUNTER, 16) + line('Bb3:1 F4:1 G4:1.5 F4:.5', 40) + line(SUBJECT_F, 48, -12),
    'A': line(SUBJECT, 16) + line(COUNTER, 24, 7) + line('D4:1 A4:1 Bb4:1.5 A4:.5', 32) + line('G4:2', 58)
         + line(SUBJECT, 60),
    'S': line(ANSWER, 24, 12) + line('C5:1 G5:1 A5:1.5 G5:.5', 36) + line('C5:1 G5:.5 F5:.5 E5:2', 44)
         + line('D5:1 Eb5:1 C#5:2 D5:4', 68),
}
KYRIE_ENTRY = {'B': 0, 'T': 8, 'A': 16, 'S': 24}
KYRIE_FINAL = {'S': 'D5', 'A': 'A4', 'T': 'A3', 'B': 'D3'}       # the bare fifth (no third)
KYRIE_LENGTH = 76

# ================================================================================================ DIES IRAE
# 4/4, Allegro assai (q = 144), 24 bars: dies (8: the outburst, a turn to F major), tremor (8: subito p, trembling
# repeated chords over a chromatic rising bass F - F# - G - G# - A, crescendo into the dominant pedal, a deceptive
# Bb, the Neapolitan), ira (8: the climax, the cadence, hammered chords, silence).

DIES = [
    (2, 'Dm', 'D5', 'D3'), (1, 'Dm', 'F5', 'D3'), (1, 'Dm', 'A5', 'D3'),
    (1.5, 'A7/C#', 'E5', 'C#3'), (.5, 'A7/C#', 'E5', 'C#3'), (2, 'Dm', 'D5', 'D3'),
    (1, 'Bb', 'D5', 'Bb2'), (1, 'Bb', 'F5', 'Bb2'), (2, 'Gm/Bb', 'G5', 'Bb2'),
    (3, 'A', 'E5', 'A2'), (1, None, None, None),
    (2, 'Dm', 'F5', 'D3'), (1, 'Bb', 'F5', 'Bb2'), (1, 'Bb', 'D5', 'Bb2'),
    (2, 'C7/E', 'G5', 'E3'), (2, 'F', 'F5', 'F3'),
    (1, 'Bb', 'F5', 'Bb2'), (1, 'Bb', 'D5', 'Bb2'), (1, 'C7', 'E5', 'C3'), (1, 'C7', 'G5', 'C3'),
    (3, 'F', 'F5', 'F3'), (1, None, None, None),
]
TREMOR = (
    [(1, 'Dm/F', 'A4', 'F3')] * 4 + [(1, 'F#dim7', 'C5', 'F#3')] * 4
    + [(1, 'Gm', 'D5', 'G3')] * 4 + [(1, 'G#dim7', 'F5', 'G#3')] * 4
    + [(2, 'Dm/A', 'F5', 'A3'), (2, 'A7', 'E5', 'A3'),
       (2, 'Dm/A', 'A5', 'A2'), (2, 'A7', 'G5', 'A2'),
       (4, 'Bb', 'F5', 'Bb2'),
       (2, 'Eb/G', 'G5', 'G2'), (2, 'A7', 'G5', 'A2')])
IRA = [
    (2, 'Dm', 'F5', 'D3'), (1, 'Dm/F', 'A5', 'F3'), (1, 'Dm/F', 'F5', 'F3'),
    (2, 'Gm/Bb', 'G5', 'Bb2'), (2, 'C#dim7/G', 'E5', 'G2'),
    (2, 'Dm/A', 'F5', 'A2'), (2, 'A7', 'E5', 'A2'),
    (3, 'Dm', 'D5', 'D3'), (1, None, None, None),
    (1, 'Dm', 'D5', 'D3'), (1, 'Dm', 'D5', 'D3'), (2, 'Bb', 'F5', 'Bb2'),
    (2, 'Eb/G', 'G5', 'G2'), (2, 'A7', 'G5', 'A2'),
    (1, 'Dm', 'F5', 'D3'), (3, None, None, None),
    (4, None, None, None),
]

# ================================================================================================ TUBA
# 4/4, Andante (q = 72), Bb major, 8 bars: the solo tenor trombone's call (a rising arpeggio, a falling answer, a
# half cadence), then the men of the choir in unison with the trombone above them; the last bar turns to A7 (the
# dominant of D minor) under a fermata.

TUBA = [
    (4, 'Bb', 'F4', 'Bb2'),
    (2, 'Bb', 'F4', 'Bb2'), (2, 'Eb', 'G4', 'Eb3'),
    (2, 'Cm', 'G4', 'C3'), (2, 'F7', 'F4', 'F2'),
    (4, 'F', 'F4', 'F2'),
    (2, 'Bb/D', 'F4', 'D3'), (2, 'Eb', 'G4', 'Eb3'),
    (2, 'Cm7', 'G4', 'C3'), (2, 'F7', 'A4', 'F2'),
    (1, 'Bb/F', 'Bb4', 'F2'), (1, 'F7', 'A4', 'F2'), (1, 'Gm', 'Bb4', 'G2'), (1, 'Eb', 'G4', 'Eb2'),
    (2, 'Gm', 'G4', 'G2'), (2, 'A7', 'G4', 'A2'),
]
TUBA_TROMBONE = ('Bb2:1 D3:1 F3:2 | Bb3:1.5 A3:.5 G3:1 F3:1 | Eb3:2 C3:1 A2:1 | F3:3 r:1 | '
                 'r:2 G3:1 Bb3:1 | C4:1.5 Bb3:.5 A3:1 C4:1 | D4:1 C4:1 Bb3:1 G3:1 | Bb3:2 A3:2')
TUBA_MEN = 'r:16 | D3:2 Eb3:2 | G3:1.5 F3:.5 F3:2 | F3:1 Eb3:1 D3:1 Bb2:1 | D3:2 r:2'

# ================================================================================================ LACRIMOSA
# 12/8 (a bar = 6 beats = four dotted quarters), Larghetto (q = 72), 12 bars: lacrimosa (8: the violins' sighs,
# the choir's lament, the chromatic climb over a descending bass to the forte climax, the sinking answer), amen
# (4: plagal 'amen' chords, the Neapolitan, the Picardy third: D major under a fermata).

G = 1.5            # one dotted quarter
LACRIMOSA = [  # (dur, chord, soprano (structural), bass) per dotted quarter
    (G, 'Dm', 'F4', 'D3'), (G, 'Dm', 'F4', 'D3'), (G, 'A7/C#', 'E4', 'C#3'), (G, 'Dm', 'F4', 'D3'),
    (G, 'Gm/Bb', 'G4', 'Bb2'), (G, 'Eb/G', 'G4', 'G2'), (G, 'Dm/A', 'F4', 'A2'), (G, 'A7', 'E4', 'A2'),
    (G, 'Dm', 'A4', 'D3'), (G, 'A/E', 'C#5', 'E3'), (G, 'Em7b5/G', 'E5', 'G2', {'A': 'D5'}), (G, 'A', 'E5', 'A2'),
    (G, 'Dm', 'F5', 'D3'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Dm/A', 'D5', 'A2'), (G, 'A', 'A4', 'A2'),
    (G, 'Dm', 'A4', 'D3'), (G, 'Gm', 'Bb4', 'G2'), (G, 'E7/G#', 'B4', 'G#2'), (G, 'Am', 'C5', 'A2'),
    (G, 'A', 'C#5', 'A2'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Em7b5/Bb', 'E5', 'Bb2'), (G, 'A7', 'E5', 'A2'),
    (G, 'Dm', 'F5', 'D3'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Dm/A', 'D5', 'A2'), (G, 'A7', 'C#5', 'A2'),
    (G, 'Dm', 'D5', 'D3'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Em7b5/G', 'E5', 'G2'), (G, 'A7', 'C#5', 'A2'),
]
AMEN = [
    (G, 'Dm', 'A4', 'D3'), (G, 'Gm/D', 'Bb4', 'D3'), (G, 'Dm', 'A4', 'D3'), (G, 'Bb/D', 'Bb4', 'D3'),
    (G, 'Eb/G', 'Bb4', 'G2'), (G, 'Dm/A', 'A4', 'A2'), (G, 'A7', 'A4', 'A2'), (G, 'A7', 'G4', 'A2'),
    (G, 'Dm', 'F4', 'D3'), (G, 'Gm/D', 'G4', 'D3'), (2 * G, 'D', 'F#4', 'D3'),
    (6, 'D', 'F#4', 'D3'),
]
LACRIMOSA_SOPRANO = ('r:12 | A4:1 D5:.5 C#5:1 D5:.5 E5:1 F5:.5 E5:1.5 | F5:1 E5:.5 D5:1 C#5:.5 D5:1 Bb4:.5 A4:1.5 | '
                     'A4:1.5 Bb4:1.5 B4:1.5 C5:1.5 | C#5:1.5 D5:1.5 E5:3 | '
                     'F5:1 E5:.5 D5:1 C#5:.5 D5:1 E5:.5 C#5:1.5 | D5:1.5 F5:1 D5:.5 E5:1 D5:.5 C#5:1.5')
AMEN_SOPRANO = 'A4:1.5 Bb4:1.5 A4:1.5 Bb4:1.5 | Bb4:1.5 A4:1.5 A4:1.5 G4:1.5 | F4:1.5 G4:1.5 F#4:3 | F#4:6'


# ================================================================================================ helpers for song.py

def _key_pcs(t: float):
    """The Kyrie's local key at beat t (from its start): (scale pcs, tonic pc, leading-tone pc)."""
    if 8 <= t < 16 or 24 <= t < 32:
        return {9, 11, 0, 2, 4, 5, 7}, 9, 8                   # A minor (the answers)
    if 32 <= t < 56:
        return {5, 7, 9, 10, 0, 2, 4}, 5, 4                   # the episode and the middle entry: F major
    return {2, 4, 5, 7, 9, 10, 0}, 2, 1                       # D minor


def _at_time(notes, t):
    for n in notes:
        if n[0] - 1e-6 <= t < n[0] + n[1] - 1e-6:
            return n[2]
    return None


def _parallel_or_rub(parts, v, seq) -> bool:
    """True when the line seq [(t, pitch) ...] of voice v (its first and last entries are the notes around the new
    ones) makes parallel fifths / octaves with another voice, or a new note rubs a semitone / minor ninth against
    one."""
    for w in ORDER:
        if w == v:
            continue
        for t, u in seq[1:-1]:
            if any(q is not None and abs(u - q) % 12 in (1, 11)
                   for q in (_at_time(parts[w], t), _at_time(parts[w], t + 0.25))):
                return True
        for (ta, ua), (tb, ub) in zip(seq, seq[1:]):
            wa, wb = _at_time(parts[w], ta), _at_time(parts[w], tb)
            if None in (wa, wb) or wa == wb or ua == ub or (ub - ua) * (wb - wa) <= 0:
                continue
            if abs(ua - wa) % 12 == abs(ub - wb) % 12 and abs(ua - wa) % 12 in (0, 7):
                return True
    return False


def arpeggiate(parts: dict, free: set, harmony: list, t0: float, until: float = 68.0) -> list:
    """The fugue's free voices move in quarters: a free note of 2 beats or more gives its last beat to another tone
    of its chord (a leap of a third to a fifth) that approaches the next note by step or third, where that makes no
    parallels or rubs. harmony: [(start, dur, chord)] from t0. Edits parts in place; returns [(beat, voice, pitch)]."""
    from agentsound.theory import chord as _ch
    added = []
    for v in ORDER:
        out = []
        ns = parts[v]
        lo, hi = CHOIR[v]
        for i, (a, d, p1) in enumerate(ns):
            nxt = ns[i + 1] if i + 1 < len(ns) else None
            c = None
            if ((v, round(a, 4)) in free and d >= 2 - 1e-6 and nxt is not None and abs(a + d - nxt[0]) < 1e-6
                    and a + d - t0 <= until):
                sym = harmony_at([(x + t0, y, z) for x, y, z in harmony], a + d - 1)
                pcs = set(_ch(sym).pcs) if sym else set()
                cands = [q for q in range(lo, hi + 1) if q % 12 in pcs and 3 <= abs(q - p1) <= 7
                         and 1 <= abs(q - nxt[2]) <= 4]
                for q in sorted(cands, key=lambda q: (abs(q - nxt[2]), abs(q - p1))):
                    if not _parallel_or_rub(parts, v, [(a + d - 1.01, p1), (a + d - 1, q), (a + d, nxt[2])]):
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


def passing_eighths(parts: dict, free: set, t0: float, until: float = 68.0) -> list:
    """Counterpoint for the fugue's free voices: a note that moves a third to the next note gives its last 8th to
    the step between, one that moves a fourth its last two 8ths (the scale of the local key; the leading tone into
    the tonic) - unless that makes parallel fifths / octaves with another voice or rubs a semitone / minor ninth
    against one. parts: {voice: [(start, dur, pitch)]} (song beats, sorted), free: {(voice, start)} of the free
    notes. Edits parts in place; returns [(beat, voice, pitch)] of the passing notes."""
    added = []
    for v in ORDER:
        out = []
        ns = parts[v]
        for i, (a, d, p1) in enumerate(ns):
            nxt = ns[i + 1] if i + 1 < len(ns) else None
            gap = abs(nxt[2] - p1) if nxt is not None else 0
            k = 1 if 3 <= gap <= 4 else 2 if gap == 5 else 0
            ok = ((v, round(a, 4)) in free and k and d >= 0.5 * k + 0.5 - 1e-6 and abs(a + d - nxt[0]) < 1e-6
                  and a + d - t0 <= until)
            xs = None
            if ok:
                p2 = nxt[2]
                tp = a + d - 0.5 * k
                pcs, tonic, lt = _key_pcs(tp - t0)
                if p2 % 12 == tonic and p2 > p1:
                    pcs = (pcs - {(tonic - 2) % 12}) | {lt}
                cands = [q for q in range(min(p1, p2) + 1, max(p1, p2)) if q % 12 in pcs]
                if len(cands) == k:
                    xs = cands if p2 > p1 else cands[::-1]
                    seq = [(tp - 0.01, p1)] + [(tp + 0.5 * j, x) for j, x in enumerate(xs)] + [(a + d, p2)]
                    if _parallel_or_rub(parts, v, seq):
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


def swells(notes, a: float, b: float, period: float, lo: float = 0.65) -> list:
    """Expression points for a sung line that breathes: from `a` to `b`, one swell per `period` beats - soft at the
    start, full on the phrase's highest note, soft again at its end (lo 0.65 = ~7.5 dB of swell) - then back to 1."""
    pts = [(a - 0.3, 1.0), (a - 0.05, lo)]
    w = a
    while w < b - 1e-6:
        e = min(b, w + period)
        inside = [n for n in notes if w - 1e-6 <= n[0] < e - 1e-6]
        peak = max(inside, key=lambda n: (n[2], -n[0]))[0] if inside else (w + e) / 2
        peak = min(max(peak, w + 0.25 * (e - w)), w + 0.75 * (e - w))
        pts += [(peak, 1.0, 'smooth'), (e - 0.05, lo, 'smooth')]
        w = e
    pts.append((b + 0.2, 1.0, 'smooth'))
    return pts
