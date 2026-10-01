"""The lead guitar's solo vocabulary for agentsound.soloist: phrases a guitar hero plays, each a soloist.Move built
from agentsound.fretwork techniques and guitarist.lead's phrasing (gestures=True). Use guitarist.vocabulary(...)
(= vocabulary() here):

    from agentsound import soloist, guitarist as gtr
    perf = soloist.solo(s, lead, gtr.vocabulary(style='rock'), at=solo, prog=PROG, motif=HOOK, seed=7)

Moves (MOVES: name -> (roles, energy, density, spice, fast); a style re-weights them - STYLES):
  motif       the motif (the song's hook) played as a guitarist would: slurs, slides, a bend into its peak, vibrato
  answer      a falling pentatonic answer landing on a chord tone with vibrato
  bend_cry    a pickup into a long singing bend (half / whole / 1.5 steps by energy), vibrato below the bent pitch
  prebend     a silent pre-bend released onto a chord tone, then a step down
  ghost       a ghost bend (soft pick, the release heard) - Gilmour's sigh
  slides      notes reached by slides (in, between) with a hammer-on, a vibrato at the end
  sequence    a 3- / 4-note pentatonic cell sequenced up, picked with accents, into a held note
  legato      a hammer / pull flurry (only the string changes picked) up to a held note
  chug        palm-muted low chugs, then a slide up into a high held note
  wah         an answer through a talking wah
  pinch       a low pickup into a pinch-harmonic squeal with a wide vibrato
  double_stop an oblique bend (one string bent under a held one)
  shred       cascading pentatonic sextuplets, alternate-picked, into a bend          (fast)
  sweep       sweep-picked arpeggios of the chords, into a held note                  (fast)
  tremolo     tremolo-picked chord tones climbing, crescendo                          (fast)
  trill       a hammer / pull trill on a high note, into a bend                       (fast)
  scream      the climax: a run to the top of the neck into a unison / 1.5-step bend held with a wide vibrato
  feedback    a long held note blooming into controlled feedback (the string's octave / twelfth)
  dive        a held high note with vibrato, then a whammy dive
  resolve     down to the tonic: a long last note, slow wide vibrato (the last phrase slides off / echo throw)
"""

from __future__ import annotations

from . import fretwork as fw
from . import gesture as G
from .patterns import Clip, Note, _vel, as_clip
from . import soloist as S
from .soloist import Move, Part, Vocabulary
from .theory import ComposeError

__all__ = ['vocabulary', 'MOVES', 'STYLES']

_EPS = 1e-6

MOVES = {
    'motif': (('motif',), 0.4, 0.4, False, False),
    'answer': (('answer', 'resolve', 'develop'), 0.5, 0.55, False, False),
    'bend_cry': (('answer', 'develop', 'climax'), 0.68, 0.25, False, False),
    'prebend': (('answer', 'resolve'), 0.45, 0.2, True, False),
    'ghost': (('answer', 'resolve'), 0.35, 0.15, True, False),
    'slides': (('answer', 'develop'), 0.5, 0.35, False, False),
    'sequence': (('develop', 'burst'), 0.7, 0.78, False, False),
    'legato': (('develop', 'burst'), 0.76, 0.85, True, False),
    'chug': (('develop', 'answer'), 0.66, 0.7, True, False),
    'wah': (('develop', 'answer'), 0.6, 0.55, True, False),
    'pinch': (('answer', 'develop', 'climax'), 0.8, 0.3, True, False),
    'double_stop': (('answer', 'climax'), 0.72, 0.3, True, False),
    'shred': (('burst',), 0.93, 0.95, True, True),
    'sweep': (('burst',), 0.88, 0.95, True, True),
    'tremolo': (('burst', 'climax'), 0.9, 0.9, True, True),
    'trill': (('burst', 'climax'), 0.82, 0.85, True, True),
    'scream': (('climax',), 1.0, 0.35, True, False),
    'feedback': (('climax', 'resolve'), 0.85, 0.1, True, False),
    'dive': (('climax', 'burst'), 0.9, 0.25, True, False),
    'resolve': (('resolve',), 0.35, 0.3, False, False),
}
"""name -> (roles, energy, density, spice, fast)."""

