"""Song: sections, tracks, buses, master chain, and compile() to the engine's render JSON.

    song = Song('Chrome Horizon', tempo=104, key='A minor', seed=7)
    intro = song.section('intro', bars=8)            # sequential; .start/.end in beats
    verse = song.section('verse', bars=16)
    hall = song.hall()                               # reverb return bus
    pad = song.track('pad', 'synthwave/warm_pad', sends={hall: -10})
    pad.loop(song.prog('i VI III VII'), intro, verse)
    song.sidechain(pad, key=drums, pitches='kick')   # pump the pad from the kick only
    render = song.compile()                          # validated dict (docs/RENDER_FORMAT.md)

Positions are beats (floats) or Sections (= their start); section.bar(4) is the 5th bar (0-based),
section.bar(-1) the last bar, section.beat(-2) two beats before the section end.

Tempo and meter (agentsound/tempo.py): beats stay quarter notes; the tempo can move (song.set_tempo,
tempo_ramp, ritardando, accelerando, fermata, rubato -> a "tempoMap" in the render JSON) and every section can
have its own meter (song.section('waltz', bars=8, meter=(3, 4)): 3 beats per bar, 6/8 = 3 beats too).
"""

from __future__ import annotations

import json
import linecache
import math
import os
import random
import re
import sys
from pathlib import Path

from . import articulation as _art
from . import automation as _auto
from . import modulation as _modulation
from . import patches as _patches
from . import silent_notes as _silent
from . import tempo as _tempo
from .humanize import _groove
from .humanize import groove as _apply_groove
from .humanize import humanize as _apply_humanize
from .modulation import Mod
from .patches import FX, Instrument, Patch, _ref
from .patterns import Clip, Note, as_clip, drum, seed_int
from .theory import ComposeError, Key, Progression

_ID_RE = re.compile(r'^[a-z0-9_-]{1,48}$')
_TARGET_RE = re.compile(r'^(gainDb|pan|instrument\.[A-Za-z0-9_.]+|fx\.[A-Za-z0-9_]+\.[A-Za-z0-9_.]+|send\.[a-z0-9_-]+'
                        r'|mod\.[A-Za-z0-9_]+\.[A-Za-z_]+)$')
_MIN_DB, _MAX_DB = -120.0, 24.0
_RANGES = {'gainDb': (_MIN_DB, _MAX_DB), 'pan': (-1.0, 1.0)}  # renderer-level targets (sends: dB like gainDb)
# Engine defaults of the automatable stack layer params (the base of a modulator on 'instrument.layers.<id>.<p>').
_LAYER_DEFAULTS = {'level': 0.0, 'pan': 0.0, 'mute': 0.0, 'fine': 0.0}


def _slug(s) -> str:
    return re.sub(r'[^a-z0-9_-]+', '_', str(s).strip().lower()).strip('_') or 'x'


def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        raise ComposeError(f"{what} = {x:g} is outside {lo:g}..{hi:g}")
    return float(x)


def _r6(x: float) -> float:
    v = round(float(x), 6)
    return 0.0 if v == 0 else v


def _caller() -> str:
    """'song.py:42: lead.play(...)' for the first stack frame outside the agentsound package."""
    f = sys._getframe(1)
    here = os.path.dirname(os.path.abspath(__file__))
    while f is not None and os.path.dirname(os.path.abspath(f.f_code.co_filename)) == here:
        f = f.f_back
    if f is None:
        return ''
    line = linecache.getline(f.f_code.co_filename, f.f_lineno).strip()
    return f"{os.path.basename(f.f_code.co_filename)}:{f.f_lineno}" + (f": {line}" if line else '')


# ----------------------------------------------------------------------------------- sections

class Section:
    """A named span of bars in its meter (.meter, e.g. (3, 4); .beats_per_bar quarter-note beats per bar).
    start/end/length are beats. Created by song.section()."""

    __slots__ = ('name', 'start', 'bars', 'beats_per_bar', 'meter', 'prog', 'parts')

    def __init__(self, name: str, start: float, bars: float, beats_per_bar: float, meter: tuple | None = None):
        self.name, self.start, self.bars, self.beats_per_bar = name, float(start), float(bars), float(beats_per_bar)
        self.meter = meter if meter is not None else ((int(beats_per_bar), 4) if float(beats_per_bar).is_integer()
                                                      else _tempo._partial_meter(beats_per_bar, f"section {name!r}"))
        self.prog: Progression | None = None      # the changes (song.form): the parts' progressions in a row
        self.parts: tuple = ()                    # song.form: the Parts (A1 A2 B A3 ...) with their progressions

    def part(self, name) -> 'Part':
        """The part `name` ('A2'; an int = its index) of a form section."""
        for i, p in enumerate(self.parts):
            if p.name == name or (isinstance(name, int) and not isinstance(name, bool) and i == name):
                return p
        raise ComposeError(f"section {self.name!r} has no part {name!r}; parts: "
                           f"{', '.join(p.name for p in self.parts) or 'none (song.form gives sections parts)'}")

    @property
    def length(self) -> float:
        return self.bars * self.beats_per_bar

    @property
    def end(self) -> float:
        return self.start + self.length

    @property
    def span(self) -> tuple[float, float]:
        return self.start, self.end

    def bar(self, n: float, beat: float = 0.0) -> float:
        """Absolute beat of bar n (0-based) of this section, plus `beat`. Negative n counts from the
        end: bar(-1) = start of the last bar. bar(bars) = the section end."""
        k = n + self.bars if n < 0 else n
        if not 0 <= k <= self.bars:
            raise ComposeError(f"section {self.name!r} has {self.bars:g} bars (0..{self.bars - 1:g}); bar({n}) is outside")
        return self.start + k * self.beats_per_bar + beat

    def beat(self, b: float) -> float:
        """Absolute beat of `b` beats into the section (negative = before the section end)."""
        x = self.end + b if b < 0 else self.start + b
        if not self.start - 1e-9 <= x <= self.end + 1e-9:
            raise ComposeError(f"beat({b}) is outside section {self.name!r} ({self.length:g} beats)")
        return x

    def bar_starts(self, every: int = 1) -> list[float]:
        """Beats of every `every`-th bar start: for b in verse.bar_starts(2): ..."""
        return [self.start + k * self.beats_per_bar for k in range(0, int(math.ceil(self.bars - 1e-9)), every)]

    def __contains__(self, beat) -> bool:
        return self.start - 1e-9 <= float(beat) < self.end - 1e-9

    def __repr__(self) -> str:
        m = '' if self.meter == (4, 4) else f", {self.meter[0]}/{self.meter[1]}"
        p = f", parts {' '.join(x.name for x in self.parts)}" if self.parts else ''
        return f"Section({self.name!r}, bars={self.bars:g}{m}, beats {self.start:g}..{self.end:g}{p})"


class Part:
    """One part of a form section (song.form): name ('A1'), index in the section, bar (0-based, in the section),
    start / end / length (beats), bars, prog (its Progression) and section. A position like a Section start:
    track.play(clip, part.start)."""

    __slots__ = ('name', 'index', 'bar', 'start', 'prog', 'section')

    def __init__(self, name: str, index: int, bar: float, start: float, prog: Progression, section: Section):
        self.name, self.index, self.bar, self.start, self.prog, self.section = name, index, bar, start, prog, section

    @property
    def length(self) -> float:
        return self.prog.length

    @property
    def end(self) -> float:
        return self.start + self.prog.length

    @property
    def bars(self) -> float:
        return self.prog.length / self.section.beats_per_bar

    def __repr__(self) -> str:
        return f"Part({self.name!r} of {self.section.name!r}, bar {self.bar:g}, {self.bars:g} bars)"


# -------------------------------------------------------------------------------------- nodes

class FXChain(list):
    """A node's insert chain (a list of FX) that also takes an effect's name or type as index:
    track.fx['compressor'].set(attack=25), s.master.fx['limiter'].set(gain=5.2), track.fx['ducker'].params['depth'].
    A type that occurs more than once is ambiguous (give the fx a name= or use its index)."""

    def __getitem__(self, k):
        if isinstance(k, str):
            hits = [f for f in self if f.name == k] or [f for f in self if f.type == k]
            listing = ', '.join(f"{i}:{f.type}" + (f"({f.name})" if f.name else '') for i, f in enumerate(self))
            if not hits:
                raise ComposeError(f"no effect named or of type {k!r} in the chain ({listing or 'empty'})")
            if len(hits) > 1:
                raise ComposeError(f"{len(hits)} {k!r} effects in the chain ({listing}): use the index, or name one")
            return hits[0]
        return super().__getitem__(k)

    def index_of(self, k) -> int:
        """The index of an effect found by name / type (as fx[k] finds it)."""
        f = self[k]
        return next(i for i, x in enumerate(self) if x is f)


class _Node:
    kind = 'node'

    @property
    def fx(self) -> FXChain:
        """The insert chain (an FXChain: index it by position, name or type)."""
        return self._fx

    @fx.setter
    def fx(self, chain) -> None:
        self._fx = chain if isinstance(chain, FXChain) else FXChain(chain)

    def __init__(self, song: 'Song', id: str, fx, gain_db, pan, output, sends, mute):
        self._song = song
        self.id = id
        self.fx: list[FX] = [FX.coerce(f) for f in (fx or ())]
        self.gain_db = _num(gain_db, f"{self.kind} {id!r} gain_db", _MIN_DB, _MAX_DB)
        # gain_db is the node's level (the fader as set - a band preset's balance for its role, a patch's level);
        # every 'gainDb' value the song writes on top (automation points, modulator base / min / max / steps values)
        # is dB relative to it: automate('gainDb', [(0, 0), (solo, 2)]) = "as set, +2 dB in the solo".
        self.pan = _num(pan, f"{self.kind} {id!r} pan", -1.0, 1.0)
        self.output = _ref(output)
        self.sends: dict[str, float] = {}
        self._patch_sends: dict[str, float] = {}
        self.mute = bool(mute)
        self._auto: list[tuple[str, list]] = []
        self._mods: list[tuple[str, Mod, tuple, str]] = []   # (target, modulator, (start, end), call site)
        for k, v in (sends or {}).items():
            self.send(k, v)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.id!r})"

    def send(self, bus, db: float = -12.0):
        """Post-fader send to a bus (reverb/delay return) at `db`."""
        self.sends[_ref(bus)] = _num(db, f"{self.kind} {self.id!r} send level", _MIN_DB, _MAX_DB)
        return self

    def to(self, output):
        """Route this node's output to a bus (or 'master')."""
        self.output = _ref(output)
        return self

    def add_fx(self, *effects, first: bool = False):
        """Append (or prepend) insert effects."""
        new = [FX.coerce(f) for f in effects]
        self.fx = new + self.fx if first else self.fx + new
        return self

    def automate(self, target: str, *points, at=None):
        """Automate a target with one or more point lists (see automation.py).
        Targets: 'instrument.<param>' (tracks), 'fx.<index|type|name>.<param>', 'gainDb', 'pan',
        'send.<bus>', 'mod.<name|index>.<field>' (a modulator field: depth, min, max, base, rate, ...).
        e.g. lead.automate('instrument.cutoff', exp_ramp(0, 32, 400, 6000)). at= (a Section, beat or (section,
        beats)) makes the points' beats relative to it: piano.automate('send.echo', [(3, -60), (3.2, -16)], at=coda)."""
        self._check_target(target)
        pts: list = []
        for p in points:
            if isinstance(p, tuple) and len(p) in (2, 3) and not isinstance(p[0], (tuple, list)):
                pts.append(p)  # a single bare point
            else:
                pts.extend(p)
        if not pts:
            raise ComposeError(f"automate({target!r}) on {self.kind} {self.id!r} got no points")
        if at is not None:
            a = self._song._at(at)
            pts = [(p[0] + a,) + tuple(p[1:]) if isinstance(p, (tuple, list)) and p and isinstance(p[0], (int, float))
                   and not isinstance(p[0], bool) else p for p in pts]
        _auto.normalize(pts, f"{self.kind} {self.id!r} automation {target!r}")  # validate early
        self._auto.append((target, pts))
        return self

    def modulate(self, target: str, *mods, window=None):
        """Drive `target` continuously with modulators (see modulation.py): lfo(), steps(), gate(),
        follow(), envelope(), sample_hold(). Targets as for automate() (fx by index, type or name).
        Several modulators on one target apply in order: absolute ones (min/max) set the value, offset ones
        (depth) add to it - to the target's automation lane if it has one, else to base= (filled in from
        the node / params when known). window=Section or (start, end) limits them; outside the window the
        automation lane / base / static value applies.
            lead.modulate('instrument.cutoff', lfo('sine', rate='1/4', min=600, max=4000, curve='exp'))
            pad.modulate('gainDb', gate('x.x.xx.x.x.xx.x.', depth=18), window=chorus)"""
        if isinstance(target, str) and target.startswith('mod.'):
            raise ComposeError(f"{self.kind} {self.id!r}: modulators can't target other modulators; automate their "
                               f"fields instead: automate('mod.<name|index>.<field>', points)")
        self._check_target(target)
        if not mods:
            raise ComposeError(f"modulate({target!r}) on {self.kind} {self.id!r} got no modulator, e.g. "
                               f"lfo('sine', rate='1/4', min=400, max=4000, curve='exp')")
        win = self._song._window(window)
        origin = _caller()
        for m in mods:
            if not isinstance(m, Mod):
                hint = (" - lfo(start, end, lo, hi) / steps({beat: value}) make automation points: pass them to "
                        "automate(); modulators are lfo('sine', rate='1/4', ...), steps([...], rate='1/16', ...)"
                        if isinstance(m, list) else '')
                raise ComposeError(f"{self.kind} {self.id!r}: modulate({target!r}) got {m!r}, which is not a modulator "
                                   f"(lfo(), steps(), gate(), follow(), envelope(), sample_hold()){hint}")
            m = m.copy()
            if m.name and any(x.name == m.name for _, x, _, _ in self._mods):
                raise ComposeError(f"{self.kind} {self.id!r} already has a modulator named {m.name!r}")
            self._song._bind_mod(self, m)
            self._mods.append((target, m, win, origin))
        return self

    def lane(self, target: str, spec, *, base: float = 0.0, glide: float = 0.0, curve: str = 'smooth',
             default=None, drops=(), drop: float = -60.0, hold: bool = False, end: bool = False):
        """A section lane on `target` (agentsound.sections): spec {section: value | (from, to[, curve]) |
        [(bar, value[, curve]), ...]} - each section starts at its value (a jump, or a glide of `glide` beats with
        `curve`), a tuple moves across the section, marks move inside it (no curve: a jump) - or a list of
        (position, value[, curve]) marks (the first is where the lane starts, the rest jump unless a curve is
        given). base is added to every value; default = the value of the sections the dict leaves out (None: they
        continue); drops = sections whose last beat falls to `drop`; hold=True writes each jump as the old value
        again at the jump + the new one (s.arc's way, the same sound); end=True holds the last value to the song end.
            pad.lane('instrument.cutoff', {'intro': (300, 900, 'exp'), 'chorus': 1600, 'outro': (2000, 300, 'exp')})
            piano.lane('send.hall', [(0, 3), (theme, 0, 'smooth'), (verse, -1)], base=-9)"""
        from .sections import lane_points
        return self.automate(target, lane_points(self._song, spec, base=base, glide=glide, curve=curve,
                                                 default=default, drops=drops, drop=drop, hold=hold, end=end,
                                                 what=f"{self.kind} {self.id!r} lane {target!r}"))

    def levels(self, spec, **opts):
        """The section lane of the node's level: lane('gainDb', spec, ...) - dB on its gain_db (the fader as set):
            kit.levels({'verse': [(0, -7), (8, -5)], 'build': (-3, 0), 'final': 0.5}, default=0, drops=['build'])"""
        return self.lane('gainDb', spec, **opts)

    def _check_target(self, target) -> None:
        if not isinstance(target, str) or not _TARGET_RE.match(target):
            hint = ''
            if isinstance(target, str):
                if target in ('gain', 'gain_db', 'volume', 'level'):
                    hint = " - did you mean 'gainDb'?"
                elif '.' not in target and self.kind == 'track':
                    hint = f" - did you mean 'instrument.{target}'?"
            raise ComposeError(f"bad target {target!r} on {self.kind} {self.id!r}{hint}. Targets: "
                               f"'instrument.<param>', 'fx.<index|type|name>.<param>', 'gainDb', 'pan', 'send.<bus>' "
                               f"(automate() also takes 'mod.<name|index>.<field>')")
        if target.startswith('instrument.') and self.kind != 'track':
            raise ComposeError(f"{self.kind} {self.id!r} has no instrument; target {target!r} is only valid on tracks")
        if target == 'pan' and self.kind == 'master':
            raise ComposeError("the master has no pan; automate 'gainDb' or 'fx.<i>.<param>'")
        if target.startswith('send.') and self.kind == 'master':
            raise ComposeError("the master has no sends")

    def duck(self, key=None, pitches=None, **params):
        """Sidechain pumping: append a 'ducker' keyed by `key` (track/bus). pitches= keys it only from
        those notes of the key track (e.g. 'kick' out of a full drum track) through a muted ghost
        track. key=None gives a tempo-synced ducker (mode='tempo', e.g. rate=1 for quarter notes).
        params go to the ducker, e.g. depth=10, release=180 (see `python -m agentsound params ducker`)."""
        self._song._duck(self, key, pitches, params)
        return self

    def carve(self, key, freq: float = 2500.0, q: float = 0.7, depth: float = 4.0, **params):
        """Dynamic EQ keyed by a lead: append a band-mode 'compressor' (sidechain = `key`) that dips this node's
        `freq` band (Q `q`) by up to `depth` dB while the key plays loud in that band, and gives it back in the
        key's gaps - the bed steps aside in the lead's presence band instead of ducking as a whole. params go to the
        compressor (threshold=-40, ratio=4, attack=10, release=250, knee=6 by default)."""
        self._song._carve(self, key, freq, q, depth, params)
        return self


