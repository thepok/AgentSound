"""Sampled orchestra, part 3 (instrument 'sampler'): the symphonic sections one per track - the five string sections
of a full orchestra and the woodwinds a2 / a3 - played (keyswitched articulations, live mod-wheel dynamics), and
muted brass sections.

  strings:    sampled/violins_1 sampled/violins_2 sampled/violas sampled/celli sampled/double_basses
  woodwinds:  sampled/flutes sampled/oboes sampled/clarinets sampled/bassoons
  muted:      sampled/horns_muted sampled/trumpets_muted

The full string orchestra in one instrument is sampled/string_section; the chamber-size VSCO sections (a desk or two)
are sampled/violin_section / viola_section / cello_section / bass_section; the soloists live in sampled_orchestra.py.
These are the symphonic sizes: write a 5-part string texture (violins I / II, violas, celli, basses) on five tracks,
each section seated where an orchestra sits it (pan in the patch).

Strings: the sustain, staccato, pizzicato and tremolo are Virtual Playing Orchestra 3's 'performance' programs (the
Sonatina / No Budget Orchestra / VSCO sections re-looped by Paul Battersby: the SSO's own sustain loops click on violas,
celli and basses), marcato and col legno the Sonatina Symphonic Orchestra 4.0 keyswitch programs - one 'dynamics'
lane (the libraries' mod wheel) for all of them. Woodwinds: the SSO a2 / a3 sections (oboes: the VPO re-loop of the
SSO oboes for the sustain). Muted brass: VSCO 2 CE solo mute recordings played as a3 sections (three players: the
neighbouring recordings of each note, retuned, a little late and seated apart - different recordings, so no comb
filtering; measured in their notes).

Each patch reads its files only when a song renders it (lazy): importing needs no samples, a missing pack fails at use
with the pack id to fetch. Measured per-zone corrections from sampled_sections_levels.json even the notes
(agentsound/patches/_levelling.py; its own table: the same recordings play other key ranges in sampled/string_section,
so their corrections differ). Levels: every patch at gain_db 0 lands at about -18 LUFS playing its audition material.
Licenses: SSO is CC Sampling Plus 1.0 (credit "Sonatina Symphonic Orchestra", no advertising use); Virtual Playing
Orchestra is royalty-free (credit appreciated); VSCO 2 CE is CC0. Version: see VERSION.
"""

from pathlib import Path

from . import Patch, _levelling, fx, inst, layer, register
from . import sampled_orchestra as _so

VERSION = 1

_SSO = 'samples/sso/Sonatina Symphonic Orchestra/'
_SSO_STR = _SSO + 'Strings - Performance/'
_SSO_WW = _SSO + 'Woodwinds - Performance/'
_VPO_S = 'samples/vpo-scripts-performance/Strings/'
_VPO_W = 'samples/vpo-scripts-performance/Woodwinds/'
_VSCO = 'samples/vsco2-ce/'

LEVEL_TABLE = Path(__file__).with_name('sampled_sections_levels.json')
# Patch levels (the instrument 'level', dB): audition-calibrated to -18.0 LUFS (python -m agentsound audition <patch>)
LEVELS = {'violins_1': 11.9, 'violins_2': 13.6, 'violas': 11.6, 'celli': 11.1, 'double_basses': 12.1, 'flutes': 5.0,
          'oboes': 6.6, 'clarinets': 8.0, 'bassoons': 10.4, 'horns_muted': 2.8, 'trumpets_muted': 1.3}
CALIBRATION: dict = {}          # patch name -> levelling spec (see sampled_orchestra._reg)
PATCHES: list = []


def _fix(ins):
    _levelling.apply(ins, _levelling.load_table(LEVEL_TABLE))


def _multi(programs: dict, level: float, gains: dict | None = None, **kw):
    progs = {}
    for name, path in programs.items():
        d = {'path': path} if isinstance(path, str) else dict(path)
        if gains and gains.get(name):
            d['gain'] = gains[name]
        progs[name] = d
    ins = inst.sfz_multi(progs, lazy=True, level=level, **kw)
    ins.lazy['post'] = [f'{__name__}:_fix']
    return ins


def _reg(patch: Patch, stack: bool = False, short=(), tune: bool = True, keys=None) -> Patch:
    """register() + the patch's levelling spec (sampled_orchestra._reg)."""
    CALIBRATION[patch.name] = {'stack': stack, 'short': list(short), 'tune': tune, 'keys': keys}
    return _add(patch)


