"""Played, not triggered: per-note articulations, legato, portamento, expression and vibrato for sampled
instruments (the 'sampler': inst.sfz / inst.sfz_multi / the sampled/* patches).

    from agentsound import articulation as art

    vln = s.track('violin', 'sampled/solo_violin')        # mono='legato', live dynamics, keyswitched articulations
    line = s.motif('...').clip(octave=5)
    art.perform(vln, line, verse)                         # everything below in one call

    line = art.legato(line)                               # tie phrases: overlapping notes -> legato transitions
    line = line.articulate('staccato', span=(8, 12))      # per-note articulation -> keyswitch notes at compile
    line = art.auto_articulate(line, vln)                 # short -> staccato / spiccato, long -> sustain, accents -> marcato
    line = line.glide(150, where=art.leaps(5))            # portamento into leaps of a 4th or more
    vln.play(line, verse)
    art.expression(vln, line, verse)                      # per-note shapes (swell, fp, sfz, dim ...) on 'dynamics'
    art.vibrato(vln, line, verse)                         # delayed vibrato on long notes ('vibrato' param)

How it reaches the engine (docs/COMPOSE_API.md "Realistic performance"):
  - articulations and glides are marks on the notes (a Note subclass: transforms built on _replace - shift, transpose,
    velocity, gate, legato, humanize, swing, slice, loop, track.groove - keep them; building fresh notes drops them).
    Song.compile turns articulations into keyswitch notes (at exactly the note's start, held until the next switch,
    never sounding: the sampler selects zones by swLast) and glides into steps of the sampler's 'glide' param just
    before the note;
  - legato: overlapping notes on a sampler with mono='legato' play legato transitions (legato() makes them overlap);
  - expression / vibrato: automation of 'instrument.dynamics' (0..1: live layer crossfades, tone, level) and
    'instrument.vibrato' / 'instrument.vibratorate'.
"""

from __future__ import annotations

import math
import random

from .patterns import Clip, Note, as_clip, beats, seed_int
from .theory import ComposeError
from .theory import note as _note_number

__all__ = ['ARTICULATION_WORDS', 'SHAPES', 'articulate', 'articulation_of', 'glide', 'glide_of', 'note', 'plain',
           'leaps', 'detached', 'legato', 'bow_changes', 'humanize_starts', 'available', 'live_dynamics',
           'auto_articulate', 'expression_points', 'expression', 'vibrato_points', 'vibrato', 'vibrato_prefixes',
           'perform', 'throws']

_EPS = 1e-6

ARTICULATION_WORDS = {
    'long': ('sustain', 'sus', 'arco', 'long', 'legato', 'vibrato', 'vib', 'normal', 'ordinario', 'ord'),
    'short': ('staccato', 'stac', 'spiccato', 'spic', 'short', 'detache', 'staccatissimo'),
    'accent': ('marcato', 'marc', 'accent', 'sforzando', 'sfz'),
    'pizz': ('pizzicato', 'pizz', 'plucked', 'pluck'),
    'trem': ('tremolo', 'trem'),
}
"""Words sample libraries use for the same kind of articulation (auto_articulate picks by them)."""


# ----------------------------------------------------------------------------------------------- marks

_CLASSES: dict[tuple, type] = {}
_KEEP = object()


def _cls(art, gl) -> type:
    key = (art, gl)
    c = _CLASSES.get(key)
    if c is None:
        label = '|'.join(x for x in (str(art) if art is not None else '', f"glide {gl:g} ms" if gl else '') if x)
        c = type(f"Note[{label}]", (Note,), {'__slots__': (), 'art': art, 'glide': gl})
        _CLASSES[key] = c
    return c


def _mark(n, art=_KEEP, gl=_KEEP) -> Note:
    a = getattr(n, 'art', None) if art is _KEEP else art
    g = getattr(n, 'glide', None) if gl is _KEEP else gl
    if a is None and not g:
        return Note(*tuple(n))
    return _cls(a, g)(*tuple(n))


def articulation_of(n) -> str | int | None:
    """The articulation mark of a note (None: the instrument's default articulation)."""
    return getattr(n, 'art', None)