class Track(_Node):
    """An instrument track. Place notes with play()/loop()/note(); shape feel with groove()/humanize()."""

    kind = 'track'

    def __init__(self, song, id, sound, fx=(), gain_db=0.0, pan=None, output='master', sends=None, mute=False):
        if isinstance(sound, str):
            sound = _patches.get(sound)
        patch_fx, patch_gain, patch_pan, patch_sends, self.patch = [], 0.0, 0.0, {}, None
        if isinstance(sound, Patch):
            if sound.instrument is None:
                raise ComposeError(f"track {id!r}: patch {sound.name!r} is an fx chain (for buses), not an instrument")
            self.instrument = sound.instrument
            patch_fx, patch_gain, patch_pan, patch_sends, self.patch = (list(sound.fx), sound.gain_db, sound.pan,
                                                                        dict(sound.sends), sound.name)
        else:
            try:
                self.instrument = Instrument.coerce(sound)
            except ComposeError as e:
                raise ComposeError(f"track {id!r}: {e}") from None
        gain = _num(gain_db, f"track {id!r} gain_db") + patch_gain
        if isinstance(fx, (FX, dict)):
            fx = [fx]
        super().__init__(song, id, patch_fx + [FX.coerce(f) for f in (fx or ())], gain,
                         patch_pan if pan is None else pan, output, sends, mute)
        self._patch_sends = patch_sends
        self._notes: list[Note] = []
        self._origin: list[str] = []   # call site that placed each note (for error messages)
        self._groove = None
        self._human: tuple | None = None

    # --- placing notes
    def play(self, what, at=0.0, *, times: int = 1, transpose: int = 0, vel: float = 1.0, replace: bool = False):
        """Place a Clip / Progression (block chords) / Motif / Chord at `at` (beat or Section),
        `times` times back to back. vel scales velocities; replace=True first removes this track's
        notes starting inside the placed span (for fills over a looping groove)."""
        c = self._prep(what, transpose, vel)
        if not isinstance(times, int) or isinstance(times, bool) or times < 1:
            raise ComposeError(f"track {self.id!r}: times must be an int >= 1, got {times!r}")
        one = c.length
        if times > 1:
            c = c.repeat(times)
        start = self._song._at(at)
        if replace:
            self.clear(start, start + max(c.length, 1e-9))
        self._place(c, start)
        self._gestures(what, [start + k * one for k in range(times)])
        return self

    def _gestures(self, what, offsets, until=None) -> None:
        """The pitch gestures a notation Line carries (^scoop, ^fall, ^vib ...), written at each offset (those
        starting at or after `until` - a loop's end - are left out)."""
        gest = getattr(what, 'gestures', None)
        if gest:
            from .notation import realize
            for a in offsets:
                gs = [g for g in gest if until is None or a + g['start'] < until - 1e-9]
                if gs:
                    realize(self, gs, a)

    def _place(self, c: Clip, start: float) -> None:
        origin = _caller()
        self._notes.extend(n._replace(start=n.start + start) for n in c)
        self._origin.extend([origin] * len(c))

    def loop(self, what, *where, bars: float | None = None, until=None, transpose: int = 0, vel: float = 1.0):
        """Repeat a clip to fill each of `where` (Sections), or from a position for `bars` bars /
        `until` a beat or section. Notes crossing the end are cut.
            drums.loop(beat, verse, chorus)      bass.loop(line, verse.bar(8), bars=8)"""
        if not where:
            raise ComposeError(f"track {self.id!r}: loop(clip, where) needs at least one section or position")
        c = self._prep(what, transpose, vel)
        if c.length <= 0:
            raise ComposeError(f"track {self.id!r}: can't loop a clip of length 0 (give the Clip a length)")
        for w in where:
            start = self._song._at(w)
            if bars is not None:
                end = self._song.bars_after(start, _num(bars, 'bars', 0))
            elif until is not None:
                end = self._song._at(until)
            elif isinstance(w, Section):
                end = w.end
            elif isinstance(w, str):
                end = self._song[w].end
            else:
                raise ComposeError(f"track {self.id!r}: loop from beat {start:g} needs bars= or until=")
            if end <= start:
                raise ComposeError(f"track {self.id!r}: loop end {end:g} is not after its start {start:g}")
            self._place(c.loop(end - start), start)
            self._gestures(what, [start + k * c.length
                                  for k in range(int(math.ceil((end - start) / c.length - 1e-9)))], until=end)
        return self

    def note(self, pitch, at, dur: float = 1.0, vel: int = 100, art=None):
        """Add one note (pitch as MIDI, 'A4' or drum name) at a beat or Section; art= an articulation mark
        (articulation.py: 'staccato', ... -> a keyswitch at compile)."""
        c = Clip([(0.0, dur, pitch, vel)], length=dur)
        return self.play(c if art is None else _art.articulate(c, art), at)

    def clear(self, start=0.0, end=None, pitches=None, *, cut: bool = False):
        """Remove notes starting in [start, end) (a Section as start means its whole span). cut=True also ends the
        notes still SOUNDING at `start` right there (a held pad or a long bass note would ring on into the silence
        otherwise): a real stop."""
        if isinstance(start, Section) and end is None:
            start, end = start.start, start.end
        a = self._song._at(start)
        b = math.inf if end is None else self._song._at(end)
        ps = None if pitches is None else {drum(p) for p in (pitches if isinstance(pitches, (list, tuple, set)) else [pitches])}
        keep = [not (a - 1e-9 <= n.start < b - 1e-9 and (ps is None or n.pitch in ps)) for n in self._notes]
        self._notes = [n for n, k in zip(self._notes, keep) if k]
        self._origin = [o for o, k in zip(self._origin, keep) if k]
        if cut:
            self.cut(a, pitches)
        return self

    def cut(self, at, pitches=None):
        """End every note sounding through `at` (a beat, Section or (section, beats)) right there - the notes that
        started before and would ring on (pitches= limits it): bass.cut(drop.start)."""
        a = self._song._at(at)
        ps = None if pitches is None else {drum(p) for p in (pitches if isinstance(pitches, (list, tuple, set)) else [pitches])}
        self._notes = [n._replace(dur=a - n.start) if (n.start < a - 1e-9 and n.start + n.dur > a + 1e-9
                                                        and (ps is None or n.pitch in ps)) else n
                       for n in self._notes]
        return self

    def feature(self, *sections, db: float = 2.0, glide: float = 1.0, target: str = 'gainDb'):
        """A spotlight lane: the track steps up `db` dB for each section (its solo) and back after it, gliding in
        over the `glide` beats before the section start / end ('gainDb' is dB on the track's gain_db):
        bass.feature(bass_solo, db=2)."""
        d = _num(db, 'feature db', -24, 24)
        g = _num(glide, 'feature glide (beats)', 0.0)
        spans = sorted(self._song._span(x, 'feature') for x in sections)
        if not spans:
            raise ComposeError("feature() needs at least one section")
        pts: list = [(0, 0.0)] if spans[0][0] - g > 0 else []
        for s0, e0 in spans:
            pts += [(s0 - g, 0.0), (s0, d, 'smooth'), (e0 - g, d), (e0, 0.0, 'smooth')]
        return self.automate(target, pts)

    # --- section plans (agentsound.sections): parts from each section's progression, per-section overrides
    def chords(self, *sections, **opts):
        """Block chords from each section's progression (sec.prog, or prog=): prog.block(**opts) placed as the
        section's part (a shorter part repeats, a longer one is cut at the section end). Any option may be a
        per-section dict {section | name: value, '*': default}. Placement options: bars=(a, b) (only those bars of
        the part, at bar a), transpose=, scale= (velocity factor), crescendo=(from, to), then= (functions clip ->
        clip), prog= (another progression).
            pad.chords(intro, verse, chorus, voicing='spread', register=('C3', 'C5'), vel={'*': 80, chorus: 84})"""
        from .sections import _harmony_parts
        _harmony_parts(self, 'chords', sections, (), opts)
        return self

    def arp(self, mode='up', *sections, **opts):
        """An arpeggio from each section's progression: prog.arp(mode, **opts) (patterns.arp: rate, octaves,
        register, vel, gate, pattern, accent ...), placed like chords() (bars=, transpose=, scale=, crescendo=,
        then=, prog=; any option per section): arp.arp('updown', verse, chorus, rate='1/16', octaves=2)."""
        from .sections import _harmony_parts
        _harmony_parts(self, 'arp', sections, (mode,), opts)
        return self

    def bassline(self, style='octave', *sections, **opts):
        """A bass line from each section's progression: prog.bass(style, **opts) (patterns.bassline: rate, low,
        vel, gate, pattern ...), placed like chords(): bass.bassline('octave', verse, chorus, rate='1/8', gate=0.85,
        prog={verse: s.prog('F#m')}, bars={verse: (0, 8)})."""
        from .sections import _harmony_parts
        _harmony_parts(self, 'bassline', sections, (style,), opts)
        return self

    def plan(self, plan: dict, *, fills=None, crashes=None, crash=None, keep=None, phrase: float = 8,
             fill_every: float = 0, same_every: float = 0):
        """Loops per section, then fills and crashes (a drum part, or any looped part):
          plan     {section: clip | [clip, (bar, clip), (bar, clip, bars)]} - each clip loops from its bar to the
                   next entry (or for `bars`, or to the section end); clip None = rest
          fills    {section: clip | (every_bars, clip) | (every_bars, clip, last)} - a fill ending on every phrase
                   end (default every 8 bars; `last` into the section end) - or {position: clip}; a fill replaces
                   what it covers, or only the pieces of (clip, pieces); keep= pieces stay under every fill
                   (keep=('kick',)). Song-wide rules for the planned sections without their own: fills['section']
                   (into each section's end) and fills['phrase'] (every `phrase` bars), spaced by the players'
                   Budget: fill_every bars between two fills, same_every bars between two of one rule
          crashes  {position: vel} or [positions] (crash= the velocity or a clip, default crash())
            kit.plan({verse: [groove, (8, groove_b)], chorus: chorus_groove}, fills={verse: tom_fill(1),
                     chorus: (8, tom_fill(2))}, crashes={verse: 112, chorus: 118, chorus.bar(8): 108})
            kit.plan({...}, fills={'section': tom_fill(2), 'phrase': snare_roll(1)}, phrase=4, fill_every=8)"""
        from .sections import _drum_plan
        _drum_plan(self, plan, fills=fills, crashes=crashes, crash=crash, keep=keep, phrase=phrase,
                  fill_every=fill_every, same_every=same_every)
        return self

    def rise(self, end, length=16, **opts):
        """A riser into `end` (a Section start / position): one note `length` beats before it (dur= its length,
        pitch=, vel=) with cutoff=(lo, hi) / hpf=(lo, hi) opening into `end` (None leaves a lane out). See
        sections.rise: riser.rise(chorus, 16, pitch='A3'); rev.rise(chorus, 2, cutoff=(2500, 16000), hpf=None)."""
        from .sections import rise
        return rise(self, end, length, **opts)

    def _prep(self, what, transpose, vel) -> Clip:
        try:
            c = as_clip(what)
        except ComposeError as e:
            raise ComposeError(f"track {self.id!r}: {e}") from None
        if transpose:
            c = c.transpose(transpose)
        if vel != 1.0:
            c = c.velocity(vel)
        return c

    # --- feel
    def humanize(self, timing_ms: float = 4.0, vel: float = 6, seed=None):
        """Seeded timing (+-ms) and velocity jitter, applied at compile with the local song tempo."""
        self._human = (_num(timing_ms, 'timing_ms', 0, 50), _num(vel, 'vel', 0, 64), seed)
        return self

    def groove(self, g):
        """Groove template applied at compile: 'straight' 'tight' 'laidback'/'synthwave' 'push' 'mpc'
        'shuffle' 'swing8' or a Groove(...). Drum tracks get per-drum offsets (snare late...)."""
        self._groove = _groove(g)
        return self

    # --- inspection
    @property
    def notes(self) -> tuple[Note, ...]:
        return tuple(sorted(self._notes, key=lambda n: (n.start, n.pitch)))

    def clip(self, start=0.0, end=None) -> Clip:
        """The track's notes in [start, end) as a Clip starting at 0 (e.g. to copy a part)."""
        a = self._song._at(start)
        b = self._song.length if end is None else self._song._at(end)
        return Clip._raw([n for n in self._notes if a <= n.start < b], b - a).shift(-a)


