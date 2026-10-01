"""Jazz toolkit: a New York bar trio / quartet (piano, upright bass, brushes, tenor sax) in one namespace.

    from agentsound import *
    from agentsound import jazz

    s = Song('Blue Room', tempo=138, key='F major', seed=7)
    head = s.section('head', bars=32)
    b = jazz.band(s, sax=True)                        # piano (comp + right hand), bass, brushes, tenor, room reverb
                                                      # (the sampled packs when installed, else GeneralUser GS);
                                                      # every track already swings at the tempo's ratio and sits
                                                      # where it belongs (bass on top, piano / sax laid back)
    prog = s.prog('Fmaj7 D7b9 | Gm7 C7 | ...')
    melody = s.motif('...').clip(octave=4)
    b.comp.play(jazz.comp(prog, style='charleston', answer=melody, seed=1), head)
    b.bass.play(jazz.walking_bass(prog, key=s.key, seed=2), head)
    b.drums.play(jazz.brushes(32, kit=b.kit, sweep=b.sweep, seed=3), head)   # the keymap of the kit it got
    jazz.horn_line(melody, s.tempo, **b.horn).place(b.sax, head)   # phrasing + scoops, falls, vibrato, swells

Finished productions (IR rooms, stage placement, master, measured balance): bands.make('jazz_trio' |
'jazz_quartet' | 'jazz_ballad' | 'bossa', s) - agentsound/bandlib/jazz.py.

Everything the pieces need is re-exported here: voicings from theory (rootless A/B, shells, quartal, So What,
block chords, upper structures, voice-led jazz_voicings, check_voicing), patterns (comp, walking_bass, brushes,
ride_pattern, brush_fill, GM_BRUSH / SWIRLY_BRUSH kit maps) and the feel (swing_ratio, layback_ms, jazz_groove,
phrase_dynamics, touch for melodies, bass_touch for bass lines). New here: Feel, the horn expression helpers (scoop, fall, swell, vibrato, breathe, horn_line),
paraphrase, block_chords, solo_line and band(). The pianist's hands: pianist() (= agentsound.pianist.arrange: a
melody + changes -> a harmonized, decorated, filled two-handed piano part) and MOVES (trill, tremolo, mordent, turn,
crush, blues_crush, slip_note, repeated, roll, sweep, gliss, runs, fourths, shake, alternating_hands - each callable
on its own as agentsound.pianist.<move>). Recipe: recipes/jazz-trio.md; reference: docs/COMPOSE_API.md (Jazz).
"""

from __future__ import annotations

import math
import random

from .humanize import (BASS_ACCENTS, LAYBACK_MS, Groove, backbeat, bass_touch, jazz_groove, lay_back, layback_ms,
                       phrase_dynamics, phrases, swing, swing_ratio, touch)
from . import pianist as _pianist
from .modulation import lfo as _lfo
from .patches import fx, inst
from .patterns import (BRUSH_STYLES, COMP_CELLS, COMP_STYLES, FILL_KINDS, GM_BRUSH, RIDE_PATTERNS, SWIRLY_BRUSH,
                       WALK_FEELS, Clip, Note, _as_prog, _vel, as_clip, beats, brush_fill, brushes, comp, ride_pattern,
                       seed_int, walking_bass)
from .theory import (BLOCK_STYLES, CHORD_KINDS, CHORD_SCALES, JAZZ_VOICINGS, LH_REGISTER, LOW_INTERVAL_LIMITS,
                     UPPER_STRUCTURES, Chord, ComposeError, Key, Progression, available_tensions, block, check_voicing,
                     chord_kind, chord_scale, chord_scale_name, guide_tones, jazz_voice, jazz_voicings, mud, note,
                     quartal, rootless, shell, so_what, upper_structure)

__all__ = [
    # voicings (theory)
    'LH_REGISTER', 'JAZZ_VOICINGS', 'LOW_INTERVAL_LIMITS', 'CHORD_KINDS', 'CHORD_SCALES', 'UPPER_STRUCTURES',
    'BLOCK_STYLES', 'mud', 'chord_kind', 'guide_tones', 'chord_scale', 'chord_scale_name', 'available_tensions',
    'rootless', 'shell', 'quartal', 'so_what', 'block', 'upper_structure', 'jazz_voice', 'jazz_voicings',
    'check_voicing', 'block_chords',
    # patterns
    'COMP_STYLES', 'COMP_CELLS', 'comp', 'WALK_FEELS', 'walking_bass', 'GM_BRUSH', 'SWIRLY_BRUSH', 'BRUSH_STYLES',
    'FILL_KINDS', 'RIDE_PATTERNS', 'brushes', 'brush_fill', 'ride_pattern',
    # feel
    'swing_ratio', 'LAYBACK_MS', 'layback_ms', 'lay_back', 'jazz_groove', 'backbeat', 'phrases', 'phrase_dynamics',
    'touch', 'bass_touch', 'BASS_ACCENTS', 'Feel',
    # horn expression
    'Expression', 'scoop', 'fall', 'swell', 'vibrato', 'breathe', 'legato_phrases', 'HornLine', 'horn_line',
    'EXPRESSION_PARAMS',
    # melody
    'paraphrase', 'solo_line',
    # the pianist's hands (agentsound.pianist)
    'pianist', 'MOVES', 'PIANIST_STYLES',
    # band
    'Band', 'band', 'JAZZ_PROGRESSIONS', 'SAMPLED_SOUNDS', 'SFZ_SOUNDS', 'PIANO_WIDTH', 'sampled', 'swirly_sweep',
]

_EPS = 1e-6


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


def _prob(x, what: str) -> float:
    return _num(x, what, 0.0, 1.0)


def _ms(ms: float, bpm: float) -> float:
    return ms / 1000.0 * bpm / 60.0


# ------------------------------------------------------------------------------------------ feel

class Feel:
    """The band's time feel at one tempo: the swing ratio (swing_ratio(bpm), or ratio=) and where each part sits
    against the beat (LAYBACK_MS; override single parts with layback={'sax': 30}).

        feel = jazz.Feel(s.tempo)
        piano.groove(feel.groove('piano'))        # compile-time: swung 8ths + 16 ms behind at 140 BPM
        bass.groove(feel.groove('bass'))          # on top, 2 and 4 a touch heavier
        clip = feel.apply(melody, 'sax')          # the same, baked into a clip (for parts with expression lanes)"""

    def __init__(self, bpm: float, ratio: float | None = None, layback: dict | None = None,
                 beats_per_bar: float = 4.0):
        self.bpm = _num(bpm, 'Feel bpm', 20, 400)
        self.beats_per_bar = _num(beats_per_bar, 'Feel beats_per_bar', 1, 16)
        self.ratio = swing_ratio(self.bpm) if ratio is None else _num(ratio, 'Feel ratio', 0.5, 0.8)
        self.layback = dict(layback or {})
        for part, ms in self.layback.items():
            _num(ms, f"Feel layback[{part!r}] (ms)", -60, 120)

    def __repr__(self) -> str:
        return f"Feel({self.bpm:g} BPM, swing {self.ratio:.3f})"

    def late_ms(self, part: str) -> float:
        """Milliseconds this part sits behind the beat (negative = ahead)."""
        return float(self.layback[part]) if part in self.layback else layback_ms(part, self.bpm)

    def groove(self, part: str, accent_24: float | None = None) -> Groove:
        """Groove for track.groove(): swing at the ratio + the part's lay-back (+ 2/4 accents on the bass)."""
        return jazz_groove(part, self.bpm, ratio=self.ratio, late_ms=self.late_ms(part), accent_24=accent_24,
                           beats_per_bar=self.beats_per_bar)

    def swing(self, clip) -> Clip:
        """Swing the off-beat 8ths of a clip at the ratio (clip-level; triplets and other off-grid notes stay)."""
        c = as_clip(clip)
        return c if self.ratio <= 0.5 + 1e-9 else swing(c, self.ratio, '1/8')

    def apply(self, clip, part: str) -> Clip:
        """Swing + the part's lay-back baked into the clip (never moved before the clip start)."""
        return lay_back(self.swing(clip), self.late_ms(part), self.bpm)


