"""A guitarist's hands: a FRETBOARD model that turns chords into playable voicings, a strumming / picking engine,
named, reusable guitar MOVES and two arrangers - a rhythm guitarist (arrange) and a lead guitarist (lead).

User feedback (recipes/HUMAN_FEEDBACK.md): "möglichst realistische, nicht keyboard-artige Instrumente" - a guitar part
is never a block chord struck on a keyboard. A guitarist frets shapes a hand can hold (open chords, barre shapes,
power chords, triads on string sets, shells), one note per string, and voice-leads between them; the picking hand
strums (a downstroke low -> high over ~15-35 ms, an upstroke high -> low, lighter, fewer strings), mutes (chucks,
dead-note scratches, palm mutes), accents, arpeggiates (Travis picking, ballad arpeggios, let-ring) and chugs; the
lead hand bends, slides, hammers on and pulls off, adds vibrato, rakes, double stops. Flashy moves are SPICE, not a
habit (the pianist's lesson: "zu viele von diesen schnellen Zwei-Tasten-Wechseln"): a budget per bar class keeps
them rare. The part follows the song form: verse lighter (arpeggios, palm mutes), chorus bigger (open strums, power
chords), fills into the next section.

    from agentsound import guitarist as gtr
    arr = gtr.arrange(prog, bpm=126, style='rock', section=verse, sound=b.gtr_l, seed=3)   # a rhythm part
    arr.play(b.gtr_l, verse)                                                                # notes (+ marks)
    b.gtr_r.play(arr.take(2).clip, verse)                                                   # a second take
    ld = gtr.lead(melody, prog, bpm=126, style='rock', sound=b.lead, seed=1)               # a lead part
    ld.play(b.lead, chorus)                                  # notes + pitchbend (bends) + vibrato automation
    b.acoustic.play(gtr.strum(gtr.shape('G'), 2.0, 96, direction='down'), verse.bar(3))    # one move

The fretboard: Fretboard(tuning='standard' | TUNINGS | 6 pitches, capo=0, stretch=4); shape(chord, kind=...) the
best shape, shapes(...) all; voice_lead(chords, kind) the smoothest path. KINDS: open, barre, full, power, upper
(triads / 4-note grips on string sets), shell (jazz). A shape knows its frets (low E first; None = muted), pitches,
fingers, span and position. Every move takes the tempo (bpm) because strums and picking figures are timed in real
time; velocities are shaped and timing carries a few ms of seeded human wobble. Articulations: with sound= (a
track / patch) the player uses the guitar's own 'palm mute', 'dead note', 'hammer-on', 'muted' keyswitches
(articulation.available); without them it emulates (short, lighter notes).
"""

from __future__ import annotations

import functools
import math
import random
from typing import NamedTuple

from . import articulation as _art
from .budget import Budget
from .humanize import touch as _touch
from .patterns import Clip, Note, _as_prog, _vel, as_clip, beats, seed_int
from .theory import Chord, ComposeError, Key, Progression, chord_kind, chord_scale, note

__all__ = ['TUNINGS', 'KINDS', 'TECHNIQUES', 'PATTERNS', 'STYLES', 'LEAD_STYLES', 'SECTION_ENERGY', 'FILLS',
           'RHYTHM_ORNAMENTS', 'FAST', 'FLASH', 'SPICE', 'MOVES', 'Fretboard', 'Shape', 'Lick', 'Memory', 'Arrangement',
           'shape', 'shapes', 'voice_lead', 'best_capo', 'strum', 'chuck', 'strum_pattern', 'arpeggio', 'travis',
           'chug', 'skank', 'scratch', 'let_ring', 'hammer_chord', 'slide_chord', 'bass_run', 'choke', 'build',
           'bend', 'prebend', 'vibrato', 'slide', 'hammer_on', 'pull_off', 'trill', 'double_stop', 'rake',
           'harmonic', 'tremolo_pick', 'lick', 'arrange', 'lead', 'vocabulary']

_EPS = 1e-6


# ------------------------------------------------------------------------------------------------ helpers

def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        rng = f"{lo:g}.." if hi is None else f"..{hi:g}" if lo is None else f"{lo:g}..{hi:g}"
        raise ComposeError(f"{what} = {x:g} is outside {rng}")
    return float(x)


def _bpm(bpm) -> float:
    return _num(bpm, 'bpm', 20, 400)


def _sec(seconds: float, bpm: float) -> float:
    """Seconds -> beats."""
    return seconds * bpm / 60.0


def _ms(ms: float, bpm: float) -> float:
    return ms / 1000.0 * bpm / 60.0


def _pos(at) -> float:
    if hasattr(at, 'start') and not isinstance(at, (int, float)):
        return float(at.start)
    return _num(at, 'at (beats)', 0)


def _tri(rng: random.Random) -> float:
    """Triangular noise in -1..1 (mostly small)."""
    return rng.random() + rng.random() - 1.0


def _vels(vel) -> tuple[float, float]:
    if isinstance(vel, (tuple, list)):
        if len(vel) != 2:
            raise ComposeError(f"vel must be a number or (lo, hi), got {vel!r}")
        a, b = _num(vel[0], 'vel', 1, 127), _num(vel[1], 'vel', 1, 127)
        return (min(a, b), max(a, b))
    v = _num(vel, 'vel', 1, 127)
    return v, v


def _chord(ch) -> Chord:
    return Chord.parse(ch)


def _key(key) -> Key | None:
    if key is None or isinstance(key, Key):
        return key
    return Key(key)


def _scale_pcs(ch=None, key=None) -> set[int]:
    if ch is not None:
        c = _chord(ch)
        return {(c.root + i) % 12 for i in chord_scale(c)}
    k = _key(key)
    return set(k.pcs) if k is not None else {0, 2, 4, 5, 7, 9, 11}


def _pentatonic(ch=None, key=None) -> set[int]:
    """The pentatonic a guitarist reaches for: minor pentatonic on minor / dominant (blues) chords, major on major."""
    if ch is None:
        k = _key(key)
        if k is None:
            return {0, 3, 5, 7, 10}
        return {(k.tonic + i) % 12 for i in ((0, 3, 5, 7, 10) if k.minorish else (0, 2, 4, 7, 9))}
    c = _chord(ch)
    kind = chord_kind(c)
    iv = (0, 2, 4, 7, 9) if kind in ('maj', 'maj7', '6', 'sus', 'aug') else (0, 3, 5, 7, 10)
    return {(c.root + i) % 12 for i in iv}


def _step(p: int, pcs, n: int) -> int:
    pcs = set(pcs)
    q, d = p, (1 if n > 0 else -1)
    for _ in range(abs(n)):
        q += d
        while q % 12 not in pcs:
            q += d
    return q


def _clip(notes, length: float | None = None) -> Clip:
    """(start, dur, pitch, vel[, art[, glide]]) tuples -> a Clip (articulation / glide marks kept)."""
    ns = []
    for x in notes:
        s, d, p, v = x[0], x[1], x[2], x[3]
        a = x[4] if len(x) > 4 else None
        g = x[5] if len(x) > 5 else None
        n = Note(float(max(0.0, s)), float(max(0.02, d)), int(p), _vel(v))
        if a is not None or g:
            n = _art._mark(n, art=a, gl=g)
        ns.append(n)
    end = max((n.start + n.dur for n in ns), default=0.0)
    L = float(length) if length is not None else (float(math.ceil(end - _EPS)) if end > 0 else 0.0)
    return Clip._raw(ns, L)


def _pick(rng: random.Random, weights: dict, avoid=None):
    items = [(k, w * (0.3 if k == avoid else 1.0)) for k, w in weights.items() if w > 0]
    if not items:
        return None
    tot = sum(w for _, w in items)
    x = rng.random() * tot
    for k, w in items:
        x -= w
        if x <= 0:
            return k
    return items[-1][0]


# ------------------------------------------------------------------------------------------------ the fretboard

TUNINGS = {
    'standard': ('E2', 'A2', 'D3', 'G3', 'B3', 'E4'),
    'drop_d': ('D2', 'A2', 'D3', 'G3', 'B3', 'E4'),
    'half_down': ('Eb2', 'Ab2', 'Db3', 'Gb3', 'Bb3', 'Eb4'),
    'full_down': ('D2', 'G2', 'C3', 'F3', 'A3', 'D4'),
    'drop_c': ('C2', 'G2', 'C3', 'F3', 'A3', 'D4'),
    'dadgad': ('D2', 'A2', 'D3', 'G3', 'A3', 'D4'),
    'open_g': ('D2', 'G2', 'D3', 'G3', 'B3', 'D4'),
    'open_d': ('D2', 'A2', 'D3', 'F#3', 'A3', 'D4'),
    'open_e': ('E2', 'B2', 'E3', 'G#3', 'B3', 'E4'),
}
"""Six-string tunings, low string first (Fretboard(tuning=...), or pass 6 pitches)."""

KINDS = ('open', 'barre', 'full', 'power', 'upper', 'shell')
"""Voicing kinds: open (first-position chords with open strings; a barre shape where none fits), barre (E- / A-shape
barre chords, 5-6 strings, no open strings), full (any 4-6 string shape, the cheapest), power (root + 5th [+ octave]
on 2-3 low strings), upper (3-4 note grips on the D-G-B-E / A-D-G-B string sets, inversions: funk, reggae, pop
verses), shell (jazz: root + 3rd + 7th on the low strings, Freddie Green)."""


class Shape(NamedTuple):
    """A fretted chord shape: frets per string (low string first; None = muted / not played, 0 = open - at the capo),
    the pitches per string (None where muted), its kind, the fingers it needs, span (fret distance of the fretted
    notes), pos (the lowest fretted fret, 0 = all open) and a cost (lower = more idiomatic)."""
    frets: tuple
    pitches: tuple
    kind: str
    fingers: int
    span: int
    pos: int
    cost: float
    chord: str = ''

    @property
    def notes(self) -> list[int]:
        """The sounding pitches, low to high."""
        return [p for p in self.pitches if p is not None]

    @property
    def strings(self) -> list[int]:
        """The sounding strings (0 = the lowest), low to high."""
        return [i for i, p in enumerate(self.pitches) if p is not None]

    @property
    def open_strings(self) -> int:
        return sum(1 for f in self.frets if f == 0)

    def diagram(self) -> str:
        """The usual chord-chart spelling, low string first: 'x32010' (frets >= 10 in parentheses)."""
        return ''.join('x' if f is None else (str(f) if f < 10 else f"({f})") for f in self.frets)

    def __repr__(self) -> str:
        return f"Shape({self.chord or '?'} {self.diagram()} {self.kind})"


class Fretboard:
    """A six-string neck: tuning (a TUNINGS name or six pitches, low first), capo (fret), frets (the highest usable
    fret) and stretch (the frets one hand covers: fretted notes of a shape at most stretch - 1 frets apart below the
    7th fret, stretch above it, where the frets are narrower). Frets of a shape are counted from the capo."""

    def __init__(self, tuning='standard', capo: int = 0, frets: int = 20, stretch: int = 4):
        if isinstance(tuning, str):
            if tuning not in TUNINGS:
                raise ComposeError(f"unknown tuning {tuning!r}; use one of {', '.join(TUNINGS)} or six pitches")
            self.tuning_name = tuning
            tun = TUNINGS[tuning]
        else:
            tun = tuple(tuning)
            self.tuning_name = 'custom'
            if len(tun) != 6:
                raise ComposeError(f"a tuning needs six pitches (low string first), got {tuning!r}")
        self.capo = int(_num(capo, 'capo', 0, 12))
        self.frets = int(_num(frets, 'frets', 5, 24))
        self.stretch = int(_num(stretch, 'stretch', 2, 6))
        self.tuning = tuple(note(x) for x in tun)
        self.open = tuple(p + self.capo for p in self.tuning)
        self.top = self.frets - self.capo

    def key(self) -> tuple:
        return (self.open, self.top, self.stretch)

    def __repr__(self) -> str:
        return f"Fretboard({self.tuning_name}, capo {self.capo})"

    @property
    def lowest(self) -> int:
        return min(self.open)

    @property
    def highest(self) -> int:
        return max(self.open) + self.top

    def pitch(self, string: int, fret: int) -> int:
        return self.open[string] + fret

    def positions(self, pitch, lo: int = 0, hi: int | None = None) -> list[tuple[int, int]]:
        """Where a pitch lies: [(string, fret)] with lo <= fret <= hi (default: the whole neck)."""
        p = note(pitch)
        h = self.top if hi is None else hi
        return [(s, p - o) for s, o in enumerate(self.open) if lo <= p - o <= h]

    def reach(self, pos: int) -> int:
        """The fret distance one hand spans at position pos."""
        return self.stretch - 1 if pos < 7 else self.stretch

    def fingers(self, frets) -> int:
        """Fingers a shape needs: one per fretted note, a barre (the index across the lowest fret on 2+ strings with
        no open string under it) counts once. 99 when impossible (an open string under a barre that is needed)."""
        fr = [(s, f) for s, f in enumerate(frets) if f is not None and f > 0]
        if not fr:
            return 0
        lo = min(f for _, f in fr)
        at_lo = [s for s, f in fr if f == lo]
        if len(at_lo) >= 2:
            a, b = min(at_lo), max(at_lo)
            barre_ok = all(frets[s] is None or frets[s] >= lo for s in range(a, b + 1))
            if barre_ok:
                return 1 + sum(1 for _, f in fr if f > lo)
        return len(fr)

    def playable(self, frets) -> bool:
        """One hand can hold it: at most 4 fingers (a barre counts once), the fretted notes within reach, on the
        neck."""
        if len(frets) != 6:
            return False
        fr = [f for f in frets if f is not None and f > 0]
        if any(f is not None and (f < 0 or f > self.top) for f in frets):
            return False
        if not fr:
            return True
        lo, hi = min(fr), max(fr)
        return hi - lo <= self.reach(lo) and self.fingers(frets) <= 4


# ------------------------------------------------------------------------------------------------ shapes

def _board(fretboard=None, tuning='standard', capo: int = 0) -> Fretboard:
    if isinstance(fretboard, Fretboard):
        return fretboard
    if fretboard is not None:
        raise ComposeError(f"fretboard must be a guitarist.Fretboard, got {fretboard!r}")
    return Fretboard(tuning, capo)


def _required(c: Chord, kind: str, strings: int) -> tuple[set[int], set[int]]:
    """(required pitch classes, allowed pitch classes) of a chord for a shape kind."""
    root = c.root
    allowed = {(root + i) % 12 for i in c.intervals} | {c.bass_pc}
    if kind == 'power':
        return {root, (root + 7) % 12}, {root, (root + 7) % 12}
    pri = [i % 12 for i in c.priority()]
    pri = list(dict.fromkeys(pri))
    if kind == 'shell':
        tones = [i for i in pri if i != 7][:3]
        if len(tones) < 3 and 7 in pri:
            tones.append(7)                    # a triad: root, 3rd and 5th
        req = {(root + i) % 12 for i in tones}
        return req, req | ({(root + 7) % 12} if 7 in pri else set())
    n = max(3, min(strings, 4))
    tones = pri[:n]
    if len(pri) > 3 and 7 in tones:            # a 7th chord or richer: the 5th is optional
        tones = [i for i in pri if i != 7][:n]
    req = {(root + i) % 12 for i in tones}
    if kind == 'upper' and len(req) > strings:
        req = {(root + i) % 12 for i in tones[:strings]}
    return req, allowed


@functools.lru_cache(maxsize=4096)
def _search(board_key: tuple, symbol: str, kind: str) -> tuple:
    """All playable shapes of a chord of a kind (cost-sorted) on a board (open strings, top fret, stretch)."""
    open_, top, stretch = board_key
    fb = Fretboard.__new__(Fretboard)
    fb.open, fb.top, fb.stretch, fb.capo, fb.frets = open_, top, stretch, 0, top
    fb.tuning_name = 'search'
    fb.tuning = open_
    c = Chord.parse(symbol)
    bass = c.bass_pc
    root = c.root
    out: dict[tuple, Shape] = {}
    if kind == 'power':
        min_s, max_s, low_strings = 2, 3, (0, 1, 2)
    elif kind == 'upper':
        min_s, max_s, low_strings = 3, 4, (1, 2, 3)
    elif kind == 'shell':
        min_s, max_s, low_strings = 3, 4, (0, 1)
    else:
        min_s, max_s, low_strings = 4, 6, (0, 1, 2)
    allow_open = kind in ('open', 'full', 'power', 'shell')
    for size in range(max_s, min_s - 1, -1):
        req, allowed = _required(c, kind, size)
        for s0 in low_strings:
            s1 = s0 + size - 1
            if s1 > 5:
                continue
            for lo in range(0, max(1, top - 2)):
                reach = fb.reach(max(lo, 1))
                window = range(max(1, lo), min(top, lo + reach) + 1)
                opts = []
                ok = True
                for s in range(6):
                    if s < s0 or s > s1:
                        opts.append([None])
                        continue
                    o = []
                    if allow_open and open_[s] % 12 in allowed:
                        o.append(0)
                    o += [f for f in window if (open_[s] + f) % 12 in allowed]
                    if kind == 'shell' and s0 < s < s1:
                        o.append(None)                 # a muted inner string (the 1-x-7-3 grips)
                    if not o:
                        ok = False
                        break
                    opts.append(o)
                if not ok:
                    continue
                _dfs(fb, c, kind, opts, req, bass, root, out)
    shapes = sorted(out.values(), key=lambda s: (s.cost, s.pos, tuple(-1 if f is None else f for f in s.frets)))
    return tuple(shapes)


def _dfs(fb, c, kind, opts, req, bass, root, out):
    frets = [None] * 6

    def rec(s):
        if s == 6:
            _consider(fb, c, kind, tuple(frets), req, bass, root, out)
            return
        for f in opts[s]:
            frets[s] = f
            rec(s + 1)
        frets[s] = None
    rec(0)


def _consider(fb, c, kind, frets, req, bass, root, out):
    ps = [None if f is None else fb.open[s] + f for s, f in enumerate(frets)]
    snd = [p for p in ps if p is not None]
    if len(snd) < 2 or frets in out:
        return
    pcs = {p % 12 for p in snd}
    if not req <= pcs:
        return
    low = snd[0]
    if kind in ('power', 'open', 'barre', 'full', 'shell') and low % 12 != bass:
        return
    if kind == 'power':
        if snd[1] - snd[0] != 7 or (len(snd) == 3 and snd[2] - snd[0] != 12):
            return
    if kind == 'shell':
        if snd[0] % 12 != c.root and snd[0] % 12 != bass:
            return
        if not 3 <= len(snd) <= 4:
            return
    if not fb.playable(frets):
        return
    fr = [f for f in frets if f]
    opens = sum(1 for f in frets if f == 0)
    if kind == 'barre' and opens:
        return
    pos = min(fr) if fr else 0
    span = (max(fr) - min(fr)) if fr else 0
    fingers = fb.fingers(frets)
    n = len(snd)
    cost = 0.0
    if kind in ('open', 'barre', 'full'):
        cost += (6 - n) * 0.35
        if frets[5] is None:
            cost += 0.3
    third = [p for p in snd if (p - c.root) % 12 in (3, 4)]
    if len(third) > 1:
        cost += 0.35 * (len(third) - 1)
    if (c.root + 7) % 12 not in pcs and 7 in c.intervals and kind not in ('shell',):
        cost += 0.25
    for a, b in zip(snd, snd[1:]):
        if b - a == 1:
            cost += 0.6
        if b - a == 0:
            return
    cost += span * 0.25
    barre = fingers < len(fr) and len(fr) >= 2
    if fingers >= 4 and not barre and opens:
        cost += 0.7                            # four single fingers around an open string: a stretch, not a grip
    if opens and fr and max(fr) > 5:
        cost += 1.2                            # open strings under a high shape: possible, rarely idiomatic
    if kind == 'open':
        cost += -0.35 * opens if pos <= 4 else 0.0
        cost += 0.6 if barre else 0.0
        cost += 0.12 * pos
    elif kind == 'full':
        cost += -0.2 * opens + 0.3 * barre + 0.07 * pos
    elif kind == 'barre':
        cost += 0.05 * abs(pos - 5)
    elif kind == 'power':
        cost += 0.08 * pos + (0.0 if frets[0] is not None or frets[1] is not None else 0.5) - 0.1 * (n == 3)
    elif kind == 'upper':
        cost += 0.05 * abs(pos - 7) + (0.0 if n == 3 else 0.2)
        if max(snd) < note('G4') - 12:
            cost += 0.5
    elif kind == 'shell':
        cost += 0.06 * abs(pos - 5)
    if fingers >= 4:
        cost += 0.25
    k = kind
    if kind in ('open', 'full'):
        k = 'open' if opens and pos <= 5 else ('barre' if barre and n >= 5 else kind)
    out[frets] = Shape(frets, tuple(ps), k, fingers, span, pos, round(cost, 4), c.symbol)


