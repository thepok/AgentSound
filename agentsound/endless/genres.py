"""Endless genres: each one a DATA spec - the composer and the players are shared (agentsound.endless).

A genre says what to roll (forms, moods -> feels / modes / keys / tempo, chord colours), how the tune is played
(the feel's pianist style and left hand, the band preset and which of its roles play) and the arrangement plan
(intro / head / solo / head out / tag / end with their dynamics). Adding a genre = a new Genre(...) in GENRES (and,
when it needs a player the plan cannot express, a hook in agentsound/endless/perform.py).

    from agentsound.endless import genres
    genres.get('jazz-piano').validate()
    genres.GENRES['my-trio'] = genres.get('jazz-piano').but(name='my-trio', band={...})
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field, fields, replace

from ..humanize import BODIES
from ..romantic import LEVELS as _LEVELS
from ..theory import ComposeError, chord

# ------------------------------------------------------------------------------------------------ harmony blocks
# Progression building blocks in roman numerals RELATIVE TO THE KEY'S TONIC (upper-case numerals, b / # = from the
# major scale), one token per chord, ':n' = bars (default 1). The quality after the numeral is either written out
# ('m6', '7#11', 'maj7#11') or ABSTRACT and coloured by the composer from COLOURS (seeded, by mood):
#   M = major 7th family, m = minor 7th family, 7 = dominant (coloured by where it resolves), o = dim7, ø = m7b5,
#   sus = 7sus4 family. Blocks are 4 bars (openers / closers) or 8 bars (bridges / contrasts); 12 for the blues.
BLOCKS = {
    'major': {
        'open': {
            'I_vi_ii_V': 'IM VIm IIm V7',
            'I_VI7_ii_V': 'IM VI7 IIm V7',
            'iii_VI_ii_V': 'IIIm VI7 IIm V7',
            'I_I7_IV_iv': 'IM I7 IVM IVm6',
            'ii_V_I': 'IIm V7 IM:2',
            'vi_IV_ii_V': 'VIm IVM IIm V7',
            'I_IV_held': 'IM:2 IVM:2',
            'I_bVII': 'IM bVII7 IM IVM',
        },
        'turn': {             # ends on the dominant (back to the top)
            'ii_V_turn': 'IIm V7 IIIm:0.5 VI7:0.5 IIm:0.5 V7:0.5',
            'iii_VI_turn': 'IIIm VI7 IIm:0.5 V7:0.5 IM:0.5 V7:0.5',
            'IV_iv_turn': 'IVM IVm6 IIIm:0.5 VI7:0.5 IIm:0.5 V7:0.5',
            'ii_V_I_VI': 'IIm V7 IM VI7',
        },
        'final': {            # ends on the tonic
            'ii_V_I': 'IIm V7 IM:2',
            'tritone': 'IIm bII7 IM:2',
            'backdoor': 'IVm6 bVII7 IM:2',
            'iii_VI_ii_V_I': 'IIIm VI7 IIm:0.5 V7:0.5 IM',
            'IV_iv_I': 'IVM IVm6 IIm:0.5 V7:0.5 IM',
        },
        'to_bridge': {        # A2 of an AABA: home, then a ii-V into IV
            'home_iiV_IV': 'IIm V7 IM Vm:0.5 I7:0.5',
            'home_I7': 'IIm V7 IM:0.5 VIm:0.5 Vm:0.5 I7:0.5',
        },
        'bridge': {
            'IV': 'IVM IVM IVm6 bVII7 IIIm VI7 IIm V7',
            'III7_cycle': 'VIIø III7 VIm VIm II7 II7 IIm V7',
            'relative': 'VIIø III7 VIm VIm IVM IVm6 IIm V7',
            'IV_cycle': 'IVM IVM IIIm VI7 IIm V7 IIIm:0.5 VI7:0.5 IIm:0.5 V7:0.5',
            'bIII': 'IVm bVII7 bIIIM bIIIM IIm V7 IIm V7',
        },
        'contrast': {         # the B of an ABAC
            'II7': 'II7:2 IIm V7 IIIm VI7 IIm V7',
            'III7': 'III7:2 VIm:2 II7:2 IIm V7',
            'IV_rise': 'IVM #IVo IIIm VI7 IIm V7 IM V7',
        },
        'climb': {            # the first half of an ABAC's C
            'IV_iv': 'IVM IVm6 IIIm VI7',
            'ii_iii': 'IIm V7 IIIm VI7',
            'IV_#iv': 'IVM #IVø IIIm VI7',
        },
        'blues': {
            'jazz_blues': 'I7 IV7 I7 Vm:0.5 I7:0.5 IV7 #IVo I7 VI7 IIm V7 I7:0.5 VI7:0.5 IIm:0.5 V7:0.5',
            'basic_blues': 'I7 IV7 I7 I7 IV7 IV7 I7 VI7 IIm V7 I7 V7',
            'bird_blues': 'IM VIIø:0.5 III7:0.5 VIm:0.5 II7:0.5 Vm:0.5 I7:0.5 IV7 IVm:0.5 bVII7:0.5 IIIm VI7 '
                          'IIm V7 IM:0.5 VI7:0.5 IIm:0.5 V7:0.5',
        },
    },
    'minor': {
        'open': {
            'i_iv': 'Im:2 IVm:2',
            'i_bVI_ii_V': 'Im bVIM IIø V7',
            'i_iv_bVII_bIII': 'Im IVm bVII7 bIIIM',
            'i_ii_V': 'Im:2 IIø V7',
            'i_line': 'Im9 ImMaj7 Im7 Im6',
        },
        'turn': {
            'bVI_V_turn': 'bVIM V7 Im IIø:0.5 V7:0.5',
            'ii_V_turn': 'IIø V7 Im bVI7:0.5 V7:0.5',
            'iv_bVII_turn': 'IVm bVII7 bIIIM:0.5 bVIM:0.5 IIø:0.5 V7:0.5',
        },
        'final': {
            'ii_V_i': 'IIø V7 Im:2',
            'bVI_V_i': 'bVIM V7 Im:2',
            'tritone': 'IIø bII7 Im:2',
        },
        'to_bridge': {
            'home_to_iv': 'IIø V7 Im Vø:0.5 I7:0.5',
        },
        'bridge': {
            'relative': 'IVm bVII7 bIIIM bIIIM bVIM bVIM IIø V7',
            'iv': 'IVm IVm bVII7 bIIIM bVIM IIø V7 V7',
            'bII': 'bVIM bVIM bIIM bIIM IIø V7 Im V7',
        },
        'contrast': {
            'relative': 'IVm bVII7 bIIIM bVIM IIø V7 Im V7',
            'iv_cycle': 'IVm:2 bVII7:2 bIIIM bVIM IIø V7',
        },
        'climb': {
            'iv_bVII': 'IVm bVII7 bIIIM bVIM',
            'bVI_ii': 'bVIM IIø Im IVm',
        },
        'blues': {
            'minor_blues': 'Im IVm Im Im IVm IVm Im Im bVI7 V7 Im IIø:0.5 V7:0.5',
            'minor_blues_ii': 'Im IVm Im Vø:0.5 I7:0.5 IVm IVm Im bIIIM:0.5 bVI7:0.5 IIø V7 Im IIø:0.5 V7:0.5',
        },
    },
}

INTROS = {
    # the intro is its OWN material: a 4-bar vamp (a waltz doubles it) with the hook over it (an octave up; the riff:
    # the hook alone an octave low, no left hand, over the head's first three bars + a ii-V); the tag reprises the
    # intro with a twist (its last chord the tritone sub bII7#11 into the end chord). name -> (block, weight); 'head:3'
    # = the A1's first three bars. 'tonic': only when the A1 opens on the tonic (the vamp is a tonic colour / pedal).
    # The weights are a distribution: no vamp dominates (blind round 3: the IV-iv-ii-V in every sample tune).
    'major': {'bVI_V': ('bVImaj7#11 V7b9 bVImaj7#11 V7b9', 1.0), 'IV_iv_ii_V': ('IVmaj9 IVm6 IIm9 V13', 0.6),
              'I_bII': ('Imaj9 bIImaj7#11 Imaj9 bIImaj7#11', 0.7), 'pedal': ('V9sus4 V7b9 V9sus4 V13', 0.7),
              'iii_VI_ii_V': ('IIIm9 VI7b9 IIm9 V13', 0.8), 'ii_V': ('IIm9 V13 IIm9 V7#11', 0.6),
              'riff': ('head:3 IIm7:0.5 V7:0.5', 0.6)},
    'minor': {'bVI_V': ('bVImaj7#11 V7b9 bVImaj7#11 V7b9', 1.0), 'iv_ii_V': ('IVm9 IVm6 IIm7b5 V7b9', 0.6),
              'i_bII': ('Im9 bIImaj7#11 Im9 bIImaj7#11', 0.7), 'pedal': ('V7sus4 V7b9 V7sus4 V7alt', 0.7),
              'i_bVI': ('Im9 bVImaj7 IIm7b5 V7alt', 0.8), 'riff': ('head:3 IIm7b5:0.5 V7b9:0.5', 0.7)},
}
INTRO_TONIC = ('I_bII', 'i_bII', 'pedal')            # vamps that want the head to open on the tonic
INTRO_LINES = {'augment': 0.35, 'fragment': 0.4, 'answer': 0.25}
TAG_LINES = {'augment': 0.45, 'fragment': 0.35, 'answer': 0.2}
"""What the right hand plays over the intro's / the tag's vamp (composer.frame), drawn per tune - a FRAGMENT of the
hook developed, never head bars copied onto new chords (blind round 5): 'augment' the hook's first bar twice as slow,
then again a step higher and landed; 'fragment' its first notes as a cell, sequenced up bar by bar, then landed;
'answer' the hook's rhythm with its contour turned, then its fragment augmented into the landing (blind round 6: the
voicings alone - one held top note over four changing chords - read as a pad; the motif is stated). The riff vamp
plays the hook itself, an octave low. Every line is re-fitted to the vamp's chords."""
ENDINGS = {'major': {'69': 0.5, 'maj9': 0.8, 'maj7#11': 0.5, 'maj13': 0.5, '6': 0.3, 'maj9#11': 0.3},
           'minor': {'mMaj9': 0.8, 'm69': 0.5, 'm9': 0.8, 'm11': 0.5}}
"""The end chord's quality (the tag's twist lands on it), drawn per tune (blind round 7: 6/9 endings everywhere)."""
TAG_FRAMES = {'reprise': 0.5, 'vamp': 0.25, 'turnaround': 0.25}
"""What the tag plays (composer.frame, drawn per tune - blind round 7: the tag the intro's reprise in every tune):
'reprise' the intro's vamp again, 'vamp' another vamp of INTROS, 'turnaround' the A's last four bars again (the
classic tag) - each with its drawn approach into the end chord."""
OUT_PARTS = {'AABA': {('B', 'A3'): 0.55, ('A1', 'A2', 'B', 'A3'): 0.3, ('A3',): 0.15},
             'ABAC': {('A2', 'C'): 0.55, ('A1', 'B', 'A2', 'C'): 0.45},
             'blues': {('A1', 'A2'): 0.6, ('A2',): 0.4}}
"""The head out's parts per form (a jazz plan's, drawn per tune; FORMS 'out' is the default) - blind round 7: the
head out always the head's second half: the whole head again, from the bridge, the last A alone (a blues: two choruses
or one)."""
TAG_APPROACH = {'tritone': 0.3, 'backdoor': 0.2, 'plagal': 0.2, 'deceptive': 0.15, 'cold': 0.15}
"""How the tag's last half bar leads into the end chord (composer.frame, drawn - blind round 4: a bII7#11 in 7 of 8
tags): tritone (bII7#11), backdoor (bVII9), plagal (IVm6), deceptive (V7 to bVImaj7, then home), cold (V7alt struck
short: a cold stop, the end chord after the silence)."""
END_STYLES = {'roll': 0.35, 'spread': 0.2, 'plink': 0.15, 'cadenza': 0.15, 'fade': 0.15}
"""The final chord (perform, drawn per tune - blind round 4: the same rolled chord everywhere): roll (the left hand
rolled up, the right hand after it), spread (a slow, wide roll, the 9th an octave higher), plink (a quick roll, then a
Basie plink: two soft high notes), cadenza (a short run down over the chord into its top note), fade (soft, the hook's
head echoed an octave up, dying away)."""
CHART_VARIANTS = {'tritone': 1.0, 'backdoor': 0.7, 'pedal': 0.5, 'plagal': 0.6, 'iiV': 0.5}
"""How a cadence is played another way (composer.variant): a blues head's second chorus (its second ending, drawn)
and the solo choruses / head out's reharm draw from these - a distribution, not the tritone sub every time."""

COLOURS = {
    # abstract quality -> {written quality: weight}; 'lush' moods colour richer (the mood's 'colour' scales the
    # tension weights). Every written quality is checked against the chord parser (Genre.validate).
    'M': {'maj7': 1.0, 'maj9': 2.0, '6': 0.6, '69': 1.0, 'maj7#11': 0.4},
    'M_tonic': {'maj9': 2.0, '69': 1.5, 'maj7': 1.0, '6': 0.6},
    'm': {'m7': 1.0, 'm9': 2.0, 'm11': 0.6},
    'm_tonic': {'m9': 2.0, 'm6': 1.0, 'm7': 0.6},
    '7_major': {'13': 2.0, '9': 1.2, '7': 0.5, '7#11': 0.4, '7sus4': 0.4},   # resolving to a major chord
    '7_minor': {'7b9': 2.0, '7b13': 1.0, '7alt': 1.2},                        # resolving to a minor chord
    '7_blues': {'13': 2.0, '9': 1.5, '7': 0.8},                               # a blues I7 / IV7 that stays put
    '7_sub': {'7#11': 2.0, '9': 1.0, '13': 0.6},                              # a tritone substitute
    'ø': {'m7b5': 1.0},
    'o': {'dim7': 1.0},
    'sus': {'7sus4': 1.0, '9sus4': 1.0},
}

# ------------------------------------------------------------------------------------------------ melody rhythm
# Rhythm cells for the tune composer: one cell = two bars, in 8ths (a negative number = a rest). 'motif' cells open
# phrases, 'line' cells continue and climb, 'land' cells end a phrase on a long note on the second bar's downbeat
# (or anticipated on the & of 4) and leave a breath. Per cell family (the feel picks one).
CELLS = {
    # two-bar cells in 8ths (a waltz: two 3/4 bars): the motif and line cells keep moving through their second bar
    # (2+ attacks there - a line, not a one-bar cell and a held note); the land cells breathe at a phrase's end
    # (no run of four on-beat quarters: a melody is not a chord-tone block per beat)
    'medium': {
        'motif': {'lift': (-2, 1, 1, 3, 1, 2, 2, 2, -2), 'sigh': (-1, 1, 1, 1, 4, 1, 1, 2, 2, -2),
                  'call': (3, 1, 2, 2, 3, 1, 2, -2), 'charleston': (3, 3, 2, 3, 3, -2),
                  'push': (-2, 2, 1, 2, 1, 2, 2, 2, -2), 'hook': (-1, 1, 2, 1, 3, 4, 2, -2)},
        'line': {'run': (1, 1, 1, 1, 2, 2, 1, 1, 2, 2, -2), 'answer': (2, 1, 1, 2, 2, -1, 1, 2, 1, 3),
                 'steps': (-2, 1, 1, 1, 1, 2, 2, 2, 1, 1, -2), 'climb': (-1, 1, 1, 1, 2, 2, 2, 4, -2)},
        'land': {'land': (2, 2, 4, 6, -2), 'land_pickup': (-2, 1, 1, 2, 2, 6, -2), 'land_dotted': (3, 1, 3, 1, 4, -4),
                 'anticipate': (-2, 2, 2, 1, 7, -2)},
    },
    'ballad': {
        'motif': {'held': (-2, 2, 4, 3, 1, 2, -2), 'breath': (2, 2, 3, 1, 4, 2, -2), 'lean': (3, 1, 4, 2, 4, -2),
                  'wait': (-4, 2, 2, 4, 2, -2), 'sing': (-2, 1, 1, 4, 2, 2, 4)},
        'line': {'answer': (2, 1, 1, 2, 2, 4, 2, -2), 'steps': (-2, 2, 1, 1, 2, 2, 1, 3, -2),
                 'rise': (-1, 1, 2, 2, 2, 1, 1, 4, -2)},
        'land': {'land': (2, 2, 4, 6, -2), 'land_pickup': (-2, 1, 1, 2, 2, 6, -2), 'long': (4, 4, 6, -2)},
    },
    'waltz': {
        'motif': {'lift': (-2, 1, 1, 2, 2, 2, -2), 'steps': (3, 1, 2, 2, 2, -2), 'sigh': (4, 2, 3, 1, -2),
                  'turn': (-2, 2, 2, 4, 2)},
        'line': {'run': (1, 1, 1, 1, 2, 2, 2, -2), 'answer': (2, 2, 2, 4, 2), 'climb': (-1, 1, 2, 2, 3, 1, -2)},
        'land': {'land': (4, 2, 5, -1), 'land_pickup': (-2, 2, 2, 5, -1), 'long': (2, 2, 2, 5, -1)},
    },
    # the singable song family (new-age / pop piano, letters-to-the-morning): a pickup into a dotted quarter, three
    # 8ths rising into a held note, sighs; few notes, long ones, and every landing breathes
    'song': {
        'motif': {'pickup': (-2, 1, 1, 3, 1, 2, 1, 1, 4), 'rise3': (-1, 1, 1, 1, 4, 1, 1, 1, 1, 4),
                  'lean': (-2, 2, 3, 1, 2, 2, 4), 'sigh': (3, 1, 2, 2, 3, 1, 4), 'call': (-2, 1, 1, 2, 2, 1, 1, 6)},
        'line': {'flow': (-1, 1, 1, 1, 2, 2, 2, 1, 1, 4), 'answer': (2, 1, 1, 4, 2, 1, 1, 4),
                 'steps': (-2, 1, 1, 2, 2, 1, 1, 2, 4)},
        'land': {'land': (-2, 1, 1, 2, 2, 6, -2), 'land_long': (3, 1, 2, 2, 6, -2),
                 'sigh_land': (-1, 1, 2, 2, 2, 4, -4), 'antic': (-2, 1, 1, 2, 1, 7, -2)},
    },
    # the singable song family in 3/4 (the new-age waltz, songs/pro-newage-waltz): two 8ths rising into a note held
    # over the bar line, a stepwise fall; every landing on the second bar's downbeat breathes
    'song3': {
        'motif': {'pickup': (-2, 1, 1, 6, 2), 'lean': (3, 1, 2, 4, 2), 'rise3': (-1, 1, 1, 1, 6, 2),
                  'call': (-2, 2, 2, 3, 1, 2)},
        'line': {'flow': (2, 1, 1, 3, 1, 2, 2), 'answer': (2, 2, 2, 3, 1, 2), 'steps': (-2, 1, 1, 2, 3, 1, 2),
                 'lilt': (3, 1, 2, 2, 3, 1), 'turn': (2, 1, 1, 2, 4, 2), 'held': (4, 2, 3, 1, 2)},
        'land': {'land': (-2, 1, 1, 2, 4, -2), 'land_long': (3, 1, 2, 5, -1), 'sigh_land': (2, 2, 2, 4, -2),
                 'antic': (-2, 1, 1, 1, 5, -2)},
    },
    # the new-age song cells (new-age-piano; the learned generator's blind round 2: a beat-2 pickup opened 17-46 % of
    # the generated bars, 0-8 % of the composed ones - 72-92 % start on the downbeat): 'song' with most motifs and
    # lines on the downbeat, an anacrusis across the bar line, one beat-2 pickup cell left
    'na': {
        'motif': {'pickup': (-2, 1, 1, 3, 1, 2, 1, 1, 4), 'rise3': (-1, 1, 1, 1, 4, 1, 1, 1, 1, 4),
                  'sigh': (3, 1, 2, 2, 3, 1, 4), 'held': (4, 1, 1, 2, 2, 2, 4), 'dotted': (3, 1, 4, 2, 2, 4),
                  'across': (-6, 1, 1, 4, 2, 2)},
        'line': {'flow': (-1, 1, 1, 1, 2, 2, 2, 1, 1, 4), 'answer': (2, 1, 1, 4, 2, 1, 1, 4),
                 'walk': (2, 2, 2, 1, 1, 3, 1, 4), 'sway': (3, 1, 2, 2, 2, 1, 1, 4), 'steps': (-2, 1, 1, 2, 2, 1, 1, 2, 4)},
        'land': {'land': (-2, 1, 1, 2, 2, 6, -2), 'land_long': (3, 1, 2, 2, 6, -2), 'land_down': (4, 2, 2, 6, -2),
                 'sigh_land': (-1, 1, 2, 2, 2, 4, -4), 'antic': (-2, 1, 1, 2, 1, 7, -2)},
    },
    # ... and in 3/4 (blind round 2: every waltz one 2-bar cell - pickup, a note held three beats, an echo): no
    # pickup-and-hold motif, a hemiola (three half notes over the two bars), lines moving through the bar
    'na3': {
        'motif': {'lean': (3, 1, 2, 4, 2), 'stroll': (2, 2, 2, 3, 1, 2), 'arch3': (2, 1, 1, 2, 4, 2),
                  'hemi': (4, 4, 4), 'flow3': (2, 1, 1, 2, 2, 3, 1), 'turn3': (3, 1, 2, 2, 3, 1)},
        'line': {'flow': (2, 1, 1, 3, 1, 2, 2), 'answer': (2, 2, 2, 3, 1, 2), 'steps': (-2, 1, 1, 2, 3, 1, 2),
                 'lilt': (3, 1, 2, 2, 3, 1), 'turn': (2, 1, 1, 2, 4, 2), 'hemi': (2, 4, 4, 2)},
        'land': {'land': (-2, 1, 1, 2, 4, -2), 'land_long': (3, 1, 2, 5, -1), 'sigh_land': (2, 2, 2, 4, -2),
                 'antic': (-2, 1, 1, 1, 5, -2)},
    },
    # the lo-fi hum (lofi-piano): two to four notes, then space - a lazy pickup, a nod onto the & of a beat, long rests
    # for the loop and the left hand; the landings breathe a whole half bar
    'lofi': {
        'motif': {'nod': (-2, 1, 1, 4, -2, 1, 1, 4), 'lazy': (-1, 1, 2, 4, -4, 2, 2), 'hum': (3, 1, 4, -2, 2, 4),
                  'push': (-3, 1, 2, 2, -2, 2, 4)},
        'line': {'drift': (-2, 1, 1, 2, 2, -2, 1, 1, 4), 'step': (-1, 1, 2, 2, 2, -4, 4),
                 'answer': (2, 2, 4, -2, 1, 1, 4)},
        'land': {'land': (-2, 1, 1, 4, 6, -2), 'sigh': (2, 2, 4, 4, -4), 'antic': (-3, 1, 2, 1, 7, -2),
                 'late': (-4, 2, 2, 2, -6)},
    },
}
# the bridge's own rhythm (blind round 4: the B in the A's cells): long notes against the moving lines - its
# 'contrast' phrases draw one of these (or, now and then, its counter-motif cell)
# (two attacks a bar at least in the jazz families - blind round 7: a bridge of one-note bars without its own idea)
for _fam, _long in (('medium', {'whole': (6, 2, 3, 3, -2), 'tied': (-2, 4, 2, 2, 4, 2), 'held': (4, 3, 1, 4, 2, -2)}),
                    ('ballad', {'whole': (6, 2, 4, 2, -2), 'sigh': (5, 1, 2, 4, 2, -2), 'tied': (-2, 4, 2, 4, 2, 2)}),
                    ('waltz', {'held': (3, 3, 2, 2, -2), 'tied': (-2, 3, 1, 4, 2), 'long': (4, 2, 2, 3, -1)}),
                    ('song', {'whole': (8, 4, 2, -2), 'held': (-2, 6, 2, 4, -2), 'sigh': (6, 2, 6, -2)}),
                    ('song3', {'whole': (6, 4, -2), 'held': (-2, 4, 2, 4), 'sigh': (4, 2, 4, -2)}),
                    ('na', {'whole': (8, 4, 2, -2), 'held': (-2, 6, 2, 4, -2), 'sigh': (6, 2, 6, -2)}),
                    # (round r9: the waltz's chorus in one-note bars, 18 of 107 - two attacks per bar)
                    ('na3', {'whole': (4, 2, 4, 2), 'held': (-1, 1, 4, 2, 2, 2), 'sigh': (4, 2, 3, 1, 2)}),
                    ('lofi', {'whole': (8, 4, -4), 'held': (-2, 6, 4, -4), 'sigh': (6, 2, 4, -4)})):
    CELLS[_fam]['long'] = _long
CELLS_3 = ('waltz', 'song3', 'na3')
"""The 3/4 cell families (two 3/4 bars = 12 8ths): a 3/4 feel draws one of them (Genre.validate)."""

CONTOURS = {
    # The period plan (blind round 4: phrases circling one pitch, no goal): a drawn shape per part kind - (x 0..1 of
    # the part, semitones added to the phrase centres) read like an arc (composer.arc_at) - so every 4-bar phrase has
    # its own register and goal and the part peaks 60-75 % through it; name -> (points, weight). The bridge adds its
    # own register (BRIDGE_SHIFT). A blues chorus is AAB: the statement, again over the IV, the answer reaching up.
    'A': {'arch': (((0.0, -3), (0.65, 4), (1.0, -4)), 1.0), 'rise': (((0.0, -4), (0.72, 5), (1.0, 0)), 0.8),
          'wave': (((0.0, 0), (0.3, -3), (0.62, 4), (1.0, -3)), 0.7),
          'late': (((0.0, -2), (0.45, 1), (0.75, 5), (1.0, -2)), 0.6)},
    'B': {'plateau': (((0.0, 2), (0.6, 3), (1.0, -1)), 1.0), 'fall': (((0.0, 3), (0.62, 2), (1.0, -2)), 0.7),
          'climb': (((0.0, -1), (0.7, 3), (1.0, 1)), 0.8)},
    'blues': {'answer': (((0.0, -2), (0.45, 0), (0.75, 4), (1.0, -3)), 1.0),
              'lift': (((0.0, -3), (0.3, 0), (0.7, 4), (1.0, -2)), 0.8)},
}
BRIDGE_SHIFT = {3: 2.0, 4: 1.5, 5: 0.8, 2: 0.8, -3: 0.5}
"""The bridge's register against the A's (semitones, drawn): mostly up, sometimes below the A."""
PHRASE_ENDS = {'down': 0.25, 'breath': 0.3, 'antic': 0.15, 'pickup': 0.1, 'lh': 0.2}
BRIDGE_ENDS = {'pickup': 0.5, 'down': 0.3, 'antic': 0.2}
"""How a phrase ends (composer: its land cell, drawn per phrase end - blind round 4: the same held landing every
time): down (the landing on the downbeat), breath (the landing held, then half a bar of silence), antic (anticipated
an 8th early, held over the bar line), pickup (a short landing, then a pickup of 8ths into the next phrase), lh (a
short landing, the right hand rests: the left hand's answer has the bar). Mostly a landing and a breath, rarely a
pickup straight into the next phrase (endless r6: "an endless monotone line of notes"). The tune's final cadence
always lands on the downbeat. The bridge's last phrase draws from BRIDGE_ENDS: its line keeps going into the
turnaround (blind round 5: a bridge faded out to grace notes), no 'lh'."""
PEAK_PART = {'last': 0.6, 'arc': 0.4}
"""Where the head's single climax goes (composer, drawn per tune): 'last' in the form's last section (an AABA's last A
then restates only its first half and climbs to the peak in a new second half; an ABAC's C; blind round 5: one
register peak per chorus, in the last section), 'arc' where the form's tension curve peaks (an AABA's bridge)."""
DEVELOP_RHYTHM = {'same': 0.3, 'displace': 0.3, 'truncate': 0.25, 'augment': 0.15}
"""How the A's 'develop' / 'answer' phrase treats the hook's rhythm (composer._vary_cell, drawn per phrase - blind
round 5: one 4-attack cell ~12 times in a tune): the same rhythm sequenced, displaced an 8th later, truncated to its
first bar and a long note, or its first bar augmented."""
SECOND_CHORUS = {'answer': 0.5, 'early': 0.3, 'second': 0.15}
"""Where a blues head's second chorus varies (by phrase function, drawn - blind round 4: chorus 2 bar 9 jumping to
the peak in every blues): answer (bars 9-12 rewritten, the climax there), early (bars 9-12 rewritten lower, the climax
in the first chorus's answer), second (the second statement over the IV and the turnaround rewritten, the climax in
bars 5-6)."""
FEEL_FORMS = {'blues': {'straight': (0.25, 1.0), 'shuffle': (1.0, 0.2), 'bossa': 0.06, 'ballad': 0.2, 'waltz': 0.0},
              'AABA': {'shuffle': 0.0, 'bossa': 1.4}, 'ABAC': {'shuffle': 0.0, 'bossa': 1.4}}
