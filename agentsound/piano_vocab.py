"""The jazz pianist's solo vocabulary for agentsound.soloist: phrases built from the soloist's shared material lines
and PLAYED by the pianist's hands (agentsound.pianist) - the right hand harmonizes each phrase (guide tones, 3rds,
6ths, drop 2, block chords, octaves: a piano solo is never a bare single-note line - HUMAN_FEEDBACK 2026-09-30
"als würde ein Kind Taste für Taste drücken"), the set pieces are the pianist's named moves (runs, cascading 4ths,
blues crushes, an octave run, a trill or tremolo on the climax: spice, budgeted - "etwas zu viele von diesen
schnellen Zwei-Tasten-Wechseln"), and the left hand comps under the whole solo (pianist.left_hand on its own track,
answering the right hand's rests) with the harmony pedal lifted for the dry runs. Use pianist.vocabulary(...)
(= vocabulary() here):

    from agentsound import soloist, pianist
    voc = pianist.vocabulary('straight', lh_track=b.comp, lh='guide')
    perf = soloist.solo(s, b.piano, voc, at=solo, prog=solo.prog, motif=HOOK, seed=3)

Moves (MOVES: name -> (roles, energy, density, spice, fast)):
  motif       the motif (the song's hook) in the right hand, harmonized (6ths / 3rds / guide tones), now and then a
              turn / mordent / crush on its long note
  answer      a falling pentatonic answer landing on a chord tone, guide tones under its strong notes
  riff        a short cell (mostly the motif's: soloist.motif_line), then answered: its rhythm again, re-fitted to
              the chord there, a new ending (call and response in one hand), in 3rds / 6ths
  sequence    the motif's cell developed (soloist.motif_line; else a target-first line, soloist.target_line) in
              8ths (16ths when dense), landing voiced
  block       the line in block chords (drop 2 / close / locked hands: Garland, Shearing) - every note in a
              'chords' stage (the block-chord chorus), elsewhere only the strong notes now and then
  octaves     the line in octaves with an inner tone (the climax sound)
  blues       a phrase with blues crushes / crushed grace notes / a slip note on its chord tones     (spice)
  run         a scale run up into a held, voiced peak                                                (spice)
  fourths     cascading 4ths down from a chord tone into a voiced landing                            (spice)
  octave_run  an octave run up into the peak                                                         (fast)
  tremolo     a held peak voicing as a tremolo swell                                                 (fast)
  trill       a pickup into a held peak trilled, landing with a turn                                 (fast)
  resolve     down to a chord tone of the closing chord: a long last note, a rolled voicing under it
"""

from __future__ import annotations

from . import soloist as S
from .patterns import Clip, Note, as_clip
from .soloist import Move, Part, Vocabulary
from .theory import ComposeError, Progression

__all__ = ['vocabulary', 'MOVES', 'STYLES']

MOVES = {
    'motif': (('motif',), 0.4, 0.4, False, False),
    'answer': (('answer', 'resolve', 'develop'), 0.5, 0.5, False, False),
    'riff': (('develop', 'answer'), 0.62, 0.6, False, False),
    'sequence': (('develop', 'burst'), 0.72, 0.78, False, False),
    'block': (('develop', 'climax', 'answer', 'chords'), 0.75, 0.5, False, False),
    'octaves': (('climax', 'develop'), 0.92, 0.5, False, False),
    'blues': (('answer', 'develop', 'climax'), 0.66, 0.55, True, False),
    'run': (('burst', 'develop'), 0.85, 0.95, True, True),
    'fourths': (('burst', 'answer', 'develop'), 0.74, 0.85, True, True),
    'octave_run': (('burst', 'climax'), 0.95, 0.95, True, True),
    'tremolo': (('climax',), 0.97, 0.4, True, True),
    'trill': (('climax', 'burst'), 0.9, 0.45, True, True),
    'resolve': (('resolve',), 0.35, 0.3, False, False),
}
"""name -> (roles, energy, density, spice, fast)."""

STYLES = {
    'straight': dict(weights={}, budget=dict(spice_every=2.0, fast_every=16, same_every=32), roll=(8, 20)),
    'bar': dict(weights={'blues': 1.6, 'octaves': 1.3, 'block': 0.8}, budget=dict(spice_every=1.5, fast_every=16,
                                                                                  same_every=32), roll=(6, 14)),
    'lush': dict(weights={'block': 1.6, 'octaves': 0.8, 'blues': 0.4, 'fourths': 0.7},
                 budget=dict(spice_every=2.0, fast_every=12, same_every=32), roll=(15, 25)),
    'ballad': dict(weights={'block': 1.4, 'sequence': 0.6, 'blues': 0.3, 'octave_run': 0.5},
                   budget=dict(spice_every=2.5, fast_every=12, same_every=32), roll=(15, 25)),
}
"""Vocabulary styles (like pianist.STYLES): move weights (1 = default), the soloist budget in bars (fast two-key
alternations about one per 16 bars) and the roll of the voicings (ms). The right hand's voicing devices per move are
the same in every style; arrange() rolls them in the style's range."""

