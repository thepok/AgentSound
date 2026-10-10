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
ENDINGS = {'major': {'69': 1.0, 'maj9': 0.8, 'maj7#11': 0.6}, 'minor': {'mMaj9': 1.0, 'm69': 1.0}}
"""The end chord's quality (the tag's twist lands on it)."""
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
for _fam, _long in (('medium', {'whole': (8, 3, 3, -2), 'tied': (-2, 6, 4, 2, -2), 'held': (4, 4, 6, -2)}),
                    ('ballad', {'whole': (8, 4, 2, -2), 'sigh': (6, 2, 6, -2), 'tied': (-2, 6, 6, 2)}),
                    ('waltz', {'held': (6, 4, -2), 'tied': (-2, 4, 6), 'long': (9, 2, -1)}),
                    ('song', {'whole': (8, 4, 2, -2), 'held': (-2, 6, 2, 4, -2), 'sigh': (6, 2, 6, -2)}),
                    ('lofi', {'whole': (8, 4, -4), 'held': (-2, 6, 4, -4), 'sigh': (6, 2, 4, -4)})):
    CELLS[_fam]['long'] = _long

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
TAG_KINDS = ('tritone', 'backdoor', 'plagal', 'deceptive', 'cold', 'sus')
SECTION_KEYS = {'name', 'part', 'frame', 'melody', 'dyn', 'figures', 'harmonize', 'chance', 'tempo', 'rit', 'fermata',
                'octave', 'keep_bars', 'lh_only', 'cadenza', 'peak', 'feels', 'drums'}
