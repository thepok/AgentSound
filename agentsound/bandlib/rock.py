"""Rock band presets: a live band in a room - sampled acoustic kits with their microphone mix, DI guitars through
amp + cabinet chains (double-tracked hard left / right), picked / fingered electric basses with drive, organ or
piano, drum room, plate and a lead delay. recipes/rock.md ('Band presets') shows how to play them.

  rock_band     drums, bass, gtr_l, gtr_r, lead, keys     classic / arena / hard rock (profile rock)
  indie_band    drums, bass, gtr_l, gtr_r, lead, keys     indie / garage / alt rock: clean + crunch (profile rock)
  power_ballad  drums, bass, piano, strings, pad, lead    80s power ballad (profile rock)

The guitars are DI (direct, un-amped) sample sets played through an amp chain in the track (amp()): a bright shelf
(the bright cap / treble booster) -> eq -> saturator (the amp) -> convolver (the speaker cabinet IR) -> eq (the cab
patches of agentsound/patches/space_ir.py) -> a scooped tone stack. The DI sets are level-matched into the amp
(DI_LEVEL). Every DI guitar here is a keyswitched instrument (di_guitar()): 'open' (default), 'palm mute' (a short
thumping note that keeps its pick attack: the chug) and 'dead note' (real muted-string scratches from Emilyguitar),
switched per note with clip.articulate('palm', ...) / 'dead'. The shared helpers (di_guitar, amp, the kit key remap,
the pack checks, master_chain) are used by agentsound/bandlib/pop.py as well.
"""

from __future__ import annotations

import copy

from .. import bands, library
from ..bands import Band
from ..patches import FX, Instrument, fx, inst
from ..patches import fx as _fx
from .. import patches as _patches
from ..theory import ComposeError

# ------------------------------------------------------------------------------------------------ helpers


def installed(pack: str) -> bool:
    """True when sample pack `pack` is installed (its SOURCE.json exists)."""
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


def require(preset: str, role: str, *packs: str) -> None:
    """ComposeError naming the fetch command when one of `packs` is missing."""
    for p in packs:
        if not installed(p):
            raise ComposeError(f"band {preset!r}: the {role} needs the sample pack {p!r}, which is not installed: "
                               f"python -m agentsound samples fetch {p} (or pass sounds={{{role!r}: ...}}, or "
                               f"without=({role!r},))")


# DI guitar articulations: zone overrides on top of the plain (open) notes. A palm mute is the picking hand resting
# on the strings at the bridge: the note loses its upper harmonics and dies within a few hundred ms - into a
# distorted amp that is the tight 'chug' (the pick attack stays: 1.6 kHz, not a muffled 900 Hz). A dead note
# (fretting hand muting) is a percussive scratch with little pitch: real muted-string samples where a set has them
# (real_dead_notes), else this filtered blip.
GUITAR_ARTICULATIONS = {
    'palm mute': {'filter': 'lpf_2p', 'cutoff': 1600.0, 'resonance': 3.0, 'filKeytrack': 40.0, 'filKeycenter': 52,
                  'decay': 0.55, 'sustain': 0.0, 'release': 0.05, 'gain': 2.0},
    'dead note': {'filter': 'bpf_2p', 'cutoff': 1600.0, 'resonance': 0.0, 'decay': 0.07, 'sustain': 0.0,
                  'release': 0.02, 'gain': -3.0},
}


# Bass articulations the same way: a staccato is the fretting hand lifting - the sustained sample, damped fast
# (the growlybass 'vicious' staccato samples start with a clipped full-scale thump, so they are not used).
BASS_ARTICULATIONS = {
    'staccato': {'decay': 0.5, 'sustain': 0.25, 'release': 0.03, 'filter': 'lpf_2p', 'cutoff': 2400.0,
                 'resonance': 0.0, 'gain': 1.0},
    'mute': {'filter': 'lpf_2p', 'cutoff': 700.0, 'resonance': 2.0, 'decay': 0.3, 'sustain': 0.0, 'release': 0.03,
             'gain': 2.0},
}


def articulated(path: str, table: dict, *, base: str = 'open', level: float = 0.0, **params) -> Instrument:
    """One sample set as a keyswitched sampler: `base` (the default, the file as recorded) + one articulation per
    `table` entry {name: zone overrides (envelope, filter, gain dB added)}, keyswitch keys 0, 1, 2 ... (C-1 up, below
    any note). Reads the .sfz now (a missing pack is a ComposeError naming it)."""
    progs = {base: path}
    for a in table:
        progs[a] = path
    ins = inst.sfz_multi(progs, keyswitch=0, level=level, **params)
    keys = ins.info['sfz']['keyswitches']
    by_key = {keys[a]: over for a, over in table.items()}
    for z in ins.params['samples']:
        over = by_key.get(z.get('swLast'))
        if not over or z.get('trigger') in ('release', 'release_key'):
            continue
        for k, v in over.items():
            if k == 'gain':
                z['gain'] = round(z.get('gain', 0.0) + v, 4)
            else:
                z[k] = v
    return ins


def di_guitar(path: str, *, articulations=('palm mute', 'dead note'), level: float = 0.0, **params) -> Instrument:
    """A DI guitar sample set as one keyswitched sampler: 'open' (the default) + GUITAR_ARTICULATIONS
    ('palm mute', 'dead note'): clip.articulate('palm', span=...) / .articulate('dead', where=...). Keyswitch keys
    0, 1, 2 (C-1..D-1, below any note). Reads the .sfz now (a missing pack is a ComposeError naming it).
    Dead notes are REAL muted-string scratches when the set has them (Emilyguitar: noises/muted1-5, 5 round robins)
    or Emilyguitar is installed (borrowed for the other DI sets); only without it they are the filtered short note."""
    for a in articulations:
        if a not in GUITAR_ARTICULATIONS:
            raise ComposeError(f"di_guitar: unknown articulation {a!r}; known: {', '.join(GUITAR_ARTICULATIONS)}")
    ins = articulated(path, {a: GUITAR_ARTICULATIONS[a] for a in articulations},
                      level=level + DI_LEVEL.get(path, 0.0), **params)
    if 'dead note' in articulations:
        real_dead_notes(ins, ins.info['sfz']['keyswitches']['dead note'], ins.info['sfz']['keyswitches']['open'],
                        donor_gain=DI_LEVEL[EMILY] - DI_LEVEL.get(path, 0.0))
    return ins


