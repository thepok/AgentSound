"""Until the Credits Roll - retrowave pop anthem (instrumental), 118 BPM, E minor -> F# minor.

Sub-style: Retrowave pop (The Midnight / Gunship), built on the reference-calibrated band preset
bands.retrowave (80s pop kit + Linn clap into the keyed gated reverb, octave bass, Juno pad, bright DX e-piano,
brass stabs, Fairlight choir, brass lead; 224XL hall + plate, dotted-8th echo, master/synthwave as tuned against
The Midnight "Sunset").

The last scene of an 80s movie. One phrase (E . D E G) carries the song: bells in the intro, the brass/saw lead
in the choruses, a tenor sax that takes the verse-2 melody, answers the hook in chorus 2 and plays the solo of the
breakdown, and a vocoder choir that speaks the title twice - once in the breakdown, once over the final chord.
The key change lands ON the final chorus downbeat (C# major -> D: the 80s modulation hit); the outro slows down
(tempo-map ritardando) into an F# MAJOR chord that rings out with the robot's last word.

Build: python -m agentsound build songs/skyline-heartbeat
Compare: python -m agentsound compare songs/skyline-heartbeat --section chorus2
         --ref "assets/refrences/The Midnight - Sunset (Official Audio) [URma_gu1aNE].opus"
"""
from agentsound import *
from agentsound import articulation as art
from agentsound import bands, speech

ANALYSIS = {'profile': 'synthwave'}                    # = bands.retrowave(...).analysis
METADATA = {'title': 'Until the Credits Roll', 'artist': 'AgentSound', 'album': 'Neon Archive',
            'genre': 'Synthwave', 'year': 2026,
            'comment': 'Retrowave pop anthem, 118 BPM, E minor -> F# minor. Tenor sax: MTG Solo Saxophones (CC-BY 4.0).'}
COVER = {'style': 'synthwave', 'palette': 'sunset', 'title': 'UNTIL THE CREDITS ROLL', 'subtitle': 'AgentSound',
         'seed': 118}

BPM = 118
UP = 2          # final chorus / outro: modulate up a whole step (E minor -> F# minor)
DRUMS_UP = 1.0     # the kit forward against the wall (the backbeat was buried: snare punch 8 vs 13 dB)
MUSIC_DOWN = 1.0


