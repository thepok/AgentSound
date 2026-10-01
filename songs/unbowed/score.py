"""Unbowed - the score as data: an original first movement in C minor in the idiom of Beethoven's middle-period
symphonies (1804-1812). No note, theme, motif or progression is Beethoven's.

The whole movement grows from one CELL: a syncopated sigh - an 8th that leaps up a sixth onto a long note struck on
the off-beat (the sforzando falls between the beats), then a step down and a landing:  G4:.5 Eb5:1 D5:.5 C5:1.
It is the first theme (a sentence: idea, its answer on the dominant, a sequence, fragmentation into half-bar cells,
a German-sixth cadence), the bass of the second theme, the closing theme in major, the sequences and the fugato
subject of the development, the imitations over the dominant pedal and, turned to C major, the triumph of the coda.

Pitches are sounding pitch (MIDI or names), times are beats (quarter notes) from the start of each section. Harmony
tables are (dur, chord, top, bass[, {voice: pitch}]) rows for agentsound.voicing (top / bass the structural outer
voices, None = free); melodies are voicing.line() strings.
"""
from __future__ import annotations

from agentsound.voicing import N, line  # noqa: F401

CELL = 'G4:.5 Eb5:1 D5:.5 C5:1'

# ================================================================================================ INTRODUCTION
# Adagio molto, q = 56, 10 bars. A unison C ff (fermata) - and the winds answer pp on Ab (the flat sixth: the
# surprise that will haunt the movement). The cell in slow motion on the violins, a second unison on Ab ff answered
# by the Neapolitan (Db) pp, a German sixth, the dominant pedal growing into the Allegro.

INTRO_UNISON = [(0, 2, 'C')]            # (beat, beats, pitch class name): every section in octaves, ff
INTRO_UNISON2 = [(24, 2, 'Ab')]
INTRO = [
    (2, None, None, None), (2, 'Ab', 'C5', 'Ab2'),
    (2, 'Db/F', 'Db5', 'F2'), (2, 'G7/F', 'B4', 'F2'),
    (4, 'Cm/Eb', 'C5', 'Eb2'),
    (2, 'Fm', 'C5', 'F2'), (2, 'G7', 'B4', 'G2'),
    (3, 'Fm/Ab', 'C5', 'Ab2'), (1, 'Cm/G', 'C5', 'G2'),
    (2, 'Bdim7/D', 'Ab4', 'D3'), (2, 'G', 'B4', 'G2'),
    (2, None, None, None), (2, 'Db', 'F5', 'Db3'),
    (2, 'Fm/Ab', 'F5', 'Ab2'), (2, 'Ab7', 'F#5', 'Ab2'),
    (2, 'G', 'D5', 'G2'), (2, 'Cm/G', 'Eb5', 'G2'),
    (4, 'G7', 'F5', 'G2'),
]
# the cell in slow motion (violins I, pp, legato), then its sequence up a step
INTRO_VIOLIN = ('r:8 | G4:1 Eb5:2 D5:1 | C5:2 B4:2 | Ab4:1 F5:2 Eb5:1 | D5:2 B4:1 r:1 | r:8 | '
                'D5:1 G5:1 Bb5:1 G5:1 | F5:1 Ab5:1 B5:1 D6:1')
INTRO_BASSOON = 'r:16 | r:12 C4:1 Eb4:1 | D4:2 r:2'          # a sigh in the bassoon under the lament
INTRO_FLUTE = 'r:32 | r:4 G5:1 B5:1 | D6:2 F6:2'              # the flute climbs with the violins into the fermata

# ================================================================================================ EXPOSITION
# Allegro con brio, q = 148.
# t1 (8 bars, p, strings): the first theme as a sentence, a half cadence on G, a general pause of two beats.
T1_MEL = ('G4:.5 Eb5:1 D5:.5 C5:1 r:1 | G4:.5 D5:1 C5:.5 B4:1 r:1 | Ab4:.5 F5:1 Eb5:.5 D5:1 r:1 | '
          'G4:.5 Eb5:1 D5:.5 B4:1 C5:1 | C5:.5 Ab5:1 G5:.5 Bb4:.5 G5:1 F5:.5 | Ab4:.5 F5:1 Eb5:.5 G4:.5 Eb5:1 D5:.5 | '
          'Eb5:1 C5:.5 Ab5:.5 F#5:1 G5:1 | G5:2 r:2')
