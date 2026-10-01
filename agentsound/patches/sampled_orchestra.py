"""Sampled orchestra & winds, part 2 (instrument 'sampler'): the solo winds and brass the first library (sampled.py)
lacked, played versions (legato, keyswitched articulations, live dynamics) of the core soloists and sections, string
colours, orchestral mallets, bells, harp, timpani rolls and percussion, choirs.

  woodwinds:  sampled/piccolo sampled/solo_flute sampled/alto_flute sampled/solo_oboe sampled/english_horn
              sampled/solo_clarinet sampled/bass_clarinet sampled/bassoon sampled/contrabassoon sampled/bari_sax
  brass:      sampled/solo_trumpet sampled/trumpet_harmon sampled/solo_horn sampled/solo_trombone
              sampled/bass_trombone sampled/tuba sampled/war_tuba sampled/trumpet_section sampled/horn_section
              sampled/trombone_section
  strings:    sampled/string_section sampled/strings_tremolo sampled/strings_harmonics sampled/solo_viola
              sampled/solo_bass
  percussion: sampled/glockenspiel sampled/xylophone sampled/marimba sampled/tubular_bells sampled/concert_harp
              sampled/timpani_rolls sampled/orchestral_percussion
  choirs:     sampled/choir_mixed sampled/choir_male sampled/choir_oh

Solo winds, brass and strings are monophonic legato players (mono='legato'): overlapping notes are legato
transitions; articulation.perform(track, line, at) plays a written line on them with articulations, the dynamics lane,
vibrato and a player's timing (docs/COMPOSE_API.md "Realistic performance"). 'dynamics' (0..1, default 0.6 = mf) is
live: the recorded layers crossfade (VSCO) or the library's mod-wheel curve opens (SSO / VPO) while a note sounds.
Pitches are SOUNDING pitch (clarinets, horns, English horn, glockenspiel and xylophone included).

Each patch reads its files only when a song renders it (lazy): importing needs no samples, a missing pack fails at
use with the pack id to fetch. On reading, measured corrections from sampled_orchestra_levels.json even the notes
(agentsound/patches/_levelling.py: no level jumps between recordings, VSCO's soft layers under the loud ones, off-key
recordings retuned). Levels: every patch at gain_db 0 lands at about -18 LUFS (the audition mix) playing its audition
material, like the other libraries. Licenses (python -m agentsound samples -v): VSCO 2 CE, VCSL and Karoryfer are
CC0; SSO is CC Sampling Plus 1.0 (credit, no advertising use); Virtual Playing Orchestra is royalty-free; No Budget
Orchestra 2 (choir_oh) is CC-BY-SA 4.0 (credit required). Version: see VERSION.
"""

from pathlib import Path

from . import Patch, _levelling, fx, inst, register

VERSION = 1

_SSO = 'samples/sso/Sonatina Symphonic Orchestra/'
_SSO_WW = _SSO + 'Woodwinds - Performance/'
_SSO_BR = _SSO + 'Brass - Performance/'
_SSO_STR = _SSO + 'Strings - Performance/'
_VSCO = 'samples/vsco2-ce/'

# --------------------------------------------------------------------------------------------- note levelling
# Measured per-zone corrections (agentsound/patches/_levelling.py): every line plays even from note to note, VSCO's
# boosted soft layers sit under the loud ones by their recorded distance (a crescendo grows), articulations balanced.
# Re-measure after changing a patch's programs: python -m agentsound.patches._levelling sampled_orchestra [patch ...]

LEVEL_TABLE = Path(__file__).with_name('sampled_orchestra_levels.json')
CALIBRATION: dict = {}          # patch name -> {'stack': bool, 'short': [articulation, ...], 'tune': bool}
PATCHES: list = []              # every patch of this module, in order


def _fix(ins):
    _levelling.apply(ins, _levelling.load_table(LEVEL_TABLE))


def _eq(hp: float, **bands):
    """Clean-up EQ: a 24 dB/oct high-pass (rumble, DC, the room's low end under the instrument's range) plus optional
    bands (peak1 low-mid, peak2 mid, peak3 presence, high shelf)."""
    return fx.eq({'hp.freq': hp, 'hp.slope': 24, **bands})


def _lazy(ins):
    ins.lazy['post'] = [f'{__name__}:_fix']
    return ins


def _ks(path: str, labels: dict, level: float, gains: dict | None = None, **kw):
    """One keyswitch program (SSO) as named articulations {'sustain': 'Sustain (looped)', ...}; its mod-wheel dynamics
    play live from 'dynamics'."""
    progs = {}
    for name, label in labels.items():
        d = {'path': path, 'articulation': label}
        if gains and gains.get(name):
            d['gain'] = gains[name]
        progs[name] = d
    return _lazy(inst.sfz_multi(progs, lazy=True, level=level, **kw))


def _multi(programs: dict, level: float, gains: dict | None = None, **kw):
    """Per-articulation programs (VSCO 2 CE: one .sfz each) as one instrument."""
    progs = {}
    for name, path in programs.items():
        d = {'path': path} if isinstance(path, str) else dict(path)
        if gains and gains.get(name):
            d['gain'] = gains[name]
        progs[name] = d
    return _lazy(inst.sfz_multi(progs, lazy=True, level=level, **kw))


def _one(path: str, level: float, **kw):
    return _lazy(inst.sfz(path, lazy=True, level=level, **kw))


