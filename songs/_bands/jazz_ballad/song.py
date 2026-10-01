"""Band preset demo: jazz_ballad - 'Last Light on Bleecker', an original ballad in Eb (66 BPM, 20 bars, ~1:20).
Build: python -m agentsound build songs/_bands/jazz_ballad

Only the preset + ordinary composition code: bands.make('jazz_ballad', s) sets up the pedalled Salamander grand, the
Meatbass (bass='pizz'; 'arco' swaps in the bowed Meatbass), the Swirly brush kit stirring, the MTG tenor in a rich
224XL plate, the 224XL chamber and the master; the preset's helpers pedal() (the sustain pedal changing with the
harmony) and brushes() (the stirs levelled for the kit) do the rest.

  intro   2   the piano alone, rubato: the turnaround, pedalled, rolled
  A1      8   the tenor sings the melody (legato, swells, delayed vibrato), piano ballad comping, bass in two,
              brushes stirring
  A2      8   the piano takes the first half (right hand, pedalled), the tenor answers and climbs to the end
  end     2   Ebmaj9, slowing: the tenor holds the 3rd, the piano rolls up to the 9th, the chamber rings
"""
from agentsound import *
from agentsound import bands, jazz
from agentsound.bandlib import jazz as jazzband      # the preset's helpers: pedal(), brushes()

ANALYSIS = {'profile': 'jazz'}       # = bands.make('jazz_ballad', ...).analysis

SAX_A1 = [
    [(0.5, 0.5, 'Bb3'), (1.0, 0.5, 'Eb4'), (1.5, 1.5, 'G4'), (3.0, 1.0, 'F4')],                      # Ebmaj7 Cm7
    [(0.0, 2.0, 'Ab4'), (2.0, 0.5, 'G4'), (2.5, 0.5, 'F4'), (3.0, 1.0, 'D4')],                       # Fm7 Bb7
    [(0.0, 1.5, 'Bb4'), (1.5, 0.5, 'G4'), (2.0, 1.75, 'E4')],                                        # Gm7 C7b9
    [(0.0, 1.0, 'F4'), (1.0, 0.5, 'Ab4'), (1.5, 0.5, 'C5'), (2.0, 1.75, 'Bb4')],                      # Fm7 Bb7
    [(0.0, 2.5, 'G4'), (2.5, 0.5, 'Db5'), (3.0, 1.0, 'C5')],                                         # Ebmaj7 Eb7
    [(0.0, 2.0, 'C5'), (2.0, 0.5, 'Bb4'), (2.5, 0.5, 'Ab4'), (3.0, 1.0, 'F4')],                      # Abmaj7 Db7
    [(0.0, 1.0, 'Bb4'), (1.0, 1.0, 'G4'), (2.0, 1.75, 'E4')],                                        # Gm7 C7b9
    [(0.0, 1.5, 'Ab4'), (1.5, 0.5, 'G4'), (2.0, 1.5, 'F4')],                                         # Fm7 Bb7
]
PIANO_A2 = [
    [(0.5, 0.5, 'Bb4'), (1.0, 0.5, 'Eb5'), (1.5, 1.5, 'G5'), (3.0, 1.0, 'F5')],                      # Ebmaj7 Cm7
    [(0.0, 2.0, 'Ab5'), (2.0, 0.5, 'G5'), (2.5, 0.5, 'F5'), (3.0, 1.0, 'D5')],                       # Fm7 Bb7
    [(0.0, 1.5, 'Bb5'), (1.5, 0.5, 'G5'), (2.0, 2.0, 'E5')],                                         # Gm7 C7b9
    [(0.0, 1.0, 'F5'), (1.0, 0.5, 'Ab5'), (1.5, 0.5, 'C6'), (2.0, 2.0, 'Bb5')],                      # Fm7 Bb7
]
SAX_A2 = [   # enters under the piano's last note, climbs, and lands on the 3rd of the final chord
    [], [], [],
    [(3.0, 0.5, 'Bb3'), (3.5, 0.5, 'D4')],
    [(0.0, 0.5, 'Eb4'), (0.5, 0.5, 'G4'), (1.0, 0.5, 'Bb4'), (1.5, 2.5, 'C5')],                      # Abmaj7
    [(0.0, 1.5, 'B4'), (1.5, 0.5, 'Ab4'), (2.0, 1.75, 'F4')],                                        # Abm6 Db9
    [(0.0, 1.0, 'D5'), (1.0, 1.0, 'Bb4'), (2.0, 1.5, 'G4'), (3.5, 0.5, 'E4')],                       # Gm7 C7b9
    [(0.0, 2.0, 'F4'), (2.0, 1.5, 'Eb4')],                                                           # Fm7 Bb7sus4
    [(0.0, 7.5, 'G4')],                                                                              # Ebmaj9 ...
]
INTRO_RH = [[(0.0, 1.0, 'D5'), (1.0, 1.0, 'F5'), (2.0, 2.0, 'E5')],                             # Gm7 C7b9
            [(0.0, 1.5, 'Ab4'), (1.5, 0.5, 'C5'), (2.0, 2.0, 'Eb5')]]                            # Fm7 Bb7sus4
