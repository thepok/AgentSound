"""Synthwave band presets: outrun, dreamwave, darksynth, retrowave, scifi.

    from agentsound import bands
    b = bands.outrun(s)                        # drums bass pad keys arp lead + returns, sidechains, master
    b.lead.play(hook, chorus); b.bass.loop(prog.bass('octave', rate='1/8'), verse, chorus)
    ANALYSIS = {'profile': 'synthwave'}        # = b.analysis (the profile the preset is calibrated for)

Each preset is one call that sets up a finished-sounding ensemble on a Song: the instruments (sampled drum machines
and the library's lush synth patches), their mix chains (eq, compression, saturation, width), pans and faders, the
return buses (Lexicon 224XL IR halls / plates where they beat the algorithmic ones, echoes, shimmer, the keyed gated
snare), the kick sidechain pump and the master chain. Every preset was calibrated on its demo song
(songs/_bands/<preset>/song.py) against a reference record with `python -m agentsound compare`, loudness-matched:
the final numbers are in each band's notes (band.notes) and in recipes/synthwave.md ('Band presets').

Common options (agentsound/bands.py): without=('arp', ...), sounds={'lead': 'synthwave/sync_lead'} (replaces the
sound, keeps the role's chain, fader, pan and sends), ids={'drums': 'kit'}. Preset options are listed per preset.
Missing sample packs fall back to the library's synthesized equivalents (band.info['fallbacks'] names what was
replaced and the pack that brings the sampled sound back); nothing here needs a pack at import time.

A bus the song already has under a preset's bus id ('hall', 'plate', 'echo', ...) is used as it is (the preset does
not replace it); new buses get the preset's calibrated chains.
"""

from __future__ import annotations

from .. import bands, library, patches
from ..modulation import sample_hold
from ..patches import Instrument, Patch, fx, inst
from ..theory import ComposeError

VERSION = 3  # v3: lead='piano' on every preset (the defaults render exactly as v2).
#   v2 (review): hall returns narrowed under the wide masters (pad-only intros kept at correlation >= 0),
#   dreamwave master width 1.5 -> 1.4, retrowave lead='supersaw' without the presence lift, scifi bells +3 dB / 808 hats -4 dB

_LINN = 'hyperreal-linndrum'
_909 = 'hyperreal-tr909'
_TIDAL = 'tidal-drum-machines'
_POP80 = 'sampleradar-80s-pop-drums'
_ESS = 'sampleradar-essential-drumkit'
_XL_HALL = 'little-devil-224xl-01-concert-hall'
_XL_DARK = 'little-devil-224xl-03-dark-hall'
_XL_PLATE = 'little-devil-224xl-13-cd-plate-a'
_CMI = 'fairlight-cmi-library-1-3'
_GRAND = 'salamander-grand'


def _have(*packs: str) -> bool:
    return all((library.SAMPLES / p / 'SOURCE.json').is_file() for p in packs)


def _s(pack: str, rel: str) -> str:
    return f'samples/{pack}/{rel}'


def _raw(name: str) -> Instrument:
    """The instrument of a library patch without its chain (the role's chain processes it instead)."""
    return patches.get(name).instrument


# ------------------------------------------------------------------------------------------ the builder


class _Role:
    """One role of a preset: its default sound (or `alt` when the sound's packs are missing) and its mix chain:
    insert fx after the sound's own (pre_fx: in front of the sound's own - drive before its chorus / doubler), fader,
    pan, sends, kick-sidechain depth, movement (modulators)."""

    def __init__(self, sound, *, alt=None, packs=(), gain: float = 0.0, pan=None, fx=(), sends=None,
                 duck: float | None = None, release: float | None = None, mods=(), pre_fx=()):
        self.sound, self.alt, self.packs = sound, alt, tuple(packs)
        self.gain, self.pan, self.fx = float(gain), pan, list(fx)
        self.pre_fx = list(pre_fx)
        self.sends = dict(sends or {})
        self.duck, self.release = duck, release
        self.mods = list(mods)          # (target, modulator) pairs applied to the track


def _as_patch(sound, role: str) -> Patch:
    if isinstance(sound, Patch):
        p = sound.copy()
    elif isinstance(sound, str):
        p = patches.get(sound)
    elif isinstance(sound, (Instrument, dict)):
        p = Patch(f'band/{role}', instrument=sound)
    else:
        raise ComposeError(f"band role {role!r}: a sound is a patch name, a Patch or an instrument (inst.*(...)), "
                           f"got {sound!r}")
    if p.instrument is None:
        raise ComposeError(f"band role {role!r}: {p.name!r} is an fx chain, not an instrument")
    return p.with_mix(sends={k: None for k in p.sends})   # the role's sends replace the patch's own


def _assemble(song, preset: str, roles: dict, *, returns: dict, master, analysis: dict, notes: str, without=(),
              sounds=None, ids=None, gate_pitches=('snare', 'clap'), key_role: str = 'drums', info=None):
    """Build the band: the returns the active roles use, the tracks, the keyed gated reverb, the kick pump and the
    master chain."""
    without, sounds, ids = set(without or ()), dict(sounds or {}), dict(ids or {})
    band = bands.Band(song, preset, notes, analysis)
    band.info.update(info or {})
    fallbacks, used_packs = {}, set()
    active = {r: spec for r, spec in roles.items() if r not in without}
    used = {b for spec in active.values() for b in spec.sends}
    for bid, (chain, gain) in returns.items():
        if bid not in used:
            continue
        if bid in song.buses:
            band.bus(bid, song.buses[bid])
        else:
            band.bus(bid, song.bus(bid, patches.get(chain) if isinstance(chain, str) else chain, gain_db=gain))
    for role, spec in active.items():
        if role in sounds:
            sound = sounds[role]
        elif spec.packs and not _have(*spec.packs):
            missing = [p for p in spec.packs if not _have(p)]
            if spec.alt is None:
                raise ComposeError(f"band {preset!r}: role {role!r} needs the sample pack(s) {', '.join(missing)}: "
                                   f"python -m agentsound samples fetch {' '.join(missing)}")
            sound = spec.alt
            fallbacks[role] = missing
        else:
            sound = spec.sound
            used_packs.update(spec.packs)
        sound = sound() if callable(sound) else sound
        t = song.track(ids.get(role, role), _as_patch(sound, role), fx=[f.copy() for f in spec.fx],
                       pre=[f.copy() for f in spec.pre_fx], gain_db=spec.gain, pan=spec.pan,
                       sends={band.buses[b]: db for b, db in spec.sends.items() if b in band.buses})
        if role not in sounds:                      # movement written for the default sound's params
            for target, mod in spec.mods:
                t.modulate(target, mod)
        band.add(role, t)
    kit = band.roles.get(key_role)
    if kit is not None:
        if 'gated' in band.buses:
            song.gated(band.buses['gated'].id, key=kit, pitches=list(gate_pitches))
        pump: dict = {}
        for role, spec in active.items():
            if spec.duck and role != key_role:
                pump.setdefault((spec.duck, spec.release or 180), []).append(band.roles[role])
        for (depth, release), targets in pump.items():
            song.sidechain(*targets, key=kit, pitches='kick', depth=depth, release=release)
    if master is not None:
        song.master.use(master)
    band.info['fallbacks'] = fallbacks
    band.info['packs'] = sorted(used_packs)
    if fallbacks:
        band.notes = (band.notes.rstrip() + '\nFallbacks (sample packs missing): ' + '; '.join(
            f"{r} -> synthesized (python -m agentsound samples fetch {' '.join(ps)})" for r, ps in fallbacks.items()))
    return band


