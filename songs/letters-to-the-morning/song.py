"""Letters to the Morning - an original new-age / pop-classical piece for solo grand piano in A-flat major.
Build: python -m agentsound build songs/letters-to-the-morning

In the style of the gentle solo-piano pop of the 2000s (a singable right-hand tune over flowing broken chords,
pop progressions with a few tender colour turns) - every note written here, no borrowed melody or figure.
4/4, 75 BPM (the return 70, the coda 66), rubato, ~3:50.

  intro   1-4    the left hand alone (two bars), then the hook's head high and soft
  A1      5-12   the theme (Ab4-F5), p: two-bar question / answer, a rest at every phrase end
  A2      13-20  the theme again, its answer higher (Ab5), a cadence on I
  B1      21-28  the hook (vi-IV-I-V): three 8ths rising into a held note, a falling sigh; the Fb -> Eb turn over
                 Dbm6 (the borrowed iv) at its end
  inter   29-32  the bed thins to quarter notes, echoes of the hook in the treble, whole bars of air
  A3      33-40  the theme with sixths / thirds under its long notes, turning to C7/E (V of vi)
  build   41-48  F minor, the melody an octave up, climbing (Gbmaj7 = bVII), the left hand widening, an inhale
  climax  49-56  the hook in chords, its peaks raised (Db6, Eb6, F6 - ff at bar 53), bass octaves, then a
                 ritardando into a held Eb7 (fermata)
  A4      57-64  the theme plain and soft over a thinned left hand, a deceptive cadence to Fm
  coda    65-69  the hook's head in the treble over Dbmaj7 - Dbm6, once more in the middle, a rolled Ab(add9)

Notation is written by hand (right hand: romantic.score; left hand: broken-chord figures per bar from the chord
symbols below); the romantic pianist plays the right hand (touch, lean on long notes, cantabile, melody rubato),
the tempo breathes per phrase with ritardandi into the cadences.

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (salon IR).
"""
import math

from agentsound import *
from agentsound import bands, jazz
from agentsound import romantic as rom
from agentsound.theory import chord as _chord

ANALYSIS = {'profile': 'piano'}
METADATA = {'title': 'Letters to the Morning', 'artist': 'AgentSound', 'album': 'Solo Piano',
            'genre': 'New Age', 'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#f3e3c8', '#8fa9c4'], 'title': 'LETTERS TO THE MORNING',
         'subtitle': 'solo piano - AgentSound', 'seed': 41}

TEMPO = 75

# the mix (MIX.md): one instrument, the pianist balances the hands (the left hand 6-9 dB under the melody per
# section); the left hand's low mids dipped a little more where both hands meet (the coda's final chords)
MIX = {'eq': {'comp': [{'freq': 400, 'gain': -2.0, 'q': 1.0}]}}

# the master (MASTER.md): the preset's gentle chain (glue 1.3:1, tape without wow, a slow limiter), driven 1.5 dB
# harder than its default (quiet intro / interlude on a phone), the pedalled bass 2 dB down, a little air above the
# presence band (no 2-5 kHz lift)
MASTER = {'drive': 6.5, 'eq': {'peak2.freq': 100, 'peak2.gain': -2.0, 'peak2.q': 1.0,
                                'peak3.freq': 3200, 'peak3.gain': -1.0, 'peak3.q': 0.8,
                                'high.freq': 9000, 'high.gain': 2.5}}

