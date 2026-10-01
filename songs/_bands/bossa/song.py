"""Band preset demo: bossa - 'Tarde em Leblon', an original bossa nova in D minor (132 BPM, 24 bars, ~0:45).
Build: python -m agentsound build songs/_bands/bossa

Only the preset + ordinary composition code: bands.make('bossa', s) sets up the FreePats nylon guitar, the Salamander
grand, the Meatbass upright, the Swirly brush kit, the Blonde Bop cross-stick, the FreePats egg shaker, the MTG tenor
(airy, straight 8ths), the salon room, a 224XL plate and the master; its bossa_groove() helper writes the kit parts
keyed for the sounds it got. Everything plays straight 8ths (the feel only lays the parts back a few ms).

  intro   4   guitar alone with the shaker and the cross-stick, the bass and brushes entering in bar 3
  A       8   the tenor's melody (long, soft notes; Getz, not Coltrane), guitar comping, root-fifth bass
  B       8   the piano takes the tune an octave up, the tenor rests; the drums open up a little
  outro   4   the tenor returns, the groove stops on the last chord (Dm9, the tenor on the 9th), which rings
"""
from agentsound import *
from agentsound import bands, jazz
from agentsound.bandlib import jazz as jazzband      # the preset's helpers: bossa_groove()

ANALYSIS = {'profile': 'jazz'}       # = bands.make('bossa', ...).analysis

SAX_A = [
    [(0.0, 1.5, 'F4'), (1.5, 0.5, 'E4'), (2.0, 2.0, 'A4')],                                          # Dm9
    [(0.0, 1.5, 'C5'), (1.5, 0.5, 'A4'), (2.0, 1.0, 'E4'), (3.0, 1.0, 'D4')],                        # Dm9
    [(0.0, 1.5, 'Bb4'), (1.5, 0.5, 'A4'), (2.0, 2.0, 'F4')],                                         # Gm9
    [(0.0, 1.0, 'E4'), (1.0, 1.0, 'G4'), (2.0, 1.75, 'A4')],                                         # C13
    [(0.0, 1.5, 'G4'), (1.5, 0.5, 'A4'), (2.0, 2.0, 'E4')],                                          # Fmaj9
    [(0.0, 1.5, 'D4'), (1.5, 0.5, 'F4'), (2.0, 2.0, 'A4')],                                          # Bbmaj7
    [(0.0, 1.5, 'G4'), (1.5, 0.5, 'Bb4'), (2.0, 2.0, 'D5')],                                         # Em7b5
    [(0.0, 1.0, 'C#5'), (1.0, 1.0, 'Bb4'), (2.0, 1.5, 'E4')],                                        # A7b9
]
PIANO_B = [
    [(0.0, 1.5, 'D5'), (1.5, 0.5, 'F5'), (2.0, 2.0, 'A5')],                                          # Gm9
    [(0.0, 1.5, 'G5'), (1.5, 0.5, 'E5'), (2.0, 2.0, 'A5')],                                          # C13
    [(0.0, 1.5, 'E5'), (1.5, 0.5, 'G5'), (2.0, 2.0, 'C5')],                                          # Fmaj9
    [(0.0, 1.5, 'D5'), (1.5, 0.5, 'F5'), (2.0, 2.0, 'A5')],                                          # Bbmaj7
    [(0.0, 1.5, 'Bb5'), (1.5, 0.5, 'G5'), (2.0, 2.0, 'D5')],                                         # Em7b5
    [(0.0, 1.5, 'C#5'), (1.5, 0.5, 'E5'), (2.0, 2.0, 'Bb5')],                                        # A7b9
    [(0.0, 1.5, 'F5'), (1.5, 0.5, 'E5'), (2.0, 2.0, 'D5')],                                          # Dm9
    [(0.0, 3.0, 'A4')],                                                                              # Dm9
]
SAX_OUT = [
    [(0.0, 2.0, 'Bb4'), (2.0, 2.0, 'A4')],                                                           # Gm9
    [(0.0, 2.0, 'G4'), (2.0, 1.5, 'C#4')],                                                           # A7b9
    [(0.0, 7.5, 'E4')],                                                                              # Dm9 (the 9th)
    [],
]

INTRO = 'Dm9 Dm9 Em7b5 A7b9'
A = 'Dm9 Dm9 Gm9 C13 | Fmaj9 Bbmaj7 Em7b5 A7b9'
B = 'Gm9 C13 Fmaj9 Bbmaj7 | Em7b5 A7b9 Dm9 Dm9'
OUTRO = 'Gm9 A7b9 Dm9:2'


