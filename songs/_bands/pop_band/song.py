"""pop_band demo: 'Glass Summer' - 24 bars of radio pop in F major at 114 BPM, built only from the pop_band preset
and ordinary composition code: a pluck hook intro over the pad, a verse with Rhodes, bass and a sparse beat, a
four-on-the-floor chorus with claps and tambourine and the lead an octave up, and a post-chorus hook.

Credits: SampleRadar Chart Kit (royalty-free), Gimme A Hand (Hydrogen, GPL), Karoryfer Growlybass (CC0),
jRhodes3d (CC-BY-NC: Jeff Learman), Lexicon 224XL plate / bright hall (Little Devil), AgentSound synth patches.
"""
from agentsound import *
from agentsound import bands

ANALYSIS = {'profile': 'pop'}
METADATA = {'title': 'Glass Summer', 'artist': 'AgentSound', 'album': 'Band Presets', 'genre': 'Pop'}


def build() -> Song:
    s = Song('Glass Summer', tempo=114, key='F major', seed=31)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    post = s.section('post', bars=4)

    b = bands.pop_band(s)
    prog = s.prog('F C Dm Bb')                                  # I V vi IV
    cprog = s.prog('Bb F C Dm')                                 # IV I V vi: the chorus lifts off the IV

    # --- the hook (pluck), heard first in the intro, answered in the post-chorus
    hook = s.motif('5:0.5 6:0.5 8:0.75 6:0.25 5:0.5 3:0.5 5:1 | 2:0.5 3:0.5 5:0.75 3:0.25 2:1 1:1').clip(octave=5,
                                                                                                         vel=96)
    b.pluck.play(hook, intro, times=2).play(hook, post, times=2)
    b.pluck.loop(cprog.arp('up', rate='1/16', octaves=1, register=('F4', 'F5'), vel=70), chorus)

    # --- pad: whole bars everywhere, filtered open over the intro
    b.pad.loop(prog.block(voicing='spread', register=('F3', 'F5'), vel=80), intro, verse)
    b.pad.loop(cprog.block(voicing='spread', register=('F3', 'F5'), vel=86), chorus, post)
    b.pad.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 700, 3500),
                   hold(verse.start, post.end, 3500))

    # --- keys: Rhodes pushed 8ths
    b.keys.loop(prog.block(voicing='drop2', register=('A3', 'C5'), rhythm='x..x..x.', step='1/8', vel=70), verse)
    b.keys.loop(cprog.block(voicing='drop2', register=('A3', 'C5'), rhythm='x.x..x.x', step='1/8', vel=86), chorus,
                post)

    # --- drums + perc
    b.drums.loop(drums({'kick': 'x.........x.....', 'snare': '....x.......x...', 'hat': '..x...x...x...x.'},
                       vel=86), verse)
    b.drums.play(snare_roll(4, build=True), verse.bar(-1), replace=True)
    b.drums.play(crash(), chorus).play(crash(), post)
    four = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.',
                  'ohh': '..x...x...x...x.'}, vel=104).vel_pattern([1.1, 0.8, 1.0, 0.8], grid='1/8')
    b.drums.loop(four, chorus, post)
    b.perc.loop(drums({'clap': '....x.......x...', 'tamb': 'x.x.x.x.x.x.x.x.'}, vel=100), chorus, post)
    b.perc.loop(drums({70: 'x.xxx.xxx.xxx.xx'}, vel=70), verse)             # 70 = maracas (shaker)
    b.perc.play(drums({40: '............x...'}, vel=90), intro.bar(3))          # 40 = a finger snap

    # --- bass: half-note roots in the verse, driving octaves in the chorus, staccato disco octaves after it
    b.bass.loop(prog.bass('root', rate='1/2', low='E1', vel=74), verse)
    b.bass.loop(cprog.bass('octave', rate='1/8', low='E1', vel=104), chorus)
    b.bass.loop(cprog.bass('octave', rate='1/8', low='E1', vel=100).articulate('staccato'), post)
    # the verse sits under the chorus (the faders are the song's: the preset balance lives in fx 'trim')
    b.bass.automate('gainDb', per_section({verse: -4, chorus: 0, post: 0}, glide=0.25))
    b.keys.automate('gainDb', per_section({verse: -2, chorus: 0, post: 0}, glide=0.25))

    # --- lead: verse low and syncopated, chorus high with long notes
    v = s.motif('r:0.5 3:0.5 3:0.5 2:0.5 1:1 r:1 | r:0.5 3:0.5 5:0.5 3:0.5 2:2 | r:0.5 3:0.5 3:0.5 2:0.5 1:0.5 '
                '2:0.5 3:1 | 2:3 r:1').clip(octave=4, vel=80)
    c = s.motif('8:1 7:0.5 6:0.5 5:2 | r:0.5 5:0.5 6:0.5 8:0.5 7:2 | 6:1 5:0.5 3:0.5 5:2 | 5:3 r:1').clip(octave=4,
                                                                                                         vel=104)
    b.lead.play(v, verse, times=2)
    b.lead.play(c, chorus, times=2)
    b.lead.automate('send.echo', hold(verse.start, chorus.bar(3, 2), -14),
                    ramp(chorus.bar(3, 2), chorus.bar(4), -14, -6), hold(chorus.bar(4, 0.5), post.end, -14))
    return s