"""The feel / form pairing (blind round 4: a bossa blues, a straight-8th jazz blues read as random): a form's weight
on each feel (default 1; a pair = (straight 8ths, swung)) - a blues swings or is a straight-8th shuffle, a bossa blues
is rare, a bossa wants a song form. compose(): the form is drawn first (by the mood x what its feels allow), then the
feel; a pinned feel (a set plan) weights the forms instead."""

# ------------------------------------------------------------------------------------------------ the spec

FORMS = {
    # form -> the head's parts (letter = its section kind), the bars per part (4/4; a waltz doubles them), the
    # parts the head out plays, how many solo choruses fit
    'AABA': {'parts': ('A1', 'A2', 'B', 'A3'), 'bars': 8, 'out': ('B', 'A3'), 'solo': 1},
    'ABAC': {'parts': ('A1', 'B', 'A2', 'C'), 'bars': 8, 'out': ('A2', 'C'), 'solo': 1},
    'blues': {'parts': ('A1', 'A2'), 'bars': 12, 'out': ('A1', 'A2'), 'solo': 3},
    # the song form of a pop / new-age piano piece: the theme twice (A1 opens + turns, A2 opens + cadences), the
    # chorus HOOK (B), the build (C: the relative minor, climbing); 'blocks' = the BLOCKS kinds per part (an 'open'
    # is shared: every A opens alike) - the arrangement (plan['sections']) orders and repeats them
    'verse': {'parts': ('A1', 'A2', 'B', 'C'), 'bars': 8, 'out': ('B',), 'solo': 0,
              'blocks': {'A1': ('open', 'turn'), 'A2': ('open', 'final'), 'B': ('hook',), 'C': ('build',)}},
}
_FORM_KINDS = {'AABA': {'open', 'turn', 'final', 'to_bridge', 'bridge'}, 'ABAC': {'open', 'turn', 'contrast', 'climb',
                                                                                  'final'}, 'blues': {'blues'}}
"""The block kinds the composer's jazz forms draw (a form with 'blocks' names its own)."""
TAG_KINDS = ('tritone', 'backdoor', 'plagal', 'deceptive', 'cold', 'sus', 'IV', 'ii', 'IV_iv', 'vi')
SECTION_KEYS = {'name', 'part', 'frame', 'melody', 'dyn', 'figures', 'harmonize', 'chance', 'tempo', 'rit', 'fermata',
                'octave', 'keep_bars', 'lh_only', 'cadenza', 'peak', 'feels', 'drums', 'bars', 'tail', 'cadence', 'climax',
                'octave_half', 'bass', 'fill', 'turn', 'reharm', 'layouts', 'harm_share', 'vary', 'key'}
"""A 'piano' plan's sections (perform.build_piano), in order: name; part (a form part: its changes + melody) or frame
('intro' / 'tag': composer.frame's vamp + line); melody 'lift' (the part's lifted climax line, Tune.out_melody);
dyn: a dynamic mark or (start, end) / (start, peak, end) marks; figures: the feel's figure set; harmonize: 1 = 3rds /
6ths under long notes, 2 = chords (the climax); harm_share: the share of the long notes harmonized (default 1.0 for
chords, 0.5 for 3rds); chance: the section is played in that share of the tunes; tempo: x the
tune's tempo from here; rit: the last bar slows to x; fermata: beats held at the end; octave: the melody moved;
keep_bars: the frame's melody only in these bars (the interlude's echoes); lh_only: bars of left hand alone first;
cadenza: a flourish over the last dominant (romantic.fioritura) in that share of the tunes; peak: the section holds the
piece's climax; feels: the section is played only in these feels (a waltz's second strain pass); drums: False = the
mood's drums rest in this section (lofi-piano: the intro, the bridge, the coda); octave may be {octaves: weight}
(drawn). The drawn arrangement options bars / tail / cadence / climax / octave_half / bass / fill / turn: perform.ARRANGE_KEYS.
layouts: the layouts (plan['set']['layout']: the arrangement's forms, pinned per set slot or drawn per tune) the
section plays in (none: every layout); lh_only may be {bars: weight} (drawn). plan['form_bars']: the sections' bar
counts are form bars (a waltz, its form doubled, plays each as two 3/4 bars). plan['set'] {'layout' / 'climax' /
'shift': {choice: weight}, 'hook': {mode: {block: weight}}}: the set-level draws (composer.set_draws: per set
slot, never the last plan['set_memory'][key] slots' choice (default the slot before's); 'hook' the chorus's chord
block; 'climax' pins the climax section's kind, 'shift' moves the melody's register in semitones)."""
SET_KEYS = ('layout', 'climax', 'shift', 'hook', 'open', 'build')
ARRANGE_CHOICES = {'climax': {'lift', 'theme', 'step', 'climb', 'grow'}, 'cadence': {'home', 'vi', 'IV'}, 'octave_half': {0, 1},
                   'bass': {'root', 'walk'}, 'fill': {0, 1}, 'turn': {0, 1}}
VARY = ('keep', 'orn', 'rhythm', 'seq', 'invert')
"""How a return develops each 2-bar unit of its part (a plan section's 'vary' {kind: weight}, drawn per unit - the
arrangement record's 'vary' list; perform._vary; the learned generator's blind round 2, docs/LEARNED_GENERATOR.md
12.6: the last A repeated an earlier one note for note, 21-40 % copied bars against 2-15 % in the composed pieces):
  keep    the unit as the part has it
  orn     embellished: a third filled by a passing tone, a long note turning to its neighbour and back, else an
          appoggiatura from the step above
  rhythm  re-rhythmed: a pickup start moved onto the downbeat, the second bar's downbeat note anticipated an 8th,
          else a pair of 8ths dotted
  seq     the unit before (as played) sequenced a scale step toward this unit's register, re-fitted to the chords
  invert  the unit's contour turned over its first note, re-fitted to the chords
The section's last unit (its cadence) draws among VARY_END only (its weights)."""
VARY_END = ('keep', 'orn', 'rhythm')
KEY_SHIFTS = {'home': (0, None), 'step': (2, None), 'IV': (5, None), 'bVI': (8, None), 'bIII': (3, None),
              'III': (4, None), 'par': (0, 'major'), 'rel': (3, 'major')}
"""A section's key (a plan section's 'key' {mode: {name: weight}}, drawn - the arrangement record's 'key'; the
learned generator's blind round 2: no piece changed key, the composed ones move to bVI, the parallel major, bIII): the
semitones its material moves (a minor piece's 'par' / 'rel' also turn it to major - perform._modulate);
perform._keys leads in on the new key's dominant and back on the home dominant."""
FRAME_LINES = {'augment', 'fragment', 'answer', 'head'}
"""composer.frame's line kinds (harmony 'intro_lines' / 'tag_lines' weigh them; default INTRO_LINES / TAG_LINES)."""

# ------------------------------------------------------------------------------------------------ the arcs
# The plan, top-down, notes last: ONE mechanism on every level - an arc is a curve of (position 0..1, level 0..1)
# points, read piecewise-linear (composer.arc_at), and TARGETS turn a level into what the composer and the players
# aim at.
#   set    the stream: one energy per tune (a gig: a medium opener, contrast, a ballad after an up-tempo tune, the
#          highlight past the middle, a quiet closer); the energy picks the tune's feel, mood, tempo, and the key moves
#          by 'keys' from the tune before (composer.set_plan)
#   form   the tune: the tension over the head, read at the middle of every two-bar phrase; the curve's maximum is
#          THE climax - the tune's single highest note sits in that phrase, the phrases before it climb (the
#          approach), the ones after it fall (the release)
#   phrase the gestures of a part (composer.PLANS: statement, sequence, rise, answer, cadence), then the notes fill them
# A level -> TARGETS (lo at level 0, hi at level 1): the phrase's centre pitch (semitones from the genre's melody
# centre), its ceiling (semitones from the register's top; every phrase but the climax stays under peak - 3), the
# line cells (below cells[0] the sparsest, above cells[1] the densest), the pianist's touch lift (velocity) and
# density, the chord colour (scales the mood's richness).
ARCS = {
    'set': {'curve': ((0.0, 0.55), (0.12, 0.85), (0.22, 0.15), (0.45, 0.6), (0.65, 1.0), (0.85, 0.5), (1.0, 0.1)),
            'tunes': 10,                       # a set of ~40 minutes; --count N plays a set of N tunes
            # the tonic's move from the tune before (semitones up): related (4th / 5th / 3rds) or far, never the same
            'keys': {5: 3.0, 7: 3.0, 3: 1.5, 9: 1.5, 2: 1.0, 10: 1.0, 6: 0.8, 8: 0.6, 4: 0.6, 1: 0.3, 11: 0.3, 0: 0.0},
            'energy_bias': 0.3},               # a tune's energy shifts its tension curve by (energy - 0.5) * this
    'forms': {
        # AABA: A1 calm, A2 alike with another cadence, the bridge climbs to the climax (~2/3), A3 comes home on its
        # energy and releases
        'AABA': ((0.0, 0.2), (0.25, 0.3), (0.45, 0.4), (0.52, 0.55), (0.66, 1.0), (0.75, 0.45), (1.0, 0.15)),
        # ABAC: the B lifts, the A2 settles, the C climbs to the climax and cadences
        'ABAC': ((0.0, 0.2), (0.25, 0.3), (0.4, 0.45), (0.5, 0.35), (0.7, 0.6), (0.84, 1.0), (1.0, 0.45)),
        # a blues: the first chorus states, the second repeats its bars 1-8 and climbs in the rewritten 9-12 (the
        # climax) before it resolves
        'blues': ((0.0, 0.25), (0.5, 0.45), (0.66, 0.55), (0.85, 1.0), (1.0, 0.4)),
        # verse: the theme calm, its restatement a little up, the hook lifts, the build climbs to the climax near its
        # end (the arrangement's climax section then plays the hook lifted over it)
        'verse': ((0.0, 0.15), (0.25, 0.25), (0.45, 0.4), (0.55, 0.6), (0.72, 0.6), (0.92, 1.0), (1.0, 0.8)),
    },
    'targets': {'center': (-4, 6), 'ceiling': (-3, 0), 'touch': (-8, 8), 'density': (-0.1, 0.2),
                'colour': (0.8, 1.4), 'cells': (0.35, 0.7)},
    'climax': ('line', 'develop', 'contrast', 'answer', 'motif'),   # phrase roles that may carry the climax (a motif:
    #                                                                 not a part's opening - the hook restated higher)
}


JAZZ_HARMONY = {'blocks': BLOCKS, 'colours': COLOURS, 'intros': INTROS, 'intro_tonic': INTRO_TONIC,
                'endings': ENDINGS, 'tag_approach': TAG_APPROACH, 'tag_frames': TAG_FRAMES}
"""A genre's chord VOCABULARY (Genre.harmony): the progression blocks per mode and kind, how abstract qualities are
coloured, the intro vamps (+ those that want the head on the tonic), the end chord's quality, the tag's approach into
it. These are the jazz tables; a genre replaces them with its own (new-age: pop progressions, classical: cadences)."""

JAZZ_TITLES = {
    'adj': ['Blue', 'Quiet', 'Late', 'Velvet', 'Amber', 'Silver', 'Paper', 'Small', 'Slow', 'Distant', 'Gentle',
            'Borrowed', 'Folded', 'Lantern', 'Copper', 'Second', 'Last', 'Other', 'Winter', 'Indigo'],
    'noun': ['Hour', 'Avenue', 'Window', 'Rain', 'Streetlight', 'Corner', 'Promise', 'Letter', 'Harbor', 'Stairway',
             'Umbrella', 'Coat', 'Lamplight', 'Snowfall', 'Bridge', 'Postcard', 'Morning', 'Ticket', 'Matchbook',
             'Kettle', 'Balcony', 'Doorway', 'Echo', 'Ferry'],
    'place': ['Bleecker', 'Carmine', 'Barrow', 'Cornelia', 'Morton', 'Bedford', 'Grove', 'Charles', 'Perry',
              'Christopher', 'Hudson', 'Leroy', 'Commerce', 'Waverly', 'Gay Street', 'Bank Street', 'Horatio'],
    'time': ['Two A.M.', 'Half Past Ten', 'Blue Monday', 'Sunday', 'November', 'After Hours', 'First Light',
             'Midnight', 'Early Spring', 'Late August'],
    'shapes': ['{adj} {noun}', '{place} {noun}', '{noun} on {place}', 'The {adj} {noun}', '{time} {noun}',
               '{adj} {noun} {suffix}', '{place} at {time}', 'A {noun} for {place}'],
    'suffix': {'waltz': 'Waltz', 'blues': 'Blues', 'bossa': 'Bossa', 'ballad': 'Ballad', '': 'Song'},
}
"""Title words (Genre.titles): each word list drawn once (in sorted order), a shape filled with them ({key}: the key
spelled out, {suffix}: by the feel / form); shapes may be a {feel: [shapes]} dict."""


