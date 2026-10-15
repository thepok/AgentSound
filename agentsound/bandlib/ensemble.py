"""How an orchestra's sections play together: the performance rules orch.perform (and so orch.Score) applies to every
sustaining role - each a published finding written as a distribution or a budget in a table. docs/ORCHESTRA_RULES.md
has the source and the published range of every number; the rules the orchestra shares with the pianist (KTH charge,
high-loud, phrase arc, punctuation, correlated timing) live in agentsound.expressive - this module is the orchestra's
vocabulary for them (a charge or a phrase arc becomes the dynamics LANE, a punctuation a bow lift).

    orch.perform(b, 'violins1', line, verse)                      # every rule, the band's style
    orch.perform(b, 'flutes', line, verse, rules={'breath': {'budget_s': {'flutes': (5, 7)}}})   # one value changed
    sc = orch.Score(s, b, DYNAMICS, style='romantic')              # a style scales the rules (STYLES)

The tables (RULES: name -> table; `rules=` overrides single values, unknown names / keys are errors):
  ENSEMBLE    onset asynchrony between sections (Rasch 1979, 1988): a seat offset (the leader ahead, the low
              strings a little behind), a shared drift the sections follow (the leader's), each section's own
              correlated (AR(1)) deviation - strings looser than winds, sharp attacks tighter, slow tempi looser
  DYNAMICS    the dynamics lane: a phrase is one continuous curve through its notes' levels (hairpins, not
              steps), long notes swell (messa di voce) by their length, accents fall back
  BOWING      strings: down-bow / up-bow weight on detached notes, a bow change on a repeated note
  BREATH      winds and brass: a phrase-length budget per instrument, a breath gap at the best phrase point
  LEGATO      notes written connected overlap by the family's transition time (no gap, no re-attack), except at
              the end of a melodic group (punctuation) and on repeated notes
  ARTICULATE  short / spiccato / marcato from the sounding length (ms) and the tempo
  BRASS       entries after a rest: tongued (trumpets, trombones: a light accent) or blooming (horns)
  RELEASE     a held note before a rest: the sections let go a little apart, with a taper (no cut-off wall)
  VIBRATO     solo players: delayed onset, depth following the dynamics
  BALANCE     the melody over the accompaniment by a level budget (orch.Score)
  STYLES      'baroque' (terraced dynamics, little swell), 'classical', 'romantic' (wider arcs, swells), 'film'
"""

from __future__ import annotations

import math
import random

from .. import articulation as art
from .. import expressive as ex
from ..patterns import Clip, _vel, as_clip, seed_int
from ..theory import ComposeError

__all__ = ['ENSEMBLE', 'DYNAMICS', 'BOWING', 'BREATH', 'LEGATO', 'ARTICULATE', 'BRASS', 'RELEASE', 'VIBRATO',
           'BALANCE', 'STYLES', 'RULES', 'family', 'merged', 'style_of', 'articulate', 'connect', 'bow', 'breathe',
           'entries', 'timing', 'release', 'lane', 'vibrato_depth', 'db_of', 'level_of']

_EPS = 1e-6

# ------------------------------------------------------------------------------------------------ the rule tables

ENSEMBLE = {
    # each section's own onset deviation (SD, ms) at ref_bpm: Rasch's asynchronization 30-50 ms between two players
    # (an SD of ~21-35 ms per player); an orchestra with a conductor at the low end, winds / brass tighter
    'sd_ms': {'strings': 25.0, 'woodwinds': 18.0, 'brass': 18.0, 'horns': 21.0, 'choir': 22.0, 'struck': 10.0,
              'other': 16.0},
    'solo': 0.85,               # a solo player (a mono role) against a section of players
    'short': 0.7,               # sharp attacks (staccato, pizzicato, marcato, struck) synchronise tighter
    'ref_bpm': 90.0,            # slower music: looser (x (ref_bpm / bpm) ** tempo_exp, within tempo_clamp)
    'tempo_exp': 0.5,
    'tempo_clamp': (0.75, 1.3),
    'rho': ex.KTH['rho'],       # a section's deviation is correlated from onset to onset (AR(1)): it drifts
    'max_ms': 60.0,             # no onset further than this from the beat (the ensemble drift and the seat added)
    'drift_ms': 8.0,            # the leader's drift (SD, ms; AR(1) per beat): the shared part every section follows
    'follow': 0.7,              # ... by this share (the leader itself: 1)
    'leader': ('violins1', 'violin1'),
    # the seat: a section's mean offset (ms; - = ahead): the leader and the melody instruments a little ahead, the
    # low strings and the horns a little behind (Rasch 1979: the melody voice leads by a few ms)
    'seat_ms': {'violins1': -4.0, 'violin1': -4.0, 'flutes': -2.0, 'oboes': -2.0, 'trumpets': -2.0,
                'violins2': -1.0, 'violin2': -1.0, 'clarinets': 0.0, 'violas': 1.0, 'viola': 1.0, 'bassoons': 2.0,
                'trombones': 2.0, 'horns': 3.0, 'cellos': 3.0, 'cello': 3.0, 'low_brass': 4.0, 'basses': 5.0,
                'tuba': 5.0},
}
"""Onset asynchrony between sections (timing())."""