# ------------------------------------------------------------------------------------------ shared chains


def _kit_chain(*, thr=-14.0, ratio=3.0, attack=12.0, drive=5.0, out=0.0, lowmid=-2.0, air=1.5, lp=16000.0,
               low=0.0):
    """Drum-machine glue: rumble high-pass, low shelf, low-mid dip, air, 80s console compression, tape soft clip."""
    return [fx.eq({'hp.freq': 30, 'hp.slope': 24, 'low.freq': 70, 'low.gain': low, 'peak1.freq': 380,
                   'peak1.gain': lowmid, 'peak1.q': 0.9, 'high.freq': 9000, 'high.gain': air, 'lp.freq': lp}),
            fx.compressor(threshold=thr, ratio=ratio, attack=attack, release=90, knee=6),
            fx.saturator(mode='tape', drive=drive, output=out)]


def _bass_chain(*, low=0.0, mud=-1.5, hp=32.0, mud_freq=260.0):
    """Bass: clean sub high-pass, low shelf, a low-mid dip, then mono (the whole bass sits in the centre)."""
    return [fx.eq({'hp.freq': hp, 'hp.slope': 24, 'low.freq': 90, 'low.gain': low, 'peak1.freq': mud_freq,
                   'peak1.gain': mud, 'peak1.q': 1.0}),
            fx.utility(mono='on')]


def _tame(*, hp=150.0, lowmid=0.0, presence=0.0, top=0.0, lp=20000.0):
    """Keep a synth out of the bass and the harsh band: high-pass, low-mid, 3.5 kHz and top shelf trims."""
    return fx.eq({'hp.freq': hp, 'peak1.freq': 350, 'peak1.gain': lowmid, 'peak1.q': 0.8,
                  'peak3.freq': 3500, 'peak3.gain': presence, 'peak3.q': 0.9, 'high.freq': 8000, 'high.gain': top,
                  'lp.freq': lp})


def _hall(dark: bool = False, width: float | None = None):
    """The Lexicon 224XL concert / dark hall (IR) when installed, else the algorithmic lush hall. width narrows the
    return (the halls are decorrelated, ~105 % side/mid: under a wide master a pad-only intro reads correlation < 0)."""
    if dark:
        name = 'bus/ir_hall_dark' if _have(_XL_DARK) else 'bus/hall_lush'
    else:
        name = 'bus/ir_hall' if _have(_XL_HALL) else 'bus/hall'
    return (name if width is None else patches.get(name).with_fx(fx.width(width=width)), 0.0)


# lead='piano' per preset: fader, the role chain on top of the patch's own (hp 210, body dip, presence + air,
# compressor, chorus + dimension), sends. Calibrated on each demo's chorus / drop / peak with the hook an octave up
# and octave-doubled (hook.clip(octave=5, vel=105).octave_double(-12, vel=0.8)) vs the preset's reference: the piano's
# integrated loudness at or above the synth lead's, every band within 2.6 dB of the synth-lead numbers, no new
# warnings. The melody an octave higher puts its fundamentals in the 0.7-2 kHz band: outrun / dreamwave get a mid dip
# there; darksynth and retrowave take the patch as it is; the dark scifi mix gets body (+2.5 dB at 450 Hz), less top.
_PIANO = {
    'outrun': dict(gain=1.5, fx=(fx.eq({'peak2.freq': 1100, 'peak2.gain': -2.5, 'peak2.q': 0.7, 'peak3.freq': 4000,
                                        'peak3.gain': 2.0, 'peak3.q': 0.8}),),
                   sends={'plate': -12, 'hall': -12, 'echo': -14}),
    'dreamwave': dict(gain=3.5, fx=(fx.eq({'peak2.freq': 700, 'peak2.gain': -2.0, 'peak2.q': 1.0}),),
                      sends={'plate': -12, 'hall': -8, 'echo': -14}),
    'darksynth': dict(gain=-1.0, fx=(), sends={'plate': -12, 'hall': -10, 'echo': -14}),
    'retrowave': dict(gain=-1.0, fx=(), sends={'plate': -12, 'hall': -12, 'echo': -14}),
    'scifi': dict(gain=2.0, fx=(fx.eq({'peak1.freq': 450, 'peak1.gain': 2.5, 'peak1.q': 0.9, 'peak3.freq': 3000,
                                       'peak3.gain': -3.0, 'peak3.q': 0.6, 'high.freq': 8000, 'high.gain': -2.0}),),
                  sends={'plate': -12, 'hall': -6, 'echo': -12}),
}


def _piano(preset: str) -> '_Role':
    """lead='piano': the sampled melody piano (sampled/piano_lead: Salamander Grand, mono centre, compressed,
    chorused; gm/piano_lead, GeneralUser's bright grand, without the pack) with the preset's role chain on top."""
    return _Role('sampled/piano_lead', alt='gm/piano_lead', packs=(_GRAND,), **_PIANO[preset])