STYLES = {
    'rock': dict(lead='rock', vib='rock', weights={}, budget=dict(spice_every=1.5, fast_every=8, same_every=16)),
    'blues': dict(lead='blues', vib='blues',
                  weights={'sweep': 0.0, 'legato': 0.4, 'shred': 0.8, 'bend_cry': 1.6, 'prebend': 1.4, 'ghost': 1.2,
                           'double_stop': 1.4, 'wah': 0.6, 'tremolo': 0.6},
                  budget=dict(spice_every=1.25, fast_every=12, same_every=16)),
    'ballad': dict(lead='ballad', vib='wide',
                   weights={'sweep': 0.0, 'shred': 0.6, 'legato': 0.6, 'chug': 0.3, 'wah': 0.3, 'ghost': 1.6,
                            'feedback': 1.5, 'bend_cry': 1.5, 'slides': 1.3},
                   budget=dict(spice_every=2.0, fast_every=16, same_every=24)),
    'fusion': dict(lead='pop', vib='narrow',
                   weights={'legato': 1.8, 'sweep': 1.4, 'slides': 1.4, 'chug': 0.4, 'pinch': 0.5, 'ghost': 0.5,
                            'feedback': 0.5},
                   budget=dict(spice_every=1.0, fast_every=6, same_every=12)),
}
"""Vocabulary styles: the guitarist.lead style used for phrasing, the fretwork vibrato, move weights (0 = never) and
the default soloist budget (bars)."""


# ------------------------------------------------------------------------------------------------ pitch material
# (shared with every vocabulary: agentsound.soloist's material helpers)

_key, _penta, _tones, _snap, _step = S.key_of, S.pentatonic, S.chord_tones, S.snap, S.step
_center, _clamp, _fit, _cv, _secs, _grid = S.center, S.fold, S.fit, S.vel, S.seconds, S.grid
_merge, _book = S.merge, S.trick


def _chord(ctx, t=None):
    return ctx.chord(t)


def _range(ctx):
    return ctx.range


def _bpm(ctx) -> float:
    return float(ctx.bpm)


def _picked(ctx, steps, *, vel_lo=0.55, vel_hi=0.85, gap_ms=14.0) -> list:
    """Picked notes for [(start, dur, pitch)] (each re-picked: a small gap before the next) with an upward arc."""
    gap = gap_ms / 1000.0 * _bpm(ctx) / 60.0
    out = []
    for i, (s, d, p) in enumerate(steps):
        nxt = steps[i + 1][0] if i + 1 < len(steps) else s + d
        e = min(s + d, nxt - gap) if i + 1 < len(steps) else s + d
        x = vel_lo + (vel_hi - vel_lo) * (i / max(1, len(steps) - 1))
        out.append(Note(max(0.0, s), max(0.03, e - s), int(p), _vel(_cv(ctx, x) * ctx.rng.uniform(0.95, 1.05))))
    return out


def _perform(ctx, clip, *, climax: bool = False, density=None, lead_style=None) -> Part:
    """A written line played by guitarist.lead(gestures=True): fingered, picked and slurred, bends into long peaks,
    vibrato on long notes - its budgets counted over the whole solo (a shared guitarist.Memory)."""
    from . import guitarist as gtr
    c = as_clip(clip)
    if not len(c):
        return Part()
    mem = ctx.memory.setdefault('_gtr_mem', gtr.Memory())
    sty = ctx.memory.get('_gtr_style', STYLES['rock'])
    lo, hi = ctx.vel
    arr = gtr.lead(c, None, bpm=_bpm(ctx), key=_key(ctx), style=lead_style or sty['lead'], energy=ctx.energy,
                   density=ctx.density if density is None else density, seed=ctx.rng.randrange(1 << 30),
                   touch=(lo, hi), mono=True, articulations={}, climax=climax, memory=mem, at=ctx.at,
                   gestures=True, vib_style=sty['vib'])
    return Part(arr.clip, arr.gestures, arr.moves)