def glide_of(n) -> float | None:
    """The portamento mark of a note in ms (None: no glide into it)."""
    return getattr(n, 'glide', None)


def _art_name(name) -> str | int:
    if isinstance(name, bool) or not isinstance(name, (str, int)):
        raise ComposeError(f"articulation must be a name like 'staccato' (or a keyswitch key / note name), got {name!r}")
    if isinstance(name, int):
        if not 0 <= name <= 127:
            raise ComposeError(f"articulation keyswitch key must be 0..127, got {name}")
        return name
    text = name.strip().lower()
    if not text:
        raise ComposeError("articulation name must not be empty")
    return text


class leaps:
    """where= selector for notes that leap at least `semitones` from the previous note (glide(), articulate()):
    line.glide(150, where=art.leaps(5)). The previous note is the highest one starting before."""

    def __init__(self, semitones: int = 5):
        self.semitones = int(semitones)
        self.prev: dict | None = None

    def bind(self, clip) -> 'leaps':
        ns = sorted(clip, key=lambda n: (n.start, n.pitch))
        self.prev = {}
        last = None
        for n in ns:
            if last is not None and n.start > last.start + _EPS:
                self.prev[(round(n.start, 9), n.pitch)] = last.pitch
            if last is None or n.start > last.start + _EPS or n.pitch > last.pitch:
                last = n
        return self

    def __call__(self, n) -> bool:
        if self.prev is None:
            raise ComposeError("leaps() is a where= selector for glide() / articulate() (they give it the clip)")
        p = self.prev.get((round(n.start, 9), n.pitch))
        return p is not None and abs(n.pitch - p) >= self.semitones


def _selector(c: Clip, where, span, pitches):
    lo, hi = (-math.inf, math.inf) if span is None else (float(span[0]), float(span[1]))
    ps = None
    if pitches is not None:
        seq = pitches if isinstance(pitches, (list, tuple, set)) else [pitches]
        ps = {p if isinstance(p, int) else _note_number(p) for p in seq}
    if where is not None and not callable(where):
        raise ComposeError(f"where= must be a function Note -> bool, got {where!r}")
    if isinstance(where, leaps):
        where = leaps(where.semitones).bind(c)

    def ok(n) -> bool:
        return lo - _EPS <= n.start < hi - _EPS and (ps is None or n.pitch in ps) and (where is None or where(n))
    return ok


def articulate(clip, name, *, where=None, span=None, pitches=None) -> Clip:
    """Mark notes with an articulation ('staccato', 'pizzicato', a label (or part of one) of the instrument's
    keyswitches, or a keyswitch key / note name). All notes, or those in span=(start, end) beats / with pitches= /
    where(note). None removes the mark (the instrument's default). Also a Clip method: clip.articulate('staccato')."""
    c = as_clip(clip)
    a = None if name is None else _art_name(name)
    ok = _selector(c, where, span, pitches)
    return Clip._raw([_mark(n, art=a) if ok(n) else n for n in c], c.length)


def glide(clip, ms: float = 120.0, *, where=None, span=None, pitches=None) -> Clip:
    """Mark notes to glide into: portamento of `ms` from the previous note (the sampler with mono='legato' bends the
    old note to the new pitch and the new one in from the old pitch while crossfading; the notes must overlap their
    predecessor - legato()). Chosen as in articulate(); where=leaps(5): leaps of a 4th or more. ms=0 / None removes
    the mark. Also a Clip method: clip.glide(150, where=leaps(5))."""
    c = as_clip(clip)
    g = None
    if ms:
        if isinstance(ms, bool) or not isinstance(ms, (int, float)) or not 0 < ms <= 2000:
            raise ComposeError(f"glide ms must be 0..2000, got {ms!r}")
        g = float(ms)
    ok = _selector(c, where, span, pitches)
    return Clip._raw([_mark(n, gl=g) if ok(n) else n for n in c], c.length)


def plain(clip) -> Clip:
    """The clip without articulation / glide marks."""
    c = as_clip(clip)
    return Clip._raw([Note(*tuple(n)) for n in c], c.length)