# Input level of each DI set into the amp (dB, instrument level): the sets are recorded at very different levels
# (FSBS ~13 dB hotter than Emilyguitar / Shinyguitar), and a saturator's drive depends on its input level - without
# this an Emily 'crunch' is nearly clean and dull. Measured: open power chords at velocity 105 -> ~-8 LUFS DI each.
DI_LEVEL = {
    'samples/freepats-fsbs-direct/EGuitarFSBS-direct bridge 20220911.sfz': 4.0,
    'samples/karoryfer-emilyguitar/emily_basic.sfz': 12.5,
    'samples/karoryfer-shinyguitar/Programs/electric_one.sfz': 12.5,
}


# the real muted-string scratches of Emilyguitar (keys 91-95 of emily_basic.sfz), relative to the notes' level
DEAD_NOTE_GAIN = -6.0


def _muted_zones(ins: Instrument, open_key: int) -> list:
    return [z for z in ins.params['samples']
            if z.get('swLast', open_key) == open_key and z.get('trigger') not in ('release', 'release_key')
            and '/noises/muted' in str(z.get('file', '')).replace('\\', '/')]


def real_dead_notes(ins: Instrument, dead_key: int, open_key: int = 0, *, donor_gain: float = 0.0) -> bool:
    """Replace the synthetic 'dead note' zones of a keyswitched DI guitar (in place) by real muted-string scratches:
    the set's own (Emilyguitar noises/muted1-5) or, for another DI set, Emilyguitar's when it is installed. The five
    scratch sets are spread over the playing range low -> high (each played within ~5 semitones of its recording,
    round robins kept; borrowed ones get `donor_gain` dB: the two sets' level difference). False (unchanged) when
    none are available."""
    zones = ins.params['samples']
    muted = _muted_zones(ins, open_key)
    if not muted and installed(_pack_of(EMILY)):
        donor = inst.sfz(EMILY)
        donor.expand()
        muted = [dict(z, swLast=open_key, gain=round(z.get('gain', 0.0) + donor_gain, 4))
                 for z in donor.params['samples'] if z.get('trigger') not in ('release', 'release_key')
                 and '/noises/muted' in str(z.get('file', '')).replace('\\', '/')]
    if not muted:
        return False
    notes = [z for z in zones if z.get('swLast') == dead_key and z.get('trigger') not in ('release', 'release_key')
             and z.get('hi', 127) < min(z2['lo'] for z2 in muted) - 1]
    if not notes:
        return False
    lo = min(z.get('lo', 0) for z in notes)
    hi = max(z.get('hi', 127) for z in notes)
    ids = {id(z) for z in notes}
    zones[:] = [z for z in zones if id(z) not in ids]
    by_key: dict = {}
    for z in muted:
        by_key.setdefault(z['lo'], []).append(z)
    keys = sorted(by_key)
    span = (hi - lo + 1) / len(keys)
    for i, k in enumerate(keys):
        b_lo = lo + round(i * span)
        b_hi = lo + round((i + 1) * span) - 1 if i < len(keys) - 1 else hi
        centre = (b_lo + b_hi) // 2
        for z in by_key[k]:
            c = copy.deepcopy(z)
            c.update(lo=b_lo, hi=b_hi, root=centre, swLast=dead_key)
            c['gain'] = round(c.get('gain', 0.0) + DEAD_NOTE_GAIN, 4)
            zones.append(c)
    return True


def remap_keys(ins: Instrument, copies: dict) -> Instrument:
    """Copy the zones of drum keys onto other keys (in place): {48: 47} makes key 48 play what key 47 plays (same
    pitch: the root moves with the key). Fills the GM keys a kit's own map leaves empty (tom_hi 48, crash2 57 ...);
    an existing zone on the target key is replaced."""
    ins.expand()
    zones = ins.params['samples']
    for dst in copies:
        zones[:] = [z for z in zones if not (z.get('lo', 0) == dst and z.get('hi', 127) == dst)]
    extra = []
    for dst, src in copies.items():
        for z in zones:
            if z.get('lo', 0) <= src <= z.get('hi', 127) and z.get('lo') == z.get('hi') == src:
                c = copy.deepcopy(z)
                c['lo'] = c['hi'] = dst
                root = c.get('root', 60)
                if isinstance(root, int):
                    c['root'] = root + (dst - src)
                extra.append(c)
    zones.extend(extra)
    return ins


def layer(*instruments: Instrument, gains=None, pans=None) -> Instrument:
    """One sampler playing several sampled instruments at once (their zones merged; groups renumbered so they do not
    cut each other off): layer(trumpets, trombones, gains=[0, -3], pans=[-0.3, 0.3]) (pans: zone positions, e.g. a
    section spread across the stage)."""
    out = None
    offset = 0
    for i, ins in enumerate(instruments):
        ins = Instrument.coerce(ins).expand()
        if ins.type != 'sampler':
            raise ComposeError(f"layer(): only sampler instruments can be layered, got {ins.type!r}")
        g = (gains or [0.0] * len(instruments))[i]
        zones = copy.deepcopy(ins.params['samples'])
        top = 0
        for z in zones:
            for k in ('group', 'offBy'):
                if z.get(k):
                    top = max(top, z[k])
                    z[k] = z[k] + offset
            if g:
                z['gain'] = round(z.get('gain', 0.0) + g, 4)
            if pans is not None:
                z['pan'] = max(-1.0, min(1.0, z.get('pan', 0.0) + pans[i]))
        offset += top
        if out is None:
            out = ins._carry(Instrument('sampler', {**copy.deepcopy(ins.params), 'samples': zones}))
        else:
            out.params['samples'].extend(zones)
    return out


class Builder:
    """Shared plumbing of the presets: roles, overrides (sounds / ids / without), buses reused when the song has
    them already."""

    def __init__(self, song, preset: str, *, without=(), sounds=None, ids=None, analysis=None, notes=''):
        self.s = song
        self.preset = preset
        self.without = set(without or ())
        self.sounds = dict(sounds or {})
        self.ids = dict(ids or {})
        self.band = Band(song, preset, notes=notes, analysis=analysis)

    def want(self, role: str) -> bool:
        return role not in self.without

    def track(self, role: str, default, *, fx=(), trim=0.0, pan=None, output='master', sends=None,
              humanize=None, groove=None):
        """Add the role's track (None when it is left out). `default` is a callable returning the sound: it runs
        only when no override is given, so a missing pack of a replaced role does not matter. `trim` (dB) is the
        preset's balance: a last 'utility' effect named 'trim' (fx.trim.gain), so the track fader (gain_db,
        'gainDb' automation) stays 0 dB for the song."""
        if not self.want(role):
            return None
        snd = self.sounds[role] if role in self.sounds else default()
        chain = list(fx) + [_fx.utility(gain=round(trim, 2), name='trim')]
        t = self.s.track(self.ids.get(role, role), snd, fx=chain, pan=pan, output=output,
                         sends={k: v for k, v in (sends or {}).items() if k is not None} or None)
        if humanize:
            t.humanize(*humanize[:2], seed=humanize[2] if len(humanize) > 2 else None)
        if groove:
            t.groove(groove)
        return self.band.add(role, t)

    def bus(self, name: str, chain, **kw):
        """A return / group bus: the song's own when it has one of that id already."""
        b = self.s.buses.get(name)
        if b is None:
            b = self.s.bus(name, chain, **kw)
        return self.band.bus(name, b)


