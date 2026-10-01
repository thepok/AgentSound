"""Sampled guitars and basses (instrument 'sampler'): acoustic, nylon, archtop, hollowbody and solidbody electrics
(pre-amped sets and DI guitars through amp + cabinet chains), metal rhythm / lead, electric basses (finger, pick,
slap, flatwound, hollowbody, short-scale, a Bass VI), a double bass and an electric upright.

  acoustic:  sampled/steel_guitar sampled/concert_guitar sampled/archtop_guitar
  electric:  sampled/jazz_guitar sampled/clean_guitar sampled/dist_guitar sampled/fuzz_guitar (pre-amped FreePats FSBS)
             sampled/gretsch_guitar sampled/hofner_guitar (hollowbodies, keyswitched: twang / staccato / hammer-on or
             behind the bridge / palm mute)
  amped DI:  sampled/rock_guitar sampled/crunch_guitar sampled/metal_guitar sampled/blues_guitar
             sampled/jangle_guitar sampled/lead_guitar sampled/archtop_electric (a DI guitar + amp / cabinet chain,
             palm mute and dead note keyswitches)
  metal:     sampled/metal_rhythm (real power chords + chugs) sampled/metal_lead
  basses:    sampled/finger_bass sampled/rock_bass sampled/round_bass sampled/slap_bass sampled/flatwound_bass
             sampled/picked_bass sampled/hollow_bass sampled/bass_vi sampled/short_scale_bass
  upright:   sampled/sneaky_bass sampled/electric_upright (more double basses: sampled/upright_bass in sampled.py)

Articulations are keyswitches inserted by the compiler: clip.articulate('palm', span=(a, b)), .articulate('dead',
where=...), .articulate('staccato') ... (agentsound/articulation.py; the notes of each patch name them). Where a pack
recorded an articulation it is the real sample (Karoryfer ghost notes, staccato, behind-the-bridge, hammer-ons,
muted plucks); palm mutes / dead notes of the DI sets and bass staccato / mute are the plain notes damped and
filtered (sfz_multi 'zone' overrides, like the band presets' DI guitars in bandlib/rock.py).

Every patch reads its samples only when a song renders it (lazy): importing the library needs no samples, and a
patch whose pack is missing fails at use with the pack id to fetch (`python -m agentsound samples fetch <id>`).
Level calibration as sampled.py: every patch at gain_db 0 lands at about -18 LUFS integrated (track node, dry
of sends, with its insert fx) playing its audition material (`python -m agentsound audition <patch>`); the amped DI
patches keep their amp input level (the drive) and calibrate with a last 'trim' utility instead. Uneven packs are
evened out where it mattered (velocity curves for normalised layers, a key-gain curve for Sneakybass); what is left
is in each patch's notes. Licences
differ per pack (`python -m agentsound samples -v`): the Karoryfer and FreePats FSBS packs are CC0, FreePats FSS is
GPL-3.0 with the FreePats exception (music made with it is free), the two Fiedler packs are CC-BY-NC-SA 3.0 with a
"commercial music production allowed" exception (credit Markus Fiedler), SampleRadar is royalty-free for music but
may not be redistributed. Version: see VERSION.
"""

from ..theory import ComposeError
from . import Patch, fx, get, inst, register
from . import space_ir as _space_ir  # noqa: F401 - registers the cab/* chains the amped DI guitars copy

VERSION = 2   # v2: the amped DI guitars and sampled/rock_bass on the engine's tube amp (the rock pass)

LEVELS = {
    # acoustic
    'steel_guitar': -2.5, 'concert_guitar': 1.7, 'archtop_guitar': 8.5,
    # pre-amped electrics
    'jazz_guitar': -4.5, 'clean_guitar': -3.4, 'dist_guitar': -7.1, 'fuzz_guitar': -10.5,
    'gretsch_guitar': 13.0, 'hofner_guitar': 9.6,
    # DI + amp
    'rock_guitar': -5.0, 'crunch_guitar': -5.6, 'metal_guitar': -3.4, 'blues_guitar': -5.4, 'jangle_guitar': -6.3,
    'lead_guitar': -6.4, 'archtop_electric': -3.2,
    # metal
    'metal_rhythm': -6.1, 'metal_lead': -9.5,
    # basses
    'finger_bass': 6.0, 'rock_bass': 2.6, 'round_bass': 5.8, 'slap_bass': 3.0, 'flatwound_bass': 10.6,
    'picked_bass': 1.3, 'hollow_bass': 2.7, 'bass_vi': 1.6, 'short_scale_bass': -2.2,
    'sneaky_bass': -0.5, 'electric_upright': 11.0,
}
# The amped DI patches: the instrument level is the amp's input (the DI sets are recorded at very different levels -
# FSBS ~13 dB hotter than Emilyguitar / Shinyguitar - and the saturator's drive depends on it; as bandlib/rock.py
# DI_LEVEL: open power chords at velocity 105 -> ~-8 LUFS DI each); LEVELS holds their output trim instead.
DI_LEVEL = {'fsbs': 4.0, 'emily': 12.5, 'shiny': 12.5}


def _hp(freq: float, slope: int = 24):
    """Clean-up high-pass (also removes the DC offset some sample sets carry)."""
    return fx.eq({'hp.freq': freq, 'hp.slope': slope})


def _eq(**bands):
    return fx.eq({k.replace('__', '.'): v for k, v in bands.items()})


def _trim(name: str):
    """The calibration of an amped DI patch: its input level drives the amp, so the output is trimmed here."""
    return fx.utility(gain=LEVELS[name], name='trim')


def _sfz(path: str, level: float, **kw):
    return inst.sfz(path, lazy=True, level=level, **kw)


def _multi(programs: dict, level: float, **kw):
    return inst.sfz_multi(programs, lazy=True, level=level, **kw)


# ------------------------------------------------------------------------------------ articulations (made)
# A palm mute is the picking hand resting on the strings at the bridge. No installed guitar pack has DI palm-mute
# samples (FSBS, Emily, Black and Green, Shiny: none; the SampleRadar metal chugs are amped), so the 'palm mute' zones
# emulate it, measured against the real amped chugs vs power chords of sampleradar-heavy-metal-guitar (Guitars A / C:
# the chug peaks as loud as the open chord, keeps its 80-315 Hz thump, is -4..-16 dB 100 ms in and -21..-35 dB at
# 200 ms, the centroid 1.1-1.9x the open chord's: the pick attack): a resonant low-pass at ~900 Hz (E3; 70 % key
# tracking) that leaves the fundamental and the low partials - the thump - and a filter envelope that opens it 3600 ct
# for the pick (~10 ms + 50 ms), a short decay (0.2 s: through a high-gain amp's compression the flat ~100 ms chug,
# then the cut) and no sustain. Through the rock amp (FSBS, power chords E2-D3 at velocity 110): peak -1.3 dB vs open,
# -4.2 / -22 dB at 100 / 200 ms, 80-160 / 160-315 Hz -1.8 / -1.5 dB vs the open chord, as bright (centroid x1.02). The
# v1 emulation (a 1.6 kHz low-pass, 0.55 s decay) lost 3-4 dB of the thump and rang ~250 ms flat into the amp; a 700 Hz
# version kept the thump but went dull (centroid x0.78). A dead note (fretting hand muting) is a short scratch.
# Bass staccato: the fretting hand lifting (the sustained sample damped fast); bass mute: the palm-muted thud.
# bandlib/rock.py GUITAR_ARTICULATIONS uses these.
PALM = {'filter': 'lpf_2p', 'cutoff': 900.0, 'resonance': 5.0, 'filKeytrack': 70.0, 'filKeycenter': 52,
        'filterEnv': [3600, 0, 0.001, 0.008, 0.05, 0, 0.05], 'decay': 0.2, 'sustain': 0.0, 'release': 0.05}
