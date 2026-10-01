"""Band preset demo: jazz_quartet - 'Tenor at the Blue Door', an original medium-swing tune in Bb (132 BPM, 32 bars,
~1:00). Build: python -m agentsound build songs/_bands/jazz_quartet

Only the preset + ordinary composition code: bands.make('jazz_quartet', s) sets up the Salamander grand (right hand +
comping, ducking ~1.5 dB under the sax), the Meatbass upright, the Swirly brush kit, the MTG tenor (a legato player:
live dynamics, its own vibrato), the salon room, a 224XL plate and the master. The tenor's written part goes through
jazz.horn_line with the options the preset hands over (band.info['horn']): swing and lay-back baked in, legato
transitions inside phrases, breaths, scoops into phrase starts, falls at phrase ends, swells on the live dynamics, a
delayed growing vibrato on long notes and portamento into some leaps.

  intro   4   piano block chords over a dominant pedal, brushes stirring
  A1      8   the tenor states the head; piano comps in its rests, bass in two
  A2      8   the head's second half climbs to the high D; the bass walks
  solo    8   a tenor chorus (written bebop line with space), the drummer on the ride
  out     4   tag into Bbmaj9: the tenor holds the 3rd with a swell and vibrato, the room rings
"""
from agentsound import *
from agentsound import bands, jazz
from agentsound.bandlib import jazz as jazzband      # the preset's helpers: brushes() levelled for its kit

ANALYSIS = {'profile': 'jazz'}       # = bands.make('jazz_quartet', ...).analysis

