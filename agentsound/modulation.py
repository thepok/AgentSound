"""Modulators: parameters are instruments too.

A modulator drives one target of a track / bus / master continuously while the engine renders
(re-evaluated every 32 samples, on the song's beat grid): an LFO, a step sequence or trance gate, an
envelope follower of another node, a per-note envelope, or seeded random steps. Build one with a
generator below and attach it with node.modulate(target, mod, window=...):

    lead.modulate('instrument.cutoff', lfo('sine', rate='1/4', min=600, max=4000, curve='exp'))
    pad.modulate('gainDb', gate('x.x.xx.x.x.xx.x.', rate='1/16', depth=18))        # trance gate
    bass.modulate('instrument.cutoff', follow('drums', min=300, max=2500, curve='exp'))
    arp.modulate('instrument.cutoff', steps([400, 2400, 800, 3200], rate='1/16', glide=0.3, curve='exp'))
    pad.modulate('pan', lfo('triangle', rate='2 bars', depth=0.6), window=chorus)
    pad.modulate('gainDb', envelope(decay='1/4', trigger=kit, pitches='kick', depth=-10))   # pump

Mapping (every generator takes one of the two):
  * min=, max=      absolute: the source sweeps the target between min and max (curve='exp' moves
                    geometrically - use it for Hz). steps() without min/max takes target values directly.
  * depth=          offset: source * depth is added to the target's automation lane, or to base= (for
                    gainDb / pan / sends and explicitly set params the compose layer fills base in).
                    Sources are bipolar (-1..1: lfo, steps, gate, sample_hold) or unipolar (0..1: follow,
                    envelope). With curve='exp' depth is in octaves: value * 2^(source * depth).
Any of min / max / depth / base (and rate, glide, smooth, phase) may be an automation point list instead
of a number, e.g. depth=ramp(verse.start, chorus.start, 0, 1.5): the wobble grows. Or name the modulator
(name='wob') and automate its fields later: node.automate('mod.wob.depth', ...).

Rates: note values '1/16' '1/8.' '1/8t' '1/4', '1 bar' '2 bars' '1/2 bar', '3 beats', a number of beats,
or (lfo only) '5hz' for free-running vibrato / tremolo speeds.
"""

from __future__ import annotations

import copy
import math
import re

from . import automation as _auto
from .patterns import beats as _beats
from .theory import ComposeError

LFO_SHAPES = ('sine', 'triangle', 'saw', 'ramp', 'square', 'random', 'smoothrandom')
_SHAPE_ALIASES = {'tri': 'triangle', 'saw_down': 'saw', 'saw_up': 'ramp', 'sh': 'random', 's&h': 'random',
                  'smooth_random': 'smoothrandom', 'smooth': 'smoothrandom'}
_MIN_RATE, _MAX_RATE = 1.0 / 1024.0, 1024.0   # beats
_MIN_HZ, _MAX_HZ = 0.001, 50.0


def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        rng = f"{lo:g}..{hi:g}" if lo is not None and hi is not None else f">= {lo:g}" if lo is not None else f"<= {hi:g}"
        raise ComposeError(f"{what} = {x:g} must be {rng}" if lo is None or hi is None else f"{what} = {x:g} is outside {rng}")
    return float(x)


def _is_points(v) -> bool:
    return isinstance(v, (list, tuple)) and len(v) > 0 and all(isinstance(p, (list, tuple)) for p in v)


def _fraction(s: str) -> float:
    if '/' in s:
        a, b = s.split('/', 1)
        if float(b) == 0:
            raise ValueError(s)
        return float(a) / float(b)
    return float(s)


def parse_rate(rate, what: str = 'rate') -> tuple[str, float]:
    """('beats' | 'bars' | 'hz', value) of a rate: '1/16', '1/8.', '1/8t', '2 bars', '1/2 bar', '3 beats',
    '5hz', or a number of beats. Bars are resolved with the song's meter at compile."""
    hint = (f"{what} {rate!r}: use a note value ('1/16', '1/8.' dotted, '1/8t' triplet), 'N bars', 'N beats', "
            f"'N hz' or a number of beats")
    if isinstance(rate, bool):
        raise ComposeError(hint)
    if isinstance(rate, (int, float)):
        if not math.isfinite(rate) or rate <= 0:
            raise ComposeError(f"{what} must be > 0 beats, got {rate!r}")
        return 'beats', float(rate)
    if isinstance(rate, str):
        s = rate.strip().lower()
        m = re.match(r'^(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)\s*(bars?|beats?|hz)$', s)
        if m:
            try:
                v = _fraction(m.group(1))
            except (ValueError, ZeroDivisionError):
                raise ComposeError(hint) from None
            if v <= 0:
                raise ComposeError(hint)
            unit = m.group(2)
            return ('bars' if unit.startswith('bar') else 'beats' if unit.startswith('beat') else 'hz'), v
        try:
            v = _beats(s)
        except ComposeError:
            raise ComposeError(hint) from None
        if v > 0:
            return 'beats', v
    raise ComposeError(hint)