def _reg(patch: Patch, stack: bool = False, short=(), tune: bool = True, keys=None) -> Patch:
    """register() + the patch's levelling spec (stack: velocity layers as a dynamics stack; short: articulations
    measured by their loudest 100 ms besides the ones named staccato / spiccato / pizzicato ... ('*': all); tune:
    retune recordings that are off their key - not for bells and drums, whose pitch a period detector misreads)."""
    CALIBRATION[patch.name] = {'stack': stack, 'short': list(short), 'tune': tune, 'keys': keys}
    return _add(patch)


def _add(patch: Patch) -> Patch:
    PATCHES.append(patch.name)
    return register(patch)


_WIND = dict(mono='legato', legatotime=60, polyphony=16)
_VSCO_DYN = dict(layers='dynamics', xfspread=2, dynrange=12, dyntone=0.4, dynamics=0.6)
_SSO_SOLO = {'sustain': 'Sustain (looped)', 'legato': 'Legato', 'marcato': 'Marcato (looped)', 'staccato': 'Staccato'}
_SSO_REED = {'sustain': 'Sustain (looped)', 'legato': 'Legato', 'staccato': 'Staccato'}


# --------------------------------------------------------------------------------------------- credits / how to play

_VSCO_C = 'VSCO 2 Community Edition (Versilian Studios). License CC0 (no credit required).'
_SSO_C = ('Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, Peter Eastman). License CC Sampling Plus 1.0: fine in '
          'music, credit "Sonatina Symphonic Orchestra", not for use in advertising.')
_VPO_C = ('Virtual Playing Orchestra 3 (Paul Battersby; samples from SSO, No Budget Orchestra, VSCO 2 CE). License '
          'royalty-free (credit appreciated); needs the packs vpo-scripts-* and vpo-wav.')
_VCSL_C = 'VCSL - Versilian Community Sample Library (Versilian Studios). License CC0 (no credit required).'
_KF_C = 'Karoryfer Samples. License CC0 (credit optional).'
_LEGATO = ('A monophonic legato player (mono=\'legato\'): overlapping notes are legato transitions without a new '
           'attack (articulation.legato / articulation.perform tie phrases), a note after a rest attacks; '
           'clip.glide(ms) for portamento. Breathe: leave gaps between phrases.')
_STACK = ('Live dynamics: the recorded p / mf / f layers crossfade while a note sounds (layers=\'dynamics\'): automate '
          '\'dynamics\' 0..1 (default 0.6 = mf; articulation.expression / perform write swells and crescendi); '
          'velocity shapes the attack.')
_MODW = ('Live dynamics: the library\'s mod-wheel dynamics (level + a filter that opens) play from \'dynamics\' 0..1 '
         '(default 0.6 = mf): automate it for swells and crescendi (articulation.expression / perform); velocity '
         'shapes the attack.')
_ARTS = ('Articulations are keyswitches inside the patch: clip.articulate(\'staccato\', span=...) or '
         'articulation.auto_articulate (short notes -> staccato); unmarked notes play the first one.')
_EVEN = ('Levelled: measured per-zone corrections even the notes out (no jumps between recordings) and retune '
         'recordings that were off their key.')


# --------------------------------------------------------------------------------------------- woodwinds

_reg(Patch(
    'sampled/piccolo',
    instrument=_ks(_SSO_WW + 'Piccolo Solo KS.sfz', _SSO_SOLO, level=1.6, gains={'marcato': -2.1, 'staccato': -9.7},
                   dynamics=0.6, **_WIND),
    fx=[_eq(400)],
    sends={'hall': -8},
    notes='v1. Solo piccolo, ' + _SSO_C + ' Articulations: sustain (looped), legato, marcato (looped), staccato. '
          'Range C5-G7 (sounding); festive top line of a tutti, doubling the flute or violins an octave up, trills '
          'and marches; tiring above C7, use it briefly. ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS + ' ' + _EVEN +
          ' Sends: hall -8. Measured -18.0 LUFS (audition phrase, octave 5).',
    audition={'notes': 'phrase', 'octave': 5}))

