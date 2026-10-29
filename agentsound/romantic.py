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

import bisect
import math
import random

from .humanize import leap_delay_ms
from .expressive import CHARGE, harmonic_charge, melodic_charge  # noqa: F401  (the shared KTH charge)
from .expressive import charge as _charge  # noqa: F401
from .patterns import Clip, Note, _vel, as_clip, seed_int
from .theory import ComposeError, Key, note

__all__ = ['SHAPES', 'LEVELS', 'RULES', 'ASYNC', 'PEDAL', 'CHARGE', 'ARTICULATION', 'PHRASE_TEMPO', 'ACCOMPANIMENT',
           'fioritura', 'grace', 'turn',
           'trill', 'accompany', 'lean_on_long', 'cantabile', 'dynamics', 'melody_rubato', 'pedal_changes', 'decay_db',
           'figure_stats', 'score', 'Score', 'Event', 'harmonize', 'travel_ms', 'spread', 'melodic_charge',
           'harmonic_charge', 'articulate']

_EPS = 1e-6

SHAPES = ('arch', 'accel', 'rit', 'even', 'wave')
"""fioritura timing shapes: 'arch' (out of the principal slowly, fastest in the middle, broadening into the
landing), 'accel' (faster and faster), 'rit' (slowing down), 'even', 'wave' (two surges)."""

LEVELS = {'ppp': 0.45, 'pp': 0.55, 'p': 0.7, 'mp': 0.85, 'mf': 1.0, 'f': 1.15, 'ff': 1.3, 'fff': 1.42}
"""Velocity factors of the dynamic marks for dynamics() (mf = the written level)."""

# ------------------------------------------------------------------------------------------------ the rule tables
# The performance rules Score.perform plays by, one table per rule family (docs/PIANIST_RULES.md: the source and the
# published range of every number). A song may pass its own values (Score.perform(rules={'async': {...}})).

ASYNC = {
    'travel': (4000.0, 20.0),   # hammer travel time (ms) = a / (velocity + b): softer keys sound later (Goebl 2001)
    'max_ms': 45.0,             # no velocity lead beyond this (melody leads 20-40 ms, rarely 50+: Palmer 1989, Goebl)
    'sd_ms': 5.0,               # the lead's own spread per onset
    'chord_sd_ms': 8.0,         # a chord's softer notes: + |N(0, sd)| after the loudest (within +-15 ms: Goebl 2001)
    'sync_ms': 14.0,            # the melody against the bass on a half-bar anchor: +-spread (melody_rubato sync_ms)
    'lean_ms': 18.0,            # melody_rubato's push-pull inside a half bar (Chopin's rubato, kept small)
    'anticipate': 0.12,         # the chance of a bass anticipation under a long anchor note (Goebl 2001, Vernon 1936)
    'anticipate_ms': (25.0, 55.0),    # how late the melody then follows the bass
    'peak_ms': 25.0,            # a melodic summit (a long local top) arrives this much late (agogic accent)
    'lh_roll': (0.6, 0.4),      # a left-hand chord: (near-simultaneous, rolled bottom-up) shares, drawn per chord
    'roll_ms': (4.0, 10.0),     # ... the bottom-up roll's step per note (x the softness: a soft chord rolls wider)
    'arp': 0.4,                 # the chance the cadence chord of a phrase is arpeggiated (bottom-up, slow) ...
    'arp_ms': (35.0, 70.0),     # ... at this step per note (max_ms does not cap it: the roll is the gesture)
}
"""Asynchrony: the melody lead as the hammers' velocity artifact (the louder melody sounds first, its lead grows with
the velocity difference), the spread inside a chord, the occasional bass anticipation of the romantic style."""

PEDAL = {
    'delay_ms': 60.0,           # syncopated pedal: up this long AFTER the new harmony's onset (Repp 1996: 40-150)
    'lift_ms': 110.0,           # ... and down again this much later (the new bass is caught, the old chord cleared)
    'vary': 0.25,               # the foot is no clock: both x (72 / BPM) ** 0.5 x 1 + N(0, vary) per change
    'half_to': 0.6,             # a half change: the treble's dampers touch, the bass rings on (0.5-0.7)
    'half_beats': 2.0,          # half changes only inside one harmony held at least this long (beats)
    'same_bass': 'half',        # a new chord over the same bass: 'half' change (the bass rings on) or 'full'
    'flutter_ms': 320.0, 'flutter_to': 0.6,    # a chromatic run's quick half lifts (pedal_changes flutter)
    'tail': 2.0,                # beats after the last bar before the pedal comes up
}
"""Pedalling: legato pedal just after every harmony change, a half change at the resolution of a melody's non-chord
tone inside a long harmony (the passing note is cleared, the bass rings on), quick half lifts in chromatic runs."""

# CHARGE (melodic / harmonic charge: the KTH rules every player shares - the pianist, the orchestra) lives in
# agentsound.expressive with melodic_charge / harmonic_charge; imported above, romantic.CHARGE is that table.

ARTICULATION = {
    'repeat_ms': (40.0, 90.0),  # a repeated key is released 25 % of the IOI (within this) before it strikes again
    'leap': 7,                  # a leap of this many semitones or more ...
    'leap_ms': (15.0, 45.0),    # ... detaches the note before it (leap articulation; more for wider leaps)
    'legato': (0.07, 0.03),     # finger legato: the key overlap = N(mean, sd) x the IOI (KOR; Bresin & Battel 2000)
    'legato_ms': (12.0, 100.0),  # ... within these ms (Repp 1997: legato overlaps of some tens of ms)
}
"""Articulation of the melody (DM repetition and leap articulation): the hand lets go of a key it strikes again and
before a wide leap; everything else stays legato (melody_rubato re-ties it)."""

PHRASE_TEMPO = {
    'depth': (0.4, 1.6),        # a phrase's rubato depth x U(lo, hi): no two phrases breathe alike (Repp 1992)
    'straight': 0.15,           # the share of phrases played nearly straight (depth x 0.2)
    'peak': {'phrase': (0.3, 0.8), 'period': (0.25, 0.7), 'end': (0.2, 0.55)},     # where the phrase is fastest
    'close': {'phrase': (0.0, 1.0), 'period': (0.6, 1.5), 'end': (1.2, 2.0)},   # its final lengthening (x depth)
    'lilt': (0.0, 1.0),         # a phrase's beat lilt x U(lo, hi): some phrases keep an even pulse
    'lilt_jitter': 0.4,         # the beat jitter x this: the phrase carries the shape, the beat stays near the grid
}
"""The phrase tempo (Score.rubato / Score.lilt): every phrase draws its own arch - its depth, where it is fastest,
how much it lengthens at its end - by its level: a 'phrase' inside a period closes lightly, a 'period' (every second
phrase: the consequent's cadence) deeper, the piece's 'end' deepest (final lengthening grows with the depth of the
boundary: Todd 1985 / 1992, Repp 1992, Penel & Drake 1998)."""

