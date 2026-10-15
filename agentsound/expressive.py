"""The shared expression layer: the performance rules that belong to no single instrument, one table each, used by
every player that plays written notes - the romantic pianist (romantic.Score.perform) and the orchestra
(bandlib/scoring.Score -> orchestra.perform, bandlib/ensemble.py). Each player keeps its own VOCABULARY for a rule
(how it sounds on that instrument): a charge is velocity on the piano and the dynamics lane's level in an orchestral
section; a phrase arc is the body's timing + velocity on the piano and a continuous dynamics lane in a section.

    from agentsound import expressive as ex
    line = ex.melodic_charge(line, chord_at)               # lean on the 9th, the 7th, the #11 (KTH)
    line = ex.harmonic_charge(line, [(0, 'C'), (4, 'Db')], 'C major')   # louder into a remote chord
    ends = ex.punctuation(line)                            # the notes that close a melodic group (a micro-pause)
    xs = ex.correlated(n, rho=ex.KTH['rho'], rng=rng)      # AR(1) timing noise: a player drifts, it is no dice

KTH: the rule tables (docs/PIANIST_RULES.md, docs/ORCHESTRA_RULES.md: the source and the published range of every
number). Where a rule is already a player-independent function elsewhere, the table names it:
  charge        melodic and harmonic charge (Sundberg, Friberg & Fryden 1991; Friberg 1991) - here
  high_loud     velocity per semitone above the phrase mean (DM high loud, ~3 dB/octave) - humanize.touch(pitch=)
  phrase_arch   tempo and loudness rise together into the phrase peak (Todd 1992) - humanize.touch (velocity) and
                humanize.Body (timing); the orchestra draws it as a continuous dynamics lane (ensemble.DYNAMICS)
  final_ritard  the decelerating-motion curve v(x) = (1 + (w^q - 1) x)^(1/q) (Friberg & Sundberg 1999) -
                humanize.rit_curve (Body, song tempo lanes)
  punctuation   micro-pauses that close small melodic groups (Friberg, Bresin, Fryden & Sundberg 1998) - here
  rho           correlated timing: human timing fluctuations are long-range correlated (Hennig et al. 2011) - the
                lilt (tempo.LILT_RHO) and the orchestra's section timing (ensemble.ENSEMBLE['rho'])
"""

from __future__ import annotations

import math
import random

from .patterns import Clip, _vel
from .tempo import LILT_RHO
from .theory import ComposeError, Key

__all__ = ['KTH', 'CHARGE', 'HIGH_LOUD', 'PUNCTUATION', 'charge', 'melodic_charge', 'harmonic_charge',
           'punctuation', 'correlated']

_EPS = 1e-6

CHARGE = {
    'melodic': 0.6,             # velocity per unit of melodic charge (DM: +0.2 dB x charge at k = 1)
    'harmonic': 1.4,            # velocity x sqrt(harmonic charge) at a chord far from the key's tonic (DM)
    'pcs': {0: 0.0, 7: 1.0, 2: 2.0, 9: 3.0, 4: 4.0, 11: 5.0, 6: 6.0,          # the circle of fifths up ...
            5: 1.5, 10: 2.5, 3: 3.5, 8: 4.5, 1: 5.5},                        # ... and down (+0.5: the flat side)
}
"""Melodic charge (a melody note's distance from the chord root on the circle of fifths: the 9th, the 7th, the
#11 lean, the root and 5th rest) and harmonic charge (a chord's distance from the tonic: the level grows into a
remote chord and relaxes after it) - Sundberg / Friberg's KTH rules (Director Musices)."""

HIGH_LOUD = 0.8
"""DM high loud: velocity per semitone above / below a phrase's mean pitch (about 0.2 dB / semitone on the Salamander
grand, near DM's 3 dB / octave) - humanize.touch's default `pitch`."""

