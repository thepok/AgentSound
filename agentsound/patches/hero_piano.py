"""Hero pianos: the pop / rock ballad piano that carries a song in front of the mix, like on a hit record (Elton John,
Billy Joel, Adele "Someone Like You", Coldplay "Clocks", 80s power ballads) - the source, its production chain and
its mix rules in one patch.

  sampled/hero_piano          the ballad hero: close, bright but not glassy, even, a big image with a solid centre
  sampled/hero_piano_pop      brighter and tighter for driving 8ths and pop hooks (Clocks, Keane, Viva la Vida)
  layered/hero_piano_strings  the ballad hero with a string section swelling in behind it (the big last chorus)

  carve(song, hero, *bed)     the mix rules: the bed ducks 2.5 dB under the hero and gets a presence dip

THE way to use them: agentsound.heroes.hero(s.track('piano', 'sampled/hero_piano'), bed=[...]) - the patches are the
'piano', 'piano_pop' and 'piano_strings' presets of the hero wrapper (chains BALLAD / POP below as its stages; the
patches are built by heroes.build() and unchanged - tests pin them; hero/piano ... add the 'air' stage), and the
wrapper applies the mix rules (duck + a keyed carve at 2.5 kHz, dips, rides, echo throws) in one logged call.

Design (measured with the audition material and a probe: velocity ladders on C5 / E4 / G3 + a two-handed ballad
passage; validated in scratch copies of songs/_bands/power_ballad and pop_band with the piano as the lead):

* Source: the Salamander Grand (Yamaha C5, 16 velocity layers, release samples, retuned to equal temperament - it
  sits with synths, bass and strings), played by a key-split stack of two instances of the same piano: below C4 the
  harmony layer keeps the recorded stereo (width 0.8-0.9: bass left, chords wide), from C4 up the melody layer is
  narrowed (width 0.4) and re-centred (pan -0.25..-0.3: the Salamander's treble sits right of centre - a B4-B5 melody
  measured -4.8 dB L/R at width 0.4, -1.8..-2.1 dB after the pan, chords -0.2 dB). Big image, solid centre: the
  melody phrase correlation 0.54 (the plain grand: -0.28 there, phasey), chords 0.40 / 43 % wide; one key plays one
  layer (no crossfade: two copies of the same sample would comb-filter), and at C4 both layers image near the centre,
  so the split is seamless.
* Voicing: hammers (inst.sfz hammers=, sfz.hammers) 0.5 on the ballad, 0.15 on the pop piano: the loud layers'
  presence stops rising (C5 velocity 60 -> 127: 2-5 kHz share +1.5 dB, 5-12 kHz +16 dB; the plain Salamander +6.4 /
  +21.8 dB) - bright, not glassy - while the level keeps its 15 dB of velocity range. The pop piano keeps more bite
  (+4.2 / +19 dB) and gets its brightness from the eq.
* Chain: tone eq (body kept, mud cut, presence, air) -> 'catch' compressor (peak, 5 ms: only the hardest hammer
  spikes) -> 'glue' compressor (rms, 20-30 ms attack so every note's attack still speaks - the note dynamics survive,
  the sustain blooms and evens out; keyhp 150 Hz: the left hand does not pump the melody) -> tape (15 ips, a little
  glue, no wow) -> width (monobass: the left hand's lows mono) -> Dimension-D (mono-compatible spread around the
  centre). No chorus on the dry piano (it detunes a piano).
* Space: a plate (the power ballad's 224XL rich plate / the pop plate) plus a little hall; echo THROWS at phrase ends
  (automate 'send.echo'), never a constant echo on a piano.

Level calibration: every patch at gain_db 0 lands at -18.0 LUFS integrated (track node, dry) on its audition material
(`python -m agentsound audition <patch>`; the phrase for the two soloists, chords for the strings stack); LEVELS below
hold the measured corrections. The samples load lazily: without the salamander-grand pack (and vpo-wav for the
strings) the patches register and fail only at use with the pack id to fetch. Version: see VERSION.
"""

