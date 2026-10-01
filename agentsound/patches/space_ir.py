"""Convolution spaces and guitar cabinets: return buses and DI-guitar insert chains on the 'convolver' effect and
the impulse-response packs of the sample library (python -m agentsound samples; find ir).

  returns    bus/ir_hall bus/ir_hall_bright bus/ir_hall_dark               Lexicon 224XL halls
             bus/ir_plate bus/ir_plate_b bus/ir_plate_short bus/ir_plate_rich bus/ir_plate_small
             bus/ir_chamber bus/ir_chamber_rich bus/ir_chamber_dark        224XL plates and chambers
             bus/ir_room bus/ir_room_big bus/ir_ambience bus/ir_room_small 224XL rooms
             bus/ir_inverse                                               224XL inverse room (80s reverse-build snare)
             bus/ir_hall_large bus/ir_concert_hall bus/ir_church bus/ir_opera bus/ir_salon bus/ir_drum_room
                                                                          Voxengo IM Reverbs (modelled real spaces)
  cabinets   cab/clean_1x12 cab/blues_1x12 cab/crunch_2x12 cab/rock_4x12 cab/metal_4x12
             DI guitar -> amp (the tube head: AMPS) -> convolver (the cabinet) -> eq (the mic)

The Lexicon 224XL (1978-) is THE 80s digital reverb; the Little Devil sets capture it in true stereo (four mono
files per preset: left / right input x left / right output), which the convolver plays as recorded. Every IR lives
in a sample pack: a patch whose pack is not installed yet is registered anyway (its notes start with 'NOT INSTALLED'
after the version), and rendering it fails with the pack to fetch (python -m agentsound samples fetch <id>). A
preset's files are looked up when the library loads.

Returns are 100 % wet (mix 1), energy-normalised IRs with a clean-up high-pass, drop-in replacements for the
algorithmic returns: the same send gives the same return level (within ~1 LU, measured in the report on a keys +
pad phrase and a snare) as bus/hall for the halls, chambers, rooms, church, opera and salon, as bus/plate for the
plates, the inverse room, the ambience and the drum room. v3 re-measured every 224XL return once all packs were
installed (a pad + e-piano phrase and a snare, each sending -8 dB, return level against bus/hall at the same send):
halls, chambers and rooms match bus/hall within about +-1 dB. The IR plates were matched against bus/plate v1: since
the lush pass gave bus/plate +7 dB of output (v2), every IR plate (and the plate-matched inverse room, ambience and
drum room) returns about 8 dB less than bus/plate at the same send (measured v3: ir_plate -8.8 dB on the phrase /
-6.3 dB on the snare, ir_plate_rich -7.8 / -7.4, ir_plate_small -7.6 / -8.2): send 6-8 dB more to them, or give
the plate bus gain_db +6..+8 (the synthwave band presets do). Use them like song.hall():
    hall = s.bus('hall', 'bus/ir_hall');  pad = s.track('pad', ..., sends={hall: -8})
    plate = s.bus('plate', patches.get('bus/ir_plate').but(predelay=30))       # params go to the convolver
Next to bus/hall the IR returns are denser and steadier (no modulation shimmer; the 224XL's flat 'constant
density' tail runs up to its ~10-12 kHz band limit, where bus/hall darkens with damping) and more coherent in the
lows (the 224XL: correlation ~0.5 below 150 Hz instead of ~0).
Cabinets are insert chains for a DI guitar track: s.track('gtr', <DI guitar>, fx=patches.get('cab/rock_4x12').fx);
they keep the DI's loudness (within 0.2 LU on a riff + lead phrase).
Version: see VERSION (bump it when a sound changes audibly).
"""

from .. import library
from . import Patch, fx, register

VERSION = 4  # v4: the cab/* chains on the engine amp (was a saturator); v2: bus/ir_ambience widened 1.5 (it was narrow from a centred source), gain re-matched
# v3: the 'gain estimated' 224XL returns re-measured with their packs installed (gains -1.9..+2.8 dB)


def _files(pack: str, *patterns: str):
    """'samples/<pack>/<file>' for each glob pattern (inside the pack folder; the first sorted match), or the list
    of them for a multi-file IR. A pack that is not installed keeps the pattern, so the render names the pack."""
    root = library.SAMPLES / pack
    installed = (root / 'SOURCE.json').is_file()
    out = []
    for pat in patterns:
        # top level first, then anywhere below (archives often unpack into a folder of their own)
        hits = []
        if installed:
            hits = sorted(p for p in root.glob(pat) if p.is_file()) or sorted(p for p in root.rglob(pat) if p.is_file())
        out.append('samples/' + (hits[0].relative_to(library.SAMPLES).as_posix() if hits else f'{pack}/{pat}'))
    return out[0] if len(out) == 1 else out


