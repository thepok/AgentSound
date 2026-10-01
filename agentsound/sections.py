"""Section plans: a song's parts written per SECTION (the pop / synthwave package).

A synthwave or pop arrangement places the same kinds of parts in every section - a chord bed, an arpeggio, a bass
line, a looped drum groove with fills and crashes - and rides levels, filters and sends section by section. These
helpers write those parts from the section's harmony (`s.section(..., prog=)`, `s.form(parts=)`: `sec.prog`) and a
plan per section; every value is a DEFAULT that a per-section dict overrides, and raw clips / automate() keep
working next to them (a part that needs something special is written by hand).

Per-section values: any option may be a dict {section (or its name): value, '*': default} - a section missing from
the dict (and no '*') leaves the option out (the generator's own default).

    pad.chords(intro, verse1, chorus1, voicing='spread', register=('C3', 'C5'), vel={'*': 80, chorus1: 84},
               bars={verse1: (8, 16)})                     # bars 8-16 of verse 1 only (placed at its bar 8)
    arp.arp('updown', verse1, chorus1, rate='1/16', octaves=2, register=('F#4', 'F#5'))
    bass.bassline('octave', verse1, chorus1, rate='1/8', gate=0.85, prog={verse1: s.prog('F#m')})
    kit.plan({verse1: [g_verse, (8, g_verse_b)], chorus1: g_chorus}, fills={chorus1: (8, tom_fill(2))},
             crashes={verse1: 112, chorus1: 118})
    kit.levels({'verse1': [(0, -3), (8, -1.5)], 'chorus1': 0}, drops=['build'])
    pad.lane('instrument.cutoff', {'intro': (300, 900, 'exp'), 'chorus1': 1600})

The section lanes (lane / levels) write automation points (automation.py): a section value is where the section
starts (a jump there, or a `glide` of beats into it), a tuple (a, b[, curve]) a move across the section, a list of
(bar, value[, curve]) marks inside it (no curve: a jump; a curve: a move arriving there). A list instead of a dict
is a lane of marks (position, value[, curve]) - the first is where the lane starts, the rest jump unless a curve is
given."""

from __future__ import annotations

from .automation import JUMP, riser as _riser
from .patterns import Clip, as_clip, beats
from .theory import ComposeError

_EPS = 1e-9
_MISSING = object()


# ------------------------------------------------------------------------------------------- per-section values

def is_per_section(value) -> bool:
    """A per-section dict: {Section | name | '*': value}."""
    return isinstance(value, dict)


def per(song, value, sec, what: str = 'option'):
    """The value of a (maybe per-section) option for `sec`; _MISSING when a per-section dict has no entry and no '*'."""
    if not is_per_section(value):
        return value
    for k in value:
        if k == '*':
            continue
        if not (hasattr(k, 'start') and hasattr(k, 'name')) and not isinstance(k, str):
            raise ComposeError(f"{what}: per-section keys are sections, section names or '*', got {k!r}")
        name = k.name if hasattr(k, 'name') else k
        if not any(s.name == name for s in song.sections):
            raise ComposeError(f"{what}: no section {name!r} (sections: {', '.join(s.name for s in song.sections)})")
    if sec in value:
        return value[sec]
    if sec.name in value:
        return value[sec.name]
    return value.get('*', _MISSING)


def sections_of(song, args, what: str) -> list:
    """Flatten Sections / names / lists of them into song Sections (in the order given)."""
    out = []
    for a in args:
        if isinstance(a, (list, tuple)):
            out += sections_of(song, a, what)
        elif isinstance(a, str):
            out.append(song[a])
        elif hasattr(a, 'start') and hasattr(a, 'bars') and hasattr(a, 'name'):
            out.append(a)
        else:
            raise ComposeError(f"{what}: give sections (or their names), got {a!r}")
    if not out:
        raise ComposeError(f"{what}: name the sections to play, e.g. pad.chords(verse, chorus, ...)")
    return out


