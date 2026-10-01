"""MIDI effects: transform ANY Clip, like Ableton's MIDI effects or a hardware arpeggiator.

Write a musical idea once, then transform it. Every function takes a Clip and returns a new Clip (the
input is never changed); each one is also a Clip method, so they chain:

    pad = prog.block(voices=3)                                        # held chords
    pad.arpeggiate('updown', rate='1/16', octaves=2, gate=0.6)        # arp over the held notes
    pad.arpeggiate('up', pattern='x.xx x.x_', accent=1.2)              # rhythm pattern ('_' ties)
    pad.strum(ms=25, bpm=s.tempo, direction='alternate')              # guitar strum
    lead.echo(times=3, delay='1/8.', decay=0.55)                      # MIDI delay
    lead.harmonize('3rd', key=s.key)                                  # diatonic thirds above
    bass.chordify('7th', key=s.key, voicing='spread')                 # notes -> diatonic 7th chords
    hats.ratchet(3, where='..x.', vel_decay=0.2)                      # rolls on every 3rd hit
    line.quantize('1/16', strength=0.8).scale_quantize(s.key).fold('A3', 'A5')
    beat.chance(0.85, seed=3).vel_random(8, seed=3)

Everything random takes an explicit seed (default 0): same seed, same notes. Times are beats; note values
('1/16', '1/8.', '1/8t') are accepted wherever a length is. Keys: a Key or a key string ('A minor').
"""

from __future__ import annotations

import math
import random

from .patterns import (_EPS, _HIT_LEVEL, Clip, Note, _arp_order, _cells, _pitch, _vel, ARP_MODES, beats as _beats,
                       seed_int)
from .theory import ComposeError, Key, _parse_quality, note

ARPEGGIATE_MODES = ARP_MODES + ('order', 'chord', 'pattern')
"""Modes of Clip.arpeggiate(): up down updown downup converge diverge pinky thumb random order chord pattern."""

_GROUP_TOL = 1.0 / 32.0   # notes starting this close together form one chord / onset (humanized chords too)
_SAME_TOL = 1e-3          # notes starting this close together on one pitch are duplicates


# ---------------------------------------------------------------------------------- helpers

def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        rng = (f"{lo:g}..{hi:g}" if lo is not None and hi is not None else
               f">= {lo:g}" if lo is not None else f"<= {hi:g}")
        raise ComposeError(f"{what} must be {rng}, got {x:g}")
    return float(x)


def _int(x, what: str, lo: int | None = None) -> int:
    if isinstance(x, bool) or not isinstance(x, int):
        raise ComposeError(f"{what} must be an int, got {x!r}")
    if lo is not None and x < lo:
        raise ComposeError(f"{what} must be >= {lo}, got {x}")
    return x


def _length(v, what: str) -> float:
    b = _beats(v)
    if b <= 0:
        raise ComposeError(f"{what} must be > 0 beats, got {v!r}")
    return b


def _key(key, what: str) -> Key:
    if key is None:
        raise ComposeError(f"{what} needs key= (e.g. key=s.key or key='A minor')")
    return Key(key)


def _groups(notes) -> list[list[Note]]:
    """Notes grouped by onset (starts within 1/32 beat of the group's first note, so humanized chords count
    as one): chords stay together."""
    out: list[list[Note]] = []
    for n in sorted(notes, key=lambda n: (n.start, n.pitch)):
        if out and n.start - out[-1][0].start <= _GROUP_TOL:
            out[-1].append(n)
        else:
            out.append([n])
    return out


def _dedupe(notes) -> list[Note]:
    """One note per (start, pitch): the longest (then loudest) wins - folding/snapping can create doubles."""
    best: dict[tuple, Note] = {}
    for n in notes:
        k = (round(n.start / _SAME_TOL), n.pitch)
        o = best.get(k)
        if o is None or (n.dur, n.vel) > (o.dur, o.vel):
            best[k] = n
    return list(best.values())


def _check_pitch(p: int, what: str) -> int:
    if not 0 <= p <= 127:
        raise ComposeError(f"{what}: pitch {p} is outside MIDI 0..127")
    return p


def _pitch_set(spec) -> set[int]:
    items = spec if isinstance(spec, (list, tuple, set, frozenset)) else [spec]
    return {_pitch(p) for p in items}


_SEL_CHARS = set('xX.-_123456789 |')


def _selector(where, n: int, what: str):
    """where= for ratchet(): None (all), a predicate, a per-onset pattern string ('x..x', digits = counts)
    or pitches ('hat', 38, ['snare', 'clap']). Returns f(note, onset_index) -> repeat count."""
    if where is None:
        return lambda x, i: n
    if callable(where):
        return lambda x, i: n if where(x) else 1
    if isinstance(where, str) and where.strip() and set(where) <= _SEL_CHARS:
        cells = [c for c in where if c not in ' |']
        if not cells:
            raise ComposeError(f"{what}: empty pattern {where!r}")

        def count(x, i):
            c = cells[i % len(cells)]
            return n if c in 'xX' else 1 if c in '.-_' else int(c)
        return count
    try:
        ps = _pitch_set(where)
    except ComposeError:
        raise ComposeError(f"{what}: where={where!r} must be None, a function note -> bool, a pattern like 'x..x' "
                           f"(per onset; digits = repeat count) or pitches ('hat', 42, ['snare', 'clap'])") from None
    return lambda x, i: n if x.pitch in ps else 1


