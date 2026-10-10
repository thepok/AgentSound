"""Band preset demo: soul_ballad - 'Blue Hour Lamp', an original soul-jazz ballad in Eb major (72 BPM, 16 bars, ~0:55).
Build: python -m agentsound build songs/_bands/soul_ballad

Only the preset + ordinary composition code: bands.make('soul_ballad', s) sets up the jRhodes3d stereo-vibrato Rhodes
(its own voicing, nearly centred), the Meatbass upright, the Swirly brush kit, the Blonde Bop cross-stick, the MTG
tenor, the salon room, a 224XL plate and the master - faders for long notes at a slow tempo (no song trims).

  intro   4   the Rhodes alone, rolled; the bass and the stirs enter in bar 3
  A       8   the tenor's melody (long soft notes), the Rhodes comping around it, the upright in two, cross-stick on 4
  end     4   the tenor's last phrase, the final Ebmaj9 rolled and held (ritardando)
"""
from agentsound import *
from agentsound import bands, jazz
from agentsound.bandlib import jazz as jazzband      # the preset's helpers: brushes()

ANALYSIS = {'profile': 'jazz'}       # = bands.make('soul_ballad', ...).analysis

INTRO = 'Abmaj9 Gm7 Fm9 Bb13sus4'
A = 'Ebmaj9 Cm9 Abmaj9 Bb13sus4 | Ebmaj9 Gm7:0.5 C7b9:0.5 Fm9 Bb7sus4:0.5 Bb7b9:0.5'
END = 'Abmaj9 Bb13sus4 Ebmaj9:2'

SAX_A = notes("""G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2 r/2 | F4/4. G4/8 Ab4/8 Bb4/4.~ | Bb4/2 r/2 |
                 G4/4. Ab4/8 Bb4/8 Bb4/4 Ab4/8 | C5/2. r/4 | F4/4. G4/8 F4/8 Eb4/4.~ | Eb4/2. r/4""", length='bar')
SAX_END = notes('r/2 C5/4. Bb4/8 | G4/2 F4/2 | Eb4:7.5', length='bar')


def build() -> Song:
    s = Song('Blue Hour Lamp', tempo=72, key='Eb major', seed=9, tail=6)
    intro, a, end = (s.section(n, bars=n_) for n, n_ in (('intro', 4), ('A', 8), ('end', 4)))
    b = bands.make('soul_ballad', s)
    horn = b.info['horn']
    prog = {n: s.prog(p) for n, p in (('intro', INTRO), ('A', A), ('end', END))}

    # --- the Rhodes: ballad comping (rootless, rolled), sparser around the tenor; the last chord held in the pedal
    for sec, name, dens in ((intro, 'intro', 0.5), (a, 'A', 0.35), (end, 'end', 0.35)):
        c = jazz.comp(prog[name], style='ballad', voicing='rootless', register=b.info['register']['piano'], density=dens,
                      intensity=0.3, vel=70, seed=len(name))
        b.piano.play(c.strum(ms=25, bpm=s.tempo), sec)
    jazzband.pedal([b.piano], prog['intro'], intro)
    jazzband.pedal([b.piano], prog['A'], a)
    jazzband.pedal([b.piano], prog['end'], end)

    # --- the upright in two (half notes, a pickup now and then), from bar 3
    b.bass.play(jazz.walking_bass(prog['intro'], key=s.key, feel='two', seed=1, vel=78).slice(8), intro.bar(2))
    b.bass.play(jazz.walking_bass(prog['A'], key=s.key, feel='two', seed=2, vel=82), a)
    b.bass.play(jazz.walking_bass(s.prog('Abmaj9 Bb13sus4'), key=s.key, feel='two', seed=3, vel=78), end)
    b.bass.note('Eb2', end.bar(2), dur=7.5, vel=74)

    # --- brush stirs (taps on 2 and 4), the cross-stick on 4
    b.drums.play(jazzband.brushes(b, 2, style='ballad', seed=1), intro.bar(2))
    b.drums.play(jazzband.brushes(b, 10, style='ballad', seed=2), a)
    rim = b.info['rim_keys']['rim']
    b.rim.play(Clip([(4 * k + 3, 0.2, rim, 72) for k in range(8)], length=32), a)
    b.rim.play(Clip([(3, 0.2, rim, 66), (7, 0.2, rim, 62)], length=8), end)

    # --- the tenor: the melody, then its last phrase onto the 3rd of the final chord
    jazz.horn_line(SAX_A, s.tempo, ratio=0.5, seed=41, scoop=0.15, fall=0.0, swell_db=(-6.0, -1.0, -8.0),
                   **horn).place(b.sax, a)
    jazz.horn_line(SAX_END, s.tempo, ratio=0.5, seed=42, fall=0.0, swell_db=(-6.0, -1.0, -9.0), **horn).place(b.sax, end)

    s.ritardando((end.bar(1), end.bar(2)), to=0.85, a_tempo=False)
    return s
