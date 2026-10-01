"""Hero guitar: the featured, singing lead-guitar solo that stands in front of the mix like on a hit record (Gilmour
"Comfortably Numb", Slash "November Rain", Gary Moore, Knopfler, the Baker Street solo) - the source, its production
chain, and how to mix and play it.

  layered/hero_guitar         the singing overdriven lead: Strat DI -> sustainer -> Plexi lead channel -> Greenback
                              4x12, velocity zones (harder picking = more gain, brighter, louder), tape, H3000-style
                              double, dotted-8th / quarter stereo echo, hall + plate sends
  sampled/hero_guitar_clean   the clean-ish Strat lead (Knopfler "Sultans of Swing", Gilmour clean): DI -> gentle
                              compressor -> edge-of-breakup combo, a polyphonic plain sampler (all tools work direct)
  layered/hero_guitar_heavy   the heavy lead (Slash, Gary Moore, 80s arena): DI zones through a hot lead amp + a real
                              amped singing lead (SampleRadar Guitar B multisample) doubled under it for sustain and width
(the driven heroes are stacks, so they live under layered/ with the other stacks; the clean one is a sampler)

The three are the 'guitar', 'guitar_clean' and 'guitar_heavy' presets of the hero wrapper (agentsound.heroes: their
chains as its stages, the patches built by heroes.build() and unchanged - tests pin them): hero(s.track('lead',
'layered/hero_guitar'), bed=[...], competitors=[...]) adds the mix rules (duck, carve, dips, rides, throws on its own
echo); play them through lead() / play() below (or heroes.play).

WHY A STACK. A driven amp is a compressor: through the old sampled/lead_guitar chain (drive 27 + compressor) a velocity
sweep 55 -> 115 moved the note onsets ~1.5 dB (the round robins scatter +-2 dB) - the report's flat_dynamics ear
flags such a lead as robotic (HUMAN_FEEDBACK "sind alle Lead-Noten gleich laut?"). Anything after the saturator cannot
know the velocity, so the two driven heroes are stacks of velocity ZONES: the same DI guitar through the same amp, one
layer per picking strength, each with its own drive, bright cap and output level (velocity -> drive / level / filter),
plus a per-note filter that opens with velocity (the zones' lpf 'filVeltrack', before the amp). Zones have hard edges:
a layer's notes stay on its main instance, so legato and glides work inside a zone (a velocity CROSSFADE would put
every fade step on its own instance and break the legato line).

PLAYING THEM. A stack takes plain notes, pitch bends ('instrument.pitchbend') and the stack params, but not the
sampler's per-note marks: glide / articulation marks and 'instrument.vibrato' need a sampler. Play the driven heroes
through this module - it writes those onto every sampler layer and keeps slurs inside one zone:

    from agentsound import guitarist as gtr
    from agentsound.patches import hero_guitar as hero
    lead = s.track('lead', 'layered/hero_guitar')
    mem = gtr.Memory()
    hero.lead(lead, melody, prog, bpm=s.tempo, key=s.key, style='rock', section=solo, memory=mem, climax=True)
    hero.play(lead, gtr.bend('A5', 4, s.tempo, rise_ms=180), solo.bar(7))       # a single move (a Lick)
    hero.play(lead, art.legato(line).glide(120, where=art.leaps(3)), verse)       # a written line (marks kept)

hero.play(track, part, at) takes a Clip, a guitarist Arrangement or a Lick: notes (glide marks -> 'instrument.layers.
<id>.glide' steps on every sampler layer, articulation marks dropped), vibrato and pitchbend automation, 'lock': a tie
(a slur, a slide) that would cross a zone edge keeps the first note's zone (the velocity is clamped to the zone edge
when that is within 8 of the written velocity or the note glides, else the tie is broken - a new pick), 'throws':
the echo up at phrase ends. On a plain sampler (sampled/hero_guitar_clean) it is the same as arrangement.play plus the
glides and vibrato the track does itself.

Level calibration as the rest of the library: every patch at gain_db 0 lands at about -18 LUFS integrated (track node,
dry of sends, with its insert fx) playing its audition material; the values are in each patch's notes. Samples: the
FreePats FSBS direct (DI) Stratocaster (CC0) and the SampleRadar heavy metal guitar lead multisample (heavy only;
royalty-free for music, no redistribution of the samples); cabinet IRs: Jester Emerald (Greenback 4x12, CC0) and
Overdriven (Celestion G12H30 1x12, clean only; free for music). Version: see VERSION.
"""

