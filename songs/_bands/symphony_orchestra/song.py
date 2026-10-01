"""Band preset demo: symphony_orchestra - a Romantic tutti climax in D major (24 bars, 72 BPM, ~1:25). Build:
    python -m agentsound build songs/_bands/symphony_orchestra

Only the preset (agentsound.bandlib.orchestra) plus ordinary composition code. Every section plays through
orch.perform (velocities -> the live dynamics lane, articulations, early long notes); the crescendo into the climax is
one orch.dynamics curve over the strings, the one hall rings on the last chord (orch.ring).

  intro  4  pp: violins II / violas tremolo on a D pedal, a timpani roll, the horns' call
  theme  8  mp -> mf: violins I sing, violins II / violas / horns hold the harmony, cellos walk down under basses
            pizzicato, the harp arpeggiates; flutes double the second phrase an octave up, clarinets and bassoons join
  build  4  crescendo p -> ff: a rising sequence over G - Em - A7sus - A7, strings tremolo, brass entering bar by bar,
            timpani roll and cymbal roll into ...
  climax 4  ... the tutti arrival: violins in octaves with flutes and oboes, horns in unison with a counter-theme,
            trumpet and trombone chords, tuba and basses, timpani, bass drum and crash on the downbeat
  close  4  subito p: strings alone with the minor iv (Gm), celesta sparkle, a ritardando and a ringing final chord

Measured (report, 'classical'): -20.6 LUFS-I, LRA 17.0 LU, 0 warnings, 0 clicks in the mix (one soft SSO loop
point in the violins II stem, masked); intro -32.7, theme -26.6, build -19.3, climax -16.4 (short-term max -15.7),
close -32.5 LUFS: pp -> ff -> subito p; reverb -10.0 LU; balance vs the classical reference within +-5 dB (mid +4.9).

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), VSCO 2 CE
(Versilian Studios, CC0: timpani, percussion, harp), Voxengo IM Reverbs (Musikvereinsaal).
"""
from agentsound import *
from agentsound import bands
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'classical'}                  # == bands.symphony_orchestra(s).analysis
METADATA = {'artist': 'AgentSound', 'album': 'Band presets', 'genre': 'Classical'}

W = 4  # beats per bar


def part(rows, vel_scale=1.0) -> Clip:
    """rows: one list per bar of (beat, beats, pitch or [pitches], velocity) -> a Clip (chords = several notes)."""
    notes = []
    for i, bar in enumerate(rows):
        for t, d, p, v in bar:
            for q in (p if isinstance(p, (list, tuple)) else [p]):
                notes.append((i * W + t, d, q, max(1, min(127, round(v * vel_scale)))))
    return Clip(notes, length=len(rows) * W)


def whole(chords, vel, beats=W) -> list:
    """One held chord / note per bar."""
    return [[(0, beats, c, v)] for c, v in zip(chords, vel if isinstance(vel, list) else [vel] * len(chords))]


def arp(chords, vel, pattern=(0, 1, 2, 3, 2, 1, 2, 1), step=0.5) -> list:
    """Harp / celesta arpeggios: per bar, the chord's pitches in `pattern` order, one every `step` beats."""
    rows = []
    for c, v in zip(chords, vel if isinstance(vel, list) else [vel] * len(chords)):
        rows.append([(k * step, step * 2.5, c[i % len(c)], v - (6 if k % 2 else 0)) for k, i in enumerate(pattern)])
    return rows


REST = [[]]

