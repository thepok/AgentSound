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
          pitch: float = 0.8, sync: float = 1.1, passing: float = 0.84, grace: float = 0.62, last: float = 0.86,
          inner: float = 0.86) -> Clip:
    """A pianist's (or singer's) touch on a melody: velocities written from the line instead of one flat level.
    phrase_dynamics() shades a written level by a few percent (about 1 dB); touch() sets the level itself, so a
    melody gets the 8-12 dB of note-to-note contrast a player gives it (user feedback 2026-09-30: a lead with every
    note at one velocity "sounds equally loud", even when the level changes between sections).

    Per phrase (split at rests >= gap): the phrase rises to its goal - its highest note (the longest of equal ones)
    - from lo + start x (hi - lo) and relaxes after it to lo + end x (hi - lo) (a cosine arc in time). The clip's
    highest note is the summit and gets hi; a phrase that peaks lower peaks softer (1 velocity per semitone below
    the summit, at least half-way up; a two-note pickup phrase half-way). On top: `pitch` velocity per semitone
    above / below the phrase's mean (higher notes sing out), syncopations - an off-beat 8th held a beat or more,
    i.e. tied over the beat - x sync, short passing notes (off the beat, a step between two neighbours) x passing,
    grace notes (<= 0.15 beat) x grace of the note they lead into, a short last note x last (the release), and
    notes sounding together (octaves, a chord under the melody) x inner below the top one (voice the top); nothing
    above hi + 3. Section levels: soft head lo 50..60 / hi 90..100, a climax lo 75..85 / hi 115..122 (the
    Salamander's top layers start at 105 / 113 / 121). Apply it before octave_double / block_chords (they scale the
    added voices from the melody's velocity)."""
    lo, hi = _num_range(lo, 'touch lo'), _num_range(hi, 'touch hi')
    if hi < lo:
        raise ComposeError(f"touch hi ({hi:g}) must be >= lo ({lo:g})")
    for x, what in ((start, 'start'), (end, 'end')):
        if not 0.0 <= x <= 1.0:
            raise ComposeError(f"touch {what} must be 0..1, got {x!r}")
    for x, what in ((sync, 'sync'), (passing, 'passing'), (grace, 'grace'), (last, 'last'), (inner, 'inner')):
        if not 0.1 <= x <= 2.0:
            raise ComposeError(f"touch {what} must be 0.1..2, got {x!r}")
    if not 0.0 <= pitch <= 5.0:
        raise ComposeError(f"touch pitch (velocity per semitone) must be 0..5, got {pitch!r}")
    out: list[Note] = []
    span = hi - lo
    cap = min(127.0, hi + 3.0)
    top_all = max((n.pitch for n in clip), default=0)
    for ph in phrases(clip, gap):
        ph.sort(key=lambda n: (n.start, -n.pitch))
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
            if n is not goal and off and n.dur >= 1.0 - _EPS:
                v *= sync
            elif 0 < i < len(tops) - 1 and n.dur <= 0.5 + _EPS and off:
                a_, b_ = tops[i - 1].pitch, tops[i + 1].pitch
                if min(a_, b_) <= n.pitch <= max(a_, b_) and abs(n.pitch - a_) <= 2 and abs(n.pitch - b_) <= 2:
                    v *= passing
            if i == len(tops) - 1 and len(tops) > 1 and n.dur < 1.0 - _EPS and n is not goal:
                v *= last
            level[id(n)] = min(v, cap)
        # grace notes lean on the note they lead into
        for i, n in enumerate(tops):
            if n.dur <= 0.15 + _EPS and i + 1 < len(tops):
                level[id(n)] = level[id(tops[i + 1])] * grace
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
    (snare late etc.) instead of the whole-part late_ms shift. bpm may be a function of the beat."""
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
    for n in clip:
        pos = n.start / gb
        k = round(pos)
        on_grid = abs(pos - k) < 1e-4
        start, dur, v = n.start, n.dur, n.vel
        if on_grid and k % 2 == 1 and shift:
            start, dur = start + shift, max(dur - shift, dur * 0.25)
        if on_grid and gr.vel:
            v = _vel(v * gr.vel[k % len(gr.vel)])
        ms = drum_ms.get(n.pitch, 0.0) if drums else gr.late_ms
        start += _ms_to_beats(ms, _local(bpm, n.start)) if ms else 0.0  # at the tempo where the note is
        res.append(Note(start, dur, n.pitch, v))
    return Clip._raw(res, clip.length)