def shapes(chord, kind: str = 'open', *, fretboard=None, tuning='standard', capo: int = 0) -> list[Shape]:
    """All playable shapes of `chord` of a KINDS kind, the most idiomatic first (cost). 'open' also lists barre and
    movable shapes (after the open ones); an empty list when the chord has no shape of that kind."""
    if kind not in KINDS:
        raise ComposeError(f"shape kind must be one of {', '.join(KINDS)}, got {kind!r}")
    fb = _board(fretboard, tuning, capo)
    c = _chord(chord)
    res = list(_search(fb.key(), c.symbol, kind))
    if not res and kind in ('upper', 'shell', 'power', 'barre'):
        # fall back to a simpler chord (the triad / power chord of it)
        simple = _simplify(c, kind)
        if simple is not None and simple.symbol != c.symbol:
            res = list(_search(fb.key(), simple.symbol, kind))
    return res


def _simplify(c: Chord, kind: str) -> Chord | None:
    if kind == 'power':
        return None
    name = c.root_name + ('m' if c.is_minor else '') + (f"/{c.bass_name}" if c.bass_name and kind != 'upper' else '')
    try:
        return Chord.parse(name)
    except ComposeError:
        return None


def shape(chord, kind: str = 'open', *, fretboard=None, tuning='standard', capo: int = 0, near=None) -> Shape:
    """The best shape of `chord` (KINDS), or with near= a Shape (or fret position) the closest good one. A
    ComposeError when the chord has no playable shape of that kind."""
    res = shapes(chord, kind, fretboard=fretboard, tuning=tuning, capo=capo)
    if not res:
        raise ComposeError(f"no playable {kind} shape for {chord!r} on this fretboard")
    if near is None:
        return res[0]
    ref = near.pos if isinstance(near, Shape) else int(near)
    return min(res[:24], key=lambda s: s.cost + 0.35 * abs(s.pos - ref))


def _move_cost(a: Shape, b: Shape) -> float:
    """How hard the change from shape a to shape b is (and how far the voices jump)."""
    fa = [f for f in a.frets if f]
    fb = [f for f in b.frets if f]
    ca = sum(fa) / len(fa) if fa else 0.0
    cb = sum(fb) / len(fb) if fb else 0.0
    cost = 0.3 * abs(ca - cb)
    top_a, top_b = max(a.notes), max(b.notes)
    cost += 0.06 * abs(top_a - top_b)
    same = sum(1 for x, y in zip(a.frets, b.frets) if x is not None and x == y)
    cost -= 0.08 * same                                  # common fingers stay
    return cost


def voice_lead(chords, kind: str = 'open', *, fretboard=None, tuning='standard', capo: int = 0, start=None,
               candidates: int = 10) -> list[Shape]:
    """The smoothest playable path of shapes through `chords` (a list of chord symbols / Chords, or a Progression):
    each shape's own cost + the hand movement to the next (position shifts, top-note leaps; common fingers are
    cheap), solved over the whole list. start= a Shape to continue from."""
    fb = _board(fretboard, tuning, capo)
    if isinstance(chords, Progression):
        chords = [c for c in chords.chords if c is not None]
    cs = [_chord(c) for c in chords]
    if not cs:
        return []
    cands = []
    for c in cs:
        res = shapes(c, kind, fretboard=fb)
        if not res and kind != 'full':
            res = shapes(c, 'full', fretboard=fb)
        if not res:
            raise ComposeError(f"no playable shape for {c.symbol!r} ({kind}) on this fretboard")
        cands.append(res[:candidates])
    best = [[(s.cost + (_move_cost(start, s) if start is not None else 0.0), -1) for s in cands[0]]]
    for i in range(1, len(cs)):
        row = []
        for s in cands[i]:
            opts = [(best[i - 1][j][0] + _move_cost(p, s) + s.cost, j) for j, p in enumerate(cands[i - 1])]
            row.append(min(opts))
        best.append(row)
    j = min(range(len(best[-1])), key=lambda k: best[-1][k][0])
    path = []
    for i in range(len(cs) - 1, -1, -1):
        path.append(cands[i][j])
        j = best[i][j][1]
    return path[::-1]


def best_capo(prog, *, tuning='standard', max_capo: int = 7) -> int:
    """The capo fret (0..max_capo) that lets `prog` (a Progression / chord list) be played with the most open
    shapes (the singer-songwriter's trick: Bb Eb F with capo 1 = A D E shapes)."""
    if isinstance(prog, Progression):
        chords = [c for c in prog.chords if c is not None]
    else:
        chords = list(prog)
    best = (math.inf, 0)
    for k in range(0, int(max_capo) + 1):
        fb = Fretboard(tuning, k)
        tot = 0.0
        for c in chords:
            res = shapes(c, 'open', fretboard=fb)
            s = res[0] if res else None
            tot += 3.0 if s is None else (s.cost - 0.4 * s.open_strings + 0.15 * s.pos)
        if tot < best[0] - 1e-9:
            best = (tot, k)
    return best[1]


# ------------------------------------------------------------------------------------------------ articulations

_ART_WORDS = {
    'palm': ('palm', 'muted', 'mute'),
    'dead': ('dead', 'muted', 'mute', 'scratch'),
    'hammer': ('hammer', 'legato', 'slur'),
    'harmonic': ('harmonic', 'harm', 'flageolet'),
}


def _arts(sound=None, given=None) -> dict:
    """{role: articulation name} for palm / dead / hammer / harmonic from the sound's keyswitches (or given= a dict;
    a role mapped to None is emulated)."""
    out = {k: None for k in _ART_WORDS}
    if sound is not None:
        try:
            names = _art.available(sound)
        except ComposeError:
            names = []
        for role, words in _ART_WORDS.items():
            for w in words:
                hit = next((n for n in names if any(x == w or x.startswith(w) for x in _art._words(n))), None)
                if hit is not None:
                    out[role] = hit
                    break
    if given:
        for k, v in dict(given).items():
            if k not in out:
                raise ComposeError(f"articulations: unknown role {k!r}; use {', '.join(out)}")
            out[k] = v
    return out


def _is_mono(sound) -> bool:
    """A monophonic legato player (a sampler with mono='legato': overlapping notes slur)."""
    if sound is None:
        return False
    ins = getattr(sound, 'instrument', sound)
    params = getattr(ins, 'params', None)
    if params is None and isinstance(ins, dict):
        params = ins.get('params', {})
    return isinstance(params, dict) and params.get('mono') == 'legato'


def _is_sampler(sound) -> bool:
    ins = getattr(sound, 'instrument', sound)
    return getattr(ins, 'type', None) == 'sampler' or (isinstance(ins, dict) and ins.get('type') == 'sampler')


# ------------------------------------------------------------------------------------------------ the picking hand

class _Hand:
    """What the picking hand struck: one event per string hit; notes ring until the same string is struck again,
    the hand damps (a chuck, a stop) or the fretting hand leaves the shape (a chord change: fretted strings lift a
    little early), then become Notes."""

    def __init__(self, bpm: float, lift_ms: float = 18.0, gap_ms: float = 7.0, max_ring: float = 8.0):
        self.b = bpm
        self.ev: list[list] = []          # [t, string, pitch, vel, art, end|None, fretted]
        self.cuts: list[tuple[float, bool]] = []     # (time, only fretted strings)
        self.lift = _ms(lift_ms, bpm)
        self.gap = _ms(gap_ms, bpm)
        self.max_ring = max_ring

    def add(self, t, string, pitch, vel, art=None, end=None, fretted=True):
        self.ev.append([float(t), int(string), int(pitch), float(vel), art, end, bool(fretted)])

    def cut(self, t, fretted_only: bool = True, strings=None):
        """Stop strings at t: every string (fretted_only=False: a damp), the fretted ones (they lift lift_ms early),
        or strings= a set of string numbers (a chord change: the strings whose fret changes or that the new shape
        mutes - an open string stops where a finger lands on it, a string the new grip leaves out is damped)."""
        self.cuts.append((float(t), bool(fretted_only), None if strings is None else frozenset(strings)))

    def change(self, t, old: Shape, new: Shape):
        """A chord change at t from shape old to shape new: the strings that do not keep their fret stop."""
        self.cut(t, strings={s for s in range(6) if old.frets[s] != new.frets[s]})

    def notes(self, L: float | None = None) -> list[tuple]:
        by: dict[int, list] = {}
        for e in sorted(self.ev, key=lambda e: (e[0], e[1])):
            by.setdefault(e[1], []).append(e)
        cuts = sorted(self.cuts, key=lambda c: c[0])
        out = []
        for s, es in by.items():
            for i, (t, _, p, v, a, end, fr) in enumerate(es):
                if L is not None and t >= L - 1e-6:
                    continue
                e_ = t + self.max_ring if end is None else end
                if i + 1 < len(es):
                    e_ = min(e_, es[i + 1][0] - self.gap)
                for ct, only, ss in cuts:
                    if ct <= t + 0.02:
                        continue
                    if ss is not None:
                        if s in ss:
                            e_ = min(e_, ct - (self.lift if fr else 0.0))
                            break
                    elif fr or not only:
                        e_ = min(e_, ct - (self.lift if fr and only else 0.0))
                        break
                if L is not None:
                    e_ = min(e_, L)
                out.append((t, max(0.03, e_ - t), p, v, a))
        return out


_DOWN_PROFILE = (0.92, 0.97, 1.0, 1.0, 0.97, 0.93)
_UP_PROFILE = (1.0, 0.93, 0.86, 0.8, 0.76, 0.72)


def _select(sh: Shape, which) -> list[int]:
    """The strings of a shape a stroke hits: 'all', 'top2'..'top5', 'low2'..'low4', 'mid' (the middle 3-4) or a list
    of string numbers."""
    ss = sh.strings
    if which in (None, 'all'):
        return ss
    if isinstance(which, (list, tuple)):
        return [s for s in which if s in ss]
    if isinstance(which, str) and which.startswith('top') and which[3:].isdigit():
        return ss[-int(which[3:]):]
    if isinstance(which, str) and which.startswith('low') and which[3:].isdigit():
        return ss[:int(which[3:])]
    if which == 'mid':
        return ss[1:-1] if len(ss) >= 4 else ss
    raise ComposeError(f"stroke strings must be 'all', 'topN', 'lowN', 'mid' or a list, got {which!r}")


def _restrict(sh: Shape, which) -> Shape:
    """The shape with only the strings `which` (as _select) sounding - the others muted."""
    keep = set(_select(sh, which))
    return sh._replace(frets=tuple(f if i in keep else None for i, f in enumerate(sh.frets)),
                       pitches=tuple(p if i in keep else None for i, p in enumerate(sh.pitches)))


def _stroke(hand: _Hand, sh: Shape, t: float, *, up: bool = False, which='all', vel: float = 90.0,
            spread_ms: float = 24.0, rng: random.Random | None = None, art=None, end=None, onset: float = 0.3,
            profile=None) -> list[float]:
    """One pick stroke across the strings `which` of shape `sh`: a downstroke low -> high, an upstroke high -> low,
    spread over spread_ms for six strings (fewer strings: proportionally less), the stroke centred a little after its
    start (onset: the share of the spread before the beat); per-string velocity from the stroke's profile (a down
    digs into the middle strings, an up rings the top string), a little jitter. Returns the string onsets."""
    rng = rng or random.Random(0)
    ss = _select(sh, which)
    if not ss:
        return []
    order = ss[::-1] if up else ss
    total = _ms(spread_ms, hand.b) * (len(order) - 1) / 5.0
    step = total / max(1, len(order) - 1)
    t0 = max(0.0, t - onset * total)
    prof = profile or (_UP_PROFILE if up else _DOWN_PROFILE)
    times = []
    for i, s in enumerate(order):
        ti = t0 + i * step * (1.0 + 0.2 * _tri(rng)) if i else t0
        k = i if up else int(round(i * 5 / max(1, len(order) - 1)))
        f = prof[min(k, len(prof) - 1)]
        hand.add(ti, s, sh.pitches[s], vel * f * (1.0 + 0.035 * _tri(rng)), art,
                 None if end is None else max(ti + 0.03, end), sh.frets[s] != 0)
        times.append(ti)
    return times


# ------------------------------------------------------------------------------------------------ patterns

PATTERNS = {
    # strums (8ths: downs on the beat, ups on the &; 16ths: downs on the even 16ths)
    'pop': ('1/8', 'D . d U . u D u'),              # "old faithful": 1, 2 &, & 3, 4 &
    'pop_push': ('1/8', 'D . d U . U d U'),
    'folk': ('1/8', 'D . D u . u D u'),
    'folk16': ('1/16', 'D . d . D . d u . u d . D . d u'),
    'eighths': ('1/8', 'D u d u D u d u'),
    'downs': ('1/8', 'D d d d D d d d'),
    'ballad': ('1/8', 'D . . u . u D u'),
    'ballad16': ('1/16', 'D . . . d . . u . u . . d . . u'),
    'half': ('1/8', 'D . . . D . d u'),
    'whole': ('1/1', 'D'),
    'anthem': ('1/8', 'D . D . D . D u'),
    'rock16': ('1/16', 'D . d u . u d u D . d u . u d u'),
    'build16': ('1/16', 'd u d u d u d u d u d u D u D u'),
    # palm-muted chugs / power chords
    'chug': ('1/8', 'P p p p P p p p'),
    'chug_push': ('1/8', 'P p p p P p D .'),
    'gallop': ('1/16', 'P . p p P . p p P . p p P . p p'),
    'power': ('1/8', 'D . . . D . D .'),
    'power_drive': ('1/8', 'D d d d D d d d'),
    'stabs': ('1/8', 'D . . D . . D .'),
    # funk / reggae / jazz / country
    'funk': ('1/16', 'D x x U X x D u x U x x X x d U'),
    'funk_sparse': ('1/16', 'D x x x X x x U x x D x X x x x'),
    'skank': ('1/16', '. . . . D . . . . . . . D . . .'),
    'bubble': ('1/16', '. . . . D u . . . . . . D u . .'),
    'four': ('1/4', 'd D d D'),
    'boom_chick': ('1/8', 'B . d u A . d u'),
    # picking (B bass, A alternate bass, 1-4 strings from the top, + = pinched together)
    'arp_ballad': ('1/8', 'B 3 2 3 1 3 2 3'),
    'arp_up': ('1/8', 'B 3 2 1 A 3 2 1'),
    'arp_pima': ('1/8', 'B 3 2 1 2 3 2 3'),
    'arp16': ('1/16', 'B 3 2 1 2 3 2 1 A 3 2 1 2 3 2 1'),
    'jangle': ('1/8', 'B 2 1 2 A 2 1 2'),
    'travis': ('1/8', 'B+1 3 A 2 B 3 A 2'),
    'travis_pinch': ('1/8', 'B+1 3 A 2 B+1 3 A 2'),
    'let_ring': ('1/8', 'B 4 3 2 1 . . .'),
}
"""Named patterns: (grid, tokens). Tokens per step: D / d down strum (accent / normal), U / u up strum, X / x a dead
(muted) strum, P / p a palm-muted downstroke, B bass string, A the alternate bass, 1-4 a single string counted from
the top sounding string, joined with + (B+1: a pinch), o a ghost up on the top strings, . or - nothing (the strings
ring). A pattern repeats; its length is len(tokens) x grid. Any token string works as pattern= (grid= its
resolution, default 1/8)."""

_TOKENS = set('DdUuXxPpBAo1234.-')


def _pattern(pattern, grid=None) -> tuple[float, list[str]]:
    if isinstance(pattern, tuple) and len(pattern) == 2:
        g, toks = pattern
    elif isinstance(pattern, str) and pattern in PATTERNS:
        g, toks = PATTERNS[pattern]
    elif isinstance(pattern, str):
        g, toks = ('1/8' if grid is None else grid), pattern
    else:
        raise ComposeError(f"pattern must be a PATTERNS name, a token string or (grid, tokens), got {pattern!r}")
    ts = [x for x in str(toks).replace('|', ' ').split() if x]
    if not ts:
        raise ComposeError(f"pattern {pattern!r} has no steps")
    for x in ts:
        for part in x.split('+'):
            if len(part) != 1 or part not in _TOKENS:
                raise ComposeError(f"pattern {pattern!r}: unknown step {x!r}; tokens: D d U u X x P p B A o 1-4 . - "
                                   f"(joined with +)")
    return beats(g), ts


_MIN_GAP_S = {'strum': 0.095, 'palm': 0.075, 'pick': 0.07}
"""The picking hand's speed limit: the shortest time between two played steps of a pattern - a strummed chord (the
whole arm, down-up) ~10.5 strokes / s, a palm-muted chug ~13 / s, a single picked string ~14 / s. A 16th pattern
faster than that (e.g. 16th strums above ~158 BPM) is played on the 8th grid instead."""


def _too_fast(g: float, toks: list[str], bpm: float) -> bool:
    """True when a pattern (grid g beats, tokens) needs a faster hand than _MIN_GAP_S at bpm."""
    step_s = g * 60.0 / bpm
    played = [i for i, x in enumerate(toks) if x not in ('.', '-')]
    if len(played) < 2:
        return False
    n = len(toks)
    for a, b_ in zip(played, played[1:] + [played[0] + n]):
        x = toks[a]
        kind = 'strum' if set(x) & set('DdUuXx') else 'palm' if set(x) & set('Pp') else 'pick'
        if (b_ - a) * step_s < _MIN_GAP_S[kind] - 1e-9:
            return True
    return False


def _halve(g: float, toks: list[str]) -> tuple[float, list[str]]:
    """A pattern on the grid twice as coarse (16ths -> 8ths): every second step, the off-beat strums turned into
    up-strokes (the hand keeps its down-up pendulum)."""
    out = []
    for j, x in enumerate(toks[::2]):
        if j % 2 == 1 and len(toks) % 2 == 0:
            x = x.replace('D', 'U').replace('d', 'u')
        out.append(x)
    return 2 * g, out


def _fit_tempo(g: float, toks: list[str], bpm: float) -> tuple[float, list[str], bool]:
    """(grid, tokens, changed): the pattern coarsened until the hand can play it at bpm."""
    changed = False
    while _too_fast(g, toks, bpm) and len(toks) >= 2 and len(toks) % 2 == 0:
        g, toks = _halve(g, toks)
        changed = True
    return g, toks, changed


# ------------------------------------------------------------------------------------------------ the rhythm engine