def master_chain(band: Band, *effects) -> bool:
    """Set the song's master chain to `effects` - only when it has none yet: a song that set its own master (or a
    second preset on the same song) keeps the first chain instead of stacking two limiters. band.info['master'] says
    which happened ('set' / 'kept')."""
    if band.song.master.fx:
        band.info['master'] = 'kept'
        return False
    band.song.master.add(*effects)
    band.info['master'] = 'set'
    return True


def lib_patch(name: str, **params):
    """A library patch without its default sends (the preset sets its own), params to its instrument."""
    p = _patches.get(name)
    p = p.with_mix(sends={k: None for k in p.sends})
    return p.but(**params) if params else p


def _patch_sound(name: str, **params):
    """The instrument of a library patch (its calibrated level, no sends / fx)."""
    p = _patches.get(name)
    ins = p.instrument
    return ins.but(**params) if params else ins


def _chain(name: str, **fx_params) -> list:
    """A copy of a library chain patch's effects; fx_params = {fx type: {param: value}}."""
    p = _patches.get(name)
    for t, ps in fx_params.items():
        p = p.but_fx(t, **ps)
    return [f.copy() for f in p.fx]


def _eq(**bands) -> FX:
    return fx.eq({k.replace('__', '.'): v for k, v in bands.items()})


# ------------------------------------------------------------------------------------------------ sounds
# Every sound is a function (called only when used) returning an instrument; the first installed choice wins.

BIG_RUSTY = 'samples/big-rusty-drums/Programs/01-full.sfz'
RED_ZEPPELIN = 'samples/avl-red-zeppelin/Red_Zeppelin_2023_repack.sfz'
UNRULY = 'samples/karoryfer-unruly-drums/Programs/01-kit-sticks.sfz'
FSBS_DI = 'samples/freepats-fsbs-direct/EGuitarFSBS-direct bridge 20220911.sfz'
FSBS_CLEAN = 'samples/freepats-fsbs-clean/EGuitarFSBS-clean bridge 20260807.sfz'
EMILY = 'samples/karoryfer-emilyguitar/emily_basic.sfz'
SHINY = 'samples/karoryfer-shinyguitar/Programs/electric_one.sfz'
GROWLY = 'samples/karoryfer-growlybass/growlybass_dirty.sfz'
FASHION = 'samples/karoryfer-fashionbass/fashionbass.sfz'
ROCK_ORGAN = 'samples/freepats-rock-organ/RockOrganEmulation-20190715.sfz'
COMBO_ORGAN = 'samples/karoryfer-caveman-cosmonaut/Programs/main.sfz'


def _pack_of(path: str) -> str:
    return path.split('/')[1]


def rock_kit(which: str = 'big_rusty', level: float = 0.0) -> Instrument:
    """A GM-mapped acoustic rock kit: 'big_rusty' (Karoryfer Big Rusty Drums: 80s kit, 14 layers x 4 round robins,
    close + overhead mics, CC0), 'unruly' (Karoryfer Unruly Drums: sticks, CC0), 'red_zeppelin' (AVL Ludwig,
    CC-BY-SA) - falling back in that order, then sampled/forzee_kit (Hydrogen, GPL) and the GeneralUser 'Rock' kit.
    Toms: 41 floor, 43, 45, 47 + copies on 48 / 50 (tom_hi / tom_high); 36 kick, 38 snare, 37 side stick, 40 rimshot,
    42 / 44 / 46 hats, 49 crash, 51 ride, 53 bell."""
    order = {'big_rusty': [BIG_RUSTY, UNRULY, RED_ZEPPELIN], 'unruly': [UNRULY, BIG_RUSTY, RED_ZEPPELIN],
             'red_zeppelin': [RED_ZEPPELIN, BIG_RUSTY, UNRULY]}[which]
    for path in order:
        if not installed(_pack_of(path)):
            continue
        if path == BIG_RUSTY:
            ins = inst.sfz(path, level=level + 1.0, mics={'oh': -2.0, 'top': 0.0, 'btm': -4.0})
            return remap_keys(ins, {48: 47, 50: 47, 57: 49, 59: 51})
        if path == UNRULY:
            # close kick mics up, overheads down (the default mic mix smears the kick wide: low-end correlation 0.5)
            # and a little close hat mic: a centred, punchier - but still small, dry, garage - kit (20" kick with
            # snare wires: little below 60 Hz)
            ins = inst.sfz(path, level=level + 1.0, cc={80: 60, 70: 127, 71: 127, 72: 10, 32: 60, 42: 60, 52: 60})
            return remap_keys(ins, {48: 47, 50: 47, 57: 49, 59: 51})
        return inst.sfz(path, level=level + 2.0)
    if installed('hydrogen-forzee-stereo'):
        return _patch_sound('sampled/forzee_kit').but(level=level)
    return inst.sf2('Power', level=level)


def _first(*paths) -> str | None:
    for p in paths:
        if installed(_pack_of(p)):
            return p
    return None


def guitar_di(preferred: str, preset: str, role: str, level: float = 0.0, **params) -> Instrument:
    """DI guitar with palm mute / dead note articulations: `preferred` first, then the other DI set."""
    path = _first(preferred, EMILY if preferred != EMILY else FSBS_DI, FSBS_DI)
    if path is None:
        require(preset, role, _pack_of(preferred))
    return di_guitar(path, level=level, **params)


def rock_bass(preset: str, style: str = 'pick', level: float = 0.0) -> Instrument:
    """Electric bass: 'pick' / 'finger' = Karoryfer Growlybass (Squier Jazz, CC0); 'round' = Karoryfer Fashionbass
    (roundwounds, 5 layers) - both keyswitched with 'staccato' and 'mute' (BASS_ARTICULATIONS); fallback FreePats
    finger bass (SoundFont), then GeneralUser 'Pick Bass' / 'Finger Bass'."""
    if style in ('pick', 'finger') and installed('karoryfer-growlybass'):
        # the file sounds an octave below its keys: transpose=12 makes written E1 sound E1
        return articulated(GROWLY, BASS_ARTICULATIONS, base='sustain', transpose=12,
                           level=level + (2.0 if style == 'pick' else 0.0))
    if installed('karoryfer-fashionbass'):
        return articulated(FASHION, BASS_ARTICULATIONS, base='sustain', level=level + 1.0)
    if installed('freepats-fingerbass-yr-sf2'):
        return inst.sf2(file=library.SAMPLES.joinpath('freepats-fingerbass-yr-sf2', 'FingerBassYR 20190930.sf2')
                        .as_posix(), level=level)
    return inst.sf2('Pick Bass' if style == 'pick' else 'Finger Bass', level=level)