ACCOMPANIMENT = {
    'arc': (0.12, 0.28),        # the left hand's phrase swell: x 1 + arc x (the arch - 0.5), drawn per phrase
    'peak': (0.45, 0.75),       # ... where it crests (its share of the phrase)
    'follow': 0.4,              # the hand follows the melody's level: x (the melody now / its phrase mean) ** follow
    'charge': 2.4,              # harmonic charge of the left hand (velocity x sqrt charge: CHARGE['harmonic'])
    'tension': 3.0,             # + velocity on a tension chord (a tritone in it, or resolving down a fifth)
    'bass': (0.92, 1.1),        # the bass against the figure: x U(lo, hi) at a phrase's start and end, linear between
    'below_db': 6.0,            # budget: a phrase's accompaniment median at least this many dB under the melody's
    # the give and take of the hands (Score.perform(balance=) only - a drawn balance plan; HUMAN_FEEDBACK
    # 2026-10-15: "the right hand always feels louder than the left - it should be dynamic"):
    'give': 1.24,               # the hand swells into the melody's gap: x this where the tune holds a note or rests,
    'give_beats': (0.6, 2.0),   # ... ramping in from this many beats after the melody's last onset to full at the 2nd
    'take': 0.93,               # ... and recedes under a melody note just struck (x this)
    'lead_end': 0.12,           # the phrase's last bar: x 1 + this more of the give (the hand leads the transition)
    'scale': (0.55, 1.9),       # a phrase's hand is scaled to its balance by at most these factors
}
"""The left hand's dynamics in a broken-chord figure (Score.perform figures): it follows the phrase's arc and the
melody (at a smaller range), swells into the tension chords and relaxes at their resolution, shifts the balance of
bass and figure, and stays under the tune (Repp 1996: the accompaniment's dynamic profile parallels the melody's a
few dB below it). With a balance plan (Score.perform(balance=)) the budget is a target per phrase instead - near
equal in a flowing build, the hand leading in an answer phrase - and the hands give and take: the left hand swells
into the melody's held notes and rests and recedes under a new melody note."""

ENERGY_EXP = 2.5
"""A note's energy as (velocity / 127) ** ENERGY_EXP (composer.NoteView's loudness model): the balance plan's dB are
the hands' summed energy per phrase - many soft notes add up like the stems' RMS (the measured endless sets: the
note dB and the stems' RMS dB within about 1 dB per piece)."""


def _energy(vel: float) -> float:
    return (vel / 127.0) ** ENERGY_EXP


RULES = {'async': ASYNC, 'pedal': PEDAL, 'charge': CHARGE, 'articulation': ARTICULATION, 'phrase_tempo': PHRASE_TEMPO,
         'accompaniment': ACCOMPANIMENT}


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


def harmonize(clip: Clip, chord_at, *, voices: int = 1, min_dur: float = 1.0, share: float = 0.6, floor='F4',
              seed=0, move: float = 0.0, still=None, long_share: float | None = None, scale_at=None) -> Clip:
    """A melody's long notes (`min_dur` beats+, `share` of them, seeded) given the chord under them in the right
    hand: voices=1 a third or a sixth below (a chord tone; the sung line's companion - letters-to-the-morning's A2 /
    A3), voices=2 two chord tones inside the octave below (the climax's chords: the hook in chords), voices=3 the
    melody in octaves with a chord tone inside (the climax's octaves); short notes stay single, nothing under
    `floor`. move: that share of the notes held 1.5 beats+ with a companion get an inner voice that MOVES under them
    (the companion let go at the half, another chord tone - or the scale step next to it - struck there: an alto
    line under the held tune; HUMAN_FEEDBACK 2026-10-15, "as if he had only one finger"; still(start, end) True: not
    under that note - a phrase's landing keeps its breath). long_share: the share for the notes held 1.5 beats+
    (default `share`; blind round g3: inner motion under held notes 0.22 - the long notes want their companion).
    scale_at(beat) -> pitch classes: the moving voice's passing step (no chord tone in reach) only inside them (the
    key's scale there; new-age round g13: MYUS's Bb4 a whole step under C5 over Cadd9 in C major, "a stray dominant
    7th on the tonic", two judges). The hand's span stays
    within a ninth. chord_at(beat) -> a Chord / symbol or None. The melody keeps its notes; voice the top with
    Score.perform(inner=)."""
    from .theory import Chord
    if voices not in (1, 2, 3):
        raise ComposeError(f"harmonize voices must be 1 (3rds / 6ths), 2 (chords) or 3 (octaves), got {voices!r}")
    rng = random.Random(seed_int(seed))
    lo = note(floor)
    out = list(clip)
    for n in clip:
        if n.dur < min_dur - _EPS or rng.random() >= (share if long_share is None or n.dur < 1.5 - _EPS
                                                       else max(share, long_share)):
            continue
        c = chord_at(n.start)
        if c is None:
            continue
        c = c if isinstance(c, Chord) else Chord.parse(c)
        tones = {(c.root + i) % 12 for i in c.intervals}
        added = []
        if voices == 1:
            cand = [p for p in range(n.pitch - 9, n.pitch - 2) if p % 12 in tones and p >= lo
                    and (n.pitch - p) in (3, 4, 8, 9)] or \
                [p for p in (n.pitch - 5,) if p % 12 in tones and p >= lo and long_share is not None
                 and n.dur >= 1.5 - _EPS]              # (a held note: an open 4th under it when no 3rd / 6th fits)
            if cand:
                added = [n._replace(pitch=rng.choice(cand), vel=_vel(n.vel * 0.85))]
        elif voices == 3:
            if n.pitch - 12 >= lo:
                mid = [p for p in range(n.pitch - 9, n.pitch - 2) if p % 12 in tones and p % 12 != n.pitch % 12]
                added = [n._replace(pitch=n.pitch - 12, vel=_vel(n.vel * 0.9))] + \
                    ([n._replace(pitch=rng.choice(mid), vel=_vel(n.vel * 0.8))] if mid else [])
        else:
            cand = sorted({p for p in range(n.pitch - 11, n.pitch - 2) if p % 12 in tones and p >= lo
                           and p % 12 != n.pitch % 12}, reverse=True)
            picked = []
            for p in cand:
                if all(abs(p - q) >= 3 for q in picked):
                    picked.append(p)
                if len(picked) == 2:
                    break
            added = [n._replace(pitch=p, vel=_vel(n.vel * 0.85)) for p in picked]
        if added and move and n.dur >= 1.5 - _EPS and rng.random() < move and \
                not (still is not None and still(n.start, n.start + n.dur)):
            # the inner voice moves under the held note: the lowest companion let go at the half, the next chord
            # tone (else the scale step) toward the melody struck there, softer
            low = min(added, key=lambda x: x.pitch)
            h = round(n.dur / 2 * 2) / 2 or 0.5
            c2 = chord_at(n.start + h)
            c2 = c2 if c2 is None or isinstance(c2, Chord) else Chord.parse(c2)
            t2 = tones if c2 is None else {(c2.root + i) % 12 for i in c2.intervals}
            nxt = [p for p in range(low.pitch - 4, n.pitch - 2) if p % 12 in t2 and p != low.pitch and p >= lo
                   and all(p != q.pitch for q in added) and (n.pitch - p) % 12 not in (1, 11)]
            # (new-age round g14: no major 7th / minor 9th under the held note - the leading tone under a held tonic
            # once the chord moves to V)
            if not nxt:                                # (blind round g3: inner motion 0.22 - no chord tone in
                # reach: the whole step under / over the companion, a passing 9th / 6th - never a 2nd under the tune)
                sc = scale_at(n.start + h) if scale_at is not None else None
                nxt = [p for p in (low.pitch - 2, low.pitch + 2) if p >= lo and n.pitch - p >= 3
                       and all(abs(p - q.pitch) >= 2 for q in added if q is not low)
                       and (sc is None or p % 12 in sc) and (n.pitch - p) % 12 not in (1, 11)]
            if nxt:
                q = min(nxt, key=lambda p: (abs(p - low.pitch), -p))
                added = [x for x in added if x is not low] + [low._replace(dur=h), low._replace(
                    start=n.start + h, dur=n.dur - h, pitch=q, vel=_vel(low.vel * 0.92))]
        out += added
    return Clip._raw(out, clip.length)