# ------------------------------------------------------------------------------- arpeggiator

class _Held:
    """Sweep over the clip's notes: the notes held at each arp step t (in increasing t) are those sounding at
    t + tol, plus any that started since the previous step (short notes between two steps are never lost).
    When new notes arrive at a step, older notes released within the first half of that step are the tail of
    the previous chord (legato / overlapping pads) and don't count."""

    def __init__(self, notes, r: float, tol: float):
        self.src = sorted(notes, key=lambda n: (n.start, n.pitch))
        self.r, self.tol, self.ptr, self.active = r, tol, 0, []

    def at(self, t: float) -> list[Note]:
        s = t + self.tol
        while self.ptr < len(self.src) and self.src[self.ptr].start <= s + _EPS:
            self.active.append(self.src[self.ptr])
            self.ptr += 1
        prev = s - self.r + _EPS              # the previous step's sampling point
        # a note not held now can't be held at any later step either, so the active list stays small
        self.active = [n for n in self.active if n.start + n.dur > s + _EPS or n.start > prev]
        if any(n.start > prev for n in self.active):
            release = t + 0.5 * self.r
            self.active = [n for n in self.active if n.start > prev or n.start + n.dur > release + _EPS]
        return list(self.active)


def _rhythm(pattern) -> list[tuple[str, float]] | None:
    """Rhythm string -> per-step ('hit', level) / ('tie', 0) / ('rest', 0)."""
    if pattern is None or not isinstance(pattern, str):
        return None
    cells = _cells(pattern, 'arpeggiate pattern')
    if all(c.isdigit() for c in cells):
        raise ComposeError(f"arpeggiate pattern {pattern!r} has only digits, which a rhythm string reads as velocity "
                           f"levels: for a note order pass a list of indices, pattern=[{', '.join(cells)}]; for a "
                           f"rhythm with levels add a rest or hit ('7.9.', 'x.5.')")
    out = []
    for c in cells:
        if c == '_':
            out.append(('tie', 0.0))
        elif c in '.-':
            out.append(('rest', 0.0))
        else:
            out.append(('hit', (int(c) * 14 if c.isdigit() else _HIT_LEVEL[c]) / 100.0))
    return out