def _add(patch: Patch) -> Patch:
    PATCHES.append(patch.name)
    return register(patch)


_SECTION = ('A polyphonic section: unison lines, divisi (2-3 notes) and double stops; one track per section, the '
            'articulations switch per note.')
_STR_ARTS = ('Articulations are keyswitches inside the patch: clip.articulate(\'staccato\', span=...) or '
             'articulation.auto_articulate (short notes -> staccato); orch.perform / articulation.perform mark them '
             'from the note lengths and accents; unmarked notes play the sustain.')
_MODW = _so._MODW
_EVEN = ('Levelled: measured per-zone corrections even the notes out (no jumps between recordings) and retune '
         'recordings that were off their key.')
_CREDIT_STR = ('Sources: ' + _so._VPO_C + ' Marcato and col legno: ' + _so._SSO_C)

# --------------------------------------------------------------------------------------------- strings

# name, VPO prefix, SSO keyswitch program, pan, hp, range, sweet spot, level, articulation gains, eq, send, role text
_STRINGS = (
    ('violins_1', '1st-violin', '1st Violins KS.sfz', -0.5, 150, 'G3-C7', 'G3-E6', 3.4,
     {'staccato': -1.0, 'pizzicato': -1.8, 'tremolo': -0.2, 'marcato': -9.6, 'col legno': -8.9},
     {'peak2.freq': 1100, 'peak2.gain': -2.0, 'peak2.q': 1.0, 'high.freq': 9000, 'high.gain': 1.5}, -7,
     'First violins: the melody and the top of the harmony; soaring lines G4-E6, the E string up to C7 for climaxes, '
     'octaves with the seconds for a big tune.'),
    ('violins_2', '2nd-violin', '2nd Violins KS.sfz', -0.22, 150, 'G3-C7', 'G3-A5', 3.4,
     {'staccato': -2.2, 'pizzicato': -4.0, 'tremolo': -1.6, 'marcato': -10.7, 'col legno': -11.2},
     {'peak2.freq': 1100, 'peak2.gain': -2.0, 'peak2.q': 1.0, 'peak3.freq': 3200, 'peak3.gain': -1.5, 'peak3.q': 1.0},
     -7, 'Second violins: the harmony under the firsts (a third or sixth below), inner-voice ostinatos and '
         'repeated-note accompaniments, the melody an octave under the firsts.'),
    ('violas', 'viola', 'Violas KS.sfz', 0.2, 110, 'C3-C6', 'C3-C5', 3.4,
     {'staccato': 0.8, 'pizzicato': -2.9, 'tremolo': 0.7, 'marcato': -10.7, 'col legno': -6.9},
     {'peak1.freq': 350, 'peak1.gain': -1.5, 'peak1.q': 1.0}, -7,
     'Violas: the dark, veiled middle of the strings - the inner harmony C3-C5, the tenor line a fifth over the celli, '
     'warm unison melodies with the celli (Brahms), the alto voice of a chorale.'),
    ('celli', 'cello', 'Celli KS.sfz', 0.42, 40, 'C2-C#5', 'C2-A4', 3.4,
     {'staccato': 1.8, 'pizzicato': -2.3, 'tremolo': 0.6, 'marcato': -9.2, 'col legno': -7.1},
     {'peak1.freq': 120, 'peak1.gain': 2.0, 'peak1.q': 0.8}, -7,
     'Celli: the bass of the harmony with the basses an octave under, and the singing tenor melody D3-A4 (the '
     'film-score cello line); arpeggiated accompaniments in staccato.'),
    ('double_basses', 'bass', 'Basses KS.sfz', 0.6, 28, 'C1-C4', 'E1-D3', 3.4,
     {'staccato': 1.0, 'pizzicato': -4.2, 'tremolo': 0.9, 'marcato': -8.1, 'col legno': -4.1},
     {'peak1.freq': 90, 'peak1.gain': 1.5, 'peak1.q': 0.8}, -7,
     'Double basses (sounding pitch): the foundation an octave under the celli, long pedal notes, pizzicato on the '
     'downbeats, ominous low tremolo; double the celli\'s bass line, rarely their melody.'),
)


# the seating's width (and mono lows for the low sections), as the symphony_orchestra band places them
_WIDTH = {'violins_1': {'width': 0.9}, 'violins_2': {'width': 0.85}, 'violas': {'width': 0.8},
          'celli': {'width': 0.5, 'monobass': 120}, 'double_basses': {'width': 0.4, 'monobass': 150}}
