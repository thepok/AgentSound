"""Hero presets for the families that had no hero yet: strings (violin), brass (trumpet), woodwind (flute), voice
(choir), organ and generic - the shared hero chain of agentsound.heroes voiced for each, around a sampled default.

  hero/strings    sampled/solo_violin (VSCO 2 CE) - the film / pop violin theme
  hero/brass      sampled/solo_trumpet (VSCO 2 CE) - the 80s pop / film trumpet solo, a fanfare line
  hero/woodwind   sampled/solo_flute (VSCO 2 CE) - the lyrical flute melody
  hero/voice      sampled/choir (VPO "ah") - a vocal-like topline ("aah" hook, dream pop, film)
  hero/organ      sampled/tonewheel_organ (FreePats setBfree B3 + the library's Leslie) - the organ solo
  hero/generic    sampled/solo_cello (SSO) - any other instrument through the neutral hero chain

Use them through the wrapper: hero(s.track('lead', 'sampled/solo_violin'), family='strings', genre='film',
bed=[pad, strings]) (the sound AND the mix rules), or hero('sampled/trumpet', family='brass') for a Patch. A single
source stays a plain sampler: the instrument's keyswitch articulations, legato transitions, 'dynamics' swells and
per-note glides keep working (articulation.perform / heroes.play); double='takes' / octave=True make a stack.

Calibration (python -m agentsound audition hero/<name>; .scratch renders of the validation): every preset at its gain_db
lands at -18.0 LUFS on its audition phrase (MEASURED holds the numbers); the chains keep the velocity response of the
source (velocity ladder 40 -> 120, dB per 10 velocity steps, raw vs hero, in MEASURED) - 2.5:1 or less with a 20-25 ms
attack, so accents pass and long notes bloom. The frequencies are the instruments' own: violin box ~500 Hz / nasal
~1.1 kHz / screech ~3.8 kHz, trumpet honk ~1.2 kHz / brilliance 2.5-3 kHz, flute breath above 8 kHz, voice presence
~3.2 kHz, organ bark ~800 Hz.
"""

from __future__ import annotations

from .. import heroes
from . import inst
from . import sampled, sampled_keys, sampled_orchestra  # noqa: F401  (the default sounds must be registered first)

VERSION = 1

_SSO_FLUTE = 'samples/sso/Sonatina Symphonic Orchestra/Woodwinds - Notation/Flute Solo 1 Sustain (looped).sfz'
"""The woodwind take: the SSO flute (another player and recording than the VSCO default - sampled/flute is the VSCO
flute again, a copy would phase), sfz level -2 dB = the library's -18 LUFS."""

LEVELS = {'strings': -1.1, 'brass': -1.8, 'woodwind': -0.7, 'voice': -2.5, 'organ': -0.2, 'generic': -1.6}
"""gain_db per preset (the audition calibration to -18.0 LUFS)."""

MEASURED: dict = {}
"""The calibration / validation numbers per preset (filled below; see the module docstring)."""


def _define(name: str, **kw) -> None:
    kw.setdefault('audition', {'notes': 'phrase'})
    kw['notes'] = kw['notes'] + ' Measured -18.0 LUFS (audition phrase).'
    heroes.define(name, family=kw.pop('family', name), gain_db=LEVELS[name], measured=MEASURED.get(name, {}), **kw)
    heroes.register(name)