# ------------------------------------------------------------------------------ horn expression

EXPRESSION_PARAMS = {'expression': ('instrument.expression', 'ratio'), 'level': ('instrument.level', 'db'),
                     'gainDb': ('gainDb', 'db'), 'dynamics': ('instrument.dynamics', 'ratio')}
"""Where swells and fades go: 'expression' (default; the sampler / sf2 expression control 0..1, CC11-like), 'level'
(the instrument's level param, dB, relative to the level the sound sets), 'gainDb' (the track fader, dB relative to
its gain_db; also moves the post-fader sends) or 'dynamics' (the sampler's played dynamics 0..1: the dB offset as a
ratio, so a swell also opens the tone and crossfades live layers - articulation.py)."""


class Expression:
    """Automation lanes and modulators for one track, built by the horn helpers (scoop, fall, swell, vibrato) or
    horn_line(); apply(track) hands them to track.automate() / track.modulate().

    lanes: {target: [points]} with absolute values; swells: {param: [(beat, dB offset, curve)]} (resolved against
    the track's own level when applied); vibratos: [(depth points, rate points)] -> on a sampler the instrument's own
    vibrato ('instrument.vibrato' cents / 'instrument.vibratorate' Hz: it runs on through legato transitions), else
    one lfo modulator each on 'instrument.pitchbend'."""

    def __init__(self):
        self.lanes: dict[str, list] = {}
        self.swells: dict[str, list] = {}
        self.vibratos: list[tuple[list, list]] = []

    def __repr__(self) -> str:
        n = sum(len(v) for v in self.lanes.values()) + sum(len(v) for v in self.swells.values())
        return f"Expression({n} points on {sorted(set(self.lanes) | set(self.swells))}, {len(self.vibratos)} vibrato)"

    def add(self, target: str, points) -> 'Expression':
        """Add automation points (absolute values) for a target such as 'instrument.pitchbend'."""
        self.lanes.setdefault(target, []).extend(points)
        return self

    def add_swell(self, param: str, points) -> 'Expression':
        """Add swell points (beat, dB offset[, curve]) for an EXPRESSION_PARAMS key."""
        if param not in EXPRESSION_PARAMS:
            raise ComposeError(f"expression param must be one of {', '.join(EXPRESSION_PARAMS)}, got {param!r}")
        self.swells.setdefault(param, []).extend(points)
        return self

    def add_vibrato(self, depth_points, rate_points) -> 'Expression':
        self.vibratos.append((list(depth_points), list(rate_points)))
        return self

    def shifted(self, by: float) -> 'Expression':
        """A copy with every point moved by `by` beats."""
        out = Expression()
        sh = lambda pts: [(p[0] + by,) + tuple(p[1:]) for p in pts]  # noqa: E731
        out.lanes = {t: sh(v) for t, v in self.lanes.items()}
        out.swells = {t: sh(v) for t, v in self.swells.items()}
        out.vibratos = [(sh(d), sh(r)) for d, r in self.vibratos]
        return out

    def __add__(self, other: 'Expression') -> 'Expression':
        out = self.shifted(0.0)
        for t, v in other.lanes.items():
            out.lanes.setdefault(t, []).extend(v)
        for t, v in other.swells.items():
            out.swells.setdefault(t, []).extend(v)
        out.vibratos += other.vibratos
        return out

    def apply(self, track):
        """Automate / modulate `track` with this expression; returns the track. Swell dB offsets are resolved
        against the sound's own level (instrument 'level' param, the track's gain_db - 'gainDb' lanes are relative
        to it -, or expression 1.0)."""
        for target, pts in self.lanes.items():
            track.automate(target, pts)
        for param, pts in self.swells.items():
            target, unit = EXPRESSION_PARAMS[param]
            if unit == 'ratio':
                vals = [(b, round(min(1.0, 10.0 ** (db / 20.0)), 5)) + tuple(rest) for b, db, *rest in pts]
            else:
                if param == 'level':
                    base = track.instrument.params.get('level', 0.0) if hasattr(track, 'instrument') else 0.0
                else:
                    base = 0.0          # 'gainDb' values are dB on the track's gain_db already
                base = float(base) if isinstance(base, (int, float)) and not isinstance(base, bool) else 0.0
                vals = [(b, round(base + db, 4)) + tuple(rest) for b, db, *rest in pts]
            track.automate(target, vals)
        ins = getattr(track, 'instrument', None)
        if self.vibratos and getattr(ins, 'type', None) == 'sampler':    # the sampler's vibrato: depth / rate lanes
            bps = track._song.tempo / 60.0
            depth_pts = [(p[0], round(p[1] * 100.0, 3)) + tuple(p[2:]) for d, _ in self.vibratos for p in d]
            rate_pts = [(p[0], round(min(12.0, max(0.5, bps / p[1])), 4)) + tuple(p[2:]) for _, r in self.vibratos for p in r]
            track.automate('instrument.vibrato', depth_pts)
            if rate_pts:
                track.automate('instrument.vibratorate', rate_pts)
            return track
        if self.vibratos and 'instrument.pitchbend' not in self.lanes:
            first = min(p[0] for d, _ in self.vibratos for p in d)
            track.automate('instrument.pitchbend', [(max(0.0, first), 0.0)])     # the lane the vibrato rides on
        for depth, rate in self.vibratos:
            track.modulate('instrument.pitchbend', _lfo('sine', rate=rate, depth=depth))
        return track


def scoop(at, cents: float = -80.0, length='1/16') -> list:
    """Pitch-bend points (for 'instrument.pitchbend', semitones) of a scoop into a note starting at `at`: the note
    starts `cents` flat (-50..-100) and glides up to pitch over `length` beats."""
    a = _pos(at)
    L = beats(length)
    if L <= 0:
        raise ComposeError("scoop length must be > 0")
    c = _num(cents, 'scoop cents', -300, 300)
    # the leading 0 keeps the lane at pitch before the scoop (before a lane's first point its first value holds)
    return [(a, 0.0), (a, c / 100.0, 'step'), (a + L, 0.0, 'smooth')]


def fall(end, semitones: float = -3.0, length='1/8', back=None) -> list:
    """Pitch-bend points of a fall-off at the end of a note ending at `end`: the pitch drops `semitones` over the
    last `length` beats and returns to 0 at `back` (default half a beat later, when the tail has died)."""
    e = _pos(end)
    L = beats(length)
    st = _num(semitones, 'fall semitones', -24, 24)
    b = e + 0.5 if back is None else _pos(back)
    if L <= 0 or b <= e:
        raise ComposeError("fall needs length > 0 and back after the note end")
    return [(e - L, 0.0), (e, st, 'smooth'), (b, 0.0, 'step')]


def swell(start, end, lo_db: float = -6.0, peak_db: float = 0.0, end_db: float = -8.0, peak: float = 0.55,
          rest=None) -> list:
    """dB-offset points (Expression.add_swell) for a long note: it starts lo_db down, swells to peak_db at `peak`
    (0..1 of the note) and fades to end_db at its end; `rest` (a beat after the note, default its end + 0.25) jumps
    back to 0 dB for the next note."""
    a, e = _pos(start), _pos(end)
    if e <= a or not 0 < peak < 1:
        raise ComposeError("swell needs end > start and 0 < peak < 1")
    r = e + 0.25 if rest is None else _pos(rest)
    pts = [(a, 0.0), (a, lo_db, 'step'), (a + (e - a) * peak, peak_db, 'smooth'), (e, end_db, 'smooth')]
    if r > e + _EPS:
        pts.append((r, 0.0, 'step'))
    return pts