def _end_note(ctx, at: float, pitch: int, vel_x: float = 0.85, *, vib=True, scale=1.0, back=None) -> Part:
    """A held note from `at` to the end of the slot with a finger vibrato."""
    D = max(0.25, ctx.beats - at)
    sty = ctx.memory.get('_gtr_style', STYLES['rock'])
    n = Note(at, D, int(pitch), _vel(_cv(ctx, vel_x)))
    gs = []
    if vib and _secs(ctx, D) > 0.45:
        gs.append(fw._vib(at, D, _bpm(ctx), sty['vib'], seed=ctx.rng.randrange(1 << 30), scale=scale))
    return Part(Clip._raw([n], at + D), gs, [(at, at + D, 'vibrato', 'held')])


def _bend_to(ctx, at: float, target: int, dur: float, *, amount=None, vel_x=0.92, release=None) -> Part:
    pcs = set(_key(ctx).pcs)
    if amount is None:
        amount = 2 if (target - 2) % 12 in pcs else 1
        if ctx.energy >= 0.9 and (target - 3) % 12 in pcs and ctx.rng.random() < 0.4:
            amount = 3
    sty = ctx.memory.get('_gtr_style', STYLES['rock'])
    p = fw.bend(target, max(0.25, dur), _bpm(ctx), amount=amount, vib=sty['vib'], vel=_cv(ctx, vel_x),
                release=release, seed=ctx.rng.randrange(1 << 30))
    return p.shifted(at)


# ------------------------------------------------------------------------------------------------ the moves

def m_motif(ctx) -> Part:
    c = S.motif_in_register(ctx)
    return _perform(ctx, c) if len(c) else Part()


def m_answer(ctx) -> Part:
    steps = S.answer_line(ctx)
    return _perform(ctx, Clip._raw([Note(t, d, p, 90) for t, d, p in steps], ctx.beats))


def m_bend_cry(ctx) -> Part:
    tones = _tones(ctx, ctx.at + 1.0)
    target = _clamp(_snap(_center(ctx, 0.1), tones, 1), ctx)
    pcs = _penta(ctx)
    k = 2 + (ctx.rng.random() < 0.5)
    g = 0.5 if ctx.energy < 0.7 else 0.25
    pick = [_step(target, pcs, -(k - i) - 1) for i in range(k)]
    steps = [(i * g, g, p) for i, p in enumerate(pick)]
    head = Part(Clip._raw(_picked(ctx, steps, vel_lo=0.5, vel_hi=0.7), k * g), [], [(0, k * g, 'picking', 'pickup')])
    rel = 0.75 if ctx.rng.random() < 0.25 else None
    return _merge(head, _bend_to(ctx, k * g, target, ctx.beats - k * g - 0.15, release=rel))


def m_prebend(ctx) -> Part:
    tones = _tones(ctx, ctx.at + 0.5)
    land = _clamp(_snap(_center(ctx, 0.05), tones, -1), ctx)
    pcs = set(_key(ctx).pcs)
    top = _step(land, pcs, 1)
    D = min(ctx.beats * 0.55, 2.5)
    p1 = fw.prebend(top, D, _bpm(ctx), amount=top - land, release=0.45, vel=_cv(ctx, 0.8),
                    seed=ctx.rng.randrange(1 << 30))
    rest = ctx.beats - D
    if rest >= 1.0:
        down = _snap(_step(land, _penta(ctx), -1), _tones(ctx, ctx.at + D + 0.5), -1)
        return _merge(p1, _end_note(ctx, D + 0.05, down, 0.6, scale=0.8))
    return p1


def m_ghost(ctx) -> Part:
    tones = _tones(ctx, ctx.at)
    land = _clamp(_snap(_center(ctx), tones, 1), ctx)
    D = min(ctx.beats - 0.25, 3.0)
    return fw.ghost_bend(land + 2, D, _bpm(ctx), amount=2, vel=_cv(ctx, 0.85), seed=ctx.rng.randrange(1 << 30))