def organ(kind: str = 'rock', level: float = 0.0) -> Instrument:
    """Hammond-style tonewheel organ (FreePats rock organ, setBfree rendering, CC0) or the 70s combo organ
    (Karoryfer Caveman Cosmonaut); fallback GeneralUser 'Rock Organ'."""
    if kind == 'combo' and installed('karoryfer-caveman-cosmonaut'):
        return inst.sfz(COMBO_ORGAN, level=level)
    if installed('freepats-rock-organ'):
        return inst.sfz(ROCK_ORGAN, level=level - 2.0)
    return inst.sf2('Rock Organ', level=level)


def piano(level: float = 0.0) -> Instrument:
    """Salamander Grand V3 (sampled/grand_piano, CC-BY: credit Alexander Holm); fallback GeneralUser 'Grand Piano'."""
    if installed('salamander-grand'):
        ins = _patch_sound('sampled/grand_piano')
        return ins.but(level=ins.params.get('level', 0.0) + level)
    return inst.sf2('Grand Piano', width=1.6, level=level + 6.0)


# ------------------------------------------------------------------------------------------------ amp chains


# per amp kind: (bright: pre-amp treble shelf dB at freq, tone stack after the cab: low 120 Hz, low-mid 450 Hz,
# presence 3 kHz). A DI guitar straight into saturator + cab IR is dull and boxy (measured on FSBS power chords:
# lowmid 32 %, presence 5 % of the energy; the FreePats FSBS 'dist' sets - the same guitar through a real amp rack -
# have lowmid 12 %, presence 16-19 %): the bright cap / treble booster before the drive and the scooped tone stack
# after it give the amp its bite (FSBS 'rock': lowmid 8 %, presence 12 %).
_VOICING = {'clean': (6.0, 2200.0, 1.0, -3.0, 2.0), 'blues': (8.0, 1800.0, 2.0, -3.0, 2.0),
            'crunch': (10.0, 1800.0, 3.0, -4.0, 3.0), 'rock': (8.0, 1800.0, 3.0, -4.0, 3.0),
            'metal': (6.0, 1800.0, 3.0, -4.0, 3.0), 'lead': (6.0, 1800.0, 1.0, -3.0, 2.0)}


def amp(kind: str, *, drive: float | None = None, tone: float | None = None, bright: float | None = None) -> list:
    """Amp + cabinet insert chain for a DI guitar: a bright shelf (the amp's bright cap / a treble booster, `bright`
    dB), the cab/* chain of agentsound/patches/space_ir.py (eq -> saturator = the amp, `drive` / `tone` -> convolver =
    the speaker cabinet IR -> eq) and a tone stack eq named 'tonestack' (bass, scooped low mids, presence): 'clean'
    (cab/clean_1x12), 'blues' (cab/blues_1x12), 'crunch' (cab/crunch_2x12), 'rock' (cab/rock_4x12, Marshall
    Greenbacks), 'metal' (cab/metal_4x12), 'lead' (cab/rock_4x12 driven harder, mids pushed)."""
    name = {'clean': 'cab/clean_1x12', 'blues': 'cab/blues_1x12', 'crunch': 'cab/crunch_2x12',
            'rock': 'cab/rock_4x12', 'metal': 'cab/metal_4x12', 'lead': 'cab/rock_4x12'}[kind]
    sat = {}
    if kind == 'lead':
        sat = {'drive': 27.0, 'tone': 2.0}
    if drive is not None:
        sat['drive'] = drive
    if tone is not None:
        sat['tone'] = tone
    b_db, b_f, lo, scoop, pres = _VOICING[kind]
    if bright is not None:
        b_db = bright
    pre = [fx.eq({'high.freq': b_f, 'high.gain': b_db}, name='bright')] if b_db else []
    stack = fx.eq({'low.freq': 120, 'low.gain': lo, 'peak1.freq': 450, 'peak1.gain': scoop, 'peak1.q': 0.8,
                   'peak3.freq': 3000, 'peak3.gain': pres, 'peak3.q': 0.9}, name='tonestack')
    return pre + _chain(name, **({'saturator': sat} if sat else {})) + [stack]


# ------------------------------------------------------------------------------------------------ presets

ROCK_NOTES = """\
How to play it (rock_band; recipe recipes/rock.md):
  drums   drums({...}) grids, GM keys (36 kick, 38 snare, 40 rimshot, 37 side stick, 42/44/46 hats, 49 crash, 51 ride,
          53 bell, toms 50/48 high .. 45 .. 43 .. 41 floor). Velocity 70-127 (14 layers: ghosts at 30-50). Humanized
          5 ms / +-8 already; change the pattern every 4-8 bars, tom_fill() into sections, crash() on downbeats.
  bass    E1-E3 roots in 8ths locked to the kick, velocity 90-115; clip.articulate('staccato', ...) for short punchy
          notes (the sustained samples damped fast), 'mute' for thuds. Picked tone with a tube drive in the chain;
          it ducks 5 dB under the kick.
  gtr_l / gtr_r   the double-tracked rhythm wall (hard left / right, two different guitars and amps). Play the SAME
          part on both (power chords: clip.chordify('power') on roots E2-A3, or 2-3 note voicings), each strummed
          (clip.strum(ms=8..14, bpm=s.tempo), 'alternate' for 8ths) - the tracks' humanize seeds differ, so they are
          two takes. Palm-muted chugs: clip.articulate('palm', span=(a, b)) (short notes, velocity 90-110); open
          chords ring in the chorus; muted scratches (real samples): articulate('dead'). The balance puts each ~4 dB
          under the lead; gain='high' = metal 4x12 + a hotter crunch (level-matched). Velocity 85-115.
  lead    the melody / solo, G3-E6, mono legato: overlapping notes slur (art.legato(clip)), clip.glide(120, where=
          art.leaps(3)) slides, art.vibrato(b.lead, clip, at, depth=25, rate=5.5) on long notes, bends by automating
          'instrument.pitchbend' (+1 / +2 st). Echo (dotted 8th) + plate sends are set; automate 'send.echo' for throws.
  keys    organ (Leslie-style tremolo; automate 'fx.tremolo.rate' 0.9 -> 6.4 Hz for the fast rotor) pads and
          stabs C3-C5 under the guitars, or keys='piano' (8th-note chords C3-C5).
Levels: each role's balance is its last effect (fx.trim.gain), the faders (gain_db, 'gainDb' automation) are yours:
use them for loud-quiet dynamics (per_section({verse: -4, chorus: 0})): the master glues only above -12 dB, so a
lighter verse stays lighter. Dry track LUFS on the demo: drums -20.5, bass -22, each rhythm guitar -23.5, lead
-19.5, keys -26. Master -9.6 LUFS (verse -9.7, chorus -8.5), true peak -1.2 dBTP (profile rock)."""


