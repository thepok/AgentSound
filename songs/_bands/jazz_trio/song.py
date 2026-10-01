"""Band preset demo: jazz_trio - 'Hudson Street Walk', an original medium-swing tune in F (144 BPM, 32 bars, ~0:55).
Build: python -m agentsound build songs/_bands/jazz_trio

Only the preset + ordinary composition code: bands.make('jazz_trio', s) sets up the Salamander grand (right hand +
comping), the Meatbass upright, the Swirly brush kit, the salon room and the master; the parts come from the jazz
toolkit (comp, walking_bass, brushes, paraphrase) and a written head and solo chorus.

  intro   4   comping over a dominant pedal, bass in two, brushes stirring
  A1      8   the head (right hand), comping in its rests, bass in two
  A2      8   the head's second half climbs; the bass starts walking
  solo    8   a written bebop chorus on the A changes, comping busier, the brushes hotter
  tag     4   iii-VI-ii-V tag into a coloured final chord, ritardando, the room ringing
"""
from agentsound import *
from agentsound import bands, jazz
from agentsound.bandlib import jazz as jazzband      # the preset's helpers: brushes() levelled for its kit

ANALYSIS = {'profile': 'jazz'}       # = bands.make('jazz_trio', ...).analysis

HEAD_A1 = [
    [(0.5, 0.5, 'A4'), (1.0, 0.5, 'C5'), (1.5, 2.5, 'E5')],                                          # Fmaj7
    [(0.0, 0.5, 'D5'), (0.5, 0.5, 'C5'), (1.0, 0.5, 'A4'), (1.5, 0.5, 'F#4'), (2.0, 1.5, 'Eb5')],     # D7b9
    [(0.5, 0.5, 'D5'), (1.0, 0.5, 'F5'), (1.5, 2.5, 'A5')],                                          # Gm7
    [(0.0, 0.5, 'G5'), (0.5, 0.5, 'F5'), (1.0, 0.5, 'E5'), (1.5, 0.5, 'D5'), (2.0, 0.5, 'Bb4'),
     (2.5, 1.5, 'G4')],                                                                              # C7
    [(0.0, 1.0, 'C5'), (1.0, 0.5, 'E5'), (1.5, 0.5, 'G5'), (2.0, 0.5, 'F#5'), (2.5, 1.5, 'Eb5')],     # Am7 D7b9
    [(0.0, 1.5, 'D5'), (1.5, 0.5, 'Bb4'), (2.0, 0.5, 'E5'), (2.5, 1.5, 'Bb4')],                       # Gm7 C7
    [(0.0, 2.0, 'A4'), (2.5, 0.5, 'C5'), (3.0, 1.0, 'F#4')],                                         # Fmaj7 D7
    [(0.0, 0.5, 'G4'), (0.5, 0.5, 'A4'), (1.0, 0.5, 'Bb4'), (1.5, 0.5, 'B4'), (2.0, 0.5, 'C5'),
     (2.5, 1.5, 'E5')],                                                                              # Gm7 C7
]
HEAD_A2 = [
    [(0.5, 0.5, 'A4'), (1.0, 0.5, 'C5'), (1.5, 2.5, 'E5')],                                          # Fmaj7
    [(0.0, 0.5, 'D5'), (0.5, 0.5, 'Eb5'), (1.0, 0.5, 'C5'), (1.5, 2.5, 'A4')],                        # F7
    [(0.5, 0.5, 'D5'), (1.0, 0.5, 'F5'), (1.5, 2.5, 'A5')],                                          # Bbmaj7
    [(0.0, 0.5, 'G5'), (0.5, 0.5, 'F5'), (1.0, 0.5, 'Db5'), (1.5, 0.5, 'Bb4'), (2.0, 2.0, 'G4')],     # Eb7
    [(0.5, 0.5, 'E5'), (1.0, 0.5, 'G5'), (1.5, 2.5, 'C6')],                                          # Am7
    [(0.0, 0.5, 'Bb5'), (0.5, 0.5, 'A5'), (1.0, 0.5, 'F#5'), (1.5, 0.5, 'Eb5'), (2.0, 1.5, 'C5')],    # D7b9
    [(0.0, 1.0, 'Bb4'), (1.0, 0.5, 'A4'), (1.5, 0.5, 'G4'), (2.0, 0.5, 'E5'), (2.5, 1.5, 'Bb4')],     # Gm7 C7
    [(0.0, 3.0, 'A4')],                                                                              # Fmaj7
]
SOLO = [    # the piano's chorus on the A changes: bebop lines off the beat, chord tones on the beats, space
    [(0.5, 0.5, 'C5'), (1.0, 0.5, 'D5'), (1.5, 0.5, 'E5'), (2.0, 0.5, 'G5'), (2.5, 1.0, 'A5'), (3.5, 0.5, 'G5')],
    [(0.0, 0.5, 'F#5'), (0.5, 0.5, 'Eb5'), (1.0, 0.5, 'D5'), (1.5, 0.5, 'C5'), (2.0, 0.5, 'A4'), (2.5, 0.5, 'F#4'),
     (3.0, 0.5, 'A4'), (3.5, 0.5, 'C5')],
    [(0.0, 0.5, 'Bb4'), (0.5, 0.5, 'D5'), (1.0, 0.5, 'F5'), (1.5, 0.5, 'A5'), (2.0, 1.0, 'G5'), (3.5, 0.5, 'F5')],
    [(0.0, 0.5, 'E5'), (0.5, 0.5, 'Db5'), (1.0, 1 / 3, 'C5'), (4 / 3, 1 / 3, 'Bb4'), (5 / 3, 1 / 3, 'A4'),
     (2.0, 0.5, 'G4'), (2.5, 0.5, 'Bb4'), (3.0, 1.0, 'E4')],
    [(1.0, 0.5, 'C5'), (1.5, 0.5, 'E5'), (2.0, 0.5, 'F#5'), (2.5, 0.5, 'A5'), (3.0, 0.5, 'C6'), (3.5, 0.5, 'Bb5')],
    [(0.0, 0.5, 'A5'), (0.5, 0.5, 'G5'), (1.0, 0.5, 'F5'), (1.5, 0.5, 'D5'), (2.0, 0.5, 'E5'), (2.5, 0.5, 'G5'),
     (3.0, 0.5, 'Bb5'), (3.5, 0.5, 'Db6')],
    [(0.0, 1.0, 'C6'), (1.0, 0.5, 'A5'), (1.5, 0.5, 'F5'), (2.0, 0.5, 'F#5'), (2.5, 0.5, 'A5'), (3.0, 1.0, 'C6')],
    [(0.0, 0.5, 'Bb5'), (0.5, 0.5, 'A5'), (1.0, 0.5, 'G5'), (1.5, 0.5, 'F5'), (2.0, 0.5, 'E5'), (2.5, 0.5, 'C5'),
     (3.0, 1.0, 'Bb4')],
]
END_RH = [[], [], [(0.5, 0.5, 'D5'), (1.0, 0.5, 'F5'), (1.5, 1.0, 'A5'), (2.5, 1.5, 'E5')],
          [(0.0, 1 / 3, 'A4'), (1 / 3, 1 / 3, 'C5'), (2 / 3, 1 / 3, 'E5'), (1.0, 1 / 3, 'G5'), (4 / 3, 2.6, 'B5')]]

