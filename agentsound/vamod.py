"""VA modulation matrix: free, per-voice modulation routings for the 'va' instrument.

The va synth has fixed amp and filter envelopes (amp.*, fenv.* + filter.env); everything else that moves
is a routing in its "mods" list - as many as you like (up to 64), each with its own source:

    from agentsound import vamod as vm

    lead = inst.va(unison=3, mods=[
        vm.lfo('sine', hz=5.5, delay=0.3, fade=0.4, id='vib') >> ('pitch', 15),   # delayed vibrato, cents
        vm.env(a=0, d=0.08) >> ('pitch', 1200),                                   # pitch zap on every note
        vm.lfo('triangle', hz=0.3, mode='global') >> ('osc2.pw', 0.3),             # slow shared PWM
        vm.velocity() >> ('cutoff', 1.5),                                         # harder = brighter (octaves)
        vm.random() >> ('pan', 0.3),                                              # per-note stereo spread
        vm.macro(1) >> ('cutoff', 2),                                             # automate 'instrument.macro1'
    ])
    pad = patches.get('synthwave/warm_pad').with_mods(vm.lfo('sine', rate='2 beats', mode='global') >> ('cutoff', 0.5))
    lead.automate('instrument.mod.vib.amount', ramp(verse.start, chorus.start, 0, 25))   # routing amounts automate

A route is `source >> (target, amount)` (or `(target, amount, id)`). Sources (values the amount scales):
  lfo(shape, rate | hz=, phase, delay, fade, mode, unipolar)  -1..1 (unipolar: 0..1)
      shapes sine | triangle (tri) | saw (falls; saw_down) | ramp (rises; saw_up) | square |
      samplehold (sh, random) | smoothrandom (smooth). Phase 0: sine/triangle at 0 rising, saw at +1,
      ramp at -1, square high first. rate: '1/8', '1/4.', '1/8t', '3 beats', a number of beats (tempo
      synced) or '5hz'; hz= for free Hz. mode 'voice' (default): every note restarts its own LFO (delay /
      fade count from the note); 'global': one free-running LFO shared by all notes, on the song grid when
      tempo-synced (delay/fade still apply per note).
  env(a, d, s, r, curve='exp')      0..1 per note, times in seconds; curve 'exp' (analog, like amp/fenv)
                                    or 'linear'; r defaults to d. A pitch envelope: env(a=0, d=0.1) >> ('pitch', 1200)
  velocity()                        0..1 (note velocity)
  key(low=None, high=None)          octaves from A4 ((note-69)/12: C5 = +0.25); with low/high (notes or names)
                                    0..1 across that range
  random(seed=None, unipolar=False) -1..1 per note (0..1 unipolar), seeded by the song; routings share the
                                    value only when they give the same seed
  macro(n)                          0..1 = the instrument param 'macroN' (n = 1..8): automate or modulate
                                    'instrument.macroN' to move all its routings together

Targets and amount units (per voice unless noted; the amount is what a source value of 1 adds):
  pitch, osc1.pitch, osc2.pitch     cents (pitch = all oscillators + sub; osc1.pitch also moves the sub)
  osc1.pw, osc2.pw                  pulse width (added to osc1.pw / osc2.pw, kept in 0.02..0.98)
  osc1.level, osc2.level, sub.level, noise.level   level (added, kept in 0..1)
  cutoff                            octaves
  resonance, filter.drive           added to the param (kept in 0..1)
  amp                               dB (all amp routings add up; -96 = silent)
  pan                               added to pan (kept in -1..1)
  unison.detune                     added (kept in 0..1)
  fm                                osc2 -> osc1 phase-modulation index in radians (needs osc1.wave 'sine')
  hpf                               octaves of the global high-pass: only global sources (lfo mode='global', macro)

Every route's amount is the automatable instrument param 'mod.<id>.amount' (id given) or 'mod.<index>.amount'
(its position in the list), smoothed ~5 ms. A flat param 'mod.<id>.amount' also overrides it:
patch.but(**{'mod.vib.amount': 25}).
"""

from __future__ import annotations

