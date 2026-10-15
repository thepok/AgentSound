"""Where the Light Lingers - an original new-age / pop-classical waltz for solo grand piano in E-flat major.
Build: python -m agentsound build songs/pro-newage-waltz

A composed ("pro") reference for the endless new-age blind rounds (songs/_blind/ROUNDS.md "New-age"): written by
hand like songs/letters-to-the-morning, played by the SAME setup as an endless new-age tune (agentsound.endless.perform
.band with the new-age-piano genre spec: the solo_piano grand, the genre's eq / master; the romantic pianist
romantic.Score.perform with the feel's touch, the shared broken-chord left hand pianist.FIGURES, the feel's body),
so the sound and the player are no tell - only the writing differs.

3/4, 96 BPM (the return 88, the coda 84), E-flat major with a C-minor middle, 101 bars, ~3:30.
The theme: a pickup of two 8ths rising a sixth into a note held across the bar line, then a stepwise fall (it sings
over the bar, never on the downbeat); its two halves answer each other over a falling bass (Eb-D-C-Ab) and a rising
one (F-G-Ab-Bb); the borrowed Abm6 (C -> Cb in the melody) is the piece's tear and comes back in every section.

  intro   1-6    the left hand alone (a flowing arpeggio over the bar), then the theme's head high and soft, pp
  A1      7-22   the theme, p (Bb4-Bb5): 4+4 question over the falling bass / answer over the rising bass; the
                 second half climbs to Bb5 and turns through Abm6 to a ii-V-I; rocking barcarolle hand, held under
                 every breath
  A2      23-38  the theme varied (its head turns upward to Bb5), sixths under its long notes, mf; a C7/E (V/ii)
                 opens a higher answer (Ab5) that sequences down to Abm6 again; the hand flows with 7ths / 9ths
  B1      39-54  C minor over a lament bass (C-Bb-Ab-G): a new figure (three 8ths rising into a tied note) sequenced
                 up a third and a sixth, a half cadence on G7/B; the second strain climbs to C6 and bends C -> Cb6
                 over Abm6, then settles; the open, walking left hand
  inter   55-58  air: the theme's head in the treble, whole bars of held left hand
  build   59-66  the head sequenced up by thirds (Abmaj7 - Bb/Ab - Gm7 - C7 - Fm7 - Dbmaj7 = bVII), the left hand
                 climbing to two octaves, mp -> f, a held inhale on Bb
  climax  67-78  the theme in chords an octave up, f -> ff: C7/E into the peak C7-Ab6-F6 over Fm7 (bar 72), Abm6,
                 a ritardando into a rolled Bb7 held on a fermata - then the deceptive Cm, the music melts
  A3      79-94  the return, calmer: the theme an octave up, pp, a music box over a sparse hand; then in the middle
                 register with sixths, Abm6 once more and a deceptive cadence to Cm
  coda    95-101 the head high once more, Abmaj7 -> Abm6 (C6 -> Cb6), the opening of the answer in the middle, and a
                 rolled Eb(add9) left to ring

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Where the Light Lingers', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#f1e6d6', '#7b6a8f'], 'title': 'WHERE THE LIGHT LINGERS',
         'subtitle': 'solo piano - AgentSound', 'seed': 23}

G = _genre('new-age-piano')
FEEL = 'gentle'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'Eb major'
METER = 3                  # 4 or 3
TEMPO = 96
SEED = 23

# ------------------------------------------------------------------------------------------------ right hand
# one entry per bar, notation (agentsound.notation, unit 1/8): E5/4. = a dotted quarter, r = rest, [B4 E5]/2 = notes
# together, ^turn / ^tr ornaments, [..]/1^roll(110) a rolled chord, {..}:N^fig(arch) a fioritura
RH = {
    # intro - the left hand alone, then the head high and soft
    1: 'r/2.', 2: 'r/2.',
    3: 'r/4 Bb5/8 Eb6/8 G6/4~',
    4: 'G6/4 F6/8 Eb6/8 D6/4',
    5: 'Eb6/2.',
    6: 'r/2.',
    # A1 - the theme: question over the falling bass, answer over the rising bass
    7: 'r/4 Bb4/8 Eb5/8 G5/4~',
    8: 'G5/4 F5/8 Eb5/8 D5/4',
    9: 'Eb5/4 D5/8 C5/8 Bb4/4',
    10: 'C5/2 r/4',
    11: 'r/4 Ab4/8 C5/8 Eb5/4~',
    12: 'Eb5/4 D5/8 Eb5/8 G5/4',
    13: 'F5/4. Eb5/8 C5/4',
    14: 'Eb5/4. D5/4.',
    # the second half: the head turns upward, the Abm6 tear, ii-V-I
    15: 'r/4 Bb4/8 Eb5/8 G5/4~',
    16: 'G5/4 F5/8 Eb5/8 F5/8 G5/8',
    17: 'Bb5/4. Ab5/8 G5/8 F5/8',
    18: 'G5/2 F5/8 Eb5/8',
    19: 'F5/4. Eb5/8 Cb5/4',
    20: 'Bb4/4 r/8 G4/8 Bb4/8 Eb5/8',
    21: 'G5/4. F5/8 Eb5/8 D5/8',
    22: 'Eb5/2 r/4',
    # A2 - the head bent upward, sixths under the long notes, a higher answer
    23: 'r/4 Bb4/8 Eb5/8 G5/4~',
    24: 'G5/4 F5/8 G5/8 Bb5/4',
    25: '[Eb5 C6]/4. Bb5/8 G5/4',
    26: '[C5 Ab5]/2 r/4',
    27: 'r/4 Ab4/8 C5/8 Eb5/4~',
    28: 'Eb5/4 D5/8 Eb5/8 [Bb4 G5]/4',
    29: '[Ab4 F5]/4. Eb5/8 [Ab4 C5]/4',
    30: 'Bb4/4 r/8 C5/8 E5/8 G5/8',
    31: 'Ab5/4. G5/8 F5/8 Eb5/8',
    32: 'D5/8 Eb5/8 F5/4 Ab5/4',
    33: 'G5/4. F5/8 Eb5/8 D5/8',
    34: 'C5/8 D5/8 Eb5/4 G5/4',
    35: '[Cb5 F5]/4. Eb5/8 [Ab4 Cb5]/4',
    36: '[G4 Bb4]/2 r/8 Bb4/8',
    37: 'Eb5/4. D5/8 C5/8 D5/8',
    38: '[G4 Eb5]/2 r/4',
    # B1 - C minor over a lament bass; a new figure: three 8ths rising into a tied note
    39: 'r/8 G4/8 C5/8 D5/8 Eb5/4~',
    40: 'Eb5/4 D5/8 C5/8 D5/4',
    41: 'r/8 Ab4/8 C5/8 Eb5/8 G5/4~',
    42: 'G5/4 F5/8 Eb5/8 D5/4',
    43: 'r/8 Ab4/8 C5/8 F5/8 Ab5/4~',
    44: 'Ab5/4 G5/8 F5/8 Eb5/8 D5/8',
    45: 'Eb5/4. D5/8 Eb5/8 F5/8',
    46: '[B4 D5]/2 r/4',
    47: 'r/8 G4/8 C5/8 D5/8 Eb5/4~',
    48: 'Eb5/4 F5/8 G5/8 Ab5/4~',
    49: 'Ab5/4 G5/8 Ab5/8 C6/4',
    50: 'Cb6/4. Bb5/8 Ab5/4',
    51: 'G5/2.',
    52: 'r/4 F5/8 G5/8 Ab5/8 Bb5/8',
    53: 'G5/4. F5/8 Eb5/4',
    54: 'F5/2 r/4',
    # interlude - air
    55: 'r/4 Bb5/8 Eb6/8 G6/4~',
    56: 'G6/2 r/4',
    57: 'r/4 G5/8 C6/8 Eb6/4~',
    58: 'Eb6/4. D6/8 r/4',
    # build - the head sequenced up by thirds
    59: 'r/4 C5/8 Eb5/8 G5/4~',
    60: 'G5/4 F5/8 G5/8 Bb5/4',
    61: 'r/4 D5/8 G5/8 Bb5/4~',
    62: 'Bb5/4 A5/8 Bb5/8 C6/4',
    63: 'r/4 F5/8 Ab5/8 C6/4~',
    64: 'C6/4 Bb5/8 Ab5/8 F5/4',
    65: 'Eb6/4. C6/8 Bb5/8 Ab5/8',
    66: 'Bb5/2 r/4',
    # climax - the theme in chords, an octave up; the peak over Fm7; the fermata on Bb7; the deceptive Cm
    67: 'r/4 Bb5/8 Eb6/8 [Bb5 G6]/4~',
    68: '[Bb5 G6]/4 F6/8 G6/8 [F6 Bb6]/4',
    69: '[Eb6 Bb6]/4. Ab6/8 G6/4',
    70: '[C6 Eb6 Ab6]/4. G6/8 F6/8 G6/8',
    71: '[Bb5 E6 G6]/4. F6/8 G6/8 Bb6/8',
    72: '[F6 Ab6 C7]/2 Bb6/8 Ab6/8',
    73: '[Cb6 F6]/4. Eb6/8 [Ab5 Cb6]/4',
    74: '[Bb5 G6]/2 F6/8 Eb6/8',
    75: '[Ab5 Eb6]/4. [Ab5 D6]/4.',
    76: '[F5 Ab5 D6]/2.^roll(70)',
    77: 'r/4 G5/8 C6/8 Eb6/4~',
    78: 'Eb6/4. D6/4.',
    # A3 - the return: the theme an octave up, pp (a music box), then in the middle with sixths
    79: 'r/4 Bb5/8 Eb6/8 G6/4~',
    80: 'G6/4 F6/8 Eb6/8 D6/4',
    81: 'Eb6/4 D6/8 C6/8 Bb5/4',
    82: 'C6/2 r/4',
    83: 'r/4 Ab5/8 C6/8 Eb6/4~',
    84: 'Eb6/4 D6/8 Eb6/8 G6/4',
    85: 'F6/4. Eb6/8 C6/4',
    86: 'Eb6/4. D6/4.',
    87: 'r/4 Bb4/8 Eb5/8 G5/4~',
    88: 'G5/4 F5/8 G5/8 [D5 Bb5]/4',
    89: '[Eb5 C6]/4. Bb5/8 G5/4',
    90: '[Cb5 F5]/4. Eb5/8 [Ab4 Cb5]/4',
    91: '[G4 Bb4]/2 r/8 Bb4/8',
    92: 'Eb5/4. D5/8 C5/8 D5/8',
    93: 'Eb5/2 D5/8 C5/8',
    94: 'C5/2 r/4',
    # coda - the head once more, the tear, the answer's opening, a rolled Eb(add9)
    95: 'r/4 Bb5/8 Eb6/8 G6/4~',
    96: 'G6/4 F6/8 Eb6/8 C6/4',
    97: 'Cb6/2.',
    98: 'Bb5/2 r/4',
    99: 'r/4 Ab4/8 C5/8 Eb5/4~',
    100: 'Eb5/4. D5/4.',
    101: '[Bb4 Eb5 F5 G5 Bb5]/2.^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two or three entries split the bar evenly). figure = a pianist.FIGURES name (flow rock
# color lilt open quart ring half up big sweep roll tenths walk10 still; 3/4: waltz waltz2 barcarolle waltz_held
# waltz_open waltz_arp waltz_step waltz_big) or your own token string over the chord's ladder (0 = the bass, 1 2 3 ...
# the chord tones above it, x = the colour tone, o = bass + its octave below, c = steps 1-3 together, R = rolled and
# held, a+b together, '-' holds): 8 tokens = 8ths in 4/4, 6 = 8ths in 3/4, 16 = 16ths.
# This piece's own 3/4 figures (named, since an LH entry is split on spaces):
FIG = {
    'ring3': '0 2 3 - - -',        # up, then the bar rings under a held melody note / a breath
    'arpx': '0 2 3 x 3 2',         # the arpeggio through the 7th / 9th / 6th
    'xring3': '0 2 x 3 - -',       # the colour tone, then ring
    'climb6': '0 1 2 3 4 5',       # climbing over the bar (the build)
    'air3': '0 - 3 - - -',         # bass and its 10th: the hand almost still
    'airx3': '0 - 3 - x -',        # the 10th and the colour tone, slow
    'bigarp3': 'o 2 3 4 5 3',      # the climax: bass octave, two octaves of chord
    'bigup3': 'o 3 4 5 4 3',
    'roll3': 'R - - - - -',        # a rolled chord, held
}

LH = {
    # intro
    1: 'Ebadd9:waltz_arp', 2: 'Abmaj7:waltz_arp', 3: 'Eb:waltz_arp', 4: 'Bb/D:waltz_arp', 5: 'Cm7:ring3',
    6: 'Bbsus4:waltz_held Bb:waltz_held',
    # A1 - the rocking barcarolle hand, still under the breaths
    7: 'Eb:barcarolle', 8: 'Bb/D:barcarolle', 9: 'Cm7:waltz_arp', 10: 'Abmaj7:ring3',
    11: 'Fm7:barcarolle', 12: 'Eb/G:barcarolle', 13: 'Abadd9:waltz_arp', 14: 'Bbsus4:ring3 Bb:waltz_held',
    15: 'Eb:barcarolle', 16: 'Bb/D:waltz2', 17: 'Cm7:barcarolle', 18: 'Abmaj7:waltz_arp',
    19: 'Abm6:arpx', 20: 'Eb/G:ring3', 21: 'Fm7:barcarolle Bb7:barcarolle', 22: 'Eb:waltz_held',
    # A2 - flowing over the bar, the colour tones inside
    23: 'Eb:waltz_arp', 24: 'Bb/D:waltz_arp', 25: 'Cm7:arpx', 26: 'Abmaj7:ring3',
    27: 'Fm7:waltz_arp', 28: 'Eb/G:waltz_arp', 29: 'Ab/C:waltz_arp', 30: 'C7/E:xring3',
    31: 'Fm7:arpx', 32: 'Bb7:waltz_arp', 33: 'Eb/G:waltz_arp', 34: 'Abmaj7:arpx',
    35: 'Abm6:xring3', 36: 'Eb/Bb:ring3', 37: 'Fm7:waltz_arp Bb7:waltz_arp', 38: 'Eb:waltz_held',
    # B1 - the open, walking hand over the lament bass; the second strain flows again
    39: 'Cm:waltz_open', 40: 'Cm/Bb:waltz_step', 41: 'Abmaj7:waltz_open', 42: 'G7sus4:waltz_open G7:waltz_open',
    43: 'Fm7:waltz_step', 44: 'Bb7:waltz_open', 45: 'Ebmaj7:waltz_step', 46: 'G7/B:waltz_held',
    47: 'Cm:waltz_arp', 48: 'Cm/Bb:waltz_arp', 49: 'Abmaj7:arpx', 50: 'Abm6:arpx',
    51: 'Eb/G:ring3', 52: 'Fm7:waltz_arp', 53: 'Eb/Bb:waltz_arp', 54: 'Bbsus4:waltz_held Bb:waltz_held',
    # interlude - air
    55: 'Ebadd9:air3', 56: 'Abmaj7:airx3', 57: 'Cm7:air3', 58: 'Bbsus4:roll3',
    # build - widening, climbing
    59: 'Abmaj7:waltz_arp', 60: 'Bb/Ab:waltz_arp', 61: 'Gm7:arpx', 62: 'C7:arpx',
    63: 'Fm7:climb6', 64: 'Dbmaj7:climb6', 65: 'Ab/Bb:bigarp3', 66: 'Bbsus4:ring3 Bb7:ring3',
    # climax
    67: 'Eb:bigarp3', 68: 'Bb/D:bigup3', 69: 'Cm7:bigarp3', 70: 'Abmaj7:bigup3',
    71: 'C7/E:bigarp3', 72: 'Fm7:bigup3', 73: 'Abm6:bigarp3', 74: 'Eb/Bb:bigup3',
    75: 'Fm7:bigarp3 Bb7:bigarp3', 76: 'Bb7:roll3', 77: 'Cm:waltz_arp', 78: 'Abmaj7:ring3 Bb:ring3',
    # A3 - sparse under the music box, then the barcarolle again
    79: 'Eb:air3', 80: 'Bb/D:air3', 81: 'Cm7:airx3', 82: 'Abmaj7:ring3',
    83: 'Fm7:air3', 84: 'Eb/G:air3', 85: 'Abadd9:airx3', 86: 'Bbsus4:waltz_held Bb:waltz_held',
    87: 'Eb:barcarolle', 88: 'Bb/D:barcarolle', 89: 'Cm7:arpx', 90: 'Abm6:xring3',
    91: 'Eb/Bb:ring3', 92: 'Fm7:barcarolle Bb7:barcarolle', 93: 'Cm:ring3', 94: 'Abmaj7:waltz_held',
    # coda
    95: 'Ebadd9:waltz_arp', 96: 'Abmaj7:waltz_arp', 97: 'Abm6:xring3', 98: 'Eb/Bb:ring3',
    99: 'Ab/C:air3', 100: 'Bbsus4:waltz_held Bb:waltz_held', 101: 'Ebadd9:roll3',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'pp'), (3, 0, 'p'), (5, 0, 'pp'),
       (7, 0, 'p'), (11, 0, 'p'), (13, 0, 'mp'), (14, 3, 'p'), (15, 0, 'p'), (17, 0, 'mp'), (19, 0, 'mp'),
       (21, 3, 'p'), (22, 0, 'p'),
       (23, 0, 'mp'), (25, 0, 'mf'), (26, 3, 'mp'), (27, 0, 'mp'), (30, 0, 'mp'), (31, 0, 'mf'), (33, 0, 'mf'),
       (35, 0, 'mp'), (37, 0, 'mp'), (38, 0, 'p'),
       (39, 0, 'p'), (41, 0, 'mp'), (43, 0, 'mf'), (45, 0, 'mp'), (46, 0, 'p'), (47, 0, 'mp'), (49, 0, 'mf'),
       (50, 3, 'mf'), (51, 0, 'mp'), (53, 0, 'p'), (54, 0, 'p'),
       (55, 0, 'pp'), (58, 3, 'pp'),
       (59, 0, 'p'), (61, 0, 'mp'), (63, 0, 'mf'), (65, 0, 'f'), (66, 3, 'mf'),
       (67, 0, 'f'), (69, 0, 'f'), (71, 0, 'ff'), (72, 3, 'ff'), (73, 3, 'f'), (75, 0, 'f'), (76, 0, 'mf'),
       (77, 0, 'mp'), (78, 3, 'p'),
       (79, 0, 'pp'), (83, 0, 'p'), (86, 3, 'pp'), (87, 0, 'p'), (89, 0, 'mp'), (91, 0, 'p'), (93, 0, 'pp'),
       (95, 0, 'pp'), (96, 3, 'p'), (98, 0, 'pp'), (99, 0, 'pp'), (101, 0, 'pp')]

PHRASES = [(1, 6), (7, 10), (11, 14), (15, 18), (19, 22), (23, 26), (27, 30), (31, 34), (35, 38),
           (39, 42), (43, 46), (47, 50), (51, 54), (55, 58), (59, 62), (63, 66), (67, 70), (71, 74), (75, 78),
           (79, 82), (83, 86), (87, 90), (91, 94), (95, 98), (99, 101)]

# sections, in order, with bars - names from the endless vocabulary: intro, A1, A2, A3, A4, B1, B2, inter, build,
# climax, coda (the blind packets print these names)
SECTIONS = [('intro', 6), ('A1', 16), ('A2', 16), ('B1', 16), ('inter', 4), ('build', 8), ('climax', 12),
            ('A3', 16), ('coda', 7)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    for k in (10, 18, 26, 42, 50, 82):                 # the breaths half-way through a period
        s.ritardando((bar(k) + 1.0, bar(k) + 3.0), to=0.9)
    for k in (6, 14, 22, 30, 38, 46, 54, 86):          # cadences / half cadences
        s.ritardando((bar(k) + 0.5, bar(k) + 3.0), to=0.8)
    s.ritardando((bar(58), bar(59)), to=0.8)           # the interlude's last bar
    s.ritardando((bar(66) + 1.0, bar(67)), to=0.85)    # the inhale before the climax
    s.ritardando((bar(74) + 1.5, bar(76) + 1.0), to=0.72, a_tempo=False)
    s.fermata(bar(76) + 2.0, hold=2.5)                 # the rolled Bb7 rings
    s.set_tempo(bar(77), 92)                           # the deceptive Cm: the music melts
    s.ritardando((bar(78), bar(79)), to=0.85, a_tempo=False)
    s.set_tempo(bar(79), 88)                           # the return: calmer
    s.ritardando((bar(93) + 1.0, bar(95)), to=0.8, a_tempo=False)
    s.set_tempo(bar(95), 84)
    s.ritardando((bar(99), bar(101)), to=0.75, a_tempo=False)
    s.fermata(bar(101) + 1.0, hold=3)
    score.lilt(s, (0.0, bar(len(RH) + 1)), beats={3: 0.03} if METER == 4 else {2: 0.04}, jitter=0.03, seed=SEED)


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
    s = Song(METADATA['title'], tempo=TEMPO, key=KEY, seed=SEED, tail=7, meter=(METER, 4))
    for name, n in SECTIONS:
        s.section(name, bars=n)
    score = rom.score(RH, None, DYN, meter=f"{METER}/4", unit='1/8', key=KEY, phrases=PHRASES)
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