from __future__ import annotations

from .. import heroes
from . import fx, inst, layer
from . import sampled_guitars as _sg    # the DI sample sets and the amp voicings (registers sampled/* + cab/*)

VERSION = 2   # v2: the plain hero on the engine's tube amp (Plexi lead voicing) + a rolled-back DI filter

# gain_db of each patch: its audition material at -18.0 LUFS (python -m agentsound audition <patch>)
LEVELS = {'hero_guitar': -4.5, 'hero_guitar_clean': -9.4, 'hero_guitar_heavy': -3.8}

DI = _sg.FSBS['direct']
METAL_LEAD = 'samples/sampleradar-heavy-metal-guitar/Guitar B/Lead Multi'

# Velocity zones of the plain hero (v2): (vello, velhi, the amp's gain knob, bright cap dB, output level dB). One
# picking strength per zone: harder = more gain, a brighter amp input, louder after the amp, ~3.2 dB apart (v1 was a
# saturator per zone: drive 19-27 dB - a fuzz box; v2 the tube amp's Plexi lead channel: PLEXI_LEAD).
ZONES = ((1, 64, 4.4, 2.0, -12.8), (65, 79, 5.0, 2.5, -9.6), (80, 94, 5.6, 3.0, -6.4), (95, 109, 6.2, 3.5, -3.2),
         (110, 127, 6.8, 4.0, 0.0))
# The plain hero's amp: a cranked two-stage Plexi with a Tube Screamer push (the Gilmour / Slash "November Rain"
# lead: less preamp gain than the heavy hero, the power amp joining in), on top of LEAD_AMP.
PLEXI_LEAD = {'stages': 2, 'boost': 8.0, 'tight': 100.0, 'mid': 7.5, 'treble': 6.5, 'presence': 7.0,
              'resonance': 5.5, 'master': 6.0, 'sag': 0.35}
# The plain hero's DI: the bridge pickup rolled back (a key-tracked low-pass at ~1.9x the note): the fundamental
# leads like the heavy hero's neck, with a little more bite.
PLEXI_DI = {'cutoff': 600.0, 'veltrack': 1200.0, 'keytrack': 100.0}
# The heavy hero (v2): (vello, velhi, the amp's gain knob 0-10, its bright cap dB, output level dB) per zone.
HEAVY_ZONES = ((1, 69, 5.6, 1.0, -9.6), (70, 86, 6.3, 2.0, -6.4), (87, 104, 7.0, 3.0, -3.2), (105, 127, 7.6, 4.0, 0.0))
# The heavy hero's lead amp (the engine's 'amp': a 3-stage hot-rodded preamp, a Marshall tone stack, a push-pull power
# amp with sag) - a Gary Moore / Slash lead channel: a light Tube Screamer push, mids forward, presence up, the master
# low enough that the preamp sings and the power amp only thickens. Measured on kestrel-bay (songs/kestrel-bay/TONE.md).
LEAD_AMP = {'stages': 3, 'boost': 6.0, 'tight': 110.0, 'bass': 5.0, 'mid': 7.0, 'treble': 7.0, 'presence': 8.0,
            'resonance': 6.0, 'master': 4.0, 'sag': 0.3, 'output': 6.02}
# The 'neck pickup' of the heavy hero: the FSBS DI is a BRIDGE pickup (the 2nd harmonic as loud as the fundamental:
# into a high-gain amp the octave above wins and the note turns hollow and nasal). A key-tracked 12 dB/oct low-pass
# at ~1.3x the note (420 Hz at E4, 100 % key tracking) makes the fundamental lead - the singing neck / rolled-back tone
# knob lead. No filter envelope for the pick: any fixed opening at the attack (2400 or 1200 ct, ~100 ms) made every
# onset equally bright and erased the picking dynamics (the note-dynamics ear: 1.9 -> 0.0 dB from velocity).
NECK = {'cutoff': 420.0, 'veltrack': 0.0, 'keytrack': 100.0, 'env': None}
# The clean hero is one sampler: its picking dynamics are the velocity curve before a lightly driven amp. The pack's
# (v/127)^2 gave 1.2 dB per 10 velocity steps after the combo; about (v/127)^3.4 (and a 1.4:1 compressor) gives 2.0.
CLEAN_VELCURVE = ((1, 0.0), (40, 0.02), (64, 0.1), (90, 0.31), (110, 0.61), (127, 1.0))


# ------------------------------------------------------------------------------------------------ building blocks