T1 = [
    (4, 'Cm', 'C5', 'C3'),
    (4, 'G7/B', 'D5', 'B2'),
    (2, 'Fm/Ab', 'F5', 'Ab2'), (2, 'Bdim7/Ab', 'D5', 'Ab2'),
    (2, 'Cm/G', 'Eb5', 'G2'), (1, 'G7', 'B4', 'G2'), (1, 'Cm', 'C5', 'C3'),
    (2, 'Ab', 'Ab5', 'Ab2'), (2, 'Eb/G', 'G5', 'G2'),
    (2, 'Fm', 'F5', 'F2'), (2, 'Cm/Eb', 'Eb5', 'Eb2'),
    (2, 'Ab', 'Eb5', 'Ab2'), (1, 'Ab7', 'F#5', 'Ab2'), (1, 'G', 'G5', 'G2'),
    (2, 'G', 'G5', 'G2'), (2, None, None, None),
]

# t1ff (8 bars, ff tutti): the counterstatement - the cell in octaves, the rests filled by hammered chords; the
# answer bends to the Neapolitan (Db) and the sentence ends with two hammer blows on C minor.
T1FF_MEL = ('G4:.5 Eb5:1 D5:.5 C5:1 r:1 | G4:.5 D5:1 C5:.5 B4:1 r:1 | Ab4:.5 F5:1 Eb5:.5 Db5:1 r:1 | '
            'Ab4:.5 F5:1 Eb5:.5 D5:1 B4:1 | C5:.5 Ab5:1 G5:.5 Bb4:.5 G5:1 F5:.5 | Ab4:.5 F5:1 Eb5:.5 G4:.5 Eb5:1 D5:.5 | '
            'Eb5:1 C5:.5 Ab5:.5 F#5:1 G5:1 | C5:1 r:.5 C5:.5 C5:1 r:1')
T1FF = [
    (4, 'Cm', 'C5', 'C3'),
    (4, 'G7/B', 'D5', 'B2'),
    (4, 'Db/F', 'F5', 'F2'),
    (2, 'Fm/Ab', 'F5', 'Ab2'), (2, 'G7', 'D5', 'G2'),
    (2, 'Ab', 'Ab5', 'Ab2'), (2, 'Eb/G', 'G5', 'G2'),
    (2, 'Fm', 'F5', 'F2'), (2, 'Cm/Eb', 'Eb5', 'Eb2'),
    (2, 'Ab', 'Eb5', 'Ab2'), (1, 'Ab7', 'F#5', 'Ab2'), (1, 'G', 'G5', 'G2'),
    (1, 'Cm', 'C5', 'C3'), (0.5, None, None, None), (0.5, 'Cm', 'C5', 'C3'), (1, 'Cm', 'C5', 'C3'),
    (1, None, None, None),
]
T1FF_STABS = [3, 7, 11]           # beats where the melody rests: a hammered tutti chord

# trans (16 bars): sforzandi on the weak beats (syncopated string chords over a chromatic falling bass), the cell in
# the basses, a hemiola (3 + 3 + 2 beats) that wrenches the bar, then the Bb pedal (V of Eb): the horn call and its
# echo in the clarinets, diminuendo.
TRANS = [
    (4, 'Cm', 'G5', 'C3'), (4, 'G7/B', 'F5', 'B2'), (4, 'C7/Bb', 'E5', 'Bb2'), (4, 'F/A', 'F5', 'A2'),
    (4, 'Fm/Ab', 'F5', 'Ab2'), (4, 'Eb/G', 'G5', 'G2'), (4, 'Ab', 'Ab5', 'Ab2'), (4, 'F7/A', 'A5', 'A2'),
    (3, 'Bb/D', 'Bb5', 'D3'), (3, 'Eb', 'G5', 'Eb3'), (2, 'F7', 'A5', 'F2'),
    (3, 'Gm', 'Bb5', 'G2'), (3, 'Cm7', 'G5', 'C3'), (2, 'F7', 'A5', 'F2'),
    (4, 'Eb/Bb', 'G4', 'Bb2'), (4, 'Bb7', 'Ab4', 'Bb2'), (4, 'Eb/Bb', 'G4', 'Bb2'), (4, 'Bb7', 'F4', 'Bb2'),
]
TRANS_BASS_CELL = 'r:16 | Ab2:.5 F3:1 Eb3:.5 Db3:1 r:1 | G2:.5 Eb3:1 D3:.5 C3:1 r:1 | Ab2:.5 Eb3:1 D3:.5 C3:1 r:1 | ' \
                  'A2:.5 F3:1 Eb3:.5 C3:1 r:1'