def m_slides(ctx) -> Part:
    pcs = _penta(ctx)
    tones = _tones(ctx, ctx.at)
    a = _clamp(_snap(_center(ctx, -0.05), tones), ctx)
    b_ = _step(a, pcs, 2)
    bpm = _bpm(ctx)
    d1 = min(1.5, ctx.beats * 0.35)
    p1 = fw.slide_in(a, d1, bpm, frm=-ctx.rng.choice((2, 3, 4)), vel=_cv(ctx, 0.7))
    d2 = min(1.5, ctx.beats * 0.3)
    p2 = fw.slide(a, b_, d1 + d2, bpm, split=d1 / (d1 + d2), vel=_cv(ctx, 0.75), squeak=ctx.rng.random() < 0.5)
    p2.clip = Clip._raw([n for n in p2.clip if n.start > 0.01], p2.clip.length)
    c = _step(b_, pcs, 1)
    h = fw.hammer_on(b_, c, 1.0, bpm, vel=_cv(ctx, 0.75)).shifted(d1 + d2 + 0.1)
    end = _end_note(ctx, d1 + d2 + 1.2, _snap(c, tones), 0.8)
    if d1 + d2 + 1.4 > ctx.beats:
        return _merge(p1, p2)
    return _merge(p1, p2, h, end)


def m_sequence(ctx) -> Part:
    pcs = _penta(ctx)
    g = _grid(ctx, 10.0, (0.25, 1 / 3, 0.5)) if ctx.density > 0.6 else 0.5
    steps = S.sequence_line(ctx, grid_=g)
    cell = 4 if g == 0.25 else 3
    t = steps[-1][0] + g
    notes = _picked(ctx, steps, vel_lo=0.55, vel_hi=0.9)
    acc = [n._replace(vel=_vel(n.vel * (1.1 if i % cell == 0 else 0.95))) for i, n in enumerate(notes)]
    head = Part(Clip._raw(acc, t), [fw.accents(acc, _bpm(ctx))], [(0, t, 'picking', 'sequence')])
    top = _clamp(_step(steps[-1][2], pcs, 1), ctx)
    if ctx.beats - t >= 1.0:
        tail = _bend_to(ctx, t, _snap(top, _tones(ctx, ctx.at + t)), ctx.beats - t - 0.1) if ctx.energy > 0.65 \
            else _end_note(ctx, t, _snap(top, _tones(ctx, ctx.at + t)), 0.9)
        return _merge(head, tail)
    return head


def m_legato(ctx) -> Part:
    pcs = set(_key(ctx).pcs) if ctx.rng.random() < 0.5 else _penta(ctx)
    secs = _secs(ctx, ctx.beats)
    n = max(6, min(24, int(min(secs * 0.65, 2.2) * 11)))
    span = n / 11.0 * _bpm(ctx) / 60.0
    up = ctx.rng.random() < 0.7
    line = _fit(S.run_line(ctx, n, up=up, pcs=pcs), ctx)
    up = line[-1] >= line[-2]
    run = fw.legato_run(line, span, _bpm(ctx), vel=(_cv(ctx, 0.6), _cv(ctx, 0.85)),
                        seed=ctx.rng.randrange(1 << 30))
    land = _snap(_step(line[-1], pcs, 1 if up else -1), _tones(ctx, ctx.at + span))
    if ctx.beats - span >= 0.75:
        return _merge(run, _end_note(ctx, span, _clamp(land, ctx), 0.95))
    return run