def vibrato(start, end, bpm: float, depth: float = 0.18, hz: float = 5.0, delay: float = 0.35,
            grow: float = 0.6) -> tuple[list, list]:
    """(depth points, rate points) of a delayed vibrato on one note (for Expression.add_vibrato): nothing for
    `delay` seconds, then the depth grows to `depth` semitones (0.12..0.25 = 12..25 cents) over `grow` seconds,
    at `hz` (4.5..5.5), and dies within 60 ms at the note end."""
    a, e = _pos(start), _pos(end)
    b = _num(bpm, 'vibrato bpm', 20, 400)
    d0 = a + _ms(delay * 1000.0, b)
    d1 = d0 + _ms(grow * 1000.0, b)
    off = e - _ms(60.0, b)
    if off <= d0 + _EPS:
        return [], []
    top = depth if off >= d1 else depth * (off - d0) / (d1 - d0)
    pts = [(a, 0.0), (d0, 0.0), (min(d1, off), round(top, 4), 'smooth'), (off, round(top, 4)),
           (e, 0.0, 'smooth')]
    rate_beats = round(b / 60.0 / _num(hz, 'vibrato hz', 0.5, 20), 6)
    return pts, [(a, rate_beats, 'step')]


_scoop_pts, _fall_pts, _swell_pts, _vibrato_pts = scoop, fall, swell, vibrato


def legato_phrases(clip, overlap: float = 0.02, max_gap='1/16') -> Clip:
    """Tie the notes inside each phrase: a note lasts until the next onset + overlap when that onset is less than
    `max_gap` beats after its written end; phrase ends (longer rests) keep their length. For monophonic horns
    (sf2 mono='on' makes the overlap a clean hand-over)."""
    c = as_clip(clip)
    g = beats(max_gap)
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    out = []
    for i, n in enumerate(ns):
        nxt = next((m for m in ns[i + 1:] if m.start > n.start + _EPS), None)
        if nxt is not None and nxt.start - (n.start + n.dur) < g - _EPS:
            n = n._replace(dur=max(n.dur, nxt.start - n.start + overlap))
        out.append(n)
    return Clip._raw(out, c.length)


def breathe(clip, bpm: float, breath_ms: float = 180.0, max_phrase: float = 8.0) -> Clip:
    """Let a horn line breathe: before every rest the last note ends at least `breath_ms` before the next phrase
    starts, and a phrase longer than `max_phrase` beats gets a breath: its longest note in the second half is cut
    `breath_ms` short (the next note then starts a new phrase)."""
    c = as_clip(clip)
    b = _num(bpm, 'breathe bpm', 20, 400)
    gap = _ms(_num(breath_ms, 'breath_ms', 0, 2000), b)
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    out = list(ns)
    # phrases longer than max_phrase: cut one breath into the second half
    for ph in phrases(Clip._raw(ns, c.length), gap=0.5):
        if ph[-1].start + ph[-1].dur - ph[0].start <= max_phrase + _EPS or len(ph) < 3:
            continue
        mid = ph[0].start + (ph[-1].start - ph[0].start) / 2.0
        cands = [n for n in ph[:-1] if n.start >= mid - _EPS and n.dur > gap * 2]
        if not cands:
            continue
        victim = max(cands, key=lambda n: (n.dur, -n.start))
        i = out.index(victim)
        nxt = next((m for m in out if m.start > victim.start + _EPS), None)
        end = (nxt.start if nxt is not None else victim.start + victim.dur) - gap
        out[i] = victim._replace(dur=max(0.1, min(victim.dur, end - victim.start)))
    # a note before a (short) rest leaves at least `gap` of air before the next phrase
    res = []
    for n in sorted(out, key=lambda n: (n.start, n.pitch)):
        nxt = next((m for m in out if m.start > n.start + _EPS), None)
        if nxt is not None:
            rest = nxt.start - (n.start + n.dur)
            if 0.05 - _EPS < rest < gap - _EPS and nxt.start - n.start > gap * 2:
                n = n._replace(dur=max(0.1, nxt.start - gap - n.start))
        res.append(n)
    return Clip._raw(res, c.length)


class HornLine:
    """A performed horn part, relative to its own start: .clip (the notes as played: swung, laid back, legato
    phrases, breaths, phrase dynamics) and .expr (scoops / falls on the pitch bend, swells on `param`, delayed
    vibrato). place(track, at) plays the clip at `at` and applies the expression shifted there."""

    def __init__(self, clip: Clip, expr: Expression):
        self.clip = clip
        self.expr = expr

    def __repr__(self) -> str:
        return f"HornLine({len(self.clip)} notes, {self.expr!r})"

    def expression(self, at=0.0) -> Expression:
        """The expression moved to start at `at` (a beat or Section)."""
        return self.expr.shifted(_pos(at))

    def place(self, track, at=0.0):
        """track.play(self.clip, at) + the expression at `at`. Returns the track."""
        a = _pos(at)
        track.play(self.clip, a)
        self.expression(a).apply(track)
        return track


def horn_line(melody, bpm: float, *, ratio: float | None = None, late_ms: float | None = None, long='1/2',
              scoop: float = 0.35, scoop_cents=(-90.0, -50.0), fall: float = 0.5, fall_st: float = -3.0,
              vibrato: bool = True, vib_hz=(4.6, 5.4), vib_depth: float = 0.18, vib_delay: float = 0.35,
              vib_grow: float = 0.6, swell: bool = True, swell_db=(-5.0, 0.0, -7.0), param: str = 'expression',
              breath_ms: float = 180.0, max_phrase: float = 8.0, legato: bool = True, dynamics: bool = True,
              glide: float = 0.0, glide_ms: float = 120.0, seed=0) -> HornLine:
    """Turn a written melody (a Clip on the straight grid, e.g. a head) into a played saxophone / horn line.

    Timing: 8ths swung at ratio (default swing_ratio(bpm)) and the whole line late_ms behind (default the 'sax'
    lay-back: ~35 ms at ballad tempo, ~22 at 140 BPM) - baked into the clip, so the expression lines up with the
    notes (don't also groove the track). Phrasing: legato inside phrases (a slight overlap: use mono='on'), breaths of
    breath_ms before rests and inside phrases longer than max_phrase beats, phrase dynamics (arch, peak, soft ends).
    Expression (seeded), for notes of at least `long` beats unless said otherwise:
      scoop   probability of a scoop (scoop_cents, e.g. -90..-50) into a note that starts a phrase or follows a leap
              up of a 3rd or more (notes of a quarter or longer)
      fall    probability of a fall-off (fall_st semitones) on a phrase-end note followed by a rest of a beat or more
      vibrato delayed vibrato on long notes: vib_delay s of straight tone, then vib_depth semitones grown over
              vib_grow s at a seeded rate in vib_hz (False for sounds with their own vibrato: GeneralUser's
              'Tenor Sax' has one, about +-19 ct at 5 Hz from 0.4 s; the FreePats tenor is straight)
      swell   long notes start swell_db[0] down, swell to [1] and fade to [2] dB, on `param` (EXPRESSION_PARAMS:
              'expression' (default), 'level', 'gainDb' or 'dynamics')
      glide   probability of a portamento (glide_ms) into a legato note after a leap of a 4th or more (a glide mark:
              the sampler's mono='legato' bends into it, e.g. sampled/tenor_sax; other instruments: leave it 0)
    On a sampler with mono='legato' (sampled/tenor_sax, sampled/alto_sax) the legato phrases are real legato
    transitions (no re-attack) and the vibrato is the sampler's own (it runs on through the transitions).
    Returns a HornLine: line.place(sax_track, head)."""
    m = as_clip(melody)
    b = _num(bpm, 'horn_line bpm', 20, 400)
    if param not in EXPRESSION_PARAMS:
        raise ComposeError(f"horn_line param must be one of {', '.join(EXPRESSION_PARAMS)}, got {param!r}")
    scoop_p, fall_p = _prob(scoop, 'horn_line scoop'), _prob(fall, 'horn_line fall')
    L_long = beats(long)
    rng = random.Random(seed_int(seed))
    r = swing_ratio(b) if ratio is None else _num(ratio, 'horn_line ratio', 0.5, 0.8)
    late = layback_ms('sax', b) if late_ms is None else _num(late_ms, 'horn_line late_ms', -60, 150)
    c = swing(m, r, '1/8') if r > 0.5 + 1e-9 else m
    if legato:
        c = legato_phrases(c)
    c = breathe(c, b, breath_ms, max_phrase)
    if dynamics:
        c = phrase_dynamics(c, gap='1/8', arch=0.14, peak=1.06, end=0.9)
    c = lay_back(c, late, b)
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    expr = Expression()
    bend: list = []
    for i, n in enumerate(ns):
        prev = ns[i - 1] if i > 0 else None
        nxt = ns[i + 1] if i + 1 < len(ns) else None
        end = n.start + n.dur
        stop = min(end, nxt.start) if nxt is not None else end        # legato: the next note takes over here
        phrase_start = prev is None or n.start - (prev.start + prev.dur) >= 0.4
        phrase_end = nxt is None or nxt.start - end >= 1.0 - _EPS
        if n.dur >= 0.9 and (phrase_start or (prev is not None and n.pitch - prev.pitch >= 3)):
            if rng.random() < scoop_p:
                cents = rng.uniform(min(scoop_cents), max(scoop_cents))
                bend += _scoop_pts(n.start, cents, length=min(0.25, n.dur * 0.3))
        falling = False
        if phrase_end and n.dur >= 0.45 and rng.random() < fall_p:
            back = min(end + 0.5, nxt.start - 0.02) if nxt is not None else end + 0.5
            if back > end + _EPS:
                fl = min(0.5, n.dur * 0.45)
                bend += _fall_pts(end, fall_st, length=fl, back=back)
                falling = True
                if swell:
                    expr.add_swell(param, [(end - fl, 0.0, 'step'), (end, -9.0, 'smooth'), (back, 0.0, 'step')])
        if n.dur >= L_long - _EPS:
            if swell and not falling and stop - n.start > 0.5:
                rest = nxt.start if nxt is not None else stop + 0.25
                lo, pk, en = swell_db
                expr.add_swell(param, _swell_pts(n.start, stop, lo, pk, en, rest=max(rest, stop + 0.01)))
            if vibrato:
                hz = rng.uniform(min(vib_hz), max(vib_hz)) if isinstance(vib_hz, (tuple, list)) else float(vib_hz)
                d, rt = _vibrato_pts(n.start, stop, b, vib_depth, hz, vib_delay, vib_grow)
                if d:
                    expr.add_vibrato(d, rt)
    if bend:
        expr.add('instrument.pitchbend', bend)
    expr = _merge_vibratos(expr)
    glide_p = _prob(glide, 'horn_line glide')
    if glide_p > 0:     # portamento into leaps inside legato phrases (drawn after the other choices: same seed, same line)
        from .articulation import _mark
        marked = []
        for i, n in enumerate(ns):
            prev = ns[i - 1] if i > 0 else None
            tied = prev is not None and prev.start + prev.dur > n.start + _EPS
            if tied and abs(n.pitch - prev.pitch) >= 5 and rng.random() < glide_p:
                n = _mark(n, gl=_num(glide_ms, 'horn_line glide_ms', 1, 2000))
            marked.append(n)
        c = Clip._raw(marked, c.length)
    return HornLine(c, expr)


