"""Gestures: additive shapes on abstract performance LANES inside and between notes - the shared micro-performance
layer of every player that moves its sound WHILE a note sounds (the hornist's breath and bell, the guitarist's bends,
vibrato, feedback and wah, the soloist's parts).

A `Gesture` is one move as played: a name, a kind, start / end (beats) and `_Shape`s on LANES - keyframes joined by
cosine eases (zero slope at every key) or a function of the beat, sampled every <= 20 ms when written (sample()):
no zipper, no clicks. Lanes are abstract; a player's render() maps them to a track's targets:

    air     dB of level after the chain (the breath stage 'fx.air.gain': a wind player's air, a guitarist's pick
            dynamics and volume knob)
    bright  dB of tone that comes with the air          mic / prox / shelf   the mic stage (distance, 300 Hz, axis)
    room    dB on the reverb sends                       bend    semitones of pitch ('instrument.pitchbend')
    vib     cents of the sampler's own (centred) vibrato depth
    harm    0..1 of the string's harmonic (sampler 'harmonic': pinch harmonics, controlled feedback)
    wah     0..1 wah pedal position (the 'wah' fx)        wahmix  0..1 the wah switched in (its mix)
    mute    0..1 palm mute (the voices' low-pass closing)  echo    0..1 added to the echo mix (throws)

The generic moves live here and are shared: pitch - bend (rise, overshoot, settle, release), vibrato (centred on
the 'vib' lane, or a waveform on the 'bend' lane that only goes UP from the note - a guitarist pushing the string - or
DOWN from a bent note), scoop, fall, doit, shake, growl; air - push, pulse, swell, messa_di_voce, fp_cresc, bloom,
taper, breath_release, accents; mic - lean_in, turn_away, off_axis, bell_swing, fade_away. agentsound.hornist (wind
players) and agentsound.fretwork (the lead guitarist's hands) are built on them.
"""

from __future__ import annotations

import bisect
import math

from .theory import ComposeError

_EPS = 1e-6
LANES = ('air', 'bright', 'bend', 'vib', 'mic', 'prox', 'shelf', 'room', 'harm', 'wah', 'wahmix', 'mute', 'echo')
_RES = 0.02          # seconds between sampled points (a lane never moves more than ~0.8 dB between two of them)


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


def _pos(at) -> float:
    if hasattr(at, 'start') and not isinstance(at, (int, float)):
        return float(at.start)
    return _num(at, 'at (beats)')


def _b(seconds: float, bpm: float) -> float:
    """seconds -> beats"""
    return seconds * bpm / 60.0


def _ease(u: float) -> float:
    u = 0.0 if u <= 0 else 1.0 if u >= 1 else u
    return 0.5 - 0.5 * math.cos(math.pi * u)


class _Shape:
    """One additive contribution to an abstract lane over [t0, t1] (beats): keyframes joined by cosine eases (zero
    slope at every key) or a function of the beat. jump: the shape starts with a step at t0 (a scoop into an
    attack); otherwise it starts and ends at 0."""

    __slots__ = ('lane', 't0', 't1', 'keys', 'fn', 'jump', 'res')

    def __init__(self, lane: str, keys=None, *, fn=None, t0=None, t1=None, jump: bool = False, res: float = _RES):
        if lane not in LANES:
            raise ComposeError(f"unknown lane {lane!r}; lanes: {', '.join(LANES)}")
        self.lane, self.jump, self.res, self.fn = lane, jump, res, fn
        if keys is not None:
            ks = sorted(((float(t), float(v)) for t, v in keys), key=lambda k: k[0])
            self.keys = ks
            self.t0, self.t1 = ks[0][0], ks[-1][0]
        else:
            self.keys = None
            self.t0, self.t1 = float(t0), float(t1)

    def __call__(self, t: float) -> float:
        if t < self.t0 - _EPS or t > self.t1 + _EPS:
            return 0.0
        if self.fn is not None:
            return self.fn(t)
        ks = self.keys
        i = bisect.bisect_right([k[0] for k in ks], t)
        if i <= 0:
            return ks[0][1]
        if i >= len(ks):
            return ks[-1][1]
        (ta, va), (tb, vb) = ks[i - 1], ks[i]
        if tb - ta < _EPS:
            return vb
        return va + (vb - va) * _ease((t - ta) / (tb - ta))

    def shifted(self, by: float) -> '_Shape':
        if self.keys is not None:
            return _Shape(self.lane, [(t + by, v) for t, v in self.keys], jump=self.jump, res=self.res)
        f = self.fn
        return _Shape(self.lane, fn=lambda t, f=f, by=by: f(t - by), t0=self.t0 + by, t1=self.t1 + by, jump=self.jump,
                      res=self.res)

    def breaks(self) -> list:
        return [k[0] for k in self.keys] if self.keys is not None else [self.t0, self.t1]


