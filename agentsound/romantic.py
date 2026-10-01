"""The romantic pianist: what a Chopin nocturne asks of a player that the jazz pianist (pianist.py) does not do.

Found by the Nocturne op. 9 no. 2 etude (songs/nocturne-etude, NOTES.md has the numbers against a concert
recording). A written-out score played by the plain tools sounds like a sequencer reading it: the fioriture tick
at one speed, the ornaments are on the grid, the melody sits on the left hand's beat, a long singing note is
followed by a note that bangs out of its decay, the accompaniment is as loud as the tune. This module plays the
score instead:

    from agentsound import romantic as rom
    run = rom.fioritura(['Db6', 'C6', 'B5', 'Bb5', 'A5', 'Ab5'], 1.5, bpm=48, at=4.0, shape='arch')
    tr = rom.trill('F5', 1.5, bpm=48, key=s.key, start='upper', land='G5')
    lh = rom.accompany([(0, 1.5, 'Eb2', ['Bb3', 'Eb4', 'G4']), ...], bpm=48)      # bass + chord + chord in 12/8
    rh = rom.cantabile(rh, bpm=48)                         # the legato illusion: no note bangs out of a decay
    rh = rom.dynamics(rh, [(0, 'p'), (6, 'mf'), (12, 'p')])                          # hairpins
    rh = rom.melody_rubato(rh, anchors=range(0, 48, 6), bpm=48, seed=2)              # the tune leans, the LH keeps time
    piano.automate('instrument.pedal', rom.pedal_changes([0, 1.5, 3, 4.5], end=6))    # legato pedal per harmony

Every function is deterministic (seeded) and returns a Clip / points; times are beats, speeds in real time (the
tempo `bpm` may be a number or a function beat -> BPM, e.g. song.tempo_at, so a ritardando slows a trill in
beats but not in notes per second).

Measured targets (the recording the etude compared against, a concert pianist):
  fioriture     11-22 notes in 1-2 beats, 8-14 notes/s, the middle ~1.6-2x faster than the ends, lighter in the
                middle (4-6 dB), the landing note on time
  trills        12-15 notes/s after a slower start (~8/s), ending in a turn (Nachschlag) into the next note
  melody vs LH  the singing note on a strong beat 20-60 ms after the bass, peaks held back 40-90 ms; the left
                hand steady (its own drift only from the tempo map)
  voicing       the melody 8-12 dB over the accompaniment chords, the bass between the two
"""

from __future__ import annotations

import math
import random

from .patterns import Clip, Note, _vel, as_clip, seed_int
from .theory import ComposeError, Key, note

__all__ = ['SHAPES', 'LEVELS', 'fioritura', 'grace', 'turn', 'trill', 'accompany', 'lean_on_long', 'cantabile',
           'dynamics', 'melody_rubato', 'pedal_changes', 'decay_db', 'figure_stats', 'score', 'Score', 'Event']

_EPS = 1e-6

SHAPES = ('arch', 'accel', 'rit', 'even', 'wave')
"""fioritura timing shapes: 'arch' (out of the principal slowly, fastest in the middle, broadening into the
landing), 'accel' (faster and faster), 'rit' (slowing down), 'even', 'wave' (two surges)."""

LEVELS = {'ppp': 0.45, 'pp': 0.55, 'p': 0.7, 'mp': 0.85, 'mf': 1.0, 'f': 1.15, 'ff': 1.3, 'fff': 1.42}
"""Velocity factors of the dynamic marks for dynamics() (mf = the written level)."""


# ------------------------------------------------------------------------------------------------ helpers

def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        rng = f"{lo:g}.." if hi is None else f"..{hi:g}" if lo is None else f"{lo:g}..{hi:g}"
        raise ComposeError(f"{what} = {x:g} is outside {rng}")
    return float(x)


def _bpm_at(bpm, beat: float) -> float:
    v = bpm(beat) if callable(bpm) else bpm
    return _num(v, 'bpm', 1, 1000)


def _beats(seconds: float, bpm, at: float) -> float:
    return seconds * _bpm_at(bpm, at) / 60.0


def _pos(at) -> float:
    if hasattr(at, 'start') and not isinstance(at, (int, float)):
        return float(at.start)
    return _num(at, 'at (beats)', 0)


def _vels(vel) -> tuple[float, float]:
    if isinstance(vel, (tuple, list)):
        if len(vel) != 2:
            raise ComposeError(f"vel must be a number or (from, to), got {vel!r}")
        return _num(vel[0], 'vel', 1, 127), _num(vel[1], 'vel', 1, 127)
    v = _num(vel, 'vel', 1, 127)
    return v, v


def _clip(notes) -> Clip:
    ns = [Note(float(s), float(max(0.02, d)), int(p), _vel(v)) for s, d, p, v in notes]
    end = max((n.start + n.dur for n in ns), default=0.0)
    return Clip._raw(ns, float(math.ceil(end - _EPS)) if end > 0 else 0.0)


def _weights(shape: str, n: int, ease: float) -> list[float]:
    """Relative durations of n notes of a figure (normalized later): large = slow."""
    if shape not in SHAPES:
        raise ComposeError(f"fioritura shape must be one of {', '.join(SHAPES)}, got {shape!r}")
    out = []
    for i in range(n):
        x = (i + 0.5) / n
        if shape == 'arch':
            w = 1.0 + ease * (0.5 + 0.5 * math.cos(2.0 * math.pi * x))      # slow ends, fast middle
        elif shape == 'accel':
            w = 1.0 + ease * (1.0 - x) * 1.5
        elif shape == 'rit':
            w = 1.0 + ease * x * 1.5
        elif shape == 'wave':
            w = 1.0 + ease * (0.5 + 0.5 * math.cos(4.0 * math.pi * x))
        else:
            w = 1.0
        out.append(w)
    return out


# ------------------------------------------------------------------------------------------------ fioriture

def fioritura(pitches, dur, bpm, *, at=0.0, shape: str = 'arch', ease: float = 0.8, vel=(70, 66),
              dip: float = 6.0, sing: float = 0.4, legato: float = 1.2, land=None, land_dur: float = 1.0,
              land_vel=None, max_rate: float = 24.0, wobble_ms: float = 4.0, seed=0) -> Clip:
    """A Chopin fioritura: the written notes `pitches` (any line - chromatic, scale, arpeggio, turns - in order)
    played as ONE free gesture in `dur` beats from `at`, not as a row of equal notes: timed by `shape` (SHAPES;
    'arch' = leaves the principal slowly, fastest in the middle, broadens into the landing; `ease` 0..1.5 how much
    slower the ends are - at 0.8 the first / last notes last ~1.8x the middle ones), velocity from vel[0] to vel[1]
    sinking by `dip` velocity in the middle (lighter), higher notes singing out by `sing` velocity per semitone
    above the figure's mean, the notes overlapping (`legato` x the gap: finger legato), a few ms of seeded wobble.
    `land` = the landing note, struck exactly at at + dur (the beat the figure leads into) for `land_dur` beats at
    `land_vel` (default vel[1] + dip/2) - leave it None when the melody's next note is written separately.
    Real-time speed: more than `max_rate` notes per second is an error (a written figure is never thinned)."""
    ps = [note(p) for p in pitches]
    if not ps:
        raise ComposeError("fioritura needs at least one pitch")
    D = _num(dur, 'fioritura dur (beats)', 0.05)
    a = _pos(at)
    e = _num(ease, 'fioritura ease', 0, 1.5)
    v0, v1 = _vels(vel)
    dp = _num(dip, 'fioritura dip (velocity)', 0, 40)
    lg = _num(legato, 'fioritura legato', 0.5, 2.5)
    secs = D * 60.0 / _bpm_at(bpm, a)
    w = _weights(shape, len(ps), e)
    tot = sum(w)
    fastest = max(tot / (x * max(secs, _EPS)) for x in w)
    if fastest > _num(max_rate, 'fioritura max_rate', 2, 60) + _EPS:
        raise ComposeError(f"fioritura: {len(ps)} notes in {secs:.2f} s run at up to {fastest:.1f} notes/s "
                           f"(max_rate {max_rate:g}); give it more time (dur) or a flatter shape (ease)")
    rng = random.Random(seed_int(seed))
    mean_p = sum(ps) / len(ps)
    out = []
    t = 0.0
    n = len(ps)
    for i, p in enumerate(ps):
        d = D * w[i] / tot
        x = i / max(1, n - 1)
        v = v0 + (v1 - v0) * x - dp * math.sin(math.pi * x) + sing * (p - mean_p)
        wob = 0.0 if i == 0 else (rng.random() * 2 - 1) * _beats(wobble_ms / 1000.0, bpm, a + t)
        wob = max(-0.3 * d, min(0.3 * d, wob))
        out.append((a + t + wob, d * lg, p, v))
        t += d
    if land is not None:
        lv = v1 + dp / 2 if land_vel is None else _num(land_vel, 'land_vel', 1, 127)
        out.append((a + D, _num(land_dur, 'land_dur', 0.05), note(land), lv))
    return _clip(out)


