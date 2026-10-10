"""Feel: seeded timing/velocity humanization, swing, grooves, velocity curves.

All functions take a Clip and return a new Clip. Everything random is seeded, so the same seed
always gives the same result. Timing in milliseconds needs the tempo (bpm); tracks do that for
you: track.humanize(timing_ms=4, vel=6) and track.groove('laidback') are applied at compile time
with the song tempo (the local tempo where each note is, when the tempo moves: `bpm` may be a function of the
beat) and a per-track seed derived from the song seed.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .patterns import DRUMS, Clip, Note, _vel, beats, seed_int
from .theory import ComposeError

_EPS = 1e-6


def _rng(seed) -> random.Random:
    return random.Random(seed_int(seed))


def _tri(r: random.Random) -> float:
    """Triangular noise in [-1, 1], most values near 0 (sum of two uniforms)."""
    return r.random() + r.random() - 1.0


def _ms_to_beats(ms: float, bpm) -> float:
    return ms / 1000.0 * bpm / 60.0


def _local(bpm, beat: float) -> float:
    """The tempo at `beat`: bpm is a number, or a function of the beat (song.tempo_at when the tempo moves)."""
    return bpm(beat) if callable(bpm) else bpm


def jitter(clip: Clip, ms: float = 4.0, bpm: float = 120.0, seed=0) -> Clip:
    """Random timing offsets of at most +-ms (triangular: mostly small); bpm may be a function of the beat."""
    r = _rng(seed)
    out = [n._replace(start=n.start + _tri(r) * _ms_to_beats(ms, _local(bpm, n.start))) for n in clip]
    return Clip._raw(out, clip.length)


def vel_jitter(clip: Clip, amount: float = 6, seed=0) -> Clip:
    """Random velocity offsets of at most +-amount (triangular), clamped to 1..127."""
    r = _rng(seed)
    return Clip._raw([n._replace(vel=_vel(n.vel + _tri(r) * amount)) for n in clip], clip.length)


def humanize(clip: Clip, timing_ms: float = 4.0, vel: float = 6, bpm: float = 120.0, seed=0) -> Clip:
    """Timing jitter (+-timing_ms) and velocity jitter (+-vel), both seeded."""
    s = seed_int(seed)
    out = jitter(clip, timing_ms, bpm, s ^ 0x5A17) if timing_ms else clip
    return vel_jitter(out, vel, s ^ 0x7E1A) if vel else out


def swing(clip: Clip, amount: float = 0.58, grid='1/16') -> Clip:
    """Delay every second `grid` step. amount = share of the pair taken by the first note:
    0.5 straight, 0.54-0.6 subtle MPC-style, 0.67 triplet shuffle (percent 50..75 also accepted).
    Swung notes are shortened by the delay so they don't overlap the next step."""
    a = amount / 100.0 if amount > 1.0 else amount
    if not 0.5 <= a <= 0.8:
        raise ComposeError(f"swing amount must be 0.5..0.8 (or 50..80 %), got {amount}")
    g = beats(grid)
    shift = (a - 0.5) * 2.0 * g
    out = []
    for n in clip:
        pos = n.start / g
        k = round(pos)
        if abs(pos - k) < 1e-4 and k % 2 == 1:
            out.append(n._replace(start=n.start + shift, dur=max(n.dur - shift, n.dur * 0.25)))
        else:
            out.append(n)
    return Clip._raw(out, clip.length)


def crescendo(clip: Clip, start: float = 0.5, end: float = 1.0, curve: float = 1.0, span=None) -> Clip:
    """Scale velocities from factor `start` to factor `end` across the clip (or span=(from, to) beats).
    curve > 1 keeps it low longer then rises fast; < 1 rises early. Notes outside the span keep their level.
    A decrescendo is crescendo(clip, 1.0, 0.4)."""
    a, b = (0.0, clip.length) if span is None else (float(span[0]), float(span[1]))
    if b <= a:
        raise ComposeError(f"crescendo span must have end > start, got {(a, b)}")
    out = []
    for n in clip:
        if a - _EPS <= n.start <= b + _EPS:
            x = min(1.0, max(0.0, (n.start - a) / (b - a))) ** curve
            out.append(n._replace(vel=_vel(n.vel * (start + (end - start) * x))))
        else:
            out.append(n)
    return Clip._raw(out, clip.length)


def decrescendo(clip: Clip, start: float = 1.0, end: float = 0.4, curve: float = 1.0, span=None) -> Clip:
    return crescendo(clip, start, end, curve, span)


def accent(clip: Clip, every: float = 1.0, amount: float = 1.2, offset: float = 0.0) -> Clip:
    """Multiply velocity of notes starting on offset + k*every beats (e.g. every=4 accents bar downbeats)."""
    e = beats(every)
    out = []
    for n in clip:
        pos = (n.start - offset) / e
        out.append(n._replace(vel=_vel(n.vel * amount)) if abs(pos - round(pos)) < 1e-4 else n)
    return Clip._raw(out, clip.length)


@dataclass(frozen=True)
class Groove:
    """A reusable feel.

    swing/grid : swing amount (0.5 = straight) applied on that grid
    vel        : velocity factors per grid slot inside a beat, cycled (e.g. 16ths: (1, .75, .9, .75))
    late_ms    : shift of every note on non-drum tracks (+ = behind the beat, laid back)
    drum_ms    : per-drum shift in ms on drum tracks, e.g. {'snare': 9} (names or GM numbers)
    """
    name: str = 'custom'
    swing: float = 0.5
    grid: str | float = '1/16'
    vel: tuple = ()
    late_ms: float = 0.0
    drum_ms: dict = field(default_factory=dict)


GROOVES: dict[str, Groove] = {
    'straight': Groove('straight'),
    'tight': Groove('tight', vel=(1.0, 0.82, 0.92, 0.82)),
    'laidback': Groove('laidback', swing=0.52, vel=(1.0, 0.74, 0.9, 0.76), late_ms=4.0,
                       drum_ms={'snare': 9, 'clap': 9, 'rim': 6, 'open_hat': 3, 'tamb': 5}),
    'push': Groove('push', vel=(1.0, 0.8, 0.92, 0.8), late_ms=-3.0,
                   drum_ms={'hat': -4, 'pedal': -4, 'open_hat': -3, 'snare': -2}),
    'mpc': Groove('mpc', swing=0.56, vel=(1.0, 0.72, 0.88, 0.72)),
    'shuffle': Groove('shuffle', swing=0.64, vel=(1.0, 0.78, 0.9, 0.78)),
    'swing8': Groove('swing8', swing=0.62, grid='1/8', vel=(1.0, 0.82)),
}
GROOVES['synthwave'] = GROOVES['laidback']


def _groove(g) -> Groove:
    if isinstance(g, Groove):
        return g
    if isinstance(g, str) and g in GROOVES:
        return GROOVES[g]
    raise ComposeError(f"unknown groove {g!r}; use one of {', '.join(GROOVES)} or a Groove(...)")


# ------------------------------------------------------------------------------------ jazz feel

_SWING_CURVE = ((70.0, 0.66), (140.0, 0.61), (220.0, 0.555), (300.0, 0.53))


def swing_ratio(bpm: float) -> float:
    """Swing ratio for a jazz tempo - the share of each beat taken by the first of two swung 8ths (0.5 straight,
    0.667 triplet). It falls as the tempo rises: ballads (<= 70 BPM) 0.66, medium swing (~140) 0.61, up-tempo
    (~220) 0.555, 300 BPM 0.53; linear in between. Override it wherever a ratio= is taken."""
    b = _bpm(bpm)
    pts = _SWING_CURVE
    if b <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if b <= x1:
            return round(y0 + (y1 - y0) * (b - x0) / (x1 - x0), 4)
    return pts[-1][1]


def _bpm(bpm) -> float:
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not 20 <= bpm <= 400:
        raise ComposeError(f"bpm must be a number 20..400, got {bpm!r}")
    return float(bpm)