import math
import re

from .modulation import parse_rate
from .theory import ComposeError, note as _note

__all__ = ['TARGETS', 'SHAPES', 'Source', 'Route', 'lfo', 'env', 'velocity', 'key', 'random', 'macro',
           'normalize_mods', 'describe']

MAX_MODS = 64
# target -> (amount min, amount max, unit, global)
TARGETS = {
    'pitch': (-4800.0, 4800.0, 'ct', False), 'osc1.pitch': (-4800.0, 4800.0, 'ct', False),
    'osc2.pitch': (-4800.0, 4800.0, 'ct', False), 'osc1.pw': (-0.9, 0.9, '', False), 'osc2.pw': (-0.9, 0.9, '', False),
    'osc1.level': (-1.0, 1.0, '', False), 'osc2.level': (-1.0, 1.0, '', False), 'sub.level': (-1.0, 1.0, '', False),
    'noise.level': (-1.0, 1.0, '', False), 'cutoff': (-10.0, 10.0, 'oct', False), 'resonance': (-1.0, 1.0, '', False),
    'filter.drive': (-1.0, 1.0, '', False), 'amp': (-96.0, 24.0, 'dB', False), 'pan': (-2.0, 2.0, '', False),
    'unison.detune': (-1.0, 1.0, '', False), 'fm': (-10.0, 10.0, 'rad', False), 'hpf': (-10.0, 10.0, 'oct', True),
}
SHAPES = ('sine', 'triangle', 'saw', 'ramp', 'square', 'samplehold', 'smoothrandom')
_SHAPE_ALIASES = {'tri': 'triangle', 'saw_down': 'saw', 'saw_up': 'ramp', 'sh': 'samplehold', 's&h': 'samplehold',
                  'random': 'samplehold', 'smooth': 'smoothrandom', 'smooth_random': 'smoothrandom'}
_SOURCE_KEYS = {
    'lfo': {'type', 'shape', 'rateHz', 'rateBeats', 'phase', 'delay', 'fade', 'mode', 'unipolar'},
    'env': {'type', 'attack', 'decay', 'sustain', 'release', 'curve'},
    'velocity': {'type'}, 'key': {'type', 'low', 'high'}, 'random': {'type', 'seed', 'unipolar'},
    'macro': {'type', 'index'},
}
_ID_RE = re.compile(r'^[a-z][a-z0-9_]{0,31}$')


def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        raise ComposeError(f"{what} = {x:g} is outside {lo:g}..{hi:g}")
    return float(x)


def _id(x, what: str) -> str | None:
    if x is None:
        return None
    if not isinstance(x, str) or not _ID_RE.match(x):
        raise ComposeError(f"{what}: id must be a lowercase name like 'vib' or 'pwm_1' (a-z, 0-9, _), got {x!r}")
    return x


def _clean(v: float):
    """Numbers as the JSON shows them: whole floats as ints (5.0 -> 5), else rounded to 9 digits."""
    v = round(float(v), 9)
    return int(v) if v.is_integer() and abs(v) < 1e15 else v


class Source:
    """A modulation source (its JSON definition + an optional id for the route). `source >> (target, amount)`
    makes a Route; `source.to(target, amount, id=None)` is the same."""

    __slots__ = ('data', 'id')

    def __init__(self, data: dict, id: str | None = None):  # noqa: A002
        self.data = dict(data)
        self.id = _id(id, f"{self.data.get('type', 'source')} source")

    def to(self, target: str, amount: float, id: str | None = None) -> 'Route':  # noqa: A002
        return Route(self, target, amount, id if id is not None else self.id)

    def __rshift__(self, dest) -> 'Route':
        if isinstance(dest, tuple) and len(dest) in (2, 3):
            return self.to(*dest)
        raise ComposeError(f"{self!r} >> {dest!r}: the right side is (target, amount) or (target, amount, id), "
                           f"e.g. >> ('cutoff', 1.5); targets: {', '.join(TARGETS)}")

    def to_json(self) -> dict:
        return dict(self.data)

    def __eq__(self, other) -> bool:
        return isinstance(other, Source) and (self.data, self.id) == (other.data, other.id)

    __hash__ = None

    def __repr__(self) -> str:
        return f"Source({describe_source(self.data)})"


