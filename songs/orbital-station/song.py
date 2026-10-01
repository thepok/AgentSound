"""Halo Orbit (folder: orbital-station) - sci-fi / soundtrack synthwave.

Style: Sci-fi / soundtrack (S U R V I V E, Stranger Things, Vangelis' Blade Runner). 84 BPM, E minor with maj7 /
min9 colours; the final section lifts a whole step to F# minor. Built on the band preset bands.scifi (sampled TR-808,
Stranger-Things arp + pulse sequence, sweep pad, moog bass, DX bells, soft lead, dark 224XL hall, tape echo,
shimmer, master/dreamwave) plus a Fairlight choir, a sampled tenor sax (the Blade Runner voice), CS-80-style brass,
Jupiter + sampled strings, a glassy FM counter-arp, a sonar ping, a vocoder station voice and real cymbals.

Form (bars): intro 8 (signal) - drift 16 (verse) - approach 8 (build, dominant pedal) - orbit 16 (chorus,
drums enter half-time) - weightless 8 (breakdown: the sax sings the hook augmented) - ascent 4 (build, pivot to
F# minor) - horizon 16 (final chorus, full backbeat) - outro 8 (ritardando into the last chord).

Story: the station picks up a signal ("signal detected", the robot voice in the intro), the arp's filter opens
over four minutes as the music comes into focus, and at the end the signal fades ("signal lost") and the arp
closes into a held F#m9.

Themes:
  hook   = call (B E G | F# E D | E D B G | B) + answer (displaced head, octave leap, leading tone D#)
  signal = the hook head in diminution (8ths), sequenced down the scale in the verse; returns in the outro

Build: python -m agentsound build songs/orbital-station
"""
from agentsound import *
from agentsound import bands, speech, vamod
from agentsound import articulation as art

arpeggio = arp                                                   # the pattern (the name 'arp' is the track below)

ANALYSIS = {'profile': 'dreamwave'}                  # = bands.scifi(...).analysis

METADATA = {'title': 'Halo Orbit', 'artist': 'AgentSound', 'album': 'Neon Archive', 'genre': 'Synthwave',
            'year': 2026, 'comment': 'sci-fi synthwave / soundtrack, 84 BPM, E minor -> F# minor'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'HALO ORBIT',
         'subtitle': 'AgentSound', 'seed': 7}

UP = 2                      # key change for the final section: E minor -> F# minor
PAT_A = (0, 1, 2, 3, 4, 3, 2, 1)                                 # 1 3 5 7 9 7 5 3 (the Stranger Things shape)
PAT_B = (0, 1, 2, 3, 4, 3, 2, 1, 2, 3, 4, 5, 6, 5, 4, 3)          # second bar climbs an octave higher
PAT_SPARSE = (0, None, 2, 4, None, 3, None, 1)                  # weightless: holes in the sequence
PAT_RISE = (0, 1, 2, 3, 4, 5, 6, 7)                              # ascent: two-octave runs
PAT_MIRROR = (4, 3, 2, 1, 0, 1, 2, 3)                            # contrary motion for the glass layer
CYM = 'samples/sampleradar-hats-cymbals-gongs/Cymbals/'
REV_LONG, REV_SHORT = 88, 89                                     # reversed cymbals on the cym kit
REV_LONG_S, REV_SHORT_S = 4.32, 2.18                             # seconds from their start to their peak


def parse(spec):
    """'Em9:2 Cmaj7:2 B7' -> [('Em9', 2.0), ('Cmaj7', 2.0), ('B7', 1.0)] (bars)."""
    out = []
    for tok in spec.split():
        sym, _, bars = tok.partition(':')
        out.append((sym, float(bars) if bars else 1.0))
    return out


def arp_tones(sym, transpose=0):
    """Close-position chord tones with the root between G2 and F#3 (the S U R V I V E register)."""
    tones = chord(sym).transpose(transpose).notes(3)
    while tones[0] > 54:
        tones = [t - 12 for t in tones]
    while tones[0] < 43:
        tones = [t + 12 for t in tones]
    return tones


def arp_line(spec, rate=0.5, pattern=PAT_A, vel=84, gate=0.85, accent=1.18, transpose=0, cut_last=0.0,
             octave=0):
    """Arpeggio over a progression spec; the pattern restarts on every chord and indexes the chord
    tones (wrapping by octaves, None = rest). cut_last = beats of silence at the end (the drop)."""
    notes, t = [], 0.0
    for sym, bars in parse(spec):
        tones = [p + 12 * octave for p in arp_tones(sym, transpose)]
        n, L = len(tones), bars * 4
        for k in range(int(round(L / rate))):
            idx = pattern[k % len(pattern)]
            if idx is None:
                continue
            o, i = divmod(idx, n)
            pos = t + k * rate
            v = vel * (accent if abs(pos - round(pos)) < 1e-6 else 1.0)
            notes.append((pos, rate * gate, tones[i] + 12 * o, int(min(127, v))))
        t += L
    clip = Clip(notes, length=t)
    return drop(clip, cut_last) if cut_last else clip


