"""Nocturne in E-flat major, op. 9 no. 2 (Frederic Chopin, 1832) - an etude for the virtual pianist.
Build: python -m agentsound build songs/nocturne-etude          (NOCTURNE_MODE=before: the pre-etude tools)

Public-domain score, rendered note for note: 12/8, Andante, E-flat major, one bar of pickup + 34 bars.
The notes were written from the score and checked bar by bar against a concert recording (analysis only: onset
+ pitch tracking of the melody, bass and chord peaks per eighth; NOTES.md lists what was corrected and where the
recording's pianist adds or varies ornaments - the recording is the verification target where editions differ).

  pickup   Bb4
  A    1-4    the theme: G5 held, F G F Eb Bb | C7 (turn on C5) C6 G5 Bb5 Ab5 G5 | F5 G5 D5 Eb5 C5 | Bb4 D6 C6 +
              a 16th cadence Bb Ab G Ab C D Eb
  A'   5-8    ornamented: a written-out turn (F G F E F G), grace turn B4 C5 Db5 C5 + the appoggiatura chain F-E
              Ab-G Db-C, a trill on F5 with its termination, the cadence again
  B    9-12   Bb | F/A | Ab Ab7 Abm | Eb Fb7 C7-F7 Gm | Cm F7 Bb... Bb7: F5 G5 F5 C5 | repeated Eb5s | the climb to
              Bb5 and the chromatic way back (Bb4 B4 C5)
  A''  13-16  fioritura A4-D5 in bar 13, bar 16 the chromatic fioritura Db6 .. Bb4 (+ a diminished arpeggio)
  B    17-20
  A''' 21-24  bar 24: the long fioritura Db6 C6 B5 Bb5 A5 Ab5 | A4 Bb4 B4 C5 Db5 D5 | G5 F5 Eb5
  coda 25-31  over an Eb pedal (Eb / Abm): Eb F Eb F G ..., the 'con forza' run G6 .. Eb5 (bar 28), stretto,
              F7/A Bb7 G7/B Cm F7/A
  32          senza tempo: flourish over Bb7 and the cadenza (the four-note cycle Cb7 Bb6 C7 A6, accelerating and
              broadening), the descent to the cadence Bb5 Ab5 C5 D5
  33-34       Eb5, the sighing Bb4 G5 Eb5 figures, the last chords ppp

Played by romantic.score(...).perform(): the right hand's touch over its principal notes, the ornaments in real
time (^tr trills, ^turn, ^fig fioriture, ^roll chords), the singing line (lean_on_long, cantabile), the dynamics, the
melody's rubato over a steady left hand (accompany), the pedal with the harmony; NOCTURNE_MODE=before plays it
with the plain tools (perform(plain=True): the 'before' column of NOTES.md).

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (Musikvereinsaal IR).
"""
import os

from agentsound import *
from agentsound import romantic as rom

ANALYSIS = {'profile': 'piano'}                   # classical targets, a solo piano's spectrum (NOTES.md)
METADATA = {'title': 'Nocturne op. 9 Nr. 2 (Chopin) – Étude', 'artist': 'AgentSound', 'album': 'Études',
            'genre': 'Classical', 'year': 2026, 'composer': 'Frédéric Chopin'}
COVER = {'style': 'classical', 'palette': ['#1d2a44', '#c9a45c'], 'title': 'NOCTURNE',
         'subtitle': 'op. 9 Nr. 2 - Chopin - AgentSound', 'seed': 9}

MODE = os.environ.get('NOCTURNE_MODE', 'after')        # 'before' = the tools as they were before the etude
TEMPO = 50                                             # quarter notes (a 12/8 bar = 6 beats = 7.2 s)
PIANO = os.environ.get('NOCTURNE_PIANO', 'salamander')  # 'recital': sampled/recital_grand (Headroom C3)
SYMPATHETIC = float(os.environ.get('NOCTURNE_SYMPATHETIC', '0.0'))   # the recording is dry: 0.6 -> T60 3.0 s
RECITAL_GAIN = float(os.environ.get('NOCTURNE_RECITAL_GAIN', '-3.0'))