def arpeggiate(clip: Clip, mode: str = 'up', rate='1/16', octaves: int = 1, gate: float = 0.7, pattern=None,
               latch: bool = False, vel: float | None = None, accent=None, retrigger: bool = True, seed=0) -> Clip:
    """Arpeggiate the notes HELD in a clip, like a hardware arp: a clock ticks every `rate`; on every step the
    arp plays the next note of whatever is held at that moment. A chord region (block chords, a held pad,
    a bass note) is arpeggiated for exactly as long as it is held; chord changes are picked up on the next step.

    mode:   up down updown downup converge diverge pinky thumb random (seeded, no immediate repeats)
            order (the order the notes were played: onset, then pitch) chord (the whole held chord on every
            step: rhythmic stabs) pattern (pattern= is a list of indices).
    octaves: the held notes plus copies 1..octaves-1 octaves up.
    gate:   note length as a fraction of the step (0.7).
    pattern: a list of indices into the sorted (octave-extended) held notes, e.g. [0, 2, 1, 3, None]
            (None = rest; indices past the end / negative wrap by octaves) - implies mode='pattern';
            or a rhythm string over the clock: 'x.xx x_x.' (x hit, X accent, o ghost, 1-9 level, '.' rest,
            '_' tie = hold the previous note one more step). Rests don't advance the note order; the rhythm is
            locked to the clock (step k uses character k).
    latch:  keep arpeggiating the last held notes through gaps (until new notes are held).
    vel:    None = each held note's own velocity, or a fixed velocity 1..127.
    accent: a factor for steps on the beat (1.2), or a list of factors cycled per step ([1.2, 0.8, 1, 0.9]).
    retrigger: True restarts the note order whenever the held notes change (or are struck again);
            False keeps the step counter running across chord changes (a continuous pattern).
    The clip keeps its length; steps run from beat 0 while they start before the clip end."""
    r = _length(rate, 'arpeggiate rate')
    octaves = _int(octaves, 'arpeggiate octaves', 1)
    g = _num(gate, 'arpeggiate gate', 0.01, 4.0)
    rhythm = _rhythm(pattern)
    idx_pattern = None
    if pattern is not None and rhythm is None:
        if not isinstance(pattern, (list, tuple)) or not pattern:
            raise ComposeError(f"arpeggiate pattern must be a list of indices like [0, 2, 1, None] or a rhythm string "
                               f"like 'x.xx', got {pattern!r}")
        for i in pattern:
            if i is not None:
                _int(i, 'arpeggiate pattern index')
        idx_pattern = list(pattern)
        if mode not in ('up', 'pattern'):
            raise ComposeError(f"arpeggiate: an index pattern replaces the mode; drop mode={mode!r} or use mode='pattern'")
        mode = 'pattern'
    if mode not in ARPEGGIATE_MODES:
        raise ComposeError(f"unknown arpeggiate mode {mode!r}; use one of {', '.join(ARPEGGIATE_MODES)}")
    if mode == 'pattern' and idx_pattern is None:
        raise ComposeError("arpeggiate mode='pattern' needs pattern=[indices], e.g. pattern=[0, 2, 1, 3]")
    if vel is not None:
        _num(vel, 'arpeggiate vel', 1, 127)
    if accent is not None and not isinstance(accent, (list, tuple)):
        _num(accent, 'arpeggiate accent', 0, 4)
    if isinstance(accent, (list, tuple)):
        if not accent:
            raise ComposeError("arpeggiate accent list is empty")
        for a in accent:
            _num(a, 'arpeggiate accent factor', 0, 4)
    rng = random.Random(seed_int(seed))
    L = clip.length if clip.length > 0 else clip.end
    tol = min(0.25 * r, 1.0 / 32.0)       # a note starting up to this late (humanized chords) still counts
    sweep = _Held(clip, r, tol)
    n_steps = int(math.ceil(L / r - _EPS)) if L > 0 else 0
    out: list[Note] = []
    counter, prev_ident, latched, last_p = 0, None, [], None
    last_hits: list[tuple[int, int]] = []   # (index in out, steps held) of the previous step's notes
    for k in range(n_steps):
        t = k * r
        held = sweep.at(t)
        if held:
            latched = held
        elif latch:
            held = latched
        ident = tuple(sorted((round(n.start, 6), n.pitch) for n in held))
        if ident != prev_ident and held and (retrigger or prev_ident is None):
            counter = 0
        if held:
            prev_ident = ident
        cell = rhythm[k % len(rhythm)] if rhythm else ('hit', 1.0)
        if cell[0] == 'tie':
            if last_hits and held:
                grown = []
                for i, m in last_hits:      # m tied steps so far: hold through them, then gate the last one
                    out[i] = out[i]._replace(dur=max(m * r + r * g, 1e-3))
                    grown.append((i, m + 1))
                last_hits = grown
            continue
        last_hits = []
        if cell[0] == 'rest' or not held:
            continue
        vmap: dict[int, int] = {}
        for n in held:
            vmap[n.pitch] = max(vmap.get(n.pitch, 0), n.vel)
        base = sorted(vmap)
        if mode == 'order':
            base = []
            for n in sorted(held, key=lambda n: (n.start, n.pitch)):
                if n.pitch not in base:
                    base.append(n.pitch)
            ext = [p + 12 * o for o in range(octaves) for p in base]
        else:
            ext = sorted({p + 12 * o for o in range(octaves) for p in base})
        if mode == 'chord':
            ps = ext
        elif mode == 'pattern':
            idx = idx_pattern[counter % len(idx_pattern)]
            counter += 1
            if idx is None:
                continue
            o, i = divmod(idx, len(ext))
            ps = [ext[i] + 12 * o]
        elif mode == 'random':
            choices = [p for p in ext if p != last_p] or ext
            ps = [rng.choice(choices)]
        else:
            order = ext if mode == 'order' else _arp_order(ext, mode)
            ps = [order[counter % len(order)]]
            counter += 1
        factor = cell[1]
        if isinstance(accent, (list, tuple)):
            factor *= accent[k % len(accent)]
        elif accent is not None and abs(t - round(t)) < _EPS:
            factor *= accent
        for p in ps:
            if not 0 <= p <= 127:
                continue
            v0 = vel if vel is not None else _src_vel(vmap, p)
            out.append(Note(t, max(r * g, 1e-3), p, _vel(v0 * factor)))
            last_hits.append((len(out) - 1, 1))
        last_p = ps[-1]
    return Clip._raw(out, clip.length)


def _src_vel(vmap: dict[int, int], p: int) -> int:
    """Velocity of the held note behind an arp pitch (octave copies inherit it)."""
    if p in vmap:
        return vmap[p]
    for q in sorted(vmap):
        if (p - q) % 12 == 0:
            return vmap[q]
    return max(vmap.values())


# ------------------------------------------------------------------------------------- strum

STRUM_DIRECTIONS = ('down', 'up', 'alternate')


