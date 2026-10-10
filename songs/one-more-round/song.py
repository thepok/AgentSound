"""One More Round - an original melodic-house / future-bass song (124 BPM, C minor, sung by Hanami, hard-tuned).

The last night of a summer fair: sugar on the fingers, the generator humming, the wheel's bulbs going out one by
one - and the two of them asking for one more turn. The idiom, not a song: a TR-909 four on the floor with a sine
sub, a reese bass pumped by the kick, soft supersaw chords that open in the builds, a pluck into the dotted-8th echo,
a bright high house piano, and Hanami's hard-tuned hook "one more round" CHOPPED into the drops (singer.chops: slices
of her own takes, pitched to a new line). A talk-box guitar says "round and round" after the first drop (singer.mouth
+ speech.talkbox), the second breakdown stacks the chorus into a prism (singer.prism).
Form: intro 8 | verse 16 | breakdown 8 | build 8 | DROP 16 | talk box 8 | breakdown 8 | build 8 | DROP 16 | outro 4.
Plan: BRIEF.md, ARRANGEMENT.md, LYRICS.md, SOUND.md, MIX.md, MASTER.md, AR.md.
Build: python -m agentsound build songs/one-more-round   (needs the Hanami + TIGER voicebanks and the WSL singing venv)
"""
from agentsound import *
from agentsound import articulation as art, bands, pianist, singer, speech
from agentsound.humanize import touch

ANALYSIS = {'profile': 'edm'}
METADATA = {'title': 'One More Round', 'artist': 'AgentSound', 'album': 'Night Fair', 'genre': 'Melodic House',
            'year': 2026}
COVER = {'style': 'synthwave', 'palette': ['#ff4f9a', '#ffd166'], 'title': 'ONE MORE ROUND', 'subtitle': 'NIGHT FAIR'}

MIX = {   # MIX.md: python -m agentsound mix songs/one-more-round (findings) + the drops' vocal over the drums
    'trim': {'pad': 6.0, 'chords': 4.0, 'pluck': 3.0, 'bass': -1.0, 'drums': -1.0, 'lead': -3.0, 'riser': -5.0,
             'vocal': -1.5, 'chops': -1.0},
    'ride': {'bass': {'drop': 2.5, 'drop2': 7.0}, 'pad': {'verse': 2.5, 'talkbox': -6.0}, 'drums': {'drop2': 1.0, 'drop': -1.0, 'build': -1.5, 'build2': -1.5},
             'vocal': {'verse': 1.5, 'drop2': 0.5}},
    'eq': {'chops': [{'freq': 1400.0, 'gain': -2.0, 'q': 1.0}], 'chords': [{'freq': 350.0, 'gain': -2.5, 'q': 0.9}],
           'pad': [{'freq': 400.0, 'gain': -2.0, 'q': 0.9}], 'lead': [{'freq': 450.0, 'gain': -2.0, 'q': 1.0}]},
}

PROG = 'Cm Ab Eb Bb'

