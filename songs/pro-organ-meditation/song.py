"""Meditation in D-flat - an original romantic organ Meditation / Elevation (a hand-composed 'pro' reference).
Build: python -m agentsound build songs/pro-organ-meditation

Every note written by hand (no organ_vocab / endless generators), played by the shared organist (agentsound.organist)
on the Burea church_organ. Form ABA' + coda, q=54 (see NOTES.md):

  intro   b1-2    Db pedal point, the accompaniment alone (Gedakt 8' + Koppelflojt 4', Brostverk)
  A       b3-10   the tune on the swell oboe (Skalmeja 8' + Rorflojt 8', tremulant): a rising sixth Ab-Db-F, a sigh,
                  half cadence on V (b6); a' climbs to Bb5 over V7/IV - IV6, cadential 6/4, a 4-3 suspension, PAC
  B       b11-24  the solo moves to the Brostverk Krumhorn, the chords to the swell strings (Salicional, box breathing):
                  Bb minor, deceptive cadence F7 -> Gb; Gb major (the head motif Bb-Db-Gb, a lydian F over Cb);
                  chromatic-mediant turn Gb -> D (F# held); G maj7 -> A major climax (box open); the A6 chord planes
                  down a semitone onto an Ab dominant pedal; the solo falls silent while a chromatic inner voice
                  sinks Eb-D-Db-C (Ab7 b5 - sus4 - Ab7), the motif's pickup, fermata
  A'      b25-35  the oboe returns, varied: a turned ii7 bar, the cadential 6/4 reached from Ab5, the climax on Db6;
                  deceptive cadence V -> vi, IV -> the minor plagal iv6 (Bb-A-Ab in the tenor), V7 4-3, PAC
  coda    b36-38  the head motif echoed on the flutes over Db (IV6/4, minor iv6/4), the strings dying in the
                  closing box
Pedal: Subbas 16' alone throughout (long notes, the Db pedal points). The swell box (oboe, strings) opens into every
phrase peak and closes at its cadence; the coda closes it to nothing.
"""
from agentsound import *
from agentsound import bands, organist
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'organ'}
METADATA = {'title': 'Meditation in D-flat', 'artist': 'AgentSound', 'album': 'Organ References',
            'genre': 'Classical', 'year': 2026}
# the solo stop a little over its accompaniment (a stronger oboe), the Subbas a little under the manuals
MIX = {'trim': {'oboe': 3.5, 'flute': 2.0, 'strings': -2.0, 'pedal_soft': -2.0}}

_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def P(name: str) -> int:
    """'Db4' -> 61 (C4 = 60; Cb4 = 59, B#3 = 60)."""
    letter, rest = name[0], name[1:]
    acc = 0
    while rest and rest[0] in '#b':
        acc += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    return _PC[letter] + acc + 12 * (int(rest) + 1)


def line(text: str, start: float) -> list:
    """'Ab4:1.5 Db5:.5 | r:1 ...' (bars '|' are only for the eye) -> [(start, dur, pitch)]."""
    out, t = [], float(start)
    for tok in text.replace('|', ' ').split():
        name, d = tok.split(':')
        d = float(d)
        if name != 'r':
            out.append((t, d, P(name)))
        t += d
    return out


def chords(rows, start: float, n: int = 3) -> list:
    """Voice-led accompaniment rows [(dur, top, middle, low), ...] -> n line voices; a pitch repeated in the same voice
    across rows is HELD (the organist keeps common tones down)."""
    voices = [[] for _ in range(n)]
    t = float(start)
    for dur, *ps in rows:
        for i, nm in enumerate(ps):
            p = P(nm)
            v = voices[i]
            if v and v[-1][2] == p and abs(v[-1][0] + v[-1][1] - t) < 1e-6:
                v[-1] = (v[-1][0], v[-1][1] + dur, p)
            else:
                v.append((t, float(dur), p))
        t += dur
    return voices


