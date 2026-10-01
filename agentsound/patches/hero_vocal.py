"""The vocal hero: a SUNG lead vocal (agentsound.singer) produced like a record's lead vocal.

    vox = singer.sing(s, melody, lyrics, at=verse)
    hero(vox.track, family='vocal', bed=[pad, strings], competitors=[keys, guitar])

The chain (heroes.ORDER), voiced on the DiffSinger voicebanks' renders:
  tone      high-pass 90 Hz (24 dB/oct: rumble, the vocoder's low-frequency noise between phrases), -2 dB of mud at
            280 Hz, -1 dB of nasal honk at 1 kHz
  comp      3:1, 8 ms attack, 120 ms release, soft knee: the vocal level nearly constant (a sung line has 10-15 dB
            between its soft and loud words), the consonants still pass
  deess     the de-esser (engine 'deesser'): s / t / sh peaks above 7 kHz down by up to 8 dB (split band: the vowel's
            brightness stays) - after the compressor that brought them up, before the presence boost. A male voice:
            hero(..., deess={'freq': 5500})
  drive     a touch of tube (density, no audible distortion)
  presence  +2 dB at 3.5 kHz (words: the intelligibility band 2-5 kHz) and a +2.5 dB air shelf at 11 kHz
  air       the breath stage (heroes.AIR): the singer's within-note air lands after the compressor
Space: the vocal plate (bus/hero_plate -12 dB), the classic vocal echo throws on phrase ends (-20 -> -6 dB).
Mix: the bed ducks 2.5 dB and steps out of 3 kHz while the vocal sings; competitors (keys, rhythm guitars) -2.5 dB
at 3 kHz; +1.5 dB in the hooks.
The preset has no default sound (a sung vocal is rendered per song): use it on a vocal track (hero(track, ...)).
Doubles and harmonies (singer.double / singer.harmony) take the same chain with the mix rules off:
hero(dbl.track, family='vocal', ride=False, throws=False, duck=False, carve=False, dips=False).
"""

from __future__ import annotations

from .. import heroes

VERSION = 1

heroes.define(
    'vocal', family='vocal', sound=None, gain_db=0.0, user_gain_db=0.0, aliases=('vox', 'lead_vocal', 'sung'),
    words=('vocal_take',),
    chain={'tone': {'hp.freq': 90, 'hp.slope': 24, 'peak1.freq': 280, 'peak1.gain': -2.0, 'peak1.q': 0.9,
                    'peak2.freq': 1000, 'peak2.gain': -1.0, 'peak2.q': 1.2},
           'comp': {'threshold': -22, 'ratio': 3.0, 'knee': 6, 'attack': 8, 'release': 120, 'automakeup': 'on'},
           'deess': {'freq': 7000, 'threshold': -30, 'ratio': 6, 'range': 8, 'attack': 0.8, 'release': 60},
           'drive': {'mode': 'tube', 'drive': 3, 'mix': 0.2, 'tone': 0.5},
           'presence': {'peak3.freq': 3500, 'peak3.gain': 2.0, 'peak3.q': 0.8, 'high.freq': 11000,
                        'high.gain': 2.5}},
    sends={'plate': -12.0, 'echo': -20.0},
    space={'plate_bus': 'bus/hero_plate', 'plate': -12.0, 'echo': -20.0, 'throw': -6.0, 'min_rest': 0.75,
           'min_dur': 0.75},
    mix={'duck': 2.5, 'carve_db': 3.0, 'carve_freq': 3000.0, 'carve_q': 0.7, 'ride_db': 1.5, 'dip_db': -2.5,
         'dip_freq': 3000.0},
    play={'vel': (64, 110), 'vib': False},
    notes=f'v{VERSION}. The vocal hero (a sung lead vocal, agentsound.singer): high-pass 90 Hz, -2 dB mud at 280 Hz, '
          '-1 dB at 1 kHz, a vocal compressor 3:1 (8 ms attack), the de-esser (7 kHz, up to -8 dB, split band), a '
          'touch of tube, +2 dB presence at 3.5 kHz, a +2.5 dB air shelf at 11 kHz, the breath stage. Space: the '
          'vocal plate (bus/hero_plate -12), echo throws (-20 -> -6 dB on phrase ends). Mix: bed ducks 2.5 dB, '
          'carved 3 dB at 3 kHz, competitors -2.5 dB, +1.5 dB in the hooks. Play it with agentsound.singer (sing, '
          'double, harmony); a male voice: deess={"freq": 5500}.',
)