# ------------------------------------------------------------------ the sung lines (Hanami, LYRICS.md), beats
VERSE = Clip([
    # Sugar on my fingers, tickets all used up,          (Cm | Ab)
    (0.0, 0.5, 'G4'), (0.5, 0.5, 'G4'), (1.0, 0.5, 'F4'), (1.5, 0.5, 'Eb4'), (2.0, 0.75, 'G4'), (2.75, 0.75, 'F4'),
    (4.0, 0.5, 'Eb4'), (4.5, 0.5, 'C4'), (5.0, 0.5, 'Eb4'), (5.5, 0.5, 'F4'), (6.0, 1.5, 'Eb4'),
    # generator humming like it's had enough,             (Eb | Bb)
    (8.0, 0.5, 'G4'), (8.5, 0.25, 'F4'), (8.75, 0.25, 'Eb4'), (9.0, 1.0, 'F4'), (10.0, 0.5, 'Bb4'),
    (10.5, 0.5, 'G4'), (11.0, 0.5, 'F4'), (11.5, 0.5, 'Eb4'), (12.0, 0.75, 'D4'), (12.75, 0.25, 'Eb4'),
    (13.0, 2.0, 'F4'),
    # someone's folding up the sky,                       (Cm | Ab)
    (16.0, 0.5, 'G4'), (16.5, 0.5, 'G4'), (17.0, 1.0, 'C5'), (18.0, 0.5, 'Bb4'), (18.5, 0.5, 'G4'),
    (19.5, 0.5, 'F4'), (20.0, 2.5, 'Eb4'),
    # one bulb at a time, goodbye.                        (Eb | Bb)
    (24.0, 0.5, 'Eb4'), (24.5, 0.5, 'F4'), (25.0, 0.5, 'G4'), (25.5, 0.5, 'F4'), (26.0, 1.5, 'G4'),
    (28.0, 0.75, 'F4'), (28.75, 2.75, 'D4'),
], length=32)
VERSE_WORDS = ("Sug-ar on my fin-gers, tick-ets all used up, gen-er-a-tor hum-ming like it's had e-nough, "
               "some-one's fold-ing up the sky, one bulb at a time, good-bye.")

PRE = Clip([
    # Hold the bar, don't look down,                      (Cm | Ab)
    (0.0, 1.0, 'C5'), (1.0, 0.5, 'Bb4'), (1.5, 1.5, 'G4'), (4.0, 0.5, 'Ab4'), (4.5, 0.5, 'G4'), (5.0, 2.0, 'Eb4'),
    # all the stars are on the house.                     (Eb | Bb)
    (8.0, 0.5, 'Eb4'), (8.5, 0.5, 'F4'), (9.0, 1.5, 'G4'), (10.5, 0.5, 'F4'), (11.0, 0.5, 'G4'),
    (11.5, 0.5, 'C5'), (12.0, 3.0, 'Bb4'),
], length=16)
PRE_WORDS = "Hold the bar, don't look down, all the stars are on the house."
PRE_PEAKS = [0.0, 12.0]

HOOK = Clip([
    # one more round, one more round, one more round, oh.         (Cm | Ab | Eb | Bb)
    (0.0, 0.5, 'G4'), (0.5, 0.5, 'Bb4'), (1.0, 2.0, 'C5'), (4.0, 0.5, 'G4'), (4.5, 0.5, 'Bb4'), (5.0, 2.0, 'C5'),
    (8.0, 0.5, 'Bb4'), (8.5, 0.5, 'C5'), (9.0, 2.0, 'Eb5'), (12.0, 3.0, 'D5'),
    # one more round, one more round, one more round.             (Cm | Ab | Eb) + a breath bar
    (16.0, 0.5, 'G4'), (16.5, 0.5, 'Bb4'), (17.0, 2.0, 'C5'), (20.0, 0.5, 'G4'), (20.5, 0.5, 'Bb4'),
    (21.0, 2.0, 'C5'), (24.0, 0.5, 'Bb4'), (24.5, 0.5, 'C5'), (25.0, 2.5, 'Eb5'),
], length=32)
HOOK_WORDS = "One more round, one more round, one more round, oh. One more round, one more round, one more round."
HOOK_PEAKS = [9.0, 25.0]

CHORUS = Clip([
    # One more round,                                     (Cm)
    (0.0, 0.5, 'G4'), (0.5, 0.5, 'Bb4'), (1.0, 2.0, 'C5'),
    # spin us up where the dark can't reach,              (Ab)
    (3.5, 0.5, 'C5'), (4.0, 0.5, 'C5'), (4.5, 0.5, 'Bb4'), (5.0, 0.5, 'C5'), (5.5, 0.5, 'Eb5'), (6.0, 0.5, 'C5'),
    (6.5, 0.5, 'Bb4'), (7.0, 1.0, 'Ab4'),
    # one more round,                                     (Eb)
    (8.0, 0.5, 'Bb4'), (8.5, 0.5, 'C5'), (9.0, 2.0, 'Eb5'),
    # all the stars are on the house.                     (Bb)
    (11.5, 0.5, 'D5'), (12.0, 0.5, 'C5'), (12.5, 0.5, 'Bb4'), (13.0, 0.5, 'C5'), (13.5, 0.5, 'Bb4'),
    (14.0, 0.5, 'F4'), (14.5, 1.5, 'G4'),
], length=16)
CHORUS_WORDS = "One more round, spin us up where the dark can't reach, one more round, all the stars are on the house."
CHORUS_PEAKS = [1.0, 9.0]

