"""Song time: tempo maps (tempo changes, ramps, ritardando / accelerando, fermatas, rubato) and meters.

The engine renders a tempo map exactly (docs/RENDER_FORMAT.md "Tempo map"): points [beat, bpm(, curve)] where
the curve ('linear' default, 'smooth', 'step') shapes how the tempo moves from the previous point, beats stay
quarter notes and note times follow by exact integration. The Song keeps its tempo *events* (song.set_tempo,
tempo_ramp, ritardando, accelerando, rubato, fermata) and builds the points at compile with TempoPlan; TempoMap
mirrors the engine's math, so song.seconds(), song.tempo_at() and humanize / groove millisecond conversions agree
with the render to the sample.

Meters: a section has its own meter (song.section('waltz', bars=8, meter=(3, 4))); bars are counted in it and
the render JSON gets a "meter" list so the report numbers the song's real bars. Beats are always quarter notes:
3/4 = 3 beats per bar, 6/8 = 3 beats (two dotted quarters), 7/8 = 3.5, 12/8 = 6.
"""

from __future__ import annotations

import math
import random
import re
from bisect import bisect_right as _bisect

from .theory import ComposeError

CURVES = ('linear', 'smooth', 'step')
EPS = 1e-4          # beats between the two points of an instant tempo jump
SAMPLE = 0.25       # beats between the points of a sampled tempo curve (rubato)
FINE = 1.0 / 32.0   # beats between the points of a finely sampled curve (lilt: beat-level shapes)
CHORD = 0.25        # beats after a fermata's beat whose onsets still belong to its chord (strums, rolls)
MIN_BPM, MAX_BPM = 10.0, 600.0     # what the compose layer accepts for a tempo
PHRASES = ('arch', 'wave', 'lean', 'breath', 'free')
LILT_MAX = 0.3      # beats a lilted beat may arrive early / late (a pulse, not a new rhythm)


def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        lo_s = f"{lo:g}" if lo is not None else '-inf'
        hi_s = f"{hi:g}" if hi is not None else 'inf'
        raise ComposeError(f"{what} = {x:g} is outside {lo_s}..{hi_s}")
    return float(x)


# ------------------------------------------------------------------------------------------ meter

def parse_meter(m, what: str = 'meter') -> tuple[int, int]:
    """(numerator, denominator) from '3/4', (3, 4) or [3, 4]; denominators 1 2 4 8 16 32."""
    if isinstance(m, str):
        mm = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', m)
        if not mm:
            raise ComposeError(f"{what} must look like '3/4' or (6, 8), got {m!r}")
        m = (int(mm.group(1)), int(mm.group(2)))
    try:
        n, d = m
    except (TypeError, ValueError):
        raise ComposeError(f"{what} must be '3/4' or (3, 4), got {m!r}") from None
    if not (isinstance(n, int) and isinstance(d, int)) or isinstance(n, bool) or isinstance(d, bool):
        raise ComposeError(f"{what} {m!r}: numerator and denominator must be whole numbers")
    if not 1 <= n <= 64 or d not in (1, 2, 4, 8, 16, 32):
        raise ComposeError(f"bad {what} {m!r}: numerator 1..64, denominator 1, 2, 4, 8, 16 or 32")
    return n, d


def beats_per_bar(meter: tuple[int, int]) -> float:
    """Quarter-note beats in one bar: 4/4 = 4, 3/4 = 3, 6/8 = 3, 7/8 = 3.5."""
    return meter[0] * 4.0 / meter[1]


def _partial_meter(beats: float, where: str) -> tuple[int, int]:
    """The meter of a short bar of `beats` beats (a pickup / leftover bar before a meter change)."""
    for d in (4, 8, 16, 32):
        n = beats * d / 4.0
        if abs(n - round(n)) < 1e-6 and 1 <= round(n) <= 64:
            return int(round(n)), d
    raise ComposeError(f"{where}: a bar of {beats:g} beats can't be written as a meter (whole 32nd notes); "
                       f"give the section whole bars or a fraction like 0.5 / 0.25 of a bar")


