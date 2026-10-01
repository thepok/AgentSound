"""Band preset demo: scifi (agentsound/bandlib/synthwave.py). Only the preset + ordinary composition code.
Build: python -m agentsound build songs/_bands/scifi
Compare: python -m agentsound compare songs/_bands/scifi --section peak --ref "assets/refrences/Timecop1983 - Deckard's Dream [-d4ij5J4zJs].opus"
"""
from agentsound import *
from agentsound import bands

ANALYSIS = {'profile': 'dreamwave'}                  # = bands.scifi(...).analysis


def build() -> Song:
    s = Song('Scifi Band Demo', tempo=92, key='A minor', seed=3, tail=7)
    intro = s.section('intro', bars=4)
    build_ = s.section('build', bars=8)
    peak = s.section('peak', bars=8)
    outro = s.section('outro', bars=4)

    b = bands.scifi(s)

    prog = s.prog('i VI i VII')                              # Am F Am G
    peak_prog = s.prog('i VI iv V')                          # Am F Dm E: the harmonic-minor lift
    cell = [0, 2, 4, 7, 4, 2]                                # the Stranger-Things arp shape (chord tones up and down)
    theme = s.motif('5:1 4:1/2 3:1/2 | 2:2 | 3:1 5:1/2 8:1/2 | 7:2 | 5:1 4:1/2 3:1/2 | 2:1 3:1 | 1:2 | r:2')
    bells = s.motif('r:1 8:1/2 5:1/2 | r:2 | r:1 9:1/2 8:1/2 | r:2')
    sparse = drums({'kick': 'x.......x.......', 'snare': '........x.......', 'hat': '..x...x...x...x.'})
    full = drums({'kick': 'x.......x.x.....', 'snare': '........x.......', 'clap': '........x.......',
                  'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '..............x.'})

    b.arp.loop(prog.arp(rate='1/8', pattern=cell, register=('A3', 'A4')), intro, build_)
    b.arp.loop(peak_prog.arp(rate='1/8', pattern=cell, register=('A3', 'A4')), peak)
    b.pad.loop(prog.block(voicing='spread', register=('C3', 'C5')), intro, build_, outro)
    b.pad.loop(peak_prog.block(voicing='spread', register=('C3', 'C5')), peak)
    b.seq.loop(prog.arp('up', rate='1/16', octaves=2, register=('A2', 'A3')), build_.bar(4), bars=4)
    b.seq.loop(peak_prog.arp('up', rate='1/16', octaves=2, register=('A2', 'A3')), peak)
    b.bass.loop(prog.bass('root', rate='1/2').legato(), build_)
    b.bass.loop(peak_prog.bass('root', rate='1/2').legato(), peak)
    b.bells.loop(bells.clip(octave=5, vel=74), build_, peak, outro)
    b.drums.loop(sparse, build_, vel=0.8).loop(full, peak)
    b.drums.play(crash(), peak)
    b.lead.play(theme.clip(octave=4), peak)

    b.pad.automate('send.shimmer', hold(intro.start, build_.start, -8), hold(build_.start, outro.start, -14),
                   hold(outro.start, outro.end, -8))
    b.arp.automate('gainDb', ramp(intro.start, intro.bar(2), -13, 0))     # dB on the preset's arp balance
    return s