def rock_band(song, *, without=(), sounds=None, ids=None, keys: str = 'organ', gain: str = 'crunch',
              kit: str = 'big_rusty') -> Band:
    """Classic / arena rock band. keys='organ'|'piano'; gain='crunch' (70s-80s Plexi / 2x12 crunch) | 'high' (tighter,
    more saturated: 90s-00s); kit='big_rusty'|'unruly'|'red_zeppelin'."""
    if keys not in ('organ', 'piano'):
        raise ComposeError(f"rock_band: keys must be 'organ' or 'piano', got {keys!r}")
    if gain not in ('crunch', 'high'):
        raise ComposeError(f"rock_band: gain must be 'crunch' or 'high', got {gain!r}")
    b = Builder(song, 'rock_band', without=without, sounds=sounds, ids=ids, analysis={'profile': 'rock'},
                notes=ROCK_NOTES)
    s = song
    room = b.bus('room', _patches.get('bus/ir_drum_room').fx if installed('voxengo-im-reverbs')
                 else [fx.reverb(type='room', mix=1.0, decay=0.8, size=0.4, predelay=4, lowcut=180, highcut=9000)])
    plate = b.bus('plate', _patches.get('bus/ir_plate').fx if installed('little-devil-224xl-13-cd-plate-a')
                  else _patches.get('bus/plate').fx)
    echo = b.bus('echo', [fx.delay(mode='pingpong', balanced='off', time=0.75, feedback=0.28, mix=1.0,
                                   highcut=4200, lowcut=300, wow=0.15, duck=0.35),
                          _eq(hp__freq=250, lp__freq=6000)])
    drum_bus = b.bus('drum_bus', [
        fx.compressor(threshold=-22, ratio=4, attack=12, release=90, knee=6, mix=0.45, automakeup='on', keyhp=60),
        fx.saturator(mode='tape', drive=3, mix=0.6),
        _eq(hp__freq=28, peak1__freq=380, peak1__gain=-1.5, peak1__q=0.9, high__freq=10000, high__gain=1.0)])

    b.track('drums', lambda: rock_kit(kit), output=drum_bus, trim=4.0,
            fx=[_eq(low__freq=70, low__gain=1.5, peak1__freq=420, peak1__gain=-2.0, peak1__q=1.0,
                    peak2__freq=150, peak2__gain=-2.5, peak2__q=1.0, peak3__freq=4500, peak3__gain=1.0, peak3__q=0.8)],
            sends={room: -5, plate: -20}, humanize=(5, 8, 3))
    b.track('bass', lambda: rock_bass('rock_band', 'pick'), trim=-3.0, pan=0.0,
            fx=[_eq(hp__freq=35, peak1__freq=250, peak1__gain=-2.0, peak1__q=0.9, peak2__freq=900, peak2__gain=2.5,
                    peak2__q=1.1, peak3__freq=60, peak3__gain=-2.5, peak3__q=1.2, low__freq=110, low__gain=1.5),
                fx.saturator(mode='tube', drive=10, mix=0.55, tone=1.0),
                fx.compressor(threshold=-22, ratio=4, attack=15, release=140, knee=6, automakeup='on'),
                _eq(lp__freq=5500)],
            sends={room: -24}, humanize=(4, 6, 5))
    hi = gain == 'high'
    b.track('gtr_l', lambda: guitar_di(FSBS_DI, 'rock_band', 'gtr_l'), pan=-0.95,
            trim=-3.8 if hi else -7.0,
            fx=amp('metal' if hi else 'rock') + [_eq(hp__freq=100, peak1__freq=250, peak1__gain=-1.5,
                                                     high__freq=9000, high__gain=-2.0)],
            sends={room: -13}, humanize=(7, 9, 11))
    b.track('gtr_r', lambda: guitar_di(EMILY, 'rock_band', 'gtr_r'), pan=0.95,
            trim=-4.4 if hi else -5.5,
            fx=amp('crunch', drive=24 if hi else 17) + [_eq(hp__freq=100, peak1__freq=250, peak1__gain=-1.5,
                                                            high__freq=9000, high__gain=-2.0)],
            sends={room: -13}, humanize=(7, 9, 23))
    b.track('lead', lambda: guitar_di(FSBS_DI, 'rock_band', 'lead', articulations=(), mono='legato',
                                      legatotime=30, glideshape='fast'),
            pan=0.0, trim=-7.3,
            fx=amp('lead') + [fx.compressor(threshold=-24, ratio=3, attack=8, release=120, automakeup='on'),
                              _eq(peak1__freq=300, peak1__gain=-2.0, peak2__freq=1700, peak2__gain=1.0,
                                  peak3__freq=4300, peak3__gain=-2.0, lp__freq=7500)],
            sends={echo: -9, plate: -11, room: -16}, humanize=(4, 6, 31))
    if keys == 'organ':
        b.track('keys', lambda: organ('rock'), pan=0.3, trim=-10.0,
                fx=[fx.saturator(mode='tube', drive=8, mix=0.7),
                    fx.tremolo(rate=6.2, depth=0.18, stereo=60), fx.width(width=0.7),
                    _eq(hp__freq=110, peak1__freq=450, peak1__gain=-2.0, lp__freq=8000)],
                sends={room: -10, plate: -16}, humanize=(4, 5, 41))
    else:
        b.track('keys', piano, pan=0.25, trim=-5.0,
                fx=[_eq(hp__freq=120, peak1__freq=300, peak1__gain=-2.5, peak3__freq=3000, peak3__gain=1.0)],
                sends={room: -14, plate: -18}, humanize=(5, 6, 41))
    if b.band.roles.get('bass') is not None and b.band.roles.get('drums') is not None:
        # the bass breathes 5 dB under the kick: kick and bass share 60-120 Hz without masking (a short duck, not
        # audible as pumping)
        s.sidechain(b.band.roles['bass'], key=b.band.roles['drums'], pitches='kick', depth=5, attack=2, release=100)
    master_chain(b.band,
                 _eq(hp__freq=25, peak1__freq=300, peak1__gain=-1.0, peak1__q=0.8, high__freq=11000,
                     high__gain=2.5),
                 fx.compressor(threshold=-12, ratio=2, attack=30, release=250, knee=8, detector='rms', keyhp=100,
                               automakeup='on'),
                 fx.tape(speed='15', drive=1.0, bump=1.0, wow=0.05, flutter=0.05),
                 fx.width(width=1.12, monobass=150),
                 fx.limiter(gain=7.0, ceiling=-1.2, release=60))
    return b.band