class MeterGrid:
    """Bars of the song from meter points [[beat, numerator, denominator], ...] (first at beat 0): the same
    numbering as the engine's report (0-based bars here, 1-based in the report)."""

    def __init__(self, points):
        self.points = [(float(b), int(n), int(d)) for b, n, d in points]
        self._segs = []  # (beat, beats per bar, bars before)
        bar0 = 0.0
        for i, (b, n, d) in enumerate(self.points):
            if i:
                pb, pbpb, pbar0 = self._segs[-1]
                bar0 = pbar0 + round((b - pb) / pbpb)
            self._segs.append((b, n * 4.0 / d, bar0))

    def _seg_beat(self, beat: float):
        s = self._segs[0]
        for seg in self._segs:
            if seg[0] <= beat + 1e-9:
                s = seg
        return s

    def meter_at(self, beat: float) -> tuple[int, int]:
        i = 0
        for k, (b, _, _) in enumerate(self.points):
            if b <= beat + 1e-9:
                i = k
        return self.points[i][1], self.points[i][2]

    def bar_at(self, beat: float) -> float:
        """Fractional 0-based bar number of a beat."""
        b, bpb, bar0 = self._seg_beat(beat)
        return bar0 + (beat - b) / bpb

    def bar_start(self, bar: float) -> float:
        """Beat where 0-based bar `bar` starts (fractions move inside the bar)."""
        s = self._segs[0]
        for seg in self._segs:
            if seg[2] <= bar + 1e-9:
                s = seg
        return s[0] + (bar - s[2]) * s[1]

    def advance(self, start: float, bars: float) -> float:
        """The beat `bars` bars after `start`, each bar in the meter where it falls."""
        pos, left = float(start), float(bars)
        while left > 1e-12:
            _, bpb, _ = self._seg_beat(pos)
            nxt = next((b for b, _, _ in self.points if b > pos + 1e-9), math.inf)
            room = (nxt - pos) / bpb
            if left <= room + 1e-12:
                return pos + left * bpb
            pos, left = nxt, left - room
        return pos


def meter_points(sections, default: tuple[int, int]) -> list[list]:
    """Engine "meter" points from sequential sections (each with .name, .start, .meter): every section's bars
    start at its start (as section.bar(n) counts them), so a point where the meter changes, and a section that
    starts inside a bar of the meter before it gets a short bar first (a pickup of 1 beat: a 1/4 bar; 4.5 bars of
    4/4 then 3/4: a 2/4 bar)."""
    first = sections[0].meter if sections else default
    pts = [[0.0, first[0], first[1]]]
    cur_beat, cur = 0.0, first
    for s in sections[1:]:
        bpb = beats_per_bar(cur)
        whole = math.floor((s.start - cur_beat) / bpb + 1e-9)
        line = cur_beat + whole * bpb
        rem = s.start - line
        start = s.start
        if rem > 1e-6:
            try:
                n, d = _partial_meter(rem, s.name)
            except ComposeError:            # (not a whole number of 32nds: the new bars start at the bar line before)
                if s.meter == cur:
                    continue
                start = line
            else:
                if abs(line - pts[-1][0]) < 1e-9:
                    pts[-1] = [line, n, d]  # the whole bar before is the short one (a pickup)
                else:
                    pts.append([line, n, d])
        elif s.meter == cur:
            continue
        if abs(start - pts[-1][0]) < 1e-9:
            pts[-1] = [start, s.meter[0], s.meter[1]]
        else:
            pts.append([start, s.meter[0], s.meter[1]])
        cur_beat, cur = start, s.meter
    return pts


# ------------------------------------------------------------------------------------------ tempo map