def _plate():
    """The 224XL constant-density plate A (IR) when installed, else the algorithmic 80s EMT plate. The IR plates
    return ~8 dB less than bus/plate at the same send (measured, agentsound/patches/space_ir.py v3): the bus gets
    +7 dB so the preset sends mean the same on both."""
    return ('bus/ir_plate', 7.0) if _have(_XL_PLATE) else ('bus/plate_80s', 0.0)


# ------------------------------------------------------------------------------------------ kits


def _linn_909_kit() -> Instrument:
    """LinnDrum LM-2 with the TR-909's long, punchy kick (BT3AADA) and, when the tidal pack is there, the Simmons
    SDS-5 toms: the Kavinsky / outrun machine."""
    m = {'kick': _s(_909, 'BT3AADA.WAV'), 'kick2': _s(_LINN, 'kick.wav')}
    if _have(_TIDAL):
        sds = 'machines/SimmonsSDS5'
        m.update({'tom_lo': _s(_TIDAL, f'{sds}/simmonssds5-lt/Tom-10.wav'),
                  'tom_mid': _s(_TIDAL, f'{sds}/simmonssds5-mt/Tom-06.wav'),
                  'tom_hi': _s(_TIDAL, f'{sds}/simmonssds5-ht/Tom-04.wav')})
    return inst.kit(_s(_LINN, ''), map=m, gains={'hats': -2, 'cymbals': -4}, lazy=True, level=0.0)


def _soft_linn_kit() -> Instrument:
    """LinnDrum played soft: its own thuddy kick, the woody snare, quiet hats (dreamwave)."""
    return inst.kit(_s(_LINN, ''), gains={'hats': -8, 'cymbals': -6, 'kick': -1.0}, lazy=True, level=0.0)


def _pop80_kit() -> Instrument:
    """SampleRadar 80s pop kit A (big processed studio drums) with the LinnDrum clap layered on 39."""
    root = f'{_POP80}/Drum Kits/Kit A'
    return inst.kit(_s(root, ''), map={'clap': _s(_LINN, 'clap.wav')},
                    gains={'hats': -14, 'shaker': -10, 'clap': -1}, lazy=True, level=-3.0)


def _hard_909_kit() -> Instrument:
    """TR-909 (Rob Roy set: every knob position) with the long kick, the brighter snare pushed forward and quiet
    hats: the darksynth machine (its distortion is in the role chain)."""
    return inst.kit(_s(_909, ''), extras=False, map={
        'kick': 'BT3AADA.WAV', 'kick2': 'BT7A0D7.WAV', 'snare': 'ST0TAS7.WAV', 'snare2': 'ST3T7S7.WAV',
        'clap': {'files': ['HANDCLP1.WAV', 'HANDCLP2.WAV'], 'layers': 'rr'},
        'rim': {'files': ['RIM63.WAV', 'RIM127.WAV'], 'layers': 'velocity'},
        'hat': 'HHCD2.WAV', 'pedal_hat': 'HHCD0.WAV', 'open_hat': 'HHOD6.WAV',
        'crash': 'CSHD8.WAV', 'crash2': 'CSHD4.WAV', 'ride': 'RIDED6.WAV', 'ride2': 'RIDEDA.WAV',
        'tom_lo': 'LT3D7.WAV', 'tom_floor_hi': 'LT7D7.WAV', 'tom_mid': 'MT3D7.WAV', 'tom_lowmid': 'MT7D7.WAV',
        'tom_hi': 'HT3D7.WAV', 'tom_high': 'HT7D7.WAV'},
        gains={'hats': -15, 'cymbals': -10, 'snare': 5.0, 'clap': 2.0, 'kick': -3.0}, lazy=True, level=-1.1)


def _808_kit() -> Instrument:
    """Roland TR-808 (SampleRadar essential kit): the boomy kick, snappy snare and clap, with the metallic hats
    and cymbals pulled well back (a sparse soundtrack kit)."""
    return inst.kit(_s(_ESS, 'TR 808 Kit'), lazy=True, level=1.6,
                    gains={'hats': -16, 'cymbals': -12, 'clap': -3, 'cowbell': -6, 'conga': -4, 'maracas': -8,
                           'claves': -6, 'rim': -4})


# ------------------------------------------------------------------------------------------ presets


def _opts(options: dict, allowed: dict, preset: str) -> dict:
    bad = set(options) - set(allowed)
    if bad:
        raise ComposeError(f"band {preset!r}: unknown option(s) {sorted(bad)}; options: "
                           f"{', '.join(f'{k}={v!r}' for k, v in allowed.items()) or 'none'}")
    out = dict(allowed)
    out.update(options)
    return out


_OUTRUN_NOTES = """\
Outrun / nightdrive (Kavinsky, Lazerhawk; 100-118 BPM, four-on-the-floor). Play:
  drums  kick on every beat, snare/clap on 2 and 4 (the gated burst is keyed from them), 8th hats vel 70-90,
         open hat on the 'and' of 4 before changes, Simmons/Linn tom fills; crash on section downbeats.
  bass   8th-note root/octave pulse E1-A2, vel 90-110: prog.bass('octave', rate='1/8', gate=0.85) is the dense
         Nightcall-style wall it is calibrated on (the default gate 0.6 pulses harder); sub osc + 3 dB kick pump.
  pad    held spread chords C3-C5 (voicing='spread'); automate instrument.cutoff for intros (600 -> 3000).
  keys   FM e-piano (DX7 E.PIANO 1) comping x..x..x. in C4-C5, vel 70-90; panned -0.3.
  arp    16th arps of the chord tones C4-C5 ('updown', octaves 2), panned +0.3; fade it in with gainDb.
  lead   the hook A4-A5 (supersaw); lead='solo' gives the resonant mono solo lead with vibrato; lead='piano' the
         sampled melody piano (sampled/piano_lead, gm/piano_lead without the pack):
         hook.clip(octave=5, vel=105).octave_double(-12, vel=0.8) (C5-C7, the octave below at 80 %), vel 90-115,
         repeated / rhythmic notes (a piano decays), instrument.pedal steps for legato lines.
  send.hall on the pad up 3-6 dB in breaks; a delay throw: automate the lead's send.echo to -4 on a last note.
Calibrated on songs/_bands/outrun (chorus) vs Kavinsky 'Nightcall', loudness-matched: every 1/3-octave region within
+-2 dB (bands sub -1.1, bass +0.7, low mids -0.8, mids +2.6, presence -0.9, brilliance +1.6, air -1.0 dB), crest 10.9
vs 11.0 dB, kick punch 11 vs 16 dB, low end mono. Nightcall is nearly mono (10 % wide above 150 Hz, correlation 0.90):
the preset stays at 48 % / 0.65, just above the synthwave profile's 40 % floor. Chorus -9.4 LUFS, song -10.7 LUFS-I,
0 warnings, 0 clicks. lead='piano' (the hook an octave up, octave-doubled): piano -17.8 vs supersaw -18.2 LUFS, bands
sub -1.0, bass +0.9, low mids -1.6, mids +3.4, presence -2.2, brilliance +0.9, air -1.0 dB (regions within +-2.8),
width 45 %, 0 warnings, 0 clicks."""