def note(start, dur, pitch, vel: int = 100, art=None, glide_ms=None) -> Note:
    """One note with an articulation / glide mark: Clip._raw([art.note(0, 0.5, 'A4', 90, 'staccato'), ...], 4) (the
    Clip() constructor rebuilds plain notes; articulate() a clip instead)."""
    n = as_clip([(start, dur, pitch, vel)])[0]
    return _mark(n, art=None if art is None else _art_name(art), gl=float(glide_ms) if glide_ms else None)


# ----------------------------------------------------------------------------------------------- phrasing

def detached(n) -> bool:
    """A note (or an articulation name) marked with a detached articulation (staccato / spiccato, pizzicato, marcato
    ...: ARTICULATION_WORDS 'short', 'pizz', 'accent'): legato() does not tie into or out of it, and on a mono='legato'
    sampler the compiler keeps it from touching the next note."""
    a = n if isinstance(n, str) else articulation_of(n)
    if not isinstance(a, str):
        return False
    ws = _words(a)
    return any(w == x or x.startswith(w) for kind in ('short', 'pizz', 'accent') for w in ARTICULATION_WORDS[kind]
               for x in ws)


def legato(clip, overlap: float = 0.03, max_gap='1/16') -> Clip:
    """Tie the notes of each phrase for a monophonic legato player: a note lasts until the next onset + `overlap`
    beats when that onset comes less than `max_gap` beats after its written end (so the sampler's mono='legato' plays
    a transition instead of a new attack); phrase ends (longer rests) keep their length, and notes marked detached
    (staccato, spiccato, pizzicato, marcato: articulate() them first) are neither tied nor tied into. Marks are kept."""
    c = as_clip(clip)
    g = beats(max_gap)
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    out = []
    for i, n in enumerate(ns):
        nxt = next((m for m in ns[i + 1:] if m.start > n.start + _EPS), None)
        if (nxt is not None and nxt.start - (n.start + n.dur) < g - _EPS and not detached(n) and not detached(nxt)):
            n = n._replace(dur=max(n.dur, nxt.start - n.start + overlap))
        out.append(n)
    return Clip._raw(out, c.length)


def bow_changes(clip, bpm: float, max_seconds: float = 4.0, gap_ms: float = 40.0) -> Clip:
    """Bow changes / breaths in long legato lines: when a tied line (overlapping notes) has run longer than
    `max_seconds`, the note before the next note ends `gap_ms` early - that note re-attacks (a new bow stroke or
    breath) instead of a legato transition. Long single notes are left alone."""
    c = as_clip(clip)
    spb = 60.0 / _num(bpm, 'bow_changes bpm', 20, 400)
    gap = _num(gap_ms, 'gap_ms', 0, 1000) / 1000.0 / spb
    limit = _num(max_seconds, 'max_seconds', 0.5, 120) / spb
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    out = list(ns)
    line_start = None
    for i, n in enumerate(ns):
        nxt = ns[i + 1] if i + 1 < len(ns) else None
        if line_start is None:
            line_start = n.start
        if nxt is None or n.start + n.dur <= nxt.start + _EPS:
            line_start = None
            continue
        if nxt.start - line_start > limit:
            out[i] = n._replace(dur=max(0.05, nxt.start - gap - n.start))
            line_start = None
    return Clip._raw(out, c.length)


def humanize_starts(clip, bpm: float, ms: float = 8.0, late_ms: float = 0.0, seed=0) -> Clip:
    """A player's timing: every note starts late_ms later (the part's lay-back; negative = ahead) plus a seeded
    triangular jitter of +-ms, while its END stays put - phrase lengths survive (track.humanize() moves whole notes)
    and a note tied into the next one (a legato overlap) keeps its overlap with that note's new start. Notes
    starting together move together (one hand / one bow)."""
    c = as_clip(clip)
    spb = 60.0 / _num(bpm, 'humanize_starts bpm', 20, 400)
    jit = _num(ms, 'ms', 0, 60) / 1000.0 / spb
    late = _num(late_ms, 'late_ms', -60, 150) / 1000.0 / spb
    rng = random.Random(seed_int(seed))
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    shift: dict[float, float] = {}
    for n in ns:
        key = round(n.start, 6)
        if key not in shift:
            shift[key] = late + (rng.random() + rng.random() - 1.0) * jit
    onsets = sorted(shift)
    out = []
    for n in ns:
        key = round(n.start, 6)
        start = max(0.0, n.start + shift[key])
        end = n.start + n.dur
        nxt = next((o for o in onsets if o > key + _EPS), None)
        if nxt is not None and end > nxt + _EPS:       # tied into the next onset: keep the overlap
            end = max(end, max(0.0, nxt + shift[nxt]) + (end - nxt))
        out.append(n._replace(start=start, dur=max(end - start, min(n.dur, 0.02))))
    return Clip._raw(out, c.length)