# (the band-pass follows the string and the envelope holds past the pick attack, which peaks ~30 ms in: a
# fixed 1.6 kHz band and a 70 ms decay left the dead notes 20-30 dB under the notes)
DEAD = {'filter': 'bpf_2p', 'cutoff': 1400.0, 'resonance': 0.0, 'filKeytrack': 60.0, 'filKeycenter': 64,
        'hold': 0.035, 'decay': 0.08, 'sustain': 0.0, 'release': 0.02}
# pre-amped (already distorted) sets: the amp's hiss and harmonics are in the sample, so the mute filters higher
PALM_AMPED = {'filter': 'lpf_2p', 'cutoff': 2400.0, 'resonance': 2.0, 'filKeytrack': 40.0, 'filKeycenter': 52,
              'decay': 0.4, 'sustain': 0.0, 'release': 0.05}
# Shinyguitar's layers are normalised (a velocity 50 note is only ~3.5 dB softer than 120): a velocity curve gives
# the picking hand its dynamic range back (about -14 dB at velocity 1, -4 dB at 64) on top of the layer timbres
ARCHTOP_VEL = {'velcurve': [[1, 0.2], [64, 0.6], [127, 1.0]]}
# the same for basses whose layers are normalised (Black And Blue, Big Little): accents and ghost notes by velocity
BASS_VEL = {'velcurve': [[1, 0.2], [64, 0.6], [127, 1.0]]}
STACCATO = {'decay': 0.5, 'sustain': 0.25, 'release': 0.03, 'filter': 'lpf_2p', 'cutoff': 2400.0, 'resonance': 0.0}
MUTE = {'filter': 'lpf_2p', 'cutoff': 700.0, 'resonance': 2.0, 'decay': 0.3, 'sustain': 0.0, 'release': 0.03}


def _guitar(path: str, level: float, palm=PALM, palm_gain: float = 2.5, dead_gain: float = 3.0, **kw):
    """One sample set as a keyswitched guitar: 'open' (the default, as recorded), 'palm mute', 'dead note'."""
    return _multi({'open': path, 'palm mute': {'path': path, 'zone': palm, 'gain': palm_gain},
                   'dead note': {'path': path, 'zone': DEAD, 'gain': dead_gain}}, level=level, **kw)


def _bass(path: str, level: float, base: str = 'sustain', **kw):
    """One sample set as a keyswitched bass: `base` (the default) + 'staccato' + 'mute'."""
    return _multi({base: path, 'staccato': {'path': path, 'zone': STACCATO, 'gain': 1.0},
                   'mute': {'path': path, 'zone': MUTE, 'gain': 2.0}}, level=level, **kw)


# --------------------------------------------------------------------------------------------- amp chains
# Amp + cabinet for a DI guitar: the engine's tube 'amp' (the head: cascaded preamp stages, the tone stack, the power
# amp with sag - the voicings in space_ir.AMPS) -> the cab IR (convolver) -> the mic's roll-off = the cab/* patches.
AMPS, CABS = _space_ir.AMPS, _space_ir.CABS
# amp()'s output against the bare cab/* chain (which keeps the DI's loudness): the library's levels (LEVELS, the band
# presets' trims, the heroes) were calibrated on the v1 chain (bright cap + saturator cab + tone stack), which came
# out this much under the DI on an FSBS power-chord riff - amp() lands where v1 did, so every balance holds.
AMP_TRIM = {'clean': -0.3, 'blues': -2.3, 'crunch': -2.4, 'rock': -4.5, 'metal': -6.4, 'lead': -5.5}


def amp(kind: str = 'rock', *, cab: str | None = None, mic: dict | None = None, name: str = 'amp', **knobs) -> list:
    """The insert chain of a DI guitar (or bass) through an amp and a cabinet: [amp, convolver, eq 'mic'] - the amp
    voicing `kind` (AMPS: clean blues crunch rock metal lead) with any amp knobs changed (gain=, bright=, mid=,
    presence=, master=, sag=, boost=, tight=, stages=, stack=, output=, mix= - docs/PARAMS.md 'amp'), into the
    cabinet of `cab` (a cab/* patch; default the kind's own: CABS), mic= the mic eq's params (replacing them, e.g.
    {'hp.freq': 70, 'lp.freq': 6000}). One amp for every DI guitar of the library: the rhythm patches, the band
    presets, the heroes."""
    if kind not in AMPS:
        raise ComposeError(f"amp(): unknown kind {kind!r}; kinds: {', '.join(AMPS)}")
    chain = [f.copy() for f in get(cab or CABS[kind]).fx]
    if [f.type for f in chain] != ['amp', 'convolver', 'eq']:
        raise ComposeError(f"amp(): {cab!r} is not a cab/* chain (amp -> convolver -> eq)")
    chain[0] = fx.amp(**{**AMPS[kind], 'output': _space_ir.AMP_OUTPUT[kind] + AMP_TRIM[kind], **knobs}, name=name)
    if mic:
        chain[2] = fx.eq(dict(mic), name='mic')
    return chain


_amp = amp

# The bass rig (an Ampeg SVT-style tube head, the DI blended under it - the rock bass sound): the amp side growls in
# the mids (tight 180 Hz: it carries no lows, so it cannot smear or phase against the DI's fundamental), the DI
# (time-aligned inside the amp: 'mix') carries the lows and the pick attack; a speaker / mic roll-off after both.
BASS_AMP = dict(stages=2, gain=4.0, bright=2.0, tight=180.0, bass=6.0, mid=6.5, treble=5.0, presence=4.0,
                resonance=5.0, master=6.0, sag=0.4, output=0.0)
BASS_AMP_OUTPUT = -5.3    # levels the amp side to the DI (Growlybass picked 8ths E1-E2: within 0.1 LU)