def _merge_vibratos(expr: Expression) -> Expression:
    """All per-note vibratos of one line -> ONE lfo (depth and rate lanes switch per note), not one per note."""
    if len(expr.vibratos) <= 1:
        return expr
    depth: list = []
    rate: list = []
    for d, r in sorted(expr.vibratos, key=lambda v: v[0][0][0]):
        depth += d
        rate += r
    expr.vibratos = [(depth, rate)]
    return expr


# ------------------------------------------------------------------------------------ melody

def paraphrase(melody, seed=0, anticipate: float = 0.3, delay: float = 0.15, embellish: float = 0.2, key=None,
               vel: float = 0.8) -> Clip:
    """Loosen a written melody the way a horn player states a head (seeded, pitches and phrase shape kept):
      anticipate  a note on beat 1 or 3 comes an 8th early (tied over; the note before gives way)
      delay       a phrase entrance on a beat comes an 8th late
      embellish   a long note (1.5+ beats) gets a pickup: a chromatic lower neighbour on the 8th before it, or an
                  enclosure (the scale step above, then the half step below, as triplets)
    Rhythms stay on the 8th / triplet grid (the feel swings them). key= for the scale step (else a whole step);
    vel = velocity factor of added notes. Paraphrase every head differently: seed=chorus number."""
    c = as_clip(melody)
    p_ant, p_del, p_emb = (_prob(x, f"paraphrase {w}") for x, w in ((anticipate, 'anticipate'), (delay, 'delay'),
                                                                     (embellish, 'embellish')))
    vel = _num(vel, 'paraphrase vel (factor of added notes)', 0.05, 2.0)
    rng = random.Random(seed_int(seed))
    k = Key(key) if key is not None else None
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    out = [list(n) for n in ns]           # [start, dur, pitch, vel]
    added: list[Note] = []

    def prev_end(i):
        return out[i - 1][0] + out[i - 1][1] if i > 0 else -math.inf

    for i, n in enumerate(out):
        start, dur, pitch, v = n
        on_beat = abs(start - round(start)) < 1e-6
        strong = on_beat and int(round(start)) % 2 == 0
        gap = start - prev_end(i)
        if strong and dur >= 0.5 - _EPS and start >= 0.5 and rng.random() < p_ant:
            if gap >= 0.5 - _EPS or (i > 0 and out[i - 1][1] >= 0.75 and out[i - 1][0] < start - 0.5):
                if i > 0 and gap < 0.5 - _EPS:
                    out[i - 1][1] = start - 0.5 - out[i - 1][0]
                n[0], n[1] = start - 0.5, dur + 0.5
                continue
        if on_beat and gap >= 1.0 - _EPS and dur >= 1.0 - _EPS and rng.random() < p_del:
            n[0], n[1] = start + 0.5, dur - 0.5
            continue
        if dur >= 1.5 - _EPS and rng.random() < p_emb:
            room = start - max(prev_end(i), 0.0)
            enclose = rng.random() < 0.5 and start >= 2.0 / 3.0
            need = 2.0 / 3.0 if enclose else 0.5
            if room >= need - _EPS or (i > 0 and out[i - 1][1] >= need + 0.5 and out[i - 1][0] < start - need - 0.25):
                if room < need - _EPS:
                    out[i - 1][1] = max(0.25, start - need - out[i - 1][0])
                if enclose:
                    above = k.transpose(pitch, 1) if k is not None else pitch + 2
                    added.append(Note(start - 2.0 / 3.0, 1.0 / 3.0, above, _vel(v * vel)))
                    added.append(Note(start - 1.0 / 3.0, 1.0 / 3.0, pitch - 1, _vel(v * vel * 0.95)))
                elif start >= 0.5:
                    added.append(Note(start - 0.5, 0.5, pitch - 1, _vel(v * vel)))
    notes = [Note(max(0.0, s), max(0.05, d), p, v) for s, d, p, v in out] + added
    return Clip._raw(notes, c.length)


def block_chords(melody, prog, style: str = 'drop2', min_dur=0.0, key=None, vel: float = 0.85) -> Clip:
    """Harmonize every melody note with a block chord under it (theory.block: 6th chords on major, dominant / minor
    sets, tensions replacing the tone below them, diminished 7ths on passing tones): Shearing / Garland locked hands
    (style='locked'), drop2 (default), drop24 or close. Notes shorter than min_dur stay single (fast runs); the
    harmony voices get `vel` x the melody velocity. prog: a Progression (or chord string) timed like the melody."""
    c = as_clip(melody)
    p = prog if isinstance(prog, Progression) else Progression(prog, key=key)
    vel = _num(vel, 'block_chords vel (factor of the harmony voices)', 0.05, 2.0)
    md = beats(min_dur)
    out: list[Note] = []
    for n in c:
        ch = p.at(n.start)
        if ch is None or n.dur < md - _EPS:
            out.append(n)
            continue
        for q in block(ch, n.pitch, style):
            out.append(n if q == n.pitch else Note(n.start, n.dur, q, _vel(n.vel * vel)))
    return Clip._raw(out, c.length)


MOVES = _pianist.MOVES
PIANIST_STYLES = tuple(_pianist.STYLES)


