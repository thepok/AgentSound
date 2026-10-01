"""Band preset demo: film_orchestra (hybrid=True) - an epic hybrid cue in D minor (24 bars, 100 BPM, ~1:00). Build:
    python -m agentsound build songs/_bands/film_orchestra

Only the preset (agentsound.bandlib.orchestra) plus ordinary composition code; the sections play through
orch.perform (articulations, velocities -> the live dynamics lane, early long notes).

  open   4  the braam (bass trombone, tuba, horns marcato on an open fifth + taikos + the synth sub), then the
            string ostinato (cellos / violas staccato 8ths accented 3+3+2) and the synth pulse; a lone oboe states
            the motif
  build  8  i - VI - III - VII (Dm Bb F C): the horns carry the theme, the choir 'aah' enters, taikos in a
            pattern, clarinets / bassoons / harp fill, everything crescendos; a cymbal roll into ...
  peak   8  ... the theme in violins (octaves, flutes on top) with the choir, trumpets and trombones in chords,
            horns in unison, timpani and taikos, the sub on every downbeat
  tail   4  the drop: violins tremolo pianissimo, a soft choir, the last braam and a ringing hit

Measured (report, 'film'): -15.3 LUFS-I, LRA 14.9 LU, TP -1.2 dBTP, 0 warnings, 0 clicks in the mix; open -21.8
(short-term max -17.4: the braam), build -19.5, peak -12.7, tail -20.4 LUFS; reverb -8.8 LU; sub +4.8 dB vs the film
reference.

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), VSCO 2 CE
(Versilian Studios, CC0: timpani, percussion, harp), MuseScore General SoundFont (taiko; MIT), Voxengo IM Reverbs.
"""
from agentsound import *
from agentsound import bands
from agentsound.bandlib import orchestra as orch
from agentsound.theory import note as nn

ANALYSIS = {'profile': 'film'}                       # == bands.film_orchestra(s).analysis
METADATA = {'artist': 'AgentSound', 'album': 'Band presets', 'genre': 'Soundtrack'}

W = 4
CHORDS = ['D', 'Bb', 'F', 'C']                       # i - VI - III - VII, two bars each in build and peak
ROOT = {'D': 'D', 'Bb': 'Bb', 'F': 'F', 'C': 'C'}
SUB = {'D': 'D1', 'Bb': 'F1', 'F': 'F1', 'C': 'C1'}     # the sub hit: 33-44 Hz (Bb takes its fifth: Bb0 is too low)
TRIAD = {'D': ['D', 'F', 'A'], 'Bb': ['Bb', 'D', 'F'], 'F': ['F', 'A', 'C'], 'C': ['C', 'E', 'G']}


def part(rows, scale=1.0) -> Clip:
    notes = []
    for i, bar in enumerate(rows):
        for t, d, p, v in bar:
            for q in (p if isinstance(p, (list, tuple)) else [p]):
                notes.append((i * W + t, d, q, max(1, min(127, round(v * scale)))))
    return Clip(notes, length=len(rows) * W)


def ostinato(roots, octave, vel, fifth=False):
    """8ths accented 3+3+2 on each bar's root (the fifth above for the violas)."""
    rows = []
    for r, v in zip(roots, vel):
        p = nn(f"{r}{octave}") + (7 if fifth else 0)
        rows.append([(k * 0.5, 0.35, p + (12 if k == 7 else 0), v + (14 if k in (0, 3, 6) else 0)) for k in range(8)])
    return rows


def pulse(roots, vel):
    return [[(k * 0.25, 0.2, nn(f"{r}2") + (12 if k % 2 else 0), v - (10 if k % 4 else 0)) for k in range(16)]
            for r, v in zip(roots, vel)]


def taiko(vel, fill=False):
    """One bar of the taiko pattern (low keys = big drums)."""
    bar = [(0, 1, 'C1', vel), (1.5, 0.5, 'G1', vel - 26), (2, 1, 'D2', vel - 14), (3, 0.5, 'G1', vel - 30),
           (3.5, 0.5, 'C2', vel - 20)]
    if fill:
        bar += [(3.25, 0.25, 'D2', vel - 24), (3.75, 0.25, 'D2', vel - 10)]
    return bar


def two_bars(seq):
    return [c for c in seq for _ in range(2)]