def strum(clip: Clip, ms: float = 30.0, direction: str = 'down', vel_decay: float = 0.0, *, beats=None,
          bpm: float = 120.0) -> Clip:
    """Strum every chord (notes starting together) like a guitar: each next string starts `ms` later
    (converted with `bpm`; or give beats=0.03 / '1/64' directly) and keeps its end, so the chord still
    releases together. direction: down (low string first), up (high first), alternate (down, up, ...).
    vel_decay: each later string is (1 - vel_decay) softer (0.1 = a lighter touch towards the end).
    A string never starts later than 3/4 of its own length. Single notes are unchanged."""
    if direction not in STRUM_DIRECTIONS:
        raise ComposeError(f"strum direction must be one of {', '.join(STRUM_DIRECTIONS)}, got {direction!r}")
    if beats is not None:
        step = _beats(beats)
    else:
        step = _num(ms, 'strum ms', 0, 2000) / 1000.0 * _num(bpm, 'strum bpm', 1, 1000) / 60.0
    dec = _num(vel_decay, 'strum vel_decay', -1, 0.99)
    out: list[Note] = []
    chord_i = 0
    for grp in _groups(clip):
        if len(grp) < 2:
            out.extend(grp)
            continue
        up = direction == 'up' or (direction == 'alternate' and chord_i % 2 == 1)
        chord_i += 1
        order = sorted(grp, key=lambda n: n.pitch, reverse=up)
        t0 = min(n.start for n in grp)        # a humanized chord strums from its first note
        for i, n in enumerate(order):
            off = min(max(t0 + i * step - n.start, 0.0), 0.75 * n.dur)
            out.append(n._replace(start=n.start + off, dur=n.dur - off, vel=_vel(n.vel * (1.0 - dec) ** i)))
    return Clip._raw(out, clip.length)


# ----------------------------------------------------------------------------------- ratchet

def ratchet(clip: Clip, n: int = 2, where=None, gate: float = 0.9, vel_decay: float = 0.0) -> Clip:
    """Split notes into n equal repeats inside their own length (rolls, trap hats, fills).
    where: None = every note; a function note -> bool; a pattern over the onsets (chords count once) like
    '...x' ('x' = n repeats, '.' = unchanged, digits 2-9 = that many repeats: '..3.4'); or pitches
    ('hat', ['snare', 'clap'], 42). gate = repeat length / slot; vel_decay: each repeat (1 - vel_decay) softer
    (negative = louder: a crescendo roll)."""
    n = _int(n, 'ratchet n', 1)
    g = _num(gate, 'ratchet gate', 0.01, 1.0)
    dec = _num(vel_decay, 'ratchet vel_decay', -1, 0.99)
    count = _selector(where, n, 'ratchet')
    out: list[Note] = []
    for oi, grp in enumerate(_groups(clip)):
        for x in grp:
            c = count(x, oi)
            if c <= 1:
                out.append(x)
                continue
            sub = x.dur / c
            out.extend(Note(x.start + k * sub, max(sub * g, 1e-3), x.pitch, _vel(x.vel * (1.0 - dec) ** k))
                       for k in range(c))
    return Clip._raw(out, clip.length)


# -------------------------------------------------------------------------------------- echo

def echo(clip: Clip, times: int = 3, delay='1/8.', decay: float = 0.6, transpose: int = 0, gate: float | None = None,
         key=None, wrap: bool = False) -> Clip:
    """MIDI delay: every note plus `times` repeats, `delay` apart, each `decay` times the previous velocity
    (repeats that would fall below velocity 1 are dropped). transpose: per repeat, in semitones - or in
    scale steps when key= is given (echo(transpose=2, key=s.key) climbs in diatonic thirds). gate: None keeps
    each note's length (at most the delay, so repeats of one pitch don't overlap), else repeat length =
    gate x delay. wrap=True folds repeats past the clip end back to its start (seamless loops);
    by default they ring past the end. A repeat that lands on a note of the same pitch at the same time
    merges with it (the louder one stays), so echoes never stack doubled voices."""
    times = _int(times, 'echo times', 0)
    d = _length(delay, 'echo delay')
    dec = _num(decay, 'echo decay', 0, 1)
    tr = _int(transpose, 'echo transpose')
    k_ = Key(key) if key is not None else None
    if gate is not None:
        _num(gate, 'echo gate', 0.01, 1.0)
    L = clip.length
    if wrap and L <= 0:
        raise ComposeError("echo wrap=True needs a clip with a length")
    out = list(clip)
    taken = {(round(x.start / _SAME_TOL), x.pitch): i for i, x in enumerate(out)}
    for x in clip:
        for k in range(1, times + 1):
            v = x.vel * dec ** k
            if v < 1.0:
                break
            p = x.pitch if not tr else (k_.transpose(x.pitch, k * tr) if k_ is not None else x.pitch + k * tr)
            if not 0 <= p <= 127:
                break
            start = x.start + k * d
            if wrap:
                start %= L
            dur = min(x.dur, d) if gate is None else d * gate
            rep = Note(start, max(dur, 1e-3), p, _vel(v))
            ident = (round(start / _SAME_TOL), p)
            if ident in taken:      # a repeat landing on a note of the same pitch: one note, the louder one
                j = taken[ident]
                if rep.vel > out[j].vel:
                    out[j] = rep
                continue
            taken[ident] = len(out)
            out.append(rep)
    return Clip._raw(out, L)


# --------------------------------------------------------------------------------- harmonize

_INTERVAL_STEPS = {'unison': 0, 'prime': 0, '1st': 0, '2nd': 1, 'second': 1, '3rd': 2, 'third': 2, '4th': 3,
                   'fourth': 3, '5th': 4, 'fifth': 4, '6th': 5, 'sixth': 5, '7th': 6, 'seventh': 6, 'octave': 7,
                   '8ve': 7, '8th': 7, '9th': 8, 'ninth': 8, '10th': 9, 'tenth': 9, '11th': 10, '12th': 11,
                   '13th': 12}