class Gesture:
    """One move as played: name, kind ('air' | 'pitch' | 'mic'), start / end (beats), shapes (additive, on LANES),
    rate (vibrato rate points (beat, Hz) - vibrato only), params (what it was played with)."""

    def __init__(self, name: str, kind: str, start: float, end: float, shapes, params=None, rate=None):
        self.name, self.kind, self.start, self.end = name, kind, float(start), float(end)
        self.shapes: list[_Shape] = list(shapes)
        self.params = dict(params or {})
        self.rate = list(rate or [])

    def __repr__(self) -> str:
        ps = ', '.join(f"{k}={v:g}" if isinstance(v, float) else f"{k}={v}" for k, v in self.params.items())
        return f"Gesture({self.name} {self.start:g}-{self.end:g}{', ' + ps if ps else ''})"

    def shifted(self, by: float) -> 'Gesture':
        return Gesture(self.name, self.kind, self.start + by, self.end + by, [s.shifted(by) for s in self.shapes],
                       self.params, [(r[0] + by,) + tuple(r[1:]) for r in self.rate])

    def value(self, lane: str, t: float) -> float:
        """The sum of this gesture's shapes on `lane` at beat t."""
        return sum(s(t) for s in self.shapes if s.lane == lane)


def _back(end: float, bpm: float, back) -> float:
    """Where a phrase-end shape returns to rest: `back` (a beat: the next onset) or 0.6 s after the end (the tail)."""
    b = end + _b(0.6, bpm)
    if back is not None:
        b = min(b, float(back) - _b(0.01, bpm))
    return max(b, end + _b(0.03, bpm))


# ------------------------------------------------------------------------------------------------ air moves

def _spot(start: float, dur: float, bpm: float, grid: float = 0.5) -> float:
    """Where a push goes by default: the first beat (else 8th: a syncopation) inside the held note, at least 0.25 s
    after the attack and 0.3 s before the end; else 40 % into the note."""
    lo, hi = start + _b(0.25, bpm), start + dur - _b(0.3, bpm)
    for g in (1.0, grid):
        t = math.ceil((lo - _EPS) / g) * g
        if t <= hi + _EPS:
            return t
    return start + 0.4 * dur


def push(start, dur, bpm, *, at=None, db: float = 2.5, ms: float = 160.0, rise: float = 0.35, lift: float = 5.0,
         bright: float = 0.35) -> Gesture:
    """A breath accent INSIDE a held note (start, dur in beats): the air rises `db` (2-4) over rise x ms (80-250 ms
    in all) and falls back, the pitch lifts `lift` cents with it (the harder-blown note goes a little sharp) and the
    tone opens bright x db. at= the beat where it starts (default the first beat or syncopation after the attack:
    _spot)."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'push dur', 0.05)
    db = _num(db, 'push db', -12, 12)
    w = _b(_num(ms, 'push ms', 40, 600) / 1000.0, b)
    r = _num(rise, 'push rise', 0.1, 0.9)
    t0 = _spot(s, d, b) if at is None else _pos(at)
    t0 = max(s, min(t0, s + d - w))
    tp = t0 + r * w
    sh = [_Shape('air', [(t0, 0), (tp, db), (t0 + w, 0)])]
    if lift:
        sh.append(_Shape('bend', [(t0, 0), (tp, lift / 100.0), (t0 + w, 0)]))
    if bright:
        sh.append(_Shape('bright', [(t0, 0), (tp, db * bright), (t0 + w, 0)]))
    return Gesture('push', 'air', t0, t0 + w, sh, dict(db=db, ms=ms, lift=lift))


def pulse(start, dur, bpm, *, n: int | None = None, every: float = 1.0, db: float = 2.0, ms: float = 140.0,
          fade: float = 0.85, lift: float = 3.0, bright: float = 0.3, jitter=None) -> Gesture:
    """2-4 rhythmic pushes over a long note, on the groove: on the beat grid (`every` beats, absolute: 1 = the
    beats, 0.5 = the 8ths) after the attack and before the release; each one `fade` x the one before; n = how many
    (default all that fit, at most 4). jitter: (random.Random, ms) - a player's timing (a few ms)."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'pulse dur', 0.05)
    ev = _num(every, 'pulse every (beats)', 0.25, 4)
    w = _b(_num(ms, 'pulse ms', 40, 500) / 1000.0, b)
    lo, hi = s + _b(0.22, b), s + d - _b(0.25, b) - w
    ts = []
    t = math.ceil((lo - _EPS) / ev) * ev
    while t <= hi + _EPS:
        ts.append(t)
        t += ev
    cap = 4 if n is None else int(_num(n, 'pulse n', 1, 8))
    ts = ts[:cap]
    if not ts:
        ts = [max(s, min(s + 0.4 * d, s + d - w))]
    sh, level = [], db
    for t in ts:
        if jitter is not None:
            rng, jms = jitter
            t = t + _b((rng.random() * 2 - 1) * jms / 1000.0, b)
        t = max(s, min(t, s + d - w))
        tp = t + 0.35 * w
        sh.append(_Shape('air', [(t, 0), (tp, level), (t + w, 0)]))
        if lift:
            sh.append(_Shape('bend', [(t, 0), (tp, lift / 100.0 * level / db if db else 0), (t + w, 0)]))
        if bright:
            sh.append(_Shape('bright', [(t, 0), (tp, level * bright), (t + w, 0)]))
        level *= _num(fade, 'pulse fade', 0.3, 1.5)
    return Gesture('pulse', 'air', ts[0], ts[-1] + w, sh, dict(n=len(ts), db=db, every=ev))