def _under_held(notes):
    """A predicate over `notes`' notes: struck under a higher one of them still held a quarter beat past it (an inner
    voice under a held melody note, not the melody - the packets' '(under)')."""
    held = sorted((n.start, n.start + n.dur, n.pitch) for n in notes)
    h0 = [x[0] for x in held]

    def under(n):
        i0, i1 = bisect.bisect_left(h0, n.start - 8), bisect.bisect_left(h0, n.start - 0.05)
        return any(z_ > n.start + 0.25 and p_ > n.pitch for _, z_, p_ in held[i0:i1])
    return under


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
                  free_ms: float = 10.0, legato: float = 0.03, seed=0, lead=None, anticipate: float = 0.0,
                  anticipate_ms=(25.0, 55.0)) -> Clip:
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
      lead       lead(beat, velocity) -> ms: the melody note sounds that much EARLIER (the hammers' velocity
                 artifact against the accompaniment struck with it - Score.perform builds it from the left hand)
      anticipate the chance that a long note on an anchor (0.8 s+) follows the bass by anticipate_ms (lo, hi) ms
                 instead (the romantic bass anticipation)
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
            if anticipate > 0 and secs >= 0.8 and rng.random() < anticipate:
                ms += anticipate_ms[0] + (anticipate_ms[1] - anticipate_ms[0]) * rng.random()
        if i > 0:
            lp = abs(n.pitch - tops[i - 1].pitch)
            if lp >= leap:
                ms += leap_delay_ms(lp, agogic_ms / 12.0, agogic_ms, above=0)
        if 0 < i < len(tops) - 1 and secs >= 0.4 and n.pitch >= tops[i - 1].pitch + 2                 and n.pitch >= tops[i + 1].pitch + 2:
            ms += peak_ms
        ms += (rng.random() * 2 - 1) * free_ms
        if lead is not None:
            ms -= lead(s, n.vel)
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
                  flutter_ms: float = 280.0, flutter_to: float = 0.0, delay_ms: float = 0.0, half=(),
                  half_to: float = 0.6, vary: float = 0.0, seed=0) -> list:
    """Legato (syncopated) pedalling: at every harmony change in `changes` (beats) the pedal comes up `delay_ms`
    after the new bass (0 = with it; a pianist's foot follows the hand by 40-150 ms, Repp 1996 - the new keys are
    down by then, so their notes are caught) and goes down again `lift_ms` later (the old harmony cleared); up at
    `end`; `half` = beats of half changes (the pedal to `half_to` for `lift_ms`, `delay_ms` after the beat: the
    treble's dampers touch - a passing note cleared - while the bass rings on); `vary` > 0: the foot is no clock -
    every change's delay and lift x (72 / the tempo there) ** 0.5 (slower music, a slower foot) x a seeded
    1 + N(0, vary) (within 0.5..1.6);
    `dry` = (start, end) windows with the pedal up; `flutter` = (start, end) windows where the pedal is cleared
    every `flutter_ms` (up `lift_ms`, down again): chromatic fioriture and cadenzas over one harmony keep their
    bass and resonance but do not pile every passing note into a cluster. `flutter_to` = the pedal value of those
    quick lifts: 0 = fully up, 0.5-0.7 = a half pedal (the sampler's 0.5..1 range: the treble clears, the bass
    rings on). Points for 'instrument.pedal' (steps)."""
    ch = sorted({_num(float(c), 'pedal change') for c in changes})
    e = _num(float(end), 'pedal end')
    dl = _num(delay_ms, 'pedal delay_ms', 0, 400)
    hv = _num(half_to, 'pedal half_to', 0, 0.95)
    vr = _num(vary, 'pedal vary', 0, 1)
    rng = random.Random(seed_int(seed) + 29)

    def foot(ms, at):
        if not vr or not ms:
            return ms
        return ms * (72.0 / _bpm_at(bpm, at)) ** 0.5 * min(1.6, max(0.5, 1.0 + rng.gauss(0.0, vr)))
    pts = []
    for c in ch:
        if c >= e:
            break
        c0 = c + (_beats(foot(dl, c) / 1000.0, bpm, c) if dl else 0.0)
        up_len = _beats(foot(lift_ms, c) / 1000.0, bpm, c0)
        if pts and pts[-1][0] >= c0 - _EPS:
            pts = [p for p in pts if p[0] < c0 - _EPS]
        pts.append((round(c0, 6), 0.0, 'step'))
        pts.append((round(c0 + up_len, 6), 1.0, 'step'))
    for h in sorted({float(x) for x in half}):
        h0 = h + (_beats(foot(dl, h) / 1000.0, bpm, h) if dl else 0.0)
        h1 = h0 + _beats(foot(lift_ms, h) / 1000.0, bpm, h0)
        if h1 >= e or any(p[1] == 0.0 and h0 - 2 * (h1 - h0) <= p[0] <= h1 + _EPS for p in pts):
            continue                                  # a full change is there already
        pts += [(round(h0, 6), hv, 'step'), (round(h1, 6), 1.0, 'step')]
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


# ------------------------------------------------------------------------------------------------ expression rules

def travel_ms(vel, travel=None) -> float:
    """The hammer's travel time (ms) from the finger's push to the string at a velocity: a / (velocity + b) with
    (a, b) = ASYNC['travel'] - about 70 ms at velocity 36, 47 at 66, 36 at 90 (softer keys sound later; Goebl 2001
    measured this on a computer-monitored grand: the melody's lead is mostly this artifact)."""
    a, b = travel or ASYNC['travel']
    return float(a) / (max(1.0, float(vel)) + float(b))


def spread(clip: Clip, bpm, *, seed=0, travel=None, max_ms: float | None = None, sd_ms: float | None = None,
           tol: float = 0.02, hand: str = 'rh', ends=(), roll=None, roll_ms=None, arp: float | None = None,
           arp_ms=None) -> Clip:
    """Chord asynchrony: notes struck together (onsets within `tol` beats) sound in the order of their hammers -
    the loudest first, every softer one travel_ms(its velocity) - travel_ms(the loudest) later plus |N(0, sd_ms)|
    of the hand's own spread, at most `max_ms` (ASYNC). A voiced chord thereby leads with its melody note by a few
    ms (the right hand: the melody is in its chords).
    hand='lh': the left hand's chords (no melody in them) draw their roll per chord (ASYNC lh_roll): mostly near-
    simultaneous (half the velocity artifact + |N(0, sd_ms / 2)|), else rolled bottom-up (roll_ms per note, wider
    for a soft chord: x travel_ms(its mean velocity) / travel_ms(64), plus half the velocity artifact); a chord
    struck at one of the `ends` beats (a phrase's cadence chord) is arpeggiated with the chance `arp` (bottom-up,
    arp_ms per note, not capped by max_ms)."""
    mx = ASYNC['max_ms'] if max_ms is None else _num(max_ms, 'spread max_ms', 0, 200)
    sd = ASYNC['chord_sd_ms'] if sd_ms is None else _num(sd_ms, 'spread sd_ms', 0, 50)
    if hand not in ('rh', 'lh'):
        raise ComposeError(f"spread hand must be 'rh' or 'lh', got {hand!r}")
    p_up = (roll or ASYNC['lh_roll'])[1]
    rlo, rhi = roll_ms or ASYNC['roll_ms']
    p_arp = ASYNC['arp'] if arp is None else _num(arp, 'spread arp', 0, 1)
    alo, ahi = arp_ms or ASYNC['arp_ms']
    ends = [float(e) for e in ends]
    rng = random.Random(seed_int(seed) + 7)
    ns = sorted(clip, key=lambda n: (n.start, -n.vel, -n.pitch))
    out, i = [], 0
    while i < len(ns):
        j = i + 1
        while j < len(ns) and ns[j].start - ns[i].start <= tol:
            j += 1
        grp = ns[i:j]
        if len(grp) == 1:
            out.append(grp[0])
        elif hand == 'rh':
            ref = travel_ms(max(n.vel for n in grp), travel)
            out.append(grp[0])
            for n in grp[1:]:
                ms = min(mx, max(0.0, travel_ms(n.vel, travel) - ref) + abs(rng.gauss(0.0, sd)))
                d = _beats(ms / 1000.0, bpm, n.start)
                out.append(n._replace(start=n.start + d, dur=max(0.03, n.dur - d)))
        else:
            ref = travel_ms(max(n.vel for n in grp), travel)
            up = sorted(grp, key=lambda n: n.pitch)
            soft = travel_ms(sum(n.vel for n in grp) / len(grp), travel) / travel_ms(64, travel)
            if any(abs(grp[0].start - e) <= tol for e in ends) and rng.random() < p_arp:
                step, cap = rng.uniform(alo, ahi), None
            elif rng.random() < p_up:
                step, cap = rng.uniform(rlo, rhi) * soft, mx
            else:
                step, cap = None, mx
            ms = [0.5 * max(0.0, travel_ms(n.vel, travel) - ref) + (abs(rng.gauss(0.0, sd * 0.5)) if step is None
                                                                     else k * step) for k, n in enumerate(up)]
            m0 = min(ms)                             # the chord's first note sounds where it was written
            for n, x in zip(up, ms):
                x -= m0
                ms_ = x if cap is None else min(cap, x)
                if ms_ <= 0:
                    out.append(n)
                    continue
                d = _beats(ms_ / 1000.0, bpm, n.start)
                out.append(n._replace(start=n.start + d, dur=max(0.03, n.dur - d)))
        i = j
    return Clip._raw(out, clip.length)