def _interval_steps(name) -> int:
    if not isinstance(name, str):
        raise ComposeError(f"harmonize interval {name!r}: use a name like '3rd', '-3rd' (below), '6th', 'octave', "
                           f"or steps=[2] (scale steps) / semitones=[12]")
    s = name.strip().lower()
    sign = 1
    if s.startswith(('-', '+')):
        sign, s = (-1 if s[0] == '-' else 1), s[1:].strip()
    for suffix in (' below', ' down'):
        if s.endswith(suffix):
            sign, s = -sign, s[:-len(suffix)].strip()
    for suffix in (' above', ' up'):
        if s.endswith(suffix):
            s = s[:-len(suffix)].strip()
    if s not in _INTERVAL_STEPS:
        raise ComposeError(f"unknown interval {name!r}; use one of 2nd 3rd 4th 5th 6th 7th octave 9th 10th "
                           f"(prefix '-' or suffix ' below' for below), or steps=/semitones=")
    return sign * _INTERVAL_STEPS[s]


def _as_list(x) -> list:
    return list(x) if isinstance(x, (list, tuple)) else [x]


def harmonize(clip: Clip, interval=None, *, key=None, steps=None, semitones=None, vel: float = 0.8,
              keep: bool = True, fit=None, strong: float = 1.0, fold=None) -> Clip:
    """Add parallel voices to every note (the original stays):
        harmonize('3rd', key=s.key)            diatonic third above (in A minor: A->C, C->E, E->G, G->B)
        harmonize(['3rd', '5th'], key=s.key)   diatonic triads on every note
        harmonize('-6th', key=s.key)           a sixth below ('6th below' too)
        harmonize(steps=[2, 4], key=s.key)     the same with scale steps (2 = a third)
        harmonize(semitones=[12])              chromatic / parallel: +12 octave, [7] fifths, [-5] ...
    Diatonic voices follow the key (chromatic notes keep their alteration). vel = velocity factor of the
    added voices. A voice that duplicates a note already sounding at that start is skipped.
    keep=False returns only the added voices (a harmony part for another track: gtr2.play(lead.harmonize('-3rd',
    key=k, keep=False, vel=0.94))). fit=prog makes the voices chord-tone aware: a voice note on a strong position
    (a multiple of `strong` beats) or at least `strong` long that is not a tone of the chord sounding there moves
    to the nearest chord tone in the voice's direction (below the line for a voice below). fold=(lo, hi) octave-folds
    the voices into a register."""
    given = [x is not None for x in (interval, steps, semitones)]
    if sum(given) != 1:
        raise ComposeError("harmonize needs exactly one of: an interval name ('3rd', ['3rd', '5th']), steps=[2] "
                           "(scale steps, with key=) or semitones=[12]")
    f = _num(vel, 'harmonize vel', 0, 4)
    if keep and fit is None and fold is None:
        return _harmonize_add(clip, interval, key, steps, semitones, f, keep=True)
    voices = _harmonize_add(clip, interval, key, steps, semitones, f, keep=False)
    if fit is not None:
        voices = _fit_voices(voices, clip, fit, key, _num(strong, 'harmonize strong', 0.01, 64))
    if fold is not None:
        if not isinstance(fold, (tuple, list)) or len(fold) != 2:
            raise ComposeError(f"harmonize fold must be (low, high), got {fold!r}")
        voices = globals()['fold'](voices, fold[0], fold[1])
    return Clip._raw(list(voices) + (list(clip) if keep else []), clip.length)


def _fit_voices(voices: Clip, line: Clip, prog, key, strong: float) -> Clip:
    from .theory import Progression
    p = prog if isinstance(prog, Progression) else Progression(prog, key=key)
    tops = {}
    for x in line:
        tops[round(x.start, 6)] = max(tops.get(round(x.start, 6), -1), x.pitch)
    out = []
    for x in voices:
        ch = p.at(x.start)
        pos = x.start / strong
        if ch is not None and x.pitch % 12 not in ch.pcs and (abs(pos - round(pos)) < 1e-6 or x.dur >= strong - 1e-6):
            below = x.pitch < tops.get(round(x.start, 6), 128)
            cands = [x.pitch + d for d in range(1, 7)] if not below else [x.pitch - d for d in range(1, 7)]
            q = next((c for c in cands if c % 12 in ch.pcs), None)
            if q is not None:
                x = x._replace(pitch=_check_pitch(q, f"harmonize fit of pitch {x.pitch}"))
        out.append(x)
    return Clip._raw(out, voices.length)


def _harmonize_add(clip: Clip, interval, key, steps, semitones, f, keep: bool = True) -> Clip:
    if semitones is not None:
        shifts = [_int(s, 'harmonize semitones') for s in _as_list(semitones)]
        move = lambda p, s: p + s  # noqa: E731
    else:
        k = _key(key, "harmonize with interval names / steps (diatonic)")
        shifts = ([_interval_steps(i) for i in _as_list(interval)] if interval is not None
                  else [_int(s, 'harmonize steps') for s in _as_list(steps)])
        move = lambda p, s: k.transpose(p, s)  # noqa: E731
    have = {(round(x.start / _SAME_TOL), x.pitch) for x in clip} if keep else set()
    out = list(clip) if keep else []
    for x in clip:
        for s in shifts:
            if s == 0:
                continue
            p = _check_pitch(move(x.pitch, s), f"harmonize of pitch {x.pitch}")
            ident = (round(x.start / _SAME_TOL), p)
            if ident in have:
                continue
            have.add(ident)
            out.append(x._replace(pitch=p, vel=_vel(x.vel * f)))
    return Clip._raw(out, clip.length)