def _tail(keys: list, end: float, bpm: float, back, lane='air', v_end=None) -> list:
    """keyframes that hold the end value past the note end (its tail) and return to 0 by `back`."""
    v = keys[-1][1] if v_end is None else v_end
    if abs(v) < 1e-9:
        return keys
    bk = _back(end, bpm, back)
    return keys + [(max(end, bk - _b(0.12, bpm)), v), (bk, 0.0)]


def swell(start, dur, bpm, *, lo: float = -3.0, peak: float = 2.0, end: float = -2.0, peak_at: float = 0.55,
          tied: bool = False, back=None, bright: float = 0.4) -> Gesture:
    """A swell over a held note: it starts `lo` dB under, grows to `peak` at peak_at (0..1 of the note) and fades to
    `end`. tied=True (a legato note: no silence before it) eases down to lo over the 50 ms before the note instead of
    stepping; the end level is held into the tail and comes back by `back` (the next onset, default the tail's end)."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'swell dur', 0.05)
    pa = _num(peak_at, 'swell peak_at', 0.05, 0.95)
    e = s + d
    pre = _b(0.05, b)
    keys = ([(s - pre, 0.0), (s, lo)] if tied else [(s, 0.0), (s, lo)]) + [(s + pa * d, peak), (e, end)]
    keys = _tail(keys, e, b, back)
    sh = [_Shape('air', keys, jump=not tied and abs(lo) > 1e-9)]
    if bright:
        sh.append(_Shape('bright', [(t, v * bright) for t, v in keys], jump=not tied and abs(lo) > 1e-9))
    return Gesture('swell', 'air', s, e, sh, dict(lo=lo, peak=peak, end=end, peak_at=pa))


def messa_di_voce(start, dur, bpm, *, lo: float = -5.0, peak: float = 2.5, end: float = -5.0, **kw) -> Gesture:
    """The classical swell: from soft to full and back to soft over one held note (a swell with the ends lower)."""
    g = swell(start, dur, bpm, lo=lo, peak=peak, end=end, peak_at=kw.pop('peak_at', 0.5), **kw)
    g.name = 'messa_di_voce'
    return g


def fp_cresc(start, dur, bpm, *, attack: float = 1.0, dip: float = -6.0, dip_ms: float = 180.0, bloom: float = 2.0,
             tied: bool = False, back=None, bright: float = 0.45) -> Gesture:
    """fp-crescendo: the attack (+attack dB), a quick dip to `dip` within dip_ms, then a bloom to +bloom at the end
    of the note (the brass / sax "pow - hush - grow")."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'fp dur', 0.05)
    e = s + d
    t1 = s + min(_b(_num(dip_ms, 'fp dip_ms', 40, 800) / 1000.0, b), 0.4 * d)
    keys = [(s, 0.0), (s + _b(0.012, b), attack), (t1, dip), (e, bloom)]
    keys = _tail(keys, e, b, back)
    sh = [_Shape('air', keys), _Shape('bright', [(t, v * bright) for t, v in keys])]
    return Gesture('fp_cresc', 'air', s, e, sh, dict(dip=dip, bloom=bloom))


