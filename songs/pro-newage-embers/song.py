"""Embers, Late - an original new-age passacaglia for solo grand piano in C minor, 4/4.
Build: python -m agentsound build songs/pro-newage-embers

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

4/4, 58 BPM (the major variation 60, the climax 62, the last 54), 56 bars. A PASSACAGLIA: an 8-bar ground in the
bass - C Eb F G Ab F D G (rising, then falling to the dominant; not the lament tetrachord) - heard seven times, every
time harmonised and textured anew while the melody above it is new each time. No intro: the first variation starts
with the ground and a low melody together. The climax is late (~80 %) on the ground's A-flat (Abmaj7#11, the top
Ab6 once); the seventh statement breaks off half-way, on G.

  A1      1-8    VAR 1 - Cm Eb Fm Gm Ab Fm7 Dm7b5 G7: a low melody (G4-D5) in long notes over held 10ths, p
  A2      9-16   VAR 2 - Cm(add9) Cm/Eb Fm7 Cm/G Abmaj7 F7 (the Dorian A natural) Bb/D Gsus4: the melody an octave
                 up in 8ths, a lilting hand
  B1      17-24  VAR 3 - C MAJOR over the same bass (C Ebmaj7 F G Abmaj7 Fm6 Dm7 G7): a consolation, the flowing hand
  A3      25-32  VAR 4 - minor again, syncopated (every bar enters on the & of 1), Eb6 / Fm9 colours, two voices at
                 the cadence; a syncopated hand
  build   33-40  VAR 5 - continuous 8ths climbing through the chords (CmMaj7 Ebmaj7 Fm6 ... G7b9), the hand in 16ths
  climax  41-48  VAR 6 - the ground in bass octaves; three-voice chords, the peak Ab6 over Abmaj7#11 (bar 45), then a
                 falling line over Fm9 - Bdim7/D - G7
  A4      49-52  VAR 7 - pp, only half the ground: it stops on G (a half cadence) and does not go on
  coda    53-56  Abmaj7 - Fm7 - Gsus4 - G, and a rolled C minor with the 3rd (Eb5) on top

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Embers, Late', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#e8d2c0', '#5c2a22'], 'title': 'EMBERS, LATE',
         'subtitle': 'solo piano - AgentSound', 'seed': 53}

G = _genre('new-age-piano')
FEEL = 'gentle'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'C minor'
TIME = (4, 4)
METER = 4                  # quarter beats per bar
TEMPO = 58
SEED = 53

# ------------------------------------------------------------------------------------------------ right hand
RH = {
    # A1 - VAR 1: low, long notes
    1: 'G4/2. C5/4',
    2: 'Bb4/2 G4/4 Eb4/4',
    3: 'Ab4/2. C5/4',
    4: 'D5/2 Bb4/4 r/4',
    5: 'C5/2. Eb5/4',
    6: 'F5/2 Eb5/4 C5/4',
    7: 'D5/4. C5/8 Ab4/2',
    8: 'B4/2 r/2',
    # A2 - VAR 2: an octave up, 8ths
    9: 'G5/8 F5/8 Eb5/8 D5/8 Eb5/4 C5/4',
    10: 'Bb5/4. G5/8 Eb5/4 C5/4',
    11: 'C5/8 F5/8 Ab5/8 C6/8 Bb5/4 Ab5/4',
    12: 'G5/2 Eb5/4 r/4',
    13: 'C6/4.^turn Bb5/8 G5/4 Eb5/4',
    14: 'A5/4 C6/8 A5/8 F5/4 Eb5/4',
    15: 'D5/8 F5/8 Bb5/8 D6/8 C6/4 F5/4',
    16: 'C6/2 B5/4 r/4',
    # B1 - VAR 3: C major over the same bass
    17: 'E5/4. G5/8 C6/2',
    18: 'Bb5/4 G5/4 D6/2',
    19: 'C6/4. A5/8 F5/4 A5/4',
    20: 'B5/2 D6/4 r/4',
    21: 'C6/4 Eb6/4 G5/2',
    22: 'Ab5/4. F5/8 D5/2',
    23: 'F5/4 A5/4 C6/4 A5/4',
    24: 'B5/2 r/2',
    # A3 - VAR 4: syncopated, minor again
    25: 'r/8 G5/8 C6/4. Bb5/8 G5/4',
    26: 'r/8 Bb5/8 Eb6/4. C6/8 G5/4',
    27: 'r/8 C6/8 F6/4. Eb6/8 Ab5/4',
    28: 'D6/4. C6/8 B5/2',
    29: 'r/8 Ab5/8 C6/4. Bb5/8 G5/4',
    30: 'r/8 C6/8 Eb6/4. C6/8 Ab5/4',
    31: 'D6/4. C6/8 Ab5/4 F5/4',
    32: '[F5 B5]/2 [D5 G5]/4 r/4',
    # build - VAR 5: climbing 8ths
    33: 'Eb5/8 G5/8 B5/8 D6/8 Eb6/4 D6/8 C6/8',
    34: 'G5/8 Bb5/8 Eb6/8 D6/8 Bb5/4 G5/4',
    35: 'Ab5/8 C6/8 F6/8 D6/8 C6/4 Ab5/4',
    36: 'B5/8 D6/8 F6/8 D6/8 B5/4 G5/4',
    37: 'Ab5/8 C6/8 Eb6/8 F6/8 Eb6/4 C6/4',
    38: 'G5/8 Ab5/8 C6/8 F6/8 Eb6/4 C6/4',
    39: 'F5/8 Ab5/8 C6/8 D6/8 F6/4 D6/4',
    40: '[B5 D6 F6]/2 [G5 B5 D6]/4 r/4',
    # climax - VAR 6: the ground in octaves, the peak Ab6
    41: '[C6 Eb6 G6]/2 [Bb5 D6 F6]/4 [G5 C6 Eb6]/4',
    42: '[G5 C6 Eb6]/4. [F5 Bb5 D6]/8 [Eb5 G5 C6]/2',
    43: '[Ab5 C6 F6]/2 [G5 C6 Eb6]/4 [F5 Ab5 D6]/4',
    44: '[G5 C6 F6]/2 [F5 B5 D6]/2',
    45: '[C6 Eb6 Ab6]/2. [D6 G6]/4',
    46: '[Ab5 C6 F6]/4. [G5 Eb6]/8 [Ab5 C6]/4 [F5 Ab5]/4',
    47: '[F5 Ab5 D6]/2 [Ab5 B5]/4 [F5 Ab5]/4',
    48: '[F5 B5 D6]/2 [D5 F5 B5]/4 r/4',
    # A4 - VAR 7: half the ground, it stops on G
    49: 'Eb5/2. G5/4',
    50: 'Bb5/2 G5/4 Eb5/4',
    51: 'Ab5/2 C5/4 r/4',
    52: 'D5/2. r/4',
    # coda
    53: 'G5/2. F5/4',
    54: 'Eb5/2 C5/4 Ab4/4',
    55: 'C5/2 B4/2',
    56: '[C4 G4 Eb5]/1^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar). The slash / root bass is always the ground's note.
FIG = {
    'synco': '0 - - 2+3 - - 1 -',       # VAR 4: the chord on the & of 2
    'climb16': '0 1 2 3 4 3 4 5 4 5 6 5 4 3 2 1',   # VAR 5
}

LH = {
    1: 'Cm:still', 2: 'Eb:still', 3: 'Fm:still', 4: 'Gm:still', 5: 'Ab:still', 6: 'Fm7:still',
    7: 'Dm7b5:still', 8: 'G7:half',
    9: 'Cmadd9:lilt', 10: 'Cm/Eb:lilt', 11: 'Fm7:lilt', 12: 'Cm/G:lilt', 13: 'Abmaj7:lilt', 14: 'F7:lilt',
    15: 'Bb/D:lilt', 16: 'Gsus4:ring G:ring',
    17: 'C:flow', 18: 'Ebmaj7:flow', 19: 'F:flow', 20: 'G:color', 21: 'Abmaj7:flow', 22: 'Fm6:flow',
    23: 'Dm7:flow', 24: 'G7:half',
    25: 'Cm:synco', 26: 'Eb6:synco', 27: 'Fm9:synco', 28: 'G7sus4:ring G7:ring', 29: 'Abmaj7:synco',
    30: 'Fm7:synco', 31: 'Dm7b5:synco', 32: 'G7:half',
    33: 'CmMaj7:climb16', 34: 'Ebmaj7:climb16', 35: 'Fm6:climb16', 36: 'G7:climb16', 37: 'Ab6:climb16',
    38: 'Fmadd9:climb16', 39: 'Dm7b5:climb16', 40: 'G7b9:ring G7:ring',
    41: 'Cm:big', 42: 'Cm/Eb:big', 43: 'Fm:big', 44: 'G7sus4:big G7:big', 45: 'Abmaj7#11:sweep',
    46: 'Fm9:big', 47: 'Bdim7/D:big', 48: 'G7:roll',
    49: 'Cm:open', 50: 'Eb:open', 51: 'Fm:open', 52: 'G:still',
    53: 'Abmaj7:open', 54: 'Fm7:open', 55: 'Gsus4:ring G:ring', 56: 'Cm:roll',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'mp'), (4, 4, 'p'), (5, 0, 'mp'), (8, 0, 'p'),
       (9, 0, 'p'), (12, 4, 'p'), (13, 0, 'mp'), (16, 0, 'p'),
       (17, 0, 'mp'), (20, 4, 'p'), (21, 0, 'mp'), (23, 0, 'mp'), (24, 0, 'p'),
       (25, 0, 'p'), (27, 0, 'mp'), (28, 4, 'p'), (29, 0, 'mp'), (31, 0, 'mf'), (32, 4, 'mp'),
       (33, 0, 'p'), (35, 0, 'p'), (37, 0, 'mp'), (39, 0, 'mp'), (40, 0, 'mf'), (40, 4, 'f'),
       (41, 0, 'f'), (43, 0, 'f'), (44, 4, 'ff'), (45, 0, 'ff'), (45, 6, 'f'), (46, 4, 'mf'), (47, 4, 'mp'),
       (48, 4, 'p'),
       (49, 0, 'p'), (50, 0, 'mp'), (51, 4, 'p'), (52, 0, 'pp'),
       (53, 0, 'p'), (54, 4, 'pp'), (55, 0, 'pp'), (56, 0, 'pp')]

PHRASES = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 40), (41, 44),
           (45, 48), (49, 52), (53, 56)]

SECTIONS = [('A1', 8), ('A2', 8), ('B1', 8), ('A3', 8), ('build', 8), ('climax', 8), ('A4', 4), ('coda', 4)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    for k in (4, 12, 20, 28):                           # the half-way breaths
        s.ritardando((bar(k) + 2.0, bar(k + 1)), to=0.88)
    for k in (8, 16, 24, 32):                           # the ground's cadences
        s.ritardando((bar(k) + 1.0, bar(k + 1)), to=0.8)
    s.set_tempo(bar(17), 60)                             # the major: a little lighter
    s.set_tempo(bar(25), 58)
    s.set_tempo(bar(33), 60)
    s.ritardando((bar(40) + 2.0, bar(41)), to=0.85)     # the inhale
    s.set_tempo(bar(41), 62)
    s.ritardando((bar(44) + 2.0, bar(45)), to=0.85)
    s.ritardando((bar(45), bar(46)), to=0.8, a_tempo=False)
    s.fermata(bar(45) + 3.0, hold=1.0)                  # the peak over A-flat
    s.set_tempo(bar(46), 58)
    s.ritardando((bar(47), bar(49)), to=0.72, a_tempo=False)
    s.fermata(bar(48) + 2.0, hold=1.5)
    s.set_tempo(bar(49), 54)
    s.ritardando((bar(51) + 2.0, bar(52) + 3.0), to=0.75, a_tempo=False)
    s.fermata(bar(52) + 2.0, hold=2.5)                  # the ground stops on G
    s.set_tempo(bar(53), 52)
    s.ritardando((bar(54) + 2.0, bar(56)), to=0.72, a_tempo=False)
    s.fermata(bar(56) + 1.0, hold=3)
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