# ------------------------------------------------------------------ the parts, section by section (sounding pitch)
# intro: D | D | Bm/D | D
INTRO = {
    'violins2': whole([['A4', 'D5'], ['A4', 'D5'], ['B4', 'D5'], ['A4', 'D5']], [36, 36, 40, 34]),
    'violas': whole(['F#4', 'F#4', 'F#4', 'F#4'], [40, 44, 48, 40]),
    'cellos': whole(['D3'] * 4, [42, 44, 46, 42]),
    'basses': [[], []] + whole(['D2'] * 2, [46, 42]),                  # enter under the horns' answer
    'horns': REST + [[(0, 1, 'A3', 56), (1, 1, 'D4', 60), (2, 2, 'F#4', 64)],
                     [(0, 2, 'F#4', 62), (2, 1, 'E4', 56), (3, 1, 'D4', 54)], [(0, 4, 'D4', 48)]],
    'timpani': [[(0, 16, 'D2', 50)], [], [], []],
}
# theme: D | A/C# | Bm | F#m/A | G | D/F# | Em7 A7 | D
MEL = [[(0, 2, 'F#5', 66), (2, 1, 'E5', 62), (3, 1, 'D5', 62)], [(0, 3, 'E5', 68), (3, 1, 'A4', 62)],
       [(0, 1, 'B4', 66), (1, 1, 'C#5', 68), (2, 1, 'D5', 70), (3, 1, 'F#5', 74)], [(0, 4, 'E5', 72)],
       [(0, 1.5, 'D5', 74), (1.5, 0.5, 'E5', 72), (2, 1, 'F#5', 78), (3, 1, 'G5', 80)], [(0, 3, 'A5', 86), (3, 1, 'F#5', 78)],
       [(0, 1, 'G5', 80), (1, 1, 'F#5', 76), (2, 1, 'E5', 74), (3, 1, 'C#5', 72)], [(0, 4, 'D5', 70)]]
