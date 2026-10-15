"""A Lamp in the Far Window - an original new-age piece for solo grand piano in B minor, 3/4.
Build: python -m agentsound build songs/pro-newage-longing

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

3/4, 72 BPM (B part 76, the climax 78, the coda 64), 78 bars. The theme: a rising SIXTH F#4 -> D5 that falls back by
step over a descending bass (B - A - G), the second phrase reaching G5 and B5. The climax comes LATE (~86 %), in two
waves, the second one holding F#6 for a whole bar over the dominant pedal; then the theme only in fragments.

  intro   1-4    the theme's head ALONE in the right hand (no left hand), as if remembered; then one held Bm(add9)
  A1      5-20   the theme, p, 4 x 4 bars; the first sentence ends on F#7, the second on the tonic
  A2      21-36  the theme varied: the 6th filled in, the second half in D major (the leap A4 -> F#5), a deceptive
                 F#7 -> Gmaj7 before the half cadence; the hand flows
  B1      37-52  a new idea from the Neapolitan region (C major in B minor: E5 G5 C6), sequenced a step up, then a
                 falling bass C - B - Bb - A to the build; the open waltz hand
  build   53-60  the 6th leap sequenced upward (F#4-D5, A4-F#5, B4-G5, D5-B5) over a rising bass
  climax  61-72  two waves: the first to D6 and back, the second to F#6 held a whole bar over F#7sus4 -> F#7(b9),
                 then a falling arpeggio, f -> ff -> p
  coda    73-78  fragments: the leap twice without its answer, the line stopping on C#5, the 9th of the final Bm(add9)

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'A Lamp in the Far Window', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#e9dcc9', '#4a3f5c'], 'title': 'A LAMP IN THE FAR WINDOW',
         'subtitle': 'solo piano - AgentSound', 'seed': 31}

G = _genre('new-age-piano')
FEEL = 'gentle'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'B minor'
TIME = (3, 4)
METER = 3                  # quarter beats per bar
TEMPO = 72
SEED = 31

# ------------------------------------------------------------------------------------------------ right hand
# one entry per bar, notation (agentsound.notation, unit 1/8): 6 eighths per bar
RH = {
    # intro - the head alone, then one held chord
    1: 'F#4/4 D5/2',
    2: 'C#5/4. B4/8 A4/4',
    3: 'B4/2.',
    4: 'r/2.',
    # A1 - the theme
    5: 'F#4/4 D5/2',
    6: 'C#5/4. B4/8 A4/4',
    7: 'B4/4 D5/4 F#5/4',
    8: 'G5/2 r/4',
    9: 'B5/4. A5/8 G5/4',
    10: 'E5/4 G5/4 C#5/4',
    11: 'F#5/4. E5/8 D5/4',
    12: 'B4/4. A#4/4.',
    13: 'F#4/4 D5/4 F#5/4',
    14: 'B5/4. A5/8 F#5/4',
    15: 'G5/4 F#5/8 E5/8 D5/4',
    16: 'E5/2 r/4',
    17: 'G5/4. F#5/8 E5/4',
    18: 'C#5/4 E5/4 A#4/4',
    19: 'B4/2 D5/8 C#5/8',
    20: 'B4/2 r/4',
    # A2 - the 6th filled in; the second half in D major
    21: 'r/4 F#4/8 B4/8 D5/4',
    22: 'E5/4. D5/8 C#5/4',
    23: 'D5/4 F#5/4 B5/4',
    24: 'A5/4.^turn G5/8 E5/4',
    25: 'F#5/2 A5/4',
    26: 'D6/4. C#6/8 B5/4',
    27: 'G5/4 B5/4 E5/4',
    28: 'D5/4. C#5/4 r/8',
    29: 'A4/4 F#5/2',
    30: 'E5/4. D5/8 C#5/4',
    31: 'D5/4 F#5/4 A5/4',
    32: 'B5/2 r/4',
    33: 'B5/4. G5/8 E5/4',
    34: 'A#4/4 C#5/4 E5/4',
    35: 'D5/4. C#5/8 B4/4',
    36: 'B4/4. A#4/4 r/8',
    # B1 - from the Neapolitan region: a new idea, sequenced up
    37: 'E5/4. G5/8 C6/4',
    38: 'B5/4 D5/4 G5/4',
    39: 'C6/4. B5/8 A5/4',
    40: 'G5/4. F#5/4 r/8',
    41: 'G5/4. B5/8 E6/4',
    42: 'D6/4 F#5/4 B5/4',
    43: 'E6/4. D6/8 C6/4',
    44: 'B5/4. A#5/4 r/8',
    45: 'G5/4 E5/8 G5/8 C6/4',
    46: 'B5/4. G5/8 D5/4',
    47: 'D5/4 F5/4 Bb5/4',
    48: 'A5/2 r/4',
    49: 'C#5/4 E5/4 A5/4',
    50: 'G5/4. F#5/8 E5/4',
    51: 'D5/4 E5/8 F#5/8 G5/4',
    52: 'F#5/2 r/4',
    # build - the 6th leap sequenced up over a rising bass
    53: 'F#4/4 D5/2',
    54: 'C#5/4 B4/4 r/4',
    55: 'A4/4 F#5/2',
    56: 'E5/4 D5/4 r/4',
    57: 'B4/4 G5/2',
    58: 'E5/4 F#5/8 G5/8 B5/4',
    59: 'D5/4 B5/2',
    60: 'A5/4 G5/8 A5/8 [D5 C#6]/4',
    # climax - two waves; the second holds F#6 over the dominant
    61: '[F#5 D6]/2 [E5 C#6]/4',
    62: '[D5 B5]/4. [C#5 A5]/8 [B4 G5]/4',
    63: '[D5 A5]/4 [F#5 B5]/4 [G5 C#6]/4',
    64: '[F#5 A5 D6]/2 r/4',
    65: '[G5 B5 E6]/4. [F#5 D6]/8 [E5 G5 C#6]/4',
    66: '[D5 F#5 B5]/4 [G5 D6]/4 [B5 E6]/4',
    67: '[B5 F#6]/2.',
    68: '[A#5 C#6 E6]/2 [G5 C#6]/4',
    69: '[F#5 B5 D6]/4. [D5 F#5 B5]/8 [E5 G5 B5]/4',
    70: '[C#5 E5 A#5]/4. [B4 F#5]/8 [E5 G5]/4',
    71: '[D5 F#5]/2 r/4',
    72: 'C#5/4 B4/8 C#5/8 [B4 E5]/4',
    # coda - fragments
    73: 'r/4 F#4/4 D5/4',
    74: 'r/2 B4/4',
    75: 'r/4 F#4/4 D5/4',
    76: 'C#5/2.',
    77: 'r/4 A4/4 B4/4',
    78: '[F#4 B4 C#5]/2.^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar into dotted quarters). 6 tokens = the 8ths of a 3/4 bar.
FIG = {
    'sway': '0 - 2 3 1 -',        # the theme's hand: bass, a rocking reply, the bar breathes
    'reach': '0 2 4 2 3 -',       # the A2 hand: reaching to the 12th
    'lift': '0 1 2 3 4 5',        # the build: up through the bar
    'held': '0+3 - - - - -',      # a 10th, held
    'deep': 'o - 2 3 4 3',        # the climax: the bass in octaves, the arpeggio
}

LH = {
    3: 'Bmadd9:held',
    5: 'Bm:sway', 6: 'F#m/A:sway', 7: 'Gmaj7:sway', 8: 'Gmaj7:waltz_held',
    9: 'Em7:sway', 10: 'A7:sway', 11: 'Dmaj7:sway', 12: 'F#7sus4:half F#7:half',
    13: 'Bm:sway', 14: 'Bm/A:sway', 15: 'Gmaj7:sway', 16: 'C#m7b5:waltz_held',
    17: 'Em7:sway', 18: 'F#7:sway', 19: 'Bm:sway', 20: 'Bm:held',
    21: 'Bm:reach', 22: 'F#m7/A:reach', 23: 'Gmaj7:reach', 24: 'A7:reach',
    25: 'Dmaj7:reach', 26: 'Bm7:reach', 27: 'Em7:reach', 28: 'A7sus4:half A7:half',
    29: 'Dmaj7:waltz_arp', 30: 'A/C#:waltz_arp', 31: 'Bm7:waltz_arp', 32: 'Gmaj7:waltz_held',
    33: 'Em7:reach', 34: 'F#7:reach', 35: 'Gmaj7:reach', 36: 'F#7sus4:half F#7:half',
    37: 'C:waltz_open', 38: 'G/B:waltz_open', 39: 'Am7:waltz_open', 40: 'D7sus4:half D7:half',
    41: 'Em7:waltz_open', 42: 'Bm/D:waltz_open', 43: 'Cmaj7:waltz_open', 44: 'F#7sus4:half F#7:half',
    45: 'C:waltz_step', 46: 'G/B:waltz_step', 47: 'Bb:waltz_step', 48: 'F/A:waltz_held',
    49: 'A:waltz_step', 50: 'Em/G:waltz_step', 51: 'Bm/F#:waltz_step', 52: 'F#7:waltz_held',
    53: 'Bm:lift', 54: 'F#m/A:waltz_held', 55: 'D/A:lift', 56: 'Bm7/A:waltz_held',
    57: 'Em/G:lift', 58: 'Em7/G:lift', 59: 'Gmaj7:lift', 60: 'A7sus4:half A7:half',
    61: 'Bm:deep', 62: 'Gmaj7:deep', 63: 'Em7:deep', 64: 'D/F#:waltz_held',
    65: 'Em7:deep', 66: 'Gmaj7:deep', 67: 'F#7sus4:deep', 68: 'F#7b9:deep',
    69: 'Bm:waltz_arp', 70: 'F#7/A#:waltz_arp', 71: 'Bm/D:waltz_held', 72: 'Em7:half F#7sus4:half',
    73: 'Gmaj7:held', 74: 'Gmaj7:held', 75: 'Em7:held', 76: 'F#7sus4:held', 77: 'Gmaj7:held',
    78: 'Bmadd9:held',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'p'), (2, 0, 'mp'), (3, 0, 'p'), (4, 0, 'pp'),
       (5, 0, 'p'), (9, 0, 'mp'), (12, 0, 'p'), (13, 0, 'p'), (17, 0, 'mp'), (20, 0, 'pp'),
       (21, 0, 'p'), (25, 0, 'mp'), (28, 3, 'p'), (29, 0, 'mp'), (33, 0, 'mp'), (36, 0, 'p'),
       (37, 0, 'mp'), (40, 3, 'mp'), (41, 0, 'mp'), (43, 0, 'mf'), (44, 3, 'mp'), (45, 0, 'p'), (48, 3, 'p'),
       (49, 0, 'p'), (52, 3, 'p'),
       (53, 0, 'p'), (55, 0, 'mp'), (57, 0, 'mp'), (59, 0, 'mf'), (60, 3, 'f'),
       (61, 0, 'f'), (62, 3, 'mf'), (63, 0, 'mf'), (64, 0, 'mp'), (65, 0, 'mf'), (66, 0, 'f'), (67, 0, 'ff'),
       (68, 3, 'f'), (69, 0, 'mf'), (70, 0, 'mp'), (71, 0, 'p'), (72, 3, 'pp'),
       (73, 0, 'pp'), (74, 4, 'p'), (75, 0, 'pp'), (76, 0, 'p'), (77, 0, 'pp'), (78, 0, 'pp')]

PHRASES = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 40), (41, 44),
           (45, 48), (49, 52), (53, 56), (57, 60), (61, 64), (65, 68), (69, 72), (73, 74), (75, 78)]

SECTIONS = [('intro', 4), ('A1', 16), ('A2', 16), ('B1', 16), ('build', 8), ('climax', 12), ('coda', 6)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    s.ritardando((bar(2), bar(3) + 1.0), to=0.8, a_tempo=False)
    s.fermata(bar(3) + 1.0, hold=2.0)                   # the remembered head rings
    s.set_tempo(bar(5), 72)
    for k in (8, 16, 24, 32, 40, 48):                   # the half-way breaths
        s.ritardando((bar(k) + 1.0, bar(k + 1)), to=0.88)
    for k in (12, 20, 28, 36, 44, 52):                  # cadences
        s.ritardando((bar(k) + 0.5, bar(k + 1)), to=0.8)
    s.set_tempo(bar(37), 76)                             # B: a little more urgency
    s.set_tempo(bar(53), 76)
    s.ritardando((bar(60) + 1.0, bar(61)), to=0.85)     # the inhale
    s.set_tempo(bar(61), 78)
    s.ritardando((bar(64), bar(65)), to=0.85)
    s.ritardando((bar(66) + 1.0, bar(68) + 1.5), to=0.72, a_tempo=False)
    s.fermata(bar(67) + 1.5, hold=1.5)                  # the held F#6
    s.set_tempo(bar(69), 70)
    s.ritardando((bar(71), bar(73)), to=0.75, a_tempo=False)
    s.set_tempo(bar(73), 64)
    s.ritardando((bar(76), bar(77)), to=0.8)
    s.fermata(bar(76) + 2.0, hold=1.5)                  # the unanswered C#
    s.ritardando((bar(77), bar(78)), to=0.75, a_tempo=False)
    s.fermata(bar(78) + 1.0, hold=3)
    score.lilt(s, (0.0, bar(len(RH) + 1)), beats={2: 0.04}, jitter=0.03, seed=SEED)


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