DYNAMICS = {
    'phrase_gap': 0.5,          # beats: a rest this long ends a phrase - the lane steps there, inside it glides
    'glide': True,              # inside a phrase the lane moves from note level to note level (False: steps)
    'swell_s': 1.2,             # a note sounding this long or longer swells (messa di voce) ...
    'swell_db': (1.5, 1.0, 6.0),    # ... by 1.5 dB + 1 dB per second beyond swell_s, at most 6 dB
    'swell_rel': 1.5,           # ... and at least this x the median length of its phrase's notes (a LONG note in
    #                             its context: a bar of half notes is a line, not a chain of swells) ...
    'swell_share': 0.7,         # ... with this probability (seeded per note: not every long note, not in step)
    'swell_peak': (0.35, 0.65), # the peak's place in the note (seeded)
    'swell_start': 0.6,         # it starts this share of the depth under the level and peaks (1 - this) over it
    'swell_end': 0.5,           # it ends this share of the depth under the level
    'accent_db': 3.0,           # a marcato / sforzando attack this much over the level, falling back in accent_ms
    'accent_ms': 180.0,
    'accent_rise': 8,           # an unmarked note is an accent only this much louder (velocity) than the one before
    #                             it (a loud note among loud notes is a level, not an accent: an ff tutti holds)
}
"""The dynamics lane per phrase (lane())."""

BOWING = {
    'weight': 4.0,              # velocity: a down-bow's attack this much heavier than an up-bow's (+-half)
    'max_beats': 1.0,           # detached notes up to this long alternate the bow
    'reset_beats': 1.0,         # after a rest this long the next stroke is a down-bow again
    'repeat_ms': (30.0, 55.0),  # a repeated note in a connected line: the bow changes (a gap) - DM repetition
    'stroke_s': 4.0,            # a solo player changes the bow after this much tied line (articulation.bow_changes)
    'change_ms': 40.0,
}
"""String bowing (bow())."""

BREATH = {
    # seconds of continuous playing per breath (seeded within the range; approx., from airflow / lung volume:
    # the oboe's small flow lasts longest, the flute's and the low brass's big flow shortest)
    'budget_s': {'flutes': (6.0, 9.0), 'oboes': (10.0, 14.0), 'clarinets': (9.0, 12.0), 'bassoons': (8.0, 11.0),
                 'horns': (7.0, 10.0), 'trumpets': (7.0, 10.0), 'trombones': (6.0, 9.0), 'low_brass': (5.0, 8.0),
                 'tuba': (5.0, 8.0)},
    'default': (7.0, 10.0),
    'loud': 0.8,                # at f and louder (velocity >= loud_vel) the budget shrinks by this factor
    'loud_vel': 95,
    'gap_ms': (150.0, 300.0),   # the breath: the note before it ends this much early (at most `share` of it) ...
    'held_gap_ms': (90.0, 160.0),   # ... a catch breath after a held note (>= held_beats): a quick lift
    'held_beats': 2.0,
    'jitter': 0.8,              # seeded per role: the sections do not all pick the same bar line
    'share': 0.4,
    'min_into': 0.45,           # a breath comes no earlier than this share of the budget ...
    'over': 1.3,                # ... and no later than this x the budget (else the line holds on: the section
    #                             staggers its breaths inside a held note)
    'taken_ms': 150.0,          # a written gap this long is a breath already
    'stagger': True,            # a chord (divisi / a2 / a3) breathes voice by voice: every other one per breath
}
"""Wind breathing (breathe())."""

LEGATO = {
    # how much a note written connected overlaps the next (ms, seeded within): the family's transition time - the
    # samples crossfade instead of leaving a gap or re-attacking
    'overlap_ms': {'strings': (40.0, 70.0), 'woodwinds': (15.0, 35.0), 'brass': (20.0, 40.0),
                   'horns': (25.0, 45.0), 'choir': (30.0, 60.0), 'other': (20.0, 40.0)},
    'max_gap': 0.03,            # a written gap of at most this share of the time to the next onset is connected
    'punctuate': True,          # a group end (expressive.punctuation) gets a micro-pause instead
}
"""Legato overlaps (connect())."""

ARTICULATE = {
    'short_ms': 260.0,          # a note sounding shorter than this (not tied) is a short articulation ...
    'short_beats': 0.5,         # ... and so is one of at most half a beat sounding shorter than short_max_ms
    'short_max_ms': 420.0,
    'spiccato_ioi_ms': 170.0,   # strings: shorts this close together bounce (spiccato, when the role has it)
    'accent_vel': 112,          # a short-ish note this loud is marcato
}
"""Articulation from the sounding length and the tempo (articulate())."""

BRASS = {
    'rest_beats': 1.0,          # an entry: the first note after this much rest
    'entry_vel': 6,             # trumpets, trombones, tuba: a tongued entry, a little accented (up to entry_top:
    'entry_top': 118,           # at ff the attack is already the loudest layer) ...
    'entry_db': 1.5,            # ... the level this much over the line's, falling back in entry_ms
    'entry_ms': 150.0,
    'horn_vel': -4,             # horns enter softer and bloom
    'horn_db': 1.5,             # ... from this much under the level, over horn_ms
    'horn_ms': 250.0,
}
"""Brass entries (entries())."""