class TempoMap:
    """Exact beat <-> seconds of engine tempo points [[beat, bpm(, curve)], ...] (the first at beat 0), the
    engine's own math: linear bpm-over-beats segments last 60*(b1-b0)/(bpm1-bpm0)*ln(bpm1/bpm0) s, smooth ones
    60*(b1-b0)/sqrt(bpm0*bpm1) s; before beat 0 the first tempo holds, after the last point the last one."""

    def __init__(self, points):
        if not points or points[0][0] != 0:
            raise ComposeError("a tempo map starts at beat 0")
        self.points = [list(p) for p in points]
        segs = []   # [b0, b1, p0, p1, kind, t0]
        for i in range(1, len(points)):
            a, b = points[i - 1], points[i]
            curve = b[2] if len(b) > 2 else 'linear'
            if b[0] <= a[0]:
                raise ComposeError(f"tempo map beats must increase ({a[0]:g} -> {b[0]:g})")
            if curve == 'step' or a[1] == b[1]:
                seg = [a[0], b[0], a[1], a[1], 'const']
            else:
                seg = [a[0], b[0], a[1], b[1], curve]
            if segs and seg[4] == 'const' and segs[-1][4] == 'const' and segs[-1][2] == seg[2]:
                segs[-1][1] = seg[1]
            else:
                segs.append(seg)
        last = [points[-1][0], math.inf, points[-1][1], points[-1][1], 'const']
        if segs and segs[-1][4] == 'const' and segs[-1][2] == last[2]:
            segs[-1][1] = math.inf
        else:
            segs.append(last)
        t = 0.0
        for s in segs:
            s.append(t)
            if math.isfinite(s[1]):
                t = self._seg_seconds(s, s[1])
        self._segs = segs

    @property
    def constant(self) -> bool:
        return len(self._segs) == 1

    @property
    def min_bpm(self) -> float:
        return min(p[1] for p in self.points)

    @property
    def max_bpm(self) -> float:
        return max(p[1] for p in self.points)

    @staticmethod
    def _seg_seconds(s, beat: float) -> float:
        b0, b1, p0, p1, kind, t0 = s
        x = beat - b0
        if kind == 'const':
            return t0 + x * 60.0 / p0
        if kind == 'linear':
            k = (p1 - p0) / (b1 - b0)
            return t0 + 60.0 / k * math.log1p(k * x / p0)
        L = b1 - b0
        u = x / L
        if u <= 0:
            return t0
        if u >= 1:
            return t0 + 60.0 * L / math.sqrt(p0 * p1)
        return t0 + 120.0 * L / (math.pi * math.sqrt(p0 * p1)) * math.atan(math.sqrt(p1 / p0) * math.tan(0.5 * math.pi * u))

    def _seg(self, beat: float):
        s = self._segs[0]
        for seg in self._segs:
            if seg[0] <= beat:
                s = seg
            else:
                break
        return s

    def bpm_at(self, beat: float) -> float:
        """Tempo at a beat (from a 'step' point on: its new tempo)."""
        if beat < 0:
            return self._segs[0][2]
        b0, b1, p0, p1, kind, _ = self._seg(beat)
        if kind == 'const':
            return p0
        u = min(1.0, max(0.0, (beat - b0) / (b1 - b0)))
        return p0 + (p1 - p0) * (u if kind == 'linear' else 0.5 - 0.5 * math.cos(math.pi * u))

    def seconds_at(self, beat: float) -> float:
        """Song time of a beat (0 at beat 0)."""
        if beat < 0:
            return beat * 60.0 / self._segs[0][2]
        return self._seg_seconds(self._seg(beat), beat)

    def beat_at(self, seconds: float) -> float:
        """The beat at a song time."""
        if seconds < 0:
            return seconds * self._segs[0][2] / 60.0
        s = self._segs[0]
        for seg in self._segs:
            if seg[5] <= seconds:
                s = seg
            else:
                break
        b0, b1, p0, p1, kind, t0 = s
        t = seconds - t0
        if kind == 'const':
            return b0 + t * p0 / 60.0
        if kind == 'linear':
            k = (p1 - p0) / (b1 - b0)
            return b0 + p0 / k * math.expm1(k * t / 60.0)
        L = b1 - b0
        theta = t * math.pi * math.sqrt(p0 * p1) / (120.0 * L)
        if theta >= 0.5 * math.pi:
            return b1
        return b0 + L * (2.0 / math.pi) * math.atan(math.tan(theta) / math.sqrt(p1 / p0))

    def seconds_between(self, a: float, b: float) -> float:
        return self.seconds_at(b) - self.seconds_at(a)