def bloom(start, dur, bpm, *, under: float = -3.0, ms: float = 320.0, over: float = 0.5, tied: bool = False,
          bright: float = 0.5) -> Gesture:
    """The note starts `under` dB (and darker) and blooms into its full tone over `ms` (a touch of overshoot
    `over`, then settles)."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'bloom dur', 0.05)
    w = min(_b(_num(ms, 'bloom ms', 60, 1500) / 1000.0, b), 0.8 * d)
    pre = _b(0.05, b)
    head = [(s - pre, 0.0), (s, under)] if tied else [(s, 0.0), (s, under)]
    keys = head + [(s + w, over), (min(s + d, s + w * 1.6), 0.0)]
    sh = [_Shape('air', keys, jump=not tied), _Shape('bright', [(t, v * bright) for t, v in keys], jump=not tied)]
    return Gesture('bloom', 'air', s, s + w, sh, dict(under=under, ms=ms))


def taper(start, dur, bpm, *, db: float = -5.0, frac: float = 0.45, back=None, bright: float = 0.4) -> Gesture:
    """The phrase end: the last `frac` of the note fades `db` (and darkens); held into the tail, back to rest by
    `back` (the next onset) at the latest."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'taper dur', 0.05)
    e = s + d
    t0 = e - _num(frac, 'taper frac', 0.05, 1.0) * d
    keys = _tail([(t0, 0.0), (e, db)], e, b, back)
    sh = [_Shape('air', keys), _Shape('bright', [(t, v * bright) for t, v in keys])]
    return Gesture('taper', 'air', t0, e, sh, dict(db=db, frac=frac))


def breath_release(end, bpm, *, db: float = -9.0, ms: float = 110.0, drop: float = -12.0, back=None) -> Gesture:
    """The air runs out at the very end of a note ending at `end`: -db over the last `ms` and the pitch sags `drop`
    cents (a released, not a cut, note)."""
    b = _bpm(bpm)
    e = _pos(end)
    w = _b(_num(ms, 'breath_release ms', 20, 500) / 1000.0, b)
    keys = _tail([(e - w, 0.0), (e, db)], e, b, back)
    bend = _tail([(e - w, 0.0), (e, drop / 100.0)], e, b, back)
    return Gesture('breath_release', 'air', e - w, e, [_Shape('air', keys), _Shape('bend', bend)],
                   dict(db=db, ms=ms, drop=drop))


# ------------------------------------------------------------------------------------------------ pitch moves

