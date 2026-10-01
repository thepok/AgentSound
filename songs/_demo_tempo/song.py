"""Tempo map demo: a string minuet in 3/4 that breathes (rubato), slows into a held final chord (ritardando +
fermata), then a jazz ending tag in 4/4 on a new tempo whose last turnaround slows down into the final chord
(ritardando + fermata). Build: python -m agentsound build songs/_demo_tempo

Tempo and meter calls (docs/COMPOSE_API.md "Tempo and meter"):
  s.section(name, bars, meter=(3, 4))       bars of 3 quarter-note beats
  s.rubato(span, depth, phrase='arch')      phrase-shaped breathing, keeps the span's length
  s.ritardando(span, to=0.7)                slow down across the span (a_tempo=False: stay slow)
  s.fermata(beat, hold=3)                   the chord at that beat rings 3 beats longer
  s.set_tempo(section, 138)                 a new tempo from there on
"""
from agentsound import *


def build() -> Song:
    s = Song('Tempo Demo', tempo=84, key='G major', seed=11)

    # ---- form: an 8-bar minuet in 3/4, then an 8-bar jazz ending tag in 4/4
    minuet = s.section('minuet', bars=8, meter=(3, 4))
    tag = s.section('tag', bars=8)

    hall = s.hall(decay=2.6)

    # ---- sounds: real (non-keyboard) instruments from the GM SoundFont
    violin = s.track('violin', inst.sf2('Violin', attack=1.2, release=1.3), gain_db=-2, pan=0.35,
                     sends={hall: -7})
    cello = s.track('cello', inst.sf2('Cello', release=1.4), gain_db=-3, pan=-0.35, sends={hall: -9})
    strings = s.track('strings', 'gm/strings', gain_db=-8, sends={hall: -6})
    harp = s.track('harp', inst.sf2('Orchestral Harp', release=1.6), gain_db=-6, pan=-0.55, sends={hall: -8})
    bass = s.track('bass', inst.sf2('Acoustic Bass', release=0.6), gain_db=-2, sends={hall: -18})
    kit = s.track('brushes', inst.sf2('Brush Kit'), gain_db=-4, sends={hall: -14}).groove('swing8')
    guitar = s.track('guitar', inst.sf2('Jazz Guitar', release=0.7), gain_db=-5, pan=0.45, sends={hall: -12})
    flute = s.track('flute', inst.sf2('Flute', attack=1.1), gain_db=-5, pan=-0.25, sends={hall: -9}).groove('swing8')

    # ---- the minuet (G major, one chord per 3/4 bar)
    m = s.prog([('G', 1), ('D/F#', 1), ('Em', 1), ('C', 1), ('G/D', 1), ('Am7', 1), ('D7', 1), ('G', 1)], meter=minuet.meter)
    melody = Clip([(0, 1, 'D5', 84), (1, 1, 'G5', 92), (2, 0.5, 'F#5', 80), (2.5, 0.5, 'E5', 76),
                   (3, 2, 'D5', 86), (5, 1, 'A4', 72),
                   (6, 1, 'B4', 78), (7, 1, 'D5', 84), (8, 1, 'G5', 94),
                   (9, 2, 'E5', 88), (11, 1, 'C5', 74),
                   (12, 1, 'D5', 84), (13, 0.5, 'C5', 74), (13.5, 0.5, 'B4', 72), (14, 1, 'A4', 76),
                   (15, 1, 'C5', 80), (16, 1, 'B4', 76), (17, 1, 'A4', 72),
                   (18, 1.5, 'A4', 80), (19.5, 0.5, 'B4', 72), (20, 1, 'C5', 78),
                   (21, 3, 'B4', 82)], length=24).legato(0.05)
    violin.play(melody, minuet)
    cello.play(m.bass('root', low='C2', vel=86), minuet)
    strings.play(m.block(voicing='smooth', register=('D3', 'D5'), vel=70), minuet)
    # (the harp rolls the final chord and lets it ring: the fermata holds everything that starts on it)
    harp.play(m.arp('up', rate='1/8', octaves=2, register=('G3', 'B5'), gate=1.0, vel=70).slice(0, 21)
              + Clip([(0, 3, p, 74) for p in ('G2', 'D3', 'B3', 'G4', 'D5')], length=3).strum(ms=45, bpm=60), minuet)

    # ---- the tag (a new tempo, swung): iii VI ii V three times, the last one slowing into bVI - bII - I
    turn = s.prog('iii7:0.5 VI7:0.5 ii7:0.5 V7:0.5', meter=tag.meter)
    ending = s.prog('bVImaj7:0.5 bII7:0.5 Imaj9:1', meter=tag.meter)
    changes = turn * 3 + ending
    bass.play(changes.bass('walk', low='E1', vel=96).slice(0, 28) + Clip([(0, 4, 'G1', 100)], length=4), tag)
    guitar.play(changes.block(voicing='drop2', register=('D3', 'B4'), rhythm='x.x.x.x.', step='1/8', gate=0.45, vel=74)
                .slice(0, 28) + Clip([(0, 4, p, 80) for p in ('G2', 'F#3', 'B3', 'D4', 'A4')], length=4).strum(ms=28, bpm=90), tag)
    ride = drums({'ride': 'x...x.x.x...x.x.', 'pedal': '....x.......x...', 'snare': '....o.......o...'}, step='1/16')
    kit.loop(ride, tag.start, bars=7)
    kit.note('ride', tag.bar(-1), 4, vel=84).note('kick', tag.bar(-1), 1, vel=52)
    lick = s.motif('5:1/4 6:1/8 5:1/8 3:1/4 2:1/4 | 3:1/2 1:1/4 r:1/4')
    flute.play(lick.clip(octave=5, vel=84), tag).play(lick.transpose(-1).clip(octave=5, vel=80), tag.bar(2))
    flute.play(lick.clip(octave=5, vel=88), tag.bar(4)).note('A5', tag.bar(-1), 4, vel=82)

    # ---- the tempo map
    s.rubato((minuet.start, minuet.bar(6)), depth=0.05, phrase='arch')        # the phrase breathes
    s.ritardando((minuet.bar(6), minuet.bar(7)), to=0.72, a_tempo=False)      # ... slows into the cadence
    s.fermata(minuet.bar(7), hold=3)                                          # final chord held 3 beats longer
    s.set_tempo(tag, 138)                                                     # the jazz tag, a new tempo
    s.ritardando((tag.bar(4), tag.bar(7)), to=0.62, a_tempo=False)            # the last turnaround slows down
    s.fermata(tag.bar(7), hold=4)                                             # ... into a long final chord

    s.master.add(fx.eq(**{'high.freq': 8000, 'high.gain': 3}), fx.limiter(gain=4))
    return s


ANALYSIS = {'loudness': [-18, -12]}