THEME = {
    'violins1': MEL,
    'violins2': whole(['A4', 'A4', 'F#4', 'C#5', 'B4', ['A4'], 'G4', 'F#4'], [58, 60, 62, 64, 68, 72, 70, 62]),
    'violas': whole(['F#4', 'E4', 'D4', 'C#4', 'D4', 'D4', 'E4', 'D4'], [56, 58, 60, 62, 66, 70, 68, 60]),
    'cellos': whole(['D3', 'C#3', 'B2', 'A2', 'G2', 'F#2'], [62, 62, 64, 66, 70, 72]) +
              [[(0, 2, 'E2', 70), (2, 2, 'A2', 70)], [(0, 4, 'D2', 64)]],
    'basses': [[(0, 1, r, 70), (2, 1, r, 64)] for r in ('D2', 'C#2', 'B1', 'A1', 'G1', 'F#1')] +
              [[(0, 1, 'E1', 72), (2, 1, 'A1', 70)], [(0, 1, 'D1', 66), (2, 1, 'D1', 58)]],
    'horns': whole([['A3', 'D4'], ['A3', 'C#4'], ['B3', 'D4'], ['A3', 'C#4'], ['G3', 'B3'], ['A3', 'D4']],
                   [50, 50, 52, 54, 58, 62]) + [[(0, 2, ['B3', 'E4'], 60), (2, 2, ['A3', 'C#4'], 60)],
                                                 [(0, 4, ['A3', 'D4'], 54)]],
    'flutes': [[]] * 4 + [[(t, d, p, v) for t, d, p, v in [(0, 1.5, 'D6', 66), (1.5, 0.5, 'E6', 64),
                                                          (2, 1, 'F#6', 70), (3, 1, 'G6', 72)]],
                          [(0, 3, 'A6', 76), (3, 1, 'F#6', 70)],
                          [(0, 1, 'G6', 72), (1, 1, 'F#6', 70), (2, 1, 'E6', 68), (3, 1, 'C#6', 66)], [(0, 4, 'D6', 62)]],
    'clarinets': [[]] * 4 + whole(['B4', 'A4', 'G4', 'F#4'], [60, 64, 62, 56]),
    'bassoons': [[]] * 4 + whole(['G2', 'F#2'], [62, 64]) + [[(0, 2, 'E2', 62), (2, 2, 'A2', 62)], [(0, 4, 'D2', 56)]],
    'harp': arp([['D3', 'A3', 'D4', 'F#4'], ['C#3', 'A3', 'C#4', 'E4'], ['B2', 'F#3', 'B3', 'D4'],
                 ['A2', 'E3', 'A3', 'C#4'], ['G2', 'D3', 'G3', 'B3'], ['F#2', 'D3', 'A3', 'D4'],
                 ['E2', 'B2', 'G3', 'E4'], ['D2', 'A2', 'F#3', 'D4']], [58, 58, 60, 60, 64, 66, 64, 58]),
}
# build: G | Em/G | A7sus4 | A7   (crescendo p -> ff)
BUILD = {
    'violins1': [[(0, 1, 'B4', 72), (1, 1, 'D5', 76), (2, 2, 'G5', 80)], [(0, 1, 'E5', 84), (1, 1, 'G5', 88), (2, 2, 'B5', 92)],
                 [(0, 2, 'A5', 96), (2, 2, 'D6', 100)], [(0, 2, 'C#6', 104), (2, 2, 'E6', 110)]],
    'violins2': whole([['G4', 'B4'], ['G4', 'B4'], ['A4', 'D5'], ['G4', 'C#5']], [70, 80, 92, 104]),
    'violas': whole(['D4', 'E4', 'E4', 'E4'], [70, 80, 92, 104]),
    'cellos': whole(['G2', 'G2', 'A2', 'A2'], [74, 84, 96, 108]),
    'basses': whole(['G1', 'G1', 'A1', 'A1'], [74, 84, 96, 108]),
    'horns': whole([['G3', 'B3', 'D4'], ['G3', 'B3', 'E4'], ['A3', 'D4', 'E4'], ['A3', 'C#4', 'E4']], [66, 76, 86, 96]),
    'trumpets': [[], [], [(0, 4, ['A4', 'D5'], 82)], [(0, 4, ['A4', 'C#5', 'E5'], 94)]],
    'trombones': [[], [(0, 4, ['G2', 'B2', 'E3'], 70)], [(0, 4, ['A2', 'D3', 'E3'], 82)],
                  [(0, 4, ['A2', 'C#3', 'E3'], 94)]],
    'tuba': [[], [], [(0, 4, 'A1', 80)], [(0, 4, 'A1', 94)]],
    'flutes': [[(0, 1, 'B5', 68), (1, 1, 'D6', 72), (2, 2, 'G6', 76)], [(0, 1, 'E6', 80), (1, 1, 'G6', 84), (2, 2, 'B6', 88)],
               [(0, 4, 'A6', 94)], [(0, 4, 'A6', 104)]],
    'oboes': [[(0, 1, 'B4', 70), (1, 1, 'D5', 74), (2, 2, 'G5', 78)], [(0, 1, 'E5', 82), (1, 1, 'G5', 86), (2, 2, 'B5', 90)],
              [(0, 2, 'A5', 94), (2, 2, 'D6', 98)], [(0, 2, 'C#6', 102), (2, 2, 'E6', 106)]],
    'clarinets': whole(['D5', 'E5', 'E5', 'E5'], [66, 76, 88, 100]),
    'bassoons': whole(['G2', 'G2', 'A2', 'A2'], [70, 80, 92, 104]),
    'timpani': [[], [], [(0, 8, 'A2', 90)], []],
    # the harp's glissando up into the climax (a fast D-major scale over the last two beats)
    'harp': [[], [], [], [(2 + k * 0.125, 0.5, p, 70 + k)
                          for k, p in enumerate(['A2', 'B2', 'C#3', 'D3', 'E3', 'F#3', 'G3', 'A3', 'B3', 'C#4', 'D4',
                                                 'E4', 'F#4', 'G4', 'A4', 'C#5'])]],
}
# climax: D | F#m/C# | Bm | G A7   (ff; the brass written one dynamic under the strings)
CMEL = [[(0, 1.5, 'F#5', 116), (1.5, 0.5, 'G5', 110), (2, 2, 'A5', 116)], [(0, 1, 'A5', 112), (1, 1, 'B5', 114), (2, 2, 'C#6', 118)],
        [(0, 3, 'D6', 120), (3, 1, 'B5', 110)], [(0, 2, 'A5', 112), (2, 1, 'G5', 106), (3, 1, 'E5', 104)]]