def _pack_note(ir) -> str:
    """' [NOT INSTALLED ...]' when an IR file of the patch is missing (its pack has not arrived yet), else ''."""
    files = ir if isinstance(ir, list) else [ir]
    for f in files:
        rel = f[len('samples/'):]
        if not (library.SAMPLES / rel).is_file():
            pack = rel.split('/', 1)[0]
            return (f" [NOT INSTALLED: pack '{pack}' is missing, a render with this patch fails until it is installed "
                    f"(python -m agentsound samples)]")
    return ''


def _xl(pack: str, variation: int = 1):
    """A Little Devil Lexicon 224XL preset: '<program> V<variation>.<input>[-01].<output>.wav', input 1 = left,
    2 = right, output L / R: four mono files in the convolver's true-stereo order LL, LR, RL, RR."""
    return _files(pack, *(f'* V{variation}.{i}*.{o}.wav' for i in (1, 2) for o in ('L', 'R')))


def _with_pack_note(notes: str, ir) -> str:
    version, _, rest = notes.partition('. ')  # 'v1' / 'v1 (gain estimated)' stays first
    return version + _pack_note(ir) + '. ' + rest


def _return(name: str, ir, notes: str, **params):
    p = {'mix': 1.0, 'lowcut': 220, **params}
    register(Patch(name, fx=[fx.convolver(ir=ir, **p)], notes=_with_pack_note(notes, ir)))


def _use(bus_id: str, name: str) -> str:
    return (f"Use: s.bus('{bus_id}', '{name}'); sends={{bus: -8}} (pads/strings -6..-12, leads -10..-14, keys -12..-16, "
            f"snare -14..-18). Params go to the convolver: .but(predelay=40, lowcut=300, highcut=8000, width=1.2).")


_XL = 'little-devil-224xl-'

# ------------------------------------------------------------------------------------------------- halls

_return('bus/ir_hall', _xl(_XL + '01-concert-hall'),
        'v2 (measured: bus/hall level +0.3 dB phrase / -0.5 dB snare). Lexicon 224XL Concert Hall (true stereo): '
        'the classic 80s digital hall - smooth, dense, a little grainy and dark on top (the 224XL stops near 10 kHz); '
        'big and wide, it glues pads, strings and slow leads. 20 ms extra pre-delay, wet high-passed at 220 Hz. '
        + _use('hall', 'bus/ir_hall'),
        predelay=20, gain=-6.0)
_return('bus/ir_hall_bright', _xl(_XL + '02-bright-hall'),
        'v2 (measured: bus/hall level +0.4 / -0.8 dB; v1 estimate was 2.3 dB low). Lexicon 224XL Bright Hall '
        '(true stereo): more air and sheen than bus/ir_hall - vocal-like leads, e-piano, glassy pads. '
        + _use('hall', 'bus/ir_hall_bright'),
        predelay=20, gain=-4.7)
_return('bus/ir_hall_dark', _xl(_XL + '03-dark-hall'),
        'v2 (measured: bus/hall level +0.3 / -0.5 dB; v1 estimate was 1.7 dB low). Lexicon 224XL Dark Hall (true '
        'stereo): a big warm hall that stays behind the mix - dreamwave pads, slow strings, ambient washes. '
        + _use('hall', 'bus/ir_hall_dark'),
        predelay=25, gain=-4.3)

# ------------------------------------------------------------------------------------------------ plates

_return('bus/ir_plate', _xl(_XL + '13-cd-plate-a'),
        "v1. Lexicon 224XL Constant Density Plate A (true stereo, RT60 ~1.5 s): the 80s snare / vocal plate - "
        "instantly dense, bright, even, no flutter. 10 ms pre-delay, wet high-passed at 250 Hz. Snare -12..-16, "
        "claps, e-piano -12..-16, stabs. " + _use('plate', 'bus/ir_plate'),
        predelay=10, lowcut=250, gain=-8.5)
_return('bus/ir_plate_b', _xl(_XL + '12-cd-plate-b'),
        'v1. Lexicon 224XL Constant Density Plate B (true stereo, RT60 ~1.5 s): heavier, more low-mid body than '
        'bus/ir_plate. ' + _use('plate', 'bus/ir_plate_b'),
        predelay=10, lowcut=250, gain=-7.5)