def m_chug(ctx) -> Part:
    k = _key(ctx)
    c = _chord(ctx)
    root = c.root if c is not None else k.tonic
    low = 52 + (root - 52) % 12
    if low > 59:
        low -= 12
    low = max(low, 45)
    bpm = _bpm(ctx)
    D = min(2.0, ctx.beats * 0.4)
    pm = fw.palm_mute([low, low, low + 7, low], D, bpm, grid=0.25 if 1.0 / _secs(ctx, 0.25) < 12 else 0.5,
                      vel=(_cv(ctx, 0.6), _cv(ctx, 0.9)), seed=ctx.rng.randrange(1 << 30))
    top = _clamp(_snap(_center(ctx, 0.15), _tones(ctx, ctx.at + D)), ctx)
    rest = ctx.beats - D - 0.1
    if rest < 1.0:
        return pm
    sl = fw.slide_in(top, rest, bpm, frm=-ctx.rng.choice((3, 5, 7)), vel=_cv(ctx, 1.0)).shifted(D + 0.1)
    sty = ctx.memory.get('_gtr_style', STYLES['rock'])
    sl.gestures.append(fw._vib(D + 0.1, rest, bpm, sty['vib'], delay=0.35, seed=ctx.rng.randrange(1 << 30)))
    return _merge(pm, sl)


def m_wah(ctx) -> Part:
    p = m_answer(ctx)
    if not len(p.clip):
        return p
    w = fw.wah_talk(p.clip, _bpm(ctx))
    return _merge(p, w)


def m_pinch(ctx) -> Part:
    pcs = _penta(ctx)
    tones = _tones(ctx, ctx.at + 1.0)
    target = _clamp(_snap(_center(ctx, -0.35), tones), ctx)
    k = 2 + (ctx.rng.random() < 0.5)
    pick = [_step(target, pcs, -(k - i)) for i in range(k)]
    g = 0.25 if ctx.energy > 0.6 else 0.5
    head = Part(Clip._raw(_picked(ctx, [(i * g, g, p) for i, p in enumerate(pick)], vel_lo=0.6, vel_hi=0.8), k * g),
                [], [(0, k * g, 'picking', 'pickup')])
    D = max(0.75, ctx.beats - k * g - 0.15)
    pin = fw.pinch(target, D, _bpm(ctx), vel=_cv(ctx, 1.0), seed=ctx.rng.randrange(1 << 30)).shifted(k * g)
    return _merge(head, pin)


def m_double_stop(ctx) -> Part:
    tones = _tones(ctx, ctx.at)
    top = _clamp(_snap(_center(ctx, 0.1), tones, 1), ctx)
    D = min(ctx.beats - 0.25, 3.0)
    p = fw.oblique_bend(top, D, _bpm(ctx), interval=ctx.rng.choice((3, 4, 5)), vel=_cv(ctx, 0.9),
                        seed=ctx.rng.randrange(1 << 30))
    return p


def m_shred(ctx) -> Part:
    pcs = _penta(ctx)
    g = _grid(ctx, 12.5, (1 / 6, 0.25, 1 / 3))
    group = 6 if abs(g - 1 / 6) < 1e-6 else (4 if g == 0.25 else 3)
    burst = min(ctx.beats - 1.0, 4.0)
    n_groups = max(1, int(burst / (group * g)))
    top = _clamp(_snap(_center(ctx, 0.2), pcs), ctx)
    steps, t = [], 0.0
    for gi in range(n_groups):
        base = _step(top, pcs, -gi) if gi else top
        offs = [0, -1, -2, -1, -2, -3][:group]
        for o in offs:
            steps.append(_step(base, pcs, o) if o else base)
            t += g
    steps = _fit(steps, ctx)
    run = fw.picked_run(steps, t, _bpm(ctx), group=group, vel=(_cv(ctx, 0.65), _cv(ctx, 0.95)),
                        seed=ctx.rng.randrange(1 << 30))
    if ctx.beats - t >= 0.75:
        land = _snap(_step(steps[-1], pcs, -1), _tones(ctx, ctx.at + t))
        if ctx.rng.random() < 0.5:
            return _merge(run, _bend_to(ctx, t, _clamp(land + 12 if land < 62 else land, ctx), ctx.beats - t - 0.1))
        return _merge(run, _end_note(ctx, t, _clamp(land, ctx), 1.0))
    return run