def pianist(melody, prog, *, bpm, key=None, style: str = 'straight', density: float = 0.5, seed=0, **kw):
    """A pianist's arrangement of a melody over changes (agentsound.pianist.arrange) -> Arrangement with .rh (the
    right hand: the melody on top, harmonized phrase by phrase - guide tones, 3rds / 6ths, close, drop 2, quartal,
    upper structures, octaves, locked hands -, long notes decorated with trills, tremolos, turns, mordents, crushes,
    slip notes, rolls, re-struck voicings, the gaps filled with runs, sweeps, cascading 4ths, answers, stabs,
    alternating-hands breaks and a glissando into the next section), .lh (with lh='guide' | 'shell' | 'rootless' |
    'tenths' | 'stride' | 'pedal'), .pedal(prog, at) and .moves (what it played). A piano lead is never a bare
    single-note line (user feedback 2026-09-30): arrange it. style: PIANIST_STYLES ('straight', 'ballad', 'bar',
    'lush', 'sparse'); density 0..1; deterministic by seed; bpm times the fast moves in real time. Apply
    jazz.touch() to the melody first (the arranger keeps its velocities and voices the inner notes ~10-15 under)."""
    return _pianist.arrange(melody, prog, bpm=bpm, key=key, style=style, density=density, seed=seed, **kw)


_SOLO_STEP = {0: 2.5, 1: 0.2, 2: 0.25, 3: 0.7, 4: 0.8, 5: 1.3, 6: 2.0, 7: 1.8}


def _solo_rhythm(a: float, b: float, rng: random.Random, density: float, triplets: float) -> list[tuple[float, float]]:
    """(start, dur) events of one phrase from a to b on the 8th / triplet grid, ending on a longer note."""
    ev: list[tuple[float, float]] = []
    t = a
    end_long = rng.choice((1.0, 1.5, 2.0))
    while t < b - end_long - 1e-9:
        on_beat = abs(t - round(t)) < 1e-9
        r = rng.random()
        if on_beat and r < triplets and t + 1 <= b - end_long + 1e-9:
            ev += [(t, 1 / 3), (t + 1 / 3, 1 / 3), (t + 2 / 3, 1 / 3)]
            t += 1.0
        elif on_beat and r < triplets + (1 - density) * 0.35 and t + 1 <= b - end_long + 1e-9:
            ev.append((t, 1.0))                                  # a quarter note: space inside the line
            t += 1.0
        elif r > 0.97 and ev:
            t += 0.5                                             # a short breath inside the phrase
        else:
            ev.append((t, 0.5))
            t += 0.5
    ev.append((t, end_long))
    return ev


def solo_line(prog, key=None, register=('C4', 'C6'), density: float = 0.6, intensity: float = 0.5, seed=0,
              motif=None, motif_prob: float = 0.3, phrase_bars=(1, 3), rest_beats=(1.5, 4.0), chromatic: float = 0.35,
              triplets: float = 0.12, vel: float = 88, length=4.0) -> Clip:
    """A bebop-flavoured improvised line over a progression -> Clip (straight: the feel swings it); a seeded starting
    point to edit or keep, like melody().

    Phrases of `phrase_bars` bars (density lengthens them and shortens the `rest_beats` between) mostly start off the
    beat and end on a longer chord tone (3rd or 9th preferred). The rhythm is running 8ths with quarter notes for
    space and 8th-note triplet turns (`triplets`). Pitches are planned per phrase (a seeded dynamic programme): chord
    tones on the beats, chord-scale and chromatic passing tones between (`chromatic`: how often an enclosure - scale
    step above, half step below - leads into a target), steps over leaps, runs in one direction, an arc per phrase,
    all inside `register`. motif= a Clip (e.g. the head's first bar): with motif_prob a phrase opens with it, fitted
    to the chords and folded into the register - motif development. Velocities: bebop accents on the upbeats, ghosted
    low notes in runs, the phrase's peak on top; intensity 0..1 raises level and register."""
    p = _as_prog(prog, key, length)
    kk = Key(key) if key is not None else p.key
    lo, hi = note(register[0]), note(register[1])
    if hi - lo < 12:
        raise ComposeError(f"solo_line register {register!r} must span at least an octave")
    density, intensity, chromatic, triplets, motif_prob = (
        _prob(x, f"solo_line {w}") for x, w in ((density, 'density'), (intensity, 'intensity'),
                                                 (chromatic, 'chromatic'), (triplets, 'triplets'),
                                                 (motif_prob, 'motif_prob')))
    vel = _num(vel, 'solo_line vel', 1, 127)
    rng = random.Random(seed_int(seed))
    L = p.length
    bpb = p.beats_per_bar
    mot = as_clip(motif) if motif is not None else None
    # phrase plan
    plan: list[tuple[float, float]] = []
    t = rng.choice((0.5, 1.0, 1.5))
    while t < L - 1.0:
        n_bars = rng.uniform(*phrase_bars) * (0.8 + 0.5 * density)
        end = min(L, round((t + max(2.0, n_bars * bpb)) * 2) / 2)
        if end - t >= 1.5:
            plan.append((t, end))
        rest = rng.uniform(*rest_beats) * (1.3 - 0.6 * density)
        t = round((end + max(1.0, rest)) * 2) / 2
        if abs(t - round(t)) < 1e-9 and rng.random() < 0.7:
            t += 0.5                                             # start off the beat
    notes: list[Note] = []
    prev_pitch = None
    base_vel = vel * (0.9 + 0.2 * intensity)
    for pi, (a, b) in enumerate(plan):
        events = _solo_rhythm(a, b, rng, density, triplets)
        fixed: dict[int, int] = {}
        if mot is not None and len(mot) and rng.random() < motif_prob:
            m = mot.shift(a - min(n.start for n in mot))
            fitted = [n for n in m.fit(p, kk) if n.start < b - 1.0]
            if fitted:
                events = [(n.start, n.dur) for n in fitted] + [e for e in events if e[0] >= max(
                    n.start + n.dur for n in fitted) - 1e-9]
                for i, n in enumerate(fitted):
                    q = n.pitch
                    while q > hi:
                        q -= 12
                    while q < lo:
                        q += 12
                    fixed[i] = q
        pitches = _solo_pitches(events, fixed, p, kk, lo, hi, rng, prev_pitch, intensity)
        for i, ((st, du), q) in enumerate(zip(events, pitches)):
            if st >= L - 1e-9:
                continue
            notes.append(Note(st, max(0.05, min(du, L - st)), q, _vel(base_vel)))
        if pitches:
            prev_pitch = pitches[-1]
    # enclosures into strong-beat targets
    notes.sort(key=lambda n: n.start)
    for i in range(2, len(notes)):
        n = notes[i]
        if abs(n.start - round(n.start)) > 1e-9 or rng.random() >= chromatic * 0.5:
            continue
        a, b = notes[i - 2], notes[i - 1]
        if abs(b.start - (n.start - 0.5)) > 1e-9 or abs(a.start - (n.start - 1.0)) > 1e-9:
            continue
        ch = p.at(n.start)
        above = kk.snap(n.pitch + 1, 1) if kk is not None else n.pitch + 2
        if ch is not None and (above - n.pitch) in (1, 2) and lo <= n.pitch - 1 and above <= hi:
            notes[i - 2] = a._replace(pitch=above)
            notes[i - 1] = b._replace(pitch=n.pitch - 1)
    c = Clip._raw(notes, L)
    return phrase_dynamics(c, gap='1/4', arch=0.12, peak=1.06, end=1.0, offbeat=1.06, ghost=0.8)