class Bus(_Node):
    """A group / effect-return bus. fx can be a list, an fx-chain Patch or a patch name."""

    kind = 'bus'

    def __init__(self, song, id, fx=(), gain_db=0.0, pan=None, output='master', sends=None, mute=False):
        patch_gain, patch_pan, patch_sends = 0.0, 0.0, {}
        if isinstance(fx, str):
            fx = _patches.get(fx)
        if isinstance(fx, Patch):
            if fx.instrument is not None:
                raise ComposeError(f"bus {id!r}: patch {fx.name!r} has an instrument; buses take fx chains")
            patch_gain, patch_pan, patch_sends, fx = fx.gain_db, fx.pan, dict(fx.sends), fx.fx
        elif isinstance(fx, (FX, dict)):
            fx = [fx]
        super().__init__(song, id, fx, _num(gain_db, f"bus {id!r} gain_db") + patch_gain,
                         patch_pan if pan is None else pan, output, sends, mute)
        self._patch_sends = patch_sends


class Master(_Node):
    """The master chain: fx, gain_db, automation ('gainDb', 'fx.<i>.<param>')."""

    kind = 'master'

    def __init__(self, song):
        super().__init__(song, 'master', (), 0.0, 0.0, 'master', None, False)

    def add(self, *effects):
        return self.add_fx(*effects)

    def use(self, chain):
        """Replace the chain with an fx-chain Patch (or its name), e.g. 'master/synthwave'."""
        p = _patches.get(chain) if isinstance(chain, str) else chain
        if not isinstance(p, Patch) or p.instrument is not None:
            raise ComposeError(f"master.use() needs an fx-chain patch, got {chain!r}")
        self.fx = [f.copy() for f in p.fx]
        self.gain_db = p.gain_db
        return self


# --------------------------------------------------------------------------------------- song

def _time_sig(ts) -> tuple[int, int]:
    if isinstance(ts, str):
        m = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', ts)
        if not m:
            raise ComposeError(f"time_sig must look like '4/4' or '6/8', got {ts!r}")
        ts = (int(m.group(1)), int(m.group(2)))
    try:
        n, d = ts
    except (TypeError, ValueError):
        raise ComposeError(f"time_sig must be '4/4' or (4, 4), got {ts!r}") from None
    if not (isinstance(n, int) and isinstance(d, int)) or n < 1 or d not in (1, 2, 4, 8, 16):
        raise ComposeError(f"bad time signature {ts!r}")
    return n, d


