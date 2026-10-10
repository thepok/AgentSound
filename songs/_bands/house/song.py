"""EDM band demo (the same 24 bars for every EDM preset - only STYLE, the tempo and the key differ): a filtered intro
on the groove, an 8-bar build (snare roll, riser, the chords opening), a breath, an 8-bar drop with the hook, the
crash and an impact, then the breakdown's pad. Built only from the preset, its grooves (band.info['grooves']) and
ordinary composition code.

Credits: the kit's samples (TR-909: hyperreal.org / Rob Roy Recordings, licence unclear - private listening; TR-808 /
main-room / modular: SampleRadar, royalty-free, no redistribution), Salamander Grand (CC-BY: Alexander Holm), the
AgentSound synth patches.
"""
from agentsound import *
from agentsound import bands
from agentsound.humanize import touch

STYLE, TEMPO, KEY, PROG = 'house', 124, 'A minor', 'i VI III VII'
ANALYSIS = {'profile': 'edm'}
METADATA = {'title': f'EDM preset: {STYLE}', 'artist': 'AgentSound', 'album': 'Band Presets', 'genre': 'Electronic'}


def build() -> Song:
    s = Song(f'EDM {STYLE}', tempo=TEMPO, key=KEY, seed=7)
    prog = s.prog(PROG)
    intro = s.section('intro', bars=4, prog=prog)
    build_ = s.section('build', bars=8, prog=prog)
    drop = s.section('drop', bars=8, prog=prog)
    brk = s.section('break', bars=4, prog=prog)
    b = bands.make(STYLE, s)
    g = b.info['grooves']
    half = STYLE == 'future_bass'

    # drums: the section grooves, a build roll into the drop, a crash on its downbeat
    b.drums.plan({intro: g['intro'], build_: g['build'], drop: g['drop'], brk: g['break']},
                 fills={build_: (8, snare_roll(4, build=True))}, crashes={drop: 118})
    # bass: offbeat 8ths (house / big room / techno) or held roots (future / melodic) in the drop, roots in the build
    if STYLE in ('house', 'big_room', 'techno'):
        b.bass.bassline('offbeat', drop, low='E1', vel=104, gate=0.8)
    else:
        b.bass.bassline('root', drop, rate='1/1', low='E1', vel=100, gate=0.95)
    b.bass.bassline('root', build_, rate='1/4', low='E1', vel=84, gate=0.8)
    # chords: the drop's rhythm; whole bars in the build (the filter opening is the riser's job)
    b.chords.chords(drop, voicing='spread', register=('C3', 'C5'), voices=4,
                    rhythm='x..x..x.' if not half else 'x._x_.x.', step='1/8', vel=96, then=lambda c: c.vel_pattern([1.0, 0.75, 0.9, 0.7], grid='1/4'))
    b.chords.chords(build_, voicing='spread', register=('C3', 'C5'), voices=4, vel=78)
    b.pad.chords(intro, brk, voicing='spread', register=('C3', 'C5'), vel=80)
    b.pluck.arp('up', build_, drop, rate='1/16', octaves=1, register=('A4', 'A5'), vel=78)
    hook = s.motif('5:0.75 4:0.25 3:0.5 1:0.5 3:1 2:1 | 5:0.75 6:0.25 5:0.5 3:0.5 2:2 '
                   '| 5:0.75 4:0.25 3:0.5 1:0.5 3:1 5:1 | 4:1.5 3:0.5 2:2').clip(octave=5, vel=104)
    hook = touch(hook, 60, 118)
    b.lead.play(hook, drop, times=2)
    if b.info['style']['lead'] == 'piano':
        b.lead.play(hook.transpose(-12).velocity(0.8), drop, times=2)          # the pianist's octave below
    fxh = s.transitions(riser=True, impact=True)
    fxh.into(drop, riser=dict(beats=16), impact=('A1', 120), breath=1)
    s.master.lane('fx.limiter.gain', {intro: -3, build_: -1.5, drop: 0, brk: -4}, base=b.info['style']['master_gain'])
    return s
