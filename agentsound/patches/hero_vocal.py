"""The vocal hero: a SUNG lead vocal (agentsound.singer) produced like a record's lead vocal.

    vox = singer.sing(s, melody, lyrics, at=verse)
    hero(vox.track, family='vocal', bed=[pad, strings], competitors=[keys, guitar])

The chain (VOCAL_ORDER: heroes.ORDER with the de-esser after the boosts), voiced on the DiffSinger voicebanks' renders:
  tone      high-pass 90 Hz (24 dB/oct: rumble, the vocoder's low-frequency noise between phrases), -2 dB of mud at
            280 Hz, -1 dB of nasal honk at 1 kHz
  comp      3:1, 8 ms attack, 120 ms release, soft knee: the vocal level nearly constant (a sung line has 10-15 dB
            between its soft and loud words), the consonants still pass
  drive     a touch of tube (density, no audible distortion)
  presence  +2 dB at 3.5 kHz (words: the intelligibility band 2-5 kHz) and a +2.5 dB air shelf at 11 kHz
  deess     the de-esser (engine 'deesser'): s / t / sh peaks above 7 kHz down by up to 8 dB (split band: the vowel's
            brightness stays) - AFTER the compressor, the drive and the presence / air boosts that would bring the
            sibilants back (measured: s / sh vs their vowel 0.5-1 dB lower, the codas unchanged). A male voice:
            hero(..., deess={'freq': 5500})
  air       the breath stage (heroes.AIR): the singer's within-note air lands after the compressor
Space: DRY and CLOSE by default (recipes/HUMAN_FEEDBACK.md "Vocals") - its own short plate (bus/vocal_plate: RT60 1.0 s,
60 ms pre-delay) at the genre's level (VOCAL_SPACE: pop -21 / rock -20 dB = the return ~16 / 15 LU under the dry
voice, jazz / ballad -25 dB = ~20 LU), no constant echo, echo only as deliberate throws on the last phrase end of each
section (pop / rock; none for jazz / ballad / classical), no band hall / room inherited. hero(..., genre=) picks the
genre's space; without a genre the singing style's (singer style 'jazz' -> the jazz space). Overridable: plate= /
echo= / throws=, vox.track.send(bus, dB) (a send the song sets stays).
Mix: the bed ducks 2.5 dB and steps out of 3 kHz while the vocal sings; competitors (keys, rhythm guitars) -2.5 dB
at 3 kHz; +1.5 dB in the hooks.
The preset has no default sound (a sung vocal is rendered per song): use it on a vocal track (hero(track, ...)).
Doubles and harmonies (singer.double / singer.harmony) take the same chain with the mix rules off:
hero(dbl.track, family='vocal', ride=False, throws=False, duck=False, carve=False, dips=False) - the same dry space.
Grit (the guitar amp on the voice): hero(vox.track, family='vocal', grit='light' | 'crunch' | 'megaphone') - see GRIT
below; level-matched, the consonants kept by the untouched clean path (light / crunch are parallel).
"""

from __future__ import annotations

from .. import heroes
from . import Patch, fx, register

VERSION = 2

# ------------------------------------------------------------------------------------------------ grit
# "kann man die Stimmen wohl mit dem Gitarren-Amp rauer machen?" - the vocal through the engine's tube 'amp' (the
# guitar heroes' head), three amounts (hero(vox.track, family='vocal', grit='light' | 'crunch' | 'megaphone')):
#   light / crunch  PARALLEL: a post-fader send (after the whole vocal chain: compressed, de-essed) into the bus
#                   '<track>_grit' = the band 300 Hz-5 kHz (24 dB/oct each side: no boomy lows into the amp, no
#                   s / t hiss to fizz) -> the amp (2 stages, bright cap off, mid-forward british stack, treble and
#                   presence down) -> a speaker roll-off (hp 250, lp 4.5 kHz 24 dB/oct, +1 dB at 1.5 kHz). It is
#                   blended UNDER the clean vocal, which stays untouched: the consonants (HUMAN_FEEDBACK: "out
#                   verliert sein t") come through the clean path, the grit only roughens the vowels. The send
#                   cancels the track's fader (synced when the song compiles): the amp always sees the chain's own
#                   level, so the drive is the calibrated one (sine at the vocal's -20 dBFS RMS: THD -10 dB light,
#                   -6.5 dB crunch = saturated) and each amp's output is set so the bus at 0 dB matches the clean
#                   vocal; 'blend' puts it under (light -9 dB, crunch -5 dB) and the vocal track is trimmed so clean +
#                   grit lands at the clean level (heroes.grit_trim with the measured correlation rho).
#   megaphone       INSERT: the whole voice through a bullhorn - band-limited twice (550 Hz-3.8 kHz, 48 dB/oct) with
#                   the horn's 1.8 kHz resonance, the amp driven hard, the horn band again after it; no air shelf.
# Measured on songs/_demo_vocal (Hanami, grit_ab.py): GRIT_MEASURED.
GRIT_BAND = {'hp.freq': 300, 'hp.slope': 24, 'lp.freq': 5000, 'lp.slope': 24}
GRIT_SPEAKER = {'hp.freq': 250, 'hp.slope': 12, 'lp.freq': 4500, 'lp.slope': 24, 'peak2.freq': 1500,
                'peak2.gain': 1.0, 'peak2.q': 0.8}