class _Ctx:
    """How the picking hand plays (the technique's settings) while the engine walks a pattern over a progression."""

    def __init__(self, bpm, rng, arts, *, spread=(16, 30), up_strings='top4', down_strings='all', gate=None,
                 timing_ms=5.0, late_ms=0.0, onset=0.3, palm_len=0.16, dead_len=0.045, swing=None):
        self.b, self.rng, self.arts = bpm, rng, arts
        self.spread, self.up_strings, self.down_strings = spread, up_strings, down_strings
        self.gate, self.timing_ms, self.late_ms, self.onset = gate, timing_ms, late_ms, onset
        self.palm_len, self.dead_len, self.swing = palm_len, dead_len, swing


def _alt_bass(sh: Shape) -> int | None:
    ss = sh.strings
    if len(ss) < 2:
        return None
    b = ss[0]
    for s in ss[1:3]:
        if (sh.pitches[s] - sh.pitches[b]) % 12 in (7, 0, 3, 4):
            return s
    return ss[1]


def _swung(t: float, grid: float, swing) -> float:
    """Swing the off-beat steps of the grid (swing = the long note's share of a pair: 0.5 straight .. 0.67)."""
    if not swing:
        return t
    pair = 2 * grid
    k = t / pair
    frac = k - math.floor(k)
    if abs(frac - 0.5) < 1e-6:
        return math.floor(k) * pair + swing * pair
    return t


def _token(hand, ctx, tok, sh, tt, t, vel_at, grid):
    rng = ctx.rng
    b = ctx.b
    gate_end = None if ctx.gate is None else tt + _sec(ctx.gate, b)
    acc = tok.isupper() and tok not in 'BA'
    if tok in '.-':
        return
    if tok in 'Dd':
        w = 1.0 if acc else 0.56
        _stroke(hand, sh, tt, up=False, which=ctx.down_strings, vel=vel_at(t, w),
                spread_ms=rng.uniform(*ctx.spread) * (0.85 if acc else 1.0), rng=rng, end=gate_end, onset=ctx.onset)
    elif tok in 'Uu':
        w = 0.8 if acc else 0.4
        _stroke(hand, sh, tt + _ms(2.0, b), up=True, which=ctx.up_strings, vel=vel_at(t, w),
                spread_ms=rng.uniform(*ctx.spread) * 0.7, rng=rng, end=gate_end, onset=ctx.onset * 0.6)
    elif tok == 'o':
        _stroke(hand, sh, tt + _ms(2.0, b), up=True, which='top2', vel=vel_at(t, 0.22),
                spread_ms=ctx.spread[0] * 0.6, rng=rng, end=tt + _sec(0.06, b), onset=0.2)
    elif tok in 'Xx':
        hand.cut(tt - _ms(1.0, b), fretted_only=False)
        w = 0.75 if tok == 'X' else 0.34
        dead = ctx.arts.get('dead')
        up = (round(t / grid) % 2 == 1)
        _stroke(hand, sh, tt, up=up, which='mid' if len(sh.strings) >= 4 else 'all', vel=vel_at(t, w),
                spread_ms=ctx.spread[0] * 0.6, rng=rng, art=dead,
                end=tt + _sec(ctx.dead_len if dead is None else 0.12, b), onset=0.2)
    elif tok in 'Pp':
        palm = ctx.arts.get('palm')
        w = 1.0 if tok == 'P' else 0.52
        allowed = _select(sh, ctx.down_strings)       # strings='top4': the palm mutes stay off the bass strings too
        which = allowed if len(allowed) <= 3 else allowed[:3]
        _stroke(hand, sh, tt, up=False, which=which, vel=vel_at(t, w), spread_ms=ctx.spread[0] * 0.5, rng=rng,
                art=palm, end=tt + _sec(ctx.palm_len * (1.4 if palm else 1.0), b), onset=0.2)
    elif tok in 'BA':
        s = sh.strings[0] if tok == 'B' else _alt_bass(sh)
        if s is None:
            return
        w = 0.9 if abs(t - round(t)) < 1e-6 and int(round(t)) % 2 == 0 else 0.78
        hand.add(tt, s, sh.pitches[s], vel_at(t, w) * (1.0 + 0.03 * _tri(rng)), None, gate_end, sh.frets[s] != 0)
    elif tok in '1234':
        ss = sh.strings
        k = min(int(tok), len(ss) - 1)
        if k < 1:
            return
        s = ss[-k]
        w = 0.62 if k == 1 else 0.52
        hand.add(tt, s, sh.pitches[s], vel_at(t, w) * (1.0 + 0.05 * _tri(rng)), None, gate_end, sh.frets[s] != 0)


# ------------------------------------------------------------------------------------------------ rhythm parts

def _as_shape(x, kind: str = 'open', fretboard=None) -> Shape:
    if isinstance(x, Shape):
        return x
    return shape(x, kind, fretboard=fretboard)


def _dyn(lo: float, hi: float, bpb: float, rng: random.Random, *, backbeat: float = 1.02, arc: float = 0.08,
         phrase_bars: int = 4, ramp=None, L: float = 0.0):
    """The rhythm hand's dynamics: vel_at(t, weight) = lo + (hi - lo) x weight, the one a little heavier, the backbeat
    (beats 2 and 4) x backbeat, a gentle arc over each phrase of phrase_bars bars (+-arc/2) and, with ramp=(from, to)
    beats, a crescendo over that span (a build into the next section); a few % of stroke-to-stroke jitter."""
    span = hi - lo

    def vel_at(t, w):
        bar = int(math.floor(t / bpb + _EPS))
        pos = t - bar * bpb
        v = lo + span * w
        if pos < 1e-6:
            v *= 1.04
        elif abs(pos - round(pos)) < 1e-6 and int(round(pos)) % 2 == 1:
            v *= backbeat
        ph = ((bar % phrase_bars) + pos / bpb) / phrase_bars
        v *= 1.0 - arc / 2.0 + arc * math.sin(math.pi * ph)
        if ramp is not None and ramp[0] <= t < ramp[1]:
            x = (t - ramp[0]) / max(_EPS, ramp[1] - ramp[0])
            v *= 0.8 + 0.35 * x
        return min(127.0, max(1.0, v * (1.0 + 0.04 * _tri(rng))))
    return vel_at


def _segs(p: Progression, L: float) -> list[tuple[float, float, Chord]]:
    """(start, end, chord) over L beats (the progression looped), no-chord segments left out."""
    out = []
    t = 0.0
    if p.length <= 0:
        return out
    while t < L - _EPS:
        for s, d, c in p:
            a, e = t + s, min(L, t + s + d)
            if a >= L - _EPS:
                break
            if c is not None:
                if out and out[-1][2] is c and abs(out[-1][1] - a) < _EPS:
                    out[-1] = (out[-1][0], e, c)
                else:
                    out.append((a, e, c))
        t += p.length
    return out


def _rhythm(prog, bpm, *, pattern, grid=None, kind='open', vel=(62, 100), spread=(16, 30), up_strings='top4',
            down_strings='all', gate=None, swing=None, anticipate: float = 0.0, open_change: float = 0.0,
            timing_ms: float = 5.0, late_ms: float = 0.0, sound=None, articulations=None, fretboard=None, seed=0,
            take=None, length=None, start_shape=None, dyn=None, key=None, lift_ms: float = 18.0) -> dict:
    """The shared rhythm engine: shapes voice-led over the progression, the pattern played across it, chord changes
    lifted (fretted strings stop lift_ms early), anticipations (a stroke an 8th before a change takes the new
    chord), the open-string change stroke. Returns {'notes': [...], 'shapes': [(start, shape)], 'pushes': [...],
    'hand': _Hand}."""
    b = _bpm(bpm)
    fb = fretboard if isinstance(fretboard, Fretboard) else _board(fretboard)
    p = _as_prog(prog, key, 4.0 if length is None else length)
    L = float(length) if length is not None else p.length
    bpb = p.beats_per_bar
    g, toks = _pattern(pattern, grid)
    lo, hi = _vels(vel)
    rng = random.Random(seed_int(seed))
    nrng = random.Random(f"{seed_int(seed)}:{take}") if take is not None else rng   # a second take: new noise
    arts = _arts(sound, articulations)
    segs = _segs(p, L)
    if not segs:
        return {'notes': [], 'shapes': [], 'pushes': [], 'hand': _Hand(b)}
    path = voice_lead([c for _, _, c in segs], kind, fretboard=fb, start=start_shape)
    # anticipations: a stroke an 8th (or a 16th) before a change plays the new chord
    bounds = [a for a, _, _ in segs]
    pushes = []

    def tok_at(t):
        i = int(round(t / g))
        if abs(i * g - t) > 1e-6:
            return '.'
        return toks[i % len(toks)]
    for i in range(1, len(segs)):
        c = bounds[i]
        for back in (0.5, 0.25):
            t = c - back
            if t > segs[i - 1][0] + 0.5 and tok_at(t) not in '.-' and not set(tok_at(t)) & set('BA1234'):
                if rng.random() < anticipate:
                    bounds[i] = t
                    pushes.append((t, c))
                break
    ctx = _Ctx(b, nrng, arts, spread=spread, up_strings=up_strings, down_strings=down_strings, gate=gate,
               timing_ms=timing_ms, late_ms=late_ms, swing=swing)
    hand = _Hand(b, lift_ms=lift_ms)
    for i in range(1, len(bounds)):
        if path[i] != path[i - 1]:
            hand.change(bounds[i], path[i - 1], path[i])

    def shape_at(t):
        j = 0
        for k, a in enumerate(bounds):
            if a <= t + 1e-6:
                j = k
        return path[j]
    changes = set(round(x, 6) for x in bounds[1:])
    oc_used = [-99.0]

    def on_step(t, tok):
        # the open-string stroke: the last up-stroke before a change, the fretting hand already on its way
        if open_change and tok in ('u',) and round(t + g, 6) in changes and t - oc_used[0] >= 2 * bpb \
                and rng.random() < open_change:
            oc_used[0] = t
            return '~'
        return None
    vel_at = dyn or _dyn(lo, hi, bpb, nrng)

    def token(hand_, ctx_, part, sh, tt, t, vat, grid_):
        if part == '~':
            opens = tuple(fb.open[s] if s in sh.strings[-3:] else None for s in range(6))
            osh = Shape(tuple(0 if q is not None else None for q in opens), opens, 'open', 0, 0, 0, 0.0, 'open')
            _stroke(hand_, osh, tt + _ms(2.0, b), up=True, which='all', vel=vat(t, 0.3) * 0.72,
                    spread_ms=ctx_.spread[0] * 0.7, rng=ctx_.rng, onset=0.2, end=tt + _sec(0.12, b))
            return
        _token(hand_, ctx_, part, sh, tt, t, vat, grid_)
    _play_steps_x(hand, ctx, toks, g, 0.0, L, shape_at, vel_at, on_step, token)
    shapes_log = [(bounds[i], path[i]) for i in range(len(path))]
    return {'notes': hand.notes(L), 'shapes': shapes_log, 'pushes': pushes, 'hand': hand, 'L': L,
            'oc': oc_used[0] > -99.0}


def _play_steps_x(hand, ctx, toks, g, t0, t1, shape_at, vel_at, on_step, token):
    n = len(toks)
    i = int(math.floor(t0 / g + _EPS))
    rng = ctx.rng
    while True:
        t = i * g
        if t >= t1 - _EPS:
            break
        tok = toks[i % n]
        tok = on_step(t, tok) or tok
        tt = max(0.0, _swung(t, g, ctx.swing) + _ms(ctx.timing_ms, ctx.b) * _tri(rng) + _ms(ctx.late_ms, ctx.b))
        sh = shape_at(t)
        if sh is not None:
            for part in tok.split('+'):
                token(hand, ctx, part, sh, tt, t, vel_at, g)
        i += 1


def strum(chord, dur, bpm, *, direction: str = 'down', strings='all', spread_ms: float = 24.0, vel=90,
          kind: str = 'open', fretboard=None, art=None, seed=0, at=0.0) -> Clip:
    """One pick stroke held for `dur` beats: `chord` (a symbol or a Shape) strummed 'down' (low -> high) or 'up'
    (high -> low, lighter), over spread_ms for six strings (15-35 ms: slower = softer / bigger, faster = tighter),
    the strings = 'all', 'topN', 'lowN', 'mid' or a list; per-string velocities (a down digs into the middle strings,
    an up rings the top string). art= an articulation mark on every note."""
    b = _bpm(bpm)
    sh = _as_shape(chord, kind, fretboard)
    if direction not in ('down', 'up'):
        raise ComposeError(f"strum direction must be 'down' or 'up', got {direction!r}")
    D = _num(dur, 'strum dur', 0.05)
    a = _pos(at)
    hand = _Hand(b)
    _stroke(hand, sh, 0.0, up=direction == 'up', which=strings, vel=_vels(vel)[0],
            spread_ms=_num(spread_ms, 'strum spread_ms', 0, 200), rng=random.Random(seed_int(seed)), art=art,
            end=D, onset=0.0)
    return _clip([(s + a, d, q, v, ar) for s, d, q, v, ar in hand.notes(D)], a + D)


def chuck(chord, bpm, *, vel=78, strings='mid', dead=None, sound=None, kind: str = 'open', fretboard=None, seed=0,
          at=0.0) -> Clip:
    """A dead strum (chuck / scratch): the strings `strings` struck while the fretting hand damps them - the
    percussive 'chk' of pop and funk strumming. dead= the guitar's dead-note articulation (default: found on sound=,
    else emulated as a 45 ms tick)."""
    b = _bpm(bpm)
    sh = _as_shape(chord, kind, fretboard)
    d = dead if dead is not None else _arts(sound).get('dead')
    a = _pos(at)
    hand = _Hand(b)
    _stroke(hand, sh, 0.0, which=strings, vel=_vels(vel)[0], spread_ms=10.0, rng=random.Random(seed_int(seed)),
            art=d, end=_sec(0.045 if d is None else 0.12, b), onset=0.0)
    return _clip([(s + a, dd, q, v, ar) for s, dd, q, v, ar in hand.notes()], a + 0.25)


def strum_pattern(prog, bpm, *, pattern='pop', grid=None, kind: str = 'open', vel=(62, 100), spread=(16, 30),
                  swing=None, anticipate: float = 0.25, sound=None, articulations=None, fretboard=None, seed=0,
                  length=None, at=0.0) -> Clip:
    """A strummed part over `prog` (a Progression / chord string; length= beats loops it): shapes voice-led (kind),
    `pattern` (PATTERNS name or tokens) with downs low -> high and ups high -> low on the top four strings, chord
    changes lifted a little early, an 8th-note anticipation of a change now and then (anticipate), velocities
    vel=(lo, hi) shaped (accents, the one, a phrase arc), a few ms of human timing (seeded)."""
    r = _rhythm(prog, bpm, pattern=pattern, grid=grid, kind=kind, vel=vel, spread=spread, swing=swing,
                anticipate=anticipate, sound=sound, articulations=articulations, fretboard=fretboard, seed=seed,
                length=length)
    a = _pos(at)
    return _clip([(s + a, d, q, v, ar) for s, d, q, v, ar in r['notes']], a + r.get('L', 0.0))


def arpeggio(prog, bpm, *, pattern='arp_ballad', grid=None, kind: str = 'open', vel=(52, 90), sound=None,
             fretboard=None, seed=0, length=None, at=0.0) -> Clip:
    """A picked arpeggio over `prog`: the pattern's B (the bass string), A (the alternate bass), 1-4 (strings from
    the top) on the grid, every string ringing until it is picked again or the chord changes (let ring) - ballad
    arpeggios, p-i-m-a, jangle; the bass on the beat heavier, the fingers lighter."""
    r = _rhythm(prog, bpm, pattern=pattern, grid=grid, kind=kind, vel=vel, sound=sound, fretboard=fretboard,
                seed=seed, length=length, timing_ms=6.0, lift_ms=10.0)
    a = _pos(at)
    return _clip([(s + a, d, q, v, ar) for s, d, q, v, ar in r['notes']], a + r.get('L', 0.0))


def travis(prog, bpm, *, pattern='travis', **kw) -> Clip:
    """Travis picking (the folk / country fingerstyle): the thumb alternates the bass (B on 1 and 3, A on 2 and 4)
    while the fingers pick the treble strings on the off-beats, pinched with the bass on the one - arpeggio(pattern=
    'travis')."""
    return arpeggio(prog, bpm, pattern=pattern, **kw)


def chug(prog, bpm, *, pattern='chug', grid=None, kind: str = 'power', vel=(78, 112), sound=None, articulations=None,
         fretboard=None, seed=0, length=None, at=0.0) -> Clip:
    """Palm-muted power-chord chugs (rock verse, metal): all downstrokes on the power shape, P / p palm-muted (the
    guitar's 'palm mute' articulation from sound=, else short notes), D / d open accents that ring; tight 5-9 ms
    strokes."""
    r = _rhythm(prog, bpm, pattern=pattern, grid=grid, kind=kind, vel=vel, spread=(8, 14), sound=sound,
                articulations=articulations, fretboard=fretboard, seed=seed, length=length, timing_ms=4.0)
    a = _pos(at)
    return _clip([(s + a, d, q, v, ar) for s, d, q, v, ar in r['notes']], a + r.get('L', 0.0))


def skank(prog, bpm, *, pattern='skank', grid=None, kind: str = 'upper', vel=(70, 100), gate: float = 0.11,
          fretboard=None, seed=0, length=None, at=0.0) -> Clip:
    """The reggae skank: short, tight down-stroke chops of a high triad on the backbeat (beats 2 and 4: 'skank', or
    'bubble' with a down-up double chop), the fretting hand releasing after `gate` seconds; laid back a few ms."""
    r = _rhythm(prog, bpm, pattern=pattern, grid=grid, kind=kind, vel=vel, spread=(8, 14), gate=gate,
                up_strings='all', fretboard=fretboard, seed=seed, length=length, late_ms=8.0, timing_ms=3.0)
    a = _pos(at)
    return _clip([(s + a, d, q, v, ar) for s, d, q, v, ar in r['notes']], a + r.get('L', 0.0))


def scratch(prog, bpm, *, pattern='funk', grid=None, kind: str = 'upper', vel=(56, 108), gate: float = 0.09,
            sound=None, articulations=None, fretboard=None, seed=0, length=None, at=0.0) -> Clip:
    """Funk 16th scratch: the hand never stops (downs on the even 16ths, ups on the odd), most strokes dead (X / x:
    the guitar's dead-note scratches from sound=, else short ticks), a few short chord stabs of a high 3-4 string grip
    (D / U), the backbeat scratch accented."""
    r = _rhythm(prog, bpm, pattern=pattern, grid=grid, kind=kind, vel=vel, spread=(6, 12), gate=gate,
                up_strings='all', sound=sound, articulations=articulations, fretboard=fretboard, seed=seed,
                length=length, timing_ms=3.0)
    a = _pos(at)
    return _clip([(s + a, d, q, v, ar) for s, d, q, v, ar in r['notes']], a + r.get('L', 0.0))


def let_ring(chord, dur, bpm, *, ms: float = 70.0, direction: str = 'down', kind: str = 'open', vel=84,
             fretboard=None, seed=0, at=0.0) -> Clip:
    """A chord strummed slowly (a 50-120 ms roll across the strings) and left ringing for `dur` - intro, outro, the
    final chord; the top string sings."""
    sh = _as_shape(chord, kind, fretboard)
    return strum(sh, dur, bpm, direction=direction, spread_ms=ms, vel=vel, seed=seed, at=at)


def _grace_string(sh: Shape, sus: int, fb: Fretboard):
    """For hammer_chord: the string carrying the chord's 3rd (highest first) and the fret it starts from."""
    c = Chord.parse(sh.chord) if sh.chord else None
    for s in reversed(sh.strings):
        f = sh.frets[s]
        p = sh.pitches[s]
        if c is not None and (p - c.root) % 12 not in (3, 4):
            continue
        if sus == 2:
            for d in (2, 1):
                if f - d >= 0 and (f - d == 0 or f - d >= max(1, sh.pos - 1)):
                    return s, f - d, f
        else:
            up = 1 if (p - c.root) % 12 == 4 else 2
            if f + up <= sh.pos + fb.reach(max(1, sh.pos)):
                return s, f + up, f
    return None