def outrun(song, *, without=(), sounds=None, ids=None, **options):
    """Outrun: LinnDrum + 909 kick with a keyed gated snare, octave bass, warm pad, DX e-piano, pluck arp, supersaw
    lead (lead='solo': solo lead, lead='piano': sampled melody piano), 224XL hall + plate, dotted-8th echo,
    master/synthwave. Options: lead='supersaw'|'solo'|'piano'."""
    o = _opts(options, {'lead': 'supersaw'}, 'outrun')
    if o['lead'] not in ('supersaw', 'solo', 'piano'):
        raise ComposeError(f"band 'outrun': lead must be 'supersaw', 'solo' or 'piano', got {o['lead']!r}")
    roles = {
        'drums': _Role(_linn_909_kit, alt=_raw('synthwave/drums_outrun'), packs=(_LINN, _909),
                       fx=_kit_chain(thr=-20, ratio=5, attack=4, drive=7, air=-2.0, lp=15000, low=-3.0),
                       gain=-1, sends={'gated': -6, 'plate': -18}),
        'bass': _Role(patches.get('synthwave/octave_bass').but(**{'sub.level': 0.7, 'amp.release': 0.2}),
                      fx=_bass_chain(low=2.0, mud=1.5), duck=3, release=200),
        'pad': _Role('synthwave/warm_pad', fx=[_tame(hp=120, lowmid=-1.5, presence=-1.5).but(**{
                          'peak2.freq': 1000, 'peak2.gain': -4, 'peak2.q': 0.7})], sends={'hall': -6}, duck=4),
        'keys': _Role('synthwave/epiano', gain=-3, pan=-0.3, fx=[_tame(hp=150).but(**{
                           'peak2.freq': 1000, 'peak2.gain': -2, 'peak2.q': 0.8})],
                      sends={'plate': -9, 'hall': -18}),
        'arp': _Role('synthwave/arp_pluck', gain=-4, pan=0.3, fx=[_tame(hp=350, lowmid=-2).but(**{
                          'peak2.freq': 1100, 'peak2.gain': -3, 'peak2.q': 0.9})],
                     sends={'echo': -10, 'hall': -14}, duck=4),
        'lead': (_Role('synthwave/supersaw_lead' if o['lead'] == 'supersaw' else 'synthwave/solo_lead', gain=2,
                       fx=[_tame(hp=200, presence=-1.5).but(**{'peak2.freq': 1000, 'peak2.gain': -2,
                                                               'peak2.q': 0.8})],
                       sends={'hall': -9, 'echo': -12})
                 if o['lead'] != 'piano' else
                 _piano('outrun')),
    }
    returns = {'hall': _hall(), 'plate': _plate(), 'echo': ('bus/echo', 0.0), 'gated': ('bus/gated', 1.0)}
    master = (patches.get('master/synthwave')
              .but_fx('eq', **{'high.gain': 1.5, 'peak2.freq': 1100, 'peak2.gain': -2.5, 'peak2.q': 1.0})
              .but_fx('compressor', threshold=-18).but_fx('width', width=1.1).but_fx('limiter', gain=8.5))
    return _assemble(song, 'outrun', roles, returns=returns, master=master,
                     analysis={'profile': 'synthwave'}, notes=_OUTRUN_NOTES, without=without, sounds=sounds, ids=ids)


_DREAM_NOTES = """\
Dreamwave / chillsynth (Timecop1983, FM-84; 80-100 BPM, half-time). Play:
  drums  half-time: kick on 1 and the 'and' of 2 (or 3), snare on 3, soft 8th hats vel 55-75; few fills.
  bass   long roots / half notes E1-A2, tied: prog.bass('root', rate='1/2').legato() (the moog bass glides; the
         calibration's dense low end), vel 85-100; its harmonics above 150 Hz are widened, the sub stays mono.
  pad    dream pad, held spread chords C3-C5 with 9ths / maj7s; strings (Juno strings) 3 dB under, A3-A5.
  keys   DX e-piano chords on 1 and the 'and' of 2, C4-C5, vel 60-85.
  lead   soft lead A4-A5, long notes, sparse (the bed carries the song); lead='piano' the sampled melody piano (the
         Timecop1983 / FM-84 piano hook):
         hook.clip(octave=5, vel=105).octave_double(-12, vel=0.8) (C5-C7, the octave below at 80 %), vel 90-115,
         repeated / rhythmic notes (a piano decays), instrument.pedal steps for legato lines.
  shimmer: automate send.shimmer on pad / strings up (-8) in intros and breaks, -18 under full sections.
Calibrated on songs/_bands/dreamwave (chorus) vs Timecop1983 'Deckard's Dream', loudness-matched: every region within
+-2.4 dB (sub -2.4, bass +0.1, low mids 0.0, mids +0.2, presence +1.7, brilliance +2.3, air +1.0 dB; the first
draft was +7.5 dB too bright, -9 dB sub), width above 150 Hz 73 % vs 158 % (correlation 0.57 vs 0.25), kick punch 7
vs 12 dB (was 28), crest 12.6 vs 14.2 dB, -11.4 vs -11.3 LUFS; 0 warnings. Width: the reference is phasey in the low
mids (correlation < 0 at 250 Hz-1 kHz); the preset stops short of that so pad-only intros / outros stay mono-safe
(correlation >= 0: the hall return is narrowed to 0.8 under the master's 1.4). The profile calls the top end 'dull'
(info): so is the reference - brighten with the master eq's high shelf if wanted. lead='piano' (the hook an octave up,
octave-doubled): piano -16.1 vs soft lead -17.0 LUFS, bands sub -2.4, bass +0.2, low mids -0.8, mids +2.8, presence
+2.8, brilliance +2.4, air +1.1 dB (the melody an octave higher: +2.6 dB mids), width 62 %, 0 warnings, 0 clicks."""


