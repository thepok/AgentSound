"""Rain on the Skylight - an original new-age piece for solo grand piano in F minor, 6/8.
Build: python -m agentsound build songs/pro-newage-skylight

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

6/8, dotted quarter = 42 (quarter 63), rubato, 66 bars. Ternary with the climax in the MIDDLE (end of the B part, ~55 %),
not near the end: the storm passes and the return is the quiet after it.

  intro   1-4    the right hand ALONE: single drops, high and soft; the left hand enters only in bar 3
  A1      5-20   the theme (C5 F5 Eb5 C5 - a leap up from the 5th to the root, a fall), two 8-bar sentences; the
                 second turns through the half-diminished ii and the Neapolitan Gbmaj7, closing on the tonic, melody
                 on the 3rd
  B1      21-32  D-flat major (VI): a new idea - a held note, three 8ths rising into the next bar - 4 + 4 + 4 bars,
                 the third phrase turning to B-flat minor and F7
  build   33-36  continuous 8ths in the right hand, a rising chromatic bass Bb - B - C (the dominant pedal)
  climax  37-42  "the downpour": over the C pedal the top Ab6 once, then falling 16th cascades through Db/C -
                 Bbm/C - Ab/C, resolving to F minor and dying away (no theme in chords)
  inter   43-46  the drops again, lower, over a single held bass
  A2      47-60  the theme returns changed: a pickup start, reharmonised (Fm/Eb, the Neapolitan earlier), its second
                 sentence rising pp to Eb6 and ending deceptively on Dbmaj7
  coda    61-66  drops over Bbm6, the head's leap once more, and F MAJOR at the very end (the sun after the rain)

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Rain on the Skylight', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#cdd5de', '#2f3c4f'], 'title': 'RAIN ON THE SKYLIGHT',
         'subtitle': 'solo piano - AgentSound', 'seed': 23}

G = _genre('new-age-piano')
FEEL = 'gentle'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'F minor'
TIME = (6, 8)
METER = 3                  # quarter beats per bar
TEMPO = 63
SEED = 23

# ------------------------------------------------------------------------------------------------ right hand
# one entry per bar, notation (agentsound.notation, unit 1/8): 6 eighths per bar
RH = {
    # intro - drops, the right hand alone (the left hand from bar 3)
    1: 'r/8 C6/8 r/4 G5/8 r/8',
    2: 'r/8 Ab5/8 r/8 Eb6/8 r/4',
    3: 'r/4 F5/8 C6/4.',
    4: 'r/8 Bb5/8 Ab5/8 G5/4.',
    # A1 - the theme, first sentence
    5: 'C5/4. F5/8 Eb5/8 C5/8',
    6: 'Db5/4. C5/4 Ab4/8',
    7: 'Bb4/8 Db5/8 F5/8 Ab5/4.',
    8: 'G5/4 F5/8 E5/4 r/8',
    9: 'C5/4. F5/8 G5/8 Ab5/8',
    10: 'Bb5/2 G5/8 Eb5/8',
    11: 'C6/4 Bb5/8 Ab5/8 G5/8 Eb5/8',
    12: 'F5/4 Db5/8 C5/4.',
    # A1 - second sentence
    13: 'r/8 C5/8 F5/8 Ab5/4 G5/8',
    14: 'F5/4.^turn Eb5/8 Db5/8 C5/8',
    15: 'Bb4/8 Db5/8 F5/8 Ab5/8 G5/8 F5/8',
    16: 'E5/4 G5/8 Bb5/4.',
    17: 'Ab5/4. F5/8 Bb5/8 Db6/8',
    18: 'Db6/4 Bb5/8 F5/4.',
    19: 'G5/4 F5/8 E5/8 C5/8 Bb4/8',
    20: 'Ab4/4. r/4.',
    # B1 - D-flat major: a held note, three 8ths rising into the next
    21: 'F5/4. Ab5/8 Bb5/8 C6/8',
    22: 'Db6/2.',
    23: 'Ab5/4. F5/8 Eb5/8 Db5/8',
    24: 'Gb5/4 Bb5/8 Ab5/4 r/8',
    25: 'F5/4. Ab5/8 Bb5/8 Db6/8',
    26: 'F6/2 Eb6/8 Db6/8',
    27: 'Bb5/4. Ab5/8 Gb5/8 F5/8',
    28: 'Gb5/4. Eb5/4 r/8',
    29: 'Db6/4. F5/8 Gb5/8 Ab5/8',
    30: 'Bb5/2 Gb5/8 Eb5/8',
    31: 'Gb5/4. Eb5/8 Db5/8 Bb4/8',
    32: 'A4/4. C5/8 Eb5/8 F5/8',
    # build - the rain gets heavier: continuous 8ths over a rising bass
    33: 'F5/8 Bb5/8 Db6/8 C6/8 Bb5/8 F5/8',
    34: 'Ab5/8 B5/8 D6/8 F6/8 D6/8 B5/8',
    35: 'C6/8 F6/8 G6/8 F6/8 C6/8 Bb5/8',
    36: 'E6/4. r/8 G5/8 C6/8',
    # climax - the downpour over the dominant pedal
    37: 'Ab6/4. F6/16 Eb6/16 Db6/16 C6/16 Ab5/16 F5/16',
    38: '[Db6 F6]/4. Eb6/16 Db6/16 Bb5/16 F5/16 Bb5/16 Db6/16',
    39: '[C6 Eb6]/4. Db6/16 C6/16 Ab5/16 Eb5/16 Ab5/16 C6/16',
    40: 'E6/4. Db6/8 Bb5/8 G5/8',
    41: '[Ab5 F6]/4. Eb6/8 Db6/8 C6/8',
    42: 'Db6/4 C6/8 [E5 Bb5]/4.',
    # interlude - the drops, lower, over one held bass
    43: 'r/8 F5/8 r/4 C5/8 r/8',
    44: 'r/8 Ab4/8 r/8 Eb5/8 r/4',
    45: 'r/4 Db5/8 Bb4/4.',
    46: 'r/8 G4/8 B4/8 C5/4.',
    # A2 - the theme returns, a pickup start, reharmonised
    47: 'r/4. C5/8 F5/8 Ab5/8',
    48: 'Ab5/4.^mord G5/8 F5/8 C5/8',
    49: 'Db5/4. C5/4 Ab4/8',
    50: 'Bb4/8 Db5/8 F5/8 Ab5/4.',
    51: 'Bb5/4. Gb5/8 F5/8 Db5/8',
    52: 'E5/4. G5/8 Bb5/8 Db6/8',
    53: 'C6/2 Ab5/8 F5/8',
    54: 'Db6/4 F5/8 Ab5/4 r/8',
    55: 'G5/4. Eb5/8 Db5/8 Bb4/8',
    56: 'C5/4. r/4.',
    57: 'F5/4. Ab5/8 C6/8 Eb6/8',
    58: 'Db6/2 C6/8 Ab5/8',
    59: 'G5/4 F5/8 E5/4 G4/8',
    60: 'F5/2.',
    # coda - drops over Bbm6, the head's leap once more, F major
    61: 'r/8 Db6/8 r/4 Bb5/8 r/8',
    62: 'r/8 G5/8 r/8 Ab5/8 F5/4',
    63: 'C5/4. F5/8 Eb5/8 Db5/8',
    64: 'C5/4 Bb4/8 E5/4.',
    65: 'r/8 C5/8 F5/8 A5/4.',
    66: '[F4 C5 E5 A5]/2.^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar into dotted quarters). 6 tokens = the 8ths of a 6/8 bar,
# 12 = 16ths. Ladder: 0 = the bass, 1 2 3 ... the chord tones above it, x the colour tone, o bass + octave below,
# c = steps 1-3 together, R rolled and held, a+b together, '-' holds.
FIG = {
    'drip': '0 - 3 - 2 -',         # the rain hand: bass, a 10th, a 5th - sparse, the pedal rings
    'rock6': '0 2 3 4 3 2',        # the barcarolle wave
    'tide': '0 3 2 4 3 1',         # wider, a turn inside: the B part's hand
    'climb': '0 1 2 3 4 5',        # rising through the bar
    'pedal': '0 - - - - -',        # one bass note, held
    'still6': '0+3 - - - - -',     # a 10th, held: the hand rests under a breath
    'pour': 'o 2 3 4 5 4 3 4 5 4 3 2',   # 16ths: the downpour's left hand
    'half6': '0 2 3 - - -',        # three notes, then the half bar rings
}

LH = {
    3: 'Fmadd9:drip', 4: 'C7sus4:drip',
    5: 'Fm:rock6', 6: 'Dbmaj7:rock6', 7: 'Bbm7:rock6', 8: 'C7sus4:half6 C7:half6',
    9: 'Fm:rock6', 10: 'Eb/G:rock6', 11: 'Abmaj7:rock6', 12: 'Bbm6:half6 C7:half6',
    13: 'Fm/Ab:drip', 14: 'Dbmaj7:rock6', 15: 'Gm7b5:rock6', 16: 'C7:rock6',
    17: 'Db:rock6', 18: 'Gbmaj7:rock6', 19: 'C7sus4:half6 C7:half6', 20: 'Fm:still6',
    21: 'Db:tide', 22: 'Gb/Db:tide', 23: 'Db/F:tide', 24: 'Ebm7:half6 Ab7:half6',
    25: 'Db:tide', 26: 'Bbm7:tide', 27: 'Gbmaj7:tide', 28: 'Ab7sus4:half6 Ab7:half6',
    29: 'Bbm:tide', 30: 'Gb:tide', 31: 'Ebm7:tide', 32: 'F7:climb',
    33: 'Bbm:climb', 34: 'Bdim7:climb', 35: 'C7sus4:climb', 36: 'C7:still6',
    37: 'Db/C:pour', 38: 'Bbm/C:pour', 39: 'Ab/C:pour', 40: 'C7:pour', 41: 'Fm:climb', 42: 'Bbm6:half6 C7:half6',
    43: 'Fm:pedal', 44: 'Fm/Eb:pedal', 45: 'Dbmaj7:pedal', 46: 'G7/B:half6 C7:half6',
    47: 'Fm:drip', 48: 'Fm/Eb:rock6', 49: 'Dbmaj7:rock6', 50: 'Bbm7:rock6',
    51: 'Gbmaj7:rock6', 52: 'C7:rock6', 53: 'Fm/Ab:rock6', 54: 'Bbm7:half6 Bbm7/Ab:half6',
    55: 'Eb7/G:rock6', 56: 'Abmaj7:still6',
    57: 'Dbmaj7:drip', 58: 'Bbm7:drip', 59: 'C7sus4:half6 C7:half6', 60: 'Dbmaj7:still6',
    61: 'Bbm6:pedal', 62: 'C7sus4:pedal', 63: 'Fm:drip', 64: 'Bbm6:half6 C7:half6', 65: 'Fsus4:pedal',
    66: 'Fadd9:still6',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'pp'), (2, 1, 'p'), (2, 3, 'pp'), (3, 0, 'p'), (3, 3, 'mp'), (4, 3, 'pp'),
       (5, 0, 'p'), (9, 0, 'p'), (11, 0, 'mp'), (12, 3, 'p'), (13, 0, 'p'), (17, 0, 'mp'), (19, 3, 'p'),
       (20, 0, 'pp'),
       (21, 0, 'p'), (22, 0, 'mp'), (24, 3, 'p'), (25, 0, 'mp'), (26, 0, 'mf'), (28, 3, 'p'), (29, 0, 'mp'),
       (31, 3, 'p'), (32, 3, 'mp'),
       (33, 0, 'p'), (34, 0, 'mp'), (35, 0, 'mf'), (35, 4, 'f'), (36, 0, 'f'), (36, 3, 'mp'),
       (37, 0, 'ff'), (38, 0, 'f'), (39, 0, 'f'), (40, 0, 'mf'), (41, 0, 'mf'), (42, 0, 'mp'), (42, 3, 'p'),
       (43, 0, 'pp'), (44, 1, 'p'), (44, 3, 'pp'), (45, 0, 'p'), (46, 3, 'pp'),
       (47, 0, 'pp'), (48, 0, 'p'), (51, 0, 'mp'), (52, 3, 'mp'), (54, 3, 'p'), (55, 0, 'p'), (56, 0, 'pp'),
       (57, 0, 'pp'), (58, 0, 'p'), (60, 0, 'pp'),
       (61, 0, 'p'), (61, 4, 'pp'), (63, 0, 'p'), (63, 3, 'mp'), (64, 3, 'pp'), (65, 0, 'p'), (66, 0, 'pp')]

PHRASES = [(1, 2), (3, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 39),
           (40, 42), (43, 46), (47, 50), (51, 56), (57, 60), (61, 62), (63, 66)]

# sections, in order, with bars (the endless vocabulary, which the blind packets print)
SECTIONS = [('intro', 4), ('A1', 16), ('B1', 12), ('build', 4), ('climax', 6), ('inter', 4), ('A2', 14), ('coda', 6)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    s.ritardando((bar(2) + 1.5, bar(3)), to=0.85)
    for k in (8, 24, 28):                               # the half-way breaths
        s.ritardando((bar(k) + 1.5, bar(k + 1)), to=0.88)
    for k in (12, 20, 32, 56):                          # cadences / section ends
        s.ritardando((bar(k) + 1.0, bar(k + 1)), to=0.8)
    s.ritardando((bar(36) + 1.5, bar(37)), to=0.8)      # the inhale before the downpour
    s.set_tempo(bar(37), 66)                             # the storm pushes
    s.ritardando((bar(41), bar(43)), to=0.72, a_tempo=False)
    s.fermata(bar(42) + 1.5, hold=2.0)                  # the half cadence rings out
    s.set_tempo(bar(43), 60)                             # after the storm
    s.ritardando((bar(46), bar(47)), to=0.85)
    s.set_tempo(bar(47), 60)
    s.ritardando((bar(59) + 1.5, bar(61)), to=0.78, a_tempo=False)
    s.fermata(bar(60) + 1.5, hold=1.5)                  # the deceptive Dbmaj7 hangs
    s.set_tempo(bar(61), 56)
    s.ritardando((bar(64), bar(66)), to=0.75, a_tempo=False)
    s.fermata(bar(66) + 1.0, hold=3)
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