HORN_CALL_EB = 'Bb3:.5 Eb4:.5 G4:1 Bb4:2 | Ab4:1.5 F4:.5 D4:2'             # trans bars 13-14 (solo horn)
CLAR_ECHO_EB = 'Bb4:.5 Eb5:.5 G5:1 Bb5:2 | Ab5:1.5 F5:.5 D5:1 r:1'         # trans bars 15-16 (clarinets)

# t2 (16 bars, Eb major, p dolce): the lyrical second theme - the solo clarinet, then violins I with the flute an
# octave higher; the cell (its rhythm) murmurs in the cellos underneath; the restatement turns deceptively to Cb
# (bVI) and finds its way back.
T2_MEL1 = ('Bb4:2 C5:1 Eb5:1 | D5:1.5 C5:.5 Bb4:2 | Ab4:1 C5:1 F5:1.5 Eb5:.5 | D5:3 r:1 | '
           'Bb4:2 C5:1 Eb5:1 | G5:1.5 F5:.5 Eb5:1 Db5:1 | C5:1 Ab5:1 G5:1 F5:1 | Eb5:3 r:1')
T2_MEL2 = ('Bb4:2 C5:1 Eb5:1 | D5:1.5 C5:.5 Bb4:2 | Ab4:1 C5:1 F5:1.5 Eb5:.5 | D5:2 F5:1 Ab5:1 | '
           'Gb5:2 Eb5:1 Cb5:1 | Ab5:2 F5:1 D5:1 | G5:1.5 Bb5:.5 F5:1 Ab5:1 | G5:2 Eb5:2')
T2 = [
    (4, 'Eb', 'Bb4', 'Eb3'), (2, 'Bb/D', 'D5', 'D3'), (2, 'Eb', 'Bb4', 'Eb3'),
    (2, 'Ab', 'C5', 'Ab2'), (2, 'Bb7', 'F5', 'Bb2'), (4, 'Bb', 'D5', 'Bb2'),
    (4, 'Eb', 'Bb4', 'Eb3'), (4, 'Eb7/Db', 'G5', 'Db3'),
    (2, 'Ab/C', 'C5', 'C3'), (1, 'Eb/Bb', 'G5', 'Bb2'), (1, 'Bb7', 'F5', 'Bb2'), (4, 'Eb', 'Eb5', 'Eb3'),
    (4, 'Eb', 'Bb4', 'Eb3'), (2, 'Bb/D', 'D5', 'D3'), (2, 'Eb', 'Bb4', 'Eb3'),
    (2, 'Ab', 'C5', 'Ab2'), (2, 'Bb7', 'F5', 'Bb2'), (4, 'Bb7', 'D5', 'Bb2'),
    (4, 'Cb', 'Gb5', 'Cb3'), (2, 'Abm/Cb', 'Ab5', 'Cb3'), (2, 'Bb7', 'F5', 'Bb2'),
    (2, 'Eb/Bb', 'G5', 'Bb2'), (2, 'Bb7', 'F5', 'Bb2'), (4, 'Eb', 'G5', 'Eb3'),
]
# the cell's rhythm (8th - quarter - 8th - quarter - rest) in the cellos under the restatement, on the bass
T2_CELLO_CELL = ('r:32 | Eb3:.5 Bb3:1 G3:.5 Eb3:1 r:1 | D3:.5 Bb3:1 F3:.5 Eb3:1 r:1 | Ab2:.5 Eb3:1 C3:.5 Bb2:1 r:1 | '
                 'Bb2:.5 F3:1 D3:.5 Bb2:1 r:1')