def grace(pitches, target, dur, bpm, *, at=0.0, ms: float = 65.0, on_beat: bool = False, vel=78,
          light: float = 16.0, legato: float = 1.3) -> Clip:
    """Grace notes (appoggiature / a written-out turn in small notes) into `target`: `pitches` each `ms` long (one
    real-time value: 45-90 ms), then the target note at `vel` for `dur` beats. Before the beat by default (the
    graces take their time from the note before - the target lands on `at`), or on_beat=True (the graces start on
    `at`, the target is delayed by them and shortened). The graces play `light` velocity under the target,
    legato."""
    gs = [note(p) for p in pitches]
    tp = note(target)
    D = _num(dur, 'grace dur (beats)', 0.05)
    a = _pos(at)
    s = _beats(_num(ms, 'grace ms', 10, 400) / 1000.0, bpm, a)
    v = _num(vel, 'grace vel', 1, 127)
    lt = _num(light, 'grace light', 0, 80)
    k = len(gs)
    g0 = a if on_beat else a - k * s
    if g0 < -_EPS:
        raise ComposeError(f"grace: {k} grace notes of {ms:g} ms before beat {a:g} start before 0; use on_beat=True")
    out = [(max(0.0, g0 + i * s), s * _num(legato, 'grace legato', 0.5, 3), q, max(12.0, v - lt * (1.0 - 0.2 * i / max(1, k))))
           for i, q in enumerate(gs)]
    t0 = g0 + k * s
    if D - (t0 - a) < 0.05:
        raise ComposeError("grace: on_beat graces take longer than the target note")
    out.append((t0, D - (t0 - a), tp, v))
    return _clip(out)


def turn(pitch, dur, bpm, *, at=0.0, key=None, inverted: bool = False, where: str = 'after', ms: float = 75.0,
         vel=78, light: float = 18.0, upper=None, lower=None) -> Clip:
    """The classical turn (gruppetto), Chopin's way: where='after' - the note, then (late in its value) upper,
    note, lower, note leading into what follows (the turn between two notes); where='on' - upper, note, lower, note
    on the beat. Neighbours from the key (scale steps; the lower one a half step when `lower` says so: lower=-1),
    or `upper` / `lower` in semitones. The figure `light` under the principal, legato, `ms` per note."""
    p = note(pitch)
    D = _num(dur, 'turn dur (beats)', 0.1)
    a = _pos(at)
    k = Key(key) if isinstance(key, str) else key
    if upper is not None:
        up = p + int(upper)
    elif k is not None:
        up = next(q for q in range(p + 1, p + 3) if k.contains(q))
    else:
        up = p + 2
    if lower is not None:
        lo = p + int(lower)
    elif k is not None:
        lo = next(q for q in range(p - 1, p - 3, -1) if k.contains(q))
    else:
        lo = p - 1
    s = _beats(_num(ms, 'turn ms', 20, 300) / 1000.0, bpm, a)
    v = _num(vel, 'turn vel', 1, 127)
    fig = [lo, p, up, p] if inverted else [up, p, lo, p]
    if where == 'on':
        if 4 * s >= D:
            raise ComposeError("turn: the note is too short for a turn on the beat")
        out = [(a + i * s, s * 1.25, q, v - (0.0 if i == 0 else light * 0.8)) for i, q in enumerate(fig[:-1])]
        out.append((a + 3 * s, D - 3 * s, p, v - light * 0.3))
        return _clip(out)
    if where != 'after':
        raise ComposeError(f"turn where must be 'after' or 'on', got {where!r}")
    t0 = a + D - 4 * s
    if t0 <= a + 0.05:
        raise ComposeError("turn: the note is too short for a turn after it")
    out = [(a, t0 - a + s * 0.3, p, v)]
    for i, q in enumerate(fig):
        out.append((t0 + i * s, s * 1.25, q, max(12.0, v - light * (0.9 if i else 0.7))))
    return _clip(out)


