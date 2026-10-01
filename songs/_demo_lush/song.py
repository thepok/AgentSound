"""Lush synthwave demo: 32 bars built only from library patches and their default (recommended) sends.

Proof that the library sounds big by default: pad bed (+ strings), supersaw lead, arp, e-piano, bells, octave bass,
drums with a keyed gated snare; hall / plate / echo / shimmer returns and the synthwave master. No per-song sound
design: the song only chooses patches, notes, faders, pans and arrangement moves.
Build: python -m agentsound build songs/_demo_lush

Measured (report.json 'space', full sections verse / chorus / final): mix width 36 / 35 / 39 % (recipe 30-55),
correlation 0.48 / 0.48 / 0.44 (0.2-0.6), width above 150 Hz 77 / 66 / 70 % (40-100), reverb returns
-11.3 / -11.4 / -11.3 LU under the mix (8-14), echo -20.9 / -18.4 / -18.6 LU (audible above -24), bed -0.3 dB under
the lead (0..-5); -10.9 LUFS-I, TP -1.1 dBTP, 0 clicks, 0 warnings, 0 info. Intro and break (no drums: not judged)
read 84-88 % wide with correlation 0.06-0.09; the shimmer blooms there 9-11 LU under the mix.
"""
from agentsound import *

ANALYSIS = {'profile': 'synthwave'}                  # the report judges against the synthwave targets


def build() -> Song:
    s = Song('Lush Demo', tempo=108, key='A minor', seed=7, tail=6)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    brk = s.section('break', bars=4)
    final = s.section('final', bars=8)

    verse_prog = s.prog('i9 VImaj7 IIIadd9 VIIsus4')         # Am9 Fmaj7 Cadd9 Gsus4
    chorus_prog = s.prog('VI VII i i')                        # F G Am Am: the lift into the tonic
    hook = s.motif('5:1/4. 4:1/8 3:1/4 5:1/4 | 4:1/4. 3:1/8 2:1/4 4:1/4 | 5:1/8 8:1/4 7:1/8 5:1/4 3:1/4 | 5:1/2. r:1/4 '
                   '| 5:1/4. 4:1/8 3:1/4 5:1/4 | 4:1/4. 5:1/8 7:1/4 9:1/4 | 8:1/2. 7:1/8 5:1/8 | 8:1/2 r:1/2')
    answer = s.motif('r:1 | r:1/2 5:1/8 6:1/8 8:1/4 | r:1 | r:1/2 9:1/8 8:1/8 7:1/4 '
                     '| r:1 | r:1/2 5:1/8 6:1/8 8:1/4 | r:1 | r:1/4 10:1/8 9:1/8 8:1/4 5:1/4')   # sparse bell answers
    beat = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...',
                  'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '..............x.'})
    beat_chorus = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'clap': '....x.......x...',
                         'hat': 'xxx.xxx.xxx.xxx.', 'ohh': '..x...x...x...x.'})

    # Returns and master: the library's lush setup (the patches' default sends feed them).
    s.hall(), s.plate(), s.echo()
    shimmer = s.bus('shimmer', 'bus/shimmer')
    s.master.use('master/synthwave')

    kit = s.track('drums', 'synthwave/drums_outrun').groove('laidback').humanize(2, 4)
    s.gated(gain_db=2, key=kit, pitches=['snare', 'clap'])
    bass = s.track('bass', 'synthwave/octave_bass')
    pad = s.track('pad', 'synthwave/warm_pad', sends={shimmer: -20})
    strings = s.track('strings', 'synthwave/jupiter_strings', gain_db=-3)
    keys = s.track('epiano', 'synthwave/epiano', pan=-0.3)
    arps = s.track('arp', 'synthwave/arp_pluck', gain_db=-1, pan=0.3)
    lead = s.track('lead', 'synthwave/supersaw_lead', gain_db=2).humanize(3, 5)
    bells = s.track('bells', 'synthwave/dx_bells', gain_db=-2, pan=0.15)
    whoosh = s.track('riser', 'synthwave/noise_riser', gain_db=-4)

    # Parts
    pad.loop(verse_prog.block(voicing='spread', register=('C3', 'C5')), intro, verse)
    pad.loop(chorus_prog.block(voicing='spread', register=('C3', 'C5')), chorus, final)
    pad.play(verse_prog.block(voicing='spread', register=('C3', 'C5')), brk)
    strings.loop(verse_prog.block(register=('A3', 'A5'), voices=3), verse.bar(4), bars=4, vel=0.8)   # the verse builds
    strings.loop(chorus_prog.block(register=('A3', 'A5'), voices=3), chorus, final)
    keys.loop(verse_prog.block(voicing='drop2', rhythm='x..x..x.', register=('C4', 'C5')), verse)
    keys.play(verse_prog.block(voicing='drop2', rhythm='x.......', register=('C4', 'C5'), vel=72), brk)
    keys.loop(chorus_prog.block(voicing='drop2', rhythm='x..x..x.', register=('C4', 'C5')), chorus, final)
    arps.loop(verse_prog.arp('updown', rate='1/16', octaves=2, register=('C4', 'C5')), intro, verse)
    arps.loop(chorus_prog.arp('updown', rate='1/16', octaves=2, register=('C4', 'C5')), chorus, final)
    bass.loop(verse_prog.bass('octave', rate='1/8'), verse, vel=0.85)
    bass.loop(chorus_prog.bass('octave', rate='1/8'), chorus, final)
    kit.loop(beat, verse, vel=0.85)                               # the verse holds back, the chorus hits
    kit.loop(beat_chorus, chorus, final)
    kit.play(snare_roll(4, build=True), verse.bar(-1), replace=True)
    kit.play(crash(), chorus).play(crash(), final)
    lead.play(hook.clip(octave=4), chorus)
    lead.play(hook.clip(octave=4), final)
    bells.play(hook.clip(octave=5, vel=70), final)                # the last chorus: bells double the hook
    bells.play(answer.clip(octave=4, vel=84), verse)
    bells.play(hook.clip(octave=5, vel=80).slice(0, 16), brk)
    whoosh.note('A3', brk.start, brk.length)
    whoosh.automate('instrument.cutoff', riser(final, length=brk.length, lo=300, hi=12000))
    whoosh.automate('instrument.hpf', riser(final, length=brk.length, lo=20, hi=1500))

    # Production moves: kick pump, the intro filter opening, the shimmer blooming in the intro and the break.
    s.sidechain(bass, key=kit, pitches='kick', depth=9, release=200)
    s.sidechain(pad, strings, arps, key=kit, pitches='kick', depth=5, release=180)
    arps.automate('gainDb', ramp(intro.start, verse.start, -13, 0))      # dB on the track's gain_db

    pad.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 600, 3000), hold(verse.start, brk.start, 3000),
                 exp_ramp(brk.start, brk.bar(3), 3000, 1400), exp_ramp(brk.bar(3), final.start, 1400, 3000))
    pad.automate('send.shimmer', hold(intro.start, verse.start, -8), hold(verse.start, brk.start, -20),
                 hold(brk.start, final.start, -8), hold(final.start, final.end, -20))
    return s