def m_sweep(ctx) -> Part:
    bpm = _bpm(ctx)
    t, parts = 0.0, []
    per = 1 / 6 if 1.0 / _secs(ctx, 1 / 6) <= 13 else 0.25
    total = min(ctx.beats - 1.0, 4.0)
    while t + 9 * per <= total + _EPS:
        c = _chord(ctx, ctx.at + t)
        k = _key(ctx)
        root = c.root if c is not None else k.tonic
        third = (c.intervals[1] if c is not None and len(c.intervals) > 1 else (3 if k.minorish else 4))
        r = 57 + (root - 57) % 12
        tones = [r, r + 7, r + 12, r + 12 + third, r + 19]
        if ctx.energy > 0.85:
            tones.append(r + 24)
        tones = [_clamp(x, ctx) for x in tones]
        tones = sorted(set(tones))
        L = per * (2 * len(tones) - 1)
        parts.append(fw.sweep(tones, L, bpm, vel=(_cv(ctx, 0.6), _cv(ctx, 0.95)),
                              seed=ctx.rng.randrange(1 << 30)).shifted(t))
        t += L + per
    if not parts:
        return m_shred(ctx)
    land = _clamp(_snap(_center(ctx, 0.2), _tones(ctx, ctx.at + t)), ctx)
    if ctx.beats - t >= 0.75:
        parts.append(_end_note(ctx, t, land, 1.0))
    return _merge(*parts)


def m_tremolo(ctx) -> Part:
    tones = _tones(ctx, ctx.at)
    bpm = _bpm(ctx)
    p = _clamp(_snap(_center(ctx, 0.0), tones), ctx)
    n = 3 if ctx.beats >= 6 else 2
    seg = min(2.0, (ctx.beats - 1.0) / n)
    parts = []
    for i in range(n):
        lo, hi = ctx.vel
        parts.append(fw.tremolo_pick(p, seg, bpm, rate=13.0, vel=(lo + (hi - lo) * (0.3 + 0.2 * i), lo + (hi - lo) *
                                                                  (0.55 + 0.2 * i)),
                                     seed=ctx.rng.randrange(1 << 30)).shifted(i * seg))
        p = _clamp(_step(p, _tones(ctx, ctx.at + (i + 1) * seg) | _penta(ctx), 2), ctx)
    rest = ctx.beats - n * seg
    if rest >= 0.75:
        parts.append(_bend_to(ctx, n * seg, p, rest - 0.1))
    if ctx.memory.get('_scraped') is None and ctx.at - ctx.phrase_start < 0.5 and _book(ctx, 'pick_scrape', -1.0):
        ctx.memory['_scraped'] = ctx.at
        parts.append(fw.pick_scrape(1.0, bpm, vel=_cv(ctx, 0.8)).shifted(-1.0))
    return _merge(*parts)


def m_trill(ctx) -> Part:
    tones = _tones(ctx, ctx.at)
    p = _clamp(_snap(_center(ctx, 0.15), tones), ctx)
    up = 2 if (p + 2) % 12 in set(_key(ctx).pcs) else 1
    D = min(2.0, ctx.beats * 0.45)
    tr = fw.trill(p, D, _bpm(ctx), upper=up, vel=_cv(ctx, 0.9), seed=ctx.rng.randrange(1 << 30))
    rest = ctx.beats - D
    if rest >= 0.75:
        tgt = _clamp(_snap(p + 3, tones, 1), ctx)
        return _merge(tr, _bend_to(ctx, D + 0.05, tgt, rest - 0.15))
    return tr