# closing (12 bars, Eb major): the cell in major, ff (violins in octaves over hammered chords), a hemiola cadence,
# and a hushed codetta - the cell in the basses alone - cut off by two blows.
CLOSING_MEL = ('Bb4:.5 G5:1 F5:.5 Eb5:1 Bb4:1 | C5:.5 Ab5:1 G5:.5 F5:.5 Eb5:.5 C5:1 | D5:.5 Bb5:1 Ab5:.5 F5:1 D5:1 | '
               'Eb5:.5 G5:.5 Bb5:.5 Eb6:.5 Eb6:1 r:1')
CLOSING = [
    (4, 'Eb', 'G5', 'Eb3'), (4, 'Ab/C', 'Ab5', 'C3'), (4, 'Bb7/D', 'Ab5', 'D3'), (4, 'Eb', 'G5', 'Eb3'),
    (3, 'Ab', 'C6', 'Ab2'), (3, 'Bb7/Ab', 'D6', 'Ab2'), (2, 'Eb/G', 'Eb6', 'G2'),
    (2, 'Ab', 'C6', 'Ab2'), (2, 'Bb7', 'D6', 'Bb2'), (4, 'Eb', 'Eb6', 'Eb3'),
    (4, 'Eb', 'G4', 'Eb3'), (4, 'Ab/Eb', 'Ab4', 'Eb3'), (4, 'Eb', 'G4', 'Eb3'),
    (2, 'Eb', 'Eb5', 'Eb3'), (2, None, None, None),
]
CLOSING_BASS_CELL = 'r:32 | Bb2:.5 G3:1 F3:.5 Eb3:1 r:1 | C3:.5 Ab3:1 G3:.5 Eb3:1 r:1 | Bb2:.5 G3:1 F3:.5 Eb3:1 r:1'
CLOSING_WIND_ANSWER = 'r:34 | Eb5:1 r:3 | r:2 Eb5:1 r:1 | r:2 G5:1 r:1'      # oboes / flutes echo the codetta

# ================================================================================================ DEVELOPMENT
# dev1 (12 bars): the cell fragmented and tossed between winds and strings through falling thirds: C minor, Ab,
# F minor, Db, Bb minor - each key a bar of the cell and a bar of its answer on the dominant - into C7 (V of F minor).
DEV1 = [
    (4, 'Cm', 'C5', 'C3'), (4, 'G7/B', 'B4', 'B2'),
    (4, 'Ab', 'Ab4', 'Ab2'), (4, 'Eb7/G', 'G4', 'G2'),
    (4, 'Fm', 'F5', 'F2'), (4, 'C7/E', 'E5', 'E2'),
    (4, 'Db', 'Db5', 'Db3'), (4, 'Ab7/C', 'C5', 'C3'),
    (4, 'Bbm', 'Bb4', 'Bb2'), (4, 'F7/A', 'A4', 'A2'),
    (4, 'Bbm/Db', 'Bb4', 'Db3'), (4, 'C7', 'Bb4', 'C3'),
]
# the cell on each key's tonic (winds) and the answer on its dominant (violins), one bar each
DEV1_CELLS = [('G4', 'Eb5', 'D5', 'C5'), ('D5', 'B5', 'A5', 'G5'), ('Eb4', 'C5', 'Bb4', 'Ab4'),
              ('Bb4', 'G5', 'F5', 'Eb5'), ('C5', 'Ab5', 'G5', 'F5'), ('G4', 'E5', 'D5', 'C5'),
              ('Ab4', 'F5', 'Eb5', 'Db5'), ('Eb4', 'C5', 'Bb4', 'Ab4'), ('F4', 'Db5', 'C5', 'Bb4'),
              ('C5', 'A5', 'G5', 'F5'), ('F4', 'Db5', 'C5', 'Bb4'), ('G4', 'E5', 'D5', 'C5')]