# the voicing devices each move asks the pianist for (arrange(devices=...)), and its ornaments (never a FAST one:
# trills / tremolos are moves of their own, budgeted by the soloist)
_DEV = {
    'motif': {'sixths': 2.0, 'thirds': 2.0, 'guide': 2.0, 'drop2': 1.0},
    'answer': {'guide': 3.0, 'thirds': 1.5, 'single': 1.5},
    'riff': {'thirds': 2.0, 'sixths': 2.0, 'guide': 1.0},
    'sequence': {'thirds': 2.0, 'single': 1.5, 'guide': 1.5},
    'block': {'drop2': 3.0, 'close': 1.5, 'locked': 2.0},
    'octaves': {'octave': 4.0, 'locked': 1.0},
    'blues': {'guide': 2.0, 'thirds': 1.5, 'octave': 1.0},
    'land': {'drop2': 2.0, 'close': 1.0, 'octave': 1.0},
    'resolve': {'guide': 2.0, 'sixths': 1.5, 'drop2': 1.5},
}
_ORN = {'turn': 1.0, 'mordent': 1.0, 'crush': 1.0, 'restrike': 1.5, 'roll': 0.6}
_BLUES = {'blues_crush': 3.0, 'crush': 1.5, 'slip': 1.2}


# ------------------------------------------------------------------------------------------------ the hands

def _window(ctx, beats: float) -> Progression:
    """The changes from ctx.at for `beats` (the solo's progression, repeated when the solo is longer)."""
    p = ctx.prog
    if p is None:
        k = S.key_of(ctx)
        return Progression([('I' if not k.minorish else 'i', beats / 4.0)], key=k)
    items, x, need = [], (ctx.at - ctx.solo_start) % p.length, float(beats)
    while need > 1e-6:
        t = 0.0
        for c, d in p.items:
            a, t = t, t + d
            if t <= x + 1e-6:
                continue
            take = min(t - max(a, x), need)
            items.append((c, take))
            need -= take
            if need <= 1e-6:
                break
        x = 0.0
    return Progression._from(items, p.key, p.beats_per_bar)


def _cfg(ctx) -> dict:
    return ctx.memory['_piano']


def _mem(ctx):
    from . import pianist
    cfg = _cfg(ctx)
    if cfg.get('memory') is not None:
        return cfg['memory']
    return ctx.memory.setdefault('_piano_mem', pianist.Memory())


def _fit_harmony(ctx, c: Clip) -> Clip:
    """The line's held and on-beat notes onto the harmony under them: a note whose pitch class is neither a chord
    tone nor an available tension of its chord (an avoid note: the motif's E over a D7b9) moves a half or whole step
    to the nearest one that is - the motif keeps its shape and sounds right over every chord it meets."""
    from .theory import available_tensions
    out = []
    ns = sorted(c)
    for i, n in enumerate(ns):
        ch = ctx.chord(ctx.at + n.start)
        strong = n.dur >= 0.75 - 1e-6 or abs(n.start - round(n.start)) < 1e-6
        nx = ns[i + 1] if i + 1 < len(ns) else None
        # a short note on the beat stepping to the next one (an appoggiatura, a chromatic passing tone) is the line's
        passing = n.dur <= 0.5 + 1e-6 and nx is not None and nx.start - n.start <= 0.5 + 1e-6 \
            and 0 < abs(nx.pitch - n.pitch) <= 2
        if ch is None or not strong or passing:
            out.append(n)
            continue
        ok = {(ch.root + i) % 12 for i in ch.intervals} | {(ch.root + i) % 12 for i in available_tensions(ch)}
        if n.pitch % 12 in ok:
            out.append(n)
            continue
        lo, hi = getattr(ctx, 'range', (0, 127))
        q = next((n.pitch + d for d in (-1, 1, -2, 2) if (n.pitch + d) % 12 in ok and lo <= n.pitch + d <= hi),
                 next((n.pitch + d for d in (-1, 1, -2, 2) if (n.pitch + d) % 12 in ok), n.pitch))
        out.append(n._replace(pitch=q))
    return Clip._raw(out, c.length)


def _steps_clip(ctx, steps) -> Clip:
    """[(start, dur, pitch)] -> a Clip fitted to the harmony and touched in the phrase's velocity range (the
    pianist's touch: an arc per phrase, higher notes sing, passing notes lighter)."""
    from .humanize import touch
    if isinstance(steps, Clip):
        # a varied motif (soloist.vary: rhythm displacement) can start before its phrase: those notes are not
        # this phrase's (pianist.arrange's moves need start >= 0)
        c = steps if all(n.start >= 0 for n in steps) else Clip._raw([n for n in steps if n.start >= 0], steps.length)
    else:
        c = Clip._raw([Note(t, d, int(p), 90) for t, d, p in steps if t < ctx.beats - 1e-6], ctx.beats)
    c = _fit_harmony(ctx, c) if ctx.prog is not None else c
    lo, hi = ctx.vel
    return touch(c, lo, hi) if len(c) else c


