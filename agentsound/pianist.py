"""A jazz pianist's hands: named, reusable piano MOVES and an arranger that turns a bare melody + changes into an
idiomatic two-handed piano part.

User feedback 2026-09-30 (perry-street-rain): "es ist, als würde ein Kind Taste für Taste drücken beim Lead - zu
simpel" and "es gibt doch da so schöne Moves, z. B. wo zwei Tasten sehr schnell abgewechselt werden". A pianist
never plays a head as a bare single-note line: the right hand harmonizes the melody (voicings under it), decorates
long notes (trills, tremolos, turns, crushed grace notes, slip notes, rolls, re-struck voicings) and fills the
gaps (runs, arpeggio sweeps, cascading 4ths, answers, stabs, alternating-hands fills, a glissando into the next
section). This module is both: every move is a function you can call on its own, and arrange() chooses them phrase
by phrase from the context (seeded, deterministic).

    from agentsound import pianist
    b.piano.play(pianist.trill('C5', 2.0, bpm=96, key=s.key), sec.beat(6))          # one move
    arr = pianist.arrange(melody, prog, bpm=96, key=s.key, style='straight', density=0.6, lh='rootless', seed=3)
    b.piano.play(arr.rh, sec); b.comp.play(arr.lh, sec)                              # both hands
    b.piano.automate('instrument.pedal', arr.pedal(prog, sec))                       # harmony pedal, dry runs

Every move returns a Clip starting at `at` (default 0, beats) and takes the tempo (`bpm`) because fast figures are
timed in real time: a real trill runs ~12-16 notes per second, a tremolo ~9-12 strokes, a glissando up to ~22.
Velocities are shaped (accents, swells, the top voice sung out) and fast figures carry a few ms of timing wobble
(seeded). Ornaments are light and legato: the principal note speaks, the figure 25-40 velocity under it.

User feedback on v3 (2026-09-30): "etwas zu viele von diesen schnellen Zwei-Tasten-Wechseln" - the FAST
alternations (trill, tremolo, shake, repeated notes, alternating hands) are spice, not a habit: arrange() budgets
them (~1 per 16 bars, structural moments only, never in neighbouring phrases), the SPICE ornaments share a larger
budget, and a Memory shared by a song's arrange() calls counts it song-wide:

    mem = pianist.Memory().save(solo.bar(31))                    # the climax gets the big figure
    arr = pianist.arrange(melody, prog, bpm=96, key=s.key, memory=mem, at=head.bar(0))

Moves (MOVES): trill, tremolo, mordent, inverted_mordent, turn, crush, blues_crush, slip_note, repeated,
roll, sweep, gliss, fourths, pentatonic_run, run, chromatic_run, octave_run, shake, alternating_hands. Voicings under
a melody note: voicing(ch, melody, device) with DEVICES (guide, thirds, sixths, close, drop2, quartal, ust, octave,
locked). Pedal: pedal(prog, at, dry=...) changes with the harmony and lifts for dry runs / trills.
"""

from __future__ import annotations

import math
import random

from . import tempo as _tempo
from .budget import Budget
from .patterns import Clip, Note, _as_prog, _vel, as_clip, seed_int
from .theory import (Chord, ComposeError, Key, Progression, available_tensions, block, chord_kind, chord_scale,
                     guide_tones, jazz_voicings, mud, note, shell, upper_structure)

__all__ = ['MOVES', 'DEVICES', 'STYLES', 'FILL_KINDS', 'ORNAMENTS', 'LH_STYLES', 'LH_METERS', 'FAST', 'SPICE',
           'Memory', 'trill', 'tremolo', 'mordent', 'inverted_mordent', 'turn', 'crush', 'blues_crush', 'slip_note',
           'repeated', 'roll', 'sweep', 'gliss', 'fourths', 'pentatonic_run', 'run', 'chromatic_run', 'octave_run',
           'shake', 'alternating_hands', 'voicing', 'left_hand', 'pedal', 'arrange', 'Arrangement', 'crushes']

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


def _pitches(x) -> list[int]:
    if isinstance(x, (list, tuple, set, frozenset)):
        ps = sorted(note(p) for p in x)
    else:
        ps = [note(x)]
    if not ps:
        raise ComposeError("a move needs at least one pitch")
    return ps


def _chord(ch) -> Chord | None:
    return None if ch is None else Chord.parse(ch)


def _key(key) -> Key | None:
    if key is None or isinstance(key, Key):
        return key
    return Key(key)


def _scale_pcs(ch=None, key=None) -> set[int]:
    """The notes a line may use over `ch`: its chord scale (+ the key's notes where they agree), else the key, else
    C major."""
    c, k = _chord(ch), _key(key)
    if c is not None:
        pcs = {(c.root + i) % 12 for i in chord_scale(c)}
        return pcs
    if k is not None:
        return set(k.pcs)
    return {0, 2, 4, 5, 7, 9, 11}


def _step(p: int, pcs, n: int) -> int:
    """`n` scale steps from pitch p (positive = up) inside pitch classes pcs."""
    pcs = set(pcs)
    if not pcs:
        raise ComposeError("empty scale")
    q, d = p, (1 if n > 0 else -1)
    for _ in range(abs(n)):
        q += d
        while q % 12 not in pcs:
            q += d
    return q


def _neighbour(p: int, up: bool, ch=None, key=None, chromatic_below: bool = False) -> int:
    """The upper / lower neighbour of p: a scale step (chord scale, else key), or a half step below."""
    if not up and chromatic_below:
        return p - 1
    q = _step(p, _scale_pcs(ch, key), 1 if up else -1)
    if abs(q - p) > 2:                       # a gap in the scale (pentatonic / whole-half): stay close
        q = p + (2 if up else -1)
    return q


def _pentatonic(ch=None, key=None) -> set[int]:
    """Pentatonic over a chord: major pentatonic on major / dominant / sus chords, minor pentatonic on minor ones,
    locrian-ish (1 b3 4 b5 b7) on m7b5; else the chord scale."""
    c = _chord(ch)
    if c is None:
        k = _key(key)
        if k is None:
            return {0, 2, 4, 7, 9}
        return {(k.tonic + i) % 12 for i in ((0, 3, 5, 7, 10) if k.minorish else (0, 2, 4, 7, 9))}
    kind = chord_kind(c)
    if kind in ('maj', 'maj7', '6', 'dom', 'sus', 'power', 'aug'):
        iv = (0, 2, 4, 7, 9)
        if kind == 'dom' and ({13, 15, 20, 8} & set(c.intervals)):      # altered: the chord scale instead
            return _scale_pcs(c)
    elif kind in ('min', 'm7', 'm6', 'mmaj7'):
        iv = (0, 3, 5, 7, 10)
    elif kind == 'm7b5':
        iv = (0, 3, 5, 6, 10)
    else:
        return _scale_pcs(c)
    return {(c.root + i) % 12 for i in iv}


def _wob(rng: random.Random, ms: float, bpm: float) -> float:
    return (rng.random() * 2.0 - 1.0) * _sec(ms / 1000.0, bpm)


def _clip(notes, at: float = 0.0) -> Clip:
    ns = [Note(float(s), float(max(0.02, d)), int(p), _vel(v)) for s, d, p, v in notes]
    end = max((n.start + n.dur for n in ns), default=at)
    return Clip._raw(ns, float(math.ceil(end - _EPS)) if end > 0 else 0.0)


def _pos(at) -> float:
    if hasattr(at, 'start') and not isinstance(at, (int, float)):
        return float(at.start)
    return _num(at, 'at (beats)', 0)


def _light(v0: float, light=None) -> float:
    """How far (velocity) an ornament's inner notes play under its principal note: `light`, or by default 25 (a soft
    principal) .. 40 (a loud one). User feedback 2026-09-30 (perry-street-rain): "es klingt hart" - a pianist plays
    trills, tremolos, turns and grace notes LIGHT: only the principal note speaks, the figure is a shimmer on it."""
    if light is not None:
        return _num(light, 'light (velocity under the principal)', 0, 100)
    return 25.0 + 15.0 * min(1.0, max(0.0, (v0 - 50.0) / 60.0))


def _soft(v0: float, light=None, x: float = 1.0) -> float:
    """The level of an ornament's inner note: `x` of the way down from the principal v0 (1 = the full `_light` drop),
    never below velocity 12."""
    return max(12.0, v0 - x * _light(v0, light))


def _figure(v0: float, light, y: float, swell='arch', extra: float = 0.0) -> float:
    """The velocity of an inner note of a light figure at y (0..1 through it): `light` under the principal v0
    (default 25-40), moved by the swell ('arch': swells in and fades, 'cresc', 'dim', None: level) between 1.1 and
    0.85 x that drop; extra = more drop (a fade, a lighter upper note)."""
    y = min(1.0, max(0.0, y))
    sw = {'arch': math.sin(math.pi * y), 'cresc': y, 'dim': 1.0 - y, None: 0.5}[swell]
    return max(12.0, v0 - _light(v0, light) * (1.1 - 0.25 * sw + extra))


def _vels(vel) -> tuple[float, float]:
    if isinstance(vel, (tuple, list)):
        if len(vel) != 2:
            raise ComposeError(f"vel must be a number or (from, to), got {vel!r}")
        return _num(vel[0], 'vel', 1, 127), _num(vel[1], 'vel', 1, 127)
    v = _num(vel, 'vel', 1, 127)
    return v, v


# ------------------------------------------------------------------------------------------------ moves: ornaments

def trill(pitch, dur, bpm, *, upper=None, chord=None, key=None, rate: float = 14.0, start_rate: float | None = None,
          turn: bool = True, hold=None, max_sec: float = 1.8, vel=80, fade: float = 0.94, light=None,
          legato: float = 1.25, wobble_ms: float = 4.5, seed=0, at=0.0) -> Clip:
    """Trill: the note and its upper neighbour (a scale step of the chord / key, or upper= semitones) alternated
    fast - starting a little slower (start_rate, default 0.65 x rate) and settling at `rate` notes per second (a
    real trill: 12-16). Played light: the first (principal) note at `vel`, the alternation `light` velocity under it
    (default 25-40, see _light), swelling in and fading to `fade`, the upper notes a little lighter, the notes
    overlapping (legato x the step), a few ms of timing wobble. It ends with a turn (turn=True: the lower neighbour,
    then the note - the Nachschlag) and the note held for the rest of `dur` (hold= beats; default ~40 % of dur, the
    trill itself at most max_sec seconds), re-struck softly (half the drop). Starts on the main note."""
    p = note(pitch)
    D = _num(dur, 'trill dur (beats)', 0.25)
    b = _bpm(bpm)
    a = _pos(at)
    r1 = _num(rate, 'trill rate (notes/s)', 4, 30)
    r0 = r1 * 0.65 if start_rate is None else _num(start_rate, 'trill start_rate', 2, 30)
    up = p + int(upper) if upper is not None else _neighbour(p, True, chord, key)
    lo = _neighbour(p, False, chord, key)
    v0, _ = _vels(vel)
    lg = _num(legato, 'trill legato', 0.5, 2.0)
    _light(v0, light)
    rng = random.Random(seed_int(seed))
    h = min(max(0.25 * D, 0.4 * D), D - 0.2) if hold is None else _num(hold, 'trill hold', 0, D)
    span = min(D - h, _sec(max_sec, b))
    s0, s1 = _sec(1.0 / r0, b), _sec(1.0 / r1, b)
    out = []
    t, i = 0.0, 0
    tail = 2 * s1 if turn else 0.0
    while True:
        x = min(1.0, t / max(span * 0.45, _EPS))
        step = s0 + (s1 - s0) * x
        if t + step > span - tail + _EPS and i >= 2 and i % 2 == 0:
            break
        if t + step > span + _EPS and i >= 2:
            break
        q = p if i % 2 == 0 else up
        y = t / max(span, _EPS)
        v = v0 if i == 0 else (_figure(v0, light, y, 'arch', (1.0 - fade) * y + (0.0 if i % 2 == 0 else 0.05))
                               * (1.0 + (rng.random() - 0.5) * 0.04))
        w = _wob(rng, wobble_ms, b) if i else 0.0
        out.append((a + max(0.0, t + w), step * lg, q, v))
        t += step
        i += 1
    if turn:
        # the trill stopped on the main note's slot: turn = (upper) lower, main
        if out and out[-1][2] == p and len(out) > 1:
            out[-1] = (out[-1][0], out[-1][1], up, _figure(v0, light, 1.0, 'arch', 1.0 - fade + 0.05))
        out.append((a + t + _wob(rng, wobble_ms, b), s1 * lg, lo, _figure(v0, light, 1.0, 'arch', 1.0 - fade)))
        t += s1
    out.append((a + t, max(0.1, D - t), p, _soft(v0, light, 0.5)))
    return _clip(out, a)


def tremolo(lower, upper, dur, bpm, *, rate: float = 11.0, swell: str | None = 'arch', land: bool = True,
            vel=82, inner: float = 0.86, light=None, legato: float = 1.15, wobble_ms: float = 4.5, seed=0,
            at=0.0) -> Clip:
    """Tremolo: fast alternation of two notes or note groups a wide interval apart - a 3rd, 6th, octave, or a chord
    against its bass note (the romantic / gospel swell): lower, upper = a pitch or a list of pitches, `rate` strokes
    per second (9-12). Played light: the first two strokes (the grip) at `vel`, the alternation `light` velocity
    under it (default 25-40) shaped by swell 'arch' (grow, then relax), 'cresc', 'dim' or None, the strokes
    overlapping a little (legato); land=True strikes both groups together for the last ~20 % and holds them, softly
    (half the drop). Starts with the lower group; the top note of the upper group sings."""
    lo, hi = _pitches(lower), _pitches(upper)
    if max(lo) >= min(hi):
        raise ComposeError(f"tremolo: the lower group {lo} must sit under the upper group {hi}")
    D = _num(dur, 'tremolo dur', 0.25)
    b = _bpm(bpm)
    a = _pos(at)
    if swell not in ('arch', 'cresc', 'dim', None):
        raise ComposeError(f"tremolo swell must be 'arch', 'cresc', 'dim' or None, got {swell!r}")
    step = _sec(1.0 / _num(rate, 'tremolo rate (strokes/s)', 3, 25), b)
    v0, _ = _vels(vel)
    _light(v0, light)
    lg = _num(legato, 'tremolo legato', 0.5, 2.0)
    rng = random.Random(seed_int(seed))
    body = D * (0.8 if land else 1.0)
    out = []
    n = max(2, int(body / step + _EPS))
    for i in range(n):
        t = i * step + (_wob(rng, wobble_ms, b) if i else 0.0)
        grp = lo if i % 2 == 0 else hi
        lv = v0 if i < 2 else _figure(v0, light, i / max(1, n - 1), swell)
        for j, q in enumerate(grp):
            top = q == max(hi) and i % 2 == 1
            d = step * lg if not land or i < n - 1 else max(0.02, n * step - max(0.0, t))
            out.append((a + max(0.0, t), d, q, lv * (1.0 if top else inner)))
    if land:
        t = n * step
        lv = _soft(v0, light, 0.5)
        for q in lo + hi:
            out.append((a + t, max(0.1, D - t), q, lv * (1.0 if q == max(hi) else inner)))
    return _clip(out, a)