def m_scream(ctx) -> Part:
    pcs = _penta(ctx)
    tones = _tones(ctx, ctx.at + 1.5)
    lo, hi = _range(ctx)
    target = _snap(min(hi - 2, _center(ctx, 0.05)), tones, -1)
    k = 4 if ctx.energy > 0.8 else 3
    g = _grid(ctx, 10.0, (0.25, 1 / 3, 0.5))
    run = _fit([_step(target, pcs, -(k - i)) for i in range(k)], ctx)
    head = Part(Clip._raw(_picked(ctx, [(i * g, g, p) for i, p in enumerate(run)], vel_lo=0.7, vel_hi=0.9), k * g),
                [], [(0, k * g, 'picking', 'run up')])
    D = max(1.0, ctx.beats - k * g - 0.1)
    bpm = _bpm(ctx)
    sty = ctx.memory.get('_gtr_style', STYLES['rock'])
    if ctx.rng.random() < 0.55:
        main = fw.unison_bend(target, D, bpm, amount=2, vib=sty['vib'], vel=_cv(ctx, 1.0), mono=True,
                              seed=ctx.rng.randrange(1 << 30))
    else:
        amt = 3 if (target - 3) % 12 in set(_key(ctx).pcs) else 2
        main = fw.bend(target, D, bpm, amount=amt, vib='wide' if sty['vib'] in ('rock', 'wide') else sty['vib'],
                       vel=_cv(ctx, 1.0), seed=ctx.rng.randrange(1 << 30))
    main = main.shifted(k * g)
    throw = G.Gesture('throw', 'tone', k * g + D * 0.6, k * g + D + 2.0,
                      [G._Shape('echo', [(k * g + D * 0.6, 0.0), (k * g + D, 0.22), (k * g + D + 2.0, 0.0)])])
    main.gestures.append(throw)
    return _merge(head, main)


def m_feedback(ctx) -> Part:
    tones = _tones(ctx, ctx.at)
    p = _clamp(_snap(_center(ctx, -0.1), tones), ctx)
    bpm = _bpm(ctx)
    D = ctx.beats - 0.1
    if _secs(ctx, D) < 2.2:
        return m_bend_cry(ctx)
    sty = ctx.memory.get('_gtr_style', STYLES['rock'])
    return fw.feedback(p, D, bpm, partial=2 if ctx.rng.random() < 0.6 else 3, start=0.25, bloom_s=1.3,
                       vib=sty['vib'], vel=_cv(ctx, 0.95), seed=ctx.rng.randrange(1 << 30))


def m_dive(ctx) -> Part:
    tones = _tones(ctx, ctx.at)
    p = _clamp(_snap(_center(ctx, 0.1), tones), ctx)
    D = ctx.beats - 0.2
    bpm = _bpm(ctx)
    sty = ctx.memory.get('_gtr_style', STYLES['rock'])
    held = 0.45
    pt = fw.whammy_dive(p, D, bpm, semis=-12 if ctx.energy > 0.85 else -7, start=held, dive=0.45, vel=_cv(ctx, 1.0))
    pt.gestures.append(fw._vib(0.0, D * held, bpm, sty['vib'], delay=0.2, seed=ctx.rng.randrange(1 << 30)))
    return pt


def m_resolve(ctx) -> Part:
    k = _key(ctx)
    pcs = set(k.pcs)
    final = ctx.next_at is None
    start = ctx.last.pitch if ctx.last is not None else _center(ctx, 0.1)
    tonic = _clamp(_snap(_center(ctx, -0.05), {k.tonic}), ctx)
    if final:
        tonic = _clamp(_snap(_center(ctx, -0.1), {k.tonic}), ctx)
    line, q = [], start
    while len(line) < 4 and abs(q - tonic) > 2:
        q = _step(q, pcs, -1 if q > tonic else 1)
        line.append(q)
    g = 0.5
    steps = [(i * g, g, p) for i, p in enumerate(line)]
    t = len(line) * g
    head = Part(Clip._raw(_picked(ctx, steps, vel_lo=0.55, vel_hi=0.45), t), [], [(0, t, 'picking', 'step down')]) \
        if steps else Part()
    D = max(1.0, ctx.beats - t)
    bpm = _bpm(ctx)
    end = _end_note(ctx, t, tonic, 0.7, scale=1.1)
    if final:
        end.gestures.append(G.taper(t, D, bpm, db=-6.0, frac=0.5))
        end.gestures.append(G.Gesture('throw', 'tone', t + D * 0.5, t + D + 3.0,
                                      [G._Shape('echo', [(t + D * 0.5, 0.0), (t + D, 0.25), (t + D + 3.0, 0.0)])]))
    return _merge(head, end)


