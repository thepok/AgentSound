"""First Light Over the Fields - an original new-age / pop-classical piece for solo grand piano in D major.
Build: python -m agentsound build songs/pro-newage-hopeful

A composed ("pro") reference for the endless new-age blind rounds (songs/_blind/ROUNDS.md "New-age"): written by
hand like songs/letters-to-the-morning, played by the SAME setup as an endless new-age tune (agentsound.endless.perform
.band with the new-age-piano genre spec: the solo_piano grand, the genre's eq / master; the romantic pianist
romantic.Score.perform with the feel's touch, the shared broken-chord left hand pianist.FIGURES, the feel's body),
so the sound and the player are no tell - only the writing differs.

Hopeful, forward-moving, sunlight: 4/4, 84 BPM (the return 78, the coda 74), D major with a lift to E major for the
last chorus, 68 bars, ~3:20.

  intro   1-4    the left hand alone over a D pedal (D - Gmaj7/D), then the chorus hook's head high and soft
  A1      5-12   the verse theme (A4-B5, p): a pickup 8th, a held note, a turn upward; answered a third lower over
                 Bm7, the question left open on the 9th of G; the second half climbs to B5 and settles on A (half
                 cadence)
  A2      13-20  the theme again, its answer higher (G5 / B5), F#m7 as a fresh turn, a full cadence on D
  B1      21-28  the chorus hook: syncopated (8th - quarter - 8th - half), a rising sixth into a held note, a
                 bar higher than the verse; sequenced up a step (G -> F#m7), F#7 (V of vi) and the borrowed Gm6
                 at its end, a half cadence on A
  inter   29-32  D pedal, the theme's cell in the treble, whole bars of air, a rolled Asus4
  A3      33-40  the theme harmonized in sixths over a walking bass (D C# B A G F# E, then up F# G G# A G F# A#)
                 with E7/G# (V of V) and A7/G - leading into B minor
  build   41-46  B minor, the theme's cell sequenced up (B5 -> E6 -> G6), the left hand widening into 16ths,
                 the unexpected Cmaj7 (bVII) sliding into B7sus4 - B7: the pivot to E
  climax  47-54  the chorus a step up in E major, in chords, its peak raised to A6 (ff, bar 51), G#7 (V of vi),
                 Am6 (the borrowed iv of E), then E/B - A7sus4 held on a fermata: A is IV of E and V of D
  A4      55-62  home: the theme an octave higher, pp, over quarter notes; Gm6 under its answer, a deceptive
                 cadence to Bm7
  coda    63-68  the chorus hook echoed softly over Gmaj7 - Gm6 - D/F#, the theme's first cell once more, a rolled
                 D(add9)

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'First Light Over the Fields', 'artist': 'AgentSound', 'album': 'Solo Piano',
            'genre': 'New Age', 'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#f4ead2', '#d98c5f'], 'title': 'FIRST LIGHT OVER THE FIELDS',
         'subtitle': 'solo piano - AgentSound', 'seed': 19}

G = _genre('new-age-piano')
FEEL = 'bright'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'D major'
METER = 4                  # 4 or 3
TEMPO = 84
SEED = 19

# ------------------------------------------------------------------------------------------------ right hand
# one entry per bar, notation (agentsound.notation, unit 1/8): E5/4. = a dotted quarter, r = rest, [B4 E5]/2 = notes
# together, ^turn / ^tr ornaments, [..]/1^roll(110) a rolled chord, {..}:N^fig(arch) a fioritura
RH = {
    # intro - the left hand alone, then the hook's head high and soft
    1: 'r/1', 2: 'r/1',
    3: 'A5/8 F#6/4 G6/8 A6/2',
    4: 'G6/8 F#6/8 E6/2 r/4',
    # A1 - the verse theme
    5: 'r/8 A4/8 D5/4. E5/8 F#5/8 E5/8',
    6: 'D5/4 B4/8 D5/8 E5/2',
    7: 'r/8 F#4/8 B4/4. C#5/8 D5/8 C#5/8',
    8: 'A4/2. r/4',
    9: 'r/8 A4/8 D5/4. E5/8 F#5/8 A5/8',
    10: 'B5/4. A5/8 G5/8 F#5/8 E5/4',
    11: 'G5/4 F#5/8 E5/8 D5/4 C#5/4',
    12: 'D5/4 E5/2 r/4',
    # A2 - the answer higher, F#m7 as a new turn, a full cadence
    13: 'r/8 A4/8 D5/4. E5/8 F#5/8 E5/8',
    14: 'D5/4 B4/8 D5/8 [B4 G5]/2',
    15: 'r/8 F#5/8 B5/4. A5/8 G5/8 F#5/8',
    16: '[C#5 E5]/2. r/4',
    17: 'r/8 B4/8 D5/8 G5/8 B5/4. A5/8',
    18: 'A5/4 F#5/8 E5/8 [A4 D5]/4. E5/8',
    19: 'F#5/4.^turn E5/8 [G4 E5]/4 C#5/4',
    20: 'D5/2. r/4',
    # B1 - the chorus hook: syncopated, a rising sixth into a held note
    21: 'B4/8 G5/4 A5/8 B5/2',
    22: 'A5/4. G5/8 F#5/8 E5/8 r/4',
    23: 'C#5/8 A5/4 B5/8 C#6/2',
    24: 'D6/4 C#6/8 B5/8 F#5/4 r/4',
    25: 'B4/8 G5/4 A5/8 [E5 B5]/2',
    26: 'A#5/4. B5/8 C#6/8 A#5/8 F#5/8 r/8',
    27: '[G5 B5]/4. A5/8 [D5 Bb5]/4 A5/4',
    28: 'G5/8 F#5/8 E5/2 r/4',
    # interlude - air over a D pedal
    29: 'r/8 A5/8 D6/4. E6/8 F#6/4',
    30: 'r/1',
    31: 'r/8 B5/8 E6/4. D6/8 B5/4',
    32: 'r/1',
    # A3 - the theme in sixths over a walking bass
    33: 'r/8 A4/8 [F#4 D5]/4. [G4 E5]/8 [A4 F#5]/8 [G4 E5]/8',
    34: '[F#4 D5]/4 B4/8 D5/8 [A4 F#5]/2',
    35: 'r/8 F#4/8 [G4 B4]/4. [A4 C#5]/8 [A4 D5]/8 [A4 C#5]/8',
    36: '[G4 B4]/2. r/4',
    37: 'r/8 A4/8 [F#4 D5]/4. [G4 E5]/8 [A4 F#5]/8 [D5 A5]/8',
    38: '[D5 B5]/4. [C#5 A5]/8 [B4 G#5]/8 [A4 F#5]/8 [G#4 E5]/4',
    39: '[C#5 A5]/4 [B4 G5]/8 [A4 F#5]/8 [G4 E5]/4 [E4 C#5]/4',
    40: '[F#4 D5]/2 r/8 A#4/8 C#5/8 E5/8',
    # build - B minor, the theme's cell sequenced up, Cmaj7 sliding into B7
    41: 'F#5/4 B5/4. C#6/8 D6/8 C#6/8',
    42: 'B5/4 A5/8 G5/8 F#5/2',
    43: 'r/8 G5/8 B5/4. C#6/8 D6/8 E6/8',
    44: 'F#6/4. E6/8 D6/8 C#6/8 A#5/4',
    45: 'r/8 G5/8 C6/8 E6/8 G6/4. F#6/8',
    46: 'E6/2 D#6/4 r/4',
    # climax - the chorus a step up (E major), in chords, the peak raised
    47: 'C#5/8 A5/4 B5/8 [E5 A5 C#6]/2',
    48: '[D#5 B5]/4. A5/8 G#5/8 F#5/8 [B4 D#5 F#5]/4',
    49: 'D#5/8 B5/4 C#6/8 [G#5 B5 D#6]/2',
    50: '[G#5 E6]/4 D#6/8 C#6/8 [E5 G#5]/4. B5/8',
    51: 'C#6/8 F#6/4 G#6/8 [C#6 E6 A6]/2',
    52: '[C6 G#6]/4. F#6/8 [B5 D#6]/4 [G#5 C6]/4',
    53: '[A5 C#6]/4. B5/8 [E5 C6]/4 B5/4',
    54: '[G#5 B5 E6]/2 [D5 G5 A5 D6]/2',
    # A4 - home, the theme an octave higher and soft, a deceptive cadence
    55: 'r/8 A5/8 D6/4. E6/8 F#6/8 E6/8',
    56: 'D6/4 B5/8 D6/8 E6/2',
    57: 'r/8 F#5/8 B5/4. C#6/8 D6/8 C#6/8',
    58: 'A5/2. r/4',
    59: 'r/8 A4/8 D5/4. E5/8 F#5/8 A5/8',
    60: 'B5/4. A5/8 [D5 Bb5]/4. A5/8',
    61: 'G5/4 F#5/8 E5/8 [G4 E5]/4 C#5/4',
    62: 'D5/2. r/4',
    # coda - the hook echoed, the theme's first cell, a rolled D(add9)
    63: 'B4/8 G5/4 A5/8 B5/2',
    64: 'r/4 Bb5/4 A5/2',
    65: 'A4/8 F#5/4 G5/8 A5/2',
    66: 'G5/4 F#5/8 E5/8 E5/4 r/4',
    67: 'r/8 A4/8 D5/4. E5/8 F#5/4',
    68: '[A4 D5 E5 F#5]/1^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two or three entries split the bar evenly). figure = a pianist.FIGURES name (flow rock
# color lilt open quart ring half up big sweep roll tenths walk10 still; 3/4: waltz waltz2 barcarolle waltz_held
# waltz_open waltz_arp waltz_step waltz_big) or your own token string over the chord's ladder (0 = the bass, 1 2 3 ...
# the chord tones above it, x = the colour tone, o = bass + its octave below, c = steps 1-3 together, R = rolled and
# held, a+b together, '-' holds): 8 tokens = 8ths in 4/4, 6 = 8ths in 3/4, 16 = 16ths.
# This piece's own figures (names for token strings, as the LH entries are split on spaces):
FIG = {
    'wave': '0 2 3 4 3 2 3 1',                          # the intro / verse hand: up to the 12th, a ripple back
    'surge': '0 1 2 3 4 3 2 1 0 1 2 3 4 5 4 3',         # the build: 16ths, widening
}

LH = {
    1: 'Dadd9:wave', 2: 'Gmaj7/D:wave', 3: 'Dadd9:wave', 4: 'Asus4:ring A:half',
    5: 'D:rock', 6: 'G/D:lilt', 7: 'Bm7:rock', 8: 'Gadd9:half',
    9: 'D/F#:flow', 10: 'G:lilt', 11: 'Em7:ring A7:ring', 12: 'Asus4:ring A:half',
    13: 'D:wave', 14: 'G/D:flow', 15: 'Bm7:wave', 16: 'F#m7:half',
    17: 'G:flow', 18: 'D/F#:color', 19: 'Em7:ring A7:ring', 20: 'D:half',
    21: 'G:color', 22: 'A:lilt', 23: 'F#m7:color', 24: 'Bm:ring',
    25: 'Em7:flow', 26: 'F#7:color', 27: 'G:ring Gm6:ring', 28: 'Asus4:ring A:half',
    29: 'Dadd9:open', 30: 'Gmaj7/D:quart', 31: 'Em7/D:open', 32: 'Asus4:roll',
    33: 'D:ring A/C#:ring', 34: 'Bm7:ring Bm7/A:ring', 35: 'Gmaj7:ring D/F#:ring', 36: 'Em7:half',
    37: 'D/F#:flow', 38: 'G:ring E7/G#:ring', 39: 'A:ring A7/G:ring', 40: 'D/F#:half F#7/A#:ring',
    41: 'Bm:flow', 42: 'Gmaj7:color', 43: 'Em7:flow', 44: 'F#7:surge',
    45: 'Cmaj7:surge', 46: 'B7sus4:ring B7:ring',
    47: 'A:big', 48: 'B:big', 49: 'G#m7:big', 50: 'C#m:big',
    51: 'F#m7:sweep', 52: 'G#7:sweep', 53: 'A:big Am6:big', 54: 'E/B:big A7sus4:roll',
    55: 'D:quart', 56: 'G/D:quart', 57: 'Bm7:quart', 58: 'Gadd9:half',
    59: 'D/F#:lilt', 60: 'G:ring Gm6:ring', 61: 'A7sus4:open A7:open', 62: 'Bm7:half',
    63: 'Gmaj7:open', 64: 'Gm6:open', 65: 'D/F#:lilt', 66: 'Em7:open A7sus4:open',
    67: 'Dadd9:open', 68: 'Dadd9:roll',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'pp'), (3, 0, 'p'), (4, 4, 'pp'),
       (5, 0, 'p'), (9, 0, 'p'), (10, 0, 'mp'), (12, 4, 'p'),
       (13, 0, 'p'), (15, 0, 'mp'), (17, 0, 'mp'), (18, 0, 'mf'), (20, 0, 'mp'),
       (21, 0, 'mf'), (22, 4, 'mp'), (23, 0, 'mf'), (24, 4, 'mp'), (25, 0, 'mf'), (26, 0, 'f'), (27, 4, 'mf'),
       (28, 4, 'mp'),
       (29, 0, 'pp'), (32, 0, 'pp'),
       (33, 0, 'p'), (37, 0, 'mp'), (38, 0, 'mf'), (40, 4, 'mp'),
       (41, 0, 'mp'), (43, 0, 'mp'), (44, 0, 'mf'), (46, 4, 'mp'),
       (47, 0, 'f'), (49, 0, 'f'), (51, 0, 'ff'), (52, 4, 'f'), (53, 0, 'f'), (54, 0, 'mf'), (54, 4, 'mp'),
       (55, 0, 'pp'), (59, 0, 'p'), (60, 0, 'mp'), (61, 4, 'p'), (62, 4, 'pp'),
       (63, 0, 'p'), (65, 0, 'p'), (66, 4, 'pp'), (68, 0, 'pp')]

PHRASES = [(1, 2), (3, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 40),
           (41, 44), (45, 46), (47, 50), (51, 54), (55, 58), (59, 62), (63, 66), (67, 68)]

# sections, in order, with bars - names from the endless vocabulary: intro, A1, A2, A3, A4, B1, B2, inter, build,
# climax, coda (the blind packets print these names)
SECTIONS = [('intro', 4), ('A1', 8), ('A2', 8), ('B1', 8), ('inter', 4), ('A3', 8), ('build', 6), ('climax', 8),
            ('A4', 8), ('coda', 6)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    for k in (8, 16, 58):                          # the theme's half-way breaths
        s.ritardando((bar(k) + 1.0, bar(k) + 4.0), to=0.9)
    for k in (12, 20, 28, 40):                     # cadences
        s.ritardando((bar(k) + 1.0, bar(k) + 4.0), to=0.82)
    s.ritardando((bar(4) + 1.0, bar(5)), to=0.85)  # the intro's breath
    s.ritardando((bar(32), bar(33)), to=0.82)      # the interlude's rolled chord
    s.ritardando((bar(46), bar(47)), to=0.85)      # the inhale before the climax
    s.ritardando((bar(53), bar(54) + 2.0), to=0.74, a_tempo=False)
    s.fermata(bar(54) + 2.5, hold=2.5)             # A7sus4 rings: the way home
    s.set_tempo(bar(55), 78)                       # the return: calmer
    s.ritardando((bar(62), bar(63)), to=0.82)      # the deceptive cadence
    s.set_tempo(bar(63), 74)
    s.ritardando((bar(66), bar(68)), to=0.75, a_tempo=False)
    s.fermata(bar(68) + 1.0, hold=3)
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