def _di(level: float = _sg.DI_LEVEL['fsbs'], cutoff: float = 1300.0, veltrack: float = 3600.0, mono: str = 'legato',
        release: float | None = 0.08, velcurve=None, keytrack: float = 50.0, env=None):
    """The FSBS DI Strat (a mono legato player unless mono='off') whose voices get a velocity-tracking low-pass before
    the amp (a soft pick is darker: at velocity 64 the filter sits ~1.5 octaves below a velocity-127 note; +50 ct per
    key above E4). release: the zones' key-up release (the pack's is 0.2 s): a picked note stops the old one - with
    the pack's release a note in another velocity zone rang 0.2 s into the next pick and blurred its attack
    (velocity response 1.17 -> 1.39 dB per 10 steps with 0.08 s; None keeps the pack's). keytrack: cents per key of
    the cutoff (100 = it follows the note); env: a filter envelope (the zone's filterEnv: [depth ct, delay, attack,
    hold, decay, sustain, release])."""
    zone = {'filter': 'lpf_2p', 'cutoff': cutoff, 'resonance': 0.0, 'filVeltrack': veltrack, 'filKeytrack': keytrack,
            'filKeycenter': 64}
    if env is not None:
        zone['filterEnv'] = list(env)
    if release is not None:
        zone['release'] = release
    if velcurve is not None:
        zone['velcurve'] = [list(p) for p in velcurve]
    return inst.sfz_multi({'open': {'path': DI, 'zone': zone}}, lazy=True, level=level, mono=mono,
                          legatotime=30, glideshape='fast')


def _sustainer(threshold: float = -40.0, ratio: float = 6.0, release: float = 300.0):
    """A pick-attack-friendly compressor before the amp (the Dyna Comp / Ross in front of a Big Muff): 15 ms attack
    lets the pick through, the tail is lifted - a DI Strat's B4 dies -15 dB in 3 s, through this ~-2.5 dB."""
    return fx.compressor(threshold=threshold, ratio=ratio, attack=15, release=release, knee=10, automakeup='on',
                         name='sustainer')


def _post_comp(attack: float = 20.0, release: float = 120.0):
    return fx.compressor(threshold=-24, ratio=3, attack=attack, release=release, automakeup='on', name='comp')


def _tube_amp(gain: float, bright: float, cab: str = 'cab/rock_4x12', mic_lp: float = 6000.0, **knobs) -> list:
    """The library's amp (sampled_guitars.amp: the engine's tube head) with LEAD_AMP + knobs into a cab IR (a cab/*
    patch) and the mic's roll-off (70 Hz high-pass, a low-pass at mic_lp)."""
    return _sg.amp('lead', cab=cab, mic={'hp.freq': 70, 'lp.freq': mic_lp},
                   **dict(LEAD_AMP, gain=gain, bright=bright, **knobs))


def _zone_layers(zones, sustainer=None, post=None, di=None, **knobs) -> list:
    """One layer per velocity zone (vello, velhi, amp gain, bright cap dB, level dB): the DI -> [sustainer] -> the
    tube amp (_tube_amp: LEAD_AMP + knobs) -> a post compressor. di: a factory of the DI source (one per zone)."""
    out = []
    for i, (lo, hi, gain, bright, lvl) in enumerate(zones):
        chain = (([sustainer.copy()] if sustainer is not None else []) + _tube_amp(gain, bright, **knobs)
                 + [(post or _post_comp()).copy()])
        out.append(layer(di() if di else _di(), f'z{i + 1}', vel=(lo, hi), level=lvl, fx=chain))
    return out


def _echo_stage(time: float = 0.75, offset: float = 33.333, feedback: float = 0.32, mix: float = 0.2) -> dict:
    """The lead's own stereo echo as a heroes 'echo' stage: dotted 8th left, quarter right (offset 33.3 %), tape-dark
    repeats that duck under the playing and bloom in the gaps. Named 'echo': automate 'fx.echo.mix' for throws
    (hero.play(..., throws=True); heroes.hero() writes them at compile)."""
    return {'name': 'echo', 'mode': 'stereo', 'time': time, 'offset': offset, 'feedback': feedback, 'highcut': 3600,
            'lowcut': 350, 'wow': 0.15, 'duck': 0.35, 'width': 1.0, 'mix': mix}


def _echo(time: float = 0.75, offset: float = 33.333, feedback: float = 0.32, mix: float = 0.2):
    """The lead's own stereo echo (an FX; see _echo_stage)."""
    return heroes.stage_fx('echo', _echo_stage(time, offset, feedback, mix))[0]


