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
from .patterns import Clip, as_clip, seed_int
from .theory import ComposeError, Key

__all__ = ['Move', 'Vocabulary', 'Ctx', 'Part', 'Performance', 'Budget', 'ARCS', 'STAGES', 'solo', 'vary', 'develop',
           'DEVELOPMENTS', 'phrase_spans', 'key_of', 'chord_tones', 'pentatonic', 'scale', 'snap', 'step', 'fold', 'fit',
           'center', 'seconds', 'grid', 'vel', 'merge', 'trick', 'motif_in_register', 'answer_line', 'sequence_line',
           'run_line']

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


ROLES = ('motif', 'answer', 'fill', 'develop', 'burst', 'climax', 'resolve')


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
    a drummer, whose feet keep the pulse through the space)."""

    def __init__(self, moves, motif=None, vary=None, *, name: str = '', place=None, register=(0.0, 1.0),
                 vel=(56, 118), phrase_bars: float = 2, touch: bool = True, budget=None, range=(48, 84),
                 rest: float = 1.0):
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
    center, fit, answer_line, sequence_line, run_line, ...) take a Ctx."""

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
}
"""Arc stages: energy, density (0..1), register (0..1 of the vocabulary's range), rest (share of the phrase left
silent at its end: space), plan - how a phrase is cut into slots: state (the motif, then space), call_response
(the motif's head as the call, a move answering it), vary_response (the motif varied / sequenced, then a move), burst
(one dense move), climax (the biggest move, at the top), resolve (the motif's head low, then a move landing on a long
last note)."""

ARCS = {
    'classic': (('statement', 0.18, True), ('answer', 0.2, False), ('develop', 0.2, False), ('burst', 0.16, False),
                ('climax', 0.14, True), ('resolve', 0.12, True)),
    'build': (('statement', 0.2, True), ('develop', 0.3, False), ('burst', 0.25, False), ('climax', 0.25, True)),
    'ballad': (('statement', 0.25, True), ('answer', 0.25, False), ('develop', 0.2, False), ('climax', 0.15, True),
               ('resolve', 0.15, True)),
    'trade': (('trade', 1.0, True),),
    'short': (('statement', 0.35, True), ('climax', 0.4, True), ('resolve', 0.25, True)),
}
"""Arcs: (stage, share of the solo's phrases, required) in order. A required stage gets at least one phrase."""


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
    if arc not in ARCS:
        raise ComposeError(f"solo arc must be one of {', '.join(ARCS)}, got {arc!r}")
    st = ARCS[arc]
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

_VARY = {'statement': (('repeat', 3.0), ('displace', 1.0)),
         'answer': (('fragment', 2.0), ('displace', 1.0), ('answer', 1.0)),
         'develop': (('sequence', 3.0), ('invert', 1.0), ('displace', 1.0), ('tail', 1.0)),
         'trade': (('sequence', 2.0), ('fragment', 1.0), ('invert', 1.0)),
         'burst': (('diminish', 2.0), ('sequence', 1.0)),
         'climax': (('octave', 2.0), ('sequence', 2.0), ('augment', 1.0)),
         'resolve': (('fragment', 2.0), ('augment', 1.0))}


def vary(motif, ctx) -> Clip:
    """The default variation of a motif for ctx.stage (seeded by ctx.rng): the statement repeats it (now and then
    displaced), the answer fragments it, the development sequences it UP by one or two scale steps (or inverts it),
    the climax lifts it an octave or sequences it high, the resolution keeps its head - then the result is folded into
    the stage's register by the vocabulary's own play."""
    c = as_clip(motif)
    opts = _VARY.get(ctx.stage, (('repeat', 1.0),))
    r = ctx.rng.random() * sum(w for _, w in opts)
    how = opts[-1][0]
    for name, w in opts:
        r -= w
        if r <= 0:
            how = name
            break
    steps = 1
    if how == 'sequence':
        steps = 1 + (ctx.phrase % 2) if ctx.stage != 'climax' else 2
    return develop(c, how, key=ctx.key, steps=steps)


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