def dreamwave(song, *, without=(), sounds=None, ids=None, **options):
    """Dreamwave: soft LinnDrum, moog bass, dream pad + Juno strings, DX e-piano, soft lead, dark 224XL hall,
    tape echo, shimmer, master/dreamwave. Options: lead='soft'|'piano' (the sampled melody piano)."""
    o = _opts(options, {'lead': 'soft'}, 'dreamwave')
    if o['lead'] not in ('soft', 'piano'):
        raise ComposeError(f"band 'dreamwave': lead must be 'soft' or 'piano', got {o['lead']!r}")
    roles = {
        'drums': _Role(_soft_linn_kit, alt=_raw('synthwave/drums_808'), packs=(_LINN,),
                       fx=_kit_chain(thr=-18, ratio=3, attack=3, drive=4, air=-1.0, lp=9000, low=-5.0),
                       sends={'gated': -8, 'hall': -18}),
        'bass': _Role(patches.get('synthwave/moog_bass').but(**{'sub.level': 0.5}),
                      fx=_bass_chain(low=2.0, mud=3.5, hp=34.0, mud_freq=220) + [fx.dimension(mode=2)],
                      duck=3, release=240),
        'pad': _Role('synthwave/dream_pad', fx=[fx.eq({'peak1.freq': 200, 'peak1.gain': 2.0, 'peak1.q': 0.9,
                                                         'peak2.freq': 550, 'peak2.gain': -3.5, 'peak2.q': 0.9}),
                                                 fx.width(width=0.75)],
                     sends={'hall': -4, 'shimmer': -18}, duck=4, release=260),
        'strings': _Role('synthwave/jupiter_strings', gain=-3, sends={'hall': -6, 'shimmer': -18}, duck=4,
                         release=260),
        'keys': _Role('synthwave/epiano', gain=-2, pan=-0.25, sends={'plate': -8, 'hall': -14}),
        'lead': (_Role('synthwave/soft_lead', gain=1, fx=[fx.chorus(mode='II', mix=0.4)],
                       sends={'hall': -6, 'echo': -12})
                 if o['lead'] == 'soft' else
                 _piano('dreamwave')),
    }
    returns = {'hall': _hall(dark=True, width=0.8), 'plate': _plate(), 'echo': ('bus/tape_echo', 0.0),
               'shimmer': ('bus/shimmer', 0.0), 'gated': ('bus/gated', -2.0)}
    master = (patches.get('master/dreamwave')
              .but_fx('eq', **{'high.freq': 3000, 'high.gain': -2.0, 'lp.freq': 13000, 'peak2.freq': 1500,
                               'peak2.gain': -2.5, 'peak2.q': 0.6})
              .but_fx('width', width=1.4).but_fx('limiter', gain=1.5))
    return _assemble(song, 'dreamwave', roles, returns=returns, master=master,
                     analysis={'profile': 'dreamwave'}, notes=_DREAM_NOTES, without=without, sounds=sounds, ids=ids,
                     gate_pitches=('snare',))


_DARK_NOTES = """\
Darksynth (Perturbator, Carpenter Brut; 110-140 BPM, minor / phrygian). Play:
  drums  four-on-the-floor or half-time breakdowns, snare/clap on 2 and 4, 16th hats vel 70-95, tom fills.
  bass   distorted 8th / 16th root pulses and octave riffs E1-A2, vel 95-120; rolling 16ths with gate 0.9 give
         the Perturbator wall (calibration), the default staccato gate punches harder.
  pad    dark pad, held chords (minor, bII) A3-A4, above the sequence.
  arp    16th sequence E3-E4 (root-octave-fifth cells), panned +0.25.
  stab   distorted brass stabs on accents C3-C5.
  lead   aggressive sync lead A3-A5 (lead='sync'); long notes with vibrato, octave jumps; lead='piano' the sampled
         melody piano over the wall:
         hook.clip(octave=5, vel=105).octave_double(-12, vel=0.8) (C5-C7, the octave below at 80 %), vel 90-115,
         repeated / rhythmic notes (a piano decays), instrument.pedal steps for legato lines.
Calibrated on songs/_bands/darksynth (drop) vs Perturbator 'Future Club' (Dangerous Days, 12:59-17:47), loudness-
matched: every region within +-2 dB except 22-35 Hz (-3.6: the bass is high-passed at 25 Hz), bands sub -0.9, bass
+0.4, low mids -0.1, mids +0.8, presence -1.5, brilliance +1.6, air -1.1 dB; width 36 vs 27 %, correlation 0.79 vs
0.73, kick punch 9 vs 11 dB, crest 9.7 vs 10.0 dB. The reference plays at -5 LUFS; the preset stops at the darksynth
profile's range (drop -9.0, song -9.4 LUFS-I); 0 warnings. lead='piano' (the riff an octave up, octave-doubled):
piano -18.4 vs sync lead -19.0 LUFS, bands sub -1.0, bass +0.3, low mids -0.3, mids +1.5, presence -1.6, brilliance
+1.4, air -1.2 dB, width 36 %, 0 warnings, 0 clicks."""