# ------------------------------------------------------------------------------------------------ right hand
# one entry per bar (4/4), notation (agentsound.notation): C5/4. = a dotted quarter, r = rest, [..] = notes together
RH = {
    # intro
    1: 'r/1', 2: 'r/1',
    3: 'r/8 C6/8 F6/8 G6/8 Ab6/2',
    4: 'G6/8 F6/8 Eb6/2 r/4',
    # A1
    5: 'r/4 Ab4/8 Bb4/8 C5/4. Bb4/8',
    6: 'Eb5/4 Db5/8 C5/8 Bb4/2',
    7: 'r/4 Ab4/8 C5/8 F5/4. Eb5/8',
    8: 'Eb5/2. r/4',
    9: 'r/4 Ab4/8 Bb4/8 C5/4. Db5/8',
    10: 'Eb5/4 F5/8 Eb5/8 Db5/4 C5/4',
    11: 'Db5/4.^turn C5/8 Bb4/4 Ab4/8 Bb4/8',
    12: 'Bb4/2. r/4',
    # A2 - the answer higher, sixths / thirds under its long notes
    13: 'r/4 Ab4/8 Bb4/8 C5/4. Bb4/8',
    14: 'Eb5/4 Db5/8 C5/8 Bb4/2',
    15: 'r/4 Ab4/8 C5/8 [Ab4 F5]/4. G5/8',
    16: '[C5 Ab5]/2. r/4',
    17: 'r/4 Eb5/8 F5/8 [Eb5 G5]/4. Ab5/8',
    18: '[Ab4 F5]/4 Eb5/8 Db5/8 [Ab4 C5]/4 Db5/4',
    19: 'Db5/4.^turn C5/8 Bb4/4 G4/4',
    20: 'Ab4/2. r/4',
    # B1 - the hook (its second half: IV - I6 - ii - iv - V, octaves under the held notes)
    21: 'r/8 C5/8 F5/8 G5/8 Ab5/2',
    22: 'G5/8 F5/8 Eb5/8 F5/8 Db5/2',
    23: 'r/8 C5/8 Eb5/8 Ab5/8 C6/2',
    24: 'Bb5/8 Ab5/8 G5/8 Ab5/8 Bb5/2',
    25: 'r/8 C5/8 F5/8 G5/8 [Ab4 Ab5]/2',
    26: 'G5/8 F5/8 Eb5/8 F5/8 [Ab4 Ab5]/4. F5/8',
    27: '[Ab4 F5]/4 Db5/4 [Ab4 Fb5]/4 [G4 Eb5]/4',
    28: 'Eb5/2. r/4',
    # interlude: air
    29: 'r/8 C6/8 Eb6/8 F6/8 Eb6/2',
    30: 'r/1',
    31: 'r/8 Ab5/8 C6/8 F6/8 Eb6/2',
    32: 'r/1',
    # A3 - sixths and thirds under the long notes
    33: 'r/4 Ab4/8 Bb4/8 [Ab4 C5]/4. Bb4/8',
    34: '[G4 Eb5]/4 Db5/8 C5/8 [G4 Bb4]/2',
    35: 'r/4 Ab4/8 C5/8 [Ab4 F5]/4. Eb5/8',
    36: '[Ab4 Eb5]/2. r/4',
    37: 'r/4 Ab4/8 Bb4/8 [Ab4 C5]/4. Db5/8',
    38: '[Ab4 Eb5]/4 F5/8 Eb5/8 [F4 Db5]/4 C5/4',
    39: 'Db5/4. C5/8 Bb4/4 Ab4/4',
    40: 'G4/2 r/4 C5/8 E5/8',
    # build - F minor, an octave up, climbing
    41: 'F5/4. Eb5/8 F5/4 Ab5/4',
    42: 'G5/4 F5/8 Eb5/8 F5/2',
    43: 'r/8 Db5/8 F5/8 Ab5/8 Bb5/4. Ab5/8',
    44: 'G5/4. F5/8 E5/2',
    45: 'r/8 C5/8 F5/8 Ab5/8 C6/4. Bb5/8',
    46: 'Ab5/4 G5/8 F5/8 Ab5/4 Db6/4',
    47: 'Db6/4. Bb5/8 Gb5/4 F5/8 Gb5/8',
    48: 'Ab5/2 G5/4 r/4',
    # climax - the hook in chords, the peaks raised
    49: 'r/8 C5/8 F5/8 G5/8 [Ab4 C5 Ab5]/2',
    50: 'G5/8 F5/8 Eb5/8 F5/8 [Db5 F5 Db6]/2',
    51: 'r/8 C5/8 Eb5/8 Ab5/8 [Ab5 C6 Eb6]/2',
    52: 'Db6/8 C6/8 Bb5/8 C6/8 [G5 Bb5 Eb6]/2',
    53: 'r/8 Ab5/8 C6/8 Eb6/8 [Ab5 C6 F6]/2',
    54: 'Eb6/8 Db6/8 C6/8 Db6/8 [F5 Ab5 F6]/4. Db6/8',
    55: '[F5 Db6]/4 [F5 Bb5]/4 [Ab5 Fb6]/4 [Ab5 Eb6]/4',
    56: '[Eb5 Ab5 Db6]/2 [Eb5 G5 Db6]/2',
    # A4 - the theme plain and soft, its answer bent (Eb5-F5, a turn on F5)
    57: 'r/4 Ab4/8 Bb4/8 C5/4. Bb4/8',
    58: 'Eb5/4 Db5/8 C5/8 Bb4/2',
    59: 'r/4 Ab4/8 C5/8 F5/4.^turn Eb5/8',
    60: 'Eb5/2. r/4',
    61: 'r/4 Ab4/8 Bb4/8 C5/4. Eb5/8',
    62: 'F5/4 Eb5/8 Db5/8 [Ab4 Db5]/4 C5/4',
    63: 'Db5/4. C5/8 Bb4/4 G4/4',
    64: 'Ab4/2. r/4',
    # coda
    65: 'r/8 Ab5/8 C6/8 Eb6/8 F6/2',
    66: 'r/4 Fb6/4 Eb6/2',
    67: 'r/8 C5/8 Eb5/8 Ab5/8 C6/2',
    68: 'Bb5/2. r/4',
    69: '[C5 Eb5 Ab5 C6 Eb6]/1^roll(110)',
}