# ---------------------------------------------------------------------------------- chordify

CHORD_SHAPES = ('triad', '7th', '9th', '6th', 'power', 'sus2', 'sus4', 'add9', 'open')
"""Named chordify shapes; any chord quality ('m7', 'maj7', 'm', 'dim', '7sus4') or semitone tuple works too."""

_DIATONIC_SHAPES = {'triad': (0, 2, 4), '7th': (0, 2, 4, 6), '9th': (0, 2, 4, 6, 8), '6th': (0, 2, 4, 5),
                    'sus2': (0, 1, 4), 'sus4': (0, 3, 4), 'add9': (0, 2, 4, 8), 'open': (0, 4, 9)}
_CHROMATIC_SHAPES = {'power': (0, 7, 12), 'sus2': (0, 2, 7), 'sus4': (0, 5, 7), 'add9': (0, 4, 7, 14),
                     'open': (0, 7, 16), 'major': (0, 4, 7), 'maj': (0, 4, 7), 'minor': (0, 3, 7), 'min': (0, 3, 7)}
CHORDIFY_VOICINGS = ('close', 'open', 'spread')


def _shape(shape, key) -> tuple[str, tuple[int, ...]]:
    """('steps' | 'semis', offsets)."""
    if isinstance(shape, (list, tuple)):
        if not shape:
            raise ComposeError("chordify shape tuple is empty")
        return 'semis', tuple(sorted({0, *(_int(s, 'chordify shape semitone') for s in shape)}))
    if not isinstance(shape, str):
        raise ComposeError(f"chordify shape must be a name ({', '.join(CHORD_SHAPES)}), a chord quality like 'm7' "
                           f"or a tuple of semitones, got {shape!r}")
    s = shape.strip()
    if s == 'power':
        return 'semis', _CHROMATIC_SHAPES['power']
    if s in _DIATONIC_SHAPES and key is not None:
        return 'steps', _DIATONIC_SHAPES[s]
    if s in _CHROMATIC_SHAPES:
        return 'semis', _CHROMATIC_SHAPES[s]
    if s in _DIATONIC_SHAPES:
        raise ComposeError(f"chordify shape {s!r} is diatonic: pass key= (e.g. key=s.key), or give a chord quality "
                           f"for parallel chords ('m7', 'maj7', 'm', '7')")
    try:
        return 'semis', _parse_quality(s)
    except ComposeError:
        raise ComposeError(f"unknown chordify shape {shape!r}; use {', '.join(CHORD_SHAPES)}, a chord quality "
                           f"('m7', 'maj9', 'dim', '7sus4') or a tuple of semitones (0, 3, 7)") from None


def _in_key_sus(k: Key, root: int, sus: str) -> list[int]:
    """A real sus chord (perfect fifth, major 2nd / perfect 4th) on `root`, in the key when possible: the asked
    shape if its tones are in the key, else the other sus shape (F in A minor: Fsus4 needs Bb -> Fsus2 F G C),
    else the chromatic asked shape (B in A minor has no perfect fifth in the key -> Bsus4 B E F#)."""
    shapes = {'sus2': (0, 2, 7), 'sus4': (0, 5, 7)}
    other = 'sus4' if sus == 'sus2' else 'sus2'
    for name in (sus, other):
        ps = [root + o for o in shapes[name]]
        if all(k.contains(p) for p in ps[1:]):
            return ps
    return [root + o for o in shapes[sus]]


def _revoice(ps: list[int], voicing: str) -> list[int]:
    ps = sorted(set(ps))
    if voicing == 'close' or len(ps) < 3:
        return ps
    if voicing == 'open':
        return sorted(p + (12 if i in (1, 3) else 0) for i, p in enumerate(ps))
    root = ps[0]
    rest = sorted(ps[1:], key=lambda p: (0 if (p - root) % 12 in (6, 7, 8) else 1, p))
    out, cur = [root], root
    for p in rest:
        cur = cur + 3 + ((p - (cur + 3)) % 12)
        out.append(cur)
    return sorted(out)