_return('bus/ir_plate_short', _xl(_XL + '12-cd-plate-b', 2),
        'v1. Lexicon 224XL CD Plate B, short variation (true stereo, RT60 ~0.6 s): a tight plate for busy parts - '
        'snare and clap on fast tempos, plucks, arps. ' + _use('plate', 'bus/ir_plate_short'),
        predelay=5, lowcut=300, gain=-7.0)
_return('bus/ir_plate_rich', _xl(_XL + '14-rich-plate', 2),   # (the pack has no V1.2: variation 1 is not true stereo)
        'v2 (measured: as bus/ir_plate, about 8 dB under bus/plate v2: see the module notes). Lexicon 224XL Rich '
        'Plate (true stereo): a lush, long plate for ballads and big snares. '
        + _use('plate', 'bus/ir_plate_rich'),
        predelay=10, lowcut=250, gain=-8.5)
_return('bus/ir_plate_small', _xl(_XL + '11-small-plate'),
        'v2 (measured: as bus/ir_plate, ~8 dB under bus/plate v2). Lexicon 224XL Small Plate (true stereo): short and '
        'bright. ' + _use('plate', 'bus/ir_plate_small'),
        predelay=5, lowcut=300, gain=-7.1)

# ---------------------------------------------------------------------------------------------- chambers

_return('bus/ir_chamber', _xl(_XL + '06-chamber'),
        'v1. Lexicon 224XL Chamber (true stereo, RT60 ~2.1 s, soft onset around 10-30 ms): warm, round and deep '
        'without the size of a hall - keys, e-piano, pads, strings, the whole mix in a jazz or soul setting. '
        + _use('chamber', 'bus/ir_chamber'),
        predelay=5, gain=-6.5)
_return('bus/ir_chamber_rich', _xl(_XL + '08-rich-chamber'),
        'v2 (measured: bus/hall level +0.5 / -0.6 dB). Lexicon 224XL Rich Chamber (true stereo): a denser, longer '
        'chamber. ' + _use('chamber', 'bus/ir_chamber_rich'),
        predelay=5, gain=-6.8)
_return('bus/ir_chamber_dark', _xl(_XL + '07-dark-chamber'),
        'v2 (measured: bus/hall level +0.7 / -0.8 dB; v1 estimate was 1.9 dB hot). Lexicon 224XL Dark Chamber (true '
        'stereo): a chamber that stays out of the top end. ' + _use('chamber', 'bus/ir_chamber_dark'),
        predelay=5, gain=-7.9)

# ------------------------------------------------------------------------------------------------- rooms

_return('bus/ir_room', _xl(_XL + '04-room', 3),
        'v1. Lexicon 224XL Room, variation 3 (true stereo, RT60 ~0.7 s, then a quiet long tail): a medium live room - '
        'drums, guitars, keys, a band in one space; keeps things close. ' + _use('room', 'bus/ir_room'),
        predelay=0, lowcut=180, gain=-7.0)
_return('bus/ir_room_big', _xl(_XL + '04-room', 1),
        'v1. Lexicon 224XL Room, variation 1 (true stereo, RT60 ~1.4 s): a big room / small hall. '
        + _use('room', 'bus/ir_room_big'),
        predelay=5, gain=-6.5)
_return('bus/ir_ambience', _xl(_XL + '04-room', 4),
        'v2. Lexicon 224XL Room, variation 4 (true stereo, RT60 ~0.3 s; widened 1.5: from a centred source the '
        'preset is narrow): short bright ambience - adds size and stereo to dry drums, snares, claps and rhythm '
        'guitars without an audible tail. ' + _use('ambience', 'bus/ir_ambience'),
        predelay=0, lowcut=200, width=1.5, gain=-12.5)
_return('bus/ir_room_small', _xl(_XL + '05-small-room'),
        'v2 (measured: bus/hall level +0.3 / -0.7 dB; v1 estimate was 2.8 dB low). Lexicon 224XL Small Room (true '
        'stereo). ' + _use('room', 'bus/ir_room_small'),
        predelay=0, lowcut=200, gain=-4.7, length=3.0)   # (the V1 files run 43.7 s: silence / noise after the tail)
_return('bus/ir_inverse', _xl(_XL + '09-inverse-room', 2),
        "v1. Lexicon 224XL Inverse Room, variation 2 (true stereo): the reverb swells up over ~200 ms and drops - the "
        "80s 'reverse' / non-linear snare and tom sound, also for stabs. Send the snare (-8..-12) and cut the send "
        "for everything else. " + _use('inverse', 'bus/ir_inverse'),
        predelay=0, lowcut=250, gain=-7.5)

