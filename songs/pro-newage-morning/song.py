"""Variations on a Morning - an original new-age piece for solo grand piano in G major (Lydian colour), 4/4.
Build: python -m agentsound build songs/pro-newage-morning

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

4/4, 76 BPM (the minor variation 66, the climax 82, the hymn 70), 58 bars. THEME AND VARIATIONS, no intro: the theme
is heard at once, plain. The theme: D5 G5 B5 (a 4th and a 3rd up), the Lydian A/G (C#6 - the raised 4th of G) and a
fall through Em7 to Cmaj7; the answer climbs to D6 and cadences.

  A1      1-8    THEME, mp, a sparse quarter-note hand; no intro
  A2      9-16   VAR 1 - diminution: the theme's notes on the strong beats, 8ths between, the hand flowing
  B1      17-24  VAR 2 - G minor, slower: the theme in the minor, long notes in the middle register over a hand that
                 holds 10ths; the Lydian C#6 becomes D6 over Ebmaj7; it ends on D7 (half cadence)
  A3      25-32  VAR 3 - the theme in triplets (a 12/8 feel inside 4/4), light, p, the hand in quarter notes
  build   33-36  VAR 4a - the head D-G-B sequenced upward (G - A/G - Bm7 - C), the hand widening
  climax  37-44  VAR 4b - a NEW line in three-voice chords that peaks once on A6 over the Lydian A/G and then falls
                 by step for six bars (G6 F#6 E6 D6 C#6 ... G5), the Lydian C# kept on the way down; f -> ff -> p
  A4      45-52  VAR 5 - the hymn: the theme augmented and reharmonised (G/D, Em9, Cmaj7#11), pp, a deceptive close
                 on Em
  coda    53-58  the opening leap D-G twice, softer; it ends on Gmaj7#11 - the Lydian colour, not a plain triad

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Variations on a Morning', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#fbf1d9', '#e0a458'], 'title': 'VARIATIONS ON A MORNING',
         'subtitle': 'solo piano - AgentSound', 'seed': 29}

G = _genre('new-age-piano')
FEEL = 'flowing'           # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'G major'
TIME = (4, 4)
METER = 4                  # quarter beats per bar
TEMPO = 76
SEED = 29

# ------------------------------------------------------------------------------------------------ right hand
# one entry per bar, notation (agentsound.notation, unit 1/8): {..}/4 = a triplet on one beat
RH = {
    # A1 - THEME (no intro)
    1: 'D5/4. G5/8 B5/4 A5/8 G5/8',
    2: 'C#6/2 B5/4 A5/4',
    3: 'G5/4. E5/8 B4/4 D5/4',
    4: 'E5/2. r/4',
    5: 'D5/4. G5/8 B5/4 D6/8 C6/8',
    6: 'B5/4.^turn A5/8 G5/4 E5/4',
    7: 'C5/4 E5/8 A5/8 G5/4. F#5/8',
    8: 'G5/2 r/4 r/8 D5/8',
    # A2 - VAR 1: diminution
    9: 'D5/8 B4/8 D5/8 G5/8 B5/4 A5/8 G5/8',
    10: 'C#6/4 E6/8 C#6/8 B5/8 A5/8 E5/4',
    11: 'G5/8 F#5/8 E5/8 B4/8 D5/8 E5/8 G5/8 B5/8',
    12: 'B5/8 G5/8 E5/4 r/2',
    13: 'r/8 D5/8 G5/8 B5/8 D6/4 C6/8 B5/8',
    14: 'B5/8 C6/8 A5/8 G5/8 E5/4 G5/8 E5/8',
    15: 'C5/8 E5/8 A5/8 C6/8 B5/8 G5/8 A5/8 F#5/8',
    16: 'G5/4 D5/8 B4/8 G4/4 r/4',
    # B1 - VAR 2: G minor, slower, long notes in the middle register
    17: 'D5/4. G5/8 Bb5/2',
    18: 'D6/2 Bb5/4 G5/4',
    19: 'Eb5/4. C5/8 G4/4 Bb4/4',
    20: 'C5/2 [A4 C5]/4 r/4',
    21: 'D5/4. G5/8 Bb5/4 D6/4',
    22: 'Eb6/4. D6/8 Bb5/4 G5/4',
    23: 'C6/4 G5/8 Eb5/8 F5/4 A5/4',
    24: 'Bb5/2 [F#5 A5]/4 r/4',
    # A3 - VAR 3: the theme in triplets
    25: '{D5 G5 B5}/4 {D6 B5 G5}/4 B5/4 {A5 G5 D5}/4',
    26: '{C#6 E6 C#6}/4 B5/4 {A5 E5 A5}/4 r/4',
    27: '{G5 B5 G5}/4 E5/4 {B4 D5 E5}/4 D5/4',
    28: '{E5 G5 B5}/4 E6/4 r/2',
    29: '{D5 G5 B5}/4 {D6 E6 D6}/4 C6/4 {B5 C6 D6}/4',
    30: '{B5 A5 G5}/4 A5/4 {G5 E5 G5}/4 r/4',
    31: '{C5 E5 A5}/4 C6/4 {B5 A5 G5}/4 F#5/4',
    32: 'G5/2 r/4 D5/4',
    # build - VAR 4a: the head sequenced up
    33: 'D5/4. G5/8 B5/2',
    34: 'E5/4. A5/8 C#6/2',
    35: 'F#5/4. B5/8 D6/4 E6/8 F#6/8',
    36: '[C6 G6]/4. [B5 F#6]/8 [A5 E6]/4 [F#5 D6]/8 [A5 F#6]/8',
    # climax - VAR 4b: a new line falling from A6 in octaves, the head inside
    37: '[B5 D6 G6]/4. [A5 D6 F#6]/8 [G5 B5 E6]/4 [G5 C#6 E6]/4',
    38: '[C#6 E6 A6]/2. [B5 E6 G6]/4',
    39: '[B5 E6 F#6]/4. [G5 B5 E6]/8 [B5 D6]/2',
    40: '[F#5 A5 C#6]/4. [F#5 A5 D6]/8 [E5 A5 C#6]/4 [D5 F#5 A5]/4',
    41: '[D5 G5 B5]/2 [C#5 A5]/4 [B4 G5]/4',
    42: '[C5 E5 G5]/4. [B4 F#5]/8 [A4 E5]/2',
    43: '[A4 C5 E5]/4 [C5 G5]/4 [B4 D5 G5]/4 [A4 C5 F#5]/4',
    44: '[B4 D5 G5]/2. r/4',
    # A4 - VAR 5: the hymn, augmented and reharmonised
    45: 'D5/2 G5/2',
    46: 'B5/2. A5/4',
    47: 'C#6/2 B5/4 A5/4',
    48: 'G5/2 E5/4 r/4',
    49: 'D5/4. G5/8 B5/4 D6/4',
    50: 'C6/4.^mord B5/8 A5/4 F#5/4',
    51: 'G5/4 E5/8 C5/8 D5/4. B4/8',
    52: 'B4/2. r/4',
    # coda - the leap twice, softer; Gmaj7#11
    53: 'r/2 D5/4. G5/8',
    54: 'B5/2 A5/4 r/4',
    55: 'r/2 D5/4. G5/8',
    56: 'A5/2. r/4',
    57: 'C#6/2 B5/4 F#5/4',
    58: '[G4 B4 C#5 F#5]/1^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar). 8 tokens = 8ths, 12 = triplet 8ths, 16 = 16ths.
FIG = {
    'beats': '0 - 2 - 3 - 2 -',       # quarter notes: the theme's plain hand
    'trip': '0 2 3 1 3 2 0 2 3 1 3 2',  # triplet 8ths: VAR 3's hand
    'chorale': '0+3 - - - 1+4 - - -',   # VAR 2: two 10ths, the hand rests
}

LH = {
    1: 'G:open', 2: 'A/G:open', 3: 'Em7:beats', 4: 'Cmaj7:half',
    5: 'G/B:beats', 6: 'Cmaj7:open', 7: 'Am7:ring D7sus4:ring', 8: 'G:half',
    9: 'G:flow', 10: 'A/G:flow', 11: 'Em7:color', 12: 'Cmaj7:ring',
    13: 'G/B:flow', 14: 'Cmaj7:color', 15: 'Am7:half D7sus4:half', 16: 'G:half',
    17: 'Gm:still', 18: 'Ebmaj7:chorale', 19: 'Cm7:chorale', 20: 'D7sus4:ring D7:ring',
    21: 'Gm/Bb:chorale', 22: 'Ebmaj7:tenths', 23: 'Cm7:ring F7:ring', 24: 'Bb:ring D7/A:ring',
    25: 'G:trip', 26: 'A/G:trip', 27: 'Em7:trip', 28: 'Cmaj7:half',
    29: 'G/B:trip', 30: 'Cmaj7:trip', 31: 'Am7:trip D7:ring', 32: 'G:half',
    33: 'G:up', 34: 'A/G:up', 35: 'Bm7:up', 36: 'C:ring D/C:ring',
    37: 'G/B:big', 38: 'A/G:sweep', 39: 'Em7:big', 40: 'D/F#:big',
    41: 'G:sweep', 42: 'Cmaj7:big', 43: 'Am7:ring D7sus4:ring', 44: 'G:roll',
    45: 'G/D:open', 46: 'Em9:open', 47: 'A/C#:open', 48: 'Cmaj7#11:half',
    49: 'G/B:quart', 50: 'Am7:quart', 51: 'Cmaj7:ring D7sus4:ring', 52: 'Em:half',
    53: 'Cmaj7:still', 54: 'G/B:open', 55: 'Am7:still', 56: 'D7sus4:open', 57: 'A/G:open',
    58: 'Gmaj7#11:roll',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'mp'), (4, 0, 'p'), (5, 0, 'mp'), (8, 0, 'p'),
       (9, 0, 'p'), (10, 4, 'mp'), (12, 0, 'p'), (13, 0, 'mp'), (16, 0, 'p'),
       (17, 0, 'p'), (20, 0, 'pp'), (21, 0, 'p'), (22, 4, 'mp'), (24, 0, 'p'),
       (25, 0, 'p'), (28, 0, 'p'), (29, 0, 'p'), (30, 4, 'mp'), (32, 0, 'pp'),
       (33, 0, 'mp'), (34, 0, 'mf'), (35, 0, 'mf'), (35, 4, 'f'), (36, 4, 'mf'),
       (37, 0, 'f'), (38, 0, 'ff'), (38, 6, 'f'), (39, 4, 'f'), (40, 4, 'mf'), (41, 4, 'mf'),
       (42, 4, 'mp'), (43, 4, 'p'), (44, 0, 'p'),
       (45, 0, 'pp'), (46, 0, 'p'), (47, 0, 'p'), (48, 4, 'pp'), (49, 0, 'pp'), (49, 6, 'p'), (50, 4, 'p'),
       (51, 4, 'pp'),
       (53, 4, 'p'), (54, 4, 'pp'), (55, 4, 'pp'), (57, 0, 'p'), (57, 4, 'pp'), (58, 0, 'pp')]

PHRASES = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 40), (41, 44),
           (45, 48), (49, 52), (53, 56), (57, 58)]

SECTIONS = [('A1', 8), ('A2', 8), ('B1', 8), ('A3', 8), ('build', 4), ('climax', 8), ('A4', 8), ('coda', 6)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    for k in (4, 12, 28):                               # the half-way breaths
        s.ritardando((bar(k) + 2.0, bar(k + 1)), to=0.88)
    s.ritardando((bar(8) + 1.0, bar(9)), to=0.82)       # the theme's cadence
    s.ritardando((bar(16), bar(17)), to=0.78, a_tempo=False)
    s.set_tempo(bar(17), 66)                             # VAR 2: the minor, slower
    s.ritardando((bar(20) + 1.0, bar(21)), to=0.85)
    s.ritardando((bar(24), bar(25)), to=0.8, a_tempo=False)
    s.fermata(bar(24) + 2.5, hold=1.5)                  # the D7 holds before the light comes back
    s.set_tempo(bar(25), 76)
    s.ritardando((bar(32) + 2.0, bar(33)), to=0.9)
    s.set_tempo(bar(33), 80)
    s.ritardando((bar(36) + 2.0, bar(37)), to=0.86)     # the inhale
    s.set_tempo(bar(37), 82)
    s.ritardando((bar(43), bar(44) + 2.0), to=0.7, a_tempo=False)
    s.fermata(bar(44) + 2.0, hold=2.0)
    s.set_tempo(bar(45), 70)                             # the hymn
    s.ritardando((bar(48) + 2.0, bar(49)), to=0.85)
    s.ritardando((bar(51) + 2.0, bar(52) + 3.0), to=0.75, a_tempo=False)
    s.set_tempo(bar(53), 66)
    s.ritardando((bar(56), bar(57)), to=0.85)
    s.ritardando((bar(57), bar(58)), to=0.75, a_tempo=False)
    s.fermata(bar(58) + 1.0, hold=3)
    score.lilt(s, (0.0, bar(len(RH) + 1)), beats={3: 0.03}, jitter=0.03, seed=SEED)


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