def _play(ctx, steps, devices, *, ornaments=None, embellish=0.0, quick=0.0, density=None, voices=None,
          doubles=None) -> Part:
    """A line harmonized by pianist.arrange (no fills - the soloist plans the space; the left hand comes from
    place()): the move's voicing devices, its ornaments (budgeted song-wide in the pianist's Memory)."""
    from . import pianist
    c = _steps_clip(ctx, steps)
    if not len(c):
        return Part()
    cfg = _cfg(ctx)
    L = max(c.length, max(n.start + n.dur for n in c))
    arr = pianist.arrange(
        c, _window(ctx, L), bpm=ctx.bpm, key=S.key_of(ctx), style=cfg['arrange_style'],
        density=min(1.0, 0.35 + 0.6 * (ctx.density if density is None else density)), seed=ctx.rng.randrange(1 << 30),
        lh=None, floor=cfg['floor'], voices=voices, roll=cfg['roll'], fill=0.0, lead_in=False, section_end=False,
        devices=devices, ornaments=ornaments if ornaments is not None else {'restrike': 1.0},
        embellish=embellish, quick=quick, memory=_mem(ctx), at=ctx.at, ceiling=cfg['ceiling'],
        doubles=doubles if doubles is not None else cfg['doubles'])
    log = [(a, b, k, n) for a, b, k, n in arr.moves] + [(a, b, 'dry', 'pedal') for a, b in arr.dry]
    return Part(arr.rh, (), log)


def _figure(ctx, clip, name: str, dry: bool = True) -> Part:
    """A pianist move's notes as a Part (logged; dry: the pedal comes up for it)."""
    c = as_clip(clip)
    if not len(c):
        return Part()
    a, e = min(n.start for n in c), max(n.start + n.dur for n in c)
    log = [(a, e, 'move', name)] + ([(a, e, 'dry', 'pedal')] if dry else [])
    return Part(c, (), log)


def _land(ctx, t: float, pitch: int, dur: float, devices=None) -> Part:
    """A voiced landing note at t (relative), held dur beats."""
    sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t, beats=max(0.5, dur)))
    pt = _play(sub, [(0.0, dur, pitch)], devices or _DEV['land'], density=1.0)
    return pt.shifted(t)


def _grid(ctx, dense: bool, length: float, cut: bool = False) -> tuple:
    """A line's (grid, length): 8ths, or 16ths for a dense line when the feel allows one here (cfg['sixteenths']:
    {'every': bars between two 16th lines, 'bars': the longest one} - blind round 7: a bossa solo in 16ths for 7
    bars; None: as dense as the stage wants). A planned burst (the double-time stage) may run twice as long; a longer
    line stays in 8ths - or, cut=True, runs its 16ths that long (the caller goes on in 8ths). A 16th line is booked
    in the solo's memory."""
    if not dense or S.seconds(ctx, 0.25) < 0.11:
        return 0.5, length
    six = _cfg(ctx).get('sixteenths')
    if not six:
        return 0.25, length
    from .budget import Budget
    bud = ctx.memory.setdefault('_sixteenths', Budget({'16': six['every'] * ctx.bpb}))
    most = six['bars'] * ctx.bpb * (2.0 if ctx.stage == 'burst' else 1.0)
    if (length > most + 1e-6 and not cut) or not bud.allows(ctx.at, '16'):
        return 0.5, length
    bud.book(ctx.at, '16')
    return 0.25, min(length, most)


LINE_ON = 3.0
"""A move fills its slot (Move beats 0): material that ends more than LINE_ON beats before the slot's end (a motif, a
riff's call and answer, a resolution's few steps) goes on as a line (_line_on) - blind round 6: a 16-beat slot played
as a 2-bar cell and a 10-beat held note read as whole silent bars inside the solo's phrases."""


def _line_on(ctx, st) -> list:
    """[(start, dur, pitch)] steps carried on to the slot's end: when the last attack leaves more than LINE_ON beats,
    its held note is cut to a beat or less and the line continues from an 8th / a beat after it - the motif's cell
    developed or a target-first line (soloist.answer_line), landing on a chord tone held to the end."""
    st = sorted((float(t), float(d), int(p)) for t, d, p in st)
    if not st:
        return st
    t, d, p = st[-1]
    if ctx.beats - t < LINE_ON + 1.0 - 1e-6:
        return st
    d = min(d, ctx.rng.choice((0.5, 1.0, 1.0, 1.5)))
    st[-1] = (t, d, p)
    t0 = t + d + ctx.rng.choice((0.0, 0.5, 0.5, 1.0))
    sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t0, beats=ctx.beats - t0,
                       last=Note(ctx.at + t, d, p, 80)))
    more = S.answer_line(sub, grid_=0.5)
    return st + [(t0 + a, b, q) for a, b, q in more]


# ------------------------------------------------------------------------------------------------ moves

def m_motif(ctx) -> Part:
    c = S.motif_in_register(ctx)
    if not len(c):
        return Part()
    return _play(ctx, _line_on(ctx, [(n.start, n.dur, n.pitch) for n in c]), _DEV['motif'], ornaments=_ORN,
                 embellish=0.35, quick=0.12)


def m_answer(ctx) -> Part:
    st = _line_on(ctx, S.answer_line(ctx, grid_=_grid(ctx, ctx.density >= 0.6, ctx.beats)[0]))
    return _play(ctx, st, _DEV['answer'], ornaments={'crush': 1.0, 'mordent': 1.0}, quick=0.15)