"""A 'piano' plan's sections (perform.build_piano), in order: name; part (a form part: its changes + melody) or frame
('intro' / 'tag': composer.frame's vamp + line); melody 'lift' (the part's lifted climax line, Tune.out_melody);
dyn: a dynamic mark or (start, end) / (start, peak, end) marks; figures: the feel's figure set; harmonize: 1 = 3rds /
6ths under long notes, 2 = chords (the climax); chance: the section is played in that share of the tunes; tempo: x the
tune's tempo from here; rit: the last bar slows to x; fermata: beats held at the end; octave: the melody moved;
keep_bars: the frame's melody only in these bars (the interlude's echoes); lh_only: bars of left hand alone first;
cadenza: a flourish over the last dominant (romantic.fioritura) in that share of the tunes; peak: the section holds the
piece's climax; feels: the section is played only in these feels (a waltz's second strain pass); drums: False = the
mood's drums rest in this section (lofi-piano: the intro, the bridge, the coda)."""

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
                'endings': ENDINGS, 'tag_approach': TAG_APPROACH}
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
    #                                   'profile': analysis profile, 'loudness': (lo, hi) LUFS gate, 'bass': walking
    #                                   bass options or None, 'drums': brushes options or None, 'trims': {role:
    #                                   dB on its fader}, 'pans': {role: the instrument's own pan}, 'sends': {role:
    #                                   {bus: dB added}}, 'eq': {role: eq params added to its chain}}
    plan: dict                       # {'intro': bars, 'tag': bars, 'end': bars, 'head': {...}, 'solo': {...}, ...}
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
            if f['style'] not in pianist.STYLES:
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
        if set(H) - {'blocks', 'colours', 'intros', 'intro_tonic', 'endings', 'tag_approach'}:
            bad(f"harmony: unknown keys {sorted(set(H) - set(JAZZ_HARMONY))}")
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
        for where, spec in [('plan dyn', self.plan.get('dyn')), ('plan dyn_out_peak', self.plan.get('dyn_out_peak'))] \
                + [(f"feel {n!r} dyn", f.get('dyn')) for n, f in self.feels.items()]:
            for sec, d in (spec or {}).items():
                if not all(lv in _LEVELS for lv in ([d] if isinstance(d, str) else d)) or \
                        (not isinstance(d, str) and len(d) not in (2, 3)):
                    bad(f"{where}[{sec!r}]: a dynamic mark or (start, end) / (start, peak, end) of {', '.join(_LEVELS)}")
        perf = self.plan.get('perform', 'jazz')
        if perf not in ('jazz', 'piano'):
            bad("plan['perform'] must be 'jazz' (head / solo / head out) or 'piano' (plan['sections'])")
        if perf == 'piano':
            secs = self.plan.get('sections') or []
            if not secs:
                bad("a 'piano' plan needs plan['sections']")
            for sd in secs:
                extra = set(sd) - SECTION_KEYS
                if extra or 'name' not in sd or ('part' in sd) == ('frame' in sd):
                    bad(f"plan section {sd!r}: a name, a 'part' (a form part) or a 'frame' (intro / tag), keys "
                        f"{', '.join(sorted(SECTION_KEYS))}")
                for f in forms:
                    if 'part' in sd and sd['part'] not in FORMS[f]['parts']:
                        bad(f"plan section {sd['name']!r}: part {sd['part']!r} is not in form {f!r}")
                for lv in ([sd['dyn']] if isinstance(sd.get('dyn'), str) else sd.get('dyn', ())):
                    if lv not in _LEVELS:
                        bad(f"plan section {sd['name']!r}: dyn {lv!r} is no dynamic mark ({', '.join(_LEVELS)})")
                for f_ in sd.get('feels', ()):
                    if f_ not in self.feels:
                        bad(f"plan section {sd['name']!r}: feels {f_!r} is no feel of the genre")
                for fname, feel in self.feels.items():
                    if sd.get('feels') and fname not in sd['feels']:
                        continue
                    if sd.get('figures') and sd['figures'] not in (feel.get('figures') or {}):
                        bad(f"plan section {sd['name']!r}: figures {sd['figures']!r} missing in a feel's figures")
        for fam in CELLS.values():
            for role, cells in fam.items():
                for cname, cell in cells.items():
                    bar = 6 if fam is CELLS['waltz'] else 8
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
            'ends': {'breath': 0.45, 'down': 0.25, 'antic': 0.15, 'lh': 0.1, 'pickup': 0.05}, 'bridge_long': 0.85,
            'hook_seq': 0.55,
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
                   'double': 0.36},
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
    band={'preset': 'jazz_trio', 'without': (), 'master_gain': 7.0, 'profile': 'jazz', 'loudness': (-18.0, -12.0),
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
            'open': {'I_V3_vi_IV': 'IM V@3 VIm IVM', 'I_iii_IV_V': 'IM IIIm IVM Vsus4:0.5 V:0.5',
                     'I_IV_vi_V': 'IM IVM VIm Vsus4:0.5 V:0.5', 'I_V_vi_iii': 'IM V VIm IIIm',
                     'I_I3_IV_iv': 'IM I@3 IVM IVm6'},
            'turn': {'IV_I3_ii_V': 'IVM I@3 IIm Vsus4:0.5 V:0.5', 'vi_iii_IV_V': 'VIm IIIm IVM Vsus4:0.5 V:0.5',
                     'ii_vi_IV_V': 'IIm VIm IVM V'},
            'final': {'IV_V_I': 'IVM Vsus4:0.5 V:0.5 IM:2', 'ii_V_I': 'IIm V IM:2', 'iv_I': 'IVM IVm6 IM:2',
                      'IV_I5_V_I': 'IVM I@5 V IM'},
            'hook': {'axis': 'VIm IVM IM V VIm IVM IIm Vsus4:0.5 V:0.5',
                     'IV_V_iii_vi': 'IVM V IIIm VIm IVM V@3 IVm6 Vsus4:0.5 V:0.5',
                     'IV_I3': 'IVM I@3 VIm V IVM I@3 IIm Vsus4:0.5 V:0.5',
                     'vi_V3_IV': 'VIm V@3 IVM IIIm IIm IM@3 IVM V'},
            'build': {'relative': 'VIm IVM IIm III7 VIm IVM bVIIM Vsus4:0.5 V:0.5',
                      'vi_iii': 'VIm IIIm IVM IM@3 IIm IVM Vsus4 V',
                      'climb': 'VIm V@3 IVM IIIm IIm I@3 IVM Vsus4:0.5 V:0.5'},
        },
        'minor': {
            'open': {'i_VI_III_VII': 'Im bVIM bIIIM bVII', 'i_iv_VII_III': 'Im IVm bVII bIIIM',
                     'i_VI_iv_V': 'Im bVIM IVm Vsus4:0.5 V:0.5', 'i_VII3_VI_V': 'Im bVII@3 bVIM Vsus4:0.5 V:0.5'},
            'turn': {'VI_VII_iv_V': 'bVIM bVII IVm Vsus4:0.5 V:0.5', 'iv_VI_V': 'IVm bVIM Vsus4 V'},
            'final': {'VI_VII_i': 'bVIM bVII Im:2', 'iv_V_i': 'IVm Vsus4:0.5 V:0.5 Im:2', 'VI_V_i': 'bVIM V Im:2'},
            'hook': {'VI_VII_III': 'bVIM bVII bIIIM Im bVIM bVII IVm Vsus4:0.5 V:0.5',
                     'III_VII': 'bIIIM bVII bVIM bIIIM IVm bVIM Vsus4 V'},
            'build': {'iv_climb': 'IVm bVII bIIIM bVIM IIø V Im V',
                      'relative': 'bIIIM bVII IVm Im bVIM bVII Vsus4 V'},
        },
    },
    # pop colours: plain triads first, add9 / maj7 as the tender colour (the mood's 'colour' scales the add9s)
    'colours': {'M': {'': 2.0, 'add9': 1.0, 'maj7': 0.8}, 'M_tonic': {'': 2.0, 'add9': 1.5, 'maj7': 0.3},
                'm': {'m': 1.0, 'm7': 1.5, 'madd9': 0.4}, 'm_tonic': {'m': 1.5, 'm7': 0.8, 'madd9': 0.6},
                '7_major': {'7': 1.0, '7sus4': 0.4}, '7_minor': {'7': 1.0}, '7_blues': {'7': 1.0},
                '7_sub': {'7': 1.0}, 'ø': {'m7b5': 1.0}, 'o': {'dim7': 1.0}, 'sus': {'7sus4': 1.0, 'sus4': 1.0}},
    'intros': {'major': {'I_IV': ('Iadd9 IVmaj7 VIm7 Vsus4:0.5 V:0.5', 1.0), 'IV_I': ('IVmaj7 Iadd9 IVmaj7 Vsus4', 0.8),
                         'vi_IV': ('VIm7 IVmaj7 Iadd9 Vsus4', 0.7)},
               'minor': {'i_VI': ('Im bVImaj7 bIIIadd9 Vsus4', 1.0), 'i_iv': ('Im7 IVm7 bVImaj7 Vsus4', 0.8)}},
    'intro_tonic': (),
    'endings': {'major': {'add9': 1.0, '': 0.6, 'maj9': 0.3}, 'minor': {'madd9': 1.0, 'm': 0.6}},
    'tag_approach': {'plagal': 1.0, 'sus': 1.0},
}