bands.register('rock_band', rock_band, genre='rock',
               roles=('drums', 'bass', 'gtr_l', 'gtr_r', 'lead', 'keys'),
               description='classic / arena rock: Big Rusty kit (close + OH mics) in a drum room, picked Growlybass '
                           'with tube drive, double-tracked DI guitars (FSBS Strat -> Marshall 4x12 L, Emily SG -> '
                           '2x12 V30 R, level-matched amps with bright cap + tone stack) with palm mute / real dead '
                           'note articulations, a lead guitar (legato, delay + plate), Leslie organ or piano',
               tuned='profile rock: songs/_bands/rock_band -9.6 LUFS, LRA 4.8, width 26 %, no warnings',
               requires=('freepats-fsbs-direct', 'karoryfer-emilyguitar'))


# ------------------------------------------------------------------------------------------------ indie

WURLI = 'samples/greg-sullivan-epianos/Wurlitzer EP200/Wurlitzer EP200.sfz'
DRAWBAR = 'samples/freepats-drawbar-organ/DrawbarOrganEmulation-20190712.sfz'


def wurlitzer(level: float = 0.0) -> Instrument:
    """Wurlitzer EP200 (Greg Sullivan, 4 layers, CC-BY 3.0: credit Greg Sullivan); fallback the Lithalean
    Wurlitzer (sampled/wurlitzer), then GeneralUser 'Tine Electric Piano'."""
    if installed('greg-sullivan-epianos'):
        return inst.sfz(WURLI, level=level + 2.0)
    if installed('lithalean-wurlitzer'):
        ins = _patch_sound('sampled/wurlitzer')
        return ins.but(level=ins.params.get('level', 0.0) + level)
    return inst.sf2('Tine Electric Piano', level=level)


INDIE_NOTES = """\
How to play it (indie_band; recipe recipes/rock.md, indie / garage / alt):
  drums   drums({...}) grids, GM keys (Big Rusty; kit='unruly' = the small dry garage kit, thin below 60 Hz; toms
          50/48/45/43/41). Driving 8ths with open hats, floor-tom grooves; velocity 60-120, ghost notes 30-50.
  bass    Fashionbass (roundwounds, 5 layers): 8th roots with octave jumps, melodic runs, E1-E3, velocity 80-115.
  gtr_l   the clean / jangly guitar (FSBS single-coil DI -> clean 1x12, compressor, chorus, 1.3 kHz honk cut):
          arpeggios (clip.arpeggiate('up', rate='1/8')), sus2 / add9 open voicings in G3-E5, 16th strums
          (clip.strum(ms=10, bpm=s.tempo, direction='alternate')), dead-note scratches (articulate('dead')).
  gtr_r   the crunch guitar (Emily SG DI -> edge-of-breakup 1x12 Celestion H30): power chords / octaves in the
          chorus, palm-muted 8ths in the verse (articulate('palm')). Hard right; gtr_l hard left: different parts are
          fine (indie = two interlocking guitars), or double one.
  lead    octave melodies (clip.octave_double(12)) or single lines, G3-A5, on the Karoryfer Shinyguitar archtop
          (pickup, cc100=0) through a blues amp with slapback + plate; polyphonic (octaves, double stops), vibrato
          with art.vibrato(b.lead, clip, at).
  keys    Wurlitzer EP200 through a small amp with tremolo (keys='wurli') or a drawbar organ (keys='organ'):
          offbeat chords / pads C3-C5.
Levels (fx.trim holds the balance, the faders are yours; dry LUFS on the demo): drums -20.5, bass -23, gtr_l -22.5,
gtr_r -22.5, lead -19.5, keys -26. Master -9.6 LUFS."""