def darksynth(song, *, without=(), sounds=None, ids=None, **options):
    """Darksynth: distorted TR-909, growl bass, dark pad, 16th sequence, distorted brass stabs, sync lead, dark hall
    + plate, echo, master/darksynth. Options: lead='sync'|'piano' (the sampled melody piano)."""
    o = _opts(options, {'lead': 'sync'}, 'darksynth')
    if o['lead'] not in ('sync', 'piano'):
        raise ComposeError(f"band 'darksynth': lead must be 'sync' or 'piano', got {o['lead']!r}")
    roles = {
        'drums': _Role(_hard_909_kit, alt=_raw('synthwave/drums_dark'), packs=(_909,),
                       fx=[fx.saturator(mode='tube', drive=10)] + _kit_chain(thr=-16, ratio=6, attack=5, drive=4,
                                                                            lowmid=-3, air=-1.0, lp=16000, low=-5.0)
                          + [fx.eq({'peak3.freq': 3500, 'peak3.gain': -2.0, 'peak3.q': 0.8})],
                       sends={'gated': -9, 'plate': -14}),
        'bass': _Role(patches.get('synthwave/dark_bass').but(**{'sub.level': 0.6}),
                      fx=_bass_chain(low=3.0, mud=5.0, mud_freq=200, hp=25.0),
                      duck=4, release=160),
        'pad': _Role('synthwave/dark_pad', gain=-1,
                     fx=[_tame(hp=100).but(**{'peak2.freq': 1200, 'peak2.gain': -4.5})], sends={'hall': -6}, duck=6),
        'arp': _Role('synthwave/seq_pulse', gain=-3, pan=0.25, fx=[_tame(hp=450, lowmid=-3)],
                     sends={'echo': -12, 'hall': -16}, duck=6),
        # the distortion in front of the patches' chorus / dimension / micro-pitch double (pre_fx): driven after
        # them it ground the moving copies together into a grainy wobble
        'stab': _Role('synthwave/brass_stab', gain=-2, pan=-0.2, pre_fx=[fx.saturator(mode='tube', drive=8)],
                      sends={'hall': -10, 'plate': -12}, duck=4),
        'lead': (_Role('synthwave/sync_lead', pre_fx=[fx.saturator(mode='tube', drive=6)],
                       fx=[_tame(hp=180).but(**{'peak2.freq': 900, 'peak2.gain': -2.5})],
                       sends={'hall': -9, 'echo': -12})
                 if o['lead'] == 'sync' else
                 _piano('darksynth')),
    }
    returns = {'hall': _hall(dark=True), 'plate': _plate(), 'echo': ('bus/echo', 0.0), 'gated': ('bus/gated', 1.0)}
    master = (patches.get('master/darksynth')
              .but_fx('eq', **{'hp.freq': 24, 'peak2.freq': 1000, 'peak2.gain': -2.0, 'peak2.q': 0.7,
                               'peak3.freq': 4000, 'peak3.gain': 4.0, 'high.freq': 10000, 'high.gain': 3.0})
              .but_fx('compressor', threshold=-20).but_fx('tape', drive=9.0).but_fx('exciter', amount=0.2)
              .but_fx('width', width=1.15).but_fx('limiter', gain=11.0))
    # A DC blocker before the limiter: the hot tape on the distorted bass left a 0.001-0.0016 DC offset (a report
    # warning); after the limiter the same high-pass pushed the true peak over 0 dBTP.
    master.fx.insert(len(master.fx) - 1, fx.eq({'hp.freq': 16}))
    return _assemble(song, 'darksynth', roles, returns=returns, master=master,
                     analysis={'profile': 'darksynth'}, notes=_DARK_NOTES, without=without, sounds=sounds, ids=ids)


_RETRO_NOTES = """\
Retrowave pop, instrumental (The Midnight, Gunship; 100-125 BPM). Play:
  drums  punchy 80s kit: kick 1 and 3 (+ pushes), snare + clap on 2 and 4 (gated), 16th hats with accents.
  bass   8th octave pulse (gate 0.85) or syncopated lines E1-A2, vel 90-110; pumped 5 dB.
  pad    Juno pad held chords C3-C5; choir (Fairlight 'aah') 4 dB under on the choruses, C3-C5.
  keys   bright DX e-piano: 8th/quarter comping C4-C5.
  brass  stabs on the off-beats / chord changes C4-C5 (short notes, vel 90-110).
  lead   the anthem hook A4-A5 (brass-y lead); lead='supersaw' or lead='sax' (a sampled tenor sax when installed);
         lead='piano' the sampled melody piano (The Midnight's piano hooks):
         hook.clip(octave=5, vel=105).octave_double(-12, vel=0.8) (C5-C7, the octave below at 80 %), vel 90-115,
         repeated / rhythmic notes (a piano decays), instrument.pedal steps for legato lines.
  choir='vocoder': the choir becomes synthwave/vocoder_choir, the robot choir that sings its chords with the words of
         a speech track: pass voice=<track> (e.g. s.track('voice', speech.words([...]).instrument())) and the preset
         keys it (speech.vocode, the voice muted), or call speech.vocode(b.choir, voice) yourself - a vocoder
         without a voice does not render.
Calibrated on songs/_bands/retrowave (chorus) vs The Midnight 'Sunset', loudness-matched: every region within
+-2.3 dB (sub -0.1, bass -0.3, low mids +1.6, mids +0.8, presence -1.3, brilliance -1.7, air +1.4 dB), width above
150 Hz 64 vs 65 %, correlation 0.59 vs 0.35 (the reference's low end is stereo; ours stays mono; the hall return is
narrowed to 0.7 so the pad-only intro stays at correlation >= 0), kick punch 14 vs 19 dB, crest 12.1 vs 14.8 dB,
-10.1 vs -9.7 LUFS; 0 warnings. lead='supersaw' gets a 3.5 kHz dip instead of the brass lead's presence lift (the
lift read +4 dB presence vs the synthwave profile: a 'harsh' warning). lead='piano' (the hook an octave up,
octave-doubled): piano -17.2 vs brass lead -17.9 LUFS, bands sub -0.2, bass -0.4, low mids +1.6, mids +0.9, presence
-1.3, brilliance -1.6, air +1.4 dB (within 0.4 dB of the brass lead's), width 57 %, 0 warnings, 0 clicks."""


