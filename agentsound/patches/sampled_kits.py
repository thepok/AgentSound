"""Sampled drum kits built by the kit builder (inst.kit, agentsound/kits.py) from one-shot collections, Hydrogen kits
and drum machine sample sets: real drum machines and real drummers' kits, GM-mapped like every kit here.

  machines:  sampled/linndrum sampled/tr808 sampled/tr909 sampled/tr707 sampled/dmx sampled/drumtraks
  80s pop:   sampled/80s_pop_kit sampled/80s_gated_kit (gated snares, electronic toms)
  acoustic:  sampled/studio_kit (close mics, velocity layers + round robins) sampled/room_kit sampled/forzee_kit
             sampled/pacific_kit

GM keys: 36 kick (35 kick 2), 37 rim / side stick, 38 snare (40 snare 2), 39 clap, 42 / 44 / 46 closed / pedal / open
hat (they choke each other), 41 43 45 47 48 50 toms low -> high, 49 / 57 crash, 51 / 59 ride, 53 ride bell, 54
tambourine, 56 cowbell, 60+ hand percussion; each kit's notes list what it has. Extra variants sit on keys 88 and up
(python -m agentsound kit <folder> prints the whole map). Every patch builds its zones when a song renders it (lazy):
importing the library needs no samples, a missing pack fails at use with its fetch command.

Level calibration: every patch at gain_db 0 lands at about -18 LUFS (track node, dry) playing the audition groove
(`python -m agentsound audition <patch>`), measured value in the notes. Licences (python -m agentsound samples -v):
MusicRadar SampleRadar packs are royalty-free for music but may not be redistributed; the hyperreal.org machine sets
have no formal licence ('Unclear-free-download': fine for sketches, check before releasing); Hydrogen kits: Forzee
GPL-2.0, BJA Pacific CC-BY-SA 3.0 (credit Bransin James Anderson). Version: see VERSION.
"""

from . import Patch, fx, inst, register

VERSION = 2


def _hp(freq: float = 25.0):
    """High-pass: removes the DC offset and subsonic rumble many old machine samples carry."""
    return fx.eq({'hp.freq': freq, 'hp.slope': 24})


def _kit(source: str, level: float, **kw):
    return inst.kit(source, lazy=True, level=level, **kw)


# --------------------------------------------------------------------------------------------- drum machines