def mordent(pitch, dur, bpm, *, upper: bool = False, chord=None, key=None, ms: float = 55.0, vel=80, light=None,
            at=0.0) -> Clip:
    """Mordent: the note, its lower neighbour (upper=True: the upper one - the inverted mordent / Pralltriller) and
    the note again, each `ms` long (45-70), then the note held for the rest of `dur`. The quick flick a pianist puts
    on a melody note: the principal at `vel`, the neighbour `light` under it (default 25-40), the return softer,
    legato."""
    p = note(pitch)
    D = _num(dur, 'mordent dur', 0.1)
    b = _bpm(bpm)
    a = _pos(at)
    s = _sec(_num(ms, 'mordent ms', 15, 200) / 1000.0, b)
    if D <= 2.5 * s:
        raise ComposeError(f"mordent: dur {D:g} beats is too short for two {ms:g} ms ornament notes")
    nb = _neighbour(p, upper, chord, key, chromatic_below=False)
    v0, _ = _vels(vel)
    return _clip([(a, s * 1.2, p, v0), (a + s, s * 1.2, nb, _soft(v0, light)),
                  (a + 2 * s, D - 2 * s, p, _soft(v0, light, 0.4))], a)


def inverted_mordent(pitch, dur, bpm, **kw) -> Clip:
    """The inverted mordent (Pralltriller): the note, its UPPER neighbour, the note - mordent(upper=True)."""
    return mordent(pitch, dur, bpm, upper=True, **kw)


def turn(pitch, dur, bpm, *, chord=None, key=None, inverted: bool = False, ms: float = 70.0, chromatic: bool = True,
         vel=80, light=None, at=0.0) -> Clip:
    """Turn (gruppetto) on the beat: upper neighbour, the note, lower neighbour (a half step below with
    chromatic=True, the jazz way), then the note held for the rest of `dur`; inverted=True starts from below.
    Each ornament note `ms` long (55-90), legato and light (the first one on the beat a little heavier, the others
    `light` under the principal, default 25-40); the held note lands at ~vel."""
    p = note(pitch)
    D = _num(dur, 'turn dur', 0.1)
    b = _bpm(bpm)
    a = _pos(at)
    s = _sec(_num(ms, 'turn ms', 20, 250) / 1000.0, b)
    if D <= 3.5 * s:
        raise ComposeError(f"turn: dur {D:g} beats is too short for three {ms:g} ms ornament notes")
    up = _neighbour(p, True, chord, key)
    lo = _neighbour(p, False, chord, key, chromatic_below=chromatic)
    v0, _ = _vels(vel)
    fig = [lo, p, up] if inverted else [up, p, lo]
    vs = (0.6, 1.0, 0.9)
    out = [(a + i * s, s * 1.2, q, _soft(v0, light, vs[i])) for i, q in enumerate(fig)]
    out.append((a + 3 * s, D - 3 * s, p, v0 * 0.95))
    return _clip(out, a)


def crush(pitch, dur, bpm, *, grace: int = -1, together: bool = False, ms: float = 35.0, under=(), vel=80,
          at=0.0) -> Clip:
    """Grace-note crush (acciaccatura): the note `grace` semitones away (default a half step below) crushed into the
    note - just before it (`ms`), or together=True struck WITH it and let go after `ms` (the piano's crushed
    note). under= pitches struck with the main note (a voicing), a little softer."""
    p = note(pitch)
    D = _num(dur, 'crush dur', 0.1)
    b = _bpm(bpm)
    a = _pos(at)
    s = _sec(_num(ms, 'crush ms', 10, 200) / 1000.0, b)
    g = p + int(grace)
    v0, _ = _vels(vel)
    if together:
        out = [(a, s * 1.2, g, _soft(v0, None, 0.7)), (a, D, p, v0)]
        t0 = a
    else:
        out = [(a, s * 1.25, g, _soft(v0)), (a + s, D - s, p, v0)]
        t0 = a + s
    out += [(t0, D - (t0 - a), q, v0 * 0.8) for q in _pitches(under) if q < p] if under else []
    return _clip(out, a)


def blues_crush(third, dur, bpm, *, ms: float = 45.0, under=(), vel=80, at=0.0) -> Clip:
    """Blues crush: the minor 3rd struck together with the major 3rd (`third`) and released after `ms` - the
    minor-into-major smear of blues and bar piano (Garner, Peterson, Monk). Put it on the 3rd of a major or dominant
    chord; under= a voicing struck with it."""
    return crush(third, dur, bpm, grace=-1, together=True, ms=ms, under=under, vel=vel, at=at)


def slip_note(pitches, dur, bpm, *, voice: int = -1, by: int = -2, ms: float = 85.0, vel=80, inner: float = 0.8,
              at=0.0) -> Clip:
    """Slip note (Floyd Cramer): a chord struck with one voice (`voice`, an index into the sorted pitches, default
    the top) a whole step low (`by` = -2, or -1) that slips up to its real note after `ms` - the country / bar piano
    'lick' on a melody note."""
    ps = _pitches(pitches)
    D = _num(dur, 'slip_note dur', 0.1)
    b = _bpm(bpm)
    a = _pos(at)
    s = _sec(_num(ms, 'slip_note ms', 20, 250) / 1000.0, b)
    if D <= 1.5 * s:
        raise ComposeError("slip_note: dur is too short for the slip")
    tgt = ps[voice]
    v0, _ = _vels(vel)
    top = max(ps)
    out = [(a, D, q, v0 * (1.0 if q == top else inner)) for q in ps if q != tgt]
    out += [(a, s * 1.2, tgt + int(by), _soft(v0, None, 0.7) if tgt == top else v0 * inner * 0.85),
            (a + s, D - s, tgt, v0 * (1.0 if tgt == top else inner))]
    return _clip(out, a)


def repeated(pitches, dur, bpm, *, rate: float = 9.0, accent=(1.0, 0.8), crescendo: float = 0.0, gate: float = 0.75,
             wobble_ms: float = 4.5, vel=80, light=None, seed=0, at=0.0) -> Clip:
    """Repeated notes: the same note (or dyad / chord) struck again and again at `rate` per second with the
    alternating-hands feel of a pianist (strokes alternate accent[0] / accent[1], the 'left-hand' strokes a few ms
    looser), crescendo = -1..1 (the level change over the figure). Light: the first stroke at `vel`, the repeats
    `light` under it (default 25-40). Fills `dur`."""
    ps = _pitches(pitches)
    D = _num(dur, 'repeated dur', 0.1)
    b = _bpm(bpm)
    a = _pos(at)
    step = _sec(1.0 / _num(rate, 'repeated rate (notes/s)', 2, 20), b)
    cr = _num(crescendo, 'repeated crescendo', -1, 1)
    g = _num(gate, 'repeated gate', 0.1, 1.0)
    v0, _ = _vels(vel)
    _light(v0, light)
    rng = random.Random(seed_int(seed))
    n = max(2, int(D / step + _EPS))
    out = []
    for i in range(n):
        x = i / max(1, n - 1)
        acc = accent[i % 2]
        t = i * step + (_wob(rng, wobble_ms, b) if i % 2 else 0.0)
        lv = v0 if i == 0 else _figure(v0, light, 0.5 + cr * (x - 0.5), None if cr == 0 else 'cresc') * acc
        for q in ps:
            out.append((a + max(0.0, t), step * g, q, lv * (1.0 if q == max(ps) else 0.85)))
    return _clip(out, a)


def roll(pitches, dur, bpm, *, ms: float = 25.0, direction: str = 'up', vel=80, inner: float = 0.84,
         at=0.0) -> Clip:
    """Rolled chord: the notes arpeggiated from the bottom (direction 'up') or the top ('down') over `ms` in total
    (8-25 for comping, 40-80 for a big ballad / ending chord), all released together; the top voice at `vel`, the
    others x inner."""
    ps = _pitches(pitches)
    D = _num(dur, 'roll dur', 0.05)
    b = _bpm(bpm)
    a = _pos(at)
    if direction not in ('up', 'down'):
        raise ComposeError(f"roll direction must be 'up' or 'down', got {direction!r}")
    total = _sec(_num(ms, 'roll ms', 0, 1000) / 1000.0, b)
    order = ps if direction == 'up' else ps[::-1]
    step = total / max(1, len(ps) - 1)
    v0, _ = _vels(vel)
    out = []
    for i, q in enumerate(order):
        off = min(i * step, 0.75 * D)
        out.append((a + off, D - off, q, v0 * (1.0 if q == ps[-1] else inner)))
    return _clip(out, a)


# ------------------------------------------------------------------------------------------------ moves: runs, sweeps

def _even_line(pitches, D, b, vel, *, accel: float = 1.0, gate: float = 1.1, wobble_ms: float = 3.0, rng=None,
               a: float = 0.0, max_rate: float = 18.0, ring: bool = False, dip: float = 0.14):
    """Notes `pitches` spread over D beats (accel < 1: the line speeds up); thinned (keeping first and last) when
    faster than max_rate notes/s. ring=True holds every note to the end. One gesture: the velocity moves from
    vel[0] to vel[1] and sinks by `dip` in the middle (a run is shaped, not a row of equal strokes), the notes
    slightly overlapping (gate)."""
    ps = list(pitches)
    sec = D * 60.0 / b
    while len(ps) > 2 and len(ps) / max(sec, _EPS) > max_rate:
        ps = ps[:1] + ps[1:-1][1::2] + ps[-1:] if len(ps) > 3 else [ps[0], ps[-1]]
    n = len(ps)
    v0, v1 = vel
    rng = rng or random.Random(0)
    out = []
    times = [D * (i / n) ** accel for i in range(n)]
    for i, q in enumerate(ps):
        t = times[i] + (_wob(rng, wobble_ms, b) if 0 < i < n - 1 else 0.0)
        nxt = times[i + 1] if i + 1 < n else D
        d = (D - times[i]) if ring else max(0.03, (nxt - times[i]) * gate)
        x = i / max(1, n - 1)
        out.append((a + max(0.0, t), d, q, (v0 + (v1 - v0) * x) * (1.0 - dip * math.sin(math.pi * x))))
    return out


def sweep(chord, dur, bpm, *, low='C3', high='C6', direction: str = 'up', tensions: bool = True,
          max_rate: float = 16.0, ring: bool = True, vel=(56, 92), wobble_ms: float = 2.0, seed=0,
          at=0.0) -> Clip:
    """Arpeggio sweep across the keyboard: the chord's tones (+ its 9th with tensions=True) from `low` to `high`
    ('up'), back ('down') or up and down ('updown'), evenly over `dur` (thinned to max_rate notes/s), each note
    ringing to the end (ring=True: the pedalled harp sweep). Velocity from vel[0] to vel[1]."""
    c = Chord.parse(chord)
    D = _num(dur, 'sweep dur', 0.25)
    b = _bpm(bpm)
    a = _pos(at)
    lo, hi = note(low), note(high)
    if hi - lo < 7:
        raise ComposeError("sweep: low..high must span at least a 5th")
    if direction not in ('up', 'down', 'updown'):
        raise ComposeError(f"sweep direction must be 'up', 'down' or 'updown', got {direction!r}")
    pcs = {(c.root + i) % 12 for i in c.intervals if i < 12}
    g3, g7 = guide_tones(c)
    pcs |= {g3} | ({g7} if g7 is not None else set())
    if tensions:
        t9 = [t for t in available_tensions(c) if t in (1, 2, 3)]
        if t9:
            pcs.add((c.root + t9[0]) % 12)
    ps = [q for q in range(lo, hi + 1) if q % 12 in pcs]
    # no minor 2nds in a sweep: drop the 9th where it rubs a chord tone
    clean = []
    for q in ps:
        if clean and q - clean[-1] == 1:
            continue
        clean.append(q)
    if direction == 'down':
        clean = clean[::-1]
    elif direction == 'updown':
        clean = clean + clean[-2::-1]
    rng = random.Random(seed_int(seed))
    v = _vels(vel)
    return _clip(_even_line(clean, D, b, v, accel=0.95, ring=ring and direction == 'up', rng=rng, a=a,
                            max_rate=_num(max_rate, 'sweep max_rate', 2, 30), wobble_ms=wobble_ms), a)


def gliss(target, length, bpm, *, direction: str = 'up', span: int = 14, chord=None, key=None, scale=None,
          max_rate: float = 22.0, land: bool = False, hold: float = 1.0, vel=(48, 92), seed=0, at=0.0) -> Clip:
    """Glissando-like fast scale sweep INTO a downbeat: a run of the scale (the chord scale, the key, scale= pitch
    classes, or 'white' keys) from `span` semitones away up (or down) to just before `target`, ending exactly at
    at + length (accelerating, crescendo, up to max_rate notes/s: the start is shortened, not the arrival).
    land=True also strikes the target at at + length and holds it `hold` beats; leave it False when the next
    section's melody plays the target."""
    t = note(target)
    L = _num(length, 'gliss length', 0.25)
    b = _bpm(bpm)
    a = _pos(at)
    if direction not in ('up', 'down'):
        raise ComposeError(f"gliss direction must be 'up' or 'down', got {direction!r}")
    if scale == 'white':
        pcs = {0, 2, 4, 5, 7, 9, 11}
    elif scale is not None:
        pcs = {int(x) % 12 for x in scale}
    else:
        pcs = _scale_pcs(chord, key)
    d = 1 if direction == 'up' else -1
    q = _step(t, pcs, -d)
    ps = []
    while abs(q - t) <= abs(int(span)):
        ps.append(q)
        q = _step(q, pcs, -d)
    ps = ps[::-1]                                  # far -> near the target
    n_max = max(2, int(L * 60.0 / b * _num(max_rate, 'gliss max_rate', 4, 40)))
    ps = ps[-n_max:]
    rng = random.Random(seed_int(seed))
    out = _even_line(ps, L, b, _vels(vel), accel=0.8, gate=1.0, rng=rng, a=a, max_rate=100.0)
    if land:
        out.append((a + L, _num(hold, 'gliss hold', 0.05), t, _vels(vel)[1]))
    return _clip(out, a)