_DESK = {'violins_1': 'violin', 'violins_2': 'violin', 'violas': 'viola', 'celli': 'cello', 'double_basses': 'bass'}

for (_name, _vpo, _sso, _pan, _hp, _rng, _sweet, _lvl, _gains, _bands, _send, _role) in _STRINGS:
    _arts = {'sustain': _VPO_S + _vpo + '-SEC-PERF.sfz',
             'staccato': _VPO_S + _vpo + '-SEC-PERF-staccato.sfz',
             'pizzicato': _VPO_S + _vpo + '-SEC-PERF-pizzicato.sfz',
             'tremolo': _VPO_S + _vpo + '-SEC-PERF-tremolo.sfz',
             'marcato': {'path': _SSO_STR + _sso, 'articulation': 'Marcato'},
             'col legno': {'path': _SSO_STR + _sso, 'articulation': 'Col Legno'}}
    _reg(Patch(
        f'sampled/{_name}',
        instrument=_multi(_arts, level=LEVELS[_name], gains=_gains, dynamics=0.6, polyphony=96),
        fx=[_so._eq(_hp, **_bands), fx.width(**_WIDTH[_name])],
        pan=_pan,
        sends={'hall': _send},
        notes=f'v{VERSION}. {_role} Symphonic section (12-16 players; the chamber-size VSCO desk: '
              f'sampled/{_DESK[_name]}_section). Seated at pan {_pan:+.2f}, width {_WIDTH[_name]["width"]}'
              + (f' (mono below {_WIDTH[_name]["monobass"]} Hz)' if 'monobass' in _WIDTH[_name] else '') +
              ' - an orchestra\'s seating, violins left, basses right. Articulations: '
              'sustain (looped, vibrato), staccato (spiccato bows), pizzicato, tremolo, marcato (accented, then held), '
              'col legno (the wood of the bow: ghostly ticks). Range ' + _rng + ', sweet spot ' + _sweet + '. ' +
              _SECTION + ' Bowing: re-bow notes longer than ~6 s (bandlib.orchestra.rebow). ' + _MODW + ' ' +
              _STR_ARTS + ' ' + _EVEN + ' ' + _CREDIT_STR + f' Sends: hall {_send}. Measured -18.0 LUFS '
              '(audition phrase' + (', octave 2' if _name == 'double_basses' else ', octave 3' if _name in (
                  'violas', 'celli') else '') + ').',
        audition={'notes': 'phrase', **({'octave': 2} if _name == 'double_basses' else {'octave': 3} if _name in (
            'violas', 'celli') else {})}),
        short=('col legno',))

# --------------------------------------------------------------------------------------------- woodwind sections

_WW = ('Woodwinds a2 / a3: the section in unison, or two parts on one track (2-note chords: the 1st and 2nd players). '
       'A polyphonic section; breathe between phrases (leave gaps).')
_WW_ARTS = ('Articulations are keyswitches inside the patch: clip.articulate(\'staccato\', span=...) or '
            'articulation.auto_articulate; unmarked notes play the sustain.')

_reg(Patch(
    'sampled/flutes',
    instrument=_multi({'sustain': {'path': _SSO_WW + 'Flutes KS.sfz', 'articulation': 'Sustain (looped)'},
                       'marcato': {'path': _SSO_WW + 'Flutes KS.sfz', 'articulation': 'Marcato (looped)'},
                       'staccato': {'path': _SSO_WW + 'Flutes KS.sfz', 'articulation': 'Staccato'},
                       'legato': {'path': _SSO_WW + 'Flutes KS.sfz', 'articulation': 'Legato'}},
                      level=LEVELS['flutes'], gains={'marcato': -3.9, 'staccato': -10.8}, dynamics=0.6, polyphony=48),
    fx=[_so._eq(220)],
    pan=-0.15,
    sends={'hall': -6},
    notes=f'v{VERSION}. Flute section a3, ' + _so._SSO_C + ' Articulations: sustain (looped), marcato (looped), '
          'staccato, legato (a softer, slurred attack). Range C4-C7, sweet spot G4-G6: doubling the violins an '
          'octave up, sustained high harmony, birdsong figures, the airy top of a woodwind chord (the solo flute: '
          'sampled/solo_flute). ' + _WW + ' ' + _MODW + ' ' + _WW_ARTS + ' ' + _EVEN + ' Seated at pan -0.15. '
          'Sends: hall -6. Measured -18.0 LUFS (audition phrase, octave 5).',
    audition={'notes': 'phrase', 'octave': 5}))

