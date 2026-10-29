"""Space-sitcom teaser score (D:/Projekte/space_sitcom/video): music for the two exterior shots of the 30-s test
(shot 1 = 0-8.0 s ship past the ringed planet, shot 2 = 8.0-15.3 s crystal nebula + a bonk). Retro-futuristic
funk-synthwave, original hook. 120 bpm = 2 s per bar: shot 1 = bars 0-3 (intro bar + 3 bars theme), shot 2 = bars 4-7
(the theme an octave up with 16th hats, sparkle arp). The engine-room scene (15.3-30.4 s) has no music (its own
H3 sound with the German line). The video assembly trims the mix to 15.3 s with a short fade.

Build: python -m agentsound build songs/space-sitcom-teaser
"""
from agentsound import *

METADATA = {'title': 'Space Sitcom Teaser (Score)', 'artist': 'AgentSound', 'genre': 'Soundtrack', 'year': 2026,
            'comment': 'teaser score for the exterior shots of the space-sitcom test, 15 s'}
ANALYSIS = {'profile': 'synthwave'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'SPACE SITCOM', 'subtitle': 'AgentSound', 'seed': 7}


def build() -> Song:
    s = Song('Space Sitcom Teaser', tempo=120, key='D minor', seed=7)

    prog = s.prog('i iv VII III')                            # Dm Gm C F
    intro = s.section('intro', bars=1, prog=s.prog('i'))
    planet = s.section('planet', bars=3, prog=prog)          # 2.0-8.0 s
    nebula = s.section('nebula', bars=4, prog=prog)          # 8.0-16.0 s (trimmed at 15.3)

    groove = drums({'kick': 'x.....x...x.....', 'snare': '....x.......x...',
                    'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '......x.......x.'})
    busy = drums({'kick': 'x.....x...x...x.', 'snare': '....x.......x.x.', 'clap': '....x.......x...',
                  'hat': 'xxxxxxxxxxxxxxxx', 'ohh': '......x.......x.'})
    hook = s.motif('1:1/8 r:1/16 1:1/16 5:1/8 4:1/8 3:1/4 r:1/8 5:1/8 | 6:1/8 5:1/8 4:1/8 3:1/8 2:1/4 r:1/4 '
                   '| 3:1/8 r:1/16 3:1/16 7:1/8 6:1/8 5:1/4 r:1/8 3:1/8 | 4:1/8 5:1/8 6:1/8 8:1/8 7:1/2')

    s.hall(), s.plate(), s.echo()
    shimmer = s.bus('shimmer', 'bus/shimmer')
    s.master.use('master/synthwave')

    kit = s.track('drums', 'synthwave/drums_outrun').groove('laidback').humanize(2, 4)
    bass = s.track('bass', 'synthwave/octave_bass', gain_db=1)
    pad = s.track('pad', 'synthwave/warm_pad', sends={shimmer: -14})
    arps = s.track('arp', 'synthwave/arp_pluck', gain_db=-3, pan=0.3)
    lead = s.track('lead', 'synthwave/supersaw_lead', gain_db=1)

    pad.chords(s.sections, voicing='spread', register=('C3', 'C5'))
    kit.plan({planet: groove, nebula: busy}, fills={planet: (3, snare_roll(2, build=True))}, crashes=[planet, nebula])
    bass.bassline('octave', planet, nebula, rate='1/8', scale={planet: 0.9})
    arps.arp('updown', nebula, rate='1/16', octaves=2, register=('C5', 'C6'))
    lead.play(hook.clip(octave=4), planet)
    lead.play(hook.clip(octave=5), nebula)

    s.sidechain(bass, pad, key=kit, pitches='kick', depth=7, release=180)
    pad.automate('instrument.cutoff', exp_ramp(intro.start, planet.start, 400, 2800))
    return s