# ----------------------------------------------------------------------------------------------- articulations

def available(sound) -> list[str]:
    """Articulation names of a sound (a Track, Patch, Instrument or instrument dict): the keyswitch labels of an
    inst.sfz / inst.sfz_multi sampler ([] when it has none). Reads a lazy .sfz now."""
    from .patches import Instrument
    ins = getattr(sound, 'instrument', sound)
    if isinstance(ins, dict):
        ins = Instrument.coerce(ins)
    if not isinstance(ins, Instrument) or ins.type != 'sampler':
        return []
    ins.expand()
    info = (ins.info or {}).get('sfz') or {}
    return list((info.get('keyswitches') or {}).keys())


def _words(name: str) -> list[str]:
    return [w for w in name.lower().replace('-', ' ').replace('_', ' ').replace('(', ' ').replace(')', ' ').split() if w]


def _pick(names: list[str], kind: str) -> str | None:
    """The articulation of `names` that is of `kind` (ARTICULATION_WORDS): by whole words first, then by prefix."""
    for w in ARTICULATION_WORDS[kind]:
        for n in names:
            if w in _words(n):
                return n
    for w in ARTICULATION_WORDS[kind]:
        for n in names:
            if any(x.startswith(w) for x in _words(n)):
                return n
    return None


def auto_articulate(clip, sound=None, *, names=None, short=0.5, bpm: float | None = None, short_ms: float | None = None,
                    accent_vel: int | None = 112, keep: bool = True) -> Clip:
    """Choose an articulation per note from what the instrument has (`sound`: a Track / Patch / Instrument, or
    names=[...]): short notes (shorter than `short` beats - or short_ms with bpm - and not tied to the next) ->
    staccato / spiccato, accents (velocity >= accent_vel, not long) -> marcato, the rest -> the sustain articulation
    (marked explicitly). Kinds the instrument lacks are left unmarked (its default); keep=True leaves notes that
    already carry a mark."""
    c = as_clip(clip)
    avail = list(names) if names is not None else available(sound)
    if not avail:
        raise ComposeError("auto_articulate: the sound has no keyswitch articulations (inst.sfz of a keyswitch program, "
                           "or inst.sfz_multi({'sustain': ..., 'staccato': ...})); or pass names=[...]")
    lim = beats(short)
    if short_ms is not None:
        if bpm is None:
            raise ComposeError("auto_articulate: short_ms needs bpm=")
        lim = _num(short_ms, 'short_ms', 1, 5000) / 1000.0 * _num(bpm, 'bpm', 20, 400) / 60.0
    s_name, a_name, l_name = _pick(avail, 'short'), _pick(avail, 'accent'), _pick(avail, 'long')
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    out = []
    for i, n in enumerate(ns):
        if keep and articulation_of(n) is not None:
            out.append(n)
            continue
        nxt = next((m for m in ns[i + 1:] if m.start > n.start + _EPS), None)
        tied = nxt is not None and n.start + n.dur > nxt.start + _EPS
        kind = None
        if not tied and n.dur < lim - _EPS and s_name:
            kind = s_name
        elif accent_vel is not None and n.vel >= accent_vel and a_name and n.dur < 2.0 * lim + _EPS:
            kind = a_name
        elif l_name:
            kind = l_name
        out.append(_mark(n, art=_art_name(kind)) if kind else n)
    return Clip._raw(out, c.length)