LAYBACK_MS: dict[str, tuple[float, float, float]] = {
    'piano': (22.0, 16.0, 10.0), 'piano_rh': (22.0, 16.0, 10.0), 'melody': (22.0, 16.0, 10.0),
    'solo': (20.0, 14.0, 8.0), 'comp': (10.0, 8.0, 5.0), 'piano_lh': (10.0, 8.0, 5.0),
    'bass': (-2.0, -3.0, -5.0), 'drums': (0.0, 0.0, 0.0), 'brushes': (0.0, 0.0, 0.0), 'ride': (-2.0, -3.0, -4.0),
    'sax': (35.0, 22.0, 12.0), 'horn': (35.0, 22.0, 12.0), 'tenor': (35.0, 22.0, 12.0), 'trumpet': (28.0, 18.0, 10.0),
}
"""Where each part sits against the beat, in ms (+ = behind / laid back, - = ahead), at ballad (70 BPM), medium
(140) and up (220) tempo: piano right hand 10-25 ms behind, comping less, bass on or a hair ahead, brushes on,
ride on top, saxophone 20-40 ms behind on ballads."""


def layback_ms(part: str, bpm: float) -> float:
    """Lay-back of a part (LAYBACK_MS) at a tempo, interpolated between ballad (70), medium (140) and up (220) BPM."""
    if part not in LAYBACK_MS:
        raise ComposeError(f"unknown part {part!r}; use one of {', '.join(LAYBACK_MS)} (or give late_ms= directly)")
    b = _bpm(bpm)
    ballad, medium, up = LAYBACK_MS[part]
    if b <= 70:
        return ballad
    if b <= 140:
        return round(ballad + (medium - ballad) * (b - 70) / 70, 2)
    if b <= 220:
        return round(medium + (up - medium) * (b - 140) / 80, 2)
    return up


def lay_back(clip: Clip, ms: float, bpm: float = 120.0) -> Clip:
    """Shift every note `ms` milliseconds later (negative = earlier, but never before the clip start)."""
    d = _ms_to_beats(float(ms), _bpm(bpm))
    return Clip._raw([n._replace(start=max(0.0, n.start + d)) for n in clip], clip.length)