def run(start, end, dur, bpm, *, chord=None, key=None, scale=None, vel=(66, 86), max_rate: float = 16.0,
        wobble_ms: float = 2.0, seed=0, at=0.0) -> Clip:
    """Scale run from `start` to `end` (both included; pitches snapped into the scale) over `dur`, evenly (the last
    note ends at at + dur); scale = the chord scale of `chord`, the key, or scale= pitch classes. Faster than
    max_rate notes/s it skips scale steps (a broken run)."""
    s, e = note(start), note(end)
    D = _num(dur, 'run dur', 0.1)
    b = _bpm(bpm)
    a = _pos(at)
    pcs = {int(x) % 12 for x in scale} if scale is not None else _scale_pcs(chord, key)
    d = 1 if e >= s else -1
    ps = [s if s % 12 in pcs else _step(s, pcs, d)]
    while (ps[-1] - e) * d < 0:
        ps.append(_step(ps[-1], pcs, d))
    if ps[-1] != e and e % 12 in pcs:
        ps[-1] = e
    rng = random.Random(seed_int(seed))
    return _clip(_even_line(ps, D, b, _vels(vel), rng=rng, a=a, max_rate=_num(max_rate, 'run max_rate', 2, 30),
                            wobble_ms=wobble_ms), a)


def chromatic_run(start, end, dur, bpm, **kw) -> Clip:
    """Chromatic run (the bar pianist's run-down): every half step from `start` to `end` over `dur`."""
    return run(start, end, dur, bpm, scale=range(12), **kw)


def pentatonic_run(start, dur, bpm, *, notes: int = 6, direction: str = 'down', chord=None, key=None, vel=(84, 64),
                   seed=0, at=0.0) -> Clip:
    """Pentatonic run: `notes` notes of the chord's pentatonic (major pentatonic on major / dominant chords, minor
    pentatonic on minor ones) from `start` down (or up), evenly over `dur`."""
    pcs = _pentatonic(chord, key)
    s = note(start)
    d = -1 if direction == 'down' else 1
    q = s if s % 12 in pcs else _step(s, pcs, d)
    end = q
    for _ in range(int(notes) - 1):
        end = _step(end, pcs, d)
    return run(q, end, dur, bpm, scale=pcs, vel=vel, seed=seed, at=at)


def octave_run(start, end, dur, bpm, *, below: bool = True, vel=(74, 96), inner: float = 0.84, **kw) -> Clip:
    """A run in octaves (the climax run): run(start, end, ...) with every note doubled an octave below (above with
    below=False), the doubling x inner."""
    c = run(start, end, dur, bpm, vel=vel, **kw)
    sh = -12 if below else 12
    return Clip._raw(list(c) + [n._replace(pitch=n.pitch + sh, vel=_vel(n.vel * inner)) for n in c], c.length)


def fourths(top, dur, bpm, *, chord=None, key=None, voices: int = 2, grid: float = 0.25, direction: str = 'down',
            vel=(90, 64), wobble_ms: float = 2.5, seed=0, at=0.0) -> Clip:
    """Cascading 4ths (McCoy Tyner): stacks of `voices` notes a 4th apart (a perfect or augmented 4th of the
    pentatonic) walking down (or up) the chord's pentatonic from `top`, one stack per `grid` beats (0.25 = 16ths,
    1/3 = triplets) for `dur`."""
    pcs = _pentatonic(chord, key)
    D = _num(dur, 'fourths dur', 0.25)
    b = _bpm(bpm)
    a = _pos(at)
    g = _num(grid, 'fourths grid', 0.05, 2)
    nv = int(_num(voices, 'fourths voices', 1, 4))
    d = -1 if direction == 'down' else 1
    q = note(top)
    q = q if q % 12 in pcs else _step(q, pcs, -1)
    n = max(1, int(D / g + _EPS))
    v0, v1 = _vels(vel)
    rng = random.Random(seed_int(seed))
    out = []
    for i in range(n):
        stack = [q]
        for _ in range(nv - 1):
            nxt = stack[-1] - 5
            if nxt % 12 not in pcs and (stack[-1] - 6) % 12 in pcs:
                nxt = stack[-1] - 6
            stack.append(nxt)
        x = i / max(1, n - 1)
        t = i * g + (_wob(rng, wobble_ms, b) if i else 0.0)
        for j, s in enumerate(stack):
            out.append((a + max(0.0, t), g * 1.08, s, (v0 + (v1 - v0) * x) * (1.0 - 0.12 * math.sin(math.pi * x))
                        * (1.0 if j == 0 else 0.84)))
        q = _step(q, pcs, d)
    return _clip(out, a)


def shake(pitches, dur, bpm, *, interval: int = 3, rate: float = 12.0, vel=90, inner: float = 0.8, light=None,
          legato: float = 1.15, wobble_ms: float = 4.5, seed=0, at=0.0) -> Clip:
    """Block-chord ending shake (the big-band shake on piano): the chord struck and held while its top note
    alternates fast with the note `interval` semitones above it (3 = a minor 3rd, the brass shake), `rate` strokes
    per second, landing back on the top note. The chord and its first top note at `vel`, the shake `light` under it
    (default 25-40) swelling and fading, legato; the landing note softly (half the drop)."""
    ps = _pitches(pitches)
    D = _num(dur, 'shake dur', 0.25)
    b = _bpm(bpm)
    a = _pos(at)
    top = ps[-1]
    step = _sec(1.0 / _num(rate, 'shake rate', 3, 25), b)
    v0, _ = _vels(vel)
    rng = random.Random(seed_int(seed))
    out = [(a, D, q, v0 * inner) for q in ps[:-1]]
    n = max(3, int(D * 0.8 / step))
    if n % 2 == 0:
        n += 1
    _light(v0, light)
    lg = _num(legato, 'shake legato', 0.5, 2.0)
    for i in range(n):
        t = i * step + (_wob(rng, wobble_ms, b) if i else 0.0)
        q = top if i % 2 == 0 else top + int(interval)
        d = step * lg if i < n - 1 else max(0.1, D - i * step)
        if i == 0:
            v = v0
        elif i == n - 1:
            v = _soft(v0, light, 0.5)
        else:
            v = _figure(v0, light, i / max(1, n - 1), 'arch', 0.0 if i % 2 == 0 else 0.05)
        out.append((a + max(0.0, t), d, q, v))
    return _clip(out, a)


def alternating_hands(chord, dur, bpm, *, top='C6', lh_register=('C3', 'C4'), grid: float = 0.25,
                      pattern: str = 'RL', vel=(88, 70), inner: float = 0.86, wobble_ms: float = 3.0, seed=0,
                      at=0.0) -> Clip:
    """Alternating-hands fill (the hands trade 16ths): the right hand plays dyads of chord tones walking down from
    `top`, the left hand a shell (3rd + 7th) in `lh_register`, in `pattern` ('RL', 'RRL', 'RLL', 'RRLL' ...) per
    `grid` beats for `dur` - the Oscar Peterson / Phineas Newborn two-handed break."""
    c = Chord.parse(chord)
    D = _num(dur, 'alternating_hands dur', 0.25)
    b = _bpm(bpm)
    a = _pos(at)
    g = _num(grid, 'alternating_hands grid', 0.05, 1)
    if not pattern or set(pattern) - {'R', 'L'}:
        raise ComposeError(f"alternating_hands pattern must be made of 'R' and 'L', got {pattern!r}")
    g3, g7 = guide_tones(c)
    tones = sorted({(c.root + i) % 12 for i in c.intervals if i < 12} | {g3} | ({g7} if g7 is not None else set()))
    lo, hi = note(lh_register[0]), note(lh_register[1])
    lh = shell(c, '37', register=(lo, hi)) if g7 is not None else [q for q in range(lo, hi + 1) if q % 12 in tones][:2]
    rh_line = [q for q in range(note(top) - 24, note(top) + 1) if q % 12 in tones][::-1]
    v0, v1 = _vels(vel)
    rng = random.Random(seed_int(seed))
    n = max(2, int(D / g + _EPS))
    out, ri = [], 0
    for i in range(n):
        x = i / max(1, n - 1)
        v = v0 + (v1 - v0) * x
        t = i * g + (_wob(rng, wobble_ms, b) if i else 0.0)
        if pattern[i % len(pattern)] == 'R':
            q = rh_line[min(ri, len(rh_line) - 1)]
            second = next((x for x in rh_line[ri + 1:] if 3 <= q - x <= 9), None)
            pair = [q] + ([second] if second is not None else [])
            for j, p_ in enumerate(pair):
                out.append((a + max(0.0, t), g * 0.95, p_, v * (1.0 if j == 0 else inner)))
            ri += 1
        else:
            for p_ in lh:
                out.append((a + max(0.0, t), g * 0.95, p_, v * inner * 0.92))
    return _clip(out, a)


def crushes(line, prob: float = 0.3, seed=0, *, min_dur: float = 0.9, grace: int = -1, ahead: float = 0.07,
            length: float = 0.09, vel: float = 0.7) -> Clip:
    """Acciaccaturas across a whole line (a played solo line, not one note): before each note of at least `min_dur`
    beats (and not at the very start) with chance `prob`, the note `grace` semitones away (a half step below)
    crushed in `ahead` beats early, `length` long, at `vel` x its velocity. Seeded; the line's own notes stay."""
    c = as_clip(line)
    rng = random.Random(seed_int(seed))
    out = list(c)
    for n in c:
        if n.dur >= min_dur and n.start >= 0.2 and rng.random() < prob:
            out.append(Note(n.start - ahead, length, n.pitch + grace, max(1, int(n.vel * vel))))
    return Clip(out, length=c.length)


MOVES = {
    'trill': trill, 'tremolo': tremolo, 'mordent': mordent, 'inverted_mordent': inverted_mordent, 'turn': turn,
    'crush': crush, 'blues_crush': blues_crush, 'slip_note': slip_note, 'repeated': repeated, 'roll': roll,
    'sweep': sweep, 'gliss': gliss, 'run': run, 'chromatic_run': chromatic_run, 'pentatonic_run': pentatonic_run,
    'octave_run': octave_run, 'fourths': fourths, 'shake': shake, 'alternating_hands': alternating_hands,
}
"""Every piano move by name -> its function (each returns a Clip starting at `at`; call it on its own or let
arrange() choose)."""


# ------------------------------------------------------------------------------------------------ voicings

DEVICES = ('single', 'guide', 'thirds', 'sixths', 'close', 'drop2', 'quartal', 'ust', 'octave', 'locked')
"""How the right hand harmonizes a melody note (voicing(ch, melody, device)): single (the bare note), guide (the
3rd / 7th under it), thirds / sixths (a diatonic 3rd or 6th under a moving line), close (4-way close), drop2,
quartal (4ths under the melody), ust (an upper-structure triad on a dominant), octave (melody in octaves + an inner
chord tone), locked (locked hands: 4-way close + the melody an octave below)."""


def _tones(ch: Chord) -> set[int]:
    g3, g7 = guide_tones(ch)
    return {(ch.root + i) % 12 for i in ch.intervals} | {g3} | ({g7} if g7 is not None else set())


def _colour(ch: Chord) -> set[int]:
    return _tones(ch) | {(ch.root + t) % 12 for t in available_tensions(ch)}


def _below(pc: int, mel: int, floor: int) -> int | None:
    """The highest pitch of class pc strictly under mel and >= floor."""
    q = mel - ((mel - pc) % 12 or 12)
    return q if q >= floor else None


def _clean(under, mel: int, floor: int, maxv: int, keep_octave: bool = False) -> list[int]:
    """Voices under the melody: unique, under it, >= floor (lifted an octave if that still fits), no minor 2nd /
    minor 9th against the melody or between neighbours, no low-interval mud, at most maxv (the highest kept)."""
    ps: set[int] = set()
    for q in under:
        q = int(q)
        while q < floor and q + 12 < mel:
            q += 12
        if floor <= q < mel and (q != mel - 12 or keep_octave):
            ps.add(q)
    out = sorted(ps)
    out = [q for q in out if mel - q not in (1, 13)]
    changed = True
    while changed:
        changed = False
        for i in range(len(out) - 1):
            if out[i + 1] - out[i] == 1:
                del out[i]                     # the lower of a minor-2nd pair goes
                changed = True
                break
    while len(out) > 1 and mud(out + [mel]):
        out.pop(0)
    if len(out) > maxv:
        out = out[len(out) - maxv:]
    return out