@dataclass
class Genre:
    """One endless genre as data (see the module docstring). Every dict is validated by validate()."""
    name: str
    description: str
    forms: dict                      # form name -> weight (FORMS)
    moods: dict                      # mood -> {'feels': {feel: w}, 'modes': {major/minor: w}, 'keys': {mode: [..]},
    #                                   'tempo': shift (BPM), 'colour': 0..2 tension richness, 'tritone': p,
    #                                   'forms': {form: w} (optional, replaces forms), 'register': (lo, hi),
    #                                   'center' / 'peak' (note names: the melody's, instead of genre.melody's),
    #                                   'drums': a 'piano' plan's drums {'style': drummer style, 'density', 'vel'}
    #                                   or None (lofi-piano: study with the kit, rain piano only)}
    feels: dict                      # feel -> {'tempo': (lo, hi), 'meter': 3|4, 'cells': CELLS key, 'style': pianist
    #                                   style, 'lh': LH style or None, 'solo': vocabulary style, 'swing': allowed,
    #                                   'comp': jazz.comp options (bossa left hand) or None, 'bass_pattern': str|None,
    #                                   'rubato': intro rubato depth, 'touch': (lo, hi) head velocity frame,
    #                                   'body': the pianist's humanize.BODIES profile ('piano' plans; default: the
    #                                   preset's, jazz.Feel.body), 'groove': the feel's own swing ratio when no
    #                                   swing is asked for (lofi's lazy swing), 'steady': the 'piano' plan keeps
    #                                   strict time (no phrase rubato / lilt / inhale: a drum loop plays along)}
    band: dict                       # {'preset': bands.make name, 'without': roles, 'master_gain': dB,
    #                                   'options': the preset's own options (jazz_trio voicing=),
    #                                   'profile': analysis profile, 'loudness': (lo, hi) LUFS gate, 'bass': walking
    #                                   bass options or None, 'drums': brushes options or None, 'trims': {role:
    #                                   dB on its fader}, 'pans': {role: the instrument's own pan}, 'sends': {role:
    #                                   {bus: dB added}}, 'eq': {role: eq params added to its chain}}
    plan: dict                       # {'intro': bars, 'tag': bars, 'end': bars, 'head': {...}, 'solo': {...}, ...,
    #                                   'candidates': the runner's best-of-N (default 8)}
    swing: float = 0.6               # the swing ratio when --swing (an option; HUMAN_FEEDBACK: default off)
    # (an A section spans an octave+: the register an octave and a fifth, the climax over it - blind round 5: an A
    # inside A4-Eb5)
    melody: dict = field(default_factory=lambda: {'register': ('G4', 'Bb5'), 'center': 'Eb5', 'peak': 'Db6'})
    arc: dict = field(default_factory=lambda: copy.deepcopy(ARCS))   # the plan's arcs (ARCS)
    album: str = 'Endless Sessions'
    harmony: dict = field(default_factory=lambda: dict(JAZZ_HARMONY))   # the chord vocabulary (JAZZ_HARMONY)
    titles: dict = field(default_factory=lambda: dict(JAZZ_TITLES))     # the title words (JAZZ_TITLES)
    style: str = 'jazz'              # the style family (endless piano --style; the cover, the mp3 genre tag)

    def but(self, **changes) -> 'Genre':
        """A copy with fields replaced (dicts deep-copied first: the original stays untouched)."""
        g = replace(self, **{f.name: copy.deepcopy(getattr(self, f.name)) for f in fields(self)})
        return replace(g, **changes)

    def validate(self) -> 'Genre':
        """Raise ComposeError on anything the composer or the players could not use."""
        from .. import pianist
        from .. import bands as _bands

        def bad(msg):
            raise ComposeError(f"endless genre {self.name!r}: {msg}")
        organ = self.plan.get('perform') == 'organ'    # (an organ genre: no pianist; endless/organ.py checks it)
        forms = dict(self.forms)
        for m in self.moods.values():
            forms.update(m.get('forms', {}))
        for f, w in forms.items():
            if f not in FORMS:
                bad(f"unknown form {f!r} (forms: {', '.join(FORMS)})")
            if not w >= 0:
                bad(f"form {f!r} weight must be >= 0")
        if not self.moods:
            bad('no moods')
        for name, m in self.moods.items():
            for k in ('feels', 'modes', 'keys'):
                if k not in m:
                    bad(f"mood {name!r} needs {k!r}")
            for f in m['feels']:
                if f not in self.feels:
                    bad(f"mood {name!r}: unknown feel {f!r} (feels: {', '.join(self.feels)})")
            for mode in m['modes']:
                if mode not in BLOCKS:
                    bad(f"mood {name!r}: mode must be major / minor, got {mode!r}")
                if not m['keys'].get(mode):
                    bad(f"mood {name!r}: no keys for mode {mode!r}")
                for k in m['keys'][mode]:
                    chord(k)                                  # a valid root name
        for name, f in self.feels.items():
            lo, hi = f['tempo']
            if not 30 <= lo <= hi <= 300:
                bad(f"feel {name!r} tempo {f['tempo']!r} must be 30..300")
            if f.get('meter', 4) not in (3, 4):
                bad(f"feel {name!r} meter must be 3 or 4")
            if f['cells'] not in CELLS:
                bad(f"feel {name!r} cells must be one of {', '.join(CELLS)}")
            if (f.get('meter', 4) == 3) != (f['cells'] in CELLS_3):
                bad(f"feel {name!r}: a 3/4 feel draws a 3/4 cell family ({', '.join(CELLS_3)}), a 4/4 feel another")
            if not organ and f['style'] not in pianist.STYLES:
                bad(f"feel {name!r} style must be a pianist style ({', '.join(pianist.STYLES)})")
            if f.get('lh') is not None and f['lh'] not in pianist.LH_STYLES:
                bad(f"feel {name!r} lh must be one of {', '.join(pianist.LH_STYLES)} or None")
            for set_, figs in (f.get('figures') or {}).items():
                for fg in ([figs] if isinstance(figs, str) else figs):
                    if fg not in pianist.FIGURES:
                        bad(f"feel {name!r} figures[{set_!r}]: {fg!r} is no pianist.FIGURES figure "
                            f"({', '.join(pianist.FIGURES)})")
            if f.get('body') is not None and f['body'] not in BODIES:
                bad(f"feel {name!r} body must be one of {', '.join(BODIES)} (humanize.BODIES)")
            for sec, st in (f.get('lh_plan') or {}).items():
                for s_ in ([st] if isinstance(st, str) else st):
                    if s_ not in pianist.LH_STYLES and s_ not in pianist.FIGURES:
                        bad(f"feel {name!r} lh_plan[{sec!r}]: {s_!r} is no LH style / FIGURES figure")
            six = f.get('sixteenths')
            if six is not None and (set(six) != {'every', 'bars'} or not all(v > 0 for v in six.values())):
                bad(f"feel {name!r} sixteenths must be {{'every': bars, 'bars': bars}} (both > 0)")
            if f.get('groove') is not None and not 0.5 <= f['groove'] <= 0.75:
                bad(f"feel {name!r} groove (its own swing ratio when --swing is not given) must be 0.5..0.75")
        if self.band.get('preset') not in _bands.list():
            bad(f"band preset {self.band.get('preset')!r} unknown (python -m agentsound bands)")
        from .. import drummer as _drummer
        for name, m in self.moods.items():
            d = m.get('drums')
            if d is None:
                continue
            if not isinstance(d, dict) or set(d) - {'style', 'density', 'vel'} or d.get('style') not in _drummer.STYLES:
                bad(f"mood {name!r} drums: None or {{'style': a drummer.STYLES style, 'density': 0..1, 'vel': x}}")
            if 'drums' not in _bands.get(self.band['preset']).roles:
                bad(f"mood {name!r} has drums, but the band preset {self.band['preset']!r} has no 'drums' role")
            loose = [f for f in m['feels'] if not self.feels[f].get('steady')]
            if loose:
                bad(f"mood {name!r} has drums: its feels must keep strict time ('steady': True), not {loose}")
        H = self.harmony
        for k in ('blocks', 'colours', 'intros', 'endings'):
            if k not in H:
                bad(f"harmony needs {k!r} (see JAZZ_HARMONY)")
        if set(H) - {'blocks', 'colours', 'intros', 'intro_tonic', 'endings', 'tag_approach', 'tag_frames',
                       'intro_lines', 'tag_lines', 'tag_span', 'reharm', 'sus_budget', 'sus_swap'}:
            bad(f"harmony: unknown keys {sorted(set(H) - set(JAZZ_HARMONY))}")
        if 'sus_budget' in H and (not H['sus_budget'] or any(not isinstance(k, int) or k < 0 or w < 0
                                                              for k, w in H['sus_budget'].items())):
            bad("harmony['sus_budget']: {dominant sus4 chords kept per tune: weight}")
        if set(H.get('sus_swap') or {}) - {'7', 'ii', 'IV'}:
            bad("harmony['sus_swap']: {'7' / 'ii' / 'IV': weight} - what a dominant sus4 over the budget becomes")
        for mode, kinds in H['blocks'].items():
            for kind, table in kinds.items():
                for bname, spec in table.items():
                    _check_block(spec, f"{mode}/{kind}/{bname}", bad)
        modes = {mode for m in self.moods.values() for mode in m['modes']}
        for f in forms:
            need = set(k for ks in (FORMS[f].get('blocks') or {}).values() for k in ks) or _FORM_KINDS[f]
            for mode in modes:
                miss = need - set(H['blocks'].get(mode, {}))
                if miss:
                    bad(f"form {f!r} in {mode}: the harmony has no blocks of kind {', '.join(sorted(miss))}")
        for mode, table in H['intros'].items():
            for iname, (spec, w) in table.items():
                own = ' '.join(t for t in spec.split() if not t.startswith('head:')) or 'I'
                _check_block(own, f"intro {mode}/{iname}", bad)
        for cq in list(H['colours'].values()) + list(H['endings'].values()):
            for q in cq:
                chord('C' + q)
        for k in H.get('tag_approach', {}):
            if k not in TAG_KINDS:
                bad(f"harmony tag_approach {k!r}: one of {', '.join(TAG_KINDS)}")
        for k in ('intro_lines', 'tag_lines'):
            if set(H.get(k, {})) - FRAME_LINES:
                bad(f"harmony {k}: line kinds of {', '.join(sorted(FRAME_LINES))}")
        for mode, table in (H.get('reharm') or {}).items():
            for src, subs in table.items():
                _check_block(src, f"reharm {mode}/{src}", bad)
                for tok, w in subs.items():
                    _check_block(tok, f"reharm {mode}/{src}/{tok}", bad)
                    if not w > 0 or len(tok.split()) != 1:
                        bad(f"harmony reharm {mode}/{src}: {{one chord token: weight > 0}}")
        if not isinstance(H.get('tag_span', 0.5), (int, float)) or not 0 < H.get('tag_span', 0.5) <= 2:
            bad("harmony tag_span: the coda approach's length in bars (0 < x <= 2; default 0.5)")
        for where, spec in [('plan dyn', self.plan.get('dyn')), ('plan dyn_out_peak', self.plan.get('dyn_out_peak'))] \
                + [(f"feel {n!r} dyn", f.get('dyn')) for n, f in self.feels.items()]:
            for sec, d in (spec or {}).items():
                if not all(lv in _LEVELS for lv in ([d] if isinstance(d, str) else d)) or \
                        (not isinstance(d, str) and len(d) not in (2, 3)):
                    bad(f"{where}[{sec!r}]: a dynamic mark or (start, end) / (start, peak, end) of {', '.join(_LEVELS)}")
        if not isinstance(self.plan.get('candidates', 8), int) or self.plan.get('candidates', 8) < 1:
            bad("plan['candidates'] (endless best-of-N) must be a whole number >= 1")
        rs = self.melody.get('restate')
        if rs is not None and (not isinstance(rs, dict) or not rs or
                               any(not isinstance(k, int) or k < 1 or w < 0 for k, w in rs.items())):
            bad("melody['restate']: {2-bar units a later A restates (>= 1): weight}")
        if not isinstance(self.plan.get('candidate_tries', 1), (int, float)) or \
                not 1 <= self.plan.get('candidate_tries', 1) <= 4:
            bad("plan['candidate_tries']: seeds per best-of-N candidate, 1..4 (rejected seeds replaced; default 1)")
        perf = self.plan.get('perform', 'jazz')
        if perf not in ('jazz', 'piano', 'organ', 'orchestra'):
            bad("plan['perform'] must be 'jazz' (head / solo / head out), 'piano' (plan['sections']), 'organ' "
                "(plan['arrangements']: endless/organ.py) or 'orchestra' (a piano plan orchestrated: "
                "endless/orchestra.py)")
        if perf == 'organ':
            from .organ import validate_plan
            validate_plan(self, bad)
        if perf == 'orchestra':
            from .orchestra import validate_plan as _vo
            _vo(self, bad)
        if perf in ('piano', 'orchestra'):
            from .orchestra import SECTION_KEYS as _OK
            own_keys = SECTION_KEYS | (_OK if perf == 'orchestra' else set())
            if self.plan.get('end_top', 'line') != 'line':
                bad("plan['end_top']: 'line' (the final chord's top resolves the last melody note) or absent")
            if not isinstance(self.plan.get('max_hold', 1.0), (int, float)) or self.plan.get('max_hold', 1.0) <= 0:
                bad("plan['max_hold']: the longest right-hand melody note in beats (> 0) or absent")
            if set(self.plan.get('lh') or {}) - {'bass_lo', 'cap', 'repeats'}:
                bad("plan['lh']: the broken-chord hand's register {'bass_lo': lowest bass, 'cap': top} and "
                    "'repeats' (an inner tone struck that many times running at most) (pianist.figure)")
            if set(self.plan.get('pedal') or {}) - {'lift_ms', 'flutter_ms', 'flutter_to', 'tail'}:
                bad("plan['pedal']: romantic.pedal_changes options lift_ms / flutter_ms / flutter_to / tail")
            if not 80 <= self.plan.get('cap', 106) <= 127:
                bad("plan['cap']: the right hand's top velocity 80..127 (default 106)")
            if set(self.plan.get('ornaments') or {}) - {'turn', 'mordent', 'prall'} or                     any(not 0 <= v <= 1 for v in (self.plan.get('ornaments') or {}).values()):
                bad("plan['ornaments']: {'turn' / 'mordent' / 'prall': chance 0..1 per part section}")
            ts = self.plan.get('touch_span')
            if ts is not None and (not isinstance(ts, dict) or not ts or any(
                    not (isinstance(k, tuple) and len(k) == 2 and all(-15 <= x <= 15 for x in k)) or w < 0
                    for k, w in ts.items())):
                bad("plan['touch_span']: {(low offset, high offset) of the feel's touch, -15..15: weight}")
            sw = self.plan.get('swell')
            if sw is not None and (not isinstance(sw, dict) or not sw or
                                   any(k not in (0, 1, 2) or w < 0 for k, w in sw.items())):
                bad("plan['swell']: {levels 0 / 1 / 2: weight} - a phrase's hairpin over the section's dynamics")
            secs = self.plan.get('sections') or []
            if not secs:
                bad("a 'piano' plan needs plan['sections']")
            bl = self.plan.get('bloom')
            if bl is not None:
                if not isinstance(bl, dict) or set(bl) != BLOOM_KEYS:
                    bad(f"plan['bloom']: the keys {', '.join(sorted(BLOOM_KEYS))} (genres._NA_BLOOM)")
                else:
                    for k_ in ('figures', 'bloom_hand', 'hand'):
                        for fs in bl[k_].values():
                            for fg in ([f_ for st_ in fs for f_ in st_] if k_ == 'figures' else fs):
                                if fg not in pianist.FIGURES:
                                    bad(f"plan['bloom'][{k_!r}]: {fg!r} is no pianist.FIGURES figure")
                    if set(bl['at']) - {s_['name'] for s_ in secs if 'part' in s_}:
                        bad("plan['bloom']['at']: {a part section's name: weight}")
                    if any(not 1.0 < x <= 1.2 for x in bl['push']) or any(not 0 < x <= 1 for x in bl['reach']) \
                            or any(not 0 <= x <= 1 for x in bl['carry']) or any(not 0.7 <= x < 1 for x in bl['rit'])                             or not 0 <= bl['weave'] <= 1:
                        bad("plan['bloom']: push 1..1.2, reach 0..1, carry 0..1, rit 0.7..1 (x the tempo), weave 0..1")
            from .arrangement import PLAY_KEYS
            pl_ = self.plan.get('play') or {}
            if set(pl_) - set(PLAY_KEYS) or any(not isinstance(w, dict) or not w for w in pl_.values()):
                bad(f"plan['play']: {{one of {', '.join(PLAY_KEYS)}: {{value: weight}}}} (the pianist's per-piece "
                    f"choices)")
            for kind_, vs_ in (self.plan.get('phrase_variants') or {}).items():
                if kind_ not in ('common', 'waltz') or any(not v_ or any(len(pl) != (8 if kind_ == 'waltz' else 4)
                                                                         for pl, _ in v_) for v_ in vs_.values()):
                    bad("plan['phrase_variants']: {'common' (4 units) / 'waltz' (8): {part kind: [(plan, weight)]}}")
            lays = (self.plan.get('set') or {}).get('layout') or {}
            for sd in secs:
                if set(sd.get('layouts', ())) - set(lays):
                    bad(f"plan section {sd.get('name')!r}: layouts {sd['layouts']!r} not all in plan['set']['layout']")
                lo_ = sd.get('lh_only')
                if isinstance(lo_, dict) and any(not isinstance(k, int) or k < 0 or w < 0 for k, w in lo_.items()):
                    bad(f"plan section {sd.get('name')!r}: lh_only must be bars or {{bars: weight}}")
            for k, w in (self.plan.get('set') or {}).items():
                if k in ('hook', 'open', 'build'):
                    blocks = self.harmony.get('blocks') or {}
                    if not isinstance(w, dict) or any(m not in blocks or not isinstance(wm, dict) or not wm
                                                      or set(wm) - set(blocks[m].get(k) or {})
                                                      or any(x < 0 for x in wm.values()) for m, wm in w.items()):
                        bad(f"plan['set'][{k!r}]: {{mode: {{a harmony['blocks'][mode][{k!r}] block: weight >= 0}}}}")
                    continue
                if k not in SET_KEYS or not isinstance(w, dict) or not w or any(x < 0 for x in w.values()):
                    bad(f"plan['set'][{k!r}]: one of {', '.join(SET_KEYS)} -> {{choice: weight >= 0}}")
                if k == 'climax' and set(w) - ARRANGE_CHOICES['climax']:
                    bad(f"plan['set']['climax']: choices of {sorted(ARRANGE_CHOICES['climax'])}")
                if k == 'shift' and any(not isinstance(x, int) or abs(x) > 7 for x in w):
                    bad("plan['set']['shift']: register shifts in semitones, -7..7")
            for sd in secs:
                extra = set(sd) - own_keys
                if extra or 'name' not in sd or ('part' in sd) == ('frame' in sd):
                    bad(f"plan section {sd!r}: a name, a 'part' (a form part) or a 'frame' (intro / tag), keys "
                        f"{', '.join(sorted(SECTION_KEYS))}")
                for f in forms:
                    if 'part' in sd and sd['part'] not in FORMS[f]['parts']:
                        bad(f"plan section {sd['name']!r}: part {sd['part']!r} is not in form {f!r}")
                for k in ('bars', 'tail', 'cadence', 'climax', 'octave_half', 'bass', 'fill', 'turn'):
                    if k in sd and (not isinstance(sd[k], dict) or not sd[k] or any(w < 0 for w in sd[k].values())
                                    or (k in ARRANGE_CHOICES and set(sd[k]) - ARRANGE_CHOICES[k])):
                        bad(f"plan section {sd['name']!r}: {k} must be {{choice: weight}}"
                            + (f" of {sorted(ARRANGE_CHOICES[k])}" if k in ARRANGE_CHOICES else ''))
                hs_ = sd.get('harm_share')
                if 'harm_share' in sd and not (all(0 < x <= 1 for x in (hs_ if isinstance(hs_, dict) else [hs_]))
                                               and sd.get('harmonize')):
                    bad(f"plan section {sd['name']!r}: harm_share must be 0..1 on a harmonized section")
                if 'reharm' in sd and (not isinstance(sd['reharm'], dict) or not sd['reharm'] or
                                       any(not 0 <= k <= 1 or w < 0 for k, w in sd['reharm'].items())):
                    bad(f"plan section {sd['name']!r}: reharm must be {{share of the chords 0..1: weight}}")
                dyns = sd.get('dyn', ())
                for dy in (list(dyns) if isinstance(dyns, dict) else [dyns]):     # (a {plan: weight}: drawn)
                    for lv in ([dy] if isinstance(dy, str) else dy):
                        if lv not in _LEVELS:
                            bad(f"plan section {sd['name']!r}: dyn {lv!r} is no dynamic mark ({', '.join(_LEVELS)})")
                if 'vary' in sd:
                    if not isinstance(sd['vary'], dict) or not sd['vary'] or set(sd['vary']) - set(VARY) or \
                            any(w < 0 for w in sd['vary'].values()):
                        bad(f"plan section {sd['name']!r}: vary must be {{kind: weight}} of {', '.join(VARY)} "
                            f"(per 2-bar unit of a part or a frame)")
                if 'key' in sd:
                    k_ = sd['key']
                    if not isinstance(k_, dict) or set(k_) - {'major', 'minor'} or any(
                            not isinstance(w, dict) or set(w) - set(KEY_SHIFTS) or any(x < 0 for x in w.values())
                            for w in k_.values()):
                        bad(f"plan section {sd['name']!r}: key must be {{mode: {{key: weight}}}} of "
                            f"{', '.join(KEY_SHIFTS)}")
                for f_ in sd.get('feels', ()):
                    if f_ not in self.feels:
                        bad(f"plan section {sd['name']!r}: feels {f_!r} is no feel of the genre")
                for fname, feel in self.feels.items():
                    if sd.get('feels') and fname not in sd['feels']:
                        continue
                    fs_ = sd.get('figures')
                    if fs_ and set(fs_ if isinstance(fs_, dict) else [fs_]) - set(feel.get('figures') or {}):
                        bad(f"plan section {sd['name']!r}: figures {fs_!r} missing in a feel's figures")
            for lay in lays:
                names = [sd['name'] for sd in secs if not sd.get('layouts') or lay in sd['layouts']]
                if len(names) != len(set(names)) or not any(sd.get('peak') for sd in secs
                                                             if not sd.get('layouts') or lay in sd['layouts']):
                    bad(f"plan layout {lay!r}: its sections need unique names and one peak section ({names})")
        for fname_, fam in CELLS.items():
            for role, cells in fam.items():
                for cname, cell in cells.items():
                    bar = 6 if fname_ in CELLS_3 else 8
                    if sum(abs(x) for x in cell) != 2 * bar:
                        bad(f"cell {cname!r} does not fill two bars")
                    if role == 'land':
                        _land_index(cell, bar)                # raises when the landing note is missing
        self._validate_arcs(bad)
        if not 0.5 <= self.swing <= 0.75:
            bad(f"swing ratio {self.swing} must be 0.5..0.75")
        for k in ('intro', 'tag', 'end'):
            if not isinstance(self.plan.get(k), int) or self.plan[k] < 0:
                bad(f"plan[{k!r}] must be a number of bars")
        from .. import soloist
        for name, d in ((self.plan.get('solo') or {}).get('shapes') or {}).items():
            if d.get('arc') not in soloist.ARCS or not d.get('weight', 0) > 0:
                bad(f"plan solo shape {name!r}: an arc of soloist.ARCS and a weight > 0")
            if set(d) - {'weight', 'arc', 'weights', 'dynamics', 'double', 'solo_vel'}:
                bad(f"plan solo shape {name!r}: weight / arc / weights / dynamics / double / solo_vel only")
            for k in d.get('dynamics', ()):
                if k not in (self.plan.get('dynamics') or {}):
                    bad(f"plan solo shape {name!r}: unknown dynamic plan {k!r}")
        for name, d in (self.plan.get('dynamics') or {}).items():
            extra = set(d) - {'weight', 'solo_vel', 'out', 'shout', 'out_peak'}
            if extra or not d.get('weight', 0) > 0:
                bad(f"plan dynamics {name!r}: a weight > 0 and solo_vel / out / shout only (got {sorted(d)})")
            if not 100 <= d.get('shout', 110) <= 127:
                bad(f"plan dynamics {name!r}: shout is the velocity of its peak note, 100..127")
        return self


    def _validate_arcs(self, bad) -> None:
        a = self.arc
        for k in ('set', 'forms', 'targets', 'climax'):
            if k not in a:
                bad(f"arc needs {k!r}")
        curves = [('set', a['set'].get('curve'))] + [(f"forms/{f}", c) for f, c in a['forms'].items()]
        for where, c in curves:
            xs = [x for x, _ in c or ()]
            if len(xs) < 2 or xs[0] != 0.0 or xs[-1] != 1.0 or xs != sorted(xs) or \
                    not all(0.0 <= y <= 1.0 for _, y in c):
                bad(f"arc {where}: want (x, level) points from x=0 to x=1, levels 0..1")
        for f in set(self.forms) | {x for m in self.moods.values() for x in m.get('forms', {})}:
            if f not in a['forms']:
                bad(f"arc: no curve for form {f!r}")
        for k in ('center', 'ceiling', 'touch', 'density', 'colour', 'cells'):
            if len(a['targets'].get(k, ())) != 2:
                bad(f"arc targets[{k!r}] must be (at level 0, at level 1)")
        if not isinstance(a['set'].get('tunes'), int) or a['set']['tunes'] < 1:
            bad("arc set['tunes'] must be a number of tunes")
        for name, f in self.feels.items():
            if not 0.0 <= f.get('energy', 0.5) <= 1.0:
                bad(f"feel {name!r} energy must be 0..1 (the set plan picks feels by it; default 0.5)")
        for name, m in self.moods.items():
            if not 0.0 <= m.get('energy', 0.5) <= 1.0:
                bad(f"mood {name!r} energy must be 0..1 (the set plan picks moods by it; default 0.5)")


def _check_block(spec: str, where: str, bad) -> None:
    from .composer import parse_block
    try:
        parse_block(spec)
    except ComposeError as e:
        bad(f"block {where}: {e}")


def _land_index(cell, bar: int) -> int:
    """Index of a land cell's landing note: the note sounding on (or anticipating by an 8th) the second bar."""
    t = 0
    for i, x in enumerate(cell):
        if x > 0 and (t == bar or (t == bar - 1 and x >= 2)):
            return i
        t += abs(x)
    raise ComposeError(f"land cell {cell} has no note landing on the second bar")


# ------------------------------------------------------------------------------------------------ the genres

_KEYS_WARM = {'major': ['Db', 'Ab', 'Eb', 'Bb', 'F', 'Gb'], 'minor': ['C', 'F', 'G', 'Bb', 'D']}
_KEYS_BRIGHT = {'major': ['C', 'F', 'Bb', 'G', 'D', 'Eb'], 'minor': ['D', 'A', 'G', 'E', 'C']}

_MOODS = {
    'late-night': {'feels': {'ballad': 3, 'straight': 3, 'waltz': 1}, 'modes': {'major': 2, 'minor': 1},
                   'keys': _KEYS_WARM, 'tempo': -4, 'colour': 1.3, 'tritone': 0.3, 'energy': 0.35},
    'bright': {'feels': {'straight': 3, 'bossa': 2, 'waltz': 2, 'shuffle': 1}, 'modes': {'major': 4, 'minor': 1},
               'keys': _KEYS_BRIGHT, 'tempo': 6, 'colour': 0.8, 'tritone': 0.15, 'energy': 0.85},
    'blue': {'feels': {'straight': 3, 'ballad': 1, 'bossa': 1, 'shuffle': 2}, 'modes': {'major': 1, 'minor': 2},
             'keys': _KEYS_WARM, 'tempo': 0, 'colour': 1.1, 'tritone': 0.25,
             'forms': {'AABA': 1, 'ABAC': 1, 'blues': 3}, 'energy': 0.6},
    'tender': {'feels': {'ballad': 4, 'waltz': 2}, 'modes': {'major': 3, 'minor': 1}, 'keys': _KEYS_WARM,
               'tempo': -6, 'colour': 1.2, 'tritone': 0.2, 'energy': 0.15},
}

_PIANO_FEELS = {
    'ballad': {'tempo': (64, 78), 'meter': 4, 'cells': 'ballad', 'style': 'ballad', 'lh': 'tenths', 'solo': 'ballad',
               'swing': True, 'rubato': 0.07, 'touch': (46, 92), 'density': 0.55, 'master': 1.0,
               'energy': 0.1},
    'straight': {'tempo': (88, 112), 'meter': 4, 'cells': 'medium', 'style': 'straight', 'lh': 'shell',
                 'solo': 'straight', 'swing': True, 'rubato': 0.05, 'touch': (50, 98), 'density': 0.6,
                 'energy': 0.65},
    'bossa': {'tempo': (112, 132), 'meter': 4, 'cells': 'medium', 'style': 'straight', 'lh': None, 'solo': 'straight',
              'swing': False, 'rubato': 0.04, 'touch': (52, 96), 'density': 0.55, 'master': -1.5, 'energy': 0.85,
              # the left hand alone: bossa cells (rootless, soft, rolled) over a root-fifth line, both well under
              # the melody (at the trio's comping level they read as loud as the right hand and masked it)
              'comp': {'style': 'bossa', 'voicing': 'rootless', 'register': ('C3', 'F4'), 'intensity': 0.3,
                       'density': 0.5, 'vel': 42, 'roll': (10, 22)},
              'bass_pattern': 'R__f', 'bass_vel': (46, 70)},
    'waltz': {'tempo': (126, 156), 'meter': 3, 'cells': 'waltz', 'style': 'straight', 'lh': 'shell',
              'solo': 'straight', 'swing': True, 'rubato': 0.05, 'touch': (50, 96), 'density': 0.55,
              'energy': 0.4},
    # the straight-8th blues groove (FEEL_FORMS: blues only): the bar pianist's style, a stride left hand
    'shuffle': {'tempo': (100, 120), 'meter': 4, 'cells': 'medium', 'style': 'bar', 'lh': 'stride', 'solo': 'bar',
                'swing': True, 'rubato': 0.04, 'touch': (52, 98), 'density': 0.6, 'energy': 0.72},
}
# The left hand per section (perform.build: 'lh_plan' {intro / head / solo / out / tag: a LH style or a
# pianist.FIGURES broken-chord figure, or {name: weight} drawn per part, never twice running} - user 2026-10-09:
# the jazz should be like letters-to-the-morning: shells -> tenths -> stride / walking 10ths -> broken chords in
# the ballads' intro / tag, holding still under the melody's breaths; blind round 6: 8th-note broken chords under a
# jazz head read as "bare roots x8" - the body plays shells / tenths / rootless voicings), and the ballads' written
# dynamics ('dyn' over plan['dyn']: quiet statements, one climax, a soft ending)
_PIANO_FEELS['ballad'].update(
    lh_plan={'intro': {'flow': 1.0, 'tenths': 0.8}, 'head': {'tenths': 1.0, 'shell': 0.8, 'rootless': 0.6},
             'solo': {'shell': 1.0, 'tenths': 0.8}, 'out': {'tenths': 1.0, 'walk10': 0.6, 'shell': 0.6},
             'tag': {'flow': 1.0, 'open': 0.7}},
    dyn={'intro': 'p', 'head': ('p', 'mf'), 'solo': ('mp', 'mf'), 'out': ('mf', 'mp'), 'tag': ('mp', 'p'),
         'end': 'p'})
_PIANO_FEELS['straight'].update(
    lh_plan={'intro': {'tenths': 1.0, 'open': 0.5}, 'head': {'shell': 1.0, 'tenths': 0.8, 'walk10': 0.6},
             'solo': {'shell': 1.0, 'rootless': 0.5}, 'out': {'walk10': 0.8, 'stride': 0.6, 'shell': 0.6},
             'tag': {'tenths': 1.0, 'flow': 0.6}})
_PIANO_FEELS['waltz'].update(
    lh_plan={'intro': {'barcarolle': 1.0, 'tenths': 0.8}, 'head': {'shell': 1.0, 'waltz2': 0.8, 'tenths': 0.6},
             'solo': 'shell', 'out': {'shell': 1.0, 'waltz': 0.6, 'waltz2': 0.5},
             'tag': {'tenths': 1.0, 'barcarolle': 0.6}})
# the solo's 16th lines per feel (piano_vocab sixteenths: one per 'every' bars, at most 'bars' long; a planned
# double-time burst twice that) - blind round 7: a bossa solo in 16ths for 7 bars; a bossa's line moves in 8ths, a
# ballad's double time is idiomatic
for _f, _six in (('ballad', (4, 2)), ('straight', (8, 1.5)), ('bossa', (16, 1)), ('waltz', (8, 2)),
                 ('shuffle', (8, 1))):
    _PIANO_FEELS[_f]['sixteenths'] = {'every': _six[0], 'bars': _six[1]}
_PIANO_FEELS['shuffle'].update(lh_plan={'head': {'stride': 1.0, 'walk10': 0.7}, 'out': {'stride': 1.0, 'walk10': 1.0},
                                        'solo': 'stride'})
_JAZZ_DYN = {'intro': 'mp', 'head': ('mp', 'mf'), 'solo': ('mp', 'mf'), 'out': ('mf', 'mp'), 'tag': ('mf', 'mp'),
             'end': 'mp'}
"""The jazz piece's written dynamics per section (perform.section_dynamics, x the players' own velocities):
the head stated a little under the solo, the solo building to the peak, the head out at the head's level, the tag
coming down only in its last bars, the final chord a few LU under the piece (blind round 6: the references' ending
2-5 LU down, the form's loudness range 5.6-7.5 LU against the generated 8.7-13.5 - a faded form); 'dyn_out_peak'
when the drawn dynamic plan puts the peak in the head out (shout)."""

JAZZ_PIANO = Genre(
    name='jazz-piano',
    description='solo jazz piano: an original standard-like tune (AABA / ABAC / blues, ballad / straight / bossa / '
                'waltz) on the warm grand, harmonized and decorated by the pianist, one improvised chorus, the head '
                'out, a rolled ending',
    forms={'AABA': 3, 'ABAC': 2, 'blues': 1},
    moods=_MOODS,
    feels=_PIANO_FEELS,
    # the solo_piano preset (agentsound/bandlib/jazz.py: the grand voiced smooth, both hands, salon room + plate,
    # a gentle master); judged as solo piano (profile 'piano'); master_gain: the limiter drive (MASTER)
    band={'preset': 'solo_piano', 'master_gain': 6.0, 'profile': 'piano', 'loudness': (-22.0, -12.0),
          'bass': None, 'drums': None,
          # (the broken-chord ballad hands ring pedalled in the bass: their low end dipped, as in letters-to-the-morning)
          'eq': {'comp': {'low.freq': 220, 'low.gain': -2.5, 'peak2.freq': 100, 'peak2.gain': -2.0, 'peak2.q': 1.0}}},
    # singable heads (user 2026-10-09: like letters-to-the-morning): mostly steps, a breath at every phrase end
    # (blind round 6: the references' heads sit at G5-C6, the generated ones at A4-E5, quiet; one hook cell and its
    # sequence along the root motion in hook_seq of the tunes)
    melody={'register': ('Bb4', 'Eb6'), 'center': 'A5', 'peak': 'F6',
            'steps': {0: 0.12, 1: 0.58, 2: 0.22, 3: 0.05, 4: 0.03},
            'ends': {'breath': 0.36, 'down': 0.2, 'antic': 0.12, 'lh': 0.08, 'pickup': 0.06, 'tail': 0.18},
            'bridge_long': 0.85,
            'hook_seq': 0.55,
            # (the head grows from its cell: an A's half cadence states the hook cell's first bar before it lands in
            # half_cell of the phrases; a bar of one note or none outside the landings in `pads` of the bars at most -
            # blind round 7: heads padding with one-note bars every other bar)
            'half_cell': 0.6, 'pads': 0.125,
            # the bridge cell's return varied (DEVELOP_RHYTHM's names; blind round 7: two-note bridge bars, the same
            # bar four times in 8)
            'bridge_return': {'displace': 0.6, 'truncate': 0.15, 'same': 0.25},
            # (the A's period climbs a 6th+ to its peak: blind round 6, the generated heads moved inside a 5th / 6th)
            'contours': {'A': {'arch': (((0.0, -4), (0.65, 5), (1.0, -4)), 1.0),
                               'rise': (((0.0, -5), (0.72, 6), (1.0, 0)), 0.8),
                               'wave': (((0.0, 0), (0.3, -4), (0.62, 5), (1.0, -3)), 0.7),
                               'late': (((0.0, -3), (0.45, 1), (0.75, 6), (1.0, -2)), 0.6)}}},
    plan={'intro': 4, 'tag': 4, 'end': 2,
          'phrases': {'A': [('motif', None), ('half', 'fall'), ('develop', None), ('land', 'fall')],
                      'B': [('contrast', None), ('half', 'fall'), ('contrast', None), ('half', 'fall')]},
          'waltz_phrases': {'A': [('motif', None), ('half', 'fall'), ('develop', None), ('half', 'fall'),
                                  ('motif', None), ('line', 'rise'), ('answer', None), ('land', 'fall')]},
          'dyn': _JAZZ_DYN, 'dyn_out_peak': {'solo': ('mp', 'mf'), 'out': ('mf', 'mp')},
          'head': {'ornaments': {'trill': 1.0, 'turn': 1.2, 'mordent': 1.0,
                                                             'restrike': 1.4, 'crush': 0.8, 'roll': 1.0},
                   # the A sections state the theme (restated note for note): fewer fills / ornaments than the
                   # pianist's style, so the tune is recognisable when it comes back
                   'theme': {'fill': 0.12, 'embellish': 0.07, 'quick': 0.02},
                   # (the bridge's long notes - singable heads hold more - ring plain more often)
                   'bridge': {'embellish': 0.18},
                   # the phrase-to-phrase dynamics of the head / head out (perform.phrase_levels -> humanize.touch
                   # levels=): each 2-bar phrase moved by arc x its plan level over the part's mean, plus a step drawn
                   # per 4-bar phrase (velocity; never the same twice, a quiet one after a loud one); the loudest
                   # phrase of a part at the plan's level, the others up to depth below - endless r6:
                   # one level phrase after phrase read as "an endless monotone line"
                   'phrase_touch': {'arc': 30, 'steps': {-6: 1.0, -3: 1.0, 0: 0.5, 3: 1.0, 5: 0.7}, 'depth': 8}},
          # the solo's lines: 8ths across the bar lines, 16ths / triplets (runs, 4ths, triplet riffs) as rare peaks
          # (vocabulary weights); the arc builds to the climax at the solo's end and never deflates (no trill /
          # tremolo filler at the top)
          # (reharm: the share of the tunes whose last solo chorus and head out play one cadence another way, the
          # melody singing the substitute's colour - blind round 6: the charts identical across the choruses)
          'solo': {'arc': 'build', 'phrase_bars': 2, 'vel': (52, 112), 'seconds': 75, 'energy': 0.72, 'reharm': 0.75,
                   'energy_set': 0.1, 'weights': {'answer': 1.2, 'block': 1.2, 'riff': 0.6, 'run': 0.5,
                                                  'fourths': 0.5, 'octave_run': 0.6, 'tremolo': 0, 'trill': 0},
                   # the solo's SHAPE, drawn per tune (blind round 4: sparse -> 16ths -> loud end in every tune):
                   # name -> its soloist.ARCS arc, weight, move weights on top, the dynamic plans it allows,
                   # double: False = never double time; 'double': the share of tunes that go double time once (a
                   # burst of 16ths at a drawn place, perform.solo_arc)
                   # (solo_vel: the shape's own velocity range - a solo that leaves the peak to the head out
                   # starts softer)
                   'shapes': {'rise': {'weight': 0.3, 'arc': 'rise'},
                              'slow': {'weight': 0.14, 'arc': 'slow', 'dynamics': ('late', 'solo', 'shout'),
                                       'solo_vel': (50, 108)},
                              'early': {'weight': 0.15, 'arc': 'early', 'dynamics': ('solo', 'late')},
                              'sparse': {'weight': 0.14, 'arc': 'sparse', 'weights': {'riff': 1.2, 'run': 0.2},
                                         'dynamics': ('late', 'solo', 'shout'), 'solo_vel': (50, 108)},
                              'chords': {'weight': 0.13, 'arc': 'chords', 'dynamics': ('solo', 'late', 'shout')},
                              'trade': {'weight': 0.05, 'arc': 'trade4', 'double': False,
                                        'dynamics': ('late', 'solo', 'shout'), 'solo_vel': (50, 108)}},
                   'double': 0.36,
                   # how the solo opens (soloist.OPENINGS) and how many literal quotes of the hook it may play (the
                   # rest paraphrased: displaced, re-fitted, a new ending), drawn per tune - blind round 7: every
                   # solo opened by quoting the head, the head verbatim in the solo
                   'opening': {'motif': 0.25, 'fragment': 0.4, 'line': 0.35}, 'quotes': {0: 0.6, 1: 0.3, 2: 0.1},
                   # where a reharm sounds: the last solo chorus and the head out alike, or the head out alone (blind
                   # round 7: the last chorus's reharm carried into the head out in every tune)
                   'reharm_in': {'both': 0.55, 'out': 0.45}},
          'out': {'paraphrase': 0.25, 'touch_drop': 0, 'last': (-1, -3, 0.5)},
          # the whole piece's dynamic plan, one drawn per tune (composer: tune.dynamics) - a distribution, never one
          # fixed plan (blind round 2 -> 3: the shout head-out in every tune read as a formula): the peak mostly in
          # the solo's last chorus (60-75 % into the piece), the solo at or above the head (solo_vel: the soloist's
          # velocity range), the head out at the head's level (out: its touch lift over the head's; blind round 6:
          # the form faded - the head out 2 LU under the head, the tag / ending 6-12 under the piece); a shout (block
          # chords, loud) rarely and only for the 2 bars around the head out's lifted top note (shout: the velocity
          # of its peak note) - every other plan peaks in the solo's last 8-16 bars ('late': at its very end)
          'dynamics': {'solo': {'weight': 0.5, 'solo_vel': (50, 112), 'out': 0},
                       'shout': {'weight': 0.08, 'solo_vel': (50, 110), 'out': 0, 'shout': 118, 'out_peak': True},
                       'late': {'weight': 0.23, 'solo_vel': (50, 112), 'out': 1},
                       'calm': {'weight': 0.15, 'solo_vel': (48, 112), 'out': -2}}},
)