# ------------------------------------------------------------------------------------------------ left hand
# per bar: 'CHORD:figure' (or two half-bar entries). The chord gives a bass in Db2-C3 and a ladder of chord tones
# above it (0 = bass, 1 = the next chord tone a 4th-6th up, 2, 3 = the 10th, 4, 5 ...); 'x' = the chord's colour
# tone (7th / 9th / 6th) above step 2, 'o' = the bass with its octave below.  Figures in 8ths, '-' holds.
FIG = {
    'flow':  '0 1 2 3 4 3 2 1',        # up to the 12th and back: the flowing broken chord
    'rock':  '0 1 3 1 2 1 3 1',        # rocking on the 10th
    'color': '0 1 2 x 3 x 2 1',        # with the 9th / 7th inside
    'half':  '0 1 3 - - - - -',        # three notes, then the bar rings (a phrase end breathes)
    'open':  '0 - 1 3 - - - -',        # sparse
    'quart': '0 - 1 - 3 - 1 -',        # quarter notes: the thinned hand
    'lilt':  '0 - 1 3 2 - 3 1',        # a quarter, then 8ths: the hand rocks instead of running
    'ring':  '0 1 2 3 - - - -',        # up, then the bar rings under a held melody note
    'colorhalf': '0 1 x 3 - - - -',    # the colour tone, then ring
    'sweep': 'o 1 2 3 4 5 4 3 2 3 4 5 4 3 2 1',   # the climax peaks: 16ths, two octaves up and down
    'up':    '0 1 2 3 4 5 - -',        # climbing into the next section
    'big':   'o 1 2 3 4 5 4 2',        # the climax: bass octave, two octaves of chord
    'roll':  'R - - - - - - -',        # a rolled chord, held
    'h4':    '0 1 3 1',                # half-bar figures (two chords in a bar)
    'h4up':  '0 1 2 3',
    'hB':    '0 1 3 -',
    'hR':    'R - - -',                # a rolled half-bar chord, held (under a fermata)
    'bigh':  'o 1 3 4',
}