# ------------------------------------------------------------------------------------------------ the score
# RH: notation per bar, a bare number counts 8ths (unit=1/8): N:dur; {..}:dur^fig(shape) a fioritura (a free figure
# landing on the next note), ^tr / ^tr(lower=-1) a trill (chromatic Nachschlag), ^turn / ^turn(upper=1, lower=-1),
# [..]^roll(60) a rolled chord, _ holds the previous note on, ! accent, ? ghost.
CADENZA = '{' + ' '.join(['Bb6', 'C7', 'A6'] + ['B6', 'Bb6', 'C7', 'A6'] * 14) + '}'   # the cycle Cb7 Bb6 C7 A6
RH = {
    0: 'Bb4:1',
    1: 'G5:5 F5:1 G5:1 F5:2 Eb5:2 Bb4:1',
    2: 'G5:2 C5:1^turn(upper=1, lower=-1) C6:2 G5:1 Bb5:3 Ab5:2 G5:1',
    3: 'F5:3 G5:2 D5:1 Eb5:3 C5:3',
    4: 'Bb4:1 D6:1 C6:1 {Bb5 Ab5 G5 Ab5 C5 D5}:3^fig(even) Eb5:5 Bb4:1',
    5: 'G5:3 {F5 G5 F5 E5 F5 G5}:3^fig F5:1.5 Eb5:2 {F5 Eb5 D5 Eb5 F5}:2.5^fig',
    6: 'G5:0.5 {B4 C5 Db5 C5}:1.5^fig {F5 E5 Ab5 G5 Db6 C6}:3^fig(even) G5:1 Bb5:3 Ab5:2 G5:1',
    7: 'F5:3^tr(lower=-1) G5:2 D5:1 Eb5:3 C5:3',
    8: 'Bb4:1 D6:1 C6:1 {Bb5 Ab5 G5 Ab5 C5 D5}:3^fig(even) Eb5:4 D5:1 Eb5:1',
    9: 'F5:3 G5:2 F5:4^turn C5:2 {F5 G5}:1^fig',
    10: 'Eb5:2 Eb5:1 Eb5:1 Eb5:2 D5:0.5 Eb5:0.5 F5:1.5 Eb5:3.5',
    11: 'r:0.5 Bb4:0.5 Eb5:2 Bb5:2! A5:1 G5:1 F5:1 Eb5:1 D5:3',
    12: 'Eb5:2.5 D5:0.5 C5:0.75 D5:0.75 Bb4:0.5 B4:1.5 C5:1 C5:1.5 D5:1 G4:1 Bb4:0.5 Eb5:0.5',
    13: 'G5:2.8 {A4 Bb4 B4 Bb4 Db5 D5}:2.2^fig G5:1 F5:1.5 Eb5:2 {F5 Eb5 D5 Eb5 F5}:2.5^fig',
    14: 'G5:0.5 {B4 C5 Db5 C5}:1.5^fig {F5 E5 Ab5 G5 Db6 C6}:3^fig(even) G5:1 Bb5:3 Ab5:2 G5:1',
    15: 'F5:3^tr(lower=-1) G5:2 D5:1 Eb5:3 C5:3',
    16: 'Bb4:1 D6:1 {Db6 C6 B5 Bb5 A5 Ab5 F5 D5 B4 Bb4}:2.5^fig D5:0.5 G5:0.75 F5:0.25 Eb5:4 D5:1 Eb5:1',
    17: 'F5:3 G5:2 F5:2 F5:2^tr C5:1 G5:1? C5:1',
    18: 'Eb5:1.5 Eb5:1 Eb5:1 Eb5:1 Eb5:1.5 D5:0.5 Eb5:0.5 F5:1.5 Eb5:3.5',
    19: 'r:0.5 Bb4:0.5 Eb5:2 Bb5:1! Ab5:1.5 A5:0.5 G5:0.5 F5:0.5 G5:0.5 F5:0.5 Eb5:1 D5:3',
    20: 'Eb5:2.5 D5:0.5 C5:0.75 D5:0.75 Bb4:0.5 B4:1.5 C5:1 C5:1.5 D5:1 G4:1 Bb4:0.5 Eb5:0.5',
    21: 'G5:2.8 {A4 Bb4 B4 Bb4 Db5 D5}:2.2^fig G5:1 F5:1.5 Eb5:2 {F5 Eb5 D5 Eb5 F5}:2.5^fig',
    22: 'G5:0.5 {B4 C5 Db5 C5}:1.5^fig {F5 E5 Ab5 G5 Db6 C6}:3^fig(even) G5:1 Bb5:3 Ab5:2 G5:1',
    23: 'F5:3^tr(lower=-1) G5:2 D5:1 Eb5:3 C5:3',
    24: 'Bb4:1 D6:1 {Db6 C6 B5 Bb5 A5 Ab5}:2.2^fig(rit) {A4 Bb4 B4 C5 Db5 D5}:1.2^fig(accel) G5:0.35 F5:0.25 Eb5:6',
    25: 'Eb5:3 F5:1 Eb5:1 F5:1 G5:6',
    26: 'Eb5:4.5 {F5 Eb5 F5 Eb5 F5}:3.25^fig G5:1.25 Eb5:1 Eb5:0.5 F5:0.5 D5:0.25 Eb5:0.75',
    27: 'Eb6:1 D6:1 C6:1 Bb5:1.75 A5:0.75 Ab5:0.75 C5:0.75 D5:1 Eb5:1 F5:1^tr D5:1 Eb5:1',
    28: 'G6:2! F6:1 Eb6:0.33 D6:0.33 C6:0.67 B5:1 Bb5:0.67 A5:1.5 Ab5:0.75 G5:3 F5:0.75',
    29: 'Eb5:4 G5:1 Eb5:1.5 Gb5:1.25 Eb5:0.75 Ab5:0.5 {F5 Eb5 F5 Eb5 F5 Eb5 F5}:3^fig(even)',
    30: 'G5:5 Eb5:1 {Ab4 Bb4 B4 Eb5 Ab5 Eb6}:2^fig(accel) {Gb5 Eb6 F6}:0.75^fig G6:1.25! Eb6:1 G5:0.5 Bb4:0.5',
    31: '_:1 D6:0.75 [C6 C7]:1!^roll(60) [B5 B6]:0.75^roll(60) Bb5:0.5 [A5 A6]:0.75^roll(60) Ab6:0.25 G6:0.5 '
        'D5:0.75 Eb5:1 Eb6:2.25 F6:1 C7:0.5 F6:1',
    32: ('[B5 B6]:1!^roll(60) {D6 Eb6 Ab5 F#6 F6 D6 C6 F6 F#6 Eb6 C7 Ab5 F6 C7 Ab6 Eb6 D6 Ab6}:2.5^fig(wave) Bb6:1 '
         f'{CADENZA}:4.5^fig {{D7 C7 Bb6 A6 Ab6 G6 F6 D6 Eb6 C6}}:1^fig(rit) Bb5:0.5 Ab5:0.5 C5:0.5 D5:0.5'),
    33: 'Eb5:1.5 Bb4:1 G5:1 Eb5:1 Bb4:1 G5:1 Eb5:1 Bb4:1 G5:1 Eb5:1 Bb4:0.75 G5:0.75',
    34: 'Eb5:4 [Bb4 G5 Eb6]:4^roll(60) [Eb5 G5]:1.5^roll(60) [Eb4 G4 Bb4 Eb5]:2.5^roll(60)',
}
# LH: per dotted quarter 'BASS:CHORD[/CHORD2][@start+len][|pattern]' (8ths), chord notes joined by '.', ';' two
# entries in one beat, pattern letters b bass, c chord, B bass + chord held, . rest; bars ' | '
A = """Eb2:Bb3.Eb4.G4 Eb2:B3.D4.Ab4 Eb2:Bb3.Eb4.G4 D2:A3.C4.F#4 | C2:Bb3.E4.G4 C2:Bb3.E4.G4 F2:Bb3.Db4.E4 F2:Ab3.C4.F4 |
       Bb1:D4.F4.Ab4 B1:G3.D4.F4 C2:G3.Eb4.G4 A1:F#3.C4.Eb4/C4.Eb4.F#4 |
       Bb1:Bb3.Eb4.Ab4 Bb1:Bb3.D4.Ab4 Eb2:G3.Bb3.Eb4 Eb2:Bb3.Eb4.G4"""
