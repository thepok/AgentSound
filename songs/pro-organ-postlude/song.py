"""Trumpet Voluntary in D - a festive postlude in the English manner (Stanley / Clarke / Boyce), hand-composed, played
by the shared organist (agentsound.organist) on the Burea church_organ. q=88, D major (see NOTES.md):

  tune     b1-16   the dotted trumpet tune on the Huvudverk Trumpet 8', detached chords on the Positiv, a walking
                   pedal: a 4+4 period in D (half cadence, then a trilled PAC), the tune restated in A (the dominant)
                   after an E7 pivot, a cadence in A with a cadential trill
  echo     b17-27  2-bar phrases on the trumpet, each answered by its echo on the Positiv (the chords on the swell
                   'soft', the pedal silent in the echoes): A major, then F# minor, then a phrase into B minor (trill)
  fugato   b28-41  a fugato on the principal chorus: subject (alto, D), answer (soprano, A) over a countersubject,
                   the subject in the pedal; a circle-of-fifths episode with a 7-3 suspension chain (Em7-A7-Dmaj7-G-
                   C#o7-F#7-Bm7-E7), a three-bar dominant pedal on A, the A7 held with a fermata
  finale   b42-53  the tune on the full organ with the pedal reeds; a deceptive cadence (A7 - Bm) instead of the
                   PAC, the tune's second bar again, a climb to D6, IV - ii6 - I6/4 - V7 (trill) - I, held broad
Every note written by hand (explicit pitches); voices are played through organist.perform (articulation, agogics,
breaths, ornaments, registration seams)."""
from agentsound import *
from agentsound import bands, organist
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'organ'}
METADATA = {'title': 'Trumpet Voluntary in D', 'artist': 'AgentSound', 'album': 'Organ References',
            'genre': 'Classical', 'year': 2026}

_STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def P(name: str) -> int:
    """'F#4' -> 66 (C4 = 60)."""
    acc = name[1:].count('#') - name[1:].count('b')
    octave = int(name.lstrip('ABCDEFG#b'))
    return 12 * (octave + 1) + _STEP[name[0]] + acc


def line(text: str, start: float) -> list:
    """'D5:1 A4:.75 | F#3.A3.D4:1 r:1' -> [(beat, dur, pitch)]: '.' joins a chord, 'r' rests, '|' a barline (each
    bar checked to hold 4 beats)."""
    out, t = [], float(start)
    for i, bar in enumerate(text.split('|')):
        b0 = t
        for tok in bar.split():
            name, dur = tok.split(':')
            d = float(dur)
            if name != 'r':
                out += [(t, d, P(n)) for n in name.split('.')]
            t += d
        if abs(t - b0 - 4) > 1e-6 and i < len(text.split('|')) - 1:
            raise ValueError(f'bar {i + 1} of {text[:30]!r}... holds {t - b0:g} beats')
    return out


def at(notes, beat: float) -> int:
    """The index (sorted by start) of the note starting at `beat` (for Voice.ornaments)."""
    ns = sorted(notes)
    return next(i for i, n in enumerate(ns) if abs(n[0] - beat) < 1e-6)


# ------------------------------------------------------------------------------------------------ the tune (D)
TUNE = {
    1: 'D5:1 A4:.75 D5:.25 F#5:.75 E5:.25 D5:1',
    2: 'B5:1.5 A5:.5 G5:.75 F#5:.25 E5:1',
    3: 'F#5:.75 G5:.25 A5:.75 F#5:.25 G5:.75 E5:.25 C#5:.75 A4:.25',
    4: 'B4:.75 C#5:.25 D5:.75 B4:.25 A4:2',
    7: 'F#5:.75 G5:.25 A5:.75 B5:.25 G5:.75 E5:.25 F#5:.75 D5:.25',
    8: 'E5:2 D5:2',
}
TUNE_CH = {   # the Positiv's detached chords
    1: 'A3.D4.F#4:1 A3.C#4.E4:1 B3.D4.F#4:1 F#3.A3.D4:1',
    2: 'B3.D4.G4:1 B3.D4.G4:1 B3.E4.G4:1 C#4.E4.A4:1',
    3: 'D4.F#4.A4:1 A3.D4.F#4:1 G3.B3.E4:1 G3.C#4.E4:1',
    4: 'B3.D4.G4:1 G3.B3.D4:1 A3.C#4.E4:2',
    7: 'D4.F#4.A4:1 B3.D4.F#4:1 B3.E4.G4:1 A3.D4.F#4:1',
}
TUNE_PED = {
    1: 'D3:1 C#3:1 B2:1 A2:1',
    2: 'G2:1 B2:1 E3:1 A2:1',
    3: 'F#2:1 D3:1 G2:1 A2:1',
    4: 'G2:1 E2:1 A2:1 C#3:1',
    7: 'F#2:1 B2:1 E3:1 A2:1',
}