def m_riff(ctx) -> Part:
    rng = ctx.rng
    g = rng.choice((0.5, 0.5, 1 / 3))
    n_ = rng.choice((2, 3, 3, 4))
    # the cell: mostly the motif's (soloist.MOTIVIC), else a short target-first line
    cell = (S.motif_line(ctx, length=max(1.5, n_ * 0.5 + 0.5)) if rng.random() < S.MOTIVIC else []) or         S.target_line(ctx, length=n_ * g, grid_=g, contour=rng.choice(('rise', 'arch', 'fall')))
    t = cell[-1][0] + cell[-1][1] + rng.choice((0.5, 1.0, 1.0, 1.5))
    st = list(cell)
    if t < ctx.beats - 1.0:
        sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t, beats=ctx.beats - t))
        d = rng.choice((-2, -1, 2, 3))
        ans = S.transform(Clip._raw([Note(s0, d0, p0 + d, 90) for s0, d0, p0 in cell], t), sub, displace=False)
        ns = sorted(ans)
        st += [(t + n.start, n.dur, n.pitch) for n in ns[:-1]]
        st.append((t + ns[-1].start, S.held(ctx.beats - t - ns[-1].start), ns[-1].pitch))
    return _play(ctx, _line_on(ctx, [x for x in st if x[0] < ctx.beats - 0.25]), _DEV['riff'], ornaments=_ORN,
                 embellish=0.3)


def m_sequence(ctx) -> Part:
    L = max(1.0, ctx.beats - ctx.rng.choice((0.75, 1.0, 1.5, 2.0)) - 0.25)
    g, L = _grid(ctx, ctx.density >= 0.75, L, cut=True)       # (a 16th burst cut short goes on in 8ths: _line_on)
    # a sequence: mostly the motif's cell sequenced / developed (soloist.MOTIVIC), else a target-first line
    st = (S.motif_line(ctx, length=L) if ctx.rng.random() < S.MOTIVIC else []) or S.target_line(ctx, grid_=g, length=L)
    st = [(t, min(d, max(0.25, L - t)), p) for t, d, p in st]
    end = st[-1][0] + st[-1][1]
    top = S.fold(S.snap(S.step(st[-1][2], S.scale(ctx), ctx.rng.choice((1, 1, -1))),
                        S.chord_tones(ctx, ctx.at + end)), ctx, near=st[-1][2])
    st.append((end, S.held(ctx.beats - end, 0.75), top))
    return _play(ctx, _line_on(ctx, st) if g < 0.5 else st, _DEV['sequence'])


def _varied_line(ctx) -> list:
    """Material for block chords / octaves: the climax a line arching up to its top note (target-first, from well
    below: the peak is reached by a line, not a leap or a run), a burst / block-chord chorus a running 8th-note line
    (locked hands: Garland, Shearing), else the current motif in the register, or (no motif) an answer line."""
    if ctx.stage == 'climax' and ctx.beats >= 3.0:
        n = max(3, int((ctx.beats - ctx.rng.choice((1.0, 1.5))) / 0.5))
        line = S.target_line(ctx, length=n * 0.5, grid_=0.5, start=S.center(ctx, -0.35), contour='arch')
        j = max(range(len(line)), key=lambda k: (line[k][2], -k))
        if j >= 4 and all(line[k][2] < line[k + 1][2] for k in range(j - 4, j)):
            # a straight climb into the top note is a sweep: the line turns once on its way up
            a, b = line[j - 2], line[j - 1]
            line[j - 2], line[j - 1] = (a[0], a[1], b[2]), (b[0], b[1], a[2])
        return line
    if ctx.stage in ('burst', 'chords') and ctx.beats >= 3.0:
        return S.answer_line(ctx, grid_=0.5, n=max(3, int((ctx.beats - ctx.rng.choice((1.0, 1.5, 2.0))) / 0.5)))
    c = S.motif_in_register(ctx)
    if len(c):
        return _line_on(ctx, [(n.start, n.dur, n.pitch) for n in c])
    return S.answer_line(ctx, grid_=0.5)


def m_block(ctx) -> Part:
    # block chords on every note only in a block-chord chorus; elsewhere a few accents (blind round 4: block-chord
    # peaks on every beat)
    return _play(ctx, _varied_line(ctx), _DEV['block'], ornaments={'restrike': 1.5, 'roll': 0.5}, embellish=0.3,
                 voices=3, density=1.0 if ctx.stage == 'chords' else 0.3)


def m_octaves(ctx) -> Part:
    return _play(ctx, _varied_line(ctx), _DEV['octaves'], ornaments={'restrike': 1.0}, embellish=0.2,
                 density=1.0 if ctx.stage == 'chords' else 0.4, doubles=0.78)


def m_blues(ctx) -> Part:
    st = _line_on(ctx, S.answer_line(ctx, grid_=0.5))
    return _play(ctx, st, _DEV['blues'], ornaments=_BLUES, embellish=0.7, quick=0.9)


def _peak(ctx, t: float):
    """A chord tone near the top of the arc at beat t (relative)."""
    return S.fold(S.snap(S.center(ctx, 0.12), S.chord_tones(ctx, ctx.at + t), 1), ctx)