# ------------------------------------------------------------------------------------------ tempo plan

class _Piece:
    """A stretch [a, b] of the tempo curve: kind 'const' | 'linear' | 'smooth' (exact engine segments) or
    'sampled' (any curve, written as points every SAMPLE beats) or 'fine' (every FINE beats: beat-level lilts);
    fn(beat) -> bpm."""

    __slots__ = ('a', 'b', 'kind', 'fn')

    def __init__(self, a, b, kind, fn):
        self.a, self.b, self.kind, self.fn = a, b, kind, fn


def _const(a, b, v):
    return _Piece(a, b, 'const', lambda x, v=v: v)


def _ramp(a, b, va, vb, curve):
    if va == vb:
        return _const(a, b, va)
    if curve == 'smooth':
        return _Piece(a, b, 'smooth', lambda x, a=a, b=b, va=va, vb=vb:
                      va + (vb - va) * (0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, (x - a) / (b - a))))))
    return _Piece(a, b, 'linear', lambda x, a=a, b=b, va=va, vb=vb: va + (vb - va) * min(1.0, max(0.0, (x - a) / (b - a))))


def _split(pieces, x):
    """Split the piece containing x (a < x < b) in two; a smooth curve cut in the middle becomes 'sampled'."""
    out = []
    for p in pieces:
        if p.a < x - 1e-9 and x < p.b - 1e-9:
            kind = 'sampled' if p.kind == 'smooth' else p.kind
            out.append(_Piece(p.a, x, kind, p.fn))
            out.append(_Piece(x, p.b, kind, p.fn))
        else:
            out.append(p)
    return out


def _scale(pieces, a, b, factor, keep_kind: bool, kind: str = 'sampled'):
    """Multiply the curve inside [a, b] by factor(beat) (constant factors keep exact segment kinds)."""
    pieces = _split(_split(pieces, a), b)
    out = []
    for p in pieces:
        if p.a >= a - 1e-9 and p.b <= b + 1e-9:
            k = p.kind if keep_kind or p.kind == 'fine' else kind
            out.append(_Piece(p.a, p.b, k, lambda x, f=p.fn, g=factor: f(x) * g(x)))
        else:
            out.append(p)
    return out


def _value(pieces, x):
    """The tempo from beat x on (after a jump at x: the new tempo)."""
    for p in pieces:
        if p.a <= x < p.b:
            return p.fn(x)
    return pieces[-1].fn(pieces[-1].a)


def _seconds(pieces, a, b, steps: int = 4096) -> float:
    """Seconds from beat a to b under the curve (Simpson on each piece: exact enough for fermata lengths)."""
    total = 0.0
    for p in pieces:
        lo, hi = max(a, p.a), min(b, p.b)
        if hi <= lo:
            continue
        n = max(2, steps - steps % 2)
        h = (hi - lo) / n
        s = 60.0 / p.fn(lo) + 60.0 / p.fn(hi)
        for i in range(1, n):
            s += (4.0 if i % 2 else 2.0) * 60.0 / p.fn(lo + i * h)
        total += s * h / 3.0
    return total