def solo(song, track, vocab: Vocabulary, at=None, arc: str = 'classic', motif=None, budget=None, seed=None, *,
         prog=None, key=None, energy=None, place: bool = True) -> Performance:
    """A solo on `track` over `at` (a Section, a list of Sections - one arc across them in order -, or (start beat,
    bars)) played from `vocab`'s moves along `arc` (ARCS: classic, build, ballad, trade, short): the span is cut
    into phrases of vocab.phrase_bars bars, each phrase gets a stage (STAGES) by its place in the arc and is cut into
    slots by the stage's plan - the motif (motif=, else vocab.motif(ctx)) stated, its head as a call and a move as
    the response, the motif varied (vocab.vary, default soloist.vary) and answered, a burst, the climax, a resolution -
    each phrase ending in planned space. Moves are chosen by role, energy and density, never the same twice running;
    spice / fast moves go through the budget (budget= a soloist.Budget shared song-wide, a dict of its bars, or the
    vocabulary's default) - a refused one is replaced by the best plain move (logged). Velocities follow the arc
    (ctx.vel per phrase) and a flat phrase is re-shaped (humanize.touch) when vocab.touch. prog= the chords (a
    Progression from the solo's start; ctx.chord(t)), key= (default song.key), energy= scales the arc (0.5..1.5),
    place=False plans without writing. Returns a Performance; place=True writes it via vocab.place (or the notes and
    the gesture lanes) and adds its warnings to the song's advice. Deterministic by seed."""
    from .humanize import touch as _touch
    if not isinstance(vocab, Vocabulary):
        raise ComposeError(f"solo needs a soloist.Vocabulary, got {vocab!r}")
    spans = _spans(song, at)
    if arc not in ARCS:
        raise ComposeError(f"solo arc must be one of {', '.join(ARCS)}, got {arc!r}")
    pb = vocab.phrase_bars
    bars = sum(b_ for _, b_, _ in spans)
    while pb > 1.0 + _EPS and bars / pb < len(ARCS[arc]):      # a short solo: shorter phrases, the whole arc
        pb = max(1.0, pb / 2.0)
    phrases = phrase_spans(spans, pb)
    if not phrases:
        raise ComposeError("solo: no phrases in at=")
    k = _key(key if key is not None else getattr(song, 'key', None))
    if prog is not None and isinstance(prog, str):
        prog = song.prog(prog)
    es = 1.0 if energy is None else float(energy)
    if not 0.3 <= es <= 1.6:
        raise ComposeError(f"solo energy= scales the arc: 0.3..1.6, got {es:g}")
    if isinstance(budget, dict):
        bud = Budget(bpb=phrases[0][2], **budget)
    elif budget is None:
        vb = vocab.budget
        bud = Budget(bpb=phrases[0][2], **vb) if isinstance(vb, dict) else (vb if vb is not None else
                                                                             Budget(bpb=phrases[0][2]))
    else:
        bud = budget
    if not isinstance(bud, _Budget):
        raise ComposeError(f"solo budget= must be a soloist.Budget or a dict of its bars, got {budget!r}")
    sd = seed_int(seed if seed is not None else f"{getattr(song, 'seed', 0)}:solo:{phrases[0][0]:g}")
    stages = _stages(arc, len(phrases))
    start, end = phrases[0][0], phrases[-1][0] + phrases[-1][1]
    perf = Performance(start, end)
    memory: dict = {}
    recent: list = []
    played = bud.__dict__.setdefault('played', {})       # moves used song-wide (a shared budget remembers them)
    last_note = None
    lo_v, hi_v = vocab.vel
    rlo, rhi = vocab.register

    def ctx_at(i, stage, role, at_, beats, mot):
        st = STAGES[stage]
        E = max(0.0, min(1.0, st['energy'] * es))
        prog_ = (i + 0.5) / len(phrases)
        reg = rlo + (rhi - rlo) * st['register']
        span = hi_v - lo_v
        vel = (round(lo_v + span * (0.05 + 0.45 * E), 1), round(lo_v + span * (0.55 + 0.45 * E), 1))
        p0, p1, bpb = phrases[i]
        return Ctx(song=song, track=track, vocab=vocab, at=at_, beats=beats,
                   bpm=song.tempo_at(at_) if hasattr(song, 'tempo_at') else 120.0, bpb=bpb, key=k, prog=prog,
                   stage=stage, role=role, energy=E, density=max(0.0, min(1.0, st['density'] * (0.7 + 0.3 * es))),
                   register=reg, vel=vel, motif=mot, phrase=i, phrases=len(phrases), progress=prog_, last=last_note,
                   next_at=None, rng=random.Random(f"{sd}:{i}:{role}:{at_:.4f}"), budget=bud, memory=memory,
                   solo_start=start, phrase_start=p0, phrase_beats=p1, range=vocab.range)

    # the motif
    if motif is not None:
        base_motif = as_clip(motif)
    elif vocab.motif is not None:
        c0 = ctx_at(0, stages[0], 'call', phrases[0][0], phrases[0][1] * (1 - STAGES[stages[0]]['rest']), None)
        base_motif = as_clip(vocab.motif(c0))
    else:
        raise ComposeError(f"solo: no motif= and {vocab!r} has no motif maker")
    if not len(base_motif):
        raise ComposeError("solo: the motif has no notes")
    base_motif = base_motif.shift(-min(n.start for n in base_motif))
    varier = vocab.vary or vary
    stage_runs: list = []
    for i, (p0, pl, bpb) in enumerate(phrases):
        stage = stages[i]
        if not stage_runs or stage_runs[-1][0] != stage:
            stage_runs.append([stage, p0, p0 + pl])
        else:
            stage_runs[-1][2] = p0 + pl
        st = STAGES[stage]
        rest = st['rest']
        if stage == 'statement' and i + 1 < len(phrases) and stages[i + 1] == 'statement':
            rest = max(rest, 0.45)
        rest *= vocab.rest
        play_len = max(bpb * 0.5, pl * (1.0 - rest))
        # slots of this phrase: (role, offset, beats, wanted role, motif)
        plan = st['plan']
        slots: list = []
        if plan == 'state':
            first = i == 0 or stages[i - 1] != 'statement'
            m_ = base_motif if first else varier(base_motif, ctx_at(i, stage, 'call', p0, play_len, base_motif))
            slots.append(('call', 0.0, play_len, 'motif', m_))
        elif plan in ('call_response', 'vary_response'):
            cl = max(bpb * 0.5, min(play_len * 0.5, play_len - bpb * 0.5))
            gap = 0.5 if play_len - cl >= 1.5 else 0.0
            if plan == 'call_response':
                m_ = develop(base_motif, 'fragment', beats=min(base_motif.length, cl))
            else:
                m_ = varier(base_motif, ctx_at(i, stage, 'call', p0, cl, base_motif))
            slots.append(('call', 0.0, cl, 'motif', m_))
            slots.append(('response', cl + gap, play_len - cl - gap, 'answer' if plan == 'call_response' else 'develop',
                          m_))
        elif plan == 'burst':
            slots.append(('lead', 0.0, play_len, 'burst', base_motif))
        elif plan == 'climax':
            slots.append(('lead', 0.0, play_len, 'climax', varier(base_motif, ctx_at(i, stage, 'lead', p0, play_len,
                                                                                      base_motif))))
        elif plan == 'resolve':
            final = i == len(phrases) - 1
            cl = min(play_len * 0.45, max(bpb * 0.5, base_motif.length / 2.0))
            m_ = develop(base_motif, 'fragment', beats=cl)
            slots.append(('call', 0.0, cl, 'motif', m_))
            slots.append(('response', cl, play_len - cl + (pl * rest * 0.6 if final else 0.0), 'resolve', m_))
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
                    if not bud.allows(at_, cls, m.name, span=(p0, p0 + pl)):
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
            # keep the notes inside the slot (+ a release tail of a quarter beat)
            lim = beats + (0.25 if j + 1 < len(slots) else pl * rest * 0.75)
            notes = [n for n in part.clip if n.start < lim - _EPS]
            notes = [n._replace(dur=min(n.dur, lim + 0.25 - n.start)) for n in notes]
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
            lo, hi = ctx_at(i, stage, 'lead', p0, pl, None).vel
            shaped = _touch(Clip._raw(sorted(ns), pl + p0), lo, hi)
            mp = {(round(n.start, 6), n.pitch): n.vel for n in shaped}
            for idx, (a, s_, r_, nm, p) in enumerate(phrase_parts):
                p.clip = Clip._raw([n._replace(vel=mp.get((round(n.start, 6), n.pitch), n.vel)) for n in p.clip],
                                   p.clip.length)
        perf.parts += phrase_parts
    perf.stages = [(s_, round(a, 4), round(b, 4), round(STAGES[s_]['energy'] * es, 3)) for s_, a, b in stage_runs]
    perf.budget.update(bud.bars if hasattr(bud, 'bars') else {})
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
# harmony at a beat, the scales a soloist reaches for, the register of the arc, lines that answer, sequence and run.

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