def retrowave(song, *, without=(), sounds=None, ids=None, **options):
    """Retrowave pop: 80s pop kit + Linn claps (gated), octave bass, Juno pad, bright DX e-piano, brass stabs, big
    lead, Fairlight choir (choir='vocoder': the vocoder choir), 224XL hall + plate, echo, master/synthwave.
    Options: lead='brass'|'supersaw'|'sax'|'piano', choir='fairlight'|'vocoder'|'synth', voice=<track> (the vocoder's
    modulator, choir='vocoder' only)."""
    o = _opts(options, {'lead': 'brass', 'choir': 'fairlight', 'voice': None}, 'retrowave')
    leads = {'brass': 'synthwave/brass_lead', 'supersaw': 'synthwave/supersaw_lead'}
    if o['lead'] not in (*leads, 'sax', 'piano'):
        raise ComposeError(f"band 'retrowave': lead must be 'brass', 'supersaw', 'sax' or 'piano', "
                           f"got {o['lead']!r}")
    if o['choir'] not in ('fairlight', 'vocoder', 'synth'):
        raise ComposeError(f"band 'retrowave': choir must be 'fairlight', 'vocoder' or 'synth', got {o['choir']!r}")
    if o['voice'] is not None and o['choir'] != 'vocoder':
        raise ComposeError("band 'retrowave': voice= keys the vocoder choir; give it with choir='vocoder'")
    if o['lead'] == 'sax':
        lead = _Role('sampled/tenor_sax', alt='synthwave/soft_lead', packs=('mtg-solo-sax',), gain=1,
                     sends={'hall': -10, 'plate': -14, 'echo': -16})
    elif o['lead'] == 'piano':
        lead = _piano('retrowave')
    else:
        # The brass lead gets presence; the supersaw already has plenty (+2 dB there read +4.0 dB presence against
        # the synthwave profile, a 'harsh presence' warning): it gets outrun's 3.5 kHz / 1 kHz dips instead.
        saw = o['lead'] == 'supersaw'
        lead = _Role(leads[o['lead']], gain=3.0 if saw else 2.0,
                     fx=[_tame(hp=200, lowmid=-2.5, presence=-3.5 if saw else 2.0)], sends={'hall': -10, 'echo': -12})
    choir = {'fairlight': _Role('sampled/fairlight_choir', alt='synthwave/choir_pad', packs=(_CMI,), gain=-4,
                                sends={'hall': -9}, duck=4),
             'vocoder': _Role('synthwave/vocoder_choir', gain=-3, sends={'hall': -9}),
             'synth': _Role('synthwave/choir_pad', gain=-4, sends={'hall': -9}, duck=4)}[o['choir']]
    roles = {
        'drums': _Role(_pop80_kit, alt=_raw('synthwave/drums_linn'), packs=(_POP80, _LINN),
                       fx=_kit_chain(thr=-15, ratio=3.5, attack=10, drive=5, low=-3.0),
                       sends={'gated': -8, 'plate': -15}),
        'bass': _Role(patches.get('synthwave/octave_bass').but(**{'sub.level': 0.25, 'amp.release': 0.2}),
                      fx=_bass_chain(low=3.5), duck=5, release=190),
        'pad': _Role('synthwave/juno_pad', fx=[_tame(hp=150, lowmid=-3.0, presence=2.0)], sends={'hall': -6},
                     duck=5),
        'keys': _Role('synthwave/epiano_bright', gain=-3, pan=-0.3, fx=[_tame(hp=220, lowmid=-3.0)],
                      sends={'plate': -9}),
        'brass': _Role('synthwave/brass_stab', gain=-2, pan=0.25, sends={'hall': -12, 'plate': -14}),
        'choir': choir,
        'lead': lead,
    }
    returns = {'hall': _hall(width=0.7), 'plate': _plate(), 'echo': ('bus/echo', 0.0), 'gated': ('bus/gated', 1.0)}
    master = (patches.get('master/synthwave')
              .but_fx('eq', **{'peak1.freq': 380, 'peak1.gain': -4.5, 'peak1.q': 0.7, 'peak3.freq': 3500,
                               'peak3.gain': 1.5, 'peak3.q': 0.7, 'high.freq': 6000, 'high.gain': 5.5})
              .but_fx('exciter', freq=3500, amount=0.75).but_fx('width', width=1.25).but_fx('limiter', gain=3.5))
    band = _assemble(song, 'retrowave', roles, returns=returns, master=master, analysis={'profile': 'synthwave'},
                     notes=_RETRO_NOTES, without=without, sounds=sounds, ids=ids)
    if o['voice'] is not None and 'choir' in band:
        from .. import speech
        speech.vocode(band.choir, o['voice'])
    return band


_SCIFI_NOTES = """\
Sci-fi / soundtrack synth (S U R V I V E, Vangelis, Timecop1983's slow side; 70-100 BPM). Play:
  arp    the 16th/8th Stranger-Things sequence C3-C5 (its own ping-pong), the heartbeat of the piece.
  seq    a second, slower sequence (8ths, octaves) C2-C4, panned left; enter it later for the build.
  pad    evolving sweep pad (slow filter drift built in), held chords C3-C5, whole bars.
  bass   long roots E1-A2 (moog bass), or none in intros.
  bells  sparse DX bell answers C5-C6, vel 60-85.
  drums  sparse TR-808: kick on 1, snare / clap on 3, a few hats; leave it out of intros.
  lead   optional soft lead A4-A5, long notes; lead='piano' the sampled melody piano (warmer here: +2.5 dB body, less
         top):
         hook.clip(octave=5, vel=105).octave_double(-12, vel=0.8) (C5-C7, the octave below at 80 %), vel 90-115,
         repeated / rhythmic notes (a piano decays), instrument.pedal steps for legato lines.
Calibrated on songs/_bands/scifi (peak) vs Timecop1983 'Deckard's Dream' (the closest reference in the set; a S U R V
I V E record would be the real one), loudness-matched: regions within +-2.9 dB from 60 Hz to 12 kHz (bass -1.0, low
mids -0.6, mids +2.4, presence +1.4, brilliance +2.9 dB: the DX bells ring at 8 kHz).
The sub follows the bass roots: in the demo's A minor (roots A1 = 55 Hz) the sub band carries +5 dB of energy, the same
demo in D minor (roots G1-D2) reads a 1/3-octave average of -4.5 dB below 56 Hz with a +6.7 dB peak at 50 Hz - judge
the low end per song. Width above 150 Hz 71 % vs 158 % (the hall return narrowed to 0.65 keeps pad-only intros at
correlation >= 0; the demo's outro reads -0.03 only through its 7 s shimmer tail), kick punch 9 vs 12 dB, crest 11.9
vs 14.2 dB, -12.2 vs -11.3 LUFS; 0 warnings. lead='piano' (the theme an octave up, octave-doubled): piano -17.9 vs
soft lead -18.0 LUFS, bands sub +5.5, bass -1.0, low mids -1.8, mids +4.1, presence +2.1, brilliance +2.8, air -1.0 dB
(mids +1.7 over the soft lead's: the melody an octave higher), width 62 %, 0 warnings, 0 clicks."""