# the drop's hook: the chops (slices of HOOK) and the piano on the same line, an octave over the sung hook
DROP_HOOK = Clip([
    (0.0, 0.5, 'G5'), (0.75, 0.25, 'G5'), (1.0, 0.5, 'Bb5'), (1.5, 1.0, 'C6'), (2.5, 0.5, 'Bb5'), (3.0, 1.0, 'G5'),
    (4.0, 0.5, 'Eb5'), (4.75, 0.25, 'Eb5'), (5.0, 0.5, 'F5'), (5.5, 1.0, 'G5'), (6.5, 0.5, 'F5'), (7.0, 1.0, 'Eb5'),
    (8.0, 0.5, 'G5'), (8.75, 0.25, 'G5'), (9.0, 0.5, 'Bb5'), (9.5, 1.0, 'C6'), (10.5, 0.5, 'D6'), (11.0, 1.0, 'Eb6'),
    (12.0, 0.5, 'D6'), (12.5, 0.5, 'C6'), (13.0, 0.5, 'Bb5'), (13.5, 0.5, 'F5'), (14.0, 2.0, 'G5'),
], length=16)
# the second statement: the last bar climbs back up to the tonic instead of falling to G
DROP_HOOK_B = Clip([n for n in DROP_HOOK if n.start < 12] + [
    Note(12.0, 0.5, note('Eb6'), 100), Note(12.5, 0.5, note('D6'), 100), Note(13.0, 0.5, note('C6'), 100),
    Note(13.5, 0.5, note('Bb5'), 100), Note(14.0, 2.0, note('C6'), 100)], length=16)
# which slice of HOOK each chop plays (its syllables: 0 one, 1 more, 2 round, 3 one ... 8 round, 9 oh): per bar
# 'round - one more round, oh, round', each bar from the next statement (its own pitch and take)
CHOP_SLICES = [2, 0, 1, 2, 9, 2,  5, 3, 4, 5, 9, 5,  8, 6, 7, 8, 9, 8,  9, 4, 3, 4, 5]
# the chops' answer in drop 2 (under the sung chorus: only in its gaps, two-beat cells)
ANSWER = Clip([(3.0, 0.25, 'G5'), (3.25, 0.25, 'Bb5'), (3.5, 0.5, 'C6'),
               (11.0, 0.25, 'Bb5'), (11.25, 0.25, 'C6'), (11.5, 0.5, 'Eb6')], length=16)

# the talk box (TIGER mouths it, the guitar speaks it), LYRICS.md
TALK = Clip([(0.0, 0.5, 'G4'), (0.5, 0.5, 'Bb4'), (1.0, 2.0, 'C5'), (4.0, 1.0, 'Eb5'), (5.0, 2.0, 'C5'),
             (8.0, 0.5, 'G4'), (8.5, 0.5, 'Bb4'), (9.0, 3.0, 'G4'),
             (16.0, 0.5, 'G4'), (16.5, 0.5, 'Bb4'), (17.0, 2.0, 'C5'), (20.0, 1.0, 'Eb5'), (21.0, 2.0, 'F5'),
             (24.0, 0.5, 'Eb5'), (24.5, 0.5, 'D5'), (25.0, 3.0, 'C5')], length=32)
TALK_WORDS = "Round and round, ooh wah, round we go. Round and round, ooh wah, round we go."


