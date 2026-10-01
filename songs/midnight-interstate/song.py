"""Last Exit Before Dawn - outrun / nightdrive (recipes/synthwave.md sub-style 'Outrun / nightdrive').

112 BPM, F# minor; the final chorus lifts a whole step to G# minor. Built on the outrun band preset
(bands.outrun: LinnDrum + TR-909 kick with Simmons toms and the keyed gated snare, octave bass with sub, warm pad,
DX e-piano, pluck arp, supersaw hook, Lexicon 224XL hall + plate, dotted-8th echo, master/synthwave) plus the
song's own layers: a pulse double under the hook, a keytar verse lead, Jupiter strings, the Fairlight CMI choir, glass bells, a sampled
tenor sax (the realism engine: legato, live dynamics, vibrato, scoops) and a vocoder robot (Windows voice
'Stefan' through synthwave/vocoder_choir) that says the title.

Harmony: the chorus starts on VI (D), so the pre-chorus' harmonic-minor V (C#) resolves deceptively into it; the
bridge ends on D#sus4 -> D# (V of G# minor) and the final chorus lands deceptively again, on E.

Hook (supersaw, doubled an octave below by the pulse lead): the head  C#-F#-.-A-C#~  (a leap of a fourth, a rest,
then the minor triad climbing to a held C#6, the major 7th of D). It is foreshadowed by the bells in the intro and
in the gap of verse 1, sequenced up the chords in the pre-chorus, displaced by an 8th in the second phrase, lifted
a third for the climax (F#6), displaced by a beat and sequenced again in the sax solo, answered by sax licks in the
final chorus and sung one last time by the sax over the ritardando of the outro. The robot says "last exit" /
"before dawn" in the intro, the whole line at the start of the breakdown, and "before dawn" on the last chord,
whose vowel it freezes while the tempo slows and the chord rings out.

Build: python -m agentsound build songs/midnight-interstate
Compare: python -m agentsound compare songs/midnight-interstate --section chorus2
         --ref "D:/Repos/AgentSound/assets/refrences/Kavinsky - Nightcall (Official Audio - HD) [46qo_V1zcOM].opus"
"""
from agentsound import *
from agentsound import bands, speech
from agentsound import articulation as art

ANALYSIS = {'profile': 'synthwave'}              # = bands.outrun(...).analysis

METADATA = {'title': 'Last Exit Before Dawn', 'artist': 'AgentSound', 'album': 'Neon Archive',
            'genre': 'Synthwave', 'year': 2026, 'track': 1,
            'comment': 'Outrun / nightdrive, 112 BPM, F# minor -> G# minor'}
COVER = {'style': 'outrun', 'title': 'LAST EXIT BEFORE DAWN', 'subtitle': 'AgentSound', 'seed': 1984}

UP = 2                           # final-chorus key change: F# minor -> G# minor


