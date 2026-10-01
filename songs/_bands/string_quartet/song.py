"""Band preset demo: string_quartet - an Adagio cantabile in F major (20 bars, 60 BPM, ~1:25). Build:
    python -m agentsound build songs/_bands/string_quartet

Only the preset (agentsound.bandlib.orchestra) plus ordinary composition code: four written lines, each played with
orch.perform (legato phrases, articulations, velocities -> the live dynamics lane with shaped long notes, delayed
vibrato, a player's timing).

  A      8  violin 1 sings the theme (portamento into its leaps), violin 2 / viola hold the harmony, the cello walks
            the bass; every long note swells, the phrase crescendos into bar 6 and settles
  B      4  D minor: the inner voices tremolo, the cello pizzicato, violin 1 climbs to a held A5 that crescendos
            inside the note (p -> f) into ...
  climax 4  ... the climax on Bb: violin 1 up to D6, everyone forte, a diminuendo inside the last held F5
  coda   4  pianissimo, violin 2 non-vibrato, the minor iv (Bbm) sighing, a ritardando and a fermata on the tonic

Measured (report, 'classical'): -21.6 LUFS-I, LRA 13.1 LU, 0 warnings, 0 clicks; sections A -22.8, B -23.7
(short-term max -18.8: the crescendo), climax -17.2, coda -29.3 LUFS; reverb -11.7 LU. From the stems: the held A5 of
bar 12 grows +14 dB INSIDE the note, the held F5 of bar 16 falls -11 dB; the inner voices' tremolo in B swells ~9 dB
with the lane (not out of silence); legato transitions are handed over, not re-attacked. The coda keeps the inner
voices under violin 1 (their pp against its p: the melody stays on top).

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), VSCO 2 CE
(Versilian Studios, CC0), Voxengo IM Reverbs (Musikvereinsaal).
"""
from agentsound import *
from agentsound import bands
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'classical'}                  # the preset's profile (bands.string_quartet(s).analysis)

# One list per bar: (beat, beats, pitch, velocity). Sounding pitches. Velocity = the dynamic (40 p, 78 mf, 95 f).
VLN1 = [
    [(0, 2, 'C5', 62), (2, 1, 'A4', 60), (3, 1, 'Bb4', 64)],                        # A: F
    [(0, 1.5, 'C5', 68), (1.5, 0.5, 'D5', 66), (2, 2, 'F5', 74)],                   # Dm7
    [(0, 2, 'D5', 72), (2, 1, 'C5', 68), (3, 1, 'Bb4', 66)],                        # Bb
    [(0, 2, 'G4', 64), (2, 1, 'A4', 64), (3, 1, 'Bb4', 68)],                        # C7
    [(0, 3, 'C5', 76), (3, 1, 'F5', 80)],                                           # F/A (a leap: portamento)
    [(0, 1.5, 'F5', 86), (1.5, 0.5, 'E5', 80), (2, 2, 'D5', 82)],                   # Gm7
    [(0, 1, 'C5', 74), (1, 1, 'D5', 72), (2, 1, 'Bb4', 68), (3, 1, 'G4', 64)],      # Bb/C C7
    [(0, 4, 'A4', 58)],                                                             # F
    [(0, 2, 'A5', 72), (2, 1, 'G5', 70), (3, 1, 'F5', 72)],                         # B: Dm
    [(0, 3, 'E5', 76), (3, 1, 'A4', 70)],                                           # A7/C#
    [(0, 1, 'F5', 62), (1, 1, 'G5', 58), (2, 1, 'A5', 56), (3, 1, 'Bb5', 54)],      # Dm/C Bb: falling back to p
    [(0, 4, 'A5', 112)],                                                            # A7: held, crescendo p -> ff
    [(0, 2, 'D6', 112), (2, 1, 'C6', 104), (3, 1, 'Bb5', 100)],                     # climax: Bb
    [(0, 2, 'A5', 100), (2, 2, 'C6', 106)],                                         # F/A
    [(0, 1, 'Bb5', 100), (1, 1, 'A5', 96), (2, 1, 'G5', 92), (3, 1, 'E5', 90)],     # Gm7 C7
    [(0, 4, 'F5', 100)],                                                            # F: held, diminuendo
    [(0, 4, 'D5', 54)],                                                             # coda: Bb
    [(0, 4, 'Db5', 56)],                                                            # Bbm
    [(0, 2, 'C5', 52), (2, 1, 'Bb4', 48), (3, 1, 'G4', 45)],                        # F/C C7
    [(0, 4, 'A4', 40)],                                                             # F
]
VLN2 = [
    [(0, 4, 'A4', 56)], [(0, 4, 'F4', 58)], [(0, 4, 'F4', 60)], [(0, 4, 'E4', 58)],
    [(0, 4, 'F4', 66)], [(0, 4, 'F4', 72)], [(0, 2, 'F4', 64), (2, 2, 'E4', 60)], [(0, 4, 'F4', 52)],
    [(0, 4, 'F4', 56)], [(0, 4, 'G4', 60)], [(0, 4, 'F4', 48)], [(0, 4, 'C#5', 104)],
    [(0, 4, 'F5', 84)], [(0, 2, 'C5', 80), (2, 2, 'F5', 82)], [(0, 2, 'D5', 80), (2, 2, 'Bb4', 78)], [(0, 4, 'A4', 80)],
    [(0, 4, 'F4', 34)], [(0, 4, 'F4', 36)], [(0, 2, 'F4', 32), (2, 2, 'E4', 30)], [(0, 4, 'F4', 28)],
]
VIOLA = [
    [(0, 4, 'C4', 54)], [(0, 2, 'A3', 56), (2, 2, 'C4', 58)], [(0, 4, 'D4', 60)], [(0, 2, 'Bb3', 58), (2, 2, 'C4', 60)],
    [(0, 4, 'C4', 64)], [(0, 2, 'D4', 70), (2, 2, 'Bb3', 66)], [(0, 2, 'C4', 62), (2, 2, 'Bb3', 58)], [(0, 4, 'C4', 50)],
    [(0, 4, 'D4', 56)], [(0, 4, 'C#4', 60)], [(0, 4, 'D4', 48)], [(0, 4, 'E4', 108)],
    [(0, 4, 'Bb4', 94)], [(0, 4, 'A4', 90)], [(0, 2, 'G4', 88), (2, 2, 'G4', 84)], [(0, 4, 'F4', 86)],
    [(0, 4, 'D4', 38)], [(0, 4, 'Db4', 42)], [(0, 2, 'C4', 38), (2, 2, 'Bb3', 36)], [(0, 4, 'C4', 32)],
]
CELLO = [
    [(0, 2, 'F2', 64), (2, 2, 'A2', 62)], [(0, 2, 'D3', 66), (2, 2, 'C3', 64)], [(0, 4, 'Bb2', 66)],
    [(0, 2, 'C3', 64), (2, 2, 'E2', 62)], [(0, 4, 'A2', 72)], [(0, 2, 'G2', 76), (2, 2, 'Bb2', 74)],
    [(0, 2, 'C3', 70), (2, 2, 'C2', 66)], [(0, 4, 'F2', 56)],
    [(0, 1, 'D3', 80), (1, 1, 'A2', 72), (2, 1, 'D3', 78), (3, 1, 'A2', 72)],       # pizzicato
    [(0, 1, 'C#3', 80), (1, 1, 'A2', 72), (2, 1, 'E3', 78), (3, 1, 'A2', 72)],
    [(0, 1, 'C3', 70), (1, 1, 'A2', 62), (2, 1, 'Bb2', 64), (3, 1, 'D3', 58)],
    [(0, 4, 'A2', 110)],                                                            # arco again: crescendo
    [(0, 2, 'Bb2', 100), (2, 2, 'D3', 96)], [(0, 4, 'A2', 96)], [(0, 2, 'G2', 94), (2, 2, 'C3', 92)],
    [(0, 4, 'F2', 94)],
    [(0, 4, 'Bb2', 46)], [(0, 4, 'Bb2', 48)], [(0, 4, 'C3', 42)], [(0, 4, 'F2', 36)],
]