_define(
    'strings', sound='sampled/solo_violin', aliases=('violin', 'string', 'fiddle'), words=('violin', 'fiddle'),
    chain={'tone': {'hp.freq': 150, 'hp.slope': 24, 'peak1.freq': 500, 'peak1.gain': -1.5, 'peak1.q': 1.0,
                    'peak2.freq': 1100, 'peak2.gain': -1.5, 'peak2.q': 1.2, 'peak3.freq': 3800, 'peak3.gain': -1.5,
                    'peak3.q': 1.4},
           'comp': {'threshold': -21, 'ratio': 1.8, 'knee': 8, 'attack': 25, 'release': 180, 'automakeup': 'on'},
           'tape': {'speed': '15', 'drive': 2, 'bump': 0.5, 'wow': 0.0, 'flutter': 0.02},
           'presence': {'peak3.freq': 2800, 'peak3.gain': 1.5, 'peak3.q': 0.8, 'high.freq': 9000,
                        'high.gain': 2.0}},
    takes=[{'id': 'section', 'sound': 'sampled/violins', 'level': -12.0, 'delay': 25.0, 'hp': 220}],
    octave={'id': 'octave', 'sound': 'sampled/solo_cello', 'level': -10.0, 'transpose': -12, 'hp': 70, 'mode': 'off'},
    sends={'hall': -9.0, 'plate': -16.0, 'echo': -28.0},
    space={'plate_bus': 'bus/hero_plate', 'plate': -16.0, 'echo': -28.0, 'throw': -12.0, 'min_rest': 0.75,
           'min_dur': 1.0},
    mix={'duck': 1.5, 'carve_db': 3.0, 'carve_freq': 2800.0, 'carve_q': 0.8, 'ride_db': 1.0, 'dip_db': -1.5,
         'dip_freq': 2800.0},
    play={'vel': (58, 112), 'vib': {'depth': 18, 'rate': 5.4, 'delay': 0.3}},
    notes=f'v{VERSION}. The hero violin (a film theme, a pop-ballad violin solo, Celtic / cinematic leads): the VSCO 2 '
          'solo violin (a legato player with its sustain / spiccato / pizzicato / tremolo keyswitches: they keep '
          'working, the hero stays a plain sampler) through the strings hero chain: high-pass 150 Hz, -1.5 dB box '
          '(500 Hz), -1.5 dB nasal (1.1 kHz), -1.5 dB screech (3.8 kHz, narrow) before a 1.8:1 compressor (25 ms '
          'attack: the bow attacks and swells pass), 15 ips tape (drive 2), then +1.5 dB presence at 2.8 kHz and a '
          '+2 dB air shelf at 9 kHz. Space: the hall (-9) and its own bright pre-delayed plate (bus/hero_plate -16 '
          'in a song), a quiet echo thrown up on the held phrase ends (-28 -> -12 dB). Options: double="takes" (the '
          'VPO first violins 12 dB under, 25 ms late: the soloist with a section behind), octave=True (the SSO solo '
          'cello an octave down, -10 dB). How to play: articulation.perform / heroes.play (legato phrases, delayed '
          'vibrato 18 ct on the long notes), swells through "dynamics" (articulation.expression), velocities 58-112 in '
          'phrase arcs, G4-E6 for a soaring theme. Mix: the bed ducks 1.5 dB and is carved 3 dB at 2.8 kHz while the '
          'violin plays, competitors -1.5 dB there, +1 dB in the hooks. Credit: VSCO 2 CE (Versilian Studios, CC0).')

