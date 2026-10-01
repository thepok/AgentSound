"""Band preset demo: darksynth (agentsound/bandlib/synthwave.py). Only the preset + ordinary composition code.
Build: python -m agentsound build songs/_bands/darksynth
Compare: python -m agentsound compare songs/_bands/darksynth --section drop --ref "assets/refrences/Perturbator - ＂Dangerous Days＂ [Full Album - Official] [1Vsf3zYppP4].opus" --ref-start 12:59 --ref-end 17:47
"""
from agentsound import *
from agentsound import bands

ANALYSIS = {'profile': 'darksynth'}                  # = bands.darksynth(...).analysis


def build() -> Song:
    s = Song('Darksynth Band Demo', tempo=118, key='E phrygian', seed=13, tail=4)
    intro = s.section('intro', bars=2)
    verse = s.section('verse', bars=8)
    drop = s.section('drop', bars=8)
    outro = s.section('outro', bars=2)

    b = bands.darksynth(s)

    prog = s.prog('i bII i bVII')                             # Em F Em D: the phrygian menace
    drop_prog = s.prog('i bVI bII V')                        # Em C F B: harmonic-minor V for the tension
    riff = s.motif('1:1/2 5:1/4 4:1/4 | 2:1/2 1:1/4 7:1/4 | 1:1/4 1:1/4 5:1/2 | 4:1/4 5:1/4 2:1/2 '
                   '| 1:1/2 5:1/4 8:1/4 | 7:1/2 5:1/4 4:1/4 | 2:1/4 4:1/4 5:1/2 | 1:1')
    four = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
    four_drop = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'clap': '....x.......x...',
                       'hat': 'xxxxxxxxxxxxxxxx', 'ohh': '..x...x...x...x.'})

    b.pad.loop(prog.block(register=('A3', 'A4'), voices=3), verse)
    b.pad.loop(drop_prog.block(register=('A3', 'A4'), voices=3), drop)
    b.arp.loop(prog.arp('up', rate='1/16', octaves=2, register=('E3', 'E4')), verse, outro)
    b.arp.loop(drop_prog.arp('updown', rate='1/16', octaves=2, register=('E3', 'E4')), drop)
    b.bass.loop(prog.bass('pulse', rate='1/8'), intro, verse)
    b.bass.loop(drop_prog.bass('octave', rate='1/16', gate=0.9), drop)
    b.stab.loop(drop_prog.block(rhythm='x..x..x.', register=('C4', 'C5'), voices=3), drop)
    b.drums.loop(drums({'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '..............x.'}), intro, vel=0.8)
    b.drums.loop(four, verse).loop(four_drop, drop).loop(four, outro, vel=0.8)
    b.drums.play(tom_fill(1), verse.bar(-1), replace=True).play(crash(), drop)
    b.lead.play(riff.clip(octave=4), drop)

    # dB on the preset's arp balance: the demo plays it 3 dB over it (as the preset was tuned), fading in the outro
    b.arp.automate('gainDb', ramp(outro.start, outro.end, 3, -11))     # (the first value holds before it)
    b.bass.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 400, 1800))
    b.drums.automate('gainDb', ramp(outro.start, outro.end, 0, -12))
    return s