def hammer_chord(chord, dur, bpm, *, sus: int = 2, delay: float = 0.5, kind: str = 'open', vel=88,
                 spread_ms: float = 22.0, sound=None, articulations=None, fretboard=None, seed=0, at=0.0) -> Clip:
    """The singer-songwriter's chord ornament: the chord strummed with its 3rd held back - a step lower (sus=2:
    Dsus2 -> D, C with the open D string -> E, the finger hammered on after `delay` beats) or a 4th above it
    (sus=4: Dsus4 -> D, the finger pulled off). The hammered / pulled note is softer and carries the guitar's
    'hammer-on' articulation when it has one."""
    b = _bpm(bpm)
    fb = fretboard if isinstance(fretboard, Fretboard) else _board(fretboard)
    sh = _as_shape(chord, kind, fb)
    D = _num(dur, 'hammer_chord dur', 0.25)
    dl = _num(delay, 'hammer_chord delay', 0.05, D)
    if sus not in (2, 4):
        raise ComposeError(f"hammer_chord sus must be 2 or 4, got {sus!r}")
    g = _grace_string(sh, sus, fb)
    a = _pos(at)
    rng = random.Random(seed_int(seed))
    v0 = _vels(vel)[0]
    if g is None:
        return strum(sh, D, b, spread_ms=spread_ms, vel=v0, seed=seed, at=at)
    s, f0, f1 = g
    frets = list(sh.frets)
    frets[s] = f0
    pitches = list(sh.pitches)
    pitches[s] = fb.open[s] + f0
    pre = sh._replace(frets=tuple(frets), pitches=tuple(pitches))
    hand = _Hand(b)
    _stroke(hand, pre, 0.0, vel=v0, spread_ms=spread_ms, rng=rng, end=D, onset=0.0)
    hand.add(dl, s, sh.pitches[s], v0 * 0.72, _arts(sound, articulations).get('hammer'), D, f1 != 0)
    return _clip([(x + a, d, q, v, ar) for x, d, q, v, ar in hand.notes(D)], a + D)


def slide_chord(chord, dur, bpm, *, frm: int = -2, ms: float = 110.0, kind: str = 'power', vel=96,
                spread_ms: float = 10.0, fretboard=None, seed=0, at=0.0) -> Clip:
    """A chord slid into: the shape struck `frm` frets away (-2: from below) and slid to its place over `ms` (the
    frets passed lightly, the arrival without a new pick attack: softer), then held - the rock / funk slide into a
    power chord or a high grip. Movable shapes only (open strings would not slide)."""
    b = _bpm(bpm)
    fb = fretboard if isinstance(fretboard, Fretboard) else _board(fretboard)
    sh = _as_shape(chord, kind, fb)
    if sh.open_strings:
        movable = [x for x in shapes(sh.chord, kind if kind != 'open' else 'barre', fretboard=fb) if not x.open_strings]
        if not movable:
            return strum(sh, dur, bpm, spread_ms=spread_ms, vel=vel, seed=seed, at=at)
        sh = movable[0]
    k = int(frm)
    if k == 0 or abs(k) > 5:
        raise ComposeError(f"slide_chord frm must be -5..-1 or 1..5 frets, got {frm!r}")
    if sh.pos + k < 1:
        k = -(sh.pos - 1) if sh.pos > 1 else abs(k)
    D = _num(dur, 'slide_chord dur', 0.1)
    a = _pos(at)
    v0 = _vels(vel)[0]
    rng = random.Random(seed_int(seed))
    total = _ms(_num(ms, 'slide_chord ms', 20, 600), b)
    steps = abs(k)
    hand = _Hand(b, gap_ms=1.0)
    for i in range(steps + 1):
        off = k + (i if k < 0 else -i)
        t = total * i / steps
        frets = tuple(None if f is None else f + off for f in sh.frets)
        ps = tuple(None if q is None else q + off for q in sh.pitches)
        cur = sh._replace(frets=frets, pitches=ps)
        v = v0 if i == 0 else v0 * (0.42 if i < steps else 0.74)
        end = D if i == steps else t + total / steps + _ms(4, b)
        _stroke(hand, cur, t, vel=v, spread_ms=spread_ms if i == 0 else 3.0, rng=rng, end=end, onset=0.0)
    return _clip([(x + a, d, q, v, ar) for x, d, q, v, ar in hand.notes(D)], a + D)


def bass_run(frm, to, dur, bpm, *, key=None, notes: int = 3, vel=84, low='E2', high='E3', seed=0, at=0.0) -> Clip:
    """A bass-string walk into the next chord (the folk / country 'G - A - B -> C'): `notes` scale steps (the key,
    else the chord scale of `frm`) from the bass note of `frm` toward the bass note of `to` (which the next bar
    plays), evenly over `dur`, played on the low strings (low..high), the last note leaning into the change."""
    b = _bpm(bpm)
    c0, c1 = _chord(frm), _chord(to)
    D = _num(dur, 'bass_run dur', 0.25)
    a = _pos(at)
    lo_, hi_ = note(low), note(high)
    start = lo_ + (c0.bass_pc - lo_) % 12
    tgt = lo_ + (c1.bass_pc - lo_) % 12
    if abs(tgt - start) > 6:
        tgt = tgt - 12 if tgt > start else tgt + 12
    pcs = _scale_pcs(key=key) if key is not None else _scale_pcs(c0) | _scale_pcs(c1)
    n = max(1, int(notes))
    d = 1 if tgt >= start else -1
    line = []
    q = tgt
    for _ in range(n):
        q = _step(q, pcs, -d)
        line.append(q)
    line = line[::-1]
    if tgt == start:
        line = [start + (2 if (start + 2) % 12 in pcs else 1) * x for x in (0, 1)][:n]
    rng = random.Random(seed_int(seed))
    v0 = _vels(vel)[0]
    step = D / len(line)
    out = []
    for i, p in enumerate(line):
        while p < lo_:
            p += 12
        while p > hi_ + 5:
            p -= 12
        t = i * step + (_ms(5.0, b) * _tri(rng) if i else 0.0)
        out.append((a + max(0.0, t), step * 0.95, p, v0 * (0.88 + 0.12 * (i + 1) / len(line))))
    return _clip(out, a + D)


def choke(chord, bpm, *, hold: float = 0.5, vel=104, kind: str = 'open', spread_ms: float = 16.0, dead=None,
          sound=None, fretboard=None, seed=0, at=0.0) -> Clip:
    """A stop: the chord hit hard and choked after `hold` beats (both hands damp: a dead scratch where the notes
    stop) - the break before a chorus or the band's hit."""
    b = _bpm(bpm)
    sh = _as_shape(chord, kind, fretboard)
    h = _num(hold, 'choke hold', 0.1, 8)
    a = _pos(at)
    rng = random.Random(seed_int(seed))
    hand = _Hand(b)
    v0 = _vels(vel)[0]
    _stroke(hand, sh, 0.0, vel=v0, spread_ms=spread_ms, rng=rng, end=h, onset=0.0)
    d = dead if dead is not None else _arts(sound).get('dead')
    _stroke(hand, sh, h, which='mid', vel=v0 * 0.45, spread_ms=6.0, rng=rng, art=d,
            end=h + _sec(0.04 if d is None else 0.1, b), onset=0.0)
    return _clip([(x + a, dd, q, v, ar) for x, dd, q, v, ar in hand.notes()], a + h + 0.25)


def build(chord, dur, bpm, *, vel=(58, 108), kind: str = 'open', pattern='build16', spread=(10, 18), fretboard=None,
          seed=0, at=0.0) -> Clip:
    """A build into the next section: 16th down-up strums on `chord` over `dur` beats, crescendo from vel[0] to vel[1],
    the last two downs accented (8ths when 16th strums would be faster than a hand: above ~158 BPM)."""
    b = _bpm(bpm)
    D = _num(dur, 'build dur', 0.25)
    lo, hi = _vels(vel)
    sh = _as_shape(chord, kind, fretboard)
    rng = random.Random(seed_int(seed))

    def vat(t, w):
        x = t / max(D, _EPS)
        return (lo + (hi - lo) * x) * (0.75 + 0.25 * w) * (1.0 + 0.03 * _tri(rng))
    g, toks = _pattern(pattern)
    g, toks, _ = _fit_tempo(g, toks, b)                 # 16th strums above ~158 BPM: 8ths
    hand = _Hand(b)
    ctx = _Ctx(b, rng, _arts(None), spread=spread, up_strings='top4', timing_ms=4.0)
    n = max(1, int(round(D / g)))
    offset = len(toks) - n if n < len(toks) else 0      # the pattern's end lines up with the end of the build
    toks2 = [toks[(offset + i) % len(toks)] for i in range(n)]
    _play_steps_x(hand, ctx, toks2, g, 0.0, D, lambda t: sh, vat, lambda t, tok: None, _token)
    a = _pos(at)
    return _clip([(x + a, dd, q, v, ar) for x, dd, q, v, ar in hand.notes(D)], a + D)


# ------------------------------------------------------------------------------------------------ lead moves

class Lick(Clip):
    """A lead move: its notes (a Clip: iterate, place, transform as usual) + the pitch automation it needs (.auto =
    {'instrument.pitchbend': points, 'instrument.vibrato': ..., 'instrument.vibratorate': ...}, beats relative to
    the move's start). lick.play(track, at) plays the notes and writes the automation there (vibrato only on a
    sampler). Clip transforms return plain Clips (without .auto). Bends move every sounding note of the track: play
    them on a monophonic lead track."""

    __slots__ = ('auto',)

    def play(self, track, at=0.0):
        return _play(track, self, self.auto, at)


def _lick(notes, length=None, auto=None) -> Lick:
    c = _clip(notes, length)
    lk = Lick._raw(c.notes, c.length)
    lk.auto = {k: list(v) for k, v in (auto or {}).items() if v}
    return lk


def _play(track, clip, auto, at):
    song = getattr(track, '_song', None)
    a = song._at(at) if song is not None else _pos(at)
    track.play(clip, a)
    for tgt, pts in (auto or {}).items():
        if not pts:
            continue
        if tgt in ('instrument.vibrato', 'instrument.vibratorate') and not _is_sampler(track):
            continue
        shifted = []
        for p in pts:
            q = (max(0.0, a + p[0]),) + tuple(p[1:])
            shifted.append(q)
        track.automate(tgt, shifted)
    return track


def _bend_pts(s: float, e: float, amount: float, rise: float, *, release=None, fall=None, pre=False,
              pre_at: float | None = None) -> list:
    """Pitchbend points (semitones) for a bend on a note from s to e: up to `amount` over `rise` beats (or already
    there: pre=True - the silent push at pre_at, default 0.02 beats before s), optionally released back to 0 from
    `release` over `fall`; back at 0 (a step) just after e."""
    pts = []
    if pre:
        t = s - 0.02 if pre_at is None else min(pre_at, s - 0.005)
        pts += [(t - 0.01, 0.0, 'step'), (t, amount, 'step')]
    else:
        pts += [(s - 0.01, 0.0, 'step'), (s + rise, amount, 'smooth')]
    if release is not None:
        r = max(release, pts[-1][0] + 0.01)
        f = fall if fall is not None else rise
        pts += [(r, amount), (min(e, r + f), 0.0, 'smooth')]
    else:
        pts += [(e, amount)]
    pts.append((e + 0.005, 0.0, 'step'))
    return pts


def bend(pitch, dur, bpm, *, amount: int = 2, rise_ms: float = 110.0, release=None, fall_ms: float | None = None,
         vel=96, vibrato: bool = True, depth: float = 26.0, rate: float = 5.6, at=0.0) -> Lick:
    """A string bend INTO `pitch`: the note fretted `amount` semitones lower (2 = a whole-step bend, 1 = half, 3 =
    a minor 3rd) and pushed up over rise_ms (70-160: a quick or a slow singing bend), held for `dur` beats, with
    release= a share of dur (0.6: bend and release back down from there) and a vibrato at the top (vibrato=True).
    Returns a Lick (notes + 'instrument.pitchbend' / vibrato automation): lick.play(track, at) on a monophonic lead
    track."""
    b = _bpm(bpm)
    p = note(pitch)
    D = _num(dur, 'bend dur', 0.1)
    k = int(_num(amount, 'bend amount (semitones)', 1, 4))
    a = _pos(at)
    rise = _ms(_num(rise_ms, 'bend rise_ms', 10, 1000), b)
    rel = None if release is None else D * _num(release, 'bend release (share of dur)', 0.1, 0.95)
    fall = None if fall_ms is None else _ms(fall_ms, b)
    auto = {'instrument.pitchbend': _bend_pts(0.0, D, k, rise, release=rel, fall=fall)}
    v0 = _vels(vel)[0]
    if vibrato and D * 60.0 / b >= 0.5:
        auto.update(_art.vibrato_points(Clip._raw([Note(0.0, D if rel is None else rel, p, _vel(v0))], D), b,
                                        depth=depth, rate=rate, delay=max(0.15, rise_ms / 1000.0 + 0.05),
                                        min_dur=0.1))
    lk = _lick([(0.0, D, p - k, v0)], D, auto)
    return lk if a == 0 else _shifted(lk, a)


def _shifted(lk: Lick, a: float) -> Lick:
    out = Lick._raw([n._replace(start=n.start + a) for n in lk], lk.length + a)
    out.auto = {k: [(p[0] + a,) + tuple(p[1:]) for p in v] for k, v in lk.auto.items()}
    return out


def prebend(pitch, dur, bpm, *, amount: int = 2, release: float = 0.5, fall_ms: float = 160.0, vel=94,
            at=0.0) -> Lick:
    """A pre-bend and release: the string bent up silently before it is picked (the note sounds at `pitch`), then
    released after `release` x dur over fall_ms down to the fretted note `amount` lower - the crying fall of blues and
    rock ballads. Returns a Lick."""
    b = _bpm(bpm)
    p = note(pitch)
    D = _num(dur, 'prebend dur', 0.1)
    k = int(_num(amount, 'prebend amount', 1, 4))
    r = D * _num(release, 'prebend release', 0.05, 0.95)
    auto = {'instrument.pitchbend': _bend_pts(0.0, D, k, 0.0, release=r, fall=_ms(fall_ms, b), pre=True)}
    lk = _lick([(0.0, D, p - k, _vels(vel)[0])], D, auto)
    a = _pos(at)
    return lk if a == 0 else _shifted(lk, a)


def vibrato(pitch, dur, bpm, *, depth: float = 28.0, rate: float = 5.6, delay: float = 0.25, vel=90,
            at=0.0) -> Lick:
    """A held note with a finger vibrato: straight for `delay` s, then growing to +-depth cents at `rate` Hz (wider
    and faster towards the end: articulation.vibrato_points). A Lick (the 'instrument.vibrato' automation needs a
    sampler)."""
    b = _bpm(bpm)
    p = note(pitch)
    D = _num(dur, 'vibrato dur', 0.1)
    c = Clip._raw([Note(0.0, D, p, _vel(_vels(vel)[0]))], D)
    auto = _art.vibrato_points(c, b, depth=depth, rate=rate, delay=delay, min_dur=0.1)
    lk = _lick([(0.0, D, p, _vels(vel)[0])], D, auto)
    a = _pos(at)
    return lk if a == 0 else _shifted(lk, a)


def slide(frm, to, dur, bpm, *, split: float = 0.5, ms: float = 90.0, legato: bool = True, vel=90,
          at=0.0) -> Clip:
    """A slide on one string from `frm` to `to`: frm held for split x dur, then the finger slides (legato=True:
    the target is tied to it with a glide mark of `ms` - a monophonic legato sampler bends into it without a new
    attack; legato=False: the frets passed are touched quickly and softly, for a polyphonic guitar)."""
    b = _bpm(bpm)
    p0, p1 = note(frm), note(to)
    D = _num(dur, 'slide dur', 0.1)
    sp = D * _num(split, 'slide split', 0.05, 0.95)
    a = _pos(at)
    v0 = _vels(vel)[0]
    if legato:
        return _clip([(a, sp + 0.03, p0, v0), (a + sp, D - sp, p1, v0 * 0.82, None, float(ms))], a + D)
    step = 1 if p1 > p0 else -1
    mids = list(range(p0 + step, p1, step))
    tot = _ms(ms, b)
    out = [(a, sp, p0, v0)]
    for i, q in enumerate(mids):
        out.append((a + sp + tot * i / max(1, len(mids) + 1), tot / max(1, len(mids) + 1), q, v0 * 0.35))
    t1 = sp + (tot * len(mids) / max(1, len(mids) + 1) if mids else 0.0)
    out.append((a + t1, D - t1, p1, v0 * 0.8))
    return _clip(out, a + D)


def hammer_on(frm, to, dur, bpm, *, split: float = 0.5, legato: bool = True, art=None, vel=90, at=0.0) -> Clip:
    """A hammer-on (to above frm) or pull-off (to below): frm picked, `to` sounded by the fretting finger alone at
    split x dur - softer, tied (legato=True: overlapping, a monophonic legato sampler plays no new attack; art= the
    guitar's hammer-on articulation for a polyphonic one)."""
    _bpm(bpm)
    p0, p1 = note(frm), note(to)
    D = _num(dur, 'hammer_on dur', 0.05)
    sp = D * _num(split, 'hammer_on split', 0.05, 0.95)
    a = _pos(at)
    v0 = _vels(vel)[0]
    over = 0.03 if legato else -0.01
    return _clip([(a, sp + over, p0, v0), (a + sp, D - sp, p1, v0 * 0.76, art)], a + D)


def pull_off(frm, to, dur, bpm, **kw) -> Clip:
    """A pull-off: frm picked, the finger pulls off to the lower `to` (hammer_on with to below frm)."""
    if note(to) >= note(frm):
        raise ComposeError(f"pull_off goes down: {to!r} must be below {frm!r}")
    return hammer_on(frm, to, dur, bpm, **kw)


def trill(pitch, dur, bpm, *, upper=None, chord=None, key=None, rate: float = 11.0, legato: bool = True, art=None,
          vel=90, wobble_ms: float = 4.0, seed=0, at=0.0) -> Clip:
    """A hammer-on / pull-off trill: the note and its upper neighbour (upper= semitones, else a scale step of chord /
    key) alternated at `rate` notes per second (9-14) by the fretting hand alone: the first note picked at vel, the
    rest light (the finger is weaker than the pick) and tied; the last half-beat holds the note. FAST: spice, never
    a habit."""
    b = _bpm(bpm)
    p = note(pitch)
    D = _num(dur, 'trill dur', 0.25)
    a = _pos(at)
    up = p + int(upper) if upper is not None else _step(p, _scale_pcs(chord, key), 1)
    if up - p > 3:
        up = p + 2
    step = _sec(1.0 / _num(rate, 'trill rate', 4, 20), b)
    v0 = _vels(vel)[0]
    rng = random.Random(seed_int(seed))
    body = max(step * 2, D - min(0.5, D * 0.3))
    n = max(2, int(body / step))
    out = []
    for i in range(n):
        t = i * step + (_ms(wobble_ms, b) * _tri(rng) if i else 0.0)
        q = p if i % 2 == 0 else up
        v = v0 if i == 0 else max(12.0, v0 - 26.0 - 6.0 * (i % 2) + 6.0 * math.sin(math.pi * i / n))
        out.append((a + max(0.0, t), step * (1.3 if legato else 0.9), q, v, None if i == 0 else art))
    t = n * step
    out.append((a + t, max(0.1, D - t), p, max(12.0, v0 - 14.0), art))
    return _clip(out, a + D)