# ----------------------------------------------------------------------------------------------- expression

SHAPES = ('flat', 'swell', 'cresc', 'dim', 'fp', 'sfz', 'accent')
"""Per-note dynamics shapes: flat (the velocity's level), swell (<> soft - peak at 55 % - softer), cresc (<), dim (>),
fp (forte attack, piano at once), sfz (sforzando: a strong attack falling back), accent (a lighter sfz)."""


def _shape(kind: str, d: float) -> list[tuple[float, float, str]]:
    """(offset beats, level factor, curve) keypoints of a shape on a note of d beats."""
    t = min(0.25, 0.3 * d)
    shapes = {
        'flat': [(0.0, 1.0, 'step')],
        'swell': [(0.0, 0.55, 'step'), (0.55 * d, 1.12, 'smooth'), (d, 0.6, 'smooth')],
        'cresc': [(0.0, 0.5, 'step'), (d, 1.2, 'smooth')],
        'dim': [(0.0, 1.0, 'step'), (d, 0.45, 'smooth')],
        'fp': [(0.0, 1.1, 'step'), (t, 0.4, 'smooth')],
        'sfz': [(0.0, 1.3, 'step'), (min(0.4, 0.35 * d), 0.62, 'smooth')],
        'accent': [(0.0, 1.15, 'step'), (t, 1.0, 'smooth')],
    }
    if kind not in shapes:
        raise ComposeError(f"expression shape must be one of {', '.join(SHAPES)}, got {kind!r}")
    return shapes[kind]


def expression_points(clip, shapes='auto', *, lo: float = 0.2, hi: float = 1.0, long=1.5, accent_vel: int = 112,
                      at=0.0, follow=None, follow_step: float = 1.0, follow_min: float = 1.0) -> list:
    """Automation points (beat, value 0..1, curve) for the sampler's 'dynamics' from a line: each note sits at its
    velocity's level (lo + (hi - lo) x vel / 127) shaped by `shapes`: one of SHAPES for every note, a list (per note
    in time order, None = flat), a dict {note index: shape}, a function Note -> shape, or 'auto' (notes of at least
    `long` beats swell, accents (vel >= accent_vel) get 'accent', the rest flat). A shape is cut where the next note
    starts; a note tied to the one before (overlapping it: a legato line) continues from where that one ended and
    moves to its own level / shape (no step at a legato transition), a note after a rest starts at its level.
    follow: a function of the song beat -> a level (a velocity: a whole piece's dynamics map, orch.Score.level):
    a note of `follow_min` beats or more whose level changes inside it by more than 3 % FOLLOWS it (a held chord
    through a written crescendo grows; points every `follow_step` beats) instead of its shape.
    Positions: the clip's own + at (a beat or Section)."""
    c = as_clip(clip)
    a0 = _pos(at)
    lo, hi = _num(lo, 'lo', 0, 1), _num(hi, 'hi', 0, 1)
    L = beats(long)
    ns = sorted(c, key=lambda n: (n.start, -n.pitch))
    firsts = []
    for n in ns:                       # one shape per onset: chords follow their top note
        if not firsts or n.start > firsts[-1].start + _EPS:
            firsts.append(n)
    clamp = lambda x: round(min(1.0, max(0.0, x)), 5)  # noqa: E731
    pts: list = []
    last = None                        # (value, end beat) of the previous note's shape
    for k, n in enumerate(firsts):
        if callable(shapes):
            kind = shapes(n) or 'flat'
        elif isinstance(shapes, dict):
            kind = shapes.get(k) or 'flat'
        elif isinstance(shapes, (list, tuple)):
            kind = (shapes[k] if k < len(shapes) else None) or 'flat'
        elif shapes == 'auto':
            kind = 'swell' if n.dur >= L - _EPS else ('accent' if n.vel >= accent_vel else 'flat')
        else:
            kind = shapes
        cut = min(n.dur, firsts[k + 1].start - n.start) if k + 1 < len(firsts) else n.dur
        b = lo + (hi - lo) * n.vel / 127.0
        keys = [(off, b * f, curve) for off, f, curve in _shape(kind, n.dur)]
        prev_n = firsts[k - 1] if k > 0 else None
        tied = prev_n is not None and last is not None and prev_n.start + prev_n.dur > n.start + _EPS
        followed = False
        if follow is not None and n.dur >= follow_min - _EPS:
            ref = follow(a0 + n.start) or 1e-9
            xs = sorted({min(n.dur, j * follow_step) for j in range(1, int(n.dur / follow_step) + 1)} | {n.dur})
            rs = [(x, follow(a0 + n.start + x) / ref) for x in xs]
            if max(abs(r - 1.0) for _, r in rs) > 0.03:
                followed = True
                lvl = lambda r: lo + (hi - lo) * min(127.0, n.vel * r) / 127.0  # noqa: E731
                keys = [(0.0, last[0] if tied else b, 'linear' if tied else 'step')] +                     [(x, lvl(r), 'linear') for x, r in rs]
        if followed:
            pass
        elif tied and kind in ('flat', 'swell', 'cresc', 'dim'):
            settle = min(0.3, 0.3 * n.dur)
            if kind == 'flat':      # glide from the line's level to the note's own
                keys = [(0.0, last[0], 'linear'), (settle, b, 'smooth')]
            else:                   # the shape moves on from the line's level
                keys = [(0.0, last[0], 'linear')] + keys[1:]
        prev = None
        for off, v, curve in keys:
            if off > cut + _EPS:            # cut: the value where the next note takes over (linear between keypoints)
                if prev is not None:
                    x = (cut - prev[0]) / max(off - prev[0], 1e-9)
                    v = prev[1] + (v - prev[1]) * x
                    pts.append((a0 + n.start + cut, clamp(v), curve))
                    prev = (cut, v)
                break
            pts.append((a0 + n.start + off, clamp(v), curve))
            prev = (off, v)
        last = (clamp(prev[1]), n.start + cut) if prev is not None else None
    return pts


