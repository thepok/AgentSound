"""The Long Way Home - an original new-age piece for solo grand piano, E-flat major -> G-flat major, 4/4.
Build: python -m agentsound build songs/pro-newage-homecoming

A composed ("pro") reference for the endless new-age generator (set 2, songs/pro-newage-*/NOTES.md): played by the
SAME setup as an endless new-age tune (agentsound.endless.perform.band with the new-age-piano spec, the romantic
pianist with the feel's touch / body, the shared broken-chord left hand pianist.figure), so only the writing differs.

4/4, 66 BPM (the bridge 64, the climax 70, the last A 62), 52 bars. SONG FORM (AABA) whose climax OVERSHOOTS: the
bridge's climb, instead of falling back to E-flat, lands on Db7 and the last A is in G-flat major (a minor third up):
the piece ends in another key than it began. The theme opens with a SCALE (Bb4 C5 D5 Eb5) into a leap to G5 - a
step-wise head, not an arpeggio.

  intro   1-2    one rolled Eb(add9), held; the theme's scale as a pickup
  A1      3-10   the theme, p: scale into a leap, the answer through Fm7 - Bb7, a full close on Eb
  A2      11-18  the theme varied: the leap held longer, Gm7 (iii) for Cm7, a secondary Eb7/Db to Ab, closing on
                 the 3rd (G5)
  B1      19-26  the bridge in C minor: a syncopated idea (the long notes on beat 2), Cm - Ab - Fm7 - G7, then
                 Cm/Bb - Abmaj7 - Fm7 - Bb7
  A3      27-34  the theme with a second voice under it (thirds and sixths), reharmonised in its second half
                 (Gm7 - C7 - Fm7)
  build   35-38  the scale head climbing (Ab - Bb/Ab - Gm7 - C7sus4), the hand climbing to 16ths
  climax  39-42  where Bb7 is expected: Db7 - the peak Gb6 (once) over Db7sus4/Ab, then down through Db7 into G-flat
  A4      43-48  the theme in G-flat, mp -> p, in the warm middle register; it closes on Ebm (the old tonic, now the
                 relative minor)
  coda    49-52  the scale head twice in Gb, a rolled Gb(add9)

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
from agentsound import *
from agentsound import jazz
from agentsound import romantic as rom
from agentsound.endless import genre as _genre
from agentsound.endless import perform

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'The Long Way Home', 'artist': 'AgentSound', 'album': 'Solo Piano', 'genre': 'New Age',
            'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#efe2cf', '#6b4a3a'], 'title': 'THE LONG WAY HOME',
         'subtitle': 'solo piano - AgentSound', 'seed': 47}

G = _genre('new-age-piano')
FEEL = 'gentle'            # the endless feel whose touch / body / rubato this piece uses: 'flowing' | 'gentle' | 'bright'
KEY = 'Eb major'
TIME = (4, 4)
METER = 4                  # quarter beats per bar
TEMPO = 66
SEED = 47

# ------------------------------------------------------------------------------------------------ right hand
RH = {
    # intro - one rolled chord, the scale as a pickup
    1: '[Eb4 Bb4 F5 G5]/2^roll(90) r/2',
    2: 'r/2 r/4 r/8 Bb4/8',
    # A1 - the theme
    3: 'C5/8 D5/8 Eb5/8 F5/8 G5/2',
    4: 'Ab5/4.^turn G5/8 Eb5/2',
    5: 'Eb5/4 D5/8 C5/8 G4/4 Bb4/4',
    6: 'C5/2 D5/4 r/4',
    7: 'Bb4/8 C5/8 D5/8 Eb5/8 Bb5/2',
    8: 'C6/4. Bb5/8 G5/4 Eb5/4',
    9: 'F5/4 Ab5/8 G5/8 F5/4 D5/4',
    10: 'Eb5/2 r/4 r/8 Bb4/8',
    # A2 - varied: the leap held, iii for vi, a secondary dominant
    11: 'C5/8 D5/8 Eb5/8 F5/8 G5/4. F5/8',
    12: 'Ab5/4.^mord G5/8 Eb5/4 C6/4',
    13: 'Bb5/4. G5/8 F5/4 D5/4',
    14: 'Eb5/2 G5/4 r/4',
    15: 'C5/8 Eb5/8 Ab5/8 Bb5/8 C6/2',
    16: 'Db6/4. C6/8 Bb5/4 G5/4',
    17: 'C6/4 Ab5/4 F5/4 Eb5/4',
    18: 'G5/2 r/2',
    # B1 - the bridge: C minor, the long notes on beat 2
    19: 'r/4 G5/2 Eb5/4',
    20: 'C6/2. Bb5/8 Ab5/8',
    21: 'Ab5/4 F5/2 C5/4',
    22: 'C5/4 D5/4 B4/4 r/4',
    23: 'r/4 G5/2 Bb5/4',
    24: 'C6/2 Eb6/4 C6/4',
    25: 'Ab5/4. G5/8 F5/4 Eb5/4',
    26: 'Eb5/2 D5/4 r/4',
    # A3 - the theme with a second voice, reharmonised
    27: 'C5/8 D5/8 Eb5/8 F5/8 [Eb5 G5]/2',
    28: '[C5 Ab5]/4. [Bb4 G5]/8 [C5 Eb5]/2',
    29: '[Bb4 D5]/4 [A4 C5]/8 [Bb4 D5]/8 [G4 Bb4]/4 [Bb4 E5]/4',
    30: '[Ab4 F5]/2 [Ab4 C5]/4 r/4',
    31: 'Bb4/8 C5/8 D5/8 Eb5/8 [G5 Bb5]/2',
    32: '[G5 Bb5]/4. [F5 A5]/8 [E5 G5]/4 [C5 E5]/4',
    33: '[C5 F5]/4 [Eb5 Ab5]/8 [D5 G5]/8 [C5 F5]/4 [Ab4 D5]/4',
    34: '[G4 Eb5]/2 r/4 r/8 Bb4/8',
    # build - the scale head climbing
    35: 'C5/8 D5/8 Eb5/8 F5/8 [Eb5 Ab5]/4 [Eb5 C6]/4',
    36: 'D5/8 Eb5/8 F5/8 G5/8 [F5 Bb5]/4 [F5 D6]/4',
    37: 'Eb5/8 F5/8 G5/8 A5/8 [G5 Bb5]/4 [Bb5 D6]/4',
    38: 'F5/8 G5/8 Bb5/8 C6/8 [E5 G5 E6]/4 [G5 Bb5 F6]/8 [G5 C6 E6]/8',
    # climax - Db7 instead of Bb7: the peak Gb6, down into G-flat
    39: '[F5 Ab5 Cb6 F6]/2 [Ab5 Cb6 Eb6]/4 [F5 Ab5 Db6]/4',
    40: '[Ab5 Db6 Gb6]/2. [F5 Ab5 Eb6]/8 [Db5 F5 Db6]/8',
    41: '[Cb5 Eb5 Cb6]/4. [Bb4 Db5 Bb5]/8 [Ab4 Db5 Ab5]/4 [F4 Ab4 F5]/4',
    42: '[Gb4 Bb4 Eb5]/4. [Ab4 Db5]/8 [Ab4 Cb5]/4 r/4',
    # A4 - the theme in G-flat, warm and low
    43: 'Eb5/8 F5/8 Gb5/8 Ab5/8 Bb5/2',
    44: 'Cb6/4.^turn Bb5/8 Gb5/2',
    45: 'Gb5/4 F5/8 Eb5/8 Bb4/4 Db5/4',
    46: 'Eb5/2 F5/4 r/4',
    47: 'Db5/8 Eb5/8 F5/8 Gb5/8 Db6/4. Cb6/8',
    48: 'Bb5/4 Gb5/8 Eb5/8 Bb4/2',
    # coda - the scale twice in G-flat, Gb(add9)
    49: 'r/4 Db5/8 Eb5/8 F5/8 Gb5/8 Bb5/4',
    50: 'Ab5/2 r/2',
    51: 'r/4 Db5/8 Eb5/8 F5/8 Gb5/8 Ab5/4',
    52: '[Gb4 Db5 Ab5]/1^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (two entries split the bar). 8 tokens = 8ths, 16 = 16ths.
FIG = {
    'home': '0 - 2 3 - 2 1 -',          # the theme's hand: a quarter, a short climb, the bar breathes
    'synco': '0 - - 2+3 - - 1 -',       # the bridge: the chord on the & of 2, against the melody's long notes
    'climb16': '0 1 2 3 4 3 4 5 4 5 6 5 4 3 2 1',   # the build's last bars
}

LH = {
    1: 'Ebadd9:roll',
    3: 'Eb:home', 4: 'Abmaj7:home', 5: 'Cm7:home', 6: 'Bb7sus4:ring Bb7:ring',
    7: 'Eb/G:home', 8: 'Abmaj7:home', 9: 'Fm7:ring Bb7:ring', 10: 'Eb:half',
    11: 'Eb:flow', 12: 'Abmaj7:flow', 13: 'Gm7:flow', 14: 'Cm7:color',
    15: 'Ab:flow', 16: 'Eb7/Db:flow', 17: 'Abmaj7:ring Bb7sus4:ring', 18: 'Eb:half',
    19: 'Cm:synco', 20: 'Ab:synco', 21: 'Fm7:synco', 22: 'G7sus4:ring G7:ring',
    23: 'Cm/Bb:synco', 24: 'Abmaj7:synco', 25: 'Fm7:synco', 26: 'Bb7sus4:ring Bb7:ring',
    27: 'Eb:lilt', 28: 'Abmaj7:lilt', 29: 'Gm7:ring C7:ring', 30: 'Fm7:half',
    31: 'Eb/G:lilt', 32: 'C7/E:lilt', 33: 'Fm7:ring Bb7sus4:ring', 34: 'Eb:half',
    35: 'Ab:up', 36: 'Bb/Ab:up', 37: 'Gm7:climb16', 38: 'C7sus4:ring C7:ring',
    39: 'Db7:big', 40: 'Db7sus4/Ab:sweep', 41: 'Cb:big Db7:big', 42: 'Ebm7:ring Db7sus4:ring',
    43: 'Gb:lilt', 44: 'Cbmaj7:lilt', 45: 'Ebm7:lilt', 46: 'Db7sus4:ring Db7:ring',
    47: 'Gb/Bb:lilt', 48: 'Ebm:half',
    49: 'Cbmaj7:open', 50: 'Db/F:still', 51: 'Cbmaj7:open', 52: 'Gbadd9:roll',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'p'), (2, 7, 'p'),
       (3, 0, 'p'), (6, 4, 'pp'), (7, 0, 'p'), (8, 0, 'p'), (10, 0, 'p'),
       (11, 0, 'p'), (12, 0, 'p'), (14, 0, 'p'), (15, 0, 'mp'), (17, 4, 'mp'), (18, 0, 'p'),
       (19, 2, 'mp'), (22, 4, 'p'), (23, 2, 'mp'), (24, 0, 'mp'), (25, 4, 'mp'), (26, 4, 'p'),
       (27, 0, 'mp'), (29, 4, 'p'), (31, 0, 'mp'), (33, 4, 'mp'), (34, 0, 'p'),
       (35, 0, 'mp'), (37, 0, 'mp'), (38, 0, 'mf'), (38, 4, 'f'),
       (39, 0, 'f'), (40, 0, 'ff'), (40, 6, 'f'), (41, 4, 'mf'), (42, 4, 'p'),
       (43, 0, 'mp'), (45, 4, 'p'), (46, 4, 'pp'), (47, 0, 'p'), (48, 4, 'pp'),
       (49, 2, 'p'), (50, 0, 'pp'), (51, 2, 'pp'), (52, 0, 'pp')]

PHRASES = [(1, 2), (3, 6), (7, 10), (11, 14), (15, 18), (19, 22), (23, 26), (27, 30), (31, 34), (35, 38), (39, 42),
           (43, 46), (47, 48), (49, 52)]

SECTIONS = [('intro', 2), ('A1', 8), ('A2', 8), ('B1', 8), ('A3', 8), ('build', 4), ('climax', 4), ('A4', 6),
            ('coda', 4)]


def bar(k: int) -> float:
    return (k - 1) * float(METER)


def tempo_plan(s: Song, score) -> None:
    """Phrase rubato (the feel's depth), ritardandi into the cadences / breaths, fermatas, tempo changes, the lilt."""
    F = G.feels[FEEL]
    score.rubato(s, depth=F['rubato'], seed='bar')
    s.fermata(bar(1) + 2.0, hold=1.5)                   # the opening chord rings
    s.ritardando((bar(2) + 2.0, bar(3)), to=0.85)
    for k in (6, 14, 22, 30):                           # the half-way breaths
        s.ritardando((bar(k) + 2.0, bar(k + 1)), to=0.88)
    for k in (10, 18, 26, 34):                          # cadences
        s.ritardando((bar(k) + 1.0, bar(k + 1)), to=0.8)
    s.set_tempo(bar(19), 64)                             # the bridge
    s.set_tempo(bar(27), 66)
    s.set_tempo(bar(35), 68)
    s.ritardando((bar(38) + 2.0, bar(39)), to=0.82)     # the inhale: Db7 instead of Bb7
    s.set_tempo(bar(39), 70)
    s.ritardando((bar(40) + 2.0, bar(42) + 3.0), to=0.7, a_tempo=False)
    s.fermata(bar(40) + 2.0, hold=1.0)                  # the peak rings
    s.fermata(bar(42) + 3.0, hold=1.5)                  # Db7sus4 waits at the door of G-flat
    s.set_tempo(bar(43), 62)
    s.ritardando((bar(48), bar(49)), to=0.8)
    s.set_tempo(bar(49), 60)
    s.ritardando((bar(50) + 2.0, bar(52)), to=0.75, a_tempo=False)
    s.fermata(bar(52) + 1.0, hold=3)
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