_FUNCS = {'motif': m_motif, 'answer': m_answer, 'bend_cry': m_bend_cry, 'prebend': m_prebend, 'ghost': m_ghost,
          'slides': m_slides, 'sequence': m_sequence, 'legato': m_legato, 'chug': m_chug, 'wah': m_wah,
          'pinch': m_pinch, 'double_stop': m_double_stop, 'shred': m_shred, 'sweep': m_sweep, 'tremolo': m_tremolo,
          'trill': m_trill, 'scream': m_scream, 'feedback': m_feedback, 'dive': m_dive, 'resolve': m_resolve}


# ------------------------------------------------------------------------------------------------ the vocabulary

def _motif_maker(ctx) -> Clip:
    """A 2-bar pentatonic motif (when the solo gets none): a rising pickup to a held note, an answer falling back."""
    pcs = _penta(ctx)
    a = _clamp(_snap(_center(ctx), pcs), ctx)
    b_ = _step(a, pcs, 2)
    c = _step(b_, pcs, -1)
    notes = [Note(0.0, 0.5, a, 88), Note(0.5, 0.5, _step(a, pcs, 1), 92), Note(1.0, 1.5, b_, 100),
             Note(3.0, 0.5, c, 86), Note(3.5, 0.5, _step(c, pcs, -1), 84), Note(4.0, 2.0, a, 92)]
    return Clip._raw(notes, 8.0)


def _place(track, perf) -> None:
    fw.render(track, [p for *_, p in perf.parts])


def vocabulary(style: str = 'rock', *, register=('G3', 'D6'), vel=(62, 122), moves=None, weights=None,
               phrase_bars: float = 2, budget=None) -> Vocabulary:
    """The lead guitar's soloist.Vocabulary: MOVES (the phrases above, built from agentsound.fretwork) weighted by
    style (STYLES: rock, blues, ballad, fusion; weights= overrides, 0 drops a move; moves= a subset by name),
    register=(lo, hi) of the arc (default G3-D6: the hero guitars' singing range), vel=(lo, hi) of the whole solo,
    phrase_bars, budget= the soloist budget in bars (default the style's). place() writes the solo through
    fretwork.render (notes on the hero guitar with its zone lock and glides, every lane once, the twin / noise aux
    tracks made when needed)."""
    from .theory import note as _note
    if style not in STYLES:
        raise ComposeError(f"guitar vocabulary style must be one of {', '.join(STYLES)}, got {style!r}")
    ST = STYLES[style]
    w = dict(ST['weights'])
    w.update(weights or {})
    names = list(MOVES) if moves is None else list(moves)
    for n in names:
        if n not in MOVES:
            raise ComposeError(f"unknown guitar solo move {n!r}; moves: {', '.join(MOVES)}")
    lo, hi = _note(register[0]), _note(register[1])
    if not 40 <= lo < hi - 12 <= 88:
        raise ComposeError(f"guitar vocabulary register must span 12+ semitones within E2..E7, got {register!r}")
    mv = []
    for n in names:
        weight = w.get(n, 1.0)
        if weight <= 0:
            continue
        roles, e, d, spice, fast = MOVES[n]
        mv.append(Move(n, 0.0, e, d, spice, _wrap(_FUNCS[n], ST), fast=fast, roles=roles, weight=weight))
    return Vocabulary(mv, motif=_wrap(_motif_maker, ST), name=f'guitar:{style}', place=_place, vel=vel,
                      phrase_bars=phrase_bars, budget=budget if budget is not None else dict(ST['budget']),
                      range=(lo, hi))


def _wrap(fn, style):
    def play(ctx):
        ctx.memory.setdefault('_gtr_style', style)
        return fn(ctx)
    play.__name__ = getattr(fn, '__name__', 'move')
    return play