_DYN_ZONE_KEYS = ('xfinLoDyn', 'xfinHiDyn', 'xfoutLoDyn', 'xfoutHiDyn', 'dynGain', 'dynCutoff')


def live_dynamics(sound) -> bool:
    """Does 'dynamics' move the LEVEL of this sampler (a Track, Patch or Instrument)? True with layers='dynamics',
    dynrange > 0 or zones mapped to it (dynGain, xf..Dyn crossfades, dynCutoff: an inst.sfz with a dynamics
    controller). Otherwise 'dynamics' only tilts the tone and expression() writes 'expression' instead. Reads a lazy
    .sfz now."""
    from .patches import Instrument
    ins = getattr(sound, 'instrument', sound)
    if isinstance(ins, dict):
        ins = Instrument.coerce(ins)
    if not isinstance(ins, Instrument) or ins.type != 'sampler':
        return False
    p = ins.params
    if p.get('layers') == 'dynamics' or (isinstance(p.get('dynrange'), (int, float)) and p.get('dynrange') > 0):
        return True
    ins.expand()
    zones = ins.params.get('samples')
    zones = zones if isinstance(zones, list) else [zones] if isinstance(zones, dict) else []
    return any(k in z for z in zones if isinstance(z, dict) for k in _DYN_ZONE_KEYS)


def _track_param(track, target: str | None) -> str:
    if target:
        return target if target.startswith('instrument.') else f"instrument.{target}"
    return 'instrument.dynamics' if live_dynamics(track) else 'instrument.expression'


def expression(track, clip, at=0.0, shapes='auto', *, target: str | None = None, **kw):
    """Write expression_points() of a line placed at `at` (a beat or Section) as automation of `target` (default:
    'dynamics' on a sampler whose dynamics move its level - live layer crossfades, tone and level: live_dynamics() -,
    else 'expression'). Returns the track."""
    pts = expression_points(clip, shapes, at=at, **kw)
    if pts:
        track.automate(_track_param(track, target), pts)
    return track