class Route:
    """One routing: source -> target with an amount (the target's unit at full source), optional id."""

    __slots__ = ('source', 'target', 'amount', 'id')

    def __init__(self, source: Source, target: str, amount: float, id: str | None = None):  # noqa: A002
        if not isinstance(source, Source):
            raise ComposeError(f"a route needs a source from vamod.lfo()/env()/velocity()/key()/random()/macro(), "
                               f"got {source!r}")
        if target not in TARGETS:
            raise ComposeError(f"unknown va modulation target {target!r}; targets: {', '.join(TARGETS)}")
        lo, hi, unit, glob = TARGETS[target]
        self.amount = _num(amount, f"amount for {target!r} ({unit or 'level'})", lo, hi)
        if glob and not _is_global(source.data):
            raise ComposeError(f"{target!r} is one high-pass after all voices: drive it from a global source "
                               f"(lfo(..., mode='global') without delay/fade, or macro(n)), not {describe_source(source.data)}")
        self.source = source
        self.target = target
        self.id = _id(id, f"route to {target!r}")

    def named(self, id: str) -> 'Route':  # noqa: A002
        """Copy with an id: its amount becomes the automatable param 'mod.<id>.amount'."""
        return Route(self.source, self.target, self.amount, id)

    def to_json(self) -> dict:
        d = {'source': self.source.to_json(), 'target': self.target, 'amount': _clean(self.amount)}
        if self.id:
            d['id'] = self.id
        return d

    def __eq__(self, other) -> bool:
        return isinstance(other, Route) and self.to_json() == other.to_json()

    __hash__ = None

    def __repr__(self) -> str:
        return f"Route({describe_route(self.to_json())})"


def _is_global(src: dict) -> bool:
    return src.get('type') == 'macro' or (src.get('type') == 'lfo' and src.get('mode') == 'global'
                                          and not src.get('delay') and not src.get('fade'))


# ------------------------------------------------------------------------------------------ sources

def lfo(shape: str = 'sine', rate=None, *, hz: float | None = None, phase: float = 0.0, delay: float = 0.0,
        fade: float = 0.0, mode: str = 'voice', unipolar: bool = False, id: str | None = None) -> Source:  # noqa: A002
    """LFO source, -1..1 (unipolar=True: 0..1). Give rate= (note value / beats: tempo-synced, or '5hz') or
    hz=. mode='voice': restarts on every note; 'global': one shared free-running LFO (on the song grid when
    synced). delay / fade (seconds) hold it back after each note start, then fade it in."""
    if not isinstance(shape, str):
        raise ComposeError(f"lfo shape must be a string, got {shape!r}")
    s = _SHAPE_ALIASES.get(shape.strip().lower(), shape.strip().lower())
    if s not in SHAPES:
        raise ComposeError(f"unknown lfo shape {shape!r}; use {', '.join(SHAPES)} (aliases tri, saw_down, saw_up, sh, smooth)")
    d: dict = {'type': 'lfo', 'shape': s}
    if (rate is None) == (hz is None):
        raise ComposeError(f"lfo({shape!r}): give rate= (tempo-synced: '1/8', '1/4.', '3 beats', a number of beats; "
                           f"or '5hz') or hz= (free), exactly one")
    if hz is not None:
        d['rateHz'] = _clean(_num(hz, f"lfo({shape!r}) hz", 0.001, 200.0))
    else:
        unit, v = parse_rate(rate, f"lfo({shape!r}) rate")
        if unit == 'bars':
            raise ComposeError(f"lfo({shape!r}) rate {rate!r}: the synth doesn't know the song's meter; give beats "
                               f"(4/4: '1 bar' = 4, '2 bars' = 8) or a note value")
        if unit == 'hz':
            d['rateHz'] = _clean(_num(v, f"lfo({shape!r}) rate (Hz)", 0.001, 200.0))
        else:
            d['rateBeats'] = _clean(_num(v, f"lfo({shape!r}) rate (beats)", 1.0 / 1024.0, 1024.0))
    if _num(phase, f"lfo({shape!r}) phase", 0.0, 1.0):
        d['phase'] = _clean(phase)
    if _num(delay, f"lfo({shape!r}) delay (s)", 0.0, 30.0):
        d['delay'] = _clean(delay)
    if _num(fade, f"lfo({shape!r}) fade (s)", 0.0, 30.0):
        d['fade'] = _clean(fade)
    if mode not in ('voice', 'global'):
        raise ComposeError(f"lfo({shape!r}) mode must be 'voice' (restarts per note) or 'global' (shared), got {mode!r}")
    if mode == 'global':
        d['mode'] = 'global'
    if not isinstance(unipolar, bool):
        raise ComposeError(f"lfo({shape!r}) unipolar must be True or False")
    if unipolar:
        d['unipolar'] = True
    return Source(d, id)


