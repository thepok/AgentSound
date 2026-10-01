"""Notes, clips and pattern generators.

A Clip is an immutable list of Notes (start, dur, pitch, vel) with a length, all in beats and
relative to the clip start. Every generator here returns a Clip; tracks place clips in the song.

    drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': '..x.'})
    grid('x..x..x.', 'A2', step='1/16')        # pitched rhythm
    arp(prog, 'updown', rate='1/16', octaves=2)
    bassline(prog, 'octave', rate='1/8')       # classic synthwave octave bass
    chords(prog, voicing='smooth', rhythm='x..x..x.')
    Motif('1:1/8 3:1/8 5:1/4 8:1/2', key).sequence(0, -1, -2).clip(octave=5)
    melody(prog, key, rhythm='x.x.x..x', seed=3)
    euclid(5, 16) -> 'x..x..x..x..x...'
"""

from __future__ import annotations

import itertools
import math
import random
import re
import zlib
from typing import NamedTuple

from .theory import (JAZZ_VOICINGS, ComposeError, Chord, Key, Progression, _degree_to_step, _is_int, _register,
                     chord_kind, chord_scale, jazz_voice, jazz_voicings, note)

_EPS = 1e-6


# ------------------------------------------------------------------------------------ helpers

def beats(v) -> float:
    """Length in beats of a number (beats) or a note value: '1/16' = 0.25, '1/8t' = 1/3 (triplet),
    '1/8.' = 0.75 (dotted), '1/2' = 2, '3/8' = 1.5."""
    if isinstance(v, bool):
        raise ComposeError(f"not a duration: {v!r}")
    if isinstance(v, (int, float)):
        if not math.isfinite(v) or v < 0:
            raise ComposeError(f"duration must be a finite number >= 0, got {v!r}")
        return float(v)
    if isinstance(v, str):
        s = v.strip().lower()
        m = re.match(r'^(\d+)/(\d+)([t.]?)$', s)
        if m and int(m.group(2)) > 0:
            val = 4.0 * int(m.group(1)) / int(m.group(2))
            return val * (2.0 / 3.0 if m.group(3) == 't' else 1.5 if m.group(3) == '.' else 1.0)
        try:
            return beats(float(s))
        except ValueError:
            pass
    raise ComposeError(f"not a duration: {v!r}; use beats (0.25) or a note value like '1/16', "
                       f"'1/8t' (triplet), '1/8.' (dotted)")


def dotted(v) -> float:
    """Dotted length in beats: dotted('1/8') == 0.75."""
    return beats(v) * 1.5


def triplet(v) -> float:
    """Triplet length in beats: triplet('1/8') == 1/3."""
    return beats(v) * 2.0 / 3.0


def seed_int(seed) -> int:
    """Stable integer seed from an int or string (never Python's randomized hash())."""
    if _is_int(seed):
        return seed
    return zlib.crc32(str(seed).encode('utf-8'))


def _vel(v) -> int:
    return max(1, min(127, int(round(v))))


# General MIDI drum map (the 'drums' instrument uses these note numbers).
DRUMS = {
    'kick': 36, 'bd': 36, 'rim': 37, 'rimshot': 37, 'rs': 37, 'snare': 38, 'sd': 38, 'sn': 38,
    'clap': 39, 'cp': 39, 'tom_lo': 41, 'tom_low': 41, 'lt': 41, 'hat': 42, 'hh': 42, 'chh': 42,
    'closed_hat': 42, 'ch': 42, 'pedal': 44, 'pedal_hat': 44, 'ph': 44, 'tom_mid': 45, 'mt': 45,
    'open_hat': 46, 'ohh': 46, 'oh': 46, 'tom_hi': 48, 'tom_high': 48, 'ht': 48, 'crash': 49,
    'cr': 49, 'ride': 51, 'rd': 51, 'tamb': 54, 'tambourine': 54, 'cowbell': 56, 'cb': 56,
}


def drum(name) -> int:
    """GM note number of a drum name ('kick' -> 36) or a pitch (int / note name)."""
    if isinstance(name, str) and name.strip().lower() in DRUMS:
        return DRUMS[name.strip().lower()]
    if isinstance(name, str) and name.strip().isdigit():
        name = int(name.strip())
    try:
        return note(name)
    except ComposeError:
        pass
    names = sorted({k for k in DRUMS if len(k) > 3})
    raise ComposeError(f"unknown drum {name!r}; use a GM note number or one of: {', '.join(names)}")


def _pitch(x) -> int:
    return drum(x) if isinstance(x, str) and x.strip().lower() in DRUMS else note(x)


class Note(NamedTuple):
    """One note: start and dur in beats (relative to its clip), MIDI pitch 0..127, velocity 1..127."""
    start: float
    dur: float
    pitch: int
    vel: int = 100


