"""Children of Neon - synthwave / dream-trance reinvention, a tribute to Robert Miles' "Children" (1995).

Sub-style: dream trance x retrowave, 122 BPM, F# minor. Only the MOOD and the production language are borrowed
(a long atmospheric intro with wind and a lone piano, a plaintive piano riff as the central hook, huge pads, the
breakdown -> anticipation -> four-on-the-floor lift); every melody, riff and progression here is original.

The hook: one rhythmic cell (dotted 8th, dotted 8th, quarter, 8th, quarter) sung four times per phrase - up
(C#-E-F#-E-C#), reaching higher (D-E-F#-A-F#), falling back (E-C#-A-B-C#) and left hanging on B over E, so the loop
never closes. The answer phrase turns and leans home (B-A-G#); the second drop climbs to C#6, the final lift goes a
whole step up (G# minor) and only the very last phrase of the song finally closes the loop on F#.

Sound: the retrowave band preset (80s pop kit with a TR-909 kick and 909 open hats, Linn clap, keyed gated snare,
octave bass, Juno pad, Fairlight choir, 224XL hall + plate, dotted-8th echo, master chain) plus a real Salamander
grand piano on the sustain pedal, the hook from verse B on played high (C#5-C#7) in octaves on the bright melody
piano (sampled/piano_lead) with the supersaw only sustaining under it, a real string section and violin descant, a dream pad with a
shimmer halo, glassy and plucked arps, a vocoder choir that sings "children of neon", wind and rain.

Build: python -m agentsound build songs/children-of-neon
Compare: python -m agentsound compare songs/children-of-neon --ref "<refs>/The Midnight - Sunset (Official Audio)
[URma_gu1aNE].opus"
"""
from agentsound import *
from agentsound import bands, speech
from agentsound import articulation as art
from agentsound.humanize import phrase_dynamics

BPM = 122
ANALYSIS = {'profile': 'synthwave'}                    # = the retrowave preset's profile
METADATA = {'title': 'Children of Neon', 'artist': 'AgentSound', 'album': 'Neon Archive', 'genre': 'Synthwave',
            'year': 2026, 'track': 6,
            'comment': "Dream-trance / synthwave tribute to Robert Miles' Children - original melody and harmony"}
COVER = {'style': 'dreamwave', 'title': 'CHILDREN OF NEON', 'subtitle': 'AgentSound', 'seed': 21}

POP = 'samples/sampleradar-80s-pop-drums/Drum Kits/Kit A'
T909 = 'samples/hyperreal-tr909'
LINN = 'samples/hyperreal-linndrum'


def silence(tracks, start, end):
    """Silence tracks in [start, end): notes ringing into it are cut, notes starting inside it removed."""
    for t in tracks:
        a = max(0.0, start - 16)
        keep = t.clip(a, start).slice(0, start - a)
        t.clear(a, end)
        if len(keep):
            t.play(keep, a)


def arc(node, base, marks, target='gainDb'):
    """A lane from (position, offset[, curve]) marks; without a curve the value jumps (step)."""
    pts = []
    for m in marks:
        at = m[0].start if isinstance(m[0], Section) else m[0]
        pts.append((at, base + m[1], m[2]) if len(m) > 2 else (at, base + m[1], 'step'))
    pts[0] = pts[0][:2]
    node.automate(target, pts)


def tweak(node, ftype, nth=0, **params):
    """Adjust an insert effect the band preset put on a track / the master (its n-th effect of that type)."""
    found = [f for f in node.fx if f.type == ftype]
    found[nth].params.update({k.replace('__', '.'): v for k, v in params.items()})


def breathe(track, chords, at, lo=0.84, hi=1.0):
    """A string section that breathes instead of re-triggering like a keyboard: at every chord change the bow eases
    (expression dips a little), then the chord swells into its middle and settles (CC11 on the sampler)."""
    a0 = at.start if isinstance(at, Section) else at
    starts = sorted({round(n.start, 4) for n in chords})
    ends = starts[1:] + [chords.length]
    pts = []
    for t, e in zip(starts, ends):
        d = e - t
        pts += [(a0 + t, lo, 'smooth'), (a0 + t + 0.45 * d, hi, 'smooth'), (a0 + e - min(1.0, 0.25 * d), 0.93, 'smooth')]
    pts[0] = (pts[0][0], pts[0][1])
    track.automate('instrument.expression', pts)