def articulate(clip: Clip, bpm, *, repeat_ms=None, leap: int | None = None, leap_ms=None, legato=None,
               legato_ms=None, seed=0) -> Clip:
    """The melody's articulation (the top note of every onset; Director Musices' repetition and leap articulation):
    a key struck again is let go 25 % of the time between the two onsets earlier (within repeat_ms (lo, hi): the key
    has to come up for the hammer to strike again), and the note before a leap of `leap`+ semitones lets go
    leap_ms (lo at the leap, hi at two octaves) before the next onset (the hand travels). Every other note tied to
    the next one (legato: it ends at or after the next onset) overlaps it by `legato` = (mean, sd) x the IOI, within
    legato_ms (lo, hi) - the finger legato's key overlap grows with the IOI and is never the same twice (Bresin &
    Battel 2000; seeded). Defaults ARTICULATION. Nothing gets shorter than half its sounding time."""
    a = ARTICULATION
    rlo, rhi = repeat_ms or a['repeat_ms']
    lp = a['leap'] if leap is None else int(leap)
    llo, lhi = leap_ms or a['leap_ms']
    km, ks = legato or a['legato']
    klo, khi = legato_ms or a['legato_ms']
    rng = random.Random(seed_int(seed) + 17)
    ns = sorted(clip, key=lambda n: (n.start, -n.pitch))
    tops = []
    for i, n in enumerate(ns):
        if tops and abs(n.start - tops[-1][1].start) < 0.02:
            continue
        p = tops[-1][1] if tops else None
        if p is not None and n.pitch < p.pitch and p.start + p.dur > n.start + 0.05:
            continue                                  # (an inner voice moving under a held top note is no melody
            #                                           note: new-age round g9 - the alto's move let the held theme
            #                                           note go at a 'leap' down to it, half the heads lost their top)
        tops.append((i, n))
    out = list(ns)
    for k, (i, n) in enumerate(tops[:-1]):
        nx = tops[k + 1][1]
        end = n.start + n.dur
        if end < nx.start - _EPS:
            continue                                  # a rest: already detached
        ioi_ms = (nx.start - n.start) * 60000.0 / _bpm_at(bpm, n.start)
        iv = abs(nx.pitch - n.pitch)
        ms = 0.0
        if iv == 0:
            ms = min(rhi, max(rlo, 0.25 * ioi_ms))
        elif iv >= lp:
            ms = llo + (lhi - llo) * min(1.0, (iv - lp) / max(1, 24 - lp))
        if ms <= 0:
            kot = min(khi, max(klo, max(0.0, rng.gauss(km, ks)) * ioi_ms))
            if end <= nx.start + _beats(0.25, bpm, nx.start):       # tied (not held on under the next notes)
                out[i] = n._replace(dur=nx.start - n.start + _beats(kot / 1000.0, bpm, nx.start))
            continue
        new_end = nx.start - _beats(ms / 1000.0, bpm, nx.start)
        out[i] = n._replace(dur=max(0.5 * min(n.dur, nx.start - n.start), new_end - n.start))
    return Clip._raw(out, clip.length)


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
        if isinstance(rh, Clip):                          # composed notes (an endless tune): grouped by onset
            plain: dict = {}
            for x in rh:
                plain.setdefault(round(x.start, 4), []).append(x)
            self.events = sorted((Event('note' if len(ns) == 1 else 'chord', at, max(x.dur for x in ns),
                                        sorted(x.pitch for x in ns), 1.0) for at, ns in plain.items()),
                                 key=lambda e: e.at)
            self.line = rh
            last = int(math.ceil((max(rh.length, max((x.start + x.dur for x in rh), default=0.0)) - self.pickup)
                                 / self.bar_beats - _EPS))
            rh = None
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
    def rubato(self, song, *, depth: float = 0.04, phrase: str = 'drawn', shapes=None, seed=None, bars=None,
               overlap: float | None = None, table: dict | None = None) -> None:
        """song.rubato over every phrase (in the bars range (first, last) when given), depth, seed (None: the song's;
        an int; 'bar' = the phrase's first bar). phrase='drawn' (the default): every phrase draws its own arch from
        PHRASE_TEMPO (`table` overrides keys) - its depth x U(depth range), nearly straight at the 'straight' share,
        its peak and final lengthening by its level ('phrase', every second one a 'period', the last the 'end');
        else a song.rubato shape name (or `shapes` cycled phrase by phrase). Two phrases that share a bar meet
        `overlap` beats into it (the bar's last beat is the next phrase's pickup)."""
        T = dict(PHRASE_TEMPO)
        for k, v in (table or {}).items():
            if k not in T:
                raise ComposeError(f"rubato table: unknown key {k!r}; use {', '.join(T)}")
            T[k] = v
        drawn = phrase == 'drawn' and not shapes
        sel = [(i, ab) for i, ab in enumerate(self.phrases)
               if bars is None or (bars[0] <= ab[0] and ab[1] <= bars[1])]
        for n, (i, (a, b)) in enumerate(sel):
            shared_start = overlap is not None and any(b0 == a for _, b0 in self.phrases)
            shared_end = overlap is not None and any(a0 == b for a0, _ in self.phrases)
            span = (self.bar(a) + (overlap if shared_start else 0),
                    self.bar(b) + (overlap if shared_end else self.bar_beats))
            sd = a if seed == 'bar' else seed
            if not drawn:
                song.rubato(span, depth=depth, phrase=shapes[i % len(shapes)] if shapes else phrase, seed=sd)
                continue
            key = f"{song.seed if seed in (None, 'bar') else seed}:phrase:{a}"
            rng = random.Random(seed_int(key))
            level = 'end' if n == len(sel) - 1 else 'period' if n % 2 else 'phrase'
            f = rng.uniform(*T['depth'])
            if rng.random() < T['straight']:
                f *= 0.2
            song.rubato(span, depth=min(0.25, depth * f), seed=seed_int(key) % 100003,
                        peak=rng.uniform(*T['peak'][level]), close=rng.uniform(*T['close'][level]))

    def lilt(self, song, span, *, beats=None, jitter: float = 0.0, seed=None, table: dict | None = None) -> None:
        """song.lilt over `span` phrase by phrase: every phrase draws how much of the beat lilt it plays (PHRASE_TEMPO
        lilt: x U(lo, hi), some phrases keep an even pulse) and the jitter x lilt_jitter - not one fixed beat delay
        in every bar of the piece (a sawtooth in the tempo map). Bars outside the phrases draw like a phrase."""
        T = dict(PHRASE_TEMPO)
        T.update(table or {})
        s0, s1 = (span.start, span.end) if hasattr(span, 'start') else (float(span[0]), float(span[1]))
        cuts = sorted({s0, s1} | {self.bar(a) for a, _ in self.phrases if s0 < self.bar(a) < s1})
        for x0, x1 in zip(cuts, cuts[1:]):
            if x1 - x0 < self.bar_beats - _EPS:
                continue
            key = f"{song.seed if seed is None else seed}:lilt:{x0:g}"
            rng = random.Random(seed_int(key))
            f = rng.uniform(*T['lilt'])
            try:
                song.lilt((x0, x1), beats={k: v * f for k, v in (beats or {}).items()},
                          jitter=jitter * T['lilt_jitter'], seed=seed_int(key) % 100003)
            except ComposeError as e:
                if 'holds no whole bar' not in str(e):
                    raise

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
                roll_bpm=None, anchors: str = 'half', pedal_opts=None, plain: bool = False, figures=None,
                figure_vel: float = 41, inner: float | None = None, figure_opts: dict | None = None,
                rules: dict | None = None, balance=None, line: dict | None = None) -> dict:
        """Play the score like a romantic pianist (the nocturne etude's measured pipeline):
          left hand first (the timekeeper: the tempo map knows its onsets) - accompany() per entry (`accompany`
            options: vel 38, bass 1.2, first 1.0, second 0.88, top 1.06, roll_ms 14), the dynamics at a gentler
            slope (factor ** lh_dyn)
          right hand - the velocities from a touch() over the melody's principal notes (`touch` options: lo 64,
            hi 96, gap 1/4, start 0.55, end 0.4, pitch 0.9; each phrase end takes `breath` beats of air for it),
            accents x their factor (at most `accent_cap`), then every ornament in real time at the tempo map:
            ^tr = trill() landing on the next note, ^turn = turn(), ^fig = fioritura() (ease 0.2 when even, 0.8
            else, flatter where the tempo moves on too fast for it; lighter in the middle), ^roll chords =
            pianist.roll at `roll_bpm` (default the song tempo); then
            lean_on_long, cantabile, the dynamics, melody_rubato (`rubato` options: sync_ms 42, seed 3; anchors at
            every half bar) and a cap (`cap`: the climax sings, not bangs)
          figures - instead of accompany() entries a BROKEN-CHORD left hand: [(at, beats, chord symbol, figure)] with
            figure a pianist.FIGURES name (flowing 8ths over a 10th, rocking, walking 10ths, a waltz's oom-pah-pah,
            'half' / 'still' under a breath ...; a fifth item {option: value} overrides `figure_opts` for that
            entry - a raised cap, mirror) at `figure_vel`, its dynamics by ACCOMPANIMENT (a drawn swell per
            phrase, the bass / figure balance shifting, swelling into tension chords, following the melody and a
            budget under it; plain: +-8 %), the dynamics at the gentler slope; its chords rolled per chord
            (spread hand='lh': together / bottom-up, an arpeggiated cadence chord now and then); the pedal
            changes with every entry's chord; `figure_opts`: pianist.figure's register
            ({'bass_lo': the lowest bass, 'cap': the top} - an e-piano's hand sits higher than a grand's)
          balance - the hands' balance plan for the broken-chord hand: [(from beat, to beat, dB)] - a phrase starting
            in a span is played with the left hand's summed note energy (ENERGY_EXP) that many dB under the right
            hand's (negative: the hand leads; a later span wins), both ways, and the hands give and take inside it
            (ACCOMPANIMENT give / take / lead_end); None: the fixed budget (below_db, only ever down)
          line - the melody as ONE dynamic line per phrase (HUMAN_FEEDBACK 2026-10-15: "note by note, not
            flowing" - neighbouring melody notes 5-7 velocity steps apart, each placed on its own): {'keep': the
            share of each note's own velocity kept (the rest a smoothed arc over its neighbours), 'step': the
            largest step between neighbouring melody notes, 'accent': a note this far over the arc keeps its
            accent, 'range' / 'stretch': the smoothed arc stretched back to that share of the phrase's own range,
            at most x stretch} - the notes under a melody note move with it (_line); None: as the rules place them
          inner - the right hand's own chords voiced to the top: the notes under the melody x inner (0.78: the
            sixths / thirds under a long note, the climax's chords sing softer than the tune)
          pedal - pedal_changes() with the harmony (the left hand's bass + chord) `delay_ms` after it, a half change
            where the melody resolves a non-chord tone inside a long harmony, cleared in chromatic figures
            (`pedal_opts` over PEDAL: delay_ms 60, lift_ms 110, half_to 0.6, flutter_ms 320, flutter_to 0.6, tail 2
            beats after the last bar)
          the expression rules (RULES - docs/PIANIST_RULES.md; `rules` = {family: {key: value}} overrides): the
            melody's lead over the left hand and every chord's spread as the hammers' velocity artifact (ASYNC), the
            melodic and harmonic charge of the figures' chords (CHARGE), the melody's repetition / leap articulation
            (ARTICULATION), the pedal's timing (PEDAL)
        plain=True: the score as the plain tools read it - the etude's 'before' baseline for an A/B: every
        left-hand strike at one level (humanized), the figures on an even grid, pianist.trill / turn, chords rolled
        25 ms, the dynamics as crescendo spans, no singing line, no rubato, no cleared pedal.
        Returns {'rh': Clip, 'lh': Clip, 'pedal': points, 'figures': [(clip, bpm, at)]}."""
        bpm = song.tempo_at
        out: dict = {'figures': []}
        R = {k: dict(v) for k, v in RULES.items()}
        for fam, kv in (rules or {}).items():
            if fam not in R:
                raise ComposeError(f"perform rules: unknown family {fam!r}; use {', '.join(R)}")
            for k in kv:
                if k not in R[fam]:
                    raise ComposeError(f"perform rules[{fam!r}]: unknown key {k!r}; use {', '.join(R[fam])}")
            R[fam].update(kv)
        A = R['async']
        rg, lg = getattr(rh_track, '_groove', None), getattr(lh_track, '_groove', None)
        if not plain and rg is not None and lg is not None and rg.late_ms != lg.late_ms:
            # one player: the right hand sits where the left hand sits (a band feel lays the melody back against
            # the comping - here the melody's timing against the left hand is ASYNC's and melody_rubato's)
            import dataclasses
            rh_track.groove(dataclasses.replace(rg, late_ms=lg.late_ms))
        fig_changes, lh_later = [], False
        harmony = []                                   # [(beat, chord symbol)]: the figures' chords
        if figures:
            last = None
            for at, beats, sym, fig, *_ in sorted(figures, key=lambda f: f[0]):
                if sym != last:
                    harmony.append((float(at), sym))
                last = sym
        chord_at = self._chord_at(harmony) if harmony else None
        if figures and lh_track is not None:
            from . import pianist
            rng = random.Random(seed_int(len(figures)) + 41)
            ns, last = [], None
            fo = dict(figure_opts or {})
            if fo.get('repeats'):                      # (the repeated-tone budget runs over the figures)
                fo['recent'] = []
            for at, beats, sym, fig, *own in sorted(figures, key=lambda f: f[0]):
                ns += pianist.figure(sym, fig, at, beats, vel=figure_vel, bar=self.bar_beats, rng=rng,
                                     **(dict(fo, **own[0]) if own and own[0] else fo))
                if sym != last:
                    fig_changes.append(round(float(at), 4))
                last = sym

            AC = R['accompaniment']
            lh = Clip._raw(ns, max(n.start + n.dur for n in ns))
            if not plain:
                lh = self._lh_arc(lh, AC, seed=len(ns))
            else:
                lh = Clip._raw([self._swell(n) for n in lh], lh.length)
            if self.dyn:
                lh = dynamics(lh, [(b, LEVELS[lv] ** lh_dyn) for b, lv in self.dyn])
            if not plain:
                if self.key is not None:
                    lh = harmonic_charge(lh, harmony, self.key, vel=AC['charge'] * lh_dyn, table=R['charge']['pcs'],
                                         tension=AC['tension'])
                ends = []                                  # the cadence chord of every phrase
                for a, b in self.phrases:
                    hs = [t for t, _ in harmony if self.bar(a) - _EPS <= t < self.bar(b + 1) - _EPS]
                    if hs:
                        ends.append(hs[-1])
                lh = spread(lh, bpm, seed=len(ns), travel=A['travel'], max_ms=A['max_ms'], sd_ms=A['chord_sd_ms'],
                            hand='lh', ends=ends, roll=A['lh_roll'], roll_ms=A['roll_ms'], arp=A['arp'],
                            arp_ms=A['arp_ms'])
            out['lh'] = lh
            lh_later = True
        elif self.entries and lh_track is not None:
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
                if getattr(lh_track, '_body', None) is not None:
                    ac['jitter_ms'] = 0.0          # a body on the track: its motor noise replaces the jitter
                ac.update(accompany or {})
                for st, ln, bass, c1, c2, pat in self.entries:
                    ns += list(_accompany([(st, ln, bass, c1, c2)], bpm, pattern=pat, seed=int(st * 3), **ac))
                lh = Clip._raw(ns, max(n.start + n.dur for n in ns))
                if self.dyn:
                    lh = dynamics(lh, [(b, LEVELS[lv] ** lh_dyn) for b, lv in self.dyn])
                lh = spread(lh, bpm, seed=len(ns), travel=A['travel'], max_ms=A['max_ms'], sd_ms=A['chord_sd_ms'],
                            hand='lh', roll=A['lh_roll'], roll_ms=A['roll_ms'])
            lh_track.play(lh, 0)
            out['lh'] = lh
        if self.events:
            if getattr(rh_track, '_body', None) is not None and not plain:
                # a body on the track (humanize body=): it moves the leaps and adds the motor noise, coupled to the
                # phrase (the score's phrases are its phrases); melody_rubato keeps the hands' independence
                rubato = dict(dict(free_ms=0.0, agogic_ms=0.0), **(rubato or {}))
                rh_track.mark_phrases(*[self.bar(a) for a, _ in self.phrases])
            lead = None if plain or out.get('lh') is None else self._lead(out['lh'], A)
            rh = self._right_hand(song, bpm, touch, breath, rubato, cap, accent_cap, roll_bpm, anchors, out, plain,
                                  R=R, chord_at=chord_at, harmony=harmony, lead=lead)
            if inner is not None:                    # voice the top: the notes under the melody sing softer
                f = _num(inner, 'perform inner', 0.3, 1)
                tops: dict = {}
                for n in rh:
                    k = round(n.start, 2)
                    tops[k] = max(tops.get(k, 0), n.pitch)
                # (new-age round g13: an inner voice struck alone under a held melody note - the moving alto of
                # harmonize(move=) - was its onset's top and sang at the melody's level, MYUS's Bb4 v79 under E5 v84:
                # a note struck under a higher one still held a quarter beat past it is an inner note too)
                under = _under_held(rh)
                rh = Clip._raw([n if n.pitch == tops[round(n.start, 2)] and not under(n)
                                else n._replace(vel=_vel(n.vel * f)) for n in rh], rh.length)
            if line and not plain:
                rh = self._line(rh, line, inner=inner is not None)
            if not plain:
                rh = spread(rh, bpm, seed=len(self.events), travel=A['travel'], max_ms=A['max_ms'],
                            sd_ms=A['chord_sd_ms'])
            rh_track.play(rh, 0)
            out['rh'] = rh
        if lh_later:                                   # the broken-chord hand under the tune: follow it, stay below
            if not plain and out.get('rh') is not None:
                out['lh'] = self._lh_under(out['lh'], out['rh'], R['accompaniment'], balance=balance)
            lh_track.play(out['lh'], 0)
        if pedal:
            po = {k: v for k, v in R['pedal'].items() if k not in ('half_beats', 'same_bass')}
            if plain:
                po.update(delay_ms=0.0, vary=0.0)
            po.update(pedal_opts or {})
            tail = po.pop('tail')
            changes, last = list(fig_changes), None
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
            half = [] if plain or chord_at is None or 'rh' not in out else \
                self._half_changes(out['rh'], harmony, R['pedal']['half_beats'])
            if not plain and R['pedal']['same_bass'] == 'half' and len(harmony) > 1:
                # a new chord over the same bass (a colour change, a suspension resolving, a pedal point): the
                # bass rings on - a half change clears the treble only
                from .theory import chord as _chord
                keep = {round(b1, 4) for (b0, s0), (b1, s1) in zip(harmony, harmony[1:])
                        if _chord(s0).bass_pc % 12 == _chord(s1).bass_pc % 12}
                half += sorted(c for c in changes if round(c, 4) in keep)
                changes = [c for c in changes if round(c, 4) not in keep]
            ped = pedal_changes(changes, end=self.end + tail, bpm=bpm, flutter=flutter, half=half, seed=len(changes),
                                **po)
            for t in (rh_track, lh_track):
                if t is not None:
                    t.automate('instrument.pedal', ped)
            out['pedal'] = ped
        return out

    def _line(self, rh: Clip, opts: dict, inner: bool = False) -> Clip:
        """perform(line=): per phrase, the melody's velocities (each onset's top note, notes over 1/3 beat - the
        figures and ornaments keep their own shape) pulled toward a smoothed arc (a triangular mean over two
        neighbours each side) - opts['keep'] of the note's own kept, an accent opts['accent'] over the arc stays -
        then the steps between neighbours limited to opts['step'] (forward and back, averaged); every note struck
        with a melody note scaled with it. inner (perform(inner=) given): a note struck under a held higher one is
        an inner voice, not on the line (_under_held)."""
        keep, step, acc = opts.get('keep', 0.4), opts.get('step', 4.0), opts.get('accent', 14.0)
        groups: dict = {}
        for n in rh:
            groups.setdefault(round(n.start, 2), []).append(n)
        # (new-age round g13: an inner voice struck alone under a held melody note is no melody note - pulled to the
        # line's arc it sang at the tune's level, MYUS's Bb4 v79 under E5 v84: _under_held)
        under = _under_held(rh) if inner else (lambda n: False)
        starts = sorted(k for k in groups if not under(max(groups[k], key=lambda n: n.pitch)))
        bounds = [self.bar(a) for a, _ in self.phrases] + [float('inf')]
        new_v: dict = {}
        for a, z in zip(bounds, bounds[1:]):
            ks = [k for k in starts if a - 0.05 <= k < z - 0.05 and max(groups[k], key=lambda n: n.pitch).dur > 1 / 3]
            if len(ks) < 3:
                continue
            v = [float(max(groups[k], key=lambda n: n.pitch).vel) for k in ks]
            arc = []
            for i in range(len(v)):
                w = [(v[j], 3 - abs(j - i)) for j in range(max(0, i - 2), min(len(v), i + 3))]
                arc.append(sum(x * k for x, k in w) / sum(k for _, k in w))
            t = [x if x - m >= acc else keep * x + (1 - keep) * m for x, m in zip(v, arc)]
            f, b_ = list(t), list(t)
            for i in range(1, len(t)):
                f[i] = min(f[i - 1] + step, max(f[i - 1] - step, f[i])) if v[i] - arc[i] < acc else f[i]
            for i in range(len(t) - 2, -1, -1):
                b_[i] = min(b_[i + 1] + step, max(b_[i + 1] - step, b_[i])) if v[i] - arc[i] < acc else b_[i]
            sm = [(x + y) / 2 for x, y in zip(f, b_)]
            # (the phrase keeps its dynamic range: the smoothed arc stretched back toward the notes' own spread -
            # one line that swells and falls, not a flattened one)
            r0, r1 = max(v) - min(v), max(sm) - min(sm)
            mu = sum(sm) / len(sm)
            k_ = min(opts.get('stretch', 1.6), max(1.0, opts.get('range', 0.9) * r0 / max(1e-6, r1)))
            for k, x, v0 in zip(ks, sm, v):
                new_v[k] = (mu + (x - mu) * k_) / max(1.0, v0)
        if not new_v:
            return rh
        return Clip._raw([n._replace(vel=_vel(n.vel * new_v[round(n.start, 2)])) if round(n.start, 2) in new_v
                          else n for n in rh], rh.length)

    def _plain_dyn(self, clip: Clip, power: float) -> Clip:
        """perform(plain=True): the dynamics with the tools that existed - humanize.crescendo per span of marks."""
        from .humanize import crescendo
        pts = [(b, LEVELS[lv] ** power) for b, lv in self.dyn]
        for (b0, l0), (b1, l1) in zip(pts, pts[1:]):
            if b1 > b0:
                clip = crescendo(clip, l0, l1, span=(b0, b1 - 1e-3))
        return clip

    def _phrase_of(self, t):
        """(index, first beat, last beat) of the phrase holding beat t (a shared bar belongs to the later phrase), or
        None."""
        hit = None
        for i, (a, b) in enumerate(self.phrases):
            if self.bar(a) - _EPS <= t < self.bar(b + 1) - _EPS:
                hit = (i, self.bar(a), self.bar(b + 1))
        return hit

    def _swell(self, n):
        """The plain left hand's swell: +-8 % over every phrase."""
        for a, b in self.phrases:
            if self.bar(a) <= n.start < self.bar(b + 1):
                x = (n.start - self.bar(a)) / max(_EPS, self.bar(b + 1) - self.bar(a))
                return n._replace(vel=_vel(n.vel * (0.92 + 0.16 * math.sin(math.pi * x))))
        return n

    def _lh_arc(self, lh: Clip, AC: dict, seed=0) -> Clip:
        """The left hand's phrase arc (ACCOMPANIMENT): per phrase a swell of drawn size cresting at a drawn place,
        and the bass against the figure drawn at the phrase's start and end (linear between); the bass is the lowest
        note of every harmony span (and its octaves)."""
        from .tempo import _shaped
        rng = random.Random(seed_int(seed) + 61)
        draws = [(rng.uniform(*AC['arc']), rng.uniform(*AC['peak']), rng.uniform(*AC['bass']),
                  rng.uniform(*AC['bass'])) for _ in self.phrases]
        ns = sorted(lh, key=lambda n: (n.start, n.pitch))
        low: dict = {}                                 # the bass pitch class per bar
        for n in ns:
            k = int((n.start - self.pickup + _EPS) // self.bar_beats)
            if k not in low or n.pitch < low[k]:
                low[k] = n.pitch
        out = []
        for n in ns:
            ph = self._phrase_of(n.start)
            if ph is None:
                out.append(n)
                continue
            i, s0, s1 = ph
            arc, pk, b0, b1 = draws[i]
            x = min(1.0, max(0.0, (n.start - s0) / max(_EPS, s1 - s0)))
            f = 1.0 + arc * (_shaped(x, pk, 0.0) - 0.5)
            lo = low[int((n.start - self.pickup + _EPS) // self.bar_beats)]
            if n.pitch % 12 == lo % 12 and n.pitch <= lo + 12:
                f *= b0 + (b1 - b0) * x
            out.append(n._replace(vel=_vel(n.vel * f)))
        return Clip._raw(out, lh.length)

    def _lh_under(self, lh: Clip, rh: Clip, AC: dict, balance=None) -> Clip:
        """The left hand under the melody (ACCOMPANIMENT): it follows the melody's level (x (the melody's last
        note / its phrase mean) ** follow) and every phrase's median stays below_db under the melody's - where the
        melody plays (a note within the last bar); alone the hand keeps its level.
        balance [(from beat, to beat, dB)]: every phrase with a melody is set to its span's dB under the right hand
        (the phrase's summed note energy, ENERGY_EXP; up or down, within AC 'scale', never raised over the phrase's
        loudest melody note; a later span wins), and inside it the hand gives and takes: x take under a
        melody note just struck, rising to x give where the tune holds a note or rests (from give_beats[0] beats
        after its onset to full at give_beats[1]; x 1 + lead_end more of it in the phrase's last bar) - the
        notes beyond a bar of melody silence inside such a phrase too."""
        if balance is not None:
            return self._lh_balance(lh, rh, AC, balance)
        tops: dict = {}
        for n in rh:
            k = round(n.start, 2)
            if k not in tops or n.pitch > tops[k].pitch:
                tops[k] = n
        mel = sorted(tops.values(), key=lambda n: n.start)
        if not mel:
            return lh
        import bisect
        import statistics
        ts = [n.start for n in mel]
        by: dict = {}
        for n in mel:
            ph = self._phrase_of(n.start)
            by.setdefault(None if ph is None else ph[0], []).append(n.vel)
        fol = _num(AC['follow'], 'accompaniment follow', 0, 2)
        out, groups = [], {}
        for n in lh:
            ph = self._phrase_of(n.start)
            key = None if ph is None else ph[0]
            mv = by.get(key)
            j = bisect.bisect_right(ts, n.start + 0.02) - 1
            if not mv or j < 0 or n.start - mel[j].start > self.bar_beats:
                out.append(n)                      # the hand alone (an intro, a bar of air): its own level
                continue
            n = n._replace(vel=_vel(n.vel * (mel[j].vel / (sum(mv) / len(mv))) ** fol))
            groups.setdefault(key, []).append(len(out))
            out.append(n)
        cap = 10 ** (-_num(AC['below_db'], 'accompaniment below_db', 0, 30) / 20)
        for key, idx in groups.items():
            mv = by.get(key)
            if not mv:
                continue
            ratio = statistics.median(out[k].vel for k in idx) / statistics.median(mv)
            if ratio > cap:
                for k in idx:
                    out[k] = out[k]._replace(vel=_vel(out[k].vel * cap / ratio))
        return Clip._raw(out, lh.length)

    def _lh_balance(self, lh: Clip, rh: Clip, AC: dict, balance) -> Clip:
        """_lh_under with a balance plan (see there)."""
        import bisect
        spans = []
        for sp in balance:
            if not isinstance(sp, (tuple, list)) or len(sp) != 3:
                raise ComposeError(f"perform balance: [(from beat, to beat, dB)], got {sp!r}")
            spans.append((float(sp[0]), float(sp[1]), _num(sp[2], 'perform balance dB', -12, 18)))
        g0, g1 = AC['give_beats']
        if not 0 <= g0 < g1:
            raise ComposeError(f"accompaniment give_beats: (from, full) beats with 0 <= from < full, got {(g0, g1)}")
        give = _num(AC['give'], 'accompaniment give', 1, 2)
        take = _num(AC['take'], 'accompaniment take', 0.5, 1)
        lead_end = _num(AC['lead_end'], 'accompaniment lead_end', 0, 1)
        lo_s, hi_s = AC['scale']
        tops: dict = {}
        for n in rh:
            k = round(n.start, 2)
            if k not in tops or n.pitch > tops[k].pitch:
                tops[k] = n
        mel = sorted(tops.values(), key=lambda n: n.start)
        if not mel:
            return lh
        ts = [n.start for n in mel]
        by: dict = {}
        for n in mel:
            ph = self._phrase_of(n.start)
            by.setdefault(None if ph is None else ph[0], []).append(n.vel)
        fol = _num(AC['follow'], 'accompaniment follow', 0, 2)
        out, groups = [], {}
        for n in lh:
            ph = self._phrase_of(n.start)
            key = None if ph is None else ph[0]
            mv = by.get(key)
            j = bisect.bisect_right(ts, n.start + 0.02) - 1
            if not mv or j < 0 or key is None:
                out.append(n)                      # a phrase without the melody (an intro): the hand's own level
                continue
            m = mel[j]
            since = n.start - m.start
            near = since <= self.bar_beats
            f = (m.vel / (sum(mv) / len(mv))) ** fol if near else 1.0
            rest = m.start + m.dur < n.start - 0.05 or not near     # the tune rests (or is far away)
            x = 1.0 if rest else min(1.0, max(0.0, (since - g0) / (g1 - g0)))
            f *= take + (give - take) * x
            if x > 0 and n.start >= ph[2] - self.bar_beats - _EPS:
                f *= 1 + lead_end * x               # the phrase's last bar: the hand leads the way on
            groups.setdefault(key, []).append(len(out))
            out.append(n._replace(vel=_vel(n.vel * f)))
        for key, idx in groups.items():
            s0 = self.phrases[key]
            start, end = self.bar(s0[0]), self.bar(s0[1] + 1)
            db = None
            for a, z, d in spans:
                if a - _EPS <= start < z - _EPS:
                    db = d
            if db is None:
                continue
            er = sum(_energy(n.vel) for n in rh if start - _EPS <= n.start < end - _EPS)
            el = sum(_energy(out[k].vel) for k in idx)
            if er <= 0 or el <= 0:
                continue
            f = min(hi_s, max(lo_s, 10 ** ((10 * math.log10(er / el) - db) / (10 * ENERGY_EXP))))
            top = max(n.vel for n in rh if start - _EPS <= n.start < end - _EPS)
            for k in idx:                          # (never a strike over the phrase's loudest melody note)
                out[k] = out[k]._replace(vel=min(_vel(out[k].vel * f), max(out[k].vel, top)))
        return Clip._raw(out, lh.length)

    def _chord_at(self, harmony):
        """chord_at(beat) -> the chord symbol in force there from [(beat, symbol)] (None before the first)."""
        import bisect
        ts = [b for b, _ in harmony]

        def at(t):
            i = bisect.bisect_right(ts, t + 1e-4) - 1
            return harmony[i][1] if i >= 0 else None
        return at

    def _lead(self, lh: Clip, A: dict):
        """lead(beat, velocity) -> ms the melody note sounds before the left hand struck with it: the hammers'
        travel-time difference (ASYNC travel, max_ms) + N(0, sd_ms), none where the left hand strikes nothing."""
        at: dict = {}
        for n in lh:
            k = round(n.start, 2)
            at[k] = max(at.get(k, 0), n.vel)
        rng = random.Random(seed_int(len(lh)) + 13)

        def lead(beat, vel):
            v = at.get(round(beat, 2))
            if v is None:
                return 0.0
            ms = travel_ms(v, A['travel']) - travel_ms(vel, A['travel']) + rng.gauss(0.0, A['sd_ms'])
            return max(-A['max_ms'], min(A['max_ms'], ms))
        return lead

    def _half_changes(self, rh: Clip, harmony, min_beats: float) -> list:
        """Beats of half pedal changes: inside a harmony held `min_beats` or longer, where the melody resolves a
        non-chord tone by step into a chord tone (the passing / neighbour note is cleared, the bass rings on)."""
        from .theory import chord as _chord
        tops: dict = {}
        for n in rh:
            k = round(n.start, 2)
            if k not in tops or n.pitch > tops[k].pitch:
                tops[k] = n
        line = [tops[k] for k in sorted(tops)]
        spans = [(b, harmony[i + 1][0] if i + 1 < len(harmony) else self.end, sym)
                 for i, (b, sym) in enumerate(harmony)]
        out = []
        for a, z, sym in spans:
            if z - a < min_beats - _EPS:
                continue
            c = _chord(sym)
            tones = {(c.root + i) % 12 for i in c.intervals} | {c.bass_pc % 12}
            ins = [n for n in line if a - 0.1 <= n.start < z - 0.1]
            for p, q in zip(ins, ins[1:]):
                if q.start > a + 0.5 and p.pitch % 12 not in tones and q.pitch % 12 in tones and \
                        0 < abs(q.pitch - p.pitch) <= 2:
                    out.append(round(q.start, 4))
        return out

    def _right_hand(self, song, bpm, touch_opts, breath, rubato_opts, cap, accent_cap, roll_bpm, anchors, out,
                    plain=False, R=None, chord_at=None, harmony=(), lead=None):
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
                # too fast where the phrase moves on: the pianist flattens the gesture
                eases = [kw.pop('ease')] if 'ease' in kw else [0.2] if shape == 'even' else [0.8, 0.55, 0.3, 0.0]
                kw.setdefault('dip', 7 if len(e.pitches) > 5 else 4)
                for k, ez in enumerate(eases):
                    try:
                        f = fioritura(list(e.pitches), d, bpm, at=at, shape=shape, vel=(v, v - 6), seed=int(at * 7),
                                      ease=ez, **kw)
                        break
                    except ComposeError as err:
                        if 'max_rate' not in str(err) or k == len(eases) - 1:
                            raise
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
                bpm_ = max(20.0, _bpm_at(bpm, at))     # (under a deep rit + fermata: the ornament's floor)
                notes_ += list(pianist.mordent(e.pitch, d, bpm_, key=self.key or song.key, vel=v, at=at, **kw))
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
        R = R or RULES
        A = R['async']
        rh = lean_on_long(rh, bpm, gain=10)
        if chord_at is not None:
            rh = melodic_charge(rh, chord_at, vel=R['charge']['melodic'], table=R['charge']['pcs'])
        rh = cantabile(rh, bpm)
        if self.dyn:
            rh = dynamics(rh, list(self.dyn))
        if harmony and self.key is not None:
            rh = harmonic_charge(rh, harmony, self.key, vel=R['charge']['harmonic'], table=R['charge']['pcs'])
        ro = dict(sync_ms=A['sync_ms'], lean_ms=A['lean_ms'], peak_ms=A['peak_ms'], seed=3, lead=lead,
                  anticipate=A['anticipate'], anticipate_ms=A['anticipate_ms'], late_ms=0.0)   # (the bass-first
        # style is the anticipation's: a share of the long anchor notes, not every downbeat late)
        ro.update(rubato_opts or {})
        if anchors == 'half':
            anc = [self.bar(k) + h * self.bar_beats / 2 for k in range(1, self.bars + 1) for h in (0, 1)]
        elif anchors == 'bar':
            anc = [self.bar(k) for k in range(1, self.bars + 1)]
        else:
            anc = list(anchors)
        rh = melody_rubato(rh, anc + [self.end], bpm, **ro)
        ar = R['articulation']
        rh = articulate(rh, bpm, repeat_ms=ar['repeat_ms'], leap=ar['leap'], leap_ms=ar['leap_ms'],
                        legato=ar['legato'], legato_ms=ar['legato_ms'], seed=len(rh))
        return Clip._raw([n._replace(vel=min(n.vel, cap)) for n in rh], rh.length)


def score(rh=None, lh=None, dyn=None, *, meter='4/4', pickup=0, unit='1/8', key=None, phrases=None,
          accent: float = 1.1, ghost: float = 0.72, refs=None) -> Score:
    """A written piano score -> Score (play it with .perform(song, rh_track, lh_track)):
      rh       the right hand in notation (agentsound.notation, read with unit= and meter=): a string, or
               {bar: notation} (bar 0 = the pickup when pickup= is given; joined with bar lines). Ornaments as
               written and realized by perform(): ^tr / ^tr(upper) / ^tr(lower=-1) trills, ^turn (upper=1,
               lower=-1: chromatic), {..}:N^fig(even | arch | rit | accel | wave) fioriture, [..]^roll(60) rolled
               chords; ! / ? accents x accent= / ghost= (dynamics belong in dyn=); or a Clip of composed notes (an
               endless tune: notes struck together are a chord, no ornaments)
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