def double_stop(top, dur, bpm, *, interval=None, chord=None, key=None, vel=92, spread_ms: float = 6.0,
                at=0.0) -> Clip:
    """Two strings at once under a melody note: `top` with a note `interval` semitones below (default: the diatonic
    3rd, 4th or 6th below that is a chord tone - the Chuck Berry / country / soul double stop), the lower note a
    little softer, a quick 6 ms rake."""
    b = _bpm(bpm)
    p = note(top)
    D = _num(dur, 'double_stop dur', 0.05)
    a = _pos(at)
    if interval is None:
        pcs = _scale_pcs(chord, key)
        tones = {(Chord.parse(chord).root + i) % 12 for i in Chord.parse(chord).intervals} if chord else pcs
        low = None
        for d in (3, 4, 5, 8, 9):
            q = p - d
            if q % 12 in pcs and q % 12 in tones:
                low = q
                break
        if low is None:
            low = _step(p, pcs, -2)
    else:
        low = p - int(interval)
    v0 = _vels(vel)[0]
    st = _ms(spread_ms, b)
    return _clip([(a, D, low, v0 * 0.84), (a + st, D - st, p, v0)], a + D)


def rake(pitch, dur, bpm, *, strings: int = 3, ms: float = 16.0, dead=None, vel=100, fretboard=None,
         at=0.0) -> Clip:
    """A rake into a note: the pick dragged across `strings` muted strings below it (dead scratches `ms` apart, the
    guitar's dead-note articulation if dead= is given, else short soft ticks) before the note is picked - the
    target lands at at + strings x ms (blues and rock phrase starts)."""
    b = _bpm(bpm)
    p = note(pitch)
    D = _num(dur, 'rake dur', 0.1)
    a = _pos(at)
    fb = fretboard if isinstance(fretboard, Fretboard) else _board(fretboard)
    n = int(_num(strings, 'rake strings', 1, 5))
    pos = fb.positions(p, 1)
    s = max((x for x in pos), key=lambda x: (x[1] <= 15, x[0]), default=(5, 0))
    st = _ms(_num(ms, 'rake ms', 5, 60), b)
    v0 = _vels(vel)[0]
    out = []
    for i in range(n):
        ls = s[0] - n + i
        q = fb.open[ls] + s[1] if ls >= 0 else p - 5 * (n - i)
        out.append((a + i * st, st * 0.9, q, v0 * (0.32 + 0.06 * i), dead))
    out.append((a + n * st, D, p, v0))
    return _clip(out, a + n * st + D)


def harmonic(pitch, dur, bpm, *, art=None, vel=72, at=0.0) -> Clip:
    """A natural harmonic (the 12th-fret octave, 7th-fret twelfth, 5th-fret double octave): the bell tone at `pitch`,
    soft and ringing - with art= the guitar's harmonic articulation (sampled/concert_guitar has real flageolets on
    G#5-G7), else a soft ringing note. An intro / ending colour."""
    _bpm(bpm)
    p = note(pitch)
    D = _num(dur, 'harmonic dur', 0.1)
    a = _pos(at)
    return _clip([(a, D, p, _vels(vel)[0], art)], a + D)


def tremolo_pick(pitch, dur, bpm, *, rate: float = 12.0, accent=(1.0, 0.8), crescendo: float = 0.3, vel=92,
                 gate: float = 0.8, wobble_ms: float = 3.0, seed=0, at=0.0) -> Clip:
    """Tremolo picking: one note (or a double stop: a list) picked down-up at `rate` notes per second (10-16), downs
    stronger (accent), a crescendo over the figure (-1..1) - surf, the climax of a solo. FAST: spice."""
    b = _bpm(bpm)
    ps = [note(x) for x in pitch] if isinstance(pitch, (list, tuple)) else [note(pitch)]
    D = _num(dur, 'tremolo_pick dur', 0.1)
    a = _pos(at)
    step = _sec(1.0 / _num(rate, 'tremolo_pick rate', 4, 24), b)
    cr = _num(crescendo, 'tremolo_pick crescendo', -1, 1)
    v0 = _vels(vel)[0]
    rng = random.Random(seed_int(seed))
    n = max(2, int(D / step + _EPS))
    out = []
    for i in range(n):
        x = i / max(1, n - 1)
        t = i * step + (_ms(wobble_ms, b) * _tri(rng) if i else 0.0)
        v = v0 * accent[i % 2] * (1.0 + cr * (x - 0.5) * 0.4)
        for q in ps:
            out.append((a + max(0.0, t), step * gate, q, v))
    return _clip(out, a + D)


def lick(chord, dur, bpm, *, start=None, direction: str = 'down', notes: int = 5, key=None, legato: bool = True,
         art=None, vel=(90, 74), seed=0, at=0.0) -> Clip:
    """A short pentatonic lick for a gap (the guitarist's answer): `notes` notes of the chord's pentatonic (minor
    pentatonic on minor / dominant chords, major on major ones) from `start` (default the chord's root around A4)
    down (or up) in 16ths, in hammer-on / pull-off pairs (every second note tied and softer), fitted into `dur`
    and landing on a chord tone."""
    b = _bpm(bpm)
    c = _chord(chord)
    D = _num(dur, 'lick dur', 0.25)
    a = _pos(at)
    pcs = _pentatonic(c, key)
    tones = {(c.root + i) % 12 for i in c.intervals}
    d = -1 if direction == 'down' else 1
    s = note(start) if start is not None else 69 + (c.root - 69) % 12
    q = s if s % 12 in pcs else _step(s, pcs, d)
    line = [q]
    for _ in range(int(_num(notes, 'lick notes', 2, 12)) - 1):
        line.append(_step(line[-1], pcs, d))
    while line[-1] % 12 not in tones and len(line) < 14:
        line.append(_step(line[-1], pcs, d))
    step = min(0.25, D / len(line))
    v0, v1 = _vels(vel) if isinstance(vel, (tuple, list)) else (_vels(vel)[0], _vels(vel)[0] * 0.8)
    if isinstance(vel, (tuple, list)):
        v0, v1 = float(vel[0]), float(vel[1])
    rng = random.Random(seed_int(seed))
    out = []
    t0 = D - step * len(line)
    for i, p in enumerate(line):
        x = i / max(1, len(line) - 1)
        slur = legato and i % 2 == 1
        t = t0 + i * step + (0.0 if slur or i == 0 else _ms(4.0, b) * _tri(rng))
        last = i == len(line) - 1
        dd = (D - t) if last else step * (1.12 if legato and i % 2 == 0 else 0.9)
        out.append((a + max(0.0, t), dd, p, (v0 + (v1 - v0) * x) * (0.8 if slur else 1.0), art if slur else None))
    return _clip(out, a + D)


MOVES = {
    # rhythm hand
    'strum': strum, 'chuck': chuck, 'strum_pattern': strum_pattern, 'arpeggio': arpeggio, 'travis': travis,
    'chug': chug, 'skank': skank, 'scratch': scratch, 'let_ring': let_ring, 'hammer_chord': hammer_chord,
    'slide_chord': slide_chord, 'bass_run': bass_run, 'choke': choke, 'build': build,
    # lead hand
    'bend': bend, 'prebend': prebend, 'vibrato': vibrato, 'slide': slide, 'hammer_on': hammer_on,
    'pull_off': pull_off, 'trill': trill, 'double_stop': double_stop, 'rake': rake, 'harmonic': harmonic,
    'tremolo_pick': tremolo_pick, 'lick': lick,
}
"""Every guitar move by name -> its function (rhythm moves return a Clip; bend / prebend / vibrato a Lick = Clip +
the pitch automation, lick.play(track, at)). Call one on its own or let arrange() / lead() choose."""


# ------------------------------------------------------------------------------------------------ budgets

FAST = ('trill', 'tremolo_pick')
"""Fast alternations (hammer-on trills, tremolo picking): the rarest spice (user feedback 2026-09-30 on the pianist:
"zu viele von diesen schnellen Zwei-Tasten-Wechseln"): at most one per fast_every bars (default 16; ballad / pop /
jazz: none), two of a kind at least 32 bars apart."""

FLASH = ('bend', 'prebend', 'rake', 'double_stop', 'lick', 'harmonic', 'slide_chord', 'build', 'choke')
"""Showy moves: bends, pre-bends, rakes, double stops, licks in the gaps; for the rhythm hand the slid-in chord and the
section-end fills (build, choke). At most one per flash_every bars (lead: rock 2, blues 1.5, ballad 3, pop 4, jazz 8;
rhythm fills: fill_every)."""

SPICE = ('slide', 'hammer_on', 'pull_off', 'scoop', 'hammer_chord', 'sus4', 'bass_run')
"""Everyday colour: slides between notes, hammer-ons / pull-offs, a scoop into a phrase, the sus2 / sus4 hammer on a
chord, a bass-string walk-up: at most one per spice_every bars."""


def _cls(name: str) -> str:
    if name in FAST:
        return 'fast'
    if name in FLASH:
        return 'flash'
    if name in SPICE:
        return 'spice'
    raise ComposeError(f"{name!r} is not a budgeted guitar move ({', '.join(FAST + FLASH + SPICE)})")


class Memory:
    """What one guitarist already played in a song: pass the same Memory to every arrange() / lead() call of the song
    (memory=, with at= the part's position in beats - a Section works; without at= each call follows the previous
    one) and the budgets count song-wide - a bend at the end of verse 1 keeps the first bar of the chorus from
    bending again, a trill every 16 bars at most. The rhythm hand also keeps its last shape (the next part starts
    near it). played(at, name) books a move placed by hand. .events: [(beat, class, name)]."""

    def __init__(self):
        self.clock = 0.0
        self.events: list = []
        self.shape: Shape | None = None
        self.sections: list = []
        self.lead_end: float | None = None         # where the lead's last note stopped (beats, song time)

    def played(self, at, name: str) -> 'Memory':
        t = _pos(at)
        self.events.append((t, _cls(name), name))
        self.clock = max(self.clock, t)
        return self

    def count(self, cls: str | None = None) -> int:
        return sum(1 for _, c, _ in self.events if cls is None or c == cls)

    def __repr__(self) -> str:
        by: dict = {}
        for _, c, n in self.events:
            by[c] = by.get(c, 0) + 1
        return f"Memory(clock {self.clock:g}, {by or 'nothing yet'})"


def _budget(cands: list[dict], memory, base: float, bpb: float, every: dict, same_every: float = 32.0) -> None:
    """Keep the best-placed candidates (dicts: name, cls, t, score, slot): per class at most one per every[cls] bars
    (0 = none), two FAST of a kind at least same_every bars apart, one move per slot (a note, a chord change);
    counted together with memory's earlier moves. Sets c['keep']. The shared mechanism: agentsound.budget.Budget."""
    bud = Budget({k: v * bpb for k, v in every.items()}, same_every=same_every * bpb, same=('fast',),
                 events=list(memory.events) if memory is not None else [])
    bud.keep(cands, base)


# ------------------------------------------------------------------------------------------------ styles

SECTION_ENERGY = {'intro': 0.35, 'verse': 0.45, 'pre': 0.62, 'chorus': 0.85, 'post': 0.75, 'bridge': 0.55,
                  'solo': 0.8, 'break': 0.4, 'outro': 0.4}
"""The default energy (0..1) of a section kind: it sets the velocity range, how busy the strums are, the strings an
up-stroke takes and which technique a style plays (verse lighter, chorus bigger)."""

_SECTION_WORDS = (('pre', 'pre'), ('intro', 'intro'), ('verse', 'verse'), ('chorus', 'chorus'), ('refrain', 'chorus'),
                  ('hook', 'chorus'), ('drop', 'chorus'), ('post', 'post'), ('bridge', 'bridge'), ('middle', 'bridge'),
                  ('solo', 'solo'), ('break', 'break'), ('interlude', 'break'), ('outro', 'outro'), ('end', 'outro'),
                  ('coda', 'outro'), ('tag', 'outro'), ('lift', 'pre'), ('build', 'pre'))


def _section_kind(name) -> str:
    if name is None:
        return 'verse'
    n = str(name).strip().lower()
    for w, k in _SECTION_WORDS:
        if n.startswith(w):
            return k
    for w, k in _SECTION_WORDS:
        if w in n:
            return k
    return 'verse'


TECHNIQUES = {
    'strum': dict(patterns={'pop': 3.0, 'folk': 2.0, 'pop_push': 1.0}, turn='pop_push', kind='open',
                  spread=(16, 30), up='top4'),
    'strum16': dict(patterns={'folk16': 2.0, 'rock16': 1.0}, turn='build16', kind='open', spread=(12, 24), up='top4'),
    'eighths': dict(patterns={'eighths': 1.0}, turn='pop_push', kind='open', spread=(12, 22), up='top4'),
    'downs': dict(patterns={'downs': 1.0}, turn='power_drive', kind='power', spread=(7, 12), up='all'),
    'ballad_strum': dict(patterns={'ballad': 2.0, 'half': 1.0}, turn='ballad', kind='open', spread=(22, 38),
                         up='top3'),
    'arpeggio': dict(patterns={'arp_ballad': 2.0, 'arp_pima': 1.0, 'arp_up': 1.0}, turn=None, kind='open',
                     level=0.85, lift_ms=10.0),
    'arp16': dict(patterns={'arp16': 1.0, 'jangle': 1.0}, turn=None, kind='open', level=0.85, lift_ms=10.0),
    'travis': dict(patterns={'travis': 2.0, 'travis_pinch': 1.0}, turn=None, kind='open', level=0.88, lift_ms=10.0),
    'let_ring': dict(patterns={'let_ring': 1.0}, turn=None, kind='open', level=0.8, lift_ms=8.0),
    'muted8': dict(patterns={'chug': 2.0, 'chug_push': 1.0}, turn='chug_push', kind='open', spread=(10, 16),
                   level=0.92),
    'chug': dict(patterns={'chug': 3.0, 'chug_push': 1.0, 'gallop': 0.5}, turn='chug_push', kind='power',
                 spread=(7, 12), level=1.0),
    'drive': dict(patterns={'power_drive': 2.0, 'eighths': 0.5}, turn='power_drive', kind='power', spread=(7, 12),
                  up='all'),
    'power': dict(patterns={'power': 2.0, 'anthem': 1.0, 'stabs': 0.6}, turn='power_drive', kind='power',
                  spread=(8, 14), up='all'),
    'scratch': dict(patterns={'funk': 2.0, 'funk_sparse': 1.0}, turn='funk', kind='upper', spread=(6, 12), up='all',
                    gate=0.09),
    'skank': dict(patterns={'skank': 2.0, 'bubble': 1.0}, turn='bubble', kind='upper', spread=(8, 14), up='all',
                  gate=0.11, late_ms=8.0),
    'four': dict(patterns={'four': 1.0}, turn=None, kind='shell', spread=(8, 14), gate=0.28, level=0.85),
    'boom_chick': dict(patterns={'boom_chick': 1.0}, turn=None, kind='open', spread=(10, 18), up='top3',
                       down='top4'),
    'ring': dict(patterns={'whole': 1.0}, turn=None, kind='open', spread=(40, 70), level=0.9),
}
"""The rhythm hand's techniques (arrange(technique=...)): patterns (PATTERNS names with weights; turn = the variant
for the last bar of a 4-bar phrase), the shape kind, the strum spread (ms for six strings), the strings of an
up-stroke, gate (seconds a chop / scratch rings), level (x the velocity range), lay-back."""

STYLES = {
    'pop': dict(sections={'intro': 'arpeggio', 'verse': 'muted8', 'pre': 'eighths', 'chorus': 'strum',
                          'post': 'strum', 'bridge': 'arpeggio', 'solo': 'strum', 'break': 'ring', 'outro': 'ring'},
                fills={'build': 2.0, 'bass_run': 1.0, 'choke': 1.0}, ornaments={'hammer_chord': 2.0, 'sus4': 1.0},
                fill=0.6, anticipate=0.3, open_change=0.12, spice_every=4, fill_every=4, timing_ms=5.0),
    'folk': dict(sections={'intro': 'travis', 'verse': 'travis', 'pre': 'strum', 'chorus': 'strum', 'post': 'strum',
                           'bridge': 'arpeggio', 'solo': 'strum', 'break': 'let_ring', 'outro': 'let_ring'},
                 fills={'bass_run': 3.0, 'build': 0.6}, ornaments={'hammer_chord': 3.0, 'sus4': 2.0},
                 fill=0.7, anticipate=0.2, open_change=0.3, spice_every=2, fill_every=4, timing_ms=6.0),
    'rock': dict(sections={'intro': 'chug', 'verse': 'chug', 'pre': 'drive', 'chorus': 'power', 'post': 'power',
                           'bridge': 'ring', 'solo': 'power', 'break': 'ring', 'outro': 'ring'},
                 fills={'build': 1.0, 'choke': 1.5, 'slide_chord': 1.0}, ornaments={'slide_chord': 1.0},
                 fill=0.6, anticipate=0.35, open_change=0.0, spice_every=8, fill_every=4, timing_ms=4.0),
    'punk': dict(sections={'intro': 'downs', 'verse': 'downs', 'pre': 'downs', 'chorus': 'downs', 'post': 'downs',
                           'bridge': 'chug', 'solo': 'downs', 'break': 'ring', 'outro': 'ring'},
                 fills={'choke': 1.0, 'build': 1.0}, ornaments={}, fill=0.5, anticipate=0.4, open_change=0.0,
                 spice_every=8, fill_every=4, timing_ms=3.0),
    'ballad': dict(sections={'intro': 'let_ring', 'verse': 'arpeggio', 'pre': 'arpeggio', 'chorus': 'ballad_strum',
                             'post': 'ballad_strum', 'bridge': 'arpeggio', 'solo': 'ballad_strum',
                             'break': 'let_ring', 'outro': 'let_ring'},
                   fills={'bass_run': 1.0, 'build': 0.5}, ornaments={'hammer_chord': 1.0, 'sus4': 0.6},
                   fill=0.4, anticipate=0.1, open_change=0.0, spice_every=4, fill_every=8, timing_ms=7.0,
                   late_ms=4.0),
    'funk': dict(sections={'intro': 'scratch', 'verse': 'scratch', 'pre': 'scratch', 'chorus': 'scratch',
                           'post': 'scratch', 'bridge': 'scratch', 'solo': 'scratch', 'break': 'scratch',
                           'outro': 'scratch'},
                 fills={'choke': 1.0, 'slide_chord': 1.0}, ornaments={'slide_chord': 1.0}, fill=0.5,
                 anticipate=0.0, open_change=0.0, spice_every=4, fill_every=8, timing_ms=3.0),
    'reggae': dict(sections={k: 'skank' for k in SECTION_ENERGY}, fills={'choke': 1.0}, ornaments={}, fill=0.3,
                   anticipate=0.0, open_change=0.0, spice_every=8, fill_every=8, timing_ms=3.0),
    'country': dict(sections={'intro': 'boom_chick', 'verse': 'boom_chick', 'pre': 'strum', 'chorus': 'strum',
                              'post': 'strum', 'bridge': 'boom_chick', 'solo': 'boom_chick', 'break': 'ring',
                              'outro': 'let_ring'},
                    fills={'bass_run': 3.0, 'build': 0.4}, ornaments={'hammer_chord': 2.0, 'sus4': 1.0}, fill=0.7,
                    anticipate=0.15, open_change=0.2, spice_every=2, fill_every=4, timing_ms=4.0),
    'indie': dict(sections={'intro': 'arp16', 'verse': 'arp16', 'pre': 'eighths', 'chorus': 'eighths',
                            'post': 'strum16', 'bridge': 'arpeggio', 'solo': 'eighths', 'break': 'ring',
                            'outro': 'ring'},
                  fills={'build': 1.0, 'choke': 0.6}, ornaments={'hammer_chord': 1.0}, fill=0.5, anticipate=0.25,
                  open_change=0.1, spice_every=4, fill_every=4, timing_ms=5.0),
    'jazz': dict(sections={k: 'four' for k in SECTION_ENERGY}, fills={}, ornaments={}, fill=0.0, anticipate=0.0,
                 open_change=0.0, spice_every=0, fill_every=0, timing_ms=4.0),
}
"""arrange() style presets: the technique per section kind (SECTION_ENERGY keys), fills into the next section
(weights; FILLS), chord ornaments (RHYTHM_ORNAMENTS), fill probability, anticipation (a stroke an 8th before a change
takes the new chord), the open-string change stroke (the fretting hand already travelling), budgets (spice_every /
fill_every bars) and the timing spread (ms)."""