INTRO = 'Am7 D7b9 Gm7 C7'
A1 = 'Fmaj7 D7b9 Gm7 C7 | Am7:0.5 D7b9:0.5 Gm7:0.5 C7:0.5 Fmaj7:0.5 D7:0.5 Gm7:0.5 C7:0.5'
A2 = 'Fmaj7 F7 Bbmaj7 Eb7 | Am7 D7b9 Gm7:0.5 C7:0.5 Fmaj7'
TAG = 'Gm7:0.5 C7:0.5 Am7:0.5 D7b9:0.5 Gm9 Fmaj9'
TAG_WALK = 'Gm7:0.5 C7:0.5 Am7:0.5 D7b9:0.5 Gm9'


def bars_to_clip(bars, vel=80) -> Clip:
    return Clip([(i * 4 + t, d, p, vel) for i, bar in enumerate(bars) for t, d, p in bar], length=len(bars) * 4)


def build() -> Song:
    s = Song('Hudson Street Walk', tempo=144, key='F major', seed=21)
    intro, a1, a2, solo, tag = (s.section(n, bars=b) for n, b in (('intro', 4), ('A1', 8), ('A2', 8), ('solo', 8),
                                                                  ('tag', 4)))
    b = bands.make('jazz_trio', s)
    kit = b.info['kit']

    prog = {n: s.prog(p) for n, p in (('intro', INTRO), ('A1', A1), ('A2', A2), ('tag', TAG))}
    head1, head2 = bars_to_clip(HEAD_A1, 86), bars_to_clip(HEAD_A2, 90)

    # piano right hand: the head (the second A a little looser), a solo chorus, the tag
    b.piano.play(head1, a1)
    b.piano.play(jazz.paraphrase(head2, seed=4, anticipate=0.3, embellish=0.2, key=s.key), a2)
    b.piano.play(jazz.phrase_dynamics(bars_to_clip(SOLO, 84), offbeat=1.06), solo)
    b.piano.play(bars_to_clip(END_RH, 64), tag)

    # comping: under the pedal in the intro, answering the head, busier behind the solo, held at the end
    b.comp.play(jazz.comp(prog['intro'], style='charleston', density=0.45, intensity=0.25, seed=1,
                          register=('A2', 'G4')), intro)
    b.comp.play(jazz.comp(prog['A1'], style='charleston', density=0.45, intensity=0.45, answer=head1, seed=2,
                          register=('A2', 'G4')), a1)
    b.comp.play(jazz.comp(prog['A2'], style='swing', density=0.5, intensity=0.5, answer=head2, seed=3,
                          register=('A2', 'G4')), a2)
    b.comp.play(jazz.comp(prog['A1'], style='swing', density=0.65, intensity=0.7, seed=4, register=('A2', 'G4')), solo)
    b.comp.play(jazz.comp(prog['tag'], style='ballad', density=0.4, intensity=0.45, seed=5, register=('A2', 'A4')), tag)

    # bass: pedal C in the intro, two-feel through A1, walking from A2, the final root held
    b.bass.play(jazz.walking_bass(prog['intro'], key=s.key, feel='two', pedal=[(0, 16, 'C2')], vel=80, seed=1), intro)
    b.bass.play(jazz.walking_bass(prog['A1'], key=s.key, feel='two', skip=0.2, vel=90, seed=2), a1)
    b.bass.play(jazz.walking_bass(prog['A2'] + prog['A1'], key=s.key, vel=86, skip=0.12, seed=3), a2)
    b.bass.play(jazz.walking_bass(s.prog(TAG_WALK), key=s.key, vel=88, seed=4), tag)
    b.bass.note('F1', tag.bar(3), dur=4, vel=84)

    # brushes: a stir per bar all the way, taps on 2 and 4, fills at the phrase ends, a swell into the last chord
    b.drums.play(jazzband.brushes(b, 4, style='two', fills=False, vel=0.6, seed=1), intro)
    b.drums.play(jazzband.brushes(b, 8, style='two', vel=0.9, seed=2), a1)
    b.drums.play(jazzband.brushes(b, 8, style='medium', vel=1.0, seed=3), a2)
    b.drums.play(jazzband.brushes(b, 8, style='medium', vel=1.25, seed=4), solo)
    b.drums.play(jazzband.brushes(b, 2, style='medium', fills=False, vel=0.75, seed=5), tag)
    b.drums.play(jazz.brush_fill('swell', 4, kit=kit, vel=(14, 52)), tag.bar(2))       # a cymbal swell into the end
    b.drums.play(Clip([(0, 4, kit['crash'], 34), (0, 0.5, kit['kick'], 30),               # the last chord: a soft
                       (0, 4, kit['sweep'], 70)], length=4), tag.bar(3))                # crash, a last stir

    s.ritardando((tag.bar(2), tag.bar(3)), to=0.8, a_tempo=False)
    for t in (b.piano, b.comp):
        t.automate('send.room', ramp(tag.bar(3), tag.end, -14, -8))
    return s
