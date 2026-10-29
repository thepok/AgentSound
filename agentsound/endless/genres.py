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
                'octave_half', 'bass', 'fill', 'turn', 'reharm', 'layouts', 'harm_share', 'vary', 'key', 'close'}
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
SET_KEYS = ('layout', 'climax', 'shift', 'hook', 'open', 'build', 'opening', 'intro', 'anthem', 'tag', 'arrival',
            'peak', 'big', 'second')
ARRANGE_CHOICES = {'climax': {'lift', 'theme', 'step', 'climb', 'grow'}, 'cadence': {'home', 'vi', 'IV'},
                   'close': {'keep', 'I', 'vi', 'IV', 'bVII', 'ii'}, 'octave_half': {0, 1},
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
                # (the symphonic composer harmonizes in a church mode too - round o2's modal colours; the piano's
                # harmony blocks are major / minor)
                if mode not in BLOCKS and not (self.plan.get('perform') == 'symphony' and mode in MODAL):
                    bad(f"mood {name!r}: mode must be major / minor (a 'symphony' plan: or {' / '.join(MODAL)}), "
                        f"got {mode!r}")
                if not m['keys'].get(mode):
                    bad(f"mood {name!r}: no keys for mode {mode!r}")
                for k in m['keys'][mode]:
                    chord(k)                                  # a valid root name
        for name, f in self.feels.items():
            lo, hi = f['tempo']
            if not 30 <= lo <= hi <= 300:
                bad(f"feel {name!r} tempo {f['tempo']!r} must be 30..300")
            if self.plan.get('perform') == 'symphony':     # (its own composer's feels: endless/symphony.py checks)
                continue
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
        if not isinstance(self.plan.get('grow_aug', 0.0), (int, float)) or not 0 <= self.plan.get('grow_aug', 0.0) <= 1:
            bad("plan['grow_aug']: a chance 0..1 (the grow climax's augmented first statement)")
        tx = self.plan.get('texture')
        if tx is not None:
            from .perform import TEXTURE_ROLES
            if not isinstance(tx, dict) or set(tx) - set(TEXTURE_ROLES) - {'min_dur', 'move', 'connect', 'long'} or any(
                    not isinstance(w, dict) or any(not (isinstance(k, tuple) and len(k) == 2 and k[0] in (0, 1, 2, 3)
                                                        and 0 <= k[1] <= 1) or x < 0 for k, x in w.items())
                    for r, w in tx.items() if r in TEXTURE_ROLES):
                bad("plan['texture']: {role (perform.TEXTURE_ROLES): {(voices 0-3, share 0..1): weight}, 'min_dur', "
                    "'move' / 'connect': {value: weight}, 'long': the share for the notes held 1.5 beats+}")
            if tx is not None and not 0 <= tx.get('long', 0.0) <= 1:
                bad("plan['texture']['long']: a share 0..1 (romantic.harmonize long_share)")
        ln = self.plan.get('line')
        if ln is not None and (not isinstance(ln, dict) or set(ln) - {'keep', 'step', 'accent', 'range', 'stretch'}):
            bad("plan['line']: {'keep', 'step', 'accent', 'range', 'stretch'} (romantic.Score.perform line=)")
        ga = self.plan.get('grow_at')
        if ga is not None and (not isinstance(ga, dict) or not ga or any(not 0.2 <= k <= 0.85 or w < 0
                                                                         for k, w in ga.items())):
            bad("plan['grow_at']: {where the grown climax climbs, 0.2..0.85 of its units: weight}")
        if not isinstance(self.plan.get('candidates', 8), int) or self.plan.get('candidates', 8) < 1:
            bad("plan['candidates'] (endless best-of-N) must be a whole number >= 1")
        hd = self.melody.get('head')
        if hd is not None and (not isinstance(hd, dict) or set(hd) != {'leap', 'at'} or
                               any(not 3 <= k <= 7 for k in hd['leap']) or any(k not in (1, 2, 3) for k in hd['at'])):
            bad("melody['head']: {'leap': {scale steps 3..7: weight}, 'at': {the head's move 1..3: weight}}")
        rs = self.melody.get('restate')
        if rs is not None and (not isinstance(rs, dict) or not rs or
                               any(not isinstance(k, int) or k < 1 or w < 0 for k, w in rs.items())):
            bad("melody['restate']: {2-bar units a later A restates (>= 1): weight}")
        if not isinstance(self.plan.get('candidate_tries', 1), (int, float)) or \
                not 1 <= self.plan.get('candidate_tries', 1) <= 4:
            bad("plan['candidate_tries']: seeds per best-of-N candidate, 1..4 (rejected seeds replaced; default 1)")
        perf = self.plan.get('perform', 'jazz')
        if perf not in ('jazz', 'piano', 'organ', 'orchestra', 'symphony'):
            bad("plan['perform'] must be 'jazz' (head / solo / head out), 'piano' (plan['sections']), 'organ' "
                "(plan['arrangements']: endless/organ.py), 'orchestra' (a piano plan orchestrated: "
                "endless/orchestra.py) or 'symphony' (the symphonic composer: endless/symphony.py)")
        if perf == 'symphony':
            from .symphony import validate_plan as _vs
            _vs(self, bad)
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
            ce = self.plan.get('ceiling')
            if ce is not None and (not isinstance(ce, dict) or set(ce) - {'line', 'peak', 'sung'} or
                                   any(not isinstance(v, int) or not 72 <= v <= 108 for v in ce.values())):
                bad("plan['ceiling']: {'line': top of an octave-up section, 'peak': top of the climax, 'sung': top of "
                    "the theme sung an octave up at the climax (perform._anthem)} (MIDI 72..108)")
            if not 0 <= self.plan.get('accent_over', 12) <= 24:
                bad("plan['accent_over']: an accent's velocity over the right hand's cap at most, 0..24 (default 12)")
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
                            or any(not 0 <= x <= 1 for x in bl['carry']) or any(not 0.7 <= x < 1 for x in bl['rit'])                             or not 0 <= bl['weave'] <= 1 or set(bl['texture']) - {'weave', 'pulse', 'none'}:
                        bad("plan['bloom']: push 1..1.2, reach 0..1, carry 0..1, rit 0.7..1 (x the tempo), weave 0..1")
            sg = self.plan.get('signature')
            if sg is not None:
                why = _signature_problem(sg)
                if why:
                    bad(f"plan['signature']: {why} (genres._NA_SIGNATURE)")
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
                if k == 'opening':
                    if not isinstance(w, dict) or any(not isinstance(wm, dict) or not wm or any(x < 0 for x in
                                                                                             wm.values())
                                                      for wm in w.values()):
                        bad("plan['set']['opening']: {cell family: {motif cell: weight >= 0}}")
                    continue
                if k in ('hook', 'open', 'build'):
                    blocks = self.harmony.get('blocks') or {}
                    if not isinstance(w, dict) or any(m not in blocks or not isinstance(wm, dict) or not wm
                                                      or set(wm) - set(blocks[m].get(k) or {})
                                                      or any(x < 0 for x in wm.values()) for m, wm in w.items()):
                        bad(f"plan['set'][{k!r}]: {{mode: {{a harmony['blocks'][mode][{k!r}] block: weight >= 0}}}}")
                    continue
                if k == 'intro':
                    intros = self.harmony.get('intros') or {}
                    if not isinstance(w, dict) or any(m not in intros or not isinstance(wm, dict) or not wm
                                                      or set(wm) - set(intros[m]) or any(x < 0 for x in wm.values())
                                                      for m, wm in w.items()):
                        bad("plan['set']['intro']: {mode: {a harmony['intros'][mode] vamp: weight >= 0}}")
                    continue
                if k not in SET_KEYS or not isinstance(w, dict) or not w or any(x < 0 for x in w.values()):
                    bad(f"plan['set'][{k!r}]: one of {', '.join(SET_KEYS)} -> {{choice: weight >= 0}}")
                if k == 'climax' and set(w) - ARRANGE_CHOICES['climax']:
                    bad(f"plan['set']['climax']: choices of {sorted(ARRANGE_CHOICES['climax'])}")
                if k == 'shift' and any(not isinstance(x, int) or abs(x) > 7 for x in w):
                    bad("plan['set']['shift']: register shifts in semitones, -7..7")
                if k == 'anthem':
                    from .perform import ANTHEMS
                    if set(w) - set(ANTHEMS):
                        bad(f"plan['set']['anthem']: choices of {', '.join(ANTHEMS)} (perform._anthem)")
                if k == 'second':
                    from .perform import ANTHEM_SECOND
                    if set(w) - set(ANTHEM_SECOND):
                        bad(f"plan['set']['second']: choices of {', '.join(ANTHEM_SECOND)} (perform._anthem)")
                if k == 'arrival':
                    from .perform import ARRIVALS
                    if set(w) - set(ARRIVALS):
                        bad(f"plan['set']['arrival']: choices of {', '.join(ARRIVALS)} (perform._arrive)")
                if k == 'tag' and set(w) - set(TAG_KINDS):
                    bad(f"plan['set']['tag']: the coda's approach, choices of {', '.join(TAG_KINDS)}")
                if k == 'peak' and any(not isinstance(x, int) or not 0 <= x <= 7 for x in w):
                    bad("plan['set']['peak']: semitones under plan['ceiling']['sung'], 0..7")
                if k == 'big':
                    from ..pianist import FIGURES as _F
                    if set(w) - set(_F):
                        bad(f"plan['set']['big']: pianist.FIGURES names (the climax's left hand)")
            for sd in secs:
                extra = set(sd) - own_keys
                if extra or 'name' not in sd or ('part' in sd) == ('frame' in sd):
                    bad(f"plan section {sd!r}: a name, a 'part' (a form part) or a 'frame' (intro / tag), keys "
                        f"{', '.join(sorted(SECTION_KEYS))}")
                for f in forms:
                    if 'part' in sd and sd['part'] not in FORMS[f]['parts']:
                        bad(f"plan section {sd['name']!r}: part {sd['part']!r} is not in form {f!r}")
                for k in ('bars', 'tail', 'cadence', 'climax', 'octave_half', 'bass', 'fill', 'turn', 'close'):
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
        for k in ('intro', 'tag', 'end') if perf != 'symphony' else ():     # (the symphony: its layouts)
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
        if not 0.0 <= a['set'].get('feel_noise', 0.04) <= 2.0 or not 0.0 <= a['set'].get('tempo_spread', 0.0) <= 1.0:
            bad("arc set['feel_noise'] 0..2 (the dice on a feel's distance), ['tempo_spread'] 0..1")
        if not isinstance(a['set'].get('feel_max', 1), int) or a['set'].get('feel_max', 1) < 1:
            bad("arc set['feel_max'] must be a number of tunes (no feel more often in a set)")
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
            # (round g9, four judges: JKGC's B1 Am-F-C-G twice, "the generic pop loop" - every diatonic hook block
            # now goes somewhere: a secondary dominant into its target (II7 -> V, III7 -> vi), a borrowed bVI / bVII)
            'hook': {'axis': 'VIm IVM IM V@3 VIm IVM II7@3 Vsus4:0.5 V:0.5',
                     'IV_V_iii_vi': 'IVM V IIIm VIm IVM V@3 IVm6 V',
                     'IV_I3': 'IVM I@3 VIm V IVM bVIIM IM:2',
                     'vi_V3_IV': 'VIm V@3 IVM III7 VIm IM@3 IVM V',
                     'IV_III7': 'IVM V III7@3 VIm IVM I@3 IIm7 V',
                     # (round r3: two pieces in one key drew one chorus chart - a wider bank, its halves apart)
                     'IV_iv_vi': 'IVM IVm6 IM@3 VIm IIm7 V@3 VIm V',
                     'ii_iii_IV': 'IIm7 IIIm7 IVM V VIm bVIM bVIIM IM',
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
            'hook': {'VI_VII_III': 'bVIM bVII7 bIIIM Im bVIM bVII IVm Vsus4:0.5 V:0.5',
                     'III_VII': 'bIIIM bVII bVIM I7@3 IVm bVIM Vsus4 V',
                     'iv_VII_III_VI': 'IVm7 bVII bIIIM bVIM IIm7b5 V@3 Im V',
                     'VI_III_iv_V': 'bVIM bIIIM IVm7 V@3 bVIM bVII II7@3 V',
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
                         'descend': ('I V@3 VIm7 I@5', 0.5), 'ii_V': ('IIm7 V7@3 IIm7 V7sus4', 0.4),
                         # (blind round g2: two pieces of a set on one intro - a wider bank for the set memory)
                         'iii_IV': ('IIIm7 IVmaj7 IIm7 V', 0.4), 'bVII': ('I bVIImaj7 IVmaj7@3 V7sus4', 0.35),
                         'IV_V3': ('IVmaj7 V@3 VIm7 IVm6', 0.35), 'ii_I3': ('IIm7 I@3 IVmaj7 IVm6', 0.35)},
               'minor': {'i_VI': ('Im bVImaj7 bIIIadd9 Vsus4', 0.7), 'i_iv': ('Im7 IVm7 bVImaj7 Vsus4', 0.5),
                         'pedal': ('Im IVm7@5 Im IVm7@5', 0.6), 'lament': ('Im V@3 bVIImaj7 IVm7@3', 0.4),
                         'iv_VII': ('IVm7 bVII bIIImaj7 V7sus4', 0.4), 'VI_VII': ('bVImaj7 bVII Im7 V', 0.4)}},
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
_NA_ENDS = {'breath': 0.42, 'down': 0.33, 'antic': 0.05, 'pickup': 0.2}
"""new-age's phrase ends: fewer whole-bar breaths, a pickup into the next phrase now and then (blind round N0: a held
note or an empty bar closing every 4-bar phrase; right hand quiet a beat+ 38 % of the time, the references 25-30 %;
blind round g3: the 'antic' end - a note struck on 4.5 held into an empty bar - in 6 of 8 pieces: rare)."""
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
               # (blind round g5: a busy left hand under the climax's theme - VUUY's triplets, GNRR 12.2 attacks a
               # bar: the broad hand first, the 16th sweep rare)
               'build': {'flow': 1.0, 'color': 0.6, 'rock': 0.4}, 'big': {'broad': 1.0, 'big': 0.5, 'sweep': 0.1},
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
    # (blind round g5: the bloom's 16ths under the climax's sung theme read as a busy left hand - rarer there)
    # (round g7: GVPE / QNFS's build 12-13 left-hand attacks a bar, the right hand only +1.5-2.2 dB over it - the
    # chorus blooms less often, and the 16ths are the bloom's colour, not its whole second stage: 'figures')
    'at': {'build': 1.0, 'B1': 0.2, 'climax': 0.1},       # the section that blooms, drawn per piece
    'push': {1.04: 0.6, 1.06: 1.0, 1.08: 0.8, 1.1: 0.4},  # the tempo it pushes to (x the section's own)
    'reach': {0.4: 0.6, 0.5: 1.0, 0.65: 0.6},             # ... reached at that share of the section, then held
    'carry': {0.5: 0.6, 0.75: 1.0, 1.0: 0.6},             # the share of the push the climax keeps (broad at its peak)
    'rit': {0.93: 0.5, 0.96: 1.0, 0.98: 0.5},             # the bloom's own breath at its end (a section's: 0.8-0.9)
    'grid': {0.25: 1.0, 0.3333: 0.5},                     # the hand-off fills' note grid in the bloom (16ths / 3lets)
    # the hand-to-hand figure on a held melody note (the left hand climbs, the right carries it on into the next
    # note): its chance per held bar in the bloom / the other part sections by part letter (never into a phrase end)
    # (blind round g2: the hand-off's 16ths in 8 of 10 pieces, a pickup on beat 4 in every climax: rarer outside)
    # (blind round g3: the end-of-bar 4-note 16th run in the climax of 7 pieces of 8 - 'peak': the climax's at most)
    'handoff': {'bloom': 0.85, 'A': 0.06, 'B': 0.1, 'C': 0.12, 'peak': 0.4},
    'link': 0.5,                  # the bloom's last bar runs on into the next section (its phrase-end breath goes)
    'lift': 12,                   # the left hand's top may rise this far over its cap: to a whole step under the tune
    # the left hand's figures per meter: in the bloom two stages - triplets / 8ths until 'reach', then 16ths -, one
    # figure per 2-bar unit (the student's blind judge, 2026-10-15: a climax hand toggling 16ths / 8ths strictly bar
    # by bar reads as a machine; the figure is shaped by the phrase); the hand-off bars in the bloom and elsewhere
    # (round g7: 12-13 attacks a bar in GVPE / QNFS's build - the first stage 8ths, the second triplets with 8ths /
    # 16ths between (perform._draw never repeats a figure): 10.8 -> 8.9 attacks a bar, at most 11)
    'figures': {4: [{'flow': 1.0, 'rock': 0.6}, {'trip12': 1.0, 'flow': 0.6, 'span16': 0.3, 'wave16': 0.2}],
                3: [{'waltz_arp': 1.0, 'barcarolle': 0.5}, {'waltz_span': 1.0, 'waltz_wave': 0.8}]},
    # the right hand in the bloom: under a melody note held a beat or more, the chord's tones below it in the grid
    # (a woven figure under the tune, the melody note ringing on in the pedal), x this velocity
    'weave': 0.7,
    # what the right hand plays under its held notes there, per piece (blind round g2: the soft 16th broken chord
    # under a held note in 8 of 10 pieces): the woven figure, repeated 8th dyads (a pulse), or nothing (round g11, the
    # g10 performer / composerB: ZVNR's / HJJR's builds "inner arpeggios under held notes", overfull - the weave rarer)
    'texture': {'weave': 0.25, 'pulse': 0.35, 'none': 0.4},
    # (blind round g1: one 16th run on beat 4 of every build / climax bar) a hand-off's chance off the phrase's goals
    # (the bars leading into its half and its last bar: x1) and right after another one (x goal / 2); a hand-off's
    # grid redrawn from 'grids' by 'regrid' (16ths, triplets or 8ths - not one grid all section); the woven right
    # hand in every other bar at most (perform._handoffs)
    'goal': 0.45, 'regrid': 0.4, 'grids': {0.25: 1.0, 0.3333: 0.8, 0.5: 0.5},
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
_NA_SIGNATURE = {
    # the signature moves (docs/PIANO_MOVES.md; the user, 2026-10-15: famous piano pieces have a few iconic "cool
    # moves" everyone recognises - ours had none): per move its slot (identity / transition / payoff), its chance per
    # piece and its parameters {value: weight}, drawn per set slot by composer.signature_draw (pinned for the slot's
    # best-of-N; the set's fingerprints never repeat) and played by perform._signature
    'cap': 0.4,              # a move in at most this share of a set's pieces (the user: no move in > 40 % of a set)
    'after': 0.35,           # x a move's chance when the slot before had it
    'both': 0.35,            # x the second identity move's chance (the motto over the ostinato)
    'moves': {
        # 5.1 the motto: a 1-2 bar cell from the theme's head, planted alone at the start, back at the seams
        # (interlude / build / the variation), paid off at the climax, a fragment in the coda
        'motto': {'slot': 'identity', 'chance': 0.55,
                  'kind': {'osc': 1.0, 'sigh': 0.8, 'toll': 0.5, 'call': 0.8, 'leap': 0.7, 'fall3': 0.6},
                  'interval': {1: 1.0, 2: 0.8},            # osc / sigh: the neighbour (semitones: m2 / M2)
                  'grid': {0.5: 1.0, 0.25: 0.8, 0.3333: 0.6},     # 8ths / 16ths / triplet 8ths (beats)
                  'slow': 80,                              # 16ths only at or under this tempo
                  'swings': {2: 0.5, 3: 1.0, 4: 0.6},      # osc: alternations before it breaks off
                  'breakoff': {'arp_fall': 1.0, 'step_land': 0.8, 'held': 0.6},
                  'exposure': {'alone': 1.0, 'over_bass': 0.8},     # the plant: no left hand / one held bass
                  'payoff': {'augment+harmonize': 1.0, 'octave+harmonize': 0.8, 'augment+octave': 0.5},
                  'dyn': {'p': 1.0, 'pp': 0.6},
                  # where the cell starts (composer.motto_anchor; blind round g4: three mottos from the head's D5 -
                  # one "D-C-C" cell to every judge): the head's first note / the key's 3rd / 5th / tonic, in a
                  # register band - the set's mottos never share a band (signature_prints)
                  'anchor': {'head': 1.0, 'third': 0.8, 'fifth': 0.8, 'root': 0.5},
                  'register': {'low': 0.8, 'mid': 1.0, 'high': 0.7}},
        # 5.2 the signature ostinato: one left-hand figure of the piece's own, alone in the intro, the A sections'
        # texture, thinned in the coda (tokens per bar: 8 = 8ths, 12 = triplets / 3/4 16ths, 16 = 16ths)
        'ostinato': {'slot': 'identity', 'chance': 0.55,
                     'grid': {4: {8: 1.0, 12: 0.7, 16: 0.4}, 3: {6: 1.0, 12: 0.5}},
                     'fast': {4: 12, 3: 6},                # the grids over this need the tempo at or under 'slow'
                     'slow': 76,
                     'contour': {'rise': 0.6, 'rise_fall': 1.0, 'rock': 0.8, 'pendulum': 0.7, 'alberti': 0.4,
                                 'interlock': 0.3},
                     'span': {3: 0.6, 4: 1.0, 5: 0.8, 6: 0.4},       # ladder steps (a 10th .. two octaves)
                     'colour': {0: 0.6, 1: 0.4},           # the chord's 7th / 9th at one token
                     'bass': {'one': 1.0, 'octave': 0.5},
                     'lh_only': {1: 1.0, 2: 0.6}},         # the intro's bars of the figure alone
        # 5.3 the suspended pause: time stops at one seam - a held sus chord, a silence, a high note, the bass alone
        'pause': {'slot': 'transition', 'chance': 0.45,
                  'kind': {'sus_hold': 1.0, 'rest': 0.6, 'high_note': 0.5, 'bass_only': 0.4},
                  'seam': {'climax': 0.6, 'return': 0.25, 'coda': 0.15},
                  'hold': {1.5: 0.6, 2.0: 1.0, 2.5: 0.6},      # the fermata (beats)
                  'approach': {'rit': 1.0, 'subito': 0.5, 'dim': 0.7},
                  'after': {'subito_p': 0.8, 'forte': 0.6}},
        # 5.4 the goosebump chord: one known melody note at the payoff over a borrowed / chromatic-mediant chord
        'goose': {'slot': 'payoff', 'chance': 0.5,
                  'degree': {'major': {'bVI': 1.0, 'iv': 0.9, 'bIII': 0.5, 'II': 0.6, 'III': 0.6, 'bVII': 0.5},
                             'minor': {'VI': 1.0, 'IV': 0.8, 'bII': 0.3, 'VofV': 0.5}},
                  'where': {'peak': 1.0, 'return': 0.4},
                  'dyn': {'accent': 1.0, 'subito_p': 0.4},
                  'voicing': {'open': 1.0, 'rolled': 0.6}},
        # 5.5 the cascade: the climax's way out - a pedalled waterfall over 2.5 octaves, the hands leapfrogging,
        # in the climax's last bar under a held melody note (blind round g4: after the peak note it read as
        # "mechanical", "texture, not music" - a link now, and rarer; round g8: a fault in all three of its g7
        # appearances, JTQL / LXCD / ZGLR - "filler", "gestures instead of the theme": retired, chance 0)
        'cascade': {'slot': 'payoff', 'chance': 0.0,
                    'pattern': {'RL': 1.0, 'RRL': 0.4},
                    'group': {3: 0.8, 4: 1.0},             # notes per hand turn
                    'length': {1: 1.0},                    # bars (round g4: the climax's last bar, a link)
                    'grid': {0.25: 1.0, 0.1667: 0.6},      # 16ths / sextuplets
                    'landing': {'roll': 1.0, 'bass': 0.5, 'figure': 0.4}},
    },
}
"""The new-age piano's signature moves (the first five of docs/PIANO_MOVES.md; plan['signature'])."""
SIGNATURE_MOVES = ('motto', 'ostinato', 'pause', 'goose', 'cascade')
SIGNATURE_KEYS = {'motto': {'slot', 'chance', 'kind', 'interval', 'grid', 'slow', 'swings', 'breakoff', 'exposure',
                            'payoff', 'dyn', 'anchor', 'register'},
                  'ostinato': {'slot', 'chance', 'grid', 'fast', 'slow', 'contour', 'span', 'colour', 'bass',
                               'lh_only'},
                  'pause': {'slot', 'chance', 'kind', 'seam', 'hold', 'approach', 'after'},
                  'goose': {'slot', 'chance', 'degree', 'where', 'dyn', 'voicing'},
                  'cascade': {'slot', 'chance', 'pattern', 'group', 'length', 'grid', 'landing'}}
"""Each signature move's keys (plan['signature']['moves'][move]; Genre's strict check)."""


def _signature_problem(sg) -> str | None:
    """What is wrong with a plan['signature'] table (None: nothing) - the keys of _NA_SIGNATURE, the values the
    players know (composer.MOTTOS, pianist.OSTINATO_CONTOURS, perform.GOOSE)."""
    from ..pianist import OSTINATO_CONTOURS
    from .composer import MOTTO_BANDS, MOTTOS
    from .perform import GOOSE
    if not isinstance(sg, dict) or set(sg) != {'cap', 'after', 'both', 'moves'}:
        return "the keys cap, after, both, moves"
    if not 0 < sg['cap'] <= 1 or not 0 <= sg['after'] <= 1 or not 0 <= sg['both'] <= 1:
        return "cap 0..1 (a move's largest share of a set), after / both 0..1 (chance factors)"
    M = sg['moves']
    if not isinstance(M, dict) or not M or set(M) - set(SIGNATURE_MOVES):
        return f"moves: {{one of {', '.join(SIGNATURE_MOVES)}: its table}}"
    for mv, X in M.items():
        if not isinstance(X, dict) or set(X) != SIGNATURE_KEYS[mv]:
            return f"moves[{mv!r}]: the keys {', '.join(sorted(SIGNATURE_KEYS[mv]))}"
        if X['slot'] not in ('identity', 'transition', 'payoff') or not 0 <= X['chance'] <= 1:
            return f"moves[{mv!r}]: slot identity / transition / payoff, chance 0..1"
    x = M.get('motto')
    if x and (set(x['kind']) - set(MOTTOS) - {'osc'} or set(x['interval']) - {1, 2}
              or set(x['grid']) - {0.5, 0.25, 0.3333} or set(x['breakoff']) - {'arp_fall', 'step_land', 'held'}
              or set(x['exposure']) - {'alone', 'over_bass'} or set(x['dyn']) - {'pp', 'p', 'mp'}
              or set(x['anchor']) - {'head', 'third', 'fifth', 'root'} or set(x['register']) - set(MOTTO_BANDS)
              or any(set(k.split('+')) - {'augment', 'octave', 'harmonize'} for k in x['payoff'])):
        return ("moves['motto']: kind osc / " + ' / '.join(MOTTOS) + ", interval 1 / 2, grid 0.5 / 0.25 / 0.3333, "
                "breakoff arp_fall / step_land / held, exposure alone / over_bass, payoff augment / octave / "
                "harmonize joined by '+', dyn pp / p / mp, anchor head / third / fifth / root, register "
                + ' / '.join(MOTTO_BANDS))
    x = M.get('ostinato')
    if x and (set(x['grid']) - {3, 4} or any(set(w) - ({8, 12, 16} if m == 4 else {6, 12}) for m, w in
                                             x['grid'].items())
              or set(x['contour']) - set(OSTINATO_CONTOURS) or any(not 2 <= k <= 7 for k in x['span'])
              or set(x['bass']) - {'one', 'octave'} or set(x['colour']) - {0, 1}):
        return ("moves['ostinato']: grid {4: {8 / 12 / 16: w}, 3: {6 / 12: w}}, contour one of "
                + ', '.join(OSTINATO_CONTOURS) + ", span 2..7, bass one / octave, colour 0 / 1")
    x = M.get('pause')
    if x and (set(x['kind']) - {'sus_hold', 'rest', 'high_note', 'bass_only'}
              or set(x['seam']) - {'climax', 'return', 'coda'} or set(x['approach']) - {'rit', 'subito', 'dim'}
              or set(x['after']) - {'subito_p', 'forte'} or any(not 0 < k <= 8 for k in x['hold'])):
        return ("moves['pause']: kind sus_hold / rest / high_note / bass_only, seam climax / return / coda, hold "
                "0..8 beats, approach rit / subito / dim, after subito_p / forte")
    x = M.get('goose')
    if x and (set(x['degree']) != {'major', 'minor'} or any(set(x['degree'][m]) - set(GOOSE[m]) for m in GOOSE)
              or set(x['where']) - {'peak', 'return'} or set(x['dyn']) - {'accent', 'subito_p'}
              or set(x['voicing']) - {'open', 'rolled'}):
        return ("moves['goose']: degree {'major' / 'minor': {a perform.GOOSE degree: w}}, where peak / return, dyn "
                "accent / subito_p, voicing open / rolled")
    x = M.get('cascade')
    if x and (set(x['pattern']) - {'RL', 'RRL'} or any(not 2 <= k <= 6 for k in x['group'])
              or set(x['length']) - {1, 2} or any(not 0.1 <= k <= 0.5 for k in x['grid'])
              or set(x['landing']) - {'roll', 'bass', 'figure'}):
        return ("moves['cascade']: pattern RL / RRL, group 2..6 notes, length 1 / 2 bars, grid 0.1..0.5 beats, "
                "landing roll / bass / figure")
    return None
_NA_CLOSE = {
    # how a section closes when it ends on the dominant (perform._close; blind round g2: Vsus4 -> V at every section
    # end): 'keep' as written, 'I' a full close (V7 -> I), 'vi' a deceptive close (V7 -> vi), 'IV' an open plagal
    # half close, 'bVII' the backdoor (bVII -> the next section's I), 'ii' an open ii7
    'A1': {'keep': 0.4, 'IV': 0.2, 'vi': 0.15, 'I': 0.15, 'ii': 0.1},
    'A2': {'keep': 0.3, 'I': 0.35, 'IV': 0.15, 'bVII': 0.1, 'vi': 0.1},
    'B': {'keep': 0.35, 'IV': 0.2, 'bVII': 0.15, 'vi': 0.15, 'I': 0.15},
    'build': {'keep': 0.5, 'IV': 0.2, 'bVII': 0.2, 'ii': 0.1},
    'climax': {'keep': 0.35, 'I': 0.3, 'vi': 0.25, 'IV': 0.1},
    'A3': {'keep': 0.35, 'I': 0.25, 'IV': 0.2, 'vi': 0.2},
}
_NA_BARS = {
    # a part's bars played (perform._arrange 'bars'; a span played again is varied and reharmonised: an extension)
    'A': {((0, 8),): 0.5, ((0, 8), (6, 8)): 0.2, ((0, 4), (6, 8)): 0.15, ((0, 7),): 0.15},
    # (round g9: the chorus's 4-bar extension replayed its second half's chart - JKGC's 12-bar B1, 'Am-F-C-G twice':
    # a 2-bar extension at most)
    'B': {((0, 8),): 0.6, ((0, 8), (6, 8)): 0.4},
}

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
          # (quiet1 0.2: HUMAN_FEEDBACK 2026-10-15 'one finger' - connecting notes and inner voices fill some air)
          # (phrase_rests: round g6 - the higher register's waltzes ran on through more phrase ends, 0.36 in one: the
          # tests' floor 0.45 a gate now)
          'breath': {'quiet1': 0.2, 'att_cv4': 0.08, 'phrase_rests': 0.45}},
    # the arrangement draws its grid, its climax and its returns (blind round N0: one grid 4|8|8|8|4|8|8|8|5 in every
    # piece, the climax = B1 louder, A4 = A2 closing on the tonic; perform.ARRANGE_KEYS): A2 may run a bar over, the
    # interlude 2 or 4 bars, A3 a half return, the build 6 or 8 bars, the climax the chorus lifted / the theme an
    # octave up / the chorus a step up, held a bar longer; the last A high then home, closing deceptively; the final
    # chord resolves the last melody note (end_top)
    plan={'perform': 'piano', 'intro': 4, 'tag': 4, 'end': 1, 'phrases': _SING_PHRASES, 'end_top': 'line',
          'waltz_phrases': _NA_WALTZ_PHRASES, 'bloom': _NA_BLOOM, 'signature': _NA_SIGNATURE,
          # the period plan per part kind, drawn per tune (composer.compose; audit 2026-10-13: one plan per kind in
          # every piece - the A always peaking in its third phrase, the chorus breathing every 4 bars)
          'phrase_variants': {
              # (round g10: KVRY / AHVN / LMUP's heads "no repeated cell" - the A's second phrase mostly grows from
              # the hook: a half cadence on the hook's first bar (melody['half_cell']) or the hook developed; a free
              # line there rarer)
              'common': {'A': [(_SING_PHRASES['A'], 1.0),
                               ([('motif', None), ('line', 'arch'), ('develop', None), ('land', 'fall')], 0.2),
                               ([('motif', None), ('half', 'fall'), ('answer', None), ('land', 'fall')], 0.4),
                               ([('motif', None), ('develop', None), ('line', 'rise'), ('land', 'fall')], 0.8)],
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
                   'cap': {96: 0.7, 102: 1.0, 108: 0.7}, 'lh_vel': {37: 0.8, 41: 1.0, 46: 0.8},
                   'pedal': {45: 0.8, 60: 1.0, 90: 0.8}, 'end_dyn': {'pp': 1.0, 'p': 0.6},
                   'end_roll': {60: 0.8, 110: 1.0, 170: 0.8}, 'end_hold': {2: 0.8, 3: 1.0, 4: 0.7},
                   # the hands' balance (perform.BALANCE; HUMAN_FEEDBACK 2026-10-15: the right hand always louder)
                   'balance': {4.5: 1.0, 5.0: 0.8, 5.5: 0.6}, 'lh_lead': {1: 0.5, 2: 1.0, 3: 0.8},
                   # the last chord's right-hand grip (perform._play_piano; blind round g2: one 4-note grip)
                   'end_voice': {'full': 1.0, 'open': 0.7, 'single': 0.4}},
          'ornaments': {'turn': 0.45, 'mordent': 0.2},
          'swell': {0: 0.3, 1: 0.6, 2: 0.1},   # a hairpin per phrase, levels up (round r3: one mark per section)
          'candidate_tries': 2,      # best-of-8 from up to 16 seeds (the arc check rejected ~40 %)
          # the tune's touch window moved (lo, hi): its own loudness budget (round r2: ~17 LU in every piece)
          'touch_span': {(0, 0): 1.0, (-6, 0): 0.6, (5, -4): 0.6, (-3, 4): 0.5},
          'max_hold': 3.5,           # a melody note rings 3.5 beats at most (round r1: 4.5-7 beat holds, refs none)
          # an accent's velocity over the drawn cap at most (blind round g3: climaxes hammered at v115-126; the
          # romantic pianist's default accent_cap 118 over every cap)
          'accent_over': 6,
          'end_styles': {'roll': 1.0, 'spread': 0.6},
          'form_bars': True,         # (the bar counts below are form bars: a waltz plays two 3/4 bars for each)
          # the set-level draws (composer.set_draws; HUMAN_FEEDBACK 2026-10-12: every sample gentle / verse / minor,
          # its climax on C6 at ~90 %): per set slot, never the slot before's, pinned for the slot's best-of-N - the
          # arrangement's layout (song: the theme twice, the hook, an interlude, the build, the climax, the theme soft;
          # chorus: the hook right after the first theme, the climax its last statement; return: the climax, then an
          # interlude and the theme's return, ternary like the waltz reference), the climax kind (perform._arrange)
          # and the melody's register (semitones: the climax pitch)
          # (blind round g2: one form skeleton in every piece, the highest note at 71-76 % in 10 of 10 - six forms:
          # song / chorus (rondo A B A C A) / return (A B A') with the climax at ~70-76 %, arch (A B C B' A', the
          # climax ~55-60 %), variations (the theme varied, no chorus, the climax ~50 %), late (A A B A C, the climax
          # ~85 % into a short coda); set_memory: none of the last 3 slots' forms)
          'set': {'layout': {'song': 0.8, 'chorus': 0.7, 'return': 0.7, 'arch': 0.8, 'variations': 0.7, 'late': 0.7},
                  # (the learned generator's blind round 2: the climax built from earlier bars - 'grow' derives it
                  # from the hook, sequenced up to a new peak)
                  # (blind round g1: the climaxes that fooled the judges carried the theme - grow / theme; the
                  # chorus an octave up (climb / lift) read as an octave transplant, chord tones tiled)
                  # (blind round g4: 7 of 8 climaxes without the theme - 47 of 48 played 'grow', the octave-up
                  # 'theme' never fit under the ceiling: 'theme' is now _anthem, the theme's head phrase stated and
                  # its head again at the peak, and the default; 'anthem' how it is stated, per slot)
                  # (round g10, all five judges: KVRY's grown climax "new material, not the theme" - every climax
                  # sings the head: no 'grow', no 'climb' - the chorus an octave up)
                  'climax': {'theme': 1.6, 'lift': 0.1, 'step': 0.05},
                  # (round g8, all five judges: JTQL's 'augment' climax heard as held single notes and runs - the
                  # theme sung, not a gesture: no 'augment')
                  # (round g10: the head answered a bar later in the inner voice - 'canon' - a payoff other than
                  # "A1 an octave up", which four judges heard as the set's one plan)
                  'anthem': {'octaves': 1.0, 'chords': 1.0, 'sequence': 0.9, 'reharm': 0.8, 'canon': 0.9},
                  # the coda's approach into the end chord (harmony['tag_approach'], now a set draw - blind round g4:
                  # the IV - iv6 split in the penultimate bar of 4 pieces of 8)
                  # (no 'IV_iv' here: the split was the shared tell; the minor plagal IVm6 once a set at most)
                  'tag': {'sus': 1.0, 'IV': 0.8, 'ii': 0.8, 'vi': 0.8, 'plagal': 0.3},
                  # how the climax arrives (perform.ARRIVALS; round g9, four judges: "the theme returns at the
                  # climax" heard as the set's one plan - DMZT ~ PKCG ~ ZACW ~ JKGC ~ LXAN): straight in, after a
                  # suspended pause, after a key move, over a held dominant, its head fragmented first, then whole
                  'arrival': {'direct': 1.0, 'pause': 0.8, 'key': 0.7, 'dominant': 0.9, 'fragment': 0.9},
                  # (round g11, the g10 statistician: nine of eleven climaxes peak on A6 / Ab6, six of eight play one
                  # left hand there - the octave bass, a chord, its 10th, a chord): the sung climax's peak this many
                  # semitones under the ceiling (perform._arrange), and the climax's favoured left-hand figure
                  # (perform._play_piano: x BIG_PIN in its figure set; a waltz keeps its own) - per slot, the set
                  # spreading them (set_memory)
                  'peak': {0: 1.0, 2: 1.0, 4: 0.8},
                  'big': {'broad': 1.0, 'big': 1.0, 'tenths': 0.5},
                  # (round g13, all seven judges: every climax opened with the head, then the head a third up - the
                  # set's one shared plan): the sung climax's second phrase after the head (perform.ANTHEM_SECOND)
                  'second': {'third': 1.0, 'fifth': 0.8, 'mirror': 0.8},
                  # (blind round g5: the register a whole step up - no -3, the floor stays at G4 over the left hand;
                  # no +3, the A theme at C6-Eb6 left no room for the sung climax an octave up)
                  'shift': {-2: 0.7, -1: 0.7, 0: 0.8, 1: 0.7, 2: 0.4},
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
                            'minor': {'iv_climb': 1.0, 'relative': 1.0, 'lament': 0.8}},
                  # the theme's opening cell per cell family (composer.CELLS[...]['motif'], melody['openings'] as
                  # weights; blind round g1: one opening rhythm in three of ten pieces - no repeat in 3 slots)
                  # (round g7: no 'across' - XEDV's theme on three empty beats, then half-empty bars)
                  # (round g12, all five judges: KTGG's waltz head - the 'hemi' cell, three half notes over two bars,
                  # 1.9 attacks a bar - "a line of whole notes, no rhythm": no 'hemi' opening)
                  'opening': {'na': {'pickup': 0.5, 'rise3': 0.6, 'sigh': 1.0, 'held': 1.0, 'dotted': 1.0},
                              'na3': {'lean': 1.0, 'stroll': 1.0, 'arch3': 1.0, 'flow3': 1.0, 'turn3': 1.0}},
                  # the intro's vamp per mode (composer.frame; blind round g2: one vi-IV-I-Vsus4 intro and interlude
                  # in two pieces of a set)
                  'intro': {'major': {k: w for k, (_, w) in NEW_AGE_HARMONY['intros']['major'].items()},
                            'minor': {k: w for k, (_, w) in NEW_AGE_HARMONY['intros']['minor'].items()}}},
          # how many slots back a set draw may not repeat (composer.set_draws; default 1: the slot before; a per-mode
          # draw counts that mode's slots)
          # (climax 0: a grow climax may follow a grow climax - blind round g2's set: memory 1 forced every other
          # slot onto climb / lift, the octave transplants of round g1)
          # (blind round g2: progressions shared between pieces of a set - the build in two, the climax route over
          # the same hook in two: the chord blocks and the intro remember the whole set)
          'set_memory': {'hook': 9, 'open': 9, 'build': 9, 'intro': 9, 'opening': 3, 'climax': 0, 'layout': 3,
                         'anthem': 3, 'tag': 7, 'arrival': 3, 'peak': 2, 'big': 2, 'second': 2},
          # a waltz's later bar of a held chord (perform._moving_bass; blind round 2: two bars per chord, four-bar
          # single-chord stretches - a one-bar harmonic rhythm mostly)
          # (blind round g1: 'X | X/inversion' pairs, 8-11 a waltz - the bass move rarer, a failed 'ped' tries a sub)
          'moves': {'hold': 0.12, 'bass': 0.08, 'sub': 0.5, 'ped': 0.3},
          # a section as high as the climax's peak comes down an octave unless its line would drop under E4 (64;
          # round r9: the chorus an octave down in the left hand's register) - then only its peak notes (_under_peak)
          'peak_floor': 64,
          # the register's ceiling (perform._arrange; HUMAN_FEEDBACK 2026-10-15: "too many very high notes" - some
          # pieces a whole climax over C6, the theme an octave up to C7): an octave-up section only where its line
          # stays at or under 'line' (D6), an octave-up / lifted / moved climax and a grown peak at or under 'peak' (F6)
          # (blind round g5, every judge's first fix: the climax sang the theme in A1's register - the sung theme
          # (perform._anthem) an octave over A1 where its head fits under 'sung' (A6, the references' climax top:
          # embers 92, tide 93): the C6 band at the climax only, the high notes concentrated there - the user's "too
          # many very high notes" was about them everywhere)
          # (round g12: A6 peaks in four of eight g11 pieces - "shrill", "glassy", four judges - and the user's dislike
          # of very high notes: the sung head an octave up only where it stays at or under F6, every climax peak at
          # E6 / F6 at most; a higher head sings a third / fifth over A1 - ANTHEM_BAND - in the C5-C6 band)
          'ceiling': {'line': 86, 'peak': 89, 'sung': 89},
          # the broken-chord hand strikes one inner tone twice running at most (pianist.figure; rounds r8 / r10:
          # E3 E3 E3 - the capped ladder folding two steps onto one key)
          'lh': {'repeats': 2},
          # the climax never rocks between two chords (X Y X Y: the third takes a substitute - perform._unswing)
          'unswing': True,
          # the 'grow' climax's first statement the hook augmented, by this chance per piece (perform._grow; blind
          # round g1: the climaxes that fooled the judges carried the theme's rhythm and contour, raised)
          'grow_aug': 0.5,
          # the right hand's texture per section kind and its connecting notes (perform._texture; HUMAN_FEEDBACK
          # 2026-10-15: "the right hand plays note by note, as if he had only one finger" - 91-96 % single-note
          # onsets, 0.9 notes a beat): {(voices, share of the notes of min_dur beats+): weight}, drawn per section
          'texture': {'A1': {(0, 0.0): 0.3, (1, 0.4): 0.5, (1, 0.7): 0.2},
                      'A': {(1, 0.7): 0.45, (1, 0.95): 0.3, (2, 0.5): 0.25},
                      'B': {(1, 0.85): 0.4, (2, 0.6): 0.35, (1, 1.0): 0.25},
                      'climax': {(2, 0.8): 0.4, (3, 0.7): 0.35, (2, 1.0): 0.25},
                      'frame': {(0, 0.0): 0.4, (1, 0.6): 0.6},
                      'min_dur': 0.5, 'move': {0.85: 1.0, 1.0: 1.0}, 'connect': {0.5: 1.0, 1.0: 1.0},
                      # (blind round g3: inner motion under held notes 0.22 - a held note harmonized in this share at
                      # least, its inner voice moving by 'move')
                      'long': 0.9},
          # the melody as one dynamic line per phrase (romantic.Score.perform line=; the same feedback: neighbouring
          # melody notes 5-7 velocity steps apart, p90 16-20)
          'line': {'keep': 0.35, 'step': 4.0, 'accent': 9.0, 'range': 0.85, 'stretch': 1.6},
          # where the grown climax's climb sits (share of its units, perform._grow; blind round g2: the peak at the
          # same place in every piece)
          'grow_at': {0.45: 0.6, 0.6: 1.0, 0.75: 0.7},
          # (the learned generator's blind round 2, all five judges: one frame in every piece - a 4-bar intro, the
          # interlude pasted from it, a 4-bar coda, the same loudness arc; and no key plan, the returns copied note for
          # note: the frames' lengths and presence, every section's dynamics, a return's development per 2-bar unit
          # ('vary') and a section's key ('key') are drawn per piece)
          'sections': [
              {'name': 'intro', 'frame': 'intro', 'dyn': {('pp', 'p'): 1.0, 'p': 0.6, ('p', 'mp'): 0.4},
               'figures': {'intro': 1.0, 'calm': 0.4}, 'chance': 0.85, 'bars': {((0, 4),): 0.55, ((2, 4),): 0.45},
               'lh_only': {0: 0.6, 1: 0.3, 2: 0.1}, 'rit': {0.8: 0.3, 0.85: 0.4, 0.9: 0.3}},
              # (blind round g2: one form skeleton - every section 8 bars + a held bar, every section closing on the
              # dominant: 'bars' draws irregular lengths - an extension (bars played again, varied and reharmonised:
              # 10 / 12 bars), a 6-bar phrase, an elision (7 bars: the cadence bar dropped, the next section starts
              # there) - and 'close' how the section ends: _NA_CLOSE)
              {'name': 'A1', 'part': 'A1', 'dyn': {'p': 1.0, ('p', 'mp'): 0.6, ('pp', 'p'): 0.3},
               'figures': {'calm': 1.0, 'flow': 0.4}, 'fill': {0: 0.5, 1: 0.5}, 'turn': {0: 0.6, 1: 0.4},
               'bars': {((0, 8),): 0.6, ((0, 8), (6, 8)): 0.25, ((0, 7),): 0.15}, 'close': _NA_CLOSE['A1']},
              {'name': 'A2', 'part': 'A2', 'dyn': {('p', 'mp'): 1.0, 'mp': 0.5, ('mp', 'p'): 0.4},
               'figures': {'flow': 1.0, 'calm': 0.4}, 'harmonize': {0: 0.3, 1: 0.7},
               'rit': {0.8: 0.4, 0.85: 0.3, 0.92: 0.3},
               'tail': {0: 0.85, 1: 0.15}, 'bass': {'root': 0.7, 'walk': 0.3}, 'fill': {0: 0.1, 1: 0.9},
               'turn': {0: 0.3, 1: 0.7}, 'vary': {'keep': 0.15, 'orn': 0.3, 'rhythm': 0.4, 'seq': 0.15},
               'reharm': {0: 0.4, 0.7: 0.6}, 'bars': _NA_BARS['A'], 'close': _NA_CLOSE['A2'],
               'layouts': ('song', 'return', 'late')},
              {'name': 'B1', 'part': 'B', 'dyn': {('mp', 'mf', 'mp'): 1.0, ('p', 'mf', 'mp'): 0.5, 'mf': 0.4},
               'figures': {'chorus': 1.0, 'flow': 0.25}, 'rit': {0.85: 0.5, 0.9: 0.3, 0.8: 0.2},
               'tail': {0: 0.9, 1: 0.1}, 'fill': {0: 0.4, 1: 0.6}, 'bars': _NA_BARS['B'], 'close': _NA_CLOSE['B'],
               'key': {'major': {'home': 0.8, 'bVI': 0.08, 'IV': 0.06, 'bIII': 0.06},
                       'minor': {'home': 0.8, 'par': 0.1, 'IV': 0.1}},
               # (blind round g5: 'variations' had no contrast - UHVW A1 A2 A3 climax A4: the chorus as its second
               # section, then the variation, the climax, the return)
               'layouts': ('song', 'chorus', 'return', 'arch', 'late', 'variations')},
              {'name': 'A2', 'part': 'A2', 'dyn': {('p', 'mp'): 1.0, 'mp': 0.5, ('mp', 'p'): 0.4},
               'figures': {'flow': 1.0, 'calm': 0.4}, 'harmonize': {0: 0.3, 1: 0.7},
               'rit': {0.8: 0.4, 0.85: 0.3, 0.92: 0.3}, 'bass': {'root': 0.5, 'walk': 0.5}, 'fill': {0: 0.1, 1: 0.9},
               'turn': {0: 0.3, 1: 0.7}, 'reharm': {0: 0.4, 0.7: 0.6}, 'bars': _NA_BARS['A'], 'close': _NA_CLOSE['A2'],
               'vary': {'keep': 0.15, 'orn': 0.3, 'rhythm': 0.35, 'seq': 0.15, 'invert': 0.05}, 'layouts': ('chorus',)},
              # (round r6: the interlude = the intro's first two bars at -9..-12 LU, a cut-off: now the intro's
              # half cadence - its last two bars, into the theme - and a step softer only)
              {'name': 'inter', 'frame': 'intro', 'dyn': {'p': 1.0, 'mp': 0.4, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'keep_bars': (2, 3), 'rit': {0.78: 0.3, 0.82: 0.4, 0.88: 0.3},
               'chance': 0.6,
               'bars': {((2, 4),): 1.0}, 'octave': {0: 0.5, 1: 0.5}, 'vary': {'keep': 0.1, 'orn': 0.5, 'rhythm': 0.4},
               'layouts': ('song', 'late')},
              {'name': 'A3', 'part': 'A1', 'dyn': {'p': 1.0, ('p', 'mp'): 0.5, ('mp', 'p'): 0.4},
               'figures': {'calm': 1.0, 'flow': 0.6}, 'harmonize': {0: 0.3, 1: 0.7}, 'chance': 0.6,
               'octave': {0: 0.7, 1: 0.3},
               'bars': {((0, 8),): 0.4, ((0, 4),): 0.3, ((0, 4), (6, 8)): 0.3}, 'bass': {'root': 0.4, 'walk': 0.6},
               'fill': {0: 0.5, 1: 0.5}, 'close': _NA_CLOSE['A3'],
               'vary': {'keep': 0.1, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.2, 'invert': 0.1},
               'reharm': {0: 0.3, 0.7: 0.7}, 'layouts': ('song', 'late')},
              # (blind round g4: a build louder than the climax - FBKR +2.5 vs +1.2 LU, ZKYC's build at 0 dB between
              # the hands: the build rises to mf, the climax to ff mostly; perform._dyn_order keeps every other mark
              # a level under the climax's loudest; a 4-bar cell played twice, ANQT 41-48: no 4-bar extension)
              {'name': 'build', 'part': 'C', 'dyn': {('mp', 'mf'): 1.0, ('p', 'mf'): 0.6, ('p', 'mp', 'mf'): 0.4},
               'figures': 'build', 'rit': {0.85: 0.5, 0.9: 0.3, 0.8: 0.2}, 'tail': {0: 0.85, 1: 0.15},
               'bars': {((0, 8),): 0.45, ((0, 4), (6, 8)): 0.3, ((0, 8), (6, 8)): 0.25}, 'fill': {0: 0.1, 1: 0.9},
               'close': _NA_CLOSE['build'], 'layouts': ('song', 'chorus', 'return', 'arch', 'late')},
              {'name': 'climax', 'part': 'B', 'melody': 'lift',
               'dyn': {('mf', 'ff', 'mp'): 1.0, ('mf', 'f', 'mp'): 0.4, ('f', 'ff', 'mf'): 0.5, ('mp', 'ff', 'mf'): 0.4},
               'figures': {'big': 1.0, 'build': 0.15}, 'harmonize': {1: 0.3, 2: 0.7},
               'harm_share': {0.35: 0.3, 0.45: 0.4, 0.6: 0.3}, 'peak': True, 'rit': {0.68: 0.3, 0.72: 0.4, 0.8: 0.3},
               'fermata': {1.5: 0.3, 2.5: 0.4, 3.5: 0.3}, 'cadenza': 0.15,
               'climax': {'lift': 0.05, 'theme': 0.75, 'climb': 0.1, 'step': 0.05, 'grow': 0.05},
               # (blind round g1: a whole climax in a foreign key read as a transplant - home more often)
               # (blind round g3: a remote key without a pivot or a way home - perform._keys prepares the move
               # over two bars, a pivot chord then the dominant, and leaves it the same way; home more often)
               'key': {'major': {'home': 0.8, 'step': 0.04, 'bVI': 0.07, 'IV': 0.06, 'bIII': 0.03},
                       'minor': {'home': 0.78, 'par': 0.12, 'rel': 0.05, 'IV': 0.05}},
               'reharm': {0: 0.05, 0.7: 0.45, 1.0: 0.5}, 'tail': {0: 0.7, 1: 0.3}, 'fill': {0: 0.1, 1: 0.9},
               'close': _NA_CLOSE['climax'],
               'vary': {'keep': 0.15, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.15, 'invert': 0.1},
               'layouts': ('song', 'chorus', 'return', 'arch', 'late')},
              # (theme and variations: no chorus, no build - the climax is a variation of the theme itself, over its
              # own chords; blind round g3: the climax at 49 %, then two A statements - a third variation before it,
              # one return after it: the peak at ~65-75 %)
              {'name': 'A3', 'part': 'A2', 'dyn': {('mp', 'mf'): 1.0, ('p', 'mf'): 0.6, 'mp': 0.4},
               'figures': {'chorus': 1.0, 'flow': 0.6}, 'harmonize': {1: 0.6, 2: 0.4},
               'rit': {0.88: 0.5, 0.92: 0.5}, 'bass': {'root': 0.4, 'walk': 0.6}, 'fill': {0: 0.5, 1: 0.5},
               'reharm': {0.7: 0.5, 1.0: 0.5}, 'close': _NA_CLOSE['B'],
               'vary': {'orn': 0.2, 'rhythm': 0.3, 'seq': 0.3, 'invert': 0.2}, 'layouts': ('variations',)},
              {'name': 'climax', 'part': 'A1',
               'dyn': {('mf', 'ff', 'mp'): 1.0, ('mf', 'f', 'mp'): 0.4, ('mp', 'ff', 'mf'): 0.5},
               'figures': {'big': 1.0, 'build': 0.3}, 'harmonize': {1: 0.4, 2: 0.6},
               'harm_share': {0.35: 0.3, 0.45: 0.4, 0.6: 0.3}, 'peak': True, 'rit': {0.72: 0.4, 0.8: 0.6},
               'fermata': {1.5: 0.5, 2.5: 0.5}, 'cadenza': 0.1,
               'climax': {'lift': 0.05, 'theme': 0.75, 'climb': 0.1, 'step': 0.05, 'grow': 0.05},
               'key': {'major': {'home': 0.78, 'bVI': 0.08, 'IV': 0.1, 'bIII': 0.04},
                       'minor': {'home': 0.75, 'par': 0.17, 'rel': 0.08}},
               'reharm': {0.7: 0.5, 1.0: 0.5}, 'tail': {0: 0.7, 1: 0.3}, 'fill': {0: 0.1, 1: 0.9},
               'close': _NA_CLOSE['climax'],
               'vary': {'keep': 0.1, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.2, 'invert': 0.1}, 'layouts': ('variations',)},
              # (return: after the climax the music melts - an interlude, the theme's return high and soft)
              # (blind round g1: A3 = A1 8 of 8 bars, chords and line - the returns that fooled the judges were
              # reharmonised: every return draws 'reharm' and keeps a unit as written less often)
              # (round r6: A3 = A1 note for note, half of it an octave up then down mid-phrase: now high or low
              # throughout, a half return or the whole)
              # (round g8: the arch without it - KTBL's climax at 57 %, B' and A' after it)
              {'name': 'inter', 'frame': 'intro', 'dyn': {'p': 1.0, 'mp': 0.4, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'keep_bars': (2, 3), 'rit': {0.75: 0.3, 0.8: 0.4, 0.86: 0.3},
               'chance': 0.7,
               'bars': {((2, 4),): 1.0}, 'octave': {0: 0.4, 1: 0.6}, 'vary': {'keep': 0.1, 'orn': 0.5, 'rhythm': 0.4},
               'layouts': ('return',)},
              # (the arch: A B C B' A' - the chorus comes back after the climax, softer, on new chords; round g8:
              # half of it - KTBL's climax at 57 % with 23 bars after it, the peak now at ~65 %+)
              {'name': 'B2', 'part': 'B', 'dyn': {('mp', 'p'): 1.0, 'mp': 0.5, ('mf', 'p'): 0.4},
               'figures': {'chorus': 1.0, 'flow': 0.5, 'calm': 0.3}, 'harmonize': {0: 0.4, 1: 0.6},
               'rit': {0.8: 0.4, 0.85: 0.4, 0.9: 0.2}, 'octave': {0: 0.6, 1: 0.4},
               'bars': {((0, 4),): 1.0}, 'bass': {'root': 0.5, 'walk': 0.5},
               'fill': {0: 0.4, 1: 0.6}, 'reharm': {0.7: 0.6, 1.0: 0.4}, 'close': _NA_CLOSE['A3'],
               'vary': {'keep': 0.1, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.2, 'invert': 0.1}, 'layouts': ('arch',)},
              {'name': 'A3', 'part': 'A1', 'dyn': {('mp', 'p'): 1.0, 'p': 0.6, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'harmonize': {0: 0.3, 1: 0.7},
               'tempo': {0.9: 0.3, 0.93: 0.4, 0.97: 0.3}, 'rit': {0.75: 0.3, 0.8: 0.4, 0.85: 0.3},
               'octave': {0: 0.5, 1: 0.5}, 'bars': {((0, 8),): 0.4, ((0, 4), (6, 8)): 0.4, ((0, 7),): 0.2},
               'bass': {'root': 0.5, 'walk': 0.5}, 'fill': {0: 0.5, 1: 0.5}, 'close': _NA_CLOSE['A3'],
               'vary': {'keep': 0.1, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.2, 'invert': 0.1},
               'reharm': {0: 0.3, 0.7: 0.7}, 'layouts': ('return',)},
              # (round g9: NSFY's arch closed in 13 bars after its climax - B' 4, A' 6, the coda 3 - "rushed": the
              # arch's A' the whole theme, now and then extended)
              {'name': 'A3', 'part': 'A1', 'dyn': {('mp', 'p'): 1.0, 'p': 0.6, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'harmonize': {0: 0.3, 1: 0.7},
               'tempo': {0.9: 0.3, 0.93: 0.4, 0.97: 0.3}, 'rit': {0.75: 0.3, 0.8: 0.4, 0.85: 0.3},
               'octave': {0: 0.5, 1: 0.5}, 'bars': {((0, 8),): 0.6, ((0, 8), (6, 8)): 0.4},
               'bass': {'root': 0.5, 'walk': 0.5}, 'fill': {0: 0.5, 1: 0.5}, 'close': _NA_CLOSE['A3'],
               'vary': {'keep': 0.1, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.2, 'invert': 0.1},
               'reharm': {0: 0.3, 0.7: 0.7}, 'layouts': ('arch',)},
              {'name': 'A4', 'part': 'A2', 'dyn': {('mp', 'p'): 1.0, 'p': 0.6, ('p', 'pp'): 0.4},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'tempo': {0.9: 0.3, 0.93: 0.4, 0.97: 0.3},
               'rit': {0.75: 0.3, 0.8: 0.4, 0.85: 0.3},
               'octave': {0: 0.5, 1: 0.5}, 'cadence': {'home': 0.3, 'vi': 0.45, 'IV': 0.25},
               'bass': {'root': 0.6, 'walk': 0.4}, 'fill': {0: 0.5, 1: 0.5}, 'turn': {0: 0.4, 1: 0.6},
               'vary': {'keep': 0.1, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.2, 'invert': 0.1},
               'reharm': {0: 0.3, 0.7: 0.7}, 'layouts': ('song', 'chorus', 'variations')},
              # (blind round g3: 'late' ended its climax straight into the coda - a short return of the theme)
              {'name': 'A4', 'part': 'A2', 'dyn': {('mp', 'p'): 1.0, 'p': 0.6},
               'figures': {'thin': 1.0, 'calm': 0.6}, 'tempo': {0.9: 0.4, 0.95: 0.6},
               'rit': {0.75: 0.4, 0.8: 0.6}, 'octave': {0: 0.6, 1: 0.4},
               'bars': {((0, 4),): 0.5, ((0, 4), (6, 8)): 0.5}, 'bass': {'root': 0.5, 'walk': 0.5},
               'fill': {0: 0.5, 1: 0.5}, 'cadence': {'home': 0.5, 'vi': 0.3, 'IV': 0.2},
               'vary': {'keep': 0.1, 'orn': 0.3, 'rhythm': 0.3, 'seq': 0.2, 'invert': 0.1},
               'reharm': {0.7: 0.7, 1.0: 0.3}, 'layouts': ('late',)},
              {'name': 'coda', 'frame': 'tag', 'dyn': {('p', 'pp'): 1.0, ('mp', 'pp'): 0.5, 'pp': 0.3},
               'figures': 'thin', 'tempo': {0.9: 0.3, 0.95: 0.4, 1.0: 0.3}, 'rit': {0.7: 0.3, 0.75: 0.4, 0.82: 0.3},
               'bars': {((0, 4),): 0.6, ((2, 4),): 0.4},
               'vary': {'keep': 0.3, 'orn': 0.35, 'rhythm': 0.35}}]},
    # (blind round g5: the A theme too low - E4-C5, inside the left hand's arpeggios; measured A median C5, its 10th
    # percentile Ab4 against the references' D5-G5 / the climax C6-D6: the register a whole step up, the singing
    # register over the left hand - the high notes still rare outside the climax)
    melody={'register': ('A4', 'C6'), 'center': 'F5', 'peak': 'D6', 'steps': _NA_STEPS, 'ends': _NA_ENDS,
            'repeat': (2.5, 1.5),         # a repeated note costs more (blind round N0: repeated-note pickups)
            'chromatic': 0.04,            # half-step-below approach notes: rare (round r1: weak-beat clashes)
            'chromatic_step': True,       # ... and only after a step (round g13: JQTJ's Eb5-Gb5-G5, a wrong note)
            # 2-bar units a later A restates (round r2: A2 = A1's first 6 bars; audit 2026-10-13: three too)
            'restate': {1: 0.35, 2: 0.5, 3: 0.15},
            # (no 'hook_seq': the hook sequenced as a 1-bar cell broke the head's writing rules - one rhythm 4x in 8
            # bars, repeated pitches over the references' 0.05 - audit 2026-10-13: kept at 0)
            # the chorus's counter-motif: the hook's shape upside down or a shape of its own (audit 2026-10-13)
            # (blind round g3: the B tune stronger than A in three pieces - the chorus answers the theme's shape)
            'counter': {'mirror': 0.7, 'own': 0.3},
            # the theme's head: one leap of a 4th to a 6th (scale steps) at its 2nd / 3rd move, a step back after it
            # (composer.compose; blind round g3: A themes circling a third or fourth, a 2-note neighbour cell)
            'head': {'leap': {3: 1.0, 4: 0.8, 5: 0.4}, 'at': {1: 1.0, 2: 0.8}},
            # the theme's head redrawn up to this many times until it has a profile (composer.HEAD_PROFILE: a leap of
            # a 4th+, its top note held, no 2-3 note band circled; round g8, all five judges: JTQL / LXCD / VJGT /
            # VWBU heads circling a step or two), and fitted until it keeps it (the A1's attempts)
            'profile': 24,
            # (round g11: VBJZ's head off the beat in fragments, VEAS's two-note shuffle, ELNQ's waltz head never
            # landing - composer.HEAD_SHAPE; each check the A1's fit misses costs this much against the others)
            'shape': 0.6,
            # how the A's answer phrase ('develop' / 'answer') treats the hook's rhythm (DEVELOP_RHYTHM's names; round
            # g13, composerE: JQTJ 5-8 / ZSTD 7-10 "the second phrase wanders" - JQTJ's answer displaced an 8th onto
            # beat 3: the answer mirrors the head's rhythm, its first bar kept, never displaced)
            'develop': {'same': 0.55, 'truncate': 0.3, 'augment': 0.15},
            # (round g13: B1 without a hook of its own, five pieces - "held notes, or busy 8ths around two notes" in
            # A's rhythm): the chorus's counter-motif cell shares at most this onset Jaccard with the hook's cell
            'b_contrast': 0.45,
            # (round g10: KVRY / AHVN / LMUP's heads "no repeated cell" - an A's half cadence grows from the hook in
            # this share of the phrases: its first bar's rhythm and intervals again, then the landing - a-b-a'-c)
            'half_cell': 0.7,
            # a chorus's inner half cadence runs on as a line in that share of the tunes (round r5: a lone held note
            # in the chorus's 4th bar of every piece)
            'half_line': {'B': 0.4},
            # how the theme / the chorus open (composer.compose: the motif cells by weight, default 1; round r10:
            # 'across' - three empty beats, a beat-4 pickup - opening the chorus in three of four pieces)
            # (round g7: 'across' rarer still - XEDV's theme on three empty beats read as half-empty bars)
            'openings': {'across': 0.05, 'pickup': 0.5, 'rise3': 0.6, 'hemi': 0.05},
            # an A part's bars (but its landings) sound half the bar at least, the theme's head is no neighbour
            # figure (composer._style_issues; round g7: XEDV's half-empty bars after a pickup, WHKZ's B-C-D-C head)
            'holes': 0.5,
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

MODAL = ('dorian', 'phrygian', 'mixolydian', 'aeolian')
"""The church modes a 'symphony' plan's moods may draw besides major / minor (endless/symphony.py steps in the key's
scale; the minor-ish ones harmonize like minor)."""

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
    'B2': {'counter_strings': 1.0, 'cello_theme': 0.7, 'strings_melody': 0.5, 'solo_pad': 0.4},
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
    for k in ('play', 'touch_span', 'ornaments', 'end_styles', 'lh', 'pedal', 'cap', 'ceiling'):
        plan.pop(k, None)                              # (the ceiling: the piano's register - the violins sing higher)
    # (round g5: the piano's sung climax theme, perform._anthem, is the pianist's - its octaves / chords and its peak
    # under the piano's ceiling; the orchestra's tutti keeps the grown climax and its old climax draw)
    plan['set'] = dict(plan['set'], climax={'grow': 1.4, 'theme': 0.7, 'climb': 0.35, 'lift': 0.15, 'step': 0.05})
    plan['set'].pop('anthem', None)
    plan['set'].pop('arrival', None)                   # (the sung climax's arrival: the piano's)
    # (round g6: the piano's melody a whole step up, over its left hand - the orchestra keeps its register: its lines
    # are orchestrated per section, the violins sing higher anyway)
    plan['set']['shift'] = {-3: 0.5, -2: 0.7, -1: 0.6, 0: 0.7, 1: 0.7, 2: 0.7, 3: 0.5}
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
        # (round g8: the theme head's profile gate - melody['profile'] - is the piano's: the score keeps its draws)
        plan=plan, melody=dict(na.melody, register=('G4', 'Bb5'), center='Eb5', peak='C6', profile=0, shape=0),
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

# ------------------------------------------------------------------------------------------------ orchestra (symphonic)
# orchestra-symphonic (HUMAN_FEEDBACK 2026-10-16: the film orchestra "very meditative ... no life"): its own composer
# (endless/symphony.py - a driving motto developed through a sonata-like form, running figuration, a lyrical second
# theme, sudden dynamics) on the same film_orchestra band and orchestrator (the symphonic rows of
# orchestration.TEXTURES); docs/ORCHESTRA_ENDLESS.md "The symphonic composer". The feels are the movement types:
# 'family' the motto's cell family (duple 4/4 or compound 6/8), 'scale' 2 = the compound bar played as two fast 3/4
# bars (the scherzo), 'meter' the song's, 'grid' the running figuration's step (beats of the compound / duple bar),
# 'layout' a fixed form (the river's journey); 'energy' places it in a set.

_SYM_KINDS = {
    # per block kind: its orchestration plans {texture: weight}, dynamics [(fraction of the block, mark[, 'step'])],
    # 'peak' (the one tutti climax), 'sf' (sforzandi on the theme's long notes), 'level' (the arc level, tune.json)
    'intro': {'tex': {'motto_unison': 1.0, 'motto_brass': 0.6}, 'dyn': [(0, 'f')], 'sf': True, 'level': 0.7},
    'mist': {'tex': {'mist': 1.0}, 'dyn': [(0, 'pp'), (1, 'mp')], 'level': 0.3},
    'source': {'tex': {'river': 1.0}, 'dyn': [(0, 'pp'), (1, 'mp')], 'level': 0.3},
    # (round o8 - o7's judges: "themes that are only running arpeggios / 16ths", AMNU / THGD: the first statement of
    # the theme on top - the motto in the bass under the violins' run is a restatement's texture, t1b / close)
    't1': {'tex': {'drive_strings': 1.0, 'running_strings': 0.8}, 'dyn': [(0, 'mf'), (1, 'f')],
           'sf': True, 'level': 0.65},
    't1b': {'tex': {'motto_bass': 1.0, 'tutti_drive': 0.5, 'motto_brass': 0.4}, 'dyn': [(0, 'f', 'step')],
            'sf': True, 'level': 0.75},
    'trans': {'tex': {'dialogue': 1.0, 'dialogue_brass': 0.6}, 'dyn': [(0, 'mf'), (1, 'f')], 'level': 0.6},
    't2': {'tex': {'cantabile': 1.0}, 'dyn': [(0, 'p', 'step'), (0.5, 'mp'), (1, 'p')], 'level': 0.4},
    't2b': {'tex': {'cantabile_strings': 1.0, 'river_theme': 0.5}, 'dyn': [(0, 'mp'), (0.75, 'f')], 'level': 0.55},
    # (round o6 - o5's judges: "a bare tutti unison scale as filler": the close without the unison)
    'close': {'tex': {'tutti_drive': 1.0, 'motto_bass': 0.6, 'hammer': 0.5}, 'dyn': [(0, 'f', 'step')], 'sf': True,
              'level': 0.7},
    'river': {'tex': {'river_theme': 1.0, 'cantabile_strings': 0.4}, 'dyn': [(0, 'mp'), (1, 'mf')], 'level': 0.5},
    # (round o12 - o11's judges: "no 16th texture without the motto over it": the episode's motto on top mostly - the
    # brass fanfare, the dialogue -, the motto under the violins' run rarer)
    'episode': {'tex': {'motto_brass': 1.0, 'dialogue_brass': 0.8, 'motto_bass': 0.35}, 'dyn': [(0, 'f')],
                'sf': True, 'level': 0.7},
    'dev_dialogue': {'tex': {'dialogue': 1.0, 'dialogue_brass': 0.7}, 'dyn': [(0, 'mp', 'step'), (1, 'f')],
                     'level': 0.6},
    'dev_fugato': {'tex': {'fugato': 1.0, 'fugato_winds': 0.5}, 'dyn': [(0, 'mf', 'step'), (1, 'f')], 'level': 0.7},
    'retrans': {'tex': {'tremolo_build': 1.0}, 'dyn': [(0, 'pp', 'step'), (1, 'ff')], 'level': 0.85},
    'recap': {'tex': {'tutti_symphonic': 1.0, 'tutti_drive': 0.05}, 'dyn': [(0, 'f', 'step'), (1, 'ff')], 'peak': True,
              'sf': True, 'level': 1.0},
    # (round o4: the second theme's return with a counter-line - the motto against it - in most textures)
    'recap2': {'tex': {'cantabile_strings': 1.0, 'dev_poly': 0.5, 'cantabile': 0.3},
               'dyn': [(0, 'p', 'step'), (1, 'mf')],
               'level': 0.5},
    'coda': {'tex': {'chorale_brass': 1.0, 'hammer': 0.6, 'tutti_drive': 0.4}, 'dyn': [(0, 'f'), (1, 'ff')],
             'sf': True, 'level': 0.9},
    # (round o5: the dissolving coda in more than one colour)
    'coda_soft': {'tex': {'dissolve': 1.0, 'cantabile_horn': 0.5, 'cantabile_strings': 0.5},
                  'dyn': [(0, 'mp'), (1, 'pp')], 'level': 0.3},
    'end': {'tex': {'hammer': 1.0}, 'dyn': [(0, 'f')], 'level': 0.8},
    # (round o6 - o5's judges, one plan in both codes: "... then a soft coda": the soft last bars in more colours)
    'end_soft': {'tex': {'dissolve': 1.0, 'chorale_winds': 0.7, 'strings_pad': 0.6}, 'dyn': [(0, 'pp')],
                 'level': 0.2},
    # (round o2) the slow introduction before the call: the motto's head augmented in the low strings or a solo wind
    'slow': {'tex': {'mist': 1.0, 'dissolve': 0.8}, 'dyn': [(0, 'p'), (0.75, 'mf'), (1, 'p')], 'level': 0.35},
    # (round o3) the solo opening: one voice states the motto over a held pedal
    'solo': {'tex': {'solo_call': 1.0}, 'dyn': [(0, 'p'), (0.6, 'mp'), (1, 'p')], 'level': 0.3},
    # (round o4: the forms beyond the sonata) the rondo's refrain (and the false recapitulation), a trio / middle
    # section's own tune, a variation of the first theme (its texture by symphony.VARIATIONS)
    'refrain': {'tex': {'drive_strings': 1.0, 'tutti_drive': 0.6, 'dialogue': 0.4}, 'dyn': [(0, 'mf'), (1, 'f')],
                'sf': True, 'level': 0.65},
    # (round o10 - o9's judges, EYPC: "the trio a flute over block clarinet / bassoon chords for 28 bars": the trio
    # mostly over moving strings - arpeggios, off-beat chords; the wind choir's block chords rarer)
    'trio': {'tex': {'cantabile_horn': 1.0, 'cantabile_winds': 0.35, 'cantabile_cello': 0.6, 'cantabile': 0.8,
                     'cantabile_pulse': 0.8},
             'dyn': [(0, 'p', 'step'), (0.5, 'mp'), (1, 'p')], 'level': 0.4},
    'var': {'tex': {'drive_strings': 1.0}, 'dyn': [(0, 'mf')], 'level': 0.6},
}
_SYM_LAYOUTS = {
    # (block name, kind, bars of the duple / compound bar[, overrides]); 'intro' / 'coda' / 'end' play the piece's
    # opening and coda draws
    'sonata': [('intro', 'intro', 4), ('t1', 't1', 8), ('t1b', 't1b', 8), ('trans', 'trans', 6), ('t2', 't2', 8),
               ('t2b', 't2b', 8), ('close', 'close', 4), ('dev1', 'dev_dialogue', 8), ('dev2', 'dev_fugato', 8),
               ('retrans', 'retrans', 6), ('recap', 'recap', 8), ('recap2', 'recap2', 8), ('coda', 'coda', 8),
               ('end', 'end', 3)],
    'fugal': [('intro', 'intro', 4), ('t1', 't1', 8), ('trans', 'trans', 6), ('t2', 't2', 8), ('t2b', 't2b', 8),
              ('close', 'close', 4), ('dev1', 'dev_fugato', 8), ('dev2', 'dev_dialogue', 8),
              ('retrans', 'retrans', 6), ('recap', 'recap', 8), ('recap2', 'recap2', 8), ('coda', 'coda', 8),
              ('end', 'end', 3)],
    'compact': [('intro', 'intro', 4), ('t1', 't1', 8), ('t1b', 't1b', 8), ('trans', 'trans', 4), ('t2', 't2', 8),
                ('close', 'close', 4), ('dev1', 'dev_dialogue', 8), ('retrans', 'retrans', 4),
                ('recap', 'recap', 8), ('recap2', 'recap2', 6), ('coda', 'coda', 6), ('end', 'end', 3)],
    # the river's journey (the Moldau principle): the source, the theme growing out of the stream, a hunting call,
    # a storm, the broad return
    'journey': [('source', 'source', 8), ('river', 'river', 8),
                ('river2', 'river', 8, {'tex': {'tutti_drive': 1.0, 'cantabile_strings': 0.6},
                                        'dyn': [(0, 'mf'), (1, 'f')], 'grow': True, 'level': 0.65}),
                ('hunt', 'episode', 8), ('close', 'close', 4), ('storm', 'dev_dialogue', 8),
                ('fugato', 'dev_fugato', 8), ('retrans', 'retrans', 6),
                ('broad', 'river', 8, {'tex': {'tutti_symphonic': 1.0, 'tutti_drive': 0.05}, 'peak': True,
                                       'dyn': [(0, 'f', 'step'), (1, 'ff')], 'sf': True, 'level': 1.0}),
                ('coda', 'coda', 8), ('end', 'end', 3)],
    # (round o4 - o3's judges: "one section plan for the whole set", 6 of 14: the forms beyond the sonata; a 'var'
    # row's technique is drawn per piece, symphony.VARIATIONS)
    # a rondo (A B A' C - developed - A'' coda): the refrain returns shortened and varied, the episode a new tune
    'rondo': [('intro', 'intro', 4), ('a1', 't1', 8), ('b1', 't2', 8), ('a2', 'refrain', 6), ('c1', 'trio', 8),
              ('dev1', 'dev_dialogue', 8), ('retrans', 'retrans', 6), ('recap', 'recap', 8), ('b2', 'recap2', 6),
              ('coda', 'coda', 6), ('end', 'end', 3)],
    # a theme and variations (no development: the variations are it)
    'variations': [('theme', 't1', 8), ('var1', 'var', 8), ('var2', 'var', 8), ('var3', 'var', 8),
                   ('var4', 'dev_fugato', 8), ('retrans', 'retrans', 4), ('recap', 'recap', 8), ('coda', 'coda', 6),
                   ('end', 'end', 3)],
    # ternary (A A' - a lyrical middle in a far key - the first theme worked (round o11) - A'' as the climax)
    'ternary': [('intro', 'intro', 4), ('t1', 't1', 8), ('t1b', 't1b', 8), ('trans', 'trans', 4), ('mid', 'trio', 8),
                ('mid2', 'trio', 8, {'grow': True, 'dyn': [(0, 'mp'), (1, 'f')], 'level': 0.6}),
                ('dev1', 'dev_dialogue', 8), ('retrans', 'retrans', 6), ('recap', 'recap', 8), ('coda', 'coda', 6),
                ('end', 'end', 3)],
    # an arch (A B C B' A'): the second theme returns before the first
    'arch': [('intro', 'intro', 4), ('t1', 't1', 8), ('trans', 'trans', 4), ('t2', 't2', 8),
             ('dev1', 'dev_dialogue', 10), ('recap2', 'recap2', 8), ('retrans', 'retrans', 4), ('recap', 'recap', 8),
             ('coda', 'coda', 6), ('end', 'end', 3)],
    # through-composed: the development between the themes, the second theme met on the way (round o11 - the
    # masterpiece panel: "the second theme never comes home", DUWT: home after the climax, as in the compact form)
    'through': [('intro', 'intro', 4), ('t1', 't1', 8), ('dev1', 'dev_dialogue', 8), ('trans', 'trans', 4),
                ('t2', 't2', 8), ('dev2', 'dev_fugato', 8), ('hunt', 'episode', 6), ('retrans', 'retrans', 6),
                ('recap', 'recap', 8), ('recap2', 'recap2', 6), ('coda', 'coda', 6), ('end', 'end', 3)],
    # a sonata with a false recapitulation (the first theme in a far key, quiet, then the development goes on)
    'false': [('intro', 'intro', 4), ('t1', 't1', 8), ('trans', 'trans', 4), ('t2', 't2', 8), ('close', 'close', 4),
              ('dev1', 'dev_dialogue', 8), ('false', 'refrain', 4, {'false': True}), ('dev2', 'dev_dialogue', 6),
              ('retrans', 'retrans', 6), ('recap', 'recap', 8), ('recap2', 'recap2', 6), ('coda', 'coda', 6),
              ('end', 'end', 3)],
    # the scherzo and trio (A A' - the trio - A'' da capo as the climax; round o11 - the masterpiece panel, PGFL: "no
    # development at all": the scherzo's theme worked before the da capo, as in the ternary's middle)
    'scherzo_trio': [('t1', 't1', 8), ('t1b', 't1b', 6), ('trio', 'trio', 8), ('trio2', 'trio', 6, {'grow': True}),
                     ('dev1', 'dev_dialogue', 6), ('retrans', 'retrans', 4), ('recap', 'recap', 8), ('coda', 'coda', 4), ('end', 'end', 3)],
    # the river with variations of its theme (the stream, the theme, the theme varied twice, the storm, the broad)
    'journey_var': [('source', 'source', 6), ('river', 'river', 8), ('var1', 'var', 8), ('hunt', 'episode', 6),
                    ('var2', 'var', 8), ('storm', 'dev_dialogue', 8), ('retrans', 'retrans', 6),
                    ('broad', 'river', 8, {'tex': {'tutti_symphonic': 1.0, 'tutti_drive': 0.05}, 'peak': True,
                                           'dyn': [(0, 'f', 'step'), (1, 'ff')], 'sf': True, 'level': 1.0}),
                    ('coda', 'coda', 6), ('end', 'end', 3)],
}


def _symphonic_genre() -> 'Genre':
    # (round o9 - o8's judges: "the choir only in the last 10 bars", FFYD: no texture writes for the choir any more -
    # the chorale climax is the brass choir - and a horn part taken in a coda handed its voice to it as the partner)
    full = tuple(r for r in ORCH_FULL if r != 'choir')
    return Genre(
        name='orchestra-symphonic',
        description='symphonic orchestra with drive and development: a short rhythmic motto stated boldly and worked '
                    'through (sequence, fragmentation, inversion, augmentation, dialogue between the choirs, a '
                    'fugato, the motto in the bass and the brass), running figuration that carries the music, a '
                    'lyrical second theme in a contrasting key, a development that builds over a pedal to the brass '
                    'climax, sudden dynamics - allegro / vivace 6/8 / scherzo / river / andante movements',
        forms={},
        # (round o2: 'slow' - the feel may open with a slow introduction (plan['set']['slow']); 'spans' the
        # proportions it allows (symphony.SPANS; the scherzo's bars count twice))
        # (round o4: 'layouts' - the forms a feel plays; the set's layout draw where the feel has it, else one of
        # these: the scherzo and trio, the river's variations)
        feels={'allegro': {'tempo': (112, 138), 'family': 'duple', 'time_sig': (4, 4), 'energy': 0.8, 'grid': 0.25,
                           'slow': True, 'layouts': ('sonata', 'fugal', 'compact', 'rondo', 'arch', 'through',
                                                     'false')},
               'vivace': {'tempo': (100, 120), 'family': 'compound', 'time_sig': (6, 8), 'energy': 0.72, 'grid': 0.25,
                          'slow': True, 'layouts': ('sonata', 'compact', 'rondo', 'arch', 'through', 'variations',
                                                    'false')},
               'scherzo': {'tempo': (138, 160), 'family': 'compound', 'scale': 2, 'time_sig': (3, 4), 'energy': 0.9,
                           'grid': 0.25, 'layouts': ('compact', 'scherzo_trio'),   # (two 3/4 bars per bar: the
                           'spans': ('tight', 'even')},                           # long layouts sagged, q1)
               'river': {'tempo': (96, 112), 'family': 'compound', 'time_sig': (6, 8), 'energy': 0.6, 'grid': 0.25,
                         'layouts': ('journey', 'journey_var')},
               'andante': {'tempo': (76, 90), 'family': 'duple', 'time_sig': (4, 4), 'energy': 0.4, 'grid': 0.25,
                           'layouts': ('sonata', 'fugal', 'variations', 'ternary', 'arch', 'through')}},
        moods={'heroic': {'feels': {'allegro': 2, 'vivace': 1}, 'modes': {'major': 1},
                          'keys': {'major': ['D', 'Eb', 'Bb', 'C', 'F']}, 'energy': 0.85, 'size': {'full': 1.0},
                          'coda': {'triumph': 1.0}, 'climax': {'brass': 1.0, 'chorale': 0.8, 'strings': 0.5}},
               'stormy': {'feels': {'allegro': 2, 'scherzo': 1}, 'modes': {'minor': 1},
                          'keys': {'minor': ['D', 'C', 'G', 'F', 'E', 'A']}, 'energy': 0.9, 'size': {'full': 1.0},
                          'coda': {'triumph': 0.7, 'dissolve': 0.3}, 'climax': {'brass': 1.0, 'strings': 0.8}},
               'journey': {'feels': {'river': 3, 'vivace': 1}, 'modes': {'minor': 1, 'major': 0.7, 'dorian': 0.5},
                           'keys': {'minor': ['E', 'D', 'G', 'A', 'C'], 'major': ['D', 'G', 'F', 'A'],
                                    'dorian': ['D', 'E', 'A', 'G']},
                           'energy': 0.6, 'size': {'full': 1.0, 'chamber': 0.3},
                           'coda': {'triumph': 0.6, 'dissolve': 0.4},
                           'climax': {'strings': 1.0, 'brass': 0.8, 'chorale': 0.6}},
               'dance': {'feels': {'scherzo': 2, 'vivace': 2}, 'modes': {'major': 1, 'minor': 0.5},
                         'keys': {'major': ['F', 'G', 'A', 'D', 'Bb'], 'minor': ['A', 'D', 'G']}, 'energy': 0.8,
                         'size': {'full': 1.0, 'chamber': 0.5}, 'coda': {'triumph': 1.0},
                         'climax': {'brass': 1.0, 'strings': 0.7}},
               'triumphant': {'feels': {'allegro': 2, 'vivace': 0.5}, 'modes': {'major': 1},
                              'keys': {'major': ['C', 'D', 'Eb', 'Bb']}, 'energy': 1.0, 'size': {'full': 1.0},
                              'coda': {'triumph': 1.0}, 'climax': {'brass': 1.0, 'chorale': 0.9}},
               'mysterious': {'feels': {'andante': 2, 'river': 1}, 'modes': {'minor': 1, 'dorian': 0.6},
                              'keys': {'minor': ['B', 'E', 'C#', 'F#', 'C'], 'dorian': ['D', 'E', 'B', 'A']},
                              'energy': 0.4,
                              'size': {'chamber': 1.0, 'full': 0.7}, 'coda': {'dissolve': 0.7, 'triumph': 0.3},
                              'climax': {'quiet': 1.0, 'strings': 0.8, 'chorale': 0.5}},
               'lyrical': {'feels': {'andante': 2, 'vivace': 1}, 'modes': {'major': 1, 'minor': 0.6},
                           'keys': {'major': ['Eb', 'Ab', 'F', 'G'], 'minor': ['G', 'C', 'F']}, 'energy': 0.35,
                           'size': {'chamber': 1.0, 'full': 0.6}, 'coda': {'dissolve': 0.6, 'triumph': 0.4},
                           'climax': {'strings': 1.0, 'quiet': 0.8, 'chorale': 0.6}}},
        # (the same band set-up as orchestra-film: endless.orchestra.band; 'romantic' style - more swell)
        band={'preset': 'film_orchestra', 'profile': 'classical', 'loudness': (-24.0, -13.0), 'style': 'romantic',
              'gain': 8.0, 'master': 'master/film-lyrical', 'line_phrasing': 0.9,
              # (round o2: the samples' edit-splice glitches repaired - the gate's "no single track" sum clicks)
              'options': {'choir': 'oh', 'repair': 9.0},
              'trims': {'percussion': -8.0, 'choir': -6.0, 'clarinets': -3.0}},
        plan={'perform': 'symphony', 'candidates': 4, 'sizes': {'chamber': ORCH_CHAMBER, 'full': full},
              'kinds': _SYM_KINDS, 'layouts': _SYM_LAYOUTS,
              # the orchestrator's rules: the plans set their own dynamics (no automatic step), a loud coda allowed
              # (round o3: 'reserve' - the top register kept for the climax)
              # (round o11 - the masterpiece panel: "no hierarchy of climaxes": the summit's top note 3 semitones
              # over everything before it, and over everything after it)
              # (round o12 - o11's judges: "the summit margin lowered the melody", folds 0.79 -> 1.54: the lines'
              # margin 1, the accompaniment's 3 - symphony.SUMMIT raises the summit's violins over the tunes before it)
              'rules': {'coda_light': False, 'dyn_peak': 0, 'dyn_light': 0, 'bass_floor': False, 'idiom': True,
                        'power_line': 8.0, 'reserve': 3, 'reserve_after': True, 'reserve_lines': 1},
              # the piece's draws (composer.set_draws: never the slot before's in a set)
              # (round o4 - o3's judges: "one section plan for the whole set": the rondo, the variations, ternary,
              # the arch, the through-composed journey, the false recapitulation; a feel's 'layouts' its own)
              'set': {'layout': {'sonata': 0.6, 'fugal': 0.5, 'compact': 0.4, 'rondo': 1.0, 'variations': 0.8,
                                 'ternary': 0.8, 'arch': 0.8, 'through': 0.8, 'false': 0.7},
                      # (round o3, the melodist: mottos with a leap and a peak - the repeated-note signals rarer;
                      # symphony.MOTTO_CHARACTER takes the next cell when a landing leaves none)
                      'motto': {'duple': {'knock': 0.25, 'hammer': 0.5, 'dotted': 1.0, 'snap': 0.7, 'call': 0.9,
                                          'leap': 1.0, 'turn': 0.7, 'spring': 1.0, 'arch': 1.0, 'fanfare': 0.9,
                                          'plunge': 0.7},
                                'compound': {'gallop': 1.0, 'knock': 0.2, 'lilt': 0.9, 'hunt': 1.0, 'dotted': 0.8,
                                             'swing': 0.7, 'leap': 1.0, 'soar': 0.9, 'fall': 0.7}},
                      'land': {3: 1.0, 4: 0.8, -1: 0.6, 1: 0.6, 2: 0.4, 5: 0.4, -3: 0.6, -4: 0.4},
                      'member': {'fifth': 1.0, 'root': 0.8, 'third': 0.6},
                      'answer': {'dominant': 1.0, 'step_up': 0.7, 'step_down': 0.5, 'invert': 0.4},
                      'intro': {'call': 1.0, 'mist': 0.6, 'source': 0.5, 'solo': 0.7},
                      'key2': {'relative': 1.0, 'dominant': 1.0, 'mediant': 0.4},
                      'dev_path': {'rise': 1.0, 'fifths': 1.0, 'thirds': 0.5, 'fall': 0.6},
                      'dev_mode': {'minor': 1.0, 'same': 0.5},   # (read by nothing any more - kept: the
                      #  set draws share one seeded stream - composer.set_draws: removed, it re-rolls every plan)
                      'entry': {'down': 1.0, 'pickup': 0.8},
                      'skeleton': {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 0.8},
                      'retrans_end': {'gp': 1.0, 'fermata': 0.6, 'direct': 0.5},
                      # (round o2: the q1 judges read the pieces as one plan family - the development's blocks,
                      # the proportions, a slow introduction, the call's first colour, the coda per set)
                      'dev': {'dialogue_fugato': 1.0, 'fugato_dialogue': 0.7, 'dialogue': 0.6, 'storm': 0.7,
                              'fugato': 0.4},
                      'span': {'even': 1.0, 'tight': 0.8, 'broad': 0.7},
                      'slow': {0: 1.0, 1: 0.6},
                      'colour': {'strings': 1.0, 'brass': 0.8},
                      'coda': {'triumph': 1.0, 'dissolve': 0.6},
                      # (the climax's type, the build before it, the orchestra's size: where the mood has them -
                      # symphony.CLIMAXES / BUILDS; the user 2026-10-16: diversity across the set)
                      'climax': {'brass': 1.0, 'strings': 0.9, 'chorale': 0.7, 'quiet': 0.5},
                      # (round o3, the judges' tells: one stock build, a development without the motto, the climax
                      # as the theme in octaves, the same material in every piece - the builds from the motto, the
                      # development's technique, the climax's material, the colours of the source and of the second
                      # theme, the accompaniment's family, the ending, the second theme from the motto: symphony.
                      # BUILDS / DEV_TECH / APEX / SOURCES / T2_COLOURS / ACCOMPANIMENTS / ENDINGS)
                      'build': {'tremolo': 0.4, 'pulse': 0.5, 'stretto': 1.0, 'calls': 0.9, 'bass': 0.9,
                                'fugato': 0.8, 'subito': 0.9},
                      # (round o6: 'theme' - the first theme's opening sequenced and imitated, then fragmented)
                      'dev_tech': {'sequence': 0.8, 'fragment': 1.0, 'stretto': 0.9, 'combine': 0.8, 'bass': 0.8,
                                   'theme': 1.2},
                      # (round o6 - o5's judges: "the climax brings a new hymn": the motto / the first theme on
                      # top - 'theme_aug', the new 'combine' -, the second theme's apotheosis rarer)
                      # (round o11 - the masterpiece panel: "the climax transforms the motto, never a literal
                      # restatement" and "the summit in the home key or its parallel": no 'restate', no 'relative')
                      'apex': {'augment': 1.0, 'theme_aug': 0.9, 'combine': 1.0, 'reharm': 0.8, 'second': 0.35},
                      # (round o6: the climax's key per set - symphony.CLX_MODES)
                      'clx_mode': {'home': 1.0, 'picardy': 0.8, 'parallel': 0.4},
                      'src': {'flutes': 0.25, 'strings': 1.0, 'low': 1.0, 'murmur': 0.9},
                      't2col': {'winds': 0.6, 'horn': 1.0, 'cello': 1.0, 'pulse': 1.0, 'choir': 0.9,
                                'strings': 0.7},
                      'acc': {'pulse': 1.0, 'rock': 1.0, 'motto': 1.0, 'sync': 0.8},
                      # (round o5: every ending a voiced cadence - V7 / IV then the tonic: symphony.ENDINGS)
                      'ending': {'cadence': 1.0, 'strokes': 0.9, 'motto': 0.8, 'held': 0.7, 'plagal': 0.7},
                      'derive': {'plain': 1.0, 'invert': 0.8, 'none': 0.4},
                      'size': {'full': 1.0, 'chamber': 0.6},
                      # (round o4: the build's harmonic frame - not always the dominant pedal -, phrases of 6 / 10 /
                      # 12 bars, one elided cadence: symphony.BUILD_FRAMES / PHRASES / ELIDE)
                      'frame': {'pedal': 0.5, 'ascent': 1.0, 'circle': 0.9, 'lament': 0.8},
                      'phrase': {'square': 0.4, 'free': 1.0},
                      'elide': {0: 1.0, 1: 0.8},
                      # (round o5 - o4's judges: the 6/8 pieces' one coda plan and one 8-bar opening ostinato: the
                      # coda's plan, the source's frame and entries - symphony.CODA_PLANS / SOURCE_CHARTS /
                      # SOURCE_ENTRIES)
                      'coda_plan': {'stretto': 1.0, 'pedal': 0.9, 'hymn': 0.8, 'descent': 1.0, 'echo': 0.9,
                                    'memory': 0.8},
                      'src_chart': {'plagal': 1.0, 'circle': 0.9, 'pedal': 0.7},
                      'src_entry': {'late': 0.8, 'early': 1.0, 'answer': 1.0},
                      # (round o10 - o9's judges: "a solo cello entry growing into a fugato" in 4 of 8 pieces: the
                      # fugato's entry order - symphony.FUGUE_ORDERS)
                      'fug_order': {'rise': 0.5, 'fall': 1.0, 'inner': 0.9, 'outer': 0.8}},
              'set_memory': {'dev': 2, 'intro': 2, 'span': 1, 'layout': 3, 'slow': 0, 'colour': 0, 'coda': 1,
                             'climax': 2, 'build': 2, 'size': 0, 'dev_tech': 2, 'apex': 3, 'src': 2, 't2col': 2,
                             'acc': 2, 'ending': 3, 'derive': 0, 'frame': 2, 'phrase': 0, 'elide': 0,
                             'coda_plan': 2, 'src_chart': 1, 'src_entry': 1, 'clx_mode': 2, 'fug_order': 2}},
        harmony={'blocks': {}, 'colours': {}, 'intros': {}, 'endings': {}},
        titles={'adj': ['Heroic', 'Restless', 'Rising', 'Northern', 'Burning', 'Wild', 'Distant', 'Golden', 'Iron',
                        'Silver', 'Bright', 'Endless', 'Open', 'Stormy', 'Hidden'],
                'noun': ['Rivers', 'Horizons', 'Mountains', 'Tides', 'Banners', 'Riders', 'Storms', 'Fields', 'Fires',
                         'Winds', 'Voyages', 'Wings', 'Forests', 'Bells'],
                'time': ['the Dawn', 'the North', 'the Sea', 'Winter', 'the Plains', 'Home', 'the Valley', 'Summer',
                         'the Harvest', 'the Storm'],
                'shapes': ['{adj} {noun}', 'The {adj} {noun}', '{noun} of {time}', 'Overture: {adj} {noun}',
                           'Toward {time}', '{adj} {noun} of {time}', 'Symphonic Dance: {noun} of {time}'],
                'suffix': {'': ''}},
        album='Endless Orchestra', style='symphony', arc=_symphonic_arc())


def _symphonic_arc() -> dict:
    # (round o2: the q1/o1 sets ran one feel order - river, vivace, andante, river, scherzo ... at the same tempos
    # every set; the dice on the feel's distance, at most two of a feel, the tempo spread over the feel's range)
    # (round o19a - o18b's judges: "bars 93-104 are identical to JDGP bars 73-84": two F major scherzos of one set
    # played the same development chart and voicing - no key twice per time signature in a set, composer._slot)
    a = copy.deepcopy(ARCS)
    a['set'].update(feel_noise=0.35, feel_max=2, tempo_spread=0.4, key_apart=True)
    return a


ORCHESTRA_SYMPHONIC = _symphonic_genre()

GENRES = {g.name: g for g in (JAZZ_PIANO, JAZZ_TRIO, NEW_AGE_PIANO, CLASSICAL_PIANO, LOFI_PIANO, NEW_AGE_EPIANO,
                               ORGAN, ORCHESTRA_FILM, ORCHESTRA_SYMPHONIC)}
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
# -- the hands' balance and the register (HUMAN_FEEDBACK 2026-10-15, composer.hands_tells; the user's ask, not the
# references': the twelve hand-written pieces play the old fixed budget - hand_bal 4.7-6.8, sd 0.7-1.6 - and sit
# higher, rh_c6 0.09-0.37, rh_med 75-81): before the dynamic balance / the ceiling the generator measured hand_bal
# 3.5-6.0, sd 1.0-2.3, rh_c6 up to 0.2(a theme climax an octave up). Round g9: hand_bal 3-5 -> 3-6: the blind judges of
# g7 / g8 asked for the melody ~4-5 dB over a quieter left hand (A, B1, the build), the references measure 4.7-6.8,
# and the generator sits at 5.2-5.3 (each piece lost ~0.3 points to the old 5 dB ceiling)
_SCORE_NEWAGE.update(
    hand_bal=(3, 6, 0.5, False, 1),                # the right hand over the left per phrase (note energy dB)
    hand_bal_sd=(1.5, 4, 0.5, False, 0.5),         # ... and it moves
    rh_c6=(0, 0.06, 1, False, 0.04),               # right-hand notes at or above C6: a rare event
    rh_e6=(0, 0.015, 0.5, False, 0.01))            # ... at or above E6: the peak, a sparkle
# -- the right hand's flow (HUMAN_FEEDBACK 2026-10-15, composer.flow_tells; the user's ask: "note by note, as if he
# had only one finger"): before plan['texture'] / plan['line'] the generator measured mel_rate 0.84, dvel_med 6.2,
# rh_multi 0.07 (A1 0.01, the chorus 0.01, the climax 0.27), inner_move 0.21 (48 seeds)
_SCORE_NEWAGE.update(
    mel_rate=(0.9, 1.5, 0.5, False, 0.2),          # the melody's onsets per beat (connecting notes)
    dvel_med=(1.5, 4.5, 1, False, 1.5),            # the median velocity step between melody notes: one line
    rh_multi=(0.25, 0.6, 1, False, 0.1),           # right-hand onsets with 2+ notes (dyads, chords, octaves)
    inner_move=(0.15, 0.7, 0.5, False, 0.1))       # held melody notes with an inner voice moving under them
# -- the theme's profile (round g8, all five judges: heads circling a 2-3 note band; composer.head_profile): the
# head leaps a 4th+, holds its top note, circles no band - 1 = yes (generated before the fix 0.21, after 0.94)
_SCORE_NEWAGE.update(head_prof=(1, 1, 1.5, False, 1))

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
    textures=(6, 12, 1, False, 1))           # distinct role sets over the sections                    8-10
"""orchestra: the new-age composer's melodic ranges on the reduction + the orchestration metrics (endless/orchestra.py
orchestra_metrics; docs/ORCHESTRA_ENDLESS.md section 6)."""

_SCORE_SYMPHONY = dict(
    # PROVISIONAL (no hand-written reference of the symphonic kind yet; ranges from the pro-orch-* orchestration
    # where it carries over, the rest from the brief: HUMAN_FEEDBACK 2026-10-16 - drive, development, contrast)
    {k: v for k, v in _SCORE_ORCHESTRA.items() if k in ('range_out', 'sweet_mel', 'gap_hi', 'low_thirds', 'mel_db',
                                                       'colour_chg')},
    tutti=(0.1, 0.4, 1, False, 0.08),        # bars with 75 %+ of the roles: tutti against solo / chamber
    roles_sd=(2.4, 5.0, 1.5, False, 0.8),     # the texture changes (roles per bar spread)
    db_bar_sd=(7.0, 12.0, 1.5, False, 1.5),  # the bar-to-bar level spread (terraced / sudden dynamics)
    dyn_rng=(13, 24, 1, False, 3),           # the note-energy range (2-bar windows, dB)
    textures=(8, 16, 1, False, 1),           # distinct role sets over the sections
    motto=(16, 80, 1, False, 6),             # motto statements (symphony.motto_stats; a short cell, worked)
    motto_tf=(4, 9, 1, False, 1),            # distinct transforms of it (plain, head, invert, augment ...)
    motto_roles=(5, 16, 1.5, False, 2),      # the roles that carry it (its colour changes)
    motto_bass=(1, 12, 1, False, 1),         # statements in the bass
    nps=(4.0, 14.0, 1, False, 2),            # attacks per second over all parts (drive; the film pieces ~2-3)
    run_share=(0.3, 0.98, 1, False, 0.1),    # attacks 0.3 s apart or closer (a running line)
    clash=(0, 4, 2, False, 2),               # theme notes clashing / leaping (melody_issues per 100 notes)
    # (round o11 - the masterpiece panel rated the 99.8 piece among the weakest, ASFP: the form's argument -
    # symphony.form_stats; the references: a development of 25-33 %, the second theme home, one summit at 65-85 %)
    dev_share=(0.22, 0.34, 2, False, 0.05),  # the development's share of the bars
    seq_links=(0, 2, 2, False, 1),           # a unit transposed unchanged at most twice in a row
    t1_home=(1, 1, 2, False, 1),             # the first theme home at or after the climax
    t2_home=(1, 1, 2, False, 1),             # the second theme home
    recap_weight=(0.9, 2.5, 1, False, 0.2),  # the return against the exposition
    cadence_end=(1, 1, 2, False, 1),         # the last chords V - I
    peak_pos=(0.62, 0.86, 1.5, False, 0.08),  # the climax's centre
    top_peak=(1, 1, 1.5, False, 1),          # the highest note in the climax
    pre_semis=(2, 24, 1.5, False, 1),        # the climax's top over everything before it (semitones)
    seconds=(180, 480, 1.5, False, 30),      # a movement, not an exposition
    # (round o12 - o11's judges: "the development a row of textures", "the summit without brass and top", "68 bars on
    # one accompaniment": symphony.own_stats / summit_stats; dev_own a gate - the references 0.8+)
    dev_own=(0.8, 1.0, 2, True, 0.1),        # the development's bars on the piece's own material
    tutti_peak=(1, 1, 1, False, 1),          # the fullest tutti at the peak
    vln_over=(3, 24, 1.5, False, 2),         # the summit's violins over every line before it (semitones)
    brass_peak=(2, 2, 1, False, 1),          # the trumpets and the trombones on the climax's line
    acc_run=(0, 8, 1.5, False, 2))           # the longest unchanged accompaniment (song bars)
"""symphony: the orchestration metrics + the motto's life and the drive + the form's argument (endless/symphony.py
symphony_metrics) - the full table; SCORES['symphony'] ranks on symphony_table() (SYMPHONY_GATES)."""

SYMPHONY_GATES = ('seq_links', 'acc_run', 'vln_over', 'tutti_peak', 'brass_peak', 't1_home', 't2_home',
                  'cadence_end', 'seconds', 'dev_share', 'peak_pos', 'top_peak', 'pre_semis')
"""The symphony metrics a construction rule guarantees with the same threshold (the code review's G1,
songs/_endless_orchestra/out/code_review/REPORT.md: DEV_LADDER links, TEX_RUN, SUMMIT over / fill / brass, RETURN and
the recap2 rows, ENDING_CADENCE, MIN_LEN, DEV_SHARE, PROPORTION, the reserve): best-of-N must not rank on them - it
would select on what every candidate has. They stay ASSERTIONS: weight 0 and hard, so a candidate that misses one is
capped (SCORE_HARD_CAP, listed in score()['hard'] - the runner logs it) and the ranking among the passing ones is on
the rest (the motto's life, the drive, the clashes, the orchestration statistics, the dev_own gate)."""
SYMPHONY_RANK_GATES = False
"""True: the old ranking (round o12's: the SYMPHONY_GATES weighted in the mean) - for paired tests against it; set it
through symphony_ranking(), which rebuilds SCORES['symphony'] in place."""


SYMPHONY_DERIVE = False
"""True (round o16, with symphony.DEV_WALK on): the dev_own gate (window matching) gives way to the derivation graph's
metrics (symphony.derive_stats) - SYMPHONY_DERIVE_ROWS; set it through symphony_derive()."""
SYMPHONY_DERIVE_ROWS = dict(
    dev_ops=(4, 16, 1.5, True, 1),           # distinct transform ops in the development (the graph; round o17: v2's
    #                                          worked processes keep the chains at 2 ops - 4 at least, o16's 6)
    dev_literal=(0, 6, 1, True, 1),          # the whole motto restated unchanged there (o17: a stretto's subject is
    #                                          the motto - its entries count; o16's at most 1)
    dev_depth=(0.5, 6, 1, False, 0.5),       # the chains' depth rising toward the retransition
    motto_tf=(4, 40, 1, False, 1),           # distinct transforms (the walk's chains: many by construction)
    motto=(16, 300, 1, False, 6))            # statements (every derived cell is one)
"""The derivation graph's rows (SYMPHONY_DERIVE); dev_own stays measured at weight 0, no gate."""


def symphony_table(rank_gates: bool | None = None) -> dict:
    """The symphony's score table: _SCORE_SYMPHONY with the SYMPHONY_GATES as weight-0 hard assertions, or (rank_gates
    True; default SYMPHONY_RANK_GATES) the full table as it ranked through round o12; SYMPHONY_DERIVE: the graph's
    rows for the dev_own gate."""
    if SYMPHONY_RANK_GATES if rank_gates is None else rank_gates:
        out = dict(_SCORE_SYMPHONY)
    else:
        out = {k: (v[0], v[1], 0, True) + tuple(v[4:]) if k in SYMPHONY_GATES else v
               for k, v in _SCORE_SYMPHONY.items()}
    if SYMPHONY_DERIVE:
        v = out['dev_own']
        out['dev_own'] = (v[0], v[1], 0, False) + tuple(v[4:])
        out.update(SYMPHONY_DERIVE_ROWS)
    if SYMPHONY_SETPLAN:
        out.update({k: (v[0], v[1], 0 if k in SYMPHONY_GATES and not (SYMPHONY_RANK_GATES if rank_gates is None
                                                                       else rank_gates) else v[2]) + tuple(v[3:])
                    for k, v in SETPLAN_ROWS.items()})
    return out


def symphony_derive(on: bool) -> None:
    """Switch the derivation graph's rows (SYMPHONY_DERIVE) - SCORES['symphony'] rebuilt in place."""
    global SYMPHONY_DERIVE
    SYMPHONY_DERIVE = bool(on)
    SCORES['symphony'].clear()
    SCORES['symphony'].update(symphony_table())


SYMPHONY_SETPLAN = False
"""True (round o18b, with symphony.SET_PLAN on): the set-level choices of orchestra-symphonic diverse and memoryful -
SETPLAN_SET's draws (the build gestures, the arc, the summit's voicing, the climax's contour, the ending families, the
mottos with their rhythm families - plan['set_groups']), SETPLAN_MEMORY, the meter mix of the set arc (SETPLAN_ARC)
and SETPLAN_ROWS in the score; set it through symphony_setplan()."""
SETPLAN_SET = {
    'build': {'swell': 1.0, 'silence': 0.9, 'fugato': 0.8, 'lowbrass': 0.9, 'deceptive': 0.9, 'stretto': 0.8,
              'calls': 0.8, 'bass': 0.7, 'pulse': 0.5, 'subito': 0.8},
    'ending': {'motto': 1.0, 'amen': 0.9, 'deceptive': 0.9, 'line': 0.9, 'strokes': 0.8, 'cadence': 0.5},
    'arc': {'return': 1.0, 'crisis': 0.45},
    # (round o19a - SET_PLAN v2: the layout's section count and the climax's place per piece, symphony.FORM_SHAPE / PEAK_AT)
    'sections': {-2: 0.6, -1: 1.0, 0: 0.8, 1: 1.0, 2: 0.6},
    'peak_at': {0.6: 0.9, 0.66: 1.0, 0.72: 0.8, 0.8: 0.9, 0.88: 0.8},
    'layout': {'sonata': 0.6, 'fugal': 0.5, 'compact': 0.6, 'rondo': 1.0, 'variations': 0.8, 'ternary': 0.8, 'arch': 0.8,
               'through': 0.8, 'false': 0.7, 'scherzo_trio': 1.0, 'journey': 1.0, 'journey_var': 1.0},
    'voicing': {'layers': 1.0, 'tutti': 0.7},
    'contour': {'wave': 1.0, 'arch': 0.9, 'terrace': 0.8, 'rise': 0.4},
    'climax': {'brass': 1.0, 'strings': 0.9, 'chorale': 0.8, 'quiet': 0.6},
    'motto': {'duple': {'knock': 0.2, 'hammer': 0.3, 'dotted': 0.8, 'snap': 0.7, 'call': 0.5, 'leap': 1.0, 'turn': 0.7,
                        'spring': 0.5, 'arch': 1.0, 'fanfare': 0.8, 'plunge': 0.4, 'synco': 0.8, 'trochee': 0.8},
              'compound': {'gallop': 0.8, 'knock': 0.2, 'lilt': 0.6, 'hunt': 0.8, 'dotted': 0.8, 'swing': 0.7,
                           'leap': 0.8, 'soar': 0.6, 'fall': 0.6, 'hemiola': 0.8, 'sigh': 0.8, 'anacrusis': 0.7}}}
"""SYMPHONY_SETPLAN's draws over plan['set'] (symphony.GESTURES / END_FAMILIES / ARC_CRISIS / VOICING / CONTOURS /
CELLS_V): 'tremolo' (the stock timpani-pedal build) is no build any more, the short-short-long mottos rarer; the
layout drawn among the slot's feel's own (plan['set_feel']: the scherzo's and the river's forms in the memory too)."""
SETPLAN_MEMORY = {'build': 4, 'ending': 4, 'motto': 3, 'climax': 3, 'apex': 3, 'arc': 0, 'voicing': 0, 'contour': 2,
                  'layout': 4, 'intro': 3, 'coda_plan': 3, 'frame': 0, 'sections': 2, 'peak_at': 2}
"""SYMPHONY_SETPLAN's set memory over plan['set_memory'] (a build gesture / an ending family never twice in 5 pieces,
a motto rhythm family never in 4 - plan['set_groups'] symphony.MOTTO_FAMILIES)."""
SETPLAN_ARC = {'meter_share': (((6, 8), 0.3125), ((4, 4), 0.5625), ((3, 4), 0.125)), 'meter_gap': True}
"""SYMPHONY_SETPLAN's set arc keys (composer._slot): the 6/8 in at most 5 of 16, the 4/4 in 9, the 3/4 (the scherzo) in
2 (round o19a - o18b: 4 of 16, one panel heard the scherzo's form twice), and no meter twice running."""
SETPLAN_SHAPE = {'by': 'feel', 'keys': ('layout', 'sections')}
"""SYMPHONY_SETPLAN's plan['set_shape'] (round o19a, composer._set_shape): a feel's layout with its section count
(symphony.FORM_SHAPE) never twice in a set - the memory on the layout's shape, not its name."""
SETPLAN_ROWS = dict(peak_pos=(0.42, 0.92, 1.5, True, 0.08), brass_peak=(1, 2, 1, True, 1))
"""SYMPHONY_SETPLAN's score rows: the crisis's climax earlier (peak_pos), the layered summit's trombones on the chords
(brass_peak) - still assertions (weight 0, hard: SYMPHONY_GATES)."""
SETPLAN_SET_V3 = dict(
    SETPLAN_SET,
    # (round o20 - SET_PLAN v3: no crisis arc - 5 of 5 slots lost or tied over o18b / o19a)
    arc={'return': 1.0},
    # (the shape by merging: 0 .. 3 blocks folded into the one before - symphony.FORM_MERGE; the climax at 0.7 or
    # later - PEAK_AT_V3; the section textures - TEX_V3)
    sections={-3: 0.6, -2: 1.0, -1: 1.0, 0: 0.8},
    peak_at={0.7: 1.0, 0.74: 0.9, 0.78: 0.9, 0.82: 0.8, 0.86: 0.7},
    tex_t1={'drive_strings': 1.0, 'walk_dialogue3': 0.8, 'cantabile_strings': 0.6, 'running_strings': 0.4,
            'tutti_drive': 0.5},
    tex_t1b={'motto_bass': 0.8, 'tutti_drive': 1.0, 'motto_brass': 0.7, 'dialogue_brass': 0.7},
    tex_dev={'dialogue': 0.6, 'dialogue_brass': 0.8, 'dev_poly': 1.0, 'walk_dialogue3': 0.9, 'walk_poly': 0.9})
"""SET_PLAN v3's draws (round o20, symphony.SET_PLAN_V3): v2's, without the crisis arc, the shape's merges, the
climax's later places and the section textures (symphony.TEX_V3)."""
SETPLAN_MEMORY_V3 = dict(SETPLAN_MEMORY, tex_t1=3, tex_t1b=2, tex_dev=3, t2col=4, src=3)
"""SET_PLAN v3's set memory: the textures of the first theme / its restatement / the development and the second
theme's colour never within that many pieces (o19a's judges: "16-bar dialogue", "oboe line over pulsing bass")."""
SETPLAN_SET_V4 = dict(
    SETPLAN_SET_V3,
    # (round o22 - SET_PLAN v4: the sentence's fragmentation by a shape - symphony.FRAG_V4, the old ladder 'rise' the
    # rarest; the piece's bar plan by its slot - symphony.bar_plan)
    frag={'rise': 0.5, 'wave': 1.0, 'terrace': 0.9, 'fall': 0.8, 'arch': 0.9},
    form_seed={j: 1.0 for j in range(64)})
"""SET_PLAN v4's draws (round o22, symphony.SET_PLAN_V4): v3's, the fragmentation's shape ('frag') and the seed of the
piece's bar plan ('form_seed')."""
SETPLAN_MEMORY_V4 = dict(SETPLAN_MEMORY_V3, frag=3, form_seed=0)
"""SET_PLAN v4's set memory: a fragmentation shape never within three pieces (the ladder like the build gestures)."""
SETPLAN_ARC_V4 = dict(SETPLAN_ARC, key_max=2, mode_quota=(2, 8), major_run=3,
                      end_alt={'loud': 'triumph', 'soft': 'dissolve', 'run': 2})
"""SET_PLAN v4's set arc keys (round o22 - o20's set judges, 7 of 7 against a programme of seven major pieces, F major
three times, six loud endings of eight; composer._slot / set_plan): 'key_max' - no key more than twice in a set, over
every time signature (key_apart stays per meter); 'mode_quota' (q, per) - at least q minor or modal pieces per `per`
(the slot that the quota needs, or after 'major_run' major pieces in a row, takes a mood with a minor / modal mode and
that mode); 'end_alt' - the endings' dynamic alternates: a dissolving coda never after a dissolving one, never more
than 'run' loud ones in a row (the slot takes a mood that has the coda it needs)."""
SETPLAN_SHAPE_V4 = {'by': 'feel', 'keys': ('layout',)}
"""SET_PLAN v4's plan['set_shape']: a feel's LAYOUT never twice in a set (o20: two allegro rondos, pieces 2 and 7 -
"3|12|12|8|12" - with different merge counts)."""
SETPLAN_BARS = {'sim': 0.4, 'tol': 1, 'keys': ('sections', 'peak_at', 'form_seed', 'phrase', 'span', 'layout'),
                'tries': 48}
"""SET_PLAN v4's memory on the realised bar plan (composer.set_plan, symphony.bar_plan): two pieces' section lengths
the same within 'tol' song bars at the same section index for more than 'sim' of the longer plan's sections are
twins (o20's set judges heard 0.64 as "piece 7 replays piece 2"; the set the judges preferred 5 of 7 stayed under
0.37) - the slot's 'keys' are drawn again (up to 'tries' candidates, the layout among the feel's own the set has
not played in that feel; the first under 'sim', else the least similar)."""
SETPLAN_VERSIONS = {1: 'SET_PLAN_V1', 2: 'SET_PLAN_V2', 3: 'SET_PLAN_V3', 4: 'SET_PLAN_V4'}
"""symphony_setplan(True, version): the version's symphony.SET_PLAN table (v1: o18b, v2: o19a, v3: o20, v4: o22 - the
default); v3 also takes SETPLAN_SET_V3 / SETPLAN_MEMORY_V3, v4 SETPLAN_SET_V4 / SETPLAN_MEMORY_V4 / SETPLAN_ARC_V4 /
SETPLAN_SHAPE_V4 / SETPLAN_BARS."""
SETPLAN_VERSION = 4
_SETPLAN_SAVED: dict = {}


def symphony_setplan(on: bool, version: int | None = None) -> None:
    """Switch SYMPHONY_SETPLAN (and symphony.SET_PLAN): ORCHESTRA_SYMPHONIC's set draws, memory, groups and set arc,
    the motto cells (symphony.CELLS_V), the score's rows - restored as they were when switched off. version: 1 / 2 / 3
    (SETPLAN_VERSIONS; default SETPLAN_VERSION) - switch off before changing it."""
    global SYMPHONY_SETPLAN
    from . import symphony as S
    G = ORCHESTRA_SYMPHONIC
    on = bool(on)
    ver = int(version or SETPLAN_VERSION)
    if ver not in SETPLAN_VERSIONS:
        raise ValueError(f"symphony_setplan: version {ver!r} - one of {sorted(SETPLAN_VERSIONS)}")
    if on and SYMPHONY_SETPLAN and S.SET_PLAN != getattr(S, SETPLAN_VERSIONS[ver]):
        symphony_setplan(False)
    if on and not SYMPHONY_SETPLAN:
        _SETPLAN_SAVED.update(set=G.plan['set'], memory=G.plan['set_memory'], groups=G.plan.get('set_groups'),
                              shape=G.plan.get('set_shape'),
                              arc=G.arc['set'], cells={f: dict(c) for f, c in S.CELLS.items()})
        for f, c in S.CELLS_V.items():
            S.CELLS[f].update(c)
        G.plan['set'] = dict(G.plan['set'], **(SETPLAN_SET_V4 if ver >= 4 else SETPLAN_SET_V3 if ver >= 3 else
                                               SETPLAN_SET))
        G.plan['set_memory'] = dict(G.plan['set_memory'], **(SETPLAN_MEMORY_V4 if ver >= 4 else SETPLAN_MEMORY_V3
                                                             if ver >= 3 else SETPLAN_MEMORY))
        G.plan['set_groups'] = {'motto': S.MOTTO_FAMILIES}
        G.plan['set_feel'] = ('layout',)
        G.plan['set_shape'] = dict(SETPLAN_SHAPE_V4 if ver >= 4 else SETPLAN_SHAPE)
        if ver >= 4:                       # (round o22: the memory on the realised bar plan - composer.set_plan)
            G.plan['set_bars'] = dict(SETPLAN_BARS)
        G.arc['set'] = dict(G.arc['set'], **(SETPLAN_ARC_V4 if ver >= 4 else SETPLAN_ARC))
        S.SET_PLAN = dict(getattr(S, SETPLAN_VERSIONS[ver]))
    elif not on and SYMPHONY_SETPLAN:
        G.plan['set'], G.plan['set_memory'] = _SETPLAN_SAVED['set'], _SETPLAN_SAVED['memory']
        G.plan.pop('set_feel', None)
        G.plan.pop('set_bars', None)
        if _SETPLAN_SAVED.get('shape') is None:
            G.plan.pop('set_shape', None)
        else:
            G.plan['set_shape'] = _SETPLAN_SAVED['shape']
        if _SETPLAN_SAVED['groups'] is None:
            G.plan.pop('set_groups', None)
        else:
            G.plan['set_groups'] = _SETPLAN_SAVED['groups']
        G.arc['set'] = _SETPLAN_SAVED['arc']
        for f, c in _SETPLAN_SAVED['cells'].items():
            S.CELLS[f].clear()
            S.CELLS[f].update(c)
        S.SET_PLAN = None
    SYMPHONY_SETPLAN = on
    SCORES['symphony'].clear()
    SCORES['symphony'].update(symphony_table())


def symphony_ranking(rank_gates: bool) -> None:
    """Switch the best-of-N ranking of orchestra-symphonic (SYMPHONY_RANK_GATES) - SCORES['symphony'] rebuilt in place,
    so composer.score and the runner pick it up."""
    global SYMPHONY_RANK_GATES
    SYMPHONY_RANK_GATES = bool(rank_gates)
    SCORES['symphony'].clear()
    SCORES['symphony'].update(symphony_table())


def symphony_tech(on: bool) -> None:
    """Switch the playing techniques of orchestra-symphonic (round o23): symphony.TECH (the palette written into the
    parts), the set's technique draw with memory (plan['set_tech']: composer.set_plan) and the band's technique
    sounds (orch.TECH_SOUNDS: the brass mutes, the col legno / harmonics levels) - all off restores the old renders."""
    from ..bandlib import orchestra as orch_
    from . import symphony as S
    G = ORCHESTRA_SYMPHONIC
    S.TECH = dict(S.TECH_ON) if on else None
    orch_.TECH_SOUNDS = bool(on)
    if on:
        G.plan['set_tech'] = True
    else:
        G.plan.pop('set_tech', None)


SYMPHONY_SHAPE = False
"""True (round o24, symphony.MACRO on): orchestra-symphonic's macro shapes and the technique fixes - set it through
symphony_shape()."""


def symphony_shape(on: bool) -> None:
    """Switch round o24's MACRO: symphony.MACRO (the macro shape - the opening, the climax's place / count / kind, the
    ending - drawn per set slot with the whole set's memory, plan['set_macro']: composer.set_plan -> symphony.
    shape_slot) and TECH['v2'] (symphony.TECH_V2: the techniques carry the material, the whole set's technique memory,
    the harmonics' home, the harp glissando heard) - off restores master. Apply BEFORE the set plan is drawn (and after
    symphony_tech: v2 rides on the technique palette)."""
    global SYMPHONY_SHAPE
    from . import symphony as S
    G = ORCHESTRA_SYMPHONIC
    on = bool(on)
    S.MACRO = dict(S.MACRO_ON) if on else None
    if S.TECH is not None:
        S.TECH = dict(S.TECH, v2=dict(S.TECH_V2), feature=S.TECH_V2['feature'], feature1=S.TECH_ON['feature']) \
            if on else dict({k: v for k, v in S.TECH.items() if k not in ('v2', 'feature1')},
                            feature=S.TECH_ON['feature'])
    if on:
        G.plan['set_macro'] = True
    else:
        G.plan.pop('set_macro', None)
    SYMPHONY_SHAPE = on


def symphony_solo(on: bool) -> None:
    """Switch round os1's SOLO for orchestra-symphonic: solo.SOLO (the exposed wind lines on the solo players, the
    string solo event, the concertmaster on the violins I's cantilena - symphony.build_symphony -> solo.solo_pass), the
    set's solo-event draw with memory (plan['set_solo']: composer.set_plan -> solo.solo_slot) - off restores master.
    Apply BEFORE the set plan is drawn."""
    from . import solo as SO
    G = ORCHESTRA_SYMPHONIC
    SO.SOLO = dict(SO.SOLO_ON) if on else None
    if on:
        G.plan['set_solo'] = True
    else:
        G.plan.pop('set_solo', None)


def symphony_pumping(on: bool) -> None:
    """Reduce the automatic phrase arc stacked over symphonic score dynamics; off is render-identical to master.
    This changes performance only, so the same saved compose seed / plan can be used for an A/B."""
    from . import symphony as S
    S.PUMPING = dict(S.PUMPING_ON) if on else None


SYMPHONY_TECH2 = False
"""True (round o24b, TECH['v2'] alone): orchestra-symphonic's technique fixes - set it through symphony_tech2()."""


def symphony_tech2(on: bool) -> None:
    """Switch round o24b's TECH2: TECH['v2'] (symphony.TECH_V2 - 3 techniques a piece, each featured at most twice a
    set, the pizzicato choir at most once per TECH_V2['pizz_gap'] slots, the trill's crown once a set; the pizzicato
    choir / col legno on the theme and the motto; the harmonics on the soft endings; the harp glissando into the
    climax with the build thinned, else into a soft arrival) drawn per set slot (plan['set_tech2']: composer.set_plan
    -> symphony.tech2_slot) - without the macro shape; off restores master. Apply BEFORE the set plan is drawn (and
    after symphony_tech: v2 rides on the technique palette)."""
    global SYMPHONY_TECH2
    from . import symphony as S
    G = ORCHESTRA_SYMPHONIC
    on = bool(on)
    if S.TECH is not None:
        S.TECH = dict(S.TECH, v2=dict(S.TECH_V2), feature=S.TECH_V2['feature'], feature1=S.TECH_ON['feature']) \
            if on else dict({k: v for k, v in S.TECH.items() if k not in ('v2', 'feature1')},
                            feature=S.TECH_ON['feature'])
    if on:
        G.plan['set_tech2'] = True
    else:
        G.plan.pop('set_tech2', None)
    SYMPHONY_TECH2 = on


SYMPHONY_SHAPE2 = False
"""True (round o24b, symphony.MACRO = MACRO2_ON): orchestra-symphonic's macro shapes, fixed - set it through
symphony_shape2()."""


def symphony_shape2(on: bool) -> None:
    """Switch round o24b's SHAPE2: symphony.MACRO = MACRO2_ON (round o24's macro shapes with MACRO2_V2 - the early /
    mid climax's material moved before its aftermath, the loud / cut endings at the climax's level, the climax types'
    own textures, the set's memory on the motto's rhythm family, the first theme's texture and the pumping bass's
    figures) drawn per set slot (plan['set_macro']: composer.set_plan -> symphony.shape_slot); the techniques are
    symphony_tech2's. Off restores master. Apply BEFORE the set plan is drawn."""
    global SYMPHONY_SHAPE2
    from . import symphony as S
    G = ORCHESTRA_SYMPHONIC
    on = bool(on)
    S.MACRO = dict(S.MACRO2_ON) if on else None
    if on:
        G.plan['set_macro'] = True
    else:
        G.plan.pop('set_macro', None)
    SYMPHONY_SHAPE2 = on


SYMPHONY_SHAPE3 = False


def symphony_shape3(on: bool) -> None:
    """Switch round o25's SHAPE3: symphony.MACRO = MACRO3_ON (SHAPE2 with MACRO3_V2 - the aftermath after an early /
    mid climax a release and a second build, then a rising theme return; the chorale climax with the motto's rhythm in
    the strings and a walking bass; the late / cut climax reached by a shorter way, the cut's chords in the motto's
    rhythm) drawn per set slot (plan['set_macro']); the techniques are symphony_tech2's. Off restores master. Apply
    BEFORE the set plan is drawn."""
    global SYMPHONY_SHAPE3
    from . import symphony as S
    G = ORCHESTRA_SYMPHONIC
    on = bool(on)
    S.MACRO = dict(S.MACRO3_ON) if on else None
    if on:
        G.plan['set_macro'] = True
    else:
        G.plan.pop('set_macro', None)
    SYMPHONY_SHAPE3 = on


def piano_diverse(on: bool) -> None:
    """Switch round p-div's PIANO_DIVERSE for new-age-piano: perform.PIANO_DIVERSE (the per-piece anti-template draws -
    the climax's left hand, the peak's place and kind, the ending gesture, the interlude from the theme) and with it
    run.candidates' selection (the score a gate, the set's memory choosing among the near-ties) - off restores the
    old renders bit for bit."""
    from . import perform as P_
    P_.PIANO_DIVERSE = dict(P_.PIANO_DIVERSE_ON) if on else None


def symphony_choir(on: bool, v2: bool = False) -> None:
    """Switch the choir of orchestra-symphonic (round oc1): endless.choir.CHOIR (the vocalset-choir pack's SATB choir
    as events - the summit, the lead-in, an a cappella, a halo, the coda) and the set's plan draw with memory
    (plan['set_choir']: composer.set_plan) - off restores the old renders. v2 (round oc2): CHOIR_V2 on top (the
    theme sung, the gestures' set memory, PLANS_V2)."""
    from . import choir as CH
    G = ORCHESTRA_SYMPHONIC
    CH.CHOIR = (dict(CH.CHOIR_ON, **CH.CHOIR_V2) if v2 else dict(CH.CHOIR_ON)) if on else None
    if on:
        G.plan['set_choir'] = True
    else:
        G.plan.pop('set_choir', None)


def symphony_colour(on: bool) -> None:
    """Switch the guest colours of orchestra-symphonic (round ox1): endless.colour.COLOUR (per piece an organ, a
    classical guitar, a harpsichord, a celesta / glockenspiel or tubular bells the piece is built around) and the
    set's guest draw with memory (plan['set_guest']: composer.set_plan) - off restores the old renders."""
    from . import colour as CO
    G = ORCHESTRA_SYMPHONIC
    CO.COLOUR = dict(CO.COLOUR_ON) if on else None
    if on:
        G.plan['set_guest'] = True
    else:
        G.plan.pop('set_guest', None)


SYMPHONY_POLISH = False
"""True (round op1): orchestra-symphonic's POLISH of the choir / solo / colour features - set it through
symphony_polish()."""


def symphony_polish(on: bool) -> None:
    """Switch round op1's POLISH for orchestra-symphonic (on top of CHOIR v2, SOLO and COLOUR, which must be on):
    solo.SOLO['polish'] (the concertmaster's fader up, no parade of solo blocks, the cello event on the theme),
    colour.COLOUR['polish'] (the guest's returns and coda, the bells' hint, the signature gestures with the set's
    memory, the guitar piece's full orchestra, the cameo guests louder), choir.CHOIR['polish'] (the orchestra leaves
    the sung theme, the summit's texture with the set's memory, the summit capped at 2 per 8 slots, the plans
    PLANS_POLISH, no short halo) and the title's form label with the set's memory (plan['set_polish']:
    composer.set_plan -> composer.title_slot / choir.choir_slot). Off restores master. Apply BEFORE the set plan is
    drawn."""
    global SYMPHONY_POLISH
    from . import choir as CH, colour as CO, solo as SO
    G = ORCHESTRA_SYMPHONIC
    on = bool(on)
    if on and not (CH.CHOIR and CH.CHOIR.get('v2') and SO.SOLO and CO.COLOUR):
        raise ComposeError("symphony_polish: CHOIR v2, SOLO and COLOUR must be on")
    if on:
        CH.CHOIR = dict(CH.CHOIR, polish=dict(CH.CHOIR_POLISH), caps=dict(CH.CHOIR_POLISH['caps']))
        SO.SOLO = dict(SO.SOLO, polish=dict(SO.SOLO_POLISH))
        CO.COLOUR = dict(CO.COLOUR, polish=dict(CO.COLOUR_POLISH))
        G.plan['set_polish'] = True
    else:
        if CH.CHOIR and 'polish' in CH.CHOIR:
            CH.CHOIR = {k: v for k, v in CH.CHOIR.items() if k != 'polish'}
            CH.CHOIR['caps'] = dict(CH.CHOIR_V2['caps'])
        if SO.SOLO and 'polish' in SO.SOLO:
            SO.SOLO = {k: v for k, v in SO.SOLO.items() if k != 'polish'}
        if CO.COLOUR and 'polish' in CO.COLOUR:
            CO.COLOUR = {k: v for k, v in CO.COLOUR.items() if k != 'polish'}
        G.plan.pop('set_polish', None)
    SYMPHONY_POLISH = on


SCORES = {
    'orchestra': _SCORE_ORCHESTRA,
    'symphony': symphony_table(),
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


symphony_setplan(True)
"""Round o22 merged (SET_PLAN v4: per piece +0.05 se 0.21 - not worse -, the set level kept 21 of 28, CI 0.55-0.89):
orchestra-symphonic plans its sets with v4 by default; `shared_plan.py --flag nosetplan` switches it off for a
paired baseline."""


symphony_tech(True)
"""Round o23 merged (TECH: per piece +0.42 se 0.15, 2.8 se, 12 won / 4 lost; the set level kept 28 of 28): the
playing-technique palette is on by default; `shared_plan.py --flag notech` switches it off for a paired baseline."""


symphony_choir(True, v2=True)
"""Round oc2 merged (CHOIR v2: per piece +0.18 se 0.18, the set level kept 28 of 28, CI 0.88-1.00): orchestra-symphonic
sings with the vocalset-choir SATB choir (the theme at the climax, a cappella, halo, coda; the gestures' set memory) by
default; `shared_plan.py --flag nochoir` switches it off for a paired baseline."""


symphony_solo(True)
"""Round os1 merged (SOLO: per piece +0.51 se 0.12, 4.3 se, 13 of 16 won, performance +1.10; the set level agreed 28 of
28 over two passes): the exposed woodwind / horn lines on the principal players, a string solo event, the concertmaster
- on by default; `shared_plan.py --flag nosolo` switches it off for a paired baseline."""


symphony_colour(True)
"""Round ox1 merged (COLOUR: per piece +0.05 se 0.19 - not worse -, the set level agreed 56 of 56 over two passes,
variety 3.96 -> 5.18): each piece built around a guest colour (organ, classical guitar, harpsichord, celesta /
glockenspiel, tubular bells) with the set's memory - on by default; `shared_plan.py --flag nocolour` switches it off."""


symphony_tech2(True)
symphony_shape3(True)
"""Round o25 merged (SHAPE3 + TECH2: per piece -0.06 se 0.18 - not worse -, the set level agreed 18 of 20 over two
passes, variety +0.80): the macro shapes (the opening, the climax's place / count / kind, the ending, a second build
after an early climax) and the technique fixes on by default; `shared_plan.py --flag noshape3` switches both off."""


symphony_pumping(True)
"""User-approved fix (2026-10-25: the 1 h set sounded "pumping, as if someone rides the volume knob"; docs/PUMPING.md):
the automatic phrase arc of orchestra-symphonic reduced to 30 % - exposed solo winds no longer surge ~17 dB within a
second; on by default; `shared_plan.py --flag nopumping` switches it off."""
