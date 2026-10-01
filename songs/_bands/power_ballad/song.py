"""power_ballad demo: 'Northern Lights Remain' - 20 bars of 80s power ballad in A major at 76 BPM, built only from the
power_ballad preset and ordinary composition code: piano alone, a verse where bass, strings and a light kit enter
under the lead guitar, a big chorus with the half-time kit, Juno pad and the lead up an octave, a held ending.

Credits: Salamander Grand Piano V3 (CC-BY: Alexander Holm), Virtual Playing Orchestra strings (Paul Battersby),
Karoryfer Big Rusty Drums / Growlybass (CC0), FreePats FSBS guitar (CC0), Lexicon 224XL room / plate / hall
(Little Devil), Jester Emerald cabinet IR.
"""
from agentsound import *
from agentsound import articulation as art, bands

ANALYSIS = {'profile': 'rock'}
METADATA = {'title': 'Northern Lights Remain', 'artist': 'AgentSound', 'album': 'Band Presets',
            'genre': 'Power Ballad'}


def pedal_points(sec, every=4):
    """Sustain pedal: re-pedal just after each chord change (every `every` beats)."""
    pts = []
    t = sec.start
    while t < sec.end - 0.01:
        pts += [(t, 0, 'step'), (t + 0.08, 1, 'step')]
        t += every
    return pts


def build() -> Song:
    s = Song('Northern Lights Remain', tempo=76, key='A major', seed=21, tail=6)
    intro = s.section('intro', bars=2)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    end = s.section('end', bars=2)

    b = bands.power_ballad(s)
    vprog = s.prog('A E/G# F#m D')
    cprog = s.prog('D E C#m F#m D E A A')

    # --- piano: broken chords in intro / verse, driving 8th chords in the chorus, pedal throughout
    broken = vprog.block(voicing='spread', register=('A2', 'E5'), vel=62).arpeggiate('pinky', rate='1/8', gate=1.6)
    b.piano.play(broken.slice(0, 8), intro)
    b.piano.loop(broken, verse)
    b.piano.play(cprog.block(voicing='spread', register=('A2', 'A5'), rhythm='x.x.x.x.', step='1/8', vel=86),
                 chorus)
    b.piano.play(s.prog('A').block(voicing='spread', register=('A1', 'E5'), vel=90).stretch(2), end)
    b.piano.automate('instrument.pedal', pedal_points(intro) + pedal_points(verse) + pedal_points(chorus)
                     + [(end.start, 0, 'step'), (end.start + 0.08, 1, 'step')])

    # --- strings: enter in the second half of the verse, swell into the chorus
    b.strings.play(vprog.block(voicing='spread', register=('A3', 'E5'), vel=70), verse.bar(4))
    b.strings.play(cprog.block(voicing='spread', register=('E3', 'A5'), vel=92), chorus)
    b.strings.play(s.prog('A').block(voicing='spread', register=('A3', 'E5'), vel=88).stretch(2), end)
    b.strings.automate('gainDb', ramp(verse.bar(4), chorus.start, -10, 0), hold(chorus.start, end.end, 0))

    # --- pad under the chorus
    b.pad.play(cprog.block(voicing='open', register=('C#3', 'C#5'), vel=80), chorus)
    b.pad.play(s.prog('A').block(register=('A3', 'A4'), vel=76).stretch(2), end)

    # --- bass: long roots in the verse, pushing 8ths in the chorus
    b.bass.play(vprog.bass('root', low='E1', vel=88), verse, times=2)
    b.bass.play(cprog.bass('pulse', rate='1/4', low='E1', vel=98), chorus)
    b.bass.note('A1', end.start, 7.5, 96)

    # --- drums: side stick + kick in the verse's second half, half-time power beat in the chorus
    b.drums.loop(drums({'kick': 'x.......x.......', 'rim': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'},
                       vel=64), verse.bar(4), bars=4)
    b.drums.play(tom_fill(2), verse.bar(-1, 2), replace=True)
    b.drums.play(crash(), chorus).play(crash(), chorus.bar(4))
    beat = drums({'kick': 'x.........x.....', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.'}, vel=108)
    b.drums.loop(beat, chorus)
    b.drums.play(tom_fill(2), chorus.bar(-1, 2), replace=True)
    b.drums.play(drums({'kick': 'x...............', 'crash': 'x...............'}, vel=120), end)

    # --- lead guitar: the melody, verse low, chorus an octave up, slides, vibrato, a bend at the peak
    # (durations in beats: 0.5 = an 8th)
    v = s.motif('r:1 3:0.5 5:0.5 6:1 5:1 | 3:3 r:1 | r:1 3:0.5 5:0.5 6:1 8:1 | 7:2 6:1 5:1').clip(octave=4, vel=80)
    c = s.motif('8:1 7:0.5 6:0.5 5:2 | 5:1 6:0.5 7:0.5 6:2 | 5:1 6:0.5 5:0.5 3:2 | 3:1 5:1 6:2 '
                '| 8:1 7:0.5 6:0.5 5:2 | 5:1 6:0.5 7:0.5 8:2 | 9:1 8:1 7:1 6:1 | 8:4').clip(octave=4, vel=104)
    v = art.legato(v, overlap=0.04).glide(140, where=art.leaps(3))
    c = art.legato(c, overlap=0.04).glide(160, where=art.leaps(3))
    b.lead.play(v, verse).play(v, verse.bar(4))
    b.lead.play(c, chorus)
    art.vibrato(b.lead, v, verse, depth=26, rate=5.2)
    art.vibrato(b.lead, v, verse.bar(4), depth=26, rate=5.2)
    art.vibrato(b.lead, c, chorus, depth=32, rate=5.6)
    peak = chorus.bar(6)
    b.lead.automate('instrument.pitchbend', [(peak, 0), (peak + 0.4, 2, 'smooth'), (peak + 0.9, 2),
                                             (peak + 1.0, 0, 'smooth')])
    b.lead.note('A5', end.start, 6, 104)
    return s