TUNE_MEL = ' | '.join([TUNE[1], TUNE[2], TUNE[3], TUNE[4], TUNE[1], TUNE[2], TUNE[7], TUNE[8],
                       # b9-12: the tune in A (the dominant), b13-16 a cadence in A
                       'A4:1 E4:.75 A4:.25 C#5:.75 B4:.25 A4:1',
                       'F#5:1.5 E5:.5 D5:.75 C#5:.25 B4:1',
                       'C#5:.75 D5:.25 E5:.75 C#5:.25 D5:.75 B4:.25 G#4:.75 E4:.25',
                       'F#4:.75 G#4:.25 A4:.75 F#4:.25 E4:2',
                       'C#5:.75 D5:.25 E5:.75 F#5:.25 D5:.75 B4:.25 E5:1',
                       'F#5:.75 E5:.25 D5:.75 C#5:.25 B4:1 E5:1',
                       'C#5:.75 D5:.25 E5:.75 F#5:.25 D5:.75 B4:.25 C#5:.75 A4:.25',
                       'B4:2 A4:1 r:1'])
TUNE_CHORDS = ' | '.join([TUNE_CH[1], TUNE_CH[2], TUNE_CH[3], TUNE_CH[4], TUNE_CH[1], TUNE_CH[2], TUNE_CH[7],
                          'G3.C#4.E4:2 A3.D4.F#4:1 G#3.B3.E4:1',
                          'E3.A3.C#4:1 E3.G#3.B3:1 F#3.A3.C#4:1 A3.C#4.E4:1',
                          'A3.D4.F#4:1 A3.D4.F#4:1 B3.D4.F#4:1 G#3.B3.D4:1',
                          'A3.C#4.E4:1 A3.C#4.E4:1 B3.D4.F#4:1 E3.G#3.B3:1',
                          'A3.D4:1 B3.D4:1 E3.G#3.B3:2',
                          'A3.C#4.E4:1 A3.C#4.E4:1 B3.D4.F#4:1 G#3.B3.D4:1',
                          'A3.D4.F#4:1 B3.D4.F#4:1 E3.B3.D4:1 C#4.E4.A4:1',
                          'A3.C#4.E4:1 A3.C#4.F#4:1 B3.D4.F#4:1 A3.C#4.E4:1',
                          'G#3.B3.D4:2 A3.C#4.E4:1 r:1'])
TUNE_BASS = ' | '.join([TUNE_PED[1], TUNE_PED[2], TUNE_PED[3], TUNE_PED[4], TUNE_PED[1], TUNE_PED[2], TUNE_PED[7],
                        'A2:1 A2:1 D3:1 E3:1',                    # A7 - D - E7: the pivot to A
                        'A2:1 G#2:1 F#2:1 E2:1',
                        'D3:1 F#3:1 B2:1 E3:1',
                        'C#3:1 A2:1 D3:1 E3:1',
                        'D3:1 B2:1 E3:2',
                        'C#3:1 A2:1 D3:1 E3:1',
                        'D3:1 B2:1 G#2:1 A2:1',
                        'C#3:1 F#3:1 B2:1 E3:1',
                        'E3:2 A2:1 r:1'])

