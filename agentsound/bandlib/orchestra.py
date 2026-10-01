"""Orchestra band presets: a string quartet, a chamber orchestra, a symphony orchestra, a film orchestra and a
church organ - each a seated, balanced ensemble in one shared hall (a convolution IR), ready to be played.

    from agentsound import bands
    from agentsound.bandlib import orchestra as orch
    b = bands.symphony_orchestra(s)                   # or bands.make('string_quartet', s), ...
    orch.perform(b, 'violins1', melody, verse)        # played: articulations, dynamics lane, timing, (legato)
    orch.dynamics(b, orch.STRINGS, [(verse.start, 'p'), (verse.bar(7), 'ff', 'smooth')])   # a tutti crescendo
    b.cellos.play(line.articulate('pizzicato'), verse)                                     # or plain notes
    ANALYSIS = b.analysis                             # {'profile': 'classical'} ('film' for film_orchestra)
    sc = orch.Score(s, b, DYNAMICS); sc.add(...); sc.double(...); sc.hits(...); sc.perform()   # the whole piece's
    # parts with one dynamics map, doublings, hits, natural brass, beds, the choir (bandlib/scoring.py, orch.*)

Presets (bands.list('orchestra'); bands.get(name) / band.describe() for the details):
  string_quartet      violin1 violin2 viola cello: solo players (mono legato), live dynamics, keyswitched articulations
  chamber_orchestra   VSCO 2 chamber strings, wind pairs, 2 horns, timpani (a Classical-era band)
  symphony_orchestra  SSO 4.0 full sections: strings 5, woodwinds 4, horns, trumpets, trombones, tuba, timpani,
                      percussion, harp, celesta
  film_orchestra      the symphony without celesta plus choir 'aah', low brass (bass trombone), epic drums; hybrid=True
                      adds a synth sub and a synth pulse
  church_organ        a GrandOrgue pipe organ (Lars Palo, Burea or Pitea): soft / principal / full registrations +
                      pedal, in a big church

How the ensembles play (band.notes / band.info carry the details per preset):
  * DYNAMICS ARE A LANE, NOT A VELOCITY. Every sustaining role is a sampler with live dynamics ('instrument.dynamics'
    0..1: the libraries' mod wheel - layers crossfade, the tone opens, the level rises WHILE notes sound). Velocity
    only shapes the attack / accent. perform() turns written velocities into that lane (vel 40 = p, 78 = mf, 95 = f,
    115 = ff) with swells on long notes; dynamics() writes one curve on several roles (crescendi, subito p). A role
    that is never automated plays at 'mf' (DYN['mf'] = 0.6), which is where the section balance is calibrated.
  * Articulations are keyswitches inside each role (one track per section): clip.articulate('pizzicato'),
    'staccato', 'tremolo' ... band.info['articulations'][role] lists what each role has (the same core names in every
    preset: sustain, staccato / spiccato, pizzicato, tremolo, marcato, legato where the library has them).
  * Sample attacks are slow (strings 150-300 ms): perform() starts long notes band.info['lead_ms'][role] early so they
    SOUND on the beat; shorts stay on it.
  * Seating (audience view) and depth: front strings closer (less hall send, full top), winds in the middle, horns /
    brass / percussion at the back (more hall, a softer top). One convolution hall for everybody.

Levelling (read from the samples when a preset is built, ~5 s the first time): the sets are uneven - VSCO 2 CE
notes jump up to 15 dB from one recording to the next (round robins up to 20), SSO a few dB. _even_notes puts every
key range of every articulation (the layer played at mf) on a straight line over the keyboard (the register's trend
stays, corrections <= 10 dB) and round robins on their mean; _level_layers turns VSCO's velocity layers (boosted
11-29 dB for velocity playing) into a live dynamics stack: each layer under the loudest by its measured median
distance, the softest at most 14 dB down (a crescendo p -> f grows, alike over the keyboard - kept as recorded, a
VSCO tremolo swung 35 dB).

Calibration (the role gains and the per-articulation 'gain's in the tables below), measured on renders of the
levelled instruments: every role plays a line over its sweet spot at mf alone and its dry loudness (LUFS) is set
against the recipe's weights (a woodwind line ~ -3 dB under a string section line; trumpets / trombones / horns for
the chords they usually play: the SSO brass samples are a2 / a3 sections). Articulations against the sustain of the
same notes at the same dynamics (the short's loudest 100 ms against the sustain's body): staccato / spiccato -1 dB,
pizzicato -2, tremolo -1, marcato +2, non-vibrato level; harmonics / col legno / muted stay as soft as recorded.
pp -> ff spans ~20 dB in every section (15-23). Where a library's sustain loops click (SSO violas, celli, basses,
oboes) the sustain comes from a cleaner set (Virtual Playing Orchestra re-loops, the VSCO 2 oboe) under the same
dynamics curve - or, when that pack is not installed, the SSO sustain at the same level; the remaining SSO loop
points (a few notes of the 1st / 2nd violins, clarinets, bassoons, the chorus) can show as soft single-track clicks,
masked in the mix.

Credits: Sonatina Symphonic Orchestra (Mattias Westlund, Peter Eastman; CC Sampling Plus 1.0), VSCO 2 CE
(Versilian Studios, CC0), Virtual Playing Orchestra (Paul Battersby; royalty-free), No Budget Orchestra 2
(CC-BY-SA 4.0, choir 'oh'), MuseScore General SoundFont (taikos), Lars Palo organs (CC-BY-SA 2.5: "sample set by
Lars Palo"), Voxengo IM Reverbs. The build writes out/credits.txt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .. import articulation as art
from .. import bands, library
from ..bands import Band
from ..patches import Instrument, Patch, fx, inst
from ..patterns import Clip, as_clip
from ..theory import ComposeError

__all__ = ['DYN', 'STRINGS', 'WOODWINDS', 'BRASS', 'PERCUSSION_KEYS', 'dyn', 'dynamics', 'perform', 'ring', 'rebow',
           'lead', 'installed',
           # the orchestrator's desk (bandlib/scoring.py): a whole piece's parts + one dynamics map, doublings, hits
           'VEL', 'PHRASING', 'FALLBACK', 'TUTTI_ROLES', 'WINDS8_ROLES', 'UNISON_OCTAVES', 'natural_brass',
           'timpani_tuning', 'Score', 'Choir', 'bed', 'double', 'colla_parte', 'hits', 'unison', 'sing', 'swells',
           'BED']

SSO = 'samples/sso/Sonatina Symphonic Orchestra/'
SSO_STR = SSO + 'Strings - Performance/'
SSO_WW = SSO + 'Woodwinds - Performance/'
SSO_BR = SSO + 'Brass - Performance/'
VSCO = 'samples/vsco2-ce/'
VPO = 'samples/vpo-scripts-standard/'
VOX = 'samples/voxengo-im-reverbs/'

DYN = {'ppp': 0.06, 'pp': 0.16, 'p': 0.3, 'mp': 0.45, 'mf': 0.6, 'f': 0.75, 'ff': 0.9, 'fff': 1.0}
"""Dynamic markings -> the 'dynamics' lane (0..1). The section balance is calibrated at 'mf'."""

STRINGS = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'violin1', 'violin2', 'viola', 'cello')
WOODWINDS = ('flutes', 'oboes', 'clarinets', 'bassoons')
BRASS = ('horns', 'trumpets', 'trombones', 'low_brass', 'tuba')


def installed(pack: str) -> bool:
    """Is the sample pack `pack` installed (assets/samples/<pack>/SOURCE.json or $AGENTSOUND_SAMPLES)?"""
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


def _require(preset: str, *packs: str) -> None:
    missing = [p for p in packs if not installed(p)]
    if missing:
        raise ComposeError(f"band {preset!r} needs the sample pack(s) {', '.join(missing)}: "
                           f"python -m agentsound samples fetch {' '.join(missing)}")


def dyn(x) -> float:
    """A dynamic marking ('pp' .. 'fff') or a number 0..1 -> the 'dynamics' value."""
    if isinstance(x, str):
        if x not in DYN:
            raise ComposeError(f"dynamic marking must be one of {', '.join(DYN)} (or 0..1), got {x!r}")
        return DYN[x]
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0.0 <= x <= 1.0:
        raise ComposeError(f"dynamics must be a marking ({', '.join(DYN)}) or 0..1, got {x!r}")
    return float(x)


# --------------------------------------------------------------------------------------------- role specs

@dataclass
class _Role:
    """How one role sounds and sits: the default sound (a builder, so nothing is read at import), placement
    (pan, width, hall send, high shelf for depth, high-pass), calibrated gain, playing hints."""
    sound: object                        # callable() -> Instrument / Patch, or a patch name
    pan: float = 0.0
    width: float = 1.0
    send: float = -6.0                   # dB to the hall
    shelf: float = 0.0                   # dB high shelf at 6 kHz (depth: the back rows are softer on top)
    hp: float = 30.0                     # high-pass Hz
    gain: float = 0.0                    # calibrated fader (dB)
    lead_ms: float = 0.0                 # long notes start this much early (slow sample attacks)
    rng: tuple = ('C2', 'C7')            # playable range (sounding)
    sweet: tuple = ('C3', 'C6')          # where it sings
    arts: tuple = ()                     # articulation names (keyswitches); () = none
    kind: str = 'sustain'                # sustain (dynamics lane) | struck (velocity = dynamics) | organ | synth
    #                                      (| plain: a sounds= override that is not a sampler)
    mono: bool = False                   # a monophonic legato player (solo instrument)
    vib: float = 0.0                     # extra delayed vibrato depth (ct) perform() adds on long notes (0 = none)
    monobass: float = 0.0                # fx.width monobass (Hz) for the low sections
    desc: str = ''
    eq: dict = field(default_factory=dict)   # extra eq bands (peak1 low-mid / peak3 presence ...) on top of hp + shelf
    extra_fx: tuple = field(default_factory=tuple)


def _pres(gain: float, freq: float = 3300.0) -> dict:
    """A presence bell (steely sampled strings / brass: the recipe's -1..-3 dB at 2.5-4 kHz)."""
    return {'peak3.freq': freq, 'peak3.gain': gain, 'peak3.q': 0.9}


def _mud(gain: float, freq: float = 320.0) -> dict:
    """A low-mid bell (dense mid sections: the recipe's -2 dB at 250-400 Hz)."""
    return {'peak1.freq': freq, 'peak1.gain': gain, 'peak1.q': 0.9}


def _honk(gain: float, freq: float = 1200.0) -> dict:
    """A mid bell (boxy / honky 0.8-2.5 kHz)."""
    return {'peak2.freq': freq, 'peak2.gain': gain, 'peak2.q': 0.8}


def _air(gain: float, freq: float = 9000.0) -> dict:
    """A high shelf for air on the front instruments (the sample sets are darker than a real front row)."""
    return {'high.freq': freq, 'high.gain': gain}


def _body(gain: float, freq: float = 140.0) -> dict:
    """A low shelf for body (cellos, basses)."""
    return {'low.freq': freq, 'low.gain': gain}


# The SSO mod-wheel level curve (dynamics x 127 -> gain: 24 dB, dB-linear up to 112), for programs from another
# library mixed into an SSO instrument, so they follow the same dynamics lane.
_DYN_CURVE = [[v, round(16.0 ** (min(v, 112) / 112.0) / 16.0, 5)] for v in range(0, 128, 8)] + [[127, 1.0]]


def _follow_dynamics(ins: Instrument, names) -> Instrument:
    """Read a (lazy) sfz_multi now and give the zones of the articulations `names` the SSO dynamics level curve
    (dynGain) when they have no dynamics mapping of their own: a VSCO tremolo inside an SSO solo string (or a
    cleaner-looping sustain from another library inside an SSO section) then swells with the same 'dynamics' lane as
    the SSO articulations around it; velocity keeps a little accent (ampVeltrack 0.3), like the SSO programs.
    Velocity-layered programs in an instrument with layers='dynamics' are left alone: the lane already crossfades
    their recorded layers (p -> f), a dynGain on top would count the dynamics twice (a 50 dB lane)."""
    ins.expand()
    keys = (ins.info or {}).get('sfz', {}).get('keyswitches') or {}
    want = {keys[n] for n in names if n in keys}
    stacked = set()
    if ins.params.get('layers') == 'dynamics':
        vel: dict = {}
        for z in ins.params.get('samples') or []:
            if z.get('swLast') in want and z.get('trigger') != 'release':
                vel.setdefault(z.get('swLast'), set()).add((z.get('vello', 0), z.get('velhi', 127)))
        stacked = {sw for sw, v in vel.items() if len(v) > 1}
    for z in ins.params.get('samples') or []:
        if z.get('swLast') in want and z.get('swLast') not in stacked and not any(
                k in z for k in ('dynGain', 'xfinLoDyn', 'xfoutLoDyn', 'xfinHiDyn', 'xfoutHiDyn')):
            z['dynGain'] = [list(p) for p in _DYN_CURVE]
            z['ampVeltrack'] = 0.3
    return ins


# --------------------------------------------------------------------------------------------- zone levelling

_LEVELS: dict = {}


def _sample_level(path: str, offset: int = 0, seconds: float = 1.5):
    """The level of a WAV as played (RMS dBFS of the first channel) in its first `seconds` from `offset` (sample
    frames): a long note's body after its attack (0.25 s on), a short note's loudest 100 ms. None when the file can't
    be read. Cached per file."""
    import array
    import os
    import wave
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (path, int(offset), st.st_mtime_ns, st.st_size)
    if key in _LEVELS:
        return _LEVELS[key]
    val = None
    try:
        with wave.open(path, 'rb') as w:
            sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
            if offset:
                w.setpos(min(int(offset), max(0, w.getnframes() - 1)))
            raw = w.readframes(int(seconds * sr))
        if sw == 2:
            a = array.array('h')
            a.frombytes(raw[:len(raw) // 2 * 2])
        elif sw == 3:                                   # the top 16 bits of each 24-bit sample
            n = len(raw) // 3
            b = bytearray(2 * n)
            b[0::2] = raw[1:3 * n:3]
            b[1::2] = raw[2:3 * n:3]
            a = array.array('h')
            a.frombytes(bytes(b))
        else:
            a = None
        if a is not None and len(a) >= ch:
            dec = 2 * ch                                 # every 2nd frame, the first channel (enough for a level)
            x = a[::dec]
            fs = sr / 2.0
            n = max(8, int(0.1 * fs))
            peak = 0.0                                   # the loudest 100 ms
            for i in range(0, max(1, len(x) - n + 1), n // 2):
                s = x[i:i + n]
                peak = max(peak, sum(v * v for v in s) / len(s))
            e = peak
            if len(x) > 1.2 * fs:                        # a sustained note is judged by its body after the attack,
                seg = x[int(0.25 * fs):]                 # a decaying one (pizzicato, a short) by its peak
                body = sum(v * v for v in seg) / max(1, len(seg))
                if body * 4.0 > peak:                    # body within 6 dB of the peak: sustained
                    e = body
            if e > 0:
                val = round(10.0 * math.log10(e / 32768.0 ** 2), 2)
    except (OSError, EOFError, ValueError, wave.Error):
        val = None
    _LEVELS[key] = val
    return val


def _zone_level(z: dict):
    lv = _sample_level(z['file'], z.get('offset', 0) or 0) if z.get('file') else None
    return None if lv is None else lv + float(z.get('gain', 0.0))


def _stack_groups(ins: Instrument, only: str | None = None) -> dict:
    """{swLast: {(lo, hi): [zones]}} of the non-release zones (from files under `only`, a path fragment)."""
    groups: dict = {}
    for z in ins.params.get('samples') or []:
        if z.get('trigger') == 'release' or not z.get('file'):
            continue
        if only and only not in z['file'].replace('\\', '/'):
            continue
        groups.setdefault(z.get('swLast'), {}).setdefault((z.get('lo', 0), z.get('hi', 127)), []).append(z)
    return groups


def _even_notes(ins: Instrument, max_db: float = 10.0) -> Instrument:
    """Even out the note-to-note level of a sampled instrument (read now): per articulation, the loudest layer of
    every key range is measured from its samples (as played: file level + zone gain) and the whole range (all its
    layers) moved onto a straight line over the keyboard - the register's natural trend stays, the jumps between
    single recordings go (VSCO 2 CE notes differ up to 15 dB: a line would jump; SSO a few dB). Corrections are
    capped at +-max_db; the mean level of the articulation does not change. A key range is judged by the layer that
    sounds at the default dynamics (mf: velocity / lane ~76) - a range recorded with one layer only must match the
    others where they are played, not their ff layer."""
    ins.expand()
    ref = int(round(127 * float(ins.params.get('dynamics', DYN['mf']))))
    for regions in _stack_groups(ins).values():
        for zs in regions.values():                  # round robins of one layer: to their mean level
            same: dict = {}
            for z in zs:
                if any(k in z for k in ('lorand', 'hirand', 'seqPosition')):
                    same.setdefault((z.get('vello', 0), z.get('velhi', 127)), []).append(z)
            for rr in same.values():
                lv = [(z, _zone_level(z)) for z in rr]
                lv = [(z, x) for z, x in lv if x is not None]
                if len(lv) < 2:
                    continue
                mean = sum(x for _, x in lv) / len(lv)
                for z, x in lv:
                    corr = max(-8.0, min(8.0, mean - x))
                    if abs(corr) >= 0.05:
                        z['gain'] = round(min(48.0, float(z.get('gain', 0.0)) + corr), 3)
        pts = []
        for (lo, hi), zs in regions.items():
            at = [z for z in zs if z.get('vello', 0) <= ref <= z.get('velhi', 127)] or zs
            lv = [x for x in (_zone_level(z) for z in at) if x is not None]
            if lv:
                pts.append(((lo + hi) / 2.0, max(lv), (lo, hi)))
        if len(pts) < 3:
            continue
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx > 0 else 0.0
        slope = max(-0.3, min(0.3, slope))         # dB per semitone: a register trend, not a jump
        for x, y, reg in pts:
            corr = max(-max_db, min(max_db, my + slope * (x - mx) - y))
            if abs(corr) < 0.05:
                continue
            for z in regions[reg]:
                z['gain'] = round(min(48.0, float(z.get('gain', 0.0)) + corr), 3)
    return ins


def _level_layers(ins: Instrument, max_range: float = 14.0) -> Instrument:
    """Read a (lazy) sampler now and set the velocity layers of VSCO 2 CE programs (from their samples) for a live
    dynamics stack (layers='dynamics'). VSCO 2 boosts its soft layers by 11-29 dB so that velocity alone sets the
    level; as a dynamics stack that is wrong in both directions: kept, a crescendo from the p to the f recording gets
    QUIETER; undone, the raw recordings lie 10-35 dB apart and the lane swings 50 dB (a tremolo swelling out of
    silence). So each layer is placed under the loudest layer of its key range by the MEDIAN recorded distance of
    its layer (per articulation, measured from the samples: one smooth crescendo over the whole keyboard), scaled so
    the softest layer sits at most `max_range` dB under the loudest ('dynrange' adds level on top). The loudest
    layer keeps its level (then _even_notes evens the key ranges)."""
    ins.expand()
    for regions in _stack_groups(ins, only='/vsco2-ce/').values():
        dist: dict = {}
        tops: dict = {}
        for reg, zs in regions.items():
            layers: dict = {}
            for z in zs:
                layers.setdefault((z.get('vello', 0), z.get('velhi', 127)), []).append(z)
            if len(layers) < 2:
                continue
            top_key = max(layers, key=lambda k: (k[1], k[0]))
            raw_top = [x for x in (_sample_level(z['file'], z.get('offset', 0) or 0) for z in layers[top_key])
                       if x is not None]
            if not raw_top:
                continue
            played_top = max(x for x in (_zone_level(z) for z in layers[top_key]) if x is not None)
            tops[reg] = (layers, top_key, played_top)
            rt = max(raw_top)
            for k, zl in layers.items():
                if k == top_key:
                    continue
                raw = [x for x in (_sample_level(z['file'], z.get('offset', 0) or 0) for z in zl) if x is not None]
                if raw:
                    dist.setdefault(k, []).append(min(0.0, max(raw) - rt))
        if not dist:
            continue
        med = {k: sorted(v)[len(v) // 2] for k, v in dist.items()}
        low = min(med.values())
        scale = min(1.0, max_range / -low) if low < 0 else 1.0
        for reg, (layers, top_key, played_top) in tops.items():
            for k, zl in layers.items():
                if k == top_key or k not in med:
                    continue
                target = played_top + med[k] * scale
                for z in zl:
                    raw = _sample_level(z['file'], z.get('offset', 0) or 0)
                    if raw is None:
                        continue
                    z['gain'] = round(min(48.0, target - raw), 3)
    return ins


def _programs(path: str, labels: dict) -> dict:
    """sfz_multi programs {our name: {'path', 'articulation'}} from one keyswitch (KS) file of a library."""
    return {name: {'path': path, 'articulation': label} for name, label in labels.items()}


def _gained(progs: dict, gains: dict | None) -> dict:
    """Program dicts with the calibrated level of each articulation ('gain' dB): short articulations brought to
    about the loudness of the sustain at the same dynamics (staccato / spiccato -1 dB, pizzicato -2, tremolo and
    marcato level with it), measured per role (8ths vs held notes, 3 s loudness)."""
    out = {}
    for k, v in progs.items():
        d = dict(v) if isinstance(v, dict) else {'path': v}
        g = (gains or {}).get(k)
        if g:
            d['gain'] = round(d.get('gain', 0.0) + g, 2)
        out[k] = d
    return out


def _packs_of(path: str) -> tuple:
    """The sample packs a program path needs (VPO scripts read their WAVs from 'vpo-wav')."""
    pack = path.split('/')[1] if path.startswith('samples/') else ''
    return (pack, 'vpo-wav') if pack.startswith('vpo-scripts') else ((pack,) if pack else ())


def _sso(path: str, labels: dict, gains: dict | None = None, sustain: str | None = None,
         fallback_gain: float = 0.0, **params):
    """A Sonatina Symphonic Orchestra 4.0 'Performance' keyswitch program as one instrument with our articulation
    names; its mod-wheel dynamics (24 dB of level + a low-pass opening from 1.1 to 5.9 kHz) play live from
    'dynamics'; velocity sets the attack speed only. Sustains loop (the WAVs' smpl loops). sustain='samples/...sfz':
    the sustain comes from that program instead (where the SSO loops click: violas, celli, basses, oboes), with its
    velocity layers at their recorded levels and the SSO dynamics curve. When that program's pack is not installed,
    the SSO sustain plays (at fallback_gain dB) - the preset still builds, a few loop points may click softly."""
    use_alt = bool(sustain) and all(installed(k) for k in _packs_of(sustain))

    def build():
        p = {'dynamics': DYN['mf'], 'polyphony': 128}
        p.update(params)
        progs = _programs(path, labels)
        if sustain and not use_alt:
            g = dict(gains or {})
            g['sustain'] = fallback_gain
            return _even_notes(inst.sfz_multi(_gained(progs, g), lazy=True, **p))
        if sustain:
            progs = {'sustain': {'path': sustain}, **{k: v for k, v in progs.items() if k != 'sustain'}}
            ins = inst.sfz_multi(_gained(progs, gains), lazy=True, **p)
            return _even_notes(_follow_dynamics(_level_layers(ins), ('sustain',)))
        return _even_notes(inst.sfz_multi(_gained(progs, gains), lazy=True, **p))
    return build


def _vsco(programs: dict, gains: dict | None = None, **params):
    """VSCO 2 CE programs (one .sfz per articulation) as one instrument: velocity layers turned into a live
    dynamics stack at their recorded levels (layers='dynamics': a held note crossfades p -> f and grows louder),
    dynrange = extra level range of the lane on top of the recordings."""
    def build():
        p = {'layers': 'dynamics', 'xfspread': 2, 'dynrange': 12, 'dyntone': 0.4, 'velsens': 0.35,
             'dynamics': DYN['mf'], 'polyphony': 96}
        p.update(params)
        progs = {k: (VSCO + v if isinstance(v, str) else {**v, 'path': VSCO + v['path']}) for k, v in programs.items()}
        return _even_notes(_level_layers(inst.sfz_multi(_gained(progs, gains), lazy=True, **p)))
    return build


def _sfz(path: str, **params):
    def build():
        return inst.sfz(path, lazy=True, **params)
    return build


def _vsco_multi(programs: dict, **params):
    """VSCO programs with velocity layers kept (struck instruments: timpani hit / roll)."""
    def build():
        progs = {k: VSCO + v for k, v in programs.items()}
        return inst.sfz_multi(progs, lazy=True, **params)
    return build


# SSO Performance keyswitch labels -> our names (aliases: spiccato -> Staccato where the set has no spiccato)
_SSO_SECTION = {'sustain': 'Sustain', 'staccato': 'Staccato', 'spiccato': 'Staccato', 'marcato': 'Marcato',
                'pizzicato': 'Pizzicato', 'tremolo': 'Tremolo', 'col legno': 'Col Legno', 'harmonics': 'Harmonics'}
_SSO_BASSES = {k: v for k, v in _SSO_SECTION.items() if k != 'harmonics'}
_SSO_BRASS = {'sustain': 'Sustain (looped)', 'marcato': 'Marcato (looped)', 'staccato': 'Staccato'}
_SSO_HORNS = {'sustain': 'Sustain', 'marcato': 'Marcato', 'staccato': 'Staccato'}
_SSO_FLUTES = {'sustain': 'Sustain (looped)', 'marcato': 'Marcato (looped)', 'staccato': 'Staccato'}
_SSO_REEDS = {'sustain': 'Sustain (looped)', 'staccato': 'Staccato'}


def _names(labels: dict) -> tuple:
    return tuple(labels)


# --------------------------------------------------------------------------------------------- the hall

def _hall(song, kind: str, *, fallback: dict, bus_id: str = 'hall'):
    """The one shared return: a convolution space from Voxengo IM Reverbs (modelled real rooms) when installed,
    else the algorithmic hall with `fallback` params. kind: 'chamber' (the Vienna Musikverein IR, x1.1: ~1.6 s),
    'concert' (x1.25: ~1.9 s), 'film' (x1.5: ~2.3 s, a scoring stage), 'church' (St Nicolaes, ~3.6 s). The return is
    100 % wet, high-passed at 110-150 Hz (centred lows), with -3 dB at 320 Hz and -2 dB at 1 kHz (no boxy tail) and
    +2.5 dB air above 7 kHz (the recipe: brighten the hall before single parts)."""
    if installed('voxengo-im-reverbs'):
        ir, p = {
            'chamber': ('Musikvereinsaal.wav', dict(stretch=1.1, predelay=12, lowcut=120, highcut=12000, width=1.4,
                                                    gain=-5.0)),
            'concert': ('Musikvereinsaal.wav', dict(stretch=1.25, predelay=18, lowcut=110, highcut=14000, width=1.4,
                                                    gain=-8.0)),
            'film': ('Musikvereinsaal.wav', dict(stretch=1.5, predelay=24, lowcut=130, highcut=13000, width=1.5,
                                                 gain=-8.0)),
            'church': ('St Nicolaes Church.wav', dict(predelay=15, lowcut=150, highcut=12000, width=1.0, gain=-4.5)),
        }[kind]
        chain = [fx.convolver(ir=VOX + ir, mix=1.0, **p),
                 fx.eq({'peak1.freq': 320, 'peak1.gain': -3.0, 'peak1.q': 0.8, 'peak2.freq': 1000, 'peak2.gain': -2.0,
                        'peak2.q': 0.7, 'high.freq': 7000, 'high.gain': 2.5})]
        return song.bus(bus_id, fx=chain), f"convolution: Voxengo IM {ir[:-4]} ({kind})"
    return song.hall(bus_id, **fallback), 'algorithmic hall (voxengo-im-reverbs not installed)'


# --------------------------------------------------------------------------------------------- building

def _coerce_sound(snd):
    if callable(snd) and not isinstance(snd, (Instrument, Patch)):
        return snd()
    return snd


def _build(song, preset: str, table: dict, *, without, sounds, ids, hall_kind: str, hall_fallback: dict,
           analysis: dict, notes: str, master: str = 'classical') -> Band:
    without = set(without or ())
    sounds = dict(sounds or {})
    ids = dict(ids or {})
    band = Band(song, preset, notes=notes, analysis=analysis)
    bus_id, n = 'hall', 1            # a second band on the same song gets its own hall ('hall_<preset>')
    while bus_id in song.buses or bus_id in song.tracks:
        n += 1
        bus_id = f"hall_{preset}" if n == 2 else f"hall_{preset}{n}"
    hall, hall_desc = _hall(song, hall_kind, fallback=hall_fallback, bus_id=bus_id)
    band.bus('hall', hall)
    info = {'articulations': {}, 'range': {}, 'sweet': {}, 'lead_ms': {}, 'kind': {}, 'mono': [], 'vibrato': {},
            'seating': {}, 'sound': {}, 'dyn': dict(DYN), 'hall': hall_desc}
    for role, r in table.items():
        if role in without:
            continue
        custom = role in sounds
        snd = _coerce_sound(sounds[role] if custom else r.sound)
        chain = [fx.eq({'hp.freq': r.hp, 'hp.slope': 24, 'high.freq': 6000, 'high.gain': r.shelf, **r.eq})]
        chain.append(fx.width(width=r.width, monobass=r.monobass) if r.monobass else fx.width(width=r.width))
        chain.extend(r.extra_fx)
        t = song.track(ids.get(role, role), snd, fx=chain, pan=r.pan, gain_db=r.gain, sends={hall: r.send})
        band.add(role, t)
        sampler = getattr(t.instrument, 'type', '') == 'sampler'
        kind = r.kind
        if custom:
            arts = art.available(t) if sampler else []
            if kind == 'sustain' and not sampler:
                kind = 'plain'       # no dynamics lane (sf2 / synth): velocity is the dynamics, perform() plays notes
        else:
            arts = list(r.arts)
        info['articulations'][role] = arts
        info['range'][role] = r.rng
        info['sweet'][role] = r.sweet
        info['lead_ms'][role] = r.lead_ms
        info['kind'][role] = kind
        info['vibrato'][role] = r.vib
        if r.mono and not custom:
            info['mono'].append(role)
        info['seating'][role] = {'pan': r.pan, 'width': r.width, 'hall_send': r.send, 'high_shelf': r.shelf}
        info['sound'][role] = 'custom' if custom else r.desc
    if any(getattr(f, 'type', '') == 'limiter' for f in song.master.fx):
        pass                         # the master already has its chain (another band, the song): keep it
    elif master == 'classical':
        song.master.add(fx.limiter(ceiling=-1.0, release=300))
    elif master == 'film':
        # a film mix is brighter and less boxy than the raw sample sets: a broad mid dip and an air shelf, 1-2 dB of
        # slow glue, the limiter (ceiling -1.2 dB: the true peak stays <= -1 dBTP)
        song.master.add(fx.eq({'peak2.freq': 1100, 'peak2.gain': -3.5, 'peak2.q': 0.6, 'peak1.freq': 400,
                               'peak1.gain': -2.5, 'peak1.q': 0.7, 'high.freq': 7500, 'high.gain': 4.0}),
                        fx.compressor(threshold=-16, ratio=1.6, knee=10, attack=30, release=400, detector='rms',
                                      keyhp=120, makeup=1.0),
                        fx.limiter(ceiling=-1.2, release=200))
    band.info = info
    return band


# --------------------------------------------------------------------------------------------- string quartet

def _quartet_table() -> dict:
    vsco = installed('vsco2-ce')
    if vsco:
        v1 = _Role(_vsco({'sustain': 'SViolinVib.sfz', 'legato': 'SViolinVib.sfz', 'spiccato': 'SViolinSpic.sfz',
                          'staccato': 'SViolinSpic.sfz', 'pizzicato': 'SViolinPizz.sfz',
                          'tremolo': 'SViolinTrem.sfz'},
                         gains={'spiccato': -1.8, 'staccato': -1.8, 'pizzicato': -5.8, 'tremolo': 0.3},
                         mono='legato', legatotime=70, dynrange=10, xfspread=1, polyphony=32),
                   arts=('sustain', 'legato', 'spiccato', 'staccato', 'pizzicato', 'tremolo'),
                   desc='VSCO 2 CE solo violin (vibrato sustain p/f layers crossfaded live, spiccato, pizzicato, '
                        'tremolo), a legato player')
    else:
        v1 = _Role(_sso(SSO_STR + 'Violin Solo 1 KS.sfz',
                        {'sustain': 'Sustain (looped)', 'legato': 'Legato', 'marcato': 'Marcato (looped)',
                         'spiccato': 'Spiccato', 'staccato': 'Staccato', 'pizzicato': 'Pizzicato',
                         'harmonics': 'Harmonics'}, mono='legato', legatotime=70, polyphony=32),
                   arts=('sustain', 'legato', 'marcato', 'spiccato', 'staccato', 'pizzicato', 'harmonics'),
                   desc='SSO solo violin 1 (fallback: vsco2-ce not installed)')
    v1.pan, v1.width, v1.send, v1.hp, v1.lead_ms, v1.rng, v1.sweet, v1.mono, v1.vib, v1.eq = (
        -0.48, 0.7, -9.0, 180, 25, ('G3', 'C7'), ('G3', 'E6'), True, 8.0,
        {**_pres(-3.5), **_honk(-2.0), **_air(2.0), **_mud(-1.5, 420)})
    v2 = _Role(_sso(SSO_STR + 'Violin Solo 2 KS.sfz',
                    {'sustain': 'Sustain', 'non-vibrato': 'Sustain Non-Vibrato', 'legato': 'Legato',
                     'marcato': 'Marcato', 'spiccato': 'Spiccato', 'staccato': 'Staccato', 'pizzicato': 'Pizzicato',
                     'tremolo': 'Tremolo', 'harmonics': 'Harmonics'},
                    gains={'non-vibrato': 0.0, 'marcato': 7.0, 'spiccato': -3.3, 'staccato': 0.1, 'pizzicato': -2.3,
                           'tremolo': 3.3}, mono='legato', legatotime=70, polyphony=32),
               pan=-0.14, width=0.7, send=-9.0, hp=180, lead_ms=40, rng=('G3', 'C7'), sweet=('G3', 'D6'), mono=True,
               vib=6.0, eq={**_pres(-5.0, 3200), **_mud(-1.5, 450), **_honk(-1.5), **_air(1.5)},
               arts=('sustain', 'non-vibrato', 'legato', 'marcato', 'spiccato', 'staccato', 'pizzicato', 'tremolo',
                     'harmonics'),
               desc='SSO 4.0 solo violin 2 (looped vibrato / non-vibrato sustains, legato, marcato, spiccato, '
                    'staccato, pizzicato, tremolo, harmonics; mod-wheel dynamics), a legato player')
    va_labels = {'sustain': 'Sustain', 'legato': 'Legato', 'marcato': 'Marcato', 'staccato': 'Staccato',
                 'spiccato': 'Staccato', 'pizzicato': 'Pizzicato', 'harmonics': 'Harmonics'}
    vc_labels = dict(va_labels)
    va_progs = _gained(_programs(SSO_STR + 'Viola Solo KS.sfz', va_labels),
                       {'marcato': 3.8, 'staccato': -4.9, 'spiccato': -4.9, 'pizzicato': -2.4})
    vc_progs = _gained(_programs(SSO_STR + 'Cello Solo KS.sfz', vc_labels),
                       {'marcato': -1.1, 'staccato': -5.0, 'spiccato': -5.0, 'pizzicato': -6.5})
    arts_va = tuple(va_labels)
    if vsco:          # the solo sets have no tremolo: a desk of the VSCO chamber section, a little quieter
        va_progs['tremolo'] = {'path': VSCO + 'ViolaEnsTrem.sfz', 'gain': 0.1}
        vc_progs['tremolo'] = {'path': VSCO + 'CelloEnsTrem.sfz', 'gain': -1.2}
        arts_va = arts_va + ('tremolo',)

    def multi(progs, **p):
        def build():
            q = {'dynamics': DYN['mf'], 'polyphony': 32, 'mono': 'legato', 'legatotime': 80, 'layers': 'dynamics',
                 'xfspread': 1}
            q.update(p)
            ins = inst.sfz_multi(progs, lazy=True, **q)
            if 'tremolo' in progs:
                ins = _level_layers(_follow_dynamics(ins, ('tremolo',)))
            return _even_notes(ins)
        return build

    va = _Role(multi(va_progs), pan=0.18, width=0.6, send=-8.5, hp=110, lead_ms=40, rng=('C3', 'E6'),
               sweet=('C3', 'C5'), mono=True, vib=6.0, arts=arts_va,
               eq={**_mud(-3.5, 350), **_pres(-1.5), **_honk(-1.0)},
               desc='SSO 4.0 solo viola (looped sustain, legato, marcato, staccato, pizzicato, harmonics; mod-wheel '
                    'dynamics)' + (' + VSCO desk tremolo' if vsco else '') + ', a legato player')
    vc = _Role(multi(vc_progs), pan=0.42, width=0.5, send=-8.5, hp=45, lead_ms=40, rng=('C2', 'C6'),
               sweet=('C2', 'A4'), mono=True, vib=6.0, arts=arts_va, monobass=120,
               eq={**_mud(-2.5, 300), **_body(3.0)},
               desc='SSO 4.0 solo cello (looped sustain, legato, marcato, staccato, pizzicato, harmonics; mod-wheel '
                    'dynamics)' + (' + VSCO desk tremolo' if vsco else '') + ', a legato player')
    return {'violin1': v1, 'violin2': v2, 'viola': va, 'cello': vc}


_QUARTET_GAIN = {'violin1': 1.8, 'violin2': -3.9, 'viola': -2.6, 'cello': 1.4}

_QUARTET_NOTES = """\
String quartet: four solo players (monophonic legato samplers: overlapping notes are legato transitions, notes after a
rest attack), seated violin 1 - violin 2 - viola - cello from left to right, in a chamber hall (~1.6 s). Play each
line with orch.perform(b, role, line, at): it marks articulations by note length (short -> staccato / spiccato,
accents vel >= 112 -> marcato where the role has it), ties the phrases (legato), turns velocities into the dynamics
lane (vel 40 p, 78 mf, 95 f, 115 ff; long notes swell), adds a delayed vibrato and a player's timing. Crescendi INSIDE
a held note: pass shapes (['cresc', None, 'swell', ...]) or automate orch.dynamics(). Registers: violins G3-E6 (the E
string above A5 for climaxes), viola C3-C5, cello C2-A4 (D4-A4 = its singing tenor). Double stops are not possible
(one note per player). Articulations: clip.articulate('pizzicato' | 'tremolo' | 'staccato' | 'spiccato' | 'marcato' |
'harmonics' | 'non-vibrato'); band.info['articulations'] per role. Density: one voice each; let the inner voices move
less than the outer ones. Sends: hall -9..-8 dB (close, chamber sound)."""


def string_quartet(song, *, without=(), sounds=None, ids=None, **options) -> Band:
    """String quartet (2 violins, viola, cello): solo instruments with legato, live dynamics and keyswitched
    articulations in a chamber hall."""
    _unknown(options, 'string_quartet', ())
    _require('string_quartet', 'sso')
    table = _quartet_table()
    for k, r in table.items():
        r.gain = _QUARTET_GAIN[k]
    return _build(song, 'string_quartet', table, without=without, sounds=sounds, ids=ids, hall_kind='chamber',
                  hall_fallback=dict(decay=1.6, predelay=14, lowcut=120, highcut=9500, width=1.1, size=0.7),
                  analysis={'profile': 'classical'}, notes=_QUARTET_NOTES)


def _unknown(options: dict, preset: str, allowed) -> None:
    bad = set(options) - set(allowed)
    if bad:
        raise ComposeError(f"band {preset!r}: unknown option(s) {sorted(bad)}; options: {', '.join(allowed) or 'none'}")


# --------------------------------------------------------------------------------------------- chamber orchestra

_VSCO_STRINGS = ('sustain', 'legato', 'spiccato', 'staccato', 'pizzicato', 'tremolo')


_VLN_ENS = {'spiccato': -8.3, 'staccato': -8.3, 'pizzicato': -7.7, 'tremolo': -2.6}   # VSCO violin section


def _vsco_strings(prefix: str, sus: str) -> dict:
    return {'sustain': sus, 'legato': sus, 'spiccato': prefix + 'Spic.sfz', 'staccato': prefix + 'Spic.sfz',
            'pizzicato': prefix + 'Pizz.sfz', 'tremolo': prefix + 'Trem.sfz'}


def _chamber_table() -> dict:
    t = {
        'violins1': _Role(_vsco(_vsco_strings('ViolinEns', 'ViolinEnsSusVib.sfz'), gains=_VLN_ENS),
                          pan=-0.5, width=0.85, send=-7.0, hp=160, lead_ms=70, rng=('G3', 'D6'), sweet=('G3', 'C6'),
                          arts=_VSCO_STRINGS, eq={**_air(3.0), **_mud(-2.0, 400)},
                          desc='VSCO 2 CE violin section (chamber size)'),
        'violins2': _Role(_vsco(_vsco_strings('ViolinEns', 'ViolinEnsSusVib.sfz'), gains=_VLN_ENS, tune=-6),
                          pan=-0.2, width=0.8, send=-7.0, hp=160, lead_ms=70, rng=('G3', 'D6'), sweet=('G3', 'A5'),
                          arts=_VSCO_STRINGS, eq={**_air(2.0), **_pres(-3.0, 3200), **_mud(-2.5, 400)},
                          desc='VSCO 2 CE violin section, 6 ct lower (a second desk)'),
        'violas': _Role(_vsco(_vsco_strings('ViolaEns', 'ViolaEnsSusVib.sfz'),
                              gains={'spiccato': 0.0, 'staccato': 0.0, 'pizzicato': -2.0, 'tremolo': 1.7}),
                        pan=0.18, width=0.75, send=-6.5, hp=110, lead_ms=70, rng=('C3', 'D6'), sweet=('C3', 'C5'),
                        arts=_VSCO_STRINGS, eq={**_mud(-3.0, 350), **_air(1.5)}, desc='VSCO 2 CE viola section'),
        'cellos': _Role(_vsco(_vsco_strings('CelloEns', 'CelloEnsSusVib.sfz'),
                              gains={'spiccato': 4.1, 'staccato': 4.1, 'pizzicato': 1.3, 'tremolo': 2.1}),
                        pan=0.42, width=0.5, send=-7.0, hp=40, lead_ms=70, rng=('C2', 'F5'), sweet=('C2', 'A4'),
                        arts=_VSCO_STRINGS, monobass=120, eq={**_mud(-3.0, 320), **_body(2.0)},
                        desc='VSCO 2 CE cello section'),
        'basses': _Role(_vsco(_vsco_strings('Contrabass', 'ContrabassSusVB.sfz'),
                              gains={'spiccato': -2.6, 'staccato': -2.6, 'pizzicato': -1.8, 'tremolo': -2.8}),
                        pan=0.58, width=0.35, send=-7.0, shelf=-1.0, hp=28, lead_ms=70, rng=('C1', 'C4'),
                        sweet=('E1', 'D3'), arts=_VSCO_STRINGS, monobass=150, eq={**_body(2.5, 90), **_mud(-2.0, 300)},
                        desc='VSCO 2 CE double bass'),
        'flutes': _Role(_vsco({'sustain': 'FluteSusVib.sfz', 'legato': 'FluteSusVib.sfz',
                               'non-vibrato': 'FluteSusNV.sfz', 'staccato': 'FluteStac.sfz'},
                              gains={'non-vibrato': 0.9, 'staccato': 4.3}),
                        pan=-0.15, width=0.6, send=-5.0, shelf=-1.0, hp=220, lead_ms=40, rng=('C4', 'C7'),
                        sweet=('G4', 'G6'), arts=('sustain', 'legato', 'non-vibrato', 'staccato'),
                        desc='VSCO 2 CE flute (two parts: play 2-note chords)'),
        'oboes': _Role(_vsco({'sustain': 'OboeSusVib.sfz', 'legato': 'OboeSusVib.sfz', 'non-vibrato': 'OboeSusNV.sfz',
                              'staccato': 'OboeStac.sfz'}, gains={'non-vibrato': -1.9, 'staccato': -10.0}),
                       pan=0.1, width=0.6, send=-5.0, shelf=-1.0, hp=200, lead_ms=40, rng=('A#3', 'F6'),
                       sweet=('D4', 'D6'), arts=('sustain', 'legato', 'non-vibrato', 'staccato'),
                       desc='VSCO 2 CE oboe (two parts)'),
        'clarinets': _Role(_vsco({'sustain': 'ClarinetSus.sfz', 'legato': 'ClarinetSus.sfz',
                                  'staccato': 'ClarinetStac.sfz'}, gains={'staccato': -2.7}),
                           pan=-0.1, width=0.6, send=-4.5, shelf=-1.0, hp=120, lead_ms=40, rng=('D3', 'F#6'),
                           sweet=('D3', 'C6'), arts=('sustain', 'legato', 'staccato'), eq=_mud(-2.0, 400),
                           desc='VSCO 2 CE clarinet in Bb, sounding pitch (two parts)'),
        'bassoons': _Role(_vsco({'sustain': 'BassoonVib.sfz', 'legato': 'BassoonVib.sfz',
                                 'non-vibrato': 'BassoonSus.sfz', 'staccato': 'BassoonStac.sfz'},
                                gains={'non-vibrato': 2.8, 'staccato': -0.1}),
                          pan=0.15, width=0.5, send=-4.5, shelf=-1.0, hp=50, lead_ms=40, rng=('A#1', 'D#5'),
                          sweet=('A#1', 'G4'), arts=('sustain', 'legato', 'non-vibrato', 'staccato'),
                          eq=_mud(-2.5, 350), desc='VSCO 2 CE bassoon (two parts)'),
        'horns': _Role(_vsco({'sustain': 'FHornSus.sfz', 'legato': 'FHornSus.sfz', 'staccato': 'FHornStac.sfz',
                              'muted': 'FHornMute.sfz'}, gains={'staccato': -2.5, 'muted': -5.9}),
                       pan=-0.3, width=0.7, send=-3.5, shelf=-2.0, hp=60, lead_ms=60, rng=('A1', 'F5'),
                       sweet=('C3', 'C5'), arts=('sustain', 'legato', 'staccato', 'muted'),
                       eq=_mud(-3.0, 380), desc='VSCO 2 CE French horn, 4 dynamic layers (two parts)'),
        'timpani': _Role(_vsco_multi({'hit': 'Timpani.sfz', 'roll': 'TimpaniRolls.sfz'}, polyphony=32),
                         pan=-0.05, width=0.5, send=-3.0, shelf=-1.0, hp=30, rng=('C2', 'C4'), sweet=('D2', 'A3'),
                         arts=('hit', 'roll'), kind='struck', monobass=100,
                         desc='VSCO 2 CE timpani: hits (3 layers x 2 round robins) and rolls (keyswitch roll)'),
    }
    return t


_CHAMBER_GAIN = {'violins1': -3.2, 'violins2': -3.4, 'violas': -11.8, 'cellos': -9.2, 'basses': -2.1,
                 'flutes': -15.1, 'oboes': -3.7, 'clarinets': -8.0, 'bassoons': -9.2, 'horns': -8.4,
                 'timpani': 1.0}

_CHAMBER_NOTES = """\
Chamber orchestra (Haydn / Mozart / early Beethoven size): VSCO 2 CE chamber strings (violins I / II, violas, cellos,
basses), wind pairs (flutes, oboes, clarinets, bassoons: each role plays both parts, 1-2 notes), 2 horns and timpani
in a mid-size hall (~1.6 s). Strings: sustain / spiccato (= staccato) / pizzicato / tremolo; the sustain samples last
7-11 s: re-bow longer notes (orch.rebow(clip, s.tempo, 6)). Winds: sustain / staccato (flutes, oboes, bassoons also
non-vibrato), horns sustain / staccato / muted. Timpani: 'hit' (velocity = dynamics, 3 layers) and 'roll' (keyswitch;
crescendo it with 'instrument.expression' or velocity). Registers: violins I G3-C6, II a third / sixth below, violas
C3-C5, cellos C2-A4 with the basses an octave lower, flutes G4-G6, oboes D4-D6, clarinets D3-C6, bassoons A#1-G4,
horns C3-C5 (sustained harmony, 2 notes), timpani tonic / dominant D2-A3. Dynamics: the lane (orch.perform /
orch.dynamics), strings the backbone at mp-mf, winds colour one dynamic softer, horns p-mf unless heroic. Sends:
strings -7, winds -5..-4.5, horns -3.5, timpani -3."""


def chamber_orchestra(song, *, without=(), sounds=None, ids=None, **options) -> Band:
    """Chamber orchestra: VSCO 2 CE chamber strings, wind pairs, 2 horns and timpani in a mid-size hall."""
    _unknown(options, 'chamber_orchestra', ())
    _require('chamber_orchestra', 'vsco2-ce')
    table = _chamber_table()
    for k, r in table.items():
        r.gain = _CHAMBER_GAIN[k]
    return _build(song, 'chamber_orchestra', table, without=without, sounds=sounds, ids=ids, hall_kind='chamber',
                  hall_fallback=dict(decay=1.7, predelay=16, lowcut=110, highcut=9000, width=1.2, size=0.75),
                  analysis={'profile': 'classical'}, notes=_CHAMBER_NOTES)


# --------------------------------------------------------------------------------------------- symphony orchestra

_SEC_ARTS = ('sustain', 'staccato', 'spiccato', 'marcato', 'pizzicato', 'tremolo', 'col legno', 'harmonics')


# the sustain level of the SSO's own program where the cleaner-looping replacement is not installed
# (vpo-scripts-standard + vpo-wav for violas / cellos / basses, vsco2-ce for the oboes), matched to it at mf
_FB = {'violas': -0.4, 'cellos': 2.4, 'basses': 0.2, 'oboes': -9.0}


def _symphony_table() -> dict:
    vsco = installed('vsco2-ce')
    vpo = all(installed(k) for k in _packs_of(VPO))
    t = {
        'violins1': _Role(_sso(SSO_STR + '1st Violins KS.sfz', _SSO_SECTION,
                               gains={'staccato': -3.9, 'spiccato': -3.9, 'marcato': 4.1, 'pizzicato': -1.0,
                                      'tremolo': 4.4}),
                          pan=-0.5, width=0.9, send=-6.0, hp=150, lead_ms=90, rng=('G3', 'C7'), sweet=('G3', 'E6'),
                          arts=_SEC_ARTS, eq={**_honk(-3.0), **_air(2.5)}, desc='SSO 4.0 1st violins'),
        'violins2': _Role(_sso(SSO_STR + '2nd Violins KS.sfz', _SSO_SECTION,
                               gains={'staccato': -5.3, 'spiccato': -5.3, 'marcato': 5.5, 'pizzicato': -3.7,
                                      'tremolo': 2.0}),
                          pan=-0.22, width=0.85, send=-6.0, hp=150, lead_ms=90, rng=('G3', 'C7'), sweet=('G3', 'A5'),
                          arts=_SEC_ARTS, eq={**_honk(-3.0), **_air(2.0)}, desc='SSO 4.0 2nd violins'),
        'violas': _Role(_sso(SSO_STR + 'Violas KS.sfz', _SSO_SECTION, sustain=VPO + 'Strings/viola-SEC-sustain.sfz',
                             fallback_gain=_FB['violas'],
                             gains={'sustain': -2.6, 'staccato': -3.8, 'spiccato': -3.8, 'marcato': 2.9,
                                    'pizzicato': -5.7, 'tremolo': 3.4}),
                        pan=0.2, width=0.8, send=-5.5, hp=110, lead_ms=90, rng=('C3', 'C6'), sweet=('C3', 'C5'),
                        arts=_SEC_ARTS, eq={**_mud(-1.5, 350), **_honk(-2.0)},
                        desc='SSO 4.0 violas (sustain: the Westlund viola section re-looped by Virtual Playing '
                             'Orchestra)'),
        'cellos': _Role(_sso(SSO_STR + 'Celli KS.sfz', _SSO_SECTION, sustain=VPO + 'Strings/cello-SEC-sustain.sfz',
                             fallback_gain=_FB['cellos'],
                             gains={'sustain': -0.7, 'staccato': -1.9, 'spiccato': -1.9, 'marcato': 3.5,
                                    'pizzicato': -2.1, 'tremolo': 5.6}),
                        pan=0.42, width=0.5, send=-6.0, hp=40, lead_ms=90, rng=('C2', 'C#5'), sweet=('C2', 'A4'),
                        arts=_SEC_ARTS, monobass=120, eq=_body(2.5),
                        desc='SSO 4.0 cellos (sustain: the No Budget Orchestra cello section, VPO loops)'),
        'basses': _Role(_sso(SSO_STR + 'Basses KS.sfz', _SSO_BASSES, sustain=VPO + 'Strings/bass-SEC-sustain.sfz',
                             fallback_gain=_FB['basses'],
                             gains={'sustain': -2.4, 'staccato': -2.4, 'spiccato': -2.4, 'marcato': 2.2,
                                    'pizzicato': -5.8, 'tremolo': 2.1}),
                        pan=0.6, width=0.4, send=-6.0, shelf=-1.0, hp=28, lead_ms=90, rng=('C1', 'C4'),
                        sweet=('E1', 'D3'), arts=_names(_SSO_BASSES), monobass=150, eq=_body(2.0, 100),
                        desc='SSO 4.0 double basses (sustain re-looped by Virtual Playing Orchestra)'),
        'flutes': _Role(_sso(SSO_WW + 'Flutes KS.sfz', _SSO_FLUTES, gains={'marcato': -2.1, 'staccato': -7.0}),
                        pan=-0.15, width=0.6, send=-4.5, shelf=-1.0, hp=220, lead_ms=50, rng=('C4', 'C7'),
                        sweet=('G4', 'G6'), arts=_names(_SSO_FLUTES), desc='SSO 4.0 flutes a2'),
        'oboes': _Role(_sso(SSO_WW + 'Oboes KS.sfz', _SSO_REEDS, gains={'sustain': -5.5, 'staccato': -19.7},
                            sustain=VSCO + 'OboeSusVib.sfz', fallback_gain=_FB['oboes']),
                       pan=0.1, width=0.6, send=-4.5, shelf=-1.0, hp=200, lead_ms=50, rng=('A#3', 'G6'),
                       sweet=('D4', 'D6'), arts=_names(_SSO_REEDS), eq=_honk(-2.5, 1300),
                       desc='SSO 4.0 oboes (sustain: the VSCO 2 CE oboe, long unlooped notes)'),
        'clarinets': _Role(_sso(SSO_WW + 'Clarinets KS.sfz', _SSO_REEDS, gains={'staccato': -8.3}),
                           pan=-0.08, width=0.6, send=-4.0, shelf=-1.0, hp=120, lead_ms=50, rng=('D3', 'F6'),
                           sweet=('D3', 'C6'), arts=_names(_SSO_REEDS), desc='SSO 4.0 clarinets a2 (sounding pitch)'),
        'bassoons': _Role(_sso(SSO_WW + 'Bassoons KS.sfz', _SSO_REEDS, gains={'staccato': -10.3}),
                          pan=0.16, width=0.5, send=-4.0, shelf=-1.0, hp=50, lead_ms=50, rng=('A#1', 'E5'),
                          sweet=('A#1', 'G4'), arts=_names(_SSO_REEDS), desc='SSO 4.0 bassoons a2'),
        'horns': _Role(_sso(SSO_BR + 'Horns KS.sfz', _SSO_HORNS, gains={'marcato': 0.9, 'staccato': -0.2}),
                       pan=-0.32, width=0.8, send=-3.0, shelf=-2.0, hp=60, lead_ms=70, rng=('E2', 'F5'),
                       sweet=('C3', 'C5'), arts=_names(_SSO_HORNS), desc='SSO 4.0 horns a4'),
        'trumpets': _Role(_sso(SSO_BR + 'Trumpets KS.sfz', _SSO_BRASS, gains={'marcato': 0.0, 'staccato': -4.2},
                               dynrange=12),
                          pan=0.14, width=0.6, send=-3.5, shelf=-1.5, hp=150, lead_ms=50, rng=('E3', 'E6'),
                          sweet=('C4', 'G5'), arts=_names(_SSO_BRASS), eq={**_honk(-3.0), **_pres(-1.5)},
                          desc='SSO 4.0 trumpets a3'),
        'trombones': _Role(_sso(SSO_BR + 'Trombones KS.sfz', _SSO_BRASS, gains={'marcato': 2.3, 'staccato': 1.2},
                                dynrange=12),
                           pan=0.34, width=0.6, send=-3.0, shelf=-1.5, hp=60, lead_ms=60, rng=('E2', 'F5'),
                           sweet=('F2', 'F4'), arts=_names(_SSO_BRASS), eq=_honk(-3.0, 1000),
                           desc='SSO 4.0 trombones a3'),
        'tuba': _Role(_sso(SSO_BR + 'Tuba KS.sfz', _SSO_BRASS, gains={'marcato': 1.5, 'staccato': -0.1}),
                      pan=0.46, width=0.4, send=-3.0, shelf=-1.5, hp=25, lead_ms=60, rng=('E1', 'D4'),
                      sweet=('F1', 'F3'), arts=_names(_SSO_BRASS), monobass=150, eq=_body(1.5, 100),
                      desc='SSO 4.0 tuba'),
    }
    if vsco:
        t['timpani'] = _Role(_vsco_multi({'hit': 'Timpani.sfz', 'roll': 'TimpaniRolls.sfz'}, polyphony=32),
                             pan=-0.05, width=0.5, send=-2.5, shelf=-1.0, hp=30, rng=('C2', 'C4'), sweet=('D2', 'A3'),
                             arts=('hit', 'roll'), kind='struck', monobass=100,
                             desc='VSCO 2 CE timpani: hits (3 layers x 2 round robins) and 17-24 s rolls')
        t['percussion'] = _Role(_sfz(VSCO + 'GM-StylePerc.sfz', polyphony=64),
                                pan=0.3, width=0.9, send=-2.5, shelf=-0.5, hp=30, rng=('G#1', 'G#7'),
                                sweet=('C2', 'C6'), kind='struck',
                                desc='VSCO 2 CE orchestral percussion, GM-style keys (see band.info["keys"])')
        t['harp'] = _Role(_sfz(VSCO + 'Harp.sfz', polyphony=64),
                          pan=-0.42, width=0.7, send=-5.0, hp=40, rng=('E1', 'F7'), sweet=('C2', 'C6'), kind='struck',
                          desc='VSCO 2 CE concert harp (rings ~9 s)')
    else:
        t['timpani'] = _Role(_sfz(SSO + 'Percussion/Timpani.sfz', polyphony=32),
                             pan=-0.05, width=0.5, send=-2.5, shelf=-1.0, hp=30, rng=('C2', 'C4'), sweet=('D2', 'A3'),
                             kind='struck', monobass=100, desc='SSO 4.0 timpani (fallback: vsco2-ce not installed)')
        t['percussion'] = _Role(_sfz(SSO + 'Percussion/All Unpitched Percussion.sfz', polyphony=64),
                                pan=0.3, width=0.9, send=-2.5, hp=30, rng=('C2', 'C6'), sweet=('C2', 'C6'),
                                kind='struck', desc='SSO 4.0 unpitched percussion (fallback)')
        t['harp'] = _Role(_sfz(SSO + 'Concert Harp.sfz', polyphony=64),
                          pan=-0.42, width=0.7, send=-5.0, hp=40, rng=('C2', 'C7'), sweet=('C2', 'C6'), kind='struck',
                          desc='SSO 4.0 concert harp (fallback)')
    t['celesta'] = _Role(_sfz(SSO + 'Percussion/Celeste.sfz', polyphony=64),
                         pan=-0.36, width=0.6, send=-5.0, hp=150, rng=('C4', 'C8'), sweet=('C5', 'C7'), kind='struck',
                         desc='SSO 4.0 celesta')
    if not vpo:
        for r in ('violas', 'cellos', 'basses'):
            t[r].desc = f"SSO 4.0 {r} (fallback: the SSO sustain - vpo-scripts-standard / vpo-wav not installed)"
    if not vsco:
        t['oboes'].desc = 'SSO 4.0 oboes (fallback: the SSO sustain - vsco2-ce not installed)'
    return t


_SYMPHONY_GAIN = {'violins1': -8.4, 'violins2': -9.0, 'violas': -10.2, 'cellos': -11.1, 'basses': -12.6,
                  'flutes': -10.8, 'oboes': 2.9, 'clarinets': -11.6, 'bassoons': -9.9, 'horns': -15.2,
                  'trumpets': -7.1, 'trombones': -10.0, 'tuba': -15.4, 'timpani': 1.0, 'percussion': -15.5,
                  'harp': -8.7, 'celesta': -16.5}

PERCUSSION_KEYS = {'bass_drum': 36, 'bass_drum_rub': 32, 'snare': 38, 'snare_roll': 39, 'snare_off': 40,
                   'snare_roll_off': 41, 'side_stick': 37, 'tam_tam': 46, 'tam_tam_scrape': 42, 'crash': 49,
                   'sus_cymbal': 51, 'sus_cymbal_stick': 59, 'cymbal_roll_short': 47, 'cymbal_roll': 48,
                   'cymbal_roll_long': 50, 'tambourine': 54, 'tambourine_roll': 55, 'tambourine_shake': 53,
                   'triangle': 81, 'triangle_muted': 80, 'sleigh_bells': 82, 'bell_tree': 83, 'anvil': 67,
                   'ratchet': 70, 'claves': 75, 'woodblock_hi': 76, 'woodblock_lo': 77, 'cowbell': 56}
"""Keys of the VSCO 2 CE GM-style percussion (symphony / film 'percussion' role): b.percussion.note(orch.
PERCUSSION_KEYS['crash'], at) or drums({'crash': 'x...'}) grids. The suspended-cymbal rolls swell to their peak in
1.4 / 3.5 / 7.1 s (cymbal_roll_short / cymbal_roll / cymbal_roll_long), then ring: start them that long before the
downbeat. tam_tam (gong) rings ~30 s, bass_drum 1.5 s."""

_SYMPHONY_NOTES = """\
Symphony orchestra (Brahms / Tchaikovsky / Dvorak size): Sonatina Symphonic Orchestra 4.0 sections - violins I / II,
violas, cellos, basses; flutes, oboes, clarinets, bassoons (a2: each role plays 1-3 parts); 4 horns, 3 trumpets, 3
trombones, tuba - with VSCO 2 CE timpani (hit / roll keyswitch), orchestral percussion (orch.PERCUSSION_KEYS: bass drum
36, crash 49, cymbal rolls 47 / 48 / 50, tam-tam 46, triangle 81 ...) and harp, and the SSO celesta, seated in a concert
hall (~1.9 s). Every sustaining section is a mod-wheel instrument: the dynamics lane IS its level (~20 dB from pp to ff)
and tone - play lines with orch.perform (velocity -> the lane) or write the lane with orch.dynamics; never leave a
climax at the default 'mf'. The sustains of violas, cellos and basses are the Virtual Playing Orchestra re-loops (the
SSO loops click), the oboes' sustain the VSCO 2 oboe - all on the same lane (the SSO's own sustains when those packs are
missing: band.info['sound']). Articulations per section: strings sustain / staccato (= spiccato) / marcato / pizzicato /
tremolo / col legno / harmonics (basses no harmonics); flutes sustain / marcato / staccato; oboes, clarinets, bassoons
sustain / staccato; horns, trumpets, trombones, tuba sustain / marcato / staccato. Balance (calibrated at mf: one line
per string / wind section, the chords brass sections usually play): the brass chords > a string section line > a
woodwind line (~3 dB softer: winds colour, double them to carry a tune) - in a tutti write the brass one dynamic under
the strings (f against ff). Registers: violins I G3-E6 (melody), II and violas the harmony G3-A5 / C3-C5, cellos C2-A4
with the basses an octave below (E1-D3), flutes G4-G6, oboes D4-D6, clarinets D3-C6, bassoons A#1-G4, horns C3-C5
(4-part pads, unison themes), trumpets C4-G5, trombones F2-F4, tuba F1-F3 (sparingly), timpani D2-A3, harp C2-C6
(arpeggios), celesta C5-C7 (doubling a melody). Densities: strings carry, winds colour (doubling at the unison /
octave), brass enters for weight, percussion only at arrivals. Sends: strings -6, woodwinds -4.5..-4, horns -3, brass
-3.5..-3, timpani / percussion -2.5 (the back rows are wetter and darker). Automate the hall send +2..4 dB on a final
chord before a general pause."""


def symphony_orchestra(song, *, without=(), sounds=None, ids=None, **options) -> Band:
    """Symphony orchestra: SSO 4.0 full sections, 4 horns, 3 trumpets, 3 trombones, tuba, timpani, percussion,
    harp and celesta in a concert hall."""
    _unknown(options, 'symphony_orchestra', ())
    _require('symphony_orchestra', 'sso')
    table = _symphony_table()
    for k, r in table.items():
        r.gain = _SYMPHONY_GAIN[k]
    band = _build(song, 'symphony_orchestra', table, without=without, sounds=sounds, ids=ids, hall_kind='concert',
                  hall_fallback=dict(decay=2.1, predelay=22, lowcut=110, highcut=9000, damping=6000, width=1.2,
                                     size=0.85),
                  analysis={'profile': 'classical'}, notes=_SYMPHONY_NOTES)
    band.info['keys'] = dict(PERCUSSION_KEYS)
    return band


# --------------------------------------------------------------------------------------------- film orchestra

_FILM_GAIN = {'violins1': -3.3, 'violins2': -4.0, 'violas': -5.2, 'cellos': -6.1, 'basses': -7.6,
              'flutes': -5.8, 'oboes': 7.9, 'clarinets': -6.6, 'bassoons': -4.9, 'horns': -10.2,
              'trumpets': -2.1, 'trombones': -5.0, 'low_brass': -6.4, 'tuba': -10.4, 'timpani': 6.0,
              'percussion': -10.5, 'drums': 0.0, 'choir': -4.6, 'harp': -3.7, 'sub': 2.1, 'pulse': -2.1}


_CHOIR_OH_LEVEL = -4.2     # the NBO choir's level: as loud as the SSO chorus at mf (its lane is 'expression')

# film seating: the same stage, recorded wider (a scoring stage with spaced main microphones)
_FILM_WIDTH = {'violins1': 1.15, 'violins2': 1.1, 'violas': 1.0, 'horns': 1.1, 'trumpets': 0.8, 'trombones': 0.8,
               'harp': 0.9, 'flutes': 0.8, 'clarinets': 0.8, 'oboes': 0.8, 'bassoons': 0.7}


def _film_table(hybrid: bool, choir: str = 'aah') -> dict:
    t = _symphony_table()
    t.pop('celesta')
    for role, w in _FILM_WIDTH.items():
        t[role].width = w
    # low brass: the SSO bass trombone for braams and pedal tones, under the trombones
    t['low_brass'] = _Role(_sso(SSO_BR + 'Bass Trombone Solo KS.sfz',
                                {'sustain': 'Sustain (looped)', 'marcato': 'Marcato (looped)', 'staccato': 'Staccato'}),
                           pan=0.28, width=0.5, send=-3.5, shelf=-1.5, hp=30, lead_ms=60, rng=('A#0', 'F4'),
                           sweet=('C1', 'C3'), arts=('sustain', 'marcato', 'staccato'), monobass=150,
                           desc='SSO 4.0 bass trombone (braams: marcato fff clusters / open fifths with tuba and '
                                'horns)')
    # epic drums: GM taikos (MuseScore General: pitched, low keys = the big drums) - keep out of the hall's lows
    t['drums'] = _Role(lambda: inst.sf2('Taiko Drum', file=library.SAMPLES.joinpath(
                           'musescore-general-sf2', 'MuseScore_General.sf2').as_posix(), release=1.5, width=1.3)
                       if installed('musescore-general-sf2') else inst.sf2('Taiko Drum', release=1.5, width=1.3),
                       pan=0.0, width=1.0, send=-9.0, hp=28, rng=('C1', 'C4'), sweet=('C1', 'G2'), kind='struck',
                       desc='taiko ensemble (GM Taiko Drum, MuseScore General; pitch = drum size: C1-G2 huge, '
                            'C3 medium)')
    if choir == 'oh' and installed('nbo-2'):
        t['choir'] = _Role(_sfz('samples/nbo-2/Choir/choir.sfz', polyphony=128, level=_CHOIR_OH_LEVEL),
                           pan=0.0, width=1.0, send=-3.0, shelf=-1.0, hp=120, lead_ms=80, rng=('G2', 'C6'),
                           sweet=('C3', 'A5'), desc='No Budget Orchestra 2 choir "oh" (clean loops; velocity + '
                                                    'expression dynamics)')
    else:
        t['choir'] = _Role(_sfz(SSO + 'Chorus - Performance/Large Chorus.sfz', dynamics=DYN['mf'], polyphony=128),
                           pan=0.0, width=1.0, send=-3.0, shelf=-1.0, hp=120, lead_ms=80, rng=('G2', 'C6'),
                           sweet=('C3', 'A5'), desc='SSO 4.0 large chorus "aah" (mod-wheel dynamics)')
    if hybrid:
        t['sub'] = _Role(lambda: inst.va(osc1__wave='sine', osc2__level=0, cutoff=400, filter__env=0,
                                         amp__attack=0.004, amp__decay=1.6, amp__sustain=0.0, amp__release=0.4,
                                         amp__velocity=0.6, pitchbend=0, drift__pitch=0, level=-2),
                         pan=0.0, width=0.0, send=-60.0, hp=20, rng=('A0', 'C2'), sweet=('C1', 'G1'), kind='synth',
                         extra_fx=(fx.eq({'lp.freq': 180, 'lp.slope': 24}),),
                         desc='synth sub hit: a decaying sine (30-45 Hz) on the downbeats with the drums / braams')
        t['pulse'] = _Role(lambda: inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.6, osc2__fine=7,
                                           cutoff=900, resonance=0.25, filter__env=2.5, fenv__decay=0.18,
                                           fenv__sustain=0.1, amp__attack=0.002, amp__decay=0.25, amp__sustain=0.35,
                                           amp__release=0.12, unison=3, unison__detune=0.2, level=-6),
                           pan=0.0, width=1.2, send=-12.0, hp=80, rng=('C2', 'C5'), sweet=('A2', 'A3'), kind='synth',
                           desc='synth pulse: a filtered saw ostinato (16ths) under the strings')
    return t


_FILM_NOTES = """\
Film orchestra (Williams / Horner lyrical, or Zimmer hybrid with hybrid=True): the symphony orchestra without celesta
plus 'low_brass' (the SSO bass trombone: braams, pedal tones), 'drums' (a taiko ensemble: low keys C1-G2 are the big
drums, velocity = strength), 'choir' (SSO large chorus 'aah', mod-wheel dynamics; choir='oh': the No Budget Orchestra
choir, clean loops for an exposed pp choir), in a scoring-stage hall (~2.3 s), seated wider, mixed louder under the
'film' profile (-16..-10 LUFS: the master takes 3.5 dB out of the boxy 1.1 kHz and 2.5 dB at 400 Hz, adds 4 dB of air
above 7.5 kHz, 1-2 dB of slow glue and a -1 dBTP limiter). hybrid=True adds 'sub' (a decaying sine hit: play A0-G1
with every big downbeat, it stays out of the hall) and 'pulse' (a filtered synth-saw ostinato, 16ths in A2-A3).
Toolbox: string ostinati (staccato 8ths / 16ths, accents 3+3+2) over a pedal in the basses; low brass + tuba + horns
marcato ff on an open fifth with drums + sub on the downbeat (the braam); horn unison themes (C3-C5), strings in
octaves for the emotional theme, choir doubling the strings an octave up for the epic statement; risers = string
tremolo crescendo (orch.dynamics from 'p' to 'ff') + the cymbal roll (percussion key 48 / 50) into the hit. Dynamics
as for the symphony (a lane per section, velocity = attack only); the drums, percussion and timpani play velocity.
Keep drums and sub out of the reverb (drums -9, sub none)."""


def film_orchestra(song, *, without=(), sounds=None, ids=None, hybrid: bool = False, choir: str = 'aah',
                   **options) -> Band:
    """Film orchestra: symphonic sections + choir, low brass, taiko drums; hybrid=True adds a synth sub and a synth
    pulse. choir='aah' (SSO large chorus, live dynamics; a few loop points click softly when exposed) or 'oh' (No
    Budget Orchestra 2 choir: clean loops, for exposed pianissimo choir)."""
    _unknown(options, 'film_orchestra', ())
    if choir not in ('aah', 'oh'):
        raise ComposeError(f"film_orchestra: choir must be 'aah' or 'oh', got {choir!r}")
    if not hybrid:
        for key, opt in (('sounds', sounds), ('ids', ids)):
            extra = sorted(set(opt or {}) & {'sub', 'pulse'})
            if extra:
                raise ComposeError(f"film_orchestra: {key}= names {extra}, roles that only exist with hybrid=True")
    _require('film_orchestra', 'sso')
    table = _film_table(bool(hybrid), choir)
    for k, r in table.items():
        r.gain = _FILM_GAIN[k]
    band = _build(song, 'film_orchestra', table, without=without, sounds=sounds, ids=ids, hall_kind='film',
                  hall_fallback=dict(decay=2.8, predelay=25, lowcut=120, highcut=8500, damping=5500, width=1.3,
                                     size=0.95),
                  analysis={'profile': 'film'}, notes=_FILM_NOTES, master='film')
    band.info['keys'] = dict(PERCUSSION_KEYS)
    band.info['hybrid'] = bool(hybrid)
    band.info['choir'] = choir
    return band


# --------------------------------------------------------------------------------------------- church organ

_ORGANS = {
    'burea': {
        'pack': 'lars-palo-burea-church',
        'soft': dict(stops=['Rorflojt 8', 'Salicional 8'], manual='Svallverk', stereo='flip'),
        'principal': dict(stops=['Principal 8', 'Oktava 4', 'Oktava 2'], manual='Huvudverk'),
        'full': dict(stops=['Principal 8', 'Oktava 4', 'Oktava 2', 'Mixtur V', 'Trumpet 8'],
                     manual='Huvudverk'),
        'pedal': dict(stops=['Subbas 16', 'Gedakt 8'], manual='pedal', stereo='left'),
        'pedal_full': dict(stops=['Subbas 16', 'Principal 8', 'Oktava 4', 'Basun 16'], manual='pedal',
                           stereo='left'),
        'desc': 'Burea Church, Sweden (Lars Palo, 3 manuals + pedal)',
    },
    'pitea': {
        'pack': 'lars-palo-pitea-mhs',
        'soft': dict(stops=['Fl.Harm. 8', 'Gamba 8', 'V.Celeste 8'], manual='Svallverk'),
        'principal': dict(stops=['Principal 8', 'Oktava 4', 'Oktava 2'], manual='Huvudverk'),
        'full': dict(stops=['Principal 8', 'Oktava 4', 'Oktava 2', 'Mixtur IV', 'Trumpet 8'],
                     manual='Huvudverk'),
        'pedal': dict(stops=['Subbas 16', 'Gedakt 8'], manual='pedal', stereo='left'),
        'pedal_full': dict(stops=['Subbas 16', 'Oktava 8', 'Oktava 4', 'Basun 16'], manual='pedal', stereo='left'),
        'desc': 'Pitea School of Music, Sweden (Lars Palo, 3 manuals + pedal)',
    },
}

_ORGAN_GAIN = {'burea': {'soft': -2.0, 'principal': -11.5, 'full': -10.3, 'pedal': -1.2, 'pedal_full': -7.6},
               'pitea': {'soft': -3.2, 'principal': -10.0, 'full': -9.3, 'pedal': -3.3, 'pedal_full': -9.5}}

_ORGAN_NOTES = """\
Church organ (a GrandOrgue pipe organ, every pipe with its attack, sustain loop and recorded release into the church)
in a big stone church (~3.6 s: give the song Song(..., tail=6)). Registrations are roles - write notes on the role
whose registration you want (switching = moving to another track, the way an organist draws stops): 'soft' (swell
flutes / strings: quiet interludes, accompaniment), 'principal' (the principal chorus 8' 4' 2': hymns, chorales,
counterpoint), 'full' (full organ with mixture and trumpet: climaxes, toccatas, the final chord), 'pedal' (Subbas 16'
+ 8': the bass line C2-C3) and 'pedal_full' (+ 4' and the Basun 16' reed: with 'full'). An organ has no velocity and
no dynamics on a note: loudness is the registration (a 4-note chord: soft ~-30, principal ~-25, full ~-20 LUFS dry;
pedal ~-28, pedal_full ~-24 on a bass line) plus the swell pedal ('instrument.expression' 0..1 on 'soft'). The
recorded pipes already carry the church (spaced microphones: the pedal plays one of them, mono and solid; Burea's soft
stops phase-flipped so they stay in phase). Play legato (overlap / touching notes, voice-led chords), a real bass line
in the pedal, release chords together, leave the church 1-2 beats of silence after a cadence."""


def church_organ(song, *, without=(), sounds=None, ids=None, organ: str = 'burea', tremulant: bool = False,
                 **options) -> Band:
    """Church organ: Lars Palo GrandOrgue registrations (soft / principal / full + pedal) in a big church.
    organ='burea' (default) or 'pitea'; tremulant=True puts the tremulant on the soft registration."""
    _unknown(options, 'church_organ', ())
    if organ not in _ORGANS:
        raise ComposeError(f"church_organ: organ must be one of {', '.join(_ORGANS)}, got {organ!r}")
    o = _ORGANS[organ]
    _require('church_organ', o['pack'])
    src = 'samples/' + o['pack']
    g = _ORGAN_GAIN[organ]

    def organ_role(key, **kw):
        spec = dict(o[key])
        if key == 'soft' and tremulant:
            spec['tremulant'] = True
        return lambda: inst.organ(src, lazy=True, **spec)

    table = {
        'soft': _Role(organ_role('soft'), pan=0.0, width=1.0, send=-9.0, hp=60, gain=g['soft'], rng=('C2', 'G6'),
                      eq=_mud(-3.0, 330),
                      sweet=('C3', 'C6'), kind='organ', desc=f"{o['desc']}: {', '.join(o['soft']['stops'])}"),
        'principal': _Role(organ_role('principal'), pan=0.0, width=1.0, send=-9.0, hp=35, gain=g['principal'],
                           rng=('C2', 'G6'), sweet=('C3', 'C6'), kind='organ',
                           desc=f"{o['desc']}: {', '.join(o['principal']['stops'])}"),
        'full': _Role(organ_role('full'), pan=0.0, width=1.0, send=-9.0, hp=90, gain=g['full'], rng=('C2', 'G6'),
                      sweet=('C2', 'C6'), kind='organ', desc=f"{o['desc']}: {', '.join(o['full']['stops'])}"),
        'pedal': _Role(organ_role('pedal'), pan=0.0, width=1.0, send=-12.0, hp=20, gain=g['pedal'], rng=('C2', 'F4'),
                       eq=_mud(-3.0, 280),
                       sweet=('C2', 'C3'), kind='organ', desc=f"{o['desc']}: pedal {', '.join(o['pedal']['stops'])}"),
        'pedal_full': _Role(organ_role('pedal_full'), pan=0.0, width=1.0, send=-12.0, hp=20, gain=g['pedal_full'],
                            eq=_mud(-2.0, 280),
                            rng=('C2', 'F4'), sweet=('C2', 'C3'), kind='organ',
                            desc=f"{o['desc']}: pedal {', '.join(o['pedal_full']['stops'])}"),
    }
    band = _build(song, 'church_organ', table, without=without, sounds=sounds, ids=ids, hall_kind='church',
                  hall_fallback=dict(decay=4.0, predelay=20, lowcut=150, highcut=8000, damping=5000, width=1.3,
                                     size=1.0),
                  analysis={'profile': 'classical'}, notes=_ORGAN_NOTES)
    band.info['organ'] = organ
    return band


# --------------------------------------------------------------------------------------------- playing helpers

def _roles(band: Band, roles) -> list:
    if isinstance(roles, str):
        roles = [roles]
    return [r for r in roles if r in band.roles]


def _points(points, at=0.0) -> list:
    a0 = float(getattr(at, 'start', at))
    out = []
    for p in points:
        if not isinstance(p, (tuple, list)) or len(p) not in (2, 3):
            raise ComposeError(f"dynamics points are (beat, marking or 0..1[, curve]), got {p!r}")
        b = float(getattr(p[0], 'start', p[0]))
        out.append((a0 + b, dyn(p[1])) + ((p[2],) if len(p) == 3 else ()))
    return out


def dynamics(band: Band, roles, points, at=0.0) -> Band:
    """Write one dynamics curve on several roles (those the band has; others are skipped): a tutti crescendo,
    a subito p, a swell on a held chord. points: [(beat, 'p' | 0..1[, curve]), ...] (+ at: a beat or Section).
        orch.dynamics(b, orch.STRINGS, [(0, 'pp'), (8, 'ff', 'smooth'), (8.5, 'p', 'step')], at=verse)
    Organ, struck, synth and 'plain' roles are skipped (their dynamics are velocity / registration)."""
    pts = _points(points, at)
    for r in _roles(band, roles):
        if band.info.get('kind', {}).get(r, 'sustain') != 'sustain':
            continue
        band[r].automate('instrument.dynamics', pts)
    return band


def ring(band: Band, at, length=2.0, db: float = 4.0, roles=None, back=None, back_beats: float = 0.25) -> Band:
    """Let the hall ring (the recipe's 'automate the room'): raise the hall send of every role (or `roles`) by `db`
    over `length` beats from `at` (a beat or Section) - on the last chord before a general pause or the end, so the
    tail blooms into the silence. It stays raised, unless `back` (a beat or Section: where the music goes on after a
    mid-song fermata) gives it back: the send returns to its seat over the `back_beats` before it (a `back` inside
    the bloom cuts it short: the send falls from where it got)."""
    a0 = float(getattr(at, 'start', at))
    bus = band.buses['hall']
    target = 'send.' + str(getattr(bus, 'id', 'hall'))
    b0 = None if back is None else float(getattr(back, 'start', back))
    if b0 is not None and b0 <= a0 + 1e-9:
        raise ComposeError(f"ring: back={b0:g} must come after the bloom's start ({a0:g})")
    for r in (_roles(band, roles) if roles is not None else list(band.roles)):
        base = band.info['seating'][r]['hall_send']
        top = min(6.0, base + db)
        pts = [(a0, base), (a0 + float(length), top, 'smooth')]
        if b0 is not None:
            pts += [(b0 - float(back_beats), top), (b0, base, 'smooth')]
        band[r].automate(target, pts)
    return band


def lead(clip, bpm: float, ms: float, *, long=0.75) -> Clip:
    """Start the long notes (>= `long` beats, and every note marked with a long articulation: sustain / legato ...)
    `ms` earlier, their ends kept: slow sample attacks then SOUND on the beat. Shorts (staccato, pizzicato ...)
    stay. Marks are kept. Positions are clamped at 0: shift a part into song time (or use perform()) so a note on a
    section's downbeat can move early too."""
    c = as_clip(clip)
    if not ms:
        return c
    d = float(ms) / 1000.0 * float(bpm) / 60.0
    out = []
    for n in c:
        a = art.articulation_of(n)
        if (n.dur >= long - 1e-9 and not art.detached(n)) or (isinstance(a, str) and a in ('sustain', 'legato')):
            start = max(0.0, n.start - d)
            out.append(n._replace(start=start, dur=n.dur + (n.start - start)))
        else:
            out.append(n)
    return Clip._raw(out, c.length)


def rebow(clip, bpm: float, max_seconds: float = 6.0, gap_ms: float = 30.0) -> Clip:
    """Split notes longer than `max_seconds` into repeated notes (a bow change / a breath every max_seconds, the
    new stroke `gap_ms` after the old one ends): long pads on samples that do not loop (VSCO sustains last 7-11 s)
    and a natural re-articulation of held chords. Marks are kept."""
    c = as_clip(clip)
    spb = 60.0 / float(bpm)
    step = max_seconds / spb
    gap = gap_ms / 1000.0 / spb
    out = []
    for n in c:
        if n.dur <= step + 1e-9:
            out.append(n)
            continue
        k = math.ceil(n.dur / step)
        seg = n.dur / k
        for i in range(k):
            s = n.start + i * seg
            d = seg - (gap if i < k - 1 else 0.0)
            out.append(n._replace(start=s, dur=d, vel=max(1, n.vel - (4 if i else 0))))
    return Clip._raw(out, c.length)


def perform(band: Band, role: str, clip, at=0.0, *, shapes='auto', lo: float = 0.0, hi: float = 1.0,
            humanize_ms: float = 8.0, seed=0, articulations='auto', short=0.5, accent_vel: int = 112,
            glide_leaps: int | None = None, glide_ms: float = 120.0, vib: bool | dict | None = None,
            bow_seconds: float | None = None, follow=None) -> Clip:
    """Play a part on a role the way the section / player would; returns the notes as played (in song beats: the
    part is placed at `at` first, so a note on the section's downbeat can still start early):
      sustaining roles: articulations by note length ('auto': short -> staccato / spiccato, vel >= accent_vel ->
        marcato, the rest sustain, from what the role has; a name for every note; None = leave the marks), long notes
        started band.info['lead_ms'][role] early, a section's timing (humanize_ms), and the velocities written as the
        dynamics lane (lo + (hi - lo) x vel / 127: 40 p, 78 mf, 95 f, 115 ff) with shapes ('auto': long notes swell,
        or SHAPES / a list / dict per note: art.expression; follow= a function beat -> level (a Score's
        dynamics map: held notes follow a written crescendo inside them);
      solo players (string_quartet) also: legato phrases, a glide into leaps >= glide_leaps, a delayed vibrato
        (vib: True / False / options), bow changes after bow_seconds of tied line;
      struck roles (timpani, percussion, harp, celesta, drums), synths and custom sounds without a dynamics lane
        (sounds= an sf2 / synth: kind 'plain'): humanized timing, velocity = dynamics;
      organ roles: plain legato playing (no dynamics per note).
    Several perform() calls on one role are fine (different spans)."""
    if role not in band.roles:
        raise ComposeError(f"perform: band {band.preset!r} has no role {role!r}; roles: {', '.join(band.roles)}")
    t = band[role]
    info = band.info
    kind = info.get('kind', {}).get(role, 'sustain')
    a0 = float(t._song._at(at))
    bpm = t._song.tempo_at(a0)
    c0 = as_clip(clip)
    c = Clip._raw([n._replace(start=n.start + a0) for n in c0], c0.length + a0)     # in song beats
    if kind in ('struck', 'synth', 'organ', 'plain'):
        if isinstance(articulations, str) and articulations != 'auto':
            c = art.articulate(c, articulations)          # timpani 'hit' / 'roll'
        if humanize_ms and kind != 'organ':
            c = art.humanize_starts(c, bpm, humanize_ms * 0.6, seed=seed)
        t.play(c, 0)
        return c
    has_arts = bool(info['articulations'].get(role))
    if articulations == 'auto':
        if has_arts:
            c = art.auto_articulate(c, t, short=short, accent_vel=accent_vel)
    elif articulations is not None:
        c = art.articulate(c, articulations)
    mono = role in info.get('mono', [])
    if mono:
        c = art.legato(c, overlap=0.04)
        if bow_seconds:
            c = art.bow_changes(c, bpm, bow_seconds)
        if glide_leaps:
            c = art.glide(c, glide_ms, where=art.leaps(int(glide_leaps)))
    c = lead(c, bpm, info.get('lead_ms', {}).get(role, 0.0))
    if humanize_ms:
        c = art.humanize_starts(c, bpm, humanize_ms, seed=seed)
    t.play(c, 0)
    if shapes is not None and getattr(t.instrument, 'type', '') == 'sampler':
        long = max(2.0, 2.5 * bpm / 60.0)       # 'auto' swells notes of 2.5 s and more (a messa di voce)
        art.expression(t, c, 0, shapes, lo=lo, hi=hi, accent_vel=accent_vel, long=long, follow=follow)
    depth = info.get('vibrato', {}).get(role, 0.0)
    if vib is None:
        vib = bool(depth) and mono
    if vib and getattr(t.instrument, 'type', '') == 'sampler':
        opts = dict(vib) if isinstance(vib, dict) else {}
        opts.setdefault('depth', depth or 12.0)
        opts.setdefault('seed', seed)
        art.vibrato(t, c, 0, **opts)
    return c


# --------------------------------------------------------------------------------------------- registration

_R = ('violins1', 'violins2', 'violas', 'cellos', 'basses')
_W = ('flutes', 'oboes', 'clarinets', 'bassoons')

bands.register('string_quartet', string_quartet, genre='orchestra', roles=('violin1', 'violin2', 'viola', 'cello'),
               description='2 violins, viola, cello: solo legato players with live dynamics and keyswitched '
                           'articulations (SSO 4.0 + VSCO 2 CE) in a chamber hall',
               tuned='classical profile; songs/_bands/string_quartet', requires=('sso',))
bands.register('chamber_orchestra', chamber_orchestra, genre='orchestra',
               roles=_R + _W + ('horns', 'timpani'),
               description='VSCO 2 CE chamber strings, wind pairs, 2 horns, timpani (Classical era) in a mid-size hall',
               tuned='classical profile; songs/_bands/chamber_orchestra', requires=('vsco2-ce',))
bands.register('symphony_orchestra', symphony_orchestra, genre='orchestra',
               roles=_R + _W + ('horns', 'trumpets', 'trombones', 'tuba', 'timpani', 'percussion', 'harp',
                                'celesta'),
               description='SSO 4.0 full sections + 4 horns, trumpets, trombones, tuba, timpani, percussion, harp, '
                           'celesta in a concert hall',
               tuned='classical profile; songs/_bands/symphony_orchestra', requires=('sso',))
bands.register('film_orchestra', film_orchestra, genre='orchestra',
               roles=_R + _W + ('horns', 'trumpets', 'trombones', 'low_brass', 'tuba', 'timpani', 'percussion',
                                'drums', 'choir', 'harp', 'sub', 'pulse'),
               description="symphonic sections + choir 'aah', bass trombone, taikos in a big hall; hybrid=True adds "
                           "a synth sub and pulse",
               tuned='film profile; songs/_bands/film_orchestra', requires=('sso',))
bands.register('church_organ', church_organ, genre='orchestra',
               roles=('soft', 'principal', 'full', 'pedal', 'pedal_full'),
               description="Lars Palo pipe organ registrations (soft / principal chorus / full organ + pedal) in a "
                           "big church; organ='burea' | 'pitea'",
               tuned='classical profile; songs/_bands/church_organ', requires=('lars-palo-burea-church',))

# the orchestrator's desk: Score (parts + one dynamics map, perform), doublings, hits, brass, unison, beds, the choir
from .scoring import (BED, FALLBACK, PHRASING, TUTTI_ROLES, UNISON_OCTAVES, VEL, WINDS8_ROLES, Choir,  # noqa: E402
                      Score, bed, colla_parte, double, hits, natural_brass, sing, swells, timpani_tuning, unison)
