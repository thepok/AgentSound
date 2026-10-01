"""Figuration: the textures an orchestra (or a pianist's left hand) plays from a harmony or from held notes - the
string drive, offbeat pulses, syncopes, oom-pah, Alberti, broken chords, ostinatos, measured tremolo, running 16ths.

    from agentsound import figures
    drive = figures.figure(parts['violas'], 'pulse8')            # held notes -> repeated 8ths inside each
    sync = figures.figure(parts['violins1'], 'syncope')           # off-beat attacks held over the beat
    lh = h.figure('broken', vel=46, seed=11)                      # a Harmony (s.prog / voicing.Harmony) -> a Clip
    oom = h.figure('oompah', low='E2', vel=(86, 60, 52))          # bass on the 1, the chord on the other beats
    line.figure('pulse8', gap=0.45)                               # a Clip's notes repeated (velocities kept)

Two families:
  * REPEAT figures re-attack each held note: 'pulse8' (8ths), 'pulse16', 'beats' (quarters), 'offbeats' (the 8th
    after each beat), 'syncope' (off-beat attacks held across the next beat: the sforzando between the beats),
    'tremolo' (measured 32nds). Options step= (every=) / gap= (the sounding length, cut at the note's end) /
    offset= (from the note's start). The input decides the output: (start, dur, pitch[, vel]) tuples give tuples
    (the velocity carried), a Clip gives a Clip (velocities and marks kept).
  * CHORD figures play a harmony (a Harmony / Progression: (start, dur, Chord) per chord): 'oompah' (bass on the
    downbeat, the chord on the other beats), 'alberti' (low-high-mid-high 8ths), 'broken' (a ballad pianist's
    rolling broken chords in 8ths: root, 5th, octave, 10th, 12th ... with a 4-bar arc), 'ostinato' (8ths on the
    bass note, the octave on every 4th, an accent every 3rd), 'storm16' (running 16ths between the chord's two top
    tones). They return a Clip in the harmony's own beats.

Every figure is a default: change any note afterwards (clip.window / map / vel_add, or write the bar by hand) - the
figure only saves writing the repeated notes.
"""

from __future__ import annotations

import math
import random

from .patterns import Clip, Note, as_clip
from .theory import ComposeError, note as _note

__all__ = ['FIGURES', 'REPEAT', 'CHORD_FIGURES', 'figure', 'repeat']

REPEAT = {
    'pulse8': {'step': 0.5, 'gap': 0.42, 'offset': 0.0},
    'pulse16': {'step': 0.25, 'gap': 0.2, 'offset': 0.0},
    'beats': {'step': 1.0, 'gap': 0.8, 'offset': 0.0},
    'offbeats': {'step': 1.0, 'gap': 0.42, 'offset': 0.5},
    'syncope': {'step': 1.0, 'gap': 0.85, 'offset': 0.5},
    'tremolo': {'step': 0.125, 'gap': 0.11, 'offset': 0.0},
}
"""Repeat figures: re-attacks every `step` beats from `offset`, each sounding `gap` beats (cut at the note's end)."""

CHORD_FIGURES = ('oompah', 'alberti', 'broken', 'ostinato', 'storm16')
FIGURES = tuple(REPEAT) + CHORD_FIGURES
_EPS = 1e-6


def _p(x) -> int:
    return x if isinstance(x, int) else _note(x)


def repeat(notes, step: float = 0.5, gap: float = 0.42, offset: float = 0.0):
    """Re-attack each note every `step` beats from its start + `offset` while it sounds, each attack `gap` beats long
    (cut at the note's end). notes: (start, dur, pitch[, vel ...]) tuples -> tuples, or a Clip -> a Clip."""
    if step <= 0 or gap <= 0:
        raise ComposeError(f"figure: step and gap must be > 0 beats, got step={step!r} gap={gap!r}")
    if isinstance(notes, Clip):
        out = []
        for n in notes:
            k = n.start + offset
            while k < n.start + n.dur - _EPS:
                out.append(n._replace(start=k, dur=min(gap, n.start + n.dur - k)))
                k += step
        return Clip._raw(out, notes.length)
    out = []
    for n in notes:
        a, d, p, rest = n[0], n[1], n[2], tuple(n[3:])
        k = a + offset
        while k < a + d - _EPS:
            out.append((k, min(gap, a + d - k), p) + rest)
            k += step
    return out


def _chords(h):
    """(start, dur, Chord) of a Harmony / Progression / [(start, dur, chord)] (rests skipped)."""
    from .theory import chord as _chord
    out = []
    for st, d, c in h:
        if c is None:
            continue
        out.append((st, d, _chord(c) if isinstance(c, str) else c))
    return out


def _length(h) -> float:
    return float(getattr(h, 'length', 0.0) or max((s + d for s, d, _ in _chords(h)), default=0.0))


def _bpb(h, kw) -> float:
    return float(kw.pop('beats_per_bar', None) or getattr(h, 'beats_per_bar', 4.0) or 4.0)


def _vel(v) -> int:
    return max(1, min(127, int(round(v))))