def bars(rows) -> Clip:
    return Clip([(i * 4 + t, d, p, v) for i, bar in enumerate(rows) for t, d, p, v in bar], length=len(rows) * 4)


def shapes(clip: Clip, where: dict) -> list:
    """One dynamics shape per note (time order): {bar: shape} for the note starting that bar (0-based), else a
    swell (messa di voce) on whole notes and flat on the others (a tied note glides to its own level)."""
    return [where.get(int(n.start // 4), 'swell') if n.start % 4 == 0 and int(n.start // 4) in where
            else ('swell' if n.dur >= 3 else None) for n in sorted(clip, key=lambda n: n.start)]


def build() -> Song:
    s = Song('Adagio cantabile', tempo=60, key='F major', seed=7, tail=5)
    a = s.section('A', bars=8)
    b = s.section('B', bars=4)
    c = s.section('climax', bars=4)
    d = s.section('coda', bars=4)
    s.rubato(a, depth=0.035, phrase='arch')
    s.rubato((b.start, c.end), depth=0.03, phrase='lean')
    s.ritardando((d.bar(2), d.end), to=0.72)
    s.fermata(d.bar(3), hold=2.5)

    q = bands.string_quartet(s)                       # q.analysis == ANALYSIS

    v1, v2, va, vc = bars(VLN1), bars(VLN2), bars(VIOLA), bars(CELLO)
    # held notes that change INSIDE the note: bar 12 A5 crescendo, bar 16 F5 diminuendo, coda sighs
    inner = {11: 'cresc', 15: 'dim', 19: 'dim'}
    orch.perform(q, 'violin1', v1, 0, shapes=shapes(v1, {11: 'cresc', 15: 'dim', 19: 'dim'}), glide_leaps=5, seed=1)
    v2 = v2.articulate('tremolo', span=(32, 48)).articulate('non-vibrato', span=(64, 80))
    orch.perform(q, 'violin2', v2, 0, shapes=shapes(v2, inner), seed=2)
    va = va.articulate('tremolo', span=(32, 48))
    orch.perform(q, 'viola', va, 0, shapes=shapes(va, inner), seed=3)
    vc = vc.articulate('pizzicato', span=(32, 44))
    orch.perform(q, 'cello', vc, 0, shapes=shapes(vc, inner), seed=4)
    orch.ring(q, d.bar(3), length=3, db=6)            # the hall blooms on the last chord (fermata)
    return s


METADATA = {'artist': 'AgentSound', 'album': 'Band presets', 'genre': 'Classical'}