B = """Bb1:Bb3.D4.F4 Bb1:Bb3.D4.F4 A1:F3.C4.F4 A1:F3.C4.F4 | Ab1:Ab3.C4.Eb4 Ab1:C4.Eb4.Gb4 Ab1:Ab3.B3.Eb4 Eb2:G3.Bb3.Eb4 |
       Eb2:Bb3.Eb4.G4 E2:Ab3.B3.D4 C2:Bb3.E4.G4/A3.Eb4.F4 G1:D4.G4.Bb4 |
       C2:C4.Eb4.G4/Eb4.F4.A4 Bb1:D4.F4.Ab4/D4.F#4 C2:E4.G4.Bb4/Eb4.F4.A4 Bb1:Ab3.D4.F4"""
LH = {1: A, 5: A, 9: B, 13: A, 17: B, 21: A, 25: """
 Eb2:Bb3.Eb4.G4/Ab3.B3.Eb4 Eb2:Ab3.B3.Eb4 Eb2:G3.Bb3.Eb4 Eb2:G3.Bb3.Eb4 |
 Eb2:G3.Bb3.Eb4 Eb2:Ab3.B3.Eb4 Eb2:Ab3.B3.Eb4 Eb2:G3.Bb3.Eb4 |
 Eb2:G3.Bb3.Eb4 Eb2:C4.F#4.A4 Eb2:Ab3.C4.Eb4/Ab3.D4.F4 Eb2:G3.Bb3.Eb4 |
 A1:C4.Eb4.F4 Bb1:Ab3.D4.F4 Bb1:Ab3.D4.F4 Bb1:Ab3.D4.F4 |
 Eb2:G3.Bb3.Eb4 Eb2:G3.Bb3.Eb4 Ab1:C4.Eb4.Gb4/B3.Eb4.Gb4 Eb2:Ab3.B3.Eb4 |
 Eb2:G3.Bb3.Eb4 Eb2:G3.Bb3.Eb4 Ab1:C4.Eb4.Gb4/Ab3.B3.Eb4 Eb2:G3.Bb3.Eb4 |
 A1:C4.Eb4.F4 Bb1:Ab3.D4.F4@0+1|b;B1:G3.D4.F4@1+2|bc C2:C4.Eb4.G4 A1:C4.Eb4.F4 |
 Bb1:F3.Ab3.D4 Bb1:Ab3.D4.F4 Bb1:F3.Ab3.D4|B.. Bb1:Ab3.D4.F4@1.5+1.5|B |
 Eb2:G3.Bb3.Eb4 Bb1:G3.Bb3.Eb4 Eb2:G3.Bb3.Eb4 Bb1:G3.Bb3.Eb4 |
 Eb2:G3.Bb3.Eb4 Eb2:G3.Bb3.Eb4|b.. Eb2:G3.Bb3.Eb4|b.. Eb1:Eb2.Bb2.G3|B.."""}