# the guitar heroes' mix / space / playing rules for heroes.hero()
_GTR_MIX = {'duck': 2.5, 'duck_attack': 10.0, 'duck_release': 180.0, 'carve_db': 2.5, 'carve_freq': 2000.0,
            'carve_q': 0.8, 'ride_db': 1.0, 'dip_db': -2.0, 'dip_freq': 2000.0, 'dip_q': 0.9}
_GTR_PLAY = {'player': 'guitar', 'vel': (60, 118)}


def _preset(name: str, patch: str, source, stages: dict, order=None, **kw) -> None:
    heroes.define(name, family='guitar', source=source, chain=stages, order=order or heroes.ORDER, named=False,
                  gain_db=LEVELS[patch.split('/')[1]], patch=patch, mix=dict(_GTR_MIX), play=dict(_GTR_PLAY),
                  audition={'notes': 'phrase'}, **kw)
    heroes.register(name)


# ------------------------------------------------------------------------------------------------ the patches

_MIX_NOTES = ('MIX: the hero sits in front - in its sections the bed (pads, strings, keys, rhythm guitars) 3-5 dB under '
              'it (report: "bed ... vs lead", tracks.png per section); carve before pushing: s.sidechain(<bed tracks>, '
              'key=<hero>, depth=2.5, attack=10, release=180) and a -2 dB presence dip at 1.5-2.5 kHz on the rhythm '
              'guitars / keys; hall / plate sends are set, the echo is its own (throws: automate \'fx.echo.mix\' or '
              'hero.play(..., throws=True)). In a band preset: bands.<preset>(s, without=(\'lead\',)) and s.track(\'lead\', '
              '<hero>) - sounds={\'lead\': ...} would put the band\'s amp chain after the hero\'s; the band\'s echo bus then '
              'idles (report reverb_inaudible): feed it from the keys / piano or ignore it.')
_PLAY_NOTES = ('PLAY: through agentsound.patches.hero_guitar - hero.lead(track, melody, prog, bpm=s.tempo, key=s.key, '
               'style=..., section=..., memory=mem) (guitarist.lead: picked notes, slurs, slides, bends, vibrato, '
               'budgeted flash moves, touch() phrase dynamics) or hero.play(track, clip | arrangement | lick, at); '
               'plain notes and instrument.pitchbend also work direct. Velocity is the picking hand: 55-75 ghosted '
               'passing notes, 85-100 the line, 105-120 the peaks and bends (a phrase needs a 10-90 % velocity range '
               'of 20+ for the dynamics ear).')

_preset(
    'guitar', 'layered/hero_guitar',
    lambda: _zone_layers(ZONES, _sustainer(), di=lambda: _di(**PLEXI_DI), **PLEXI_LEAD),
    {'tone': {'name': 'tone', 'hp.freq': 90, 'hp.slope': 12, 'peak1.freq': 260, 'peak1.gain': -1.0,
              'peak1.q': 0.9, 'lp.freq': 7500},
     'tape': {'speed': '15', 'drive': 0.0, 'bump': 0.5, 'wow': 0.04, 'flutter': 0.04},
     'double': {'style': 'smooth', 'detune': 7, 'delay': 6, 'focus': 300, 'mix': 0.3},
     'echo': _echo_stage()},
    user_gain_db=2.5, words=('guitar', 'gtr', 'strat', 'stratocaster', 'lead_guitar'),
    measured={'lufs': -18.0, 'velocity_db_per_10': 1.9, 'b4_sustain_3s_db': -3.0},
    sends={'hall': -12, 'plate': -18},
    notes=f'v{VERSION}. The singing overdriven lead guitar (Gilmour, Slash "November Rain", Gary Moore, the Baker Street '
          'solo). SOURCE: the FreePats FSBS Stratocaster, bridge pickup, recorded DI (2 picking strengths x 4 random '
          'takes, E2-D6), the pickup rolled back (a key-tracked low-pass at ~1.9x the note: the fundamental leads), a mono '
          'legato player, key-up release 80 ms (a new pick stops the old note). CHAIN per velocity zone (5 zones, '
          '1-64 / 65-79 / 80-94 / 95-109 / 110-127): a sustainer compressor (15 ms attack: the pick speaks, the tail '
          'sings), the engine\'s tube amp as a cranked Plexi lead channel (fx \'amp\': 2 preamp stages, gain 4.4 / 5.0 / '
          '5.6 / 6.2 / 6.8, bright +2..+4 dB, a Tube Screamer push, Marshall stack mid 7.5, master 6: the power amp '
          'joins in, sag 0.35) into a Marshall 4x12 Greenback IR, a 3:1 compressor (20 ms attack); zone levels -12.8 / '
          '-9.6 / -6.4 / -3.2 / 0 dB (v1 was one tube saturator per zone at 19-27 dB of drive: a fuzz box). Then for '
          'the whole: eq (90 Hz high-pass, -1 dB at 260 Hz, low-pass 7.5 kHz), tape without drive, an H3000-style '
          'microshift double (+-7 ct above 300 Hz: width without phasing) and its own stereo echo (dotted 8th left / '
          'quarter right, dark, ducked). ' + _MIX_NOTES + ' ' + _PLAY_NOTES + ' Range G3-D6 (solos G4-D6; above C6 '
          'the DI decays in ~3 s even with the sustainer - long held peaks: layered/hero_guitar_heavy). Tweak: '
          '.layer("z5", level=1) (hotter peaks), .but_fx("echo", mix=0.3), .but_fx("microshift", mix=0) (a dry mono '
          'lead). Samples CC0; cab IR Jester Emerald (CC0). '
          'Measured -18.0 LUFS (audition phrase).')