class Mod:
    """A modulator: source + mapping. Made by lfo() / steps() / gate() / follow() / envelope() /
    sample_hold(); attach with node.modulate(target, mod, window=...). Immutable once attached (copied)."""

    __slots__ = ('kind', 'source', 'rate', 'mode', 'curve', 'mapping', 'lanes', 'name', 'node', 'trigger',
                 'pitches', 'retrigger')

    def __init__(self, kind: str, name: str | None = None):
        self.kind = kind                 # lfo | steps | follow | envelope | random
        self.source: dict = {'type': kind}
        self.rate: tuple[str, float] | None = None
        self.mode = 'absolute'
        self.curve = 'linear'
        self.mapping: dict[str, float] = {}      # min / max / depth / base
        self.lanes: dict[str, list] = {}         # render-JSON field -> automation points
        if name is not None and (not isinstance(name, str) or not re.match(r'^[a-z][a-z0-9_]*$', name)):
            raise ComposeError(f"modulator name must be a lowercase identifier like 'wob', got {name!r}")
        self.name = name
        self.node = None                 # follow: node id (after modulate())
        self.trigger = None              # envelope: None = own notes, else a track id
        self.pitches: tuple[int, ...] | None = None
        self.retrigger = False

    def copy(self) -> 'Mod':
        m = Mod.__new__(Mod)
        for k in Mod.__slots__:
            setattr(m, k, copy.deepcopy(getattr(self, k)))
        return m

    @property
    def unipolar(self) -> bool:
        return self.kind in ('follow', 'envelope')

    def __repr__(self) -> str:
        what = self.source.get('shape', '')
        rng = (f"{self.mapping.get('min'):g}..{self.mapping.get('max'):g}" if self.mode == 'absolute' and 'min' in self.mapping
               else f"depth {self.mapping['depth']:g}" if 'depth' in self.mapping else 'values')
        return f"Mod({self.kind}{' ' + what if what else ''}, {self.mode} {rng}{', exp' if self.curve == 'exp' else ''})"

    # --- helpers for the generators
    def _field(self, field: str, v, what: str, lo=None, hi=None) -> float:
        """A number, or an automation point list (its first value is the static value)."""
        if _is_points(v):
            pts = _auto.normalize(list(v), what)
            for b, val, *_ in pts:
                _num(val, f"{what} (point at beat {b:g})", lo, hi)
            self.lanes[field] = list(v)
            return pts[0][1]
        return _num(v, what, lo, hi)

    def _map(self, what: str, mn, mx, depth, base, curve, steps_values=None) -> 'Mod':
        if curve not in ('linear', 'exp'):
            raise ComposeError(f"{what}: curve must be 'linear' or 'exp' (exp for Hz: even musical speed), got {curve!r}")
        self.curve = curve
        absolute = mn is not None or mx is not None
        if absolute and depth is not None:
            raise ComposeError(f"{what}: give min=/max= (absolute sweep) or depth= (offset around the current value), not both")
        if depth is not None:
            self.mode = 'offset'
            lim = 10.0 if curve == 'exp' else None
            self.mapping['depth'] = self._field('depth', depth, f"{what} depth" + (' (octaves)' if lim else ''),
                                                -lim if lim else None, lim)
        elif absolute:
            if steps_values is not None:
                raise ComposeError(f"{what}: steps() values are the target values themselves; drop min=/max= "
                                   f"(or give values in -1..1 with depth=)")
            if mn is None or mx is None:
                raise ComposeError(f"{what}: absolute mapping needs both min= and max=")
            lo = 1e-6 if curve == 'exp' else None
            self.mapping['min'] = self._field('min', mn, f"{what} min" + (" (curve='exp' needs > 0)" if lo else ''), lo)
            self.mapping['max'] = self._field('max', mx, f"{what} max" + (" (curve='exp' needs > 0)" if lo else ''), lo)
        elif steps_values is None:
            raise ComposeError(f"{what}: say how it moves the target: min= and max= (the range it sweeps) or "
                               f"depth= (how far it moves around the automated / base value)")
        if steps_values is not None:
            for k, v in enumerate(steps_values):
                if self.mode == 'offset' and not -1.0 <= v <= 1.0:
                    raise ComposeError(f"{what}: with depth= the values are -1..1 (scaled by depth); value #{k} is {v:g}")
                if self.mode == 'absolute' and curve == 'exp' and v <= 0:
                    raise ComposeError(f"{what}: curve='exp' needs values > 0; value #{k} is {v:g}")
        if base is not None:
            self.mapping['base'] = self._field('base', base, f"{what} base",
                                               1e-6 if (self.mode == 'offset' and curve == 'exp') else None)
        return self

    def _set_rate(self, rate, what: str, hz_ok: bool) -> None:
        if _is_points(rate):
            if self.kind == 'steps':
                raise ComposeError(f"{what}: the step length can't be automated (it would break the grid); "
                                   f"use a fixed rate like '1/16'")
            self.rate = ('beats', self._field('rateBeats', rate, f"{what} rate (beats)", _MIN_RATE, _MAX_RATE))
            return
        unit, v = parse_rate(rate, f"{what} rate")
        if unit == 'hz' and not hz_ok:
            raise ComposeError(f"{what}: rate {rate!r} - only lfo() runs in Hz; steps and random steps follow the beat grid")
        if unit == 'hz':
            _num(v, f"{what} rate (Hz)", _MIN_HZ, _MAX_HZ)
        self.rate = (unit, v)

    # --- compile
    def source_json(self, beats_per_bar: float, where: str) -> dict:
        d = {'type': self.kind}
        if 'shape' in self.source:
            d['shape'] = self.source['shape']
        if self.rate is not None:
            unit, v = self.rate
            if unit == 'hz':
                d['rateHz'] = round(v, 6)
            else:
                b = v * beats_per_bar if unit == 'bars' else v
                if not _MIN_RATE <= b <= _MAX_RATE:
                    raise ComposeError(f"{where}: rate of {b:g} beats is outside {_MIN_RATE:g}..{_MAX_RATE:g}")
                d['stepBeats' if self.kind == 'steps' else 'rateBeats'] = round(b, 9)
        d.update((k, v) for k, v in self.source.items() if k not in d)
        if self.kind == 'follow':
            d['node'] = self.node
        if self.kind == 'envelope':
            d['trigger'] = self.trigger or 'note'
        if self.retrigger:
            d['retrigger'] = 'note'
        return d


