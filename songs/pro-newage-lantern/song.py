"""Lanterns Along the River - an original new-age rondo for solo grand piano in A-flat major, 4/4.
Build: python -m agentsound build songs/pro-newage-lantern

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

4/4, 88 BPM (episode 1: 84, the climax 92), 64 bars. A RONDO (refrain - episode - refrain - episode - refrain): the
refrain is a bright, syncopated tune (Eb5 Ab5 C6, a quarter across the beat, the leap to Eb6), every return changed;
the episodes are in other keys. The climax sits in the second episode (in E major, a bVI away) and turns home on an
enharmonic pivot: its held G#6 is re-heard as A-flat, the refrain's tonic.

  intro   1-2    two bars of the refrain's left hand with the hook's first cell high, pp
  A1      3-10   REFRAIN, mf, the pulse hand; it closes on the tonic
  B1      11-22  EPISODE 1 - F minor, lyrical, long notes low in the voice (C5-Ab5), the flowing hand; 4 + 4 + 4 bars,
                 the third phrase through Db and Gb (bVII of Ab) to Eb7sus4
  A2      23-30  REFRAIN varied: the hook a third higher at first, Fm7 for Eb/G, the cadence deceptive (Fm)
  B2      31-36  EPISODE 2 - Db minor = C# minor: the refrain's head in the minor, sinking into E major
  build   37-40  E major: a rising line over C#m7 - A - B7sus4, the hand climbing
  climax  41-44  E major: a new tune in three-voice chords up to G#6 (once), the G#6 rings on a fermata over E
  inter   45-46  the retransition: the next chord re-hears the G# as A-flat (Ab/Eb - Eb7sus4 - Eb7), home without a
                 modulation
  A3      47-56  REFRAIN, last: from pp, in the warm middle register, extended by two bars to a full close on Ab
  coda    57-64  the hook in long notes (augmented), Db/Ab - Ab, the bells of the intro, a rolled Ab(add9)

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Lanterns Along the River', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#f6e6c4', '#b5562b'], 'title': 'LANTERNS ALONG THE RIVER',
         'subtitle': 'solo piano - AgentSound', 'seed': 37}

G = _genre('new-age-piano')
FEEL = 'bright'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'Ab major'
TIME = (4, 4)
METER = 4                  # quarter beats per bar
TEMPO = 88
SEED = 37

# ------------------------------------------------------------------------------------------------ right hand
RH = {
    # intro - the hook's first cell high over the refrain's hand
    1: 'r/2 C6/8 Eb6/8 G6/4',
    2: 'Eb6/4 r/4 r/2',
    # A1 - REFRAIN
    3: 'Eb5/8 Ab5/8 C6/4 Bb5/8 Ab5/8 Eb5/4',
    4: 'G5/4. Bb5/8 Eb6/4 r/4',
    5: 'Ab5/4 G5/8 F5/8 C5/4 Eb5/4',
    6: 'F5/2 Eb5/4 r/4',
    7: 'Eb5/8 Ab5/8 C6/4 Db6/8 C6/8 Ab5/4',
    8: 'F5/4.^turn Ab5/8 Db6/4 C6/4',
    9: 'Bb5/4 Db6/8 C6/8 Ab5/4 Bb5/4',
    10: 'Ab5/2 r/4 r/8 C5/8',
    # B1 - EPISODE 1: F minor, lyrical, low
    11: 'F5/2. Eb5/8 C5/8',
    12: 'Db5/4. C5/8 Bb4/2',
    13: 'G4/4 Bb4/4 Eb5/4 G5/4',
    14: 'F5/2 r/4 r/8 C5/8',
    15: 'F5/4. G5/8 Ab5/2',
    16: 'Bb5/4. Ab5/8 F5/4 Db5/4',
    17: 'E5/4 G5/4 C6/4 Bb5/8 G5/8',
    18: 'Ab5/2 r/2',
    19: 'Db5/4. F5/8 Ab5/4 C6/4',
    20: 'Bb5/4. Ab5/8 Gb5/4 Db5/4',
    21: 'Eb5/4 Gb5/8 F5/8 Eb5/4 Db5/4',
    22: 'C5/4 Eb5/4 r/4 Eb5/8 Ab5/8',
    # A2 - REFRAIN varied: higher at first, a deceptive close
    23: 'C6/4 Eb6/4 Db6/8 C6/8 Ab5/4',
    24: 'Ab5/4. C6/8 F6/4 r/4',
    25: 'Ab5/4 G5/8 F5/8 C5/4 Eb5/4',
    26: 'Db5/4 F5/8 Ab5/8 Eb5/2',
    27: 'Eb5/8 Ab5/8 C6/4 Db6/8 Eb6/8 C6/4',
    28: 'Db6/4.^mord C6/8 Ab5/4 F5/4',
    29: 'G5/4 Bb5/8 Ab5/8 G5/4 Eb5/4',
    30: 'F5/2 r/2',
    # B2 - EPISODE 2: the head in Db minor, sinking to E major
    31: 'E5/8 G#5/8 B5/4 A5/8 G#5/8 E5/4',
    32: 'F#5/4. A5/8 D6/4 r/4',
    33: 'C#6/4 B5/8 A5/8 E5/4 F#5/4',
    34: 'G#5/2 r/4 B4/4',
    35: 'E5/4. F#5/8 G#5/4 B5/4',
    36: 'A5/4. G#5/8 F#5/2',
    # build - E major, rising
    37: 'r/8 E5/8 G#5/8 B5/8 E6/4. D#6/8',
    38: 'C#6/4. B5/8 A5/4 E5/4',
    39: 'r/8 F#5/8 A5/8 C#6/8 F#6/4. E6/8',
    40: '[F#5 D#6]/2 [F#5 A5 C#6]/4 [A5 B5]/4',
    # climax - a new tune in chords, G#6 once, then the pivot G# = Ab
    41: '[G#5 B5 E6]/4. [F#5 D#6]/8 [E5 G#5 C#6]/4 [G#5 B5]/4',
    42: '[A5 C#6 F#6]/2 [G#5 E6]/4 [F#5 D#6]/4',
    43: '[E5 G#5 C#6]/4. [D#5 B5]/8 [E5 G#5 E6]/4 [F#5 B5 F#6]/4',
    44: '[B5 E6 G#6]/2. [G#5 E6]/4',
    45: '[Eb5 Ab5 C6]/2 [Db5 F5 Bb5]/4 [C5 Eb5 Ab5]/4',
    46: '[Db5 G5 Bb5]/2 [Db5 G5]/4 r/4',
    # A3 - REFRAIN, last: from pp, the middle register, a full close
    47: 'C5/8 Eb5/8 Ab5/4 G5/8 F5/8 Eb5/4',
    48: 'G5/4. Bb5/8 Eb5/4 r/4',
    49: 'Ab5/4 G5/8 F5/8 C5/4 Eb5/4',
    50: 'F5/2 Db5/4 r/4',
    51: 'Eb5/8 Ab5/8 C6/4 Db6/8 C6/8 Ab5/4',
    52: 'F5/4.^turn Ab5/8 Db6/4 C6/4',
    53: 'Bb5/4 C6/8 Bb5/8 Gb5/4 F5/4',
    54: 'Eb5/2 Ab5/4 G5/4',
    55: 'Bb5/4 Db6/8 C6/8 Ab5/4 G5/4',
    56: 'Ab5/2 r/2',
    # coda - the hook augmented, Db/Ab, the intro's bells
    57: 'Eb5/2 Ab5/2',
    58: 'C6/2. Bb5/4',
    59: 'Ab5/2 F5/4 Db5/4',
    60: 'Eb5/1',
    61: 'r/2 C6/8 Eb6/8 F6/4',
    62: 'Eb6/2 r/2',
    63: 'r/4 C5/4 Eb5/4 Bb5/4',
    64: '[Ab4 Eb5 Bb5 C6]/1^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar). 8 tokens = 8ths, 16 = 16ths.
FIG = {
    'lantern': '0 - c 2 - 3 c -',      # the refrain's pulse: bass, a chord on the & of 1, light 8ths
    'run16': '0 1 2 3 4 3 2 1 0 1 2 3 4 3 2 1',  # the build: 16ths
}

LH = {
    1: 'Ab:lantern', 2: 'Eb/G:lantern',
    3: 'Ab:lantern', 4: 'Eb/G:lantern', 5: 'Fm7:lantern', 6: 'Dbadd9:pulse',
    7: 'Ab/C:lantern', 8: 'Db:lantern', 9: 'Bbm7:pulse Eb7sus4:pulse', 10: 'Ab:half',
    11: 'Fm:flow', 12: 'Bbm7:flow', 13: 'Eb7:flow', 14: 'Abmaj7:color',
    15: 'Fm/Ab:flow', 16: 'Bbm7:flow', 17: 'C7:flow', 18: 'Fm:color',
    19: 'Db:flow', 20: 'Gb:flow', 21: 'Ebm7:ring Db/F:ring', 22: 'Ab/Eb:ring Eb7sus4:ring',
    23: 'Ab:lantern', 24: 'Fm7:lantern', 25: 'Fm7:lantern', 26: 'Db:pulse',
    27: 'Ab/C:lantern', 28: 'Db:lantern', 29: 'Eb7sus4:pulse Eb7:pulse', 30: 'Fm:half',
    31: 'C#m:rock', 32: 'D:rock', 33: 'A:rock', 34: 'E/G#:half',
    35: 'C#m7:color', 36: 'D:ring B7sus4:ring',
    37: 'E:up', 38: 'A:flow', 39: 'F#m7:up', 40: 'B7sus4:ring B7:ring',
    41: 'E:big', 42: 'F#m7:big', 43: 'C#m7:big', 44: 'E:sweep',
    45: 'Ab/Eb:big Eb7sus4:big', 46: 'Eb7:ring Eb7:half',
    47: 'Ab:quart', 48: 'Eb/G:quart', 49: 'Fm7:lilt', 50: 'Dbadd9:lilt',
    51: 'Ab/C:lantern', 52: 'Db:lantern', 53: 'Gb:lilt', 54: 'Ab/Eb:ring Fm7:ring',
    55: 'Bbm7:ring Eb7sus4:ring', 56: 'Ab:half',
    57: 'Db/Ab:open', 58: 'Ab:open', 59: 'Db:open', 60: 'Ab/Eb:ring Eb7sus4:ring',
    61: 'Db/Ab:open', 62: 'Ab:still', 63: 'Db/Ab:open', 64: 'Abadd9:roll',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'pp'), (2, 0, 'p'),
       (3, 0, 'p'), (5, 0, 'p'), (6, 4, 'pp'), (7, 0, 'p'), (9, 0, 'mp'), (10, 0, 'p'),
       (11, 0, 'p'), (13, 0, 'mp'), (14, 4, 'p'), (15, 0, 'p'), (17, 0, 'mp'), (18, 4, 'p'), (19, 0, 'p'),
       (20, 0, 'mp'), (21, 4, 'p'), (22, 4, 'mp'),
       (23, 0, 'mp'), (25, 0, 'p'), (26, 4, 'p'), (27, 0, 'mp'), (29, 0, 'mp'), (30, 0, 'p'),
       (31, 0, 'p'), (33, 0, 'p'), (34, 6, 'p'), (35, 0, 'mp'), (36, 4, 'mp'),
       (37, 0, 'mp'), (38, 0, 'mf'), (39, 0, 'mf'), (40, 0, 'f'),
       (41, 0, 'f'), (42, 0, 'f'), (43, 4, 'ff'), (44, 0, 'ff'), (44, 6, 'f'), (45, 0, 'mf'), (46, 0, 'mp'),
       (46, 4, 'p'),
       (47, 0, 'pp'), (48, 0, 'p'), (49, 4, 'p'), (51, 0, 'mp'), (52, 0, 'mp'), (53, 0, 'mf'), (54, 4, 'mp'),
       (55, 0, 'mp'), (56, 0, 'p'),
       (57, 0, 'p'), (58, 0, 'mp'), (59, 4, 'p'), (60, 0, 'pp'), (61, 4, 'p'), (62, 0, 'pp'), (63, 0, 'pp'),
       (64, 0, 'pp')]

PHRASES = [(1, 2), (3, 6), (7, 10), (11, 14), (15, 18), (19, 22), (23, 26), (27, 30), (31, 34), (35, 36), (37, 40),
           (41, 44), (45, 46), (47, 50), (51, 56), (57, 60), (61, 64)]

SECTIONS = [('intro', 2), ('A1', 8), ('B1', 12), ('A2', 8), ('B2', 6), ('build', 4), ('climax', 4), ('inter', 2),
            ('A3', 10), ('coda', 8)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    s.ritardando((bar(2) + 1.0, bar(3)), to=0.85)
    for k in (6, 14, 26, 34):                           # the half-way breaths
        s.ritardando((bar(k) + 2.0, bar(k + 1)), to=0.88)
    for k in (10, 18, 30, 50):                          # cadences
        s.ritardando((bar(k) + 1.0, bar(k + 1)), to=0.82)
    s.set_tempo(bar(11), 84)                             # episode 1: a little broader
    s.ritardando((bar(22), bar(23)), to=0.8)
    s.set_tempo(bar(23), 88)
    s.ritardando((bar(36), bar(37)), to=0.85)
    s.set_tempo(bar(37), 90)
    s.ritardando((bar(40) + 2.0, bar(41)), to=0.86)     # the inhale
    s.set_tempo(bar(41), 92)
    s.ritardando((bar(44), bar(45) + 2.0), to=0.78, a_tempo=False)
    s.fermata(bar(44) + 3.0, hold=1.5)                  # G#6 rings and turns into A-flat
    s.ritardando((bar(46), bar(47)), to=0.75, a_tempo=False)
    s.set_tempo(bar(47), 84)
    s.ritardando((bar(55), bar(56) + 2.0), to=0.8, a_tempo=False)
    s.set_tempo(bar(57), 76)
    s.ritardando((bar(60), bar(61)), to=0.85)
    s.ritardando((bar(62), bar(64)), to=0.75, a_tempo=False)
    s.fermata(bar(64) + 1.0, hold=3)
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