# dev2 (16 bars): fugato in F minor on a subject spun from the cell; entries cellos (+ basses) - violas (answer in C
# minor) - violins II (subject) - violins I (answer), each voice going on in free counterpoint (agentsound.voicing).
SUBJECT = 'C3:.5 Ab3:1 G3:.5 F3:1 E3:1 | F3:.5 Db4:1 C4:.5 Bb3:1 Ab3:1 | G3:.5 E3:.5 F3:.5 G3:.5 Ab3:.5 Bb3:.5 C4:.5 Db4:.5 | C4:1 Bb3:.5 Ab3:.5 G3:1 F3:1'
SUBJECT_H = [(0, 3, 'Fm'), (3, 1, 'C7/E'), (4, 2, 'Db'), (6, 2, 'Bbm7'), (8, 1, 'C7'), (9, 3, 'Fm'),
             (12, 1, 'Fm/C'), (13, 2, 'C7'), (15, 1, 'Fm')]
ANSWER_SHIFT = 7                  # the answer: the subject a fifth up, in C minor
FUGATO_ENTRIES = [('cellos', 0, 0), ('violas', 16, ANSWER_SHIFT), ('violins2', 32, 12), ('violins1', 48, 12 + ANSWER_SHIFT)]

# dev3 (8 bars): the storm breaks - hammered syncopated tutti chords (sforzandi between the beats) driving into Gb
# major, a tritone from home; subito pp the second theme's head in Gb on the clarinet, the flute answers in Gb minor,
# and a German sixth on Ab opens the way to G.
DEV3 = [
    (4, 'Db', 'Ab5', 'Db3'), (4, 'Bbm/Db', 'Bb5', 'Db3'), (4, 'Ebm/Gb', 'Bb5', 'Gb2'), (4, 'Db7/Ab', 'Cb6', 'Ab2'),
    (4, 'Gb', 'Db5', 'Gb2'), (2, 'Db/F', 'F5', 'F2'), (2, 'Gb', 'Db5', 'Gb2'),
    (4, 'Ebm/Gb', 'Eb5', 'Gb2'), (4, 'Ab7', 'F#5', 'Ab2'),
]
DEV3_CLAR = 'r:16 | Db5:2 Eb5:1 Gb5:1 | F5:1.5 Eb5:.5 Db5:2'
DEV3_FLUTE = 'r:24 | Db6:2 Eb6:1 Gb6:1 | F#6:1.5 Eb6:.5 C6:2'

# dev4 (16 bars): the dominant pedal on G - basses and timpani - pp; the cell climbs in imitation from the cellos to
# the flutes, the harmony tightens over the pedal (Ab/G, Fm/G, Bdim7/G), a long crescendo into the recapitulation.
DEV4 = [
    (4, 'Cm/G', 'Eb5', 'G2'), (4, 'G7', 'D5', 'G2'), (4, 'Cm/G', 'Eb5', 'G2'), (4, 'G7', 'F5', 'G2'),
    (4, 'Ab/G', 'Eb5', 'G2'), (4, 'G7', 'F5', 'G2'), (4, 'Fm/G', 'Ab5', 'G2'), (4, 'G7', 'B5', 'G2'),
    (4, 'Cm/G', 'C6', 'G2'), (4, 'Bdim7/G', 'D6', 'G2'), (4, 'Cm/G', 'Eb6', 'G2'), (4, 'Bdim7/G', 'F6', 'G2'),
    (4, 'G7', 'D6', 'G2'), (4, 'G7', 'F6', 'G2'), (4, 'G7', 'B5', 'G2'), (2, 'G7', 'B5', 'G2'), (2, None, None, None),
]
# who carries the cell in each bar of the pedal (it rises): role, octave shift from the cell on G (D-B-A-G)
DEV4_IMITATION = [('cellos', -12), ('violas', -12), ('violins2', 0), ('violins1', 0), ('clarinets', 0), ('oboes', 0),
                  ('violins1', 12), ('flutes', 12), ('violins2', 0), ('violins1', 12), ('oboes', 12), ('flutes', 12),
                  ('violins1', 12), ('flutes', 12), ('violins1', 12), ('flutes', 12)]