def _as_note(x) -> Note:
    if isinstance(x, dict):
        try:
            x = (x['start'], x['dur'], x['pitch'], x.get('vel', 100))
        except KeyError as e:
            raise ComposeError(f"note dict {x!r} is missing {e}") from None
    if not isinstance(x, (tuple, list)) or len(x) not in (3, 4):
        raise ComposeError(f"not a note: {x!r}; use (start, dur, pitch[, vel]) with pitch as MIDI or 'A4'")
    start, dur, pitch = x[0], x[1], x[2]
    vel = x[3] if len(x) == 4 else 100
    for name, v in (('start', start), ('dur', dur)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ComposeError(f"note {tuple(x)!r}: {name} must be a finite number of beats")
    if dur <= 0:
        raise ComposeError(f"note {tuple(x)!r}: dur must be > 0 beats")
    if isinstance(vel, bool) or not isinstance(vel, (int, float)) or not 1 <= vel <= 127:
        raise ComposeError(f"note {tuple(x)!r}: velocity must be 1..127")
    return Note(float(start), float(dur), _pitch(pitch), int(round(vel)))


# --------------------------------------------------------------------------------------- clip

class Clip:
    """Immutable notes + length (beats). Combine: a + b (sequence), a | b (layer), a * 4 (repeat).

    Transforms return new clips: shift, transpose, octave, transpose_scale, slice, repeat, loop,
    stretch, reverse, velocity, with_vel, gate, legato, only, without, filter, map, fit,
    humanize, swing, groove, crescendo, accent.
    MIDI effects (midifx.py): arpeggiate, strum, ratchet, echo, harmonize, chordify, quantize,
    scale_quantize, chance, thin, fold, octave_double, vel_random, vel_pattern, staccato, retrograde, invert."""

    __slots__ = ('_notes', 'length')

    def __init__(self, notes=(), length=None):
        ns = [_as_note(n) for n in notes]
        ns.sort(key=lambda n: (n.start, n.pitch))
        self._notes = tuple(ns)
        if length is None:
            end = max((n.start + n.dur for n in ns), default=0.0)
            length = float(math.ceil(end - _EPS)) if end > 0 else 0.0
        self.length = beats(length)

    @classmethod
    def _raw(cls, notes, length) -> 'Clip':
        c = cls.__new__(cls)
        c._notes = tuple(sorted(notes, key=lambda n: (n.start, n.pitch)))
        c.length = float(length)
        return c

    @staticmethod
    def rest(length) -> 'Clip':
        """An empty clip of `length` beats (use in sequences: a + Clip.rest(4) + b)."""
        return Clip._raw((), beats(length))

    # --- container protocol
    @property
    def notes(self) -> tuple[Note, ...]:
        return self._notes

    def __iter__(self):
        return iter(self._notes)

    def __len__(self) -> int:
        return len(self._notes)

    def __getitem__(self, i):
        return self._notes[i]

    def __eq__(self, other) -> bool:
        return isinstance(other, Clip) and self._notes == other._notes and self.length == other.length

    __hash__ = None

    def __repr__(self) -> str:
        return f"Clip({len(self._notes)} notes, length={self.length:g})"

    @property
    def end(self) -> float:
        """Beat where the last note ends (may exceed length for ringing notes)."""
        return max((n.start + n.dur for n in self._notes), default=0.0)

    @property
    def pitches(self) -> list[int]:
        return sorted({n.pitch for n in self._notes})

    # --- combination
    def __add__(self, other) -> 'Clip':
        o = as_clip(other)
        return Clip._raw(self._notes + tuple(n._replace(start=n.start + self.length) for n in o),
                         self.length + o.length)

    def __or__(self, other) -> 'Clip':
        o = as_clip(other)
        return Clip._raw(self._notes + o._notes, max(self.length, o.length))

    def __mul__(self, n: int) -> 'Clip':
        return self.repeat(n)

    __rmul__ = __mul__

    # --- time
    def shift(self, by: float) -> 'Clip':
        """Move every note by `by` beats (length unchanged)."""
        return Clip._raw([n._replace(start=n.start + by) for n in self._notes], self.length)

    def repeat(self, n: int) -> 'Clip':
        if not _is_int(n) or n < 0:
            raise ComposeError(f"repeat count must be an int >= 0, got {n!r}")
        L = self.length
        if L <= 0 and n > 1:
            raise ComposeError("can't repeat a clip of length 0; give it a length: Clip(notes, length=4)")
        return Clip._raw([x._replace(start=x.start + k * L) for k in range(n) for x in self._notes], L * n)

    def loop(self, length) -> 'Clip':
        """Repeat to fill exactly `length` beats; notes are cut at the end."""
        total = beats(length)
        L = self.length
        if L <= 0:
            raise ComposeError("can't loop a clip of length 0; give it a length: Clip(notes, length=4)")
        out = []
        k = 0
        while k * L < total - _EPS:
            for x in self._notes:
                s = x.start + k * L
                if s < total - _EPS:
                    out.append(x._replace(start=s, dur=min(x.dur, total - s)))
            k += 1
        return Clip._raw(out, total)

    def slice(self, start: float, end: float | None = None) -> 'Clip':
        """Notes starting in [start, end), moved to start at 0 and cut at the slice end."""
        end = self.length if end is None else end
        if end <= start:
            raise ComposeError(f"slice end {end} must be after start {start}")
        out = [x._replace(start=x.start - start, dur=min(x.dur, end - x.start))
               for x in self._notes if start - _EPS <= x.start < end - _EPS]
        return Clip._raw(out, end - start)

    def stretch(self, factor: float) -> 'Clip':
        """Scale time (2 = half speed, 0.5 = double speed)."""
        if factor <= 0:
            raise ComposeError(f"stretch factor must be > 0, got {factor}")
        return Clip._raw([x._replace(start=x.start * factor, dur=x.dur * factor) for x in self._notes],
                         self.length * factor)

    def reverse(self) -> 'Clip':
        """Retrograde: play the clip backwards in time (a note ringing past the clip end is cut there)."""
        L = self.length
        out = []
        for x in self._notes:
            end = min(x.start + x.dur, L)
            if end > x.start + _EPS:
                out.append(x._replace(start=L - end, dur=end - x.start))
        return Clip._raw(out, L)

    def with_length(self, length) -> 'Clip':
        return Clip._raw(self._notes, beats(length))

    def window(self, start: float = 0.0, end: float | None = None) -> 'Clip':
        """The notes starting in [start, end) at their own positions (unlike slice(): nothing moves or is cut; the
        length stays): bass.window(16) = the second half of a 32-beat line, still at 16."""
        a, b = float(start), math.inf if end is None else float(end)
        if b <= a:
            raise ComposeError(f"window end {end} must be after start {start}")
        return Clip._raw([x for x in self._notes if a - _EPS <= x.start < b - _EPS], self.length)

    # --- pitch
    def transpose(self, semitones: int) -> 'Clip':
        out = []
        for x in self._notes:
            p = x.pitch + int(semitones)
            if not 0 <= p <= 127:
                raise ComposeError(f"transposing pitch {x.pitch} by {semitones} leaves the MIDI range 0..127")
            out.append(x._replace(pitch=p))
        return Clip._raw(out, self.length)

    def octave(self, n: int = 1) -> 'Clip':
        return self.transpose(12 * n)

    def transpose_scale(self, steps: int, key) -> 'Clip':
        """Move by scale steps inside `key` (diatonic transposition; -2 = a third below).
        Harmony line: lead | lead.transpose_scale(-2, key)."""
        k = Key(key)
        return Clip._raw([x._replace(pitch=note(k.transpose(x.pitch, steps))) for x in self._notes], self.length)

    def fit(self, prog, key=None, strong: float = 1.0) -> 'Clip':
        """Make a line consonant with a progression: notes on strong positions (multiples of `strong`
        beats) or at least `strong` long move to the nearest chord tone; other notes snap to `key`."""
        p = prog if isinstance(prog, Progression) else Progression(prog, key=key)
        k = None if key is None else Key(key)
        out = []
        for x in self._notes:
            ch = p.at(x.start)
            pos = x.start / strong
            if ch is not None and (abs(pos - round(pos)) < _EPS or x.dur >= strong - _EPS):
                pcs = ch.pcs
                best = min((x.pitch + d for d in range(-6, 7) if (x.pitch + d) % 12 in pcs),
                           key=lambda q: (abs(q - x.pitch), q))
                out.append(x._replace(pitch=best))
            elif k is not None:
                out.append(x._replace(pitch=k.snap(x.pitch)))
            else:
                out.append(x)
        return Clip._raw(out, self.length)

    # --- dynamics / articulation
    def velocity(self, factor: float) -> 'Clip':
        """Scale velocities (clamped to 1..127)."""
        return Clip._raw([x._replace(vel=_vel(x.vel * factor)) for x in self._notes], self.length)

    def with_vel(self, vel: int) -> 'Clip':
        return Clip._raw([x._replace(vel=_vel(vel)) for x in self._notes], self.length)

    def vel_add(self, dv: float) -> 'Clip':
        """Add `dv` to every velocity (clamped to 1..127): line.vel_add(-8) for a softer double."""
        return Clip._raw([x._replace(vel=_vel(x.vel + dv)) for x in self._notes], self.length)

    def arch(self, bars: float = 4, depth: float = 0.3, *, beats_per_bar: float = 4.0, power: float = 0.8,
             lo: int = 30, hi: int = 120) -> 'Clip':
        """A phrase arch on the velocities, every `bars` bars from the clip start: x (1 - depth/2 + depth *
        sin(pi * x^power)), x = the position in the arch (0..1) - rising to ~60 % of it, relaxing after; clamped to
        lo..hi. Played chords / pads that breathe in 4-bar phrases: pad.play(prog.block().arch(4, 0.3), verse)."""
        span = float(bars) * float(beats_per_bar)
        if span <= 0 or not 0 <= depth <= 2:
            raise ComposeError(f"arch(bars={bars}, depth={depth}): bars must be > 0 and depth 0..2")
        return Clip._raw([x._replace(vel=max(lo, min(hi, round(
            x.vel * (1 - depth / 2 + depth * math.sin(math.pi * ((x.start % span) / span) ** power))))))
            for x in self._notes], self.length)

    def roll(self, ms=(8.0, 22.0), *, seed=0, bpm: float = 120.0, direction: str = 'up') -> 'Clip':
        """A pianist's hands never land flat: every chord rolled (strum()) by `ms` milliseconds - a number, or
        (lo, hi) for a seeded speed between them (seed: an int / str, or a random.Random to draw from)."""
        if isinstance(ms, (tuple, list)):
            if len(ms) != 2:
                raise ComposeError(f"roll ms must be a number or (lo, hi), got {ms!r}")
            rng = seed if isinstance(seed, random.Random) else random.Random(seed_int(seed))
            ms = rng.uniform(float(ms[0]), float(ms[1]))
        return self.strum(ms=ms, direction=direction, bpm=bpm)

    def gate(self, factor: float) -> 'Clip':
        """Scale note durations (0.5 = staccato)."""
        return Clip._raw([x._replace(dur=max(x.dur * factor, 1e-3)) for x in self._notes], self.length)

    def legato(self, overlap: float = 0.02) -> 'Clip':
        """Extend every note to the next onset + `overlap` beats (default 0.02: the notes overlap slightly, so
        mono / legato synths glide instead of retriggering). The engine orders note-ons before note-offs at
        the same sample, so overlap=0 (notes touching) also plays legato."""
        starts = sorted({x.start for x in self._notes})
        nxt = {s: (starts[i + 1] if i + 1 < len(starts) else max(self.length, s + 1e-3)) for i, s in enumerate(starts)}
        return Clip._raw([x._replace(dur=max(nxt[x.start] - x.start + overlap, 1e-3)) for x in self._notes],
                         self.length)

    # --- selection
    def only(self, *pitches) -> 'Clip':
        """Keep only these pitches (drum names ok): beat.only('kick')."""
        ps = {_pitch(p) for p in pitches}
        return Clip._raw([x for x in self._notes if x.pitch in ps], self.length)

    def without(self, *pitches) -> 'Clip':
        ps = {_pitch(p) for p in pitches}
        return Clip._raw([x for x in self._notes if x.pitch not in ps], self.length)

    def filter(self, fn) -> 'Clip':
        return Clip._raw([x for x in self._notes if fn(x)], self.length)

    def map(self, fn) -> 'Clip':
        """fn(Note) -> Note | (start, dur, pitch, vel) | None (drop)."""
        out = []
        for x in self._notes:
            y = fn(x)
            if y is not None:
                out.append(_as_note(y))
        return Clip(out, self.length)

    # --- feel (see humanize.py)
    def humanize(self, timing_ms: float = 4.0, vel: float = 6, bpm: float = 120.0, seed=0) -> 'Clip':
        from .humanize import humanize
        return humanize(self, timing_ms=timing_ms, vel=vel, bpm=bpm, seed=seed)

    def swing(self, amount: float = 0.58, grid='1/16') -> 'Clip':
        from .humanize import swing
        return swing(self, amount, grid)

    def groove(self, name, bpm: float = 120.0, drums: bool = False) -> 'Clip':
        from .humanize import groove
        return groove(self, name, bpm=bpm, drums=drums)

    def crescendo(self, start: float = 0.5, end: float = 1.0, curve: float = 1.0) -> 'Clip':
        from .humanize import crescendo
        return crescendo(self, start, end, curve=curve)

    def accent(self, every: float = 1.0, amount: float = 1.2, offset: float = 0.0) -> 'Clip':
        from .humanize import accent
        return accent(self, every=every, amount=amount, offset=offset)

    # --- MIDI effects (see midifx.py for the full documentation)
    def arpeggiate(self, mode: str = 'up', rate='1/16', octaves: int = 1, gate: float = 0.7, pattern=None,
                   latch: bool = False, vel: float | None = None, accent=None, retrigger: bool = True,
                   seed=0) -> 'Clip':
        """Arpeggiate the notes held at each moment (chords, pads, held notes) like a hardware arp:
        modes up down updown downup converge diverge pinky thumb random order chord pattern;
        pattern=[0, 2, 1, None] (indices) or a rhythm 'x.xx x_x.'; retrigger restarts on chord changes."""
        from .midifx import arpeggiate
        return arpeggiate(self, mode, rate, octaves, gate, pattern, latch, vel, accent, retrigger, seed)

    def strum(self, ms: float = 30.0, direction: str = 'down', vel_decay: float = 0.0, *, beats=None,
              bpm: float = 120.0) -> 'Clip':
        """Guitar strum: offset the notes of every chord by `ms` (at `bpm`; or beats=) each, keeping their ends.
        direction down | up | alternate."""
        from .midifx import strum
        return strum(self, ms, direction, vel_decay, beats=beats, bpm=bpm)

    def ratchet(self, n: int = 2, where=None, gate: float = 0.9, vel_decay: float = 0.0) -> 'Clip':
        """Split notes into n repeats (rolls); where = predicate, onset pattern '..x.' (digits = counts) or pitches."""
        from .midifx import ratchet
        return ratchet(self, n, where, gate, vel_decay)

    def echo(self, times: int = 3, delay='1/8.', decay: float = 0.6, transpose: int = 0, gate: float | None = None,
             key=None, wrap: bool = False) -> 'Clip':
        """MIDI delay: `times` repeats `delay` apart, velocity x decay each, optional transpose per repeat
        (semitones, or scale steps with key=)."""
        from .midifx import echo
        return echo(self, times, delay, decay, transpose, gate, key, wrap)

    def harmonize(self, interval=None, *, key=None, steps=None, semitones=None, vel: float = 0.8, keep: bool = True,
                  fit=None, strong: float = 1.0, fold=None) -> 'Clip':
        """Parallel voices: harmonize('3rd', key=k) (diatonic), ['3rd', '5th'], '-6th', steps=[2], semitones=[12];
        keep=False only the voices (a harmony part), fit=prog chord-tone aware, fold=(lo, hi) a register."""
        from .midifx import harmonize
        return harmonize(self, interval, key=key, steps=steps, semitones=semitones, vel=vel, keep=keep, fit=fit,
                         strong=strong, fold=fold)

    def chordify(self, shape='triad', key=None, voicing: str = 'close', vel: float = 1.0) -> 'Clip':
        """Every note becomes a chord rooted on it: triad 7th 9th 6th (diatonic, need key=), sus2 sus4 add9
        open power, a quality 'm7' or semitones (0, 3, 7); voicing close | open | spread."""
        from .midifx import chordify
        return chordify(self, shape, key, voicing, vel)

    def quantize(self, grid='1/16', strength: float = 1.0, ends: bool = False, swing: float = 0.0) -> 'Clip':
        """Pull note starts (ends=True: and ends) to the grid by `strength`; swing 0 or 0.5..0.8."""
        from .midifx import quantize
        return quantize(self, grid, strength, ends, swing)

    def scale_quantize(self, key, direction: str = 'nearest') -> 'Clip':
        """Snap pitches into the key's scale (nearest | up | down)."""
        from .midifx import scale_quantize
        return scale_quantize(self, key, direction)

    def chance(self, p: float = 0.8, seed=0) -> 'Clip':
        """Keep each note with probability p (seeded)."""
        from .midifx import chance
        return chance(self, p, seed)

    def thin(self, every: int = 2, offset: int = 0) -> 'Clip':
        """Keep every n-th onset (chords stay whole), starting at onset `offset`."""
        from .midifx import thin
        return thin(self, every, offset)

    def fold(self, low, high) -> 'Clip':
        """Octave-fold every pitch into [low, high] (a register at least 11 semitones wide)."""
        from .midifx import fold
        return fold(self, low, high)

    def octave_double(self, interval=12, vel: float = 0.8) -> 'Clip':
        """Add octave copies: +12, -12 (sub), 24 or a list; vel = factor of the copies."""
        from .midifx import octave_double
        return octave_double(self, interval, vel)

    def vel_random(self, amount: float = 10, seed=0) -> 'Clip':
        """Uniform random velocity offsets in +-amount (seeded)."""
        from .midifx import vel_random
        return vel_random(self, amount, seed)

    def vel_pattern(self, levels, grid=None) -> 'Clip':
        """Cycle velocity factors [1.2, 0.8, 1, 0.8] (or absolute velocities [120, 70, ...]) over the onsets,
        or over grid positions with grid='1/16'."""
        from .midifx import vel_pattern
        return vel_pattern(self, levels, grid)

    def staccato(self, length='1/16') -> 'Clip':
        """Cap every note at `length` beats."""
        from .midifx import staccato
        return staccato(self, length)

    def retrograde(self, rhythm: bool = True) -> 'Clip':
        """Backwards: rhythm=True mirrors time (= reverse()); rhythm=False reverses only the pitch order."""
        from .midifx import retrograde
        return retrograde(self, rhythm)

    def invert(self, pivot=None, key=None) -> 'Clip':
        """Mirror pitches around `pivot` (default the first note); diatonic in scale steps with key=."""
        from .midifx import invert
        return invert(self, pivot, key)


def as_clip(x, length=None) -> Clip:
    """Anything playable -> Clip: Clip, Progression (block chords), Motif, Chord, Note, list of notes."""
    if isinstance(x, Clip):
        return x
    if isinstance(x, Progression):
        return chords(x)
    if isinstance(x, Motif):
        return x.clip()
    if isinstance(x, Chord):
        return chords(Progression([x]))
    if isinstance(x, Note):
        return Clip([x], length)
    if isinstance(x, (list, tuple)):
        return Clip(x, length)
    raise ComposeError(f"can't play {type(x).__name__} {x!r}: expected a Clip, Progression, Motif, Chord "
                       f"or a list of (start, dur, pitch, vel) notes")


# --------------------------------------------------------------------------------------- grids

_HIT_LEVEL = {'X': 118, 'x': 100, 'o': 62}
_GRID_CHARS = set('Xxo123456789._-')


def _cells(pattern: str, what: str = 'pattern') -> list[str]:
    if not isinstance(pattern, str):
        raise ComposeError(f"{what} must be a string like 'x...x...', got {pattern!r}")
    cells = [c for c in pattern if c not in ' |\t\n']
    bad = [c for c in cells if c not in _GRID_CHARS]
    if bad:
        raise ComposeError(f"{what} {pattern!r} has invalid character {bad[0]!r}; use X (accent), x (hit), "
                           f"o (ghost), 1-9 (velocity level), '.' or '-' (rest), '_' (tie/hold), ' ' and '|' ignored")
    if not cells:
        raise ComposeError(f"{what} is empty")
    return cells


def _events(cells: list[str], total: int) -> list[tuple[int, int, str]]:
    """(step, n_steps, level_char) for hits over `total` steps, cells tiled; '_' extends the previous hit."""
    out: list[list] = []
    for i in range(total):
        c = cells[i % len(cells)]
        if c in '._-':
            if c == '_' and out and out[-1][0] + out[-1][1] == i:
                out[-1][1] += 1
            continue
        out.append([i, 1, c])
    return [tuple(e) for e in out]


def _level_scale(vel, what: str) -> float:
    """A grid's `vel`: a percentage of the written levels (100 = as written), 2..200. Strict: a 0..1 ratio (the
    scale track.play / loop(vel=0.8) take) would silently play every hit at velocity 1."""
    if isinstance(vel, bool) or not isinstance(vel, (int, float)) or not math.isfinite(vel):
        raise ComposeError(f"{what} vel must be a number (100 = as written), got {vel!r}")
    if not 2 <= vel <= 200:
        hint = (f"; it looks like a 0..1 ratio - write vel={vel * 100:g} (track.play / loop(vel=...) are the ones "
                f"that take a ratio)" if 0 < vel < 2 else '')
        raise ComposeError(f"{what} vel is a percentage of the written levels (100 = as written, 2..200), got "
                           f"{vel:g}{hint}")
    return float(vel)


def _level(c: str, base: float) -> int:
    """Velocity of a grid cell; `base` scales every level (100 = as written, digits included)."""
    raw = int(c) * 14 if c.isdigit() else _HIT_LEVEL[c]
    return _vel(raw * base / 100.0)


def _drum_voices(spec) -> list[tuple[int, list[str]]]:
    if isinstance(spec, dict):
        items = list(spec.items())
    elif isinstance(spec, str):
        items = []
        for line in spec.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^([A-Za-z0-9_#]+)\s*[:=]?\s+(.*)$|^([A-Za-z0-9_#]+)\s*[:=]\s*(.*)$', line)
            if not m:
                raise ComposeError(f"drum line {line!r} must look like 'kick: x...x...'")
            name, pat = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            items.append((name, pat))
        if not items:
            raise ComposeError("empty drum pattern")
    elif isinstance(spec, (list, tuple)):
        items = list(spec)
    else:
        raise ComposeError(f"drum pattern must be a dict {{'kick': 'x...'}} or 'kick: x...' lines, got {spec!r}")
    out = []
    for name, pat in items:
        out.append((drum(name), _cells(pat, f"drum pattern for {name!r}")))
    return out


def drums(pattern, step='1/16', bars: float | None = None, vel: float = 100, beats_per_bar: float = 4) -> Clip:
    """Multi-voice drum grid -> Clip. One character per step (default a 16th):
    X accent, x hit, o ghost, 1-9 explicit level, '.'/'-' rest, '_' hold, spaces and '|' ignored.

        drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': '..x.'})
        drums('''kick:  x...x...x...x...
                 clap:  ....X.......X...
                 ohh:   ..x...x...x...x.''')

    Voices may be drum names (kick snare clap rim hat pedal ohh tom_lo tom_mid tom_hi crash ride
    tamb cowbell) or MIDI numbers. Shorter voices repeat to the longest one (a 4-step hat pattern
    fills the bar); bars= forces the clip length. `vel` scales all levels: a percentage, 100 = as written, 2..200
    (a 0..1 ratio is an error: that is track.play / loop(vel=...))."""
    vel = _level_scale(vel, 'drums()')
    voices = _drum_voices(pattern)
    st = beats(step)
    if st <= 0:
        raise ComposeError("step must be > 0")
    total = max(len(c) for _, c in voices) if bars is None else int(round(bars * beats_per_bar / st))
    notes = [Note(i * st, n * st, p, _level(c, vel)) for p, cells in voices for i, n, c in _events(cells, total)]
    return Clip._raw(notes, total * st)


def grid(pattern: str, pitch, step='1/16', vel: float = 96, gate: float = 0.9, length=None) -> Clip:
    """Pitched rhythm: one character per step (like drums()), '_' holds the note.
    `pitch` may be a list (chord stab). grid('x.x_x...', 'A2'). `vel` scales the levels like drums() (100 = as
    written: x = 100, X = 118, o = 62)."""
    vel = _level_scale(vel, 'grid()')
    cells = _cells(pattern)
    st = beats(step)
    ps = [_pitch(p) for p in pitch] if isinstance(pitch, (list, tuple)) else [_pitch(pitch)]
    total = len(cells) if length is None else int(round(beats(length) / st))
    notes = []
    for i, n, c in _events(cells, total):
        v = _level(c, vel)
        notes.extend(Note(i * st, n * st * gate, p, v) for p in ps)
    return Clip._raw(notes, total * st)


def euclid(k: int, n: int, rotate: int = 0, hit: str = 'x', rest: str = '.') -> str:
    """Euclidean rhythm (Bjorklund) as a grid string: euclid(3, 8) == 'x..x..x.'.
    rotate shifts the pattern left by that many steps. Feed it to drums()/grid()."""
    if not (_is_int(k) and _is_int(n)) or n <= 0 or not 0 <= k <= n:
        raise ComposeError(f"euclid needs 0 <= k <= n and n > 0, got k={k!r}, n={n!r}")
    if k == 0:
        bits = [0] * n
    else:
        a: list[list[int]] = [[1] for _ in range(k)]
        b: list[list[int]] = [[0] for _ in range(n - k)]
        while len(b) > 1:
            m = min(len(a), len(b))
            a, b = [a[i] + b[i] for i in range(m)], (a[m:] if len(a) > m else b[m:])
        bits = [x for grp in a + b for x in grp]
    r = rotate % n
    bits = bits[r:] + bits[:r]
    return ''.join(hit if x else rest for x in bits)


# ------------------------------------------------------------------------- chords / arp / bass

def _as_prog(src, key=None, length=4.0) -> Progression:
    if isinstance(src, Progression):
        return src
    if isinstance(src, Chord):
        return Progression([(src, beats(length) / 4.0)], key=key)
    if isinstance(src, str):
        toks = src.replace('|', ' ').split()
        if len(toks) == 1 and ':' not in toks[0]:
            return Progression([(toks[0], beats(length) / 4.0)], key=key)
        return Progression(src, key=key)
    raise ComposeError(f"expected a Progression, chord symbol string or Chord, got {src!r}")


def _segments(src, key, length, register, voices) -> tuple[list[tuple[float, float, list[int]]], float]:
    """[(start, dur, tones)] and total length, for arps over progressions, chords or pitch lists."""
    if isinstance(src, (list, tuple)) and src and not isinstance(src[0], (tuple, list, Chord)):
        tones = sorted({_pitch(p) for p in src})
        L = beats(length)
        return [(0.0, L, tones)], L
    p = _as_prog(src, key, length)
    return [(s, d, v) for s, d, v in p.voiced('smooth', register=register, voices=voices)], p.length


ARP_MODES = ('up', 'down', 'updown', 'downup', 'converge', 'diverge', 'pinky', 'thumb', 'random')


def _arp_order(t: list[int], mode: str) -> list[int]:
    if mode == 'up':
        return t
    if mode == 'down':
        return t[::-1]
    if mode == 'updown':
        return t + t[-2:0:-1] if len(t) > 2 else t
    if mode == 'downup':
        d = t[::-1]
        return d + d[-2:0:-1] if len(d) > 2 else d
    if mode in ('converge', 'diverge'):
        lo, hi, out = 0, len(t) - 1, []
        while lo <= hi:
            out.append(t[lo])
            if hi != lo:
                out.append(t[hi])
            lo, hi = lo + 1, hi - 1
        return out if mode == 'converge' else out[::-1]
    if mode == 'pinky':
        return [x for p in t[:-1] for x in (p, t[-1])] or t
    if mode == 'thumb':
        return [x for p in t[1:] for x in (t[0], p)] or t
    raise ComposeError(f"unknown arp mode {mode!r}; use one of {', '.join(ARP_MODES)} or pattern=[0, 2, 1, 3]")


def arp(chords, mode: str = 'up', rate='1/16', octaves: int = 1, gate: float = 0.6, vel: float = 92,
        accent: float = 1.15, register=(57, 76), voices: int | None = None, pattern=None, seed=0,
        restart: bool = True, length=4.0, key=None) -> Clip:
    """Arpeggiate a progression (or one chord / a list of pitches) -> Clip.

    mode: up down updown downup converge diverge pinky (top-note pedal) thumb (bottom pedal) random.
    pattern: explicit step order as indices into the (octave-extended) sorted chord tones, e.g.
      [0, 2, 1, 3]; negative / out-of-range indices wrap by octaves; None = rest step.
    Chord tones are voice-led inside `register` so the arp moves smoothly between chords; octaves=2
    adds the same tones an octave up. rate = step length, gate = note length / step, accent = velocity
    factor on the beat. restart=False keeps the step counter running across chord changes."""
    segs, total = _segments(chords, key, length, register, voices)
    r = beats(rate)
    if r <= 0:
        raise ComposeError("arp rate must be > 0")
    if not _is_int(octaves) or octaves < 1:
        raise ComposeError(f"octaves must be an int >= 1, got {octaves!r}")
    if pattern is None and mode != 'random':
        _arp_order([0, 1, 2], mode)  # validate mode early
    rng = random.Random(seed_int(seed))
    notes, counter, last = [], 0, None
    for start, dur, tones in segs:
        ext = sorted({t + 12 * o for o in range(octaves) for t in tones})
        order = _arp_order(ext, mode) if pattern is None and mode != 'random' else ext
        if restart:
            counter = 0
        for k in range(int(math.floor(dur / r + _EPS))):
            t = start + k * r
            if pattern is not None:
                idx = pattern[counter % len(pattern)]
                counter += 1
                if idx is None:
                    continue
                o, i = divmod(int(idx), len(ext))
                p = ext[i] + 12 * o
            elif mode == 'random':
                choices = [x for x in ext if x != last] or ext
                p = rng.choice(choices)
            else:
                p = order[counter % len(order)]
                counter += 1
            last = p
            if 0 <= p <= 127:
                v = vel * (accent if abs(t - round(t)) < _EPS else 1.0)
                notes.append(Note(t, r * gate, p, _vel(v)))
    return Clip._raw(notes, total)


BASS_STYLES = ('root', 'pulse', 'octave', 'fifth', 'offbeat', 'gallop', 'walk', 'arp')
_BASS_DEFAULTS = {'root': (None, 0.95), 'pulse': ('1/8', 0.7), 'octave': ('1/8', 0.6), 'fifth': ('1/8', 0.7),
                  'offbeat': ('1/8', 0.55), 'gallop': ('1/16', 0.8), 'walk': ('1/4', 0.9), 'arp': ('1/8', 0.7)}


def _tones(ch: Chord, root: int) -> dict[str, int]:
    iv = set(ch.intervals)
    third = 3 if 3 in iv else 4 if 4 in iv else 5 if 5 in iv else 2 if 2 in iv else 4
    fifth = 7 if 7 in iv else 6 if 6 in iv else 8 if 8 in iv else 7
    seventh = 10 if 10 in iv else 11 if 11 in iv else 9 if 9 in iv else 12
    return {'r': root, 'x': root, 'o': root + 12, 'f': root + fifth, 't': root + third, 's': root + seventh,
            'l': root - 12}


def _walk(ch: Chord, root: int, nxt: int, n: int, lo: int, key=None) -> list[int]:
    """Walking line of n notes over one chord: root first, a chromatic approach to `nxt` (the next
    chord's bass) last, and in between the smoothest path through chord tones (scale tones of `key`,
    else of the chord's pentatonic, as passing notes), preferring steps and thirds over leaps, repeats and back-and-forth."""
    if n <= 1:
        return [root] * n
    band = range(max(lo - 2, min(root, nxt) - 7), max(root, nxt) + 10)
    tones = {p for p in band if p % 12 in ch.pcs}
    if key is not None:
        scale_pcs = Key(key).pcs
    else:  # no key: passing tones from the chord's own pentatonic
        scale_pcs = frozenset((ch.root + i) % 12 for i in ((0, 3, 5, 7, 10) if ch.is_minor else (0, 2, 4, 7, 9)))
    cands = sorted(tones | {p for p in band if p % 12 in scale_pcs})

    def step(a: int, b: int) -> float:
        d = abs(a - b)
        return {0: 6.0, 1: 0.8, 2: 0.6, 3: 1.0, 4: 1.2, 5: 1.8}.get(d, 1.0 + 0.5 * d) + (4.0 if d > 7 else 0.0)

    # Dynamic programming over the current pitch (the path carries the history for the penalties).
    states: dict[int, tuple[float, list[int]]] = {root: (0.0, [root])}
    for i in range(1, n):
        last = i == n - 1
        new: dict[int, tuple[float, list[int]]] = {}
        for cur, (c, path) in states.items():
            for q in ((nxt - 1, nxt + 1) if last else cands):
                cc = c + step(cur, q) + (0.0 if last or q in tones else 0.7)
                if len(path) > 1 and q == path[-2]:
                    cc += 1.0                      # no A-B-A wobble
                if q in path:
                    cc += 0.5                      # prefer new pitches
                if q not in new or (cc, path) < (new[q][0] - 1e-9, new[q][1]):
                    new[q] = (cc, path + [q])
        states = new
    return min(states.values())[1]


def bassline(chords, style: str = 'octave', rate=None, low='E1', vel: float = 100, gate: float | None = None,
             accent: float = 1.1, pattern: str | None = None, key=None, length=4.0) -> Clip:
    """Bassline over a progression -> Clip. The bass note is each chord's slash bass or root, placed in
    the octave starting at `low` (default E1, so roots land between E1 and D#2).

    styles: root (one held note per chord), pulse (repeated root), octave (root/octave alternating -
      the classic synthwave bass, try rate='1/16'), fifth (root/fifth), offbeat (off-beat 8ths),
      gallop (8th + two 16ths per beat), walk (quarter-note walk with chromatic approach), arp.
    pattern: custom per-step string (overrides style), one char per `rate` step, restarted on every
      chord: r/x root, o octave up, l octave down, f fifth, t third, s seventh, UPPERCASE = accent,
      '_' hold, '.'/'-' rest. e.g. bassline(prog, pattern='r.ro r.ro', rate='1/16')."""
    p = _as_prog(chords, key, length)
    if pattern is None and style not in _BASS_DEFAULTS:
        raise ComposeError(f"unknown bass style {style!r}; use one of {', '.join(BASS_STYLES)} or pattern='r.ro'")
    d_rate, d_gate = _BASS_DEFAULTS.get(style, ('1/8', 0.7)) if pattern is None else ('1/8', 0.7)
    r = beats(rate if rate is not None else (d_rate or 1.0))
    g = d_gate if gate is None else gate
    lo = note(low)
    segs = [(s, d, c) for s, d, c in p if c is not None]
    notes: list[Note] = []

    def add(t, dur, pitch, v):
        if 0 <= pitch <= 127:
            notes.append(Note(t, dur, pitch, _vel(v * (accent if abs(t - round(t)) < _EPS else 1.0))))

    for si, (start, dur, ch) in enumerate(segs):
        root = ch.bass_note(lo)
        tones = _tones(ch, root)
        n = max(1, int(math.floor(dur / r + _EPS)))
        if pattern is not None:
            cells = [c for c in pattern if c not in ' |']
            for c in cells:
                if c.lower() not in 'rxoftsl' and c not in '._-':
                    raise ComposeError(f"bass pattern {pattern!r}: invalid {c!r}; use r o l f t s x, '_' hold, '.' rest")
            ev: list[list] = []
            for k in range(n):
                c = cells[k % len(cells)]
                if c == '_' and ev and ev[-1][0] + ev[-1][1] == k:
                    ev[-1][1] += 1
                elif c not in '._-':
                    ev.append([k, 1, c])
            for k, m, c in ev:
                add(start + k * r, m * r * g, tones[c.lower()], vel * (1.2 if c.isupper() else 1.0))
        elif style == 'root':
            add(start, dur * g, root, vel)
        elif style == 'gallop':
            for b in range(int(math.floor(dur + _EPS))):
                for off, ln in ((0.0, 0.5), (0.5, 0.25), (0.75, 0.25)):
                    add(start + b + off, ln * g, root, vel * (1.0 if off == 0 else 0.85))
        elif style == 'walk':
            nxt = segs[si + 1][2].bass_note(lo) if si + 1 < len(segs) else root
            line = _walk(ch, root, nxt, n, lo, key if key is not None else p.key)
            for k, pitch in enumerate(line):
                add(start + k * r, r * g, pitch, vel * (1.0 if k == 0 else 0.9))
        else:
            arp_seq = [tones['r'], tones['t'], tones['f'], tones['o']]
            for k in range(n):
                t = start + k * r
                if style == 'pulse':
                    pitch = root
                elif style == 'octave':
                    pitch = root if k % 2 == 0 else root + 12
                elif style == 'fifth':
                    pitch = root if k % 2 == 0 else tones['f']
                elif style == 'offbeat':
                    if k % 2 == 0:
                        continue
                    pitch = root
                else:  # arp
                    pitch = arp_seq[k % 4]
                add(t, r * g, pitch, vel * (0.92 if style == 'octave' and k % 2 else 1.0))
    return Clip._raw(notes, p.length)


def chords(prog, voicing: str = 'smooth', register=(52, 76), voices: int | None = 4, vel: float = 84,
           gate: float = 1.0, rhythm: str | None = None, step='1/8', strum: float = 0.0, bass: bool = False,
           octave: int = 4, inversion: int = 0, key=None, length=4.0) -> Clip:
    """Block chords over a progression -> Clip (pads, keys, stabs).

    voicing: smooth (voice-led, default), close, open, drop2, drop3, spread. register=(lo, hi) is
    where the voicing sits; voices = notes per chord (tones chosen by importance, doubled if needed).
    rhythm: grid string repeated inside every chord (e.g. 'x..x..x.' with step='1/8' for stabs,
    '_' holds), None = one held chord per chord change. gate shortens notes (1 = full length).
    strum: delay in beats between successive voices (0.02 = quick guitar-like strum).
    bass=True adds the slash bass / root below each voicing."""
    p = _as_prog(prog, key, length)
    v = p.voiced(voicing, register=register, voices=voices, bass=bass, octave=octave, inversion=inversion)
    notes = []
    st = beats(step)
    cells = _cells(rhythm, 'rhythm') if rhythm is not None else None
    for start, dur, pitches in v:
        if cells is None:
            hits = [(0.0, dur, vel)]
        else:
            hits = [(i * st, n * st, _level(c, vel)) for i, n, c in _events(cells, int(math.floor(dur / st + _EPS)))]
        for off, ln, hv in hits:
            for i, pitch in enumerate(sorted(pitches)):
                o = i * strum
                if o < ln:
                    notes.append(Note(start + off + o, max((ln - o) * gate, 1e-3), pitch, _vel(hv)))
    return Clip._raw(notes, p.length)


# ------------------------------------------------------------------------------------- motifs

class _Ev(NamedTuple):
    step: int | None   # 0-based scale step (None = rest)
    alter: int
    dur: float
    acc: float


_DEG_RE = re.compile(r'^([#b]*)(-?\d+)$')


class Motif:
    """A melody in scale degrees of a key, so it can be transposed/inverted/sequenced diatonically.

        m = Motif('1:1/8 3:1/8 5:1/4 r:1/4 8:1/2', key)   # degree[:duration] tokens
        m = key.motif('5 _ 3 1 2 _ _ .', dur='1/8')        # default duration; '_' holds, '.'/r rest
        m = Motif([(1, 0.5), (3, 0.5), ('b7', 1), (None, 1), ('E5', 2)], key)

    Items: 1-based degree (8 = octave, -1 = below tonic), altered degree '#4'/'b7', note name 'E5',
    rest 'r'/'.'/None. Suffix '!' accents, '?' ghosts. Render with .clip(octave=4)."""

    __slots__ = ('key', 'events')

    def __init__(self, spec, key, dur=0.5):
        self.key = Key(key)
        d0 = beats(dur)
        evs: list[_Ev] = []
        items = spec.replace('|', ' ').split() if isinstance(spec, str) else list(spec)
        for it in items:
            if isinstance(it, tuple):
                if len(it) not in (2, 3):
                    raise ComposeError(f"motif item {it!r} must be (degree, dur) or (degree, dur, accent)")
                item, d = it[0], beats(it[1])
                acc = float(it[2]) if len(it) == 3 else 1.0
            elif isinstance(it, str):
                acc = 1.2 if '!' in it else 0.65 if '?' in it else 1.0
                tok = it.replace('!', '').replace('?', '')
                item, _, dd = tok.partition(':')
                d = beats(dd) if dd else d0
            else:
                item, d, acc = it, d0, 1.0
            if item == '_':
                if not evs:
                    raise ComposeError("motif can't start with '_' (hold)")
                evs[-1] = evs[-1]._replace(dur=evs[-1].dur + d)
                continue
            step, alter = self._parse_item(item)
            evs.append(_Ev(step, alter, d, acc))
        if not evs:
            raise ComposeError(f"empty motif {spec!r}")
        self.events = tuple(evs)

    def _parse_item(self, item) -> tuple[int | None, int]:
        if item is None or (isinstance(item, str) and item.lower() in ('r', '.', 'rest', '-')):
            return None, 0
        if _is_int(item):
            return _degree_to_step(item), 0
        if isinstance(item, str):
            m = _DEG_RE.match(item)
            if m:
                return _degree_to_step(int(m.group(2))), sum(1 if c == '#' else -1 for c in m.group(1))
            return self.key.step_of(note(item))
        raise ComposeError(f"motif item {item!r}: use a degree (int), '#4'/'b7', a note name 'E5' or a rest 'r'")

    @classmethod
    def _of(cls, key, events) -> 'Motif':
        m = cls.__new__(cls)
        m.key, m.events = key, tuple(events)
        return m

    def __repr__(self) -> str:
        toks = ['r' if e.step is None else ('#' * e.alter if e.alter > 0 else 'b' * -e.alter)
                + str(e.step + 1 if e.step >= 0 else e.step) for e in self.events]
        return f"Motif('{' '.join(f'{t}:{e.dur:g}' for t, e in zip(toks, self.events))}', {self.key.name!r})"

    @property
    def length(self) -> float:
        return sum(e.dur for e in self.events)

    def __len__(self) -> int:
        return len(self.events)

    def __add__(self, other: 'Motif') -> 'Motif':
        return Motif._of(self.key, self.events + other.events)

    def __mul__(self, n: int) -> 'Motif':
        return Motif._of(self.key, self.events * int(n))

    __rmul__ = __mul__

    # --- transforms
    def transpose(self, steps: int) -> 'Motif':
        """Diatonic transposition by scale steps (2 = up a third)."""
        return Motif._of(self.key, [e if e.step is None else e._replace(step=e.step + steps) for e in self.events])

    def invert(self, axis: int | None = None) -> 'Motif':
        """Mirror intervals around a degree (default: the first note)."""
        first = next((e.step for e in self.events if e.step is not None), 0)
        ax = first if axis is None else _degree_to_step(axis)
        return Motif._of(self.key, [e if e.step is None else e._replace(step=2 * ax - e.step, alter=-e.alter)
                                    for e in self.events])

    def retrograde(self) -> 'Motif':
        return Motif._of(self.key, self.events[::-1])

    def stretch(self, factor: float) -> 'Motif':
        return Motif._of(self.key, [e._replace(dur=e.dur * factor) for e in self.events])

    def rhythm(self, durs) -> 'Motif':
        """Same pitches, new rhythm (durations cycled): m.rhythm(['1/8', '1/8', '1/4'])."""
        ds = [beats(d) for d in (durs.split() if isinstance(durs, str) else durs)]
        if not ds:
            raise ComposeError("rhythm needs at least one duration")
        return Motif._of(self.key, [e._replace(dur=ds[i % len(ds)]) for i, e in enumerate(self.events)])

    def sequence(self, *offsets: int) -> 'Motif':
        """Repeat at scale-step offsets: m.sequence(0, -1, -2) = motif, one step lower, two lower."""
        out: list[_Ev] = []
        for o in offsets or (0,):
            out.extend(self.transpose(o).events)
        return Motif._of(self.key, out)

    def resolve(self, degree: int = 1) -> 'Motif':
        """Answer phrase: the last note moves to the nearest `degree` (default tonic)."""
        evs = list(self.events)
        for i in range(len(evs) - 1, -1, -1):
            if evs[i].step is not None:
                n = len(self.key.intervals)
                target = _degree_to_step(degree) % n
                s = evs[i].step
                cands = [s - ((s - target) % n), s - ((s - target) % n) + n]
                evs[i] = evs[i]._replace(step=min(cands, key=lambda c: (abs(c - s), c)), alter=0)
                break
        return Motif._of(self.key, evs)

    def vary(self, seed=0, amount: float = 0.3) -> 'Motif':
        """Seeded rhythmic/melodic variation keeping the total length: splits notes, merges pairs,
        dots rhythms and swaps in neighbour tones. amount = probability per note."""
        rng = random.Random(seed_int(seed))
        ev = list(self.events)
        out: list[_Ev] = []
        i = 0
        while i < len(ev):
            e = ev[i]
            if e.step is not None and 0 < i and rng.random() < amount:
                op = rng.choice(('split', 'neighbor', 'merge', 'dot'))
                if op == 'split' and e.dur >= 0.5 - _EPS:
                    h = e.dur / 2
                    out += [e._replace(dur=h), e._replace(step=e.step + rng.choice((-1, 1)), alter=0, dur=h, acc=e.acc * 0.9)]
                    i += 1
                    continue
                if op == 'neighbor':
                    out.append(e._replace(step=e.step + rng.choice((-1, 1)), alter=0))
                    i += 1
                    continue
                if op == 'merge' and i + 1 < len(ev):
                    out.append(e._replace(dur=e.dur + ev[i + 1].dur))
                    i += 2
                    continue
                if op == 'dot' and i + 1 < len(ev) and ev[i + 1].dur > e.dur / 2 + _EPS:
                    out.append(e._replace(dur=e.dur * 1.5))
                    ev[i + 1] = ev[i + 1]._replace(dur=ev[i + 1].dur - e.dur / 2)
                    i += 1
                    continue
            out.append(e)
            i += 1
        return Motif._of(self.key, out)

    # --- output
    def pitches(self, octave: int = 4) -> list[int | None]:
        return [None if e.step is None else self.key.step(e.step, octave) + e.alter for e in self.events]

    def clip(self, octave: int = 4, vel: float = 96, gate: float = 0.92) -> Clip:
        """Render to a Clip; degree 1 is the tonic in `octave`."""
        notes, t = [], 0.0
        for e, p in zip(self.events, self.pitches(octave)):
            if p is not None:
                if not 0 <= p <= 127:
                    raise ComposeError(f"motif note {p} is outside MIDI 0..127; use a different octave")
                notes.append(Note(t, max(e.dur * gate, 1e-3), p, _vel(vel * e.acc)))
            t += e.dur
        return Clip._raw(notes, t)


# ------------------------------------------------------------------------------------- melody

_CONTOURS = {
    'arch': lambda x: math.sin(math.pi * x),
    'rise': lambda x: x,
    'fall': lambda x: 1.0 - x,
    'wave': lambda x: 0.5 + 0.5 * math.sin(2 * math.pi * x - math.pi / 2),
    'valley': lambda x: 1.0 - math.sin(math.pi * x),
    'flat': lambda x: 0.5,
}


def melody(prog, key, rhythm: str = 'x.x.x..x', step='1/8', register=('E4', 'E5'), contour: str = 'arch',
           seed=0, vel: float = 96, gate: float = 0.9, end_on_root: bool = True) -> Clip:
    """Generate a singable, chord-aware melody (a starting point to edit or motif-ise).

    Hits come from `rhythm` (grid string, repeated over the progression). Strong beats (1 and 3) and
    long notes take chord tones, others take scale tones; small steps are preferred over leaps,
    and the line follows `contour` (arch rise fall wave valley flat) inside `register`. Seeded."""
    p = prog if isinstance(prog, Progression) else Progression(prog, key=key)
    k = Key(key)
    lo, hi = _register(register)
    if contour not in _CONTOURS:
        raise ComposeError(f"unknown contour {contour!r}; use one of {', '.join(_CONTOURS)}")
    shape = _CONTOURS[contour]
    rng = random.Random(seed_int(seed))
    st = beats(step)
    cells = _cells(rhythm, 'rhythm')
    total = int(math.floor(p.length / st + _EPS))
    evs = _events(cells, total)
    scale_ps = k.notes(lo, hi)
    prev, prev2, repeats = None, None, 0
    notes = []
    for idx, (i, n, c) in enumerate(evs):
        t, d = i * st, n * st
        ch = p.at(t)
        strong = abs(t - round(t)) < _EPS and round(t) % 2 == 0
        pool = scale_ps
        if ch is not None and (strong or d >= 1.0 - _EPS or idx == len(evs) - 1):
            pool = [q for q in range(lo, hi + 1) if q % 12 in ch.pcs] or scale_ps
        if idx == len(evs) - 1 and end_on_root and ch is not None:
            pool = [q for q in range(lo, hi + 1) if q % 12 == ch.root] or pool
        target = lo + (hi - lo) * shape(t / max(p.length, _EPS))
        ref = target if prev is None else prev

        def score(q):
            s = abs(q - ref) * (1.0 if prev is not None else 0.3) + abs(q - target) * 0.35 + rng.random() * 2.5
            if prev is not None:
                if q == prev:
                    s += 2.5 + 6.0 * repeats  # a repeated note is fine once, a drone is not
                elif q == prev2:
                    s += 1.2                  # discourage E-F-E-F wobbles
                if abs(q - prev) > 7:
                    s += 4.0
            return s
        q = min(pool, key=score)
        repeats = repeats + 1 if q == prev else 0
        prev2, prev = prev, q
        notes.append(Note(t, d * gate, q, _level(c, vel)))
    return Clip._raw(notes, p.length)


# -------------------------------------------------------------------------------------- fills

def snare_roll(length: float = 2.0, step='1/16', vel=(40, 120), pitch='snare', build: bool = False) -> Clip:
    """Snare (or any drum) roll with a velocity crescendo. build=True accelerates: 8ths, then the
    step, then half-steps over the last quarter (classic pre-chorus build)."""
    L, st = beats(length), beats(step)
    p = drum(pitch)
    v0, v1 = vel
    times: list[tuple[float, float]] = []
    if build:
        parts = [(0.0, L / 2, st * 2), (L / 2, L * 0.75, st), (L * 0.75, L, st / 2)]
        for a, b, s in parts:
            t = a
            while t < b - _EPS:
                times.append((t, s))
                t += s
    else:
        times = [(k * st, st) for k in range(int(math.floor(L / st + _EPS)))]
    notes = [Note(t, s, p, _vel(v0 + (v1 - v0) * (t / L) ** 1.5)) for t, s in times]
    return Clip._raw(notes, L)


def tom_fill(length: float = 1.0, step='1/16', toms=('tom_hi', 'tom_mid', 'tom_lo'), vel=(96, 124)) -> Clip:
    """Descending tom run over `length` beats (toms split into equal groups)."""
    L, st = beats(length), beats(step)
    ps = [drum(t) for t in toms]
    n = int(math.floor(L / st + _EPS))
    v0, v1 = vel
    notes = [Note(k * st, st, ps[min(len(ps) - 1, k * len(ps) // max(n, 1))],
                  _vel(v0 + (v1 - v0) * k / max(n - 1, 1))) for k in range(n)]
    return Clip._raw(notes, L)


def crash(vel: float = 112, pitch='crash') -> Clip:
    """A single crash hit (1 beat long clip) at velocity `vel` (1..127)."""
    if isinstance(vel, bool) or not isinstance(vel, (int, float)) or not 1 <= vel <= 127:
        raise ComposeError(f"crash vel is a MIDI velocity 1..127, got {vel!r}")
    return Clip._raw([Note(0.0, 1.0, drum(pitch), _vel(vel))], 1.0)



# ======================================================================================== jazz
#
# Comping, walking bass, brushes and ride for small-group jazz. Every generator writes STRAIGHT 8ths (and exact
# triplets where a triplet is meant): the swing ratio (by tempo) and each part's lay-back are applied afterwards by
# the feel - track.groove(jazz_groove('bass', s.tempo)) or jazz.Feel - so one part works at any tempo. Seeded.

def _unit(x, what: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
        raise ComposeError(f"{what} must be a number 0..1, got {x!r}")
    return float(x)


def _clampv(v: float) -> float:
    return max(1.0, min(127.0, float(v)))


def _real(x, what: str, lo: float, hi: float) -> float:
    """A finite number in lo..hi (strict: strings, bools, NaN and out-of-range values are errors)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not lo <= x <= hi:
        raise ComposeError(f"{what} must be a number {lo:g}..{hi:g}, got {x!r}")
    return float(x)


# ----------------------------------------------------------------------------------- comping

COMP_STYLES = ('swing', 'charleston', 'garland', 'ballad', 'sparse', 'bossa', 'waltz')

COMP_CELLS: dict[str, tuple] = {
    'charleston': ((0.0, 1.0, 1.0), (1.5, 0.5, 0.92)),            # 1, & of 2
    'reverse':    ((0.5, 0.5, 0.9), (2.0, 1.0, 1.0)),             # & of 1, 3 (reverse Charleston)
    'push4':      ((3.5, 1.0, 1.0),),                             # & of 4: anticipates the next bar
    'charl_push': ((0.0, 1.0, 1.0), (1.5, 0.5, 0.9), (3.5, 1.0, 0.95)),
    'one_and3':   ((0.0, 0.9, 1.0), (2.5, 1.0, 0.92)),
    'and2':       ((1.5, 2.0, 0.95),),                            # a held push on the & of 2
    'and3':       ((2.5, 1.2, 0.95),),
    'and2and4':   ((1.5, 0.4, 0.95), (3.5, 0.4, 0.95)),           # Red Garland: short hits on the & of 2 and 4
    'and1and3':   ((0.5, 0.4, 0.9), (2.5, 0.4, 0.95)),
    'on2on4':     ((1.0, 0.4, 0.85), (3.0, 0.4, 0.9)),
    'four_push':  ((3.0, 0.4, 0.85), (3.5, 1.0, 1.0)),
    'two':        ((0.0, 1.9, 1.0), (2.0, 1.9, 0.9)),             # 1 and 3, held (ballads, two-feel)
    'whole':      ((0.0, 3.8, 1.0),),                             # one held chord on 1
    'rest':       (),
    # 3/4
    'w_one':      ((0.0, 2.8, 1.0),),
    'w_one_and2': ((0.0, 0.9, 1.0), (1.5, 1.2, 0.92)),
    'w_two_three': ((1.0, 0.45, 0.9), (2.0, 0.45, 0.92)),
    'w_and2':     ((1.5, 1.2, 0.95),),
    'w_and3':     ((2.5, 1.0, 1.0),),
    'w_rest':     (),
}
"""Comping cells: (position in beats inside the bar, length in beats, level) on a straight 8th grid."""

_COMP_WEIGHTS = {
    'swing':      {'charleston': 3.0, 'reverse': 2.0, 'push4': 2.0, 'charl_push': 1.0, 'one_and3': 1.5, 'and2': 1.5,
                   'and3': 1.0, 'and2and4': 1.0, 'and1and3': 1.0, 'four_push': 1.0, 'whole': 1.0, 'rest': 1.0},
    'charleston': {'charleston': 6.0, 'charl_push': 2.0, 'reverse': 1.5, 'push4': 1.0, 'rest': 0.5},
    'garland':    {'and2and4': 5.0, 'and1and3': 1.5, 'and2': 1.0, 'four_push': 1.0, 'charleston': 1.0, 'rest': 0.5},
    'ballad':     {'whole': 4.0, 'two': 3.0, 'and2': 1.0, 'one_and3': 1.0, 'push4': 0.8, 'rest': 0.4},
    'sparse':     {'whole': 2.0, 'rest': 3.0, 'and2': 1.5, 'push4': 1.5, 'charleston': 1.0, 'and3': 1.0},
    'waltz':      {'w_one': 3.0, 'w_one_and2': 2.0, 'w_two_three': 1.5, 'w_and2': 1.5, 'w_and3': 1.0, 'w_rest': 0.7},
}
_ANCHORED = {'charleston', 'charl_push', 'one_and3', 'two', 'whole', 'w_one', 'w_one_and2'}
_PUSHING = {'push4', 'charl_push', 'four_push', 'and2and4', 'w_and3'}
_BOSSA = ((((0.0, 0.9, 1.0), (1.5, 0.9, 0.9), (3.0, 0.9, 0.95)),      # bar 1: 1, & of 2, 4
           ((1.0, 0.9, 0.9), (2.5, 1.4, 0.95))),                     # bar 2: 2, & of 3
          (((0.0, 0.9, 1.0), (1.5, 0.9, 0.9), (3.0, 0.9, 0.95)),
           ((1.0, 0.9, 0.9), (2.5, 0.9, 0.9), (3.5, 1.2, 0.95))))     # bar 2 pushing into the next cycle


def _segments_of(p: Progression) -> list[tuple[float, float, Chord]]:
    return [(s, d, c) for s, d, c in p if c is not None]


def _seg_index(segs, t: float) -> int | None:
    for i, (s, d, _) in enumerate(segs):
        if s - _EPS <= t < s + d - _EPS:
            return i
    return None


def _merge_spans(clip: Clip, tail: float) -> list[tuple[float, float]]:
    spans: list[list[float]] = []
    for n in sorted(clip, key=lambda n: n.start):
        a, b = n.start, n.start + n.dur + tail
        if spans and a <= spans[-1][1] + _EPS:
            spans[-1][1] = max(spans[-1][1], b)
        else:
            spans.append([a, b])
    return [(a, b) for a, b in spans]


def comp(prog, style: str = 'swing', voicing: str = 'rootless', register=(48, 72), voices: int = 4,
         density: float = 0.5, intensity: float = 0.5, answer=None, phrase: int = 8, vel: float | None = None,
         roll: float | None = None, seed=0, key=None, touch: float = 1.0, length=4.0) -> Clip:
    """Jazz piano comping over a progression -> Clip (straight 8ths: swing it with the feel).

    Every bar picks a rhythm cell (COMP_CELLS) from the style's table, seeded and varied (no cell three times in a
    row; phrase starts - every `phrase` bars - favour a chord on 1, phrase ends a push into the next phrase):
      swing       the conversational mix: Charleston, reverse Charleston, & of 4 pushes, held & of 2, rests ...
      charleston  mostly Charleston (1, & of 2) and its variants
      garland     Red Garland: short chords on the & of 2 and the & of 4
      ballad      held chords on 1 (and 3), rolled, few pushes
      sparse      lots of space: held chords, pushes, empty bars
      bossa       the two-bar bossa nova pattern (1, &2, 4 | 2, &3) - play it straight, no swing
      waltz       3/4 cells
    A hit on the 8th before a chord change plays the NEW chord and ties over the change (an anticipation), and the
    change itself is then not struck again. density 0..1 moves the average from ~0.6 to ~3 hits per bar; intensity
    0..1 sets the velocity (about 50..88) and shortens the stabs. Voicings: `voicing` is a jazz style
    (JAZZ_VOICINGS: rootless (default, A/B voice-led), shell, quartal, sowhat, ust) or a classic one, placed in
    `register` (left hand C3..C5). answer=<melody Clip> (timed like the progression) comps in the melody's rests:
    hits under sounding melody notes are dropped (a chord change keeps a soft anchor) and every rest of a beat or
    more gets an answer. roll= beats between the voices of a chord (ballad default 0.02: a gentle roll).
    touch 0..1: the pianist's touch per hit - the comping breathes over each `phrase` (x0.87 at its ends, x1.13 in
    the middle) and every 2 bars (+-8 %), anticipations lean in (x1.16), short off-beat stabs are lighter (x0.9)
    than the anchors on 1 (x1.06), +-7 % per hit (~4-5 dB of hit-to-hit dynamics on a sampled piano), normalized in
    energy (vel / intensity keep the loudness); 0 = the flat cell levels."""
    touch = _unit(touch, 'comp touch')
    if style not in COMP_STYLES:
        raise ComposeError(f"unknown comp style {style!r}; use one of {', '.join(COMP_STYLES)}")
    density = _unit(density, 'comp density')
    intensity = _unit(intensity, 'comp intensity')
    if not _is_int(phrase) or phrase < 1:
        raise ComposeError(f"comp phrase must be an int >= 1 (bars), got {phrase!r}")
    p = _as_prog(prog, key, length)
    bpb = p.beats_per_bar
    if style == 'waltz' and abs(bpb - 3) > _EPS:
        raise ComposeError("comp style 'waltz' needs a 3/4 progression (beats_per_bar=3)")
    if style != 'waltz' and abs(bpb - 4) > _EPS:
        raise ComposeError(f"comp style {style!r} is written for 4/4; use style='waltz' for 3/4")
    segs = _segments_of(p)
    if not segs:
        return Clip._raw((), p.length)
    if voicing in JAZZ_VOICINGS:
        vs = jazz_voicings([c for _, _, c in segs], voicing, register=register, voices=voices)
    else:
        vs = [v for _, _, v in p.voiced(voicing, register=register, voices=voices)]
    rng = random.Random(seed_int(seed))
    base_vel = _real(vel, 'comp vel', 1, 127) if vel is not None else 50.0 + 38.0 * intensity
    target_hits = 0.6 + 2.4 * density
    n_bars = int(math.ceil(p.length / bpb - _EPS))
    hits: list[list] = []          # [t, dur, level, seg_index, pushed]
    history: list[str] = []
    starts = {round(s, 6) for s, _, _ in segs}
    for b in range(n_bars):
        t0 = b * bpb
        if style == 'bossa':
            cyc = _BOSSA[1 if density > 0.6 and rng.random() < 0.5 else 0]
            cells = cyc[b % 2]
        else:
            table = _COMP_WEIGHTS[style]
            names, weights = [], []
            nxt_change = round(t0 + bpb, 6) in starts
            for name, w in table.items():
                n_hits = len(COMP_CELLS[name])
                w *= math.exp(-((n_hits - target_hits) ** 2) / 2.0)
                if b % phrase == 0 and name in _ANCHORED:
                    w *= 2.5
                if b % phrase == phrase - 1 and name in _PUSHING and nxt_change:
                    w *= 2.0
                if len(history) >= 2 and history[-1] == history[-2] == name:
                    w = 0.0
                if b == 0 and name in ('rest', 'w_rest'):
                    w *= 0.1
                if w > 0:
                    names.append(name)
                    weights.append(w)
            name = rng.choices(names, weights)[0]
            history.append(name)
            cells = COMP_CELLS[name]
        for pos, dur, level in cells:
            t = t0 + pos
            if t >= p.length - _EPS:
                continue
            i = _seg_index(segs, t)
            if i is None:
                continue
            pushed = False
            s, d, _ = segs[i]
            if i + 1 < len(segs) and abs(segs[i + 1][0] - (t + 0.5)) < _EPS and abs(s + d - segs[i + 1][0]) < _EPS:
                i, pushed = i + 1, True          # the & before a change: anticipate the next chord
            hits.append([t, dur, level, i, pushed])
    # an anticipated change is not struck again on its downbeat
    pushed_into = {h[3] for h in hits if h[4]}
    hits = [h for h in hits if not (not h[4] and h[3] in pushed_into and abs(h[0] - segs[h[3]][0]) < _EPS)]
    # every chord of 2+ beats gets at least one hit (unless the texture is meant to be empty)
    if density >= 0.25:
        have = {h[3] for h in hits}
        for i, (s, d, _) in enumerate(segs):
            if i not in have and d >= 2 - _EPS:
                hits.append([s, min(1.5, d * 0.5), 0.9, i, False])
    if answer is not None:
        hits = _answer_hits(hits, as_clip(answer), segs, p.length, rng)
    hits.sort(key=lambda h: h[0])
    uniq: list[list] = []
    for h in hits:                    # one chord per instant (an answer / anchor never doubles a hit)
        if not uniq or h[0] - uniq[-1][0] > _EPS:
            uniq.append(h)
    hits = uniq
    if roll is None:
        roll = 0.02 if style == 'ballad' else 0.0
    trng = random.Random(seed_int(seed) + 211)       # the touch's own dice: the hits are the same with any touch
    span = phrase * bpb
    tfs = []
    for t, dur, level, i, pushed in hits:
        # the pianist's touch: the comping breathes over the phrase (softer at its ends, fuller in the middle),
        # anticipations lean in, short off-beat stabs are lighter than the anchors on 1, no two hits alike
        x = (t % span) / span
        x2 = (t % (2 * bpb)) / (2 * bpb)                # a 2-bar breath inside it
        on_one = abs(t % bpb) < _EPS
        stab = not pushed and not on_one and dur <= 0.5 + _EPS
        arc = 1.0 + touch * (0.26 * (0.5 - 0.5 * math.cos(2.0 * math.pi * x)) - 0.13
                             + 0.08 * math.sin(2.0 * math.pi * x2))
        accent = 1.0 + touch * (0.06 if on_one else -0.1 if stab else 0.1 / 1.06 if pushed else 0.0)
        tfs.append(arc * accent * (1.0 + touch * 0.07 * (2.0 * trng.random() - 1.0)))
    # the touch shapes the level, vel / intensity keep it: normalized in energy (a sampled piano's level grows about
    # with velocity^2, its energy ^4), so the louder hits don't lift the comping's loudness
    norm = (len(tfs) / sum(x ** 4 for x in tfs)) ** 0.25 if tfs else 1.0
    notes: list[Note] = []
    for hi_, (t, dur, level, i, pushed) in enumerate(hits):
        tf = tfs[hi_] * norm
        s, d, _ = segs[i]
        if dur < 1.5:
            dur = max(0.25, dur * (1.2 - 0.4 * intensity))
        end = s + d
        if pushed:
            dur = max(dur, min(1.25, s + d - t))
        # the hand lets go before it strikes again: a held push never runs into the next hit (same keys twice
        # at once would retrigger / cut each other in the instrument)
        nxt_t = hits[hi_ + 1][0] if hi_ + 1 < len(hits) else math.inf
        dur = max(0.2, min(dur, end - t, p.length - t, nxt_t - t - 0.04))
        v = base_vel * level * (1.06 if pushed else 1.0) * (1.0 + (rng.random() - 0.5) * 0.08) * tf
        ps = sorted(vs[i])
        for k, pitch in enumerate(ps):
            o = k * roll
            if o >= dur * 0.5:
                o = 0.0
            f = 1.05 if k == len(ps) - 1 else 0.95 if k == 0 else 1.0
            notes.append(Note(t + o, max(dur - o, 0.05), pitch, _vel(v * f)))
    return Clip._raw(notes, p.length)


def _answer_hits(hits, melody: Clip, segs, total: float, rng: random.Random) -> list[list]:
    """Keep comping hits out of the melody (a chord change inside a melody note keeps a soft, short anchor) and put
    an answer into every melody rest of a beat or more."""
    busy = _merge_spans(melody, 0.25)

    def is_busy(t):
        return any(a - _EPS <= t < b - _EPS for a, b in busy)
    kept = []
    for h in hits:
        t, dur, level, i, pushed = h
        if not is_busy(t):
            kept.append(h)
        elif abs(t - segs[i][0]) < _EPS or pushed:
            kept.append([t, min(dur, 0.5), level * 0.8, i, pushed])
    gaps = []
    edge = 0.0
    for a, b in busy:
        if a - edge >= 1.0 - _EPS:
            gaps.append((edge, a))
        edge = max(edge, b)
    if total - edge >= 1.0 - _EPS:
        gaps.append((edge, total))
    for a, b in gaps:
        if any(a - _EPS <= h[0] < b - _EPS for h in kept):
            continue
        t = math.ceil(a * 2 - _EPS) / 2.0               # the next 8th
        if abs(t - round(t)) < _EPS and rng.random() < 0.6 and t + 0.5 < b - 0.25:
            t += 0.5                                      # answer on the off-beat
        if t >= b - 0.25 or t >= total - _EPS:
            continue
        i = _seg_index(segs, t)
        if i is None:
            continue
        kept.append([t, min(1.0, b - t), 0.92, i, False])
        if b - a >= 2.5 and rng.random() < 0.5:
            t2 = t + 1.5
            j = _seg_index(segs, t2)
            if j is not None and t2 < b - 0.25:
                kept.append([t2, min(0.75, b - t2), 0.85, j, False])
    return kept


# ------------------------------------------------------------------------------- walking bass

WALK_FEELS = ('four', 'two')
_APPROACH_WEIGHTS = {'chromatic': (3.0, 1.0, 0.5), 'scale': (1.0, 3.0, 0.5), 'mixed': (2.0, 1.5, 1.0),
                     'dominant': (1.0, 1.0, 3.0)}
_STEP_COST = {0: 3.5, 1: 0.6, 2: 0.4, 3: 0.8, 4: 0.9, 5: 1.4, 6: 2.5, 7: 1.8, 8: 3.0, 9: 3.0, 10: 4.0, 11: 4.0,
              12: 2.5}


def _near(pc: int, ref: float, lo: int, hi: int) -> int:
    """The pitch of class `pc` nearest to `ref` inside [lo, hi] (ties go down)."""
    cands = [p for p in range(lo, hi + 1) if p % 12 == pc % 12]
    if not cands:
        raise ComposeError(f"bass range {lo}..{hi} holds no pitch class {pc}")
    return min(cands, key=lambda p: (abs(p - ref), p))


def _home(pc: int, prev: float | None, lo: int, hi: int) -> int:
    """Where the bass takes pitch class `pc` next: near the previous note, but pulled back towards the middle of
    the range (a line that drifts to an edge jumps an octave home instead of crawling along it)."""
    mid = (lo + hi) / 2.0
    if prev is None:
        return _near(pc, lo + 9, lo, hi)
    cands = [p for p in range(lo, hi + 1) if p % 12 == pc % 12]
    return min(cands, key=lambda p: (abs(p - prev) + 0.45 * max(0.0, abs(p - mid) - 7.0), p))


def _merge_same(segs):
    """Consecutive segments of the same chord become one (the bass keeps walking instead of restarting)."""
    out: list[list] = []
    for s, d, c in segs:
        if out and out[-1][2].symbol == c.symbol and abs(out[-1][0] + out[-1][1] - s) < _EPS:
            out[-1][1] += d
        else:
            out.append([s, d, c])
    return [tuple(x) for x in out]


def _pedal_spans(pedal, total: float) -> list[tuple[float, float, int]]:
    if pedal is None:
        return []
    if isinstance(pedal, (str, int)) and not isinstance(pedal, bool):
        return [(0.0, total, note(pedal))]
    out = []
    for item in pedal:
        if not isinstance(item, (tuple, list)) or len(item) != 3:
            raise ComposeError(f"pedal spans must be (start_beat, end_beat, pitch), got {item!r}")
        a, b, pitch = item
        a, b = float(getattr(a, 'start', a)), float(getattr(b, 'start', b))
        if b <= a:
            raise ComposeError(f"pedal span {item!r}: end must be after start")
        out.append((a, b, note(pitch)))
    return out


def walking_bass(prog, key=None, feel: str = 'four', low='E1', high='G3', seed=0, vel: float = 90,
                 gate: float = 0.9, approach: str = 'mixed', skip: float = 0.1, octave: float = 0.05,
                 repeat: float = 0.05, pedal=None, accent: float = 1.05, skip_grid: str = 'swing',
                 touch: float = 1.0, length=4.0) -> Clip:
    """Upright-bass line over a progression -> Clip (straight: swing the skip notes with the feel).

    feel='four' walks quarter notes: the root (or slash bass) on beat 1 of every chord, chord tones on the strong
    beat 3 and chord / scale / chromatic passing tones between, and on the last beat before each change an approach
    to the next root - chromatic from above or below, a scale step, or its dominant (5th) - chosen by `approach`
    (chromatic | scale | dominant | mixed) and by the direction the line comes from. The line is planned like a melody
    (a seeded dynamic programme: steps and 3rds over leaps, no A-B-A wobbles, one direction per bar) inside
    `low`..`high` (E1..G3). Colour, all seeded probabilities per beat: skip (a ghosted 8th skip note before the next
    beat), octave (an octave leap), repeat (beat 2 repeats beat 1). Long chords keep walking (bar 2 starts on a
    chord tone, not always the root). feel='two': half notes, root then 5th / an approach, with pickup 8ths (skip).
    pedal='G1' (the whole clip) or [(start, end, 'C2'), ...] holds pedal points (four: quarters with an occasional
    octave, two: half notes) and approaches the chord after the pedal. accent = beats 2 and 4 (subtle); gate = note
    length per beat (0.9: slightly detached; ballads 0.97). skip_grid: 'swing' puts a skip note on the & (the feel
    swings it with everything else), 'triplet' exactly on the last 8th-note triplet of the beat (the skip-note
    triplet, independent of the swing ratio). touch 0..1: a bassist's dynamics (humanize.bass_touch: 4-bar phrase
    arcs ~0.8 x vel .. ~1.16 x vel with the loudness kept at vel, beats 2 / 4 feathered in 'four', 1 / 3 in 'two',
    ghosted skip notes, lighter approach notes, pushed anticipations accented; ~6 dB per phrase on a
    velocity-responsive bass); 0 = the flat written level (vel +-3 %: the dynamics ear reads it as flat_dynamics)."""
    touch = _unit(touch, 'walking_bass touch')
    if skip_grid not in ('swing', 'triplet'):
        raise ComposeError(f"walking_bass skip_grid must be 'swing' or 'triplet', got {skip_grid!r}")
    if feel not in WALK_FEELS:
        raise ComposeError(f"walking_bass feel must be one of {', '.join(WALK_FEELS)}, got {feel!r}")
    if approach not in _APPROACH_WEIGHTS:
        raise ComposeError(f"walking_bass approach must be one of {', '.join(_APPROACH_WEIGHTS)}, got {approach!r}")
    skip, octave, repeat = (_unit(x, f"walking_bass {n}") for x, n in ((skip, 'skip'), (octave, 'octave'),
                                                                       (repeat, 'repeat')))
    vel = _real(vel, 'walking_bass vel', 1, 127)
    gate = _real(gate, 'walking_bass gate', 0.05, 1.0)
    accent = _real(accent, 'walking_bass accent', 0.5, 2.0)
    p = _as_prog(prog, key, length)
    kk = Key(key) if key is not None else p.key
    lo, hi = note(low), note(high)
    if hi - lo < 12:
        raise ComposeError(f"walking_bass range {low!r}..{high!r} must span at least an octave")
    rng = random.Random(seed_int(seed))
    segs = _merge_same(_segments_of(p))
    events: list[list] = []        # [t, dur, pitch, vel_factor, kind]
    prev: float | None = None
    for i, (s, d, c) in enumerate(segs):
        nxt = segs[i + 1] if i + 1 < len(segs) and abs(segs[i + 1][0] - (s + d)) < _EPS else None
        ev = (_walk_four if feel == 'four' else _walk_two)(c, s, d, nxt[2] if nxt else None, prev, lo, hi, kk, rng,
                                                           approach, octave, repeat, p.beats_per_bar)
        events += ev
        if ev:
            prev = ev[-1][2]
    for a, b, pitch in _pedal_spans(pedal, p.length):
        events = _apply_pedal(events, a, b, pitch, feel, segs, lo, hi, rng)
    events.sort(key=lambda e: e[0])
    notes: list[Note] = []
    for k, (t, dur, pitch, f, kind) in enumerate(events):
        nxt_t = events[k + 1][0] if k + 1 < len(events) else p.length
        room = nxt_t - t
        if kind != 'ghost' and skip > 0 and room >= 1.0 - _EPS and rng.random() < skip and t + 0.5 < p.length:
            if feel == 'four' or abs(room - 2.0) < 0.5:
                pickup = 1.0 / 3.0 if skip_grid == 'triplet' else 0.5
                g = t + (room - pickup)
                nxt_p = events[k + 1][2] if k + 1 < len(events) else pitch
                gp = pitch if abs(nxt_p - pitch) != 2 or rng.random() < 0.5 else (pitch + nxt_p) // 2
                notes.append(Note(g, min(0.3, pickup * 0.8), gp, _vel(vel * 0.5)))
                dur = min(dur, room - pickup - 0.05)
        beat_in_bar = (t % p.beats_per_bar)
        acc = accent if abs(beat_in_bar - round(beat_in_bar)) < _EPS and int(round(beat_in_bar)) % 2 == 1 else 1.0
        length_ = min(dur, room) * (gate if kind != 'ghost' else 1.0) if dur >= 0.99 else dur
        v = vel * f * acc * (1.0 + (rng.random() - 0.5) * 0.06)
        notes.append(Note(t, max(0.05, length_), pitch, _vel(v)))
    if touch > 0:
        notes = _bass_touched(notes, p.length, vel, touch, '2-4' if feel == 'four' else '1-3', p.beats_per_bar,
                              seed_int(seed) + 101)
    return Clip._raw(notes, p.length)


def _bass_touched(notes: list, length: float, vel: float, amount: float, accent: str, bpb: float, seed) -> list:
    """walking_bass's line through humanize.bass_touch (4-bar arcs lo 0.8 x vel .. hi 1.16 x vel, beat accents,
    ghosts, approaches), blended with the written velocities by `amount` (1 = fully touched) and scaled back to the
    written loudness (energy, velocity^4: vel keeps the level). Its own seed: the notes are the same with any amount."""
    from .humanize import bass_touch
    ns = sorted(notes, key=lambda n: (n.start, n.pitch))
    shaped = bass_touch(Clip._raw(ns, length), max(1.0, vel * (1.0 - 0.2 * amount)),
                        min(127.0, vel * (1.0 + 0.16 * amount)), accent=accent, phrase=4 * bpb, beats_per_bar=bpb,
                        seed=seed)
    new = [n.vel * (1.0 - amount) + m.vel * amount for n, m in zip(ns, sorted(shaped, key=lambda n: (n.start, n.pitch)))]
    # the line's loudness stays: normalized in energy (the level of a velocity-responsive bass grows ~ velocity^2)
    norm = (sum(n.vel ** 4 for n in ns) / sum(v ** 4 for v in new)) ** 0.25 if new and sum(new) > 0 else 1.0
    return [n._replace(vel=_vel(v * norm)) for n, v in zip(ns, new)]


def _bass_pool(c: Chord, kk, lo: int, hi: int) -> tuple[set[int], set[int]]:
    """(chord-tone pitches, scale pitches) in lo..hi: the key's scale when the chord fits it, else the chord scale."""
    chord_pcs = {(c.root + i) % 12 for i in c.intervals if i < 12} | {c.bass_pc}
    if kk is not None and chord_pcs <= kk.pcs:
        scale_pcs = set(kk.pcs)
    else:
        scale_pcs = {(c.root + i) % 12 for i in chord_scale(c)}
    scale_pcs |= chord_pcs
    rng_ = range(lo, hi + 1)
    return {p for p in rng_ if p % 12 in chord_pcs}, {p for p in rng_ if p % 12 in scale_pcs}


def _approach_options(target: int, c_next: Chord | None, kk, lo: int, hi: int, mode: str) -> list[tuple[int, float]]:
    wc, ws, wd = _APPROACH_WEIGHTS[mode]
    opts: dict[int, float] = {}

    def add(p, w):
        if lo <= p <= hi and p != target:
            opts[p] = max(opts.get(p, 0.0), w)
    add(target - 1, wc)
    add(target + 1, wc)
    if c_next is not None:
        _, scale = _bass_pool(c_next, kk, lo - 2, hi + 2)
        below = max((q for q in scale if q < target), default=None)
        above = min((q for q in scale if q > target), default=None)
        if below is not None:
            add(below, ws)
        if above is not None:
            add(above, ws)
    add(target + 7, wd)
    add(target - 5, wd)
    return list(opts.items())


def _walk_line(start: int, target: int | None, n: int, c: Chord, c_next: Chord | None, lo: int, hi: int, kk,
               rng: random.Random, mode: str, repeat_first: bool = False) -> list[int]:
    """n quarter-note pitches: `start` first, then a planned path; the last one approaches `target` if given.
    repeat_first=True makes the second note repeat the first (a planned repeated note)."""
    if n <= 1:
        return [start][:n]
    tones, scale = _bass_pool(c, kk, lo, hi)
    comfy_lo, comfy_hi = lo + 3, hi - 4
    direction = 0 if target is None else (1 if target > start else -1 if target < start else 0)
    if direction == 0:
        direction = 1 if start < (lo + hi) / 2 else -1
    cands = sorted(p for p in range(max(lo, start - 10), min(hi, start + 10) + 1))
    noise = {(k, q): rng.random() * 0.9 for k in range(n) for q in range(lo - 13, hi + 14)}

    def note_cost(k, q, is_last):
        if is_last:
            return 0.0
        cost = 0.0
        if q not in scale:
            cost += 1.2 if k % 2 == 1 else 2.2           # chromatic: a passing tone on 2 or 4, rarely on 3
        elif q not in tones:
            cost += 0.3 if k % 2 == 1 else 1.5
        if not comfy_lo <= q <= comfy_hi:
            cost += 0.8
        return cost + noise[(k, q)]

    last_opts = (_approach_options(target, c_next, kk, lo, hi, mode) if target is not None
                 else [(q, 1.0) for q in cands if q in tones])
    last_cost = {q: (2.0 - math.log(w)) for q, w in last_opts}
    # states: (pitch, previous pitch) -> (cost, path)
    states: dict[tuple, tuple[float, list[int]]] = {(start, None): (0.0, [start])}
    for k in range(1, n):
        is_last = k == n - 1
        pool = list(last_cost) if is_last else ([start] if (k == 1 and repeat_first) else cands)
        new: dict[tuple, tuple[float, list[int]]] = {}
        for (q0, qm), (c0, path) in states.items():
            for q in pool:
                d = abs(q - q0)
                step = 0.0 if (k == 1 and repeat_first) else _STEP_COST.get(d, 8.0)
                cost = c0 + step + note_cost(k, q, is_last)
                if is_last:
                    cost += last_cost[q] + noise[(k, q)] * 0.5
                    if target is not None and q0 == target:
                        cost += 1.0                                # arrived a beat early
                if qm is not None and q == qm and d > 0:
                    cost += 1.2                                    # A-B-A wobble
                if not is_last and (q - q0) * direction < 0:
                    cost += 0.5                                    # against the bar's direction
                if qm is not None and d == 1 and abs(q0 - qm) == 1 and (q - q0) * (q0 - qm) > 0 and q0 not in scale:
                    cost -= 1.0                                    # chromatic passing tone resolving on
                key_ = (q, q0)
                if key_ not in new or cost < new[key_][0] - 1e-9:
                    new[key_] = (cost, path + [q])
        states = new
    return min(states.values(), key=lambda v: (v[0], v[1]))[1]


def _walk_four(c: Chord, s: float, d: float, c_next: Chord | None, prev, lo, hi, kk, rng, mode, octave, repeat,
               bpb: float = 4.0):
    n = max(1, int(math.floor(d + _EPS)))
    root = _home(c.bass_pc, prev, lo, hi)
    tones, _ = _bass_pool(c, kk, lo, hi)
    out: list[list] = []
    m_bar = max(1, int(round(bpb)))          # walk bar by bar (3/4: chunks of 3)
    chunks = [m_bar] * (n // m_bar) + ([n % m_bar] if n % m_bar else [])
    if not chunks:
        chunks = [n]
    pos = s
    cur = root
    for ci, m in enumerate(chunks):
        last_chunk = ci == len(chunks) - 1
        if last_chunk:
            if c_next is not None:
                target = _home(c_next.bass_pc, cur, lo, hi)
            else:
                target = None
        else:        # the next bar of the same chord starts on its root, 3rd or 5th near here
            strong = [q for q in tones if (q - c.root) % 12 in (0, 3, 4, 5, 7) and q != cur]
            pick = sorted(strong, key=lambda q: (abs(q - cur), q))[:3]
            target = rng.choice(pick) if pick else cur
        rep = m >= 3 and ci == 0 and rng.random() < repeat
        line = _walk_line(cur, target, m, c, c_next if last_chunk else c, lo, hi, kk, rng, mode, rep)
        if m >= 3 and rng.random() < octave:      # an octave leap: the previous note again, an octave away
            k = rng.choice([1, 2]) if m >= 4 else 1
            for q in (line[k - 1] + 12, line[k - 1] - 12):
                if lo <= q <= hi and abs(q - line[k + 1]) <= 7:
                    line[k] = q
                    break
        for k, q in enumerate(line):
            is_app = last_chunk and k == m - 1 and c_next is not None and m > 1
            f = 1.03 if (ci == 0 and k == 0) else 0.94 if is_app else 1.0
            out.append([pos + k, 1.0, q, f, 'approach' if is_app else 'walk'])
        pos += m
        if not last_chunk:
            cur = target
    rest = d - n
    if rest > _EPS and out:
        out[-1][1] += rest
    return out


def _walk_two(c: Chord, s: float, d: float, c_next: Chord | None, prev, lo, hi, kk, rng, mode, octave, repeat,
              bpb: float = 4.0):
    root = _home(c.bass_pc, prev, lo, hi)
    tones, _ = _bass_pool(c, kk, lo, hi)
    out: list[list] = []
    n_half = max(1, int(math.floor(d / 2 + _EPS)))
    t = s
    cur = root
    for h in range(n_half):
        last = h == n_half - 1
        if h == 0:
            q = root
        elif last and c_next is not None:
            tgt = _home(c_next.bass_pc, cur, lo, hi)
            opts = _approach_options(tgt, c_next, kk, lo, hi, mode)
            fifth = [x for x in tones if (x - c.root) % 12 == 7 and abs(x - cur) <= 7]
            opts += [(x, 1.5) for x in fifth]                    # or simply the chord's own 5th
            opts = [(p_, w * (1.5 if abs(p_ - tgt) in (5, 7) else 1.0) / (1.0 + 0.15 * max(0, abs(p_ - cur) - 5)))
                    for p_, w in opts if p_ != cur and abs(p_ - cur) <= 9]
            q = rng.choices([p_ for p_, _ in opts], [w for _, w in opts])[0] if opts else cur
        else:
            fifths = [x for x in tones if (x - c.root) % 12 in (6, 7, 8) and abs(x - cur) <= 7 and x != cur]
            thirds = [x for x in tones if (x - c.root) % 12 in (3, 4) and abs(x - cur) <= 9 and x != cur]
            roots = [x for x in tones if x % 12 == c.bass_pc and x != cur and abs(x - cur) <= 12]
            pool = fifths if (fifths and rng.random() < 0.7) else (thirds or fifths or roots or [cur])
            mid = (lo + hi) / 2.0
            q = min(pool, key=lambda x: (abs(x - cur) + 0.45 * max(0.0, abs(x - mid) - 7.0), x))
        dur = 2.0 if not last else d - 2.0 * h
        out.append([t, dur, q, 1.03 if h == 0 else 0.96, 'walk' if h == 0 else 'approach'])
        t += 2.0
        cur = q
    if d < 2.0 - _EPS:
        out = [[s, d, root, 1.0, 'walk']]
    return out


def _apply_pedal(events, a: float, b: float, pitch: int, feel: str, segs, lo: int, hi: int, rng) -> list[list]:
    keep = [e for e in events if not (a - _EPS <= e[0] < b - _EPS)]
    step = 1.0 if feel == 'four' else 2.0
    t = a
    new = []
    while t < b - _EPS:
        q = pitch
        if feel == 'four' and abs((t - a) % 4 - 2) < _EPS and rng.random() < 0.3 and pitch + 12 <= hi:
            q = pitch + 12
        new.append([t, min(step, b - t), q, 1.0 if abs((t - a) % 4) < _EPS else 0.95, 'pedal'])
        t += step
    after = _seg_index(segs, b)
    if new and after is not None and abs(segs[after][0] - b) < _EPS and segs[after][2].bass_pc != pitch % 12:
        tgt = _near(segs[after][2].bass_pc, pitch, lo, hi)
        app = tgt + (1 if tgt < pitch else -1)
        if lo <= app <= hi and new[-1][1] >= 1.0 - _EPS:
            last = new[-1]
            if feel == 'four':
                last[2] = app
            else:
                new.append([last[0] + 1.0, last[1] - 1.0, app, 0.9, 'approach'])
                last[1] = 1.0
    return keep + new


# --------------------------------------------------------------------------------- brushes

GM_BRUSH = {'kick': 36, 'kick2': 35, 'rim': 37, 'tap': 38, 'slap': 39, 'sweep': 40, 'tom_lo': 41, 'hat': 42,
            'tom_mlo': 43, 'hat_foot': 44, 'tom_mid': 45, 'hat_open': 46, 'tom_hi': 48, 'crash': 49, 'ride': 51,
            'ride_bell': 53, 'splash': 55, 'crash2': 57, 'ride2': 59}
"""GS / GeneralUser 'Brush' kit (inst.sf2(bank=128, program=40)): 38 brush tap, 39 brush slap, 40 brush swirl (a
held, looped sweep: hold the note for the length of the sweep), brushed toms 41..48, jazz kick 36, pedal hat 44."""

SWIRLY_BRUSH = {'kick': 36, 'tap': 38, 'dig': 39, 'slap': 40, 'sweep': 60, 'sweep_fast': 64, 'sweep_stop': 62,
                'flutter': 61, 'flutter2': 63, 'tom_lo': 41, 'hat': 42, 'tom_mlo': 43, 'hat_foot': 44, 'tom_mid': 45,
                'hat_open': 46, 'tom_hi': 47, 'tom_vhi': 48, 'crash': 49, 'ride': 51, 'china': 53, 'hat_splash': 54,
                'splash': 55, 'crash2': 57}
"""Karoryfer Swirly Drums keymap (assets/samples/swirly-drums/Programs/keymaps, default = Full_kit.sfz): 38 snare
(brush tap), 40 snare edge, 39 dig (pressed stroke), 60 slow stir / 64 fast stir (one-shot samples of 9-13 s that
the kit shapes into a swell: ~0.6 s in, an exponential tail; a new stir fades the old one; 62 silences them), 61 / 63
flutter, 44 hi-hat foot, 42 tight hat, 46 hat (closed..open), 51 ride, 49 crash, toms 41 43 45 47 48. Start a stir
about every second (the next one crossfades it): sweep=jazz.swirly_sweep(tempo) - half bars at medium swing, beats
at ballads."""

BRUSH_STYLES = ('medium', 'ballad', 'up', 'two')
_BRUSH_DEFAULTS = {   # sweep vel, tap vel, kick vel, hat vel, ghost-tap probability (sweep length: _sweep_beats)
    'medium': (50, 60, 18, 56, 0.3),
    'ballad': (42, 46, 14, 46, 0.12),
    'up':     (52, 62, 20, 58, 0.45),
    'two':    (46, 54, 16, 52, 0.2),
}
FILL_KINDS = ('triplets', 'eighths', 'slap', 'toms', 'swell')


def _kit_note(kit: dict, role: str, i: int = 0) -> int:
    if role not in kit:
        raise ComposeError(f"drum kit mapping has no {role!r}; it maps: {', '.join(sorted(kit))} "
                           f"(add {role!r}: <note>)")
    v = kit[role]
    if isinstance(v, (list, tuple)):
        if not v:
            raise ComposeError(f"drum kit role {role!r} has an empty list of notes")
        v = v[i % len(v)]
    return _pitch(v)


def _check_kit(kit) -> dict:
    if kit is None:
        return dict(GM_BRUSH)
    if not isinstance(kit, dict) or not kit:
        raise ComposeError(f"kit must be a dict role -> note (e.g. GM_BRUSH, SWIRLY_BRUSH), got {kit!r}")
    for role, v in kit.items():
        for x in (v if isinstance(v, (list, tuple)) else [v]):
            try:
                _pitch(x)
            except ComposeError:
                raise ComposeError(f"kit role {role!r}: {x!r} is not a note number / name") from None
    return dict(kit)


def _sweep_beats(sweep, style: str, bpb: float) -> float | None:
    if sweep is None:          # half bars (medium, two) or whole bars (ballad, up); a waltz sweeps in 3
        return bpb if (style in ('ballad', 'up') or int(round(bpb)) % 2) else bpb / 2.0
    if sweep is False:
        return None
    named = {'beat': 1.0, 'half': bpb / 2.0, 'bar': bpb, '2bars': 2.0 * bpb}
    if isinstance(sweep, str):
        if sweep not in named:
            raise ComposeError(f"sweep must be 'beat', 'half', 'bar', '2bars', a number of beats or False, "
                               f"got {sweep!r}")
        return named[sweep]
    v = beats(sweep)
    if v <= 0:
        raise ComposeError(f"sweep length must be > 0 beats, got {sweep!r}")
    return v


def brushes(bars: float = 4, style: str = 'medium', kit=None, sweep=None, taps: bool = True, kick='feather',
            hat: bool = True, ride=False, fills: bool = True, phrase: int = 8, fill: str | None = None,
            vel: float = 1.0, seed=0, beats_per_bar: float = 4) -> Clip:
    """Brush-kit groove -> Clip (straight 8ths; swing it with the feel). The recipe's 'seichte' drums:
      sweep   the continuous stir on the snare: one kit['sweep'] note per 'half' bar (medium, two), 'bar' (ballad,
              up), '2bars', 'beat' or a length in beats; each note held until just before the next (GM brush swirl is
              a held loop; a Swirly Drums stir is a one-shot swell - jazz.swirly_sweep(tempo)). False = no sweep.
      taps    the other brush on 2 and 4 (kit['tap']), with seeded ghost taps on the & of 4 / & of 2
      kick    'feather' (very soft on every beat), 'two' (1 and 3), None / 'none'
      hat     hi-hat foot on 2 and 4 (kit['hat_foot'])
      ride    True (or a velocity factor) adds the spang-a-lang ride (see ride_pattern()) and drops the taps - the
              right hand moves to the ride for the hottest chorus
      fills   the last bar of every `phrase` bars ends with a fill (brush_fill: fill= one of FILL_KINDS, else seeded)
    style: medium | ballad | up | two (sets the defaults and levels); beats_per_bar=3 plays a jazz waltz (taps and
    hi-hat on 2 and 3, one sweep per bar); vel scales every level. kit: a dict role -> note: GM_BRUSH (GeneralUser
    'Brush' kit, default) or SWIRLY_BRUSH or your own (roles: sweep tap slap kick hat_foot ride crash tom_lo tom_mid
    tom_hi ...; a list of notes alternates round-robin)."""
    if style not in BRUSH_STYLES:
        raise ComposeError(f"brushes style must be one of {', '.join(BRUSH_STYLES)}, got {style!r}")
    if kick not in ('feather', 'two', 'none', None, False):
        raise ComposeError(f"brushes kick must be 'feather', 'two' or None, got {kick!r}")
    if fill is not None and fill not in FILL_KINDS:
        raise ComposeError(f"brushes fill must be one of {', '.join(FILL_KINDS)} (or None: seeded), got {fill!r}")
    if not _is_int(phrase) or phrase < 1:
        raise ComposeError(f"brushes phrase must be an int >= 1 (bars), got {phrase!r}")
    kit = _check_kit(kit)
    bpb = _real(beats_per_bar, 'brushes beats_per_bar', 1, 16)
    L = _real(bars, 'brushes bars', 0, 4096) * bpb
    if L <= 0:
        raise ComposeError(f"brushes needs bars > 0, got {bars!r}")
    vel = _real(vel, 'brushes vel (a level factor)', 0.0, 4.0)
    if ride is None or ride is False:
        ride_f = None
    else:
        ride_f = 1.0 if ride is True else _real(ride, 'brushes ride (True or a level factor)', 0.0, 4.0)
    if ride_f == 0.0:
        ride_f = None
    rng = random.Random(seed_int(seed))
    sv, tv, kv, hv, ghost_p = _BRUSH_DEFAULTS[style]
    notes: list[Note] = []
    rr: dict[str, int] = {}          # round-robin counter per role (a list of notes alternates)

    def add(t, d, role, v):
        if t < L - _EPS:
            i = rr.get(role, 0)
            rr[role] = i + 1
            notes.append(Note(t, max(0.05, min(d, L - t)), _kit_note(kit, role, i), _vel(v * vel)))
    S = _sweep_beats(sweep, style, bpb)
    if S is not None:
        k = 0
        while k * S < L - _EPS:
            t = k * S
            accent_ = 1.0 if (t % bpb) + S > bpb - _EPS or S >= bpb else 0.9      # the swish into 4 is stronger
            add(t, S - 0.03, 'sweep', sv * accent_ * (1.0 + (rng.random() - 0.5) * 0.08))
            k += 1
    n_bars = int(math.ceil(L / bpb - _EPS))
    fill_bars = {b for b in range(n_bars) if fills and b % phrase == phrase - 1}
    for b in range(n_bars):
        t0 = b * bpb
        fill_len = 0.0
        if b in fill_bars:
            fill_len = 1.0 if style == 'ballad' else 2.0
        backbeats = [1, 2] if int(round(bpb)) == 3 else [x for x in range(int(bpb)) if x % 2 == 1]   # waltz: 2, 3
        if taps and ride_f is None:
            for x in backbeats:
                t = t0 + x
                if t < t0 + bpb - fill_len - _EPS:
                    add(t, 0.25, 'tap', tv * (1.0 + (rng.random() - 0.5) * 0.1))
            for off, pr in ((bpb - 0.5, ghost_p), (1.5, ghost_p * 0.4)):
                t = t0 + off
                if off < bpb and t < t0 + bpb - fill_len - _EPS and rng.random() < pr:
                    add(t, 0.2, 'tap', tv * 0.55)
        if kick in ('feather', 'two'):
            for x in range(int(bpb)):
                if kick == 'two' and x % 2 == 1:
                    continue
                add(t0 + x, 0.25, 'kick', kv * (1.1 if x == 0 else 1.0) * (1.0 + (rng.random() - 0.5) * 0.1))
        if hat:
            for x in backbeats:
                add(t0 + x, 0.2, 'hat_foot', hv * (1.0 + (rng.random() - 0.5) * 0.1))
        if fill_len:
            kind = fill if fill is not None else rng.choice(('triplets', 'eighths', 'slap') if style != 'up'
                                                            else ('triplets', 'eighths', 'toms'))
            f = brush_fill(kind, fill_len, kit=kit, vel=(_clampv(tv * 0.55 * vel), _clampv(tv * 1.15 * vel)))
            at = t0 + bpb - fill_len
            notes.extend(n._replace(start=n.start + at) for n in f if at + n.start < L)
    if ride_f is not None:
        r = ride_pattern(L / bpb, kit=kit, vel=_clampv(72 * ride_f * vel), seed=rng.random(), beats_per_bar=bpb)
        notes.extend(r)
    return Clip._raw(notes, L)


def brush_fill(kind: str = 'triplets', length=2.0, kit=None, vel=(40, 90)) -> Clip:
    """A short brush fill -> Clip of `length` beats (place it at the end of a phrase; brushes() does that itself):
      triplets  taps on 8th-note triplets with a crescendo, the last one a slap
      eighths   taps on the 8ths (swung by the feel), crescendo, slap + kick on the last 8th
      slap      a set-up: a tap on the & before the last beat, then slap + kick on the last 8th
      toms      brushed toms on triplets, high to low
      swell     a soft cymbal roll (ride) swelling into the next downbeat
    vel=(start, end) velocity range."""
    if kind not in FILL_KINDS:
        raise ComposeError(f"unknown brush fill {kind!r}; use one of {', '.join(FILL_KINDS)}")
    kit = _check_kit(kit)
    L = beats(length)
    if L <= 0:
        raise ComposeError("brush_fill needs a length > 0 beats")
    if not isinstance(vel, (tuple, list)) or len(vel) != 2:
        raise ComposeError(f"brush_fill vel must be (start, end) velocities, got {vel!r}")
    v0, v1 = (_real(x, 'brush_fill vel', 1, 127) for x in vel)
    notes: list[Note] = []
    slap_f, kick_f = 0.8, 0.5        # a slap / kick sample is far louder than a tap at the same velocity

    def ramp(x):
        return v0 + (v1 - v0) * x

    def last_hit(k, n):
        return ('slap', slap_f) if (k == n - 1 and 'slap' in kit) else ('tap', 1.0)
    if kind in ('triplets', 'toms'):
        n = int(round(L * 3))
        toms = [r for r in ('tom_hi', 'tom_mid', 'tom_lo') if r in kit] or ['tap']
        for k in range(n):
            t = k / 3.0
            x = k / max(1, n - 1)
            if kind == 'toms':
                role, f = toms[min(len(toms) - 1, k * len(toms) // n)], 0.9
            else:
                role, f = last_hit(k, n)
            notes.append(Note(t, 0.2, _kit_note(kit, role, k), _vel(ramp(x) * f)))
    elif kind == 'eighths':
        n = int(round(L * 2))
        for k in range(n):
            role, f = last_hit(k, n)
            notes.append(Note(k * 0.5, 0.2, _kit_note(kit, role, k), _vel(ramp(k / max(1, n - 1)) * f)))
        if 'kick' in kit:
            notes.append(Note((n - 1) * 0.5, 0.25, _kit_note(kit, 'kick'), _vel(v1 * kick_f)))
    elif kind == 'slap':
        if L >= 1.0:
            notes.append(Note(L - 1.5 if L >= 1.5 else 0.0, 0.2, _kit_note(kit, 'tap'), _vel(v0)))
        role = 'slap' if 'slap' in kit else 'tap'
        notes.append(Note(L - 0.5, 0.25, _kit_note(kit, role), _vel(v1 * (slap_f if role == 'slap' else 1.0))))
        if 'kick' in kit:
            notes.append(Note(L - 0.5, 0.25, _kit_note(kit, 'kick'), _vel(v1 * kick_f)))
    else:   # swell
        n = int(round(L * 6))
        for k in range(n):
            x = (k / max(1, n - 1)) ** 1.5
            notes.append(Note(k / 6.0, 0.3, _kit_note(kit, 'ride', k), _vel(v0 * 0.5 + (v1 - v0 * 0.5) * x)))
    return Clip._raw(notes, L)


RIDE_PATTERNS = ('spang', 'quarters', 'two', 'broken')


def ride_pattern(bars: float = 4, pattern: str = 'spang', kit=None, vel: float = 72, accent: float = 1.12,
                 variation: float = 0.15, seed=0, beats_per_bar: float = 4) -> Clip:
    """Ride cymbal time -> Clip (straight 8ths: the feel swings the skip notes).
      spang     spang-a-lang: 1, 2 &, 3, 4 & - the jazz ride (quarters, the skip note on the & of 2 and 4: swung,
                it leads into 3 and 1)
      quarters  four on the floor of the cymbal (up-tempo)
      two       1 and 3 (ballads, two-feel)
      broken    spang-a-lang with seeded gaps and extra skips (solo-chorus looseness)
    accent = beats 2 and 4 heavier (the ride and the hi-hat foot lock there); variation = chance per bar of a dropped
    or added skip note (seeded)."""
    if pattern not in RIDE_PATTERNS:
        raise ComposeError(f"ride pattern must be one of {', '.join(RIDE_PATTERNS)}, got {pattern!r}")
    kit = _check_kit(kit)
    variation = _unit(variation, 'ride variation')
    vel = _real(vel, 'ride_pattern vel', 1, 127)
    accent = _real(accent, 'ride_pattern accent', 0.5, 2.0)
    bpb = _real(beats_per_bar, 'ride_pattern beats_per_bar', 1, 16)
    L = _real(bars, 'ride_pattern bars', 0, 4096) * bpb
    if L <= 0:
        raise ComposeError(f"ride_pattern needs bars > 0, got {bars!r}")
    rng = random.Random(seed_int(seed))
    notes: list[Note] = []
    n_bars = int(math.ceil(L / bpb - _EPS))
    for b in range(n_bars):
        t0 = b * bpb
        if pattern == 'two':
            hits = [(x, 1.0) for x in range(0, int(bpb), 2)]
        elif pattern == 'quarters':
            hits = [(x, 1.0) for x in range(int(bpb))]
        else:
            hits = [(x, 1.0) for x in range(int(bpb))] + [(x + 0.5, 0.62) for x in range(1, int(bpb), 2)]
            if pattern == 'broken' or rng.random() < variation:
                if rng.random() < 0.5:
                    skips = [h for h in hits if h[0] % 1]
                    if skips:
                        hits.remove(rng.choice(skips))
                else:
                    hits.append((rng.choice([x + 0.5 for x in range(0, int(bpb), 2)]), 0.55))
        for pos, lvl in sorted(hits):
            t = t0 + pos
            if t >= L - _EPS:
                continue
            a = accent if abs(pos - round(pos)) < _EPS and int(round(pos)) % 2 == 1 else 1.0
            v = vel * lvl * a * (1.0 + (rng.random() - 0.5) * 0.08)
            notes.append(Note(t, 0.5 if lvl >= 1.0 else 0.3, _kit_note(kit, 'ride', int(pos * 2)), _vel(v)))
    return Clip._raw(notes, L)