def build() -> Song:
    s = Song(METADATA['title'], tempo=124, key='C minor', seed=11)
    prog = s.prog(PROG)
    intro = s.section('intro', bars=8, prog=prog)
    verse = s.section('verse', bars=16, prog=prog)
    brk1 = s.section('breakdown', bars=8, prog=prog)
    build1 = s.section('build', bars=8, prog=prog)
    drop1 = s.section('drop', bars=16, prog=prog)
    talk = s.section('talkbox', bars=8, prog=prog)
    brk2 = s.section('breakdown2', bars=8, prog=prog)
    build2 = s.section('build2', bars=8, prog=prog)
    drop2 = s.section('drop2', bars=16, prog=prog)
    outro = s.section('outro', bars=4, prog=s.prog('Cm Ab Cm Cm'))

    b = bands.make('melodic_house', s)
    g = b.info['grooves']

    # ---------------------------------------------------------------- drums (the preset's grooves + variation)
    drop_b = drums("kick: X...X...X...X... | clap: ....X.......X... | ohh: ..x...x...x...x. | hat: x.o.x.o.x.o.x.o. "
                   "| rim: ......x.......x. | 82: oxxooxxooxxooxxo | ride: x...x...x...x...".replace('|', '\n'), bars=1)
    no_kick = drums("clap: ....x.......x... | hat: ..x...x...x...x. | 82: oxxooxxooxxooxxo".replace('|', '\n'), bars=1)
    b.drums.plan({intro: [g['intro'], (4, g['groove'])], verse: g['groove'], brk1: g['break'],
                  build1: [g['build'], (7, None)], drop1: [g['drop'], (8, drop_b)], talk: [no_kick, (4, g['groove'])],
                  brk2: g['break'], build2: [g['build'], (7, None)], drop2: drop_b, outro: [g['intro'], (2, None)]},
                 fills={verse: (8, snare_roll(1)), drop1: (8, snare_roll(1)), drop2: (8, snare_roll(1)),
                        build1: (8, snare_roll(16, vel=(30, 100), build=True)),
                        build2: (8, snare_roll(16, vel=(30, 104), build=True))},
                 crashes={drop1: 120, drop1.bar(8): 108, drop2: 122, drop2.bar(8): 112, verse: 104, talk: 100})

    # ---------------------------------------------------------------- bass: reese over the clean sub
    b.bass.bassline('offbeat', verse, low='C1', vel=96, gate=0.8)
    b.bass.bassline('root', drop1, rate='1/2', low='C1', vel=104, gate=0.9)
    b.bass.bassline('offbeat', drop2, low='C1', vel=106, gate=0.8)
    b.bass.bassline('root', build1, build2, rate='1/4', low='C1', vel=84, gate=0.8, bars={build1: (0, 6),
                                                                                           build2: (0, 6)})
    b.bass.bassline('root', intro, rate='1/1', low='C1', vel=80, gate=0.95, bars={intro: (4, 8)})
    b.bass.bassline('offbeat', talk, low='C1', vel=92, gate=0.75, bars={talk: (4, 8)})
    b.bass.note('C1', outro.bar(2), 8, 92)

    # ---------------------------------------------------------------- chords, pad, pluck
    accents = lambda c: c.vel_pattern([1.0, 0.62, 0.86, 0.58], grid='1/4')      # noqa: E731
    b.chords.chords(drop1, drop2, voicing='spread', register=('C3', 'C5'), voices=4, rhythm='x..x..x.x..x..x.',
                    step='1/8', vel=104, then=accents)
    b.chords.chords(build1, build2, voicing='spread', register=('C3', 'C5'), voices=4, rhythm='x.x.x.x.', step='1/8',
                    vel=92, then=lambda c: touch(c, 58, 104))
    b.chords.lane('instrument.cutoff', {build1: (700, 7000, 'exp'), drop1: 5200, build2: (700, 7000, 'exp'),
                                        drop2: 5200})
    b.pad.chords(intro, brk1, brk2, outro, voicing='spread', register=('C3', 'C5'), vel=80)
    b.pad.chords(verse, talk, voicing='spread', register=('C3', 'C5'), vel=62)
    b.pad.lane('instrument.cutoff', {intro: (500, 2600, 'exp'), verse: 2600, brk1: 3000, outro: (3000, 600)})
    shape = lambda c: touch(c, 52, 100)                                         # noqa: E731
    b.pluck.arp('up', verse, rate='1/16', octaves=1, register=('G4', 'G5'), vel=74, then=shape)
    b.pluck.arp('updown', build1, build2, drop2, rate='1/16', octaves=2, register=('C4', 'C6'), vel=80, then=shape)
    b.pluck.arp('up', intro, rate='1/8', octaves=1, register=('G4', 'G5'), vel=66, bars={intro: (4, 8)}, then=shape)

    # ---------------------------------------------------------------- the vocal: Hanami, hard-tuned
    lead = dict(voice='hanami', style='pop', seed=5, tune='hard')
    mem = singer.Memory()
    singer.sing(s, VERSE, VERSE_WORDS, at=verse.bar(8), take=0, memory=mem, vel=(66, 104), **lead)
    singer.sing(s, PRE, PRE_WORDS, at=brk1, take=1, memory=mem, peaks=PRE_PEAKS, vel=(60, 100), **lead)
    hook1 = singer.sing(s, HOOK, HOOK_WORDS, at=build1, take=2, memory=mem, peaks=HOOK_PEAKS, vel=(70, 112), **lead)
    ch2 = singer.sing(s, CHORUS, CHORUS_WORDS, at=brk2, take=3, memory=mem, peaks=CHORUS_PEAKS, vel=(64, 108),
                      **lead)
    singer.sing(s, HOOK, HOOK_WORDS, at=build2, take=4, memory=mem, peaks=HOOK_PEAKS, vel=(74, 116), **lead)
    ch2b = singer.sing(s, CHORUS, CHORUS_WORDS, at=brk2.bar(4), take=6, memory=mem, peaks=CHORUS_PEAKS,
                       vel=(70, 112), **lead)
    for k, at in enumerate((drop2, drop2.bar(4))):
        singer.sing(s, CHORUS, CHORUS_WORDS, at=at, take=5 + 2 * k, memory=mem, peaks=CHORUS_PEAKS, vel=(74, 118),
                    **lead)
    vox = s.tracks['vocal']
    hero(vox, family='vocal', genre='pop', bed=[b.pad, b.chords], competitors=[b.pluck, b.lead, b.drums])

    # the prism: the second breakdown's chorus re-sung on the chord tones around it (hard-tuned, wide)
    pr = singer.prism(ch2b, s.harmony('Cm Ab Eb Bb', at=brk2.bar(4)), preset='prismizer')
    pr.bus.add_fx(fx.eq(hp__freq=200, peak1__freq=350, peak1__gain=-2.0, high__freq=9000, high__gain=1.5))
    pr.bus.send(s.node('hall'), -12)

    # ---------------------------------------------------------------- vocal chops: slices of the build's hook
    hook_line = touch(DROP_HOOK, 62, 116)
    singer.chops(hook1, hook_line, at=drop1, slices=CHOP_SLICES, sends={'echo': -9, 'hall': -16}, gain_db=-1.0,
                 pan=0.0, fx=[fx.chorus(mode='I+II', mix=0.4)])
    singer.chops(hook1, touch(DROP_HOOK_B, 62, 118), at=drop1.bar(4), slices=CHOP_SLICES)
    singer.chops(hook1, touch(DROP_HOOK.transpose(-12), 60, 108), at=drop1.bar(8), slices=CHOP_SLICES)
    singer.chops(hook1, touch(DROP_HOOK_B.transpose(-12), 60, 110), at=drop1.bar(12), slices=CHOP_SLICES)
    singer.chops(hook1, touch(ANSWER, 70, 108), at=drop2, slices=[0, 1, 2])
    singer.chops(hook1, touch(ANSWER, 70, 108), at=drop2.bar(4), slices=[4, 5, 6])
    singer.chops(hook1, hook_line, at=drop2.bar(8), slices=CHOP_SLICES)
    singer.chops(hook1, touch(DROP_HOOK_B, 64, 120), at=drop2.bar(12), slices=CHOP_SLICES)
    singer.chops(hook1, touch(Clip([(0, 0.5, 'G5'), (0.5, 0.5, 'Bb5'), (1.0, 2.5, 'C6')], length=4), 60, 96),
                 at=talk.bar(4), slices=[0, 1, 2])
    singer.chops(hook1, touch(Clip([(0, 0.5, 'G4'), (0.5, 0.5, 'Bb4'), (1.0, 3.0, 'C5')], length=4), 50, 80),
                 at=outro, slices=[0, 1, 2])
    chops_t = s.tracks['chops']
    b.drums.carve(chops_t, freq=3500, depth=3)           # the hats step aside in the chops' presence band
    chops_t.lane('send.echo', {drop1: -9, talk: -6, drop2: -9, outro: -4})

    # ---------------------------------------------------------------- the piano: soft hook, then the drop's octaves
    pmem = pianist.Memory()
    soft = pianist.arrange(touch(DROP_HOOK.transpose(-12), 40, 98), prog, bpm=124, key=s.key, style='ballad',
                           density=0.45, seed=3, memory=pmem, at=brk1.bar(4))
    b.lead.play(soft.rh, brk1.bar(4))
    big = pianist.arrange(touch(DROP_HOOK, 70, 118), prog, bpm=124, key=s.key, style='bar', density=0.5, seed=7,
                          climax=True, memory=pmem, at=drop1.bar(8))
    for at in (drop1.bar(8), drop1.bar(12), drop2.bar(8), drop2.bar(12)):
        b.lead.play(big.rh, at)
    b.lead.play(touch(prog.block(voicing='spread', register=('C4', 'C5'), vel=60), 48, 70), brk2)

    # ---------------------------------------------------------------- the talk box: a guitar says "round and round"
    gtr = s.track('talkbox', 'sampled/lead_guitar', gain_db=2.0, sends={'plate': -16, 'echo': -14})
    line = touch(TALK.transpose(-12), 82, 118)
    gtr.play(art.legato(line, overlap=0.04, max_gap=1.0).glide(70, where=art.leaps(2)), talk)
    art.vibrato(gtr, line, talk, depth=18, rate=5.2)
    m = singer.mouth(s, line.transpose(12), TALK_WORDS, at=talk, voice='tiger', seed=5)   # its velocities = the level
    speech.talkbox(gtr, m)
    # the box's LPC + the amp + the guitar's compressor flatten the picking: the accents as a gain lane after them
    gtr.add_fx(fx.utility(gain=0.0, name='accent'))
    pts, last = [], 0.0
    for n in line:
        db = round(-7.0 * (118 - n.vel) / 36.0, 2)
        pts += [[talk.start + n.start - 0.04, last], [talk.start + n.start, db]]
        last = db
    gtr.automate('fx.accent.gain', pts)

    # ---------------------------------------------------------------- transitions + the loudness arc
    fxh = s.transitions(riser=True, reverse=True, impact=True, down=True)
    fxh.into(drop1, riser=16, reverse=2, impact=('C2', 120), breath=1)
    fxh.into(drop2, riser=16, reverse=2, impact=('C2', 124), breath=1)
    fxh.into(talk, down=('C4', 8, 96))
    fxh.into(outro, down=('C4', 8, 90))
    for f in s.master.fx:                      # SOUND.md: the supersaw / pad walls a little wider (mono < 150 Hz)
        if f.type == 'width':
            f.params['width'] = 1.45
    s.master.lane('fx.limiter.gain', {intro: -6, verse: -4, brk1: -7, build1: (-8, -4.5), drop1: 0, talk: -3.5,
                                      brk2: -7, build2: (-8, -4.5), drop2: 0.5, outro: -6},
                  base=b.info['style']['master_gain'] + 1.0, glide=1)
    return s