def _window(spec, sec, what: str):
    """bars= of a section: None (all), (a, b), (a, None) or a (from bar a) -> (a, b) bars."""
    if spec is None or spec is _MISSING:
        return None
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        a, b = float(spec), sec.bars
    elif isinstance(spec, (tuple, list)) and len(spec) == 2:
        a, b = float(spec[0]), sec.bars if spec[1] is None else float(spec[1])
    else:
        raise ComposeError(f"{what}: bars= is a bar (from there) or (from, to) bars of section {sec.name!r}, "
                           f"got {spec!r}")
    if not 0 <= a < b <= sec.bars + _EPS:
        raise ComposeError(f"{what}: bars ({a:g}, {b:g}) are outside section {sec.name!r} ({sec.bars:g} bars)")
    return a, b


def _then(clip, fns, what: str):
    if fns is None or fns is _MISSING:
        return clip
    for f in (fns if isinstance(fns, (list, tuple)) else [fns]):
        if not callable(f):
            raise ComposeError(f"{what}: then= takes a function clip -> clip (or a list of them), got {f!r}")
        clip = as_clip(f(clip))
    return clip


def place(track, clip, sec, *, bars=None, transpose=0, scale=1.0, then=None, crescendo=None, cut=True,
          what='part'):
    """Play `clip` as the part of section `sec`: then= (functions clip -> clip: clip.legato, ...) shape it first;
    it fills the section - a shorter clip repeats, notes ringing past the section end are cut there (cut=False: a
    clip exactly as long as the section keeps them) - or with bars=(a, b) only those bars of it, at bar a;
    crescendo=(from, to) shapes the placed part; transpose / scale (a velocity factor) as for track.play()."""
    c = _then(as_clip(clip), then, what)
    L = sec.length
    win = _window(bars, sec, what)
    kw = {}
    if transpose not in (None, 0, _MISSING):
        kw['transpose'] = transpose
    if scale not in (None, 1.0, 1, _MISSING):
        kw['vel'] = scale
    part = c if (cut is False and abs(c.length - L) < 1e-9) else c.loop(L)
    at = sec.start
    if win is not None:
        a, b = win
        part = part.slice(a * sec.beats_per_bar, b * sec.beats_per_bar)
        at = sec.bar(a)
    if crescendo not in (None, _MISSING):
        part = part.crescendo(*crescendo)
    track.play(part, at, **kw)


_PLACE_KEYS = ('prog', 'bars', 'transpose', 'scale', 'then', 'crescendo', 'cut')


def _harmony_parts(track, kind: str, sections, gen_args: tuple, kw: dict) -> None:
    """track.chords / arp / bassline: per section the section's progression (or prog=) through the generator."""
    song = track._song
    what = f"track {track.id!r}: {kind}()"
    secs = sections_of(song, sections, what)
    for sec in secs:
        opts = {}
        for k, v in kw.items():
            r = per(song, v, sec, f"{what} {k}=")
            if r is not _MISSING:
                opts[k] = r
        prog = opts.pop('prog', None)
        if prog is None:
            prog = sec.prog
        if prog is None:
            raise ComposeError(f"{what}: section {sec.name!r} has no progression - give it one "
                               f"(s.section(..., prog=...), s.form(..., parts=...)) or pass prog=")
        if isinstance(prog, str):
            prog = song.prog(prog, meter=sec.meter)
        pl = {k: opts.pop(k) for k in _PLACE_KEYS[1:] if k in opts}
        args = tuple(per(song, a, sec, what) for a in gen_args)
        if kind == 'chords':
            clip = prog.block(**opts)
        elif kind == 'arp':
            clip = prog.arp(*args, **opts)
        else:
            clip = prog.bass(*args, **opts)
        place(track, clip, sec, what=f"{what} in {sec.name!r}", **pl)


# --------------------------------------------------------------------------------------------- the drum plan