_preset(
    'guitar_clean', 'sampled/hero_guitar_clean',
    lambda: _di(cutoff=1700.0, veltrack=3000.0, mono='off', release=0.12, velcurve=CLEAN_VELCURVE),
    {'comp': {'threshold': -18, 'ratio': 1.4, 'attack': 25, 'release': 220, 'knee': 8, 'automakeup': 'on',
              'name': 'comp'},
     'amp': _sg.amp('blues', gain=2.0, bright=3.0),
     'tone': {'name': 'tone', 'hp.freq': 120, 'hp.slope': 24, 'peak1.freq': 700, 'peak1.gain': -2.0, 'peak1.q': 0.8,
              'peak2.freq': 2800, 'peak2.gain': 2.0, 'peak2.q': 1.2, 'peak3.freq': 5200, 'peak3.gain': -1.5,
              'peak3.q': 1.0, 'lp.freq': 9500},
     'tape': {'speed': '15', 'drive': 2.0, 'bump': 0.5, 'wow': 0.04, 'flutter': 0.04},
     'double': {'style': 'smooth', 'detune': 6, 'delay': 4, 'focus': 300, 'mix': 0.22},
     'echo': _echo_stage(time=1.0, offset=-25.0, feedback=0.25, mix=0.14)},
    order=('comp', 'amp', 'tone', 'tape', 'double', 'echo'),
    user_gain_db=-2.9, aliases=('clean_guitar',),
    measured={'lufs': -18.0, 'velocity_db_per_10': 2.0},
    sends={'plate': -14, 'hall': -16},
    notes=f'v{VERSION}. The clean-ish Strat lead (Knopfler "Sultans of Swing", "Brothers in Arms" clean passages, '
          'Gilmour clean, 80s pop-rock fills): the FreePats FSBS Stratocaster DI, polyphonic (notes ring into each '
          'other like strings, 120 ms release; a velocity-tracking low-pass per note: soft picks darker; a velocity '
          'curve ~(v/127)^3.4) -> a gentle 1.4:1 compressor (25 ms attack: the pick snaps) -> an edge-of-breakup '
          'British combo (the engine\'s tube amp, blues voicing at gain 2, bright cap +3 dB, a 1x12 Celestion '
          'G12H30 IR) -> eq (-2 dB boxiness at 700 Hz, +2 dB snap at 2.8 kHz, low-pass 9.5 kHz), tape, a light '
          'microshift double and a quarter / dotted-8th stereo echo (low mix). A PLAIN SAMPLER: guitarist.lead(..., '
          'sound=track) and arrangement.play(track, at) work direct (hero.lead / hero.play do the same); the guitarist '
          'plays it as a polyphonic guitar (double stops, slides as softly touched frets, hammer-ons as soft notes). '
          'Pitch bends and instrument.vibrato move every ringing note: bend single notes. Velocity moves level and '
          'tone (~2 dB per 10 velocity steps). ' + _MIX_NOTES + ' Play it like Knopfler: '
          'fingerpicked single notes and double stops, quick hammer-on / pull-off triplets, slides into chord tones, '
          'answering phrases between the melody (guitarist style \'country\' or \'pop\'); velocity 60-115. Range E3-D6. '
          'Samples CC0; cab IR Overdriven (free for music). '
          'Measured -18.0 LUFS (audition phrase).')


