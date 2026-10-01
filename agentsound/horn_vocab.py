"""The wind player's solo vocabulary for agentsound.soloist (sax, trumpet, trombone, flute, clarinet; bowed strings):
phrases built from the soloist's shared material lines and played by agentsound.hornist.arrange - the breath inside
held notes (pushes, swells, blooms, tapers), air-coupled vibrato, scoops / falls / doits, mic moves, and the rare shake
or growl at the climax. Use hornist.vocabulary(...) (= vocabulary() here):

    from agentsound import soloist, hornist
    perf = soloist.solo(s, sax, hornist.vocabulary('sax', style='hero'), at=solo, prog=PROG, motif=HOOK, seed=3)

Moves (MOVES: name -> (roles, energy, density, spice, fast)):
  motif      the motif (the song's hook) breathed: legato, a swell / push on its peak, vibrato on the held notes
  answer     a falling pentatonic answer landing on a chord tone (taper, breath release)
  riff       a short cell stated twice, the second time answered differently (call and response in one breath)
  long_tone  a pickup into a long held chord tone: swell, vibrato deepening with the air, the bell leaning in
  scoop_call a phrase whose notes are scooped into (the vocal sax / trumpet entry)
  fall_off   an answer that falls off its last note
  sequence   a pentatonic cell sequenced up (8ths / 16ths within the breath)
  run        a scale run up to a held peak                                             (fast)
  shake      a held peak with a lip / sax shake (sax, trumpet)                        (fast)
  growl      a held peak growled (sax, trombone)                                       (fast)
  resolve    down to the tonic: a long last note tapering, the bell turning away
"""

from __future__ import annotations

from . import soloist as S
from .patterns import Clip, Note, as_clip
from .soloist import Move, Part, Vocabulary
from .theory import ComposeError

__all__ = ['vocabulary', 'MOVES', 'RANGES']

MOVES = {
    'motif': (('motif',), 0.4, 0.4, False, False),
    'answer': (('answer', 'resolve', 'develop'), 0.5, 0.5, False, False),
    'riff': (('develop', 'answer'), 0.62, 0.6, False, False),
    'long_tone': (('answer', 'climax', 'develop'), 0.72, 0.15, False, False),
    'scoop_call': (('answer', 'develop'), 0.55, 0.4, True, False),
    'fall_off': (('answer', 'resolve'), 0.45, 0.35, True, False),
    'sequence': (('develop', 'burst'), 0.72, 0.78, False, False),
    'run': (('burst',), 0.9, 0.95, True, True),
    'shake': (('climax', 'burst'), 0.95, 0.3, True, True),
    'growl': (('climax', 'burst'), 1.0, 0.3, True, True),
    'resolve': (('resolve',), 0.35, 0.3, False, False),
}
"""name -> (roles, energy, density, spice, fast)."""

RANGES = {'sax': ('C4', 'A5'), 'trumpet': ('E4', 'C6'), 'trombone': ('F3', 'F5'), 'flute': ('D5', 'D7'),
          'clarinet': ('E4', 'C6'), 'strings': ('G4', 'E6')}
"""The solo range (sounding) per hornist family: the arc moves inside it."""


def _perform(ctx, steps_or_clip, *, peaks=(), climax: bool = False, extra=()) -> Part:
    """A line played by hornist.arrange (the family / style of the vocabulary; its budgets counted over the solo)."""
    from . import hornist
    c = steps_or_clip if isinstance(steps_or_clip, Clip) else \
        Clip._raw([Note(t, d, p, 92) for t, d, p in steps_or_clip], ctx.beats)
    c = as_clip(c)
    if not len(c):
        return Part()
    cfg = ctx.memory['_horn']
    mem = ctx.memory.setdefault('_horn_mem', hornist.Memory())
    lo, hi = ctx.vel
    perf = hornist.arrange(c, ctx.bpm, family=cfg['family'], style=cfg['style'], energy=0.55 + 0.6 * ctx.energy,
                           peaks=tuple(peaks), vel=(lo, hi), seed=ctx.rng.randrange(1 << 30), climax=climax,
                           memory=mem, at=ctx.at, bpb=ctx.bpb)
    return Part(perf.clip, list(perf.gestures) + list(extra), [(a, b, k, n) for a, b, k, n in perf.moves])


def _peak(steps) -> list:
    """The beat of the highest held note of a line (the phrase's peak: the most air)."""
    held = [(p, d, t) for t, d, p in steps if d >= 0.75]
    return [max(held)[2]] if held else []