END_RH = [[(0.0, 0.25, 'Eb4'), (0.25, 0.25, 'G4'), (0.5, 0.25, 'Bb4'), (0.75, 0.25, 'D5'), (1.0, 0.25, 'F5'),
           (1.25, 6.5, 'Bb5')], []]

INTRO = 'Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7sus4:0.5'
A1 = ('Ebmaj7:0.5 Cm7:0.5 Fm7:0.5 Bb7:0.5 Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 | '
      'Ebmaj7:0.5 Eb7:0.5 Abmaj7:0.5 Db7:0.5 Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5')
A2 = ('Ebmaj7:0.5 Cm7:0.5 Fm7:0.5 Bb7:0.5 Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 | '
      'Abmaj7 Abm6:0.5 Db9:0.5 Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7sus4:0.5')
END = 'Ebmaj9:2'


def bars_to_clip(bars, vel=80) -> Clip:
    return Clip([(i * 4 + t, d, p, vel) for i, bar in enumerate(bars) for t, d, p in bar], length=len(bars) * 4)


def build() -> Song:
    s = Song('Last Light on Bleecker', tempo=66, key='Eb major', seed=3, tail=6)
    intro, a1, a2, end = (s.section(n, bars=b) for n, b in (('intro', 2), ('A1', 8), ('A2', 8), ('end', 2)))
    b = bands.make('jazz_ballad', s)
    kit, horn = b.info['kit'], b.info['horn']
    prog = {n: s.prog(p) for n, p in (('intro', INTRO), ('A1', A1), ('A2', A2), ('end', END))}

    # --- piano: a rubato pedalled intro, the melody of A2's first half, a last roll up to the 9th
    b.piano.play(bars_to_clip(INTRO_RH, 58), intro)
    b.piano.play(jazz.phrase_dynamics(bars_to_clip(PIANO_A2, 92), arch=0.18), a2)
    b.piano.play(bars_to_clip(END_RH, 58), end)
    for sec, name, dens, inten, seed in ((intro, 'intro', 0.35, 0.22, 1), (a1, 'A1', 0.3, 0.28, 2),
                                         (a2, 'A2', 0.4, 0.45, 3), (end, 'end', 0.2, 0.2, 4)):
        b.comp.play(jazz.comp(prog[name], style='ballad', density=dens, intensity=inten, seed=seed,
                              register=('A2', 'G4')), sec)
        jazzband.pedal([b.piano, b.comp], prog[name], sec)

    # --- tenor: the melody, then the answer and climb in A2 onto the held 3rd of the last chord
    jazz.horn_line(bars_to_clip(SAX_A1, 68), s.tempo, seed=21, fall=0.2, **horn).place(b.sax, a1)
    jazz.horn_line(bars_to_clip(SAX_A2, 96), s.tempo, seed=22, fall=0.0, **horn).place(b.sax, a2)

    # --- bass: two-feel with long notes, the final root under the fermata
    b.bass.play(jazz.walking_bass(prog['intro'], key=s.key, feel='two', gate=0.97, vel=86, seed=1), intro)
    b.bass.play(jazz.walking_bass(prog['A1'] + prog['A2'], key=s.key, feel='two', gate=0.97, skip=0.1, vel=84,
                                  seed=2), a1)
    b.bass.note('Eb2', end, dur=8, vel=80)

    # --- brushes: a continuous stir (one per beat at this tempo: b.info['sweep']), soft taps on 2 and 4, a swell
    b.drums.play(jazzband.brushes(b, 8, style='ballad', kick=None, vel=0.75, seed=2), a1)
    b.drums.play(jazzband.brushes(b, 7, style='ballad', vel=0.95, seed=3), a2)
    b.drums.play(jazz.brush_fill('swell', 4, kit=kit, vel=(12, 48)), a2.bar(7))
    b.drums.play(Clip([(t, 0.97, kit['sweep'], round(72 - 4 * t)) for t in range(8)]   # the stir dying away
                      + [(0, 6, kit['crash'], 28)], length=8), end)

    # --- time: a breathing intro, broadening into the last chord (which rings for two slow bars)
    s.rubato(intro, depth=0.06, phrase='lean')
    s.ritardando((a2.bar(6), a2.end), to=0.85)
    for t in (b.piano, b.comp, b.sax):
        t.automate('send.room', ramp(end.start, end.end, -12, -7))
    return s