def indie_band(song, *, without=(), sounds=None, ids=None, keys: str = 'wurli', kit: str = 'big_rusty') -> Band:
    """Indie / garage / alt rock band: a clean jangle guitar left (the Fender-style FSBS), a crunch guitar right (the
    Emily SG), Karoryfer kit and bass, a Shinyguitar lead with slapback, Wurlitzer or organ; a tight live room (224XL
    room) and a short plate. keys='wurli'|'organ'; kit='big_rusty' (default: the full low end) | 'unruly' (the small
    dry garage kit: a 20" kick with snare wires, thin below 60 Hz - pair it with a fuller bass) | 'red_zeppelin'."""
    if keys not in ('wurli', 'organ'):
        raise ComposeError(f"indie_band: keys must be 'wurli' or 'organ', got {keys!r}")
    b = Builder(song, 'indie_band', without=without, sounds=sounds, ids=ids, analysis={'profile': 'rock'},
                notes=INDIE_NOTES)
    s = song
    room = b.bus('room', _patches.get('bus/ir_room').fx if installed('little-devil-224xl-04-room')
                 else [fx.reverb(type='room', mix=1.0, decay=0.9, size=0.45, predelay=6, lowcut=180, highcut=9000)])
    plate = b.bus('plate', _patches.get('bus/ir_plate').fx if installed('little-devil-224xl-13-cd-plate-a')
                  else _patches.get('bus/plate').fx)
    slap = b.bus('slap', [fx.delay(mode='mono', sync='off', timems=110, feedback=0.12, mix=1.0,
                                   highcut=3800, lowcut=300, wow=0.2),
                          _eq(hp__freq=250)])
    drum_bus = b.bus('drum_bus', [
        fx.compressor(threshold=-22, ratio=3, attack=15, release=100, knee=6, mix=0.4, automakeup='on', keyhp=60),
        fx.saturator(mode='tape', drive=4, mix=0.5),
        _eq(hp__freq=30, peak1__freq=400, peak1__gain=-1.5, high__freq=10000, high__gain=1.5)])
    b.track('drums', lambda: rock_kit(kit), output=drum_bus, trim=1.5,
            fx=[_eq(low__freq=60, low__gain=-2.0, peak1__freq=450, peak1__gain=-2.0, peak3__freq=5000,
                    peak3__gain=1.0)],
            sends={room: -6, plate: -22}, humanize=(6, 9, 4))
    b.track('bass', lambda: rock_bass('indie_band', 'round'), trim=-3.0,
            fx=[_eq(hp__freq=32, low__freq=70, low__gain=2.5, peak1__freq=220, peak1__gain=-2.0, peak2__freq=1100,
                    peak2__gain=2.0),
                fx.saturator(mode='tube', drive=6, mix=0.4),
                fx.compressor(threshold=-22, ratio=4, attack=12, release=140, knee=6, automakeup='on'),
                _eq(lp__freq=6000)],
            sends={room: -24}, humanize=(5, 7, 6))
    b.track('gtr_l', lambda: guitar_di(FSBS_DI, 'indie_band', 'gtr_l'), pan=-0.9, trim=-4.8,
            fx=amp('clean', drive=3) + [fx.compressor(threshold=-26, ratio=4, attack=5, release=120,
                                                     automakeup='on'),
                                       fx.chorus(mode='I', mix=0.3),
                                       # the jangle lives in the sparkle, not in 1-2 kHz (honk)
                                       _eq(hp__freq=120, peak1__freq=300, peak1__gain=-2.0, peak2__freq=1300,
                                           peak2__gain=-3.0, peak2__q=0.8, peak3__freq=4000, peak3__gain=1.0,
                                           high__freq=8000, high__gain=1.5)],
            sends={room: -12, plate: -18}, humanize=(7, 9, 12))
    b.track('gtr_r', lambda: guitar_di(EMILY, 'indie_band', 'gtr_r'), pan=0.9, trim=-6.0,
            fx=amp('blues', drive=13) + [_eq(hp__freq=100, peak1__freq=280, peak1__gain=-1.5, peak2__freq=1300,
                                              peak2__gain=-3.0, peak2__q=0.8, high__freq=9000, high__gain=-1.0)],
            sends={room: -12, plate: -22}, humanize=(7, 9, 24))

    def shiny():
        if installed('karoryfer-shinyguitar'):
            return inst.sfz(SHINY, cc={100: 0}, level=DI_LEVEL[SHINY])
        return guitar_di(EMILY, 'indie_band', 'lead', articulations=())
    b.track('lead', shiny, trim=-7.0,
            fx=amp('blues', drive=10, bright=3.0) + [
                fx.compressor(threshold=-24, ratio=3, attack=8, release=120, automakeup='on'),
                _eq(hp__freq=150, peak1__freq=350, peak1__gain=-2.0, peak2__freq=2000, peak2__gain=1.0, peak2__q=1.0,
                    peak3__freq=4000, peak3__gain=-3.0, peak3__q=0.8)],
            sends={slap: -10, plate: -14, room: -18}, humanize=(4, 6, 32))
    if keys == 'wurli':
        b.track('keys', wurlitzer, pan=0.3, trim=-2.0,
                fx=[fx.saturator(mode='tube', drive=7, mix=0.6), fx.tremolo(rate=5.2, depth=0.22, stereo=30),
                    _eq(hp__freq=140, peak1__freq=350, peak1__gain=-2.0, high__freq=7000, high__gain=-1.5)],
                sends={room: -12, plate: -16}, humanize=(5, 6, 42))
    else:
        b.track('keys', lambda: inst.sfz(DRAWBAR, level=-2.0) if installed('freepats-drawbar-organ')
                else organ('rock'), pan=0.3, trim=-9.0,
                fx=[fx.saturator(mode='tube', drive=6, mix=0.6), fx.tremolo(rate=6.0, depth=0.15, stereo=40),
                    fx.width(width=0.8), _eq(hp__freq=140, peak1__freq=450, peak1__gain=-2.0, lp__freq=8000)],
                sends={room: -12, plate: -18}, humanize=(4, 5, 42))
    if b.band.roles.get('bass') is not None and b.band.roles.get('drums') is not None:
        s.sidechain(b.band.roles['bass'], key=b.band.roles['drums'], pitches='kick', depth=3, attack=2, release=110)
    master_chain(b.band,
                 _eq(hp__freq=25, peak1__freq=320, peak1__gain=-1.0, peak1__q=0.8, high__freq=11000,
                     high__gain=2.5),
                 fx.compressor(threshold=-16, ratio=2, attack=30, release=250, knee=8, detector='rms', keyhp=100,
                               automakeup='on'),
                 fx.tape(speed='15', drive=2.0, bump=1.5, wow=0.08, flutter=0.06),
                 fx.width(width=1.15, monobass=150),
                 fx.limiter(gain=7.8, ceiling=-1.2, release=70))
    return b.band


bands.register('indie_band', indie_band, genre='rock',
               roles=('drums', 'bass', 'gtr_l', 'gtr_r', 'lead', 'keys'),
               description='indie / garage / alt rock: Big Rusty (or the dry Unruly garage) kit in a 224XL room, '
                           'Fashionbass, a clean jangle guitar (FSBS -> clean 1x12 + chorus) left and a crunch '
                           'guitar (Emily SG -> 1x12 H30) right, a Shinyguitar archtop lead with slapback, '
                           'Wurlitzer or organ',
               tuned='profile rock: songs/_bands/indie_band -9.6 LUFS, LRA 3.9, width 30 %, no warnings',
               requires=('freepats-fsbs-direct', 'karoryfer-emilyguitar'))


# ------------------------------------------------------------------------------------------------ power ballad

BALLAD_NOTES = """\
How to play it (power_ballad; recipes/rock.md + recipes/pop.md 'Pop ballad'):
  piano   the song's bed: broken chords / 8th arpeggios in the verse (C3-C5, velocity 60-95), block chords in the
          chorus; automate 'instrument.pedal' (1 down, 0 up at each chord change: [(t, 0, 'step'), (t + 0.05, 1,
          'step')]).
  strings sampled string section (VPO, sustain): whole-bar chords C3-C5 from the 2nd verse on, octaves in the last
          chorus; automate 'gainDb' swells (the preset's balance sits in fx 'trim', the fader is yours).
  pad     80s Juno pad (synthwave/juno_pad) under the chorus, register C3-C5.
  drums   enters in the 2nd verse or the chorus: half-time or slow 8ths (kick 1 + 3, snare 2 + 4 at velocity
          110-127: the kit is sent to a big 224XL rich plate), tom fills, crash on section downbeats.
  bass    fingered roots in quarter / half notes, E1-E3, velocity 80-105.
  lead    the melody / guitar solo, G3-E6: long notes with vibrato (art.vibrato(b.lead, clip, at, depth=30)),
          slides (clip.glide), bends (automate 'instrument.pitchbend'); a quarter-note echo and the hall are set.
Levels (fx.trim holds the balance, the faders are yours; dry LUFS on the demo): piano -23, strings -24.5, pad -27.5,
drums -22 (-20 while playing), bass -23.5, lead -22. Master -10 LUFS."""