PUNCTUATION = {
    'ms': (25.0, 55.0),         # the micro-pause that closes a group (DM punctuation: some tens of ms)
    'long': 2.0,                # a note at least this many times longer than the one before ends a group ...
    'leap': 9,                  # ... and so does a note before a leap of this many semitones or more
    'min_beats': 0.75,          # (only notes of at least this length: a passing 8th closes nothing)
}
"""Punctuation (Friberg, Bresin, Fryden & Sundberg 1998): the melody falls into small groups, a player separates them
with a micro-pause on the group's last note. punctuation() finds the group ends (a long note after shorter ones, a
note before a wide leap); the player decides what the pause is (the orchestra: a bow lift / a tongued breath in a
legato line, ensemble.LEGATO)."""

KTH = {'charge': CHARGE, 'high_loud': HIGH_LOUD, 'punctuation': PUNCTUATION, 'rho': LILT_RHO,
       'phrase_arch': 'humanize.touch / humanize.Body', 'final_ritard': 'humanize.rit_curve'}
"""The shared rule tables (see the module docs: where each rule is applied)."""


def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        raise ComposeError(f"{what} = {x:g} is outside {lo:g}..{hi:g}")
    return float(x)


# ------------------------------------------------------------------------------------------------ charge

def charge(pc: int, root: int, table=None) -> float:
    """The charge of pitch class `pc` over `root`: its distance on the circle of fifths (CHARGE['pcs'])."""
    return (table or CHARGE['pcs'])[(int(pc) - int(root)) % 12]


def melodic_charge(clip: Clip, chord_at, *, vel: float | None = None, table=None) -> Clip:
    """Melodic charge (Sundberg / Friberg, Director Musices): the melody (the top note of every onset) leans on the
    notes far from the chord root on the circle of fifths - the 9th, the 6th / 13th, the major 7th, the #11, the b9
    (charge 2-6) - and rests on the root and the 5th (0-1): + `vel` velocity per unit of charge (CHARGE['melodic'];
    the charge table CHARGE['pcs']), the notes under the top moving with it. chord_at(beat) -> a chord symbol or a
    theory Chord or None (no chord: unchanged)."""
    from .theory import chord as _chord
    k = CHARGE['melodic'] if vel is None else _num(vel, 'melodic_charge vel', 0, 5)
    add: dict = {}
    for n in clip:
        key = round(n.start, 3)
        if key not in add or n.pitch > add[key][0]:
            add[key] = (n.pitch, n)
    bonus = {}
    for key, (p, n) in add.items():
        c = chord_at(n.start)
        if c is None:
            continue
        c = _chord(c) if isinstance(c, str) else c
        bonus[key] = k * charge(p % 12, c.root % 12, table)
    return Clip._raw([n._replace(vel=_vel(n.vel + bonus.get(round(n.start, 3), 0.0))) for n in clip], clip.length)