def bass_rig(*, mix: float = 0.35, lp: float = 4500.0, name: str = 'amp', **knobs) -> list:
    """A bass amp rig as an insert chain: [amp (BASS_AMP + knobs, the DI blended in: mix = the amp's share, 0.5 = half
    and half), eq 'cab' (a speaker roll-off at lp)]. More growl: gain=5-6 or mix=0.6; cleaner: gain=2-3, mix=0.35."""
    a = {**BASS_AMP, 'output': BASS_AMP_OUTPUT, **knobs, 'mix': mix}
    return [fx.amp(**a, name=name), fx.eq({'lp.freq': lp, 'lp.slope': 24, 'peak2.freq': 800, 'peak2.gain': 1.0,
                                           'peak2.q': 0.8}, name='cab')]


# ------------------------------------------------------------------------------------------------ packs

FSBS = {kind: f'samples/freepats-fsbs-{kind}/EGuitarFSBS-{kind} bridge {date}.sfz'
        for kind, date in (('jazz', '20260807'), ('clean', '20260807'), ('dist1', '20220911'),
                           ('dist2', '20220911'), ('direct', '20220911'))}
EMILY = 'samples/karoryfer-emilyguitar/emily_basic.sfz'
SHINY = 'samples/karoryfer-shinyguitar/Programs/main.sfz'
SHINY_ELECTRIC = 'samples/karoryfer-shinyguitar/Programs/electric_one.sfz'
# (the per-articulation programs, not the keyswitch files: each keyswitch file is re-imported per articulation, and
# the separate files load 2-4x faster)
BNG = 'samples/karoryfer-black-and-green-guitars/Programs/'
STEEL = 'samples/freepats-fss-steel-guitar/FSS-SteelStringGuitar-20200521.sfz'
CONCERT = 'samples/fiedler-natural-concert-guitar/mf-natural-concert-guitar-ogg.sfz'
METAL = 'samples/sampleradar-heavy-metal-guitar/'
GROWLY_CLEAN = 'samples/karoryfer-growlybass/growlybass_clean.sfz'
GROWLY_DIRTY = 'samples/karoryfer-growlybass/growlybass_dirty.sfz'
FASHION = 'samples/karoryfer-fashionbass/fashionbass.sfz'
FIEDLER_BASS = 'samples/fiedler-precision-e-bass/mf-precission-e-bass-fingered-pop-slap-slide-fretnoise.sfz'
SWAG = 'samples/karoryfer-swagbass/swagbass.sfz'
BNB = 'samples/karoryfer-black-and-blue-basses/Programs/'
PASTA = 'samples/karoryfer-pastabass/'
BIG_LITTLE = 'samples/karoryfer-big-little-bass/Programs/01-big_little_pluck.sfz'
SNEAKY = 'samples/karoryfer-sneakybass/Programs/'
ERGO = 'samples/karoryfer-ergo-eub/'
# Sneakybass was played very quietly and its upper notes fade: measured (velocity 100) C1-C#2 ~-20 dB, D2-F2 -21,
# F#2-B2 -28, C3-G3 -37. The curve (in the file's keys: an octave above the sounding notes) lifts the top by up to
# 12 dB, so a walking line up to C3 stays even (the highest notes stay a little softer, as played).
SNEAKY_KEYGAIN = [[50, 0.0], [54, 4.0], [60, 9.0], [67, 12.0]]

_CC0 = 'License CC0 (public domain).'
_KARORYFER = 'Karoryfer Lecolds / D. Smolken, ' + _CC0
_FREEPATS = 'FreePats (freepats.zenvoid.org), ' + _CC0
_PLAY_GUITAR = ('Play it like a guitarist: chords strummed, not struck (clip.strum(ms=8..25, bpm=s.tempo), '
                "'alternate' down / up for 8ths and 16ths, slower 30-60 ms for ballad and final chords), voicings "
                'a guitar can finger (clip.chordify(\'power\') or 3-5 note shapes spanning E2-E5, not piano '
                'clusters), velocities varied 70-115 with the accents on the beat, light timing humanize.')
_DI_ARTS = ("Articulations (keyswitches C-1 .. D-1, inserted by the compiler): 'open' (default), 'palm mute' "
            "(clip.articulate('palm', span=(a, b)): the damped chug, velocity 90-115) and 'dead note' (a muted "
            "scratch: articulate('dead', where=...) on off-beat 16ths for funk and rock rhythm).")


# --------------------------------------------------------------------------------------------- acoustic