def _metal_double(level: float):
    """The SampleRadar Guitar B lead multisample (an amped, singing high-gain lead, one long note every minor 3rd
    D2-D6) as a legato layer under the DI zones: sustain, a real amp's grain and a second performance for width."""
    return inst.multisample(METAL_LEAD, lazy=True, level=level, keys=(36, 90), loop='none', tune=-10,
                            mono='legato', legatotime=40, glideshape='fast', release=0.08, velsens=0.9)


HEAVY_VERSION = 2    # v2: the engine's tube amp + the neck-pickup filter (v1: one saturator per zone, songs/kestrel-bay/TONE.md)


def _neck_di():
    return _di(cutoff=NECK['cutoff'], veltrack=NECK['veltrack'], keytrack=NECK['keytrack'], env=NECK['env'])


_preset(
    'guitar_heavy', 'layered/hero_guitar_heavy',
    lambda: _zone_layers(HEAVY_ZONES, sustainer=_sustainer(threshold=-36.0, ratio=5.0), di=_neck_di) + [
        layer(_metal_double(_sg.LEVELS['metal_lead']), 'double', level=-7.0, pan=0.45,
              fx=[fx.eq({'hp.freq': 140, 'hp.slope': 24, 'peak1.freq': 400, 'peak1.gain': -2.0, 'peak1.q': 0.8,
                         'peak3.freq': 3800, 'peak3.gain': -3.0, 'peak3.q': 1.0, 'lp.freq': 7000}),
                  fx.compressor(threshold=-22, ratio=3, attack=12, release=150, automakeup='on')])],
    {'tone': {'name': 'tone', 'hp.freq': 80, 'hp.slope': 12, 'lp.freq': 7500},
     'tape': {'speed': '15', 'drive': 0.0, 'bump': 0.5, 'wow': 0.04, 'flutter': 0.04},
     'double': {'style': 'smooth', 'detune': 9, 'delay': 8, 'focus': 300, 'mix': 0.3},
     'echo': _echo_stage(time=0.75, offset=33.333, feedback=0.3, mix=0.18)},
    user_gain_db=2.7, aliases=('heavy_guitar',),
    measured={'lufs': -18.0, 'velocity_db_per_10': 1.6},
    sends={'hall': -13, 'plate': -18},
    notes=f'v{HEAVY_VERSION}. The heavy singing lead (Slash, Gary Moore "Parisienne Walkways" / "Still Got the Blues", '
          '80s arena solos, hard-rock ballads): the FSBS Stratocaster DI as a NECK pickup (a key-tracked low-pass at '
          '~1.3x the note so the fundamental leads - the bridge DI\'s octave would otherwise win in the amp and sound '
          'hollow -) in 4 velocity zones (1-69 / 70-86 / 87-104 / 105-127) '
          'through a sustainer and the engine\'s tube amp (fx \'amp\': 3 cascaded preamp stages, gain 5.6 / 6.3 / 7.0 / '
          '7.6, bright +1..+4 dB, a light Tube Screamer push, Marshall tone stack bass 5 mid 7 treble 7, presence 8, '
          'master 4, sag 0.3) into a Marshall 4x12 Greenback IR, levels -9.6 / -6.4 / -3.2 / 0 dB; + the SampleRadar '
          'amped lead multisample as a legato double 7 dB down, panned right (different guitar, different amp: no '
          'phasing; it sustains 5-10 s). Then a gentle eq (80 Hz high-pass, 7.5 kHz low-pass), tape without drive (the amp is the distortion: tape drive after it put the fizz back above 8 kHz), microshift double, '
          'dotted-8th / quarter echo. Measured (songs/kestrel-bay/TONE.md): odd harmonics lead (h3 / h5 over h2 / h4 like '
          'a real amped lead), held notes lose ~4 dB in the first second then hold (-0.5 dB/s), 4-8 kHz at -14 dB of '
          'the energy like a recorded lead. ' + _MIX_NOTES + ' ' + _PLAY_NOTES + ' Range G3-D6. Tweak: '
          '.layer("double", level=-4) (thicker, more sustain), .layer("double", mute=True); the amp per zone: '
          '.but_fx on the zone layers (\'amp\': gain / mid / presence / master). Samples: FSBS CC0; SampleRadar '
          'royalty-free for music, no redistribution of the samples. Measured -18.0 LUFS (audition phrase).')


# ------------------------------------------------------------------------------------------------ performance