RELEASE = {
    'min_beats': 1.5,           # a held note this long ...
    'rest_beats': 2.0,          # ... before this much rest (a fermata, a general pause, the end) is released:
    'sd_ms': 30.0,              # its end moves N(0, sd) (the sections let go a little apart), within max_ms
    'max_ms': 70.0,
    'taper_db': 3.0,            # the level falls this much over its last taper_ms (no cut-off wall)
    'taper_ms': 300.0,
}
"""Releases of held notes (release())."""

VIBRATO = {
    'delay_s': (0.2, 0.35),     # a straight tone first (seeded within)
    'grow_s': 0.45,             # the depth grows over this
    'rate_hz': 5.6,             # violin / cello vibrato 5.5-6.5 Hz
    'dynamics': (0.6, 0.7),     # depth x (a + b x the lane level 0..1): wider when louder
}
"""Solo players' vibrato (vibrato_depth(); orch.perform on mono roles)."""

BALANCE = {
    'db': 2.5,                  # the accompaniment sits at least this much under the melody line sounding with it
    'max_db': 4.0,              # ... pulled down by at most this much (the written balance mostly holds)
    'phrase_gap': 1.0,          # one pull per accompaniment phrase (notes closer than this many beats): its arc stays
    'share': 0.75,              # ... the pull that brings this share of the phrase's notes under the melody
}
"""Melody over accompaniment (orch.Score: lines vs chords / figures / pads): every accompaniment phrase is pulled
down as a whole (the shortfall of `share` of its notes) - a section plays its whole phrase softer, its own
hairpins kept."""

STYLES = {
    # terrace: hairpins become steps (terraced dynamics); swell / timing / vibrato / phrasing scale those rules
    'baroque': {'terrace': True, 'swell': 0.5, 'timing': 0.9, 'vibrato': 0.5, 'phrasing': 0.8},
    'classical': {'terrace': False, 'swell': 0.8, 'timing': 1.0, 'vibrato': 0.8, 'phrasing': 1.0},
    'romantic': {'terrace': False, 'swell': 1.2, 'timing': 1.1, 'vibrato': 1.1, 'phrasing': 1.2},
    'film': {'terrace': False, 'swell': 1.0, 'timing': 0.85, 'vibrato': 1.0, 'phrasing': 1.0},
}
"""Performance styles: terraced dynamics vs hairpins, how much swell / timing spread / vibrato / phrase arc."""

RULES = {'ensemble': ENSEMBLE, 'dynamics': DYNAMICS, 'bowing': BOWING, 'breath': BREATH, 'legato': LEGATO,
         'articulate': ARTICULATE, 'brass': BRASS, 'release': RELEASE, 'vibrato': VIBRATO, 'balance': BALANCE}


def merged(rules=None) -> dict:
    """The rule tables with `rules` ({table: {key: value}}) laid over a copy; unknown tables / keys are errors."""
    out = {k: dict(v) for k, v in RULES.items()}
    for name, over in (rules or {}).items():
        if name not in out:
            raise ComposeError(f"orchestra rules: unknown table {name!r}; tables: {', '.join(RULES)}")
        if not isinstance(over, dict):
            raise ComposeError(f"orchestra rules[{name!r}] must be a dict of values, got {over!r}")
        for k, v in over.items():
            if k not in out[name]:
                raise ComposeError(f"orchestra rules[{name!r}]: unknown key {k!r}; keys: {', '.join(out[name])}")
            out[name][k] = dict(out[name][k], **v) if isinstance(out[name][k], dict) and isinstance(v, dict) else v
    return out


def style_of(band, style=None) -> dict:
    """The STYLES entry of `style` (a name), else the band's (band.info['style'], 'film' for film_orchestra, else
    'classical')."""
    name = style or band.info.get('style') or ('film' if getattr(band, 'preset', '') == 'film_orchestra'
                                                else 'classical')
    if name not in STYLES:
        raise ComposeError(f"orchestra style {name!r}: use one of {', '.join(STYLES)}")
    return dict(STYLES[name], name=name)


# ------------------------------------------------------------------------------------------------ helpers

_FAMILY = (('woodwinds', ('flute', 'piccolo', 'oboe', 'english', 'cor_anglais', 'clarinet', 'bassoon',
                          'contrabassoon', 'winds', 'woodwind')),
           ('horns', ('horn',)),
           ('brass', ('trumpet', 'trombone', 'tuba', 'low_brass', 'brass', 'cornet', 'euphonium')),
           ('strings', ('violin', 'viola', 'cello', 'bass', 'contrabass', 'strings')),
           ('choir', ('choir', 'chorus', 'voices')))


def family(role: str, kind: str = 'sustain') -> str:
    """The family of a role by its name: strings, woodwinds, horns, brass, choir, struck (kind 'struck') or other."""
    if kind == 'struck':
        return 'struck'
    r = role.lower()
    for fam, words in _FAMILY:
        if any(r.startswith(w) or ('_' + w) in r for w in words):
            return fam
    return 'other'


def _wind(fam: str) -> bool:
    return fam in ('woodwinds', 'brass', 'horns')