def build() -> Song:
    s = Song('Last Exit Before Dawn', tempo=112, key='F# minor', seed=1984, tail=7)

    # ------------------------------------------------------------------ form (112 bars, ~4:05 + the ending)
    intro = s.section('intro', 8)
    verse1 = s.section('verse1', 16)
    build1 = s.section('build1', 8)
    chorus1 = s.section('chorus1', 16)
    verse2 = s.section('verse2', 8)
    build2 = s.section('build2', 4)
    chorus2 = s.section('chorus2', 16)
    bridge = s.section('bridge', 12)
    final = s.section('final', 16)
    outro = s.section('outro', 8)

    # ------------------------------------------------------------------ harmony
    P_intro = s.prog('i VImaj7 III VII') * 2                  # F#m Dmaj7 A E
    P_verse = s.prog('i VII VImaj7 VII')                      # F#m E Dmaj7 E (over an F# pedal first)
    P_build1 = s.prog('iv:2 VI:2 VII:2 Vsus4:1 V:1')          # Bm D E C#sus4 C#  (harmonic-minor V)
    P_build2 = s.prog('iv VI VII V')
    P_chorus = (s.prog('VImaj7 VII i III') + s.prog('VImaj7 VII i VII') + s.prog('VImaj7 VII i III')
                + s.prog('VImaj7 VII i i'))                   # Dmaj7 E F#m A | .. E | .. A | .. F#m F#m
    P_bridge = s.prog('VImaj7:2 VII:2 i IV VI VII i IV') + s.prog('VI Vsus4:0.5 V:0.5').transpose(UP)
    #          Dmaj7 E F#m B(dorian) D E F#m B  | E D#sus4 D#  = VI V of G# minor
    P_final = P_chorus.transpose(UP)
    P_outro = (s.prog('VImaj7 VII i III') + s.prog('VImaj7 VII Vsus4:0.5 V:0.5 iadd9')).transpose(UP)
    #          E F# G#m B | E F# D#sus4 D# G#m(add9): the only perfect cadence of the song, under the ritardando

    # ------------------------------------------------------------------ melodies (scale degrees of F# minor)
    H = {
        'a1': '5:1/8 8:1/8 r:1/8 10:1/8 12:1/4.! 10:1/8',         # D    C# F# . A C#~ A   (maj7 held)
        'a2': '11:1/4. 10:1/8 9:1/2',                             # E    B~ A G#~
        'a3': '5:1/8 8:1/8 r:1/8 10:1/8 12:1/8 13:1/4! 12:1/8',   # F#m  C# F# . A C# D~ C#  (b6 leaning on 5)
        'a4': '14:1/2 12:1/4 10:1/4',                             # A    E6~ C# A  (the phrase peak, held)
        'b2': '9:1/4. 10:1/8 11:1/2',                             # E    G#~ A B~  (the answer turns upward)
        'b3': 'r:1/8 5:1/8 8:1/8 r:1/8 10:1/8 12:1/8 13:1/4!',    # F#m  the head displaced by an 8th, hangs on D
        'b4': '12:1/4. 11:1/8 9:1/4 7:1/4',                       # E    C#~ B G# E  (D resolves, falls)
        'c1': '10:1/8 12:1/8 r:1/8 12:1/8 14:1/8 15:1/4! 14:1/8',  # D    A C# . C# E F#6~ E  (the climax)
        'c2': '14:1/4. 13:1/8 11:1/2',                            # E    E6~ D B~
        'c3': '12:1/4 10:1/8 9:1/8 8:1/2',                        # F#m  C# A G# F#~
        'c4': '_:1/2 5:1/8 8:1/8 r:1/8 10:1/8',                   # F#m  (F# held) C# F# . A: the head echoes
    }

    def mot(*keys):
        return s.motif(' '.join(H[k] for k in keys))

    hook_m = mot('a1', 'a2', 'a3', 'a4') + mot('a1', 'b2', 'b3', 'b4') + mot('a1', 'a2', 'a3', 'a4') \
        + mot('c1', 'c2', 'c3', 'c4')                                          # 16 bars: A B A C

    V = {   # verse lines, one bar each (F#m E D E): held downbeats, phrase ends pushed an 8th early
        'a0': 'r:1/2 1:1/8 3:1/8 5:1/8 3:1/8',      # F#m  . . F# A C# A
        'a1': '4:1/4. 3:1/8 2:1/4. 5:1/8',          # E    B~ A G#~ C#>
        'a2': '_:1/2 4:1/8 3:1/8 1:1/4',            # D    ~C# B A F#
        'a3': '2:1/4. 1:1/8 -1:1/2',                # E    G#~ F# E~
        'rest': 'r:4',                              #      (the bells answer)
        'a6': '3:1/2. 5:1/8 6:1/8',                 # D    A~ C# D
        'a7': '7:1/4. 5:1/8 4:1/2',                 # E    E~ C# B~
        'b0': 'r:1/2 1:1/8 3:1/8 5:1/8 8:1/8',      # F#m  . . F# A C# F#
        'b1': '7:1/4. 6:1/8 4:1/4. 8:1/8',          # E    E~ D B~ F#>
        'b2': '_:1/2 7:1/8 6:1/8 5:1/4',            # D    ~F# E D C#
        'b3': '4:1/4. 5:1/8 7:1/2',                 # E    B~ C# E~
        'b4': 'r:1/2 5:1/8 8:1/8 10:1/8 8:1/8',     # F#m  . . C# F# A F#
        'b5': '9:1/4. 8:1/8 7:1/4. 8:1/8',          # E    G#~ F# E~ F#>
        'b6': '_:1/2 10:1/8 9:1/8 8:1/4',           # D    ~F# A G# F#
        'b7': '9:1/4. 8:1/8 7:1/4 r:1/4',           # E    G#~ F# E .
    }

    def vmot(*keys):
        return s.motif(' '.join(V[k] for k in keys))

    verse_a = vmot('a0', 'a1', 'a2', 'a3', 'rest', 'rest', 'a6', 'a7')
    verse_b = vmot('b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7')
    verse_c = vmot('a0', 'a1', 'a2', 'a3', 'b0', 'b1', 'b2', 'b3')           # verse 2: straight to the climb
    build1_m = s.motif('r:1/2 1:1/8 4:1/8 r:1/8 6:1/8 | 8:1/2. r:1/4 | r:1/2 3:1/8 6:1/8 r:1/8 8:1/8 '
                       '| 10:1/2. r:1/4 | r:1/2 4:1/8 7:1/8 r:1/8 9:1/8 | 11:1/2. r:1/4 '
                       '| 12:1/2 11:1/4 9:1/4 | #7:1/2. r:1/4')      # the head sequenced Bm, D, E; E# -> F#
    build2_m = s.motif('r:1/2 1:1/8 4:1/8 r:1/8 6:1/8 | r:1/2 3:1/8 6:1/8 r:1/8 8:1/8 '
                       '| r:1/2 4:1/8 7:1/8 r:1/8 9:1/8 | #7:1/2. r:1/4')
    answer_m = [s.motif('r:1/2 r:1/8 7:1/8 5:1/4'), s.motif('r:1/2 r:1/8 9:1/8 7:1/8 5:1/8'),
                s.motif('r:1/2 r:1/8 8:1/8 7:1/8 5:1/8'), s.motif('r:1/2 r:1/8 9:1/8 11:1/8 12:1/8')]

    hook_clip = hook_m.clip(octave=4, vel=104)
    double_clip = hook_m.clip(octave=3, vel=96)
    # chorus 2 second voice: mostly diatonic 6ths below the hook, bent onto chord tones
    H2 = {
        'a1': '-1:1/8 3:1/8 r:1/8 5:1/8 7:1/4. 5:1/8', 'a2': '7:1/4. 5:1/8 4:1/2',
        'a3': '-1:1/8 3:1/8 r:1/8 5:1/8 7:1/8 8:1/4 7:1/8', 'a4': '10:1/2 7:1/4 5:1/4',
        'b2': '4:1/4. 5:1/8 7:1/2', 'b3': 'r:1/8 -1:1/8 3:1/8 r:1/8 5:1/8 7:1/8 8:1/4',
        'b4': '7:1/4. 6:1/8 4:1/4 2:1/4', 'c1': '5:1/8 7:1/8 r:1/8 7:1/8 8:1/8 10:1/4 8:1/8',
        'c2': '9:1/4. 8:1/8 7:1/2', 'c3': '7:1/4 5:1/8 4:1/8 3:1/2', 'c4': '_:1/2 -1:1/8 3:1/8 r:1/8 5:1/8',
    }

    def mot2(*keys):
        return s.motif(' '.join(H2[k] for k in keys))

    harmony_m = (mot2('a1', 'a2', 'a3', 'a4') + mot2('a1', 'b2', 'b3', 'b4') + mot2('a1', 'a2', 'a3', 'a4')
                 + mot2('c1', 'c2', 'c3', 'c4'))
    harmony_clip = harmony_m.clip(octave=4, vel=78)

    # ------------------------------------------------------------------ the band (preset) + the song's own layers
    b = bands.outrun(s, ids={'lead': 'hook'})
    kit, bass, pad, keys, arp, hook = b.drums, b.bass, b.pad, b.keys, b.arp, b.lead
    hall, plate, echo = b.hall, b.plate, b.echo
    # tone vs Nightcall (loudness-matched compare): the hook owns the 0.7-2.2 kHz excess and part of the 4.5-9 kHz one
    hook.add_fx(fx.eq({'peak1.freq': 1250, 'peak1.gain': -4.5, 'peak1.q': 0.9,
                       'peak3.freq': 6300, 'peak3.gain': -4.0, 'peak3.q': 1.2, 'high.freq': 8000, 'high.gain': -1.5}))
    hook.add_fx(fx.eq({'peak2.freq': 850, 'peak2.gain': -2.0, 'peak2.q': 1.2}))   # the choruses' 0.7-1.4 kHz honk
    pad.add_fx(fx.eq({'peak1.freq': 330, 'peak1.gain': 1.5, 'peak1.q': 0.8}))     # body back into the low mids
    bass.add_fx(fx.eq({'low.freq': 55, 'low.gain': 2.0, 'peak1.freq': 82, 'peak1.gain': -2.0, 'peak1.q': 1.6,
                       'peak2.freq': 200, 'peak2.gain': 1.5, 'peak2.q': 0.8}))

    # the drum bus lets the kick through: 20 ms attack instead of the preset's 4 (kick punch was 11 vs 16 dB)
    kit.fx[1] = kit.fx[1].but(attack=20)
    kit.send(plate, -24)                           # less plate on the hats: they tick instead of hiss
    kit.gain_db = 0.0                              # +1 dB over the preset: the kick leads the low end

    double = s.track('hook-double', 'synthwave/pulse_lead', gain_db=-8, sends={hall: -14, echo: -18})
    # the verse melody on the keytar voice (two saws, Moog ladder, tube, legato glide) instead of the bare pulse:
    # a played-sounding lead, not a chiptune square
    vlead = s.track('verse-lead', patches.get('synthwave/solo_lead').but(glide=0.035), gain_db=-3, pan=0.05,
                    sends={hall: -11, echo: -13}).humanize(3, 5)
    strings = s.track('strings', 'synthwave/jupiter_strings', gain_db=-6, sends={hall: -8})
    choir = s.track('choir', 'sampled/fairlight_choir', gain_db=-5, sends={hall: -8})
    glass = s.track('glass', 'synthwave/arp_glass', gain_db=-6, pan=-0.45, sends={hall: -12, echo: -12})
    sax = s.track('sax', 'sampled/tenor_sax', gain_db=1, sends={hall: -8, plate: -13, echo: -15},
                  fx=[fx.chorus(mode='I', mix=0.25), fx.microshift(style='smooth', detune=8, mix=0.3)])
    robot = s.track('robot', 'synthwave/vocoder_choir', gain_db=-6, sends={hall: -7, echo: -14})
    rise = s.track('riser', 'synthwave/noise_riser', gain_db=-9)
    rev = s.track('reverse', patches.get('synthwave/noise_riser').but(amp__attack=0.9, amp__release=0.03,
                                                                      hpf=1800, resonance=0.25), gain_db=-10)
    boom = s.track('impact', 'synthwave/impact', gain_db=0)
    fall = s.track('downlifter', 'synthwave/downlifter', gain_db=-7)

    # the robot's words (Windows TTS, cached in samples/speech/ next to this file)
    vox = speech.words(['last exit', 'before dawn', 'last exit before dawn'], voice='onecore:Stefan', rate=-2)
    voice = s.track('voice', vox.instrument())

    # ------------------------------------------------------------------ drums
    K = 'x...x...x...x...'
    H8 = '6.8.6.8.6.8.6.8.'
    H16 = '4737473747374737'
    g_intro = drums({'hat': '..5...5...5...6.'})
    g_verse_a = drums({'kick': K, 'hat': H8})
    g_verse_b = drums({'kick': K, 'snare': '....x.......x...', 'hat': H16, 'ohh': '..............5.'})
    g_verse2 = drums({'kick': K, 'snare': '....x.......x...' + '....x.......x..o', 'hat': H16,
                      'tamb': '....5.......5...', 'ohh': '.' * 30 + '6.'})
    g_chorus1 = drums({'kick': K, 'snare': '....x.......x...', 'clap': '....x.......x...',
                       'hat': '4747474747474747', 'ohh': '..............7.'})
    g_chorus2 = drums({'kick': K, 'snare': '....x.......x...', 'clap': '....x.......x...',
                       'hat': '47.747.747.747.7', 'ohh': '..6...6...6...7.'})
    g_final = drums({'kick': K, 'snare': '....x.......x...', 'clap': '....x.......x...',
                     'hat': '47.747.747.747.7', 'ohh': '..6...6...6...7.', 'tamb': '....5.......5...'})
    kick_only = drums({'kick': K})
    g_half = drums({'kick': 'x.......x.......', 'snare': '........x.......', 'hat': '4.6.4.6.4.6.4.6.'})

    kit.loop(g_intro, intro.bar(4), bars=4)
    kit.loop(g_verse_a, verse1, bars=8).loop(g_verse_b, verse1.bar(8), bars=8)   # verse grows: backbeat at bar 9
    kit.loop(g_verse_b, build1, bars=6).loop(kick_only, build1.bar(6), bars=1)
    kit.play(snare_roll(6.5, build=True, vel=(45, 122)), build1.bar(6))
    kit.loop(g_chorus1, chorus1)
    kit.loop(g_verse2, verse2)
    kit.loop(g_verse_b, build2, bars=2).loop(drums({'kick': 'x.x.x.x.x.x.x.x.'}), build2.bar(2), bars=1)
    kit.play(snare_roll(6.5, build=True, pitch='clap', vel=(50, 120)), build2.bar(2))
    kit.loop(g_chorus2, chorus2)
    # bridge: a real breakdown - no drums for 4 bars, half-time hats under the solo, the groove returns at bar 9
    kit.loop(drums({'hat': '3.5.3.5.3.5.3.6.'}), bridge.bar(4), bars=2)
    kit.loop(g_half, bridge.bar(6), bars=2)
    kit.loop(g_verse_b, bridge.bar(8), bars=2).loop(kick_only, bridge.bar(10), bars=1)
    kit.play(snare_roll(6.5, build=True, vel=(40, 124)), bridge.bar(10))
    kit.loop(g_final, final)
    kit.loop(g_verse_a, outro, bars=4)

    for at in (verse1.start, chorus1.start, chorus1.bar(8), verse2.start, chorus2.start, chorus2.bar(8),
               bridge.bar(8), final.start, final.bar(8), outro.start):
        kit.play(crash(112), at)

    def fill(at, clip):
        kit.play(clip, at, replace=True)

    fill(intro.beat(-1), tom_fill(1))
    fill(verse1.bar(7, 3), snare_roll(1, vel=(60, 105)))
    fill(verse1.beat(-1), tom_fill(1))
    fill(chorus1.bar(7, 3), tom_fill(1))
    fill(chorus1.beat(-2), tom_fill(2))
    fill(verse2.beat(-1), snare_roll(1, vel=(60, 110)))
    fill(chorus2.bar(3, 3), snare_roll(1, vel=(60, 105)))
    fill(chorus2.bar(7, 3), tom_fill(1))
    fill(chorus2.bar(11, 3), snare_roll(1, vel=(60, 105)))
    fill(chorus2.beat(-2), tom_fill(2))
    fill(bridge.bar(7, 3), tom_fill(1))
    fill(final.bar(3, 3), tom_fill(1))
    fill(final.bar(7, 3), tom_fill(1))
    fill(final.bar(11, 3), tom_fill(1))
    fill(final.beat(-2), tom_fill(2))
    fill(outro.bar(3, 2), tom_fill(2))

    # ------------------------------------------------------------------ bass (8th-note octave drive, gate 0.85)
    G = 0.85
    bass.loop(bassline('F#m', 'octave', rate='1/8', gate=G), verse1, bars=8)          # tonic pedal, filter closed
    bass.loop(P_verse.bass('octave', rate='1/8', gate=G), verse1.bar(8), bars=8)      # release: follows the roots
    bass.play(P_build1.bass('octave', rate='1/8', gate=G), build1)
    bass.play(bassline('C#', 'octave', rate='1/16', gate=G), build1.bar(7), replace=True)
    bass.play(P_chorus.bass('octave', rate='1/8', gate=G), chorus1)
    bass.loop(bassline(P_verse, pattern='rorororf', gate=G), verse2)
    bass.play(P_build2.bass('octave', rate='1/8', gate=G), build2)
    bass.play(bassline('C#', 'octave', rate='1/16', gate=G), build2.bar(3), replace=True)
    bass.play(P_chorus.bass('octave', rate='1/8', gate=G), chorus2)
    bass.play(P_chorus.bass('octave', rate='1/16', gate=G).slice(48, 64), chorus2.bar(12), replace=True)
    bass.play(P_bridge.bass('root', vel=90).slice(16, 32), bridge.bar(4))           # long roots under the solo
    bass.play(P_bridge.bass('octave', rate='1/8', gate=G).slice(32, 40), bridge.bar(8))
    bass.play(bassline('E', 'octave', rate='1/8', gate=G), bridge.bar(10))
    bass.play(bassline('D#', 'octave', rate='1/16', gate=G), bridge.bar(11))
    bass.play(P_final.bass('octave', rate='1/8', gate=G), final)
    bass.play(P_final.bass('octave', rate='1/16', gate=G).slice(32, 64), final.bar(8), replace=True)
    bass.play(P_outro.bass('octave', rate='1/8', gate=G).slice(0, 16), outro)
    bass.play(P_outro.bass('root', vel=92).slice(16, 32), outro.bar(4))                # long roots, then the end

    # ------------------------------------------------------------------ pads, strings, choir
    PAD = dict(voicing='spread', register=('C#3', 'E5'))
    PAD_UP = dict(voicing='spread', register=('D#3', 'F#5'))
    pad.play(P_intro.block(**PAD), intro)
    pad.loop(P_verse.block(**PAD), verse1)
    pad.play(P_build1.block(**PAD), build1)
    pad.play(P_chorus.block(**PAD), chorus1)
    pad.loop(P_verse.block(**PAD), verse2)
    pad.play(P_build2.block(**PAD), build2)
    pad.play(P_chorus.block(**PAD), chorus2)
    pad.play(P_bridge.block(**PAD), bridge)
    pad.play(P_final.block(**PAD_UP), final)
    pad.play(P_outro.block(**PAD_UP), outro)

    strings.play(P_build1.block(register=('A4', 'A5'), voices=3, vel=70).slice(16, 32), build1.bar(4))
    strings.play(P_chorus.block(register=('A4', 'A5'), voices=3, vel=66), chorus1)     # chorus 1: a quieter halo
    strings.play(P_build2.block(register=('A4', 'A5'), voices=3, vel=68), build2)
    strings.play(P_chorus.block(register=('A4', 'A5'), voices=3, vel=78), chorus2)
    strings.play(P_bridge.block(register=('F#4', 'F#5'), voices=3, vel=52).slice(0, 16), bridge)
    strings.play(P_bridge.block(register=('F#4', 'F#5'), voices=3, vel=64).slice(16, 48), bridge.bar(4))
    strings.play(P_final.block(register=('B4', 'B5'), voices=3, vel=84), final)
    strings.play(P_outro.block(register=('B4', 'B5'), voices=3, vel=70), outro)
    choir.play(P_bridge.block(register=('C#4', 'C#5'), voices=3, vel=80).slice(16, 48), bridge.bar(4))
    choir.play(P_final.block(register=('D#4', 'D#5'), voices=3, vel=90), final)
    choir.play(P_outro.block(register=('D#4', 'D#5'), voices=3, vel=80).slice(16, 32), outro.bar(4))

    # ------------------------------------------------------------------ arps, bells, keys
    AR, AR_UP = ('F#4', 'F#5'), ('G#4', 'G#5')
    arp.play(P_intro.arp('up', octaves=2, register=AR), intro)
    arp.loop(P_verse.arp('up', octaves=2, register=AR), verse1)
    arp.play(P_build1.arp('updown', octaves=2, register=AR), build1)
    arp.play(P_chorus.arp('updown', octaves=2, register=AR), chorus1)
    arp.loop(P_verse.arp('pinky', octaves=2, register=AR), verse2)
    arp.play(P_build2.arp('up', octaves=2, register=AR), build2)
    arp.play(P_chorus.arp('updown', octaves=2, register=AR), chorus2)
    arp.play(P_bridge.arp('up', octaves=2, register=AR).slice(32, 48), bridge.bar(8))
    arp.play(P_final.arp('updown', octaves=2, register=AR_UP), final)
    arp.play(P_outro.arp('up', octaves=2, register=AR_UP).slice(0, 24), outro)

    rest_bar = s.motif('r:4')
    glass.play((mot('a1') + rest_bar + mot('a3') + rest_bar).clip(octave=3, vel=84), intro.bar(4))  # a memory
    glass.play(mot('a1', 'a2').clip(octave=3, vel=80), verse1.bar(4))       # answers in the verse's gap
    for i, m in enumerate(answer_m):                                         # verse 2: call & response
        glass.play(m.clip(octave=3, vel=90), verse2.bar(2 * i + 1))
    glass.play(P_chorus.arp('up', rate='1/8', register=('F#4', 'F#5'), vel=72), chorus2)
    glass.play(P_bridge.arp('up', rate='1/4', register=('F#4', 'F#5'), vel=64).slice(0, 16), bridge)
    glass.play(hook_clip.transpose(UP).velocity(0.75), final)                          # sounds an octave up
    glass.note('G#5', outro.bar(7), 4, 72).note('D#6', outro.bar(7, 1), 3, 62).note('A#6', outro.bar(7, 2), 2, 54)

    keys.loop(P_verse.block(voicing='drop2', register=('C#4', 'C#5'), rhythm='x..x..x.', vel=82), verse1.bar(8),
              bars=8)
    keys.loop(P_verse.block(voicing='drop2', register=('C#4', 'C#5'), rhythm='x..x..x...x..x..', vel=88), verse2)
    keys.play(P_chorus.block(voicing='drop2', register=('C#4', 'C#5'), rhythm='x..x..x.', vel=76), chorus2)
    keys.play(P_bridge.block(voicing='drop2', register=('C#4', 'C#5'), vel=74).slice(0, 16), bridge)
    keys.play(P_bridge.block(voicing='drop2', register=('C#4', 'C#5'), rhythm='x..x..x.', vel=76).slice(16, 32),
              bridge.bar(4))
    keys.play(P_final.block(voicing='drop2', register=('D#4', 'D#5'), rhythm='x..x..x.', vel=78), final)
    keys.play(P_outro.block(voicing='drop2', register=('D#4', 'D#5'), vel=70).slice(16, 32), outro.bar(4))

    # ------------------------------------------------------------------ leads
    vlead.play(verse_a.clip(octave=4, vel=92), verse1).play(verse_b.clip(octave=4, vel=96), verse1.bar(8))
    vlead.play(build1_m.clip(octave=4, vel=98), build1)
    vlead.play(verse_c.clip(octave=4, vel=96), verse2)
    vlead.play(build2_m.clip(octave=4, vel=100), build2)

    hook.play(hook_clip, chorus1).play(hook_clip, chorus2).play(hook_clip.transpose(UP), final)
    double.play(double_clip, chorus1).play(double_clip | harmony_clip, chorus2)
    double.play(double_clip.transpose(UP), final)

    # the sax: written at sounding pitch; the tenor's range ends at E5
    SOLO = [
        # bars 1-4 (Dmaj7, E): the hook's head displaced to beat 2, its C# held over Dmaj7, answered lower
        (5.0, .5, 'C#4'), (5.5, .5, 'F#4'), (6.5, .5, 'A4'), (7.0, 2.0, 'C#5', 108), (9.0, .5, 'B4'), (9.5, .5, 'A4'),
        (10.0, 1.0, 'G#4'), (11.0, .5, 'F#4'), (11.5, .5, 'E4'),
        (12.5, .5, 'E4'), (13.0, .5, 'F#4'), (13.5, .5, 'G#4'), (14.0, 1.0, 'B4'), (15.0, .5, 'A4'), (15.5, .5, 'G#4'),
        # bars 5-8 (F#m B D E): the dorian D# over B, a 16th run
        (16.0, 1.5, 'F#4', 110), (17.5, .5, 'E4'), (18.0, .5, 'F#4'), (18.5, .5, 'A4'), (19.0, 1.0, 'C#5'),
        (20.0, 1.0, 'D#5', 112), (21.0, .5, 'C#5'), (21.5, .5, 'B4'), (22.0, 1.5, 'F#4'), (23.5, .5, 'G#4'),
        (24.0, .25, 'A4'), (24.25, .25, 'G#4'), (24.5, .25, 'F#4'), (24.75, .25, 'E4'), (25.0, .5, 'F#4'),
        (25.5, .5, 'A4'), (26.0, 1.0, 'D5', 112), (27.0, .5, 'C#5'), (27.5, .5, 'A4'),
        (28.0, 1.5, 'B4'), (29.5, .5, 'G#4'), (30.0, .5, 'E4'), (30.5, .5, 'G#4'), (31.0, 1.0, 'B4'),
        # bars 9-12 (F#m B E D#sus4 D#): the head sequenced up a step per bar, then D# pulls to G# minor
        (32.0, .5, 'C#4'), (32.5, .5, 'F#4'), (33.5, .5, 'A4'), (34.0, 2.0, 'C#5', 112),
        (36.0, .5, 'D#4'), (36.5, .5, 'G#4'), (37.5, .5, 'B4'), (38.0, 2.0, 'D#5', 116),
        (40.0, .5, 'E4'), (40.5, .5, 'A4'), (41.5, .5, 'C#5'), (42.0, 2.0, 'E5', 122),
        (44.0, .25, 'D#4'), (44.25, .25, 'G#4'), (44.5, .25, 'A#4'), (44.75, 1.25, 'D#5', 120),
    ]
    # final chorus: short answers in the hook's held notes, echoing the solo (sounding pitches, G# minor)
    LICKS = [
        (6.5, .25, 'C#4'), (6.75, .25, 'D#4'), (7.0, .75, 'F#4', 106), (7.75, .25, 'D#4'),               # bar 2 (F#)
        (12.5, .25, 'D#4'), (12.75, .25, 'E4'), (13.0, .5, 'F#4', 106), (13.5, .5, 'D#4'),               # bar 4 (B)
        (28.5, .25, 'A#3'), (28.75, .25, 'C#4'), (29.0, 1.0, 'D#4', 106),                               # bar 8 (F#)
        (44.5, .25, 'D#4'), (44.75, .25, 'F#4'), (45.0, .5, 'G#4', 110), (45.5, .5, 'F#4'),             # bar 12 (B)
        (58.5, .5, 'D#4'), (59.0, .5, 'F#4'), (59.5, .5, 'G#4'),                                        # bars 15-16
        (60.0, .25, 'B4'), (60.25, .25, 'A#4'), (60.5, 1.5, 'G#4', 112),
    ]
    # outro: the hook's head one last time (G# minor), falling home instead of climbing; the last G# rings
    OUT = [
        (0.0, .5, 'D#4'), (0.5, .5, 'G#4'), (1.5, .5, 'B4'), (2.0, 1.5, 'D#5', 108), (3.5, .5, 'B4'),
        (4.0, 1.5, 'C#5'), (5.5, .5, 'B4'), (6.0, 2.0, 'A#4'),
        (8.0, .5, 'D#4'), (8.5, .5, 'G#4'), (9.5, .5, 'B4'), (10.0, .5, 'D#5'), (10.5, 1.0, 'E5', 112),
        (11.5, .5, 'D#5'), (12.0, 2.0, 'F#4'), (14.0, 1.0, 'A#4'), (15.0, 1.0, 'B4'),
        (16.0, 2.0, 'B4', 100), (18.0, .5, 'G#4'), (18.5, .5, 'B4'), (19.0, 1.0, 'D#5', 104),     # E (maj7)
        (20.0, 2.0, 'C#5', 100), (22.0, 1.0, 'A#4'), (23.0, 1.0, 'F#4'),                          # F#
        (24.0, 2.0, 'G#4', 96), (26.0, 1.0, 'A#4', 96), (27.0, 1.0, 'G4', 100),                   # D#sus4 D#
        (28.0, 4.0, 'G#4', 92),                                                                    # G#m: home
    ]

    def line(notes, length):
        return Clip([(n[0], n[1], n[2], n[3] if len(n) > 3 else 100) for n in notes], length=length)

    solo = art.perform(sax, line(SOLO, bridge.length), bridge, glide_leaps=5, glide_ms=90, humanize_ms=7, seed=3)
    art.perform(sax, line(LICKS, final.length), final, glide_leaps=5, glide_ms=80, humanize_ms=6, seed=5)
    art.perform(sax, line(OUT, outro.length), outro, glide_leaps=5, glide_ms=110, humanize_ms=8, seed=7)
    # scoops into the solo's peaks (a player bending up into the note)
    bend = []
    for at in (bridge.start + 7, bridge.start + 20, bridge.start + 34, bridge.start + 38, bridge.start + 42,
               final.start + 60.5, outro.start + 2, outro.start + 10.5):
        bend += [(at - 0.05, 0), (at, -1.0, 'step'), (at + 0.3, 0, 'smooth')]
    sax.automate('instrument.pitchbend', bend)

    # ------------------------------------------------------------------ the robot: "last exit ... before dawn"
    voice.play(vox.clip({0: 'last exit', 8: 'before dawn'}, length=16), intro.bar(4))
    voice.play(vox.clip({0: 'last exit before dawn'}, length=8), bridge)
    voice.play(vox.clip({0: 'before dawn'}, length=4), outro.bar(7))
    RV = dict(voicing='spread', register=('A2', 'E5'), voices=5)
    robot.play(s.prog('i').block(**RV).slice(0, 3), intro.bar(4))                 # F#m
    robot.play(s.prog('III').block(**RV).slice(0, 3), intro.bar(6))               # A
    robot.play(s.prog('VImaj7:2').block(**RV).slice(0, 7), bridge)                # Dmaj7
    robot.play(s.prog('i').transpose(UP).block(**RV), outro.bar(7))               # G#m: the last word
    speech.vocode(robot, voice)
    # the ending: slow into the last chord, which rings 6 beats longer; the robot freezes the vowel of 'dawn'
    s.ritardando((outro.bar(5), outro.bar(7)), to=0.78, a_tempo=False)
    s.fermata(outro.bar(7), hold=6, length=4)
    dawn = outro.bar(7) + 0.7 * vox.seconds['before dawn'] * s.tempo_at(outro.bar(7) + 0.01) / 60
    robot.automate('fx.vocoder.hold', [(0, 0), (dawn - 0.01, 0), (dawn, 1, 'step'), (outro.end, 1)])

    # ------------------------------------------------------------------ transitions: risers, impacts, drops
    rises = [(verse1.start, 16, 80), (build1.end - 1, 31, 110), (build2.end - 1, 15, 110), (bridge.end - 1, 15, 115)]
    for end, L, v in rises:
        rise.note('A3', end - L, L, v)
    rise.automate('instrument.cutoff', *[riser(e, L, 300, 12000) for e, L, _ in rises])
    rise.automate('instrument.hpf', *[riser(e, L, 20, 1500) for e, L, _ in rises])
    for c in (chorus1, chorus2, final):          # reversed-cymbal swell sucking into each chorus, through the drop
        rev.note('A3', c.start - 2, 2, 100)
    rev.automate('instrument.cutoff', *[riser(c.start, 2, 2500, 16000) for c in (chorus1, chorus2, final)])
    boom.note('D2', chorus1.start, 4, 120).note('D2', chorus2.start, 4, 116).note('E1', final.start, 4, 124)
    boom.note('G#1', outro.bar(7), 4, 104)                                   # the last chord is struck
    kit.play(crash(104), outro.bar(7)).note('kick', outro.bar(7), 1, 110)
    fall.note('A3', verse2.start, 4, 90).note('A3', bridge.start, 8, 110).note('A3', outro.start, 8, 100)
    for c in (chorus1, chorus2, final):
        bass.clear(c.start, c.start + 1)            # the impact's sub boom owns the downbeat

    # one-beat drop before every chorus: everything stops, only the riser's tail and the reverbs remain
    def cut(t, d, gap=1.0):
        t.clear(d, d + gap)
        for n in [n for n in t.notes if n.start < d - 1e-9 and n.start + n.dur > d + 1e-9]:
            t.clear(n.start, n.start + 1e-6, pitches=n.pitch)          # shorten notes ringing into the drop
            t.note(n.pitch, n.start, d - n.start, n.vel)

    for d in (build1.end - 1, build2.end - 1, bridge.end - 1):
        for t in (kit, bass, pad, strings, choir, arp, glass, keys, vlead, double, hook, sax):
            cut(t, d)


    # ------------------------------------------------------------------ movement & mix
    s.sidechain(strings, choir, glass, key=kit, pitches='kick', depth=4, release=250)
    s.sidechain(bass, key=kit, pitches='kick', depth=7, release=110)       # + the preset's 3 dB: the kick breathes

    pad.automate('instrument.cutoff', [
        (intro.start, 500), (verse1.start, 2600, 'exp'), (verse1.start, 1900), (verse1.bar(8), 1900),
        (build1.start, 2300, 'exp'), (build1.end - 1, 5200, 'exp'), (chorus1.start, 4000),
        (verse2.start, 4000), (verse2.start, 2100), (build2.start, 2100), (build2.end - 1, 5200, 'exp'),
        (chorus2.start, 4200), (bridge.start, 4200), (bridge.start, 1100), (bridge.bar(4), 2400, 'exp'),
        (bridge.end - 1, 5200, 'exp'), (final.start, 4800), (outro.start, 4800), (outro.end, 900, 'exp'),
    ])
    arp.automate('instrument.cutoff', [
        (intro.start, 450), (verse1.start, 1400, 'exp'), (verse1.bar(8), 1400), (build1.start, 1800, 'exp'),
        (build1.end - 1, 4200, 'exp'), (chorus1.start, 2600), (verse2.start, 2600), (verse2.start, 1600),
        (build2.start, 1600), (build2.end - 1, 4200, 'exp'), (chorus2.start, 2800), (bridge.start, 2800),
        (bridge.start, 900), (bridge.end - 1, 4200, 'exp'), (final.start, 3000), (outro.start, 3000),
        (outro.end, 400, 'exp'),
    ])
    arp.modulate('pan', lfo('sine', rate='4 bars', depth=0.35))                  # slow drift across the stereo field
    bass.automate('instrument.cutoff', [
        (verse1.start, 500), (verse1.bar(7), 500), (verse1.bar(8), 900, 'exp'),   # opens with the backbeat
        (build1.start, 900), (build1.start, 500), (build1.end - 1, 1800, 'exp'), (chorus1.start, 1200),
        (verse2.start, 1200), (verse2.start, 850), (build2.start, 850), (build2.start, 500),
        (build2.end - 1, 1800, 'exp'), (chorus2.start, 1200), (bridge.start, 1200), (bridge.start, 380),
        (bridge.bar(8), 380), (bridge.bar(8), 550), (bridge.end - 1, 1800, 'exp'), (final.start, 1300),
        (outro.start, 1300), (outro.end, 450, 'exp'),
    ])
    # the hall blooms in the breaks
    pad.automate('send.hall', [(intro.start, -3), (verse1.start, -6, 'step'), (bridge.start, -2, 'step'),
                               (bridge.bar(8), -6, 'step'), (outro.bar(4), -6), (outro.end, -1, 'smooth')])

    # delay throws: the hook's echo send jumps up on beats 3-4 of a phrase end (chorus 2 once, final three times)
    throws = [chorus1.bar(15, 2), chorus2.bar(7, 2), final.bar(3, 2), final.bar(7, 2), final.bar(11, 2)]
    pts = [(0, -12)]
    for t in throws:
        pts += [(t, -12), (t, -4), (t + 2, -4), (t + 2, -12)]
    hook.automate('send.echo', pts)

    # arrangement dynamics: small section-level moves on top of the arrangement itself
    # (a tuple = ramp from..to across the section, a list = [(bar, dB), ...] steps inside it)
    E = {'intro': 0, 'verse1': -2, 'build1': (-2, 0), 'chorus1': 0, 'verse2': -2, 'build2': (-2, 0),
         'chorus2': 0, 'bridge': [(0, -3), (8, -1.5)], 'final': 0.5, 'outro': [(0, -1), (4, -2)]}
    ZERO = {k: 0 for k in E}

    def energy(track, scale=1.0, base_map=E, **override):
        base, pts = 0.0, []                        # a 'gainDb' lane is dB on the track's gain_db

        for sec in s.sections:
            v = override.get(sec.name, base_map[sec.name])
            if isinstance(v, tuple):
                pts += [(sec.start, base + scale * v[0], 'step'), (sec.end - 1, base + scale * v[1])]
            elif isinstance(v, list):
                pts += [(sec.bar(b), base + scale * x, 'step') for b, x in v]
            else:
                pts.append((sec.start, base + scale * v, 'step'))
        track.automate('gainDb', pts)

    energy(kit, verse1=[(0, -3), (8, -1.5)], chorus1=0, chorus2=0, final=0.5)
    energy(bass, verse1=[(0, -4), (8, -2.5)], verse2=-3, bridge=[(0, -5), (8, -2)])
    energy(pad, verse1=-3.5, verse2=-2.5, bridge=[(0, -4), (8, -1.5)], chorus1=-2, chorus2=-2, final=-1.5)
    energy(arp, intro=[(0, -8), (4, -4)], verse1=[(0, -4), (8, -2.5)], verse2=-2.5)
    # the bells carry the hook's memory in the intro and the verse gap: audible, not a -10 dB ghost under the pad
    energy(glass, base_map=ZERO, intro=5, verse1=4, verse2=3, final=-2)
    energy(keys, base_map=ZERO, verse2=-1.5, bridge=[(0, -2.5), (8, -3.5)])
    energy(sax, base_map=ZERO, bridge=[(0, -2.5), (8, -1)], final=1.5)
    # the hook stays on top of the growing bed (chorus 2 adds strings, the final chorus choir + strings + bells)
    energy(hook, base_map=ZERO, chorus1=1.0, chorus2=2.5, final=3.5)
    energy(vlead, base_map=ZERO, build1=1.5, build2=1.5)       # the sequenced head over the strings
    energy(double, base_map=ZERO, final=1.0)
    energy(choir, base_map=ZERO, bridge=[(0, -2), (4, 0)], final=-2, outro=-1)
    energy(strings, base_map=ZERO, chorus1=-3, final=-1.5)

    # master: the preset's chain (master/synthwave as bands.outrun sets it) with almost no low-mid dip (warmth); the
    # 0.7-2.2 kHz and 4-11 kHz excess of the Nightcall compare trimmed with broad bells, air above 13 kHz, wider,
    # mono below 150 Hz, 0.8 dB more drive (the section moves after the limiter give the level back to the verses)
    s.master.use(patches.get('master/synthwave')
                 .but_fx('eq', **{'hp.freq': 30, 'peak1.gain': -0.5, 'high.freq': 13000, 'high.gain': 2.0, 'peak2.freq': 1000,
                                  'peak2.gain': -5.5, 'peak2.q': 0.6, 'peak3.freq': 6500, 'peak3.gain': -2.0,
                                  'peak3.q': 0.6})
                 .but_fx('compressor', threshold=-18).but_fx('width', width=1.3, monobass=150)
                 .but_fx('limiter', gain=7.3))
    # section levels after the limiter (the limiter flattens pre-limiter moves): verses and the breakdown sit
    # 1-1.5 dB under the choruses, the builds ramp up into them. Then the ending: the last chord decays like a
    # struck chord (linear in dB) to -26 dB, so its release and the hall tail vanish instead of stopping.
    s.master.automate('gainDb', [
        (0, 0), (verse1.start, -1.0, 'step'), (build1.start, -1.0, 'step'), (build1.end - 1, 0),
        (chorus1.start, 0, 'step'), (verse2.start, -1.0, 'step'), (build2.start, -0.8, 'step'), (build2.end - 1, 0),
        (chorus2.start, 0, 'step'), (bridge.start, -1.5, 'step'), (bridge.bar(8), -0.8, 'step'),
        (bridge.end - 1, 0), (final.start, 0, 'step'), (outro.bar(7, 1), 0), (outro.end, -26, 'linear')])
    # the drumless intro and breakdown are wide on their own (pad, hall, bells): less master width there keeps them
    # mono-safe (correlation well above 0); the full sections get the whole 1.3
    s.master.automate('fx.width.width', [(0, 1.1), (verse1.start - 1, 1.1), (verse1.start, 1.3),
                                         (bridge.start, 1.3), (bridge.start + 1, 1.15), (bridge.bar(4), 1.15),
                                         (bridge.bar(6), 1.3)])
    return s
