"""Band preset demo: dreamwave (agentsound/bandlib/synthwave.py). Only the preset + ordinary composition code.
Build: python -m agentsound build songs/_bands/dreamwave
Compare: python -m agentsound compare songs/_bands/dreamwave --section chorus --ref "assets/refrences/Timecop1983 - Deckard's Dream [-d4ij5J4zJs].opus"
"""
from agentsound import *
from agentsound import bands

ANALYSIS = {'profile': 'dreamwave'}                  # = bands.dreamwave(...).analysis


def build() -> Song:
    s = Song('Dreamwave Band Demo', tempo=88, key='D minor', seed=5, tail=7)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    outro = s.section('outro', bars=4)

    b = bands.dreamwave(s)

    verse_prog = s.prog('i9 VImaj7 IIIadd9 VIIsus4')          # Dm9 Bbmaj7 Fadd9 Csus4
    chorus_prog = s.prog('VImaj7 VII i9 i9')                  # Bbmaj7 C Dm9 Dm9
    hook = s.motif('5:1/2 4:1/4 3:1/4 | 2:1 | 3:1/2 5:1/4 8:1/4 | 7:1 '
                   '| 5:1/2 4:1/4 3:1/4 | 4:1/2 5:1/2 | 3:1.5 r:1/2 | r:1')
    half = drums({'kick': 'x.......x.x.....', 'snare': '........x.......', 'hat': 'x.x.x.x.x.x.x.x.'})
    half_chorus = drums({'kick': 'x.......x.x.....', 'snare': '........x.......', 'clap': '........x.......',
                         'hat': 'x.xxx.x.x.xxx.x.', 'ohh': '..............x.'})

    spread = dict(voicing='spread', register=('C3', 'C5'))
    b.pad.loop(verse_prog.block(**spread), intro, verse).loop(chorus_prog.block(**spread), chorus)
    b.pad.loop(verse_prog.block(**spread), outro)
    b.strings.loop(verse_prog.block(register=('A3', 'A5'), voices=3), verse.bar(4), bars=4, vel=0.8)
    b.strings.loop(chorus_prog.block(register=('A3', 'A5'), voices=3), chorus)
    b.keys.loop(verse_prog.block(voicing='drop2', rhythm='x.....x.', register=('C4', 'C5'), vel=74), intro, verse)
    b.keys.loop(chorus_prog.block(voicing='drop2', rhythm='x.....x.', register=('C4', 'C5'), vel=80), chorus)
    b.keys.play(verse_prog.block(voicing='drop2', rhythm='x.......', register=('C4', 'C5'), vel=66), outro)
    b.bass.loop(verse_prog.bass('root', rate='1/2').legato(), verse, vel=0.9)
    b.bass.loop(chorus_prog.bass('octave', rate='1/4').legato(), chorus)
    b.drums.loop(half, verse, vel=0.85).loop(half_chorus, chorus)
    b.drums.play(crash(), chorus)
    b.lead.play(hook.clip(octave=4), chorus)

    b.pad.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 700, 2600),
                   exp_ramp(outro.start, outro.end, 2600, 600))
    b.pad.automate('send.shimmer', hold(intro.start, verse.start, -8), hold(verse.start, outro.start, -18),
                   hold(outro.start, outro.end, -8))
    return s