def _bpm(tm, beat: float) -> float:
    return max(1.0, float(tm.bpm_at(beat)))


def _b(ms: float, tm, beat: float) -> float:
    """ms -> beats from `beat` (exact through tempo changes and fermatas: + later, - earlier)."""
    if not ms:
        return 0.0
    return max(0.0, tm.beat_at(max(0.0, tm.seconds_at(beat) + ms / 1000.0))) - beat


def _ms(beats: float, tm, beat: float) -> float:
    return beats * 60000.0 / _bpm(tm, beat)


def db_of(x: float) -> float:
    """The level (dB under full) of a dynamics lane value 0..1 on the orchestra's samplers (_DYN_CURVE: 16^v / 16
    up to velocity 112): ~27 dB from 0 to 0.88, flat above."""
    v = min(max(x, 0.0) * 127.0, 112.0) / 112.0
    return 20.0 * math.log10(max(1e-9, 16.0 ** v / 16.0))


def level_of(db: float) -> float:
    """The lane value of a level in dB (the inverse of db_of below 0.88)."""
    return max(0.0, (db / (20.0 * math.log10(16.0)) + 1.0) * 112.0 / 127.0)


def _shift_db(x: float, db: float) -> float:
    """A lane value moved by `db` decibels (above the curve's flat top, where every value sounds the same: up stays
    up, down goes from the top)."""
    top = 112.0 / 127.0
    if x >= top:
        return max(0.0, min(1.0, x if db >= 0 else level_of(db)))
    return max(0.0, min(1.0, level_of(db_of(x) + db)))


def _fit(x: float, up: float) -> float:
    """The level a shape that rises `up` dB over its note's level starts from: the note's level, or lower when the
    rise would pass the curve's flat top (an ff accent / swell is heard as the fall after it, not as more level)."""
    room = -db_of(x)
    return x if up <= room + 1e-9 else _shift_db(x, room - up)


def _onsets(ns) -> list:
    """[(start, [notes])] of notes starting together (within 1e-4 beats)."""
    out: list = []
    for n in sorted(ns, key=lambda n: (n.start, -n.pitch)):
        if out and abs(n.start - out[-1][0]) < 1e-4:
            out[-1][1].append(n)
        else:
            out.append((n.start, [n]))
    return out


def _short(n) -> bool:
    a = art.articulation_of(n)
    return art.detached(n) or (isinstance(a, str) and 'pizz' in a)


# ------------------------------------------------------------------------------------------------ articulation

def articulate(clip, tm, avail, fam: str, R: dict) -> Clip:
    """Mark notes without an articulation by their SOUNDING length (ARTICULATE): shorter than short_ms (or at most
    short_beats and shorter than short_max_ms) and not tied -> staccato (strings this close together -> spiccato),
    loud (>= accent_vel) and not long -> marcato, else sustain - from the articulations the role has (avail)."""
    A = R['articulate']
    c = as_clip(clip)
    s_name, a_name, l_name = art._pick(avail, 'short'), art._pick(avail, 'accent'), art._pick(avail, 'long')
    spic = next((x for x in avail if 'spic' in x.lower()), None)
    ns = sorted(c, key=lambda n: (n.start, n.pitch))
    starts = sorted({round(n.start, 6) for n in ns})
    out = []
    for n in ns:
        if art.articulation_of(n) is not None:
            out.append(n)
            continue
        nxt = next((s for s in starts if s > n.start + _EPS), None)
        tied = nxt is not None and n.start + n.dur > nxt + _EPS
        ms = _ms(n.dur, tm, n.start)
        short = not tied and (ms < A['short_ms'] or (n.dur <= A['short_beats'] + _EPS and ms < A['short_max_ms']))
        kind = None
        if short and s_name:
            ioi = _ms(nxt - n.start, tm, n.start) if nxt is not None else 1e9
            kind = spic if (fam == 'strings' and spic and ioi < A['spiccato_ioi_ms']) else s_name
        elif n.vel >= A['accent_vel'] and a_name and ms < 2.0 * A['short_max_ms']:
            kind = a_name
        elif l_name:
            kind = l_name
        out.append(art._mark(n, art=art._art_name(kind)) if kind else n)
    return Clip._raw(out, c.length)


# ------------------------------------------------------------------------------------------------ connecting