def _entries(spec, sec, what: str) -> list:
    """A section's plan: clip | [clip | (bar, clip) | (bar, clip, bars)] -> [(from bar, to bar, clip)]."""
    items = spec if isinstance(spec, list) else [spec]
    rows = []
    for it in items:
        if isinstance(it, tuple):
            if len(it) not in (2, 3) or not isinstance(it[0], (int, float)) or isinstance(it[0], bool):
                raise ComposeError(f"{what}: plan entries are a clip, (bar, clip) or (bar, clip, bars), got {it!r}")
            rows.append((float(it[0]), it[1], None if len(it) == 2 else float(it[2])))
        else:
            rows.append((0.0 if not rows else None, it, None))
    out = []
    for i, (a, clip, n) in enumerate(rows):
        if a is None:
            raise ComposeError(f"{what}: in section {sec.name!r} only the first entry may leave out its bar")
        if n is not None:
            b = a + n
        else:
            nxt = next((r[0] for r in rows[i + 1:]), None)
            b = sec.bars if nxt is None else nxt
        if not 0 <= a < b <= sec.bars + _EPS:
            raise ComposeError(f"{what}: entry at bar {a:g} ({b - a:g} bars) does not fit section {sec.name!r} "
                               f"({sec.bars:g} bars)")
        out.append((a, b, clip))
    return out


def _fill_rows(song, sec, spec, what: str) -> list:
    """A section's fill rule -> [(position, clip, pieces)]: clip (at the end of every 8 bars), (every, clip) or
    (every, clip, last) - the fill ends on each phrase end; `last` replaces the one into the section end."""
    if isinstance(spec, tuple) and spec and isinstance(spec[0], (int, float)) and not isinstance(spec[0], bool):
        if len(spec) not in (2, 3):
            raise ComposeError(f"{what}: a section's fills are a clip, (every_bars, clip) or (every_bars, clip, "
                               f"last_clip), got {spec!r}")
        every, clip, last = float(spec[0]), spec[1], spec[2] if len(spec) == 3 else None
    else:
        every, clip, last = 8.0, spec, None
    if every <= 0:
        raise ComposeError(f"{what}: fills every {every:g} bars")
    out = []
    k = 1
    while every * k <= sec.bars + _EPS:
        end_bar = every * k
        f = last if (last is not None and end_bar >= sec.bars - _EPS) else clip
        fc, pieces = _fill_clip(f, what)
        out.append((sec.bar(end_bar) - fc.length, fc, pieces))
        k += 1
    return out


def _fill_clip(spec, what: str):
    if isinstance(spec, tuple):
        if len(spec) != 2:
            raise ComposeError(f"{what}: a fill is a clip or (clip, pieces to clear under it), got {spec!r}")
        return as_clip(spec[0]), spec[1]
    return as_clip(spec), None


_RULES = ('section', 'phrase')


def _rule_fills(song, secs, fills, phrase, fill_every, same_every, what) -> list:
    """The song-wide fill rules fills['section'] (into each planned section's end) and fills['phrase'] (every
    `phrase` bars inside), kept apart by a Budget (agentsound.budget, the players' one ledger): fill_every bars
    between two fills, same_every bars between two of the same rule; the section ends are decided first."""
    from .budget import Budget
    cands = []
    for sec in secs:
        bpb = sec.beats_per_bar
        k = 1
        while phrase * k <= sec.bars + _EPS:
            last = phrase * k >= sec.bars - _EPS
            name = 'section' if last else 'phrase'
            if name in fills:
                fc, pieces = _fill_clip(fills[name], f"{what} fills[{name!r}]")
                cands.append(dict(t=sec.bar(phrase * k) - fc.length, cls='fill', name=name, score=2.0 if last else 1.0,
                                  clip=fc, pieces=pieces))
            k += 1
        if phrase * (k - 1) < sec.bars - _EPS and 'section' in fills:      # a section not a whole number of phrases
            fc, pieces = _fill_clip(fills['section'], f"{what} fills['section']")
            cands.append(dict(t=sec.end - fc.length, cls='fill', name='section', score=2.0, clip=fc, pieces=pieces))
    bud = Budget({'fill': float(fill_every) * 4.0}, same_every=float(same_every) * 4.0, same=('fill',))
    kept = bud.keep(cands) if fill_every or same_every else cands
    return [(c['t'], c['clip'], c['pieces']) for c in sorted(kept, key=lambda c: c['t'])]