def chordify(clip: Clip, shape='triad', key=None, voicing: str = 'close', vel: float = 1.0) -> Clip:
    """Turn every note into a chord built on it (the note is the root, at the bottom).
    shape: triad 7th 9th 6th (diatonic: stacked scale thirds of key=; they need a key), add9 open
    (diatonic with key=, else chromatic), sus2 sus4 (always a true sus chord - perfect fifth, major 2nd /
    perfect 4th; with key= the other sus shape is used where the asked one leaves the key: F in A minor gives
    Fsus2), power (root + fifth + octave, always chromatic), any chord quality
    for parallel chords ('m7', 'maj7', 'm', 'dim', '7sus4' - deep-house stabs) or a semitone tuple (0, 3, 7, 10).
    voicing: close (stacked inside the octave), open (2nd and 4th voices up an octave), spread (fifth first,
    each tone at least a minor third above the last: wide pads). vel = velocity factor of the added tones."""
    if voicing not in CHORDIFY_VOICINGS:
        raise ComposeError(f"chordify voicing must be one of {', '.join(CHORDIFY_VOICINGS)}, got {voicing!r}")
    k = Key(key) if key is not None else None
    kind, offs = _shape(shape, k)
    f = _num(vel, 'chordify vel', 0, 4)
    sus = shape.strip() if isinstance(shape, str) and shape.strip() in ('sus2', 'sus4') else None
    out: list[Note] = []
    for x in clip:
        ps = [x.pitch + o for o in offs] if kind == 'semis' else [k.transpose(x.pitch, o) for o in offs]
        if sus and kind == 'steps':
            ps = _in_key_sus(k, x.pitch, sus)
        ps = _revoice(ps, voicing)
        for p in ps:
            _check_pitch(p, f"chordify of pitch {x.pitch}")
            out.append(x if p == x.pitch else x._replace(pitch=p, vel=_vel(x.vel * f)))
    return Clip._raw(_dedupe(out), clip.length)


# ---------------------------------------------------------------------------------- quantize

def _swing_shift(swing, g: float) -> float:
    a = _num(swing, 'quantize swing', 0, 80)
    if a == 0:
        return 0.0
    a = a / 100.0 if a > 1.0 else a
    if not 0.5 <= a <= 0.8:
        raise ComposeError(f"quantize swing must be 0 (off) or 0.5..0.8 like Clip.swing (0.58 subtle, 0.67 "
                           f"triplet; 50..80 % also accepted), got {swing}")
    return (a - 0.5) * 2.0 * g


def quantize(clip: Clip, grid='1/16', strength: float = 1.0, ends: bool = False, swing: float = 0.0) -> Clip:
    """Move note starts toward the nearest `grid` line; strength 1 = all the way, 0.5 = halfway (keeps some
    feel). ends=True also snaps note ends (at least one grid step after the start). swing (0 = straight, or
    0.5..0.8 like Clip.swing) delays every second grid line: quantize('1/16', swing=0.58)."""
    g = _length(grid, 'quantize grid')
    s = _num(strength, 'quantize strength', 0, 1)
    shift = _swing_shift(swing, g)

    def target(t: float) -> float:
        k = round(t / g)
        return k * g + (shift if k % 2 else 0.0)
    out = []
    for x in clip:
        ts = target(x.start)
        st = x.start + (ts - x.start) * s
        if ends:
            end = x.start + x.dur
            te = target(end)
            if te <= ts + _EPS:
                te = ts + g
            en = end + (te - end) * s
            out.append(x._replace(start=st, dur=max(en - st, 1e-3)))
        else:
            out.append(x._replace(start=st))
    return Clip._raw(out, clip.length)


_DIRECTIONS = {'nearest': 0, 'up': 1, 'down': -1}


def scale_quantize(clip: Clip, key, direction: str = 'nearest') -> Clip:
    """Snap every pitch into the key's scale: direction nearest (ties go down) | up | down.
    Two notes landing on the same pitch at the same time merge (the longer one stays)."""
    if direction not in _DIRECTIONS:
        raise ComposeError(f"scale_quantize direction must be nearest, up or down, got {direction!r}")
    k = _key(key, 'scale_quantize')
    d = _DIRECTIONS[direction]
    out = [x._replace(pitch=_check_pitch(k.snap(x.pitch, d), 'scale_quantize')) for x in clip]
    return Clip._raw(_dedupe(out), clip.length)


# ------------------------------------------------------------------------ selection / density

def chance(clip: Clip, p: float = 0.8, seed=0) -> Clip:
    """Keep each note with probability p (seeded: the same seed keeps the same notes)."""
    pr = _num(p, 'chance p', 0, 1)
    rng = random.Random(seed_int(seed))
    return Clip._raw([x for x in clip if rng.random() < pr], clip.length)


def thin(clip: Clip, every: int = 2, offset: int = 0) -> Clip:
    """Keep every n-th onset (chords count once and stay whole), starting with onset `offset`:
    thin(2) keeps the 1st, 3rd, 5th ...; thin(2, offset=1) the 2nd, 4th ..."""
    every = _int(every, 'thin every', 1)
    offset = _int(offset, 'thin offset', 0)
    return Clip._raw([x for i, grp in enumerate(_groups(clip)) if i % every == offset % every for x in grp],
                     clip.length)


# --------------------------------------------------------------------------------- register

def fold(clip: Clip, low, high) -> Clip:
    """Octave-fold every pitch into [low, high] (at least 11 semitones apart): notes above move down by
    octaves, notes below move up - keeps a line or arp in one register. Doubles that land on one pitch merge."""
    lo, hi = note(low), note(high)
    if hi - lo < 11:
        raise ComposeError(f"fold range {low!r}..{high!r} must span at least 11 semitones so every pitch class fits")
    out = []
    for x in clip:
        p = x.pitch
        if p > hi:
            p -= 12 * math.ceil((p - hi) / 12)
        if p < lo:
            p += 12 * math.ceil((lo - p) / 12)
        out.append(x._replace(pitch=p))
    return Clip._raw(_dedupe(out), clip.length)