def voicing(ch, melody, device: str = 'drop2', *, floor='G3', voices: int = 3, key=None) -> list[int]:
    """A right-hand voicing with `melody` on top: the pitches (ascending, melody last) for DEVICES. The voices under
    the melody stay >= floor, clear of minor 2nds / 9ths against the melody and of low-interval mud, at most
    `voices` under the melody. A device that doesn't fit (ust on a non-dominant, a non-chord melody note) falls
    back to guide tones or the bare note."""
    c = Chord.parse(ch)
    m = note(melody)
    fl = note(floor)
    if device not in DEVICES:
        raise ComposeError(f"voicing device must be one of {', '.join(DEVICES)}, got {device!r}")
    nv = int(_num(voices, 'voicing voices', 0, 5))
    pcs = _scale_pcs(c, key)
    under: list[int] = []
    keep_oct = False
    g3, g7 = guide_tones(c)
    if device == 'single' or nv == 0:
        return [m]
    if device == 'guide':
        for pc in (g3, g7):
            if pc is not None and pc != m % 12:
                q = _below(pc, m, fl)
                if q is not None:
                    under.append(q)
    elif device == 'thirds':
        under = [_step(m, pcs, -2)]
    elif device == 'sixths':
        under = [_step(m, pcs, -5)]
    elif device in ('close', 'drop2', 'locked'):
        under = [q for q in block(c, m, device) if q != m]
        keep_oct = device == 'locked'
        if device == 'drop2' and min(under, default=m) < fl:
            under = [q for q in block(c, m, 'close') if q != m]
    elif device == 'quartal':
        q = m
        for _ in range(max(1, nv)):
            nxt = q - 5 if (q - 5) % 12 in pcs else q - 6 if (q - 6) % 12 in pcs else q - 4
            under.append(nxt)
            q = nxt
    elif device == 'ust':
        if chord_kind(c) == 'dom':
            try:
                us = upper_structure(c, top=m, register=(fl - 12, m + 1))
            except ComposeError:
                us = []
            tri = us[2:] if len(us) >= 5 else []
            if tri and tri[-1] == m:
                under = tri[:-1] + [q for q in us[:2]]
        if not under:
            under = [q for q in block(c, m, 'drop2') if q != m]
    elif device == 'octave':
        under = [m - 12]
        keep_oct = True
        col = _tones(c)
        inner = [q for q in range(m - 9, m - 4) if q % 12 in col and q % 12 != m % 12]
        if inner:
            under.append(max(inner, key=lambda q: (q % 12 in (g3, g7), q)))
    maxv = nv + (1 if device in ('locked', 'octave') else 0)
    return _clean(under, m, fl, maxv, keep_octave=keep_oct) + [m]


# ------------------------------------------------------------------------------------------------ left hand

LH_STYLES = ('guide', 'shell', 'rootless', 'tenths', 'stride', 'pedal')
"""Left-hand styles for left_hand() / arrange(lh=...): guide (3rd + 7th, the rootless shell: with a bassist),
shell (1-7 / 1-3 Bud Powell shells, root in the bass: solo piano or a thin bass), rootless (Bill Evans A/B
voicings), tenths (root + 10th, rolled), stride (a stride hint: bass note on 1 and 3, a chord on 2 and 4 - in
the meter's own pulse: 'oom-pah-pah' in 3/4, see LH_METERS), pedal (a pedal point held under guide-tone shells)."""

LH_METERS = {
    (4, 4): {'answer': (2.0, 1.5, 2.5), 'weights': None, 'lift': False, 'light': 0.82,
             'stride': ((0, 'bass'), (1, 'chord'), (2, 'fifth'), (3, 'chord'))},
    (2, 2): {'answer': (2.0, 1.5, 2.5), 'weights': None, 'lift': False, 'light': 0.82,
             'stride': ((0, 'bass'), (1, 'chord'), (2, 'fifth'), (3, 'chord'))},
    (2, 4): {'answer': (1.0, 1.5), 'weights': None, 'lift': True, 'light': 0.74,
             'stride': ((0, 'bass'), (1, 'chord'), (2, 'fifth'), (3, 'chord'))},
    (3, 4): {'answer': (1.0, 1.5, 2.0), 'weights': (0.53, 0.35, 0.12), 'lift': True, 'light': 0.74,
             'stride': ((0, 'bass'), (1, 'chord'), (2, 'chord'), (3, 'fifth'), (4, 'chord'), (5, 'chord'))},
    (6, 8): {'answer': (1.5, 2.0, 2.5), 'weights': None, 'lift': True, 'light': 0.74,
             'stride': ((0, 'bass'), (1.5, 'chord'), (3, 'fifth'), (4.5, 'chord'))},
    (9, 8): {'answer': (1.5, 3.0), 'weights': None, 'lift': True, 'light': 0.74,
             'stride': ((0, 'bass'), (1.5, 'chord'), (3, 'chord'), (4.5, 'fifth'), (6, 'chord'), (7.5, 'chord'))},
    (12, 8): {'answer': (3.0, 1.5, 4.5), 'weights': None, 'lift': True, 'light': 0.74,
              'stride': ((0, 'bass'), (1.5, 'chord'), (3, 'fifth'), (4.5, 'chord'))},
    (5, 4): {'answer': (3.0, 3.5, 2.0), 'weights': None, 'lift': True, 'light': 0.74,
             'stride': ((0, 'bass'), (1, 'chord'), (2, 'chord'), (3, 'fifth'), (4, 'chord'))},
    (7, 8): {'answer': (2.0, 1.0), 'weights': None, 'lift': True, 'light': 0.74,
             'stride': ((0, 'bass'), (1, 'chord'), (2, 'chord'), (3.5, 'fifth'), (4.5, 'chord'), (5.5, 'chord'))},
    (7, 4): {'answer': (4.0, 2.0, 5.0), 'weights': None, 'lift': True, 'light': 0.74,
             'stride': ((0, 'bass'), (1, 'chord'), (2, 'fifth'), (3, 'chord'), (4, 'bass'), (5, 'chord'),
                        (6, 'chord'))},
}
"""How the left hand fills a bar per meter (offsets in quarter beats from the chord's start). answer: where the
answering re-strike of a chord lasting a bar or more may go, the first place where the right hand leaves room;
weights: instead one place is drawn (3/4: on 2, the & of 2 or 3) and the hand stays out when the right hand is
there; lift: the held voicing is cut just before the answer (a real hand lifts; 4/4 keeps the held chord under it,
as it always did); light: the answer's level against the strike (the 'pah' is light); stride: the stride pattern
(bass note, its fifth, chords on the other pulses; over one bar or two, repeated over a long chord) - 3/4
'oom-pah-pah', 6/8 'oom-pah' on the dotted quarters, 5/4 3+2, 7/8 2+2+3. Other meters get a generic one: the
answer near the middle of the bar, bass on 1, chords on the other beats."""

_METER_OF_BPB = {4.0: (4, 4), 3.0: (3, 4), 2.0: (2, 4), 5.0: (5, 4), 6.0: (12, 8), 3.5: (7, 8), 7.0: (7, 4),
                 4.5: (9, 8)}


def _lh_meter(meter, bpb: float) -> tuple[float, dict]:
    """(bar length in beats, its LH_METERS entry) for a meter (None: from the progression's beats per bar)."""
    if meter is None:
        m = _METER_OF_BPB.get(round(float(bpb), 3)) or (max(1, min(64, int(round(bpb * 2)))), 8)
    else:
        m = _tempo.parse_meter(meter, 'left_hand meter')
        if abs(_tempo.beats_per_bar(m) - bpb) > 1e-6:
            raise ComposeError(f"left_hand meter {m[0]}/{m[1]} has {_tempo.beats_per_bar(m):g} beats per bar but the "
                               f"progression {bpb:g}; make it with song.prog(..., meter='{m[0]}/{m[1]}')")
    bar = _tempo.beats_per_bar(m)
    if m in LH_METERS:
        return bar, LH_METERS[m]
    h = round(bar) / 2.0 if bar >= 2 else bar / 2.0      # generic: the answer near the middle of the bar
    ans = tuple(x for x in (h, h - 0.5, h + 0.5) if 0 < x < bar) or (bar / 2.0,)
    beats = [float(k) for k in range(1, int(math.ceil(bar - _EPS)))]
    return bar, {'answer': ans, 'weights': None, 'lift': True, 'light': 0.74,
                 'stride': ((0, 'bass'),) + tuple((k, 'chord') for k in beats) + ((bar, 'fifth'),)
                 + tuple((bar + k, 'chord') for k in beats)}


