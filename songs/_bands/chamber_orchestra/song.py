"""Band preset demo: chamber_orchestra - a Classical-era Allegro moderato in G major (24 bars, 104 BPM, ~0:58). Build:
    python -m agentsound build songs/_bands/chamber_orchestra

Only the preset (agentsound.bandlib.orchestra) plus ordinary composition code; every part goes through orch.perform
(articulations, velocities -> the live dynamics lane, early long notes, a section's timing).

  A   8  the theme in violins I (4 + 4: a half cadence, then the tonic), violins II and violas in staccato 8ths,
         cellos and basses in staccato quarters, the horns' open-fifth pedal, the oboe doubling the answer
  B   8  a wind chorale (flutes, oboes, clarinets, bassoons in pairs, horns) over pizzicato strings; then the strings
         answer legato, crescendo onto the dominant with a timpani roll
  C   8  tutti forte: the theme in octaves, winds doubling, timpani on the downbeats; a tremolo crescendo on D7, two
         staccato tutti chords and the final chord ringing into the hall

Measured (report, 'classical'): -20.9 LUFS-I, LRA 15.0 LU, 0 warnings, 0 clicks; A -29.4, B -24.4 (short-term
max -19.4: the strings' crescendo onto D7), C -17.7 LUFS; reverb -7.5 LU, width 25 % above 150 Hz, lows correlation
0.93.

CREDITS: VSCO 2 CE (Versilian Studios, CC0), Voxengo IM Reverbs (Musikvereinsaal).
"""
from agentsound import *
from agentsound import bands
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'classical'}                  # == bands.chamber_orchestra(s).analysis
METADATA = {'artist': 'AgentSound', 'album': 'Band presets', 'genre': 'Classical'}

W = 4
STRINGS = ('violins1', 'violins2', 'violas', 'cellos', 'basses')
LOW_STRINGS = STRINGS[1:]


def part(rows, scale=1.0) -> Clip:
    """rows: one list per bar of (beat, beats, pitch or [pitches], velocity)."""
    notes = []
    for i, bar in enumerate(rows):
        for t, d, p, v in bar:
            for q in (p if isinstance(p, (list, tuple)) else [p]):
                notes.append((i * W + t, d, q, max(1, min(127, round(v * scale)))))
    return Clip(notes, length=len(rows) * W)


def held(chords, vels, beats=W):
    return [[(0, beats, c, v)] if c else [] for c, v in zip(chords, vels)]


def pulses(per_bar, vels, step=0.5, dur=0.35):
    """Repeated notes (8ths / quarters): per bar a pitch (or [first half, second half])."""
    rows = []
    for p, v in zip(per_bar, vels):
        halves = p if isinstance(p, list) else [p, p]
        rows.append([(k * step, dur, halves[int(k * step >= 2)], v - (8 if k % 2 else 0))
                     for k in range(int(W / step))])
    return rows


# ------------------------------------------------------------------ A: G | D7 | G | Am7 D || G | C Am | G/D D7 | G
A_MEL = [[(0, 1, 'G4', 70), (1, 1, 'B4', 72), (2, 1.5, 'D5', 78), (3.5, 0.5, 'B4', 70)],
         [(0, 1, 'C5', 74), (1, 1, 'A4', 70), (2, 1.5, 'F#4', 68), (3.5, 0.5, 'A4', 66)],
         [(0, 1, 'B4', 72), (1, 1, 'D5', 76), (2, 1.5, 'G5', 84), (3.5, 0.5, 'F#5', 78)],
         [(0, 1, 'E5', 80), (1, 1, 'C5', 74), (2, 2, 'A4', 70)],
         [(0, 1, 'G4', 72), (1, 1, 'B4', 74), (2, 1.5, 'D5', 80), (3.5, 0.5, 'G5', 84)],
         [(0, 1.5, 'G5', 86), (1.5, 0.5, 'E5', 78), (2, 1, 'C5', 76), (3, 1, 'E5', 78)],
         [(0, 1, 'D5', 78), (1, 1, 'B4', 74), (2, 1, 'A4', 72), (3, 1, 'C5', 74)],
         [(0, 2, 'B4', 72), (2, 2, 'G4', 64)]]