def bars_to_clip(bars, vel=80) -> Clip:
    return Clip([(i * 4 + t, d, p, vel) for i, bar in enumerate(bars) for t, d, p in bar], length=len(bars) * 4)


def guitar(prog, seed, vel=None) -> Clip:
    """Bossa guitar: the two-bar comping cells in drop-2 voicings (fingers), strummed a few ms apart."""
    c = jazz.comp(prog, style='bossa', voicing='drop2', register=('E3', 'E5'), voices=4, intensity=0.5, vel=vel,
                  seed=seed)
    return c.strum(ms=12, bpm=132)


def build() -> Song:
    s = Song('Tarde em Leblon', tempo=132, key='D minor', seed=8, tail=5)
    intro, a, b_sec, outro = (s.section(n, bars=n_) for n, n_ in (('intro', 4), ('A', 8), ('B', 8), ('outro', 4)))
    b = bands.make('bossa', s)
    horn = b.info['horn']
    prog = {n: s.prog(p) for n, p in (('intro', INTRO), ('A', A), ('B', B), ('outro', OUTRO))}

    # --- guitar comping all the way, softer in the intro, the last chord held
    b.guitar.play(guitar(prog['intro'], 1, vel=66), intro)
    b.guitar.play(guitar(prog['A'], 2, vel=70), a)
    b.guitar.play(guitar(prog['B'], 3, vel=74), b_sec)
    b.guitar.play(guitar(s.prog('Gm9 A7b9'), 4, vel=68), outro)
    b.guitar.play(Clip([(0, 7.5, p, 64) for p in ('D3', 'A3', 'C4', 'E4', 'F4')], length=8).strum(ms=25, bpm=132),
                  outro.bar(2))

    # --- bass: root-fifth, the bossa's dotted rhythm (1 . . & | 3 . . &), from bar 3
    for sec, name, vel in ((intro, 'intro', 80), (a, 'A', 86), (b_sec, 'B', 88)):
        line = prog[name].bass(pattern='R__f', rate='1/8', low='C2', vel=vel, gate=0.85)
        b.bass.play(line.slice(8) if name == 'intro' else line, sec.bar(2) if name == 'intro' else sec)
    b.bass.play(s.prog('Gm9 A7b9').bass(pattern='R__f', rate='1/8', low='C2', vel=84, gate=0.85), outro)
    b.bass.note('D2', outro.bar(2), dur=7.5, vel=80)

    # --- kit: brush 8ths + kick + hat foot, cross-stick, egg shaker (bossa_groove keys them for the sounds), up to
    # the last chord; there one soft hit on the crash, kick and cross-stick and a last shake while it rings
    g = jazzband.bossa_groove(18, b, seed=1)
    intro_g = jazzband.bossa_groove(4, b, seed=2, vel=0.8, fills=False)
    b.shaker.play(intro_g['shaker'], intro)
    b.rim.play(intro_g['rim'], intro)
    b.drums.play(intro_g['drums'].slice(8), intro.bar(2))
    for role in ('drums', 'rim', 'shaker'):
        b[role].play(g[role], a)
    kit, shk = b.info['kit'], b.info['shaker_keys']
    b.drums.play(Clip([(0, 4, kit['crash'], 30), (0, 0.5, kit['kick'], 34)], length=4), outro.bar(2))
    b.rim.play(Clip([(0, 0.2, b.info['rim_keys']['rim'], 62)], length=4), outro.bar(2))
    b.shaker.play(Clip([(0, 0.25, shk['soft'], 48), (0.5, 0.5, shk['slow'], 40)], length=4), outro.bar(2))

    # --- melody: tenor in A, piano in B, tenor again to end on the 9th
    jazz.horn_line(bars_to_clip(SAX_A, 82), s.tempo, ratio=0.5, seed=31, scoop=0.2, fall=0.1,
                   swell_db=(-6.0, -1.0, -8.0), **horn).place(b.sax, a)
    b.piano.play(jazz.phrase_dynamics(bars_to_clip(PIANO_B, 80), arch=0.15), b_sec)
    jazz.horn_line(bars_to_clip(SAX_OUT, 80), s.tempo, ratio=0.5, seed=32, fall=0.0, swell_db=(-6.0, -1.0, -9.0),
                   **horn).place(b.sax, outro)

    s.ritardando((outro.bar(1), outro.bar(2)), to=0.85, a_tempo=False)
    for t in (b.guitar, b.sax):
        t.automate('send.room', ramp(outro.bar(2), outro.end, -13, -8))
    return s
