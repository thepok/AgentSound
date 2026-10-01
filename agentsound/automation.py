"""Automation point generators (and the normalizer the song compiler uses).

A point is (beat, value) or (beat, value, curve). The curve shapes the segment ARRIVING at the point:
'linear' (default), 'exp' (exponential - use for frequencies, values must be > 0), 'smooth' (cosine
ease), 'step' (jump at the point). Before the first point the first value holds, after the last the
last value holds. Generators return point lists; hand one or several to node.automate():

    lead.automate('instrument.cutoff', exp_ramp(verse.start, chorus.start, 400, 6000))
    pad.automate('fx.chorus.mix', per_section({intro: 0.2, chorus: 0.5}, glide=2))
    music.automate('fx.filter.cutoff', riser(chorus.start, 8, lo=300, hi=18000, reset=18000))
    bass.automate('instrument.cutoff', lfo(verse.start, verse.end, 300, 2400, period='1/4', log=True))

Several automate() calls on the same target merge. Points on exactly the same beat become an instant
jump (the earlier point is moved JUMP beats back); a 'step' point (hold, steps, per_section, riser
reset) is always the value after the jump, otherwise the point listed later is.
"""

from __future__ import annotations

import math

from .patterns import beats
from .theory import ComposeError

CURVES = ('linear', 'exp', 'smooth', 'step')
JUMP = 1e-3  # beats between the two points of an instant jump