def _emit(pieces) -> list[list]:
    """Engine points for contiguous pieces (a jump between two pieces is a 'step' point; after a curved piece
    it arrives EPS beats early, so the new tempo starts exactly at the jump)."""
    pts: list[list] = []
    prev = None
    for p in pieces:
        va = p.fn(p.a)
        if not pts:
            pts.append([p.a, va, 'linear'])
        elif abs(pts[-1][1] - va) > 1e-9 * max(1.0, abs(va)):
            if prev.kind == 'const':
                if len(pts) > 1 and pts[-1][0] >= p.a - 1e-12:
                    pts.pop()          # the step holds the constant tempo up to the jump by itself
            elif pts[-1][0] >= p.a - 1e-12:
                x = p.a - EPS
                if len(pts) > 1 and x > pts[-2][0] + 1e-9:
                    pts[-1][0], pts[-1][1] = x, prev.fn(x)
                elif len(pts) > 1:
                    pts.pop()
            pts.append([p.a, va, 'step'])
        prev = p
        if not math.isfinite(p.b):
            break
        if p.kind == 'const':
            pts.append([p.b, va, 'linear'])
        elif p.kind in ('linear', 'smooth'):
            pts.append([p.b, p.fn(p.b), p.kind])
        else:
            n = max(2, int(math.ceil((p.b - p.a) / (FINE if p.kind == 'fine' else SAMPLE) - 1e-9)))
            for k in range(1, n + 1):
                x = p.a + (p.b - p.a) * k / n
                pts.append([x, p.fn(x), 'linear'])
    out: list[list] = []
    for b, v, c in pts:
        b, v = round(b, 6), round(v, 6)
        if out and b <= out[-1][0]:
            if c == 'step' or abs(v - out[-1][1]) > 1e-9:
                out[-1] = [out[-1][0], v] + (['step'] if c == 'step' else [])
            continue
        if out and len(out) > 1 and c == 'linear' and v == out[-1][1] == out[-2][1] and len(out[-1]) == 2:
            out[-1] = [b, v]         # a run of equal tempi: one constant stretch
            continue
        out.append([b, v] + ([c] if c != 'linear' else []))
    return out


def _shape(phrase: str, u: float) -> float:
    if phrase == 'arch':
        return math.sin(2.0 * math.pi * u)      # moves forward into the phrase, broadens towards its end
    if phrase == 'wave':
        return math.sin(4.0 * math.pi * u)      # two breaths
    if phrase == 'lean':
        return -math.sin(2.0 * math.pi * u)     # holds back first, then leans forward
    if phrase == 'breath':
        # a singer's / pianist's phrase: moves on gently through the first 60 % (up to 2/3 of the depth), then
        # broadens into its end (the full depth in the last 40 %: the breath before the next phrase); zero mean,
        # so the span keeps its length. Measured on a concert recording of Satie's Gymnopedie No. 1: phrase
        # middles +2.5 %, last bars -3.5 % (-8..-11 % at the big cadences) against the phrase's median tempo.
        if u < 0.6:
            return (2.0 / 3.0) * math.sin(math.pi * u / 0.6)
        return -math.sin(math.pi * (u - 0.6) / 0.4)
    return 0.0


def lilt_factor(delays, beat_in_bar: float, bar_len: float) -> float:
    """Tempo factor at `beat_in_bar` (0 .. bar_len) of a bar whose inner beats k = 1, 2, ... (quarter notes) arrive
    delays[k-1] beats late (negative: early); the downbeats stay. Between two beats the extra time is a smooth
    half-sine bump in 1/tempo, so the tempo is continuous and exactly the delay is taken (or given back) per beat."""
    m = len(delays)                                  # inner beats 1..m; the last interval runs from m to bar_len
    k = min(m, max(0, int(math.floor(beat_in_bar + 1e-12))))
    d0 = delays[k - 1] if k >= 1 else 0.0
    d1 = delays[k] if k < m else 0.0
    w = 1.0 if k < m else max(1e-6, bar_len - m)
    x = (beat_in_bar - k) / w
    inv = 1.0 + (d1 - d0) / w * 0.5 * math.pi * math.sin(math.pi * min(1.0, max(0.0, x)))
    return 1.0 / max(0.2, inv)