_TRIO_FEELS = copy.deepcopy(_PIANO_FEELS)
for _f in _TRIO_FEELS.values():               # the bassist has the roots: the left hand plays guide tones / rootless
    _f['lh'] = 'guide' if _f['lh'] is not None else None
    _f.pop('lh_plan', None)                   # (the bassist owns the low register: the guide-tone hand throughout)
_TRIO_FEELS['bossa'].update(bass_vel=(66, 92))       # the upright plays the bossa line (Meatbass levels)
_TRIO_FEELS['bossa']['comp'].update(vel=50)

JAZZ_TRIO = JAZZ_PIANO.but(
    name='jazz-trio',
    description='piano trio: the jazz-piano tune and pianist plus an upright bass (straight two / push lines, a walk '
                'when swung) and brushes - the perry-street-rain setup',
    feels=_TRIO_FEELS,
    # the trio's bassist owns the low register: no trading 4s with the left hand
    plan=dict(JAZZ_PIANO.plan, solo=dict(JAZZ_PIANO.plan['solo'], shapes={
        k: v for k, v in JAZZ_PIANO.plan['solo']['shapes'].items() if v['arc'] != 'trade4'})),
    # the smooth grand (user 2026-10-10: "a verry smooth piano, i think the normal ones maybe simply to dry"):
    # jazz_trio voicing='smooth' - solo_piano's softened grand, a wetter salon with a pre-delayed rich plate
    band={'preset': 'jazz_trio', 'options': {'voicing': 'smooth'}, 'without': (), 'master_gain': 9.0,
          'profile': 'jazz', 'loudness': (-18.0, -12.0),
          'bass': {'straight': True, 'feel': 'two', 'vel': 84}, 'drums': {'straight': True, 'style': 'ballad',
                                                                          'vel': 0.6},
          'trims': {'piano': -2.5}},
)

# ------------------------------------------------------------------------------------------------ piano genres
# Through-composed solo piano (plan['perform'] = 'piano': perform.build_piano plays plan['sections'] with the
# romantic pianist - romantic.Score from the composed notes, a broken-chord left hand from pianist.FIGURES per
# section, written dynamics per section, phrase rubato, ritardandi, a fermata at the climax). The composer is the
# same; what differs is data: the chord vocabulary, the melody's cells / steps / phrase plans, the arrangement.

_SING_STEPS = {0: 0.1, 1: 0.64, 2: 0.18, 3: 0.05, 4: 0.03}
"""A singable line: mostly steps, few thirds, a leap now and then (genres' melody['steps'], composer._contour)."""
_SING_ENDS = {'breath': 0.55, 'down': 0.25, 'antic': 0.15, 'lh': 0.05}
"""Every phrase end breathes: the landing held, then half a bar of silence (melody['ends'], PHRASE_ENDS' kinds)."""
_SING_PHRASES = {'A': [('motif', None), ('half', 'fall'), ('develop', None), ('land', 'fall')],
                 'B': [('contrast', None), ('half', 'fall'), ('contrast', None), ('half', 'fall')],
                 'C': [('motif', None), ('line', 'rise'), ('develop', None), ('half', 'fall')]}
"""Singable periods: a 4-bar question (the hook + a landing), a 4-bar answer (the hook developed + the cadence) - a
rest at every phrase end (plan['phrases'] over composer.PLANS)."""

NEW_AGE_HARMONY = {
    'blocks': {
        'major': {
            'open': {'I_V3_vi_IV': 'IM V@3 VIm IVM', 'I_iii_IV_V': 'IM IIIm IVM V',
                     'I_IV_vi_V': 'IM IVM VIm Vsus4:0.5 V:0.5', 'I_V_vi_iii': 'IM V VIm IIIm',
                     'I_I3_IV_iv': 'IM I@3 IVM IVm6', 'lament': 'IM V@3 VIm I@5',
                     # (the learned generator's blind round 2: colour chords that never resolve, 17-27 symbols -
                     # applied dominants that go where they point, a descending bass)
                     'I_I7_IV': 'IM I7@3 IVM IVm6', 'I_V3_vi_I7': 'IM V@3 VIm I7@7'},
            'turn': {'IV_I3_ii_V': 'IVM I@3 IIm7 V', 'vi_iii_IV_V': 'VIm IIIm IIm7 V',
                     'ii_vi_IV_V': 'IIm VIm IVM V', 'vi_V2_V': 'VIm II7@3 IVM Vsus4:0.5 V:0.5',
                     'IV_III7_vi_V': 'IVM III7@3 VIm IVM:0.5 V:0.5',
                     'iii_VI7_ii_V': 'IIIm VI7 IIm7 V', 'IV_vii_III7_vi': 'IVM VIIm7b5:0.5 III7:0.5 VIm IIm7:0.5 V:0.5'},
            'final': {'IV_V_I': 'IVM Vsus4:0.5 V:0.5 IM:2', 'ii_V_I': 'IIm V IM:2', 'iv_I': 'IVM IVm6 IM:2',
                      'IV_I5_V_I': 'IVM I@5 V IM'},
            'hook': {'axis': 'VIm IVM IM V VIm IVM IIm Vsus4:0.5 V:0.5',
                     'IV_V_iii_vi': 'IVM V IIIm VIm IVM V@3 IVm6 V',
                     'IV_I3': 'IVM I@3 VIm V IVM V@3 IM:2',
                     'vi_V3_IV': 'VIm V@3 IVM IIIm IIm IM@3 IVM V',
                     'IV_III7': 'IVM V III7@3 VIm IVM I@3 IIm7 V',
                     # (round r3: two pieces in one key drew one chorus chart - a wider bank, its halves apart)
                     'IV_iv_vi': 'IVM IVm6 IM@3 VIm IIm7 V@3 VIm V',
                     'ii_iii_IV': 'IIm7 IIIm7 IVM V VIm IIIm IVmaj7 IM',
                     'vi_ii_V_I': 'VIm IIm7 V IM@3 IVM II7@3 IVm6 V',
                     'IV_V_VI7_ii': 'IVM V VIm VI7@3 IIm7 V IM@3 IVM', 'I7_IV_iv': 'IM I7@3 IVM IVm6 IIIm VI7 IIm7 V'},
            'build': {'relative': 'VIm IVM IIm III7 VIm IVM bVIIM Vsus4:0.5 V:0.5',
                      'vi_iii': 'VIm IIIm IVM IM@3 IIm IVM Vsus4 V',
                      'climb': 'VIm V@3 IVM IIIm IIm I@3 IVM V',
                      'bVII': 'VIm IIIm IVM II7@3 VIm IVM bVIIM V',
                      'iv_bVI': 'VIm IVM IVm6 bVIM IIm7 I@5 Vsus4 V', 'pedal': 'VIm IIIm IVM IM@3 IIm7 IM@5 II7@3 V'},
        },
        'minor': {
            'open': {'i_VI_III_VII': 'Im bVIM bIIIM bVII', 'i_iv_VII_III': 'Im IVm bVII bIIIM',
                     'i_VI_iv_V': 'Im bVIM IVm Vsus4:0.5 V:0.5', 'i_VII3_VI_V': 'Im bVII@3 bVIM V',
                     'i_V3_VII_IV3': 'Im V@3 bVIIM IVM@3', 'i_i7_VI_V': 'Im Im7@7 bVIM V'},
            'turn': {'VI_VII_iv_V': 'bVIM bVII IVm7 V', 'iv_VI_V': 'IVm bVIM Vsus4 V',
                     'iio_V_VI_V': 'IIm7b5 V bVIM V7', 'VI_N_V': 'bVIM bIIM V Vsus4:0.5 V:0.5'},
            'final': {'VI_VII_i': 'bVIM bVII Im:2', 'iv_V_i': 'IVm Vsus4:0.5 V:0.5 Im:2', 'VI_V_i': 'bVIM V Im:2'},
            'hook': {'VI_VII_III': 'bVIM bVII bIIIM Im bVIM bVII IVm Vsus4:0.5 V:0.5',
                     'III_VII': 'bIIIM bVII bVIM bIIIM IVm bVIM Vsus4 V',
                     'iv_VII_III_VI': 'IVm7 bVII bIIIM bVIM IIm7b5 V@3 Im V',
                     'VI_III_iv_V': 'bVIM bIIIM IVm7 V@3 bVIM bVII IVm7 V',
                     'iv_i_ii_V': 'IVm7 Im@3 IIm7b5 V bVIM bIIIM bVII@3 V'},
            'build': {'iv_climb': 'IVm bVII bIIIM bVIM IIø V Im V',
                      'relative': 'bIIIM bVII IVm Im bVIM bVII Vsus4 V',
                      'lament': 'Im bVIIM bVIM V IVm Im@3 bIIM V'},
        },
    },
    # pop colours: plain triads first, add9 / maj7 as the tender colour (the mood's 'colour' scales the add9s)
    # (the learned generator's blind round 2 and new-age r8: add9 / sus4 in ~60 % of the chord labels - plain triads and
    # 7ths first, add9 rarer)
    'colours': {'M': {'': 2.4, 'add9': 0.5, 'maj7': 0.8, '6': 0.25}, 'M_tonic': {'': 2.2, 'add9': 0.8, 'maj7': 0.4},
                'm': {'m': 1.2, 'm7': 1.5, 'madd9': 0.2}, 'm_tonic': {'m': 1.6, 'm7': 0.8, 'madd9': 0.3},
                '7_major': {'7': 1.0, '7sus4': 0.4}, '7_minor': {'7': 1.0}, '7_blues': {'7': 1.0},
                '7_sub': {'7': 1.0}, 'ø': {'m7b5': 1.0}, 'o': {'dim7': 1.0}, 'sus': {'7sus4': 1.0, 'sus4': 1.0}},
    # (the learned generator's blind round 2: one 4-bar vi-IV-I-Vsus4 frame in every piece - a tonic pedal, a
    # descending bass, a plagal swing and an open ii-V too)
    'intros': {'major': {'I_IV': ('Iadd9 IVmaj7 VIm7 Vsus4:0.5 V:0.5', 0.6), 'IV_I': ('IVmaj7 Iadd9 IVmaj7 Vsus4', 0.5),
                         'vi_IV': ('VIm7 IVmaj7 Iadd9 Vsus4', 0.4), 'pedal': ('I IVmaj7@5 I IVmaj7@5', 0.6),
                         'descend': ('I V@3 VIm7 I@5', 0.5), 'ii_V': ('IIm7 V7@3 IIm7 V7sus4', 0.4)},
               'minor': {'i_VI': ('Im bVImaj7 bIIIadd9 Vsus4', 0.7), 'i_iv': ('Im7 IVm7 bVImaj7 Vsus4', 0.5),
                         'pedal': ('Im IVm7@5 Im IVm7@5', 0.6), 'lament': ('Im V@3 bVIImaj7 IVm7@3', 0.4)}},
    'intro_tonic': (),
    # (the set's endings spread: HUMAN_FEEDBACK 2026-10-12 - add9 in most pieces)
    'endings': {'major': {'add9': 1.0, '': 0.8, 'maj9': 0.5, '6': 0.4, 'maj7': 0.4},
                'minor': {'madd9': 1.0, 'm': 0.8, 'm9': 0.5, 'm7': 0.3}},
    # how the coda reaches the end chord (blind round N0: every coda 'Vsus4 - iv6 - I'), what it plays (the intro's
    # vamp again in every piece) and its line / the intro's (two- or three-note scraps): the hook's head and its echo
    # (the learned generator's blind round 2: 'IV - ivm6 - I(add9)' in most codas - the minor plagal rarer)
    'tag_approach': {'plagal': 0.35, 'sus': 0.5, 'IV': 0.4, 'ii': 0.35, 'IV_iv': 0.3, 'vi': 0.35},
    # the dominant's sus4 chords a tune keeps, the others V7 / ii - V / IV - V (composer._sus_budget; round r10:
    # every phrase of a minor piece closing Vsus4 - V)
    'sus_budget': {0: 0.15, 1: 0.35, 2: 0.3, 3: 0.2},
    'sus_swap': {'7': 0.45, 'ii': 0.35, 'IV': 0.2},
    # (round r5: the coda's chords = the intro's in most pieces - the reprise rarer)
    'tag_frames': {'reprise': 0.15, 'vamp': 0.4, 'turnaround': 0.45},
    # the coda's approach into the end chord takes a whole bar (round r2: 'sus4 IV iv6' crammed into one bar)
    'tag_span': 1.0,
    # the climax's own harmony (round r3: the climax = A1's chord chart cell for cell; the references put the theme
    # over new chords - rain: Cmaj7 / Am7 / the Neapolitan, the waltz: C7/E into Fm7, Abm6): per source degree the
    # substitutes perform._reharm draws among those the melody sings over
    'reharm': {
        'major': {'IM': {'VIm7': 1.0, 'IIIm7': 0.5, 'I@3': 0.3, 'IVmaj7@5': 0.3},
                  'IIm': {'IVmaj7': 1.0, 'II7@3': 0.6},
                  'IIIm': {'III7@3': 0.8, 'Imaj7': 0.6, 'V@3': 0.5},
                  'IVM': {'IIm7': 1.0, 'IVm6': 0.5, 'VIm7': 0.4},
                  'VM': {'V@3': 0.8, 'IIIm7': 0.6, 'V7': 0.5},
                  'VIm': {'IVmaj7': 1.0, 'III7@3': 0.8, 'I@3': 0.4}},
        'minor': {'Im': {'bVImaj7': 1.0, 'Im@3': 0.6, 'bIIImaj7': 0.6},
                  'bIIIM': {'Im7': 0.8, 'bIII@3': 0.6, 'IVm7': 0.3},
                  'IVm': {'bVImaj7': 1.0, 'IIm7b5': 0.8, 'IVm6': 0.6},
                  'VM': {'V@3': 0.8, 'V7': 0.8},
                  'bVIM': {'IVm7': 1.0, 'IIm7b5': 0.5, 'Im7': 0.4},
                  'bVIIM': {'bVII@3': 0.6, 'IIm7b5': 0.5, 'bIIImaj7': 0.4}}},
    # (round r4: the augmented line = two long notes; r5: intro / interlude a held note + a pickup at the same places
    # in every piece - the hook's head as a cell sequenced bar by bar joins)
    'intro_lines': {'head': 0.45, 'answer': 0.3, 'fragment': 0.3},
    # (round r4: a coda looping the head's 2-bar cell twice - 5, 6, 5, 6 - read as no ending)
    # (round r5: the coda in whole notes - the augmented line rarer, the head's cell sequenced joins)
    'tag_lines': {'head': 0.35, 'augment': 0.15, 'answer': 0.3, 'fragment': 0.2},
}

_NA_STEPS = {0: 0.03, 1: 0.68, 2: 0.19, 3: 0.06, 4: 0.04}
"""new-age's steps: _SING_STEPS with fewer repeated notes (blind round N0: 14 % repeated-pitch steps, the references
0-2 %; the repeated-note pickups)."""
_NA_ENDS = {'breath': 0.35, 'down': 0.3, 'antic': 0.15, 'pickup': 0.2}
"""new-age's phrase ends: fewer whole-bar breaths, a pickup into the next phrase now and then (blind round N0: a held
note or an empty bar closing every 4-bar phrase; right hand quiet a beat+ 38 % of the time, the references 25-30 %)."""
_NA_PHRASES = dict(_SING_PHRASES,
                   B=[('contrast', None), ('line', 'rise'), ('contrast', None), ('half', 'fall')])
"""new-age's periods: the A a question and an answer, the B one breath in 8 bars - its antecedent runs on in a line
(the references' right hand is quiet a beat+ 25-30 % of the time, the generated 35 % with a landing every 4 bars)."""
_NA_WALTZ_PHRASES = {'A': [('motif', None), ('line', 'arch'), ('develop', None), ('half', 'fall'), ('answer', None),
                           ('line', 'rise'), ('line', 'arch'), ('land', 'fall')],
                     'C': [('motif', None), ('line', 'rise'), ('line', 'arch'), ('half', 'fall'), ('develop', None),
                           ('line', 'rise'), ('line', 'arch'), ('land', 'fall')]}
"""The new-age waltz's periods (two 3/4 bars per unit, 16 bars per part): the hook stated and developed once per
period, then lines (composer.WALTZ_PLANS stated it four times per A: the hook in every other phrase)."""
_NA_FIGURES = {'intro': {'flow': 1.0, 'lilt': 1.0}, 'calm': {'rock': 1.0, 'lilt': 1.0, 'quart': 0.4},
               'flow': {'flow': 1.0, 'rock': 1.0, 'lilt': 0.7, 'color': 0.5}, 'thin': {'quart': 1.0, 'open': 1.0},
               # the chorus's own hand (blind round N0: the references change texture there - tenths, a pulse)
               'chorus': {'tenths': 1.0, 'flow': 0.7, 'pulse': 0.6, 'color': 0.5},
               'build': {'flow': 1.0, 'color': 0.6, 'rock': 0.4}, 'big': {'big': 1.0, 'sweep': 0.35},
               'rest': {'half': 1.0, 'open': 0.4, 'ring': 0.3}, 'into': {'up': 1.0, 'flow': 0.5}, 'end': 'roll'}
"""The broken-chord hand per section (pianist.FIGURES, drawn per bar, never twice running): 'rest' under the
melody's breaths, 'into' the bar before a peak section (both drawn: audit 2026-10-13), 'end' the last chord."""
_NA_WALTZ_FIGURES = {'intro': {'waltz_arp': 1.0, 'barcarolle': 1.0},
                     'calm': {'barcarolle': 1.0, 'waltz_open': 0.7, 'waltz_held': 0.4},
                     'flow': {'waltz_arp': 1.0, 'barcarolle': 0.8, 'waltz2': 0.6},
                     'thin': {'waltz_held': 1.0, 'waltz_open': 0.8},
                     'chorus': {'waltz_open': 1.0, 'waltz2': 0.8, 'waltz_step': 0.6},
                     'build': {'waltz_arp': 1.0, 'barcarolle': 0.8, 'waltz_step': 0.6},
                     'big': {'waltz_big': 1.0, 'waltz_arp': 0.5}, 'rest': {'waltz_held': 1.0, 'waltz_open': 0.4},
                     'into': {'barcarolle': 1.0, 'waltz_arp': 0.6}, 'end': 'roll'}
"""The new-age waltz's hand (songs/pro-newage-waltz: a rocking barcarolle held under the breaths, an arpeggio over
the bar, the open hand in the middle strain): the 3/4 figures of pianist.FIGURES per section."""
_NA_BLOOM = {
    # (HUMAN_FEEDBACK 2026-10-15: "they lack a blossoming where the tempo gets faster and more happens; they just
    # ripple along; bass and lead always very clearly separated; nothing flowing like Für Elise" - measured: every
    # climax slower than A1 (0.88-0.94), the right hand 0.6-1.7 notes a beat everywhere, a hard split at E4 / G4)
    'at': {'build': 1.0, 'B1': 0.35, 'climax': 0.3},      # the section that blooms, drawn per piece
    'push': {1.04: 0.6, 1.06: 1.0, 1.08: 0.8, 1.1: 0.4},  # the tempo it pushes to (x the section's own)
    'reach': {0.4: 0.6, 0.5: 1.0, 0.65: 0.6},             # ... reached at that share of the section, then held
    'carry': {0.5: 0.6, 0.75: 1.0, 1.0: 0.6},             # the share of the push the climax keeps (broad at its peak)
    'rit': {0.93: 0.5, 0.96: 1.0, 0.98: 0.5},             # the bloom's own breath at its end (a section's: 0.8-0.9)
    'grid': {0.25: 1.0, 0.3333: 0.5},                     # the hand-off fills' note grid in the bloom (16ths / 3lets)
    # the hand-to-hand figure on a held melody note (the left hand climbs, the right carries it on into the next
    # note): its chance per held bar in the bloom / the other part sections by part letter (never into a phrase end)
    'handoff': {'bloom': 0.85, 'A': 0.12, 'B': 0.2, 'C': 0.25},
    'link': 0.5,                  # the bloom's last bar runs on into the next section (its phrase-end breath goes)
    'lift': 12,                   # the left hand's top may rise this far over its cap: to a whole step under the tune
    # the left hand's figures per meter: in the bloom two stages - triplets / 8ths until 'reach', then 16ths -, one
    # figure per 2-bar unit (the student's blind judge, 2026-10-15: a climax hand toggling 16ths / 8ths strictly bar
    # by bar reads as a machine; the figure is shaped by the phrase); the hand-off bars in the bloom and elsewhere
    'figures': {4: [{'trip12': 1.0, 'flow': 0.5}, {'span16': 1.0, 'wave16': 0.8}],
                3: [{'waltz_arp': 1.0, 'barcarolle': 0.5}, {'waltz_span': 1.0, 'waltz_wave': 0.8}]},
    # the right hand in the bloom: under a melody note held a beat or more, the chord's tones below it in the grid
    # (a woven figure under the tune, the melody note ringing on in the pedal), x this velocity
    'weave': 0.7,
    'bloom_hand': {4: {'ring16': 1.0, 'up16': 1.0, 'ring': 0.4, 'up': 0.4},
                   3: {'waltz_hand16': 1.0, 'waltz_up': 0.8, 'waltz_hand': 0.5}},
    'hand': {4: {'ring': 1.0, 'up': 1.0}, 3: {'waltz_hand': 1.0, 'waltz_up': 1.0}},
}
"""The bloom of a new-age piece (perform._bloom / _handoffs): one section per piece where the motion doubles (the
left hand in 16ths / triplets over two and a half octaves, rising to the melody; the right hand carrying the figure
on over its held notes), the tempo pushes forward (an accelerando, held, a light breath at its end, the climax keeping
part of it - broad only at its peak), and the hand-to-hand figure now and then elsewhere. Drawn per piece from its
own seed (not in the arrangement record: a texture decision, like the left hand's figures)."""
BLOOM_KEYS = frozenset(_NA_BLOOM)