def bar(n: int) -> float:
    """Bar n (1-based, 4/4) -> its first beat."""
    return 4.0 * (n - 1)


# ---------------------------------------------------------------------------------------------------- the score
# A: the oboe tune (b3-10)
MEL_A = ('Ab4:1.5 Db5:.5 F5:2 | Eb5:1 Db5:.5 C5:.5 Db5:1 Bb4:1 | F5:1.5 Eb5:.5 Db5:1 Eb5:1 | F5:2 Eb5:1.5 r:.5 | '
         'Ab4:1.5 Db5:.5 F5:1 Ab5:1 | Bb5:2 Ab5:.5 Gb5:1.5 | F5:1.5 Eb5:.5 Db5:1 C5:1 | Db5:3')
# intro + A accompaniment (flute, b1-10): I IV6/4 | I Iadd9 | I | ii7 vi7 | IVmaj7 ii7 | I6/4 V7 | I V7/IV | IV6 ii7 |
# I6/4 V7 (no 3rd: the 4-3 is the tune's) | I
ACC_A = [(2, 'F4', 'Db4', 'Ab3'), (2, 'Gb4', 'Db4', 'Bb3'),
         (2, 'F4', 'Db4', 'Ab3'), (2, 'Eb4', 'Db4', 'Ab3'),
         (4, 'F4', 'Db4', 'Ab3'),
         (2, 'Gb4', 'Db4', 'Bb3'), (2, 'F4', 'Db4', 'Ab3'),
         (2, 'F4', 'Db4', 'Bb3'), (2, 'Gb4', 'Db4', 'Bb3'),
         (2, 'F4', 'Db4', 'Ab3'), (2, 'Gb4', 'C4', 'Ab3'),
         (4, 'F4', 'Db4', 'Ab3'),
         (4, 'Gb4', 'Db4', 'Bb3'),
         (2, 'F4', 'Db4', 'Ab3'), (2, 'Gb4', 'Eb4', 'Ab3'),
         (4, 'F4', 'Db4', 'Ab3')]
PED_A = 'Db3:12 | Eb3:2 Bb2:2 | Gb2:2 Eb3:2 | Ab2:4 | Db3:2 Cb3:2 | Bb2:3 Eb3:1 | Ab2:4 | Db3:4'

# B: the flute solo (b11-24)
MEL_B = ('r:1 F4:1 Bb4:1.5 C5:.5 | Db5:2 C5:1 Bb4:1 | A4:1.5 Bb4:.5 C5:1 Eb5:1 | Db5:3 r:1 | '
         'Bb4:1.5 Db5:.5 Gb5:2 | F5:1 Eb5:1.5 Db5:.5 Cb5:1 | Bb4:2 A4:2 | B4:1 C#5:1 D5:1 F#5:1 | '
         'C#5:1.5 E5:.5 A5:2 | G#5:1 F#5:1 E5:2 | F5:2 Eb5:1.5 Db5:.5 | C5:3 r:1 | r:4 | r:1.5 Eb4:.5 Ab4:1 C5:1')
# Bbm | Gbmaj7 Ebm6 | F7 | Gb (deceptive) | Gb Gb6 | Cb Abm7 | Gb6 D | D6 Gmaj7 | A | F#m7 | Ab6 Ab7 |
# Ab7 Ab7(b5) | Ab7sus4 Ab7 | Ab7 - the strings' chromatic inner voice Eb-D-Db-C over the Ab pedal
ACC_B = [(4, 'Db4', 'Bb3', 'F3'),
         (2, 'Db4', 'Bb3', 'F3'), (2, 'Eb4', 'Bb3', 'Gb3'),
         (4, 'Eb4', 'C4', 'F3'),
         (4, 'Db4', 'Bb3', 'Gb3'),
         (2, 'Db4', 'Bb3', 'Gb3'), (2, 'Eb4', 'Bb3', 'Gb3'),
         (4, 'Eb4', 'Cb4', 'Gb3'),
         (2, 'Db4', 'Bb3', 'Gb3'), (2, 'D4', 'A3', 'F#3'),
         (4, 'D4', 'B3', 'F#3'),
         (4, 'E4', 'C#4', 'A3'),
         (4, 'E4', 'C#4', 'A3'),
         (2, 'Eb4', 'C4', 'Ab3'), (2, 'Eb4', 'C4', 'Gb3'),
         (2, 'Eb4', 'C4', 'Gb3'), (2, 'D4', 'Gb3', 'Eb3'),
         (2, 'Db4', 'Gb3', 'Eb3'), (2, 'C4', 'Gb3', 'Eb3'),
         (4, 'C4', 'Gb3', 'Eb3')]