def connect(clip, tm, fam: str, R: dict, rng: random.Random) -> Clip:
    """Notes written connected (their end within LEGATO max_gap of the time to the next onset of the role) overlap
    the next onset by the family's transition time (overlap_ms, seeded per onset) - the sampled section crossfades
    instead of leaving a gap; a repeated pitch gets a bow change / tongue instead (BOWING repeat_ms, a gap) and a
    melodic group's end (expressive.punctuation) a micro-pause (PUNCTUATION ms). Detached notes are left alone."""
    L, B = R['legato'], R['bowing']
    c = as_clip(clip)
    ons = _onsets(c)
    if len(ons) < 2:
        return c
    lo, hi = L['overlap_ms'].get(fam, L['overlap_ms']['other'])
    groups = ex.punctuation(c) if L['punctuate'] else set()
    p_lo, p_hi = ex.PUNCTUATION['ms']
    r_lo, r_hi = B['repeat_ms']
    out = []
    for k, (t, ns) in enumerate(ons):
        if k + 1 >= len(ons):
            out += ns
            continue
        t2, nxt = ons[k + 1]
        ioi = t2 - t
        ov = lo + (hi - lo) * rng.random()
        pause = p_lo + (p_hi - p_lo) * rng.random()
        rep = r_lo + (r_hi - r_lo) * rng.random()
        nxt_p = {m.pitch for m in nxt}
        top = max(ns, key=lambda n: n.pitch)
        for n in ns:
            end = n.start + n.dur
            gap = t2 - end
            if _short(n) or any(_short(m) for m in nxt) or gap > L['max_gap'] * ioi + _EPS or \
                    end > t2 + 0.25 * ioi + _EPS:
                out.append(n)                     # detached, a rest, or held on under the next onset: as written
                continue
            if n.pitch in nxt_p:
                ms = -min(rep, 0.3 * _ms(ioi, tm, t))      # the same pitch again: a new stroke
            elif n is top and (round(top.start, 4), top.pitch) in groups:
                ms = -min(pause, 0.25 * _ms(ioi, tm, t))   # a group's last note: a bow lift / a breath of air
            else:
                ms = ov
            new_end = t2 + _b(ms, tm, t2)
            out.append(n._replace(dur=max(0.5 * n.dur, new_end - n.start)))
    return Clip._raw(out, c.length)


# ------------------------------------------------------------------------------------------------ bowing

def bow(clip, R: dict, bar_of=None, *, style: dict | None = None) -> Clip:
    """Strings: detached notes (up to BOWING max_beats, not tied) alternate down-bow / up-bow - the down-bow's
    attack `weight` velocity heavier than the up-bow's -, a rest of reset_beats (or a new bar after a rest) starts
    with a down-bow again (the rule of the down-bow). Chords take one stroke."""
    Bw = R['bowing']
    c = as_clip(clip)
    w = Bw['weight'] / 2.0
    ons = _onsets(c)
    out = []
    down, last_end = True, None
    for k, (t, ns) in enumerate(ons):
        nxt = ons[k + 1][0] if k + 1 < len(ons) else None
        dur = max(n.dur for n in ns)
        tied = nxt is not None and t + dur > nxt + _EPS
        if last_end is not None and t - last_end >= Bw['reset_beats'] - _EPS:
            down = True
        if dur <= Bw['max_beats'] + _EPS and not tied:
            out += [n._replace(vel=_vel(n.vel + (w if down else -w))) for n in ns]
            down = not down
        else:
            out += ns
            down = True                            # a long stroke: the next detached run starts fresh
        last_end = max(t + dur, last_end or 0.0)
    return Clip._raw(out, c.length)


# ------------------------------------------------------------------------------------------------ breathing