# ----------------------------------------------------------------------------------- generators

def _shape(shape) -> str:
    if not isinstance(shape, str):
        raise ComposeError(f"lfo shape must be a string, got {shape!r}")
    s = shape.strip().lower()
    s = _SHAPE_ALIASES.get(s, s)
    if s not in LFO_SHAPES:
        raise ComposeError(f"unknown lfo shape {shape!r}; use sine, triangle, saw (falls), ramp (rises), square, "
                           f"random (sample & hold per cycle) or smoothrandom")
    return s


def lfo(*args, **kw):
    """lfo(shape='sine', rate='1/4', *, min=, max= | depth=, base=None, curve='linear', phase=0,
    retrigger=False, name=None) -> a modulator for node.modulate().

    Shapes (phase 0 = the start of each cycle, on the song grid): sine and triangle start at their minimum
    and peak mid-cycle (a quarter-note filter wobble opens between the beats); saw falls (aliases
    saw_down), ramp rises (saw_up); square is high for the first half; random holds a new seeded value per
    cycle, smoothrandom glides between them. rate: '1/4', '1/8t', '2 bars', '5hz' ... phase: 0..1 cycles.
    retrigger=True restarts the cycle on every note of the track.

    (The old form lfo(start, end, lo, hi, period=...) still returns automation points for automate().)"""
    if (args and not isinstance(args[0], str)) or any(k in kw for k in ('start', 'end', 'lo', 'hi', 'period', 'log')):
        return _auto.lfo(*args, **kw)
    return _lfo(*args, **kw)


def _lfo(shape='sine', rate='1/4', *, min=None, max=None, depth=None, base=None, curve='linear',  # noqa: A002
         phase=0.0, retrigger=False, name=None) -> Mod:
    m = Mod('lfo', name)
    m.source['shape'] = _shape(shape)
    what = f"lfo({shape!r})"
    m._set_rate(rate, what, hz_ok=True)
    ph = m._field('phase', phase, f"{what} phase", 0.0, 1.0)
    if ph or 'phase' in m.lanes:
        m.source['phase'] = ph
    m.retrigger = bool(retrigger)
    return m._map(what, min, max, depth, base, curve)