def drop(clip, beats_=1.0):
    """Silence the last `beats_` of a clip (held notes are cut there): the pre-chorus drop."""
    return clip.slice(0, clip.length - beats_).with_length(clip.length)


def tame(presence=-3.0, top=-3.0, hp=150.0, lowmid=0.0):
    """Keep an added voice out of the bass and the 2-5 kHz band (the preset's roles carry their own eq)."""
    return fx.eq({'hp.freq': hp, 'peak1.freq': 300, 'peak1.gain': lowmid, 'peak1.q': 0.8,
                  'peak3.freq': 3000, 'peak3.gain': presence, 'peak3.q': 0.7, 'high.freq': 8000, 'high.gain': top})


def build() -> Song:
    s = Song('Halo Orbit', tempo=84, key='E minor', seed=7, tail=9.0)

    intro = s.section('intro', bars=8)
    drift = s.section('drift', bars=16)
    approach = s.section('approach', bars=8)
    orbit = s.section('orbit', bars=16)
    weightless = s.section('weightless', bars=8)
    ascent = s.section('ascent', bars=4)
    horizon = s.section('horizon', bars=16)
    outro = s.section('outro', bars=8)

    # the ending: the last phrase slows into the final chord, which rings into the tail
    s.ritardando((outro.bar(4), outro.bar(6)), to=0.78, a_tempo=False)

    # ------------------------------------------------------------------ harmony (bars per chord)
    P_INTRO = 'Em9:2 Cmaj7:2 Em9:2 Cmaj7:2'
    P_V1 = 'Em9:2 Cmaj7:2 Am9:2 B7sus4 B7'
    P_V2 = 'Em9:2 Cmaj7:2 Fmaj7:2 B7sus4 B7'            # Phrygian bII darkens the second pass
    P_BUILD = 'Am9:2 Cmaj7:2 Dadd9:2 B7sus4 B7'         # over a B pedal
    P_CHORUS = 'Cmaj7 Dadd9 Em9:2 Cmaj7 Dadd9 B7sus4 B7'  # VI-VII-i lift, V -> VI deceptive loop
    P_BREAK = 'Cmaj7:2 Bm7:2 Fmaj7#11:2 Gmaj7:2'
    P_ASCENT = 'Dmaj7:2 C#7sus4 C#7'                     # Dmaj7 = VII of E minor = VI of F# minor
    P_OUTRO = 'F#m9:2 Dmaj7#11:2 Bm9:2 F#m9:2'           # plagal iv -> i: the signal fades, no cadence

    def prog(spec, transpose=0):
        p = s.prog(spec)
        return p.transpose(transpose) if transpose else p

    def pads(spec, transpose=0, reg=(48, 72), voices=5, vel=74, times=1):
        return chords(prog(spec, transpose) * times, voicing='spread', register=reg, voices=voices, vel=vel)

    # ------------------------------------------------------------------ themes
    hook_call = s.motif('5:1/4 8:1/4 10:1/2 | 9:1/4. 8:1/8 7:1/2 | 8:1/4. 7:1/8 5:1/4 3:1/4 | 5:4')
    hook_answer = s.motif('r:1/8 5:1/8 8:1/4 12:1/2 | 11:1/4. 10:1/8 9:1/2 | 9:1/4. 8:1/8 9:1/2 | #7:1/2. r:1/4')
    hook = hook_call + hook_answer                                   # 8 bars over P_CHORUS
    harmony = s.motif('D4:1/4 G4:1/4 B4:1/2 | A4:1/4. G4:1/8 F#4:1/2 | G4:1/4. F#4:1/8 D4:1/4 B3:1/4 | D4:4 '
                      '| r:1/8 D4:1/8 G4:1/4 D5:1/2 | F#5:1/4. E5:1/8 D5:1/2 | A4:1/4. G4:1/8 A4:1/2 '
                      '| F#4:1/2. r:1/4')                            # 6ths / 3rds under the hook
    cell = s.motif('r:1/2 5:1/8 8:1/8 10:1/4 | 9:1/4. 8:1/8 7:1/2')   # hook head in diminution
    cell_up = s.motif('r:1/2 5:1/8 8:1/8 10:1/4 | 12:1/4. 10:1/8 9:1/2')  # answer rises instead
    cadence = s.motif('r:1/2 5:1/8 8:1/8 9:1/4 | #7:4')
    signal = cell.sequence(0, -1, -2) + cadence                      # 8 bars over P_V1
    signal2 = cell_up.sequence(0, -1, -2) + cadence                  # 8 bars over P_V2
    # the sax's breakdown line: the hook call augmented, with a turn into the long B and a rising tail
    sax_line = s.motif('5:1/2 8:1/2 10:1 | 9:1/2. 8:1/4 7:1 | 8:1/2. 7:1/4 5:1/2 3:1/4 4:1/4 | 5:1 '
                       '| r:1/4 5:1/8 7:1/8 8:1/2 12!:1 | 11:1/2. 10:1/4 9:1/2 7:1/2 | 8:2')

    # ------------------------------------------------------------------ the band (preset) + extra voices
    b = bands.scifi(s)
    kit, bass, arp, seq, pad, bells, lead = b.drums, b.bass, b.arp, b.seq, b.pad, b.bells, b.lead
    hall, echo, shimmer = b.hall, b.echo, b.shimmer
    plate = s.bus('plate', 'bus/ir_plate', gain_db=7)               # 224XL plate (+7: the IR plates return ~8 dB low)
    shimmer.add_fx(fx.width(width=0.75))       # the octave halo is decorrelated: keeps pad-only intro / tail mono-safe
    kit.humanize(2, 4)
    bells.add_fx(fx.eq({'peak3.freq': 2800, 'peak3.gain': -4.5, 'peak3.q': 0.7}))   # they carry the verse tune
    bells.gain_db -= 2
    pad.add_fx(fx.eq({'peak1.freq': 1600, 'peak1.gain': -3.5, 'peak1.q': 0.8}),
               fx.eq({'peak1.freq': 180, 'peak1.gain': 0.0, 'peak1.q': 0.7,
                      'peak2.freq': 1400, 'peak2.gain': 0.0, 'peak2.q': 0.6}, name='room'))     # room for the bells / lead
    bass.add_fx(fx.eq({'low.freq': 40, 'low.gain': 0.5}), first=True)             # a deeper floor (sub)
    for e in bass.fx:                   # the preset's 36 Hz high-pass left 22-35 Hz ~4 dB under the reference
        if e.type == 'eq' and e.params.get('hp.freq') == 36.0:
            e.params['hp.freq'] = 29.0
    # the added voices push the 0.5-5 kHz band over the reference (Timecop1983): a broad dip on the master,
    # after the preset's own eq
    s.master.fx.insert(1, fx.eq({'peak1.freq': 700, 'peak1.gain': -1.5, 'peak1.q': 1.0,
                                 'peak2.freq': 1600, 'peak2.gain': -2.5, 'peak2.q': 0.5,
                                 'peak3.freq': 4000, 'peak3.gain': -1.5, 'peak3.q': 0.7}))
    # the final chorus stacks brass, lead, choir, orchestra, strings and sax in 0.45-2.8 kHz: a section-only dip
    s.master.fx.insert(2, fx.eq({'peak2.freq': 1300, 'peak2.gain': 0.0, 'peak2.q': 0.5}, name='final'))
    bells.humanize(timing_ms=3, vel=5)
    lead.humanize(timing_ms=4, vel=5)
    lead.gain_db += 1.5                                              # the hook sits on the bed, not in it
    lead.add_fx(fx.eq({'peak3.freq': 2200, 'peak3.gain': -2.0, 'peak3.q': 1.2}))    # ...without the 2 kHz edge

    choir = s.track('choir', 'sampled/fairlight_choir', gain_db=-2, sends={hall: -7, shimmer: -16},
                    fx=[tame(presence=-4, top=-4, hp=120).but(**{'peak2.freq': 1500, 'peak2.gain': -2.0,
                                                                 'peak2.q': 0.7}),
                        fx.chorus(mode='II', mix=0.5), fx.dimension(mode=1)])    # the CMI sample is near mono
    strings = s.track('strings', 'synthwave/jupiter_strings', gain_db=-5, sends={hall: -7}, fx=[tame()])
    orch = s.track('orch', 'sampled/strings', gain_db=-6, sends={hall: -7}, fx=[tame(presence=-4, top=-3, hp=60)])
    brass = s.track('brass_lead', patches.get('synthwave/brass_lead').with_mix(sends={'plate': None}), gain_db=3.5,
                    sends={hall: -8, plate: -16, echo: -13},
                    fx=[tame(presence=-4, top=-4, hp=180).but(**{'peak2.freq': 1800, 'peak2.gain': -2.5,
                                                                 'peak2.q': 0.8}),
                        fx.dimension(mode=1)])                        # a wide halo around the centred hook
    brass.humanize(timing_ms=4, vel=5)
    glass = s.track('glass', 'synthwave/arp_glass', gain_db=-9, pan=0.35, sends={echo: -12, hall: -12},
                    fx=[tame(presence=-3, top=-5, hp=400)])
    sax = s.track('sax_lead', 'sampled/tenor_sax', gain_db=0, sends={hall: -9, plate: -12, echo: -15})
    # the station's sonar (replaces the 'pew' laser zap: too video-game for a lush record): a pure FM sine ping
    # with a metallic strike that rings into the tape echo and the hall
    ping = s.track('ping', inst.va(osc1__wave='sine', osc2__wave='sine', osc2__semi=12, osc2__level=0.0, fm=0.4,
                                    mods=[vamod.env(a=0.001, d=0.12, id='strike') >> ('fm', 2.2)],
                                    filter__type='lp12', cutoff=7000, amp__attack=0.002, amp__decay=2.2,
                                    amp__sustain=0.0, amp__release=1.6, amp__velocity=0.6, hpf=300),
                    gain_db=-7, pan=-0.15, sends={echo: -3, hall: -7},
                    fx=[fx.eq({'peak3.freq': 3000, 'peak3.gain': -2.0, 'peak3.q': 0.7, 'lp.freq': 9000})])
    impact = s.track('impact', 'synthwave/impact', gain_db=-8)
    riser_t = s.track('riser', 'synthwave/noise_riser', gain_db=-9)
    fall = s.track('fall', 'synthwave/downlifter', gain_db=-12)
    cym = s.track('cym', inst.kit(CYM + 'Accoustic', extras=False, lazy=True,
                                  map={'crash': 'Crash 01.wav', 'crash2': 'Crash 03.wav',
                                       REV_LONG: CYM + 'Processed/Reversed 16.wav',
                                       REV_SHORT: CYM + 'Processed/Reversed 04.wav'}),
                  gain_db=-8, sends={hall: -12})

    # the station's voice: Windows TTS through the robot choir (cached in samples/speech/)
    vox = speech.words(['signal detected', 'signal lost'], voice='zira', rate=-3)
    voice = s.track('voice', vox.instrument())
    robot = s.track('robot', 'synthwave/vocoder_choir', gain_db=-1, sends={hall: -6, echo: -9, shimmer: -12})
    speech.vocode(robot, voice)

    def rev(note, peak_at, secs):
        """A reversed cymbal whose swell peaks exactly at `peak_at` (seconds through the tempo map)."""
        t_end = s.seconds(peak_at)
        lo, hi = peak_at - 16.0, peak_at
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if t_end - s.seconds(mid) > secs else (lo, mid)
        cym.note(note, hi, 1.0, vel=100)

    # ================================================================== INTRO: the signal
    arp.play(arp_line(P_INTRO, vel=78), intro)
    pad.play(pads(P_INTRO, vel=70), intro)
    for bb in (1, 3, 5, 7):                                          # sonar pings
        bells.note('B5', intro.bar(bb), 4, vel=62 if bb < 5 else 70)
    impact.note('E1', intro.start, 4, vel=100)
    bass.note('E1', intro.bar(4), 16, vel=84)
    choir.play(Clip([(0, 16, p, 72) for p in ('E3', 'B3', 'D4', 'G4')], length=16), intro.bar(4))
    # "signal detected": the robot sings it on an Em9 voicing
    voice.play(vox.clip({0: 'signal detected'}), intro.bar(4))
    robot.play(Clip([(0, 7, p, 90) for p in ('E3', 'G3', 'B3', 'D4', 'F#4')], length=8), intro.bar(4))
    ping.note('A5', intro.bar(2, beat=2.5), 0.25, vel=60)
    ping.note('E5', intro.bar(6, beat=1.5), 0.25, vel=56)

    # ================================================================== DRIFT (verse)
    arp.play(arp_line(P_V1), drift).play(arp_line(P_V2, pattern=PAT_B), drift.bar(8))
    pad.play(pads(P_V1 + ' ' + P_V2, vel=74), drift)
    bass.play(bassline(prog(P_V1), 'root', low='E1', vel=92).legato(), drift)
    bass.play(bassline(prog(P_V2), low='E1', pattern='r__r__r_', rate='1/8', vel=96).legato(), drift.bar(8))
    bells.play(signal.clip(octave=4, vel=84), drift)
    bells.play(signal2.clip(octave=4, vel=88), drift.bar(8))
    # pass 2: the pulse sequence and a soft 808 heartbeat come in
    seq.play(bassline(prog(P_V2), 'octave', rate='1/8', low='E2', vel=80, gate=0.5).crescendo(0.6, 1.0), drift.bar(8))
    beat_v = drums({'kick': 'X.........x.....', 'rim': '........x.......', 'hat': '..o...o...o...o.'}, vel=90)
    kit.play(drums({'hat': '..o...o...o...o.'}, vel=62).loop(16).crescendo(0.45, 0.9), drift.bar(4))  # a clock
    kit.loop(beat_v, drift.bar(8), bars=7)
    kit.play(drums({'kick': 'x.........x.....', 'rim': '........x...x.x.', 'hat': '..o...o...o.xxxx'},
                   vel=84), drift.bar(15))
    ping.note('B5', drift.bar(3, beat=2.5), 0.25, vel=62)           # answers after the bell phrases
    ping.note('F#5', drift.bar(11, beat=3), 0.25, vel=58)
    ping.note('A5', drift.bar(15, beat=0.5), 0.25, vel=66)

    # ================================================================== APPROACH (build over a B pedal)
    arp.play(arp_line(P_BUILD, pattern=PAT_B, vel=88, cut_last=1), approach)
    pad.play(drop(pads(P_BUILD, vel=78)), approach)
    choir.play(drop(pads(P_BUILD, reg=(52, 72), voices=4, vel=80)), approach)
    choir.automate('gainDb', ramp(approach.start, approach.bar(6), -14, 0)
                   + [(weightless.start, 0), (weightless.bar(1), -3),
                      (weightless.end - 0.5, -3)])
    pedal = grid('xxxxxxxx', 'B1', step='1/8', gate=0.85, vel=100).loop(32).crescendo(0.5, 1.0)
    bass.play(drop(pedal), approach)
    seq.play(drop(arpeggio(prog(P_BUILD), 'up', rate='1/16', octaves=2, register=(40, 64), vel=84)
                  .crescendo(0.4, 1.0)), approach.bar(4))
    bells.play(s.motif('5:1/4 8:1/4 10:1/2').clip(octave=4, vel=82), approach)      # hook preview
    bells.play(s.motif('9:1/4. 8:1/8 7:1/2').clip(octave=4, vel=78), approach.bar(4))
    kit.play(drums({'kick': 'x.........x.....', 'hat': 'x.o.x.o.x.o.x.o.'}, vel=70).loop(16), approach)
    kit.play(drop(drums({'hat': 'xooox.oox.oox.oo', 'kick': 'x.o.....x.o.....'}, vel=78).loop(16)
                  .crescendo(0.7, 1.0)), approach.bar(4), replace=True)
    kit.play(snare_roll(7, build=True, vel=(30, 116)), approach.bar(6))
    riser_t.note('E3', approach.bar(4), 15)
    rev(REV_LONG, approach.beat(-1), REV_LONG_S)
    ping.note('E5', approach.beat(-1), 0.5, vel=78)                 # the only sound in the drop

    # ================================================================== ORBIT (chorus 1)
    arp.play(arp_line(P_CHORUS + ' ' + P_CHORUS, vel=90), orbit)
    pad.play(pads(P_CHORUS, vel=80, times=2), orbit)
    choir.play(pads(P_CHORUS, reg=(52, 72), voices=4, vel=84), orbit.bar(8))
    bass.play(bassline(prog(P_CHORUS), 'root', rate='1/2', low='E1', vel=98).legato(), orbit)
    bass.play(bassline(prog(P_CHORUS), 'pulse', rate='1/8', low='E1', vel=98, gate=0.85), orbit.bar(8))
    seq.play(bassline(prog(P_CHORUS) * 2, 'octave', rate='1/8', low='E2', vel=78, gate=0.5), orbit)
    lead.play(hook.clip(octave=4, vel=94), orbit, times=2)
    bells.play(hook.clip(octave=4, vel=78), orbit)
    bells.play(hook.clip(octave=5, vel=62), orbit.bar(8))            # pass 2: the bells an octave up
    strings.play(art.legato(harmony.clip(octave=4, vel=86)), orbit.bar(8))   # a string line under the hook
    half = drums({'kick': 'X.....x.........', 'snare': '........X.......', 'hat': 'x.o.x.o.x.o.x.o.'}, vel=100)
    half2 = drums({'kick': 'X.....x...o.....', 'snare': '........X.......', 'clap': '........X.......',
                   'hat': 'xoo.xoo.xoo.xoo.', 'ohh': '..............x.'}, vel=100)
    kit.loop(half, orbit, bars=8).loop(half2, orbit.bar(8), bars=8)
    kit.play(tom_fill(2, vel=(84, 116)), orbit.bar(7, beat=2), replace=True)
    kit.play(tom_fill(2, vel=(90, 122)), orbit.bar(15, beat=2), replace=True)
    cym.note(49, orbit.start, 4, vel=112).note(57, orbit.bar(8), 4, vel=100)
    impact.note('E1', orbit.start, 4, vel=118)
    ping.note('B5', orbit.bar(3, beat=3.5), 0.25, vel=68)
    ping.note('E5', orbit.bar(11, beat=3.5), 0.25, vel=68)
    fall.note('E3', orbit.bar(15), 8, vel=90)                        # the floor falls away into the break

    # ================================================================== WEIGHTLESS (breakdown: the sax)
    arp.play(arp_line(P_BREAK, pattern=PAT_SPARSE, vel=78, octave=1), weightless)   # floats up an octave
    pad.play(pads(P_BREAK, vel=72), weightless)
    choir.play(pads(P_BREAK, reg=(52, 72), voices=4, vel=76), weightless)
    art.perform(sax, sax_line.clip(octave=3, vel=96), weightless, glide_leaps=7, humanize_ms=8, late_ms=10,
                vib={'depth': 20, 'rate': 5.0, 'delay': 0.4})
    bass.play(bassline(prog(P_BREAK), 'root', low='E1', vel=84).legato().slice(16, 32),
              weightless.bar(4))                                     # enters under the sax's second phrase
    bells.note('B5', weightless.bar(2), 4, vel=60).note('B5', weightless.bar(6), 4, vel=56)
    glass.play(arp_line(P_BREAK, rate=1.0, pattern=(4, None, 2, None), vel=66, octave=1), weightless)
    cym.note(57, weightless, 4, vel=84)

    # ================================================================== ASCENT (build, pivot to F# minor)
    arp.play(arp_line(P_ASCENT, rate=0.25, pattern=PAT_RISE, vel=84, cut_last=1), ascent)
    pad.play(drop(pads(P_ASCENT, vel=80)), ascent)
    choir.play(drop(pads(P_ASCENT, reg=(52, 72), voices=4, vel=86)), ascent)
    choir.automate('gainDb', [(ascent.start, 0), (ascent.start + 0.01, -10),
                              (ascent.beat(-1), 0), (horizon.start, -2.5)])
    bass.play(drop(bassline(prog(P_ASCENT), 'pulse', rate='1/16', low='E1', vel=92, gate=0.85)
                   .crescendo(0.55, 1.0)), ascent)
    seq.play(drop(arpeggio(prog(P_ASCENT), 'up', rate='1/16', octaves=2, register=(42, 66), vel=86)
                  .crescendo(0.5, 1.0)), ascent)
    kit.play(drop(drums({'hat': 'xoxoxoxoxoxoxoxo'}, vel=80).loop(16).crescendo(0.6, 1.0)), ascent)
    kit.play(drop(drums({'kick': 'x...x...x...x...'}, vel=100).loop(8).crescendo(0.6, 1.0)), ascent.bar(2))
    kit.play(snare_roll(14, build=True, vel=(28, 120)), ascent)
    kit.play(tom_fill(1, vel=(100, 124)), ascent.beat(-2), replace=True)
    kit.clear(ascent.beat(-1), ascent.end)
    riser_t.note('E3', ascent.start, 15)
    rev(REV_LONG, ascent.beat(-1), REV_LONG_S)
    ping.note('F#5', ascent.beat(-1), 0.5, vel=74)

    # ================================================================== HORIZON (final chorus, F# minor)
    arp.play(arp_line(P_CHORUS + ' ' + P_CHORUS, rate=0.25, vel=90, transpose=UP), horizon)
    glass.play(arp_line(P_CHORUS + ' ' + P_CHORUS, rate=0.5, pattern=PAT_MIRROR, vel=84, transpose=UP,
                        octave=1), horizon)
    pad.play(pads(P_CHORUS, UP, vel=84, times=2), horizon)
    choir.play(pads(P_CHORUS, UP, reg=(52, 72), voices=4, vel=88), horizon)
    choir.play(pads(P_CHORUS, UP, reg=(59, 79), voices=4, vel=88), horizon.bar(8))  # opens up
    orch.play(pads(P_CHORUS, UP, reg=(45, 76), voices=5, vel=92, times=2), horizon)
    strings.play(pads(P_CHORUS, UP, reg=(66, 86), voices=3, vel=82), horizon)
    strings.play(art.legato(harmony.clip(octave=4, vel=90)), horizon.bar(8), transpose=UP)
    bass.play(bassline(prog(P_CHORUS, UP) * 2, 'pulse', rate='1/8', low='E1', vel=100, gate=0.85), horizon)
    seq.play(bassline(prog(P_CHORUS, UP) * 2, 'octave', rate='1/16', low='E2', vel=74, gate=0.5), horizon)
    brass.play(hook.clip(octave=4, vel=100), horizon, times=2, transpose=UP)
    lead.play(hook.clip(octave=4, vel=84), horizon, times=2, transpose=UP)       # doubles the brass: body + chorus
    bells.play(hook.clip(octave=5, vel=58), horizon.bar(8), transpose=UP)      # pass 2: the bells an octave up
    art.perform(sax, harmony.clip(octave=3, vel=92), horizon.bar(8), glide_leaps=None, humanize_ms=7,
                late_ms=8, vib={'depth': 16, 'rate': 5.2}, seed=3)     # the sax answers under the brass
    kit.loop(drums({'snare': '....X.......X...', 'clap': '....x.......x...',
                    'hat': 'x.o.x.o.x.o.x.o.', 'ohh': '..............x.'}, vel=104), horizon, bars=8)
    kit.loop(drums({'snare': '....X.......X...', 'clap': '....x.......x...',
                    'hat': 'xoxoxoxoxoxoxoxo', 'ohh': '..............x.', 'tamb': '....x.......x...'}, vel=106),
             horizon.bar(8), bars=8)
    kit.loop(drums({'kick': 'x.....x.x.......'}, vel=88), horizon, bars=16)
    for bb in (3, 11):
        kit.play(tom_fill(1, vel=(96, 118)), horizon.bar(bb, beat=3), replace=True)
    for bb in (7, 15):
        kit.play(tom_fill(2, vel=(96, 124)), horizon.bar(bb, beat=2), replace=True)
    cym.note(49, horizon.start, 4, vel=118).note(57, horizon.bar(8), 4, vel=108)
    impact.note('F#1', horizon.start, 4, vel=122).note('F#1', horizon.bar(8), 4, vel=98)
    for bb, p in ((7, 'C#6'), (15, 'F#5')):
        ping.note(p, horizon.bar(bb, beat=1.5), 0.25, vel=72)       # one ping, the echo repeats it

    # ================================================================== OUTRO: signal lost
    arp.play(arp_line('F#m9:2 Dmaj7#11:2 Bm9:2', vel=80), outro)
    arp.note('F#3', outro.bar(6), 1.0, vel=76)                       # the arp's last note, into the echoes
    pad.play(pads(P_OUTRO, vel=72), outro)
    choir.play(Clip([(0, 8, p, 70) for p in ('C#4', 'E4', 'A4', 'C#5')], length=8), outro.bar(6))
    orch.play(Clip([(0, 8, p, 70) for p in ('F#2', 'C#3', 'A3', 'E4', 'G#4')], length=8), outro.bar(6))
    bass.play(bassline(prog(P_OUTRO), 'root', low='E1', vel=86).legato(), outro)
    bells.play(cell.clip(octave=4, vel=78), outro, transpose=UP)     # the signal, one last time
    bells.note('C#6', outro.bar(6), 8, vel=60).note('F#5', outro.bar(6), 8, vel=54)
    voice.play(vox.clip({0: 'signal lost'}), outro.bar(2))
    robot.play(Clip([(0, 7, p, 84) for p in ('D3', 'F#3', 'A3', 'C#4', 'G#4')], length=8), outro.bar(2))
    cym.note(57, outro, 4, vel=90)
    fall.note('F#3', outro.start, 8, vel=96)
    impact.note('F#1', outro.bar(6), 4, vel=78)
    rev(REV_SHORT, outro.bar(6), REV_SHORT_S)
    ping.note('C#6', outro.bar(4, beat=1.5), 0.25, vel=52)
    arp.automate('fx.delay.feedback', [(outro.start, 0.4), (outro.bar(6), 0.6)])   # echoes trail into space
    arp.automate('fx.delay.mix', [(outro.start, 0.22), (outro.bar(6), 0.4)])

    # ================================================================== automation & mix moves
    # the main voice opens over minutes, dips for the breakdown, blooms for the final, closes at the end
    arp.automate('instrument.cutoff', [
        (intro.start, 420), (drift.start, 560, 'exp'), (approach.start, 850, 'exp'),
        (approach.beat(-1), 1600, 'exp'), (orbit.end, 2000, 'exp'), (weightless.bar(2), 750, 'smooth'),
        (weightless.end, 900, 'exp'), (ascent.beat(-1), 2800, 'exp'), (horizon.end, 3400, 'exp'),
        (outro.bar(6), 380, 'exp')])
    # 'gainDb' lanes are dB on each track's gain_db
    arp.automate('gainDb', [(intro.start, -16), (intro.bar(2), 0, 'smooth'), (orbit.end, 0),
                            (weightless.bar(1), -2), (weightless.end, -2), (ascent.start, 0)])
    bass.automate('gainDb', [(intro.start, -3), (drift.bar(8), -3), (approach.start, -1, 'smooth'),
                             (approach.beat(-1), 0), (weightless.start, 0), (weightless.bar(1), -4),
                             (ascent.start, -1), (ascent.end, 0), (outro.start, 0), (outro.bar(2), -4)])
    pad.automate('fx.room.peak2.gain', [(drift.start - 2, 0.0), (drift.start, -5.0, 'smooth'),
                                        (drift.end - 1, -5.0), (drift.end, 0.0, 'smooth')])
    # the pad fades in with the arp
    pad.automate('gainDb', [(intro.start, -30), (intro.bar(3), 0, 'smooth'), (ascent.end - 0.5, 0),

                            (horizon.start, -1), (horizon.end - 1, -1), (outro.start, 0, 'smooth')])
    # the bass enters the breakdown under the sax's second phrase: the pad gives up its low end there
    pad.automate('fx.room.peak1.gain', [(weightless.bar(4) - 1, 0.0), (weightless.bar(4), -5.0, 'smooth'),
                                        (weightless.end - 0.5, -5.0), (weightless.end, 0.0, 'smooth')])
    pad.automate('fx.width.width', [(intro.start, 0.45), (intro.bar(3), 0.45), (intro.bar(5), 0.8, 'smooth')])  # opens with the bass
    for when in (approach, ascent):
        riser_t.automate('instrument.cutoff', riser(when.beat(-1), length=15, lo=300, hi=11000))
        riser_t.automate('instrument.hpf', riser(when.beat(-1), length=15, lo=20, hi=1200))
    # shimmer blooms in the intro, the breakdown and the ending; stays low under the full sections
    pad.automate('send.shimmer', hold(intro.start, drift.bar(8), -8), hold(drift.bar(8), weightless.start, -16),
                 hold(weightless.start, ascent.start, -7), hold(ascent.start, outro.start, -16),
                 hold(outro.start, outro.end, -6))
    sax.automate('gainDb', [(weightless.start, 3), (weightless.end, 3), (weightless.end + 1, 2)])
    sax.automate('pan', [(weightless.start, 0.0), (horizon.start, 0.0), (horizon.start + 0.01, -0.3)])  # beside the brass
    sax.automate('send.echo', [(weightless.start, -15), (weightless.bar(6), -15), (weightless.bar(6) + 0.5, -7),
                               (weightless.end, -7), (weightless.end + 0.5, -15)])  # a delay throw on the long B

    # dry drops: the returns are cut for the silent beat before each chorus (the ping's echo stays)
    for bus in (hall, shimmer):
        bus.automate('gainDb', [(approach.beat(-1), 0), (approach.beat(-0.75), -24), (orbit.start - 0.02, -24),
                                (orbit.start, 0), (ascent.beat(-1), 0), (ascent.beat(-0.75), -24),
                                (horizon.start - 0.02, -24), (horizon.start, 0)])
    riser_t.automate('gainDb', [(approach.beat(-1), 0), (approach.beat(-0.9), -60),
                                (ascent.start, -60), (ascent.start + 0.01, 0),
                                (ascent.beat(-1), 0), (ascent.beat(-0.9), -60)])
    limiter = s.master.fx[-1]
    assert limiter.type == 'limiter'
    limiter.params['gain'] = 2.9                                    # +1.4 dB: the choruses sit at the reference
    end = outro.bar(6)
    s.master.automate('fx.final.peak2.gain', [(horizon.start - 1, 0.0), (horizon.start - 0.5, -3.0),
                                              (horizon.end - 1, -3.0), (horizon.end, 0.0, 'smooth')])
    lead.automate('gainDb', [(horizon.start - 1, 0), (horizon.start - 0.5, -2)])  # the brass leads, the lead doubles

    s.master.automate('gainDb', [(end + 1, 0), (outro.end, -9, 'smooth'), (outro.end + 8, -16)])
    # a bit wider than the preset's 1.5; narrower while the pad is alone (intro) and into the tail: mono-safe
    s.master.automate('fx.width.width', [(0, 1.15), (intro.bar(4), 1.65, 'smooth'), (end, 1.65), (outro.end, 1.1, 'smooth')])
    return s