from .. import heroes
from . import fx, inst, layer
from . import sampled  # noqa: F401  (sampled/strings must be registered before the layered patch reads it)

VERSION = 1

_SALAMANDER = 'samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz'
SPLIT = 'C4'
"""The key split of the hero stacks: below it the harmony layer ('low': wide, as recorded), from it up the melody
layer ('high': narrowed and re-centred)."""

LEVELS = {'hero_piano': 2.2, 'hero_piano_pop': 3.2, 'hero_piano_strings': 2.6}
"""gain_db per patch: the audition calibration to -18.0 LUFS."""

_CREDIT = 'Credit: Salamander Grand Piano V3 by Alexander Holm, CC-BY 3.0.'

_MIX = ('Mix rules (the hero stands in front): its sections need the bed (pads, strings, choir) 3-5 dB under the piano '
        '(the report\'s "bed ... vs lead"; with the power_ballad / pop_band presets the hero track at gain_db about '
        '-4 / -2 does it) - carve instead of pushing: hero_piano.carve(song, hero, strings, pad[, keys, pluck]) ducks '
        'the bed 2.5 dB while the piano plays and dips 2 dB at 2.5 kHz on it. In a band the piano\'s left hand shares '
        'the bassist\'s octave: keep it above E2 or open the eq there (.but_fx("tone", **{"hp.freq": 90})). Echo throws '
        'on the last note of a phrase: a send "echo" at -60 and automate "send.echo" to -2..-4 dB for 2 beats.')

_PLAY = ('How to play (a pianist, never a bare line - recipes/HUMAN_FEEDBACK.md): arrange the melody with '
         'pianist.arrange(melody, prog, bpm=, key=, style="ballad", devices={"close": 2, "octave": 2, "thirds": 1.5, '
         '"sixths": 1.5, "drop2": 1}) - pop voicings rather than jazz clusters; climax=True for the last chorus '
         '(octaves, locked hands) - with humanize.touch(melody, lo, hi) first: verse 55-95, chorus 75-118. Melody '
         'C4-C6 (the centred layer), left hand broken chords / 8th pulses A1-C4 with their own accents (the 1 and '
         'the 3 up, off-beats x0.75-0.85). The chain evens things out by ~1 dB of note-to-note contrast: write the '
         'accents 20-30 velocity apart and the flat_dynamics ear stays quiet. Pedal: instrument.pedal steps at each '
         'chord change (lift and re-press just after the change); rolled chords (clip.strum 25-40 ms) for intro and '
         'final chords.')

_TWEAK = ('Tweaks: .layer("high", width=0.6) (a wider melody), .layer("low", width=1.0) (the full recorded spread), '
          '.but_fx("glue", ratio=3) (a squashier 80s ballad), .but_fx("dimension", mix=0) (a drier, more natural '
          'piano), .but_fx("tone", **{"high.gain": 5}) (more air).')


def _eq(name=None, **bands):
    return fx.eq({k.replace('__', '.'): v for k, v in bands.items()}, **({'name': name} if name else {}))


def _salamander(level: float, hammers: float, width: float, pan: float = 0.0):
    return inst.sfz(_SALAMANDER, lazy=True, level=level, hammers=hammers, width=width, pan=pan, polyphony=160)


def _keys(level: float, hammers: float, low=(0.9, 0.0), high=(0.4, -0.25)):
    """The two key layers of one piano: (width, pan) below SPLIT and from SPLIT up."""
    return (layer(_salamander(level, hammers, *low), 'low', keys=('A0', 'B3')),
            layer(_salamander(level, hammers, *high), 'high', keys=(SPLIT, 'C8')))


