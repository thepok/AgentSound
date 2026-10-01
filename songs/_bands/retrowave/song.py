"""Band preset demo: retrowave (agentsound/bandlib/synthwave.py). Only the preset + ordinary composition code.
Build: python -m agentsound build songs/_bands/retrowave
Compare: python -m agentsound compare songs/_bands/retrowave --section chorus --ref "assets/refrences/The Midnight - Sunset (Official Audio) [URma_gu1aNE].opus"
"""
from agentsound import *
from agentsound import bands

ANALYSIS = {'profile': 'synthwave'}                  # = bands.retrowave(...).analysis


def build() -> Song:
    s = Song('Retrowave Band Demo', tempo=112, key='C# minor', seed=21, tail=5)
    intro = s.section('intro', bars=2)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    outro = s.section('outro', bars=2)

    b = bands.retrowave(s)

    verse_prog = s.prog('i VI III VII')                     # C#m A E B
    chorus_prog = s.prog('VI VII III i')                     # A B E C#m: the anthem lift
    hook = s.motif('3:1/8 5:1/8 5:1/4 5:1/8 6:1/8 5:1/4 | 3:1/2 r:1/4 1:1/8 2:1/8 | 3:1/8 5:1/8 5:1/4 8:1/4 7:1/8 5:1/8 '
                   '| 5:1/2 r:1/2 | 3:1/8 5:1/8 5:1/4 5:1/8 6:1/8 5:1/4 | 8:1/2 7:1/4 5:1/4 | 6:1/4 5:1/4 3:1/4 2:1/4 '
                   '| 1:3/4 r:1/4')
    beat = drums({'kick': 'x.......x.x.....', 'snare': '....x.......x...',
                  'hat': 'x.xxx.xxx.xxx.xx', 'ohh': '..............x.'})
    beat_chorus = drums({'kick': 'x.......x.x.....', 'snare': '....x.......x...', 'clap': '....x.......x...',
                         'hat': 'x.xxx.xxx.xxx.xx', 'ohh': '..x...x...x...x.'})

    spread = dict(voicing='spread', register=('C3', 'C5'))
    b.pad.loop(verse_prog.block(**spread), intro, verse).loop(chorus_prog.block(**spread), chorus)
    b.pad.loop(verse_prog.block(**spread), outro)
    b.keys.loop(verse_prog.block(voicing='drop2', rhythm='x.x.x.x.', register=('C4', 'C5'), vel=78), verse)
    b.keys.loop(chorus_prog.block(voicing='drop2', rhythm='x..x..x.', register=('C4', 'C5'), vel=84), chorus)
    b.bass.loop(verse_prog.bass('octave', rate='1/8', gate=0.85), verse, vel=0.9)
    b.bass.loop(chorus_prog.bass('octave', rate='1/8', gate=0.85), chorus)
    b.brass.loop(chorus_prog.block(rhythm='...x...x', register=('C4', 'C5'), voices=3, gate=0.5), chorus)
    b.choir.loop(chorus_prog.block(register=('C3', 'C5'), voices=4), chorus)
    b.drums.loop(beat, verse, vel=0.9).loop(beat_chorus, chorus)
    b.drums.play(snare_roll(2, build=True), verse.beat(-2), replace=True)
    b.drums.play(crash(), verse).play(crash(), chorus).play(crash(), outro)
    b.lead.play(hook.clip(octave=4), chorus)

    b.pad.automate('instrument.cutoff', exp_ramp(outro.start, outro.end, 3000, 500))
    b.lead.automate('send.echo', hold(chorus.start, chorus.bar(7), -12), hold(chorus.bar(7), chorus.end, -4))
    return s