# ------------------------------------------------------------------------------------------------ the echoes
ECHO_X = 'C#5:.5 E5:.5 A5:1 F#5:.75 E5:.25 D5:.75 F#5:.25 | E5:.75 D5:.25 C#5:.5 B4:.5 A4:1 r:1'
ECHO_X_CH = 'A3.C#4.E4:1 A3.C#4.E4:1 A3.D4.F#4:1 D4.F#4.B4:1 | B3.D4.E4:1 A3.C#4.E4:1 A3.C#4.E4:1 r:1'
ECHO_X_PED = 'A2:1 C#3:1 D3:1 B2:1 | G#2:1 E3:1 A2:1 r:1'
ECHO_Y = 'A4:.5 C#5:.5 F#5:1 D5:.75 C#5:.25 B4:.75 D5:.25 | C#5:.75 B4:.25 A4:.5 G#4:.5 F#4:1 r:1'
ECHO_Y_CH = 'F#3.A3.C#4:1 F#3.A3.C#4:1 F#3.B3.D4:1 G#3.B3.D4:1 | G#3.B3.F4:1 F#3.A3.C#4:1 F#3.A3.C#4:1 r:1'
ECHO_Y_PED = 'F#2:1 A2:1 B2:1 G#2:1 | F2:1 C#3:1 F#2:1 r:1'          # (F2 = E#: C#7/E#)
ECHO_Z = ('D5:.75 E5:.25 F#5:.75 B5:.25 G5:.75 E5:.25 C#5:.75 A#4:.25 | G5:.75 F#5:.25 E5:.75 D5:.25 C#5:2 | '
          'B4:1.5 r:2.5')
ECHO_Z_CH = ('B3.D4.F#4:1 F#3.B3.D4:1 B3.E4.G4:1 A#3.C#4.E4:1 | B3.D4.G4:1 B3.E4.G4:1 A#3.C#4.E4:2 | '
             'B3.D4.F#4:1.5 r:2.5')
ECHO_Z_PED = 'B2:1 D3:1 E3:1 F#2:1 | G2:1 E3:1 F#2:2 | B2:1.5 r:2.5'

# ------------------------------------------------------------------------------------------------ the fugato
FUG_S = ' | '.join(['r:4', 'r:4',
                    'A4:.75 B4:.25 C#5:.5 A4:.5 E5:1 D5:.5 C#5:.5',              # the answer (A)
                    'B4:.5 D5:.5 C#5:.5 B4:.5 A4:1 B4:.5 C#5:.5',
                    'D5:.5 F#5:.5 A5:.5 F#5:.5 E5:.5 C#5:.5 B4:.5 A4:.5',
                    'A4:.5 C#5:.5 D5:.75 E5:.25 F#5:.5 E5:.5 F#5:.5 D5:.5',
                    'G5:.75 F#5:.25 E5:.5 B4:.5 C#5:.75 D5:.25 E5:.5 C#5:.5',      # episode: Em7 - A7
                    'F#5:.75 E5:.25 D5:.5 A4:.5 B4:.75 C#5:.25 D5:.5 B4:.5',       # Dmaj7 - G
                    'E5:.75 D5:.25 C#5:.5 G4:.5 A#4:.75 B4:.25 C#5:.5 A#4:.5',     # C#o7 - F#7
                    'D5:.75 C#5:.25 B4:.5 F#4:.5 G#4:.75 A4:.25 B4:.5 D5:.5',     # Bm7 - E7
                    'C#5:.75 D5:.25 E5:.5 C#5:.5 F#5:.75 E5:.25 D5:.5 F#5:.5',     # over the A pedal
                    'G5:.75 F#5:.25 E5:.5 G5:.5 A5:.75 G5:.25 F#5:.5 E5:.5',
                    'B5:.75 A5:.25 G5:.5 B5:.5 A5:.75 G5:.25 F#5:.5 D5:.5',
                    'E5:2 r:2'])