A = {
    'violins1': A_MEL,
    'violins2': pulses(['D4', 'C4', 'D4', ['C4', 'A3'], 'D4', ['E4', 'C4'], ['D4', 'C4'], 'D4'], [58] * 8),
    'violas': pulses(['B3', 'A3', 'B3', ['A3', 'F#3'], 'B3', ['C4', 'A3'], ['B3', 'A3'], 'B3'], [56] * 8),
    'cellos': pulses(['G2', 'F#2', 'G2', ['A2', 'D2'], 'G2', ['C3', 'A2'], ['D2', 'D2'], 'G2'], [66] * 8, 1, 0.5),
    'basses': pulses(['G1', 'F#1', 'G1', ['A1', 'D2'], 'G1', ['C2', 'A1'], ['D2', 'D2'], 'G1'], [64] * 8, 1, 0.5),
    'horns': [[(0, 8, ['G3', 'D4'], 44)], [], [(0, 8, ['G3', 'D4'], 44)], [], [(0, 4, ['G3', 'D4'], 46)],
              [(0, 4, ['G3', 'E4'], 48)], [(0, 4, ['A3', 'D4'], 48)], [(0, 4, ['G3', 'D4'], 44)]],
    'oboes': [[]] * 4 + held(['D5', 'E5', 'D5', 'D5'], [56, 58, 58, 52]),     # a wind 'fill' over the answer
    'timpani': [[], [], [], [(2, 1, 'D3', 70)], [], [], [(0, 1, 'D3', 72)], [(0, 1, 'G2', 76)]],
}
def split(a, b, va, vb=None):
    """A bar of two half-note chords."""
    return [(0, 2, a, va), (2, 2, b, va if vb is None else vb)]


def offbeats(p, v, p2=None):
    """Pizzicato chords on beats 2 and 4."""
    return [(1, 0.5, p, v), (3, 0.5, p if p2 is None else p2, v - 4)]


def two_hits(p, v):
    """Two short tutti chords (beats 1 and 3)."""
    return [(0, 1, p, v), (2, 1, p, v)]