def _drum_plan(track, plan: dict, *, fills=None, crashes=None, crash=None, keep=None, phrase: float = 8,
              fill_every: float = 0, same_every: float = 0) -> None:
    """track.plan(): loops per section, then the fills (replacing what they cover), then the crashes."""
    from .patterns import crash as _crash, drum
    song = track._song
    what = f"track {track.id!r}: plan()"
    if not isinstance(plan, dict):
        raise ComposeError(f"{what}: give a dict {{section: clip | [clip, (bar, clip), (bar, clip, bars)]}}")
    planned = []
    for key, spec in plan.items():
        sec = sections_of(song, [key], what)[0]
        planned.append(sec)
        for a, b, clip in _entries(spec, sec, what):
            if clip is None:
                continue
            track.loop(clip, sec.bar(a), until=sec.bar(b))
    rows = []
    fills = fills or {}
    own = set()
    for key, spec in fills.items():
        if isinstance(key, str) and key in _RULES:
            continue
        if isinstance(key, (int, float, tuple)) and not isinstance(key, bool):
            fc, pieces = _fill_clip(spec, what)
            rows.append((song._at(key), fc, pieces))
        else:
            sec = sections_of(song, [key], what)[0]
            own.add(sec.name)
            rows += _fill_rows(song, sec, spec, f"{what} fills[{sec.name!r}]")
    if any(k in fills for k in _RULES if isinstance(k, str)):
        rows += _rule_fills(song, [s for s in planned if s.name not in own], fills, float(phrase), fill_every,
                            same_every, what)
    for at, fc, pieces in rows:
        end = at + max(fc.length, 1e-9)
        if pieces is None and keep:
            ks = {drum(p) for p in keep}
            pieces = sorted({n.pitch for n in track._notes if at - 1e-9 <= n.start < end - 1e-9} - ks)
            if pieces:
                track.clear(at, end, pitches=pieces)
        elif pieces is not None:
            track.clear(at, end, pitches=list(pieces))
        else:
            track.clear(at, end)
        track.play(fc, at)
    if crashes is not None:
        if isinstance(crashes, dict):
            items = list(crashes.items())
        else:
            items = [(p, None) for p in crashes]
        for pos, vel in items:
            if vel is None:
                c = crash if isinstance(crash, Clip) else _crash(112 if crash is None else crash)
            elif isinstance(vel, Clip):
                c = vel
            else:
                c = _crash(vel)
            track.play(c, pos)


# --------------------------------------------------------------------------------------------- section lanes

def _marks(spec, sec, what: str) -> list:
    """A section's lane value -> marks [(bar, value[, curve])]."""
    if isinstance(spec, bool):
        raise ComposeError(f"{what}: {spec!r} is not a lane value")
    if isinstance(spec, (int, float)):
        return [(0.0, float(spec))]
    if isinstance(spec, tuple):
        if len(spec) not in (2, 3):
            raise ComposeError(f"{what}: a move across section {sec.name!r} is (from, to[, curve]), got {spec!r}")
        return [(0.0, float(spec[0])), (sec.bars, float(spec[1]), spec[2] if len(spec) == 3 else 'linear')]
    if isinstance(spec, list):
        out = []
        for m in spec:
            if not isinstance(m, (tuple, list)) or len(m) not in (2, 3):
                raise ComposeError(f"{what}: marks in section {sec.name!r} are (bar, value[, curve]), got {m!r}")
            out.append((float(m[0]), float(m[1])) + ((m[2],) if len(m) == 3 else ()))
        return out
    raise ComposeError(f"{what}: section {sec.name!r}: a lane value is a number, (from, to[, curve]) or a list of "
                       f"(bar, value[, curve]) marks, got {spec!r}")