register(Patch(
    'sampled/steel_guitar',
    instrument=_sfz(STEEL, level=LEVELS['steel_guitar'], tune=-10),
    fx=[_hp(80), _eq(peak1__freq=250, peak1__gain=-2.0, peak1__q=0.9, high__freq=8000, high__gain=1.5)],
    sends={'hall': -16},
    notes='v1. FreePats FSS steel-string acoustic guitar (a Seagull, from the FlameStudios set): 2 velocity layers '
          '(soft / hard), one sample per note, D#2-C#6. The strummed pop / rock / folk / singer-songwriter '
          'acoustic. ' + _PLAY_GUITAR + ' Open-position shapes (E, A, D, G, C, Em, Am) sound most natural; '
          'fingerpicking: arpeggio patterns with the bass note on the beat. tune -10 ct (the samples sit ~10 ct '
          'sharp). Tweak: velsens 0.8 (more even strums), cutoff 7000 (warmer). License GPL-3.0 with the FreePats '
          'exception: songs made with it are yours (the samples themselves stay GPL). Sends: hall -16. '
          'Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/concert_guitar',
    instrument=_sfz(CONCERT, level=LEVELS['concert_guitar']),
    fx=[_hp(70), _eq(peak1__freq=220, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'hall': -12},
    notes='v1. Natural Concert Guitar (Markus Fiedler): a classical nylon-string guitar, 4 velocity layers x up to 7 '
          'round robins, release (finger-off) and fret noises; the most alive nylon guitar here (sampled/nylon_guitar: '
          'one sample per note, one layer). Sampled on the open strings and fifths (E2 A2 D3 G3 B3 E4 A4 D5, the notes '
          'between shifted up to 5 semitones: the top octave gets a little thinner). Natural harmonics '
          '(flageolets, one sample each) on G#5-G7 (keys 80-103): a bell-like ending or accent. Classical, bossa, '
          'flamenco-light, film, ballads. Range E2-G5 for real parts. '
          'Play: arpeggios and fingerpicking (p-i-m-a patterns, the bass on the beat, velocities 50-100), bossa '
          'comping rolled 10-20 ms, rest strokes on melody notes (+10 velocity), tremolo as repeated 1/32 notes. '
          'License CC-BY-NC-SA 3.0 with the author\'s exception: commercial MUSIC productions are allowed, not '
          'sample products; credit Markus Fiedler (fiedler-audio.de). Its OGG source is lossy (inaudible here). '
          'Sends: hall -12. Measured -18.0 LUFS (audition arpeggio).',
    audition={'notes': 'arp'}))

register(Patch(
    'sampled/archtop_guitar',
    instrument=_multi({'open': {'path': SHINY, 'cc': {100: 127}, 'zone': ARCHTOP_VEL},
                       'muted': {'path': SHINY, 'cc': {100: 127, 110: 100}, 'zone': ARCHTOP_VEL}},
                      level=LEVELS['archtop_guitar']),
    fx=[_hp(80), _eq(peak1__freq=300, peak1__gain=-2.0, peak1__q=0.9)],
    sends={'hall': -14},
    notes='v1. Shinyguitar (Karoryfer): an acoustic archtop, the microphone signal (cc 100 = 127), 4 velocity layers '
          'x 5 random takes; its normalised layers get a velocity curve here (~9 dB from velocity 40 to 120). The swing / big-band rhythm guitar (Freddie Green: 3-4 note shell voicings on the low '
          'strings, four to the bar, short and even, velocity 70-90), gypsy-jazz la pompe, folk, intimate ballads. '
          "Articulations (keyswitches C-1, C#-1): 'open' (default) and 'muted' (the player's muting control, "
          "cc 110: short notes - clip.articulate('muted') for the choked chords of la pompe). Range E2-E6. "
          + _PLAY_GUITAR + ' ' + _KARORYFER + ' Sends: hall -14. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))


# --------------------------------------------------------------------------------- electric (pre-amped FSBS)
# FreePats FSBS: a Fender (Squier-class) Stratocaster, bridge pickup, every string sampled every ~3 semitones; soft
# (velocity <= 92) and hard (93+) picking x 4 random takes; the FreePats rendered each through an amp / effects rack
# (jazz, clean, dist1, dist2) - no amp chain needed. The same guitar as a DI set: sampled/rock_guitar & co.

_FSBS_NOTE = ('FreePats FSBS electric guitar (a Fender Stratocaster, bridge pickup; 2 picking strengths - velocity '
              '<= 92 soft, 93+ hard - x 4 random takes), range E2-D6. ' + _FREEPATS)

register(Patch(
    'sampled/jazz_guitar',
    instrument=_guitar(FSBS['jazz'], LEVELS['jazz_guitar']),
    fx=[_hp(70), _eq(peak1__freq=350, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'hall': -14},
    notes='v1. ' + _FSBS_NOTE + ' Rendered through the FreePats "jazz" amp rack: round, warm, the treble rolled '
          'off. Jazz comping (3-4 note shell / drop-2 voicings C3-C5, rolled 10-20 ms, velocity 60-90 - under 93 '
          'stays on the soft pick layer), chord melodies, single-note lines (octaves for the Wes Montgomery '
          'climax). ' + _DI_ARTS + ' Sends: hall -14. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/clean_guitar',
    instrument=_guitar(FSBS['clean'], LEVELS['clean_guitar']),
    fx=[_hp(90), _eq(peak1__freq=300, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'plate': -16},
    notes='v1. ' + _FSBS_NOTE + ' Rendered through the FreePats "clean" amp rack: a bright clean Strat for pop, '
          'funk, soul, indie arpeggios and country. Funk: 16th scratches with dead notes between the chords '
          '(velocity 100+ on the accents), 2-3 note voicings high on the neck (G3-D5). Chorus / delay: '
          '.with_fx(fx.chorus(mode="I", mix=0.3)). ' + _DI_ARTS + ' Sends: plate -16. Measured -18.0 LUFS '
          '(audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/dist_guitar',
    instrument=_guitar(FSBS['dist1'], LEVELS['dist_guitar'], palm=PALM_AMPED, palm_gain=1.0),
    fx=[_hp(90), _eq(peak1__freq=400, peak1__gain=-2.0, peak1__q=0.8, lp__freq=9000)],
    sends={'plate': -20},
    notes='v1. ' + _FSBS_NOTE + ' Rendered through the FreePats "dist1" rack: a distorted, powerful rock rhythm '
          'guitar. Power chords (clip.chordify(\'power\') on roots E2-A3, strummed 6-12 ms), palm-muted 8th chugs '
          '(articulate(\'palm\')), open chords ringing in the chorus. Double-track it: the same part on two tracks '
          'panned -0.9 / +0.9 with different humanize seeds (or sampled/dist_guitar left and sampled/fuzz_guitar '
          'right). ' + _DI_ARTS + ' Sends: plate -20. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/fuzz_guitar',
    instrument=_guitar(FSBS['dist2'], LEVELS['fuzz_guitar'], palm=PALM_AMPED, palm_gain=1.0),
    fx=[_hp(90), _eq(peak1__freq=400, peak1__gain=-2.0, peak1__q=0.8, lp__freq=9000)],
    sends={'plate': -20},
    notes='v1. ' + _FSBS_NOTE + ' Rendered through the FreePats "dist2" rack: the second distorted voicing, '
          'more saturated and compressed than sampled/dist_guitar (fuzzier sustain) - riffs, stoner / grunge '
          'rhythm, the other side of a double-tracked wall. ' + _DI_ARTS + ' Sends: plate -20. Measured -18.0 '
          'LUFS (audition chords).',
    audition={'notes': 'chord'}))


# ------------------------------------------------------------------------ hollowbody electrics (Karoryfer)
_BNG = ('Black And Green Guitars (Karoryfer, recorded by Brian Wood): 3 velocity layers x 4 round robins, '
        'release samples (the string noise at key-up). ')

register(Patch(
    'sampled/gretsch_guitar',
    instrument=_multi({'twang': BNG + '04-green_twang.sfz', 'staccato': BNG + '05-green_staccato.sfz',
                       'hammer-on': BNG + '06-green_hammer-on.sfz',
                       'palm mute': {'path': BNG + '04-green_twang.sfz', 'cc': {70: 100}}},
                      level=LEVELS['gretsch_guitar']),
    fx=[_hp(80), _eq(peak1__freq=300, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'plate': -16},
    notes='v1. ' + _BNG + 'A green Gretsch Anniversary hollowbody: twangy, airy clean - rockabilly, surf, '
          'country, 50s-60s pop, indie. Articulations (keyswitches C-1 .. D#-1, inserted by the compiler): '
          "'twang' (default: the open picked note), 'staccato' (real short notes: clip.articulate('stac')), "
          "'hammer-on' (real legato hammer-ons / pull-offs without a pick attack: articulate('hammer') on the "
          "second note of a slur), 'palm mute' (the pack's muting control: articulate('palm')). Range E2-D6. "
          + _PLAY_GUITAR + ' Slapback: a short echo send (~110 ms). ' + _KARORYFER + ' Sends: plate -16. '
          'Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/hofner_guitar',
    instrument=_multi({'twang': BNG + '07-black_twang.sfz', 'staccato': BNG + '08-black_staccato.sfz',
                       'behind the bridge': BNG + '09-black_behind_the_bridge.sfz',
                       'palm mute': {'path': BNG + '07-black_twang.sfz', 'cc': {70: 100}}},
                      level=LEVELS['hofner_guitar']),
    fx=[_hp(80), _eq(peak1__freq=300, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'plate': -16},
    notes='v1. ' + _BNG + 'A black Hofner Club hollowbody (the early-Beatles guitar): woody, warm clean - 60s '
          'beat, jazz-pop, indie, soul chords. Articulations (keyswitches C-1 .. D#-1): \'twang\' (default), '
          "'staccato' (real short notes), 'behind the bridge' (the plinky string-behind-the-bridge effect, E2-C5: "
          "an eerie accent, articulate('behind')), 'palm mute' (the muting control). Range E2-D6. "
          + _PLAY_GUITAR + ' ' + _KARORYFER + ' Sends: plate -16. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))


# ---------------------------------------------------------------------------------- DI guitars + amp chains
_POST = _eq(hp__freq=100, peak1__freq=250, peak1__gain=-1.5, high__freq=9000, high__gain=-2.0)
_DI_FSBS = 'The DI (un-amped) FreePats FSBS Stratocaster (CC0; 2 picking strengths x 4 random takes, E2-D6)'
_DI_EMILY = ('The DI Epiphone "Emily the Strange" guitar (Karoryfer, CC0; flatwounds, both pickups; 4 velocity '
             'layers x 3 round robins, string-release noises; E2-C7)')
_AMP_TWEAK = ("Tweak: .but_fx('amp', gain=...) (the gain knob 0-10), .but_fx('amp', mid=..., presence=..., master=...) "
              "(the tone stack and the power amp; docs/PARAMS.md 'amp'), any voicing into any cab: "
              "sampled_guitars.amp(kind, cab=...).")

register(Patch(
    'sampled/rock_guitar',
    instrument=_guitar(FSBS['direct'], DI_LEVEL['fsbs']),
    fx=amp('rock') + [_POST, _trim('rock_guitar')],
    sends={'room': -13},
    notes='v2. ' + _DI_FSBS + ' through a Plexi-style amp and a Marshall 4x12 with Greenbacks (cab/rock_4x12: '
          'the engine\'s tube amp: a cranked two-stage Plexi, gain 6, mids 7, master 7): the 70s-80s rock rhythm guitar '
          '(rock_band gtr_l). '
          + _DI_ARTS + ' Power chords on E2-A3 roots, strummed 8-14 ms, double-tracked with sampled/crunch_guitar '
          'on the other side. ' + _AMP_TWEAK + ' Sends: room -13. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/crunch_guitar',
    instrument=_guitar(EMILY, DI_LEVEL['emily']),
    fx=amp('crunch') + [_POST, _trim('crunch_guitar')],
    sends={'room': -13},
    notes='v2. ' + _DI_EMILY + ' through a crunch amp into a 2x12 Celestion Vintage 30 (cab/crunch_2x12, the tube amp at gain '
          '5): mid-forward classic-rock / indie crunch (rock_band gtr_r). ' + _DI_ARTS + ' Its own muted-string '
          'scratches sit on keys G6-B6 (91-95, 5 takes each) in the open articulation. ' + _AMP_TWEAK +
          ' Sends: room -13. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/metal_guitar',
    instrument=_guitar(FSBS['direct'], DI_LEVEL['fsbs']),
    fx=amp('metal') + [_POST, _trim('metal_guitar')],
    sends={'room': -16},
    notes='v2. ' + _DI_FSBS + ' through a high-gain amp and a 4x12 Vintage 30 (cab/metal_4x12: 110 Hz tight '
          'input, a Tube Screamer boost, four preamp stages at gain 7, scooped mids): modern rock / metal rhythm. Tight palm-muted 8th / 16th chugs on E2-G2 '
          '(articulate(\'palm\'), velocity 100-120), power chords and 5ths, double-tracked hard left / right (two '
          'tracks, different humanize seeds). ' + _DI_ARTS + ' ' + _AMP_TWEAK + ' Sends: room -16. Measured -18.0 '
          'LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/blues_guitar',
    instrument=_guitar(EMILY, DI_LEVEL['emily']),
    fx=amp('blues') + [_eq(hp__freq=100, peak1__freq=280, peak1__gain=-1.5, peak2__freq=1300,
                                      peak2__gain=-3.0, peak2__q=0.8, high__freq=9000, high__gain=-1.0),
                                  _trim('blues_guitar')],
    sends={'room': -12, 'plate': -22},
    notes='v2. ' + _DI_EMILY + ' into an edge-of-breakup British combo (cab/blues_1x12, the tube amp at gain 3.5, sag 0.45): blues, indie, '
          'soul rhythm and fills (indie_band gtr_r). Double stops, 6ths and 3rds, shuffle rhythms, fills in the '
          'vocal gaps. ' + _DI_ARTS + ' ' + _AMP_TWEAK + ' Sends: room -12, plate -22. Measured -18.0 LUFS '
          '(audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/jangle_guitar',
    instrument=_guitar(FSBS['direct'], DI_LEVEL['fsbs']),
    fx=amp('clean') + [fx.compressor(threshold=-26, ratio=4, attack=5, release=120, automakeup='on'),
                                 fx.chorus(mode='I', mix=0.3),
                                 _eq(hp__freq=120, peak1__freq=300, peak1__gain=-2.0, peak2__freq=1300,
                                     peak2__gain=-3.0, peak2__q=0.8, peak3__freq=4000, peak3__gain=1.0,
                                     high__freq=8000, high__gain=1.5),
                                 _trim('jangle_guitar')],
    sends={'room': -12, 'plate': -18},
    notes='v2. ' + _DI_FSBS + ' through a clean combo (cab/clean_1x12), a compressor and Juno chorus I: the '
          'chiming indie / dream-pop / 80s arpeggio guitar (indie_band gtr_l). Open-string arpeggios in 8ths and '
          '16ths (G3-E5), sus2 / add9 shapes, let chords ring. ' + _DI_ARTS + ' ' + _AMP_TWEAK +
          " .but_fx('chorus', mix=0) for a dry clean Strat. Sends: room -12, plate -18. Measured -18.0 LUFS "
          '(audition arpeggio).',
    audition={'notes': 'arp'}))

register(Patch(
    'sampled/lead_guitar',
    instrument=_sfz(FSBS['direct'], DI_LEVEL['fsbs'], mono='legato', legatotime=30, glideshape='fast'),
    fx=amp('lead') + [fx.compressor(threshold=-24, ratio=3, attack=8, release=120, automakeup='on'),
                       _eq(peak1__freq=300, peak1__gain=-2.0, peak2__freq=1700, peak2__gain=1.0,
                           peak3__freq=4300, peak3__gain=-2.0, lp__freq=7500),
                       _trim('lead_guitar')],
    sends={'echo': -9, 'plate': -11},
    notes='v2. ' + _DI_FSBS + ' as a monophonic legato player (mono=\'legato\') through the tube amp\'s lead '
          'channel (3 stages, gain 7, a boost, mids pushed) into cab/rock_4x12 and a compressor: the singing rock lead / solo (rock_band '
          'lead). Overlapping notes slur without a new pick attack (articulation.legato(clip)); slides: '
          'clip.glide(80-150, where=articulation.leaps(3)); bends: automate instrument.pitchbend in steps (+1 / +2 '
          'st, a quick 40-80 ms rise, hold, release); vibrato on long notes: articulation.vibrato(track, clip, at, '
          'depth=25, rate=5.5). Range G3-E6 (the top two strings). Throws: automate send.echo. ' + _AMP_TWEAK +
          ' Sends: echo -9 (dotted 8th), plate -11. Measured -18.0 LUFS (audition melody).',
    audition={'notes': 'phrase'}))

register(Patch(
    'sampled/archtop_electric',
    instrument=_multi({'open': {'path': SHINY, 'cc': {100: 0}, 'zone': ARCHTOP_VEL},
                       'muted': {'path': SHINY, 'cc': {100: 0, 110: 100}, 'zone': ARCHTOP_VEL}},
                      level=DI_LEVEL['shiny']),
    fx=amp('clean', gain=1.0, bright=0.0) + [_eq(hp__freq=90, peak1__freq=320, peak1__gain=-1.5,
                                                   lp__freq=5500), _trim('archtop_electric')],
    sends={'hall': -14},
    notes='v2. Shinyguitar (Karoryfer, CC0): an archtop jazz guitar, its magnetic pickup (cc 100 = 0; 4 velocity '
          'layers x 5 takes) into a clean 1x12 combo with the treble rolled off (low-pass 5.5 kHz): the classic '
          'jazz-box tone - single-note lines, chord melodies, comping. Articulations: \'open\' (default), '
          "'muted' (the pack's muting control, short choked chords). Range E2-E6. Jazz comping: shells and drop-2 "
          'voicings C3-C5 rolled 10-20 ms, velocity 55-90; lines: articulation.legato for slurred phrases, '
          'ghosted notes at velocity 40-50. Tweak: .but_fx(\'eq\', **{\'lp.freq\': 8000}) (brighter); the bright '
          'blues tone of indie_band\'s lead: sampled/blues_guitar. ' + _KARORYFER + ' Sends: hall -14. Measured '
          '-18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))


# ------------------------------------------------------------------------------------------------ metal
# SampleRadar heavy metal guitar: amped, double-tracked recordings. Guitar C's power chords (3 takes) and palm-muted
# chugs (2 takes) on the roots E2 F2 G2 A2 B2 C3 D3 E3 become one keyswitched chord instrument (the notes between are
# the neighbours shifted a semitone); Guitar B's lead multisample is a playable lead. The files are ~10 ct sharp.
_METAL_ROOTS = ((40, 'E Lo', 36, 40), (41, 'F', 41, 41), (43, 'G', 42, 43), (45, 'A', 44, 45), (47, 'B', 46, 47),
                (48, 'C', 48, 48), (50, 'D', 49, 50), (52, 'E Hi', 51, 55))


def _metal_rhythm_zones() -> list:
    """Explicit zones: 'open' power chords (keyswitch C-1) and 'palm mute' chugs (C#-1); the files are looked up
    when a song renders (inst.sampler(zones=..., lazy=True))."""
    base = METAL + 'Guitar C'
    zones = []
    for root, name, lo, hi in _METAL_ROOTS:
        for i, take in enumerate('ABC'):
            f = f"{base}/Power chords {take}/HMRhy{take}{'Pwrchord' if take == 'C' else 'PwrChord'}-{name}.wav"
            zones.append({'file': f, 'root': root, 'lo': lo, 'hi': hi, 'lorand': round(i / 3, 4),
                          'hirand': round((i + 1) / 3, 4) if i < 2 else 1.0, 'tune': -10, 'release': 0.12,
                          'swLast': 0, 'swDefault': 0})
        for i, take in enumerate('AB'):
            f = f"{base}/Chugs {take}/HMRhy{take}Chug-{name}.wav"
            zones.append({'file': f, 'root': root, 'lo': lo, 'hi': hi, 'lorand': 0.5 * i, 'hirand': 0.5 * (i + 1),
                          'tune': -4, 'release': 0.05, 'swLast': 1, 'swDefault': 0})
    zones[0]['swLo'], zones[0]['swHi'] = 0, 1
    return zones


def _metal_rhythm():
    ins = inst.sampler(zones=_metal_rhythm_zones(), lazy=True, level=LEVELS['metal_rhythm'], velsens=0.5,
                       attack=0.0, release=0.1, polyphony=24)
    # the articulation names for clip.articulate() (what inst.sfz_multi records for its keyswitches)
    ins.info = {'sfz': {'keyswitches': {'open': 0, 'palm mute': 1}}}
    return ins


register(Patch(
    'sampled/metal_rhythm',
    instrument=_metal_rhythm(),
    fx=[_hp(70), _eq(peak1__freq=400, peak1__gain=-2.0, peak1__q=0.8, lp__freq=10000)],
    sends={'room': -18},
    notes='v1. SampleRadar heavy metal guitar, Guitar C: REAL recorded power chords (3 takes, random) and '
          "palm-muted chugs (2 takes) of a high-gain amped guitar, one sample per root (E2 F2 G2 A2 B2 C3 D3 E3; "
          "the keys between shift a neighbour by a semitone). Play ONE note per chord - its root, E2-E3 (D2-G3 "
          "stretch): the note is the whole power chord. Articulations (keyswitches C-1, C#-1, inserted by the "
          "compiler): 'open' (default: ringing chords - hold them, they sustain 10-20 s) and 'palm mute' "
          "(clip.articulate('palm'): the tight chug; 8th / 16th gallops on E2, velocity 100-120). No velocity "
          'layers (velsens 0.5: velocity changes the level a little). Metal, hard rock, punk: chug the verse, '
          'open chords on the accents and in the chorus; double-track with sampled/metal_guitar (a DI + amp) '
          'hard left / right for a wall. tune -10 / -4 ct (the files sit sharp). License: royalty-free for music, '
          'no redistribution of the samples. Sends: room -18. Measured -18.0 LUFS (audition: E2 chord hits held '
          'a bar).',
    audition={'notes': 'hit', 'pitch': 'E2', 'length': 4}))

register(Patch(
    'sampled/metal_lead',
    instrument=inst.multisample('samples/sampleradar-heavy-metal-guitar/Guitar B/Lead Multi', lazy=True,
                                level=LEVELS['metal_lead'], keys=(36, 90), loop='none', tune=-10, mono='legato',
                                legatotime=40, glideshape='fast', release=0.15),
    fx=[_hp(120), _eq(peak1__freq=400, peak1__gain=-1.5, peak1__q=0.8, peak3__freq=3500, peak3__gain=-1.5,
                      lp__freq=9000),
        fx.compressor(threshold=-20, ratio=3, attack=10, release=150, automakeup='on')],
    sends={'echo': -12, 'plate': -12},
    notes='v1. SampleRadar heavy metal guitar, Guitar B lead multisample: a saturated, singing high-gain lead tone, '
          'one long sustaining note every minor third D2-D6 (the notes between shifted up to a semitone), no '
          "velocity layers. A monophonic legato player (mono='legato'): overlapping notes slur "
          '(articulation.legato), clip.glide(80-150) for slides, bends by automating instrument.pitchbend (+1 / +2 '
          'st), articulation.vibrato on long notes (depth 20-35, rate 5.5-6.5). Range E3-D6 for solos. Metal / '
          'hard-rock solos, harmonised twin leads (a second track a third or sixth above, panned apart). tune -10 '
          'ct. License: royalty-free for music, no redistribution of the samples. Sends: echo -12, plate -12. '
          'Measured -18.0 LUFS (audition melody).',
    audition={'notes': 'phrase'}))


# --------------------------------------------------------------------------------------------- electric basses
# Most Karoryfer basses map their samples an octave above the sounding pitch (bass guitar notation): those patches
# carry transpose=12, so written E1 sounds E1 like every bass here. Their own keyswitches (D#1 .. G1) would collide
# with low notes, so the articulations are re-keyed below the range (C-1 up) via sfz_multi.

_PLAY_BASS = ('Play it like a bassist: roots and 5ths locked to the kick, approach notes (chromatic / scale) into '
              'chord changes, velocity 80-115 with accents on the beat and softer off-beats, ghost notes (velocity '
              '30-50 or the ghost / mute articulation) in funk and 16th grooves, light timing humanize (5-10 ms).')
_BASS_ARTS = ("Articulations (keyswitches C-1 .. D-1, inserted by the compiler): 'sustain' (default), 'staccato' "
              "(clip.articulate('stac'): the fretting hand lifting, short punchy notes - the note damped fast) and "
              "'mute' (articulate('mute'): the palm-muted thud).")

register(Patch(
    'sampled/finger_bass',
    instrument=_bass(GROWLY_CLEAN, LEVELS['finger_bass'], transpose=12),
    fx=[_hp(30), _eq(peak1__freq=250, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'room': -24},
    notes='v1. Growlybass clean (Karoryfer): a Squier Jazz Bass, roundwounds, both pickups, fingered; 4 velocity '
          'layers x 4 round robins. The all-round electric bass for pop, soul, funk, rock, fusion (pop_band / '
          'funk bass). Range E1-G3 for real lines (C#1 on the detuned low string). ' + _BASS_ARTS + ' ' + _PLAY_BASS
          + ' Tweak: cutoff 3000 (darker), velsens 0.8, the rock_band chain: sampled/rock_bass. ' + _KARORYFER +
          ' Sends: room -24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/rock_bass',
    instrument=_bass(GROWLY_DIRTY, LEVELS['rock_bass'], transpose=12),
    fx=[_eq(hp__freq=35, peak1__freq=250, peak1__gain=-2.0, peak1__q=0.9, peak2__freq=900, peak2__gain=1.0,
            peak2__q=1.1, peak3__freq=60, peak3__gain=-2.5, peak3__q=1.2, low__freq=110, low__gain=1.5)]
       + bass_rig() + [fx.compressor(threshold=-22, ratio=4, attack=15, release=140, knee=6, automakeup='on')],
    sends={'room': -24},
    notes='v2. Growlybass (Karoryfer): the Squier Jazz Bass with its string-release samples, through the rock_band '
          'bass chain: an SVT-style rig (bass_rig: the engine\'s tube amp growling in the mids, the time-aligned DI '
          'under it for the lows and the pick, a speaker roll-off), a compressor - the picked-sounding rock '
          'bass that cuts through guitar walls. Range E1-G3. ' + _BASS_ARTS + ' Rock: 8th roots locked to the kick '
          '(velocity 95-115), staccato in the verse, sustained notes in the chorus, fills into sections. Duck it '
          'under the kick: song.sidechain(bass, key=drums, pitches=\'kick\', depth=5). Its pick scrapes are on '
          'keys the samples map above the range (see python -m agentsound sfz). ' + _KARORYFER + ' Sends: room '
          '-24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/round_bass',
    instrument=_bass(FASHION, LEVELS['round_bass']),
    fx=[_hp(30), _eq(peak1__freq=250, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'room': -24},
    notes='v1. Fashionbass (Karoryfer): a Killer KB bass, two-year-old roundwounds, neck pickup, 5 velocity layers x '
          '3 round robins, string-release samples: bright, round and punchy - indie, pop, funk, fusion (indie_band '
          'bass). Range E1-G3 (F#0 / A0 on the detuned low string). ' + _BASS_ARTS + ' ' + _PLAY_BASS + ' '
          + _KARORYFER + ' Sends: room -24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/slap_bass',
    instrument=_sfz(FIEDLER_BASS, LEVELS['slap_bass'], transpose=12),
    fx=[_hp(30), _eq(peak1__freq=300, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'room': -24},
    notes='v1. MF Precision E-Bass (Markus Fiedler): a Fender Precision, fingered (up to 4 velocity layers) and '
          'slapped / popped at velocity 104-127 (2-3 sounds per note). Funk, disco, fusion: thumb slaps on the low '
          'roots (velocity 104-115), pops on the octave (116-127), fingered ghost notes between (velocity 30-60). '
          'Range E1-B2 for notes; the pack\'s effects sit above (sounding the file an octave down, transpose=12): '
          'slides up / down on keys C3-G4, slides down G#4-C5, fret noises D5-C6 (one layer). License CC-BY-NC-SA '
          '3.0 with the author\'s exception: commercial MUSIC productions are allowed, not sample products; credit '
          'Markus Fiedler (fiedler-audio.de). Sends: room -24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/flatwound_bass',
    instrument=_bass(SWAG, LEVELS['flatwound_bass']),
    fx=[_hp(30), _eq(peak1__freq=250, peak1__gain=-1.0, peak1__q=0.9)],
    sends={'room': -24},
    notes='v1. Swagbass (Karoryfer): an Ibanez BTB with old, dead d\'Addario Chrome flatwounds, neck pickup; 3 '
          'velocity layers x 4 round robins, string-release samples: the warm, thumpy Motown / soul / 60s pop / '
          'reggae bass. Range A0-G3 (the low string tuned down to A; its A0-C#1 samples sit 30-45 ct sharp - use them '
          'for passing notes, E1 up is in tune). ' + _BASS_ARTS + ' Motown: melodic lines '
          'with chromatic approaches and syncopated 8ths, staccato notes against the backbeat. ' + _KARORYFER +
          ' Sends: room -24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/picked_bass',
    instrument=_multi({a: {'path': BNB + f, 'zone': BASS_VEL}
                       for a, f in (('pluck', '05-darkblack_pluck.sfz'), ('staccato', '09-darkblack_stac.sfz'),
                                    ('ghost', '07-darkblack_ghost.sfz'), ('behind the bridge', '10-darkblack_btb.sfz'))},
                      level=LEVELS['picked_bass'], transpose=12),
    fx=[_hp(30), _eq(peak1__freq=250, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'room': -24},
    notes='v1. Black And Blue Basses "darkblack" (Karoryfer): a picked 5-string solidbody, 4 velocity layers x 4 '
          'round robins; every articulation is recorded: \'pluck\' (default), \'staccato\', \'ghost\' (dead '
          'ghost notes: articulate(\'ghost\') on the 16ths between the notes) and \'behind the bridge\' (a '
          'clanky percussive effect), keyswitches C-1 .. D#-1 (inserted by the compiler). Rock, punk, post-punk, '
          'new wave: driving 8ths with the pick, velocity 90-120. Range B0-E4 (the low B string). '
          + _PLAY_BASS + ' Its layers are normalised, so a velocity curve adds the level (~7-10 dB from velocity 40 to 120: accents and '
          'ghosts by velocity). Its filter / wobble controls (varN) are not supported and left out. ' + _KARORYFER +
          ' Sends: room -24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/hollow_bass',
    instrument=_multi({'pluck': {'path': BNB + '03-babyblue_all.sfz', 'zone': BASS_VEL}}, LEVELS['hollow_bass'],
                      transpose=12),
    fx=[_hp(30), _eq(peak1__freq=250, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'room': -24},
    notes='v1. Black And Blue Basses "babyblue" (Karoryfer): a fingered 5-string hollowbody, 2 velocity layers x 8 '
          'round robins, low notes down to E0 (the low B string, and below it retuned samples): a soft, woody, '
          'round bass for ballads, soul, singer-songwriter, jazz-pop and lo-fi. Range B0-E4. ' + _PLAY_BASS +
          ' Its layers are normalised, so a velocity curve adds the level (~7-10 dB from velocity 40 to 120: accents and '
          'ghosts by velocity). Its filter / wobble controls (varN) are not supported and left out. ' + _KARORYFER + ' Sends: room '
          '-24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/bass_vi',
    instrument=_multi({'picked': PASTA + 'linguine.sfz', 'muted': PASTA + 'tagliatelle.sfz',
                       'fingered': PASTA + 'fetuccine.sfz', 'roundwound': PASTA + 'spaghetti.sfz'},
                      level=LEVELS['bass_vi'], transpose=12),
    fx=[_hp(35), _eq(peak1__freq=300, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'plate': -20},
    notes='v1. Pastabass (Karoryfer, recorded by spacecoyote): a Squier Bass VI - a six-string baritone tuned an '
          'octave below a guitar, 3-4 velocity layers x 3-4 random takes. Articulations (keyswitches C-1 .. D#-1): '
          "'picked' (default: flatwounds, bridge pickup - the twangy 60s 'tic-tac' / surf / spaghetti-western "
          "bass), 'muted' (picked and palm-muted, pickup combo: the tic-tac doubling of a string bass), "
          "'fingered' (flatwounds, neck pickup: round) and 'roundwound' (brighter strings). Range E1-E4; melodic "
          'baritone lines and twangy riffs up to E5. ' + _PLAY_BASS + ' ' + _KARORYFER + ' Sends: plate -20. '
          'Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/short_scale_bass',
    instrument=_multi({'pluck': {'path': BIG_LITTLE, 'zone': BASS_VEL}}, LEVELS['short_scale_bass'], transpose=12),
    fx=[_hp(30), _eq(peak1__freq=250, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'room': -24},
    notes='v1. Big Little Bass (Karoryfer): a Washburn AB95 acoustic-electric hollowbody bass with double-bass '
          'strings, played high on the neck - a short, plucky, woody sound between an upright and a ukulele bass; '
          '2 velocity layers x 5 round robins. Indie-folk, lo-fi, chamber pop, bossa, film. Range B0-F#4. '
          + _PLAY_BASS + ' Its layers are normalised, so a velocity curve adds the level (~7-10 dB from velocity 40 to 120: accents and '
          'ghosts by velocity). Its filter / wobble controls (varN) are not supported and left out. ' + _KARORYFER +
          ' Sends: room -24. Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))


# ------------------------------------------------------------------------------------------- upright basses

register(Patch(
    'sampled/sneaky_bass',
    instrument=_multi({'pluck': {'path': SNEAKY + '02-sneakybass_pluck.sfz', 'keygain': SNEAKY_KEYGAIN},
                       'ghost': {'path': SNEAKY + '03-sneakybass_ghost.sfz', 'keygain': SNEAKY_KEYGAIN},
                       'mute': {'path': SNEAKY + '04-sneakybass_mute.sfz', 'keygain': SNEAKY_KEYGAIN},
                       'fingering noise': SNEAKY + '05-sneakybass_fingering_noise.sfz'},
                      level=LEVELS['sneaky_bass'], transpose=12),
    fx=[_hp(30), _eq(peak1__freq=250, peak1__gain=-1.0, peak1__q=0.9)],
    sends={'plate': -20},
    notes='v1. Sneakybass (Karoryfer, played by D. Smolken): a 1958 Otto Rubner double bass, pizzicato, played very '
          'quietly ("late night practice"): close, intimate, with finger noise - ballads, quiet jazz trio, lo-fi, '
          'film. 4 round robins per note. Articulations (keyswitches C-1 .. D#-1): \'pluck\' (default), \'ghost\' '
          '(ghosted notes for walking-bass skips), \'mute\' (left-hand muted thump), \'fingering noise\' (the '
          'finger sliding on the string: sprinkle it before phrase starts). Range C1-C3 (fifths tuning); the pack '
          'fades ~20 dB towards the top (lifted up to 12 dB here: keygain), its upper notes stay soft and airy and '
          'a few low ones (F1, F#1, G#1) sit 25-40 ct flat - a lo-fi character bass, not a precise one. Walking: '
          'quarter notes at velocity 70-100, a ghost on the "and" of 4 now and then; sampled/upright_bass '
          '(Meatbass) is the louder, fuller jazz bass. ' + _KARORYFER + ' Sends: plate -20. Measured -18.0 LUFS '
          '(audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/electric_upright',
    # the bowed notes swell ~8 dB above the plucked ones at the same velocity: balanced by the program gain
    instrument=_multi({'pizz': ERGO + 'ergo_pizz.sfz', 'arco': {'path': ERGO + 'ergo_arco.sfz', 'gain': -8.0}},
                      level=LEVELS['electric_upright']),
    fx=[_hp(28), _eq(peak1__freq=250, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'plate': -20},
    notes='v1. Ergo EUB (Karoryfer, played by D. Smolken): an electric upright bass recorded direct, Spirocore '
          'strings, 3 velocity layers x 4 round robins, fifths tuning with the low string also tuned down to A and '
          'E (so it reaches E0, an octave below a 4-string bass). Articulations (keyswitches C-1, C#-1): \'pizz\' '
          '(default: tight, modern jazz / fusion / world / pop upright) and \'arco\' (bowed: sustained lines, '
          'cinematic sub drones; clip.articulate(\'arco\'); the bowed samples are ~2 s long and not looped, so '
          'arco notes fade after ~2 s - re-bow longer notes). Range E0-A3. Walking lines at velocity 70-110; arco: '
          'long notes, automate expression for swells. ' + _KARORYFER + ' Sends: plate -20. Measured -18.0 LUFS '
          '(audition 8th bass).',
    audition={'notes': 'bass'}))