# ------------------------------------------------------------------ Voxengo IM Reverbs (modelled real spaces)

_VOX = 'voxengo-im-reverbs'
_return('bus/ir_hall_large', _files(_VOX, 'Large Long Echo Hall.wav'),
        'v1. A large concert hall (Voxengo IM Reverbs, stereo, RT60 ~3.5 s like bus/hall): long, open and bright, '
        'distinct early reflections before a smooth, steady tail - orchestral pads, strings, cinematic swells, big '
        'ballad keys. ' + _use('hall', 'bus/ir_hall_large'),
        predelay=10, lowcut=220, highcut=12000, gain=-4.5)
_return('bus/ir_concert_hall', _files(_VOX, 'Musikvereinsaal.wav'),
        "v1. The Vienna Musikverein's golden hall (Voxengo IM Reverbs, modelled, stereo, RT60 ~1.5 s, first "
        "reflections at 20 ms; widened 1.5: the recording is narrow): warm, clear, close - strings, piano, classical "
        "and jazz ensembles. " + _use('hall', 'bus/ir_concert_hall'),
        predelay=0, lowcut=180, highcut=12000, width=1.5, gain=-5.0)
_return('bus/ir_church', _files(_VOX, 'St Nicolaes Church.wav'),
        'v1. A stone church (Voxengo IM Reverbs, stereo, RT60 ~3.6 s): huge, reverent and bright - choirs, '
        'organ, solo piano or strings, ambient intros. Keep the sends low (-12..-18) and the tempo slow; it rings '
        'for ~5 s, so give the song a long enough tail (Song(..., tail=6)): the render does not lengthen it. '
        + _use('church', 'bus/ir_church'),
        predelay=15, lowcut=200, highcut=11000, gain=-4.5)
_return('bus/ir_opera', _files(_VOX, 'Scala Milan Opera Hall.wav'),
        'v1. La Scala opera house (Voxengo IM Reverbs, modelled, stereo, RT60 ~1.0 s; widened 1.5): a dry, clear '
        'theatre space - vocal-like leads, piano, acoustic ensembles. ' + _use('hall', 'bus/ir_opera'),
        predelay=5, lowcut=180, highcut=12000, width=1.5, gain=-5.0)
_return('bus/ir_salon', _files(_VOX, 'French 18th Century Salon.wav'),
        'v1. An 18th-century salon (Voxengo IM Reverbs, stereo, RT60 ~0.8 s): an intimate wooden room - jazz trio, '
        'chamber music, upright piano, brushes. ' + _use('room', 'bus/ir_salon'),
        predelay=0, lowcut=160, highcut=12000, gain=-6.5)
_return('bus/ir_drum_room', _files(_VOX, 'Nice Drum Room.wav'),
        'v1. A live drum room (Voxengo IM Reverbs, stereo, RT60 ~0.6 s): room sound for dry kits - send the kit '
        '(-10..-14) or use it as a parallel room mic. ' + _use('room', 'bus/ir_drum_room'),
        predelay=0, lowcut=150, highcut=12000, gain=-9.5)

# ---------------------------------------------------------------------------------------------- cabinets


# The amp of each cabinet patch (the engine's 'amp': cascaded triode preamp stages, the TMB tone stack, a sagging
# push-pull power amp - engine/fx/AmpFx.cpp) and its use. Measured on FSBS / Emily DI power chords and palm-muted
# chugs (songs/the-drummer-speaks/ROCK.md): the old single tube waveshaper per cab gave a fizzy, hollow (even-
# harmonic), mid-scooped rhythm tone that had to be filtered back; the cascade gives the odd-harmonic crunch, the
# tone stack the mids. 'output' levels each amp so the chain keeps the DI's loudness (within ~0.5 LU on a power-chord
# riff at velocity 105).
AMPS = {
    'clean': dict(stages=1, gain=1.5, bright=4.0, tight=70.0, bass=5.0, mid=4.0, treble=6.5, stack='american',
                  presence=6.0, resonance=5.0, master=3.0, sag=0.2),
    'blues': dict(stages=2, gain=3.5, bright=3.0, tight=80.0, bass=5.0, mid=6.0, treble=6.0, presence=6.0,
                  resonance=5.5, master=5.0, sag=0.45),
    'crunch': dict(stages=2, gain=5.0, bright=2.0, tight=100.0, bass=5.0, mid=6.5, treble=5.5, presence=5.5,
                   resonance=5.5, master=6.0, sag=0.35),
    'rock': dict(stages=2, gain=6.0, bright=2.5, tight=90.0, bass=5.5, mid=7.0, treble=6.0, presence=6.0,
                 resonance=6.0, master=7.0, sag=0.4),
    'metal': dict(stages=4, gain=7.0, boost=8.0, bright=2.0, tight=130.0, bass=6.0, mid=3.5, treble=6.5, presence=6.5,
                  resonance=6.5, master=5.0, sag=0.15),
    'lead': dict(stages=3, gain=7.0, boost=6.0, bright=3.0, tight=110.0, bass=5.0, mid=7.0, treble=7.0, presence=8.0,
                 resonance=6.0, master=4.0, sag=0.3),
}
AMP_OUTPUT = {'clean': 5.6, 'blues': 6.2, 'crunch': 4.7, 'rock': 5.7, 'metal': 5.4, 'lead': 4.4}
CABS = {'clean': 'cab/clean_1x12', 'blues': 'cab/blues_1x12', 'crunch': 'cab/crunch_2x12', 'rock': 'cab/rock_4x12',
        'metal': 'cab/metal_4x12', 'lead': 'cab/rock_4x12'}