FUG_A = ' | '.join(['D4:.75 E4:.25 F#4:.5 D4:.5 A4:1 G4:.5 F#4:.5',                  # the subject (D)
                    'E4:.5 G4:.5 F#4:.5 E4:.5 D4:1 C#4:.5 B3:.5',
                    'A3:.5 C#4:.5 E4:1 C#4:.5 A3:.5 G#3:.5 A3:.5',                   # the countersubject
                    'G#3:1 A3:.5 G#3:.5 C#4:1 D4:.5 E4:.5',
                    'F#4:.5 A4:1.5 C#4:1 D4:1',
                    'E4:1 D4:1 A4:.5 F#4:.5 D4:.5 F#4:.5',
                    'G4:4', 'F#4:4', 'E4:4', 'D4:4',                                # the 7-3 chain, upper voice
                    'E4:2 F#4:2', 'E4:2 F#4:2', 'E4:2 F#4:1 E4:1',
                    'G4:2 r:2'])
FUG_T = ' | '.join(['r:4'] * 6 + ['D4:2 C#4:2', 'C#4:2 B3:2', 'B3:2 A#3:2', 'A3:2 G#3:2',      # lower chain voice
                                  'C#4:2 D4:2', 'C#4:2 D4:2', 'C#4:2 D4:1 C#4:1', 'C#4:2 r:2'])
FUG_P = ' | '.join(['r:4'] * 4 + ['D3:.75 E3:.25 F#3:.5 D3:.5 A3:1 G3:.5 F#3:.5',           # the subject (pedal)
                                  'E3:.5 G3:.5 F#3:.5 E3:.5 D3:1 B2:1',
                                  'E3:1 B2:1 A2:1 C#3:1', 'D3:1 A2:1 G2:1 B2:1',
                                  'C#3:1 E3:1 F#2:1 A#2:1', 'B2:1 F#2:1 E2:1 G#2:1'])
FUG_P_POINT = 'A2:14 r:2'                                                          # the dominant pedal (b38-41)

# ------------------------------------------------------------------------------------------------ the finale
FIN_MEL = ' | '.join([TUNE[1], TUNE[2], TUNE[3], TUNE[4], TUNE[1], TUNE[2], TUNE[7],
                      'E5:2 D5:2',                                                  # A7 - Bm: deceptive
                      TUNE[2],
                      'F#5:.75 G5:.25 A5:1 B5:.75 C#6:.25 D6:1',
                      'B5:.75 A5:.25 G5:1 F#5:1 E5:1',                              # IV ii6 I6/4 V7
                      'D5:4'])
FIN_CHORDS = ' | '.join([TUNE_CH[1], TUNE_CH[2], TUNE_CH[3], TUNE_CH[4], TUNE_CH[1], TUNE_CH[2], TUNE_CH[7],
                         'G3.A3.C#4:2 F#3.B3.D4:2',
                         TUNE_CH[2],
                         'D4.F#4.A4:1 A3.D4.F#4:1 D4.G4.B4:1 B3.D4.F#4:1',
                         'B3.D4.G4:1 G3.B3.D4:1 A3.D4:1 G3.A3.C#4:1',
                         'D3.F#3.A3.D4.F#4:4'])
FIN_BASS = ' | '.join([TUNE_PED[1], TUNE_PED[2], TUNE_PED[3], TUNE_PED[4], TUNE_PED[1], TUNE_PED[2], TUNE_PED[7],
                       'A2:2 B2:2', TUNE_PED[2], 'F#2:1 D3:1 G2:1 B2:1', 'G2:1 E2:1 A2:2', 'D2:4'])