def _num(x, what: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    return float(x)


def _pos(x) -> float:
    """A beat position: number or anything with a .start (a Section)."""
    if hasattr(x, 'start') and not isinstance(x, (int, float)):
        return float(x.start)
    return _num(x, 'beat')


def point(beat, value, curve: str = 'linear') -> list:
    """A single point (as a one-element list, so it can be concatenated with other generators)."""
    return [(_pos(beat), value, curve)]


def ramp(start, end, frm: float, to: float, curve: str = 'linear') -> list:
    """Go from `frm` at `start` to `to` at `end`."""
    s, e = _pos(start), _pos(end)
    if e <= s:
        raise ComposeError(f"ramp end {e} must be after start {s}")
    return [(s, frm), (e, to, curve)]


def exp_ramp(start, end, frm: float, to: float) -> list:
    """Exponential ramp (even musical speed for frequencies: 200 -> 400 takes as long as 4000 -> 8000)."""
    if frm <= 0 or to <= 0:
        raise ComposeError(f"exp_ramp needs values > 0, got {frm} -> {to}")
    return ramp(start, end, frm, to, 'exp')


def smooth_ramp(start, end, frm: float, to: float) -> list:
    return ramp(start, end, frm, to, 'smooth')


def hold(start, end, value: float) -> list:
    """Jump to `value` at `start` and keep it until `end` (then the next points take over)."""
    s, e = _pos(start), _pos(end)
    if e <= s:
        raise ComposeError(f"hold end {e} must be after start {s}")
    return [(s, value, 'step'), (e, value)]


def steps(values: dict) -> list:
    """{beat_or_section: value} -> stepped values (jump at each beat)."""
    return [(_pos(b), v, 'step') for b, v in sorted(values.items(), key=lambda kv: _pos(kv[0]))]


def per_section(values: dict, glide: float = 0.0, curve: str = 'smooth') -> list:
    """{section: value}: each section starts at its value. glide > 0 moves there over the last
    `glide` beats of the previous section (with `curve`), else it jumps on the section start."""
    items = sorted(values.items(), key=lambda kv: _pos(kv[0]))
    pts: list = []
    prev = None
    for sec, v in items:
        s = _pos(sec)
        if prev is None:
            pts.append((s, v))
        elif glide > 0:
            pts += [(max(s - glide, pts[-1][0] + JUMP), prev), (s, v, curve)]
        else:
            pts.append((s, v, 'step'))
        prev = v
    return pts


def swell(start, end, lo: float, hi: float, peak: float = 0.5, curve: str = 'smooth') -> list:
    """Rise from lo to hi and fall back to lo; peak = where the top is (0..1 of the span)."""
    s, e = _pos(start), _pos(end)
    if e <= s or not 0 < peak < 1:
        raise ComposeError("swell needs end > start and 0 < peak < 1")
    return [(s, lo), (s + (e - s) * peak, hi, curve), (e, lo, curve)]


def riser(end, length: float = 8.0, lo: float = 200.0, hi: float = 12000.0, curve: str = 'exp',
          reset: float | None = None) -> list:
    """Build-up into `end` (a drop / section start): lo -> hi over the last `length` beats.
    reset= snaps to that value exactly at `end` (e.g. a high-pass rising into the drop, then off)."""
    e = _pos(end)
    L = beats(length)
    if L <= 0 or e - L < 0:
        raise ComposeError(f"riser of {L} beats into beat {e} would start before 0")
    if reset is None:
        return [(e - L, lo), (e, hi, curve)]
    return [(e - L, lo), (e - JUMP, hi, curve), (e, reset, 'step')]


def fade(start, end, frm: float = -60.0, to: float = 0.0) -> list:
    """Fader move in dB for the 'gainDb' target (fade(outro.start, outro.end, 0, -60) fades out)."""
    return ramp(start, end, frm, to, 'linear')


def lfo(start, end, lo: float, hi: float, period=1.0, shape: str = 'sine', phase: float = 0.0,
        res: int = 16, log: bool = False) -> list:
    """Tempo-synced LFO drawn as points between lo and hi.
    shape: sine, tri, saw (ramp up), saw_down, square. period in beats or '1/8' etc.; phase in cycles.
    log=True moves geometrically (use for Hz, both values must be > 0). res = points per cycle."""
    s, e = _pos(start), _pos(end)
    P = beats(period)
    if e <= s or P <= 0:
        raise ComposeError("lfo needs end > start and period > 0")
    if log and (lo <= 0 or hi <= 0):
        raise ComposeError("lfo(log=True) needs lo and hi > 0")

    def val(u: float) -> float:
        return lo * (hi / lo) ** u if log else lo + (hi - lo) * u

    cur = 'exp' if log else 'linear'
    frac = lambda t: ((t - s) / P + phase) % 1.0  # noqa: E731
    pts: list = []
    if shape in ('sine', 'tri', 'triangle'):
        n = max(1, int(math.ceil((e - s) / P * res - 1e-9)))
        for k in range(n + 1):
            t = min(s + k * P / res, e)
            x = frac(t) if t < e else ((e - s) / P + phase) % 1.0
            u = 0.5 - 0.5 * math.cos(2 * math.pi * x) if shape == 'sine' else 1.0 - abs(2.0 * x - 1.0)
            if pts and t - pts[-1][0] < JUMP:
                continue
            pts.append((t, val(u), cur) if pts else (t, val(u)))
        return pts
    if shape not in ('saw', 'saw_down', 'square'):
        raise ComposeError(f"unknown lfo shape {shape!r}; use sine, tri, saw, saw_down or square")

    def u_at(x: float) -> float:
        return x if shape == 'saw' else 1.0 - x if shape == 'saw_down' else (1.0 if x < 0.5 else 0.0)

    pts.append((s, val(u_at(frac(s)))))
    step_len = P / 2 if shape == 'square' else P
    if shape == 'square':  # next time the phase crosses a half cycle
        t = s + ((math.floor(2 * phase) + 1) / 2 - phase) * P
    else:                  # next cycle start
        t = s + (math.floor(phase) + 1 - phase) * P
    if t <= s + JUMP:
        t += step_len
    while t < e - JUMP:
        x = frac(t + JUMP / 2)
        if shape == 'square':
            pts.append((t, val(u_at(x)), 'step'))
        else:
            if t - JUMP > pts[-1][0] + JUMP / 2:
                pts.append((t - JUMP, val(u_at(1.0 - 1e-9)), cur))
            pts.append((t, val(u_at(0.0)), 'step'))
        t += step_len
    if shape != 'square':
        x_end = frac(e)
        pts.append((e, val(u_at(x_end if x_end > 1e-9 else 1.0 - 1e-9)), cur))  # arrive, don't wrap
    return pts


def normalize(points, where: str = 'automation') -> list[list]:
    """Validate and merge points into the render format: [[beat, value], [beat, value, curve], ...],
    strictly increasing in beat. Points on the same beat become an instant jump to the last one, where
    'step' points (the start of hold / steps / per_section / a riser reset) win over plain arrivals,
    so hold(4, 8, v) means "v from beat 4" whether it is listed before or after a ramp ending at 4."""
    pts = []
    for i, p in enumerate(points):
        if not isinstance(p, (tuple, list)) or len(p) not in (2, 3):
            raise ComposeError(f"{where}: point {p!r} must be (beat, value) or (beat, value, curve)")
        b = _num(p[0], f"{where}: point #{i} beat")
        v = _num(p[1], f"{where}: point #{i} value")
        c = p[2] if len(p) == 3 else 'linear'
        if c not in CURVES:
            raise ComposeError(f"{where}: point {tuple(p)!r} has curve {c!r}; use one of {', '.join(CURVES)}")
        if b < 0:
            raise ComposeError(f"{where}: point {tuple(p)!r} is before beat 0")
        pts.append((b, v, c, i))
    pts.sort(key=lambda q: (round(q[0], 6), q[2] == 'step', q[3]))
    out: list[list] = []
    for b, v, c, _ in pts:
        if out and abs(b - out[-1][0]) < 1e-6:
            if abs(v - out[-1][1]) < 1e-12:
                continue
            if out[-1][0] - JUMP > (out[-2][0] + 1e-6 if len(out) > 1 else -1e-9):
                out[-1][0] -= JUMP
            else:
                out.pop()
            out.append([b, v, 'step'])
        else:
            out.append([b, v, c])
    for k, (b, v, c) in enumerate(out):
        if c == 'exp' and (v <= 0 or (k > 0 and out[k - 1][1] <= 0)):
            raise ComposeError(f"{where}: 'exp' curve at beat {b:g} needs strictly positive values on both "
                               f"ends (got {out[k - 1][1] if k else v:g} -> {v:g}); use 'linear' or 'smooth'")
    return [[round(b, 6), round(v, 6)] + ([c] if c != 'linear' else []) for b, v, c in out]