class TempoPlan:
    """The song's tempo events; points() turns them into engine tempo points."""

    def __init__(self):
        self.events: list[tuple] = []     # ('set', beat, bpm) | ('ramp', start, end, bpm, factor, curve, a_tempo, what)
        self.rubatos: list[tuple] = []    # (start, end, depth, phrase, seed)
        self.fermatas: list[tuple] = []   # (beat, hold, seconds, length)
        self.lilts: list[tuple] = []      # (start, end, [(bar start, bar length, [delay of inner beat 1, 2, ...])])

    def empty(self) -> bool:
        return not (self.events or self.rubatos or self.fermatas or self.lilts)

    # --- building
    def add_set(self, beat: float, bpm: float) -> None:
        self._check_free(beat, beat, f"set_tempo at beat {beat:g}")
        self.events = [e for e in self.events if not (e[0] == 'set' and abs(e[1] - beat) < 1e-9)]
        self.events.append(('set', beat, bpm))

    def add_ramp(self, start, end, bpm, factor, curve, a_tempo, what) -> None:
        if end <= start:
            raise ComposeError(f"{what}: the span {start:g}..{end:g} is empty (end must be after start)")
        self._check_free(start, end, what)
        self.events.append(('ramp', start, end, bpm, factor, curve, a_tempo, what))

    def _check_free(self, a, b, what) -> None:
        for e in self.events:
            if e[0] == 'ramp':
                s, t = e[1], e[2]
                inside = (s + 1e-9 < a < t - 1e-9) or (s + 1e-9 < b < t - 1e-9) or (a < s + 1e-9 and b > t - 1e-9 and b > a)
                if inside:
                    raise ComposeError(f"{what} overlaps {e[7]} (beats {s:g}..{t:g}); tempo ramps can't overlap other "
                                       f"tempo changes - end one where the next starts")
            elif e[0] == 'set' and a + 1e-9 < e[1] < b - 1e-9:
                raise ComposeError(f"{what} contains the tempo change set_tempo({e[1]:g}, {e[2]:g}); ramps can't "
                                   f"overlap other tempo changes")

    # --- evaluation
    def _fermata_span(self, beat: float, length, onsets) -> float:
        """Beats a fermata at `beat` stretches: length=, else to the next onset after its chord (notes within
        CHORD beats of it: strums, rolls), else to the end of the chord's longest note."""
        if length is not None:
            return length
        chord = [b + d for b, d in (onsets or []) if beat - 1e-6 <= b < beat + CHORD]
        later = [b for b, _ in (onsets or []) if b >= beat + CHORD]
        return (later[0] - beat) if later else (max(chord) - beat if chord else 1.0)

    def _a_tempo_at(self, t: float, onsets) -> float:
        """Where the tempo from before an a_tempo ritardando / accelerando ending at `t` returns: right at `t`,
        after the held chord when a fermata sits on `t` (rit. - fermata - a tempo), never (inf) when no note
        starts after the chord on `t` (the song's last chord keeps the slowed tempo, its tail too)."""
        if not onsets:
            # no notes placed yet (a song asking tempo_at() while it builds its parts - real-time ornaments,
            # fioriture): assume the music goes on, else every a-tempo ramp would keep its slowed tempo for good
            return t
        if not any(b >= t + CHORD for b, _ in onsets):
            return math.inf
        for beat, _, _, length in self.fermatas:
            if abs(beat - t) < 1e-6:
                return t + self._fermata_span(beat, length, onsets)
        return t

    def pieces(self, base: float, onsets=None) -> list[_Piece]:
        """The tempo curve: events, then rubato, then fermatas (onsets: sorted (beat, longest duration) of the
        song's notes, for fermatas without an explicit length and where an a_tempo ramp returns)."""
        cur, x, out = base, 0.0, []
        back = None   # (beat, bpm): an a_tempo ramp's return to the tempo from before it
        order = sorted(self.events, key=lambda e: (e[1], 0 if e[0] == 'set' else 1))  # a set, then a ramp from it
        for e in order:
            if back is not None:
                # the next change starts after the return: a tempo first; at / before it: it continues from the
                # slowed (or pushed) tempo, e.g. a second ritardando right after the first
                if e[1] > back[0] + 1e-9:
                    out.append(_const(x, back[0], cur))
                    x, cur = back[0], back[1]
                back = None
            if e[0] == 'set':
                if e[1] > x:
                    out.append(_const(x, e[1], cur))
                    x = e[1]
                cur = e[2]
                continue
            _, s, t, bpm, factor, curve, a_tempo, what = e
            if s > x:
                out.append(_const(x, s, cur))
                x = s
            target = bpm if bpm is not None else cur * factor
            if not MIN_BPM <= target <= MAX_BPM:
                raise ComposeError(f"{what}: the target tempo {target:g} BPM is outside {MIN_BPM:g}..{MAX_BPM:g}")
            out.append(_ramp(s, t, cur, target, curve))
            if a_tempo:
                back = (self._a_tempo_at(t, onsets), cur)
            x, cur = t, target
        if back is not None and math.isfinite(back[0]):
            if back[0] > x:
                out.append(_const(x, back[0], cur))
                x = back[0]
            cur = back[1]
        out.append(_const(x, math.inf, cur))
        for s, t, depth, phrase, seed in self.rubatos:
            rng = random.Random(seed)
            amps = [rng.uniform(-1.0, 1.0) for _ in range(4)]

            def factor(b, s=s, t=t, depth=depth, phrase=phrase, amps=amps):
                u = min(1.0, max(0.0, (b - s) / (t - s)))
                noise = sum(a * math.sin(2.0 * math.pi * m * u) / m for m, a in zip((2, 3, 4, 5), amps))
                return min(1.5, max(0.5, 1.0 + depth * (_shape(phrase, u) + 0.5 * noise)))
            out = _scale(out, s, t, factor, keep_kind=False)
        for s, t, bars in self.lilts:
            starts = [b0 for b0, _, _ in bars]

            def lfactor(b, bars=bars, starts=starts):
                i = max(0, min(len(bars) - 1, _bisect(starts, b) - 1))
                b0, L, delays = bars[i]
                if not b0 - 1e-9 <= b <= b0 + L + 1e-9:
                    return 1.0
                return lilt_factor(delays, b - b0, L)
            out = _scale(out, s, t, lfactor, keep_kind=False, kind='fine')
        spans = []
        for beat, hold, seconds, length in sorted(self.fermatas):
            L = self._fermata_span(beat, length, onsets)
            end = beat + L
            for a, b in spans:
                if beat < b - 1e-9 and end > a + 1e-9:
                    raise ComposeError(f"fermata at beat {beat:g} (holding {L:g} beats) overlaps the fermata at beat {a:g}; "
                                       f"give length= to shorten one")
            spans.append((beat, end))
            d0 = _seconds(out, beat, end)
            extra = seconds if seconds is not None else hold * 60.0 / _value(out, beat)
            f = d0 / (d0 + extra)
            if _value(out, beat) * f < 2.0:
                why = "the span ends at the next note onset" if length is None else "length="
                raise ComposeError(f"fermata at beat {beat:g}: holding {L:g} beats ({why}) {extra:.2f} s longer would need "
                                   f"{_value(out, beat) * f:.2g} BPM; give length= (the beats to stretch) or a shorter hold")
            out = _scale(out, beat, end, lambda b, f=f: f, keep_kind=True)
        return out

    def needs_onsets(self) -> bool:
        """Whether points() depends on the song's note onsets (fermata spans, a_tempo returns)."""
        return bool(self.fermatas) or any(e[0] == 'ramp' and e[6] for e in self.events)

    def points(self, base: float, onsets=None) -> list[list]:
        """Engine tempo points ([[0, base]] when nothing changes the tempo)."""
        if self.empty():
            return [[0.0, float(base)]]
        pts = _emit(self.pieces(base, onsets))
        for b, v, *_ in pts:
            if not 1.0 <= v <= 1000.0:
                raise ComposeError(f"the tempo map reaches {v:g} BPM at beat {b:g} (the engine renders 1..1000 BPM); "
                                   f"shorten the fermata / ramp there")
        return pts


def render_seconds(render: dict, beat: float) -> float:
    """Song seconds of a beat for a render dict ("tempo" or "tempoMap")."""
    if 'tempoMap' in render:
        return TempoMap(render['tempoMap']).seconds_at(beat)
    return beat * 60.0 / render['tempo']