def trill(pitch, dur, bpm, *, at=0.0, key=None, upper=None, lower=None, start: str = 'main', rate: float = 12.0,
          start_rate: float | None = None, end_rate: float | None = None, grow: float = 0.35, settle: float = 0.3,
          termination: bool = True, land=None, land_dur: float = 1.0, prefix=None, vel=80, light: float = 22.0,
          fade: float = 6.0, legato: float = 1.2, wobble_ms: float = 4.0, seed=0) -> Clip:
    """A classical trill that begins and ends properly: `start` 'main' (the note, then the upper neighbour -
    Chopin's usual start), 'upper' (the upper note first, on the beat: the classical appoggiatura start) or
    'lower' (a lower-neighbour prefix into it); `prefix` = explicit notes before the first alternation. Shaped like
    a player's: it starts at `start_rate` (default 0.55 x rate) and speeds up over the first `grow` of its length to
    `rate` notes/s (12-15 for a real trill), holds it, and settles over the last `settle` to `end_rate` (default
    0.7 x rate) into the termination (Nachschlag: lower neighbour, main, at end_rate) that leads into `land`
    (struck at at + dur, `land_dur` beats) - or, without `land`, onto the main note held softly to the end of
    `dur`. Played light (`light` velocity under the principal, fading `fade` to its end). Neighbours from `key`
    (scale steps) or `upper` / `lower` semitones (lower=-1: the chromatic Nachschlag, F5 trill ending E5 F5). Measured on the recording the etude compared with: ~10.5 notes/s overall,
    the ends ~1.7x slower than the middle (an even 14/s trill reads as a buzz)."""
    p = note(pitch)
    D = _num(dur, 'trill dur (beats)', 0.2)
    a = _pos(at)
    if start not in ('main', 'upper', 'lower'):
        raise ComposeError(f"trill start must be 'main', 'upper' or 'lower', got {start!r}")
    k = Key(key) if isinstance(key, str) else key
    if upper is not None:
        up = p + int(upper)
    elif k is not None:
        up = next(q for q in range(p + 1, p + 3) if k.contains(q))
    else:
        up = p + 2
    if lower is not None:
        lo = p + int(lower)
    else:
        lo = next((q for q in range(p - 1, p - 3, -1) if k.contains(q)), p - 1) if k is not None else p - 1
    r1 = _num(rate, 'trill rate (notes/s)', 4, 30)
    r0 = 0.55 * r1 if start_rate is None else _num(start_rate, 'trill start_rate', 2, 30)
    r2 = 0.7 * r1 if end_rate is None else _num(end_rate, 'trill end_rate', 2, 30)
    gw = _num(grow, 'trill grow', 0, 0.9)
    st = _num(settle, 'trill settle', 0, 0.9)
    v0 = _num(vel, 'trill vel', 1, 127)
    lt = _num(light, 'trill light', 0, 80)
    fd = _num(fade, 'trill fade', 0, 60)
    lg = _num(legato, 'trill legato', 0.5, 2.5)
    rng = random.Random(seed_int(seed))
    held = 0.0 if land is not None else min(0.4 * D, max(0.0, D - _beats(1.6, bpm, a)))
    body = D - held

    def rate_at(x):
        if gw > 0 and x < gw:
            return r0 + (r1 - r0) * (0.5 - 0.5 * math.cos(math.pi * x / gw))
        if st > 0 and x > 1.0 - st:
            return r1 + (r2 - r1) * (0.5 - 0.5 * math.cos(math.pi * (x - 1.0 + st) / st))
        return r1

    seq = [note(q) for q in (prefix or [])]
    if start == 'lower' and not seq:
        seq = [lo]
    first = up if start == 'upper' else p
    tail = [lo, p] if termination else []
    notes, t, i = [], 0.0, 0
    for q in seq:
        s = _beats(1.0 / r0, bpm, a + t)
        notes.append((t, s, q))
        t += s
    alt = [first, p if first == up else up]
    tail_t = sum(_beats(1.0 / r2, bpm, a + body) for _ in tail)
    while True:
        s = _beats(1.0 / rate_at(min(1.0, t / max(body - tail_t, _EPS))), bpm, a + t)
        q = alt[i % 2]
        # the termination follows a MAIN note: stop before an upper note when the rest would not fit
        if t + s + tail_t > body + _EPS and i >= 2 and q == up:
            break
        if t + s > body + _EPS and i >= 2:
            break
        notes.append((t, s, q))
        t += s
        i += 1
    for q in tail:
        s = _beats(1.0 / r2, bpm, a + t)
        notes.append((t, s, q))
        t += s
    scale = body / max(t, _EPS)                   # fit exactly into the body
    out = []
    n = len(notes)
    for j, (tt, s, q) in enumerate(notes):
        y = j / max(1, n - 1)
        if j == 0:
            v = v0
        else:
            v = v0 - lt * (1.0 - 0.25 * math.sin(math.pi * y)) - fd * y - (2.0 if q == up else 0.0)
        wob = 0.0 if j == 0 else (rng.random() * 2 - 1) * _beats(wobble_ms / 1000.0, bpm, a + tt)
        out.append((a + tt * scale + max(-0.25 * s, min(0.25 * s, wob)), s * scale * lg, q, max(12.0, v)))
    if land is not None:
        out.append((a + D, _num(land_dur, 'land_dur', 0.05), note(land), v0))
    else:
        out.append((a + body, max(0.05, held), p, max(12.0, v0 - lt * 0.5)))
    return _clip(out)


# ------------------------------------------------------------------------------------------------ left hand

def accompany(beats, bpm, *, pattern: str = 'bcc', step: float = 0.5, vel: float = 40, bass: float = 1.2,
              first: float = 1.0, second: float = 0.9, top: float = 1.05, roll_ms: float = 12.0,
              breathe: float = 0.06, phrase: float = 12.0, hold_bass: bool = True, jitter_ms: float = 5.0,
              seed=0) -> Clip:
    """The nocturne left hand: per entry of `beats` - (start, length, bass, chord[, chord2]) in beats, bass a
    pitch, chord a list - the `pattern` in `step` beats ('bcc' = bass, chord, chord: the 12/8 nocturne figure; 'bc'
    6/8 halves, 'bccccc' a waltz bar, 'b' just the bass, 'c' chords only; '.' rest), repeated to fill the length.
    'B' strikes the bass and the chord together (the chord rolled up from the bass) and holds both to the end of
    the entry. Touch: chords at `vel` (the second strike x `second`, the first x `first`), the bass x `bass` (it carries the
    harmony), the chord's top voice x `top`, the chord slightly rolled (`roll_ms` total, bottom up), a slow swell
    over each `phrase` beats (+-`breathe`), a few ms of seeded jitter (the left hand is the steady one). The bass
    rings to the end of its entry when hold_bass (the pedal catches it anyway); chord notes last one step (legato
    to the next strike). chord2 = the chord for the later strikes (voice-leading inside a beat)."""
    b0 = _num(vel, 'accompany vel', 1, 127)
    st = _num(step, 'accompany step (beats)', 0.05, 4)
    if not pattern or set(pattern) - set('bcB.'):
        raise ComposeError(f"accompany pattern: letters b (bass), c (chord), B (bass + chord held), . (rest), "
                           f"got {pattern!r}")
    rng = random.Random(seed_int(seed))
    out = []
    ph = _num(phrase, 'accompany phrase (beats)', 0.5)
    for entry in beats:
        if len(entry) not in (4, 5):
            raise ComposeError(f"accompany entry {entry!r}: use (start, length, bass, chord[, chord2])")
        s0, L = _num(entry[0], 'entry start', 0), _num(entry[1], 'entry length', 0.05)
        bp = None if entry[2] is None else note(entry[2])
        ch1 = [note(q) for q in (entry[3] or [])]
        ch2 = [note(q) for q in (entry[4] or [])] if len(entry) == 5 else ch1
        n = max(1, int(round(L / st)))
        chord_i = 0
        for i in range(n):
            t = s0 + i * st
            if t >= s0 + L - _EPS:
                break
            c = pattern[i % len(pattern)]
            sw = 1.0 + breathe * math.sin(2.0 * math.pi * ((t % ph) / ph) - math.pi / 2)
            jit = (rng.random() * 2 - 1) * _beats(jitter_ms / 1000.0, bpm, t)
            if c in 'bB' and bp is not None:
                d = (s0 + L - t) if (hold_bass or c == 'B') else st
                out.append((max(0.0, t + (jit if i else 0.0)), d, bp, b0 * bass * sw))
            if c == 'B':                            # a held chord (rolled up from the bass): endings, fermatas
                roll = _beats(3 * roll_ms / 1000.0, bpm, t) / max(1, len(ch1))
                for j, q in enumerate(sorted(ch1)):
                    vv = b0 * first * sw * (top if q == max(ch1) else 1.0)
                    out.append((t + (j + 1) * roll, max(st, s0 + L - t - (j + 1) * roll), q, vv))
            elif c == 'c':
                ch = ch1 if chord_i == 0 else ch2
                f = first if chord_i == 0 else second
                chord_i += 1
                roll = _beats(roll_ms / 1000.0, bpm, t) / max(1, len(ch) - 1)
                for j, q in enumerate(sorted(ch)):
                    vv = b0 * f * sw * (top if q == max(ch) else 1.0) * (1.0 + (rng.random() - 0.5) * 0.06)
                    out.append((max(0.0, t + jit + j * roll), st * 1.02, q, vv))
    return _clip(out)


# ------------------------------------------------------------------------------------------------ the singing line

def decay_db(pitch, seconds: float) -> float:
    """How far (dB) a held piano note has decayed after `seconds`: fast at first, then slower, faster in the
    treble (about 7 dB after 1 s and 11 dB after 2.5 s at C5, a third less an octave lower). A model for the
    legato illusion, not a measurement of one sample set."""
    p = note(pitch)
    t = max(0.0, float(seconds))
    rate = 11.0 * 2.0 ** ((p - 72) / 24.0)
    return rate * t / (1.0 + t / 1.6)