def _cab(name: str, ir, notes: str, *, kind: str, lp: float, gain: float):
    register(Patch(name, fx=[
        fx.amp(**AMPS[kind], output=AMP_OUTPUT[kind], name='amp'),
        fx.convolver(ir=ir, mix=1.0, gain=gain),
        fx.eq({'hp.freq': 70, 'lp.freq': lp, 'lp.slope': 24}, name='mic'),
    ], notes=_with_pack_note(notes, ir) + (
        f" Insert chain for a DI (direct, un-amped) electric guitar: s.track('gtr', <guitar>, "
        f"fx=patches.get('{name}').fx) - or agentsound.patches.sampled_guitars.amp('{kind}', gain=...) (any amp voicing "
        f"into any cab). The 'amp' effect is the head: .but_fx('amp', gain=..., mid=..., presence=...); the convolver is "
        f"the speaker cabinet and mic, 'mic' its roll-off.")))


_cab('cab/clean_1x12', _files('overdriven-uk-112-stealth-65-ssp1-v1-2', 'SSP1/DYN-57/OD-UK112-ST65-DYN-57-P10-30.wav'),
     'v2. Clean combo: a one-stage Fender-style amp just breaking up (gain 1.5, american stack) into a 1x12 with a '
     'Jensen Tornado Stealth 65 (SM57): round, full, soft top - jazz, funk, clean arpeggios, 80s chorus guitars.',
     kind='clean', lp=8000, gain=-8.0)
_cab('cab/blues_1x12', _files('overdriven-112-celestion-h30-tubepreamp2-v1-2',
                              'TubePreamp2/DYN-57/OD-O112-H30-DYN-57-P05-30.wav'),
     'v2. Edge-of-breakup British combo: a two-stage amp at gain 3.5 with a spongy supply (sag 0.45) into a 1x12 '
     'Celestion G12H30 (SM57): blues, indie, rhythm crunch that cleans up with a softer pick.',
     kind='blues', lp=7000, gain=-4.5)
_cab('cab/crunch_2x12', _files('overdriven-calif-212-v30-kt88-ssp1-v1-1', 'SSP1/DYN-57/OD-R212-V30-DYN-57-P10-00.wav'),
     'v2. Crunch: a two-stage British amp at gain 5, mids forward, the power amp joining in, into a 2x12 Celestion '
     'Vintage 30 (SM57): classic rock rhythm, power chords, 80s rock.',
     kind='crunch', lp=6000, gain=-3.5)
_cab('cab/rock_4x12', _files('jester-emerald-ir-pack', 'Impulses/48kHz/1_Nacho_Guacamole_48.wav'),
     'v2. Plexi-style rock: a cranked two-stage Plexi (gain 6, master 7: the power amp saturates, mids 7) into a '
     'Marshall 1960AX 4x12 with Celestion Greenbacks (SM57, Jester Emerald pack, CC0): big, woody, the 70s-80s rock '
     'stack - riffs, leads, solos.',
     kind='rock', lp=6000, gain=-5.5)
_cab('cab/metal_4x12', _files('kalthallen-cabs-free', 'Kalthallen IRs/001a-SM57-V30-4x12.wav'),
     'v2. High gain: a Tube Screamer boost (8 dB) and a tight input (130 Hz) into a four-stage modern preamp (gain '
     '7, scooped mids 3.5) and a 4x12 Celestion Vintage 30 (SM57, Kalthallen): modern rock and metal rhythm.',
     kind='metal', lp=6000, gain=-7.5)