def lane_points(song, spec, *, base: float = 0.0, glide: float = 0.0, curve: str = 'smooth', default=None,
                drops=(), drop: float = -60.0, hold: bool = False, end: bool = False, what: str = 'lane') -> list:
    """Automation points of a section lane (see the module doc). glide > 0: each section start glides there over
    `glide` beats with `curve` (the first section starts plain); glide 0: a jump - a 'step' point, or with hold=True
    the old value written again at the jump (s.arc's way; the same sound). default: the value of the sections the
    dict leaves out (None: they continue). drops: sections whose last beat falls to `drop`. end=True closes the lane
    with its last value at the song end."""
    b0 = float(base)
    if isinstance(spec, list):                       # a lane of marks
        pts = []
        cur = None
        for i, m in enumerate(spec):
            if not isinstance(m, (tuple, list)) or len(m) not in (2, 3):
                raise ComposeError(f"{what}: marks are (position, value[, curve]), got {m!r}")
            at, v = song._at(m[0]), b0 + float(m[1])
            if i == 0:
                pts.append((at, v))
            elif len(m) == 3:
                pts.append((at, v, m[2]))
            elif hold:
                pts += [(at, cur), (at, v)]
            else:
                pts.append((at, v, 'step'))
            cur = v
        return pts
    if not isinstance(spec, dict):
        raise ComposeError(f"{what}: give {{section: value}} or a list of (position, value[, curve]) marks")
    per(song, spec, song.sections[0], what)          # validates the keys
    drop_names = {d if isinstance(d, str) else d.name for d in drops}
    unknown = drop_names - {s.name for s in song.sections}
    if unknown:
        raise ComposeError(f"{what}: drops: no section {sorted(unknown)[0]!r}")
    pts: list = []
    cur = None
    for sec in song.sections:
        v = per(song, spec, sec, what)
        if v is _MISSING:
            v = default
        if v is not None:
            for m in _marks(v, sec, what):
                at, val = sec.bar(m[0]), b0 + m[1]
                if len(m) == 3:
                    pts.append((at, val, m[2]))
                elif m[0] == 0 and glide > 0:
                    if cur is None:
                        pts.append((at, val))
                    else:
                        pts += [(max(at - glide, pts[-1][0] + JUMP), cur), (at, val, curve)]
                elif hold:
                    if cur is not None:
                        pts.append((at, cur))
                    pts.append((at, val))
                else:
                    pts.append((at, val, 'step'))
                cur = val
        if sec.name in drop_names:
            e = sec.end - 1
            if hold:
                pts += [(e, cur), (e, float(drop))]
            else:
                pts.append((e, float(drop), 'step'))
            cur = float(drop)
    if end and cur is not None:
        pts.append((song.length, cur))
    if not pts:
        raise ComposeError(f"{what}: no points (no section listed and no default)")
    return pts


# ------------------------------------------------------------------------------------------------ transitions

_HIT_PATCHES = {'riser': 'synthwave/noise_riser', 'impact': 'synthwave/impact', 'down': 'synthwave/downlifter'}