CLIMAX = {
    'violins1': CMEL,
    'violins2': [[(t, d, p.replace('5', '4').replace('6', '5'), v - 4) for t, d, p, v in bar] for bar in CMEL],
    'violas': [[(0, 4, 'F#4', 108)], [(0, 4, 'E4', 108)], [(0, 4, 'F#4', 110)], [(0, 2, 'D4', 106), (2, 2, 'C#4', 104)]],
    'cellos': whole(['D3', 'C#3', 'B2'], [114, 112, 112]) + [[(0, 2, 'G2', 110), (2, 2, 'A2', 110)]],
    'basses': whole(['D2', 'C#2', 'B1'], [114, 112, 112]) + [[(0, 2, 'G1', 110), (2, 2, 'A1', 110)]],
    'horns': [[(0, 2, 'A3', 104), (2, 1, 'D4', 104), (3, 1, 'F#4', 106)], [(0, 3, 'E4', 106), (3, 1, 'C#4', 100)],
              [(0, 2, 'D4', 106), (2, 2, 'F#4', 108)], [(0, 2, 'E4', 104), (2, 2, 'C#4', 100)]],
    'trumpets': [[(0, 4, ['A4', 'D5', 'F#5'], 100)], [(0, 4, ['A4', 'C#5', 'F#5'], 98)], [(0, 4, ['B4', 'D5', 'F#5'], 100)],
                 [(0, 2, ['B4', 'D5', 'G5'], 98), (2, 2, ['A4', 'C#5', 'E5'], 96)]],
    'trombones': [[(0, 4, ['D3', 'F#3', 'A3'], 100)], [(0, 4, ['C#3', 'F#3', 'A3'], 98)], [(0, 4, ['B2', 'D3', 'F#3'], 100)],
                  [(0, 2, ['G2', 'B2', 'D3'], 98), (2, 2, ['A2', 'C#3', 'E3'], 96)]],
    'tuba': whole(['D2', 'C#2', 'B1'], [98, 96, 98]) + [[(0, 2, 'G1', 96), (2, 2, 'A1', 94)]],
    'flutes': CMEL,
    'oboes': [[(0, 4, 'A5', 106)], [(0, 4, 'A5', 106)], [(0, 4, 'F#5', 108)], [(0, 2, 'G5', 104), (2, 2, 'E5', 100)]],
    'clarinets': whole(['D5', 'C#5', 'D5'], [104, 104, 106]) + [[(0, 2, 'D5', 102), (2, 2, 'C#5', 100)]],
    'bassoons': whole(['D3', 'C#3', 'B2'], [106, 104, 106]) + [[(0, 2, 'G2', 104), (2, 2, 'A2', 102)]],
    'timpani': [[(0, 1, 'D2', 124), (2, 1, 'A2', 104)], [(0, 1, 'A2', 110)], [(0, 1, 'D2', 114), (2, 1, 'D2', 96)],
                [(2, 0.5, 'A2', 112), (2.5, 0.5, 'A2', 96), (3, 0.5, 'A2', 104), (3.5, 0.5, 'A2', 116)]],
    'harp': arp([['D3', 'A3', 'D4', 'F#4', 'A4'], ['C#3', 'A3', 'C#4', 'F#4', 'A4'], ['B2', 'F#3', 'B3', 'D4', 'F#4'],
                 ['G2', 'D3', 'G3', 'B3', 'D4']], [96, 94, 96, 92], pattern=(0, 1, 2, 3, 4, 3, 2, 1)),
}
# close: D | G/D | Gm/D | D   (subito p, ritardando, the final chord rings)
CLOSE = {
    'violins1': [[(0, 4, 'F#5', 52)], [(0, 2, 'E5', 50), (2, 2, 'D5', 48)], [(0, 2, 'D5', 46), (2, 2, 'Bb4', 44)],
                 [(0, 4, 'A4', 36)]],
    'violins2': whole(['A4', 'B4', 'G4', 'F#4'], [46, 44, 42, 32]),
    'violas': whole(['D4', 'D4', 'D4', 'D4'], [44, 42, 40, 30]),
    'cellos': whole(['D3', 'D3', 'D3', 'D2'], [46, 44, 42, 32]),
    'basses': whole(['D2', 'D2', 'D2', 'D2'], [44, 42, 40, 30]),
    'horns': [[], [], [(0, 4, ['G3', 'Bb3', 'D4'], 44)], [(0, 4, ['F#3', 'A3', 'D4'], 36)]],
    'celesta': arp([['D6', 'F#6', 'A6', 'D7'], ['D6', 'G6', 'B6', 'D7'], ['D6', 'G6', 'Bb6', 'D7'], ['D6', 'F#6', 'A6']],
                   [70, 66, 62, 56], pattern=(0, 1, 2, 3, 2, 1, 2, 3)),
    'harp': [[], [], [], [(k * 0.1, 4, p, 56) for k, p in enumerate(['D2', 'A2', 'F#3', 'D4', 'A4'])]],
    'timpani': [[], [], [], [(0, 4, 'D2', 34)]],
}