def build() -> Song:
    s = Song('Children of Neon', tempo=BPM, key='F# minor', seed=21, tail=9.0)
    key = s.key

    # ------------------------------------------------------------------ form: 120 bars, ~4:00 + the ritardando tail
    intro = s.section('intro', 16)       # wind, rain, the robot whisper, the lone piano cell fades in
    theme = s.section('theme', 8)        # the piano riff, both hands, no beat yet
    verse = s.section('verse', 16)       # four on the floor, octave bass (tonic pedal, then released)
    build_ = s.section('build', 8)       # repeated piano chords, strings climb, roll + riser, one-beat breath
    drop1 = s.section('drop1', 16)       # the lift: supersaw doubles the riff, rolling bass
    brk = s.section('breakdown', 8)      # beat gone: the riff at half speed over new colours, the robot choir
    rise = s.section('rise', 8)          # anticipation: riff at tempo, filtered kick, strings swell
    drop2 = s.section('drop2', 16)       # bigger: the climb to C#6, choir, real strings, violin descant, thirds
    lift = s.section('lift', 8)          # the last chorus a whole step up (G# minor): everything
    outro = s.section('outro', 16)       # back to F# minor, the beat strips away, the loop finally closes

    # ------------------------------------------------------------------ harmony
    P = s.prog('i VI III VII')                              # F#m D A E
    TURN = s.prog('Bm D Esus4 E')                           # iv VI VIIsus4 VII: pulls back to i
    P_intro = s.prog('F#m9:2 Dmaj7:2 Aadd9:2 Esus4 E') * 2  # the loop at half speed, open colours
    P_theme = P * 2
    P_build = s.prog('Bm D E C#m') + TURN                   # iv VI VII v: the v7 colour darkens the climb
    P_drop = P * 3 + TURN
    P_break = s.prog('Dmaj7:2 E6:2 C#m7:2 F#m9:2')          # new colours: VImaj7 VII6 v7 i9
    P_rise = P + TURN
    P_lift = (P + TURN).transpose(2)                        # G#m E B F#: a whole step up
    P_outro = P * 2 + s.prog('Dmaj7:2 Esus4 E F#m9:4')

    # ------------------------------------------------------------------ melody (degrees of F# minor, 8 = F#5)
    H = {
        'a': '5:1/8. 7:1/8. 8:1/4 7:1/8 5:1/4',       # C#5 E5 F#5 E5 C#5   the cell
        'b': '6:1/8. 7:1/8. 8:1/4 10:1/8 8:1/4',      # D5 E5 F#5 A5 F#5    reaching up
        'c': '7:1/8. 5:1/8. 3:1/4 4:1/8 5:1/4',       # E5 C#5 A4 B4 C#5    falling back
        'd': '4:1/8. 5:1/8. 4:1/2 r:1/8',             # B4 C#5 B4           the open question
        'c2': '7:1/8. 8:1/8. 7:1/4 5:1/8 3:1/4',      # E5 F#5 E5 C#5 A4    the turn
        'd2': '4:1/8. 3:1/8. 2:1/4. 3:1/8 4:1/8',     # B4 A4 G#4 . A4 B4   leaning home
        'bh': '6:1/8. 8:1/8. 10:1/4 12:1/8 10:1/4',   # D5 F#5 A5 C#6 A5    the climax (drop 2)
        'end': '4:1/8. 3:1/8. 2:1/2 r:1/8',           # B4 A4 G#4 ...       (F#4 lands on the last chord)
    }

    def mel(*names):
        return s.motif(' '.join(H[n] for n in names))

    phA = mel('a', 'b', 'c', 'd')
    phB = mel('a', 'b', 'c2', 'd2')
    hook = phA + phB                                   # 8 bars
    hook_hi = phA + mel('a', 'bh', 'c2', 'd2')
    slow = mel('a', 'c', 'a', 'd2').stretch(2)         # breakdown: augmentation over the new chords
    # the verse's own song: long, calm notes over the kick (so the hook's return in bar 9 is a lift), rising to A5
    # and leaning back into the hook's C#5
    verse_mel = s.motif('5:1/2. 4:1/8 3:1/8 | 3:1/4 6:1/2 5:1/4 | 5:1/2 3:1/4 2:1/4 | 2:1/2. r:1/4 '
                        '| 5:1/2. 7:1/8 8:1/8 | 8:1/4 10:1/2 8:1/4 | 7:1/2 5:1/4 7:1/4 | 5:1/4 4:1/4 2:1/4 4:1/4')

    def rh(m, vel=100):
        """Right hand / lead line, phrased like a player: an arch over every phrase, its top note leaned into, the
        bar downbeats a touch heavier (not a keyboard's constant velocity)."""
        c = m.clip(octave=4, vel=vel, gate=0.95)
        return phrase_dynamics(c, gap='1/8', arch=0.16, peak=1.06, end=0.9).accent(every=4, amount=1.06)

    # the hook for the high melody piano (a piano decays: no held synth notes). The hanging B is re-struck with a
    # little A-B turn instead of a held half note, the G# leaning home is repeated - the loop still never closes.
    HP = dict(H, d='4:1/8. 5:1/8. 4:1/4 4:1/8 3:1/16 4:1/16 r:1/8',       # B4 C#5 B4 B4 A4-B4
              d2='4:1/8. 3:1/8. 2:1/4 2:1/8 3:1/8 4:1/8')                 # B4 A4 G#4 G#4 A4 B4

    def pmel(*names):
        return s.motif(' '.join(HP[n] for n in names))

    p_hook = pmel('a', 'b', 'c', 'd', 'a', 'b', 'c2', 'd2')
    p_hook_hi = pmel('a', 'b', 'c', 'd', 'a', 'bh', 'c2', 'd2')
    p_phB = pmel('a', 'b', 'c2', 'd2')

    def lead(m, vel=104, octave=5, dbl=0.72):
        """The hook on the high melody piano (C#5-C#7): a pianist's right hand in octaves - the melody on top, the
        octave below softer (~70 %), the two keys a few ms apart. Played, not triggered: the bar downbeats leaned
        into, 8th passing notes lighter, grace / 16th pickups light, an arch over every 4-bar phrase (crescendo into
        its peak note, diminuendo at its end); the top softly limited so the accents never all hit the same wall."""
        c = m.clip(octave=octave, vel=vel, gate=0.95)

        def role(n):
            f, beat = 1.0, n.start % 4
            if beat < 1e-3:
                f *= 1.08                          # the downbeat
            elif abs(beat - 2) < 1e-3:
                f *= 1.03                          # beat 3
            if n.dur <= 0.3:
                f *= 0.7                           # grace notes / 16th pickups
            elif n.dur <= 0.55:
                f *= 0.86                          # 8th passing notes
            return n._replace(vel=max(1, min(127, round(n.vel * f))))

        c = phrase_dynamics(c.map(role), gap='1/8', arch=0.24, peak=1.1, end=0.8)
        c = c.map(lambda n: n._replace(vel=round(n.vel if n.vel <= 104 else min(118, 104 + (n.vel - 104) * 0.5))))
        return c.octave_double(-12, vel=dbl).strum(ms=7, direction='up', bpm=BPM)

    def lh(prog, vel=66, rate='1/8', pattern=(0, 1, 2, 1, 3, 1, 2, 1)):
        """Left hand: circling broken chords (voice-led, D3-E4)."""
        held = prog.block(register=(50, 64), voices=3)
        return (held.arpeggiate(rate=rate, pattern=list(pattern), vel=vel, gate=0.95)
                .vel_pattern([1.1, 0.86, 0.96, 0.86], grid=rate))      # the beat under the fingers, lighter between

    # ------------------------------------------------------------------ the band (retrowave preset) + extra players
    kit_sound = inst.kit(POP, map={'kick': f'{T909}/BT3AADA.WAV', 'kick2': 'Kick01', 'clap': f'{LINN}/clap.wav',
                                   'open_hat': f'{T909}/HHOD4.WAV', 'crash': f'{T909}/CSHD8.WAV',
                                   'ride': f'{T909}/RIDED6.WAV', 'tamb': f'{LINN}/tamb.wav',
                                   'shaker': f'{LINN}/cabasa.wav'},
                         gains={'hats': -15, 'shaker': -17, 'clap': 1, 'cymbals': -6, 'tamb': -8, 'snare': 6.5,
                                'kick': 2.5},
                         lazy=True, level=-3.0)
    bass_sound = patches.get('synthwave/octave_bass').but(**{'sub.level': 0.25, 'amp.release': 0.2,
                                                             'amp.attack': 0.004})
    b = bands.retrowave(s, lead='supersaw', without=('keys', 'brass'), sounds={'drums': kit_sound, 'bass': bass_sound})
    kit, bass, pad, choir, saw = b.drums, b.bass, b.pad, b.choir, b.lead
    # mix moves on top of the preset (measured against The Midnight 'Sunset', loudness-matched):
    tweak(kit, 'compressor', attack=25)                       # let the kick and snare transients through
    tweak(kit, 'saturator', drive=2.5)                        # the preset's tape drive 5 rounded every hit (punch 12 vs 19)
    kit.add_fx(fx.eq({'peak1.freq': 185, 'peak1.gain': -2, 'peak1.q': 1.4,     # 142-224 Hz read +2 dB (kit 29 %)
                      'high.freq': 8000, 'high.gain': -6.5}))  # the 909 hats: +2 dB air (11-18 kHz) vs Sunset
    tweak(bass, 'ducker', depth=10)                           # the kick punches through the bass wall
    tweak(pad, 'ducker', depth=7)                             # ... and the beds breathe with it (trance pump)
    tweak(choir, 'ducker', depth=6)
    bass.add_fx(fx.eq({'low.freq': 46, 'low.gain': -5.5, 'peak1.freq': 68, 'peak1.gain': 3.5, 'peak1.q': 1.2,
                       'peak2.freq': 165, 'peak2.gain': -5, 'peak2.q': 1.0,
                       'peak3.freq': 210, 'peak3.gain': -3.5, 'peak3.q': 1.2}))
    tweak(s.master, 'eq', high__gain=4.0)                     # the preset's +5.5 dB air shelf read +3 dB over the ref
    tweak(s.master, 'exciter', amount=0.45)
    tweak(s.master, 'eq', peak3__gain=0.8)                    # presence read +4 dB vs the synthwave profile (harsh)
    saw.instrument.params['amp.velocity'] = 0.7   # was 0.3: every supersaw note came out equally loud
    saw.gain_db -= 10.5       # the high piano carries the hook; the supersaw only sustains underneath (-9 dB)
    saw.add_fx(fx.eq({'peak1.freq': 520, 'peak1.gain': -2, 'peak1.q': 1.2, 'peak2.freq': 800, 'peak2.gain': -2,
                      'peak2.q': 1.0, 'peak3.freq': 3300, 'peak3.gain': -2.5,
                       'peak3.q': 1.0, 'high.freq': 8000, 'high.gain': -3.5}))
    pad.add_fx(fx.eq({'peak1.freq': 480, 'peak1.gain': -2.5, 'peak1.q': 1.0,
                      'peak2.freq': 1300, 'peak2.gain': -2.5, 'peak2.q': 0.9}))    # room for the piano
    choir.gain_db += 2
    hall, plate, echo = b.buses['hall'], b.buses['plate'], b.buses['echo']
    shimmer = s.bus('shimmer', 'bus/shimmer')
    b.buses['gated'].add_fx(fx.width(width=0.6))              # the gated burst read correlation -0.17
    tweak(hall, 'width', width=0.85)                          # the hall carries the width the narrowed piano gave up

    piano = s.track('piano', patches.get('sampled/grand_piano').but(width=0.55, pan=-0.3),  # AB pair narrowed and
                    fx=[fx.eq({'hp.freq': 70, 'hp.slope': 12, 'peak1.freq': 300, 'peak1.gain': -2.5, 'peak1.q': 0.8,
                               'peak2.freq': 580, 'peak2.gain': -3.5, 'peak2.q': 1.1,
                               'peak3.freq': 2400, 'peak3.gain': 2.0, 'peak3.q': 0.8}),
                        fx.compressor(threshold=-24, ratio=3, attack=6, release=140, knee=6, makeup=3),
                        fx.chorus(mode='I', mix=0.08)],
                    gain_db=3, sends={hall: -9, echo: -18, plate: -20, shimmer: -30}).humanize(4, 5)
    # (width 0.5 / chorus 0.08: at 0.7 the AB pair read correlation -0.34..+0.1 in the solo-piano theme - a phone
    # speaker sums it to mono)
    # (pan -0.3: the recorded AB image put the right hand's melody right of centre, the intro leaned 1.3 dB right)
    # the hook's voice from verse B on: the high melody piano (Salamander, mono centre, high-passed, presence + air,
    # compressed, chorused) - the retrowave preset's lead='piano' chain; the grand keeps the left hand and the solos
    # (-3.5 dB and -1.5 dB at 1.1 kHz: at the preset's -1 dB it read 4 dB over the old supersaw, mids +4.1 dB)
    # (dimension width 0.8 -> 1.15: with the wide supersaw pulled back the mix read width 54 vs 59 %)
    # (compressor -13 dB 3:1 -> -10 dB 2:1: the patch's 4-5 dB off every attack flattened the accents)
    # layered: the same hook piano + a DX glass halo an octave up (-10 dB) + a warm pad swelling in under held notes
    keys = s.track('keys_lead', patches.get('layered/piano_glass_lead').but(**{
                       'layers.piano.fx.dimension.width': 1.15, 'layers.piano.fx.compressor.threshold': -10,
                       'layers.piano.fx.compressor.ratio': 2.0}), gain_db=-1.5,
                   fx=[fx.eq({'peak2.freq': 1100, 'peak2.gain': -2.0, 'peak2.q': 0.9, 'peak3.freq': 3300,
                              'peak3.gain': -2.5, 'peak3.q': 1.0})],
                   sends={plate: -14, hall: -12, echo: -14})
    strings = s.track('strings', 'sampled/strings', gain_db=-3, sends={hall: -8},
                      fx=[fx.eq({'peak1.freq': 480, 'peak1.gain': -2.5, 'peak1.q': 1.0})])
    violins = s.track('violins', 'sampled/violins', gain_db=-4, pan=0.15, sends={hall: -7, echo: -20})
    solo = s.track('solo_violin', patches.get('sampled/solo_violin').but(width=0.45, pan=0.4), gain_db=8,
                   sends={hall: -6, echo: -16})    # the VSCO pair read correlation -0.13 and sat left
    dream = s.track('dreampad', 'synthwave/dream_pad', gain_db=-3,
                    fx=[fx.eq({'peak1.freq': 470, 'peak1.gain': -4.5, 'peak1.q': 0.7,
                               'peak2.freq': 750, 'peak2.gain': -3, 'peak2.q': 0.9}), fx.width(width=0.8)],
                    sends={hall: -6, shimmer: -15})
    pluck = s.track('pluck', 'synthwave/arp_pluck', gain_db=-6, pan=-0.3,
                    sends={echo: -10, hall: -14})
    glass = s.track('glass', 'synthwave/arp_glass', gain_db=-3, pan=0.35, sends={echo: -12, hall: -12})

    # the robot choir: Windows speech (cached in samples/speech/) through the vocoder
    vox = speech.words(['children of neon', 'children', 'neon'], voice='zira', rate=-3)
    voice = s.track('voice', vox.instrument())
    robot = s.track('robot', 'synthwave/vocoder_choir', gain_db=-4, fx=[fx.width(width=1.2)],
                    sends={hall: -5, shimmer: -14})

    wind = s.track('wind', inst.va({'osc1.level': 0, 'noise.level': 1, 'noise.color': 'pink', 'noise.stereo': 0.3,
                                    'filter.type': 'bp12', 'cutoff': 700, 'resonance': 0.45,
                                    'filter.keytrack': 0, 'filter.env': 0, 'filter.velocity': 0,
                                    'amp.attack': 4, 'amp.sustain': 1, 'amp.release': 6, 'amp.velocity': 0,
                                    'drift.cutoff': 3}),
                   fx=[fx.chorus(mode='II', mix=0.25)], gain_db=-10, sends={hall: -8})
    rain = s.track('rain', inst.va({'osc1.level': 0, 'noise.level': 1, 'noise.color': 'white', 'noise.stereo': 0.3,
                                    'filter.type': 'lp12', 'cutoff': 9000, 'hpf': 2500,
                                    'filter.keytrack': 0, 'filter.env': 0, 'filter.velocity': 0,
                                    'amp.attack': 3, 'amp.sustain': 1, 'amp.release': 5, 'amp.velocity': 0}),
                   gain_db=-24, sends={hall: -10})
    riser_t = s.track('riser', 'synthwave/noise_riser', gain_db=-10)
    impact = s.track('impact', 'synthwave/impact', gain_db=1)
    down = s.track('down', 'synthwave/downlifter', gain_db=-9)

    # ------------------------------------------------------------------ atmosphere
    for a, e in ((intro.start, theme.bar(4)), (brk.start, rise.bar(4)), (outro.bar(6), outro.end)):
        wind.note('F#3', a, e - a, 100)
        rain.note('F#3', a, e - a, 100)
    wind.modulate('instrument.cutoff', sample_hold('1 bar', smooth=1, min=300, max=2000, curve='exp'))
    wind.modulate('gainDb', sample_hold('2 bars', smooth=1, depth=5))
    rain.modulate('gainDb', sample_hold('1/16', smooth=0.5, depth=4))

    # ------------------------------------------------------------------ piano: the heart
    # intro: the lone cell, far away, answered by its own echo; then the whole question phrase
    for i, bar in enumerate((4, 6, 8, 10)):
        piano.play(rh(mel('a'), vel=58 + 8 * i), intro.bar(bar))
    piano.play(rh(phA, vel=86), intro.bar(12))
    # theme: both hands, alone
    piano.play(rh(hook, vel=96), theme).play(lh(P_theme, vel=58), theme)
    # verse: a new, calmer melody first; then the riff returns with a high octave sparkle and a 16th left hand
    # (verse B: the riff returns an octave up on the high melody piano, in octaves)
    piano.play(rh(verse_mel, vel=90), verse)
    keys.play(lead(p_hook, vel=88, dbl=0.68), verse.bar(8))   # the first statement, softer
    piano.play(lh(P * 2, vel=56), verse)
    piano.play(lh(P * 2, vel=60, rate='1/16', pattern=(0, 1, 2, 3)), verse.bar(8))
    # build: the melody rests - repeated 8th chords swelling (the pianist leaning in), a high answer at the top
    piano.play(P_build.block(rhythm='xxxxxxxx', step='1/8', register=(54, 74), voices=3, vel=96)
               .crescendo(0.45, 0.9), build_)
    # drops: the riff on the high melody piano in octaves (the grand keeps the left hand, the supersaw sustains
    # underneath); the second half leans in harder
    keys.play(lead(p_hook, vel=96), drop1).play(lead(p_hook, vel=104, dbl=0.75), drop1.bar(8))
    piano.play(lh(P_drop, vel=64), drop1)
    keys.play(lead(p_hook_hi, vel=100), drop2).play(lead(p_hook_hi, vel=108, dbl=0.75), drop2.bar(8))
    piano.play(lh(P_drop, vel=66), drop2)
    # breakdown: augmentation over the new chords, slow left hand
    piano.play(rh(slow, vel=92), brk)
    piano.play(lh(P_break, vel=52, rate='1/4', pattern=(0, 1, 2, 3)), brk)
    # rise: the riff at tempo again, in octaves for the last four bars
    piano.play(rh(phA, vel=96), rise)
    keys.play(lead(p_phB, vel=96), rise.bar(4))
    piano.play(lh(P_rise, vel=60), rise)
    # lift: a whole step up, octaves (the top reaches D#7 once, at the climax)
    keys.play(lead(p_hook_hi, vel=114, dbl=0.78).transpose(2), lift)   # the strongest
    piano.play(lh(P_lift, vel=68), lift)
    # outro: the riff once more, softly; then the lone cell, and at last the phrase closes on F#
    piano.play(rh(hook, vel=90), outro).play(lh(P * 2, vel=54), outro)
    piano.play(rh(mel('a'), vel=80), outro.bar(8)).play(rh(mel('a'), vel=74), outro.bar(10))
    piano.play(rh(mel('end'), vel=70), outro.bar(11))
    last = Clip([(0, 16, p, v) for p, v in (('F#2', 64), ('C#3', 58), ('A3', 56), ('E4', 56), ('G#4', 58),
                                            ('F#4', 72))], length=16).strum(ms=45, bpm=100)
    piano.play(last, outro.bar(12))

    # sustain pedal: down just after every chord change (lifted at the change), off in the build's repeated chords
    ped = []

    def pedal(prog, at):
        t = at.start if isinstance(at, Section) else at
        for _, bars in prog.items:
            ped.extend([(t, 0, 'step'), (t + 0.12, 1, 'step')])
            t += bars * 4
        ped.append((t - 0.06, 0, 'step'))

    pedal(P_intro, intro)
    pedal(P_theme, theme)
    pedal(P * 4, verse)
    pedal(P_drop, drop1)
    pedal(P_break, brk)
    pedal(P_rise, rise)
    pedal(P_drop, drop2)
    pedal(P_lift, lift)
    pedal(P * 2 + s.prog('Dmaj7:2 Esus4 E'), outro)
    ped.extend([(outro.bar(12), 0, 'step'), (outro.bar(12) + 0.1, 1, 'step')])
    ped[0] = ped[0][:2]
    piano.automate('instrument.pedal', ped)
    # the melody piano sings legato on the pedal too: down after each chord change, lifted at the change
    ped = [(0, 0)]
    pedal((P * 2), verse.bar(8))
    pedal(P_drop, drop1)
    pedal(TURN, rise.bar(4))
    pedal(P_drop, drop2)
    pedal(P_lift, lift)
    keys.automate('instrument.pedal', ped)

    # ------------------------------------------------------------------ supersaw lead + harmony
    saw.play(rh(hook, vel=100), drop1).play(rh(hook, vel=104), drop1.bar(8))
    saw.play(rh(phB, vel=92), rise.bar(4))
    saw.play(rh(hook_hi, vel=102), drop2)
    hi2 = rh(hook_hi, vel=106)
    saw.play(hi2 | hi2.transpose_scale(-2, key).velocity(0.75), drop2.bar(8))     # diatonic thirds below
    up = rh(hook_hi, vel=108).transpose(2)
    saw.play(up | up.transpose_scale(-2, Key('G# minor')).velocity(0.75), lift)
    saw.automate('send.echo', [(0, -12), (drop1.bar(15), -12), (drop1.bar(15, 2), -4, 'step'), (brk.start, -12, 'step'),
                               (lift.bar(7), -12), (lift.bar(7, 2), -4, 'step'), (outro.start, -12, 'step')])

    # ------------------------------------------------------------------ pads, strings, choir, robot
    spread = dict(voicing='spread', register=('C3', 'C5'))
    dream.play(P_intro.block(register=(50, 74), voices=5, vel=76), intro)
    pad.play(P_theme.block(register=(62, 79), voices=3, vel=62).slice(16, 32), theme.bar(4))  # the piano alone first,
    # the bed arrives with the bass (a pad under the whole theme masked the left hand)
    pad.play((P * 2).block(register=(55, 74), voices=3, vel=72), verse)
    pad.play((P * 2).block(**spread, vel=78), verse.bar(8))
    pad.play(P_build.block(**spread, vel=78), build_)
    pad.play(P_drop.block(**spread, vel=82), drop1).play(P_drop.block(**spread, vel=84), drop2)
    dream.play(P_break.block(register=(50, 74), voices=5, vel=80), brk)
    pad.play(P_rise.block(**spread, vel=78), rise)
    pad.play(P_lift.block(**spread, vel=86), lift)
    pad.play(P_outro.block(**spread, vel=76).slice(0, 48), outro)
    dream.play(P_outro.block(register=(50, 74), voices=5, vel=74).slice(32, 64), outro.bar(8))

    sv = dict(register=('A3', 'E5'), voices=4)
    for chords, at in ((P_build.block(**sv, vel=70).crescendo(0.6, 1.0), build_),
                       ((P * 2).block(**sv, vel=66), verse.bar(8)),
                       (P_break.block(register=('F#3', 'C#5'), voices=4, vel=72), brk),
                       (P_rise.block(**sv, vel=80).slice(16, 32).crescendo(0.6, 1.0), rise.bar(4)),
                       (P_drop.block(**sv, vel=86), drop2),
                       (P_lift.block(**sv, vel=92), lift),
                       (P_outro.block(**sv, vel=66).slice(0, 32), outro)):
        strings.play(chords.humanize(8, 4, bpm=BPM, seed=int(at.start if isinstance(at, Section) else at)), at)
        breathe(strings, chords, at)                  # players do not enter together: a few ms apart, per voice
    # violin descant: a sighing line above the hook (C#6 D6 C#6 B5 ...), second half of drop 2 and the lift
    # played twice: the VPO section for body (breathing on CC11) and a solo violin on top that PLAYS it - legato
    # transitions, swells on the long notes, delayed vibrato, bow changes (articulation.perform)
    desc = s.motif('12:4 13:4 12:4 11:4 | 13:4 13:4 11:2 12:2 11:4').clip(octave=4, vel=92, gate=1.0)
    for line, at in ((desc, drop2.bar(8)), (desc.transpose(2), lift)):
        violins.play(line, at)
        breathe(violins, line, at, lo=0.8)
        art.perform(solo, line.velocity(0.95), at, bow_seconds=4, vib={'depth': 20, 'rate': 5.4}, humanize_ms=8)

    choir.play(P_break.block(register=('C#3', 'C#5'), voices=4, vel=70), brk)
    choir.play(P_drop.block(**spread, vel=80).slice(32, 64), drop2.bar(8))
    choir.play(P_lift.block(**spread, vel=86), lift)

    # "children of neon": a whisper in the intro, the robot choir in the breakdown, a last farewell in the outro
    voice.play(vox.clip({0: 'children of neon'}, length=16, vel=96), intro.bar(2))
    voice.play(vox.clip({0: 'children of neon', 16: 'children', 24: 'neon'}, length=32), brk)
    voice.play(vox.clip({0: 'children of neon'}, length=16, vel=96), outro.bar(12))
    robot.play(Clip([(0, 7.5, p, 58) for p in ('F#3', 'A3', 'C#4', 'G#4')], length=8), intro.bar(2))
    robot.play(P_break.block(register=('A2', 'E4'), voices=4, vel=90), brk)
    robot.play(Clip([(0, 7.5, p, 56) for p in ('F#3', 'A3', 'C#4', 'G#4')], length=8), outro.bar(12))
    speech.vocode(robot, voice, unvoiced=0.25, sibilance=0.25, attack=20)   # 20 ms: the words read, the 'ch' soft
    neon = brk.bar(6) + 0.4                              # freeze the vowel of the last 'neon' into the rise
    robot.automate('fx.vocoder.hold', [(neon - 2, 0), (neon, 1, 'step'), (rise.start + 2, 0, 'step')])

    # ------------------------------------------------------------------ arps
    glass.play(P_intro.arp('up', rate='1/8', register=(57, 69), vel=70).slice(32, 64), intro.bar(8))
    glass.play((P * 2).arp('down', rate='1/8', register=(57, 69), vel=72), verse.bar(8))
    glass.play(P_break.arp('up', rate='1/8', register=(57, 69), vel=70).slice(16, 32), brk.bar(4))
    glass.play(P_drop.arp('up', rate='1/8', register=(57, 69), vel=72).slice(32, 64), drop1.bar(8))
    glass.play(P_drop.arp('updown', rate='1/8', register=(57, 72), vel=76).slice(0, 32), drop2)
    glass.play(P_drop.arp('updown', rate='1/16', register=(57, 72), vel=78).slice(32, 64), drop2.bar(8))
    glass.play(P_lift.arp('updown', rate='1/16', register=(59, 74), vel=80), lift)
    glass.play((P * 2).arp('up', rate='1/8', register=(57, 69), vel=68), outro)
    pluck.play(P_build.arp('up', rate='1/16', register=(54, 69), vel=82), build_)
    pluck.play(P_drop.arp('updown', rate='1/16', register=(54, 69), vel=86), drop1)
    pluck.play(P_rise.arp('up', rate='1/16', register=(54, 69), vel=82).slice(16, 32), rise.bar(4))
    pluck.play(P_drop.arp('updown', rate='1/16', octaves=2, register=(54, 66), vel=88), drop2)
    pluck.play(P_lift.arp('updown', rate='1/16', octaves=2, register=(56, 68), vel=90), lift)

    # ------------------------------------------------------------------ bass (octave pulse, gate 0.85: a dense wall)
    oct8 = dict(rate='1/8', gate=0.85)
    bass.play(P_theme.bass('root', vel=70).slice(16, 32), theme.bar(4))
    bass.loop(s.prog('F#m').bass('octave', **oct8), verse, bars=8, vel=0.9)             # tonic pedal
    bass.loop(P.bass('octave', **oct8), verse.bar(8), bars=8)                            # released
    bass.play(P_build.bass(pattern='..r.' * 4, rate='1/16', gate=0.9).slice(0, 28), build_)   # trance off-beats,
    # then the low end drops out for the last bar: only the snare roll and the riser lead into the drop
    roll = '.rOr' * 4
    bass.play(P_drop.bass(pattern=roll, rate='1/16', gate=0.9), drop1)
    bass.play(P_drop.bass(pattern=roll, rate='1/16', gate=0.9), drop2)
    bass.play(P_lift.bass(pattern=roll, rate='1/16', gate=0.9), lift)
    bass.play(P_break.bass('root', vel=74), brk)
    bass.play(P_rise.bass('root', vel=80).slice(0, 16), rise)
    bass.play(P_rise.bass('octave', **oct8).slice(16, 32), rise.bar(4))
    bass.play((P * 2).bass('octave', **oct8), outro)
    bass.play(s.prog('Dmaj7:2 Esus4 E F#m9:4').bass('root', vel=74), outro.bar(8))

    # ------------------------------------------------------------------ drums
    K4 = 'x...x...x...x...'
    kit.loop(drums({'hat': '..o...o...o...o.'}), theme.bar(4), bars=3)
    kit.play(drums({'hat': '..o...o...o.....', 'tom_hi': '............x...', 'tom_mid': '.............x..',
                    'tom_lo': '..............xx'}), theme.bar(7))
    kit.loop(drums({'kick': K4, 'hat': '..x...x...x...x.', 'snare': '....x.......x...'}), verse, bars=8, vel=0.9)
    kit.loop(drums({'kick': K4, 'hat': 'o.x.o.x.o.x.o.x.', 'ohh': '..x...x...x...x.', 'snare': '....X.......X...',
                    'clap': '....x.......x...', 82: 'oxooxoxooxooxoxo'}), verse.bar(8), bars=8)
    kit.play(drums({'kick': K4, 'snare': '....X.......oxxX', 'hat': 'o.x.o.x.o.x.....'}), verse.bar(15),
             replace=True)
    # build
    kit.loop(drums({'kick': K4, 'hat': 'xoXoxoXoxoXoxoXo', 'snare': '....X.......X...'}), build_, bars=4)
    kit.loop(drums({'kick': K4, 'hat': 'xoXoxoXoxoXoxoXo', 'snare': 'x.x.x.x.x.x.x.x.'}), build_.bar(4), bars=2)
    kit.play(snare_roll(7, build=True, vel=(40, 112)), build_.bar(6))
    # drops
    drop_kit = drums({'kick': K4, 'hat': 'x.o.x.o.x.o.x.o.', 'ohh': '..x...x...x...x.',
                      'snare': '....X.......X...', 'clap': '....X.......X...', 82: 'oxooxoxooxooxoxo'})
    kit.loop(drop_kit, drop1)
    kit.loop(drop_kit | drums({'tamb': '..x...x...x...x.'}), drop2)
    kit.loop(drop_kit | drums({'tamb': 'x.x.x.x.x.x.x.x.', 'hat': 'xoxoxoxoxoxoxoxo'}), lift)
    kit.play(drums({'kick': K4, 'snare': '....X.......xxXX', 'clap': '....X.......X...', 'ohh': '..x...x.......'}),
             drop1.bar(7), replace=True)
    kit.play(tom_fill(2, vel=(90, 124)), drop1.bar(15, 2), replace=True)
    for bar in (3, 11):
        kit.play(tom_fill(1, vel=(88, 116)), drop2.bar(bar, 3), replace=True)
    kit.play(tom_fill(2, vel=(96, 126)), drop2.bar(7, 2), replace=True)
    kit.play(snare_roll(4, build=True, vel=(50, 118)) | drums({'kick': K4}), drop2.bar(15), replace=True)
    kit.play(tom_fill(2, vel=(96, 126)), lift.bar(3, 2), replace=True)
    kit.play(drums({'kick': K4, 'snare': '....X.....xxXXXX', 'clap': '....X.......X...'}), lift.bar(7), replace=True)
    # rise: filtered kick comes back, then the roll
    kit.loop(drums({'kick': K4}), rise.bar(4), bars=2)
    kit.loop(drums({'kick': K4, 'hat': 'xoXoxoXoxoXoxoXo'}), rise.bar(6), bars=2)
    kit.play(snare_roll(8, build=True, vel=(40, 114)), rise.bar(6))
    # outro: the beat strips away
    kit.loop(drums({'kick': K4, 'hat': '..x...x...x...x.', 'ohh': '..............x.', 'snare': '....X.......X...'}),
             outro, bars=4)
    kit.loop(drums({'kick': K4, 'hat': '..o...o...o...o.'}), outro.bar(4), bars=4)
    for at in (verse.start, drop1.start, drop1.bar(8), brk.start, drop2.start, drop2.bar(8), lift.start,
               lift.bar(4), outro.start):
        kit.play(crash(116), at)
    kit.add_fx(fx.filter(name='kf', mode='lp', cutoff=20000))
    kit.automate('fx.kf.cutoff', [(0, 20000), (rise.bar(4) - 0.01, 20000), (rise.bar(4), 250, 'step'),
                                  (rise.bar(7), 3000, 'exp'), (rise.end - 1, 20000, 'exp')])

    # ------------------------------------------------------------------ transitions
    for sec, length in ((build_, 32), (rise, 32), (drop2.bar(12), 16)):
        t0 = sec.start if isinstance(sec, Section) else sec
        drop_at = t0 + length - 1
        riser_t.note('F#3', t0, length - 1, 100)
        riser_t.automate('instrument.cutoff', riser(drop_at, length=length - 1, lo=300, hi=12000))
        riser_t.automate('instrument.hpf', riser(drop_at, length=length - 1, lo=20, hi=1500))
    impact.note('F#1', drop1.start, 4, 120).note('F#1', drop2.start, 4, 124).note('G#1', lift.start, 4, 124)
    down.note('F#3', brk.start, 8, 110).note('F#3', outro.start, 6, 90)

    # a one-beat breath before each drop: only the reverb tails
    band = [kit, bass, piano, keys, pad, strings, pluck, glass, choir, saw, dream]
    silence(band, drop1.start - 1, drop1.start)
    silence(band, drop2.start - 1, drop2.start)
    # ... broken only by the melody piano's pickup into the hook (A-B -> C#), the octave rolled
    pick = lead(s.motif('3:1/16 4:1/16'), vel=100, dbl=0.65)
    for at in (drop1.start - 0.5, drop2.start - 0.5):
        keys.play(pick, at)

    # ------------------------------------------------------------------ production moves
    s.sidechain(pluck, glass, strings, dream, key=kit, pitches='kick', depth=7, release=260)
    s.sidechain(violins, solo, robot, key=kit, pitches='kick', depth=3, release=260)
    s.sidechain(bass, key=kit, pitches='snare', depth=6, release=120)   # the snare rolls cut through the bass too
    # the kick gets its hole in the wash: the reverbs and the lead lines give way for ~150 ms (punch 12 vs 19 dB)
    s.sidechain(plate, shimmer, saw, key=kit, pitches='kick', depth=4, release=180)
    s.sidechain(hall, key=kit, pitches='kick', depth=2.5, release=200)
    s.sidechain(piano, keys, key=kit, pitches='kick', depth=1.5, release=150)
    dream.automate('instrument.cutoff', exp_ramp(intro.start, intro.bar(12), 500, 2600))
    pad.automate('instrument.cutoff', exp_ramp(theme.start, theme.end, 700, 1800), hold(verse.start, build_.start, 2600),
                 exp_ramp(build_.start, drop1.start, 1800, 3400), hold(drop1.start, brk.start, 3400),
                 exp_ramp(rise.start, drop2.start, 1200, 3600), hold(drop2.start, outro.start, 3600),
                 exp_ramp(outro.start, outro.bar(12), 3000, 700))
    pluck.automate('instrument.cutoff', exp_ramp(build_.start, build_.end, 300, 900),
                   hold(drop1.start, brk.start, 800), exp_ramp(rise.bar(4), rise.end, 300, 900),
                   hold(drop2.start, outro.start, 1000))
    saw.automate('instrument.cutoff', exp_ramp(rise.bar(4), rise.end, 700, 5000), hold(drop1.start, drop1.end, 5000),
                 hold(drop2.start, outro.start, 5500))
    # the piano breathes in the empty spaces: more hall / echo / shimmer where the beat is gone
    arc(piano, -9, [(0, 3), (theme, 0, 'smooth'), (verse, -1), (build_, 1.5), (drop1, -1), (brk, 0), (brk.bar(1), 3, 'smooth'),
                    (rise, 0, 'smooth'), (drop2, -1), (outro.bar(8), -1), (outro.bar(12), 3, 'smooth')],
        target='send.hall')
    arc(piano, -18, [(0, 8), (theme, 8), (theme.bar(1), 0, 'smooth'), (brk, 0), (brk.bar(1), 7, 'smooth'),
                     (rise, 2, 'smooth'), (outro.bar(6), 0), (outro.bar(10), 8, 'smooth')], target='send.echo')
    arc(piano, -30, [(0, 12), (theme, 12), (theme.bar(1), 0, 'smooth'), (brk, 0), (brk.bar(1), 16, 'smooth'),
                     (rise, 0, 'smooth'), (outro.bar(8), 0), (outro.bar(12), 18, 'smooth')], target='send.shimmer')
    arc(wind, 0, [(intro, -14), (intro.bar(3), -2, 'smooth'), (intro.bar(14), -2), (theme.bar(4), -14, 'smooth'),
                    (brk, -14), (brk.bar(2), 0, 'smooth'), (rise.bar(3), 0), (rise.bar(4), -14, 'smooth'),
                    (outro.bar(6), -14), (outro.bar(10), 0, 'smooth'), (outro.bar(13), 0),
                    (outro.end, -24, 'smooth')])
    # the last chord: the beds fade away under the piano's own decay and the reverb tails
    for t in (dream, rain):
        t.automate('gainDb', [(outro.bar(12), 0), (outro.end, -26, 'smooth')])     # dB on the track's gain_db
    # drop 1 is leaner than drop 2: its bass sits 1.5 dB lower; the outro's held roots recede
    arc(bass, 0, [(0, 0), (drop1, -1.5), (brk, -4), (rise.bar(4), 0), (outro.bar(8), 0), (outro.bar(9), -5, 'smooth'),
                  (outro.bar(12), -5), (outro.end, -30, 'smooth')])

    # the energy arc: limiter drive per section (the verse and the breakdown hold back, the lift pushes)
    # (the drops ~1 dB less drive than the first re-production: at a -1.2 dB ceiling every dB of drive is a dB of
    # kick / snare punch lost - drop 2 read crest 12 vs 14.8 dB and kick punch 14 vs 19 dB against 'Sunset')
    # (the build pulls back and drop 1 pushes: the build's roll + riser read LOUDER than drop 1 - an anticlimax)
    s.master.automate('fx.limiter.gain', [(0, 5.2), (verse.start, 3.9, 'step'), (build_.start, 3.2, 'step'),
                                          (drop1.start, 4.8, 'step'), (brk.start, 2.7, 'step'),
                                          (rise.bar(4), 3.3), (drop2.start - 1, 3.3),
                                          (drop2.start, 4.2, 'step'), (lift.start, 4.6, 'step'), (outro.start, 4.3, 'step'),
                                          (outro.bar(8), 4.3), (outro.bar(12), 2.3, 'smooth')])
    # the breakdown belongs to the robot choir: the Fairlight choir steps back, the vocoder steps forward
    arc(choir, 0, [(0, 0), (brk, -4), (rise, 0)])                    # 'gainDb' lanes: dB on the track's gain_db
    arc(robot, 0, [(0, 0), (brk, 2.5), (rise, 0)])
    arc(keys, 0, [(0, 0), (lift, 1), (outro, 0)])
     # the melody piano stays on top of the lift's choir
    # room for the hook: the sustained bed dips ~2.5 dB while the melody piano plays (keyed by it), so the hook reads
    # in front without pushing its level (mids / presence were at the profile's limit)
    s.sidechain(pad, choir, strings, dream, key=keys, threshold=-34, depth=2.5, attack=15, hold=60, release=260)

    # ------------------------------------------------------------------ ending: slow into the last chord, let it ring
    s.ritardando((outro.bar(10), outro.bar(12)), to=0.8, a_tempo=False)
    return s