def vibrato(start, dur, bpm, *, depth: float = 22.0, hz: float = 5.4, delay: float = 0.28, grow: float = 0.5,
            rise: float = 0.3, shape: str = 'centre', lane: str | None = None, widen: float = 0.0,
            wobble: float = 0.0, seed=0, base: float = 0.0) -> Gesture:
    """Delayed vibrato on a held note: straight for `delay` s, then the depth (cents) grows over `grow` s, dies
    in the last 60 ms; the rate starts at `hz` and quickens by `rise` Hz over a long note. When placed, the depth
    follows the air (deeper on a push or a swell's peak, shallower in a taper).

    shape: 'centre' (+-depth around the note: a wind player, a string player, a whammy bar - on the sampler's own
    vibrato lane 'vib' unless lane='bend'), 'up' (0 .. +depth: a guitarist pushing the string - the pitch only goes UP
    from the note) or 'down' (0 .. -depth: the vibrato of a BENT note, released a little and pushed back to the
    target); 'up' / 'down' are a waveform on the 'bend' lane (sampled every 8 ms). widen: the depth grows by this
    share over the next 3 s of a long note (a guitarist's vibrato opens up as the note sings); wobble: 0..0.3 a
    player's unevenness - depth and rate drift slowly (seeded); base: semitones added to the lane over the note (a
    held bend under the vibrato is usually its own gesture)."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'vibrato dur', 0.05)
    if shape not in ('centre', 'up', 'down'):
        raise ComposeError(f"vibrato shape must be 'centre', 'up' or 'down', got {shape!r}")
    ln = lane if lane is not None else ('vib' if shape == 'centre' else 'bend')
    if ln not in ('vib', 'bend'):
        raise ComposeError(f"vibrato lane must be 'vib' or 'bend', got {ln!r}")
    if ln == 'vib' and shape != 'centre':
        raise ComposeError("vibrato on the 'vib' lane (the sampler's centred LFO) is shape='centre'; "
                           "'up' / 'down' go on lane='bend'")
    e = s + d
    d0, d1 = s + _b(delay, b), s + _b(delay + grow, b)
    off = e - _b(0.06, b)
    if off <= d0 + _EPS:
        return Gesture('vibrato', 'pitch', s, e, [], dict(depth=0.0, hz=hz))
    top = depth if off >= d1 else depth * (off - d0) / (d1 - d0)
    hz = _num(hz, 'vibrato hz', 0.5, 12)
    hz1 = min(12.0, hz + rise * min(1.0, (e - s) * 60 / b / 3.0))
    if ln == 'vib' and not widen and not wobble and not base:
        keys = [(d0, 0.0), (min(d1, off), top), (off, top), (e, 0.0)]
        rate = [(s, round(hz, 3), 'step'), (e, round(hz1, 3))]
        return Gesture('vibrato', 'pitch', s, e, [_Shape('vib', keys)], dict(depth=round(top, 2), hz=round(hz, 2)),
                       rate=rate)
    import random as _random
    rng = _random.Random(f"vibrato:{seed}:{s:.6f}")
    ph1, ph2, ph3 = (rng.random() * 2 * math.pi for _ in range(3))
    wob = _num(wobble, 'vibrato wobble', 0, 0.5)
    wid = _num(widen, 'vibrato widen', 0, 3)
    T = max(1e-6, (e - s) * 60.0 / b)               # seconds
    df = hz1 - hz

    def phase(tau):                                 # cycles at tau seconds into the note
        p = hz * tau + df * tau * tau / (2.0 * T)
        if wob:                                     # the rate drifts +-wob/2 at ~0.9 Hz
            w = 2 * math.pi * 0.9
            p += 0.5 * wob * hz * (math.cos(ph1) - math.cos(w * tau + ph1)) / w
        return p

    def env(t):
        if t <= d0:
            return 0.0
        g = _ease((t - d0) / max(_EPS, d1 - d0))
        g *= 1.0 + wid * min(1.0, max(0.0, (t - d1) * 60.0 / b / 3.0))
        if wob:
            tau = (t - s) * 60.0 / b
            g *= 1.0 + wob * (0.6 * math.sin(2 * math.pi * 0.7 * tau + ph2) + 0.4 * math.sin(2 * math.pi * 1.3 * tau + ph3))
        return g * _ease((e - t) / max(_EPS, e - off))

    if shape == 'centre':
        def wave(c):
            return math.sin(2 * math.pi * c)
    elif shape == 'up':
        def wave(c):
            return 0.5 - 0.5 * math.cos(2 * math.pi * c)
    else:
        def wave(c):
            return -(0.5 - 0.5 * math.cos(2 * math.pi * c))
    unit = depth / 100.0 if ln == 'bend' else depth

    def fn(t):
        tau = (t - s) * 60.0 / b
        return base + unit * env(t) * wave(phase(tau))
    shapes = [_Shape(ln, fn=fn, t0=s, t1=e, res=0.008)]
    return Gesture('vibrato', 'pitch', s, e, shapes, dict(depth=round(top, 2), hz=round(hz, 2), shape=shape,
                                                         widen=wid, wobble=wob))


def bend(start, dur, bpm, *, semis: float = 2.0, at: float = 0.0, rise_ms: float = 140.0, overshoot: float = 8.0,
         settle_ms: float = 110.0, release=None, release_ms: float = 180.0, release_to: float = 0.0, pre=None,
         back=None, return_ms: float = 25.0) -> Gesture:
    """A pitch bend on the 'bend' lane over a note (start, dur in beats): the note sounds `semis` lower at first (the
    fretted note: write it there) and is pushed up `at` s after the attack over rise_ms (fast at first, then
    landing), overshooting by `overshoot` cents and settling onto the target over settle_ms (a player's ear catching
    the pitch: 5-15 ct); held; release= a beat (absolute) where it is let down over release_ms to release_to
    semitones (0 = the fretted note). pre= seconds before the note: a PRE-bend - the string is already up when the
    note is picked (the lane steps up silently `pre` s before the onset; then release= lets it down). After the note
    the lane returns to 0 within return_ms (the string let go while muted), by `back` (the next onset) at the latest.
    Generic: a guitar's bends (agentsound.fretwork), a whammy bar, a synth's pitch wheel."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'bend dur', 0.02)
    st = _num(semis, 'bend semis', -24, 24)
    e = s + d
    ov = _num(overshoot, 'bend overshoot (cents)', -50, 50) / 100.0 * (1 if st >= 0 else -1)
    if pre is not None:
        t0 = s - _b(_num(pre, 'bend pre (s)', 0.005, 2.0), b)
        keys = [(t0, st)]
        jump = True
        t_up = t0
    else:
        t_up = s + _b(_num(at, 'bend at (s)', 0, 30), b)
        r = _b(_num(rise_ms, 'bend rise_ms', 10, 3000) / 1000.0, b)
        sl = _b(_num(settle_ms, 'bend settle_ms', 0, 2000) / 1000.0, b)
        keys = [(t_up, 0.0), (t_up + r, st + ov)]
        if sl > 0 and ov:
            keys.append((t_up + r + sl, st))
        jump = False
        t_up = keys[-1][0]
    last = st
    if release is not None:
        rel = max(_pos(release), t_up + _b(0.01, b))
        rto = _num(release_to, 'bend release_to', -24, 24)
        rw = _b(_num(release_ms, 'bend release_ms', 10, 3000) / 1000.0, b)
        keys += [(rel, st), (min(rel + rw, max(rel + _b(0.01, b), e)), rto)]
        last = rto
    if keys[-1][0] < e:
        keys.append((e, last))
    if abs(last) > 1e-9:
        bk = e + _b(_num(return_ms, 'bend return_ms', 2, 500) / 1000.0, b)
        if back is not None:
            bk = min(bk, float(back) - _b(0.004, b))
        keys.append((max(bk, keys[-1][0] + _b(0.002, b)), 0.0))
    return Gesture('bend', 'pitch', keys[0][0], e, [_Shape('bend', keys, jump=jump)],
                   dict(semis=st, rise_ms=rise_ms, overshoot=overshoot, pre=pre is not None, release=release is not None))