FILLS = ('build', 'bass_run', 'choke', 'slide_chord')
"""Section-end fills of the rhythm hand (the last 1-2 beats of a part with section_end=True): build (16th strums,
crescendo), bass_run (a walk on the bass strings into the next chord), choke (a hit, then silence: the stop before
the chorus), slide_chord (a power chord / grip slid into the next downbeat)."""

RHYTHM_ORNAMENTS = ('hammer_chord', 'sus4', 'slide_chord')
"""Ornaments on a chord change: hammer_chord (the 3rd hammered on from the 2nd: Dsus2 -> D), sus4 (struck as sus4,
pulled off to the 3rd), slide_chord (the grip slid in from two frets below). Budgeted (spice_every)."""

LEAD_STYLES = {
    'rock': dict(moves={'bend': 3.0, 'prebend': 1.0, 'slide': 2.0, 'hammer_on': 2.0, 'pull_off': 2.0, 'rake': 1.0,
                        'double_stop': 0.5, 'scoop': 1.0, 'trill': 0.5, 'tremolo_pick': 0.2, 'lick': 1.0},
                 vib=(28.0, 5.6), flash_every=2.0, spice_every=1.0, fast_every=16.0, fill=0.5, late_ms=4.0,
                 timing_ms=6.0, legato=0.2, touch=(62, 110)),
    'blues': dict(moves={'bend': 4.0, 'prebend': 1.5, 'rake': 1.5, 'double_stop': 1.5, 'slide': 2.0,
                         'hammer_on': 2.0, 'pull_off': 2.0, 'scoop': 1.0, 'trill': 0.5, 'lick': 1.5},
                  vib=(32.0, 5.2), flash_every=1.5, spice_every=1.0, fast_every=16.0, fill=0.6, late_ms=10.0,
                  timing_ms=8.0, legato=0.25, touch=(58, 112)),
    'ballad': dict(moves={'bend': 2.0, 'prebend': 0.6, 'slide': 2.5, 'hammer_on': 1.0, 'pull_off': 1.0,
                          'scoop': 1.5, 'lick': 0.4},
                   vib=(24.0, 5.0), flash_every=3.0, spice_every=1.5, fast_every=0.0, fill=0.3, late_ms=8.0,
                   timing_ms=7.0, legato=0.75, touch=(50, 90)),
    'pop': dict(moves={'slide': 2.0, 'hammer_on': 1.5, 'pull_off': 1.5, 'bend': 1.0, 'scoop': 1.0,
                       'double_stop': 0.5, 'lick': 0.5},
                vib=(18.0, 5.4), flash_every=4.0, spice_every=1.5, fast_every=0.0, fill=0.3, late_ms=3.0,
                timing_ms=5.0, legato=0.3, touch=(60, 106)),
    'country': dict(moves={'double_stop': 2.0, 'bend': 2.0, 'slide': 2.0, 'hammer_on': 2.0, 'pull_off': 2.0,
                           'rake': 0.5, 'lick': 1.0},
                    vib=(12.0, 5.8), flash_every=2.0, spice_every=1.0, fast_every=16.0, fill=0.5, late_ms=2.0,
                    timing_ms=5.0, legato=0.1, touch=(60, 108)),
    'jazz': dict(moves={'slide': 2.0, 'hammer_on': 1.0, 'pull_off': 1.0, 'scoop': 0.5},
                 vib=(8.0, 5.0), flash_every=8.0, spice_every=2.0, fast_every=0.0, fill=0.2, late_ms=6.0,
                 timing_ms=6.0, legato=0.45, touch=(54, 98)),
}
"""lead() style presets: move weights (how readily each is proposed), the vibrato (cents, Hz), the budgets
(flash_every / spice_every / fast_every bars; 0 = never), the gap-lick probability, lay-back and timing (ms) and the
touch() velocity range."""


# ------------------------------------------------------------------------------------------------ the result

class Arrangement:
    """What arrange() / lead() played: clip (the notes, with articulation / glide marks), auto ({target: points},
    beats relative to the part: pitchbend for bends, vibrato), moves (a log: (start, end, kind, name) with kind
    'technique' | 'pattern' | 'shape' | 'anticipation' | 'ornament' | 'fill' | 'move' | 'phrasing' | 'vibrato' |
    'dropped'), shapes ([(beat,
    Shape)] the rhythm hand's grips), budget (what the budgets allowed), energy, technique, section.
    play(track, at) places it (notes + automation), take(n) = the same part played again (another take: the same
    decisions, new timing / velocity noise - for a double-tracked guitar), summary() counts the moves."""

    def __init__(self, clip: Clip, auto: dict, moves: list, *, shapes=None, budget=None, energy=None, technique=None,
                 section=None, rerun=None, gestures=None):
        self.clip, self.auto, self.moves = clip, auto, moves
        self.gestures = list(gestures or [])
        self.shapes = shapes or []
        self.budget = budget or {}
        self.energy, self.technique, self.section = energy, technique, section
        self._rerun = rerun

    def __repr__(self) -> str:
        return (f"Arrangement({self.section or '-'}: {self.technique or 'lead'}, energy {self.energy}, "
                f"{len(self.clip)} notes, {self.summary()})")

    def play(self, track, at=0.0):
        """Place the part on a track at `at` (a beat or a Section): the notes and the automation (vibrato only on
        a sampler); a lead(gestures=True) part: the notes and its gestures through fretwork.render."""
        if self.gestures:
            from . import fretwork
            fretwork.render(track, self.part(), at)
            return track
        return _play(track, self.clip, self.auto, at)

    def part(self):
        """The arrangement as a soloist.Part (clip + gestures; the moves as its log)."""
        from .soloist import Part
        return Part(self.clip, self.gestures, self.moves)

    def take(self, n: int = 2) -> 'Arrangement':
        """The same part as another take (the same shapes, patterns and moves; timing and velocities played anew):
        the second guitar of a double-tracked pair."""
        if self._rerun is None:
            raise ComposeError("this arrangement cannot be re-taken")
        return self._rerun(n)

    def summary(self) -> dict:
        out: dict = {}
        for _, _, kind, name in self.moves:
            if kind in ('shape', 'pattern'):
                continue
            k = f"{kind}:{name}"
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    def count(self, kind: str, name: str | None = None) -> int:
        return sum(1 for _, _, k, n in self.moves if k == kind and (name is None or n == name))


# ------------------------------------------------------------------------------------------------ the rhythm arranger

def _level(energy: float, level: float = 1.0) -> tuple[float, float]:
    lo = 44.0 + 36.0 * energy
    hi = min(122.0, lo + 28.0 + 10.0 * energy)
    return lo * level, min(124.0, hi * (0.5 + 0.5 * level))


def arrange(prog, *, bpm, key=None, style: str = 'pop', section=None, energy: float | None = None,
            density: float = 0.5, seed=0, take=None, technique: str | None = None, pattern=None,
            kind: str | None = None, vel=None, fill: float | None = None, fills: dict | None = None,
            ornaments: dict | None = None, section_end: bool = True, next_chord=None, anticipate: float | None = None,
            open_change: float | None = None, swing=None, spice_every: float | None = None,
            fill_every: float | None = None, tuning='standard', capo: int = 0, fretboard=None, sound=None,
            articulations=None, memory: Memory | None = None, at=None, length=None, into=None,
            strings=None) -> Arrangement:
    """A rhythm guitarist's part over `prog` -> Arrangement (.clip, .play(track, at), .take(2), .moves, .shapes).

    The section decides (section= a Section - its name, length and start - or a name: intro, verse, pre, chorus,
    post, bridge, solo, break, outro; energy= overrides SECTION_ENERGY): the style's technique for it (STYLES: pop =
    arpeggio intro, palm-muted verse, 8ths pre, open strums in the chorus; folk = Travis picking, strummed chorus;
    rock = palm-muted power-chord chugs, 8th drive, ringing power chords; punk, ballad, funk (16th scratch), reggae
    (skank), country (boom-chick), indie (jangle), jazz (four to the bar); technique= / pattern= / kind= override),
    the velocity range (vel=(lo, hi) overrides), how many strings an up-stroke takes. The fretting hand: shapes of
    the kind voice-led through the changes (Fretboard: tuning, capo, a hand's stretch; memory= continues from the
    last shape), fretted strings lift a little before a change, an anticipation now and then (a stroke an 8th before
    the change takes the new chord), the open-string stroke of a travelling hand (folk / pop). The picking hand:
    downs low -> high, ups high -> low and lighter, spread in ms, dead strums, palm mutes (sound= finds the guitar's
    'palm mute' / 'dead note' / 'hammer-on' articulations, articulations= overrides, else emulated), accents, a
    phrase arc, the last bar of each 4-bar phrase a variant (turn), human timing (seeded; take= new noise only).
    Ornaments on chord changes (RHYTHM_ORNAMENTS: hammer_chord, sus4, slide_chord) at most one per spice_every bars;
    a fill into the next section (FILLS; section_end=True, next_chord= the chord it leads to, else the progression's
    first) at most one per fill_every bars; into= the next section (a Section or a name) makes it a transition: into a
    bigger section a fill is (nearly) certain and leans to build / choke / slide, into a smaller one it is rarer and
    leans to the bass run; a picked part (arpeggio, Travis, let ring) never ends in a choke or a build unless the
    next section is clearly bigger. strings= the strings a downstroke takes ('top5' / 'top4': an acoustic in a full
    band that leaves the low strings to the bass; ornaments, palm mutes and fills keep to them too). The hand has a
    speed limit: a 16th pattern faster than it can strum (above ~158 BPM) is played on the 8th grid. At a chord
    change the strings that do not keep their fret stop (a grip that leaves out the low E damps it). density 0..1
    scales ornaments and fills. Deterministic by seed."""
    if style not in STYLES:
        raise ComposeError(f"guitarist style must be one of {', '.join(STYLES)}, got {style!r}")
    S = STYLES[style]
    b = _bpm(bpm)
    dens = _num(density, 'guitarist density', 0, 1)
    sec_name = getattr(section, 'name', section)
    sk = _section_kind(sec_name)
    if length is None and hasattr(section, 'length') and not isinstance(section, str):
        length = float(section.length)
    if at is None and hasattr(section, 'start') and not isinstance(section, str):
        at = float(section.start)
    e = SECTION_ENERGY[sk] if energy is None else _num(energy, 'guitarist energy', 0, 1)
    tech = technique or S['sections'][sk]
    if tech not in TECHNIQUES:
        raise ComposeError(f"guitarist technique must be one of {', '.join(TECHNIQUES)}, got {tech!r}")
    T = TECHNIQUES[tech]
    if strings is not None:                       # the strings a downstroke takes ('top5': leave the low E to the bass)
        _select(shape('E'), strings)
        T = dict(T, down=strings)
    k_ = kind or T['kind']
    if k_ not in KINDS:
        raise ComposeError(f"guitarist kind must be one of {', '.join(KINDS)}, got {k_!r}")
    fb = _board(fretboard, tuning, capo)
    p = _as_prog(prog, key, 4.0 if length is None else length)
    L = float(length) if length is not None else p.length
    if L <= 0:
        raise ComposeError("guitarist.arrange needs a progression (or length) longer than 0 beats")
    bpb = p.beats_per_bar
    rng = random.Random(seed_int(seed))
    lo, hi = _vels(vel) if vel is not None else _level(e, T.get('level', 1.0))
    arts = _arts(sound, articulations)
    base = _pos(at) if at is not None else (memory.clock if memory is not None else 0.0)
    moves: list = [(0.0, L, 'technique', tech)]
    # the pattern: the section's main one, a variant for the last bar of each 4-bar phrase
    main = pattern if pattern is not None else _pick(rng, T['patterns'])
    turn = None if pattern is not None else T.get('turn')
    if turn is not None and rng.random() > 0.35 + 0.5 * dens:
        turn = None
    g, toks = _pattern(main)
    pname = main if isinstance(main, str) else 'custom'
    if pattern is None:                           # the hand's speed limit: a 16th pattern too fast for it -> 8ths
        g, toks, slow = _fit_tempo(g, toks, b)
        if slow:
            pname += ' (8ths: tempo)'
    moves.append((0.0, L, 'pattern', pname))
    if turn is not None:
        tg_, tt_ = _pattern(turn)
        turn = _fit_tempo(tg_, tt_, b)[:2]
    # energy shapes the hand: fewer strings on the ups and thinner strums when soft
    up = T.get('up', 'top4')
    if e < 0.5 and up == 'top4':
        up = 'top3'
    elif e >= 0.8 and up == 'top3':
        up = 'top4'
    # the fill into the next section
    p_fill = min(1.0, (S['fill'] if fill is None else _num(fill, 'guitarist fill', 0, 1)) * (0.5 + dens))
    fw = dict(S['fills'] if fills is None else fills)
    for name in fw:
        if name not in FILLS:
            raise ComposeError(f"unknown guitar fill {name!r}; use {', '.join(FILLS)}")
    if k_ in ('upper', 'shell'):
        fw.pop('bass_run', None)
    if k_ != 'power' and k_ not in ('upper', 'barre'):
        fw.pop('slide_chord', None)
    e2 = SECTION_ENERGY[_section_kind(getattr(into, 'name', into))] if into is not None else None
    if any(set(x) & set('BA1234') for x in toks) and not (e2 is not None and e2 > e + 0.1 + _EPS):
        # a picked part (arpeggio, Travis, let ring) does not end in a hard hit or a 16th strum build unless the
        # band clearly lifts next: it walks (bass run) or just rings on
        fw.pop('choke', None)
        fw.pop('build', None)
    if into is not None:
        if e2 > e + 0.1 + _EPS:                   # into a bigger section: announce it
            p_fill = max(p_fill, 0.9)
            for x in ('build', 'choke', 'slide_chord'):
                if x in fw:
                    fw[x] *= 2.0
        elif e2 < e - 0.1 - _EPS:                 # down into a smaller one: rarer, a walk rather than a build
            p_fill *= 0.6
            fw.pop('build', None)
    segs0 = _segs(p, L)
    nxt = _chord(next_chord) if next_chord is not None else (segs0[0][2] if segs0 else None)
    cands = []
    fill_kind, fill_len = None, 0.0
    if section_end and fw and L >= 2 * bpb - _EPS and rng.random() < p_fill:
        fill_kind = _pick(rng, fw)
        fill_len = {'build': 2.0 if e >= 0.6 else 1.0, 'bass_run': 1.0 if b < 110 else 2.0, 'choke': 2.0,
                    'slide_chord': 1.0}[fill_kind]
        fill_len = min(fill_len, bpb)
        cands.append(dict(name=fill_kind, cls=_cls(fill_kind), t=L - fill_len, score=2.0, slot=('end',),
                          what='fill'))
    # chord-change ornaments
    ow = dict(S['ornaments'] if ornaments is None else ornaments)
    for name in ow:
        if name not in RHYTHM_ORNAMENTS:
            raise ComposeError(f"unknown guitar ornament {name!r}; use {', '.join(RHYTHM_ORNAMENTS)}")
    if k_ not in ('open', 'full'):
        ow.pop('hammer_chord', None)
        ow.pop('sus4', None)
    if k_ not in ('power', 'barre', 'upper'):
        ow.pop('slide_chord', None)
    p_orn = min(1.0, 0.35 * (0.5 + dens) * (1.0 if ow else 0.0))
    for i, (a0, a1, c) in enumerate(segs0):
        if a1 - a0 < 2.0 - _EPS or a0 >= L - fill_len - 1.0 or rng.random() >= p_orn:
            continue
        name = _pick(rng, ow)
        if name is None:
            continue
        cands.append(dict(name=name, cls='spice' if name != 'slide_chord' else 'flash', t=a0,
                          score=1.0 + 0.5 * (i == 0) + 0.3 * rng.random(), slot=(round(a0, 4),), what='ornament',
                          chord=c))
    sp_every = S['spice_every'] if spice_every is None else _num(spice_every, 'guitarist spice_every', 0)
    f_every = S['fill_every'] if fill_every is None else _num(fill_every, 'guitarist fill_every', 0)
    _budget(cands, memory, base, bpb, {'spice': sp_every, 'flash': f_every if f_every else 0.0})
    if fill_kind is not None and not next(c for c in cands if c['what'] == 'fill')['keep']:
        moves.append((L - fill_len, L, 'dropped', fill_kind))
        fill_kind, fill_len = None, 0.0
    L_main = L - fill_len
    orn_at = {round(c['t'], 4): c for c in cands if c['what'] == 'ornament' and c['keep']}
    for c in cands:
        if c['what'] == 'ornament' and not c['keep']:
            moves.append((c['t'], c['t'] + 1.0, 'dropped', c['name']))
    anti = S['anticipate'] if anticipate is None else _num(anticipate, 'guitarist anticipate', 0, 1)
    oc = S['open_change'] if open_change is None else _num(open_change, 'guitarist open_change', 0, 1)
    if k_ not in ('open', 'full') or tech in ('arpeggio', 'arp16', 'travis', 'let_ring', 'muted8', 'ring'):
        oc = 0.0

    # the hand starts near where the previous part left it - fixed now, so that take(n) (called later, after other
    # parts moved the memory on) plays the very same shapes
    start_shape = memory.shape if memory is not None else None

    def run(take_):
        return _arrange_run(p, b, fb, T, k_, toks, g, turn, lo, hi, e, up, anti, oc, swing, arts, sound, rng_seed,
                            take_, L, L_main, bpb, orn_at, fill_kind, fill_len, nxt, key, S, start_shape)
    rng_seed = seed_int(seed)
    notes, shapes_log, pushes, extra = run(take)
    for t, sh in shapes_log:
        moves.append((t, t, 'shape', f"{sh.chord} {sh.diagram()}"))
    for t, c in pushes:
        moves.append((t, c, 'anticipation', 'push'))
    moves += extra
    moves.sort(key=lambda m: (m[0], m[2]))
    budget = {'spice_every': sp_every, 'fill_every': f_every,
              'kept': [(round(c['t'], 4), c['name']) for c in cands if c['keep']],
              'dropped': [(round(c['t'], 4), c['name']) for c in cands if not c['keep']]}
    if memory is not None:
        for c in cands:
            if c['keep']:
                memory.events.append((base + c['t'], c['cls'], c['name']))
        memory.clock = base + L
        if shapes_log:
            memory.shape = shapes_log[-1][1]
        memory.sections.append((sec_name, e))
    clip = _clip(notes, L)

    def rerun(n):
        ns, _, _, _ = run(n)
        return Arrangement(_clip(ns, L), {}, list(moves), shapes=list(shapes_log), budget=budget, energy=e,
                           technique=tech, section=sec_name, rerun=rerun)
    return Arrangement(clip, {}, moves, shapes=shapes_log, budget=budget, energy=round(e, 3), technique=tech,
                       section=sec_name, rerun=rerun)