def harmonic_charge(clip: Clip, changes, key, *, vel: float | None = None, table=None, tension: float = 0.0) -> Clip:
    """Harmonic charge (Director Musices): the level grows toward a chord far from the key's tonic on the circle of
    fifths (IV, V: a little; ii, vi more; bII, bVI, the secondary dominants most) and relaxes after it: at every
    change the charge's sqrt x `vel` velocity (CHARGE['harmonic']), between two changes the level moves linearly from
    one to the next (a crescendo into the remote chord). changes = [(beat, chord symbol)], key a theory Key / name -
    or [(beat, chord symbol, key)] when the key moves (a modulating piece: each chord's charge from its own tonic;
    `key` is the default). tension: + this velocity at a tension chord - a tritone in it (a dominant 7th, a
    diminished chord) or its root a fifth above the next chord's (it resolves) - the swell into it, the release at
    its resolution (romantic.ACCOMPANIMENT['tension'] for the pianist's left hand)."""
    from .theory import chord as _chord
    k = CHARGE['harmonic'] if vel is None else _num(vel, 'harmonic_charge vel', 0, 10)
    tn = _num(tension, 'harmonic_charge tension', 0, 20)
    kk = Key(key) if not isinstance(key, Key) else key
    cs = []
    for ch in sorted(changes, key=lambda x: x[0]):
        c = _chord(ch[1]) if isinstance(ch[1], str) else ch[1]
        if c is not None:
            kc = kk if len(ch) < 3 or ch[2] is None else (ch[2] if isinstance(ch[2], Key) else Key(ch[2]))
            cs.append((float(ch[0]), c, kc))
    pts = []
    for i, (b, c, kc) in enumerate(cs):
        v = k * math.sqrt(charge(c.root % 12, kc.tonic % 12, table))
        if tn:
            pcs = c.pcs
            tri = any((p + 6) % 12 in pcs for p in pcs)
            res = i + 1 < len(cs) and (c.root - cs[i + 1][1].root) % 12 == 7
            v += tn if tri or res else 0.0
        pts.append((b, v))
    if not pts:
        return clip

    def at(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (b0, v0), (b1, v1) in zip(pts, pts[1:]):
            if t < b1:
                return v0 + (v1 - v0) * (t - b0) / max(_EPS, b1 - b0)
        return pts[-1][1]
    return Clip._raw([n._replace(vel=_vel(n.vel + at(n.start))) for n in clip], clip.length)


# ------------------------------------------------------------------------------------------------ punctuation

def punctuation(clip, *, long: float | None = None, leap: int | None = None, min_beats: float | None = None) -> set:
    """The group ends of a melody (Friberg et al. 1998, DM punctuation), as {(round(start, 4), pitch)} of the top note
    of every onset: a note at least `long` x the length of the note before it that is followed by a shorter one (a
    group's long last note), or a note before a leap of `leap`+ semitones; notes shorter than `min_beats` and a
    line's last note are never a group end. Defaults PUNCTUATION."""
    P = PUNCTUATION
    lg = P['long'] if long is None else _num(long, 'punctuation long', 1, 8)
    lp = P['leap'] if leap is None else int(leap)
    mb = P['min_beats'] if min_beats is None else _num(min_beats, 'punctuation min_beats', 0, 8)
    tops = []
    for n in sorted(clip, key=lambda n: (n.start, -n.pitch)):
        if tops and abs(n.start - tops[-1].start) < 0.02:
            continue
        tops.append(n)
    out = set()
    for i in range(1, len(tops) - 1):
        p, n, nx = tops[i - 1], tops[i], tops[i + 1]
        ioi = nx.start - n.start
        if ioi < mb - _EPS:
            continue
        prev_ioi = n.start - p.start
        next_ioi = tops[i + 2].start - nx.start if i + 2 < len(tops) else nx.dur
        if (ioi >= lg * prev_ioi - _EPS and next_ioi < ioi - _EPS) or abs(nx.pitch - n.pitch) >= lp:
            out.add((round(n.start, 4), n.pitch))
    return out


# ------------------------------------------------------------------------------------------------ correlated noise

def correlated(n: int, *, rho: float | None = None, rng: random.Random | None = None, seed=0) -> list:
    """n values of unit-variance AR(1) noise x_k = rho x_(k-1) + sqrt(1 - rho^2) N(0, 1): a player's timing drifts
    and comes back (rho ~ 0.6: Hennig et al. 2011; a player corrects 10-40 % of an asynchrony per note: Wing et al.
    2014), white per-note jitter reads as a machine. rho default KTH['rho']."""
    r = KTH['rho'] if rho is None else _num(rho, 'correlated rho', 0, 0.99)
    g = rng or random.Random(seed)
    s = math.sqrt(1.0 - r * r)
    x = g.gauss(0.0, 1.0)
    out = []
    for _ in range(int(n)):
        out.append(x)
        x = r * x + s * g.gauss(0.0, 1.0)
    return out
