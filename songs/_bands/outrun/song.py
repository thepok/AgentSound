"""Band preset demo: outrun (agentsound/bandlib/synthwave.py). Only the preset + ordinary composition code: no sound
design here, the band brings the sounds, the mix chains, the returns, the pump and the master.
Build: python -m agentsound build songs/_bands/outrun
Compare: python -m agentsound compare songs/_bands/outrun --section chorus --ref "assets/refrences/Kavinsky - Nightcall (Official Audio - HD) [46qo_V1zcOM].opus"
"""
from agentsound import *
from agentsound import bands

ANALYSIS = {'profile': 'synthwave'}                  # = bands.outrun(...).analysis


def build() -> Song:
    s = Song('Outrun Band Demo', tempo=106, key='F# minor', seed=11, tail=5)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    outro = s.section('outro', bars=4)

    b = bands.outrun(s)

    verse_prog = s.prog('i VI III VII')                     # F#m D A E
    chorus_prog = s.prog('VI VII i i')                       # D E F#m F#m: the lift
    hook = s.motif('5:1/4. 4:1/8 3:1/4 5:1/4 | 4:1/4. 3:1/8 2:1/4 1:1/4 | 3:1/8 5:1/4 8:1/8 7:1/4 5:1/4 | 5:1/2. r:1/4 '
                   '| 5:1/4. 4:1/8 3:1/4 5:1/4 | 4:1/4. 5:1/8 7:1/4 9:1/4 | 8:1/2. 7:1/8 5:1/8 | 8:1/2 r:1/2')
    beat = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...',
                  'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '..............x.'})
    beat_chorus = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'clap': '....x.......x...',
                         'hat': 'xxx.xxx.xxx.xxx.', 'ohh': '..x...x...x...x.'})

    pad_v = verse_prog.block(voicing='spread', register=('C3', 'C5'))
    pad_c = chorus_prog.block(voicing='spread', register=('C3', 'C5'))
    b.pad.loop(pad_v, intro, verse).loop(pad_c, chorus).loop(pad_v, outro)
    b.arp.loop(verse_prog.arp('updown', rate='1/16', octaves=2, register=('C4', 'C5')), intro, verse, outro)
    b.arp.loop(chorus_prog.arp('updown', rate='1/16', octaves=2, register=('C4', 'C5')), chorus)
    b.keys.loop(verse_prog.block(voicing='drop2', rhythm='x..x..x.', register=('C4', 'C5')), verse)
    b.keys.loop(chorus_prog.block(voicing='drop2', rhythm='x..x..x.', register=('C4', 'C5')), chorus)
    b.bass.loop(verse_prog.bass('octave', rate='1/8', gate=0.85), verse, vel=0.9)
    b.bass.loop(chorus_prog.bass('octave', rate='1/8', gate=0.85), chorus)
    b.drums.loop(drums({'hat': 'x.x.x.x.x.x.x.x.'}), intro.bar(2), bars=2, vel=0.6)
    b.drums.loop(beat, verse, vel=0.9).loop(beat_chorus, chorus)
    b.drums.play(snare_roll(4, build=True), verse.bar(-1), replace=True)
    b.drums.play(crash(), verse).play(crash(), chorus).play(crash(), outro)
    b.lead.play(hook.clip(octave=4), chorus)

    # dB on the preset's arp balance: the demo plays it 2 dB over it (as the preset was tuned)
    b.arp.automate('gainDb', ramp(intro.start, verse.start, -12, 2), ramp(outro.start, outro.end, 2, -14))
    b.pad.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 600, 3000),
                   exp_ramp(outro.start, outro.end, 3000, 500))
    b.lead.automate('send.echo', hold(chorus.start, chorus.bar(7), -12), hold(chorus.bar(7), chorus.end, -4))  # throw
    return s