THEME = [[(0, 4, 'A4', 0)], [(0, 1.5, 'A4', 0), (1.5, 0.5, 'Bb4', 0), (2, 1, 'A4', 0), (3, 1, 'F4', 0)],
         [(0, 4, 'D5', 0)], [(0, 1.5, 'D5', 0), (1.5, 0.5, 'C5', 0), (2, 1, 'Bb4', 0), (3, 1, 'F4', 0)],
         [(0, 4, 'C5', 0)], [(0, 1, 'C5', 0), (1, 1, 'D5', 0), (2, 1, 'C5', 0), (3, 1, 'A4', 0)],
         [(0, 2, 'G4', 0), (2, 2, 'E4', 0)], [(0, 4, 'G4', 0)]]


def theme(transpose, vels):
    return [[(t, d, nn(p) + transpose, v) for t, d, p, _ in bar] for bar, v in zip(THEME, vels)]


def chords(voicings, vels, beats=W):
    return [[(0, beats, v, vel)] for v, vel in zip(voicings, vels)]


BUILD_V = [60, 64, 68, 72, 78, 84, 90, 96]
PEAK_V = [110, 108, 112, 110, 114, 112, 116, 118]
ROOTS8 = two_bars(CHORDS)


def build() -> Song:
    s = Song('Ascension', tempo=100, key='D minor', seed=9, tail=6)
    op, bu, pk, tl = (s.section('open', 4), s.section('build', 8), s.section('peak', 8), s.section('tail', 4))
    o = bands.film_orchestra(s, hybrid=True)
    P = lambda role, rows, sec, **kw: orch.perform(o, role, part(rows), sec, seed=sum(map(ord, role)), **kw)  # noqa

    # ---------------------------------------------------------------- open: the braam, the ostinato, the motif
    P('low_brass', [[(0, 3.5, ['D2', 'A2'], 120)]], op, articulations='marcato')
    P('tuba', [[(0, 3.5, 'D2', 118)]], op, articulations='marcato')
    P('horns', [[(0, 3.5, ['D3', 'A3'], 116)]], op, articulations='marcato')
    P('drums', [[(0, 2, 'C1', 124), (0, 2, 'G1', 110)]], op)
    P('sub', [[(0, 2, 'D1', 120)]], op)
    P('timpani', [[(0, 1, 'D2', 118)]], op, articulations='hit')
    P('cellos', [[]] + ostinato(['D'] * 3, 3, [50, 56, 62]), op, articulations='staccato')
    P('violas', [[]] * 2 + ostinato(['D'] * 2, 3, [50, 58], fifth=True), op, articulations='staccato')
    P('pulse', [[]] + pulse(['D'] * 3, [70, 76, 82]), op)
    P('basses', [[]] + [[(0, 12, 'D2', 50)]] + [[]] * 2, op)
    P('oboes', [[]] * 2 + [[(0, 1.5, 'A4', 100), (1.5, 0.5, 'Bb4', 96), (2, 1, 'A4', 100), (3, 1, 'F4', 92)],
                           [(0, 4, 'D4', 90)]], op)

    # ---------------------------------------------------------------- build: Dm Bb F C x2 bars, crescendo
    P('cellos', ostinato([ROOT[c] for c in ROOTS8], 2, [v - 4 for v in BUILD_V]), bu, articulations='staccato')
    P('violas', ostinato([ROOT[c] for c in ROOTS8], 3, [v - 8 for v in BUILD_V], fifth=True), bu, articulations='staccato')
    P('pulse', pulse([ROOT[c] for c in ROOTS8], [80 + k * 3 for k in range(8)]), bu)
    P('basses', chords([nn(ROOT[c] + '2') if ROOT[c] in ('C', 'D') else nn(ROOT[c] + '1') for c in ROOTS8],
                       BUILD_V), bu, shapes='cresc')
    P('horns', theme(-12, BUILD_V), bu)                              # the theme, horns in unison (A3 .. D4)
    P('choir', chords([[nn(p + '3') if p in ('F', 'G', 'A', 'Bb') else nn(p + '4') for p in TRIAD[c]]
                       for c in ROOTS8], [v - 10 for v in BUILD_V]), bu, shapes='cresc')
    P('clarinets', chords([[nn(TRIAD[c][1] + '4')] for c in ROOTS8], [v - 14 for v in BUILD_V]), bu)
    P('bassoons', chords([[nn(ROOT[c] + '3')] for c in ROOTS8], [v - 10 for v in BUILD_V]), bu)
    P('harp', [[(k * 0.5, 1.5, nn(TRIAD[c][k % 3] + ('3' if k < 3 else '4')), v - 18) for k in range(8)]
               for c, v in zip(ROOTS8, BUILD_V)], bu)
    P('drums', [taiko(70 + k * 5, fill=(k == 7)) for k in range(8)], bu)
    P('sub', [[(0, 1.5, SUB[c], 90)] if k % 2 == 0 else [] for k, c in enumerate(ROOTS8)], bu)
    P('timpani', [[]] * 7 + [[(0, 4, 'A2', 90)]], bu, articulations='roll')
    k = orch.PERCUSSION_KEYS
    o.percussion.note(k['cymbal_roll'], pk.start - 5.8, 8, 100)       # its swell peaks 3.5 s (5.8 beats) in

    # ---------------------------------------------------------------- peak: tutti theme
    P('violins1', theme(12, PEAK_V), pk)                             # A5 .. D6
    P('violins2', theme(0, [v - 6 for v in PEAK_V]), pk)             # A4 .. D5: octaves
    P('flutes', theme(12, [v - 12 for v in PEAK_V]), pk)
    P('choir', theme(0, [v - 10 for v in PEAK_V]), pk)
    P('horns', theme(-12, [v - 6 for v in PEAK_V]), pk)
    P('violas', chords([[nn(TRIAD[c][2] + '4')] for c in ROOTS8], [v - 8 for v in PEAK_V]), pk)
    P('cellos', ostinato([ROOT[c] for c in ROOTS8], 2, [v - 20 for v in PEAK_V]), pk, articulations='staccato')
    P('basses', chords([nn(ROOT[c] + '2') if ROOT[c] in ('C', 'D') else nn(ROOT[c] + '1') for c in ROOTS8],
                       PEAK_V), pk)
    P('trumpets', chords([[nn(p + '4') for p in TRIAD[c]] for c in ROOTS8], [v - 16 for v in PEAK_V]), pk)
    P('trombones', chords([[nn(p + '3') for p in TRIAD[c]] for c in ROOTS8], [v - 14 for v in PEAK_V]), pk)
    P('low_brass', chords([nn(ROOT[c] + '2') for c in ROOTS8], [v - 12 for v in PEAK_V]), pk)
    P('tuba', chords([nn(ROOT[c] + '2') if ROOT[c] in ('C', 'D') else nn(ROOT[c] + '1') for c in ROOTS8],
                     [v - 14 for v in PEAK_V]), pk)
    P('clarinets', chords([[nn(p + '4') for p in TRIAD[c][:2]] for c in ROOTS8], [v - 16 for v in PEAK_V]), pk)
    P('bassoons', chords([[nn(ROOT[c] + '3')] for c in ROOTS8], [v - 14 for v in PEAK_V]), pk)
    P('pulse', pulse([ROOT[c] for c in ROOTS8], [100] * 8), pk)
    P('drums', [taiko(112, fill=(i % 4 == 3)) for i in range(8)], pk)
    P('sub', [[(0, 1.5, SUB[c], 118)] for c in ROOTS8], pk)
    P('timpani', [[(0, 1, 'D2' if c in ('D', 'Bb') else 'A2', 118), (2, 1, 'A2', 96)] for c in ROOTS8], pk,
      articulations='hit')
    for b in (0, 4):
        o.percussion.note(k['crash'], pk.bar(b), 4, 116).note(k['bass_drum'], pk.bar(b), 2, 120)

    # ---------------------------------------------------------------- tail: the drop and the last hit
    P('violins1', [[(0, 4, ['D5', 'A5'], 44)], [(0, 4, ['D5', 'A5'], 40)], [(0, 4, ['E5', 'A5'], 36)], []], tl,
      articulations='tremolo')
    P('choir', [[(0, 8, ['D4', 'F4', 'A4'], 46)], [], [(0, 3.5, ['C#4', 'E4', 'A4'], 40)], []], tl)
    P('basses', [[(0, 12, 'D2', 44)], [], [], []], tl)
    P('low_brass', [[]] * 3 + [[(0, 4, ['D2', 'A2'], 124)]], tl, articulations='marcato')
    P('tuba', [[]] * 3 + [[(0, 4, 'D2', 120)]], tl, articulations='marcato')
    P('horns', [[]] * 3 + [[(0, 4, ['D3', 'A3'], 118)]], tl, articulations='marcato')
    P('drums', [[]] * 3 + [[(0, 2, 'C1', 127), (0, 2, 'G1', 116)]], tl)
    P('sub', [[]] * 3 + [[(0, 3, 'D1', 124)]], tl)
    P('timpani', [[]] * 3 + [[(0, 1, 'D2', 124)]], tl, articulations='hit')
    o.percussion.note(k['tam_tam'], tl.bar(3), 6, 110)
    orch.ring(o, tl.bar(3), length=2, db=4, roles=[r for r in o.roles if r not in ('drums', 'sub')])
    return s