_NA_FIGURES = {'intro': {'flow': 1.0, 'lilt': 1.0}, 'calm': {'rock': 1.0, 'lilt': 1.0, 'quart': 0.4},
               'flow': {'flow': 1.0, 'rock': 1.0, 'lilt': 0.7, 'color': 0.5}, 'thin': {'quart': 1.0, 'open': 1.0},
               'build': {'flow': 1.0, 'color': 0.6, 'rock': 0.4}, 'big': {'big': 1.0, 'sweep': 0.35},
               'rest': 'half', 'into': 'up', 'end': 'roll'}
"""The broken-chord hand per section (pianist.FIGURES, drawn per bar, never twice running): 'rest' under the
melody's breaths, 'into' the bar before a peak section, 'end' the last chord."""

NEW_AGE_PIANO = Genre(
    name='new-age-piano',
    description='new-age solo piano (letters-to-the-morning): a singable theme and a chorus hook over flowing '
                'broken-chord figures, pop progressions with tender colour chords; intro, theme twice, the hook, an '
                'interlude, the build, one climax (the hook in chords), the theme soft, a coda - rubato, ritardandi',
    forms={'verse': 1},
    moods={'morning': {'feels': {'flowing': 3, 'gentle': 1}, 'modes': {'major': 1},
                       'keys': {'major': ['Ab', 'Db', 'Eb', 'F', 'Bb', 'C']}, 'tempo': 0, 'colour': 1.0,
                       'tritone': 0.0, 'energy': 0.5},
           'longing': {'feels': {'gentle': 2, 'flowing': 2}, 'modes': {'minor': 2, 'major': 1},
                       'keys': {'major': ['Db', 'Ab', 'Gb', 'E'], 'minor': ['F', 'C', 'Bb', 'G', 'D', 'A']},
                       'tempo': -2, 'colour': 1.2, 'tritone': 0.0, 'energy': 0.3},
           'hopeful': {'feels': {'flowing': 2, 'bright': 2}, 'modes': {'major': 1},
                       'keys': {'major': ['C', 'G', 'D', 'F', 'A', 'E']}, 'tempo': 2, 'colour': 0.9,
                       'tritone': 0.0, 'energy': 0.8},
           'rain': {'feels': {'gentle': 3, 'flowing': 1}, 'modes': {'minor': 1},
                    'keys': {'minor': ['E', 'A', 'D', 'B', 'F#', 'C#']}, 'tempo': -3, 'colour': 1.1,
                    'tritone': 0.0, 'energy': 0.15}},
    feels={'flowing': {'tempo': (70, 80), 'meter': 4, 'cells': 'song', 'style': 'ballad', 'lh': 'broken',
                       'swing': False, 'rubato': 0.05, 'touch': (52, 100), 'energy': 0.55, 'figures': _NA_FIGURES,
                       'body': 'lyrical'},
           'gentle': {'tempo': (62, 72), 'meter': 4, 'cells': 'song', 'style': 'ballad', 'lh': 'broken',
                      'swing': False, 'rubato': 0.06, 'touch': (48, 96), 'energy': 0.2, 'body': 'calm',
                      'figures': dict(_NA_FIGURES, flow={'rock': 1.0, 'lilt': 1.0, 'flow': 0.6},
                                      calm={'lilt': 1.0, 'quart': 0.8, 'open': 0.4})},
           'bright': {'tempo': (80, 92), 'meter': 4, 'cells': 'song', 'style': 'ballad', 'lh': 'broken',
                      'swing': False, 'rubato': 0.04, 'touch': (56, 102), 'energy': 0.85, 'body': 'lyrical',
                      'figures': dict(_NA_FIGURES, calm={'rock': 1.0, 'flow': 0.8, 'lilt': 0.5})}},
    # the solo_piano preset as letters-to-the-morning mixed it: the pedalled broken chords' low mids dipped on the
    # left hand, the master's pedalled bass down a little and air above the presence band (no 2-5 kHz lift)
    band={'preset': 'solo_piano', 'master_gain': 6.5, 'profile': 'piano', 'loudness': (-23.0, -15.0), 'bass': None,
          'drums': None, 'eq': {'comp': {'low.freq': 220, 'low.gain': -4.0, 'peak1.freq': 1400, 'peak1.gain': -2.0,
                                         'peak1.q': 0.8, 'peak2.freq': 100, 'peak2.gain': -2.5, 'peak2.q': 1.0}},
          'master_eq': {'peak2.freq': 100, 'peak2.gain': -2.0, 'peak2.q': 1.0, 'peak3.freq': 3200,
                        'peak3.gain': -1.0, 'peak3.q': 0.8, 'high.freq': 9000, 'high.gain': 2.5},
          'breath': {'quiet1': 0.25, 'att_cv4': 0.08}},
    plan={'perform': 'piano', 'intro': 4, 'tag': 4, 'end': 1, 'phrases': _SING_PHRASES,
          'end_styles': {'roll': 1.0, 'spread': 0.6},
          'sections': [
              {'name': 'intro', 'frame': 'intro', 'dyn': ('pp', 'p'), 'figures': 'intro', 'lh_only': 2, 'rit': 0.85},
              {'name': 'A1', 'part': 'A1', 'dyn': 'p', 'figures': 'calm'},
              {'name': 'A2', 'part': 'A2', 'dyn': ('p', 'mp'), 'figures': 'flow', 'harmonize': 1, 'rit': 0.8},
              {'name': 'B1', 'part': 'B', 'dyn': ('mp', 'mf', 'mp'), 'figures': 'flow', 'rit': 0.85},
              {'name': 'inter', 'frame': 'intro', 'dyn': 'pp', 'figures': 'thin', 'keep_bars': (0, 2), 'rit': 0.82},
              {'name': 'A3', 'part': 'A1', 'dyn': 'p', 'figures': 'calm', 'harmonize': 1, 'chance': 0.6},
              {'name': 'build', 'part': 'C', 'dyn': ('mp', 'f'), 'figures': 'build', 'rit': 0.85},
              {'name': 'climax', 'part': 'B', 'melody': 'lift', 'dyn': ('f', 'ff', 'mf'), 'figures': 'big',
               'harmonize': 2, 'peak': True, 'rit': 0.72, 'fermata': 2.5},
              {'name': 'A4', 'part': 'A2', 'dyn': ('p', 'pp'), 'figures': 'thin', 'tempo': 0.93, 'rit': 0.8},
              {'name': 'coda', 'frame': 'tag', 'dyn': 'pp', 'figures': 'thin', 'tempo': 0.95, 'rit': 0.75}]},
    melody={'register': ('G4', 'Bb5'), 'center': 'Eb5', 'peak': 'C6', 'steps': _SING_STEPS, 'ends': _SING_ENDS,
            'bridge_long': 0.0,
            'contours': {'C': {'climb': (((0.0, -2), (0.75, 5), (1.0, 1)), 1.0),
                               'wave': (((0.0, 0), (0.4, -2), (0.8, 5), (1.0, 0)), 0.7)}},
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

GENRES = {g.name: g for g in (JAZZ_PIANO, JAZZ_TRIO, NEW_AGE_PIANO, CLASSICAL_PIANO, LOFI_PIANO)}
STYLES = {'jazz': 'jazz-piano', 'new-age': 'new-age-piano', 'classical': 'classical-piano', 'lofi': 'lofi-piano'}
"""`endless piano --style S`: the genre of each piano style ('mix': the set plan alternates them)."""


def get(name: str) -> Genre:
    if name not in GENRES:
        raise ComposeError(f"unknown endless genre {name!r}; genres: {', '.join(GENRES)}")
    return GENRES[name]
