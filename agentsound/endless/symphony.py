"""Endless SYMPHONY: a symphonic composer that thinks orchestrally - a short rhythmic MOTTO is the piece's engine,
stated boldly, then developed (sequence, fragmentation, inversion, augmentation / diminution, dialogue between the
choirs, a fugato, the motto in the bass, as an accompaniment rhythm, as a brass fanfare); RUNNING FIGURATION carries
the music forward (the Moldau principle: two flutes in a flowing stream, the strings take it over, the theme grows out
of it); a lyrical second theme in a contrasting key; a development that modulates and builds over a pedal to the
brass climax; a recapitulation and a coda (the motto triumphant or dissolving). HUMAN_FEEDBACK 2026-10-16 (the
orchestra-film pieces: "very meditative, hardly anything happens ... no life"); original material only - the
TECHNIQUES of the classics, never their themes.

    python -m agentsound endless orchestra-symphonic --count 4

The stages (docs/ORCHESTRA_ENDLESS.md "The symphonic composer"):
- compose(genre, seed, ...) -> Tune: the movement type (the genre's feels: allegro / vivace 6/8 / scherzo 3/4 /
  river 6/8 / andante), the mood, key, tempo, the set-level draws (plan['set']: the form layout, the motto's cell,
  the opening, the answer, the development's order, the second key) and the MATERIAL (material(): per block of the
  form its lines - the theme line, a dialogue's answers, a fugato's voices - and its chord chart, written melody
  first and harmonised by one shared chooser, harmonize()). Deterministic from the tune's fields.
- build_symphony(tune) -> Song: the blocks become an orchestration.OrchScore; per block the genre's {texture:
  weight} (plan['kinds'][kind]['tex'], the symphonic rows of orchestration.TEXTURES) is drawn (plan_blocks), the
  accompaniment the texture asks for is written by its slot's 'figure' (drive 8ths, the motto's rhythm in the
  strings, running figuration, a pumping / plucked bass, timpani in the motto's rhythm, rolls, a cymbal swell),
  orchestrated (orchestrate: the slots' entries / drop-outs inside a block) and played by orch.Score in the
  'romantic' style on the film_orchestra band (endless.orchestra.band: the same set-up as orchestra-film and the
  hand-written references) - sudden marks (subito p), sforzandi on the motto's long notes in the tutti, hairpins
  over the pedals, fermatas on the opening call.
The shared primitives are endless.orchestra's (_harmony: voice-led real parts, _bass, _counter, _ostinato, _colour,
band) and the composer's (_pick, _scale_step, set_draws, title, melody_issues): no parallel technique.

The song keeps s.symphony_log (every motto statement: block, beat, transform, function) for symphony_metrics()."""
from __future__ import annotations

import math
import random

from ..bandlib import orchestra as orch
from ..bandlib import orchestration as orc
from ..song import Song
from ..theory import ComposeError, Key, chord
from . import orchestra as eo

__all__ = ['compose', 'material', 'build_symphony', 'symphony_metrics', 'validate_plan', 'CELLS', 'KINDS',
           'harmonize', 'RECORDED']

_EPS = 1e-6

RECORDED = ('texture', 'lead', 'counter')
"""The orchestrator's draws kept in the Arrangement record (kind 'symphony'), as the orchestra's."""

CELLS = {
    # the motto's rhythm cells: (onset, duration, scale step over the anchor | 'L' the landing: the step drawn per piece from the note before it |
    # ('L', k) the landing + k) in beats of a 4/4 bar ('duple') or a 6/8 bar ('compound': 3 beats, pulses on 0 and
    # 1.5; the fast 3/4 scherzo plays it twice as slow - one compound bar = two 3/4 bars)
    'duple': {
        'knock': ((0, .5, 0), (.5, .5, 0), (1, .5, 0), (1.5, 2.5, 'L')),          # short-short-short-long
        'hammer': ((0, .5, 0), (.5, .5, 0), (1, .5, 1), (1.5, .5, 2), (2, 2, 'L')),
        'dotted': ((0, .75, 0), (.75, .25, 1), (1, .75, 2), (1.75, .25, 3), (2, 2, 'L')),
        'snap': ((0, .25, 0), (.25, .75, 1), (1, .25, 2), (1.25, .75, 3), (2, 2, 'L')),
        'call': ((0, .5, 0), (.5, .5, 0), (1, 1, 3), (2, .5, 2), (2.5, .5, 1), (3, 1, 'L')),   # a horn call
        'leap': ((0, .5, 0), (.5, 1.5, 5), (2, .5, 4), (2.5, .5, 3), (3, 1, 'L')),
        'turn': ((0, .25, 0), (.25, .25, 1), (.5, .25, 0), (.75, .25, -1), (1, 1, 'L'), (2, .5, ('L', 1)),
                 (2.5, .5, ('L', 0)), (3, 1, ('L', -1))),
        # (round o3, the melodist: mottos with a leap and a peak, memorable on their own - not repeated-note signals)
        'spring': ((0, .5, 0), (.5, .5, 2), (1, 1.5, 5), (2.5, .5, 4), (3, 1, 'L')),        # up to a held 6th
        'arch': ((0, 1, 0), (1, .5, 4), (1.5, .5, 5), (2, 1, 3), (3, 1, 'L')),             # a fifth, the peak, down
        'fanfare': ((0, .75, 0), (.75, .25, 0), (1, 1, 4), (2, .75, 7), (2.75, .25, 6), (3, 1, 'L')),
        'plunge': ((0, .5, 4), (.5, .5, 5), (1, 1, 0), (2, .5, 1), (2.5, .5, 2), (3, 1, 'L')),
    },
    'compound': {
        'gallop': ((0, 1, 0), (1, .5, 1), (1.5, 1, 2), (2.5, .5, 3), (3, 3, 'L')),
        'knock': ((0, .5, 0), (.5, .5, 0), (1, .5, 0), (1.5, 1.5, 'L')),
        'lilt': ((0, .5, 0), (.5, .5, 1), (1, .5, 2), (1.5, 1, 'L'), (2.5, .5, ('L', -1))),
        'hunt': ((0, 1, 0), (1, .5, 2), (1.5, 1, 4), (2.5, .5, 2), (3, 3, 'L')),   # a hunting call
        'dotted': ((0, .75, 0), (.75, .25, 1), (1, .5, 2), (1.5, 1.5, 'L')),
        'swing': ((0, 1.5, 0), (1.5, .5, 1), (2, .5, 2), (2.5, .5, 3), (3, 3, 'L')),
        'leap': ((0, 1, 0), (1, .5, 4), (1.5, 1, 5), (2.5, .5, 3), (3, 3, 'L')),
        'soar': ((0, .5, 0), (.5, .5, 4), (1, .5, 3), (1.5, 1, 7), (2.5, .5, 5), (3, 3, 'L')),
        'fall': ((0, 1, 5), (1, .5, 4), (1.5, 1, 1), (2.5, .5, 2), (3, 3, 'L')),
    },
}
"""The motto cells (the piece's draws: plan['set']['motto'] {cell: weight} per family, the landing plan['motto'])."""
CELLS_V = {
    # round o18b (SET_PLAN; genres.symphony_setplan adds them to CELLS): rhythm families the table lacked - the
    # set's mottos were mostly short-short-long
    # (five notes like the old cells: the development's head / kernel windows - dev_own - read them alike)
    'duple': {'synco': ((0, .5, 0), (.5, 1, 4), (1.5, .5, 3), (2, 1, 5), (3, 1, 'L')),     # the long off the beat
              'trochee': ((0, 1.5, 0), (1.5, .5, -1), (2, .75, 3), (2.75, .25, 2), (3, 1, 'L'))},   # long-short
    'compound': {'hemiola': ((0, 1, 0), (1, 1, 4), (2, 1, 3), (3, 1.5, 5), (4.5, 1.5, 'L')),  # quarters across
                 'sigh': ((0, 1.5, 4), (1.5, 1, 3), (2.5, .5, 0), (3, 1.5, 1), (4.5, 1.5, 'L')),  # long-long-short
                 'anacrusis': ((0, .5, -3), (.5, 2.5, 2), (3, 1, 1), (4, .5, 0), (4.5, 1.5, 'L'))},  # a pickup
}
MOTTO_FAMILIES = {
    'duple': {'knock': 'shorts', 'hammer': 'shorts', 'dotted': 'dotted', 'fanfare': 'dotted', 'snap': 'snap',
              'call': 'ssl', 'spring': 'ssl', 'plunge': 'ssl', 'leap': 'iamb', 'arch': 'dactyl', 'turn': 'run',
              'synco': 'syncope', 'trochee': 'trochee'},
    'compound': {'gallop': 'trochee', 'hunt': 'trochee', 'leap': 'trochee', 'fall': 'trochee', 'knock': 'shorts',
                 'lilt': 'shorts', 'soar': 'shorts', 'dotted': 'dotted', 'swing': 'dactyl', 'hemiola': 'hemiola',
                 'sigh': 'long', 'anacrusis': 'pickup'}}
"""The motto cells' rhythm families (SET_PLAN: the set's memory - genre.plan['set_groups'] - never repeats a family
within its 'motto' memory; 'ssl' the short-short-long the judges heard in every piece)."""
MOTTO_CHARACTER = {'repeats': 1, 'leap': 5, 'span': 12, 'scale': 2}
"""A motto with character (round o3, the melodist: 'no repeated-note signals'): at most `repeats` repeated notes in a
row, a leap of `leap` semitones or more, one highest note, within `span` semitones (motto_character) - compose()
takes the next landing, then the next cell of the family, until the motto has it. Round o12 (o11's judges: "themes
without profile", WBTS 7-22 "G-A-B-C", FUQW 4-11 "a scale fragment"): at most `scale` steps in a row one way - a head
that climbs a scale (C-D-E-F: the dotted / snap / gallop / swing cells) is no kernel; the next cell is drawn by the
set's weights (a seeded order, not always the first of the table)."""

LYRIC = {
    # the cantilena's rhythm per bar (onsets, durations), the cadence bars' cells apart
    'duple': {'body': (((0, 2), (2, 1), (3, 1)), ((0, 3), (3, 1)), ((0, 1.5), (1.5, .5), (2, 2)),
                       ((0, 1), (1, 1), (2, 2)), ((0, 2), (2, 2)), ((0, 1.5), (1.5, .5), (2, 1), (3, 1)),
                       # (round o4: livelier cells - the second theme's own rhythm)
                       ((0, 1), (1, .5), (1.5, .5), (2, 1.5), (3.5, .5)), ((0, .5), (.5, .5), (1, 1.5), (2.5, .5),
                                                                         (3, 1)),
                       ((0, 1.5), (1.5, .5), (2, .5), (2.5, .5), (3, 1)), ((0, 1), (1, 1.5), (2.5, .5), (3, 1))),
              'half': (((0, 3), (3, 1)), ((0, 2), (2, 2)), ((0, 1), (1, .5), (1.5, .5), (2, 2))),
              'end': (((0, 4),), ((0, 3),))},
    'compound': {'body': (((0, 1.5), (1.5, 1.5)), ((0, 1), (1, .5), (1.5, 1.5)), ((0, 1.5), (1.5, 1), (2.5, .5)),
                          ((0, .5), (.5, .5), (1, .5), (1.5, 1.5)), ((0, 2), (2, .5), (2.5, .5)),
                          ((0, 1), (1, .5), (1.5, .5), (2, .5), (2.5, .5)), ((0, .5), (.5, 1), (1.5, 1), (2.5, .5)),
                          ((0, 1.5), (1.5, .5), (2, .5), (2.5, .5))),
                 'half': (((0, 3),), ((0, 1.5), (1.5, 1.5)), ((0, 1), (1, .5), (1.5, 1.5))), 'end': (((0, 3),),)},
    'leap': (3, 4, 5),
}
"""The lyrical theme's rhythm cells per bar (body / the antecedent's half cadence / the end); 'leap' the head's leap
(scale steps: a 4th, 5th, 6th - round o4)."""


DANCE = {
    # the scherzo's tune (Writer.dance, round o5): cells per 3/4 bar of the song (onset, duration in song beats)
    'idea': (((0, 1), (1, 1), (2, 1)), ((0, 1.5), (1.5, .5), (2, 1)), ((0, .5), (.5, .5), (1, 1), (2, 1)),
             ((0, 1), (1, .5), (1.5, .5), (2, 1)), ((0, .75), (.75, .25), (1, 1), (2, 1))),
    'land': (((0, 2), (2, 1)), ((0, 1), (1, 2)), ((0, 1), (2, 1)), ((0, 2.5),)),
    'run': (((0, .5), (.5, .5), (1, .5), (1.5, .5), (2, 1)), ((0, 1), (1, .5), (1.5, .5), (2, .5), (2.5, .5)),
            ((0, .5), (.5, .5), (1, 1), (2, .5), (2.5, .5))),
    'end': (((0, 2),), ((0, 1), (1, 1)), ((0, 1.5),)),
    # the scherzo's lyrical themes (the trio, the second theme) per 3/4 bar - a waltz's cells, every fourth bar held
    'lyric': (((0, 2), (2, 1)), ((0, 3),), ((0, 1), (1, 1), (2, 1)), ((0, 1), (1, 2)), ((0, 1.5), (1.5, .5), (2, 1)),
              ((0, 2), (2, .5), (2.5, .5))),
}
"""The scherzo theme's rhythm cells (song beats in a 3/4 bar): the basic idea's lively first bar ('idea', 3+ notes),
its landing bar ('land': a held note on the downbeat or on two - the accent - and a pickup), the cadence's running
bar ('run') and the crisp end ('end': the goal short, then the rest); one of each drawn per piece."""


DANCE_FILL = 'neighbour'
"""Round o12 (o11's judges, WBTS 7-22: "a step-scale head, G-A-B-C"): the scherzo tune's notes past the motto's go in
as a neighbour turning away before its narrowest step (the leap kept) - 'passing' filled the widest leap by step."""
DANCE_VARY = {'answer': True, 'invert': True, 'idea': True, 'return': ('dot', 'reharm')}
"""The scherzo tune's restatements varied (round o8 - o7's judges: "XGPD repeats its cell in almost every bar", "the
returns nearly literal"): 'answer' the consequent's answer on another idea cell, 'invert' every second bar of the
fragmentation the head inverted on that cell (the sequence goes on up); the restatement (t1b) is always dotted and the
climax's dance (APEX_SCHERZO 'combine') answers inverted over its new harmony. 'return' (round o10 - o9's judges, EYPC
9-28: "the scherzo theme restated nearly literally"): the restatement's vary - dotted and on the other idea / landing
cells over the submediant ('reharm')."""


def stretch(sk: tuple, bars: int) -> tuple:
    """A skeleton for `bars` bars (round o4: phrases of 6 / 10 / 12 bars): under 8 the first bars and the home; over 8
    the consequent extended before its cadence by (the submediant - a deceptive cadence -, the approach again) pairs."""
    if bars < 8:
        return tuple(sk[:bars - 1]) + (sk[-1],)
    ext = []
    while len(ext) < bars - 8:
        ext += [6, sk[6]]
    return tuple(sk[:7]) + tuple(ext[:bars - 8]) + (sk[7],)

SKELETONS = {
    # the cantilena's structural degree per bar (8 bars: an antecedent to a half cadence, the consequent home; the
    # high point in bar 6)
    'major': ((3, 5, 4, 2, 3, 6, 5, 1), (5, 8, 7, 5, 6, 9, 7, 8), (1, 3, 5, 5, 6, 8, 7, 8), (3, 4, 5, 2, 3, 6, 4, 1),
              (5, 6, 5, 2, 5, 8, 7, 8), (8, 7, 6, 5, 6, 10, 9, 8)),
    'minor': ((5, 3, 4, 2, 5, 8, 7, 8), (1, 3, 4, 5, 6, 8, 7, 8), (3, 5, 4, 2, 3, 6, 2, 1), (5, 6, 5, 2, 3, 6, 4, 1),
              (8, 7, 6, 5, 6, 9, 7, 8)),
}

SKELETON = {'start': {1: 1.0, 3: 1.0, 5: 1.0}, 'move': {1: 1.0, 2: 1.0, -1: 0.8, 3: 0.6, -2: 0.5},
            'half': (2, 5, 7), 'again': {0: 1.0, 2: 0.6, -2: 0.4}, 'lift': {1: 1.0, 2: 0.8},
            'approach': (2, 4, 5, 7), 'home': (1, 8)}
"""The second theme's skeleton drawn per piece (skeleton(); round o3 - six fixed SKELETONS gave two pieces of a set
one tune): the start degree, the first bars' moves, the antecedent's half cadence (a tone of V), the consequent's
start (the start again, or a third away), the lift to the high point (bar 6), the cadence's approach and the home."""


def skeleton(rng) -> tuple:
    """An 8-bar skeleton of structural degrees (SKELETON): bars 1-3 from the start by drawn moves, bar 4 the half
    cadence nearest, bar 5 the consequent's start, bar 6 the high point over all, bar 7 the approach, bar 8 home."""
    deg = [_pick(rng, SKELETON['start'])]
    for _ in range(2):
        deg.append(min(8, max(1, deg[-1] + _pick(rng, SKELETON['move']))))
    deg.append(min(SKELETON['half'], key=lambda x: (abs(x - deg[-1]), x)))
    deg.append(min(8, max(1, deg[0] + _pick(rng, SKELETON['again']))))
    deg.append(max(deg) + _pick(rng, SKELETON['lift']))
    deg.append(min(SKELETON['approach'], key=lambda x: (abs(x - (deg[-1] - 2)), x)))
    deg.append(min(SKELETON['home'], key=lambda x: (abs(x - deg[-1]), x)))
    return tuple(deg)


_ROMANS = {'major': ('I', 'ii', 'iii', 'IV', 'V', 'vi', 'V7'),
           'minor': ('i', 'ii°', 'III', 'iv', 'V', 'VI', 'VII', 'V7')}
_DEG = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7}
NEXT = {1: {4: 1.0, 5: 1.0, 6: 0.8, 2: 0.7, 3: 0.3, 1: 0.35, 7: 0.3},
        2: {5: 1.3, 7: 0.3, 1: 0.2, 4: 0.3, 2: 0.3},
        3: {6: 1.0, 4: 0.8, 2: 0.3},
        4: {5: 1.0, 1: 0.8, 2: 0.7, 4: 0.3, 7: 0.3},
        5: {1: 1.4, 6: 0.6, 4: 0.2, 5: 0.35},
        6: {2: 1.0, 4: 1.0, 5: 0.6, 3: 0.3, 7: 0.4},
        7: {1: 1.0, 3: 0.8, 5: 0.3}}
"""The chord chooser's progression weights {root degree: {next root degree: weight}} (functional harmony)."""
_PRIOR = {'iii': -0.6, 'III': -0.2, 'VII': -0.3, 'ii°': -0.4, 'V7': -0.1}

KINDS = ('intro', 'mist', 'source', 't1', 't1b', 'trans', 't2', 't2b', 'close', 'river', 'episode',
         'dev_dialogue', 'dev_fugato', 'retrans', 'recap', 'recap2', 'coda', 'coda_soft', 'end', 'end_soft', 'slow',
         'solo', 'refrain', 'trio', 'var')
"""The block kinds the composer writes (plan['layouts'] names blocks of these kinds; plan['kinds'] their data). A
layout's 'intro' plays the piece's opening draw (plan['set']['intro']: 'call' -> 'intro', 'mist', 'source'), its
'coda' / 'end' the mood's coda ('triumph' -> 'coda' / 'end', 'dissolve' -> 'coda_soft' / 'end_soft'); 'slow' the
slow introduction (plan['set']['slow'], SLOW)."""
KIND_KEYS = {'tex', 'dyn', 'peak', 'sf', 'level'}
THEME_NEEDS = {'t1': 'theme', 't1b': 'theme', 'recap': 'theme', 'close': 'theme', 'episode': 'theme',
               't2': 'theme', 't2b': 'theme', 'recap2': 'theme', 'river': 'theme', 'trans': 'theme',
               'retrans': 'theme', 'coda': 'theme', 'coda_soft': 'theme', 'intro': 'theme', 'mist': 'theme',
               'source': None, 'dev_dialogue': 'theme', 'dev_fugato': 'voice', 'end': 'theme', 'end_soft': 'theme',
               'slow': 'theme', 'solo': 'theme', 'refrain': 'theme', 'trio': 'theme', 'var': 'theme'}
"""What each kind writes for its texture to seat: 'theme' (a melody line - or, by the texture's 'theme', the bass),
'voice' (a fugato's voices), None (the accompaniment only)."""


# ------------------------------------------------------------------------------------------------ pitch helpers

def _pick(rng, weights):
    from .composer import _pick as p
    return p(rng, weights)


def _step(p: int, n: int, pcs) -> int:
    from .composer import _scale_step
    return _scale_step(p, n, pcs) if n else p


def _cpcs(sym) -> set:
    c = chord(sym)
    return {(c.root + i) % 12 for i in c.intervals}


def pcs_of(key: str, sym: str | None = None) -> set:
    """The scale to step in: the key's; in minor over a chord holding the leading tone (V, V7, vii°) the harmonic
    minor (the raised 7th for the natural one)."""
    K = Key(key)
    pcs = set(K.pcs)
    if K.minorish and sym is not None:
        lead = (K.tonic + 11) % 12
        if lead in _cpcs(sym):
            pcs.discard((K.tonic + 10) % 12)
            pcs.add(lead)
    return pcs


def _near(pcs, centre: float, lo: int = 0, hi: int = 127) -> int:
    c = [q for q in range(max(lo, int(centre) - 12), min(hi, int(centre) + 13) + 1) if q % 12 in pcs]
    if not c:
        c = [q for q in range(lo, hi + 1) if q % 12 in pcs]
    return min(c, key=lambda q: (abs(q - centre), q))


def _member(sym: str, member: str) -> int:
    c = chord(sym)
    iv = {'root': 0, 'third': next((i for i in c.intervals if i in (3, 4)), 4),
          'fifth': next((i for i in c.intervals if i in (6, 7, 8)), 7)}[member]
    return (c.root + iv) % 12


def _roman(key: str, rn: str) -> str:
    return Key(key).chord(rn).symbol


def _deg(rn: str) -> int:
    r = rn.rstrip('7°ø+').lower()
    return _DEG.get(r, 1)


def _transpose_key(key: str, semis: int, mode: str | None = None) -> str:
    K = Key(key)
    from ..theory import _spell
    root = _spell((K.tonic + semis) % 12, (mode or K.mode) != 'major')
    return f"{root} {mode or K.mode}"


# ------------------------------------------------------------------------------------------ the chromatic vocabulary

_MAJOR_SC = (0, 2, 4, 5, 7, 9, 11)
CHROMA = {
    # rn: 'tones' (scale degree, alteration against the tonic's MAJOR scale) in the chord's root order, 'bass' the
    # tone in the bass, 'to' the chords it resolves to, 'tend' {tone index: +1 rises / -1 falls by step into the
    # resolution, -2 falls by step or stays a common tone (a seventh)}, 'deg' the root degree the progression weights
    # (NEXT) read it as, 'major' only in a major key
    'V7/V': {'tones': ((2, 0), (4, 1), (6, 0), (1, 0)), 'bass': 0, 'to': ('V', 'V7', 'cad64'), 'tend': {1: 1, 3: -2},
             'deg': 2},
    'vii°7/V': {'tones': ((4, 1), (6, 0), (1, 0), (3, -1)), 'bass': 0, 'to': ('V', 'V7', 'cad64'),
                'tend': {0: 1, 3: -2}, 'deg': 2},
    'V7/IV': {'tones': ((1, 0), (3, 0), (5, 0), (7, -1)), 'bass': 0, 'to': ('IV',), 'tend': {1: 1, 3: -2}, 'deg': 1},
    'V7/ii': {'tones': ((6, 0), (1, 1), (3, 0), (5, 0)), 'bass': 0, 'to': ('ii',), 'tend': {1: 1, 3: -2}, 'deg': 6,
              'major': True},
    'V7/vi': {'tones': ((3, 0), (5, 1), (7, 0), (2, 0)), 'bass': 0, 'to': ('vi',), 'tend': {1: 1, 3: -2}, 'deg': 3,
              'major': True},
    'N6': {'tones': ((2, -1), (4, 0), (6, -1)), 'bass': 1, 'to': ('V', 'V7', 'cad64'), 'tend': {0: -1}, 'deg': 2},
    'It6': {'tones': ((6, -1), (1, 0), (4, 1)), 'bass': 0, 'to': ('V', 'V7'), 'tend': {0: -1, 2: 1}, 'deg': 2},
    'Fr6': {'tones': ((6, -1), (1, 0), (2, 0), (4, 1)), 'bass': 0, 'to': ('V', 'V7'), 'tend': {0: -1, 3: 1}, 'deg': 2},
    'Ger6': {'tones': ((6, -1), (1, 0), (3, -1), (4, 1)), 'bass': 0, 'to': ('cad64',), 'tend': {0: -1, 3: 1},
             'deg': 2},
    'bVI': {'tones': ((6, -1), (1, 0), (3, -1)), 'bass': 0, 'to': ('IV', 'ii', 'V', 'V7', 'cad64', 'N6', 'Ger6'),
            'tend': {}, 'deg': 6, 'major': True},                 # (mixture; V - bVI the deceptive cadence)
    'mix_iv': {'tones': ((4, 0), (6, -1), (1, 0)), 'bass': 0, 'to': ('V', 'V7', 'cad64', 'I'), 'tend': {}, 'deg': 4,
               'major': True},                                    # (mixture: the minor subdominant in major)
}
"""The chromatic vocabulary (the code review's A2 step 1, songs/_endless_orchestra/out/code_review/REPORT.md): applied
dominants (V7/x, vii°7/V), the Neapolitan sixth, the augmented sixths (Italian / French / German), mixture in major
(bVI, mix_iv: the minor iv) and - with bVI after V - the deceptive cadence (CHROMA names never collide with
_ROMANS'). harmonize() takes them as candidates (CHROMA_WEIGHTS: 0, so off by default - bit-identical) and as
function pins; realise() voices one into its resolution (the tendency tones by step: the augmented sixth's b6 down and
#4 up to the dominant, the Neapolitan's b2 down, the applied leading tone up and its seventh down; no parallel fifths /
octaves; the tendency tones never doubled)."""
CHROMA_WEIGHTS = {rn: 0.0 for rn in CHROMA}
"""The chooser's weight per chromatic candidate in EVERY segment (0 = not a candidate: the default, bit-identical);
harmonize(chroma=) gives a call's segments their own."""
CHROMA_CADENCE = None
"""Off (None, the default: bit-identical) or {'recap': bool, 'final': bool, 'bars': n}: the chromatic predominant
(CHROMA_PRE, chosen by harmonize() among the vocabulary that resolves to the cadence's next chord) before the return's
dominant pedal (Writer.retrans - the pedal frame gets 'bars' more bars first: form_rows) and before the final cadence's
approach (the end block), the last 'bars' bars before each two chords a bar (the harmonic rhythm accelerating into the
cadence: tonic / predominant, predominant, the chromatic chord); the harmony / inner parts voice it by realise()
(_chroma_voice)."""
CHROMA_CADENCE_ON = {'recap': True, 'final': True, 'bars': 2}
"""The CHROMA_CADENCE setting a paired round switches on (symphony.CHROMA_CADENCE = dict(CHROMA_CADENCE_ON))."""
CHROMA_PRE = {'cad64': ('Ger6', 'N6', 'vii°7/V'), 'V': ('It6', 'Fr6', 'N6', 'vii°7/V', 'V7/V'),
              'V7': ('It6', 'Fr6', 'N6', 'vii°7/V', 'V7/V'), 'IV': ('V7/IV',)}
"""The chromatic predominants CHROMA_CADENCE offers per next chord (the cadence's: the dominant pedal's V, the final
approach's cadential six-four / V7 / IV)."""
END_CHROMA = {'cad64': 'cad64', 'V': 'V7', 'echo': 'V7', 'pre': 'IV', 'IV': 'IV'}
"""The final approach's first chord per ENDING_CADENCE / SOFT_ENDINGS plan (the chromatic predominant's resolution;
'pedal' - IV over the tonic pedal - takes none)."""
PREDOM = {'major': ('ii', 'IV', 'vi'), 'minor': ('ii°', 'iv', 'VI')}
"""The diatonic predominants (the accelerated bars' middle chords)."""


def _mode_rn(rn: str, minor: bool) -> str:
    """A major-case target roman in the key's mode (CHROMA 'to': IV -> iv, ii -> ii°, vi -> VI, I -> i in minor)."""
    return {'IV': 'iv', 'ii': 'ii°', 'vi': 'VI', 'I': 'i'}.get(rn, rn) if minor else rn


def chroma_fits(key: str, rn: str) -> bool:
    """A CHROMA chord exists in the key: major / minor keys only (no church modes), 'major' entries in major only."""
    K = Key(key)
    if K.mode not in ('major', 'minor') or rn not in CHROMA:
        return False
    return not (CHROMA[rn].get('major') and K.minorish)


def _chroma_pc(key: str, tone) -> int:
    deg, acc = tone
    return (Key(key).tonic + _MAJOR_SC[deg - 1] + acc) % 12


def chroma_spell(key: str, rn: str) -> list:
    """The chord's note names in its root order, spelled by degree (Ger6 in C: Ab C Eb F#, never Gb)."""
    from ..theory import spell_above
    K = Key(key)
    return [spell_above(K.tonic_name, (_chroma_pc(key, t) - K.tonic) % 12, t[0] - 1) for t in CHROMA[rn]['tones']]


_CHROMA_QUALITY = {(0, 4, 7): '', (0, 3, 7): 'm', (0, 4, 7, 10): '7', (0, 4, 10): '7no5', (0, 4, 6, 10): '7b5',
                   (0, 3, 6, 9): 'dim7', (0, 3, 6): 'dim'}


def chroma_symbol(key: str, rn: str) -> str:
    """The chart symbol of a CHROMA chord (or 'cad64': the tonic over the dominant): root + quality over the bass (Ger6
    in C 'Ab7', It6 'Ab7no5', Fr6 'Ab7b5', N6 'Db/F', vii°7/V 'F#dim7')."""
    K = Key(key)
    if rn == 'cad64':
        return _roman(key, 'i' if K.minorish else 'I') + '/' + chord(_roman(key, 'V')).root_name
    C = CHROMA[rn]
    names = chroma_spell(key, rn)
    pcs = [_chroma_pc(key, t) for t in C['tones']]
    q = _CHROMA_QUALITY[tuple(sorted((p - pcs[0]) % 12 for p in pcs))]
    return names[0] + q + (f"/{names[C['bass']]}" if C['bass'] else '')


def chroma_targets(key: str, rn: str) -> tuple:
    """The chords (romans in the key's mode, 'cad64') a CHROMA chord resolves to."""
    minor = Key(key).minorish
    return tuple(_mode_rn(x, minor) for x in CHROMA[rn]['to'])


def _target_tones(key: str, rn: str) -> tuple:
    """(bass pc, the chord's pcs, its third's pc, its root pc) of a resolution chord ('cad64', a roman, a CHROMA)."""
    if rn in CHROMA:
        C = CHROMA[rn]
        pcs = [_chroma_pc(key, t) for t in C['tones']]
        return pcs[C['bass']], set(pcs), pcs[1 % len(pcs)], pcs[0]
    sym = chroma_symbol(key, rn) if rn == 'cad64' else _roman(key, rn)
    c = chord(sym)
    pcs = {(c.root + i) % 12 for i in c.intervals}
    third = (c.root + next((i for i in c.intervals if i in (3, 4)), 4)) % 12
    if rn == 'cad64':                                     # (the six-four: the tonic's third and root over the fifth)
        return c.bass % 12, pcs, third, c.root % 12
    return c.bass_pc % 12, pcs, third, c.root % 12


def _parallel(a0, a1, b0, b1) -> bool:
    """Two voices a0 -> a1, b0 -> b1 in parallel (or hidden-by-contrary none: both moving) fifths / octaves."""
    if a0 == a1 or b0 == b1:
        return False
    i0, i1 = (a0 - b0) % 12, (a1 - b1) % 12
    return i0 == i1 and i0 in (0, 7) and (a1 - a0 > 0) == (b1 - b0 > 0)


def realise(key: str, rn: str, nxt: str, n: int = 3, lo: int = 53, hi: int = 79, cap: int | None = None,
            centre: float | None = None, bass: int | None = None):
    """A CHROMA chord voiced into its resolution `nxt` (one of chroma_targets): ((bass, [n upper voices low-high]),
    (bass, [the same voices resolved])) in MIDI, or None when no voicing satisfies the rules: every tendency tone
    (CHROMA 'tend') moves by step (1-2 semitones) its way into a tone of nxt, the others hold a common tone or move
    to the nearest; no parallel fifths / octaves between any two voices (the bass included); no tendency tone doubled;
    the chord's tones all present when n + 1 voices can hold them; nxt with its third; the upper voices in lo..hi,
    under `cap` (the tune's lowest note), an octave at most apart, around `centre`; bass: the chord's bass near it
    (default 43)."""
    from itertools import product
    if not chroma_fits(key, rn) or nxt not in chroma_targets(key, rn):
        return None
    C = CHROMA[rn]
    pcs = [_chroma_pc(key, t) for t in C['tones']]
    tend = {pcs[i]: d for i, d in C['tend'].items()}
    bpc = pcs[C['bass']]
    b0 = _near({bpc}, 43 if bass is None else bass, 28, 55)
    nb_pc, npcs, nthird, nroot = _target_tones(key, nxt)
    b1 = min((q for q in range(b0 - 7, b0 + 8) if q % 12 == nb_pc), key=lambda q: (abs(q - b0), q))
    top = min(hi, (cap - 1) if cap is not None else hi)
    centre = (lo + top) / 2.0 if centre is None else centre
    pool = [q for q in range(lo, top + 1) if q % 12 in pcs]
    need = set(pcs) if n + 1 >= len(pcs) else set(tend) | ({pcs[1]} if len(pcs) > 1 else set())
    best, bc = None, 1e9
    for up in product(pool, repeat=n):
        if any(up[i] >= up[i + 1] for i in range(n - 1)) or (n > 1 and up[-1] - up[0] > 12 * (n - 1)):
            continue
        if any(up[i + 1] - up[i] > 12 for i in range(n - 1)) or up[0] <= b0:
            continue
        have = [q % 12 for q in up] + [bpc]
        if not need <= set(have) or any(have.count(t) > 1 for t in tend):
            continue
        # the resolution: a tendency tone by step its way; the others: held, or the nearest tone below / above
        opts = []
        for q in up:
            d = tend.get(q % 12)
            if d:
                s_ = 1 if d > 0 else -1
                c = [x for x in (q + s_, q + 2 * s_) if x % 12 in npcs][:1]
                opts.append(([q] if abs(d) == 2 and q % 12 in npcs else []) + c)
            else:
                c = [q] if q % 12 in npcs else []
                dn = next((x for x in range(q - 1, q - 4, -1) if x % 12 in npcs), None)
                upq = next((x for x in range(q + 1, q + 4) if x % 12 in npcs), None)
                opts.append(c + [x for x in (dn, upq) if x is not None and x not in c])
        if not all(opts):
            continue
        for res in product(*opts):
            if any(res[i] >= res[i + 1] for i in range(n - 1)) or res[-1] > top or res[0] <= b1:
                continue
            if not {nthird, nroot} <= {x % 12 for x in res} | {b1 % 12} or \
                    [x % 12 for x in res + (b1,)].count(nthird) > 1:
                continue                            # (the resolution's third there, never doubled: the leading tone)
            vs0, vs1 = (b0,) + tuple(up), (b1,) + tuple(res)
            if any(_parallel(vs0[i], vs1[i], vs0[j], vs1[j]) for i in range(n + 1) for j in range(i + 1, n + 1)):
                continue
            cost = sum(abs(x - y) for x, y in zip(up, res)) + 0.15 * sum(abs(x - centre) for x in up) + \
                0.5 * sum(1 for i in range(n - 1) if up[i + 1] - up[i] > 7)
            if cost < bc - 1e-9:
                best, bc = ((b0, list(up)), (b1, list(res))), cost
    return best


_REALISABLE = {}


def chroma_pre(key: str, t0: float, U: float, bars: int, target: str, first: str | None = None, rng=None):
    """CHROMA_CADENCE's accelerated predominant: `bars` bars from t0 two chords a bar, chosen by harmonize() (no
    melody: the progression weights) - the first `first` (the bar's chord so far) or a predominant (PREDOM), the
    middle ones predominants, the last a chromatic chord of CHROMA_PRE[target] that realise() can voice into `target`
    (the roman / 'cad64' the cadence goes on with, pinned on the bar after; rng: the candidates' weights drawn) ->
    (chart rows [(start, beats, symbol)], the chromatic record [(start, beats, rn, target)]), or None (no such chord in
    the key)."""
    minor = Key(key).minorish
    tgt = _mode_rn(target, minor) if target != 'cad64' else target
    tk = 'V7' if tgt == 'V7' else 'V' if tgt == 'V' else 'cad64' if tgt == 'cad64' else 'IV'
    cls = []
    for rn in CHROMA_PRE[tk]:
        if not chroma_fits(key, rn) or tgt not in chroma_targets(key, rn):
            continue
        k_ = (key, rn, tgt)
        if k_ not in _REALISABLE:
            _REALISABLE[k_] = realise(key, rn, tgt, 3) is not None
        if _REALISABLE[k_]:
            cls.append(rn)
    if not cls or bars < 1:
        return None
    pre = PREDOM['minor' if minor else 'major']
    forced = {(i, h): pre for i in range(bars) for h in (0, 1)}
    if first:
        forced[(0, 0)] = first
    forced[(bars - 1, 1)] = tuple(cls)
    forced[bars] = tgt
    w = {rn: 0.5 + (rng.random() if rng is not None else 0.5) for rn in cls}
    chart = harmonize([], key, t0, bars + 1, U, forced, split=set(range(bars)), chroma={(bars - 1, 1): w})
    rows = [r for r in chart if r[0] < t0 + bars * U - _EPS]
    syms = {chroma_symbol(key, rn): rn for rn in cls}
    rec = [(a, d, syms[s], tgt) for a, d, s in rows if s in syms]
    return rows, rec


def _chroma_pcs(key: str, sym: str, syms) -> set:
    """pcs_of for a chromatic chord of `syms` (CHROMA_CADENCE's): the scale with the chord's tones for the scale tones a
    semitone from them; any other chord: pcs_of."""
    if not syms or sym not in syms:
        return pcs_of(key, sym)
    cs = _cpcs(sym)
    pcs = {p for p in pcs_of(key) if not any((p - c) % 12 in (1, 11) for c in cs)}
    return pcs | cs


# ------------------------------------------------------------------------------------------ the chromatic event

CHROMA_EVENT = None
"""Off (None, the default: bit-identical) or {'final', 'recap', 'level', 'soft', 'hold', 'chain', 'chain_level',
'chain_top'}: round o15b - the chromatic harmony as an EVENT at the two structural points only (o14's judges heard
CHROMA_CADENCE's two quiet inner-voice chords nowhere; they praised the stormy reference's sudden tutti Neapolitan
before the last cadence and its chord-block chain into the dominant pedal). 'final': the end block's predominant bar
before the approach becomes ONE chromatic chord (EVENT_FINAL per approach: the Neapolitan in root position - the bass
on b2 - or the German / French sixth - the bass on b6), the whole orchestra on it at 'level' ('soft' in a soft
ending), held under a fermata of 'hold' beats, then V(7) - I (the plagal 'pre' approach becomes V7 under it); once a
piece. 'recap': before the return's dominant pedal a chord-block chain of 'chain' song bars (EVENT_CHAINS, drawn per
piece) into V - the brass and the strings in block chords at 'chain_level', its last (chromatic) chord at
'chain_top', then the pedal at its own level. Both voiced by _event_voice (realise()'s rules over the whole chain:
the tendency tones by step their way, no parallel fifths / octaves - the melody and the bass included -, no tendency
tone or leading tone doubled, the chords complete); the melody takes the top voice; in the event's span every other
part of the block gives way to the tutti chords (_event_tutti)."""
CHROMA_EVENT_ON = {'final': True, 'recap': True, 'level': 'ff', 'soft': 'f', 'hold': 2.0, 'chain': 4,
                   'chain_level': 'f', 'chain_top': 'ff'}
"""The CHROMA_EVENT setting a paired round switches on (symphony.CHROMA_EVENT = dict(CHROMA_EVENT_ON))."""
EVENT_TONES = {
    'I': ((1, 0), (3, 0), (5, 0)), 'i': ((1, 0), (3, -1), (5, 0)),
    'V': ((5, 0), (7, 0), (2, 0)), 'V7': ((5, 0), (7, 0), (2, 0), (4, 0)),
    'IV': ((4, 0), (6, 0), (1, 0)), 'iv': ((4, 0), (6, -1), (1, 0)),
    'bVI': ((6, -1), (1, 0), (3, -1)), 'vii°': ((7, 0), (2, 0), (4, 0)),
    'I7': CHROMA['V7/IV']['tones'], 'vii°7/V': CHROMA['vii°7/V']['tones'], 'V7/V': CHROMA['V7/V']['tones'],
    'N': CHROMA['N6']['tones'], 'Ger6': CHROMA['Ger6']['tones'], 'Fr6': CHROMA['Fr6']['tones'],
    'It6': CHROMA['It6']['tones']}
"""The event chords' tones (scale degree, alteration against the tonic's MAJOR scale - CHROMA's notation) in root
order; 'I' / 'i' also the cadential six-four (the bass on the fifth)."""
EVENT_TEND = {'V': {1: 1}, 'V7': {1: 1, 3: -2}, 'vii°': {0: 1}, 'I7': CHROMA['V7/IV']['tend'],
              'vii°7/V': CHROMA['vii°7/V']['tend'], 'V7/V': CHROMA['V7/V']['tend'], 'N': {0: -1},
              'Ger6': CHROMA['Ger6']['tend'], 'Fr6': CHROMA['Fr6']['tend'], 'It6': CHROMA['It6']['tend']}
"""The tendency tones per chord (tone index: +1 rises / -1 falls by step / -2 falls by step or holds - CHROMA 'tend';
the leading tone of V / V7 / vii° rises): binding where the next chord has a tone there (the six-four's 6 and 4 fall:
_event_voice)."""
EVENT_FIFTH = ('I', 'i', 'V', 'V7', 'IV', 'iv', 'bVI', 'I7', 'V7/V')
"""The event chords whose fifth may be left out (the tonic after V7: the leading tone up, the seventh down, the melody
on the root - the classical incomplete tonic); the chromatic chords keep every tone."""
EVENT_FINAL = {'cad64': {'Ger6': 1.0, 'N': 1.0}, 'V': {'N': 1.0, 'Fr6': 0.8}}
"""The final event's chord per approach (its first chord: the cadential six-four, or V7 - 'V', 'echo' and the plagal
'pre' turned V7): the German sixth only into the six-four (into V its fifths are parallel)."""
EVENT_CHAINS = {
    'descent': {'major': (('I', 0), ('V', 1), ('I7', 3), ('IV', 1), ('iv', 1)),
                'minor': (('i', 0), ('V', 1), ('I7', 3), ('IV', 1), ('iv', 1))},
    'deceptive': {'major': (('V7', 0), ('bVI', 0), ('Fr6', 0)), 'minor': (('V7', 0), ('bVI', 0), ('Fr6', 0))},
    'ascent': {'major': (('I', 1), ('IV', 0), ('vii°7/V', 0)), 'minor': (('i', 1), ('iv', 0), ('vii°7/V', 0))},
    'neapolitan': {'major': (('N', 0), ('vii°', 0), ('bVI', 0), ('V7/V', 0)),
                   'minor': (('N', 0), ('vii°', 0), ('bVI', 0), ('V7/V', 0))}}
"""The retransition's chord chains into V ((chord, the bass's tone index) in order): 'descent' the bass falling by
semitones 1 - 7 - b7 - 6 - b6 - 5 (I, V6, I7/b7, IV6, iv6: the chromatic lament), 'deceptive' V7 - bVI - Fr6 (the
bass 5 - b6 - b6 - 5: the dominant's deceptive move, then the real one), 'ascent' the bass rising 3 - 4 - #4 - 5 (I6,
IV, vii°7/V), 'neapolitan' N - vii° - bVI - V7/V (the stormy reference's chord-block chain, VRNU 71-74)."""
EVENT_CHAIN_W = {'descent': 1.0, 'deceptive': 1.0, 'ascent': 0.7, 'neapolitan': 1.0}


def _ev_chord(key: str, name: str, bass: int = 0) -> dict:
    """An event chord: {'name', 'pcs' (root order), 'bass' (pc), 'tend' {pc: d}, 'sym' (the chart symbol), 'lt'
    (its leading tone, never doubled), 'six4'}."""
    from ..theory import spell_above
    K = Key(key)
    tones = EVENT_TONES[name]
    pcs = [_chroma_pc(key, t) for t in tones]
    tend = {pcs[i]: d for i, d in EVENT_TEND.get(name, {}).items()}
    six4 = name in ('I', 'i') and bass == 2
    if six4:                                    # (the cadential six-four: its 6 and 4 fall to 5's third and root)
        tend = {pcs[0]: -1, pcs[1]: -1}
    names = [spell_above(K.tonic_name, (p - K.tonic) % 12, t[0] - 1) for p, t in zip(pcs, tones)]
    q = _CHROMA_QUALITY[tuple(sorted((p - pcs[0]) % 12 for p in pcs))]
    sym = names[0] + q + (f"/{names[bass]}" if bass else '')
    lt = (K.tonic + 11) % 12 if name in ('V', 'V7', 'vii°') else None
    return {'name': name, 'pcs': pcs, 'bass': pcs[bass], 'tend': tend, 'sym': sym, 'lt': lt, 'six4': six4}


def _event_voice(chords, n: int = 4, lo: int = 52, hi: int = 81, centre: float | None = None, top0=None,
                 fix=None, bass0: int = 43, loose_top: bool = False):
    """The chords (_ev_chord dicts) voiced as a chorale: [(bass, [n upper voices low-high])] or None. realise()'s
    rules over the whole chain: the chords complete (bass + upper voices), no tendency tone (the bass aside) and no
    leading tone doubled; from each chord to the next every tendency tone moves by step (1-2 semitones) its way where
    the next chord has a tone there (-2 may hold a common tone); no parallel fifths / octaves between any two voices,
    the bass included; the upper voices in lo..hi, rising, an octave at most apart, the lowest over the bass. fix: per
    chord the top voice's pitch (the melody) or None (free; top0 the first's preferred top); the bass: each chord's
    bass pc nearest the bass before (bass0 the first's), in 31..52 (the Neapolitan's root may double the bass);
    loose_top: the top voice's tendencies free (the fallback). Cheapest by the voices' motion + 0.15 x their
    distance from `centre`."""
    from itertools import combinations
    fix = list(fix or [None] * len(chords))
    centre = (lo + hi) / 2.0 if centre is None else centre
    basses, pb = [], bass0
    for c in chords:
        pb = min((q for q in range(31, 53) if q % 12 == c['bass']), key=lambda q: (abs(q - pb), abs(q - bass0), q))
        basses.append(pb)
    cands = []
    for k, c in enumerate(chords):
        pool = [q for q in range(lo, hi + 1) if q % 12 in c['pcs']]
        out = []
        for up in combinations(pool, n):
            if up[0] <= basses[k] or any(up[i + 1] - up[i] > 12 for i in range(n - 1)):
                continue
            if fix[k] is not None and up[-1] != fix[k]:
                continue
            have = [q % 12 for q in up]
            need = set(c['pcs']) - ({c['pcs'][2]} if c['name'] in EVENT_FIFTH and c['pcs'][2] != c['bass'] else set())
            if not need <= set(have) | {c['bass']}:
                continue
            allv = have + [c['bass']]
            if any(have.count(t) + (1 if t == c['bass'] and c['name'] != 'N' else 0) > 1 for t in c['tend']) or \
                    (c['lt'] is not None and allv.count(c['lt']) > 1):
                continue
            own = 0.15 * sum(abs(q - centre) for q in up) + 0.5 * sum(1 for i in range(n - 1) if up[i + 1] - up[i] > 7)
            if k == 0 and top0 is not None and fix[0] is None:
                own += 0.5 * abs(up[-1] - top0)
            out.append((own, up))
        if not out:
            return None
        cands.append(out)

    def ok(k, u, v):
        c, nx = chords[k], chords[k + 1]
        npcs = set(nx['pcs'])
        for i, (q0, q1) in enumerate(zip(u, v)):
            if i == n - 1 and ((fix[k] is not None and fix[k + 1] is not None) or loose_top):
                continue                                 # (the melody as written)
            d = c['tend'].get(q0 % 12)
            if d:
                s_ = 1 if d > 0 else -1
                tg = [x for x in (q0 + s_, q0 + 2 * s_) if x % 12 in npcs]
                if tg and q1 not in tg and not (abs(d) == 2 and q1 == q0 and q0 % 12 in npcs):
                    return False
            if abs(q1 - q0) > 9:
                return False
        vs0, vs1 = (basses[k],) + tuple(u), (basses[k + 1],) + tuple(v)
        return not any(_parallel(vs0[i], vs1[i], vs0[j], vs1[j]) for i in range(n + 1) for j in range(i + 1, n + 1))
    best = [{up: (own, None) for own, up in cands[0]}]
    for k in range(1, len(chords)):
        row = {}
        for own, v in cands[k]:
            bc, bu = None, None
            for u, (cu, _) in best[-1].items():
                if not ok(k - 1, u, v):
                    continue
                c_ = cu + own + sum(abs(x - y) for x, y in zip(u, v))
                if bc is None or c_ < bc - 1e-9:
                    bc, bu = c_, u
            if bc is not None:
                row[v] = (bc, bu)
        if not row:
            return None
        best.append(row)
    v = min(best[-1], key=lambda x: (best[-1][x][0], x))
    path = [v]
    for k in range(len(chords) - 1, 0, -1):
        v = best[k][v][1]
        path.append(v)
    path.reverse()
    return [(b, list(up)) for b, up in zip(basses, path)]


def _final_event(w, name: str, key: str, blk: dict, t: float, ta: float, U: float, kind: str, seed: int):
    """CHROMA_EVENT 'final' on the end block (material): the predominant bar before the approach (ta - U) one chromatic
    chord (EVENT_FINAL), voiced with the approach and the tonic (_event_voice, the melody fixed from ta on, its top the
    melody's held note in the event bar) -> the event record (internal beats), the block's chart / theme rewritten; or
    None (a church mode, no predominant bar, a plagal / pedal close, no voicing)."""
    K = Key(key)
    cad = blk.get('cadence')
    if K.mode not in ('major', 'minor') or cad not in ('cad64', 'V', 'echo', 'pre') or ta - U < t - _EPS:
        return None
    minor = K.minorish
    I = 'i' if minor else 'I'
    If = _roman(key, I)
    end = t + blk['bars'] * U
    if cad == 'pre':                         # (the predominant is the event: the approach V7 under it)
        ch_, sop = _approach(key, 'V', ta, U, blk['theme'][-1][2])
        blk['chart'] = [r for r in blk['chart'] if r[0] < ta - _EPS] + ch_ + [(ta + U, end - ta - U, If)]
        blk['theme'] = [n for n in blk['theme'] if n[0] < ta - _EPS] + sop + \
            [n for n in blk['theme'] if n[0] >= ta + U - _EPS]
        cad = 'V'
    ws = EVENT_FINAL['cad64' if cad == 'cad64' else 'V']
    rng = random.Random(f"symphony:{seed}:event_final")
    opts = sorted(ws)
    first = _pick(rng, {x: ws[x] for x in opts})
    app = [r for r in sorted(blk['chart']) if ta - _EPS <= r[0] < ta + U - _EPS]
    rest = []
    for a_, d_, sy in app:
        if '/' in sy and cad == 'cad64' and a_ < ta + _EPS:
            rest.append(_ev_chord(key, I, 2))
        else:
            rest.append(_ev_chord(key, 'V7', 0))
    rest.append(_ev_chord(key, I, 0))
    starts = [ta - U] + [a_ for a_, _, _ in app] + [ta + U]
    durs = [U] + [d_ for _, d_, _ in app] + [end - ta - U]

    def mel_at(x):
        return next((p for a_, d_, p in blk['theme'] if a_ - _EPS <= x < a_ + d_ - _EPS), None)
    fix = [None] + [mel_at(x) for x in starts[1:]]
    prev = next((p for a_, d_, p in reversed(blk['theme']) if a_ < ta - U - _EPS), None)
    tops = [x for x in fix if x is not None] + ([prev] if prev is not None else [])
    hi = max(tops) if tops else w.centre + 7
    got = None
    lo_ = min(hi - 29, min(tops) - 22) if tops else hi - 29
    for rn in [first] + [x for x in opts if x != first and ws[x] > 0]:     # (the drawn chord, else the other)
        ev_c = _ev_chord(key, rn, 0)
        seq = [ev_c] + rest
        for n_, loose in ((4, False), (3, False), (4, True), (3, True)):
            got = got or _event_voice(seq, n=n_, lo=lo_, hi=hi, centre=(lo_ + hi) / 2, top0=prev, fix=fix,
                                      loose_top=loose)
        if got:
            break
    if not got:
        return None
    top = got[0][1][-1]
    blk['chart'] = [r for r in blk['chart'] if not (ta - U - _EPS <= r[0] < ta - _EPS)] + [(ta - U, U, ev_c['sym'])]
    blk['chart'].sort()
    blk['theme'] = [(a_, min(d_, ta - U - a_), p) for a_, d_, p in blk['theme'] if a_ < ta - U - _EPS] + \
        [(ta - U, U, top)] + [n for n in blk['theme'] if n[0] >= ta - _EPS]
    return {'kind': 'final', 'rn': rn, 'a': ta - U, 'z': end, 'hold': (ta - U, U),
            'chords': [(a_, d_, c['sym'], b, up) for a_, d_, c, (b, up) in zip(starts, durs, seq, got)],
            'tops': [(ta - U, U, top)], 'cut': (ta - U, end), 'soft': kind == 'end_soft'}


# ------------------------------------------------------------------------------------------------ the chooser

def harmonize(notes, key: str, t0: float, bars: int, U: float, forced: dict | None = None,
              split: set | None = None, chroma: dict | None = None) -> list:
    """The chords under a melody (melody first): a chord per bar - two per bar where one cannot hold the bar's
    important notes (on a pulse, or held a beat+), or where `split` names the bar - chosen by one dynamic programme
    over the bars: the notes' fit (an important note outside the chord costs most) + the progression's weight
    (NEXT) + a prior (iii / VII / ii° rarer). forced {segment index (bar, half): roman} pins a chord (the cadences);
    a bar index alone pins the whole bar; a TUPLE of romans pins a function (the chooser picks one of them - CHROMA
    names and 'cad64' allowed). The chromatic vocabulary (CHROMA): candidates in every segment by CHROMA_WEIGHTS (0:
    none - the default) and per segment by chroma {segment index: {rn: weight}}; a chromatic chord moves only into
    one of its resolutions (chroma_targets). Returns the chart [(start, beats, symbol)] in the notes' beats."""
    forced = dict(forced or {})
    split = set(split or ())
    mode = 'minor' if Key(key).minorish else 'major'
    cands = [(rn, _roman(key, rn)) for rn in _ROMANS[mode]]
    every = {rn: w for rn, w in CHROMA_WEIGHTS.items() if w > 0 and chroma_fits(key, rn)}

    def sym_of(rn):
        return chroma_symbol(key, rn) if rn in CHROMA or rn == 'cad64' else _roman(key, rn)

    def fdeg(rn):
        return CHROMA[rn]['deg'] if rn in CHROMA else 5 if rn == 'cad64' else _deg(rn)
    half = U / 2.0
    pulses = (0.0, half) if U == 4 else (0.0, 1.5) if U == 3 else (0.0,)

    def fit(a, d, sym):
        cs = _cpcs(sym)
        sc = 0.0
        for st, du, p in notes:
            o = min(st + du, a + d) - max(st, a)
            if o <= _EPS:
                continue
            strong = any(abs((st - t0) % U - x) < 1e-3 for x in pulses)
            w = o * (2.0 if strong or du >= 1.0 - _EPS else 0.5)
            if p % 12 not in cs:
                sc -= 3.0 * w
        return sc
    segs = []
    for b in range(bars):
        a = t0 + b * U
        whole = forced.get(b)
        if whole is None and b not in split and (b, 0) not in forced and (b, 1) not in forced:
            best = max(fit(a, U, s) for _, s in cands)
            if best > -1.5:
                segs.append(((b, None), a, U))
                continue
        if whole is not None:
            segs.append(((b, None), a, U))
            continue
        segs.append(((b, 0), a, half))
        segs.append(((b, 1), a + half, half))
    # the dynamic programme
    INF = -1e9
    prev = None
    table = []
    for k, (ix, a, d) in enumerate(segs):
        pin = forced.get(ix[0]) if ix[1] is None else forced.get(ix)
        extra = dict(every)
        extra.update({rn: w for rn, w in ((chroma or {}).get(ix) or {}).items() if w > 0 and chroma_fits(key, rn)})
        if isinstance(pin, tuple):                  # (a function pin: one of these)
            opts = [(rn, s) for rn, s in cands if rn in pin] + \
                [(rn, sym_of(rn)) for rn in pin if rn not in _ROMANS[mode] and (rn not in CHROMA or
                                                                             chroma_fits(key, rn))]
        else:
            opts = [(rn, s) for rn, s in cands if pin is None or rn == pin]
            if pin is not None and not opts:
                opts = [(pin, sym_of(pin))]
            elif pin is None:
                opts += [(rn, sym_of(rn)) for rn in extra]
        row = {}
        for rn, s in opts:
            f = fit(a, d, s) + _PRIOR.get(rn, 0.0)
            if rn in extra:
                f += 1.2 * math.log(extra[rn])
            if rn == 'V7' and k + 1 < len(segs):
                f -= 0.2
            if rn in CHROMA and k + 1 == len(segs):
                f -= 50.0                           # (a chromatic chord resolves inside the chart)
            if prev is None:
                row[rn] = (f + (1.0 if fdeg(rn) == 1 else 0.0), None, s)
                continue
            bestv, bestp = INF, None
            for prn, (pv, _, _) in prev.items():
                if prn in CHROMA:                   # (a chromatic chord into one of its resolutions only)
                    w = 1.4 if rn in chroma_targets(key, prn) else 1e-20
                else:
                    w = NEXT.get(fdeg(prn), {}).get(fdeg(rn), 0.05)
                    if prn == rn:
                        w = 0.25 if ix[1] != 1 else 0.05
                v = pv + f + 1.2 * math.log(w)
                if v > bestv:
                    bestv, bestp = v, prn
            row[rn] = (bestv, bestp, s)
        table.append(row)
        prev = row
    # back-track
    rn = max(table[-1], key=lambda r: table[-1][r][0])
    picks = []
    for k in range(len(table) - 1, -1, -1):
        picks.append(table[k][rn][2])
        rn = table[k][rn][1] or rn
    picks.reverse()
    chart = []
    for (ix, a, d), sym in zip(segs, picks):
        if chart and chart[-1][2] == sym:
            chart[-1] = (chart[-1][0], chart[-1][1] + d, sym)
        else:
            chart.append((a, d, sym))
    return chart


def _chart_at(chart, t: float):
    for a, b, s in chart:
        if a - _EPS <= t < a + b - _EPS:
            return s
    return chart[-1][2] if chart else None


def fit_line(notes, chart, key: str, strict: float = 1.0, chroma=None) -> list:
    """The clash snap: every note in its chord's scale (pcs_of: the leading tone over V in minor); a note held
    `strict` beats+ or on the chord's onset outside the chord moves to the nearest chord tone (a step at most).
    chroma: the chart's chromatic symbols (CHROMA_CADENCE) - their scale takes their tones (_chroma_pcs)."""
    out = []
    for a, d, p in notes:
        sym = _chart_at(chart, a + min(d, 0.5) * 0.5)
        if sym is None:
            out.append((a, d, p))
            continue
        sc = _chroma_pcs(key, sym, chroma) if chroma else pcs_of(key, sym)
        if p % 12 not in sc:
            p = min((q for q in (p - 1, p + 1) if q % 12 in sc), key=lambda q: (abs(q - p), q), default=p)
        cs = _cpcs(sym)
        on = any(abs(a - x) < 1e-3 for x, _, _ in chart)
        if (d >= strict - _EPS or on) and p % 12 not in cs:
            q = min((q for q in range(p - 2, p + 3) if q % 12 in cs), key=lambda q: (abs(q - p), q), default=p)
            p = q
        out.append((a, d, p))
    return out


# ------------------------------------------------------------------------------------------------ the motto

def cell_of(m: dict) -> tuple:
    return CELLS[m['family']][m['kind']]


def lead_of(m: dict) -> float:
    """The landing note's onset in the cell (beats): a pickup entry starts this much before the downbeat."""
    return next(on for on, _, st in cell_of(m) if st == 'L')


def motto_notes(m: dict, t: float, anchor: int, pcs, tf=(), land: int | None = None, fill: float | None = None):
    """One statement of the motto from beat t on its anchor pitch, stepping in pcs: tf - 'invert' (the steps
    mirrored), 'augment' / 'diminish' (x2 / x0.5), 'head' (the notes before the landing + the landing as a beat),
    'chordal' (every step on the anchor's chord: the motto's rhythm hammered); fill: the landing held to this beat.
    The code review's A1 step 1: Kernel.motto(m).apply - the derivation engine's kernel (bit-identical)."""
    return Kernel.motto(m).apply(t, anchor, pcs, tf, land, fill)


# ------------------------------------------------------------------------------------------ the derivation engine

DERIVE_OPS = ('retro', 'expand', 'contract', 'liquidate', 'displace', 'shift', 'frag2', 'frag3', 'combine', 'mode',
              'reharm', 'recall')
"""The transform algebra's ops past motto_notes' (invert, augment, diminish, head, chordal, kernel), applied in their
order after those (Kernel.steps): 'retro' the retrograde (the rhythm and the steps reversed, from the anchor),
'expand' / 'contract' every interval a scale step wider / narrower (a step stays a step), 'liquidate' every interval a
step its way (the cell's leaps gone, its rhythm kept), 'displace' the line half a beat late (off the beat), 'shift' a
half bar late (the change of metric position), 'frag2' / 'frag3' the first 2 / 3 notes (fragment(k), the last held a
beat), 'combine' the line's rhythm on the other kernel's intervals (the second theme's: combine(a, b)); 'mode' (the
parallel mode) and 'reharm' (the model's chord a third under) are harmony ops - the walk realises them, the notes
pass; 'recall' a line taken up again from the development (the recapitulation's / coda's counter-line)."""


class Kernel:
    """A motivic kernel (the code review's A1, songs/_endless_orchestra/out/code_review/REPORT.md): its rhythm cell,
    interval cell (scale steps), contour and signature (the accent pattern), stated by apply(ops). The cell is CELLS'
    form - (onset, duration, step | 'L' the landing: `land` steps over the note before | ('L', k) the landing + k) -;
    Kernel.motto(m) is the motto (motto_notes), Kernel.line(notes, key) a written line's head (the second theme's)."""

    def __init__(self, cell, land: int, family: str, name: str = 'K1'):
        self.cell, self.land, self.family, self.name = tuple(cell), land, family, name

    @classmethod
    def motto(cls, m: dict) -> 'Kernel':
        return cls(cell_of(m), m['land'], m['family'], 'K1')

    @classmethod
    def line(cls, notes, key: str, family: str, span: float, name: str = 'K2'):
        """The kernel of a written line (notes from 0): its notes in the first `span` beats (the first two spans when
        one holds under 3), the steps counted in the key's scale, the first held note (a beat+) after the first the
        landing; None for a line of under 3 notes."""
        ns = sorted(n for n in notes if n[0] < span - _EPS)
        if len(ns) < 3:
            ns = sorted(n for n in notes if n[0] < 2 * span - _EPS)
        if len(ns) < 3:
            return None
        pcs = set(Key(key).pcs)
        t0, p0 = ns[0][0], ns[0][2]
        st = [_steps_to(p0, q, pcs) for _, _, q in ns]
        li = next((i for i in range(1, len(ns)) if ns[i][1] >= 1.0 - _EPS), len(ns) - 1)
        cell = []
        for i, (a, d, _) in enumerate(ns):
            x = (round(a - t0, 3), round(min(d, (ns[i + 1][0] - a) if i + 1 < len(ns) else d), 3))
            cell.append(x + ((st[i],) if i < li else ('L',) if i == li else (('L', st[i] - st[li]),)))
        return cls(cell, st[li] - st[li - 1], family, name)

    def resolved(self, land: int | None = None) -> list:
        """The cell's steps with the landing resolved: [(onset, duration, step)]."""
        return self.steps(0.0, (), land)

    @property
    def rhythm(self) -> tuple:
        return tuple((on, du) for on, du, _ in self.cell)

    def intervals(self) -> tuple:
        s = [x[2] for x in self.resolved()]
        return tuple(b - a for a, b in zip(s, s[1:]))

    def contour(self) -> tuple:
        return tuple((x > 0) - (x < 0) for x in self.intervals())

    def signature(self) -> tuple:
        """The accent pattern: the indices of the notes held longer than the one before (the cell's arrivals)."""
        r = self.rhythm
        return tuple(i for i in range(len(r)) if i == 0 or r[i][1] > r[i - 1][1] + _EPS)

    def span(self, tf=()) -> float:
        """The beats one statement lasts."""
        ns = self.steps(0.0, tf)
        return max((a + d for a, d, _ in ns), default=0.0)

    def steps(self, t: float, tf=(), land: int | None = None, fill: float | None = None, other=None) -> list:
        """[(beat, duration, step over the anchor)] of one statement from beat t: motto_notes' transforms, then the
        DERIVE_OPS in tf's order (other: the kernel 'combine' takes its intervals from)."""
        L = self.land if land is None else land
        k = 2.0 if 'augment' in tf else 0.5 if 'diminish' in tf else 1.0
        out, seen_l = [], False
        prev, ls = 0, None                     # (the landing: steps from the note before it)
        for on, du, st in self.cell:
            if isinstance(st, tuple):
                s = (ls if ls is not None else prev + L) + st[1]
            elif st == 'L':
                if 'head' in tf and seen_l:
                    break
                s, seen_l = prev + L, True
                ls = s
            else:
                s = st
            prev = s
            if 'chordal' in tf:
                s = 0
            if 'invert' in tf:
                s = -s
            dur = du * k
            if 'head' in tf and st == 'L':
                dur = min(dur, 1.0 * k)
            out.append((t + on * k, dur, s))
            if 'head' in tf and st == 'L':
                break
        if 'kernel' in tf and out:            # the kernel: the notes inside the first half bar, the last held to it
            kl = (2.0 if self.family == 'duple' else 1.5) * k
            keep = [n for n in out if n[0] - t < kl - _EPS]
            keep = keep if len(keep) >= 2 else out[:2]
            a, d, p = keep[-1]
            keep[-1] = (a, max(0.25 * k, t + kl - a) if a - t < kl else d, p)
            out = keep
        for op in tf:
            if op in DERIVE_OPS and out:
                out = _derive_op(op, out, t, self.family, other)
        if fill is not None and out:
            a, d, p = out[-1]
            out[-1] = (a, max(d, fill - a), p)
        return out

    def apply(self, t: float, anchor: int, pcs, tf=(), land: int | None = None, fill: float | None = None,
              other=None) -> list:
        """One statement: steps() on the anchor pitch, stepping in pcs."""
        return [(a, d, _step(anchor, s, pcs)) for a, d, s in self.steps(t, tf, land, fill, other)]


def _steps_to(p: int, q: int, pcs) -> int:
    """The scale steps from p to q (q off the scale: counted to the scale tone past it)."""
    sg = 1 if q >= p else -1
    n, x = 0, p
    while (x - q) * sg < 0:
        x += sg
        if x % 12 in pcs:
            n += sg
    return n


def _derive_op(op: str, out: list, t: float, family: str, other=None) -> list:
    """One DERIVE_OPS transform on a statement's [(beat, duration, step)]."""
    def sg(x):
        return (x > 0) - (x < 0)

    def by_iv(f):
        res, cur = [out[0]], out[0][2]
        for (_, _, s0), (a1, d1, s1) in zip(out, out[1:]):
            cur += f(s1 - s0)
            res.append((a1, d1, cur))
        return res
    if op == 'retro':
        E = max(a + d for a, d, _ in out)
        r = sorted((t + (E - (a + d)), d, s) for a, d, s in out)
        s0 = r[0][2] - out[0][2]
        return [(a, d, s - s0) for a, d, s in r]
    if op == 'expand':
        return by_iv(lambda iv: iv + sg(iv))
    if op == 'contract':
        return by_iv(lambda iv: iv if abs(iv) <= 1 else iv - sg(iv))
    if op == 'liquidate':
        return by_iv(sg)
    if op in ('displace', 'shift'):
        dx = 0.5 if op == 'displace' else (2.0 if family == 'duple' else 1.5)
        return [(a + dx, d, s) for a, d, s in out]
    if op in ('frag2', 'frag3'):
        keep = list(out[:2 if op == 'frag2' else 3])
        a, d, s = keep[-1]
        keep[-1] = (a, max(d, 1.0), s)
        return keep
    if op == 'combine' and other is not None:
        ivs = other.intervals() or (1,)
        res, cur = [out[0]], out[0][2]
        for i, (a, d, _) in enumerate(out[1:]):
            cur += ivs[i % len(ivs)]
            res.append((a, d, cur))
        return res
    return out


SEQ_PAIR = (None, ()), (1, ('invert',))
"""A fragmentation's kernel in pairs (round q1: the sentence's and the retransition's kernel twice on one pitch read
as a two-note shake, D-F#-D-F#): per pair member (scale steps over the end of the pair's first kernel - None: the
pair's anchor itself -, transform): the kernel, then the kernel inverted from a step above where it ended (it goes
on up, then falls back: a rising sequence of up-and-back cells, no a-b-a-b)."""

TAIL = {'grid': {'duple': 0.5, 'compound': 0.5, 'scherzo': 1.0}, 'max': 4}
"""A landing held over a whole bar of the song (the scherzo's doubled values: a theme of chord-tone outlines in long
notes, round q1) keeps one bar - the held peak - and its rest becomes a stepwise answer on 'grid' (song beats per
family; 'scherzo' the fast 3/4) toward the next statement's first note, at most 'max' notes."""


def motto_character(m: dict) -> bool:
    """MOTTO_CHARACTER: the motto (in C major from C4) has a leap, one peak and no repeated-note signal."""
    ps = [p for _, _, p in motto_notes(m, 0.0, 60, set(Key('C major').pcs))]
    run = best = 0
    for a, b in zip(ps, ps[1:]):
        run = run + 1 if a == b else 0
        best = max(best, run)
    leap = max((abs(b - a) for a, b in zip(ps, ps[1:])), default=0)
    steps = run_ = 0                       # (round o12: the longest run of steps one way - a scale head)
    prev = 0
    for a, b in zip(ps, ps[1:]):
        d = b - a
        sg = (d > 0) - (d < 0)
        run_ = run_ + 1 if 0 < abs(d) <= 2 and sg == prev else (1 if 0 < abs(d) <= 2 else 0)
        prev = sg if 0 < abs(d) <= 2 else 0
        steps = max(steps, run_)
    lim = MOTTO_CHARACTER.get('scale')
    return bool(ps) and best <= MOTTO_CHARACTER['repeats'] and leap >= MOTTO_CHARACTER['leap'] and \
        ps.count(max(ps)) == 1 and max(ps) - min(ps) <= MOTTO_CHARACTER['span'] and (lim is None or steps <= lim)


def _seq_pair(m: dict, anchor: int, k: int, pcs) -> tuple:
    """The k-th kernel of a fragmentation on the pair's anchor: (its anchor, its transform) by SEQ_PAIR."""
    st, tf = SEQ_PAIR[k % len(SEQ_PAIR)]
    if st is None:
        return anchor, tf
    end = motto_notes(m, 0.0, anchor, pcs, ('kernel',))[-1][2]
    return _step(end, st, pcs), tf


def _shakes(ps) -> list:
    """The indices i where pitches i .. i+n-1 swing between two pitches (a-b-a-b: composer.HEAD_SHAPE['osc'] notes in
    a row - the piano's head-shape check, shared)."""
    from .composer import HEAD_SHAPE
    n = HEAD_SHAPE['osc']
    return [i for i in range(len(ps) - n + 1) if ps[i] != ps[i + 1] and all(ps[i + j] == ps[i + j % 2]
                                                                          for j in range(n))]


def _unshake(notes, pcs, chart=None) -> list:
    """A theme line without a two-note shake (_shakes): the shake's third note goes on past the second, in the
    direction the line was moving (a-b-a-b -> a-b-c-b); with the chart, to the nearest tone of its chord that is
    neither (the line stays fitted)."""
    out = list(notes)
    for _ in range(len(out)):
        sh = _shakes([p for _, _, p in out])
        if not sh:
            break
        i = sh[0] + 2
        a, d, p = out[i]
        prev, mid = out[i - 2][2], out[i - 1][2]
        up = mid > prev
        q = _step(mid, 1 if up else -1, pcs)
        sym = _chart_at(chart, a) if chart else None
        if sym is not None:
            cs = _cpcs(sym)
            c = [x for x in range(mid - 7, mid + 8) if x % 12 in cs and x not in (prev, mid)]
            if c:
                q = min(c, key=lambda x: (0 if (x > mid) == up else 1, abs(x - mid), x))
        if q == p:
            break
        out[i] = (a, d, q)
    return out


def _mono(notes) -> list:
    """One line: sorted, one note per onset (the first written), each note cut at the next onset."""
    out = []
    for a, d, p in sorted(notes, key=lambda n: n[0]):
        if out and abs(out[-1][0] - a) < 1e-3:
            continue
        if out and out[-1][0] + out[-1][1] > a + _EPS:
            out[-1] = (out[-1][0], max(0.125, a - out[-1][0]), out[-1][2])
        out.append((a, d, p))
    return out


def _frange(a: float, z: float, step: float) -> list:
    """a, a + step, ... under z."""
    out, x = [], a
    while x < z - _EPS:
        out.append(x)
        x += step
    return out


def _dotted(notes, t0: float) -> list:
    """A line's even pairs dotted (round o4, the recapitulation's other rhythm): two notes in a row of one length
    (half / one beat), the pair on its own grid, become dotted - long, short."""
    out = list(notes)
    i = 0
    while i + 1 < len(out):
        a, d, p = out[i]
        b, e, q = out[i + 1]
        if d in (0.5, 1.0) and abs(e - d) < _EPS and abs(b - a - d) < _EPS and abs(((a - t0) % (2 * d))) < _EPS:
            out[i], out[i + 1] = (a, 1.5 * d, p), (a + 1.5 * d, 0.5 * d, q)
            i += 2
            continue
        i += 1
    return out


def _to_mode(notes, k1: str, k2: str) -> list:
    """A line from key k1 into the parallel key k2: each scale degree moved to k2's (other notes as they are)."""
    A, B = Key(k1), Key(k2)
    pa = sorted((x - A.tonic) % 12 for x in A.pcs)
    pb = sorted((x - B.tonic) % 12 for x in B.pcs)
    out = []
    for a, d, p in notes:
        r = (p - A.tonic) % 12
        out.append((a, d, p - r + pb[pa.index(r)] if r in pa and len(pa) == len(pb) else p))
    return out


FUGUE_ORDERS = {'rise': ('v4', 'v3', 'v2', 'v1'), 'fall': ('v1', 'v2', 'v3', 'v4'), 'inner': ('v2', 'v3', 'v1', 'v4'),
                'outer': ('v1', 'v4', 'v2', 'v3')}
"""The fugato's entry order (plan['set']['fug_order'], round o10 - o9's judges: "a solo cello entry that grows into a
fugato", the set's shared signature in 4 of 8 pieces): low to high (the cellos first), high to low, from the middle
out, the outer voices first; the subject's tonic / dominant answers alternate by entry."""
FUGUE = None
FUGUE_ON_V1 = {
    'keys': {'major': {'vi': 1.0, 'ii': 0.8, 'iii': 0.6, 'IV': 0.5, 'V': 0.4},
             'minor': {'iv': 1.0, 'v': 0.8, 'III': 0.8, 'VI': 0.6}},
    'orders': {'rise': ('v4', 'v3', 'v2', 'v1'), 'fall': ('v2', 'v1', 'v3', 'v4'), 'inner': ('v3', 'v2', 'v1', 'v4'),
               'outer': ('v3', 'v4', 'v2', 'v1')},
    'voices': {'v1': (65, 86, 76), 'v2': (60, 79, 69), 'v3': (52, 72, 62), 'v4': (40, 62, 51)},
    'tex': {'fugue_mixed': 1.0, 'fugue_horn': 0.8, 'fugue_reeds': 0.8},
    'episode': {'fifths': 1.0, 'rising': 0.7}, 'frag': {'head': 1.0, 'tail': 0.6},
    'final': {'bass': 1.0, 'stretto': 0.9}, 'ep_max': 4, 'lead': 8.0, 'other': -6.0, 'horn_s': 0.2,
    'dyn': [(0, 'mp', 'step'), (0.5, 'mf'), (1, 'f')]}
"""Round o19b (o18a's judges on the dev_fugato both codes share: "18 bars of one repeated sequence pattern", "the
lone violin 1 ... too thin", "violas, cellos, bassoons and basses play the same line in octaves"; the code review's C7
/ A4): Writer.fugue2 - a fugal exposition (the subject from the motto and a tail in the other rhythm, a tonal answer at
the fifth, a counter-subject in the complementary rhythm that returns with every later entry), entries in 3-4 voices
over the registers and the choirs (the textures 'tex'), an episode from a fragment of the subject ('frag') that
modulates by a sequence ('episode': falling fifths / rising) into a related key, then a middle entry (a long block), a
second episode and the final entry - the bass's or a stretto ('final') - into a half cadence driving on. The fugato's
key from 'keys' (romans of the home key: not always vi / iv), the entry order by the set's fug_order ('orders'); the
simultaneous lines checked and repaired by voicing's joint voice-leading core (cp_issues / counterline / repair);
the entering voice 'lead' velocity steps up, the others 'other'. None: off (Writer.fugato). Round o21: FUGUE_ON is v2
(FUGUE_V2 under 'v2'); this one stays reachable (`shared_plan.py --flag fugue1`)."""
FUGUE_V2 = {
    'gap': {0.0: 1.0, 1.0: 0.6, -0.5: 0.6, -1.0: 0.4},
    'cap': {'vivace': 12, 'scherzo': 6},
    'tex': {'fugue2_mixed': 1.0, 'fugue2_horn': 0.8, 'fugue2_reeds': 0.8},
    'tex_dance': {'fugue2_dance': 1.0, 'fugue2_dance_winds': 0.7},
    'pad_until': 2, 'cs': 3.0, 'grow': 3.0, 'marks': ('mp', 'mf', 'mf', 'f'), 'overlap': 3.0, 'rounds': 5, 'cs_cost': 9.0,
    'ret': {'aug': 2, 'starts': (0, 2, 4), 'reach': 2, 'centre': 45, 'range': (33, 57)}}
"""Round o21, FUGUE v2 (o19b's judges on its fugato, the fix list): the subject is the first theme's opening S bars as
heard (Writer.fsubject2 - theme1's first phrase in the fugato's key, its landing held), not the motto kernel with a
tail; the entries' distance drawn per piece ('gap': bars added to the subject's - a codetta bar, half a bar of
overlap, a bar of stretto); the exposition never one voice alone - a per-entry pedal (the entry's tonic, until the bass
voice enters) and a soft string pad until entry 'pad_until' (0-based: the third), the dynamics rising entry by entry
('marks' at each entry, and 'grow' velocity steps per entry entered); the counter-subject heard ('cs' velocity steps
over the free voices, doubled in a colour of its own - the texture's 'counter' role); in the fast feels ('cap': the
vivace / scherzo's internal bars) the fugato capped, its surplus bars to the development's dialogue, and the dance
accompaniment (an ostinato: 'tex_dance') under the entries; the subject back at the summit ('ret': in the bass,
augmented x 'aug' - not in the scherzo -, its start bar and octave by the joint voice leading against the climax's
melody, repaired within 'reach' semitones)."""
FUGUE_ON = dict(FUGUE_ON_V1, v2=FUGUE_V2)
FUGUE = dict(FUGUE_ON)
"""Round o21 merged (on vs off +0.38 se 0.13, 2.9 se): FUGUE v2 is the default; `shared_plan.py --flag nofugue` turns
it off (Writer.fugato) for a paired baseline."""
_FUGUE_RN = {'vi': (9, 'minor'), 'ii': (2, 'minor'), 'iii': (4, 'minor'), 'IV': (5, 'major'), 'V': (7, 'major'),
             'iv': (5, 'minor'), 'v': (7, 'minor'), 'III': (3, 'major'), 'VI': (8, 'major'), 'VII': (10, 'major')}
_FUGUE_EP = {('fifths', 'major'): ('iii', 'vi', 'ii', 'V7'), ('fifths', 'minor'): ('III', 'VI', 'iv', 'V7'),
             ('rising', 'major'): ('ii', 'iii', 'IV', 'V7'), ('rising', 'minor'): ('iv', 'v', 'VI', 'V7')}
"""The episodes' chord chains in the goal key (the last E of them for an E-bar episode)."""


def fugue_key(home: str, rn: str) -> str:
    """A key related to `home` by a roman of FUGUE's 'keys' (_FUGUE_RN: its semitones and mode)."""
    semis, mode = _FUGUE_RN[rn]
    return _transpose_key(home, semis, mode)


MOTTO_RATION ={'frag': True, 'counter': 4}
"""Round o10 (o9's judges: "the motto's head opens almost every phrase", BLMX / UZWK "about thirty times"; mot_per8
5.0 statements per 8 bars outside the development): the sentence's fragmentation states the kernel once per bar, its
second half bar a free run toward the next ('frag'), and the motto against a theme (Writer.motto_counter) comes every
'counter' bars, not every two."""
REPEAT = {'units': (2, 1), 'step': 1}
"""Round o9 (o8's judges: "the apotheosis motto restated literally - the same two bars three times", 7 of 7; the
scherzo's literal restatements): a unit of a line (two song bars, then one) that copies the unit before it note for
note moves 'step' scale steps up - a sequence; every restatement changes (_unrepeat: the sentence, the dance, the
climax, the coda)."""


def _unrepeat(notes, t0: float, bar: float, pcs) -> list:
    """The line with every literal copy of the unit before it (REPEAT's units of `bar` beats from t0: the same onsets,
    lengths and pitches) sequenced up a step."""
    out = sorted(notes)
    if len(out) < 4:
        return out
    end = max(a for a, _, _ in out)
    for u in REPEAT['units']:
        L = u * bar
        prev = None
        for k in range(int((end - t0) / L + _EPS) + 1):
            x0 = t0 + k * L
            idx = [i for i, (a, _, _) in enumerate(out) if x0 - _EPS <= a < x0 + L - _EPS]
            sig = tuple((round(out[i][0] - x0, 3), round(out[i][1], 3), out[i][2]) for i in idx)
            if prev is not None and len(idx) >= 2 and sig == prev:
                for i in idx:
                    a, d, p = out[i]
                    out[i] = (a, d, _step(p, REPEAT['step'], pcs))
                sig = tuple((round(out[i][0] - x0, 3), round(out[i][1], 3), out[i][2]) for i in idx)
            prev = sig
    return out


def _ornament(notes, pcs) -> list:
    """A line's notes of a beat or more ornamented (a variation's diminution): the first half held, the rest running
    (8ths; 16ths in a note under two beats) toward the next note."""
    out = []
    for i, (a, d, p) in enumerate(notes):
        nxt = notes[i + 1][2] if i + 1 < len(notes) else p
        if d < 1.0 - _EPS or i + 1 >= len(notes):
            out.append((a, d, p))
            continue
        g = 0.5 if d >= 2.0 - _EPS else 0.25
        n = int(round((d / 2) / g))
        out.append((a, d / 2, p))
        sgn = 1 if nxt >= p else -1
        out += run_to(_step(p, sgn, pcs), nxt, a + d / 2, n, g, pcs) if n >= 1 else []
    return out


def _held_to(notes, end: float, gap: float = 0.5) -> list:
    """The last note held to `end - gap` (a breath before the next statement), never shortened under its own."""
    if not notes:
        return notes
    a, d, p = notes[-1]
    return notes[:-1] + [(a, max(d, min(end - gap - a, 3.5)), p)]


def run_to(p0: int, goal: int, t: float, n: int, g: float, pcs) -> list:
    """n notes on the grid g from beat t moving from p0 toward goal (arriving on it at t + n * g, not included):
    stepwise; with steps to spare it swings away first (a turn), too far it moves by thirds."""
    from .composer import _scale_step
    dist, q = 0, p0
    sgn = 1 if goal > p0 else -1
    while q != goal and abs(dist) < 30:
        q = _scale_step(q, sgn, pcs)
        dist += sgn
        if (sgn > 0 and q > goal) or (sgn < 0 and q < goal):
            break
    steps = abs(dist)
    out, p = [], p0
    if steps >= n:
        per = [max(1, round(steps * (i + 1) / n) - round(steps * i / n)) for i in range(n)]
        for i in range(n):
            out.append((t + i * g, g, p))
            p = _scale_step(p, sgn * per[i], pcs)
        return out
    away = (n - steps) // 2
    path = [-sgn] * away + [sgn] * (steps + away)
    path = path[:n]
    for i in range(n):
        out.append((t + i * g, g, p))
        if i < len(path):
            p = _scale_step(p, path[i], pcs)
    return out


# ------------------------------------------------------------------------------------------------ the writers

class Writer:
    """One piece's composer state: the home key, the bar (U beats internally), the motto, the draws, the log."""

    def __init__(self, key: str, family: str, motto: dict, draws: dict, rng: random.Random, centre: int = 74,
                 scale: int = 1):
        self.key, self.family, self.m, self.d, self.rng, self.centre = key, family, motto, draws, rng, centre
        self.U = 4.0 if family == 'duple' else 3.0
        self.scale = scale
        self.bar = self.U / scale if family == 'compound' else self.U     # (one bar of the song, internal beats)
        self.log: list = []
        self.minor = Key(key).minorish
        self.tmode: dict = {}              # (round o6: each theme's skeleton by the mode of its first statement)

    def tail(self, notes, end: float, goal: int | None, pcs) -> list:
        """The statement's landing held to `end` (_held_to) - and, when that holds it over a bar of the song, one
        bar kept and the rest a stepwise answer toward `goal` (TAIL)."""
        notes = _held_to(notes, end)
        if not notes or goal is None:
            return notes
        a, d, p = notes[-1]
        if d <= self.bar + _EPS:
            return notes
        g = TAIL['grid']['scherzo' if self.scale == 2 else self.family] / self.scale
        t = a + self.bar
        n = min(TAIL['max'], int((a + d - t) / g + _EPS))
        if n < 2:
            return notes
        sgn = -1 if goal < p else 1
        run = run_to(_step(p, sgn, pcs), goal, t, n, g, pcs)
        x, _, q = run[-1]
        run[-1] = (x, max(g, a + d - x), q)
        return notes[:-1] + [(a, self.bar, p)] + run

    def free(self, last: int, goal: int, t: float, dur: float, pcs) -> list:
        """A free run of 8ths (or two notes in a short span) over [t, t + dur) from the step after `last` toward
        `goal` - the kernel's answer where the motto is rationed (MOTTO_RATION)."""
        n = max(2, int(round(dur / 0.5)))
        return run_to(_step(last, 1 if goal >= last else -1, pcs), goal, t, n, dur / n, pcs)

    # -- a statement, logged
    def state(self, block: str, t: float, anchor: int, pcs, tf=(), fn: str = 'melody', land=None, fill=None):
        ns = motto_notes(self.m, t, anchor, pcs, tf, land, fill)
        self.log.append(dict({'block': block, 'beat': t, 'tf': '+'.join(sorted(tf)) or 'plain', 'fn': fn,
                              'end': max(a + d for a, d, _ in ns) if ns else t}, **self.node('K1', tuple(tf))))
        return ns

    def node(self, parent: str, ops: tuple, depth: int | None = None, src: str = 'K1') -> dict:
        """A derivation node (the code review's A1): every written statement logs {node, parent, ops, depth, src} -
        the kernel it comes from ('K1' the motto, 'K2' the second theme's) or the node it was derived from."""
        self.nodes = getattr(self, 'nodes', 0) + 1
        return {'node': f"n{self.nodes}", 'parent': parent, 'ops': tuple(ops),
                'depth': len(ops) if depth is None else depth, 'src': src}

    def anchor(self, key: str, sym: str, centre: float | None = None) -> int:
        return _near({_member(sym, self.m['member'])}, centre or self.centre)

    # -- the first theme: a sentence (statement, its answer, fragmentation, cadence)
    def sentence(self, block: str, key: str, t0: float, bars: int, end: str = 'PAC', answer: str | None = None,
                 centre: float | None = None, payoff: bool = False, vary=()):
        """vary (round o4: the recapitulation recomposed - o3's judges: "the return = the exposition's bars"):
        'reharm' the answer over the submediant and the cadence approached from the subdominant, 'invert' the answer
        inverted, 'dot' the statements' even pairs dotted (another rhythm)."""
        if self.scale == 2:                # (round o5: the scherzo's theme is a dance tune - Writer.dance)
            return self.dance(block, key, t0, bars, end=end, answer=answer, centre=centre, vary=vary)
        U, m = self.U, self.m
        if 'invert' in vary:
            answer = 'invert'
        pcs = pcs_of(key)
        tonic = _roman(key, 'I' if not Key(key).minorish else 'i')
        dom = _roman(key, 'V')
        lead = lead_of(m)
        pickup = self.d.get('entry') == 'pickup' and lead <= U - 1.0
        u = 2 if bars >= 8 else 1                                 # bars per phrase unit
        c = centre or self.centre
        a1 = self.anchor(key, tonic, c)
        s0 = t0 + (U - lead if pickup else 0.0)
        mel = []
        n1 = self.state(block, s0, a1, pcs)
        next_start = t0 + u * U + (U - lead if pickup else 0.0)
        ans = answer or self.d.get('answer', 'dominant')
        if ans == 'dominant':
            a2 = min((_step(a1, 4, pcs), _step(a1, -3, pcs)), key=lambda q: abs(q - c))
            tf2 = ()
        elif ans == 'step_up':
            a2, tf2 = _step(a1, 1, pcs), ()
        elif ans == 'step_down':
            a2, tf2 = _step(a1, -1, pcs), ()
        else:
            a2, tf2 = a1, ('invert',)
        frag_at = t0 + 2 * u * U
        n2 = self.state(block, next_start, a2, pcs, tf2, land=None)
        mel += self.tail(n1, next_start, n2[0][2] if n2 else a2, pcs)
        mel += self.tail(n2, frag_at + (U - lead if pickup else 0.0) if bars >= 6 else t0 + bars * U,
                         _step(n2[0][2] if n2 else a2, 1, pcs) if bars >= 6 else None, pcs)
        if bars >= 6:
            # fragmentation: the kernel (the motto's first half bar), rising a step per half bar - the phrase
            # accelerates; at the recapitulation's payoff the first one augmented (a bar)
            fa = n2[0][2] if n2 else a2
            k = 0
            t = frag_at
            stop = t0 + (bars - 2) * U
            # (round o22, SET_PLAN v4: the steps by the piece's shape - FRAG_V4; the old ladder is 'rise')
            fsh = FRAG_V4.get(self.d.get('frag')) if SET_PLAN and SET_PLAN.get('v4') else None
            while t < stop - _EPS:
                if k % 2 == 0:                    # (a step up per bar, the kernel twice in it: SEQ_PAIR)
                    fa = _step(fa, fsh[(k // 2) % len(fsh)] if fsh else 1, pcs)
                aug = payoff and k == 0
                if MOTTO_RATION.get('frag') and k % 2 == 1 and mel:
                    # (round o10 - o9's judges: "the motto's head opens almost every phrase", "about thirty times":
                    # the kernel's answer is a free run toward the next kernel, not the kernel again)
                    mel += self.free(mel[-1][2], _step(fa, 1, pcs), t, U / 2, pcs)
                    t += U / 2
                    k += 1
                    continue
                a_, tf_ = _seq_pair(m, fa, k, pcs)
                mel += self.state(block, t, a_, pcs, ('kernel',) + tf_ + (('augment',) if aug else ()))
                t += U if aug else U / 2
                k += 1
            # the cadence: a run to the goal over ii / IV - V (- I)
            goal_pc = {'PAC': Key(key).tonic, 'HC': (Key(key).tonic + 7) % 12}[end]
            last = mel[-1][2]
            goal = _near({goal_pc}, last)
            g = 0.5
            n = int(round(U / g))
            mel += run_to(last, goal, stop, n, g, pcs)
            mel.append((stop + U, U - (0.5 if end == 'HC' else 0.0), goal))
        mel = _unshake(_mono([n for n in mel if n[0] < t0 + bars * U - _EPS]), pcs)
        if 'dot' in vary:
            mel = _dotted(mel, t0)
        mel = _unrepeat(mel, t0, self.bar, pcs)          # (round o9: no literal restatement - REPEAT)
        minor_ = Key(key).minorish
        forced = {0: 'i' if minor_ else 'I'}
        if ans == 'dominant':
            forced[u] = 'V'
        if 'reharm' in vary:
            forced[u] = 'VI' if minor_ else 'vi'
        if bars >= 6:
            if end == 'PAC':
                forced[(bars - 2, 1)] = 'V'
                forced[bars - 1] = 'I' if not minor_ else 'i'
                if 'reharm' in vary:
                    forced[(bars - 2, 0)] = 'iv' if minor_ else 'IV'
            else:
                forced[bars - 1] = 'V'
        chart = harmonize(mel, key, t0, bars, U, forced, split={bars - 2} if bars >= 6 else None)
        return fit_line(mel, chart, key), chart

    # -- the scherzo's theme: a dance tune in 3/4 (round o5)
    def dance(self, block: str, key: str, t0: float, bars: int, end: str = 'PAC', answer: str | None = None,
              centre: float | None = None, vary=()):
        """The scherzo's first theme (o4's judges: "held notes over oom-pah" - the motto's cell at the compound bar's
        doubled values): a dance in 3/4 bars (DANCE, the cells drawn once per piece: every statement one tune) -
        per phrase of up to 8 song bars the basic idea (2 bars: a lively cell, then a landing cell, on the motto's
        contour), its answer (the sentence's: on the dominant, a step up / down, inverted), the first bar's cell
        sequenced up a step a bar, the cadence (a running bar, the goal); 16 bars and more: an antecedent to a half
        cadence and its consequent home. vary as Writer.sentence's. -> (melody, chart) in internal beats."""
        U, m = self.U, self.m
        sb = U / 2.0                                  # (one 3/4 bar of the song: half the compound bar)
        sbeat = sb / 3.0
        pcs = pcs_of(key)
        minor_ = Key(key).minorish
        I_ = 'i' if minor_ else 'I'
        tonic = _roman(key, I_)
        c = centre or self.centre
        r = random.Random(f"{self.d.get('seed', 0)}:dance")
        i1 = r.randrange(len(DANCE['idea']))
        c1 = DANCE['idea'][i1]
        c2 = DANCE['land'][r.randrange(len(DANCE['land']))]
        crun = DANCE['run'][r.randrange(len(DANCE['run']))]
        cend = DANCE['end'][r.randrange(len(DANCE['end']))]
        # (round o8 - o7's judges: "the scherzo cell restated almost literally about 6 times": the consequent's
        # answer on another idea cell of as many notes, the fragmentation's bars alternate the head and its
        # inversion - DANCE_VARY)
        c1b = next((DANCE['idea'][(i1 + k_) % len(DANCE['idea'])] for k_ in range(1, len(DANCE['idea']))
                    if len(DANCE['idea'][(i1 + k_) % len(DANCE['idea'])]) == len(c1)), c1)
        # (round o9 - o8's judges: "the scherzo's literal restatements", sch_lit 2.5: the consequent's - and a
        # reharmonised return's - basic idea in the other idea cell and another landing cell of as many notes)
        c2b = next((x for x in DANCE['land'] if x != c2 and len(x) == len(c2)), c2)
        ans = 'invert' if 'invert' in vary else (answer or self.d.get('answer', 'dominant'))
        a1 = self.anchor(key, tonic, c)
        nsb = int(round(bars * 2))
        phrases = [8, nsb - 8] if nsb >= 14 else [nsb]

        def cells(cl, x):
            return [(x + on * sbeat, du * sbeat) for on, du in cl]

        def contour(anchor, ps_):
            ms = [q for _, _, q in motto_notes(m, 0.0, anchor, ps_)]
            n = len(c1) + len(c2)
            path = list(ms)
            while len(path) < n:                 # (passing tones into the widest gap; a turn at the end)
                gaps = [(abs(b_ - a_), i) for i, (a_, b_) in enumerate(zip(path, path[1:]))]
                g_, i = max(gaps) if gaps else (0, 0)
                if g_ <= 2:
                    path.insert(len(path) - 1, _step(path[-1], 1, ps_))
                    continue
                if DANCE_FILL == 'neighbour' and len(gaps) > 1:
                    # (round o12 - o11's judges, WBTS 7-22: "G-A-B-C", the leap filled into a scale: the leap kept,
                    # a neighbour note turning away from it before the narrowest step - a cell with a profile)
                    g2, j = min(gaps)
                    a_, b_ = path[j], path[j + 1]
                    path.insert(j + 1, _step(a_, -1 if b_ >= a_ else 1, ps_))
                    continue
                path.insert(i + 1, _step(path[i], 1 if path[i + 1] > path[i] else -1, ps_))
            while len(path) > n:                 # (the first, the highest and the landing kept)
                keep = {0, len(path) - 1, path.index(max(path))}
                i = next(j for j in range(len(path) - 2, 0, -1) if j not in keep)
                path.pop(i)
            return path
        mel, forced, split = [], {0: I_}, set()
        x, bi = t0, 0
        for j, P in enumerate(phrases):
            if P <= 0:
                continue
            last = j == len(phrases) - 1
            goal_end = end if last else 'HC'
            p_end = x + P * sb
            # the basic idea and its answer
            idea = contour(a1, pcs)
            if P < 4:                             # (too short for a cadence: the idea alone)
                rh = cells(c1, x) + cells(c2, x + sb)
                mel += [(a, d, q) for (a, d), q in zip(rh, idea) if a < p_end - _EPS]
                x = p_end
                continue
            self.log.append({'block': block, 'beat': x, 'tf': 'dance', 'fn': 'melody', 'end': x + 2 * sb})
            other = DANCE_VARY['idea'] and (j == 1 or 'reharm' in vary)
            rh = cells(c1b if other else c1, x) + cells(c2b if other else c2, x + sb)
            mel += [(a, d, q) for (a, d), q in zip(rh, idea)]
            y = x + 2 * sb
            if P >= 6:
                if ans == 'invert':
                    alt = [a1 - (q - a1) for q in idea]
                    alt = [_near(pcs, q) for q in alt]
                elif ans == 'dominant':
                    a2 = min((_step(a1, 4, pcs), _step(a1, -3, pcs)), key=lambda q: abs(q - c))
                    alt = contour(a2, pcs_of(key, _roman(key, 'V')))
                    forced[int(round((y - t0) / U))] = 'V'
                else:
                    alt = contour(_step(a1, 1 if ans == 'step_up' else -1, pcs), pcs)
                if j == 1:                        # (the consequent: the answer a step higher than the antecedent's)
                    alt = [_step(q, 1, pcs) for q in alt]
                self.log.append({'block': block, 'beat': y, 'tf': 'dance', 'fn': 'melody', 'end': y + 2 * sb})
                rh = cells(c1b if j == 1 and DANCE_VARY['answer'] else c1, y) + cells(c2, y + sb)
                mel += [(a, d, q) for (a, d), q in zip(rh, alt)]
                y += 2 * sb
            # the fragmentation: the first bar's cell sequenced up a step a bar
            head = idea[:len(c1)]
            k = 1
            while y < p_end - 2 * sb - _EPS:
                up_ = (k - 1) % 3 + 1 + (1 if j == 1 else 0)      # (a step, two, three - then again)
                inv = DANCE_VARY['invert'] and not k % 2
                hd = [head[0] - (q - head[0]) for q in head] if inv else head
                mel += [(a, d, _step(_near(pcs, q), up_, pcs)) for (a, d), q in zip(cells(c1b if inv else c1, y), hd)]
                y += sb
                k += 1
            # the cadence: a running bar to the goal, the goal
            lastp = mel[-1][2] if mel else a1
            if goal_end == 'PAC':
                goal = _near({Key(key).tonic}, lastp)
            else:
                goal = _near({(Key(key).tonic + 7) % 12, (Key(key).tonic + 2) % 12}, lastp)
            rr = cells(crun, y)               # (the run falls into the goal from a tone of V over it)
            Vc = _cpcs(_roman(key, 'V'))
            p0 = min((q for q in range(goal + 3, goal + 10) if q % 12 in Vc), key=lambda q: (abs(q - lastp), q),
                     default=_step(goal, 2, pcs))
            path = run_to(p0, goal, 0.0, len(rr), 1.0, pcs_of(key, _roman(key, 'V')))
            mel += [(a, d, q) for (a, d), (_, _, q) in zip(rr, path)]
            mel += [(a, d, goal) for a, d in cells(cend if goal_end == 'PAC' else ((0, 3),), y + sb)]
            cb = int(round((y - t0) / U - 0.25))     # (the cadence's compound bar: split, V then the goal's chord)
            if goal_end == 'PAC':
                forced[(cb, 0)], forced[(cb, 1)] = 'V', I_
            else:
                forced[(cb, 0)], forced[(cb, 1)] = ('iv' if minor_ else 'IV'), 'V'
            split.add(cb)
            x = p_end
            bi += 1
        mel = _unshake(_mono([n for n in mel if n[0] < t0 + bars * U - _EPS]), pcs)
        if 'dot' in vary:
            mel = _dotted(mel, t0)
        mel = _unrepeat(mel, t0, sb, pcs)                 # (round o9: no literal restatement - REPEAT)
        if 'reharm' in vary and 1 in forced:
            forced[1] = 'VI' if minor_ else 'vi'
        forced = {k_: v for k_, v in forced.items() if (k_ if isinstance(k_, int) else k_[0]) < bars}
        chart = harmonize(mel, key, t0, bars, U, forced, split=split & set(range(bars)))
        return fit_line(mel, chart, key), chart

    # -- the lyrical theme: a period (antecedent to a half cadence, consequent home), long notes, one high point
    def cantilena(self, block: str, key: str, t0: float, bars: int = 8, centre: float | None = None, sk=None,
                  theme: str = 'B', vary: bool = False):
        """theme: the theme's name - its rhythm cells are drawn from its own seed, so every statement of one theme
        (t2, t2b; the river's returns) is the same tune in its key and register. Round o4 (o3's judges: "second themes
        as held notes / broken chords, not a 4+4 tune"): a period whose answer phrase (bars 5-6) takes the head's
        rhythm (bars 1-2), the head a cell of 3+ notes with a leap (LYRIC 'leap'), the one high point in bar 6, the
        rest of the bars drawn from the livelier cells; bars over 8 extend the consequent by a deceptive cadence
        (stretch). vary: the return changed (recap2) - the head kept, the other bars' cells drawn again."""
        U = self.U
        fam = LYRIC[self.family]
        mode = 'minor' if Key(key).minorish else 'major'
        # (round o6 - o5's judges: "a new hymn at the climax": the second theme in the other mode was drawn from the
        # other mode's skeleton - another tune; every statement of a theme now sings its first statement's degrees)
        sm = self.tmode.setdefault(theme, mode)
        sk = stretch(sk or self.d.get('skeleton', {}).get(sm) or SKELETONS[sm][0], bars)
        K = Key(key)
        pcs = pcs_of(key)
        c = centre or self.centre
        tops = []
        for i, dgr in enumerate(sk):
            o = 4 + (dgr - 1) // 7
            p = K.degree(((dgr - 1) % 7) + 1, octave=o)
            while p < c - 7:
                p += 12
            while p > c + 7:
                p -= 12
            if tops and abs(p - tops[-1]) > 7:
                p += -12 if p > tops[-1] else 12
            tops.append(p)
        for i in range(1, len(tops) - 1):           # (a degree twice in a row: the second a third toward the
            if tops[i] == tops[i - 1]:              # next - round q1's E5 E5 | E5 E5 cantilena bars)
                tops[i] = _step(tops[i], 2 if tops[i + 1] > tops[i] else -2, pcs)
        hp = 5 if bars >= 8 else len(sk) - 2                     # the high point: bar 6 sung a step over the rest
        if hp > 0 and tops[hp] <= max(tops[:hp] + tops[hp + 1:]):
            q = tops[hp]
            while q <= max(tops[:hp] + tops[hp + 1:]):
                q = _step(q, 1, pcs)
            tops[hp] = q
        r = random.Random(f"{self.d.get('seed', 0)}:cantilena:{theme}")
        rv = random.Random(f"{self.d.get('seed', 0)}:cantilena:{theme}:vary") if vary else r
        # (round o6 - o5's judges: "episodes not built from the motto - a new oboe tune": the trio's / the rondo's
        # episode's head and the river's theme grow from the motto too)
        derive = self.d.get('derive') if theme in ('B', 'C', 'R') and self.d.get('derive') != 'none' else None
        if derive is None and theme in DERIVE['always']:   # (round o9: the trio / the river tune always derived)
            derive = DERIVE['always'][theme]
        if derive and theme == 'C':                   # (the trio's head the other way: not the second theme's)
            derive = {'plain': 'invert', 'invert': 'plain'}.get(derive, derive)
        cells = list(fam['body'])
        heads = [x for x in cells if len(x) >= 3]
        first = heads[r.randrange(len(heads))]
        second = [x for x in cells if x != first][r.randrange(len(cells) - 1)]
        leap = LYRIC['leap'][r.randrange(len(LYRIC['leap']))]
        n_ = len(sk)
        mel = []
        prev_cell = None
        for i in range(n_):
            a = t0 + i * U
            if i == n_ - 1:
                cell = fam['end'][0]
            elif bars >= 8 and i == 3:
                cell = fam['half'][rv.randrange(len(fam['half']))]
            elif i in (0, 4):
                cell = first
            elif i in (1, 5) and bars >= 8:       # (the answer phrase in the head's rhythm)
                cell = second if not vary or i == 5 else [x for x in cells if x != first][rv.randrange(len(cells) - 1)]
            else:
                opts = [x for x in cells if x != prev_cell and x != first] or cells
                cell = opts[rv.randrange(len(opts))]
            prev_cell = cell
            p0 = tops[i]
            nxt = tops[i + 1] if i + 1 < len(tops) else p0
            n = len(cell)
            if n == 1:
                mel.append((a + cell[0][0], cell[0][1], p0))
                continue
            path = run_to(p0, nxt, 0.0, n, 1.0, pcs) if nxt != p0 else \
                [(0, 1, p0)] + [(k, 1, _step(p0, 1 if k % 2 else -1, pcs) if k < n - 1 or n == 2 else p0)
                                for k in range(1, n)]
            if i in (0, 4) and n >= 3:            # (the head's profile: a leap up, then by step toward the next bar)
                hi_ = _step(p0, leap, pcs)
                rest = run_to(_step(hi_, -1 if nxt < hi_ else 1, pcs), nxt, 0, n - 2, 1, pcs)
                path = [(0, 1, p0), (1, 1, hi_)] + [(j + 2, 1, q) for j, (_, _, q) in enumerate(rest)]
            if i in (0, 4) and derive:        # (round o3: the second theme grows from the motto - its head's
                ms = [q for _, _, q in motto_notes(self.m, 0.0, p0, pcs)][:n]       # contour in long notes)
                if len(ms) == n:
                    path = [(k, 1, p0 + (q - ms[0]) * (-1 if derive == 'invert' else 1)) for k, q in enumerate(ms)]
                    path = [(k, 1, _near(pcs, q)) for k, _, q in path]
            if i in (1, 5) and derive and theme in DERIVE['continue'] and bars >= 8 and n >= 2:
                # (round o9 - o8's judges: "episodes with new tunes unrelated to the theme", KQFD / XBGS: the answer
                # bar goes on with the motto - its notes after the head's, else the head backwards - from this bar)
                ms = [q for _, _, q in motto_notes(self.m, 0.0, p0, pcs)]
                cont = ms[len(first):len(first) + n] if len(ms) >= len(first) + n else ms[:n][::-1]
                if len(cont) == n:
                    sg = -1 if derive == 'invert' else 1
                    path = [(k, 1, _near(pcs, p0 + (q - cont[0]) * sg)) for k, q in enumerate(cont)]
            for (on, du), (_, _, p) in zip(cell, path):
                mel.append((a + on, du, p))
        if hp > 0:                                # (one high point: no other bar reaches it)
            top = max(p for x, _, p in mel if t0 + hp * U - _EPS <= x < t0 + (hp + 1) * U - _EPS)
            mel = [(x, d, p if t0 + hp * U - _EPS <= x < t0 + (hp + 1) * U - _EPS or p < top else
                    max(q for q in range(top - 12, top) if q % 12 in pcs)) for x, d, p in mel]
        if self.scale == 2:                       # (round o5, the scherzo's fast 3/4 - o4's judges: "held notes": the
            sb, out_ = U / 2.0, []                # tune re-rhythmed per bar of the song in DANCE['lyric'] cells - the
            sbeat = sb / 3.0                      # pitches of each bar's start, a line toward the next bar's)
            rl = random.Random(f"{self.d.get('seed', 0)}:lyric3:{theme}")
            multi = [c_ for c_ in DANCE['lyric'] if len(c_) >= 2]
            pattern = [multi[rl.randrange(len(multi))] for _ in range(3)] + [((0, 3),)]
            srt = sorted(mel)

            def at(x):
                return next((p for a, d, p in reversed(srt) if a <= x + _EPS), srt[0][2])
            nsb = int(round(n_ * 2))
            for i in range(nsb):
                x = t0 + i * sb
                p, nx = at(x), at(x + sb)
                cell = ((0, 3),) if i == nsb - 1 else pattern[i % 4]
                path = run_to(p, nx, 0.0, len(cell), 1.0, pcs) if nx != p else \
                    [(0, 1, p)] + [(k_, 1, _step(p, 1, pcs) if k_ % 2 else p) for k_ in range(1, len(cell))]
                out_ += [(x + on * sbeat, du * sbeat, q) for (on, du), (_, _, q) in zip(cell, path)]
            mel = out_
        mel = _unshake(mel, pcs)
        I_ = 'I' if mode == 'major' else 'i'
        forced = {0: I_, n_ - 1: I_}
        if bars >= 8:
            forced[3] = 'V'
            forced[(n_ - 2, 1)] = 'V'
            for i in range(7, n_ - 1):            # (the extension: the deceptive cadence on its submediant bars)
                if sk[i] == 6:
                    forced[i] = 'vi' if mode == 'major' else 'VI'
        chart = harmonize(mel, key, t0, n_, U, forced, split={n_ - 2} if bars >= 8 else None)
        self.log.append({'block': block, 'beat': t0, 'tf': 'cantilena', 'fn': 'melody', 'end': t0 + bars * U,
                         'theme2': True})
        mel = fit_line(mel, chart, key, strict=0.75)
        if hp > 0:                                # (the chord fit kept under the high point too)
            def inside(x):
                return t0 + hp * U - _EPS <= x < t0 + (hp + 1) * U - _EPS
            top = max(p for x, _, p in mel if inside(x))
            mel = [(x, d, p) if inside(x) or p < top else
                   (x, d, max((q for q in range(top - 12, top) if q % 12 in _cpcs(_chart_at(chart, x))),
                              default=top - 1)) for x, d, p in mel]
        return mel, chart

    # -- the climax's counter: the material at its own speed over its augmentation (round o9, APEX_CANON)
    def canon(self, block: str, kind: str, key: str, ch, t0: float, bars: int, mel, theme1=None) -> list:
        """The augmented climax's counter-line: 'theme_aug' the first theme (theme1 = (key, notes from 0, bars)) at its
        own speed, 'augment' the motto at its own values every two bars a step higher each - over the augmented line
        (APEX_CANON 'over'), until the cadence's two bars, fitted to the chords."""
        U = self.U
        stop = t0 + (bars - 2) * U
        pcs = pcs_of(key)
        med = sorted(p for _, _, p in mel)[len(mel) // 2] if mel else self.centre
        goal = med + APEX_CANON['over']
        seg = []
        if kind == 'theme_aug' and theme1:
            k1, ns1, _ = theme1
            sh = Key(key).tonic - Key(k1).tonic
            base = [(a_, d_, p_ + sh) for a_, d_, p_ in ns1]
            if Key(k1).minorish != Key(key).minorish:
                base = _to_mode(base, _transpose_key(k1, sh % 12), key)
            seg = [(t0 + a_, d_, p_) for a_, d_, p_ in base if t0 + a_ < stop - _EPS]
            if seg:
                self.log.append({'block': block, 'beat': t0, 'tf': 'theme', 'fn': 'counter', 'end': stop})
        else:
            x, j = t0, 0
            cont = self.contour()
            while x < stop - _EPS:
                sym = _chart_at(ch, x) or _roman(key, 'i' if Key(key).minorish else 'I')
                rise = sum(cont[i % len(cont)] for i in range(j)) if cont else j * APEX_CANON['rise']
                a = _step(_near({_member(sym, self.m['member'])}, goal), rise, pcs)
                z = min(stop, x + 2 * U)
                st_ = self.state(block, x, a, pcs, (), fn='counter')
                end_ = max((y + d for y, d, _ in st_), default=x)
                if APEX_CANON.get('answer') and end_ <= x + U + _EPS and x + U < z - U / 2:
                    # (round o10 - o9's judges, APPS: "held brass blocks under a violin line": the motto's second bar
                    # empty on top - its inverted head answers it there, a step under its landing)
                    q_ = st_[-1][2] if st_ else a
                    st_ = [(y, min(d, x + U - y), p) for y, d, p in st_] + \
                        self.state(block, x + U, _step(q_, -1, pcs), pcs, ('head', 'invert'), fn='counter',
                                   fill=z - 0.25)
                seg += [(y, min(d, z - 0.25 - y), p) for y, d, p in st_ if y < z - 0.25 - _EPS]
                x, j = x + 2 * U, j + 1
        if not seg:
            return []
        while sum(p for _, _, p in seg) / len(seg) < goal - 3:
            seg = [(a, d, p + 12) for a, d, p in seg]
        while sum(p for _, _, p in seg) / len(seg) > goal + 9:
            seg = [(a, d, p - 12) for a, d, p in seg]
        seg = [(a, min(d, stop - a), p) for a, d, p in seg if a < stop - _EPS]
        return _mono(fit_line(_mono(seg), ch, key, strict=1.5))

    # -- the development: the motto WORKED (round o3, 12 of 14 judges: "the development does not develop the
    # motto") - 2-bar models through a key path, each a technique of DEV_TECH on the piece's own motto
    def develop(self, block: str, keys: list, t0: float, bars: int, tech: str, home: str, theme2=None,
                theme1=None):
        """(melody, counter, chart) of a development block: n = bars // 2 models, model i in keys[i] (bar 1 on its
        I, bar 2 on the next model's V7 - the sequence moves on), the register rising a step per model. tech:
        'sequence' (the whole motto, its inversion answering a bar later in the other choir; the last model
        fragmented), 'fragment' (liquidation: the motto, its head, its kernel twice, the kernel diminished - tossed
        between the choirs bar by bar), 'stretto' (the motto against itself, the second entry a bar, then half a bar
        later), 'combine' (the motto against the second theme: theme2 = (key, notes from 0) - its bars under the
        models), 'bass' (the motto in the bass - the texture's 'theme': 'bass' -, its inversion answering above),
        'theme' (round o6 - o5's judges: "developments not built from the motto, a chromatic chain of arpeggiated
        triads": the first theme's opening two bars - theme1 = (key, notes from 0, bars) - sequenced through the keys,
        imitated a bar later an octave under in the other choir; the second half of the models its first bar only,
        then its kernel - fragmented, liquidated). Round o6: 'sequence' states the whole motto in the first half of
        the models only, then its head answered by its head, the last model its kernel diminished. Round o11
        (DEV_LADDER, dev_stages): every technique states its own unit in at most three models, then the unit shrinks
        - the head and its inversion, the kernel per half bar, the kernel diminished in the last model."""
        U, m = self.U, self.m
        mel, ans, chart = [], [], []
        n = max(1, bars // 2)
        if tech == 'combine' and not theme2:
            tech = 'sequence'
        if tech == 'theme' and not theme1:
            tech = 'fragment'
        stages = dev_stages(tech, n)
        for i in range(n):
            k = keys[i % len(keys)]
            nxt = keys[(i + 1) % len(keys)] if i + 1 < n else home
            pcs = pcs_of(k)
            t = t0 + 2 * i * U
            end = t + 2 * U
            Ik = _roman(k, 'I' if not Key(k).minorish else 'i')
            V7 = _roman(nxt, 'V7')
            ch = [(t, U, Ik), (t + U, U, V7)]
            chart += ch
            pv = pcs_of(nxt, V7)
            low = tech == 'bass'
            rise = 2 * i if n <= 4 else round(6 * i / (n - 1))    # (round o4: a 16-bar development climbs no higher)
            a1 = self.anchor(k, Ik, (50 if low else self.centre - 2) + rise)
            hi = _near(_cpcs(Ik), (self.centre + 2 if low else a1 + 5))

            def fit(ns, z=end, raw=False):
                ns = [(a, min(d, z - 0.25 - a), p) for a, d, p in ns if a < z - 0.25 - _EPS]
                if ns:                            # (a statement kept in a band around the development's register:
                    c_ = (50 if low else self.centre) + rise         # the lines span what one section plays)
                    while max(p for _, _, p in ns) > c_ + 12:
                        ns = [(a, d, p - 12) for a, d, p in ns]
                    while min(p for _, _, p in ns) < c_ - 16:
                        ns = [(a, d, p + 12) for a, d, p in ns]
                if raw and DEV_BASS_RAW:          # (the motto in the bass keeps its intervals in the key)
                    return [(a, max(0.125, d), p) for a, d, p in ns]
                return [(a, max(0.125, d), p) for a, d, p in fit_line([x for x in ns if x[0] < t + U - _EPS], ch, k)
                        + fit_line([x for x in ns if x[0] >= t + U - _EPS], ch, nxt)]
            stage = stages[i]
            rep = 0                                        # (the same stage again: its statements inverted)
            while i - rep - 1 >= 0 and stages[i - rep - 1] == stage:
                rep += 1
            rep %= 2
            if tech == 'theme' and stage <= 1:
                k1, ns1, _ = theme1
                sh = Key(k).tonic - Key(k1).tonic
                seg = [(a_, d_, p_ + sh) for a_, d_, p_ in ns1 if a_ < 2 * U - _EPS]
                if Key(k1).minorish != Key(k).minorish:
                    seg = _to_mode(seg, _transpose_key(k1, sh % 12), k)
                half = stage == 1                          # (the head stage: the first bar only, rising a step)
                if half:
                    seg = [x for x in seg if x[0] < U - _EPS]
                if seg:                                    # (centred on the model's anchor: the line climbs)
                    off = a1 - seg[0][2]
                    off -= 12 * round(off / 12)
                    seg = [(t + a_, d_, p_ + off) for a_, d_, p_ in seg]
                    if half:
                        seg = seg + [(a_ + U, d_, _step(p_, 1, pv)) for a_, d_, p_ in seg]
                    self.log.append({'block': block, 'beat': t, 'tf': 'theme', 'fn': 'melody', 'end': end})
                    mel += fit(seg)
                    imit = [(a_ + (U / 2 if half else U), d_, p_ - 12) for a_, d_, p_ in seg]
                    self.log.append({'block': block, 'beat': t + U / 2 if half else t + U, 'tf': 'theme',
                                     'fn': 'counter', 'end': end})
                    ans += fit(imit)
            elif stage == 0 and tech in ('sequence', 'fragment'):
                mel += fit(self.state(block, t, a1, pcs))
                if tech == 'sequence':
                    ans += fit(self.state(block, t + U, _near(_cpcs(V7), hi - 2), pv, ('invert',), fn='counter'))
            elif stage == 1:                      # (the head inverted, answered by itself - the other way round
                inv = () if rep else ('invert',)  # when the stage goes on: never the same unit three times; a
                #                                   one-bar motto's head is the whole motto - inverted first)
                mel += fit(self.state(block, t, a1, pcs, ('head',) + inv), t + U)
                ans += fit(self.state(block, t + U, _near(_cpcs(V7), a1 + 2), pv,
                                      ('head',) + (('invert',) if rep else ()), fn='counter'))
            elif stage == 2 and DEV_LADDER.get('imitate'):
                # (round o12 - o11's judges: "the development a row of textures, not an argument with the motto",
                # dev_own 0.80 -> 0.67 - the kernel per half bar heard as a figure: the head in imitation - each bar
                # the head (inverted when the stage goes on), its imitation half a bar later a fourth under in the
                # other choir, the pair a step higher a bar later: a stretto of the motto's head)
                for j in range(2):
                    x = t + j * U
                    pk_ = pcs if x < t + U else pv
                    sym_ = Ik if x < t + U else V7
                    a = _near(_cpcs(sym_), _step(a1, j, pk_))
                    tf = ('head',) + (('invert',) if (j + rep) % 2 else ())
                    mel += fit(self.state(block, x, a, pk_, tf), x + U)
                    z_ = min(end, x + U / 2 + U)
                    ans += fit(self.state(block, x + U / 2, _near(_cpcs(sym_), a - 5), pk_, tf, fn='counter'), z_)
            elif stage >= 2:
                per = 2 if stage == 2 else 4
                a = a1
                for j in range(2 * per):          # (the kernel per half bar / quarter bar, a step up per pair,
                    x = t + j * U / per           # strings and winds in turn)
                    if j % 2 == 0:
                        a = _step(a, 1, pcs if x < t + U else pv)
                    tf = ('kernel',) + (('diminish',) if per == 4 else ()) + (('invert',) if (j + rep) % 2 else ())
                    pk_ = pcs if x < t + U else pv
                    if sum(1 for y in motto_notes(m, x, a, pk_, tf) if y[0] < x + U / per - _EPS) < 2:
                        # (round o11: a one-note kernel - a held first beat - is no unit: the head diminished)
                        tf = ('head', 'diminish') + tf[-1:] * ('invert' in tf)
                    ns = fit(self.state(block, x, a, pk_, tf, fn='melody' if j % 2 == 0 else 'counter'),
                             x + U / per + 0.25)
                    (mel if j % 2 == 0 else ans).extend(ns)
            elif tech == 'stretto':
                gap = U if i == 0 else U / 2
                mel += fit(self.state(block, t, a1, pcs))
                ans += fit(self.state(block, t + gap, _near(_cpcs(Ik if gap < U else V7), a1 + 7),
                                      pcs if gap < U else pv, fn='counter'))
            elif tech == 'combine':
                mel += fit(self.state(block, t, a1, pcs), t + U)
                mel += fit(self.state(block, t + U, _near(_cpcs(V7), a1 + 2), pv, ('invert', 'head')))
                k2, b2 = theme2
                sh = Key(k).tonic - Key(k2).tonic
                seg = [(a - 2 * i * U % (8 * U), d, p + sh) for a, d, p in b2
                       if 2 * i * U % (8 * U) - _EPS <= a < 2 * i * U % (8 * U) + 2 * U - _EPS]
                if seg:
                    while max(p for _, _, p in seg) > a1 - 3:
                        seg = [(a, d, p - 12) for a, d, p in seg]
                    while min(p for _, _, p in seg) < 50:
                        seg = [(a, d, p + 12) for a, d, p in seg]
                    ans += fit([(t + a, d, p) for a, d, p in seg])
            elif tech == 'bass':
                mel += fit(self.state(block, t, a1, pcs, fn='bass'), raw=True)
                ans += fit(self.state(block, t + U, _near(_cpcs(V7), hi), pv, ('invert', 'head'), fn='counter'), raw=True)
            else:
                raise ComposeError(f"symphony: development technique {tech!r} unknown ({', '.join(DEV_TECH)})")
        return _mono(mel), _mono(ans), chart

    # -- the development as a PLANNED WALK through the derivation space (DEV_WALK - the code review's A1, round o16)
    def kernel2(self, theme2):
        """The second theme's kernel (Kernel.line of its first bar - two when the first holds under 3 notes)."""
        if not theme2:
            return None
        if getattr(self, '_k2', None) is None or self._k2[0] is not theme2:
            self._k2 = (theme2, Kernel.line(theme2[1], theme2[0], self.family, self.U))
        return self._k2[1]

    def derive(self, block: str, x: float, anchor: int, pcs, K, ops, fn: str = 'melody', parent: str | None = None,
               other=None, depth: int | None = None, tf: str | None = None):
        """One derived statement (kernel K through `ops` from beat x on `anchor`), logged as a derivation node ->
        (notes, node)."""
        ns = K.apply(x, anchor, pcs, tuple(ops), other=other)
        nd = self.node(parent or K.name, tuple(ops), depth, K.name)
        self.log.append(dict({'block': block, 'beat': x, 'tf': tf or ('+'.join(ops) or 'plain'), 'fn': fn,
                              'end': max(a + d for a, d, _ in ns) if ns else x}, **nd))
        return ns, nd

    def walk(self, block: str, keys: list, t0: float, bars: int, home: str, theme2=None, pos=(0.0, 1.0)):
        """(melody, counter, chart, phases, route) of a development block as a planned walk (WALK; DEV_WALK): its phases
        [(start, bars, arrangement, key)] - each one texture -, its segments (the route: per segment the model's
        length, the models, the move, the links, the arrival, the kernel, the op chain and its depth). pos: the
        block's span in the whole development (0-1) - the chains deepen and the register rises toward the
        retransition. The last segment arrives on the home key's dominant (the retransition follows)."""
        W_ = WALK
        U, sc = self.U, self.scale
        rng = random.Random(f"symphony:{self.d.get('seed')}:walk:{block}")
        K1, K2 = Kernel.motto(self.m), self.kernel2(theme2)
        mem = self.__dict__.setdefault('walk_mem', {'used': {}, 'false': False, 'chain': None, 'lines': []})
        # 1. the phases: 1-3, each its arrangement (a texture)
        pmin = max(1, W_['phase']['min'] // sc)
        n_ph = 1 if bars < 2 * pmin else min(W_['phase']['most'], bars // pmin,
                                              3 if bars >= 3 * pmin and rng.random() < 0.5 else 2)
        cuts = [pmin] * n_ph
        for _ in range(bars - pmin * n_ph):
            cuts[rng.randrange(n_ph)] += 1
        arrs = []
        for j in range(n_ph):
            w_ = {a: v * (0.15 if a in arrs else 1.0) for a, v in W_['arrange'].items() if not arrs or a != arrs[-1]}
            if not K2:
                w_.pop('against', None)
            if mem['false'] or (j == 0 and pos[0] < _EPS) or (j == n_ph - 1 and pos[1] > 1 - _EPS):
                w_.pop('false', None)     # (one false entry a piece: never the development's first or last bars)
            arrs.append(_pick(rng, w_))
            mem['false'] = mem['false'] or arrs[-1] == 'false'
        # 2. the segments: models by the shape's lengths, 1-3 a sequence
        shape = W_['shapes'][_pick(rng, {s: 1.0 for s in W_['shapes']})]
        segs, x, si = [], t0, 0
        for j, (nb, arr) in enumerate(zip(cuts, arrs)):
            left, first = nb, True
            while left > 0:
                Lm = min(shape[si % len(shape)], 2 if sc == 2 else 4, left)
                r = _pick(rng, {k: v for k, v in W_['reps'].items() if k * Lm <= left})
                segs.append({'phase': j, 'arr': arr, 'start': x, 'len': Lm, 'reps': r, 'first': first})
                x += Lm * r * U
                left -= Lm * r
                si += 1
                first = False
        # 3. per segment: its key, move, links, arrival, kernel and op chain (deeper toward the retransition)
        d0, d1 = W_['depth']
        prev_mv = None
        for i, sg in enumerate(segs):
            p = pos[0] + (pos[1] - pos[0]) * (sg['start'] - t0) / max(_EPS, bars * U)
            sg['p'] = p
            k = keys[i % len(keys)]
            src = 'K1' if not K2 or sg['arr'] == 'false' else _pick(rng, W_['src'])
            target = max(1, min(5, int(round(d0 + (d1 - d0) * p))))
            prev = mem['chain']
            if prev and prev[0] == src and rng.random() >= W_['branch']:
                chain, parent = list(prev[1]), prev[2] or '__prev__'
            else:
                chain, parent = [], src
            while len(chain) >= target and chain:          # (the unit may grow back: its fragmenting op first)
                fr = [o for o in chain if o in WALK_FRAG]
                chain.remove(fr[0] if fr and sg['len'] >= 2 else chain[rng.randrange(len(chain))])
            while len(chain) < target:
                w_ = {}
                for op, v in W_['ops'].items():
                    if op in chain or any(op in c and set(chain) & (c - {op}) for c in WALK_CONFLICT):
                        continue
                    if (op == 'combine' and src == 'K1' and not K2) or \
                            (op == 'mode' and Key(k).mode not in ('major', 'minor')):
                        continue
                    w_[op] = v * (W_['novel'] if not mem['used'].get(op) else 1.0)
                if not w_:
                    break
                chain.append(_pick(rng, w_))
            if prev and prev[0] == src and tuple(chain) == prev[1] and chain:    # (never the last unit again)
                alt = [o for o in W_['ops'] if o not in chain and not any(
                    o in c and set(chain[:-1]) & (c - {o}) for c in WALK_CONFLICT) and
                    not (o == 'combine' and src == 'K1' and not K2) and o != 'mode']
                if alt:
                    chain[-1] = alt[rng.randrange(len(alt))]
            for o in chain:
                mem['used'][o] = mem['used'].get(o, 0) + 1
            if 'mode' in chain and Key(k).mode in ('major', 'minor'):
                k = _transpose_key(k, 0, 'minor' if Key(k).mode == 'major' else 'major')
            mv = 'up' if sg['reps'] == 1 else _pick(rng, {m: v * (0.3 if m == prev_mv else 1.0)
                                                         for m, v in W_['moves'].items()})
            prev_mv = mv
            sg.update(key=k, src=src, ops=tuple(chain), parent=parent, move=mv,
                      dir=_pick(rng, W_['real']) if mv == 'real' else 0,
                      links=_pick(rng, W_['links']), arrive=_pick(rng, W_['arrive']),
                      answer=_pick(rng, W_['answer']), inner=_pick(rng, W_['inner']),
                      delay=_pick(rng, W_['imit']['delay']), isteps=_pick(rng, W_['imit']['steps']))
            mem['chain'] = (src, tuple(chain), None)
        for i, sg in enumerate(segs):
            sg['goal'] = segs[i + 1]['key'] if i + 1 < len(segs) else home
            if sg['arrive'] == 'deceptive' and i + 1 >= len(segs):
                sg['arrive'] = 'pac'
            if sg['arrive'] == 'deceptive':
                segs[i + 1]['first_rn'] = 'VI' if Key(sg['goal']).minorish else 'vi'
        # 4. the notes and the chords
        mel, ans, chart, zones = [], [], [], []
        for i, sg in enumerate(segs):
            if sg['parent'] == '__prev__':
                sg['parent'] = mem.get('last_node') or sg['src']
            m_, a_, c_, z_ = self._walk_segment(block, sg, home, K1, K2, rng, mem)
            mel += m_
            ans += a_
            chart += c_
            zones += z_
        out_m, out_a = [], []
        for a, b, k, cs in zones:                         # (every note in its zone's scale and chords)
            out_m += fit_line([n for n in mel if a - _EPS <= n[0] < b - _EPS], chart, k, chroma=cs or None)
            out_a += fit_line([n for n in ans if a - _EPS <= n[0] < b - _EPS], chart, k, chroma=cs or None)
        if any(sg['arr'] == 'bass' for sg in segs) and DEV_BASS_RAW:     # (the bass keeps its intervals)
            low = {(round(n[0], 4)) for sg in segs if sg['arr'] == 'bass' for n in mel
                   if sg['start'] - _EPS <= n[0] < sg['start'] + sg['len'] * sg['reps'] * U - _EPS}
            out_m = [n for n in out_m if round(n[0], 4) not in low] + \
                [n for n in mel if round(n[0], 4) in low]
        mem['chain'] = (segs[-1]['src'], segs[-1]['ops'], mem.get('last_node'))
        phases, a0 = [], t0
        for j, nb in enumerate(cuts):
            phases.append((a0, nb, arrs[j], next(sg['key'] for sg in segs if sg['phase'] == j)))
            a0 += nb * U
        route = [{k_: (v if not isinstance(v, tuple) else list(v)) for k_, v in sg.items()
                  if not k_.startswith('_') and k_ not in ('p', 'first')} for sg in segs]
        for r_, sg in zip(route, segs):
            r_['depth'] = len(sg['ops'])
            r_['shape'] = shape
        return sorted(out_m), sorted(out_a), chart, phases, route

    def _walk_segment(self, block, sg, home, K1, K2, rng, mem):
        """One segment of the walk -> (melody, counter, chart rows, fit zones [(start, end, key, chromatic syms)])."""
        W_ = WALK
        U = self.U
        k, goal, Lm, reps, arr = sg['key'], sg['goal'], sg['len'], sg['reps'], sg['arr']
        Kx = K1 if sg['src'] == 'K1' else K2
        Ko = (K2 if sg['src'] == 'K1' else K1) or K1
        mode_ = 'minor' if Key(k).minorish else 'major'
        degs = WALK_DEG[sg['move']]
        rot = -2 if 'reharm' in sg['ops'] else 0
        deg = [((degs[r % len(degs)] - 1 + rot) % 7) + 1 for r in range(reps)]
        rns = [WALK_ROMAN[mode_][d] for d in deg]
        if sg.get('first_rn'):
            rns[0] = sg['first_rn']
        t_s = sg['start']
        z_s = t_s + Lm * reps * U
        x_arr = z_s - U                                   # (the arrival bar)
        low = arr == 'bass'
        centre = (50 if low else self.centre - 3) + int(round(6 * sg['p']))
        pk = pcs_of(k)
        a_base = _near({_member(_roman(k, rns[0]), self.m['member'])}, centre)
        mel, ans, unit_nodes = [], [], []
        for r in range(reps):
            x0 = t_s + r * Lm * U
            xe = x0 + Lm * U
            if sg['move'] == 'real':
                rk = _transpose_key(k, r * sg['dir'])
                anc = a_base + r * sg['dir']
            else:
                rk = k
                off = (deg[r] - deg[0]) % 7
                off = off - 7 if off > 3 else off
                anc = _step(a_base, off, pk) if r else a_base
            pr = pcs_of(rk, _roman(rk, rns[r] if sg['move'] != 'real' else rns[0]))
            xu = x0
            m_rep = []
            if arr == 'false' and sg['first'] and r == 0:
                # (the false entry: the motto's head plain in the home key - a return too early - broken off)
                Ih = _roman(home, 'i' if Key(home).minorish else 'I')
                fa = _near({_member(Ih, self.m['member'])}, self.centre)
                z_f = x0 + (U if Lm >= 2 else Lm * U) - 0.25
                ns_, _ = self.derive(block, x0, fa, pcs_of(home), K1, ('head',), tf='false')
                m_rep += [(a, min(d, z_f - a), p) for a, d, p in ns_ if a < z_f - _EPS]
                sg['false_at'] = (x0, Ih)
                if Lm < 2:
                    mel += m_rep
                    continue
                xu = x0 + U
            ops = self._fit_ops(Kx, sg['ops'], xe - xu - 0.25)
            ns_, nd = self.derive(block, xu, anc, pr, Kx, ops, fn='bass' if low else 'melody',
                                  parent=unit_nodes[0]['node'] if unit_nodes else sg['parent'], other=Ko)
            if not unit_nodes:
                mem['last_node'] = nd['node']
            unit_nodes.append(nd)
            m_rep += [(a, min(d, xe - 0.25 - a), p) for a, d, p in ns_ if a < xe - 0.25 - _EPS]
            # the model's rest: the unit's inner derivations, sequenced toward the next model
            sgn = 1 if sg['move'] in ('up', 'real') else -1 if sg['move'] in ('down', 'thirds') else 0
            inner = [ops + ((sg['inner'],) if sg['inner'] not in ops else ()), ops + ('frag2',) if
                     'frag2' not in ops and not set(ops) & {'head', 'kernel', 'frag3'} else ops + ('invert',)]
            xa = xu + (U if Lm >= 2 else U / 2)      # (the call's answer: the call rests under it)
            m_end = xa if arr in ('call', 'false') and xa < xe - 0.5 else xe
            m_rep = [(a, min(d, m_end - 0.25 - a), p) for a, d, p in m_rep if a < m_end - 0.25 - _EPS] or m_rep[:1]
            m_rep = self._fill(block, Kx, m_rep, inner, m_end, pr, sgn, 'bass' if low else 'melody', nd, Ko)
            m_rep = self._band(m_rep, centre)
            mel += m_rep
            # the counter-line
            c_rep = []
            if arr in ('call', 'false'):
                if xa < xe - 0.5:
                    o2 = self._fit_ops(Kx, ops + ((sg['answer'],) if sg['answer'] not in ops else ()), xe - xa - 0.25)
                    ns3, nd3 = self.derive(block, xa, _step(anc, 2, pr), pr, Kx, o2, fn='counter', parent=nd['node'],
                                           other=Ko, depth=nd['depth'] + 1)
                    c_rep = [(a, min(d, xe - 0.25 - a), p) for a, d, p in ns3 if a < xe - 0.25 - _EPS]
                    c_rep = self._fill(block, Kx, c_rep, [o2 + ('frag2',) if 'frag2' not in o2 else o2], xe, pr,
                                       -sgn or 1, 'counter', nd3, Ko)
                    c_rep = self._band(c_rep, centre + 3)
                    mem['lines'].append((nd3['depth'], 1, c_rep, xa, rk, nd3))
            elif arr == 'imitate':
                dl = sg['delay'] * U
                c_rep = [(a + dl, min(d, xe - 0.25 - a - dl), _step(p, sg['isteps'], pr)) for a, d, p in m_rep
                         if a + dl < xe - 0.25 - _EPS]
                if c_rep:
                    self.log.append(dict({'block': block, 'beat': xu + dl, 'tf': 'canon', 'fn': 'counter',
                                          'end': xe}, **self.node(nd['node'], nd['ops'], nd['depth'], Kx.name)))
                    mem['lines'].append((nd['depth'], 0, c_rep, xu + dl, rk, nd))
            elif arr in ('against', 'bass'):
                o2 = ('head', 'augment') if arr == 'bass' else ('augment',) if Lm >= 2 else ()
                o2 = self._fit_ops(Ko, o2, xe - x0 - 0.25)
                ca = _near({_member(_roman(rk, rns[r] if sg['move'] != 'real' else rns[0]), self.m['member'])},
                           self.centre + 2 if arr == 'bass' else centre - 8)
                ns3, nd3 = self.derive(block, x0, ca, pr, Ko, o2, fn='counter', other=Kx)
                c_rep = [(a, min(d, xe - 0.25 - a), p) for a, d, p in ns3 if a < xe - 0.25 - _EPS]
                c_rep = self._fill(block, Ko, c_rep, [o2 + ('invert',), o2], xe, pr, -sgn or -1, 'counter', nd3, Kx)
                c_rep = self._band(c_rep, self.centre + 2 if arr == 'bass' else max(55, centre - 8))
                mem['lines'].append((nd3['depth'], 1, c_rep, x0, rk, nd3))
            ans += c_rep
            if not low:
                mem['lines'].append((nd['depth'], 0, [n for n in m_rep if n[0] < xu + 2 * U - _EPS], xu, rk, nd))
        # the chords: the models' degrees (diatonic) or keys (real), the links, the arrival in the goal
        rows, zones = [], []
        csyms = set()
        nbh = Lm * reps - 1
        f_at = sg.get('false_at')
        if f_at:
            rows.append((f_at[0], U, f_at[1]))
            zones.append((f_at[0], f_at[0] + U, home, set()))
        h0 = 1 if f_at else 0
        if sg['move'] == 'real':
            for r in range(reps):
                rk = _transpose_key(k, r * sg['dir'])
                b0, b1 = max(h0, r * Lm), min(nbh, (r + 1) * Lm)
                if b1 > b0:
                    x0 = t_s + b0 * U
                    ns_ = [n for n in mel if x0 - _EPS <= n[0] < t_s + b1 * U - _EPS]
                    rows += harmonize(ns_, rk, x0, b1 - b0, U, {0: rns[0]} if b0 == r * Lm else None)
                    zones.append((x0, t_s + b1 * U, rk, set()))
        elif nbh > h0:
            forced, split = {}, set()
            x0 = t_s + h0 * U
            for r in range(reps):
                b = r * Lm - h0
                if b < 0 or b >= nbh - h0:
                    continue
                ap = WALK_APPLIED.get(deg[r]) if sg['links'] == 'applied' and r > 0 else None
                if ap and chroma_fits(k, ap) and rns[r] in chroma_targets(k, ap) and b >= 1:
                    forced[(b - 1, 1)] = (ap,)
                    forced[(b, 0)] = rns[r]
                    split |= {b - 1, b}
                    csyms.add(chroma_symbol(k, ap))
                else:
                    forced[b] = rns[r]
            ns_ = [n for n in mel if x0 - _EPS <= n[0] < x_arr - _EPS]
            rows += harmonize(ns_, k, x0, nbh - h0, U, forced, split=split)
            zones.append((x0, x_arr, k, csyms))
        Vg7, Vg = _roman(goal, 'V7'), _roman(goal, 'V')
        cs2 = set()
        how = sg['arrive']
        if how == 'chroma':
            cands = [rn for rn in CHROMA_PRE['V7'] if chroma_fits(goal, rn) and 'V7' in chroma_targets(goal, rn)]
            if cands:
                sy = chroma_symbol(goal, cands[rng.randrange(len(cands))])
                rows += [(x_arr, U / 2, sy), (x_arr + U / 2, U / 2, Vg7)]
                cs2.add(sy)
            else:
                how = sg['arrive'] = 'pac'
        if how in ('pac', 'deceptive'):
            Kg = Key(goal)
            pre = 'IV' if Kg.mode == 'dorian' else 'iv' if Kg.minorish else 'ii'
            rows += [(x_arr, U / 2, _roman(goal, pre)), (x_arr + U / 2, U / 2, Vg7)]
        elif how == 'hc':
            rows.append((x_arr, U, Vg))
        if f_at and nbh < 1:                              # (a one-bar false entry: its own chord, no arrival)
            rows = [r_ for r_ in rows if r_[0] < x_arr - _EPS]
        else:
            zones.append((x_arr, z_s, goal, cs2))
        return mel, ans, rows, zones

    def _fit_ops(self, K, ops, room: float) -> tuple:
        """ops with the next fragmenting op (WALK_FRAG, then 'diminish') added while the statement outlasts `room`
        beats."""
        ops = tuple(ops)
        for fb in WALK_FRAG + ('diminish',):
            if K.span(ops) <= room + _EPS:
                break
            if fb in ops or any(fb in c and set(ops) & (c - {fb}) for c in WALK_CONFLICT):
                continue
            ops = ops + (fb,)
        return ops

    def _fill(self, block, K, line, cycle, xe: float, pcs, sgn: int, fn: str, nd, other=None) -> list:
        """The model's rest after its unit (`line`): the next statements of `cycle` (op chains, in turn) from where
        the line ends (the next half beat), each from a step past its last note (sgn: up, down; 0 in turn), the line
        legato into each (a gap of 2 beats at most closed), until the model's end (xe) - its last note held toward the
        next model."""
        out = list(line)
        if not out:
            return out
        for c in range(2 * int(round((xe - out[0][0]) / self.U)) + 2):
            y = 0.5 * math.ceil(max(a + d for a, d, _ in out) / 0.5 - _EPS)
            if y > xe - 1.0 + _EPS:
                break
            ops = self._fit_ops(K, cycle[c % len(cycle)], xe - y - 0.25)
            sg_ = sgn or (1 if c % 2 == 0 else -1)
            ns, _ = self.derive(block, y, _step(out[-1][2], sg_, pcs), pcs, K, ops, fn=fn, parent=nd['node'],
                                other=other, depth=nd['depth'] + 1)
            ns = [(a, min(d, xe - 0.25 - a), p) for a, d, p in ns if a < xe - 0.25 - _EPS]
            if not ns:
                break
            a, d, p = out[-1]
            if 0 < ns[0][0] - (a + d) <= 2.0 + _EPS:
                out[-1] = (a, ns[0][0] - a, p)
            out += ns
        a, d, p = out[-1]
        out[-1] = (a, max(d, min(xe - 0.25 - a, 2.0)), p)
        return out

    def _band(self, ns, centre: float) -> list:
        """A statement kept in a band around the register (the old development's fit: an octave over, 16 under)."""
        if ns:
            while max(p for _, _, p in ns) > centre + 12:
                ns = [(a, d, p - 12) for a, d, p in ns]
            while min(p for _, _, p in ns) < centre - 16:
                ns = [(a, d, p + 12) for a, d, p in ns]
        return ns

    # -- DEV_WALK v2 (round o17): the development block as ONE argument - worked processes, no panels
    def walk2(self, block: str, keys: list, t0: float, bars: int, home: str, theme2=None, pos=(0.0, 1.0),
              over=None):
        """(melody, counter, chart, phases, route, over) of a development block as WALK2's worked processes (DEV_WALK
        v2, round o17 - o16's judges: "4-6 bar panels, each a new colour", "unrelated material"): the block stays one
        block (one texture family, its colour growing at phrase boundaries - WALK2 'tex'); it holds 1-3 PROCESSES of
        8-12 song bars each, drawn per piece: 'sequence' (the unit 2-3 times as a sequence, then its head and kernel
        driving into the arrival), 'stretto' (the subject in imitation, the entries closer and closer - two bars, a
        bar, half a bar - into the arrival), 'against' (the motto's unit over the second theme's head, sequenced),
        'bass' (the unit in the bass, a counter entering over it). Every process rises in register and density toward
        its goal (a cadence in the next key, a half cadence, a chromatic predominant; the last one the home key's
        dominant) and its level climbs (the 'dyn' ramp per process). The unit's op chain is at most WALK2 'cap' ops
        deep with one interval op at most (the motto's head stays audible); a model's rest is its last note held,
        then rests. A false entry only after the thinning that ends the process before it. `over`: the block's
        overrides (the 'storm' block keeps its brass) -> the returned over with the walk's 'tex' and 'dyn'."""
        W_ = WALK2
        U, sc = self.U, self.scale
        rng = random.Random(f"symphony:{self.d.get('seed')}:walk2:{block}")
        K1, K2 = Kernel.motto(self.m), self.kernel2(theme2)
        mem = self.__dict__.setdefault('walk_mem', {'used': {}, 'false': False, 'chain': None, 'lines': []})
        mem.setdefault('procs', {})
        mem.setdefault('ki', 0)
        over = dict(over or {})
        storm = 'dyn' in over and 'dialogue_brass' in (over.get('tex') or {})
        song = bars * sc
        lo, hi = W_['bars']
        n = max(1, min(song // lo, math.ceil(song / hi), W_['most']))
        base = bars // n
        cuts = [base] * n
        cuts[-1] += bars - base * n
        Lm = W_['model'][sc]
        kinds = []
        for j in range(n):
            w_ = {}
            for kd, v in W_['procs'].items():
                if (kd == 'against' and not K2) or (kd == 'bass' and (n > 1 or storm)) or (kinds and kd == kinds[-1]):
                    continue
                v *= W_['reuse'] if mem['procs'].get(kd) else 1.0
                if j == n - 1 and pos[1] > 1 - _EPS and kd == 'stretto':
                    v *= W_['drive']
                w_[kd] = v
            kd = _pick(rng, w_)
            kinds.append(kd)
            mem['procs'][kd] = mem['procs'].get(kd, 0) + 1
        procs, x = [], t0
        for j, (nb, kd) in enumerate(zip(cuts, kinds)):
            k = keys[mem['ki'] % len(keys)]
            mem['ki'] += 1
            p = pos[0] + (pos[1] - pos[0]) * (x - t0) / max(_EPS, bars * U)
            src = 'K2' if K2 and kd == 'sequence' and rng.random() < W_['k2'] else 'K1'
            ops = self._walk2_ops(rng, mem, kd, src, k, K2, p)
            if 'mode' in ops and Key(k).mode in ('major', 'minor'):
                k = _transpose_key(k, 0, 'minor' if Key(k).mode == 'major' else 'major')
            false = bool(j > 0 and not mem['false'] and kd != 'bass' and rng.random() < W_['false'])
            mem['false'] = mem['false'] or false
            reps = max(1, min(W_['states'], (nb - (1 if false else 0) - 1) // Lm))
            procs.append({'phase': j, 'arr': kd, 'start': x, 'bars': nb, 'len': Lm, 'reps': reps, 'key': k,
                          'src': src, 'ops': ops, 'p': p, 'false': false,
                          'move': _pick(rng, W_['moves']) if kd != 'stretto' else 'imitate',
                          'links': _pick(rng, W_['links']), 'arrive': _pick(rng, W_['arrive']),
                          'isteps': _pick(rng, W_['isteps'])})
            x += nb * U
        for j, pr in enumerate(procs):
            pr['goal'] = procs[j + 1]['key'] if j + 1 < len(procs) else home
            if pr['arrive'] == 'deceptive' and j + 1 >= len(procs):
                pr['arrive'] = 'pac'
            if pr['arrive'] == 'deceptive':
                procs[j + 1]['first_rn'] = 'VI' if Key(pr['goal']).minorish else 'vi'
            if j + 1 < len(procs) and procs[j + 1]['false']:
                pr['thin'] = True                # (the thinning before the false entry: the arrival breaks off)
        mel, ans, chart, zones = [], [], [], []
        for pr in procs:
            m_, a_, c_, z_ = self._walk2_proc(block, pr, home, K1, K2, mem)
            mel += m_
            ans += a_
            chart += c_
            zones += z_
        out_m, out_a = [], []
        for a, b, k, cs in zones:
            seg_m = [nn for nn in mel if a - _EPS <= nn[0] < b - _EPS]
            low = any(pr['arr'] == 'bass' and pr['start'] - _EPS <= a < pr['start'] + pr['bars'] * U - _EPS
                      for pr in procs)
            out_m += seg_m if low and DEV_BASS_RAW else fit_line(seg_m, chart, k, chroma=cs or None)
            out_a += fit_line([nn for nn in ans if a - _EPS <= nn[0] < b - _EPS], chart, k, chroma=cs or None)
        phases = [(pr['start'], pr['bars'], pr['arr'], pr['key']) for pr in procs]
        route = [{k_: (list(v) if isinstance(v, tuple) else v) for k_, v in pr.items() if k_ != 'p'} for pr in procs]
        for r_ in route:
            r_['depth'] = len(r_['ops'])
        # the block's colour (one texture family) and its level: a ramp per process, the next process a step under
        # where the one before arrived (after a thinning: softer still)
        tex = dict(over['tex']) if storm else dict(W_['tex'][kinds[0]])
        L = bars * U
        dyn = []
        for j, pr in enumerate(procs):
            f0, f1 = (pr['start'] - t0) / L, (pr['start'] - t0 + pr['bars'] * U) / L
            a_lv = W_['levels'][0] if j == 0 or pr['false'] else W_['levels'][1]
            dyn += [(round(f0, 4), a_lv, 'step'), (round(max(f0, f1 - 0.02) if j + 1 < n else 1.0, 4),
                                                 W_['levels'][2])]
        if storm and over.get('dyn'):
            dyn = list(over['dyn'])
        over.update(tex=tex, dyn=dyn)
        return _mono(sorted(out_m)), _mono(sorted(out_a)), chart, phases, route, over

    def _walk2_ops(self, rng, mem, kd: str, src: str, key: str, K2, p: float) -> tuple:
        """A process's unit: an op chain of WALK2 'depth' ops (by the development's progress p), no WALK_CONFLICT
        pair, one interval op at most, ops the piece has not used preferred; the stretto's subject one op at most
        (WALK2 'subject')."""
        W_ = WALK2
        d = _pick(rng, W_['depth'][0 if p < 0.5 else 1])
        if kd == 'stretto':
            d = min(d, 1)
        chain = []
        while len(chain) < d:
            w_ = {}
            for op, v in W_['ops'].items():
                if op in chain or any(op in c and set(chain) & (c - {op}) for c in WALK_CONFLICT):
                    continue
                if op in W_['interval'] and set(chain) & set(W_['interval']):
                    continue
                if (op == 'combine' and not K2) or (op == 'mode' and Key(key).mode not in ('major', 'minor')):
                    continue
                if kd == 'stretto' and op not in W_['subject']:
                    continue
                w_[op] = v * (W_['novel'] if not mem['used'].get(op) else 1.0)
            if not w_:
                break
            chain.append(_pick(rng, w_))
        for o in chain:
            mem['used'][o] = mem['used'].get(o, 0) + 1
        return tuple(chain)

    def _cap_ops(self, K, ops, room: float) -> tuple:
        """ops fitted to `room` beats (_fit_ops) and kept at WALK2 'cap' ops: the fragmenting op first."""
        out = self._fit_ops(K, ops, room)
        cap = WALK2['cap']
        if len(out) > cap:
            fr = [o for o in out if o in WALK_FRAG + ('diminish',)]
            keep = [o for o in out if o not in fr]
            out = tuple((fr[:1] + keep)[:cap])
        return tuple(out)

    def _band2(self, ns, centre: float) -> list:
        """A statement moved by octaves so that its middle (the median pitch) sits nearest the register's centre -
        an interval op that widens the line keeps it where the line is heard (WALK2; _band keeps the old fit)."""
        if not ns:
            return ns
        ps = sorted(p for _, _, p in ns)
        med = ps[len(ps) // 2]
        k = int(round((centre - med) / 12.0))
        while max(ps) + 12 * k > WALK2['top']:
            k -= 1
        return [(a, d, p + 12 * k) for a, d, p in ns]

    def _walk2_proc(self, block, pr, home, K1, K2, mem):
        """One WALK2 process -> (melody, counter, chart rows, fit zones [(start, end, key, chromatic syms)])."""
        W_ = WALK2
        U = self.U
        k, goal, P, kd, Lm = pr['key'], pr['goal'], pr['bars'], pr['arr'], pr['len']
        t_s = pr['start']
        z_s = t_s + P * U
        x_arr = z_s - U                                   # (the arrival bar)
        low = kd == 'bass'
        Kx = K2 if pr['src'] == 'K2' else K1
        Ko = (K1 if pr['src'] == 'K2' else K2) or K1
        pk = pcs_of(k)
        mode_ = 'minor' if Key(k).minorish else 'major'
        c0 = 50 if low else self.centre - 5

        def centre(x):                                     # (the register rises toward the goal)
            return c0 + W_['rise'] * (x - t_s) / max(_EPS, P * U)
        mel, ans, rows, zones = [], [], [], []
        x_c = t_s
        if pr['false']:
            # (the false entry, after the thinning: the motto's head plain in the home key - a return too early -,
            # broken off; the process goes on from the next bar)
            Ih = _roman(home, 'i' if Key(home).minorish else 'I')
            fa = _near({_member(Ih, self.m['member'])}, self.centre)
            z_f = t_s + 0.75 * U
            ns_, _ = self.derive(block, t_s, fa, pcs_of(home), K1, ('head',), tf='false')
            mel += [(a, min(d, z_f - a), q) for a, d, q in ns_ if a < z_f - _EPS]
            rows.append((t_s, U, Ih))
            zones.append((t_s, t_s + U, home, set()))
            x_c = t_s + U
        csyms = set()
        parent = pr['src']
        if kd == 'stretto':
            # the subject in imitation, the entries closer and closer: two entries a subject's length apart (the
            # exposition), two at half of it (the stretto: they overlap), the head at half the subject, the kernel
            # half a bar apart into the arrival - each new pair a step higher
            subj = pr['ops']
            span = x_arr - x_c
            hb = U / 2

            def half(v):
                return max(hb, hb * math.ceil(v / hb - _EPS))
            s = min(Lm * U, max(U, half(K1.span(subj))))
            tail = U if span >= 3 * U - _EPS else hb
            body = span - tail
            items = []
            for g, what in ((s, 'subj'), (s, 'subj'), (half(s / 2), 'subj'), (half(s / 2), 'subj')):
                if body - g >= -_EPS:
                    items.append([g, what])
                    body -= g
            gh = half(s / 2)
            while body >= gh - _EPS:
                items.append([gh, 'head'])
                body -= gh
            if body > _EPS:
                if items:
                    items[-1][0] += body
                else:
                    tail += body
            items += [[hb, 'kernel'] for _ in range(int(tail / hb + _EPS))]
            gaps = [g for g, _ in items]
            I_k = _roman(k, 'i' if Key(k).minorish else 'I')
            last_m = _near({_member(I_k, self.m['member'])}, centre(x_c))
            x = x_c
            inv = tuple(o for o in subj if o == 'invert')
            for i, (g, what) in enumerate(items):
                voice = i % 2
                ops = subj if what == 'subj' else (what,) + inv
                room = g + (gaps[i + 1] if i + 1 < len(gaps) else 0.0)
                ops = self._cap_ops(K1, ops, room - 0.25)
                if voice == 0 and i >= 2:
                    last_m = _step(last_m, 1, pk)
                anc = last_m if voice == 0 else _step(last_m, pr['isteps'], pk)
                ns_, nd = self.derive(block, x, anc, pk, K1, ops, fn='melody' if voice == 0 else 'counter',
                                      parent=parent, other=Ko)
                parent = nd['node']
                z = min(x_arr - 0.25, x + room)
                ns_ = [(a, min(d, z - a), q) for a, d, q in ns_ if a < z - _EPS]
                if ns_:
                    a, d, q = ns_[-1]
                    ns_[-1] = (a, max(d, min(z - a, d + W_['hold'])), q)
                ns_ = self._band2(ns_, centre(x) + (0 if voice == 0 else -5))
                (mel if voice == 0 else ans).extend(ns_)
                mem['lines'].append((nd['depth'], voice, [y for y in ns_ if y[0] < x + 2 * U - _EPS], x, k, nd))
                x += g
            nb_ = int(round((x_arr - x_c) / U))
            if nb_ >= 1:
                ns_h = [y for y in mel + ans if x_c - _EPS <= y[0] < x_arr - _EPS]
                rows += harmonize(sorted(ns_h), k, x_c, nb_, U, {0: 'i' if Key(k).minorish else 'I'})
                zones.append((x_c, x_arr, k, set()))
        else:
            degs = W_['deg'][pr['move']]
            rot = -2 if 'reharm' in pr['ops'] else 0
            S = pr['reps']
            deg = [((degs[r % len(degs)] - 1 + rot) % 7) + 1 for r in range(S)]
            rns = [WALK_ROMAN[mode_][d] for d in deg]
            if pr.get('first_rn'):
                rns[0] = pr['first_rn']
            a_base = _near({_member(_roman(k, rns[0]), self.m['member'])}, centre(x_c))
            dirs = W_['real']
            rk = k
            for r in range(S):
                x0 = x_c + r * Lm * U
                xe = x0 + Lm * U
                if pr['move'] == 'real':
                    rk = _transpose_key(k, r * dirs)
                    anc = a_base + r * dirs
                    pr_ = pcs_of(rk, _roman(rk, rns[0]))
                    sym_r = _roman(rk, rns[0])
                else:
                    off = (deg[r] - deg[0]) % 7
                    off = off - 7 if off > 3 else off
                    anc = _step(a_base, off, pk) if r else a_base
                    pr_ = pcs_of(k, _roman(k, rns[r]))
                    sym_r = _roman(k, rns[r])
                ops = self._cap_ops(Kx, pr['ops'], Lm * U - 0.25)
                ns_, nd = self.derive(block, x0, anc, pr_, Kx, ops, fn='bass' if low else 'melody', parent=parent,
                                      other=Ko)
                parent = nd['node']
                ns_ = [(a, min(d, xe - 0.25 - a), q) for a, d, q in ns_ if a < xe - 0.25 - _EPS]
                if ns_:                                   # (the model's rest: its last note held, then rests)
                    a, d, q = ns_[-1]
                    ns_[-1] = (a, max(d, min(xe - 0.25 - a, d + W_['hold'])), q)
                ns_ = self._band2(ns_, centre(x0))
                xh = x0 + Lm * U / 2
                if kd == 'against' and r >= 1 and Lm >= 2 and ns_ and ns_[-1][0] < xh - _EPS:
                    # (over the second theme's held head the call answers itself: its head inverted - denser
                    # from the second model on)
                    e_ops = self._cap_ops(Kx, ('head',) + (() if 'invert' in ops else ('invert',)), xe - xh - 0.25)
                    ns2, _ = self.derive(block, xh, _step(ns_[-1][2], 1, pr_), pr_, Kx, e_ops, parent=nd['node'],
                                         other=Ko)
                    ns2 = [(a, min(d, xe - 0.25 - a), q) for a, d, q in ns2 if a < xe - 0.25 - _EPS]
                    a, d, q = ns_[-1]
                    ns_[-1] = (a, min(d, xh - a), q)
                    ns_ = ns_ + self._band2(ns2, centre(x0) + 2)
                mel += ns_
                if not low:
                    mem['lines'].append((nd['depth'], 0, [y for y in ns_ if y[0] < x0 + 2 * U - _EPS], x0, rk, nd))
                # the counter: density grows model by model
                c_rep, nd3 = [], None
                if kd == 'against':
                    o2 = self._cap_ops(Ko, ('augment',) if Lm >= 2 else (), Lm * U - 0.25)
                    ca = _near({_member(sym_r, self.m['member'])}, centre(x0) - 9)
                    c_rep, nd3 = self.derive(block, x0, ca, pr_, Ko, o2, fn='counter', parent=nd['node'], other=Kx)
                    c_rep = self._band2(c_rep, max(55, centre(x0) - 9))
                else:                                     # (the answer half a model late, then a quarter, an
                    dl = Lm * U / 2 ** (r + 1)            # eighth: the call and its answer overlap more and more)
                    if kd == 'bass':
                        o2, Kc = ('head',), Ko
                        ca = _near({_member(sym_r, self.m['member'])}, self.centre + 2)
                    else:
                        o2 = tuple(o for o in ops if o != 'invert') if 'invert' in ops else ops + ('invert',)
                        Kc = Kx
                        ca = _step(anc, pr['isteps'], pr_)
                    o2 = self._cap_ops(Kc, o2, xe - x0 - dl - 0.25)
                    c_rep, nd3 = self.derive(block, x0 + dl, ca, pr_, Kc, o2, fn='counter', parent=nd['node'],
                                             other=Kx if Kc is Ko else Ko)
                    c_rep = self._band2(c_rep, (self.centre + 2) if kd == 'bass' else centre(x0) - 5)
                c_rep = [(a, min(d, xe - 0.25 - a), q) for a, d, q in c_rep if a < xe - 0.25 - _EPS]
                if c_rep:
                    a, d, q = c_rep[-1]
                    c_rep[-1] = (a, max(d, min(xe - 0.25 - a, d + W_['hold'])), q)
                    ans += c_rep
                    mem['lines'].append((nd3['depth'], 1, c_rep, c_rep[0][0], rk, nd3))
            # the drive: the unit's head, then its kernel, the two lines in turn a step higher each pair - denser
            # toward the arrival
            xd = x_c + S * Lm * U
            dk = rk if pr['move'] == 'real' else k
            pd = pcs_of(dk)
            nh = int(round((x_arr - xd) / U))
            a_d = _step(a_base + ((S - 1) * dirs if pr['move'] == 'real' else 0), 1, pd)
            inv = ('invert',) if 'invert' in pr['ops'] else ()
            x, j = xd, 0
            while x < x_arr - _EPS:
                per = U if (x_arr - x) > max(U, U * nh / 2) + _EPS else U / 2     # (the head, then the kernel)
                ops = self._cap_ops(Kx, (('head',) if per >= U - _EPS else ('kernel',)) + inv, per - 0.25 + _EPS)
                voice = 0 if low else j % 2
                if voice == 0 and j:
                    a_d = _step(a_d, 1, pd)
                anc = a_d if voice == 0 else _step(a_d, pr['isteps'], pd)
                ns_, nd = self.derive(block, x, anc, pd, Kx, ops, fn='melody' if voice == 0 else 'counter',
                                      parent=parent, other=Ko)
                ns_ = [(a, min(d, x + per - 0.25 - a), q) for a, d, q in ns_ if a < x + per - 0.25 - _EPS]
                ns_ = self._band2(ns_, centre(x) + (0 if voice == 0 else -5))
                (mel if voice == 0 else ans).extend(ns_)
                x += per
                j += 1
            # the chords: the models' degrees (diatonic) or keys (real), the links, the drive harmonised
            nbh = int(round((x_arr - x_c) / U))
            if pr['move'] == 'real':
                for r in range(S):
                    rk_ = _transpose_key(k, r * dirs)
                    b0 = r * Lm
                    b1 = min(nbh, (r + 1) * Lm) if r + 1 < S else nbh
                    if b1 > b0:
                        x0 = x_c + b0 * U
                        ns_ = [y for y in mel if x0 - _EPS <= y[0] < x_c + b1 * U - _EPS]
                        rows += harmonize(ns_, rk_, x0, b1 - b0, U, {0: rns[0]})
                        zones.append((x0, x_c + b1 * U, rk_, set()))
            elif nbh > 0:
                forced, split = {}, set()
                for r in range(S):
                    b = r * Lm
                    if b >= nbh:
                        continue
                    ap = WALK_APPLIED.get(deg[r]) if pr['links'] == 'applied' and r > 0 else None
                    if ap and chroma_fits(k, ap) and rns[r] in chroma_targets(k, ap) and b >= 1:
                        forced[(b - 1, 1)] = (ap,)
                        forced[(b, 0)] = rns[r]
                        split |= {b - 1, b}
                        csyms.add(chroma_symbol(k, ap))
                    else:
                        forced[b] = rns[r]
                ns_ = [y for y in mel if x_c - _EPS <= y[0] < x_arr - _EPS]
                rows += harmonize(ns_, k, x_c, nbh, U, forced, split=split)
                zones.append((x_c, x_arr, k, csyms))
        # the arrival in the goal: a predominant (or a chromatic one) - V7, or a half cadence; the melody's kernel on
        # the predominant, its landing held on the dominant (the thinning before a false entry: broken off)
        Vg7, Vg = _roman(goal, 'V7'), _roman(goal, 'V')
        cs2 = set()
        how = pr['arrive']
        rng = random.Random(f"symphony:{self.d.get('seed')}:walk2:{block}:{t_s}")
        pre_sym = None
        if how == 'chroma':
            cands = [rn for rn in CHROMA_PRE['V7'] if chroma_fits(goal, rn) and 'V7' in chroma_targets(goal, rn)]
            if cands:
                pre_sym = chroma_symbol(goal, cands[rng.randrange(len(cands))])
                rows += [(x_arr, U / 2, pre_sym), (x_arr + U / 2, U / 2, Vg7)]
                cs2.add(pre_sym)
            else:
                how = pr['arrive'] = 'pac'
        if how in ('pac', 'deceptive'):
            Kg = Key(goal)
            pre = 'IV' if Kg.mode == 'dorian' else 'iv' if Kg.minorish else 'ii'
            pre_sym = _roman(goal, pre)
            rows += [(x_arr, U / 2, pre_sym), (x_arr + U / 2, U / 2, Vg7)]
        elif how == 'hc':
            rows.append((x_arr, U, Vg))
        sym1 = pre_sym or Vg
        a1 = _near({_member(sym1, self.m['member'])}, centre(x_arr) + 2, 40 if low else 55)
        hd = self.derive(block, x_arr, a1, pcs_of(goal), Kx, self._cap_ops(Kx, ('kernel',), U / 2 - 0.25),
                         fn='bass' if low else 'melody', parent=parent, other=Ko)[0]
        hd = [(a, min(d, x_arr + U / 2 - 0.25 - a), q) for a, d, q in hd if a < x_arr + U / 2 - 0.25 - _EPS]
        v_top = _near(_cpcs(Vg), (hd[-1][2] if hd else a1) + 1)
        end = x_arr + U / 2 + (U / 4 if pr.get('thin') else U / 2 - 0.25)
        mel += self._band2(hd + [(x_arr + U / 2, end - x_arr - U / 2, v_top)], centre(x_arr))
        if not low and not pr.get('thin'):
            ans += [(x_arr + U / 2, U / 2 - 0.25, _near(_cpcs(Vg), v_top - 7))]
        zones.append((x_arr, z_s, goal, cs2))
        return mel, ans, rows, zones

    # -- DEV_WALK v3 (round o18a): one key per block or ONE prepared modulation, processes sized by time, a stretto of
    # four voices driving into the retransition
    def walk3(self, block: str, keys: list, t0: float, bars: int, home: str, theme2=None, pos=(0.0, 1.0),
              over=None, nxt=None, j_dev: int = 0):
        """(melody, counter, chart, phases, route, over, entries) of a development block as WALK3's processes (DEV_WALK
        v3, round o18a - o17's judges: "the theme set in one new key after another with no preparation", the slow
        developments static, v2's stretto never named, silent_notes rejects): the block stays in ONE key (keys[j_dev],
        its path's j-th) or makes one prepared modulation - into `nxt` (key, kind), the next block's key - at a
        process boundary or at its end (a pivot chord diatonic in both keys, or the new key's dominant held a bar);
        before the retransition the last process drives into it on the home key's dominant without a cadence. The
        processes are sized by seconds (WALK3 'secs' - an andante block holds more, shorter processes than an
        allegro's), at slow tempi on one-bar models whose rest the kernel bridges; the head / kernel drive lasts
        'drive' bars at most. The stretto: four entries - melody, counter, the tenor (the harmony's top voice) and
        the bass - closer and closer, then the head in turn, the bass last. No note under 'min_s' seconds (no
        diminution into 32nds: the o17 rejects). entries: {'inner', 'bass': notes, 'win': [(start, end)]} - the
        stretto's tenor and bass, written over the texture's harmony top voice and bass in its windows."""
        W_ = WALK3
        U, sc = self.U, self.scale
        rng = random.Random(f"symphony:{self.d.get('seed')}:walk3:{block}")
        K1, K2 = Kernel.motto(self.m), self.kernel2(theme2)
        mem = self.__dict__.setdefault('walk_mem', {'used': {}, 'false': False, 'chain': None, 'lines': []})
        mem.setdefault('procs', {})
        over = dict(over or {})
        storm = 'dyn' in over and 'dialogue_brass' in (over.get('tex') or {})
        bar_s = getattr(self, 'bar_s', None) or 2.0
        beat_s = bar_s / U
        slow = bar_s >= W_['slow'] - _EPS
        kb = keys[j_dev % len(keys)]
        nk, nkind = nxt or (None, None)
        into = nkind == 'retrans'
        if into:
            nk = home
        n = int(round(bars * bar_s / W_['secs']))
        n = max(1, min(n, bars // W_['least'], W_['most']))
        base = bars // n
        cuts = [base] * n
        cuts[-1] += bars - base * n
        kinds = []
        for j in range(n):
            w_ = {}
            for kd, v in W_['procs'].items():
                if (kd == 'against' and not K2) or (kd == 'bass' and (n > 1 or storm)) or (kinds and kd == kinds[-1]):
                    continue
                v *= W_['reuse'] if mem['procs'].get(kd) else 1.0
                if j == n - 1 and (into or pos[1] > 1 - _EPS) and kd == 'stretto':
                    v *= W_['into']
                w_[kd] = v
            kd = _pick(rng, w_)
            kinds.append(kd)
            mem['procs'][kd] = mem['procs'].get(kd, 0) + 1
        # the keys: kb throughout, or one modulation into nk (mid: from process `at` on; else in the last arrival)
        at = None
        if nk and nk != kb and not into and n > 1 and rng.random() < W_['mid']:
            at = rng.randrange(1, n)
        pkeys = [nk if at is not None and j >= at else kb for j in range(n)]
        procs, x = [], t0
        for j, (nb, kd) in enumerate(zip(cuts, kinds)):
            k = pkeys[j]
            p = pos[0] + (pos[1] - pos[0]) * (x - t0) / max(_EPS, bars * U)
            src = 'K2' if K2 and kd == 'sequence' and rng.random() < W_['k2'] else 'K1'
            ops = self._walk3_ops(rng, mem, kd, src, k, K2, p)
            last = j + 1 == n
            goal = pkeys[j + 1] if not last else (nk or kb)
            if last and into:
                how = 'drive'
            elif goal != k:
                how = _pick(rng, W_['modulate'])
            else:
                how = _pick(rng, {a: v for a, v in W_['arrive'].items() if not (last and a == 'elide')})
            Lm = 1 if slow and sc == 1 else W_['model'][sc]
            arr_b = 0 if how == 'elide' else 1
            avail = nb - arr_b
            dcap = max(1, min(W_['drive'], int(W_['drive_s'] / bar_s + _EPS)))
            reps, dr = 1, avail - Lm
            for L_ in (Lm, Lm + 1):                       # (a model a bar longer - else more statements)
                reps = max(1, min(W_['states'], avail // L_))
                dr = avail - reps * L_
                if dr <= dcap:
                    Lm = L_
                    break
            else:
                reps = max(1, (avail - dcap + Lm - 1) // Lm)
                dr = avail - reps * Lm
            procs.append({'phase': j, 'arr': kd, 'start': x, 'bars': nb, 'len': Lm, 'reps': reps, 'drive': dr,
                          'key': k, 'goal': goal, 'src': src, 'ops': ops, 'p': p, 'false': False,
                          'move': _pick(rng, W_['moves']) if kd != 'stretto' else 'imitate',
                          'links': _pick(rng, W_['links']), 'arrive': how, 'mod': goal != k,
                          'isteps': _pick(rng, W_['isteps']), 'secs': round(nb * bar_s, 1)})
            x += nb * U
        for j, pr in enumerate(procs):
            if pr['arrive'] == 'deceptive' and j + 1 < len(procs):
                procs[j + 1]['first_rn'] = 'VI' if Key(pr['goal']).minorish else 'vi'
        mel, ans, chart, zones = [], [], [], []
        ent = {'inner': [], 'bass': [], 'win': []}
        for pr in procs:
            m_, a_, c_, z_, e_ = self._walk3_proc(block, pr, K1, K2, mem, slow, beat_s)
            mel += m_
            ans += a_
            chart += c_
            zones += z_
            if e_:
                ent['inner'] += e_['inner']
                ent['bass'] += e_['bass']
                ent['win'].append(e_['win'])
        mind = max(W_['min_beat'] / sc, W_['min_s'] / beat_s)
        out_m, out_a, out_i, out_b = [], [], [], []
        for a, b, k, cs in zones:
            low = any(pr['arr'] == 'bass' and pr['start'] - _EPS <= a < pr['start'] + pr['bars'] * U - _EPS
                      for pr in procs)

            def seg(ns):
                return [nn for nn in ns if a - _EPS <= nn[0] < b - _EPS]
            out_m += seg(mel) if low and DEV_BASS_RAW else fit_line(seg(mel), chart, k, chroma=cs or None)
            out_a += fit_line(seg(ans), chart, k, chroma=cs or None)
            out_i += fit_line(seg(ent['inner']), chart, k, chroma=cs or None)
            out_b += fit_line(seg(ent['bass']), chart, k, chroma=cs or None)

        def clean(ns):                                     # (no note too short to sound - the o17 rejects)
            return [nn for nn in _mono(sorted(ns)) if nn[1] >= mind - _EPS]
        ent = {'inner': clean(out_i), 'bass': clean(out_b), 'win': ent['win']} if ent['win'] else None
        phases = [(pr['start'], pr['bars'], pr['arr'], pr['key']) for pr in procs]
        route = [{k_: (list(v) if isinstance(v, tuple) else v) for k_, v in pr.items() if k_ != 'p'} for pr in procs]
        for r_ in route:
            r_['depth'] = len(r_['ops'])
        # the block's colour (one texture family - the polyphonic one where it holds the stretto) and ONE level ramp
        if storm:
            tex = dict(over['tex'])
        elif 'stretto' in kinds:
            tex = dict(W_['tex']['stretto'])
        else:
            tex = dict(W_['tex'][kinds[0]])
        lv = W_['levels']
        dyn = [(0, lv[0] if pos[0] < _EPS else lv[1], 'step'), (1.0, lv[2])]
        if storm and over.get('dyn'):
            dyn = list(over['dyn'])
        over.update(tex=tex, dyn=dyn)
        return clean(out_m), clean(out_a), chart, phases, route, over, ent

    def _walk3_ops(self, rng, mem, kd: str, src: str, key: str, K2, p: float) -> tuple:
        """A process's unit (WALK3 'ops': no diminution, no mode change - a key change in disguise), as _walk2_ops."""
        W_ = WALK3
        d = _pick(rng, W_['depth'][0 if p < 0.5 else 1])
        if kd == 'stretto':
            d = 1                                          # (the subject one op from the motto: never the literal one)
        elif len(mem['used']) < 3:
            d = max(d, 1 if kd == 'bass' or p < 0.5 else 2)     # (the piece's first units: some transform at least)
        chain = []
        while len(chain) < d:
            w_ = {}
            for op, v in W_['ops'].items():
                if op in chain or any(op in c and set(chain) & (c - {op}) for c in WALK_CONFLICT):
                    continue
                if op in W_['interval'] and set(chain) & set(W_['interval']):
                    continue
                if kd == 'stretto' and op not in W_['subject']:
                    continue
                w_[op] = v * (W_['novel'] if not mem['used'].get(op) else 1.0)
            if not w_:
                break
            chain.append(_pick(rng, w_))
        for o in chain:
            mem['used'][o] = mem['used'].get(o, 0) + 1
        return tuple(chain)

    def _fit3(self, K, ops, room: float) -> tuple:
        """ops fitted to `room` beats by the fragmenting ops only (never 'diminish': the statement is cut instead),
        WALK3 'cap' ops at most (the fragmenting op first)."""
        ops = tuple(o for o in ops if o != 'diminish')
        for fb in WALK_FRAG:
            if K.span(ops) <= room + _EPS:
                break
            if fb in ops or any(fb in c and set(ops) & (c - {fb}) for c in WALK_CONFLICT):
                continue
            ops = ops + (fb,)
        cap = WALK3['cap']
        if len(ops) > cap:
            fr = [o for o in ops if o in WALK_FRAG]
            keep = [o for o in ops if o not in fr]
            ops = tuple((fr[:1] + keep)[:cap])
        return tuple(ops)

    def _pivot(self, k: str, goal: str) -> str | None:
        """A chord of `goal` diatonic in `k` too (the pivot of a prepared modulation) - its predominant first."""
        Kg = Key(goal)
        rns = ('IV', 'ii', 'VII') if Kg.mode == 'dorian' else ('iv', 'VI', 'III') if Kg.minorish else \
            ('ii', 'IV', 'vi')
        pk = set(pcs_of(k))
        for rn in rns:
            sym = _roman(goal, rn)
            if _cpcs(sym) <= pk:
                return sym
        return None

    def _walk3_proc(self, block, pr, K1, K2, mem, slow: bool, beat_s: float):
        """One WALK3 process -> (melody, counter, chart rows, fit zones, entries {'inner', 'bass', 'win'} | None)."""
        W_ = WALK3
        U = self.U
        k, goal, P, kd, Lm = pr['key'], pr['goal'], pr['bars'], pr['arr'], pr['len']
        how = pr['arrive']
        t_s = pr['start']
        z_s = t_s + P * U
        x_arr = z_s if how == 'elide' else z_s - U         # (the arrival bar; an elided arrival has none)
        low = kd == 'bass'
        Kx = K2 if pr['src'] == 'K2' else K1
        Ko = (K1 if pr['src'] == 'K2' else K2) or K1
        pk = pcs_of(k)
        mode_ = 'minor' if Key(k).minorish else 'major'
        c0 = 50 if low else self.centre - 5
        hold = min(W_['hold'], W_['hold_s'] / beat_s)
        gap_b = W_['gap_s'] / beat_s

        def centre(x):                                     # (the register rises toward the goal)
            return c0 + W_['rise'] * (x - t_s) / max(_EPS, P * U)
        mel, ans, rows, zones = [], [], [], []
        ent = None
        x_c = t_s
        csyms = set()
        parent = pr['src']
        inv = ('invert',) if 'invert' in pr['ops'] else ()
        if kd == 'stretto':
            m_, a_, i_, b_, parent = self._walk3_stretto(block, pr, K1, Ko, mem, x_c, x_arr, centre, parent, pk, k,
                                                         hold)
            mel += m_
            ans += a_
            ent = {'inner': i_, 'bass': b_, 'win': (x_c, z_s)}
            nb_ = int(round((x_arr - x_c) / U))
            if nb_ >= 1:
                ns_h = [y for y in mel + ans if x_c - _EPS <= y[0] < x_arr - _EPS]
                rows += harmonize(sorted(ns_h), k, x_c, nb_, U, {0: 'i' if Key(k).minorish else 'I'})
                zones.append((x_c, x_arr, k, set()))
        else:
            degs = W_['deg'][pr['move']]
            rot = -2 if 'reharm' in pr['ops'] else 0
            S = pr['reps']
            deg = [((degs[r % len(degs)] - 1 + rot) % 7) + 1 for r in range(S)]
            rns = [WALK_ROMAN[mode_][d] for d in deg]
            if pr.get('first_rn'):
                rns[0] = pr['first_rn']
            a_base = _near({_member(_roman(k, rns[0]), self.m['member'])}, centre(x_c))
            for r in range(S):
                x0 = x_c + r * Lm * U
                xe = x0 + Lm * U
                off = (deg[r] - deg[0]) % 7
                off = off - 7 if off > 3 else off
                anc = _step(a_base, off, pk) if r else a_base
                pr_ = pcs_of(k, _roman(k, rns[r]))
                sym_r = _roman(k, rns[r])
                ops = self._fit3(Kx, pr['ops'], Lm * U - 0.25)
                ns_, nd = self.derive(block, x0, anc, pr_, Kx, ops, fn='bass' if low else 'melody', parent=parent,
                                      other=Ko)
                parent = nd['node']
                ns_ = [(a, min(d, xe - 0.25 - a), q) for a, d, q in ns_ if a < xe - 0.25 - _EPS]
                if ns_:                                   # (the model's rest: its last note held, then rests)
                    a, d, q = ns_[-1]
                    ns_[-1] = (a, max(d, min(xe - 0.25 - a, d + hold)), q)
                ns_ = self._band2(ns_, centre(x0))
                xh = x0 + Lm * U / 2
                if kd == 'against' and r >= 1 and Lm >= 2 and ns_ and ns_[-1][0] < xh - _EPS:
                    e_ops = self._fit3(Kx, ('head',) + (() if 'invert' in ops else ('invert',)), xe - xh - 0.25)
                    ns2, _ = self.derive(block, xh, _step(ns_[-1][2], 1, pr_), pr_, Kx, e_ops, parent=nd['node'],
                                         other=Ko)
                    ns2 = [(a, min(d, xe - 0.25 - a), q) for a, d, q in ns2 if a < xe - 0.25 - _EPS]
                    a, d, q = ns_[-1]
                    ns_[-1] = (a, min(d, xh - a), q)
                    ns_ = ns_ + self._band2(ns2, centre(x0) + 2)
                if ns_ and not low:
                    # (a rest longer than 'gap_s' - the slow tempi: the kernel bridges it toward the next model)
                    e = max(a + d for a, d, _ in ns_)
                    y = 0.5 * math.ceil(e / 0.5 - _EPS)
                    if (xe - 0.25 - y) >= gap_b - _EPS and (xe - 0.25 - y) >= U / 2 - _EPS:
                        nxt_a = _step(anc, 1 if r + 1 < S else 2, pk)
                        sg_ = 1 if nxt_a >= ns_[-1][2] else -1
                        l_ops = self._fit3(Kx, ('kernel',) + inv, xe - 0.25 - y)
                        nsl, _ = self.derive(block, y, _step(ns_[-1][2], sg_, pr_), pr_, Kx, l_ops, parent=nd['node'],
                                             other=Ko, tf='link')
                        nsl = [(a, min(d, xe - 0.25 - a), q) for a, d, q in nsl if a < xe - 0.25 - _EPS]
                        if nsl:
                            a, d, q = ns_[-1]
                            ns_[-1] = (a, min(d, nsl[0][0] - a), q)
                            a, d, q = nsl[-1]
                            nsl[-1] = (a, max(d, xe - 0.25 - a), q)
                            ns_ = ns_ + self._band2(nsl, centre(x0) + 1)
                mel += ns_
                if not low:
                    mem['lines'].append((nd['depth'], 0, [y for y in ns_ if y[0] < x0 + 2 * U - _EPS], x0, k, nd))
                c_rep, nd3 = [], None
                if kd == 'against':
                    o2 = self._fit3(Ko, ('augment',) if Lm >= 2 else (), Lm * U - 0.25)
                    ca = _near({_member(sym_r, self.m['member'])}, centre(x0) - 9)
                    c_rep, nd3 = self.derive(block, x0, ca, pr_, Ko, o2, fn='counter', parent=nd['node'], other=Kx)
                    c_rep = self._band2(c_rep, max(55, centre(x0) - 9))
                else:                                     # (the answer half a model late, then a quarter ... - at slow
                    dl = Lm * U / 2 ** (r + (2 if slow else 1))       # tempi a quarter from the first model on)
                    dl = max(0.5, 0.5 * round(dl / 0.5))
                    if kd == 'bass':                       # (over the bass the other kernel's head, inverted in turn)
                        o2, Kc = ('head', 'invert') if r % 2 else ('head',), Ko
                        ca = _near({_member(sym_r, self.m['member'])}, self.centre + 2)
                    else:
                        o2 = tuple(o for o in ops if o != 'invert') if 'invert' in ops else ops + ('invert',)
                        Kc = Kx
                        ca = _step(anc, pr['isteps'], pr_)
                    o2 = self._fit3(Kc, o2, xe - x0 - dl - 0.25)
                    c_rep, nd3 = self.derive(block, x0 + dl, ca, pr_, Kc, o2, fn='counter', parent=nd['node'],
                                             other=Kx if Kc is Ko else Ko)
                    c_rep = self._band2(c_rep, (self.centre + 2) if kd == 'bass' else centre(x0) - 5)
                c_rep = [(a, min(d, xe - 0.25 - a), q) for a, d, q in c_rep if a < xe - 0.25 - _EPS]
                if c_rep:
                    a, d, q = c_rep[-1]
                    c_rep[-1] = (a, max(d, min(xe - 0.25 - a, d + hold)), q)
                    ans += c_rep
                    mem['lines'].append((nd3['depth'], 1, c_rep, c_rep[0][0], k, nd3))
            # the drive ('drive' bars at most): the unit's head, then its kernel, the two lines in turn a step higher
            xd = x_c + S * Lm * U
            nh = int(round((x_arr - xd) / U))
            a_d = _step(a_base, 1, pk)
            x, j = xd, 0
            while x < x_arr - _EPS:
                per = U if (x_arr - x) > max(U, U * nh / 2) + _EPS else U / 2
                ops = self._fit3(Kx, (('head',) if per >= U - _EPS else ('kernel',)) + inv, per - 0.25 + _EPS)
                voice = 0 if low else j % 2
                if voice == 0 and j:
                    a_d = _step(a_d, 1, pk)
                anc = a_d if voice == 0 else _step(a_d, pr['isteps'], pk)
                ns_, nd = self.derive(block, x, anc, pk, Kx, ops, fn='melody' if voice == 0 else 'counter',
                                      parent=parent, other=Ko)
                ns_ = [(a, min(d, x + per - 0.25 - a), q) for a, d, q in ns_ if a < x + per - 0.25 - _EPS]
                ns_ = self._band2(ns_, centre(x) + (0 if voice == 0 else -5))
                (mel if voice == 0 else ans).extend(ns_)
                x += per
                j += 1
            nbh = int(round((x_arr - x_c) / U))
            if nbh > 0:
                forced, split = {}, set()
                for r in range(S):
                    b = r * Lm
                    if b >= nbh:
                        continue
                    ap = WALK_APPLIED.get(deg[r]) if pr['links'] == 'applied' and r > 0 else None
                    if ap and chroma_fits(k, ap) and rns[r] in chroma_targets(k, ap) and b >= 1:
                        forced[(b - 1, 1)] = (ap,)
                        forced[(b, 0)] = rns[r]
                        split |= {b - 1, b}
                        csyms.add(chroma_symbol(k, ap))
                    else:
                        forced[b] = rns[r]
                ns_ = [y for y in mel if x_c - _EPS <= y[0] < x_arr - _EPS]
                rows += harmonize(ns_, k, x_c, nbh, U, forced, split=split)
                zones.append((x_c, x_arr, k, csyms))
        if how == 'elide':                                 # (no arrival: the next process takes over in the key)
            return mel, ans, rows, zones, ent
        # the arrival: in the key (a cadence, a half cadence, a deceptive one, a chromatic predominant), a prepared
        # modulation (the pivot chord, or the new key's dominant held a bar), or the drive into the retransition
        Vg7, Vg = _roman(goal, 'V7'), _roman(goal, 'V')
        cs2 = set()
        rng = random.Random(f"symphony:{self.d.get('seed')}:walk3:{block}:{t_s}")
        pre_sym = None
        if how == 'chroma':
            cands = [rn for rn in CHROMA_PRE['V7'] if chroma_fits(goal, rn) and 'V7' in chroma_targets(goal, rn)]
            if cands:
                pre_sym = chroma_symbol(goal, cands[rng.randrange(len(cands))])
                rows += [(x_arr, U / 2, pre_sym), (x_arr + U / 2, U / 2, Vg7)]
                cs2.add(pre_sym)
            else:
                how = pr['arrive'] = 'pac'
        if how == 'pivot':
            pre_sym = self._pivot(k, goal)
            if pre_sym:
                rows += [(x_arr, U / 2, pre_sym), (x_arr + U / 2, U / 2, Vg7)]
            else:
                how = pr['arrive'] = 'dominant'
        if how in ('pac', 'deceptive'):
            Kg = Key(goal)
            pre = 'IV' if Kg.mode == 'dorian' else 'iv' if Kg.minorish else 'ii'
            pre_sym = _roman(goal, pre)
            rows += [(x_arr, U / 2, pre_sym), (x_arr + U / 2, U / 2, Vg7)]
        elif how == 'hc':
            rows.append((x_arr, U, Vg))
        elif how == 'dominant':
            rows.append((x_arr, U, Vg7))
        elif how == 'drive':
            pv = self._pivot(k, goal) if k != goal else None
            rows += [(x_arr, U / 2, pv), (x_arr + U / 2, U / 2, Vg)] if pv else [(x_arr, U, Vg)]
            pre_sym = pv
        sym1 = pre_sym or Vg
        if how == 'drive':
            # (no cadence, no landing: the kernel in both lines a step higher each half bar into the retransition,
            # the bass - in the stretto - on the dominant's root through the bar)
            a1 = _near({_member(sym1, self.m['member'])}, centre(x_arr) + 2, 55)
            for i in range(2):
                xx = x_arr + i * U / 2
                hd = self.derive(block, xx, _step(a1, i, pcs_of(goal)), pcs_of(goal), Kx,
                                 self._fit3(Kx, ('kernel',) + inv, U / 2 - 0.25), fn='melody', parent=parent,
                                 other=Ko)[0]
                hd = [(a, min(d, xx + U / 2 - 0.25 - a), q) for a, d, q in hd if a < xx + U / 2 - 0.25 - _EPS]
                mel += self._band2(hd, centre(x_arr) + 1)
                ha = self.derive(block, xx + U / 4, _step(a1, i + pr['isteps'], pcs_of(goal)), pcs_of(goal), Kx,
                                 self._fit3(Kx, ('kernel',) + inv, U / 4 + U / 2 - 0.25), fn='counter',
                                 parent=parent, other=Ko)[0]
                z_ = min(z_s, xx + U / 4 + U / 2) - 0.25
                ha = [(a, min(d, z_ - a), q) for a, d, q in ha if a < z_ - _EPS]
                ans += self._band2(ha, centre(x_arr) - 5)
            if ent is not None:
                ent['bass'] += [(x_arr, U / 2, _near({chord(sym1).root % 12}, 45, 36, 52)),
                                (x_arr + U / 2, U / 2, _near({chord(Vg).root % 12}, 43, 36, 50))]
            zones.append((x_arr, z_s, goal, cs2))
            return mel, ans, rows, zones, ent
        a1 = _near({_member(sym1, self.m['member'])}, centre(x_arr) + 2, 40 if low else 55)
        hd = self.derive(block, x_arr, a1, pcs_of(goal), Kx, self._fit3(Kx, ('kernel',), U / 2 - 0.25),
                         fn='bass' if low else 'melody', parent=parent, other=Ko)[0]
        hd = [(a, min(d, x_arr + U / 2 - 0.25 - a), q) for a, d, q in hd if a < x_arr + U / 2 - 0.25 - _EPS]
        v_top = _near(_cpcs(Vg), (hd[-1][2] if hd else a1) + 1)
        end = x_arr + U - 0.25
        mel += self._band2(hd + [(x_arr + U / 2, end - x_arr - U / 2, v_top)], centre(x_arr))
        if not low:
            ans += [(x_arr + U / 2, U / 2 - 0.25, _near(_cpcs(Vg), v_top - 7))]
        if ent is not None:                                # (the stretto's bass lands on the arrival's roots)
            ent['bass'] += [(x_arr, U / 2, _near({chord(sym1).root % 12}, 45, 36, 52)),
                            (x_arr + U / 2, U / 2 - 0.25, _near({chord(Vg).root % 12}, 43, 36, 50))]
        zones.append((x_arr, z_s, goal, cs2))
        return mel, ans, rows, zones, ent

    def _walk3_stretto(self, block, pr, K1, Ko, mem, x_c: float, x_end: float, centre, parent, pk, k: str,
                       hold: float):
        """The stretto of four voices over [x_c, x_end) -> (melody, counter, tenor, bass, the last node): the subject
        (the motto, one op at most) in the melody, the counter 'isteps' under, the tenor an octave under the melody,
        the bass an octave under the counter - the exposition a subject apart (or half), the later entries half a
        subject apart; then the head in turn every half subject, each voice a step higher each time, the bass last.
        Each voice holds its last note toward its next entry (no voice drops out once it has entered)."""
        U = self.U
        hb = U / 2

        def half(v):
            return max(hb, hb * math.ceil(v / hb - _EPS))
        subj = pr['ops']
        s = min(max(2, pr['len']) * U, max(U, half(K1.span(subj))))
        span = x_end - x_c
        gs = half(s / 2)
        offs, vs = None, None
        for g1 in (s, gs):
            if g1 + 2 * gs + s <= span + _EPS:
                offs, vs = [0.0, g1, g1 + gs, g1 + 2 * gs], [0, 1, 2, 3]
                break
        if offs is None:
            if 2 * gs + s <= span + _EPS:
                offs, vs = [0.0, gs, 2 * gs], [0, 1, 3]
            elif gs + s <= span + _EPS:
                offs, vs = [0.0, gs], [0, 3]
            else:
                offs, vs = [0.0], [0]
        ev = [(x_c + o, v, 'subj') for o, v in zip(offs, vs)]
        y = ev[-1][0] + s if len(ev) == 1 else ev[-1][0] + gs
        tail = []
        while y + hb <= x_end - _EPS:
            tail.append(y)
            y += gs
        cyc = sorted(set(vs))
        i3 = cyc.index(cyc[-1])
        m = len(tail)
        for i, yy in enumerate(tail):
            v = cyc[(i - (m - 1) + i3) % len(cyc)]
            ev.append((yy, v, 'subj' if i == m - 1 and v == cyc[-1] and x_end - yy >= s - _EPS else 'head'))
        I_k = _roman(k, 'i' if Key(k).minorish else 'I')
        a0 = _near({_member(I_k, self.m['member'])}, centre(x_c))
        a1 = _step(a0, pr['isteps'], pk)
        bases = {0: a0, 1: a1, 2: a0 - 12, 3: a1 - 12}
        shift = {0: 0.0, 1: -5.0, 2: -12.0}
        seen = {v: 0 for v in bases}
        nxt_of = {}
        for i, (yy, v, _) in enumerate(ev):
            later = [e[0] for e in ev[i + 1:] if e[1] == v]
            nxt_of[i] = later[0] if later else x_end
        out = {0: [], 1: [], 2: [], 3: []}
        inv = tuple(o for o in subj if o == 'invert')
        for i, (yy, v, what) in enumerate(ev):
            z = nxt_of[i] - 0.25
            room = z - yy
            if room < 0.5 - _EPS:
                continue
            ops = subj if what == 'subj' else ('head',) + inv
            ops = self._fit3(K1, ops, room)
            anc = _step(bases[v], seen[v], pk)
            seen[v] += 1
            ns_, nd = self.derive(block, yy, anc, pk, K1, ops,
                                  fn=('melody', 'counter', 'inner', 'bass')[v], parent=parent, other=Ko)
            parent = nd['node']
            ns_ = [(a, min(d, z - a), q) for a, d, q in ns_ if a < z - _EPS]
            if not ns_:
                continue
            # (the voice goes on toward its next entry: the kernel inverted, a fragment, the head contracted - each from
            # a step past its last note, in turn up and down (the next voice down and up); a voice never drops out once
            # it has entered)
            for c in range(16):
                e = max(a + d for a, d, _ in ns_)
                y0 = 0.5 * math.ceil(e / 0.5 - _EPS)
                if z - y0 < U / 2 - _EPS:
                    break
                c_ops = self._fit3(K1, (('kernel', 'invert'), ('frag3',), ('head', 'contract'))[c % 3], z - y0)
                nc, ndc = self.derive(block, y0, _step(ns_[-1][2], 1 if (c + v) % 2 == 0 else -1, pk), pk, K1, c_ops,
                                      fn=('melody', 'counter', 'inner', 'bass')[v], parent=nd['node'], other=Ko,
                                      tf='continue')
                nc = [(a, min(d, z - a), q) for a, d, q in nc if a < z - _EPS]
                if not nc:
                    break
                a, d, q = ns_[-1]
                ns_[-1] = (a, max(d, min(nc[0][0] - a, d + hold)), q)
                ns_ += nc
            a, d, q = ns_[-1]
            ns_[-1] = (a, max(d, min(z - a, d + max(hold, (z - a) if v >= 2 else 0.0))), q)
            ns_ = self._band2(ns_, WALK3['bass_c'] if v == 3 else centre(yy) + shift[v])
            out[v] += ns_
            if v <= 1:
                mem['lines'].append((nd['depth'], v, [n_ for n_ in ns_ if n_[0] < yy + 2 * U - _EPS], yy, k, nd))
        return out[0], out[1], out[2], out[3], parent


    def contour(self):
        """The climax's statement steps (SET_PLAN 'contour': CONTOURS by the set's draw), or None (the old climb)."""
        if SET_PLAN and SET_PLAN.get('contour') and self.d.get('contour') in CONTOURS:
            return CONTOURS[self.d['contour']]
        return None

    def dev_line(self):
        """The development's counter-line for the return (WALK 'line'): the deepest derived line of 3+ notes lasting
        1-2 bars (a counter-line before a melody, the later before the earlier) - {notes from 0, key, node}."""
        mem = getattr(self, 'walk_mem', None)
        if not mem or not mem['lines']:
            return None
        lo, hi = WALK['line']['span']
        cand = []
        for depth, ctr, ns, x, k, nd in mem['lines']:
            if len(ns) < WALK['line']['min']:
                continue
            span = max(a + d for a, d, _ in ns) - x
            if lo * self.U - _EPS <= span <= hi * self.U + _EPS:
                cand.append(((min(4, len({p for _, _, p in ns})), depth, ctr, x), ns, x, k, nd))
        if not cand:
            return None
        _, ns, x, k, nd = max(cand, key=lambda c: c[0])
        return {'notes': [(a - x, d, p) for a, d, p in ns], 'key': k, 'node': nd}

    def recall(self, block: str, key: str, ch, t0: float, bars: int, below: float = 5) -> list:
        """The development's counter-line (dev_line) against a returning theme: stated from bar 2 every its bars + a
        bar's breath, its first note on its chord's member `below` the centre, cut before the last bar, fitted."""
        L_ = self.dev_line()
        if not L_:
            return []
        U = self.U
        rel, k0, nd = L_['notes'], L_['key'], L_['node']
        span = max(a + d for a, d, _ in rel)
        step = U * max(1, math.ceil(span / U - _EPS))
        sh = Key(key).tonic - Key(k0).tonic
        base = [(a, d, p + sh) for a, d, p in rel]
        if Key(k0).minorish != Key(key).minorish:
            base = _to_mode(base, _transpose_key(k0, sh % 12), key)
        out = []
        x = t0 + U
        stop = t0 + (bars - 1) * U
        while x + U <= stop + _EPS:
            sym = _chart_at(ch, x)
            tgt = _near({_member(sym, self.m['member'])}, self.centre - below)
            off = tgt - base[0][2]
            z = min(x + step, stop)
            seg = [(x + a, min(d, z - 0.25 - x - a), p + off) for a, d, p in base if x + a < z - 0.25 - _EPS]
            if seg:
                self.log.append(dict({'block': block, 'beat': x, 'tf': 'recall', 'fn': 'counter', 'end': z},
                                     **self.node(nd['node'], tuple(nd['ops']) + ('recall',), nd['depth'] + 1,
                                                 nd['src'])))
                out += seg
            x += step + U
        if not out:
            return []
        while min(p for _, _, p in out) < 50:
            out = [(a, d, p + 12) for a, d, p in out]
        return _mono(fit_line(_mono(out), ch, key))

    # -- a fugato: the motto + a running tail as the subject, entries low to high (tonic / dominant / octave)
    def fugato(self, block: str, key: str, t0: float, bars: int, gap: float | None = None):
        """gap: the entries' distance (beats; default spread over the block - the fugato build: a bar, closer)."""
        U, m = self.U, self.m
        pcs = pcs_of(key)
        tonic = _roman(key, 'i' if Key(key).minorish else 'I')
        cell = motto_notes(m, 0.0, 0, pcs)
        cl = max(a + d for a, d, _ in cell)
        span = 2 * U if cl <= U + _EPS else 3 * U
        centres = {'v4': 50, 'v3': 57, 'v2': 62, 'v1': 69}
        order = FUGUE_ORDERS.get(self.d.get('fug_order'), FUGUE_ORDERS['rise'])
        entries = [(v, j % 2, centres[v]) for j, v in enumerate(order)]
        if gap is None:
            gap = max(U, (bars * U - span) / 3.0)
            gap = U * max(1, int(round(gap / U)))
        vs = {}
        subj_notes = []
        for j, (v, dom, centre) in enumerate(entries):
            t = t0 + j * gap
            if t >= t0 + bars * U - U + _EPS:
                break
            k_ = key if not dom else _transpose_key(key, 7, 'major' if not Key(key).minorish else 'minor')
            pk = pcs_of(key, _roman(key, 'V')) if dom else pcs
            anc = _near({_member(_roman(key, 'V') if dom else tonic, self.m['member'])}, centre)
            ns = self.state(block, t, anc, pk, (), fn='voice')
            a, d, p = ns[-1]
            ns[-1] = (a, min(d, 1.0), p)
            tail_t = a + min(d, 1.0)
            # (round o3: "fugato subjects unrelated to the main idea" - the tail is the motto's kernel, inverted,
            # sequenced down a step: the subject is the motto and its answer to itself)
            kl = 2.0 if self.family == 'duple' else 1.5
            x, q, j = tail_t, p, 0
            while x < t + span - 0.5 - _EPS:          # (SEQ_PAIR: the kernel and its inversion, the pair a step
                if j % 2 == 0:                         # lower each time - a falling sequence in the voice's range)
                    q = _step(q, -1, pk)
                a_k, tf_k = _seq_pair(m, q, j, pk)
                ns += [(a_, min(d_, t + span - a_), p_) for a_, d_, p_ in
                       motto_notes(m, x, a_k, pk, ('kernel',) + tf_k) if a_ < t + span - _EPS]
                x += kl
                j += 1
            vs[v] = [x_ for x_ in _mono(ns) if x_[0] < t0 + bars * U - _EPS]
            subj_notes += vs[v]
            del k_
        forced = {0: 'i' if Key(key).minorish else 'I', bars - 1: 'V'}
        chart = harmonize(subj_notes, key, t0, bars, U, forced)
        # the free voices after their subject: the counter-subject - the motto inverted (round o3: the motto
        # against itself), from the chord tone nearest the voice's register, fitted to the chords
        rh = [(on, du) for on, du, _ in cell_of(m)]
        cl_ = max(U, U * math.ceil(max(on + du for on, du in rh) / U - _EPS))
        for v, ns in vs.items():
            home = dict((e[0], e[2]) for e in entries)[v]
            end = max(a + d for a, d, _ in ns)
            p = ns[-1][2]
            t = t0 + U * math.ceil((end - t0) / U - _EPS)
            free = []
            while t < t0 + bars * U - _EPS:
                sym = _chart_at(chart, t)
                anc = min((q for q in range(home - 6, home + 7) if q % 12 in _cpcs(sym)),
                          key=lambda q: (abs(q - home) + 0.4 * abs(q - p), q))
                st_ = min(([x for x in motto_notes(m, t, anc, pcs, tf) if x[0] < min(t + cl_, t0 + bars * U) - _EPS]
                           for tf in (('invert',), ())),       # (inverted, or as stated: whichever stays nearer
                          key=lambda ns_: (min((q for _, _, q in ns_), default=home) < home - 8,     # the register)
                                           abs(sum(q for _, _, q in ns_) / max(1, len(ns_)) - home)))
                free += [(a, min(d, t + cl_ - a, 2.0), p_) for a, d, p_ in st_]
                p = st_[-1][2] if st_ else anc
                t += cl_
            vs[v] = fit_line(ns, chart, key) + fit_line(free, chart, key)
        return vs, chart

    # -- FUGUE's fugato (round o19b): an exposition with a counter-subject, episodes, the final entry
    def fsubject(self, key: str, head=None, S: int | None = None) -> tuple:
        """The fugue subject in `key` from beat 0 (a reference register): the motto, its landing held at most a beat
        (a 6/8 pulse), then a tail in the other rhythm (quarters after a quick head, 8ths after a slow one; 6/8: a
        quarter and an 8th) stepping to the tonic's third on the last bar's second pulse -> (notes, bars). head / S
        (FUGUE v2, fsubject2): the head given - the first theme's opening - its subject S bars; a head reaching the
        tail's goal is held to the end."""
        U, m = self.U, self.m
        pcs = pcs_of(key)
        ton = _roman(key, 'i' if Key(key).minorish else 'I')
        given = head is not None
        if not given:
            head = motto_notes(m, 0.0, _near({_member(ton, m['member'])}, 64), pcs)
            S = 2 if max(a + d for a, d, _ in head) <= U + _EPS else 3
        hl = 1.0 if self.family == 'duple' else 1.5
        a, d, p = head[-1]
        head = head[:-1] + [(a, min(d, hl), p)]
        x = a + min(d, hl)
        z = (S - 1) * U + (U / 2 if self.family == 'duple' else 1.5)
        if given and x >= z - _EPS:
            return _mono(head[:-1] + [(a, S * U - a, p)]), S
        goal = _near({_member(ton, 'third')}, p - 2)
        fast = sorted(d_ for _, d_, _ in head)[len(head) // 2] <= 0.5 + _EPS
        cells = ((1.0,) if fast else (0.5,)) if self.family == 'duple' else ((1.0, 0.5) if fast else (0.5,))
        if (z - x) / (sum(cells) / len(cells)) < 3 - _EPS:      # (a short tail: 8ths - three notes at least)
            cells = (0.5,)
        rh, t = [], x
        while t < z - _EPS:
            for c in cells:
                if t < z - _EPS:
                    rh.append((t, min(c, z - t)))
                    t += min(c, z - t)
        tail = []
        if rh:
            run = run_to(_step(p, -1 if goal < p else 1, pcs), goal, x, len(rh), 0.5, pcs)
            tail = [(a_, d_, q) for (a_, d_), (_, _, q) in zip(rh, run)]
            if tail[-1][2] == goal:                          # (the run reached it early: it ends on the tonic)
                goal = _near({Key(key).tonic % 12}, goal - 1)
        zz = max(z, x)
        return _mono(head + tail + [(zz, S * U - zz, goal)]), S

    def fsubject2(self, key: str, theme1=None) -> tuple:
        """FUGUE v2's subject in `key` from beat 0: the first theme's opening S bars as heard (theme1 = (key, notes
        from 0, bars) - the motto and its continuation), moved into the key (its mode), the last note held to the
        subject's end -> (notes, bars); fsubject's when there is no first theme (or too few notes)."""
        U = self.U
        S = 2 if max(a + d for a, d, _ in motto_notes(self.m, 0.0, 64, pcs_of(key))) <= U + _EPS or \
            self.scale == 2 else 3                    # (the scherzo's: two of its compound bars - four 3/4 bars)
        if not theme1:
            return self.fsubject(key)
        k1, ns, _ = theme1
        src = sorted((a, min(d, S * U - a), p) for a, d, p in ns if -_EPS <= a < S * U - _EPS)
        if len(src) < 4 or len({p for _, _, p in src}) < 3:
            return self.fsubject(key)
        sh = (Key(key).tonic - Key(k1).tonic) % 12
        sh = sh - 12 if sh > 6 else sh
        src = [(a, d, p + sh) for a, d, p in src]
        if Key(key).minorish != Key(k1).minorish:
            src = _to_mode(src, _transpose_key(k1, sh % 12), key)
        src = _mono(src)
        o = 12 * round((64 - sum(q for _, _, q in src) / len(src)) / 12)
        src = [(a, d, q + o) for a, d, q in src]
        a, d, p = src[-1]
        if d <= (1.0 if self.family == 'duple' else 1.5) + _EPS and a + d >= S * U - U / 2 - _EPS:
            src[-1] = (a, S * U - a, p)                # (the opening moves on to its end: its last note held)
            return src, S
        return self.fsubject(key, head=src, S=S)     # (a long landing or a rest: held a beat, fsubject's tail)

    def fug_return(self, block: str, key: str, t0: float, bars: int, mel, chart) -> list:
        """FUGUE v2: the fugato's subject back at the summit - in the bass, augmented (FUGUE_V2 'ret' 'aug'; the
        scherzo's not), moved into the climax's key, its start bar and octave the least joint cost against the
        climax's melody (voicing.cp_issues, the strong beats' non-chord tones), repaired within 'reach' semitones
        (voicing.repair: the first note fixed) -> notes in [t0, t0 + bars U), or []."""
        from .. import voicing as vc
        sub = getattr(self, 'fug_subj', None)
        R_ = FUGUE['v2']['ret']
        if not sub or not mel or not chart:
            return []
        U = self.U
        f = 1 if self.scale == 2 else R_['aug']
        k0, subj, S = sub
        if S * U * f > bars * U + _EPS:
            f = 1
        if S * U * f > bars * U + _EPS:
            return []
        sh = (Key(key).tonic - Key(k0).tonic) % 12
        sh = sh - 12 if sh > 6 else sh
        ns = [(a * f, d * f, p + sh) for a, d, p in subj]
        if Key(key).minorish != Key(k0).minorish:
            ns = _to_mode(ns, _transpose_key(k0, sh % 12), key)
        strong = 2.0 if self.family == 'duple' else 1.5
        lo, hi = R_['range']
        best = None
        for b0 in R_['starts']:
            x0 = t0 + b0 * U
            if x0 + S * U * f > t0 + bars * U + _EPS:
                continue
            for o in (-36, -24, -12, 0):
                cand = [(x0 + a, d, p + o) for a, d, p in ns]
                av = sum(p for _, _, p in cand) / len(cand)
                if not lo <= av <= hi:
                    continue
                top = [n for n in mel if x0 - _EPS <= n[0] < x0 + S * U * f - _EPS]
                c = vc.cp_cost(vc.cp_issues({'mel': top, 'bass': cand}, order=('mel', 'bass'), strong=strong, t0=t0))
                c += sum(1.0 for a, d, p in cand if abs((a - t0) / strong - round((a - t0) / strong)) < 1e-6 and
                         (_chart_at(chart, a) is not None and p % 12 not in _cpcs(_chart_at(chart, a))))
                c += 0.05 * abs(av - R_['centre']) + 0.2 * b0
                if best is None or c < best[0] - _EPS:
                    best = (c, cand)
        if best is None:
            return []
        cand = best[1]
        first = round(cand[0][0], 4)
        fixed = vc.repair({'mel': list(mel), 'bass': cand}, scale=lambda t: pcs_of(key, _chart_at(chart, t)),
                          harmony=chart, order=('mel', 'bass'), strong=strong, t0=t0, reach=R_['reach'],
                          movable=lambda v, n_: v == 'bass' and round(n_[0], 4) != first,
                          ranges={'bass': (lo - 5, hi + 5)})
        out = _mono(fixed.get('bass', cand))
        self.log.append(dict({'block': block, 'beat': out[0][0], 'tf': 'augment' if f > 1 else 'plain',
                              'fn': 'bass', 'end': out[-1][0] + out[-1][1]}, **self.node('K1', ('subject',))))
        return out

    def fugue2(self, block: str, key: str, t0: float, bars: int, home: str, seed: int = 0,
               beat_s: float | None = None, theme1=None, dance: bool = False) -> dict:
        """FUGUE's fugato in `key` over [t0, t0 + bars U) -> {'voices' {v1..v4: notes}, 'chart', 'leads' [(voice,
        start, end)], 'bass' (the basses' octave under v4), 'tex', 'form' [(section, bars, key)], 'issues' (the
        joint voice leading's left after the repair)} - the module's FUGUE_ON."""
        from .. import voicing as vc
        F_, U = FUGUE, self.U
        rng = random.Random(f"symphony:fugue:{seed}:{block}")
        VO = F_['voices']
        names = tuple(VO)
        duple = self.family == 'duple'
        strong = 2.0 if duple else 1.5
        end = t0 + bars * U
        minor = Key(key).minorish
        V2 = F_.get('v2')
        subj, S = self.fsubject2(key, theme1) if V2 else self.fsubject(key)
        D = _transpose_key(key, 7, 'minor' if minor else 'major')
        ans = [(a, d, p + 7) for a, d, p in subj]
        if subj[0][2] % 12 == (Key(key).tonic + 7) % 12:      # (the tonal answer: the dominant answered by the tonic)
            ans[0] = (ans[0][0], ans[0][1], ans[0][2] - 2)
        hs = harmonize(subj, key, 0.0, S, U, {0: 'i' if minor else 'I'})
        ha = harmonize(ans, D, 0.0, S, U)
        order = F_['orders'].get(self.d.get('fug_order'), F_['orders']['rise'])
        if V2:                                 # (v2: the entries' distance drawn - a codetta, an overlap)
            gw = {S + k: w_ for k, w_ in V2['gap'].items() if S + k >= S - (1.0 if S >= 3 else 0.5) - _EPS}
            order0 = F_['orders'].get(self.d.get('fug_order'), F_['orders']['rise'])

            def _oct(ns, v):
                c = sum(p for _, _, p in ns) / len(ns)
                return [(a, d, p + 12 * round((VO[v][2] - c) / 12)) for a, d, p in ns]
            for g_ in [g_ for g_ in gw if g_ < S - _EPS]:      # (an overlap only where subject and answer agree)
                a1, a2 = _oct(subj, order0[0]), _oct([(a + g_ * U, d, p) for a, d, p in ans], order0[1])
                hi_, lo_ = sorted((order0[0], order0[1]), key=names.index)
                pr = {hi_: a1 if hi_ == order0[0] else a2, lo_: a2 if hi_ == order0[0] else a1}
                if vc.cp_cost(vc.cp_issues(pr, order=(hi_, lo_), strong=strong, t0=0.0)) > V2['overlap']:
                    del gw[g_]
            gap = float(_pick(rng, gw))
            n = 4 if bars >= 3 * gap + S + 2 - _EPS else 3
            if (n - 1) * gap + S > bars + _EPS:
                gap = float(max(1, (bars - S) // (n - 1)))
            rest = bars - int(math.ceil((n - 1) * gap + S - _EPS))
            if gap > S + _EPS and rest < S + 3 <= bars - ((n - 1) * S + S):   # (a codetta that leaves no final
                gap = float(S)                                                 # entry: the entries close up)
                rest = bars - ((n - 1) * S + S)
        else:
            n = 4 if bars >= 4 * S + 2 else 3
            gap = S if n * S <= bars else max(1, (bars - S) // (n - 1))
            rest = bars - ((n - 1) * gap + S)

        hp = pcs_of(home) | {(Key(home).tonic + 11) % 12}

        def related(k):                        # (the keys near k whose tonic chord is diatonic to home)
            ks = [fugue_key(k, r) for r in (('III', 'iv', 'v', 'VI') if Key(k).minorish else
                                             ('vi', 'ii', 'IV', 'V', 'iii'))]
            return [x for x in ks if _cpcs(_roman(x, 'i' if Key(x).minorish else 'I')) <= hp]
        no = {Key(home).tonic % 12, Key(key).tonic % 12, Key(D).tonic % 12}
        c1 = [k for k in related(key) if Key(k).tonic % 12 not in no] or related(key)
        T1 = c1[rng.randrange(len(c1))]
        c2 = [k for k in related(T1) + [key] if Key(k).tonic % 12 not in {Key(home).tonic % 12, Key(T1).tonic % 12}]
        T2 = c2[rng.randrange(len(c2))] if c2 else key
        techs = list(F_['episode'])
        tech = _pick(rng, F_['episode'])
        techs = [tech] + [x for x in techs if x != tech]
        frag = _pick(rng, F_['frag'])
        fin_ = _pick(rng, F_['final'])
        plan = []
        if rest >= 2 * S + 5:
            eps = rest - 2 * S - 1
            e1 = min(F_['ep_max'], (eps + 1) // 2)
            e2 = min(F_['ep_max'], eps - e1)
            close = rest - 2 * S - e1 - e2
            plan = [('ep', e1, T1), ('mid', S, T1), ('ep', e2, T2)]
            while close > 2 + S - 1:
                plan.append(('mid', S, T2))
                close -= S
            plan += [('fin', S, T2), ('close', close, T2)]
        elif rest >= S + 3:
            e1 = min(F_['ep_max'], rest - S - 1)
            plan = [('ep', e1, T1), ('fin', S, T1), ('close', rest - S - e1, T1)]
        elif rest >= 1:
            plan = [('ep', rest, T1)]
            if V2 and rest > F_['ep_max']:         # (v2: no episode over ep_max bars - the half cadence after it)
                plan = [('ep', F_['ep_max'], T1), ('close', rest - F_['ep_max'], T1)]
        if 'v4' not in order[:n] and not any(p[0] == 'fin' for p in plan):
            order = tuple(order[:n - 1]) + ('v4',)            # (no final entry: the bass enters in the exposition)
        fin = fin_ if 'v4' in order[:n] else 'bass'
        written = {v: [] for v in names}
        fixed = set()                          # (voice, round(start, 4)) of the entries' and fragments' notes
        leads, chart, rests, first, form = [], [], {v: [] for v in names}, {}, [('expo', bars - rest, key)]

        def fit_reg(ns, v):
            lo, hi, c = VO[v]
            o = min(range(-3, 4), key=lambda o: (sum(1 for _, _, p in ns if not lo <= p + 12 * o <= hi),
                                                 abs(sum(p for _, _, p in ns) / max(1, len(ns)) + 12 * o - c), o))
            return [(a, d, p + 12 * o) for a, d, p in ns], 12 * o

        def enter(v, ns, kind, shift, k_):
            written[v] += ns
            fixed.update((v, round(a, 4)) for a, _, _ in ns)
            first.setdefault(v, ns[0][0])
            a, z = ns[0][0], max(x + d for x, d, _ in ns)
            leads.append({'v': v, 'a': a, 'z': z, 'kind': kind, 'shift': shift, 'notes': ns, 'key': k_})
            self.log.append(dict({'block': block, 'beat': a, 'tf': 'plain' if kind != 'answer' else 'answer',
                                  'fn': 'voice', 'end': z}, **self.node('K1', (kind,))))

        def in_key(k_, v, x0):                 # (the subject moved into key k_: the nearest transposition, its mode)
            sh = (Key(k_).tonic - Key(key).tonic) % 12
            sh = sh - 12 if sh > 5 else sh
            ns = [(a + x0, d, p + sh) for a, d, p in subj]
            if Key(k_).minorish != minor:
                ns = _to_mode(ns, _transpose_key(key, sh % 12), k_)
            ns, o = fit_reg(ns, v)
            return ns, sh + o
        def mid_voice():                       # (the middle entry: the upper voice that led longest ago)
            return min((v for v in names if v != 'v4'),
                       key=lambda v: (max((L['a'] for L in leads if L['v'] == v), default=-1e9), v))
        # the exposition
        for j, v in enumerate(order[:n]):
            tj = t0 + j * gap * U
            ns, o = fit_reg([(a + tj, d, p) for a, d, p in (subj if j % 2 == 0 else ans)], v)
            enter(v, ns, 'subject' if j % 2 == 0 else 'answer', o + (7 if j % 2 else 0), key if j % 2 == 0 else D)
            w1 = tj + (gap * U if j < n - 1 else S * U)
            chart += [(tj + a, min(d, w1 - tj - a), s) for a, d, s in (hs if j % 2 == 0 else ha) if tj + a < w1 - _EPS]
            if V2 and j < n - 1 and gap > S + _EPS:     # (v2's codetta: the subject's head again, a step on)
                pk_ = pcs_of(key if j % 2 == 0 else D)
                hd = [x for x in subj if x[0] < U - _EPS]
                c0, cz = tj + S * U, tj + gap * U
                anc = _step(ns[-1][2], 1 if ns[-1][2] < VO[v][2] else -1, pk_)
                written[v] += [(c0 + a, min(d, cz - c0 - a), _step(anc, _steps_to(hd[0][2], p, pk_), pk_))
                               for a, d, p in hd if c0 + a < cz - _EPS]
        # the episodes, the middle and final entries, the close
        x0 = t0 + (bars - rest) * U
        k_prev = D if (n - 1) % 2 else key
        for i, (kind, nb, k_) in enumerate(plan):
            form.append((kind, nb, k_))
            z0 = x0 + nb * U
            nxt = next((p for p in plan[i + 1:] if p[0] in ('mid', 'fin')), None)
            if kind == 'ep':
                tech = techs.pop(0) if techs else tech
                rns = _FUGUE_EP[(tech, 'minor' if Key(k_).minorish else 'major')][-nb:]
                if nb > len(_FUGUE_EP[(tech, 'major')]):
                    rns = (rns[0],) * (nb - len(rns)) + tuple(rns)
                ch = [(x0 + j * U, U, _roman(k_, rn)) for j, rn in enumerate(rns)]
                chart += ch
                rest_v = None
                if nxt is not None:
                    rest_v = mid_voice() if nxt[0] == 'mid' else 'v4' if fin == 'bass' else 'v1'
                    rests[rest_v].append((x0, z0))
                sgb = -1 if rng.random() < 0.6 else 1           # (the imitation inverted, or as stated)
                act = [v for v in names if v in first and first[v] <= x0 + _EPS and v != rest_v]
                pk_ = pcs_of(key)
                src = [n_ for n_ in subj if U - _EPS <= n_[0] < 2 * U - _EPS]       # (the tail's first bar)
                if frag == 'head' or len(src) < 3 or len({q for _, _, q in src}) < 3:
                    src = [n_ for n_ in subj if n_[0] < U - _EPS]                  # (the head: the motto's)
                o_ = src[0][0]
                fr = [(a - o_, min(d, U - (a - o_)), _steps_to(src[0][2], p, pk_)) for a, d, p in src]
                if act:
                    A = act[0]
                    lo, hi, ca = VO[A]
                    pa = ca + (4 if tech == 'fifths' else -4)      # (room for the sequence to fall / rise)
                    for j, (x, _, sym) in enumerate(ch):
                        cts = _cpcs(sym)
                        pk = pcs_of(k_, sym)
                        tg = pa + (0 if j == 0 else (-2 if tech == 'fifths' else 2))
                        anc = min((q for q in range(lo - 12, hi + 13) if q % 12 in cts),     # (the link moves,
                                  key=lambda q: (3 * sum(1 for _, _, s_ in fr if not lo - 3 <= _step(q, s_, pk) <=  # in range)
                                                         hi + 3) + abs(q - tg), q))
                        if j == len(ch) - 1 and nb > 1:          # (the sequence's last bar: its first note held)
                            ns = [(x, U, anc)]
                        else:
                            ns = [(x + a, d, _step(anc, s_, pk)) for a, d, s_ in fr if a < U - _EPS]
                        written[A] += ns
                        fixed.update((A, round(a, 4)) for a, _, _ in ns)
                        self.log.append(dict({'block': block, 'beat': x, 'tf': 'head', 'fn': 'voice', 'end': x + U},
                                             **self.node('K1', ('head', 'episode'))))
                        if len(act) > 2:                         # (the second voice imitates it half a bar later)
                            Bv = act[1]
                            lb, hb, _ = VO[Bv]
                            xb = x + U / 2 if duple else x + 1.5
                            best = None
                            for sg in (sgb, -sgb):               # (under the leader: the least joint cost)
                                for dn in (7, 4, 9, 12):
                                    ab = _near(cts, min(q for _, _, q in ns) - dn, lb, hb)
                                    nb_ = [(xb + a, min(d, x + U - xb - a), _step(ab, sg * s_, pk)) for a, d, s_ in fr
                                           if xb + a < x + U - _EPS]
                                    c = vc.cp_cost(vc.cp_issues({A: ns, Bv: nb_}, order=names, strong=strong, t0=t0)) +                                         0.5 * sum(1 for _, _, q in nb_ if not lb <= q <= hb)
                                    if best is None or c < best[0] - _EPS:
                                        best = (c, nb_)
                            if j < len(ch) - 1 or nb == 1:
                                written[Bv] += best[1]
                        pa = anc
            elif kind in ('mid', 'fin'):
                if kind == 'mid':
                    v = mid_voice()
                    ns, sh = in_key(k_, v, x0)
                    enter(v, ns, 'middle', sh, k_)
                    lead_ns = ns
                elif fin == 'bass':
                    ns, sh = in_key(k_, 'v4', x0)
                    enter('v4', ns, 'final', sh, k_)
                    lead_ns = ns
                else:                                            # (the stretto: the top voice, then the bass)
                    best = None
                    for off in ((U, 2 * U) if S * U > 2 * U + _EPS else (U, U / 2 if duple else 1.5)):
                        top, sh1 = in_key(k_, 'v1', x0)
                        low, sh2 = in_key(k_, 'v4', x0 + off)
                        low = [(a, min(d, z0 - a), p) for a, d, p in low if a < z0 - _EPS]
                        c = vc.cp_cost(vc.cp_issues({'v1': top, 'v4': low}, strong=strong, t0=t0))
                        if best is None or c < best[0]:
                            best = (c, top, sh1, low, sh2)
                    _, top, sh1, low, sh2 = best
                    enter('v1', top, 'final', sh1, k_)
                    enter('v4', low, 'final', sh2, k_)
                    lead_ns = top + low
                chart += harmonize(lead_ns, k_, x0, nb, U, {0: 'i' if Key(k_).minorish else 'I'})
            else:                                                # (the close: a half cadence, the bass driving)
                pre = 'iv' if Key(k_).minorish else 'ii'
                rns = ([pre] * (nb - 1) + ['V7']) if nb > 1 else ['V7']
                chart += [(x0 + j * U, U, _roman(k_, rn)) for j, rn in enumerate(rns)]
                low = max((v for v in names if v in first), key=lambda v: names.index(v))
                r5 = _near({chord(_roman(k_, 'V')).root % 12}, VO[low][0] + 5, VO[low][0], VO[low][1])
                g_ = 0.5
                ns = [(x0 + (nb - 1) * U + g_ * j, g_ * 0.9 if j < int(U / g_) - 1 else g_, r5)
                      for j in range(int(U / g_))]
                written[low] += ns
                fixed.update((low, round(a, 4)) for a, _, _ in ns)
            x0 = z0
            k_prev = k_
        del k_prev
        # the chart: sorted, each chord to the next one's start, over the whole block
        chart = sorted(chart)
        ch2 = []
        for i, (a, d, s) in enumerate(chart):
            z = chart[i + 1][0] if i + 1 < len(chart) else end
            if z > a + _EPS:
                ch2.append((a, z - a, s))
        chart = ch2
        sec_keys = [(t0, key)]
        x_ = t0 + (bars - rest) * U
        for kind, nb, k_ in plan:
            sec_keys.append((x_, k_))
            x_ += nb * U
        for L in leads:                                          # (the answers sound in the dominant)
            if L['kind'] == 'answer':
                sec_keys.append((L['a'], D))
            elif L['kind'] == 'subject' and L['a'] > t0 + _EPS:
                sec_keys.append((L['a'], key))
        sec_keys.sort()

        def key_at(t):
            k_ = key
            for a, kk in sec_keys:
                if a <= t + _EPS:
                    k_ = kk
            return k_

        def scale(t):
            return pcs_of(key_at(t), _chart_at(chart, t))
        # the free voices: the counter-subject after a voice's own entry, free counterpoint else
        cs_ref = None
        Gf, Hf, Lf = (1.0, 2.0, 3.0) if duple else (1.5, 1.5, 3.0)

        bounds = sorted({round(L['a'], 6) for L in leads} | {round(a, 6) for a, _ in sec_keys})
        cs_spans = []

        def cs_lead(v, a):                     # (v2: the entry after the voice's own - a codetta / an overlap too)
            ms = [M for M in leads if M['v'] == v and M['z'] <= a + _EPS]
            if not ms:
                return None
            M = max(ms, key=lambda M: M['z'])
            nx = [L for L in leads if L['v'] != v and L['a'] > M['a'] + _EPS and L['kind'] != 'final']
            if not nx:
                return None
            L = min(nx, key=lambda L: L['a'])
            if L['a'] - U / 2 - _EPS <= a < L['z'] - _EPS and (abs(a - M['z']) < _EPS or abs(a - L['a']) <= U / 2 + _EPS):
                return L
            return None

        def gaps():
            out = []
            for v in names:
                if v not in first:
                    continue
                cov = sorted((a, a + d) for a, d, _ in written[v]) + sorted(rests[v])
                x = first[v]
                for a, z in sorted(cov) + [(end, end)]:
                    if a > x + 0.5 - _EPS:          # (a gap split at the sections' and entries' starts)
                        cut = [b for b in bounds if x + _EPS < b < a - _EPS]
                        out += [(p, q, v) for p, q in zip([x] + cut, cut + [a]) if q - p > 0.5 - _EPS]
                    x = max(x, z)
            return sorted(out, key=lambda g: (g[0], names.index(g[2])))
        for _ in range(256):
            gs = gaps()
            if not gs:
                break
            a, z, v = gs[0]
            lo, hi, c = VO[v]
            others = {w: written[w] for w in names if w != v and written[w]}
            sounding = [w for w in names if w != v and any(x - _EPS <= a < x + d - _EPS or a <= x < z
                                                           for x, d, _ in written[w])]
            above = [w for w in names[:names.index(v)] if w in sounding]
            below = [w for w in names[names.index(v) + 1:] if w in sounding]
            prev = [p for x, d, p in written[v] if x < a]
            start = prev[-1] if prev else None
            if V2:
                L = cs_lead(v, a)
            else:
                L = next((L for L in leads if L['v'] != v and abs(L['a'] - a) <= U / 2 + _EPS and
                          L['kind'] != 'final' and any(abs(M['z'] - a) < _EPS for M in leads if M['v'] == v)), None)
            if L is not None:                            # (the counter-subject)
                cz = min(z, L['z'])
                if cs_ref is None:
                    rh = vc.complement_rhythm(L['notes'], a, cz, grid=0.5, hold=1.0, longest=2.0)
                    ns = vc.counterline(others, rh, scale=scale, lo=lo, hi=hi, centre=c, start=start,
                                        harmony=chart, strong=strong, t0=t0, below=above, above=below)
                    cs_ref = {'notes': [(x - L['a'], d, p) for x, d, p in ns], 'shift': L['shift']}
                else:
                    base = [(L['a'] + x, d, p + L['shift'] - cs_ref['shift']) for x, d, p in cs_ref['notes']
                            if a - _EPS <= L['a'] + x < cz - _EPS]
                    best = None
                    for o in (-24, -12, 0, 12, 24):
                        ns = [(x, min(d, cz - x), _near(scale(x), p + o, lo - 12, hi + 12)) for x, d, p in base]
                        if not ns:
                            continue
                        out_ = sum(1 for _, _, p in ns if not lo <= p <= hi)
                        cc = vc.cp_cost(vc.cp_issues(dict(others, **{v: ns}), order=names, strong=strong, t0=t0,
                                                     span=(a, cz)))
                        if best is None or (out_, cc) < best[0]:
                            best = ((out_, cc), ns)
                    ns = best[1] if best else []
                    if best and (best[0][0] or (V2 and best[0][1] > V2['cs_cost'])):
                        ns = []                          # (v2: a restatement that clashes - free counterpoint)
                if ns and V2:
                    cs_spans.append((v, a, cz))
                if not ns:                               # (no room for it: free counterpoint there)
                    rh = vc.complement_rhythm(L['notes'], a, cz, grid=Gf, hold=Hf, longest=Lf)
                    ns = vc.counterline(others, rh, scale=scale, lo=lo, hi=hi, centre=c, start=start,
                                        harmony=chart, strong=strong, t0=t0, below=above, above=below)
            else:
                cz = z
                lead_now = [n_ for w in names if w != v for n_ in written[w] if n_[0] < z and n_[0] + n_[1] > a]
                lowest = not below and v == max((w for w in names if w in first), key=lambda w: names.index(w))
                if lowest:
                    rh = [(x, min(strong, z - x)) for x in _frange(a, z, strong)]
                else:
                    rh = vc.complement_rhythm(lead_now, a, z, grid=Gf, hold=Hf, longest=Lf)
                ns = vc.counterline(others, rh, scale=scale, lo=lo, hi=hi, centre=c, start=start, harmony=chart,
                                    strong=strong, t0=t0, below=above, above=below, bass=lowest)
            if not ns:
                ns = [(a, cz - a, start if start is not None else _near(scale(a), c))]
            written[v] = sorted(written[v] + ns)
        parts = vc.repair({v: ns for v, ns in written.items() if ns}, scale=scale, harmony=chart, order=names,
                          movable=lambda v, n_: (v, round(n_[0], 4)) not in fixed, strong=strong, t0=t0,
                          ranges={v: VO[v][:2] for v in names}, **({'rounds': V2['rounds']} if V2 else {}))
        voices = {v: _mono([n_ for n_ in parts.get(v, []) if n_[0] < end - _EPS]) for v in names}
        voices = {v: [(a, min(d, end - a), p) for a, d, p in ns] for v, ns in voices.items()}
        iss = vc.cp_issues({v: ns for v, ns in voices.items() if ns}, order=names, strong=strong, t0=t0)
        low = voices['v4']
        if 'v4' in first:
            bass = [(a, d, p - 12) for a, d, p in low if p - 12 >= 28]
        else:
            bass = []
        horn = beat_s is None or min(d for _, d, _ in subj) * beat_s >= F_['horn_s']
        tw = {t_: w_ for t_, w_ in (V2['tex_dance'] if V2 and dance else V2['tex'] if V2 else F_['tex']).items()
              if horn or 'horn' not in t_}
        extra = {}
        if V2:                                 # (v2: the pedal, the pad's end, the counter-subject, the entries)
            self.fug_subj = (key, subj, S)
            starts = [t0 + j * gap * U for j in range(n)]
            xz = t0 + (bars - rest) * U
            ped = []
            for j, tj in enumerate(starts):
                if 'v4' in order[:j + 1]:
                    break
                z_ = starts[j + 1] if j + 1 < n else xz
                k_ = key if j % 2 == 0 else D
                ped.append((tj, z_ - tj, _near({Key(k_).tonic % 12}, 43, 36, 50)))
            pu = V2['pad_until']
            cs_notes = sorted(n_ for v, a, z in cs_spans for n_ in voices[v] if a - _EPS <= n_[0] < z - _EPS)
            extra = {'pedal': ped, 'pad': starts[pu] if pu < n else xz, 'cs': cs_spans, 'cs_notes': cs_notes,
                     'entries': starts, 'gap': gap, 'subject': [(a, d, p) for a, d, p in subj]}
        return {'voices': voices, 'chart': chart, 'leads': [(L['v'], L['a'], L['z']) for L in leads], 'bass': bass,
                'tex': _pick(rng, tw), 'form': form, 'issues': vc.summary(iss), 'n_issues': len(iss), **extra,
                'keys': [key] + [k_ for _, _, k_ in plan]}

    # -- the retransition: a dominant pedal, the motto's head rising (liquidated: faster, then one held note)
    def retrans(self, block: str, key: str, t0: float, bars: int, build: str = 'tremolo', frame: str = 'pedal'):
        """The build into the climax (BUILDS) -> (melody, chart, pedal, counter, voices): 'tremolo' / 'pulse' /
        'subito' the kernel rising per half bar, the last two bars diminished; 'stretto' the whole motto's entries
        closer and closer (2 bars, a bar, half a bar), melody and counter in turn, a step up each; 'calls' the head
        called and answered inverted, the answer closer each time; 'bass' the motto in the bass a step up per two
        bars (the texture's 'theme': 'bass') under a high dominant pedal; 'fugato' a fugato whose entries come a bar
        apart. Every build ends on the held top note of V7 (the retransition's end). frame (BUILD_FRAMES, round o4 -
        o3's judges: "a bare dominant pedal, a woodwind line climbing" in 7 of 14): the harmony under it - 'pedal'
        the dominant pedal; 'ascent' a bass rising by step to V, 'circle' a sequence of fifths, 'lament' a bass
        falling by step to V (the line above falls too) - the 'pedal' slot plays the moving bass."""
        U = self.U
        V = _roman(key, 'V')
        V7 = _roman(key, 'V7')
        K = Key(key)
        # (round o18b, SET_PLAN: `build` a GESTURES name - its writer and its pedal's bars)
        G_ = GESTURES.get(build) if SET_PLAN and SET_PLAN.get('builds') else None
        if G_:
            build = G_['writer']
        if build == 'bass':                      # (the motto in the bass: under the high pedal only)
            frame = 'pedal'
        seq = (BUILD_FRAMES.get(frame) or {}).get('minor' if K.minorish else 'major')
        bass_line = None
        i64 = _roman(key, 'i' if K.minorish else 'I') + '/' + chord(V).root_name
        iv = _roman(key, 'iv' if K.minorish and K.mode != 'dorian' else 'IV') + '/' + chord(V).root_name
        plan = [V, i64, V7, iv, V, V7, i64, V7]
        # (round o11: the frame before the dominant pedal's RT_PEDAL bars - its last bar the lead-in over V7)
        P_ = int(math.ceil(RT_PEDAL['bars'] / self.scale - _EPS)) if RT_PEDAL else 1
        if G_:
            P_ = max(1, int(math.ceil(G_['pedal'] / self.scale - _EPS)))
        if seq:
            n = max(1, bars - P_) if RT_PEDAL else bars - 1
            if frame == 'ascent':                 # (each chord a bar or more, the rise spread over the block)
                seq = seq[-n:] if len(seq) >= n else seq
                cuts = [round(i * n / len(seq)) for i in range(len(seq) + 1)]
                rows = [(cuts[i], cuts[i + 1] - cuts[i], rn, dg) for i, (rn, dg) in enumerate(seq)
                        if cuts[i + 1] > cuts[i]]
            else:                                 # (a sequence: the cycle again)
                rows = [(i, 1, seq[i % len(seq)][0], seq[i % len(seq)][1]) for i in range(n)]
            chart, bass_line, prev = [], [], 43
            for b0, nb, rn, dg in rows:
                sym = _roman(key, rn)
                pc = K.degree(dg, octave=4) % 12
                if chord(sym).root % 12 != pc:
                    from ..theory import _spell
                    sym = f"{sym}/{_spell(pc, K.minorish)}"
                chart.append((t0 + b0 * U, nb * U, sym))
                prev = _near({pc}, prev, 36, 50)
                bass_line.append((t0 + b0 * U, nb * U, prev))
            dom_ = _near({chord(V).root % 12}, prev, 36, 50)
            for i in range(n, bars - 1):          # (the pedal: the dominant held under V / I6-4 / V7 / IV6-4)
                chart.append((t0 + i * U, U, plan[(i - n) % len(plan)]))
                bass_line.append((t0 + i * U, U, dom_))
            chart.append((t0 + (bars - 1) * U, U, V7))
            bass_line.append((t0 + (bars - 1) * U, U, dom_))
            if len(bass_line) > 1 and bass_line[-2][2] == dom_ and RT_PEDAL:    # (one held pedal note)
                b_ = [x for x in bass_line if x[0] < t0 + n * U - _EPS]
                bass_line = b_ + [(t0 + n * U, (bars - n) * U, dom_)]
            if G_ and G_.get('deceptive') and bars >= 5:
                # (round o18b, GESTURES 'deceptive': V7 - vi (bVI) - V7 in the last three bars, the bass 5 - 6 - 5)
                x3 = t0 + (bars - 3) * U
                dec = _deceptive(key)
                chart = [(a_, min(d_, x3 - a_), s_) for a_, d_, s_ in chart if a_ < x3 - _EPS] + \
                    [(x3, U, V7), (x3 + U, U, dec), (x3 + 2 * U, U, V7)]
                b_ = [(a_, min(d_, x3 - a_), p_) for a_, d_, p_ in bass_line if a_ < x3 - _EPS]
                bass_line = b_ + [(x3, U, dom_), (x3 + U, U, _near({chord(dec).root % 12}, dom_ + 1, 36, 50)),
                                  (x3 + 2 * U, U, dom_)]
        else:
            chart = [(t0 + i * U, U, plan[i % len(plan)]) for i in range(bars)]
            chart[-1] = (chart[-1][0], U, V7)
        csyms = None
        if CHROMA_CADENCE and CHROMA_CADENCE.get('recap') and build != 'bass':
            # (the code review's A2: the chromatic predominant before the return's dominant pedal, the harmonic rhythm
            # two chords a bar into it - the pedal frame: its first bars, a frame: its last bars before the pedal)
            got = self._chroma_rt(block, key, t0, bars, U, P_, chart, bass_line, rows if seq else None,
                                  n if seq else None, V, plan)
            if got:
                chart, bass_line, csyms = got
        ev_ = None
        if CHROMA_EVENT and CHROMA_EVENT.get('recap') and build != 'bass':
            # (round o15b: the chord-block chain into the dominant pedal - CHROMA_EVENT)
            got = self._event_rt(block, key, t0, bars, U, P_, chart, bass_line, rows if seq else None,
                                 n if seq else None, V, plan)
            if got:
                chart, bass_line, esyms = got
                csyms = (csyms or set()) | esyms
                ev_ = self.events[block]
        dirn = -1 if frame == 'lament' else 1
        mel, ans, voices = [], [], {}
        pv = pcs_of(key, V)
        a = self.anchor(key, V, self.centre + (4 if dirn < 0 else -4))
        end = t0 + (bars - 1) * U
        gp = self.d.get('retrans_end', 'gp')
        if build in ('stretto', 'calls'):
            t, gap, j = t0, (2 * U if bars > 6 else U), 0
            a = self.anchor(key, V, self.centre + (3 if dirn < 0 else -6))
            while t < end - _EPS:
                if build == 'stretto':
                    tf, who = (() if gap >= U else ('head',)), j % 2
                    ns = self.state(block, t, a, pv, tf, fn='counter' if who else 'melody')
                    ns = [(x, min(d, min(end, t + 2 * gap) - 0.25 - x), p) for x, d, p in ns
                          if x < min(end, t + 2 * gap) - 0.25 - _EPS]
                    (ans if who else mel).extend(ns)
                    a = _step(a, (2 if gap >= U else 1) * dirn, pv)
                    t += gap
                    j += 1
                    if j in (2, 4):
                        gap = max(U / 2, gap / 2)
                else:                             # (the call, its inverted answer `gap` later; the pair a step up)
                    z = min(end, t + 2 * gap)
                    for x, tf, fn, q in ((t, ('head',), 'melody', a), (t + gap, ('head', 'invert'), 'counter',
                                                                         _step(a, 4, pv))):
                        if x >= z - _EPS:
                            continue
                        ns = [(y, min(d, z - 0.25 - y), p) for y, d, p in self.state(block, x, q, pv, tf, fn=fn)
                              if y < z - 0.25 - _EPS]
                        (mel if fn == 'melody' else ans).extend(ns)
                    a = _step(a, dirn, pv)
                    t = z
                    gap = max(U / 2, gap / 2)
        elif build == 'bass':
            a = _near({_member(V, self.m['member'])}, 48)
            for i in range(0, bars - 1, 2):
                z = min(end, t0 + (i + 2) * U)
                mel += [(x, min(d, z - 0.25 - x), p) for x, d, p in self.state(block, t0 + i * U, a, pv, fn='bass')
                        if x < z - 0.25 - _EPS]
                a = _step(a, 2, pv)
        elif build == 'fugato':
            vs, _ = self.fugato(block, key, t0, bars - 1, gap=U)
            voices = {v: [n for n in ns if n[0] < end - _EPS] for v, ns in vs.items()}
        elif build == 'lowbrass':                # (round o18b: the motto augmented in the bass, a third up each)
            a = _near({_member(V, self.m['member'])}, 47)
            span = max(x + d for x, d, _ in motto_notes(self.m, 0.0, 60, pv, ('augment',)))
            span = U * max(1, math.ceil(span / U - _EPS))
            x = t0
            while x < end - _EPS:
                z = min(end, x + span)
                mel += [(y, min(d, z - 0.25 - y), p) for y, d, p in self.state(block, x, a, pv, ('augment',),
                                                                               fn='bass') if y < z - 0.25 - _EPS]
                a = _step(a, 2, pv)
                x += span
        else:
            p0 = t0 + (bars - P_) * U if RT_PEDAL and RT_PEDAL.get('imitate', True) else end
            # (round o18b: the 'wave' writer steps by the piece's contour - CONTOURS, never 'rise' - not a step a bar)
            wave = CONTOURS.get(self.d.get('contour') if self.d.get('contour') != 'rise' else 'wave',
                                CONTOURS['wave']) if build == 'wave' else None
            nst = 0
            for i in range(bars - 1):             # the kernel per half bar, rising; the last two bars diminished
                t = t0 + i * U
                per = 2 if i < bars - 3 else 4
                for k in range(per):
                    if k % 2 == 0:
                        a = _step(a, dirn * (wave[nst % len(wave)] if wave else 1), pv)
                        nst += 1
                    if MOTTO_RATION.get('frag') and k % 2 == 1 and mel:    # (round o10: the kernel's answer free)
                        mel += self.free(mel[-1][2], _step(a, dirn, pv), t + k * U / per, U / per, pv)
                        continue
                    a_, tf_ = _seq_pair(self.m, a, k, pv)
                    ns_ = self.state(block, t + k * U / per, a_, pv,
                                     ('kernel',) + tf_ + (('diminish',) if per == 4 else ()))
                    mel += ns_
                    x_ = t + k * U / per
                    if x_ >= p0 - _EPS and per == 2 and k == 0:
                        # (round o11: over the pedal the head answered in imitation - half a bar later, an octave
                        # under, in another choir; RT_PEDAL)
                        z_ = min(end, x_ + U)
                        ans += [(y + U / 2, min(d, z_ - y - U / 2 - 0.25), q - 12) for y, d, q in
                                self.state(block, x_, a_, pv, ('kernel',) + tf_, fn='counter')
                                if y + U / 2 < z_ - 0.25 - _EPS]
        mel = _mono(mel)
        last = mel[-1][2] if mel else max((ns[-1][2] for ns in voices.values() if ns), default=a)
        top = _near(_cpcs(V7), (last if build != 'bass' else self.centre) + 2)
        z = end + U - (1.0 if gp == 'gp' else 0.0)
        lead = [n for n in self.state(block, end, top, pcs_of(key, V7), ('head',), fill=z) if n[0] < z - _EPS] \
            if RETRANS_LEAD and gp != 'fermata' else []
        # (round o9 - o8's judges, TZKN: "a static retransition": the motto's head over V7 as the lead-in to the
        # climax - RETRANS_LEAD; the fermata keeps its held top note)
        mel += [(x, min(d, z - x), p) for x, d, p in lead] or [(end, z - end, top)]
        pedal = [(t0, bars * U - (1.0 if gp == 'gp' else 0.0), _near({chord(V).root % 12}, 40, 36, 47))]
        if build == 'bass':                       # (the dominant held high: the horns' pedal over the bass's motto)
            pedal = [(t0, bars * U - (1.0 if gp == 'gp' else 0.0), _near({chord(V).root % 12}, 60, 55, 67))]
        elif bass_line:                           # (a moving frame: the bass walks)
            a_, d_, p_ = bass_line[-1]
            pedal = bass_line[:-1] + [(a_, d_ - (1.0 if gp == 'gp' else 0.0), p_)]
        if ev_:                                   # (the chain's span: its top voice the melody, no other line)
            a_e, z_e = ev_['cut']

            def out_(ns):
                return [(x, min(d, a_e - x), q) for x, d, q in ns if x < a_e - _EPS] + \
                    [(x, d, q) for x, d, q in ns if x >= z_e - _EPS]
            mel = sorted(out_(mel) + list(ev_['tops']))
            ans = out_(ans)
            voices = {v: out_(ns) for v, ns in voices.items()}
        voices = {v: fit_line(ns, chart, key, chroma=csyms) for v, ns in voices.items()}
        return fit_line(mel, chart, key, chroma=csyms), chart, pedal, _mono(fit_line(ans, chart, key, chroma=csyms)), \
            voices

    def _chroma_rt(self, block, key, t0, bars, U, P_, chart, bass_line, rows, n, V, plan):
        """CHROMA_CADENCE in the retransition (Writer.retrans): (chart, bass line, the chromatic symbols) with the
        accelerated chromatic predominant into the dominant pedal - the pedal frame's first 'bars' bars (the pedal
        from there; form_rows grew the block), a frame's last 'bars' bars before the pedal - or None (no room, a
        church mode). The record goes to self.chroma[block] (material: blk['chroma'])."""
        cb = int(CHROMA_CADENCE.get('bars', 2))
        pre_n = n if rows is not None else max(0, bars - P_ if RT_PEDAL else bars - 1)
        cb = min(cb, pre_n)
        if cb < 1:
            return None
        a0 = t0 + ((pre_n - cb) * U if rows is not None else 0.0)
        z0 = a0 + cb * U
        first = next((rn for b0, nb, rn, _ in rows if b0 <= pre_n - cb < b0 + nb), None) if rows is not None else None
        got = chroma_pre(key, a0, U, cb, 'V', first, random.Random(f"symphony:chroma:{block}:{key}:{self.m}"))
        if not got:
            return None
        crows, rec = got
        vr = chord(V).root % 12
        if rows is not None:
            dom = next(p for a, _, p in reversed(bass_line) if a >= z0 - _EPS)
            prev = next((p for a, _, p in reversed(bass_line) if a < a0 - _EPS), dom)
        else:
            dom = _near({vr}, 40, 36, 47)
            prev = dom
        new_bass = []
        for i, (a, d, sy) in enumerate(crows):
            pc = chord(sy).bass_pc % 12
            ref = dom if i == len(crows) - 1 else prev
            prev = min((q for q in range(ref - 6, ref + 7) if q % 12 == pc and 33 <= q <= 52),
                       key=lambda q: (abs(q - ref), q), default=_near({pc}, ref, 36, 50))
            new_bass.append((a, d, prev))

        def cut(line):
            return [(a, min(d, a0 - a), s) for a, d, s in line if a < a0 - _EPS]
        if rows is not None:
            chart = cut(chart) + crows + [r for r in chart if r[0] >= z0 - _EPS]
            bass_line = cut(bass_line) + new_bass + [r for r in bass_line if r[0] >= z0 - _EPS]
        else:
            V7 = _roman(key, 'V7')
            chart = crows + [(t0 + i * U, U, plan[(i - cb) % len(plan)]) for i in range(cb, bars)]
            chart[-1] = (chart[-1][0], U, V7)
            bass_line = new_bass + [(z0, t0 + bars * U - z0, dom)]
        if not hasattr(self, 'chroma'):
            self.chroma = {}
        self.chroma[block] = rec
        return chart, bass_line, {chroma_symbol(key, r[2]) for r in rec}

    def _event_rt(self, block, key, t0, bars, U, P_, chart, bass_line, rows, n, V, plan):
        """CHROMA_EVENT 'recap' in the retransition (Writer.retrans): the chord-block chain (EVENT_CHAINS, drawn per
        piece) over the last 'chain' song bars before the dominant pedal, into V -> (chart, bass line, the chain's
        symbols), or None (a church mode, no room, no voicing). The record (the chords voiced, the melody's top notes,
        the arrival on V) goes to self.events[block] (material: blk['event'])."""
        K = Key(key)
        if K.mode not in ('major', 'minor'):
            return None
        cb = int(math.ceil(CHROMA_EVENT.get('chain', 4) / self.scale - _EPS))
        pre_n = n if rows is not None else max(0, bars - P_ if RT_PEDAL else bars - 1)
        cb = min(cb, pre_n)
        if cb < 1:
            return None
        a0 = t0 + (pre_n - cb) * U
        z0 = a0 + cb * U
        rng = random.Random(f"symphony:event:{block}:{key}:{self.m}")
        cname = _pick(rng, {c: EVENT_CHAIN_W[c] for c in sorted(EVENT_CHAINS)})
        spec = EVENT_CHAINS[cname]['minor' if K.minorish else 'major']
        slots = 2 * cb
        if slots < len(spec):
            spec = spec[-slots:]
        cuts = [round(i * slots / len(spec)) for i in range(len(spec) + 1)]
        seq = [_ev_chord(key, nm, bi) for nm, bi in spec] + [_ev_chord(key, 'V', 0)]
        starts = [a0 + cuts[i] * U / 2 for i in range(len(spec))] + [z0]
        durs = [(cuts[i + 1] - cuts[i]) * U / 2 for i in range(len(spec))] + [U / 2]
        b_prev = next((p for a, _, p in reversed(bass_line or []) if a < a0 - _EPS), 43)
        hi = int(min(86, self.centre + 10))
        got = None
        for n_ in (4, 3):
            got = got or _event_voice(seq, n=n_, lo=hi - 28, hi=hi, centre=hi - 11, top0=self.centre + 4, bass0=b_prev)
        if not got:
            return None
        vr = chord(V).root % 12
        dom = _near({vr}, 40, 36, 47)
        crows = [(starts[i], durs[i], seq[i]['sym']) for i in range(len(spec))]
        cbass = [(starts[i], durs[i], got[i][0]) for i in range(len(spec))]

        def cut(line):
            return [(a, min(d, a0 - a), s) for a, d, s in line if a < a0 - _EPS]
        if rows is not None:
            chart = cut(chart) + crows + [r for r in chart if r[0] >= z0 - _EPS]
            bass_line = cut(bass_line) + cbass + [r for r in bass_line if r[0] >= z0 - _EPS]
        else:
            V7 = _roman(key, 'V7')
            j0 = pre_n - cb
            chart = [r for r in chart if r[0] < a0 - _EPS] + crows + \
                [(t0 + i * U, U, plan[(i - pre_n) % len(plan)]) for i in range(pre_n, bars)]
            chart[-1] = (chart[-1][0], U, V7)
            bass_line = ([(t0, a0 - t0, dom)] if j0 > 0 else []) + cbass + [(z0, t0 + bars * U - z0, dom)]
        if not hasattr(self, 'events'):
            self.events = {}
        self.events[block] = {
            'kind': 'chain', 'chain': cname, 'a': a0, 'z': z0, 'cut': (a0, z0), 'top_at': starts[len(spec) - 1],
            'chords': [(x, d, c['sym'], b, up) for x, d, c, (b, up) in zip(starts, durs, seq, got)],
            'tops': [(starts[i], durs[i], got[i][1][-1]) for i in range(len(spec))]}
        return chart, bass_line, {c['sym'] for c in seq[:-1]}

    # -- the codas
    def coda(self, block: str, key: str, t0: float, bars: int, kind: str, plan: str | None = None, theme2=None):
        """(melody, chart, answer) of the coda: kind 'triumph' / 'dissolve' by its plan (CODA_PLANS, round o5 - o4's
        judges: the 6/8 pieces "share one coda plan"): 'stretto' the motto augmented, then its kernel in stretto
        climbing; 'pedal' the motto's head called and answered (inverted, a third over) bar by bar over I - IV - I - V,
        a step up per pair; 'hymn' the second theme's head augmented as a chorale, then the run home; 'descent' the
        head falling, augmented; 'echo' the head and its echo an octave under, a step lower each pair; 'memory' the
        second theme's head remembered, then its head augmented a step lower - the last bars the tonic."""
        U = self.U
        K = Key(key)
        I = _roman(key, 'i' if K.minorish else 'I')
        IV = _roman(key, 'iv' if K.minorish and K.mode != 'dorian' else 'IV')
        pcs = pcs_of(key)
        mel, ans = [], []
        if plan in ('hymn', 'memory') and not theme2:
            plan = 'stretto' if kind == 'triumph' else 'descent'
        if plan in ('pedal', 'echo') and bars >= 4:
            up = plan == 'pedal'
            a = self.anchor(key, I, self.centre + (1 if up else -2))
            seq = [I, IV, I, _roman(key, 'V7')]
            chart = [(t0 + i * U, U, seq[i % 4]) for i in range(bars - 2)] + \
                [(t0 + (bars - 2) * U, U, _roman(key, 'V7')), (t0 + (bars - 1) * U, U, I)]
            q_prev = None
            for i in range(bars - 2):
                x = t0 + i * U
                sym = chart[i][2]
                q = _near({_member(sym, self.m['member'])}, a + (i // 2) * (2 if up else -2))
                if i % 2 == 0 and q_prev is not None and q == q_prev:
                    # (round o9 - o8's judges, PZSU 58-63: "the same two bars three times": the chord member snapped
                    # each pair back to one pitch - the next chord tone over / under the pair before)
                    rng_ = range(q + 1, q + 13) if up else range(q - 1, q - 13, -1)
                    q = next((y for y in rng_ if y % 12 in _cpcs(sym)), q)
                if i % 2 == 0:
                    q_prev = q
                    mel += [(y, min(d, x + U - 0.25 - y), p) for y, d, p in
                            self.state(block, x, q, pcs_of(key, sym), ('head',)) if y < x + U - 0.25 - _EPS]
                else:
                    q2 = _step(q, 2, pcs_of(key, sym)) if up else q - 12
                    ans += [(y, min(d, x + U - 0.25 - y), p) for y, d, p in
                            self.state(block, x, q2, pcs_of(key, sym), ('head', 'invert') if up else ('head',),
                                       fn='counter') if y < x + U - 0.25 - _EPS]
            last = (mel or ans)[-1][2]
            goal = _near({K.tonic}, last)
            mel += run_to(_step(goal, 2, pcs), goal, t0 + (bars - 2) * U, int(round(U / (0.5 if up else 1.0))),
                          0.5 if up else 1.0, pcs_of(key, chart[-2][2]))
            mel.append((t0 + (bars - 1) * U, U, goal))
            mel = _unrepeat(_mono([n for n in mel if n[0] < t0 + bars * U - _EPS]), t0, self.bar, pcs)
            return fit_line(mel, chart, key), chart, _mono(fit_line(_unrepeat(ans, t0, self.bar, pcs), chart, key))
        if plan in ('hymn', 'memory') and bars >= 4:
            k2, b2 = theme2
            sh = K.tonic - Key(k2).tonic
            head = sorted((a, d, p + sh) for a, d, p in b2 if a < 2 * U - _EPS)
            aug = 2.0 if plan == 'hymn' and self.scale == 1 else 1.0     # (round o7: the scherzo's at its values)
            head = [(t0 + a * aug, d * aug, p) for a, d, p in head if a * aug < (bars - 2) * U - _EPS]
            c_ = self.centre + (2 if plan == 'hymn' else -3)
            while head and sum(p for _, _, p in head) / len(head) > c_ + 4:
                head = [(a, d, p - 12) for a, d, p in head]
            while head and sum(p for _, _, p in head) / len(head) < c_ - 8:
                head = [(a, d, p + 12) for a, d, p in head]
            mel = [(a, d, _near(pcs, p)) for a, d, p in head]
            # (round o8 - o7's judges: "the coda without the motto", 4 of 8 new pieces: the second theme's head, then
            # the MOTTO recalled before the close - 'hymn' the whole motto a step over the tonic, 'memory' its head
            # a step lower, quiet; CODA_RECALL bars before the last two)
            rec = next((r_ for r_ in (CODA_RECALL['bars'], 2) if bars - 2 >= r_ + 2), 0)
            z_head = t0 + (bars - 2 - rec) * U
            mel = [(a, min(d, z_head - a), p) for a, d, p in mel if a < z_head - _EPS]
            self.log.append({'block': block, 'beat': t0, 'tf': 'cantilena', 'fn': 'melody', 'end': z_head,
                             'theme2': True})
            if rec:
                a_ = self.anchor(key, I, self.centre + (1 if plan == 'hymn' else -4))
                tf_ = () if plan == 'hymn' else ('head',)       # (at its own speed: an augmented motto's passing
                #                                                     notes were snapped to the chords - another tune)
                # (round o12 - o11's judges: "codas that sustain instead of transforming", YFQA 87-99 / ARFK 96-107:
                # the motto recalled per CODA_RECALL 'unit' bars - the hymn's rising a step, the memory's head
                # falling a step, every other one inverted)
                u_ = CODA_RECALL.get('unit', rec) * U
                zz = t0 + (bars - 2) * U
                x_, j_ = z_head, 0
                while x_ < zz - _EPS:
                    ze = min(zz, x_ + u_)
                    st_ = (_step(a_, j_ if plan == 'hymn' else -j_, pcs),
                           tf_ + (('invert',) if plan != 'hymn' and j_ % 2 else ()))
                    mel += [(a, min(d, ze - 0.25 - a), p) for a, d, p in
                            self.state(block, x_, st_[0], pcs, st_[1], fill=ze - 0.5) if a < ze - 0.25 - _EPS]
                    x_, j_ = ze, j_ + 1
            mel = _mono([(a, min(d, t0 + (bars - 2) * U - a), p) for a, d, p in mel
                         if a < t0 + (bars - 2) * U - _EPS])
            last = mel[-1][2] if mel else self.centre
            goal = _near({K.tonic}, last)
            if plan == 'hymn':
                mel += run_to(last, goal, t0 + (bars - 2) * U, int(round(U)), 1.0, pcs)[1:]
                mel.append((t0 + (bars - 1) * U, U, goal))
            else:
                mel.append((t0 + (bars - 2) * U, 2 * U, goal))
            mel = _unrepeat(_mono([n for n in mel if n[0] < t0 + bars * U - _EPS]), t0, self.bar, pcs)
            forced = {0: 'i' if K.minorish else 'I', bars - 1: 'i' if K.minorish else 'I', (bars - 2, 1): 'V'}
            chart = harmonize(mel, key, t0, bars, U, forced, split={bars - 2})
            return fit_line([n for n in mel if n[0] < z_head - _EPS], chart, key, strict=0.75) + \
                fit_line([n for n in mel if n[0] >= z_head - _EPS], chart, key), chart, []
        if kind == 'triumph':
            a = self.anchor(key, I, self.centre + 3)
            t = t0
            half = max(2, bars // 2)
            if self.scale == 1:               # (the motto in the brass, augmented)
                ns = self.state(block, t, a, pcs, ('augment',), fill=t0 + half * U - 0.5)
                mel += [n for n in ns if n[0] < t0 + half * U - _EPS]
            else:
                # (round o7 - o6's judges: the scherzo's coda "the theme augmented into whole-bar notes" - the
                # internal values sound doubled in the fast 3/4: the motto at its own speed, a statement per bar of
                # the song, rising a step every second one)
                j = 0
                while t < t0 + half * U - _EPS:
                    z = min(t + U / 2, t0 + half * U)
                    mel += [(y, min(d, z - y), p) for y, d, p in
                            self.state(block, t, _step(a, j // 2, pcs), pcs, ('diminish',)) if y < z - _EPS]
                    t, j = z, j + 1
            t = t0 + half * U
            st = 0
            while t < t0 + (bars - 1) * U - _EPS:                     # the kernel in stretto, climbing
                dt = U / 2 if self.scale == 1 else U / 4
                if MOTTO_RATION.get('frag') and st % 2 == 1 and mel:   # (round o10: every other one a free run)
                    mel += self.free(mel[-1][2], _step(a, st + 1 if self.scale == 1 else (st + 1) // 2, pcs), t, dt,
                                     pcs)
                elif self.scale == 1:
                    mel += self.state(block, t, _step(a, st, pcs), pcs, ('kernel',))
                else:                         # (the scherzo's: the kernel at its own speed, a step every two)
                    mel += self.state(block, t, _step(a, st // 2, pcs), pcs, ('kernel', 'diminish'))
                t += dt
                st += 1
            top = _near({K.tonic}, mel[-1][2] + 1 if mel else a + 3)
            mel.append((t0 + (bars - 1) * U, U, top))
            # (round o8: only the first half bar pinned - a whole bar of I under the augmented motto snapped its
            # passing notes to the chord: another tune, coda_mot)
            forced = {(0, 0): 'i' if K.minorish else 'I', bars - 1: 'i' if K.minorish else 'I', (bars - 2, 1): 'V'}
            split = {bars - 2}
        else:
            a = self.anchor(key, I, self.centre - 2)
            t = t0
            k = 0
            while t < t0 + (bars - 2) * U - _EPS:
                # (round o8: the descent opens with the whole motto - "the coda without the motto" -, then its head
                # augmented falling)
                ns_ = self.state(block, t, _step(a, -k, pcs), pcs, ('head', 'augment') if k else ())
                z_ = t + 2 * U
                mel += [(y, min(d, z_ - 0.25 - y), p) for y, d, p in ns_ if y < z_ - 0.25 - _EPS] or ns_[:1]
                t = z_
                k += 1
            mel.append((t0 + (bars - 2) * U, 2 * U, _near({K.tonic}, a - 2)))
            forced = {0: 'i' if K.minorish else 'I', bars - 1: 'i' if K.minorish else 'I'}
            split = set()
        mel = _unrepeat(_mono([n for n in mel if n[0] < t0 + bars * U - _EPS]), t0, self.bar, pcs)
        chart = harmonize(mel, key, t0, bars, U, forced, split=split)
        if kind == 'triumph' and self.scale == 1 and CODA_CANON:
            # (round o9 - o8's judges: "the coda as 16ths over a brass chorale, the theme absent": the motto at its own
            # speed over its augmentation in the coda's first half - the violins' counter, CODA_CANON)
            half = max(2, bars // 2)
            return fit_line(mel, chart, key), chart, self.canon(block, 'augment', key, chart, t0, half + 2,
                                                                 [n for n in mel if n[0] < t0 + half * U - _EPS])
        return fit_line(mel, chart, key), chart, []

    # -- a theme combined: the motto against it, the second theme under it (round o4: the recapitulation)
    def motto_counter(self, block: str, key: str, ch, t0: float, bars: int, below: float = 5, tf=('head',),
                      first: int = 1) -> list:
        """The motto against a theme: a statement (tf) every two bars from bar `first`, on its chord's member
        `below` the centre, each cut before the next and before the last bar."""
        U, m = self.U, self.m
        pcs = pcs_of(key)
        cnt = []
        for j in range(first, bars - 1, MOTTO_RATION.get('counter', 2)):
            x = t0 + j * U
            a = _near({_member(_chart_at(ch, x), m['member'])}, self.centre - below)
            z = min(t0 + (bars - 1) * U, x + 2 * U)
            cnt += [(y, min(d, z - 0.25 - y), p) for y, d, p in self.state(block, x, a, pcs, tf, fn='counter')
                    if y < z - 0.25 - _EPS]
        return _mono(fit_line(cnt, ch, key))

    def theme_under(self, theme2, key: str, t0: float, bars: int, ch) -> list:
        """The second theme (theme2 = (key, notes from 0)) as a counter-line under a returning first theme: in
        `key`, an octave or more under the centre (over C3), cut to the block, fitted to its chords."""
        k2, b2 = theme2
        sh = Key(key).tonic - Key(k2).tonic
        seg = [(t0 + a, d, p + sh) for a, d, p in b2 if a < (bars - 1) * self.U - _EPS]
        if not seg:
            return []
        if Key(k2).minorish != Key(key).minorish:     # (round o6: in the block's mode - the same tune, not snapped)
            seg = _to_mode(seg, _transpose_key(k2, sh % 12), key)
        while max(p for _, _, p in seg) > self.centre - 5:
            seg = [(a, d, p - 12) for a, d, p in seg]
        while min(p for _, _, p in seg) < 48:
            seg = [(a, d, p + 12) for a, d, p in seg]
        return _mono(fit_line(seg, ch, key))

    # -- a variation of the first theme (round o4: the theme-and-variations forms)
    def variation(self, block: str, key: str, t0: float, bars: int, how: str, theme1) -> tuple:
        """(melody, chart, counter, key) of a variation (VARIATIONS) of theme1 = (key, notes from 0, bars) over
        `bars` bars (the theme again where the block is longer, cut where it is shorter), harmonised anew (I, the
        cadence's V, I): 'orn' its long notes ornamented in running notes toward the next, 'bass' as given (the
        texture puts it in the bass), 'minore' in the parallel mode, 'canon' with itself a bar later an octave
        under (the counter), 'march' its even pairs dotted, 'chorale' in augmentation (its first half over the
        block)."""
        U = self.U
        k1, ns1, b1 = theme1
        sh = Key(key).tonic - Key(k1).tonic
        L = bars * U
        base, x = [], 0.0
        while x < L - _EPS:
            base += [(t0 + x + a, d, p + sh) for a, d, p in ns1 if x + a < L - _EPS]
            x += b1 * U
        k = key
        if how == 'chorale':
            base = [(t0 + 2 * (a - t0), 2 * d, p) for a, d, p in base if 2 * (a - t0) < L - _EPS]
        elif how == 'minore':
            k = _transpose_key(key, 0, 'major' if Key(key).minorish else 'minor')
            base = _to_mode(base, key, k)
        pcs = pcs_of(k)
        if how == 'orn':
            base = _ornament(_mono(base), pcs)
        elif how == 'march':
            base = _dotted(_mono(base), t0)
        mel = [(a, min(d, t0 + L - a), p) for a, d, p in _mono(base)]
        I_ = 'i' if Key(k).minorish else 'I'
        chart = harmonize(mel, k, t0, bars, U, {0: I_, bars - 1: I_, (bars - 2, 1): 'V'}, split={bars - 2})
        mel = fit_line(mel, chart, k, strict=0.75)
        cnt = []
        if how == 'canon':
            cnt = _mono(fit_line([(a + U, d, p - 12) for a, d, p in mel if a + U < t0 + L - U - _EPS], chart, k))
        return mel, chart, cnt, k

    # -- the climax transformed (APEX; round o3: "the theme louder in octaves")
    def apex(self, block: str, kind: str, home: str, t0: float, bars: int, theme2=None, key: str | None = None,
             theme1=None, river: bool = False):
        """(melody, chart, counter, key) of the climax by its material, in `key` (CLX_MODES: the home, its parallel or
        its relative - default the home): 'reharm' the first theme's sentence over another harmony at home (round
        o11: no bVI / IV / bIII climax key any more - the retired REHARM draw); 'second' the
        second theme (the same tune: its first statement's degrees) as an apotheosis, the motto's head answering it
        every two bars; 'combine' (round o6 - o5's judges: "a new hymn at the climax where the motto should be
        transformed") the whole motto on top every two bars, sequenced up, the second theme under it; 'augment' the
        motto in augmentation, sequenced up (a third, then a step), and the sentence's cadence; 'theme_aug' (round
        o6) the first theme in augmentation (its first half over the block) and the cadence - theme1 = (key, notes
        from 0, bars). Round o11: a river's climax (river) takes its tune - APEX_RIVER."""
        U, m = self.U, self.m
        k = key or home
        minor = Key(k).minorish
        if river and theme1 and self.scale == 1:
            kind = APEX_RIVER.get(kind, kind)
        if kind == 'reharm':
            vary = ()
            if k == home and not minor:              # (round o11: the summit at home - the theme over another
                k = _transpose_key(home, 0, 'major')  # harmony; the key respelled as the retired REHARM draw did)
                vary = ('reharm',)
            elif k == home:                          # (a minor climax at home: the theme over another harmony)
                vary = ('reharm',)
            if river and theme1:                     # (round o9 - o8's judges, QMBR: "a new arpeggio idea at the
                # climax instead of the opening theme": the river's climax is its own tune - theme1 - in the new key)
                mel, ch = self.cantilena(block, k, t0, bars, centre=self.centre + 3, theme='R')
                return mel, ch, self.motto_counter(block, k, ch, t0, bars, below=5, tf=('head',), first=1), k
            mel, ch = self.sentence(block, k, t0, bars, end='PAC', centre=self.centre + 3, payoff=True, vary=vary)
            return mel, ch, [], k
        if kind == 'second':
            mel, ch = self.cantilena(block, k, t0, bars, centre=self.centre + 3, theme='B')
            cnt = self.motto_counter(block, k, ch, t0, bars, below=5, tf=('head',), first=1)
            return mel, ch, cnt, k
        if kind not in ('augment', 'combine', 'theme_aug'):
            raise ComposeError(f"symphony: climax material {kind!r} unknown ({', '.join(APEX)})")
        if self.scale == 2 and kind == 'combine':
            # (round o7 - o6's judges, the worst piece: the scherzo's combine stated the motto at its internal values
            # - one note per 3/4 bar, "the dance tune augmented into whole-bar notes": the dance tune at its own
            # speed, reharmonised, on top; the second theme under it)
            mel, ch = self.dance(block, k, t0, bars, end='PAC', centre=self.centre + 3, vary=('reharm', 'invert'))
            cnt = []
            if theme2:
                cnt = [n for n in self.theme_under(theme2, k, t0, bars, ch) if n[0] < t0 + (bars - 1) * U - _EPS]
                if cnt:
                    self.log.append({'block': block, 'beat': t0, 'tf': 'cantilena', 'fn': 'counter',
                                     'end': t0 + (bars - 1) * U, 'theme2': True})
            return mel, ch, _mono(fit_line(cnt, ch, k, strict=1.5)), k
        pcs = pcs_of(k)
        I = 'i' if minor else 'I'
        stop = t0 + (bars - 2) * U
        mel = []
        if kind == 'theme_aug' and theme1:           # (the first theme at half speed, in the climax's key and mode)
            k1, ns1, _ = theme1
            sh = Key(k).tonic - Key(k1).tonic
            base = [(a_, d_, p_ + sh) for a_, d_, p_ in ns1]
            if Key(k1).minorish != minor:
                base = _to_mode(base, _transpose_key(k1, sh % 12), k)
            c_ = self.centre + 1
            while base and sum(p_ for _, _, p_ in base) / len(base) > c_ + 4:
                base = [(a_, d_, p_ - 12) for a_, d_, p_ in base]
            while base and sum(p_ for _, _, p_ in base) / len(base) < c_ - 6:
                base = [(a_, d_, p_ + 12) for a_, d_, p_ in base]
            mel = [(t0 + 2 * a_, 2 * d_, _near(pcs, p_)) for a_, d_, p_ in base if t0 + 2 * a_ < stop - _EPS]
            mel = [(a_, min(d_, stop - a_), p_) for a_, d_, p_ in mel]
            if mel:
                self.log.append({'block': block, 'beat': t0, 'tf': 'augment', 'fn': 'melody', 'end': stop})
        if not mel:
            aug = kind != 'combine'                  # (the combine: the motto at its own values, every two bars)
            a = self.anchor(k, _roman(k, I), self.centre + (1 if aug else 3))
            span = max(x + d for x, d, _ in motto_notes(m, 0.0, 60, pcs, ('augment',) if aug else ()))
            span = U * math.ceil(span / U - _EPS)
            if not aug:
                span = max(span, 2 * U)
            x, j = t0, 0
            while x < stop - _EPS:
                # (the combine: the third statement on diminished, a bar each - the motto accelerates into the
                # cadence)
                tf, sp = (('augment',), span) if aug else ((), span) if j < 2 else (('diminish',), U)
                z = min(stop, x + sp)
                mel += [(y, min(d, z - y - (0.25 if not aug else 0.0)), p) for y, d, p in
                        self.state(block, x, a, pcs, tf, fill=z - 0.25 if 'diminish' in tf else None) if y < z - _EPS]
                x += sp
                cont = self.contour()
                a = _step(a, cont[j % len(cont)] if cont else 2 if j == 0 else 1, pcs)
                j += 1
        mel = _unrepeat(_mono([(a_, max(0.125, d_), p_) for a_, d_, p_ in mel]), t0, self.bar, pcs)
        if kind in ('augment', 'theme_aug') and APEX_CANON:
            # (round o9: the augmented line where the trumpets sing it - over their G4 floor; o8's climaxes had it in
            # the horns' low register, "a brass chorale" under the violins)
            while min(p_ for _, _, p_ in mel) < APEX_CANON['floor'] and \
                    max(p_ for _, _, p_ in mel) + 12 <= APEX_CANON['top']:
                mel = [(a_, d_, p_ + 12) for a_, d_, p_ in mel]
        last = mel[-1][2]
        goal = _near({Key(k).tonic}, last)
        mel += run_to(last, goal, stop, int(round(U / 0.5)), 0.5, pcs)
        mel.append((stop + U, U, goal))
        forced = {(0, 0): I, bars - 1: I, (bars - 2, 1): 'V'}       # (round o8: the first half bar - the coda's)
        cnt = []
        if kind == 'combine' and theme2:             # (the second theme under the motto: one chart for both)
            cnt = [n for n in self.theme_under(theme2, k, t0, bars, []) if n[0] < stop - _EPS]
            if cnt:
                self.log.append({'block': block, 'beat': t0, 'tf': 'cantilena', 'fn': 'counter', 'end': stop,
                                 'theme2': True})
        ch = harmonize(mel + [n for n in cnt if n[1] >= 1.0 - _EPS], k, t0, bars, U, forced, split={bars - 2})
        if kind in ('augment', 'theme_aug') and APEX_CANON:      # (round o9: the material at its own speed over it)
            return fit_line(mel, ch, k), ch, self.canon(block, kind, k, ch, t0, bars, mel, theme1), k
        return fit_line(mel, ch, k), ch, _mono(fit_line(cnt, ch, k, strict=1.5)), k


# ------------------------------------------------------------------------------------------------ figuration

RUN_FIGURES = {'arch': ('c', (0, 1, 2, 3, 2, 1, 0, 1)), 'broken': ('c', (0, 2, 1, 2, 0, 2, 1, 2)),
               'climb': ('c', (0, 1, 2, 1, 2, 3, 2, 3)), 'leap': ('c', (0, 2, 3, 2, 0, 2, 3, 2)),
               'up': ('s', 1), 'down': ('s', -1)}
"""The moto perpetuo's per-pulse figures (round o5 - o4's judges: "16th circling over a static bass", "write
patterned arpeggios or scales that outline the chords"): 'c' (chord-tone ladder steps over the pulse's chord tone: an
arpeggio, a broken chord - every note a tone of the chord; a pulse of 4 / 6 notes takes the first 4 / 6) or 's' (a
scale run that way, going on from where it ended: the notes on the strong positions - every other one - chord tones,
the scale's passing tones between). One drawn per 2-bar unit, never the unit before's; the chord tones move with the
chart."""


def figuration(chart, key: str, kind: str, g: float, lo: int, hi: int, U: float, seed, start: int | None = None):
    """Running figuration over a chart on the grid g: 'wave' (a scale stream rising and falling, a chord tone on
    every pulse - the river's flutes), 'run' (moto perpetuo: per pulse a chord tone and a RUN_FIGURES figure on it,
    the chord tones climbing a bar and falling the next). Round o5 (o4's judges: "figuration that ignores the
    harmony"): the strong positions (every other note of the grid) are tones of the chord sounding, a scale's passing
    tones fall between; the pulse is half the bar (the scherzo's: one 3/4 bar). -> [(start, dur, pitch)]."""
    rng = random.Random(seed)
    out = []
    pulse = U / 2.0
    p = start if start is not None else (lo + hi) // 2
    direction = 1
    fig, last_unit = 'arch', -1
    shape = RUN_FIGURES[fig]
    flip = False                       # (round o4: the run turns at the range's edge - it was folded an octave)
    t_0 = chart[0][0] if chart else 0.0

    def tone(x, up_, cs_):
        q_ = x + (1 if up_ else -1)
        while q_ % 12 not in cs_:
            q_ += 1 if up_ else -1
        return q_

    def ladder(x, k_, cs_):            # (k_ chord tones above / below x, a chord tone)
        q_ = x
        for _ in range(abs(k_)):
            q_ = tone(q_, k_ > 0, cs_)
        return q_

    def strong(t_):
        return abs(((t_ - t_0) / g) % 2) < 1e-3 or abs(((t_ - t_0) / g) % 2 - 2) < 1e-3
    span = int(round(pulse / g)) * (2 if kind == 'wave' else 1)
    for a, b, sym in chart:
        pcs = pcs_of(key, sym)
        cs = _cpcs(sym)
        t = a
        p_first = True
        while t < a + b - _EPS:
            on_pulse = abs(((t - t_0) % pulse)) < 1e-3 or abs(((t - t_0) % pulse) - pulse) < 1e-3
            if kind == 'wave':
                if on_pulse or p_first or (strong(t) and p % 12 not in cs):
                    # (round o6 - o5's judges: "flutes in 16th thirds, repeated-note rate 0.76": p_first was never
                    # cleared here, so every note snapped back to the chord tone it had left - one pitch for bars;
                    # the snap goes on the way the stream runs)
                    q = min((x for x in range(p - 2, p + 3) if x % 12 in cs),
                            key=lambda x: (abs(x - p), -direction * x), default=p)
                    p = q
                    p_first = False
                out.append((t, g, p))
                k = int(round((t - t_0) / g))
                if k % span == span - 1:
                    direction = -direction
                q = _step(p, direction, pcs)
                if q > hi or q < lo:
                    direction = -direction
                    q = _step(p, direction, pcs)
                p = q
            else:
                if on_pulse or p_first:
                    bar_i = int((t - t_0 + _EPS) // U)
                    up = (bar_i % 2 == 0) != flip
                    # (a scale figure goes on from where it ended - restarted from the pulse's tone it was a
                    # sawtooth, heard as runs folded an octave)
                    src = out[-1][2] if out else p
                    q = tone(src, up, cs) if not p_first or src % 12 not in cs else src
                    if (q > hi and up) or (q < lo and not up):   # (the line turns back: the next bars run
                        flip, up = not flip, not up                # the other way - toward the range)
                        q = tone(src, up, cs)
                    p = q
                    unit = int((t - t_0 + _EPS) // (2 * U))      # (the figure changes by 2-bar unit)
                    if unit != last_unit:
                        opts = [f for f in RUN_FIGURES if f != fig] or list(RUN_FIGURES)
                        fig = opts[rng.randrange(len(opts))]
                        last_unit = unit
                    kind_, sh_ = RUN_FIGURES[fig]
                    if kind_ == 'c':
                        offs = tuple(x if up else -x for x in sh_)
                        ext = [ladder(p, x, cs) for x in offs]
                        if max(ext) > hi + 2 or min(ext) < lo - 2:      # (a figure leaving the range: mirrored)
                            offs = tuple(-x for x in offs)
                            ext = [ladder(p, x, cs) for x in offs]
                        for _ in range(2):            # (still outside: the figure moved by octaves into it)
                            if max(ext) > hi + 2 and min(ext) - 12 >= lo - 2:
                                ext = [x - 12 for x in ext]
                            elif min(ext) < lo - 2 and max(ext) + 12 <= hi + 2:
                                ext = [x + 12 for x in ext]
                        shape = ('c', ext)
                    else:
                        d_ = sh_ if up else -sh_
                        n_ = int(round(pulse / g))
                        if _step(p, d_ * n_, pcs) > hi + 2 or _step(p, d_ * n_, pcs) < lo - 2:
                            d_ = -d_
                        shape = ('s', d_)
                    p_first = False
                    cur = p
                k = int(round(((t - t_0) % pulse) / g)) % max(1, int(round(pulse / g)))
                if shape[0] == 'c':
                    q = shape[1][k % len(shape[1])]
                else:                               # (the scale: a chord tone on every strong position)
                    q = cur if k == 0 else _step(cur, shape[1], pcs)
                    if k and strong(t) and q % 12 not in cs:
                        q = tone(cur, shape[1] > 0, cs)
                    cur = q
                out.append((t, g, q))
            t += g
    return out


def thirds_below(notes, chart, key: str) -> list:
    """A second voice a diatonic third under (the two flutes in thirds)."""
    return [(a, d, _step(p, -2, pcs_of(key, _chart_at(chart, a)))) for a, d, p in notes]


# ------------------------------------------------------------------------------------------------ the form

def _rows(genre, layout: str) -> list:
    """[(name, kind, bars, overrides)] of a layout (plan['layouts'][layout]: (name, kind, bars[, {kind key: value}])
    rows - an override replaces the kind's 'tex' / 'dyn' / 'peak' ... for that block)."""
    return [(r[0], r[1], int(r[2]), dict(r[3]) if len(r) > 3 else {}) for r in genre.plan['layouts'][layout]]


DEV_FORMS = {'dialogue_fugato': ('dev_dialogue', 'dev_fugato'), 'fugato_dialogue': ('dev_fugato', 'dev_dialogue'),
             'dialogue': ('dev_dialogue',), 'storm': ('dev_dialogue', 'dev_dialogue'), 'fugato': ('dev_fugato',)}
"""The development's blocks (plan['set']['dev'], round o2: the judges read the q1 pieces as one plan family - a
fugato in nearly every piece): they replace the layout's development rows (a layout with one development row takes
the first). 'storm': two dialogues, the second through the next key path, with the brass."""
SPANS = {'tight': {'trans': 4, 'close': 4, 'dev_dialogue': 6, 'dev_fugato': 6, 'retrans': 4, 'coda': 6},
         'even': {},
         'broad': {'trans': 6, 'close': 6, 'dev_dialogue': 10, 'dev_fugato': 10, 'retrans': 8, 'coda': 8}}
"""The proportions (plan['set']['span']): bars per block kind over the layout's (the themes keep their periods);
a feel's 'spans' lists the ones it allows (the scherzo: its bars count twice)."""


def _dev_room(rows, i: int, sc: int) -> bool:
    """Whether the development block rows[i] may grow a step: the development stays under DEV_SHARE['max']."""
    D_ = DEV_SHARE
    dev = sum(b for _, k, b, _ in rows if k in D_['kinds']) + D_['step']
    return dev <= D_['max'] * (sum(r[2] for r in rows) + D_['step']) + _EPS


def _grow_dev(rows, sc: int, path: str | None = None) -> list:
    """DEV_SHARE: the development's blocks grown to their share / least bars (internal bars; sc the feel's scale) -
    each to DEV_SHARE['block'] song bars; when every one is there, a new dialogue after the last (its key path the
    next of DEV_PATHS after `path`, the piece's): a long development is two arguments, not one unit 12 times."""
    D_ = DEV_SHARE
    rows = list(rows)
    if not any(r[1] in D_['kinds'] for r in rows):
        return rows
    blk = int(math.ceil(D_['block'] / sc - _EPS))
    for _ in range(64):
        at = [i for i, r in enumerate(rows) if r[1] in D_['kinds']]
        T = sum(r[2] for r in rows)
        D = sum(rows[i][2] for i in at)
        if D * sc >= D_['min'] - _EPS and D >= D_['share'] * T - _EPS:
            break
        room = [i for i in at if rows[i][2] < blk]
        short = max(D_['min'] / sc - D, (D_['share'] * T - D) / (1 - D_['share']))
        if not room and short <= 2 * D_['step'] + _EPS:     # (a few bars short: the last block grows on)
            room = at[-1:]
        if not room:
            paths = list(DEV_PATHS)
            p_ = paths[(paths.index(path) + 1) % len(paths)] if path in paths else paths[0]
            names = {r[0] for r in rows}
            nm = next(f"dev{j}" for j in range(len(at) + 1, 99) if f"dev{j}" not in names)
            rows.insert(at[-1] + 1, (nm, 'dev_dialogue', D_['step'], {'path': p_}))
            continue
        i = min(room, key=lambda i: (rows[i][1] != 'dev_dialogue', rows[i][2], i))
        n, k, b, o = rows[i]
        rows[i] = (n, k, b + D_['step'], o)
    return rows


def _grow_return(rows) -> list:
    """RETURN: the return's blocks (after the first development block) grown to the exposition's theme weight."""
    R_ = RETURN
    rows = list(rows)
    first = next((i for i, r in enumerate(rows) if r[1] in DEV_SHARE['kinds'] or r[1] == 'var'), None)
    if first is None:
        return rows
    expo = sum(b for _, k, b, _ in rows[:first] if k in R_['expo'])
    for _ in range(32):
        back = sum(b for _, k, b, _ in rows[first:] if k in R_['back'])
        if back >= R_['share'] * expo - _EPS:
            break
        cand = [i for i in range(first, len(rows)) if rows[i][1] in R_['grow'] and rows[i][2] < R_['max']]
        if not cand:
            break
        i = min(cand, key=lambda j: (R_['grow'].index(rows[j][1]), rows[j][2], j))
        n, k, b, o = rows[i]
        rows[i] = (n, k, min(R_['max'], b + 2), o)
    return rows


def _grow_len(rows, bar_s: float, sc: int, extra: float = 0.0, skip: tuple = (), more: tuple | None = None) -> list:
    """MIN_LEN: the blocks grown in its order until the movement lasts its seconds (bar_s: an internal bar's; extra:
    the seconds the slow introduction adds - only MIN_LEN 'more' reads them; skip: kinds never grown - round o20's
    capped fade, FADE_V3; more: MIN_LEN 'more' replaced - round o20's FORM_MERGE['more'])."""
    M_ = MIN_LEN if more is None else dict(MIN_LEN, more=more)
    rows = list(rows)
    more = False
    for _ in range(64):
        if sum(r[2] for r in rows) * bar_s + (extra if more else 0.0) >= M_['seconds'] - _EPS:
            break
        grown = False
        for kind, mx in (M_.get('more', ()) if more else M_['grow']):
            for i, (n, k, b, o) in enumerate(rows):
                if k != kind or k in skip:
                    continue
                if mx is None:
                    if b * sc >= DEV_SHARE['block'] - _EPS or not _dev_room(rows, i, sc):
                        continue
                elif b >= mx:
                    continue
                rows[i] = (n, k, b + M_['step'], o)
                grown = True
                break
            if grown:
                break
        if not grown:
            if more or not M_.get('more'):
                break
            more = True
    return rows


def form_rows(genre, layout: str, draws: dict, feel: dict, seed: int = 0, bar_s: float | None = None) -> list:
    """The piece's blocks [(name, kind, bars, overrides)]: the layout's rows with the set's draws applied - the
    development (DEV_FORMS by draws['dev']), the proportions (SPANS by draws['span'], the feel's 'spans'; round o4
    draws['phrase'] 'free': each block's bars drawn from PHRASES, seeded by the piece and the block - a feel at scale 2
    never longer than its layout's), the slow introduction (draws['slow'] and the feel's 'slow'). Round o11: the
    development's share (DEV_SHARE), the return's weight (RETURN), the retransition's pedal (RT_PEDAL) and - bar_s the
    seconds of an internal bar - the movement's least length (MIN_LEN)."""
    rows = _rows(genre, layout)
    dev = draws.get('dev')
    if dev in DEV_FORMS:
        at = [i for i, r in enumerate(rows) if r[1] in ('dev_dialogue', 'dev_fugato')]
        if at:
            kinds = DEV_FORMS[dev][:len(at)]
            paths = list(DEV_PATHS)
            new = list(rows)                  # (the development rows replaced where they stand - round o4: a
            for j, i in enumerate(at):        # block between two of them, the false recapitulation, stays)
                if j >= len(kinds):
                    new[i] = None
                    continue
                over = {}
                if dev == 'storm' and j == 1:
                    p0 = draws.get('dev_path', paths[0])
                    over = {'path': paths[(paths.index(p0) + 1) % len(paths)] if p0 in paths else paths[0],
                            'tex': {'dialogue_brass': 1.0, 'dialogue': 0.3}, 'dyn': [(0, 'mf', 'step'), (1, 'ff')]}
                new[i] = (f'dev{j + 1}', kinds[j], rows[i][2], over)
            rows = [r for r in new if r is not None]
    if MACRO and isinstance(draws.get('shape'), dict):     # (round o24: the macro shape on the layout's rows)
        rows = _macro_rows(genre, rows, draws['shape'])
    v3 = bool(SET_PLAN and SET_PLAN.get('v3'))
    if SET_PLAN and SET_PLAN.get('v2') and not v3 and draws.get('sections') in FORM_SHAPE['deltas']:
        rows = _shape_rows(rows, int(draws['sections']))      # (round o19a: the layout's shape - FORM_SHAPE)
    span = draws.get('span')
    ok = feel.get('spans')
    if ok and span not in ok:
        span = ok[0]
    sp = SPANS.get(span) or {}
    rows = [(n, k, sp.get(k, b), o) for n, k, b, o in rows]
    if draws.get('phrase') == 'free':         # (round o4: phrases of 6 / 10 / 12 bars, drawn per block)
        out = []
        for n, k, b, o in rows:
            w = PHRASES.get(k)
            if w and feel.get('scale', 1) != 1:
                w = {x: v for x, v in w.items() if x <= b} or None
            out.append((n, k, int(_pick(random.Random(f"symphony:{seed}:phrase:{n}"), w)) if w else b,
                        o))
        # (the piece no longer than PHRASE_CAP x its square layout: the longest blocks drawn over theirs back)
        cap = PHRASE_CAP * sum(r[2] for r in rows)
        while sum(r[2] for r in out) > cap + _EPS:
            i = max(range(len(out)), key=lambda j: (out[j][2] - rows[j][2], -j))
            if out[i][2] <= rows[i][2]:
                break
            out[i] = out[i][:2] + (rows[i][2],) + out[i][3:]
        rows = out
    sc_ = feel.get('scale', 1)
    if DEV_SHARE:                   # (round o11 - the masterpiece panel: "the development too short or absent")
        rows = _grow_dev(rows, sc_, draws.get('dev_path'))
    if RETURN:                      # (round o11: "the recap thinner than the exposition")
        rows = _grow_return(rows)
    if RT_PEDAL:                    # (round o11: the retransition's dominant pedal, RT_PEDAL bars, after its frame)
        P_ = int(math.ceil(RT_PEDAL['bars'] / sc_ - _EPS))
        fr = draws.get('frame') if draws.get('frame') in BUILD_FRAMES else 'pedal'
        need = P_ if fr == 'pedal' or draws.get('build') == 'bass' else P_ + RT_PEDAL['frame']
        if CHROMA_CADENCE and CHROMA_CADENCE.get('recap') and fr == 'pedal' and draws.get('build') != 'bass':
            need = P_ + int(CHROMA_CADENCE.get('bars', 2))      # (the chromatic predominant before the pedal)
        if CHROMA_EVENT and CHROMA_EVENT.get('recap') and draws.get('build') != 'bass':
            need = max(need, P_ + int(math.ceil(CHROMA_EVENT.get('chain', 4) / sc_ - _EPS)))   # (the chord chain)
        if SET_PLAN and SET_PLAN.get('builds'):     # (round o18b: the gesture's own least bars, its silence after)
            G_ = GESTURES[draws.get('build') if draws.get('build') in GESTURES else 'swell']
            need = max(4, int(math.ceil(G_['need'] / sc_ - _EPS))) + int(G_.get('silence', 0))
        rows = [(n, k, max(b, need) if k == 'retrans' else b, o) for n, k, b, o in rows]
    # (round o8 - o7's judges: "short climaxes after a 4-bar build": the build and the climax at least PROPORTION's
    # share of the piece's bars, and its 'min' bars - the scherzo's internal bars count twice)
    total = sum(r[2] for r in rows)
    out = []
    for n, k, b, o in rows:
        role = 'build' if k == 'retrans' else 'peak' if kind_data(genre, k, o).get('peak') else None
        if role:
            P_ = PROPORTION[role]
            b = max(b, int(math.ceil(P_['share'] * total - _EPS)), int(math.ceil(P_['min'] / sc_)))
        out.append((n, k, b, o))
    rows = out
    if MIN_LEN and bar_s:           # (round o11: "an exposition, not a movement" - DUWT / TSSB at 2:05-2:23)
        ex_ = 0.0
        if draws.get('slow') and feel.get('slow') and rows[0][1] == 'intro':
            sb_ = int(_pick(random.Random(f"symphony:{seed}:slow_bars"), SLOW['bars']))                 if isinstance(SLOW['bars'], dict) else SLOW['bars']
            ex_ = sb_ * bar_s / SLOW['tempo']
        rows = _grow_len(rows, bar_s, sc_, ex_)
    if END_LEN:                     # (round o10: the last bars in proportion to the climax and the coda before them)
        pc = sum(b for n, k, b, o in rows if k in ('coda',) or kind_data(genre, k, o).get('peak'))
        e_ = min(END_LEN['max'], max(END_LEN['min'], int(round(END_LEN['share'] * pc))))
        if SET_PLAN and SET_PLAN.get('v2'):     # (round o19a: room for the motto and the cadence - END_V2)
            e_ = max(e_, END_V2['min'])
        rows = [(n, k, max(b, e_) if k == 'end' else b, o) for n, k, b, o in rows]
    if draws.get('slow') and feel.get('slow') and rows[0][1] == 'intro':
        # (round o6 - the 6/8 pieces' shared opening, same_open68: the slow introduction's length drawn)
        sb_ = int(_pick(random.Random(f"symphony:{seed}:slow_bars"), SLOW['bars'])) \
            if isinstance(SLOW['bars'], dict) else SLOW['bars']
        rows = [('slow', 'slow', sb_, {})] + rows
    # (round o10 - o9's judges: "an opening that empties after a few bars", ECER: a slow introduction and a 6-bar
    # mist before the theme at bar 11; the theme within OPENING's bars - the slow bars count by their tempo)
    th = next((i for i, r in enumerate(rows) if r[1] in ('t1', 'river')), None)
    if OPENING and th:
        sc_ = feel.get('scale', 1)

        def before(rs):
            return sum(r[2] * sc_ * (1 / SLOW['tempo'] if r[1] == 'slow' else 1) for r in rs[:th_(rs)])

        def th_(rs):
            return next(i for i, r in enumerate(rs) if r[1] in ('t1', 'river'))
        cap = OPENING['bars']
        for i, (n, k, b, o) in enumerate(rows[:th]):
            if k in ('intro', 'source') and before(rows) > cap + _EPS:
                over = before(rows) - cap
                rows[i] = (n, k, max(OPENING['min'], b - int(math.ceil(over / sc_ - _EPS))), o)
        if rows[0][1] == 'slow' and before(rows) > cap + _EPS:
            rows = rows[1:]
    if DEV_SHARE:                   # (round o11: its share again over the grown piece)
        rows = _grow_dev(rows, sc_, draws.get('dev_path'))
    if v3:                          # (round o20: the shape by merging and lengthening - FORM_MERGE)
        lo_ = int(math.ceil(FORM_MERGE['least'] / sc_ - _EPS))
        rows = [(n, k, max(b, lo_) if k in FORM_MERGE['long'] and not o.get('false') else b, o)
                for n, k, b, o in rows]
        d_ = draws.get('sections')
        rows = _merge_rows(genre, rows, -int(d_) if d_ in FORM_MERGE['deltas'] else 0, FORM_MERGE['cap'],
                           parts=bool(SET_PLAN.get('v4')))      # (round o22: the parts kept - JOIN_V4)
        if MIN_LEN and bar_s:
            rows = _grow_len(rows, bar_s, sc_, more=FORM_MERGE['more'])
    return rows


def _crisis_rows(genre, rows) -> tuple:
    """ARC_CRISIS on the piece's rows: (rows, True) with the crisis (a 'recap' row: the peak, in the dark key), the
    collapse (a 'retrans' row) and the calm return (the old peak row, no peak) after the retransition - or (rows,
    False) where the retransition does not follow a development block or no peak follows it."""
    A = ARC_CRISIS
    r = next((i for i, x in enumerate(rows) if x[1] == 'retrans'), None)
    if not r or rows[r - 1][1] not in A['kinds'] or r + 1 >= len(rows) or \
            not kind_data(genre, rows[r + 1][1], rows[r + 1][3]).get('peak'):
        return rows, False
    n, k, b, o = rows[r + 1]
    v2 = SET_PLAN and SET_PLAN.get('v2')
    crisis = ('crisis', 'recap', b + (CRISIS_V2['grow'] if v2 else 0), {'crisis': True})
    if v2:                                    # (round o19a: the return transformed and quiet - CRISIS_V2)
        calm = (n, k, max(A['calm_min'], b - A['calm_cut']), dict(o, **CRISIS_V2['calm_over'], peak=False, calm=True))
        coll = ('collapse', 'retrans', max(A['collapse'], rows[r][2] - 2), dict(A['collapse_over'], collapse=True))
        return rows[:r + 1] + [crisis, coll, calm] + rows[r + 2:], True
    coll = ('collapse', 'retrans', max(A['collapse'], rows[r][2] - 2), dict(A['collapse_over'], collapse=True))
    calm = (n, k, max(A['calm_min'], b - A['calm_cut']), dict(o, **A['calm_over'], peak=False, calm=True))
    return rows[:r + 1] + [crisis, coll, calm] + rows[r + 2:], True


OPENING = {'bars': 8, 'min': 3}
"""Round o10 (o9's judges, ECER / CKNM): the first theme starts within 'bars' song bars - the opening rows (the call /
mist / solo, the source) shortened to 'min' bars at least, then the slow introduction (its bars x 1 / SLOW['tempo'])
left out."""


END_LEN = {'share': 0.25, 'min': 3, 'max': 6}
"""Round o10 (o9's judges: "endings short after a long build", EYPC 65-66, UZWK 90-92): the end block at least 'share'
of the climax's and the coda's bars (between 'min' and 'max'); the bars over three are the closing bars before the
cadence (END_PRE: the tonic and the motto's head, then the predominant)."""
DEV_SHARE = {'share': 0.25, 'max': 0.33, 'min': 16, 'step': 2, 'block': 16, 'kinds': ('dev_dialogue', 'dev_fugato')}
"""Round o11 (the masterpiece panel, 5 of 6 judges: "development by block sequence; too short or absent" - DUWT's 8 of
70 bars, PGFL none): the development's blocks take at least 'share' of the piece's bars and 'min' song bars (never
over 'max'): the dialogues grow first, 'step' internal bars (a model) at a time, to 'block' song bars each, then the
fugato, then the dialogues again. The scherzo / trio and the ternary forms have a development row now (genres)."""
RETURN = {'share': 1.0, 'expo': ('t1', 't1b', 't2', 't2b', 'river'), 'back': ('recap', 'recap2', 'coda', 'river'),
          'grow': ('recap2', 'recap'), 'max': 12}
"""Round o11 (the panel, 6 of 6 judges: "the return does not arrive ... the recap thinner than the exposition", DUWT
51-59, LYRF 71-78): the return's blocks after the development ('back': the recapitulations, the coda, the river's
broad return) weigh at least 'share' of the exposition's theme blocks ('expo'); the second theme's return grows
first, then the first theme's, two bars at a time, to 'max' bars. The compact and through-composed forms bring the
second theme back now (a recap2 row)."""
RT_PEDAL = {'bars': 6, 'frame': 2}
"""Round o11 (the panel: "the only real staged retransition", UGGX's 28-beat dominant pedal): the retransition ends on
'bars' song bars over the dominant pedal (its last bar the motto's lead-in over V7), its harmonic frame (BUILD_FRAMES)
in the 'frame' bars or more before them; the kernel builds answer the motto's head in imitation over the pedal
(Writer.retrans)."""
MIN_LEN = {'seconds': 180, 'step': 2,
           'grow': (('dev_dialogue', None), ('t2', 12), ('recap2', 12), ('trio', 12), ('river', 12), ('episode', 10),
                    ('recap', 12), ('t2b', 10), ('t1b', 10), ('dev_fugato', None), ('coda', 10), ('var', 10)),
           'more': (('t1', 12), ('t2', 14), ('recap2', 14), ('recap', 14))}
"""Round o11 (the panel: "an exposition, not a movement" - DUWT / TSSB / ASFP at 2:05-2:23, the references 3:20-3:43): a
movement shorter than 'seconds' grows its blocks 'step' bars at a time in the 'grow' order, each to its bars (internal;
None: the development's DEV_SHARE 'block' / 'max'), until it lasts that long. Round o15b (o14 slot 7: 179.4 s, every
'grow' block at its bars): 'more' - then the first theme to 12, the second theme and the returns to 14, only when
nothing in 'grow' can and the movement with its slow introduction (at its tempo) is still short."""
PROPORTION = {'build': {'share': 0.08, 'min': 6}, 'peak': {'share': 0.13, 'min': 8}}
"""The build's (the retransition) and the climax's (the peak block) least length (round o8): 'share' of the piece's
bars, and 'min' bars of the song (internal bars x the feel's scale)."""
PHRASE_CAP = 1.1
PHRASES = {'t1': {8: 1.0, 6: 0.5, 10: 0.5, 12: 0.25}, 't1b': {8: 1.0, 6: 0.6, 10: 0.5},
           't2': {8: 1.0, 10: 0.7, 12: 0.5, 6: 0.4}, 't2b': {8: 1.0, 6: 0.6, 10: 0.5},
           'trans': {4: 1.0, 5: 0.6, 6: 0.8, 7: 0.4}, 'close': {4: 1.0, 3: 0.5, 6: 0.5, 2: 0.3},
           'dev_dialogue': {8: 1.0, 6: 0.6, 10: 0.8, 12: 0.6, 16: 0.3}, 'dev_fugato': {8: 1.0, 10: 0.7, 12: 0.6},
           'retrans': {6: 1.0, 4: 0.6, 5: 0.5, 8: 0.7, 10: 0.4}, 'recap': {8: 1.0, 10: 0.7, 12: 0.5},
           'recap2': {6: 1.0, 8: 0.8, 10: 0.4}, 'coda': {6: 1.0, 8: 0.8, 5: 0.5, 10: 0.4},
           'refrain': {6: 1.0, 4: 0.6, 8: 0.6}, 'trio': {8: 1.0, 10: 0.7, 12: 0.5}, 'var': {8: 1.0, 10: 0.5, 6: 0.4},
           'episode': {8: 1.0, 6: 0.6, 10: 0.6}, 'river': {8: 1.0, 10: 0.6, 12: 0.4},
           'source': {8: 0.8, 6: 1.0, 4: 0.6}, 'intro': {4: 1.0, 3: 0.6, 6: 0.5}}
"""The blocks' lengths in bars {kind: {bars: weight}} under plan['set']['phrase'] 'free' (round o4 - o3's judges:
"4 / 8-bar modules", "equal section layouts across pieces"): the sentence extends its fragmentation, the cantilena
its consequent (stretch), the development takes a model per two bars (even lengths only); the piece at most
PHRASE_CAP x its square layout's bars (the blocks drawn longest over theirs are set back)."""
ELIDE = ('t1b', 'recap', 'refrain', 'var')
"""The blocks whose cadence bar may be the next block's first (plan['set']['elide'] 1: one per piece, drawn - round
o4): the block is written whole, then its last bar cut."""
VARIATIONS = {'orn': {'tex': {'running_strings': 1.0, 'drive_strings': 0.5}, 'dyn': [(0, 'mf')]},
              'bass': {'tex': {'motto_bass': 1.0}, 'dyn': [(0, 'f')]},
              'minore': {'tex': {'cantabile': 1.0, 'cantabile_horn': 0.6}, 'dyn': [(0, 'p', 'step'), (1, 'mp')]},
              'canon': {'tex': {'dev_poly': 1.0}, 'dyn': [(0, 'mp'), (1, 'f')]},
              'march': {'tex': {'tutti_drive': 1.0, 'hammer': 0.6}, 'dyn': [(0, 'f', 'step')]},
              'chorale': {'tex': {'cantabile_winds': 1.0, 'tutti_chorale': 0.5}, 'dyn': [(0, 'p'), (1, 'mf')]}}
"""A variation's technique ('var' blocks, drawn per piece without repeats; Writer.variation) and its texture /
dynamics: the theme in diminution (running ornaments), in the bass, in the parallel mode, in canon, dotted as a march,
augmented as a chorale."""


def kind_data(genre, kind: str, over: dict | None = None) -> dict:
    return dict(genre.plan['kinds'][kind], **{k: v for k, v in (over or {}).items() if k in KIND_KEYS})


def _second_key(home: str, rel: str) -> str:
    K = Key(home)
    if rel == 'relative':
        return _transpose_key(home, 3 if K.minorish else 9, 'major' if K.minorish else 'minor')
    if rel == 'dominant':
        return _transpose_key(home, 7, 'major' if not K.minorish else 'minor')
    if rel == 'mediant':               # a third relation (bVI major)
        return _transpose_key(home, 8, 'major')
    if rel == 'subdominant':
        return _transpose_key(home, 5)
    raise ComposeError(f"symphony: second key {rel!r} unknown")


DEV_PATHS = {'rise': {'major': (2, 3, 4, 5), 'minor': (3, 4, 5, 6)},
             'fifths': {'major': (3, 6, 2, 5), 'minor': (7, 3, 6, 4)},
             'thirds': {'major': (6, 4, 2, 5), 'minor': (1, 6, 4, 7)},
             'fall': {'major': (6, 5, 4, 3), 'minor': (6, 5, 4, 3)}}
"""The development's key paths: the home key's scale degree per 2-bar model, each model in the key of that degree's
triad (major / minor; a diminished degree takes the next one) - rising steps, a circle of fifths, falling thirds,
falling steps. Round o8 (o7's judges, the lost slot: "a chromatic trumpet line over C# / Eb / G# chords", 7 of 7):
the paths were semitones from the second key, every model in the minor - F minor, Db minor, A minor in a D dorian
piece; the development now moves through the RELATED keys (the closely related keys of the home), the chromatic notes
only its secondary dominants' voice-leading (each model's bar 2 the next key's V7)."""


def dev_keys(home: str, path: str) -> list:
    """The development's keys (DEV_PATHS[path] in the home's scale; the home's mode family picks the row)."""
    K = Key(home)
    pcs = sorted((x - K.tonic) % 12 for x in K.pcs)
    out = []
    for d in DEV_PATHS[path]['minor' if K.minorish else 'major']:
        for k in range(7):
            i = (d - 1 + k) % len(pcs)
            third = (pcs[(i + 2) % len(pcs)] - pcs[i]) % 12
            fifth = (pcs[(i + 4) % len(pcs)] - pcs[i]) % 12
            if fifth == 7 and third in (3, 4):
                break
        out.append(_transpose_key(home, pcs[i], 'major' if third == 4 else 'minor'))
    return out
INTRO_KINDS = {'call': 'intro', 'mist': 'mist', 'source': 'source', 'solo': 'solo'}
"""The openings (plan['set']['intro']): the call, the mist, the source, round o3 the solo (a solo voice states the
motto over a held pedal, pp - the judges: 'not always flute-in-thirds over harp')."""
SOURCES = {'flutes': {'tex': {'river': 1.0}}, 'strings': {'tex': {'river_strings': 1.0}},
           'low': {'tex': {'river_low': 1.0}}, 'murmur': {'tex': {'river_murmur': 1.0}}}
"""The source's colour (plan['set']['src'], round o3: the flutes' thirds over the harp opened four pieces of a panel):
the flutes' stream in thirds, one stream in the violins II, the clarinets' low stream, the violas' murmur under a high
violin pedal."""
SOURCE_CHARTS = {'plagal': {'major': ('I', 'IV', 'I', 'V'), 'minor': ('i', 'iv', 'i', 'V')},
                 'circle': {'major': ('I', 'vi', 'ii', 'V'), 'minor': ('i', 'VI', 'iv', 'V')},
                 'pedal': {'major': ('I', 'I', 'IV', 'I'), 'minor': ('i', 'i', 'iv', 'i')}}
SOURCE_ENTRIES = ('late', 'early', 'answer')
"""The source's frame and entries (plan['set']['src_chart'] / ['src_entry'], round o5 - o4's statistician: one
8-bar opening ostinato with the oboe at bar 7 in the 6/8 pieces): its chords per bar (the last bar V), and where the
motto's head enters - at the end ('late'), at bar 3 and at the end ('early'), or answered by its inversion two bars
later ('answer'; 6 bars and more)."""
T2_COLOURS = {'winds': {'tex': {'cantabile': 1.0}}, 'horn': {'tex': {'cantabile_horn': 1.0}},
              'cello': {'tex': {'cantabile_cello': 1.0}}, 'pulse': {'tex': {'cantabile_pulse': 1.0}},
              'choir': {'tex': {'cantabile_winds': 1.0}}, 'strings': {'tex': {'cantabile_strings': 1.0}}}
"""The second theme's colour (plan['set']['t2col'], round o3: 'the same oboe / clarinet second theme over the harp'):
a wind over the strings' arpeggios and the harp, a horn over held divisi strings, the cellos under a high pad, a wind
over syncopated strings, the woodwind choir over pizzicato, the violins with a cello counter-line."""
DEV_TECH = {'sequence': {'tex': {'dialogue': 1.0, 'dialogue_brass': 0.6}},
            'fragment': {'tex': {'dialogue': 1.0, 'dialogue_brass': 0.5}},
            'stretto': {'tex': {'dev_poly': 1.0, 'dialogue_brass': 0.4}},
            'combine': {'tex': {'dev_poly': 1.0}},
            'bass': {'tex': {'dev_bass': 1.0}},
            'theme': {'tex': {'dev_poly': 1.0, 'dialogue': 0.6}}}
"""The development's techniques (plan['set']['dev_tech']; Writer.develop - round o3: the development works the
piece's motto) and their textures; a second development block takes DEV_NEXT of the first."""
DEV_BASS_RAW = True
"""Round o12 (dev_own 0.12 for the 'bass' technique in a scherzo of the o12 plan: fit_line snapped the motto's steps in
the bass to the chords - A G D E B became Bb Bb Eb G Db): the development's motto in the bass keeps its intervals in
the key (the passing tones over the held chord, as a bass theme does); the answer over it is still fitted."""
DEV_NEXT = {'sequence': 'fragment', 'fragment': 'stretto', 'stretto': 'bass', 'combine': 'fragment', 'bass': 'stretto',
            'theme': 'stretto'}
DEV_LADDER = {'links': 2, 'imitate': True}
"""Round o11 (the masterpiece panel, gap 1: "whole phrases transposed up by step, 2-bar units sequenced 4-8 times,
nothing broken down to a kernel", LYRF 37-52): a development block's 2-bar models state the technique's own unit at
most 'links' + 1 times (never more than 'links' transposed copies in a row), then the unit shrinks toward the
retransition - the head answered by its inversion (1 bar), the kernel per half bar, the kernel diminished per quarter
(dev_stages); a stage that goes on inverts its statements (the next unit is never the same shape). Round o12
('imitate'; o11's judges: "the development a row of textures, not an argument", dev_own 0.80 -> 0.67): the kernel
stage is the head in imitation - the head each bar, its answer half a bar later a fourth under in the other choir (a
stretto of the head); the diminished kernel stays the last model's."""


def dev_stages(tech: str, n: int) -> list:
    """The stage of each of a development block's n models (DEV_LADDER): 0 the technique's own unit, 1 the head, 2 the
    kernel per half bar, 3 the kernel diminished. 'fragment' is the ladder from its second model; 'sequence' / 'theme'
    keep their own unit in the first half of the models at most; the last model of two or more is stage 3."""
    if n <= 1:
        return [0] * n
    links = DEV_LADDER['links'] if DEV_LADDER else n
    if tech == 'fragment':
        own = 1
    else:
        own = min(links + 1, n - 1 if n >= 3 else n, max(1, n // 2) if tech in ('sequence', 'theme') else n)
    rest = n - own
    if rest <= 0:
        return [0] * n
    h = (rest - 1) // 2                  # (the head, then the kernel, the diminished kernel the last model only)
    return [0] * own + [1] * h + [2] * (rest - 1 - h) + [3]


DEV_WALK = None
"""Off (None, the default: bit-identical) or DEV_WALK_ON - the code review's A1 step 2-3 (round o16): every
dev_dialogue block is a PLANNED WALK through the derivation space (Writer.walk) instead of dev_stages' fixed ladder,
and the recapitulation's / coda's counter-line is one the development derived (Writer.recall): 'split' cuts the block
into its phases (each its own texture and level), 'recall' the counter-line, 'graph' the score's dev_own gate replaced
by the derivation graph's metrics (derive_stats; genres.symphony_derive). Round o17: DEV_WALK_ON is v2 ('v2': the
block stays ONE block of worked processes - Writer.walk2, WALK2); o16's walk is DEV_WALK_V1 (the phases split into
blocks - Writer.walk, WALK). Round o18a: DEV_WALK_ON is v3 ('v3': one key per block or one prepared modulation, the
processes by time, the four-voice stretto into the retransition - Writer.walk3, WALK3); o17's is DEV_WALK_V2."""
DEV_WALK_ON = {'v3': True, 'recall': True, 'graph': True}
DEV_WALK_V2 = {'v2': True, 'recall': True, 'graph': True}
DEV_WALK_V1 = {'split': True, 'recall': True, 'graph': True}

WALK = {
    # the model lengths (internal bars) per segment in turn - the unit can grow as well as shrink
    'shapes': {'shrink': (4, 2, 1), 'grow': (1, 2, 4), 'arch': (2, 1, 3), 'wave': (3, 1, 2), 'pairs': (2, 2, 1),
               'broad': (3, 2, 2), 'surge': (1, 1, 3)},
    'reps': {1: 0.4, 2: 1.0, 3: 0.6},          # models per sequence (its links: at most 2 transposed copies)
    'ops': {'invert': 1.0, 'retro': 0.8, 'augment': 0.5, 'diminish': 0.6, 'head': 0.9, 'kernel': 0.8, 'frag2': 0.7,
            'frag3': 0.6, 'liquidate': 0.5, 'expand': 0.7, 'contract': 0.6, 'displace': 0.6, 'shift': 0.5,
            'mode': 0.4, 'reharm': 0.6, 'combine': 0.8},
    'novel': 2.5,                               # an op the piece has not used yet: its weight x this
    'depth': (1, 4),                            # the chain's length at the development's start / at the retransition
    'branch': 0.3,                              # a segment's chain from the kernel again (a new branch)
    'src': {'K1': 1.0, 'K2': 0.45},             # the kernel a chain starts from (the motto, the second theme's)
    'arrange': {'call': 1.0, 'imitate': 0.9, 'against': 0.8, 'bass': 0.6, 'false': 0.5},
    'moves': {'up': 1.0, 'down': 0.7, 'fifths': 0.9, 'thirds': 0.6, 'real': 0.8},
    'real': {2: 1.0, -2: 0.7, 3: 0.5},          # a real sequence's transposition per model (semitones)
    'links': {'plain': 1.0, 'applied': 0.8},    # the models linked by their own chords or by applied dominants
    'arrive': {'pac': 1.0, 'hc': 0.6, 'deceptive': 0.5, 'chroma': 0.9},
    'answer': {'invert': 1.0, 'retro': 0.8, 'augment': 0.4, 'shift': 0.5},
    'inner': {'invert': 1.0, 'retro': 0.7, 'frag2': 0.8, 'liquidate': 0.5, 'expand': 0.4},
    'imit': {'delay': {0.5: 1.0, 1.0: 0.8, 0.25: 0.4}, 'steps': {-3: 1.0, -4: 0.8, -7: 0.6, 2: 0.4}},
    'tex': {'call': {'dialogue': 1.0, 'dialogue_brass': 0.6}, 'imitate': {'dev_poly': 1.0, 'dialogue': 0.3},
            'against': {'dev_poly': 1.0}, 'bass': {'dev_bass': 1.0}, 'false': {'dialogue': 1.0, 'dev_poly': 0.5}},
    'phase': {'min': 4, 'most': 3},             # a phase's least internal bars (scale 1; the scherzo's half), most phases
    'levels': ('p', 'mp', 'mf', 'f'),           # each phase's level (rising)
    'line': {'min': 4, 'span': (0.75, 2.0)},    # the recalled counter-line: notes, span in bars
}
"""The walk's vocabulary (DEV_WALK, Writer.walk). A dev_dialogue block is cut into 1-3 PHASES (a texture each, drawn
by the phase's arrangement: 'call' the unit answered by its transform in the other choir, 'imitate' the line in canon
a step-count under / over, 'against' the motto's derivation against the second theme's, 'bass' the line in the bass
under a counter-line from the other kernel, 'false' a false entry - the motto's head plain in the home key, broken off
into the phase's key); each phase into SEGMENTS: a model of 1-4 bars (the shape's next length) stated 1-3 times as a
sequence ('moves': diatonic up / down a step, by falling fifths or thirds, or 'real': transposed by semitones), the
models linked by their own chords or applied dominants, the segment ARRIVING in the next segment's key ('arrive':
V7 - I, a half cadence, V7 - vi, or a chromatic predominant from CHROMA before the V7). Each segment's unit is a node
of the derivation graph: an op chain on K1 (the motto) or K2 (the second theme's head), its depth rising from
'depth'[0] to 'depth'[1] over the development, ops the piece has not used preferred ('novel'), a model too short for
its unit fragmenting it."""
WALK_DEG = {'up': (1, 2, 3, 4), 'down': (1, 7, 6, 5), 'fifths': (1, 4, 7, 3, 6, 2, 5), 'thirds': (1, 6, 4, 2),
            'real': (1, 1, 1, 1)}
"""The models' chord degrees per move (a diatonic sequence: the model's chord moves with it)."""
WALK_ROMAN = {'major': {1: 'I', 2: 'ii', 3: 'iii', 4: 'IV', 5: 'V', 6: 'vi', 7: 'V'},
              'minor': {1: 'i', 2: 'ii°', 3: 'III', 4: 'iv', 5: 'V', 6: 'VI', 7: 'VII'}}
WALK_APPLIED = {2: 'V7/ii', 4: 'V7/IV', 5: 'V7/V', 6: 'V7/vi'}
"""The applied dominant before a model on that degree ('links' 'applied')."""
WALK_CONFLICT = ({'augment', 'diminish'}, {'head', 'kernel', 'frag2', 'frag3'}, {'expand', 'contract', 'liquidate'},
                 {'displace', 'shift'})
WALK_FRAG = ('head', 'kernel', 'frag3', 'frag2')
"""Ops that never stand in one chain together; the fragmenting ops (a model too short for its unit takes the next)."""

WALK2 = {
    'bars': (8, 12),                            # a process's song bars: at least / about at most
    'most': 3,                                  # processes per block at most
    'model': {1: 2, 2: 1},                      # the model's internal bars by the feel's scale (2 / 2 song bars)
    'states': 3,                                # the unit's statements in a sequence at most (DEV_LADDER's links + 1)
    'procs': {'sequence': 1.0, 'stretto': 0.9, 'against': 0.7, 'bass': 0.45},
    'reuse': 0.35,                              # a process kind the piece has used: its weight x this
    'drive': 2.0,                               # the stretto as the development's last process (into the pedal) x
    'k2': 0.3,                                  # a sequence on the second theme's head (K2) instead of the motto
    'depth': ({0: 0.5, 1: 1.0, 2: 0.3}, {1: 0.8, 2: 1.0}),     # the unit's ops: the development's first / second half
    'cap': 2,                                   # ops in any statement at most (the fragmenting op first)
    'ops': {'invert': 1.0, 'augment': 0.3, 'diminish': 0.3, 'head': 0.6, 'frag3': 0.4, 'expand': 0.6,
            'contract': 0.4, 'displace': 0.5, 'shift': 0.3, 'mode': 0.5, 'reharm': 0.6},
    'interval': ('expand', 'contract', 'liquidate', 'combine'),  # one of them per chain at most (liquidate /
    #                                                              combine lose the contour: not drawn - 'ops')
    'subject': ('invert', 'mode', 'reharm', 'displace'),         # the stretto subject's op (one at most)
    'novel': 2.0,                               # an op the piece has not used yet: its weight x this
    'moves': {'up': 1.0, 'real': 0.8, 'rise3': 0.6, 'fifths': 0.5},
    'deg': {'up': (1, 2, 3, 4), 'rise3': (1, 3, 5, 7), 'fifths': (1, 4, 7, 3), 'real': (1, 1, 1, 1)},
    'real': 2,                                  # a real sequence's transposition per model (semitones up)
    'links': {'plain': 1.0, 'applied': 0.8},
    'arrive': {'pac': 1.0, 'chroma': 0.9, 'hc': 0.6, 'deceptive': 0.4},
    'isteps': {-4: 1.0, -3: 0.8, -7: 0.5},      # the answer / the imitation: scale steps under the call
    'hold': 2.0,                                # a statement's last note held this many beats more (then rests)
    'rise': 7,                                  # the register's rise over a process (semitones)
    'top': 91,                                  # a statement's highest note at most (G6)
    'false': 0.35,                              # a false entry at a later process's start (after the thinning)
    'levels': ('p', 'mp', 'f'),                 # a process's level: the first / a later one at its start, its goal
    'tex': {'sequence': {'walk_dialogue': 1.0, 'dialogue_brass': 0.4}, 'stretto': {'walk_poly': 1.0},
            'against': {'walk_poly': 1.0, 'walk_dialogue': 0.4}, 'bass': {'dev_bass': 1.0}},
}
"""DEV_WALK v2's vocabulary (round o17 - o16's judges: the walk's phases as 4-6 bar panels, each a new colour, 29 vs
6 sentences; its deep op chains as unrelated material, 16 vs 6; "when a fugato starts, finish it"): Writer.walk2. A
dev_dialogue block stays one block; it holds 1-'most' PROCESSES of 'bars' song bars, drawn per piece ('procs',
'reuse': the piece's other blocks draw other kinds; the development's last process prefers the stretto, 'drive'):
'sequence' - the unit stated 'states' times as a sequence ('moves': up a step, up by thirds, the falling-fifths
chain, real: 'real' semitones up), the counter entering in the second model half a model late and in the third a
quarter, then the head per bar and the kernel per half bar in the two lines in turn into the arrival; 'stretto' -
the subject (the motto, 'subject' its one op at most) in imitation 'isteps' under, the entries closer and closer
(a model, a model, a bar, half a bar) and a step higher each pair; 'against' - the unit over the second theme's head
(augmented) in every model; 'bass' - the unit in the bass under the other kernel's head (a block of one process).
Every process arrives in the next one's key ('arrive', the last in the home key - the retransition follows), its
register rises 'rise' semitones and its level climbs ('levels' - capped under the climax by LOUDEST); a statement's
rest is its last note held 'hold' beats, then rests (no inner derivations). The unit's op chain: 'depth' ops by the
development's half, at most 'cap' in any statement, one 'interval' op at most. A false entry ('false', one a piece)
opens a later process after the thinning: the arrival before it breaks off. The texture ('tex') is the first
process's: one family, its colour growing at the block's middle (walk_dialogue / walk_poly: a doubling enters)."""

WALK3 = dict(
    WALK2,
    secs=17.0,                                  # a process's seconds (about): the block's count by its duration
    least=4,                                    # a process's internal bars at least
    slow=2.7,                                   # an internal bar of this many seconds or more: a slow tempo (one-bar
    #                                             models, the answer a quarter model late, the kernel bridging rests)
    states=4,                                   # the unit's statements in a sequence at most
    drive=2, drive_s=6.5,                       # the head / kernel drive: bars and seconds at most
    procs={'sequence': 1.0, 'stretto': 0.9, 'against': 0.7, 'bass': 0.45},
    into=3.0,
    depth=({0: 0.2, 1: 1.0, 2: 0.4}, {1: 0.6, 2: 1.0}),     # the unit's ops: the development's first / second half                                   # the stretto as the development's last process (into the pedal) x
    ops={'invert': 1.0, 'augment': 0.3, 'head': 0.6, 'frag3': 0.4, 'expand': 0.6, 'contract': 0.4,
         'displace': 0.5, 'shift': 0.3, 'reharm': 0.6},
    subject=('invert', 'reharm', 'displace'),
    moves={'up': 1.0, 'down': 0.6, 'rise3': 0.6, 'fifths': 0.7},
    deg={'up': (1, 2, 3, 4), 'down': (1, 7, 6, 5), 'rise3': (1, 3, 5, 7), 'fifths': (1, 4, 7, 3)},
    arrive={'elide': 1.0, 'hc': 0.8, 'deceptive': 0.6, 'pac': 0.5, 'chroma': 0.3},
    modulate={'pivot': 1.0, 'dominant': 0.6},
    mid=0.4,                                    # the modulation at a process boundary (else in the block's last
    #                                             arrival)
    hold_s=1.2,                                 # a statement's held last note: 'hold' beats, this many seconds at most
    gap_s=1.0,                                  # a model's rest of this many seconds and more: the kernel bridges it
    min_beat=0.25, min_s=0.12,                  # no note under a 16th (internal beats / the scale) or these seconds
    bass_c=46,                                  # the stretto's bass entries: their register's centre (B-flat 2)
    levels=('p', 'mp', 'f'),                    # the block's level: the development's first block / a later one at its
    #                                             start, the block's end - one ramp
    tex={'sequence': {'walk_dialogue3': 1.0, 'dialogue_brass': 0.4}, 'stretto': {'walk_stretto': 1.0},
         'against': {'walk_poly': 1.0, 'walk_dialogue3': 0.4}, 'bass': {'dev_bass': 1.0}},
)
"""DEV_WALK v3's vocabulary (round o18a - o17's judges: "the theme set in one new key after another with no
preparation" (key panels 23 vs 11, modulation 21 vs 11), "bars 40-55 stand still" in the andantes, v2's stretto never
named; o17's silent_notes rejects: the unit diminished into 32nds at a model's end): Writer.walk3. WALK2's, with: ONE
key per block (its path's j-th - the j-th development block) or one prepared modulation into the next block's key
('modulate': a pivot chord diatonic in both keys before the new V7, or the new key's V7 held a bar; at a process
boundary 'mid' of the time, else in the block's last arrival); the in-key arrivals mostly elided or half cadences
('arrive'); before the retransition the last process drives on (the home key's dominant, no cadence - the stretto
preferred there, 'into'); processes sized by 'secs' (an andante's block more, shorter processes; at 'slow' tempi one-bar
models, the answer a quarter model late, a rest of 'gap_s' bridged by the kernel); the drive 'drive' bars / 'drive_s'
seconds at most; no diminution and no mode op ('ops'); the stretto four voices (the tenor in the harmony's top voice,
the bass entries in the bass - the texture walk_stretto); one level ramp per block ('levels'); no note under
'min_beat' / 'min_s'; no false entry (never named in o16 / o17)."""


APEX = {'restate': {}, 'augment': {'tex': {'apex_augment': 1.0}}, 'combine': {'tex': {'apex_combine': 1.0}},
        'reharm': {}, 'second': {}, 'theme_aug': {'tex': {'apex_theme': 1.0}}}
"""The climax's MATERIAL (plan['set']['apex'], round o3 - 11 of 14 judges: "the climax restates the theme louder in
octaves"): 'restate' the first theme's sentence (the q1 / o2 climax), 'augment' the motto in augmentation in the
brass under the strings' running figuration, 'combine' the second theme with the motto against it, 'reharm' the first
theme in another key (the tonic major / bVI), 'second' the second theme as the apotheosis (in the major). 'augment'
and 'combine' have their own textures; the others take the climax type's (CLIMAXES). Round o6 (o5's judges: 5 of 8
climaxes "bring new material - a new hymn over harp arpeggios"): 'combine' is the whole motto on top (the brass with
the violins) and the second theme under it, 'theme_aug' the first theme in augmentation in the brass under the
violins' running figuration (apex_augment), and every statement of the second theme is its first statement's tune
(Writer.cantilena's skeleton by the theme's first mode). Round o9 (o8's judges, 5 of 8 new climaxes: "violin 16th
broken chords over a brass chorale, the theme absent"): 'theme_aug' has its own texture (apex_theme: the augmented
theme in the brass, the theme at its own speed over it, no running figuration) and the augmented climaxes sing the
material at its own speed against its augmentation (APEX_CANON, Writer.canon)."""
APEX_CANON = {'over': 7, 'rise': 1, 'floor': 67, 'top': 84, 'answer': True}
"""The augmented climax's counter (round o9; Writer.canon): 'augment' the motto at its own values every two bars,
'theme_aug' the first theme at its own speed - 'over' semitones above the augmented line's median, each motto statement
'rise' scale steps over the one before (a sequence, never a copy); the augmented line moved up by octaves until its
lowest note reaches 'floor' (the trumpets' tune floor G4) while its highest stays at or under 'top'. 'answer' (round
o10 - o9's judges, APPS: "a climax of held brass blocks under a violin line"): a one-bar motto's second bar answered by
its inverted head - the counter on top never pauses for a bar over the held augmentation."""
APEX_RIVER = {'augment': 'theme_aug'}
"""Round o11 (o10's judges, NYQP: "no tune to hold - never the opening back at the climax"; the masterpiece panel:
"river / journey forms keep one tune that returns"): a river piece's augmented climax augments its tune (theme1, the
river's), the motto's augmentation is the other forms'."""
APEX_SCHERZO = {'augment': 'combine', 'theme_aug': 'reharm'}
"""The scherzo's climax material (round o7 - o6's judges, the worst piece, GKVA: "the theme augmented into whole-bar
notes"): in the fast 3/4 (scale 2) the augmented climaxes take a stand-in - the dance tune over the second theme
('combine': Writer.apex states the dance at its own speed), the dance reharmonised in another key."""
CLX_MODES = ('home', 'picardy', 'parallel', 'relative')
"""The climax's key against the home (plan['set']['clx_mode'], round o6 - o5's judges heard one plan in both codes: "a
minor piece turns to the parallel major in the climax, then a soft coda"): 'home' all in the home key; 'picardy' the
climax and the coda at home, only the last chord in the tonic major (a minor piece; a major one: 'home'); 'parallel'
a minor piece's climax, coda and end in the tonic major, a major piece's climax in the tonic minor (a dark climax,
then home); 'relative' the climax in the relative key, the coda home (clx_keys)."""


def clx_keys(home: str, mode: str) -> tuple:
    """(the climax's key, the coda's, the last chord's) of CLX_MODES `mode`."""
    K = Key(home)
    minor = K.minorish
    par = _transpose_key(home, 0, 'major' if minor else 'minor')
    if mode == 'parallel':
        return (par, par, par) if minor else (par, home, home)
    if mode == 'relative':
        return _second_key(home, 'relative'), home, home
    if mode == 'picardy' and minor:
        return home, home, par
    return home, home, home
ENDINGS = {'cadence': {'tex': {'end_cadence': 1.0}}, 'strokes': {'tex': {'end_strokes': 1.0}},
           'motto': {'tex': {'end_motto': 1.0}}, 'held': {'tex': {'end_held': 1.0}},
           'plagal': {'tex': {'end_held': 1.0, 'end_cadence': 0.5}}}
"""The last bars (plan['set']['ending'], round o3: one ending in every piece; round o5 - o4's judges: "a bare unison or
a stop", "a full chord with its third, prepared by a dominant"): every ending is a voiced cadence (ENDING_CADENCE: the
first bar the approach, the rest the tonic) - 'cadence' V7 - I held by the full orchestra under a timpani roll,
'strokes' V7 - I struck (STROKES: the approach's chords cut into strokes), 'motto' the motto's head in unison over V7
landing on the tonic chord the winds and horns voice, 'held' V7 - I held over the roll, 'plagal' - the name kept for
the set's draws (a renamed draw would re-roll every plan) - since round o11 the predominant, V7 and I under the held
colour (ENDING_CADENCE 'pre'), no IV - I. An end_soft ending draws SOFT_ENDINGS: the soft fading chord after V7."""
ENDING_CADENCE = {'cadence': 'cad64', 'strokes': 'V', 'motto': 'V', 'held': 'pre', 'plagal': 'pre'}
"""Round o7 - o6's judges: "several pieces stop on two or three held chords" (5 of 14), "the dominant without a bass,
then the tonic voiced upside-down" (both orchestrators, 9 pieces): the approach bar's plan per ending (_approach) -
'cad64' the cadential six-four, then V7 (the soprano 3 - 2 - 1 over the bass's 5 - 5 - 1), 'pre' a predominant (IV /
iv), then V7 (1 - 7 - 1), 'V' V7 (2 - 1), 'IV' plagal (1 held); the soft endings (SOFT_ENDINGS, the set's ending draw
mapped by SOFT_OF): also 'pedal' IV over the tonic pedal fading to I (4 - 3) and 'echo' the motto's head, quiet, over
V7 into the tonic. The chords are voiced by END_VOICING."""
SOFT_ENDINGS = {'V': 1.0, 'pre': 0.8, 'cad64': 0.9, 'echo': 0.8}
SOFT_OF = {'cadence': 'V', 'strokes': 'cad64', 'motto': 'echo', 'held': 'pre', 'plagal': 'pre'}
"""Round o11 (o10's judges, DCQG 52-60: "fades to held chords and a soft plagal G - D with no V - I", XFBA "C - D - G, no
V7"; the masterpiece panel: "every ending gets a real V - I"): the plagal ending is the predominant, V7 and I (its
texture keeps the held colour), and no soft ending fades on IV or over the tonic pedal - V7, the predominant and V7,
the cadential six-four or the motto's echo over V7, each into the tonic."""
END_VOICING = {'harmony': {'h1': (64, 79, 71), 'h2': (59, 74, 66), 'h3': (55, 69, 62), 'h4': (53, 67, 60)},
               'inner': {'i1': (45, 58, 52), 'i2': (38, 53, 45)}}
"""The last block's chord voices (round o7; voicing.voice ranges): the four harmony parts close under the tune
(the end textures: violins II, clarinets, violas, horns top-down), the two inner parts under them (the trombones
closed under the horns, the bassoons in the tenor) - the bass's root under all. V7 - I: the leading tone rises to
the tonic, the seventh falls to the third (_resolve)."""


def _resolve(parts: dict, chart, key: str, mel=(), ranges=None) -> dict:
    """The last chord of a chart voiced from the chord before it in parts {voice: notes} (round o7 - o6's
    orchestrators: the voicing's smallest motion let the leading tone fall, the seventh rise and the inner voices leap
    a seventh): every voice moves to the nearest tone of the last chord within its range (ranges {voice: (lo, hi,
    centre)}) and under the tune's final note; over V7 the leading tone rises to the tonic (in an inner voice under
    the tune's tonic it may fall) and the seventh falls to the third; the third is never left out."""
    rows = sorted(chart)
    if len(rows) < 2:
        return parts
    K = Key(key)
    (a5, _, s5), (a1, _, s1) = rows[-2], rows[-1]
    c5, c1 = chord(s5), chord(s1)
    pcs1 = {(c1.root + i_) % 12 for i_ in c1.intervals}
    third = (c1.root + next((i_ for i_ in c1.intervals if i_ in (3, 4)), 4)) % 12
    dom = c5.root % 12 == (K.tonic + 7) % 12 and c1.root % 12 == K.tonic % 12
    lt, sev = (K.tonic + 11) % 12, (K.tonic + 5) % 12
    cap = min((p for a, d, p in mel if a <= a1 + _EPS < a + d), default=128)
    rng_ = ranges or {}
    goal = {}
    used = [p % 12 for a, d, p in mel if a <= a1 + _EPS < a + d]
    for v, ns in sorted(parts.items()):
        at5 = next((n for n in ns if n[0] <= a5 + _EPS and n[0] + n[1] > a5 + _EPS), None)
        if at5 is None or not any(abs(n[0] - a1) < _EPS for n in ns):
            continue
        p5 = at5[2]
        lo, hi = rng_.get(v, (0, 127))[:2]
        hi = min(hi, cap - 1)
        if dom and p5 % 12 == lt and p5 + 1 <= hi:
            goal[v] = p5 + 1
            used.append(goal[v] % 12)
            continue
        if dom and p5 % 12 == sev and any(q % 12 == third for q in range(p5 - 2, p5)):
            goal[v] = max(q for q in range(p5 - 2, p5) if q % 12 == third)
            used.append(third)
            continue
        c = [q for q in range(max(lo, p5 - 7), min(hi, p5 + 7) + 1) if q % 12 in pcs1]
        # (the doubling: the root, then the fifth - a second third is the last choice)
        goal[v] = min(c, key=lambda q: (abs(q - p5) + (3 if q % 12 == third and third in used else 0), -q)) if c             else next(n[2] for n in ns if abs(n[0] - a1) < _EPS)
        used.append(goal[v] % 12)
    if goal and third not in {q % 12 for q in goal.values()} | {p % 12 for a, d, p in mel if a <= a1 + _EPS < a + d}:
        v = min(goal, key=lambda v_: min((abs(q - goal[v_]) for q in range(goal[v_] - 4, goal[v_] + 5)
                                          if q % 12 == third), default=99))
        goal[v] = min((q for q in range(goal[v] - 4, goal[v] + 5) if q % 12 == third), key=lambda q: abs(q - goal[v]))
    return {v: [(n[0], n[1], goal[v]) if v in goal and abs(n[0] - a1) < _EPS else n for n in ns]
            for v, ns in parts.items()}


STROKES = {'duple': (0.0, 1.0, 2.0), 'compound': (0.0, 1.5), 'len': 0.6, 'motto': True}
"""The strokes of the 'strokes' ending's approach bar (internal beats of the bar; 'len' the stroke in song beats);
'motto' (round o9 - o8's judges: "a quarter-note V chord three times, then a held I"): in the motto's rhythm - its
onsets inside the first bar, 2 to 5 of them - where it has one."""
END_PRE = {'bars': 1, 'chord': {'cad64': ('IV', 'iv'), 'V': ('IV', 'iv'), 'echo': ('IV', 'iv'), 'pre': ('vi', 'VI'),
                                'amen': ('ii', 'iv'), 'decep': ('IV', 'iv'),
                                'IV': ('vi', 'VI'), 'pedal': ('vi', 'VI')}}
"""The last block's predominant bar(s) before its approach (round o9 - o8's judges: "a bare 2-beat V - I": 'bars'
when the block has 2 more; 'chord' (major, minor) per approach plan): the motto's head over it - the close built from
the theme; the end rows are 3 bars."""
POST_PEAK = {'recap2': {'tex': {'cantabile_strings': 1.0, 'dev_poly': 0.8},
                        'dyn': [(0, 'f'), (0.5, 'mf'), (1, 'mp')]},
             'coda_soft': {'tex': {'cantabile_strings': 1.0, 'cantabile_horn': 0.6, 'dissolve': 0.3}}}
"""Round o9 (o8's judges: "a harp interlude between the climax and the coda", FVNG; "a solo oboe coda after the
climax", XBGS): the block right after the peak is a controlled descent - the second theme's return falls from f
under its motto counter-line (no harp-only pad), the dissolving coda sung by the violins with a counter."""
EPISODE_FROM = {'river': 'march'}
"""Round o9 (o8's judges: "episodes with new tunes unrelated to the theme", XBGS 25-52): a river piece's episode (the
hunt) is its tune varied - VARIATIONS' technique ('march': dotted) in the second key."""
DERIVE = {'always': {'C': 'invert', 'R': 'plain'}, 'continue': ('C', 'R')}
"""Round o9 (the same tell, KQFD's trio): the trio's ('C') and the river's ('R') tunes grow from the motto even when
the set draws no derivation ('always': the derivation then), and their answer bars go on with the motto ('continue':
Writer.cantilena)."""
STATIC = {'bars': 8, 'figure': {'from': 4, 'span': 4, 'how': {'arp': 1.0, 'rock': 0.7}},
          'walk': ('t2', 't2b', 'trio', 'river', 'episode', 'recap2')}
"""Round o9 (o8's judges, TZKN: "a harp ostinato under held strings for 28 bars"): in a block longer than 'bars' song
bars the held harmony moves (INNER_MOTION, _move_inner) and the harp's arpeggios stop after 'bars' bars. Round o10
(o9's judges, EYPC: "the trio a flute over block clarinet / bassoon chords for 28 bars"; the o9 static_run tell missed
it - a chord per half bar counted as motion): 'figure' - where such a block has no ostinato or figuration, its two top
held parts break into a figure ('how': eo._ostinato's arpeggio / rocking 8ths) from bar 'from' on, every other 'span'
bars (_figure_held). Round o11 (o10's judges, about 30 of 56: "static middle episodes - held chords under a thin line,
no moving bass"): 'walk' - the long bass of these kinds' lyrical textures moves by the half bar (_walk_long)."""


def _walk_long(bass, chart, key: str, U: float) -> list:
    """STATIC['walk'] (round o11 - o10's judges: "static middle episodes: held chords over a thin line, no moving bass",
    XFBA 30-37, UEQX 31-42): a bass note held a bar or more moves by the half bar - the chord's root, then another
    chord tone a fourth / fifth / third away, and on the last half bar a step into the next chord's bass."""
    pcs = pcs_of(key)
    srt = sorted(bass)
    out = []
    h = U / 2
    for i, (a, d, p) in enumerate(srt):
        nxt = srt[i + 1][2] if i + 1 < len(srt) else None
        if d < U - _EPS or nxt is None:
            out.append((a, d, p))
            continue
        n = int(d / h + _EPS)
        for j in range(n):
            x = a + j * h
            du = h if j < n - 1 else a + d - x
            q = p
            if j == n - 1 and n >= 2 and abs(nxt - p) > 2:
                q = _step(nxt, 1 if p > nxt else -1, pcs)          # (the passing step into the next chord)
            elif j % 2 == 1:
                cp = _cpcs(_chart_at(chart, x))
                c = [y for y in range(p - 9, p + 10) if y % 12 in cp and y != p and 31 <= y <= 57]
                q = min(c, key=lambda y: (abs(abs(y - p) - 6), -y)) if c else p
            out.append((x, max(0.25, du - 0.05), q))
    return out


def _figure_held(harm: dict, start: float, bar: float, rs) -> dict:
    """The held harmony {voice: notes} with its two top voices figured every other STATIC['figure'] span after its
    'from' bars (eo._ostinato on them as its o1 / o2)."""
    F_ = STATIC['figure']
    vs = sorted(harm, key=lambda v: -max((p for _, _, p in harm[v]), default=0))[:2]
    fig = eo._ostinato({'o1': harm[vs[0]], 'o2': harm[vs[1]]}, _pick(rs, F_['how']), rs)
    a0, sp = start + F_['from'] * bar, F_['span'] * bar

    def on(a):
        return a >= a0 - _EPS and int((a - a0 + _EPS) // sp) % 2 == 0
    out = dict(harm)
    for v, o_ in zip(vs, ('o1', 'o2')):
        out[v] = sorted([n for n in harm[v] if not on(n[0])] + [n for n in fig.get(o_, []) if on(n[0])])
        # (a held note running into a figured span ends there)
        out[v] = [(a, min(d, max(_EPS, next((x - a for x in (a0 + sp * k for k in range(64)) if x > a + _EPS
                                             and on(x)), d))), p) if not on(a) else (a, d, p) for a, d, p in out[v]]
    return out
OPENING_COLOURS = {'strings': {'motto_unison': 1.0}, 'brass': {'motto_brass': 1.0}}
"""The call's first colour (plan['set']['colour']): the motto in the strings' unison or as a brass fanfare."""
CODA_KINDS = {'triumph': ('coda', 'end'), 'dissolve': ('coda_soft', 'end_soft')}
CODA_PLANS = {'triumph': {'stretto': 1.0, 'pedal': 0.9, 'hymn': 0.8},
              'dissolve': {'descent': 1.0, 'echo': 0.9, 'memory': 0.8}}
"""The coda's plan per coda kind (plan['set']['coda_plan'], round o5; Writer.coda): a drawn plan the kind does not
have is drawn again from the kind's."""
CODA_FALL = ((0, 'f'), (0.3, 'mp'), (1, 'pp'))
"""The dissolving coda's dynamics right after the climax (round o8 - o7's judges: "a soft held-chord coda right after
an ff climax"): it starts loud and dies away - its first statement the motto's echo of the climax."""
CODA_RECALL = {'bars': 4, 'unit': 2}
"""The motto recalled in the second theme's codas ('hymn' / 'memory', round o8 - o7's judges: "climaxes and codas
without the motto", THGD / WDMN / PFBT / JWCL): its statement fills the 'bars' bars before the last two (a coda of
'bars' + 4 bars or more). Round o12 (o11's judges: "codas that sustain instead of transforming"): 'bars' 4 (2 in a
shorter coda), a statement per 'unit' bars - the hymn's motto rising a step, the memory's head falling a step and every
other one inverted."""
CODA_CANON = True
"""The triumph coda's augmented motto with the motto at its own speed over it (round o9; Writer.canon - o8's judges:
"the coda as violin 16ths over a brass chorale with the theme absent")."""
CLIMAXES = {'brass': {},
            'strings': {'tex': {'apotheosis_strings': 1.0}},
            # (round o8: ARRIVALS; round o9 - o8's judges: "the choir only in the last 10 bars", FFYD: the chorale
            # climax in the brass choir - the choir never enters for the close alone)
            'chorale': {'tex': {'tutti_chorale_brass': 1.0}},
            'quiet': {'tex': {'quiet_climax': 1.0}, 'dyn': [(0, 'p', 'step'), (0.5, 'mf'), (0.8, 'f'), (1, 'mp')]},
            # (round o24, MACRO only - no mood draws it: the climax as a dialogue, the tune against the brass choir's
            # own line - o23's judges: "the unison climax in every piece")
            'dialogue': {'tex': {'apex_dialogue': 1.0}}}
"""The climax's type (plan['set']['climax'], where the mood's 'climax' weights have it; round o2 - the q1 set was one
brass climax per piece): the peak block's override - the brass tutti (the kind's own), the strings' apotheosis, the
chorale over the choir, a quiet climax (the theme high and hushed, swelling to f once)."""
BUILDS = {'tremolo': {}, 'pulse': {'tex': {'pulse_build': 1.0}},
          'stretto': {'tex': {'stretto_build': 1.0}}, 'calls': {'tex': {'calls_build': 1.0}},
          'bass': {'tex': {'bass_build': 1.0}}, 'fugato': {'tex': {'fugato_build': 1.0}},
          'subito': {'tex': {'subito_build': 1.0}, 'dyn': [(0, 'pp', 'step'), (0.5, 'mp'), (1, 'ff')]}}
"""The retransition's build (plan['set']['build']; Writer.retrans writes each from the motto - round o3, 13 of 14
judges named ONE stock build: a timpani pedal, a rising oboe, a cymbal roll): string tremolo over a pedal (the
kind's own), the strings' repeated 8ths over a plucked pedal, the motto in stretto, the brass calls answered closer
and closer, the motto in the bass under a high pedal, a fugato thickening into the climax, subito pp and the long
crescendo."""
CLIMAX_DEFAULT = {'brass': 1.0, 'strings': 0.8, 'chorale': 0.6}
ARRIVALS = {'crash': 0.5, 'dry': 0.8, 'timp': 1.0, 'none': 0.6}
ARRIVAL_FIG = {'crash': {}, 'dry': {'crash': 'crash_dry', 'swell_cym': None},
               'timp': {'crash': None, 'crash_dry': None, 'swell_cym': None},
               'none': {'crash': None, 'crash_dry': None, 'swell_cym': None}}
"""The climax's arrival per piece (round o8 - o7's judges and the stock_n tell, 0.54 a piece: "the stock build - a
cymbal roll, a crash and the choir"): drawn per piece - the crash with the suspended cymbal's roll into it, the dry
crash, the timpani alone, none - and ARRIVAL_FIG maps the build's and the climax's cymbal figures to it (None: left
out). The chorale climax draws the choir or the brass choir (CLIMAXES)."""
BUILD_FRAMES = {
    'pedal': None,
    'ascent': {'major': (('I', 1), ('V', 2), ('I', 3), ('IV', 4), ('V', 5)),
               'minor': (('i', 1), ('V', 2), ('i', 3), ('iv', 4), ('V', 5))},
    'circle': {'major': (('vi', 6), ('ii', 2), ('V', 5), ('I', 1), ('IV', 4), ('ii', 2)),
               'minor': (('VI', 6), ('ii°', 2), ('V', 5), ('i', 1), ('iv', 4), ('ii°', 2))},
    'lament': {'major': (('I', 1), ('V', 7), ('vi', 6), ('iii', 5), ('IV', 4), ('I', 3), ('ii', 2)),
               'minor': (('i', 1), ('VII', 7), ('VI', 6), ('V', 5), ('iv', 4), ('III', 3), ('ii°', 2))}}
"""The build's harmonic frame (plan['set']['frame'], round o4 - o3's judges heard one frame under every build: "a
bare dominant pedal in timpani and basses, a woodwind line climbing"): the dominant pedal (Writer.retrans' own plan),
or (roman, the bass's scale degree) per bar before the last bar's V7 - a bass rising by step to V (spread over the
block), a sequence of fifths, a bass falling by step (the cycle again when the block is longer)."""
RETRANS_LEAD = True
"""The retransition's last bar: the motto's head over V7 into the climax (round o9), not one held note."""
T1B_DOT = 0.5
"""The share of the first theme's restatements (t1b) whose even pairs are dotted (round o4)."""
RECAP_VARY = ('reharm', 'dot')
"""The restated recapitulation (APEX 'restate'): its answer over the submediant, the cadence from the subdominant,
the statements dotted (Writer.sentence's vary - round o4: "recapitulations copied from the exposition")."""

SET_PLAN = None
"""Round o18b (o16 / o17: the judges' template flags per packet 45-52 for our pieces against the references' 7-28,
and they come from SET-level plans both codes shared - the timpani dominant-pedal build into the return, the doubled
unison climax at 72-87 % of the piece, the harp coda and the lone timpani last bar, the short-short-long motto, the
one-step-a-bar sequence up to the climax, mostly 6/8): None = off (bit-identical); SET_PLAN_ON (genres.
symphony_setplan(True) switches it with the set's tables) makes the set-level choices diverse and memoryful:
  builds   the retransition's GESTURE (plan['set']['build']: GESTURES) - the writer, the harmonic frame, the dominant
           pedal's bars (most none) and whether RT_DRIVE's struck timpani pedal plays (only 'pulse');
  arc      plan['set']['arc'] 'crisis' (ARC_CRISIS): the climax after the development's build in a dark key, then a
           collapse and a QUIET return (the code review's C1: another dramatic arc than "the return is the climax");
  voicing  plan['set']['voicing'] 'layers': the summit harmonised (VOICING) - the trumpets and the violins on the
           tune, the horns / trombones / reeds on the chords, no unison stack (C8);
  contour  plan['set']['contour']: the climax's statements and the swell's steps by CONTOURS, not a step a bar;
  endings  plan['set']['ending'] families (END_FAMILIES): the motto's last word, the plagal amen after V - I, a
           deceptive cadence then V - I, a held cadence over a moving line, the struck stretto close; no harp in the
           codas and no timpani in the last block (END_COLOURS) but where the strokes strike it.
The motto's rhythm families and the meter mix are the set's tables (genres.symphony_setplan: MOTTO_FAMILIES,
CELLS_V, the arc's meter rules)."""
SET_PLAN_V2 = {'builds': True, 'arc': True, 'voicing': True, 'contour': True, 'endings': True, 'v2': True}
"""Round o19a: SET_PLAN v2 - SET_PLAN_V1 (o18b's) and the fixes of its judges ('v2'): the layout's SHAPE drawn per
piece (FORM_SHAPE: the section count; the set's memory per feel - genres.SETPLAN_SHAPE), the climax's place drawn
(PEAK_AT), no harp after the climax (POST_HARP, POST_PEAK_V2), the crisis as the summit with a quiet transformed
return (CRISIS_V2), the endings' motto and cadences in the melody (END_V2)."""
SET_PLAN_V3 = {'builds': True, 'arc': False, 'voicing': True, 'contour': True, 'endings': True, 'v2': True, 'v3': True}
"""Round o20: SET_PLAN v3 - v2 and the fixes of o19a's judges ('v3'): the shape by MERGING and lengthening (FORM_MERGE
instead of FORM_SHAPE: no added sections, at most 12), the section textures drawn with the set's memory (TEX_V3), the
dissolving fade capped (FADE_V3), no crisis arc ('arc' off), the climax at 0.7 or later (PEAK_AT_V3), the harp gated on
its level (POST_HARP_V3). v2's no post-climax harp, the endings (END_V2), the gestures and key_apart stay."""
SET_PLAN_V4 = dict(SET_PLAN_V3, v4=True)
"""Round o22: SET_PLAN v4 - v3 and the fixes of o20's judges ('v4'): every merged block changes at its join (JOIN_V4:
the merged block's own material and a new texture inside one section, never just more bars of the same), the
sentence's fragmentation by a drawn shape with the set's memory (FRAG_V4: the one-step-a-bar ladder one shape of
five), the piece's bar plan a function of its slot (draws['form_seed']: composer.set_plan compares the realised
section lengths - bar_plan - and keeps them apart). The set's memory on the mode and the key, the endings' dynamic
and the layouts per feel are the set planner's (genres.SETPLAN_ARC_V4 / SETPLAN_SHAPE_V4 / SETPLAN_BARS)."""
SET_PLAN_ON = SET_PLAN_V4
"""The flag's current version (genres.symphony_setplan(True); version 3 = SET_PLAN_V3, 2 = SET_PLAN_V2, 1 =
SET_PLAN_V1)."""
SET_PLAN_V1 = {'builds': True, 'arc': True, 'voicing': True, 'contour': True, 'endings': True}
GESTURES = {
    # the build gesture: 'writer' (the melody: Writer.retrans), 'frames' (the harmonic frame - the set's 'frame' draw
    # where it is one of them, else the first), 'pedal' (song bars of the dominant pedal before the last bar; 0 none),
    # 'drive' (RT_DRIVE's struck pedal), 'over' (the block's texture / dynamics), 'need' (the block's least bars)
    'swell': {'writer': 'wave', 'frames': ('ascent',), 'pedal': 0, 'drive': False, 'need': 6,
              'over': {'tex': {'swell_build': 1.0}, 'dyn': [(0, 'pp', 'step'), (0.5, 'mp'), (1, 'ff')]}},
    'silence': {'writer': 'kernel', 'frames': ('circle', 'ascent'), 'pedal': 2, 'drive': False, 'need': 6,
                'silence': 1, 'over': {'tex': {'swell_build': 1.0, 'stretto_build': 0.6},
                                       'dyn': [(0, 'p', 'step'), (0.8, 'ff')]}},
    'fugato': {'writer': 'fugato', 'frames': ('ascent', 'circle'), 'pedal': 0, 'drive': False, 'need': 6,
               'over': {'tex': {'fugato_build': 1.0}}},
    'lowbrass': {'writer': 'lowbrass', 'frames': ('circle', 'lament'), 'pedal': 0, 'drive': False, 'need': 6,
                 'over': {'tex': {'lowbrass_build': 1.0}, 'dyn': [(0, 'p', 'step'), (1, 'ff')]}},
    'deceptive': {'writer': 'stretto', 'frames': ('ascent',), 'pedal': 0, 'drive': False, 'need': 7,
                  'deceptive': True, 'over': {'tex': {'stretto_build': 1.0, 'swell_build': 0.6}}},
    'stretto': {'writer': 'stretto', 'frames': ('circle', 'ascent'), 'pedal': 2, 'drive': False, 'need': 6,
                'over': {'tex': {'stretto_build': 1.0}}},
    'calls': {'writer': 'calls', 'frames': ('lament', 'circle'), 'pedal': 2, 'drive': False, 'need': 6,
              'over': {'tex': {'calls_build': 1.0}}},
    'bass': {'writer': 'bass', 'frames': ('pedal',), 'pedal': 6, 'drive': False, 'need': 6,
             'over': {'tex': {'bass_build': 1.0}}},
    'pulse': {'writer': 'kernel', 'frames': ('pedal',), 'pedal': 6, 'drive': True, 'need': 6,
              'over': {'tex': {'pulse_build': 1.0}}},
    'subito': {'writer': 'wave', 'frames': ('lament',), 'pedal': 0, 'drive': False, 'need': 6,
               'over': {'tex': {'subito_build': 1.0}, 'dyn': [(0, 'pp', 'step'), (0.5, 'mp'), (1, 'ff')]}},
    # (not drawn: the crisis arc's collapse after its climax - ARC_CRISIS)
    'collapse': {'writer': 'kernel', 'frames': ('lament',), 'pedal': 0, 'drive': False, 'need': 4, 'over': {}},
}
"""The builds into the climax under SET_PLAN (plan['set']['build']; Writer.retrans): 'swell' a long crescendo over a
bass rising by step, the motto's kernel in waves (CONTOURS); 'silence' the kernel's drive cut by a bar of silence
(a general pause), the climax entering subito; 'fugato' the entries a bar apart over a moving bass; 'lowbrass' the
motto augmented in the trombones (the bass) under the strings' tremolo, a sequence of fifths; 'deceptive' the stretto
arriving on V7 - vi (bVI) at f, subito p, then the real dominant crescendo; 'stretto' / 'calls' / 'bass' / 'subito'
as BUILDS (no struck pedal); 'pulse' the one classic build - the repeated 8ths over the dominant pedal and RT_DRIVE's
timpani. 'tremolo' (BUILDS' default, the stock timpani pedal) is retired."""
ARC_CRISIS = {'kinds': ('dev_dialogue', 'dev_fugato', 'var', 'episode'), 'collapse': 4,
              'collapse_over': {'tex': {'collapse_build': 1.0}, 'dyn': [(0, 'f'), (0.5, 'mp'), (1, 'p')],
                                'level': 0.5},
              'calm_over': {'tex': {'cantabile_strings': 0.6, 'drive_strings': 1.0, 'motto_bass': 0.5},
                            'dyn': [(0, 'p', 'step'), (0.6, 'mf'), (1, 'f')], 'sf': False, 'level': 0.6},
              'calm_cut': 2, 'calm_min': 6}
"""The 'crisis' arc (SET_PLAN 'arc'): a piece whose retransition follows a development block ('kinds') plays its
build into a CRISIS - the climax (the peak, its material and type) in the dark key (a major piece: the tonic minor;
a minor / modal one: its home) - then a 'collapse' (a retransition of 'collapse' bars at least: the lament's falling
kernel, f to p, no pedal) and the return QUIET ('calm_over': the first theme at home, p to f, 'calm_cut' bars
shorter, at least 'calm_min'). No crisis with a quiet climax (its hush is the summit) or a literal restatement."""
VOICING = {'chords': ('horns', 'trombones', 'clarinets', 'bassoons'), 'brass': ('trumpets',)}
"""The summit's voicing 'layers' (SET_PLAN 'voicing'; _summit): only the 'brass' roles join the tune (the trumpets),
the 'chords' roles SUMMIT's fill would put on a line hold the chart's chord tones (nearest their sweet spot, voice-led,
under the top line) - the tune in two colours over a harmonised tutti, not one line in seven roles. 'tutti' = SUMMIT."""
CONTOURS = {'rise': (2, 1, 1, 1, 1, 1), 'wave': (2, -1, 2, -1, 2, -1), 'arch': (2, 2, -1, -1, -2, 1),
            'terrace': (0, 3, 0, 2, 0, -1)}
"""The climax's statement-to-statement steps (scale steps; SET_PLAN 'contour', the set's draw): Writer.apex's
augmented / combined motto and Writer.canon's counter - 'rise' the old climb (a step a statement), 'wave' up two and
back one, 'arch' up then down, 'terrace' a statement repeated, then a leap (the one-step-a-bar sequence up to the
climax was a tell)."""
END_FAMILIES = {'motto': 'V', 'amen': 'amen', 'deceptive': 'decep', 'line': 'pre', 'strokes': 'V', 'cadence': 'cad64'}
"""The ending families under SET_PLAN (plan['set']['ending'] -> the approach plan, ENDING_CADENCE / SOFT_OF):
'motto' the motto's last word (its head over V7 landing on the tonic), 'amen' V7 - I with the plagal IV6/4 between
(the amen over the tonic pedal), 'deceptive' V7 - vi in the bar before, then the predominant, V7 - I, 'line' the
predominant, V7 - I under a falling line in the tenor (END_LINE), 'strokes' V7 - I struck, 'cadence' the cadential
six-four. Every one also as the soft ending (the dissolving coda's)."""
END_TEX = {'motto': {'tex': {'end_motto': 1.0}}, 'amen': {'tex': {'end_held': 1.0}},
           'deceptive': {'tex': {'end_cadence': 1.0}}, 'line': {'tex': {'end_line': 1.0}},
           'strokes': {'tex': {'end_strokes': 1.0}}, 'cadence': {'tex': {'end_cadence': 1.0}}}
END_COLOURS = {'harp': ('coda', 'coda_soft', 'end', 'end_soft'), 'timpani': ('end', 'end_soft'),
               'keep_timp': ('strokes',)}
"""SET_PLAN: the harp leaves the codas and the last block, the timpani the last block (the harp coda and the lone
timpani bar were tells) - but where the ending strikes it ('keep_timp')."""
END_LINE = {'centre': 52, 'step': 0.5}
"""The 'line' ending's falling tenor line (_end_line): toward the tonic near 'centre' - 4, a step every 'step' x a bar
(from the octave over it at most), the counter of end_line."""
END_SOFT = {'motto': 'echo', 'amen': 'amen', 'deceptive': 'decep', 'line': 'pre', 'strokes': 'cad64', 'cadence': 'V'}
"""The ending families' soft approach (the dissolving coda's end_soft; END_FAMILIES)."""


def _deceptive(key: str) -> str:
    """The deceptive cadence's chord (SET_PLAN): vi in major, VI in minor, bVI in a church mode."""
    K = Key(key)
    return _roman(key, 'vi' if K.mode == 'major' else 'VI' if K.mode == 'minor' else 'bVI')


def _end_line(key: str, chart, t0: float, z: float, end: float, U: float) -> list:
    """END_LINE: the 'line' ending's tenor line - from the octave over the tonic (or lower: as many scale steps as it
    has half bars to z) falling a step every END_LINE['step'] bars to the tonic at z, held to `end`; fitted to the
    chart, its moving notes free (strict over their length)."""
    pk = pcs_of(key)
    tonic = _near({Key(key).tonic}, END_LINE['centre'] - 4)
    st = U * END_LINE['step']
    n = int((z - t0) / st + _EPS)
    if n < 1:
        return []
    top = min(n, 7)
    notes, x = [], t0
    hold = n - top
    for j in range(top, 0, -1):
        d = st * (1 + hold) if j == top else st
        notes.append((x, d, _step(tonic, j, pk)))
        x += d
    notes.append((z, end - z, tonic))
    return _mono(fit_line(notes, chart, key, strict=st + 0.1))


# ---- round o19a: SET_PLAN v2 (SET_PLAN['v2'])
FORM_SHAPE = {'deltas': (-2, -1, 0, 1, 2),
         'drop': (('kind', 't1b'), ('kind', 'close'), ('grow', 'trio'), ('kind', 't2b'), ('kind', 'episode'),
                  ('kind', 'intro'), ('var', 'var')),
         'add': ('t2b', 'episode', 'false', 'refrain', 'close', 'var')}
"""Round o19a (o18b's judges: "it is the BVMD plan exactly (202 bars, 13 sections, tutti at 141-162, harp episode S12,
coda S13)" - the layout is the template): plan['set']['sections'] - the piece's layout with fewer or more sections
(_shape_rows). 'drop' (in order; the first that applies, one per step): the first theme's restatement, the closing
group, the trio's repeat, the second theme's restatement, an episode, the opening call, a third variation; 'add': the
second theme's restatement, a codetta episode before the development, a false recapitulation between two
development blocks, the scherzo's da capo after the trio (a refrain), the closing group, a variation. The set's
memory (composer._set_shape) never repeats a feel's (layout, sections)."""
PEAK_AT = {'at': (0.6, 0.66, 0.72, 0.8, 0.88), 'tol': 0.03, 'crisis': (0.48, 0.62), 'step': 2,
           'post': {'recap2': (4, 16), 'coda': (4, 14), 'recap': (6, 12), 'river': (6, 12)},
           'pre': {'t1': (6, 12), 't2': (6, 12), 't2b': (6, 10), 't1b': (6, 10), 'trio': (6, 12), 'episode': (4, 10),
                   'river': (6, 12), 'var': (6, 10), 'refrain': (4, 8), 'close': (3, 6), 'trans': (4, 6),
                   'dev_dialogue': (6, 20), 'dev_fugato': (6, 16)}}
"""Round o19a (o18b: the peak at 72-87 % in 13 of 16 pieces - the statistician's "S10 loudest with the highest note at
76-81 %"): plan['set']['peak_at'] - the climax's centre at that share of the piece (+- 'tol'; the crisis arc's
development climax mapped into 'crisis'): _place_peak grows the blocks on the side that is short ('post' after the
peak, 'pre' before it: (least, most) bars, 'step' bars at a time), then shortens the other side, then (a climax too
early) brings the second theme's return before the retransition (the reversed recapitulation). Never under MIN_LEN's
seconds, the development within DEV_SHARE."""
POST_HARP = {'min': 16}
"""Round o19a (o18b's judges: "the harp episode after the climax deflates the piece", 14 / 17 sentences; two silent_node
rejects - a harp whose only notes were the coda's): no harp after the climax block; a harp left with fewer than 'min'
notes in the whole piece is taken out (no near-silent track)."""
POST_PEAK_V2 = {'recap2': {'tex': {'dev_poly': 1.0, 'cantabile_horn': 0.7, 'tutti_drive': 0.5},
                           'dyn': [(0, 'f'), (0.5, 'mf'), (1, 'mf')]}}
"""Round o19a: the block after the climax keeps its momentum - the motto against the second theme (dev_poly), the horn's
cantabile or the driving tutti, mf (POST_PEAK's lyrical strings with the harp were 'the harp section')."""
CRISIS_V2 = {'grow': 2, 'calm_over': {'tex': {'cantabile_winds': 1.0, 'cantabile_horn': 0.7, 'dev_poly': 0.4},
                                      'dyn': [(0, 'p', 'step'), (0.6, 'mp'), (1, 'mf')], 'sf': False, 'level': 0.45},
             'calm_var': 'chorale', 'coda': 'dissolve', 'coda_plan': ('memory', 'descent', 'echo')}
"""Round o19a (o18b: the crisis arc lost its three slots - "the minor-key climax is too short", "the one tutti comes from
nowhere", the calm return "a fade"): the crisis is the summit - 'grow' bars longer than the return's climax was, the
peak's full treatment (LOUDEST, SUMMIT) - and nothing after it as loud: the return is the first theme TRANSFORMED
('calm_var': augmented as a chorale in the winds, p to mf), the coda the dissolving kind with the motto recalled
('coda_plan'). A mood without the dissolving coda plays the 'return' arc."""
END_V2 = {'min': 5, 'motto': True, 'amen': True, 'decep': {'end': ('f', 'p'), 'end_soft': ('mf', 'pp')}}
"""Round o19a (o18b: no verdict named a plagal or deceptive cadence; 17 lines ask for the motto at the close): the end
block at least 'min' bars; 'motto' - the whole motto at its own speed over the closing bars (then its head), before
the cadence; 'amen' - V7 - I, then IV - I with the melody 4 - 3 on top (the plagal amen in the tune, not the inner
voices); 'decep' - the deceptive chord at the first mark with the melody's tonic held over it, then subito the second
(the predominant and V7 - I grow from there)."""

# ---- round o20: SET_PLAN v3 (SET_PLAN['v3'])
FORM_MERGE = {'deltas': (-3, -2, -1, 0), 'cap': 12,
              'into': {'t1b': ('t1',), 'close': ('t2', 't2b', 'river', 'episode', 'trio', 'var'), 't2b': ('t2',),
                       'trio': ('trio',), 'river': ('river',), 'var': ('var',),
                       'episode': ('t2', 't2b', 'close', 'river', 'var', 'trio')},
              'max': {'t1': 12, 't2': 14, 't2b': 10, 'trio': 12, 'river': 12, 'var': 10, 'episode': 10, 'close': 6},
              'least': 8, 'long': ('t1', 't1b', 't2', 't2b', 'trio', 'var', 'recap', 'recap2', 'river', 'episode',
                                   'refrain', 'dev_dialogue', 'dev_fugato'),
              'more': (('t1', 12), ('t2', 14), ('recap2', 14), ('recap', 14), ('river', 16), ('var', 12),
                       ('trio', 14), ('episode', 12), ('t2b', 12), ('t1b', 10), ('dev_dialogue', None),
                       ('source', 10), ('retrans', 10))}
"""Round o20 (o19a's judges on v2's added sections: "seven sections of four to six bars start and stop", "nine short
sections of 4-6 bars never let a theme establish itself" - the +1 / +2 shapes lost -1.00 a slot): the layout's shape by
MERGING - plan['set']['sections'] (-3 .. 0) blocks folded into the block before them (_merge_rows: a block of a kind
in 'into' whose predecessor is one of its kinds; the shortest first), the merged bars added to it (to its 'max'
internal bars - the writers' tested lengths: MIN_LEN 'more' / PHRASES), and a piece of more than 'cap' sections
merged until it has 'cap' (the slow introduction counted). No section is added: the lengths grow instead - every
block of a 'long' kind at least 'least' song bars (o19a's 4-6 bar themes), and MIN_LEN grows the remaining blocks to
the movement's seconds, with 'more' (the kinds the merged layouts still have: the river, the variations, the trio)
in place of MIN_LEN's. The peak, the retransition, the development, the transition and the ending are never
merged."""
PEAK_AT_V3 = dict(PEAK_AT, at=(0.7, 0.74, 0.78, 0.82, 0.86),
                  post={'recap2': (8, 16), 'coda': (4, 8), 'recap': (8, 12), 'river': (8, 12)},
                  pre={k_: (max(8, lo_), max(8, hi_)) if k_ in ('t1', 't2', 't2b', 't1b', 'trio', 'episode', 'river',
                                                               'var', 'refrain', 'dev_dialogue', 'dev_fugato')
                       else (lo_, hi_) for k_, (lo_, hi_) in PEAK_AT['pre'].items()}, floor=0.66)
"""Round o20 (o19a: the climaxes before 0.7 lost -0.43 a slot, the later ones -0.11): the climax's place drawn at 0.7
or later (PEAK_AT's mechanics, _place_peak), the coda grown to 8 bars at most to move it (FADE_V3), and never under
'floor' (placed again at the first 'at' when it lands under it)."""
FADE_V3 = {'max': 10, 'coda_min': 4, 'kinds': ('coda',)}
"""Round o20 (o19a's judges: "The fades run 19-20 bars (EWFT 106-124, YPEH 90-108, YZGH 80-99, KDFY 94-113)" - "End in
6-10 bars"): the dissolving coda and its last block together at most 'max' song bars - the coda shortened (to
'coda_min' song bars), the movement's least length made up before the climax (MIN_LEN without the 'kinds')."""
TEX_V3 = {'t1': {'drive_strings': 1.0, 'walk_dialogue3': 0.8, 'cantabile_strings': 0.6, 'running_strings': 0.4,
                 'tutti_drive': 0.5},
          't1b': {'motto_bass': 0.8, 'tutti_drive': 1.0, 'motto_brass': 0.7, 'dialogue_brass': 0.7},
          'dev': {'dialogue': 0.6, 'dialogue_brass': 0.8, 'dev_poly': 1.0, 'walk_dialogue3': 0.9, 'walk_poly': 0.9},
          'dev_tech': ('sequence', 'fragment', 'theme', 'stretto', 'combine')}
"""Round o20 (o19a's judges, both codes: "running figure over a held note, tutti statement, remote-key or harp block,
16-bar violins1 / cellos dialogue over bassoon bass, oboe line over pulsing bass, timpani pedal, climax, quiet coda" -
nine packets, four of them v2's): the section TEXTURES drawn per piece with set memory like the gestures -
plan['set']['tex_t1'] (the first theme's), ['tex_t1b'] (its restatement's), ['tex_dev'] (the development dialogue's:
the first dialogue block takes it, a second one the next of the table's order; a 'dev_tech' the dialogue's own
texture is not the technique's bass / fugato), the second theme's colour ('t2col') remembered longer. The walk
textures grow their colour at the block's middle (the texture changes inside the section)."""
POST_HARP_V3 = {'min': 4}
"""Round o20 (o19a's drop, slot 2 seed 135010: v2's POST_HARP emptied a harp of under 16 notes, but its part stayed in
the band - an empty harp track is silent_node; every section where the o19a harps played measured -22 .. -42 dBFS RMS,
the gate's floor is -50): no harp after the climax (as v2), and the harp's track kept on its LEVEL - a harp that still
plays 'min' notes sounds (a pluck peaks far over -40 dBFS); one with fewer, or none, is taken out of the band (its
parts removed, not emptied)."""

# ---- round o22: SET_PLAN v4 (SET_PLAN['v4'])
JOIN_V4 = {'least': 4, 'even': True}
"""Round o22 (o20's judges: "too long / static / loops" 2.06 lines a packet against 0.75, life -0.32 - BPBB: "cut or
merge S4-S8, about 60 bars of thin texture"; a merged block was the predecessor's material over more bars): a merged
block keeps its PARTS (_merge_rows records the blocks it folded in) and plays each from its join on (_split_joins: the
block's bars shared out by the parts' own bars, every part at least 'least' song bars, 'even' internal bars but the
last) - the restatement after the first theme, the closing group or the episode after the second theme, the next
variation, the trio's growing repeat: its own writer, its own dynamics and a NEW texture (build_symphony: the texture
before the join is not drawn again) - inside ONE section of the song (the song's section is the merged block's)."""
FRAG_V4 = {'rise': (1,), 'wave': (2, -1), 'terrace': (0, 2), 'fall': (-1,), 'arch': (1, 1, -1, -1)}
"""Round o22 (o20's judges: "its S2 theme climbs one step per bar, and its S9 climax is the same tutti ladder", the
step sequence into the climax 1.25 lines a packet against 0.50; measured over o20's slots: the first theme's sentence
climbs 6-7 bars in a row in 7 of 16 v3 pieces - the merged 12-bar t1 -, the reharmonised climax 6-10 bars): the
sentence's fragmentation (Writer.sentence: the kernel twice a bar) steps by the piece's draw plan['set']['frag'] - a
step up a bar ('rise': the old ladder), up two and back one, a bar held then two up, falling, up and back - with the
set's memory like the build gestures (genres.SETPLAN_MEMORY_V4: no shape within three pieces)."""


def _merge_rows(genre, rows, n: int, cap: int, parts: bool = False) -> list:
    """FORM_MERGE: `n` merges (and more while the rows are over `cap`) - each the shortest block of a kind in 'into'
    folded into the block before it (that block's bars + its bars, to 'max'). parts (round o22, JOIN_V4): the merged
    row's overrides record the blocks in it - 'parts' ((name, kind, bars, overrides), ...), its own first."""
    M_ = FORM_MERGE
    rows = list(rows)
    k_ = 0
    while k_ < n or len(rows) > cap:
        cand = [i for i in range(1, len(rows)) if rows[i][1] in M_['into'] and
                rows[i - 1][1] in M_['into'][rows[i][1]] and not rows[i][3].get('false') and
                not kind_data(genre, rows[i][1], rows[i][3]).get('peak') and
                not kind_data(genre, rows[i - 1][1], rows[i - 1][3]).get('peak')]
        if not cand:
            break
        i = min(cand, key=lambda j: (rows[j][2], j))
        n0, k0, b0, o0 = rows[i - 1]
        b = b0 + rows[i][2]
        b = min(b, max(b0, M_['max'].get(k0, b0)))
        if parts:
            def own(r):
                return tuple(r[3].get('parts') or ((r[0], r[1], r[2], dict(r[3])),))
            o0 = dict(o0, parts=own(rows[i - 1]) + own(rows[i]))
        rows[i - 1] = (n0, k0, b - (b - b0) % 2, o0)
        rows.pop(i)
        k_ += 1
    return rows


def _split_joins(rows, sc: int) -> list:
    """JOIN_V4: every row with 'parts' as its parts from their joins on - the row's bars shared by the parts' own bars
    (each at least JOIN_V4['least'] song bars: the later parts dropped where the bars do not hold them all); the first
    part keeps the row's name, kind and overrides, every later one is its own row marked 'joined' (the first's name)."""
    lo = max(1, int(math.ceil(JOIN_V4['least'] / sc - _EPS)))
    out = []
    for n, k, b, o in rows:
        ps = o.get('parts')
        o = {x: v for x, v in o.items() if x != 'parts'}
        if not ps:
            out.append((n, k, b, o))
            continue
        ps = list(ps[:max(1, b // lo)])
        if len(ps) < 2:
            out.append((n, k, b, o))
            continue
        tot = float(sum(max(1, p[2]) for p in ps))
        left, bars = b, []
        for j, p in enumerate(ps):
            rest = len(ps) - j - 1
            if not rest:
                bars.append(left)
                break
            x = int(round(b * max(1, p[2]) / tot))
            if JOIN_V4['even'] and x % 2:
                x += 1 if x + 1 <= left - rest * lo else -1
            x = max(lo, min(x, left - rest * lo))
            bars.append(x)
            left -= x
        out.append((n, k, bars[0], o))
        for p, x in zip(ps[1:], bars[1:]):
            out.append((p[0], p[1], x, dict({y: v for y, v in p[3].items() if y != 'parts'}, joined=n)))
    return out


def _fade_v3(genre, rows, coda_kind: str, sc: int) -> list:
    """FADE_V3: a dissolving coda and the last block at most FADE_V3['max'] song bars (the coda shortened)."""
    if CODA_KINDS.get(coda_kind, ('coda',))[0] != 'coda_soft':
        return rows
    F_ = FADE_V3
    rows = list(rows)
    ci = next((i for i, r in enumerate(rows) if r[1] == 'coda'), None)
    ei = next((i for i, r in enumerate(rows) if r[1] == 'end'), None)
    if ci is None:
        return rows
    e = rows[ei][2] if ei is not None else 0
    lo = max(1, int(math.ceil(F_['coda_min'] / sc - _EPS)))
    n, k, b, o = rows[ci]
    b2 = max(lo, min(b, int(F_['max'] / sc + _EPS) - e))
    rows[ci] = (n, k, b2, o)
    return rows


def _shape_rows(rows, delta: int) -> list:
    """FORM_SHAPE: the rows with |delta| sections dropped (delta < 0) or added (delta > 0) - each step the first rule of
    FORM_SHAPE['drop'] / ['add'] that applies."""
    rows = list(rows)
    names = {r[0] for r in rows}

    def nm(base):
        x = base if base not in names else next(f"{base}{j}" for j in range(2, 99) if f"{base}{j}" not in names)
        names.add(x)
        return x
    for _ in range(abs(int(delta))):
        kinds = [r[1] for r in rows]
        done = False
        if delta < 0:
            for how, what in FORM_SHAPE['drop']:
                for i, (n, k, b, o) in enumerate(rows):
                    ok = (how == 'kind' and k == what and not (k == 'intro' and i != 0)) or \
                        (how == 'grow' and k == what and o.get('grow')) or \
                        (how == 'var' and k == 'var' and kinds.count('var') >= 3)
                    if ok:
                        rows.pop(i)
                        done = True
                        break
                if done:
                    break
        else:
            dev = [i for i, r in enumerate(rows) if r[1] in ('dev_dialogue', 'dev_fugato')]
            for what in FORM_SHAPE['add']:
                if what == 't2b' and 't2' in kinds and 't2b' not in kinds:
                    rows.insert(kinds.index('t2') + 1, (nm('t2b'), 't2b', 8, {}))
                elif what == 'episode' and dev and 'episode' not in kinds and dev[0] > 1:
                    rows.insert(dev[0], (nm('codetta'), 'episode', 6, {}))
                elif what == 'false' and len(dev) >= 2 and not any(r[3].get('false') for r in rows):
                    rows.insert(dev[0] + 1, (nm('false'), 'refrain', 4, {'false': True}))
                elif what == 'refrain' and 'trio' in kinds and 'refrain' not in kinds:
                    rows.insert(max(j for j, k in enumerate(kinds) if k == 'trio') + 1, (nm('da_capo'), 'refrain', 6, {}))
                elif what == 'close' and 'close' not in kinds and ('t2' in kinds or 't2b' in kinds):
                    rows.insert(max(j for j, k in enumerate(kinds) if k in ('t2', 't2b')) + 1, (nm('close'), 'close', 4, {}))
                elif what == 'var' and kinds.count('var') >= 2:
                    rows.insert(max(j for j, k in enumerate(kinds) if k == 'var') + 1, (nm('var'), 'var', 8, {}))
                else:
                    continue
                done = True
                break
        if not done:
            break
    return rows


def _fugue_cap(rows, cap: int) -> list:
    """FUGUE v2: every dev_fugato row at most `cap` bars - the surplus (at most cap // 3 bars: no long dialogue) to the
    development's next (else previous) dialogue row, the rest dropped."""
    rows = [list(r) for r in rows]
    for i, r in enumerate(rows):
        if r[1] == 'dev_fugato' and r[2] > cap:
            extra = min(r[2] - cap, cap // 3)
            r[2] = cap
            near = [j for j in (i + 1, i - 1) if 0 <= j < len(rows) and rows[j][1] == 'dev_dialogue']
            if near:
                rows[near[0]][2] += extra
    return [tuple(r) for r in rows]


def _peak_index(genre, rows):
    return next((i for i, r in enumerate(rows) if kind_data(genre, r[1], r[3]).get('peak')), None)


def _peak_pos(genre, rows):
    """The climax block's centre as a share of the rows' bars (None: no climax)."""
    pi = _peak_index(genre, rows)
    if pi is None:
        return None
    return (sum(r[2] for r in rows[:pi]) + rows[pi][2] / 2) / max(1, sum(r[2] for r in rows))


def _place_peak(genre, rows, target: float, bar_s: float | None = None, sc: int = 1, table: dict | None = None) -> list:
    """PEAK_AT: the rows moved toward the climax's centre at `target` of the piece's bars (bar_s: an internal bar's
    seconds - MIN_LEN; sc the feel's scale - DEV_SHARE's song bars; table: PEAK_AT's keys - round o20's PEAK_AT_V3)."""
    P_ = table or PEAK_AT
    D_ = DEV_SHARE
    rows0 = rows = list(rows)
    moved = False

    def fits(rs):
        T = sum(r[2] for r in rs)
        dv = sum(r[2] for r in rs if r[1] in D_['kinds'])
        if MIN_LEN and bar_s and T * bar_s < MIN_LEN['seconds'] - _EPS:
            return False
        return not dv or (dv * sc >= D_['min'] - _EPS and D_['share'] * T - _EPS <= dv <= D_['max'] * T + _EPS)
    for _ in range(48):
        pi = _peak_index(genre, rows)
        if pi is None:
            break
        pos = _peak_pos(genre, rows)
        if abs(pos - target) <= P_['tol']:
            break
        late = pos > target

        def cands(side, grow):
            tab = P_[side]
            out = []
            for i in (range(pi + 1, len(rows)) if side == 'post' else range(0, pi)):
                n, k, b, o = rows[i]
                if k not in tab or o.get('collapse') or o.get('false'):
                    continue
                lo, hi = tab[k]
                if (grow and b + P_['step'] <= hi) or (not grow and b - P_['step'] >= lo):
                    rs = rows[:i] + [(n, k, b + (P_['step'] if grow else -P_['step']), o)] + rows[i + 1:]
                    if fits(rs) or (grow and k not in D_['kinds'] and not fits(rows)):
                        out.append(i)
            return out
        # (a climax too late: more after it, then less before it; too early: more before it, then less after it)
        c = cands('post' if late else 'pre', True)
        if c:
            i = min(c, key=lambda j: (rows[j][2], j))
            n, k, b, o = rows[i]
            rows[i] = (n, k, b + P_['step'], o)
            continue
        c = cands('pre' if late else 'post', False)
        if c:
            i = max(c, key=lambda j: (rows[j][2], -j))
            n, k, b, o = rows[i]
            rows[i] = (n, k, b - P_['step'], o)
            continue
        if not late and not moved and not P_.get('norev'):
            # (the reversed recapitulation: the second theme's return before the retransition)
            r2 = next((i for i in range(pi + 1, len(rows)) if rows[i][1] == 'recap2'), None)
            rt = next((i for i in range(pi - 1, -1, -1) if rows[i][1] == 'retrans'), None)
            if r2 is not None and rt is not None:
                rows.insert(rt, rows.pop(r2))
                moved = True
                continue
        break
    return rows if fits(rows) or not fits(rows0) else rows0


def _approach(key: str, cad: str, t: float, U: float, tonic: int, strokes: bool = False) -> tuple:
    """The last block's approach bar (ENDING_CADENCE / SOFT_ENDINGS plan `cad`): (chart rows, soprano notes) from beat t
    over one bar U, the soprano toward `tonic` (the final note; 'pedal' ends on the third over it)."""
    K = Key(key)
    I = _roman(key, 'i' if K.minorish else 'I')
    V7 = _roman(key, 'V7')
    IV = _roman(key, 'iv' if K.minorish and K.mode != 'dorian' else 'IV')
    pv = pcs_of(key, V7)
    pk = pcs_of(key)
    h = U / 2
    if cad == 'cad64':                  # (I6/4 - V7: the soprano 3 - 2 over the dominant in the bass)
        return [(t, h, I + '/' + chord(V7).root_name), (t + h, h, V7)],             [(t, h, _step(tonic, 2, pk)), (t + h, h, _step(tonic, 1, pv))]
    if cad in ('pre', 'decep'):         # (IV - V7: 1 - 7; 'decep' after the bar's V7 - vi, END_FAMILIES)
        return [(t, h, IV), (t + h, h, V7)], [(t, h, tonic), (t + h, h, _step(tonic, -1, pv))]
    if cad == 'amen':                   # (round o18b: V7 - IV6/4 - I, the plagal amen over the tonic: 2 - 1 - 1)
        return [(t, h, V7), (t + h, h, IV + '/' + chord(I).root_name)], \
            [(t, h, _step(tonic, 1, pv)), (t + h, h, tonic)]
    if cad == 'IV':                     # (plagal: the tonic held over the subdominant)
        return [(t, U, IV)], [(t, U, tonic)]
    if cad == 'pedal':                  # (IV over the tonic pedal: 4 - 3)
        return [(t, U, IV + '/' + chord(I).root_name)], [(t, U, _step(tonic, 3, pk))]
    sop = [(t, U, _step(tonic, 1, pv))] if not strokes else         [(t, h, _step(tonic, 1, pv)), (t + h, h, _step(tonic, -1, pv))]
    return [(t, U, V7)], sop


def _phase_blocks(blk: dict, U: float, log: list) -> list:
    """DEV_WALK 'split': a walked development block cut into its phases (Writer.walk) - each a block of its own (the
    first keeps the name, the next ones 'b', 'c' after it), its texture by the phase's arrangement (WALK 'tex') and its
    level a step over the one before (WALK 'levels'); the composer's log entries follow their phase."""
    out = []
    lv = WALK['levels']
    for j, (a, nb, arr, key) in enumerate(blk['phases']):
        z = a + nb * U
        nm = blk['name'] if j == 0 else f"{blk['name']}{'abcdefgh'[j]}"
        o = dict(blk['over'], tex=dict(WALK['tex'][arr]),
                 dyn=[(0, lv[min(j, len(lv) - 2)], 'step'), (1, lv[min(j + 1, len(lv) - 1)])])
        sub = {k_: v for k_, v in blk.items() if k_ != 'phases'}
        sub.update(name=nm, start=a, bars=nb, key=key, over=o, phase=arr,
                   theme=[(x, min(d, z - x), p) for x, d, p in blk['theme'] if a - _EPS <= x < z - _EPS],
                   answer=[(x, min(d, z - x), p) for x, d, p in blk['answer'] if a - _EPS <= x < z - _EPS],
                   chart=[(x, min(d, z - x), s_) for x, d, s_ in blk['chart'] if a - _EPS <= x < z - _EPS],
                   route=[r for r in blk['route'] if r['phase'] == j])
        for e in log:
            if e['block'] == blk['name'] and a - _EPS <= e['beat'] < z - _EPS:
                e['block'] = nm
        out.append(sub)
    return out


def _next_area(rows, name: str, home: str, minor: bool, draws: dict, j_dev: int):
    """DEV_WALK v3: (key, kind) of the block after the development block `name` - the key a prepared modulation
    goes to: the next dialogue's (its path's next key), the fugato's, the false recapitulation's, home before the
    retransition; (None, kind) where the next block's key is not the development's to prepare."""
    i = next(j for j, r in enumerate(rows) if r[0] == name)
    if i + 1 >= len(rows):
        return None, None
    _, kind, _, over = rows[i + 1]
    if kind == 'dev_dialogue':
        ks = dev_keys(home, over.get('path') or draws['dev_path'])
        return ks[(j_dev + 1) % len(ks)], kind
    if kind == 'dev_fugato':
        return _transpose_key(home, 5 if minor else 9, 'minor'), kind
    if kind == 'refrain' and over.get('false'):
        return (_transpose_key(home, 8, 'major') if minor else _transpose_key(home, 5)), kind
    if kind == 'retrans':
        return home, kind
    return None, kind


def _form_seed(draws: dict, key: str, seed):
    """The seed of the piece's bar plan: the composition seed - or (SET_PLAN v4, round o22) the slot's
    draws['form_seed'] with its key, so the set planner sees the bars the piece plays (bar_plan) and every candidate
    plays them."""
    if SET_PLAN and SET_PLAN.get('v4') and isinstance(draws.get('form_seed'), int):
        return f"f{int(draws['form_seed'])}:{key}"
    return seed


def _layout_of(genre, F: dict, draws: dict, seed) -> str:
    """The piece's layout: the feel's, the set's draw, or (a draw the feel does not have) one of the feel's own."""
    layout = F.get('layout') or draws['layout']
    if F.get('layouts') and layout not in F['layouts']:  # (round o4: a feel's own forms - the scherzo and trio, the
        w_ = genre.plan['set'].get('layout') or {}       # river's variations; the set's draw where the feel has it)
        layout = _pick(random.Random(f"symphony:{seed}:layout"), {x: w_.get(x, 1.0) for x in F['layouts']})
    return layout


def _coda_of(M: dict, draws: dict, seed) -> str:
    """The coda's kind: the set's draw where the mood has it, else the mood's own by `seed`."""
    coda_kind = _pick(random.Random(f"symphony:{seed}:coda"), M.get('coda', {'triumph': 1.0}))
    if M.get('coda', {}).get(draws.get('coda'), 0) > 0:      # (the set's coda draw, where the mood has it)
        coda_kind = draws['coda']
    return coda_kind


def _place_v3(genre, rows, draws: dict, F: dict, U: float, tempo, coda_kind: str) -> list:
    """SET_PLAN v3's placement (round o20): the climax at 0.7 or later (PEAK_AT_V3), the development's share, the
    dissolving coda's fade capped (FADE_V3), the movement's least length - twice, the floor checked."""
    sc3 = F.get('scale', 1)
    bs3 = U * sc3 * 60.0 / tempo if tempo else None
    soft3 = CODA_KINDS.get(coda_kind, ('coda',))[0] == 'coda_soft'
    T3 = dict(PEAK_AT_V3, post={k_: v_ for k_, v_ in PEAK_AT_V3['post'].items()
                                if not (soft3 and k_ in FADE_V3['kinds'])})
    tg = float(draws['peak_at']) if draws.get('peak_at') in PEAK_AT_V3['at'] else PEAK_AT_V3['at'][0]
    floor3 = PEAK_AT_V3['floor']
    sh = draws.get('shape') if MACRO else None
    if isinstance(sh, dict) and sh.get('at') is not None:     # (round o24: the macro shape's climax centre)
        tg, floor3 = float(sh['at']), MACRO['floor']
        T3 = dict(T3, post=dict(T3['post'], **{k_: v_ for k_, v_ in MACRO['post'].get(sh.get('arc'), {}).items()
                                               if not (soft3 and k_ in FADE_V3['kinds'])}))
        if MACRO.get('v2') and sh.get('arc') in MACRO['v2']['arcs_move']:
            T3['norev'] = True                  # (round o24b: the second theme's return stays after the climax)
    for _ in range(2):
        rows = _place_peak(genre, rows, tg, bs3, sc3, T3)
        if DEV_SHARE:
            rows = _grow_dev(rows, sc3, draws.get('dev_path'))
        rows = _fade_v3(genre, rows, coda_kind, sc3)
        if MIN_LEN and bs3:
            rows = _grow_len(rows, bs3, sc3, skip=FADE_V3['kinds'] if soft3 else (), more=FORM_MERGE['more'])
        pp_ = _peak_pos(genre, rows)
        if pp_ is None or pp_ >= floor3 - _EPS:
            break
        tg = max(tg, PEAK_AT_V3['at'][0] if floor3 >= PEAK_AT_V3['floor'] else floor3 + 0.06)
    return rows


def bar_plan(genre, slot: dict) -> list:
    """SET_PLAN v4 (round o22): the song bars of each section a set slot's piece plays - the layout's rows after the
    merges, the climax's place, the growth and the joins (one section per merged block; the last block counted with
    the one before, as the packets print it) - by the slot alone (its draws['form_seed']); material() plays them."""
    F = genre.feels[slot['feel']]
    M = genre.moods[slot['mood']]
    fs = _form_seed(slot, slot['key'], 0)
    layout = _layout_of(genre, F, slot, fs)
    U = 4.0 if F['family'] == 'duple' else 3.0
    sc = F.get('scale', 1)
    tempo = slot.get('tempo')
    rows = form_rows(genre, layout, slot, F, fs, bar_s=U * sc * 60.0 / tempo if tempo else None)
    rows = _place_v3(genre, rows, slot, F, U, tempo, _coda_of(M, slot, fs))
    rows = _split_joins(rows, sc)
    out = []
    for n, k, b, o in rows:
        if (o.get('joined') or n == 'end') and out:
            out[-1] += b * sc
        else:
            out.append(b * sc)
    return out


def material(genre, key: str, feel: str, mood: str, seed: int, draws: dict, tempo: float | None = None) -> dict:
    """The piece's material (the module docstring): {'layout', 'family', 'U', 'scale', 'motto', 'blocks': [{'name',
    'kind', 'start', 'bars', 'key', 'chart', 'theme' (notes), 'answer', 'voices', 'pedal', 'peak', 'sf', 'over'}],
    'log', 'second', 'coda'} in INTERNAL beats (x 'scale' for the song: the scherzo's compound bar = two 3/4 bars)."""
    F = genre.feels[feel]
    fam = F['family']
    rng = random.Random(f"symphony:{genre.name}:{seed}:material")
    M = genre.moods[mood]
    motto = {'family': fam, 'kind': draws['motto'][fam], 'land': draws['land'], 'member': draws['member']}
    if motto['kind'] not in CELLS[fam]:
        raise ComposeError(f"symphony: motto cell {motto['kind']!r} not in the {fam} cells")
    fs = _form_seed(draws, key, seed)      # (round o22: the bar plan a function of the slot - SET_PLAN v4)
    layout = _layout_of(genre, F, draws, fs)
    w = Writer(key, fam, motto, dict(draws, seed=seed), rng, scale=int(F.get('scale', 1)))
    U = w.U
    home = key
    minor = w.minor
    rel = draws['key2'] if minor or draws['key2'] != 'relative' else 'dominant'
    second = _second_key(home, rel)
    coda_kind = _coda_of(M, draws, fs)
    climax = None                                            # (no 'climax' draw: the kind's own brass tutti)
    if 'climax' in draws:
        cw = M.get('climax', CLIMAX_DEFAULT)
        climax = draws['climax'] if cw.get(draws['climax'], 0) > 0 else \
            _pick(random.Random(f"symphony:{seed}:climax"), cw)
    shape_ = draws.get('shape') if MACRO and isinstance(draws.get('shape'), dict) else None
    if shape_ and shape_.get('climax') in CLIMAXES:          # (round o24: the macro shape's climax type)
        climax = shape_['climax']
    I_h = 'i' if minor else 'I'
    # (round o3: the piece's material draws - the development's technique, the climax's material, the source's and
    # the second theme's colours, the ending; a draw the plan does not have keeps the o2 piece)
    apex = draws.get('apex') if draws.get('apex') in APEX else 'restate'
    if climax == 'quiet' and APEX[apex]:          # (the quiet climax keeps its hush: the first theme reharmonised -
        apex = 'reharm'                           # round o8, o7's judges: "the climax without the motto" - not the
        #                                           second theme, its motto head under it)
    if F.get('scale', 1) == 2:                    # (round o7: no augmentation in the fast 3/4 - APEX_SCHERZO)
        apex = APEX_SCHERZO.get(apex, apex)
    # (round o6 - o5's judges, one plan in both codes: "a minor piece turns to the parallel major in the climax,
    # then a soft coda": the climax's key drawn per set - CLX_MODES; no draw: o5's, the tonic major after a
    # reharmonised / second-theme climax of a minor piece)
    cmode = draws.get('clx_mode')
    if cmode not in CLX_MODES:
        cmode = 'parallel' if apex in ('reharm', 'second') and minor else 'home'
    clx_key, finale, last_key = clx_keys(home, cmode)
    past_peak = False
    tech, theme2, theme1 = None, None, None
    river1 = False                          # (round o9: theme1 is the river's tune - its episode / climax take it)
    blocks, t = [], 0.0
    # (round o11: the movement's least length - MIN_LEN - by the seconds of an internal bar at the piece's tempo)
    rows = form_rows(genre, layout, draws, F, fs,
                     bar_s=U * F.get('scale', 1) * 60.0 / tempo if tempo else None)
    crisis_key = None
    if SET_PLAN and SET_PLAN.get('arc') and draws.get('arc') == 'crisis' and climax != 'quiet' and apex != 'restate':
        v2_ = SET_PLAN.get('v2')
        if not v2_ or M.get('coda', {}).get('dissolve', 0) > 0:   # (round o19a: a quiet return ends quietly)
            rows, ok_ = _crisis_rows(genre, rows)      # (round o18b: the climax before a quiet return - ARC_CRISIS)
            if ok_:
                crisis_key = _transpose_key(home, 0, 'minor') if Key(home).mode == 'major' else home
                if v2_:                                # (round o19a: the coda dissolves - CRISIS_V2)
                    coda_kind = CRISIS_V2['coda']
    if SET_PLAN and SET_PLAN.get('v3'):
        # (round o20: the climax at 0.7 or later, the dissolving coda's fade capped - PEAK_AT_V3, FADE_V3)
        rows = _place_v3(genre, rows, draws, F, U, tempo, coda_kind)
        if SET_PLAN.get('v4'):                 # (round o22: the merged blocks' parts from their joins - JOIN_V4)
            rows = _split_joins(rows, F.get('scale', 1))
        if shape_:                             # (round o24: the twin peak, the second summit, the surprise, the cut)
            rows = _macro_marks(genre, rows, shape_)
    elif SET_PLAN and SET_PLAN.get('v2') and draws.get('peak_at') is not None:
        # (round o19a: the climax's place drawn per piece - PEAK_AT; the crisis's in the development, earlier)
        tg = float(draws['peak_at'])
        if crisis_key is not None:
            lo_, hi_ = PEAK_AT['crisis']
            a0_, a1_ = PEAK_AT['at'][0], PEAK_AT['at'][-1]
            tg = lo_ + (hi_ - lo_) * (tg - a0_) / max(_EPS, a1_ - a0_)
        bs_ = U * F.get('scale', 1) * 60.0 / tempo if tempo else None
        rows = _place_peak(genre, rows, tg, bs_, F.get('scale', 1))
        if DEV_SHARE:
            rows = _grow_dev(rows, F.get('scale', 1), draws.get('dev_path'))
            rows = _place_peak(genre, rows, tg, bs_, F.get('scale', 1))
    if FUGUE and FUGUE.get('v2') and feel in FUGUE['v2']['cap']:
        rows = _fugue_cap(rows, FUGUE['v2']['cap'][feel])     # (round o21: the fast feels' fugato capped)
    dev_all =sum(r[2] for r in rows if r[1] == 'dev_dialogue')       # (DEV_WALK: the walk's place in the development)
    dev_done = 0
    # (round o4: the variations' techniques drawn per piece, none twice; the one elided cadence)
    var_order = sorted(VARIATIONS, key=lambda x: random.Random(f"symphony:{seed}:var:{x}").random())
    elide = None
    if draws.get('elide'):
        cand = [r[0] for r, nx in zip(rows, rows[1:]) if r[1] in ELIDE and nx[1] not in ('end', 'end_soft') and
                r[2] >= 6]
        elide = cand[random.Random(f"symphony:{seed}:elide").randrange(len(cand))] if cand else None
    rows_tex = {r[0]: r[3] for r in rows}         # (the layout's own overrides - round o20's TEX_V3 keeps them)
    for name, kind, bars, over in rows:
        if kind == 'var':
            how = over.get('var') or var_order[sum(1 for b in blocks if b['kind'] == 'var') % len(var_order)]
            over = {**VARIATIONS[how], **over, 'var': how}
        elif kind == 'refrain' and over.get('false'):     # (the false recapitulation: quiet, in a far key)
            over = dict(over, tex={'cantabile_strings': 1.0, 'dialogue': 0.6}, dyn=[(0, 'p', 'step'), (1, 'mp')])
        if kind == 'intro':
            kind = INTRO_KINDS[draws['intro']]
            if kind == 'intro' and draws.get('colour') in OPENING_COLOURS:     # (the motto's first colour)
                over = dict(over, tex=dict(OPENING_COLOURS[draws['colour']]))
        elif kind in ('coda', 'end'):
            kind = CODA_KINDS[coda_kind][0 if kind == 'coda' else 1]
            if kind == 'coda_soft' and blocks and blocks[-1]['peak'] and 'dyn' not in over:
                over = dict(over, dyn=list(CODA_FALL))      # (round o8: the ff climax dies away into it)
                if 'tex' not in over:                       # (round o9: the descent sung, POST_PEAK)
                    over = dict(over, **POST_PEAK['coda_soft'])
            if SET_PLAN and SET_PLAN.get('endings'):   # (round o18b: the ending families - END_FAMILIES / END_TEX)
                E_ = END_TEX.get(draws.get('ending'))
                if E_ and (kind == 'end' or draws.get('ending') == 'line'):
                    over = dict(over, **E_)
            elif kind == 'end' and draws.get('ending') in ENDINGS:          # (the last bars' gesture)
                over = dict(over, **ENDINGS[draws['ending']])
        elif kind == 'recap2' and blocks and blocks[-1]['peak'] and 'tex' not in over:
            over = dict(over, **(POST_PEAK_V2 if SET_PLAN and SET_PLAN.get('v2') else POST_PEAK)['recap2'])
            #                                           (round o9: the descent after the climax, POST_PEAK)
        elif kind == 'retrans' and SET_PLAN and SET_PLAN.get('builds'):   # (round o18b: the build's gesture)
            if not over.get('collapse'):
                over = dict(over, **GESTURES[draws.get('build') if draws.get('build') in GESTURES else 'swell']['over'])
        elif kind == 'retrans' and draws.get('build') in BUILDS:          # (the set's build type)
            over = dict(over, **BUILDS[draws['build']])
        elif kind == 't2' and draws.get('t2col') in T2_COLOURS:           # (the second theme's colour)
            over = dict(over, **T2_COLOURS[draws['t2col']])
        elif kind == 'dev_dialogue':                                       # (the development's technique)
            tech = over.get('tech') or (DEV_NEXT[tech] if tech else draws.get('dev_tech')) or 'sequence'
            if tech in DEV_TECH:
                over = dict(over, tech=tech, **({} if tech in ('sequence', 'fragment') and 'tex' in over
                                                else DEV_TECH[tech]))
        if SET_PLAN and SET_PLAN.get('v3') and 'tex' not in dict(rows_tex.get(name) or {}):
            # (round o20: the section textures drawn per piece with the set's memory - TEX_V3)
            if kind in ('t1', 't1b') and draws.get('tex_' + kind) in TEX_V3[kind]:
                over = dict(over, tex={draws['tex_' + kind]: 1.0})
            elif kind == 'dev_dialogue' and over.get('tech') in TEX_V3['dev_tech'] and \
                    draws.get('tex_dev') in TEX_V3['dev']:
                order = list(TEX_V3['dev'])
                j3 = sum(1 for b in blocks if b['kind'] == 'dev_dialogue')
                over = dict(over, tex={order[(order.index(draws['tex_dev']) + j3) % len(order)]: 1.0})
        if kind == 'source' and draws.get('src') in SOURCES:
            over = dict(over, **SOURCES[draws['src']])
        if kind_data(genre, kind, over).get('peak') and climax:          # (the climax's type)
            over = dict(over, **CLIMAXES[climax])
            if shape_ and MACRO.get('v2') and not APEX[apex].get('tex') and climax in MACRO['v2']['climax_tex']:
                over = dict(over, **MACRO['v2']['climax_tex'][climax])     # (round o24b: SHAPE2's climax types)
        if kind_data(genre, kind, over).get('peak') and APEX[apex]:      # (the climax's material: its texture)
            over = dict(over, **APEX[apex])
        if shape_ and over.get('sh_dyn'):       # (round o24: the macro shape's dynamics, over the kind's own)
            over = dict(over, dyn=list(over['sh_dyn']))
        if shape_ and over.get('sh_tex'):       # (round o24b: the cut's texture over the ending family's)
            over = dict(over, tex=dict(over['sh_tex']))
        K = kind_data(genre, kind, over)
        blk = {'name': name, 'kind': kind, 'start': t, 'bars': bars, 'key': home, 'chart': [], 'theme': [],
               'answer': [], 'voices': {}, 'pedal': [], 'peak': bool(K.get('peak')), 'sf': bool(K.get('sf')),
               'over': over}
        if over.get('joined'):                # (round o22: a merged block's later part - one section with the block
            blk['joined'] = over['joined']    # it joins, JOIN_V4)
        L = bars * U
        Ih, Vh = _roman(home, I_h), _roman(home, 'V')
        pcs = pcs_of(home)
        if kind == 'intro':                   # the call: the motto twice, boldly, each landing held (fermata)
            a = w.anchor(home, Ih)
            a2 = min((_step(a, -1, pcs), _step(a, 4, pcs)), key=lambda q: abs(q - w.centre))
            # (round o6: a call of 3 / 6 bars too - PHRASES 'intro': a statement per two bars, the third a step
            # over the first; the first and the last landing held)
            at = list(range(0, bars, 2))
            ns_, ch_ = [], []
            for j, b0 in enumerate(at):
                z = t + at[j + 1] * U - 0.75 if j + 1 < len(at) else t + L - 0.5
                ns_.append(w.state(name, t + b0 * U, (a, a2, _step(a, 2, pcs))[j % 3], pcs, fill=z))
                zc = t + at[j + 1] * U if j + 1 < len(at) else t + L
                ch_.append((t + b0 * U, zc - t - b0 * U,
                            Vh if j % 3 == 1 and a2 != _step(a, -1, pcs) else Ih))
            ns_ = [[(x, min(d, t + L - x), p) for x, d, p in y if x < t + L - 0.5 - _EPS] or y[:1] for y in ns_]
            blk['theme'] = [n for x in ns_ for n in x]
            blk['chart'] = [(x, d, s_) for x, d, s_ in ch_ if d > _EPS]
            blk['theme'] = fit_line(blk['theme'], blk['chart'], home)
            blk['fermatas'] = [ns_[0][-1][0], ns_[-1][-1][0]] if len(ns_) > 1 else [ns_[0][-1][0]]
        elif kind == 'slow':                  # the slow introduction: the motto's head augmented, quiet, rising a
            a = w.anchor(home, Ih, w.centre - 7)          # step over I - iv - VI|ii - V, held on V (fermata)
            iv = _roman(home, 'iv' if minor else 'IV')
            vi = _roman(home, 'VI' if minor else 'ii')
            seq = [Ih, iv, vi, Vh]
            blk['chart'] = [(t + i * U, U, seq[min(i, 3)] if i < bars - 1 else Vh) for i in range(bars)]
            n1 = w.state(name, t, a, pcs, ('head', 'augment'), fill=t + 2 * U - 0.5)
            n2 = w.state(name, t + 2 * U, _step(a, 1, pcs), pcs, ('head', 'augment'), fill=t + L - 0.25)
            blk['theme'] = fit_line([n for n in n1 + n2 if n[0] < t + L - _EPS], blk['chart'], home)
        elif kind == 'mist':                  # the motto in the low strings under hushed tremolo
            a = w.anchor(home, Ih, 50)
            if OPENING and bars > 4:
                # (round o10 - o9's judges, ECER: "bar 9 silent": a long mist states the motto every two bars, a step
                # higher each time, I and V in turn under it - the block never empties)
                at = [t + U + 2 * U * j for j in range(max(1, (bars - 1) // 2))]
                ns_ = []
                for j, x in enumerate(at):
                    z = at[j + 1] - 0.5 if j + 1 < len(at) else t + L - 0.5
                    ns_ += [n for n in w.state(name, x, _step(a, j, pcs), pcs, () if j == 0 else ('head',), fn='bass',
                                               fill=z) if n[0] < z - _EPS]
                blk['chart'] = [(t + i * U, U, Vh if i == bars - 1 or (i >= 2 and (i // 2) % 2 == 1) else Ih)
                                for i in range(bars)]
                blk['theme'] = fit_line(ns_, blk['chart'], home)
            else:
                n1 = w.state(name, t + U, a, pcs, fn='bass', fill=t + 2.5 * U)
                n2 = w.state(name, t + 2.5 * U, _step(a, 1, pcs), pcs, ('head',), fn='bass')
                blk['chart'] = [r for r in [(t, min(L, 2 * U), Ih), (t + 2 * U, L - 2 * U, Vh)] if r[1] > _EPS]
                blk['theme'] = fit_line([(x, min(d, t + L - x), q) for x, d, q in n1 + n2 if x < t + L - _EPS],
                                        blk['chart'], home)
        elif kind == 'source':                # the figuration alone, the motto's head from afar at the end
            # (round o5 - o4's statistician: "the 8-bar running-eighths ostinato with the oboe entering at bar 7"
            # opened every 6/8 piece: the source's harmonic frame and the head's entries drawn - SOURCE_PLANS)
            sc_ = draws.get('src_chart') if draws.get('src_chart') in SOURCE_CHARTS else 'plagal'
            seq = [_roman(home, 'IV' if r_ == 'iv' and Key(home).mode == 'dorian' else r_)   # (dorian's IV)
                   for r_ in SOURCE_CHARTS[sc_]['minor' if minor else 'major']]
            blk['chart'] = [(t + i * U, U, seq[i % 4] if i < bars - 1 else Vh) for i in range(bars)]
            a = w.anchor(home, Vh, 64)
            pv_ = pcs_of(home, Vh)
            entry = draws.get('src_entry') if draws.get('src_entry') in SOURCE_ENTRIES and bars >= 6 else 'late'
            if entry == 'early':              # (the head at bar 3, then again at the end)
                blk['theme'] = [n for n in w.state(name, t + 2 * U, w.anchor(home, Ih, 64), pcs, ('head',),
                                                   fill=t + 4 * U - 0.5) if n[0] < t + 4 * U - _EPS] + \
                    w.state(name, t + L - 2 * U, a, pv_, ('head',), fill=t + L - 0.5)
            elif entry == 'answer':           # (the head, then its inversion a step over it, two bars apart)
                blk['theme'] = [n for n in w.state(name, t + L - 4 * U, a, pv_, ('head',), fill=t + L - 2.5 * U)
                                if n[0] < t + L - 2 * U - _EPS] + \
                    w.state(name, t + L - 2 * U, _step(a, 2, pv_), pv_, ('head', 'invert'), fill=t + L - 0.5)
            else:
                blk['theme'] = w.state(name, t + L - 2 * U, a, pv_, ('head',), fill=t + L - 0.5)
            blk['theme'] = fit_line(blk['theme'], blk['chart'], home)
            blk['entry'] = entry
            blk['pedal'] = [(t, L - U, _near({Key(home).tonic}, 79))]          # (a high pedal: the murmur's)
        elif kind == 'solo':                  # a solo voice: the motto, then its head a step higher, over a pedal
            a = w.anchor(home, Ih, w.centre - 3)
            n1 = w.state(name, t, a, pcs, fill=t + 2 * U - 0.5)
            n2 = w.state(name, t + 2 * U, _step(a, 1, pcs_of(home, Vh)), pcs_of(home, Vh), ('head',),
                         fill=t + L - 0.5)
            blk['chart'] = [r for r in [(t, min(L, 2 * U), Ih), (t + 2 * U, L - 2 * U, Vh)] if r[1] > _EPS]
            blk['theme'] = fit_line([n for n in n1 + n2 if n[0] < t + L - _EPS], blk['chart'], home)
            blk['pedal'] = [(t, L, _near({Key(home).tonic}, 40, 36, 47))]
        elif over.get('calm') and SET_PLAN and SET_PLAN.get('v2') and theme1:
            # (round o19a: the return after the crisis transformed - the first theme augmented as a chorale, quiet)
            mel, ch, cnt, k = w.variation(name, home, t, bars, CRISIS_V2['calm_var'], theme1)
            blk['theme'], blk['chart'], blk['answer'], blk['key'] = mel, ch, cnt, k
            if mel:
                w.log.append({'block': name, 'beat': t, 'tf': 'theme', 'fn': 'melody', 'end': t + bars * w.U})
        elif (kind == 'recap' or (kind == 'river' and blk['peak'])) and apex != 'restate' and not over.get('calm'):
            mel, ch, ans, k = w.apex(name, apex, home, t, bars, theme2, key=crisis_key if over.get('crisis') else
                                     clx_key, theme1=theme1, river=river1)
            blk['theme'], blk['chart'], blk['answer'], blk['key'] = mel, ch, ans, k
        elif kind == 'recap2' and apex in ('combine', 'second') and crisis_key is None:     # (the second theme was the climax: the first
            # theme comes back quiet - round o4: recomposed, its answer inverted over the submediant, the second
            # theme under it)
            kr = finale if past_peak else home
            mel, ch = w.sentence(name, kr, t, bars, end='PAC', centre=w.centre - 2, vary=('reharm', 'invert'))
            blk['theme'], blk['chart'], blk['key'] = mel, ch, kr
            if theme2:
                blk['answer'] = w.theme_under(theme2, kr, t, bars, ch)
        elif kind == 'episode' and river1 and EPISODE_FROM.get('river'):
            # (round o9 - o8's judges, XBGS: "five short episodes, new tunes": the river's episode is its tune
            # varied - VARIATIONS[EPISODE_FROM['river']] in the second key)
            mel, ch, cnt, k = w.variation(name, second, t, bars, EPISODE_FROM['river'], theme1)
            blk['theme'], blk['chart'], blk['answer'], blk['key'] = mel, ch, cnt, k
            if mel:                           # (the river tune grows from the motto - DERIVE: its variation states it)
                w.log.append({'block': name, 'beat': t, 'tf': 'theme', 'fn': 'melody', 'end': t + bars * w.U})
        elif kind in ('t1', 't1b', 'recap', 'episode', 'close'):
            k = second if kind in ('episode', 'close') else home
            blk['key'] = k
            nxt = [r[1] for r in rows]
            end = 'HC' if kind == 't1' and bars >= 8 and 't1b' in nxt else 'PAC'
            ans = None
            if kind == 't1b':                 # one change against the first statement (plant, recur, pay off)
                ans = 'step_up' if draws['answer'] == 'dominant' else 'dominant'
            elif kind == 'close':
                ans = 'step_down'
            vary = RECAP_VARY if kind == 'recap' else ()
            if kind == 't1b' and (random.Random(f"symphony:{seed}:t1b").random() < T1B_DOT or w.scale == 2):
                vary = ('dot',)               # (round o4: the restatement in another rhythm - "leads with few cells")
                if w.scale == 2 and DANCE_VARY.get('return'):
                    vary = DANCE_VARY['return']   # (round o10: the scherzo's restatement on its other cells too)
            mel, ch = w.sentence(name, k, t, bars, end=end, answer=ans,
                                 centre=w.centre + (3 if kind == 'recap' else 0), payoff=kind == 'recap', vary=vary)
            blk['theme'], blk['chart'] = mel, ch
            if kind == 'recap' and theme2:      # (round o4: the restated climax with the second theme under it)
                blk['answer'] = w.theme_under(theme2, k, t, bars, ch)
            if kind == 't1' and theme1 is None:  # (the theme the variations vary)
                theme1 = (k, [(a - t, d, p) for a, d, p in mel], bars)
        elif kind in ('t2', 't2b', 'recap2', 'river'):
            k = (finale if past_peak else home) if kind == 'recap2' else home if kind == 'river' else second
            blk['key'] = k
            mel, ch = w.cantilena(name, k, t, bars, centre=w.centre + (2 if kind == 't2b' else 0),
                                  theme='R' if kind == 'river' else 'B', vary=kind == 'recap2')
            if kind == 't2b' or over.get('grow'):     # the restatement grows: its second half an octave up
                mel = [(a, d, p + 12 if a >= t + L / 2 and p + 12 <= 88 else p) for a, d, p in mel]
            if kind == 'river' and theme1 is None:
                theme1 = (k, [(a - t, d, p) for a, d, p in mel], bars)
                river1 = True
            blk['theme'], blk['chart'] = mel, ch
            if kind == 'recap2':                      # (round o4: the second theme returns changed - its bars
                blk['answer'] = w.motto_counter(name, k, ch, t, bars, below=9)    # redrawn, the motto against it)
                if DEV_WALK and DEV_WALK.get('recall') and w.dev_line():
                    # (round o16: the development's counter-line against it - the masterpiece report's "a new
                    # counter-line from the development")
                    blk['answer'] = w.recall(name, k, ch, t, bars, below=9)
            if theme2 is None and kind in ('t2', 'river'):       # (the second theme, for the development's and
                theme2 = (k, [(a - t, d, p) for a, d, p in mel])  # the climax's combinations)
        elif kind == 'trans':                 # the motto's head in a sequence toward the second key's V
            blk['key'] = second
            V2 = _roman(second, 'V')
            m2 = Key(second).minorish
            p2 = pcs_of(second)
            mel, ch = [], []
            a0 = w.anchor(second, _roman(second, 'iv' if m2 else 'ii'), w.centre - 3)
            for i in range(bars):             # (the kernel per half bar rising a step per bar - a sequence, its
                tt = t + i * U                # chords drawn under it; the last two bars diminished over V: faster)
                if i < bars - 2:
                    for j in range(2):
                        if MOTTO_RATION.get('frag') and j == 1 and mel:     # (round o10: the answer free)
                            mel += w.free(mel[-1][2], _step(a0, i + 1, p2), tt + U / 2, U / 2, p2)
                            continue
                        a_, tf_ = _seq_pair(motto, _step(a0, i, p2), j, p2)
                        mel += w.state(name, tt + j * U / 2, a_, p2, ('kernel',) + tf_)
                else:
                    ch.append((tt, U, V2))
                    base = _near(_cpcs(V2), w.centre + 2)
                    for j in range(4):            # (rising by step: the run-up to the second theme)
                        pv2 = pcs_of(second, V2)
                        q_ = _step(base, j + 2 * (i - bars + 2), pv2)
                        if MOTTO_RATION.get('frag') and j % 2 == 1 and mel:
                            mel += w.free(mel[-1][2], _step(q_, 1, pv2), tt + j * U / 4, U / 4, pv2)
                            continue
                        mel += w.state(name, tt + j * U / 4, q_, pv2, ('kernel', 'diminish'))
            head = harmonize([n for n in mel if n[0] < t + (bars - 2) * U - _EPS], second, t, bars - 2, U,
                             {0: 'iv' if m2 else 'ii'}) if bars > 2 else []
            ch = head + ch
            blk['theme'], blk['chart'] = fit_line(mel, ch, second), ch
            blk['pedal'] = [(t + (bars - 2) * U, 2 * U, _near({chord(V2).root % 12}, 40, 36, 47))]
        elif kind == 'dev_dialogue':
            keys = dev_keys(home, over.get('path') or draws['dev_path'])    # (round o8: the related keys)
            if DEV_WALK and DEV_WALK.get('v3'):     # (round o18a: one key per block, the processes by time)
                j_dev = sum(1 for b_ in blocks if b_['kind'] == 'dev_dialogue')
                w.bar_s = U * F.get('scale', 1) * 60.0 / tempo if tempo else None
                call, answer, ch, blk['phases'], blk['route'], blk['over'], ents = w.walk3(
                    name, keys, t, bars, home, theme2, (dev_done / max(1, dev_all), (dev_done + bars) / max(1, dev_all)),
                    over, _next_area(rows, name, home, minor, draws, j_dev), j_dev)
                if ents:
                    blk['entries'] = ents
            elif DEV_WALK and DEV_WALK.get('v2'):     # (round o17: one block of worked processes - Writer.walk2)
                call, answer, ch, blk['phases'], blk['route'], blk['over'] = w.walk2(
                    name, keys, t, bars, home, theme2, (dev_done / max(1, dev_all), (dev_done + bars) / max(1, dev_all)),
                    over)
            elif DEV_WALK:                      # (round o16: the development as a planned walk - Writer.walk)
                call, answer, ch, blk['phases'], blk['route'] = w.walk(
                    name, keys, t, bars, home, theme2, (dev_done / max(1, dev_all), (dev_done + bars) / max(1, dev_all)))
            else:
                call, answer, ch = w.develop(name, keys, t, bars, over.get('tech') or 'sequence', home, theme2,
                                             theme1=theme1)
            dev_done += bars
            blk['theme'], blk['answer'], blk['chart'], blk['key'] = call, answer, ch, keys[0]
            if DEV_WALK and DEV_WALK.get('v3'):
                blk['key'] = blk['route'][0]['key']     # (v3: the block's own key)
        elif kind == 'dev_fugato' and FUGUE:      # (round o19b: an exposition, episodes, the final entry - fugue2)
            rn = _pick(random.Random(f"symphony:{seed}:fugue_key:{name}"), FUGUE['keys']['minor' if minor else 'major'])
            k = fugue_key(home, rn)
            V2_ = FUGUE.get('v2')
            fg = w.fugue2(name, k, t, bars, home, seed=seed,
                          beat_s=60.0 * F.get('scale', 1) / tempo if tempo else None,
                          **({'theme1': theme1, 'dance': feel in V2_['cap']} if V2_ else {}))
            blk['voices'], blk['chart'], blk['key'] = fg['voices'], fg['chart'], k
            blk['fugue'] = {x: fg[x] for x in ('leads', 'bass', 'form', 'issues', 'n_issues', 'keys')}
            blk['over'] = dict(blk['over'], tex={fg['tex']: 1.0}, dyn=list(FUGUE['dyn']))
            if V2_:                           # (round o21: the pedal, the pad, the counter-subject; the marks grow
                blk['pedal'] = fg['pedal']    # entry by entry)
                blk['fugue'].update({x: fg[x] for x in ('pad', 'cs', 'cs_notes', 'entries', 'gap', 'subject')})
                ms_ = V2_['marks']
                dyn_ = [(round((a_ - t) / L, 4), ms_[min(j_, len(ms_) - 1)], 'step')
                        for j_, a_ in enumerate(fg['entries'])]
                blk['over'] = dict(blk['over'], dyn=dyn_ + [(1, ms_[-1])])
        elif kind == 'dev_fugato':
            k = _transpose_key(home, 5 if minor else 9, 'minor')
            vs, ch = w.fugato(name, k, t, bars)
            blk['voices'], blk['chart'], blk['key'] = vs, ch, k
            # (the horns' dominant pedal under the later entries: the textures that ask for it - a build)
            blk['pedal'] = [(t + L / 2, L / 2, _near({(Key(k).tonic + 7) % 12}, 55, 50, 62))]
        elif kind == 'retrans' and SET_PLAN and SET_PLAN.get('builds'):
            # (round o18b: the build's gesture - GESTURES; the crisis's collapse)
            gname = 'collapse' if over.get('collapse') else \
                draws.get('build') if draws.get('build') in GESTURES else 'swell'
            G_ = GESTURES[gname]
            fr = draws.get('frame') if draws.get('frame') in G_['frames'] else G_['frames'][0]
            sil = int(G_.get('silence', 0)) if bars >= 5 else 0
            blk['gp'] = 'direct' if gname == 'collapse' else 'gp' if sil else draws.get('retrans_end', 'gp')
            mel, ch, pedal, ans, vs = w.retrans(name, home, t, bars - sil, gname, frame=fr)
            if sil:                           # (the general pause: the last bar silent over the dominant)
                ch = ch + [(t + (bars - sil) * U, sil * U, _roman(home, 'V7'))]
                blk['silence'] = (t + (bars - sil) * U, t + L)
            blk['theme'], blk['chart'], blk['pedal'], blk['answer'], blk['voices'] = mel, ch, pedal, ans, vs
            blk['gesture'] = gname
            if G_.get('deceptive') and bars >= 6:     # (the deceptive arrival two bars before the end: subito p)
                fd = round((bars - 2) / bars, 3)
                blk['over'] = dict(blk['over'], dyn=[(0, 'mp', 'step'), (max(0.0, fd - 0.02), 'f'), (fd, 'p', 'step'),
                                                     (1, 'ff')])
        elif kind == 'retrans':
            blk['gp'] = draws.get('retrans_end', 'gp')
            mel, ch, pedal, ans, vs = w.retrans(name, home, t, bars, draws.get('build') if draws.get('build') in
                                                BUILDS else 'tremolo',
                                                frame=draws['frame'] if draws.get('frame') in BUILD_FRAMES else 'pedal')
            blk['theme'], blk['chart'], blk['pedal'], blk['answer'], blk['voices'] = mel, ch, pedal, ans, vs
            if getattr(w, 'chroma', {}).get(name):           # (CHROMA_CADENCE: the chromatic predominant)
                blk['chroma'] = w.chroma[name]
            if getattr(w, 'events', {}).get(name):           # (CHROMA_EVENT: the chord chain)
                blk['event'] = w.events[name]
        elif kind in ('coda', 'coda_soft'):
            cp = draws.get('coda_plan')
            if crisis_key is not None and SET_PLAN and SET_PLAN.get('v2') and cp not in CRISIS_V2['coda_plan']:
                cp = CRISIS_V2['coda_plan'][random.Random(f"symphony:{seed}:crisis_coda").randrange(
                    len(CRISIS_V2['coda_plan']))]    # (round o19a: the motto recalled as it dissolves)
            if cp not in CODA_PLANS[coda_kind]:   # (round o5: the coda's plan - the set's draw where it fits the kind)
                cp = _pick(random.Random(f"symphony:{seed}:coda_plan"), CODA_PLANS[coda_kind])
            mel, ch, ans = w.coda(name, finale, t, bars, coda_kind, cp, theme2)
            if DEV_WALK and DEV_WALK.get('recall') and w.dev_line():        # (round o16: the development's counter-line)
                ans = w.recall(name, finale, ch, t, bars, below=5) or ans
                blk['recalled'] = True        # (a texture without a counter leaves it out - never into the tune)
            blk['theme'], blk['chart'], blk['key'], blk['answer'], blk['plan'] = mel, ch, finale, ans, cp
        elif kind in ('end', 'end_soft'):
            Kf = Key(last_key)
            If = _roman(last_key, 'i' if Kf.minorish else 'I')
            blk['key'] = last_key
            blk['chart'] = [(t, L, If)]
            tonic = _near({Kf.tonic}, w.centre + (3 if kind == 'end' else -2))
            blk['theme'] = [(t, L, tonic)]
            pre = END_PRE['bars'] if bars >= END_PRE['bars'] + 2 else 0     # (round o9: the predominant first)
            if pre and END_LEN:               # (round o10: a longer end block - its closing bars before the cadence)
                pre = max(pre, bars - 3)
            ta = t + pre * U                  # (the approach bar)
            ending = draws.get('ending') if kind == 'end' else None
            if SET_PLAN and SET_PLAN.get('endings') and draws.get('ending') in END_FAMILIES:
                cad = END_FAMILIES[draws['ending']] if kind == 'end' else END_SOFT[draws['ending']]
            elif kind == 'end':
                cad = ENDING_CADENCE.get(ending)
            elif draws.get('ending') in SOFT_OF:  # (round o7: the soft ending from the set's draw - spread)
                cad = SOFT_OF[draws['ending']]
            else:
                cad = _pick(random.Random(f"symphony:{seed}:soft_end"), SOFT_ENDINGS)
            if cad and bars >= 2:             # (round o5: the approach bar, then the tonic; round o7: _approach)
                v2e = SET_PLAN and SET_PLAN.get('v2')
                amen2 = v2e and END_V2.get('amen') and cad == 'amen' and t + L - ta - U >= 2 * U - _EPS
                ch_, sop = _approach(last_key, 'V' if amen2 else cad, ta, U, tonic, strokes=ending == 'strokes')
                z_ = t + L - ta - U
                blk['chart'] = ch_ + [(ta + U, z_, If)]
                blk['theme'] = sop + [(ta + U, z_, _step(tonic, 2, pcs_of(last_key)) if cad == 'pedal' else tonic)]
                if amen2:                     # (round o19a: V7 - I, then the plagal amen in the tune: IV - I,
                    IVa = _roman(last_key, 'iv' if Kf.minorish and Kf.mode != 'dorian' else 'IV')   # 4 - 3 on top)
                    V7a = _roman(last_key, 'V7')
                    pk_ = pcs_of(last_key)
                    blk['chart'] = [(ta, U / 2, V7a), (ta + U / 2, U / 2, If), (ta + U, U, IVa),
                                    (ta + 2 * U, z_ - U, If)]
                    blk['theme'] = [(ta, U / 2, _step(tonic, 1, pcs_of(last_key, V7a))), (ta + U / 2, U / 2, tonic),
                                    (ta + U, U, _step(tonic, 3, pk_)), (ta + 2 * U, z_ - U, _step(tonic, 2, pk_))]
                    blk['amen'] = ta + U
                blk['cadence'] = cad
                blk['strokes'] = ending == 'strokes'
                blk['approach'] = ta
                if pre:
                    # (round o9 - o8's judges: "a bare two-beat V - I", CLND / FVNG / KQFD; "close with a cadence
                    # built from the theme": a predominant bar first, the motto's head over it, END_PRE)
                    P_rn = END_PRE['chord'][cad][1 if Kf.minorish else 0]
                    IV_rn = 'iv' if Kf.minorish and Kf.mode != 'dorian' else 'IV'
                    P_ = _roman(last_key, P_rn)
                    IVf = _roman(last_key, IV_rn)
                    pre_ch, pre_th = [], []
                    rns = [P_rn if i == pre - 1 else (('i' if Kf.minorish else 'I') if i % 2 == 0 else IV_rn)
                           for i in range(pre)]
                    for i in range(pre):      # (the closing bars: the tonic and the subdominant in turn, the
                        pre_ch.append((t + i * U, U, P_ if i == pre - 1 else (If if i % 2 == 0 else IVf)))
                    if cad == 'decep':        # (round o18b: V7 - vi in the bar before the approach - END_FAMILIES)
                        x_ = t + (pre - 1) * U
                        pre_ch[-1] = (x_, U / 2, _roman(last_key, 'V7'))
                        pre_ch.append((x_ + U / 2, U / 2, _deceptive(last_key)))
                    csyms = None
                    if CHROMA_CADENCE and CHROMA_CADENCE.get('final') and cad in END_CHROMA:
                        # (the code review's A2: the chromatic predominant before the final cadence, the last bars
                        # two chords a bar into the approach)
                        cb_ = min(int(CHROMA_CADENCE.get('bars', 2)), pre)
                        a0_ = t + (pre - cb_) * U
                        got_ = chroma_pre(last_key, a0_, U, cb_, END_CHROMA[cad], rns[pre - cb_],
                                          random.Random(f"symphony:{seed}:chroma_end"))
                        if got_:
                            pre_ch = [r for r in pre_ch if r[0] < a0_ - _EPS] + got_[0]
                            blk['chroma'] = got_[1]
                            csyms = {chroma_symbol(last_key, r[2]) for r in got_[1]}
                    whole = 0
                    if SET_PLAN and SET_PLAN.get('v2') and END_V2.get('motto') and \
                            pre >= (3 if cad == 'decep' else 2):      # (the deceptive's own last bar kept)
                        # (round o19a: the whole motto at its own speed over the first two closing bars - END_V2)
                        sy = _chart_at(pre_ch, t)
                        pp_ = pcs_of(last_key, sy)
                        anc = _near({x % 12 for x in pp_}, _step(tonic, 2, pcs_of(last_key)))
                        z0 = t + 2 * U - 0.25
                        pre_th += [(a, min(d, z0 - a), p) for a, d, p in w.state(name, t, anc, pcs_of(last_key),
                                                                                  fill=z0) if a < z0 - _EPS]
                        whole = 2
                    for i in range(whole, pre):  # predominant last - the motto's head over each, a step lower each)
                        x0 = t + i * U
                        sy = _chart_at(pre_ch, x0)
                        pp_ = _chroma_pcs(last_key, sy, csyms) if csyms else pcs_of(last_key, sy)
                        z0 = x0 + U - 0.25
                        anc = _step(_near({_member(sy, w.m['member'])}, tonic + 2), -(pre - 1 - i), pcs_of(last_key))
                        anc = _near({x % 12 for x in pp_}, anc) if pp_ else anc
                        if cad == 'decep' and i == pre - 1 and SET_PLAN and SET_PLAN.get('v2'):
                            # (round o19a: the head over V7, the tonic held over the deceptive chord - END_V2)
                            zh = x0 + U / 2 - 0.25
                            pre_th += [(a, min(d, zh - a), p) for a, d, p in
                                       w.state(name, x0, anc, pp_, ('head',), fill=zh) if a < zh - _EPS]
                            pre_th.append((x0 + U / 2, U / 2, _near({Kf.tonic}, anc)))
                            blk['decep'] = x0 + U / 2
                            continue
                        pre_th += [(a, min(d, z0 - a), p) for a, d, p in
                                   w.state(name, x0, anc, pp_, ('head',), fill=z0) if a < z0 - _EPS]
                    blk['chart'] = pre_ch + blk['chart']
                    blk['theme'] = fit_line(pre_th, pre_ch, last_key, chroma=csyms) + blk['theme']
            if bars >= 2 and ((kind == 'end' and ending == 'motto') or cad == 'echo'):   # (the head, landing on
                hd = [n for n in w.state(name, ta, _step(tonic, -4, pcs_of(last_key)), pcs_of(last_key), ('head',))
                      if n[0] < ta + U - 0.25]                                           # the tonic)
                blk['theme'] = [n for n in blk['theme'] if n[0] < ta - _EPS] + \
                    fit_line([(a, min(d, ta + U - a), p) for a, d, p in hd], blk['chart'], last_key) + \
                    [(ta + U, t + L - ta - U, tonic)]
            if blk.get('decep') is not None and SET_PLAN and SET_PLAN.get('v2'):
                m1, m2 = END_V2['decep'][kind]
                fd = round((blk['decep'] - t) / L, 3)
                fz = round((blk['decep'] + U / 2 - t) / L, 3)
                blk['over'] = dict(blk['over'], dyn=[(0, 'mf' if kind == 'end' else 'p'), (max(0.0, fd - 0.01), m1),
                                                     (fz, m2, 'step'), (1, m1)])
            if SET_PLAN and SET_PLAN.get('endings') and draws.get('ending') == 'line' and blk.get('cadence'):
                blk['answer'] = _end_line(last_key, blk['chart'], t, ta + U, t + L, U)   # (the falling line)
            if CHROMA_EVENT and CHROMA_EVENT.get('final') and bars >= 2 and pre:
                ev_ = _final_event(w, name, last_key, blk, t, ta, U, kind, seed)   # (round o15b: the event)
                if ev_:
                    blk['event'] = ev_
        elif kind == 'trio':                  # (round o4: a contrasting middle - its own tune in a far key)
            k = _transpose_key(home, 5, 'major') if not minor else \
                _transpose_key(home, 8 if rel == 'relative' else 3, 'major')
            blk['key'] = k
            sk = skeleton(random.Random(f"symphony:{seed}:trio"))
            mel, ch = w.cantilena(name, k, t, bars, centre=w.centre - 3, sk=sk, theme='C')
            if over.get('grow'):
                mel = [(a, d, p + 12 if a >= t + L / 2 and p + 12 <= 88 else p) for a, d, p in mel]
            blk['theme'], blk['chart'] = mel, ch
        elif kind == 'refrain':               # (round o4: the rondo's refrain back, shortened and varied; the false
            false = over.get('false')         # recapitulation's first theme in a far key)
            k = (_transpose_key(home, 8, 'major') if minor else _transpose_key(home, 5)) if false else home
            blk['key'] = k
            rr = random.Random(f"symphony:{seed}:refrain:{name}")
            vary = (('dot', 'reharm', 'invert')[rr.randrange(3)],)
            ans = 'step_up' if draws['answer'] == 'dominant' else 'dominant'
            mel, ch = w.sentence(name, k, t, bars, end='PAC', answer=ans, centre=w.centre - (3 if false else 0),
                                 vary=vary)
            blk['theme'], blk['chart'] = mel, ch
        elif kind == 'var':
            th = theme1 or (home, [(a - t, d, p) for a, d, p in w.sentence(name, home, t, 8)[0]], 8)
            mel, ch, cnt, k = w.variation(name, home, t, bars, over['var'], th)
            blk['theme'], blk['chart'], blk['answer'], blk['key'] = mel, ch, cnt, k
        else:
            raise ComposeError(f"symphony: block kind {kind!r} has no writer")
        if FUGUE and FUGUE.get('v2') and blk['peak'] and getattr(w, 'fug_subj', None) and blk['theme']:
            # (round o21: the fugato's subject back at the summit - in the bass, augmented, against the melody)
            ret_ = w.fug_return(name, blk['key'], t, bars, blk['theme'], blk['chart'])
            if ret_:
                blk['fug_return'] = ret_
        if name == elide:                     # (the cadence bar is the next block's first: cut)
            L -= U
            blk['bars'] -= 1
            z = t + L
            for k_ in ('theme', 'answer', 'pedal'):
                blk[k_] = [(a, min(d, z - a), p) for a, d, p in blk[k_] if a < z - _EPS]
            blk['voices'] = {v: [(a, min(d, z - a), p) for a, d, p in ns if a < z - _EPS]
                             for v, ns in blk['voices'].items()}
            blk['chart'] = [(a, min(d, z - a), s_) for a, d, s_ in blk['chart'] if a < z - _EPS]
            blk['elided'] = True
        for blk in (_phase_blocks(blk, U, w.log) if blk.get('phases') and DEV_WALK.get('split') else [blk]):
            t_ = blk['start']                 # (DEV_WALK 'split': each phase of the walk its own block)
            for k_ in ('theme', 'answer'):    # (every line one line: a statement never overlaps the next; no
                blk[k_] = _mono(blk[k_])      # two-note shake left after the chord fit)
                if blk['chart'] and kind not in ('end', 'end_soft'):
                    blk[k_] = _unshake(blk[k_], pcs_of(blk['key']), blk['chart'])
            blk['voices'] = {v: _mono(ns) for v, ns in blk['voices'].items()}
            if blk.get('event'):              # (CHROMA_EVENT: the melody keeps the chords' top voice)
                ev_ = blk['event']
                a_e, z_e = ev_['cut'] if ev_['kind'] == 'chain' else (ev_['hold'][0],
                                                                       ev_['hold'][0] + ev_['hold'][1])
                blk['theme'] = sorted([(x, min(d, a_e - x), q) for x, d, q in blk['theme'] if x < a_e - _EPS] +
                                      list(ev_['tops']) + [n for n in blk['theme'] if n[0] >= z_e - _EPS])
            if SEQ_BREAK and kind in FORM_STATS['dev']:   # (round o15b: no chain of more links than the gate's)
                z_ = t_ + blk['bars'] * U
                for k_ in ('theme', 'answer'):
                    blk[k_] = _break_links(blk[k_], U, t_, z_)
                blk['voices'] = {v: _break_links(ns, U, t_, z_) for v, ns in blk['voices'].items()}
            past_peak = past_peak or blk['peak']
            blocks.append(blk)
        t += L
    return {'layout': layout, 'family': fam, 'U': U, 'scale': F.get('scale', 1), 'motto': motto, 'blocks': blocks,
            'log': w.log, 'second': second, 'coda': coda_kind, 'climax': climax or 'brass'}


# ------------------------------------------------------------------------------------------------ compose

def compose(genre, seed: int, mood: str | None = None, swing=None, plan: dict | None = None):
    """A symphonic Tune (composer.compose hands every plan['perform'] = 'symphony' genre here): the movement type,
    mood, key, tempo (plan pins them: a set_plan entry), the set draws (plan['set']), the material - deterministic."""
    from .composer import Tune, set_draws, title
    del swing
    plan = dict(plan or {})
    rng = random.Random(f"endless:{genre.name}:{seed}")
    mood = mood or plan.get('mood') or _pick(rng, {m: 1.0 for m in sorted(genre.moods)})
    if mood not in genre.moods:
        raise ComposeError(f"genre {genre.name!r} has no mood {mood!r}; moods: {', '.join(genre.moods)}")
    M = genre.moods[mood]
    feel = plan.get('feel') or _pick(rng, M['feels'])
    if feel not in genre.feels:
        raise ComposeError(f"genre {genre.name!r} has no feel {feel!r}; feels: {', '.join(genre.feels)}")
    F = genre.feels[feel]
    if plan.get('key'):
        tonic, mode = plan['key'].split()
    else:
        mode = _pick(rng, M['modes'])
        tonic = rng.choice(M['keys'][mode])
    key = f"{tonic} {mode}"
    lo, hi = F['tempo']
    tempo = int(plan['tempo']) if plan.get('tempo') else \
        int(round(min(hi, max(lo, rng.uniform(lo, hi) + M.get('tempo', 0)))))
    energy = float(plan.get('energy', (F.get('energy', 0.5) + M.get('energy', 0.5)) / 2))
    own = set_draws(genre, random.Random(f"symphony-draws:{genre.name}:{seed}"))
    draws = {k: plan.get(k, v) for k, v in own.items()}
    fam = F['family']
    if not isinstance(draws['motto'], dict):
        draws['motto'] = {fam: draws['motto']}
    if fam not in draws['motto']:
        draws['motto'] = dict(draws['motto'], **{fam: own['motto'][fam]})
    if draws['motto'][fam] == 'knock' and draws['land'] in (-2, 2):
        draws['land'] = 3                # (three repeated notes and a third: the famous one - never)
    cell_m = {'family': fam, 'kind': draws['motto'][fam], 'member': draws['member']}

    def _ok(cm, alt):
        return alt and not (cm['kind'] == 'knock' and alt in (-2, 2)) and not _shakes(
            [p for _, _, p in motto_notes(dict(cm, land=alt), 0.0, 60, set(Key('C major').pcs))]) and \
            motto_character(dict(cm, land=alt))
    w_ = (genre.plan['set']['motto'] or {}).get(fam) or {}
    if MOTTO_CHARACTER.get('scale') is not None:      # (round o12: the next cell by the weights, seeded per piece)
        ro = random.Random(f"symphony:{genre.name}:{seed}:motto-next")
        cells = [cell_m['kind']] + sorted((c for c in CELLS[fam] if c != cell_m['kind']),
                                          key=lambda c: (-ro.random() ** (1.0 / max(1e-3, w_.get(c, 0.05))), c))
    else:
        cells = [cell_m['kind']] + sorted((c for c in CELLS[fam] if c != cell_m['kind']),
                                          key=lambda c: (-w_.get(c, 0), c))
    found = False
    for kind in cells:                  # (a motto whose landing makes a two-note shake, round o3: or one without
        cm = dict(cell_m, kind=kind)    # character - MOTTO_CHARACTER: the next landing, then the next cell)
        for alt in (draws['land'], draws['land'] + 1, draws['land'] - 1, draws['land'] + 2, 3, 4, -3, 5, -4, 2):
            if _ok(cm, alt):
                draws['land'], found = alt, True
                if kind != cell_m['kind']:
                    draws['motto'] = dict(draws['motto'], **{fam: kind})
                break
        if found:
            break
    # (round o3: two pieces of a set sang the same second theme - six fixed skeletons; a skeleton of the piece's own)
    rk = random.Random(f"symphony:{genre.name}:{seed}:skeleton:{draws.get('skeleton') or 0}")
    draws['skeleton'] = {m_: skeleton(rk) for m_ in SKELETONS}
    if MACRO:                                 # (round o24: the macro shape - the set's, else the piece's own)
        sh_ = plan.get('shape') if isinstance(plan.get('shape'), dict) else None
        if sh_ is None:
            fs_ = _form_seed(draws, key, seed)
            sh_ = shape_draw(genre, feel, _layout_of(genre, F, draws, fs_), mood, _coda_of(M, draws, fs_),
                             random.Random(f"sym-shape:{seed}"))
        draws = _macro_draws(dict(draws, shape=dict(sh_)))
    mat = material(genre, key, feel, mood, seed, draws, tempo=tempo)
    sc = mat['scale']
    meter = 4 if fam == 'duple' else 3
    name = title(random.Random(f"title:{genre.name}:{seed}"), feel, mat['layout'], genre.titles, key,
                 prefix=plan.get('title_form') if genre.plan.get('set_polish') else None)   # (round op1: POLISH)
    parts = [b['name'] for b in mat['blocks']]
    k_ = sc
    changes, melody, levels = {}, {}, {}
    for b in mat['blocks']:
        a = b['start']
        changes[b['name']] = [(s, d * k_) for _, d, s in b['chart']] or [(_roman(key, 'I'), b['bars'] * mat['U'] * k_)]
        line = b['theme'] or next(iter(b['voices'].values()), [])
        melody[b['name']] = [(_q12((x - a) * k_), max(1 / 12, _q12(d * k_)), p) for x, d, p in line]   # (the tokens' grid)
        nb = max(1, int(round(b['bars'] * mat['U'] * k_ / (2 * meter))))
        lv = kind_data(genre, b['kind'], b['over']).get('level', 0.6)
        levels[b['name']] = [lv] * nb
    head = next((b for b in mat['blocks'] if b['kind'] in ('t1', 'river', 'intro') and b['theme']), mat['blocks'][0])
    motif = [((x - head['start']) * k_, d * k_, p) for x, d, p in (head['theme'] or [])][:6]
    end_chord = _roman(key, 'i' if Key(key).minorish else 'I')
    if not any(melody.values()):
        raise ComposeError("symphony: no melody written")
    tune = Tune(genre=genre.name, seed=seed, mood=mood, title=name, key=key, mode=mode, tempo=tempo, meter=meter,
                feel=feel, swing=None, form=mat['layout'], parts=parts, changes=changes, melody=melody,
                motif=motif, end_chord=end_chord, energy=energy, levels=levels,
                arrange={k: v for k, v in draws.items() if k != 'skeleton'})
    if TECH and TECH.get('v2'):               # (round o24: the ranking with the whole set's memory - tech_rank_v2)
        tune.arrange['tech'] = list(plan['tech2'] if 'tech2' in plan else plan.get('tech') or
                                    tech_rank_v2(feel, random.Random(f"sym-tech:{seed}"), (), draws.get('shape'))[0])
        tune.arrange['tech_crown'] = bool(plan.get('tech_crown', True))
    elif TECH:                                # (round o23: the technique ranking - the set's, else the piece's own)
        tune.arrange['tech'] = list(plan.get('tech') or tech_rank(feel, random.Random(f"sym-tech:{seed}")))
    from . import choir as CH
    if CH.CHOIR:                              # (round oc1: the choir's plan - the set's, else the piece's own)
        tune.arrange['choir'] = plan.get('choir') or CH.choir_draw(feel, random.Random(f"sym-choir:{seed}"))
        if CH.CHOIR.get('polish') and plan.get('choir_tex'):    # (round op1: the summit's texture, set memory)
            tune.arrange['choir_tex'] = plan['choir_tex']
    from . import solo as solo_
    if solo_.SOLO:                            # (round os1: the string solo event - the set's, else the piece's own)
        tune.arrange['solo'] = plan.get('solo') or solo_.solo_draw(random.Random(f"sym-solo:{seed}"))
    from . import hero_sax as HS
    mode = plan.get('hero_sax', 'occasional')
    enabled = HS.draw(mode, seed)
    if 'hero_sax_enabled' in plan and not isinstance(plan['hero_sax_enabled'], bool):
        raise ComposeError('hero_sax_enabled must be a boolean')
    tune.arrange['hero_sax'] = mode
    tune.arrange['hero_sax_enabled'] = bool(plan.get('hero_sax_enabled', enabled)) and mode != 'off'
    from . import colour as CO
    if CO.COLOUR:                             # (round ox1: the guest colour - the set's, else the piece's own)
        tune.arrange['guest'] = dict(plan.get('guest') or CO.guest_draw(feel, random.Random(f"sym-guest:{seed}")))
    tune.symphony = mat
    tune.time_sig = tuple(F['time_sig'])       # (Tune.meter is the beats per bar: a 6/8 printed '3/4' - q1)
    return tune


def _material_of(tune, g) -> dict:
    mat = getattr(tune, 'symphony', None)
    if mat is None:
        again = compose(g, tune.seed, tune.mood, plan={'feel': tune.feel, 'key': tune.key, 'tempo': tune.tempo,
                                                       **(tune.arrange or {})})
        mat = again.symphony
    return mat


# ------------------------------------------------------------------------------------------------ the build

def _q12(x: float) -> float:
    """x on the 1/12-beat grid (the Tune's summary lines are tokenized: learn.tokens)."""
    return round(x * 12) / 12


def _scaled(notes, k: float):
    return [(a * k, d * k, p) for a, d, p in notes]


def _walk_entries(b, ents: dict, k: float) -> None:
    """DEV_WALK v3's stretto (Writer.walk3 'entries'): in each stretto window the harmony's top voice plays the tenor's
    entries and the bass line the bass's (k: internal -> song beats); a texture without the role leaves them out."""
    wins = [(a * k, z * k) for a, z in ents['win']]

    def inside(x):
        return any(a - _EPS <= x < z - _EPS for a, z in wins)
    for fn, ns in (('harmony', ents['inner']), ('bass', ents['bass'])):
        lines = sorted(b.get(fn), key=lambda x: x.voice)
        if not lines or not ns:
            continue
        x = lines[0]
        x.notes = sorted([n for n in x.notes if not inside(n[0])] + _scaled(ns, k))
        for a, z in wins:                     # (a held chord into a window ends where it starts)
            x.notes = [(s, min(d, a - s) if s < a - _EPS < s + d else d, p) for s, d, p in x.notes]
        x.notes = [n for n in x.notes if n[1] > _EPS]


def validate_plan(genre, bad) -> None:
    """A 'symphony' plan: plan['layouts'] {name: [(block name, kind, bars)]}, plan['kinds'] {kind: {'tex': {texture:
    weight}, 'dyn': [(fraction, mark[, 'step'])], 'peak', 'sf', 'level'}}, plan['sizes'], plan['set'] (the draws),
    the feels' 'family' ('duple' | 'compound'), 'scale' (1 | 2) and 'time_sig' (the song's (n, d))."""
    P = genre.plan
    for k in ('layouts', 'kinds', 'sizes', 'set'):
        if not isinstance(P.get(k), dict) or not P[k]:
            bad(f"a 'symphony' plan needs plan[{k!r}]")
    sizes = P['sizes']
    table = orch.role_table(genre.band['preset'])
    for name, roles in sizes.items():
        if set(roles) - set(table):
            bad(f"plan sizes[{name!r}]: {sorted(set(roles) - set(table))} are no {genre.band['preset']} roles")
    for m, d in genre.moods.items():
        sw = d.get('size')
        if not isinstance(sw, dict) or not sw or set(sw) - set(sizes):
            bad(f"mood {m!r}: size {{one of {', '.join(sizes)}: weight}}")
        if set(d.get('coda', {'triumph': 1})) - {'triumph', 'dissolve'}:
            bad(f"mood {m!r}: coda {{'triumph' / 'dissolve': weight}}")
        if set(d.get('climax', CLIMAX_DEFAULT)) - set(CLIMAXES):
            bad(f"mood {m!r}: climax {{{' / '.join(CLIMAXES)}: weight}}")
    for kind, K in P['kinds'].items():
        if kind not in KINDS:
            bad(f"plan kinds: {kind!r} is no block kind ({', '.join(KINDS)})")
        if set(K) - KIND_KEYS - {'level'}:
            bad(f"plan kinds[{kind!r}]: unknown keys {sorted(set(K) - KIND_KEYS - {'level'})}")
        tex = K.get('tex')
        if not isinstance(tex, dict) or not tex or any(t not in orc.TEXTURES or w <= 0 for t, w in tex.items()):
            bad(f"plan kinds[{kind!r}]['tex']: {{texture: weight > 0}} of orchestration.TEXTURES")
        need = THEME_NEEDS.get(kind)
        for t in tex:
            T = orc.TEXTURES[t]
            if need == 'voice' and 'voice' not in T:
                bad(f"plan kinds[{kind!r}]: texture {t!r} has no 'voice' slot (a fugato's voices)")
            if need == 'theme' and 'melody' not in T and T.get('theme') != 'bass':
                bad(f"plan kinds[{kind!r}]: texture {t!r} seats no theme (a 'melody' slot or 'theme': 'bass')")
        for x in K.get('dyn') or ():
            if not (isinstance(x, tuple) and len(x) in (2, 3) and 0 <= x[0] <= 1 and x[1] in orch.VEL and
                    (len(x) == 2 or x[2] == 'step')):
                bad(f"plan kinds[{kind!r}]['dyn']: (fraction 0..1, a mark of {', '.join(orch.VEL)}[, 'step'])")
    for lay, rows in P['layouts'].items():
        names = [r[0] for r in rows]
        if len(set(names)) != len(names):
            bad(f"plan layouts[{lay!r}]: a block name twice")
        for r in rows:
            if len(r) not in (3, 4) or r[1] not in P['kinds'] or not isinstance(r[2], int) or r[2] < 1 or \
                    (len(r) == 4 and (not isinstance(r[3], dict) or set(r[3]) - KIND_KEYS - {'grow', 'false', 'var'})):
                bad(f"plan layouts[{lay!r}]: rows (name, a plan['kinds'] kind, bars >= 1[, {{kind key: value}}]), "
                    f"got {r!r}")
        if rows[-1][1] != 'end':
            bad(f"plan layouts[{lay!r}]: the last block is the 'end'")
    for x in list(INTRO_KINDS.values()) + [k for ks in CODA_KINDS.values() for k in ks]:
        if x not in P['kinds']:
            bad(f"plan kinds: {x!r} missing (the openings / codas the draws play)")
    for f, F in genre.feels.items():
        if F.get('family') not in CELLS:
            bad(f"feel {f!r}: family 'duple' or 'compound'")
        if F.get('scale', 1) not in (1, 2) or (F.get('scale', 1) == 2 and F['family'] != 'compound'):
            bad(f"feel {f!r}: scale 1, or 2 for a compound feel (the fast 3/4)")
        ts = F.get('time_sig')
        if not (isinstance(ts, (tuple, list)) and len(ts) == 2 and tuple(ts) in ((4, 4), (6, 8), (3, 4))) or \
                (tuple(ts) == (4, 4)) != (F['family'] == 'duple') or \
                (tuple(ts) == (3, 4)) != (F.get('scale', 1) == 2):
            bad(f"feel {f!r}: time_sig (4, 4) duple, (6, 8) compound, (3, 4) compound at scale 2")
        if F.get('layout') is not None and F['layout'] not in P['layouts']:
            bad(f"feel {f!r}: layout {F['layout']!r} is no plan['layouts'] entry")
        if set(F.get('layouts') or ()) - set(P['layouts']):
            bad(f"feel {f!r}: layouts {F['layouts']!r} not all plan['layouts'] entries")
    S = P['set']
    for k in ('layout', 'motto', 'land', 'member', 'answer', 'intro', 'key2', 'dev_path', 'entry'):
        if k not in S:
            bad(f"plan['set'] needs {k!r} (the piece's draws)")
    for fam_, cells in (S.get('motto') or {}).items():
        if fam_ not in CELLS or not isinstance(cells, dict) or set(cells) - set(CELLS[fam_]):
            bad(f"plan['set']['motto']: {{family: {{cell: weight}}}} of {sorted(CELLS)}")
    if set(S.get('layout', {})) - set(P['layouts']):
        bad("plan['set']['layout']: names of plan['layouts']")
    if set(S.get('dev_path', {})) - set(DEV_PATHS):
        bad(f"plan['set']['dev_path']: of {', '.join(DEV_PATHS)}")
    for k, allowed in (('dev', DEV_FORMS), ('span', SPANS), ('colour', OPENING_COLOURS),
                       ('coda', CODA_KINDS), ('slow', (0, 1)), ('climax', CLIMAXES),
                       ('build', GESTURES if SET_PLAN else BUILDS),
                       ('size', sizes), ('dev_tech', DEV_TECH), ('apex', APEX), ('src', SOURCES),
                       ('t2col', T2_COLOURS), ('ending', END_TEX if SET_PLAN else ENDINGS), ('acc', ACCOMPANIMENTS),
                       ('arc', ('return', 'crisis')), ('voicing', ('tutti', 'layers')), ('contour', CONTOURS),
                       ('derive', ('plain', 'invert', 'none')), ('frame', BUILD_FRAMES),
                       ('phrase', ('square', 'free')), ('elide', (0, 1)),
                       ('coda_plan', {x for v in CODA_PLANS.values() for x in v}), ('src_chart', SOURCE_CHARTS),
                       ('src_entry', SOURCE_ENTRIES), ('clx_mode', CLX_MODES),
                       ('sections', set(FORM_SHAPE['deltas']) | set(FORM_MERGE['deltas'])),
                       ('peak_at', set(PEAK_AT['at']) | set(PEAK_AT_V3['at'])), ('tex_t1', TEX_V3['t1']),
                       ('tex_t1b', TEX_V3['t1b']), ('tex_dev', TEX_V3['dev'])):
        if set(S.get(k, {})) - set(allowed):
            bad(f"plan['set'][{k!r}]: of {', '.join(map(str, allowed))}")
    for f, F in genre.feels.items():
        if set(F.get('spans') or ()) - set(SPANS):
            bad(f"feel {f!r}: spans of {', '.join(SPANS)}")
        if F.get('slow') and 'slow' not in P['kinds']:
            bad(f"feel {f!r}: a slow introduction needs plan['kinds']['slow']")
    if genre.band.get('style', 'romantic') not in ('film', 'romantic', 'classical', 'baroque'):
        bad("band['style']: the orchestral player's style (ensemble.STYLES)")


CHAMBER = {'tutti_symphonic': 'apotheosis_strings', 'tutti_chorale': 'apotheosis_strings',
           'motto_brass': 'motto_unison', 'dialogue_brass': 'dialogue', 'chorale_brass': 'hammer',
           'apex_augment': 'apex_augment_strings', 'apex_theme': 'apex_theme_strings'}
"""The chamber orchestra's stand-in for a plan that needs the brass (texture 'size': 'full'); one not named: the
strings' apotheosis at a peak, else the driving tutti."""

SCHERZO_TEX = {'kinds': ('t1', 't1b', 'recap', 'refrain', 'close'),
               'tex': {'motto_bass': 'tutti_drive', 'running_strings': 'drive_strings'}}
"""The scherzo's theme textures (round o6 - o5's judges, the worst piece: "the dance tune in the cellos / basses,
violins1's broken-chord eighths over it - heard as the theme"): in the fast 3/4 (scale 2) a theme block's texture with
the tune under a running part ('kinds') takes the stand-in ('tex') with the tune on top over the repeated 8ths - the
violins (with the flutes in the tutti), the strings' drive under them."""

ACCOMPANIMENTS = ('pulse', 'rock', 'motto', 'sync')
ACC_SHARE = 0.75
"""The driving accompaniment's family per piece (plan['set']['acc'], round o3 - "the same accompaniment cells in
every piece: violins II in 8ths, violas on 1 / 2 / 3"): a 'drive' slot plays the piece's family this share of its
blocks (the rest drawn): repeated 8ths, the rocking 3rds / 6ths, the motto's rhythm, off-beat chords."""


OSTINATO_VARY = {'span': {4: 1.0, 6: 0.7, 8: 0.5},
                 'alt': {'pulse': ('rock', 'arp', 'motto'), 'rock': ('pulse', 'arp', 'sync'), 'arp': ('rock', 'pulse'),
                         'motto': ('pulse', 'rock'), 'sync': ('pulse', 'rock')}}
"""Round o4 (o3's judges: 16-bar unchanged ostinati): a block's string ostinato alternates with another figure ('alt'
per figure) every 'span' song bars (drawn)."""


INNER_MOTION = {'move_beats': 3.0, 'sus': (1, 2), 'pass': (3, 4), 'floor': 48}
"""Round o7 (o6's judges: "repeated-note inner strings with no melody", the violas / violins II on one pitch for whole
bars): the ostinato's two held parts move before they are struck (_move_inner) - a held chord tone of
'move_beats'+ goes to the chord's next tone and back every half bar of the song (the upper part up, the lower
down: contrary motion; bar: the song's bar in beats), the note
before a chord change a semitone / tone over the new one is held into it as a suspension resolving a beat later
('sus'), and a third to the next note is filled with the passing tone on the last beat ('pass'). Round o12 ('floor'; o11's
judges, ARFK 30-83: "harp arpeggios side by side" in the development): the lower part never moves under C3 - under the
violas' floor no string covered the ostinato and the harp took it."""


def _move_inner(o: dict, chart, key: str, bar: float = 4.0) -> dict:
    """The ostinato's held parts {voice: [(start, dur, pitch)]} with moving inner voices (INNER_MOTION)."""
    M = INNER_MOTION
    pk = pcs_of(key)

    def cpcs_at(t):
        sym = _chart_at(chart, t)
        return _cpcs(sym) if sym else pk
    out = {}
    for j, (v, ns) in enumerate(sorted(o.items())):
        ns = sorted(ns)
        up = j == 0                            # (o1 the upper part: up; o2 down - contrary motion)
        res = []
        for i, (a, d, p) in enumerate(ns):
            prev = ns[i - 1] if i and abs(ns[i - 1][0] + ns[i - 1][1] - a) < _EPS else None
            nxt = ns[i + 1] if i + 1 < len(ns) and abs(a + d - ns[i + 1][0]) < _EPS else None
            seg = [(a, d, p)]
            cs = cpcs_at(a + 0.01)
            if prev is not None and prev[2] - p in M['sus'] and prev[2] % 12 not in cs and d >= 2.0 - _EPS:
                seg = [(a, 1.0, prev[2]), (a + 1.0, d - 1.0, p)]          # (the suspension, resolving down)
            elif d >= M['move_beats'] - _EPS:   # (the chord's next tone every half bar of the song, and back)
                h = max(1.5, bar / 2)
                seg, x, k = [], a, 0
                while x < a + d - _EPS:
                    ch_ = cpcs_at(x + 0.01)
                    q = p if k % 2 == 0 else next((y for y in (range(p + 1, p + 6) if up else range(p - 1, p - 6, -1))
                                                   if y % 12 in ch_ and (up or y >= M.get('floor', 0))), p)
                    seg.append((x, min(h, a + d - x), q))
                    x, k = x + h, k + 1
            if nxt is not None and abs(nxt[2] - seg[-1][2]) in M['pass'] and seg[-1][1] >= 2.0 - _EPS:
                x, dx, q = seg[-1]
                mid = _step(q, 1 if nxt[2] > q else -1, pk)
                if min(q, nxt[2]) < mid < max(q, nxt[2]):
                    seg = seg[:-1] + [(x, dx - 1.0, q), (x + dx - 1.0, 1.0, mid)]
            res += [s_ for s_ in seg if s_[1] > _EPS]
        out[v] = res
    return out


def _ostinato_figure(how: str, o: dict, start: float, U: float, rs, motto_rhythm) -> dict:
    """The string ostinato's parts from the two held parts o (eo._harmony on OSTINATO_SET): 'pulse' / 'rock' / 'arp'
    (eo._ostinato), 'sync' (off-beat chords), 'motto' (the motto's rhythm on the held notes)."""
    if how == 'sync':
        from .. import figures
        return {v: figures.repeat(ns, step=1.0, gap=0.42, offset=0.5) for v, ns in o.items()}
    if how != 'motto':
        return eo._ostinato(o, how, rs)
    parts = {}
    for v, ns in o.items():
        out = []
        for a, d, p in ns:
            t = a
            while t < a + d - _EPS:
                bar = start + U * math.floor((t - start) / U + _EPS)
                for on, du in motto_rhythm:
                    x = bar + on
                    if t - _EPS <= x < a + d - _EPS and on < U:
                        out.append((x, min(du * 0.85, 0.9), p))
                t = bar + U
        parts[v] = sorted(set(out))
    return parts


FIG_RANGE = {'wave': (72, 88, 60), 'wave1': (60, 79, 55), 'run': (67, 86, 55)}
FIG_UNDER = {'gap': 2, 'span': 12, 'low': True}
"""The running figuration's register per figure (lowest, highest note, the floor under a tune) and - round o8, o7's judges: "themes that are
only running arpeggios / 16ths: the violins' 16ths over the tune" - under a tune on top the figuration's range moved
under the tune's median by 'gap' semitones (its span kept, over its floor - G3 the strings', C4 the flutes'), when it keeps
'span' semitones to run in; a low tune (horns, cellos) keeps the stream over it. Round o10 ('low'): under the tune's
lowest note first (CKNM: the stream ran through the tune's register, heard as the theme)."""


def _chroma_voice(parts: dict, rec, chart, key: str, mel=()) -> dict:
    """CHROMA_CADENCE's chords voiced by realise() in the chord parts {voice: notes} (eo._harmony's smallest motion let
    the augmented sixth's #4 fall, the Neapolitan's b2 rise): per record (start, beats, rn, target) the voices sounding
    at the chromatic chord and at its resolution (the chart row after it) take realise()'s voicing - their register
    kept (lo / hi / centre from their pitches), under the tune's lowest note; no voicing: the parts as they were."""
    if not rec:
        return parts
    edges = sorted({a for a, _, _ in chart} | {a + d for a, d, _ in chart})

    def split(ns, t):
        out = []
        for a, d, p in ns:
            if a < t - _EPS < a + d - 2 * _EPS:
                out += [(a, t - a, p), (t, a + d - t, p)]
            else:
                out.append((a, d, p))
        return out
    for a, d, rn, tgt in rec:
        z = a + d
        z2 = next((e for e in edges if e > z + _EPS), None)
        cuts = [a, z] + ([z2] if z2 is not None else [])
        ps = {v: ns for v, ns in parts.items() if ns}
        for t in cuts:
            ps = {v: split(ns, t) for v, ns in ps.items()}
        at = {v: next((n for n in ns if abs(n[0] - a) < 1e-4), None) for v, ns in ps.items()}
        res = {v: next((n for n in ns if abs(n[0] - z) < 1e-4), None) for v, ns in ps.items()}
        vs = sorted((v for v in ps if at[v] is not None and res[v] is not None), key=lambda v: (at[v][2], v))
        if not vs:
            continue
        cap = min((p for x, du, p in mel if x < z + d - _EPS and x + du > a + _EPS), default=None)
        pit = [at[v][2] for v in vs]
        got = None
        for dl, dh in ((5, 5), (9, 7), (14, 7)):       # (the voices' register, wider when it cannot hold the chord)
            got = got or realise(key, rn, tgt, len(vs), lo=min(pit) - dl, hi=max(pit) + dh, cap=cap,
                                 centre=sum(pit) / len(pit))
        if got is None:
            continue
        (_, up0), (_, up1) = got
        for v, q0, q1 in zip(vs, up0, up1):
            ps[v] = [(x, du, q0) if abs(x - a) < 1e-4 else (x, du, q1) if abs(x - z) < 1e-4 else (x, du, p)
                     for x, du, p in ps[v]]
        parts = dict(parts, **{v: eo._tie(ns) for v, ns in ps.items()})
    return parts


def _write_accompaniment(b, blk, need: dict, key: str, U: float, theme_top, rs, motto_rhythm) -> None:
    """The lines the texture's slots ask for besides the block's own material (their 'figure')."""
    chart = b.chart
    if not chart:
        return
    mel = theme_top
    end = blk.get('kind') in ('end', 'end_soft')       # (round o7: the last chords voiced - END_VOICING)
    if 'harmony' in need:
        n = max(2, min(4, need['harmony'][0].get('n', 3)))
        harm = eo._harmony(chart, mel, n, key, ranges=dict(list(END_VOICING['harmony'].items())[:n]) if end
                           else None)
        if blk.get('chroma'):                           # (CHROMA_CADENCE: the chromatic chord voiced into its goal)
            harm = _chroma_voice(harm, blk['chroma'], chart, blk['key'], mel)
        if end:
            harm = _resolve(harm, chart, blk['key'], mel, END_VOICING['harmony'])
        elif STATIC and not b.peak and b.length > STATIC['bars'] * blk.get('bar', U) + _EPS:
            harm = _move_inner(harm, chart, key, blk.get('bar', U))      # (round o9: no 8+ bars of held pads)
            if STATIC.get('figure') and not ({'ostinato', 'figuration'} & set(need)) and len(harm) >= 2:
                harm = _figure_held(harm, b.start, blk.get('bar', U), rs)
        for v, ns in harm.items():
            if ns:
                b.add(orc.Line('harmony', ns, voice=v))
    if 'inner' in need:
        inner = eo._harmony(chart, mel, 2, key, ranges=END_VOICING['inner'] if end else
                            {'i1': (55, 76, 64), 'i2': (48, 69, 57)})
        if blk.get('chroma'):
            inner = _chroma_voice(inner, blk['chroma'], chart, blk['key'], mel)
        if end:
            inner = _resolve(inner, chart, blk['key'], mel, END_VOICING['inner'])
        else:                   # (round o10: inner voices over G3 - a violin section can take them: o.folded)
            inner = {v: [(a, d, p + 12 if p < 55 else p) for a, d, p in ns] for v, ns in inner.items()}
        for v, ns in inner.items():
            if ns:
                b.add(orc.Line('inner', ns, voice=v))
    if 'ostinato' in need:
        s = need['ostinato'][0]
        fig = s.get('figure', 'drive')
        o = _move_inner(eo._harmony(chart, mel, 2, key, ranges=eo.OSTINATO_SET), chart, key, blk.get('bar', U))
        if fig in ('arp', 'sync', 'motto'):     # (round o3: 'sync' the off-beat chords - the second theme's pulse;
            how = fig                           # round o25: 'motto' the motto's rhythm, SHAPE3's chorale / cut)
        elif fig == 'drive':
            how = _pick(rs, {'pulse': 1.0, 'rock': 0.8, 'motto': 0.9})
            if blk.get('acc') in ACCOMPANIMENTS and rs.random() < ACC_SHARE:
                how = blk['acc']                # (the piece's accompaniment family: one per piece, the set's spread)
        else:
            how = 'pulse'
        parts = _ostinato_figure(how, o, b.start, U, rs, motto_rhythm)
        # (round o4: an ostinato changes every 4-8 bars - o3's judges: "16 bars of the same viola pattern")
        alt = OSTINATO_VARY['alt'][how]
        span = _pick(rs, OSTINATO_VARY['span']) * blk.get('bar', U)
        if b.length > span + _EPS:
            other = _ostinato_figure(alt[rs.randrange(len(alt))], o, b.start, U, rs, motto_rhythm)
            parts = {v: [n for n in parts.get(v, []) if int((n[0] - b.start + _EPS) // span) % 2 == 0] +
                     [n for n in other.get(v, []) if int((n[0] - b.start + _EPS) // span) % 2 == 1]
                     for v in sorted(set(parts) | set(other))}
        for v, ns in parts.items():
            if ns:
                b.add(orc.Line('ostinato', sorted(ns), voice=v, art=s.get('art')))
    if 'bass' in need and not b.get('bass'):
        s = need['bass'][0]
        fig = s.get('figure', 'long')
        bass = eo._bass(chart, key, 0.0, rs.random())
        if fig == 'pump' and blk.get('bass_fig') and U != 6:
            bass = _pump_figure(bass, blk['bass_fig'], U, b.start)
        elif fig == 'pump':
            out = []
            for a, d, p in bass:
                t = a
                step = 0.5 if U == 4 else None
                while t < a + d - _EPS:
                    if U == 6:                              # (round o5, the scherzo's 3/4: the downbeat and the
                        out.append((t, 0.9, p))             # third beat - it was the 6/8 gallop across the bar)
                        if t + 2.0 < a + d - _EPS:
                            out.append((t + 2.0, 0.6, p))
                        t += 3.0
                    elif step:
                        out.append((t, 0.42, p))
                        t += step
                    else:                                   # (6/8: the gallop - a quarter, an eighth)
                        out.append((t, 0.9, p))
                        if t + 1.0 < a + d - _EPS:
                            out.append((t + 1.0, 0.42, p))
                        t += 1.5
            bass = out
        elif fig == 'walk':                         # (round o25: SHAPE3's chorale climax - a walking bass)
            bass = _walk_long(bass, chart, key, U)
        elif fig == 'long' and STATIC.get('walk') and blk.get('kind') in STATIC['walk'] and not b.peak and \
                b.length > STATIC['bars'] * blk.get('bar', U) - _EPS:
            bass = _walk_long(bass, chart, key, U)    # (round o11: a moving bass under the long lyrical blocks)
        elif fig == 'pluck':
            out = []
            pulse = 2.0 if U == 4 else 1.5
            for a, d, p in bass:
                t = a
                while t < a + d - _EPS:
                    out.append((t, min(0.9, a + d - t), p))
                    t += pulse
            bass = out
        if end:
            bass = _end_bass(bass, next(iter(s.get('pick') or {'cellos': 1})))
        if bass:
            b.add(orc.Line('bass', bass))
    if 'pedal' in need and blk['pedal']:
        b.add(orc.Line('pedal', blk['pedal']))
    if 'figuration' in need and not b.get('figuration'):
        s = need['figuration'][0]
        fig = s.get('figure', 'run')
        g = blk.get('grid', 0.25)
        lo, hi, floor = FIG_RANGE[fig]
        if mel:                                 # (round o8: the figuration under a high tune - FIG_RANGE)
            srt_ = sorted(p for _, _, p in mel)
            # (round o10 - o9's judges, CKNM: "12 bars of clarinet 16th scale runs" around the river's tune: under the
            # tune's lowest note where that leaves the span, else under its median)
            for ref in ((srt_[0], srt_[len(srt_) // 2]) if FIG_UNDER.get('low') else (srt_[len(srt_) // 2],)):
                top = min(hi, ref - FIG_UNDER['gap'])
                if top - max(floor, top - (hi - lo)) >= FIG_UNDER['span']:
                    lo, hi = max(floor, top - (hi - lo)), top
                    break
        if fig == 'wave':
            f1 = figuration(chart, key, 'wave', g, lo, hi, U, rs.random(), start=lo + 7)
            b.add(orc.Line('figuration', f1, voice='f1'))
            b.add(orc.Line('figuration', thirds_below(f1, chart, key), voice='f2'))
        else:                                   # ('wave1', round o3: one stream, no thirds - the source's colours)
            f1 = figuration(chart, key, 'wave' if fig == 'wave1' else 'run', g, lo, hi, U, rs.random(),
                            start=lo + 7)
            b.add(orc.Line('figuration', f1, voice='f1'))
    for i, slot in enumerate(need.get('colour', ())):
        if b.meta.get(f'colour{i}', 'none') == 'none':
            continue
        fig = slot.get('figure', 'arp')
        if blk.get('arrive'):                   # (round o8: the climax's arrival - ARRIVALS)
            fig = ARRIVAL_FIG[blk['arrive']].get(fig, fig)
            if fig is None:
                continue
        tun = orch.timpani_tuning(key)
        lines = []
        if fig == 'motto_timp':
            hits = []
            for a, d, p in blk['theme_song']:
                sym = next((sy for x, bb, sy in chart if x - _EPS <= a < x + bb - _EPS), None)
                if sym is None:
                    continue
                r = chord(sym).root % 12
                q = tun.get(r) or tun.get((r + 7) % 12)
                if q is not None:
                    hits.append((a, min(d, 1.0), q))
            lines = [(hits, 'hit')] if hits else []
        elif fig == 'roll_long':
            pc = chord(chart[0][2]).root % 12
            q = next((tun[x] for x in (pc, (pc + 7) % 12, Key(key).tonic % 12) if x in tun), None)
            lines = [([(b.start, b.length, q)], 'roll')] if q is not None else []
        elif fig == 'swell_cym':
            ln = min(b.length, 2 * U)
            lines = [([(b.end - ln, ln, orch.PERCUSSION_KEYS['cymbal_roll'])], 'sustain')]
        elif fig == 'crash_dry':                # (round o3: the crash on the climax's downbeat without the roll
            lines = [([(b.start, 4.0, orch.PERCUSSION_KEYS['crash'])], 'sustain')]     # into it)
        else:
            lines = eo._colour(fig, chart, {}, key, b, int(U), rs.random()) if fig != 'aah' else []
            if fig == 'arp' and STATIC:               # (round o9: the harp's ostinato at most STATIC bars)
                z_ = b.start + STATIC['bars'] * blk.get('bar', U)
                lines = [([n for n in ns if n[0] < z_ - _EPS], art) for ns, art in lines]
        for ns, art in lines:
            if ns:
                b.add(orc.Line('colour', ns, art=art, meta={'slot': i, 'figure': fig}))


BASS_FIGS = {'duple': {'eighths': 0.6, 'octaves': 1.0, 'quarters': 0.8, 'walk': 0.9, 'dotted': 0.6},
             'compound': {'gallop': 0.6, 'octaves': 1.0, 'dotted': 0.8, 'walk': 0.7}}
"""Round o10 (o9's judges: "the same repeated-eighth bass under whole pieces", bass_rep 0.28): the 'pump' bass's figure
drawn per block (never the block before's): repeated 8ths / the 6/8 gallop, 8ths in octaves, quarters, a walking
line (quarters, the last beat a step to the next chord's bass), the dotted quarter and 8th; the scherzo's 3/4 keeps its
downbeat and third beat (_pump_figure)."""


def _pump_figure(bass, how: str, U: float, start: float) -> list:
    """The bass line [(start, dur, pitch)] in BASS_FIGS figure `how` (U the bar: 4 duple, 3 compound)."""
    out = []
    srt = sorted(bass)
    duple = U == 4
    for i, (a, d, p) in enumerate(srt):
        nxt = srt[i + 1][2] if i + 1 < len(srt) else p
        z = a + d
        if how in ('eighths', 'octaves'):
            step = 0.5 if duple else 0.5
            t, j = a, 0
            while t < z - _EPS:
                q = p + 12 if how == 'octaves' and j % 2 == 1 and p + 12 <= 62 else p
                out.append((t, min(0.42, z - t), q))
                t, j = t + step, j + 1
        elif how == 'gallop':
            t = a
            while t < z - _EPS:
                out.append((t, min(0.9, z - t), p))
                if t + 1.0 < z - _EPS:
                    out.append((t + 1.0, 0.42, p))
                t += 1.5
        elif how in ('quarters', 'walk'):
            step = 1.0 if duple else 1.5
            t = a
            while t < z - _EPS:
                q = p
                if how == 'walk' and z - t <= step + _EPS and nxt != p and t > a + _EPS:
                    q = nxt + (1 if nxt < p else -1) * (2 if abs(nxt - p) > 2 else 1)     # (a step into the next)
                out.append((t, min(step * 0.85, z - t), q))
                t += step
        elif how == 'dotted':
            rh = ((0.0, 1.5), (1.5, 0.5), (2.0, 1.5), (3.5, 0.5)) if duple else ((0.0, 1.0), (1.0, 0.5),
                                                                                    (1.5, 1.0), (2.5, 0.5))
            t = start + U * math.floor((a - start) / U + _EPS)
            while t < z - _EPS:
                for on, du in rh:
                    x = t + on
                    if a - _EPS <= x < z - _EPS:
                        out.append((x, min(du * 0.9, z - x), p))
                t += U
        else:
            raise ComposeError(f"symphony: bass figure {how!r} unknown")
    return out


UNISON_KINDS = ('intro', 'mist', 'solo', 'slow')
"""The blocks whose texture's bass 'theme' figure doubles the tune in the bass (the opening call in unison / octaves);
elsewhere a tune on top gets the theme's rhythm on the chords' bass notes (_bass_in_rhythm - round o7: the coda's and
the closing hammer strokes stacked the tune in 5-6 octaves, the tuba and the basses on the melody)."""


def _bass_in_rhythm(theme, chart, key: str, seed) -> list:
    """The bass line (eo._bass) struck in the theme's rhythm: at every theme onset the bass note sounding there - round
    o8 (o7's orchestrators: "the tuba in repeated eighths"): a repeat of the note before it under BASS_HOLD beats after
    it is held instead."""
    bass = eo._bass(chart, key, 0.0, seed)
    out = []
    for a, d, _ in sorted(theme):
        q = next((p for x, dd, p in bass if x - _EPS <= a < x + dd - _EPS), None)
        if q is not None:
            if out and out[-1][2] == q and a - out[-1][0] < BASS_HOLD - _EPS:
                out[-1] = (out[-1][0], a + d - out[-1][0], q)
                continue
            out.append((a, d, q))
    return _mono(out) or bass


BASS_HOLD = 1.0
END_BASS = {'cellos': (43, 54), 'basses': (31, 42)}
"""Round o8 (o7's orchestrators: "the final chord needs a real low root - the basses and the tuba both on D3"): the
last block's bass line voice-led down to the final tonic in the window of its role (the cellos G2-F#3: the basses and
the tuba an octave under them; the basses themselves B1-F#2)."""


def _end_bass(bass, role: str) -> list:
    """The last block's bass line ending on its final note in END_BASS[role]'s window, the notes before it each moved
    by octaves to the nearest of the note after it."""
    if not bass:
        return bass
    lo, hi = END_BASS.get(role, END_BASS['cellos'])
    out = sorted(bass)
    a, d, q = out[-1]
    q = lo + (q - lo) % 12
    if q > hi:
        q -= 12
    res = [(a, d, q)]
    for a, d, p in reversed(out[:-1]):
        nxt = res[-1][2]
        p = min((p + 12 * k for k in range(-4, 5)), key=lambda x: (abs(x - nxt), x))
        res.append((a, d, p))
    return res[::-1]


LEAD_HINT = ('melody',)
"""The functions whose parts are the song's leads for the report (Song.lead_hint -> the render JSON's analysis.leads,
round o9): per block the role carrying the melody - the note-dynamics ear judges those as leads over their blocks and
no other part by its name (o8's gate lost 3 candidates to flat_dynamics on a tuba doubling, a violins II ostinato and
the trumpets' harmony, read as leads because of their names). () leaves the guess to the analysis."""

HOLD = {'seconds': 4.0, 'families': ('strings', 'woodwinds', 'brass'), 'restrike': ('harmony', 'inner', 'pedal')}
"""The longest note a sampled section holds (seconds): the SSO sustain samples are 4-5 s long and a note held past
its sample stops dead with a click (the gate's click rerolls, round o2: a trumpet's fermata landing, held violas and
basses) - a longer note ends at the limit with its release instead (it sounded no longer anyway). The families of
orch.ROLE_TRAITS. Round o10 (o9's judges, ECER: "bar 9 silent, -9 LU" - a 4-bar V under the mist cut after 4 s): a
'restrike' function's note (the held chords, the pedal) is struck again at the limit (on an 8th) instead."""

SHAPE = {'statement': 8.0, 'stream': 10.0, 'breath': 6.0, 'phrase': 6.0, 'ceiling': 110}
"""The parts' velocity shapes (the gate's flat_dynamics: the analysis judges every wind / brass / violin track as a
lead by its name - the motto's repeated notes in the trumpets, a flute stream, held trombone chords at one level):
'statement' +- this over each motto statement (a crescendo into its landing), 'stream' the figuration's swell per two
bars (+- this), 'breath' the winds' and brass's accompaniment the same per two bars, 'phrase' (round o4) a melody /
counter / doubling line outside the motto's statements the same (a cantilena, a trio, a chorale); 'ceiling' the
level a shape's top reaches at most - a loud part's shape moves down under it (round o4: ff recap doublings clipped
at 127 and flattened to 2.5 dB per phrase, the gate's rejects)."""

SLOW = {'tempo': 0.5, 'bars': {4: 1.0, 3: 0.7}}
"""The slow introduction (plan['set']['slow'], the allegro / vivace feels that allow it): at 'tempo' x the
movement's tempo, 'bars' bars of the motto augmented over a dominant-bound chain, a fermata, then the allegro
(round o6: 'bars' drawn per piece)."""


def _hold(notes, role: str, tm, restrike: bool = False) -> list:
    """The notes of a role with every note longer than HOLD['seconds'] ending there (a role outside HOLD's families
    as given); restrike (round o10, HOLD['restrike']: a chord part) - the note struck again there instead, until its
    written end."""
    if orch.ROLE_TRAITS.get(role, {}).get('family') not in HOLD['families']:
        return notes
    lim = HOLD['seconds']
    out = []
    for a, d, p in notes:
        z = a + d
        while True:
            t0 = tm.seconds_at(a)
            if tm.seconds_at(z) - t0 <= lim + _EPS:
                out.append((a, z - a, p))
                break
            lo, hi = a, z                           # (the beat where the limit falls)
            for _ in range(40):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if tm.seconds_at(mid) - t0 <= lim else (lo, mid)
            if not restrike:
                out.append((a, lo - a, p))
                break
            x = a + 0.5 * math.floor((lo - a) / 0.5 + _EPS) if lo - a >= 1.0 else lo   # (on an 8th: a new bow)
            out.append((a, x - a, p))
            a = x
    return out


PUMPING_ON = {'phrasing': 0.3}
"""Scale the automatic touch arc layered over the score map and SHAPE offsets. The piano-like 40..80 touch
range at romantic strength otherwise adds about 10 dB of repeated contour emphasis on exposed sampled winds.
Keep a small contour gesture, the written dynamics, SHAPE, accents, swells and all orchestration intact."""
PUMPING = None
"""Opt-in performance fix (genres.symphony_pumping); None preserves the pre-fix render exactly."""


def _shape_offs(p, stm, unit_bar: float, level=None):
    """The velocity offsets of a placed part (SHAPE): a function note -> offset, or None; level(beat) the score's
    dynamics map - the shape moved down where its top would pass SHAPE['ceiling']."""
    f = _shape_raw(p, stm, unit_bar)
    if f is None or level is None:
        return f
    top = max(SHAPE[x] for x in ('statement', 'stream', 'breath', 'phrase'))
    return lambda n: f(n) - max(0.0, level(n[0]) + p.off + top - SHAPE['ceiling'])


def _fugue_offs(offs, leads, voice: str, cs=(), entries=()):
    """FUGUE's entries in front: a part's offsets (offs: note -> steps, or None) + FUGUE 'lead' while its voice plays
    an entry, + 'other' while another voice does (leads [(voice, start, end)] in song beats); v2: + 'cs' (FUGUE_V2)
    while it plays the counter-subject (cs [(voice, start, end)]), + 'grow' per exposition entry begun (entries:
    their starts) - the exposition's crescendo."""
    V2 = FUGUE.get('v2') or {}

    def f(n):
        on = [v for v, a, z in leads if a - _EPS <= n[0] < z - _EPS]
        x = FUGUE['lead'] if voice in on else FUGUE['other'] if on else 0.0
        if cs and voice not in on and any(v == voice and a - _EPS <= n[0] < z - _EPS for v, a, z in cs):
            x = V2.get('cs', 0.0)
        if entries:
            x += V2.get('grow', 0.0) * max(0, sum(1 for a in entries if a <= n[0] + _EPS) - 1)
        return x + (offs(n) if offs is not None else 0.0)
    return f


def _shape_raw(p, stm, unit_bar: float):
    span = 2 * unit_bar
    if p.function in ('melody', 'counter', 'voice', 'doubling', 'bass') and stm:
        on = sorted(stm)
        # (round o4: a line outside the motto's statements - a cantilena, a trio, a chorale - arcs per two bars;
        # master's heroic allegro failed the gate 21 times on a flat trombones melody, a trio on the violins II 3)
        amp = SHAPE['phrase'] if p.function in ('melody', 'counter', 'doubling') else 0.0

        def f(n):
            a = n[0]
            for b0, b1 in on:
                if b0 - _EPS <= a < b1 - _EPS:
                    return SHAPE['statement'] * (2.0 * (a - b0) / max(_EPS, b1 - b0) - 1.0)
                if b0 > a:
                    break
            if not amp:
                return 0.0
            x = (a % span) / span
            return amp * (1.0 - 2.0 * abs(2.0 * x - 1.0))
        return f
    amp = SHAPE['stream'] if p.function == 'figuration' else \
        SHAPE['breath'] if orch.ROLE_TRAITS.get(p.role, {}).get('breath') and not p.line else 0.0
    if not amp:
        return None

    def g(n):
        x = (n[0] % span) / span
        return amp * (1.0 - 2.0 * abs(2.0 * x - 1.0))
    return g


IDIOM = {'timpani': (41, 52), 'timpani_low': 38, 'viola_low': 48, 'viola_share': 0.25,
         'horns': {'h1': (60, 72, 66), 'h2': (53, 67, 60)}, 'horn_off': -4.0}
"""Round o4's orchestration pass (_orchestra_pass; o3's orchestrators: timpani on A3 / B3 / Cb4, violas above the
violins, chamber climaxes without brass): the timpani tuned per block to the home's and the block's tonic /
dominant - the tonic in 'timpani' (F2-E3), the dominant the fifth below it (not under 'timpani_low', else the fourth
above), other notes left out; a viola part with 'viola_share' of its notes above every violin note sounding moves
down an octave (when it stays over 'viola_low'; else those notes alone); a chamber climax with no horns gets the
horns' sustained harmony ('horns' ranges, 'horn_off' dB)."""


def _timp_pitch(pc: int, tonic: int) -> int:
    T = 36 + tonic % 12
    if T < IDIOM['timpani'][0]:
        T += 12
    if pc % 12 == tonic % 12:
        return T
    return T - 5 if T - 5 >= IDIOM['timpani_low'] else T + 7


AUDIBLE = {'leads': ('violins1', 'flutes', 'oboes', 'clarinets', 'trumpets'),
           'under': ('harmony', 'inner', 'ostinato', 'colour', 'pedal', 'figuration'), 'share': 0.25,
           'counter_top': ('apex_augment', 'apex_augment_strings', 'apex_theme', 'apex_theme_strings',
                           'chorale_brass')}
"""Round o5 (o4's orchestrators: "the tune in violins1 around G4-A4 beneath the harp, the violas or the violins II"):
under a high lead (a melody on one of 'leads') the accompaniment parts ('under' functions, not lines) stay below the
melody note sounding - the harp's notes over it move down octaves (or are left out under its range), another part
with 'share' of its notes over the melody moves down an octave as a whole (when it fits its range; else those notes
alone). Round o10 (o9's judges, APPS: "held brass blocks under a violin line"; clx_top: the clarinets' and trumpets'
chord over the violins' canon in the augmented climaxes): in the 'counter_top' textures the counter on a lead role is
the line kept on top (the augmented melody sits under it in the brass); the running figuration is an 'under' part too
(CKNM / the river's stream moved over a violin tune by its section's sweet spot)."""


FOLD = {'near': 0.5, 'jump': 10, 'reach': 9}
"""Round o8 (o7's folds 1.63 a piece, the tells: the inner strings' and the harp's notes over the tune moved down an
octave one by one - an octave's leap inside a running figure): a note that must go under the tune takes the highest
tone of its chord under the tune within 'reach' semitones under it (a re-voicing, the figure's shape kept); without
one, an octave down - and where that leaps 'jump' semitones or more from a neighbour 'near' beats or closer, the
neighbour's pitch (under the tune), else it is left out (_lower)."""


def _lower(notes, over, lo: int, under, pcs_at=None, drop: bool = False) -> list:
    """notes (sorted) with the ones flagged `over` moved under under(a) (the tune's note there; None: no limit): FOLD. A
    note that cannot go over `lo` stays (a plain part's) or, drop, is left out (the harp's)."""
    ns = list(notes)
    out = []
    for i, ((a, d, q), o) in enumerate(zip(ns, over)):
        if not o:
            out.append((a, d, q))
            continue
        m = under(a)
        cs = pcs_at(a) if pcs_at else None
        cand = [y for y in range(q - 1, q - FOLD['reach'] - 1, -1)
                if cs is not None and y % 12 in cs and (m is None or y < m) and y >= lo]
        if cand:
            out.append((a, d, cand[0]))
            continue
        x = q - 12
        while m is not None and x >= m:
            x -= 12
        if x < lo and not drop:                # (no room under it: the note stays - a plain part's)
            out.append((a, d, q))
            continue
        near = []
        if out and a - out[-1][0] <= FOLD['near'] + _EPS:
            near.append((a - out[-1][0], out[-1][2]))
        if i + 1 < len(ns) and not over[i + 1] and ns[i + 1][0] - a <= FOLD['near'] + _EPS:
            near.append((ns[i + 1][0] - a, ns[i + 1][2]))
        if any(abs(x - y) >= FOLD['jump'] for _, y in near) or x < lo:
            alt = [y for _, y in sorted(near) if (m is None or y < m) and y >= lo]
            if not alt:
                continue
            x = alt[0]
        out.append((a, d, x))
    return out


UNFOLD = True
"""Round o10 (folds 0.88 -> 1.08 a piece in o9; the tells: a repeated-note ostinato whose notes over the tune went an
octave down while the next chord's stayed - 74 74 -> 62 62 | 73 73): after _lower a part's note that leaps FOLD['jump']
semitones or more from the note before it 'near' beats or closer takes the octave nearest that note (over the part's
lowest, under the tune) - the run stays in the register it was moved to until its own line comes back (_unfold)."""


def _lower_runs(notes, over, lo: int, under, cuts) -> tuple:
    """(notes, still over) - each chord's run of notes (between the chart's changes `cuts`) with a note over the tune
    moved down as one, by the smallest octave that takes all its over-notes under the tune and stays over `lo` (an
    accompaniment figure keeps its shape inside the chord; UNFOLD); a run no octave fits keeps its notes and flags."""
    ns, ov = list(notes), list(over)
    bounds = sorted(set(cuts))
    groups = {}
    for i, (a, _, _) in enumerate(ns):
        k = sum(1 for x in bounds if x <= a + _EPS)
        groups.setdefault(k, []).append(i)
    for idx in groups.values():
        if not any(ov[i] for i in idx):
            continue
        for sh in (-12, -24):
            ok = all(ns[i][2] + sh >= lo for i in idx) and all(
                (under(ns[i][0]) is None or ns[i][2] + sh < under(ns[i][0])) for i in idx if ov[i])
            if ok:
                for i in idx:
                    ns[i] = (ns[i][0], ns[i][1], ns[i][2] + sh)
                    ov[i] = False
                break
    return ns, ov


def _unfold(notes, lo: int, under) -> list:
    """notes (sorted) with every fast octave fold taken back to the octave nearest the note before (UNFOLD)."""
    out = []
    for a, d, q in sorted(notes):
        if out and a - out[-1][0] <= FOLD['near'] + _EPS and abs(q - out[-1][2]) >= FOLD['jump']:
            pq = out[-1][2]
            m = under(a)
            c = [q + 12 * k for k in (-2, -1, 1, 2) if q + 12 * k >= lo and (m is None or q + 12 * k < m)]
            y = min(c, key=lambda y_: abs(y_ - pq), default=None)
            if y is not None and abs(y - pq) < abs(q - pq):
                q = y
        out.append((a, d, q))
    return out


def _chart_pcs(chart):
    """a -> the pitch classes of the chord sounding at beat a in a block's chart (None outside it)."""
    def f(a):
        sym = next((s_ for x, d, s_ in chart if x - _EPS <= a < x + d - _EPS), None)
        return _cpcs(sym.split('/')[0]) if sym else None
    return f


def _audible(plan_o, score, table) -> None:
    """AUDIBLE, in place on plan_o.parts."""
    for b in score.blocks:
        ps = [p for p in plan_o.parts if p.block == b.name and p.notes]
        mel = [n for p in ps if p.function == 'melody' and p.role in AUDIBLE['leads'] for n in p.notes]
        if b.texture in AUDIBLE.get('counter_top', ()):     # (round o10: the canon's line over the augmentation)
            mel = [n for p in ps if p.function == 'counter' and p.role in AUDIBLE['leads'] for n in p.notes] or mel
        if not mel:
            continue

        def mel_at(a):
            on = [q for x, d, q in mel if x - _EPS <= a < x + d - _EPS]
            return min(on) if on else None
        for p in ps:
            if p.function not in AUDIBLE['under'] or p.line or p.role in ('percussion', 'timpani') or \
                    p.role not in table:
                continue
            lo = orc._n(table[p.role]['range'][0])
            over = []
            for a, _, q in p.notes:
                m = mel_at(a + 0.05)
                over.append(m is not None and q >= m)
            if not any(over):
                continue
            if p.role != 'harp' and sum(over) >= AUDIBLE['share'] * len(over) and \
                    min(q for _, _, q in p.notes) - 12 >= lo and p.role != 'violins2':
                p.notes = [(a, d, q - 12) for a, d, q in p.notes]   # (the violins II never as a whole under the
                p.shift -= 12                                       # violas)
            else:                             # (round o8: no octave folds inside a figure - _lower)
                # (round o9 - o9's judges, UZWK: "the final E minor chord keeps D#4 in the violins II": a note over
                # the tune held into the next chord is cut at the chord change - FOLD re-voices each piece to its
                # own chord, and a piece under the tune keeps its written pitch)
                cuts = sorted({x for x, _, _ in b.chart})
                ns_, ov_ = [], []
                for (a, d, q), o in zip(p.notes, over):
                    xs = [x for x in cuts if a + _EPS < x < a + d - _EPS] if o else []
                    if not xs:
                        ns_.append((a, d, q))
                        ov_.append(o)
                        continue
                    for x0, x1 in zip([a] + xs, xs + [a + d]):
                        m = mel_at(x0 + 0.05)
                        ns_.append((x0, x1 - x0, q))
                        ov_.append(m is not None and q >= m)
                srt = sorted(zip(ns_, ov_))
                n_, o_ = [n for n, _ in srt], [o for _, o in srt]
                if UNFOLD and p.role != 'harp' and p.function in ('ostinato', 'harmony', 'inner', 'figuration'):
                    n_, o_ = _lower_runs(n_, o_, lo, lambda a: mel_at(a + 0.05), cuts)
                p.notes = _lower(n_, o_, lo, lambda a: mel_at(a + 0.05), _chart_pcs(b.chart), drop=p.role == 'harp')
                if UNFOLD:                    # (round o10: no octave leap left inside the figure - _unfold)
                    p.notes = _unfold(p.notes, lo, lambda a: mel_at(a + 0.05))


def _strokes(plan_o, block: str, t0: float, bar: float, onsets) -> None:
    """The 'strokes' ending (STROKES): every pitched part's notes in the approach bar [t0, t0 + bar) cut into strokes
    on `onsets` (song beats from t0), each STROKES['len'] beats; the tonic after it as written."""
    ln = STROKES['len']
    for p in plan_o.parts:
        if p.block != block or not p.notes or p.role in ('percussion', 'timpani'):
            continue
        out = []
        for a, d, q in p.notes:
            z = min(a + d, t0 + bar)
            hits = [t0 + o for o in onsets if a - _EPS <= t0 + o < z - _EPS] if a < t0 + bar - _EPS else []
            if not hits:
                out.append((a, d, q))
                continue
            out += [(x, min(ln, z - x), q) for x in hits]
            if a + d > t0 + bar + _EPS:
                out.append((t0 + bar, a + d - t0 - bar, q))
        p.notes = out
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)


VLN_UNISON = 84
"""Round o10 (o9's judges, UZWK 72: "violins I + II in unison up to B6"): a violins II note on the violins I's pitch at
the same time above this (C6) plays an octave under it - the two sections split where the unison turns shrill."""


def _orchestra_pass(plan_o, score, home: str, size: str, roles, table=None) -> None:
    """IDIOM: the timpani, the violas, the chamber climax's horns; AUDIBLE (round o5) - in place on plan_o.parts."""
    if table is not None:                # (first: the violas' and the timpani's pass below sees where it moved)
        _audible(plan_o, score, table)
    if VLN_UNISON:                       # (round o10: the violins II an octave under the violins I's high unison)
        v1 = {(round(a, 2), q) for p in plan_o.parts if p.role == 'violins1' for a, _, q in p.notes}
        for p in plan_o.parts:
            if p.role == 'violins2' and any(q > VLN_UNISON and (round(a, 2), q) in v1 for a, _, q in p.notes):
                p.notes = [(a, d, q - 12 if q > VLN_UNISON and (round(a, 2), q) in v1 else q) for a, d, q in p.notes]
    blocks = {b.name: b for b in score.blocks}
    kh = Key(home).tonic
    vio = {}
    for p in plan_o.parts:
        if p.role in ('violins1', 'violins2'):
            vio.setdefault(p.block, []).extend(p.notes)
    for p in plan_o.parts:
        if p.role == 'timpani' and p.notes:
            kb = Key(blocks[p.block].key).tonic
            ok = {}
            for t_ in (kb, kh):                  # (the home's tuning first: a pc of both keys)
                ok[t_ % 12] = ok[(t_ + 7) % 12] = t_
            p.notes = [(a, d, _timp_pitch(q, ok[q % 12])) for a, d, q in p.notes if q % 12 in ok]
        elif p.role == 'violas' and p.notes and vio.get(p.block):
            vs = vio[p.block]

            def over(a, q):
                on = [y for x, dd, y in vs if x - _EPS <= a < x + dd - _EPS]
                return bool(on) and q > max(on)
            hi = [over(a, q) for a, _, q in p.notes]
            if not any(hi):
                continue
            if sum(hi) >= IDIOM['viola_share'] * len(hi) and min(q for _, _, q in p.notes) - 12 >= IDIOM['viola_low']:
                p.notes = [(a, d, q - 12) for a, d, q in p.notes]
                p.shift -= 12
            else:                                # (round o8: no octave folds inside a figure - _lower)
                srt = sorted(zip(p.notes, hi))
                def vtop(a):
                    on = [y for x, dd, y in vs if x - _EPS <= a < x + dd - _EPS]
                    return max(on) + 1 if on else None
                n_, h_ = [n for n, _ in srt], [h for _, h in srt]
                if UNFOLD and p.function in ('ostinato', 'harmony', 'inner'):
                    n_, h_ = _lower_runs(n_, h_, IDIOM['viola_low'], vtop, [x for x, _, _ in blocks[p.block].chart])
                p.notes = _lower(n_, h_, IDIOM['viola_low'], vtop, _chart_pcs(blocks[p.block].chart))
                if UNFOLD:
                    p.notes = _unfold(p.notes, IDIOM['viola_low'], vtop)
    if size == 'chamber' and 'horns' in roles:
        for b in score.blocks:
            if not b.peak or any(p.role == 'horns' and p.block == b.name and p.notes for p in plan_o.parts):
                continue
            mel = [n for x in b.get('melody') for n in x.notes]
            if not b.chart or not mel:
                continue
            for v, ns in sorted(eo._harmony(b.chart, mel, 2, b.key, ranges=IDIOM['horns']).items()):
                if ns:
                    plan_o.parts.append(orc.Part('horns', b.name, 'harmony', v, ns, 'sustain', IDIOM['horn_off'],
                                                 False))
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)


LOUDEST = {'peak': 'ff', 'cap': 'f', 'free': ('retrans',), 'pre': 'mf', 'pre_free': ('intro',), 'quiet': 'mf'}
"""Round o10 (o9's judges: "the loudest section mid-piece with a quieter recap", EMWY +2.7 LU in its episode, BLMX
+3.6 LU in its closing group; the reports: the coda the loudest section in 3 of 8 new pieces): the peak block's marks
at least 'peak' from its start, every other block's at most 'cap' (the build into the climax - 'free' kinds - keeps its
crescendo); a quiet climax keeps its plan. Round o11 (the masterpiece panel: "earlier tuttis 2-3 LU under the
summit"; the loudness proxy's margin 1.0 -> 2.1 LU over one set): 'pre' - the blocks before the peak at most this mark
(None: 'cap'), but the 'pre_free' kinds (the opening call keeps its boldness: a strong motto); 'quiet' - under a quiet
climax (its swell to f) every other block at most this mark (96102 / 96107: the closing group 2 LU over it)."""
_MARK_ORDER = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')


def _mark_max(m, floor: str):
    return m if m not in _MARK_ORDER or _MARK_ORDER.index(m) >= _MARK_ORDER.index(floor) else floor


def _mark_min(m, cap: str):
    return m if m not in _MARK_ORDER or _MARK_ORDER.index(m) <= _MARK_ORDER.index(cap) else cap


SUMMIT = {'over': 4, 'floor': 81, 'ceil': 96, 'brass': {'trumpets': (62, 84), 'trombones': (43, 70)},
          'horns': (53, 77), 'drop': 1.0, 'hand': ('oboes', 'clarinets', 'violins2', 'violas'),
          'fill': ('flutes', 'oboes', 'clarinets', 'bassoons', 'horns', 'trumpets', 'trombones', 'tuba', 'violins1',
                   'violins2', 'violas', 'cellos', 'basses', 'timpani')}
"""Round o12 (o11's judges, about 15 of 56: "the summit has no brass and no top" - JAUQ 60-72 7 of 7: "violins alone to
C7, no trumpets / trombones", WBTS "the highest note of the piece F#5", FUQW "never above B5"; tutti at the peak 0.42 of
the pieces): the peak block (_summit, before the reserve) - its violins I's top at least 'over' semitones over every
line before it and at 'floor' (A5) or higher: the violins' line an octave up where it stays under 'ceil' (C7), the
violins II keeping its first octave where they are free, else the line's closing 2-bar units (its last third or more)
up the octave; still short, the earlier blocks' phrases that reach the summit go an octave down (a phrase: notes
'drop' beats or less apart, breath to breath - never a fold inside a run - and the accompaniment that would cover
them with them; a role without the low octave hands the phrase to the first free 'hand' role that has it; the
development sits under the climax); the trumpets and the trombones on the
climax's melody (the transformed motto) where they do not carry it, each at the octave that holds most of its notes in
its tune range ('brass': lowest, highest - the notes outside rest, at least half sound) - a classical orchestra without
either: the horns ('horns'); and the fullest tutti - every 'fill' role the piece plays elsewhere doubles the peak's
melody / counter / bass nearest its sweet spot, never over the top line (but the flutes an octave over it), the
timpani on the chords' downbeats."""
TEX_RUN = {'bars': 8, 'span': 2, 'fns': ('ostinato', 'figuration', 'colour', 'bass', 'pedal', 'harmony', 'inner'),
           'skip': ('retrans', 'end', 'end_soft'), 'repair': True}
"""Round o12 (o11's judges, about 10 of 56: "long single-texture middles" - WBTS 71-138 "68 bars on one repeated-eighth
accompaniment", JAUQ 24-45 22 bars, RHDT 63-90): the accompaniment's rhythm as heard (every accompaniment part's onsets
in the bar on a 1/4-beat grid) never runs unchanged over 'bars' song bars outside the peak and the 'skip' kinds (the
build's drive, the last chords): the next 'span' bars thin it to every other pulse of its grid (8ths to quarters, the
6/8's to its dotted pulses) - a breath, then the figure again (_vary_runs; acc_run in symphony_metrics). Round o15b
('repair' - o14's 4 of 16 acc_run caps under best-of-1, runs of 10 / 12 bars: a run of 8 ending on a coarser grid had
its next bars thinned by the finer one - nothing changed - and the reset hid the new run's first bars; a 6/8's dotted
pulses thinned to themselves): after the pass, every run acc_runs still measures over 'bars' has the bars after its
8th thinned by its own grid (one all on the kept pulse: to the downbeat) - bit-identical where no run is too long."""
RT_DRIVE = {'roles': {'basses': (31, 45), 'cellos': (43, 55)}, 'timp': True}
"""Round o12 (o11's judges, YVCM 64-70 5 lenses: "the dominant pedal has no bass and no drive - violin scales over one
held horn Eb"): the retransition's last RT_PEDAL bars hold the dominant in the low strings ('roles' windows, where a
role does not sing a line there) and the timpani, struck - quarter pulses, then 8ths in the second half: the pedal
drives into the return under the motto's fragments (_rt_drive)."""


def _part_off(fn: str, role: str, line: bool, R: dict) -> float:
    """A part's velocity offset as the orchestrator gives it (orchestration._place): the function's, the powerful
    roles under it (RULES power_line / power_db)."""
    off = orc.FUNCTIONS[fn]['off']
    pw = orch.ROLE_TRAITS.get(role, {}).get('power', 1.0)
    return off - (R.get('power_line', 0.0) if line else R.get('power_db', 0.0)) * max(0.0, math.log2(pw))


def _octave_in(notes, lo: int, hi: int, prefer_high: bool = True):
    """The octave shift (-36 .. 24) that puts all notes inside [lo, hi] - the highest (or lowest) such - or None."""
    ks = [k for k in (24, 12, 0, -12, -24, -36) if notes and all(lo <= p + k <= hi for _, _, p in notes)]
    if not ks:
        return None
    return max(ks) if prefer_high else min(ks)


def _chord_part(chart, T: dict, ceiling: int, held: dict) -> list:
    """VOICING 'layers': a role's held chord tones over the peak's chart (T its idiom table row) - in its sweet spot
    (2 semitones' leeway), under the top line, voice-led from its last note, a chord tone the other chord roles do not
    hold yet where it has one (held {chart row: pcs})."""
    lo, hi = (orc._n(v) for v in T['range'])
    slo, shi = (orc._n(v) for v in T['sweet'])
    top, bot = min(hi, shi + 2, ceiling - 1), max(lo, slo - 2)
    out, prev = [], None
    for i, (a, d, sy) in enumerate(sorted(chart)):
        c = chord(sy.split('/')[0])
        pcs = {(c.root + x) % 12 for x in c.intervals}
        cand = [q for q in range(bot, top + 1) if q % 12 in pcs]
        if not cand or d <= _EPS:
            continue
        taken = held.setdefault(i, set())
        ref = prev if prev is not None else (slo + shi) / 2
        q = min(cand, key=lambda q_: (q_ % 12 in taken, abs(q_ - ref), q_))
        taken.add(q % 12)
        out.append((a, d, q))
        prev = q
    return out


def _summit(plan_o, score, roles, table, R: dict, bar: float = 4.0, voicing: str | None = None) -> None:
    """SUMMIT, in place on plan_o.parts (the peak block's violins, brass and tutti; bar: a song bar in beats);
    voicing 'layers' (SET_PLAN): the VOICING's chord roles hold the chords instead of doubling a line."""
    peak = next((b for b in score.blocks if b.peak), None)
    if peak is None or not SUMMIT:
        return
    layers = voicing == 'layers'
    names = [b.name for b in score.blocks]
    before = set(names[:names.index(peak.name)])
    unp = ('percussion', 'timpani', 'harp')
    lines_fn = ('melody', 'counter', 'voice', 'doubling')
    parts = plan_o.parts
    pre = max((q for p in parts if p.block in before and p.role not in unp and p.function in lines_fn
               for _, _, q in p.notes), default=0)
    pk = [p for p in parts if p.block == peak.name and p.notes]
    v1 = [p for p in pk if p.role == 'violins1' and p.function in ('melody', 'counter', 'doubling')]
    want = max(pre + SUMMIT['over'], SUMMIT['floor'])
    vtop = max((q for p in v1 for _, _, q in p.notes), default=0)
    if v1 and vtop < want:
        src = max(v1, key=lambda p: max(q for _, _, q in p.notes))
        orig = list(src.notes)
        if vtop + 12 <= SUMMIT['ceil']:          # (the whole line up the octave, the violins II keep its octave)
            src.notes = [(a, d, q + 12) for a, d, q in src.notes]
            src.shift += 12
            if 'violins2' in roles and not any(p.role == 'violins2' for p in pk):
                parts.append(orc.Part('violins2', peak.name, 'doubling', src.function if src.function != 'doubling'
                                      else src.voice, orig, src.art, _part_off('doubling', 'violins2', True, R),
                                      True, src.shift - 12, src.sf))
        else:                                    # (too high as a whole: the line's last 2-bar units - its climb -
            z = peak.end                         # up the octave, at least a third of the block)
            x = z
            while x - 2 * bar >= peak.start - _EPS and \
                    all(q + 12 <= SUMMIT['ceil'] for a, _, q in src.notes if x - 2 * bar - _EPS <= a < z):
                x -= 2 * bar
            if z - x >= peak.length / 3 - _EPS and \
                    max((q for a, _, q in src.notes if a >= x - _EPS), default=-99) + 12 >= want:   # (o14: a line
                src.notes = [(a, d, q + 12 if a >= x - _EPS else q) for a, d, q in src.notes]   # ending before x)
    vtop = max((q for p in parts if p.block == peak.name and p.role == 'violins1' for _, _, q in p.notes), default=0)
    if SUMMIT.get('drop') and vtop:
        thr = vtop - SUMMIT['over']
        for p in list(parts):
            if p.block not in before or not p.notes or p.role in unp or p.function not in lines_fn or                     p.role not in table or max(q for _, _, q in p.notes) <= thr:
                continue
            ns = sorted(p.notes)
            cut = [0] + [i for i in range(1, len(ns)) if ns[i][0] - ns[i - 1][0] >= SUMMIT['drop'] - _EPS] + [len(ns)]
            keep = []
            for i0, i1 in zip(cut, cut[1:]):        # (each phrase - breath to breath - that reaches the summit)
                ph = ns[i0:i1]
                if max(q for _, _, q in ph) <= thr:
                    keep += ph
                    continue
                x0, x1 = ph[0][0], ph[-1][0] + ph[-1][1]
                lo_ph = min(q for _, _, q in ph) - 12
                # (the octave down in the role - or handed to a free line role that has it: the flute's phrase to
                # the oboe; none: the phrase stays)
                to = next((r for r in (p.role,) + SUMMIT['hand'] if r in roles and r in table
                           and lo_ph >= orc._n(table[r]['range'][0])
                           and (r == p.role or not any(o.block == p.block and o.role == r and o.function in lines_fn
                                                       and any(a < x1 and a + d > x0 for a, d, _ in o.notes)
                                                       for o in parts))), None)
                if to is None:
                    keep += ph
                    continue
                low_ph = [(a, d, q - 12) for a, d, q in ph]
                if to == p.role:
                    keep += low_ph
                else:
                    arts = table[to].get('arts') or ()
                    parts.append(orc.Part(to, p.block, p.function, p.voice, low_ph,
                                          p.art if p.art in arts else ('sustain' if 'sustain' in arts else None),
                                          p.off, p.line, p.shift - 12,
                                          tuple(t_ for t_ in p.sf if x0 - _EPS <= t_ < x1)))
                top = max(q for _, _, q in low_ph)
                for o in parts:                     # (the accompaniment under it follows: the line stays the top)
                    if o.block != p.block or o.role in unp or o.function in lines_fn or o.role not in table:
                        continue
                    lo_ = orc._n(table[o.role]['range'][0])
                    o.notes = [(a, d, q - 12 if x0 <= a < x1 and q >= top and q - 12 >= lo_ else q)
                               for a, d, q in o.notes]
            p.notes = keep
    pk = [p for p in parts if p.block == peak.name and p.notes]
    mel = max((p for p in pk if p.function == 'melody'), key=lambda p: len(p.notes), default=None)
    brass = dict(SUMMIT['brass'])
    if SUMMIT.get('horns') and not any(r in roles for r in brass):
        brass = {'horns': SUMMIT['horns']}
    if mel is not None:
        for role, (lo, hi) in brass.items():
            if role not in roles or any(p.role == role and p.function in lines_fn for p in pk):
                continue
            if layers and role not in VOICING['brass'] and any(r in roles for r in VOICING['brass']):
                continue                       # (round o18b: the trombones hold the chords - VOICING)
            # (the octave that holds most of the line in the tune range - the brass on the statements it can sing)
            k, ns = max(((k_, [(a, d, q + k_) for a, d, q in mel.notes if lo <= q + k_ <= hi])
                         for k_ in (12, 0, -12, -24)), key=lambda x: (len(x[1]), x[0]))
            if len(ns) < max(2, len(mel.notes) / 2):
                continue
            parts.append(orc.Part(role, peak.name, 'doubling', 'melody', ns, 'sustain',
                                  _part_off('doubling', role, True, R), True, mel.shift + k,
                                  tuple(t_ for t_ in mel.sf if any(abs(a - t_) < 1e-3 for a, _, _ in ns))))
    used = {p.role for p in parts if p.notes}
    here = {p.role for p in parts if p.block == peak.name and p.notes}
    pk = [p for p in parts if p.block == peak.name and p.notes and p.role not in unp]
    top_line = max((p for p in pk if p.function in ('melody', 'counter')),
                   key=lambda p: sum(q for _, _, q in p.notes) / len(p.notes), default=None)
    ceiling = max((q for _, _, q in top_line.notes), default=127) if top_line else 127
    cands = [p for p in pk if p.function in ('melody', 'counter', 'bass')]
    held = {}                                  # (layers: the chord tones taken per chart row)
    for role in SUMMIT['fill']:
        if role not in roles or role not in used or role in here or role not in table:
            continue
        if layers and role in VOICING['chords']:
            ns = _chord_part(peak.chart, table[role], ceiling, held)
            if ns:
                parts.append(orc.Part(role, peak.name, 'harmony', '', ns, 'sustain' if 'sustain' in
                                      (table[role].get('arts') or ()) else None,
                                      _part_off('harmony', role, False, R), False))
                here.add(role)
            continue
        if role == 'timpani':
            hits = [(a, min(1.0, d), chord(sy.split('/')[0]).root % 12 + 48) for a, d, sy in peak.chart]
            if hits:
                parts.append(orc.Part('timpani', peak.name, 'colour', '', hits, 'hit',
                                      _part_off('colour', 'timpani', False, R), False))
            continue
        lo, hi = (orc._n(v) for v in table[role]['range'])
        slo, shi = (orc._n(v) for v in table[role]['sweet'])
        mid = (slo + shi) / 2.0
        best = None
        for p in cands:
            for k in (-24, -12, 0, 12, 24):
                ns = [(a, d, q + k) for a, d, q in p.notes]
                if not all(lo <= q <= hi for _, _, q in ns):
                    continue
                # (never over the top line - but the flutes an octave over it: the summit's triple octave)
                if max(q for _, _, q in ns) > ceiling and not (role == 'flutes' and p is top_line and k == 12):
                    continue
                med = sorted(q for _, _, q in ns)[len(ns) // 2]
                key_ = (abs(med - mid) + (0 if p.function in ('melody', 'counter') else 3), p.function, k)
                if best is None or key_ < best[0]:
                    best = (key_, p, k, ns)
        if best is None:
            continue
        _, p, k, ns = best
        line = p.function in ('melody', 'counter')
        fn = 'doubling' if line else p.function
        arts = table[role].get('arts') or ()
        art = p.art if p.art in arts else ('sustain' if 'sustain' in arts else None)
        parts.append(orc.Part(role, peak.name, fn, p.function if line else p.voice, ns, art,
                              _part_off(fn, role, line, R), line, p.shift + k, p.sf if line else ()))
        here.add(role)
    plan_o.notes = sum(len(p.notes) for p in parts)


def _set_plan_pass(plan_o, mat, k: float, ending) -> None:
    """SET_PLAN, in place on plan_o.parts: a build's general pause (GESTURES 'silence': every part silent in the
    block's 'silence' span - a note sounding into it cut) and END_COLOURS (the harp out of the codas, the timpani out
    of the last block but where the ending strikes it)."""
    kinds = {b['name']: b['kind'] for b in mat['blocks']}
    E = END_COLOURS if SET_PLAN.get('endings') else None
    for blk in mat['blocks']:
        if not blk.get('silence'):
            continue
        a, z = blk['silence'][0] * k, blk['silence'][1] * k
        for p in plan_o.parts:
            p.notes = [(x, min(d, a - x), q) for x, d, q in p.notes if x < a - 0.05] + \
                [n for n in p.notes if n[0] >= z - _EPS]
    v3 = bool(SET_PLAN.get('v3'))
    if SET_PLAN.get('v2') and (POST_HARP or v3):
        # (round o19a: no harp after the climax; a harp left with too few notes taken out - POST_HARP; round o20:
        # gated on its level, its parts removed - POST_HARP_V3, below)
        order = [b['name'] for b in mat['blocks']]
        pi = next((i for i, b in enumerate(mat['blocks']) if b['peak']), None)
        after = set(order[pi + 1:]) if pi is not None else set()
        for p in plan_o.parts:
            if p.role == 'harp' and p.block in after:
                p.notes = []
        if not v3 and sum(len(p.notes) for p in plan_o.parts if p.role == 'harp') < POST_HARP['min']:
            for p in plan_o.parts:
                if p.role == 'harp':
                    p.notes = []
    if E:
        for p in plan_o.parts:
            kd = kinds.get(p.block)
            if (p.role == 'harp' and kd in E['harp']) or \
                    (p.role == 'timpani' and kd in E['timpani'] and ending not in E['keep_timp']):
                p.notes = []
    if v3:
        # (round o20: a role left without notes, or a harp under POST_HARP_V3's notes, out of the band - no empty
        # track: silent_node)
        cnt = {}
        for p in plan_o.parts:
            cnt[p.role] = cnt.get(p.role, 0) + len(p.notes)
        gone = {r for r, c in cnt.items() if c == 0 or (r == 'harp' and c < POST_HARP_V3['min'])}
        plan_o.parts = [p for p in plan_o.parts if p.role not in gone]
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)


def _rt_drive(plan_o, score, mat, k: float, bpb: float, home: str, roles) -> None:
    """RT_DRIVE, in place on plan_o.parts."""
    if not RT_DRIVE or not RT_PEDAL:
        return
    i = next((j for j, x in enumerate(score.blocks) if x.peak), None)
    if not i or mat['blocks'][i - 1]['kind'] != 'retrans':
        return
    b, blk = score.blocks[i - 1], mat['blocks'][i - 1]
    if SET_PLAN and SET_PLAN.get('builds') and not GESTURES.get(blk.get('gesture'), {}).get('drive'):
        return                                # (round o18b: the struck pedal is the 'pulse' build's only)
    z = b.end - (1.0 * k if blk.get('gp') == 'gp' else 0.0)
    a0 = max(b.start, b.end - RT_PEDAL['bars'] * bpb)
    if z - a0 < bpb - _EPS:
        return
    dom = (Key(home).tonic + 7) % 12
    duple = abs(bpb - round(bpb)) < _EPS and int(round(bpb)) % 2 == 0
    pulse = 1.0 if duple else 1.5
    mid = a0 + (z - a0) / 2

    def drive(lo_, hi_):
        out, x = [], a0
        while x < z - _EPS:
            g = pulse if x < mid - _EPS else 0.5
            out.append((x, min(g * 0.8, z - x), lo_))
            x += g
        return out
    parts = plan_o.parts
    sing = {p.role for p in parts if p.block == b.name and p.function in ('melody', 'counter', 'voice') and
            any(a0 - _EPS <= a < z for a, _, _ in p.notes)}
    if orc.TEXTURES.get(b.texture, {}).get('theme') == 'bass':      # (the motto in the bass build: it sings there)
        sing |= set(RT_DRIVE['roles'])
    for role, (lo, hi) in RT_DRIVE['roles'].items():
        if role not in roles or role in sing:
            continue
        q = _near({dom}, (lo + hi) / 2, lo, hi)
        for p in parts:
            if p.block == b.name and p.role == role:
                p.notes = [n for n in p.notes if not (a0 - _EPS <= n[0] < z)]
                p.notes = [(a, min(d, a0 - a), q_) if a + d > a0 + _EPS and a < a0 else (a, d, q_)
                           for a, d, q_ in p.notes]
        parts.append(orc.Part(role, b.name, 'pedal', '', drive(q, q), 'staccato', -6.0, False))
    if RT_DRIVE.get('timp') and 'timpani' in roles:
        for p in parts:
            if p.block == b.name and p.role == 'timpani':
                p.notes = [n for n in p.notes if not (a0 - _EPS <= n[0] < z)]
        parts.append(orc.Part('timpani', b.name, 'colour', '', drive(dom + 36, dom + 36), 'hit', -8.0, False))
    plan_o.notes = sum(len(p.notes) for p in parts)


def _acc_sig(parts, a0: float, bpb: float) -> frozenset:
    return frozenset(round((a - a0) * 4) / 4 for p in parts for a, _, _ in p.notes if a0 - _EPS <= a < a0 + bpb - _EPS)


def _acc_parts(plan_o):
    return [p for p in plan_o.parts if p.notes and p.function in TEX_RUN['fns'] and p.role != 'percussion']


def acc_runs(plan_o, score, kinds: dict, bpb: float) -> list:
    """[(first bar, bars)] of the accompaniment's unchanged runs (TEX_RUN: the same onset grid bar after bar, outside
    the peak and the 'skip' kinds)."""
    acc = _acc_parts(plan_o)
    out = []
    for b in score.blocks:
        if b.peak or kinds.get(b.name) in TEX_RUN['skip']:
            out.append(None)
            continue
        ps = [p for p in acc if p.block == b.name]
        for j in range(int(round(b.length / bpb))):
            out.append(_acc_sig(ps, b.start + j * bpb, bpb))
    runs, run, start = [], 0, 0
    for i, sg in enumerate(out + [None]):
        if sg and i and out[i - 1] == sg:
            run += 1
            continue
        if run:
            runs.append((start, run + 1))
        run, start = 0, i
    return runs


UNFOLD_ALL = ('ostinato', 'figuration')
"""Round o12 (folds 0.79 -> 1.54 a piece over o10 / o11, the tells: the violins II's / violas' pulse leaping a
tenth at a chord change - 74 74 | 64 64 - where no note went under the tune): every 'UNFOLD_ALL' part of the
finished orchestration through _unfold (the octave nearest the note before, under the block's lines, over the role's
lowest), then _refold (a leap no single octave mends: the run after it, or the one before, moved as a whole)."""


def _unfold_all(plan_o, table) -> None:
    """UNFOLD_ALL, in place on plan_o.parts."""
    if not UNFOLD_ALL:
        return
    lines = {}
    for p in plan_o.parts:
        if p.notes and p.function in ('melody', 'counter', 'voice') and p.role not in ('percussion', 'timpani'):
            lines.setdefault(p.block, []).extend(p.notes)
    for p in plan_o.parts:
        if not p.notes or p.function not in UNFOLD_ALL or p.role not in table:
            continue
        ln = sorted(lines.get(p.block, []))

        def under(a, ln=ln):
            qs = [q for x, d, q in ln if x - _EPS <= a < x + d - _EPS]
            return min(qs) if qs else None
        p.notes = _refold(_unfold(p.notes, orc._n(table[p.role]['range'][0]), under),
                          orc._n(table[p.role]['range'][0]), under)


def _refold(notes, lo: int, under) -> list:
    """notes (sorted) whose remaining fast folds (FOLD) move a whole run - the notes after the leap up to the next
    breath, else the ones before it back to the last, else the repeated notes before / after it - an octave toward the
    other side, where it stays over lo, under the lines and makes no new fold at its seams."""
    ns = sorted(notes)
    n = len(ns)
    near = lambda i, j: 0 <= i < n and 0 <= j < n and abs(ns[j][0] - ns[i][0]) <= FOLD['near'] + _EPS  # noqa: E731

    def leap(i, j, xs):
        return near(i, j) and abs(xs[j][2] - xs[i][2]) >= FOLD['jump']
    i = 1
    while i < n:
        if not leap(i - 1, i, ns):
            i += 1
            continue
        sh = 12 if ns[i - 1][2] > ns[i][2] else -12
        z = i
        while z + 1 < n and near(z, z + 1) and abs(ns[z + 1][2] - ns[z][2]) < FOLD['jump']:
            z += 1
        a0 = i - 1
        while a0 - 1 >= 0 and near(a0 - 1, a0) and abs(ns[a0][2] - ns[a0 - 1][2]) < FOLD['jump']:
            a0 -= 1
        z1 = i                                  # (the repeated notes on each side: 74 74 74 | 64 64)
        while z1 + 1 <= z and ns[z1 + 1][2] == ns[i][2]:
            z1 += 1
        b1 = i - 1
        while b1 - 1 >= a0 and ns[b1 - 1][2] == ns[i - 1][2]:
            b1 -= 1
        done = False
        for lo_i, hi_i, k in ((i, z, sh), (a0, i - 1, -sh), (b1, i - 1, -sh), (i, z1, sh)):
            xs = list(ns)
            for m in range(lo_i, hi_i + 1):
                xs[m] = (xs[m][0], xs[m][1], xs[m][2] + k)
            ok = all(xs[m][2] >= lo and (under(xs[m][0]) is None or xs[m][2] < under(xs[m][0]))
                     for m in range(lo_i, hi_i + 1))
            if ok and not leap(lo_i - 1, lo_i, xs) and not leap(hi_i, hi_i + 1, xs):
                ns, done = xs, True
                break
        i = (z if done else i) + 1
    return ns


def _thin_bar(acc, bj, x0: float, bpb: float, sg, exact: bool = False) -> None:
    """TEX_RUN's thinning of one bar (block bj, from x0) after a run of the onset grid `sg`: the onsets off twice the
    grid's finest pulse out, the note before tied over them (held bars re-struck at the half instead); exact (the
    repair): a grid all on the kept pulse (the 6/8's dotted quarters) thins to the downbeat."""
    compound = abs(bpb - 3.0) < _EPS
    gaps = sorted(y - x for x, y in zip(sorted(sg), sorted(sg)[1:]) if y - x > _EPS)
    g = gaps[0] if gaps else bpb
    keep = 1.5 if compound and g >= 0.5 - _EPS else 2 * g
    if exact and gaps and all(abs((x + _EPS) % keep) < 0.02 for x in sg):
        keep = bpb
    h = 1.5 if compound else bpb / 2
    for p in acc:
        if p.block != bj.name:
            continue
        inb = lambda n: x0 - _EPS <= n[0] < x0 + bpb - _EPS     # noqa: E731
        if not gaps:                            # (held bars: each held note re-struck at the half instead)
            p.notes = sorted(x for n in p.notes for x in (
                ((n[0], h, n[2]), (n[0] + h, n[1] - h, n[2])) if inb(n) and abs(n[0] - x0) < 0.02
                and n[1] > h + 0.1 else (n,)))
            continue
        out = []                                # (the off-grid onsets out, the note before tied over them)
        for n in sorted(p.notes):
            if inb(n) and abs((n[0] - x0 + _EPS) % keep) >= 0.02:
                if out and abs(out[-1][0] + out[-1][1] - n[0]) < 0.3 and out[-1][2] == n[2]:
                    out[-1] = (out[-1][0], n[0] + n[1] - out[-1][0], n[2])
                elif out and abs(out[-1][0] + out[-1][1] - n[0]) < 0.3 and out[-1][0] >= x0 - _EPS:
                    out[-1] = (out[-1][0], min(n[0] + n[1], x0 + bpb) - out[-1][0], out[-1][2])
                continue
            out.append(n)
        p.notes = out


def _vary_runs(plan_o, score, kinds: dict, bpb: float) -> None:
    """TEX_RUN, in place: the accompaniment thinned for TEX_RUN['span'] bars after every TEX_RUN['bars'] bars of one
    onset grid (_thin_bar); then TEX_RUN 'repair' (round o15b): a run acc_runs still measures longer than 'bars' has
    the bars after its 'bars'-th thinned by the run's grid, until none is (nothing changes where none is)."""
    if not TEX_RUN:
        return
    acc = _acc_parts(plan_o)
    bars = []                                  # (block, bar start)
    for b in score.blocks:
        ok = not (b.peak or kinds.get(b.name) in TEX_RUN['skip'])
        bars += [(b if ok else None, b.start + j * bpb) for j in range(int(round(b.length / bpb)))]
    run, prev, i = 0, None, 0
    while i < len(bars):
        b, a0 = bars[i]
        if b is None:
            run, prev, i = 0, None, i + 1
            continue
        ps = [p for p in acc if p.block == b.name]
        sg = _acc_sig(ps, a0, bpb)
        run = run + 1 if sg and sg == prev else (1 if sg else 0)
        prev = sg
        if run < TEX_RUN['bars']:
            i += 1
            continue
        for j in range(1, TEX_RUN['span'] + 1):
            if i + j >= len(bars) or bars[i + j][0] is None:
                break
            _thin_bar(acc, bars[i + j][0], bars[i + j][1], bpb, sg)
        run, prev = 0, None
        i += TEX_RUN['span'] + 1
    if not TEX_RUN.get('repair'):
        return
    rb = []                                    # (acc_runs' index: one entry per bar, one per skipped block)
    for b in score.blocks:
        if b.peak or kinds.get(b.name) in TEX_RUN['skip']:
            rb.append(None)
        else:
            rb += [(b, b.start + j * bpb) for j in range(int(round(b.length / bpb)))]
    bars = rb
    for _ in range(64):
        long_ = [(s_, n_) for s_, n_ in acc_runs(plan_o, score, kinds, bpb) if n_ > TEX_RUN['bars']]
        if not long_:
            return
        s_, n_ = long_[0]
        i = s_ + TEX_RUN['bars'] - 1               # (the run's last allowed bar)
        b, a0 = bars[i]
        sg = _acc_sig([p for p in acc if p.block == b.name], a0, bpb)
        for j in range(1, min(TEX_RUN['span'], s_ + n_ - 1 - i) + 1):
            _thin_bar(acc, bars[i + j][0], bars[i + j][1], bpb, sg, exact=True)


EVENT_ROLES = (('trumpets', ('t', 't1')), ('horns', ('m2', 'm1')), ('trombones', ('m1', 'b+')), ('tuba', ('b',)),
               ('basses', ('b',)), ('cellos', ('b',)), ('violas', ('m1',)), ('violins2', ('m2',)),
               ('violins1', ('t',)), ('bassoons', ('b+',)), ('clarinets', ('m2',)), ('oboes', ('t1',)),
               ('flutes', ('t+',)))
"""CHROMA_EVENT's tutti (_event_tutti): per role the chorale's voices it doubles in its own octave ('b' the bass, 'b+'
an octave over it, 'm1' / 'm2' the lowest / second upper voice, 't1' the one under the top, 't' the top, 't+' an
octave over it) - the brass first, then the strings and the winds; a role that sings the melody there keeps it."""
EVENT_OFF = 3.0
"""The tutti chords' velocity over the harmony function's offset (_event_tutti)."""


def _event_tutti(plan_o, score, ev: dict, block: str, k: float, roles, table, R: dict) -> None:
    """CHROMA_EVENT's chords on the whole orchestra, in place on plan_o.parts: in the event's span ('cut') every part
    of the block but the melody and the percussion gives way (the timpani keep the notes in the chord there); each
    EVENT_ROLES role the piece plays doubles its chorale voices in its range (the sweet range first) as held chords -
    never more roles in the block than the peak sounds (tutti_peak), never over the summit's top (top_peak; before
    the peak 2 semitones under it: pre_semis)."""
    a, z = ev['cut'][0] * k, ev['cut'][1] * k
    chords = [(x * k, d * k, sym, b, up) for x, d, sym, b, up in ev['chords']]

    def pcs_at(x):
        for c0, d, _, b, up in chords:
            if c0 - _EPS <= x < c0 + d - _EPS:
                return {q % 12 for q in [b] + list(up)}
        return set()

    def cut(ns):
        out = []
        for x, d, q in ns:
            if x < a - _EPS:
                out.append((x, min(d, a - x), q))
                if x + d > z + _EPS:
                    out.append((z, x + d - z, q))
            elif x >= z - _EPS:
                out.append((x, d, q))
            elif x + d > z + 0.5:
                out.append((z, x + d - z, q))
        return out
    mel_roles = set()
    for p in plan_o.parts:
        if p.block != block or not p.notes or p.role == 'percussion':
            continue
        if p.function == 'melody':
            if any(a - _EPS <= x < z for x, _, _ in p.notes):
                mel_roles.add(p.role)
            continue
        if p.role == 'timpani':
            p.notes = [nt for nt in p.notes if not (a - _EPS <= nt[0] < z - _EPS) or nt[2] % 12 in pcs_at(nt[0])]
            continue
        p.notes = cut(p.notes)
    peak = next((x for x in score.blocks if x.peak), None)
    cap = len({p.role for p in plan_o.parts if p.notes and peak and p.block == peak.name} - set(TUTTI_SKIP)) \
        if peak else 99
    have = {p.role for p in plan_o.parts if p.block == block and p.notes} - set(TUTTI_SKIP)
    nup = len(chords[0][4])
    # (under the summit: the peak's highest note stays the piece's - top_peak; a block before it 2 semitones under
    # it - pre_semis)
    names = [x.name for x in score.blocks]
    ceil_ = 127
    if peak is not None:
        ptop = max((q for p in plan_o.parts if p.block == peak.name and p.notes and
                    p.role not in ('percussion', 'timpani', 'harp') for _, _, q in p.notes), default=127)
        ceil_ = ptop - 2 if names.index(block) < names.index(peak.name) else ptop

    def line(v):
        out = []
        for x, d, _, b, up in chords:
            q = {'b': b, 'b+': b + 12, 'm1': up[0], 'm2': up[1], 't1': up[nup - 2], 't': up[-1], 't+': up[-1] + 12}[v]
            out.append((x, d, q))
        return out
    for role, vs in EVENT_ROLES:
        if role not in roles or role not in table or role in mel_roles:
            continue
        if role not in have and len(have) >= cap:
            continue
        added = False
        for v in vs:
            ns = line(v)
            sh = None
            for rk in ('sweet', 'range'):
                lo, hi = (orc._n(x) for x in table[role][rk])
                sh = next((s_ for s_ in (0, 12, -12, 24, -24) if all(lo <= q + s_ <= min(hi, ceil_)
                                                                     for _, _, q in ns)), None)
                if sh is not None:
                    break
            if sh is None:
                continue
            plan_o.parts.append(orc.Part(role, block, 'harmony', f"ev_{v}", [(x, d, q + sh) for x, d, q in ns],
                                         'sustain', _part_off('harmony', role, False, R) + EVENT_OFF, False))
            added = True
        if added:
            have.add(role)
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)


def _event_marks(sc, mat: dict, k: float) -> None:
    """CHROMA_EVENT's dynamics on the Score's map (before any part is written): the final chord at 'level' ('soft' in
    a soft ending) to the block's end, the chain at 'chain_level' and its last chromatic chord at 'chain_top', then
    subito the map's own level again."""
    for blk in mat['blocks']:
        ev = blk.get('event')
        if not ev:
            continue
        a, z = ev['cut'][0] * k, ev['cut'][1] * k
        lv = CHROMA_EVENT['soft' if ev.get('soft') else 'level'] if ev['kind'] == 'final' else \
            CHROMA_EVENT['chain_level']
        before, after = sc.level(a - 0.05), sc.level(z + 0.01)
        pts = [(a - 0.05, before), (a, lv, 'step')]
        if ev['kind'] == 'chain' and CHROMA_EVENT.get('chain_top'):
            c0 = ev['top_at'] * k
            pts += [(c0 - 0.05, lv), (c0, CHROMA_EVENT['chain_top'], 'step'), (z - 0.05, CHROMA_EVENT['chain_top'])]
        else:
            pts.append((z - 0.05, lv))
        if ev['kind'] == 'chain':               # (the arrival on V loud too, then the pedal's own level)
            x_, d_ = ev['chords'][-1][:2]
            z = (x_ + d_) * k
            after = sc.level(z + 0.01)
            pts[-1] = (z - 0.05, pts[-1][1])
        pts.append((z, after, 'step'))
        sc.mark(pts)


# ------------------------------------------------------------------------------------------------ playing techniques

TECH = None
"""Round o23 (HUMAN_FEEDBACK 2026-10-24: "I feel techniques are missing, e.g. plucked strings" - 8 master pieces:
strings 65 % sustain, 24 % staccato, pizzicato 2 % and only in the basses; never col legno, harmonics, trills, mutes,
a glissando): the orchestra's playing techniques as musical EVENTS, each tied to a dramatic function and a place in
the form (TECHNIQUES). Per piece a ranking of the palette (tech_rank: the feel's affinity, the set's memory - a
technique featured in the slots before is drawn less), the first TECH['feature'] that the piece's blocks allow are
written (_tech_pre: the pizzicato choir is a texture, chosen before the orchestration; _tech_pass: the others change
the orchestrated parts). None = off (bit-identical); genres.symphony_tech switches it with the set draw and the band's
technique sounds (orch.TECH_SOUNDS: the mutes, col legno / harmonics levels)."""
TECH_ON = {'feature': 4, 'memory': (0.15, 0.45), 'trill_s': 0.085, 'gliss_s': 0.75, 'pizz_blocks': 1,
           'pizz_reach': 0}
"""TECH on: techniques per piece, the weight of one featured by the slot before / the one before that, the trill's
note length (s), the harp glissando's length (s), the pizzicato-choir blocks per piece, how far past the featured
ranks the pizzicato choir is still placed (it is chosen before the parts exist)."""

_STR = ('violins1', 'violins2', 'violas', 'cellos', 'basses')
_WW = ('flutes', 'oboes', 'clarinets', 'bassoons')
_ACC = ('harmony', 'inner', 'pedal', 'ostinato')
_DEV = ('dev_dialogue', 'dev_fugato', 'episode')
_SOFT_END = ('coda_soft', 'end_soft')

TECHNIQUES = {
    # name: the dramatic function (fn), where it goes (kinds: block kinds; 'peak' / 'pre_peak' / 'soft' / 'fast'
    # conditions), the feels' affinity (w x feel weight; a feel missing = 1.0, 0 = never)
    'pizz_choir': {'fn': 'lightness and contrast: the whole string choir plucked under a woodwind tune (the trio / '
                         'episode / second-theme texture of the classic pizzicato scherzo)',
                   'kinds': ('trio', 't2', 'episode', 'var', 't2b', 'recap2', 'refrain', 'close', 'river'),
                   'w': 1.8, 'feels': {'scherzo': 1.6, 'vivace': 1.3, 'andante': 1.0, 'river': 0.9, 'allegro': 0.8}},
    'pizz_walk': {'fn': 'motion under a held texture: the basses (and cellos) walk pizzicato in beats',
                  'kinds': ('t1', 't1b', 'refrain', 'dev_dialogue', 'episode', 'var', 'close', 'trans', 'river',
                            'recap2', 't2', 'trio'),
                  'w': 1.0, 'feels': {'andante': 1.3, 'river': 1.0, 'scherzo': 0.6}},
    'trem_build': {'fn': 'tension before the climax: the strings\' held harmony tremolo under the build\'s crescendo',
                   'kinds': ('retrans',), 'w': 1.0, 'feels': {'allegro': 1.4, 'scherzo': 1.1}},
    'measured_trem': {'fn': 'agitation in the development: held string chords as repeated (measured) notes',
                      'kinds': _DEV + ('retrans', 'var'), 'w': 0.9,
                      'feels': {'allegro': 1.5, 'vivace': 1.2, 'river': 0.8, 'andante': 0.6}},
    'trill': {'fn': 'brilliance on the summit and the cadence: a woodwind trill on the climax\'s held notes (flutes '
                    'over the tutti) and on the cadence\'s penultimate note',
              'kinds': ('peak', 't1', 'close', 'recap', 'coda', 't2'), 'w': 1.2,
              'feels': {'allegro': 1.2, 'vivace': 1.2}},
    'harp_gliss': {'fn': 'an arrival announced: a harp glissando up into the climax (and a return)',
                   'kinds': ('peak', 'recap', 'refrain', 'river'), 'w': 1.0,
                   'feels': {'river': 1.5, 'andante': 1.3, 'scherzo': 0.6}},
    'ww_chatter': {'fn': 'wit and momentum: the woodwinds chatter staccato, answering the strings\' ostinato every '
                         'other two bars',
                   'kinds': ('t1', 't1b', 'refrain', 'trans', 'dev_dialogue', 'episode', 'close', 'var', 'recap2'),
                   'w': 1.0, 'fast': True, 'feels': {'scherzo': 1.8, 'vivace': 1.6, 'allegro': 1.2, 'river': 0.4,
                                                     'andante': 0.0}},
    'muted_brass': {'fn': 'a veiled, distant colour in the quiet passages: horns (and trumpets) muted',
                    'kinds': None, 'soft': 'mp', 'w': 1.0, 'feels': {'andante': 1.5, 'river': 1.2, 'scherzo': 0.6}},
    'stopped_horn': {'fn': 'menace in the development: stopped-horn accents (muted ff) on the phrase starts',
                     'kinds': _DEV + ('retrans',), 'w': 0.5, 'feels': {'allegro': 1.2, 'scherzo': 1.0,
                                                                         'andante': 0.6}},
    'harmonics': {'fn': 'air at the end: the violins\' held notes in harmonics in a soft coda',
                  'kinds': _SOFT_END + ('coda', 'end', 'mist', 'intro'), 'soft': 'mp', 'w': 1.0,
                  'feels': {'andante': 1.5, 'river': 1.2, 'allegro': 0.5, 'vivace': 0.6, 'scherzo': 0.5}},
    'col_legno': {'fn': 'a dry, ghostly rattle in the scherzo: the strings\' ostinato col legno',
                  'kinds': ('trio', 't2', 'episode', 'dev_dialogue', 'var', 'refrain', 't1', 'recap2'), 'fast': True,
                  'w': 0.9, 'feels': {'scherzo': 2.0, 'vivace': 1.0, 'allegro': 0.5, 'river': 0.0, 'andante': 0.0}},
    'sfz': {'fn': 'violence in the development: sforzando strokes on the string / horn chords every other bar',
            'kinds': _DEV, 'w': 0.8, 'feels': {'allegro': 1.3, 'andante': 0.6}},
    'timp_roll': {'fn': 'the threshold of the climax: a timpani roll with a crescendo over the bars into it',
                  'kinds': ('pre_peak',), 'w': 0.9, 'feels': {}},
}
"""The technique palette (round o23). Realised by _tech_pre ('pizz_choir': the TEXTURE orc.TEXTURES['pizz_choir']) and
_tech_pass (the others: articulations and notes on the orchestrated parts). Every one is built from the installed
publishable packs: SSO 4.0 (pizzicato, tremolo, col legno, harmonics, staccato / spiccato), VSCO 2 CE (the mutes, harp,
timpani rolls) - the trills, the measured tremolo, the walking pizzicato and the glissandi are written as notes."""


def tech_rank(feel: str, rng, history=()) -> list:
    """The palette ranked for one piece: a weighted draw without replacement (weight x the feel's affinity, x
    TECH['memory'] for a technique among the first feature + 2 of the slot before / the one before that - the ones
    a piece may write when an earlier one finds no place; history: the earlier slots' 'tech' rankings, newest
    last). -> [technique names], the first ones featured."""
    T = TECH or TECH_ON
    feat = T.get('feature1', T['feature'])        # (round o24: master's window under MACRO's TECH v2)
    m1, m2 = T['memory']
    w = {}
    for name, x in TECHNIQUES.items():
        v = x['w'] * x.get('feels', {}).get(feel, 1.0)
        if history and name in (history[-1] or ())[:feat + 2]:
            v *= m1
        elif len(history) > 1 and name in (history[-2] or ())[:feat + 2]:
            v *= m2
        if v > 0:
            w[name] = v
    keys = {n: rng.random() ** (1.0 / v) for n, v in sorted(w.items())}
    return sorted(keys, key=lambda n: (-keys[n], n))


TECH_V2 = {'cap': 2, 'pizz_gap': 3, 'harm_soft': 2.5, 'feature': 3, 'over': 0.3,
           'pizz_kinds': ('t1b', 'refrain', 'var', 'trio', 'episode', 't2', 't2b', 'close', 'recap2', 'river'),
           'pizz_min': 0.25, 'col_legno': True, 'halo': (79, 91, 84),
           'harm_kinds': ('end_soft', 'coda_soft', 't2', 'trio', 'recap2', 'river', 'mist'),
           'gliss_off': 4.0, 'gliss_keep': ('harp', 'timpani', 'basses', 'tuba'), 'gliss_fns': ('bass', 'pedal')}
"""Round o24, TECH['v2'] (genres.symphony_shape - o23's judges: "the techniques return as a checklist", "texture for
its own sake"): 'cap' - a technique featured (the first TECH['feature'] of a slot's ranking) at most this often in a
set (tech_rank_v2: the WHOLE set's memory, not the two slots before); 'pizz_gap' - the pizzicato choir (and the
dance opening, MACRO) never within this many slots of the last one; the trill's crown on a climax once per set
(slot['tech_crown']); 'harm_soft' - the harmonics' weight in a piece that ends softly (MACRO's dying / surprise end,
the inverse arc). The material: the pizzicato choir on a block of the first theme ('pizz_kinds' first) with the
violins I plucking the tune (notes of 'pizz_min' beats and longer), the col legno's top part the motto's head on
the chords; the harmonics' home - the soft last chord / a quiet chorale ('harm_kinds'), as a held 'halo' (lo, hi,
centre) over it where no held violin part is there; the harp glissando into the climax with the build's last beats
thinned to the 'gliss_keep' roles / 'gliss_fns' (heard: o23's 4 tutti glissandi were under 1 % of their section),
'gliss_off' dB, elsewhere only into a soft (mf) arrival."""


def tech_rank_v2(feel: str, rng, history=(), sh=None) -> tuple:
    """TECH v2's ranking for one piece (TECH_V2): tech_rank's weighted draw with the whole set's memory - history: the
    earlier slots (dicts with 'tech2' / 'tech', 'shape', 'tech_crown'), oldest first; sh: this piece's macro shape.
    -> (the ranking, whether this piece's climax may take the trill's crown)."""
    T = TECH or TECH_ON
    V = T.get('v2') or TECH_V2
    feat = T['feature']
    m1, m2 = T['memory']
    hist = [h for h in history if isinstance(h, dict)]
    ranks = [list((h['tech2'] if 'tech2' in h else h.get('tech')) or ()) for h in hist]

    def featured(j):
        r = ranks[j][:feat]
        sh_ = hist[j].get('shape')
        if isinstance(sh_, dict) and sh_.get('open') == 'dance' and 'pizz_choir' not in r:
            r = r + ['pizz_choir']
        return r
    feats = [featured(j) for j in range(len(hist))]
    cnt: dict = {}
    for f in feats:
        for x in f:
            cnt[x] = cnt.get(x, 0) + 1
    soft = isinstance(sh, dict) and (sh.get('end') in ('dying', 'surprise') or sh.get('arc') == 'inverse')
    dance = isinstance(sh, dict) and sh.get('open') == 'dance'
    w, spare = {}, {}
    for name, x in TECHNIQUES.items():
        v = x['w'] * x.get('feels', {}).get(feel, 1.0)
        if ranks and name in ranks[-1][:feat + 2]:
            v *= m1
        elif len(ranks) > 1 and name in ranks[-2][:feat + 2]:
            v *= m2
        if name == 'pizz_choir' and (dance or any('pizz_choir' in f for f in feats[-V['pizz_gap']:])):
            v = 0.0
        if name == 'harmonics' and soft:
            v *= V['harm_soft']
        if v > 0 and cnt.get(name, 0) >= V['cap']:
            spare[name] = v * V['over']     # (over the cap: only where the piece would have too few)
        elif v > 0:
            w[name] = v
    for name in sorted(spare, key=lambda x_: (cnt.get(x_, 0), -spare[x_], x_)):
        if len(w) >= feat + 1:
            break
        w[name] = spare[name]
    keys = {n: rng.random() ** (1.0 / v) for n, v in sorted(w.items())}
    rank = sorted(keys, key=lambda n: (-keys[n], n))
    crown = not any(h.get('tech_crown') and 'trill' in feats[j] for j, h in enumerate(hist))
    return rank, crown


def _vmax(b) -> int:
    from ..bandlib.scoring import VEL
    return max((VEL.get(m[1], 78) if isinstance(m[1], str) else int(m[1]) for m in b.marks), default=78)


def _tech_soft(b, cap: str) -> bool:
    from ..bandlib.scoring import VEL
    return _vmax(b) <= VEL[cap]


def _tech_fast(tune) -> bool:
    return tune.feel in ('scherzo', 'vivace', 'allegro') or tune.tempo >= 120


def _tech_beat(tune) -> float:
    """The pulse a plucked / walking line strikes on: the dotted quarter in 6/8, else the quarter."""
    return 1.5 if tuple(getattr(tune, 'time_sig', ())) == (6, 8) else 1.0


def _tech_candidates(name: str, mat: dict, score, tune) -> list:
    """The blocks (score.blocks) a technique may go into, best first."""
    X = TECHNIQUES[name]
    kinds = X.get('kinds')
    if X.get('fast') and not _tech_fast(tune):
        return []
    out = []
    blocks = list(zip(mat['blocks'], score.blocks))
    for i, (blk, b) in enumerate(blocks):
        kd = blk['kind']
        nxt_peak = i + 1 < len(blocks) and blocks[i + 1][0]['peak']
        if kinds is not None:
            ok = kd in kinds or ('peak' in kinds and blk['peak']) or ('pre_peak' in kinds and nxt_peak)
            if not ok or (blk['peak'] and 'peak' not in kinds):
                continue
        if X.get('soft') and not _tech_soft(b, X['soft']):
            continue
        out.append(b)
    if kinds:
        order = {k: j for j, k in enumerate(kinds)}
        kd = {x['name']: x['kind'] for x in mat['blocks']}
        out.sort(key=lambda b: (0 if b.peak and 'peak' in kinds else 1, order.get(kd[b.name], len(order)), b.start))
    return out


def _tech_pre(mat: dict, score, tune, weights: dict) -> dict:
    """TECH before the orchestration: the piece's ranking (the set's, else its own) and - when the pizzicato choir is
    among its first TECH['feature'] + TECH['pizz_reach'] (the ones before it may find no place in the parts) and a
    block allows it - the pizzicato choir's block(s) given the 'pizz_choir' texture. -> {'rank', 'pizz': [names]}."""
    rank = list((tune.arrange or {}).get('tech') or tech_rank(tune.feel, random.Random(f"sym-tech:{tune.seed}")))
    pizz = []
    if TECH.get('v2'):                     # (round o24: the dance opening is the piece's pizzicato choir - MACRO)
        pizz = [b.name for b in score.blocks if set(weights.get(b.name) or {}) == {'pizz_choir'}]
        if pizz:
            return {'rank': rank, 'pizz': pizz}
    if 'pizz_choir' in rank[:TECH['feature'] + TECH['pizz_reach']]:
        by = {x['name']: x for x in mat['blocks']}
        cand = [b for b in _tech_candidates('pizz_choir', mat, score, tune) if not b.peak and _tech_soft(b, 'mf')
                and by[b.name]['theme'] and not by[b.name]['voices']]
        if TECH.get('v2'):                 # (round o24: the first theme's blocks first - the theme carried)
            pk_ = TECH['v2']['pizz_kinds']
            cand.sort(key=lambda b: (pk_.index(by[b.name]['kind']) if by[b.name]['kind'] in pk_ else len(pk_),
                                     b.start))
        pizz = [b.name for b in cand[:TECH['pizz_blocks']]]
        for n in pizz:
            weights[n] = {'pizz_choir': 1.0}
    return {'rank': rank, 'pizz': pizz}


def _root_pc(sym):
    try:
        return chord(sym).root % 12 if sym else None
    except ComposeError:
        return None


def _tech_part(plan_o, like, **kw):
    """A new orchestrated Part (a technique's added line), its velocity offset from FUNCTIONS unless given."""
    fn = kw.get('function', 'colour')
    d = dict(role=None, block=None, function=fn, voice='', notes=[], art='sustain',
             off=orc.FUNCTIONS[fn]['off'], line=False)
    if like is not None:
        d.update(block=like.block)
    d.update(kw)
    p = orc.Part(**d)
    plan_o.parts.append(p)
    return p


def _restrike(notes, step: float, dur: float | None = None) -> list:
    """Long notes struck again every `step` beats (from each note's start: a plucked / repeated line), each `dur`
    long (default 0.9 step); short notes kept."""
    out = []
    for a, d, p in notes:
        if d <= step * 1.25 + _EPS:
            out.append((a, min(d, dur if dur is not None else d), p))
            continue
        t = a
        while t < a + d - 0.25 * step:
            out.append((round(t, 4), dur if dur is not None else 0.9 * step, p))
            t += step
    return sorted(out)


def _walk(notes, step: float, key: str, chart) -> list:
    """A held bass line walked in `step` beats: each long note's first beat its pitch, the beats between steps of the
    key's scale toward the next note (the last beat a step above / below it), an octave / fifth where the next note
    is too near."""
    ns = sorted(notes)
    out = []
    for i, (a, d, p) in enumerate(ns):
        n = max(1, int(round(d / step)))
        if n < 2:
            out.append((a, min(d, 0.9 * step), p))
            continue
        q = ns[i + 1][2] if i + 1 < len(ns) else p
        pcs = pcs_of(key, _chart_at(chart, a))
        line = [p]
        cur = p
        for j in range(1, n):
            left = n - j                   # (beats left before q)
            gap = q - cur
            if left == 1 and q != cur:     # (the approach: a step above / below the goal)
                cur = _step(q, 1 if gap < 0 else -1, pcs)
            elif abs(gap) > 2 * left:
                cur = _step(cur, 1 if gap > 0 else -1, pcs)
            else:
                cur = p + 7 if j % 2 else p        # (the fifth and back)
                if cur % 12 not in pcs:
                    cur = p + 12 if p + 12 <= 55 else p
            line.append(cur)
        for j, x in enumerate(line):
            out.append((round(a + j * step, 4), 0.9 * step, x))
    return out


def _trill(note, key: str, chart, tempo: float, upper: bool = True) -> list:
    """A held note as a trill with its upper scale neighbour (note length TECH['trill_s'] at the tempo, on a beat
    fraction 1/2 .. 1/8), ending with the turn (lower neighbour, main) into the note's last stretch."""
    a, d, p = note
    sb = 60.0 / max(30.0, tempo)
    st = min((1 / 2, 1 / 3, 1 / 4, 1 / 6, 1 / 8), key=lambda f: abs(f * sb - TECH['trill_s']))
    pcs = pcs_of(key, _chart_at(chart, a))
    up, lo = _step(p, 1, pcs), _step(p, -1, pcs)
    n = int((d * 0.8) / st)
    out = [(round(a + i * st, 4), st * 1.05, p if i % 2 == 0 else up) for i in range(max(2, n - 2))]
    t = a + len(out) * st
    out += [(round(t, 4), st * 1.05, lo), (round(t + st, 4), max(st, a + d - t - st), p)]
    return out


def _gliss(z: float, key: str, chart, tempo: float, top_lo: int = 76, top_hi: int = 86) -> list:
    """A harp glissando up the arrival's scale (the key's, the chord's tones on top), ~TECH['gliss_s'] seconds
    long, landing on a chord tone at beat z."""
    sym = _chart_at(chart, z + 0.01)
    pcs = pcs_of(key, sym)
    cp = _cpcs(sym) if sym else set(pcs)
    top = next((q for q in range(top_lo, top_hi + 1) if q % 12 in cp), top_lo)
    scale = [q for q in range(top - 16, top) if q % 12 in pcs]          # (from ~G4: lower, the first notes went
    #                                                                    unheard under the arrival - the gate's silent notes)
    sb = 60.0 / max(30.0, tempo)
    span = min(2.0, max(0.5, round(TECH['gliss_s'] / sb * 4) / 4))
    dt = span / max(1, len(scale))
    return [(round(z - span + i * dt, 4), 1.0, q) for i, q in enumerate(scale)] + [(z, 2.0, top)]


def _tech_pass(plan_o, score, mat: dict, tune, roles, info: dict, log: list, bar: float) -> None:
    """TECH after the orchestration: the featured techniques written into the parts (TECHNIQUES; the pizzicato
    choir's texture was chosen before - here its violins I join the plucked choir an octave up on the beats). A
    technique with no place in the parts is skipped and the next of the ranking written instead, up to
    TECH['feature']; log gets (technique, block) per event."""
    have = set(roles)
    by = {x['name']: x for x in mat['blocks']}
    sb = {b.name: b for b in score.blocks}
    beat = _tech_beat(tune)
    fast = _tech_fast(tune)
    V2 = TECH.get('v2')                       # (round o24: TECH_V2 - the techniques carry the material)
    kf = float(mat.get('scale', 1))

    def parts(b, rs=None, fns=None, arts=None):
        return [p for p in plan_o.parts if p.block == b.name and p.notes and (rs is None or p.role in rs) and
                (fns is None or p.function in fns) and (arts is None or p.art in arts)]

    def used(b):
        return {p.role for p in plan_o.parts if p.block == b.name and p.notes}

    def long_(p, x=1.0):
        return sum(d for _, d, _ in p.notes) / max(1, len(p.notes)) >= x * beat - _EPS

    def do(name):
        out = []
        cand = _tech_candidates(name, mat, score, tune)
        if name == 'pizz_choir':
            for n in info['pizz']:
                b = sb[n]
                if b.texture != 'pizz_choir':
                    continue
                mel = parts(b, None, ('melody',)) if V2 else []
                if mel and 'violins1' in have and 'violins1' not in used(b):
                    # (round o24: the violins I pluck the tune itself - the theme on the technique)
                    m = mel[0]
                    ns = []
                    for a, d, q in sorted(m.notes):
                        if d < V2['pizz_min'] * beat - _EPS:
                            continue
                        while q > 86:
                            q -= 12
                        while q < 55:
                            q += 12
                        ns.append((a, min(d, 0.75 * beat), q))
                    if len(ns) >= 4:
                        _tech_part(plan_o, m, role='violins1', function='doubling', notes=ns, art='pizzicato',
                                   off=m.off)
                        out.append(n)
                        continue
                for p in parts(b, ('violins2',), ('ostinato',)):
                    on = [(a, d, q + 12) for a, d, q in p.notes
                          if abs((a - b.start) / beat - round((a - b.start) / beat)) < 0.02 and q + 12 <= 88]
                    if on and 'violins1' in have and 'violins1' not in used(b):
                        _tech_part(plan_o, p, role='violins1', function='ostinato', notes=on, art='pizzicato',
                                   off=p.off - 2.0)
                out.append(n)
        elif name == 'pizz_walk':
            for b in cand:
                if b.peak or len(out) >= 2:
                    continue
                ps = [p for p in parts(b, ('basses', 'cellos'), ('bass', 'doubling'), ('sustain',)) if long_(p, 1.5)]
                if not ps:
                    continue
                for p in ps:
                    p.notes, p.art = _walk(p.notes, beat, by[b.name]['key'], b.chart), 'pizzicato'
                out.append(b.name)
        elif name in ('trem_build', 'measured_trem'):
            for b in cand:
                if out:
                    break
                ps = [p for p in parts(b, _STR, ('harmony', 'inner', 'pedal'), ('sustain',)) if long_(p)]
                if not ps:
                    continue
                for p in ps:
                    if name == 'trem_build':
                        p.art = 'tremolo'
                    else:
                        st = 0.25 if tune.tempo <= 100 and beat == 1.0 else 0.5
                        p.notes, p.art = _restrike(p.notes, st), 'spiccato'
                out.append(b.name)
        elif name == 'trill':
            for b in cand:
                if len(out) >= 2:
                    break
                mel = parts(b, None, ('melody',))
                if not mel:
                    continue
                m = mel[0]
                key = by[b.name]['key']
                if b.peak and V2 and not (tune.arrange or {}).get('tech_crown', True):
                    continue                        # (round o24: the trill's crown once per set)
                if b.peak:
                    held = sorted((n for n in m.notes if n[1] >= max(1.5, beat) - _EPS),
                                  key=lambda n: (-n[1], -n[2], n[0]))[:2]
                    ww = [p for p in parts(b, ('flutes', 'oboes', 'clarinets'), ('melody', 'doubling'))]
                    if not held:
                        continue
                    if ww:
                        w = ww[0]
                        tr = []
                        for h in held:
                            hit = [n for n in w.notes if abs(n[0] - h[0]) < 0.05 and n[1] >= max(1.5, beat) - _EPS]
                            for n in hit:
                                w.notes.remove(n)
                                tr += _trill(n, key, b.chart, tune.tempo)
                        if tr:
                            w.notes = sorted(w.notes + tr)
                            out.append(b.name)
                            continue
                    for r, (lo, hi) in (('flutes', (72, 93)), ('oboes', (64, 86)), ('clarinets', (55, 84))):
                        if r not in have or r in used(b):
                            continue
                        tr = []
                        for h in held:
                            q = h[2] + 12 if h[2] + 12 <= hi else h[2]
                            if lo <= q <= hi:
                                tr += _trill((h[0], h[1], q), key, b.chart, tune.tempo)
                        if tr:
                            _tech_part(plan_o, m, role=r, function='colour', notes=tr, off=-3.0)
                            out.append(b.name)
                            break
                    continue
                w = [p for p in mel + parts(b, _WW, ('doubling',)) if p.role in _WW]
                if not w:
                    continue
                ns = sorted(w[0].notes)
                if len(ns) < 2:
                    continue
                pen, last = ns[-2], ns[-1]
                if pen[1] >= beat - _EPS and abs(pen[0] + pen[1] - last[0]) < 0.3:
                    w[0].notes = ns[:-2] + _trill(pen, key, b.chart, tune.tempo) + [last]
                    out.append(b.name)
        elif name == 'harp_gliss':
            if 'harp' not in have:
                return out
            for b in cand:
                if len(out) >= 2:
                    break
                if b.start < 1.0:
                    continue
                if any(p.role == 'harp' and any(b.start - 2.0 <= a < b.start for a, _, _ in p.notes)
                       for p in plan_o.parts):
                    continue
                prev = next((x for x in score.blocks if x.start + x.length > b.start - 0.5 and x.start < b.start),
                            None)
                if prev is None:
                    continue
                if V2 and not b.peak and not (_tech_soft(b, 'mf') and _tech_soft(prev, 'mf')):
                    continue                        # (round o24: never into a loud block but the climax)
                g = _gliss(b.start, by[b.name]['key'], b.chart, tune.tempo)
                off_ = 2.0
                if V2 and b.peak:                   # (round o24: the build's last beats thinned under the sweep)
                    a0 = g[0][0]
                    for p in plan_o.parts:
                        if p.block != prev.name or p.role in V2['gliss_keep'] or p.function in V2['gliss_fns']:
                            continue
                        keep = [(a, min(d, a0 - a), q) for a, d, q in p.notes if a < a0 - 0.1]
                        keep = [x for x in keep if x[1] > 0.1]
                        if keep:
                            p.notes = keep
                    off_ = V2['gliss_off']
                _tech_part(plan_o, None, role='harp', block=prev.name, function='colour', notes=g[:-1], art=None,
                           off=off_)
                _tech_part(plan_o, None, role='harp', block=b.name, function='colour', notes=g[-1:], art=None,
                           off=off_)
                out.append(b.name)
        elif name == 'ww_chatter':
            for b in cand:
                if b.peak or out:
                    continue
                src = [p for p in parts(b, _STR, ('ostinato', 'figuration'), ('staccato', 'spiccato', 'sustain'))]
                if not src:
                    continue
                s = max(src, key=lambda p: sum(q for _, _, q in p.notes) / len(p.notes))
                gaps = sorted(y[0] - x[0] for x, y in zip(s.notes, s.notes[1:]))
                if gaps and gaps[len(gaps) // 2] * 60.0 / tune.tempo < 0.14:
                    continue                        # (too fast to tongue)
                free = [r for r in ('flutes', 'clarinets', 'oboes') if r in have and r not in used(b)]
                if not free:
                    continue
                odd = [n for n in s.notes if int((n[0] - b.start + _EPS) // (2 * bar)) % 2 == 1]
                if len(odd) < 4:
                    continue
                for r in free[:2]:
                    lo, hi = {'flutes': (72, 93), 'clarinets': (55, 84), 'oboes': (62, 86)}[r]
                    sh = 12 if r == 'flutes' else 0
                    ns = [(a, min(d, 0.6 * beat), q + sh) for a, d, q in odd]
                    while ns and min(q for _, _, q in ns) < lo:
                        ns = [(a, d, q + 12) for a, d, q in ns]
                    while ns and max(q for _, _, q in ns) > hi:
                        ns = [(a, d, q - 12) for a, d, q in ns]
                    if ns and lo <= min(q for _, _, q in ns):
                        _tech_part(plan_o, s, role=r, function='ostinato', notes=ns, art='staccato', off=-5.0)
                out.append(b.name)
        elif name == 'muted_brass':
            for b in cand:
                if len(out) >= 2:
                    break
                ps = parts(b, ('horns', 'trumpets'), None, ('sustain',))
                hit = False
                for p in ps:
                    lo, hi = orch.MUTES[p.role]['range']
                    inn = [n for n in p.notes if lo <= n[2] <= hi]
                    if not inn:
                        continue
                    rest = [n for n in p.notes if not lo <= n[2] <= hi]
                    p.notes, p.art = inn, 'muted'
                    if rest:
                        _tech_part(plan_o, p, role=p.role, function=p.function, voice=p.voice, notes=rest,
                                   art='sustain', off=p.off, line=p.line)
                    hit = True
                if hit:
                    out.append(b.name)
        elif name == 'stopped_horn':
            if 'horns' not in have:
                return out
            for b in cand:
                if out or b.peak:
                    continue
                hon = [a for p in parts(b, ('horns',)) for a, _, _ in p.notes]
                ns = []
                t = b.start
                while t < b.start + b.length - bar and len(ns) < 6:
                    r = _root_pc(_chart_at(b.chart, t + 0.01))
                    if r is not None and not any(abs(a - t) < 0.5 for a in hon):
                        lo = next(q for q in range(53, 65) if q % 12 == r)
                        ns += [(t, 0.75 * beat, lo), (t, 0.75 * beat, lo + 7)]
                    t += 4 * bar
                if ns:
                    _tech_part(plan_o, None, role='horns', block=b.name, function='colour', notes=ns, art='muted',
                               off=6.0)
                    out.append(b.name)
        elif name == 'harmonics' and V2:
            out = _harmonics_v2(plan_o, score, mat, tune, have, parts, used, long_, cand, by)
        elif name == 'harmonics':
            for b in cand:
                ps = parts(b, ('violins1', 'violins2'), ('harmony', 'pedal', 'inner', 'colour'), ('sustain',))
                hit = False
                for p in ps:
                    if not long_(p):
                        continue
                    ns = [(a, d, q + 12 if q < 67 and q + 12 <= 93 else q) for a, d, q in p.notes]
                    if min(q for _, _, q in ns) >= 67:
                        p.notes, p.art = ns, 'harmonics'
                        hit = True
                if hit:
                    out.append(b.name)
                    break
        elif name == 'col_legno':
            for b in cand:
                if b.peak or out or not _tech_soft(b, 'mf'):
                    continue
                ps = parts(b, _STR, ('ostinato', 'figuration'), ('staccato', 'spiccato'))
                if not ps:
                    continue
                for p in ps:
                    p.art = 'col legno'
                if V2 and V2.get('col_legno'):      # (round o24: the col legno's top part plays the motto's head)
                    _col_legno_motto(max(ps, key=lambda p: sum(q for _, _, q in p.notes) / len(p.notes)), b, mat,
                                     by[b.name]['key'], kf, bar, beat)
                out.append(b.name)
        elif name == 'sfz':
            for b in cand:
                if len(out) >= 2:
                    break
                ps = [p for p in parts(b, _STR + ('horns',), ('harmony', 'inner', 'pedal'), ('sustain', 'tremolo'))
                      if long_(p)]
                hit = False
                for p in ps:
                    sf = [a for a, d, _ in p.notes if d >= beat - _EPS and
                          abs((a - b.start) / bar - round((a - b.start) / bar)) < 0.02 and
                          int(round((a - b.start) / bar)) % 2 == 1]
                    if sf:
                        p.sf = tuple(sorted(set(p.sf) | set(sf)))
                        hit = True
                if hit:
                    out.append(b.name)
        elif name == 'timp_roll':
            if 'timpani' not in have:
                return out
            for b in cand:
                if out:
                    break
                nxt = next((x for x in score.blocks if abs(x.start - (b.start + b.length)) < 0.05), None)
                if nxt is None or not nxt.peak:
                    continue
                span = bar * (2 if bar * 60.0 / tune.tempo < 2.5 else 1)
                a0 = nxt.start - span
                if a0 < b.start or any(p.role == 'timpani' and any(a0 - _EPS <= a < nxt.start for a, _, _ in p.notes)
                                       for p in plan_o.parts):
                    continue
                sym = _chart_at(b.chart, nxt.start - 0.05) or _chart_at(nxt.chart, nxt.start + 0.05)
                tonic = Key(by[nxt.name]['key']).tonic
                r = _root_pc(sym)
                if r not in (tonic % 12, (tonic + 7) % 12):
                    r = (tonic + 7) % 12
                q = _timp_pitch(r, tonic)
                st = span / 4
                ns = [(round(a0 + i * st, 4), st + 0.25, q) for i in range(4)]
                _tech_part(plan_o, None, role='timpani', block=b.name, function='colour', notes=ns, art='roll',
                           off=-4.0)
                out.append(b.name)
        return out

    done = []
    tried = info['rank'][:TECH['feature'] + 1] if V2 else info['rank']     # (round o24: the set's memory holds)
    for name in (['pizz_choir'] if info['pizz'] else []) + [n for n in tried if n != 'pizz_choir']:
        if len(done) >= TECH['feature']:
            break
        bl = do(name)
        if bl:
            done.append(name)
            log.extend((name, x) for x in bl)
    info['done'] = done
    plan_o.notes = sum(len(p.notes) for p in plan_o.parts)


def _col_legno_motto(p, b, mat: dict, key: str, k: float, bar: float, beat: float) -> None:
    """TECH v2: the col legno part's notes over block b replaced by the motto's head on the chords (a statement per
    bar, or per two bars where the head is longer than half a bar), struck short, near the part's register."""
    ns0 = sorted(p.notes)
    med = sorted(q for _, _, q in ns0)[len(ns0) // 2]
    out = []
    t = b.start
    while t < b.start + b.length - 0.5 * bar - _EPS:
        sym = _chart_at(b.chart, t + 0.01)
        pcs = pcs_of(key, sym)
        cp = _cpcs(sym) if sym else set(pcs)
        anchor = _near(cp, med)
        head = _scaled(motto_notes(mat['motto'], t / k, anchor, pcs, ('head',)), k)
        if not head:
            break
        span = head[-1][0] - t
        step = bar if span <= 0.6 * bar else 2 * bar
        out += [(a, min(d, 0.5 * beat), q) for a, d, q in head
                if t - _EPS <= a < min(t + step, b.start + b.length) - 0.1]
        t += step
    if len(out) >= 4:
        lo, hi = min(q for _, _, q in ns0) - 5, max(q for _, _, q in ns0) + 5
        p.notes = [(a, d, min(hi, max(lo, q))) for a, d, q in out]


def _harmonics_v2(plan_o, score, mat: dict, tune, have, parts, used, long_, cand, by) -> list:
    """TECH v2's harmonics (TECH_V2): their home first - the soft last block, the dissolving coda, a quiet chorale
    ('harm_kinds', at most mp) - the violins' held notes there in harmonics (as v1), else a held HALO: the chart's
    chord tone nearest the halo centre in the violins I (or II) where that role is free, one note per chord."""
    V2 = TECH['v2']
    lo, hi, mid = V2['halo']
    kinds = V2['harm_kinds']
    pool = [b for b in score.blocks if by[b.name]['kind'] in kinds and not (b.peak and mat.get('climax') != 'quiet')
            and _tech_soft(b, 'mp')]
    pool.sort(key=lambda b: (kinds.index(by[b.name]['kind']), -b.start))
    for b in pool + [x for x in cand if x not in pool]:
        hit = False
        for p in parts(b, ('violins1', 'violins2'), ('harmony', 'pedal', 'inner', 'colour'), ('sustain',)):
            if not long_(p):
                continue
            ns = [(a, d, q + 12 if q < 67 and q + 12 <= 93 else q) for a, d, q in p.notes]
            if min(q for _, _, q in ns) >= 67:
                p.notes, p.art = ns, 'harmonics'
                hit = True
        if not hit and b in pool:
            r = next((x for x in ('violins1', 'violins2') if x in have and x not in used(b)), None)
            if r and b.chart:
                ns = []
                for a, d, sym in b.chart:
                    if not sym or d < 0.99:
                        continue
                    cp = _cpcs(sym)
                    q = _near(cp, mid, lo, hi)
                    if ns and ns[-1][2] == q and abs(ns[-1][0] + ns[-1][1] - a) < 0.05:
                        ns[-1] = (ns[-1][0], ns[-1][1] + d, q)
                    else:
                        ns.append((a, d, q))
                if ns:
                    _tech_part(plan_o, None, role=r, block=b.name, function='colour', notes=ns, art='harmonics',
                               off=-1.0)
                    hit = True
        if hit:
            return [b.name]
    return []


TECH_FAMILY = {'strings': _STR, 'woodwinds': _WW, 'brass': ('horns', 'trumpets', 'trombones', 'tuba'),
               'timpani': ('timpani',), 'harp': ('harp',)}


def _exposed_answers(plan_o):
    """A counter-line answering in the melody's rests is the foreground voice.

    Keep the counter offset when the two lines overlap (real counterpoint).
    Use score-time note spans, before humanized overlaps and releases, and
    leave doublings at their supporting level. Works after solo substitutions.
    """
    melody = {}
    for p in plan_o.parts:
        if p.function == 'melody':
            melody.setdefault(p.block, []).extend((a, a + d) for a, d, _ in p.notes)
    return {i: {round(a, 3) for a, d, _ in p.notes
                if not any(x < a + d - _EPS and z > a + _EPS for x, z in melody[p.block])}
            for i, p in enumerate(plan_o.parts)
            if p.function == 'counter' and p.line and melody.get(p.block)}


def _theme_accents(plan_o, score):
    """Allocate automatic theme arrivals after all role/doubling choices.

    One leader keeps the sfz attack. Melodic doublings share eight velocity
    points (at most four each), without a copied marcato envelope. Supporting
    basses keep their own articulation. The first arrival at a marked peak
    remains a deliberate tutti. Explicit technique accents elsewhere survive.
    Returns the small supporting offsets by part index and beat.
    """
    support = {}
    for b in score.blocks:
        arrivals = sorted({round(t, 3) for x in b.lines for t in x.meta.get('sf', ())})
        for t in arrivals:
            parts = [(i, p) for i, p in enumerate(plan_o.parts) if p.block == b.name
                     and any(round(a, 3) == t for a in p.sf)
                     and any(round(a, 3) == t for a, _, _ in p.notes)]
            if not parts or (b.peak and t == arrivals[0]):
                continue
            # Prefer the actual melody, including a solo replacement; a bass
            # theme leads only when the texture has no melody at this arrival.
            leaders = [(i, p) for i, p in parts if p.function == 'melody']
            if not leaders:
                leaders = [(i, p) for i, p in parts if p.function == 'bass']
            if not leaders:
                leaders = [(i, p) for i, p in parts if p.line]
            if not leaders:
                continue
            leader_i, leader = leaders[0]
            doubles = [(i, p) for i, p in parts if i != leader_i and p.function == 'doubling'
                       and p.voice == (leader.voice or leader.function)]
            boost = min(4.0, 8.0 / len(doubles)) if doubles else 0.0
            for i, p in parts:
                if i != leader_i:
                    p.sf = tuple(a for a in p.sf if round(a, 3) != t)
            for i, p in doubles:
                support.setdefault(i, {})[t] = boost
    return support


def tech_stats(song) -> dict:
    """The articulation distribution of an orchestrated symphonic song (s.orchestration; a sforzando counts as
    marcato): {family: {art: share of the family's notes}}, {role: {art: share}}, the techniques written (s.tech:
    the TECH events) and the counts of the built ones (trills = the alternations, glissandi, walking pizzicato)."""
    plan_o = getattr(song, 'orchestration', None)
    out = {'family': {}, 'role': {}, 'events': list(getattr(song, 'tech_events', ()) or ())}
    if plan_o is None:
        return out
    cnt: dict = {}
    for p in plan_o.parts:
        sf = {round(x, 3) for x in p.sf}
        for a, _, _ in p.notes:
            art_ = 'marcato' if round(a, 3) in sf else (p.art or 'hit')
            cnt.setdefault(p.role, {}).setdefault(art_, 0)
            cnt[p.role][art_] += 1
    out['counts'] = {r: dict(sorted(c.items())) for r, c in sorted(cnt.items())}
    for r, c in cnt.items():
        n = sum(c.values())
        out['role'][r] = {k: round(v / n, 4) for k, v in sorted(c.items())}
    for f, rs in TECH_FAMILY.items():
        c: dict = {}
        for r in rs:
            for k, v in cnt.get(r, {}).items():
                c[k] = c.get(k, 0) + v
        n = sum(c.values())
        if n:
            out['family'][f] = {k: round(v / n, 4) for k, v in sorted(c.items())}
    out['techniques'] = sorted({e[0] for e in out['events']})
    return out


# ------------------------------------------------------------------------------------------------ round o24: MACRO

MACRO = None
"""Round o24 (o23's judges, both codes: template flags 44 per packet against the references' 9 - "every piece has the
same overall shape": a soft opening, a staccato middle, a tremolo build, a unison tutti at 78-85 %, a dip, a coda; the
statistician's loudness arcs "template A / B"): the piece's MACRO MACRO drawn per set slot with the whole set's memory
(shape_draw / shape_slot) - how it opens, where its climax falls and how many there are, what kind of climax, how it
ends - and realised by re-shaping the layout's own blocks (no short block added; o19a: imposed sections hurt):
  open    'motto' the call loud from bar 1, 'solo' one voice, 'soft' the mist / the source, 'medias' in medias res
          (the opening block left out, the first theme f in the tutti), 'dance' the first theme p in the woodwinds over
          the plucked string choir (the fast feels; the pizzicato choir carrying the main theme);
  arc     the climax's centre ('at': 'classic' 0.76-0.8, 'mid', 'early' with the coda a second summit, 'late' with the
          second theme's return before the build, 'twin' a first f peak in the exposition, 'inverse' the quiet climax);
  climax  brass / strings / chorale / 'dialogue' (the tune against the brass choir's own line, apex_dialogue) /
          'quiet' (the inverse arc);
  end     the coda's kind decides the family (the set's end_alt): 'loud' / 'cut' (no coda: the end straight after the
          climax), 'dying' (the fade) / 'surprise' (the block before held f, the coda subito pp).
None = off (bit-identical); genres.symphony_shape switches it with the set draw (plan['set_macro']) and the technique
fixes (TECH['v2'])."""
MACRO_ON = {
    'open': {'motto': 1.0, 'solo': 0.8, 'soft': 0.7, 'medias': 1.0, 'dance': 0.9},
    'arc': {'classic': 0.6, 'mid': 1.0, 'early': 0.9, 'late': 0.8, 'twin': 1.0, 'inverse': 0.9},
    'end': {'loud': 1.0, 'cut': 0.9, 'dying': 1.0, 'surprise': 1.0},
    'climax': {'brass': 0.8, 'strings': 1.0, 'chorale': 1.0, 'dialogue': 1.0},
    'at': {'classic': (0.76, 0.8), 'mid': (0.64, 0.7), 'early': (0.56, 0.62), 'late': (0.86, 0.9),
           'twin': (0.74, 0.8), 'inverse': (0.66, 0.74)},
    'ends': {'triumph': ('loud', 'cut'), 'dissolve': ('dying', 'surprise')},
    'arc_ends': {'early': ('loud',), 'late': ('cut', 'loud')},
    'end_arcs': {'cut': ('late', 'classic', 'twin')}, 'tol': 0.07, 'tries': 6,
    'opens': {'intro': ('motto', 'solo', 'soft', 'medias', 'dance'), 'source': ('soft', 'medias'),
              None: ('soft', 'medias', 'dance')},
    'fast': ('allegro', 'vivace', 'scherzo'),
    'medias': {'tex': {'tutti_drive': 1.0, 'drive_strings': 0.4}, 'dyn': [(0, 'f'), (1, 'f')], 'cap': 'f'},
    'dance': {'tex': {'pizz_choir': 1.0}, 'dyn': [(0, 'p'), (0.6, 'mp'), (1, 'mf')]},
    'twin': {'kinds': ('close', 't1b', 'episode', 'refrain', 'var', 't2b', 'trio'),
             'loud': ('close', 't1b', 'episode', 'refrain'), 'at': (0.22, 0.58), 'centre': 0.42,
             'dyn': [(0, 'f', 'step'), (1, 'f')], 'tex': {'tutti_drive': 1.0}},
    'second': {'dyn': [(0, 'f', 'step'), (0.5, 'f'), (1, 'ff')], 'cap': 'ff'},
    'surprise': {'coda': [(0, 'pp', 'step'), (1, 'pp')], 'before': [(0, 'f'), (1, 'f')]},
    'floor': 0.5,
    'post': {'early': {'recap2': (8, 18), 'coda': (6, 12), 'recap': (8, 12), 'river': (8, 12)}},
}
"""MACRO on: the draw's weights per dimension (open / arc / end / climax), the climax's centre per arc, the endings a
coda kind allows, the endings an arc needs (an early climax wants the coda's second summit, a late one no fade
after it), the openings a layout's first block allows (an intro row; the river's source; a layout opening on its
theme), the feels that dance, the overrides (medias: the first theme's texture / dynamics / LOUDEST cap; dance; the
twin peak's kinds, place, dynamics; the early arc's second summit in the coda; the surprise's subito pp coda after
an f block), the climax's lowest centre (PEAK_AT_V3's floor 0.66 lowered) and the early arc's longer post-climax
blocks (_place_peak)."""
MACRO2_V2 = {
    'move': ('dev_dialogue', 'episode', 'var', 'trio', 'dev_fugato'), 'arcs_move': ('early', 'mid'),
    'after': {'dyn': [(0, 'f'), (0.5, 'mf'), (1, 'mp')], 'cap': 'f'},
    'loud': {'coda': {'dyn': [(0, 'f'), (0.4, 'ff'), (1, 'ff')], 'cap': 'ff', 'level': 1.0},
             'end': {'dyn': [(0, 'ff')], 'cap': 'ff', 'level': 1.0}},
    'cut': {'dyn': [(0, 'ff')], 'cap': 'ff', 'level': 1.0, 'tex': {'hammer': 1.0}},
    'climax_tex': {'strings': {'tex': {'apex_low': 1.0}}, 'chorale': {'tex': {'apex_chorale2': 1.0}},
                   'dialogue': {'tex': {'apex_dialogue2': 1.0}}},
    'tex_t1_cap': 2, 'tex_t1_near': 2, 'bass_n': 2, 'bass_cap': {'octaves': 3, 'eighths': 3, 'gallop': 3},
}
"""Round o24b (SHAPE2 - o24's judges: "every climax at 71-90 %", "the loud endings fade", "piece 5 opens with piece 1's
head rhythm and its harp-arpeggio S2", "the staccato octave-bass ostinato under a woodwind tune in 3-4 pieces"):
'move' - the early / mid arc ('arcs_move') moves the climax's MATERIAL: the development's blocks before the
retransition (these kinds, latest first) go after the climax as its aftermath, 'after' (falling from f; LOUDEST cap
f) - the build and the summit come earlier, real music follows them; 'loud' - the triumphant coda and the last bars
at ff (the level of the climax), 'cut' - the end right after the climax at ff in the tutti's hammered chords
(over the ending family's texture), no fade; 'climax_tex' - the climax
types that are not the brass tutti in their own textures (the tune low under the violins' run, the brass choir's
chorale in a string shimmer, the dialogue over a held bass) where the climax's material has no texture of its own;
the set's memory over the whole set on the motto's rhythm family (shape['motto']: a family heard before replaced by
the least heard one), on the first theme's texture (shape['tex_t1']: at most 'tex_t1_cap' times, never one of the
'tex_t1_near' slots before) and on the pumping bass's figures (shape['bass_figs']: 'bass_n' figures a piece, the
least used first, 'bass_cap' pieces a set at most)."""
MACRO2_ON = dict(MACRO_ON, v2=MACRO2_V2,
                 arc={'classic': 0.5, 'mid': 1.2, 'early': 1.2, 'late': 0.7, 'twin': 0.8, 'inverse': 0.8},
                 at={'classic': (0.74, 0.8), 'mid': (0.57, 0.62), 'early': (0.5, 0.56), 'late': (0.86, 0.9),
                     'twin': (0.74, 0.8), 'inverse': (0.62, 0.7)},
                 arc_ends={'late': ('cut', 'loud')}, tol=0.05, floor=0.45,
                 medias={'tex': {'motto_bass': 1.0, 'dialogue_brass': 0.7, 'tutti_drive': 0.3},
                         'dyn': [(0, 'f'), (1, 'f')], 'cap': 'f'},
                 post={'early': {'recap2': (8, 18), 'coda': (6, 12), 'recap': (8, 12), 'river': (8, 12),
                                 'dev_dialogue': (6, 20), 'dev_fugato': (6, 16), 'episode': (4, 12), 'var': (6, 12),
                                 'trio': (6, 12)},
                       'mid': {'recap2': (8, 18), 'coda': (4, 10), 'recap': (8, 12), 'river': (8, 12),
                               'dev_dialogue': (6, 20), 'dev_fugato': (6, 16), 'episode': (4, 12), 'var': (6, 12),
                               'trio': (6, 12)}})
"""SHAPE2 on (round o24b, genres.symphony_shape2): MACRO_ON with MACRO2_V2, the climax centres drawn wider (early
0.5-0.56, mid 0.57-0.62), any ending after an early / mid climax (the aftermath is the post-climax music, no second
summit in the coda), the realised centre within 'tol', the in medias res opening without the pumping drive, the
moved blocks' lengths free after the climax (_place_peak's 'post')."""
MACRO3_V2 = dict(
    MACRO2_V2, v3=True,
    cut=dict(MACRO2_V2['cut'], tex={'hammer_motto': 1.0}),
    climax_tex=dict(MACRO2_V2['climax_tex'], chorale={'tex': {'apex_chorale3': 1.0}}),
    aftermath={'one': [(0, 'f'), (0.35, 'mp'), (1, 'f')], 'first': [(0, 'f'), (0.5, 'mp'), (1, 'mf')],
               'mid': [(0, 'mf'), (1, 'mf')], 'last': [(0, 'mf'), (0.6, 'f'), (1, 'f')]},
    rise={'dyn': [(0, 'mf'), (0.4, 'f'), (1, 'f')], 'cap': 'f', 'level': 0.85, 'tex': {'tutti_drive': 1.0},
          'kinds': ('recap2', 'recap', 'river', 'refrain', 'var', 'episode', 'trio', 't1', 't2')},
    runup={'arcs': ('late',), 'ends': ('cut',), 'drop': ('recap2',), 'retrans': 6},
)
"""Round o25 (SHAPE3 - o24b's judges, B per piece -1.86 se: "38 quiet bars after the climax at 65 %", "the chorale
climax homorhythmic brass on stepwise lines", the late / cut slots lost): SHAPE2 with
'aftermath' - the moved blocks after an early / mid climax are a release AND a second build (one block: f, down to mp,
back to f; two or more: the first falling to mp, the last rising mp -> f), then 'rise' - the first return after them
(these kinds) a rising theme return at f in the driving tutti (LOUDEST cap f, under the climax's ff) before the
ending;
'climax_tex' chorale - apex_chorale3: the brass choir's chorale with the strings hammering the motto's rhythm around
it and a walking bass (not held chords); 'cut' - the end's hammered chords in the motto's rhythm (hammer_motto);
'runup' - the late arc / the cut ending without the second theme's return before the build ('drop') and the build
('retrans') at most 6 bars: a shorter way into the climax."""
MACRO3_ON = dict(MACRO2_ON, v2=MACRO3_V2)
"""SHAPE3 on (round o25, genres.symphony_shape3): MACRO2_ON with MACRO3_V2."""


def _shape_opens(genre, feel: str, layout: str) -> tuple:
    X = MACRO or MACRO_ON
    first = _rows(genre, layout)[0][1]
    return tuple(o for o in X['opens'][first if first in ('intro', 'source') else None]
                 if o != 'dance' or feel in X['fast'])


def shape_draw(genre, feel: str, layout: str, mood: str, coda: str, rng, history=(), n: int | None = None,
               ban=(), dance: bool = True) -> dict:
    """One piece's macro shape (MACRO): {'open', 'arc', 'climax', 'end', 'at'} - drawn among the combinations the
    layout / feel / mood / coda allow, weighted, with the set's memory over EVERY earlier slot (history: their shape
    dicts, oldest first; n the set's size): no dimension as the slot before's, no value more than ceil(n / its
    choices) times, no (open, arc, end) twice - relaxed in that order where nothing is left. ban: arcs the piece cannot
    realise (shape_slot); dance False: no dance opening (the pizzicato choir was too recent - TECH_V2 'pizz_gap')."""
    X = MACRO or MACRO_ON
    opens = tuple(o for o in _shape_opens(genre, feel, layout) if dance or o != 'dance') or \
        _shape_opens(genre, feel, layout)
    M = genre.moods[mood]
    quiet = (M.get('climax') or CLIMAX_DEFAULT).get('quiet', 0) > 0
    arcs = [a for a in X['arc'] if (a != 'inverse' or quiet) and a not in ban] or ['classic']
    ends = X['ends'].get(coda, X['ends']['triumph'])
    hist = [h for h in history if isinstance(h, dict)]
    N = max(int(n or 0), len(hist) + 1)
    last = hist[-1] if hist else {}
    dims = {'open': len(X['open']), 'arc': len(X['arc']), 'end': len(X['end']), 'climax': len(X['climax']) + 1}
    caps = {d: max(1, int(math.ceil(N / float(v) - 1e-9))) for d, v in dims.items()}
    count = {d: {} for d in dims}
    for h in hist:
        for d in dims:
            count[d][h.get(d)] = count[d].get(h.get(d), 0) + 1
    triples = {(h.get('open'), h.get('arc'), h.get('end')) for h in hist}
    combos = []
    for o in opens:
        for a in arcs:
            for e in ends:
                if (a in X['arc_ends'] and e not in X['arc_ends'][a]) or \
                        (e in X['end_arcs'] and a not in X['end_arcs'][e]):
                    continue
                for c in (('quiet',) if a == 'inverse' else tuple(X['climax'])):
                    w = X['open'][o] * X['arc'][a] * X['end'][e] * (1.0 if c == 'quiet' else X['climax'][c])
                    combos.append(((o, a, e, c), w))
    if not combos:                         # (an arc that needs an ending the coda kind has not: the arc relaxed)
        combos = [((o, 'mid', e, 'strings'), 1.0) for o in opens for e in ends]

    def ok(x, level):
        o, a, e, c = x
        v = {'open': o, 'arc': a, 'end': e, 'climax': c}
        near = ('open', 'arc', 'end', 'climax') if level == 0 else ('open', 'arc') if level == 1 else \
            ('arc',) if level in (2, 3) else ()
        if any(last.get(d) == v[d] for d in near):
            return False
        if level <= 2 and any(count[d].get(v[d], 0) >= caps[d] for d in dims if level <= 1 or d != 'end'):
            return False
        return level > 0 or (o, a, e) not in triples
    for level in range(5):
        cand = [(x, w) for x, w in combos if ok(x, level)]
        if cand:
            break
    keys = {x: rng.random() ** (1.0 / w) for x, w in sorted(cand)}
    o, a, e, c = max(sorted(keys), key=lambda x: keys[x])
    lo, hi = X['at'][a]
    return {'open': o, 'arc': a, 'climax': c, 'end': e, 'at': round(lo + (hi - lo) * rng.random(), 3)}


def shape_slot(genre, slot: dict, history: list, n: int, rng) -> None:
    """composer.set_plan's hook (plan['set_macro'], round o24): the slot's macro shape (slot['shape'], shape_draw with
    the set's memory) and - TECH v2 - its technique ranking with the WHOLE set's memory (slot['tech2'], tech_rank_v2;
    slot['tech_crown']: whether its climax may be crowned by a trill). Own dice: master's draws unchanged."""
    F = genre.feels[slot['feel']]
    fs = _form_seed(slot, slot['key'], 0)
    layout = _layout_of(genre, F, slot, fs)
    coda = _coda_of(genre.moods[slot['mood']], slot, fs)
    X = MACRO or MACRO_ON
    hist = [h.get('shape') for h in history]
    dance = not _pizz_recent(history)
    ban, best = set(), None
    for _ in range(X['tries']):             # (an arc the layout cannot realise - its climax placed far off - banned)
        sh = shape_draw(genre, slot['feel'], layout, slot['mood'], coda, random.Random(f"{rng.random()}:shape"),
                        hist, n, ban=ban, dance=dance)
        pos = _realized_peak(genre, slot, sh)
        miss = abs(pos - sh['at']) if pos is not None else 0.0
        if best is None or miss < best[0]:
            best = (miss, sh)
        if miss <= X['tol']:
            break
        ban.add(sh['arc'])
    sh = best[1]
    if X.get('v2'):                         # (round o24b, SHAPE2: the set's memory on the motto / t1 / bass figures)
        sh = dict(sh, **_shape2_extras(genre, slot, history, n, random.Random(f"{rng.random()}:shape2")))
    slot['shape'] = sh
    if TECH and TECH.get('v2') and not genre.plan.get('set_tech2'):
        rank, crown = tech_rank_v2(slot['feel'], random.Random(f"{rng.random()}:tech"), history, sh)
        slot['tech2'], slot['tech_crown'] = rank, crown


def _shape2_extras(genre, slot: dict, history: list, n: int, rng) -> dict:
    """SHAPE2 (MACRO2_V2): the slot's motto cell (its rhythm family not heard in the set before, else the least heard
    one), its first theme's texture and its pumping bass's figures, each with the WHOLE set's memory - by the earlier
    slots' shapes (history) and their own draws."""
    V = MACRO['v2']
    F = genre.feels[slot['feel']]
    fam = F['family']
    hist = [h for h in history if isinstance(h, dict)]
    N = max(int(n or 0), len(hist) + 1)
    out = {}

    def eff(h, key):
        sh_ = h.get('shape') if isinstance(h.get('shape'), dict) else {}
        return sh_.get(key, h.get(key))
    # the motto's rhythm family
    fams = MOTTO_FAMILIES.get(fam, {})
    cells = [c for c in sorted(CELLS.get(fam, {})) if c in fams]
    cell = (slot.get('motto') or {}).get(fam)
    used = {}
    for h in hist:
        if genre.feels[h['feel']]['family'] != fam:
            continue
        c_ = (eff(h, 'motto') or {}).get(fam)
        if c_ in fams:
            used[fams[c_]] = used.get(fams[c_], 0) + 1
    if cell in fams and used.get(fams[cell], 0) > 0 and cells:
        least = min(used.get(fams[c], 0) for c in cells)
        pool = [c for c in cells if used.get(fams[c], 0) == least]
        out['motto'] = dict(slot.get('motto') or {}, **{fam: pool[rng.randrange(len(pool))]})
    # the first theme's texture
    T1 = TEX_V3['t1']
    t1 = slot.get('tex_t1')
    seen = [eff(h, 'tex_t1') for h in hist]
    near = set(seen[-V['tex_t1_near']:])
    cnt = {x: seen.count(x) for x in T1}
    if t1 in T1 and (t1 in near or cnt[t1] >= V['tex_t1_cap']):
        w = {x: v for x, v in T1.items() if x not in near and cnt[x] < V['tex_t1_cap']} or \
            {x: v for x, v in T1.items() if x != t1}
        keys = {x: rng.random() ** (1.0 / v) for x, v in sorted(w.items())}
        out['tex_t1'] = max(sorted(keys), key=lambda x: keys[x])
    # the pumping bass's figures
    kind = 'duple' if fam == 'duple' else 'compound'
    figs = BASS_FIGS.get(kind, {})
    bc = {}
    for h in hist:
        for x in (eff(h, 'bass_figs') or ()):
            bc[x] = bc.get(x, 0) + 1
    last = set(eff(hist[-1], 'bass_figs') or ()) if hist else set()
    capd = {x: max(1, int(math.ceil(V['bass_cap'].get(x, N) * N / 8.0 - 1e-9))) for x in figs}
    order = sorted(figs, key=lambda x: (bc.get(x, 0) >= capd[x], x in last, bc.get(x, 0), rng.random()))
    out['bass_figs'] = sorted(order[:V['bass_n']])
    return out


def tech2_slot(genre, slot: dict, history: list, rng) -> None:
    """composer.set_plan's hook (plan['set_tech2'], round o24b - TECH2 alone, genres.symphony_tech2): the slot's
    technique ranking with the WHOLE set's memory (slot['tech2'], slot['tech_crown'], tech_rank_v2) on its own dice,
    after the macro shape when there is one (MACRO: its ending / opening), else the slot's coda kind (a dissolving
    coda is the soft ending the harmonics are weighted up for)."""
    sh = slot.get('shape') if MACRO and isinstance(slot.get('shape'), dict) else None
    if sh is None:
        fs = _form_seed(slot, slot['key'], 0)
        coda = _coda_of(genre.moods[slot['mood']], slot, fs)
        sh = {'end': 'dying' if CODA_KINDS.get(coda, ('coda',))[0] == 'coda_soft' else 'loud'}
    slot['tech2'], slot['tech_crown'] = tech_rank_v2(slot['feel'], rng, history, sh)


def _pizz_recent(history) -> bool:
    """TECH v2: the pizzicato choir (or a dance opening) featured within TECH_V2['pizz_gap'] slots before."""
    T = TECH or TECH_ON
    V = T.get('v2') or TECH_V2
    for h in list(history)[-V['pizz_gap']:]:
        sh_ = h.get('shape') if isinstance(h, dict) else None
        if (isinstance(sh_, dict) and sh_.get('open') == 'dance') or \
                'pizz_choir' in list((h['tech2'] if 'tech2' in h else h.get('tech')) or ())[:T['feature']]:
            return True
    return False


def _realized_peak(genre, slot: dict, sh: dict):
    """The climax centre a slot's piece would get with the macro shape sh (bar_plan's rows: form_rows + _place_v3)."""
    if not (SET_PLAN and SET_PLAN.get('v3')):
        return None
    F = genre.feels[slot['feel']]
    M = genre.moods[slot['mood']]
    d = _macro_draws(dict(slot, shape=sh)) if MACRO else dict(slot, shape=sh)
    fs = _form_seed(d, d['key'], 0)
    layout = _layout_of(genre, F, d, fs)
    U = 4.0 if F['family'] == 'duple' else 3.0
    sc = F.get('scale', 1)
    tempo = d.get('tempo')
    rows = form_rows(genre, layout, d, F, fs, bar_s=U * sc * 60.0 / tempo if tempo else None)
    rows = _place_v3(genre, rows, d, F, U, tempo, _coda_of(M, d, fs))
    return _peak_pos(genre, rows)


def _macro_draws(draws: dict) -> dict:
    """MACRO: the piece's draws as its macro shape needs them (idempotent): the opening's kind and no slow introduction
    before a loud / solo / plunging start, the climax's type."""
    sh = draws.get('shape') if MACRO else None
    if not isinstance(sh, dict):
        return draws
    d = dict(draws)
    o = sh.get('open')
    if o == 'motto':
        d.update(intro='call', slow=0)
    elif o == 'solo':
        d.update(intro='solo', slow=0)
    elif o == 'soft' and d.get('intro') in ('call', 'solo'):
        d['intro'] = 'mist'
    elif o in ('medias', 'dance'):
        d['slow'] = 0
    if sh.get('climax'):
        d['climax'] = sh['climax']
    if isinstance(sh.get('motto'), dict):       # (round o24b, SHAPE2: the set's memory on the motto / t1)
        d['motto'] = dict(sh['motto'])
    if sh.get('tex_t1'):
        d['tex_t1'] = sh['tex_t1']
    return d


def _macro_rows(genre, rows, sh: dict) -> list:
    """MACRO on the layout's rows (form_rows, before the lengths): in medias res / the dance - the opening block left
    out, the first theme's texture and dynamics; the 'cut' ending - no coda; the late climax - the second theme's
    return moved before the build (the climax then needs no long return after it)."""
    X = MACRO
    rows = list(rows)
    o, a, e = sh.get('open'), sh.get('arc'), sh.get('end')
    if o in ('medias', 'dance'):
        while len(rows) > 1 and rows[0][1] in ('intro', 'source'):
            rows.pop(0)
        n0, k0, b0, o0 = rows[0]
        if k0 in ('t1', 'river'):
            Y = X[o]
            rows[0] = (n0, k0, b0, dict(o0, tex=dict(Y['tex']), sh_dyn=list(Y['dyn']), sh=o,
                                        **({'sh_cap': Y['cap']} if Y.get('cap') else {})))
    if e == 'cut' and any(r[1] == 'end' for r in rows):
        rows = [r for r in rows if r[1] != 'coda']
    if a in ('early', 'mid', 'inverse'):      # (the arch's second theme before the build: after the climax now)
        pi = _peak_index(genre, rows)
        if pi is not None:
            r2 = next((i for i in range(pi - 1, -1, -1) if rows[i][1] == 'recap2'), None)
            if r2 is not None:
                rows.insert(pi, rows.pop(r2))
    V = X.get('v2')
    R3 = V.get('runup') if V and V.get('v3') else None
    if R3 and (a in R3['arcs'] or e in R3['ends']):   # (round o25, SHAPE3: a shorter way into the late / cut climax)
        if _peak_index(genre, rows) is not None:
            rows = [r for r in rows if r[1] not in R3['drop']]
            rows = [(n_, k_, min(b_, R3['retrans']) if k_ == 'retrans' else b_, o_) for n_, k_, b_, o_ in rows]
    if a == 'late':
        pi = _peak_index(genre, rows)
        if pi is not None:
            r2 = next((i for i in range(pi + 1, len(rows)) if rows[i][1] == 'recap2'), None)
            rt = next((i for i in range(pi - 1, -1, -1) if rows[i][1] == 'retrans'), None)
            if r2 is not None and rt is not None:
                rows.insert(rt, rows.pop(r2))
    V = X.get('v2')
    if V and a in V['arcs_move'] and sh.get('at') is not None:
        rows = _macro_move(genre, rows, float(sh['at']), V)
    if V and e == 'cut':                      # (round o24b: the cut ends ON the climax - its returns before it)
        pi = _peak_index(genre, rows)
        rt = next((i for i in range(pi - 1, -1, -1) if rows[i][1] == 'retrans'), None) if pi is not None else None
        if rt is not None:
            post = [r for r in rows[pi + 1:] if r[1] not in ('end', 'end_soft')]
            rows = rows[:rt] + post + rows[rt:pi + 1] + [r for r in rows[pi + 1:] if r[1] in ('end', 'end_soft')]
    return rows


def _macro_move(genre, rows, at: float, V: dict) -> list:
    """SHAPE2's early / mid arc: the development's blocks before the retransition (V['move'] kinds, latest first; never
    the first two rows) go after the climax - right after it and the blocks moved before them - as its aftermath
    (V['after']: falling from f, LOUDEST cap f), until the climax's centre is at `at` + 0.03 or less."""
    rows = list(rows)
    for _ in range(4):
        pi = _peak_index(genre, rows)
        pos = _peak_pos(genre, rows)
        if pi is None or pos is None or pos <= at + 0.03:
            break
        rt = pi - 1 if pi > 0 and rows[pi - 1][1] == 'retrans' else pi
        cand = [i for i in range(rt - 1, 1, -1) if rows[i][1] in V['move'] and not rows[i][3].get('false') and
                not rows[i][3].get('collapse')]
        if not cand:
            break
        pref = {k_: j for j, k_ in enumerate(V['move'])}
        i = min(cand, key=lambda j: (pref[rows[j][1]], -j))
        n_, k_, b_, o_ = rows.pop(i)
        pi -= 1
        z = pi + 1
        while z < len(rows) and rows[z][3].get('sh') == 'after':
            z += 1
        rows.insert(z, (n_, k_, b_, dict(o_, sh='after', sh_dyn=list(V['after']['dyn']), sh_cap=V['after']['cap'])))
    return rows


def _macro_marks(genre, rows, sh: dict) -> list:
    """MACRO on the placed rows (material, after the joins): the twin peak (the exposition block nearest
    MACRO['twin']['centre'] of the piece made an f summit, past the LOUDEST 'pre' cap), the early arc's second summit
    in the coda (f to ff), the surprise (the block before the dissolving coda held f, the coda subito pp), the cut's
    end in the climax's ff."""
    X = MACRO
    rows = list(rows)
    a, e = sh.get('arc'), sh.get('end')
    pi = _peak_index(genre, rows)
    tot = float(max(1, sum(r[2] for r in rows)))

    def put(i, **kw):
        n_, k_, b_, o_ = rows[i]
        rows[i] = (n_, k_, b_, dict(o_, **kw))
    if a == 'twin' and pi:
        T = X['twin']
        c, best = 0.0, None
        for i, (n_, k_, b_, o_) in enumerate(rows[:pi]):
            mid = (c + b_ / 2.0) / tot
            c += b_
            if k_ in T['kinds'] and T['at'][0] <= mid <= T['at'][1] and not o_.get('false'):
                key_ = (0 if k_ in T['loud'] else 1, abs(mid - T['centre']), i)
                if best is None or key_ < best[0]:
                    best = (key_, i)
        if best is not None:
            i = best[1]
            kw = dict(sh_dyn=list(T['dyn']), sh_cap='f', sh='twin', level=0.85)
            if rows[i][1] not in T['loud']:
                kw['tex'] = dict(T['tex'])
            put(i, **kw)
    ci = next((i for i, r in enumerate(rows) if r[1] == 'coda'), None)
    V = X.get('v2')
    if a == 'early' and ci is not None and pi is not None and ci > pi and not V:
        put(ci, sh_dyn=list(X['second']['dyn']), sh_cap=X['second']['cap'], sh='second')
    if e == 'surprise' and ci is not None and pi is not None and ci > pi:
        put(ci, sh_dyn=list(X['surprise']['coda']), sh='surprise')
        if ci - 1 != pi and ci - 1 > pi:
            put(ci - 1, sh_dyn=list(X['surprise']['before']), sh_cap='f')
    if e == 'cut' and pi is not None and pi + 1 < len(rows) and rows[pi + 1][1] == 'end':
        put(pi + 1, sh_dyn=[(0, 'ff')], sh_cap='ff', sh='cut')
        if V:                                   # (round o24b: the cut at the climax's level, no fade)
            put(pi + 1, sh_dyn=list(V['cut']['dyn']), sh_cap=V['cut']['cap'], level=V['cut']['level'],
                sh_tex=dict(V['cut']['tex']))
    if V and e == 'loud' and pi is not None:    # (round o24b: the loud ending at the climax's level)
        for i in range(pi + 1, len(rows)):
            k_ = rows[i][1]
            if k_ in ('coda', 'end') and rows[i][3].get('sh') != 'after':
                L = V['loud'][k_]
                put(i, sh_dyn=list(L['dyn']), sh_cap=L['cap'], level=L['level'], sh='loud')
    if V and V.get('v3') and pi is not None:    # (round o25, SHAPE3: the aftermath a second build, a rising return)
        run = []
        for i in range(pi + 1, len(rows)):      # (the moved blocks and any development block among them)
            if rows[i][3].get('sh') != 'after' and (rows[i][1] not in V['move'] or rows[i][3].get('sh')):
                break
            run.append(i)
        if run and not any(rows[i][3].get('sh') == 'after' for i in run):
            run = []                            # (only after a moved climax)
        A3 = V['aftermath']
        for j, i in enumerate(run):
            d_ = A3['one'] if len(run) == 1 else A3['first'] if j == 0 else \
                A3['last'] if j == len(run) - 1 else A3['mid']
            put(i, sh_dyn=list(d_))
        if run:
            R_ = V['rise']
            nxt = run[-1] + 1
            if nxt < len(rows) and rows[nxt][1] in R_['kinds'] and not rows[nxt][3].get('sh'):
                put(nxt, sh_dyn=list(R_['dyn']), sh_cap=R_['cap'], level=R_['level'], sh='rise',
                    sh_tex=dict(R_['tex']))
    return rows


def build_symphony(tune, genre=None, arrangement=None) -> Song:
    """The Song of a symphonic tune (the module docstring). Deterministic from the tune; arrangement: an Arrangement
    record (kind 'symphony') to replay (default tune.arrangement)."""
    from .arrangement import Dice
    from .composer import _pick as pk
    from .genres import get
    g = genre or get(tune.genre)
    P, BD = g.plan, g.band
    mat = _material_of(tune, g)
    k = float(mat['scale'])
    U = mat['U']
    sd = tune.seed
    F = g.feels[tune.feel]
    if arrangement is None:
        arrangement = getattr(tune, 'arrangement', None)
    dice = Dice('symphony', arrangement)
    sw = g.moods[tune.mood]['size']
    pin = (tune.arrange or {}).get('size')
    if sw.get(pin, 0) > 0:                 # (the set's orchestra size, where the mood has it: chamber pieces in a set)
        sw = {pin: 1.0}
    size = dice.pick(None, 'size', random.Random(f"sym-size:{sd}"), sw)
    table = orch.role_table(BD['preset'])
    roles = [r for r in P['sizes'][size] if r in table]

    def pick(block, key, weights):
        if not weights:
            return None
        r_ = random.Random(f"sym:{sd}:{block}:{key}")
        if key in RECORDED:
            return dice.pick(block, key, r_, weights)
        return pk(r_, weights)
    meter = tuple(F['time_sig'])
    s = Song(tune.title, tempo=tune.tempo, key=tune.key, seed=sd % 100000 + 1, tail=8, meter=meter)
    bpb = s.beats_per_bar
    # (round o22, JOIN_V4: a merged block's later parts sound in the section of the block they join)
    sec_of = {}
    groups = []
    for blk in mat['blocks']:
        if blk.get('joined') and groups:
            groups[-1][1] += blk['bars']
        else:
            groups.append([blk['name'], blk['bars']])
        sec_of[blk['name']] = groups[-1][0]
    for name_, nb_ in groups:
        s.section(name_, bars=nb_ * U * k / bpb)
    score = orc.OrchScore(tune.title, tune.key, int(bpb), tune.tempo)
    pre_peak = True
    for blk in mat['blocks']:
        a, L = blk['start'] * k, blk['bars'] * U * k
        K = kind_data(g, blk['kind'], blk['over'])
        pre_peak = pre_peak and not blk['peak']
        marks = []
        for x in K.get('dyn') or (('mf',),):
            if len(x) == 1:
                marks.append((a, x[0]))
            else:
                marks.append((a + x[0] * L - (0.01 if x[0] >= 1 else 0.0), x[1]) + tuple(x[2:]))
        sh_cap = blk['over'].get('sh_cap') if MACRO else None      # (round o24: a macro shape's own summit)
        if LOUDEST and mat.get('climax') == 'quiet' and LOUDEST.get('quiet') and not blk['peak'] and \
                blk['kind'] not in LOUDEST['free'] and not sh_cap:
            # (round o11: a quiet climax is the summit too - every other block under its f)
            marks = [m[:1] + (_mark_min(m[1], LOUDEST['quiet']),) + m[2:] for m in marks]
        if LOUDEST and mat.get('climax') != 'quiet':
            # (round o10 - o9's judges: "the loudest music in the middle", EMWY / BLMX: the peak the loudest block)
            if blk['peak']:
                marks = [m[:1] + (_mark_max(m[1], LOUDEST['peak']),) + m[2:] for m in marks]
            elif blk['kind'] not in LOUDEST['free']:
                cap_ = LOUDEST.get('pre') if pre_peak and LOUDEST.get('pre') and                     blk['kind'] not in LOUDEST.get('pre_free', ()) else LOUDEST['cap']
                if sh_cap and _MARK_ORDER.index(sh_cap) > _MARK_ORDER.index(cap_):
                    cap_ = sh_cap
                marks = [m[:1] + (_mark_min(m[1], cap_),) + m[2:] for m in marks]
        chart = [(x * k, d * k, sy) for x, d, sy in blk['chart']]
        score.block(blk['name'], a, L, chart, key=blk['key'], marks=marks, peak=blk['peak'],
                    frame='end' if blk['kind'] == 'end' else None)
    weights = {blk['name']: dict(kind_data(g, blk['kind'], blk['over'])['tex']) for blk in mat['blocks']}
    if mat['scale'] == 2:                    # (round o6: the scherzo's tune on top - SCHERZO_TEX)
        for blk in mat['blocks']:
            if blk['kind'] in SCHERZO_TEX['kinds']:
                sub = {}
                for t_, x in weights[blk['name']].items():
                    t_ = SCHERZO_TEX['tex'].get(t_, t_)
                    sub[t_] = sub.get(t_, 0.0) + x
                weights[blk['name']] = sub
    if not {'trumpets', 'trombones'} <= set(roles):      # (the chamber orchestra: a plan that needs the brass takes
        for name, w in weights.items():                    # its CHAMBER stand-in - round o3: the climax's
            sub = {}                                       # tutti_symphonic became the next plan's weight, a
            for t_, x in w.items():                        # 'tutti_drive' at 0.05)
                if orc.TEXTURES[t_].get('size') == 'full':
                    t_ = CHAMBER.get(t_, 'apotheosis_strings' if orc.TEXTURES[t_].get('peak') else 'tutti_drive')
                sub[t_] = sub.get(t_, 0.0) + x
            weights[name] = sub
    joins = [blk['name'] for blk in mat['blocks'] if blk.get('joined')]
    for name in joins:                     # (round o22: a new texture at the join - JOIN_V4; the kind's own as the
        own_ = dict(g.plan['kinds'][next(b['kind'] for b in mat['blocks'] if b['name'] == name)].get('tex') or {})
        for t_, x in own_.items():         # alternatives where the drawn one is the texture before the join)
            if t_ not in weights[name] and t_ in orc.TEXTURES and \
                    ({'trumpets', 'trombones'} <= set(roles) or orc.TEXTURES[t_].get('size') != 'full'):
                weights[name][t_] = 0.3 * x
    tech = _tech_pre(mat, score, tune, weights) if TECH else None      # (round o23: the pizzicato choir's block)
    orc.plan_blocks(score, weights, roles, pick, rules=P.get('rules'), change=joins)
    rhythm = [(on * k, du * k) for on, du, _ in cell_of(mat['motto'])]
    in_bass = set()                         # (the blocks whose theme the texture gave to the bass)
    bass_prev = None                        # (round o10: the pump bass's figure of the block before - BASS_FIGS)
    arrive = pk(random.Random(f"sym-arrive:{sd}"), ARRIVALS)
    at_peak = {x.name for i, x in enumerate(score.blocks) if x.peak or
               (i + 1 < len(score.blocks) and score.blocks[i + 1].peak)}
    for blk, b in zip(mat['blocks'], score.blocks):
        T = orc.TEXTURES[b.texture]
        need = orc.needs(b.texture)
        rs = random.Random(f"sym-lines:{sd}:{b.name}")
        theme = _scaled(blk['theme'], k)
        if blk['answer'] and not ('counter' in need and b.meta.get('counter', 'none') != 'none'):
            # (round o3: a counter-line where the texture has no counter role - the climax's motto answering the
            # second theme, the development's imitation - joins the melody's line, never chords on its role;
            # round o4: a recapitulation's counter-line under a whole theme is left out instead)
            if (blk['kind'] not in ('recap', 'recap2') or blk['peak']) and not blk.get('recalled'):
                theme = _mono(sorted(theme + _scaled(blk['answer'], k)))
            blk = dict(blk, answer=[])
        blk['theme_song'] = theme
        blk['grid'] = F.get('grid', 0.25) * k
        blk['bar'] = bpb
        # (sforzandi on the theme's arrivals: a long note after a shorter one, one a bar - round o4: a recap of
        # half notes was all sforzandi, its doubling at 127 throughout and the gate's flat_dynamics)
        sfs, bars_ = [], set()
        for i, (a, d, _) in enumerate(theme if blk['sf'] else ()):
            if d >= 1.0 - _EPS and (i == 0 or theme[i - 1][1] < d - _EPS) and int(a // bpb) not in bars_:
                sfs.append(a)
                bars_.add(int(a // bpb))
        top = theme
        if blk['voices'] and blk.get('fugue'):          # (FUGUE: the basses double the bass voice from its entry)
            for v, ns in sorted(blk['voices'].items()):
                b.add(orc.Line('voice', _scaled(ns, k), voice=v))
            low = [(a_, min(d_, b.end - a_), p_) for a_, d_, p_ in _scaled(blk['fugue']['bass'], k) if a_ < b.end - _EPS]
            if 'bass' in need and low:
                b.add(orc.Line('bass', low))
            top = _scaled(blk['voices'].get('v1', []), k)
            cs_ = _scaled(blk['fugue'].get('cs_notes') or [], k)    # (FUGUE v2: the counter-subject's own colour)
            if cs_ and 'counter' in need and b.meta.get('counter', 'none') != 'none':
                b.add(orc.Line('counter', cs_))
        elif blk['voices']:
            for v, ns in sorted(blk['voices'].items()):
                b.add(orc.Line('voice', _scaled(ns, k), voice=v))
            low = _scaled(blk['voices'].get('v4', []), k)
            if 'bass' in need and low:
                b.add(orc.Line('bass', [(a, d, p - 12) for a, d, p in low if a >= b.start + b.length / 2 - _EPS]
                               or [(a, d, p - 12) for a, d, p in low]))
            top = _scaled(max(blk['voices'].values(), key=lambda ns: sum(p for _, _, p in ns) / max(1, len(ns))), k)
        elif theme:
            if T.get('theme') == 'bass' or ('melody' not in need and 'bass' in need):
                low = theme
                while min(p for _, _, p in low) > 50:
                    low = [(a, d, p - 12) for a, d, p in low]
                b.add(orc.Line('bass', low, meta={'sf': sfs}))
                in_bass.add(b.name)
                top = []
            elif 'melody' in need:
                b.add(orc.Line('melody', theme, meta={'sf': sfs}))
                if blk['kind'] in ('coda', 'end', 'close', 'recap') and 'bass' in need and \
                        need['bass'][0].get('figure') == 'theme':
                    # (round o7 - o6's judges: "the tuba doubles the tune", "the basses play the melody": the
                    # theme's rhythm on the chords' bass notes under a tune on top - UNISON_KINDS keep the unison)
                    b.add(orc.Line('bass', _bass_in_rhythm(theme, b.chart, blk['key'], rs.random())))
            elif 'figuration' in need:
                pass
        if blk['answer']:
            ans = _scaled(blk['answer'], k)
            if 'counter' in need and b.meta.get('counter', 'none') != 'none':
                b.add(orc.Line('counter', ans))
            elif 'melody' in need:
                b.add(orc.Line('melody', ans))
        elif 'counter' in need and b.meta.get('counter', 'none') != 'none' and theme and 'melody' in need and \
                blk['kind'] not in ('end', 'end_soft'):
            bass = eo._bass(b.chart, blk['key'], 0.0, rs.random())
            cl = eo._counter(b.chart, theme, bass, blk['key'], int(bpb), rs.random())
            if cl:
                b.add(orc.Line('counter', cl))
        if 'bass' in need and need['bass'][0].get('figure') == 'theme' and not b.get('bass') and theme:
            if blk['kind'] in UNISON_KINDS or 'melody' not in need:
                low = theme
                while min(p for _, _, p in low) > 50:
                    low = [(a, d, p - 12) for a, d, p in low]
            else:
                low = _bass_in_rhythm(theme, b.chart, blk['key'], rs.random())
                if blk['kind'] in ('end', 'end_soft'):
                    low = _end_bass(low, next(iter(need['bass'][0].get('pick') or {'cellos': 1})))
            b.add(orc.Line('bass', low, meta={'sf': sfs}))
        bfig = None
        if BASS_FIGS and U * k != 6 and 'bass' in need and need['bass'][0].get('figure') == 'pump':
            w_ = {x: v for x, v in BASS_FIGS['duple' if U * k == 4 else 'compound'].items() if x != bass_prev}
            sh2_ = (tune.arrange or {}).get('shape') if MACRO and MACRO.get('v2') else None
            if isinstance(sh2_, dict) and sh2_.get('bass_figs'):   # (round o24b: SHAPE2's set memory on them)
                w_ = {x: v for x, v in w_.items() if x in sh2_['bass_figs']} or \
                    {x: v for x, v in BASS_FIGS['duple' if U * k == 4 else 'compound'].items()
                     if x in sh2_['bass_figs']} or w_
            bfig = bass_prev = pk(random.Random(f"sym-bass:{sd}:{b.name}"), w_)
        extra_ = {}
        if blk.get('chroma'):                   # (CHROMA_CADENCE's chromatic chords in song beats)
            extra_['chroma'] = [(a_ * k, d_ * k, rn_, tg_) for a_, d_, rn_, tg_ in blk['chroma']]
        _write_accompaniment(b, dict(blk, pedal=_scaled(blk['pedal'], k), acc=(tune.arrange or {}).get('acc'),
                                     arrive=arrive if b.name in at_peak else None, bass_fig=bfig, **extra_),
                             need, blk['key'], U * k, top, rs, rhythm)
        if blk.get('entries'):                  # (DEV_WALK v3: the stretto's tenor and bass entries)
            _walk_entries(b, blk['entries'], k)
        if blk.get('fugue') and blk['fugue'].get('pad') is not None:     # (FUGUE v2: the pad until the third entry)
            z_ = blk['fugue']['pad'] * k
            for x in b.get('harmony'):
                x.notes = [(a_, min(d_, z_ - a_), p_) for a_, d_, p_ in x.notes if a_ < z_ - _EPS]
        if blk.get('fug_return'):               # (FUGUE v2: the subject in the bass at the summit, over its span)
            ret_ = _scaled(blk['fug_return'], k)
            a_r, z_r = ret_[0][0], ret_[-1][0] + ret_[-1][1]
            for x in b.get('bass'):
                x.notes = sorted([(a_, min(d_, a_r - a_), p_) for a_, d_, p_ in x.notes if a_ < a_r - _EPS] +
                                 [n_ for n_ in x.notes if n_[0] >= z_r - _EPS] + ret_)
            if 'bass' in need and not b.get('bass'):
                b.add(orc.Line('bass', ret_))
    R_ = dict(orc.RULES, **(P.get('rules') or {}))
    summit = bool(SUMMIT and R_.get('reserve'))      # (round o12: the summit raised first, then the reserve under it)
    plan_o = orc.orchestrate(score, {r: table[r] for r in roles}, pick,
                             rules=dict(P.get('rules') or {}, reserve=False) if summit else P.get('rules'))
    if summit:
        itab = orc._idiom_table({r: table[r] for r in roles}, R_)
        _summit(plan_o, score, roles, itab, R_, bar=bpb, voicing=(tune.arrange or {}).get('voicing')
                if SET_PLAN and SET_PLAN.get('voicing') else None)
        orc._reserve(plan_o, score, itab, margin=1 if R_['reserve'] is True else int(R_['reserve']),
                     after=bool(R_.get('reserve_after')), lines=R_.get('reserve_lines'))
        plan_o.notes = sum(len(p.notes) for p in plan_o.parts)
    _rt_drive(plan_o, score, mat, k, bpb, tune.key, roles)
    _orchestra_pass(plan_o, score, tune.key, size, roles, table)
    if CHROMA_EVENT:                         # (round o15b: the chromatic events on the whole orchestra)
        for blk in mat['blocks']:
            if blk.get('event'):
                _event_tutti(plan_o, score, blk['event'], blk['name'], k, roles, table, R_)
    _vary_runs(plan_o, score, {blk['name']: blk['kind'] for blk in mat['blocks']}, bpb)
    _unfold_all(plan_o, table)
    if SET_PLAN:                             # (round o18b: the build's silence, the codas' colours)
        _set_plan_pass(plan_o, mat, k, (tune.arrange or {}).get('ending'))
    ons = [on for on, _, _ in cell_of(mat['motto']) if on < U - _EPS] if STROKES.get('motto') else []
    for blk in mat['blocks']:
        if blk.get('strokes'):
            _strokes(plan_o, blk['name'], blk.get('approach', blk['start']) * k, U * k,
                     [x * k for x in (ons if 2 <= len(ons) <= 5 else STROKES[mat['family']])])
    if tech is not None:                     # (round o23: the playing techniques - TECHNIQUES)
        s.tech_events = []
        _tech_pass(plan_o, score, mat, tune, roles, tech, s.tech_events, bar=U * k)
        s.tech_plan = tech
    from . import choir as CH
    ch = CH.prepare(plan_o, score, mat, tune, k) if CH.CHOIR else None      # (round oc1: the choir's events)
    from . import hero_sax as HS
    sax_events = HS.prepare(plan_o, score, tune, ch)
    from . import solo as solo_
    if solo_.SOLO:                           # (round os1: the solo players - solo.solo_pass)
        s.solo_events = solo_.solo_pass(plan_o, score, mat, tune, bpb)
    from . import colour as CO
    cl = CO.prepare(plan_o, score, mat, tune, k, roles,
                    reserved=[(e['start'], e['end']) for e in sax_events]) if CO.COLOUR else None
    accent_support = _theme_accents(plan_o, score)
    exposed_answers = _exposed_answers(plan_o)
    used = plan_o.roles()
    b_ = eo.band(s, used, g)
    if solo_.SOLO and solo_.SOLO.get('polish'):     # (round op1: the concertmaster's fader)
        solo_.polish_band(b_)
    marks = sorted((m for x in score.blocks for m in x.marks), key=lambda m: (m[0], len(m)))
    sc = orch.Score(s, b_, marks, key=tune.key, seed=sd % 9973, style=BD.get('style', 'romantic'))
    if PUMPING:
        sc.phrasing = {role: value * PUMPING['phrasing'] for role, value in sc.phrasing.items()}
    if solo_.SOLO and solo_.SOLO.get('rules'):      # (round os1: the sections' deeper swells, smoother legato)
        sc.rules = solo_.SOLO['rules']
    if CHROMA_EVENT:
        _event_marks(sc, mat, k)
    # ---- the tempo: steady, the opening call's fermatas, the retransition's stop, the coda's broadening, the slow
    # introduction (set before the parts: their held notes are measured in seconds - HOLD)
    secs = {x.name: x for x in s.sections}
    for i, blk in enumerate(mat['blocks']):
        x = secs[sec_of[blk['name']]]
        if blk['kind'] == 'slow':
            s.set_tempo(x.start, max(40, round(tune.tempo * SLOW['tempo'])))
            s.ritardando((x.end - U * k, x.end), to=0.85, a_tempo=False)
            s.fermata(x.end - 1.0, hold=1.5, length=1.0)
            s.set_tempo(x.end, tune.tempo)
        # (every span given: set before the parts, a span read from the notes placed so far ran over the next one)
        stops = [x.start + 2 * U * k, x.end]
        for j, f in enumerate(blk.get('fermatas', ())):
            s.fermata(f * k + 0.25, hold=1.5 * k, length=max(0.5, stops[min(j, 1)] - f * k - 0.25))
        if blk['kind'] == 'retrans' and blk.get('gp') == 'fermata':
            s.fermata(x.end - U * k + 0.25, hold=2.0, length=U * k - 0.25)
        ev_ = blk.get('event')
        if ev_ and ev_['kind'] == 'final' and CHROMA_EVENT.get('hold'):    # (the chromatic chord held)
            s.fermata(ev_['hold'][0] * k, hold=float(CHROMA_EVENT['hold']), length=ev_['hold'][1] * k)
        if blk['kind'] == 'coda':
            s.ritardando((x.end - U * k, x.end), to=0.88, a_tempo=False)
        elif blk['kind'] == 'coda_soft':           # (the dissolving coda broadens more - it never did: q1)
            s.ritardando((x.end - 2 * U * k, x.end), to=0.75, a_tempo=False)
    end = secs[mat['blocks'][-1]['name']]
    # (round o5: an ending with its approach bar holds the last chord, the tonic, not the dominant)
    lb = mat['blocks'][-1]
    last_at = end.start + ((lb.get('approach', lb['start']) - lb['start'] + U) * k if lb.get('cadence') else 0.0)
    if lb.get('amen') is not None:             # (round o19a: the amen's IV before the last chord - END_V2)
        last_at = end.start + (lb['amen'] - lb['start'] + U) * k
    s.fermata(last_at, hold=eo.END_HOLD)
    tm = s.tempo_map()
    stm = [(e['beat'] * k, e['end'] * k) for e in mat['log'] if e['tf'] != 'cantilena']
    lp = BD.get('line_phrasing')
    if PUMPING and lp:
        lp *= PUMPING['phrasing']
    fleads = {blk['name']: [(v, a * k, z * k) for v, a, z in blk['fugue']['leads']] for blk in mat['blocks']
              if blk.get('fugue')}
    fcs = {blk['name']: ([(v, a * k, z * k) for v, a, z in blk['fugue']['cs']], [a * k for a in blk['fugue']['entries']])
           for blk in mat['blocks'] if blk.get('fugue') and blk['fugue'].get('cs') is not None}
    for part_i, p in enumerate(plan_o.parts):
        if p.role in b_.roles and p.notes:
            ph = max(sc.phrasing.get(p.role, 0.0), lp) if (p.line and lp) else None
            notes = _hold([(a, d, q) for a, d, q in p.notes], p.role, tm,
                          restrike=p.function in HOLD.get('restrike', ()) and not p.line and
                          p.block != mat['blocks'][-1]['name'])        # (the final chord dies away)
            offs = _shape_offs(p, stm, U * k, sc.level)
            if p.block in fleads and p.function in ('voice', 'bass'):
                offs = _fugue_offs(offs, fleads[p.block], 'v4' if p.function == 'bass' else p.voice,
                                   *fcs.get(p.block, ((), ())))
            elif p.block in fcs and p.function == 'counter':
                offs = _fugue_offs(offs, (), '', (), fcs[p.block][1])
            if exposed_answers.get(part_i):
                answer_beats = exposed_answers[part_i]
                lift = orc.FUNCTIONS['melody']['off'] - orc.FUNCTIONS['counter']['off']
                previous = offs
                offs = lambda n, previous=previous, beats=answer_beats, lift=lift: \
                    (previous(n) if previous else 0.0) + (lift if round(n[0], 3) in beats else 0.0)
            if part_i in accent_support:
                boosts = accent_support[part_i]
                previous = offs
                offs = lambda n, previous=previous, boosts=boosts: \
                    (previous(n) if previous else 0.0) + boosts.get(round(n[0], 3), 0.0)
            sc.add(p.role, notes, p.art, off=p.off, line=p.line, phrasing=ph, sf=p.sf, offs=offs)
    s.tempo_at = lambda beat: tm.bpm_at(s._at(beat))
    try:
        sc.perform(follow=True)
        if ch is not None:
            CH.sing(s, b_, sc, ch, gain=BD.get('gain', 0.0))
        if cl is not None:
            CO.play(s, b_, marks, tune, cl, gain=BD.get('gain', 0.0), style=BD.get('style', 'romantic'))
    finally:
        del s.tempo_at
    orch.ring(b_, last_at, length=2.0, db=3.0)
    # (round o9 - o8's gate: 3 rejects of flat_dynamics on parts the analysis guessed as leads by their names - a tuba
    # doubling, a violins II ostinato, the trumpets' climax harmony: the melody's tracks per block, LEAD_HINT)
    if LEAD_HINT:
        hint = {}
        for p in plan_o.parts:
            if p.function in LEAD_HINT and p.notes and p.role in b_.roles:
                hint.setdefault(b_[p.role].id, set()).add(sec_of.get(p.block, p.block))
        s.lead_hint = {t: sorted(v) for t, v in hint.items()}
    s.endless_tune = tune
    s.endless_sections = [(x.name, x.start, x.end) for x in s.sections]
    s.endless_timeline = [(a, bb, sym) for x in score.blocks for a, bb, sym in x.chart]
    s.endless_arrangement = dice.out
    s.orch_score = score
    s.orchestration = plan_o
    s.orch_size = size
    s.symphony_log = [dict(e, beat=e['beat'] * k, end=e['end'] * k,
                           fn='bass' if e['block'] in in_bass and e['fn'] == 'melody' else e['fn'])
                      for e in mat['log']]
    HS.play(s, tune, sax_events)
    # Listening-approved mix, 2026-10-28: matched Wings of the Sea A/B, pass 2.
    # Apply after all orchestral and colour tracks exist; retain notes and master.
    for role, trim in (('bells', -2.0), ('horns', -1.5)):
        if role in s.tracks:
            s.tracks[role].gain_db += trim
    if 'violins1' in s.tracks:
        from ..song import FX
        s.tracks['violins1'].fx.append(FX('eq', {
            'peak3.freq': 3500, 'peak3.gain': -1.5, 'peak3.q': 0.9}))
    return s


# ------------------------------------------------------------------------------------------------ the score

def motto_stats(song) -> dict:
    """The motto's life (from the composer's log and the orchestration): statements, distinct transforms, the
    roles that carried it, statements in the bass, the blocks that state it, its share of the blocks."""
    log = getattr(song, 'symphony_log', None) or []
    plan = getattr(song, 'orchestration', None)
    mot = [e for e in log if e['tf'] != 'cantilena']
    roles = set()
    if plan is not None:
        for e in mot:
            for p in plan.parts:
                if p.block == e['block'] and p.function in (e['fn'], 'doubling') and p.notes and \
                        any(e['beat'] - _EPS <= a < e['end'] - _EPS for a, _, _ in p.notes) and \
                        (p.function != 'doubling' or p.voice in ('melody', e['fn'])):
                    roles.add(p.role)
    blocks = {e['block'] for e in mot}
    nblocks = len({x.name for x in song.sections})
    return {'motto': len(mot), 'motto_tf': len({e['tf'] for e in mot}), 'motto_roles': len(roles),
            'motto_bass': sum(1 for e in mot if e['fn'] == 'bass'), 'motto_blocks': round(len(blocks) / max(1, nblocks), 3)}


FORM_STATS = {'dev': ('dev_dialogue', 'dev_fugato'), 'theme1': ('recap', 'refrain', 'river', 'var'),
              'expo': ('t1', 't1b', 't2', 't2b', 'river'), 'back': ('recap', 'recap2', 'coda', 'river')}
"""Round o11 (the masterpiece panel: the internal score rated ASFP 99.8 - the panel heard one of the weakest; "form's
argument"): the block kinds form_stats reads - the development, the first theme's returns, the exposition's and the
return's theme blocks (DEV_SHARE / RETURN)."""


def _seq_links(line, unit: float, t0: float, t1: float) -> int:
    """The longest chain of `unit`-beat units in [t0, t1) each the unit before transposed unchanged (the same onsets,
    the same interval directions, each interval within a semitone - a block sequence's links)."""
    units = _seq_units(line, unit, t0, t1)
    best = run = 0
    for u, v in zip(units, units[1:]):
        run = run + 1 if _seq_same(u, v) else 0
        best = max(best, run)
    return best


def _seq_units(line, unit: float, t0: float, t1: float) -> list:
    units, a = [], t0
    while a < t1 - _EPS:
        units.append(sorted((round(x - a, 2), q) for x, _, q in line if a - _EPS <= x < a + unit - _EPS))
        a += unit
    return units


def _seq_same(u, v) -> bool:
    """Unit v is unit u transposed unchanged (_seq_links)."""
    if len(u) < 2 or len(u) != len(v) or [x for x, _ in u] != [x for x, _ in v] or u[0][1] == v[0][1]:
        return False
    iu = [b[1] - a_[1] for a_, b in zip(u, u[1:])]
    iv = [b[1] - a_[1] for a_, b in zip(v, v[1:])]
    return all((x > 0) == (y > 0) and (x < 0) == (y < 0) and abs(x - y) <= 1 for x, y in zip(iu, iv))


SEQ_BREAK = 2
"""Round o15b (o14: 3 of 16 pieces capped by seq_links under best-of-1 - a fugato's counter-subject a semitone up and
down for 22 bars, 9 links; a dialogue ladder's call 4 links): a development line whose 1- / 2-bar units run more than
SEQ_BREAK links transposed unchanged (the seq_links gate) has the unit that would make the next link changed - its last
note tied into the note before (the rhythm changes, the harmony stays); None: off (_break_links)."""


def _break_links(line, U: float, t0: float, t1: float) -> list:
    """SEQ_BREAK on one line (sorted notes): unchanged where no chain runs longer."""
    if not SEQ_BREAK or not line:
        return line
    ln = sorted(line)
    for _ in range(64):
        hit = None
        for unit in (U, 2 * U):
            units = _seq_units(ln, unit, t0, t1)
            run = 0
            for k in range(1, len(units)):
                run = run + 1 if _seq_same(units[k - 1], units[k]) else 0
                if run > SEQ_BREAK:
                    hit = (t0 + k * unit, unit)
                    break
            if hit:
                break
        if not hit:
            return ln if ln != sorted(line) else line
        a, unit = hit
        idx = [i for i, n in enumerate(ln) if a - _EPS <= n[0] < a + unit - _EPS]
        i = idx[-1]
        prev = ln[i - 1]
        ln = ln[:i - 1] + [(prev[0], ln[i][0] + ln[i][1] - prev[0], prev[2])] + ln[i + 1:]
    return ln


def form_stats(song) -> dict:
    """The form's argument (round o11; songs/_blind/tells_orch.py measure_o11 reads the same): dev_share (the
    development blocks' bars over the piece's), seq_links (the longest chain of 1- / 2-bar units of its lines
    transposed unchanged), t1_home (the first theme in the home tonic at or after the peak), t2_home (the second theme
    back in the home tonic - absent without one), recap_weight (the return's theme blocks over the exposition's),
    cadence_end (the last chart V - I), peak_pos (the peak block's centre), top_peak (the first highest pitched note in
    the peak block), pre_semis (the peak's highest note over the highest before it), seconds."""
    tune = getattr(song, 'endless_tune', None)
    mat = getattr(tune, 'symphony', None)
    score = getattr(song, 'orch_score', None)
    plan = getattr(song, 'orchestration', None)
    if not mat or score is None or plan is None:
        return {}
    F_ = FORM_STATS
    blocks = mat['blocks']
    U = mat['U']
    out = {'seconds': round(song.seconds(song.length), 1)}
    total = sum(b['bars'] for b in blocks)
    dev = [b for b in blocks if b['kind'] in F_['dev']]
    out['dev_share'] = round(sum(b['bars'] for b in dev) / max(1, total), 3)
    links = 0
    for b in dev:
        t0, t1 = b['start'], b['start'] + b['bars'] * U
        for ln in [b['theme'], b['answer']] + list(b['voices'].values()):
            if ln:
                links = max(links, _seq_links(ln, U, t0, t1), _seq_links(ln, 2 * U, t0, t1))
    out['seq_links'] = links
    ht = Key(tune.key).tonic
    pb = next((i for i, b in enumerate(blocks) if b.get('peak')), None)
    apx = (tune.arrange or {}).get('apex')
    if pb is not None:
        out['t1_home'] = int(any(Key(b['key']).tonic == ht and b['theme'] and (
            b['kind'] in F_['theme1'] or (b['kind'] == 'recap2' and apx in ('combine', 'second'))) for b in blocks[pb:]))
    first = next((i for i, b in enumerate(blocks) if b['kind'] in F_['dev'] or b['kind'] == 'var'), len(blocks))
    if any(b['kind'] == 't2' for b in blocks[:first]):
        out['t2_home'] = int(any(b['kind'] == 'recap2' and Key(b['key']).tonic == ht for b in blocks[first:]))
    expo = sum(b['bars'] for b in blocks[:first] if b['kind'] in F_['expo'])
    back = sum(b['bars'] for b in blocks[first:] if b['kind'] in F_['back'])
    if expo:
        out['recap_weight'] = round(back / expo, 3)
    ch = [sy for b in blocks[-2:] for _, d, sy in sorted(b['chart']) if d > _EPS]
    if len(ch) >= 2:
        lk = Key(blocks[-1]['key'])
        r1, r2 = chord(ch[-2].split('/')[0]).root % 12, chord(ch[-1].split('/')[0]).root % 12
        out['cadence_end'] = int(r2 == lk.tonic % 12 and r1 in ((lk.tonic + 7) % 12, (lk.tonic + 11) % 12))
        if SET_PLAN and SET_PLAN.get('endings') and not out['cadence_end'] and len(ch) >= 3 and \
                r2 == lk.tonic % 12 and r1 == (lk.tonic + 5) % 12 and \
                chord(ch[-3].split('/')[0]).root % 12 == (lk.tonic + 7) % 12:
            out['cadence_end'] = 1            # (round o18b: the amen - V7, then IV6/4 - I over the tonic)
        if SET_PLAN and SET_PLAN.get('v2') and not out['cadence_end'] and len(ch) >= 4 and \
                r2 == lk.tonic % 12 and r1 == (lk.tonic + 5) % 12 and \
                chord(ch[-3].split('/')[0]).root % 12 == lk.tonic % 12 and \
                chord(ch[-4].split('/')[0]).root % 12 == (lk.tonic + 7) % 12:
            out['cadence_end'] = 1            # (round o19a: V7 - I, then the amen IV - I - END_V2)
    peak = next((x for x in score.blocks if x.peak), None)
    if peak is not None:
        out['peak_pos'] = round((peak.start + peak.end) / 2 / max(_EPS, song.length), 3)
        pit = [p for p in plan.parts if p.notes and p.role not in ('percussion', 'timpani', 'harp')]
        allq = [(q, a) for p in pit for a, _, q in p.notes]
        if allq:
            top = max(q for q, _ in allq)
            t_top = min(a for q, a in allq if q == top)
            out['top_peak'] = int(peak.start - _EPS <= t_top < peak.end)
            names = [x.name for x in score.blocks]
            before = set(names[:names.index(peak.name)])
            ptop = max((q for p in pit if p.block == peak.name for _, _, q in p.notes), default=0)
            btop = max((q for p in pit if p.block in before for _, _, q in p.notes), default=None)
            if btop is not None:
                out['pre_semis'] = ptop - btop
    return out


OWN = {'win': 4, 'kinds': ('dev_dialogue', 'dev_fugato', 'episode', 'var'),
       'motto': ('intro', 'mist', 'solo', 'slow', 'source', 't1', 't1b', 'river')}
"""Round o12 (o11's judges, about 18 of 56: "the development is a row of textures, not an argument with the motto";
dev_own 0.80 -> 0.67): own_stats' material windows - 'win' notes of a role's top line (their onset ratios, whether the
last is held, their intervals) - and the kinds it reads: the development's / episodes' / variations' bars against the
motto's cell and the exposition's lines ('motto' the blocks that state the motto; songs/_blind/tells_orch.py dev_own
measures the same)."""


def _top_line(notes) -> list:
    by = {}
    for a, d, q in notes:
        k_ = round(a, 3)
        if k_ not in by or q > by[k_][2]:
            by[k_] = (a, d, q)
    return [by[k_] for k_ in sorted(by)]


def _windows(line) -> list:
    out = []
    W = OWN['win']
    for i in range(len(line) - W + 1):
        w = line[i:i + W]
        io = [b[0] - a[0] for a, b in zip(w, w[1:])]
        long_ = int(w[-1][1] >= 1.5 * max(io))
        if min(io) <= _EPS or max(io) > 6.0 or (max(io) - min(io) < 1e-3 and not long_):
            continue
        iv = tuple(b[2] - a[2] for a, b in zip(w, w[1:]))
        if not any(iv) or max(abs(x) for x in iv) > 12:
            continue
        out.append((w[0][0], tuple(round(x / io[0], 2) for x in io[1:]) + (long_,), iv))
    return out


def _wmatch(w, mats) -> bool:
    _, r, iv = w
    for _, r2, iv2 in mats:
        if r[-1] == r2[-1] and all(abs(a - b) <= 0.06 * max(1.0, b) for a, b in zip(r[:-1], r2[:-1])):
            for sg in (1, -1):
                if all(abs(a - sg * b) <= 1 and ((a > 0) - (a < 0)) == sg * ((b > 0) - (b < 0))
                       for a, b in zip(iv, iv2)):
                    return True
    return False


def own_stats(song) -> dict:
    """dev_own (OWN): the share of the development's (episodes', variations') song bars whose melodic lines (melody,
    counter, voice, bass - the roles' top lines, no doubling) hold a window of the piece's own material."""
    tune = getattr(song, 'endless_tune', None)
    mat = getattr(tune, 'symphony', None)
    score = getattr(song, 'orch_score', None)
    plan = getattr(song, 'orchestration', None)
    if not mat or score is None or plan is None:
        return {}
    blocks = mat['blocks']
    bpb = song.beats_per_bar
    parts = [p for p in plan.parts if p.notes and p.role not in ('percussion', 'timpani', 'harp') and
             p.function != 'doubling']

    def lines(names, fns):
        out = {}
        for p in parts:
            if p.block in names and p.function in fns:
                out.setdefault(p.role, []).extend(p.notes)
        return [_top_line(ns) for ns in out.values()]
    first = next((i for i, b in enumerate(blocks) if b['kind'].startswith('dev') or b['kind'] == 'var'), len(blocks))
    expo = {b['name'] for b in blocks[:first]}
    mot = {b['name'] for b in blocks[:first] if b['kind'] in OWN['motto']}
    mats = [w for tf in ((), ('invert',), ('augment',)) for w in
            _windows(sorted(motto_notes(mat['motto'], 0.0, 72, {0, 2, 4, 5, 7, 9, 11}, tf)))]
    mats += [w for ln in lines(mot, ('melody', 'bass', 'voice')) for w in _windows(ln)]
    mats += [w for ln in lines(expo, ('melody', 'bass', 'voice', 'counter')) for w in _windows(ln)]
    sb = {x.name: x for x in score.blocks}
    rondo = mat['layout'] == 'rondo'
    hit = tot = 0
    for b in blocks:
        if not (b['kind'] in OWN['kinds'] or (rondo and b['kind'] == 'trio')) or b['name'] not in sb:
            continue
        x = sb[b['name']]
        nb = int(round(x.length / bpb))
        bars = {i: False for i in range(nb)}
        for ln in lines({b['name']}, ('melody', 'counter', 'voice', 'bass')):
            for w in _windows(ln):
                i = int((w[0] - x.start + _EPS) // bpb)
                if i in bars and not bars[i] and _wmatch(w, mats):
                    bars[i] = True
        hit += sum(bars.values())
        tot += nb
    return {'dev_own': round(hit / tot, 3)} if tot else {}


def derive_stats(song) -> dict:
    """DEV_WALK 'graph' (round o16 - the code review's A1: the derivation is known by construction, so dev_own's window
    matching gives way to the graph): over the development's (dev_dialogue's) logged statements - dev_ops the distinct
    transform ops, dev_depth the rise of the chains' depth (the last third's mean over the first's), dev_literal the
    whole motto restated unchanged. {} with DEV_WALK off (the score unchanged)."""
    if not (DEV_WALK and DEV_WALK.get('graph')):
        return {}
    tune = getattr(song, 'endless_tune', None)
    mat = getattr(tune, 'symphony', None)
    if not mat:
        return {}
    dev = {b['name'] for b in mat['blocks'] if b['kind'] == 'dev_dialogue'}
    log = [e for e in mat['log'] if e['block'] in dev and 'node' in e]
    if not log:
        return {}
    ops = {o for e in log for o in e['ops'] if o != 'recall'}
    t0, t1 = min(e['beat'] for e in log), max(e['end'] for e in log)
    th = (t1 - t0) / 3.0
    first = [e['depth'] for e in log if e['beat'] < t0 + th]
    last = [e['depth'] for e in log if e['beat'] >= t1 - th]
    rise = (sum(last) / len(last) - sum(first) / len(first)) if first and last else 0.0
    return {'dev_ops': len(ops), 'dev_depth': round(rise, 2), 'dev_literal': sum(1 for e in log if not e['ops'])}


TUTTI_SKIP = ('harp', 'percussion')
"""The roles tutti_peak does not count (round o15b): SUMMIT's 'fill' never adds them to the peak."""


def summit_stats(song) -> dict:
    """The summit (SUMMIT) and the accompaniment's runs (TEX_RUN): tutti_peak 1 when no block sounds more roles than
    the peak, vln_over the peak's violins I top over every line before it (semitones), brass_peak the trumpets and
    the trombones on a line in the peak (0-2; an orchestra without them: 2 for the horns), acc_run the longest unchanged accompaniment run (song bars)."""
    tune = getattr(song, 'endless_tune', None)
    mat = getattr(tune, 'symphony', None)
    score = getattr(song, 'orch_score', None)
    plan = getattr(song, 'orchestration', None)
    if not mat or score is None or plan is None:
        return {}
    out = {}
    parts = [p for p in plan.parts if p.notes]
    kinds = {b['name']: b['kind'] for b in mat['blocks']}
    runs = acc_runs(plan, score, kinds, song.beats_per_bar)
    out['acc_run'] = max((n for _, n in runs), default=0)
    peak = next((x for x in score.blocks if x.peak), None)
    if peak is None:
        return out
    roles = {}
    for p in parts:                 # (round o15b: the roles SUMMIT's fill can add - the harp and the percussion are
        if p.role not in TUTTI_SKIP:    # colour, never in it: o14's 15 a harp variation over the peak's 11 roles)
            roles.setdefault(p.block, set()).add(p.role)
    out['tutti_peak'] = int(len(roles.get(peak.name, ())) >= max((len(v) for v in roles.values()), default=0))
    names = [x.name for x in score.blocks]
    before = set(names[:names.index(peak.name)])
    lf = ('melody', 'counter', 'voice', 'doubling')
    pre = max((q for p in parts if p.block in before and p.function in lf and
               p.role not in ('percussion', 'timpani', 'harp') for _, _, q in p.notes), default=None)
    vt = max((q for p in parts if p.block == peak.name and p.role == 'violins1' for _, _, q in p.notes), default=None)
    if pre is not None and vt is not None:
        out['vln_over'] = vt - pre
    on = lambda r: any(p.block == peak.name and p.role == r and p.function in lf for p in parts)  # noqa: E731
    out['brass_peak'] = sum(1 for r in ('trumpets', 'trombones') if on(r)) if any(
        p.role in ('trumpets', 'trombones') for p in parts) else 2 * int(on('horns'))
    return out


def activity(song) -> dict:
    """Notes per second (all parts' attacks / the piece's seconds) and the share of seconds with a running line
    (an attack every 0.3 s or faster in some part)."""
    scs = getattr(song, 'orch_scores', None) or []
    on = sorted({round(n[0], 3) for sc in scs for ns in sc.parts.values() for n in ns})
    if not on:
        return {}
    secs = song.seconds(song.length)
    ts = [song.seconds(x) for x in on]
    return {'nps': round(len(on) / max(1.0, secs), 2),
            'run_share': round(sum(1 for a, b_ in zip(ts, ts[1:]) if b_ - a <= 0.3) / max(1, len(ts) - 1), 3)}


def symphony_metrics(song, tune=None) -> dict:
    """The symphonic score's metrics: the orchestration (orchestration.metrics), the motto's life (motto_stats),
    the activity (notes / s) and the theme lines' clashes (composer.melody_issues per block, per 100 notes)."""
    from .composer import Harm, melody_issues
    scs = getattr(song, 'orch_scores', None) or []
    if not scs:
        raise ComposeError("symphony score: the song has no orch.Score")
    out = dict(orc.metrics(eo._merge(scs)))
    out.update(motto_stats(song))
    out.update(activity(song))
    out.update(form_stats(song))                   # (round o11: the form's argument)
    out.update(own_stats(song))                    # (round o12: the development's own material, the summit)
    out.update(derive_stats(song))                 # (round o16: the derivation graph - DEV_WALK only)
    out.update(summit_stats(song))
    score = getattr(song, 'orch_score', None)
    issues = n = 0
    if score is not None:
        for b in score.blocks:
            for x in b.get('melody'):
                rel = [(a - b.start, d, p) for a, d, p in x.notes]
                ch = [(sy, bb) for _, bb, sy in b.chart]
                if not ch or not rel:
                    continue
                harm = Harm(ch, Key(b.key).pcs)
                issues += sum(1 for i in melody_issues(rel, harm, 0, 127, meter=score.meter)
                              if i.startswith(('clash', 'leap')))
                n += len(rel)
    out['clash'] = round(100.0 * issues / max(1, n), 2)
    return {k_: v for k_, v in out.items() if v is not None}