LH = {
    1: 'Abadd9:flow', 2: 'Dbmaj7:lilt', 3: 'Fm7:rock', 4: 'Ebsus4:hB Eb:hB',
    5: 'Ab:rock', 6: 'Eb/G:lilt', 7: 'Fm7:flow', 8: 'Dbadd9:half',
    9: 'Ab/C:rock', 10: 'Db:flow', 11: 'Bbm7:lilt', 12: 'Ebsus4:hB Eb:hB',
    13: 'Ab:flow', 14: 'Eb/G:rock', 15: 'Fm7:flow', 16: 'Dbadd9:colorhalf',
    17: 'Ab/C:lilt', 18: 'Dbmaj7:flow', 19: 'Bbm7:h4 Eb7:h4', 20: 'Ab:half',
    21: 'Fm:flow', 22: 'Db:lilt', 23: 'Ab:flow', 24: 'Eb:ring',
    25: 'Dbmaj7:flow', 26: 'Ab/C:rock', 27: 'Bbm7:h4 Dbm6:h4', 28: 'Ebsus4:hB Eb:hB',
    29: 'Abadd9:open', 30: 'Dbmaj7:quart', 31: 'Fm7:open', 32: 'Ebsus4:roll',
    33: 'Ab:rock', 34: 'Eb/G:lilt', 35: 'Fm7:rock', 36: 'Dbadd9:half',
    37: 'Ab/C:flow', 38: 'Db:lilt', 39: 'Bbm7:flow', 40: 'C7/E:up',
    41: 'Fm:flow', 42: 'Db:lilt', 43: 'Bbm7:flow', 44: 'C7sus4:h4up C7:hB',
    45: 'Fm:big', 46: 'Dbmaj7:big', 47: 'Gbmaj7:big', 48: 'Ebsus4:h4up Eb:hB',
    49: 'Dbmaj7:big', 50: 'Eb/Db:big', 51: 'Ab/C:sweep', 52: 'Eb/Bb:big',
    53: 'Fm:sweep', 54: 'Db:big', 55: 'Bbm7:bigh Dbm6:bigh', 56: 'Ebsus4:hB Eb7:hR',
    57: 'Ab:quart', 58: 'Eb/G:quart', 59: 'Fm7:quart', 60: 'Dbadd9:half',
    61: 'Ab/C:lilt', 62: 'Db:rock', 63: 'Bbm7:h4 Eb7:h4', 64: 'Fm7:half',
    65: 'Dbmaj7:open', 66: 'Dbm6:open', 67: 'Ab/Eb:rock', 68: 'Ebsus4:hB Eb:hB', 69: 'Abadd9:roll',
}

# dynamics: (bar, position in 8ths, level) - both hands (the left at a gentler slope)
DYN = [(1, 0, 'pp'), (3, 0, 'p'), (4, 4, 'pp'),
       (5, 0, 'p'), (9, 0, 'p'), (10, 4, 'mp'), (12, 4, 'p'),
       (13, 0, 'p'), (15, 0, 'mp'), (17, 0, 'mp'), (18, 0, 'mf'), (20, 0, 'mp'),
       (21, 0, 'mp'), (23, 0, 'mf'), (24, 4, 'mp'), (25, 0, 'mp'), (26, 0, 'mf'), (27, 4, 'mp'), (28, 4, 'p'),
       (29, 0, 'pp'), (32, 0, 'pp'),
       (33, 0, 'p'), (37, 0, 'p'), (39, 0, 'mp'), (40, 4, 'mp'),
       (41, 0, 'mp'), (43, 0, 'mf'), (45, 0, 'mf'), (47, 0, 'f'), (48, 4, 'mf'),
       (49, 0, 'f'), (51, 0, 'f'), (53, 0, 'ff'), (54, 4, 'f'), (55, 0, 'f'), (56, 0, 'mf'), (56, 4, 'mp'),
       (57, 0, 'p'), (61, 0, 'p'), (62, 0, 'mp'), (63, 4, 'p'), (64, 4, 'pp'),
       (65, 0, 'pp'), (67, 0, 'p'), (68, 0, 'pp'), (69, 0, 'pp')]