def env(a: float = 0.0, d: float = 0.3, s: float = 0.0, r: float | None = None, *, curve: str = 'exp',
        id: str | None = None) -> Source:  # noqa: A002
    """Per-note envelope source 0..1: attack a, decay d, release r (seconds; r defaults to d), sustain level s.
    curve 'exp' (analog RC shape, like the amp / filter envelopes) or 'linear'."""
    data = {'type': 'env', 'attack': _clean(_num(a, 'env attack (s)', 0.0, 30.0)),
            'decay': _clean(_num(d, 'env decay (s)', 0.001, 30.0)),
            'sustain': _clean(_num(s, 'env sustain', 0.0, 1.0)),
            'release': _clean(_num(d if r is None else r, 'env release (s)', 0.001, 30.0))}
    if curve not in ('exp', 'linear'):
        raise ComposeError(f"env curve must be 'exp' (analog) or 'linear', got {curve!r}")
    if curve == 'linear':
        data['curve'] = 'linear'
    return Source(data, id)


def velocity(id: str | None = None) -> Source:  # noqa: A002
    """Note velocity, 0..1."""
    return Source({'type': 'velocity'}, id)


def key(low=None, high=None, id: str | None = None) -> Source:  # noqa: A002
    """Key tracking: octaves from A4 ((note - 69) / 12), or with low/high (MIDI numbers or names) 0..1 across
    that range (clamped)."""
    if (low is None) != (high is None):
        raise ComposeError("key(): give both low= and high= (0..1 across that range) or neither (octaves from A4)")
    data: dict = {'type': 'key'}
    if low is not None:
        lo, hi = _note(low), _note(high)
        if hi <= lo:
            raise ComposeError(f"key(): high {high!r} must be above low {low!r}")
        data.update(low=lo, high=hi)
    return Source(data, id)


def random(seed: int | None = None, unipolar: bool = False, id: str | None = None) -> Source:  # noqa: A002
    """A per-note random value -1..1 (0..1 unipolar), drawn from the song seed and the note's position (so
    renders and previews agree). Routings without a seed are independent; the same seed = the same value."""
    data: dict = {'type': 'random'}
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 1_000_000_000:
            raise ComposeError(f"random(seed=...) must be a whole number 0..1e9, got {seed!r}")
        data['seed'] = seed
    if not isinstance(unipolar, bool):
        raise ComposeError("random(unipolar=...) must be True or False")
    if unipolar:
        data['unipolar'] = True
    return Source(data, id)


def macro(n: int, id: str | None = None) -> Source:  # noqa: A002
    """Macro n (1..8): the value (0..1) of the instrument param 'macroN'. Automate / modulate
    'instrument.macroN' at song level to move every routing it feeds."""
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 8:
        raise ComposeError(f"macro(n): n must be 1..8, got {n!r}")
    return Source({'type': 'macro', 'index': n}, id)


# ------------------------------------------------------------------------------- lists / validation