class Transitions:
    """The fx-hit tracks of a song and the moves into a section (Song.transitions): a riser opening into it, a
    reversed swell sucking into it, an impact and / or a downlifter on its downbeat, a breath before it.

        fxh = s.transitions(riser=riser_t, reverse=rev, impact=boom, down=fall, pitch='A3')
        fxh.into(chorus1, riser=16, reverse=2, impact=('D2', 120), breath=1)
        fxh.into(final, riser=dict(beats=15, end=-1, vel=115), impact=('E1', 124), breath=1, keep=[robot])
        fxh.into(breakdown, down=('A3', 8, 110))

    into(at, riser=, reverse=, impact=, down=, breath=, keep=(), cut=True):
      riser    beats, or dict(beats=, end= beats from `at` where it peaks (-1: into a breath), pitch=, vel=, dur=,
               cutoff=(lo, hi), hpf=(lo, hi)) - track.rise()
      reverse  beats, or such a dict (default cutoff (2500, 16000), no high-pass): a short swell into `at`
      impact   (pitch, vel[, beats]) on the downbeat (4 beats);  down: (pitch, beats, vel) on the downbeat
      breath   beats of silence before `at` for every other track (Song.breath; keep= more tracks that go on)
    The tracks: a Track, a patch name (a new track 'riser' / 'reverse' / 'impact' / 'down') or None."""

    def __init__(self, song, *, riser=None, reverse=None, impact=None, down=None, pitch='C4'):
        self.song, self.pitch = song, pitch
        self.riser = self._track('riser', riser)
        self.reverse = self._track('reverse', reverse)
        self.impact = self._track('impact', impact)
        self.down = self._track('down', down)

    def _track(self, kind, x):
        if x is None or hasattr(x, 'play'):
            return x
        if x is True:
            x = _HIT_PATCHES.get(kind, 'synthwave/noise_riser')
        if not isinstance(x, str):
            raise ComposeError(f"transitions({kind}=...): a track, a patch name or None, got {x!r}")
        return self.song.track(kind, x)

    @property
    def tracks(self) -> list:
        return [t for t in (self.riser, self.reverse, self.impact, self.down) if t is not None]

    def _need(self, kind):
        t = getattr(self, kind)
        if t is None:
            raise ComposeError(f"transitions: no {kind} track (s.transitions({kind}=track or patch name))")
        return t

    def _rise(self, track, at, spec, defaults, what):
        o = {'beats': spec} if isinstance(spec, (int, float)) and not isinstance(spec, bool) else dict(spec)
        if 'beats' not in o:
            raise ComposeError(f"transitions.into({what}=...): give the beats (a number or dict(beats=...))")
        o = dict(defaults, **o)
        beats_, end = o.pop('beats'), o.pop('end', 0)
        o.setdefault('pitch', self.pitch)
        a = self.song._at(at)
        return rise(track, a + end if end else at, beats_, **o)

    def into(self, at, *, riser=None, reverse=None, impact=None, down=None, breath=None, keep=(), cut=True):
        if riser is not None:
            self._rise(self._need('riser'), at, riser, {}, 'riser')
        if reverse is not None:
            self._rise(self._need('reverse'), at, reverse, {'cutoff': (2500.0, 16000.0), 'hpf': None}, 'reverse')
        if impact is not None:
            if not isinstance(impact, tuple) or len(impact) not in (2, 3):
                raise ComposeError(f"transitions.into(impact=...): (pitch, vel[, beats]), got {impact!r}")
            self._need('impact').note(impact[0], at, impact[2] if len(impact) == 3 else 4, impact[1])
        if down is not None:
            if not isinstance(down, tuple) or len(down) != 3:
                raise ComposeError(f"transitions.into(down=...): (pitch, beats, vel), got {down!r}")
            self._need('down').note(down[0], at, down[1], down[2])
        if breath is not None:
            self.song.breath(before=at, beats=breath, keep=self.tracks + list(keep), cut=cut)
        return self


def rise(track, end, length=16, *, pitch='C4', vel: int = 100, dur=None, cutoff=(300.0, 12000.0),
         hpf=(20.0, 1500.0)):
    """A riser (noise sweep) into `end`: one note of `dur` beats (default `length`) starting `length` beats before
    `end`, its filter opening over those beats (automation.riser on 'instrument.cutoff' / 'instrument.hpf'; None
    leaves one out). A reversed swell is the same with a short length: rev.rise(chorus, 2, cutoff=(2500, 16000),
    hpf=None)."""
    song = track._song
    e = song._at(end)
    L = beats(length)
    if L <= 0 or e - L < -1e-9:
        raise ComposeError(f"track {track.id!r}: rise() of {L:g} beats into beat {e:g} would start before 0")
    track.note(pitch, e - L, L if dur is None else beats(dur), vel)
    for target, rng in (('instrument.cutoff', cutoff), ('instrument.hpf', hpf)):
        if rng is not None:
            track.automate(target, _riser(e, length=L, lo=rng[0], hi=rng[1]))
    return track