def build() -> Song:
    s = Song('Trumpet Voluntary in D', tempo=88, key='D major', seed=5, tail=8)
    tune = s.section('tune', bars=16)
    echo = s.section('echo', bars=11)
    fug = s.section('fugato', bars=14)
    fin = s.section('finale', bars=12)
    T0, E0, F0, Z0 = tune.start, echo.start, fug.start, fin.start

    # ---- time: each section's cadence broadens; the church rings before every change of stops
    s.ritardando((tune.bar(14) + 2, tune.end), to=0.82)
    s.fermata(tune.bar(15) + 2, hold=2)
    s.set_tempo(E0, 86)
    s.ritardando((echo.bar(9) + 2, echo.end), to=0.82)
    s.set_tempo(F0, 92)
    s.ritardando((fug.bar(12) + 2, fug.end), to=0.84)
    s.fermata(fug.bar(13), hold=2)
    s.set_tempo(Z0, 84)
    s.ritardando((fin.bar(9) + 2, fin.bar(11)), to=0.8, a_tempo=False)
    s.fermata(fin.bar(11), hold=3)

    b = bands.church_organ(s, registers=('trumpet', 'positiv'), without=())

    # ---- the voices
    mel = line(TUNE_MEL, T0)
    V = organist.Voice
    voices = [
        V(mel, 'trumpet', 'tune', ornaments={at(mel, T0 + 28): 'trill', at(mel, T0 + 60): 'trill',
                                             at(mel, T0 + 24): 'mordent', at(mel, T0 + 48): 'prall'}),
        V(line(TUNE_CHORDS, T0), 'positiv', 'tune chords', kind='chords'),
        V(line(TUNE_BASS, T0), 'pedal', 'tune pedal', touch='detache'),
    ]
    # echoes: trumpet phrase + pedal; its echo on the Positiv; the chords on the swell all through
    ex = (line(ECHO_X, E0) + line(ECHO_Y, E0 + 16) + line(ECHO_Z, E0 + 32))
    echo_tr = organist.Voice(ex, 'trumpet', 'echo trumpet',
                             ornaments={at(ex, E0 + 5): 'prall',
                                        at(ex, E0 + 38): 'trill'})
    eco = line(ECHO_X, E0 + 8) + line(ECHO_Y, E0 + 24)
    echo_pos = organist.Voice(eco, 'positiv', 'echo', ornaments={at(eco, E0 + 13): 'prall'})
    ech = (line(ECHO_X_CH, E0) + line(ECHO_X_CH, E0 + 8) + line(ECHO_Y_CH, E0 + 16) + line(ECHO_Y_CH, E0 + 24)
           + line(ECHO_Z_CH, E0 + 32))
    ecp = line(ECHO_X_PED, E0) + line(ECHO_Y_PED, E0 + 16) + line(ECHO_Z_PED, E0 + 32)
    voices += [echo_tr, echo_pos, V(ech, 'soft', 'echo chords', kind='chords'),
               V(ecp, 'pedal', 'echo pedal', touch='detache')]
    # fugato on the principal chorus
    fs = line(FUG_S, F0)
    voices += [V(fs, 'principal', 'fugato S', ornaments={at(fs, F0 + 8): 'mordent'}),
               V(line(FUG_A, F0), 'principal', 'fugato A'),
               V(line(FUG_T, F0), 'principal', 'fugato T'),
               V(line(FUG_P, F0) + line(FUG_P_POINT, fug.bar(10)), 'pedal', 'fugato pedal')]
    # finale on the full organ
    fm = line(FIN_MEL, Z0)
    voices += [V(fm, 'full', 'finale tune', ornaments={at(fm, Z0 + 28): 'trill', at(fm, Z0 + 43): 'trill',
                                                       at(fm, Z0 + 24): 'mordent'}),
               V(line(FIN_CHORDS, Z0), 'full', 'finale chords', kind='chords', touch='ordinary'),
               V(line(FIN_BASS, Z0), 'pedal_full', 'finale pedal', touch='detache')]

    phrases = [T0 + 16, T0 + 32, T0 + 48, E0, E0 + 8, E0 + 16, E0 + 24, E0 + 32, F0, F0 + 8, F0 + 24, F0 + 40,
               Z0, Z0 + 16, Z0 + 32]
    organist.perform(s, b, voices, phrases=phrases, seed=5)

    # ---- the swell box: open under the trumpet, closing under each echo
    pts = []
    for k in range(4):
        a = E0 + 8 * k
        pts += [(a, 1.0 if k % 2 == 0 else 0.55), (a + 7.9, 1.0 if k % 2 == 0 else 0.55)]
    pts += [(E0 + 32, 1.0)]
    orch.swell(b, pts)
    # the church blooms into the silences and the final chord
    orch.ring(b, tune.bar(15) + 2, length=2, db=3, roles=('trumpet', 'positiv'), back=E0)
    orch.ring(b, fug.bar(13), length=2, db=3, roles=('principal', 'pedal'), back=Z0)
    orch.ring(b, fin.bar(11), length=4, db=4)
    return s
