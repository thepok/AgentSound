"""Hero leads: the instrument that sits LOUD on top of a record with everything carved around it - the late-70s /
80s "hero sax" (Raphael Ravenscroft on "Baker Street", Sanborn-era pop sax). recipes/HUMAN_FEEDBACK.md
(2026-09-30, lamplight-avenue): "bei Baker Street klingt das Sax irgendwie epischer und praesenter".

  leads:   hero/sax                      (THE hero sax, v2 - the late-70s record sax: dynamic mic, a breath trace,
                                          4:1 compression, tube + tape grit, near-mono, a 10 Hz random autopan, a
                                          bright 3.6 s plate; the user's pick 2026-10-15: "das wird das standard sax")
           hero/sax_clean = layered/hero_sax  (the v1 hero: cleaner, double-tracked; opt-out: family='sax_clean')
  returns: bus/hero_plate, bus/hero_plate_70s  (the big bright pre-delayed plates behind them)

THE way to use it: agentsound.heroes.hero(s.track('sax', 'layered/hero_sax'), family='sax', bed=[...]) - the sound
plus its mix rules (hero plate, echo throws, bed duck + carve, rides). This module defines the 'sax' preset of that
wrapper (heroes.PRESETS['sax']: the generic source spec - a main take, two takes of another sample set, a muted
octave layer - and the shared hero chain tone -> comp -> drive -> presence -> air with the values of HERO_SAX) and
registers the patch through heroes.build(); the patch is unchanged (tests pin it).

What a hero sound is, as data (HERO_SAX below, read by the 'sax' preset):
  generic (any hero lead: sax, guitar, synth, trumpet ...)
    - 'comp':   a fast compressor with 6-10 dB of reduction on the hook (the level nearly constant, long notes bloom),
                slow enough (10-15 ms attack) that the note attacks keep the phrase dynamics
    - 'drive':  a little tube / tape grit after it (harmonics = density and edge at the same loudness)
    - 'eq':     mud and honk out below the compressor, presence (2-3 kHz) and air (8 kHz+) in after it
    - 'double': a second and third take, detuned +-8-10 ct, 16-27 ms late, panned L/R ~10 dB under the lead: width
                without phasing (different takes are uncorrelated) or a flam (inside the Haas window)
    - 'space':  a big bright pre-delayed plate (the attack stays dry and in front, the bloom behind it), some hall,
                an echo that is thrown at the phrase ends (articulation.throws) rather than always on
    - 'mix':    the bed >= 4-6 dB under the lead in its sections, the bed's presence band carved while the lead
                plays (song.carve: a keyed dynamic EQ), the lead ridden 1-2 dB up in the hook sections
  sax-specific
    - the sources: Weresax alto through its overdriven dynamic mic (cc 120 = 127: the close 70s SM57 / MD421
      sound, grit and a bright top on F5-Ab5 where the condenser gets duller) + MTG alto takes as the doubles
      (a different player and horn: a real double, not a copy) + an optional MTG tenor an octave down (weight)
    - the frequencies: honk at ~650 Hz, bite at ~2.6 kHz, air above 8 kHz; playing: velocities 90-122 on the hook,
      vibrato on the held peaks (articulation.perform / .vibrato reach every sampler layer of the stack)

Level calibration: -18 LUFS integrated (track node, dry) on the audition phrase, like the rest of the library.
Version: see VERSION (bump it when the sound changes audibly).
"""

from .. import heroes
from . import Patch, fx, inst, register
from .sampled import WERESAX_CC, WERESAX_ZONE

VERSION = 2          # v2: hero/sax = the 70s record sax (HERO_SAX); v1 lives on as sax_clean / layered/hero_sax

_WERESAX = 'samples/karoryfer-weresax/Programs/Sax.sfz'
_MTG = 'samples/mtg-solo-sax/MTG Solo Saxophones/'