_reg(Patch(
    'sampled/oboes',
    instrument=_multi({'sustain': _VPO_W + 'oboe-SEC-PERF.sfz',
                       'staccato': {'path': _SSO_WW + 'Oboes KS.sfz', 'articulation': 'Staccato'}},
                      level=LEVELS['oboes'], gains={'staccato': -9.6}, dynamics=0.6, polyphony=48),
    fx=[_so._eq(200, **{'peak2.freq': 1300, 'peak2.gain': -2.0, 'peak2.q': 1.2})],
    pan=0.1,
    sends={'hall': -6},
    notes=f'v{VERSION}. Oboe section a3, ' + _so._SSO_C + ' The sustain is the Virtual Playing Orchestra re-loop of '
          'the SSO oboes (the originals click at their loop points), ' + _so._VPO_C + ' Articulations: sustain '
          '(looped), staccato. Range A#3-G6, sweet spot D4-D6: the reedy middle of a woodwind chord, pastoral '
          'doublings of the violins, nasal accents (the solo oboe: sampled/solo_oboe). ' + _WW + ' ' + _MODW + ' ' +
          _WW_ARTS + ' ' + _EVEN + ' Seated at pan +0.10. Sends: hall -6. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}))

_reg(Patch(
    'sampled/clarinets',
    instrument=_multi({'sustain': {'path': _SSO_WW + 'Clarinets KS.sfz', 'articulation': 'Sustain (looped)'},
                       'staccato': {'path': _SSO_WW + 'Clarinets KS.sfz', 'articulation': 'Staccato'},
                       'legato': {'path': _SSO_WW + 'Clarinets KS.sfz', 'articulation': 'Legato'}},
                      level=LEVELS['clarinets'], gains={'staccato': -10.8}, dynamics=0.6, polyphony=48),
    fx=[_so._eq(120, **{'peak1.freq': 400, 'peak1.gain': -1.5, 'peak1.q': 1.0})],
    pan=-0.08,
    sends={'hall': -6},
    notes=f'v{VERSION}. Clarinet section a3 (sounding pitch), ' + _so._SSO_C + ' Articulations: sustain (looped), '
          'staccato, legato (a slurred attack). Range D3-F6, sweet spot D3-C6: the warm, round middle of the '
          'woodwinds - sustained inner harmony, arpeggio figures, a soft unison melody with the violas (the solo '
          'clarinet: sampled/solo_clarinet). ' + _WW + ' ' + _MODW + ' ' + _WW_ARTS + ' ' + _EVEN +
          ' Seated at pan -0.08. Sends: hall -6. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}))

_reg(Patch(
    'sampled/bassoons',
    instrument=_multi({'sustain': {'path': _SSO_WW + 'Bassoons KS.sfz', 'articulation': 'Sustain (looped)'},
                       'staccato': {'path': _SSO_WW + 'Bassoons KS.sfz', 'articulation': 'Staccato'},
                       'legato': {'path': _SSO_WW + 'Bassoons KS.sfz', 'articulation': 'Legato'}},
                      level=LEVELS['bassoons'], gains={'staccato': -14.5}, dynamics=0.6, polyphony=48),
    fx=[_so._eq(50, **{'peak1.freq': 350, 'peak1.gain': -2.0, 'peak1.q': 1.0}), fx.width(width=0.5, monobass=120)],
    pan=0.16,
    sends={'hall': -6},
    notes=f'v{VERSION}. Bassoon section a2, ' + _so._SSO_C + ' Articulations: sustain (looped), staccato, legato. '
          'Range A#1-E5, sweet spot A#1-G4: the bass of the woodwind choir, doubling the celli, staccato bass '
          'lines (the witty bassoons), the tenor of a woodwind chorale (the solo bassoon: sampled/bassoon). ' + _WW +
          ' ' + _MODW + ' ' + _WW_ARTS + ' ' + _EVEN + ' Seated at pan +0.16, width 0.5 (mono below 120 Hz). '
          'Sends: hall -6. Measured -18.0 LUFS (audition phrase, octave 2).',
    audition={'notes': 'phrase', 'octave': 2}))


# ------------------------------------------------------------------------------- muted brass (a3 from solos)
# Three players from one solo set: each plays the recording of a neighbouring note, retuned to the written one (the
# layer's transpose +4 / -3 st and the sampler's tune -400 / +300 ct) - different recordings, so the stack does not
# comb-filter like copies of one sample would - a few cents apart, 0 / 23 / 41 ms late and seated apart.

A3_PLAYERS = (('p1', 0, 0, 0, -0.2), ('p2', 4, 6, 23, 0.0), ('p3', -3, -5, 41, 0.2))
"""(layer id, recording offset in semitones, detune in cents, delay in ms, pan) of the three players."""
_VSCO_DYN = dict(layers='dynamics', xfspread=2, dynrange=12, dyntone=0.4, dynamics=0.6, polyphony=24)


def _orch_as(ins, art: str):
    """The solo patch's measured corrections (sampled_orchestra_levels.json, articulation `art`) on these zones."""
    table = _levelling.load_table(_so.LEVEL_TABLE)
    for z in ins.params.get('samples') or []:
        if isinstance(z, dict) and z.get('file'):
            k = f"{_levelling._rel(z['file'])}|{art}"
            if table.get(k):
                z['gain'] = round(float(z.get('gain', 0.0)) + table[k], 3)
            if table.get(k + '|tune'):
                z['tune'] = round(float(z.get('tune', 0.0)) + table[k + '|tune'], 1)
    return ins


def _fix_horn_mute(ins):
    _orch_as(ins, 'muted')


def _fix_trumpet_mute(ins):
    _orch_as(ins, 'straight mute')


def a3(path: str, fix: str | None = None, level: float = 0.0, players=A3_PLAYERS, **params):
    """A KISS a3 section from one solo SFZ: a stack of three players, each on the recording of a neighbouring note
    (players: (id, semitones, cents, delay ms, pan)); fix = a 'module:function' post hook for the zones."""
    out = []
    for pid, st, ct, ms, pan in players:
        ins = inst.sfz(path, lazy=True, tune=-100 * st + ct, **{**_VSCO_DYN, **params})
        if fix:
            ins.lazy['post'] = [fix]
        out.append(layer(ins, pid, transpose=st, delay=ms, pan=pan))
    return inst.stack(*out, level=level)


_A3_NOTE = ('Three players from the VSCO 2 CE solo recordings (License CC0, no credit required): each plays the '
            'recording of a neighbouring note (4 semitones up / 3 down, retuned; three different recordings at about '
            '3 of 4 notes), 0 / 23 / 41 ms apart and a few cents off, seated left - centre - right. No comb filtering '
            '(measured on held notes: per harmonic the players sum within 1.6 dB of their energy sum) and the '
            'harmonics beat 2.4-3.5 dB like the recorded SSO sections (3.1-3.2 dB; the solos 2.1-3.0; three copies of '
            'one recording: 3.1-4.2, a chorus).')

_add(Patch(
    'sampled/horns_muted',
    instrument=a3(_VSCO + 'FHornMute.sfz', f'{__name__}:_fix_horn_mute', LEVELS['horns_muted']),
    fx=[_so._eq(60)],
    pan=-0.3,
    sends={'hall': -6},
    notes=f'v{VERSION}. Muted French horns a3 (hand-stopped / mute: distant, veiled, slightly nasal; forced it '
          'turns brassy and menacing). ' + _A3_NOTE + ' Range C#3-C#5 (sounding; the recordings A#2-F5 less the '
          'neighbours), sweet spot E3-C5. Soft chords under strings, a distant call, the eerie stopped-horn swell in '
          'film and fairy-tale cues; the solo muted horn: sampled/solo_horn with clip.articulate(\'muted\'). '
          + _so._STACK + ' Seated at pan -0.30. Sends: hall -6. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

_add(Patch(
    'sampled/trumpets_muted',
    instrument=a3(_VSCO + 'TrumpetStraightMuteSus.sfz', f'{__name__}:_fix_trumpet_mute', LEVELS['trumpets_muted']),
    fx=[_so._eq(200)],
    pan=0.14,
    sends={'hall': -7},
    notes=f'v{VERSION}. Trumpets a3 with straight mutes (thin, nasal, buzzing - the muted fanfare, a mysterious '
          'or comic colour, cool soft chords). ' + _A3_NOTE + ' Range C#4-G#5 (the recordings A#3-C6 less the '
          'neighbours), sweet spot E4-A5. Soft muted chords and fanfares, a nasal counter-line (short notes work: '
          'the recordings are sustains, so no crisp staccato); the solo muted trumpet: sampled/trumpet_harmon '
          '(Harmon) or sampled/solo_trumpet clip.articulate(\'straight mute\'). ' + _so._STACK + ' Seated at pan '
          '+0.14. Sends: hall -7. Measured -18.0 LUFS (audition chords, octave 4).',
    audition={'notes': 'chord', 'octave': 4}))
