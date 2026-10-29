"""Drachen im Sandkasten - intro + outro for the Drama 3 kids scene (D:/Repos/drama3/out/scenes/sandkasten_lang).
A playful, small-orchestra adventure tune (original hook in F major): xylophone + clarinet theme, bassoon
staccato, upright bass, brushes, glockenspiel sparkle. 132 bpm (1 bar = 1.82 s).
Layout: intro (6 bars, theme, ends on a held chord) | gap (2 silent bars: reverb tail, cut point) |
outro (6 bars, theme reprise in a lighter scoring -> ritardando-like long final chord).
The scene assembly cuts the mix at the gap: intro = 0 .. gap.start, outro = outro.start .. end.

Build: python -m agentsound build songs/drachen-sandkasten
"""
from agentsound import *

METADATA = {'title': 'Drachen im Sandkasten (Intro/Outro)', 'artist': 'AgentSound', 'genre': 'Soundtrack',
            'year': 2026, 'comment': 'intro + outro for the kids sandbox audio scene'}
ANALYSIS = {'profile': 'film'}
COVER = {'style': 'synthwave', 'palette': 'sunset', 'title': 'DRACHEN IM SANDKASTEN', 'subtitle': 'AgentSound',
         'seed': 3}


def build() -> Song:
    s = Song('Drachen im Sandkasten', tempo=132, key='F major', seed=3)

    prog = s.prog('I vi IV V')                                   # F Dm Bb C
    intro = s.section('intro', bars=6, prog=s.prog('I vi IV V I I'))
    gap = s.section('gap', bars=2, prog=s.prog('I'))
    outro = s.section('outro', bars=6, prog=s.prog('IV V I vi IV V I'))

    hook = s.motif('1:1/8 3:1/8 5:1/8 r:1/8 6:1/8 5:1/8 3:1/4 | 4:1/8 6:1/8 8:1/8 r:1/8 7:1/8 6:1/8 5:1/4 '
                   '| 6:1/8 5:1/8 4:1/8 3:1/8 2:1/8 3:1/8 4:1/8 2:1/8 | 5:1/4 r:1/8 5:1/8 8:1/4 r:1/4')
    tail = s.motif('8:1/2. r:1/4 | 8:1/1')
    walk = drums({'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})

    s.hall(), s.plate()
    xylo = s.track('xylo', 'sampled/xylophone', gain_db=-2, pan=0.25)
    clar = s.track('clarinet', 'sampled/solo_clarinet', gain_db=0, pan=-0.2)
    glock = s.track('glock', 'sampled/glockenspiel', gain_db=-14, pan=0.4)
    bsn = s.track('bassoon', 'sampled/bassoon', gain_db=-5, pan=-0.3)
    bass = s.track('bass', 'sampled/upright_bass', gain_db=-3)
    strings = s.track('strings', 'sampled/strings', gain_db=-9)
    kit = s.track('brushes', 'sampled/brush_kit', gain_db=-8).humanize(3, 5)

    # intro: xylophone states the hook, clarinet answers an octave lower; outro: clarinet leads, xylophone doubles
    xylo.play(hook.clip(octave=5), intro)
    clar.play(hook.clip(octave=4), outro)
    xylo.play(hook.clip(octave=5).velocity(0.7), outro)
    clar.play(tail.clip(octave=4), intro.bar(4))
    xylo.play(tail.clip(octave=5).velocity(0.6), outro.bar(4))
    glock.arp('up', intro, outro, rate='1/8', octaves=1, register=('C6', 'C7'))

    bsn.chords(intro, outro, voicing='close', rhythm='x.x.x.x.', register=('F2', 'F3'))
    bass.bassline('octave', intro, outro, rate='1/4')
    strings.chords(intro, outro, voicing='spread', register=('C4', 'C5'))
    kit.plan({intro: walk, outro: walk.velocity(0.8)})
    return s