# The v1 hero sax (now the opt-out 'sax_clean' preset and the pinned layered/hero_sax): everything that made the sax
# a hero, in one place (values that are sax-specific are marked in the module notes above).
HERO_SAX_CLEAN = {
    'source': {'sfz': _WERESAX, 'level': -0.7, 'cc': {120: 127}, 'legatotime': 50, 'hp': 90, 'velcurve': 2.5},
    'double': [   # extra takes: (id, sfz, sampler level, layer level dB, fine ct, delay ms, pan)
        ('dbl_l', _MTG + 'MTG Alto Sax.sfz', 9.3, -10.0, 9.0, 17.0, -0.85),
        ('dbl_r', _MTG + 'MTG Alto Sax.sfz', 9.3, -10.5, -8.0, 26.0, 0.85),
    ],
    'octave': {'sfz': _MTG + 'MTG Tenor Sax.sfz', 'level': 11.8, 'layer_level': -13.5, 'transpose': -12,
               'mute': True},
    'eq': {'hp.freq': 140, 'peak1.freq': 330, 'peak1.gain': 1.5, 'peak1.q': 1.0,
           'peak2.freq': 650, 'peak2.gain': -2.5, 'peak2.q': 1.4,
           'peak3.freq': 1300, 'peak3.gain': -4.0, 'peak3.q': 0.9},
    'comp': {'threshold': -31, 'ratio': 3.0, 'knee': 6, 'attack': 25, 'release': 130, 'automakeup': 'on'},
    'drive': {'mode': 'tube', 'drive': 9, 'mix': 0.45, 'tone': 1.0},
    'presence': {'peak3.freq': 3000, 'peak3.gain': 2.0, 'peak3.q': 0.7, 'high.freq': 8000, 'high.gain': 3.0},
    'air': {'freq': 3500, 'drive': 30, 'amount': 0.25, 'character': 0.4},
    'space': {'plate': -14.0, 'hall': -16.0, 'echo': -24.0, 'throw': -5.0, 'plate_bus': 'bus/hero_plate'},
    'mix': {'bed_under_db': 5.0, 'carve_db': 4.0, 'carve_freq': 2500, 'carve_q': 0.7, 'ride_db': 2.0},
    # hero(genre='jazz' / 'ballad'): a soft tenor-style hero - one take, no octave, no tube grit, no exciter, 2:1 at
    # -26 dB (the 3:1 / -31 chain flattened the MTG tenor to 3.6 dB per phrase: 5.4 dB here), the presence gentle
    # (songs/nowhere-to-be; user: "was ist das fuer ein merkwuerdiges Lead-Instrument?" about the doubled sax)
    'soft': {'drive': False, 'exciter': False,
             'comp': {'threshold': -26, 'ratio': 2.0, 'attack': 30, 'release': 160},
             'presence': {'peak3.freq': 3000, 'peak3.gain': 0.0, 'peak3.q': 0.7, 'high.freq': 9000, 'high.gain': 1.0}},
}
GAIN_DB_CLEAN = -2.6   # audition calibration of layered/hero_sax (-18.0 LUFS)