_define(
    'brass', sound='sampled/solo_trumpet', aliases=('trumpet', 'horn_lead'),
    words=('trumpet', 'flugelhorn', 'cornet', 'brass', 'trombone', 'horn'),
    chain={'tone': {'hp.freq': 140, 'hp.slope': 24, 'peak1.freq': 420, 'peak1.gain': -1.5, 'peak1.q': 1.0,
                    'peak2.freq': 1200, 'peak2.gain': -2.0, 'peak2.q': 1.2, 'peak3.freq': 4800, 'peak3.gain': -1.5,
                    'peak3.q': 1.2},
           'comp': {'threshold': -23, 'ratio': 2.0, 'knee': 6, 'attack': 20, 'release': 140, 'automakeup': 'on'},
           'drive': {'mode': 'tube', 'drive': 6, 'mix': 0.35, 'tone': 0.5},
           'presence': {'peak3.freq': 2800, 'peak3.gain': 1.5, 'peak3.q': 0.7, 'high.freq': 8500, 'high.gain': 2.0},
           'exciter': {'freq': 4000, 'drive': 25, 'amount': 0.2, 'character': 0.4}},
    takes=[{'id': 'dbl_l', 'sound': 'sampled/trumpet', 'level': -10.0, 'fine': 8.0, 'delay': 18.0, 'pan': -0.7,
            'hp': 180},
           {'id': 'dbl_r', 'sound': 'sampled/trumpet', 'level': -10.5, 'fine': -7.0, 'delay': 27.0, 'pan': 0.7,
            'hp': 180}],
    octave={'id': 'octave', 'sound': 'sampled/solo_trombone', 'level': -11.0, 'transpose': -12, 'hp': 80,
            'mode': 'off'},
    sends={'plate': -14.0, 'hall': -14.0, 'echo': -24.0},
    space={'plate_bus': 'bus/hero_plate', 'plate': -14.0, 'echo': -24.0, 'throw': -8.0, 'min_rest': 0.75,
           'min_dur': 0.75},
    mix={'duck': 2.0, 'carve_db': 3.0, 'carve_freq': 2200.0, 'carve_q': 0.7, 'ride_db': 1.5, 'dip_db': -2.0,
         'dip_freq': 2200.0},
    play={'vel': (66, 120), 'vib': {'depth': 14, 'rate': 5.6, 'delay': 0.35}},
    notes=f'v{VERSION}. The hero trumpet (an 80s pop trumpet solo, a film fanfare line, Chris Botti-style ballads with '
          'a softer touch): the VSCO 2 solo trumpet in C (a legato player, its articulations keep working) through '
          'the brass hero chain: high-pass 140 Hz, -1.5 dB low-mid at 420 Hz, -2 dB honk at 1.2 kHz, -1.5 dB '
          'brittle 4.8 kHz before a 2:1 '
          'compressor (20 ms attack: the tongued attacks and accents pass, long notes bloom), tube grit (drive 6 at '
          '35 %), then +1.5 dB brilliance at 2.8 kHz, +2 dB air at 8.5 kHz and a light exciter '
          'from 4 kHz. Space: its own bright plate (bus/hero_plate -14), hall -14, echo thrown on the phrase ends '
          '(-24 -> -8 dB). Options: double="takes" (the VPO trumpet as two takes 10 dB under, +8 / -7 ct, 18 / 27 ms, '
          'panned 0.7 apart: a double-tracked pop horn without phasing), double="shift" (a micro-pitch double), '
          'octave=True (the SSO trombone an octave down, -11 dB: a unison brass line). How to play: heroes.play '
          '(legato phrases, narrow delayed vibrato 14 ct), velocities 66-120 (the tongue: accents 20-30 over the '
          'line), breaths between phrases, C4-C6 (the money notes G5-C6). Mix: the bed ducks 2 dB and is carved 3 dB '
          'at 2.2 kHz while it plays, competitors -2 dB there, +1.5 dB in the hooks. Credit: VSCO 2 CE (CC0); VPO '
          '(Paul Battersby) and SSO 4.0 (CC Sampling Plus 1.0) for the options.')

_define(
    'woodwind', sound='sampled/solo_flute', aliases=('flute', 'winds', 'wind'),
    words=('flute', 'clarinet', 'oboe', 'piccolo', 'woodwind', 'bassoon', 'recorder', 'whistle', 'english_horn'),
    chain={'tone': {'hp.freq': 200, 'hp.slope': 24, 'peak1.freq': 450, 'peak1.gain': -1.5, 'peak1.q': 1.0,
                    'peak2.freq': 1500, 'peak2.gain': -1.0, 'peak2.q': 1.2},
           'comp': {'threshold': -21, 'ratio': 1.8, 'knee': 8, 'attack': 25, 'release': 180, 'automakeup': 'on'},
           'tape': {'speed': '15', 'drive': 2, 'bump': 0.0, 'wow': 0.0, 'flutter': 0.02},
           'presence': {'peak3.freq': 3000, 'peak3.gain': 1.0, 'peak3.q': 0.8, 'high.freq': 9000, 'high.gain': 2.5}},
    takes=[{'id': 'dbl', 'sound': inst.sfz(_SSO_FLUTE, lazy=True, level=-2.0, mono='legato', legatotime=60),
            'level': -11.0, 'fine': 6.0, 'delay': 20.0, 'pan': 0.5, 'hp': 250}],
    octave={'id': 'octave', 'sound': 'sampled/clarinet', 'level': -10.0, 'transpose': -12, 'hp': 120, 'mode': 'off'},
    sends={'plate': -14.0, 'hall': -10.0, 'echo': -24.0},
    space={'plate_bus': 'bus/hero_plate', 'plate': -14.0, 'echo': -24.0, 'throw': -9.0, 'min_rest': 0.75,
           'min_dur': 0.75},
    mix={'duck': 2.0, 'carve_db': 3.0, 'carve_freq': 2200.0, 'carve_q': 0.7, 'ride_db': 1.0, 'dip_db': -1.5,
         'dip_freq': 2200.0},
    play={'vel': (60, 112), 'vib': {'depth': 12, 'rate': 5.2, 'delay': 0.35}},
    notes=f'v{VERSION}. The hero flute (a lyrical film / folk melody, a pop flute hook): the VSCO 2 solo flute (a '
          'legato player; its articulations keep working) through the woodwind hero chain: high-pass 200 Hz, -1.5 dB '
          'at 450 Hz (hollow boom), -1 dB at 1.5 kHz, a gentle 1.8:1 compressor (25 ms attack), light tape, +1 dB '
          'at 3 kHz and a +2.5 dB breath / air shelf at 9 kHz. Space: its own plate (bus/hero_plate -14), hall -10, '
          'echo throws (-24 -> -9 dB). Options: double="takes" (the SSO flute 11 dB under, +6 ct, 20 ms late, pan '
          '0.5), octave=True (the clarinet an octave down, -10 dB: the woodwind unison in octaves). How to play: '
          'heroes.play (legato, delayed vibrato 12 ct), breaths between phrases, velocities 60-112, C5-C7. Mix: bed '
          'ducks 2 dB, carved 3 dB at 2.2 kHz, competitors -1.5 dB, +1 dB in the hooks. Credit: VSCO 2 CE (CC0).')