_reg(Patch(
    'sampled/solo_flute',
    instrument=_multi({'sustain': _VSCO + 'FluteSusVib.sfz', 'non-vibrato': _VSCO + 'FluteSusNV.sfz',
                       'expressive': _VSCO + 'FluteExpVib.sfz', 'staccato': _VSCO + 'FluteStac.sfz'},
                      level=6.4, gains={'non-vibrato': 3.1, 'expressive': 6.0, 'staccato': 6.9}, **_VSCO_DYN, **_WIND),
    fx=[_eq(220)],
    sends={'hall': -9},
    notes='v1. Played solo flute (the played counterpart of sampled/flute), ' + _VSCO_C + ' Articulations: sustain '
          '(vibrato), non-vibrato, expressive (a swelling vibrato note: long notes in a ballad), staccato (4 '
          'velocity layers x 2 round robins, F4 up). Range C4-C7; sweet spot G4-G6, the low octave is soft and breathy '
          '(quiet textures only), the top brilliant. ' + _LEGATO + ' ' + _STACK + ' ' + _ARTS + ' ' + _EVEN +
          ' Sends: hall -9. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}), stack=True)

_reg(Patch(
    'sampled/alto_flute',
    instrument=_ks(_SSO_WW + 'Alto Flute Solo KS.sfz', _SSO_SOLO, level=3.2, gains={'marcato': 1.0, 'staccato': -8.7},
                   dynamics=0.6, **_WIND),
    fx=[_eq(150)],
    sends={'hall': -9},
    notes='v1. Solo alto flute (in G, sounding pitch), ' + _SSO_C + ' Articulations: sustain (looped), legato, marcato '
          '(looped), staccato. Range G3-G6, sweet spot G3-D5: a dark, breathy, intimate colour for film and ballads '
          '(best in soft textures, low strings under it). ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS + ' ' + _EVEN +
          ' Sends: hall -9. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}))

_reg(Patch(
    'sampled/solo_oboe',
    instrument=_multi({'sustain': _VSCO + 'OboeSusVib.sfz', 'non-vibrato': _VSCO + 'OboeSusNV.sfz',
                       'staccato': _VSCO + 'OboeStac.sfz'}, level=12.5, gains={'non-vibrato': -0.8, 'staccato': -7.6},
                      **_VSCO_DYN, **_WIND),
    fx=[_eq(200)],
    sends={'hall': -9},
    notes='v1. Played solo oboe (the played counterpart of sampled/oboe), ' + _VSCO_C + ' Articulations: sustain '
          '(vibrato), non-vibrato (baroque / pastoral lines), staccato (3 layers x 2 round robins). Range A#3-F6, '
          'sweet spot D4-D6: the plaintive solo voice; weak pp at the bottom. ' + _LEGATO + ' ' + _STACK + ' ' +
          _ARTS + ' ' + _EVEN + ' Sends: hall -9. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}), stack=True)

_reg(Patch(
    'sampled/english_horn',
    instrument=_ks(_SSO_WW + 'Cor Anglais Solo KS.sfz', _SSO_REED, level=3.8, gains={'staccato': -5.2}, dynamics=0.6,
                   **_WIND),
    fx=[_eq(130)],
    sends={'hall': -9},
    notes='v1. Solo English horn / cor anglais (sounding pitch), ' + _SSO_C + ' Articulations: sustain (looped), '
          'legato, staccato. Range F3-F5 (the samples; the instrument reaches E3-C6), sweet spot G3-G5: the '
          'melancholic solo (Dvorak 9 Largo, film nostalgia) over soft strings. ' + _LEGATO + ' ' + _MODW + ' ' +
          _ARTS + ' ' + _EVEN + ' Sends: hall -9. Measured -18.0 LUFS (audition phrase, octave 3).',
    audition={'notes': 'phrase', 'octave': 3}))

_reg(Patch(
    'sampled/solo_clarinet',
    instrument=_multi({'sustain': _VSCO + 'ClarinetSus.sfz', 'staccato': _VSCO + 'ClarinetStac.sfz'},
                      level=6.6, gains={'staccato': -1.2}, **_VSCO_DYN, **_WIND),
    fx=[_eq(130)],
    sends={'hall': -9},
    notes='v1. Played solo clarinet in Bb (sounding pitch; the played counterpart of sampled/clarinet), ' + _VSCO_C +
          ' Articulations: sustain (3 layers), staccato (3 layers x 2 round robins). Range D3-F#6: the chalumeau '
          'D3-E4 dark and rich (a little softer, as played), the clarion A4-A#5 bright; the best pianissimo of the '
          'winds - fade in from dynamics 0.1. ' + _LEGATO + ' ' + _STACK + ' ' + _ARTS + ' ' + _EVEN +
          ' Sends: hall -9. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}), stack=True)

_reg(Patch(
    'sampled/bass_clarinet',
    instrument=_ks(_SSO_WW + 'Bass Clarinet Solo KS.sfz', _SSO_REED, level=2.8, gains={'staccato': -4.9}, dynamics=0.6,
                   **_WIND),
    fx=[_eq(60)],
    sends={'hall': -10},
    notes='v1. Solo bass clarinet (sounding pitch), ' + _SSO_C + ' Articulations: sustain (looped), legato, staccato. '
          'Range D2-D5, sweet spot D2-C4: a soft velvet bass that doubles cellos or bassoons, dark film ostinatos, '
          'jazz-noir lines. ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS + ' ' + _EVEN + ' Sends: hall -10. Measured '
          '-18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}))

_reg(Patch(
    'sampled/bassoon',
    instrument=_multi({'sustain': _VSCO + 'BassoonSus.sfz', 'vibrato': _VSCO + 'BassoonVib.sfz',
                       'staccato': _VSCO + 'BassoonStac.sfz'}, level=6.0, gains={'vibrato': -2.4, 'staccato': -2.7},
                      **_VSCO_DYN, **_WIND),
    fx=[_eq(50)],
    sends={'hall': -10},
    notes='v1. Solo bassoon, ' + _VSCO_C + ' Articulations: sustain (straight tone, 2 layers, the full range A#1-D#5), '
          'vibrato (recorded vibrato, 3 layers, C2-C5 only - or add articulation.vibrato to the sustain), staccato '
          '(2 layers x 2 round robins: the witty bassoon staccato). Range A#1-D#5, sweet spot A#1-G4; D3-D4 is its '
          'lyrical tenor. The bass of the woodwinds: doubles cellos, walks under clarinets. ' + _LEGATO + ' ' +
          _STACK + ' ' + _ARTS + ' ' + _EVEN + ' Sends: hall -10. Measured -18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}), stack=True)

_reg(Patch(
    'sampled/contrabassoon',
    instrument=_ks(_SSO_WW + 'Contrabassoon Solo KS.sfz', _SSO_REED, level=2.3, gains={'staccato': -5.0},
                   dynamics=0.6, **_WIND),
    fx=[_eq(28)],
    sends={'hall': -10},
    notes='v1. Contrabassoon (sounding pitch), ' + _SSO_C + ' Articulations: sustain (looped), legato, staccato. Range '
          'A#0-A#3: the organ pedal of the orchestra - doubles the double basses an octave down or the tuba, slow '
          'grotesque solos (Ravel). ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS + ' ' + _EVEN + ' Sends: hall -10. '
          'Measured -18.0 LUFS (audition phrase, octave 1).',
    audition={'notes': 'phrase', 'octave': 1}))

_reg(Patch(
    'sampled/bari_sax',
    instrument=_one('samples/karoryfer-bear-sax/Programs/1-solo-mono.sfz', level=8.9, mono='legato', legatotime=50,
                    polyphony=24),
    fx=[_eq(45)],
    sends={'plate': -14},
    notes='v1. Bear Sax: a 1926 Conn baritone saxophone, ' + _KF_C + ' Articulations (live keyswitches of the file): '
          'sustain, marcato, staccato, growl, sub (subtone: soft, breathy); scripted legato transitions and '
          'round robins. Range C2-G#4 (sounding). Funk / soul / rock horn sections (the bottom of trumpet + tenor + '
          'bari riffs, octave-doubled bass riffs), jazz ballads (sub), rock-and-roll honks (growl). ' + _LEGATO +
          ' Live dynamics: the file\'s CC1 dynamics play from \'dynamics\' (default 0.5, about 11 dB from 0.1 to 1); '
          'velocity does not change the level - write the lane (articulation.perform turns velocities into it). '
          'Tweak (import settings, '
          'your own inst.sfz of the file): cc={111: 40} vibrato depth, cc={122: 60} breath noise, cc={121: 60} '
          'fingering noise. Sends: plate -14. Measured -18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}))

# --------------------------------------------------------------------------------------------- brass

_reg(Patch(
    'sampled/solo_trumpet',
    instrument=_multi({'sustain': _VSCO + 'TrumpetSus.sfz', 'vibrato': _VSCO + 'TrumpetSusVib.sfz',
                       'staccato': _VSCO + 'TrumpetStac.sfz', 'harmon': _VSCO + 'TrumpetHarmonMuteSus.sfz',
                       'straight mute': _VSCO + 'TrumpetStraightMuteSus.sfz'}, level=-2.2,
                      gains={'vibrato': 12.5, 'staccato': 11.9, 'harmon': 6.5, 'straight mute': 3.5},
                      **_VSCO_DYN, **_WIND),
    fx=[_eq(150)],
    sends={'hall': -9},
    notes='v1. Played solo trumpet in C (the played counterpart of sampled/trumpet), ' + _VSCO_C + ' Articulations: '
          'sustain (straight tone), vibrato (lyrical solos, ballads), staccato (3 layers x 2 round robins: fanfares, '
          'repeated notes), harmon (Harmon mute: the intimate jazz-ballad sound, sampled/trumpet_harmon has it as '
          'default), straight mute (a thin, nasal colour); the mutes A#3-C6. Range E3-C6, sweet spot C4-G5. ' +
          _LEGATO + ' ' + _STACK + ' ' + _ARTS + ' ' + _EVEN + ' Sends: hall -9 (a plate for pop / jazz). Measured '
          '-18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}), stack=True)

_reg(Patch(
    'sampled/trumpet_harmon',
    instrument=_one(_VSCO + 'TrumpetHarmonMuteSus.sfz', level=8.2, **_VSCO_DYN, **_WIND),
    fx=[_eq(200)],
    sends={'plate': -12},
    notes='v1. Trumpet with a Harmon mute (stem out): the breathy, buzzing muted trumpet of jazz ballads and cool '
          'jazz, film noir and lounge; ' + _VSCO_C + ' 2 layers. Range A#3-C6, sweet spot D4-G5; play soft '
          '(dynamics 0.3-0.6), few notes, space between phrases, a delayed vibrato on the long notes '
          '(articulation.vibrato). ' + _LEGATO + ' ' + _STACK + ' ' + _EVEN + ' Sends: plate -12. Measured '
          '-18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}), stack=True)

_reg(Patch(
    'sampled/solo_horn',
    instrument=_multi({'sustain': _VSCO + 'FHornSus.sfz', 'staccato': _VSCO + 'FHornStac.sfz',
                       'muted': _VSCO + 'FHornMute.sfz'}, level=4.4, gains={'staccato': -1.1},
                      **_VSCO_DYN, **_WIND),
    fx=[_eq(60)],
    sends={'hall': -7},
    notes='v1. Solo French horn, ' + _VSCO_C + ' Articulations: sustain (4 layers), staccato (5 layers x 2 round '
          'robins), muted (stopped / muted, 3 layers, A#2-F5; softer and distant). Range A1-F5 (sounding), sweet spot '
          'C3-C5; the lowest notes are softer, as played. Noble solos, heroic unison themes (double it with '
          'sampled/horn_section), calls. ' + _LEGATO + ' ' + _STACK + ' ' + _ARTS + ' ' + _EVEN + ' Sends: hall -7 '
          '(horns sit back in the room). Measured -18.0 LUFS (audition phrase, octave 3).',
    audition={'notes': 'phrase', 'octave': 3}), stack=True)

_reg(Patch(
    'sampled/solo_trombone',
    instrument=_ks(_SSO_BR + 'Tenor Trombone Solo KS.sfz', _SSO_SOLO, level=1.2,
                   gains={'marcato': 2.0, 'staccato': -2.2}, dynamics=0.6, **_WIND),
    fx=[_eq(55)],
    sends={'hall': -8},
    notes='v1. Solo tenor trombone, ' + _SSO_C + ' Articulations: sustain (looped), legato, marcato (looped), '
          'staccato. Range E2-B4, sweet spot F2-F4: chorales, lyrical solos, big-band and ska lines; glissandi: '
          'clip.glide(250-400) between legato notes (a trombone slides). ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS +
          ' ' + _EVEN + ' Sends: hall -8. Measured -18.0 LUFS (audition phrase, octave 3).',
    audition={'notes': 'phrase', 'octave': 3}))

_reg(Patch(
    'sampled/bass_trombone',
    instrument=_ks(_SSO_BR + 'Bass Trombone Solo KS.sfz', _SSO_SOLO, level=2.8,
                   gains={'marcato': 2.0, 'staccato': -2.1}, dynamics=0.6, **_WIND),
    fx=[_eq(35)],
    sends={'hall': -8},
    notes='v1. Bass trombone, ' + _SSO_C + ' Articulations: sustain (looped), legato, marcato (looped), staccato. '
          'Range E1-G4, sweet spot F1-F3: the bottom of the brass with the tuba, film "braams" (marcato fff open fifths / '
          'clusters with tuba and horns), menacing low lines. ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS + ' ' +
          _EVEN + ' Sends: hall -8. Measured -18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}))

_reg(Patch(
    'sampled/tuba',
    instrument=_multi({'sustain': _VSCO + 'TubaSus.sfz', 'staccato': _VSCO + 'TubaStac.sfz'}, level=9.8,
                      gains={'staccato': -0.5}, **_VSCO_DYN, **_WIND),
    fx=[_eq(25)],
    sends={'hall': -8},
    notes='v1. Orchestral tuba, ' + _VSCO_C + ' Articulations: sustain (3 layers, two microphones), staccato (2 layers '
          'x 4 round robins). Range F1-D4, sweet spot F1-F3: the foundation of the brass (octaves with the basses, '
          'the bass of brass chorales); sparing in soft music. The lowest recordings (F1-G1) waver up to 30 ct at '
          'the start of a note, as played. ' + _LEGATO + ' ' + _STACK + ' ' + _ARTS + ' ' + _EVEN + ' Sends: hall '
          '-8. Measured -18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}), stack=True)

_reg(Patch(
    'sampled/war_tuba',
    instrument=_multi({'sustain': {'path': 'samples/karoryfer-war-tuba/Programs/1-solo-legato.sfz',
                                   'articulation': 'Sustain'},
                       'staccato': {'path': 'samples/karoryfer-war-tuba/Programs/1-solo-legato.sfz',
                                    'articulation': 'Staccato'},
                       'staccatissimo': {'path': 'samples/karoryfer-war-tuba/Programs/1-solo-legato.sfz',
                                         'articulation': 'Staccatissimo'}},
                      level=3.3, mono='legato', legatotime=50, polyphony=24),
    fx=[_eq(25)],
    sends={'plate': -16},
    notes='v1. War Tuba: a solo tuba played close and punchy (folk-punk, brass band), ' + _KF_C + ' Articulations: '
          'sustain, staccato, staccatissimo; 5 dynamic layers x up to 10 round robins, two microphones. Range '
          'D#1-C4 (C#4-E4: valve and mechanical noises, for effect). Oom-pah and polka bass (staccato on 1 and 3), '
          'New Orleans / brass-band bass lines, balkan, comedic film cues, rock with horns - a rougher, closer tuba '
          'than sampled/tuba. Sustained notes last about 6 s (the recordings end; one microphone stops first with an '
          'audible tick): re-attack or breathe before that. ' + _LEGATO + ' Live '
          'dynamics: the file\'s CC1 dynamics play from \'dynamics\' (default 0.5; the recorded layers, about 20 dB '
          'from 0.1 to 1); velocity does not change the level - write the lane (articulation.perform turns '
          'velocities into it). ' +
          _ARTS + ' ' + _EVEN + ' Sends: plate -16. Measured -18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}), keys=(27, 60))

_SSO_SEC = {'sustain': 'Sustain (looped)', 'marcato': 'Marcato (looped)', 'staccato': 'Staccato', 'legato': 'Legato'}
_SECTION = ('A polyphonic section: chords and unison lines; one track per section, the articulations switch per note.')

_reg(Patch(
    'sampled/trumpet_section',
    instrument=_ks(_SSO_BR + 'Trumpets KS.sfz', _SSO_SEC, level=-5.2, gains={'marcato': 4.7, 'staccato': -4.3},
                   dynamics=0.6, polyphony=64),
    fx=[_eq(150)],
    sends={'hall': -7},
    notes='v1. Trumpet section (a3), ' + _SSO_C + ' Articulations: sustain (looped), marcato (looped), staccato, '
          'legato. Range E3-E6, sweet spot C4-G5: fanfares, climaxes, film brass stabs (marcato / staccato chords), '
          'pop and funk horn hits (with sampled/trombone_section and a sax). ' + _SECTION + ' ' + _MODW + ' ' + _ARTS +
          ' ' + _EVEN + ' Sends: hall -7. Measured -18.0 LUFS (audition chords, octave 5).',
    audition={'notes': 'chord', 'octave': 5}))

_reg(Patch(
    'sampled/horn_section',
    instrument=_ks(_SSO_BR + 'Horns KS.sfz', {'sustain': 'Sustain', 'marcato': 'Marcato', 'staccato': 'Staccato',
                                              'legato': 'Legato'}, level=-8.3, gains={'marcato': 2.6, 'staccato': -3.0},
                   dynamics=0.6, polyphony=64),
    fx=[_eq(60)],
    sends={'hall': -6},
    notes='v1. French horn section (a4), played: ' + _SSO_C + ' Articulations: sustain, marcato, staccato, legato (the '
          'plain sustain section: sampled/french_horns). Range E2-F5, sweet spot C3-C5: the glue of the orchestra '
          '(sustained harmony), heroic unison themes (film), swells. ' + _SECTION + ' ' + _MODW + ' ' + _ARTS + ' ' +
          _EVEN + ' Sends: hall -6 (horns face backwards: more room). Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

_reg(Patch(
    'sampled/trombone_section',
    instrument=_ks(_SSO_BR + 'Trombones KS.sfz', _SSO_SEC, level=-7.2, gains={'marcato': 5.0, 'staccato': 0.7},
                   dynamics=0.6, polyphony=64),
    fx=[_eq(55)],
    sends={'hall': -7},
    notes='v1. Trombone section (a3), played: ' + _SSO_C + ' Articulations: sustain (looped), marcato (looped), '
          'staccato, legato (the plain sustain section: sampled/trombones). Range E2-F5, sweet spot F2-F4: chorales, '
          'weight, ff power, film ostinatos in marcato / staccato. ' + _SECTION + ' ' + _MODW + ' ' + _ARTS + ' ' +
          _EVEN + ' Sends: hall -7. Measured -18.0 LUFS (audition chords, octave 3).',
    audition={'notes': 'chord', 'octave': 3}))

# --------------------------------------------------------------------------------------------- strings

_VPO_PERF = 'samples/vpo-scripts-performance/Strings/'

_reg(Patch(
    'sampled/string_section',
    instrument=_multi({'sustain': _VPO_PERF + 'all-strings-SEC-PERF-panned.sfz',
                       'staccato': _VPO_PERF + 'all-strings-SEC-PERF-staccato-panned.sfz',
                       'pizzicato': _VPO_PERF + 'all-strings-SEC-PERF-pizzicato-panned.sfz',
                       'tremolo': _VPO_PERF + 'all-strings-SEC-PERF-tremolo-panned.sfz',
                       'col legno': _SSO_STR + 'All Strings Col Legno.sfz'},
                      level=5.5, gains={'staccato': 0.4, 'pizzicato': -4.2, 'tremolo': -0.6, 'col legno': -2.3},
                      dynamics=0.6, polyphony=160),
    fx=[_eq(35)],
    sends={'hall': -7},
    notes='v1. Full string orchestra in one instrument, played (the plain sustain: sampled/strings): violins, violas, '
          'cellos and basses split by register and seated (violins left, basses right). ' + _VPO_C + ' Col legno '
          'from ' + _SSO_C + ' Articulations: sustain, staccato, pizzicato, tremolo, col legno (the wood of the '
          'bow: ghostly ticks). Section harmonics are left out: the SSO harmonic loops click on held notes (solo '
          'harmonics: sampled/solo_viola, sampled/solo_bass). Range C1-A7; 4-6 note voicings C2-C6, the bass an octave '
          'under the cellos. Pads and chorales that swell with \'dynamics\', pop / film ostinatos in staccato, '
          'tremolo tension beds, pizzicato accompaniment. ' + _SECTION + ' ' + _MODW + ' ' + _ARTS + ' ' + _EVEN +
          ' Sends: hall -7. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

_reg(Patch(
    'sampled/strings_tremolo',
    instrument=_one(_VPO_PERF + 'all-strings-SEC-PERF-tremolo-panned.sfz', level=5.7, dynamics=0.6, polyphony=128),
    fx=[_eq(35)],
    sends={'hall': -7},
    notes='v1. String section tremolo (bowed very fast): the tension bed of film and thriller cues, dramatic swells, '
          'shimmering chords behind a climax. ' + _VPO_C + ' Range C1-A7, seated like an orchestra. Hold chords and '
          'automate \'dynamics\' (0.15 -> 0.9 over 2-4 bars for the classic swell); ' + _MODW + ' ' + _EVEN +
          ' Sends: hall -7. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

_reg(Patch(
    'sampled/solo_viola',
    instrument=_ks(_SSO_STR + 'Viola Solo KS.sfz', {'sustain': 'Sustain', 'legato': 'Legato', 'marcato': 'Marcato',
                                                    'staccato': 'Staccato', 'pizzicato': 'Pizzicato',
                                                    'harmonics': 'Harmonics'},
                   level=7.2, gains={'marcato': 2.0, 'staccato': -5.7, 'pizzicato': -5.0, 'harmonics': 3.0},
                   dynamics=0.6, mono='legato', legatotime=80, polyphony=16),
    fx=[_eq(110)],
    sends={'hall': -9},
    notes='v1. Solo viola, ' + _SSO_C + ' Articulations: sustain (looped), legato, marcato, staccato, pizzicato, '
          'harmonics. Range C3-E6, sweet spot C3-C5: dark, veiled, the inner voice of a quartet; lyrical solos a '
          'fourth or fifth under a violin line. Bowing: rebow long notes every few seconds (bandlib.orchestra.rebow) '
          'and add a delayed vibrato (articulation.vibrato). ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS + ' ' + _EVEN +
          ' Sends: hall -9. Measured -18.0 LUFS (audition phrase, octave 3).',
    audition={'notes': 'phrase', 'octave': 3}))

_reg(Patch(
    'sampled/solo_bass',
    instrument=_ks(_SSO_STR + 'Bass Solo KS.sfz', {'sustain': 'Sustain', 'legato': 'Legato', 'marcato': 'Marcato',
                                                   'staccato': 'Staccato', 'pizzicato': 'Pizzicato',
                                                   'harmonics': 'Harmonics'},
                   level=11.2, gains={'marcato': 1.1, 'staccato': -6.5, 'pizzicato': -7.1, 'harmonics': 3.0},
                   dynamics=0.6, mono='legato', legatotime=80, polyphony=16),
    fx=[_eq(30)],
    sends={'hall': -9},
    notes='v1. Solo double bass, bowed (arco; pizzicato as an articulation), ' + _SSO_C + ' Articulations: sustain '
          '(looped), legato, marcato, staccato, pizzicato, harmonics. Range C1-G4 (sounding), sweet spot E1-D3: the '
          'bass of a string quartet+bass or chamber group, dark solo lines (Saint-Saens\' elephant), long pedal '
          'notes. For a jazz walking bass use sampled/upright_bass. ' + _LEGATO + ' ' + _MODW + ' ' + _ARTS + ' ' +
          _EVEN + ' Sends: hall -9. Measured -18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}))

# --------------------------------------------------------------------------------------------- mallets, bells, harp

_VCSL = 'samples/vcsl/Idiophones/Struck Idiophones/'
_STRUCK = ('Velocity is the dynamics (the recorded layers crossfade with velocity: vary it, 60-110, accents higher); '
           'notes ring on after the key is released (let them).')

_reg(Patch(
    'sampled/glockenspiel',
    instrument=_one(_VCSL + 'Glockenspiel.sfz', level=-1.5, transpose=-12, polyphony=64),
    fx=[_eq(400)],
    sends={'hall': -8},
    notes='v1. Orchestral glockenspiel (steel bars, brass mallets; soft / medium / loud strokes crossfaded), ' +
          _VCSL_C + ' Played at SOUNDING pitch: range G5-C#8 (write the part 2 octaves up from the score, or use '
          'the melody an octave or two above the violins). Doubles a melody at the top for sparkle (Christmas, '
          'fairy tale, pop intros), single notes and simple lines, not chords. ' + _STRUCK + ' ' + _EVEN +
          ' Sends: hall -8. Measured -18.0 LUFS (audition arpeggio, octave 6).',
    audition={'notes': 'arp', 'octave': 6}), short=('*',))

_reg(Patch(
    'sampled/xylophone',
    instrument=_ks(_VCSL + 'Xylophone - Keyswitch.sfz', {'hard': 'Hard Mallets', 'medium': 'Medium Mallets',
                                                         'soft': 'Soft Mallets'},
                   level=-2.7, transpose=-12, polyphony=64),
    fx=[_eq(200)],
    sends={'hall': -9},
    notes='v1. Xylophone, ' + _VCSL_C + ' Mallets as articulations: hard (default: dry, bright, the classic '
          'orchestral xylophone), medium, soft (rounder, marimba-like); 2 velocity layers each. Played at SOUNDING '
          'pitch: range G4-C#8 (an octave above the written part). Fast staccato doubling of a melody or ostinato, '
          'skeleton dances, cartoon runs; repeated notes and short rolls (fast 16ths / 32nds, vary velocity). '
          'The top fifth (G7 up) is about 20 ct sharp and very short. ' + _STRUCK + ' ' + _ARTS + ' ' + _EVEN +
          ' Sends: hall -9. Measured -18.0 LUFS (audition arpeggio, octave 5).',
    audition={'notes': 'arp', 'octave': 5}), short=('*',))

_reg(Patch(
    'sampled/marimba',
    instrument=_one(_VCSL + 'Marimba.sfz', level=-3.9, polyphony=64),
    fx=[_eq(60)],
    sends={'hall': -10},
    notes='v1. Concert marimba (rosewood bars, soft / medium / loud strokes crossfaded by velocity), ' + _VCSL_C +
          ' Range F2-C#7. Minimalist patterns (Reich), film ostinatos, warm pop / world grooves, 2-4 note chords '
          '(one per hand pair); long notes as rolls (repeated 32nds at velocity 50-70). The real counterpart of '
          'synthwave/marimba. ' + _STRUCK + ' ' + _EVEN + ' Sends: hall -10. Measured -18.0 LUFS (audition '
          'arpeggio).',
    audition={'notes': 'arp'}), short=('*',))

_reg(Patch(
    'sampled/tubular_bells',
    instrument=_one(_VCSL + 'Tubular Bells 2.sfz', level=-0.8, polyphony=64),
    fx=[_eq(120)],
    sends={'hall': -7},
    notes='v1. Tubular bells / chimes (2 velocity layers), ' + _VCSL_C + ' Range C4-G5. Bells at climaxes, weddings, '
          'funerals, the hour strike; single notes or slow bell patterns on the downbeats, octaves with the '
          'glockenspiel for brilliance. A bell\'s perceived pitch comes from its upper partials: tuning left as '
          'recorded. ' + _STRUCK + ' ' + _EVEN + ' Sends: hall -7. Measured -18.0 LUFS (audition hits C5).',
    audition={'notes': 'hit', 'pitch': 'C5', 'length': 4}), short=('*',), tune=False)

_reg(Patch(
    'sampled/concert_harp',
    instrument=_one('samples/vcsl/Chordophones/Composite Chordophones/Concert Harp.sfz', level=0.5, polyphony=96),
    fx=[_eq(45)],
    sends={'hall': -9},
    notes='v1. Concert pedal harp, 2 layers (mp / f) crossfaded by velocity, the full range E1-F#7 (the source of '
          'the FreePats concert harp), ' + _VCSL_C + ' An alternative to sampled/harp (a single layer): arpeggios '
          'over 2-3 octaves, glissandi (fast diatonic scales of 32nds), rolled chords (clip.strum), bass notes '
          'ringing under the strings. Strings ring about 30 s: notes are not cut at note-off (write a harpist\'s '
          'ring; mute by letting the harmony change). The bass octave is softer, as played. ' + _STRUCK + ' ' +
          _EVEN + ' Sends: hall -9. Measured -18.0 LUFS (audition arpeggio).',
    audition={'notes': 'arp'}), short=('*',))

_reg(Patch(
    'sampled/timpani_rolls',
    instrument=_multi({'roll': _VSCO + 'TimpaniRolls.sfz', 'hit': _VSCO + 'Timpani.sfz'}, level=7.2, polyphony=32),
    fx=[_eq(30)],
    sends={'hall': -9},
    notes='v1. Timpani with rolls: roll (default; recorded 17-24 s rolls, 2 layers: a held note is a roll that '
          'lasts as long as the note - crescendo it with velocity + expression automation) and hit (3 layers x 2 '
          'round robins) as keyswitch articulations (clip.articulate(\'hit\')); ' + _VSCO_C + ' Range C2-C4 '
          '(tune the drums to tonic and dominant: D2-A2, F2-C3, A#2-F3, D3-A3). Swells into downbeats (roll, then a '
          'hit on the one), dramatic rolls under a tutti. The plain hits: sampled/timpani. ' + _STRUCK + ' ' + _EVEN +
          ' Sends: hall -9. Measured -18.0 LUFS (audition roll A2).',
    audition={'notes': 'hit', 'pitch': 'A2', 'length': 4}), tune=False)

_add(Patch(
    'sampled/orchestral_percussion',
    instrument=inst.sfz(_VSCO + 'GM-StylePerc.sfz', lazy=True, level=-4.2, polyphony=64),
    fx=[_eq(25)],
    sends={'hall': -8},
    notes='v1. Orchestral percussion on GM-style keys, ' + _VSCO_C + ' Concert bass drum (7 layers x 2 round robins), '
          'concert snare (hits, rolls, taps), suspended cymbal (hits, bowed, crescendo swells - short / medium / '
          'long - and scrapes), crash cymbals, gong / tam-tam (hits p..fff, scrapes), triangles (hits, rolls), '
          'tambourine (hits, rolls, shakes), sleigh bells, anvil, bell tree, brake drum, claves, cowbell, congas, '
          'log drums, guiro, ratchet: python -m agentsound sfz samples/vsco2-ce/GM-StylePerc.sfz lists the keys. '
          'Film accents (bass drum + cymbal on the downbeat of a climax, a suspended-cymbal swell into it), '
          'marches (snare), Christmas (sleigh bells, triangle). Velocity is the dynamics. Sends: hall -8. Measured '
          '-18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

# --------------------------------------------------------------------------------------------- choirs

_CHOIR_DYN = dict(dynamics=0.6, dynrange=18, dyntone=0.5, polyphony=128)
_CHOIR = ('Live dynamics: \'dynamics\' 0..1 (default 0.6) moves the level (18 dB) and the brightness of the held '
          'chords - automate it for swells (0.2 -> 0.8 over two bars) and fades; velocity sets the attack level.')
_SEAMS = ('Notes held longer than ~2 s pass faint loop seams that the analysis may flag as medium clicks when the '
          'choir is exposed (masked under a hall and other parts; like sampled/choir); sampled/choir_oh loops '
          'cleanly.')

_reg(Patch(
    'sampled/choir_mixed',
    instrument=_one('samples/vpo-scripts-standard/Vocals/choir-MIXED-sustain.sfz', level=0.5, **_CHOIR_DYN),
    fx=[_eq(110)],
    sends={'hall': -6},
    notes='v1. Mixed choir (sopranos, altos, tenors, basses) singing "ah": the Sonatina Symphonic Orchestra chorus '
          're-looped by Virtual Playing Orchestra (clean loops; the SSO originals click at some loop points). ' +
          _VPO_C + ' Range G2-C6 (each voice where it sings: B E2-E4, T C3-A4, A G3-E5, S C4-A5). Film choir pads, '
          'chorales, the epic "ah" over a climax; voice it like a choir (4 parts, not piano chords). ' + _CHOIR +
          ' ' + _SEAMS +
          ' ' + _EVEN + ' Sends: hall -6. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

_reg(Patch(
    'sampled/choir_male',
    instrument=_one('samples/vpo-scripts-standard/Vocals/choir-MALE-sustain.sfz', level=2.0, **_CHOIR_DYN),
    fx=[_eq(80)],
    sends={'hall': -6},
    notes='v1. Male choir (tenors and basses) "ah", ' + _VPO_C + ' Range G2-F#4: dark, monastic, epic low choir - '
          'film battle and fantasy cues (open fifths and octaves), chant-like unison lines, the bottom of a mixed '
          'choir with sampled/choir (female). ' + _CHOIR + ' ' + _SEAMS + ' ' + _EVEN + ' Sends: hall -6. '
          'Measured -18.0 LUFS '
          '(audition chords, octave 3).',
    audition={'notes': 'chord', 'octave': 3}))

_reg(Patch(
    'sampled/choir_oh',
    instrument=_one('samples/nbo-2/Choir/choir.sfz', level=0.3, **_CHOIR_DYN),
    fx=[_eq(110)],
    sends={'hall': -6},
    notes='v1. Choir singing "oh" (a round, warm vowel; clean loops), No Budget Orchestra 2 (Jeff Glatt and the '
          'sample authors named in its license.txt). License CC-BY-SA 4.0: credit "No Budget Orchestra" (the build '
          'lists it in credits.txt), share-alike. Samples D2-C#5, one every 2-3 semitones (above C#5 the top sample '
          'is stretched: keep real parts at C#5 and under; a soprano line above it on sampled/choir_mixed). '
          'Soft, rounded pads under strings, hymns, the "ooh"-like colour for ballads. ' + _CHOIR + ' ' + _EVEN +
          ' Sends: hall -6. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))
