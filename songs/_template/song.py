"""Synthwave starter with the lush library setup. Build: python -m agentsound build songs/<slug>

Sounds: `python -m agentsound patches` lists the library - s.track('x', 'category/name'); every patch lands at
-18 LUFS and brings its recommended reverb/echo sends. `python -m agentsound params va` shows every parameter.
Reference: docs/COMPOSE_API.md; recipes/synthwave.md ('Size and space' = the width / reverb / bed targets the
report checks).
"""
from agentsound import *

ANALYSIS = {'profile': 'synthwave'}                  # the report judges against the synthwave targets


def build() -> Song:
    s = Song('Template', tempo=108, key='A minor', seed=1)

    # Arrangement (bars). Positions: sec.start / sec.bar(n) (0-based, -1 = last bar) / sec.beat(-2).
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=16)
    chorus = s.section('chorus', bars=16)
    outro = s.section('outro', bars=4)

    # Material
    prog = s.prog('i VI III VII')                            # Am F C G, one bar each
    beat = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...',
                  'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '..............x.'})
    lift = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'clap': '....x.......x...',
                  'hat': 'xxx.xxx.xxx.xxx.', 'ohh': '..x...x...x...x.'})     # chorus: 16th hats, claps
    hook = s.motif('5:1/4 4:1/8 3:1/8 1:1/4 3:1/4 | 2:1/4 3:1/8 5:1/8 3:1/2 '
                   '| 5:1/4 6:1/8 5:1/8 8:1/4 7:1/4 | 5:1/2. r:1/4')   # 4 bars, degree:note-value

    # Space: the returns every patch's default sends feed, and the master chain.
    s.hall(), s.plate(), s.echo()                            # hall (pads, leads), plate (keys), dotted-8th ping-pong
    shimmer = s.bus('shimmer', 'bus/shimmer')                # octave halo: pads send to it in intros / breaks
    s.master.use('master/synthwave')                         # glue, tape, exciter, width (mono lows), limiter

    # Sounds; gain_db is your fader (the bed sits 0-5 dB under the lead)
    kit = s.track('drums', 'synthwave/drums_outrun').groove('laidback').humanize(2, 4)
    s.gated(key=kit, pitches=['snare', 'clap'])              # 80s gated snare (the kit sends -6 dB to it)
    bass = s.track('bass', 'synthwave/octave_bass')
    pad = s.track('pad', 'synthwave/warm_pad', sends={shimmer: -20})
    keys = s.track('keys', 'gm/epiano', gain_db=-2, pan=-0.3)     # synthwave/epiano: the DX7 version (needs the ROMs)
    arps = s.track('arp', 'synthwave/arp_pluck', gain_db=-2, pan=0.3)
    lead = s.track('lead', 'synthwave/supersaw_lead', gain_db=2)

    # Parts
    pad.loop(prog.block(voicing='spread', register=('C3', 'C5')), intro, verse, chorus, outro)
    kit.loop(beat, verse, vel=0.85).loop(lift, chorus)                  # the verse holds back, the chorus hits
    kit.play(snare_roll(4, build=True), verse.bar(-1), replace=True)
    kit.play(crash(), chorus)
    bass.loop(prog.bass('octave', rate='1/8'), verse, vel=0.85).loop(prog.bass('octave', rate='1/8'), chorus)
    arps.loop(prog.arp('updown', rate='1/16', octaves=2, register=('C4', 'C5')), intro, verse, chorus, outro)
    keys.loop(prog.block(voicing='drop2', rhythm='x..x..x.', register=('C4', 'C5')), verse, chorus)
    lead.play(hook.clip(octave=4), chorus, times=4)

    # Production moves: kick pump (bass deeper than the bed), the arp fading in and out, the intro filter
    # opening, the shimmer blooming when the drums are out.
    s.sidechain(bass, key=kit, pitches='kick', depth=9, release=200)
    s.sidechain(pad, arps, key=kit, pitches='kick', depth=5, release=180)
    # 'gainDb' lanes are dB on the track's gain_db: fade in from -12, out to -18
    arps.automate('gainDb', ramp(intro.start, verse.start, -12, 0), ramp(outro.start, outro.end, 0, -18))

    pad.automate('instrument.cutoff', exp_ramp(intro.start, verse.start, 600, 3000),
                 exp_ramp(outro.start, outro.end, 3000, 500))
    pad.automate('send.shimmer', hold(intro.start, verse.start, -8), hold(verse.start, outro.start, -20),
                 hold(outro.start, outro.end, -8))
    return s