def jazz_groove(part: str = 'piano', bpm: float = 140.0, ratio: float | None = None, late_ms: float | None = None,
                accent_24: float | None = None, beats_per_bar: float = 4.0) -> Groove:
    """A Groove for track.groove(): 8ths swung at swing_ratio(bpm) (or ratio=), the part's lay-back
    (layback_ms(part, bpm), or late_ms=) and accents on the backbeats (accent_24: 2 and 4, in 3/4 2 and 3; the bass
    gets 1.04 by default).
        piano.groove(jazz_groove('piano', s.tempo)); bass.groove(jazz_groove('bass', s.tempo))
    Applied at compile to the whole track: notes on off-beat 8ths move to the swung position (triplets and other
    off-grid notes stay), every note moves by the lay-back. Bossa / latin parts: ratio=0.5 (straight)."""
    r = swing_ratio(bpm) if ratio is None else ratio
    a = r / 100.0 if r > 1.0 else r
    if not 0.5 <= a <= 0.8:
        raise ComposeError(f"jazz_groove ratio must be 0.5..0.8, got {ratio}")
    late = layback_ms(part, bpm) if late_ms is None else float(late_ms)
    acc = (1.04 if part == 'bass' else None) if accent_24 is None else float(accent_24)
    vel: tuple = ()
    if acc and acc != 1.0:
        n = max(1, int(round(float(beats_per_bar))))        # 8th-note slots of one bar, accents on the backbeats
        back = (1, 2) if n == 3 else tuple(b for b in range(n) if b % 2 == 1)
        vel = tuple(acc if (k % 2 == 0 and k // 2 in back) else 1.0 for k in range(2 * n))
    return Groove(f'jazz-{part}', swing=a, grid='1/8', vel=vel, late_ms=late)


def backbeat(clip: Clip, amount: float = 1.08, beats_per_bar: float = 4.0) -> Clip:
    """Accent the notes on the backbeats - 2 and 4 in 4/4 (every other beat), 2 and 3 in a 3/4 jazz waltz."""
    bpb = float(beats_per_bar)
    waltz = abs(bpb - 3.0) < _EPS
    out = []
    for n in clip:
        pos = n.start % bpb
        on = abs(pos - round(pos)) < 1e-4
        k = int(round(pos)) % max(1, int(round(bpb)))
        hit = on and ((k in (1, 2)) if waltz else k % 2 == 1)
        out.append(n._replace(vel=_vel(n.vel * amount)) if hit else n)
    return Clip._raw(out, clip.length)


def phrases(clip: Clip, gap=0.5) -> list[list[Note]]:
    """The clip's notes split into phrases: a new phrase starts after a rest of at least `gap` beats (from the end
    of everything sounding to the next onset)."""
    g = beats(gap)
    out: list[list[Note]] = []
    end = None
    for n in sorted(clip, key=lambda n: (n.start, n.pitch)):
        if end is None or n.start - end >= g - _EPS:
            out.append([n])
            end = n.start + n.dur
        else:
            out[-1].append(n)
            end = max(end, n.start + n.dur)
    return out


def phrase_dynamics(clip: Clip, gap='1/8', arch: float = 0.12, peak: float = 1.06, end: float = 0.9,
                    offbeat: float = 1.0, ghost: float | None = None) -> Clip:
    """Shape velocities phrase by phrase (phrases split at rests >= gap): an arch over each phrase (+-arch/2 around
    the written level: softer at the ends, fuller in the middle), the phrase's highest note x peak, a short last note
    x end (the release of a sung line; a long last note keeps its level), notes on off-beat 8ths x offbeat (1.05..1.1
    = bebop accents on the upbeats) and, with ghost=0.6..0.8, 8th notes lower than both neighbours ghosted (runs)."""
    out: list[Note] = []
    for ph in phrases(clip, gap):
        ph.sort(key=lambda n: (n.start, n.pitch))
        t0, t1 = ph[0].start, ph[-1].start
        top = max(n.pitch for n in ph)
        for i, n in enumerate(ph):
            x = 0.5 if t1 - t0 < _EPS else (n.start - t0) / (t1 - t0)
            f = 1.0 + arch * (math.sin(math.pi * x) - 0.5)
            if n.pitch == top and len(ph) > 1:
                f *= peak
            if i == len(ph) - 1 and len(ph) > 1 and n.dur < 1.0 - _EPS:
                f *= end
            pos = n.start * 2.0
            if offbeat != 1.0 and abs(pos - round(pos)) < 1e-4 and int(round(pos)) % 2 == 1:
                f *= offbeat
            if ghost is not None and 0 < i < len(ph) - 1 and n.dur <= 0.5 + _EPS:
                a, b = ph[i - 1], ph[i + 1]
                if n.pitch < a.pitch and n.pitch < b.pitch and b.start - a.start <= 1.2:
                    f *= ghost
            out.append(n._replace(vel=_vel(n.vel * f)))
    return Clip._raw(out, clip.length)


def touch(clip: Clip, lo: float = 60, hi: float = 108, *, gap='1/4', start: float = 0.4, end: float = 0.3,
          pitch: float = 0.8, sync: float = 1.1, passing: float = 0.9, grace: float = 0.62, last: float = 0.86,
          inner: float = 0.86, leap: float = 1.06, step: float = 15.0, jitter: float = 2.0,
          pickup: float = 0.88, levels=None) -> Clip:
    """A pianist's (or singer's) touch on a melody: velocities written from the line instead of one flat level.
    phrase_dynamics() shades a written level by a few percent (about 1 dB); touch() sets the level itself, so a
    melody gets the 8-12 dB of note-to-note contrast a player gives it (user feedback 2026-09-30: a lead with every
    note at one velocity "sounds equally loud", even when the level changes between sections).

    Per phrase (split at rests >= gap): the phrase rises to its goal - its highest note (the longest of equal ones)
    - from lo + start x (hi - lo) and relaxes after it to lo + end x (hi - lo) (a cosine arc in time). The clip's
    highest note is the summit and gets hi; a phrase that peaks lower peaks softer (1 velocity per semitone below
    the summit, at least half-way up; a two-note pickup phrase half-way). On top: `pitch` velocity per semitone
    above / below the phrase's mean (higher notes sing out), syncopations - an off-beat 8th held over the beat or
    followed by a rest - x sync, leap targets (a 4th+ from the note before) and contour tops x leap, short passing
    notes (a step between two neighbours) and low neighbours (under both) x passing - on or off the beat alike: the
    line's dynamics follow its contour and its phrase, never the beat (blind test round 3: on-beat accents of
    +7..+14 read as a machine) -, grace notes (<= 0.15 beat) x grace of the note they lead into, a phrase's short
    pickup (its first note, an 8th or less before the next) at least x pickup of that note, a short last note
    x last (the release), and notes sounding together (octaves, a chord under the melody) x inner below the top one
    (voice the top); neighbouring notes of a line (half a beat apart or closer) differ by at most `step` (a ghost or
    grace note or the phrase goal excepted), every note +-`jitter` (seeded by its place: a hand is never perfectly
    even); nothing above hi + 3. levels: [(beat, shift)] - each phrase moved up / down by the shift in force at its
    first note (a step function from the clip's start: the phrase-to-phrase dynamics a player gives a tune - a quiet
    phrase after a busy one, the plan's arc; endless r6: one level phrase after phrase read as "a monotone line").
    Section levels: soft head lo 50..60 / hi 90..100, a climax lo 75..85 / hi 115..122 (the Salamander's top layers
    start at 105 / 113 / 121). Apply it before octave_double / block_chords (they scale the added voices from the
    melody's velocity)."""
    lo, hi = _num_range(lo, 'touch lo'), _num_range(hi, 'touch hi')
    if hi < lo:
        raise ComposeError(f"touch hi ({hi:g}) must be >= lo ({lo:g})")
    for x, what in ((start, 'start'), (end, 'end')):
        if not 0.0 <= x <= 1.0:
            raise ComposeError(f"touch {what} must be 0..1, got {x!r}")
    for x, what in ((sync, 'sync'), (passing, 'passing'), (grace, 'grace'), (last, 'last'), (inner, 'inner'),
                    (pickup, 'pickup')):
        if not 0.1 <= x <= 2.0:
            raise ComposeError(f"touch {what} must be 0.1..2, got {x!r}")
    if not 0.0 <= pitch <= 5.0:
        raise ComposeError(f"touch pitch (velocity per semitone) must be 0..5, got {pitch!r}")
    if not 0.5 <= leap <= 2.0:
        raise ComposeError(f"touch leap must be 0.5..2, got {leap!r}")
    if not 0.0 <= step <= 127.0 or not 0.0 <= jitter <= 10.0:
        raise ComposeError(f"touch step must be 0..127 (0 = no cap) and jitter 0..10, got {step!r} / {jitter!r}")
    steps = sorted((float(t), float(v)) for t, v in (levels or ()))
    if any(not (math.isfinite(t) and math.isfinite(v) and -40 <= v <= 40) for t, v in steps):
        raise ComposeError(f"touch levels must be [(beat, shift -40..40)], got {levels!r}")
    out: list[Note] = []
    span = hi - lo
    top_all = max((n.pitch for n in clip), default=0)
    for ph in phrases(clip, gap):
        ph.sort(key=lambda n: (n.start, -n.pitch))
        shift = next((v for t, v in reversed(steps) if t <= ph[0].start + _EPS), 0.0)
        cap = min(127.0, hi + 3.0 + max(0.0, shift))
        # the line = the top note of every onset; notes sounding with it are inner voices
        tops: list[Note] = []
        for n in ph:
            if tops and abs(n.start - tops[-1].start) < 0.02:
                continue
            tops.append(n)
        mains = [n for n in tops if n.dur > 0.15 + _EPS] or tops
        goal = max(mains, key=lambda n: (n.pitch, n.dur, -n.start))
        t0, t1, tg = mains[0].start, mains[-1].start, goal.start
        mean_p = sum(n.pitch for n in mains) / len(mains)
        # the clip's summit gets hi; a phrase that peaks lower peaks softer (1 velocity per semitone, at least
        # half-way up), a two-note pickup phrase only half-way
        g_hi = max(lo + 0.5 * span, hi - (top_all - goal.pitch))
        if len(mains) <= 2 and sum(n.dur for n in mains) <= 1.0 + _EPS:
            g_hi = lo + 0.5 * span
        g_span = g_hi - lo
        level: dict[int, float] = {}
        ghost: set = set()
        for i, n in enumerate(tops):
            if n.start <= tg:
                x = 1.0 if tg - t0 < _EPS else (n.start - t0) / (tg - t0)
                a = start + (1.0 - start) * (0.5 - 0.5 * math.cos(math.pi * max(0.0, x)))
            else:
                x = 1.0 if t1 - tg < _EPS else (n.start - tg) / (t1 - tg)
                a = 1.0 - (1.0 - end) * (0.5 - 0.5 * math.cos(math.pi * min(1.0, x)))
            v = lo + g_span * a + (pitch * (n.pitch - mean_p) if n is not goal else 0.0)
            pos = n.start / 0.5
            off = abs(pos - round(pos)) < 1e-3 and int(round(pos)) % 2 == 1
            nxt = tops[i + 1] if i + 1 < len(tops) else None
            rest_after = nxt is None or nxt.start - (n.start + n.dur) >= 0.5 - _EPS
            if n is not goal and off and (n.dur >= 0.75 - _EPS or (rest_after and nxt is not None)):
                v *= sync                                    # a syncopation: tied over the beat / an upbeat that stops
            elif 0 < i < len(tops) - 1 and n.dur <= 0.5 + _EPS:
                a_, b_ = tops[i - 1].pitch, tops[i + 1].pitch
                passing_ = min(a_, b_) <= n.pitch <= max(a_, b_) and abs(n.pitch - a_) <= 2 and abs(n.pitch - b_) <= 2
                if passing_ or n.pitch < min(a_, b_):
                    v *= passing
                    if not passing_:
                        ghost.add(id(n))                 # a low neighbour: a deliberate ghost
                elif abs(n.pitch - a_) >= 5 or n.pitch > max(a_, b_):
                    v *= leap                            # a leap target, a turn at the top of the contour
            elif i and n is not goal and abs(n.pitch - tops[i - 1].pitch) >= 5:
                v *= leap
            if i == len(tops) - 1 and len(tops) > 1 and n.dur < 1.0 - _EPS and n is not goal:
                v *= last
            if jitter and n is not goal:                 # seeded by the note's place: deterministic, never even
                h = (int(round(n.start * 960)) * 7919 + n.pitch * 104729) % 1000 / 999.0
                v += jitter * (2.0 * h - 1.0)
            level[id(n)] = min(v + shift, cap)
        # grace notes lean on the note they lead into; so does a phrase's pickup (a short first note right before the
        # next one: blind round 5 - a soft 8th pickup and a loud downbeat read as an accent on the beat)
        for i, n in enumerate(tops):
            if n.dur <= 0.15 + _EPS and i + 1 < len(tops):
                level[id(n)] = level[id(tops[i + 1])] * grace
                ghost.add(id(n))
            elif i == 0 and len(tops) > 2 and n.dur <= 0.5 + _EPS and tops[1].start - n.start <= 0.5 + _EPS:
                level[id(n)] = max(level[id(n)], level[id(tops[1])] * pickup)
        # a line moves in steps: neighbours (half a beat apart or closer) at most `step` apart, a ghost excepted
        if step:
            ref = None                                   # the last note that is not a ghost (a dip comes back)
            for a_, b_ in zip(tops, tops[1:]):
                if id(a_) not in ghost:
                    ref = level[id(a_)]
                if b_.start - a_.start > 0.5 + _EPS:
                    ref = None
                elif ref is not None and id(b_) not in ghost and b_ is not goal:   # the goal may stand out
                    level[id(b_)] = min(ref + step, max(ref - step, level[id(b_)]))
        top_at = {round(n.start, 3): level[id(n)] for n in tops}
        for n in ph:
            if id(n) in level:
                out.append(n._replace(vel=_vel(level[id(n)])))
            else:
                ref = top_at.get(round(n.start, 3))
                if ref is None:
                    ref = min(tops, key=lambda m: abs(m.start - n.start))
                    ref = level[id(ref)]
                out.append(n._replace(vel=_vel(ref * inner)))
    return Clip._raw(out, clip.length)


BASS_ACCENTS = {
    '1-3': (1.0, 0.84, 0.93, 0.86),     # a two-feel / straight-8th line: the root on 1 leads, 3 answers
    '2-4': (0.95, 1.0, 0.9, 0.97),      # a swinging walk: feathered 2 and 4 (with the hi-hat), 1 still lands
    'even': (0.97, 0.94, 0.95, 0.94),   # a pedal / ballad line: hardly any beat accent
}
"""Beat weights (beats 1..4 of a 4/4 bar; 3/4 uses the first three) for bass_touch(accent=...)."""


def bass_touch(clip: Clip, lo: float = 62, hi: float = 100, *, accent: str = '1-3', phrase: float = 16.0,
               peak: float = 0.6, offbeat: float = 0.82, ghost: float = 0.55, approach: float = 0.84,
               anticipation: float = 1.1, pitch: float = 0.35, beats_per_bar: float = 4.0, jitter: float = 0.03,
               seed=0) -> Clip:
    """A bassist's touch: velocities written from the line instead of one level (a bass whose every note is
    equally loud sounds programmed; the dynamics ear reports it as flat_dynamics).
    Per `phrase` beats (16 = 4 bars) the line breathes: from lo at the phrase start it swells to hi at `peak`
    (0..1 of the phrase) and relaxes again - a cosine arc; on top, per note:
      beat weights  BASS_ACCENTS[accent]: '1-3' two-feel / straight 8ths (1 strong, 3 answers), '2-4' a swinging
                    walk (feathered 2 and 4), 'even' (pedal points, ballads)
      offbeat 8ths  x offbeat (the & notes of a push / drive are lighter than the beat notes)
      ghosts        short notes (<= 1/3 beat: skip notes, dead-note pickups) x ghost of the soft end of the arc
      approaches    a note leading into the next bar line by a half / whole step (chromatic or scale approach
                    into the next chord) x approach
      anticipations an off-beat note held over the next bar line (the next chord pushed an 8th early) x
                    anticipation - an accent, not a ghost
      register      `pitch` velocity per semitone above / below the phrase's mean (a line that climbs grows)
    plus a seeded +-jitter. Nothing goes above hi + 8. With a velocity-responsive bass (sampled/upright_bass
    follows (v/127)^2) lo 62 / hi 100 is ~8 dB from a phrase start to its peak: heads lo 56..64 / hi 88..96,
    solos and climaxes lo 70 / hi 110. Apply it to a finished line (after merging ties, before the feel)."""
    lo, hi = _num_range(lo, 'bass_touch lo'), _num_range(hi, 'bass_touch hi')
    if hi < lo:
        raise ComposeError(f"bass_touch hi ({hi:g}) must be >= lo ({lo:g})")
    if accent not in BASS_ACCENTS:
        raise ComposeError(f"bass_touch accent must be one of {', '.join(BASS_ACCENTS)}, got {accent!r}")
    for x, what in ((offbeat, 'offbeat'), (ghost, 'ghost'), (approach, 'approach'), (anticipation, 'anticipation')):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0.1 <= x <= 2.0:
            raise ComposeError(f"bass_touch {what} must be 0.1..2, got {x!r}")
    for x, what in ((phrase, 'phrase'), (beats_per_bar, 'beats_per_bar')):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 < x <= 256:
            raise ComposeError(f"bass_touch {what} must be > 0 beats, got {x!r}")
    if not 0.0 <= peak <= 1.0:
        raise ComposeError(f"bass_touch peak must be 0..1, got {peak!r}")
    if not 0.0 <= pitch <= 3.0:
        raise ComposeError(f"bass_touch pitch (velocity per semitone) must be 0..3, got {pitch!r}")
    if not 0.0 <= jitter <= 0.2:
        raise ComposeError(f"bass_touch jitter must be 0..0.2, got {jitter!r}")
    bpb = float(beats_per_bar)
    n_beats = max(1, min(4, int(round(bpb))))
    weights = BASS_ACCENTS[accent]
    rng = _rng(seed)
    ns = sorted(clip, key=lambda n: (n.start, n.pitch))

    def window(n):
        return int(math.floor(n.start / phrase + _EPS))
    by_win: dict[int, list[int]] = {}
    for n in ns:
        by_win.setdefault(window(n), []).append(n.pitch)
    means = {k: sum(ps) / len(ps) for k, ps in by_win.items()}
    cap = min(127.0, hi + 8.0)
    out: list[Note] = []
    for i, n in enumerate(ns):
        k = window(n)
        x = min(1.0, max(0.0, (n.start - k * phrase) / phrase))
        if x <= peak:
            a = 1.0 if peak < _EPS else 0.5 - 0.5 * math.cos(math.pi * x / peak)
        else:
            a = 0.5 + 0.5 * math.cos(math.pi * (x - peak) / (1.0 - peak))
        v = lo + (hi - lo) * a
        pos = n.start % bpb
        bar_line = (math.floor(n.start / bpb + _EPS) + 1) * bpb          # the next bar line
        if abs(pos - round(pos)) < 0.02:
            beat = int(round(pos)) % max(1, int(round(bpb)))
            v *= weights[beat] if beat < n_beats else weights[-1]
        elif n.dur <= 1.0 / 3.0 + _EPS:
            v = ghost * (lo + 0.35 * (v - lo))                           # ghosts stay ghosts at the peak
        elif bar_line - n.start <= 0.5 + _EPS and n.start + n.dur > bar_line + 0.05:
            v *= anticipation                                             # pushed over the bar line
        else:
            v *= offbeat
        nxt = ns[i + 1] if i + 1 < len(ns) else None
        if (nxt is not None and n.dur > 1.0 / 3.0 + _EPS and abs(nxt.start - bar_line) < 0.05
                and 1 <= abs(nxt.pitch - n.pitch) <= 2 and bar_line - n.start <= 1.0 + _EPS):
            v *= approach
        v += pitch * (n.pitch - means[k])
        v *= 1.0 + jitter * (2.0 * rng.random() - 1.0)
        out.append(n._replace(vel=_vel(min(cap, v))))
    return Clip._raw(out, clip.length)


def _num_range(x, what: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 1 <= x <= 127:
        raise ComposeError(f"{what} must be a velocity 1..127, got {x!r}")
    return float(x)


def groove(clip: Clip, g, bpm: float = 120.0, drums: bool = False) -> Clip:
    """Apply a groove template (name from GROOVES or a Groove). drums=True uses the per-drum offsets
    (snare late etc.) instead of the whole-part late_ms shift. bpm may be a function of the beat. The swing moves a
    rolled chord / a crushed grace note as a whole: notes up to 40 ms before a swung grid line that has a note on it
    move with it."""
    return Clip._raw(_grooved(clip, g, bpm, drums), clip.length)


def _grooved(clip: Clip, g, bpm, drums: bool) -> list[Note]:
    """groove()'s notes in the clip's order (note i of the result is note i of the clip moved)."""
    gr = _groove(g)
    gb = beats(gr.grid)
    a = gr.swing / 100.0 if gr.swing > 1.0 else gr.swing
    if not 0.5 <= a <= 0.8:
        raise ComposeError(f"groove {gr.name!r}: swing must be 0.5..0.8, got {gr.swing}")
    shift = (a - 0.5) * 2.0 * gb
    drum_ms = {}
    for k, ms in gr.drum_ms.items():
        p = DRUMS[k] if isinstance(k, str) and k in DRUMS else int(k)
        drum_ms[p] = ms
    res = []
    swung = {round(n.start / gb) for n in clip if abs(n.start / gb - round(n.start / gb)) < 1e-4
             and round(n.start / gb) % 2 == 1} if shift else set()
    for n in clip:
        pos = n.start / gb
        k = round(pos)
        on_grid = abs(pos - k) < 1e-4
        start, dur, v = n.start, n.dur, n.vel
        # a rolled chord moves as a whole: its lower voices (up to 40 ms before a swung line that has a note on it)
        # are swung with the top
        lead = not on_grid and shift and math.ceil(pos) in swung and \
            (math.ceil(pos) * gb - n.start) <= _ms_to_beats(40.0, _local(bpm, n.start)) + 1e-9
        if (on_grid and k % 2 == 1 and shift) or lead:
            start, dur = start + shift, max(dur - shift, dur * 0.25)
        if on_grid and gr.vel:
            v = _vel(v * gr.vel[k % len(gr.vel)])
        ms = drum_ms.get(n.pitch, 0.0) if drums else gr.late_ms
        start += _ms_to_beats(ms, _local(bpm, n.start)) if ms else 0.0  # at the tempo where the note is
        res.append(Note(start, dur, n.pitch, v))
    return res


# ------------------------------------------------------------------------------------ the body

@dataclass(frozen=True)
class Body:
    """A player's body: ONE physical gesture per phrase moves its timing and its dynamics together (user 2026-10-09,
    the breath A/B: "I imagine a player gently moving his body"), instead of independent random jitter per note.

    arc_ms / tempo / arc_vel  the phrase arc (Todd 1992, "The dynamics of dynamics"): tempo and loudness rise
                together into the phrase's peak (its loudest written note, 25-75 % in) and relax together toward
                its end - local tempo +-`tempo` (a share), velocity +-`arc_vel`, one curve; the phrase keeps its
                length (its onsets move at most `arc_ms` early / late; phrases under 3 s less)
    rit_beats / rit_w / rit_ms  every phrase end broadens: its last `rit_beats` beats slow to `rit_w` of the tempo
                along the decelerating-motion curve of Friberg & Sundberg (1999, "Does music performance allude to
                locomotion?"): v(x) = (1 + (w^q - 1) x)^(1/q), x = 0..1 through the span; the last onset at most
                `rit_ms` late (w is raised until it is) and never more than half the breath after it
    end_beats / end_w / end_ms  a section's last phrase: the deeper final ritardando
    q           the curve's shape (2-3: a runner, a ball rolling to rest)
    leap_ms / leap_cap  the hand travels: a note after a leap beyond a 4th arrives `leap_ms` per semitone late
                (at most `leap_cap` and a third of the time to it) - Friberg's leap rules, a pianist's hand shift
    breath_ms / breath_vel  a phrase start after a rest: a drawn breath - `breath_ms` late (settling back over the
                phrase's first beat), the first onset x `breath_vel`
    sway        the weight in the bar (velocity x): downbeat, the bar's middle, the other beats, off-beats - small
    noise_ms / noise_vel  what is left of the random jitter: motor noise (triangular +-)
    follow      the share of the arc's velocity the other hand takes (a follower moves with the lead's timing)
    Nothing within a phrase moves more than BODY_MAX_MS (40 ms); only the ritardandi add to the late side. Where the
    song's tempo lanes already shape the time (song.rubato, ritardando / ramps, fermatas over a phrase) the body
    leaves the tempo to them: no arc timing and no ritardando there, and its dynamic arc follows THEIR tempo (louder
    where they move on, softer where they hold back; leaps, breaths and sway stay)."""
    name: str = 'custom'
    arc_ms: float = 25.0
    tempo: float = 0.08
    arc_vel: float = 0.07
    rit_beats: float = 1.5
    rit_w: float = 0.85
    rit_ms: float = 40.0
    end_beats: float = 3.0
    end_w: float = 0.65
    end_ms: float = 100.0
    q: float = 2.5
    leap_ms: float = 2.0
    leap_cap: float = 25.0
    breath_ms: float = 14.0
    breath_vel: float = 0.92
    sway: tuple = (1.04, 1.01, 0.985, 0.975)
    noise_ms: float = 2.0
    noise_vel: float = 2.0
    follow: float = 0.6


BODIES: dict[str, Body | None] = {
    # a ballad at rest: small arcs, a slow settle into the phrase ends
    'calm': Body('calm', arc_ms=16.0, tempo=0.06, arc_vel=0.05, rit_beats=2.0, rit_w=0.85, rit_ms=35.0, end_beats=3.0,
                 end_w=0.7, end_ms=80.0, q=2.5, leap_ms=1.5, leap_cap=20.0, breath_ms=10.0, breath_vel=0.94,
                 sway=(1.03, 1.01, 0.99, 0.98), noise_ms=1.5, noise_vel=1.5, follow=0.6),
    # a singing line: the phrase pulls forward into its peak and lets go
    'lyrical': Body('lyrical'),
    # time is steady (a band keeps it): small arcs, light phrase ends, a section's end only laid back
    'swing': Body('swing', arc_ms=10.0, tempo=0.04, arc_vel=0.05, rit_beats=1.0, rit_w=0.92, rit_ms=20.0,
                  end_beats=3.0, end_w=0.8, end_ms=45.0, q=3.0, leap_ms=1.5, leap_cap=18.0, breath_ms=8.0,
                  breath_vel=0.95, sway=(1.025, 1.005, 0.99, 0.985), noise_ms=2.0, noise_vel=2.0, follow=0.5),
    # a salon waltz: the lyrical line with smaller arcs and a light sway - the downbeat leans in, beats 2 and 3
    # lighter (the oom-pah-pah's weight; its lilt - beat 2 early - is the song's tempo lilt)
    'waltz': Body('waltz', arc_ms=16.0, tempo=0.05, arc_vel=0.06, rit_beats=1.5, rit_w=0.88, rit_ms=30.0,
                  end_beats=3.0, end_w=0.7, end_ms=80.0, q=2.5, leap_ms=1.5, leap_cap=20.0, breath_ms=10.0,
                  breath_vel=0.94, sway=(1.055, 1.0, 0.975, 0.97), noise_ms=1.5, noise_vel=1.5, follow=0.7),
    'none': None,           # no body: the plain jitter (timing_ms / vel)
}
"""Body profiles for track.humanize(body=...) / body(): 'calm' (ballads), 'lyrical' (straight 8ths, a singing
line), 'swing' (a swung tune: steady time), 'waltz' (3/4: a light sway in the bar), 'none'. jazz.Feel.body picks one
from the feel; an endless piano feel names its own (genres feels 'body')."""

BODY_MAX_MS = 40.0          # no onset of a phrase moves further than this (ritardandi at phrase / section ends add)
BODY_PHRASE_BEATS = 16.0    # a phrase longer than this (no rest in it) is cut at its widest gap


def body_profile(b) -> Body | None:
    """A Body from a name of BODIES or a Body (None for 'none')."""
    if isinstance(b, Body):
        return b
    if isinstance(b, str) and b in BODIES:
        return BODIES[b]
    raise ComposeError(f"unknown body {b!r}; use one of {', '.join(BODIES)} or a humanize.Body(...)")


def leap_delay_ms(interval: int, per: float, cap: float, above: int = 4) -> float:
    """The time a hand takes for a leap: `per` ms per semitone beyond `above` (a 4th), at most `cap`."""
    return min(float(cap), float(per) * max(0, abs(int(interval)) - above))


def _rit_integral(x: float, w: float, q: float) -> float:
    """Integral of 1 / v over 0..x for v(x) = (1 + (w^q - 1) x)^(1/q) (Friberg & Sundberg's final ritardando)."""
    a = w ** q - 1.0
    r = 1.0 - 1.0 / q
    if abs(a) < 1e-9:
        return x
    if abs(r) < 1e-9:
        return math.log(1.0 + a * x) / a
    return ((1.0 + a * x) ** r - 1.0) / (a * r)


def rit_curve(x: float, w: float, q: float = 2.5) -> float:
    """Friberg & Sundberg's decelerating motion: the tempo at x (0..1 through the ritardando) as a share of the
    tempo before it, ending at w."""
    return (1.0 + (w ** q - 1.0) * min(1.0, max(0.0, x))) ** (1.0 / q)


class Motion:
    """A lead line's gestures (what the body did to it), for a follower - the other hand moves with the same body:
    `at(beat, tol)` -> (ms late, the arc's velocity factor) at a beat of the score."""

    def __init__(self, onsets, phrases):
        self.onsets = onsets            # sorted [(beat, ms late, arc factor, smooth ms (arc + ritardando))]
        self.phrases = phrases          # [(first onset beat, last onset beat, next phrase's first onset or None)]
        self._t = [o[0] for o in onsets]

    def at(self, beat: float, tol: float) -> tuple[float, float]:
        import bisect
        if not self.onsets:
            return 0.0, 1.0
        i = bisect.bisect_left(self._t, beat)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(self._t) and abs(self._t[j] - beat) <= tol and \
                    (best is None or abs(self._t[j] - beat) < abs(self._t[best] - beat)):
                best = j
        if best is not None:                      # struck with the lead: the whole gesture (a breath, a leap too)
            return self.onsets[best][1], self.onsets[best][2]
        k = bisect.bisect_right([p[0] for p in self.phrases], beat + _EPS) - 1
        if k < 0:
            return 0.0, 1.0
        t0, t1, nxt = self.phrases[k]
        if beat <= t1 + _EPS:                     # inside a phrase: the smooth part between the lead's onsets
            j = max(1, min(len(self._t) - 1, i))
            a, b = self.onsets[j - 1], self.onsets[j]
            u = 0.0 if b[0] - a[0] < _EPS else min(1.0, max(0.0, (beat - a[0]) / (b[0] - a[0])))
            return a[3] + (b[3] - a[3]) * u, a[2] + (b[2] - a[2]) * u
        j = bisect.bisect_right(self._t, t1 + _EPS) - 1      # the breath after it: the gesture comes to rest
        last = self.onsets[j][3]
        if nxt is None:
            return last, 1.0
        u = min(1.0, max(0.0, (beat - t1) / max(_EPS, nxt - t1)))
        return last * (1.0 - u), 1.0


def _clusters(notes, bpm) -> list[dict]:
    """Onsets: notes struck together (within 35 ms: chords, rolls) are one; its top note is the line."""
    order = sorted(range(len(notes)), key=lambda i: (notes[i].start, -notes[i].pitch))
    out: list[dict] = []
    for i in order:
        n = notes[i]
        if out and n.start - out[-1]['t'] <= _ms_to_beats(35.0, _local(bpm, n.start)):
            c = out[-1]
            c['idx'].append(i)
            c['end'] = max(c['end'], n.start + n.dur)
            continue
        out.append({'t': n.start, 'top': n.pitch, 'vel': n.vel, 'dur': n.dur, 'end': n.start + n.dur, 'idx': [i]})
    return out


def _phrase_starts(cl: list[dict], gap: float, marks) -> list[int]:
    """Cluster indices that start a phrase: after a rest >= gap, at a mark (the onset after the widest silence in
    the 1.5 beats before it) and, inside a phrase longer than BODY_PHRASE_BEATS, at its widest gap."""
    if not cl:
        return []
    silence = [math.inf]
    end = cl[0]['end']
    for c in cl[1:]:
        silence.append(c['t'] - end)
        end = max(end, c['end'])
    starts = {0} | {k for k in range(1, len(cl)) if silence[k] >= gap - _EPS}
    ts = [c['t'] for c in cl]
    for m in sorted(float(x) for x in marks or ()):
        if any(m - 1.5 - _EPS <= ts[k] <= m + 0.5 for k in starts):
            continue
        cand = [k for k in range(1, len(cl)) if m - 1.5 - _EPS <= ts[k] <= m + 0.05]
        if cand:
            starts.add(max(cand, key=lambda k: (silence[k], -abs(ts[k] - m))))
    changed = True
    while changed:
        changed = False
        order = sorted(starts)
        for a, b in zip(order, order[1:] + [len(cl)]):
            if ts[b - 1] - ts[a] > BODY_PHRASE_BEATS + _EPS:
                lo, hi = ts[a] + 0.25 * (ts[b - 1] - ts[a]), ts[a] + 0.75 * (ts[b - 1] - ts[a])
                mid = [k for k in range(a + 1, b) if lo <= ts[k] <= hi]
                if mid:
                    starts.add(max(mid, key=lambda k: (round(silence[k], 3), round(ts[k] - ts[k - 1], 3), -k)))
                    changed = True
                    break
    return sorted(starts)


def _sway(b: Body, bar_of, t: float) -> float:
    pos, blen = bar_of(t)
    if abs(pos - round(pos)) >= 0.04:
        return b.sway[3]
    k = int(round(pos)) % max(1, int(round(blen)))
    if k == 0:
        return b.sway[0]
    mid = blen >= 4 - _EPS and abs(blen % 2) < _EPS and k == int(round(blen / 2))
    return b.sway[1] if mid else b.sway[2]


def gesture(clip: Clip, body='lyrical', bpm=120.0, *, gap=0.5, marks=(), ends=(), busy=None, bar_of=None):
    """The body's plan for a line: ([(ms late, velocity factor)] per note of `clip` (in its order), Motion).
    gap: the rest (beats) that ends a phrase; marks: beats where the player's phrases start (notation phrases, the
    soloist's plan); ends: section ends (a deeper ritardando into them); busy(a, b): True where the song's tempo
    lanes shape the time (the body leaves it to them); bar_of(beat) -> (beat in the bar, beats per bar)."""
    b = body_profile(body)
    notes = list(clip)
    plan = [(0.0, 1.0)] * len(notes)
    if b is None or not notes:
        return plan, Motion([], [])
    bar_of = bar_of or (lambda t: (t % 4.0, 4.0))
    cl = _clusters(notes, bpm)
    starts = _phrase_starts(cl, beats(gap), marks)
    ends = sorted(float(e) for e in ends or ())
    K = len(cl)
    dt = [0.0] * K          # ms late
    smooth = [0.0] * K      # the arc + ritardando + breath part (what a follower takes between the lead's onsets)
    ritd = [0.0] * K        # the ritardando part (it may pass BODY_MAX_MS)
    fa = [1.0] * K          # the arc's velocity factor
    fx_ = [1.0] * K         # breath x sway
    phr = []

    def sec(a, c):
        return (c - a) * 60.0 / _local(bpm, a)
    for pi, k0 in enumerate(starts):
        k1 = starts[pi + 1] if pi + 1 < len(starts) else K
        P = list(range(k0, k1))
        ts = [cl[k]['t'] for k in P]
        nxt_t = cl[k1]['t'] if k1 < K else None
        phr.append((ts[0], ts[-1], nxt_t))
        grace = [k + 1 < k1 and cl[k]['dur'] <= 0.15 + _EPS and cl[k + 1]['t'] - cl[k]['t'] <= 0.15 + _EPS for k in P]
        L = ts[-1] - ts[0]
        gi = 0
        # ---- the arc: one curve for the tempo and the loudness, peaking where the phrase is loudest
        if len(P) >= 2 and L > _EPS:
            vs = [cl[k]['vel'] for k in P]
            vsm = [sum(vs[max(0, j - 1):j + 2]) / len(vs[max(0, j - 1):j + 2]) for j in range(len(P))]
            rng_v = max(vsm) - min(vsm)
            gi = max(range(len(P)), key=lambda j: (vsm[j], -j)) if rng_v >= 3.0 else \
                max(range(len(P)), key=lambda j: (cl[P[j]]['top'], -j))
            p = min(0.75, max(0.25, (ts[gi] - ts[0]) / L))
            lanes = bool(busy and busy(ts[0], ts[-1]))
            E = []
            if lanes and callable(bpm):
                # the song's tempo lanes move this phrase (rubato, a ritardando): the dynamics follow THEIR tempo -
                # louder where it moves on, softer where it holds back (10 % of tempo = the whole arc)
                tl = [math.log(max(1e-6, _local(bpm, t))) for t in ts]
                med = sorted(tl)[len(tl) // 2]
                E = [min(1.0, max(-1.0, (x - med) / math.log(1.1))) for x in tl]
            else:
                for j, t in enumerate(ts):
                    u = (t - ts[0]) / L
                    a = 0.5 - 0.5 * math.cos(math.pi * u / p) if u <= p else \
                        0.5 + 0.5 * math.cos(math.pi * (u - p) / (1.0 - p))
                    E.append(0.5 * a + 0.5 * (vsm[j] - min(vsm)) / rng_v if rng_v >= 3.0 else a)
                m = sum(E) / len(E)
                E = [e - m for e in E]
                s_ = max(abs(e) for e in E) or 1.0
                E = [e / s_ for e in E]
            for j, k in enumerate(P):
                fa[k] = 1.0 + b.arc_vel * E[j]
            if len(P) >= 3 and not lanes:
                secs = [sec(ts[j], ts[j + 1]) for j in range(len(P) - 1)]
                c, S = [0.0], [0.0]
                for j, s0 in enumerate(secs):
                    f = 1.0 + b.tempo * 0.5 * (E[j] + E[j + 1])
                    c.append(c[-1] + s0 / f - s0)
                    S.append(S[-1] + s0)
                if S[-1] > 0:
                    c = [c[j] - c[-1] * S[j] / S[-1] for j in range(len(c))]   # the phrase keeps its length
                peak = max(abs(x) for x in c) * 1000.0
                target = min(BODY_MAX_MS, b.arc_ms * min(1.0, S[-1] / 3.0))
                sc = 1000.0 * (min(1.0, target / peak) if peak > _EPS else 0.0)
                for j, k in enumerate(P):
                    dt[k] += c[j] * sc
                    smooth[k] += c[j] * sc
        # ---- the phrase end broadens (a section's last phrase: the final ritardando)
        end_e = next((e for e in ends if ts[-1] < e - _EPS and e - ts[-1] <= 4.0 + _EPS
                      and (nxt_t is None or nxt_t >= e - 0.05)), None)
        span_b, w, cap = (b.end_beats, b.end_w, b.end_ms) if end_e is not None else (b.rit_beats, b.rit_w, b.rit_ms)
        W = [j for j, t in enumerate(ts) if t >= ts[-1] - span_b - _EPS and not grace[j]]
        if len(W) >= 2 and ts[-1] - ts[W[0]] >= 0.5 - _EPS and not (busy and busy(ts[W[0]], ts[-1] + 0.5)):
            if nxt_t is not None:                        # never more than half the breath after the phrase
                end_ = max(cl[k]['end'] for k in P)
                cap = min(cap, 500.0 * sec(end_, nxt_t) if nxt_t > end_ else 0.0)
            Ssec = sec(ts[W[0]], ts[-1])

            def last_ms(w_):
                return Ssec * (_rit_integral(1.0, w_, b.q) - 1.0) * 1000.0
            if cap > 1.0:
                w_ = w
                if last_ms(w_) > cap:                   # raise w until the last onset is `cap` late
                    lo_w, hi_w = w, 1.0
                    for _ in range(40):
                        mid = 0.5 * (lo_w + hi_w)
                        lo_w, hi_w = (mid, hi_w) if last_ms(mid) > cap else (lo_w, mid)
                    w_ = hi_w
                for j in W:
                    x = (ts[j] - ts[W[0]]) / (ts[-1] - ts[W[0]])
                    d = Ssec * (_rit_integral(x, w_, b.q) - x) * 1000.0
                    dt[P[j]] += d
                    smooth[P[j]] += d
                    ritd[P[j]] += d
        # ---- the hand travels: a leap's landing late
        for j in range(1, len(P)):
            if grace[j] or grace[j - 1]:
                continue
            ioi = ts[j] - ts[j - 1]
            iv = cl[P[j]]['top'] - cl[P[j - 1]]['top']
            if 0.2 - _EPS <= ioi <= 1.5 + _EPS and abs(iv) >= 5:
                dt[P[j]] += min(leap_delay_ms(iv, b.leap_ms, b.leap_cap), sec(ts[j - 1], ts[j]) * 1000.0 / 3.0)
        # ---- grace notes lean on the note they lead into; the breath before the phrase
        for j in range(len(P) - 2, -1, -1):
            if grace[j]:
                dt[P[j]] = dt[P[j + 1]]
                smooth[P[j]] = smooth[P[j + 1]]
                ritd[P[j]] = ritd[P[j + 1]]
        first = next((j for j in range(len(P)) if not grace[j]), 0)
        # late after the breath, settling back over the rise into the phrase's peak (at least a beat): the hand
        # catches up as the line swells - faster with louder (Todd); settling within the first beat while the line
        # is still soft hurried the quiet start (the piano bodies' coupling came out negative)
        rise = max(1.0, ts[gi] - ts[first])
        for j in range(len(P)):
            u = 0.0 if j <= first else (ts[j] - ts[first]) / rise
            if u >= 1.0:
                break
            dt[P[j]] += b.breath_ms * (1.0 - u)
            smooth[P[j]] += b.breath_ms * (1.0 - u)
            if j <= first:
                fx_[P[j]] *= b.breath_vel
    for k, c in enumerate(cl):
        fx_[k] *= _sway(b, bar_of, c['t'])               # the weight in the bar
    # ---- bounds: +-40 ms within a phrase (a ritardando adds to the late side); the order kept
    for k in range(K):
        dt[k] = max(-BODY_MAX_MS, min(BODY_MAX_MS + ritd[k], dt[k]))
    for k in range(1, K):
        t0, t1 = cl[k - 1]['t'], cl[k]['t']
        floor = t0 + _ms_to_beats(dt[k - 1], _local(bpm, t0)) + 0.3 * (t1 - t0)
        if t1 + _ms_to_beats(dt[k], _local(bpm, t1)) < floor:
            dt[k] = (floor - t1) * 60000.0 / _local(bpm, t1)
    for k, c in enumerate(cl):
        for i in c['idx']:
            plan[i] = (dt[k], fa[k] * fx_[k])
    return plan, Motion([(c['t'], dt[k], fa[k], smooth[k]) for k, c in enumerate(cl)], phr)


def follow_plan(clip: Clip, motion: Motion, body, bpm=120.0, *, bar_of=None) -> list[tuple[float, float]]:
    """A follower's plan (the other hand): each note moves with the lead's gesture at its beat - struck with a lead
    onset, all of it (a breath, a leap); between, the smooth arc / ritardando - and takes `follow` of the arc's
    velocity, with its own weight in the bar."""
    b = body_profile(body)
    notes = list(clip)
    if b is None:
        return [(0.0, 1.0)] * len(notes)
    bar_of = bar_of or (lambda t: (t % 4.0, 4.0))
    out = []
    for n in notes:
        ms, fa = motion.at(n.start, _ms_to_beats(35.0, _local(bpm, n.start)))
        out.append((ms, (1.0 + b.follow * (fa - 1.0)) * _sway(b, bar_of, n.start)))
    return out


def apply_plan(notes, plan, bpm=120.0, *, at=None, noise_ms: float = 0.0, noise_vel: float = 0.0, seed=0) -> list:
    """Notes moved by a body plan [(ms late, velocity factor)] (+ triangular motor noise, seeded); `at`: the beats
    whose tempo converts the milliseconds (default the notes' own starts)."""
    r = _rng(seed)
    out = []
    for k, (n, (ms, f)) in enumerate(zip(notes, plan)):
        t = n.start if at is None else at[k]
        ms_ = ms + (_tri(r) * noise_ms if noise_ms else 0.0)
        v = n.vel * f + (_tri(r) * noise_vel if noise_vel else 0.0)
        out.append(n._replace(start=max(0.0, n.start + _ms_to_beats(ms_, _local(bpm, t))), vel=_vel(v)))
    return out


def body(clip: Clip, body='lyrical', bpm=120.0, *, seed=0, gap=0.5, marks=(), ends=(), lead=None,
         noise_ms: float | None = None, noise_vel: float | None = None) -> Clip:
    """Play a line with a body (BODIES / a Body): one gesture per phrase moves its timing and its dynamics together -
    the phrase arc (faster and louder into the peak, broader and softer away from it), a ritardando into every
    phrase end along the decelerating-motion curve (deeper into `ends`), a leap's landing late, a breath before a
    phrase after a rest, the weight in the bar, a little motor noise. lead: the other hand's clip (or a Motion from
    gesture()) whose gesture this one follows. bpm may be a function of the beat. On a track:
    track.humanize(body='lyrical') (+ lead='piano' on the left hand) - applied at compile, after the groove."""
    b = body_profile(body)
    if b is None:
        return clip
    if lead is not None:
        mo = lead if isinstance(lead, Motion) else gesture(lead, b, bpm, gap=gap)[1]
        plan = follow_plan(clip, mo, b, bpm)
    else:
        plan = gesture(clip, b, bpm, gap=gap, marks=marks, ends=ends)[0]
    nm = b.noise_ms if noise_ms is None else noise_ms
    nv = b.noise_vel if noise_vel is None else noise_vel
    return Clip._raw(apply_plan(list(clip), plan, bpm, noise_ms=nm, noise_vel=nv, seed=seed), clip.length)


# ------------------------------------------------------------------------------------ measuring a body

def _pearson(xs, ys) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx < 1e-12 or sy < 1e-12:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def fit_rit(xs, vs) -> tuple[float, float, float]:
    """(w, q, rms) of Friberg & Sundberg's v(x) = (1 + (w^q - 1) x)^(1/q) fitted to tempo shares vs at xs (0..1)."""
    best = (1.0, 2.5, math.inf)
    for wi in range(40, 106):
        w = wi / 100.0
        for qi in range(2, 25):
            q = qi / 4.0
            e = sum((rit_curve(x, w, q) - v) ** 2 for x, v in zip(xs, vs))
            if e < best[2]:
                best = (w, q, e)
    return best[0], best[1], math.sqrt(best[2] / max(1, len(xs)))


def body_metrics(written, played, seconds, ends=(), gap=0.5) -> dict:
    """How a line moves (the lead hand): written notes (after the groove, beats) vs the same notes as played
    (beats; matched by pitch, the nearest within 0.15 beat), seconds(beat) the song's tempo map.
      coupling       per phrase (6+ onsets) the correlation of local tempo and velocity, mean over phrases:
                     'note' the player's own timing (onsets vs the written ones at the same tempo map), 'heard'
                     with the tempo map (local beats per second) - Todd's arc: faster where louder (> 0)
      rit            the phrase into each section end: its last onset's lateness against the tempo before the
                     ritardando window (ms) and Friberg & Sundberg's curve fitted (w = the final tempo share, q)
      leap / step    a note's lateness against its neighbours' after a leap of a 5th+ / a step (ms)
      breath         a phrase's first onset vs its second (ms late, velocity share)
      noise_ms       the spread (sd) of the onsets' lateness against their neighbours' on steps"""
    used = set()
    by_pitch: dict[int, list[int]] = {}
    for j, n in enumerate(played):
        by_pitch.setdefault(n.pitch, []).append(j)
    pairs = []
    for n in sorted(written, key=lambda n: (n.start, n.pitch)):
        cand = [j for j in by_pitch.get(n.pitch, ()) if j not in used and abs(played[j].start - n.start) <= 0.15]
        if cand:
            j = min(cand, key=lambda j: abs(played[j].start - n.start))
            used.add(j)
            pairs.append((n, played[j]))
    cl = _clusters([w for w, _ in pairs], 120.0)
    for c in cl:
        top = max(c['idx'], key=lambda i: pairs[i][0].pitch)
        w, p = pairs[top]
        c.update(S=seconds(w.start), P=seconds(p.start), pv=p.vel)
        c['d'] = (c['P'] - c['S']) * 1000.0
    starts = _phrase_starts(cl, beats(gap), ())
    out: dict = {'onsets': len(cl), 'phrases': len(starts)}
    rn, rh_, leaps, steps, breaths, bvel, rits = [], [], [], [], [], [], []
    for pi, k0 in enumerate(starts):
        k1 = starts[pi + 1] if pi + 1 < len(starts) else len(cl)
        P = cl[k0:k1]
        ln, lh, lv = [], [], []
        for a, b in zip(P, P[1:]):
            if b['t'] - a['t'] < 0.2 - _EPS or b['P'] - a['P'] <= 1e-6:
                continue
            ln.append((b['S'] - a['S']) / (b['P'] - a['P']))
            lh.append((b['t'] - a['t']) / (b['P'] - a['P']))
            lv.append(0.5 * (a['pv'] + b['pv']))
        if len(ln) >= 5:
            for xs, acc in ((ln, rn), (lh, rh_)):
                r = _pearson(xs, lv)
                if r is not None:
                    acc.append(r)
        for j in range(1, len(P) - 1):
            ioi = P[j]['t'] - P[j - 1]['t']
            if not 0.2 - _EPS <= ioi <= 1.5 + _EPS or P[j + 1]['t'] - P[j]['t'] < 0.2 - _EPS:
                continue
            e = P[j]['d'] - 0.5 * (P[j - 1]['d'] + P[j + 1]['d'])
            iv = abs(P[j]['top'] - P[j - 1]['top'])
            (leaps if iv >= 7 else steps if iv <= 2 else []).append(e)
        if pi and len(P) >= 2:
            breaths.append(P[0]['d'] - P[1]['d'])
            bvel.append(P[0]['pv'] / max(1, P[1]['pv']))
        # the ritardando into a section end
        last = P[-1]
        e_ = next((e for e in ends if last['t'] < e - _EPS and e - last['t'] <= 4.0 + _EPS
                   and (k1 >= len(cl) or cl[k1]['t'] >= e - 0.05)), None)
        if e_ is None:
            continue
        W = [c for c in P if c['t'] >= last['t'] - 3.0 - _EPS]
        before = [c for c in cl[:k1] if W[0]['t'] - 4.0 - _EPS <= c['t'] <= W[0]['t'] + _EPS]
        ref = [(b['t'] - a['t']) / (b['P'] - a['P']) for a, b in zip(before, before[1:])
               if b['t'] - a['t'] >= 0.2 - _EPS and b['P'] > a['P']]
        if len(W) < 3 or len(ref) < 2:
            continue
        ref_ = sorted(ref)[len(ref) // 2]
        span = last['t'] - W[0]['t']
        xs, vs = [], []
        for a, b in zip(W, W[1:]):
            if b['t'] - a['t'] >= 0.2 - _EPS and b['P'] > a['P']:
                xs.append((0.5 * (a['t'] + b['t']) - W[0]['t']) / span)
                vs.append((b['t'] - a['t']) / (b['P'] - a['P']) / ref_)
        late = (last['P'] - (W[0]['P'] + span / ref_)) * 1000.0
        w, q, rms = fit_rit(xs, vs) if len(xs) >= 2 else (None, None, None)
        rits.append({'at': round(e_, 2), 'late_ms': round(late, 1), 'w': w, 'q': q, 'rms': None if rms is None
                     else round(rms, 3)})

    def mean(xs, nd=2):
        return round(sum(xs) / len(xs), nd) if xs else None
    out['coupling'] = {'note': mean(rn, 3), 'heard': mean(rh_, 3), 'phrases': len(rn)}
    fitted = [r for r in rits if r['w'] is not None and r['w'] < 0.92]
    out['rit'] = {'ends': len(rits), 'late_ms': mean([r['late_ms'] for r in rits], 1),
                  'w': mean([r['w'] for r in fitted]), 'q': mean([r['q'] for r in fitted]), 'fitted': len(fitted),
                  'each': rits}
    out['leap_ms'], out['step_ms'], out['leaps'] = mean(leaps, 1), mean(steps, 1), len(leaps)
    out['breath_ms'], out['breath_vel'] = mean(breaths, 1), mean(bvel, 3)
    if len(steps) > 2:
        m = sum(steps) / len(steps)
        out['noise_ms'] = round(math.sqrt(sum((x - m) ** 2 for x in steps) / len(steps)), 1)
    return out


def body_stats(song, track: str = 'piano', gap=0.5) -> dict:
    """body_metrics() of a song's track (compiled: the groove, the body / the jitter, the tempo map)."""
    render = song.compile()
    t = song.tracks[track]
    tm = song.tempo_map()
    bpm = song.tempo if tm.constant else tm.bpm_at
    written = list(Clip._raw(t._notes, song.length))
    if t._groove is not None:
        written = _grooved(Clip._raw(written, song.length), t._groove, bpm, t.instrument.type == 'drums')
    rt = next(x for x in render['tracks'] if x['id'] == track)
    played = [Note(s, d, p, v) for s, d, p, v in rt['notes']]
    return body_metrics(written, played, tm.seconds_at, [s.end for s in song.sections], gap)