def vibrato_points(clip, bpm: float, *, depth: float = 18.0, rate: float = 5.2, delay: float = 0.35, grow: float = 0.6,
                   min_dur=0.75, rise: float = 0.5, spread: float = 0.2, seed=0, at=0.0) -> dict:
    """Delayed vibrato per long note: {'instrument.vibrato': depth points (cents), 'instrument.vibratorate': rate
    points (Hz)}. Notes of at least `min_dur` beats: a straight tone for `delay` s, then the depth grows to `depth`
    cents (+- spread, seeded) over `grow` s and dies at the note end (or where the next note takes over); the rate
    starts at `rate` Hz and speeds up by up to `rise` Hz over the note (the vibrato intensifies). Other notes: none."""
    c = as_clip(clip)
    bps = _num(bpm, 'vibrato bpm', 20, 400) / 60.0
    a0 = _pos(at)
    rng = random.Random(seed_int(seed))
    ns = sorted(c, key=lambda n: (n.start, -n.pitch))
    firsts = []
    for n in ns:
        if not firsts or n.start > firsts[-1].start + _EPS:
            firsts.append(n)
    dpts: list = [(a0 + firsts[0].start, 0.0)] if firsts else []
    rpts: list = []
    for k, n in enumerate(firsts):
        end = min(n.start + n.dur, firsts[k + 1].start) if k + 1 < len(firsts) else n.start + n.dur
        if n.dur < beats(min_dur) - _EPS:
            continue
        s, e = a0 + n.start, a0 + end
        d0, d1 = s + delay * bps, s + (delay + grow) * bps
        off = e - 0.06 * bps
        if off <= d0 + _EPS:
            continue
        dep = depth * (1.0 + spread * (2.0 * rng.random() - 1.0))
        top = dep if off >= d1 else dep * (off - d0) / (d1 - d0)
        dpts += [(s, 0.0, 'step'), (d0, 0.0), (min(d1, off), round(top, 3), 'smooth'), (off, round(top, 3)),
                 (e, 0.0, 'smooth')]
        r0 = rate * (1.0 + 0.5 * spread * (2.0 * rng.random() - 1.0))
        rpts += [(s, round(r0, 3), 'step'), (e, round(r0 + rise * min(1.0, (e - s) / bps / 3.0), 3))]
    if not rpts:
        return {}
    return {'instrument.vibrato': dpts, 'instrument.vibratorate': rpts}


def vibrato_prefixes(sound) -> list:
    """Where a track's (Patch's, Instrument's) vibrato lives: ['instrument'] on a sampler, one
    'instrument.layers.<id>' per sampler layer of a stack (a layered sax: every take gets the vibrato), [] else."""
    ins = getattr(sound, 'instrument', sound)
    t = getattr(ins, 'type', None)
    if t == 'sampler':
        return ['instrument']
    if t == 'stack':
        return [f'instrument.layers.{x.id}' for x in ins.layers
                if x.id is not None and getattr(x.instrument, 'type', None) == 'sampler']
    return []


def vibrato(track, clip, at=0.0, **kw):
    """Write vibrato_points() of a line placed at `at` on a sampler track ('vibrato' / 'vibratorate' params) - on a
    stack track (layered/hero_sax ...) on every sampler layer; the tempo comes from the track's song. Returns the
    track."""
    bpm = kw.pop('bpm', None) or track._song.tempo
    prefixes = vibrato_prefixes(track) or ['instrument']
    for target, pts in vibrato_points(clip, bpm, at=at, **kw).items():
        for pre in prefixes:
            track.automate(pre + target[len('instrument'):], pts)
    return track


# ----------------------------------------------------------------------------------------------- all at once

