"""Vocoder demo: a robot voice sings "neon lights, city nights, midnight drive" (Retrowave pop, 100 BPM, A minor).

16 bars. intro (4): pad and hats, the robot whispers "midnight drive" on a soft Am chord. verse (8): the robot
choir (synthwave/vocoder_choir) sings the line on the chords i VI III VII - one word per bar over a
four-on-the-floor beat and octave bass - and freezes the vowel of "drive" with the vocoder's 'hold' over the G bar.
outro (4): the talkbox (synthwave/talkbox, LPC mode) answers "mid-night drive" as a sliding melody, the choir hums
underneath. The words are Windows text-to-speech (agentsound.speech, voice Zira), cached in samples/speech/ so the
song re-renders identically on any machine.

Build: python -m agentsound build songs/_demo_vocoder
"""
from agentsound import *
from agentsound import speech

ANALYSIS = {'profile': 'synthwave'}


def build() -> Song:
    s = Song('Midnight Drive (vocoder demo)', tempo=100, key='A minor', seed=11)
    prog = s.prog('i VI III VII')                         # Am F C G, one bar each
    intro = s.section('intro', bars=4, prog=prog)
    verse = s.section('verse', bars=8, prog=prog)
    outro = s.section('outro', bars=4, prog=prog)

    # The words: one sample per word / phrase on consecutive keys (one-shot, -18 dBFS), cached next to this file,
    # on the voice track (the modulator: muted once a vocoder listens to it)
    vox = speech.voice(s, ['neon lights', 'city nights', 'midnight drive', 'midnight', 'drive'], voice='zira', rate=-2)

    hall, echo, gated = s.hall(decay=3.4, predelay=30), s.echo(), s.gated()
    kit = s.track('drums', 'synthwave/drums_outrun', gain_db=-1).groove('tight')
    bass = s.track('bass', 'synthwave/octave_bass', gain_db=-1)
    pad = s.track('pad', 'synthwave/juno_pad', gain_db=-4, fx=[fx.eq({'peak1.freq': 420, 'peak1.gain': -3})],
                  sends={hall: -6})
    choir = s.track('choir', 'synthwave/vocoder_choir', gain_db=-2, fx=[fx.width(width=1.3)], sends={hall: -5})
    talk = s.track('talkbox', 'synthwave/talkbox', gain_db=2, fx=[fx.chorus(mode='I', mix=0.3)],
                   sends={echo: -9, hall: -8})

    # the robot choir: a whispered teaser on a soft Am chord (intro), the line on the chords - a word per bar - over
    # the verse, the outro's words hummed on a held Am (the talkbox below sings them)
    line = {0: 'neon lights', 4: 'city nights', 8: 'midnight', 10: 'drive'}
    vox.robot(choir, say={intro.bar(2): 'midnight drive', verse: line, verse.bar(4): line,
                          outro: {0: 'midnight', 2: 'drive', 8: 'midnight drive'}},
              chords={intro.bar(2): ('A3 C4 E4', 7.5, 60), outro: ('A3 C4 E4', 16, 70)})
    choir.chords(verse, voicing='spread', register=('A2', 'E5'), voices=5)
    freeze = []                                           # 'drive' frozen over the G bar
    for half in (0, 4):
        drive = verse.bar(half + 2, 2)                    # 'drive' starts here, its vowel 0.1-0.35 s later
        freeze += [(drive - 2, 0), (drive + 0.4, 1, 'step'), (drive + 5.5, 0, 'step')]   # 'aaai' over C and G
    choir.automate('fx.vocoder.hold', freeze)

    # --- outro: the talkbox answers "mid-night drive" as a sung line (legato: it glides between syllables)
    talk.play(Clip([(0, 0.4, 'E3', 110), (0.4, 1.6, 'D3', 110), (2, 5.5, 'C3', 110),     # (low notes: more harmonics
                    (8, 0.4, 'E3', 110), (8.4, 0.7, 'G3', 110), (9.1, 6.4, 'A3', 110)], length=16), outro)  # to shape)
    talk.automate('fx.vocoder.hold', [(outro.start, 0), (outro.beat(2.4), 1, 'step'), (outro.beat(7.5), 0, 'step'),
                                      (outro.beat(9.5), 1, 'step'), (outro.beat(15.5), 0, 'step')])
    speech.vocode(talk, vox.track)                        # both vocoders listen to the same voice track

    # --- the band
    pad.chords(s.sections, voicing='smooth', register=('E3', 'E5'))
    pad.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 900, 3000),
                 exp_ramp(outro.start, outro.end, 3000, 700))
    pad.automate('gainDb', [(outro.start, 0), (outro.beat(4), -6, 'smooth'),
                            (outro.end, -12)])     # the outro strips down: room for the talkbox (dB on gain_db)

    kit.plan({intro: drums({'hat': '..x...x...x...x.'}),
              verse: drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.xo'}),
              outro: drums({'kick': 'x...x...x...x...', 'snare': '............x...', 'hat': '..x...x...x...x.'})},
             fills={verse: snare_roll(1, build=True)}, crashes=[verse])
    bass.bassline({verse: 'octave', outro: 'offbeat'}, verse, outro, rate={verse: '1/8'})
    s.sidechain(pad, bass, key=kit, pitches='kick', depth=9, release=180)

    s.master.use(patches.get('master/synthwave').but_fx('limiter', gain=6))
    return s