def left_hand(prog, bpm, *, style: str = 'guide', register=('C3', 'C4'), density: float = 0.5, vel: float = 58,
              roll=(12, 28), anticipate=(), rh=None, pedal_note=None, seed=0, length=None, touch: float = 1.0,
              meter=None, answers: float | None = None) -> Clip:
    """The pianist's left hand over `prog` (LH_STYLES): struck on every chord change (an 8th early where `anticipate`
    lists the change - the right hand's anticipations - or, seeded, a push), held into the next chord, rolled up
    (`roll` ms range, seeded per chord); on a chord of a bar or more the left hand answers the right hand: with
    probability `answers` (default density x 0.8) it re-strikes once, softer and shorter, where `rh` (a Clip) has no
    onset - in the meter's own place (LH_METERS): 4/4 on 3 or the & of 2; 3/4 on 2, the & of 2 or 3 (seeded; the
    held voicing lifts before it: a light 'oom-pah-pah'); 6/8 on the second dotted quarter; 5/4 on 4 (3+2); 12/8,
    7/8, 7/4, 9/8, 2/4 likewise. meter: '6/8', (5, 4), ... (default: from the progression's beats per bar - 3 beats
    read as 3/4, so pass meter='6/8' for compound time; 6 beats read as 12/8). register: where the voicing
    sits (the root of shell / tenths / stride goes below it, E1..D#3). vel: the level (seeded +-5). touch 0..1: the
    two hands breathe together - each strike follows the right hand's level around it (`rh`: the loudest right-hand
    note within a beat, relative to its median, ^0.9, x0.65..1.4; without `rh` a 4-bar arc
    x0.88..1.12), anticipations lean in (x1.1), +-5 % per strike, normalized in energy (vel keeps the loudness); 0 = one
    level (the dynamics ear reads it flat)."""
    p = _as_prog(prog, None, 4.0 if length is None else length)
    b = _bpm(bpm)
    touch = _num(touch, 'left_hand touch', 0, 1)
    if style not in LH_STYLES:
        raise ComposeError(f"left_hand style must be one of {', '.join(LH_STYLES)}, got {style!r}")
    dens = _num(density, 'left_hand density', 0, 1)
    lo, hi = note(register[0]), note(register[1])
    rng = random.Random(seed_int(seed))
    items = [(st, d, c) for st, d, c in p if c is not None]
    if not items:
        return Clip._raw((), p.length)
    rh_on = sorted({round(n.start, 3) for n in as_clip(rh)}) if rh is not None else []
    antic = {round(float(x), 3) for x in anticipate}
    rh_ns = sorted((n.start, n.vel) for n in as_clip(rh)) if rh is not None else []
    trng = random.Random(seed_int(seed) + 313)      # the touch's own dice: the notes are the same with any touch
    bpb = p.beats_per_bar
    bar, mtr = _lh_meter(meter, bpb)
    p_answer = dens * 0.8 if answers is None else _num(answers, 'left_hand answers', 0, 1)

    def rh_level(t):
        near = [v for s_, v in rh_ns if t - 1.0 <= s_ <= t + 1.0]
        return max(near) if near else None
    # the reference: the median of that local level over the right hand's own onsets (so the factors centre on 1)
    refs = sorted(x for x in (rh_level(s_) for s_ in sorted({s_ for s_, _ in rh_ns})) if x is not None)
    rh_ref = refs[len(refs) // 2] if refs else 0

    def feel(t, pushed=False):
        """The touch factor of a strike at t: the right hand's level around it (or a 4-bar arc), a push."""
        if touch <= 0:
            return 1.0
        near = rh_level(t)
        if rh_ref > 0 and near is not None:
            f = min(1.4, max(0.65, (near / rh_ref) ** 0.9))
        else:
            x = (t % (4 * bpb)) / (4 * bpb)
            f = 0.88 + 0.24 * (0.5 - 0.5 * math.cos(2.0 * math.pi * x))
        f *= (1.1 if pushed else 1.0) * (1.0 + 0.05 * (2.0 * trng.random() - 1.0))
        f = 1.0 + touch * (f - 1.0)
        applied.append(f)
        return f
    applied: list[float] = []

    def rh_hits(t, w=0.2):
        return any(abs(x - t) < w for x in rh_on)
    chords = [c for _, _, c in items]
    if style == 'rootless':
        vs = jazz_voicings(chords, 'rootless', register=(lo, max(hi, lo + 14)), voices=4)
    elif style in ('guide', 'pedal'):
        vs = jazz_voicings(chords, 'shell', register=(lo, max(hi, lo + 12)))
    else:
        vs = []
        prev = None
        for c in chords:
            root = _below(c.bass_pc, 52, 40) or 40 + (c.bass_pc - 40) % 12
            g3, g7 = guide_tones(c)
            if style == 'shell':
                opts = [[root, root + ((g7 - root) % 12)], [root, root + ((g3 - root) % 12) + 12]] if g7 is not None \
                    else [[root, root + ((g3 - root) % 12) + 12]]
                v = min(opts, key=lambda o: abs(o[-1] - (prev[-1] if prev else o[-1])) + rng.random() * 0.5)
            elif style == 'tenths':
                v = [root, root + ((g3 - root) % 12) + 12]
            else:                                  # stride: bass note + a chord (guide tones + colour) above
                v = [root] + jazz_voicings([c], 'rootless', register=(52, 67), voices=3)[0]
            vs.append(v)
            prev = v
    ped = note(pedal_note) if pedal_note is not None else None
    out = []
    L = p.length
    for (st, d, c), v in zip(items, vs):
        t = st
        if round(st, 3) in antic or (st >= 0.5 and rng.random() < 0.12 * dens and not rh_hits(st - 0.5, 0.1)):
            t = st - 0.5
        end = st + d - 0.05
        lv0 = vel * (1.0 + (rng.random() - 0.5) * 0.16)
        lv = lv0 * feel(t, t < st - _EPS)
        ms = rng.uniform(*roll)
        if style == 'stride':
            bass, ch_ = v[0], v[1:]
            pat = mtr['stride']
            span = 2 * bar if pat[-1][0] >= bar - _EPS else bar      # the pattern covers one bar or two
            offs = [o for o, _ in pat] + [span]
            k = 0
            while True:
                o, kind = pat[k % len(pat)]
                beat = (k // len(pat)) * span + o
                if st + beat >= st + d - _EPS:
                    break
                gap = offs[k % len(pat) + 1] - o                      # to the pattern's next pulse
                if kind == 'chord':
                    out += [(st + beat, 0.45 * gap, q, lv * 0.82) for q in ch_]
                else:
                    alt = bass if kind == 'bass' else bass + 7
                    out.append((st + beat if beat else t, 0.9 * gap + (0.0 if beat else st - t), alt, lv * 1.05))
                k += 1
            continue
        notes = [(t, end - t, q) for q in v]
        if ped is not None:
            notes.append((t, end - t, ped))
        step = _sec(ms / 1000.0, b) / max(1, len(notes) - 1)
        struck = len(out)
        for i, (tt, dd, q) in enumerate(sorted(notes, key=lambda x: x[2])):
            out.append((tt + i * step, max(0.1, dd - i * step), q, lv * (1.0 if i == 0 else 0.9)))
        # answer the right hand on a chord of a bar or more, in the meter's place
        if d >= bar - _EPS and rng.random() < p_answer:
            cands = mtr['answer']
            if mtr['weights'] is not None:                   # one place drawn: no hunting for a gap
                r, pick = rng.random() * sum(mtr['weights']), len(cands) - 1
                for j, w in enumerate(mtr['weights']):
                    r -= w
                    if r < 0:
                        pick = j
                        break
                cands = (cands[pick],)
            for off in cands:
                cand = st + off
                if cand < st + d - 0.5 and not rh_hits(cand):
                    dd = min(1.0, st + d - cand - 0.05)
                    lv_a = lv0 * feel(cand) * mtr['light']
                    if mtr['lift']:                          # the hand lifts off the held voicing to re-strike it
                        out[struck:] = [(s_, min(d_, max(0.1, cand - s_ - 0.04)) if q_ in v else d_, q_, v_)
                                        for s_, d_, q_, v_ in out[struck:]]
                    for i, q in enumerate(sorted(v)):
                        out.append((cand + i * step * 0.6, dd, q, lv_a))
                    break
    # the touch shapes the level, `vel` keeps the loudness (normalized in energy: a piano's energy grows ~ velocity^4)
    norm = (len(applied) / sum(f ** 4 for f in applied)) ** 0.25 if applied else 1.0
    ns = [Note(max(0.0, s), max(0.05, d), q, _vel(v * norm)) for s, d, q, v in out if s < L]
    return Clip._raw(ns, L)


# ------------------------------------------------------------------------------------------------ pedal

def top_leads(clip, factor: float, window: float = 0.06):
    """The melody on top leads: every note struck under the highest one of its onset (within `window` beats: the
    octave / sixth / third doubles, a rolled voicing) played at `factor` x its velocity."""
    c = as_clip(clip)
    soft, group = set(), []
    for n in sorted(c, key=lambda n: n.start) + [None]:
        if group and (n is None or n.start - group[0].start > window):
            top = max(g.pitch for g in group)
            soft.update((g.start, g.pitch) for g in group if g.pitch < top)
            group = []
        if n is not None:
            group.append(n)
    return c.map(lambda n: n._replace(vel=max(1, round(n.vel * factor))) if (n.start, n.pitch) in soft else n)


class Player:
    """A pianist through a whole song: arrange() per section with one Memory (the ornament budget song-wide), the
    melody touched (humanize.touch lo..hi), both hands played, the harmony pedal collected and written once.

        pp = pianist.Player(lead, bpm=BPM, key=s.key, ornaments=ORN)
        pp.play(VERSE, P_verse, verse1, lo=52, hi=88, style='sparse', density=0.35, seed=2)   # a str: degrees
        pp.play(hook, P_chorus, chorus1, lo=70, hi=108, devices=HOOKDEV, doubles=0.75)
        pp.play(PRE, P_pre, pre1, lo=60, hi=96, until=28)        # the hook voice rests from beat 28 (pedal up)
        pp.pedal()                                               # the pedal lane, once

    play(melody, prog, at, *, lo, hi, key=None, octave=4, gate=0.95, until=None, **arrange options): melody is a
    degree string (key.motif(...).clip(octave, gate)), a Motif or a Clip; until= cuts both hands there (beats into
    the part) and lifts the pedal; every arrange() option can be given per call or as a Player default. Returns the
    Arrangement (also in .arrangements)."""

    def __init__(self, track, *, bpm, key=None, lh_track=None, memory: Memory | None = None, log=None, **defaults):
        self.track, self.lh_track, self.bpm, self.key = track, lh_track, bpm, key
        self.memory = memory if memory is not None else Memory()
        self.defaults = defaults
        self.log = log
        self.arrangements: list = []
        self._pedal: list = []

    def play(self, melody, prog, at, *, lo, hi, key=None, octave: int = 4, gate: float = 0.95, until=None, **kw):
        from .humanize import touch
        k = key if key is not None else self.key
        if isinstance(melody, str):
            melody = _key(k).motif(melody)
        m = melody.clip(octave=octave, gate=gate) if hasattr(melody, 'clip') and not isinstance(melody, Clip) \
            else melody
        opts = dict(self.defaults, **kw)
        arr = arrange(touch(m, lo, hi), prog, bpm=self.bpm, key=k, memory=self.memory, at=at, **opts)
        rh, lh = arr.rh, arr.lh
        if until is not None:
            rh, lh = rh.slice(0, until), (lh.slice(0, until) if len(lh) else lh)
        self.track.play(rh, at)
        if len(lh):
            (self.lh_track or self.track).play(lh, at)
        pts = arr.pedal(prog, at)
        if until is not None:
            t = self.track._song.at(at, until)
            pts = [p for p in pts if p[0] < t] + [(t, 0.0)]
        self._pedal.extend(pts)
        self.arrangements.append(arr)
        if self.log:
            self.log(f"pianist {getattr(at, 'name', at)}: {arr!r}")
        return arr

    def pedal_points(self) -> list:
        """The collected pedal points, one per beat (rounded to 1e-4: the later call wins), sorted."""
        return sorted({round(t, 4): (t, v) + tuple(c) for t, v, *c in self._pedal}.values())

    def pedal(self, *, before=None, then=()):
        """Write the collected pedal on the track ('instrument.pedal', the first point plain): points before
        `before` (a position) only, then the points `then` (an ending's own pedal)."""
        pts = self.pedal_points()
        if before is not None:
            b = self.track._song._at(before)
            pts = [p for p in pts if p[0] < b] + list(then)
        else:
            pts += list(then)
        self.track.automate('instrument.pedal', [p[:2] if i == 0 else p for i, p in enumerate(pts)])
        return self.track


def pedal(prog, at=0.0, *, dry=(), lift: float = 0.1, end=None, early: float = 0.0) -> list:
    """Sustain-pedal points for 'instrument.pedal': up at every chord change of `prog` (placed at `at`), down again
    `lift` beats later, and UP during the `dry` windows ((start, end) beats relative to `at`: trills, runs,
    repeated notes - a pianist clears the pedal so fast figures don't smear), down again after them while the chord
    lasts; up at the end (`end`, default the progression's end) - `early` beats before it. Returns absolute points."""
    p = _as_prog(prog, None, 4.0)
    a = _pos(at)
    stop = (p.length if end is None else _pos(end) - a) - early
    starts = sorted({st for st, _, c in p if c is not None and st < stop - _EPS})
    wins = sorted((float(s), float(e)) for s, e in dry if e > s)

    def down(t):
        if any(s - 0.02 <= t < e for s, e in wins):
            return False
        if t >= stop:
            return False
        return not any(st <= t < st + lift for st in starts)
    edges = sorted({0.0, stop} | set(starts) | {st + lift for st in starts} | {s - 0.02 for s, _ in wins}
                   | {e for _, e in wins})
    edges = [x for x in edges if 0.0 <= x <= stop]
    pts: list = []
    state = None
    for x in edges:
        s = down(x + 1e-4)
        if s != state:
            pts.append((round(a + x, 6), 1.0 if s else 0.0, 'step'))
            state = s
    if state:
        pts.append((round(a + stop, 6), 0.0, 'step'))
    return pts


# ------------------------------------------------------------------------------------------------ the arranger

FILL_KINDS = ('run', 'chromatic', 'arpeggio', 'answer', 'stabs', 'fourths', 'pentatonic', 'hands', 'octave_run',
              'tremolo', 'repeated', 'gliss')
"""What arrange() plays in the melody's gaps: run (a scale run leading into the next note), chromatic (a run-down
into it), arpeggio (a sweep through the chord), answer (the phrase's tail echoed below), stabs (comping chords),
fourths (cascading 4ths), pentatonic (a pentatonic run), hands (alternating-hands 16ths), octave_run, tremolo (a
chord tremolo swell), repeated (a repeated dyad figure), gliss (a fast scale sweep into the next section: only in the
last gap before the clip end)."""

ORNAMENTS = ('trill', 'tremolo', 'restrike', 'turn', 'mordent', 'inverted_mordent', 'roll', 'crush', 'blues_crush',
             'slip', 'repeated', 'shake')
"""What arrange() does with a long melody note: the moves of the same names, 'restrike' = the melody held while the
voicing under it is struck again (re-voiced) half-way through, 'roll' = a slow, big roll, 'shake' = the block-chord
shake (phrase-end notes)."""

STYLES = {
    'straight': dict(devices={'guide': 3.0, 'thirds': 2.0, 'sixths': 1.5, 'drop2': 2.0, 'quartal': 1.5, 'close': 1.0,
                              'octave': 0.8},
                     ornaments={'trill': 1.4, 'turn': 1.0, 'mordent': 0.8, 'inverted_mordent': 0.8, 'restrike': 1.5,
                                'roll': 0.8, 'crush': 1.0, 'tremolo': 0.7, 'repeated': 0.5, 'blues_crush': 0.5},
                     fills={'run': 2.0, 'answer': 2.0, 'stabs': 1.5, 'fourths': 1.0, 'arpeggio': 1.2,
                            'chromatic': 0.8, 'pentatonic': 1.0, 'hands': 0.5, 'repeated': 0.3},
                     roll=(8, 20), anticipate=0.25, delay=0.08, voices=3, inner=0.8, fill=0.7, embellish=0.55,
                     weak=1.0, quick=0.12, lh='guide', fast_every=16, spice_every=2),
    'ballad': dict(devices={'drop2': 3.0, 'close': 2.0, 'ust': 1.5, 'guide': 1.0, 'sixths': 1.0, 'quartal': 1.0},
                   ornaments={'trill': 1.4, 'roll': 2.0, 'restrike': 2.0, 'turn': 1.0, 'tremolo': 1.2, 'mordent': 0.5},
                   fills={'arpeggio': 3.0, 'answer': 2.0, 'run': 1.0, 'fourths': 0.6, 'pentatonic': 0.6,
                          'tremolo': 0.6},
                   roll=(15, 25), anticipate=0.1, delay=0.05, voices=3, inner=0.78, fill=0.6, embellish=0.6,
                   weak=0.9, quick=0.08, lh='rootless', fast_every=10, spice_every=2),
    'bar': dict(devices={'octave': 3.0, 'drop2': 1.5, 'locked': 1.0, 'thirds': 1.5, 'guide': 1.0, 'sixths': 1.0},
                ornaments={'crush': 1.5, 'blues_crush': 2.0, 'slip': 1.5, 'repeated': 1.2, 'tremolo': 1.5, 'shake': 1.0,
                           'trill': 1.0, 'mordent': 1.0, 'turn': 0.6},
                fills={'chromatic': 2.0, 'hands': 1.5, 'run': 1.5, 'stabs': 2.0, 'octave_run': 1.0, 'fourths': 0.8,
                       'repeated': 1.0, 'tremolo': 0.6, 'answer': 1.0},
                roll=(6, 14), anticipate=0.35, delay=0.1, voices=3, inner=0.8, fill=0.75, embellish=0.6, weak=1.0,
                quick=0.3, lh='guide', fast_every=16, spice_every=1.5),
    'lush': dict(devices={'drop2': 3.0, 'ust': 2.0, 'close': 2.0, 'quartal': 1.5, 'octave': 0.5},
                 ornaments={'roll': 2.0, 'tremolo': 2.0, 'trill': 1.5, 'restrike': 2.0, 'turn': 0.7},
                 fills={'arpeggio': 3.0, 'answer': 1.0, 'fourths': 1.0, 'run': 1.0, 'tremolo': 1.0},
                 roll=(15, 25), anticipate=0.15, delay=0.05, voices=4, inner=0.78, fill=0.7, embellish=0.7,
                 weak=1.0, quick=0.08, lh='rootless', fast_every=12, spice_every=2),
    'sparse': dict(devices={'guide': 3.0, 'single': 3.0, 'thirds': 1.0, 'quartal': 1.0},
                   ornaments={'mordent': 1.0, 'crush': 1.0, 'restrike': 1.0, 'turn': 0.5, 'trill': 0.5},
                   fills={'answer': 3.0, 'stabs': 1.0, 'run': 0.5, 'pentatonic': 0.5},
                   roll=(8, 16), anticipate=0.2, delay=0.1, voices=2, inner=0.8, fill=0.4, embellish=0.3, weak=0.4,
                   quick=0.12, lh='guide', fast_every=0, spice_every=3),
}
"""arrange() style presets: which voicing devices (weights), ornaments on long notes, gap fills, the chord roll
range (ms), anticipation / delayed-entrance probabilities, voices under the melody, the inner-voice level (x the
melody velocity: ~10-15 velocity under it), fill / embellish probabilities (scaled by density), weak (how often
short off-beat chord tones get a voice too), quick (the chance of a quick ornament - blues crush, crush, slip note,
mordent, turn - on a shorter chord tone, at most one per phrase), the default left hand and the ornament budget:
fast_every (bars per FAST alternation: straight / bar 16, lush 12, ballad 10, sparse 0 = none) and spice_every
(bars between two SPICE ornaments: 1.5-3)."""

FAST = ('trill', 'tremolo', 'shake', 'repeated', 'hands')
"""The fast two-key alternations (ornaments and fills of these names: trill, tremolo, shake, repeated notes,
alternating hands). User feedback 2026-09-30 (perry-street-rain v3): "etwas zu viele von diesen schnellen
Zwei-Tasten-Wechseln" - they are rare spice, not a habit: arrange() budgets them (fast_every / same_every)."""

SPICE = ('turn', 'mordent', 'inverted_mordent', 'crush', 'blues_crush', 'slip', 'roll')
"""The other ornaments: a separate, larger budget (spice_every). 'restrike' (the voicing re-struck under a held
melody note) is not an ornament figure and is not budgeted."""


def _fast_kind(name: str) -> str:
    return {'alternating_hands': 'hands', 'slip_note': 'slip'}.get(name, name)


class Memory:
    """What one pianist already played in a song. Pass the same Memory to every arrange() call of the song
    (memory=, with at= the clip's position in beats; without at= each call follows the previous one) and the
    ornament budget counts song-wide: a trill at the end of one chorus keeps the next chorus from trilling again,
    two tremolos never land within same_every bars, never in neighbouring phrases. played(at, kind) books a move
    placed by hand (a pianist.trill() in the intro); save(at) keeps the fast budget free for a later moment (the
    climax: the calls before it keep their fast figures fast_every bars away from it). .fast / .spice: [(beat,
    kind, phrase number)], .saved: [beat]."""

    def __init__(self):
        self.clock = 0.0
        self.phrases = 0
        self.fast: list = []
        self.spice: list = []
        self.saved: list = []

    def save(self, at) -> 'Memory':
        """Save the fast budget for beat `at` (a climax, the final chord): arrange() calls whose clip does not
        contain `at` treat it as taken; the call that contains it spends it on its best-placed candidate."""
        self.saved.append(_pos(at))
        return self

    def played(self, at, kind: str) -> 'Memory':
        """Book a move played outside arrange() at beat `at` (a FAST or SPICE name, or a MOVES name)."""
        t, k = _pos(at), _fast_kind(kind)
        if k in FAST:
            self.fast.append((t, k, self.phrases))
        elif k in SPICE:
            self.spice.append((t, k, self.phrases))
        else:
            raise ComposeError(f"Memory.played: {kind!r} is not a budgeted ornament ({', '.join(FAST + SPICE)})")
        self.phrases += 1
        self.clock = max(self.clock, t)
        return self

    def __repr__(self) -> str:
        return (f"Memory({len(self.fast)} fast: {', '.join(f'{k}@{t:g}' for t, k, _ in self.fast)}; "
                f"{len(self.spice)} spice; clock {self.clock:g}, {self.phrases} phrases)")


_STRUCTURAL = 2.0
"""The score a FAST candidate needs (a structural moment): the clip's last long note (+1.5), a phrase end (+1), the top
of the line (+0..1), a section-end fill (+1.5), climax=True (+0.5) on top of the base (ornament 1 + up to 0.5 for a
long note, fill 0.8 + up to 0.5 for a long gap)."""


def _budget(events, memory, at, L, nphr, bpb, fast_every, spice_every, same_every) -> dict:
    """Keep the best-placed FAST candidates (events: dicts with kind / t / phrase / score): at most one per
    fast_every bars, two of a kind at least same_every bars apart, never in neighbouring phrases (counted with
    `memory`'s earlier ones). Sets e['keep']; returns the budget record (finished by _spice)."""
    fe = _num(fast_every, 'pianist fast_every (bars)', 0)
    sp = _num(spice_every, 'pianist spice_every (bars)', 0)
    se = _num(same_every, 'pianist same_every (bars)', 0)
    if memory is not None and not isinstance(memory, Memory):
        raise ComposeError(f"pianist memory must be a pianist.Memory(), got {memory!r}")
    base = _pos(at) if at is not None else (memory.clock if memory is not None else 0.0)
    ph0 = memory.phrases if memory is not None else 0
    booked = list(memory.fast) if memory is not None else []
    saved = list(memory.saved) if memory is not None else []
    bud = Budget({'fast': fe * bpb}, same_every=se * bpb, min_score={'fast': _STRUCTURAL}, phrase_gap={'fast': 1.0},
                 events=[(t, 'fast', k_, q) for t, k_, q in booked], saved=saved)
    fast = [e for e in events if e['kind'] in FAST]
    for e in fast:
        e.update(cls='fast', name=e['kind'], phrase=e['phrase'] + ph0)
    for e in bud.keep(fast, base, (base, base + L), slots=False):
        booked.append((base + e['t'], e['kind'], e['phrase']))
    for e in fast:
        e['phrase'] -= ph0
    return {'fast_every': fe, 'spice_every': sp, 'same_every': se, 'at': base, '_phrase0': ph0, '_booked': booked,
            '_L': L, '_nphr': nphr}


def _spice(events, bud: dict, memory, bpb) -> None:
    """Keep SPICE candidates (e['keep'] None) at least spice_every bars apart, the best-placed first; finish the
    budget record and move `memory` on."""
    base, ph0, L = bud['at'], bud.pop('_phrase0'), bud.pop('_L')
    nphr = bud.pop('_nphr')
    sp = bud['spice_every']
    booked = list(memory.spice) if memory is not None else []
    bud_ = Budget({'spice': sp * bpb}, events=[(t, 'spice', k_, q) for t, k_, q in booked])
    spice = [e for e in events if e['kind'] in SPICE and e.get('keep') is None]
    for e in spice:
        e['cls'] = 'spice'
    for e in bud_.keep(spice, base, slots=False):
        booked.append((base + e['t'], e['kind'], ph0 + e['phrase']))
    fast = bud.pop('_booked')
    bud['fast'] = [(round(t - base, 4), k) for t, k, _ in sorted(fast) if base - _EPS <= t < base + L]
    bud['spice'] = sum(1 for t, _, _ in booked if base - _EPS <= t < base + L)
    bud['dropped'] = [(round(e['t'], 4), e['kind'], e.get('sub')) for e in sorted(events, key=lambda e: e['t'])
                      if e.get('keep') is False]
    if memory is not None:
        memory.saved = [t for t in memory.saved if not base - _EPS <= t < base + L]
        memory.fast, memory.spice = sorted(fast), sorted(booked)
        memory.clock, memory.phrases = base + L, ph0 + nphr

_DRY = {'trill', 'repeated', 'shake', 'run', 'chromatic', 'fourths', 'pentatonic', 'hands', 'octave_run', 'gliss',
        'mordent', 'inverted_mordent', 'turn'}


class Arrangement:
    """What arrange() played: rh / lh (Clips), melody (the melody as placed: after anticipations), moves (a log:
    (start, end, kind, name) with kind 'ornament' | 'fill' | 'device', and 'dropped' for an ornament / fill the
    budget did not allow - its substitute, if any, is logged as played), dry ((start, end) windows where the pedal
    should come up: runs and repeated notes), budget (fast_every / spice_every / same_every, 'fast': the FAST
    alternations kept [(beat, kind)], 'spice': how many SPICE ornaments, 'dropped': [(beat, kind, substitute)]).
    pedal(prog, at) -> the pedal points; summary() counts what was used (and 'dropped:<kind>'); place(rh_track,
    lh_track, at) plays it (the two hands and the pedal); prog / at: what arrange() was given."""

    def __init__(self, rh: Clip, lh: Clip, melody: Clip, moves: list, dry: list):
        self.rh, self.lh, self.melody, self.moves, self.dry = rh, lh, melody, moves, dry
        self.harmonized = 0.0          # share of melody notes with voices under them (or an ornament)
        self.budget: dict = {}
        self.prog = None               # the changes arrange() played over
        self.at = None                 # arrange(at=): where it is meant to be placed

    def place(self, rh_track, lh_track=None, at=None, *, pedal: bool = True, end=None) -> 'Arrangement':
        """Play the arrangement: the right hand on rh_track, the left hand on lh_track (the comping track; default
        rh_track) when it has notes, and with pedal=True the harmony pedal on rh_track (self.pedal(prog, at, end=)).
        at defaults to arrange(at=) - a Section, beat or (section, beats)."""
        if at is None:
            at = self.at
        if at is None:
            raise ComposeError("Arrangement.place(): give at= (arrange() had no at=)")
        rh_track.play(self.rh, at)
        if len(self.lh):
            (lh_track or rh_track).play(self.lh, at)
        if pedal:
            if self.prog is None:
                raise ComposeError("Arrangement.place(pedal=True): the arrangement has no progression")
            rh_track.automate('instrument.pedal', self.pedal(self.prog, rh_track._song._at(at), end=end))
        return self

    def __repr__(self) -> str:
        return (f"Arrangement(rh {len(self.rh)} notes, lh {len(self.lh)} notes, {self.harmonized:.0%} of the melody "
                f"harmonized, {self.summary()})")

    def pedal(self, prog, at=0.0, lift: float = 0.1, end=None) -> list:
        """Harmony pedal with the dry windows lifted (pianist.pedal)."""
        return pedal(prog, at, dry=self.dry, lift=lift, end=end)

    def summary(self) -> dict:
        out: dict = {}
        for _, _, kind, name in self.moves:
            out[f"{kind}:{name}"] = out.get(f"{kind}:{name}", 0) + 1
        return dict(sorted(out.items()))

    @property
    def ornaments(self) -> list:
        return [(a, b, n) for a, b, k, n in self.moves if k == 'ornament']

    @property
    def fills(self) -> list:
        return [(a, b, n) for a, b, k, n in self.moves if k == 'fill']


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


def arrange(melody, prog, *, bpm, key=None, style: str = 'straight', density: float = 0.5, seed=0, lh=None,
            floor=None, voices: int | None = None, roll=None, anticipate: float | None = None,
            delay: float | None = None, fill: float | None = None, embellish: float | None = None,
            quick: float | None = None,
            devices: dict | None = None, ornaments: dict | None = None, fills: dict | None = None,
            climax: bool = False, lead_in: bool = False, section_end: bool = True, inner: float | None = None,
            lh_vel: float = 58, lh_register=('C3', 'C4'), ceiling='C7', fast_every: float | None = None,
            spice_every: float | None = None, same_every: float = 32.0, memory: Memory | None = None,
            at=None, meter=None, lh_answers: float | None = None, doubles: float | None = None) -> Arrangement:
    """A pianist's arrangement of a melody over changes -> Arrangement (.rh, .lh, .pedal(prog, at), .moves).

    The melody stays on top; per phrase (split at rests of an 8th or more; a line longer than ~6 beats changes
    device after a long note or at a bar line) the right hand picks a voicing DEVICE
    (seeded from the style's weights, never the same one twice running; climax=True favours octaves / locked
    hands / drop 2) and harmonizes: chord tones on strong beats and long notes get the full device, short weak
    chord tones a guide tone at most, non-chord (passing) notes stay single (thirds / sixths move in parallel with
    the line); long notes (1.5+ beats) are embellished with an ORNAMENT (trill, tremolo, restrike, turn, mordent,
    roll, crush / blues crush, slip note, repeated notes, shake - at most one per phrase, two when dense) and now and
    then a shorter chord tone gets a quick one (blues crush on a major 3rd, crush, slip note, mordent, turn: the
    style's `quick` rate); gaps of a
    beat or more get a FILL (run, chromatic run-down, arpeggio sweep, answer, stabs, cascading 4ths, pentatonic
    run, alternating hands, octave run, tremolo, repeated dyads; the last gap before the clip end a glissando with
    section_end=True; the gap before the first note only with lead_in=True). Rhythm: anticipations (a phrase note on
    beat 1 or 3 an 8th early, voiced with the chord it belongs to) and delayed entrances; chords rolled (the lower
    voices lead into the melody, which keeps its time). Velocities: the melody's own (use jazz.touch() first), inner
    voices x inner (~10-15 under). lh= a LH_STYLES left hand (the style's default with lh=True; None = none): then
    the right hand stays above `floor` (default C4 with a left hand, G3 without); meter= ('6/8', ...; default from
    the progression's beats per bar, 3 = 3/4) and lh_answers= (the chance of an answering re-strike per chord of a
    bar or more; default density x 0.8) go to left_hand().

    Ornament budget (user feedback 2026-09-30: too many fast two-key alternations): the FAST alternations (trill,
    tremolo, shake, repeated notes, alternating hands - ornaments and fills) are rare spice: at most one per
    `fast_every` bars (the style's: straight / bar 16, lush 12, ballad 10, sparse 0 = none), two of the same kind
    at least `same_every` bars (32) apart, never in neighbouring phrases, only at structural moments and the
    best-placed first (the clip's last long note, a phrase end, the top of the line, a section-end fill,
    climax=True); a dropped one becomes another
    ornament / fill of the style (not a fast one) or the plain voicing. The SPICE ornaments (turn, mordent, crush,
    blues crush, slip note, roll) share a larger budget: at least `spice_every` bars apart (1.5-3; 0 = none).
    memory= a pianist.Memory() shared by all arrange() calls of a song (at= the clip's position in beats) counts
    the budget song-wide; without it each call counts alone. What was kept / dropped: .budget, .moves ('dropped'),
    .summary(). Ornaments are played light and legato (their figures 25-40 velocity under the principal note, the
    pedal stays down); runs and repeated notes lift it.

    style: STYLES ('straight', 'ballad', 'bar', 'lush', 'sparse'); density 0..1 scales how much is harmonized,
    embellished and filled; devices= / ornaments= / fills= override the style's weights; voices, roll (ms range),
    anticipate, delay, fill, embellish, quick, inner, fast_every, spice_every override single settings.
    doubles= a velocity factor for the notes struck under the melody's top note (top_leads(): the octave / sixth /
    third doubles softer, so the melody leads; 0.75 for a hook in octaves). Deterministic by seed."""
    if style not in STYLES:
        raise ComposeError(f"pianist style must be one of {', '.join(STYLES)}, got {style!r}")
    S = dict(STYLES[style])
    b = _bpm(bpm)
    dens = _num(density, 'pianist density', 0, 1)
    rng = random.Random(seed_int(seed))
    m = as_clip(melody)
    p = _as_prog(prog, key, m.length or 4.0)
    L = max(m.length, p.length)
    k = _key(key) if key is not None else p.key
    if lh is True:
        lh = S['lh']
    if lh is not None and lh is not False and lh not in LH_STYLES:
        raise ComposeError(f"pianist lh must be one of {', '.join(LH_STYLES)}, True or None, got {lh!r}")
    if meter is not None:
        _lh_meter(meter, p.beats_per_bar)              # strict: a wrong meter is an error even without a left hand
    fl = note(floor) if floor is not None else (60 if lh else 55)
    top_lim = note(ceiling)
    nv = int(_num(voices if voices is not None else S['voices'], 'pianist voices', 0, 5))
    rl = roll if roll is not None else S['roll']
    p_ant = _num(anticipate if anticipate is not None else S['anticipate'], 'pianist anticipate', 0, 1)
    p_del = _num(delay if delay is not None else S['delay'], 'pianist delay', 0, 1)
    p_fill = min(1.0, _num(fill if fill is not None else S['fill'], 'pianist fill', 0, 1) * (0.5 + dens))
    p_emb = min(1.0, _num(embellish if embellish is not None else S['embellish'], 'pianist embellish', 0, 1)
                * (0.5 + dens))
    inn = _num(inner if inner is not None else S['inner'], 'pianist inner', 0.3, 1.0)
    dev_w = dict(devices if devices is not None else S['devices'])
    orn_w = dict(ornaments if ornaments is not None else S['ornaments'])
    fill_w = dict(fills if fills is not None else S['fills'])
    for name in dev_w:
        if name not in DEVICES:
            raise ComposeError(f"unknown voicing device {name!r}; use {', '.join(DEVICES)}")
    for name in orn_w:
        if name not in ORNAMENTS:
            raise ComposeError(f"unknown ornament {name!r}; use {', '.join(ORNAMENTS)}")
    for name in fill_w:
        if name not in FILL_KINDS:
            raise ComposeError(f"unknown fill {name!r}; use {', '.join(FILL_KINDS)}")
    if climax:
        for d_, w in (('octave', 3.0), ('locked', 2.0), ('drop2', 1.5)):
            dev_w[d_] = dev_w.get(d_, 0.0) + w
        for f_, w in (('octave_run', 1.5), ('hands', 1.0), ('tremolo', 0.8)):
            fill_w[f_] = fill_w.get(f_, 0.0) + w
        orn_w['tremolo'] = orn_w.get('tremolo', 0.0) + 1.0
        orn_w['shake'] = orn_w.get('shake', 0.0) + 0.8
    bpb = p.beats_per_bar

    # ---- the melody line: the top note of every onset; given lower notes are kept as they are
    ns = sorted(m, key=lambda n: (n.start, -n.pitch))
    mel: list[list] = []            # [start, dur, pitch, vel, harmony_time]
    given: list[Note] = []
    for n in ns:
        if mel and abs(n.start - mel[-1][0]) < 0.02:
            given.append(n)
            continue
        mel.append([n.start, n.dur, n.pitch, n.vel, n.start])

    # ---- rhythm: anticipations and delayed entrances
    for i, n in enumerate(mel):
        st = n[0]
        prev_end = mel[i - 1][0] + mel[i - 1][1] if i else -math.inf
        gap = st - prev_end
        pos = st % bpb
        on_beat = abs(pos - round(pos)) < 1e-6
        strong = on_beat and int(round(pos)) % 2 == 0
        r = rng.random()
        if strong and n[1] >= 0.5 - _EPS and st >= 0.5 and r < p_ant and n[1] > 0.15:
            if gap >= 0.5 - _EPS:
                n[0], n[1] = st - 0.5, n[1] + 0.5
            elif i and mel[i - 1][1] >= 1.0 - _EPS and mel[i - 1][0] < st - 0.75:
                mel[i - 1][1] = st - 0.5 - mel[i - 1][0]
                n[0], n[1] = st - 0.5, n[1] + 0.5
        elif on_beat and gap >= 1.0 - _EPS and n[1] >= 1.0 - _EPS and r > 1.0 - p_del:
            n[0], n[1] = st + 0.5, n[1] - 0.5

    # ---- phrases
    phr: list[list[list]] = []
    for n in mel:
        if not phr or n[0] - max(x[0] + x[1] for x in phr[-1]) >= 0.5 - _EPS:
            phr.append([n])
        else:
            phr[-1].append(n)
    # long phrases (a line without rests) change device every ~2 bars: split after a long note or at a bar line
    units: list[tuple[list[list], bool]] = []          # (notes, ends the real phrase)
    for pi, ph in enumerate(phr):
        cur, t0 = [ph[0]], ph[0][0]
        for prev, n in zip(ph, ph[1:]):
            if n[0] - t0 >= 6.0 - _EPS and (prev[1] >= 1.0 - _EPS or abs(n[0] % bpb) < 1e-6):
                units.append((cur, False, pi))
                cur, t0 = [n], n[0]
            else:
                cur.append(n)
        units.append((cur, True, pi))

    rh: list[tuple] = []            # (start, dur, pitch, vel) - not rolled
    groups: list[list[tuple]] = []  # chords: rolled at the end (melody last, on its time)
    moves: list = []
    dry: list = []
    last_dev = None
    mel_vels = [n[3] for n in mel] or [80]
    ref_v = sum(mel_vels) / len(mel_vels)

    n_harm = [0]

    def chord_at(t):
        return p.at(min(max(t, 0.0), L - 1e-6))

    p_quick = min(1.0, _num(quick if quick is not None else S['quick'], 'pianist quick', 0, 1) * (0.5 + dens))
    events: list[dict] = []         # ornaments and fills, kept or dropped by the budget after the pass
    mel_lo, mel_hi = min((n[2] for n in mel), default=60), max((n[2] for n in mel), default=72)
    arrival = max((n for n in mel if n[1] >= 1.5 - _EPS), key=lambda n: n[0], default=None)   # last long note

    def height(q):
        return (q - mel_lo) / max(1, mel_hi - mel_lo)
    for ph, real_end, pi in units:
        dev = _pick(rng, dev_w, avoid=last_dev) or 'single'
        last_dev = dev
        moves.append((ph[0][0], ph[-1][0] + ph[-1][1], 'device', dev))
        goal = max(ph, key=lambda x: (x[2], x[1]))
        n_orn = n_quick = 0
        max_orn = 2 if dens > 0.7 and style in ('ballad', 'lush') else 1
        # the ornament goes on the phrase's best long note (the longest; ties: the later)
        longs = [x for x in ph if x[1] >= 1.5 - _EPS and x[1] * 60.0 / b >= 0.7]
        orn_targets = []
        for x in sorted(longs, key=lambda x: (-x[1], -x[0])):
            if len(orn_targets) < max_orn and rng.random() < p_emb:
                orn_targets.append(id(x))
        for idx, n in enumerate(ph):
            st, du, mp, mv, ht = n
            ch = chord_at(ht)
            if du <= 0.15 + _EPS or ch is None:
                rh.append((st, du, mp, mv))
                continue
            ct = mp % 12 in _colour(ch)
            on_beat = abs(st - round(st)) < 1e-6
            strong = on_beat or du >= 1.0 - _EPS or n is goal
            if dev in ('thirds', 'sixths') and du >= 0.25 - _EPS:
                d_ = dev
            elif not ct:
                d_ = 'single'
            elif strong:
                d_ = dev if rng.random() < 0.55 + 0.45 * dens else 'guide'
            else:
                r_ = rng.random() / S['weak'] if dev != 'single' else 1.0
                d_ = 'guide' if r_ < 0.25 + 0.45 * dens else 'thirds' if r_ < 0.35 + 0.55 * dens else 'single'
            if d_ in ('thirds', 'sixths') and not ct and du < 0.5 - _EPS and rng.random() < 0.5:
                d_ = 'single'
            try:
                vc = voicing(ch, mp, d_, floor=fl, voices=1 if d_ == 'guide' and not strong else nv, key=k)
            except ComposeError:
                vc = [mp]
            under = vc[:-1]
            hold = du * (0.97 if du <= 0.5 else 1.0)
            iv = mv * inn
            chord_notes = [(st, hold, q, iv * (0.95 if i == 0 and len(under) > 2 else 1.0)
                            * (1.0 + (rng.random() - 0.5) * 0.06)) for i, q in enumerate(under)]
            p_end = real_end and idx == len(ph) - 1
            ctx = (ch, mp, mv, under, st, du, p_end)
            plain = chord_notes + [(st, du, mp, mv)]
            if id(n) in orn_targets:
                kind = _ornament(rng, orn_w, ch, mp, under, du, p_end, b)
                if kind is not None:
                    fig, dry_w = _ornament_notes(kind, rng, ch, k, mp, mv, under, st, du, b, inn, fl)
                    # structural moments score high: the last note of the clip, a phrase end, the top of the line
                    score = (1.0 + 1.5 * (n is arrival) + 1.0 * p_end + 1.0 * height(mp) + 0.5 * min(du, 4.0) / 4.0
                             + 0.5 * climax)
                    events.append(dict(what='ornament', kind=kind, t=st, end=st + du, fig=fig, dry=dry_w,
                                       phrase=pi, score=score, ctx=ctx, plain=plain, under=bool(under)))
                    n_orn += 1
                    continue
            if id(n) not in orn_targets and n_quick < 1 and du >= 0.5 - _EPS and ct and rng.random() < p_quick:
                kind = _quick(rng, orn_w, ch, mp, under, du, strong)
                if kind is not None:
                    fig, dry_w = _ornament_notes(kind, rng, ch, k, mp, mv, under, st, du, b, inn, fl)
                    events.append(dict(what='ornament', kind=kind, t=st, end=st + du, fig=fig, dry=dry_w,
                                       phrase=pi, score=0.3 + 0.5 * height(mp), ctx=ctx, plain=plain,
                                       under=bool(under)))
                    n_quick += 1
                    continue
            groups.append(chord_notes + [(st, du, mp, mv)])
            n_harm[0] += bool(under)

    # ---- fills in the gaps
    spans = [(ph[0][0], max(x[0] + x[1] for x in ph), ph) for ph in phr]
    gaps = []                       # (from, to, phrase before, phrase after, phrase number: between the two)
    if spans and lead_in and spans[0][0] >= 1.0 - _EPS:
        gaps.append((0.0, spans[0][0], None, spans[0][2], -0.5))
    for gi, ((a0, e0, ph0), (a1, _, ph1)) in enumerate(zip(spans, spans[1:])):
        gaps.append((e0, a1, ph0, ph1, gi + 0.5))
    if spans and section_end and L - spans[-1][1] >= 0.75 - _EPS:
        gaps.append((spans[-1][1], L, spans[-1][2], None, len(spans) - 0.5))

    def fill_fig(kind, r, g0, g1, before, after):
        fig = _fill_notes(kind, r, p, k, g0, g1, before, after, b, fl, top_lim, ref_v, inn, L)
        return [x for x in fig or [] if x[0] >= g0 - _EPS and x[0] + x[1] <= g1 + 0.02]
    for g0, g1, before, after, gph in gaps:
        g = g1 - g0
        if g < 0.75 - _EPS or rng.random() >= p_fill:
            continue
        fw = dict(fill_w)
        if after is None:
            fw = {'gliss': 3.0, 'run': 1.0, 'arpeggio': 1.0} if section_end else fw
        else:
            fw.pop('gliss', None)
        if before is None:
            for x in ('answer', 'stabs'):
                fw.pop(x, None)
        kind = _pick(rng, fw)
        if kind is None:
            continue
        fig = fill_fig(kind, rng, g0, g1, before, after)
        if not fig:
            continue
        a_, e_ = min(x[0] for x in fig), max(x[0] + x[1] for x in fig)
        events.append(dict(what='fill', kind=kind, t=a_, end=e_, fig=fig, phrase=gph, fw=fw,
                           gap=(g0, g1, before, after), score=0.8 + 1.5 * (after is None) + 0.5 * climax
                           + 0.5 * min(g1 - g0, 4.0) / 4.0))

    # ---- the ornament budget: fast two-key alternations are rare spice, the other ornaments share a larger budget
    srng = random.Random(f"{seed_int(seed)}:budget")      # substitutes: the main stream (devices, fills) stays put
    side_groups: list[list[tuple]] = []
    budget = _budget(events, memory, at, L, len(phr), bpb, fast_every if fast_every is not None else S['fast_every'],
                     spice_every if spice_every is not None else S['spice_every'], same_every)
    for e in sorted((e for e in events if e.get('keep') is False and e['kind'] in FAST), key=lambda e: e['t']):
        if e['what'] == 'fill':                 # another (not fast) fill in the gap
            kind2 = _pick(srng, {x: w for x, w in e['fw'].items() if x not in FAST})
            fig2 = fill_fig(kind2, srng, *e['gap']) if kind2 else []
            if fig2:
                events.append(dict(what='fill', kind=kind2, t=min(x[0] for x in fig2),
                                   end=max(x[0] + x[1] for x in fig2), fig=fig2, phrase=e['phrase'], score=e['score'],
                                   keep=True))
            e['sub'] = kind2 if fig2 else None
            continue
        ch, mp, mv, under, st, du, p_end = e['ctx']
        kind2 = _ornament(srng, {x: w for x, w in orn_w.items() if x not in FAST}, ch, mp, under, du, p_end, b)
        e['sub'] = kind2
        if kind2 is None:
            side_groups.append(e['plain'])
            n_harm[0] += e['under']
            continue
        fig2, dry2 = _ornament_notes(kind2, srng, ch, k, mp, mv, under, st, du, b, inn, fl)
        events.append(dict(what='ornament', kind=kind2, t=st, end=st + du, fig=fig2, dry=dry2, phrase=e['phrase'],
                           score=e['score'], ctx=e['ctx'], plain=e['plain'], under=e['under'],
                           keep=None if kind2 in SPICE else True))
    _spice(events, budget, memory, bpb)
    n_kept = 0
    for e in sorted(events, key=lambda e: e['t']):
        if e.get('keep') is False:
            moves.append((e['t'], e['end'], 'dropped', e['kind']))
            if e['kind'] in SPICE:              # a dropped quick ornament: the note is played plain
                side_groups.append(e['plain'])
                n_harm[0] += e['under']
            continue
        rh.extend(e['fig'])
        moves.append((e['t'], e['end'], e['what'], e['kind']))
        if e['what'] == 'fill':
            if e['kind'] in _DRY:
                dry.append((e['t'], e['end']))
        else:
            n_kept += 1
            if e['dry']:
                dry.append((e['t'], e['t'] + min(e['end'] - e['t'], e['dry'])))

    # ---- roll the chords: the lower voices lead into the melody, which keeps its time
    for grp, r_ in [(g_, rng) for g_ in groups] + [(g_, srng) for g_ in side_groups]:
        top = grp[-1]
        low = sorted(grp[:-1], key=lambda x: x[2])
        if low and rl:
            ms = r_.uniform(*rl)
            total = _sec(ms / 1000.0, b)
            step = total / len(low)
            for i, (s0, d0, q, v) in enumerate(low):
                off = (len(low) - i) * step
                s1 = max(0.0, s0 - off)
                rh.append((s1, d0 + (s0 - s1), q, v))
        else:
            rh.extend(low)
        rh.append(top)
    rh.extend((n.start, n.dur, n.pitch, n.vel) for n in given)
    rh_ns = [Note(max(0.0, s), max(0.03, d), int(q), _vel(v)) for s, d, q, v in rh if s < L]
    rh_clip = Clip._raw(rh_ns, L)
    lh_clip = Clip._raw((), L)
    if lh:
        antic = [n[4] for n in mel if n[4] - n[0] > 0.25]
        lh_clip = left_hand(p, b, style=lh, register=lh_register, density=dens, vel=lh_vel,
                            anticipate=antic, rh=rh_clip, seed=seed_int(seed) + 7, length=L, meter=meter,
                            answers=lh_answers)
    mel_clip = Clip._raw([Note(n[0], n[1], n[2], n[3]) for n in mel], L)
    if doubles is not None:
        rh_clip = top_leads(rh_clip, doubles)
    arr = Arrangement(rh_clip, lh_clip, mel_clip, sorted(moves), sorted(dry))
    arr.harmonized = (n_harm[0] + n_kept) / max(1, len(mel))
    arr.budget = budget
    arr.prog, arr.at = prog, at
    return arr


def _ornament(rng, weights, ch, mp, under, du, phrase_end, b) -> str | None:
    """Pick an ornament that fits the note."""
    w = dict(weights)
    kind3 = chord_kind(ch)
    third = (mp - ch.root) % 12 == 4 and kind3 in ('maj', 'maj7', '6', 'dom')
    if not third:
        w.pop('blues_crush', None)
    if not under:
        for x in ('tremolo', 'restrike', 'slip', 'roll'):
            w.pop(x, None)
    if not phrase_end:
        w.pop('shake', None)
    if du * 60.0 / b < 0.9:
        w.pop('trill', None)
        w.pop('tremolo', None)
    return _pick(rng, w)


def _quick(rng, weights, ch, mp, under, du, strong) -> str | None:
    """A quick ornament for a shorter chord-tone melody note (half a beat or more): a blues crush on the major 3rd of
    a major / dominant chord, a crushed grace note or a slip note on a strong note, a mordent on a quarter or
    longer, a turn on a beat or longer."""
    w = {}
    third = (mp - ch.root) % 12 == 4 and chord_kind(ch) in ('maj', 'maj7', '6', 'dom')
    if third and 'blues_crush' in weights:
        w['blues_crush'] = weights['blues_crush'] * 2.0
    if strong:
        for x in ('crush', 'slip'):
            if x in weights and (x != 'slip' or under):
                w[x] = weights[x]
    if du >= 0.75 - _EPS:
        for x in ('mordent', 'inverted_mordent'):
            if x in weights:
                w[x] = weights[x]
    if du >= 1.0 - _EPS and 'turn' in weights:
        w['turn'] = weights['turn']
    return _pick(rng, w)


def _ornament_notes(kind, rng, ch, k, mp, mv, under, st, du, b, inn, fl):
    """The notes of an ornament on melody note mp (st, du) with the voicing `under`; returns (notes, dry beats)."""
    sd = rng.randrange(1 << 30)
    uv = mv * inn
    held = [(st, du, q, uv) for q in under]
    if kind == 'trill':
        c = trill(mp, du, b, chord=ch, key=k, vel=mv, rate=rng.uniform(12.5, 15.5), seed=sd, at=st)
        return held + list(c), 0.0
    if kind == 'tremolo':
        lower = under if under else [mp - 12]
        if len(lower) > 2:
            lower = lower[-2:]
        c = tremolo(lower, [mp], du, b, rate=rng.uniform(9.5, 12.0), swell=rng.choice(('arch', 'cresc')), vel=mv,
                    seed=sd, at=st)
        return list(c), 0.0
    if kind == 'restrike':
        half = st + (1.0 if du >= 2.0 else du / 2.0)
        alt = [q + 12 if q + 12 < mp and (q + 12) not in under else q for q in under[:1]] + under[1:]
        alt = sorted(set(alt))
        out = [(st, du, mp, mv)] + [(st, half - st, q, uv) for q in under]
        out += [(half, st + du - half, q, uv * 0.88) for q in alt if q < mp]
        return out, 0.0
    if kind in ('turn', 'mordent', 'inverted_mordent'):
        f = {'turn': turn, 'mordent': mordent, 'inverted_mordent': inverted_mordent}[kind]
        c = f(mp, du, b, chord=ch, key=k, vel=mv, at=st)
        return held + list(c), 0.0
    if kind == 'roll':
        c = roll(under + [mp], du, b, ms=rng.uniform(45, 75), vel=mv, inner=inn, at=st)
        return list(c), 0.0
    if kind == 'crush':
        c = crush(mp, du, b, grace=-1, together=rng.random() < 0.5, vel=mv, under=under, at=st)
        return list(c), 0.0
    if kind == 'blues_crush':
        c = blues_crush(mp, du, b, vel=mv, under=under, at=st)
        return list(c), 0.0
    if kind == 'slip':
        c = slip_note(under + [mp], du, b, voice=-1, by=-2 if (mp - 2) % 12 in _scale_pcs(ch, k) else -1, vel=mv,
                      inner=inn, at=st)
        return list(c), 0.0
    if kind == 'repeated':
        top = [under[-1], mp] if under else [mp]
        c = repeated(top, du, b, rate=rng.uniform(7.0, 9.0), vel=mv, crescendo=0.4, seed=sd, at=st)
        return list(c), du
    if kind == 'shake':
        c = shake(under + [mp], du, b, interval=3, vel=mv, inner=inn, seed=sd, at=st)     # the brass shake: a minor 3rd
        return list(c), 0.0
    return [(st, du, mp, mv)] + held, 0.0


def _fill_notes(kind, rng, p, k, g0, g1, before, after, b, fl, top_lim, ref_v, inn, L):
    """The notes of one gap fill between g0 and g1 (beats)."""
    sd = rng.randrange(1 << 30)
    g = g1 - g0
    nxt = after[0][2] if after else None
    prv = before[-1][2] if before else None
    ref = prv if prv is not None else (nxt if nxt is not None else 72)
    fv = ref_v * 0.86
    ch = p.at(min(max(g0 + 0.01, 0.0), L - 1e-6))
    ch_end = p.at(min(max(g1 - 0.01, 0.0), L - 1e-6))
    if ch is None:
        return []
    # the fill leads into the next note: it ends a little before it
    margin = 0.03
    if kind in ('run', 'chromatic', 'pentatonic', 'octave_run', 'gliss'):
        ln = min(g - 0.25 if g >= 1.25 else g, 2.0)
        a = g1 - ln
        a = max(g0, math.ceil(a * 4 - _EPS) / 4)
        ln = g1 - margin - a
        if ln < 0.4:
            return []
        if kind == 'gliss':
            tgt = (after[0][2] if after else min(top_lim - 2, max(ref + 7, 79)))
            c = gliss(tgt, ln, b, direction='up', span=rng.choice((12, 14, 17)), chord=ch_end, key=k,
                      vel=(fv * 0.6, fv * 1.08), seed=sd, at=a)
            return [x for x in c if x.pitch >= fl]
        if nxt is None:
            nxt = ref
        n_notes = max(3, int(round(ln / (0.25 if ln >= 1.0 else 1.0 / 6.0))))
        down = prv is not None and prv > nxt + 2 or (prv is None and rng.random() < 0.5)
        if kind == 'chromatic':
            end = nxt + 1 if down else nxt - 1
            start = end + (n_notes - 1) * (1 if down else -1)
            c = chromatic_run(start, end, ln, b, vel=(fv * 0.95, fv * 0.8) if down else (fv * 0.8, fv), seed=sd,
                              at=a)
        elif kind == 'pentatonic':
            end_pcs = _pentatonic(ch, k)
            start = nxt + (7 if down else -7)
            c = pentatonic_run(start, ln, b, notes=n_notes, direction='down' if down else 'up', chord=ch, key=k,
                               vel=(fv * 0.98, fv * 0.8), seed=sd, at=a)
            del end_pcs
        else:
            pcs = _scale_pcs(ch_end, k)
            end = _step(nxt, pcs, 1 if down else -1)
            start = _step(end, pcs, (n_notes - 1) * (1 if down else -1))
            if kind == 'octave_run':
                c = octave_run(start, end, ln, b, chord=ch_end, key=k, vel=(fv, fv * 1.1), seed=sd, at=a)
            else:
                c = run(start, end, ln, b, chord=ch_end, key=k, vel=(fv * 0.82, fv * 0.98), seed=sd, at=a)
        out = [x for x in c if fl <= x.pitch <= top_lim]
        return out
    if kind == 'arpeggio':
        ln = min(g - 0.25 if g >= 1.25 else g - margin, 2.5)
        a = g0 + (0.25 if g >= 1.25 else 0.0)
        ln = min(ln, g1 - margin - a)
        if ln < 0.5:
            return []
        hi = min(top_lim, max(ref, nxt or ref) + rng.choice((3, 5, 8)))
        lo_ = max(fl, hi - rng.choice((17, 19, 24)))
        c = sweep(ch, ln, b, low=lo_, high=hi, direction=rng.choice(('up', 'up', 'down')), ring=False,
                  vel=(fv * 0.7, fv), seed=sd, at=a)
        return [(x.start, min(x.dur, g1 - margin - x.start), x.pitch, x.vel) for x in c if x.start < g1 - margin]
    if kind == 'answer':
        if not before or len(before) < 2:
            return []
        tail = [x for x in before[-4:]]
        t0 = tail[0][0]
        span = tail[-1][0] + min(tail[-1][1], 1.0) - t0
        a = math.ceil((g0 + (0.5 if g >= 1.5 else 0.0)) * 2 - _EPS) / 2
        room = g1 - margin - a
        if room < 0.5:
            return []
        f = min(1.0, room / max(span, _EPS))
        sh = -12 if min(x[2] for x in tail) - 12 >= fl else (-5 if rng.random() < 0.5 else 3)
        pcs = _scale_pcs(ch, k)
        out = []
        for x in tail:
            s = a + (x[0] - t0) * f
            if s >= g1 - margin - 0.1:
                break
            q = x[2] + sh
            if q % 12 not in pcs:
                q = _step(q, pcs, -1)
            d = min(x[1] * f, g1 - margin - s)
            out.append((s, max(0.08, d * 0.95), q, fv * 0.85))
        return [x for x in out if x[2] >= fl]
    if kind == 'stabs':
        out = []
        cands = [t for t in (g0 + 0.5, g0 + 1.5, g0 + 1.0, g0 + 2.5) if t + 0.35 <= g1 - margin]
        cands = sorted(set(round(t * 2) / 2 for t in cands if t >= g0))[:2]
        for t in cands:
            c2 = p.at(min(t, L - 1e-6))
            if c2 is None:
                continue
            topn = min(top_lim, max(fl + 7, (nxt or ref) - rng.choice((2, 3, 5))))
            topn = max(q for q in range(topn - 11, topn + 1) if q % 12 in _tones(c2))
            vc = voicing(c2, topn, rng.choice(('close', 'quartal', 'guide')), floor=fl, voices=2, key=k)
            ms = rng.uniform(8, 18)
            step = _sec(ms / 1000.0, b) / max(1, len(vc) - 1)
            for i, q in enumerate(vc):
                out.append((t + i * step, 0.4, q, fv * (0.8 if q == vc[-1] else 0.7)))
        return out
    if kind == 'fourths':
        ln = min(g - margin - (0.5 if g >= 1.5 else 0.0), 1.5)
        if ln < 0.5:
            return []
        a = g1 - margin - ln
        a = math.ceil(a * 4 - _EPS) / 4
        ln = g1 - margin - a
        top = min(top_lim, max(ref, nxt or ref) + rng.choice((2, 4, 7)))
        c = fourths(top, ln, b, chord=ch, key=k, voices=2, grid=rng.choice((0.25, 1.0 / 3.0)),
                    vel=(fv, fv * 0.78), seed=sd, at=a)
        return [x for x in c if x.pitch >= fl and x.start + x.dur <= g1 + 0.02]
    if kind == 'hands':
        ln = min(g - margin, 1.5)
        a = g1 - margin - ln
        a = math.ceil(a * 4 - _EPS) / 4
        ln = g1 - margin - a
        if ln < 0.5:
            return []
        lhr = (max(48, fl - 12), max(60, fl))
        c = alternating_hands(ch, ln, b, top=min(top_lim, max(ref, nxt or ref) + 3), lh_register=lhr,
                              pattern=rng.choice(('RL', 'RRL', 'RRLL')), vel=(fv * 1.02, fv * 0.8), seed=sd, at=a)
        return list(c)
    if kind == 'tremolo':
        ln = min(g - margin - 0.25, 2.0)
        if ln < 0.75:
            return []
        a = g0 + 0.25
        tops = [q for q in range(ref - 7, ref + 1) if q % 12 in _tones(ch)]
        if not tops:
            return []
        hi_ = max(tops)
        lo_ = [q for q in range(max(fl, hi_ - 12), hi_ - 4) if q % 12 in _tones(ch)][:2]
        if not lo_:
            return []
        c = tremolo(lo_, [hi_], ln, b, rate=rng.uniform(9, 11), swell='cresc', vel=fv, seed=sd, at=a)
        return list(c)
    if kind == 'repeated':
        ln = min(g - margin - 0.25, 1.5)
        if ln < 0.5:
            return []
        a = g1 - margin - ln
        tops = [q for q in range(ref - 5, ref + 3) if q % 12 in _tones(ch)]
        if not tops:
            return []
        hi_ = max(tops)
        dy = voicing(ch, hi_, 'thirds', floor=fl, key=k)
        c = repeated(dy, ln, b, rate=rng.uniform(6.5, 8.0), vel=fv, crescendo=0.5, seed=sd, at=a)
        return list(c)
    return []