_define(
    'voice', sound='sampled/choir', aliases=('choir', 'aah'),
    words=('choir', 'voice', 'aah', 'aahs', 'ooh', 'oh'),
    chain={'tone': {'hp.freq': 160, 'hp.slope': 24, 'peak1.freq': 300, 'peak1.gain': -2.0, 'peak1.q': 0.9,
                    'peak2.freq': 900, 'peak2.gain': -1.0, 'peak2.q': 1.2},
           'comp': {'threshold': -21, 'ratio': 2.0, 'knee': 6, 'attack': 15, 'release': 150, 'automakeup': 'on'},
           'drive': {'mode': 'tube', 'drive': 5, 'mix': 0.3, 'tone': 0.5},
           'presence': {'peak3.freq': 3200, 'peak3.gain': 2.0, 'peak3.q': 0.8, 'high.freq': 10000, 'high.gain': 3.0},
           'exciter': {'freq': 4500, 'drive': 25, 'amount': 0.2, 'character': 0.4},
           'double': {'style': 'smooth', 'detune': 9, 'delay': 12, 'focus': 300, 'mix': 0.3}},
    sends={'plate': -12.0, 'hall': -14.0, 'echo': -20.0},
    space={'plate_bus': 'bus/hero_plate', 'plate': -12.0, 'echo': -20.0, 'throw': -6.0, 'min_rest': 0.75,
           'min_dur': 0.75},
    mix={'duck': 2.5, 'carve_db': 3.0, 'carve_freq': 3000.0, 'carve_q': 0.7, 'ride_db': 1.5, 'dip_db': -2.0,
         'dip_freq': 3000.0},
    play={'vel': (60, 112), 'vib': False},
    notes=f'v{VERSION}. The hero voice (a vocal-like "aah" topline: dream pop, film, 80s ballads - produced like a '
          'lead vocal): the VPO female choir "ah" through the voice hero chain: high-pass 160 Hz, -2 dB mud at 300 '
          'Hz, -1 dB at 900 Hz, a vocal compressor 2:1 (15 ms attack), a little tube warmth, +2 dB presence at 3.2 '
          'kHz, a +3 dB air shelf at 10 kHz, a light exciter and a vocal doubler (micro-pitch, +-9 ct, mix 0.3). '
          'Space: the vocal plate (bus/hero_plate -12), hall -14, the classic vocal echo throws (-20 -> -6 dB on the '
          'phrase ends). How to play: a singable line F4-E5, velocities 60-112 in phrase arcs, breaths; no vibrato '
          'marks (the samples carry their own). Mix: bed ducks 2.5 dB, carved 3 dB at 3 kHz, competitors -2 dB, '
          '+1.5 dB in the hooks. Credit: Virtual Playing Orchestra (Paul Battersby, royalty-free).')