# THE hero sax (v2, hero/sax, hero(track, family='sax') in every genre): the late-70s record sax of the user's A/B
# (2026-10-15, variant d: "started the imaginary sax in my head"; "nein, das wird das standard sax!"). Over the clean
# hero: the Weresax with its breath trace (WERESAX_CC / WERESAX_ZONE: the dynamic mic, cc 122 = 16 through a 2-pole
# 3 kHz low-pass), velocity curve 1.7 instead of 2.5 (the forte layer sounds from ~velocity 84: hooks played at 84-124
# land where the A/B's 95-127 did), near-mono (width 0.3), one take (no doubles / octave by default), a firmer 4:1
# compressor, a second tube saturator (drive 7, full) and 15 ips tape (drive 6) after the presence / exciter, a 10 Hz
# smooth-random autopan tremolo (the reed's fast amplitude flutter: HUMAN_FEEDBACK 2026-10-15) and a bright 3.6 s plate
# (bus/hero_plate_70s: bus/plate_80s with a longer, brighter tail). The doubles / octave layer of the clean hero stay
# available: hero(..., double='takes', octave='muted').
HERO_SAX = {
    'source': {'sfz': _WERESAX, 'level': -0.7, 'cc': dict(WERESAX_CC), 'zone': dict(WERESAX_ZONE), 'legatotime': 50,
               'hp': 90, 'velcurve': 1.7, 'width': 0.3},
    'double': HERO_SAX_CLEAN['double'],
    'octave': dict(HERO_SAX_CLEAN['octave']),
    'eq': dict(HERO_SAX_CLEAN['eq']),
    'comp': {'threshold': -33, 'ratio': 4.0, 'knee': 6, 'attack': 20, 'release': 120, 'automakeup': 'on'},
    'drive': dict(HERO_SAX_CLEAN['drive']),
    'presence': dict(HERO_SAX_CLEAN['presence']),
    'air': dict(HERO_SAX_CLEAN['air']),
    'grit': {'mode': 'tube', 'drive': 7, 'mix': 1.0},              # the second saturator, after the exciter
    'tape': {'speed': '15', 'drive': 6},
    'flutter': {'rate': 10, 'depth': 0.25, 'stereo': 180, 'ratemod': 3, 'depthmod': 0.1, 'modrate': 0.3,
                'modshape': 'random'},                              # the autopan tremolo
    'plate': {'decay': 3.6, 'damping': 12000},                      # bus/hero_plate_70s = bus/plate_80s with these
    'space': dict(HERO_SAX_CLEAN['space'], plate_bus='bus/hero_plate_70s'),
    'mix': dict(HERO_SAX_CLEAN['mix']),
}
GAIN_DB = -2.9   # audition calibration of hero/sax (-18.0 LUFS)
USER_GAIN_DB = -3.1   # around another -18 LUFS sound (heroes.Preset.user_gain_db)
# the 70s hero's chain order: the second saturator ('amp' stage), the tape and the autopan ('width' stage) after the
# presence / exciter, as in the A/B (the song's inserts after the hero chain)
ORDER_70S = ('tone', 'catch', 'comp', 'deess', 'drive', 'presence', 'exciter', 'amp', 'tape', 'chorus', 'double',
             'width', 'dimension', 'air', 'echo')


def hero_sax_stages(h: dict = HERO_SAX) -> dict:
    """The hero chain as heroes stages: cut (tone) -> compress -> drive -> presence/air -> excite (-> the 70s hero's
    grit saturator, tape and autopan)."""
    st = {'tone': dict(h['eq']), 'comp': dict(h['comp']), 'drive': dict(h['drive']),
          'presence': dict(h['presence']), 'exciter': dict(h['air'])}
    if h.get('grit'):
        st['amp'] = [fx.saturator(**h['grit'])]
    if h.get('tape'):
        st['tape'] = dict(h['tape'])
    if h.get('flutter'):
        st['width'] = [fx.tremolo(**h['flutter'])]
    return st


def hero_sax_chain(h: dict = HERO_SAX) -> list:
    """The hero insert chain after the takes are summed (hero_sax_stages in the preset's order)."""
    return heroes.chain(hero_sax_stages(h), ORDER_70S if h.get('grit') else heroes.ORDER, named=False)


def hero_sax_source(h: dict = HERO_SAX, octave_mode: str | None = None) -> dict:
    """The sax preset's source as heroes layer specs: {'main': ..., 'takes': [...], 'octave': ...}."""
    src = h['source']
    kw = {'zone': dict(src['zone'])} if src.get('zone') else {}
    if 'width' in src:
        kw['width'] = src['width']
    main = {'id': 'sax', 'sound': inst.sfz(src['sfz'], lazy=True, level=src['level'], mono='legato',
                                           legatotime=src['legatotime'], cc=dict(src['cc']), **kw),
            'velcurve': src['velcurve'], 'hp': src['hp']}
    takes = [{'id': lid, 'sound': inst.sfz(path, lazy=True, level=lvl, mono='legato', legatotime=50), 'level': level,
              'fine': fine, 'delay': delay, 'pan': pan, 'hp': 160}
             for lid, path, lvl, level, fine, delay, pan in h['double']]
    o = h.get('octave')
    octave = {'id': 'octave', 'sound': inst.sfz(o['sfz'], lazy=True, level=o['level'], mono='legato', legatotime=50),
              'level': o['layer_level'], 'transpose': o['transpose'], 'hp': 90,
              'mode': octave_mode or ('muted' if o['mute'] else 'on')} if o else None
    return {'main': main, 'takes': takes, 'octave': octave}