class Song:
    """The whole arrangement. Build it, then compile() / save() (or `python -m agentsound build`)."""

    def __init__(self, title: str = 'Untitled', tempo: float = 120.0, key='C major', seed: int = 1,
                 time_sig='4/4', sample_rate: int = 48000, tail: float = 4.0, meter=None):
        self.title = str(title)
        self.tempo = _num(tempo, 'tempo (BPM)', 30, 300)   # the tempo the song starts with (see set_tempo & co.)
        self.key = Key(key)
        if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 0xFFFFFFFF:
            raise ComposeError(f"seed must be an int 0..4294967295, got {seed!r}")
        self.seed = seed
        self.time_sig = _tempo.parse_meter(meter, 'meter') if meter is not None else _time_sig(time_sig)
        self.beats_per_bar = self.time_sig[0] * 4.0 / self.time_sig[1]   # of the default meter
        if sample_rate not in (44100, 48000, 96000):
            raise ComposeError(f"sample_rate must be 44100, 48000 or 96000, got {sample_rate!r}")
        self.sample_rate = sample_rate
        self.tail = _num(tail, 'tail (seconds)', 0, 30)
        self.sections: list[Section] = []
        self.tracks: dict[str, Track] = {}
        self.buses: dict[str, Bus] = {}
        self.master = Master(self)
        self.stems = False
        self.bit_depth = 24
        self.warnings: list[str] = []
        self.advice: list[str] = []            # warnings of the players (drummer: missing kit pieces), kept by compile()
        self._length: float | None = None
        self._ghosts: dict[str, tuple[str, tuple[int, ...]]] = {}
        self._tempo_plan = _tempo.TempoPlan()
        self.applied_mix: dict | None = None   # the MIX dict agentsound.mixer.apply() wrote into the song
        self._compile_hooks: list = []         # add_compile_hook(): run at the start of every compile()

    def __repr__(self) -> str:
        bpm = f"{self.tempo:g} BPM" if self._tempo_plan.empty() else f"{self.tempo:g} BPM (tempo map)"
        return f"Song({self.title!r}, {bpm}, {self.key.name}, {len(self.sections)} sections, {len(self.tracks)} tracks)"

    @property
    def meter(self) -> tuple[int, int]:
        """The default meter (sections without meter= use it)."""
        return self.time_sig

    # --- time
    def section(self, name: str, bars: float, meter=None, *, prog=None) -> Section:
        """Append a section of `bars` bars after the previous one; returns it (with .start/.end in beats).
        meter=(3, 4) / '6/8' gives it its own meter (default: the song's); beats stay quarter notes, so a 3/4
        bar is 3 beats and a 6/8 bar 3 beats (two dotted quarters). prog= its harmony (a progression spec in the
        song key, or a Progression; it may be shorter than the section: the section plans repeat it) -> sec.prog,
        which track.chords() / arp() / bassline() play."""
        if not isinstance(name, str) or not name.strip():
            raise ComposeError(f"section name must be a non-empty string, got {name!r}")
        if any(s.name == name for s in self.sections):
            raise ComposeError(f"section {name!r} already exists; names must be unique (e.g. 'verse1', 'verse2')")
        b = _num(bars, f"section {name!r} bars")
        if b <= 0:
            raise ComposeError(f"section {name!r} needs bars > 0")
        m = self.time_sig if meter is None else _tempo.parse_meter(meter, f"section {name!r} meter")
        start = self.sections[-1].end if self.sections else 0.0
        s = Section(name, start, b, _tempo.beats_per_bar(m), m)
        if prog is not None:
            try:
                s.prog = prog if isinstance(prog, Progression) else self.prog(prog, meter=meter)
            except ComposeError as e:
                raise ComposeError(f"section {name!r} prog: {e}") from None
        self.sections.append(s)
        return s

    def form(self, spec: str, parts: dict | None = None, *, meter=None) -> tuple:
        """The form in one line, the changes attached: sections in a row, each `name:what` - what is a number of
        bars ('intro:4'; its prog is parts['intro'] if given) or its parts: letters ('head:AABA' - the k-th A is
        parts['A<k>'] when given, else parts['A']) or names joined by ',' ('out:B,A3o'). parts = {name: a
        progression spec (song.prog in `meter`) or a Progression}. Every section gets .prog (its parts' changes in
        a row) and .parts (Part: name, index, bar, start, end, prog), so the players need no progression argument
        (jazz.chorus(band, head, ...), part.prog). Returns the sections in order:
            intro, head, solo, out, end = s.form('intro:4 head:AABA solo:AABA out:B,A3 end:2', parts=CHANGES)"""
        if not isinstance(spec, str) or not spec.split():
            raise ComposeError(f"form() takes a string like 'intro:4 head:AABA end:2', got {spec!r}")
        progs = {}
        for k, v in (parts or {}).items():
            try:
                progs[k] = v if isinstance(v, Progression) else self.prog(v, meter=meter)
            except ComposeError as e:
                raise ComposeError(f"form(): part {k!r}: {e}") from None
        made = []
        for tok in spec.split():
            name, sep, what = tok.partition(':')
            if not sep or not name or not what:
                raise ComposeError(f"form(): {tok!r} must be name:bars or name:PARTS ('head:AABA', 'out:B,A3')")
            bpb = self.beats_per_bar if meter is None else _tempo.beats_per_bar(_tempo.parse_meter(meter, 'form meter'))
            if re.fullmatch(r'\d+(?:\.\d+)?', what):
                bars = float(what)
                plist = [(name, progs[name])] if name in progs else []
                if plist and plist[0][1].length > bars * bpb + 1e-9:
                    raise ComposeError(f"form(): parts[{name!r}] holds {plist[0][1].length / bpb:g} bars, the "
                                       f"section {bars:g}")
            else:
                if ',' in what or '+' in what:
                    labels = [x for x in re.split(r'[,+]', what) if x]
                elif re.fullmatch(r'[A-Z]+', what):
                    seen: dict = {}
                    labels = []
                    for ch in what:
                        seen[ch] = seen.get(ch, 0) + 1
                        labels.append(f"{ch}{seen[ch]}" if f"{ch}{seen[ch]}" in progs else ch)
                else:
                    labels = [what]
                missing = [x for x in labels if x not in progs]
                if missing:
                    raise ComposeError(f"form(): section {name!r} needs part {missing[0]!r}; parts: "
                                       f"{', '.join(progs) or 'none (give parts={...})'}")
                plist = [(x, progs[x]) for x in labels]
                bars = sum(p.length for _, p in plist) / bpb
            sec = self.section(name, bars, meter=meter)
            at, out = 0.0, []
            for i, (lab, p) in enumerate(plist):
                out.append(Part(lab, i, at / bpb, sec.start + at, p, sec))
                at += p.length
            sec.parts = tuple(out)
            if plist:
                total = plist[0][1]
                for _, p in plist[1:]:
                    total = total + p
                sec.prog = total
            made.append(sec)
        return tuple(made)

    def __getitem__(self, name: str) -> Section:
        for s in self.sections:
            if s.name == name:
                return s
        raise ComposeError(f"no section {name!r}; sections: {', '.join(s.name for s in self.sections) or 'none'}")

    def bar(self, n: float, beat: float = 0.0) -> float:
        """Absolute beat of song bar n (0-based), counting every section's bars in its meter."""
        return self.meter_grid().bar_start(n) + beat

    def bars_after(self, start, bars: float) -> float:
        """The beat `bars` bars after `start` (beat or Section), each bar in the meter where it falls."""
        return self.meter_grid().advance(self._at(start), _num(bars, 'bars', 0))

    def meter_at(self, beat) -> tuple[int, int]:
        """The meter at a beat (or Section)."""
        return self.meter_grid().meter_at(self._at(beat))

    def meter_grid(self) -> _tempo.MeterGrid:
        """The song's bars (the render JSON's "meter"): bar_at(beat), bar_start(bar), advance(beat, bars)."""
        return _tempo.MeterGrid(self._meter_points())

    def _meter_points(self) -> list[list]:
        return _tempo.meter_points(self.sections, self.time_sig)

    def seconds(self, beat) -> float:
        """Song time of a beat (or Section), through the tempo map."""
        b = self._at(beat)
        if self._tempo_plan.empty():
            return b * 60.0 / self.tempo
        return self.tempo_map().seconds_at(b)

    def beat_at(self, seconds: float, before=None) -> float:
        """The beat at a song time (the inverse of seconds()); before= a position: the beat `seconds` before it -
        a reversed cymbal of 4.3 s peaking on the chorus: cym.note(88, s.beat_at(4.3, before=chorus))."""
        t = _num(seconds, 'beat_at seconds')
        if before is not None:
            t = self.seconds(before) - t
        if self._tempo_plan.empty():
            return t * self.tempo / 60.0
        return self.tempo_map().beat_at(t)

    # --- tempo (agentsound/tempo.py; the render JSON gets a "tempoMap" once any of these is used)
    def tempo_at(self, beat) -> float:
        """The tempo (BPM) at a beat or Section, after every tempo change, ramp, rubato and fermata."""
        b = self._at(beat)
        if self._tempo_plan.empty():
            return self.tempo
        return self.tempo_map().bpm_at(b)

    def tempo_map(self) -> _tempo.TempoMap:
        """The tempo map as the engine will render it (beat <-> seconds, bpm_at)."""
        return _tempo.TempoMap(self.tempo_points())

    def tempo_points(self) -> list[list]:
        """The render JSON "tempoMap" points ([[0, tempo]] while the tempo never changes)."""
        return self._tempo_plan.points(self.tempo, self._onsets() if self._tempo_plan.needs_onsets() else None)

    def set_tempo(self, at, bpm: float) -> 'Song':
        """From `at` (beat or Section) on the tempo is `bpm` (until the next tempo change): a new tempo for a
        section, e.g. song.set_tempo(bridge, 84)."""
        self._tempo_plan.add_set(self._pos(at, 'set_tempo'), _num(bpm, 'set_tempo bpm', _tempo.MIN_BPM, _tempo.MAX_BPM))
        return self

    def tempo_ramp(self, start, end, to_bpm: float, curve: str = 'linear') -> 'Song':
        """Move the tempo from what it is at `start` to `to_bpm` at `end` (beats or Sections), and keep it:
        curve 'linear' (bpm linear in beats) or 'smooth' (eases in and out)."""
        self._ramp(start, end, 'tempo_ramp', curve, bpm=_num(to_bpm, 'tempo_ramp to_bpm', _tempo.MIN_BPM, _tempo.MAX_BPM),
                   a_tempo=False)
        return self

    def ritardando(self, span, to: float | None = 0.8, bpm: float | None = None, curve: str = 'smooth',
                   a_tempo: bool = True) -> 'Song':
        """Slow down across `span` (a Section, or (start, end) beats / Sections) to `to` x the tempo there (0.8 =
        20 % slower) or to `bpm`; curve 'smooth' (natural) or 'linear'. a_tempo=True: the tempo from before
        returns at the span end (rit. ... a tempo) - after the held chord when a fermata sits on the span end,
        never when no note starts after the chord there (the song's final chord stays slow) - and a tempo change
        starting right at the span end (another ritardando) continues from the slower tempo; False keeps the
        slower tempo. Into a final chord: song.ritardando((ending.bar(-2), ending.bar(-1)));
        song.fermata(ending.bar(-1), hold=2)."""
        return self._rit(span, to, bpm, curve, a_tempo, 'ritardando', slower=True)

    def accelerando(self, span, to: float | None = 1.15, bpm: float | None = None, curve: str = 'smooth',
                    a_tempo: bool = False) -> 'Song':
        """Speed up across `span` to `to` x the tempo there (1.15 = 15 % faster) or to `bpm`. a_tempo=False
        (default) keeps the new tempo after the span; True returns to the one from before (as for ritardando)."""
        return self._rit(span, to, bpm, curve, a_tempo, 'accelerando', slower=False)

    def fermata(self, at, hold: float | None = None, seconds: float | None = None, length: float | None = None) -> 'Song':
        """Hold the music at `at` (beat or Section) longer: the chord / note starting there rings `hold` extra
        beats (default 1.5, at the tempo there) or `seconds` longer, then the song goes on. The stretched span
        runs from `at` to the next note onset of any track after the chord (notes starting within 1/4 beat of
        `at` - strums, rolls - belong to it), else to the end of the chord's longest note; length= sets it in
        beats. The tempo drops inside the span, so everything there (and its echoes) waits too."""
        b = self._pos(at, 'fermata')
        if hold is not None and seconds is not None:
            raise ComposeError("fermata: give hold= (extra beats) or seconds=, not both")
        h = 1.5 if hold is None and seconds is None else (None if hold is None else _num(hold, 'fermata hold (beats)', 0, 64))
        sec = None if seconds is None else _num(seconds, 'fermata seconds', 0, 60)
        ln = None if length is None else _num(length, 'fermata length (beats)', 1e-3, 1024)
        if any(abs(f[0] - b) < 1e-9 for f in self._tempo_plan.fermatas):
            raise ComposeError(f"there is already a fermata at beat {b:g}")
        self._tempo_plan.fermatas.append((b, h, sec, ln))
        return self

    def rubato(self, span, depth: float = 0.04, phrase: str = 'arch', seed=None) -> 'Song':
        """Let the tempo breathe across `span` (a Section or (start, end)): +-depth (0.04 = 4 %) around the tempo,
        shaped like a phrase - 'arch' moves forward into the phrase and broadens towards its end, 'wave' breathes
        twice, 'lean' holds back first then moves on, 'breath' moves on gently through the first 60 % and broadens
        into the last 40 % (the singer's phrase: measured on a concert recording of a slow piano piece), 'free' only
        wanders - plus a seeded, smooth irregularity
        (seed=None: from the song seed). The span keeps its length (time taken is given back) and meets the
        tempo around it seamlessly. Ballads, classical phrases, rubato piano: depth 0.02-0.06."""
        s, e = self._span(span, 'rubato')
        d = _num(depth, 'rubato depth', 0.0, 0.25)
        if phrase not in _tempo.PHRASES:
            raise ComposeError(f"rubato phrase must be one of {', '.join(_tempo.PHRASES)}, got {phrase!r}")
        for a, b, *_ in self._tempo_plan.rubatos:
            if s < b - 1e-9 and e > a + 1e-9:
                raise ComposeError(f"rubato {s:g}..{e:g} overlaps the rubato {a:g}..{b:g}")
        sd = seed_int(f"{self.seed}:rubato:{s:g}") if seed is None else seed_int(seed)
        self._tempo_plan.rubatos.append((s, e, d, phrase, sd))
        return self

    def lilt(self, span, beats=None, jitter: float = 0.0, seed=None) -> 'Song':
        """Beat-level agogics in every whole bar of `span` (a Section or (start, end)): the pulse inside the bar is
        not metronomic, while the downbeats keep their places on the tempo map (each bar gives its time back).
        beats = {beat number (1-based quarter beats of the bar): delay in beats} - {2: 0.06}: beat 2 arrives 6 % of
        a beat late (the lingering chord of a slow 3/4 - measured +0.066 beats on a concert recording of Satie's
        Gymnopedie No. 1), {2: -0.06}: early (the Viennese waltz's anticipated 2nd beat); jitter = a seeded random
        extra delay per beat (standard deviation in beats: 0.02-0.05 is a pianist's breathing pulse; the recording
        read +-0.08 on beat 2 and +-0.14 on beat 3). The whole tempo moves (all tracks, both hands together), unlike
        humanize(), which moves single notes apart. Stacks with rubato / ramps / fermatas (they multiply);
        lilt spans may not overlap each other. Delays are clamped to +-0.3 beats."""
        s, e = self._span(span, 'lilt')
        spec = {} if beats is None else beats
        if not isinstance(spec, dict):
            raise ComposeError(f"lilt beats must be a dict {{beat number: delay in beats}} like {{2: 0.06}}, got {beats!r}")
        for k, v in spec.items():
            if isinstance(k, bool) or not isinstance(k, int) or k < 2:
                raise ComposeError(f"lilt beats: {k!r} is not an inner beat number (2, 3, ... - beat 1, the downbeat, "
                                   f"stays on the grid)")
            _num(v, f"lilt delay of beat {k}", -_tempo.LILT_MAX, _tempo.LILT_MAX)
        jit = _num(jitter, 'lilt jitter (beats)', 0.0, 0.15)
        for a, b, _ in self._tempo_plan.lilts:
            if s < b - 1e-9 and e > a + 1e-9:
                raise ComposeError(f"lilt {s:g}..{e:g} overlaps the lilt {a:g}..{b:g}")
        grid = self.meter_grid()
        rng = random.Random(seed_int(f"{self.seed}:lilt:{s:g}") if seed is None else seed_int(seed))
        bars, bar = [], math.ceil(grid.bar_at(s) - 1e-9)
        while True:
            b0 = grid.bar_start(bar)
            b1 = grid.bar_start(bar + 1)
            if b1 > e + 1e-9:
                break
            L = b1 - b0
            inner = int(math.ceil(L - 1e-9)) - 1
            if [k for k in spec if k > inner + 1] and not bars:
                raise ComposeError(f"lilt beats {sorted(spec)}: the bar at beat {b0:g} has only {inner + 1} beats")
            delays = []
            for k in range(2, inner + 2):
                d = spec.get(k, 0.0) + (max(-3.0, min(3.0, rng.gauss(0.0, 1.0))) * jit if jit else 0.0)
                delays.append(max(-_tempo.LILT_MAX, min(_tempo.LILT_MAX, d)))
            bars.append((b0, L, delays))
            bar += 1
        if not bars:
            raise ComposeError(f"lilt {s:g}..{e:g} holds no whole bar")
        self._tempo_plan.lilts.append((bars[0][0], bars[-1][0] + bars[-1][1], bars))
        return self

    def _rit(self, span, to, bpm, curve, a_tempo, what, slower: bool) -> 'Song':
        if bpm is not None:
            target = dict(bpm=_num(bpm, f"{what} bpm", _tempo.MIN_BPM, _tempo.MAX_BPM))
        else:
            f = _num(to, f"{what} to (factor)", 0.05, 4.0)
            if (slower and f >= 1.0) or (not slower and f <= 1.0):
                raise ComposeError(f"{what}(to={f:g}): the factor must be {'< 1 (e.g. 0.8 = 20 % slower)' if slower else '> 1 (e.g. 1.15 = 15 % faster)'}")
            target = dict(factor=f)
        s, e = self._span(span, what)
        self._ramp(s, e, what, curve, a_tempo=bool(a_tempo), **target)
        return self

    def _ramp(self, start, end, what, curve, bpm=None, factor=None, a_tempo=False) -> None:
        if curve not in ('linear', 'smooth'):
            raise ComposeError(f"{what}: curve must be 'linear' or 'smooth', got {curve!r}")
        s, e = self._pos(start, what), self._pos(end, what)
        label = f"{what}({s:g}..{e:g})"
        self._tempo_plan.add_ramp(s, e, bpm, factor, curve, a_tempo, label)

    def _pos(self, x, what: str) -> float:
        b = self._at(x)
        if b < 0:
            raise ComposeError(f"{what}: beat {b:g} is before the song start")
        return b

    def _span(self, span, what: str) -> tuple[float, float]:
        if isinstance(span, Section):
            return span.start, span.end
        if isinstance(span, str):
            sec = self[span]
            return sec.start, sec.end
        if isinstance(span, (tuple, list)) and len(span) == 2:
            a, b = self._pos(span[0], what), self._pos(span[1], what)
            if b <= a:
                raise ComposeError(f"{what}: the span ({a:g}, {b:g}) is empty; the end must be after the start")
            return a, b
        raise ComposeError(f"{what}: span must be a Section or (start, end) in beats / Sections, got {span!r}")

    def _onsets(self) -> list[tuple[float, float]]:
        """(beat, longest duration) of every distinct note onset of the song, as placed (fermata spans)."""
        at: dict[float, float] = {}
        for t in self.tracks.values():
            for n in t._notes:
                k = round(n.start, 6)
                at[k] = max(at.get(k, 0.0), n.dur)
        return sorted(at.items())

    @property
    def length(self) -> float:
        """Song length in beats: the explicit value, else the end of the last section, else the
        end of the last note rounded up to a bar."""
        if self._length is not None:
            return self._length
        if self.sections:
            return self.sections[-1].end
        end = max((n.start + n.dur for t in self.tracks.values() for n in t._notes), default=0.0)
        return math.ceil(end / self.beats_per_bar - 1e-9) * self.beats_per_bar

    @length.setter
    def length(self, beats: float) -> None:
        self._length = _num(beats, 'song length (beats)', 0)

    def at(self, pos, beats: float = 0.0) -> float:
        """The absolute beat of a position - a beat, a Section or section name (= its start), or (position, beats) -
        plus `beats`: s.at(chorus, 2.5) == chorus.start + 2.5. Every position argument of the song API takes the same
        forms: track.note('C4', (verse, 3.5)), track.play(fill, (chorus, -1)), automate(..., at=coda)."""
        return self._at(pos) + _num(beats, 'at beats')

    def _at(self, x) -> float:
        if isinstance(x, (Section, Part)):
            return x.start
        if isinstance(x, str):
            return self[x].start
        if isinstance(x, tuple) and len(x) == 2 and not isinstance(x[0], bool) \
                and isinstance(x[0], (Section, str, int, float, tuple)):
            return self._at(x[0]) + _num(x[1], f"position {x!r}: beats after")
        return _num(x, 'position (beats)')

    def breath(self, before, beats: float = 1.0, *, keep=(), tracks=None, cut: bool = True) -> 'Song':
        """A drop: everything stops for `beats` beats before each position of `before` (Sections / beats) - notes
        starting there are removed and notes still sounding are ended (track.clear(cut=True)) - except the tracks in
        keep= (risers, impacts, a voice); tracks= names the ones to stop instead. cut=False only removes the notes
        starting in the gap (a drum part's last hits ring out).
            s.breath(before=[chorus1, chorus2, final], beats=1, keep=[riser, impact])"""
        pos = list(before) if isinstance(before, list) else [before]
        b = _num(beats, 'breath beats', 0)
        if b <= 0:
            raise ComposeError("breath() needs beats > 0")
        if tracks is not None and keep:
            raise ComposeError("breath(): give keep= or tracks=, not both")
        ids = [_ref(t) for t in (tracks if tracks is not None else keep)]
        unknown = [i for i in ids if i not in self.tracks]
        if unknown:
            raise ComposeError(f"breath(): no track {unknown[0]!r} (tracks: {', '.join(self.tracks)})")
        sel = [self.tracks[i] for i in ids] if tracks is not None else \
            [t for t in self.tracks.values() if t.id not in set(ids)]
        for p in pos:
            x = self._at(p)
            for t in sel:
                t.clear(x - b, x, cut=cut)
        return self

    def transitions(self, *, riser=None, reverse=None, impact=None, down=None, pitch='C4'):
        """The fx-hit set (agentsound.sections.Transitions): tracks (a Track, a patch name, True = the library's
        synthwave hit, None) and .into(section, riser=16, reverse=2, impact=('D2', 120), down=('A3', 8, 100),
        breath=1, keep=[...]) - the moves into a section in one call."""
        from .sections import Transitions
        return Transitions(self, riser=riser, reverse=reverse, impact=impact, down=down, pitch=pitch)

    def ending(self, at, *, chords=(), bass=None, drums=None, rit=None, to: float = 0.72, hold: float | None = 2.0,
               seconds: float | None = None, length: float | None = None, roll_bpm: float | None = None,
               pedal: bool = True, room=None, room_tracks=(), send: str = 'room', until=None) -> 'Song':
        """The last chord of a ballad / jazz tune at `at` (a Section or position), in one call:
          chords    [(track, clip, ms[, delay]), ...]: each chord rolled (clip.strum: `ms` per note, upwards, at
                    roll_bpm - default the tempo at the ritardando's start x `to`) and placed `delay` beats after
                    `at` (the right hand lands after the left hand's roll); with pedal=True each chord track's pedal
                    lifts just before and goes down just after the chord (it rings in the pedal)
          bass      (track, pitch, dur, vel): the bass's last note
          drums     (track, clip): the cymbal / stir / soft kick under it (jazz.last_stir(kit, ...))
          rit       where the ritardando into the chord starts (to=`to` x the tempo; it stays slow)
          hold / seconds / length   the fermata on the chord (song.fermata)
          room      (from_db, to_db): the chord tracks (and room_tracks) send more into `send` while it rings, from
                    `at` to the end (`until`, default the section end)
        Everything stays overridable: leave a part out and write it by hand.
            s.ending(end, chords=[(b.comp, hold('Ab2 Eb3 G3', 7.9), 70), (b.piano, END_RH, 80, 0.25)],
                     bass=(b.bass, 'Ab1', 7, 92), drums=(b.drums, jazz.last_stir(kit, 8, every=2, last=3)),
                     rit=tag.bar(2), hold=2, length=4, room=(-13, -8))"""
        from .automation import ramp as _ramp_pts
        a = self._at(at)
        if rit is not None and roll_bpm is None:
            roll_bpm = self.tempo_at(self._at(rit)) * _num(to, 'ending to (factor)', 0.05, 1.0)
        elif roll_bpm is None:
            roll_bpm = self.tempo_at(a)
        tracks = []
        for ch in chords:
            if not isinstance(ch, (tuple, list)) or len(ch) not in (3, 4):
                raise ComposeError(f"ending(): chords are (track, clip, ms[, delay]), got {ch!r}")
            t, clip, ms = ch[0], as_clip(ch[1]), ch[2]
            c = clip.strum(ms=ms, bpm=roll_bpm)
            if len(ch) == 4:
                c = c.shift(ch[3])
            t.play(c, a)
            tracks.append(t)
        if pedal:
            for t in tracks:
                t.automate('instrument.pedal', [(a - 0.05, 0.0, 'step'), (a + 0.02, 1.0, 'step')])
        if bass is not None:
            t, pitch, dur, vel = bass
            t.note(pitch, a, dur=dur, vel=vel)
        if drums is not None:
            drums[0].play(drums[1], a)
        if rit is not None:
            self.ritardando((rit, a), to=to, a_tempo=False)
        if hold is not None or seconds is not None or length is not None:
            self.fermata(a, hold=None if seconds is not None else hold, seconds=seconds, length=length)
        if room is not None:
            end = self._at(until) if until is not None else (at.end if isinstance(at, (Section, Part)) else None)
            if end is None:
                raise ComposeError("ending(room=...): give until= (where the room ramp ends) for a beat position")
            for t in list(dict.fromkeys(tracks + list(room_tracks))):
                t.automate(f'send.{send}', _ramp_pts(a, end, room[0], room[1]))
        return self

    # --- music helpers bound to the song key / meter
    def prog(self, spec, bars: float = 1, meter=None) -> Progression:
        """Progression in the song key; chord lengths in bars (of the song's meter, or meter=(3, 4) /
        meter=waltz.meter for a section in another one): song.prog('i VI III VII'). It is a voicing.Harmony (a
        Progression that also voices itself: .voice(), .under(), .chorale(), .figure() ...)."""
        from .voicing import Harmony
        bpb = self.beats_per_bar if meter is None else _tempo.beats_per_bar(_tempo.parse_meter(meter, 'prog meter'))
        return Harmony(spec, key=self.key, bars=bars, beats_per_bar=bpb)

    def harmony(self, spec, at=0.0, *, key=None, bars: float = 1, meter=None):
        """A voicing.Harmony in the song key (or key=): a progression string (lengths in bars) or a voicing table
        [(dur, chord, top, bass[, {voice: pitch}])] (beats), placed at `at` (a beat or Section): its methods then
        work in song beats - s.harmony(T1, t1).under(theme, voicing.STRINGS)."""
        from .voicing import Harmony
        bpb = self.beats_per_bar if meter is None else _tempo.beats_per_bar(_tempo.parse_meter(meter, 'harmony meter'))
        return Harmony(spec, key=self.key if key is None else key, at=self._at(at), bars=bars, beats_per_bar=bpb)

    def arc(self, rides: dict, *, within=None, glide: float = 0.5, default: float = 0.0, curve: str = 'smooth',
            name: str = 'arc'):
        """The conductor's arc: a gain ride per section on the master input (a utility `name` first in the master
        chain, before any compressor / limiter) - soft passages up, early fortissimos under the climax - without
        touching the written dynamics. rides {section name: dB} (others `default`); each section glides there over
        the `glide` beats before it (`curve`); within {section name: [(beat in it, dB[, curve])]} adds points inside
        a section (a subito p, a climb). The first section starts at its ride. Returns the master bus."""
        from .patches import fx as _fx
        within = within or {}
        names = [x.name for x in self.sections]
        unknown = [n for n in list(rides) + list(within) if n not in names]
        if unknown:
            raise ComposeError(f"arc: unknown section(s) {unknown}; sections: {', '.join(names)}")
        self.master.add_fx(_fx.utility(gain=0.0, name=name), first=True)
        pts: list = []
        for i, sec in enumerate(self.sections):
            g = rides.get(sec.name, default)
            a = float(sec.start)
            if i == 0:
                pts.append((a, g))
            else:
                pts += [(a - glide, pts[-1][1]), (a, g, curve)]
            pts += [(a + p[0],) + tuple(p[1:]) for p in within.get(sec.name, ())]
        self.master.automate(f'fx.{name}.gain', sorted(pts, key=lambda p: p[0]))
        return self.master

    def motif(self, spec, dur=0.5):
        """Motif in the song key: song.motif('1:1/8 3:1/8 5:1/4')."""
        return self.key.motif(spec, dur)

    # --- nodes
    def _new_id(self, id, what: str) -> str:
        if not isinstance(id, str) or not _ID_RE.match(id):
            raise ComposeError(f"{what} id {id!r} must match [a-z0-9_-]+ (at most 48 characters), "
                               f"e.g. {_slug(id)[:48]!r}")
        if id == 'master':
            raise ComposeError("'master' is reserved")
        if id in self.tracks or id in self.buses:
            raise ComposeError(f"id {id!r} is already used by a {'track' if id in self.tracks else 'bus'}")
        if id in self._ghosts:
            raise ComposeError(f"id {id!r} is reserved for a sidechain key track")
        return id

    def track(self, id: str, sound, *, fx=(), gain_db: float = 0.0, pan: float | None = None,
              output='master', sends: dict | None = None, mute: bool = False) -> Track:
        """Add an instrument track. sound = Patch, patch name, inst.va(...) or {'type', 'params'}.
        Patch fx come first, then `fx`; gain_db adds to the patch level; pan None keeps the patch pan;
        sends merge with the patch's (patch sends to buses that don't exist are dropped with a warning)."""
        t = Track(self, self._new_id(id, 'track'), sound, fx, gain_db, pan, output, sends, mute)
        self.tracks[id] = t
        return t

    def bus(self, id: str, fx=(), *, gain_db: float = 0.0, pan: float | None = None, output='master',
            sends: dict | None = None, mute: bool = False) -> Bus:
        """Add a bus (group or effect return). Route with track.to(bus) or sends={bus: -12}."""
        b = Bus(self, self._new_id(id, 'bus'), fx, gain_db, pan, output, sends, mute)
        self.buses[id] = b
        return b

    def node(self, id: str):
        if id == 'master':
            return self.master
        n = self.tracks.get(id) or self.buses.get(id)
        if n is None:
            raise ComposeError(f"no track or bus {id!r}")
        return n

    def _return_bus(self, id, patch_name, fallback: FX, params, gain_db) -> Bus:
        if id in self.buses:
            if params or gain_db:
                raise ComposeError(f"bus {id!r} already exists; set its params when it is first created "
                                   f"(or pass another id: song.{patch_name[4:]}('{id}2', ...))")
            return self.buses[id]
        if _patches.has(patch_name):
            p = _patches.get(patch_name)
            if params:  # the params belong to the reverb/delay, wherever it sits in the chain
                p = p.but_fx(fallback.type, **params) if any(f.type == fallback.type for f in p.fx) else p.but(**params)
            return self.bus(id, p, gain_db=gain_db)
        return self.bus(id, [fallback.but(**params)], gain_db=gain_db)

    def hall(self, id: str = 'hall', gain_db: float = 0.0, **params) -> Bus:
        """Big reverb return bus (patch 'bus/hall' if the library has it, else a 100% wet hall reverb).
        Extra params go to the reverb: song.hall(decay=3.5, predelay=30)."""
        return self._return_bus(id, 'bus/hall', FX('reverb', {'type': 'hall', 'mix': 1.0}), params, gain_db)

    def plate(self, id: str = 'plate', gain_db: float = 0.0, **params) -> Bus:
        """Short bright reverb return ('bus/plate' patch or a 100% wet reverb)."""
        return self._return_bus(id, 'bus/plate', FX('reverb', {'type': 'plate', 'mix': 1.0}), params, gain_db)

    def echo(self, id: str = 'echo', gain_db: float = 0.0, **params) -> Bus:
        """Delay return ('bus/echo' patch or a 100% wet delay)."""
        return self._return_bus(id, 'bus/echo', FX('delay', {'mix': 1.0}), params, gain_db)

    def gated(self, id: str = 'gated', gain_db: float = 0.0, *, key=None, pitches=None, **params) -> Bus:
        """80s gated reverb return for snares/toms ('bus/gated' patch or a 100% wet gatedreverb).

        key=<track> keys the gate from that track instead of the bus input, and pitches='snare' (or
        ['snare', 'clap'], [38, 40]) from only those notes of it, through the muted ghost key track that
        sidechain()/duck() use: then only the snare opens the gate, so the whole kit may feed the reverb
        (kick and hats ring only inside the snare's burst). Calling it again with just key= keys an existing bus.
            kit = s.track('drums', 'synthwave/drums_outrun')                # its patch sends to 'gated'
            s.gated(gain_db=-2, hold=250, key=kit, pitches='snare')"""
        if pitches is not None and key is None:
            raise ComposeError("gated(pitches=...) needs key=<drum track> whose notes open the gate, "
                               "e.g. s.gated(key=kit, pitches='snare')")
        kid = None if key is None else _ref(key)
        if kid is not None and kid == id:
            raise ComposeError(f"bus {id!r}: gated(key=...) can't key the gate from the gated bus itself")
        ps = None
        if pitches is not None:
            if kid not in self.tracks:
                raise ComposeError(f"gated(pitches=) needs a key *track*; {kid!r} is not a track"
                                   + (" (create it before this call)" if kid not in self.buses else ''))
            ps = tuple(sorted({drum(p) for p in (pitches if isinstance(pitches, (list, tuple, set)) else [pitches])}))
        bus = self._return_bus(id, 'bus/gated', FX('gatedreverb', {'mix': 1.0}), params, gain_db)
        if kid is None:
            return bus
        gates = [f for f in bus.fx if f.type == 'gatedreverb']
        if not gates:
            raise ComposeError(f"bus {bus.id!r} has no gatedreverb to key (chain: "
                               f"{', '.join(f.type for f in bus.fx) or 'empty'})")
        current = {f.sidechain for f in gates} - {None}
        same = {g for g in current if (self._ghosts.get(g) == (kid, ps) if ps is not None else g == kid)}
        if current - same:
            raise ComposeError(f"bus {bus.id!r}: the gatedreverb is already keyed from {sorted(current)[0]!r}; "
                               f"use another bus id for a second keyed gate: s.gated('{bus.id}2', key=...)")
        src = self._ghost(kid, ps, 'gated(pitches=)') if ps is not None else kid
        for f in gates:
            f.sidechain = src
        return bus

    def sidechain(self, *targets, key, pitches=None, **params) -> None:
        """Duck every target from `key` (classic pump): song.sidechain(pad, bass, key=drums, pitches='kick')."""
        if not targets:
            raise ComposeError("sidechain() needs at least one target track/bus")
        for t in targets:
            self.node(_ref(t)).duck(key, pitches, **params)

    def carve(self, *targets, key, freq: float = 2500.0, q: float = 0.7, depth: float = 4.0, **params) -> None:
        """Carve room for a lead: every target gets a dynamic EQ keyed by `key` (a band-mode compressor) that dips
        its `freq` band (default 2.5 kHz, Q 0.7: ~1.2-4.5 kHz) by up to `depth` dB while the lead plays and releases
        in the lead's gaps: song.carve(strings, piano, rhodes, key=sax, depth=4). Unlike sidechain() the bed keeps
        its level and body; only the lead's presence band steps aside."""
        if not targets:
            raise ComposeError("carve() needs at least one target track/bus")
        for t in targets:
            self.node(_ref(t)).carve(key, freq, q, depth, **params)

    def _carve(self, node, key, freq, q, depth, params) -> None:
        kid = _ref(key)
        if kid == node.id:
            raise ComposeError(f"carve(): {node.id!r} cannot be keyed by itself")
        opts = {'threshold': -40.0, 'ratio': 4.0, 'knee': 6.0, 'attack': 10.0, 'release': 250.0, **params,
                'range': depth, 'band': freq, 'bandq': q}
        node.fx.append(FX('compressor', opts, sidechain=kid))

    def _duck(self, node, key, pitches, params) -> None:
        if key is None:
            node.fx.append(FX('ducker', {'mode': 'tempo', **params}))
            return
        kid = _ref(key)
        if pitches is None:
            node.fx.append(FX('ducker', params, sidechain=kid))
            return
        ps = tuple(sorted({drum(p) for p in (pitches if isinstance(pitches, (list, tuple, set)) else [pitches])}))
        node.fx.append(FX('ducker', params, sidechain=self._ghost(kid, ps, 'sidechain pitches=')))

    def _ghost(self, kid: str, ps: tuple[int, ...], what: str) -> str:
        """Id of a muted key track playing only pitches `ps` of track `kid` (created on first use)."""
        if kid not in self.tracks:
            raise ComposeError(f"{what} needs a key *track*; {kid!r} is not a track"
                               + (" (create it before this call)" if kid not in self.buses else ''))
        gid = next((g for g, v in self._ghosts.items() if v == (kid, ps)), None)
        if gid is None:
            gid, k = f"{kid[:44]}-key", 2   # ids are limited to 48 characters
            while gid in self._ghosts or gid in self.tracks or gid in self.buses:
                gid, k = f"{kid[:40]}-key{k}", k + 1
            self._ghosts[gid] = (kid, ps)
        return gid

    def _window(self, window) -> tuple:
        """(startBeat | None, endBeat | None) of a modulator window: None, a Section (its span) or (start, end)
        with beats / Sections (= their start) / None."""
        if window is None:
            return (None, None)
        if isinstance(window, Section):
            return (window.start, window.end)
        if isinstance(window, str):
            s = self[window]
            return (s.start, s.end)
        if isinstance(window, (tuple, list)) and len(window) == 2:
            a = None if window[0] is None else self._at(window[0])
            b = None if window[1] is None else self._at(window[1])
            if a is not None and a < 0:
                raise ComposeError(f"modulator window starts before beat 0 ({a:g})")
            if a is not None and b is not None and b <= a:
                raise ComposeError(f"modulator window ({a:g}, {b:g}) is empty: the end must be after the start")
            return (a, b)
        raise ComposeError(f"window must be a Section or (start, end), got {window!r}")

    def _bind_mod(self, node, m: Mod) -> None:
        """Resolve a modulator's node references (follow key, envelope trigger, pitches= ghost key tracks)."""
        where = f"{node.kind} {node.id!r}"
        if m.kind == 'follow':
            kid = _ref(m.node)
            if kid == 'master':
                raise ComposeError(f"{where}: follow('master') is impossible - every node feeds the master")
            if m.pitches is not None:
                kid = self._ghost(kid, m.pitches, 'follow(pitches=)')
            if kid == node.id:
                raise ComposeError(f"{where}: a node can't follow its own output")
            m.node = kid
        elif m.kind == 'envelope':
            if m.trigger is None and m.pitches is None:
                if node.kind != 'track':
                    raise ComposeError(f"{where}: envelope() is triggered by this node's notes, but a {node.kind} has "
                                       f"none; pass trigger=<track> (e.g. trigger=kit, pitches='kick')")
            else:
                tid = node.id if m.trigger is None else _ref(m.trigger)
                m.trigger = self._ghost(tid, m.pitches, 'envelope(pitches=)') if m.pitches is not None else tid
        if m.retrigger and node.kind != 'track':
            raise ComposeError(f"{where}: lfo(retrigger=True) restarts on this node's notes, but a {node.kind} has none")

    def export(self, stems: bool | None = None, bit_depth: int | None = None) -> 'Song':
        """Render options: stems=True writes one WAV per track/bus; bit_depth 16 | 24 | 32 (float)."""
        if stems is not None:
            self.stems = bool(stems)
        if bit_depth is not None:
            if bit_depth not in (16, 24, 32):
                raise ComposeError(f"bit_depth must be 16, 24 or 32, got {bit_depth!r}")
            self.bit_depth = bit_depth
        return self

    def mix(self, mix: dict) -> 'Song':
        """Apply a mix engineer's MIX dict (agentsound.mixer: 'trim' / 'ride' dB per track and section, 'duck'
        sidechains, 'eq' dips) - the settings mixer.auto() / mixer.plan() write. Call it once, at the end of build();
        a module-level MIX = {...} in song.py is applied by the CLI instead (not both)."""
        from . import mixer
        return mixer.apply(self, mix)

    def add_compile_hook(self, fn) -> None:
        """Run fn(song) at the start of every compile(), before anything is read: moves that need the whole song
        (heroes.hero(): echo throws on every phrase end the hero plays, rides per section). A hook must be idempotent
        (compile() can run more than once): it replaces what its last run wrote."""
        if not callable(fn):
            raise ComposeError(f"add_compile_hook() takes a callable fn(song), got {fn!r}")
        self._compile_hooks.append(fn)

    # --- compile
    def compile(self) -> dict:
        """Validate everything and return the render dict (docs/RENDER_FORMAT.md). Raises ComposeError
        with a precise message on any problem; non-fatal issues go to song.warnings."""
        self.warnings = list(dict.fromkeys(self.advice))   # the players' warnings (drummer), then compile's own
        for fn in self._compile_hooks:
            fn(self)
        L = self.length
        if L <= 0:
            raise ComposeError("the song is empty: add sections (song.section('intro', bars=8)) and notes")
        if L > 100000:
            raise ComposeError(f"the song is {L:g} beats long; the engine limit is 100000 beats")
        if not self.tracks:
            raise ComposeError("the song has no tracks: add one with song.track('id', sound)")
        track_ids, bus_ids = set(self.tracks), set(self.buses)
        tempo_points = self.tempo_points()
        tempo_map = _tempo.TempoMap(tempo_points)
        # humanize / groove milliseconds at the local tempo (the plain tempo when it never changes)
        const_bpm = self.tempo if self._tempo_plan.empty() else tempo_points[0][1]   # (e.g. set_tempo(0, ...) alone)
        local_bpm = const_bpm if tempo_map.constant else tempo_map.bpm_at
        marks: dict[str, list] = {}
        notes = {t.id: self._compile_notes(t, L, marks, local_bpm) for t in self.tracks.values()}
        all_ids = track_ids | bus_ids | set(self._ghosts)
        edges: dict[tuple[str, str], str] = {}

        out_tracks = []
        silent: list[dict] = []          # compile-time silent notes (agentsound.silent_notes) -> analysis.silentNotes
        grid = self.meter_grid()
        for t in self.tracks.values():
            d = self._compile_node(t, all_ids, bus_ids, track_ids, edges)
            d['notes'] = notes[t.id]
            if not d['notes']:
                self.warnings.append(f"track {t.id!r} has no notes")
            switches = self._performance(t, d, marks.get(t.id), L)
            if not t.mute and d['notes']:
                for f in _silent.check(t.id, d['instrument'], d['notes'], d.get('automation'), grid,
                                       _silent.instrument_info(t.instrument)):
                    silent.append(f)
                    self.warnings.append(f"silent notes: {f['message']}")
            d['instrument'] = self._prune_zones(t.id, d['instrument'], d['notes'], switches=switches)
            self._sfz_warnings(t)
            out_tracks.append(self._order(d, t))
        for gid, (kid, ps) in self._ghosts.items():
            key = self.tracks[kid]
            gn = [n for n in notes[kid] if n[2] in ps]
            if not gn:
                self.warnings.append(f"sidechain key {gid!r}: track {kid!r} has no notes with pitches {list(ps)}")
            out_tracks.append({'id': gid, 'instrument': self._prune_zones(gid, key.instrument.to_dict(), gn, quiet=True),
                               'fx': [], 'gainDb': round(key.gain_db, 4), 'pan': 0.0,
                               'mute': True, 'output': 'master',
                               'sends': {}, 'notes': gn, 'automation': []})
            edges.setdefault((gid, 'master'), 'output')
        out_buses = []
        for b in self.buses.values():
            d = self._compile_node(b, all_ids, bus_ids, track_ids, edges)
            out_buses.append(self._order(d, b))
        fed = {v for (u, v), lbl in edges.items() if lbl in ('output', 'send')}
        for b in self.buses:
            if b not in fed:
                self.warnings.append(f"bus {b!r} receives nothing (route with track.to(bus) or sends)")
        master = self._compile_node(self.master, all_ids, bus_ids, track_ids, edges)
        if not any(f.type == 'limiter' for f in self.master.fx):
            self.warnings.append("master chain has no limiter: add song.master.add(fx.limiter()) "
                                 "(or master.use('master/...')) to keep peaks safe")
        self._check_cycles(edges)
        out_master = {'fx': master['fx'], 'gainDb': master['gainDb'], 'automation': master['automation']}
        if master.get('modulators'):
            out_master['modulators'] = master['modulators']

        # (a constant tempo outside the "tempo" range 30..300, e.g. set_tempo(0, 20), stays a one-point map)
        plain = tempo_map.constant and 30.0 <= const_bpm <= 300.0
        timing: dict = {'tempo': const_bpm} if plain else {'tempoMap': tempo_points}
        meter = self._meter_points()
        if meter != [[0.0, 4, 4]]:
            timing['meter'] = [[_r6(b), n, d] for b, n, d in meter]
        extra: dict = {}
        if silent:   # report-only (never changes the audio): the engine repeats them as 'silent_notes' warnings
            extra['analysis'] = {'silentNotes': silent}
        return {
            'format': 'agentsound.render',
            'version': 1,
            'title': self.title,
            'sampleRate': self.sample_rate,
            **timing,
            'lengthBeats': _r6(L),
            'tailSeconds': self.tail,
            'seed': self.seed,
            'sections': [{'name': s.name, 'startBeat': _r6(s.start), 'endBeat': _r6(s.end)} for s in self.sections],
            'tracks': out_tracks,
            'buses': out_buses,
            'master': out_master,
            'export': {'stems': self.stems, 'bitDepth': self.bit_depth},
            **extra,
        }

    def _prune_zones(self, tid: str, inst: dict, notes: list, quiet: bool = False, switches=None) -> dict:
        """Sampler zone lists keep only the zones a note of this track can trigger (key after the 'transpose' param,
        velocity - any velocity with layers='dynamics' -, the keyswitch articulations the track uses; release zones
        too): big sample libraries load only what the song plays. `switches`: (keyswitch keys, the keys the track
        selects) from _performance(). A stack prunes each sampler layer with the notes that reach it (its key and
        velocity range, transpose, velocity curve)."""
        if inst.get('type') == 'stack':
            return self._prune_stack(tid, inst, notes, quiet)
        zones = inst['params'].get('samples') if inst.get('type') == 'sampler' else None
        if not isinstance(zones, list) or not zones:
            return inst
        tr = inst['params'].get('transpose', 0)
        tr = int(tr) if isinstance(tr, (int, float)) and not isinstance(tr, bool) else 0
        sw_keys, used = switches if switches else (set(), None)
        any_vel = inst['params'].get('layers') == 'dynamics'
        vels: dict[int, set[int]] = {}
        for n in notes:
            if int(n[2]) in sw_keys:
                continue   # keyswitch notes never sound
            k = int(n[2]) + tr
            if 0 <= k <= 127:
                vels.setdefault(k, set()).add(int(n[3]))

        def selected(z: dict) -> bool:
            if used is None:
                return True
            last, down = z.get('swLast'), z.get('swDown')
            if last is not None:
                lo_, hi_ = (last, last) if isinstance(last, int) else (last[0], last[1])
                if not any(lo_ <= k <= hi_ for k in used):
                    return False
            return down is None or down in used

        def reachable(z: dict) -> bool:
            lo, hi = z.get('lo', 0), z.get('hi', 127)
            vlo, vhi = (0, 127) if any_vel else (z.get('vello', 0), z.get('velhi', 127))
            return selected(z) and any(lo <= k <= hi and any(vlo <= v <= vhi for v in vs) for k, vs in vels.items())

        keep = [z for z in zones if reachable(z)]
        if len(keep) == len(zones):
            return inst
        if not keep:
            keep = zones[:1]
            if not quiet and notes:
                self.warnings.append(f"track {tid!r}: no note can sound on its sampler (none of its {len(zones)} zones "
                                     f"covers the played keys / velocities)")
        elif not quiet and len(zones) > 8:
            ks = sorted(vels)
            vs = sorted({v for s in vels.values() for v in s})
            self.warnings.append(f"track {tid!r} (sampler): {len(keep)} of {len(zones)} zones can sound with its notes "
                                 f"(keys {ks[0]}-{ks[-1]}, velocities {vs[0]}-{vs[-1]}); only those load")
        out = dict(inst)
        out['params'] = {**inst['params'], 'samples': keep}
        return out

    def _prune_stack(self, tid: str, inst: dict, notes: list, quiet: bool) -> dict:
        params = dict(inst['params'])
        layers = []
        for i, L in enumerate(params.get('layers') or []):
            child = L.get('instrument') or {}
            if child.get('type') != 'sampler':
                layers.append(L)
                continue
            klo, khi = int(L.get('keylo', 0)), int(L.get('keyhi', 127))
            vlo, vhi = int(L.get('vello', 0)), int(L.get('velhi', 127))
            tr = int(L.get('transpose', 0))
            curve, scale = float(L.get('velcurve', 1.0)), float(L.get('velscale', 1.0))
            mine = []
            for n in notes:
                k, v = int(n[2]), int(n[3])
                if not (klo <= k <= khi and vlo <= v <= vhi) or not 0 <= k + tr <= 127:
                    continue
                if curve != 1.0 or scale != 1.0:   # the velocity the child gets (both neighbours: rounding)
                    x = min(1.0, max(1.0 / 127.0, (v / 127.0) ** curve * scale)) * 127.0
                    vs = sorted({max(1, min(127, math.floor(x))), max(1, min(127, math.ceil(x)))})
                else:
                    vs = [v]
                mine.extend([n[0], n[1], k, w] for w in vs)   # (the layer transpose is added below, with the child's)
            child_tr = child['params'].get('transpose', 0)
            child_tr = int(child_tr) if isinstance(child_tr, (int, float)) and not isinstance(child_tr, bool) else 0
            probe = {**child, 'params': {**child['params'], 'transpose': child_tr + tr}}
            pruned = self._prune_zones(f"{tid}.layers.{L.get('id', i)}", probe, mine, quiet=quiet or not mine)
            if pruned is probe:
                layers.append(L)
            else:
                pp = dict(pruned['params'])
                if 'transpose' in child['params']:
                    pp['transpose'] = child['params']['transpose']
                else:
                    pp.pop('transpose', None)
                layers.append({**L, 'instrument': {**pruned, 'params': pp}})
        params['layers'] = layers
        return {**inst, 'params': params}

    def _sfz_warnings(self, t) -> None:
        """One warning per SFZ instrument that uses features the sampler does not play (or has file problems)."""
        if t.instrument is not None and t.instrument.type == 'stack':
            for x in t.instrument.params['layers']:
                self._sfz_info_warnings(f"{t.id!r} (layer {x.id!r})", (x.instrument.info or {}).get('sfz'))
            return
        self._sfz_info_warnings(repr(t.id), (t.instrument.info or {}).get('sfz') if t.instrument is not None else None)

    def _sfz_info_warnings(self, who: str, info) -> None:
        if not info:
            return
        name = os.path.basename(info.get('path', 'sfz'))
        if info.get('unsupported'):
            what = ', '.join(f"{k} ({v})" for k, v in list(info['unsupported'].items())[:8])
            more = len(info['unsupported']) - 8
            self.warnings.append(f"track {who}: {name} uses SFZ features the sampler does not play: {what}"
                                 + (f" and {more} more" if more > 0 else '')
                                 + f" (details: python -m agentsound sfz \"{info.get('path')}\")")
        if info.get('problems'):
            self.warnings.append(f"track {who}: {name}: " + '; '.join(info['problems'][:4]))

    @staticmethod
    def _order(d: dict, node) -> dict:
        keys = ['id', 'instrument', 'fx', 'gainDb', 'pan', 'mute', 'output', 'sends', 'notes', 'automation', 'modulators']
        out = {k: d[k] for k in keys if k in d}
        if not node.mute:
            out.pop('mute', None)
        if not out.get('modulators'):
            out.pop('modulators', None)
        return out

    def _performance(self, t: 'Track', d: dict, marks: list | None, L: float):
        """Per-note articulations -> keyswitch notes, per-note glides -> 'instrument.glide' steps (articulation.py).
        Returns (keyswitch keys, the keys the track selects) of a sampler with keyswitches (for zone pruning), else
        None. d['notes'] are the compiled notes (sorted), `marks` their (articulation, glide) marks."""
        inst = d['instrument']
        zones = inst['params'].get('samples') if inst.get('type') == 'sampler' else None
        has_marks = bool(marks) and any(a is not None or g for a, g in marks)
        if not isinstance(zones, list):
            if has_marks:
                raise ComposeError(f"track {t.id!r}: notes carry articulation / glide marks (articulation.py), but its "
                                   f"instrument is {inst.get('type')!r}; they need a sampler (inst.sfz / inst.sfz_multi / "
                                   f"a sampled/* patch)")
            return None
        # the keyswitch keys and the default articulation of the zone set
        sw_keys: set[int] = set()
        default = None
        for z in zones:
            last = z.get('swLast')
            if last is not None:
                sw_keys.update([last] if isinstance(last, int) else range(last[0], last[1] + 1))
            if z.get('swDown') is not None:
                sw_keys.add(z['swDown'])
            if z.get('swLo') is not None and z.get('swHi') is not None:
                sw_keys.update(range(z['swLo'], z['swHi'] + 1))
            if default is None and z.get('swDefault') is not None:
                default = z['swDefault']
        used = {default} if default is not None else set()
        used |= {int(n[2]) for n in d['notes'] if int(n[2]) in sw_keys}   # keyswitch notes played by hand
        if not has_marks:
            return (sw_keys, used) if sw_keys else None
        info = (t.instrument.info or {}).get('sfz') or {}
        table = {str(k).lower(): v for k, v in (info.get('keyswitches') or {}).items()}
        notes = d['notes']
        # --- detached notes (staccato, spiccato, pizzicato, marcato marks) never touch the next note: on a mono='legato'
        # sampler touching / overlapping notes play legato transitions
        if inst['params'].get('mono') == 'legato':
            gap = 0.006 * self.tempo / 60.0          # 6 ms
            starts = sorted({n[0] for n in notes if int(n[2]) not in sw_keys})
            for (a, _), n in zip(marks, notes):
                if a is None or int(n[2]) in sw_keys:
                    continue
                nxt = next((x for x in starts if x > n[0] + 1e-9), None)
                if nxt is not None and n[0] + n[1] > nxt - gap and _art.detached(a):
                    n[1] = max(round(nxt - gap - n[0], 6), min(n[1], 1e-3))
            for i, (a, _) in enumerate(marks):   # ... and nothing ties into a detached note
                if a is None or not _art.detached(a):
                    continue
                s0 = notes[i][0]
                for n in notes:
                    if int(n[2]) not in sw_keys and n[0] < s0 - 1e-9 and n[0] + n[1] > s0 - gap:
                        n[1] = max(round(s0 - gap - n[0], 6), min(n[1], 1e-3))
        # --- articulations -> keyswitch notes
        want: list = []
        for (a, _), n in zip(marks, notes):
            want.append(None if a is None else self._keyswitch(t, a, table, sw_keys))
        if any(k is not None for k in want):
            if not sw_keys:
                raise ComposeError(f"track {t.id!r}: notes ask for articulations but its sampler has no keyswitch "
                                   f"articulations (use a keyswitch program via inst.sfz, or inst.sfz_multi)")
            events = []          # (beat, key)
            cur = default
            i = 0
            while i < len(notes):
                start = notes[i][0]
                j = i
                while j < len(notes) and notes[j][0] == start:
                    j += 1
                group, i = want[i:j], j
                ks = [k if k is not None else default for k in group]
                ks = [k for k in ks if k is not None]
                if not ks:
                    continue
                if len(set(ks)) > 1:
                    self.warnings.append(f"track {t.id!r}: notes at beat {start:g} ask for different articulations; "
                                         f"one keyswitch at a time: all play {self._art_label(ks[-1], table)!r}")
                k = ks[-1]
                if k != cur:
                    events.append((start, k))
                    cur = k
            ks_notes = []
            for j, (b, k) in enumerate(events):
                end = events[j + 1][0] if j + 1 < len(events) else L
                ks_notes.append([b, max(round(end - b, 6), 1e-6), k, 1])
                used.add(k)
            # keyswitches first at the same beat: the engine plays same-sample note-ons in list order
            tagged = [(n, 1) for n in notes] + [(n, 0) for n in ks_notes]
            tagged.sort(key=lambda x: (x[0][0], x[1], x[0][2], x[0][1]))
            d['notes'] = [n for n, _ in tagged]
        # --- glides -> 'instrument.glide' steps just before the glided notes
        glides = [(n[0], g) for (_, g), n in zip(marks, notes) if g]
        if glides:
            if any(a.get('target') == 'instrument.glide' for a in d['automation']):
                raise ComposeError(f"track {t.id!r}: notes carry glide marks and the track also automates "
                                   f"'instrument.glide'; use one of the two")
            if inst['params'].get('mono') != 'legato':
                self.warnings.append(f"track {t.id!r}: glide marks need the sampler's mono='legato' (and overlapping "
                                     f"notes: articulation.legato) - they have no effect here")
            starts = sorted({n[0] for n in notes if int(n[2]) not in sw_keys})
            # a glide bends from the note before: it needs one still sounding (overlapping or touching) at its start
            loose = [b for b, _ in glides
                     if not any(n[0] < b - 1e-9 and n[0] + n[1] >= b - 1e-6 and int(n[2]) not in sw_keys for n in notes)]
            if loose and inst['params'].get('mono') == 'legato':
                self.warnings.append(f"track {t.id!r}: glide marks at beat(s) {', '.join(f'{b:g}' for b in loose[:6])} "
                                     f"have no note sounding into them (a rest or a detached note before): no effect - "
                                     f"tie the line (articulation.legato) to glide")
            base = inst['params'].get('glide', 0.0)
            pts: list = [(0.0, base)]
            for b, g in glides:
                prev = max((x for x in starts if x < b - 1e-9), default=None)
                lead = max(b - 0.05, (prev + b) / 2.0 if prev is not None else b - 0.05, 0.0)
                pts += [(lead, g, 'step'), (b + 1e-3, base, 'step')]
            d['automation'].append({'target': 'instrument.glide', 'points': _auto.normalize(pts, f"track {t.id!r} glides")})
        return (sw_keys, used)

    @staticmethod
    def _art_label(key: int, table: dict) -> str:
        return next((name for name, k in table.items() if k == key), str(key))

    @staticmethod
    def _keyswitch(t: 'Track', a, table: dict, sw_keys: set) -> int:
        """The keyswitch key of an articulation mark: a label of the instrument's keyswitches (exact, then a word or a
        prefix of one: 'stac' -> 'Staccato'), a key number or a note name ('C1')."""
        where = f"track {t.id!r}: articulation {a!r}"
        listing = ', '.join(f"{name} ({k})" for name, k in table.items()) or 'none (keys: ' + \
            ', '.join(map(str, sorted(sw_keys))) + ')'
        if isinstance(a, int):
            if a not in sw_keys:
                raise ComposeError(f"{where} is not a keyswitch key of the instrument; articulations: {listing}")
            return a
        if a in table:
            return table[a]
        hits = [k for name, k in table.items() if a in _art._words(name) or any(w.startswith(a) for w in _art._words(name))]
        if len(set(hits)) == 1:
            return hits[0]
        if not hits:
            try:
                from .theory import note as _n
                k = _n(a)
            except ComposeError:
                k = None
            if k is not None and k in sw_keys:
                return k
            raise ComposeError(f"{where} matches no articulation of the instrument; articulations: {listing}")
        raise ComposeError(f"{where} is ambiguous; articulations: {listing}")

    def _compile_notes(self, t: Track, L: float, marks: dict | None = None, bpm=None) -> list[list]:
        """The track's notes for the render JSON; bpm = the tempo for groove / humanize ms (a number, or a
        function of the beat when the tempo changes)."""
        for n, origin in zip(t._notes, t._origin):
            where = (f"track {t.id!r}: note (start={n.start:g}, dur={n.dur:g}, pitch={n.pitch}, vel={n.vel})"
                     + (f" placed at {origin}" if origin else ''))
            if n.start < 0:
                raise ComposeError(f"{where} starts before beat 0")
            if n.start >= L - 1e-9:
                raise ComposeError(f"{where} starts at/after the song end (beat {L:g}); add or lengthen "
                                   f"sections, or don't place notes there")
        c = Clip._raw(t._notes, L)
        bpm = self.tempo if bpm is None else bpm
        marked = any(_art.articulation_of(n) is not None or _art.glide_of(n) for n in c)
        if t._groove is not None:
            drums = t.instrument.type == 'drums'
            if marked:   # note by note (a groove moves each note on its own), so the marks stay on their notes
                c = Clip._raw([_art._mark(_apply_groove(Clip._raw([n], L), t._groove, bpm=bpm, drums=drums)[0],
                                          art=_art.articulation_of(n), gl=_art.glide_of(n)) for n in c], L)
            else:
                c = _apply_groove(c, t._groove, bpm=bpm, drums=drums)
        if t._human is not None:
            ms, vel, seed = t._human
            s = seed_int(f"{self.seed}:{t.id}:humanize") if seed is None else seed_int(seed)
            c = _apply_humanize(c, timing_ms=ms, vel=vel, bpm=bpm, seed=s)
        out = []
        for n in c:
            where = f"track {t.id!r}: note (start={n.start:g}, dur={n.dur:g}, pitch={n.pitch}, vel={n.vel})"
            if not (math.isfinite(n.start) and math.isfinite(n.dur) and n.dur > 0):
                raise ComposeError(f"{where} has a non-finite time or non-positive duration")
            if not 0 <= n.pitch <= 127 or not 1 <= n.vel <= 127:
                raise ComposeError(f"{where}: pitch must be 0..127 and velocity 1..127")
            start = min(max(n.start, 0.0), L - 1e-4)  # groove/humanize shifts at the song edges
            out.append(([_r6(start), max(_r6(n.dur), 1e-6), int(n.pitch), int(n.vel)],
                        (_art.articulation_of(n), _art.glide_of(n))))
        out.sort(key=lambda x: (x[0][0], x[0][2], x[0][1]))
        if marks is not None and marked:
            marks[t.id] = [m for _, m in out]
        return [n for n, _ in out]

    def _compile_node(self, node: _Node, all_ids, bus_ids, track_ids, edges) -> dict:
        where = f"{node.kind} {node.id!r}"
        chain = []
        for i, f in enumerate(node.fx):
            d = f.to_dict()
            if f.sidechain is not None:
                if f.sidechain not in all_ids:
                    raise ComposeError(f"{where}: fx #{i} ({f.type}) sidechain {f.sidechain!r} is not a track or bus")
                if f.sidechain == node.id:
                    raise ComposeError(f"{where}: fx #{i} ({f.type}) can't use itself as sidechain key")
                edges.setdefault((f.sidechain, node.id), 'sidechain')
            chain.append(d)
        d: dict = {'id': node.id, 'fx': chain, 'gainDb': round(node.gain_db, 4), 'pan': round(node.pan, 4),
                   'mute': node.mute}
        if isinstance(node, Track):
            d['instrument'] = node.instrument.to_dict()
        if node.kind != 'master':
            out = node.output
            if out != 'master' and out not in bus_ids:
                kind = 'a track' if out in track_ids else 'not a bus'
                raise ComposeError(f"{where}: output {out!r} is {kind}; outputs must be a bus id or 'master'")
            if out == node.id:
                raise ComposeError(f"{where} can't output to itself")
            d['output'] = out
            edges.setdefault((node.id, out), 'output')
            sends = {}
            for b, db in node._patch_sends.items():
                if b in bus_ids and b != node.id:
                    sends[b] = db
                else:
                    self.warnings.append(f"{where}: patch send to {b!r} dropped (no such bus; create it with "
                                         f"song.bus({b!r}, ...) or song.hall()/plate()/echo())")
            for b, db in node.sends.items():
                if b not in bus_ids:
                    raise ComposeError(f"{where}: send to {b!r} but there is no bus {b!r} "
                                       f"(buses: {', '.join(sorted(bus_ids)) or 'none'})")
                if b == node.id:
                    raise ComposeError(f"{where} can't send to itself")
                sends[b] = db
            d['sends'] = {b: round(v, 4) for b, v in sends.items()}
            for b in sends:
                edges.setdefault((node.id, b), 'send')
        send_levels = d.get('sends', {})
        lane_targets = {self._resolve_target(node, t, node.fx, set(send_levels)) for t, _ in node._auto
                        if not t.startswith('mod.')}
        mods, mod_lanes = self._compile_mods(node, node.fx, send_levels, lane_targets, all_ids, track_ids, edges)
        d['automation'] = self._compile_auto(node, node.fx, set(send_levels), mod_lanes)
        if mods:
            d['modulators'] = mods
        return d

    def _compile_auto(self, node: _Node, chain: list[FX], send_ids: set[str], extra=()) -> list[dict]:
        where = f"{node.kind} {node.id!r}"
        groups: dict[str, list] = {}
        for target, pts in node._auto:
            groups.setdefault(self._resolve_target(node, target, chain, send_ids), []).extend(pts)
        for target, pts in extra:  # modulator fields given as point lists (depth=ramp(...))
            groups.setdefault(target, []).extend(pts)
        out = []
        for t, pts in groups.items():
            norm = _auto.normalize(pts, f"{where} automation {t!r}")
            if self._on_fader(node, t):      # 'gainDb' values are dB on the node's gain_db
                for p in norm:
                    p[1] = round(p[1] + node.gain_db, 6)
            lim = _RANGES.get(t)
            if t.startswith('send.'):
                lim = (_MIN_DB, _MAX_DB)
            if lim:
                for p in norm:
                    if not lim[0] <= p[1] <= lim[1]:
                        on = (f" ({p[1] - node.gain_db:g} dB on the gain_db {node.gain_db:g}: 'gainDb' values are "
                              f"relative to it)" if self._on_fader(node, t) else '')
                        raise ComposeError(f"{where} automation {t!r}: value {p[1]:g} at beat {p[0]:g} is outside "
                                           f"{lim[0]:g}..{lim[1]:g}{on}")

            out.append({'target': t, 'points': norm})
        return out

    def _compile_mods(self, node: _Node, chain: list[FX], send_levels: dict, lane_targets: set[str], all_ids,
                      track_ids, edges) -> tuple[list[dict], list[tuple[str, list]]]:
        out: list[dict] = []
        lanes: list[tuple[str, list]] = []
        groups: dict[str, list[int]] = {}
        for i, (target, m, (ws, we), origin) in enumerate(node._mods):
            where = (f"{node.kind} {node.id!r} modulator #{i} ({m.kind} on {target!r}"
                     + (f", placed at {origin}" if origin else '') + ')')
            t = self._resolve_target(node, target, chain, set(send_levels))
            bpb = _tempo.beats_per_bar(self.meter_at(ws if ws is not None else 0.0))   # 'N bars' in the meter there
            d: dict = {'target': t, 'source': m.source_json(bpb, where), 'mode': m.mode}
            for k in ('min', 'max', 'depth'):
                if k in m.mapping:
                    d[k] = round(m.mapping[k], 6)
            if m.curve == 'exp':
                d['curve'] = 'exp'
            module_param = t.startswith('instrument.') or t.startswith('fx.')
            windowed = ws is not None or we is not None
            if 'base' in m.mapping:
                if t in lane_targets:
                    raise ComposeError(f"{where}: base= is only for targets without automation; {t!r} is automated "
                                       f"and its lane is the base the modulator adds to - drop base=")
                d['base'] = round(m.mapping['base'], 6)
            elif t not in lane_targets and (m.mode == 'offset' or (windowed and module_param)):
                b = self._static_value(node, t, chain, send_levels)
                if b is None and m.mode == 'offset':
                    raise ComposeError(f"{where}: depth= moves {t!r} around its current value, but it has no automation "
                                       f"and isn't set explicitly in the {'instrument' if t.startswith('instrument.') else 'fx'} "
                                       f"params; give base= (the centre value) or automate {t!r}")
                if b is not None:
                    d['base'] = round(b, 6)
            if self._on_fader(node, t):      # 'gainDb' values are dB on the node's gain_db
                for k in ('base', 'min', 'max'):
                    if k in d:
                        d[k] = round(d[k] + node.gain_db, 6)
                if m.mode == 'absolute' and m.kind == 'steps':
                    d['source']['values'] = [round(v + node.gain_db, 6) for v in d['source']['values']]
            lim = _RANGES.get(t, (_MIN_DB, _MAX_DB) if t.startswith('send.') else None)
            if lim:
                vals = ([('base', d['base'])] if 'base' in d else [])
                if m.mode == 'absolute':
                    vals += ([('value', v) for v in d['source']['values']] if m.kind == 'steps'
                             else [('min', d['min']), ('max', d['max'])])
                for what, v in vals:
                    if not lim[0] <= v <= lim[1]:
                        raise ComposeError(f"{where}: {what} {v:g} is outside the range {lim[0]:g}..{lim[1]:g} of {t!r}")
            if m.mode == 'absolute' and t in lane_targets and not windowed:
                self.warnings.append(f"{where}: sets {t!r} absolutely for the whole song, so its automation lane is "
                                     f"ignored; use depth= (offset around the lane) or window= to combine them")
            if ws is not None:
                d['startBeat'] = _r6(ws)
            if we is not None:
                d['endBeat'] = _r6(we)
            if m.kind == 'follow':
                if m.node not in all_ids:
                    raise ComposeError(f"{where}: follow({m.node!r}) - there is no track or bus {m.node!r}")
                edges.setdefault((m.node, node.id), 'follow')
            if m.kind == 'envelope' and m.trigger is not None and m.trigger not in track_ids and m.trigger not in self._ghosts:
                raise ComposeError(f"{where}: envelope(trigger={m.trigger!r}) - there is no track {m.trigger!r} "
                                   f"(triggers are tracks: their notes restart the envelope)")
            for field, pts in m.lanes.items():
                lanes.append((f"mod.{i}.{field}", pts))
            groups.setdefault(t, []).append(i)
            out.append(d)
        for t, idx in groups.items():
            ds = [out[i] for i in idx]
            if t in lane_targets or not (t.startswith('instrument.') or t.startswith('fx.')):
                continue
            if all('startBeat' in x or 'endBeat' in x for x in ds) and not any('base' in x for x in ds):
                raise ComposeError(f"{node.kind} {node.id!r}: the modulators on {t!r} only act inside their windows, and "
                                   f"the value outside them is unknown here (not set explicitly in the params); give "
                                   f"base= (the value outside the window), set the param on the sound, or automate {t!r}")
        return out, lanes

    @staticmethod
    def _on_fader(node: _Node, t: str) -> bool:
        """Does the resolved target `t` hold 'gainDb' values (dB relative to node.gain_db)? 'gainDb', and the
        base / min / max lanes of a modulator on 'gainDb'."""
        if not node.gain_db:
            return False
        if t == 'gainDb':
            return True
        if t.startswith('mod.'):
            idx, _, field = t[4:].partition('.')
            return (idx.isdigit() and int(idx) < len(node._mods) and node._mods[int(idx)][0] == 'gainDb'
                    and field in ('base', 'min', 'max'))
        return False

    @staticmethod
    def _static_value(node: _Node, t: str, chain: list[FX], send_levels: dict) -> float | None:
        """The value a target has without automation/modulation, when the compose layer knows it."""
        if t == 'gainDb':
            return 0.0                  # dB on the node's gain_db (compile adds it)
        if t == 'pan':
            return round(node.pan, 4)
        if t.startswith('send.'):
            return send_levels.get(t[5:])
        if t.startswith('instrument.layers.') and isinstance(node, Track) and node.instrument.type == 'stack':
            ref, _, p = t[18:].partition('.')
            L = next((x for x in node.instrument.params['layers'] if x.id == ref), None)
            if L is None:
                return None
            if p in _patches.LAYER_KEYS:
                v = L.params.get(p, _LAYER_DEFAULTS.get(p))
            elif p.startswith('fx.'):
                idx, _, fp = p[3:].partition('.')
                v = L.fx[int(idx)].params.get(fp) if idx.isdigit() and int(idx) < len(L.fx) else None
            else:
                v = L.instrument.params.get(p)
        elif t.startswith('instrument.'):
            v = node.instrument.params.get(t[11:]) if isinstance(node, Track) else None
        else:
            idx, _, p = t[3:].partition('.')
            v = chain[int(idx)].params.get(p)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        return float(v)

    @staticmethod
    def _resolve_target(node: _Node, target: str, chain: list[FX], send_ids: set[str]) -> str:
        where = f"{node.kind} {node.id!r}"
        if target.startswith('mod.'):
            ref, _, field = target[4:].partition('.')
            listing = ', '.join(f"{i}:{m.kind}" + (f"({m.name})" if m.name else '')
                                for i, (_, m, _, _) in enumerate(node._mods)) or 'none'
            if ref.isdigit():
                idx = int(ref)
                if idx >= len(node._mods):
                    raise ComposeError(f"{where}: automation target {target!r}: no modulator #{idx} (modulators: {listing})")
            else:
                hits = [i for i, (_, m, _, _) in enumerate(node._mods) if m.name == ref]
                if not hits:
                    raise ComposeError(f"{where}: automation target {target!r}: no modulator named {ref!r} "
                                       f"(modulators: {listing}; name one with name='{ref}')")
                idx = hits[0]
            f = _modulation.field_name(node._mods[idx][1], field, f"{where}: automation target {target!r}")
            return f"mod.{idx}.{f}"
        if target.startswith('instrument.layers.') and isinstance(node, Track) and node.instrument.type == 'stack':
            # 'instrument.layers.<id or index>.<param>' -> the layer's id; 'fx.<index|name|type>' of the layer -> index
            ref, _, p = target[18:].partition('.')
            layers = node.instrument.params['layers']
            L = layers[_patches._layer_index(layers, ref, f"{where}: automation target {target!r}")]
            if not p:
                raise ComposeError(f"{where}: automation target {target!r} must be 'instrument.layers.<id>.<param>'")
            if p.startswith('fx.'):
                fref, _, fp = p[3:].partition('.')
                i = _patches._fx_index(L.fx, int(fref) if fref.isdigit() else fref,
                                       f"{where}: automation target {target!r} (layer {L.id!r})")
                p = f"fx.{i}.{fp}"
            return f"instrument.layers.{L.id}.{p}"
        if target.startswith('send.'):
            bus = target[5:]
            if bus not in send_ids:
                raise ComposeError(f"{where}: automation target {target!r} but there is no send to {bus!r}; "
                                   f"add one first: .send({bus!r}, -12)")
            return target
        if not target.startswith('fx.'):
            return target
        ref, _, param = target[3:].partition('.')
        listing = ', '.join(f"{i}:{f.type}" + (f"({f.name})" if f.name else '') for i, f in enumerate(chain)) or 'empty'
        if ref.isdigit():
            idx = int(ref)
            if idx >= len(chain):
                raise ComposeError(f"{where}: automation target {target!r}: no fx #{idx} (chain: {listing})")
        else:
            named = [i for i, f in enumerate(chain) if f.name == ref]
            typed = [i for i, f in enumerate(chain) if f.type == ref]
            hits = named or typed
            if not hits:
                raise ComposeError(f"{where}: automation target {target!r}: no fx named or of type {ref!r} (chain: {listing})")
            if len(hits) > 1:
                raise ComposeError(f"{where}: automation target {target!r} is ambiguous ({len(hits)} {ref!r} effects in "
                                   f"chain: {listing}); use the index 'fx.<i>.{param}' or give the fx a name=")
            idx = hits[0]
        return f"fx.{idx}.{param}"

    @staticmethod
    def _check_cycles(edges: dict[tuple[str, str], str]) -> None:
        adj: dict[str, list[str]] = {}
        for (u, v) in edges:
            adj.setdefault(u, []).append(v)
        state: dict[str, int] = {}
        for root in sorted(adj):
            if state.get(root):
                continue
            stack = [(root, iter(adj.get(root, [])))]
            path = [root]
            state[root] = 1
            while stack:
                u, it = stack[-1]
                v = next(it, None)
                if v is None:
                    state[u] = 2
                    stack.pop()
                    path.pop()
                    continue
                if state.get(v) == 1:
                    cyc = path[path.index(v):] + [v]
                    verb = {'output': 'outputs to', 'send': 'sends to', 'sidechain': 'is the sidechain key of',
                            'follow': 'is followed by a modulator of'}
                    how = ', '.join(f"{a} {verb[edges[(a, b)]]} {b}" for a, b in zip(cyc, cyc[1:]))
                    raise ComposeError(f"routing cycle: {' -> '.join(cyc)} ({how}); a signal may not feed itself")
                if not state.get(v):
                    state[v] = 1
                    path.append(v)
                    stack.append((v, iter(adj.get(v, []))))

    # --- output
    def to_json(self) -> str:
        return dumps(self.compile())

    def save(self, path) -> Path:
        """Compile and write the render JSON; returns the path."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding='utf-8')
        return p

    def describe(self) -> str:
        """Human overview: sections, tracks, buses, routing."""
        L = self.length
        tm = self.tempo_map() if not self._tempo_plan.empty() else None
        sec = (lambda b: tm.seconds_at(b)) if tm else (lambda b: b * 60.0 / self.tempo)
        clock = lambda b: f"{int(sec(b) // 60)}:{sec(b) % 60:04.1f}"  # noqa: E731
        bpm = f"{self.tempo:g} BPM" if tm is None else f"{self.tempo:g} BPM (tempo map {tm.min_bpm:g}-{tm.max_bpm:g})"
        grid = self.meter_grid()
        lines = [f"{self.title} - {bpm}, {self.key.name}, {self.time_sig[0]}/{self.time_sig[1]}, "
                 f"{grid.bar_at(L):g} bars = {clock(L)}"]
        for s in self.sections:
            m = '' if s.meter == self.time_sig else f" {s.meter[0]}/{s.meter[1]}"
            tempo = '' if tm is None else f"  {tm.bpm_at(s.start):.0f}-{tm.bpm_at(max(s.start, s.end - 1e-6)):.0f} BPM"
            lines.append(f"  [{clock(s.start)}] {s.name:<12} {s.bars:>4g} bars{m}  beats {s.start:g}-{s.end:g}{tempo}")
        for t in self.tracks.values():
            src = t.patch or t.instrument.type
            fxs = ' > '.join(f.type + (f"<-{f.sidechain}" if f.sidechain else '') for f in t.fx) or '-'
            sends = ', '.join(f"{b} {v:+g}" for b, v in {**t._patch_sends, **t.sends}.items())
            lines.append(f"  track {t.id:<10} {src:<28} {len(t._notes):>5} notes  fx: {fxs}  -> {t.output}"
                         + (f"  sends: {sends}" if sends else '') + ('  [muted]' if t.mute else '') + self._describe_mods(t))
        for b in self.buses.values():
            fxs = ' > '.join(f.type + (f"<-{f.sidechain}" if f.sidechain else '') for f in b.fx) or '-'
            lines.append(f"  bus   {b.id:<10} fx: {fxs}  -> {b.output}" + self._describe_mods(b))
        lines.append(f"  master fx: {' > '.join(f.type for f in self.master.fx) or '-'}" + self._describe_mods(self.master))
        return '\n'.join(lines)

    @staticmethod
    def _describe_mods(node: _Node) -> str:
        if not node._mods:
            return ''
        parts = []
        for target, m, (ws, we), _ in node._mods:
            src = m.kind + (f" {m.source['shape']}" if 'shape' in m.source else '') + (f" <- {m.node}" if m.node else '')
            win = (f" @{(ws or 0.0):g}-" + (f"{we:g}" if we is not None else 'end')) if ws is not None or we is not None else ''
            parts.append(f"{target}~{src}{win}")
        return f"  mods: {', '.join(parts)}"


def dumps(obj) -> str:
    """JSON with one note / automation point per line and small objects inline (diff- and agent-friendly)."""
    def scalar(x):
        return not isinstance(x, (dict, list))

    def enc(o, ind: int) -> str:
        pad = '  ' * ind
        if isinstance(o, dict):
            if not o:
                return '{}'
            flat = json.dumps(o, allow_nan=False)
            if len(flat) <= 100 and not any(isinstance(v, list) and v and not scalar(v[0]) for v in o.values()):
                return flat
            return '{\n' + ',\n'.join(f"{pad}  {json.dumps(k)}: {enc(v, ind + 1)}" for k, v in o.items()) + f"\n{pad}}}"
        if isinstance(o, list):
            if not o:
                return '[]'
            if all(scalar(x) for x in o):
                return json.dumps(o, allow_nan=False)
            return '[\n' + ',\n'.join(f"{pad}  {enc(x, ind + 1)}" for x in o) + f"\n{pad}]"
        return json.dumps(o, allow_nan=False)

    return enc(obj, 0) + '\n'