def scoop(start, bpm, *, cents: float = -70.0, ms: float = 90.0) -> Gesture:
    """The note starts `cents` flat and glides up to pitch over `ms` (a scoop into an attack)."""
    b = _bpm(bpm)
    s = _pos(start)
    w = _b(_num(ms, 'scoop ms', 20, 400) / 1000.0, b)
    c = _num(cents, 'scoop cents', -2400, 2400)
    return Gesture('scoop', 'pitch', s, s + w, [_Shape('bend', [(s, c / 100.0), (s + w, 0.0)], jump=True)],
                   dict(cents=c, ms=ms))


def fall(end, bpm, *, semis: float = -3.0, ms: float = 200.0, back=None, air: float = -6.0) -> Gesture:
    """A fall-off: the last `ms` of the note drop `semis` (and the air goes out, `air` dB); both come back to rest
    after the tail (by `back`)."""
    b = _bpm(bpm)
    e = _pos(end)
    w = _b(_num(ms, 'fall ms', 40, 800) / 1000.0, b)
    st = _num(semis, 'fall semis', -12, 12)
    sh = [_Shape('bend', _tail([(e - w, 0.0), (e, st)], e, b, back))]
    if air:
        sh.append(_Shape('air', _tail([(e - w, 0.0), (e, air)], e, b, back)))
    return Gesture('fall' if st < 0 else 'doit', 'pitch', e - w, e, sh, dict(semis=st, ms=ms))


def doit(end, bpm, *, semis: float = 3.0, ms: float = 160.0, back=None, air: float = -4.0) -> Gesture:
    """A doit: the end of the note flips UP `semis` and dies (a fall upwards)."""
    return fall(end, bpm, semis=abs(semis), ms=ms, back=back, air=air)