_PICK_GAP_MS = 14.0     # a re-picked note: the old one stops this much before (as guitarist.lead)
_LOCK_REACH = 8         # a tied note may be moved this far in velocity to stay in its zone (else it is re-picked)


def _stack(track):
    ins = getattr(track, 'instrument', None)
    return ins if getattr(ins, 'type', None) == 'stack' else None


def sampler_layers(track) -> list:
    """Ids of the sampler layers of a stack track (they get the glide / vibrato lanes); [] for other tracks."""
    st = _stack(track)
    return [x.id for x in st.layers if x.instrument.type == 'sampler'] if st is not None else []


def zones(track) -> list:
    """The velocity zones of a stack track: (vello, velhi) of its layers that have a velocity range, sorted."""
    st = _stack(track)
    if st is None:
        return []
    out = {(int(x.params.get('vello', 0)), int(x.params.get('velhi', 127))) for x in st.layers
           if 'vello' in x.params or 'velhi' in x.params}
    return sorted(out)


def _zone_of(v: float, zs):
    for i, (lo, hi) in enumerate(zs):
        if lo <= v <= hi:
            return i
    return None


def lock_ties(clip, zs, bpm: float):
    """The legato lock: a tie (a note starting while the one before still sounds) that would cross a zone edge keeps
    the first note's zone - its velocity clamped to that zone when the clamp is within _LOCK_REACH of the written
    velocity or the note glides (a slide stays on one string), else the tie is broken (the old note stops
    _PICK_GAP_MS before: a new pick). Returns (clip, number clamped, number re-picked)."""
    from .. import articulation as _art
    from ..patterns import Clip
    ns = sorted(clip, key=lambda n: (n.start, -n.pitch))
    if not zs or len(ns) < 2:
        return clip, 0, 0
    gap = _PICK_GAP_MS / 1000.0 * bpm / 60.0
    out = list(ns)
    clamped = repicked = 0
    for k in range(1, len(out)):
        a, b = out[k - 1], out[k]
        if b.start <= a.start + 1e-6 or b.start > a.start + a.dur + 1e-6:
            continue                                  # a chord note, or a note after a rest / a pick gap
        za, zb = _zone_of(a.vel, zs), _zone_of(b.vel, zs)
        if za is None or zb is None or za == zb:
            continue
        lo, hi = zs[za]
        v = min(max(b.vel, lo), hi)
        if _art.glide_of(b) or abs(v - b.vel) <= _LOCK_REACH:
            out[k] = b._replace(vel=int(v))
            clamped += 1
        else:
            out[k - 1] = a._replace(dur=max(0.02, b.start - a.start - gap))
            repicked += 1
    return Clip._raw(out, clip.length), clamped, repicked


def _glide_points(clip, at: float, base: float = 0.0) -> list:
    """'glide' lane steps for the glide-marked notes of a clip placed at `at` (as the compiler writes them for a
    sampler; the reset a little later, so a humanized note still latches its glide)."""
    from .. import articulation as _art
    starts = sorted({at + n.start for n in clip})
    pts: list = []
    for n in clip:
        g = _art.glide_of(n)
        if not g:
            continue
        b = at + n.start
        prev = max((x for x in starts if x < b - 1e-9), default=None)
        nxt = min((x for x in starts if x > b + 1e-9), default=b + 1.0)
        lead_ = max(b - 0.05, (prev + b) / 2.0 if prev is not None else b - 0.05, 0.0)
        pts += [(max(0.0, lead_ - 0.01), base, 'step'), (lead_, float(g), 'step'),
                (b + min(0.1, 0.5 * (nxt - b)), base, 'step')]
    return pts


def _throw_points(clip, at: float, base: float, lift: float = 0.2) -> list:
    """Echo throws: at each phrase end (a rest of 1+ beat after it, or the part's end) the echo mix rises by `lift`
    as the note ends and falls back before the next phrase."""
    ns = sorted(clip, key=lambda n: n.start)
    pts: list = []
    for i, n in enumerate(ns):
        end = n.start + n.dur
        nxt = min((m.start for m in ns[i + 1:] if m.start > n.start + 1e-9), default=None)
        room = (nxt - end) if nxt is not None else 4.0
        if room < 1.0 - 1e-6 or n.dur < 0.45:
            continue
        up, top = at + max(n.start, end - 0.25), at + end + 0.25
        down = at + end + min(3.0, room - 0.3)
        if down <= top + 0.5:
            continue
        pts += [(up, base), (top, round(base + lift, 4), 'smooth'), (down - 0.4, round(base + lift, 4)),
                (down, base, 'smooth')]
    return pts