def _set_piece(ctx, D: float = 2.0, land: float = 1.5):
    """Where a figure goes in its slot: (lead-in Part or None, figure start, figure length, landing length). The
    figure's length (D x 0.75..1.3) and its landing (land x 0.5..1.6) are drawn; a slot longer than both opens with
    a line (target-first in a dense stage, an answer else) and the figure comes late in it, its place drawn (on an
    8th; the line may run straight into it or breathe first) - a set piece crowns a phrase, it does not fill it, and
    it never sits in the same spot twice. The landing is held its drawn length (+ a beat at most), not to the slot's
    end: _crowned goes on with a line after it (blind round 8: a waltz's fourths cascade landing on a chord held 2.5
    bars, then a bar of silence - 4-9 silent bars per waltz chorus)."""
    rng = ctx.rng
    D = min(max(1.0, round(D * rng.uniform(0.75, 1.3) * 4) / 4), max(1.0, ctx.beats * 0.45))
    land = land * rng.uniform(0.5, 1.6)
    rest = ctx.beats - D - land - 0.25
    if rest < 2.0:
        return None, 0.0, D, S.held(ctx.beats - D, 0.75)
    t0 = max(1.5, float(int(rest * rng.uniform(0.6, 1.0) * 2) / 2.0))     # on an 8th
    sub = S.Ctx(**dict(ctx.__dict__, beats=t0 - rng.choice((0.0, 0.25, 0.5))))
    if ctx.density >= 0.7:
        st = S.target_line(sub, grid_=_grid(sub, True, sub.beats)[0], length=sub.beats)
        pre = _play(sub, st, _DEV['sequence'])
    else:
        pre = _play(sub, S.answer_line(sub, grid_=0.5), _DEV['answer'])
    return pre, t0, D, S.held(min(ctx.beats - t0 - D, land + 1.0), 0.75)


def _crowned(pre, t0, fig: Part, land: Part, ctx=None) -> Part:
    """The lead-in, the figure at t0 and its landing; with ctx, a slot left open after the landing (more than LINE_ON
    beats) goes on as an answering line (LINE_ON)."""
    out = fig.shifted(t0).merge(land.shifted(t0))
    out = pre.merge(out) if pre is not None else out
    if ctx is None or not len(out.clip):
        return out
    end = max(n.start + n.dur for n in out.clip)
    if ctx.beats - end < LINE_ON + 1.0 - 1e-6:
        return out
    last = max(out.clip, key=lambda n: (n.start, n.pitch))
    t1 = end + ctx.rng.choice((0.0, 0.5, 0.5, 1.0))
    sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t1, beats=ctx.beats - t1,
                       last=Note(ctx.at + last.start, last.dur, last.pitch, 80)))
    return out.merge(_play(sub, S.answer_line(sub, grid_=0.5), _DEV['answer']).shifted(t1))


def _last_pitch(part) -> int | None:
    """The top note of a Part's last attack (where a figure after it has to connect)."""
    if part is None or not len(part.clip):
        return None
    t = max(n.start for n in part.clip)
    return max(n.pitch for n in part.clip if n.start > t - 0.1)


def m_run(ctx) -> Part:
    """A scale run out of the line before it: up into a held, voiced peak - or, when the line already sits high, down
    into a chord tone below (its span, 5..14 semitones, drawn)."""
    from . import pianist
    pre, t0, D, hold = _set_piece(ctx)
    lo, hi = ctx.range
    last = _last_pitch(pre)
    tones = S.chord_tones(ctx, ctx.at + t0 + D)
    span = ctx.rng.randint(5, 14)
    if last is not None and last > (lo + hi) / 2 and ctx.rng.random() < 0.6:       # down from where the line is
        start = last + ctx.rng.choice((-2, -1, 1))
        top = max(lo, S.snap(start - span, tones, -1))
        end = top + 1
    else:
        top = _peak(ctx, t0 + D)
        start = last - ctx.rng.choice((1, 2, 3)) if last is not None and lo <= last < top - 4 else \
            max(lo, top - span)
        end = top - 1
    sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t0))
    tries = iter((0, 2, -2, 3))                      # (a run that repeats a recent lick starts elsewhere: fresh)

    def make():
        return pianist.run(max(lo, start + next(tries, 0)), end, D, ctx.bpm, chord=ctx.chord(ctx.at + t0),
                           key=S.key_of(ctx), vel=(S.vel(ctx, 0.35), S.vel(ctx, 0.8)), seed=ctx.rng.randrange(1 << 30))
    run = S.fresh(sub, make)
    return _crowned(pre, t0, _figure(ctx, run, 'run'), _land(sub, D, top, hold), ctx)


def m_fourths(ctx) -> Part:
    from . import pianist
    pre, t0, D, hold = _set_piece(ctx)
    sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t0))
    top = _peak(sub, 0.0)
    f = pianist.fourths(top, D, ctx.bpm, chord=ctx.chord(ctx.at + t0), key=S.key_of(ctx),
                        grid=0.5 if S.seconds(ctx, 0.25) < 0.11 else 0.25,
                        vel=(S.vel(ctx, 0.85), S.vel(ctx, 0.45)), seed=ctx.rng.randrange(1 << 30))
    # the cascade stops where it would leave the right hand's range (its landing never leaps back up an octave)
    floor = ctx.range[0] - 3
    cut = next((n.start for n in sorted(f) if n.pitch < floor), None)
    if cut is not None and cut > 0.4:
        f = Clip._raw([n for n in f if n.start < cut - 1e-6], f.length)
    low = min(n.pitch for n in f) if len(f) else top - 7
    land = S.fold(S.snap(low + 2, S.chord_tones(ctx, ctx.at + t0 + D), 1), ctx, near=low)
    return _crowned(pre, t0, _figure(ctx, f, 'fourths'), _land(sub, D, land, hold), ctx)


