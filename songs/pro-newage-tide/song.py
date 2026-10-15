"""The Tide Turns Twice - an original new-age piece for solo grand piano in D Dorian, 6/8.
Build: python -m agentsound build songs/pro-newage-tide

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

6/8, dotted quarter = 56 (quarter 84), 82 bars. An ARCH (A B C B' A'): the climax in the CENTRE (~54 %), the second
half mirrors the first in other keys, and the piece ends with the material it began with. D Dorian: the raised 6th
(B natural - G major as IV) is the colour, not a minor key.

  intro   1-4    a rippling right-hand ostinato in the middle register (D5 A4 E5 A4 F5 A4), no bass; the bass
                 enters in bar 3
  A1      5-20   the theme: a wave (A4 D5 F5 rising, a fall through the Dorian B5 over G/D), 4 x 4 bars, cadencing
                 on Am7 (the minor v), the second half through Bb and C
  B1      21-36  F major with the Lydian B natural (G/F): longer notes, the leap to B5, a 10ths hand
  build   37-44  the theme's head climbing the Dorian chords i - ii - bIII - IV - v - bVI - bVII, to A7
  climax  45-50  a HEMIOLA: three quarter-note chords per 6/8 bar (the meter turns over), up to A6 once, then the
                 6/8 swing again, falling to A7sus4 - A7
  inter   51-52  a breath: the ostinato's fragment
  B2      53-64  the B tune in B-flat Lydian (C/Bb, E natural), then back to D through G/D
  A2      65-76  the theme varied (a pickup start, Bb for F), closing on G/D (the Dorian plagal colour, not the tonic)
  coda    77-82  the opening ostinato returns and thins out; the last chord is Dm6 (D A B F) - the Dorian 6th on top

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'The Tide Turns Twice', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#d4e6e4', '#1f5560'], 'title': 'THE TIDE TURNS TWICE',
         'subtitle': 'solo piano - AgentSound', 'seed': 41}

G = _genre('new-age-piano')
FEEL = 'flowing'           # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'D dorian'
TIME = (6, 8)
METER = 3                  # quarter beats per bar
TEMPO = 84
SEED = 41

# ------------------------------------------------------------------------------------------------ right hand
RH = {
    # intro - the ostinato alone, the bass from bar 3
    1: 'D5/8 A4/8 E5/8 A4/8 F5/8 A4/8',
    2: 'G5/8 A4/8 F5/8 A4/8 E5/8 C5/8',
    3: 'D5/8 A4/8 E5/8 A4/8 F5/8 A4/8',
    4: 'B4/8 D5/8 E5/8 G5/8 A5/4',
    # A1 - the wave
    5: 'A4/8 D5/8 F5/8 A5/4.',
    6: 'B5/8 A5/8 G5/8 D5/4.',
    7: 'F5/4. E5/8 D5/8 A4/8',
    8: 'E5/4 D5/8 C5/4.',
    9: 'A4/8 D5/8 F5/8 C6/4.',
    10: 'B5/4 A5/8 G5/4 E5/8',
    11: 'A5/4. G5/8 F5/8 C5/8',
    12: 'E5/4. r/4.',
    13: 'D5/8 F5/8 Bb5/8 A5/4 F5/8',
    14: 'G5/4. E5/8 C5/8 G4/8',
    15: 'A4/8 D5/8 E5/8 F5/4 A5/8',
    16: 'G5/4 E5/8 C5/4.',
    17: 'F5/4.^turn D5/8 A5/8 Bb5/8',
    18: 'C6/4. G5/4 E5/8',
    19: 'D6/4 B5/8 A5/4 G5/8',
    20: 'A5/4. r/4.',
    # B1 - F with the Lydian B: long notes
    21: 'A4/4 C5/8 G5/4.',
    22: 'B5/2.',
    23: 'A5/4. G5/8 E5/8 D5/8',
    24: 'E5/2.',
    25: 'F5/4 A5/8 C6/4.',
    26: 'B5/4. D6/4.',
    27: 'E6/4. D6/8 B5/8 G5/8',
    28: 'A5/2 r/4',
    29: 'A4/4 C5/8 E5/4.',
    30: 'D5/8 G5/8 B5/8 D6/4.',
    31: 'E6/4 D6/8 B5/4 G5/8',
    32: 'A5/4. E5/4.',
    33: 'F5/4 A5/8 D6/4 C6/8',
    34: 'B5/4. A5/8 G5/8 D5/8',
    35: 'F5/4. D5/8 F5/8 A5/8',
    36: 'G5/4. r/4.',
    # build - the head climbing the Dorian chords
    37: 'A4/8 D5/8 F5/8 A5/4 F5/8',
    38: 'B4/8 E5/8 G5/8 B5/4 G5/8',
    39: 'C5/8 F5/8 A5/8 C6/4 A5/8',
    40: 'D5/8 G5/8 B5/8 D6/4 B5/8',
    41: 'E5/8 A5/8 C6/8 E6/8 D6/8 C6/8',
    42: 'D6/4. F6/4 D6/8',
    43: 'E6/4. G6/8 E6/8 C6/8',
    44: 'D6/4. C#6/4.',
    # climax - the hemiola: three quarter-note chords per bar
    45: '[F5 A5 D6]/4 [A5 D6 F6]/4 [D6 F6 A6]/4',
    46: '[B5 D6 G6]/4 [G5 B5 E6]/4 [B5 D6]/4',
    47: '[G5 C6 E6]/4 [E5 G5 C6]/4 [G5 B5 D6]/4',
    48: '[E5 A5 C6]/4. [C5 E5 A5]/4.',
    49: '[F5 A5 D6]/4. [D5 F5 Bb5]/8 [F5 A5]/8 [D5 F5]/8',
    50: '[D5 E5 A5]/4. [C#5 E5 G5]/4.',
    # inter - a breath
    51: 'r/4. A4/8 D5/8 E5/8',
    52: 'F5/4. E5/8 C5/8 G4/8',
    # B2 - the B tune in B-flat Lydian
    53: 'D5/4 F5/8 A5/4.',
    54: 'E6/2.',
    55: 'D6/4. C6/8 A5/8 G5/8',
    56: 'A5/2.',
    57: 'Bb5/4 D6/8 F6/4.',
    58: 'E6/4. D6/4 C6/8',
    59: 'C6/4. A5/8 F5/8 E5/8',
    60: 'D5/4. C#5/4.',
    61: 'F5/4 A5/8 D6/4.',
    62: 'B5/4. A5/8 G5/8 D5/8',
    63: 'A5/4. F5/8 D5/8 F5/8',
    64: 'E5/4. r/4.',
    # A2 - the theme varied, closing on G/D
    65: 'r/8 D5/8 F5/8 A5/4.',
    66: 'B5/4 G5/8 D5/4.',
    67: 'A5/4.^mord F5/8 E5/8 D5/8',
    68: 'E5/4 D5/8 G4/4.',
    69: 'r/8 D5/8 F5/8 C6/4 A5/8',
    70: 'B5/4. G5/8 E5/8 D5/8',
    71: 'D6/4. Bb5/8 F5/8 D5/8',
    72: 'E5/4. G5/4.',
    73: 'C6/4 B5/8 A5/4 E5/8',
    74: 'F5/4. A5/8 G5/8 F5/8',
    75: 'B4/4 D5/8 G5/4.',
    76: 'D5/2.',
    # coda - the ostinato returns, thinning; Dm6
    77: 'D5/8 A4/8 E5/8 A4/8 F5/8 A4/8',
    78: 'G5/8 A4/8 F5/8 A4/8 E5/8 B4/8',
    79: 'D5/8 A4/8 E5/8 A4/8 r/4',
    80: 'r/4. B4/8 D5/8 A5/8',
    81: 'r/8 B4/8 D5/8 F5/4.',
    82: '[D4 A4 B4 F5]/2.^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar into dotted quarters). 6 tokens = the 8ths of a 6/8 bar.
FIG = {
    'cross': '0 3 4 2 3 1',          # the theme's hand: up to the 12th, crossing back inside
    'ten6': '0+3 - 2 - 1+4 -',       # the B hand: 10ths, a tone, a wider 10th
    'climb': '0 1 2 3 4 5',          # the build: up through the bar
    'hemi': 'o - 2+3 - 3+4 -',       # the climax: three quarter-note strokes (the hemiola in the left hand too)
    'surge': 'o 2 3 4 5 4',          # the climax's 6/8 bars
    'pedal': '0 - - - - -',          # one held bass
    'still6': '0+3 - - - - -',       # a 10th, held
    'half6': '0 2 3 - - -',          # three notes, the half bar rings
}

LH = {
    3: 'Dm:pedal', 4: 'G/D:half6 Dsus4:half6',
    5: 'Dm:cross', 6: 'G/D:cross', 7: 'Dm:cross', 8: 'C/E:cross',
    9: 'Dm:cross', 10: 'G/B:cross', 11: 'F:cross', 12: 'Am7:still6',
    13: 'Bb:cross', 14: 'C:cross', 15: 'Dm:cross', 16: 'Am/C:cross',
    17: 'Bbmaj7:cross', 18: 'C:cross', 19: 'G/B:cross', 20: 'Dm:half6 Dm/C:half6',
    21: 'Fmaj7:ten6', 22: 'G/F:ten6', 23: 'Em7:ten6', 24: 'Am7:ten6',
    25: 'Dm7:ten6', 26: 'G:ten6', 27: 'Cmaj7:ten6', 28: 'Am7:half6 Am7/G:half6',
    29: 'Fmaj7:ten6', 30: 'G/F:ten6', 31: 'Em7:ten6', 32: 'Am7:ten6',
    33: 'Dm7:ten6', 34: 'G:ten6', 35: 'Bbmaj7:ten6', 36: 'C7sus4:still6',
    37: 'Dm:climb', 38: 'Em7:climb', 39: 'F:climb', 40: 'G:climb',
    41: 'Am7:climb', 42: 'Bb:climb', 43: 'C:climb', 44: 'A7sus4:half6 A7:half6',
    45: 'Dm:hemi', 46: 'G/D:hemi', 47: 'Cmaj7:hemi', 48: 'Am7:surge', 49: 'Bbmaj7:surge',
    50: 'A7sus4:half6 A7:half6',
    51: 'Dm:pedal', 52: 'Bbmaj7:pedal',
    53: 'Bbmaj7:cross', 54: 'C/Bb:cross', 55: 'Am7:cross', 56: 'Dm7:cross',
    57: 'Gm7:cross', 58: 'C:cross', 59: 'Fmaj7:cross', 60: 'A7sus4:half6 A7:half6',
    61: 'Dm:ten6', 62: 'G/D:ten6', 63: 'Bbmaj7:ten6', 64: 'C:half6 C/E:half6',
    65: 'Dm:cross', 66: 'G/D:cross', 67: 'Dm/F:cross', 68: 'C/E:cross',
    69: 'Dm:cross', 70: 'G/B:cross', 71: 'Bb:cross', 72: 'C:cross',
    73: 'Am7:ten6', 74: 'Dm/F:ten6', 75: 'G:ten6', 76: 'G/D:still6',
    77: 'Dm:pedal', 78: 'G/D:pedal', 79: 'Dm:pedal', 80: 'G/D:pedal', 81: 'Dm6:pedal',
    82: 'Dm6:still6',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'pp'), (2, 0, 'p'), (2, 4, 'pp'), (3, 0, 'p'), (4, 3, 'mp'),
       (5, 0, 'p'), (9, 0, 'p'), (12, 0, 'p'), (13, 0, 'mp'), (17, 0, 'mp'), (20, 0, 'p'),
       (21, 0, 'p'), (25, 0, 'mp'), (28, 0, 'p'), (29, 0, 'p'), (31, 0, 'mp'), (33, 0, 'mp'), (36, 0, 'p'),
       (37, 0, 'p'), (38, 0, 'mp'), (40, 0, 'mp'), (42, 0, 'mf'), (43, 3, 'f'), (44, 3, 'mf'),
       (45, 0, 'f'), (45, 4, 'ff'), (46, 4, 'f'), (47, 4, 'mf'), (48, 3, 'mf'), (49, 0, 'mp'), (50, 3, 'p'),
       (51, 0, 'pp'), (52, 0, 'p'), (52, 3, 'pp'),
       (53, 0, 'pp'), (57, 0, 'p'), (60, 0, 'pp'), (61, 0, 'pp'), (62, 0, 'p'), (64, 0, 'pp'),
       (65, 0, 'pp'), (66, 0, 'p'), (68, 0, 'pp'), (69, 0, 'p'), (71, 0, 'mp'), (73, 0, 'p'), (76, 0, 'pp'),
       (77, 0, 'pp'), (78, 0, 'p'), (78, 4, 'pp'), (80, 3, 'p'), (81, 3, 'pp'), (82, 0, 'pp')]

PHRASES = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 40), (41, 44),
           (45, 47), (48, 50), (51, 52), (53, 56), (57, 60), (61, 64), (65, 68), (69, 72), (73, 76), (77, 82)]

SECTIONS = [('intro', 4), ('A1', 16), ('B1', 16), ('build', 8), ('climax', 6), ('inter', 2), ('B2', 12), ('A2', 12),
            ('coda', 6)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    s.ritardando((bar(4) + 1.5, bar(5)), to=0.88)
    for k in (8, 16, 24, 32, 56, 68):                   # the half-way breaths
        s.ritardando((bar(k) + 1.5, bar(k + 1)), to=0.9)
    for k in (12, 20, 28, 36, 64, 72):                  # cadences
        s.ritardando((bar(k) + 1.0, bar(k + 1)), to=0.82)
    s.set_tempo(bar(21), 80)                             # B: broader
    s.set_tempo(bar(37), 84)
    s.ritardando((bar(44) + 1.5, bar(45)), to=0.85)     # the inhale
    s.set_tempo(bar(45), 80)                             # the hemiola: weighty
    s.ritardando((bar(49), bar(51)), to=0.72, a_tempo=False)
    s.fermata(bar(50) + 1.5, hold=1.5)
    s.set_tempo(bar(51), 72)
    s.ritardando((bar(52), bar(53)), to=0.85)
    s.set_tempo(bar(53), 80)
    s.set_tempo(bar(65), 84)
    s.ritardando((bar(75), bar(77)), to=0.78, a_tempo=False)
    s.set_tempo(bar(77), 78)
    s.ritardando((bar(79), bar(82)), to=0.7, a_tempo=False)
    s.fermata(bar(82) + 1.0, hold=3)
    score.lilt(s, (0.0, bar(len(RH) + 1)), beats=None, jitter=0.03, seed=SEED)


def figures() -> list:
    """The left hand as [(beat, beats, chord, figure)] for Score.perform(figures=)."""
    out = []
    for k in sorted(LH):
        parts = LH[k].split()
        span = METER / len(parts)
        for i, part in enumerate(parts):
            sym, fig = part.split(':', 1)
            out.append((bar(k) + i * span, span, sym, FIG.get(fig, fig)))
    return out


def build() -> Song:
    s = Song(METADATA['title'], tempo=TEMPO, key=KEY, seed=SEED, tail=7, meter=TIME)
    for name, n in SECTIONS:
        s.section(name, bars=n)
    score = rom.score(RH, None, DYN, meter=f"{TIME[0]}/{TIME[1]}", unit='1/8', key=KEY, phrases=PHRASES)
    tempo_plan(s, score)
    F = G.feels[FEEL]
    feel = jazz.Feel(TEMPO, ratio=0.5, beats_per_bar=METER)
    b = perform.band(s, G, FEEL, feel)                 # exactly the endless new-age sound
    b.piano.humanize(body=F['body'])                    # the feel's body, the left hand following the right
    b.comp.humanize(body=F['body'], lead=b.piano.id)
    lo, hi = F['touch']
    tm = s.tempo_map()                                  # one tempo map for the pianist (as perform.build_piano)
    s.tempo_at = lambda beat: tm.bpm_at(s._at(beat))
    try:
        score.perform(s, b.piano, b.comp, pedal=True, touch=dict(lo=lo, hi=hi), breath=0.35, cap=106,
                      figures=figures(), inner=0.78)
    finally:
        del s.tempo_at
    return s