def hero_sax_layers(h: dict = HERO_SAX_CLEAN) -> list:
    """The layers of layered/hero_sax (main take, the two doubles, the octave layer)."""
    p = heroes.build('sax_clean')
    return list(p.instrument.layers)


_SPACE = HERO_SAX_CLEAN["space"]
_NOTES_CLEAN = ('v1 (hero/sax until 2026-10-15; the opt-out sax_clean). The late-70s / 80s hero alto (Raphael Ravenscroft on "Baker Street", Sanborn-era pop sax): '
          'close-miked, bright and forward, heavily compressed, a little grit, double-tracked, LOUD on top. Takes: '
          'Weresax alto (Karoryfer, CC0) through its overdriven dynamic mic (cc 120 = 127; brighter on F5-Ab5 than the '
          'condenser, whose top notes lose ~5 dB of presence), velocity curve 2.5 (the file moves only ~5 dB from '
          'velocity 40 to 127: the curve spreads the played velocities so accents survive the compressor) + two MTG '
          'alto takes (MTG / UPF, CC-BY 4.0) as the double-track: +9 / -8 ct, 17 / 26 ms late, panned -0.85 / +0.85, '
          '-10 / -10.5 dB (each ~10 LU under the lead; different player and horn, so uncorrelated: the stack energy = '
          'the sum of the takes within 0.1 dB, correlation lead vs doubles -0.03 - no phasing, no flam) + an MTG tenor '
          'an octave down at -13.5 dB, MUTED by default (weight for the big sections: automate '
          '"instrument.layers.octave.mute" to 0). Chain: high-pass 140, +1.5 dB 330 Hz (body), -2.5 dB 650 Hz (honk), -4 '
          'dB 1.3 kHz (the boxy "mid" the pop profile flags) -> compressor 3:1, -31 dB, 25 ms attack (the note '
          'attacks and phrase dynamics pass), 130 ms release: 6.5 dB median / 8.7 dB p90 gain reduction on a hook '
          'at velocities 86-120 (the 10-90 % spread of 50 ms levels 7 -> 4 dB: the notes bloom) -> tube drive 9 dB at 45 % -> '
          '+2 dB at 3 kHz (bite), +3 dB shelf at 8 kHz (air) -> exciter from 3.5 kHz. Measured on the lamplight-avenue '
          'riff vs the plain Weresax chain it replaced: 1.5-5 kHz share -5.8 -> -4.5 dB, 400-800 Hz -1.9 -> -3.0 dB '
          '(the honk down, the bite up), 50 ms level spread 7.0 -> 4.2 dB; width from real takes (side/mid -12.7 dB, '
          'correlation 0.90) instead of a pitch-shifted copy. Sends: plate -14 (best: its own bus/hero_plate), hall -16, '
          'echo -24 with throws to -5 on the phrase ends (articulation.throws). How to play: hooks at velocities '
          '84-124 (still phrase arcs: touch()), articulation.perform (legato, scoops through instrument.pitchbend, '
          'the vibrato reaches every take), wide vibrato (24-28 ct) on the held peaks. Mix it as a hero: 1-3 dB over '
          'the whole band in the hook sections, the bed 6-8 dB under it (report: bed vs lead), song.carve(bed ..., '
          'key=sax, depth=4) for the 1-4 kHz. The values live in HERO_SAX_CLEAN (patches/hero.py). Range: C#3-Ab5 '
          '(Weresax). Measured -18.0 LUFS (audition phrase). Tweak: .layer("dbl_l", mute=True).layer("dbl_r", '
          'mute=True) (a single take, mono), .layer("octave", mute=False) (always the octave), .but_fx("compressor", '
          'threshold=-27) (less squeeze), .but_fx("saturator", drive=14) (more grit).')