def lean_on_long(clip: Clip, bpm, *, gain: float = 10.0, full: float = 1.6, min_s: float = 0.45,
                 cap: float = 118.0) -> Clip:
    """Weight by length: a singing pianist gives a long melody note more tone - it has to carry through its own
    decay (the opening G of the nocturne sings for three seconds) - while the short notes around it stay light.
    Each top-voice note held `min_s` seconds or longer gains up to `gain` velocity (in full at `full` seconds and
    more, linearly from min_s); notes under it (octaves, chords) move with it; never above `cap`. touch() shapes
    the phrase by pitch and position only; apply this after it and before cantabile()."""
    g = _num(gain, 'lean_on_long gain (velocity)', 0, 40)
    fu = _num(full, 'lean_on_long full (s)', 0.1)
    ms = _num(min_s, 'lean_on_long min_s (s)', 0)
    cp = _num(cap, 'lean_on_long cap', 1, 127)
    ns = sorted(clip, key=lambda n: (n.start, -n.pitch))
    tops = []
    for n in ns:
        if not tops or abs(n.start - tops[-1].start) >= 0.02:
            tops.append(n)
    add = {}
    for i, n in enumerate(tops):
        nxt = tops[i + 1].start if i + 1 < len(tops) else n.start + n.dur
        secs = min(n.dur, max(0.0, nxt - n.start)) * 60.0 / _bpm_at(bpm, n.start)
        if secs >= ms:
            add[round(n.start, 3)] = g * min(1.0, (secs - ms) / max(_EPS, fu - ms))
    out = []
    for n in ns:
        d = add.get(round(n.start, 3), 0.0)
        out.append(n._replace(vel=_vel(min(cp, n.vel + d))) if d else n)
    return Clip._raw(out, clip.length)


def cantabile(clip: Clip, bpm, *, match: float = 0.35, lift: float = 5.0, db_per_vel: float = 0.25,
              floor: float = 0.72, min_hold: float = 1.0, gap: float = 0.26, fast: float = 0.18) -> Clip:
    """The legato illusion on a melody (the top voice of `clip`): a piano note dies away, so a singer's line on the
    piano plays the note after a long one softer - it continues the decayed tone instead of banging out of it.
    For each melody note after a note held at least `min_hold` seconds, its velocity is capped at the previous
    note's velocity minus `match` x its decay (decay_db over its sounding time, in velocity via `db_per_vel`) plus
    `lift` velocity (a rising line may grow a little), never below `floor` x its written velocity. Notes after a
    rest of `gap` beats or more start a new phrase (not capped). Ornaments move as one: notes less than `fast`
    seconds apart (a trill, a turn, a fioritura and the note it lands on) form a group whose first note is judged
    and whose other notes keep their level relative to it (a trill never plays louder than its principal). Notes
    under the top voice follow their top note."""
    m = _num(match, 'cantabile match', 0, 1)
    lf = _num(lift, 'cantabile lift (velocity)', -20, 40)
    dpv = _num(db_per_vel, 'cantabile db_per_vel', 0.05, 2)
    fl = _num(floor, 'cantabile floor', 0.3, 1)
    mh = _num(min_hold, 'cantabile min_hold (s)', 0)
    fs = _num(fast, 'cantabile fast (s)', 0)
    ns = sorted(clip, key=lambda n: (n.start, -n.pitch))
    tops, others = [], []
    for n in ns:
        if tops and abs(n.start - tops[-1].start) < 0.02:
            others.append(n)
        else:
            tops.append(n)

    def secs(a, b):
        return (b - a) * 60.0 / _bpm_at(bpm, a)
    groups, i = [], 0
    while i < len(tops):
        g = [i]
        while i + 1 < len(tops) and secs(tops[i].start, tops[i + 1].start) < fs:
            i += 1
            g.append(i)
        groups.append(g)
        i += 1
    factor = {}
    prev, prev_v = None, None
    for g in groups:
        n = tops[g[0]]
        v = float(n.vel)
        if prev is not None:
            rest = n.start - (prev.start + prev.dur)
            held = secs(prev.start, prev.start + min(prev.dur, n.start - prev.start))
            if rest < gap and held >= mh:
                cap = prev_v - m * decay_db(prev.pitch, held) / dpv + lf
                v = max(fl * n.vel, min(v, cap))
        f = v / max(1.0, float(n.vel))
        for j in g:
            factor[id(tops[j])] = f
        last = tops[g[-1]]
        prev, prev_v = last, last.vel * f
    top_at = {round(n.start, 3): factor[id(n)] for n in tops}
    out = [n._replace(vel=_vel(n.vel * factor[id(n)])) for n in tops]
    for n in others:
        out.append(n._replace(vel=_vel(n.vel * top_at.get(round(n.start, 3), 1.0))))
    return Clip._raw(out, clip.length)


def dynamics(clip: Clip, marks, *, curve: str = 'smooth', at: float = 0.0) -> Clip:
    """Dynamic marks and hairpins: `marks` = [(beat, level[, 'step'])] with level a mark of LEVELS ('pp' .. 'ff')
    or a velocity factor; between two marks the factor moves (a hairpin: 'smooth' cosine or 'linear'), a 'step'
    mark changes at once (subito). Beats relative to `at` (the clip's placement). Before the first / after the last
    mark their level holds. Every note's velocity x the factor at its start."""
    if curve not in ('smooth', 'linear'):
        raise ComposeError(f"dynamics curve must be 'smooth' or 'linear', got {curve!r}")
    pts = []
    for m in marks:
        if len(m) not in (2, 3):
            raise ComposeError(f"dynamics mark {m!r}: use (beat, level) or (beat, level, 'step')")
        lv = LEVELS.get(m[1]) if isinstance(m[1], str) else _num(m[1], 'dynamics factor', 0.1, 3)
        if lv is None:
            raise ComposeError(f"unknown dynamic {m[1]!r}; use one of {', '.join(LEVELS)} or a factor")
        pts.append((_num(m[0], 'mark beat') - at, lv, len(m) == 3 and m[2] == 'step'))
    if not pts:
        return clip
    f = dynamics_factor(pts, curve)
    return Clip._raw([n._replace(vel=_vel(n.vel * f(n.start))) for n in clip], clip.length)


def dynamics_factor(points, curve: str = 'smooth'):
    """The level function of dynamics(): points = [(beat, factor, step)] -> f(beat). Between two points the factor
    moves ('smooth' cosine or 'linear' - a hairpin) unless the later point is a step (it changes at once there);
    before the first / after the last point their factor holds. (The notation's dynamics use it too.)"""
    if curve not in ('smooth', 'linear'):
        raise ComposeError(f"dynamics curve must be 'smooth' or 'linear', got {curve!r}")
    pts = sorted(points, key=lambda p: p[0])
    if not pts:
        raise ComposeError("dynamics_factor needs at least one point")

    def f(b):
        if b <= pts[0][0]:
            return pts[0][1]
        for (b0, l0, _), (b1, l1, stp) in zip(pts, pts[1:]):
            if b < b1:
                if stp:
                    return l0
                u = (b - b0) / max(_EPS, b1 - b0)
                if curve == 'smooth':
                    u = 0.5 - 0.5 * math.cos(math.pi * u)
                return l0 + (l1 - l0) * u
        return pts[-1][1]
    return f


# ------------------------------------------------------------------------------------------------ rubato