def steps(values, rate=None, **kw):
    """steps(values, rate='1/16', *, glide=0, loop=True, depth=None, base=None, curve='linear', name=None)
    -> a step-sequencer modulator. values are target values ([400, 2400, 800, 3200] Hz) or, with depth=,
    -1..1 scaled by depth. One value per `rate`, counted from the window start (or beat 0), looping.
    glide 0..1 = the fraction of each step spent gliding into its value (curve='exp': geometric glides).

    (The old form steps({beat: value}) still returns stepped automation points.)"""
    if isinstance(values, dict):
        if rate is not None or kw:
            raise ComposeError("steps({beat: value}) makes automation points and takes no other arguments; "
                               "for a step modulator pass a list: steps([400, 2400], rate='1/16')")
        return _auto.steps(values)
    return _steps(values, '1/16' if rate is None else rate, **kw)


def _steps(values, rate='1/16', *, glide=0.0, loop=True, depth=None, base=None, curve='linear', name=None,
           min=None, max=None) -> Mod:  # noqa: A002
    if isinstance(values, str) or not isinstance(values, (list, tuple)) or not values:
        raise ComposeError(f"steps() needs a non-empty list of numbers, got {values!r}")
    if len(values) > 1024:
        raise ComposeError(f"steps() takes at most 1024 values, got {len(values)}")
    vals = [_num(v, f"steps() value #{k}") for k, v in enumerate(values)]
    m = Mod('steps', name)
    what = 'steps()'
    m._set_rate(rate, what, hz_ok=False)
    m.source['values'] = [round(v, 6) for v in vals]
    g = m._field('glide', glide, f"{what} glide", 0.0, 1.0)
    if g or 'glide' in m.lanes:
        m.source['glide'] = g
    if not loop:
        m.source['loop'] = False
    return m._map(what, min, max, depth, base, curve, steps_values=vals)


_GATE_HELP = "use x (open), . (closed), 0-9 (partly open: 0 closed .. 9 open), _ (repeat the previous step)"


def gate_values(pattern: str) -> list[float]:
    """Step values of a gate pattern: 'x' -> 0 (open), '.' / '-' -> -1 (closed), digit d -> d/9 - 1,
    '_' repeats the previous step; spaces and '|' are ignored."""
    if not isinstance(pattern, str):
        raise ComposeError(f"gate pattern must be a string like 'x.x.xx.x', got {pattern!r}")
    vals: list[float] = []
    for ch in pattern:
        if ch in ' |\t\n':
            continue
        if ch in 'xX':
            vals.append(0.0)
        elif ch in '.-':
            vals.append(-1.0)
        elif ch.isdigit():
            vals.append(round(int(ch) / 9.0 - 1.0, 6))
        elif ch == '_':
            if not vals:
                raise ComposeError(f"gate pattern {pattern!r} starts with '_' (nothing to repeat)")
            vals.append(vals[-1])
        else:
            raise ComposeError(f"gate pattern {pattern!r}: unknown character {ch!r}; {_GATE_HELP}")
    if not vals:
        raise ComposeError(f"gate pattern {pattern!r} is empty; {_GATE_HELP}")
    return vals


def gate(pattern: str, rate='1/16', *, depth=24.0, glide=0.0, base=None, curve='linear', name=None) -> Mod:
    """Trance gate: a rhythmic on/off pattern, one character per step ('x.x.xx.x.x.xx.x.' at '1/16').
    On 'gainDb' closed steps sit `depth` dB below the fader (glide softens the edges). Works on any target:
    gate('x..x', depth=2, curve='exp') on 'instrument.cutoff' drops the cutoff two octaves on closed steps.
    """
    m = _steps(gate_values(pattern), rate, glide=glide, depth=depth, base=base, curve=curve, name=name)
    return m


def follow(node, *, attack: float = 5.0, release: float = 120.0, gain_db: float = 0.0, pitches=None,
           min=None, max=None, depth=None, base=None, curve='linear', name=None, tap=None) -> Mod:  # noqa: A002
    """Envelope follower of another track / bus (its post-fader level, like a sidechain key): 0 when it is
    silent, 1 at full scale (a key peaking at -6 dBFS gives 0.5; gain_db drives it harder).
    attack / release in ms. pitches='kick' follows only those notes of a drum track (muted key track).
    tap= where it listens: post-fader (default), 'prefader', 'prefx' or 'pre:<fx name>' (agentsound.patches.TAPS).
        bass.modulate('instrument.cutoff', follow(kit, pitches='kick', min=300, max=2500, curve='exp'))
        pad.modulate('gainDb', follow('lead', depth=-6))     # duck the pad under the lead"""
    from .patches import check_tap
    m = Mod('follow', name)
    m.node = node
    m.pitches = _pitches(pitches)
    t = check_tap(tap, 'follow()')
    if t is not None:
        m.source['tap'] = t
    m.source['attackMs'] = m._field('attackMs', attack, 'follow() attack (ms)', 0.0, 10000.0)
    m.source['releaseMs'] = m._field('releaseMs', release, 'follow() release (ms)', 0.0, 10000.0)
    g = m._field('gainDb', gain_db, 'follow() gain_db', -48.0, 48.0)
    if g or 'gainDb' in m.lanes:
        m.source['gainDb'] = g
    return m._map('follow()', min, max, depth, base, curve)