def breathe(clip, tm, role: str, R: dict, rng: random.Random, bar_of=None) -> tuple:
    """Winds and brass: a breath before the line has run longer than its budget (BREATH budget_s, seeded, x loud
    at f+). The breath goes to the best note boundary between min_into and over x the budget - a melodic group's end
    (expressive.punctuation), after a long note, before a bar line / half bar, before a leap -, never between a
    short pickup and its downbeat; the note(s) before it end gap_ms early - in a chord (a section's divisi) every
    other voice, the others at the next breath (stagger: the chord never gaps). A line that holds one note past the
    budget holds on (a section staggers its breaths). Returns (clip, [breath beats])."""
    Br = R['breath']
    c = as_clip(clip)
    ons = _onsets(c)
    if len(ons) < 2:
        return c, []
    lo_b, hi_b = Br['budget_s'].get(role, Br['default'])
    groups = ex.punctuation(c)
    ends = {}                                     # onset index -> its end (latest note end)
    for k, (t, ns) in enumerate(ons):
        ends[k] = max(n.start + n.dur for n in ns)
    cut: dict = {}                                # onset index -> beats to end early
    breaths = []
    sec = lambda b: tm.seconds_at(b)              # noqa: E731
    start = ons[0][0]
    budget = lo_b + (hi_b - lo_b) * rng.random()
    k = 1
    while k < len(ons):
        t = ons[k][0]
        gap_s = sec(t) - sec(ends[k - 1])
        if gap_s * 1000.0 >= Br['taken_ms']:
            start, budget = t, lo_b + (hi_b - lo_b) * rng.random()
            k += 1
            continue
        loud = max(n.vel for n in ons[k][1]) >= Br['loud_vel']
        B = budget * (Br['loud'] if loud else 1.0)
        if sec(ends[k]) - sec(start) <= B:
            k += 1
            continue
        # the line runs out of breath during onset k: choose a boundary j (between j-1 and j) in the window
        best, best_s = None, -1e9
        for j in range(1, len(ons)):
            tj = ons[j][0]
            if tj <= start + _EPS:
                continue
            into = sec(tj) - sec(start)
            if into < Br['min_into'] * B:
                continue
            if into > Br['over'] * B:
                break
            if ends[j - 1] > tj + _EPS and any(m.start + m.dur > tj + 0.25 for m in ons[j - 1][1]):
                continue                          # a note held on through the boundary: no breath there
            prev = ons[j - 1][1]
            top = max(prev, key=lambda n: n.pitch)
            d_prev = tj - ons[j - 1][0]
            sc = 0.0
            if (round(top.start, 4), top.pitch) in groups:
                sc += 2.0
            sc += min(1.0, d_prev)                # after a long note
            if bar_of is not None:
                ph = bar_of(tj)
                sc += 1.0 if ph < 0.02 else 0.5 if abs(ph - 0.5) < 0.02 else 0.0
            nx = max(ons[j][1], key=lambda n: n.pitch)
            if abs(nx.pitch - top.pitch) >= 5:
                sc += 0.5
            if d_prev <= 0.5 + _EPS and j + 1 < len(ons) and ons[j + 1][0] - tj > d_prev + _EPS:
                sc -= 1.5                         # a short note leading on: a pickup, keep it with its goal
            sc -= 0.15 * abs(into / B - 0.85)     # near the end of the breath, not too early
            sc += Br['jitter'] * rng.random()     # this section's own choice
            if sc > best_s:
                best, best_s = j, sc
        if best is None:
            k += 1                                # nothing in the window: a held note carries the line on
            continue
        tj = ons[best][0]
        prev_t = ons[best - 1][0]
        g_lo, g_hi = Br['held_gap_ms'] if tj - prev_t >= Br['held_beats'] - _EPS else Br['gap_ms']
        gap_b = -_b(-(g_lo + (g_hi - g_lo) * rng.random()), tm, tj)
        gap_b = min(gap_b, Br['share'] * (tj - prev_t))
        cut[best - 1] = gap_b
        breaths.append(tj)
        start, budget = tj, lo_b + (hi_b - lo_b) * rng.random()
        k = best + 1
    if not cut:
        return c, []
    out, turn = [], 0
    for k, (t, ns) in enumerate(ons):
        if k in cut:
            tj = ons[k + 1][0]
            for i, n in enumerate(sorted(ns, key=lambda m: m.pitch)):
                if Br['stagger'] and len(ns) > 1 and i % 2 != turn:
                    out.append(n)                 # a chord: every other voice breathes here, the rest at the next
                    continue
                end = min(n.start + n.dur, tj) - cut[k]
                out.append(n._replace(dur=max(0.3 * n.dur, end - n.start)))
            turn = 1 - turn if len(ns) > 1 else turn
        else:
            out += ns
    return Clip._raw(out, c.length), breaths


# ------------------------------------------------------------------------------------------------ brass entries

def entries(clip, fam: str, R: dict) -> tuple:
    """Brass: the first note after BRASS rest_beats of rest is an entry - trumpets / trombones / tuba tongue it (+
    entry_vel), horns enter softer (horn_vel) and bloom. Returns (clip, {(round(start, 4), pitch) of the entries})."""
    Bs = R['brass']
    if fam not in ('brass', 'horns'):
        return as_clip(clip), set()
    c = as_clip(clip)
    dv = Bs['horn_vel'] if fam == 'horns' else Bs['entry_vel']
    top = Bs['entry_top']
    out, keys, last_end = [], set(), None
    for t, ns in _onsets(c):
        if (last_end is None or t - last_end >= Bs['rest_beats'] - _EPS) and not any(_short(n) for n in ns):
            out += [n._replace(vel=_vel(n.vel + (min(dv, max(0, top - n.vel)) if dv > 0 else dv))) for n in ns]
            keys |= {(round(n.start, 4), n.pitch) for n in ns}
        else:
            out += ns
        last_end = max(last_end or 0.0, max(n.start + n.dur for n in ns))
    return Clip._raw(out, c.length), keys


# ------------------------------------------------------------------------------------------------ timing

def _drift(song, tm, n_beats: int, R: dict) -> list:
    """The leader's drift (ms) per beat: AR(1) at drift_ms, seeded by the song (the same for every section)."""
    E = R['ensemble']
    rng = random.Random(seed_int(getattr(song, 'seed', 0)) * 31 + 7)
    return [E['drift_ms'] * x for x in ex.correlated(max(2, n_beats + 2), rho=E['rho'], rng=rng)]


