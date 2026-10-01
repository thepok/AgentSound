"""The riff player: a rock rhythm guitarist's riffs, written compactly and played with the section's energy - and the
double-tracked wall (two real takes, not a copy).

A rock part is not a strummed chord progression (guitarist.arrange does those): it is a RIFF - a figure on the low
strings (power chords, palm-muted chugs, an open-string pedal against moving notes, stops in unison with the drums)
that the band repeats, opens up in the chorus and pulls back in the verse. The same riff is played differently by
energy (riff(energy=...) or section=): a verse plays it palm-muted, single notes (quiet, tight), a pre-chorus as
power chords with the short notes chugged and the accents open, the chorus as big ringing power chords with the
octave on top. A riff is written as a line of steps on a grid:

    from agentsound import guitarist as gtr
    r = gtr.riff('E> . E G . A . G | E - - x D> - B A', bpm=116, section=verse)          # 8th grid
    gtr.double(r, (b.gtr_l, b.gtr_r), verse)          # two takes hard left / right: the wall
    kick = r.cell()                                  # 'x..x..x.' the riff's rhythm: drummer / bassist lock to it

Steps (space separated, '|' bar lines ignored): a note name (E, F#, Bb, or with octave: D3 - without an octave the
lowest such pitch on the low string: E2..D#3 in standard tuning, D2.. in drop D), '-' holds the step before, '.' a
rest (both hands damp), 'x' a dead-string scratch. Marks after a note: '>' accent, '!' let ring (open even in a
quiet verse), 'p' palm mute (forced), '^' a hit: struck hard and choked (the band's stop). kind= 'single' (one string),
'power' (root + 5th), 'power8' (+ the octave), 'octave'; default by energy (single < 0.5 <= power < 0.75 <= power8).

The vocabulary around it: pedal() writes an open-string pedal riff, hits() the stops in unison with the drums,
build_up() the pre-chorus chug build, double() plays any part as two (or more) separate performances: other round
robins (the tracks' own sampler seeds), its own timing that drifts a few ms around the beat (not a fixed offset), a
slight tuning drift per take (a slow 'instrument.pitchbend' lane, +-cents), other velocities - into the two
different guitars / amps of the band presets (gtr_l / gtr_r). Deterministic by seed.
"""

from __future__ import annotations

import math
import random
import re

from . import articulation as _art
from .guitarist import (Arrangement, Memory, SECTION_ENERGY, TUNINGS, _budget, _clip, _section_kind, _tri)
from .patterns import Clip, as_clip, beats, seed_int
from .theory import ComposeError, note

__all__ = ['riff', 'pedal', 'hits', 'build_up', 'double', 'cell', 'RIFF_KINDS', 'RIFF_LEVELS']

_EPS = 1e-6

RIFF_KINDS = {'single': (0,), 'power': (0, 7), 'power8': (0, 7, 12), 'octave': (0, 12)}
"""The grip of a riff note: semitones above its root, low string first."""

RIFF_LEVELS = {
    # energy below: (name, kind, palm rule, velocity range, strum ms for 3 strings)
    0.5: ('quiet', 'single', 'all', (68, 96), 6.0),
    0.75: ('drive', 'power', 'short', (82, 112), 8.0),
    1.01: ('open', 'power8', 'chugs', (94, 122), 10.0),
}
"""How a riff is played by energy: quiet (a verse: single notes, everything palm-muted but '!'), drive (a pre-chorus:
power chords, the short notes chugged, accents and long notes open), open (a chorus: power chords + octave ringing,
only repeated short notes and 'p' palm-muted)."""