def power_ballad(song, *, without=(), sounds=None, ids=None, kit: str = 'big_rusty') -> Band:
    """80s power ballad: grand piano, string section, Juno pad, a big-room kit with a huge plate, fingered bass and
    a singing lead guitar (DI -> Marshall 4x12, long echo, hall)."""
    b = Builder(song, 'power_ballad', without=without, sounds=sounds, ids=ids, analysis={'profile': 'rock'},
                notes=BALLAD_NOTES)
    s = song
    room = b.bus('room', _patches.get('bus/ir_room_big').fx if installed('little-devil-224xl-04-room')
                 else [fx.reverb(type='room', mix=1.0, decay=1.4, size=0.6, predelay=8, lowcut=200)])
    plate = b.bus('plate', _patches.get('bus/ir_plate_rich').fx if installed('little-devil-224xl-14-rich-plate')
                  else _patches.get('bus/plate').fx)
    hall = b.bus('hall', _patches.get('bus/ir_hall').fx if installed('little-devil-224xl-01-concert-hall')
                 else _patches.get('bus/hall').fx)
    echo = b.bus('echo', [fx.delay(mode='pingpong', balanced='off', time=1.0, feedback=0.32, mix=1.0,
                                   highcut=4000, lowcut=300, wow=0.2, duck=0.4),
                          _eq(hp__freq=250, lp__freq=6000)])
    drum_bus = b.bus('drum_bus', [
        fx.compressor(threshold=-22, ratio=4, attack=20, release=150, knee=6, mix=0.45, automakeup='on', keyhp=60),
        fx.saturator(mode='tape', drive=3, mix=0.5),
        _eq(hp__freq=30, peak1__freq=400, peak1__gain=-2.0, high__freq=10000, high__gain=1.0)])
    b.track('piano', lambda: piano().but(width=0.9), pan=0.0, trim=-3.5,
            fx=[_eq(hp__freq=80, peak1__freq=320, peak1__gain=-4.5, peak1__q=0.8, peak3__freq=3500,
                    peak3__gain=1.0, high__freq=6000, high__gain=2.5),
                fx.compressor(threshold=-24, ratio=2, attack=20, release=200, automakeup='on')],
            sends={hall: -15, plate: -22}, humanize=(6, 6, 51))

    def strings():
        if installed('vpo-scripts-standard') and installed('vpo-wav'):
            return lib_patch('sampled/strings')
        return lib_patch('gm/strings')
    b.track('strings', strings, pan=0.0, trim=-6.5,
            fx=[_eq(hp__freq=110, peak1__freq=300, peak1__gain=-2.0, peak2__freq=1300, peak2__gain=-3.5, peak2__q=0.8,
                    high__freq=7000, high__gain=2.5),
                fx.width(width=1.4)],
            sends={hall: -6}, humanize=(8, 5, 52))
    b.track('pad', lambda: lib_patch('synthwave/juno_pad'), trim=-8.0,
            fx=[_eq(hp__freq=200, peak1__freq=400, peak1__gain=-2.0)],
            sends={hall: -8})
    b.track('drums', lambda: rock_kit(kit), output=drum_bus, trim=3.5,
            fx=[_eq(low__freq=70, low__gain=2.0, peak1__freq=420, peak1__gain=-2.5, peak3__freq=5000,
                    peak3__gain=1.0, high__freq=9000, high__gain=1.5)],
            sends={room: -6, plate: -12}, humanize=(5, 7, 53))
    b.track('bass', lambda: rock_bass('power_ballad', 'finger'), trim=-1.0,
            fx=[_eq(hp__freq=32, low__freq=60, low__gain=-2.0, peak1__freq=240, peak1__gain=-2.0,
                    peak2__freq=800, peak2__gain=1.5, peak3__freq=110, peak3__gain=1.5, peak3__q=1.0),
                fx.saturator(mode='tube', drive=4, mix=0.35),
                fx.compressor(threshold=-22, ratio=4, attack=20, release=180, knee=6, automakeup='on'),
                _eq(lp__freq=4500)],
            sends={room: -26}, humanize=(5, 6, 54))
    b.track('lead', lambda: guitar_di(FSBS_DI, 'power_ballad', 'lead', articulations=(), mono='legato',
                                      legatotime=40, glideshape='ease'),
            trim=-5.8,
            fx=amp('lead', drive=24) + [fx.compressor(threshold=-24, ratio=3, attack=10, release=150,
                                                     automakeup='on'),
                                       _eq(peak1__freq=300, peak1__gain=-2.0, peak2__freq=1200, peak2__gain=-4.5,
                                           peak2__q=0.7,
                                           peak3__freq=4300, peak3__gain=-2.0, lp__freq=7000)],
            sends={echo: -9, hall: -10, plate: -18}, humanize=(4, 6, 55))
    if b.band.roles.get('bass') is not None and b.band.roles.get('drums') is not None:
        s.sidechain(b.band.roles['bass'], key=b.band.roles['drums'], pitches='kick', depth=6, attack=2, release=160)
    master_chain(b.band,
                 _eq(hp__freq=25, peak1__freq=320, peak1__gain=-1.5, peak1__q=0.8, peak2__freq=1100,
                     peak2__gain=-1.0, peak2__q=0.6, high__freq=10000, high__gain=2.5),
                 fx.compressor(threshold=-16, ratio=1.8, attack=30, release=300, knee=8, detector='rms', keyhp=100,
                               automakeup='on'),
                 fx.tape(speed='15', drive=1.0, bump=1.0, wow=0.05, flutter=0.05),
                 fx.width(width=1.05, monobass=150),
                 fx.limiter(gain=9.0, ceiling=-1.2, release=120))
    return b.band


bands.register('power_ballad', power_ballad, genre='rock',
               roles=('piano', 'strings', 'pad', 'drums', 'bass', 'lead'),
               description='80s power ballad: Salamander grand, VPO string section, Juno pad, Big Rusty kit in a big '
                           'room with a 224XL rich plate, fingered Growlybass, a singing lead guitar (FSBS DI -> '
                           'Marshall 4x12, quarter echo, 224XL hall)',
               tuned='profile rock: songs/_bands/power_ballad -10 LUFS, LRA 4.4, width 32 %, no warnings',
               requires=('freepats-fsbs-direct',))