# ================================================================================================ RECAPITULATION
# rec1 (8 bars): the first theme ff in the full orchestra (it was p in the strings), the half cadence held -> the
# oboe's cadenza (Adagio, 2 bars, over a held G7 pp) -> rec2.
REC1_MEL = T1_MEL
REC1 = T1
OBOE_CADENZA = 'G5:1.5 F5:.25 Eb5:.25 D5:.5 C5:.5 B4:.5 Ab4:.5 | G4:1 Ab4:.5 B4:.5 D5:.5 F5:.5 Eb5:.5 D5:.5'
CADENZA = [(4, 'G7', 'D5', 'G2'), (2, 'Fm/Ab', 'C5', 'Ab2'), (2, 'G', 'B4', 'G2')]

# rec2 (12 bars): the transition rewritten to reach G (V of C major): syncopes, the hemiola, the horn call on G.
REC2 = [
    (4, 'Cm', 'G5', 'C3'), (4, 'G7/B', 'F5', 'B2'), (4, 'C7/Bb', 'E5', 'Bb2'), (4, 'F/A', 'F5', 'A2'),
    (3, 'Fm/Ab', 'F5', 'Ab2'), (3, 'C/G', 'E5', 'G2'), (2, 'D7/F#', 'D5', 'F#2'),
    (3, 'G', 'D5', 'G2'), (3, 'Am', 'E5', 'A2'), (2, 'D7', 'F#5', 'D3'),
    (4, 'C/G', 'E4', 'G2'), (4, 'G7', 'F4', 'G2'), (4, 'C/G', 'E4', 'G2'), (4, 'G7', 'D4', 'G2'),
]
HORN_CALL_C = 'G3:.5 C4:.5 E4:1 G4:2 | F4:1.5 D4:.5 B3:2'
CLAR_ECHO_C = 'G4:.5 C5:.5 E5:1 G5:2 | F5:1.5 D5:.5 B4:1 r:1'


def transpose_table(table, semis):
    """A harmony table moved by semitones (chord symbols and pitches)."""
    from agentsound.theory import chord as _chord
    out = []
    for row in table:
        dur, sym, top, bass, *more = row
        if sym is None:
            out.append(row)
            continue
        c = _chord(sym).transpose(semis)
        out.append((dur, c.symbol, None if top is None else N(top) + semis, None if bass is None else N(bass) + semis,
                    *more))
    return out


# rec3 (16 bars): the second theme in C major (violins, then flute + oboe in octaves); the deceptive turn lands on Ab.
REC3 = transpose_table(T2, -3)
REC3_MEL1 = T2_MEL1
REC3_MEL2 = T2_MEL2
REC3_CELLO_CELL = T2_CELLO_CELL

# rec4 (12 bars): the closing in C major - but where the codetta should close, G7 turns to Ab (bVI) ff: the coda.
REC4 = transpose_table(CLOSING[:10], -3) + [
    (4, 'C', 'E4', 'C3'), (4, 'F/C', 'F4', 'C3'), (4, 'G7', 'F5', 'G2'), (4, 'Ab', 'Eb5', 'Ab2'),
]
REC4_MEL = CLOSING_MEL
REC4_BASS_CELL = 'r:32 | G2:.5 E3:1 D3:.5 C3:1 r:1 | A2:.5 F3:1 E3:.5 C3:1 r:1'

# ================================================================================================ CODA
# coda1 (16 bars): a second development - from Ab through the Neapolitan (Db) back into C minor (subito p, the
# struggle returns), then the bass climbs chromatically C - D - Eb - E - F - F# - G under a crescendo to the
# cadential six-four and G7.
CODA1 = [
    (4, 'Ab', 'Eb5', 'Ab2'), (4, 'Fm/Ab', 'F5', 'Ab2'), (4, 'Db', 'F5', 'Db3'), (4, 'Bbm/Db', 'F5', 'Db3'),
    (4, 'G7/D', 'F5', 'D3'), (4, 'Cm/Eb', 'Eb5', 'Eb3'), (4, 'Fm/Ab', 'F5', 'Ab2'), (4, 'G7', 'D5', 'G2'),
    (4, 'Cm', 'Eb5', 'C3'), (4, 'G/D', 'D5', 'D3'), (4, 'Cm/Eb', 'Eb5', 'Eb3'), (4, 'C7/E', 'Bb5', 'E3'),
    (4, 'Fm', 'Ab5', 'F3'), (4, 'F#dim7', 'C6', 'F#2'), (4, 'Cm/G', 'C6', 'G2'), (4, 'G7', 'B5', 'G2'),
]
CODA1_CELLS = [('Eb4', 'C5', 'Bb4', 'Ab4'), ('C5', 'Ab5', 'G5', 'F5'), ('Ab4', 'F5', 'Eb5', 'Db5'),
               ('F4', 'Db5', 'C5', 'Bb4'), ('D5', 'B5', 'A5', 'G5'), ('G4', 'Eb5', 'D5', 'C5'),
               ('C5', 'Ab5', 'G5', 'F5'), ('D5', 'B5', 'A5', 'G5')]

