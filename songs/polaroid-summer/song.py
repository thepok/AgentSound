"""Summer, Overexposed  -  dreamwave / chillsynth (FM-84, Timecop1983), 88 BPM, D major -> E major.

Sub-style: Dreamwave / chillsynth, built on the reference-calibrated band preset bands.dreamwave (soft LinnDrum,
moog bass, dream pad + Juno strings, DX7 E.PIANO 1, soft lead, dark 224XL hall, tape echo, shimmer, master/dreamwave)
plus an alto sax played with the realism engine (legato, live dynamics, delayed vibrato, scoops), a sampled choir, a
glassy CELESTE arp, a vocoder that says the title twice, and the fx hits (riser, downlifter, impact).

Harmony: the signature move is IVmaj7 -> iv6 (Gmaj7 -> Gm6, the B -> Bb -> A inner line: the photograph fading).
Lydian colour from IVmaj7 with the #11 (C# over G) in the melody, maj7 / add9 tonics. Pre-chorus lifts through
bVI - bVII (Bb - C) into the tonic; the last lift uses C - D = bVI - bVII of E major and the final chorus lands a
whole step up. The ending is plagal and minor: Am6 -> Emaj9, slowing down (tempo map) into a held, rolled chord.

Form (96 bars, ~4:25):  intro 8 | verse1 16 | pre 4 | chorus1 16 | verse2 8 | breakdown 8 | solo 8 | lift 4 |
final 16 (E major) | outro 8 (ritardando).
"""
from agentsound import *
from agentsound import articulation as art
from agentsound import bands, jazz, speech

ANALYSIS = {'profile': 'dreamwave'}              # = bands.dreamwave(...).analysis

METADATA = {'title': 'Summer, Overexposed', 'artist': 'AgentSound', 'album': 'Neon Archive', 'genre': 'Synthwave',
            'year': 2026, 'comment': 'Dreamwave, 88 BPM, D major -> E major. A summer you only remember from a '
                                     'sun-bleached photograph.'}
COVER = {'style': 'dreamwave', 'title': 'SUMMER, OVEREXPOSED', 'subtitle': 'AgentSound', 'seed': 1986}