def m_motif(ctx) -> Part:
    c = S.motif_in_register(ctx)
    ns = list(c)
    return _perform(ctx, c, peaks=_peak([(n.start, n.dur, n.pitch) for n in ns])) if ns else Part()


def m_answer(ctx) -> Part:
    st = S.answer_line(ctx, grid_=0.5 if ctx.density < 0.6 else 0.25)
    return _perform(ctx, st)


def m_riff(ctx) -> Part:
    pcs = S.pentatonic(ctx)
    a = S.fold(S.snap(S.center(ctx), pcs), ctx)
    cell = [a, S.step(a, pcs, 1), S.step(a, pcs, 2)]
    ans = [cell[0], S.step(a, pcs, -1), S.snap(S.step(a, pcs, -2), S.chord_tones(ctx, ctx.at + 2.5), -1)]
    g = 0.5
    st = [(i * g, g, p) for i, p in enumerate(S.fit(cell, ctx))]
    t = len(cell) * g + 0.5
    st += [(t + i * g, g, p) for i, p in enumerate(S.fit(ans[:-1], ctx))]
    t2 = t + 2 * g
    st.append((t2, max(0.5, ctx.beats - t2 - 0.25), S.fold(ans[-1], ctx)))
    return _perform(ctx, [x for x in st if x[0] < ctx.beats - 0.25])


def m_long_tone(ctx) -> Part:
    tones = S.chord_tones(ctx, ctx.at + 1.0)
    top = S.fold(S.snap(S.center(ctx, 0.1), tones, 1), ctx)
    pcs = S.pentatonic(ctx)
    pick = S.fit([S.step(top, pcs, -2), S.step(top, pcs, -1), top], ctx)
    st = [(0.0, 0.5, pick[0]), (0.5, 0.5, pick[1]), (1.0, max(1.0, ctx.beats - 1.25), pick[2])]
    return _perform(ctx, st, peaks=[1.0], climax=ctx.stage == 'climax')


def m_scoop_call(ctx) -> Part:
    from . import hornist
    st = S.answer_line(ctx, grid_=0.5)
    pt = _perform(ctx, st)
    if len(pt.clip):
        first = min(pt.clip, key=lambda n: n.start)
        pt.gestures.append(hornist.scoop(first.start, ctx.bpm, cents=-ctx.rng.uniform(60, 110), ms=ctx.rng.uniform(80, 130)))
    return pt


def m_fall_off(ctx) -> Part:
    from . import hornist
    st = S.answer_line(ctx)
    t, d, p = st[-1]
    st[-1] = (t, min(d, 2.0), p)
    pt = _perform(ctx, st)
    if len(pt.clip):
        last = max(pt.clip, key=lambda n: n.start)
        pt.gestures.append(hornist.fall(last.start + last.dur, ctx.bpm, semis=-ctx.rng.uniform(3, 6),
                                        ms=ctx.rng.uniform(180, 320)))
    return pt


def m_sequence(ctx) -> Part:
    g = S.grid(ctx, 9.0, (0.25, 1 / 3, 0.5)) if ctx.density > 0.6 else 0.5
    st = S.sequence_line(ctx, grid_=g, length=ctx.beats - 1.5)
    end = st[-1][0] + g
    top = S.fold(S.snap(S.step(st[-1][2], S.pentatonic(ctx), 1), S.chord_tones(ctx, ctx.at + end)), ctx)
    st.append((end, max(0.75, ctx.beats - end - 0.25), top))
    return _perform(ctx, st, peaks=[end])


def m_run(ctx) -> Part:
    g = S.grid(ctx, 11.0, (1 / 6, 0.25, 1 / 3))
    n = max(5, min(16, int((ctx.beats - 1.5) / g)))
    line = S.fit(S.run_line(ctx, n, up=True), ctx)
    st = [(i * g, g, p) for i, p in enumerate(line)]
    end = n * g
    top = S.fold(S.snap(S.step(line[-1], S.scale(ctx), 1), S.chord_tones(ctx, ctx.at + end), 1), ctx)
    st.append((end, max(0.75, ctx.beats - end - 0.25), top))
    return _perform(ctx, st, peaks=[end], climax=True)


def _peak_move(ctx, kind: str) -> Part:
    from . import hornist
    pt = m_long_tone(ctx)
    held = max(pt.clip, key=lambda n: n.dur) if len(pt.clip) else None
    if held is None or held.dur * 60.0 / ctx.bpm < 1.0:
        return pt
    s, d = held.start, held.dur
    g = hornist.shake(s + 0.45 * d, 0.45 * d, ctx.bpm, interval=3.0) if kind == 'shake' else \
        hornist.growl(s + 0.25 * d, 0.6 * d, ctx.bpm)
    pt.gestures.append(g)
    pt.log.append((round(g.start, 4), round(g.end, 4), 'pitch', kind))
    return pt