def _solo_pitches(events, fixed: dict[int, int], p: Progression, kk, lo: int, hi: int, rng: random.Random,
                  prev_pitch, intensity: float) -> list[int]:
    """Viterbi over (pitch, previous pitch) for one phrase: chord tones on the beats, scale / chromatic passing tones
    between, small steps, runs in one direction, an arc; `fixed` event indices keep their pitch (a motif)."""
    n = len(events)
    if n == 0:
        return []
    shape = rng.choice(('arch', 'rise', 'fall', 'valley'))
    span = hi - lo
    centre = lo + span * (0.4 + 0.2 * intensity)
    a0, a1 = events[0][0], events[-1][0]
    info = []
    for st, du in events:
        ch = p.at(st)
        if ch is None:
            tones, scale, colour = set(), set(range(12)), set()
        else:
            tones = {(ch.root + i) % 12 for i in ch.intervals}
            g3, g7 = guide_tones(ch)
            tones |= {g3} | ({g7} if g7 is not None else set())
            colour = {(ch.root + t) % 12 for t in available_tensions(ch)}
            scale = {(ch.root + i) % 12 for i in chord_scale(ch)} | tones
            if kk is not None and tones <= kk.pcs:
                scale |= set(kk.pcs)
        strong = abs(st - round(st)) < 1e-9
        info.append((tones, colour, scale, strong, ch))

    def contour(x: float) -> float:
        f = {'arch': math.sin(math.pi * x), 'rise': x, 'fall': 1 - x, 'valley': 1 - math.sin(math.pi * x)}[shape]
        return centre + (f - 0.5) * span * 0.55

    noise = [{q: rng.random() * 0.6 for q in range(lo, hi + 1)} for _ in range(n)]
    states: dict[tuple, tuple[float, list[int]]] = {}
    first_pool = [fixed[0]] if 0 in fixed else range(lo, hi + 1)
    for q in first_pool:
        tones, colour, scale, strong, _ = info[0]
        c = 0.0 if q % 12 in tones else 1.0 if q % 12 in scale else 3.0
        if prev_pitch is not None:
            c += 0.08 * abs(q - prev_pitch)
        states[(q, None)] = (c + noise[0][q], [q])
    for i in range(1, n):
        tones, colour, scale, strong, ch = info[i]
        last = i == n - 1
        x = 0.5 if a1 - a0 < 1e-9 else (events[i][0] - a0) / (a1 - a0)
        cen = contour(x)
        pool = [fixed[i]] if i in fixed else range(lo, hi + 1)
        new: dict[tuple, tuple[float, list[int]]] = {}
        for q in pool:
            pc = q % 12
            if last:
                third = guide_tones(ch)[0] if ch is not None else None
                nc = 0.0 if (pc == third or (pc in colour and (pc - (ch.root if ch else 0)) % 12 in (2, 9))) else \
                    0.6 if pc in tones else 4.0
            elif strong:
                nc = 0.0 if pc in tones else 0.6 if pc in colour else 2.2 if pc in scale else 3.5
            else:
                nc = 0.3 if pc in tones else 0.2 if pc in scale else 1.0
            nc += 0.07 * abs(q - cen) + noise[i][q]
            for (q0, qm), (c0, path) in states.items():
                d = abs(q - q0)
                step = _SOLO_STEP.get(d, 2.5 + 0.35 * (d - 8) if d <= 12 else 6.0)
                cost = c0 + nc + step
                if not strong and not last and pc not in scale and d > 2:
                    cost += 1.0                                   # chromatic tones come by step, not by leap
                if qm is not None:
                    up_now, up_before = q > q0, q0 > qm
                    if q != q0 and q0 != qm and up_now != up_before:
                        cost += 0.35                              # a turn: fine now and then, not every note
                    if q == qm and d > 0:
                        cost += 1.5                               # A-B-A
                    if d == 1 and abs(q0 - qm) == 1 and (q - q0) * (q0 - qm) > 0 and (q0 % 12) not in info[i - 1][2]:
                        cost -= 1.2                               # a chromatic passing tone that keeps going
                key_ = (q, q0)
                if key_ not in new or cost < new[key_][0] - 1e-9:
                    new[key_] = (cost, path + [q])
        # keep the 5 best histories per pitch: the search stays small, the (pitch, previous) memory stays useful
        best: dict[int, list] = {}
        for k_, v in new.items():
            best.setdefault(k_[0], []).append((v[0], k_, v))
        states = {k_: v for lst in best.values() for _, k_, v in sorted(lst, key=lambda e: (e[0], e[1][1] or 0))[:5]}
    return min(states.values(), key=lambda v: (v[0], v[1]))[1]


JAZZ_PROGRESSIONS = {
    'ii_v_i': 'ii7 V7 Imaj7:2',
    'minor_ii_v_i': 'iiø7 V7b9 i6:2',
    'turnaround': 'Imaj7 vi7 ii7 V7',
    'iii_vi_ii_v': 'iii7 VI7 ii7 V7',
    'tritone_turnaround': 'Imaj7 bIII7 bVI7 bII7',
    'backdoor': 'iv7 bVII7 Imaj7:2',
    'rhythm_a': 'Imaj7:0.5 vi7:0.5 ii7:0.5 V7:0.5 | iii7:0.5 VI7:0.5 ii7:0.5 V7:0.5 | Imaj7:0.5 I7:0.5 IV7:0.5 '
                '#IVdim7:0.5 | Imaj7:0.5 V7:0.5 Imaj7',
    'blues': 'I7 IV7 I7 v7:0.5 I7:0.5 | IV7 #IVdim7 I7 VI7 | ii7 V7 I7:0.5 VI7:0.5 ii7:0.5 V7:0.5',
    'bridge_cycle': 'III7:2 VI7:2 II7:2 V7:2',
}
"""Jazz progressions as roman numerals (key.prog(JAZZ_PROGRESSIONS['rhythm_a']))."""


# ---------------------------------------------------------------------------------------- band

class Band:
    """The tracks jazz.band() made: comp (piano left hand / comping), piano (right hand: melody, solos), bass,
    drums, sax (or None), room and plate (the reverb buses, or None) and the feel; kit / sweep (the brush keymap
    and sweep length for jazz.brushes on the drums it got; stir: the (stir, tap) velocity factors that level a
    Swirly stir against its taps - agentsound.bandlib.jazz.brushes(band, bars, ...) applies all three), horn
    (horn_line options for its sax) and sounds (role -> what plays it)."""

    def __init__(self, **kw):
        self.comp = self.piano = self.bass = self.drums = self.sax = self.room = self.plate = self.feel = None
        self.kit, self.sweep, self.stir, self.horn, self.sounds = dict(GM_BRUSH), None, (1.0, 1.0), {}, {}
        for k, v in kw.items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        parts = [n for n in ('comp', 'piano', 'bass', 'drums', 'sax') if getattr(self, n) is not None]
        return f"Band({', '.join(parts)}; {self.feel!r})"


SAMPLED_SOUNDS = {
    'piano': ('salamander-grand-v3-sf2', 'SalamanderGrandPiano-V3+20200602.sf2', {'width': 0.7, 'level': 12.0},
              {'hp.freq': 70, 'low.freq': 160, 'low.gain': -3.0, 'peak1.freq': 300, 'peak1.gain': -3.5,
               'peak1.q': 0.8, 'high.freq': 9000, 'high.gain': 1.0},
              'Salamander Grand Piano V3 (Yamaha C5, 16 velocity layers; CC-BY 3.0 Alexander Holm - credit it)'),
    'sax': ('freepats-tenor-sax-sf2', 'TenorSaxophone-20200717.sf2', {'mono': 'on', 'level': -2.8},
            {'hp.freq': 100, 'low.freq': 220, 'low.gain': -2.0, 'peak1.freq': 400, 'peak1.gain': -3.0,
             'peak1.q': 0.9, 'peak3.freq': 2600, 'peak3.gain': 2.0, 'peak3.q': 0.8},
            'FreePats Tenor Saxophone (from VCSL, looped; CC0)'),
}
"""Sample packs that already come as SoundFonts (the sf2 player loads them today): role -> (pack id, file, sf2
params levelled like band()'s GeneralUser sounds, the eq band() gives it, credit): band(sampled_sounds='sf2').
The SFZ packs (SFZ_SOUNDS) are band()'s default when installed. The Salamander is a spaced-pair recording: its
linked L/R samples are barely correlated (some notes negative), so it plays at sf2 width 0.7 and band() gives it no
extra widener - at width 1.4 + the GeneralUser piano's 1.7 widener it measured 360 % wide, correlation -0.65, -8 dB
in mono. Its pianissimo layers are real: lines at velocity 40-55 sit ~6 dB under the GeneralUser piano (use 60-90)."""