# The tenor, concert pitch, written straight (horn_line swings and lays it back): one list per bar
HEAD_A1 = [
    [(0.5, 0.5, 'F4'), (1.0, 0.5, 'G4'), (1.5, 2.5, 'A4')],                                          # Bbmaj7
    [(0.0, 0.5, 'Ab4'), (0.5, 0.5, 'G4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'D4'), (2.0, 1.75, 'B3')],     # G7b9
    [(0.5, 0.5, 'Eb4'), (1.0, 0.5, 'G4'), (1.5, 2.5, 'Bb4')],                                        # Cm7
    [(0.0, 0.5, 'A4'), (0.5, 0.5, 'G4'), (1.0, 0.5, 'Eb4'), (1.5, 0.5, 'C4'), (2.0, 1.5, 'A3')],      # F7
    [(0.0, 1.0, 'F4'), (1.0, 0.5, 'A4'), (1.5, 0.5, 'C5'), (2.0, 0.5, 'B4'), (2.5, 1.5, 'F4')],       # Dm7 G7
    [(0.0, 1.5, 'Eb4'), (1.5, 0.5, 'D4'), (2.0, 0.5, 'C4'), (2.5, 1.5, 'A3')],                       # Cm7 F7
    [(0.0, 2.0, 'D4'), (2.5, 0.5, 'Ab4'), (3.0, 1.0, 'G4')],                                         # Bbmaj7 G7
    [(0.0, 1.0, 'Eb4'), (1.0, 0.5, 'D4'), (1.5, 0.5, 'C4'), (2.0, 1.75, 'A3')],                      # Cm7 F7
]
HEAD_A2 = [
    [(0.5, 0.5, 'F4'), (1.0, 0.5, 'G4'), (1.5, 2.5, 'A4')],                                          # Bbmaj7
    [(0.0, 0.5, 'Ab4'), (0.5, 0.5, 'F4'), (1.0, 0.5, 'D4'), (1.5, 2.25, 'F4')],                      # Bb7
    [(0.5, 0.5, 'G4'), (1.0, 0.5, 'Bb4'), (1.5, 2.5, 'D5')],                                         # Ebmaj7
    [(0.0, 0.5, 'C5'), (0.5, 0.5, 'Bb4'), (1.0, 0.5, 'Gb4'), (1.5, 0.5, 'Eb4'), (2.0, 1.75, 'C4')],   # Ab7
    [(0.5, 0.5, 'A4'), (1.0, 0.5, 'C5'), (1.5, 2.5, 'E5')],                                          # Dm7
    [(0.0, 0.5, 'D5'), (0.5, 0.5, 'B4'), (1.0, 0.5, 'Ab4'), (1.5, 0.5, 'F4'), (2.0, 1.75, 'Ab4')],    # G7b9
    [(0.0, 1.0, 'G4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'Eb4'), (2.0, 0.5, 'C4'), (2.5, 1.5, 'A3')],      # Cm7 F7
    [(0.0, 3.5, 'Bb3')],                                                                             # Bb6
]
SOLO = [
    [(0.5, 0.5, 'D4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'A4'), (2.0, 0.5, 'C5'), (2.5, 1.0, 'Bb4'), (3.5, 0.5, 'A4')],
    [(0.0, 0.5, 'Ab4'), (0.5, 0.5, 'F4'), (1.0, 0.5, 'D4'), (1.5, 0.5, 'B3'), (2.0, 1.0, 'Ab3'), (3.0, 0.5, 'B3'),
     (3.5, 0.5, 'D4')],
    [(0.0, 0.5, 'Eb4'), (0.5, 0.5, 'G4'), (1.0, 0.5, 'Bb4'), (1.5, 0.5, 'D5'), (2.0, 1.5, 'C5')],
    [(0.0, 1 / 3, 'Bb4'), (1 / 3, 1 / 3, 'A4'), (2 / 3, 1 / 3, 'G4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'Eb4'),
     (2.0, 0.5, 'C4'), (2.5, 1.5, 'A3')],
    [(1.0, 0.5, 'A3'), (1.5, 0.5, 'C4'), (2.0, 0.5, 'F4'), (2.5, 0.5, 'B4'), (3.0, 1.0, 'A4')],
    [(0.0, 0.5, 'G4'), (0.5, 0.5, 'Eb4'), (1.0, 0.5, 'C4'), (1.5, 0.5, 'Bb3'), (2.0, 0.5, 'A3'), (2.5, 0.5, 'C4'),
     (3.0, 0.5, 'Eb4'), (3.5, 0.5, 'Gb4')],
    [(0.0, 1.5, 'F4'), (1.5, 0.5, 'D4'), (2.0, 0.5, 'F4'), (2.5, 0.5, 'Ab4'), (3.0, 1.0, 'B4')],
    [(0.0, 0.5, 'C5'), (0.5, 0.5, 'Bb4'), (1.0, 0.5, 'G4'), (1.5, 0.5, 'Eb4'), (2.0, 2.0, 'A4')],
]
OUT = [[(0.5, 0.5, 'G4'), (1.0, 0.5, 'Bb4'), (1.5, 1.0, 'A4'), (2.5, 0.5, 'G4'), (3.0, 1.0, 'F4')],
       [(0.0, 1.5, 'F4'), (1.5, 0.5, 'E4'), (2.0, 0.5, 'F4'), (2.5, 1.5, 'Ab4')],
       [(0.0, 2.0, 'G4'), (2.0, 1.5, 'Eb4')],
       [(0.0, 4.0, 'D4')]]
INTRO_RH = [[(0.5, 0.5, 'F4'), (1.0, 0.5, 'A4'), (1.5, 2.0, 'C5')],                     # Dm7
            [(0.5, 0.5, 'Ab4'), (1.0, 0.5, 'B4'), (1.5, 2.0, 'D5')],                    # G7b9
            [(0.5, 0.5, 'Eb5'), (1.0, 0.5, 'D5'), (1.5, 1.0, 'C5'), (2.5, 1.5, 'G4')],   # Cm7
            [(0.0, 2.0, 'A4')]]                                                          # F7
END_RH = [[], [], [], [(0.0, 1 / 3, 'F4'), (1 / 3, 1 / 3, 'A4'), (2 / 3, 1 / 3, 'D5'), (1.0, 1 / 3, 'E5'),
                       (4 / 3, 2.6, 'A5')]]

INTRO = 'Dm7 G7b9 Cm7 F7'
A1 = 'Bbmaj7 G7b9 Cm7 F7 | Dm7:0.5 G7:0.5 Cm7:0.5 F7:0.5 Bbmaj7:0.5 G7:0.5 Cm7:0.5 F7:0.5'
A2 = 'Bbmaj7 Bb7 Ebmaj7 Ab7 | Dm7 G7b9 Cm7:0.5 F7:0.5 Bb6'
OUT_CH = 'Cm7:0.5 F7:0.5 Dm7:0.5 G7:0.5 Cm9:0.5 F13:0.5 Bbmaj9'


def bars_to_clip(bars, vel=90) -> Clip:
    return Clip([(i * 4 + t, d, p, vel) for i, bar in enumerate(bars) for t, d, p in bar], length=len(bars) * 4)


def build() -> Song:
    s = Song('Tenor at the Blue Door', tempo=132, key='Bb major', seed=5)
    intro, a1, a2, solo, out = (s.section(n, bars=b) for n, b in (('intro', 4), ('A1', 8), ('A2', 8), ('solo', 8),
                                                                  ('out', 4)))
    b = bands.make('jazz_quartet', s)
    kit, horn = b.info['kit'], b.info['horn']
    prog = {n: s.prog(p) for n, p in (('intro', INTRO), ('A1', A1), ('A2', A2), ('out', OUT_CH))}

    # --- the tenor: head (the second A paraphrased a little), a solo chorus, the held last note
    head = bars_to_clip(HEAD_A1, 76) + jazz.paraphrase(bars_to_clip(HEAD_A2, 90), seed=3, anticipate=0.25, key=s.key)
    jazz.horn_line(head, s.tempo, seed=11, **horn).place(b.sax, a1)
    solo_line = jazz.phrase_dynamics(bars_to_clip(SOLO, 108), offbeat=1.08)
    jazz.horn_line(solo_line, s.tempo, seed=12, scoop=0.3, fall=0.4, **horn).place(b.sax, solo)
    jazz.horn_line(bars_to_clip(OUT, 78), s.tempo, seed=13, fall=0.0, **horn).place(b.sax, out)

    # --- piano: block-chord intro, comping that answers the tenor, busier under the solo; a last arpeggio
    b.piano.play(jazz.block_chords(bars_to_clip(INTRO_RH, 54), prog['intro'], style='drop2'), intro)
    b.piano.play(bars_to_clip(END_RH, 60), out)
    under = ('A2', 'G4')
    b.comp.play(jazz.comp(prog['A1'], style='charleston', density=0.4, intensity=0.3, seed=2, register=under,
                          answer=head.slice(0, 32)), a1)
    b.comp.play(jazz.comp(prog['A2'], style='swing', density=0.45, intensity=0.45, seed=3, register=under,
                          answer=head.slice(32, 64).shift(-32)), a2)
    b.comp.play(jazz.comp(prog['A1'], style='garland', voicing='shell', density=0.6, intensity=0.65, seed=4,
                          register=('D3', 'D5')), solo)
    b.comp.play(jazz.comp(prog['out'], style='ballad', density=0.35, intensity=0.4, seed=5, register=under), out)

    # --- bass: pedal F under the intro, two-feel for A1, walking from A2, the root to end
    b.bass.play(jazz.walking_bass(prog['intro'], key=s.key, feel='two', pedal=[(0, 16, 'F2')], vel=84, seed=1), intro)
    b.bass.play(jazz.walking_bass(prog['A1'], key=s.key, feel='two', skip=0.2, vel=84, seed=2), a1)
    b.bass.play(jazz.walking_bass(prog['A2'] + prog['A1'], key=s.key, vel=86, skip=0.12, seed=3), a2)
    b.bass.play(jazz.walking_bass(s.prog('Cm7:0.5 F7:0.5 Dm7:0.5 G7:0.5 Cm9:0.5 F13:0.5'), key=s.key, vel=87,
                                  seed=4), out)
    b.bass.note('Bb1', out.bar(3), dur=4, vel=82)

    # --- brushes: stirring through the head, the ride for the tenor's chorus, a swell into the last chord
    b.drums.play(jazzband.brushes(b, 4, style='two', fills=False, vel=0.55, seed=1), intro)
    b.drums.play(jazzband.brushes(b, 8, style='two', vel=0.72, seed=2), a1)
    b.drums.play(jazzband.brushes(b, 8, style='medium', vel=1.0, seed=3), a2)
    b.drums.play(jazzband.brushes(b, 8, style='medium', ride=0.85, vel=1.15, seed=4), solo)
    b.drums.play(jazzband.brushes(b, 2, style='medium', fills=False, vel=0.8, seed=5), out)
    b.drums.play(jazz.brush_fill('swell', 4, kit=kit, vel=(14, 50)), out.bar(2))
    b.drums.play(Clip([(0, 4, kit['crash'], 32), (0, 0.5, kit['kick'], 28), (0, 4, kit['sweep'], 66)], length=4),
                 out.bar(3))

    s.ritardando((out.bar(2), out.bar(3)), to=0.8, a_tempo=False)
    for t in (b.piano, b.comp, b.sax):
        t.automate('send.room', ramp(out.bar(3), out.end, -13, -8))
    return s