def m_octave_run(ctx) -> Part:
    from . import pianist
    pre, t0, D, hold = _set_piece(ctx)
    sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t0))
    top = _peak(sub, D)
    start = max(ctx.range[0] + 12, top - 9)
    run = pianist.octave_run(start, top - 1, D, ctx.bpm, chord=ctx.chord(ctx.at + t0), key=S.key_of(ctx),
                             vel=(S.vel(ctx, 0.5), S.vel(ctx, 0.9)), seed=ctx.rng.randrange(1 << 30))
    land = _land(sub, D, top, hold, devices={'octave': 3.0, 'locked': 1.0})
    return _crowned(pre, t0, _figure(ctx, run, 'octave_run'), land, ctx)


def _held(ctx):
    """(pickup steps, held start, held dur, top) - a pickup into a long chord tone near the top."""
    tones = S.chord_tones(ctx, ctx.at + 1.0)
    top = S.fold(S.snap(S.center(ctx, 0.1), tones, 1), ctx)
    pcs = S.pentatonic(ctx)
    pick = S.fit([S.step(top, pcs, -2), S.step(top, pcs, -1), top], ctx)
    return [(0.0, 0.5, pick[0]), (0.5, 0.5, pick[1])], 1.0, max(1.0, ctx.beats - 1.25), pick[2]


def _crown_held(ctx, inner) -> Part:
    """A held-peak figure (trill / tremolo) at the end of its slot: a line first when the slot is long."""
    pre, t0, _, _ = _set_piece(ctx, D=1.0, land=2.0)
    if pre is None:
        return inner(ctx)
    sub = S.Ctx(**dict(ctx.__dict__, at=ctx.at + t0, beats=ctx.beats - t0))
    return pre.merge(inner(sub).shifted(t0))


def m_tremolo(ctx) -> Part:
    return _crown_held(ctx, _tremolo)


def m_trill(ctx) -> Part:
    return _crown_held(ctx, _trill)


def _tremolo(ctx) -> Part:
    from . import pianist
    pick, t, d, top = _held(ctx)
    land = _land(ctx, t, top, d, devices={'drop2': 2.0, 'close': 1.0})
    under = sorted(n.pitch for n in land.clip if abs(n.start - t) < 0.2 and n.pitch < top)
    pre = _play(ctx, pick, _DEV['answer'])
    if not under or d * 60.0 / ctx.bpm < 0.8:
        return pre.merge(land)
    trem = pianist.tremolo(under, [top], d, ctx.bpm, vel=S.vel(ctx, 0.9), seed=ctx.rng.randrange(1 << 30), at=t)
    _mem(ctx).played(ctx.at + t, 'tremolo')
    return pre.merge(_figure(ctx, trem, 'tremolo', dry=False))


def _trill(ctx) -> Part:
    from . import pianist
    pick, t, d, top = _held(ctx)
    pre = _play(ctx, pick, _DEV['answer'])
    if d * 60.0 / ctx.bpm < 0.8:
        return pre.merge(_land(ctx, t, top, d))
    tr = pianist.trill(top, d, ctx.bpm, chord=ctx.chord(ctx.at + t), key=S.key_of(ctx), vel=S.vel(ctx, 0.9),
                       seed=ctx.rng.randrange(1 << 30), at=t)
    _mem(ctx).played(ctx.at + t, 'trill')
    # the voicing under the trill's principal note, struck with it (the trill sings on top)
    land = _land(ctx, t, top, d, devices={'guide': 2.0, 'drop2': 1.0})
    under = Clip._raw([n for n in land.clip if n.pitch < top], land.clip.length)
    return pre.merge(_figure(ctx, tr, 'trill')).merge(Part(under))


def m_resolve(ctx) -> Part:
    k = S.key_of(ctx)
    start = ctx.last.pitch if ctx.last is not None else S.center(ctx, 0.1)
    end_t = ctx.beats
    goal_tones = S.chord_tones(ctx, ctx.at + max(0.0, end_t - 1.0))
    target = S.fold(S.snap(S.center(ctx, -0.05), goal_tones | {k.tonic}), ctx)
    # the target held a bar at most: a longer slot comes down to it as a falling line first (the climax's descent;
    # blind round 6: a resolution of a few steps and a note held over two bars read as empty bars)
    hold = max(1.0, min(ctx.bpb - 1.0, 0.5 * ctx.beats))
    st, t0 = [], 0.0
    if ctx.beats - hold > 3.5:
        st = S.target_line(ctx, length=ctx.beats - hold - 2.0, grid_=0.5, start=start, contour='fall')
        t0, start = st[-1][0] + st[-1][1], st[-1][2]
    line, q = [], start
    while len(line) < 4 and abs(q - target) > 2:
        q = S.step(q, S.scale(ctx), -1 if q > target else 1)
        line.append(q)
    st += [(t0 + i * 0.5, 0.5, p) for i, p in enumerate(S.fit(line, ctx))]
    t = t0 + len(line) * 0.5
    k_ = 0
    while ctx.beats - t > hold + 0.25 and k_ < 6:          # (early: the target enclosed - above, below - until its bar)
        q = S.step(target, S.scale(ctx), 1 if k_ % 2 == 0 else -1)
        st.append((t, 0.5, q))
        t, k_ = t + 0.5, k_ + 1
    st.append((t, max(1.0, ctx.beats - t), target))
    return _play(ctx, st, _DEV['resolve'], ornaments={'roll': 2.0, 'restrike': 1.0, 'turn': 0.5}, embellish=0.5)


