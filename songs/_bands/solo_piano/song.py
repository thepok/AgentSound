"""Band preset demo: solo_piano - 'Window Seat', an original jazz ballad for solo piano in Db (72 BPM, 22 bars, ~1:20).
Build: python -m agentsound build songs/_bands/solo_piano

Only the preset + ordinary composition code: bands.make('solo_piano', s) sets up the Salamander grand voiced smooth
(hammers fully softened, a dynamic presence cut on the loudest notes), both hands, the salon room + plate and the
gentle master; the pianist (jazz.chorus -> pianist.arrange) harmonizes and decorates the written melody, the left
hand plays tenths. The second A climbs to the loudest notes on purpose: they must bloom, not bite.

  intro   2   the A's last two bars, rubato
  A1      8   the melody, soft
  A2      8   the melody an octave-ish higher, the touch up (the climax in bar 5-6)
  end     4   ii-V into a rolled Dbmaj9, ritardando, the room rings
"""
from agentsound import *
from agentsound import bands, jazz, pianist

ANALYSIS = {'profile': 'piano'}      # = bands.make('solo_piano', ...).analysis

A = 'Dbmaj9 Bbm9 Ebm9 Ab13 Fm7 Bb7b9 Ebm9 Ab7sus4'
MEL_A1 = notes("""r/4 Ab4/8 Bb4/8 C5/4. Db5/8 | F5/2 r/4 Eb5/8 Db5/8 | Bb4/4. C5/8 Db5/4 Gb5/4 | F5/2. r/4 |
                  r/4 C5/8 Db5/8 Eb5/4. F5/8 | Ab5/2 Gb5/4 F5/4 | Eb5/4. Db5/8 Bb4/4 C5/4 | Ab4/2. r/4""",
                length='bar')
MEL_A2 = notes("""r/4 Ab5/8 Bb5/8 C6/4. Db6/8 | F6/2 r/4 Eb6/8 Db6/8 | Bb5/4. C6/8 Db6/4 Gb6/4 | F6/2. r/4 |
                  r/4 C6/8 Db6/8 Eb6/4. F6/8 | Ab6/2 Gb6/4 F6/4 | Eb6/4. Db6/8 Bb5/4 C6/4 | Db6/2. r/4""",
                length='bar')


def build() -> Song:
    s = Song('Window Seat', tempo=72, key='Db major', seed=12, tail=6)
    intro, head, end = s.form('intro:2 head:AA end:4', parts={'A': A, 'intro': 'Ebm9 Ab7sus4',
                                                              'end': 'Ebm9 Ab13 Dbmaj9:2'})
    feel = jazz.Feel(s.tempo, ratio=0.5, beats_per_bar=4)
    b = bands.make('solo_piano', s, feel=feel)
    mem = pianist.Memory()
    play = lambda *a, **k: jazz.chorus(b, *a, memory=mem, bass=None, drums=None, defaults=dict(
        piano=dict(lh='tenths', lh_vel=50, style='ballad')), **k)

    play(intro, notes('r/2 Eb5/4 Db5/4 | C5/2. r/4', length='bar'),
         piano=dict(density=0.5, seed=3, touch=(42, 70), section_end=True))
    s.rubato(intro, depth=0.07, phrase='lean')
    play(head, [MEL_A1, MEL_A2], piano=dict(seed=5, density=jazz.each(0.5, 0.7),
                                            touch=jazz.each((46, 80), (60, 108))))
    play(end, notes('r/4 Bb4/8 C5/8 Db5/4 Eb5/4 | F5/2 Eb5/4 C5/4 | Db5:8', length='bar'), pedal_end=end.end - 0.2,
         piano=dict(density=0.4, seed=7, touch=(44, 76), section_end=True))
    s.ritardando((end.bar(1), end.bar(3)), to=0.8, a_tempo=False)
    return s