_NOTES = (f'v{VERSION}. THE hero sax: the late-70s record alto (the user\'s pick in a blind A/B, 2026-10-15: "das wird '
          'das standard sax"). Source: Weresax alto (Karoryfer, CC0) through its overdriven dynamic mic (cc 120 = 127) '
          'with the file\'s wind-noise layer as a trace (cc 122 = 16 through a 2-pole 3 kHz low-pass: ~12 dB under the '
          'dry sax in 3-16 kHz on held notes, felt more than heard), velocity curve 1.7 (hooks at 84-124 sound the '
          'forte layer), near-mono (width 0.3), one take. Chain: high-pass 140, +1.5 dB 330 Hz, -2.5 dB 650 Hz, -4 dB '
          '1.3 kHz -> compressor 4:1, -33 dB, 20 ms attack, 120 ms release -> tube drive 9 dB at 45 % -> +2 dB 3 kHz, '
          '+3 dB shelf 8 kHz -> exciter from 3.5 kHz -> a second tube saturator (drive 7, full) -> 15 ips tape (drive '
          '6) -> a 10 Hz autopan tremolo (depth 0.25, stereo 180, its rate +-3 Hz and depth +-0.1 moved by a smooth '
          'random LFO at 0.3 Hz: the reed\'s fast flutter) -> the air stage. Sends: plate -14 (its own '
          'bus/hero_plate_70s: the bright 80s EMT with a 3.6 s tail), hall -16, echo -24 with throws. How to play: '
          'hornist.arrange(..., style=\'hero70s\') (pop phrasing, a growl on a held peak at most every 8 bars, no '
          'shakes, the body sway) at velocities 84-124. Opt-outs: hero(..., family=\'sax_clean\') (the v1 hero: '
          'cleaner, double-tracked; = layered/hero_sax), double=\'takes\' / octave=\'muted\' (the clean hero\'s MTG '
          'doubles and octave tenor), drive=False, tape=False, width=False (no autopan). The values live in HERO_SAX '
          '(patches/hero.py). Range: C#3-Ab5 (Weresax). Measured -18.0 LUFS (audition phrase).')

_SRC = hero_sax_source(HERO_SAX, octave_mode='off')
heroes.define(
    'sax', family='sax', main=_SRC['main'], takes=_SRC['takes'], octave=_SRC['octave'], double=None,
    sound='sampled/alto_sax',      # a track on the library alto becomes this hero's own source (the same Weresax)
    chain=hero_sax_stages(HERO_SAX), order=ORDER_70S, named=False, gain_db=GAIN_DB,
    sends={'plate': _SPACE['plate'], 'hall': _SPACE['hall'], 'echo': _SPACE['echo']},
    space={'plate_bus': HERO_SAX['space']['plate_bus'], 'plate': _SPACE['plate'], 'echo': _SPACE['echo'],
           'throw': _SPACE['throw'], 'min_rest': 0.5, 'min_dur': 1.0},
    mix={'duck': 2.5, 'duck_attack': 15.0, 'duck_release': 260.0, 'carve_db': HERO_SAX['mix']['carve_db'],
         'carve_freq': HERO_SAX['mix']['carve_freq'], 'carve_q': HERO_SAX['mix']['carve_q'],
         'ride_db': HERO_SAX['mix']['ride_db'], 'dip_db': -2.0, 'dip_freq': 2500.0},
    play={'vel': (84, 124), 'vib': {'depth': 24, 'rate': 5.4, 'delay': 0.3}, 'style': 'hero70s'},
    user_gain_db=USER_GAIN_DB,
    notes=_NOTES, audition={'notes': 'phrase'},
    words=('sax', 'saxophone', 'alto', 'tenor', 'soprano', 'bari', 'weresax'),
    measured={'lufs': -18.0})
heroes.register('sax')