def melody_rubato(clip: Clip, anchors, bpm, *, lean_ms: float = 35.0, late_ms: float = 6.0,
                  sync_ms: float = 32.0, agogic_ms: float = 50.0, leap: int = 5, peak_ms: float = 40.0,
                  free_ms: float = 10.0, legato: float = 0.03, seed=0) -> Clip:
    """Tempo rubato the Chopin way: the MELODY moves freely while the left hand keeps time (the hand that plays
    the accompaniment is the conductor). Only `clip` (the right hand) is moved; the tempo map stays the LH's.
    Between two `anchors` (beats: bar lines, half bars) every onset gets an offset in real time:
      lean       a smooth push-pull over the span: up to `lean_ms` ahead in its first half, behind in its
                 second half (the line hurries into the middle and takes its time into the next anchor), seeded
                 in depth per span
      sync       a long melody note on an anchor (a downbeat) is NOT struck with the bass: `late_ms` after it on
                 average, spread by a seeded +-`sync_ms` (about the standard deviation) either way - the melody
                 sometimes anticipates the harmony, mostly floats just after it (the recording: the melody vs
                 bass offset at the bar lines spreads 47 ms, a lock-step render 8 ms)
      agogic     a note after a leap of `leap`+ semitones is held back up to `agogic_ms` (x leap / 12), a local
                 summit (2+ semitones over both neighbours, 0.4 s or longer) `peak_ms`
      free       +-`free_ms` of seeded irregularity
    The offsets never reorder the notes (at most 40 % of the time to the neighbours); notes sounding together
    (chords, octaves) move together; afterwards every melody note is re-tied to the next onset (+`legato` beats)
    unless a rest follows. `bpm` is a number or a function beat -> BPM (song.tempo_at)."""
    anc = sorted({_num(float(x), 'anchor beat') for x in anchors})
    if len(anc) < 2:
        raise ComposeError("melody_rubato needs at least two anchors (the spans the melody may lean inside)")
    rng = random.Random(seed_int(seed))
    groups: dict[float, list[Note]] = {}
    for n in clip:
        key = round(n.start, 3)
        groups.setdefault(key, []).append(n)
    starts = sorted(groups)
    if not starts:
        return clip
    tops = [max(groups[s], key=lambda n: n.pitch) for s in starts]
    span_depth = {i: 0.55 + 0.45 * rng.random() for i in range(len(anc))}
    offs = []
    for i, s in enumerate(starts):
        n = tops[i]
        j = max(0, min(len(anc) - 2, max((k for k in range(len(anc)) if anc[k] <= s + _EPS), default=0)))
        a0, a1 = anc[j], anc[j + 1]
        u = min(1.0, max(0.0, (s - a0) / max(_EPS, a1 - a0)))
        ms = -lean_ms * span_depth[j] * math.sin(2.0 * math.pi * u)
        secs = n.dur * 60.0 / _bpm_at(bpm, s)
        on_anchor = any(abs(s - x) < 0.02 for x in anc)
        if on_anchor:
            g = max(-2.0, min(2.0, rng.gauss(0.0, 1.0)))
            ms = (late_ms + sync_ms * g) * min(1.0, secs / 0.8) if secs >= 0.3 else 0.0
        if i > 0:
            lp = abs(n.pitch - tops[i - 1].pitch)
            if lp >= leap:
                ms += agogic_ms * min(1.0, lp / 12.0)
        if 0 < i < len(tops) - 1 and secs >= 0.4 and n.pitch >= tops[i - 1].pitch + 2                 and n.pitch >= tops[i + 1].pitch + 2:
            ms += peak_ms
        ms += (rng.random() * 2 - 1) * free_ms
        offs.append(_beats(ms / 1000.0, bpm, s))
    # keep the order: at most 40 % of the distance to each neighbour
    moved = []
    for i, s in enumerate(starts):
        lo = (starts[i - 1] - s) * 0.4 if i > 0 else -0.25
        hi = (starts[i + 1] - s) * 0.4 if i + 1 < len(starts) else 0.25
        moved.append(s + max(lo, min(hi, offs[i])))
    out = []
    for i, s in enumerate(starts):
        nxt = moved[i + 1] if i + 1 < len(moved) else None
        for n in groups[s]:
            ns = max(0.0, moved[i])
            end = n.start + n.dur
            if nxt is not None and starts[i + 1] - 0.02 <= end <= starts[i + 1] + max(0.1, 2 * legato):
                d = nxt - ns + legato                       # tied to the next onset: re-tie it
            else:
                d = max(0.03, end - ns)                     # a rest follows / held under the next notes
            out.append(n._replace(start=ns, dur=max(0.03, d)))
    return Clip._raw(out, clip.length)


def pedal_changes(changes, *, end, lift_ms: float = 90.0, bpm=60.0, dry=(), flutter=(),
                  flutter_ms: float = 280.0, flutter_to: float = 0.0) -> list:
    """Legato (syncopated) pedalling: at every harmony change in `changes` (beats) the pedal comes up WITH the
    new bass and goes down again `lift_ms` later (the new harmony is caught, the old one cleared); up at `end`;
    `dry` = (start, end) windows with the pedal up; `flutter` = (start, end) windows where the pedal is cleared
    every `flutter_ms` (up `lift_ms`, down again): chromatic fioriture and cadenzas over one harmony keep their
    bass and resonance but do not pile every passing note into a cluster. `flutter_to` = the pedal value of those
    quick lifts: 0 = fully up, 0.5-0.7 = a half pedal (the sampler's 0.5..1 range: the treble clears, the bass
    rings on). Points for 'instrument.pedal' (steps)."""
    ch = sorted({_num(float(c), 'pedal change') for c in changes})
    e = _num(float(end), 'pedal end')
    pts = []
    for c in ch:
        if c >= e:
            break
        up_len = _beats(lift_ms / 1000.0, bpm, c)
        if pts and pts[-1][0] >= c - _EPS:
            pts = [p for p in pts if p[0] < c - _EPS]
        pts.append((round(c, 6), 0.0, 'step'))
        pts.append((round(c + up_len, 6), 1.0, 'step'))
    for a, b in dry:
        pts = [p for p in pts if not a <= p[0] < b]
        pts.append((round(a, 6), 0.0, 'step'))
        pts.append((round(b, 6), 1.0, 'step'))
    fm = _num(flutter_ms, 'pedal flutter_ms', 60)
    fv = _num(flutter_to, 'pedal flutter_to', 0, 0.95)
    for a, b in flutter:
        a, b = float(a), float(b)
        pts = [p for p in pts if not a <= p[0] < b]
        t = a
        while t < b - _EPS:
            up = _beats(lift_ms / 1000.0, bpm, t)
            pts.append((round(t, 6), fv, 'step'))
            pts.append((round(min(b, t + up), 6), 1.0, 'step'))
            t += max(2 * up, _beats(fm / 1000.0, bpm, t))
    pts.append((round(e, 6), 0.0, 'step'))
    pts.sort(key=lambda p: p[0])
    clean = []
    for p in pts:
        if clean and abs(clean[-1][0] - p[0]) < 1e-9:
            clean[-1] = p
        elif not clean or clean[-1][1] != p[1]:
            clean.append(p)
    return clean


# ------------------------------------------------------------------------------------------------ measuring

