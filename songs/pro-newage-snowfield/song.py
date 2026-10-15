"""Snow Without Footprints - an original new-age piece for solo grand piano in E major, 3/4.
Build: python -m agentsound build songs/pro-newage-snowfield

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

3/4, 60 BPM (the climax 64, the C-major part 56), 62 bars. THROUGH-COMPOSED: no section returns; everything grows
from one three-note cell (B4 E5 F#5: a 4th and a step). A still piece: the one climax is EARLY (~45 %) and only f -
a swell, not a peak in chords - and the music then sinks into a new key (C major, bVI) instead of coming back.

  intro   1-4    bells: single high notes over a held low E (the left hand barely there)
  A1      5-20   the cell and its answers in long notes (quarters, dotted halves), sus2 / maj7 colours, open-fifth
                 left hand
  B1      21-28  the cell inverted and in 8ths ("wind"), C#m - A - F#m7 - B7sus4, the rocking hand
  climax  29-34  a swell to E6 (once) over A - B - C#m, f; it falls away through G#m/B and A
  B2      35-54  new ground: C major (bVI), low and chorale-like (C4-C5) over a 10ths hand; the cell as a slow
                 bass-register answer; back to E through C7 (= the German sixth of E) -> B7sus4 -> B7
  coda    55-62  the bells again over E; the last chord Esus2 (no third): open, unresolved like the snow

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Snow Without Footprints', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#f2f5f8', '#7b8ea3'], 'title': 'SNOW WITHOUT FOOTPRINTS',
         'subtitle': 'solo piano - AgentSound', 'seed': 43}

G = _genre('new-age-piano')
FEEL = 'gentle'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'E major'
TIME = (3, 4)
METER = 3                  # quarter beats per bar
TEMPO = 60
SEED = 43

# ------------------------------------------------------------------------------------------------ right hand
RH = {
    # intro - bells over a held low E
    1: 'r/4 B5/2',
    2: 'r/4 F#5/2',
    3: 'r/4 G#5/4 E5/4',
    4: 'B4/2.',
    # A1 - the cell (B4 E5 F#5) and its answers
    5: 'B4/4 E5/4 F#5/4',
    6: 'G#5/2.',
    7: 'E5/4 A5/4 B5/4',
    8: 'C#6/2.',
    9: 'B5/4. G#5/8 E5/4',
    10: 'F#5/2 D#5/4',
    11: 'C#5/4 E5/4 B4/4',
    12: 'E5/2 r/4',
    13: 'B4/4 E5/4 F#5/4',
    14: 'B5/2.',
    15: 'C#6/4.^turn B5/8 G#5/4',
    16: 'A5/2 r/4',
    17: 'G#5/4 E5/4 C#5/4',
    18: 'B4/2 C#5/4',
    19: 'E5/2 D#5/4',
    20: 'E5/2 r/4',
    # B1 - the cell inverted, in 8ths: wind
    21: 'G#5/4 F#5/8 E5/8 B4/4',
    22: 'C#5/8 E5/8 A5/2',
    23: 'A5/4 G#5/8 F#5/8 C#5/4',
    24: 'E5/8 F#5/8 B5/2',
    25: 'D#6/4 C#6/8 B5/8 G#5/4',
    26: 'C#6/2 E5/4',
    27: 'F#5/8 G#5/8 A5/8 C#6/8 B5/4',
    28: 'A5/4. F#5/8 D#5/4',
    # climax - a swell to E6, f, and away
    29: 'C#5/8 E5/8 A5/8 C#6/8 D#6/4',
    30: 'E6/2 D#6/8 B5/8',
    31: 'C#6/4. G#5/8 E5/4',
    32: 'B5/4. A5/8 G#5/4',
    33: 'F#5/4. E5/8 C#5/4',
    34: 'D#5/2 r/4',
    # B2 - C major, low and chorale-like; home through C7 = the German sixth
    35: '[E4 G4]/4 [C4 C5]/4 [D4 B4]/4',
    36: '[C4 G4]/2. ',
    37: '[C4 E4 A4]/4. [B3 D4 G4]/8 [C4 F4]/4',
    38: '[A3 C4 E4]/2 r/4',
    39: 'G4/4 C5/4 D5/4',
    40: 'E5/2.',
    41: 'C5/4. A4/8 F4/4',
    42: 'G4/2 r/4',
    43: '[E4 G4 C5]/4 [D4 F4 B4]/4 [C4 E4 A4]/4',
    44: '[D4 F4 A4]/2.',
    45: 'r/4 F4/4 A4/4',
    46: 'G4/2 F4/4',
    47: 'E4/4 G4/4 C5/4',
    48: 'B4/2.',
    49: 'r/4 C5/4 E5/4',
    50: 'G5/4. F5/8 E5/4',
    51: 'D5/2 r/4',
    52: '[E5 Bb5]/2.',
    53: '[E5 A5]/2 [D#5 A5]/4',
    54: '[D#5 F#5]/2 r/4',
    # coda - the bells again; Esus2
    55: 'r/4 B5/2',
    56: 'r/4 G#5/4 F#5/4',
    57: 'r/4 E5/2',
    58: 'r/4 C#6/2',
    59: 'B5/4 G#5/2',
    60: 'r/4 F#5/2',
    61: 'r/4 E5/4 B4/4',
    62: '[E4 B4 F#5]/2.^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar into dotted quarters). 6 tokens = the 8ths of a 3/4 bar.
FIG = {
    'pedal': '0 - - - - -',          # one held bass
    'fifth': '0 - 1 - - -',          # bass and its 5th: the open hand
    'rock3': '0 2 3 2 1 2',          # the wind: a rocking 8ths hand
    'swell': '0 1 2 3 4 3',          # the climax: up through the bar
    'chorale': '0+3 - - - 1+4 -',    # B2: two 10ths
    'still3': '0+3 - - - - -',       # a 10th, held
}

LH = {
    1: 'E:pedal', 2: 'E:pedal', 3: 'E:pedal', 4: 'E:pedal',
    5: 'Eadd9:fifth', 6: 'E:fifth', 7: 'A/E:fifth', 8: 'A/E:fifth',
    9: 'C#m7:fifth', 10: 'B/D#:fifth', 11: 'Aadd9:fifth', 12: 'Bsus4:half B:half',
    13: 'E:fifth', 14: 'G#m7:fifth', 15: 'Amaj7:fifth', 16: 'F#m7:fifth',
    17: 'C#m:fifth', 18: 'Amaj7:fifth', 19: 'Bsus4:half B:half', 20: 'E:still3',
    21: 'C#m:rock3', 22: 'A:rock3', 23: 'F#m7:rock3', 24: 'B7sus4:rock3',
    25: 'G#m:rock3', 26: 'C#m:rock3', 27: 'F#m7:rock3', 28: 'B7:rock3',
    29: 'A:swell', 30: 'B:swell', 31: 'C#m:swell', 32: 'G#m/B:swell', 33: 'A:rock3', 34: 'B7/D#:still3',
    35: 'C:chorale', 36: 'C:still3', 37: 'Am:chorale', 38: 'Am:still3',
    39: 'G/B:chorale', 40: 'C:chorale', 41: 'F:chorale', 42: 'G:still3',
    43: 'C/E:chorale', 44: 'Dm7:still3', 45: 'F:chorale', 46: 'G7sus4:half G7:half',
    47: 'C:chorale', 48: 'G/B:still3', 49: 'Am:chorale', 50: 'C/G:chorale',
    51: 'G7:still3', 52: 'C7:still3', 53: 'B7sus4:half B7:half', 54: 'B7:still3',
    55: 'E:pedal', 56: 'E:pedal', 57: 'A/E:pedal', 58: 'A/E:pedal', 59: 'E:pedal', 60: 'Bsus4/E:pedal',
    61: 'E:pedal', 62: 'Esus2:still3',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'p'), (2, 2, 'mp'), (3, 2, 'p'), (4, 0, 'p'),
       (5, 0, 'mp'), (9, 3, 'mp'), (12, 0, 'p'), (13, 0, 'mp'), (14, 0, 'mf'), (16, 0, 'mp'), (19, 0, 'p'),
       (20, 0, 'p'),
       (21, 0, 'mp'), (24, 2, 'mf'), (26, 2, 'mp'), (27, 0, 'mf'), (28, 3, 'mp'),
       (29, 0, 'mf'), (30, 0, 'f'), (30, 4, 'mf'), (32, 3, 'mp'), (34, 0, 'p'),
       (35, 0, 'p'), (37, 0, 'mp'), (38, 0, 'p'), (40, 0, 'mp'), (42, 0, 'p'), (43, 0, 'mp'), (44, 0, 'p'),
       (47, 0, 'mp'), (48, 0, 'p'), (49, 0, 'mp'), (50, 0, 'mf'), (51, 0, 'mp'), (52, 0, 'mf'), (53, 3, 'mp'),
       (54, 0, 'p'),
       (55, 0, 'p'), (56, 2, 'mp'), (57, 2, 'p'), (58, 2, 'mp'), (59, 3, 'p'), (61, 0, 'pp'), (62, 0, 'pp')]

PHRASES = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 31), (32, 34), (35, 38), (39, 42),
           (43, 46), (47, 51), (52, 54), (55, 58), (59, 62)]

SECTIONS = [('intro', 4), ('A1', 16), ('B1', 8), ('climax', 6), ('B2', 20), ('coda', 8)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'] * 1.2, seed='bar')
    s.ritardando((bar(4), bar(5)), to=0.8)
    for k in (8, 16, 24, 40, 48):                       # the half-way breaths
        s.ritardando((bar(k) + 1.0, bar(k + 1)), to=0.88)
    for k in (12, 20, 28, 38, 42, 46):                  # cadences
        s.ritardando((bar(k) + 0.5, bar(k + 1)), to=0.8)
    s.set_tempo(bar(21), 62)
    s.set_tempo(bar(29), 64)                             # the swell moves a little
    s.ritardando((bar(32), bar(35)), to=0.75, a_tempo=False)
    s.fermata(bar(34) + 2.0, hold=1.5)
    s.set_tempo(bar(35), 56)                             # the new key, lower and slower
    s.ritardando((bar(51), bar(52)), to=0.85)
    s.ritardando((bar(53), bar(55)), to=0.75, a_tempo=False)
    s.fermata(bar(54) + 2.0, hold=2.0)                  # B7 waits before home
    s.set_tempo(bar(55), 58)
    s.ritardando((bar(60), bar(62)), to=0.72, a_tempo=False)
    s.fermata(bar(62) + 1.0, hold=3)
    score.lilt(s, (0.0, bar(len(RH) + 1)), beats={2: 0.05}, jitter=0.03, seed=SEED)


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