def envelope(attack=0.0, decay='1/8', sustain: float = 0.0, release=None, *, trigger=None, pitches=None,
             min=None, max=None, depth=None, base=None, curve='linear', name=None) -> Mod:  # noqa: A002
    """Linear ADSR (times in beats or note values) restarted by every note-on of this track, or of
    trigger=<track> (pitches='kick' picks notes of a drum track). The gate is open while a trigger note is
    held; release=None releases as fast as it decays. Output 0..1:
        arp.modulate('instrument.cutoff', envelope(decay='1/8', min=500, max=5000, curve='exp'))  # pluck
        pad.modulate('gainDb', envelope(decay='1/4', trigger=kit, pitches='kick', depth=-10))     # pump"""
    m = Mod('envelope', name)
    m.trigger = trigger
    m.pitches = _pitches(pitches)

    def t(v, field, what):
        if _is_points(v):
            return m._field(field, v, f"envelope() {what} (beats)", 0.0, 1024.0)
        return _num(_beats(v), f"envelope() {what} (beats)", 0.0, 1024.0)

    m.source['attackBeats'] = round(t(attack, 'attackBeats', 'attack'), 9)
    m.source['decayBeats'] = round(t(decay, 'decayBeats', 'decay'), 9)
    m.source['sustain'] = m._field('sustain', sustain, 'envelope() sustain', 0.0, 1.0)
    m.source['releaseBeats'] = round(m.source['decayBeats'] if release is None else t(release, 'releaseBeats', 'release'), 9)
    return m._map('envelope()', min, max, depth, base, curve)


def sample_hold(rate='1/16', *, smooth: float = 0.0, min=None, max=None, depth=None, base=None,  # noqa: A002
                curve='linear', name=None) -> Mod:
    """Seeded random steps (sample & hold): a new value every `rate`, deterministic from the song seed.
    smooth 0..1 glides into each new value (1 = continuous random drift).
        lead.modulate('instrument.cutoff', sample_hold('1/16', min=800, max=5000, curve='exp'))
        pad.modulate('instrument.osc2.fine', sample_hold('1 bar', smooth=1, depth=6, base=8))  # drift"""
    m = Mod('random', name)
    m._set_rate(rate, 'sample_hold()', hz_ok=False)
    sm = m._field('smooth', smooth, 'sample_hold() smooth', 0.0, 1.0)
    if sm or 'smooth' in m.lanes:
        m.source['smooth'] = sm
    return m._map('sample_hold()', min, max, depth, base, curve)


def _pitches(pitches) -> tuple[int, ...] | None:
    if pitches is None:
        return None
    from .patterns import drum
    ps = pitches if isinstance(pitches, (list, tuple, set)) else [pitches]
    return tuple(sorted({drum(p) for p in ps}))


# Friendly field names for automate('mod.<name|index>.<field>', ...), per source kind.
def field_name(mod: Mod, field: str, where: str) -> str:
    """Render-JSON field name of a modulator field ('rate' -> 'rateBeats' / 'rateHz' / 'stepBeats' ...)."""
    alias = {'rate': 'rateHz' if mod.rate and mod.rate[0] == 'hz' else 'rateBeats',
             'attack': 'attackMs' if mod.kind == 'follow' else 'attackBeats',
             'release': 'releaseMs' if mod.kind == 'follow' else 'releaseBeats',
             'decay': 'decayBeats', 'gain_db': 'gainDb'}
    f = alias.get(field, field)
    known = {'depth', 'min', 'max', 'base', 'rateBeats', 'rateHz', 'phase', 'glide', 'smooth', 'attackMs',
             'releaseMs', 'gainDb', 'attackBeats', 'decayBeats', 'sustain', 'releaseBeats'}
    if f not in known:
        raise ComposeError(f"{where}: unknown modulator field {field!r}; fields: depth min max base rate phase glide "
                           f"smooth attack decay sustain release gain_db")
    if mod.kind == 'steps' and f in ('rateBeats', 'rateHz'):
        raise ComposeError(f"{where}: the step length of steps()/gate() can't be automated (it would break the grid)")
    return f
