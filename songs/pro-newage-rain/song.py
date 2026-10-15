"""Glass After Rain - an original new-age / pop-classical piece for solo grand piano in E minor.
Build: python -m agentsound build songs/pro-newage-rain

A composed ("pro") reference for the endless new-age blind rounds (songs/_blind/ROUNDS.md "New-age"): written by
hand like songs/letters-to-the-morning, played by the SAME setup as an endless new-age tune (agentsound.endless.perform
.band with the new-age-piano genre spec: the solo_piano grand, the genre's eq / master; the romantic pianist
romantic.Score.perform with the feel's touch, the shared broken-chord left hand pianist.FIGURES, the feel's body),
so the sound and the player are no tell - only the writing differs.

4/4, 68 BPM (the return 63, the coda 60), rubato, 60 bars. Two ideas: the THEME (a dotted sigh G-F#-E falling to B,
answered by a step-wise rise) over a lament bass E-D-C-B, and the "drops" (four 8ths falling from E6 through the
chord, a held note) - plus the piece's signature, the suspension E -> D# over B (bars 8, 16, 35, 46, 50, 59).

  intro   1-4    the left hand alone over the lament bass (Em Em/D Cmaj7 B7), then the drops, high and soft
  A1      5-12   the theme, p: a 4-bar question ending on the E -> D# suspension, the answer through Am7 - D to Em
  A2      13-21  the theme over flowing 8ths, the answer climbing higher (B5) and extended by a bar (Gmaj7 - Cmaj7);
                 F#m7b5 - B7 does not go home: a deceptive turn to Cmaj7 opens the B section
  B1      22-29  the relative-major hook (quarter arpeggio into a held note, a dotted fall), each statement a step
                 higher (B5, B5, C6, D6) over open tenths, ending on Dsus4 - D
  inter   30-31  the drops again, over Cmaj7 - B7, the left hand still
  A3      32-35  the theme harmonised in sixths and thirds over a rocking hand
  build   36-40  the hook in minor (Am7 - D - Bm7 - Cmaj7), the left hand widening, a run into B7
  climax  41-46  the theme in octaves, ff at the A6 over Cmaj7 (bar 43), falling through Am7 to the Neapolitan F/A,
                 a breath, the suspension in chords and a fermata
  A4      47-54  the theme an octave up, pp over quarter notes; its answer in the old register, a deceptive cadence
  coda    55-60  the drops over Cmaj7, darkened over Cm6 (Eb), a glance at G, the theme's head and the suspension
                 one last time, a rolled Em(add9)

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Glass After Rain', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#d7dee6', '#3f5266'], 'title': 'GLASS AFTER RAIN',
         'subtitle': 'solo piano - AgentSound', 'seed': 19}

G = _genre('new-age-piano')
FEEL = 'gentle'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'E minor'
METER = 4                  # 4 or 3
TEMPO = 68
SEED = 19

# ------------------------------------------------------------------------------------------------ right hand
# one entry per bar, notation (agentsound.notation, unit 1/8): E5/4. = a dotted quarter, r = rest, [B4 E5]/2 = notes
# together, ^turn / ^tr ornaments, [..]/1^roll(110) a rolled chord, {..}:N^fig(arch) a fioritura
RH = {
    # intro - the left hand alone, then the drops
    1: 'r/1',
    2: 'r/1',
    3: 'r/8 E6/8 D6/8 B5/8 G5/2',
    4: 'r/8 E6/8 D#6/8 B5/8 F#5/2',
    # A1 - the theme: question (5-8), answer (9-12)
    5: 'G5/4. F#5/8 E5/4 B4/4',
    6: 'D5/4. E5/8 F#5/2',
    7: 'G5/4. A5/8 G5/4 F#5/4',
    8: 'E5/2 D#5/4 r/4',
    9: 'A5/4. G5/8 E5/4 C5/4',
    10: 'D5/8 E5/8 F#5/8 G5/8 A5/2',
    11: 'G5/4.^turn F#5/8 E5/4 D#5/4',
    12: 'E5/2. r/4',
    # A2 - the theme again, its answer higher and a bar longer, a deceptive cadence
    13: 'G5/4. F#5/8 E5/8 D5/8 B4/4',
    14: 'D5/4. E5/8 F#5/2',
    15: 'G5/4. B5/8 A5/4 G5/8 F#5/8',
    16: '[B4 E5]/2 [B4 D#5]/4 r/4',
    17: 'A5/4. G5/8 E5/4 C5/8 E5/8',
    18: 'D5/4. E5/8 F#5/4 A5/4',
    19: 'B5/4. A5/8 G5/4 F#5/4',
    20: 'E5/4. F#5/8 G5/4 B5/4',
    21: 'A5/4. G5/8 F#5/8 r/8 D#5/4',
    # B1 - the relative-major hook, each statement a step higher
    22: 'E5/4 G5/4 [G5 B5]/2',
    23: 'A5/4. G5/8 F#5/4 D5/4',
    24: 'D5/4 G5/4 [G5 B5]/4. C6/8',
    25: 'B5/4. A5/8 G5/4 r/4',
    26: 'E5/4 G5/4 [E5 C6]/2',
    27: 'B5/4. A5/8 G5/4 F#5/4',
    28: 'G5/4 B5/4 [G5 D6]/4. C6/8',
    29: 'B5/4 A5/8 G5/8 F#5/4 r/4',
    # interlude - the drops
    30: 'r/8 E6/8 D6/8 B5/8 G5/4 r/4',
    31: 'r/8 E6/8 D#6/8 B5/8 A5/2',
    # A3 - the theme in sixths and thirds
    32: '[B4 G5]/4. [A4 F#5]/8 [G4 E5]/4 B4/4',
    33: '[B4 D5]/4. [C5 E5]/8 [D5 F#5]/2',
    34: '[E5 G5]/4. [F#5 A5]/8 [E5 G5]/4 [D5 F#5]/4',
    35: '[B4 E5]/2 [B4 D#5]/4 r/8 B4/8',
    # build - the hook in minor, climbing
    36: 'C5/4 E5/4 [C5 A5]/2',
    37: 'A5/4. G5/8 F#5/4 D5/4',
    38: 'D5/4 F#5/4 [D5 B5]/2',
    39: 'E5/8 G5/8 B5/8 D6/8 C6/4. B5/8',
    40: 'A5/8 B5/8 C6/8 E6/8 [B5 D#6 F#6]/2',
    # climax - the theme in octaves, the A6, the Neapolitan, the suspension
    41: '[G5 B5 G6]/4. [F#5 F#6]/8 [E5 E6]/4 [B4 B5]/4',
    42: '[D5 D6]/4. [E5 E6]/8 [F#5 A5 F#6]/2',
    43: '[G5 B5 G6]/4. [A5 A6]/8 [G5 G6]/4 [F#5 F#6]/4',
    44: '[E5 E6]/4. [D5 D6]/8 [E5 C6]/4 [B4 B5]/4',
    45: '[A5 C6 F6]/2. r/4',
    46: '[B5 E6]/2 [B5 D#6]/4 r/4',
    # A4 - the theme an octave up, pp; its answer back home, deceptive
    47: 'G6/4. F#6/8 E6/4 B5/4',
    48: 'D6/4. E6/8 F#6/2',
    49: 'G6/4. F#6/8 E6/4 D6/4',
    50: 'E6/2 D#6/4 r/4',
    51: 'A5/4. G5/8 E5/4 C5/4',
    52: 'D5/4. E5/8 F#5/4. G5/8',
    53: 'G5/4.^turn F#5/8 E5/4 D#5/4',
    54: 'E5/2. r/4',
    # coda
    55: 'r/8 E6/8 D6/8 B5/8 G5/2',
    56: 'r/8 Eb6/8 D6/8 A5/8 G5/2',
    57: 'B5/2. r/4',
    58: 'r/2 G5/4. F#5/8',
    59: 'E5/2 D#5/4 r/4',
    60: '[B4 E5 G5 B5]/1^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two or three entries split the bar evenly). figure = a pianist.FIGURES name (flow rock
# color lilt open quart ring half up big sweep roll tenths walk10 still; 3/4: waltz waltz2 barcarolle waltz_held
# waltz_open waltz_arp waltz_step waltz_big) or your own token string over the chord's ladder (0 = the bass, 1 2 3 ...
# the chord tones above it, x = the colour tone, o = bass + its octave below, c = steps 1-3 together, R = rolled and
# held, a+b together, '-' holds): 8 tokens = 8ths in 4/4, 6 = 8ths in 3/4, 16 = 16ths.
# Own figures (named here, resolved in figures()):
FIG = {
    'drift': '0 2 3 4 - 3 2 -',        # 8ths that pause on the 4th and 8th: the rain between the drops
    'swing': '0 - 2 3 4 3 - 1',        # the bass rings a quarter, a rise and a fall: the B section's open hand
}

LH = {
    1: 'Em:drift', 2: 'Em/D:drift', 3: 'Cmaj7:ring', 4: 'B7:half',
    5: 'Em:lilt', 6: 'Em/D:lilt', 7: 'Cmaj7:color', 8: 'Bsus4:half B:half',
    9: 'Am7:lilt', 10: 'D:rock', 11: 'Cmaj7:half B7:half', 12: 'Em:half',
    13: 'Em:flow', 14: 'Em/D:flow', 15: 'Cmaj7:color', 16: 'Bsus4:half B:half',
    17: 'Am7:flow', 18: 'D/F#:rock', 19: 'Gmaj7:flow', 20: 'Cmaj7:color', 21: 'F#m7b5:half B7:half',
    22: 'Cmaj7:tenths', 23: 'D:swing', 24: 'G/B:tenths', 25: 'Em7:half',
    26: 'Cmaj7:walk10', 27: 'D/F#:swing', 28: 'G:walk10', 29: 'Dsus4:half D:half',
    30: 'Cmaj7:open', 31: 'B7:still',
    32: 'Em:rock', 33: 'Em/D:rock', 34: 'Cmaj7:lilt', 35: 'Bsus4:half B7:half',
    36: 'Am7:flow', 37: 'D:flow', 38: 'Bm7:big', 39: 'Cmaj7:big', 40: 'Am7:up B7:up',
    41: 'Em:sweep', 42: 'Em/D:big', 43: 'Cmaj7:sweep', 44: 'Am7:big', 45: 'F/A:big', 46: 'Bsus4:half B7:roll',
    47: 'Em:quart', 48: 'Em/D:quart', 49: 'Cmaj7:open', 50: 'Bsus4:half B:half',
    51: 'Am7:lilt', 52: 'D:lilt', 53: 'Cmaj7:half B7:half', 54: 'Cmaj7:ring',
    55: 'Cmaj7:open', 56: 'Cm6:open', 57: 'G/B:still', 58: 'Cmaj7:half', 59: 'Bsus4:half B:half',
    60: 'Emadd9:roll',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'pp'), (3, 0, 'mp'), (3, 3, 'p'), (4, 0, 'mp'), (4, 3, 'p'), (4, 6, 'pp'),
       (5, 0, 'p'), (7, 0, 'mp'), (8, 4, 'p'), (9, 0, 'p'), (10, 0, 'mp'), (11, 4, 'p'), (12, 4, 'pp'),
       (13, 0, 'p'), (14, 4, 'mp'), (16, 4, 'p'), (17, 0, 'mp'), (19, 0, 'mf'), (20, 4, 'mp'), (21, 4, 'p'),
       (22, 0, 'mp'), (24, 0, 'mf'), (25, 4, 'mp'), (26, 0, 'mf'), (28, 0, 'mf'), (29, 0, 'mp'), (29, 4, 'p'),
       (30, 0, 'p'), (30, 3, 'pp'), (31, 0, 'p'), (31, 3, 'pp'),
       (32, 0, 'p'), (33, 0, 'mp'), (34, 0, 'mf'), (34, 6, 'mp'), (35, 4, 'p'),
       (36, 0, 'mp'), (38, 0, 'mf'), (39, 4, 'mf'), (40, 0, 'f'),
       (41, 0, 'f'), (43, 0, 'ff'), (44, 4, 'f'), (45, 0, 'f'), (46, 0, 'mf'), (46, 4, 'mp'),
       (47, 0, 'pp'), (48, 4, 'p'), (50, 0, 'pp'), (51, 0, 'p'), (52, 4, 'mp'), (53, 4, 'p'),
       (55, 0, 'mp'), (55, 3, 'p'), (56, 0, 'mp'), (56, 3, 'p'), (57, 0, 'p'), (58, 0, 'p'), (59, 4, 'pp'),
       (60, 0, 'pp')]

PHRASES = [(1, 2), (3, 4), (5, 8), (9, 12), (13, 16), (17, 21), (22, 25), (26, 29), (30, 31), (32, 35), (36, 40),
           (41, 43), (44, 46), (47, 50), (51, 54), (55, 57), (58, 60)]

# sections, in order, with bars - names from the endless vocabulary: intro, A1, A2, A3, A4, B1, B2, inter, build,
# climax, coda (the blind packets print these names)
SECTIONS = [('intro', 4), ('A1', 8), ('A2', 9), ('B1', 8), ('inter', 2), ('A3', 4), ('build', 5), ('climax', 6),
            ('A4', 8), ('coda', 6)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    for k in (8, 16, 25, 50):                      # the half-way breaths
        s.ritardando((bar(k) + 1.0, bar(k) + 4.0), to=0.9)
    for k in (4, 12, 21, 29, 35, 54):              # cadences / section ends
        s.ritardando((bar(k) + 1.0, bar(k) + 4.0), to=0.8)
    s.ritardando((bar(31), bar(32)), to=0.82)      # the interlude's last bar
    s.ritardando((bar(40) + 2.0, bar(41)), to=0.88)  # the inhale before the climax
    s.ritardando((bar(45), bar(46) + 2.0), to=0.72, a_tempo=False)
    s.fermata(bar(45) + 2.5, hold=1.0)            # the Neapolitan rings into its breath
    s.fermata(bar(46) + 2.5, hold=2.5)            # the suspension resolved, the B7 rings
    s.set_tempo(bar(47), 63)                       # the return: calmer
    s.set_tempo(bar(55), 60)
    s.ritardando((bar(58), bar(60)), to=0.75, a_tempo=False)
    s.fermata(bar(60) + 1.0, hold=3)
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