def scifi(song, *, without=(), sounds=None, ids=None, **options):
    """Sci-fi: Stranger-Things arp + second sequence, evolving sweep pad, moog bass, DX bells, sparse TR-808, soft
    lead (lead='piano': the sampled melody piano); dark 224XL hall (narrowed), shimmer, tape echo, master/dreamwave.
    Options: lead='soft'|'piano'."""
    o = _opts(options, {'lead': 'soft'}, 'scifi')
    if o['lead'] not in ('soft', 'piano'):
        raise ComposeError(f"band 'scifi': lead must be 'soft' or 'piano', got {o['lead']!r}")
    roles = {
        'drums': _Role(_808_kit, alt=_raw('synthwave/drums_808'), packs=(_ESS,),
                       fx=_kit_chain(thr=-16, ratio=2.5, attack=5, drive=3, air=-2.0, lp=8000, low=-7.0), gain=-2,
                       sends={'hall': -14}),
        'bass': _Role(patches.get('synthwave/moog_bass').but(**{'sub.level': 0.2}),
                      fx=_bass_chain(low=0.0, mud=4.5, hp=36.0, mud_freq=200) + [fx.dimension(mode=2)],
                      duck=6, release=260),
        'arp': _Role('synthwave/stranger_arp', gain=-1, fx=[_tame(hp=300, lowmid=-2.0, presence=-3.0, top=-3.0)
                                                            .but(**{'peak2.freq': 900, 'peak2.gain': -2.0})],
                     sends={'hall': -8}),
        'seq': _Role('synthwave/seq_pulse', gain=-4, pan=-0.35, sends={'echo': -12, 'hall': -14}),
        'pad': _Role('synthwave/sweep_pad', fx=[fx.eq({'peak1.freq': 200, 'peak1.gain': 2.0, 'peak1.q': 0.9,
                                                       'peak2.freq': 700, 'peak2.gain': -4.0, 'peak2.q': 0.7}),
                                                fx.width(width=0.8)],
                     sends={'hall': -4, 'shimmer': -14},
                     mods=[('instrument.cutoff', sample_hold('2 bars', smooth=1, depth=0.5, curve='exp'))]),
        'bells': _Role('synthwave/dx_bells', gain=-2, pan=0.2, fx=[_tame(hp=300, top=-6.0, lp=9000)],
                       sends={'hall': -8, 'echo': -12, 'shimmer': -12}),
        'lead': (_Role('synthwave/soft_lead', gain=0, fx=[fx.chorus(mode='II', mix=0.4)],
                       sends={'hall': -5, 'echo': -12})
                 if o['lead'] == 'soft' else
                 _piano('scifi')),
    }
    # the plate return only exists when a role sends to it (lead='piano')
    returns = {'hall': _hall(dark=True, width=0.65), 'plate': _plate(), 'echo': ('bus/tape_echo', 0.0),
               'shimmer': ('bus/shimmer', 0.0)}
    master = (patches.get('master/dreamwave')
              .but_fx('eq', **{'high.freq': 3000, 'high.gain': -3.0, 'lp.freq': 13000, 'peak2.freq': 800,
                               'peak2.gain': -3.0, 'peak2.q': 0.7})
              .but_fx('width', width=1.5).but_fx('limiter', gain=1.5))
    return _assemble(song, 'scifi', roles, returns=returns, master=master,
                     analysis={'profile': 'dreamwave'}, notes=_SCIFI_NOTES, without=without, sounds=sounds, ids=ids)


# ------------------------------------------------------------------------------------------ registry

bands.register('outrun', outrun, genre='synthwave', roles=('drums', 'bass', 'pad', 'keys', 'arp', 'lead'),
               description='LinnDrum + 909 kick, gated snare, 8th octave bass, warm pad, DX e-piano, pluck arp, '
                           'supersaw / solo / piano lead; 224XL hall + plate, echo; master/synthwave',
               tuned='Kavinsky - Nightcall (compare, loudness-matched)')
bands.register('dreamwave', dreamwave, genre='synthwave',
               roles=('drums', 'bass', 'pad', 'strings', 'keys', 'lead'),
               description='half-time soft LinnDrum, moog bass, dream pad + Juno strings, DX e-piano, soft / piano '
                           'lead; dark 224XL hall, tape echo, shimmer; master/dreamwave',
               tuned="Timecop1983 - Deckard's Dream (compare, loudness-matched)")
bands.register('darksynth', darksynth, genre='synthwave', roles=('drums', 'bass', 'pad', 'arp', 'stab', 'lead'),
               description='distorted TR-909, growl bass, dark pad, 16th sequence, distorted brass stabs, sync / piano '
                           'lead; '
                           'master/darksynth',
               tuned='Perturbator - Future Club (compare, loudness-matched)')
bands.register('retrowave', retrowave, genre='synthwave',
               roles=('drums', 'bass', 'pad', 'keys', 'brass', 'choir', 'lead'),
               description='80s pop kit + claps (gated), octave bass, Juno pad, bright DX e-piano, brass stabs, '
                           'Fairlight / vocoder choir, brass / supersaw / sax / piano lead; master/synthwave',
               tuned='The Midnight - Sunset (compare, loudness-matched)')
bands.register('scifi', scifi, genre='synthwave', roles=('drums', 'bass', 'arp', 'seq', 'pad', 'bells', 'lead'),
               description='Stranger-Things arp + sequence, evolving sweep pad, moog bass, DX bells, sparse TR-808, '
                           'soft / piano lead; dark hall, shimmer, tape echo; master/dreamwave',
               tuned="Timecop1983 - Deckard's Dream (the closest reference; compare, loudness-matched)")
