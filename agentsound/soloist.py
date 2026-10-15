"""The soloist: one instrument-agnostic wrapper that builds a SOLO with a dramatic arc out of any player's vocabulary.

A solo is not a scale run. It has a shape (Gilmour, Gary Moore, Satriani, a sax break, a drum solo alike): a low,
sparse statement of a motif -> call and response -> the motif repeated and varied, sequenced up -> a speed burst ->
the climax at the top of the range -> a resolution, low, on a long note. It develops the song's hook instead of
noodling, leaves SPACE (rests are planned, not left over), keeps tricks as spice (one budget: agentsound.budget -
HUMAN_FEEDBACK "zu viele von diesen schnellen Zwei-Tasten-Wechseln"), and its dynamics follow the arc and are never
flat. The instrument lives in a Vocabulary (its moves, its motif maker, its variations, how its parts are written on a
track); the soloist only plans:

    from agentsound import soloist, guitarist as gtr
    perf = soloist.solo(s, lead, gtr.vocabulary(style='rock'), at=solo, prog=PROG, motif=HOOK, seed=7)
    print(perf.summary(), perf.stages, perf.warnings, perf.budget)

The interface (docs/COMPOSE_API.md "The soloist") - other players implement it:
    Move(name, beats, energy, density, spice, play, *, fast=False, roles=(), weight=1.0)
    Vocabulary(moves, motif=None, vary=None, *, name='', place=None, register=(0, 1), vel=(56, 118), phrase_bars=2,
               touch=True, budget=None, range=(48, 84), rest=1.0)
    Ctx            what play / motif / vary get (the slot, the arc here, the harmony, the motif, the budget ...)
    Part(clip, gestures=(), log=(), tricks=(), steps=None, aux=None)   what a move played
    solo(song, track, vocab, at=..., arc='classic', motif=None, budget=None, seed=None, *, prog=None, key=None,
         energy=None, place=True) -> Performance
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable

from .budget import Budget as _Budget
from .patterns import Clip, Note, as_clip, seed_int
from .theory import ComposeError, Key
from .theory import clash as _clash

__all__ = ['Move', 'Vocabulary', 'Ctx', 'Part', 'Performance', 'Budget', 'ARCS', 'STAGES', 'solo', 'vary', 'develop',
           'DEVELOPMENTS', 'phrase_spans', 'key_of', 'chord_tones', 'pentatonic', 'scale', 'snap', 'step', 'fold', 'fit',
           'center', 'seconds', 'grid', 'vel', 'merge', 'trick', 'motif_in_register', 'answer_line', 'target_line',
           'run_line', 'transform', 'motif_cell', 'motif_line', 'MOTIVIC', 'CELL_MOVES', 'RUNS',
           'BREATH', 'CONTRAST', 'PHRASES', 'LICKS', 'fresh', 'lick_ledger']

_EPS = 1e-6


# ------------------------------------------------------------------------------------------------ the interface

@dataclass(frozen=True)
class Move:
    """One thing a player can do in a solo. beats: the length it wants (0 = it fills the slot it is given); energy /
    density 0..1 (the arc picks moves near its stage's values); spice: a trick the budget counts (fast=True: the rarest
    kind - bursts, trills, rolls); roles: where it fits ('motif' 'answer' 'fill' 'develop' 'burst' 'climax'
    'resolve'; () = anywhere); play(ctx) -> Part | Clip | [notes] (relative to ctx.at); weight: how readily it is
    chosen."""
    name: str
    beats: float
    energy: float
    density: float
    spice: bool
    play: Callable
    fast: bool = False
    roles: tuple = ()
    weight: float = 1.0

    def __post_init__(self):
        for k in ('energy', 'density'):
            v = getattr(self, k)
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                raise ComposeError(f"Move {self.name!r}: {k} must be 0..1, got {v!r}")
        if not isinstance(self.beats, (int, float)) or self.beats < 0:
            raise ComposeError(f"Move {self.name!r}: beats must be >= 0, got {self.beats!r}")
        if not callable(self.play):
            raise ComposeError(f"Move {self.name!r}: play must be a function play(ctx)")
        if self.fast and not self.spice:
            raise ComposeError(f"Move {self.name!r}: a fast move is spice too (spice=True)")
        bad = [r for r in self.roles if r not in ROLES]
        if bad:
            raise ComposeError(f"Move {self.name!r}: unknown role(s) {bad}; roles: {', '.join(ROLES)}")


ROLES = ('motif', 'answer', 'fill', 'develop', 'burst', 'climax', 'resolve', 'chords')


class Part:
    """What a move played: clip (the notes, relative to the move's start), gestures (agentsound.gesture.Gesture on the
    abstract lanes, relative), log [(start, end, kind, name)], tricks [(beat, name, fast)] (spice inside the move,
    booked in the budget), steps {param: [(beat, value)]} (latched per-note params: a guitar's bendfollow,
    harmonicnum), aux {role: Clip} (notes for a helper track: the guitar's noise track)."""

    __slots__ = ('clip', 'gestures', 'log', 'tricks', 'steps', 'aux')

    def __init__(self, clip=None, gestures=(), log=(), tricks=(), steps=None, aux=None):
        self.clip = as_clip(clip) if clip is not None else Clip.rest(0)
        self.gestures = list(gestures)
        self.log = list(log)
        self.tricks = list(tricks)
        self.steps = {k: list(v) for k, v in (steps or {}).items()}
        self.aux = {k: as_clip(v) for k, v in (aux or {}).items()}

    def __repr__(self) -> str:
        return f"Part({len(self.clip)} notes, {len(self.gestures)} gestures, {len(self.tricks)} tricks)"

    @staticmethod
    def of(x) -> 'Part':
        if isinstance(x, Part):
            return x
        if x is None:
            return Part()
        return Part(as_clip(x))

    def shifted(self, by: float) -> 'Part':
        p = Part(self.clip.shift(by) if by else self.clip, [g.shifted(by) for g in self.gestures],
                 [(a + by, b + by) + tuple(r) for a, b, *r in self.log], [(t + by,) + tuple(r) for t, *r in self.tricks],
                 {k: [(t + by,) + tuple(r) for t, *r in v] for k, v in self.steps.items()},
                 {k: (c.shift(by) if by else c) for k, c in self.aux.items()})
        return p

    def merge(self, other: 'Part') -> 'Part':
        """Both parts together (same origin)."""
        notes = list(self.clip) + list(other.clip)
        L = max(self.clip.length, other.clip.length)
        steps = {k: list(v) for k, v in self.steps.items()}
        for k, v in other.steps.items():
            steps.setdefault(k, []).extend(v)
        aux = dict(self.aux)
        for k, c in other.aux.items():
            aux[k] = Clip._raw(sorted(list(aux[k]) + list(c)), max(aux[k].length, c.length)) if k in aux else c
        return Part(Clip._raw(sorted(notes), L), self.gestures + other.gestures, self.log + other.log,
                    self.tricks + other.tricks, steps, aux)


class Vocabulary:
    """A player's vocabulary for solo(): moves (Move list), motif(ctx) -> Clip (a motif when the solo gets none),
    vary(motif, ctx) -> Clip (default soloist.vary), place(track, perf) (writes the parts: default the notes + the
    gestures through agentsound.hornist.render), register (lo, hi) share of the instrument's range the arc may use,
    vel (lo, hi) the velocity range of the whole solo (the arc moves inside it), phrase_bars, touch (re-shape a flat
    phrase's velocities: humanize.touch), budget (its default Budget: spice_every / fast_every / same_every bars),
    rest (0..1: scales every stage's planned space at the phrase ends - 1 for a wind player who breathes, ~0.4 for
    a drummer, whose feet keep the pulse through the space), lines (True: a melodic player - the solo() line rules
    apply: free phrasing across the bar grid, the motif quoted literally at most twice, no verbatim bar repeats, no
    octave wraps in fast lines, shaped run dynamics; False: a drummer - the pitches are drum pieces, the phrases
    follow the phrase_bars grid)."""

    def __init__(self, moves, motif=None, vary=None, *, name: str = '', place=None, register=(0.0, 1.0),
                 vel=(56, 118), phrase_bars: float = 2, touch: bool = True, budget=None, range=(48, 84),
                 rest: float = 1.0, lines: bool = True):
        self.moves = list(moves)
        if not self.moves:
            raise ComposeError("Vocabulary needs at least one Move")
        for m in self.moves:
            if not isinstance(m, Move):
                raise ComposeError(f"Vocabulary moves must be soloist.Move, got {m!r}")
        names = [m.name for m in self.moves]
        if len(set(names)) != len(names):
            raise ComposeError(f"Vocabulary move names must be unique: {names}")
        self.motif, self.vary, self.place = motif, vary, place
        self.name = name
        self.register = (float(register[0]), float(register[1]))
        self.vel = (float(vel[0]), float(vel[1]))
        if not 1 <= self.vel[0] < self.vel[1] <= 127:
            raise ComposeError(f"Vocabulary vel must be (lo, hi) in 1..127, got {vel!r}")
        self.phrase_bars = float(phrase_bars)
        if self.phrase_bars <= 0:
            raise ComposeError("Vocabulary phrase_bars must be > 0")
        self.touch = bool(touch)
        if isinstance(rest, bool) or not isinstance(rest, (int, float)) or not 0.0 <= rest <= 1.0:
            raise ComposeError(f"Vocabulary rest must be 0..1 (a share of the stages' planned space), got {rest!r}")
        self.rest = float(rest)
        self.lines = bool(lines)
        self.budget = budget
        from .theory import note as _note
        self.range = (_note(range[0]), _note(range[1]))
        if not 0 <= self.range[0] < self.range[1] - 11 <= 116:
            raise ComposeError(f"Vocabulary range must be (lo, hi) spanning an octave+ in MIDI 0..127, got {range!r}")

    def __repr__(self) -> str:
        return f"Vocabulary({self.name or 'player'}: {', '.join(m.name for m in self.moves)})"

    def move(self, name: str) -> Move:
        for m in self.moves:
            if m.name == name:
                return m
        raise ComposeError(f"{self!r} has no move {name!r}")


class Budget(_Budget):
    """The soloist's budget (agentsound.budget.Budget): spice moves at most one per spice_every bars, fast moves one
    per fast_every bars (and only in the burst / climax stages), one name same_every bars apart. save(beat) keeps
    the fast budget for a moment. Pass one Budget to several solo() calls to count song-wide."""

    def __init__(self, spice_every: float = 1.5, fast_every: float = 8.0, same_every: float = 16.0, bpb: float = 4.0):
        self.bars = dict(spice_every=float(spice_every), fast_every=float(fast_every), same_every=float(same_every))
        self.bpb = float(bpb)
        super().__init__({'spice': spice_every * bpb, 'fast': fast_every * bpb}, same_every=same_every * bpb,
                         same=('spice', 'fast'))

    def __repr__(self) -> str:
        return (f"soloist.Budget(spice {self.bars['spice_every']:g} / fast {self.bars['fast_every']:g} / same "
                f"{self.bars['same_every']:g} bars; {len(self.events)} booked)")


class Ctx:
    """What a move's play(ctx) (and motif / vary) gets: song, track, vocab, at (song beat), beats (the slot, the rest
    excluded), bpm, bpb, key, prog (the progression, from the solo's start) and chord(t=None) (the chord at a song
    beat), stage, role ('call' | 'response' | 'fill' | 'lead'), energy, density (0..1 here), register (0..1: low
    statement .. the top at the climax), vel ((lo, hi) of this phrase), motif (the current Clip), phrase, phrases,
    progress (0..1), last (the last Note played, absolute), next_at (where the next slot starts, None at the end),
    rng, budget, memory (a dict the vocabulary keeps for the whole solo), solo_start, phrase_start (song beats),
    phrase_beats, range ((lo, hi) MIDI: the vocabulary's). The material helpers below (chord_tones, pentatonic,
    center, fit, answer_line, target_line, transform, run_line, ...) take a Ctx."""

    range = (48, 84)
    last = None
    next_at = None

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def chord(self, t=None):
        p = self.prog
        if p is None:
            return None
        x = (self.at if t is None else float(t)) - self.solo_start
        if p.length <= 0:
            return None
        return p.at(min(max(x, 0.0), p.length - 1e-6) % p.length)

    def __repr__(self) -> str:
        return (f"Ctx({self.stage}/{self.role} at {self.at:g} for {self.beats:g} beats, energy {self.energy:.2f}, "
                f"density {self.density:.2f}, register {self.register:.2f})")


# ------------------------------------------------------------------------------------------------ the arc

STAGES = {
    'statement': dict(energy=0.35, density=0.3, register=0.2, rest=0.4, plan='state'),
    'answer': dict(energy=0.5, density=0.45, register=0.4, rest=0.3, plan='call_response'),
    'develop': dict(energy=0.62, density=0.55, register=0.58, rest=0.25, plan='vary_response'),
    'burst': dict(energy=0.85, density=0.92, register=0.72, rest=0.1, plan='burst'),
    'climax': dict(energy=1.0, density=0.5, register=1.0, rest=0.18, plan='climax'),
    'resolve': dict(energy=0.4, density=0.3, register=0.25, rest=0.3, plan='resolve'),
    'trade': dict(energy=0.6, density=0.55, register=0.5, rest=0.25, plan='call_response'),
    'space': dict(energy=0.45, density=0.35, register=0.45, rest=0.5, plan='call_response'),
    'chords': dict(energy=0.75, density=0.5, register=0.7, rest=0.2, plan='chords'),
    'swap': dict(energy=0.6, density=0.5, register=0.5, rest=0.0, plan='call_response'),
}
"""Arc stages: energy, density (0..1), register (0..1 of the vocabulary's range), rest (share of the phrase left
silent at its end: space), plan - how a phrase is cut into slots: state (the motif, then space), call_response
(the motif's head as the call, a move answering it), vary_response (the motif varied / sequenced, then a move), burst
(one dense move), climax (the biggest move, at the top), resolve (the motif's head low, then a move landing on a long
last note), chords (one move for the 'chords' role: a block-chord chorus). 'space' leaves long gaps (less is more);
'swap' trades 4-bar phrases with the left hand (_free_phrases: the right hand plays 4 bars, the next 4 are
Performance.trades - the vocabulary's place() gives them to its other hand)."""

ARCS = {
    'classic': (('statement', 0.18, True), ('answer', 0.2, False), ('develop', 0.2, False), ('burst', 0.16, False),
                ('climax', 0.14, True), ('resolve', 0.12, True)),
    'build': (('statement', 0.2, True), ('develop', 0.3, False), ('burst', 0.25, False), ('climax', 0.25, True)),
    'ballad': (('statement', 0.25, True), ('answer', 0.25, False), ('develop', 0.2, False), ('climax', 0.15, True),
               ('resolve', 0.15, True)),
    'trade': (('trade', 1.0, True),),
    'short': (('statement', 0.35, True), ('climax', 0.4, True), ('resolve', 0.25, True)),
    'jazz': (('statement', 0.12, True), ('answer', 0.14, False), ('develop', 0.26, False), ('burst', 0.13, False),
             ('climax', 0.14, True), ('answer', 0.08, False), ('resolve', 0.13, True)),
    # solo shapes without a fixed double-time stage (the endless genres draw one per tune and insert a 'burst' only
    # sometimes, wherever it is drawn): a straight rise, a slow build, an answer-and-develop arch, less is more, a
    # block-chord chorus - each climbing to its climax in the last stretch and coming down from it (blind round 6:
    # the composed solos peak in their last 8-16 bars, a ladder over the head's top, then a descent) -, trading 4s
    'rise': (('statement', 0.25, True), ('develop', 0.4, False), ('climax', 0.25, True), ('resolve', 0.1, True)),
    'slow': (('statement', 0.3, True), ('answer', 0.25, False), ('develop', 0.25, True), ('climax', 0.12, True),
             ('resolve', 0.08, True)),
    'early': (('statement', 0.15, True), ('answer', 0.2, True), ('develop', 0.3, True), ('climax', 0.22, True),
              ('resolve', 0.13, True)),
    'sparse': (('statement', 0.3, True), ('space', 0.4, True), ('develop', 0.15, False), ('climax', 0.1, True),
               ('resolve', 0.05, True)),
    'chords': (('statement', 0.25, True), ('develop', 0.25, False), ('chords', 0.35, True), ('resolve', 0.15, True)),
    'trade4': (('swap', 1.0, True),),
}
"""Arcs: (stage, share of the solo's phrases, required) in order. A required stage gets at least one phrase. 'jazz':
the line gets denser chorus-long and peaks once about two thirds in, then talks itself down (a jazz chorus). solo()
also takes such a tuple itself (a shape built per tune)."""


def _arc(arc) -> tuple:
    """An arc's stages: an ARCS name or a tuple of (stage, share, required)."""
    if isinstance(arc, str):
        if arc not in ARCS:
            raise ComposeError(f"solo arc must be one of {', '.join(ARCS)} or a tuple of stages, got {arc!r}")
        return ARCS[arc]
    st = tuple(tuple(x) for x in arc)
    if not st or any(len(x) != 3 or x[0] not in STAGES or not x[1] > 0 for x in st):
        raise ComposeError(f"solo arc: a tuple of (stage, share > 0, required) with stages {', '.join(STAGES)}")
    return st


def phrase_spans(spans, phrase_bars: float) -> list:
    """[(start beat, beats, bpb)] for spans [(start, bars, bpb)] cut into phrases of phrase_bars bars (a shorter
    rest phrase of at least one bar joins its neighbour)."""
    out = []
    for start, bars, bpb in spans:
        n = max(1, int(round(bars / phrase_bars)))
        edges = [round(k * bars / n) for k in range(n + 1)]
        for a, b in zip(edges, edges[1:]):
            if b > a:
                out.append((start + a * bpb, (b - a) * bpb, bpb))
    return out


def _stages(arc, n: int) -> list:
    st = _arc(arc)
    counts = [max(1 if req else 0, int(round(sh * n))) for _, sh, req in st]
    while sum(counts) > n:
        # take from the largest optional stage, then from the largest required one (keeping 1)
        opt = [i for i, (_, _, req) in enumerate(st) if not req and counts[i] > 0]
        pool = opt or [i for i in range(len(st)) if counts[i] > 1] or [i for i in range(len(st)) if counts[i] > 0]
        i = max(pool, key=lambda k: (counts[k], -k))
        counts[i] -= 1
    while sum(counts) < n:
        i = max(range(len(st)), key=lambda k: (st[k][1] * n - counts[k], -k))
        counts[i] += 1
    out = []
    for (name, _, _), c in zip(st, counts):
        out += [name] * c
    return out


# ------------------------------------------------------------------------------------------------ motivic development

def _key(key) -> Key | None:
    if key is None or isinstance(key, Key):
        return key
    return Key(key)


def develop(motif, how: str, *, key=None, steps: int = 1, beats: float | None = None, by: float = 0.5,
            factor: float = 2.0) -> Clip:
    """One development of a motif (a Clip from 0): 'repeat', 'sequence' (diatonic transposition by `steps` scale
    steps: key=), 'invert' (diatonically, around its first note), 'retrograde', 'fragment' (its first `beats`, default
    half), 'tail' (its last half), 'displace' (shifted `by` beats later: the same notes, a new accent), 'augment'
    (x factor longer), 'diminish' (x 1/factor), 'octave' (`steps` octaves), 'answer' (the head, then sequenced down to
    end a step lower). DEVELOPMENTS lists them."""
    c = as_clip(motif)
    if not len(c):
        return c
    k = _key(key)
    if how == 'repeat':
        return c
    if how == 'sequence':
        return c.transpose_scale(int(steps), k) if k is not None else c.transpose(2 * int(steps))
    if how == 'invert':
        return c.invert(pivot=min(c, key=lambda n: n.start).pitch, key=k) if k is not None else c.invert()
    if how == 'retrograde':
        return c.retrograde()
    if how == 'fragment':
        b = c.length / 2.0 if beats is None else float(beats)
        out = c.slice(0, b)
        return out if len(out) else c
    if how == 'tail':
        b = c.length / 2.0
        out = c.slice(b).shift(-b) if len(c.slice(b)) else c
        return out
    if how == 'displace':
        return Clip._raw([n._replace(start=n.start + by) for n in c], c.length + by)
    if how == 'augment':
        return c.stretch(factor)
    if how == 'diminish':
        return c.stretch(1.0 / factor)
    if how == 'octave':
        return c.transpose(12 * int(steps))
    if how == 'answer':
        h = develop(c, 'fragment', beats=beats)
        return h + develop(h, 'sequence', key=key, steps=-1)
    raise ComposeError(f"develop: unknown development {how!r}; use {', '.join(DEVELOPMENTS)}")


DEVELOPMENTS = ('repeat', 'sequence', 'invert', 'retrograde', 'fragment', 'tail', 'displace', 'augment', 'diminish',
                'octave', 'answer')

_VARY = {'statement': (('displace', 2.0), ('tail', 1.0), ('sequence', 1.0)),
         'answer': (('fragment', 2.0), ('displace', 1.0), ('answer', 1.0)),
         'develop': (('sequence', 3.0), ('invert', 1.0), ('displace', 1.0), ('tail', 1.0)),
         'trade': (('sequence', 2.0), ('fragment', 1.0), ('invert', 1.0)),
         'swap': (('sequence', 2.0), ('fragment', 1.0), ('invert', 1.0)),
         'space': (('sequence', 2.0), ('invert', 1.0), ('augment', 1.0), ('displace', 1.0)),
         'chords': (('sequence', 2.0), ('displace', 1.0), ('invert', 0.5)),
         'burst': (('diminish', 2.0), ('sequence', 1.0)),
         'climax': (('octave', 2.0), ('sequence', 2.0), ('augment', 1.0)),
         'resolve': (('fragment', 2.0), ('augment', 1.0))}


def vary(motif, ctx) -> Clip:
    """The default variation of a motif for ctx.stage (seeded by ctx.rng): the statement displaces it (or keeps its
    tail, or sequences it), the answer fragments it, the development sequences it UP by one or two scale steps (or
    inverts it), the climax lifts it an octave or sequences it high, the resolution keeps its head - and every variation
    is made new by transform() (re-fitted to the chords it meets, a new ending: a motif is quoted literally once or
    twice, never as a loop). The vocabulary's own play folds it into the stage's register."""
    c = as_clip(motif)
    opts = _VARY.get(ctx.stage, (('displace', 1.0),))
    r = ctx.rng.random() * sum(w for _, w in opts)
    how = opts[-1][0]
    for name, w in opts:
        r -= w
        if r <= 0:
            how = name
            break
    steps, by = 1, 0.5
    if how == 'sequence':
        steps = 1 + (ctx.phrase % 2) if ctx.stage != 'climax' else 2
    elif how == 'displace':                              # a new accent each time: an 8th .. a beat and a half later
        by = ctx.rng.choice((0.5, 1.0, 1.5))
    return transform(develop(c, how, key=ctx.key, steps=steps, by=by), ctx, displace=how != 'displace')


def _sgn(x) -> int:
    return (x > 0) - (x < 0)


def transform(motif, ctx, *, displace: bool = True) -> Clip:
    """A motif quote made new (after the first literal one or two): displaced by an 8th .. a beat and a half (new
    accents; displace=False keeps its place), RE-FITTED to the chords it now meets at ctx.at (strong notes - on a beat
    or a dotted 8th+ - onto a chord tone, the others onto the chord's scale - scale() - every step in the motif's own
    direction: its contour stays recognisable) and given a NEW ENDING (its last note moved to another chord tone near
    it, the same way, held shorter or longer, now and then approached by a half step into a note on the beat) - the
    same idea, never the same bar twice and never the old notes over a new chord."""
    c = as_clip(motif)
    if not len(c):
        return c
    rng = ctx.rng
    lo_, hi_ = getattr(ctx, 'range', (0, 127))
    by = rng.choice((0.5, 1.0, 1.5, 0.5)) if displace else 0.0
    room = float(getattr(ctx, 'beats', c.length + by) or (c.length + by))
    t0 = min(n.start for n in c)                         # from its first note (a fragment may open with a rest)
    ns = [n._replace(start=n.start - t0 + by) for n in sorted(c)]
    ns = [n for n in ns if n.start < room - 0.25 - _EPS] or [sorted(c)[0]._replace(start=0.0)]
    out = []
    for i, n in enumerate(ns):
        t = ctx.at + n.start
        tones = chord_tones(ctx, t)
        strong = abs(t - round(t)) < _EPS or n.dur >= 0.75 - _EPS
        pcs = tones if strong else (scale(ctx, t) | tones)
        if i:                                            # the contour is kept: every step the motif's direction
            d = n.pitch - ns[i - 1].pitch
            want = out[-1].pitch + d
            # (a repeated note an 8th or less after the last becomes a neighbour: no unisons inside a line)
            same = d == 0 and n.start - ns[i - 1].start <= 0.55
            cand = [q for q in range(want - 4, want + 5) if q % 12 in pcs and
                    (q != out[-1].pitch if same else _sgn(q - out[-1].pitch) == _sgn(d))]
            q = min(cand, key=lambda q: (abs(q - want), q)) if cand else snap(want, pcs, rng.choice((-1, 1)))
        else:
            q = snap(n.pitch, pcs, rng.choice((-1, 1)))
        out.append(n._replace(pitch=q if lo_ <= q <= hi_ or not lo_ <= n.pitch <= hi_ else
                              snap(n.pitch, pcs, -1 if q > hi_ else 1)))
    last = out[-1]
    tones = chord_tones(ctx, ctx.at + last.start)
    d_last = ns[-1].pitch - ns[-2].pitch if len(ns) >= 2 else 0
    alt = [p for p in range(last.pitch - 5, last.pitch + 6) if p % 12 in tones and p != last.pitch
           and (len(out) < 2 or (p != out[-2].pitch and _sgn(p - out[-2].pitch) == _sgn(d_last)))
           and (lo_ <= p <= hi_ or not lo_ <= last.pitch <= hi_)]
    np_ = min(alt, key=lambda p: (abs(p - last.pitch) + rng.random() * 2.5)) if alt else last.pitch
    dur = held(min(room - last.start, last.dur * rng.choice((0.5, 1.5, 2.0)) + 0.25))
    out[-1] = last._replace(pitch=np_, dur=dur)
    t_last = ctx.at + out[-1].start                      # (a chromatic approach only into a note on the beat)
    if len(out) >= 2 and rng.random() < 0.35 and out[-1].start - (out[-2].start + 0.5) >= 0.5 - _EPS \
            and abs(t_last - round(t_last)) < _EPS:
        out.insert(-1, last._replace(start=out[-1].start - 0.5, dur=0.5, pitch=np_ + rng.choice((-1, 1)),
                                     vel=max(1, int(last.vel * 0.85))))
    out = sorted(out)                                    # (inside the range: a line wider than it turns at its edge)
    if hasattr(ctx, "range"):
        out = [n._replace(pitch=q) for n, q in zip(out, fit([n.pitch for n in out], ctx))]
    return Clip._raw(out, max(c.length + by, max(n.start + n.dur for n in out)))


# ------------------------------------------------------------------------------------------------ the result

class Performance:
    """What solo() played: start / end (song beats), parts [(beat, stage, role, move, Part)] (Parts at song beats),
    clip (all notes, relative to start), gestures (song beats), moves [(start, end, stage, name)], stages [(stage,
    start, end, energy)], budget ({'kept': [(beat, name)], 'dropped': [(beat, name, substitute)], every bars}),
    warnings, summary()."""

    def __init__(self, start: float, end: float):
        self.start, self.end = start, end
        self.parts: list = []
        self.moves: list = []
        self.stages: list = []
        self.warnings: list = []
        self.budget: dict = {'kept': [], 'dropped': []}
        self.trades: list = []          # [(start, end)]: bars the right hand leaves to the other hand (trading 4s)

    @property
    def clip(self) -> Clip:
        notes = sorted(n._replace(start=n.start - self.start) for _, _, _, _, p in self.parts for n in p.clip)
        return Clip._raw(notes, self.end - self.start)

    @property
    def gestures(self) -> list:
        return [g for _, _, _, _, p in self.parts for g in p.gestures]

    def steps(self) -> dict:
        out: dict = {}
        for _, _, _, _, p in self.parts:
            for k, v in p.steps.items():
                out.setdefault(k, []).extend(v)
        return {k: sorted(v) for k, v in out.items()}

    def aux(self) -> dict:
        out: dict = {}
        for _, _, _, _, p in self.parts:
            for k, c in p.aux.items():
                out.setdefault(k, []).extend(c)
        return {k: Clip._raw(sorted(v), max((n.start + n.dur for n in v), default=0.0)) for k, v in out.items()}

    def summary(self) -> dict:
        out: dict = {}
        for _, stage, _, name, _ in self.parts:
            out.setdefault(stage, []).append(name)
        return out

    def __repr__(self) -> str:
        return (f"soloist.Performance({self.start:g}-{self.end:g}: {len(self.parts)} parts, "
                f"{sum(len(p.clip) for *_, p in self.parts)} notes, {len(self.warnings)} warnings)")


# ------------------------------------------------------------------------------------------------ solo()

def _spans(song, at) -> list:
    """[(start, bars, bpb)] of `at`: a Section, a list of Sections, or (start, bars)."""
    def one(x):
        if hasattr(x, 'start') and hasattr(x, 'bars'):
            return (float(x.start), float(x.bars), float(x.beats_per_bar))
        raise ComposeError(f"solo at= must be a Section, a list of Sections or (start beat, bars); got {x!r}")
    if at is None:
        raise ComposeError("solo needs at= (a Section, a list of Sections or (start beat, bars))")
    if isinstance(at, tuple) and len(at) == 2 and all(isinstance(v, (int, float)) for v in at):
        start, bars = float(at[0]), float(at[1])
        if bars <= 0:
            raise ComposeError(f"solo at=(start, bars): bars must be > 0, got {bars:g}")
        from . import tempo as _tempo
        bpb = _tempo.beats_per_bar(song.meter_at(start)) if hasattr(song, 'meter_at') else 4.0
        return [(start, bars, bpb)]
    if isinstance(at, (list, tuple)):
        out = [one(x) for x in at]
        if not out:
            raise ComposeError("solo at=[]: no sections")
        return sorted(out)
    return [one(at)]


def _flat(notes) -> bool:
    vs = sorted(n.vel for n in notes)
    if len(vs) < 4:
        return False
    lo, hi = vs[int(0.1 * (len(vs) - 1))], vs[int(math.ceil(0.9 * (len(vs) - 1)))]
    return hi - lo < 10


def _choose(cands: list, E: float, D: float, rng, recent: list, played=None) -> list:
    """Candidates ordered best first: near the stage's energy / density, the move's weight, not the one just played,
    and fresh: a move the player already used (this solo, or an earlier one sharing the budget: played = {name:
    count}) loses 0.35 per use - a second solo says something new."""
    def score(m):
        s = -2.0 * abs(m.energy - E) - 1.4 * abs(m.density - D) + 0.35 * math.log(max(m.weight, 1e-3))
        if recent and m.name == recent[-1]:
            s -= 1.0
        elif m.name in recent[-3:]:
            s -= 0.45
        if played and 'motif' not in m.roles:
            s -= 0.35 * played.get(m.name, 0)
        return s + 0.35 * rng.random()
    return sorted(cands, key=score, reverse=True)


OPENINGS = ('motif', 'fragment', 'line')
"""How a melodic solo's first statement opens (solo(opening=)): 'motif' the motif (literal while literal quotes
remain), 'fragment' a developed fragment of it (displaced, re-fitted), 'line' a line of its own (an answer move: the
motif comes later). Blind round 7: every solo opened by quoting the head."""


def solo(song, track, vocab: Vocabulary, at=None, arc: str = 'classic', motif=None, budget=None, seed=None, *,
         prog=None, key=None, energy=None, place: bool = True, quotes: int = 2, opening: str = 'motif') -> Performance:
    """A solo on `track` over `at` (a Section, a list of Sections - one arc across them in order -, or (start beat,
    bars)) played from `vocab`'s moves along `arc` (ARCS: classic, build, ballad, trade, short, jazz). PHRASING: a
    melodic vocabulary (vocab.lines) breathes - heavy-tailed phrases (PHRASES: a 1-bar fragment to an 8-bar line, one
    long line per chorus) with a BREATH of a beat or two after each (now and then a bar), starting anywhere in the bar
    and crossing bar lines and the phrase grid; the breath is silence (the phrase's last note rings into it, no
    attack); a drummer (lines=False) cuts the span into phrases of vocab.phrase_bars bars. Each phrase gets a stage (STAGES) by its place in the arc and is cut into slots by the
    stage's plan - the motif (motif=, else vocab.motif(ctx)) stated, a call from it and a move as the response, the
    motif varied (vocab.vary, default soloist.vary) and answered, a burst, the climax, a resolution. The motif is
    quoted literally at most twice (the statement, the closing callback); every other call is transformed
    (displaced, re-fitted to the chords, a new ending). Moves are chosen by role, energy and density, never the same
    twice running; spice / fast moves go through the budget (budget= a soloist.Budget shared song-wide, a dict of its
    bars, or the vocabulary's default) - a refused one is replaced by the best plain move (logged). Velocities follow
    the arc (ctx.vel per phrase: a narrow window that rises a little, the climax accented) and a flat phrase is
    re-shaped (humanize.touch) when vocab.touch. The LINE RULES of a melodic vocabulary then check the whole solo
    (_lines): no octave wrap (a leap of a 9th+) inside a fast line, no bar repeated verbatim within 8 bars, the
    dynamics inside every run shaped by its contour (a ramp to its high point, low neighbours ghosted). prog= the
    chords (a Progression from the solo's start; ctx.chord(t)), key= (default song.key), energy= scales the arc (0.5..1.5),
    quotes= the literal motif quotes a melodic solo may play (0..2; the rest transformed - blind round 7: the head
    quoted verbatim in the solo), opening= how its first statement opens (OPENINGS), place=False plans without
    writing. Returns a Performance; place=True writes it via vocab.place (or the notes and
    the gesture lanes) and adds its warnings to the song's advice. Deterministic by seed."""
    from .humanize import touch as _touch
    if not isinstance(vocab, Vocabulary):
        raise ComposeError(f"solo needs a soloist.Vocabulary, got {vocab!r}")
    if opening not in OPENINGS:
        raise ComposeError(f"solo opening must be one of {', '.join(OPENINGS)}, got {opening!r}")
    if isinstance(quotes, bool) or not isinstance(quotes, int) or not 0 <= quotes <= 2:
        raise ComposeError(f"solo quotes (literal motif quotes) must be 0..2, got {quotes!r}")
    spans = _spans(song, at)
    arc = _arc(arc)
    pb = vocab.phrase_bars
    bars = sum(b_ for _, b_, _ in spans)
    while pb > 1.0 + _EPS and bars / pb < len(arc):      # a short solo: shorter phrases, the whole arc
        pb = max(1.0, pb / 2.0)
    grid_phrases = phrase_spans(spans, pb)
    if not grid_phrases:
        raise ComposeError("solo: no phrases in at=")
    k = _key(key if key is not None else getattr(song, 'key', None))
    if prog is not None and isinstance(prog, str):
        prog = song.prog(prog)
    es = 1.0 if energy is None else float(energy)
    if not 0.3 <= es <= 1.6:
        raise ComposeError(f"solo energy= scales the arc: 0.3..1.6, got {es:g}")
    bpb0 = grid_phrases[0][2]
    if isinstance(budget, dict):
        bud = Budget(bpb=bpb0, **budget)
    elif budget is None:
        vb = vocab.budget
        bud = Budget(bpb=bpb0, **vb) if isinstance(vb, dict) else (vb if vb is not None else Budget(bpb=bpb0))
    else:
        bud = budget
    if not isinstance(bud, _Budget):
        raise ComposeError(f"solo budget= must be a soloist.Budget or a dict of its bars, got {budget!r}")
    sd = seed_int(seed if seed is not None else f"{getattr(song, 'seed', 0)}:solo:{grid_phrases[0][0]:g}")
    start, end = grid_phrases[0][0], grid_phrases[-1][0] + grid_phrases[-1][1]
    # the phrases: (start, played beats, room until the next phrase, bpb) - free (lines) or on the grid
    if vocab.lines:
        phrases = _free_phrases(spans, arc, vocab.rest, random.Random(f"{sd}:phrasing"))
    else:
        phrases = []
        for i, (p0, pl, bpb) in enumerate(grid_phrases):
            phrases.append((p0, pl, pl, bpb))
    stages = _stages(arc, len(phrases))
    if not vocab.lines:                                        # the grid's planned space at every phrase end
        out = []
        for i, (p0, pl, _, bpb) in enumerate(phrases):
            rest = STAGES[stages[i]]['rest']
            if stages[i] == 'statement' and i + 1 < len(phrases) and stages[i + 1] == 'statement':
                rest = max(rest, 0.45)
            out.append((p0, max(bpb * 0.5, pl * (1.0 - rest * vocab.rest)), pl, bpb))
        phrases = out
    perf = Performance(start, end)
    memory: dict = {}
    recent: list = []
    played = bud.__dict__.setdefault('played', {})       # moves used song-wide (a shared budget remembers them)
    last_note = None
    lo_v, hi_v = vocab.vel
    rlo, rhi = vocab.register

    # the stage that owns the top of the range (the solo's peak note): the climax - in an arc without one, its
    # block-chord chorus (a 'chords' solo peaked under the head's top note: the piece's highest note in the head)
    peak_stage = 'climax' if 'climax' in stages else ('chords' if 'chords' in stages else None)

    def calm(i):
        return (vocab.lines and 0 < i < len(phrases) and stages[i] not in CONTRAST['not']
                and (i + 0.5) / len(phrases) < CONTRAST['until']
                and phrases[i - 1][1] >= CONTRAST['after_bars'] * phrases[i - 1][3] - _EPS)

    def ctx_at(i, stage, role, at_, beats, mot):
        st = STAGES[stage]
        E = max(0.0, min(1.0, st['energy'] * es))
        prog_ = (i + 0.5) / len(phrases)
        reg = rlo + (rhi - rlo) * st['register']
        span = hi_v - lo_v
        if vocab.lines:
            # a narrow window that rises a little with the energy (a jazz solo gets denser more than louder); the
            # climax is the one accented phrase, its whole window up (the piece's peak: 60-75 % into it)
            # (and builds a little across the solo, whatever its shape: its second half at least the first's level -
            # blind round 5: a sparse solo under the head's loudness)
            mid = 0.3 + 0.25 * E + 0.12 * (prog_ - 0.5)
            vel = ((round(lo_v + span * (mid - 0.25), 1), round(lo_v + span * (mid + 0.25), 1))
                   if stage not in ('climax', 'chords')
                   else (round(lo_v + span * (mid + 0.06), 1), round(lo_v + span * 0.96, 1)))
        else:
            vel = (round(lo_v + span * (0.05 + 0.45 * E), 1), round(lo_v + span * (0.55 + 0.45 * E), 1))
        dens = st['density'] * (0.7 + 0.3 * es)
        if calm(i):                                     # a quiet phrase after a long one (CONTRAST)
            dens *= CONTRAST['density']
            reg -= (rhi - rlo) * CONTRAST['register']
            vel = (vel[0] - CONTRAST['vel'], vel[1] - CONTRAST['vel'])
        p0, p1, _, bpb = phrases[i]
        r_lo, r_hi = vocab.range
        if vocab.lines and stage != peak_stage:         # the top of the range is the climax's: the solo's peak note
            r_hi = max(r_lo + 12, min(r_hi - 4, round(r_lo + (r_hi - r_lo) * (0.75 + 0.2 * st['register']))))
        return Ctx(song=song, track=track, vocab=vocab, at=at_, beats=beats,
                   bpm=song.tempo_at(at_) if hasattr(song, 'tempo_at') else 120.0, bpb=bpb, key=k, prog=prog,
                   stage=stage, role=role, energy=E, density=max(0.0, min(1.0, dens)),
                   register=reg, vel=vel, motif=mot, phrase=i, phrases=len(phrases), progress=prog_, last=last_note,
                   next_at=None, rng=random.Random(f"{sd}:{i}:{role}:{at_:.4f}"), budget=bud, memory=memory,
                   solo_start=start, phrase_start=p0, phrase_beats=p1, range=(r_lo, r_hi))

    # the motif
    if motif is not None:
        base_motif = as_clip(motif)
    elif vocab.motif is not None:
        c0 = ctx_at(0, stages[0], 'call', phrases[0][0], phrases[0][1], None)
        base_motif = as_clip(vocab.motif(c0))
    else:
        raise ComposeError(f"solo: no motif= and {vocab!r} has no motif maker")
    if not len(base_motif):
        raise ComposeError("solo: the motif has no notes")
    base_motif = base_motif.shift(-min(n.start for n in base_motif))
    if vocab.lines and phrases[0][1] < max(n.start + n.dur for n in base_motif) - _EPS:   # the motif fits
        phrases = _free_phrases(spans, arc, vocab.rest, random.Random(f"{sd}:phrasing"),
                                first=max(n.start + n.dur for n in base_motif))
        stages = _stages(arc, len(phrases))
    varier = vocab.vary or vary
    stage_runs: list = []
    n_quotes = 0                                         # literal quotes of the motif so far (lines: `quotes`)
    prng = random.Random(f"{sd}:plans")
    # a melodic solo DEVELOPS a cell of the motif (blind round 5: the hook quoted again and again, a chord arpeggio per
    # bar): a stage starts from the motif's fragment, every call / line of the stage develops the cell before it
    # further (vary: sequenced, inverted, displaced, augmented ... and re-fitted to the chords it meets)
    cell: list = [None, None]                            # [the stage's current cell (a Clip from 0), its stage]

    mid0 = sorted(n.pitch for n in base_motif)[len(base_motif) // 2]
    if hasattr(track, 'mark_phrases'):                   # the plan's phrases are the body's phrases (humanize body=)
        track.mark_phrases(*[p[0] for p in phrases])

    def develop_cell(stage_, c_, beats_):
        m_ = varier(cell[0], c_) if cell[0] is not None and cell[1] == stage_ else None
        if m_ is None or len(m_) < 3 or max(n.pitch for n in m_) - min(n.pitch for n in m_) > 9:
            # a new stage (or a cell worn down to two notes, or spread over more than a 6th): afresh
            m_ = transform(develop(base_motif, 'fragment', beats=min(base_motif.length, max(1.5, beats_))), c_)
        if len(m_):                                      # (sequenced on and on, it stays near the motif's register)
            m_ = m_.transpose(-12 * round((sorted(n.pitch for n in m_)[len(m_) // 2] - mid0) / 12.0))
            t0_ = min(n.start for n in m_)
            cell[0], cell[1] = Clip._raw([n._replace(start=n.start - t0_) for n in m_], m_.length - t0_), stage_
        return m_
    for i, (p0, play_len, room, bpb) in enumerate(phrases):
        stage = stages[i]
        if not stage_runs or stage_runs[-1][0] != stage:
            stage_runs.append([stage, p0, p0 + room])
        else:
            stage_runs[-1][2] = p0 + room
        st = STAGES[stage]
        tail = 0.0 if stage == 'swap' else max(0.0, room - play_len)   # the space after the phrase (a trade: the
        #                                                               other hand's)
        final = i == len(phrases) - 1
        # slots of this phrase: (role, offset, beats, wanted role, motif)
        plan = st['plan']
        slots: list = []

        def quote(m_, c_):
            """The motif (or its fragment) as given while quotes remain, else transformed (lines only)."""
            nonlocal n_quotes
            if not vocab.lines or n_quotes < quotes:
                n_quotes += 1
                return m_
            return transform(m_, c_)
        if plan == 'state':
            first = i == 0 or stages[i - 1] != 'statement'
            c_ = ctx_at(i, stage, 'call', p0, play_len, base_motif)
            # a melodic statement: the idea, a half-bar breath, a developed answer; a later statement varies the
            # idea's first half and answers it (blind round 3: the motif and then a held note over empty bars, again
            # and again, read as sparseness by rule)
            if first and vocab.lines and opening == 'line':          # (a line of its own: the motif comes later)
                slots.append(('call', 0.0, play_len, 'answer', base_motif))
                m_ = None
            elif first and (opening == 'motif' or not vocab.lines):
                m_ = quote(base_motif, c_)
            elif vocab.lines:
                m_ = varier(develop(base_motif, 'fragment', beats=max(bpb, base_motif.length / 2.0)), c_)
            else:
                m_ = varier(base_motif, c_)
            call = min(play_len, math.ceil(max((n.start + n.dur for n in as_clip(m_)), default=play_len) * 2) / 2) \
                if m_ is not None else play_len
            gap = max(0.5, math.floor(bpb / 2.0 * 2) / 2)
            if m_ is None:
                pass
            elif vocab.lines and play_len - call - gap >= 1.5:
                slots.append(('call', 0.0, call, 'motif', m_))
                slots.append(('response', call + gap, play_len - call - gap, 'answer', m_))
            else:
                slots.append(('call', 0.0, play_len, 'motif', m_))
        elif plan in ('call_response', 'vary_response'):
            cl = max(bpb * 0.5, min(play_len * 0.5, play_len - bpb * 0.5))
            gap = 0.5 if play_len - cl >= 1.5 else 0.0
            # (a melodic solo: mostly a call from the cell and a response developing it - phrases answering each
            # other; now and then one line through the phrase)
            with_call = not vocab.lines or (play_len >= 4.0 and prng.random() < (0.65 if plan == 'call_response'
                                                                                    else 0.6))
            want = 'answer' if plan == 'call_response' else 'develop'
            if not with_call:                            # one line through the phrase, no motif call
                slots.append(('lead', 0.0, play_len, want, develop_cell(stage, ctx_at(i, stage, 'lead', p0, play_len,
                                                                                       base_motif),
                                                                        base_motif.length / 2.0)
                              if vocab.lines else base_motif))
            else:
                if vocab.lines:
                    # the call: the stage's cell (half the motif, developed further every time) at its own length,
                    # the response continues it
                    c_ = ctx_at(i, stage, 'call', p0, max(1.5, play_len - 1.5), base_motif)
                    m_ = develop_cell(stage, c_, base_motif.length / 2.0)
                    end_ = max((n.start + n.dur for n in m_), default=1.5)
                    cl = max(bpb * 0.5, min(play_len - 1.5, math.ceil(end_ * 2) / 2))
                    gap = 0.5 if play_len - cl >= 2.0 else 0.0
                else:
                    c_ = ctx_at(i, stage, 'call', p0, cl, base_motif)
                if vocab.lines:
                    pass
                elif plan == 'call_response':
                    m_ = develop(base_motif, 'fragment', beats=min(base_motif.length, cl))
                else:
                    m_ = varier(base_motif, c_)
                slots.append(('call', 0.0, cl, 'motif', m_))
                slots.append(('response', cl + gap, play_len - cl - gap, want, m_))
        elif plan in ('burst', 'chords'):
            slots.append(('lead', 0.0, play_len, plan, base_motif))
        elif plan == 'climax':
            slots.append(('lead', 0.0, play_len, 'climax', varier(base_motif, ctx_at(i, stage, 'lead', p0, play_len,
                                                                                      base_motif))))
        elif plan == 'resolve':
            cl = min(play_len * 0.45, max(bpb * 0.5, base_motif.length / 2.0))
            m_ = develop(base_motif, 'fragment', beats=cl)
            m_ = quote(m_, ctx_at(i, stage, 'call', p0, cl, base_motif)) if final or not vocab.lines else \
                transform(m_, ctx_at(i, stage, 'call', p0, cl, base_motif))
            slots.append(('call', 0.0, cl, 'motif', m_))
            slots.append(('response', cl, play_len - cl + (tail * 0.6 if final else 0.0), 'resolve', m_))
        else:  # pragma: no cover - STAGES are fixed
            raise ComposeError(f"unknown stage plan {plan!r}")
        phrase_parts = []
        for j, (role, off, beats, want, m_) in enumerate(slots):
            if beats < 0.25:
                continue
            at_ = p0 + off
            ctx = ctx_at(i, stage, role, at_, beats, m_)
            ctx.next_at = p0 + slots[j + 1][1] if j + 1 < len(slots) else (phrases[i + 1][0] if i + 1 < len(phrases)
                                                                           else None)
            cands = [m for m in vocab.moves if (want in m.roles or not m.roles) and (m.beats <= beats + _EPS)]
            if not cands:
                cands = [m for m in vocab.moves if want in m.roles or not m.roles]
            if not cands:
                perf.warnings.append(f"no move for role {want!r} (stage {stage} at beat {at_:g}): the slot stays empty")
                continue
            ordered = _choose(cands, ctx.energy, ctx.density, ctx.rng, recent, played)
            chosen = None
            for m in ordered:
                if m.spice:
                    cls = 'fast' if m.fast else 'spice'
                    if m.fast and stage not in ('burst', 'climax'):
                        continue
                    # a saved moment (budget.save) is spent by the phrase that contains it; the other phrases of
                    # the solo keep their fast figures fast_every bars away from it
                    if not bud.allows(at_, cls, m.name, span=(p0, p0 + room)):
                        perf.budget['dropped'].append((round(at_, 4), m.name, None))
                        continue
                chosen = m
                break
            if chosen is None:
                plain = [m for m in ordered if not m.spice]
                if not plain:
                    perf.warnings.append(f"every {want!r} move is spice and the budget refused them at beat {at_:g}")
                    continue
                chosen = plain[0]
            if perf.budget['dropped'] and perf.budget['dropped'][-1][0] == round(at_, 4) \
                    and perf.budget['dropped'][-1][2] is None:
                d0 = perf.budget['dropped'][-1]
                perf.budget['dropped'][-1] = (d0[0], d0[1], chosen.name)
            if chosen.beats > beats + _EPS:
                perf.warnings.append(f"move {chosen.name!r} wants {chosen.beats:g} beats, the slot at {at_:g} has "
                                     f"{beats:g}: cut")
            try:
                part = Part.of(chosen.play(ctx))
            except ComposeError as e:
                perf.warnings.append(f"move {chosen.name!r} at beat {at_:g} failed: {e}")
                continue
            if chosen.spice:
                bud.book(at_, 'fast' if chosen.fast else 'spice', chosen.name)
                perf.budget['kept'].append((round(at_, 4), chosen.name))
            for t, name, fast in part.tricks:
                bud.book(at_ + t, 'fast' if fast else 'spice', name)
            # keep the attacks inside the slot (+ a quarter beat); the phrase's last notes may ring into its breath -
            # no new attack there (the breath is silence, not the move's overflow)
            lim = beats + 0.25
            ring = lim + 0.25 + (0.0 if j + 1 < len(slots) else tail * 0.75)
            notes = [n for n in part.clip if n.start < lim - _EPS]
            notes = [n._replace(dur=min(n.dur, ring - n.start)) for n in notes]
            part.clip = Clip._raw(sorted(notes), max(beats, part.clip.length))
            placed = part.shifted(at_)
            phrase_parts.append((at_, stage, role, chosen.name, placed))
            recent.append(chosen.name)
            played[chosen.name] = played.get(chosen.name, 0) + 1
            if len(placed.clip):
                last_note = max(placed.clip, key=lambda n: n.start)
            perf.moves.append((round(at_, 4), round(at_ + beats, 4), stage, chosen.name))
        # dynamics: a flat phrase gets an arc (touch) in the stage's range
        ns = [n for *_, p in phrase_parts for n in p.clip]
        if vocab.touch and _flat(ns):
            lo, hi = ctx_at(i, stage, 'lead', p0, room, None).vel
            shaped = _touch(Clip._raw(sorted(ns), room + p0), lo, hi)
            mp = {(round(n.start, 6), n.pitch): n.vel for n in shaped}
            for idx, (a, s_, r_, nm, p) in enumerate(phrase_parts):
                p.clip = Clip._raw([n._replace(vel=mp.get((round(n.start, 6), n.pitch), n.vel)) for n in p.clip],
                                   p.clip.length)
        perf.parts += phrase_parts
    if stage_runs:                                       # the stages tile the solo
        stage_runs[0][1] = start
        for a, b in zip(stage_runs, stage_runs[1:]):
            a[2] = b[1]
        stage_runs[-1][2] = end
    perf.stages = [(s_, round(a, 4), round(b, 4), round(STAGES[s_]['energy'] * es, 3)) for s_, a, b in stage_runs]
    perf.budget.update(bud.bars if hasattr(bud, 'bars') else {})
    perf.trades = _trades(spans) if all(st_ == 'swap' for st_, _, _ in arc) else []
    if vocab.lines:
        _lines(perf, k, prog, start, vocab.range, random.Random(f"{sd}:lines"), bpb0, spans, perf.trades)
    if not perf.parts:
        perf.warnings.append("the solo played nothing")
    if place:
        if vocab.place is not None:
            vocab.place(track, perf)
        else:
            _default_place(track, perf)
        if hasattr(song, 'advice'):
            tid = getattr(track, 'id', '?')
            for w in perf.warnings:
                song.advice.append(f"soloist on {tid!r}: {w}")
    return perf


def _trades(spans) -> list:
    """The bars a trading-4s solo leaves to the other hand: the second 4 of every 8 (song beats)."""
    out = []
    for s0, bars, bpb in spans:
        e0 = s0 + bars * bpb
        t = s0
        while t + 4 * bpb < e0 - 1.0 - _EPS:
            out.append((t + 4 * bpb, min(t + 8 * bpb, e0)))
            t += 8 * bpb
    return out


def _arc_stage(arc, x: float) -> str:
    """The arc's stage at x (0..1 of the solo) by the stages' shares."""
    st = _arc(arc)
    tot = sum(sh for _, sh, _ in st)
    acc = 0.0
    for name, sh, _ in st:
        acc += sh / tot
        if x < acc - _EPS:
            return name
    return st[-1][0]


PHRASES = {'bars': {0.5: 0.03, 1: 0.12, 1.5: 0.05, 2: 0.2, 3: 0.12, 4: 0.2, 6: 0.15, 8: 0.13},
           'short': {0.0: 0.3, 0.5: 0.4, 1.0: 0.3}, 'dense': 1.0, 'long_beats': 16.0, 'long_every': 40.0,
           'upbeat': 0.6}
"""A melodic solo's phrase lengths (_free_phrases), heavy-tailed: 'bars' {length in bars: weight} - 1-bar fragments
to 8-bar lines (the long ones x (1 + dense x the stage's density): a busy stage plays longer lines) -, each ending
'short' {beats: weight} before its bar line; the next phrase starts off the beat in `upbeat` of the cases; at least
one line of long_beats+ beats in every long_every beats of the solo (a chorus). Blind round 6: the generated phrases
were 5-9 beats with a near-constant spread, the composed solos 12-46 (an 8-12-bar line, then a fragment)."""

BREATH = {'beats': {1.0: 0.3, 1.5: 0.3, 2.0: 0.25, 2.5: 0.15}, 'rest': 2.0, 'build': 0.5,
          'bar': (1.0, 1.75), 'bar_every': 96.0, 'bar_after': 6.0}
"""The breath between two phrases of a melodic solo (_free_phrases): 'beats' {beats: weight} - a beat or two at the
phrase end (the last note rings into it; x bpb / 4: a waltz's a little shorter; x 0.6 + 0.4 x the vocabulary's rest) -,
the longer ones x (1 + rest x the stage's rest (STAGES) x the vocabulary's rest) and x (1 - build x the solo's
progress: shorter as the solo builds); now and then a long breath of
'bar' bars - at most one per bar_every beats (a chorus), only after a line of bar_after+ beats and only across the
start of a 4-bar phrase (after its cadence, never inside a turnaround). User 2026-10-09 (endless r6): "an endless
monotone line of notes" - silence belongs to a phrase end; blind round 6: the fix overshot (4-10 silent bars per
solo, the solo sparser than the head) - inside a chorus a breath is 1-2 beats."""


CONTRAST = {'after_bars': 2.0, 'density': 0.85, 'register': 0.08, 'vel': 4.0, 'until': 0.6,
            'not': ('climax', 'chords', 'burst', 'swap')}
"""Contrast between a melodic solo's phrases (solo): the phrase after a long line (after_bars bars or more) is a
calmer one - its density x density, its register lower by that share of the range, its velocity window down by vel -
unless it is a climax / block-chord / burst / traded phrase or past `until` of the solo (its last stretch builds to the
end; endless r6: one density and level phrase after phrase read as "an endless monotone line"; blind round 6: a
density x 0.6 made the solo sparser than the head - the contrast is register and touch, the line keeps going)."""


def _free_phrases(spans, arc: str, rest_scale: float, rng, first: float = 0.0) -> list:
    """Free phrasing for a melodic solo: [(start, played beats, room until the next phrase, bpb)] - phrase lengths
    drawn from PHRASES (longer as the arc gets denser, one long line per chorus) and a BREATH after each (a beat or
    two, once per chorus a bar after a line), on an 8th grid, starting anywhere in the bar; the last phrase of a span
    runs to a beat before its end; the first phrase is at least `first` beats long (the motif fits). Enough phrases for the
    arc's stages (shorter ones in a short solo; a very short one: its required stages)."""
    total = sum(b * bpb for _, b, bpb in spans)
    # a phrase for every stage of the arc (its required ones in a short solo: one per 8 beats at most)
    need = max(sum(1 for _, _, req in _arc(arc) if req), min(len(_arc(arc)), int(total // 8)))
    if all(st_ == 'swap' for st_, _, _ in _arc(arc)):
        # trading 4s: the right hand plays 4 bars - two phrases with a breath between them, the second ending a
        # beat before the 5th bar -, the other hand has the next 4 (_trades)
        out = []
        for s0, bars, bpb in spans:
            e0, t = s0 + bars * bpb, s0
            while t < e0 - 1.0 - _EPS:
                room = min(8 * bpb, e0 - t)
                own = min(4 * bpb, room)
                l1 = round(rng.uniform(0.4, 0.55) * own * 2) / 2
                r1 = rng.choice((0.5, 1.0, 1.0, 1.5))
                if own - l1 - r1 >= 3.0:
                    out.append((t, l1, l1 + r1, bpb))
                    out.append((t + l1 + r1, own - l1 - r1 - 1.0, room - l1 - r1, bpb))
                else:
                    out.append((t, max(1.0, own - 1.0), room, bpb))
                t += room
        return out
    for scale_ in (1.0, 0.7, 0.5, 0.35):
        out = []
        done = 0.0
        for s0, bars, bpb in spans:
            e0 = s0 + bars * bpb
            t = s0 + rng.choice((0.0, 0.0, 0.5, 1.0, 1.5)) * (1 if bars * bpb >= 8 else 0)
            last_long, last_bar = s0, s0 - BREATH['bar_every']
            while t < e0 - 1.0 - _EPS:
                x = (done + t - s0) / total
                st = STAGES[_arc_stage(arc, x)]
                # the phrase (PHRASES): heavy-tailed - a fragment, a 2-bar idea, now and then a long line (a busy
                # stage longer); one long line per chorus
                w = {b: wt * (1.0 + PHRASES['dense'] * st['density'] if b >= 4 else 1.0)
                     for b, wt in PHRASES['bars'].items()}
                L = max(1.5, (_pick_w(rng, w) * bpb - _pick_w(rng, PHRASES['short'])) * scale_)
                if t - last_long >= PHRASES['long_every'] - PHRASES['long_beats'] - _EPS and scale_ == 1.0:
                    L = max(L, PHRASES['long_beats'] + rng.choice((0.0, 0.5, 1.0, 2.0, 3.5)))
                L = round(L * 2) / 2
                if not out and first:
                    L = max(L, min(math.ceil(first * 2) / 2, e0 - t - 1.0))
                if L >= PHRASES['long_beats'] - _EPS:
                    last_long = t
                # the breath (BREATH): a beat or two (longer in a spacious stage, shorter as the solo builds); the
                # last note rings into it. A long one (a bar+) once per chorus, after a line, across a 4-bar start
                bw = {b: wt * ((1.0 + BREATH['rest'] * st['rest'] * rest_scale) if b > 1.5 else 1.0)
                      * ((1.0 - BREATH['build'] * x) if b > 1.5 else 1.0) for b, wt in BREATH['beats'].items()}
                r = max(1.0, round(_pick_w(rng, bw) * bpb / 4.0 * (0.6 + 0.4 * rest_scale) * 2) / 2)   # (3/4: shorter)
                z = t + L - s0
                if L >= BREATH['bar_after'] - _EPS and t - last_bar >= BREATH['bar_every'] - _EPS \
                        and z % (4 * bpb) >= 3 * bpb - _EPS and rng.random() < 0.5 + st['rest']:
                    r = max(r, round(rng.uniform(*BREATH['bar']) * bpb * 2) / 2)
                    last_bar = t
                nxt = t + L + r                              # the next phrase starts off the beat as often as not
                if abs(nxt - round(nxt)) < _EPS and rng.random() < PHRASES['upbeat']:
                    r += 0.5
                if e0 - (t + L) < 3.0 + r:                   # too little left for another phrase: run to the end
                    L = max(1.0, e0 - t - 1.0)
                    out.append((t, L, e0 - t, bpb))
                    break
                out.append((t, L, L + r, bpb))
                t += L + r
            done += bars * bpb
        if len(out) >= need:
            return out
    return out


def _lines(perf, key, prog, start, rng_, rng, bpb: float = 4.0, spans=None, trades=()) -> None:
    """The line rules over a melodic solo (perf.parts at song beats), per attack (notes within 0.1 beat are one
    chord; its top note is the line):
      wraps    inside a fast line (attacks half a beat apart or closer) a leap of a 9th+ moves the rest of the run an
               octave toward the note before it, a single note folded out and back (a 7th+ each way) moves home -
               the line turns, it never folds (inside the range)
      repeats  a bar (3+ attacks) equal to one of the 8 bars before it (positions, pitches, lengths) loses its last
               off-beat attack (the note before rings on) or, without one, its last note moves to another chord tone
      runs     in a run of 4+ attacks half a beat apart or closer the velocities ramp to the run's focus (RUN_TOUCH:
               its high point, its landing or an early peak, drawn per run) and fall after it, a little louder higher
               up, a leap target leaned on, now and then a low neighbour (under both sides) ghosted 5-10, a player's
               unevenness on top - the phrase, never the beat, and not the pitch step by step; neighbours at most 15
               apart
      chords   (with prog) a note on beat 1 / 3 (3/4: 1) or longer than half a beat that breaks theory.clash() over
               its chord (an anticipation: the chord it anticipates) moves a half / whole step onto a chord tone or
               tension; a note held into a chord it clashes with is released at the change (blind round 3: a moved
               motif / a held note that ignores the chord)
      unisons  no repeated note inside a line (attacks half a beat apart or closer): the off-beat one of the two
               moves a step (scale / chord), never onto its neighbours"""
    lo, hi = rng_
    E = []                                               # [part index, start, dur, pitch, vel, alive]
    for pi, (*_, p) in enumerate(perf.parts):
        for n in p.clip:
            E.append([pi, n.start, n.dur, n.pitch, n.vel, True])
    if not E:
        return

    def clusters():
        out = []
        for idx in sorted((i for i, e in enumerate(E) if e[5]), key=lambda i: (E[i][1], -E[i][3])):
            if out and E[idx][1] - E[out[-1][0]][1] < 0.1:
                out[-1].append(idx)
            else:
                out.append([idx])
        return out

    def top(c):
        return max(c, key=lambda i: E[i][3])

    def tones_at(t):
        if prog is not None and prog.length > 0:
            ch = prog.at(min(max(t - start, 0.0), prog.length - 1e-6) % prog.length)
            if ch is not None:
                return {(ch.root + i) % 12 for i in ch.intervals}
        k = key if key is not None else Key('A minor')
        return {(k.tonic + i) % 12 for i in ((0, 3, 7) if k.minorish else (0, 4, 7))}

    def runs(cs):
        out, cur = [], [0]
        for j in range(1, len(cs)):
            if E[cs[j][0]][1] - E[cs[j - 1][0]][1] <= 0.5 + _EPS and E[top(cs[j - 1])][2] <= 0.6:
                cur.append(j)
            else:
                out.append(cur)
                cur = [j]
        out.append(cur)
        return [r for r in out if len(r) >= 2]

    def shift(cs, by):
        for c in cs:
            for i in c:
                E[i][3] += by
    # ---- wraps
    cs = clusters()
    for r in runs(cs):
        for a, b in zip(r, r[1:]):
            d = E[top(cs[b])][3] - E[top(cs[a])][3]
            if abs(d) >= 13:
                by = -12 * (1 if d > 0 else -1) * (abs(d) // 12)
                rest = [cs[j] for j in r if j >= b]
                if all(lo <= E[top(c)][3] + by <= hi for c in rest):
                    shift(rest, by)
        for a, b, c_ in zip(r, r[1:], r[2:]):
            p0, p1, p2 = (E[top(cs[j])][3] for j in (a, b, c_))
            if abs(p1 - p0) >= 10 and abs(p2 - p1) >= 10 and (p1 > p0) != (p2 > p1):
                by = 12 if p1 < p0 else -12
                if lo <= p1 + by <= hi:
                    shift([cs[b]], by)
    # ---- verbatim bar repeats
    cs = clusters()
    bars: dict = {}
    for c in cs:
        bars.setdefault(int(math.floor((E[c[0]][1] - start) / bpb + _EPS)), []).append(c)

    def sig(b):
        b0 = start + b * bpb
        return tuple((round((E[c[0]][1] - b0) * 12), E[top(c)][3], round(E[top(c)][2] * 4)) for c in bars.get(b, []))
    sigs = {b: sig(b) for b in bars}
    for b in sorted(bars):
        s_ = sigs[b]
        if len(s_) < 3 or not any(sigs.get(x) == s_ for x in range(b - 8, b)):
            continue
        cl = bars[b]
        weak = [j for j in range(1, len(cl)) if abs(E[cl[j][0]][1] - round(E[cl[j][0]][1])) > 0.05]
        if weak:
            j = weak[-1]
            gone_end = max(E[i][1] + E[i][2] for i in cl[j])
            for i in cl[j]:
                E[i][5] = False
            for i in cl[j - 1]:
                E[i][2] = max(E[i][2], gone_end - E[i][1])
        else:
            t_ = top(cl[-1])
            tones = tones_at(E[t_][1])
            alt = [q for q in range(E[t_][3] - 5, E[t_][3] + 6) if q % 12 in tones and q != E[t_][3]
                   and lo <= q <= hi]
            if alt:
                E[t_][3] = min(alt, key=lambda q: abs(q - E[t_][3]) + rng.random())
        sigs[b] = sig(b)
    # ---- the chord under every strong / long note (theory.clash), notes held into a clashing chord, repeated notes
    if prog is not None and prog.length > 0:
        L = prog.length
        end_ = max(E[i][1] + E[i][2] for i in range(len(E)))
        changes = sorted({start + k * L + s for k in range(int((end_ - start) // L) + 2) for s, _, _ in prog})

        def chord_at(t):
            return prog.at((t - start) % L)

        def fits(q, ch):
            from .theory import available_tensions
            return (q - ch.root) % 12 in {x % 12 for x in ch.intervals} | set(available_tensions(ch))
        cs = clusters()
        tops_ = [top(c) for c in cs]
        for j, c in enumerate(cs):
            t_ = tops_[j]
            t0, du, p = E[t_][1], E[t_][2], E[t_][3]
            if du <= 0.15 + _EPS:                        # a grace note: deliberate
                continue
            ant = next((x for x in changes if t0 < x <= t0 + 0.55 and t0 + du > x + 0.1), None)
            ch = chord_at((ant if ant is not None else t0) + 1e-3)
            pos = (t0 - start) % bpb
            strong = (abs(pos - round(pos)) < 0.05 and int(round(pos)) % (3 if abs(bpb - 3) < _EPS else 2) == 0) \
                or du > 0.5 + _EPS
            prv = E[tops_[j - 1]][3] if j else None
            nxt = E[tops_[j + 1]][3] if j + 1 < len(cs) else None
            if strong and ch is not None and _clash(ch, p):
                alt = [q for q in (p - 1, p + 1, p - 2, p + 2) if lo <= q <= hi and fits(q, ch)
                       and q not in (prv, nxt)]
                if alt:
                    shift([c], alt[0] - p)
                    p = alt[0]
            # held into a chord it clashes with: released at the change (a re-strike is the next phrase's business)
            for x in changes:
                if t0 + 0.25 < x < t0 + du - 0.25 and x != ant and _clash(chord_at(x + 1e-3), p):
                    for i in c:
                        E[i][2] = min(E[i][2], max(0.25, x - E[i][1] - 0.02))
                    break
        # no repeated note inside a line (8ths / 16ths): the weaker of the two moves a step (a neighbour that turns
        # the line), never onto the note after it
        cs = clusters()
        tops_ = [top(c) for c in cs]
        for j in range(1, len(cs)):
            a_, b_ = tops_[j - 1], tops_[j]
            if E[a_][3] != E[b_][3] or E[b_][1] - E[a_][1] > 0.55 + _EPS or E[a_][2] > 0.6:
                continue
            fr_b = E[b_][1] - math.floor(E[b_][1] + _EPS)
            k = j if abs(fr_b) > 0.05 or j == 1 else j - 1          # the off-beat one (else the later)
            t_ = tops_[k]
            ch = chord_at(E[t_][1] + 1e-3)
            near = [E[tops_[x]][3] for x in (k - 1, k + 1) if 0 <= x < len(cs)]
            pcs = (set(key.pcs) if key is not None else set()) | {(ch.root + i) % 12 for i in ch.intervals}
            alt = [q for q in (E[t_][3] + 1, E[t_][3] - 1, E[t_][3] + 2, E[t_][3] - 2)
                   if q % 12 in pcs and lo <= q <= hi and q not in near and not _clash(ch, q)]
            if alt:
                shift([cs[k]], alt[0] - E[t_][3])
    # ---- run dynamics
    cs = clusters()
    RT = RUN_TOUCH
    for r in runs(cs):
        if len(r) < 4:
            continue
        tops = [top(cs[j]) for j in r]
        focus = _pick_w(rng, RT['focus'])
        hp = max(range(len(r)), key=lambda j: (E[tops[j]][3], -j)) if focus == 'top' else \
            len(r) - 1 if focus == 'end' else max(1, int(round(rng.uniform(0.25, 0.45) * (len(r) - 1))))
        base = sum(E[t][4] for t in tops) / len(tops)
        mean_p = sum(E[t][3] for t in tops) / len(tops)
        prev_v = None
        for j, t in enumerate(tops):
            # the run's shape follows the phrase, never the beat: a ramp to its focus and a fall after it, a little
            # louder higher up, a leap target leaned on, now and then a low neighbour (under both sides) ghosted
            v = base * ((0.88 + 0.17 * j / hp) if j <= hp and hp else (1.05 - 0.15 * (j - hp) / max(1, len(r) - 1 - hp)))
            v += RT['pitch'] * (E[t][3] - mean_p)
            ghost = False
            if 0 < j < len(tops) - 1:
                pa, pb = E[tops[j - 1]][3], E[tops[j + 1]][3]
                if E[t][3] < min(pa, pb) and rng.random() < RT['ghost']:
                    v -= rng.uniform(5, 10)
                    ghost = True
                elif abs(E[t][3] - pa) >= 5:
                    v += rng.uniform(3, 6)
            v += rng.uniform(-RT['jitter'], RT['jitter'])
            if prev_v is not None and not ghost:             # neighbours at most 15 apart (a ghost excepted)
                v = min(prev_v + 15, max(prev_v - 15, v))
            prev_v = v if not ghost else prev_v
            f = max(1.0, v) / max(1.0, E[t][4])
            for i in cs[r[j]]:
                E[i][4] = max(1, min(127, int(round(E[i][4] * f))))
    # ---- back into the parts
    per: dict = {}
    for e in E:
        if e[5]:
            per.setdefault(e[0], []).append(Note(e[1], max(0.03, e[2]), int(e[3]), int(e[4])))
    for pi, (a, s_, r_, nm, p) in enumerate(perf.parts):
        p.clip = Clip._raw(sorted(per.get(pi, [])), p.clip.length)


RUN_TOUCH = {'focus': {'top': 0.35, 'end': 0.35, 'early': 0.3}, 'pitch': 0.5, 'jitter': 4.5, 'ghost': 0.5}
"""The dynamics of a melodic solo's runs (_lines): the run swells to its focus - drawn per run: 'top' its high point,
'end' its landing (a line leaning into its target), 'early' a point a quarter to half-way in (attack and release) -
and falls after it; 'pitch' velocity per semitone over the run's mean, a 'jitter' of the hand (+-), a low neighbour
ghosted in 'ghost' of the cases. Blind round 7: the solo's velocity followed the pitch on 74-84 % of the steps (a
ramp to the high point plus 0.8 per semitone) - the touch follows the phrase and its accents;
blind round 8 (pitch 0.25): the composed solos' velocity followed the pitch MORE (r 0.52-0.71 against 0.45-0.52)."""


def _default_place(track, perf: Performance) -> None:
    """The notes, then every gesture lane on the track's targets (agentsound.hornist.render: air, mic, bend, the
    sampler vibrato)."""
    track.play(perf.clip, perf.start)
    gs = perf.gestures
    if gs:
        from .hornist import render
        render(track, gs)


# ------------------------------------------------------------------------------------------------ material
# Pitch and time helpers every vocabulary shares (the guitar's and the wind player's phrases are built on them): the
# harmony at a beat, the scales a soloist reaches for, the register of the arc, lines that answer, run and aim at targets.

def key_of(ctx) -> Key:
    """The solo's key (ctx.key, default A minor)."""
    return ctx.key if isinstance(ctx.key, Key) else Key(ctx.key or 'A minor')


def chord_tones(ctx, t=None) -> set:
    """Pitch classes of the chord at song beat t (default ctx.at); the key's tonic triad without prog=."""
    c = ctx.chord(t)
    if c is None:
        k = key_of(ctx)
        return {(k.tonic + i) % 12 for i in ((0, 3, 7) if k.minorish else (0, 4, 7))}
    return {(c.root + i) % 12 for i in c.intervals}


def pentatonic(ctx, t=None) -> set:
    """The pentatonic a soloist reaches for at beat t: minor pentatonic on minor / dominant chords, major on major ones
    (kept inside the key when 4+ of its notes are); the key's own pentatonic without prog=."""
    from .theory import chord_kind
    c = ctx.chord(t)
    k = key_of(ctx)
    if c is None:
        return {(k.tonic + i) % 12 for i in ((0, 3, 5, 7, 10) if k.minorish else (0, 2, 4, 7, 9))}
    iv = (0, 2, 4, 7, 9) if chord_kind(c) in ('maj', 'maj7', '6', 'sus', 'aug') else (0, 3, 5, 7, 10)
    pcs = {(c.root + i) % 12 for i in iv}
    inside = pcs & set(k.pcs)
    return inside if len(inside) >= 4 else pcs


def scale(ctx, t=None) -> set:
    """The notes a line may use at song beat t (default ctx.at): the key's pitch classes over a chord of the key (its
    tones all diatonic: a ii-7 dorian, a iii-7 phrygian; a written tension outside the key replaces its neighbour), the
    chord's OWN scale over a borrowed / chromatic chord (a secondary dominant, a tritone sub, a bVImaj7, a minor iv:
    blind round 5 heard a Db over Bbmaj9 and a B natural over Gm6 - notes of the key, not of the chord)."""
    k = set(key_of(ctx).pcs)
    c = ctx.chord(t) if getattr(ctx, 'prog', None) is not None else None
    if c is None:
        return k
    from .theory import chord_scale
    core = {(c.root + i) % 12 for i in c.intervals if i < 12}
    if not core <= k:
        return {(c.root + i) % 12 for i in chord_scale(c)} | core
    for x in {(c.root + i) % 12 for i in c.intervals if i >= 12} - k:      # a written #11 / b9 / b13 over the key
        k = (k - {(x + 1) % 12, (x - 1) % 12}) | core | {x}
    return k


def snap(p: int, pcs, direction: int = 0) -> int:
    """The nearest pitch in pcs (direction > 0: prefer up, < 0: down)."""
    for d in range(0, 12):
        for q in ((p + d, p - d) if direction >= 0 else (p - d, p + d)):
            if q % 12 in pcs:
                return q
    return p


def step(p: int, pcs, n: int) -> int:
    """n steps along pcs from p (negative: down)."""
    q, d = p, (1 if n > 0 else -1)
    for _ in range(abs(n)):
        q += d
        while q % 12 not in pcs:
            q += d
    return q


def fold(p: int, ctx, near=None) -> int:
    """p moved by octaves into ctx.range; near= a pitch: the octave of p inside the range nearest to it (a line's
    next note never lands an octave away from the note before it)."""
    lo, hi = ctx.range
    if near is not None:
        cands = [q for q in range(p % 12, 128, 12) if lo <= q <= hi]
        if cands:
            return min(cands, key=lambda q: (abs(q - near), q))
    while p > hi:
        p -= 12
    while p < lo:
        p += 12
    return p


def fit(pitches, ctx) -> list:
    """A line moved by octaves into ctx.range; a line still wider than the range TURNS at its edge (the intervals
    from there on mirrored, snapped to the line's own pitch classes) - never a single note folded an octave inside a
    line (D6 Eb5 D6)."""
    lo, hi = ctx.range
    ps = [int(p) for p in pitches]
    while ps and max(ps) > hi and min(ps) - 12 >= lo:
        ps = [p - 12 for p in ps]
    while ps and min(ps) < lo and max(ps) + 12 <= hi:
        ps = [p + 12 for p in ps]
    if not ps or (lo <= min(ps) and max(ps) <= hi):
        return ps
    pcs = {p % 12 for p in ps}
    out, sign = [fold(ps[0], ctx)], 1
    for a, b in zip(ps, ps[1:]):
        d = (b - a) * sign
        q = out[-1] + d
        if not lo <= q <= hi:
            sign = -sign
            q = snap(out[-1] - d, pcs, -1 if d > 0 else 1)
            if not lo <= q <= hi:
                q = fold(q, ctx, near=out[-1])
        out.append(q)
    return out


def center(ctx, shift: float = 0.0, jitter: float = 1.5) -> int:
    """The pitch the arc sits on here: ctx.register (0 = the bottom of ctx.range .. 1 = its top) + shift, a little
    seeded wobble."""
    lo, hi = ctx.range
    c = lo + 3 + (hi - lo - 5) * max(0.0, min(1.0, ctx.register + shift))
    return int(round(c + (ctx.rng.uniform(-jitter, jitter) if jitter else 0.0)))


def seconds(ctx, beats: float) -> float:
    return beats * 60.0 / float(ctx.bpm)


def grid(ctx, max_rate: float = 11.0, options=(1 / 6, 0.25, 1 / 3, 0.5)) -> float:
    """The fastest grid (beats) from options whose notes per second stay under max_rate."""
    for g in options:
        if 1.0 / seconds(ctx, g) <= max_rate:
            return g
    return options[-1]


def vel(ctx, x: float) -> float:
    """A velocity at share x (0..1) of this phrase's range ctx.vel."""
    lo, hi = ctx.vel
    return lo + (hi - lo) * max(0.0, min(1.0, x))


def merge(*parts) -> 'Part':
    """Parts (same origin) as one."""
    out = Part()
    for p in parts:
        if p is not None:
            out = out.merge(Part.of(p))
    return out


def trick(ctx, name: str, at: float = 0.0, fast: bool = False) -> bool:
    """A trick INSIDE a move (beats from ctx.at): True and booked when the solo's budget allows it."""
    cls = 'fast' if fast else 'spice'
    T = ctx.at + at
    if ctx.budget.allows(T, cls, name):
        ctx.budget.book(T, cls, name)
        return True
    return False


def motif_in_register(ctx, motif=None) -> Clip:
    """The motif (default ctx.motif) moved by octaves to the arc's register and cut to the slot (its last note may
    ring a little longer)."""
    c = as_clip(ctx.motif if motif is None else motif)
    if not len(c):
        return c
    med = sorted(n.pitch for n in c)[len(c) // 2]
    c = c.transpose(12 * round((center(ctx, jitter=0) - med) / 12.0))
    lo, hi = ctx.range
    while max(n.pitch for n in c) > hi and min(n.pitch for n in c) - 12 >= lo:
        c = c.transpose(-12)
    while min(n.pitch for n in c) < lo and max(n.pitch for n in c) + 12 <= hi:
        c = c.transpose(12)
    ns = [n for n in c if n.start < ctx.beats - _EPS]
    if not ns:
        return Clip.rest(ctx.beats)
    last = max(ns, key=lambda n: n.start)
    ns = [n if n is not last else n._replace(dur=max(n.dur, min(ctx.beats - n.start, n.dur * 1.5))) for n in ns]
    return Clip._raw(sorted(ns), ctx.beats)


def answer_line(ctx, *, start=None, n=None, grid_=None) -> list:
    """An answer: [(start, dur, pitch)] - in MOTIVIC of the cases the motif's cell developed (motif_line: the call's
    cell answered), else a line (target_line: mostly falling, now and then an arch) from a 3rd-5th above the last
    note played (or the arc's centre), its length from the slot and the density (n notes, default about half the slot
    at low density .. nearly all of it, but long enough that its landing holds ANSWER_HOLD bars at most), landing on
    a chord tone near its last note held to the slot's end."""
    if start is None:
        start = ctx.last.pitch + ctx.rng.choice((3, 5, 7)) if ctx.last is not None else center(ctx, 0.08)
    if ctx.rng.random() < MOTIVIC:                       # mostly the motif's cell developed (blind round 5)
        line = motif_line(ctx, start=int(start))
        if line:
            return line
    g = grid_ if grid_ is not None else (0.5 if ctx.density < 0.5 else 0.25)
    room = ctx.beats - 0.75
    if n is None:
        n = max(3, int(room / g * (0.6 + 0.4 * ctx.density) * ctx.rng.uniform(0.85, 1.15)),
                int((room - ANSWER_HOLD * float(getattr(ctx, 'bpb', 4.0) or 4.0)) / g + 0.999))
    while n > 2 and n * g > room:
        n -= 1
    line = target_line(ctx, length=n * g, grid_=g, start=int(start),
                       contour='fall' if ctx.rng.random() < 0.8 else 'arch')     # (the leap up, then back down)
    end = line[-1][0] + line[-1][1]
    tones = chord_tones(ctx, ctx.at + end)
    tail = fold(snap(line[-1][2] + ctx.rng.choice((-2, -1, 1, 2)), tones, -1), ctx, near=line[-1][2])
    if tail == line[-1][2]:
        tail = fold(snap(tail - 1, tones, -1), ctx, near=line[-1][2])
    return line + [(end, held(ctx.beats - end), tail)]


ANSWER_HOLD = 0.6
"""answer_line's landing note is held 0.6 bar at most (x the slot's bpb): the line runs long enough - blind round 8: a
sparse waltz answer in a 10-beat slot held its landing 7 beats, silent bars inside the solo's phrases."""

MOTIVIC = 0.45
"""The share of the solo's answer lines (answer_line; the piano's sequences and riffs too) built from the motif
(motif_line: a 3-5 note cell of it developed) instead of a target-first line - blind round 5: a chord arpeggio per
bar reads as generated; a solo states a cell of the head and develops it."""

CELL_MOVES = {'sequence': 3.0, 'invert': 1.0, 'displace': 1.4, 'truncate': 1.2, 'augment': 0.6, 'repeat': 0.3}
"""How motif_line develops its cell from one statement to the next (drawn per statement): sequence (a scale step or
two along the line's contour), invert (its intervals turned), displace (an 8th later: new accents), truncate (its
head only: a fragment), augment (twice as slow, once per line), repeat (as it was, re-fitted)."""


def motif_cell(ctx, rng=None) -> list:
    """A 3-5 note cell of ctx.motif as [(start from 0, dur, pitch)]: its head mostly, now and then a later window -
    [] when the motif has fewer than 3 notes."""
    rng = rng or ctx.rng
    c = sorted(as_clip(ctx.motif)) if getattr(ctx, 'motif', None) is not None else []
    if len(c) < 3:
        return []
    k = min(len(c), rng.choice((3, 4, 4, 5)))
    i0 = 0 if rng.random() < 0.6 or len(c) == k else rng.randrange(0, len(c) - k + 1)
    w = c[i0:i0 + k]
    return [(n.start - w[0].start, min(n.dur, 2.0), n.pitch) for n in w]


def motif_line(ctx, *, length=None, start=None, contour=None) -> list:
    """motif_line_once through the recent-lick memory (fresh): a development that repeats a recent lick is drawn
    again."""
    return fresh(ctx, lambda: motif_line_once(ctx, length=length, start=start, contour=contour))


def motif_line_once(ctx, *, length=None, start=None, contour=None) -> list:
    """A line built FROM THE MOTIF (blind round 5: 'take a 3-5 note cell from the head and develop it'): a cell of
    ctx.motif (motif_cell) stated from `start` (default near the last note played / the arc's centre), then developed
    statement by statement (CELL_MOVES, drawn: sequenced along the contour - rise / fall / arch, turning at the
    range's edges -, inverted, displaced, truncated, augmented), a breath of 0-1 beat between the statements, across
    the bar lines; every statement re-fitted to the chords it meets (on a beat or a dotted 8th+: a chord tone or
    tension near the shape; the rest: the chord's own scale - scale()), no repeated note; its last note a chord tone
    held to the end. [(start, dur, pitch)] for `length` beats (default the slot minus half a beat); [] without a cell."""
    from .theory import available_tensions
    rng = ctx.rng
    cell = motif_cell(ctx, rng)
    if not cell:
        return []
    lo, hi = ctx.range
    L = (ctx.beats - 0.5) if length is None else float(length)
    if L < 1.0:
        return []
    shape = contour or _pick_w(rng, {'rise': 1.0, 'fall': 1.0, 'arch': 1.3})
    d = -1 if shape == 'fall' else 1
    q0 = start if start is not None else (ctx.last.pitch + rng.choice((-3, -2, 2, 3)) if ctx.last is not None
                                          else center(ctx))
    first = fold(snap(int(q0), chord_tones(ctx, ctx.at)), ctx, near=ctx.last.pitch if ctx.last is not None else None)
    ivs = [b[2] - a[2] for a, b in zip(cell, cell[1:])]
    rhythm = [(s, du) for s, du, _ in cell]
    gap_ = cell[-1][0] / max(1, len(cell) - 1)
    if gap_ >= 0.75 - _EPS and rng.random() < ctx.density:     # a slow cell in a busy stage: in diminution
        rhythm = [(s / 2, max(0.25, du / 2)) for s, du in rhythm]
    out, t, augmented, prev = [], 0.0, False, None
    while t < L - 0.25 - _EPS:
        p, stmt = first, []
        for j, (s, du) in enumerate(rhythm):
            if t + s >= L - 0.25 - _EPS:
                break
            want = p if j == 0 else p + ivs[j - 1]
            T = ctx.at + t + s
            ch = ctx.chord(T)
            tones = chord_tones(ctx, T)
            strong = abs(T - round(T)) < _EPS or du >= 0.75 - _EPS
            pcs = (tones | ({(ch.root + x) % 12 for x in available_tensions(ch)} if ch is not None else set())) \
                if strong else (scale(ctx, T) | tones)
            q = fold(snap(want, pcs, 1 if j and ivs[j - 1] > 0 else -1), ctx, near=want)
            if prev is not None and abs(q - prev) > 9:   # (no leap over a 6th: the octave nearer the note before)
                q = fold(q, ctx, near=prev)
            if q == prev:                                # no repeated note: the next one of the set
                q = fold(snap(q + (1 if want >= q else -1), pcs, 1 if want >= q else -1), ctx, near=q)
            stmt.append((t + s, du, q))
            p, prev = q, q
        out += stmt
        if not stmt:
            break
        end = max(s + du for s, du in rhythm)
        t += end + _pick_w(rng, {0.0: 0.2 + 0.4 * ctx.density, 0.5: 0.45, 1.0: 0.25 * max(0.0, 0.5 - ctx.density)})
        # the next statement: the cell developed (CELL_MOVES)
        how = _pick_w(rng, {k: w for k, w in CELL_MOVES.items()
                            if not (k == 'truncate' and len(rhythm) < 4) and not (k == 'augment' and
                                                                                  (augmented or 2 * end > L - t))})
        if shape == 'arch' and t > L * 0.55:
            d = -1
        if how == 'sequence':
            first = step(first, scale(ctx, ctx.at + min(t, L - 0.01)), d * rng.choice((1, 1, 2)))
        elif how == 'invert':
            ivs = [-x for x in ivs]
            first = step(first, scale(ctx, ctx.at + min(t, L - 0.01)), d)
        elif how == 'displace':
            t += 0.5
        elif how == 'truncate':
            rhythm, ivs = rhythm[:len(rhythm) - 1], ivs[:len(rhythm) - 2]
        elif how == 'augment':
            rhythm, augmented = [(s * 2, du * 2) for s, du in rhythm], True
        if prev is not None and abs(first - prev) >= 5:  # (no leap back between statements: the line chains on)
            first = step(prev, scale(ctx, ctx.at + min(t, L - 0.01)), d)
        span = [first + sum(ivs[:j]) for j in range(len(rhythm))]
        if max(span) > hi - 2 or min(span) < lo + 2:     # the contour turns at the range's edge
            d = -d
            first = step(first, scale(ctx, ctx.at + min(t, L - 0.01)), 2 * d)
    if not out:
        return []
    out = [n for n in out if n[0] < L - 0.25 - _EPS] or out[:1]
    s, du, q = out[-1]
    tones = chord_tones(ctx, ctx.at + s)
    q = fold(snap(q, tones, -1), ctx, near=q)
    out[-1] = (s, held(max(du + 0.25, L + 0.5 - s)), q)
    return out


def held(room: float, least: float = 0.5) -> float:
    """A held / landing note's length in `room` beats: a quarter beat's release, floored to the 8th grid (at least
    `least`) - a quarter, a half, a dotted half ..., not the 1.25 / 1.75 a slot's leftover would give."""
    return max(least, math.floor((room - 0.25) * 2 + 1e-6) / 2.0)


_RHYTHMS = {
    0.5: {(0.0, 0.5): 0.8, (0.0,): 0.14, (0.0, 1 / 3, 2 / 3): 0.06},
    0.25: {(0.0, 0.25, 0.5, 0.75): 0.62, (0.0, 0.5): 0.3, (0.0, 1 / 3, 2 / 3): 0.08},
    1 / 3: {(0.0, 1 / 3, 2 / 3): 0.72, (0.0, 0.5): 0.18, (0.0,): 0.1},
    1 / 6: {(0.0, 1 / 6, 1 / 3, 0.5, 2 / 3, 5 / 6): 0.5, (0.0, 0.25, 0.5, 0.75): 0.3, (0.0, 1 / 3, 2 / 3): 0.2},
}
"""target_line's rhythm per beat for its grid (the first entry: the grid itself): mostly the grid, now and then a
quarter, 8ths in a 16th line, a triplet as a rare peak (a line that only runs on one grid is a pattern; one that
changes its grid every beat reads as random: blind test round 2, duration entropy 2.4-3.4 vs composed 1.7-2.2)."""


LEAN = 0.5
"""target_line: the share of its inner beats that lean on a non-chord tone resolving by step to the next note."""

RUNS = (6, 9)
"""target_line turns back after a directed run of RUNS[0]..RUNS[1] notes (blind round 6: composed lines are 4-8-note
runs - scale, chromatic, an enclosure -; a leap restarts the line, which fills back stepwise)."""


def _pick_w(rng, table: dict):
    r = rng.random() * sum(table.values())
    for k_, w in table.items():
        r -= w
        if r <= 0:
            return k_
    return k_


LICKS = {'notes': 5, 'bars': 4.0, 'tries': 4}
"""The player's recent-lick memory (fresh): a cell of `notes` attacks (its pitches as struck) played again within
`bars` bars reads as "that lick again" (blind round 7: a chromatic D-Eb-F-F#-G cell four times in four bars) - a
line that would repeat one is drawn again, up to `tries` times, the freshest kept. One ledger per solo
(ctx.memory['_licks'], a budget.Budget: the cell is the name, same_every the memory's span), shared by every line
maker (target_line, motif_line, the pianist's runs)."""


def lick_ledger(ctx):
    """The solo's recent-lick ledger (a budget.Budget in ctx.memory; None for a context without a memory)."""
    mem = getattr(ctx, 'memory', None)
    if mem is None:
        return None
    led = mem.get('_licks')
    if led is None:
        led = mem['_licks'] = _Budget({'lick': 0.0}, zero='unlimited', same=('lick',),
                                      same_every=LICKS['bars'] * float(getattr(ctx, 'bpb', 4.0) or 4.0))
    return led


def _lick_cells(line, at: float) -> list:
    """[(song beat, cell)] of a line's LICKS['notes']-attack windows (tuples (start, dur, pitch) or Notes; one attack
    per onset, its top note)."""
    pts = sorted(((n.start, n.pitch) if hasattr(n, 'pitch') else (float(n[0]), int(n[2])) for n in line),
                 key=lambda x: (x[0], -x[1]))
    tops = []
    for t, p in pts:
        if tops and t - tops[-1][0] < 0.06:
            continue
        tops.append((t, p))
    k = LICKS['notes']
    return [(at + tops[i][0], tuple(p for _, p in tops[i:i + k])) for i in range(len(tops) - k + 1)]


def fresh(ctx, make):
    """A line from make() (a list of (start, dur, pitch) or a Clip, relative to ctx.at) that repeats no cell the
    solo played within the last LICKS['bars'] bars (lick_ledger) nor one of its own inside that span: drawn again up
    to LICKS['tries'] times, the one with the fewest stale cells kept and its cells booked."""
    led = lick_ledger(ctx)
    if led is None:
        return make()
    span = led.same_every
    best = None
    for _ in range(LICKS['tries']):
        line = make()
        cs = _lick_cells(line, ctx.at)
        stale = sum(not led.allows(t, 'lick', c) for t, c in cs)
        stale += sum(1 for i, (t, c) in enumerate(cs)
                     if any(c2 == c and t - t2 < span and i - j >= LICKS['notes'] for j, (t2, c2) in enumerate(cs[:i])))
        if best is None or stale < best[0]:
            best = (stale, line, cs)
        if not stale:
            break
    for t, c in best[2]:
        led.book(t, 'lick', c)
    return best[1]


def target_line(ctx, *, length=None, grid_=0.5, start=None, contour=None) -> list:
    """target_line_once through the recent-lick memory (fresh): a line that repeats a recent lick is drawn again."""
    return fresh(ctx, lambda: target_line_once(ctx, length=length, grid_=grid_, start=start, contour=contour))


def target_line_once(ctx, *, length=None, grid_=0.5, start=None, contour=None) -> list:
    """A line built TARGET-FIRST, the way a jazz player thinks it (not a pattern): the beats get targets - the 3rd
    or 7th of the chord sounding there (now and then another chord tone) - chosen along a contour (rise / fall /
    arch / valley, turned at the range's edges: the line never folds); the notes between are filled with scale
    steps of the key and the chord, now and then a chromatic approach (a half step into the target) or an enclosure
    (the step above, the half step below, the target). Rhythm per beat from _RHYTHMS (mostly grid_, now and then a
    quarter / triplet / 8ths). [(start, dur, pitch)] for `length` beats (default the slot minus a beat) from start
    (default near the last note played / the arc's centre); its last note is a target."""
    from .theory import guide_tones
    rng = ctx.rng
    lo, hi = ctx.range
    L = (ctx.beats - 1.0) if length is None else float(length)
    g = min(_RHYTHMS, key=lambda x: abs(x - grid_))
    times, t = [], 0.0
    while t < L - 1e-6:
        a = ctx.at + t
        frac = a - math.floor(a + _EPS)
        if frac > _EPS:                                  # off the beat: the grid up to the next beat
            times.append(t)
            t = min(t + grid_, t + (1.0 - frac))
            continue
        pat = _pick_w(rng, _RHYTHMS[g]) if times else next(iter(_RHYTHMS[g]))
        times += [t + x for x in pat if t + x < L - 1e-6]
        t += 1.0
    if len(times) < 2:
        times = [0.0, grid_] if L > grid_ + _EPS else [0.0]
    n = len(times)
    durs = [b - a for a, b in zip(times, times[1:])] + [min(grid_, max(0.1, L - times[-1]))]
    sc = scale(ctx, ctx.at)
    tgt = [abs((ctx.at + x) - round(ctx.at + x)) < 1e-6 for x in times]
    tgt[0] = tgt[-1] = True
    shape = contour or _pick_w(rng, {'rise': 1.0, 'fall': 1.0, 'arch': 1.2, 'valley': 0.6})
    turn = rng.uniform(0.35, 0.65)
    q0 = start if start is not None else (ctx.last.pitch + rng.choice((-3, -2, 2, 3)) if ctx.last is not None
                                          else center(ctx, -0.05))
    q0 = fold(snap(int(q0), chord_tones(ctx, ctx.at) | sc), ctx)
    pitches = [q0] * n
    flip = 1

    def dir_at(x):
        if shape == 'rise':
            return 1
        if shape == 'fall':
            return -1
        if shape == 'arch':
            return 1 if x < turn else -1
        return -1 if x < turn else 1
    ti = [i for i in range(n) if tgt[i]]
    limit = rng.randint(*RUNS)
    for a, b in zip(ti, ti[1:]):
        P, m = pitches[a], b - a
        d = dir_at(times[b] / max(L, _EPS)) * flip
        u_ = rng.uniform(1.1, 1.9)
        if not lo + 2 <= P + d * m * u_ <= hi - 2:       # the contour turns at the edge
            flip, d = -flip, -d
        run_ = 0                                         # the notes so far moving this way
        for j in range(a, 0, -1):
            if pitches[j] == pitches[j - 1] or (pitches[j] > pitches[j - 1]) != (d > 0):
                break
            run_ += 1
        if run_ + m > limit and lo + 2 <= P - d * m * u_ <= hi - 2:   # a turn-back after a directed run (RUNS)
            d, limit = -d, rng.randint(*RUNS)
        want = P + d * m * rng.uniform(1.1, 1.9)
        T = ctx.at + times[b]
        ch = ctx.chord(T)
        tones = chord_tones(ctx, T)
        # a chord change lands on its 3rd / 7th (the guide-tone line); inside a chord now and then another tone
        if ch is not None and rng.random() < (0.92 if ch != ctx.chord(T - 0.5) else 0.6):
            g3, g7 = guide_tones(ch)
            tones = {x % 12 for x in (g3, g7) if x is not None} or tones
        cands = [c for c in range(lo, hi + 1) if c % 12 in tones and c != P and abs(c - P) <= max(7, 2 * m + 2)]
        if not cands:
            cands = [c for c in range(lo, hi + 1) if c % 12 in tones] or [P]
        pitches[b] = min(cands, key=lambda c: abs(c - want) + rng.random() * 0.8)
        Q, k = pitches[b], m - 1
        if k <= 0:
            continue
        pcs = scale(ctx, ctx.at + times[a]) | chord_tones(ctx, ctx.at + times[a])
        fill, prev = [], P
        for j in range(1, k + 1):
            q = snap(int(round(P + (Q - P) * j / (k + 1))), pcs, 1 if Q >= P else -1)
            if q == prev:                                # no repeated note: on along the line's way
                q = step(q, pcs, 1 if Q >= P else -1)
            if q == Q:                                   # (nor the target struck early: its neighbour leads in)
                q = step(Q, pcs, -1 if Q >= P else 1)
                if q == prev:
                    q = Q - 1 if Q >= P else Q + 1
            fill.append(q)
            prev = q
        # a chromatic note only as an approach into a target ON THE BEAT, by half step (blind round 5)
        r = rng.random() if abs(T - round(T)) < _EPS else 1.0
        if k >= 2 and r < 0.22:                          # an enclosure: the step above, the half step below
            fill[-2], fill[-1] = step(Q, scale(ctx, T), 1), Q - 1
        elif r < 0.55 and abs(fill[-1] - Q) > 1:         # a chromatic approach from the side the line comes from
            fill[-1] = Q - 1 if fill[-1] < Q else Q + 1
        for j, q in enumerate(fill):
            pitches[a + 1 + j] = q
    ps = fit(pitches, ctx)
    # now and then a beat leans on a non-chord tone resolving by step to the chord tone after it (an appoggiatura from
    # above or below, a step of the chord's own scale - never a chromatic note on the beat): composed lines strike
    # chord tones on ~80-88 % of their beats, not all
    for i in range(1, n - 1):
        if not tgt[i] or times[i + 1] - times[i] > 0.5 + _EPS or rng.random() >= LEAN \
                or ctx.chord(ctx.at + times[i]) != ctx.chord(ctx.at + times[i] - 0.5):     # (a change: its chord)
            continue
        q = ps[i + 1]
        if q % 12 not in chord_tones(ctx, ctx.at + times[i + 1]):
            continue
        sc_i = scale(ctx, ctx.at + times[i])
        # (from the side the line comes from: the lean keeps the run's direction - blind round 6: lines turning
        # every second note, 0.51-0.61 direction changes per step against the composed 0.30-0.42)
        x = step(q, sc_i, -1 if ps[i - 1] < q else 1)
        if x != ps[i - 1] and lo <= x <= hi and (x - ps[i - 1]) * (q - ps[i - 1]) > 0:
            ps[i] = x
    return [(times[i], durs[i], ps[i]) for i in range(n)]


def run_line(ctx, n: int, *, up: bool = True, pcs=None, start=None) -> list:
    """n pitches running along pcs (default the key's scale) from start (default below the arc's centre), turning
    at the ends of ctx.range."""
    pcs = scale(ctx) if pcs is None else pcs
    lo, hi = ctx.range
    q = fold(snap(center(ctx, -0.2) if start is None else start, pcs), ctx)
    out = []
    for _ in range(int(n)):
        out.append(q)
        q = step(q, pcs, 1 if up else -1)
        if not lo <= q <= hi:
            up = not up
            q = step(q, pcs, 2 if up else -2)
    return out