def octave_double(clip: Clip, interval=12, vel: float = 0.8) -> Clip:
    """Add an octave copy of every note: interval +12 (up), -12 (sub octave), 24, or a list ([12, -12]).
    vel = velocity factor of the copies."""
    shifts = [_int(i, 'octave_double interval') for i in _as_list(interval)]
    for s in shifts:
        if s == 0 or s % 12:
            raise ComposeError(f"octave_double interval must be a non-zero multiple of 12 semitones (12, -12, 24), "
                               f"got {s}; use harmonize(semitones=[...]) for other intervals")
    f = _num(vel, 'octave_double vel', 0, 4)
    have = {(round(x.start / _SAME_TOL), x.pitch) for x in clip}
    out = list(clip)
    for x in clip:
        for s in shifts:
            p = _check_pitch(x.pitch + s, f"octave_double of pitch {x.pitch}")
            if (round(x.start / _SAME_TOL), p) not in have:
                out.append(x._replace(pitch=p, vel=_vel(x.vel * f)))
    return Clip._raw(out, clip.length)


# --------------------------------------------------------------------------------- velocity

def vel_random(clip: Clip, amount: float = 10, seed=0) -> Clip:
    """Uniform random velocity offsets in +-amount (seeded), clamped to 1..127.
    (Clip.humanize / vel_jitter use a softer triangular spread.)"""
    a = _num(amount, 'vel_random amount', 0, 127)
    rng = random.Random(seed_int(seed))
    return Clip._raw([x._replace(vel=_vel(x.vel + rng.uniform(-a, a))) for x in clip], clip.length)


def vel_pattern(clip: Clip, levels, grid=None) -> Clip:
    """Cycle a velocity pattern over the onsets (chords count once): factors like [1.2, 0.8, 1.0, 0.8], or -
    when any value is above 4 - absolute velocities like [120, 70, 96, 70]. grid='1/16' indexes the pattern
    by grid position instead (step = round(start / grid)), so accents stay locked to the beat."""
    if not isinstance(levels, (list, tuple)) or not levels:
        raise ComposeError(f"vel_pattern needs a non-empty list like [1.2, 0.8, 1, 0.8] or [120, 70, 96, 70], got {levels!r}")
    vals = [_num(v, 'vel_pattern level', 0, 127) for v in levels]
    absolute = any(v > 4 for v in vals)
    g = _length(grid, 'vel_pattern grid') if grid is not None else None
    out = []
    for i, grp in enumerate(_groups(clip)):
        for x in grp:
            j = int(round(x.start / g)) if g else i
            v = vals[j % len(vals)]
            out.append(x._replace(vel=_vel(v if absolute else x.vel * v)))
    return Clip._raw(out, clip.length)


# ----------------------------------------------------------------------------------- length

def staccato(clip: Clip, length='1/16') -> Clip:
    """Cap every note at `length` beats (short, detached notes); shorter notes stay as they are.
    For a proportional shortening use Clip.gate(0.5)."""
    m = _length(length, 'staccato length')
    return Clip._raw([x._replace(dur=min(x.dur, m)) for x in clip], clip.length)


# ------------------------------------------------------------------------------------ pitch

def retrograde(clip: Clip, rhythm: bool = True) -> Clip:
    """Play the clip backwards. rhythm=True (default) mirrors time (= Clip.reverse()); rhythm=False keeps the
    rhythm and reverses only the order of the pitches (onsets; a chord moves as a whole)."""
    if rhythm:
        return clip.reverse()
    groups = _groups(clip)
    pitch_sets = [sorted(x.pitch for x in grp) for grp in groups][::-1]
    out = []
    for grp, ps in zip(groups, pitch_sets):
        dur, vel = max(x.dur for x in grp), max(x.vel for x in grp)
        t = grp[0].start
        if len(grp) == len(ps):
            out.extend(x._replace(pitch=p) for x, p in zip(sorted(grp, key=lambda x: x.pitch), ps))
        else:
            out.extend(Note(t, dur, p, vel) for p in ps)
    return Clip._raw(out, clip.length)


def invert(clip: Clip, pivot=None, key=None) -> Clip:
    """Mirror the melody upside down around `pivot` (a pitch / note name; default the first note).
    With key= the inversion is diatonic (in scale steps: a step up becomes a step down inside the key);
    without it, chromatic (semitones)."""
    if not len(clip):
        return clip
    piv = clip[0].pitch if pivot is None else _pitch(pivot)
    out = []
    if key is None:
        for x in clip:
            out.append(x._replace(pitch=_check_pitch(2 * piv - x.pitch, 'invert')))
    else:
        k = Key(key)
        ps, _ = k.step_of(k.snap(piv))
        for x in clip:
            s, a = k.step_of(x.pitch)
            out.append(x._replace(pitch=_check_pitch(k.step(2 * ps - s) - a, 'invert')))
    return Clip._raw(out, clip.length)