GRIT_AMP = {
    'light': dict(stages=2, gain=3.5, bright=0.0, tight=300.0, bass=3.0, mid=7.0, treble=4.0, presence=3.0,
                  resonance=3.0, master=4.0, sag=0.3, stack='british', output=-1.4),
    'crunch': dict(stages=2, gain=6.0, boost=4.0, bright=0.0, tight=300.0, bass=3.0, mid=7.5, treble=4.0,
                   presence=3.0, resonance=3.0, master=6.0, sag=0.35, stack='british', output=-2.4),
}
MEGAPHONE_BAND = {'hp.freq': 550, 'hp.slope': 24, 'lp.freq': 3800, 'lp.slope': 24}
MEGAPHONE_AMP = dict(stages=2, gain=6.5, bright=0.0, tight=450.0, bass=2.0, mid=8.0, treble=5.0, presence=4.0,
                     resonance=2.0, master=6.0, sag=0.2, stack='british', output=-5.9)

GRIT = {
    'light': {'mode': 'parallel', 'bus': 'bus/vocal_grit_light', 'blend': -9.0, 'rho': 0.1},
    'crunch': {'mode': 'parallel', 'bus': 'bus/vocal_grit_crunch', 'blend': -5.0, 'rho': 0.0},
    'megaphone': {'mode': 'insert', 'trim': -0.4, 'stages': {
        'amp': [fx.eq({**MEGAPHONE_BAND, 'peak2.freq': 1800, 'peak2.gain': 5.0, 'peak2.q': 1.4}, name='horn_in'),
                fx.eq(dict(MEGAPHONE_BAND), name='horn_in2'),
                fx.amp(**MEGAPHONE_AMP, name='amp'),
                fx.eq({'hp.freq': 450, 'hp.slope': 24, 'lp.freq': 4000, 'lp.slope': 24, 'peak2.freq': 2200,
                       'peak2.gain': 3.0, 'peak2.q': 1.2}, name='horn')],
        'presence': {'high.gain': 0.0}}},
}
"""The vocal hero's grit amounts (heroes.GRIT_MODES, heroes.grit_spec): blend = the grit bus's level under the clean
vocal, rho = how correlated grit and clean are (measured at blend 0: light +3.5 dB summed -> 0.1, crunch +2.9 dB ->
0.0; the trim follows: heroes.grit_trim), trim = the track's level change (megaphone: measured)."""
GRIT_MEASURED = {
    # songs/_demo_vocal/grit_ab.py (Hanami, the same take over the band): the lead vocal as heard (its stem + its grit
    # bus) vs the clean hero (LU), the mix vs clean (LU), the clean vocal's own share of the mix's 2.5-6 kHz word band
    # (clean 73 %), the word-final consonants vs their vowel at 2-8 kHz vs clean (median / worst dB; 'out' /t/)
    'light': {'vocal_lu': 0.0, 'mix_lu': -0.1, 'presence_pct': 69, 'coda_db': (0.0, -2.0), 'out_t_db': -0.4},
    'crunch': {'vocal_lu': -0.2, 'mix_lu': -0.1, 'presence_pct': 67, 'coda_db': (0.0, -3.7), 'out_t_db': -0.4},
    'megaphone': {'vocal_lu': -0.3, 'mix_lu': 0.5, 'presence_pct': 87, 'coda_db': (0.0, -8.4), 'out_t_db': 1.4},
    'tiger_crunch': {'vocal_lu': -0.5, 'mix_lu': -0.2, 'presence_pct': 65, 'coda_db': (0.5, -1.9), 'out_t_db': -0.6},
    # singer.diction (the takes' timelines): no coda_buried in any variant; clicks 0 everywhere
    # NOTE (fix/dry-vocals): grit_ab.py placed the codas offset_s (~0.3-0.6 s) too early (the timeline's times count
    # from the first note, not from the take file's start) - the coda_db / out_t_db numbers above measured the wrong
    # windows; the scripts are fixed, the numbers wait for a re-run (TODO.md)
}
"""The A/B numbers of songs/_demo_vocal/grit_ab.py (out/grit_ab/grit_ab.json). The megaphone's mix is +0.5 LU at a
matched vocal: its flat, band-limited voice has less crest for the master limiter to catch, and the plate (filtered
450 Hz-9.5 kHz) gets more of it. Its worst coda is a nasal ('and' /n/: its energy is below the horn band)."""