def m_shake(ctx) -> Part:
    return _peak_move(ctx, 'shake')


def m_growl(ctx) -> Part:
    return _peak_move(ctx, 'growl')


def m_resolve(ctx) -> Part:
    from . import hornist
    k = S.key_of(ctx)
    start = ctx.last.pitch if ctx.last is not None else S.center(ctx, 0.1)
    tonic = S.fold(S.snap(S.center(ctx, -0.05), {k.tonic}), ctx)
    line, q = [], start
    while len(line) < 4 and abs(q - tonic) > 2:
        q = S.step(q, S.scale(ctx), -1 if q > tonic else 1)
        line.append(q)
    st = [(i * 0.5, 0.5, p) for i, p in enumerate(S.fit(line, ctx))]
    t = len(st) * 0.5
    st.append((t, max(1.0, ctx.beats - t), tonic))
    pt = _perform(ctx, st)
    if ctx.next_at is None and len(pt.clip):
        last = max(pt.clip, key=lambda n: n.start)
        pt.gestures.append(hornist.fade_away(last.start, last.dur, ctx.bpm))
    return pt


_FUNCS = {'motif': m_motif, 'answer': m_answer, 'riff': m_riff, 'long_tone': m_long_tone,
          'scoop_call': m_scoop_call, 'fall_off': m_fall_off, 'sequence': m_sequence, 'run': m_run,
          'shake': m_shake, 'growl': m_growl, 'resolve': m_resolve}


def _motif_maker(ctx) -> Clip:
    pcs = S.pentatonic(ctx)
    a = S.fold(S.snap(S.center(ctx), pcs), ctx)
    b = S.step(a, pcs, 2)
    notes = [Note(0.0, 0.5, a, 90), Note(0.5, 0.5, S.step(a, pcs, 1), 94), Note(1.0, 2.0, b, 102),
             Note(3.5, 0.5, S.step(b, pcs, -1), 88), Note(4.0, 2.5, a, 94)]
    return Clip._raw(notes, 8.0)


def vocabulary(family: str = 'sax', *, style: str = 'hero', register=None, vel=(64, 120), moves=None, weights=None,
               phrase_bars: float = 2, budget=None) -> Vocabulary:
    """The wind player's soloist.Vocabulary: MOVES played through hornist.arrange (family: hornist.FAMILIES - sax,
    trumpet, trombone, flute, clarinet, strings; style: hornist.STYLES - hero, pop, ballad, jazz, classical), the
    family's range (RANGES; register=(lo, hi) overrides), vel=(lo, hi) of the whole solo, weights= / moves= as the
    guitar's (shake only where the family shakes, growl where it growls), budget= the soloist budget in bars (default:
    spice every 2, fast every 12, same 24). The default place: the notes + hornist.render (air, mic, pitch, vibrato on
    the track's targets)."""
    from . import hornist
    if family not in hornist.FAMILIES:
        raise ComposeError(f"wind vocabulary family must be one of {', '.join(hornist.FAMILIES)}, got {family!r}")
    if style not in hornist.STYLES:
        raise ComposeError(f"wind vocabulary style must be one of {', '.join(hornist.STYLES)}, got {style!r}")
    F = hornist.FAMILIES[family]
    w = {'shake': 1.0 if F['shake'] else 0.0, 'growl': 1.0 if F['growl'] else 0.0}
    w.update(weights or {})
    names = list(MOVES) if moves is None else list(moves)
    cfg = {'family': family, 'style': style}
    mv = []
    for n in names:
        if n not in MOVES:
            raise ComposeError(f"unknown wind solo move {n!r}; moves: {', '.join(MOVES)}")
        if w.get(n, 1.0) <= 0:
            continue
        roles, e, d, spice, fast = MOVES[n]
        mv.append(Move(n, 0.0, e, d, spice, _wrap(_FUNCS[n], cfg), fast=fast, roles=roles, weight=w.get(n, 1.0)))
    rng = register or RANGES[family]
    return Vocabulary(mv, motif=_wrap(_motif_maker, cfg), name=f'{family}:{style}', vel=vel, phrase_bars=phrase_bars,
                      budget=budget if budget is not None else dict(spice_every=2.0, fast_every=12, same_every=24),
                      range=rng)


def _wrap(fn, cfg):
    def play(ctx):
        ctx.memory.setdefault('_horn', cfg)
        return fn(ctx)
    play.__name__ = getattr(fn, '__name__', 'move')
    return play