# dynamics (the score's p espressivo / dolce, its hairpins, the B section's crescendo to the con forza bar and the
# coda's two climaxes; the cadenza leggiero): (bar, eighth, level); the melody gets them in full, the left hand at a
# gentler slope (factor ** 0.6)
DYN = [(0, 0, 'p'), (1, 0, 'p'), (2, 1, 'p'), (2, 3, 'mf'), (2, 9, 'mp'), (3, 3, 'mf'), (3, 8, 'mp'), (4, 0, 'mp'),
       (4, 9, 'p'),
       (5, 0, 'p'), (6, 1, 'p'), (6, 3, 'mf'), (6, 9, 'mp'), (7, 3, 'mf'), (7, 8, 'mp'), (8, 3, 'mp'), (8, 9, 'p'),
       (9, 0, 'pp'), (9, 6, 'p'), (10, 0, 'p'), (10, 9, 'mp'), (11, 3, 'mp'), (11, 9, 'mf'), (12, 0, 'f'),
       (12, 6, 'f'), (12, 11, 'mp'),
       (13, 0, 'p'), (14, 1, 'p'), (14, 3, 'mp'), (14, 9, 'p'), (15, 3, 'mp'), (15, 8, 'p'), (16, 3, 'mp'), (16, 9, 'p'),
       (17, 0, 'pp'), (17, 6, 'p'), (18, 0, 'p'), (18, 9, 'mp'), (19, 3, 'mp'), (19, 9, 'mf'), (20, 0, 'f'),
       (20, 6, 'f'), (20, 11, 'mp'),
       (21, 0, 'p'), (22, 1, 'p'), (22, 3, 'mp'), (22, 9, 'p'), (23, 3, 'mp'), (23, 8, 'p'), (24, 3, 'p'), (24, 9, 'pp'),
       (25, 0, 'pp'), (26, 6, 'p'), (27, 0, 'p'), (27, 9, 'mp'), (28, 0, 'mp'), (28, 6, 'p'), (28, 11, 'p'),
       (29, 0, 'p'), (30, 0, 'mp'), (30, 9, 'f'), (31, 5, 'f'), (31, 11, 'f'), (32, 0, 'mf'), (32, 1.5, 'mp'),
       (32, 3.5, 'p'), (32, 4.5, 'p'), (32, 9, 'p'), (32, 11, 'pp'), (33, 0, 'p'), (34, 0, 'pp'), (34, 8, 'ppp')]