for _amount in ('light', 'crunch'):
    _g = GRIT[_amount]
    register(Patch(
        f'bus/vocal_grit_{_amount}',
        fx=[fx.eq(dict(GRIT_BAND), name='band'), fx.amp(**GRIT_AMP[_amount], name='amp'),
            fx.eq(dict(GRIT_SPEAKER), name='speaker')],
        notes=f"v1. The vocal hero's parallel grit return ({_amount}): the band 300 Hz-5 kHz -> the tube amp "
              f"(gain {GRIT_AMP[_amount]['gain']:g}, 2 stages, mid-forward, no bright cap) -> a speaker roll-off "
              f"(lp 4.5 kHz). Use: hero(vox.track, family='vocal', grit='{_amount}') (makes the bus "
              f"'<track>_grit', the send, the blend and the level trim); by hand: g = s.bus('vocal_grit', "
              f"'bus/vocal_grit_{_amount}', gain_db={_g['blend']:g}); vocal.send(g, 0); vocal.gain_db -= "
              f"{-heroes.grit_trim(_g['blend'], _g['rho']):.2f} (clean + grit at the clean level)."))

# ------------------------------------------------------------------------------------------------ space
# "der Gesang hat immer viel Hall und/oder Reverb, er klingt nicht trocken" (recipes/HUMAN_FEEDBACK.md "Vocals"): a
# sung vocal sits DRY and CLOSE by default. Its own short plate (bus/vocal_plate: 60 ms pre-delay - every syllable's
# consonant and vowel onset is heard dry first -, RT60 1.0 s, the send band 300 Hz-8 kHz: no low mud, no s / t splash
# in the tail), no constant echo (echo only as deliberate throws: the last phrase end of each section, pop / rock),
# no band hall / room inherited (heroes 'inherit': False). Levels: the plate's return under the dry vocal (LU, measured
# with songs/_demo_vocal/wetness.py: every non-vocal track muted, BS.1770 over the same gated blocks) - VOCAL_SPACE.
VOCAL_PLATE_DECAY = 1.0
VOCAL_PLATE_PREDELAY = 60
register(Patch(
    'bus/vocal_plate',
    fx=[fx.eq({'hp.freq': 300, 'hp.slope': 24, 'lp.freq': 8000, 'lp.slope': 24}),
        fx.reverb(type='plate', mix=1.0, decay=VOCAL_PLATE_DECAY, predelay=VOCAL_PLATE_PREDELAY, lowcut=300,
                  highcut=9000, damping=7000, moddepth=0.3, early=0.0, width=0.9),
        fx.eq({'output': 9.0})],
    notes='v1. The sung vocal\'s own short plate (the vocal hero\'s space): the send band-limited 300 Hz-8 kHz (24 '
          'dB/oct: no mud, no sibilant splash), an EMT-style plate with RT60 1.0 s and a 60 ms pre-delay (every '
          'syllable is heard dry first, the bloom follows), width 0.9, calibrated like bus/hero_plate (+9 dB '
          'output). The vocal hero sends it 16-20 LU under the dry voice (hero_vocal.VOCAL_SPACE): felt in the gaps, '
          'never a wash. Tweak: but_fx("reverb", decay=0.8-1.6, predelay=40-90).'))

