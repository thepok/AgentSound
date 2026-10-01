"""Fretwork: a lead guitarist's hands INSIDE and BETWEEN notes - the micro-performance that makes a sampled guitar
sound played (the hornist's breath, for a guitar hero).

The user's wish (2026-10-01): "masterful electric guitar solos, and the techniques needed for them, like we did for
the saxophone". A rock / blues / fusion lead is not a line of picked notes: the string is BENT (fast rise, a little
overshoot, settling on pitch; pre-bent and released; held with a vibrato that goes down from the bent pitch; two
strings bent in unison), the fretting hand adds VIBRATO that only goes UP from the note (narrow and fast, or wide
and slow, delayed, widening as the note sings), HAMMERS and PULLS notes without the pick (a legato attack), SLIDES
into, out of and between notes, the picking hand ALTERNATES with accents, TREMOLO-picks, SWEEPS arpeggios and RAKES
into a note, and the hands and the amp make TONE moves - a PINCH harmonic's squeal, PALM-muted chugs, a WHAMMY dive
or scoop, a held note blooming into controlled FEEDBACK (the string's upper harmonic taking over), a WAH sweep, a
PICK SCRAPE, finger squeaks.

Every move here returns a soloist.Part: the notes (as written for the guitar: the fretted pitch of a bent note) and
gestures on agentsound.gesture's abstract lanes (shared with the hornist: 'bend' semitones, 'harm' 0..1 the string's
harmonic, 'mute' 0..1 palm mute, 'wah' / 'wahmix' the pedal, 'air' dB after the compressor, 'echo' throws), plus
latched per-note steps ('bendfollow', 'harmonicnum') and aux notes (a 'twin' string for unison bends on a mono lead,
'noise' for scrapes and squeaks). render(track, part, at) writes it all on a track:

    from agentsound import fretwork as fw
    part = fw.bend('A5', 3, s.tempo, amount=2) .merge(fw.vibrato(...))     # moves are Parts (merge / shifted)
    fw.render(lead, part, at=solo.bar(3))          # notes (hero_guitar.play: zone lock, glides) + every lane
    fw.render(lead, [p1.shifted(0), p2.shifted(8)], at=solo)               # several at once: one lane per target

Targets (targets(track)): 'bend' -> 'instrument.pitchbend' (a stack forwards it to its layers); 'harm' / 'mute' /
the steps -> every sampler layer's 'harmonic' / 'cutoff' / 'bendfollow' / 'harmonicnum' (engine: the sampler's
string harmonic and per-note bend latch); 'wah' / 'wahmix' -> a 'wah' fx inserted ahead of the amp (in every zone of a
hero stack, else first on the track: wah_stage()); 'air' -> the breath stage 'fx.air.gain' (agentsound.heroes /
hornist.air_stage: after the compressor, so pick accents survive it); 'echo' -> 'fx.echo.mix' (the hero's own echo).
The moves are used by guitarist.vocabulary() (the soloist's guitar) and guitarist.lead(gestures=True).
"""

from __future__ import annotations

import math
import random

from . import articulation as _art
from . import gesture as G
from .patterns import Clip, Note, _vel, as_clip, seed_int
from .soloist import Part
from .theory import ComposeError, note

__all__ = ['VIBRATOS', 'MOVES', 'bend', 'prebend', 'ghost_bend', 'unison_bend', 'oblique_bend', 'vibrato',
           'hammer_on', 'pull_off', 'trill', 'legato_run', 'slide', 'slide_in', 'slide_out', 'picked_run',
           'tremolo_pick', 'sweep', 'rake', 'pinch', 'palm_mute', 'whammy_dive', 'whammy_scoop', 'whammy_vibrato',
           'feedback', 'wah', 'wah_talk', 'pick_scrape', 'squeak', 'accents', 'targets', 'render', 'wah_stage',
           'noise_track', 'twin_track', 'pinch_partial', 'lanes']

_EPS = 1e-6
_PICK_GAP_MS = 14.0      # a re-picked note: the one before stops this much earlier (a new attack on a legato sampler)
_TIE = 0.03              # beats a slurred note overlaps the next (a mono='legato' sampler plays no new attack)


# ------------------------------------------------------------------------------------------------ helpers

def _num(x, what, lo=None, hi=None) -> float:
    return G._num(x, what, lo, hi)


def _bpm(bpm) -> float:
    return G._bpm(bpm)


def _b(seconds: float, bpm: float) -> float:
    return seconds * bpm / 60.0


def _ms(ms: float, bpm: float) -> float:
    return ms / 1000.0 * bpm / 60.0


def _pos(at) -> float:
    if hasattr(at, 'start') and not isinstance(at, (int, float)):
        return float(at.start)
    return _num(at, 'at (beats)')


def _v(vel) -> float:
    if isinstance(vel, (tuple, list)):
        return float(vel[0])
    return _num(vel, 'vel', 1, 127)


def _n(start, dur, pitch, vel, art=None, glide=None) -> Note:
    n = Note(float(max(0.0, start)), float(max(0.02, dur)), int(pitch), _vel(max(1.0, min(127.0, vel))))
    if art is not None or glide:
        n = _art._mark(n, art=art, gl=glide)
    return n


def _part(notes, gestures=(), log=(), steps=None, aux=None, length=None, tricks=()) -> Part:
    ns = sorted(notes, key=lambda n: (n.start, n.pitch))
    end = max((n.start + n.dur for n in ns), default=0.0)
    for g in gestures:
        end = max(end, g.end)
    L = float(length) if length is not None else end
    return Part(Clip._raw(ns, L), list(gestures), list(log), list(tricks), steps, aux)


def _shift(p: Part, at) -> Part:
    a = _pos(at)
    return p if a == 0 else p.shifted(a)


def _rng(seed, *salt) -> random.Random:
    return random.Random(f"{seed_int(seed)}:" + ':'.join(str(s) for s in salt))


def _hz(pitch: float) -> float:
    return 440.0 * 2.0 ** ((pitch - 69) / 12.0)


# ------------------------------------------------------------------------------------------------ vibrato

VIBRATOS = {
    'narrow': dict(depth=24.0, hz=6.4, delay=0.2, grow=0.35, widen=0.25, wobble=0.12),
    'rock': dict(depth=45.0, hz=5.7, delay=0.24, grow=0.4, widen=0.45, wobble=0.15),
    'wide': dict(depth=70.0, hz=5.0, delay=0.3, grow=0.5, widen=0.5, wobble=0.15),
    'blues': dict(depth=85.0, hz=4.6, delay=0.28, grow=0.45, widen=0.4, wobble=0.2),
    'bb': dict(depth=60.0, hz=6.8, delay=0.12, grow=0.25, widen=0.2, wobble=0.15),
    'shred': dict(depth=110.0, hz=7.0, delay=0.15, grow=0.3, widen=0.3, wobble=0.12),
    'subtle': dict(depth=14.0, hz=5.6, delay=0.35, grow=0.6, widen=0.3, wobble=0.1),
}
"""Finger vibrato styles (cents of the push UP from the note, Hz, delay / grow s, widen = how much it opens over a
long note, wobble = a player's unevenness): narrow (fast and tight: Knopfler, fusion), rock (Slash, the default),
wide (Gilmour's slow wide singing), blues (Gary Moore's slow and wide), bb (B.B. King's fast "butterfly"), shred (Zakk
Wylde's wide and fast), subtle (clean ballads). Guitar vibrato goes ABOVE the note (the string is pushed); on a held
bend it goes BELOW the bent pitch (released a little and pushed back)."""