def scale(ctx) -> set:
    """The key's pitch classes."""
    return set(key_of(ctx).pcs)


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


def fold(p: int, ctx) -> int:
    """p moved by octaves into ctx.range."""
    lo, hi = ctx.range
    while p > hi:
        p -= 12
    while p < lo:
        p += 12
    return p


def fit(pitches, ctx) -> list:
    """A line moved by octaves into ctx.range (then any stray note folded in)."""
    lo, hi = ctx.range
    ps = list(pitches)
    while ps and max(ps) > hi and min(ps) - 12 >= lo:
        ps = [p - 12 for p in ps]
    while ps and min(ps) < lo and max(ps) + 12 <= hi:
        ps = [p + 12 for p in ps]
    return [fold(p, ctx) for p in ps]


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
    """An answer: [(start, dur, pitch)] falling along the pentatonic from a 3rd-5th above the last note played (or the
    arc's centre), now and then a step back up, landing on a chord tone held to the slot's end."""
    pcs = pentatonic(ctx)
    if start is None:
        start = ctx.last.pitch + ctx.rng.choice((3, 5, 7)) if ctx.last is not None else center(ctx, 0.08)
    q = fold(snap(int(start), pcs), ctx)
    n = n if n is not None else 3 + int(round(ctx.density * 4 + ctx.rng.random()))
    g = grid_ if grid_ is not None else (0.5 if ctx.density < 0.5 else 0.25)
    while n > 2 and n * g > ctx.beats - 1.0:
        n -= 1
    line = []
    for _ in range(n):
        line.append(q)
        q = step(q, pcs, -1 if ctx.rng.random() < 0.8 else 1)
    tail = snap(line[-1], chord_tones(ctx, ctx.at + n * g), -1)
    line = fit(line + [tail], ctx)
    return ([(i * g, g, p) for i, p in enumerate(line[:-1])]
            + [(n * g, max(0.5, ctx.beats - n * g - 0.25), line[-1])])


def sequence_line(ctx, *, grid_=0.25, cell=None, length=None, start=None) -> list:
    """A sequence: a 3- or 4-note cell of the pentatonic repeated a step higher each time (a classic rock / sax
    build), [(start, dur, pitch)] on grid_ for `length` beats (default the slot minus a beat)."""
    pcs = pentatonic(ctx)
    cell = cell or (4 if grid_ <= 0.25 + _EPS else 3)
    L = (ctx.beats - 1.0) if length is None else length
    n_cells = max(1, int(L / (cell * grid_)))
    q0 = fold(snap(center(ctx, -0.12) if start is None else start, pcs), ctx)
    shape = [0, 1, 2, 1][:cell] if ctx.rng.random() < 0.5 else [0, 1, 2, 3][:cell]
    ps = []
    for ci in range(n_cells):
        base = step(q0, pcs, ci) if ci else q0
        ps += [step(base, pcs, k) if k else base for k in shape]
    ps = fit(ps, ctx)
    return [(i * grid_, grid_, p) for i, p in enumerate(ps)]


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