# The hero chains as agentsound.heroes stages (the shared order: tone -> catch -> comp -> tape -> width ->
# dimension); the fx keep their names ('tone', 'catch', 'glue') for .but_fx().
BALLAD = {
    'tone': {'name': 'tone', 'hp.freq': 45, 'hp.slope': 24, 'peak1.freq': 280, 'peak1.gain': -3.0, 'peak1.q': 0.8,
             'peak2.freq': 2000, 'peak2.gain': 2.5, 'peak2.q': 0.8, 'high.freq': 10000, 'high.gain': 3.0},
    'catch': {'name': 'catch', 'threshold': -10, 'ratio': 3, 'attack': 5, 'release': 60, 'knee': 6},
    'comp': {'name': 'glue', 'threshold': -24, 'ratio': 2.0, 'attack': 30, 'release': 350, 'knee': 10,
             'detector': 'rms', 'keyhp': 150, 'automakeup': 'on'},
    'tape': {'speed': '15', 'drive': 3, 'bump': 1.0, 'wow': 0.0, 'flutter': 0.02},
    'width': {'width': 1.2, 'monobass': 150},
    'dimension': {'mode': 2, 'mix': 0.5},
}
POP = {
    'tone': {'name': 'tone', 'hp.freq': 100, 'hp.slope': 24, 'peak1.freq': 350, 'peak1.gain': -3.5, 'peak1.q': 0.9,
             'peak3.freq': 3000, 'peak3.gain': 2.5, 'peak3.q': 0.8, 'high.freq': 9000, 'high.gain': 4.0},
    'catch': {'name': 'catch', 'threshold': -12, 'ratio': 3, 'attack': 5, 'release': 50, 'knee': 6},
    'comp': {'name': 'glue', 'threshold': -24, 'ratio': 2.0, 'attack': 20, 'release': 150, 'knee': 8,
             'detector': 'rms', 'keyhp': 150, 'automakeup': 'on'},
    'tape': {'speed': '15', 'drive': 5, 'bump': 0.0, 'wow': 0.0, 'flutter': 0.02},
    'width': {'width': 1.1, 'monobass': 200},
    'dimension': {'mode': 3, 'mix': 0.45},
}


def _ballad_chain():
    return heroes.chain(BALLAD)


def _pop_chain():
    return heroes.chain(POP)


# the piano heroes' mix rules for heroes.hero() (carve() below keeps the old static-dip form)
_PIANO_MIX = {'duck': 2.5, 'duck_threshold': -45.0, 'duck_attack': 15.0, 'duck_hold': 40.0, 'duck_release': 400.0,
              'carve_db': 2.0, 'carve_freq': 2500.0, 'carve_q': 0.9, 'ride_db': 1.0, 'dip_db': -2.0,
              'dip_freq': 2500.0, 'dip_q': 0.9}
_PIANO_SPACE = {'echo': -60.0, 'throw': -3.0, 'min_rest': 0.75, 'min_dur': 0.5}
_PIANO_PLAY = {'player': 'piano', 'vel': (55, 118)}


def _preset(name: str, patch: str, source, stages: dict, *, sends: dict, notes: str, audition: dict, **kw) -> None:
    heroes.define(name, family='piano', source=source, chain=stages, named=False,
                  gain_db=LEVELS[patch.split('/')[1]], sends=sends, notes=notes, audition=audition, patch=patch,
                  mix=dict(_PIANO_MIX), space=dict(_PIANO_SPACE), play=dict(_PIANO_PLAY), **kw)
    heroes.register(name)