def timing(clip, tm, song, role: str, fam: str, R: dict, rng: random.Random, *, solo: bool = False,
           scale: float = 1.0) -> Clip:
    """The section's onsets as an ensemble plays them (ENSEMBLE): each onset (a chord: one stroke) moves by
    seat_ms[role] + follow x the leader's drift there (the leader: 1 x) + the section's own AR(1) deviation of
    sd_ms[family] (x solo, x short for sharp attacks, x the tempo factor, x scale), within max_ms. Ends stay put
    (a note tied into the next keeps its overlap with that note's new start)."""
    E = R['ensemble']
    c = as_clip(clip)
    ons = _onsets(c)
    if not ons:
        return c
    sd0 = E['sd_ms'].get(fam, E['sd_ms']['other']) * (E['solo'] if solo else 1.0) * scale
    beta = 1.0 if role in E['leader'] else E['follow']
    seat = E['seat_ms'].get(role, 0.0)
    xs = ex.correlated(len(ons), rho=E['rho'], rng=rng)
    drift = _drift(song, tm, int(ons[-1][0]) + 1, R)
    lo_c, hi_c = E['tempo_clamp']
    shift = {}
    for (t, ns), x in zip(ons, xs):
        bpm = _bpm(tm, t)
        f = min(hi_c, max(lo_c, (E['ref_bpm'] / bpm) ** E['tempo_exp']))
        sharp = all(_short(n) for n in ns) or fam == 'struck'
        sd = sd0 * f * (E['short'] if sharp else 1.0)
        i = max(0, int(t))
        u = t - i
        d = drift[min(i, len(drift) - 1)] * (1 - u) + drift[min(i + 1, len(drift) - 1)] * u
        ms = max(-E['max_ms'], min(E['max_ms'], seat + beta * d + sd * x))
        shift[round(t, 6)] = _b(ms, tm, t)
    starts = sorted(shift)
    pos = {k: i for i, k in enumerate(starts)}
    key_of = {id(n): round(t, 6) for t, ns in ons for n in ns}
    out = []
    for n in c:                                   # in the clip's order (a caller may map notes by index)
        key = key_of[id(n)]
        i = pos[key]
        nxt = starts[i + 1] if i + 1 < len(starts) else None
        s = max(0.0, n.start + shift[key])
        end = n.start + n.dur
        if nxt is not None and end > nxt + _EPS:              # tied into the next onset: keep the overlap
            end = max(end, max(0.0, nxt + shift[nxt]) + (end - nxt))
        out.append(n._replace(start=s, dur=max(end - s, min(n.dur, 0.02))))
    return Clip._raw(out, c.length)


# ------------------------------------------------------------------------------------------------ releases

def release(clip, tm, R: dict, rng: random.Random) -> tuple:
    """Held notes (RELEASE min_beats) before rest_beats of rest in the role (a fermata, a general pause, the end):
    the end moves N(0, sd_ms) within max_ms - the sections let go a little apart. Returns (clip, {(round(start, 4),
    pitch) of the released notes}) - lane() tapers them."""
    Rl = R['release']
    c = as_clip(clip)
    ons = _onsets(c)
    out, keys = [], set()
    for k, (t, ns) in enumerate(ons):
        nxt = ons[k + 1][0] if k + 1 < len(ons) else None
        end = max(n.start + n.dur for n in ns)
        if max(n.dur for n in ns) >= Rl['min_beats'] - _EPS and (nxt is None or nxt - end >= Rl['rest_beats'] - _EPS):
            ms = max(-Rl['max_ms'], min(Rl['max_ms'], rng.gauss(0.0, Rl['sd_ms'])))
            d = _b(ms, tm, end)
            for n in ns:
                if n.start + n.dur >= end - 0.25:
                    out.append(n._replace(dur=max(0.5 * n.dur, n.dur + d)))
                    keys.add((round(n.start, 4), n.pitch))
                else:
                    out.append(n)
        else:
            out += ns
    return Clip._raw(out, c.length), keys


# ------------------------------------------------------------------------------------------------ the lane