PIANO_WIDTH = {'generaluser': 1.7, 'other': 1.0}
"""Stereo widener (fx.width) band() puts on the piano tracks: 1.7 on the narrow GeneralUser piano, 1.0 (none) on any
other piano (sampled grands are recorded in stereo and are wide already). band(piano_width=...) overrides."""


STIR_EVERY = 1.1
"""Seconds between Swirly Drums stirs that keep the 'shhh' continuous (see swirly_sweep)."""


def swirly_sweep(tempo: float, beats_per_bar: float = 4) -> str:
    """The jazz.brushes sweep= for the Swirly Drums brush kit (sampled/brush_kit) at `tempo`: the longest of 'bar',
    'half', 'beat' whose stirs start at most STIR_EVERY (1.1 s) apart. A Swirly stir is a swell (~0.6 s in, then an
    exponential tail) that the next stir crossfades: measured on the kit, one stir per ~1 s keeps a continuous stir
    that swells ~9 dB per gesture; one per bar at 144 BPM (1.7 s) or per half bar at 66 BPM (1.8 s) leaves 25-30 dB
    gaps of silence between the stirs. 144 BPM -> 'half', 66 BPM -> 'beat', 240 BPM -> 'bar'."""
    beat = 60.0 / float(tempo)
    for name, n in (('bar', float(beats_per_bar)), ('half', beats_per_bar / 2.0)):
        if n * beat <= STIR_EVERY:
            return name
    return 'beat'


def sampled(role: str, **params):
    """The sampled-pack sound for a band role ('piano', 'sax') as an sf2 instrument, levelled like band()'s
    default for that role: jazz.sampled('piano') = the Salamander Grand. Raises (with the install command) when the
    pack isn't installed. Extra params override (level=10, cutoff=-6 ...)."""
    if role not in SAMPLED_SOUNDS:
        raise ComposeError(f"no sampled SoundFont for {role!r}; roles: {', '.join(SAMPLED_SOUNDS)} (bass and brushes "
                           f"come as SFZ packs: meatbass, swirly-drums)")
    from . import library
    pack, fname, base, _, _ = SAMPLED_SOUNDS[role]
    path = library.SAMPLES / pack / fname
    if not path.is_file():
        raise ComposeError(f"jazz.sampled({role!r}): {path} is not installed; install it with "
                           f"`python -m agentsound samples fetch {pack}` (or use the GeneralUser default)")
    return inst.sf2(file=path.as_posix(), **{**base, **params})


SFZ_SOUNDS = {
    'piano': ('salamander-grand', 'sampled/grand_piano', {'width': 0.6, 'polyphony': 160}, 7.5,
              {'hp.freq': 40, 'low.freq': 120, 'low.gain': -1.0, 'peak1.freq': 320, 'peak1.gain': -2.0,
               'peak1.q': 0.9, 'peak3.freq': 3200, 'peak3.gain': -1.0, 'peak3.q': 0.9, 'high.freq': 11000,
               'high.gain': 0.5},
              'Salamander Grand Piano V3 (SFZ, release samples; CC-BY 3.0 Alexander Holm - credit it)'),
    'bass': ('meatbass', 'sampled/upright_bass', {}, 1.5,
             {'hp.freq': 42, 'hp.slope': 24, 'low.freq': 90, 'low.gain': -5.0, 'peak1.freq': 180, 'peak1.gain': -2.5,
              'peak1.q': 1.0, 'peak2.freq': 900, 'peak2.gain': 2.0, 'peak2.q': 1.1, 'high.freq': 7000,
              'high.gain': -1.0},
             'Meatbass pizz (Karoryfer, CC0: 4 velocity layers x 5 takes)'),
    'drums': ('swirly-drums', 'sampled/brush_kit', {'width': 1.3}, 4.0,
              {'hp.freq': 80, 'hp.slope': 24, 'low.freq': 120, 'low.gain': -3.0, 'peak1.freq': 400,
               'peak1.gain': -1.5, 'peak1.q': 0.8, 'high.freq': 9000, 'high.gain': -1.0},
              "Swirly Drums brush kit (Karoryfer, CC0; keymap SWIRLY_BRUSH, sweep=swirly_sweep(tempo))"),
    'sax': ('mtg-solo-sax', 'sampled/tenor_sax', {}, 8.5,
            {'hp.freq': 90, 'peak1.freq': 400, 'peak1.gain': -3.5, 'peak1.q': 0.8, 'peak2.freq': 1100,
             'peak2.gain': -3.5, 'peak2.q': 0.8, 'high.freq': 6000, 'high.gain': 1.5},
            'MTG tenor saxophone (legato player; CC-BY 4.0 - credit it)'),
}
"""The SFZ sample packs band() plays when they are installed (sampled_sounds='auto', the default): role -> (pack
id, library patch, params, dB on the track fader against the GeneralUser default, the eq band() gives it, credit).
Levelled to the GeneralUser balance on medium-swing material (two calibration lines at 138 BPM, velocities 88 / 100:
comping, bass and brushes within ~1 dB; the MTG tenor needed +8.5 dB - at +6 it read 2.5 dB under the GeneralUser
tenor); the Salamander plays at width 0.6 (at 0.8 its melody register measured correlation ~0, hollow in mono). Each
falls back to GeneralUser GS alone when its pack is missing. With the Swirly brush kit the brush parts need its keymap: jazz.brushes(..., kit=b.kit, sweep=b.sweep);
the MTG tenor is a legato player with live dynamics: horn_line(..., **b.horn) (param='dynamics', our vibrato)."""


def _sfz_sound(role: str):
    """The library patch of a SFZ_SOUNDS role, without its default sends (band() makes its own returns)."""
    from . import patches as _patches
    _, name, params, _, _, _ = SFZ_SOUNDS[role]
    p = _patches.get(name)
    p = p.with_mix(sends={k: None for k in p.sends})
    return p.but(**params) if params else p