def _check_dict(r: dict, where: str) -> dict:
    extra = set(r) - {'source', 'target', 'amount', 'id'}
    if extra or not {'source', 'target', 'amount'} <= set(r):
        raise ComposeError(f"{where}: a routing is {{'source': {{...}}, 'target': ..., 'amount': ..., 'id'?: ...}}, "
                           f"got keys {sorted(r)}")
    src = r['source']
    if not isinstance(src, dict) or src.get('type') not in _SOURCE_KEYS:
        raise ComposeError(f"{where}: 'source' must be a dict with 'type' one of {', '.join(_SOURCE_KEYS)}, got {src!r}")
    bad = set(src) - _SOURCE_KEYS[src['type']]
    if bad:
        raise ComposeError(f"{where}: unknown key(s) {sorted(bad)} for a {src['type']} source "
                           f"(keys: {', '.join(sorted(_SOURCE_KEYS[src['type']]))})")
    route = Route(Source(src), r['target'], r['amount'], r.get('id'))  # validates target, amount, id, global
    return route.to_json()


def normalize_mods(value, where: str = "va 'mods'") -> list[dict]:
    """The JSON list for the va param 'mods' from Routes (source >> (target, amount)) and/or routing dicts."""
    if isinstance(value, (Route, dict)):
        value = [value]
    if not isinstance(value, (list, tuple)):
        raise ComposeError(f"{where} must be a list of routes like [vamod.lfo('sine', hz=5) >> ('pitch', 15)], "
                           f"got {value!r}")
    if len(value) > MAX_MODS:
        raise ComposeError(f"{where}: {len(value)} routings; at most {MAX_MODS}")
    out: list[dict] = []
    for i, r in enumerate(value):
        w = f"{where}[{i}]"
        if isinstance(r, Route):
            out.append(r.to_json())
        elif isinstance(r, dict):
            out.append(_check_dict(r, w))
        elif isinstance(r, Source):
            raise ComposeError(f"{w}: {r!r} has no target; write source >> ('cutoff', 1.5)")
        else:
            raise ComposeError(f"{w}: not a route: {r!r} (use vamod.lfo(...) >> ('pitch', 15))")
    ids = [r['id'] for r in out if 'id' in r]
    dup = sorted({x for x in ids if ids.count(x) > 1})
    if dup:
        raise ComposeError(f"{where}: id(s) {', '.join(map(repr, dup))} used twice (ids name 'mod.<id>.amount')")
    return out


# ------------------------------------------------------------------------------------ description

def describe_source(src: dict) -> str:
    t = src.get('type')
    if t == 'lfo':
        rate = f"{src['rateHz']:g} Hz" if 'rateHz' in src else f"{src.get('rateBeats', 0):g} beats"
        extra = ''.join(f" {k} {src[k]:g}" for k in ('phase', 'delay', 'fade') if k in src)
        return (f"lfo {src.get('shape', 'sine')} {rate}{extra}" + (' global' if src.get('mode') == 'global' else '')
                + (' unipolar' if src.get('unipolar') else ''))
    if t == 'env':
        return (f"env a {src.get('attack', 0):g} d {src.get('decay', 0.3):g} s {src.get('sustain', 0):g} "
                f"r {src.get('release', 0.3):g}" + (' linear' if src.get('curve') == 'linear' else ''))
    if t == 'key' and 'low' in src:
        return f"key {src['low']}..{src['high']}"
    if t == 'random':
        return 'random' + (f" seed {src['seed']}" if 'seed' in src else '') + (' unipolar' if src.get('unipolar') else '')
    if t == 'macro':
        return f"macro{src.get('index')}"
    return str(t)


def describe_route(r: dict) -> str:
    unit = TARGETS.get(r['target'], (0, 0, '', False))[2]
    return (f"{describe_source(r['source'])} -> {r['target']} {r['amount']:+g}{(' ' + unit) if unit else ''}"
            + (f" [mod.{r['id']}.amount]" if 'id' in r else ''))


def describe(mods) -> str:
    """One line per routing, with the name of its automatable amount param."""
    rows = normalize_mods(mods)
    return '\n'.join(describe_route({**r, 'id': r.get('id', str(i))}) for i, r in enumerate(rows))