def _fx_param(track, name: str, param: str, default: float) -> float:
    for f in getattr(track, 'fx', []) or []:
        if getattr(f, 'name', None) == name:
            return float(f.params.get(param, default))
    return default


def play(track, part, at=0.0, *, lock: bool = True, throws: bool = False, vib=None):
    """Play a part on a hero guitar track: a Clip (glide marks kept), a guitarist Arrangement (lead() / arrange():
    notes + its pitchbend / vibrato automation) or a Lick (bend, prebend, vibrato moves). On a stack (the driven
    heroes) the glide marks become 'instrument.layers.<id>.glide' steps and the vibrato lanes go to every sampler
    layer; lock=True keeps ties inside one velocity zone (lock_ties); throws=True raises the echo ('fx.echo.mix') at
    the phrase ends; vib=True / {'depth': .., 'rate': ..} adds articulation.vibrato_points on the long notes of a
    plain Clip. On a plain sampler track it is the normal play (the compiler does the glides) plus the same automation.
    Returns the clip as placed (relative to `at`)."""
    from .. import articulation as _art
    from ..patterns import as_clip
    clip = getattr(part, 'clip', None)
    auto = dict(getattr(part, 'auto', None) or {})
    if clip is None:
        clip = as_clip(part)
    song = getattr(track, '_song', None)
    a = song._at(at) if song is not None else float(at)
    bpm = song.tempo_at(a) if song is not None else 120.0
    if vib:
        opts = {'depth': 26.0, 'rate': 5.6} if vib is True else dict(vib)
        auto.update(_art.vibrato_points(clip, bpm, **opts))
    st = _stack(track)
    if st is not None:
        if lock:
            clip, _, _ = lock_ties(clip, zones(track), bpm)
        ids = sampler_layers(track)
        gl = _glide_points(clip, a)
        track.play(_art.plain(clip), a)
        for lid in ids:
            if gl:
                track.automate(f'instrument.layers.{lid}.glide', gl)
        for tgt, pts in auto.items():
            shifted = [(max(0.0, a + p[0]),) + tuple(p[1:]) for p in pts]
            if tgt in ('instrument.vibrato', 'instrument.vibratorate'):
                for lid in ids:
                    track.automate(f"instrument.layers.{lid}.{tgt.split('.', 1)[1]}", shifted)
            else:
                track.automate(tgt, shifted)
    else:
        track.play(clip, a)
        sampler = getattr(getattr(track, 'instrument', None), 'type', None) == 'sampler'
        for tgt, pts in auto.items():
            if tgt in ('instrument.vibrato', 'instrument.vibratorate') and not sampler:
                continue
            track.automate(tgt, [(max(0.0, a + p[0]),) + tuple(p[1:]) for p in pts])
    if throws:
        pts = _throw_points(clip, a, _fx_param(track, 'echo', 'mix', 0.2))
        if pts:
            track.automate('fx.echo.mix', pts)
    return clip


def lead(track, melody, prog=None, *, bpm=None, key=None, section=None, at=None, lock: bool = True,
         throws: bool = False, **kw):
    """guitarist.lead(...) played on a hero guitar track: the melody fingered, picked and slurred, touch() phrase
    dynamics, bends / slides / vibrato / budgeted flash moves (kw: style, energy, density, seed, memory, climax,
    moves, flash_every ... as guitarist.lead), then play(track, arrangement, at). A stack track plays as a mono legato
    player (mono=True); a plain sampler track is passed as sound= (its own legato / articulations are read). Returns the
    Arrangement."""
    from .. import guitarist as _gtr
    song = getattr(track, '_song', None)
    if isinstance(section, str) and song is not None:
        section = song[section]                      # a section name: the song's Section (its start places the part)
    pos = at if at is not None else section
    if pos is None:
        pos = 0.0
    a = song._at(pos) if song is not None else float(getattr(pos, 'start', pos))
    if bpm is None:
        bpm = song.tempo_at(a) if song is not None else 120.0
    if key is None and song is not None:
        key = song.key
    if _stack(track) is not None:
        kw.setdefault('mono', True)
        kw.setdefault('articulations', {})
    else:
        kw.setdefault('sound', track)
    arr = _gtr.lead(melody, prog, bpm=bpm, key=key, section=section, at=a, **kw)
    play(track, arr, a, lock=lock, throws=throws)
    return arr