NEW_AGE_PIANO = Genre(
    name='new-age-piano',
    description='new-age solo piano (letters-to-the-morning): a singable theme and a chorus hook over flowing '
                'broken-chord figures, pop progressions with tender colour chords; intro, theme twice, the hook, an '
                'interlude, the build, one climax (the hook in chords), the theme soft, a coda - rubato, ritardandi',
    forms={'verse': 1},
    # (HUMAN_FEEDBACK 2026-10-12, "nicht sehr abwechslungsreich": a set must spread its moods / feels / meters /
    # tempi - the waltz (3/4, songs/pro-newage-waltz) joins three moods, the tempo ranges widened)
    moods={'morning': {'feels': {'flowing': 3, 'gentle': 1, 'waltz': 1.5}, 'modes': {'major': 1},
                       'keys': {'major': ['Ab', 'Db', 'Eb', 'F', 'Bb', 'C']}, 'tempo': 0, 'colour': 1.0,
                       'tritone': 0.0, 'energy': 0.5},
           'longing': {'feels': {'gentle': 2, 'flowing': 2, 'waltz': 1.5}, 'modes': {'minor': 2, 'major': 1},
                       'keys': {'major': ['Db', 'Ab', 'Gb', 'E'], 'minor': ['F', 'C', 'Bb', 'G', 'D', 'A']},
                       'tempo': -2, 'colour': 1.2, 'tritone': 0.0, 'energy': 0.3},
           'hopeful': {'feels': {'flowing': 2, 'bright': 2}, 'modes': {'major': 1},
                       'keys': {'major': ['C', 'G', 'D', 'F', 'A', 'E']}, 'tempo': 2, 'colour': 0.9,
                       'tritone': 0.0, 'energy': 0.8},
           'rain': {'feels': {'gentle': 3, 'flowing': 1, 'waltz': 1}, 'modes': {'minor': 1},
                    'keys': {'minor': ['E', 'A', 'D', 'B', 'F#', 'C#']}, 'tempo': -3, 'colour': 1.1,
                    'tritone': 0.0, 'energy': 0.15}},
    feels={'flowing': {'tempo': (68, 82), 'meter': 4, 'cells': 'na', 'style': 'ballad', 'lh': 'broken',
                       'swing': False, 'rubato': 0.05, 'touch': (52, 100), 'energy': 0.55, 'figures': _NA_FIGURES,
                       'body': 'lyrical'},
           'gentle': {'tempo': (58, 70), 'meter': 4, 'cells': 'na', 'style': 'ballad', 'lh': 'broken',
                      'swing': False, 'rubato': 0.06, 'touch': (48, 96), 'energy': 0.2, 'body': 'calm',
                      'figures': dict(_NA_FIGURES, flow={'rock': 1.0, 'lilt': 1.0, 'flow': 0.6},
                                      calm={'lilt': 1.0, 'quart': 0.8, 'open': 0.4})},
           'bright': {'tempo': (82, 96), 'meter': 4, 'cells': 'na', 'style': 'ballad', 'lh': 'broken',
                      'swing': False, 'rubato': 0.04, 'touch': (56, 102), 'energy': 0.85, 'body': 'lyrical',
                      'figures': dict(_NA_FIGURES, calm={'rock': 1.0, 'flow': 0.8, 'lilt': 0.5})},
           # the new-age waltz (songs/pro-newage-waltz, 96 BPM): the form doubled into 3/4 bars, the 3/4 song cells
           'waltz': {'tempo': (84, 104), 'meter': 3, 'cells': 'na3', 'style': 'ballad', 'lh': 'broken',
                     'swing': False, 'rubato': 0.06, 'touch': (50, 98), 'energy': 0.4, 'body': 'waltz',
                     'figures': _NA_WALTZ_FIGURES}},
    # the solo_piano preset as letters-to-the-morning mixed it: the pedalled broken chords' low mids dipped on the
    # left hand, the master's pedalled bass down a little and air above the presence band (no 2-5 kHz lift)
    band={'preset': 'solo_piano', 'master_gain': 6.5, 'profile': 'piano', 'loudness': (-23.0, -15.0), 'bass': None,
          'drums': None, 'eq': {'comp': {'low.freq': 220, 'low.gain': -4.0, 'peak1.freq': 1400, 'peak1.gain': -2.0,
                                         'peak1.q': 0.8, 'peak2.freq': 100, 'peak2.gain': -2.5, 'peak2.q': 1.0}},
          'master_eq': {'peak2.freq': 100, 'peak2.gain': -2.0, 'peak2.q': 1.0, 'peak3.freq': 3200,
                        'peak3.gain': -1.0, 'peak3.q': 0.8, 'high.freq': 9000, 'high.gain': 2.5},
          'breath': {'quiet1': 0.25, 'att_cv4': 0.08}},
    # the arrangement draws its grid, its climax and its returns (blind round N0: one grid 4|8|8|8|4|8|8|8|5 in every
    # piece, the climax = B1 louder, A4 = A2 closing on the tonic; perform.ARRANGE_KEYS): A2 may run a bar over, the
    # interlude 2 or 4 bars, A3 a half return, the build 6 or 8 bars, the climax the chorus lifted / the theme an
    # octave up / the chorus a step up, held a bar longer; the last A high then home, closing deceptively; the final
    # chord resolves the last melody note (end_top)
    plan={'perform': 'piano', 'intro': 4, 'tag': 4, 'end': 1, 'phrases': _SING_PHRASES, 'end_top': 'line',
          'waltz_phrases': _NA_WALTZ_PHRASES, 'bloom': _NA_BLOOM,
          # the period plan per part kind, drawn per tune (composer.compose; audit 2026-10-13: one plan per kind in
          # every piece - the A always peaking in its third phrase, the chorus breathing every 4 bars)
          'phrase_variants': {
              'common': {'A': [(_SING_PHRASES['A'], 1.0),
                               ([('motif', None), ('line', 'arch'), ('develop', None), ('land', 'fall')], 0.6),
                               ([('motif', None), ('half', 'fall'), ('answer', None), ('land', 'fall')], 0.4),
                               ([('motif', None), ('develop', None), ('line', 'rise'), ('land', 'fall')], 0.4)],
                         'B': [(_SING_PHRASES['B'], 1.0), (_NA_PHRASES['B'], 0.8),
                               ([('contrast', None), ('line', 'arch'), ('line', 'rise'), ('half', 'fall')], 0.4)],
                         'C': [(_SING_PHRASES['C'], 1.0),
                               ([('motif', None), ('line', 'rise'), ('develop', None), ('half', 'fall')], 0.6),
                               ([('motif', None), ('develop', None), ('line', 'rise'), ('half', 'fall')], 0.5)]},
              'waltz': {'A': [(_NA_WALTZ_PHRASES['A'], 1.0),
                              ([('motif', None), ('line', 'arch'), ('develop', None), ('half', 'fall'),
                                ('motif', None), ('line', 'rise'), ('answer', None), ('land', 'fall')], 0.6)],
                        'C': [(_NA_WALTZ_PHRASES['C'], 1.0),
                              ([('motif', None), ('line', 'arch'), ('develop', None), ('half', 'fall'),
                                ('line', 'arch'), ('line', 'rise'), ('line', 'arch'), ('land', 'fall')], 0.6)]}},
          # the pianist's own per-piece choices (arrangement.PLAY_KEYS, recorded; audit 2026-10-13: the same rubato,
          # breath, inner voices, top velocity, left-hand level, pedal and last chord in every piece)
          'play': {'rubato': {0.7: 1.0, 1.0: 1.0, 1.4: 0.8}, 'inhale': {0: 0.25, 1.0: 0.3, 2.0: 0.45},
                   'lilt': {0.015: 0.8, 0.03: 1.0, 0.045: 0.8}, 'breath': {0.25: 1.0, 0.35: 1.0, 0.5: 0.8},
                   'push': {10: 0.8, 18: 1.0, 28: 0.8}, 'inner': {0.72: 1.0, 0.78: 1.0, 0.84: 1.0},
                   'cap': {98: 0.7, 106: 1.0, 114: 0.7}, 'lh_vel': {37: 0.8, 41: 1.0, 46: 0.8},
                   'pedal': {45: 0.8, 60: 1.0, 90: 0.8}, 'end_dyn': {'pp': 1.0, 'p': 0.6},
                   'end_roll': {60: 0.8, 110: 1.0, 170: 0.8}, 'end_hold': {2: 0.8, 3: 1.0, 4: 0.7}},
          'ornaments': {'turn': 0.45, 'mordent': 0.2},
          'swell': {0: 0.3, 1: 0.6, 2: 0.1},   # a hairpin per phrase, levels up (round r3: one mark per section)
          'candidate_tries': 2,      # best-of-8 from up to 16 seeds (the arc check rejected ~40 %)
          # the tune's touch window moved (lo, hi): its own loudness budget (round r2: ~17 LU in every piece)
          'touch_span': {(0, 0): 1.0, (-6, 0): 0.6, (5, -4): 0.6, (-3, 4): 0.5},
          'max_hold': 3.5,           # a melody note rings 3.5 beats at most (round r1: 4.5-7 beat holds, refs none)
          'end_styles': {'roll': 1.0, 'spread': 0.6},
          'form_bars': True,         # (the bar counts below are form bars: a waltz plays two 3/4 bars for each)
          # the set-level draws (composer.set_draws; HUMAN_FEEDBACK 2026-10-12: every sample gentle / verse / minor,
          # its climax on C6 at ~90 %): per set slot, never the slot before's, pinned for the slot's best-of-N - the
          # arrangement's layout (song: the theme twice, the hook, an interlude, the build, the climax, the theme soft;
          # chorus: the hook right after the first theme, the climax its last statement; return: the climax, then an
          # interlude and the theme's return, ternary like the waltz reference), the climax kind (perform._arrange)
          # and the melody's register (semitones: the climax pitch)
          'set': {'layout': {'song': 1.0, 'chorus': 0.7, 'return': 0.6},
                  # (the learned generator's blind round 2: the climax built from earlier bars - 'grow' derives it
                  # from the hook, sequenced up to a new peak)
                  'climax': {'grow': 1.2, 'theme': 0.6, 'climb': 0.7, 'lift': 0.4, 'step': 0.1},
                  'shift': {-3: 0.5, -2: 0.7, -1: 0.6, 0: 0.7, 1: 0.7, 2: 0.7, 3: 0.5},
                  # the chorus's chord block per mode (round r10: one hook chart, I - I7/3 - IV - iv6 - iii - VI7 -
                  # ii7 - V, in three of four pieces - harmony['blocks'] are drawn uniformly per tune)
                  'hook': {'major': {'axis': 1.0, 'IV_V_iii_vi': 1.0, 'IV_I3': 0.8, 'vi_V3_IV': 1.0, 'IV_III7': 0.8,
                                     'IV_iv_vi': 0.8, 'ii_iii_IV': 1.0, 'vi_ii_V_I': 0.8, 'IV_V_VI7_ii': 0.6,
                                     'I7_IV_iv': 0.4},
                           'minor': {'VI_VII_III': 1.0, 'III_VII': 0.8, 'iv_VII_III_VI': 1.0, 'VI_III_iv_V': 1.0,
                                     'iv_i_ii_V': 0.8}},
                  # the theme's and the build's blocks too (audit 2026-10-13: uniform per tune, a set could repeat)
                  'open': {'major': {'I_V3_vi_IV': 1.0, 'I_iii_IV_V': 1.0, 'I_IV_vi_V': 0.8, 'I_V_vi_iii': 1.0,
                                     'I_I3_IV_iv': 0.7, 'lament': 0.8, 'I_I7_IV': 0.6, 'I_V3_vi_I7': 0.7},
                           'minor': {'i_VI_III_VII': 1.0, 'i_iv_VII_III': 1.0, 'i_VI_iv_V': 0.8, 'i_VII3_VI_V': 1.0,
                                     'i_V3_VII_IV3': 0.8, 'i_i7_VI_V': 0.7}},
                  'build': {'major': {'relative': 1.0, 'vi_iii': 1.0, 'climb': 1.0, 'bVII': 0.8, 'iv_bVI': 0.7,
                                      'pedal': 0.7},
                            'minor': {'iv_climb': 1.0, 'relative': 1.0, 'lament': 0.8}}},
          # how many slots back a set draw may not repeat (composer.set_draws; default 1: the slot before)
          'set_memory': {'hook': 4, 'open': 3, 'build': 2},
          # a waltz's later bar of a held chord (perform._moving_bass; blind round 2: two bars per chord, four-bar
          # single-chord stretches - a one-bar harmonic rhythm mostly)
          'moves': {'hold': 0.12, 'bass': 0.25, 'sub': 0.4, 'ped': 0.3},
          # a section as high as the climax's peak comes down an octave unless its line would drop under E4 (64;
          # round r9: the chorus an octave down in the left hand's register) - then only its peak notes (_under_peak)
          'peak_floor': 64,
          # the broken-chord hand strikes one inner tone twice running at most (pianist.figure; rounds r8 / r10:
          # E3 E3 E3 - the capped ladder folding two steps onto one key)
          'lh': {'repeats': 2},
          # the climax never rocks between two chords (X Y X Y: the third takes a substitute - perform._unswing)
          'unswing': True,
          # (the learned generator's blind round 2, all five judges: one frame in every piece - a 4-bar intro, the
          # interlude pasted from it, a 4-bar coda, the same loudness arc; and no key plan, the returns copied note for
          # note: the frames' lengths and presence, every section's dynamics, a return's development per 2-bar unit
          # ('vary') and a section's key ('key') are drawn per piece)
          'sections': [
              {'name': 'intro', 'frame': 'intro', 'dyn': {('pp', 'p'): 1.0, 'p': 0.6, ('p', 'mp'): 0.4},
               'figures': {'intro': 1.0, 'calm': 0.4}, 'chance': 0.85, 'bars': {((0, 4),): 0.55, ((2, 4),): 0.45},
               'lh_only': {0: 0.6, 1: 0.3, 2: 0.1}, 'rit': {0.8: 0.3, 0.85: 0.4, 0.9: 0.3}},
              {'name': 'A1', 'part': 'A1', 'dyn': {'p': 1.0, ('p', 'mp'): 0.6, ('pp', 'p'): 0.3},
               'figures': {'calm': 1.0, 'flow': 0.4}, 'fill': {0: 0.5, 1: 0.5}, 'turn': {0: 0.6, 1: 0.4}},
              {'name': 'A2', 'part': 'A2', 'dyn': {('p', 'mp'): 1.0, 'mp': 0.5, ('mp', 'p'): 0.4},
               'figures': {'flow': 1.0, 'calm': 0.4}, 'harmonize': {0: 0.3, 1: 0.7},
               'rit': {0.8: 0.4, 0.85: 0.3, 0.92: 0.3},
               'tail': {0: 0.7, 1: 0.3}, 'bass': {'root': 0.7, 'walk': 0.3}, 'fill': {0: 0.1, 1: 0.9},
               'turn': {0: 0.3, 1: 0.7}, 'vary': {'keep': 0.35, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.05},
               'layouts': ('song', 'return')},
              {'name': 'B1', 'part': 'B', 'dyn': {('mp', 'mf', 'mp'): 1.0, ('p', 'mf', 'mp'): 0.5, 'mf': 0.4},
               'figures': {'chorus': 1.0, 'flow': 0.25}, 'rit': {0.85: 0.5, 0.9: 0.3, 0.8: 0.2},
               'tail': {0: 0.8, 1: 0.2}, 'fill': {0: 0.4, 1: 0.6},
               'key': {'major': {'home': 0.8, 'bVI': 0.08, 'IV': 0.06, 'bIII': 0.06},
                       'minor': {'home': 0.8, 'par': 0.1, 'IV': 0.1}}},
              {'name': 'A2', 'part': 'A2', 'dyn': {('p', 'mp'): 1.0, 'mp': 0.5, ('mp', 'p'): 0.4},
               'figures': {'flow': 1.0, 'calm': 0.4}, 'harmonize': {0: 0.3, 1: 0.7},
               'rit': {0.8: 0.4, 0.85: 0.3, 0.92: 0.3}, 'bass': {'root': 0.5, 'walk': 0.5}, 'fill': {0: 0.1, 1: 0.9},
               'turn': {0: 0.3, 1: 0.7},
               'vary': {'keep': 0.3, 'orn': 0.3, 'rhythm': 0.25, 'seq': 0.1, 'invert': 0.05}, 'layouts': ('chorus',)},
              # (round r6: the interlude = the intro's first two bars at -9..-12 LU, a cut-off: now the intro's
              # half cadence - its last two bars, into the theme - and a step softer only)
              {'name': 'inter', 'frame': 'intro', 'dyn': {'p': 1.0, 'mp': 0.4, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'keep_bars': (2, 3), 'rit': {0.78: 0.3, 0.82: 0.4, 0.88: 0.3},
               'chance': 0.6,
               'bars': {((2, 4),): 1.0}, 'octave': {0: 0.5, 1: 0.5}, 'vary': {'keep': 0.1, 'orn': 0.5, 'rhythm': 0.4},
               'layouts': ('song',)},
              {'name': 'A3', 'part': 'A1', 'dyn': {'p': 1.0, ('p', 'mp'): 0.5, ('mp', 'p'): 0.4},
               'figures': {'calm': 1.0, 'flow': 0.6}, 'harmonize': {0: 0.3, 1: 0.7}, 'chance': 0.6,
               'octave': {0: 0.7, 1: 0.3},
               'bars': {((0, 8),): 0.5, ((0, 4),): 0.5}, 'bass': {'root': 0.4, 'walk': 0.6}, 'fill': {0: 0.5, 1: 0.5},
               'vary': {'keep': 0.2, 'orn': 0.3, 'rhythm': 0.2, 'seq': 0.2, 'invert': 0.1}, 'layouts': ('song',)},
              {'name': 'build', 'part': 'C', 'dyn': {('mp', 'f'): 1.0, ('p', 'mf'): 0.5, ('mp', 'mf'): 0.5},
               'figures': 'build', 'rit': {0.85: 0.5, 0.9: 0.3, 0.8: 0.2}, 'tail': {0: 0.7, 1: 0.3},
               'bars': {((0, 8),): 0.55, ((0, 4), (6, 8)): 0.45}, 'fill': {0: 0.1, 1: 0.9}},
              {'name': 'climax', 'part': 'B', 'melody': 'lift',
               'dyn': {('f', 'ff', 'mf'): 1.0, ('mf', 'f', 'mp'): 0.6, ('f', 'ff', 'f'): 0.4, ('mf', 'ff', 'mp'): 0.5},
               'figures': {'big': 1.0, 'build': 0.35}, 'harmonize': {1: 0.3, 2: 0.7},
               'harm_share': {0.35: 0.3, 0.45: 0.4, 0.6: 0.3}, 'peak': True, 'rit': {0.68: 0.3, 0.72: 0.4, 0.8: 0.3},
               'fermata': {1.5: 0.3, 2.5: 0.4, 3.5: 0.3}, 'cadenza': 0.15,
               'climax': {'lift': 0.15, 'theme': 0.3, 'climb': 0.2, 'step': 0.1, 'grow': 0.5},
               'key': {'major': {'home': 0.55, 'step': 0.1, 'bVI': 0.12, 'IV': 0.1, 'bIII': 0.08, 'III': 0.05},
                       'minor': {'home': 0.5, 'par': 0.25, 'rel': 0.1, 'IV': 0.15}},
               'reharm': {0: 0.05, 0.7: 0.45, 1.0: 0.5}, 'tail': {0: 0.55, 1: 0.45}, 'fill': {0: 0.1, 1: 0.9},
               'vary': {'keep': 0.15, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.15, 'invert': 0.1}},
              # (return: after the climax the music melts - an interlude, the theme's return high and soft)
              # (round r6: A3 = A1 note for note, half of it an octave up then down mid-phrase: now high or low
              # throughout, a half return or the whole)
              {'name': 'inter', 'frame': 'intro', 'dyn': {'p': 1.0, 'mp': 0.4, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'keep_bars': (2, 3), 'rit': {0.75: 0.3, 0.8: 0.4, 0.86: 0.3},
               'chance': 0.7,
               'bars': {((2, 4),): 1.0}, 'octave': {0: 0.4, 1: 0.6}, 'vary': {'keep': 0.1, 'orn': 0.5, 'rhythm': 0.4},
               'layouts': ('return',)},
              {'name': 'A3', 'part': 'A1', 'dyn': {('mp', 'p'): 1.0, 'p': 0.6, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'harmonize': {0: 0.3, 1: 0.7},
               'tempo': {0.9: 0.3, 0.93: 0.4, 0.97: 0.3}, 'rit': {0.75: 0.3, 0.8: 0.4, 0.85: 0.3},
               'octave': {0: 0.5, 1: 0.5}, 'bars': {((0, 8),): 0.45, ((0, 4), (6, 8)): 0.55},
               'bass': {'root': 0.5, 'walk': 0.5}, 'fill': {0: 0.5, 1: 0.5},
               'vary': {'keep': 0.2, 'orn': 0.3, 'rhythm': 0.2, 'seq': 0.2, 'invert': 0.1}, 'layouts': ('return',)},
              {'name': 'A4', 'part': 'A2', 'dyn': {('mp', 'p'): 1.0, 'p': 0.6, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'tempo': {0.9: 0.3, 0.93: 0.4, 0.97: 0.3},
               'rit': {0.75: 0.3, 0.8: 0.4, 0.85: 0.3},
               'octave': {0: 0.5, 1: 0.5}, 'cadence': {'home': 0.3, 'vi': 0.45, 'IV': 0.25},
               'bass': {'root': 0.6, 'walk': 0.4}, 'fill': {0: 0.5, 1: 0.5}, 'turn': {0: 0.4, 1: 0.6},
               'vary': {'keep': 0.2, 'orn': 0.3, 'rhythm': 0.2, 'seq': 0.2, 'invert': 0.1}, 'layouts': ('song', 'chorus')},
              {'name': 'coda', 'frame': 'tag', 'dyn': {('p', 'pp'): 1.0, ('mp', 'pp'): 0.5, 'pp': 0.3},
               'figures': 'thin', 'tempo': {0.9: 0.3, 0.95: 0.4, 1.0: 0.3}, 'rit': {0.7: 0.3, 0.75: 0.4, 0.82: 0.3},
               'bars': {((0, 4),): 0.6, ((2, 4),): 0.4},
               'vary': {'keep': 0.3, 'orn': 0.35, 'rhythm': 0.35}}]},
    melody={'register': ('G4', 'Bb5'), 'center': 'Eb5', 'peak': 'C6', 'steps': _NA_STEPS, 'ends': _NA_ENDS,
            'repeat': (2.5, 1.5),         # a repeated note costs more (blind round N0: repeated-note pickups)
            'chromatic': 0.04,            # half-step-below approach notes: rare (round r1: weak-beat clashes)
            # 2-bar units a later A restates (round r2: A2 = A1's first 6 bars; audit 2026-10-13: three too)
            'restate': {1: 0.35, 2: 0.5, 3: 0.15},
            # (no 'hook_seq': the hook sequenced as a 1-bar cell broke the head's writing rules - one rhythm 4x in 8
            # bars, repeated pitches over the references' 0.05 - audit 2026-10-13: kept at 0)
            # the chorus's counter-motif: the hook's shape upside down or a shape of its own (audit 2026-10-13)
            'counter': {'mirror': 0.5, 'own': 0.5},
            # a chorus's inner half cadence runs on as a line in that share of the tunes (round r5: a lone held note
            # in the chorus's 4th bar of every piece)
            'half_line': {'B': 0.4},
            # how the theme / the chorus open (composer.compose: the motif cells by weight, default 1; round r10:
            # 'across' - three empty beats, a beat-4 pickup - opening the chorus in three of four pieces)
            'openings': {'across': 0.15, 'pickup': 0.5, 'rise3': 0.6},
            # where the head's climax goes, drawn per tune (the learned generator 2026-10-12: always part C bar 4-5 at
            # 87-91 % of the head, C6 / B5): the build (C) or the chorus (B), its phrase by the curve's level; the
            # climax pitch moves with plan['set']['shift']
            'climax_parts': {'C': 1.0, 'B': 0.8},
            'plain_head': 3,            # a hook statement's first 3 notes keep their chord tones (round r5: the
            #                               theme's head on non-chord tones - the appoggiatura goes elsewhere)
            'raised_v': True,           # V in minor: the key's scale with G# (round r7: C#, D#, F# over E in A minor)
            'bridge_long': 0.2,         # the chorus on the long cells in that share (audit: always the contrast)
            # (the build starts nearer the hook's register: ~60 % of the tunes had the hook above the build - the
            # arc check rejected them, best-of-8 saw 3-5 candidates)
            # (audit 2026-10-13: every A peaking in its third phrase, every B in its third / first - A / B shapes
            # peaking early or at the end too)
            'contours': {'A': dict(CONTOURS['A'], early=(((0.0, -1), (0.3, 4), (1.0, -4)), 0.5),
                                   end=(((0.0, -4), (0.5, 0), (0.9, 5), (1.0, 3)), 0.35)),
                         'B': dict(CONTOURS['B'], early=(((0.0, 1), (0.3, 4), (1.0, -2)), 0.5)),
                         'C': {'climb': (((0.0, 1), (0.75, 6), (1.0, 3)), 1.0),
                               'wave': (((0.0, 2), (0.4, 0), (0.8, 6), (1.0, 2)), 0.7)}},
            'shift': {'B': {2: 1.0, 3: 1.0, 4: 0.6}, 'C': {5: 1.0, 7: 0.8, 6: 0.5}}},
    harmony=NEW_AGE_HARMONY,
    titles={'adj': ['Quiet', 'Paper', 'Golden', 'Small', 'Distant', 'Gentle', 'Silver', 'Early', 'Open', 'Falling',
                    'Little', 'Hidden', 'Slow', 'Faded', 'Glass', 'Soft', 'Other', 'Northern'],
            'noun': ['Rivers', 'Lanterns', 'Windows', 'Seasons', 'Wings', 'Kites', 'Footsteps', 'Promises', 'Lights',
                     'Leaves', 'Bridges', 'Waves', 'Stars', 'Stones', 'Gardens', 'Mirrors', 'Petals', 'Postcards'],
            'time': ['the Morning', 'Autumn', 'the Rain', 'Spring', 'the Evening', 'Snowfall', 'the Tide', 'Summer',
                     'Dawn', 'the Sea', 'the Hills', 'Winter'],
            'shapes': ['{noun} to {time}', '{adj} {noun}', '{noun} in {time}', 'The {adj} {noun}', '{noun} of {time}',
                       'Before {time}', '{adj} {noun} of {time}', 'After {time}'],
            'suffix': {'': ''}},
    album='Endless Piano', style='new-age',
)

CLASSICAL_HARMONY = {
    'blocks': {
        'major': {
            'open': {'I_IV_I_V': 'I IV@5 I V7', 'I_vi_ii_V': 'I VIm IIm7@3 V7', 'I_I7_IV_iv': 'I I7 IV IVm6',
                     'I_V3_I_V': 'I V7@3 I V'},
            'turn': {'IV_ii_V': 'IV IIm7@3 V7:2', 'vi_II7_V': 'VIm II7 V7:2', 'IV_ivo_I64_V': 'IV #IVo I@5 V7'},
            'final': {'IV_I64_V_I': 'IV I@5 V7 I', 'ii65_V_I': 'IIm7@3 V7 I:2', 'iv_I64_V_I': 'IVm6 I@5 V7 I',
                      'N6_V_I': 'bII@3 V7 I:2'},
            'to_bridge': {'home_I7': 'IIm7 V7 I I7'},
            'bridge': {'IV_iv': 'IV IVm I@5 VIm IIm7 II7 V V7', 'relative': 'VIm III7 VIm IIIm IV #IVo V V7',
                       'dominant': 'II7 V II7 V VIm II7 IIm7@3 V7', 'bVI': 'bVI bII@3 V7 I IVm6 I@5 IIm7 V7'},
        },
        'minor': {
            'open': {'i_iv_V_i': 'Im IVm V7 Im', 'i_VI_ii_V': 'Im bVI IIø@3 V7', 'i_V3_i_iv': 'Im V7@3 Im IVm'},
            'turn': {'iv_ii_V': 'IVm IIø@3 V7:2', 'VI_iv_V': 'bVI IVm V7:2', 'VI_N_V': 'bVI bII@3 V7:2'},
            'final': {'iv_V_i': 'IVm V7 Im:2', 'N6_V_i': 'bII@3 V7 Im:2', 'ii_V_i': 'IIø@3 V7 Im:2',
                      'iv_i64_V_i': 'IVm Im@5 V7 Im'},
            'to_bridge': {'home_to_iv': 'IIø V7 Im I7'},
            'bridge': {'relative': 'bIII bVII7 bIII bVI IIø V7 Im V7', 'iv': 'IVm IVm bVII7 bIII bVI IIø V7 V7',
                       'major': 'I IV@5 I V7 IVm6 Im@5 IIø V7'},
        },
    },
    'colours': {'M': {'': 3.0, 'maj7': 0.4}, 'M_tonic': {'': 1.0}, 'm': {'m': 2.0, 'm7': 0.8}, 'm_tonic': {'m': 1.0},
                '7_major': {'7': 1.0}, '7_minor': {'7': 1.0, '7b9': 0.4}, '7_blues': {'7': 1.0}, '7_sub': {'7': 1.0},
                'ø': {'m7b5': 1.0}, 'o': {'dim7': 1.0}, 'sus': {'7sus4': 1.0}},
    'intros': {'major': {'I_V': ('I V7 I V7', 1.0), 'I_IV': ('I IV@5 I V7', 0.8)},
               'minor': {'i_V': ('Im V7 Im V7', 1.0), 'i_iv': ('Im IVm Im V7', 0.8)}},
    'intro_tonic': (),
    'endings': {'major': {'': 1.0}, 'minor': {'m': 1.0, '': 0.3}},
    'tag_approach': {'plagal': 1.0, 'sus': 0.5},
}

CLASSICAL_PIANO = Genre(
    name='classical-piano',
    description='romantic solo piano (a nocturne / a salon waltz): ternary a a\' b b\' a\'\' + coda, a song-like '
                'melody over a nocturne arpeggio or an oom-pah-pah, chromatic colour (Neapolitan, diminished, '
                'borrowed iv), the b\' the climax with a cadenza flourish into the return',
    forms={'AABA': 1},
    moods={'reverie': {'feels': {'nocturne': 3, 'waltz': 1}, 'modes': {'major': 2, 'minor': 1},
                       'keys': {'major': ['Db', 'Eb', 'Ab', 'B', 'E', 'F'], 'minor': ['C#', 'F', 'C', 'G', 'Bb']},
                       'tempo': 0, 'colour': 1.0, 'tritone': 0.0, 'energy': 0.35},
           'melancholy': {'feels': {'nocturne': 2, 'waltz': 2}, 'modes': {'minor': 1},
                          'keys': {'minor': ['C#', 'A', 'E', 'B', 'F', 'C']}, 'tempo': -2, 'colour': 1.0,
                          'tritone': 0.0, 'energy': 0.25},
           'salon': {'feels': {'waltz': 3, 'nocturne': 1}, 'modes': {'major': 3, 'minor': 1},
                     'keys': {'major': ['Ab', 'Db', 'Gb', 'Eb', 'E', 'A'], 'minor': ['A', 'C#', 'E', 'F']},
                     'tempo': 4, 'colour': 1.0, 'tritone': 0.0, 'energy': 0.75}},
    feels={'nocturne': {'tempo': (54, 66), 'meter': 4, 'cells': 'ballad', 'style': 'ballad', 'lh': 'broken',
                        'swing': False, 'rubato': 0.07, 'touch': (40, 104), 'energy': 0.3, 'body': 'lyrical',
                        'figures': {'intro': {'nocturne': 1.0}, 'calm': {'nocturne': 1.0, 'flow': 0.5},
                                    'flow': {'nocturne': 1.0, 'color': 0.4, 'flow': 0.4},
                                    'thin': {'open': 1.0, 'quart': 0.7}, 'build': {'nocturne': 1.0, 'color': 0.5},
                                    'big': {'big': 1.0, 'sweep': 0.5}, 'rest': 'ring', 'into': 'up',
                                    'end': 'roll'}},
           'waltz': {'tempo': (138, 162), 'meter': 3, 'cells': 'waltz', 'style': 'ballad', 'lh': 'broken',
                     'swing': False, 'rubato': 0.06, 'touch': (44, 104), 'energy': 0.65, 'body': 'waltz',
                     'figures': {'intro': {'waltz': 1.0, 'waltz_held': 0.6, 'waltz_open': 0.5},
                                 'calm': {'waltz': 1.0, 'waltz2': 0.6, 'waltz_open': 0.6, 'waltz_held': 0.3},
                                 'flow': {'waltz': 1.0, 'waltz2': 1.0, 'waltz_open': 0.7, 'waltz_arp': 0.5,
                                          'barcarolle': 0.4},
                                 'thin': {'waltz_held': 1.0, 'waltz': 0.7, 'waltz_open': 0.5},
                                 'build': {'waltz2': 1.0, 'barcarolle': 1.0, 'waltz_step': 0.8, 'waltz_arp': 0.6},
                                 'big': {'waltz_big': 1.0, 'waltz': 0.6, 'waltz_arp': 0.5}, 'rest': 'waltz',
                                 'into': 'barcarolle', 'end': 'roll'}}},
    band={'preset': 'solo_piano', 'master_gain': 7.5, 'profile': 'piano', 'loudness': (-23.0, -15.0), 'bass': None,
          'drums': None, 'eq': NEW_AGE_PIANO.band['eq'], 'master_eq': NEW_AGE_PIANO.band['master_eq'],
          'breath': {'quiet1': 0.25, 'att_cv4': 0.08}},
    plan={'perform': 'piano', 'intro': 2, 'tag': 4, 'end': 1, 'phrases': {'A': _SING_PHRASES['A']},
          'end_styles': {'roll': 1.0, 'spread': 0.8},
          'sections': [
              {'name': 'intro', 'frame': 'intro', 'dyn': 'p', 'figures': 'intro', 'lh_only': 2},
              {'name': 'A1', 'part': 'A1', 'dyn': 'p', 'figures': 'calm'},
              {'name': 'A2', 'part': 'A2', 'dyn': ('p', 'mp'), 'figures': 'flow', 'harmonize': 1, 'rit': 0.85},
              {'name': 'B1', 'part': 'B', 'dyn': ('mp', 'mf'), 'figures': 'build'},
              # the waltz plays its strains twice (a salon waltz: ~3 minutes, not 2): the theme back fuller, an
              # interlude on the intro's vamp, the second A building into the climax
              {'name': 'A1b', 'part': 'A1', 'dyn': 'mp', 'figures': 'flow', 'harmonize': 1, 'feels': ('waltz',)},
              {'name': 'inter', 'frame': 'intro', 'dyn': 'p', 'figures': 'thin', 'keep_bars': (0, 2), 'rit': 0.85,
               'feels': ('waltz',)},
              {'name': 'A2b', 'part': 'A2', 'dyn': ('p', 'mf'), 'figures': 'build', 'feels': ('waltz',)},
              {'name': 'B2', 'part': 'B', 'melody': 'lift', 'dyn': ('mf', 'f', 'mp'), 'figures': 'big',
               'harmonize': 2, 'peak': True, 'rit': 0.75, 'fermata': 1.5, 'cadenza': 0.7},
              {'name': 'A3', 'part': 'A3', 'dyn': ('p', 'pp'), 'figures': 'calm', 'harmonize': 1, 'tempo': 0.95,
               'rit': 0.8},
              {'name': 'coda', 'frame': 'tag', 'dyn': 'pp', 'figures': 'thin', 'tempo': 0.92, 'rit': 0.75}]},
    melody={'register': ('F4', 'Bb5'), 'center': 'Db5', 'peak': 'C6', 'steps': {0: 0.1, 1: 0.58, 2: 0.22, 3: 0.06,
                                                                               4: 0.04},
            'ends': _SING_ENDS, 'bridge_long': 0.4},
    harmony=CLASSICAL_HARMONY,
    titles={'adj': ['Quiet', 'Pale', 'Distant', 'Silver', 'Lost', 'Winter', 'Evening', 'Lonely', 'Tender', 'Faded',
                    'Gentle', 'Last'],
            'noun': ['Garden', 'Candle', 'Promise', 'Letter', 'Shore', 'Mirror', 'Lantern', 'Rose', 'Swallow',
                     'Window', 'Ribbon', 'Harbour'],
            'shapes': {'nocturne': ['Nocturne in {key}', 'Nocturne in {key} ({adj} {noun})', 'Romance in {key}',
                                    'Reverie in {key}', 'The {adj} {noun}'],
                       'waltz': ['Waltz in {key}', 'Valse: The {adj} {noun}', 'Waltz in {key} ({adj} {noun})',
                                 'Salon Waltz in {key}']},
            'suffix': {'': ''}},
    album='Endless Piano', style='classical',
)

# ------------------------------------------------------------------------------------------------ lo-fi piano
# A warm, dull, intimate piano on a cassette (the lofi_piano band preset: the felt piano, tape wow / flutter / hiss, the
# highs rolled off, a vinyl crackle bed), jazzy 7th / 9th loops (ii-V-I, IVmaj7-iii7-vi7, borrowed chords), short
# loop-like 8-bar parts, a sparse melody with lots of space, a lazy swing or straight 8ths at 70-90 BPM and - per mood -
# a soft dusty kit (drummer style 'lofi': boom-bap kick, a laid-back snare, the piano gently ducked by it).

LOFI_HARMONY = {
    'blocks': {
        'major': {
            # the loop: 4 bars, every A opens alike (the loop comes back)
            'open': {'ii_V_I_vi': 'IIm V7 IM VIm', 'IV_iii_vi': 'IVM IIIm VIm:2', 'I_vi_ii_V': 'IM VIm IIm V7',
                     'IV_iv_iii_vi': 'IVM IVm6 IIIm VIm', 'I_III7_IV_iv': 'IM III7 IVM IVm7'},
            'turn': {'IV_iii_ii_V': 'IVM IIIm IIm V7', 'ii_V_iii_VI': 'IIm V7 IIIm VI7',
                     'IV_iv_ii_V': 'IVM IVm7 IIm Vsus:0.5 V7:0.5', 'bVI_bVII': 'IVM IIIm bVIM bVII7'},
            'final': {'ii_V_I': 'IIm V7 IM:2', 'backdoor': 'IVM IVm7 bVII7 IM', 'IV_iv_I': 'IVM IVm6 IM:2',
                      'ii_bII_I': 'IIm bII7 IM:2'},
            # the B: its own loop twice, the second time with a small change at its end
            'hook': {'IV_iii_vi': 'IVM IIIm VIm VIm IVM IIIm IIm V7', 'IV_iv_iii_VI': 'IVM IVm7 IIIm VI7 IIm V7 IM V7',
                     'vi_ii_V_I': 'VIm IIm V7 IM VIm IIm bVII7 Vsus', 'bVI_bVII_I': 'IVM bVIM bVII7 IM IVM bVIM IIm V7'},
            'build': {'iii_VI_ii_V': 'IIIm VI7 IIm V7 IIIm VI7 IIm V7', 'IV_iv': 'IVM IVM IVm7 IVm7 IIIm VI7 IIm V7',
                      'ii_cycle': 'IIm IIm V7 V7 IM VIm IIm V7'},
        },
        'minor': {
            'open': {'i_iv_VII_III': 'Im IVm bVII7 bIIIM', 'i_VI_ii_V': 'Im bVIM IIø V7', 'i_iv': 'Im IVm Im IVm',
                     'i_VII_VI_V': 'Im bVII7 bVIM V7'},
            'turn': {'iv_VII_VI_V': 'IVm bVII7 bVIM V7', 'VI_ii_V': 'bVIM IIø V7:2', 'iv_v_VI_V': 'IVm Vm bVIM V7'},
            'final': {'ii_V_i': 'IIø V7 Im:2', 'VI_V_i': 'bVIM V7 Im:2', 'iv_VII_i': 'IVm bVII7 Im:2'},
            'hook': {'VI_VII_III': 'bVIM bVII7 bIIIM bIIIM bVIM bVII7 IIø V7',
                     'iv_VII_III_VI': 'IVm bVII7 bIIIM bVIM IVm bVII7 IIø V7'},
            'build': {'VI_iv': 'bVIM bVIM IVm IVm IIø V7 Im V7', 'III_VII': 'bIIIM bVII7 IVm Im bVIM bVII7 IIø V7'},
        },
    },
    # the lo-fi colours: 7ths and 9ths everywhere, a m11, a 13 - never a plain triad
    'colours': {'M': {'maj7': 1.5, 'maj9': 2.0, '69': 0.6, '6': 0.3}, 'M_tonic': {'maj9': 2.0, 'maj7': 1.2, '69': 1.0},
                'm': {'m7': 1.2, 'm9': 2.0, 'm11': 0.8}, 'm_tonic': {'m9': 2.0, 'm7': 1.0, 'm11': 0.6},
                '7_major': {'9': 1.5, '13': 1.5, '7': 0.4}, '7_minor': {'7b9': 1.5, '7b13': 1.0, '7#9': 0.5},
                '7_blues': {'9': 1.5, '13': 1.0}, '7_sub': {'9': 1.0, '7#11': 1.0},
                'ø': {'m7b5': 1.0}, 'o': {'dim7': 1.0}, 'sus': {'9sus4': 1.0, '7sus4': 0.6}},
    'intros': {'major': {'IV_iii_vi': ('IVmaj9 IIIm7 VIm9 V9sus4', 1.0), 'ii_V': ('IIm9 V13 IIm9 V13', 0.8),
                         'I_IV': ('Imaj9 IVmaj9 Imaj9 IVmaj9', 0.7)},
               'minor': {'i_iv': ('Im9 IVm9 Im9 IVm9', 1.0), 'VI_V': ('bVImaj9 V7b9 bVImaj9 V7b9', 0.8),
                         'i_VII': ('Im9 bVII9 bVImaj7 V7#9', 0.6)}},
    'intro_tonic': (),
    'endings': {'major': {'maj9': 1.0, '69': 0.8, 'maj7': 0.5}, 'minor': {'m9': 1.0, 'm11': 0.6}},
    'tag_approach': {'plagal': 1.0, 'backdoor': 0.8, 'sus': 0.6},
}

_LOFI_FIGURES = {'intro': {'lofi_hold': 1.0, 'lofi_push': 0.6}, 'calm': {'lofi_hold': 1.0, 'lofi_push': 0.8,
                                                                         'lofi_two': 0.5},
                 'flow': {'lofi_push': 1.0, 'lofi_skip': 0.8, 'lofi_two': 0.6, 'lofi_hold': 0.4},
                 'thin': {'lofi_hold': 1.0, 'lofi_rest': 0.6}, 'build': {'lofi_skip': 1.0, 'lofi_push': 0.8,
                                                                         'lofi_two': 0.6},
                 'big': {'lofi_two': 1.0, 'lofi_skip': 0.8, 'lofi_push': 0.6}, 'rest': 'lofi_rest', 'into': 'lofi_push',
                 'end': 'roll'}
"""The lo-fi left hand per section (pianist.FIGURES 'lofi_*': a 7th chord voiced root - 10th - 5th - 7th, held, pushed
onto the & of 2, struck on 1 and 3 or skipping onto 2 and 4; 'lofi_rest' under the melody's breaths)."""

_LOFI_DRUMS = {'style': 'lofi', 'density': 0.4, 'vel': 0.85}
"""A mood's drums (perform.build_piano: drummer.arrange on the band's 'drums' over the sections without
'drums': False; vel x the drummer's levels): the boom-bap lofi kit; None = piano only."""

LOFI_PIANO = Genre(
    name='lofi-piano',
    description='lo-fi piano: a warm, dull, felt-ish piano on a wobbly cassette with vinyl crackle, jazzy 7th / 9th '
                'loops (ii-V-I, IVmaj7-iii7-vi7, borrowed chords), short 8-bar A / B parts, a sparse melody with lots '
                'of space, lazy swing or straight 8ths at 70-90 BPM and - per mood - a soft dusty boom-bap kit',
    forms={'verse': 1},
    moods={'study': {'feels': {'lazy': 3, 'even': 2}, 'modes': {'major': 3, 'minor': 1},
                     'keys': {'major': ['F', 'Bb', 'Eb', 'Ab', 'C', 'D'], 'minor': ['D', 'A', 'E', 'G']}, 'tempo': 0,
                     'colour': 1.0, 'tritone': 0.0, 'energy': 0.55, 'drums': _LOFI_DRUMS},
           'rain': {'feels': {'drift': 1}, 'modes': {'minor': 2, 'major': 1},
                    'keys': {'major': ['Db', 'Ab', 'E', 'Gb'], 'minor': ['F', 'C', 'Bb', 'C#', 'G#']}, 'tempo': -2,
                    'colour': 1.2, 'tritone': 0.0, 'energy': 0.15, 'drums': None},
           # (a mood with drums plays only the steady feels: the kit keeps strict time)
           'late-night': {'feels': {'lazy': 1}, 'modes': {'minor': 2, 'major': 1},
                          'keys': {'major': ['Db', 'Ab', 'Eb', 'B'], 'minor': ['C', 'F', 'G', 'Bb', 'Eb']},
                          'tempo': -3, 'colour': 1.3, 'tritone': 0.0, 'energy': 0.35,
                          'drums': dict(_LOFI_DRUMS, density=0.25, vel=0.72)},
           'sunday': {'feels': {'even': 3, 'lazy': 1}, 'modes': {'major': 1},
                      'keys': {'major': ['C', 'G', 'D', 'F', 'A', 'E']}, 'tempo': 3, 'colour': 0.9, 'tritone': 0.0,
                      'energy': 0.8, 'drums': dict(_LOFI_DRUMS, density=0.5, vel=0.9)}},
    # lazy / even: the drums keep time (steady: no phrase rubato, no lilt, no inhale - the kit plays the grid); drift:
    # piano alone, a little rubato. 'groove': the feel's own swing ratio when --swing is not given (lazy swing)
    feels={'lazy': {'tempo': (72, 86), 'meter': 4, 'cells': 'lofi', 'style': 'ballad', 'lh': 'broken', 'swing': True,
                    'groove': 0.57, 'steady': True, 'rubato': 0.0, 'touch': (42, 96), 'energy': 0.45,
                    'body': 'swing', 'figures': _LOFI_FIGURES},
           'even': {'tempo': (80, 90), 'meter': 4, 'cells': 'lofi', 'style': 'ballad', 'lh': 'broken', 'swing': True,
                    'steady': True, 'rubato': 0.0, 'touch': (44, 98), 'energy': 0.75, 'body': 'swing',
                    'figures': _LOFI_FIGURES},
           'drift': {'tempo': (68, 76), 'meter': 4, 'cells': 'lofi', 'style': 'ballad', 'lh': 'broken', 'swing': True,
                     'rubato': 0.03, 'touch': (38, 94), 'energy': 0.15, 'body': 'calm',
                     'figures': dict(_LOFI_FIGURES, flow={'lofi_hold': 1.0, 'lofi_push': 0.7, 'lofi_two': 0.3},
                                     big={'lofi_two': 1.0, 'lofi_hold': 0.8})}},
    band={'preset': 'lofi_piano', 'master_gain': 8.0, 'profile': 'piano', 'loudness': (-21.0, -13.0),
          'bass': None, 'drums': None, 'breath': {'quiet1': 0.25, 'att_cv4': 0.08}},
    plan={'perform': 'piano', 'intro': 4, 'tag': 4, 'end': 1, 'phrases': _SING_PHRASES,
          'end_styles': {'roll': 1.0},
          'sections': [
              {'name': 'intro', 'frame': 'intro', 'dyn': 'p', 'figures': 'intro', 'lh_only': 2, 'drums': False},
              {'name': 'A1', 'part': 'A1', 'dyn': 'mp', 'figures': 'calm'},
              {'name': 'A2', 'part': 'A2', 'dyn': 'mp', 'figures': 'flow', 'harmonize': 1},
              {'name': 'B1', 'part': 'B', 'dyn': ('mp', 'mf', 'mp'), 'figures': 'flow'},
              {'name': 'A3', 'part': 'A1', 'dyn': 'mp', 'figures': 'calm', 'harmonize': 1, 'chance': 0.6},
              {'name': 'bridge', 'part': 'C', 'dyn': ('p', 'mp'), 'figures': 'build', 'chance': 0.5, 'drums': False},
              {'name': 'B2', 'part': 'B', 'melody': 'lift', 'dyn': ('mp', 'mf', 'mp'), 'figures': 'big',
               'harmonize': 1, 'peak': True},
              {'name': 'A4', 'part': 'A2', 'dyn': ('mp', 'p'), 'figures': 'calm'},
              {'name': 'coda', 'frame': 'tag', 'dyn': 'p', 'figures': 'thin', 'rit': 0.8, 'drums': False}]},
    # the melody sits low and close (an intimate hum, not a singer's top): few notes, long rests
    melody={'register': ('F4', 'G5'), 'center': 'C5', 'peak': 'A5', 'steps': _SING_STEPS,
            'ends': {'breath': 0.6, 'down': 0.2, 'antic': 0.15, 'lh': 0.05}, 'bridge_long': 0.3,
            'contours': {'C': {'wave': (((0.0, 0), (0.4, -2), (0.8, 3), (1.0, 0)), 1.0),
                               'climb': (((0.0, -2), (0.75, 3), (1.0, 0)), 0.6)}},
            'shift': {'B': {2: 1.0, 3: 1.0, 0: 0.5}, 'C': {0: 1.0, -2: 0.6, 2: 0.6}}},
    harmony=LOFI_HARMONY,
    titles={'adj': ['Dusty', 'Sleepy', 'Rainy', 'Warm', 'Faded', 'Lazy', 'Quiet', 'Late', 'Soft', 'Hazy', 'Paper',
                    'Little', 'Slow', 'Cloudy', 'Worn'],
            'noun': ['Tapes', 'Windows', 'Notebooks', 'Polaroids', 'Headphones', 'Streetlights', 'Mornings', 'Plants',
                     'Records', 'Cassettes', 'Rooftops', 'Umbrellas', 'Pages', 'Mugs', 'Trains'],
            'time': ['3 A.M.', 'Sunday', 'the Rain', 'Dusk', 'Midnight', 'the Weekend', 'Autumn', 'the Last Bus',
                     'Daybreak', 'Study Hall'],
            'shapes': ['{adj} {noun}', '{noun} at {time}', '{adj} {time}', '{noun} for {time}', 'Before {time}',
                       '{adj} {noun} ({time})'],
            'suffix': {'': ''}},
    album='Endless Lo-Fi', style='lofi',
)

# ------------------------------------------------------------------------------------------------ church organ
# The pipe organ (the church_organ band preset, played by agentsound.organist): the same composer writes the tune - a
# hymn tune in quarters and halves (CELLS 'hymn'), a dotted trumpet tune (CELLS 'march'), a singing line for the
# meditation / trio - over triadic cadential harmony (ORGAN_HARMONY); perform.build hands a plan['perform'] = 'organ'
# tune to endless/organ.py, which sets it in organ TEXTURES (a chorale in four parts, a chorale prelude's ornamented
# cantus over flowing counterpoint, a trio, a toccata with the tune in the pedal, a meditation, a trumpet tune) per
# section of plan['arrangements'][feel], each on a drawn REGISTRATION (organ.REGISTRATIONS).

CELLS['hymn'] = {
    # a chorale tune: quarters, a half now and then, every phrase landing on a long note with a breath (the fermata)
    'motif': {'quarters': (2, 2, 2, 2, 2, 2, 2, 2), 'half_open': (4, 2, 2, 2, 2, 4), 'dotted': (3, 1, 2, 2, 2, 2, 4),
              'passing': (2, 2, 1, 1, 2, 2, 2, 4)},
    'line': {'quarters': (2, 2, 2, 2, 2, 2, 2, 2), 'passing': (2, 1, 1, 2, 2, 2, 2, 4), 'halves': (4, 2, 2, 4, 4),
             'turn': (2, 2, 2, 1, 1, 4, 4)},
    'land': {'land': (2, 2, 2, 2, 6, -2), 'land_half': (4, 2, 2, 6, -2), 'land_pass': (2, 1, 1, 2, 2, 6, -2)},
    'long': {'whole': (4, 4, 6, -2), 'breve': (8, 6, -2), 'held': (4, 2, 2, 6, -2)},
}
CELLS['march'] = {
    # a trumpet tune / festive postlude: dotted pairs, a quick pickup, a held landing
    'motif': {'dotted': (3, 1, 2, 2, 3, 1, 4), 'fanfare': (2, 1, 1, 2, 2, 3, 1, 4), 'pickup': (-2, 1, 1, 3, 1, 2, 2, 4)},
    'line': {'run': (1, 1, 1, 1, 2, 2, 3, 1, 2, 2), 'dotted': (3, 1, 3, 1, 2, 2, 4), 'step': (2, 2, 1, 1, 2, 3, 1, 4)},
    'land': {'land': (3, 1, 2, 2, 6, -2), 'land_pick': (2, 1, 1, 4, 6, -2)},
    'long': {'held': (6, 2, 6, -2), 'call': (4, 2, 2, 6, -2)},
}

CELLS['aria'] = {
    # the meditation's singing line: long-short sighs and arches that start ON the beat (blind round 1: a melody of
    # fragments, every phrase after a rest on beat 1), a held landing with a breath
    'motif': {'sigh': (3, 1, 2, 2, 4, 4), 'arch': (2, 2, 3, 1, 4, 2, 2), 'long_short': (6, 2, 2, 2, 4),
              'flow': (2, 1, 1, 2, 2, 3, 1, 4)},
    'line': {'flow': (2, 2, 1, 1, 2, 4, 2, 2), 'dotted': (3, 1, 2, 2, 6, 2), 'turn': (2, 1, 1, 4, 2, 2, 4),
             'long': (4, 2, 2, 4, 4)},
    'land': {'land': (3, 1, 2, 2, 6, -2), 'land_long': (4, 2, 2, 6, -2), 'land_sigh': (2, 2, 3, 1, 6, -2)},
    'long': {'whole': (4, 4, 6, -2), 'breve': (8, 6, -2), 'held': (6, 2, 6, -2)},
}

ORGAN_HARMONY = {
    # triads and dominant 7ths, cadences in every phrase (organ_vocab.harmonize re-harmonizes beat by beat under the
    # tune, the chart chord preferred): a bar per chord, the cadence's dominant a whole bar or two
    'blocks': {
        'major': {
            'open': {'I_IV_V_I': 'I IV V I', 'I_vi_IV_V': 'I VIm IV V', 'I_ii_V_I': 'I IIm V I',
                     'I_V_vi_iii': 'I V VIm IIIm', 'I_IV_I_V': 'I IV I V'},
            'turn': {'IV_ii_V': 'IV IIm V:2', 'vi_ii_V': 'VIm IIm V:2', 'IV_I_V': 'IV I V:2', 'ii_V_of_V': 'IIm II7 V:2'},
            'final': {'IV_V_I': 'IV V7 I:2', 'ii_V_I': 'IIm V7 I:2', 'IV_I64_V_I': 'IV I@5 V7 I',
                      'vi_ii_V_I': 'VIm IIm V7 I'},
            'to_bridge': {'home_I7': 'IIm V7 I I7'},
            'bridge': {'relative': 'VIm IIIm IV I IIm VIm II7 V', 'IV': 'IV I IV V VIm IIIm IIm V',
                       'dominant': 'V I V VIm II7 V IIm V'},
        },
        'minor': {
            'open': {'i_iv_V_i': 'Im IVm V Im', 'i_VI_iv_V': 'Im bVI IVm V', 'i_VII_III_VI': 'Im bVII bIII bVI',
                     'i_V_i_iv': 'Im V Im IVm'},
            'turn': {'iv_V': 'IVm Im V:2', 'VI_iv_V': 'bVI IVm V:2', 'III_iv_V': 'bIII IVm V:2'},
            'final': {'iv_V_i': 'IVm V7 Im:2', 'VI_V_i': 'bVI V7 Im:2', 'iv_i64_V_i': 'IVm Im@5 V7 Im',
                      'picardy': 'IVm V7 I:2'},
            'to_bridge': {'home_to_iv': 'IVm V7 Im I7'},
            'bridge': {'relative': 'bIII bVII bIII bVI IVm Im V V', 'iv': 'IVm bVII bIII bVI IVm Im V V',
                       'major': 'I IV I V IVm Im V V'},
        },
    },
    'colours': {'M': {'': 1.0}, 'M_tonic': {'': 1.0}, 'm': {'m': 1.0}, 'm_tonic': {'m': 1.0}, '7_major': {'7': 1.0},
                '7_minor': {'7': 1.0}, '7_blues': {'7': 1.0}, '7_sub': {'7': 1.0}, 'ø': {'m7b5': 1.0},
                'o': {'dim7': 1.0}, 'sus': {'7sus4': 1.0}},
    'intros': {'major': {'I_V': ('I IV@5 I V', 1.0), 'I_IV': ('I IV I V', 0.8)},
               'minor': {'i_V': ('Im IVm Im V', 1.0), 'i_VI': ('Im bVI IVm V', 0.8)}},
    'intro_tonic': (),
    'endings': {'major': {'': 1.0}, 'minor': {'m': 1.0, '': 0.4}},
    'tag_approach': {'plagal': 1.0, 'IV': 0.5, 'deceptive': 0.3},
    'tag_span': 1.0,
}
"""The organ's chord vocabulary: triads, V7, a secondary dominant now and then, a Picardy third (the minor's major
tonic at the end), the plagal Amen in the tag - no jazz colour."""

ORGAN = Genre(
    name='organ',
    description='church organ: a chorale and its variations (four-part harmony, flowing 8ths, the full organ), a '
                'chorale prelude (an ornamented cantus over flowing counterpoint), a trio, a toccata with the tune '
                'in the pedal, a meditation (a soft solo with tremulant over strings), a trumpet tune - registration, '
                'articulation and the swell box instead of touch dynamics',
    forms={'AABA': 1},
    moods={'chorale': {'feels': {'chorale': 1, 'prelude': 1}, 'modes': {'major': 2, 'minor': 1},
                       'keys': {'major': ['G', 'F', 'D', 'C', 'Bb', 'Eb'], 'minor': ['D', 'G', 'E', 'A', 'C']},
                       'energy': 0.45},
           'meditation': {'feels': {'meditation': 1}, 'modes': {'major': 2, 'minor': 1},
                          'keys': {'major': ['F', 'Db', 'Eb', 'Ab', 'G'], 'minor': ['F', 'C', 'G', 'E']},
                          'energy': 0.15, 'register': ('D4', 'Bb5'), 'center': 'C5', 'peak': 'Ab5'},
           'trio': {'feels': {'trio': 1}, 'modes': {'major': 2, 'minor': 1},
                    'keys': {'major': ['G', 'C', 'F', 'D', 'Bb'], 'minor': ['D', 'A', 'G', 'C']},
                    'energy': 0.55, 'register': ('D4', 'G5')},
           'toccata': {'feels': {'toccata': 1}, 'modes': {'major': 1, 'minor': 1},
                       'keys': {'major': ['F', 'C', 'G', 'D', 'Bb'], 'minor': ['D', 'G', 'C', 'F', 'E']},
                       'energy': 1.0},
           'festive': {'feels': {'postlude': 1}, 'modes': {'major': 1},
                       'keys': {'major': ['D', 'C', 'Bb', 'Eb', 'F', 'G']}, 'energy': 0.8,
                       'register': ('E4', 'B5'), 'center': 'C5', 'peak': 'A5'}},
    feels={'chorale': {'tempo': (60, 74), 'meter': 4, 'cells': 'hymn', 'swing': False, 'energy': 0.4},
           'prelude': {'tempo': (54, 68), 'meter': 4, 'cells': 'hymn', 'swing': False, 'energy': 0.35},
           'trio': {'tempo': (76, 92), 'meter': 4, 'cells': 'song', 'swing': False, 'energy': 0.55},
           'toccata': {'tempo': (100, 116), 'meter': 4, 'cells': 'hymn', 'swing': False, 'energy': 1.0},
           'meditation': {'tempo': (50, 60), 'meter': 4, 'cells': 'aria', 'swing': False, 'energy': 0.15,
                          'tremulant': True},
           'postlude': {'tempo': (84, 100), 'meter': 4, 'cells': 'march', 'swing': False, 'energy': 0.8}},
    band={'preset': 'church_organ', 'organ': 'burea', 'profile': 'organ', 'loudness': (-25.0, -13.0)},
    plan={'perform': 'organ', 'intro': 4, 'tag': 4, 'end': 1, 'candidates': 8, 'candidate_tries': 2,
          'phrases': _SING_PHRASES,
          'arrangements': {
              # a chorale and two variations: the hymn in four parts on the principals, a chorale-prelude verse
              # (the tune ornamented on a solo stop over flowing counterpoint), the last half on the full organ
              # re-harmonized (the climax) and the cadence home
              'chorale': [
                  dict(name='intro', frame='intro', texture='chorale', reg={'flutes': 1.0, 'soft': 0.6}, verse=0,
                       rit=0.85, chance=0.6),
                  dict(name='v1a', part='A1', texture='chorale', reg={'principal': 1.0}, verse=1),
                  dict(name='v1b', part='A2', texture='chorale', reg={'principal': 1.0}, verse=1),
                  dict(name='v1c', part='B', texture='chorale', reg={'principal': 1.0}, verse=1),
                  dict(name='v1d', part='A3', texture='chorale', reg={'principal': 1.0}, verse=1, rit=0.85),
                  dict(name='v2a', part='A1', texture='cantus', reg={'cornet': 1.0, 'cromorne': 0.8, 'oboe': 0.6},
                       verse=2),
                  dict(name='v2b', part='A2', texture='cantus', reg={'cornet': 1.0, 'cromorne': 0.8, 'oboe': 0.6},
                       verse=2, rit=0.85),
                  dict(name='v3c', part='B', texture='chorale', flow=1.0, reg={'plenum': 1.0}, verse=3),
                  dict(name='v3pp', frame='pedal_point', bars={2: 1.0, 3: 0.7}, texture='chorale', flow=1.0,
                       reg={'plenum': 1.0}, verse=3, chance=0.6),
                  dict(name='v3d', part='A3', texture='chorale', flow=0.8, reg={'plenum': 1.0}, verse=3, rit=0.85,
                       descant=True),
                  dict(name='coda', frame='tag', texture='chorale', reg={'plenum': 1.0}, verse=3, rit=0.7,
                       fermata=3.0)],
              # a chorale prelude: the cantus ornamented on a solo stop over one motif's flowing counterpoint and a
              # walking pedal; the accompaniment opens alone (the motif first)
              'prelude': [
                  dict(name='intro', frame='intro', texture='cantus', solo=False, reg={'cornet': 1.0, 'cromorne': 0.7,
                                                                                       'oboe': 0.6}, verse=1),
                  dict(name='A1', part='A1', texture='cantus', reg={'cornet': 1.0}, verse=1),
                  dict(name='A2', part='A2', texture='cantus', reg={'cornet': 1.0}, verse=1),
                  # (the middle on the Swell: the cantus on the oboe / cromorne, the box breathing - the contrast)
                  dict(name='B', part='B', texture='cantus', reg={'oboe': 1.0, 'cromorne': 0.8}, verse=2,
                       swell='breathe'),
                  dict(name='A3', part='A3', texture='cantus', reg={'cornet': 1.0}, verse=1, rit=0.85),
                  dict(name='coda', frame='tag', texture='cantus', reg={'cornet': 1.0}, verse=1, rit=0.7,
                       fermata=2.5)],
              # a trio: the tune on one manual, a counter-line on another, the pedal walking; twice, on new stops
              'trio': [
                  dict(name='intro', frame='intro', texture='trio', solo=False, reg={'trio': 1.0}, verse=1),
                  dict(name='A1', part='A1', texture='trio', reg={'trio': 1.0}, verse=1),
                  dict(name='A2', part='A2', texture='trio', reg={'trio': 1.0}, verse=1),
                  dict(name='B', part='B', texture='trio', reg={'trio': 1.0}, verse=1),
                  dict(name='A3', part='A3', texture='trio', reg={'trio': 1.0}, verse=1, rit=0.9),
                  # (the second time louder or brighter: the tune on the Great's principals or the positive, the
                  # left hand on the Swell's oboe breathing in the box)
                  dict(name='A1b', part='A1', texture='trio', reg={'trio_great': 1.0, 'trio_reed': 0.6}, verse=2,
                       swell='breathe'),
                  dict(name='A2b', part='A2', texture='trio', reg={'trio_great': 1.0, 'trio_reed': 0.6}, verse=2,
                       swell='breathe'),
                  dict(name='Bb', part='B', texture='trio', reg={'trio_great': 1.0, 'trio_reed': 0.6}, verse=2,
                       swell='breathe'),
                  dict(name='A3b', part='A3', texture='trio', reg={'trio_great': 1.0, 'trio_reed': 0.6}, verse=2,
                       rit=0.8, swell='breathe'),
                  dict(name='coda', frame='tag', texture='trio', reg={'trio_great': 1.0, 'trio_reed': 0.6}, verse=2,
                       rit=0.7, fermata=2.0, swell='close')],
              # a toccata: 16ths over the harmony (three figures), off-beat chords, the tune in the pedal; the
              # figuration's band climbs to the end; the bridge a crescendo in the swell box; twice, the second
              # time on the echo manual first; the coda's figuration stops on a held full chord
              'toccata': [
                  dict(name='intro', frame='intro', texture='toccata', pedal=False, reg={'plenum': 1.0}, verse=1,
                       register=('F4', 'F5')),
                  dict(name='A1', part='A1', texture='toccata', reg={'plenum': 1.0}, verse=1, register=('G4', 'G5')),
                  dict(name='A2', part='A2', texture='toccata', reg={'principal': 1.0}, verse=2, figure=2,
                       register=('A4', 'A5'), pedal_line='bass', lh='beat'),
                  dict(name='B', part='B', texture='toccata', reg={'swell': 1.0}, swell='cresc', verse=3, figure=3,
                       register=('G4', 'G5'), pedal_line='bass'),
                  dict(name='A3', part='A3', texture='toccata', reg={'plenum': 1.0}, verse=1, register=('Bb4', 'Bb5')),
                  dict(name='A1b', part='A1', texture='toccata', reg={'positiv': 1.0}, verse=4, figure=2,
                       register=('G4', 'G5'), pedal_line='bass', lh='beat'),
                  dict(name='Bb', part='B', texture='toccata', reg={'swell': 1.0}, swell='cresc', verse=3, figure=3,
                       register=('A4', 'A5'), pedal_line='bass'),
                  dict(name='pp', frame='pedal_point', bars={2: 0.6, 3: 1.0, 4: 0.6}, texture='toccata',
                       reg={'swell': 1.0}, swell='cresc', verse=3, figure=2, register=('Bb4', 'Bb5'), chance=0.8),
                  dict(name='A3b', part='A3', texture='toccata', reg={'plenum': 1.0}, verse=1, rit=0.85,
                       register=('C5', 'C6')),
                  dict(name='coda', frame='tag', texture='toccata', reg={'plenum': 1.0}, verse=1, rit=0.65,
                       fermata=4.0, register=('C5', 'C6'))],
              # a meditation: a soft solo (oboe / flute, tremulant) over held strings breathing in the swell box
              'meditation': [
                  dict(name='intro', frame='intro', texture='meditation', solo=False,
                       reg={'oboe': 1.0, 'flute_solo': 1.0}, swell='breathe', verse=1),
                  dict(name='A1', part='A1', texture='meditation', reg={'oboe': 1.0, 'flute_solo': 1.0}, swell='breathe', verse=1),
                  dict(name='A2', part='A2', texture='meditation', reg={'oboe': 1.0, 'flute_solo': 1.0}, swell='breathe', verse=1,
                       rit=0.9),
                  dict(name='B', part='B', texture='meditation', reg={'cromorne': 1.0, 'cornet': 0.6},
                       planing=0.4, verse=2),
                  dict(name='pp', frame='pedal_point', bars={2: 1.0, 3: 0.5}, texture='meditation', solo=False,
                       reg={'oboe': 1.0, 'flute_solo': 1.0}, swell='cresc', verse=1, chance=0.6),
                  dict(name='A3', part='A3', texture='meditation', reg={'oboe': 1.0, 'flute_solo': 1.0}, swell='breathe', verse=1,
                       rit=0.85, lift=12),
                  dict(name='coda', frame='tag', texture='meditation', solo=False, reg={'oboe': 1.0, 'flute_solo': 1.0},
                       swell='close', verse=1, rit=0.7, fermata=3.0)],
              # a trumpet tune: the tune on the trumpet, detached chords on another manual, a walking pedal; the
              # bridge an echo; then the hymn in chords on the full organ
              'postlude': [
                  dict(name='intro', frame='intro', texture='trumpet', solo=False, reg={'trumpet': 1.0}, verse=1),
                  dict(name='A1', part='A1', texture='trumpet', reg={'trumpet': 1.0}, verse=1),
                  dict(name='A2', part='A2', texture='trumpet', reg={'trumpet': 1.0}, verse=1),
                  dict(name='B', part='B', texture='trumpet', reg={'cornet': 1.0}, verse=2),
                  dict(name='A3', part='A3', texture='trumpet', reg={'trumpet': 1.0}, verse=1, rit=0.9),
                  dict(name='B2', part='B', texture='chorale', flow=1.2, reg={'plenum': 1.0}, verse=3),
                  dict(name='pp', frame='pedal_point', bars={2: 1.0, 3: 0.8}, texture='chorale', flow=1.2,
                       reg={'plenum': 1.0}, verse=3, chance=0.7),
                  dict(name='A3b', part='A3', texture='chorale', flow=1.0, reg={'plenum': 1.0}, verse=3, rit=0.85,
                       descant=True),
                  dict(name='coda', frame='tag', texture='chorale', reg={'plenum': 1.0}, verse=3, rit=0.7,
                       fermata=3.0)]},
          },
    melody={'register': ('D4', 'F5'), 'center': 'A4', 'peak': 'F5', 'steps': {0: 0.08, 1: 0.64, 2: 0.2, 3: 0.05,
                                                                              4: 0.03},
            'ends': _SING_ENDS, 'bridge_long': 0.4},
    harmony=ORGAN_HARMONY,
    titles={'adj': ['Eternal', 'Holy', 'Morning', 'Evening', 'Golden', 'Quiet', 'Radiant', 'Silent', 'Ancient',
                    'Living', 'Gentle', 'Glorious'],
            'noun': ['Light', 'Shepherd', 'Star', 'Grace', 'Dawn', 'Spirit', 'Peace', 'Harvest', 'River', 'Mountain',
                     'Kingdom', 'Glory'],
            'shapes': {'chorale': ['Chorale on "{adj} {noun}"', 'Chorale in {key}', 'Hymn: {adj} {noun}',
                                   'Partita on "{adj} {noun}"'],
                       'prelude': ['Chorale Prelude on "{adj} {noun}"', 'Chorale Prelude in {key}',
                                   'Prelude on "{adj} {noun}"'],
                       'trio': ['Trio in {key}', 'Trio on "{adj} {noun}"', 'Pastorale in {key}'],
                       'toccata': ['Toccata in {key}', 'Toccata on "{adj} {noun}"', 'Toccata and Hymn in {key}'],
                       'meditation': ['Meditation in {key}', 'Elevation in {key}', 'Priere: {adj} {noun}',
                                      'Communion in {key}'],
                       'postlude': ['Trumpet Tune in {key}', 'Festive Postlude in {key}', 'Voluntary in {key}',
                                    'Processional: {adj} {noun}']},
            'suffix': {'': ''}},
    album='Endless Organ', style='organ',
)

# ------------------------------------------------------------------------------------------------ new-age e-piano
# new-age-piano played on THE 80s e-piano (DX7 ROM1 "E.PIANO 1": synthwave/epiano - stereo-doubled, Juno chorus II,
# a Dimension side layer) in a stack, so the pianist's sustain pedal holds it (the stack keeps a dx7 layer's note-offs
# until pedal-up). Same composer, plan and score as the grand; what an FM e-piano needs that a grand does not: the left
# hand higher (the bass from G2: below it the FM body turns thin and muddy under the pedal; the figures' top to A4), no
# bass-octave climax figures ('big' / 'sweep' double the bass an octave down), clean pedal lifts in chromatic figures
# (the stack's pedal is on / off: a half pedal holds everything), the touch (below: the level from the played
# velocity, the timbre in the round zone), the doubled image narrower (the patch's width 0.6 + dimension read
# 'very wide', correlation 0.13), the chamber + a louder plate (the lush 80s ballad space) and an eq that takes back
# the grand chain's 6.5 kHz air (the tine's bell read +8 dB brilliance) and its 310 Hz cut (thin low mids).

def _epiano_genre() -> 'Genre':
    from ..patches import inst, layer
    na = NEW_AGE_PIANO
    big = {'flow': 1.0, 'pulse': 0.6, 'color': 0.5}
    feels = copy.deepcopy(na.feels)
    for name in feels:                               # (the waltz: its 3/4 hand without the bass octaves)
        feels[name]['figures'] = dict(feels[name]['figures'], big=big if feels[name].get('meter', 4) == 4 else
                                      {'waltz_arp': 1.0, 'waltz2': 0.6, 'waltz_open': 0.5})

    # The touch: E.PIANO 1's velocity moves its timbre (the tine) far more than its level (the gate measured
    # ~0.9 dB per phrase, 0.5 dB per 10 velocity steps: a flat lead; a grand ~2.2), so the stack splits the two -
    # the LEVEL follows the played velocity (velocity fade-ins: the body over 1..127, the right hand's second and
    # third voice of the same sound over 40..127 / 72..127 - a played v41 / v60 / v88 sounds at -6 / 0 / +6.5 dB;
    # measured 1.4 dB per 10 steps with the body alone, 1.9 with two voices, 2.4 with three and the chain's level
    # fixed (below) - the grand reads ~2.2),
    # the TIMBRE gets the velocity curved into the round zone (velcurve / velscale: the right hand's v40 / v70 /
    # v100 / v106 strike the DX7 at v60 / v84 / v104 / v107 - the barky tine only at the climax; the left hand's
    # v25-56 at v48-74: under ~v45 the FM body turns dull and thin)
    def ep(id_, scale, lo=1, **kw):
        return layer('synthwave/epiano', id_, polyphony=32, velsens=1.0, width=0.35, vello=lo, velfade=127 - lo,
                     xfvoices=8, velcurve=0.6, velscale=scale, **kw)
    band = copy.deepcopy(na.band)
    band.update(master_gain=6.0, options={
        # (the stacks 8 dB down into the grand's chain, the faders 4 dB up: its attack compressor and tape, set for
        # the Salamander's level, flattened the loud notes - the piano peaked at +0.3 dBFS before the master; the
        # right hand's layers panned right against its track's -0.35: the mix leaned 2 dB left)
        'sounds': {'piano': inst.stack(ep('epiano', 0.95, pan=0.6), ep('touch', 0.95, lo=40, pan=0.6),
                                       ep('accent', 0.95, lo=72, pan=0.6), level=-8.0),
                   'comp': inst.stack(ep('epiano', 1.0, pan=0.1), level=-8.0)},
        'space': 'chamber'},
        trims={'piano': 4.0, 'comp': 4.0},
        sends={'piano': {'plate': 4.0}},
        eq={'piano': {'peak1.freq': 330, 'peak1.gain': 4.0, 'peak1.q': 0.8, 'high.freq': 6500, 'high.gain': -9.0},
            'comp': {'hp.freq': 90, 'peak1.freq': 330, 'peak1.gain': 3.0, 'peak1.q': 0.8, 'high.freq': 6500,
                     'high.gain': -9.0}},
        master_eq={'peak2.freq': 100, 'peak2.gain': -1.5, 'peak2.q': 1.0, 'high.freq': 9000, 'high.gain': -1.0})
    plan = dict(copy.deepcopy(na.plan), lh=dict(na.plan['lh'], bass_lo=43, cap=69), cap=106,
                pedal={'flutter_to': 0.0, 'lift_ms': 90})
    return na.but(
        name='new-age-epiano',
        description='new-age piano on the 80s DX7 e-piano (ROM1 "E.PIANO 1", chorused, a chamber and a plate): the '
                    'new-age-piano composer and plan - a singable theme and a chorus hook over flowing broken '
                    'chords, one climax - with the left hand voiced higher, a softer round touch, the tine only at '
                    'the climax',
        feels=feels, band=band, plan=plan, album='Endless E-Piano')


NEW_AGE_EPIANO = _epiano_genre()

# ------------------------------------------------------------------------------------------------ orchestra (film)
# orchestra-film: the new-age composer (its cells, phrase plans, harmony, set draws, arrangement plan) written into the
# orchestral score of lines with functions and orchestrated per section (endless/orchestra.py, bandlib/orchestration.py,
# docs/ORCHESTRA_ENDLESS.md): every plan section names its orchestration plans {texture: weight} ('orch'); the piece's
# size per mood (plan['sizes']: chamber = strings, woodwinds, horns, harp, timpani; full = + trumpets, trombones, tuba,
# percussion, choir); played by orch.Score in the 'film' style on the film_orchestra band.

ORCH_CHAMBER = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons',
                'horns', 'harp', 'timpani')
ORCH_FULL = ORCH_CHAMBER + ('trumpets', 'trombones', 'tuba', 'percussion', 'choir')
_ORCH_DROP = ('harmonize', 'harm_share', 'cadenza')     # (the pianist's own keys: no orchestral meaning)
_ORCH_TEX = {
    # the orchestration plans per plan section (by name; a name in two layouts shares them)
    'intro': {'strings_pad': 1.0, 'harp_solo': 0.7, 'solo_pad': 0.6, 'chorale_winds': 0.4},
    'A1': {'solo_pad': 1.0, 'harp_solo': 0.7, 'cello_theme': 0.5, 'strings_pad': 0.4},
    'A2': {'strings_melody': 1.0, 'counter_strings': 0.8, 'cello_theme': 0.6, 'solo_pad': 0.4},
    'B1': {'strings_melody': 1.0, 'horn_ostinato': 0.7, 'counter_strings': 0.6, 'cello_theme': 0.4},
    'inter': {'chorale_winds': 1.0, 'harp_solo': 0.8, 'solo_pad': 0.6},
    'A3': {'counter_strings': 1.0, 'solo_pad': 0.7, 'cello_theme': 0.6, 'chorale_winds': 0.4},
    'build': {'horn_ostinato': 1.0, 'counter_strings': 0.6, 'strings_melody': 0.5},
    'climax': {'tutti': 1.0, 'tutti_lyrical': 0.9},
    'A4': {'solo_pad': 1.0, 'strings_melody': 0.5, 'chorale_winds': 0.5, 'strings_pad': 0.5},
    'coda': {'strings_pad': 1.0, 'solo_pad': 0.8, 'chorale_winds': 0.5, 'harp_solo': 0.4},  # (r2: one coda look)
}


def _orchestra_genre() -> 'Genre':
    na = NEW_AGE_PIANO
    plan = copy.deepcopy(na.plan)
    for k in ('play', 'touch_span', 'ornaments', 'end_styles', 'lh', 'pedal', 'cap'):
        plan.pop(k, None)
    secs = []
    for sd in plan['sections']:
        sd = {k: v for k, v in sd.items() if k not in _ORCH_DROP}
        sd['orch'] = dict(_ORCH_TEX[sd['name']])
        secs.append(sd)
    # every phrase a hairpin (the r2 gate: a section's held harmony notes all at one level - 'violins2' judged flat)
    plan.update(perform='orchestra', sections=secs, candidates=6, sizes={'chamber': ORCH_CHAMBER, 'full': ORCH_FULL},
                swell={1: 0.6, 2: 0.4})
    return na.but(
        name='orchestra-film',
        description='new-age / lyrical film orchestra: the new-age composer (a singable theme, a chorus hook, one '
                    'climax) written as a score of lines - melody, harmony, bass, counter-melody, ostinato, colour - '
                    'and orchestrated per section (a solo over a string pad, the violins singing, a cello theme, a '
                    'woodwind chorale, horns over an ostinato, the tutti climax) on the film orchestra',
        moods={'hopeful': {'feels': {'flowing': 2, 'bright': 2}, 'modes': {'major': 1},
                           'keys': {'major': ['D', 'F', 'G', 'Bb', 'C', 'Eb']}, 'tempo': 2, 'colour': 0.9,
                           'tritone': 0.0, 'energy': 0.75, 'size': {'full': 1.0, 'chamber': 0.4}},
               'longing': {'feels': {'gentle': 2, 'flowing': 2, 'waltz': 1}, 'modes': {'minor': 2, 'major': 1},
                           'keys': {'major': ['Eb', 'Ab', 'F'], 'minor': ['D', 'G', 'C', 'E', 'A', 'F']},
                           'tempo': -2, 'colour': 1.2, 'tritone': 0.0, 'energy': 0.35,
                           'size': {'chamber': 1.0, 'full': 0.6}},
               'epic': {'feels': {'bright': 2, 'flowing': 1}, 'modes': {'major': 1, 'minor': 1},
                        'keys': {'major': ['D', 'C', 'Bb', 'Eb'], 'minor': ['D', 'C', 'G']}, 'tempo': 0,
                        'colour': 1.0, 'tritone': 0.0, 'energy': 1.0, 'size': {'full': 1.0}},
               'pastoral': {'feels': {'flowing': 2, 'waltz': 2, 'gentle': 1}, 'modes': {'major': 1},
                            'keys': {'major': ['F', 'G', 'D', 'A', 'Bb']}, 'tempo': 0, 'colour': 0.9,
                            'tritone': 0.0, 'energy': 0.5, 'size': {'chamber': 1.0, 'full': 0.4}},
               'night': {'feels': {'gentle': 3, 'waltz': 1}, 'modes': {'minor': 1, 'major': 1},
                         'keys': {'major': ['Db', 'Ab', 'E'], 'minor': ['E', 'B', 'A', 'C#']}, 'tempo': -3,
                         'colour': 1.1, 'tritone': 0.0, 'energy': 0.15, 'size': {'chamber': 1.0}}},
        # judged as concert music (profile 'classical', -23..-16 LUFS): a lyrical score keeps its quiet A sections;
        # 'gain': dB on every role (the raw sections sit under the level the band is levelled for); 'master': the
        # song's master chain (a slow ride: the score's ~17 LU loudness range -> ~12); 'line_phrasing': every line's
        # phrase arc at least this deep (orch.Score phrasing: a horn / oboe solo is shaped like the violins')
        band={'preset': 'film_orchestra', 'profile': 'classical', 'loudness': (-24.0, -14.0), 'style': 'film',
              'gain': 8.0, 'master': 'master/film-lyrical', 'line_phrasing': 0.9, 'options': {'choir': 'oh'},
              # (the r2 / set1 gate: a crash peaking 7-10 dB under the loudest part; set1's tracks: the choir and the
              # clarinets' inner parts as loud as the climax's violins)
              'trims': {'percussion': -10.0, 'choir': -6.0, 'clarinets': -3.0}},
        plan=plan,
        titles={'adj': ['Distant', 'Golden', 'Silent', 'Northern', 'Endless', 'Hidden', 'Open', 'Falling', 'Last',
                        'Bright', 'Quiet', 'Rising', 'Lost', 'First', 'Wide'],
                'noun': ['Horizons', 'Rivers', 'Skies', 'Shores', 'Lanterns', 'Fields', 'Wings', 'Mountains',
                         'Harbours', 'Meadows', 'Voyages', 'Stars', 'Gardens', 'Bridges'],
                'time': ['the Morning', 'the Dawn', 'Autumn', 'the Sea', 'Winter', 'the Night', 'Home', 'Spring',
                         'the Valley', 'the Light', 'Evening'],
                'shapes': ['{noun} of {time}', '{adj} {noun}', 'Across {time}', 'The {adj} {noun}',
                           '{noun} to {time}', 'Toward {time}', '{adj} {noun} of {time}', 'Theme from {time}'],
                'suffix': {'': ''}},
        album='Endless Orchestra', style='orchestra')


ORCHESTRA_FILM = _orchestra_genre()

GENRES = {g.name: g for g in (JAZZ_PIANO, JAZZ_TRIO, NEW_AGE_PIANO, CLASSICAL_PIANO, LOFI_PIANO, NEW_AGE_EPIANO,
                               ORGAN, ORCHESTRA_FILM)}
STYLES = {'jazz': 'jazz-piano', 'new-age': 'new-age-piano', 'classical': 'classical-piano', 'lofi': 'lofi-piano'}
"""`endless piano --style S`: the genre of each piano style ('mix': the set plan alternates them)."""

# ------------------------------------------------------------------------------------------------ the score
# composer.score(song, tune): one number 0-100 from the notes (no audio) - per style a table {metric: (lo, hi,
# weight, hard[, unit])} over composer.score_metrics(): inside lo..hi a metric scores 1, outside 1 / (1 + d^2), d the
# distance in units (default: the range's width); the score is the weighted mean x 100, a HARD metric outside its
# range scales it into 0 .. SCORE_HARD_CAP x its sub-score. The runner's best-of-N (endless --candidates N) renders the
# best.

SCORE_HARD_CAP = 60.0
"""The most a tune with a broken hard rule can score (x the rule's sub-score; its mean scaled into that)."""

_SCORE_JAZZ = {
    # -- hard: what no reference does (ROUNDS.md rounds 1-6)
    'wraps': (0, 0, 2, True, 1),            # octave wraps in the solo's fast lines (round 1)
    'over_chord': (0, 0, 2, True, 1),       # a solo bar repeated verbatim over another chord (round 1)
    'cell_loop': (0, 0, 2, True, 2),        # one bar looped literally over changing chords (round 6)
    'sil_cad': (0, 0, 2, True, 1),          # silent solo bars at a cadence / turnaround (round 6)
    'both_mid': (0, 1, 1, True, 1),         # body bars neither hand strikes (round 6)
    'clash_total': (0, 5, 1, True, 2),      # theory.clash on strong / long notes (pro2 1-2, pro 0-5)
    'mel_issues': (0, 4, 1, True, 2),       # the lead sheet's melody_issues (pro 0-4)
    'intro_copy': (0, 0, 1, True, 1),       # the intro / tag a copy of the form's bars (round 2)
    'tag_copy': (0, 0, 1, True, 1),
    'isolated': (0, 0, 1, True, 1),         # a one-off solo reharm the head out does not play (round 2)
    # -- round 6 / 7 (the pro2 references: waltz / blues / latenight / bossa)
    'solo_att': (4.3, 6.2, 2, False, 1),    # solo right-hand attacks per bar
    'dens_ratio': (1.15, 1.6, 2, False),    # solo / head density
    'sil_ch': (0, 1, 2, False, 1),          # silent solo bars per chorus
    'ph_len': (12, 46, 2, False, 6),        # solo phrase length (beats)
    'ph_sd': (8, 52, 1, False, 6),          # its spread (heavy-tailed phrases)
    'long16': (0.33, 1, 1, False, 0.33),    # choruses with a 16+-beat line
    'upbeat': (0.5, 0.9, 1, False, 0.15),   # phrases starting off the beat
    'eighths': (0.65, 0.8, 1, False, 0.1),  # 8th steps inside phrases
    'dir_chg': (0.28, 0.42, 2, False, 0.06),  # direction changes per step
    'leap5': (0.03, 0.1, 2, False, 0.04),   # leaps of 5+ semitones
    'rep_p': (0, 0.02, 1, False, 0.015),    # repeated pitches
    'vel_p10': (50, 62, 1, False, 5),       # the right hand's soft end
    'end_db': (-5, -2.2, 1, False, 1.5),    # tag + ending under the body (dB of note energy)
    'final_vel': (45, 55, 1, False, 5),     # the final chord's softest note
    'after_final': (0, 2, 0.5, False, 1),
    'top_solo_end': (1, 1, 2, False, 1),    # the piece's highest note in the solo's last 16 bars
    'top_over_head': (2, 5, 1, False, 2),
    'top_vel': (100, 124, 1, False, 8),
    'out_below': (1, 1, 1, False, 1),       # nothing later as high
    'head_centre': (77, 80, 2, False, 2),   # the head's median pitch (MIDI)
    'head_span': (10, 14, 1, False, 2),
    'head_vel': (67, 81, 2, False, 5),      # the head's touch
    'head_rise8': (3.5, 14, 1, False, 3),
    'a_ends': (1, 1, 1, False, 1),          # A1 / A2 end differently
    'hook_head': (4, 12, 1, False, 2),      # the hook's shape restated in the head (round 6: heads without a hook)
    'reharm_col': (0.5, 1, 1, False, 0.3),  # the head out's substitutes met by a colour tone
    'lh_bare': (0, 0, 1, False, 1),         # bars of bare left-hand roots
    'lh_alt': (0, 5, 0.5, False, 2),
    'lh_jump': (0, 0, 1, False, 1),
    'frame_hold': (1, 2, 1, False, 1),      # one top pitch over the frame's chords (a pad)
    'scoops': (0, 1, 0.5, False, 1),
    'lick_rep': (0, 0, 1.5, False, 1),      # licks recurring in the solo (round 7: a cell 4x within 4 bars)
    'vel': (0, 9, 1, False, 4),             # the solo's top velocity over the head (round 1: a plateau)
    'solo_db2': (1, 2.5, 1, False, 1),      # the solo from its 2nd chorus over the head (dB)
    # -- round 7 (composer.tells: _tells_r7; pro2 in brackets)
    'lick_near': (0, 1, 1, False, 1),       # 5-note licks recurring within 4 bars, per 32 solo bars (0 / 0 / 0 / 2)
    'run16': (0, 1, 1, False, 1),           # 16th-motion solo bars per 32 (0; a bossa solo in 16ths)
    'head_one': (0, 0.2, 1, False, 0.05),   # one-note head bars outside the landings (0-0.19)
    'bridge_one': (0, 0.25, 1, False, 0.08),  # ... in the bridge (a bridge without its own idea; 0-0.25)
    'head_quote': (0, 0, 0.5, False, 1),    # 6-attack windows of the head played verbatim in the solo (0)
    'vel_pitch': (0.65, 0.85, 1, False, 0.08),  # velocity following pitch step by step (pro2 0.74-0.85; round 7:
                                            # 'too much', round 8: the composed follow it more - r 0.52-0.71)
    'climb_step': (4, 24, 0.5, False, 8),   # the largest velocity step of the 4 bars into the top (10-33)
    'lh_over': (0, 0.11, 1, False, 0.05),   # bars where the left hand is louder than the melody (0-0.11)
    # -- rounds 1-5
    'head_5gram': (0.2, 0.51, 1, False, 0.1),   # a theme restated
    'solo_entropy': (1.45, 2.0, 1, False, 0.2),
    'dyn_range': (4.8, 6.6, 1.5, False, 1),     # the note-energy range (dB)
    'peak_x': (0.62, 0.78, 1, False, 0.06),     # the loudest 4 bars (0..1 of the piece)
    'top_x': (0.62, 0.78, 0.5, False, 0.06),
    'cell_max': (0.15, 0.33, 0.5, False, 0.05),
    'quarter_runs': (0, 2, 0.5, False, 1),
    'figure_repeats': (0, 0, 1, False, 1),
    'harmonized_fast': (0, 0.08, 0.5, False, 0.04),
    'vel_onoff': (-1, 5.5, 0.5, False, 2),
    'rep_notes': (0, 0.03, 0.5, False, 0.02),
    'circle': (0.19, 0.26, 1, False, 0.03),     # the head's phrases circling one pitch
    'circle_max': (0.25, 0.33, 0.5, False, 0.04),
    'onbeat_ct': (0.69, 0.85, 1, False, 0.05),  # beats on chord tones
    'guide_land': (0.49, 0.75, 0.5, False, 0.1),
    'head_guide': (0.24, 0.42, 1, False, 0.06),
    'head_arp': (0.12, 0.35, 0.5, False, 0.08),
    'a_range': (13, 18, 1, False, 2),
    'ct_run5': (1, 3.6, 0.5, False, 1),
    'rev_cells': (0, 0.9, 0.5, False, 0.5),
    'arp5': (0, 0.07, 0.5, False, 0.05),
    'starts_on_one': (0, 0.1, 0.5, False, 0.1),
    'solo_end': (1, 1, 0.5, False, 1),
    'mel_style': (0, 1, 1, False, 1),           # the lead sheet's _style_issues
    # -- breath (the user's r6 'monotone line'; pro2 in brackets) and the body
    'quiet1': (0.15, 0.35, 1.5, False, 0.05),   # right hand quiet for a beat+ (0.16-0.35)
    'phrase_rests': (0.48, 0.88, 1, False, 0.1),
    'att_cv4': (0.16, 0.4, 0.5, False, 0.08),
    'body_heard': (0.15, 0.4, 0.5, False, 0.1),
}
"""jazz: the pro2 references' ranges (ROUNDS.md 'After round 6', re-measured with score_metrics), widened to the pro
set where a judge did not name it as a tell; weights: round 6 / 7 tells 2, older rounds 1, details 0.5."""

_SCORE_SING = {
    'climax_single': (1, 1, 1, False, 1),       # one top note (soft: letters-to-the-morning strikes its top twice)
    'mel_issues': (0, 0, 1, True, 2),           # the lead sheet's melody_issues
    'climax_x': (0.6, 0.85, 2, False, 0.1),     # the one climax ~60-80 % in (recipes/classical.md: golden section)
    'peak_x': (0.6, 0.85, 1.5, False, 0.08),    # the loudest 4 bars
    'phrase_rests': (0.75, 1, 2, False, 0.15),  # a breath at the phrase ends (letters-to-the-morning 1.0)
    'quiet1': (0.25, 0.35, 2, False, 0.05),     # (letters 0.30)
    'att_cv4': (0.08, 0.25, 1, False, 0.05),    # (letters 0.12)
    'rest_bar': (1.5, 3.5, 1, False, 1.5),      # rests of a bar+ per 32 bars (letters 2.3)
    'long_share': (0.15, 0.25, 1, False, 0.05),  # (letters 0.19)
    'ph_vel': (7, 13, 1.5, False, 2.5),         # phrase-to-phrase velocity change (letters 9.6)
    'ph_reg': (2, 4.5, 1, False, 1),            # ... register (letters 3.0)
    'ph_den': (0.15, 0.45, 0.5, False, 0.1),
    'dyn_range': (8, 12.5, 1, False, 2),        # (letters 11.2)
    'hook': (3, 8, 1.5, False, 2),              # the hook's statements in the played top line
    'hook_sections': (3, 7, 1, False, 1),
    'hook_tag': (1, 3, 0.5, False, 1),
    'lh_distinct': (4, 9, 1, False, 2),         # left-hand figures per section
    'orn32': (0, 6, 0.5, False, 3),             # (letters 4.6)
    'att_bar': (3.2, 4.5, 0.5, False, 0.5),     # right-hand attacks per bar (letters 3.9)
    'body_heard': (0.1, 0.5, 0.5, False, 0.15),  # faster where louder (letters 0.25-0.28)
    'arc_pitch_r': (0.3, 1, 1, False, 0.3),     # the phrases' register follows the plan
    'mel_style': (0, 1, 1, False, 1),
}
"""new-age: letters-to-the-morning (the user's model) and recipes/classical.md's one climax."""

_SCORE_NEWAGE = dict(
    _SCORE_SING,
    # the four composed references (letters-to-the-morning, pro-newage-rain / -hopeful / -waltz) re-measured: the
    # breath ranges widened from letters alone to the four
    quiet1=(0.22, 0.33, 2, False, 0.05), rest_bar=(0.5, 3.0, 1, False, 1.5), att_bar=(2.9, 4.5, 0.5, False, 0.5),
    long_share=(0.15, 0.28, 1, False, 0.05), phrase_rests=(0.7, 1, 2, False, 0.15), ph_vel=(8, 13, 1.5, False, 2.5),
    # -- blind round N0 (composer.newage_tells; the references in brackets)
    climax_copy=(0, 0.25, 2, False, 0.2),       # the climax = an earlier section bar for bar (0 / 0 / 0 / 0)
    block_copy=(0, 0.25, 2, False, 0.1),        # body sections repeating earlier ones (0.06-0.24)
    rep_pitch=(0, 0.05, 2, False, 0.03),        # repeated-pitch melody steps (0.017-0.046)
    final_jump=(-5, 8, 1, False, 4),            # the final chord's top over the last melody note (0-8)
    final_top=(0, 0, 1, False, 1),              # the final chord holds the piece's highest note (0)
    frame_pitches=(8, 16, 1, False, 3),         # distinct pitches in intro / interlude / coda (9-13)
    chords_n=(18, 36, 1, False, 4),             # distinct chords (19-33)
    chord_rep4=(0, 0.27, 1, False, 0.1),        # 4-chord windows heard before (0.06-0.26)
    ret_tonic=(0, 0, 1, False, 1),              # the last return closes on the tonic (0: deceptive)
    orn32=(0.3, 6, 0.5, False, 2),              # ornaments per 32 bars (0.4-4.6)
    # -- blind round r1
    climax_lift=(8, 16, 1.5, False, 2),         # the climax's mean top line over A1's, semitones (9.7-14)
    peak_holes=(0, 0, 1.5, False, 1),           # bars without a right-hand onset in the build + climax (0)
    long_holds=(0, 1, 1, False, 1),             # right-hand top notes held 4+ beats before the final chord (0)
    # -- blind round r2
    a1_copy=(0, 0.3, 1.5, False, 0.1),          # later bars restating A1's same bar at any transposition (0.2-0.29)
    # -- blind round r3
    climax_chart=(0, 0.5, 1.5, False, 0.2),     # climax bars on an earlier section's same chords (0-0.5)
    ph_vspread=(22.5, 30, 1, False, 2),         # top-line velocity p90 - p10 inside a 4-bar phrase (23.1-24.8)
    # -- blind round r4
    vel_jump12=(0, 0.27, 1, False, 0.08),       # bar-to-bar velocity jumps of 12+ inside a section (0.18-0.29)
)
"""new-age: letters-to-the-morning (the user's model) + the three pro-newage references, recipes/classical.md's one
climax, the new-age blind rounds' tells (songs/_blind/ROUNDS.md "New-age")."""
# -- reference set 2 (ROUNDS.md "Reference set 2"; round r6): the ranges re-measured on all 12 hand-written references
# (letters + rain / hopeful / waltz + skylight / morning / longing / lantern / tide / snowfield / homecoming /
# embers: measure_newage.py --set2) - min..max of the twelve, the weights and units as before. The old four alone
# made placement / lift / density choices of three pieces a window (set 2 scored 94.3, the generator's mean); a
# climax by key change or swell, a climax before the return, variations and a passacaglia are in the range now. The
# table rewards what the references share; the SET's spread is the set plan's job (plan['set'], set_plan).
_SCORE_NEWAGE.update(
    climax_x=(0.47, 0.86, 2, False, 0.1), peak_x=(0.46, 0.86, 1.5, False, 0.08),
    phrase_rests=(0.64, 1, 2, False, 0.15), quiet1=(0.2, 0.32, 2, False, 0.05), att_cv4=(0.1, 0.36, 1, False, 0.05),
    rest_bar=(0, 5.1, 1, False, 1.5), long_share=(0.12, 0.27, 1, False, 0.05), ph_vel=(8.4, 15.9, 1.5, False, 2.5),
    ph_reg=(2.5, 4.3, 1, False, 1), ph_den=(0.15, 0.51, 0.5, False, 0.1), dyn_range=(8, 12, 1, False, 2),
    orn32=(0.4, 5.5, 0.5, False, 2), att_bar=(2.6, 4.4, 0.5, False, 0.5), body_heard=(0.07, 0.4, 0.5, False, 0.15),
    climax_copy=(0, 0.1, 2, False, 0.2), block_copy=(0, 0.24, 2, False, 0.1), final_jump=(-2, 8, 1, False, 4),
    frame_pitches=(5, 16, 1, False, 3), chords_n=(19, 33, 1, False, 4), chord_rep4=(0, 0.26, 1, False, 0.1),
    ret_tonic=(0, 1, 1, False, 1), climax_lift=(1.6, 15, 1.5, False, 2), a1_copy=(0, 0.29, 1.5, False, 0.1),
    climax_chart=(0, 0.62, 1.5, False, 0.2), ph_vspread=(21, 27, 1, False, 2), vel_jump12=(0.17, 0.36, 1, False, 0.08))
# -- the bloom (HUMAN_FEEDBACK 2026-10-15, composer.bloom_tells; plan['bloom']): not the references' ranges - the
# hand-written pieces never push forward (tempo_push 1.0) - but the user's ask, measured on the generator before /
# after (docs/PIANIST_RULES.md "The bloom"): before tempo_push 1.0, climax_tempo 0.88-0.94, rh_peak_den 0.9-1.3,
# flow32 1.4-5.6
_SCORE_NEWAGE.update(
    tempo_push=(1.03, 1.12, 1.5, False, 0.03),     # the bloom's section mean tempo over A1's
    climax_tempo=(0.93, 1.06, 1, False, 0.04),     # the climax section's over A1's (broad at its peak only)
    rh_peak_den=(1.6, 3.2, 1, False, 0.4),         # right-hand onsets per beat in the densest 4 bars
    flow32=(4, 14, 0.5, False, 2),                 # figures through both hands over two octaves per 32 bars
    orn32=(0.4, 7, 0.5, False, 2))                 # (the bloom's 16ths under the melody's rubato count: 5.5 -> 7)

_SCORE_ORGAN = {
    # the organ tells (endless/organ.py organ_metrics), ranges measured on the four songs/pro-organ-* references and
    # sharpened by the blind organ rounds (songs/_blind/ROUNDS.md "Organ"): voice leading, cadences, the pedal,
    # registration changes and the church's ring, the touch; the end on the tonic (hard), no verse copied bar for bar,
    # the climax late, the pedal under the hands
    'par58': (0.0, 1.0, 2, False, 4.0), 'inner_leap': (0.0, 0.12, 2, False, 0.05),
    'top_leap': (0.0, 0.04, 1, False, 0.03), 'cad_kinds': (2, 4, 1.5, False, 1),
    'cad_auth': (0.2, 0.6, 1, False, 0.15), 'pedal_idle': (0.0, 0.2, 1.5, False, 0.1),
    'reg_sets': (2, 6, 2, False, 1), 'reg_run_s': (30, 100, 2, False, 30), 'reg_min': (0.3, 1.5, 1, False, 0.5),
    'ring_min': (1.0, 4.0, 0.5, False, 0.5), 'legato': (0.3, 0.9, 0.5, False, 0.15),
    'gap_ms': (80, 230, 1, False, 40), 'time_sd_ms': (20, 50, 1, False, 8), 'chord_ms': (0, 5, 1, False, 3),
    'orn_min': (0, 5, 1, False, 1.5), 'rest_share': (0.0, 0.12, 1, False, 0.04), 'textures': (5, 10, 1, False, 1),
    'dur_min': (2.3, 4.0, 1, False, 1), 'bar_copy': (0.0, 0.2, 2, False, 0.05), 'end_tonic': (1, 1, 3, True, 1),
    'top_at': (0.45, 1.0, 1.5, False, 0.1), 'pedal_high': (0.0, 0.3, 1, False, 0.1),
    'rep_run': (1, 3, 1.5, False, 1),
}

_SCORE_ORCHESTRA = dict(
    # the melodic / harmonic layer: the new-age composer's ranges, measured on the score's reduction
    # (endless/orchestra.py MELODIC: the melody line as the right hand)
    {k: v for k, v in _SCORE_NEWAGE.items() if k in ('climax_x', 'peak_x', 'phrase_rests', 'rest_bar', 'ph_reg',
                                                     'mel_issues', 'climax_copy', 'block_copy', 'rep_pitch',
                                                     'chords_n', 'chord_rep4', 'climax_lift', 'a1_copy',
                                                     'climax_chart', 'arc_pitch_r', 'climax_single')},
    # the orchestration (bandlib/orchestration.metrics), from the four hand-written references songs/pro-orch-*
    # (epic / hopeful / longing / night: the measured values in the comments, ROUNDS.md "Orchestra")
    range_out=(0, 0, 3, True, 0.5),          # notes outside their role's range (per 100)              0 (0.09)
    sweet_mel=(0.88, 1.0, 1.5, False, 0.1),  # the line notes in their role's sweet spot                0.93-1.0
    gap_hi=(0, 0.25, 1, False, 0.1),         # gaps over an octave between neighbours above C4         0.01-0.23
    low_thirds=(0, 0.07, 1, False, 0.05),    # thirds between the two lowest voices under C3           0-0.07
    mel_db=(1.0, 6.0, 1.5, False, 1.5),      # the line over the loudest accompaniment (dB)             1.3-1.7
    colour_chg=(0.7, 1.0, 1.5, False, 0.2),  # the lines' roles change at a section boundary           0.86-1.0
    tutti=(0.08, 0.3, 1, False, 0.08),       # bars with 75 %+ of the roles                             0.15-0.27
    coda_thin=(0.3, 0.8, 1, False, 0.15),    # the last section's roles / the most in a section        0.5-0.73
    roles_bar=(6, 10, 1, False, 2),          # roles sounding per bar                                  6.7-8.9
    roles_sd=(2.0, 4.5, 1, False, 0.8),      # the texture breathes (roles per bar spread)              2.4-3.7
    dbl_share=(0.55, 0.9, 1, False, 0.15),   # line notes doubled at the unison / octave               0.72-0.85
    dbl_low=(0, 0.3, 0.5, False, 0.1),       # a melody doubled into the bass register                 0.05-0.3
    o_peak_x=(0.6, 0.85, 1.5, False, 0.08),  # the loudest 4 bars (all the orchestra's notes)           0.68-0.71
    dyn_rng=(12, 21, 1, False, 3),           # the note-energy range (2-bar windows, dB)                12.8-19.8
    db_bar_sd=(6.5, 11, 1, False, 1.5),      # the bar-to-bar level spread (dB)                         7.9-10
    textures=(6, 12, 1, False, 1))           # distinct role sets over the sections                    8-10           # distinct role sets over the sections
"""orchestra: the new-age composer's melodic ranges on the reduction + the orchestration metrics (endless/orchestra.py
orchestra_metrics; docs/ORCHESTRA_ENDLESS.md section 6)."""

SCORES = {
    'orchestra': _SCORE_ORCHESTRA,
    'organ': _SCORE_ORGAN,
    'jazz': _SCORE_JAZZ,
    'new-age': _SCORE_NEWAGE,
    # PROVISIONAL (no composed reference of the generated kind: the Chopin / Satie etudes are different pieces -
    # 12/8 fioriture, a climax at the start; ranges from the demos + recipes/classical.md): denser ornaments, a sparser
    # line, a wider phrase-to-phrase contrast
    'classical': dict(_SCORE_SING, att_bar=(2.0, 3.5, 0.5, False, 0.5), orn32=(0, 10, 0.5, False, 4),
                      climax_x=(0.6, 0.78, 2, False, 0.08), peak_x=(0.6, 0.78, 1.5, False, 0.08),
                      rest_bar=(1.5, 5, 1, False, 1.5), long_share=(0.15, 0.35, 1, False, 0.05),
                      lh_distinct=(3, 8, 1, False, 2), quiet1=(0.25, 0.45, 2, False, 0.05),
                      att_cv4=(0.12, 0.4, 1, False, 0.06), dyn_range=(7, 12, 1, False, 2)),
    # PROVISIONAL (no reference; the demos + the genre: a hum of 2-4 notes per two bars over a steady kit): sparse,
    # long notes, a narrow loudness range, a resting left hand; no body measure (the kit keeps strict time)
    'lofi': {k: v for k, v in dict(
        _SCORE_SING, quiet1=(0.4, 0.6, 2, False, 0.05), att_bar=(1.6, 2.8, 0.5, False, 0.4),
        orn32=(0, 3, 0.5, False, 2),
        dyn_range=(3.5, 7, 1, False, 1.5), long_share=(0.3, 0.55, 1, False, 0.08), rest_bar=(3, 8, 1, False, 2),
        ph_vel=(3, 8, 1, False, 2), lh_distinct=(3, 7, 1, False, 2), lh_still=(0.2, 0.6, 0.5, False, 0.15),
        att_cv4=(0.05, 0.3, 1, False, 0.05)).items() if k != 'body_heard'},
}


def get(name: str) -> Genre:
    if name not in GENRES:
        raise ComposeError(f"unknown endless genre {name!r}; genres: {', '.join(GENRES)}")
    return GENRES[name]