def carve(song, hero, *others, duck: float = 2.5, dip: float = -2.0, dip_freq: float = 2500.0,
          attack: float = 15.0, release: float = 400.0) -> None:
    """The hero's mix rules in one call: every track / bus in `others` (the bed - pads, strings, choir - and the
    comping keys / plucks that share the piano's register) ducks `duck` dB while the hero plays (song.sidechain keyed
    by the hero track: 2-3 dB, attack 15 ms, release 400 ms - a gentle make-room, not a pump) and gets a `dip` dB
    presence dip at `dip_freq` (Q 0.9, an eq named 'hero_dip') where the piano's hammer and melody speak. duck=0 /
    dip=0 skip either. The hero's fader stays the song's: set it so the bed sits 3-5 dB under the hero in its
    sections (the report's 'bed ... vs lead')."""
    if not others:
        return
    if duck:
        song.sidechain(*others, key=hero, depth=duck, attack=attack, hold=40, release=release, threshold=-45)
    if dip:
        for o in others:
            o.add_fx(fx.eq({'peak2.freq': dip_freq, 'peak2.gain': dip, 'peak2.q': 0.9}, name='hero_dip'))


_preset(
    'piano', 'sampled/hero_piano',
    lambda: list(_keys(-3.0, 0.5)),
    BALLAD,
    user_gain_db=0.1, words=('piano', 'grand', 'salamander', 'upright'),
    measured={'lufs': -18.0, 'melody_correlation': 0.54, 'c5_vel60_127_level_db': 15.5, 'presence_rise_db': 1.5,
              'power_ballad_bed_vs_piano_db': -4.6, 'note_dynamics_db': 3.7},
    sends={'plate': -7, 'hall': -16},
    notes=f'v{VERSION}. The ballad hero piano (Elton John, Billy Joel, Adele "Someone Like You", the 80s power ballad '
          'that opens on piano): the Salamander Grand as a key-split stack - below C4 the recorded stereo (width 0.9: a '
          'wide, warm left hand), from C4 up a melody layer narrowed to width 0.4 and re-centred (pan -0.25) - with '
          'softened hammers (0.5: loud notes bloom, they do not turn glassy). Chain: eq (high-pass 45 Hz, -3 dB at '
          '280 Hz, +2.5 dB at 2 kHz, +3 dB air shelf at 10 kHz), "catch" compressor (peak, -10 dB, 3:1, 5 ms: only the '
          'hardest hits), "glue" compressor (rms, -24 dB, 2:1, 30 / 350 ms: the sustain blooms and stays in front, '
          'the attacks keep their accents), 15 ips tape (drive 3), width 1.2 with the lows mono below 150 Hz, '
          'Dimension-D mode 2 (mix 0.5). Space: plate -7 (the characteristic lush plate), hall -16. Measured: '
          'melody phrase correlation 0.54, 31 % wide, L/R -2.1 dB; chords correlation 0.40, 43 % wide; C5 velocity '
          '60 -> 127 +15.5 dB level, presence +1.5 dB (the plain grand +6.4). In songs/_bands/power_ballad with the '
          'piano as the lead (gain_db -4, carve on strings + pad): bed 4.6 dB under the piano in the chorus (the '
          'preset piano: 1.6, sampled/piano_lead: 3.9), the piano 36 % of the chorus\'s 1-5 kHz band (18 % / 25 %), '
          'correlation above 150 Hz 0.32 (0.14), crest 16.6 dB (19.0), note dynamics 3.7 dB per phrase, no '
          'masking / reverb warning (the preset: strings mask the drums, the echo unheard). ' + _MIX + ' ' + _PLAY + ' ' + _TWEAK + ' ' + _CREDIT + ' Measured -18.0 LUFS '
          '(audition phrase).',
    audition={'notes': 'phrase'})