# ------------------------------------------------------------------ B: C | G/B | Am D7 | G || Em | C | Am7 | D7
B = {
    'flutes': [[(0, 4, ['E5', 'G5'], 60)], [(0, 4, ['D5', 'G5'], 62)], split(['C5', 'E5'], ['C5', 'F#5'], 64),
               [(0, 4, ['B4', 'D5'], 58)]],
    'oboes': [[(0, 4, 'C5', 60)], [(0, 4, 'B4', 62)], split('A4', 'A4', 64), [(0, 4, 'G4', 56)]],
    'clarinets': [[(0, 4, ['E4', 'G4'], 58)], [(0, 4, ['D4', 'G4'], 60)], split(['C4', 'E4'], ['D4', 'C5'], 62),
                  [(0, 4, ['B3', 'D4'], 56)]],
    'bassoons': [[(0, 4, ['C3', 'G3'], 60)], [(0, 4, ['B2', 'G3'], 60)], split(['A2', 'E3'], ['D3', 'A3'], 62),
                 [(0, 4, ['G2', 'D3'], 56)]] + held(['E3', 'C3', 'A2', 'D3'], [62, 68, 76, 86]),
    'horns': [[(0, 4, ['C4', 'E4'], 54)], [(0, 4, ['B3', 'D4'], 54)], split(['A3', 'C4'], ['A3', 'C4'], 56),
              [(0, 4, ['G3', 'D4'], 50)], [], [], [(0, 4, ['A3', 'E4'], 70)], [(0, 4, ['A3', 'D4'], 84)]],
    'violins2': [offbeats(['E4', 'G4'], 58), offbeats(['D4', 'G4'], 58), offbeats(['C4', 'E4'], 58, ['C4', 'F#4']),
                 [(1, 0.5, ['B3', 'D4'], 56)]] + held(['G4', 'G4', 'G4', 'C5'], [62, 68, 76, 86]),
    'violas': [offbeats('C4', 56), offbeats('B3', 56), offbeats('A3', 56), [(1, 0.5, 'G3', 54)]] +
              held(['E4', 'E4', 'E4', 'D4'], [60, 66, 74, 84]),
    'cellos': [[(0, 0.5, 'C3', 66), (2, 0.5, 'G2', 60)], [(0, 0.5, 'B2', 66), (2, 0.5, 'G2', 60)],
               [(0, 0.5, 'A2', 66), (2, 0.5, 'D3', 62)], [(0, 0.5, 'G2', 62)]] +
              held(['E3', 'C3', 'A2', 'D3'], [62, 68, 76, 86]),
    'basses': [[(0, 0.5, 'C2', 64), (2, 0.5, 'G1', 58)], [(0, 0.5, 'B1', 64), (2, 0.5, 'G1', 58)],
               [(0, 0.5, 'A1', 64), (2, 0.5, 'D2', 60)], [(0, 0.5, 'G1', 60)]] +
              held(['E2', 'C2', 'A1', 'D2'], [60, 66, 74, 84]),
    'violins1': [[]] * 4 + [[(0, 2, 'B4', 62), (2, 1, 'C5', 64), (3, 1, 'D5', 66)], [(0, 2, 'E5', 70), (2, 2, 'G5', 74)],
                            [(0, 1, 'E5', 76), (1, 1, 'C5', 76), (2, 2, 'A5', 82)],
                            [(0, 2, 'C6', 90), (2, 1, 'A5', 86), (3, 1, 'F#5', 84)]],
    'timpani': [[], [], [], [], [], [], [], [(0, 4, 'D3', 70)]],
}
# ------------------------------------------------------------------ C: the theme tutti, then C | D7 (tremolo) | G G | G
C_MEL = [[(t, d, p, v + 26) for t, d, p, v in bar] for bar in A_MEL[:4]] + [
    [(0, 1, 'E5', 104), (1, 1, 'G5', 106), (2, 2, 'C6', 110)], [(0, 4, 'A5', 96)], two_hits('G5', 112),
    [(0, 4, 'G5', 114)]]


def octave_down(rows):
    """The line an octave lower (notes that would fall under the violin's G3 stay)."""
    from agentsound.theory import note as nn
    return [[(t, d, nn(p) - 12 if nn(p) - 12 >= nn('G3') else nn(p), v - 4) for t, d, p, v in bar] for bar in rows]


def softer(rows, db):
    return [[(t, d, p, v - db) for t, d, p, v in bar] for bar in rows]