PHRASES = [(1, 2), (3, 4), (5, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 40),
           (41, 44), (45, 48), (49, 52), (53, 56), (57, 60), (61, 64), (65, 69)]

SCORE = rom.score(RH, None, DYN, meter='4/4', unit='1/8', key='Ab major', phrases=PHRASES)

SECTIONS = [('intro', 4), ('A1', 8), ('A2', 8), ('B1', 8), ('inter', 4), ('A3', 8), ('build', 8), ('climax', 8),
            ('A4', 8), ('coda', 5)]


def bar(k: int) -> float:
    return (k - 1) * 4.0


# ------------------------------------------------------------------------------------------------ the left hand

def ladder(sym: str) -> tuple[list[int], int, int]:
    """(bass + chord tones above it, the colour tone above step 2, the bass) for a chord symbol: the bass in
    Db2-C3 (lower ones boom under the pedal), the ladder from the triad (or sus) tones from a 4th above the bass up two octaves."""
    c = _chord(sym)
    bpc = c.bass_pc
    bass = 37 + (bpc - 1) % 12                     # Db2 .. C3
    triad = [(c.root + i) % 12 for i in c.intervals[:3]]
    colour = [(c.root + i) % 12 for i in c.intervals[3:]]
    up = [p for p in range(bass + 5, bass + 30) if p % 12 in triad]
    lad = [bass] + up[:6]
    x = None
    if colour:
        x = next(p for p in range(lad[2] + 1, lad[2] + 13) if p % 12 == colour[0])
    return lad, x, bass


def _cap(p: int) -> int:
    """The left hand stays under the melody (G4 at most)."""
    return p - 12 if p > 67 else p


def figure(sym: str, fig: str, at: float, span: float, vel: float, rng) -> list:
    lad, x, bass = ladder(sym)
    toks = FIG[fig].split()
    step = span / len(toks)
    out = []
    idx = [i for i, t in enumerate(toks) if t != '-']
    ups = [_cap(lad[3] if t == 'x' and x is None else x if t == 'x' else lad[int(t)])
           for t in toks if t not in ('-', 'R', 'o', '0')] or [lad[1]]
    lo, hi = min(ups), max(ups)
    for j, i in enumerate(idx):
        t = toks[i]
        start = at + i * step
        nxt = idx[j + 1] if j + 1 < len(idx) else len(toks)
        dur = (nxt - i) * step
        jit = 1.0 + (rng.random() - 0.5) * 0.08
        if t == 'R':                               # a rolled, held chord from the bass
            for k, p in enumerate(lad[:4]):
                out.append(Note(start + k * 0.06, span - k * 0.06, p, vel * (1.12 if k == 0 else 0.9) * jit))
            continue
        if t == 'o':
            out.append(Note(start, span, bass - 12, vel * 1.05 * jit))
            out.append(Note(start, span, bass, vel * 1.02 * jit))
            continue
        p = _cap(lad[3] if t == 'x' and x is None else x if t == 'x' else lad[int(t)])
        if i == 0 and t == '0':
            v, d = vel * 1.02, span                # the bass carries and rings through the chord
        else:                                      # the figure crests on its top note
            v = vel * (0.8 + 0.24 * ((p - lo) / (hi - lo) if hi > lo else 0.5))
            d = max(dur, 1.0)                      # finger legato: each note held into the next ones
        out.append(Note(start, d, p, v * jit))
    return out