ROLLS = {'intro': [0], 'build': [2], 'close': [3]}   # bars (per section) whose timpani notes are rolls


def build() -> Song:
    s = Song('Symphonic climax', tempo=72, key='D major', seed=3, tail=6)
    secs = {n: s.section(n, bars=b) for n, b in (('intro', 4), ('theme', 8), ('build', 4), ('climax', 4), ('close', 4))}
    s.rubato(secs['theme'], depth=0.03, phrase='arch')
    s.ritardando((secs['close'].bar(2), secs['close'].end), to=0.75)
    s.fermata(secs['close'].bar(3), hold=2)

    o = bands.symphony_orchestra(s)
    for name, parts in (('intro', INTRO), ('theme', THEME), ('build', BUILD), ('climax', CLIMAX), ('close', CLOSE)):
        sec = secs[name]
        for role, rows in parts.items():
            c = part(rows, 0.86 if name == 'build' else 1.0)    # the build grows from p to f: the climax is ff
            if role in ('violins2', 'violas') and name in ('intro', 'build'):
                c = c.articulate('tremolo')
            if role == 'basses' and name == 'theme':
                c = c.articulate('pizzicato')
            if role == 'timpani':
                c = c.articulate('hit')
                for b in ROLLS.get(name, []):
                    c = c.articulate('roll', span=(b * W, b * W + W))
            if role == 'trumpets' and name == 'climax':
                c = c.articulate('marcato', span=(0, 1))
            if name == 'build' and role not in ('harp', 'timpani'):
                orch.perform(o, role, c, sec, shapes='cresc')          # each held chord grows into the next
            else:
                orch.perform(o, role, c, sec, seed=sum(map(ord, role)))
    # percussion: cymbal roll swelling into the climax, bass drum + crash on the downbeat, a softer crash in bar 3
    k = orch.PERCUSSION_KEYS
    cl = secs['climax']
    o.percussion.note(k['cymbal_roll'], cl.start - 4.2, 6, 96)       # its swell peaks 3.5 s (4.2 beats) in
    o.percussion.note(k['bass_drum'], cl.start, 2, 118).note(k['crash'], cl.start, 4, 116)
    o.percussion.note(k['crash'], cl.bar(2), 4, 92).note(k['bass_drum'], cl.bar(2), 2, 96)
    o.percussion.note(k['triangle'], secs['close'].bar(3), 2, 70)
    orch.ring(o, secs['close'].bar(3), length=3, db=5)
    return s