def build() -> Song:
    s = Song('Until the Credits Roll', tempo=BPM, key='E minor', seed=7, tail=7.0)
    key = s.key

    # ------------------------------------------------------------------ harmony
    P_intro = s.prog('C D G Em')                          # the chorus chords, foreshadowed
    P_verse = s.prog('Em Cmaj7 Am7 Bm7')                   # moody: minor v (Bm7)
    P_pre = s.prog('Am Em/B C D Am Em/B C B')             # bass climbs A-B-C-D; ends on MAJOR V (B)
    P_chorus = s.prog('C D G Em') * 3 + s.prog('C D Bsus4 B')   # V -> VI deceptive lift into it
    P_break = s.prog('Em9:2 Cmaj7:2 Dadd9:2 Bm7:2 Em9:2')  # half-speed harmony, new colours
    # the lift stays in E minor; its last bar pushes up to C# major = V of F# minor, so the key change
    # lands ON the final chorus downbeat (C# -> D)
    P_lift = s.prog('Am Em/B C D Am Em/B C C#')
    P_final = P_chorus.transpose(UP)
    P_outro = s.prog('D E A F#m D E F#:3')                 # F# minor ... ends on F# MAJOR (Picardy)

    # ------------------------------------------------------------------ form: 123 bars, ~4:10 + ring-out
    intro = s.section('intro', 8, prog=P_intro)
    verse1 = s.section('verse1', 16, prog=P_verse)
    pre1 = s.section('pre1', 8, prog=P_pre)
    chorus1 = s.section('chorus1', 16, prog=P_chorus)
    verse2 = s.section('verse2', 8, prog=P_verse)
    pre2 = s.section('pre2', 8, prog=P_pre)
    chorus2 = s.section('chorus2', 16, prog=P_chorus)
    breakdown = s.section('breakdown', 10, prog=P_break)
    lift = s.section('lift', 8, prog=P_lift)
    final = s.section('final', 16, prog=P_final)
    outro = s.section('outro', 9, prog=P_outro)

    # ------------------------------------------------------------------ melody (degrees of E minor, 8 = E5 at octave 4)
    H = {
        'a1': '8:1/4. 7:1/8 8:1/8 10:1/4 9:1/8',     # E5 . D E G F#>  (F# pushed into the D bar)
        'b': '_:1/2 r:1/2',                          # F# held; two beats of space -> brass / sax answer
        'c': 'r:1/8 7:1/8 8:1/8 9:1/8 10:1/4 5:1/4',  # 8th run D E F# G, drop to B4
        'd': '8:1/2 r:1/4 5:1/8 7:1/8',              # home + pickup
        'd3': '8:1/4 10:1/8 12:1/8 _:1/4 11:1/8 9:1/8',   # chorus 2: E G B~ A F# - the run keeps going
        'a2': '8:1/4. 7:1/8 8:1/8 10:1/4 11:1/8',    # E5 . D E G A>  (A pushed)
        'f': '_:1/4 9:1/8 11:1/8 12:1/2',            # A, F# A, B5 arrives early on beat 3 over D
        'p': '_:1/2. 11:1/8 10:1/8',                 # B5 held ~5 beats over G: the peak, then A G
        'd2': '9:1/4 8:1/4. r:1/8 5:1/8 7:1/8',      # F# E + pickup
        'g2': '_:1/2 11:1/4 9:1/4',                  # B5 held over Bsus4, A F#
        'gF': '15:1/2. 12:1/8 11:1/8',               # final chorus only: E6 (F#6) - the one time it appears
        'h': '8:1/2 #7:1/2',                         # E5 -> D#5 over B: suspension resolving
    }

    def mel(*bars):
        return s.motif(' '.join(H[b] for b in bars))

    phrase1 = mel('a1', 'b', 'c', 'd')
    phrase2 = mel('a2', 'f', 'p', 'd2')
    hook = mel('a1', 'b', 'c', 'd', 'a2', 'f', 'p', 'd2', 'a1', 'b', 'c', 'd', 'a2', 'f', 'g2', 'h')      # 16 bars
    hook2 = mel('a1', 'b', 'c', 'd', 'a2', 'f', 'p', 'd2', 'a1', 'b', 'c', 'd3', 'a2', 'f', 'g2', 'h')
    hook_fin = mel('a1', 'b', 'c', 'd', 'a2', 'f', 'p', 'd2', 'a1', 'b', 'c', 'd3', 'a2', 'f', 'gF', 'h')
    pickup = s.motif('5:1/8 #7:1/8')                                  # B4 D#5 in the 1-beat drop
    hook_c = hook.clip(octave=4, vel=100)
    hook_c2 = hook2.clip(octave=4, vel=102)
    hook_f = hook_fin.clip(octave=4, vel=106)
    harm_c = hook2.clip(octave=4, vel=86).transpose_scale(-2, key).fit(P_chorus, key)
    harm_f = hook_fin.clip(octave=4, vel=88).transpose_scale(-2, key).fit(P_chorus, key)

    V = {
        1: 'r:1/4. 5:1/8 8:1/4 7:1/8 5:1/8',
        2: '6:1/4. 5:1/8 3:1/2',
        3: 'r:1/4. 4:1/8 6:1/4 8:1/8 7:1/8',
        4: '7:1/4 5:1/2.',
        7: 'r:1/4. 4:1/8 6:1/4 10:1/8 9:1/8',
        8: '9:1/2. r:1/4',
        9: 'r:1/4. 8:1/8 10:1/4 9:1/8 8:1/8',     # the answer, a third higher: E G F# E
        10: '10:1/4. 8:1/8 6:1/2',                # G E C over Cmaj7
        11: 'r:1/4. 6:1/8 8:1/4 11:1/8 10:1/8',   # C E A G over Am7
        12: '9:1/2. r:1/4',
        15: 'r:1/4. 4:1/8 6:1/4 8:1/8 10:1/8',
        16: H['c'],                               # = hook bar 'c': foreshadows the chorus run
    }
    verse_a = s.motif(' '.join(V[i] for i in (1, 2, 3, 4, 1, 2, 7, 8)))
    verse_b = s.motif(' '.join(V[i] for i in (9, 10, 11, 12, 1, 2, 15, 16)))
    pre_m = s.motif('8:1/4 8:1/8 7:1/8 6:1/4 4:1/4 | 5:1/2. r:1/4 | 8:1/4 8:1/8 7:1/8 8:1/4 10:1/4 | 9:1/2. r:1/4 | '
                    '8:1/4 8:1/8 7:1/8 6:1/4 4:1/4 | 5:1/4 7:1/4 8:1/4 10:1/4 | 10:1/4 10:1/8 9:1/8 8:1/4 10:1/4 | '
                    '9:1/2 #7:1/4 r:1/4')
    pre_harm = pre_m.clip(octave=4, vel=82).transpose_scale(-2, key).fit(P_pre, key)
    outro_m = mel('a2', 'f') + s.motif('#10:1/1 _:1/1 _:1/1')   # ... climbs, lands on A#5: the major third of F#

    # the sax solo of the breakdown (tenor, octave 3: 8 = E4, 15 = E5): the hook cell laid back, then a climb
    # through the new chords to the E5 peak over Em9 and a run down into the lift
    solo_m = s.motif('r:1/4 8:1/4. 7:1/8 8:1/8 10:1/8 | _:1/2 12:1/8 11:1/8 10:1/8 12:1/8 | '
                     '11:1/2. 9:1/8 11:1/8 | 12:1/2 11:1/4 9:1/8 7:1/8 | '
                     '8:1/4. 9:1/8 10:1/4 12:1/4 | 14:1/2. 12:1/8 14:1/8 | '
                     '15:1/2. 14:1/8 12:1/8 | 14:1/8 12:1/8 11:1/8 10:1/8 9:1/4 8:1/4')
    sax_lick = s.motif('12:1/8 14:1/8 12:1/8 11:1/8')                # 2 beats: answers the held F# of the hook
    sax_outro = s.motif('r:1/4 8:1/4. 7:1/8 8:1/8 10:1/8 | _:1/2 12:1/8 11:1/8 12:1/4 | '
                        '14:1/2. 12:1/8 11:1/8 | 12:1/2. r:1/4')

    # ------------------------------------------------------------------ the band (preset) + extra players
    b = bands.retrowave(s)
    kit, bass, pad, keys, brass, choir, lead = (b.drums, b.bass, b.pad, b.keys, b.brass, b.choir, b.lead)
    hall, plate, echo = b.hall, b.plate, b.echo
    kit.groove('laidback').humanize(2, 4)
    shimmer = s.bus('shimmer', 'bus/shimmer')
    music = s.bus('music')                                 # plain group buses: only for the energy-arc faders
    dbus = s.bus('drumbus')
    for t in (kit,):
        t.to(dbus)
    for t in (bass, pad, keys, brass, choir, lead):
        t.to(music)
    pad.send(shimmer, -20)

    # mix moves on top of the preset (from the loudness-matched compare against "Sunset"): the kick hits stick
    # out more (slower kit-compressor attack, deeper bass/pad pump, a little less limiting), more 60-90 Hz weight
    kit.fx['compressor'].set(attack=25, ratio=2.5)
    kit.fx['eq'].set({'hp.freq': 25, 'low.gain': 1.0, 'peak3.freq': 80, 'peak3.gain': 2.5, 'peak3.q': 1.2,
                      'high.gain': 0.0, 'lp.freq': 13000, 'peak2.freq': 3500, 'peak2.gain': -1.5, 'peak2.q': 0.9})
    kit.fx['saturator'].set(drive=2.5)                        # the tape clip rounded the kick's attack off
    kit.gain_db += 2.0
    kit.instrument.lazy['gains'].update(snare=2.5, clap=0.0)   # the backbeat forward (snare punch 8 vs 13 dB)
    bass.fx['ducker'].set(depth=14, hold=60, release=160, curve=0.5)
    bass.gain_db -= 2.5                                        # was the loudest part (-17 dB RMS), over the kit
    bass.fx[2].set({'hp.freq': 27})                           # the preset's bass high-pass: let 27-32 Hz through
    b.gated.fx['gatedreverb'].set(width=0.9)                  # 1.2 read correlation -0.17 (the burst cancels in mono)
    lead.fx['eq'].set({'peak3.gain': 0.0})                    # the preset's +2 dB presence lift read 'harsh' here
    keys.fx[0].set({'peak3.gain': -2.0})                      # the e-piano steps out of the snare's presence band
    pad.fx['ducker'].set(depth=7)
    bass.add_fx(fx.eq({'peak2.freq': 80, 'peak2.gain': 3.5, 'peak2.q': 1.3}))    # weight at 60-90 Hz, not at 45
    s.master.fx['limiter'].set(gain=5.2)
    s.master.fx['eq'].set({'high.gain': 3.0})                  # the preset's +5.5 dB shelf read +3 dB air here

    perc = s.track('perc', 'sampled/forzee_kit', output=dbus, gain_db=-5, sends={plate: -18},   # crash, tambourine
                   fx=[fx.eq({'high.freq': 9000, 'high.gain': -6})])
    perc.humanize(3, 5)
    saw = s.track('saw', patches.get('synthwave/supersaw_lead').but_fx('eq', **{'peak3.freq': 3500, 'peak3.gain': -3}),
                  output=music, gain_db=-8, sends={hall: -12, echo: -14})
    soft = s.track('soft', 'synthwave/soft_lead', output=music, gain_db=0, sends={hall: -10, echo: -12}).humanize(3, 5)
    sax = s.track('sax', 'sampled/tenor_sax', output=music, gain_db=1.5, sends={hall: -9, plate: -13, echo: -15})
    harm = s.track('harm', 'synthwave/brass_lead', output=music, gain_db=-9, pan=0.2)
    brass2 = s.track('brass2', 'synthwave/dx_brass', output=music, gain_db=-8, pan=-0.3)
    strings = s.track('strings', 'synthwave/jupiter_strings', output=music, gain_db=-6)
    violin = s.track('violin', patches.get('synthwave/jupiter_strings').but(cutoff=5200), output=music,
                     gain_db=-7, pan=-0.2, sends={hall: -6})
    arp_t = s.track('arp', 'synthwave/arp_pluck', output=music, gain_db=-8, pan=0.3, sends={echo: -8})
    arp2 = s.track('arp2', 'synthwave/arp_pluck', output=music, gain_db=-4, pan=-0.4, sends={echo: -10})
    glass = s.track('glass', 'synthwave/arp_glass', output=music, gain_db=-8, pan=0.4)
    bells = s.track('bells', 'synthwave/dx_bells', output=music, gain_db=-6, pan=-0.3)
    sub = s.track('sub', 'synthwave/sub_bass', output=music, gain_db=-8)
    riser_t = s.track('riser', 'synthwave/noise_riser', gain_db=-2, fx=[fx.eq({'high.freq': 9000, 'high.gain': -3})])
    impact = s.track('impact', 'synthwave/impact', gain_db=1, fx=[fx.eq({'high.freq': 8000, 'high.gain': -5})])
    down = s.track('down', 'synthwave/downlifter', gain_db=-7)
    # the robot: Windows TTS (cached in samples/speech/) keys a vocoder choir that sings the chords
    vox = speech.voice(s, ['until the credits roll'], voice='zira', rate=-3)
    robot = s.track('robot', 'synthwave/vocoder_choir', output=music, gain_db=0, sends={hall: -7, shimmer: -12})

    # ------------------------------------------------------------------ drums
    K4 = 'X...X...X...X...'
    KH = 'X.......X.x.....'                               # verse: 1, 3 and the push
    H8 = 'o.X.o.X.o.X.o.X.'
    H16 = 'xoXoxoXoxoXoxoXo'
    SN = '....X.......X...'
    kit_v1b = drums({'kick': KH + K4, 'hat': H8 + 'o.X.o.X.o.X.o...', 'ohh': '.' * 16 + '..............x.',
                     'snare': SN + '....X.....o.X..o'})
    kit_v2 = drums({'kick': K4 + 'X...X...X...X..x', 'hat': 'x.Xox.Xox.Xox.Xo' * 2,
                    'ohh': '.' * 16 + '..............x.', 'snare': SN + '....X.....o.X..o'})
    kit_ch = drums({'kick': K4 * 2, 'hat': H16 + 'xoXoxoXoxoXoxo..', 'ohh': '.' * 16 + '..............x.',
                    'snare': SN * 2, 'clap': SN * 2})
    kit_fin = drums({'kick': K4 * 2, 'hat': H16 + 'xoXoxoXoxoXoxo..', 'ohh': '..x...x...x...x.' + '..............x.',
                     'snare': SN + '....X.......X.oo', 'clap': SN * 2})
    tamb_a = drums({'tamb': '....x.......x...'})
    tamb_b = drums({'tamb': 'o.x.o.x.o.x.o.x.'})
    SC = ('snare', 'clap')                              # a snare / clap fill: the kick and hats keep going

    kit.plan({
        # intro: hats creep in over the last 4 bars, a tom fill into the verse
        intro: [(4, drums({'hat': '..o...o...o...o.'})), (7, drums({'hat': '..o...o...o.....', 'tom_hi': '............x...',
                                                                   'tom_mid': '.............x..', 'tom_lo': '..............xx'}))],
        verse1: [drums({'kick': KH, 'hat': H8, 'snare': SN}), (8, kit_v1b)],   # half-time kick, then four on the floor
        # pre 1: 8th hats -> 16ths, snare on every beat, build roll, 1-beat drop
        pre1: [drums({'kick': K4, 'hat': H8, 'snare': SN}), (4, drums({'kick': K4, 'hat': H16, 'snare': 'x...X...x...X...',
                                                                        'clap': SN})),
               (6, drums({'kick': K4, 'hat': 'xoXoxoXoxoXo....'})), (7, drums({'kick': K4}))],
        chorus1: kit_ch, verse2: kit_v2,                   # verse 2: busier hats, kick pickup, ghost snares
        pre2: [kit_v2, (5, drums({'kick': K4, 'hat': H16, 'snare': 'X.x.X.x.X.x.X.x.', 'clap': SN})),
               (6, drums({'kick': K4, 'hat': 'xoXoxoXo........', 'snare': 'x.x.X.x.xxxxXXXX'})),
               (7, drums({'kick': 'X...X...X.......'}))],  # pre 2: toms instead of the snare roll
        chorus2: kit_ch,
        breakdown: (6, drums({'kick': 'x.........x.....', 'hat': '..x...x...x...x.'})),   # no drums for 6 bars
        # lift: half-time -> four on the floor -> roll + toms (no drop: the key change arrives on a fill)
        lift: [drums({'kick': 'x.........x.....', 'hat': 'x.x.x.x.x.x.x.x.', 'snare': '........X.......'}),
               (4, drums({'kick': K4, 'hat': H16, 'snare': SN, 'clap': SN})), (7, drums({'kick': K4}))],
        final: kit_fin,
        # outro: groove for 4 bars, a build through the ritardando, one last hit on the F# major chord
        outro: [drums({'kick': K4, 'hat': H8, 'snare': SN}), (4, drums({'kick': K4, 'hat': H16, 'snare': SN, 'clap': SN})),
                (5, drums({'kick': K4}), 1)]},
        # tom fills over the kick (hats, snare and clap make room) only into the phrase turns
        fills={verse1.bar(15): (drums({'snare': '....X.......oxxX'}), SC),
               pre1.bar(6): (snare_roll(7, build=True, vel=(40, 110)), SC),
               chorus1.bar(7): (drums({'snare': '....X.......xxxx', 'clap': SN}), SC),
               verse2.bar(7): (drums({'snare': '....X.......xxXX'}), SC), chorus2.bar(7, 3): tom_fill(1),
               lift.bar(6): (drums({'snare': 'X.x.X.x.X.xxXxxx', 'clap': SN}), SC),
               lift.bar(7): (snare_roll(2, vel=(60, 112)), SC), final.bar(7, 2): tom_fill(2, vel=(96, 126)),
               final.bar(15, 2): tom_fill(2, vel=(96, 126)), outro.bar(5): (snare_roll(2, build=True, vel=(60, 112)), SC)},
        keep=('kick',))
    kit.play(tom_fill(2.5, vel=(90, 124)), pre2.bar(7))
    kit.play(drums({'snare': '............x...'}), breakdown.bar(9))
    kit.play(tom_fill(2, vel=(96, 126)), lift.bar(7, 2))
    kit.play(tom_fill(1, vel=(100, 126)), outro.bar(5, 3))
    kit.note('kick', outro.bar(6), 1, 124)
    # the tambourine from chorus 1's second half; crashes on the section downbeats (a real cymbal: the pop kit has none)
    perc.plan({chorus1: (8, tamb_a), pre2: (0, tamb_a, 6), chorus2: tamb_b, lift: (4, tamb_a), final: tamb_b,
               outro: (0, tamb_a, 4)}, crash=118,
              crashes=[verse1, chorus1, chorus1.bar(8), verse2, chorus2, chorus2.bar(8), breakdown, lift.bar(4), final,
                       final.bar(8), outro, outro.bar(6)])

    # ------------------------------------------------------------------ bass
    bass.loop(s.prog('Em').bass('octave', rate='1/8', gate=0.85), verse1, bars=8)                   # tonic pedal
    bass.bassline('octave', verse1, pre1, chorus1, pre2, lift, outro, rate='1/8', gate=0.85,       # released
                  bars={verse1: 8, pre1: (0, 6), pre2: (0, 6), lift: (0, 6), outro: (0, 6)})
    bass.bassline('pulse', pre1, pre2, lift, rate='1/16', gate=0.8, bars={pre1: (6, 7), pre2: (6, 7.75), lift: 6})
    bass.bassline('pulse', pre1, rate='1/16', gate=0.8, bars=(7, 7.75))   # drive into the drop; lift: C -> C# push
    bass.bassline('octave', verse2, chorus2, pattern='R_roR_roR_roR_ro', rate='1/16', gate=0.9)          # gallop
    bass.bassline('octave', final, rate='1/16', gate=0.85)                                               # top gear
    sub.bassline('root', breakdown, low='E1')
    sub.play(s.prog('F#:3').bass('root', low='E1'), outro.bar(6))

    # ------------------------------------------------------------------ pad, strings, choir
    pad.chords(s.sections, voicing='spread', register=('C3', 'C5'), voices=4, vel=80)
    big = (chorus1, chorus2, final, breakdown)
    strings.chords(intro, pre1, pre2, chorus1, chorus2, final, breakdown, lift, outro, voices=3,
                   register={'*': (62, 79), **dict.fromkeys(big, (64, 81))}, bars={intro: 4, pre1: 4, chorus1: 8},
                   vel={'*': 76, chorus1: 80, chorus2: 80, final: 80, breakdown: 70, outro: 80},
                   prog={final: P_chorus}, transpose={final: UP})
    # the descant: above the hook, moving against it
    desc = ['E6', 'D6', 'D6', 'B5', 'G6', 'F#6', 'D6', 'E6', 'E6', 'F#6', 'G6', 'E6', 'G6', 'F#6', 'F#6', 'D#6']
    descant = Clip([(i * 4, 4, p, 84) for i, p in enumerate(desc)], length=64)
    desc[14] = 'E6'                                          # final chorus: doubles the lead's one-off peak
    descant_f = Clip([(i * 4, 4, p, 90) for i, p in enumerate(desc)], length=64)
    violin.play(descant.slice(32, 64), chorus2.bar(8))
    violin.play(descant_f, final, transpose=UP)
    choir.chords(chorus2, final, outro, voicing='spread', register=('C3', 'C5'), voices=4, vel=84,
                 bars={chorus2: 8, outro: 3})

    # ------------------------------------------------------------------ keys / arps
    ep = dict(step='1/16', register=(57, 74), voices=4, vel=92)
    keys.chords(verse1, pre1, verse2, **ep, bars={verse1: (0, 8)}, crescendo={pre1: (0.45, 0.9)},
                rhythm={verse1: 'x.....x.....x...', pre1: 'x.x.x.x.x.x.x.x.', verse2: '..x..x..x...x.x.'})
    keys.chords(verse1, **ep, rhythm='x..x..x...x..x..', bars=8)
    # the e-piano answers the verse melody in its rests (the hook cell's shape)
    for bb, rep in ((3, 'r:2 12:1/4 11:1/8 12:1/8'), (7, 'r:2 11:1/4 9:1/8 11:1/8'),
                    (11, 'r:2 12:1/4 11:1/8 12:1/8')):
        keys.play(s.motif(rep).clip(octave=4, vel=100), verse1.bar(bb))
    keys.chords(chorus2, final, rhythm='x..x..x.', step='1/8', register={chorus2: (60, 76), final: (62, 78)},
                vel={chorus2: 84, final: 86})
    keys.arp('updown', breakdown, rate='1/8', register=(60, 79), gate=0.9, vel=80)

    two = (pre2, chorus2, lift, final)                    # the arp's two-octave sections
    arp_t.arp({'*': 'up', verse2: 'updown', chorus2: 'updown', final: 'updown'}, intro, verse2, pre2, chorus1, chorus2,
              lift, final, outro, rate='1/16', octaves=dict.fromkeys(two, 2), gate={chorus1: 0.5},
              register={'*': (57, 76), pre2: (57, 72), chorus2: (57, 72), lift: (59, 74), final: (59, 74), outro: (59, 78)},
              vel={intro: 84, verse2: 86, pre2: 86, chorus1: 88, chorus2: 90, lift: 88, final: 92, outro: 84},
              bars={intro: 4, outro: (0, 6)})
    arp2.arp('down', chorus2, final, rate='1/8', gate=0.5, register={chorus2: (67, 84), final: (69, 86)},
             vel={chorus2: 84, final: 88}, bars={chorus2: 8})
    glass.arp({'*': 'up', verse1: 'down'}, intro, verse1, breakdown, outro, rate='1/8',
              register={'*': (64, 79), verse1: (64, 76)}, vel={intro: 80, verse1: 76, breakdown: 78, outro: 80},
              bars={verse1: 8, outro: (0, 6)})

    # ------------------------------------------------------------------ brass: stabs answer the hook's gaps
    def stabs(prog, rhythm, vel=106):
        return prog.block(rhythm=rhythm, step='1/16', register=(57, 74), voices=4, vel=vel)

    def one(ch, rhythm, vel=106):
        return stabs(s.prog(ch), rhythm, vel) if rhythm else Clip.rest(4)

    ONE, GAP, HELD, ANS = 'X_..............', '........X_..x_..', '....X_......x_..', 'X_......x.X_....'
    FOUR = 'X_..X_..X_..X_..'

    def brass_part(gap=True, g_hit=''):
        ph1 = one('C', ONE) + one('D', GAP if gap else '') + one('G', g_hit) + one('Em', ANS)
        ph2 = one('C', ONE) + one('D', '') + one('G', HELD) + one('Em', ANS)
        ph4 = one('C', ONE) + one('D', '') + one('Bsus4', ONE) + one('B', FOUR)
        return ph1 + ph2 + ph1 + ph4

    br1 = brass_part()
    br2 = brass_part(gap=False, g_hit='X_..............')    # chorus 2 / final: the sax takes the D-bar gap
    br_pre_a = stabs(s.prog('Am Em/B C'), ONE, vel=88)
    br_pre_b = stabs(s.prog('B'), 'x_..x_..X_......', vel=96)
    brass.play(br1, chorus1)
    brass.play(br2, chorus2).play(br2, final, transpose=UP)
    brass2.play(br2, chorus2).play(br2, final, transpose=UP)
    for t in (brass, brass2):
        t.play(br_pre_a + br_pre_b, pre2.bar(4))
        t.play(br_pre_a, lift.bar(4)).play(br_pre_b, lift.bar(7), transpose=UP)   # B -> C# stab
    brass.play(br_pre_a + br_pre_b, pre1.bar(4))
    brass.play(stabs(s.prog('Em r Am7 r'), 'X_....x_........', vel=94) * 2, verse2)
    brass.play(stabs(s.prog('D E'), ONE) + s.prog('F#:3').block(register=(54, 73), voices=4, vel=110), outro.bar(4))
    brass2.play(s.prog('F#:3').block(register=(54, 73), voices=4, vel=108), outro.bar(6))
    for pch in ('F#5', 'A#5', 'C#6'):                                      # a last chime on the major chord
        bells.note(pch, outro.bar(6), 8, 84)

    # ------------------------------------------------------------------ leads
    bells.play(phrase1.clip(octave=4, vel=92) + phrase2.clip(octave=4, vel=96), intro)
    soft.play(verse_a.clip(octave=4, vel=96) + verse_b.clip(octave=4, vel=98), verse1)
    soft.play(pre_m.clip(octave=4, vel=98), pre1)
    soft.play(pre_m.clip(octave=4, vel=100), pre2)
    harm.play(pre_harm, pre2)
    for sec, tr, line in ((chorus1, 0, hook_c), (chorus2, 0, hook_c2), (final, UP, hook_f)):
        lead.play(pickup.clip(octave=4, vel=96), sec.start - 1, transpose=tr)
        lead.play(line, sec, transpose=tr)
    saw.play(hook_c.slice(32, 64), chorus1.bar(8))                        # chorus 1 holds the saw back to its half
    saw.play(hook_c2, chorus2).play(hook_f, final, transpose=UP)
    harm.play(harm_c, chorus2).play(harm_f, final, transpose=UP)
    soft.play(hook_f.slice(0, 56), final, transpose=UP + 12)              # octave-UP double (sparkle), not bar 15-16
    # lift: the pre-chorus melody on the lead in E minor; only its last bar is already in the new key
    lift_m = pre_m.clip(octave=4, vel=96)
    lead.play(lift_m.slice(0, 28), lift).play(lift_m.slice(28, 32), lift.bar(7), transpose=UP)
    harm.play(pre_harm.slice(16, 28), lift.bar(4)).play(pre_harm.slice(28, 32), lift.bar(7), transpose=UP)
    lead.play(outro_m.clip(octave=4, vel=100), outro.bar(4), transpose=UP)

    # the sax: verse 2 melody (an octave under the verse-1 lead), answers in chorus 2, the breakdown solo,
    # the outro phrase - played, not triggered: legato, glides into leaps, swells and delayed vibrato
    art.perform(sax, verse_a.clip(octave=3, vel=96), verse2, preset='sax')
    for bar in (1, 9):
        art.perform(sax, sax_lick.clip(octave=3, vel=114), chorus2.bar(bar, 2), preset='sax')   # a shout, not an aside
    art.perform(sax, solo_m.clip(octave=3, vel=104), breakdown.bar(2), preset='sax')
    art.perform(sax, sax_outro.clip(octave=3, vel=100), outro, preset='sax', seed=3)
    sax.clear(outro.bar(4), outro.end)

    # the robot says the title: in the breakdown (over Em9, before the sax), and over the final F# major chord
    vox.robot(robot, say={breakdown.start + 0.5: 'until the credits roll', outro.bar(6, 1): 'until the credits roll'},
              chords={breakdown: ('E3 B3 D4 G4 F#4', 7.5, 84), outro.bar(6): ('F#3 C#4 F#4 A#4', 12, 86)})
    ln = vox.beats('until the credits roll', BPM)
    robot.automate('fx.vocoder.hold', [(breakdown.start, 0), (breakdown.start + 0.5 + ln - 0.35, 1, 'step'),
                                       (breakdown.start + 7.5, 0, 'step'),
                                       (outro.bar(6, 1) + ln - 0.35, 1, 'step')])

    # ------------------------------------------------------------------ transitions / fx
    gain = []
    for sec in (pre1, pre2, lift):
        drop_at = sec.end - 1 if sec is not lift else sec.end
        riser_t.rise(drop_at, drop_at - sec.start, pitch='E3')
        gain += [(sec, -9), (drop_at, -7, 'linear'), (drop_at + 0.125, -58, 'linear')]      # dB on its gain_db
    riser_t.levels(gain)
    impact.note('E1', chorus1.start, 4, 120).note('E1', chorus2.start, 4, 120)
    impact.note('F#1', final.start, 4, 124).note('F#1', outro.bar(6), 12, 124)
    down.note('E3', verse2.start, 6, 100).note('E3', breakdown.start, 8, 110)

    # the 1-beat drop before chorus 1 and 2: only the lead pickup sings
    s.breath(before=[chorus1, chorus2], tracks=[kit, perc, bass, sub, pad, strings, violin, keys, arp_t, arp2, glass,
                                                 brass, brass2, soft, harm, saw, choir, bells, sax])
    for t in (kit, arp_t, keys, glass):                      # the final F# major chord rings alone after the last hit
        t.clear(outro.bar(6, 1), outro.end, cut=True)

    # ------------------------------------------------------------------ the ending: slow into the last chord
    s.ritardando((outro.bar(4), outro.bar(6)), to=0.8, a_tempo=False)

    # ------------------------------------------------------------------ lead expression
    vib = [(0, 0.0)]
    for n in lead.notes:
        if n.dur >= 1.5 and n.start >= chorus1.start - 1:
            a, e = n.start + 0.6, n.start + n.dur
            if a > vib[-1][0] + 0.01:
                vib += [(a, 0.0, 'step'), (min(a + 0.8, e - 0.05), 0.2, 'linear'), (e, 0.2, 'step'),
                        (e + 0.05, 0.0, 'linear')]
    lead.modulate('instrument.pitchbend', lfo('sine', rate='5.5hz', depth=vib, base=0))
    art.throws(lead, spans=[((sec, at), ln_) for sec in (chorus1, chorus2, final)
                            for at, ln_ in ((12, 2.5), (29, 2), (44, 2.5), (62, 2))], base=-12, throw=-3)

    # ------------------------------------------------------------------ production moves
    s.sidechain(strings, arp_t, arp2, sub, key=kit, pitches='kick', depth=5, release=190)
    # the rest of the synth wall breathes with the kick too (the melodies - lead, soft, sax, robot - stay steady):
    # each kick opens a hole in the dense chorus instead of landing on a flat wall
    s.sidechain(brass, brass2, keys, saw, harm, violin, glass, key=kit, pitches='kick', depth=3, hold=20,
                release=150, curve=0.3)
    pad.automate('instrument.cutoff', exp_ramp(intro.start, intro.end, 600, 3000),
                 exp_ramp(breakdown.start, breakdown.bar(2), 3000, 1500),
                 exp_ramp(lift.start, final.start, 1500, 3000),
                 exp_ramp(outro.bar(6), outro.end, 3000, 700))
    pad.automate('send.shimmer', [(intro.start, -8), (verse1.start, -20, 'smooth'), (breakdown.start, -7, 'step'),
                                  (lift.start, -20, 'smooth'), (outro.bar(4), -8, 'smooth')])
    arp_t.automate('instrument.cutoff', exp_ramp(intro.bar(4), intro.end, 300, 600),
                   hold(intro.end, pre2.start, 650), exp_ramp(pre2.start, chorus2.start - 1, 650, 1500),
                   hold(chorus2.start, lift.start, 800), exp_ramp(lift.start, final.start - 0.5, 800, 1600),
                   hold(final.start, outro.end, 900))

    # energy arc (gainDb lanes of marks: dB on each node's gain_db; without a curve a jump): the band sits back in
    # the verses, the builds rise, each chorus steps forward
    dbus.levels([(intro, -4), (verse1, -5), (verse1.bar(8), -4), (pre1, -3.5), (chorus1.start - 1, -2.5, 'linear'),
                 (chorus1, -0.5), (verse2, -4.5), (pre2, -3), (chorus2.start - 1, -2, 'linear'), (chorus2, 0),
                 (breakdown, -6), (lift, -5), (lift.bar(4), -3, 'linear'), (final.start - 0.5, -1, 'linear'),
                 (final, 0.5), (outro, -1)], base=DRUMS_UP)
    music.levels([(intro, -5), (intro.bar(3), -2.5, 'smooth'), (verse1, -5.5), (verse1.bar(8), -4.5), (pre1, -4),
                  (chorus1.start - 1, -3, 'linear'), (chorus1, -0.5), (verse2, -5), (pre2, -3.5),
                  (chorus2.start - 1, -2.5, 'linear'), (chorus2, 0), (breakdown, -7), (breakdown.bar(6), -5, 'smooth'),
                  (lift, -5.5), (lift.bar(4), -3.5, 'linear'), (final.start - 0.5, -1, 'linear'), (final, 0.5),
                  (outro, -1), (outro.bar(6), 0.5), (outro.bar(7), -1, 'smooth'), (outro.end, -14, 'smooth')],
                 base=-MUSIC_DOWN)                                                   # ... and the credits fade
    lead.levels([(pre1, 0), (final, 1.0), (outro, 0)])
    soft.levels([(verse1, 0), (final, -10), (outro, 0)])                # the octave-up double sits under the hook
    return s