PED_B = 'Bb2:4 | Gb2:2 Eb3:2 | F2:4 | Gb2:8 | Cb3:2 Ab2:2 | Bb2:2 D3:4 G2:2 | A2:4 | F#2:4 | Ab2:16'

# A': the oboe returns (b25-35)
MEL_A2 = ('Ab4:1.5 Db5:.5 F5:2 | Eb5:1 Db5:.5 C5:.5 Db5:1 Bb4:1 | F5:1.5 Eb5:.5 Db5:.5 Eb5:.5 Gb5:1 | '
          'Ab5:1 F5:1 Eb5:1.5 r:.5 | Ab4:1.5 Db5:.5 F5:1 Ab5:1 | Db6:1.5 Bb5:.5 Ab5:1 Gb5:1 | '
          'F5:1.5 Eb5:.5 Db5:1 C5:1 | Db5:2 Eb5:1 F5:1 | Gb5:3 F5:1 | Eb5:2 Db5:1 C5:1 | Db5:4')
# as A to b31; b32 vi vi7 (deceptive) | IV iv6 (Bbb) | V7 (4-3 in the tune) | I
ACC_A2 = [(4, 'F4', 'Db4', 'Ab3'),
          (2, 'Gb4', 'Db4', 'Bb3'), (2, 'F4', 'Db4', 'Ab3'),
          (2, 'F4', 'Db4', 'Bb3'), (2, 'Gb4', 'Db4', 'Bb3'),
          (2, 'F4', 'Db4', 'Ab3'), (2, 'Gb4', 'C4', 'Ab3'),
          (4, 'F4', 'Db4', 'Ab3'),
          (4, 'Gb4', 'Db4', 'Bb3'),
          (2, 'F4', 'Db4', 'Ab3'), (2, 'Gb4', 'Eb4', 'Ab3'),
          (2, 'F4', 'Db4', 'Bb3'), (2, 'F4', 'Db4', 'Ab3'),
          (2, 'Gb4', 'Db4', 'Bb3'), (2, 'Eb4', 'Db4', 'A3'),
          (4, 'Gb4', 'Eb4', 'Ab3'),
          (4, 'F4', 'Db4', 'Ab3')]
PED_A2 = ('Db3:4 | Eb3:2 Bb2:2 | Gb2:2 Eb3:2 | Ab2:4 | Db3:2 Cb3:2 | Bb2:3 Eb3:1 | Ab2:4 | Bb2:4 | Gb2:4 | Ab2:4 | '
          'Db3:4')

# coda (b36-38): the motif on the flutes over a Db pedal; IV6/4 - minor iv6/4 - I in the strings
MEL_C = 'Ab4:1.5 Db5:.5 F5:2 | Eb5:2 Db5:2.5'
ACC_C = [(2, 'F4', 'Db4', 'Ab3'), (2, 'Gb4', 'Db4', 'Bb3'),
         (2, 'Gb4', 'Db4', 'A3'), (2, 'F4', 'Db4', 'Ab3'),
         (4, 'F4', 'Db4', 'Ab3')]
PED_C = 'Db3:10.5'