VOCAL_SPACE = {
    # genre: (plate send dB, the return under the dry vocal it measures: LU) - the jazz / ballad numbers are lower
    # (intimate: a sparse band exposes every tail in the gaps; a close-miked club / ballad vocal), pop / rock a little
    # more (a dense band masks the return while the voice sings: only the tails in the gaps read as space)
    'pop': -21.0, 'rock': -20.0, 'jazz': -25.0, 'ballad': -25.0,
}
"""The vocal plate's send per genre (dB). Targets (the return under the dry vocal, LU): pop 16, rock 15, jazz /
ballad 20 - see VOCAL_SPACE_MEASURED."""
VOCAL_SPACE_MEASURED = {
    # songs/_demo_vocal/wetness.py (every non-vocal track muted): the returns vs the dry vocal (LU), the returns 250 ms
    # after a phrase end vs the phrase (dB) and the time voice + returns take to fall 30 dB; before -> after
    'jane-street-bossa (jazz)': {'before': {'wet_lu': -9.7, 'plate_lu': -10.4, 'room_lu': -18.6, 'tail_250_db': -15.8,
                                            'decay30_s': 1.0},
                                 'after': {'wet_lu': -20.6, 'plate_lu': -20.6, 'tail_250_db': -40.4, 'decay30_s': 0.1}},
    '_demo_vocal (pop)': {'before': {'wet_lu': -3.9, 'plate_lu': -5.9, 'echo_lu': -8.1},
                          'after': {'wet_lu': -14.7, 'plate_lu': -16.6, 'echo_lu': -19.1}},
    '_demo_vocal_rock (rock, TIGER)': {'before': {'wet_lu': -5.1, 'plate_lu': -5.5, 'echo_lu': -16.9, 'tail_250_db': -9.2},
                                       'after': {'wet_lu': -15.1, 'plate_lu': -15.5, 'echo_lu': -25.5,
                                                 'tail_250_db': -31.5}},
}
"""The return vs the dry vocal (LU) and the tail after a phrase end, measured per song (wetness.py). Why these
targets: a return within ~10 LU of the voice is heard as a wash on every held vowel (the old -4..-10 LU); 15-18 LU
under it, a dense pop / rock band masks the return while the voice sings and only a short tail is felt in the gaps
(depth without distance); a sparse jazz trio / ballad exposes every gap, so 18-22 LU (a close-miked voice in a club:
a high direct-to-reverberant ratio). The 60 ms pre-delay keeps every syllable's onset dry (clarity), the 1 s RT60 lets
the tail die within ~0.1-0.3 s of a phrase end, and a dry voice is what grit / distortion should take."""


def _space(g: str) -> dict:
    jazzy = g in ('jazz', 'ballad', 'classical', 'piano')
    return {'plate': VOCAL_SPACE.get(g, VOCAL_SPACE['jazz' if jazzy else 'pop']), 'echo': None, 'throw': -10.0,
            'throws': not jazzy, 'throw_scope': 'sections'}


VOCAL_ORDER = ('tone', 'catch', 'comp', 'amp', 'drive', 'tape', 'presence', 'deess', 'exciter', 'chorus', 'double',
               'width', 'dimension', 'echo', 'air')
"""The vocal's chain order: the de-esser AFTER the drive and the presence / air boosts (+2 dB at 3.5 kHz, +2.5 dB
shelf at 11 kHz), which would otherwise bring the sibilants back (the chain audit); the breath stage last."""

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
    sends={'plate': VOCAL_SPACE['pop']},
    order=VOCAL_ORDER,
    space={'plate_bus': 'bus/vocal_plate', 'plate': VOCAL_SPACE['pop'], 'echo': None, 'throw': -10.0,
           'min_rest': 0.75, 'min_dur': 0.75, 'throws': True, 'throw_scope': 'sections', 'inherit': False,
           'genres': {g: _space(g) for g in ('pop', 'rock', 'jazz', 'ballad', 'classical', 'piano', 'film',
                                              'synthwave', 'dreamwave', 'darksynth', 'default')}},
    mix={'duck': 2.5, 'carve_db': 3.0, 'carve_freq': 3000.0, 'carve_q': 0.7, 'ride_db': 1.5, 'dip_db': -2.5,
         'dip_freq': 3000.0},
    play={'vel': (64, 110), 'vib': False},
    grit=GRIT,
    notes=f'v{VERSION}. The vocal hero (a sung lead vocal, agentsound.singer): high-pass 90 Hz, -2 dB mud at 280 Hz, '
          '-1 dB at 1 kHz, a vocal compressor 3:1 (8 ms attack), a '
          'touch of tube, +2 dB presence at 3.5 kHz, a +2.5 dB air shelf at 11 kHz, the de-esser after the boosts, '
          'the breath stage. Space: dry and close - its own short pre-delayed plate (bus/vocal_plate, 16 LU under the '
          'voice for pop, 15 rock, 20 jazz / ballad), no constant echo, echo throws only on section ends (pop / rock), '
          'no band hall / room. Mix: bed ducks 2.5 dB, '
          'carved 3 dB at 3 kHz, competitors -2.5 dB, +1.5 dB in the hooks. Play it with agentsound.singer (sing, '
          'double, harmony); a male voice: deess={"freq": 5500}. Rougher: grit="light" / "crunch" (a parallel '
          'tube-amp bus 300 Hz-5 kHz, -9 / -5 dB under the clean vocal) or "megaphone" (the whole voice band-limited '
          'and driven), level-matched.',
)