def shake(start, dur, bpm, *, interval: float = 3.0, hz: float = 6.5, fade_in: float = 0.15) -> Gesture:
    """A lip shake / sax shake on a held note: the pitch flips between the note and `interval` semitones above at
    `hz`, fading in over fade_in s and out at the end. Rare: a set piece for a hook peak."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'shake dur', 0.05)
    e = s + d
    fi, fo = _b(_num(fade_in, 'shake fade_in', 0.02, 1), b), _b(0.08, b)
    iv, f = _num(interval, 'shake interval', 0.5, 5), _num(hz, 'shake hz', 2, 12)

    def fn(t):
        env = _ease((t - s) / fi) * _ease((e - t) / fo)
        return env * iv * (0.5 - 0.5 * math.cos(2 * math.pi * f * (t - s) * 60.0 / b))
    return Gesture('shake', 'pitch', s, e, [_Shape('bend', fn=fn, t0=s, t1=e, res=0.005)], dict(interval=iv, hz=f))


def growl(start, dur, bpm, *, db: float = 1.6, cents: float = 10.0, hz: float = 27.0, bright: float = 1.5) -> Gesture:
    """A growl (humming into the horn): a fast rough flutter of level (+-db) and pitch (+-cents) at ~hz with a
    brighter, edgier tone, faded in and out. Rare: rock / r&b sax and trombone peaks."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'growl dur', 0.05)
    e = s + d
    fi = _b(0.08, b)
    f = _num(hz, 'growl hz', 10, 45)

    def env(t):
        return _ease((t - s) / fi) * _ease((e - t) / fi)

    def am(t):
        return env(t) * db * math.sin(2 * math.pi * f * (t - s) * 60.0 / b)

    def fm(t):
        return env(t) * cents / 100.0 * math.sin(2 * math.pi * f * (t - s) * 60.0 / b + 1.1)
    sh = [_Shape('air', fn=am, t0=s, t1=e, res=0.003), _Shape('bend', fn=fm, t0=s, t1=e, res=0.003),
          _Shape('bright', [(s, 0), (s + fi, bright), (e - fi, bright), (e, 0)])]
    return Gesture('growl', 'pitch', s, e, sh, dict(db=db, cents=cents, hz=f))


# ------------------------------------------------------------------------------------------------ mic moves

def _plateau(lane, s, e, v, a, r):
    a, r = min(a, 0.45 * (e - s)), min(r, 0.45 * (e - s))
    return _Shape(lane, [(s, 0.0), (s + a, v), (e - r, v), (e, 0.0)])


def lean_in(start, dur, bpm, *, db: float = 2.0, prox: float = 2.5, bright: float = 1.8, room: float = -3.0,
            ms: float = 350.0) -> Gesture:
    """The bell leans into the mic for the span (start, dur): louder (+db), the proximity lift around 300 Hz
    (+prox dB: fuller), a little brighter (+bright above ~3 kHz), drier (the reverb sends `room` dB), moving in and
    out over ~ms."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'lean_in dur', 0.1)
    e, w = s + d, _b(_num(ms, 'lean_in ms', 60, 2000) / 1000.0, b)
    sh = [_plateau('mic', s, e, db, w, w), _plateau('prox', s, e, prox, w, w), _plateau('shelf', s, e, bright, w, w)]
    if room:
        sh.append(_plateau('room', s, e, room, w, w))
    return Gesture('lean_in', 'mic', s, e, sh, dict(db=db, prox=prox, bright=bright, room=room))


def turn_away(start, dur, bpm, *, shelf: float = -4.0, db: float = -1.0, room: float = 2.5, ms: float = 400.0) -> Gesture:
    """The bell turns off-axis for the span: darker (a gentle shelf `shelf` dB above ~3.2 kHz), a little quieter
    (db), relatively more room (the reverb sends +room dB)."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'turn_away dur', 0.1)
    e, w = s + d, _b(_num(ms, 'turn_away ms', 60, 2000) / 1000.0, b)
    sh = [_plateau('shelf', s, e, shelf, w, w), _plateau('mic', s, e, db, w, w)]
    if room:
        sh.append(_plateau('room', s, e, room, w, w))
    return Gesture('turn_away', 'mic', s, e, sh, dict(shelf=shelf, db=db, room=room))


def off_axis(start, dur, bpm, **kw) -> Gesture:
    """= turn_away."""
    g = turn_away(start, dur, bpm, **kw)
    g.name = 'off_axis'
    return g