def build() -> Song:
    s = Song('Meditation in D-flat', tempo=54, key='Db major', seed=7, tail=10)
    intro = s.section('intro', bars=2)
    a = s.section('A', bars=8)
    b = s.section('B', bars=14)
    a2 = s.section('A2', bars=11)
    coda = s.section('coda', bars=3)

    # ---- time: the cadences broaden, the middle breathes, fermatas before the return and at the end
    s.ritardando((bar(9) + 2, bar(11)), to=0.88)                 # A's PAC
    s.ritardando((bar(13) + 2, bar(15)), to=0.9)                 # the deceptive cadence
    s.rubato((bar(15), bar(21)), depth=0.035, phrase='breath')
    s.ritardando((bar(23), bar(24) + 3), to=0.8)                 # the chromatic descent
    s.fermata(bar(24) + 3, hold=1.5)                             # the pickup's C over V7
    s.ritardando((bar(33), bar(35) + 2), to=0.82)                # A' cadence
    s.ritardando((bar(37), coda.end), to=0.8, a_tempo=False)
    s.fermata(bar(37) + 2, hold=2.0)                             # the last Db

    o = bands.church_organ(s, registers=('oboe', 'flute', 'reed', 'strings', 'pedal_soft'), tremulant=True,
                           without=('soft', 'principal', 'full', 'pedal', 'pedal_full'))
    for r in ('flute', 'reed'):            # the Brostverk's spaced pair read partly out of phase (over_wide)
        o[r].add_fx(fx.width(width=0.7))

    voices = [organist.Voice(line(MEL_A, bar(3)), 'oboe', 'tune A', touch='cantabile'),
              organist.Voice(line(MEL_B, bar(11)), 'reed', 'tune B', touch='cantabile'),
              organist.Voice(line(MEL_A2, bar(25)), 'oboe', "tune A'", touch='cantabile',
                             ornaments={20: 'turn'}),
              organist.Voice(line(MEL_C, bar(36)), 'flute', 'tune coda', touch='cantabile')]
    for name, rows, role, at in (('A', ACC_A, 'flute', bar(1)), ('B', ACC_B, 'strings', bar(11)),
                                 ("A'", ACC_A2, 'flute', bar(25)), ('coda', ACC_C, 'strings', bar(36))):
        for i, v in enumerate(chords(rows, at)):
            voices.append(organist.Voice(v, role, f'acc {name} {i + 1}', touch='legato'))
    voices += [organist.Voice(line(PED_A, bar(1)), 'pedal_soft', 'pedal A', touch='legato'),
               organist.Voice(line(PED_B, bar(11)), 'pedal_soft', 'pedal B', touch='legato'),
               organist.Voice(line(PED_A2, bar(25)), 'pedal_soft', "pedal A'", touch='legato'),
               organist.Voice(line(PED_C, bar(36)), 'pedal_soft', 'pedal coda', touch='legato')]
    organist.perform(s, o, voices, phrases=[bar(3), bar(7), bar(11), bar(15), bar(19), bar(21), bar(25), bar(29),
                                            bar(32), bar(36)], seed=5)

    # ---- the swell box breathes with the phrases (oboe in A / A', strings in B and the coda)
    orch.swell(o, [(bar(1), 0.6), (bar(3), 0.6), (bar(5), 0.85, 'smooth'), (bar(6) + 3, 0.65, 'smooth'),
                   (bar(7), 0.65), (bar(8), 1.0, 'smooth'), (bar(10) + 2, 0.6, 'smooth'),
                   (bar(11), 0.35), (bar(13) + 2, 0.62, 'smooth'), (bar(15), 0.45, 'smooth'),
                   (bar(19), 1.0, 'smooth'), (bar(20) + 2, 0.85, 'smooth'), (bar(23), 0.4, 'smooth'),
                   (bar(24) + 3, 0.32, 'smooth'),
                   (bar(25), 0.62), (bar(28), 0.8, 'smooth'), (bar(30), 1.0, 'smooth'), (bar(32), 0.75, 'smooth'),
                   (bar(35), 0.6, 'smooth'),
                   (bar(36), 0.42), (coda.end, 0.0, 'smooth')])
    return s