_preset(
    'piano_pop', 'sampled/hero_piano_pop',
    lambda: list(_keys(-3.0, 0.15, low=(0.8, 0.0), high=(0.4, -0.3))),
    POP,
    user_gain_db=1.0, aliases=('pop_piano',),
    measured={'lufs': -18.0, 'c5_vel60_127_level_db': 15.3, 'presence_rise_db': 4.2, 'phrase_correlation': 0.60,
              'note_dynamics_db': 4.0},
    sends={'plate': -12, 'hall': -20},
    notes=f'v{VERSION}. The bright, tight pop hero piano for driving 8ths and piano hooks (Coldplay "Clocks", Keane, '
          'Viva la Vida, modern pop-rock and piano-led radio pop): the same key-split Salamander (left hand width '
          '0.8, melody layer width 0.4 re-centred at pan -0.3), hammers only 0.15 (the hard layers keep their bite). '
          'Chain: eq (high-pass 100 Hz: the bassist owns the bottom; -3.5 dB at 350 Hz, +2.5 dB at 3 kHz, +4 dB air '
          'shelf at 9 kHz), "catch" (peak, -12 dB, 3:1, 5 ms), "glue" (rms, -24 dB, 2:1, 20 / 150 ms: a faster '
          'release for 8th-note pulses), 15 ips tape (drive 5, no head bump), width 1.1 with the lows mono below 200 Hz, Dimension-D '
          'mode 3 (mix 0.45). Space: a shorter send - plate -12, hall -20 - and echo throws. Measured: C5 velocity '
          '60 -> 127 +15.3 dB, presence +4.2 dB (bright, still under the plain grand\'s +6.4), loud-hit centroid '
          '1.19 kHz (hero_piano 0.92); phrase correlation 0.60, 25 % wide. In songs/_bands/pop_band with the piano '
          'as the lead (a Clocks-style 3+3+2 8th ostinato + the chorus line, carve on pad / keys / pluck): the '
          'preset\'s lead piano read "very wide" (chorus correlation -0.01 above 150 Hz) and "low mids high"; the '
          'hero: correlation 0.51-0.56 above 150 Hz, no balance warning, chorus crest 18.3 dB (19.3), the piano 64 % '
          'of the chorus\'s 1-5 kHz band (the preset 65 %, at 0.3 dB more level), note dynamics 4.0 dB.For the ostinato: accents 25-35 velocity over the passing 8ths '
          '(vel_pattern([1, .62, .72, .92, .62, .72, .86, .66], grid="1/8")), the left hand on 1 and the "and" of 2 '
          'and 3 (C3-E4, clear of the bass). ' + _MIX + ' ' + _PLAY + ' ' + _TWEAK + ' ' + _CREDIT +
          ' Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'})

_preset(
    'piano_strings', 'layered/hero_piano_strings',
    lambda: list(_keys(-3.0, 0.5)) + [
        layer('sampled/strings', 'strings', level=-14, delay=70, pedal=False,
              fx=[_eq(hp__freq=180, hp__slope=24, peak3__freq=3000, peak3__gain=-3.0, peak3__q=0.8)])],
    BALLAD,
    user_gain_db=0.1,
    measured={'lufs': -18.0, 'strings_under_piano_lu': 5.0},
    sends={'plate': -10, 'hall': -12},
    notes=f'v{VERSION}. The ballad hero with strings behind it on one track (the last chorus of a power ballad, film '
          'and pop-piano climaxes): sampled/hero_piano\'s two key layers + the VPO string section (sampled/strings) '
          'at -14 dB, 70 ms late (the hammer speaks first, the section swells in), ignoring the sustain pedal (it '
          'follows the keys while the piano rings on), high-passed at 180 Hz and -3 dB at 3 kHz (under the piano\'s '
          'presence); the whole stack through the hero chain (the glue compressor also tucks the strings under each '
          'piano attack). On held chords the strings alone measure ~5 LU under the piano; on a moving melody they are '
          'a sheen (short notes never reach the section\'s attack). Hold chords through the bar; automate '
          'instrument.layers.strings.level (-20 -> -9) to bring the section in over the last chorus; .layer("strings", '
          'keylo=60) keeps them on the right hand only. Band strings on their own track then play less (or leave). '
          + _MIX + ' ' + _PLAY + ' ' + _TWEAK + ' .layer("strings", level=-9) (a lusher section). ' + _CREDIT + ' Virtual Playing Orchestra strings (Paul Battersby, royalty-free). '
          'Measured -18.0 LUFS (audition chord).',
    audition={'notes': 'chord'})
