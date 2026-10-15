"""Wavetable demo: the five wavetable/ presets (built-in tables only, no files needed) in a short piece.

  intro   the evolving pad alone: its vowel table wandering, the harmonic layer blooming on each chord
  groove  the warm pad (its position automated from triangle towards saw over the section), the pluck sequence
          (harmonic strike falling back to the fundamental), the bass with its position 'bite', drums
  lift    + the lead: vocal formant table with its octave-down body, glide and vibrato, a counter-line in C4-C5
  outro   pad morphing back, the evolving pad alone
Build: python -m agentsound build songs/_demo_wavetable
"""
from agentsound import *

ANALYSIS = {'profile': 'synthwave'}


def build() -> Song:
    s = Song('Wavetable Demo', tempo=100, key='D minor', seed=11, tail=5)
    PROG = s.prog('i VI III VII')                               # Dm Bb F C
    LIFT = s.prog('VI VII i i')                                 # Bb C Dm Dm
    intro = s.section('intro', bars=4, prog=PROG)
    groove = s.section('groove', bars=8, prog=PROG)
    lift = s.section('lift', bars=8, prog=LIFT)
    outro = s.section('outro', bars=4, prog=PROG)

    s.hall(), s.plate(), s.echo()
    s.master.use(patches.get('master/synthwave').but_fx('limiter', gain=5))

    evolve = s.track('evolve', 'wavetable/evolving_pad', gain_db=-2)
    pad = s.track('pad', 'wavetable/warm_pad', gain_db=-3)
    pluck = s.track('pluck', 'wavetable/pluck', gain_db=-3, pan=0.25)
    bass = s.track('bass', 'wavetable/bass', gain_db=-1)
    lead = s.track('lead', 'wavetable/lead', gain_db=1).humanize(4, 6)
    kit = s.track('drums', 'synthwave/drums_outrun', gain_db=-3).groove('laidback').humanize(2, 4)

    evolve.chords(intro, outro, voicing='spread', register=('D3', 'D5'), vel=80)
    evolve.chords(lift, voicing='spread', register=('D3', 'D5'), vel=70, bars=2)
    pad.chords(groove, lift, voicing='spread', register=('C3', 'C5'), vel=84)
    pluck.arp('updown', groove, lift, rate='1/16', octaves=2, register=('D4', 'D5'), vel=96)
    bass.bassline('octave', groove, lift, rate='1/8', scale={groove: 0.85})
    kit.plan({groove: drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
              .velocity(0.85),
              lift: drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'clap': '....x.......x...',
                           'hat': 'xxx.xxx.xxx.xxx.', 'ohh': '..x...x...x...x.'})},
             fills={groove: snare_roll(2, build=True)}, crashes=[lift])

    # The lead: a counter-line in the middle register with velocity arcs over each 2-bar phrase.
    line = s.motif('1:1/4 3:1/8 4:1/8 5:1/2 | 4:1/4 3:1/4 2:1/2 | 3:1/4 5:1/8 6:1/8 7:1/4. 6:1/8 | 5:1 '
                   '| 6:1/4 5:1/8 4:1/8 3:1/2 | 4:1/4 5:1/4 7:1/2 | 8:1/4. 7:1/8 6:1/4 5:1/4 | 5:1')
    lead.play(line.clip(octave=4, vel=92).arch(2, 0.6).accent(2, 1.15), lift)

    # Morph moves: the warm pad's table position automated (triangle -> towards saw, brighter into the lift); the pump.
    pad.automate('instrument.osc1.position', ramp(groove.start, lift.start, 0.36, 0.5),
                 ramp(lift.start, outro.start, 0.5, 0.62))
    s.sidechain(bass, key=kit, pitches='kick', depth=11, release=160)
    s.sidechain(pad, pluck, key=kit, pitches='kick', depth=4, release=180)
    return s