def lane(clip, tm, fam: str, R: dict, rng: random.Random, *, lo: float = 0.0, hi: float = 1.0,
         accent_vel: int = 112, follow=None, entry=frozenset(), released=frozenset(), style: dict | None = None,
         follow_step: float = 1.0, follow_min: float = 1.0) -> list:
    """The dynamics lane (points (beat, 0..1, curve)) of a played line (song beats), one shape per onset (a chord
    follows its top note): each note at its velocity's level (lo + (hi - lo) x vel / 127); inside a phrase (DYNAMICS
    phrase_gap) the lane moves continuously from note level to note level where the notes connect (a hairpin
    through a legato line; detached notes, a terracing style or glide off: steps), after a rest it starts at the
    note's level; notes sounding swell_s or longer swell (messa di voce, swell_db by length, x the style's swell),
    marcato / sforzando notes (vel >= accent_vel or a marcato mark) start accent_db over and fall back, brass entries
    (entry: BRASS) are tongued (trumpets ...) or bloom (horns), released notes (RELEASE) taper over their end; an
    accent / swell that would pass the sampler curve's flat top starts lower (_fit: heard as the fall after it). follow: a function beat -> level (a Score's
    dynamics map): a note of follow_min beats or more whose level moves inside it by more than 3 % follows it."""
    D, Bs, Rl = R['dynamics'], R['brass'], R['release']
    st = style or STYLES['classical']
    terrace = st.get('terrace', False) or not D['glide']
    c = as_clip(clip)
    firsts = [max(ns, key=lambda n: n.pitch) for _, ns in _onsets(c)]
    clamp = lambda x: round(min(1.0, max(0.0, x)), 5)   # noqa: E731
    pts: list = []
    prev_end = None
    med: dict = {}                                # the median length of each note's phrase (swell_rel)
    ph: list = []
    last = None
    for n in firsts:
        if not ph or n.start - last >= D['phrase_gap'] - _EPS:
            ph.append([])
        ph[-1].append(n)
        last = max(last or 0.0, n.start + n.dur)
    for g in ph:
        ds = sorted(m.dur for m in g)
        for m in g:                               # (a phrase of one or two notes: every long note may swell)
            med[id(m)] = ds[len(ds) // 2] if len(ds) >= 3 else 0.0
    for k, n in enumerate(firsts):
        nxt = firsts[k + 1] if k + 1 < len(firsts) else None
        cut = min(n.dur, nxt.start - n.start) if nxt is not None else n.dur
        b = lo + (hi - lo) * n.vel / 127.0
        in_phrase = prev_end is not None and n.start - prev_end < D['phrase_gap'] - _EPS
        pv = firsts[k - 1] if k else None             # glide only from a note that sounds into this one (legato);
        tied = pv is not None and pv.start + pv.dur >= n.start - R['legato']['max_gap'] * (n.start - pv.start) - _EPS
        first_curve = 'smooth' if (in_phrase and tied and not terrace) else 'step'   # detached notes step
        secs = tm.seconds_at(n.start + n.dur) - tm.seconds_at(n.start)
        a = art.articulation_of(n)
        key = (round(n.start, 4), n.pitch)
        keys: list = []
        if follow is not None and n.dur >= follow_min - _EPS:
            ref = follow(n.start) or 1e-9
            xs = sorted({min(n.dur, j * follow_step) for j in range(1, int(n.dur / follow_step) + 1)} | {n.dur})
            rs = [(x, follow(n.start + x) / ref) for x in xs]
            if max(abs(r - 1.0) for _, r in rs) > 0.03:
                keys = [(0.0, b, first_curve)] + [(x, lo + (hi - lo) * min(127.0, n.vel * r) / 127.0, 'linear')
                                                  for x, r in rs]
        if not keys:
            pv_vel = firsts[k - 1].vel if k else 0
            accent = (isinstance(a, str) and any(w in a.lower() for w in ('marc', 'sfz', 'accent'))) or \
                (n.vel >= accent_vel and secs < 1.0 and n.vel >= pv_vel + D['accent_rise'])
            if accent:
                t_ = _b(D['accent_ms'], tm, n.start)
                b = _fit(b, D['accent_db'])
                keys = [(0.0, _shift_db(b, D['accent_db']), 'step'), (min(t_, 0.6 * n.dur), b, 'smooth')]
            elif key in entry:
                t_ = min(0.6 * n.dur, _b(Bs['horn_ms' if fam == 'horns' else 'entry_ms'], tm, n.start))
                db = -Bs['horn_db'] if fam == 'horns' else Bs['entry_db']
                b = _fit(b, max(0.0, db))
                keys = [(0.0, _shift_db(b, db), 'step'), (t_, b, 'smooth')]
            else:
                keys = [(0.0, b, first_curve)]
            long_ = secs >= D['swell_s'] and n.dur >= D['swell_rel'] * med[id(n)] - _EPS
            if long_ and not accent and not _short(n) and rng.random() < D['swell_share']:
                d0, per, mx = D['swell_db']
                depth = min(mx, d0 + per * (secs - D['swell_s'])) * st.get('swell', 1.0)
                p_lo, p_hi = D['swell_peak']
                pk = p_lo + (p_hi - p_lo) * rng.random()
                if len(keys) == 1:                # (after an accent / entry the swell grows from its own level)
                    b = _fit(b, (1.0 - D['swell_start']) * depth)
                s0 = _shift_db(b, -D['swell_start'] * depth)
                if keys[0][2] == 'step' and len(keys) == 1:
                    keys = [(0.0, s0, 'step')]
                elif len(keys) == 1:              # in a phrase: arrive at the swell's start level
                    keys = [(0.0, s0, first_curve)]
                keys += [(pk * n.dur, _shift_db(b, (1.0 - D['swell_start']) * depth), 'smooth'),
                         (0.92 * n.dur, _shift_db(b, -D['swell_end'] * depth), 'smooth')]
        if key in released:
            tt = -_b(-Rl['taper_ms'], tm, n.start + n.dur)
            if n.dur > tt + 0.05:
                last = keys[-1]
                at_ = max(last[0] + 0.01, n.dur - tt)
                if at_ < n.dur:
                    lv = last[1]
                    keys = [p for p in keys if p[0] < at_ - 1e-6] + [(at_, lv, 'linear'),
                                                                     (n.dur, _shift_db(lv, -Rl['taper_db']), 'smooth')]
        prev = None
        for off, v, curve in keys:
            if off > cut + _EPS:
                if prev is not None:
                    x = (cut - prev[0]) / max(off - prev[0], 1e-9)
                    v = prev[1] + (v - prev[1]) * x
                    pts.append((n.start + cut, clamp(v), curve))
                break
            pts.append((n.start + off, clamp(v), curve))
            prev = (off, v)
        prev_end = max(prev_end or 0.0, n.start + n.dur) if in_phrase else n.start + n.dur
    return [(round(b, 6), v, cv) for b, v, cv in pts]


def vibrato_depth(base: float, level: float, R: dict, style: dict | None = None) -> float:
    """A solo player's vibrato depth (cents) at a lane level 0..1: base x (a + b x level) x the style's vibrato."""
    a, b = R['vibrato']['dynamics']
    return base * (a + b * max(0.0, min(1.0, level))) * (style or {}).get('vibrato', 1.0)