def bell_swing(start, dur, bpm, *, seconds: float = 1.2, shelf: float = -3.0, db: float = -0.8, room: float = 2.0,
               at: float = 0.35) -> Gesture:
    """The bell sweeps through: on-axis -> off-axis -> back over `seconds` (0.5-2 s) inside a long note (from `at`
    of it), darker and roomier in the middle."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'bell_swing dur', 0.1)
    w = min(_b(_num(seconds, 'bell_swing seconds', 0.3, 4), b), 0.9 * d)
    t0 = min(s + _num(at, 'bell_swing at', 0, 0.9) * d, s + d - w)
    m = t0 + 0.5 * w
    sh = [_Shape('shelf', [(t0, 0), (m, shelf), (t0 + w, 0)]), _Shape('mic', [(t0, 0), (m, db), (t0 + w, 0)])]
    if room:
        sh.append(_Shape('room', [(t0, 0), (m, room), (t0 + w, 0)]))
    return Gesture('bell_swing', 'mic', t0, t0 + w, sh, dict(seconds=round(w * 60 / b, 3), shelf=shelf))


def fade_away(start, dur, bpm, *, shelf: float = -5.0, db: float = -4.0, room: float = 3.0, frac: float = 0.6,
              back=None) -> Gesture:
    """A phrase end played away from the mic: over the last `frac` of the note the bell turns off-axis (shelf dB
    darker, room dB more reverb) while the level tapers `db`; back to rest after the tail."""
    b = _bpm(bpm)
    s, d = _pos(start), _num(dur, 'fade_away dur', 0.1)
    e = s + d
    t0 = e - _num(frac, 'fade_away frac', 0.1, 1) * d
    sh = [_Shape('shelf', _tail([(t0, 0.0), (e, shelf)], e, b, back)),
          _Shape('mic', _tail([(t0, 0.0), (e, db)], e, b, back))]
    if room:
        sh.append(_Shape('room', _tail([(t0, 0.0), (e, room)], e, b, back)))
    return Gesture('fade_away', 'mic', t0, e, sh, dict(shelf=shelf, db=db, room=room))


def accents(notes, bpm, *, db_per_vel: float = 0.12, ms: float = 40.0, limit: float = 4.0, back=None) -> Gesture:
    """The player's note-to-note dynamics as air: every note of a phrase sits (vel - the phrase's mean velocity) x
    db_per_vel dB off (at most +-limit), moving to it over the first `ms` of each onset (the tongue: legato, no step). notes = [(start,
    dur, vel)] of one phrase. On a compressed chain (a hero lead) the velocities alone barely move the level - the
    compressor squeezes them - so place() writes these after it (the 'air' / 'mic' stage); elsewhere the
    velocities do it themselves and place() leaves this out."""
    b = _bpm(bpm)
    ns = sorted(notes)
    if not ns:
        return Gesture('accents', 'air', 0, 0, [])
    mv = sum(v for _, _, v in ns) / len(ns)
    k = _num(db_per_vel, 'accents db_per_vel', 0, 1)
    h = _b(_num(ms, 'accents ms', 2, 200) / 2000.0, b)
    lvl = [max(-limit, min(limit, (v - mv) * k)) for _, _, v in ns]
    keys = [(ns[0][0], lvl[0])]
    for i in range(1, len(ns)):
        t = ns[i][0]
        keys += [(max(keys[-1][0], t), lvl[i - 1]), (t + 2 * h, lvl[i])]
    end = ns[-1][0] + ns[-1][1]
    keys = _tail(keys + [(end, lvl[-1])], end, b, back)
    return Gesture('accents', 'air', ns[0][0], end, [_Shape('air', keys, jump=abs(lvl[0]) > 1e-9)],
                   dict(db_per_vel=k, mean_vel=round(mv, 1)))


# ------------------------------------------------------------------------------------------------ sampling

def _sample(shapes: list, combine, bpm: float) -> list:
    """Points of combine({lane: sum}) where the shapes are active: windows = overlapping shapes, a point every
    <= res s (and at every keyframe); a jump shape adds a step at its start."""
    if not shapes:
        return []
    shapes = sorted(shapes, key=lambda s: s.t0)
    wins: list[list] = []
    for s in shapes:
        if wins and s.t0 <= wins[-1][1] + _EPS:
            wins[-1][1] = max(wins[-1][1], s.t1)
            wins[-1][2].append(s)
        else:
            wins.append([s.t0, s.t1, [s]])
    pts: list = []
    for w0, w1, group in wins:
        res = _b(min(s.res for s in group), bpm)
        ts = {w0, w1}
        for s in group:
            ts.update(s.breaks())
        n = int(math.ceil((w1 - w0) / res - 1e-9))
        ts.update(w0 + k * (w1 - w0) / max(n, 1) for k in range(n + 1))
        jumps = {round(s.t0, 9) for s in group if s.jump}

        def vals(t, skip_jump_at=None):
            v: dict = {}
            for s in group:
                if skip_jump_at is not None and s.jump and abs(s.t0 - skip_jump_at) < _EPS:
                    continue
                if s.t0 - _EPS <= t <= s.t1 + _EPS:
                    v[s.lane] = v.get(s.lane, 0.0) + s(t)
            return v
        for t in sorted(ts):
            if round(t, 9) in jumps:
                pts.append((round(t, 6), round(combine(vals(t, t)), 5)))
                pts.append((round(t, 6), round(combine(vals(t)), 5), 'step'))
            else:
                pts.append((round(t, 6), round(combine(vals(t)), 5)))
    return pts