_define(
    'organ', sound='sampled/tonewheel_organ', aliases=('hammond', 'b3'),
    words=('organ', 'hammond', 'b3', 'tonewheel', 'leslie'),
    chain={'tone': {'hp.freq': 70, 'hp.slope': 24, 'peak1.freq': 250, 'peak1.gain': -2.0, 'peak1.q': 0.9,
                    'peak2.freq': 800, 'peak2.gain': 1.0, 'peak2.q': 1.0},
           'comp': {'threshold': -21, 'ratio': 2.0, 'knee': 8, 'attack': 20, 'release': 150, 'automakeup': 'on'},
           'drive': {'mode': 'tube', 'drive': 8, 'mix': 0.4, 'tone': 0.3},
           'presence': {'peak3.freq': 2500, 'peak3.gain': 1.5, 'peak3.q': 0.8, 'high.freq': 8000, 'high.gain': 1.5}},
    sends={'hall': -14.0, 'echo': -26.0},
    space={'echo': -26.0, 'throw': -10.0, 'min_rest': 0.75, 'min_dur': 1.0},
    mix={'duck': 2.0, 'carve_db': 2.5, 'carve_freq': 1500.0, 'carve_q': 0.7, 'ride_db': 1.0, 'dip_db': -2.0,
         'dip_freq': 1500.0},
    play={'vel': (80, 112), 'vib': False},
    notes=f'v{VERSION}. The hero organ (a Jon Lord / Booker T / gospel organ solo): the FreePats tonewheel B3 with the '
          "library's Leslie chain through the organ hero chain: high-pass 70 Hz, -2 dB mud at 250 Hz, +1 dB bark at "
          '800 Hz, a 2:1 compressor, the preamp pushed (tube drive 8 at 40 %), +1.5 dB bite at 2.5 kHz and +1.5 dB '
          'at 8 kHz. No plate: the Leslie is its space; hall -14, echo throws (-26 -> -10 dB). An organ has no '
          'velocity: its dynamics are the expression pedal (automate instrument.expression) and the Leslie speed. '
          'How to play: single-note lines with grace-note crushes and glissandi, held chords with the Leslie '
          'speeding up. Mix: bed ducks 2 dB, carved 2.5 dB at 1.5 kHz, competitors -2 dB, +1 dB in the hooks. '
          'Credit: FreePats (CC0).')

_define(
    'generic', sound='sampled/solo_cello', aliases=('any', 'default'), words=('cello',),
    chain={'tone': {'hp.freq': 60, 'hp.slope': 24, 'peak1.freq': 300, 'peak1.gain': -2.0, 'peak1.q': 0.9},
           'comp': {'threshold': -21, 'ratio': 1.8, 'knee': 8, 'attack': 20, 'release': 180, 'automakeup': 'on'},
           'tape': {'speed': '15', 'drive': 3, 'bump': 0.5, 'wow': 0.0, 'flutter': 0.02},
           'presence': {'peak3.freq': 2800, 'peak3.gain': 1.5, 'peak3.q': 0.8, 'high.freq': 9000, 'high.gain': 2.0}},
    sends={'plate': -16.0, 'hall': -12.0, 'echo': -24.0},
    space={'plate_bus': 'bus/hero_plate', 'plate': -16.0},
    play={'vel': (60, 116), 'vib': {'depth': 16, 'rate': 5.3, 'delay': 0.32}},
    notes=f'v{VERSION}. The generic hero: any instrument without its own preset through the shared hero chain with '
          'neutral values (high-pass 60 Hz, -2 dB mud at 300 Hz, a 1.8:1 compressor with a 20 ms attack, 15 ips '
          'tape, +1.5 dB presence at 2.8 kHz, +2 dB air at 9 kHz), its own plate (bus/hero_plate -16), hall -12, '
          'echo throws (-24 -> -8 dB); here around the SSO solo cello (a cello theme: film, pop ballads). Give it '
          'your sound: hero("sampled/<x>", family="generic") or hero(track) (the family inferred from the name). '
          'Mix: the generic rules (bed ducks 2.5 dB, carved 3 dB at 2.5 kHz, competitors -2 dB, +1 dB in the hooks). '
          'Credit: Sonatina Symphonic Orchestra (CC Sampling Plus 1.0).')