# two-bar phrases: the touch breathes at their ends, the tempo moves per phrase (tempo_plan)
SCORE = rom.score(RH, LH, DYN, meter='12/8', pickup='1/8', key='Eb major',
                  phrases=[(k, k + 1) for k in range(1, 35, 2)])


def tempo_plan(s: Song) -> None:
    """The left hand's time (the tempo map): every two-bar phrase breathes (moves on into its middle, broadens
    into its cadence), the A cadences take a breath, the B section presses on into the repeated E-flats and holds
    back in its chromatic way home, the coda is slower, its two climaxes are pressed and then broadened, the
    cadenza is senza tempo (its figures are timed in real time), the end dies away with a fermata."""
    b = SCORE.bar
    SCORE.rubato(s, depth=0.1, shapes=('lean', 'arch'), seed='bar', bars=(1, 24))   # settles in, broadens
    for k in (4, 8, 16):                        # the A cadences: a breath into the dotted-quarter Eb
        s.ritardando((b(k) + 1.5, b(k) + 3.0), to=0.8)
    for k in (10, 18):                          # B: pressing on into the repeated E-flats ...
        s.accelerando((b(k), b(k) + 3.0), to=1.1, a_tempo=True)
    for k in (12, 20):                          # ... and held back on the chromatic way home
        s.ritardando((b(k) + 3.0, b(k) + 6.0), to=0.72)
    s.ritardando((b(24) + 1.0, b(24) + 3.0), to=0.75)
    s.set_tempo(b(25), 46)                      # coda: quieter, a touch slower
    s.rubato((b(25), b(27)), depth=0.08, phrase='arch', seed=25)
    s.accelerando((b(27), b(28)), to=1.08)
    s.ritardando((b(28) + 3.0, b(29)), to=0.82)
    s.set_tempo(b(29), 47)
    s.accelerando((b(30), b(31) + 3.0), to=1.12)
    s.ritardando((b(31) + 3.0, b(32)), to=0.8)
    s.set_tempo(b(32), 24)                      # senza tempo: the flourish and the cadenza in real time
    s.ritardando((b(32) + 5.0, b(33)), to=0.7)
    s.set_tempo(b(33), 42)
    s.ritardando((b(34), b(34) + 5.5), to=0.72)
    s.fermata(b(34) + 4.75, hold=3)


def build() -> Song:
    s = Song('Nocturne op. 9 Nr. 2', tempo=TEMPO, key='Eb major', seed=9, time_sig='12/8', tail=7.0)
    s.section('pickup', bars=1, meter=(1, 8))
    for name, bars in (('A', 4), ('A2', 4), ('B', 4), ('A3', 4), ('B2', 4), ('A4', 4), ('coda', 7), ('cadenza', 1),
                       ('end', 2)):
        s.section(name, bars=bars)
    tempo_plan(s)

    hall = s.bus('hall', patches.get('bus/ir_concert_hall').but_fx('convolver', width=1.0))
    if PIANO == 'recital':                      # the Headroom C3 recital grand (the Gymnopedie etude's)
        piano = patches.get('sampled/recital_grand')
        tone = {'hp.freq': 30, 'hp.slope': 24}
        gain, pan_rh = RECITAL_GAIN, -0.15
    else:                                       # the Salamander voiced warm, with string resonance
        piano = inst.sfz('samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz', level=1.7, hammers=0.45,
                         polyphony=192, width=0.4, sympathetic=SYMPATHETIC)
        tone = {'hp.freq': 30, 'hp.slope': 24, 'peak1.freq': 280, 'peak1.gain': -1.0, 'peak1.q': 0.8,
                'high.freq': 10000, 'high.gain': 3.5}
        gain, pan_rh = 4.2, -0.55
    rh_t = s.track('rh', piano, fx=[fx.eq(tone)], gain_db=gain, pan=pan_rh, sends={hall: -10})
    lh_t = s.track('lh', piano, fx=[fx.eq({**tone, 'low.freq': 180, 'low.gain': -5.0})], gain_db=gain, pan=-0.1,
                   sends={hall: -10})
    # the left hand first (the timekeeper: the tempo map knows its onsets), the singing right hand over it, the
    # pedal with the harmony (cleared in the chromatic figures and the cadenza)
    global FIGURES
    FIGURES = SCORE.perform(s, rh_t, lh_t, plain=MODE == 'before')['figures']
    s.master.add(fx.limiter(ceiling=-1.0))
    return s


FIGURES = []