def left_hand(rng) -> tuple[Clip, list]:
    notes_, changes = [], []
    for k in sorted(LH):
        parts = LH[k].split()
        span = 4.0 / len(parts)
        for i, part in enumerate(parts):
            sym, fig = part.split(':')
            at = bar(k) + i * span
            changes.append(at)
            notes_ += figure(sym, fig, at, span, 41, rng)
    # a swell over every phrase (the hand leans into its middle, relaxes at its end): +-8 %
    def swell(n):
        for a, b in PHRASES:
            if bar(a) <= n.start < bar(b + 1):
                x = (n.start - bar(a)) / (bar(b + 1) - bar(a))
                return n._replace(vel=n.vel * (0.92 + 0.16 * math.sin(math.pi * x)))
        return n
    lh = Clip._raw([swell(n) for n in notes_], bar(70))
    marks = [(bar(b) + pos * 0.5, rom.LEVELS[lv] ** 0.6) for b, pos, lv in DYN]
    return rom.dynamics(lh, marks), changes


# ------------------------------------------------------------------------------------------------ the tempo

def tempo_plan(s: Song) -> None:
    """Phrase rubato (the singer's breath: on through the phrase, broader into its end), ritardandi into the
    cadences and the breaths, the climax held on a fermata, a slow ending."""
    SCORE.rubato(s, depth=0.05, shapes=('breath', 'breath', 'lean'), seed='bar')
    for k in (8, 16, 36, 60):                      # the rests at the theme's half-way points: a small breath
        s.ritardando((bar(k) + 1.0, bar(k) + 4.0), to=0.9)
    for k in (12, 20, 28, 40, 64):                 # cadences
        s.ritardando((bar(k) + 1.0, bar(k) + 4.0), to=0.8)
    s.ritardando((bar(32), bar(33)), to=0.82)      # the interlude's last bar
    s.ritardando((bar(48) + 2.0, bar(49)), to=0.85)  # the inhale before the climax
    s.ritardando((bar(55), bar(56) + 2.0), to=0.72, a_tempo=False)
    s.fermata(bar(56) + 2.5, hold=2.5)            # after the roll: the chord rings, the roll is not stretched
    s.set_tempo(bar(57), 70)                       # the return: calmer
    s.set_tempo(bar(65), 66)
    s.ritardando((bar(67), bar(69)), to=0.75, a_tempo=False)
    s.fermata(bar(69) + 1.0, hold=3)
    s.lilt((bar(1), bar(69)), beats={3: 0.03}, jitter=0.03, seed=41)


# ------------------------------------------------------------------------------------------------ build

def build() -> Song:
    s = Song('Letters to the Morning', tempo=TEMPO, key='Ab major', seed=41, tail=7)
    for name, n in SECTIONS:
        s.section(name, bars=n)
    tempo_plan(s)

    feel = jazz.Feel(s.tempo, ratio=0.5, beats_per_bar=4)
    b = bands.make('solo_piano', s, feel=feel, master_gain=MASTER['drive'])
    rh_t, lh_t = b.piano, b.comp
    s.master.fx['eq'].set(**MASTER['eq'])
    # the pedalled broken chords pile up 80-250 Hz (the preset's left hand is voiced for jazz shells): a broad
    # low shelf, and a little out of the melody's 1-2 kHz
    lh_t.add_fx(fx.eq({'low.freq': 220, 'low.gain': -4.0, 'peak1.freq': 1400, 'peak1.gain': -2.0, 'peak1.q': 0.8,
                       'peak2.freq': 100, 'peak2.gain': -2.5, 'peak2.q': 1.0}))

    import random
    lh, changes = left_hand(random.Random(41))
    lh_t.play(lh, 0)

    # inner=0.78: the notes under the melody in the right hand's chords sing softer (voice the top)
    SCORE.perform(s, rh_t, None, pedal=False, touch=dict(lo=52, hi=100), breath=0.35, cap=106, inner=0.78)

    ped = rom.pedal_changes(changes, end=bar(70) + 6, bpm=s.tempo_at, lift_ms=110)
    for t in (rh_t, lh_t):
        t.automate('instrument.pedal', ped)
    return s