def build() -> Song:
    s = Song('Summer, Overexposed', tempo=88, key='D major', seed=1986, tail=10.0)

    intro = s.section('intro', bars=8)
    verse1 = s.section('verse1', bars=16)
    pre = s.section('pre', bars=4)
    chorus1 = s.section('chorus1', bars=16)
    verse2 = s.section('verse2', bars=8)
    brk = s.section('breakdown', bars=8)
    solo = s.section('solo', bars=8)
    lift = s.section('lift', bars=4)
    final = s.section('final', bars=16)
    outro = s.section('outro', bars=8)

    E = 'E major'           # the last chorus / outro key

    # ------------------------------------------------------------------ harmony
    VERSE = s.prog('Dmaj7 F#m7 Gmaj7 Gm6')                       # I iii IVmaj7 iv6
    PRE = s.prog('Em7 F#m7 Gmaj7 Bbmaj7:0.5 Cadd9:0.5')          # ii iii IV | bVI bVII -> I
    CHORUS = s.prog('Dadd9 A/C# Bm7 Gmaj7 Em7 F#m7 Gmaj7 Gm6')   # I V/3 vi IV ii iii IV iv
    BREAK = s.prog('Bbmaj7 Cadd9 Dmaj7 Bm7 Bbmaj7 Cadd9 Gm6 %')  # borrowed bVI bVII colour
    SOLO = s.prog('Dadd9 A/C# Bm7 Gmaj7 Em7 F#m7 Gmaj7 A7sus4')  # the chorus changes, a V7sus4 turn at the end
    LIFT = s.prog('Em7 F#m7 Gmaj7 Cmaj7:0.5 Dadd9:0.5')          # ... C D = bVI bVII of E
    CHORUS_E = CHORUS.transpose(2)
    OUTRO = s.prog('Emaj7 G#m7 Amaj7 Am6 Emaj7 G#m7 Am6 Emaj9')
    OUTRO_COMP = s.prog('Emaj7 G#m7 Amaj7 Am6 Emaj7 G#m7 Am6')

    # ------------------------------------------------------------------ melodies (scale degrees)
    # The hook cell: x . . (x-1) | x . (x+2) - a sigh and a lift. Everything below grows from it.
    VERSE_A = '8:1/4. 7:1/8 8:1/4 10:1/4 | 9:1/2 r:1/2 | 8:1/4. 7:1/8 8:1/4 9:1/4 | b6:1/2. 5:1/4'
    VERSE_B = '8:1/4. 7:1/8 8:1/4 12:1/4 | 10:1/2 9:1/4 7:1/4 | 8:1/2 7:1/4 6:1/4 | b6:1/2 5:1/2'
    VERSE_A2 = '8:1/4. 7:1/8 8:1/4 10:1/4 | 9:1/2 r:1/2 | 8:1/4. 9:1/8 10:1/4 12:1/4 | b6:1/2. 5:1/4'
    VERSE_B2 = '8:1/4. 7:1/8 8:1/4 12:1/4 | 10:1/2 9:1/4 7:1/4 | 8:1/2 9:1/4 10:1/4 | 11:1/2. r:1/4'
    # answers in the gaps of a 4-bar phrase (bar 2 and bar 4)
    ANSWER = 'r:1/1 | r:1/2 7:1/8 5:1/8 3:1/4 | r:1/1 | r:1/2 b6:1/8 4:1/8 2:1/4'
    ANSWER2 = 'r:1/1 | r:1/2 5:1/8 6:1/8 5:1/4 | r:1/1 | r:1/2 9:1/8 8:1/8 b6:1/4'

    PRE_M = '2:1/4. 1:1/8 2:1/4 4:1/4 | 3:1/4. 2:1/8 3:1/4 5:1/4 | 4:1/4. 3:1/8 4:1/4 6:1/4 | b6:1/2 b7:1/4 r:1/4'
    LIFT_M = '2:1/4. 1:1/8 2:1/4 4:1/4 | 3:1/4. 2:1/8 3:1/4 5:1/4 | 4:1/4. 3:1/8 4:1/4 6:1/4 | b7:1/2 8:1/4 r:1/4'

    HOOK_A = '3:1/4. 2:1/8 3:1/4 5:1/4 | 2:1/2 r:1/4 1:1/8 2:1/8 | 3:1/4. 2:1/8 3:1/4 6:1/4 | 7:1/4 6:1/4 5:1/2'
    HOOK_B = '2:1/4. 1:1/8 2:1/4 4:1/4 | 3:1/2 r:1/4 5:1/8 6:1/8 | 8:1/4. 7:1/8 5:1/2 | b6:1/2 5:1/2'
    HOOK_A2 = '3:1/4. 2:1/8 3:1/4 5:1/4 | 2:1/2 r:1/4 1:1/8 2:1/8 | 3:1/4. 2:1/8 3:1/4 6:1/4 | 7:1/4 8:1/4 9:1/2'
    HOOK_B2 = '2:1/4. 1:1/8 2:1/4 5:1/4 | 6:1/2 5:1/4 3:1/4 | 8:1/4. 9:1/8 8:1/4 7:1/4 | b6:1/2. 5:1/4'
    HOOK = ' | '.join((HOOK_A, HOOK_B, HOOK_A2, HOOK_B2))
    # harmony a third/fourth under HOOK_A2 + HOOK_B2 (octave 4 degrees)
    HARM = ('8:1/4. 7:1/8 8:1/4 10:1/4 | 7:1/2 r:1/4 5:1/8 7:1/8 | 8:1/4. 7:1/8 8:1/4 10:1/4 | 12:1/4 13:1/4 14:1/2 | '
            '6:1/4. 6:1/8 6:1/4 9:1/4 | 10:1/2 10:1/4 7:1/4 | 13:1/4. 14:1/8 13:1/4 12:1/4 | 11:1/2. 10:1/4')

    BREAK_M = ('8:1/4. b7:1/8 8:1/4 b10:1/4 | 9:1/2 r:1/4 8:1/8 9:1/8 | 10:1/4. 9:1/8 10:1/4 12:1/4 | 10:1/2 9:1/4 8:1/4 | '
               '8:1/4. b7:1/8 8:1/4 b10:1/4 | 9:1/2 r:1/4 8:1/8 9:1/8 | b13:1/2 12:1/2 | 12:1/1')
    # the alto sax solo over the chorus changes (octave 4: D4 = 1; the alto tops out at G#5 = degree 11 here)
    SOLO_M = ('r:1/8 5:1/8 6:1/8 8:1/8 10:1/2 | 9:1/8 10:1/8 9:1/4 7:1/4 5:1/4 | 6:1/4. 5:1/8 6:1/4 8:1/4 | '
              '10:1/4 9:1/8 8:1/8 7:1/2 | 5:1/8 6:1/8 8:1/8 9:1/8 11:1/2 | 10:1/4. 9:1/8 8:1/4 6:1/4 | '
              '7:1/4. 8:1/8 9:1/2 | 9:1/8 8:1/8 5:1/4 4:1/2')
    OUTRO_M = '3:1/4. 2:1/8 3:1/4 5:1/4 | 2:1/1 | 3:1/4. 2:1/8 3:1/4 1:1/4 | 1:1/1'
    # the hook cell displaced by a beat - the memory slightly out of step
    OUTRO_EP = 'r:1/1 | r:1/1 | r:1/1 | r:1/1 | r:1/4 3:1/4. 2:1/8 3:1/4 | 5:1/4 2:1/2. | b6:1/2 5:1/2 | 3:1/1'
    # the sax's last word: the Bb-A sigh (here C-B), an octave under the E.piano's displaced hook
    OUTRO_SAX = 'r:1/1 | r:1/1 | r:1/1 | r:1/1 | r:1/1 | r:1/2 5:1/4 6:1/4 | b6:1/2. 5:1/4 | 3:1/1'

    def mD(spec):
        return Motif(spec, 'D major')

    def mE(spec):
        return Motif(spec, E)

    # ------------------------------------------------------------------ the band (reference-calibrated preset)
    # the preset's soft LinnDrum with the kick 3 dB forward (the reference's kick stands 12 dB over the wall)
    linn = inst.kit('samples/hyperreal-linndrum', gains={'hats': -14, 'cymbals': -7, 'kick': 5.0}, lazy=True,
                    level=0.0)
    b = bands.dreamwave(s, sounds={'lead': patches.get('synthwave/soft_lead').but(**{'osc2.level': 0.45}),
                                   'drums': linn})
    hall, plate, echo, shimmer = b.buses['hall'], b.buses['plate'], b.buses['echo'], b.buses['shimmer']
    kit, bass, pad, strings, ep, lead = b.drums, b.bass, b.pad, b.strings, b.keys, b.lead
    kit.groove('laidback').humanize(2, 4)
    for f in kit.fx:
        if f.type == 'compressor':
            f.params['attack'] = 25.0      # let the kick's attack through the kit glue (punch)
            f.params['ratio'] = 2.5
    ep.humanize(5, 6)
    lead.humanize(3, 4)
    # tone against the reference (loudness-matched compare): the soft lead and the keys carried +4 dB of 0.5-3.5 kHz
    lead.add_fx(fx.eq({'peak2.freq': 1200, 'peak2.gain': -3.5, 'peak2.q': 0.5, 'peak3.freq': 2100,
                       'peak3.gain': -2.5, 'peak3.q': 1.1}))
    ep.add_fx(fx.eq({'peak1.freq': 420, 'peak1.gain': 0.0, 'peak1.q': 0.8, 'peak2.freq': 1000, 'peak2.gain': -2.0,
                     'peak2.q': 0.7, 'peak3.freq': 3200, 'peak3.gain': -1.5, 'peak3.q': 0.8}, name='tone'))
    ep.add_fx(fx.eq({'peak1.freq': 720, 'peak1.gain': -1.5, 'peak1.q': 1.6}))     # 560-900 Hz ran +1.6 dB
    ep.automate('fx.tone.peak1.gain', per_section({intro: -5.0, verse1: 0.0}, glide=2))   # the pad owns the intro's body
    pad.add_fx(fx.eq({'peak2.freq': 1200, 'peak2.gain': 0.0, 'peak2.q': 0.9, 'peak3.freq': 2300, 'peak3.gain': -3.0,
                      'peak3.q': 0.8}, name='carve'))
    # the pad makes room for the E.piano where the two are alone together (intro, breakdown: they masked 0.8-2.5 kHz)
    pad.automate('fx.carve.peak2.gain', per_section({intro: -4.0, verse1: 0.0, brk: -4.0, solo: 0.0, outro: -2.0},
                                                    glide=2))
    strings.add_fx(fx.eq({'peak3.freq': 3500, 'peak3.gain': -3.0, 'peak3.q': 0.8}))
    s.sidechain(bass, key=kit, pitches='kick', depth=8, release=170)      # + the preset's 3 dB: the kick breathes
    # roots from G1: the G1 / F#1 fundamentals and the rumble under them stay in proportion (no sub boom)
    bass.add_fx(fx.eq({'low.freq': 40, 'low.gain': -3.0, 'peak1.freq': 105, 'peak1.gain': -2.5, 'peak1.q': 1.8,
                       'peak3.freq': 49, 'peak3.gain': -3.0, 'peak3.q': 1.2}))     # 90-140 Hz ran +1.8 dB
    # the reference's 200-350 Hz warmth comes from the wide bed, not from the (mono) bass
    pad.add_fx(fx.eq({'peak1.freq': 250, 'peak1.gain': 1.0, 'peak1.q': 0.9}))
    # width: the preset narrows the pad (0.75) so pad-only passages stay mono-safe; open it where the drums play
    pad.automate('fx.width.width', per_section({intro: 0.75, verse1: 1.0, brk: 0.75, solo: 1.05, outro: 0.8},
                                               glide=2))
    ep.add_fx(fx.width(width=1.15, monobass=140))
    for f in pad.fx:
        if f.type == 'width':
            f.params['monobass'] = 140      # the pad's chorus spreads its lowest notes: keep the lows mono
    # the E.piano alone (intro, breakdown, the last chord) stays at its own width: mono-safe
    ep.automate('fx.width.width', per_section({intro: 0.85, verse1: 1.15, brk: 0.85, solo: 1.15, outro: 0.9},
                                              glide=2))
    # master: the preset's chain with broad 650 Hz / 1.9 kHz dips and a gentle top shelf in front of it (this
    # arrangement carries more mid-range parts than the preset's calibration demo: E.piano, lead, sax, harmony,
    # choir, arp) and 3.1 dB more limiter drive (the reference's loudness)
    s.master.add_fx(fx.eq({'peak1.freq': 700, 'peak1.gain': -5.5, 'peak1.q': 0.9, 'peak2.freq': 2000,
                           'peak2.gain': -5.0, 'peak2.q': 0.6, 'peak3.freq': 2250, 'peak3.gain': -1.5,
                           'peak3.q': 2.0, 'high.freq': 5000, 'high.gain': -1.5}, name='tone'),
                    first=True)
    # the final chorus (sax + doubled lead + harmony + choir) piles up 1.5-3 kHz: a deeper dip there only
    s.master.automate('fx.tone.peak2.gain', per_section({intro: -5.0, final: -6.5, outro: -5.0}, glide=2))
    for f in s.master.fx:
        if f.type == 'limiter':
            f.params['gain'] = 5.0
    # the energy arc the limiter flattened: chorus 1 drives it a little less, the final E-major chorus more
    s.master.automate('fx.limiter.gain', per_section({intro: 5.0, chorus1: 4.2, verse2: 5.0, final: 5.5,
                                                      outro: 5.0}, glide=1))
    # a wider wall where the drums play (the reference is twice as wide); the drumless parts stay mono-safe
    s.master.automate('fx.width.width', per_section({intro: 1.3, verse1: 1.6, brk: 1.35, solo: 1.7,
                                                     outro: 1.4}, glide=2))

    # extra parts
    lead2 = s.track('lead2', patches.get('synthwave/soft_lead'), gain_db=-7, pan=0.2,
                    fx=[fx.chorus(mode='II', mix=0.4)], sends={hall: -6, echo: -14}).humanize(4, 4)
    sax = s.track('sax', 'sampled/alto_sax', gain_db=6, pan=0.08,
                  fx=[fx.eq({'peak1.freq': 320, 'peak1.gain': -2.5, 'peak1.q': 0.9, 'peak3.freq': 2400,
                             'peak3.gain': -2.5, 'peak3.q': 0.9, 'high.freq': 9000, 'high.gain': -2}),
                      fx.compressor(threshold=-22, ratio=3, attack=12, release=120, knee=6),
                      fx.microshift(style='smooth', detune=7, mix=0.2)],
                  sends={hall: -8, plate: -14, echo: -16})
    glass = s.track('glass', 'synthwave/arp_glass', gain_db=-6, pan=0.3,
                    fx=[fx.eq({'hp.freq': 400, 'peak2.freq': 1100, 'peak2.gain': -2.5, 'peak2.q': 0.8,
                               'high.freq': 6000, 'high.gain': -3})],
                    sends={echo: -10, hall: -12})
    choir = s.track('choir', 'sampled/choir', gain_db=-7, fx=[fx.eq({'hp.freq': 200, 'peak1.freq': 400,
                                                                     'peak1.gain': -2, 'peak1.q': 0.8}),
                                                              fx.chorus(mode='II', mix=0.3)],
                    sends={hall: -6, shimmer: -14})
    vox = s.track('vox', 'synthwave/vocoder_choir', gain_db=-4, sends={hall: -6, echo: -12, shimmer: -12})
    riser_t = s.track('riser', 'synthwave/noise_riser', gain_db=-10,
                      fx=[fx.eq({'peak1.freq': 4200, 'peak1.gain': -5, 'peak1.q': 0.8, 'lp.freq': 9000})],
                      sends={hall: -12})
    down = s.track('down', 'synthwave/downlifter', gain_db=-11, sends={hall: -12})
    boom = s.track('impact', 'synthwave/impact', gain_db=5, sends={hall: -10})
    s.sidechain(glass, choir, key=kit, pitches='kick', depth=4, release=260)
    s.sidechain(pad, strings, key=kit, pitches='kick', depth=2, release=240)   # + the preset's 4 dB

    # the robot says the title (Windows TTS, cached in samples/speech/)
    words = speech.words(['summer', 'overexposed'], voice='zira', rate=-3)
    voice = s.track('voice', words.instrument())
    speech.vocode(vox, voice)

    # ------------------------------------------------------------------ drums (soft LinnDrum)
    CAB = 69            # LinnDrum cabasa
    g_intro = drums({'hat': '..4...4...4...4.', CAB: '....3.......3...'})
    g_verse = drums('''kick:  X.....6.........|X.........6.....
                       snare: ........x.......
                       hat:   5.3.5.3.5.3.5.3.''')
    g_verse_b = drums('''kick:  X.....6.........|X.........6..5..
                         snare: ........x.......|........x.....o.
                         hat:   5.3.5.3.5.3.5.33|5.3.5.3.5.3.5.3.
                         tamb:  ....3.......3...''')
    g_chorus = drums('''kick:  X.....6.x.......|X.....6.x.....6.
                        snare: ....x.......x...
                        clap:  ....x.......x...
                        hat:   6353635363536353|6353635363536...
                        ohh:   ................|..............5.
                        tamb:  3424342434243424''')
    g_verse2 = drums('''kick:  X.....6...6.....|X.....6.......6.
                        snare: ........x.......
                        rim:   ...3......3....3|......3.....3...
                        hat:   4343434343434343''')
    g_solo = drums({'kick': 'X.....6.........|X.........6.....', 'snare': '........x.......',
                    'hat': '5.3.5.3.5.3.5.3.', CAB: '..3...3...3...3.',
                    64: '......4.......4.|......4...4...4.', 63: '...3......3.....'})
    g_build = drums('''kick:  x...x...x...x...
                       snare: ........x.......
                       hat:   4343434343434343''')
    g_final = drums('''kick:  X.....6.x.....6.|X.....6.x...6.6.
                       snare: ....x.......x...
                       clap:  ....x.......x...
                       hat:   6353635363536353|6353635363536...
                       ohh:   ................|..............6.
                       tamb:  3424342434243424''')
    g_outro = drums('''kick:  x.........6.....
                       snare: ........o.......
                       hat:   4.3.4.3.4.3.4.3.''')

    kit.loop(g_intro, intro.bar(4), bars=4)
    kit.loop(g_verse, verse1.start, bars=8).loop(g_verse_b, verse1.bar(8), bars=8)
    kit.play(tom_fill(1, vel=(60, 90)), verse1.beat(-1), replace=True)
    kit.loop(g_build, pre)
    kit.play(snare_roll(7, build=True, vel=(40, 110)), pre.bar(2), replace=True)
    kit.play(drums({'kick': 'x...x...x...x...'}, bars=2), pre.bar(2))
    kit.loop(g_chorus, chorus1)
    kit.play(crash(96), chorus1).play(crash(84), chorus1.bar(8))
    kit.play(tom_fill(1, vel=(70, 100)), chorus1.bar(7, 3), replace=True)
    kit.play(tom_fill(2, vel=(70, 105)), chorus1.bar(15, 2), replace=True)
    kit.loop(g_verse2, verse2)
    kit.play(drums({'hat': '5.3.5.3.5.3.5.3.', 'ohh': '..............5.'}), verse2.bar(-1), replace=True)
    kit.play(crash(84), brk)
    kit.loop(drums({'kick': 'x.......6.......', 'hat': '..3...3...3...3.'}), brk.bar(6), bars=2)
    kit.play(snare_roll(1, vel=(30, 80)), brk.beat(-1), replace=True)
    kit.loop(g_solo, solo)
    kit.play(crash(76), solo)
    kit.play(tom_fill(1, vel=(60, 95)), solo.beat(-1), replace=True)
    kit.loop(g_build, lift)
    kit.play(snare_roll(7, build=True, vel=(45, 116)), lift.bar(2), replace=True)
    kit.play(drums({'kick': 'x...x...x...x...'}, bars=2), lift.bar(2))
    kit.loop(g_final, final)
    kit.play(crash(100), final).play(crash(90), final.bar(8))
    kit.play(tom_fill(1, vel=(75, 105)), final.bar(7, 3), replace=True)
    kit.play(tom_fill(2, vel=(80, 112)), final.bar(15, 2), replace=True)
    kit.loop(g_outro, outro.start, bars=4)
    kit.loop(drums({'hat': '3.2.3.2.3.2.3.2.'}), outro.bar(4), bars=2)
    kit.play(crash(84), outro)

    # ------------------------------------------------------------------ bass (moog, tied roots: the dense low end)
    def bl(prog, pattern, vel=96):
        return prog.bass(pattern=pattern, rate='1/8', low='G1', gate=1.0, vel=vel).legato(0.03)

    bass.loop(bl(VERSE, 'r_______', vel=90), verse1.start, bars=8)
    bass.loop(bl(VERSE, 'r_____r_', vel=92), verse1.bar(8), bars=8)
    bass.play(bl(PRE, 'r___r___'), pre)
    bass.loop(bl(CHORUS, 'r__r__o_'), chorus1)
    bass.loop(bl(VERSE, 'r_____o_', vel=92), verse2)
    bass.play(bl(BREAK, 'r_______', vel=84).slice(16), brk.bar(4))      # the bass returns halfway
    bass.loop(bl(SOLO, 'r_____r_', vel=94), solo)
    bass.play(bl(LIFT, 'r___r___'), lift)
    bass.loop(bl(CHORUS_E, 'r__r__or'), final)
    bass.play(bl(OUTRO, 'r_______', vel=88), outro)

    # ------------------------------------------------------------------ pad (dream pad, spread voicings)
    def padc(prog, reg=('C3', 'C5'), vel=80):
        return chords(prog, voicing='spread', register=reg, voices=4, vel=vel)

    pad.loop(padc(VERSE, ('D3', 'A4')), intro)       # low under the E.piano: the picture develops
    pad.loop(padc(VERSE), verse1, verse2)
    pad.clear(intro.start, intro.bar(2))              # the E.piano starts alone, the pad develops in at bar 3
    pad.play(padc(PRE, ('D3', 'D5')), pre)
    pad.loop(padc(CHORUS, ('E3', 'E5')), chorus1)
    # the breakdown: a low, dark bed under the E.piano from its first bar (the E.piano alone left a 13 LU hole,
    # phasey in mono), the cutoff opening later
    pad.play(padc(BREAK, ('D3', 'A4'), vel=70), brk)
    pad.loop(padc(SOLO), solo)
    pad.play(padc(LIFT, ('D3', 'D5')), lift)
    pad.loop(padc(CHORUS_E, ('F#3', 'F#5')), final)
    pad.play(padc(OUTRO, ('E3', 'B4')), outro)

    # strings: a quiet second bed in verse 1 (B half), the chorus lift, the solo, the final
    def strc(prog, reg=('A3', 'A5'), vel=78):
        return chords(prog, voicing='spread', register=reg, voices=3, vel=vel)

    strings.loop(strc(VERSE, vel=66), verse1.bar(8), bars=8)
    strings.loop(strc(CHORUS, ('F#3', 'F#5'), vel=74), chorus1.start, bars=8)
    strings.loop(strc(CHORUS, ('A3', 'A5'), vel=84), chorus1.bar(8), bars=8)
    strings.loop(strc(VERSE, ('D4', 'D6'), vel=62), verse2)     # a high, thin second bed under the E.piano's song
    strings.loop(strc(SOLO, vel=74), solo)
    strings.play(strc(LIFT, vel=80), lift)
    strings.loop(strc(CHORUS_E, ('G#3', 'G#5'), vel=80), final)
    strings.play(strc(OUTRO, ('G#3', 'G#5'), vel=70).slice(0, 16), outro)

    # choir: the breakdown's second half and the whole final chorus (the 'overexposed' layer)
    choir.play(chords(BREAK, voicing='spread', register=('F3', 'F5'), voices=4, vel=70, gate=0.96).slice(16), brk.bar(4))
    choir.loop(chords(CHORUS_E, voicing='spread', register=('G#3', 'G#5'), voices=4, vel=82, gate=0.96), final)

    # ------------------------------------------------------------------ E.piano (the heart)
    def comp(prog, rhythm='x__x__x_', reg=('A3', 'C#5'), vel=80):
        return chords(prog, voicing='smooth', register=reg, voices=4, vel=vel, rhythm=rhythm, step='1/8',
                      strum=0.012, gate=0.95)

    ep.loop(comp(VERSE, reg=('F#4', 'A5'), vel=70), intro.start, bars=4)     # then the hook alone over the pad
    ep.play(mD(HOOK_A.rsplit('|', 1)[0] + '| b6:1/2 5:1/2').clip(octave=5, vel=84), intro.bar(4))
    ep.play(comp(VERSE, rhythm='x_______', reg=('F#3', 'A4'), vel=64), intro.bar(4))
    ep.loop(comp(VERSE, vel=78), verse1)
    ep.play(mD(ANSWER).clip(octave=5, vel=76), verse1.bar(8), times=2)
    ep.play(comp(PRE, rhythm='x_x_x_x_', vel=82), pre)
    ep.loop(comp(CHORUS, reg=('C#4', 'E5'), vel=90), chorus1)
    ep.play(mD(VERSE_A + ' | ' + VERSE_B2).clip(octave=4, vel=98), verse2)       # the E.piano sings the verse
    ep.play(comp(VERSE, rhythm='x_______', reg=('F#3', 'A4'), vel=70), verse2, times=2)
    ep.play(mD(BREAK_M).clip(octave=4, vel=100), brk)
    ep.loop(comp(SOLO, rhythm='x_____x_', reg=('F#3', 'A4'), vel=74), solo)
    ep.play(comp(LIFT, rhythm='x_x_x_x_', vel=86), lift)
    ep.loop(comp(CHORUS_E, reg=('D#4', 'F#5'), vel=92), final)
    ep.play(comp(OUTRO_COMP, rhythm='x__x__x_', reg=('B3', 'D#5'), vel=72), outro)
    ep.play(chords(s.prog('Emaj9'), register=('D#4', 'F#5'), voices=4, vel=70, strum=0.06), outro.bar(7))  # rolled
    ep.play(mE(OUTRO_EP).clip(octave=5, vel=78), outro)

    # ------------------------------------------------------------------ lead (soft lead topline)
    lead.play(mD(' | '.join((VERSE_A, VERSE_B, VERSE_A2, VERSE_B2))).clip(octave=4, vel=90), verse1)
    lead.play(mD(PRE_M).clip(octave=5, vel=94), pre)
    lead.play(mD(HOOK).clip(octave=5, vel=100), chorus1)
    lead.play(mD(LIFT_M).clip(octave=5, vel=98), lift)
    lead.play(mE(HOOK).clip(octave=5, vel=96), final)          # the octave shine above the sax
    lead.play(mE(OUTRO_M).clip(octave=5, vel=84), outro)
    lead2.play(mE(HARM).clip(octave=4, vel=90), final.bar(8))  # the harmony, second half of the final

    # ------------------------------------------------------------------ alto sax (played, not triggered)
    def blow(line, at, seed, vib=16):
        return art.perform(sax, line, at, glide_leaps=7, glide_ms=90, humanize_ms=7, late_ms=10, seed=seed,
                           vib={'depth': vib, 'rate': 5.0, 'delay': 0.4, 'grow': 0.6})

    blow(mD(ANSWER + ' | ' + ANSWER2).clip(octave=4, vel=84), verse2, seed=3, vib=12)   # it introduces itself
    solo_line = blow(mD(SOLO_M).clip(octave=4, vel=96), solo, seed=5, vib=18)
    final_line = blow(mE(HOOK).clip(octave=4, vel=100), final, seed=7, vib=16)
    blow(mE(OUTRO_SAX).clip(octave=4, vel=78), outro, seed=9, vib=14)
    # scoops into the phrase entries (the sampler's pitch bend)
    bend = [(verse2.start, 0.0)]
    for n in (solo_line[0], solo_line[9], solo_line[20]):
        bend += jazz.scoop(solo.start + n.start, cents=-70, length=0.2)
    for i in (0, 16, 32):
        bend += jazz.scoop(final.start + final_line[i].start, cents=-60, length=0.18)
    sax.automate('instrument.pitchbend', bend)
    # delay throws on phrase ends
    sax.automate('send.echo', [(verse2.start, -16), (solo.bar(3), -16), (solo.bar(3, 2), -6, 'step'),
                               (solo.bar(4), -16, 'step'), (solo.bar(7), -16), (solo.bar(7, 2), -5, 'step'),
                               (lift.start, -16, 'step')])

    # ------------------------------------------------------------------ glass arp sparkle (sounds +1 oct)
    glass.loop(arp(VERSE, 'up', rate='1/8', register=('A3', 'A4'), vel=66, gate=0.5), intro.bar(2), bars=6)
    glass.loop(arp(VERSE, 'updown', rate='1/8', register=('A4', 'A5'), vel=62, gate=0.5), verse1.bar(8), bars=8)
    glass.play(arp(PRE, 'up', rate='1/16', octaves=2, register=('A3', 'A4'), vel=64), pre)
    glass.loop(arp(CHORUS, 'updown', rate='1/16', register=('A4', 'A5'), vel=64), chorus1)
    glass.loop(arp(VERSE, pattern=[0, 2, 1, 3, None, 2, 1, None], rate='1/8', register=('A4', 'A5'), vel=64),
               verse2)
    glass.play(arp(BREAK, 'up', rate='1/4', register=('A3', 'A4'), vel=58), brk)
    glass.loop(arp(SOLO, pattern=[0, None, 2, 1, None, 3, 2, None], rate='1/8', register=('A4', 'A5'), vel=56), solo)
    glass.play(arp(LIFT, 'up', rate='1/16', octaves=2, register=('A3', 'A4'), vel=66), lift)
    glass.loop(arp(CHORUS_E, 'updown', rate='1/16', register=('B4', 'B5'), vel=58), final)
    glass.play(arp(OUTRO, 'down', rate='1/8', register=('B3', 'B4'), vel=58).slice(0, 24), outro.start)

    # ------------------------------------------------------------------ the vocoder: 'summer ... overexposed'
    vox.play(chords(s.prog('Dmaj7 Bm7'), voicing='spread', register=('A2', 'E5'), voices=5, vel=100),
             brk.bar(2))
    vox.play(chords(s.prog('Gm6:2'), voicing='spread', register=('A2', 'E5'), voices=5, vel=100), brk.bar(6))
    vox.play(chords(s.prog('Emaj7 G#m7'), voicing='spread', register=('B2', 'F#5'), voices=5, vel=96),
             outro.bar(4))
    voice.play(words.clip({0: 'summer'}, length=8), brk.bar(2))
    voice.play(words.clip({0.5: 'overexposed'}, length=8), brk.bar(6))
    voice.play(words.clip({0.5: 'summer'}, length=8), outro.bar(4))

    # ------------------------------------------------------------------ the 1-beat drops before the choruses
    # clear() only removes notes that START in the gap: the tied bass roots and held chords rang straight through the
    # 'silence' (the mix stayed at -13 dB RMS). cut() also ends every note that sounds into it - a real drop, with
    # only the pad's release and the reverb tails breathing in the gap before the impact.
    def cut(track, at):
        a = s._at(at)
        track._notes = [n._replace(dur=a - n.start) if n.start < a - 1e-6 < n.start + n.dur else n
                        for n in track._notes]

    for t in (kit, bass, ep, glass, strings, pad, choir, lead, lead2):
        for gap in (pre, lift):
            t.clear(gap.beat(-1), gap.end)
            cut(t, gap.beat(-1))

    # ------------------------------------------------------------------ fx hits
    riser_t.note('A3', intro.bar(6), 8, vel=80)
    riser_t.note('A3', pre.start, 15, vel=100)
    riser_t.note('A3', brk.bar(6), 8, vel=76)
    riser_t.note('A3', lift.start, 15, vel=110)
    riser_t.automate('instrument.cutoff', riser(verse1, 8, 300, 6000), riser(pre.beat(-1), 15, 300, 9000),
                     riser(solo, 8, 300, 5000), riser(lift.beat(-1), 15, 300, 10000))
    riser_t.automate('instrument.hpf', riser(verse1, 8, 20, 800), riser(pre.beat(-1), 15, 20, 1500),
                     riser(solo, 8, 20, 800), riser(lift.beat(-1), 15, 20, 1500))
    down.note('A3', verse2, 8, vel=86).note('A3', brk, 8, vel=104).note('A3', outro, 8, vel=90)
    boom.note('D1', chorus1, 4, vel=100).note('E1', final, 4, vel=118)

    # ------------------------------------------------------------------ production moves
    pad.automate('instrument.cutoff', [
        (intro.start, 500), (intro.bar(6), 1000, 'exp'), (intro.end, 1600, 'exp'),
        (pre.start, 1800), (chorus1.start, 2800, 'exp'),
        (chorus1.end, 2600), (verse2.start, 2000, 'exp'),
        (brk.start, 900, 'exp'), (solo.start, 1400), (solo.end, 2200, 'exp'), (final.start, 2800, 'exp'),
        (outro.start, 2600), (outro.end, 450, 'exp')])
    lead.automate('instrument.cutoff', per_section({verse1: 2600, pre: 3000, chorus1: 3600, lift: 3200,
                                                    final: 3800, outro: 2800}))
    # the shimmer halo blooms where the drums leave
    for t, lo in ((pad, -18), (strings, -18)):
        t.automate('send.shimmer', per_section({intro: -11, verse1: lo, verse2: lo, brk: -7, solo: lo,
                                                outro: -8}, glide=4))
    pad.automate('send.hall', per_section({intro: -6, verse1: -4, brk: -2, solo: -4, outro: -2}, glide=4))
    # the E.piano's hall blooms where it plays alone (breakdown) and on the last chord
    ep.automate('send.hall', per_section({verse1: -14, brk: -8, solo: -14}, glide=2),
                [(outro.bar(6), -14), (outro.end, -7, 'smooth')])
    ep.send(shimmer, -60)     # the last chord leaves an octave halo that rings into the tail
    ep.automate('send.shimmer', [(outro.bar(6), -60), (outro.bar(7), -14, 'smooth'), (outro.end, -10, 'smooth')])
    # delay throws on the lead's phrase ends
    lead.automate('send.echo', [(verse1.start, -12), (pre.bar(3), -12), (pre.bar(3), -4, 'step'),
                                (chorus1.start, -12, 'step'), (chorus1.bar(15), -12), (chorus1.bar(15, 2), -5, 'step'),
                                (verse2.start, -12, 'step'), (outro.bar(3), -12), (outro.bar(3), -4, 'step')])

    # energy arc: fader rides per section on top of the arrangement (a 'gainDb' lane is dB on the track's gain_db)
    def ride(node, values, fade=0.0):
        base = 0.0

        pts = per_section({sec: base + v for sec, v in values.items()}, glide=1)
        if fade:        # the ending: a decrescendo through the last two bars into the held chord and the tail
            last = base + values.get(outro, 0.0)
            pts += [(outro.bar(6), last), (outro.end, last - fade, 'smooth')]
        node.automate('gainDb', pts)

    ride(kit, {intro: 0, verse1: -2, pre: 0, chorus1: 1.5, verse2: -0.5, brk: -1, solo: 0, lift: 1,
               final: 2.5, outro: -1})
    ride(bass, {verse1: -4, pre: -1.5, chorus1: 0, verse2: -2, brk: -3, solo: -1.5, lift: -0.5, final: 0.5,
                outro: -2}, fade=14)
    ride(pad, {intro: 2, verse1: -4, pre: -1.5, chorus1: -1, verse2: -2.5, brk: -1, solo: -2, lift: -1, final: 0.5,
               outro: 0}, fade=16)
    ride(strings, {verse1: -3, chorus1: 0, verse2: -4, solo: -1.5, lift: 0, final: 0, outro: 0})
    ride(lead, {verse1: -0.5, pre: 0.5, chorus1: 3, lift: 1.5, final: -2, outro: 0})
    ride(ep, {intro: 1.5, verse1: -1.5, pre: -1, chorus1: -1.5, verse2: 1, brk: 3.5, solo: -1.5, lift: 0, final: 0,
              outro: 0.5}, fade=4)
    ride(sax, {verse2: 0, final: 1.5, outro: 0}, fade=7)
    ride(glass, {intro: 0}, fade=6)

    # the ending: slow down into the last bar, the rolled Emaj9 held longer (tempo map)
    s.ritardando((outro.bar(5), outro.bar(7)), to=0.78, a_tempo=False)
    s.fermata(outro.bar(7), hold=4)
    return s