_TOKEN = re.compile(r'^(?P<p>[A-G](?:#|b)?(?:-?\d)?)?(?P<m>[>!p^]*)$')
_PCS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def _num(x, what, lo=None, hi=None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        raise ComposeError(f"{what} = {x:g} is outside {lo:g}..{hi:g}")
    return float(x)


def _bpm(bpm) -> float:
    return _num(bpm, 'bpm', 20, 400)


def _sec(ms: float, bpm: float) -> float:
    return ms / 1000.0 * bpm / 60.0


def _low(tuning) -> int:
    if isinstance(tuning, str):
        if tuning not in TUNINGS:
            raise ComposeError(f"riff tuning must be one of {', '.join(TUNINGS)} or 6 pitches, got {tuning!r}")
        return note(TUNINGS[tuning][0])
    try:
        return note(list(tuning)[0])
    except (TypeError, IndexError):
        raise ComposeError(f"riff tuning must be a TUNINGS name or 6 pitches, got {tuning!r}") from None


def _resolve(tok: str, low: int) -> int:
    if tok[-1].isdigit():
        return note(tok)
    pc = (_PCS[tok[0]] + (1 if '#' in tok else -1 if tok.endswith('b') else 0)) % 12
    p = low + (pc - low) % 12
    return p


def parse(spec, *, tuning='standard') -> list:
    """A riff spec -> steps: [(kind, pitch, marks, hold_steps)] - kind 'note' | 'rest' | 'dead'; a note's hold counts
    the '-' steps after it."""
    if not isinstance(spec, str) or not spec.strip():
        raise ComposeError(f"riff spec must be a non-empty string of steps, got {spec!r}")
    low = _low(tuning)
    steps: list = []
    for tok in spec.replace('|', ' ').split():
        if tok == '-':
            if not steps:
                raise ComposeError(f"riff {spec!r}: '-' (hold) needs a step before it")
            steps[-1][3] += 1
            steps.append(['hold', None, '', 0])
            continue
        if tok == '.':
            steps.append(['rest', None, '', 0])
            continue
        if tok == 'x':
            steps.append(['dead', None, '', 0])
            continue
        m = _TOKEN.match(tok)
        if not m or not m.group('p'):
            raise ComposeError(f"riff {spec!r}: unknown step {tok!r}; steps: a note (E, F#, Bb, D3) with marks > ! p ^, "
                               f"'-' hold, '.' rest, 'x' dead scratch")
        steps.append(['note', _resolve(m.group('p'), low), m.group('m'), 0])
    # a hold after a hold belongs to the note before
    out, last = [], None
    for s in steps:
        if s[0] == 'hold':
            out.append(('hold', None, '', 0))
            continue
        out.append(s)
    for i, s in enumerate(out):
        if s[0] == 'note':
            k = i + 1
            while k < len(out) and out[k][0] == 'hold':
                k += 1
            out[i] = ('note', s[1], s[2], k - i - 1)
    return [tuple(s) for s in out]


def _level(e: float):
    for top in sorted(RIFF_LEVELS):
        if e < top:
            return RIFF_LEVELS[top]
    return RIFF_LEVELS[max(RIFF_LEVELS)]


def _energy(section, energy) -> float:
    if energy is not None:
        return _num(energy, 'riff energy', 0, 1)
    return SECTION_ENERGY[_section_kind(getattr(section, 'name', section))]


def _strum(notes, t, pitches, vel, bpm, ms, rng, *, up=False, dur=0.5, art=None, profile=None):
    """One stroke: the grip's strings low -> high (an upstroke high -> low, lighter), spread over ms."""
    order = list(pitches) if not up else list(reversed(pitches))
    n = len(order)
    for i, p in enumerate(order):
        off = _sec(ms * i / max(1, n - 1), bpm) if n > 1 else 0.0
        off *= 1.0 + 0.25 * _tri(rng)
        v = vel * (profile[i] if profile else (1.0 - 0.04 * i if not up else 0.9 - 0.05 * i))
        notes.append((t + off, max(0.03, dur - off), p, v, art))


def riff(spec, *, bpm, energy=None, section=None, kind=None, grid='1/8', tuning='standard', palm=None, vel=None,
         strum_ms=None, timing_ms: float = 4.0, seed=0, take=None, length=None, at=None, end=None, into=None,
         memory: Memory | None = None, fill_every: float = 4.0) -> Arrangement:
    """A riff (spec: steps on `grid`, see the module doc) played at the section's energy -> Arrangement (.clip,
    .play(track, at), .take(n): the same riff played again - another take for the double -, .cell(): its rhythm,
    .moves). energy= or section= (SECTION_ENERGY by name: verse 0.45 quiet, pre 0.62 drive, chorus 0.85 open) picks
    the grip (kind=), the palm muting (palm= True / False overrides; 'p' / '!' marks per note always win), the
    velocity range (vel=(lo, hi)) and the strum spread; length= (beats, or a Section's) loops the riff; end= the last
    beat(s): 'choke' (a stop), 'slide' (a power chord slid into the next downbeat), 'build' (a chug build over the
    last bar), 'ring' (the last chord rings) or None - with into= a bigger next section a fill is chosen (budgeted
    with memory=: one per fill_every bars). Downstrokes on the beat grid, upstrokes on the off 16ths; repeated short
    notes are chugs; human timing (timing_ms, seeded; take= new noise only)."""
    b = _bpm(bpm)
    g = beats(grid)
    if g <= 0:
        raise ComposeError("riff grid must be > 0")
    steps = parse(spec, tuning=tuning)
    e = _energy(section, energy)
    lvl_name, k_default, palm_rule, vrange, ms_default = _level(e)
    kind_ = kind or k_default
    if kind_ not in RIFF_KINDS:
        raise ComposeError(f"riff kind must be one of {', '.join(RIFF_KINDS)}, got {kind_!r}")
    lo, hi = (vel if vel is not None else vrange)
    lo, hi = _num(lo, 'riff vel', 1, 127), _num(hi, 'riff vel', 1, 127)
    ms = ms_default if strum_ms is None else _num(strum_ms, 'riff strum_ms', 0, 60)
    if length is None and hasattr(section, 'length') and not isinstance(section, str):
        length = float(section.length)
    L1 = len(steps) * g
    L = float(length) if length is not None else L1
    if L <= 0:
        raise ComposeError("riff length must be > 0 beats")
    if at is None and hasattr(section, 'start') and not isinstance(section, str):
        at = float(section.start)
    base = float(at) if isinstance(at, (int, float)) else (memory.clock if memory is not None else 0.0)
    if end not in (None, 'choke', 'slide', 'build', 'ring'):
        raise ComposeError(f"riff end must be 'choke', 'slide', 'build', 'ring' or None, got {end!r}")
    rng0 = random.Random(seed_int(seed))
    # the fill into the next section (decided once: every take plays it)
    fill = end
    if fill is None and into is not None:
        e2 = SECTION_ENERGY[_section_kind(getattr(into, 'name', into))]
        if e2 > e + 0.1:
            w = {'build': 1.0 if e < 0.75 else 0.4, 'slide': 1.0, 'choke': 0.8}
            x = rng0.random() * sum(w.values())
            for name, wt in w.items():
                x -= wt
                if x <= 0:
                    fill = name
                    break
    moves: list = [(0.0, L, 'technique', 'riff'), (0.0, L, 'pattern', f"{lvl_name} {kind_}")]
    fill_len = {'choke': 1.0, 'slide': 1.0, 'build': 4.0, 'ring': 0.0, None: 0.0}[fill]
    fill_len = min(fill_len, L)
    if fill in ('choke', 'slide', 'build') and memory is not None:
        cands = [dict(name=fill, cls='flash', t=L - fill_len, score=2.0, slot=('end',), what='fill')]
        _budget(cands, memory, base, 4.0, {'flash': fill_every})
        if not cands[0]['keep']:
            moves.append((L - fill_len, L, 'dropped', fill))
            fill, fill_len = None, 0.0
    # the steps, looped over the length
    n_steps = len(steps)
    events = []                       # (t, kind, pitch, marks, hold)
    t = 0.0
    i = 0
    while t < L - fill_len - _EPS:
        st = steps[i % n_steps]
        if st[0] != 'hold':
            events.append((t, st[0], st[1], st[2], st[3]))
        t += g
        i += 1
    onsets = [ev[0] for ev in events if ev[1] in ('note', 'dead')]
    rest_at = [ev[0] for ev in events if ev[1] == 'rest']
    grip = RIFF_KINDS[kind_]
    pitched = [ev for ev in events if ev[1] == 'note']

    def decide(idx_ev):
        """palm / ring / hit for a note event."""
        t0, _, p, marks, hold = idx_ev
        dur = (hold + 1) * g
        if '^' in marks:
            return 'hit'
        if '!' in marks:
            return 'ring'
        if 'p' in marks:
            return 'palm'
        if palm is True:
            return 'palm'
        if palm is False:
            return 'open'
        if palm_rule == 'all':
            return 'palm'
        if palm_rule == 'short':
            return 'palm' if dur < 0.75 - _EPS and '>' not in marks else 'open'
        # 'chugs': a short note followed by the same pitch (a repeated chug) stays muted
        nxt = next((x for x in pitched if x[0] > t0 + _EPS), None)
        return 'palm' if dur < 0.5 - _EPS and nxt is not None and nxt[2] == p and '>' not in marks else 'open'

    plan = [(ev, decide(ev) if ev[1] == 'note' else ev[1]) for ev in events]
    n_palm = sum(1 for _, d in plan if d == 'palm')
    n_hit = sum(1 for _, d in plan if d == 'hit')
    if n_palm:
        moves.append((0.0, L, 'technique', f"palm x{n_palm}"))
    if n_hit:
        moves.append((0.0, L, 'technique', f"hits x{n_hit}"))
    bpb = 4.0
    last_root = pitched[-1][2] if pitched else _low(tuning)

    def run(take_):
        rng = random.Random(seed_int(seed) * 7919 + (0 if take_ is None else 104729 * int(take_)))
        notes: list = []
        for (t0, kind_ev, p, marks, hold), how in plan:
            if kind_ev == 'rest':
                continue
            nxt_on = next((o for o in onsets if o > t0 + _EPS), L - fill_len)
            nxt_rest = next((r for r in rest_at if r > t0 + _EPS), None)
            jitter = _sec(timing_ms * _tri(rng), b)
            tt = max(0.0, t0 + jitter)
            beat_pos = t0 % 1.0
            up = g < 0.5 - _EPS and (abs(beat_pos - 0.25) < _EPS or abs(beat_pos - 0.75) < _EPS)
            w = 0.55
            if abs(t0 % bpb) < _EPS:
                w = 0.8
            elif beat_pos < _EPS:
                w = 0.68
            elif abs(beat_pos - 0.5) < _EPS:
                w = 0.5
            else:
                w = 0.4
            if '>' in marks or how == 'hit':
                w = 1.0
            v = (lo + (hi - lo) * w) * (1.0 + 0.04 * _tri(rng))
            if kind_ev == 'dead':
                notes.append((tt, _sec(60, b), last_root + 12, v * 0.55, _art._art_name('dead')))
                continue
            if how == 'hit':
                d = min(g, 0.25)
                _strum(notes, tt, [p + x for x in RIFF_KINDS['power8' if kind_ != 'single' else 'power']], v, b,
                       ms * 0.7, rng, dur=d)
                notes.append((tt + d, _sec(60, b), p + 12, v * 0.45, _art._art_name('dead')))
                continue
            dur = (hold + 1) * g
            if how == 'ring':
                end_t = nxt_rest if nxt_rest is not None else L - fill_len
                dur = max(dur, end_t - t0)
            else:
                dur = min(dur, nxt_on - t0)
                if nxt_rest is not None and nxt_rest < t0 + dur:
                    dur = nxt_rest - t0
            dur = max(0.05, dur - _sec(12, b))
            art = _art._art_name('palm') if how == 'palm' else None
            gp = list(grip)
            if how == 'palm' and len(gp) > 2:
                gp = gp[:2]                      # a chug takes the two low strings
            _strum(notes, tt, [p + x for x in gp], v * (0.96 if how == 'palm' else 1.0), b,
                   ms * (0.6 if how == 'palm' else 1.0), rng, up=up, dur=dur, art=art)
        # the fill
        if fill == 'choke':
            r0 = L - fill_len
            _strum(notes, r0, [last_root + x for x in RIFF_KINDS['power8']], hi, b, ms, rng, dur=0.5)
            notes.append((r0 + 0.5, _sec(60, b), last_root + 12, hi * 0.45, _art._art_name('dead')))
        elif fill == 'slide':
            r0 = L - fill_len
            # struck two frets low, slid up a whole step into the riff's first root on the next downbeat
            target = next((s[1] for s in steps if s[0] == 'note'), last_root)
            src = target - 2
            n_sl = 4
            for j in range(n_sl):
                pj = src + round(2 * j / (n_sl - 1))
                vj = hi * (1.0 if j == 0 else 0.4)
                _strum(notes, r0 + 0.5 + 0.12 * j, [pj + x for x in (0, 7)], vj, b, 4.0, rng, dur=0.14)
            _strum(notes, r0, [last_root + x for x in (0, 7)], (lo + hi) / 2, b, ms, rng, dur=0.45,
                   art=_art._art_name('palm'))
        elif fill == 'build':
            r0 = L - fill_len
            bu = build_up(last_root, fill_len, b, kind='power', vel=(lo, hi), seed=seed, take=take_, at=r0)
            notes.extend((n.start, n.dur, n.pitch, n.vel, _art.articulation_of(n)) for n in bu)
        elif fill == 'ring' and notes:
            # the last stroke rings to the end
            t_last = max(x[0] for x in notes)
            notes[:] = [x if x[0] < t_last - _sec(40, b) else (x[0], max(x[1], L - x[0]), x[2], x[3], None)
                        for x in notes]
        return notes

    notes = run(take)
    if fill:
        moves.append((L - fill_len, L, 'fill', fill))
    if memory is not None:
        if fill in ('choke', 'slide', 'build'):
            memory.events.append((base + L - fill_len, 'flash', fill))
        memory.clock = base + L
        memory.sections.append((getattr(section, 'name', section), e))

    def rerun(n):
        return Arrangement(_clip(run(n), L), {}, list(moves), energy=round(e, 3), technique='riff',
                           section=getattr(section, 'name', section), rerun=rerun)
    return Arrangement(_clip(notes, L), {}, moves, energy=round(e, 3), technique='riff',
                       section=getattr(section, 'name', section), rerun=rerun)


def pedal(moving, *, pedal_note: str = 'E', rhythm: str = 'PPM', bars: float = 2, grid='1/8', accent: bool = True) -> str:
    """An open-string pedal riff spec: the pedal (the open low string, palm-muted chugs 'P') against moving notes ('M':
    the next of `moving`, accented, ringing): pedal(['G', 'A', 'B', 'A'], rhythm='PPM') -> 'E E G> E E A> E E B> ...'.
    rhythm: P / M / . / - per grid step, repeated over `bars` (4 beats each). Play it with riff(spec, ...)."""
    if not moving:
        raise ComposeError("pedal() needs moving notes")
    if not rhythm or any(c not in 'PM.-' for c in rhythm):
        raise ComposeError(f"pedal rhythm: P (pedal), M (moving), '.', '-' per step, got {rhythm!r}")
    n = int(round(_num(bars, 'pedal bars', 0.25) * 4.0 / beats(grid)))
    out, k = [], 0
    for i in range(n):
        c = rhythm[i % len(rhythm)]
        if c == 'P':
            out.append(f"{pedal_note}p")
        elif c == 'M':
            out.append(f"{moving[k % len(moving)]}{'>' if accent else ''}")
            k += 1
        else:
            out.append(c)
    return ' '.join(out)


def hits(cell_, root, bpm, *, grid='1/16', kind: str = 'power8', vel=(100, 124), tuning='standard', ring_last=True,
         seed=0, at=0.0, length=None) -> Clip:
    """Stops in unison with the drums: power chords struck on the 'x' / 'X' steps of `cell_` (the same cell string
    the drummer plays: 'x..x..x...x.x...'), 'x' choked short (both hands damp - a dead scratch where it stops), 'X' an
    accented hit that rings to the next one, '.' nothing, '-' holds; root: a note name / pitch, or a list (one per
    hit). ring_last: the last hit rings to the end."""
    b = _bpm(bpm)
    g = beats(grid)
    if not isinstance(cell_, str) or not cell_ or any(c not in 'xX.-|' for c in cell_):
        raise ComposeError(f"hits cell must be a string of x X . - steps, got {cell_!r}")
    steps = [c for c in cell_ if c != '|']
    L = float(length) if length is not None else len(steps) * g
    roots = root if isinstance(root, (list, tuple)) else [root]
    low = _low(tuning)
    roots = [r if isinstance(r, int) else _resolve(r, low) if not str(r)[-1].isdigit() else note(r) for r in roots]
    on = [i for i, c in enumerate(steps) if c in 'xX']
    rng = random.Random(seed_int(seed))
    lo, hi = _vels(vel)
    notes: list = []
    for j, i in enumerate(on):
        t = i * g
        nxt = on[j + 1] * g if j + 1 < len(on) else L
        p = roots[j % len(roots)]
        acc = steps[i] == 'X'
        hold = 1
        while i + hold < len(steps) and steps[i + hold] == '-':
            hold += 1
        last = j == len(on) - 1
        if acc or (last and ring_last):
            d = max(g * hold, nxt - t - _sec(12, b))
            _strum(notes, t, [p + x for x in RIFF_KINDS[kind]], hi, b, 9.0, rng, dur=d)
        else:
            d = max(g * hold * 0.8, min(0.25, g * hold))
            _strum(notes, t, [p + x for x in RIFF_KINDS[kind]], (lo + hi) / 2 * (1 + 0.03 * _tri(rng)), b, 7.0, rng,
                   dur=d)
            notes.append((t + d, _sec(60, b), p + 12, lo * 0.45, _art._art_name('dead')))
    a = float(at)
    return _clip([(x[0] + a,) + tuple(x[1:]) for x in notes], a + L)


def _vels(vel):
    if isinstance(vel, (tuple, list)):
        return _num(vel[0], 'vel', 1, 127), _num(vel[1], 'vel', 1, 127)
    v = _num(vel, 'vel', 1, 127)
    return v, v


def build_up(root, dur, bpm, *, kind: str = 'power', vel=(70, 118), grid16_from: float = 0.5, open_last: bool = True,
             tuning='standard', seed=0, take=None, at=0.0) -> Clip:
    """The rock pre-chorus build: palm-muted chugs on `root` over `dur` beats - 8ths, then 16ths from grid16_from
    (a fraction of dur) - crescendo from vel[0] to vel[1], the palm lifting over the last beat (the chugs open up) and
    the last 8th an open accented chord (open_last) that rings into the next downbeat."""
    b = _bpm(bpm)
    D = _num(dur, 'build_up dur', 0.5)
    p = root if isinstance(root, int) else (note(root) if str(root)[-1].isdigit() else _resolve(root, _low(tuning)))
    lo, hi = _vels(vel)
    rng = random.Random(seed_int(seed) * 31 + (0 if take is None else 977 * int(take)))
    notes: list = []
    t = 0.0
    while t < D - _EPS:
        g = 0.25 if t >= D * grid16_from - _EPS and 0.25 * 60.0 / b >= 0.075 else 0.5
        x = t / D
        v = (lo + (hi - lo) * x) * (1.0 + 0.03 * _tri(rng)) * (1.06 if abs(t % 1.0) < _EPS else 1.0)
        last = t + g >= D - _EPS
        open_ = (open_last and last) or (t >= D - 1.0 and abs(t % 0.5) < _EPS and x > 0.9)
        art = None if open_ else _art._art_name('palm')
        tt = t + _sec(3.0 * _tri(rng), b)
        d = (D - t + 0.5) if (open_last and last) else g * 0.9
        _strum(notes, max(0.0, tt), [p + i for i in RIFF_KINDS[kind if not (open_last and last) else 'power8']],
               min(127.0, v), b, 6.0 if art else 9.0, rng, up=(g < 0.5 and abs(t % 0.5 - 0.25) < _EPS), dur=d, art=art)
        t += g
    a = float(at)
    return _clip([(x[0] + a,) + tuple(x[1:]) for x in notes], a + D)


def cell(part, grid='1/16', *, length=None) -> str:
    """The rhythm of a part as a cell string on `grid`: 'x' where a stroke (a chord's first note) starts, '.' else -
    the riff's rhythm for the drummer (drummer.DrumMotif.make(cell=...), riff_drums) and the bassist (kick=)."""
    c = part.clip if hasattr(part, 'clip') and not isinstance(part, Clip) else as_clip(part)
    g = beats(grid)
    L = float(length) if length is not None else c.length
    n = max(1, int(round(L / g)))
    out = ['.'] * n
    last = -1.0
    for x in sorted(c, key=lambda n_: n_.start):
        if _art.articulation_of(x) == 'dead':
            continue
        if x.start - last < _sec(25, 120) and last >= 0:     # strings of one stroke
            continue
        last = x.start
        k = int(round(x.start / g))
        if 0 <= k < n:
            out[k] = 'x'
    return ''.join(out)


def _drift(rng, a: float, b_: float, every: float, amp: float):
    """A smooth random curve: control values (+-amp) every `every` beats from a to b, cosine-interpolated."""
    n = max(2, int(math.ceil((b_ - a) / every)) + 2)
    vals = [amp * (rng.random() * 2.0 - 1.0) for _ in range(n)]

    def f(t):
        x = (t - a) / every
        i = max(0, min(n - 2, int(math.floor(x))))
        u = min(1.0, max(0.0, x - i))
        w = 0.5 - 0.5 * math.cos(math.pi * u)
        return vals[i] * (1 - w) + vals[i + 1] * w
    return f, vals


def double(part, tracks, at=0.0, *, drift_ms: float = 7.0, drift_every: float = 2.0, jitter_ms: float = 2.5,
           vel: float = 5.0, cents: float = 4.0, seed=0, tune=True) -> list:
    """Play `part` as separate PERFORMANCES on `tracks` (the double-tracked wall: (b.gtr_l, b.gtr_r); 3-4 tracks for
    a quad-tracked wall). An Arrangement with take() (riff(), guitarist.arrange()) is re-played per track
    (take 1, 2, ...: the same decisions, new timing / velocity noise); a Clip is re-performed. On top, each take has
    its own feel: a timing drift that wanders +-drift_ms around the beat (a smooth curve, a new value every
    drift_every beats - rushing and dragging, not a fixed offset), +-jitter_ms per stroke, +-vel velocity, and (tune)
    a slight tuning drift: a slow 'instrument.pitchbend' lane per track (+-cents, its own offset per take - two
    guitars are never tuned the same). The tracks' own sampler seeds pick other round robins; the band presets'
    gtr_l / gtr_r are two different guitars into two different amps / cabs. Returns [(track, clip)] (song beats)."""
    trs = [t for t in (tracks.values() if isinstance(tracks, dict) else tracks)]
    if len(trs) < 2:
        raise ComposeError("double() needs two or more tracks (the takes)")
    song = getattr(trs[0], '_song', None)
    a0 = song._at(at) if song is not None else float(at)
    bpm = float(getattr(song, 'tempo', 120.0)) if song is not None else 120.0
    out = []
    for k, tr in enumerate(trs):
        rng = random.Random(seed_int(seed) * 1009 + 7 * k + 1)
        if hasattr(part, 'take') and hasattr(part, 'clip'):
            try:
                c = part.take(k + 1).clip if k else part.clip
            except ComposeError:
                c = part.clip
        else:
            c = as_clip(part)
        L = c.length
        dr, _ = _drift(rng, 0.0, max(L, 1.0), drift_every, drift_ms)
        ns = []
        stroke_t, stroke_off = -1.0, 0.0
        for n in sorted(c, key=lambda n_: (n_.start, n_.pitch)):
            if n.start - stroke_t > _sec(30, bpm):         # a new stroke: its own jitter
                stroke_t = n.start
                stroke_off = _sec(dr(n.start) + jitter_ms * _tri(rng), bpm)
            s = max(0.0, n.start + stroke_off)
            v = max(1, min(127, round(n.vel + vel * _tri(rng))))
            ns.append(n._replace(start=s, vel=v))          # (a marked note keeps its articulation)
        clip = Clip._raw(ns, L)
        tr.play(clip, a0)
        if tune and cents > 0:
            off = cents * (0.6 if k % 2 == 0 else -0.6) * (0.7 + 0.6 * rng.random())
            f, _ = _drift(rng, 0.0, max(L, 1.0), 16.0, cents * 0.5)
            pts = []
            t = 0.0
            while t <= L + _EPS:
                pts.append((a0 + t, round((off + f(t)) / 100.0, 5), 'smooth'))
                t += 8.0
            tr.automate('instrument.pitchbend', pts)
        out.append((tr, clip.shift(a0) if a0 else clip))
    return out