def perform(track, clip, at=0.0, *, tie: bool = True, overlap: float = 0.03, articulations='auto', short=0.5,
            accent_vel: int = 112, glide_leaps: int | None = None, glide_ms: float = 110.0, shapes='auto',
            vib: bool | dict = True, humanize_ms: float = 6.0, late_ms: float = 0.0, bow_seconds: float | None = None,
            seed=0) -> Clip:
    """Play a written line on a track like a player. tie: legato phrases (overlapping notes -> legato transitions on
    a mono='legato' sampler); bow_seconds: a bow change / breath after that much tied line (None: off);
    articulations: 'auto' = auto_articulate() when the instrument has keyswitches, a name for every note, None =
    leave the marks as they are; glide_leaps: portamento (glide_ms) into leaps of at least that many semitones;
    humanize_ms / late_ms: a player's timing (humanize_starts); shapes: dynamics shapes (expression(); 'auto' swells
    long notes, None: none); vib: delayed vibrato on long notes (True, a dict of vibrato_points() options, False).
    Returns the clip as played (placed at `at`)."""
    bpm = track._song.tempo
    c = as_clip(clip)
    if articulations == 'auto':            # on the written durations, before the phrases are tied
        if available(track):
            c = auto_articulate(c, track, short=short, accent_vel=accent_vel)
    elif articulations is not None:
        c = articulate(c, articulations)
    if tie:
        c = legato(c, overlap=overlap)
    if bow_seconds:
        c = bow_changes(c, bpm, bow_seconds)
    if glide_leaps:
        c = glide(c, glide_ms, where=leaps(int(glide_leaps)))
    if humanize_ms or late_ms:
        c = humanize_starts(c, bpm, humanize_ms, late_ms, seed=seed)
    track.play(c, at)
    if shapes is not None:
        expression(track, c, at, shapes, accent_vel=accent_vel)
    if vib and vibrato_prefixes(track):
        opts = dict(vib) if isinstance(vib, dict) else {}
        opts.setdefault('seed', seed)
        vibrato(track, c, at, **opts)
    return c


def throws(track, clip, at=0.0, *, bus='echo', base: float | None = None, throw: float = -8.0,
           min_rest: float = 0.75, min_dur: float = 0.5) -> list:
    """Delay throws at phrase ends (the producer's hand on the echo send): 'send.<bus>' rises from `base` (default:
    the track's static send to that bus, else -60) to `throw` dB over the last note of every phrase - a note of at
    least `min_dur` beats followed by `min_rest` beats of rest, or the line's last note - and falls back when the
    note ends (at the latest just before the next phrase starts), so only the held phrase ends echo into the gap.
    A send lane replaces the static send: automate every stretch of the track through this (or give `base`).
    Returns the phrase-end notes that got a throw."""
    c = as_clip(clip)
    a0 = _pos(at)
    bid = getattr(bus, 'id', bus)
    if base is None:
        base = float(getattr(track, 'sends', {}).get(bid, -60.0))
    base, throw = _num(base, 'throws base', -60, 12), _num(throw, 'throws throw', -60, 12)
    ns = sorted(c, key=lambda n: n.start)
    starts = sorted({round(n.start, 6) for n in ns})
    ends, pts = [], []
    for n in ns:
        nxt = next((s for s in starts if s > n.start + _EPS), None)
        if n.dur < min_dur - _EPS or (nxt is not None and nxt - (n.start + n.dur) < min_rest - _EPS):
            continue
        s, e = a0 + n.start, a0 + n.start + n.dur
        stop = e + 0.25 if nxt is None else min(e + 0.25, a0 + nxt - 0.1)
        up = s + min(0.25, 0.4 * n.dur)
        if stop <= up + 0.05:
            continue
        pts += [(s, base), (up, throw, 'smooth'), (stop - 0.05, throw), (stop, base, 'smooth')]
        ends.append(n)
    if pts:
        track.automate(f'send.{bid}', pts)
    return ends


# ----------------------------------------------------------------------------------------------- utilities

def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        raise ComposeError(f"{what} = {x:g} is outside {lo:g}..{hi:g}")
    return float(x)


def _pos(x) -> float:
    if hasattr(x, 'start') and not isinstance(x, (int, float)):
        return float(x.start)
    return _num(x, 'position (beats)')


def _clip_articulate(self, name, **kw) -> Clip:
    return articulate(self, name, **kw)


def _clip_glide(self, ms: float = 120.0, **kw) -> Clip:
    return glide(self, ms, **kw)


_clip_articulate.__doc__, _clip_glide.__doc__ = articulate.__doc__, glide.__doc__
Clip.articulate = _clip_articulate      # clip.articulate('staccato', span=(8, 12))
Clip.glide = _clip_glide                # clip.glide(150, where=leaps(5))