register(Patch(
    'sampled/linndrum',
    instrument=_kit('samples/hyperreal-linndrum', level=-1.7),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. LinnDrum LM-2 (hyperreal.org set, 44.1 kHz): the 80s pop machine (Prince, Hall & Oates, Human League). '
          'Keys: 36 kick (35 "kickme"), 38 snare (40 high snare), 37 side stick, 39 clap, 42 / 46 hats (44 = closed), '
          'toms 41 43 45 48 50 (47 filled), 49 crash, 51 ride, 54 tambourine, 56 cowbell, 62-64 congas, 69 cabasa; '
          'extras 88+: long / short closed hats, low snare, high / low side sticks, low congas, the demo loop. Tweak: '
          "tune (whole kit), gains={'hats': -3} in your own inst.kit(...). License unclear (free download, no terms). "
          'Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/tr808',
    instrument=_kit('samples/sampleradar-essential-drumkit/TR 808 Kit', level=1.6,
                    gains={'hats': -7, 'cymbals': -8, 'clap': -3, 'cowbell': -6, 'conga': -4, 'maracas': -8,
                           'claves': -6, 'rim': -4}),
    fx=[_hp(22)],
    sends={'plate': -24},
    notes='v1. Roland TR-808 (SampleRadar essential drum kit, 23 hits): the long boomy kick, snappy snare, clap, '
          'metallic hats. Keys: 36 kick (35 / 90 other kick tunings), 38 / 40 snares, 39 clap, 37 rimshot, 42 / 46 '
          'hats (44 = closed), 41 45 48 toms (43 47 50 retuned fills), 49 / 57 cymbals, 56 cowbell, 62 / 63 congas, '
          '70 maracas, 75 claves. Glides: automate instrument.pitchbend. MusicRadar licence: royalty-free, no '
          'redistribution. Sends: plate -24. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/tr909',
    instrument=_kit('samples/hyperreal-tr909', level=-1.1, extras=False, map={
        'kick': 'BT3AADA.WAV', 'kick2': 'BT7A0D7.WAV',
        'snare': 'ST3T7S7.WAV', 'snare2': 'ST0TAS7.WAV',
        'clap': {'files': ['HANDCLP1.WAV', 'HANDCLP2.WAV'], 'layers': 'rr'},
        'rim': {'files': ['RIM63.WAV', 'RIM127.WAV'], 'layers': 'velocity'},
        'hat': 'HHCD2.WAV', 'pedal_hat': 'HHCD0.WAV', 'open_hat': 'HHOD6.WAV',
        'crash': 'CSHD8.WAV', 'crash2': 'CSHD4.WAV', 'ride': 'RIDED6.WAV', 'ride2': 'RIDEDA.WAV',
        'tom_lo': 'LT3D7.WAV', 'tom_floor_hi': 'LT7D7.WAV', 'tom_mid': 'MT3D7.WAV', 'tom_lowmid': 'MT7D7.WAV',
        'tom_hi': 'HT3D7.WAV', 'tom_high': 'HT7D7.WAV'},
        gains={'hats': -4, 'cymbals': -5}),
    fx=[_hp(22)],
    sends={'plate': -24},
    notes='v1. Roland TR-909 (Rob Roy Recordings set, hyperreal.org, every knob position sampled): house / techno / '
          'synthwave. Chosen settings: kick BT3AADA (tune 3, attack and decay full; 35 = BT7A0D7, tighter), snare '
          'ST3T7S7 (40 = ST0TAS7, brighter), clap (2 takes alternating), rim (2 velocity layers), hats HHCD2 / pedal '
          'HHCD0 / open HHOD6, crash CSHD8 (57 CSHD4), ride RIDED6 (59 RIDEDA), toms 41-50 from the low / mid / high '
          'toms at two tunings. Other settings: inst.kit("samples/hyperreal-tr909", map={...}) with the file names '
          '(python -m agentsound kit samples/hyperreal-tr909). License unclear (free, not for profit). Sends: plate '
          '-24. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/tr707',
    instrument=_kit('samples/hyperreal-tr707', level=0.8, gains={'hats': -3, 'cymbals': -3}),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. Roland TR-707 (hyperreal.org, 15 hits): the crisp mid-80s digital machine (Italo, freestyle, '
          'synth-pop). Keys: 36 kick (its two bass drums alternate), 38 / 40 snares, 37 rimshot, 39 clap, 42 / 46 '
          'hats, 41 45 48 toms, 49 crash, 51 ride, 54 tambourine, 56 cowbell. License unclear (free download). '
          'Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/dmx',
    instrument=_kit('samples/sampleradar-essential-drumkit/DX_DMX Kit', level=0.4,
                    gains={'hats': -7, 'cymbals': -8, 'tambourine': -8, 'shaker': -8, 'clap': -3, 'timbale': -4}),
    fx=[_hp(25)],
    sends={'plate': -22},
    notes='v1. Oberheim DMX / DX (SampleRadar essential drum kit): the hard, punchy 12-bit machine of 80s hip-hop and '
          'synth-pop (Run-DMC, New Order, Madonna). Keys: 36 / 35 kicks, 38 / 40 snares, 37 rimshot, 39 clap, 42 / 46 '
          'hats, toms 41 45 48 50 (measured low -> high), 49 / 57 cymbals, 54 tambourine, 65 / 66 timbales, 82 '
          'shaker. MusicRadar licence: royalty-free, no redistribution. Sends: plate -22. Measured -18.0 LUFS '
          '(audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/drumtraks',
    instrument=_kit('samples/hyperreal-drumtraks', level=0.1, gains={'hats': -3, 'cymbals': -3}),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. Sequential Circuits Drumtraks (hyperreal.org, 13 hits): warm early-80s digital drums, big toms. '
          'Keys: 36 kick, 38 snare, 37 rimshot, 39 clap, 42 / 46 hats, 45 / 48 toms (others retuned fills), 49 crash, '
          '51 ride, 54 tambourine, 56 cowbell, 69 cabasa. License unclear (free download). Sends: plate -22. '
          'Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

# --------------------------------------------------------------------------------------------- 80s pop

_POP = 'samples/sampleradar-80s-pop-drums'

register(Patch(
    'sampled/80s_pop_kit',
    instrument=_kit(f'{_POP}/Drum Kits/Kit A', level=-3.0,
                    map={'snare2': f'{_POP}/Gated Snares/80PD_GatedSnare-05.wav'},
                    gains={'hats': -8, 'shaker': -8, 'clap': -3}),
    fx=[_hp(28)],
    sends={'gated': -10, 'plate': -24},
    notes='v1. SampleRadar 80s Pop Drums, kit A: big processed 80s studio drums (Phil Collins, Tears for Fears). '
          'Keys: 36 / 35 kicks, 38 snare (88+ two more), 40 gated snare, 39 clap, 42 / 46 hats (88 half-open), toms '
          '41-50 (low / mid / high, two hits each), 82 shaker. More gated snares: map={"snare": "' + _POP + '/Gated '
          'Snares/80PD_GatedSnare-12.wav"} (32 of them). MusicRadar licence: royalty-free, no redistribution. Sends: '
          'gated -10, plate -24. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/80s_gated_kit',
    instrument=_kit(f'{_POP}/Drum Kits/Kit C', level=-0.7,
                    map={'snare': f'{_POP}/Gated Snares/80PD_GatedSnare-12.wav',
                         'snare2': f'{_POP}/Gated Snares/80PD_GatedSnare-20.wav'},
                    gains={'hats': -8, 'shaker': -8, 'tambourine': -8, 'cymbals': -6, 'conga': -4, 'cowbell': -6}),
    fx=[_hp(28)],
    sends={'plate': -24},
    notes='v1. SampleRadar 80s Pop Drums, kit C with gated-reverb snares on 38 / 40 (the snare carries its own gated '
          'room, no gated send needed): power ballads, synth-pop, outrun. Keys: 36 kick, 38 / 40 gated snares (88+ the '
          "kit's own snares), 39 clap, 42 / 46 hats, 41 45 48 toms, 49 / 57 crashes, 56 cowbell, 54 tambourine, 62-64 "
          'congas, 82 shaker. MusicRadar licence: royalty-free, no redistribution. Sends: plate -24. Measured -18.0 '
          'LUFS (audition groove).',
    audition={'notes': 'drums'}))

# --------------------------------------------------------------------------------------------- acoustic

_DS = 'samples/sampleradar-drum-samples/Drum Kits'

register(Patch(
    'sampled/studio_kit',
    instrument=_kit(f'{_DS}/Kit 1 - Acoustic close', level=2.7, gains={'hats': -3}),
    fx=[_hp(30)],
    sends={'plate': -18},
    notes='v1. SampleRadar acoustic kit, close microphones: several hits per drum at rising strength, played as '
          'velocity layers with round robins inside a layer (no two hits alike), so dynamics sound played. Keys: 36 '
          'kick (8 hits), 38 snare, 40 rimshot, 37 side stick, 42 / 44 / 46 hats (9 / 4 / 7 hits), 88+ flams and '
          'snares-off. No toms or cymbals in this set: add sampled/room_kit or a cymbal track. Use velocities 30-127. '
          'MusicRadar licence: royalty-free, no redistribution. Sends: plate -18. Measured -18.0 LUFS (audition '
          'groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/room_kit',
    instrument=_kit(f'{_DS}/Kit 2 - Acoustic room', level=0.7, gains={'hats': -3}),
    fx=[_hp(30)],
    sends={'plate': -24},
    notes='v1. SampleRadar acoustic kit, room microphones: the same drummer as sampled/studio_kit heard from the '
          'room (layer the two for close + room). Velocity layers with round robins. MusicRadar licence: royalty-free, '
          'no redistribution. Sends: plate -24. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/forzee_kit',
    instrument=_kit('samples/hydrogen-forzee-stereo', level=0.0),
    fx=[_hp(30)],
    sends={'plate': -20},
    notes='v2. Forzee Stereo Drumkit (Hydrogen; Tama Superstar, Pearl snare, Paiste cymbals, 4 microphones mixed to '
          'stereo): a full rock / pop kit with 3-5 velocity layers per piece. Keys: 36 kick, 38 snare, 40 rimshot, 37 '
          'rim click (side stick), 42 / 44 / 46 hats, 41 45 48 toms, 49 crash, 51 ride (59 crash/ride), 53 ride bell, '
          '52 china, 55 splash, 54 tambourine, 67 / 68 agogo; 88+ snares-off snare and rimshot, semi-open hat, ride, '
          'crash/ride bow and bell, foot tambourine, sticks. GPL-2.0. Sends: plate '
          '-20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/pacific_kit',
    instrument=_kit('samples/hydrogen-bja-pacific', level=-1.8),
    fx=[_hp(30)],
    sends={'plate': -20},
    notes='v1. BJA Pacific (Hydrogen, sampled by Bransin James Anderson): a warm acoustic kit with 8 velocity layers '
          'on kick, snare, toms and hats. Keys: 36 kick, 38 snare (40 dry snare), 42 / 46 hats, 41 floor tom, 48 tom, '
          '49 / 57 crashes, 51 / 59 rides, 53 ride bell; 88 snare roll. License CC-BY-SA 3.0 US: credit Bransin James '
          'Anderson. Sends: plate -20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))