_FUNCS = {'motif': m_motif, 'answer': m_answer, 'riff': m_riff, 'sequence': m_sequence, 'block': m_block,
          'octaves': m_octaves, 'blues': m_blues, 'run': m_run, 'fourths': m_fourths, 'octave_run': m_octave_run,
          'tremolo': m_tremolo, 'trill': m_trill, 'resolve': m_resolve}


def _motif_maker(ctx) -> Clip:
    """A 2-bar motif when the solo gets none: a rising pentatonic pickup into a held note, an answer falling back."""
    pcs = S.pentatonic(ctx)
    a = S.fold(S.snap(S.center(ctx), pcs), ctx)
    b = S.step(a, pcs, 2)
    notes = [Note(0.0, 0.5, a, 88), Note(0.5, 0.5, S.step(a, pcs, 1), 92), Note(1.0, 1.5, b, 100),
             Note(3.0, 0.5, S.step(b, pcs, -1), 86), Note(3.5, 0.5, S.step(b, pcs, -2), 84), Note(4.0, 2.0, a, 92)]
    return Clip._raw(notes, 8.0)


# ------------------------------------------------------------------------------------------------ place

def _traded(lh: Clip, perf, cfg, win) -> tuple:
    """Trading 4s (soloist stage 'swap': perf.trades): in each traded span the left hand's comping gives way to a line
    of its own - target-first, single notes in its register, landing on a chord tone a beat before the right hand
    comes back - and the right hand comps under it: a soft rootless voicing early in every bar. (left hand, comp)."""
    import random as _random
    from .humanize import touch
    from .theory import note as _note, rootless
    lo, hi = _note(cfg['lh_register'][0]), _note(cfg['lh_register'][1]) + 5
    rng = _random.Random(f"{cfg['seed']}:trades")
    bpb = win.beats_per_bar
    ns, comp = list(lh), []
    for a, b in perf.trades:
        a0, b0 = a - perf.start, b - perf.start
        ns = [n._replace(dur=min(n.dur, max(0.1, a0 - 0.05 - n.start))) if n.start < a0 else n
              for n in ns if not a0 - 0.05 <= n.start < b0 - 0.05]
        ctx = S.Ctx(prog=win, at=a, solo_start=perf.start, beats=b - a - 1.0, key=cfg.get('_key'), bpm=cfg['_bpm'],
                    range=(lo, hi), register=0.55, density=0.45, rng=rng, last=None, stage='swap', energy=0.6,
                    vel=(cfg['lh_vel'] + 12, cfg['lh_vel'] + 32))      # (the traded line as present as the RH's)
        line = S.answer_line(ctx, grid_=0.5)
        c = touch(Clip._raw([Note(a0 + t, d, int(q), 80) for t, d, q in line], b0 - a0), *ctx.vel)
        ns += list(c)
        for k in range(int(round((b0 - a0) / bpb))):
            t = a0 + k * bpb + rng.choice((0.5, 1.0, 1.0, 1.5))      # off the bar line: under the line
            ch = win.at(min(t, win.length - 1e-6))
            if ch is None:
                continue
            v = int(cfg['lh_vel'] - 6 + rng.randint(-3, 3))
            comp += [Note(t + 0.015 * i, rng.choice((1.0, 1.5)), q, v)
                     for i, q in enumerate(sorted(rootless(ch, rng.choice('AB'), 4, register=(60, 74))))]
    return Clip._raw(sorted(ns), lh.length), Clip._raw(sorted(comp), lh.length)


def _place_fn(cfg):
    def place(track, perf) -> None:
        """The right hand on the track, the left hand (pianist.left_hand under the whole solo, answering the right
        hand's rests) on lh_track, the harmony pedal lifted for the dry figures."""
        from . import pianist
        track.play(perf.clip, perf.start)
        prog, solo_start = cfg.get('_prog'), cfg.get('_solo_start', perf.start)
        if prog is None:
            return
        L = perf.end - perf.start
        win = _window(S.Ctx(prog=prog, at=perf.start, solo_start=solo_start, key=cfg.get('_key')), L)
        if cfg['lh'] and cfg['lh_track'] is not None:
            lh = pianist.left_hand(win, cfg['_bpm'], style=cfg['lh'], register=cfg['lh_register'],
                                   density=cfg['lh_density'], vel=cfg['lh_vel'], rh=perf.clip, seed=cfg['seed'],
                                   length=L, answers=cfg['lh_answers'])
            if getattr(perf, 'trades', None):
                lh, comp = _traded(lh, perf, cfg, win)
                track.play(comp, perf.start)
            cfg['lh_track'].play(lh, perf.start)
            cfg['_lh'] = lh
        if cfg['pedal']:
            dry = [(a - perf.start, b - perf.start) for *_, p in perf.parts for a, b, k, _ in p.log if k == 'dry']
            track.automate('instrument.pedal', pianist.pedal(win, perf.start, dry=dry))
    return place