def _broken(h, vel=60, low=36, top=64, seed=0, phrase=16.0, step=0.5):
    """The ballad pianist's left hand: rolling broken chords in 8ths (root, 5th, octave, 10th, 12th ...), the 1 and
    the 3 leaning in, a `phrase`-beat arc, every note a little different (seeded)."""
    rnd = random.Random(seed)
    out = []
    low, top = _p(low), _p(top)
    for st, ln, c in _chords(h):
        r = c.bass_note(low=low)
        third_ = 3 if c.is_minor else 4
        fifth = 6 if 'dim' in c.quality or 'b5' in c.quality else 7
        up = [r, r + fifth, r + 12, r + 12 + third_, r + 12 + fifth, r + 12 + third_, r + 12, r + fifth]
        up = [p if p <= top else p - 12 for p in up]
        k = 0
        t = 0.0
        while t < ln - 1e-6:
            pos = st + t
            arc = 0.9 + 0.2 * abs(((pos / phrase) % 1.0) - 0.5) * -2 + 0.1
            acc = 1.18 if abs(t % 2.0) < 1e-6 else (0.8 if (t % 1.0) > 0.25 else 0.92)
            v = vel * acc * arc * (1 + rnd.uniform(-0.06, 0.06))
            out.append((pos, 0.9 if t + step < ln else 0.5, up[k % len(up)], max(20, min(110, round(v)))))
            k += 1
            t += step
    return Clip(out, length=_length(h))


def _oompah(h, low='E2', vel=(78, 60, 52), accent=8, wave=3, bass_dur=0.6, chord_dur=0.35, octave=4, notes=3,
            beats_per_bar=None, split=False):
    """Bass on each chord's downbeat (its bass note from `low`), the chord (`notes` tones from `octave`) on the other
    beats of its bar. vel: (bass, beat 2, beat 3 ...); every other chord's bass + accent, the chords rise by `wave`
    over four chords. split=True: (the oom Clip, the pah Clip) for two sections."""
    bpb = float(beats_per_bar or getattr(h, 'beats_per_bar', 4.0))
    vs = vel if isinstance(vel, (tuple, list)) else (vel, vel * 0.78, vel * 0.68)
    oom, pah = [], []
    for i, (t, ln, c) in enumerate(_chords(h)):
        oom.append((t, bass_dur, c.bass_note(low=_p(low)), _vel(vs[0] + (accent if i % 2 == 0 else 0))))
        up = c.notes(octave)[:notes]
        b = 1
        while b < min(ln, bpb) - 1e-6:
            v = vs[min(b, len(vs) - 1)]
            pah += [(t + b, chord_dur, p, _vel(v + (i % 4) * wave)) for p in up]
            b += 1
    if split:
        return Clip(oom, length=_length(h)), Clip(pah, length=_length(h))
    return Clip(oom + pah, length=_length(h))


def _alberti(h, octave=4, vel=60, step=0.5, gap=0.45):
    """low - high - middle - high in 8ths over each chord (its first three tones from `octave`)."""
    out = []
    for t, ln, c in _chords(h):
        lo_, mid, hi_ = c.notes(octave)[:3]
        k, j = 0.0, 0
        while k < ln - 1e-6:
            p = (lo_, hi_, mid, hi_)[j % 4]
            out.append((t + k, min(gap, ln - k), p, _vel(vel * (1.1 if j % 4 == 0 else 0.9))))
            k += step
            j += 1
    return Clip(out, length=_length(h))


def _ostinato(h, low='A2', vel=84, accent=14, octave_every=4, accent_every=3, step=0.5, gap=0.35):
    """8ths on each chord's bass note (from `low`), its octave on every `octave_every`-th 8th, + `accent` on every
    `accent_every`-th (a string ostinato under a rock anthem)."""
    out = []
    for t, ln, c in _chords(h):
        r = c.bass_note(low=_p(low))
        for j in range(int(ln / step)):
            out.append((t + j * step, gap, r + (12 if j % octave_every == octave_every - 1 else 0),
                        _vel(vel + (accent if j % accent_every == 0 else 0))))
    return Clip(out, length=_length(h))


def _storm16(h, octave=5, vel=96, accent=10, soft=-5, gap=0.22):
    """Running 16ths alternating the chord's two top tones (from `octave`), the beat accented (+accent, else soft)."""
    out = []
    for t, ln, c in _chords(h):
        ps = sorted(c.notes(octave))
        hi_, lo_ = ps[-1], ps[-2] if len(ps) > 1 else ps[-1]
        k = 0.0
        while k < ln - 1e-6:
            on = abs(k - round(k)) < 1e-6
            out.append((t + k, gap, hi_ if int(round(k * 4)) % 2 == 0 else lo_, _vel(vel + (accent if on else soft))))
            k += 0.25
    return Clip(out, length=_length(h))


_CHORD_FN = {'oompah': _oompah, 'alberti': _alberti, 'broken': _broken, 'ostinato': _ostinato, 'storm16': _storm16}


def figure(src, kind: str, **kw):
    """A figure (FIGURES) from held notes / a Clip (repeat figures) or a harmony (chord figures); options override
    the figure's defaults (REPEAT[kind] or the chord figure's keywords: step=, gap=, offset=, every= ...)."""
    if kind in REPEAT:
        o = dict(REPEAT[kind])
        if 'every' in kw:
            kw['step'] = kw.pop('every')
        bad = set(kw) - set(o)
        if bad:
            raise ComposeError(f"figure {kind!r}: unknown option(s) {sorted(bad)}; it takes step (every), gap, offset")
        o.update(kw)
        if hasattr(src, 'items') and not isinstance(src, (Clip, list, tuple)):
            raise ComposeError(f"figure {kind!r} repeats held notes: give notes or a Clip, not a harmony "
                               f"(h.figure('{kind}') voices it first: h.voice(...).figure('{kind}'))")
        return repeat(src, o['step'], o['gap'], o['offset'])
    if kind in _CHORD_FN:
        try:
            return _CHORD_FN[kind](src, **kw)
        except TypeError as e:
            raise ComposeError(f"figure {kind!r}: {e}") from None
    raise ComposeError(f"unknown figure {kind!r}; figures: {', '.join(FIGURES)}")


def _clip_figure(self, kind: str, **kw) -> Clip:
    return figure(self, kind, **kw)


Clip.figure = _clip_figure