_SRC_CLEAN = hero_sax_source(HERO_SAX_CLEAN)
heroes.define(
    'sax_clean', family='sax', main=_SRC_CLEAN['main'], takes=_SRC_CLEAN['takes'], octave=_SRC_CLEAN['octave'],
    double='takes', chain=hero_sax_stages(HERO_SAX_CLEAN), named=False, gain_db=GAIN_DB_CLEAN,
    sends={'plate': _SPACE['plate'], 'hall': _SPACE['hall'], 'echo': _SPACE['echo']},
    space={'plate_bus': _SPACE['plate_bus'], 'plate': _SPACE['plate'], 'echo': _SPACE['echo'],
           'throw': _SPACE['throw'], 'min_rest': 0.5, 'min_dur': 1.0},
    mix={'duck': 2.5, 'duck_attack': 15.0, 'duck_release': 260.0, 'carve_db': HERO_SAX_CLEAN['mix']['carve_db'],
         'carve_freq': HERO_SAX_CLEAN['mix']['carve_freq'], 'carve_q': HERO_SAX_CLEAN['mix']['carve_q'],
         'ride_db': HERO_SAX_CLEAN['mix']['ride_db'], 'dip_db': -2.0, 'dip_freq': 2500.0},
    play={'vel': (84, 124), 'vib': {'depth': 24, 'rate': 5.4, 'delay': 0.3}},
    user_gain_db=-2.8,
    genres={'jazz': {**heroes.PLAIN, **HERO_SAX_CLEAN['soft']}, 'ballad': {**heroes.PLAIN, **HERO_SAX_CLEAN['soft']},
            'classical': heroes.PLAIN},
    notes=_NOTES_CLEAN, audition={'notes': 'phrase'}, patch='layered/hero_sax', aliases=('clean_sax',),
    measured={'lufs': -18.0, 'gr_median_db': 6.5, 'gr_p90_db': 8.7, 'spread_50ms_db': (7.0, 4.2),
              'lamplight_hooks_sax_vs_band_db': (0.8, 1.7), 'lamplight_bed_vs_lead_db': (-5.3, -8.3)})
heroes.register('sax_clean')


register(Patch(
    'bus/hero_plate',
    fx=[fx.eq({'hp.freq': 450, 'lp.freq': 9500}),
        fx.reverb(type='plate', mix=1.0, decay=2.8, predelay=45, lowcut=380, highcut=13000, damping=9000,
                  moddepth=0.5, width=1.0),
        fx.eq({'peak3.freq': 3200, 'peak3.gain': 2.0, 'peak3.q': 0.7, 'output': 9.0})],
    notes='v1. The hero-lead plate (a sax or vocal-like lead that should bloom behind itself): bright EMT-style '
          'plate, the send filtered 450 Hz-9.5 kHz (body and bite only, no mud), RT60 2.8 s, a long 45 ms pre-delay '
          '(the attack stays dry and in front, the bloom follows), natural width (mono-safe), +2 dB at 3.2 kHz, calibrated like '
          'bus/plate_80s (+9 dB output). Use: hp = s.bus("hero_plate", "bus/hero_plate"); the hero track sends '
          '{hp: -14} (and patches.get("layered/hero_sax").with_mix(sends={"plate": None}), so that the plate of the '
          'band stays for the snare). On lamplight-avenue the return sits ~5.5 LU under the dry sax and all reverbs '
          'together ~8.5 LU under the mix (pop: lush 7-16). Tweak: but_fx("reverb", decay=2.2-3.5, predelay=30-60).'))

register(Patch(
    'bus/hero_plate_70s',
    fx=[fx.eq({'hp.freq': 500, 'lp.freq': 10000}),
        fx.reverb(type='plate', mix=1.0, decay=HERO_SAX['plate']['decay'], predelay=22, lowcut=400, highcut=14000,
                  damping=HERO_SAX['plate']['damping'], moddepth=0.5, width=1.0),
        fx.eq({'peak3.freq': 4500, 'peak3.gain': 2.0, 'peak3.q': 0.7, 'output': 9.0})],
    notes='v1. The 70s hero sax plate (hero/sax): bus/plate_80s (the bright EMT: send filtered 500 Hz-10 kHz, 22 ms '
          'pre-delay, +2 dB at 4.5 kHz, +9 dB output) with a longer, brighter tail - RT60 3.6 s, damping 12 kHz (the '
          'user\'s A/B pick, 2026-10-15). hero(track, family=\'sax\') sends to it (plate -14). Tweak: '
          'but_fx("reverb", decay=2.4-4).'))