def vocabulary(style: str = 'straight', *, lh_track=None, lh: str | None = 'guide', lh_vel: float = 56,
               lh_register=('C3', 'C4'), lh_density: float = 0.5, lh_answers: float | None = None, pedal: bool = True,
               register=('A4', 'D6'), floor='C4', ceiling='C7', vel=(58, 112), doubles: float | None = 0.8,
               memory=None, moves=None, weights=None, phrase_bars: float = 2, budget=None, seed=0,
               sixteenths=None) -> Vocabulary:
    """The jazz pianist's soloist.Vocabulary: MOVES built from the soloist's material and played by the pianist's
    hands (pianist.arrange per phrase with the move's voicing devices - no fills: the soloist plans the space -; the
    named moves for the set pieces). style: STYLES ('straight', 'bar', 'lush', 'ballad': move weights, the budget,
    the roll; the right hand is arranged in the pianist style of the same name). register=(lo, hi): the solo's top
    line range (the arc moves inside it); floor: the right hand's lowest voice (C4 with a left hand). lh_track: the
    comping track for the left hand (pianist.left_hand: lh=LH_STYLES, lh_vel, lh_register, lh_density, lh_answers -
    it answers in the right hand's rests); lh=None or no lh_track: right hand only. pedal: the harmony pedal on the
    right hand's track, lifted for runs / 4ths / trills. vel=(lo, hi) of the whole solo; doubles: the notes under the
    melody's top note x this velocity (the line leads). memory: a pianist.Memory shared with the song's arrange()
    calls (the ornament budget song-wide; default one per solo). weights= / moves= as the guitar's; budget= the
    soloist budget in bars (default the style's: fast every 16, spice every 2). seed: the left hand's dice.
    sixteenths: {'every': bars, 'bars': bars} - 16th lines at most one per `every` bars and `bars` long (the feel's
    density: a bossa rarely, a ballad's double time more often; None: whenever a dense stage wants them)."""
    from . import pianist
    from .theory import note as _note
    if style not in STYLES:
        raise ComposeError(f"piano vocabulary style must be one of {', '.join(STYLES)}, got {style!r}")
    if lh is not None and lh not in pianist.LH_STYLES:
        raise ComposeError(f"piano vocabulary lh must be one of {', '.join(pianist.LH_STYLES)} or None, got {lh!r}")
    if memory is not None and not isinstance(memory, pianist.Memory):
        raise ComposeError(f"piano vocabulary memory must be a pianist.Memory(), got {memory!r}")
    ST = STYLES[style]
    if sixteenths is not None and (set(sixteenths) != {'every', 'bars'} or
                                   not all(isinstance(v, (int, float)) and v > 0 for v in sixteenths.values())):
        raise ComposeError(f"piano vocabulary sixteenths must be {{'every': bars > 0, 'bars': bars > 0}}, got "
                           f"{sixteenths!r}")
    lo, hi = _note(register[0]), _note(register[1])
    if not 48 <= lo < hi - 12 <= 96:
        raise ComposeError(f"piano vocabulary register must span 12+ semitones within C3..C8, got {register!r}")
    cfg = {'arrange_style': style if style in pianist.STYLES else 'straight', 'roll': ST['roll'],
           'floor': _note(floor), 'ceiling': ceiling, 'doubles': doubles, 'memory': memory, 'lh_track': lh_track,
           'lh': lh, 'lh_vel': lh_vel, 'lh_register': lh_register, 'lh_density': lh_density, 'lh_answers': lh_answers,
           'pedal': bool(pedal), 'seed': seed, 'sixteenths': dict(sixteenths) if sixteenths else None}
    w = dict(ST['weights'])
    w.update(weights or {})
    names = list(MOVES) if moves is None else list(moves)
    mv = []
    for n in names:
        if n not in MOVES:
            raise ComposeError(f"unknown piano solo move {n!r}; moves: {', '.join(MOVES)}")
        if w.get(n, 1.0) <= 0:
            continue
        roles, e, d, spice, fast = MOVES[n]
        mv.append(Move(n, 0.0, e, d, spice, _wrap(_FUNCS[n], cfg), fast=fast, roles=roles, weight=w.get(n, 1.0)))
    return Vocabulary(mv, motif=_wrap(_motif_maker, cfg), name=f'piano:{style}', place=_place_fn(cfg), vel=vel,
                      phrase_bars=phrase_bars, budget=budget if budget is not None else dict(ST['budget']),
                      range=(lo, hi))


def _wrap(fn, cfg):
    def play(ctx):
        ctx.memory.setdefault('_piano', cfg)
        cfg.update(_prog=ctx.prog, _solo_start=ctx.solo_start, _bpm=ctx.bpm, _key=ctx.key)
        return fn(ctx)
    play.__name__ = getattr(fn, '__name__', 'move')
    return play