def _arrange_run(p, b, fb, T, k_, toks, g, turn, lo, hi, e, up, anti, oc, swing, arts, sound, seed, take, L, L_main,
                 bpb, orn_at, fill_kind, fill_len, nxt, key, S, start_shape):
    """One performance of an arrangement (the decisions fixed by the caller; `take` changes only the noise)."""
    rng = random.Random(seed)
    nrng = random.Random(f"{seed}:take{take}") if take is not None else random.Random(f"{seed}:noise")
    segs = _segs(p, L_main) if L_main > _EPS else []
    notes: list = []
    extra: list = []
    shapes_log: list = []
    pushes: list = []
    if segs:
        path = voice_lead([c for _, _, c in segs], k_, fretboard=fb, start=start_shape)
        bounds = [a for a, _, _ in segs]

        def tok_at(t):
            i = int(round(t / g))
            if abs(i * g - t) > 1e-6:
                return '.'
            return toks[i % len(toks)]
        for i in range(1, len(segs)):
            c = bounds[i]
            for back in (0.5, 0.25):
                t = c - back
                if t > segs[i - 1][0] + 0.5 and tok_at(t) not in '.-' and not set(tok_at(t)) & set('BA1234'):
                    if rng.random() < anti and round(c, 4) not in orn_at:
                        bounds[i] = t
                        pushes.append((t, c))
                    break
        ctx = _Ctx(b, nrng, arts, spread=T.get('spread', (16, 30)), up_strings=up, down_strings=T.get('down', 'all'),
                   gate=T.get('gate'), timing_ms=S.get('timing_ms', 5.0),
                   late_ms=T.get('late_ms', S.get('late_ms', 0.0)),
                   swing=swing)
        hand = _Hand(b, lift_ms=T.get('lift_ms', 18.0))
        for i in range(1, len(bounds)):
            if path[i] != path[i - 1]:
                hand.change(bounds[i], path[i - 1], path[i])
        idx = {}

        def shape_at(t):
            j = 0
            for kk, a in enumerate(bounds):
                if a <= t + 1e-6:
                    j = kk
            idx['j'] = j
            return path[j]
        changes = set(round(x, 6) for x in bounds[1:])
        oc_last = [-99.0]
        tg, ttoks = turn if turn is not None else (None, None)
        ramp = (L_main - 2 * bpb, L_main) if e >= 0.55 and fill_kind in (None, 'build') and L_main >= 4 * bpb else None
        vel_at = _dyn(lo, hi, bpb, nrng, ramp=ramp, backbeat=1.03 if k_ in ('open', 'power', 'barre') else 1.0)
        n = len(toks)
        i = 0
        done_orn = set()
        picking = any(set(x) & set('BA1234') for x in toks)
        pending: dict = {}
        while True:
            bar = int(math.floor(i * g / bpb + _EPS))
            use_turn = ttoks is not None and bar % 4 == 3
            gg, tk = (tg, ttoks) if use_turn else (g, toks)
            t = i * g
            if t >= L_main - _EPS:
                break
            if use_turn:
                # play the whole turn bar at its own grid, then continue after the bar
                t_end = min(L_main, (bar + 1) * bpb)
                _play_steps_x(hand, ctx, tk, gg, bar * bpb, t_end, shape_at, vel_at,
                              lambda t_, tok_: None, _token)
                i = int(round(t_end / g))
                continue
            tok = tk[i % n]
            if oc and tok == 'u' and round(t + g, 6) in changes and t - oc_last[0] >= 2 * bpb and nrng.random() < oc:
                oc_last[0] = t
                tok = '~'
            tt = max(0.0, _swung(t, g, swing) + _ms(ctx.timing_ms, b) * _tri(nrng) + _ms(ctx.late_ms, b))
            sh = shape_at(t)
            key_t = round(t, 4)
            if pending and (t >= pending['until'] - _EPS or sh is not pending['shape']):
                pending.clear()                        # the grace string was never picked: no hammer
            if key_t in orn_at and key_t not in done_orn and tok not in '.-' and picking \
                    and orn_at[key_t]['name'] in ('hammer_chord', 'sus4'):
                # a picked pattern: the grace note is played where the pattern picks its string, the finger
                # hammers on (sus2 -> 3rd) or pulls off (sus4 -> 3rd) half a step of the grid later
                done_orn.add(key_t)
                c = orn_at[key_t]
                gs = _grace_string(sh, 2 if c['name'] == 'hammer_chord' else 4, fb)
                if gs is not None:
                    s_, f0, f1 = gs
                    pre = sh._replace(frets=tuple(f0 if j == s_ else f for j, f in enumerate(sh.frets)),
                                      pitches=tuple(fb.open[s_] + f0 if j == s_ else q
                                                    for j, q in enumerate(sh.pitches)))
                    pending.update(s=s_, fretted=f1 != 0, pre=pre, shape=sh, until=t + 2.0, name=c['name'], t=t)
            if pending and sh is pending['shape']:
                before = sum(1 for ev in hand.ev if ev[1] == pending['s'])
                for part in tok.split('+'):
                    _token(hand, ctx, part, pending['pre'], tt, t, vel_at, g)
                if sum(1 for ev in hand.ev if ev[1] == pending['s']) > before:
                    s_ = pending['s']
                    hand.add(tt + max(g / 2, _ms(70, b)), s_, sh.pitches[s_], vel_at(t, 0.45), arts.get('hammer'), None,
                             pending['fretted'])
                    extra.append((pending['t'], t + g, 'ornament', pending['name']))
                    pending.clear()
                i += 1
                continue
            if key_t in orn_at and key_t not in done_orn and tok not in '.-':
                done_orn.add(key_t)
                c = orn_at[key_t]
                nxt_dt = next((k * g for k in range(1, n + 1) if tk[(i + k) % n] not in '.-'), 1.0)
                _ornament(hand, c['name'], sh, tt, t, b, fb, vel_at, nrng, arts, g, T, nxt_dt)
                extra.append((t, t + 1.0, 'ornament', c['name']))
            elif sh is not None:
                for part in tok.split('+'):
                    if part == '~':
                        opens = tuple(fb.open[s] if s in sh.strings[-3:] else None for s in range(6))
                        osh = Shape(tuple(0 if q is not None else None for q in opens), opens, 'open', 0, 0, 0, 0.0,
                                    'open')
                        _stroke(hand, osh, tt + _ms(2.0, b), up=True, vel=vel_at(t, 0.28) * 0.72, spread_ms=10.0,
                                rng=nrng,
                                onset=0.2, end=tt + _sec(0.1, b))
                        extra.append((t, t + g, 'ornament', 'open_change'))
                    else:
                        _token(hand, ctx, part, sh, tt, t, vel_at, g)
            i += 1
        notes = hand.notes(L_main)
        shapes_log = [(bounds[i], path[i]) for i in range(len(path))]
    # the fill into the next section
    if fill_kind is not None:
        a0 = L - fill_len
        cur = p.at(min(max(a0, 0.0), p.length - 1e-6)) if p.length else None
        cur_sh = shapes_log[-1][1] if shapes_log else (shape(cur, k_, fretboard=fb) if cur is not None else None)
        dn = T.get('down', 'all')
        if cur_sh is not None and dn != 'all':        # strings= also for the fill's strums
            cur_sh = _restrict(cur_sh, dn)
        sd = rng.randrange(1 << 30) if take is None else seed_int(f"{seed}:{take}:fill")
        if fill_kind == 'build' and cur_sh is not None:
            c = build(cur_sh, fill_len, b, vel=(lo * 0.85, min(124.0, hi * 1.08)), seed=sd)
        elif fill_kind == 'choke' and cur_sh is not None:
            c = choke(cur_sh, b, hold=min(0.75, fill_len / 2), vel=min(124.0, hi * 1.02), dead=arts.get('dead'),
                      seed=sd)
        elif fill_kind == 'bass_run' and cur is not None and nxt is not None:
            c = bass_run(cur, nxt, fill_len, b, key=key, notes=int(round(fill_len * 2)) if fill_len >= 2 else 2,
                         vel=(lo + hi) / 2, seed=sd)
            if cur_sh is not None:        # the chord keeps ringing on the treble strings under the walk
                top = strum(cur_sh, fill_len, b, strings='top3', vel=lo * 0.9, spread_ms=14.0, seed=sd)
                c = c | top
        elif fill_kind == 'slide_chord' and nxt is not None:
            kk = k_ if k_ in ('power', 'barre', 'upper') else 'power'
            try:
                target = shape(nxt, kk, fretboard=fb, near=cur_sh)
            except ComposeError:
                target = None
            c = Clip._raw((), 0)
            if target is not None:
                ms = min(140.0, 0.4 * 60000.0 / b)
                sl_b = _ms(ms, b)
                land = fill_len - 0.5                     # the slide lands on the & of 4 (a pushed change)
                if cur_sh is not None and land - sl_b > 0.2:
                    c = strum(cur_sh, land - sl_b - 0.02, b, vel=hi * 0.95, spread_ms=10.0, seed=sd)
                sl = slide_chord(target, 0.5 + sl_b, b, frm=-2, ms=ms, vel=hi, seed=sd, at=land - sl_b)
                c = c | sl
        else:
            c = Clip._raw((), 0)
        notes += [(n.start + a0, min(n.dur, L - (n.start + a0)), n.pitch, n.vel, _art.articulation_of(n))
                  for n in c if n.start + a0 < L - 1e-6]
        extra.append((a0, L, 'fill', fill_kind))
    return notes, shapes_log, pushes, extra


def _ornament(hand, name, sh, tt, t, b, fb, vel_at, rng, arts, g, T, nxt_dt: float = 1.0):
    """A chord-change ornament played into the hand at tt (instead of the step's token); nxt_dt = beats to the
    pattern's next stroke (a hammer-on lands before it, so that the hammered note is heard)."""
    v = vel_at(t, 1.0)
    dn = T.get('down', 'all')                     # strings= (an acoustic leaving the bass strings alone) holds here too
    if name in ('hammer_chord', 'sus4'):
        gs = _grace_string(sh, 2 if name == 'hammer_chord' else 4, fb)
        if gs is None:
            _stroke(hand, sh, tt, which=dn, vel=v, spread_ms=rng.uniform(*T.get('spread', (16, 30))), rng=rng)
            return
        s, f0, f1 = gs
        frets = list(sh.frets)
        frets[s] = f0
        ps = list(sh.pitches)
        ps[s] = fb.open[s] + f0
        pre = sh._replace(frets=tuple(frets), pitches=tuple(ps))
        _stroke(hand, pre, tt, which=dn, vel=v, spread_ms=rng.uniform(*T.get('spread', (16, 30))), rng=rng)
        hand.add(tt + min(max(g, 0.5) * 0.9, 0.6 * nxt_dt), s, sh.pitches[s], v * 0.72, arts.get('hammer'), None,
                 f1 != 0)
    elif name == 'slide_chord':
        movable = sh if not sh.open_strings else None
        if movable is None or movable.pos < 3:
            _stroke(hand, sh, tt, which=dn, vel=v, spread_ms=10.0, rng=rng)
            return
        total = _ms(90.0, b)
        t0 = max(0.0, tt - total)
        hand.cut(t0 - _ms(5.0, b), fretted_only=False)
        for i, off in enumerate((-2, -1, 0)):
            cur = sh._replace(frets=tuple(None if f is None else f + off for f in sh.frets),
                              pitches=tuple(None if q is None else q + off for q in sh.pitches))
            ti = t0 + total * i / 2
            _stroke(hand, cur, ti, which=dn, vel=v * (0.9, 0.4, 0.78)[i], spread_ms=8.0 if i == 0 else 3.0, rng=rng,
                    onset=0.0, end=None if i == 2 else ti + total / 2 + _ms(3, b))


# ------------------------------------------------------------------------------------------------ the lead arranger

def _finger(pitches: list[int], fb: Fretboard, lo: int = 3, hi: int = 17) -> list[tuple[int, int]]:
    """A fingering (string, fret) for a single line: the hand stays in a position (a shift costs, more when it is
    far), prefers the middle of the neck (lo..hi) and fretted notes (an open string cannot be bent or vibrated),
    solved over the whole line."""
    if not pitches:
        return []
    cands = []
    for p in pitches:
        c = fb.positions(p)
        if not c:
            q = p
            while q < fb.lowest:
                q += 12
            while q > fb.highest:
                q -= 12
            c = fb.positions(q) or [(0, 0)]
        cands.append(c)

    def own(sf):
        s, f = sf
        return (0.5 if f == 0 else 0.0) + (0.25 * (lo - f) if f < lo else 0.0) + (0.25 * (f - hi) if f > hi else 0.0)

    def move(a, b):
        (sa, fa), (sb, fb_) = a, b
        d = abs(fb_ - fa)
        c = max(0, d - 3) * 0.6 + 0.12 * min(d, 3)
        c += 0.25 * max(0, abs(sb - sa) - 1)
        return c
    best = [[(own(x), -1) for x in cands[0]]]
    for i in range(1, len(cands)):
        row = []
        for x in cands[i]:
            row.append(min((best[i - 1][j][0] + move(y, x) + own(x), j) for j, y in enumerate(cands[i - 1])))
        best.append(row)
    j = min(range(len(best[-1])), key=lambda k: best[-1][k][0])
    out = []
    for i in range(len(cands) - 1, -1, -1):
        out.append(cands[i][j])
        j = best[i][j][1]
    return out[::-1]


_LEAD_VIB = {'rock': 'rock', 'blues': 'blues', 'ballad': 'wide', 'pop': 'narrow', 'country': 'narrow',
             'jazz': 'subtle'}
"""lead(gestures=True): the fretwork.VIBRATOS style per LEAD_STYLES name."""


def _fw_bend(st0, e_, amt, rise_ms, rel, b, nxt, vstyle, rng) -> list:
    """lead(gestures=True): a bend as fretwork plays it (rise, overshoot, settle; a vibrato below the bent pitch)."""
    from . import fretwork as _fw
    pt = _fw.bend(0, max(0.1, e_ - st0), b, amount=amt, rise_ms=rise_ms, vib=vstyle,
                  release=None if rel is None else max(0.1, min(0.95, (rel - st0) / max(1e-6, e_ - st0))),
                  back=None if nxt is None else nxt - st0, seed=rng.randrange(1 << 30))
    return [g.shifted(st0) for g in pt.gestures]