def figure_stats(clip: Clip, bpm) -> dict:
    """Timing of a fast figure as played: notes, seconds, notes/s overall, the fastest and slowest inter-onset
    interval (ms), the middle vs ends speed ratio and the evenness (coefficient of variation of the IOIs) - the
    numbers the etude compared with the recording."""
    ons = sorted({round(n.start, 6) for n in clip})
    if len(ons) < 3:
        return {'notes': len(ons)}
    secs = [(b - a) * 60.0 / _bpm_at(bpm, a) for a, b in zip(ons, ons[1:])]
    n = len(secs)
    mid = secs[n // 3: max(n // 3 + 1, 2 * n // 3)]
    ends = secs[:max(1, n // 4)] + secs[-max(1, n // 4):]
    mean = sum(secs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in secs) / n)
    return {'notes': len(ons), 'seconds': round(sum(secs), 3), 'rate': round(n / sum(secs), 2),
            'fastest_ms': round(1000 * min(secs), 1), 'slowest_ms': round(1000 * max(secs), 1),
            'ends_vs_middle': round((sum(ends) / len(ends)) / (sum(mid) / len(mid)), 2),
            'cv': round(sd / mean, 3)}


# ------------------------------------------------------------------------------------------------ written scores

_accompany = accompany


class Event:
    """One right-hand event of a Score: kind ('note', 'chord' = notes struck together as written, or the ornament
    of the notation: 'trill', 'turn', 'mordent', 'prall', 'crush', 'roll', 'strum', 'fig'), at / dur (beats; a
    note's dur includes its holds), pitches, factor (the written accent: ! > 1, ? < 1), args / kw (the ornament's
    arguments as written: ^tr(upper), ^turn(upper=1, lower=-1), ^fig(even), ^roll(60))."""

    __slots__ = ('kind', 'at', 'dur', 'pitches', 'factor', 'args', 'kw')

    def __init__(self, kind, at, dur, pitches, factor=1.0, args=(), kw=None):
        self.kind, self.at, self.dur, self.pitches = kind, float(at), float(dur), tuple(pitches)
        self.factor, self.args, self.kw = factor, tuple(args), dict(kw or {})

    @property
    def pitch(self) -> int:
        return self.pitches[0]

    @property
    def top(self) -> int:
        return max(self.pitches)

    def __repr__(self) -> str:
        return f"Event({self.kind}, at {self.at:g}, dur {self.dur:g}, {list(self.pitches)})"


def _lh_entries(specs: list, t0: float, slot: float, unit: float, slots: int, where: str) -> list:
    """Left-hand entries of one bar: slot specs 'BASS:CHORD[/CHORD2][@off+len][|pattern]' (chord notes joined by
    '.', ';' = several entries in one slot, '-' = no bass; off / len in units)."""
    if len(specs) != slots:
        raise ComposeError(f"{where}: {len(specs)} left-hand slots, the meter has {slots}: {' '.join(specs)!r}")
    out = []
    for i, sp in enumerate(specs):
        for part in sp.split(';'):
            pat = 'bcc'
            if '|' in part:
                part, pat = part.split('|')
            off, ln = 0.0, slot / unit
            if '@' in part:
                part, span = part.split('@')
                off, ln = (float(x) for x in span.split('+'))
            bass, _, chords = part.partition(':')
            if not chords:
                raise ComposeError(f"{where}: left-hand slot {part!r} must be BASS:CHORD (C2:G3.C4.E4)")
            ch = [c.split('.') for c in chords.split('/')]
            out.append((t0 + i * slot + off * unit, ln * unit, None if bass == '-' else bass, ch[0],
                        ch[1] if len(ch) > 1 else ch[0], pat))
    return out


class Score:
    """A written piano score (romantic.score): the right hand in notation with its ornaments as written, the left
    hand as accompaniment entries, dynamics, phrases. .bar(k), .events, .entries, .dyn (beat, level), .phrases;
    .perform(song, rh_track, lh_track) plays it like a pianist; .rubato(song) / .touch(clip, levels) are the
    phrase loops of a slow piece."""

    def __init__(self, rh=None, lh=None, dyn=None, *, meter='4/4', pickup=0, unit='1/8', key=None, phrases=None,
                 accent: float = 1.1, ghost: float = 0.72, refs=None):
        from .notation import _meter_beats, _duration, notes as _notes
        from .tempo import parse_meter
        self.meter = parse_meter(meter, 'score meter')
        self.bar_beats = float(_meter_beats(self.meter))
        self.pickup = float(_duration(pickup, 'score pickup')) if pickup else 0.0
        self.unit = float(_duration(unit, 'score unit'))
        n, d = self.meter
        self.slot = self.bar_beats / (n // 3) if n % 3 == 0 and d == 8 and n > 3 else 4.0 / d
        self.key = Key(key) if key is not None else None
        self.phrases = [tuple(p) for p in (phrases or [])]
        self.events: list[Event] = []
        self.line = None
        last = 0
        if rh is not None:
            bars = rh if isinstance(rh, dict) else None
            text = rh if bars is None else ' | '.join(bars[k] for k in sorted(bars))
            if bars is not None:
                last = max(bars)
                if sorted(bars) != list(range(0 if self.pickup else 1, last + 1)):
                    raise ComposeError("score rh: give every bar once, in a row (0 = the pickup)")
            kw = {'key': self.key} if self.key is not None else {}
            line = _notes(text, unit=unit, meter=meter, pickup=pickup, expand=False, vel=100, accent=accent,
                          ghost=ghost, refs=refs, **kw)
            self.line = line.shift(self.pickup) if self.pickup else line
            evs = [Event(o['kind'], o['start'], o['dur'], o['pitches'], o['vel'] / 100, o['args'], o['kw'])
                   for o in self.line.ornaments]
            plain: dict = {}
            for x in self.line:
                plain.setdefault(x.start, []).append(x)
            for at, ns in plain.items():
                evs.append(Event('note' if len(ns) == 1 else 'chord', at, max(x.dur for x in ns),
                                 sorted(x.pitch for x in ns), max(x.vel for x in ns) / 100))
            self.events = sorted(evs, key=lambda e: e.at)
            if bars is None:
                last = int(math.ceil((self.line.length - self.pickup) / self.bar_beats - _EPS))
        self.entries = []
        if lh is not None:
            spb = int(round(self.bar_beats / self.slot))
            for first in sorted(lh):
                bars_, cur = [], []
                for t in str(lh[first]).split():          # bars: ' | ' (a pattern's '|' sits inside its slot)
                    if t == '|':
                        bars_.append(cur)
                        cur = []
                    else:
                        cur.append(t)
                bars_.append(cur)
                for i, specs in enumerate(x for x in bars_ if x):
                    k = first + i
                    self.entries += _lh_entries(specs, self.bar(k), self.slot, self.unit, spb, f"score lh bar {k}")
                    last = max(last, k)
        self.bars = last
        self.dyn = []
        for item in (dyn or []):
            if len(item) != 3:
                raise ComposeError(f"score dyn: (bar, position in units, level), got {item!r}")
            b, pos, lv = item
            if lv not in LEVELS:
                raise ComposeError(f"score dyn: unknown level {lv!r}; use one of {', '.join(LEVELS)}")
            self.dyn.append((self.bar(b) + pos * self.unit, lv))

    def __repr__(self) -> str:
        return (f"Score({self.bars} bars of {self.meter[0]}/{self.meter[1]}, {len(self.events)} right-hand events, "
                f"{len(self.entries)} left-hand entries)")

    def bar(self, k) -> float:
        """The beat of bar k (1 = the first full bar; 0 = the pickup)."""
        if k == 0 and self.pickup:
            return 0.0
        return self.pickup + (k - 1) * self.bar_beats

    def in_bar(self, k) -> list:
        """The right-hand events starting in bar k."""
        a, b = self.bar(k), self.bar(k + 1) if k else self.pickup
        return [e for e in self.events if a - _EPS <= e.at < b - _EPS]

    @property
    def end(self) -> float:
        return self.bar(self.bars + 1)

    # ------------------------------------------------------------------ the phrase loops
    def rubato(self, song, *, depth: float = 0.04, phrase: str = 'arch', shapes=None, seed=None, bars=None,
               overlap: float | None = None) -> None:
        """song.rubato over every phrase (in the bars range (first, last) when given): `phrase` (or `shapes`
        cycled phrase by phrase), depth, seed (None: the song's; an int; 'bar' = the phrase's first bar). Two
        phrases that share a bar meet `overlap` beats into it (the bar's last beat is the next phrase's pickup)."""
        for i, (a, b) in enumerate(self.phrases):
            if bars is not None and not (bars[0] <= a and b <= bars[1]):
                continue
            shared_start = overlap is not None and any(b0 == a for _, b0 in self.phrases)
            shared_end = overlap is not None and any(a0 == b for a0, _ in self.phrases)
            span = (self.bar(a) + (overlap if shared_start else 0),
                    self.bar(b) + (overlap if shared_end else self.bar_beats))
            sd = a if seed == 'bar' else seed
            song.rubato(span, depth=depth, phrase=shapes[i % len(shapes)] if shapes else phrase, seed=sd)

    def touch(self, clip, levels, *, gap=16, **kw) -> list:
        """Per-phrase dynamics of a melody: for each phrase (lo, hi) = levels[(first, last)] - the notes of its
        bars (a bar two phrases share belongs to the first) shifted to the phrase start, through touch(). Returns
        [(phrase, beat of its start, the shaped notes sorted by (start, pitch))]; phrases without notes or with
        hi 0 are left out."""
        from .humanize import touch as _touch
        done, out = set(), []
        ns = sorted(as_clip(clip), key=lambda x: (x.start, x.pitch))
        for a, b in self.phrases:
            lo, hi = levels[(a, b)][:2]
            sel = []
            for k in range(a, b + 1):
                if k in done:
                    continue
                done.add(k)
                sel += [x._replace(start=x.start - self.bar(a)) for x in ns
                        if self.bar(k) - _EPS <= x.start < self.bar(k + 1) - _EPS]
            if not sel or hi == 0:
                continue
            out.append(((a, b), self.bar(a), sorted(_touch(Clip(sel), lo, hi, gap=gap, **kw),
                                                     key=lambda x: (x.start, x.pitch))))
        return out

    def phrase_of(self, k) -> tuple:
        """The phrase (first, last) bar k belongs to (the first one that holds it)."""
        for a, b in self.phrases:
            if a <= k <= b:
                return a, b
        raise ComposeError(f"bar {k} is in no phrase of the score")

    # ------------------------------------------------------------------ the performance
    def perform(self, song, rh_track, lh_track=None, *, pedal: bool = True, touch=None, breath: float = 0.3,
                accompany=None, lh_dyn: float = 0.6, rubato=None, cap: int = 112, accent_cap: float = 118,
                roll_bpm=None, anchors: str = 'half', pedal_opts=None, plain: bool = False) -> dict:
        """Play the score like a romantic pianist (the nocturne etude's measured pipeline):
          left hand first (the timekeeper: the tempo map knows its onsets) - accompany() per entry (`accompany`
            options: vel 38, bass 1.2, first 1.0, second 0.88, top 1.06, roll_ms 14), the dynamics at a gentler
            slope (factor ** lh_dyn)
          right hand - the velocities from a touch() over the melody's principal notes (`touch` options: lo 64,
            hi 96, gap 1/4, start 0.55, end 0.4, pitch 0.9; each phrase end takes `breath` beats of air for it),
            accents x their factor (at most `accent_cap`), then every ornament in real time at the tempo map:
            ^tr = trill() landing on the next note, ^turn = turn(), ^fig = fioritura() (ease 0.2 when even, 0.8
            else; lighter in the middle), ^roll chords = pianist.roll at `roll_bpm` (default the song tempo); then
            lean_on_long, cantabile, the dynamics, melody_rubato (`rubato` options: sync_ms 42, seed 3; anchors at
            every half bar) and a cap (`cap`: the climax sings, not bangs)
          pedal - pedal_changes() with the harmony (the left hand's bass + chord), cleared in chromatic figures
            (`pedal_opts`: lift_ms 110, flutter_ms 320, flutter_to 0.6, tail 2 beats after the last bar)
        plain=True: the score as the plain tools read it - the etude's 'before' baseline for an A/B: every
        left-hand strike at one level (humanized), the figures on an even grid, pianist.trill / turn, chords rolled
        25 ms, the dynamics as crescendo spans, no singing line, no rubato, no cleared pedal.
        Returns {'rh': Clip, 'lh': Clip, 'pedal': points, 'figures': [(clip, bpm, at)]}."""
        bpm = song.tempo_at
        out: dict = {'figures': []}
        if self.entries and lh_track is not None:
            ns = []
            if plain:
                from .humanize import humanize as _human
                for st, ln, bass, c1, c2, pat in self.entries:
                    for i in range(int(round(ln / self.unit))):
                        c, t = pat[i % len(pat)], st + i * self.unit
                        if c in 'bB' and bass:
                            ns.append(Note(t, ln - i * self.unit, note(bass), 58))
                        if c in 'cB':
                            ns += [Note(t, self.unit if c == 'c' else ln - i * self.unit, note(p), 58)
                                   for p in (c1 if i <= 1 else c2)]
                lh = self._plain_dyn(_human(Clip._raw(ns, max(n.start + n.dur for n in ns)), timing_ms=4, vel=6,
                                            bpm=song.tempo, seed=2), lh_dyn)
            else:
                ac = dict(vel=38, bass=1.2, first=1.0, second=0.88, top=1.06, roll_ms=14)
                ac.update(accompany or {})
                for st, ln, bass, c1, c2, pat in self.entries:
                    ns += list(_accompany([(st, ln, bass, c1, c2)], bpm, pattern=pat, seed=int(st * 3), **ac))
                lh = Clip._raw(ns, max(n.start + n.dur for n in ns))
                if self.dyn:
                    lh = dynamics(lh, [(b, LEVELS[lv] ** lh_dyn) for b, lv in self.dyn])
            lh_track.play(lh, 0)
            out['lh'] = lh
        if self.events:
            rh = self._right_hand(song, bpm, touch, breath, rubato, cap, accent_cap, roll_bpm, anchors, out, plain)
            rh_track.play(rh, 0)
            out['rh'] = rh
        if pedal:
            po = dict(lift_ms=110, flutter_ms=320, flutter_to=0.6, tail=2.0)
            po.update(pedal_opts or {})
            tail = po.pop('tail')
            changes, last = [], None
            for e in sorted(self.entries, key=lambda e: e[0]):
                h = (e[2], tuple(e[3]))
                if e[2] and h != last:
                    changes.append(round(e[0], 4))
                last = h
            flutter = []
            for e in ([] if plain else self.events):
                if e.kind == 'fig' and len(e.pitches) >= 6:
                    if sum(1 for x, y in zip(e.pitches, e.pitches[1:]) if abs(x - y) == 1) >= 3:
                        flutter.append((e.at, e.at + e.dur))
            ped = pedal_changes(changes, end=self.end + tail, bpm=bpm, flutter=flutter, **po)
            for t in (rh_track, lh_track):
                if t is not None:
                    t.automate('instrument.pedal', ped)
            out['pedal'] = ped
        return out

    def _plain_dyn(self, clip: Clip, power: float) -> Clip:
        """perform(plain=True): the dynamics with the tools that existed - humanize.crescendo per span of marks."""
        from .humanize import crescendo
        pts = [(b, LEVELS[lv] ** power) for b, lv in self.dyn]
        for (b0, l0), (b1, l1) in zip(pts, pts[1:]):
            if b1 > b0:
                clip = crescendo(clip, l0, l1, span=(b0, b1 - 1e-3))
        return clip

    def _right_hand(self, song, bpm, touch_opts, breath, rubato_opts, cap, accent_cap, roll_bpm, anchors, out,
                    plain=False):
        from . import pianist
        from .humanize import touch as _touch
        sk = []
        for e in self.events:
            sk.append((e.at, e.dur, e.top if e.kind in ('chord', 'roll', 'strum') else e.pitch, 80))
        sk = Clip(sk)
        ends = {self.bar(b + 1) for _, b in self.phrases}
        if breath:
            sk = Clip._raw([n._replace(dur=n.dur - breath) if any(abs(n.start + n.dur - e) < 0.05 for e in ends)
                            and n.dur > 0.6 else n for n in sk], sk.length)
        to = dict(lo=60, hi=100, gap='1/4', start=0.35, end=0.3, pitch=0.7) if plain else \
            dict(lo=64, hi=96, gap='1/4', start=0.55, end=0.4, pitch=0.9)
        to.update(touch_opts or {})
        sk = _touch(sk, **to)
        vel = {round(n.start, 4): n.vel for n in sk}
        rb = song.tempo if roll_bpm is None else roll_bpm
        notes_ = []
        for i, e in enumerate(self.events):
            at, d = e.at, e.dur
            v = vel.get(round(at, 4), 70)
            if e.factor > 1:
                v = min(accent_cap, v * e.factor)
            elif e.factor < 1:
                v = v * e.factor
            nxt = self.events[i + 1] if i + 1 < len(self.events) else None
            kw = dict(e.kw)
            if e.kind == 'note':
                notes_.append(Note(at, d, e.pitch, v))
            elif e.kind == 'chord':
                notes_ += [Note(at, d, p, v) for p in e.pitches]
            elif e.kind == 'roll':
                if plain:
                    kw['ms'] = 25
                elif e.args and isinstance(e.args[0], (int, float)):
                    kw.setdefault('ms', e.args[0])
                notes_ += list(pianist.roll(sorted(e.pitches), d, rb, vel=v, at=at, **kw))
            elif plain and e.kind == 'fig':            # the notes on an even grid, the pianist's light drop
                n = len(e.pitches)
                f = Clip([(at + j * d / n, d / n * 1.1, p, v if j == 0 else max(1, v - 12))
                          for j, p in enumerate(e.pitches)])
                out['figures'].append((f, bpm, at))
                notes_ += list(f)
            elif plain and e.kind == 'trill':
                f = pianist.trill(e.pitch, d, song.tempo, key=self.key or song.key, vel=v, at=at, hold=0.0)
                out['figures'].append((f, bpm, at))
                notes_ += list(f)
            elif plain and e.kind == 'turn':
                notes_ += list(pianist.turn(e.pitch, d, song.tempo, key=self.key or song.key, vel=v, at=at))
            elif e.kind == 'fig':
                shape = e.args[0] if e.args else kw.pop('shape', 'arch')
                kw.setdefault('ease', 0.2 if shape == 'even' else 0.8)
                kw.setdefault('dip', 7 if len(e.pitches) > 5 else 4)
                f = fioritura(list(e.pitches), d, bpm, at=at, shape=shape, vel=(v, v - 6), seed=int(at * 7), **kw)
                out['figures'].append((f, bpm, at))
                notes_ += list(f)
            elif e.kind == 'trill':
                if e.args:
                    kw.setdefault('start', e.args[0])
                land = nxt.pitch if nxt is not None and nxt.kind in ('note', 'trill', 'turn') else None
                f = trill(e.pitch, d, bpm, at=at, key=self.key or song.key, land=land, land_dur=0.05, vel=v,
                          seed=int(at), **kw)
                f = Clip([n for n in f if n.start < at + d - 1e-6])      # the landing note is the next event
                out['figures'].append((f, bpm, at))
                notes_ += list(f)
            elif e.kind == 'turn':
                if e.args:
                    kw.setdefault('where', e.args[0])
                notes_ += list(turn(e.pitch, d, bpm, at=at, key=self.key or song.key, vel=v, **kw))
            elif e.kind in ('mordent', 'prall'):
                kw.setdefault('upper', e.kind == 'prall' or (bool(e.args) and e.args[0] == 'upper'))
                notes_ += list(pianist.mordent(e.pitch, d, _bpm_at(bpm, at), key=self.key or song.key, vel=v, at=at,
                                               **kw))
            elif e.kind == 'crush':
                if e.args:
                    kw.setdefault('grace', int(e.args[0]))
                notes_ += list(pianist.crush(e.pitch, d, _bpm_at(bpm, at), vel=v, at=at, **kw))
            else:   # strum
                from .midifx import strum
                ms = e.args[0] if e.args and isinstance(e.args[0], (int, float)) else 30.0
                notes_ += list(strum(Clip._raw([Note(at, d, p, v) for p in e.pitches], 0.0), ms,
                                     bpm=_bpm_at(bpm, at), **kw))
        rh = Clip._raw(notes_, max(n.start + n.dur for n in notes_))
        if plain:
            return self._plain_dyn(rh, 1.0)
        rh = lean_on_long(rh, bpm, gain=10)
        rh = cantabile(rh, bpm)
        if self.dyn:
            rh = dynamics(rh, list(self.dyn))
        ro = dict(sync_ms=42, seed=3)
        ro.update(rubato_opts or {})
        if anchors == 'half':
            anc = [self.bar(k) + h * self.bar_beats / 2 for k in range(1, self.bars + 1) for h in (0, 1)]
        elif anchors == 'bar':
            anc = [self.bar(k) for k in range(1, self.bars + 1)]
        else:
            anc = list(anchors)
        rh = melody_rubato(rh, anc + [self.end], bpm, **ro)
        return Clip._raw([n._replace(vel=min(n.vel, cap)) for n in rh], rh.length)


def score(rh=None, lh=None, dyn=None, *, meter='4/4', pickup=0, unit='1/8', key=None, phrases=None,
          accent: float = 1.1, ghost: float = 0.72, refs=None) -> Score:
    """A written piano score -> Score (play it with .perform(song, rh_track, lh_track)):
      rh       the right hand in notation (agentsound.notation, read with unit= and meter=): a string, or
               {bar: notation} (bar 0 = the pickup when pickup= is given; joined with bar lines). Ornaments as
               written and realized by perform(): ^tr / ^tr(upper) / ^tr(lower=-1) trills, ^turn (upper=1,
               lower=-1: chromatic), {..}:N^fig(even | arch | rit | accel | wave) fioriture, [..]^roll(60) rolled
               chords; ! / ? accents x accent= / ghost= (dynamics belong in dyn=)
      lh       {first bar: 'slot slot slot slot | next bar ...'}: per slot of the meter (a dotted quarter in 12/8,
               a quarter in 4/4) 'BASS:CHORD[/CHORD2][@off+len][|pattern]' - accompany() entries (chord notes
               joined by '.', ';' several entries in one slot, '-' no bass, off / len in units, the pattern of
               b bass / c chord / B both held / . rest, default 'bcc')
      dyn      [(bar, position in units, 'p' | 'mf' | ...)]: marks and the hairpins between them
      phrases  [(first bar, last bar)]: the breaths of the touch, Score.rubato / Score.touch
    meter ('12/8'), pickup (a note value: '1/8'), unit (what a bare number counts, '1/8'), key (ornaments' scale).
    Found and measured by the nocturne etude (songs/nocturne-etude)."""
    return Score(rh, lh, dyn, meter=meter, pickup=pickup, unit=unit, key=key, phrases=phrases, accent=accent,
                 ghost=ghost, refs=refs)