def _vib(start, dur, bpm, style='rock', *, shape='up', depth=None, hz=None, delay=None, seed=0, scale=1.0):
    if isinstance(style, dict):
        V = dict(VIBRATOS['rock'], **style)
    else:
        if style not in VIBRATOS:
            raise ComposeError(f"vibrato style must be one of {', '.join(VIBRATOS)}, got {style!r}")
        V = dict(VIBRATOS[style])
    if depth is not None:
        V['depth'] = depth
    if hz is not None:
        V['hz'] = hz
    if delay is not None:
        V['delay'] = delay
    r = _rng(seed, 'vib', round(start, 4))
    return G.vibrato(start, dur, bpm, depth=V['depth'] * scale * (0.9 + 0.2 * r.random()),
                     hz=V['hz'] * (0.96 + 0.08 * r.random()), delay=V['delay'], grow=V['grow'], rise=0.25,
                     shape=shape, lane='bend', widen=V['widen'], wobble=V['wobble'], seed=r.randrange(1 << 30))


def vibrato(pitch, dur, bpm, *, style='rock', depth=None, hz=None, delay=None, vel=96, seed=0, at=0.0) -> Part:
    """A held note with finger vibrato (VIBRATOS style or a dict): straight for `delay` s, then the string pushed UP
    and back at `hz`, the push growing to `depth` cents and opening up further on a long note, a little uneven (a
    hand, not an LFO)."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'vibrato dur', 0.1)
    g = _vib(0.0, D, b, style, depth=depth, hz=hz, delay=delay, seed=seed)
    return _shift(_part([_n(0, D, p, _v(vel))], [g], [(0.0, D, 'vibrato', style if isinstance(style, str) else 'custom')]),
                  at)


# ------------------------------------------------------------------------------------------------ bends

_RISE = {1: 95.0, 2: 140.0, 3: 190.0, 4: 240.0}


def bend(pitch, dur, bpm, *, amount: float = 2, rise_ms=None, delay_ms: float = 0.0, overshoot=None,
         settle_ms: float = 120.0, release=None, release_ms: float = 200.0, vib='rock', vib_depth=None,
         vel=104, back=None, seed=0, at=0.0) -> Part:
    """A bend INTO `pitch`: the note fretted `amount` semitones lower (1 = half step, 2 = whole step, 3 = a step
    and a half, 4 = two steps) and pushed up after delay_ms over rise_ms (default by amount: 95 / 140 / 190 / 240 ms -
    a wider bend takes longer), overshooting a few cents (overshoot=, default 4 + 3 x amount ct, a little random) and
    settling onto pitch (settle_ms); held with a vibrato (vib= a VIBRATOS style or None) that goes DOWN from the
    bent pitch; release= a share of dur: let back down over release_ms (bend and release). back= the next onset
    (beats from the move's start): the lane is at 0 again before it. Returns a Part."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'bend dur', 0.1)
    k = _num(amount, 'bend amount (semitones)', 0.25, 5)
    r = _rng(seed, 'bend', p, D)
    rise = rise_ms if rise_ms is not None else _RISE.get(int(round(k)), 140.0 + 50.0 * (k - 2))
    rise *= 0.9 + 0.2 * r.random()
    ov = (4.0 + 3.0 * k) * (0.7 + 0.6 * r.random()) if overshoot is None else overshoot
    rel = None if release is None else D * _num(release, 'bend release (share of dur)', 0.1, 0.95)
    g = G.bend(0.0, D, b, semis=k, at=delay_ms / 1000.0, rise_ms=rise, overshoot=ov, settle_ms=settle_ms,
               release=rel, release_ms=release_ms, back=back)
    gs = [g]
    land = _b(delay_ms / 1000.0 + (rise + settle_ms) / 1000.0, b)
    vend = rel if rel is not None else D
    if vib and vend - land > _b(0.35, b):
        gs.append(_vib(land, vend - land, b, vib, shape='down', depth=vib_depth, delay=0.1, seed=seed, scale=0.7))
    log = [(0.0, D, 'bend', f"bend {k:g}" + (' + release' if rel is not None else ''))]
    return _shift(_part([_n(0, D, p - k, _v(vel))], gs, log), at)


def prebend(pitch, dur, bpm, *, amount: float = 2, release: float = 0.4, release_ms: float = 260.0,
            pre_ms: float = 90.0, vib='rock', vel=96, back=None, seed=0, at=0.0) -> Part:
    """A pre-bend and release: the string bent up SILENTLY pre_ms before the pick (the note sounds at `pitch`), held,
    then let down after `release` x dur over release_ms to the fretted note `amount` lower - the crying fall of a blues
    ballad. A finger vibrato on the landed note when it is long enough. Needs a rest of pre_ms before it."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'prebend dur', 0.1)
    k = _num(amount, 'prebend amount', 0.25, 5)
    rel = D * _num(release, 'prebend release', 0.05, 0.95)
    rw = _ms(release_ms, b)
    g = G.bend(0.0, D, b, semis=k, pre=pre_ms / 1000.0, release=rel, release_ms=release_ms, back=back)
    gs = [g]
    if vib and D - (rel + rw) > _b(0.4, b):
        gs.append(_vib(rel + rw, D - rel - rw, b, vib, delay=0.12, seed=seed, scale=0.8))
    return _shift(_part([_n(0, D, p - k, _v(vel))], gs, [(0.0, D, 'bend', f"prebend {k:g}")]), at)


def ghost_bend(pitch, dur, bpm, *, amount: float = 2, release: float = 0.25, release_ms: float = 380.0,
               vel=96, seed=0, at=0.0, **kw) -> Part:
    """A ghost bend: pre-bent silently and picked SOFTLY (the attack ghosted, ~0.62 x vel), the slow release is what
    you hear - it swells a little as it falls (Gilmour's sighing release)."""
    b = _bpm(bpm)
    v = _v(vel) * 0.62
    pt = prebend(pitch, dur, b, amount=amount, release=release, release_ms=release_ms, vel=v, seed=seed, **kw)
    D = _num(dur, 'ghost_bend dur', 0.1)
    rel = D * release
    pt.gestures.append(G.swell(0.0, D, b, lo=-2.5, peak=1.5, end=-1.0, peak_at=min(0.9, release + 0.25),
                               bright=0.3))
    pt.log = [(0.0, D, 'bend', f"ghost bend {amount:g}")]
    del rel
    return _shift(pt, at)


def unison_bend(pitch, dur, bpm, *, amount: float = 2, rise_ms=None, vib='rock', vel=106, mono: bool = True,
                rake_ms: float = 8.0, seed=0, at=0.0) -> Part:
    """A unison bend: `pitch` held on the higher string while the lower string, fretted `amount` lower, is bent up to
    meet it - landing a few cents off for the beating that makes it sing (Hendrix, Page, every rock solo's climax).
    The held string never bends: on a mono lead (mono=True, a hero stack) it plays on the 'twin' aux track (a second
    instance of the guitar: twin_track()), on a polyphonic guitar it is latched out of the bend ('bendfollow' 0, the
    sampler's per-note bend latch). The bent string's vibrato goes below the pitch."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'unison_bend dur', 0.25)
    r = _rng(seed, 'unison', p)
    rk = _ms(rake_ms, b)
    bent = bend(p, D - rk, b, amount=amount, rise_ms=rise_ms, overshoot=-(3.0 + 6.0 * r.random()), vib=vib,
                vel=_v(vel) * 0.95, seed=seed)
    bent = bent.shifted(rk)
    held = _n(0.0, D, p, _v(vel) * 0.9)
    if mono:
        out = bent
        out.aux = {'twin': Clip._raw([held], D)}
    else:
        out = Part(Clip._raw(sorted([held] + list(bent.clip)), D), bent.gestures, bent.log, (),
                   {'bendfollow': [(-_ms(4, b), 0.0), (rk - _ms(3, b), 1.0)]})
    out.log = [(0.0, D, 'bend', f"unison bend {amount:g}")]
    return _shift(out, at)


def oblique_bend(top, dur, bpm, *, interval: int = 5, amount: float = 2, vib=None, vel=104, mono: bool = True,
                 seed=0, at=0.0) -> Part:
    """An oblique bend (a double stop with one string bent): `top` held on the higher string, the string below bent
    `amount` up to `interval` semitones under it (5 = a fourth: the classic G-string-under-B-string move; 3, 4: thirds).
    Held string as unison_bend (twin track on a mono lead, bendfollow 0 on a polyphonic guitar)."""
    b = _bpm(bpm)
    t, D = note(top), _num(dur, 'oblique_bend dur', 0.25)
    target = t - int(_num(interval, 'oblique interval', 2, 9))
    rk = _ms(7.0, b)
    bent = bend(target, D - rk, b, amount=amount, vib=vib, vel=_v(vel) * 0.95, seed=seed).shifted(rk)
    held = _n(0.0, D, t, _v(vel) * 0.9)
    if mono:
        out = bent
        out.aux = {'twin': Clip._raw([held], D)}
    else:
        out = Part(Clip._raw(sorted([held] + list(bent.clip)), D), bent.gestures, bent.log, (),
                   {'bendfollow': [(-_ms(4, b), 0.0), (rk - _ms(3, b), 1.0)]})
    out.log = [(0.0, D, 'bend', f"oblique bend {amount:g} under {interval}")]
    return _shift(out, at)


# ------------------------------------------------------------------------------------------------ legato

def _tied_line(steps, bpm, *, picked, vel, accent=1.0, slur=0.78) -> list:
    """Notes of a line [(start, dur, pitch)]: picked[i] True = a pick (a small gap before it so it re-attacks), else
    slurred (tied into from the note before: no new attack, softer)."""
    gap = _ms(_PICK_GAP_MS, bpm)
    out = []
    for i, (s, d, p) in enumerate(steps):
        nxt_picked = i + 1 < len(steps) and picked[i + 1]
        if i + 1 < len(steps):
            ns = steps[i + 1][0]
            end = ns - gap if nxt_picked else ns + _TIE
        else:
            end = s + d
        v = vel * (accent if picked[i] and i == 0 else 1.0) * (1.0 if picked[i] else slur)
        out.append(_n(s, max(0.03, end - s), p, v))
    return out


def hammer_on(frm, to, dur, bpm, *, split: float = 0.5, vel=96, at=0.0) -> Part:
    """frm picked, `to` (above) sounded by the fretting finger alone at split x dur: tied, no pick attack, softer."""
    b = _bpm(bpm)
    p0, p1 = note(frm), note(to)
    D = _num(dur, 'hammer_on dur', 0.05)
    sp = D * _num(split, 'hammer_on split', 0.05, 0.95)
    ns = _tied_line([(0.0, sp, p0), (sp, D - sp, p1)], b, picked=[True, False], vel=_v(vel))
    return _shift(_part(ns, (), [(sp, D, 'legato', 'hammer_on' if p1 > p0 else 'pull_off')]), at)


def pull_off(frm, to, dur, bpm, **kw) -> Part:
    """frm picked, the finger pulls off to the lower `to` (a little pluck, no pick)."""
    if note(to) >= note(frm):
        raise ComposeError(f"pull_off goes down: {to!r} must be below {frm!r}")
    return hammer_on(frm, to, dur, bpm, **kw)


def trill(pitch, dur, bpm, *, upper: int = 2, rate: float = 11.0, vel=96, seed=0, at=0.0) -> Part:
    """A hammer-on / pull-off trill: `pitch` and `upper` semitones above alternated at `rate` notes per second by the
    fretting hand alone - one pick, all the rest tied and lighter, a slight unevenness, the last part holding the
    note. FAST: the rarest spice."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'trill dur', 0.25)
    step = _b(1.0 / _num(rate, 'trill rate', 4, 20), b)
    r = _rng(seed, 'trill', p)
    body = max(2 * step, D - min(0.5, 0.3 * D))
    n = max(2, int(body / step))
    steps = []
    for i in range(n):
        t = i * step + (_ms(4.0, b) * (r.random() * 2 - 1) if i else 0.0)
        steps.append((max(0.0, t), step, p if i % 2 == 0 else p + int(upper)))
    steps.append((n * step, D - n * step, p))
    ns = _tied_line(steps, b, picked=[True] + [False] * (len(steps) - 1), vel=_v(vel), slur=0.74)
    ns = [x._replace(vel=_vel(x.vel * (1.0 + 0.06 * math.sin(math.pi * i / len(ns))))) for i, x in enumerate(ns)]
    return _shift(_part(ns, (), [(0.0, D, 'legato', 'trill')], tricks=[(0.0, 'trill', True)]), at)


def legato_run(pitches, dur, bpm, *, per_string: int = 3, vel=(92, 104), grid=None, seed=0, at=0.0) -> Part:
    """A legato run (Satriani, Holdsworth, Vai): the notes even across `dur` (or on `grid` beats), only the first
    note on each string picked (every per_string notes), the rest hammered / pulled: tied, softer, no pick attack -
    smooth and fluid where a picked run is percussive. vel=(start, end): a crescendo or a fade."""
    b = _bpm(bpm)
    ps = [note(x) for x in pitches]
    if len(ps) < 2:
        raise ComposeError("legato_run needs 2+ pitches")
    D = _num(dur, 'legato_run dur', 0.1)
    st = D / len(ps) if grid is None else _num(grid, 'legato_run grid', 0.05)
    r = _rng(seed, 'legato_run', len(ps))
    v0, v1 = (vel if isinstance(vel, (tuple, list)) else (vel, vel))
    steps = [(i * st + (_ms(3.0, b) * (r.random() * 2 - 1) if i else 0.0), st, q) for i, q in enumerate(ps)]
    steps = [(max(0.0, s), d, q) for s, d, q in steps]
    picked = [i % max(1, int(per_string)) == 0 for i in range(len(ps))]
    ns = []
    for i, x in enumerate(_tied_line(steps, b, picked=picked, vel=1.0, slur=0.8)):
        f = i / max(1, len(ps) - 1)
        ns.append(x._replace(vel=_vel(max(1.0, (v0 + (v1 - v0) * f) * (x.vel / 1.0)))))
    last = ns[-1]
    ns[-1] = last._replace(dur=max(last.dur, D - last.start))
    return _shift(_part(ns, (), [(0.0, D, 'legato', 'legato_run')], tricks=[(0.0, 'legato_run', False)]), at)


def slide(frm, to, dur, bpm, *, split: float = 0.5, ms=None, vel=96, squeak: bool = False, at=0.0) -> Part:
    """A shift slide on one string: frm held for split x dur, then the finger slides to `to` without a new pick (a
    glide mark: the mono legato sampler bends into it - ms default ~22 ms per fret, 50-160 ms), the target a little
    softer. squeak=True: a finger-slide noise on the 'noise' aux track."""
    b = _bpm(bpm)
    p0, p1 = note(frm), note(to)
    D = _num(dur, 'slide dur', 0.1)
    sp = D * _num(split, 'slide split', 0.05, 0.95)
    g = ms if ms is not None else max(50.0, min(160.0, 22.0 * abs(p1 - p0)))
    ns = [_n(0.0, sp + _TIE, p0, _v(vel)), _n(sp, D - sp, p1, _v(vel) * 0.86, glide=float(g))]
    aux = {'noise': Clip._raw([_n(sp - _ms(g * 0.5, b), _ms(g, b), 96 if p1 > p0 else 92, 40)], D)} if squeak else None
    return _shift(_part(ns, (), [(sp, D, 'legato', 'slide')], aux=aux), at)


def slide_in(pitch, dur, bpm, *, frm: float = -4, ms: float = 110.0, vel=100, at=0.0) -> Part:
    """Sliding INTO a note from `frm` semitones away (below: negative): the note picked there and slid up to pitch over
    ms (the bend lane: one attack, a smooth glissando - a slide guitarist's or a rock lead's entry)."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'slide_in dur', 0.1)
    g = G.scoop(0.0, b, cents=_num(frm, 'slide_in frm', -12, 12) * 100.0, ms=ms)
    g.name = 'slide_in'
    return _shift(_part([_n(0.0, D, p, _v(vel))], [g], [(0.0, _ms(ms, b), 'legato', 'slide_in')]), at)


def slide_out(pitch, dur, bpm, *, semis: float = -7, ms: float = 300.0, vel=96, back=None, at=0.0) -> Part:
    """A note that slides OFF at its end: the last `ms` the finger slides `semis` down the neck while the note dies
    (the air fades): a phrase end."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'slide_out dur', 0.1)
    g = G.fall(D, b, semis=_num(semis, 'slide_out semis', -24, 24), ms=min(ms, 0.8 * D * 60000.0 / b), back=back,
               air=-12.0)
    g.name = 'slide_out'
    return _shift(_part([_n(0.0, D, p, _v(vel))], [g], [(D - _ms(ms, b), D, 'legato', 'slide_out')]), at)


# ------------------------------------------------------------------------------------------------ the picking hand

def accents(notes, bpm, *, db_per_vel: float = 0.1, limit: float = 4.0, back=None):
    """The pick's note-to-note dynamics as an 'air' gesture after the compressor (gesture.accents: the hornist's
    accents, shared): a hero lead's compressor squeezes the velocities, this gives them back."""
    ns = sorted((float(n.start), float(n.dur), float(n.vel)) for n in notes)
    return G.accents(ns, bpm, db_per_vel=db_per_vel, limit=limit, back=back)


def picked_run(pitches, dur, bpm, *, group: int = 4, vel=(90, 108), accent: float = 1.12, down: float = 1.05,
               gate: float = 0.88, grid=None, seed=0, at=0.0) -> Part:
    """An alternate-picked burst: every note picked (down-up-down-up: the downstrokes a little stronger), the first of
    every `group` accented (sextuplets: group=6), a crescendo from vel[0] to vel[1], a few ms of human timing; each
    note stops just before the next pick (gate) - percussive, articulate (Al Di Meola, Paul Gilbert, Gary Moore's
    runs). Pick accents also as 'air' after the compressor."""
    b = _bpm(bpm)
    ps = [note(x) for x in pitches]
    if not ps:
        raise ComposeError("picked_run needs pitches")
    D = _num(dur, 'picked_run dur', 0.05)
    st = D / len(ps) if grid is None else _num(grid, 'picked_run grid', 0.05)
    r = _rng(seed, 'picked', len(ps))
    v0, v1 = (vel if isinstance(vel, (tuple, list)) else (vel, vel))
    ns = []
    for i, q in enumerate(ps):
        f = i / max(1, len(ps) - 1)
        v = (v0 + (v1 - v0) * f) * (accent if i % max(1, group) == 0 else 1.0) * (down if i % 2 == 0 else 1.0 / down)
        v *= 0.96 + 0.08 * r.random()
        t = i * st + (_ms(3.0, b) * (r.random() * 2 - 1) if i else 0.0)
        d = st * gate if i + 1 < len(ps) else max(st, D - i * st)
        ns.append(_n(max(0.0, t), d, q, v))
    g = accents(ns, b)
    return _shift(_part(ns, [g] if g.shapes else [], [(0.0, D, 'picking', 'picked_run')],
                        tricks=[(0.0, 'picked_run', True)]), at)


def tremolo_pick(pitch, dur, bpm, *, rate: float = 13.0, vel=(84, 112), seed=0, at=0.0) -> Part:
    """Tremolo picking: one note picked down-up at `rate` notes per second (11-16), the downstrokes stronger, a
    crescendo vel[0] -> vel[1] (the climax of a solo, surf, Dick Dale), pick accents after the compressor. FAST."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'tremolo_pick dur', 0.1)
    step = _b(1.0 / _num(rate, 'tremolo_pick rate', 4, 24), b)
    n = max(2, int(D / step + _EPS))
    pt = picked_run([p] * n, n * step, b, group=2, vel=vel, accent=1.08, gate=0.8, seed=seed)
    pt.log = [(0.0, D, 'picking', 'tremolo_pick')]
    pt.tricks = [(0.0, 'tremolo_pick', True)]
    return _shift(pt, at)


def sweep(pitches, dur, bpm, *, direction: str = 'updown', vel=(88, 104), top_hammer: bool = True, seed=0,
          at=0.0) -> Part:
    """A sweep-picked arpeggio (Yngwie, Becker, fusion): one note per string (pitches low -> high, e.g. a triad over 5
    strings), the pick sweeping through in one motion - each note picked and muted as the next sounds (a rolling, not
    a strummed, chord) - up, and with direction='updown' back down; at the top a hammer-on / pull-off turn
    (top_hammer: the top note tied, no pick). FAST spice."""
    b = _bpm(bpm)
    ps = sorted(note(x) for x in pitches)
    if len(ps) < 3:
        raise ComposeError("sweep needs 3+ pitches (one per string)")
    seq = ps if direction == 'up' else (ps[::-1] if direction == 'down' else ps + ps[-2::-1])
    if direction not in ('up', 'down', 'updown'):
        raise ComposeError(f"sweep direction must be 'up', 'down' or 'updown', got {direction!r}")
    D = _num(dur, 'sweep dur', 0.1)
    st = D / len(seq)
    picked = [True] * len(seq)
    if top_hammer and direction == 'updown':
        picked[len(ps) - 1] = False            # the top: hammered from the string below's position
    steps = [(i * st, st, q) for i, q in enumerate(seq)]
    v0, v1 = (vel if isinstance(vel, (tuple, list)) else (vel, vel))
    ns = []
    for i, x in enumerate(_tied_line(steps, b, picked=picked, vel=1.0, slur=0.85)):
        f = i / max(1, len(seq) - 1)
        ns.append(x._replace(vel=_vel((v0 + (v1 - v0) * (1 - abs(2 * f - 1))) * x.vel)))
    ns[-1] = ns[-1]._replace(dur=max(ns[-1].dur, D - ns[-1].start))
    return _shift(_part(ns, [accents(ns, b)], [(0.0, D, 'picking', f'sweep {direction}')],
                        tricks=[(0.0, 'sweep', True)]), at)


def rake(pitch, dur, bpm, *, strings: int = 3, ms: float = 16.0, vel=104, at=0.0) -> Part:
    """A rake into a note: the pick dragged across `strings` muted strings below it (dead, choked scratches: short,
    soft notes under a palm-mute 'mute' plateau) before the note is picked - the note lands at strings x ms."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'rake dur', 0.1)
    n = int(_num(strings, 'rake strings', 1, 5))
    st = _ms(_num(ms, 'rake ms', 5, 60), b)
    ns = [_n(i * st, st * 0.85, p - 5 * (n - i), _v(vel) * (0.4 + 0.07 * i)) for i in range(n)]
    ns.append(_n(n * st, D, p, _v(vel)))
    mute = G.Gesture('rake', 'tone', 0.0, n * st, [G._Shape('mute', [(0.0, 0.9), (n * st - _ms(3, b), 0.9),
                                                                     (n * st, 0.0)], jump=True)])
    return _shift(_part(ns, [mute], [(0.0, n * st, 'picking', 'rake')]), at)


# ------------------------------------------------------------------------------------------------ tone moves

def pinch_partial(pitch, top_hz: float = 2600.0) -> int:
    """The partial a pinch harmonic squeals on for this note: the highest of 3..6 under ~top_hz (a low note
    screams two octaves + a fifth up, a high one an octave + fifth)."""
    f = _hz(note(pitch))
    for n in (6, 5, 4, 3):
        if f * n <= top_hz:
            return n
    return 2


def pinch(pitch, dur, bpm, *, partial=None, amount: float = 0.8, vib='shred', vel=112, back=None, seed=0,
          at=0.0) -> Part:
    """A pinch harmonic (the thumb grazes the string as it is picked: the squeal - Zakk Wylde, Billy Gibbons): the
    note's partial (pinch_partial(): 3-6) brought out from the pick on (the 'harm' lane stepped up a few ms before
    the note, 'harmonicnum' latched), held through the note with a wide vibrato on top, gone after it. Spice."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'pinch dur', 0.1)
    n = pinch_partial(p) if partial is None else int(_num(partial, 'pinch partial', 2, 8))
    a = _num(amount, 'pinch amount', 0.1, 1.0)
    pre = _ms(6.0, b)
    end = D + _ms(40.0, b)
    if back is not None:
        end = min(end, float(back) - _ms(4, b))
    h = G.Gesture('pinch', 'tone', -pre, end, [G._Shape('harm', [(-pre, a), (D * 0.6, a), (D, a * 0.85), (end, 0.0)],
                                                        jump=True)], dict(partial=n, amount=a))
    gs = [h]
    if vib and D * 60.0 / b > 0.4:
        gs.append(_vib(0.0, D, b, vib, delay=0.15, seed=seed))
    return _shift(_part([_n(0.0, D, p, _v(vel))], gs, [(0.0, D, 'tone', f'pinch harmonic {n}')],
                        steps={'harmonicnum': [(-pre - _ms(6, b), float(n))]}, tricks=[(0.0, 'pinch', False)]), at)


def palm_mute(pitches, dur, bpm, *, grid: float = 0.25, depth: float = 0.8, vel=(92, 108), accents_on=1.0,
              seed=0, at=0.0) -> Part:
    """Palm-muted chugs inside a lead (the hand's edge on the strings at the bridge): short, dark, percussive notes
    on the `grid` (16ths), the pitches cycled, accents every `accents_on` beats, under a 'mute' plateau of `depth`
    (the voices' low-pass closing: thud, not ring) that opens again after."""
    b = _bpm(bpm)
    ps = [note(x) for x in (pitches if isinstance(pitches, (list, tuple)) else [pitches])]
    D = _num(dur, 'palm_mute dur', 0.1)
    gr = _num(grid, 'palm_mute grid', 0.0625, 2)
    r = _rng(seed, 'pm', len(ps))
    v0, v1 = (vel if isinstance(vel, (tuple, list)) else (vel, vel))
    n = max(1, int(D / gr + _EPS))
    ns = []
    for i in range(n):
        t = i * gr
        acc = accents_on and abs(t / accents_on - round(t / accents_on)) < 1e-6
        v = (v0 + (v1 - v0) * i / max(1, n - 1)) * (1.1 if acc else 0.92) * (0.95 + 0.1 * r.random())
        ns.append(_n(t + (_ms(2.5, b) * (r.random() * 2 - 1) if i else 0.0), gr * 0.5, ps[i % len(ps)], v))
    k = _ms(15, b)
    m = G.Gesture('palm_mute', 'tone', -k, D + k, [G._Shape('mute', [(-k, 0.0), (0.0, depth), (D, depth),
                                                                      (D + k, 0.0)])])
    return _shift(_part(ns, [m, accents(ns, b)], [(0.0, D, 'tone', 'palm_mute')]), at)


def whammy_dive(pitch, dur, bpm, *, semis: float = -12, start: float = 0.35, dive: float = 0.5,
                back_up: bool = False, vel=110, at=0.0) -> Part:
    """A whammy-bar dive: the note held, then the bar pushed down `semis` (to -24) over `dive` x dur from `start` x
    dur (Van Halen, Vai, the end of a burst); back_up=True brings it back up at the end (a dive-and-return)."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'whammy_dive dur', 0.25)
    sm = _num(semis, 'whammy semis', -24, 4)
    t0 = D * _num(start, 'whammy start', 0, 0.9)
    t1 = min(D, t0 + D * _num(dive, 'whammy dive', 0.05, 1.0))
    keys = [(t0, 0.0), (t1, sm)]
    if back_up:
        keys += [(t1 + 0.15 * (D - t1), sm), (D, 0.0)]
    else:
        keys += [(D, sm), (D + _ms(30, b), 0.0)]
    g = G.Gesture('whammy_dive', 'pitch', t0, D, [G._Shape('bend', keys)], dict(semis=sm))
    air = G.Gesture('whammy_dive', 'air', t0, D, [G._Shape('air', [(t0, 0.0), (t1, -3.0), (D, -6.0),
                                                                   (D + _ms(30, b), 0.0)])])
    return _shift(_part([_n(0.0, D, p, _v(vel))], [g, air], [(t0, D, 'whammy', 'dive')],
                        tricks=[(t0, 'whammy_dive', False)]), at)


def whammy_scoop(pitch, dur, bpm, *, semis: float = -1.5, ms: float = 130.0, vel=104, at=0.0) -> Part:
    """A whammy scoop: the bar pressed just before the pick and released into pitch (a scooped, vocal attack)."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'whammy_scoop dur', 0.1)
    g = G.scoop(0.0, b, cents=_num(semis, 'whammy_scoop semis', -12, 0) * 100.0, ms=ms)
    g.name = 'whammy_scoop'
    return _shift(_part([_n(0.0, D, p, _v(vel))], [g], [(0.0, _ms(ms, b), 'whammy', 'scoop')]), at)


def whammy_vibrato(pitch, dur, bpm, *, depth: float = 35.0, hz: float = 5.2, delay: float = 0.25, vel=100,
                   seed=0, at=0.0) -> Part:
    """Bar vibrato: smooth and CENTRED around the note (the bar goes both ways, unlike the finger), wider and rounder
    than a finger vibrato (Jeff Beck, Satriani's melodies)."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'whammy_vibrato dur', 0.1)
    g = G.vibrato(0.0, D, b, depth=depth, hz=hz, delay=delay, grow=0.5, shape='centre', lane='bend', widen=0.3,
                  wobble=0.08, seed=seed)
    return _shift(_part([_n(0.0, D, p, _v(vel))], [g], [(0.0, D, 'whammy', 'bar vibrato')]), at)


def feedback(pitch, dur, bpm, *, partial: int = 2, start: float = 0.3, bloom_s: float = 1.4, amount: float = 0.85,
             swell_db: float = 3.0, vib='wide', vel=104, back=None, seed=0, at=0.0) -> Part:
    """Controlled feedback on a long held note (the guitar facing the amp): the note sustains, and from `start` x dur
    its upper partial (2 = the octave, 3 = octave + fifth) blooms in over bloom_s seconds until it carries the note
    (`amount`; the engine holds it at the note's peak level - it sustains like feedback), a little louder as it
    grows (swell_db, after the compressor), then a wide vibrato on top. The note should be 2+ s long. Spice."""
    b = _bpm(bpm)
    p, D = note(pitch), _num(dur, 'feedback dur', 0.5)
    n = int(_num(partial, 'feedback partial', 2, 6))
    t0 = D * _num(start, 'feedback start', 0.05, 0.8)
    t1 = min(D, t0 + _b(_num(bloom_s, 'feedback bloom_s', 0.2, 6), b))
    a = _num(amount, 'feedback amount', 0.1, 1.0)
    end = D + _ms(50, b)
    if back is not None:
        end = min(end, float(back) - _ms(4, b))
    h = G.Gesture('feedback', 'tone', t0, end, [G._Shape('harm', [(t0, 0.0), (t1, a), (D, a), (end, 0.0)])],
                  dict(partial=n, amount=a))
    sw = G.Gesture('feedback', 'air', t0, end, [G._Shape('air', [(t0, 0.0), (t1, swell_db), (D, swell_db * 0.8),
                                                                 (end, 0.0)])])
    gs = [h, sw]
    if vib and D - t1 > _b(0.4, b):
        gs.append(_vib(t1 - _b(0.1, b), D - t1 + _b(0.1, b), b, vib, delay=0.2, seed=seed))
    return _shift(_part([_n(0.0, D, p, _v(vel))], gs, [(t0, D, 'tone', f'feedback bloom x{n}')],
                        steps={'harmonicnum': [(-_ms(8, b), float(n))]}, tricks=[(t0, 'feedback', False)]), at)


def wah(dur, bpm, *, kind: str = 'swell', lo: float = 0.08, hi: float = 0.92, pos: float = 0.6, grid: float = 0.5,
        fade_ms: float = 30.0, at=0.0) -> Part:
    """A wah-pedal move over `dur` beats (no notes: merge it with the notes it colours): 'swell' (heel -> toe over the
    span: a vowel opening), 'close' (toe -> heel), 'wacka' (rocking heel <-> toe every `grid` beats: the funk / Hendrix
    "wacka"), 'cocked' (parked at `pos`: the nasal Money-for-Nothing / Schenker tone). The wah is switched in
    ('wahmix') for the span and out after."""
    b = _bpm(bpm)
    D = _num(dur, 'wah dur', 0.1)
    f = _ms(fade_ms, b)
    if kind == 'swell':
        keys = [(0.0, lo), (D, hi)]
    elif kind == 'close':
        keys = [(0.0, hi), (D, lo)]
    elif kind == 'cocked':
        keys = [(0.0, pos), (D, pos)]
    elif kind == 'wacka':
        gr = _num(grid, 'wah grid', 0.0625, 4)
        keys = []
        t, i = 0.0, 0
        while t <= D + _EPS:
            keys.append((min(t, D), lo if i % 2 == 0 else hi))
            t += gr
            i += 1
    else:
        raise ComposeError(f"wah kind must be 'swell', 'close', 'wacka' or 'cocked', got {kind!r}")
    g = G.Gesture('wah', 'tone', -f, D + f, [G._Shape('wah', keys), G._Shape('wahmix', [(-f, 0.0), (0.0, 1.0), (D, 1.0),
                                                                                       (D + f, 0.0)])],
                  dict(kind=kind))
    # the pedal lane holds its last value after the span (the wah is switched out): it rests at `lo`
    return _shift(_part([], [g], [(0.0, D, 'tone', f'wah {kind}')], length=D), at)


def wah_talk(clip, bpm, *, lo: float = 0.1, hi: float = 0.85, open_ms: float = 45.0, close_ms: float = 260.0,
             at=0.0) -> Part:
    """A talking wah that follows the playing: on every pick the foot rocks open (open_ms) and closes over close_ms
    (the 'wah-wah' of each note - Hendrix, Slash's "Sweet Child" solo). No notes: merge with the clip it follows."""
    b = _bpm(bpm)
    c = as_clip(clip)
    ns = sorted(c, key=lambda n: n.start)
    if not ns:
        return _part([], [], [], length=0.0)
    keys = [(ns[0].start - _ms(20, b), lo)]
    for i, n in enumerate(ns):
        t = n.start
        if t <= keys[-1][0] + _EPS:
            continue
        nxt = ns[i + 1].start if i + 1 < len(ns) else n.start + n.dur
        top = t + min(_ms(open_ms, b), 0.4 * (nxt - t))
        down = min(nxt - _ms(5, b), top + _ms(close_ms, b))
        keys += [(t, keys[-1][1]), (top, hi)]
        if down > top + _EPS:
            keys.append((down, lo + 0.25 * (hi - lo)))
    end = max(n.start + n.dur for n in ns)
    f = _ms(30, b)
    keys.append((end, lo))
    g = G.Gesture('wah_talk', 'tone', keys[0][0], end + f,
                  [G._Shape('wah', keys), G._Shape('wahmix', [(keys[0][0] - f, 0.0), (keys[0][0], 1.0), (end, 1.0),
                                                              (end + f, 0.0)])])
    return _shift(_part([], [g], [(ns[0].start, end, 'tone', 'wah talk')], length=c.length), at)


def pick_scrape(dur, bpm, *, vel=96, at=0.0) -> Part:
    """A pick scrape (the pick's edge dragged down the wound strings: a rasping 'shhhrrrr' falling in pitch - an intro
    or the drop into a solo) on the 'noise' aux track (noise_track(): band-passed noise through the amp, its filter
    following the note: one note gliding from high to low)."""
    b = _bpm(bpm)
    D = _num(dur, 'pick_scrape dur', 0.25)
    ns = [_n(0.0, _ms(30, b) + _TIE, 100, _v(vel)), _n(_ms(30, b), D - _ms(30, b), 60, _v(vel) * 0.9,
                                                      glide=float(min(2000.0, D * 60000.0 / b * 0.9)))]
    return _shift(_part([], [], [(0.0, D, 'tone', 'pick scrape')], aux={'noise': Clip._raw(ns, D)}, length=D), at)


def squeak(bpm, *, pitch: int = 98, ms: float = 70.0, vel=36, at=0.0) -> Part:
    """A finger squeak (the fingertip sliding on a wound string at a position shift): a tiny noise sweep on the
    'noise' aux track."""
    b = _bpm(bpm)
    d = _ms(ms, b)
    ns = [_n(0.0, d * 0.4 + _TIE, pitch, _v(vel)), _n(d * 0.4, d * 0.6, pitch - 6, _v(vel) * 0.8, glide=float(ms * 0.5))]
    return _shift(_part([], [], [(0.0, d, 'tone', 'squeak')], aux={'noise': Clip._raw(ns, d)}, length=d), at)


MOVES = {'bend': bend, 'prebend': prebend, 'ghost_bend': ghost_bend, 'unison_bend': unison_bend,
         'oblique_bend': oblique_bend, 'vibrato': vibrato, 'hammer_on': hammer_on, 'pull_off': pull_off,
         'trill': trill, 'legato_run': legato_run, 'slide': slide, 'slide_in': slide_in, 'slide_out': slide_out,
         'picked_run': picked_run, 'tremolo_pick': tremolo_pick, 'sweep': sweep, 'rake': rake, 'pinch': pinch,
         'palm_mute': palm_mute, 'whammy_dive': whammy_dive, 'whammy_scoop': whammy_scoop,
         'whammy_vibrato': whammy_vibrato, 'feedback': feedback, 'wah': wah, 'wah_talk': wah_talk,
         'pick_scrape': pick_scrape, 'squeak': squeak}
"""Every fretwork move by name (each returns a soloist.Part)."""


# ------------------------------------------------------------------------------------------------ targets + render

def _stack(track):
    ins = getattr(track, 'instrument', None)
    return ins if getattr(ins, 'type', None) == 'stack' else None


def _sampler_prefixes(track) -> list:
    st = _stack(track)
    if st is not None:
        return [f'instrument.layers.{x.id}' for x in st.params['layers'] if x.instrument.type == 'sampler']
    if getattr(getattr(track, 'instrument', None), 'type', None) == 'sampler':
        return ['instrument']
    return []


def _own_instrument(track):
    """The track's instrument as its own copy (a patch's instrument is shared by every track playing it)."""
    from .patches import Instrument
    if not getattr(track, '_fretwork_own', False):
        track.instrument = Instrument.coerce(track.instrument)
        track._fretwork_own = True
    return track.instrument


def wah_stage(track, **params) -> list:
    """The track's wah: a 'wah' fx ahead of the amp, switched out (mix 0) until a wah move switches it in. On a stack
    (the hero guitars: an amp per velocity zone) one in front of every zone's chain, else the first fx of the track.
    Returns the automation prefixes ('instrument.layers.<id>.fx.0' / 'fx.wah')."""
    from .patches import FX
    if '_fretwork_wah' in track.__dict__:
        return track._fretwork_wah
    p = {'pedal': 0.1, 'mix': 0.0, 'q': 5.0, 'lo': 380, 'hi': 2100, 'gain': 3.0}
    p.update(params)
    st = _stack(track)
    if st is not None:
        st = _own_instrument(track)
        out = []
        for x in st.params['layers']:
            if x.instrument.type == 'sampler':
                x.fx.insert(0, FX('wah', dict(p), name='wah'))
                out.append(f'instrument.layers.{x.id}.fx.0')
        track._fretwork_wah = out
    else:
        track.fx.insert(0, FX('wah', dict(p), name='wah'))
        track._fretwork_wah = ['fx.wah']
    return track._fretwork_wah


def targets(track) -> dict:
    """Where this track's lanes go: {'bend': 'instrument.pitchbend', 'samplers': [prefixes of every sampler (layer)],
    'air': 'fx.air.gain' (the breath stage), 'echo': ('fx.echo.mix', base) or None}."""
    from .hornist import air_stage
    out = {'bend': 'instrument.pitchbend', 'samplers': _sampler_prefixes(track), 'echo': None}
    st_air, p = air_stage(track)
    out['air'] = f'fx.air.{p}' if st_air is not None else None
    for f in getattr(track, 'fx', []) or []:
        if getattr(f, 'name', None) == 'echo':
            out['echo'] = ('fx.echo.mix', float((f.params or {}).get('mix', 0.2)))
    return out


def lanes(gestures, bpm) -> dict:
    """{lane: points} - the gestures sampled per lane (gesture._sample)."""
    out = {}
    for ln in G.LANES:
        sh = [s for g in gestures for s in g.shapes if s.lane == ln]
        if sh:
            out[ln] = G._sample(sh, lambda v, ln=ln: v.get(ln, 0.0), bpm)
    return out


def _mute_cut(m: float) -> float:
    m = max(0.0, min(1.0, m))
    return round(math.exp(math.log(20000.0) + m * (math.log(650.0) - math.log(20000.0))), 1)


def render(track, parts, at=0.0, *, notes: bool = True, aux_tracks=None, bpm=None) -> dict:
    """Write fretwork Parts on a track: the notes (agentsound.patches.hero_guitar.play: glide marks on every sampler
    layer of a stack, ties kept inside one velocity zone), then every lane once (one automation lane per target):
    bend -> 'instrument.pitchbend'; harm -> each sampler's 'harmonic'; mute -> each sampler's 'cutoff' (20 kHz open ..
    650 Hz at 1); wah / wahmix -> the wah stage (wah_stage(): pedal / mix); air -> the breath stage; echo -> 'fx.echo.mix'
    (base + lane); vib -> each sampler's 'vibrato'; steps ('bendfollow', 'harmonicnum') -> each sampler, as steps.
    aux notes go to aux_tracks={'twin': Track, 'noise': Track} (made with twin_track() / noise_track(); missing ones
    are created). parts: a Part or a list of Parts (positions from `at`). Returns {target: number of points}."""
    from .patches import hero_guitar as _hg
    ps = parts if isinstance(parts, (list, tuple)) else [parts]
    a = _pos(at)
    song = getattr(track, '_song', None)
    if song is not None and hasattr(at, 'start'):
        a = song._at(at)
    allp = Part()
    for p in ps:
        allp = allp.merge(Part.of(p))
    allp = allp.shifted(a) if a else allp
    b = _bpm(bpm if bpm is not None else (song.tempo_at(a) if song is not None else 120.0))
    written: dict = {}
    if notes and len(allp.clip):
        _hg.play(track, allp.clip, 0.0)
    plan = targets(track)
    ln = lanes(allp.gestures, b)

    def put_on(tr, target, pts):
        pts = _from_zero(pts)
        if pts:
            tr.automate(target, pts)
            written[f'{tr.id}:{target}'] = written.get(f'{tr.id}:{target}', 0) + len(pts)

    def put(target, pts):
        pts = _from_zero(pts)
        if pts:
            track.automate(target, pts)
            written[target] = written.get(target, 0) + len(pts)

    if 'bend' in ln:
        put(plan['bend'], [(t, max(-24.0, min(24.0, v))) + tuple(r) for t, v, *r in ln['bend']])
    for pre in plan['samplers']:
        if 'harm' in ln:
            put(f'{pre}.harmonic', [(t, round(max(0.0, min(1.0, v)), 5)) + tuple(r) for t, v, *r in ln['harm']])
        if 'mute' in ln:
            put(f'{pre}.cutoff', [(t, _mute_cut(v)) + tuple(r) for t, v, *r in ln['mute']])
        if 'vib' in ln:
            put(f'{pre}.vibrato', [(t, max(0.0, min(200.0, v))) + tuple(r) for t, v, *r in ln['vib']])
        for param, steps in allp.steps.items():
            pts = []
            last = None
            for t, v in sorted(steps):
                if last is not None and abs(t - last) < 1e-6:
                    pts[-1] = (pts[-1][0], v, 'step')
                    continue
                pts.append((max(0.0, t), v, 'step'))
                last = t
            put(f'{pre}.{param}', pts)
    if 'wah' in ln or 'wahmix' in ln:
        for pre in wah_stage(track):
            if 'wah' in ln:
                put(f'{pre}.pedal', [(t, round(max(0.0, min(1.0, v)), 5)) + tuple(r) for t, v, *r in ln['wah']])
            if 'wahmix' in ln:
                put(f'{pre}.mix', [(t, round(max(0.0, min(1.0, v)), 5)) + tuple(r) for t, v, *r in ln['wahmix']])
    if 'air' in ln and plan['air'] is not None:
        put(plan['air'], [(t, max(-30.0, min(12.0, v))) + tuple(r) for t, v, *r in ln['air']])
    if 'echo' in ln and plan['echo'] is not None:
        tgt, base = plan['echo']
        put(tgt, [(t, max(0.0, min(1.0, base + v))) + tuple(r) for t, v, *r in ln['echo']])
    if allp.aux:
        aux_tracks = dict(aux_tracks or {})
        for role, clip in allp.aux.items():
            tr = aux_tracks.get(role)
            if tr is None:
                if song is None:
                    raise ComposeError(f"fretwork.render: aux notes for {role!r} need a track in a song")
                tr = twin_track(song, track) if role == 'twin' else noise_track(song, track) if role == 'noise' else None
                if tr is None:
                    raise ComposeError(f"fretwork.render: no aux track for {role!r} (aux_tracks={{'{role}': track}})")
            if role == 'twin':
                _hg.play(tr, clip, 0.0)
            elif getattr(tr.instrument, 'type', None) == 'sampler':
                tr.play(clip, 0.0)
            else:                       # a synth (the noise track): glide marks -> its portamento time, stepped
                gl = []
                for n in sorted(clip, key=lambda n: n.start):
                    g = _art.glide_of(n)
                    if g:
                        gl += [(max(0.0, n.start - 0.06), round(g / 1000.0, 4), 'step'), (n.start + 0.02, 0.15, 'step')]
                tr.play(_art.plain(clip), 0.0)
                if gl:
                    put_on(tr, 'instrument.glide', gl)
            written[f'aux:{role}'] = len(clip)
    return written


def _from_zero(pts) -> list:
    """Points from beat 0 on: those before it collapse into one point at 0 (the value there)."""
    pts = sorted(pts, key=lambda p: p[0])
    neg = [p for p in pts if p[0] <= 0.0]
    if not neg:
        return pts
    return [(0.0,) + tuple(neg[-1][1:2])] + [p for p in pts if p[0] > 0.0]


def twin_track(song, lead, id=None):
    """A second instance of the lead guitar for the held string of unison / oblique bends on a mono lead (its own
    pitch bend: none). Same patch, sends and fx as the lead, a hair to the side. Made once per lead."""
    tid = id or f'{lead.id}_twin'
    if tid in song.tracks:
        return song.tracks[tid]
    tr = song.track(tid, lead.patch or lead.instrument, pan=max(-1.0, min(1.0, (lead.pan or 0.0) + 0.12)))
    tr.fx = [f.copy() for f in lead.fx]
    tr.gain_db = lead.gain_db - 1.5
    tr.sends.update(dict(getattr(lead, 'sends', {}) or {}))
    tr._patch_sends = dict(getattr(lead, '_patch_sends', {}) or {})
    return tr


def noise_track(song, lead, id=None, level_db: float = -8.0):
    """The guitar's noise track for pick scrapes and finger squeaks: band-passed noise (a va: noise only, a 12 dB
    band-pass that follows the note 1:1, portamento in legato) through a crunch amp and cabinet, the lead's sends.
    Its notes are filter positions (C4 = 900 Hz): a glide from a high to a low note is a scrape."""
    tid = id or f'{lead.id}_noise'
    if tid in song.tracks:
        return song.tracks[tid]
    from .patches import inst
    from .patches import sampled_guitars as _sg
    noise = inst.va(**{'osc1.level': 0.0, 'osc2.level': 0.0, 'noise.level': 1.0, 'noise.color': 'white',
                       'filter.type': 'bp12', 'cutoff': 900, 'filter.keytrack': 1.0, 'resonance': 0.55,
                       'hpf': 250, 'amp.attack': 0.004, 'amp.decay': 0.6, 'amp.sustain': 0.7, 'amp.release': 0.08,
                       'amp.velocity': 0.9, 'glide': 0.15, 'mode': 'legato'})
    tr = song.track(tid, noise, fx=_sg._amp('lead', drive=20.0, bright=3.0), gain_db=level_db,
                    pan=getattr(lead, 'pan', 0.0) or 0.0)
    tr.sends.update(dict(getattr(lead, '_patch_sends', {}) or {}))
    tr.sends.update(dict(getattr(lead, 'sends', {}) or {}))
    return tr