def lead(melody, prog=None, *, bpm, key=None, style: str = 'rock', section=None, energy: float | None = None,
         density: float = 0.5, seed=0, touch: bool | tuple = True, sound=None, mono: bool | None = None,
         articulations=None, moves: dict | None = None, flash_every: float | None = None,
         spice_every: float | None = None, fast_every: float | None = None, same_every: float = 32.0,
         fill: float | None = None, climax: bool = False, vib=None, tuning='standard', capo: int = 0,
         fretboard=None, memory: Memory | None = None, at=None, gestures: bool = False,
         vib_style: str | None = None) -> Arrangement:
    """A lead guitarist's performance of a melody -> Arrangement (.clip, .auto = pitchbend / vibrato automation,
    .play(track, at) writes both, .moves).

    The line is fingered on the neck (a position that shifts as little as it can, the middle of the neck, fretted
    notes), given touch() phrase dynamics (touch=True: the style's range raised with the energy; (lo, hi); False =
    the written velocities) and played like a guitarist: notes PICKED (each a new attack: a small gap before the next
    note) except where the hand slurs - a hammer-on / pull-off between close notes on one string, a slide into a
    leap on one string, a scoop into a phrase (the legato ones tie, a mono='legato' sampler plays no new attack; on a
    polyphonic guitar the 'hammer-on' articulation or soft, emulated slides). Long notes get a finger vibrato (the
    style's depth / rate, delayed, growing); moves by context: a BEND into a long phrase-peak or phrase-end note (from
    a whole or half step below: pitchbend automation; a whole step only on the D, G, B, E strings, never on a written
    double stop), a PRE-BEND released into the next note a step below (pushed up silently in a rest of 120 ms or more
    before the note: the pitch wheel moves the whole track), a RAKE into an accented phrase start (rakes and scoops
    need room before their note), a DOUBLE STOP on a long chord tone (polyphonic sounds only), a TRILL or TREMOLO
    picking on a very long note (climax=True), a LICK (pentatonic, hammer / pull pairs) in a gap of 1.5+ beats.
    gestures=True: the pitch moves as agentsound.fretwork gestures instead of automation points (.gestures, .auto
    empty): bends with a fast rise, overshoot and settle and a vibrato below the bent pitch, pre-bends pushed silently
    before the pick, finger vibrato that goes UP from the note (vib_style: a fretwork.VIBRATOS name; default by style:
    rock 'rock', blues 'blues', ballad 'wide', pop / country 'narrow', jazz 'subtle') - .play(track) writes them via
    fretwork.render (one lane per target, mergeable with other fretwork parts: .part()).
    Budgets (song-wide with memory=): FLASH moves (bend, prebend, rake, double stop, lick) at most one per
    flash_every bars, SPICE (slide, hammer-on, pull-off, scoop) one per spice_every bars, FAST (trill, tremolo
    picking) one per fast_every bars (0 = never), two of a kind same_every bars apart - the best-placed first (a
    phrase end, the top of the line, a long note). Human timing (a few ms, laid back by style). Styles: LEAD_STYLES
    (rock, blues, ballad, pop, country, jazz); moves= overrides the weights. Deterministic by seed."""
    if style not in LEAD_STYLES:
        raise ComposeError(f"guitarist lead style must be one of {', '.join(LEAD_STYLES)}, got {style!r}")
    S = LEAD_STYLES[style]
    b = _bpm(bpm)
    dens = _num(density, 'lead density', 0, 1)
    sec_name = getattr(section, 'name', section)
    sk = _section_kind(sec_name)
    if at is None and hasattr(section, 'start') and not isinstance(section, str):
        at = float(section.start)
    e = SECTION_ENERGY[sk] if energy is None else _num(energy, 'lead energy', 0, 1)
    m = as_clip(melody)
    p = _as_prog(prog, key, m.length or 4.0) if prog is not None else None
    L = max(m.length, p.length if p is not None else 0.0)
    k = _key(key) if key is not None else (p.key if p is not None else None)
    bpb = p.beats_per_bar if p is not None else 4.0
    fb = _board(fretboard, tuning, capo)
    rng = random.Random(seed_int(seed))
    arts = _arts(sound, articulations)
    is_mono = _is_mono(sound) if mono is None else bool(mono)
    mw = dict(S['moves'] if moves is None else moves)
    for name in mw:
        if name not in FAST + FLASH + SPICE:
            raise ComposeError(f"unknown lead move {name!r}; use {', '.join(sorted(set(FAST + FLASH + SPICE)))}")
    if is_mono:
        mw.pop('double_stop', None)
    if not climax:
        mw.pop('tremolo_pick', None)
    base = _pos(at) if at is not None else (memory.clock if memory is not None else 0.0)
    # ---- dynamics
    if touch is not False:
        if touch is True:
            lo0, hi0 = S['touch']
            lift = (e - 0.5) * 16.0
            lo_, hi_ = max(30.0, lo0 + lift), min(124.0, hi0 + lift * 0.8)
        else:
            lo_, hi_ = _vels(touch)
        m = _touch(m, lo_, hi_)
    # ---- the line: the top note of each onset (lower notes given with it stay as double stops)
    ns = sorted(m, key=lambda n: (n.start, -n.pitch))
    line: list[list] = []
    given: list = []
    for n in ns:
        if line and abs(n.start - line[-1][0]) < 0.02:
            given.append(n)
            continue
        line.append([n.start, n.dur, n.pitch, float(n.vel), getattr(n, 'art', None)])
    if not line:
        return Arrangement(Clip._raw((), L), {}, [], energy=e, section=sec_name)
    fing = _finger([x[2] for x in line], fb)
    # line notes with a written lower note under them (a double stop the polyphonic guitar plays)
    partnered = set() if is_mono else {i for i, x in enumerate(line) if any(abs(n.start - x[0]) < 0.02 for n in given)}
    # phrases
    phr: list[list[int]] = []
    for i, x in enumerate(line):
        if not phr or x[0] - (line[i - 1][0] + line[i - 1][1]) >= 0.5 - _EPS:
            phr.append([i])
        else:
            phr[-1].append(i)
    ph_of = {i: pi for pi, ph in enumerate(phr) for i in ph}
    mel_hi = max(x[2] for x in line)
    mel_lo = min(x[2] for x in line)
    vmed = sorted(x[3] for x in line)[len(line) // 2]

    def chord_at(t):
        return p.at(min(max(t, 0.0), p.length - 1e-6)) if p is not None and p.length > 0 else None

    def pcs_at(t):
        c = chord_at(t)
        return _scale_pcs(c, k) if c is not None else _scale_pcs(None, k)

    def height(q):
        return (q - mel_lo) / max(1, mel_hi - mel_lo)

    def want(name, boost=1.0):
        w = mw.get(name, 0.0)
        return w > 0 and rng.random() < min(0.95, w / 3.0 * (0.45 + dens) * boost)
    cands: list[dict] = []
    for pi, ph in enumerate(phr):
        peak = max(ph, key=lambda i: (line[i][2], line[i][1]))
        for idx, i in enumerate(ph):
            s, d, q, v, _ = line[i]
            secs = d * 60.0 / b
            last = idx == len(ph) - 1
            first = idx == 0
            nxt = line[ph[idx + 1]] if not last else None
            gap_next = (nxt[0] - (s + d)) if nxt is not None else math.inf
            st, fr = fing[i]
            longn = d >= 1.0 - _EPS and secs >= 0.45
            score = 1.0 + 1.2 * last + 1.0 * (i == peak) + 0.8 * height(q) + 0.3 * min(d, 4.0) / 4.0 + 0.4 * climax
            # bends: never a written double stop (the partner would bend too), a whole step only on the D, G, B and
            # E strings (the wound low strings: a half step), the fretted note at the 2nd fret or higher (near the
            # nut the string is too stiff)
            bendable = i not in partnered
            max_amt = 2 if st >= 2 else 1
            # main moves: one per note
            if longn and fr >= 3 and bendable \
                    and want('bend', 4.0 if i == len(line) - 1 else 2.0 if (last or i == peak) else 0.6):
                amount = min(max_amt, 2 if (q - 2) % 12 in pcs_at(s) else 1)
                if fr - amount >= 2:
                    cands.append(dict(name='bend', cls='flash', t=s, score=score, slot=((i, 'main'),), i=i,
                                      amount=amount,
                                      release=last and rng.random() < 0.3))
            # a pre-bend: the string pushed up silently BEFORE the pick - the hand needs a moment for it (a rest of
            # 120 ms or more before the note), and nothing may slur into it (a tied note would jump with the bend)
            if i > 0:
                gap_prev = s - (line[i - 1][0] + line[i - 1][1])
            elif memory is not None and memory.lead_end is not None:
                gap_prev = base + s - memory.lead_end            # the previous part's last note
            else:
                gap_prev = math.inf
            if nxt is not None and 1 <= q - nxt[2] <= max_amt and d >= 0.5 - _EPS and nxt[1] >= 0.5 - _EPS \
                    and gap_next < 0.1 and fing[i + 1][0] == st and fr - (q - nxt[2]) >= 2 and bendable \
                    and (i + 1) not in partnered and gap_prev * 60.0 / b >= 0.12 and want('prebend'):
                cands.append(dict(name='prebend', cls='flash', t=s, score=score + 0.3,
                                  slot=((i, 'main'), (i, 'into'), (i, 'pre'), (i + 1, 'main'), (i + 1, 'into')), i=i,
                                  amount=q - nxt[2], gap_prev=gap_prev))
            if d >= 2.0 - _EPS and secs >= 1.0 and want('trill', 0.8 + climax):
                cands.append(dict(name='trill', cls='fast', t=s, score=score - 0.5, slot=((i, 'main'),), i=i))
            if d >= 2.0 - _EPS and secs >= 1.0 and climax and want('tremolo_pick'):
                cands.append(dict(name='tremolo_pick', cls='fast', t=s, score=score - 0.2, slot=((i, 'main'),), i=i))
            ch = chord_at(s)
            if longn and ch is not None and q % 12 in {(ch.root + x) % 12 for x in ch.intervals} \
                    and v >= vmed and want('double_stop'):
                cands.append(dict(name='double_stop', cls='flash', t=s, score=score - 0.2, slot=((i, 'main'),), i=i))
            # a rake / scoop happens BEFORE the note: it needs room in the part (a clip cannot start before 0)
            room = s - (line[i - 1][0] + line[i - 1][1]) if i > 0 else s
            if first and d >= 0.5 - _EPS and v >= vmed and (pi == 0 or room >= 0.75) and room >= _ms(80.0, b) \
                    and want('rake'):
                cands.append(dict(name='rake', cls='flash', t=s - 0.1, score=1.0 + 0.5 * height(q), slot=((i, 'pre'),),
                                  i=i))
            # connectors into the next note (spice)
            if nxt is not None and gap_next < 0.1 and fing[i + 1][0] == st:
                iv = nxt[2] - q
                if 1 <= abs(iv) <= 4 and d <= 0.75 + _EPS:
                    name = 'hammer_on' if iv > 0 else 'pull_off'
                    if want(name, 1.2):
                        cands.append(dict(name=name, cls='spice', t=nxt[0], score=0.8 + 0.2 * rng.random(),
                                          slot=((i + 1, 'into'),), i=i + 1))
                elif 2 <= abs(iv) <= 7 and want('slide'):
                    cands.append(dict(name='slide', cls='spice', t=nxt[0], score=0.9 + 0.2 * rng.random(),
                                      slot=((i + 1, 'into'),), i=i + 1))
            if first and d >= 1.0 - _EPS and fr >= 3 and room >= _sec(0.07, b) + 0.02 and want('scoop'):
                cands.append(dict(name='scoop', cls='spice', t=s, score=0.7 + 0.3 * height(q),
                                  slot=((i, 'into'), (i, 'pre')),
                                  i=i))
    # gap licks
    p_fill = min(1.0, (S['fill'] if fill is None else _num(fill, 'lead fill', 0, 1)) * (0.5 + dens))
    if mw.get('lick', 0) > 0:
        for pi in range(len(phr)):
            g0 = line[phr[pi][-1]][0] + line[phr[pi][-1]][1]
            g1 = line[phr[pi + 1][0]][0] if pi + 1 < len(phr) else L
            if g1 - g0 >= 1.5 - _EPS and rng.random() < p_fill and chord_at(g0) is not None:
                cands.append(dict(name='lick', cls='flash', t=g0, score=0.9 + 0.6 * (pi + 1 == len(phr)),
                                  slot=(f"gap{pi}",), gap=(g0, g1)))
    fe = S['flash_every'] if flash_every is None else _num(flash_every, 'lead flash_every', 0)
    se = S['spice_every'] if spice_every is None else _num(spice_every, 'lead spice_every', 0)
    fa = S['fast_every'] if fast_every is None else _num(fast_every, 'lead fast_every', 0)
    _budget(cands, memory, base, bpb, {'flash': fe, 'spice': se, 'fast': fa}, same_every)
    kept = [c for c in cands if c['keep']]
    by_note: dict = {}
    for c in kept:
        by_note.setdefault(c.get('i'), []).append(c)
    # ---- render
    gst: list = []
    vstyle = vib_style or _LEAD_VIB.get(style, 'rock')
    nrng = random.Random(f"{seed_int(seed)}:lead")
    tim = _ms(S['timing_ms'], b)
    late = _ms(S['late_ms'], b)
    pick_gap = _ms(14.0, b)
    out: list[tuple] = []
    pb: list = []
    mlog: list = []
    vib_notes: list = []
    skip = set()
    # legato phrasing (not a move, the style's singing): close notes in a phrase tied now and then - no new pick.
    # Only on one string (a hammer-on / pull-off within the hand's reach: <= 4 frets) and never out of a bent note
    # (the bend is released before the next note is picked)
    lrng = random.Random(f"{seed_int(seed)}:legato")
    slur = set()
    for ph in phr:
        for i, j in zip(ph, ph[1:]):
            gap_ = line[j][0] - (line[i][0] + line[i][1])
            busy = any(c['name'] in ('prebend', 'trill', 'tremolo_pick', 'double_stop', 'hammer_on', 'pull_off',
                                     'slide', 'scoop', 'rake') for c in by_note.get(j, []) + by_note.get(i, [])) \
                or any(c['name'] == 'bend' for c in by_note.get(i, []))
            if gap_ < 0.1 and 0 < abs(line[j][2] - line[i][2]) <= 4 and fing[i][0] == fing[j][0] and not busy \
                    and lrng.random() < S.get('legato', 0.0):
                slur.add(j)
    starts = [x[0] + (late + tim * _tri(nrng) if x[0] > 0 else max(0.0, late)) for x in line]
    for j in slur:
        starts[j] = line[j][0] + late * 0.5
    for i, (s, d, q, v, a_) in enumerate(line):
        if i in skip:
            continue
        cs = {c['name']: c for c in by_note.get(i, [])}
        st0 = starts[i]
        ph = phr[ph_of[i]]
        is_last = i == ph[-1]
        nxt_start = starts[i + 1] if not is_last else None
        into = next((c for c in cs.values() if c['name'] in ('hammer_on', 'pull_off', 'slide')), None)
        tie_next = (not is_last and (i + 1 in slur or any(c['name'] in ('hammer_on', 'pull_off', 'slide')
                                                          for c in by_note.get(i + 1, []))))
        if into is not None:
            st0 = s + late * 0.5                      # a slurred note sits where the finger lands, no pick jitter
            starts[i] = st0
        if nxt_start is not None:
            end = nxt_start + 0.03 if (tie_next and is_mono) else nxt_start - pick_gap
            if tie_next and not is_mono:
                end = nxt_start - _ms(3.0, b)
        else:
            end = s + d
        end = max(st0 + 0.05, end)
        vv = v
        art_ = a_
        glide = None
        if i in slur:
            vv = v * 0.9                              # tied: the finger, not the pick
            mlog.append((st0, st0, 'phrasing', 'legato'))
        if into is not None:
            vv = v * (0.8 if into['name'] != 'slide' else 0.86)
            if into['name'] in ('hammer_on', 'pull_off'):
                art_ = art_ or arts.get('hammer')
            elif is_mono:
                glide = float(min(140.0, max(50.0, 25.0 * abs(q - line[i - 1][2]))))
            else:                                     # a slide on a polyphonic guitar: the frets passed, softly
                prev = line[i - 1][2]
                stp = 1 if q > prev else -1
                mids = list(range(prev + stp, q, stp))[-3:]
                tot = _ms(70.0, b)
                for j, mq in enumerate(mids):
                    out.append((st0 - tot + tot * j / max(1, len(mids)), tot / max(1, len(mids)), mq, v * 0.32, None))
            mlog.append((st0, st0 + (end - st0), 'move', into['name']))
        if 'scoop' in cs:
            gl = _sec(0.07, b)
            gq = q - 2 if (q - 2) % 12 in pcs_at(s) else q - 1
            out.append((max(0.0, st0 - gl), gl + (0.02 if is_mono else -0.005), gq, v * 0.7, None))
            if is_mono:
                glide = 60.0
            mlog.append((st0 - gl, st0, 'move', 'scoop'))
        if 'rake' in cs:
            rk = rake(q, 0.25, b, strings=2 + int(nrng.random() < 0.5), ms=nrng.uniform(12, 20),
                      dead=arts.get('dead'), vel=vv, fretboard=fb)
            pre = [n for n in rk if n.pitch != q]
            dt = max(n.start for n in rk if n.pitch == q)
            for n in pre:
                out.append((max(0.0, st0 - dt + n.start), n.dur, n.pitch, n.vel, _art.articulation_of(n)))
            mlog.append((st0 - dt, st0, 'move', 'rake'))
        main = next((cs[x] for x in ('bend', 'prebend', 'trill', 'tremolo_pick', 'double_stop') if x in cs), None)
        if main is not None and main['name'] == 'bend':
            amt = main['amount']
            rise = _ms(nrng.uniform(80, 150), b)
            e_ = min(end, nxt_start - 0.04) if nxt_start is not None else end
            rel = st0 + (e_ - st0) * 0.65 if main.get('release') else None
            if gestures:
                gst += _fw_bend(st0, e_, amt, rise * 60000.0 / b, rel, b, nxt_start, vstyle, nrng)
            else:
                pb += _bend_pts(st0, e_, amt, rise, release=rel, fall=_ms(160, b) if rel else None)
                vib_notes.append(Note(st0, (rel or e_) - st0, q, _vel(vv)))
            out.append((st0, e_ - st0, q - amt, vv, art_, glide))
            mlog.append((st0, e_, 'move', 'bend'))
            continue
        if main is not None and main['name'] == 'prebend':
            amt = main['amount']
            nx = line[i + 1]
            e_ = starts[i + 1] + nx[1] if i + 1 < len(line) else end
            later = i + 2 < len(line) and ph_of.get(i + 2) == ph_of[i]
            if later:
                e_ = min(e_, starts[i + 2] - pick_gap)
            rel = starts[i + 1]
            # the silent push: half-way into the rest before the note (at most 60 ms early), after the previous
            # note has stopped
            pre_at = st0 - min(_ms(60.0, b), 0.5 * main.get('gap_prev', 0.04))
            if gestures:
                from . import gesture as _G
                gst.append(_G.bend(st0, e_ - st0, b, semis=amt, pre=max(0.005, (st0 - pre_at) * 60.0 / b),
                                   release=rel, release_ms=nrng.uniform(120, 200),
                                   back=starts[i + 2] if later else None))
            else:
                pb += _bend_pts(st0, e_, amt, 0.0, release=rel, fall=_ms(nrng.uniform(120, 200), b), pre=True,
                                pre_at=pre_at)
            out.append((st0, e_ - st0, q - amt, vv, art_))
            skip.add(i + 1)
            if nx[1] * 60.0 / b >= 0.6:
                vib_notes.append(Note(rel + _ms(200, b), e_ - rel - _ms(200, b), nx[2], _vel(nx[3])))
            mlog.append((st0, e_, 'move', 'prebend'))
            continue
        if main is not None and main['name'] == 'trill':
            c = trill(q, end - st0, b, chord=chord_at(s), key=k, rate=nrng.uniform(9.5, 12.5), legato=True,
                      art=arts.get('hammer'), vel=vv, seed=nrng.randrange(1 << 30), at=st0)
            out += [(n.start, n.dur, n.pitch, n.vel, _art.articulation_of(n)) for n in c]
            mlog.append((st0, end, 'move', 'trill'))
            continue
        if main is not None and main['name'] == 'tremolo_pick':
            c = tremolo_pick(q, end - st0, b, rate=nrng.uniform(11, 14), vel=vv, seed=nrng.randrange(1 << 30), at=st0)
            out += [(n.start, n.dur, n.pitch, n.vel) for n in c]
            mlog.append((st0, end, 'move', 'tremolo_pick'))
            continue
        if main is not None and main['name'] == 'double_stop':
            c = double_stop(q, end - st0, b, chord=chord_at(s), key=k, vel=vv, at=st0)
            out += [(n.start, n.dur, n.pitch, n.vel) for n in c if n.pitch != q]
            mlog.append((st0, end, 'move', 'double_stop'))
        out.append((st0, end - st0, q, vv, art_, glide))
        if (end - st0) * 60.0 / b >= 0.45 and end - st0 >= 0.75:
            vib_notes.append(Note(st0, end - st0, q, _vel(vv)))
    # given lower notes (written double stops) - a polyphonic guitar only
    if not is_mono:
        out += [(n.start, n.dur, n.pitch, n.vel * 0.9, getattr(n, 'art', None)) for n in given]
    # gap licks
    for c in kept:
        if c['name'] != 'lick':
            continue
        g0, g1 = c['gap']
        ln = min(2.0, g1 - g0 - 0.25)
        if ln < 0.75:
            continue
        a0 = g1 - 0.12 - ln
        ch = chord_at(g0)
        nxt_q = next((line[i][2] for i in range(len(line)) if line[i][0] >= g1 - _EPS), line[-1][2])
        st_q = max(55, min(88, nxt_q + nrng.choice((3, 5, 7))))
        lk = lick(ch, ln, b, start=st_q, direction='down', notes=nrng.choice((4, 5, 6)), key=k, legato=True,
                  art=arts.get('hammer'), vel=(vmed * 0.95, vmed * 0.8), seed=nrng.randrange(1 << 30), at=a0)
        prev_end = a0
        lk_ns = sorted(lk, key=lambda n: n.start)
        for j, n in enumerate(lk_ns):
            slur = _art.articulation_of(n) is not None or (j % 2 == 1)
            d_ = n.dur
            if j + 1 < len(lk_ns) and not is_mono:
                d_ = min(d_, lk_ns[j + 1].start - n.start - _ms(3, b))
            out.append((n.start, max(0.03, d_), n.pitch, n.vel, _art.articulation_of(n)))
            prev_end = n.start + d_
        del prev_end
        mlog.append((a0, g1, 'fill', 'lick'))
    # vibrato automation on the long notes
    auto: dict = {}
    if pb:
        auto['instrument.pitchbend'] = sorted(pb, key=lambda x: x[0])
    vd, vr = S['vib'] if vib is None else vib
    if gestures and vib_notes and vd > 0:
        from . import fretwork as _fw
        for n in vib_notes:
            gst.append(_fw._vib(n.start, n.dur, b, vstyle, seed=seed_int(seed) + 11, scale=0.85 + 0.3 * e))
        mlog += [(n.start, n.start + n.dur, 'vibrato', 'vibrato') for n in vib_notes]
    elif vib_notes and vd > 0:
        vc = Clip._raw(sorted(vib_notes), L)
        vp = _art.vibrato_points(vc, b, depth=vd * (0.85 + 0.3 * e), rate=vr, delay=0.28, min_dur=0.75,
                                 seed=seed_int(seed) + 11)
        auto.update(vp)
        mlog += [(n.start, n.start + n.dur, 'vibrato', 'vibrato') for n in vib_notes]
    for c in cands:
        if not c['keep']:
            mlog.append((c['t'], c['t'], 'dropped', c['name']))
    clip_end = min(L, max((x[0] + x[1] for x in out), default=0.0))
    if memory is not None:
        for c in kept:
            memory.events.append((base + c['t'], c['cls'], c['name']))
        memory.clock = base + L
        memory.sections.append((sec_name, e))
        if clip_end > 0:
            memory.lead_end = base + clip_end
    budget = {'flash_every': fe, 'spice_every': se, 'fast_every': fa,
              'kept': [(round(c['t'], 4), c['name']) for c in sorted(kept, key=lambda c: c['t'])],
              'dropped': [(round(c['t'], 4), c['name']) for c in sorted(cands, key=lambda c: c['t']) if not c['keep']]}
    clip = _clip(out, L)
    return Arrangement(clip, auto, sorted(mlog, key=lambda m: (m[0], m[2])), budget=budget, energy=round(e, 3),
                       technique=f"lead:{style}", section=sec_name, gestures=gst)


def vocabulary(style: str = 'rock', **kw):
    """The lead guitar's solo vocabulary for agentsound.soloist (agentsound.guitar_vocab.vocabulary): phrases built
    from agentsound.fretwork's techniques - bends, vibrato, legato, picking, tone moves - and lead(gestures=True)'s
    phrasing, weighted by style ('rock', 'blues', 'ballad', 'fusion').

        perf = soloist.solo(s, lead, gtr.vocabulary('rock'), at=solo, prog=PROG, motif=HOOK, seed=7)"""
    from .guitar_vocab import vocabulary as _v
    return _v(style, **kw)