# coda2 (12 bars): the triumph - the cell in C MAJOR, ff tutti with trumpets and horns, then the horn call in C
# hammered out by all the horns and trumpets over a tonic pedal.
CODA2_MEL = ('G4:.5 E5:1 D5:.5 C5:1 r:1 | G4:.5 D5:1 C5:.5 B4:1 r:1 | A4:.5 F5:1 E5:.5 D5:1 r:1 | '
             'G4:.5 E5:1 D5:.5 B4:1 C5:1 | E5:.5 C6:1 B5:.5 A5:.5 F5:1 E5:.5 | D5:.5 B5:1 A5:.5 G5:1 r:1 | '
             'C5:.5 E5:.5 G5:.5 C6:.5 E6:1 D6:1 | C6:2 r:2')
CODA2 = [
    (4, 'C', 'C5', 'C3'), (4, 'G7/B', 'D5', 'B2'), (2, 'F/A', 'F5', 'A2'), (2, 'G7/B', 'D5', 'B2'),
    (2, 'C/G', 'E5', 'G2'), (1, 'G7', 'B4', 'G2'), (1, 'C', 'C5', 'C3'),
    (2, 'Am', 'C6', 'A2'), (2, 'F', 'A5', 'F2'), (2, 'G', 'B5', 'G2'), (2, 'G7', 'G5', 'G2'),
    (2, 'C/E', 'C6', 'E2'), (1, 'F', 'C6', 'F2'), (1, 'G7', 'D6', 'G2'), (4, 'C', 'C6', 'C3'),
    (8, 'C', 'G5', 'C3'), (4, 'G7', 'F5', 'G2'), (4, 'C', 'E5', 'C3'),
]
CODA2_HORNS = 'r:32 | G3:.5 C4:.5 E4:1 G4:2 | C5:2 G4:1 r:1 | B3:.5 D4:.5 F4:1 G4:2 | E4:2 C4:1 r:1'

# coda3 (8 bars): the hammered tonic chords, the last held in unison under a fermata.
CODA3 = [
    (1, 'C', 'E5', 'C3'), (1, None, None, None), (1, 'C', 'G5', 'C3'), (1, None, None, None),
    (1, 'G7', 'F5', 'G2'), (1, None, None, None), (1, 'C', 'E5', 'C3'), (1, None, None, None),
    (1, 'C', 'C6', 'C3'), (1, None, None, None), (1, 'G7', 'B5', 'G2'), (1, None, None, None),
    (2, 'C', 'C6', 'C3'), (2, 'G7', 'D6', 'G2'),
    (1, 'C', 'E6', 'C3'), (3, None, None, None),
    (1, 'C', 'C6', 'C3'), (3, None, None, None),
    (4, 'C5', 'C6', 'C3'), (2, 'C5', 'C6', 'C3'), (2, None, None, None),
]


def cell(p1, p2, p3, p4, t0=0.0, shift=0):
    """The cell on four pitches: 8th, (syncopated) quarter, 8th, quarter: [(start, dur, pitch)]."""
    t0 = float(t0)
    return [(t0 + a, d, N(p) + shift) for a, d, p in ((0, .5, p1), (.5, 1, p2), (1.5, .5, p3), (2, 1, p4))]


def at(h, t0):
    return [(s + t0, d, c) for s, d, c in h]