def band(s, *, sax: bool = False, piano=None, bass=None, drums=None, horn=None, room: bool = True,
         plate: bool = True, sampled_sounds='auto', feel: Feel | None = None, ids: dict | None = None,
         piano_width: float | None = None) -> Band:
    """Set up a jazz trio (+ tenor sax with sax=True) on song `s`: tracks with sounds, placement, eq, the shared
    small room (+ a plate for the horn and the piano's right hand) and each part's feel (swing at the tempo's ratio
    and its lay-back) already set as the track groove.

      comp   piano left hand / comping ('comp')      piano  right hand: melody, solo ('piano')
      bass   upright ('bass')                        drums  brush kit ('drums')
      sax    tenor saxophone ('sax', mono)           room / plate   reverb buses ('room', 'plate')

    sampled_sounds: 'auto' (default) plays each role from its installed SFZ pack (SFZ_SOUNDS: Salamander Grand with
    release samples, Meatbass pizz, Swirly Drums brushes, the MTG legato tenor) and from GeneralUser GS where the
    pack is missing; True wants every SFZ pack (a missing one is an error naming `samples fetch`); 'sf2' the older
    SoundFont packs (SAMPLED_SOUNDS: Salamander Grand, FreePats tenor); False GeneralUser only ('Grand Piano' width
    2.0, 'Acoustic Bass', the 'Brush' kit bank 128 program 40, 'Tenor Sax'). The Band says what it got:
    b.sounds (role -> description), b.kit / b.sweep (the brush keymap for jazz.brushes: SWIRLY_BRUSH + sweep=
    swirly_sweep(tempo) on the Swirly kit, else GM_BRUSH) and b.horn (horn_line options for the sax sound: param, vibrato, glide).
    Balance (the recipe; dry track levels measured on medium-swing material): a piano melody or the sax
    at about -19.5 LUFS, comping -23.5 (3-5 dB under the lead), bass -22.5 (audible, 3 dB under), brushes -29 (8-12
    dB under). Pass piano= / bass= / drums= / horn= (any sound: inst.sf2(...), a sampled instrument, a patch) to swap
    one - then set its level / the track gain_db to keep that balance; ids={'comp': 'lh', ...} renames tracks.
    Pans (audience view): piano 0.15 (a wide stereo piano: the comping register sits left of the treble), bass
    and drums centre (the kit's own spread + a Haas microshift), sax -0.25 (+ a subtle microshift). The piano
    tracks get a stereo widener of piano_width (default PIANO_WIDTH: 1.7 on the narrow GeneralUser piano, 1.0 on a
    sampled / passed-in piano, which is stereo already - more makes it hollow in mono).
    The sax track has NO groove: horn_line() bakes the feel into its clip so the expression lanes line up.
    Complete productions (IR rooms, master chain, more ensembles): bands.make('jazz_trio' | 'jazz_quartet' |
    'jazz_ballad' | 'bossa', s) - agentsound/bandlib/jazz.py."""
    if sampled_sounds not in ('auto', True, False, 'sf2'):
        raise ComposeError(f"band sampled_sounds must be 'auto', True, False or 'sf2', got {sampled_sounds!r}")
    from . import library
    f = feel if feel is not None else Feel(s.tempo, beats_per_bar=s.beats_per_bar)
    names = {'comp': 'comp', 'piano': 'piano', 'bass': 'bass', 'drums': 'drums', 'sax': 'sax', 'room': 'room',
             'plate': 'plate'}
    names.update(ids or {})
    room_bus = plate_bus = None
    if room:
        room_bus = s.bus(names['room'], [fx.reverb(type='room', mix=1.0, decay=1.2, size=0.45, predelay=12,
                                                   lowcut=200, highcut=9000, damping=6500, early=0.6, width=1.1)])
    if plate:
        plate_bus = s.bus(names['plate'], [fx.reverb(type='plate', mix=1.0, decay=1.9, predelay=28, lowcut=280,
                                                     highcut=8500, damping=6000, width=1.2)])

    def sends(r, p=None):
        out = {}
        if room_bus is not None and r is not None:
            out[room_bus] = r
        if plate_bus is not None and p is not None:
            out[plate_bus] = p
        return out or None
    eqs = {'piano': {'hp.freq': 45, 'peak1.freq': 320, 'peak1.gain': -1.5, 'peak1.q': 0.9, 'high.freq': 9000,
                     'high.gain': 1.5},
           'sax': {'hp.freq': 90, 'peak1.freq': 380, 'peak1.gain': -2.5, 'peak1.q': 1.0, 'peak3.freq': 2600,
                   'peak3.gain': 1.5, 'peak3.q': 0.8},
           'bass': {'hp.freq': 35, 'peak1.freq': 170, 'peak1.gain': -2.5, 'peak1.q': 0.9,
                    'peak2.freq': 850, 'peak2.gain': 2.0, 'peak2.q': 1.2},
           'drums': {'hp.freq': 45}}
    trim = {'piano': 0.0, 'bass': 0.0, 'drums': 0.0, 'sax': 0.0}
    got = {'piano': piano, 'bass': bass, 'drums': drums, 'sax': horn}
    desc = {r: ('passed in' if v is not None else 'GeneralUser GS') for r, v in got.items()}
    if sampled_sounds in ('auto', True):
        for role in ('piano', 'bass', 'drums', 'sax'):
            if got[role] is not None or (role == 'sax' and not sax):
                continue
            pack = SFZ_SOUNDS[role][0]
            if not (library.SAMPLES / pack / 'SOURCE.json').is_file():
                if sampled_sounds is True:
                    raise ComposeError(f"jazz.band(sampled_sounds=True): the {role} pack {pack!r} is not installed; "
                                       f"install it with `python -m agentsound samples fetch {pack}` (or use "
                                       f"sampled_sounds='auto': GeneralUser where a pack is missing)")
                continue
            got[role] = _sfz_sound(role)
            trim[role], eqs[role], desc[role] = SFZ_SOUNDS[role][3], dict(SFZ_SOUNDS[role][4]), SFZ_SOUNDS[role][5]
    elif sampled_sounds == 'sf2':
        if got['piano'] is None:
            got['piano'], eqs['piano'], desc['piano'] = (sampled('piano'), dict(SAMPLED_SOUNDS['piano'][3]),
                                                         SAMPLED_SOUNDS['piano'][4])
        if got['sax'] is None and sax:
            got['sax'], eqs['sax'], desc['sax'] = (sampled('sax'), dict(SAMPLED_SOUNDS['sax'][3]),
                                                   SAMPLED_SOUNDS['sax'][4])
    piano, bass, drums, horn = got['piano'], got['bass'], got['drums'], got['sax']
    if piano_width is None:
        piano_width = PIANO_WIDTH['generaluser' if piano is None else 'other']
    pw = _num(piano_width, 'band piano_width', 0.0, 2.0)
    comp_sound = piano if piano is not None else inst.sf2('Grand Piano', width=2.0, level=7.4)
    rh_sound = piano if piano is not None else inst.sf2('Grand Piano', width=2.0, level=7.4)
    comp_t = s.track(names['comp'], comp_sound, fx=[fx.eq(dict(eqs['piano'])), fx.width(width=pw, monobass=120)],
                     gain_db=-7.0 + trim['piano'], pan=0.15, sends=sends(-15))
    comp_t.groove(f.groove('comp'))
    rh = s.track(names['piano'], rh_sound, fx=[fx.eq(dict(eqs['piano'])), fx.width(width=pw, monobass=120)],
                 gain_db=0.0 + trim['piano'], pan=0.15, sends=sends(-14, -20))
    rh.groove(f.groove('piano'))
    bass_sound = bass if bass is not None else inst.sf2('Acoustic Bass', level=0.0)
    bass_t = s.track(names['bass'], bass_sound,
                     # a peak catcher, not a leveller: the old -20 dB 3:1 automakeup compressor flattened the
                     # walking line's note-to-note dynamics (flat_dynamics); the makeup stands in for its automakeup
                     fx=[fx.eq(eqs['bass']),
                         fx.compressor(threshold=-9, ratio=3.0, knee=6, attack=1.5, release=90, makeup=2.5)],
                     gain_db=-4.5 + trim['bass'], pan=0.0, sends=sends(-20))
    bass_t.groove(f.groove('bass'))
    drum_sound = drums if drums is not None else inst.sf2(bank=128, program=40, width=1.5, level=12.0)
    drums_t = s.track(names['drums'], drum_sound, fx=[fx.eq(eqs['drums']),
                                                     fx.microshift(style='smooth', detune=0, delay=12, focus=300,
                                                                   mix=0.3)],
                      gain_db=-3.0 + trim['drums'], pan=0.0,
                      sends=sends(-12))
    drums_t.groove(f.groove('drums'))
    swirly = desc['drums'] == SFZ_SOUNDS['drums'][5]
    sax_t = None
    horn_opts = {'param': 'expression', 'vibrato': False}      # GeneralUser's tenor has its own vibrato
    if sax:
        horn_sound = horn if horn is not None else inst.sf2('Tenor Sax', mono='on', level=2.0)
        if desc['sax'] == SFZ_SOUNDS['sax'][5]:
            horn_opts = {'param': 'dynamics', 'vibrato': True, 'glide': 0.2}
        elif desc['sax'] != 'GeneralUser GS':
            horn_opts = {'param': 'expression', 'vibrato': True}
        sax_t = s.track(names['sax'], horn_sound,
                        fx=[fx.eq(eqs['sax']),
                            fx.microshift(style='smooth', detune=3, delay=10, focus=300, mix=0.15)],
                        gain_db=-1.5 + trim['sax'], pan=-0.25, sends=sends(-11, -13))
    return Band(comp=comp_t, piano=rh, bass=bass_t, drums=drums_t, sax=sax_t, room=room_bus, plate=plate_bus,
                feel=f, kit=dict(SWIRLY_BRUSH if swirly else GM_BRUSH),
                sweep=swirly_sweep(s.tempo, s.beats_per_bar) if swirly else None,
                stir=(1.9, 0.8) if swirly else (1.0, 1.0),
                horn=horn_opts, sounds={r: d for r, d in desc.items() if r != 'sax' or sax})