C = {
    'violins1': C_MEL,
    'violins2': octave_down(C_MEL[:5]) + [[(0, 4, ['C5', 'F#5'], 96)], two_hits('B4', 110),
                                          [(0, 4, ['B4', 'D5'], 112)]],
    'violas': pulses(['B3', 'A3', 'B3', ['C4', 'A3']], [84] * 4) +
              [[(0, 4, 'C4', 96)], [(0, 4, 'A3', 90)], two_hits('D4', 108), [(0, 4, 'D4', 110)]],
    'cellos': pulses(['G2', 'F#2', 'G2', ['A2', 'D2']], [96] * 4, 1, 0.5) +
              [[(0, 1, 'C3', 100), (1, 1, 'C3', 92), (2, 1, 'E3', 98), (3, 1, 'C3', 92)], [(0, 4, 'D3', 90)],
               two_hits('G2', 112), [(0, 4, 'G2', 112)]],
    'basses': pulses(['G1', 'F#1', 'G1', ['A1', 'D2']], [94] * 4, 1, 0.5) +
              [[(0, 1, 'C2', 98), (2, 1, 'C2', 96)], [(0, 4, 'D2', 88)], two_hits('G1', 110), [(0, 4, 'G1', 110)]],
    'flutes': softer(C_MEL[:5], 8) + [[(0, 4, ['F#5', 'A5'], 94)], two_hits(['G5', 'B5'], 104),
                                      [(0, 4, ['G5', 'B5'], 106)]],
    'oboes': softer(C_MEL[:5], 10) + [[(0, 4, 'A5', 90)], two_hits('D5', 102), [(0, 4, 'D5', 104)]],
    'clarinets': held([['B4', 'D5'], ['A4', 'C5'], ['B4', 'D5'], ['A4', 'C5'], ['G4', 'C5'], ['A4', 'C5']],
                      [86, 86, 88, 88, 92, 88]) + [two_hits(['G4', 'B4'], 104), [(0, 4, ['G4', 'B4'], 106)]],
    'bassoons': pulses(['G2', 'F#2', 'G2', ['A2', 'D2']], [88] * 4, 1, 0.5) +
                [[(0, 4, ['C3', 'G3'], 94)], [(0, 4, ['D3', 'C4'], 88)], two_hits(['G2', 'D3'], 104),
                 [(0, 4, ['G2', 'D3'], 106)]],
    'horns': [[(0, 8, ['G3', 'D4'], 78)], [], [(0, 8, ['G3', 'D4'], 80)], [], [(0, 4, ['G3', 'E4'], 84)],
              [(0, 4, ['A3', 'D4'], 80)], two_hits(['G3', 'D4'], 104), [(0, 4, ['G3', 'D4'], 106)]],
    'timpani': [[(0, 1, 'G2', 100)], [(0, 1, 'D3', 92)], [(0, 1, 'G2', 100)], [(2, 1, 'D3', 96)], [(0, 1, 'G2', 96)],
                [(0, 4, 'D3', 80)], [(0, 1, 'G2', 118), (2, 1, 'G2', 116)], [(0, 1, 'G2', 120)]],
}


def build() -> Song:
    s = Song('Allegro moderato', tempo=104, key='G major', seed=5, tail=4)
    secs = {n: s.section(n, bars=8) for n in 'ABC'}
    s.rubato((secs['B'].bar(4), secs['B'].end), depth=0.025, phrase='lean')
    s.ritardando((secs['C'].bar(6), secs['C'].end), to=0.8)
    s.fermata(secs['C'].bar(7), hold=2)

    o = bands.chamber_orchestra(s)
    for name, parts in (('A', A), ('B', B), ('C', C)):
        sec = secs[name]
        for role, rows in parts.items():
            c = part(rows, 1.1 if name == 'A' else 1.0)                  # A: mp - mf
            if name == 'A' and role in LOW_STRINGS:
                c = c.articulate('staccato')                              # the accompaniment 8ths / quarters
            if name == 'B' and role in LOW_STRINGS:
                c = c.articulate('pizzicato', span=(0, 16))               # under the wind chorale
            if name == 'C':
                if role in ('violas', 'cellos', 'basses', 'bassoons'):
                    c = c.articulate('staccato', span=(0, 16))
                if role in STRINGS:
                    c = c.articulate('tremolo', span=(20, 24))            # the D7 crescendo
                if role != 'timpani':
                    c = c.articulate('staccato', span=(24, 28))           # two short tutti chords
            if role == 'timpani':
                c = c.articulate('hit')
                if name == 'B':
                    c = c.articulate('roll', span=(28, 32))
                if name == 'C':
                    c = c.articulate('roll', span=(20, 24))
            # B: the strings' answer crescendos note by note onto the dominant; C: the tremolo D7 grows p -> ff
            if name == 'B':
                shapes = (lambda n: 'cresc' if n.start >= 15.5 else None)
            elif name == 'C':
                shapes = (lambda n: 'cresc' if 19.5 <= n.start < 24 else ('accent' if n.start >= 24 else None))
            else:
                shapes = 'auto'
            orch.perform(o, role, c, sec, shapes=shapes, seed=sum(map(ord, role + name)))
    orch.ring(o, secs['C'].bar(7), length=2, db=5)
    return s
