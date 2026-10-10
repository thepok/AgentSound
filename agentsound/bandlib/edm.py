"""EDM band presets: house, techno, big_room, future_bass, melodic_house (recipes/edm.md).

    from agentsound import bands
    b = bands.make('melodic_house', s)          # drums bass chords pad pluck lead + returns, kick pump, master
    b.drums.plan({drop: b.info['grooves']['drop'], build: b.info['grooves']['build']})
    ANALYSIS = b.analysis                        # {'profile': 'edm'}

One builder, five sub-styles: the differences are DATA (STYLES): the kit, the bass / chord / lead sounds, how hard and
how long the kick pumps the rest, the master's drive and the drum grooves (GROOVES, handed over as band.info['grooves']:
Clips per section kind - 'intro', 'groove', 'build', 'drop', 'break' - to loop with track.plan / track.loop). Nothing
here is a new module: the sounds are library patches (agentsound/patches/edm.py, synthwave pads / risers), the kits are
the sampled machines (sampled/tr909, sampled/tr808, the SampleRadar main-room / modular kits) with a sine sub thump
under the kick (bandlib.pop.kick_sub), the pump is song.sidechain, the transitions are song.transitions(riser=True ...).

Common options (agentsound/bands.py): without=('pluck', ...), sounds={'lead': 'sampled/piano_lead'} (keeps the role's
chain), ids={'drums': 'kit'}. Preset options: lead='supersaw' | 'piano' | 'pluck' (the hook's sound: the edm/lead
supersaw with an octave-down body, the bright high house piano, or the pluck), kit= ('909', '808', 'main_room',
'modular': another machine), sub= (the kick's sine sub: True = the song's tonic, a note, False).
"""

from __future__ import annotations

from .. import bands
from ..bands import Band
from ..patches import fx
from ..patterns import drums as _drums
from ..theory import ComposeError
from .pop import kick_sub, tonic_sub
from .rock import Builder, _eq, _patch_sound, installed, lib_patch, master_chain

VERSION = 1

_ESS = 'samples/sampleradar-essential-drumkit/'
SHAKER = 82                     # the kits' shaker key (GROOVES use it)

KITS = {
    '909': 'sampled/tr909',
    '808': 'sampled/tr808',
    'main_room': _ESS + 'Main Room Kit',
    'modular': _ESS + 'Modular Kit',
}
"""The machines: the Roland TR-909 (house / techno / melodic), the TR-808 (future bass: the long boomy kick and its
clap), the SampleRadar 'Main Room' kit (big room: layered EDM kick, big claps, stacked hits) and its 'Modular' kit
(techno: tight analog kick, rims, metallic percs). Without the packs: the engine's 909 / 808 drum machines."""

STYLES = {
    'house': dict(kit='909', bass='edm/bass', chords='piano', lead='piano', pump=8.0, pump_release=0.55,
                  chord_pump=6.0, pad_pump=8.0, tempo=(120, 126), master_gain=11.0, swing=0.54,
                  description='house / deep house: TR-909 + sine sub, offbeat bass (edm/bass), piano house chords, '
                              'warm pad, pluck, a bright piano (or supersaw) hook, 8 dB kick pump'),
    'techno': dict(kit='modular', bass='edm/reese', chords='pluck', lead='supersaw', pump=6.0, pump_release=0.5,
                   chord_pump=5.0, pad_pump=8.0, tempo=(125, 135), master_gain=11.0, swing=0.5,
                   description='techno: tight modular kit, rolling reese bass, pluck stabs into the echo, dark pad, '
                               'hypnotic 16th hats and rims, 6 dB pump'),
    'big_room': dict(kit='main_room', bass='edm/bass', chords='supersaw', lead='supersaw', pump=10.0,
                     pump_release=0.6, chord_pump=10.0, pad_pump=10.0, tempo=(126, 130), master_gain=11.5,
                     swing=0.5,
                     description='big room / festival: the main-room kit (layered kick, big clap), supersaw chords '
                                 'and the supersaw-with-body lead, hard 10 dB pump, a hot master'),
    'future_bass': dict(kit='808', bass='edm/bass', chords='future_chords', lead='piano', pump=12.0,
                        pump_release=0.85, chord_pump=12.0, pad_pump=10.0, tempo=(140, 160), master_gain=11.0,
                        swing=0.5,
                        description='future bass: half-time TR-808 with trap hats, wobbling future chords pumped 12 dB '
                                    'with a long release (the breathing chords), sub + mid bass, piano / supersaw hook'),
    'melodic_house': dict(kit='909', bass='edm/reese', chords='supersaw', lead='piano', pump=8.0,
                          pump_release=0.6, chord_pump=7.0, pad_pump=9.0, tempo=(120, 124), master_gain=11.0,
                          swing=0.5,
                          description='melodic house / progressive: TR-909, reese bass over a clean sub, soft supersaw '
                                      'chords, airy pad, the pluck into the echo, a bright piano hook, 8 dB pump'),
}
"""The sub-styles as data: kit (KITS), bass / chord sounds, the hook's sound (lead='supersaw' | 'piano' | 'pluck'),
pump depth (dB) and release (x one beat) on the bass, chords and pad, the tempo range of the style (recipes/edm.md;
only a hint - the song sets its tempo), the master limiter's drive and the hats' swing."""

GROOVES = {
    'house': {
        'intro': "kick: x...x...x...x... | hat: ..x...x...x...x.",
        'groove': "kick: x...x...x...x... | clap: ....x.......x... | hat: ..x...x...x...x. | 82: x.xxx.xxx.xxx.xx",
        'build': "kick: x...x...x...x... | hat: x.x.x.x.x.x.x.x. | clap: ....x.......x...",
        'drop': "kick: X...X...X...X... | clap: ....X.......X... | ohh: ..x...x...x...x. | hat: x.o.x.o.x.o.x.o. "
                "| 82: oxoxoxoxoxoxoxox",
        'break': "hat: ..o...o...o...o.",
    },
    'techno': {
        'intro': "kick: x...x...x...x... | hat: x.o.x.o.x.o.x.o.",
        'groove': "kick: x...x...x...x... | ohh: ..x...x...x...x. | hat: xoxoxoxoxoxoxoxo | rim: ...x..x....x..x.",
        'build': "kick: x...x...x...x... | hat: xxxxxxxxxxxxxxxx | rim: ...x..x....x..x.",
        'drop': "kick: X...X...X...X... | clap: ....x.......x... | ohh: ..X...X...X...X. | hat: xoxoxoxoxoxoxoxo "
                "| rim: ...x..x..x...x..",
        'break': "hat: ..o...o...o...o.",
    },
    'big_room': {
        'intro': "kick: x...x...x...x... | hat: ..x...x...x...x.",
        'groove': "kick: x...x...x...x... | clap: ....x.......x... | ohh: ..x...x...x...x.",
        'build': "kick: x...x...x...x... | clap: ....x.......x... | hat: x.x.x.x.x.x.x.x.",
        'drop': "kick: X...X...X...X... | clap: ....X.......X... | snare: ....x.......x... | ohh: ..X...X...X...X. "
                "| hat: x.x.x.x.x.x.x.x.",
        'break': "",
    },
    'future_bass': {
        'intro': "hat: x.x.x.x.x.x.x.x.",
        'groove': "kick: x.........x..... | clap: ........x....... | hat: x.x.x.x.x.x.x.x.",
        'build': "kick: x.......x.......  | clap: ....x.......x... | hat: xxxxxxxxxxxxxxxx",
        'drop': "kick: X.....x...x..x.. | clap: ........X....... | snare: ........x....... | hat: x.xxx.x.x.xxx.x. "
                "| ohh: ..............x.",
        'break': "hat: x...x...x...x...",
    },
    'melodic_house': {
        'intro': "kick: x...x...x...x... | 82: o.x.o.x.o.x.o.x.",
        'groove': "kick: x...x...x...x... | clap: ....x.......x... | hat: ..x...x...x...x. | 82: oxxooxxooxxooxxo",
        'build': "kick: x...x...x...x... | clap: ....x.......x... | hat: x.x.x.x.x.x.x.x.",
        'drop': "kick: X...X...X...X... | clap: ....X.......X... | ohh: ..x...x...x...x. | hat: x.o.x.o.x.o.x.o. "
                "| rim: ......x.......x. | 82: oxxooxxooxxooxxo",
        'break': "82: o.x.o.x.o.x.o.x.",
    },
}
"""One bar of each section kind per style (patterns.drums grids; 82 = the kits' shaker key): band.info['grooves'] holds
them as Clips. 'build' is the time under a build (add drummer.build / patterns.snare_roll(build=True) and a riser on
top); 'break' the breakdown's pulse (empty: no drums). Vary them (a fill every 8 bars, the 4th bar's kick
drop-out, a crash on each drop's downbeat): every repeat must change something."""

NOTES = """\
How to play it ({preset}; recipe recipes/edm.md):
  drums   {kit}: GM keys 36 kick (+ a sine sub thump on the song's tonic: sub=), 38 snare, 39 clap, 37 rim, 42 / 46
          hats, 49 crash, 82 shaker. band.info['grooves'][kind] = one bar per section kind (intro / groove / build /
          drop / break): loop them, add drummer.build(...) / patterns.snare_roll(build=True) into each drop and a
          crash on its downbeat. Machine-tight (no humanize on the kick), hat velocities shaped.
  bass    {bass}: sub + mid layers (the sub carries < 90 Hz, mono). House: offbeat 8ths between the kicks; melodic /
          future: held roots and slides; techno: rolling 16ths. Roots E1-E2. Pumped {pump:g} dB by the kick.
  chords  {chords}: 3-5 note chords C3-C5 (the drop's rhythm or whole-bar swells), pumped {chord_pump:g} dB.
  pad     warm pad (synthwave/warm_pad): whole-bar chords C3-C5 in the breakdowns and under the drops, pumped {pad_pump:g} dB.
  pluck   edm/pluck: 16th / 8th chord-tone patterns C4-C6 into the dotted-8th echo (melodic house, techno stabs).
  lead    {lead}: the hook - never a thin beep (recipes/HUMAN_FEEDBACK.md). piano: C5-C7, octave-doubled right hand,
          velocities 70-118; supersaw (edm/lead): A4-C6 with phrase arcs. A sung / chopped vocal hook (singer.sing
          tune='hard', singer.chops) sits on top of or replaces it.
Space: plate (snare / clap / keys), hall (chords, pad, lead), echo (pluck, lead throws, chops). Transitions:
s.transitions(riser=True, reverse=True, impact=True, down=True).into(drop, riser=16, impact=('<root>1', 120), breath=1).
Master: master/edm, limiter +{master_gain:g} dB (edm profile -10..-6 LUFS, drops -9..-6); ride s.master.lane('fx.limiter.gain', ...) so
the breakdowns stay softer."""


TUNED = {'melodic_house': 'songs/one-more-round (profile edm: 0 warnings, drops -8.7 / -8.4 LUFS, -9.8 integrated)'}
"""What each preset was checked against (filled in from the demo / showcase builds)."""


def _kit(which: str, level: float = 0.0):
    if which not in KITS:
        raise ComposeError(f"edm kit must be one of {', '.join(KITS)}, got {which!r}")
    src = KITS[which]
    from ..patches import inst
    main = installed('sampleradar-essential-drumkit')
    if src.startswith('sampled/'):
        pack = {'sampled/tr909': 'hyperreal-tr909', 'sampled/tr808': 'sampleradar-essential-drumkit'}[src]
        if not installed(pack):
            return inst.drums(kit='909' if which == '909' else '808', level=level)
        ins = _patch_sound(src)
        ins = ins.but(level=ins.params.get('level', 0.0) + level).expand()
        if main and not any(z.get('lo', 60) <= SHAKER <= z.get('hi', 60) for z in ins.params['samples']):
            # the machines have no shaker: the main-room kit's two shakers (round robin) on key 82
            mr = inst.kit(KITS['main_room'], level=0.0, gains={'shaker': -10}).expand()
            shk = [dict(z) for z in mr.params['samples'] if z.get('lo') == SHAKER]
            for z in shk:
                z['gain'] = round(z.get('gain', 0.0) + mr.params.get('level', 0.0) - ins.params.get('level', 0.0), 3)
            ins.params['samples'].extend(shk)
        return ins
    if main:
        return inst.kit(src, level=level - 2.0, spread=0.8,
                        gains={'hats': -6, 'cymbals': -7, 'clap': -1, 'shaker': -10, 'rim': -5, 'perc': -6})
    return inst.drums(kit='909', level=level)


def _lead(kind: str):
    if kind == 'supersaw':
        return lib_patch('edm/lead')
    if kind == 'piano':
        return lib_patch('sampled/piano_lead') if installed('salamander-grand') else lib_patch('gm/piano_lead')
    if kind == 'pluck':
        return lib_patch('edm/pluck')
    raise ComposeError(f"edm lead must be 'supersaw', 'piano' or 'pluck', got {kind!r}")


_LEAD_CHAIN = {
    'supersaw': (lambda: [_eq(peak1__freq=400, peak1__gain=-1.5)], 0.0),
    'piano': (lambda: [_eq(hp__freq=120, peak1__freq=350, peak1__gain=-2.0, high__freq=9000, high__gain=1.0)], 0.0),
    'pluck': (lambda: [_eq(peak3__freq=3000, peak3__gain=1.0)], 1.0),
}


def _chords(kind: str):
    if kind == 'piano':          # piano house chords: the bright grand, compressed, the room is the plate
        return _patch_sound('sampled/grand_piano') if installed('salamander-grand') else lib_patch('gm/grand_piano')
    return lib_patch({'supersaw': 'edm/supersaw', 'future_chords': 'edm/future_chords', 'pluck': 'edm/pluck'}[kind])


def edm_band(song, *, style: str = 'house', without=(), sounds=None, ids=None, lead: str | None = None,
             kit: str | None = None, sub=True) -> Band:
    """An EDM band of sub-style `style` (STYLES: house, techno, big_room, future_bass, melodic_house): drums (kit +
    sine sub thump, drum bus), bass (sub + mid), chords, pad, pluck, lead; plate / hall / echo returns; the kick pumps
    bass, chords and pad (song.sidechain); master/edm. lead= 'supersaw' | 'piano' | 'pluck' (default: the style's),
    kit= KITS name (default: the style's), sub= True (the song's tonic in E1..D#2) | a note | False."""
    if style not in STYLES:
        raise ComposeError(f"edm style must be one of {', '.join(STYLES)}, got {style!r}")
    st = STYLES[style]
    lead = lead or st['lead']
    if lead not in _LEAD_CHAIN:
        raise ComposeError(f"{style}: lead must be 'supersaw', 'piano' or 'pluck', got {lead!r}")
    kit = kit or st['kit']
    notes = NOTES.format(preset=style, kit=kit, bass=st['bass'], chords=st['chords'], lead=lead, **{
        k: st[k] for k in ('pump', 'chord_pump', 'pad_pump', 'master_gain')})
    b = Builder(song, style, without=without, sounds=sounds, ids=ids, analysis={'profile': 'edm'}, notes=notes)
    s = song
    beat_ms = 60000.0 / float(s.tempo)
    plate = b.bus('plate', lib_patch('bus/plate').fx)
    hall = b.bus('hall', lib_patch('bus/hall').fx)
    echo = b.bus('echo', lib_patch('bus/echo').fx)
    drum_bus = b.bus('drum_bus', [
        fx.compressor(threshold=-18, ratio=4, attack=10, release=70, knee=6, mix=0.4, automakeup='on', keyhp=60),
        fx.saturator(mode='tape', drive=4, mix=0.5),
        _eq(hp__freq=25, peak1__freq=300, peak1__gain=-2.0, high__freq=10000, high__gain=1.5)])
    sub_pitch = tonic_sub(s.key) if sub is True else sub

    def kit_sound():
        k = _kit(kit)
        return kick_sub(k, sub_pitch, gain=1.0, decay=0.35) if sub_pitch else k
    kit_t = b.track('drums', kit_sound, output=drum_bus, trim=-4.0,
                    fx=[_eq(low__freq=55, low__gain=2.0, peak1__freq=250, peak1__gain=-2.5, peak2__freq=500,
                            peak2__gain=-1.5, peak3__freq=5000, peak3__gain=1.0)],
                    sends={plate: -22}, groove=None)
    bass_t = b.track('bass', lambda: lib_patch(st['bass']), trim=0.0, fx=[_eq(peak1__freq=250, peak1__gain=-1.5)])
    chords_t = b.track('chords', lambda: _chords(st['chords']), trim=-5.0,
                       fx=([_eq(hp__freq=180, peak1__freq=380, peak1__gain=-3.0, high__freq=9000, high__gain=1.5),
                            fx.compressor(threshold=-22, ratio=2, attack=25, release=150, knee=6, automakeup='on')]
                           if st['chords'] == 'piano' else [_eq(hp__freq=170)]),
                       sends={hall: -14, plate: -18})
    pad_t = b.track('pad', lambda: lib_patch('synthwave/warm_pad'), trim=-8.0,
                    fx=[_eq(hp__freq=250, peak1__freq=450, peak1__gain=-3.0, high__freq=9000, high__gain=1.5)],
                    sends={hall: -6})
    pluck_t = b.track('pluck', lambda: lib_patch('edm/pluck'), pan=0.25, trim=-6.0, sends={echo: -9, hall: -14})
    chain, trim = _LEAD_CHAIN[lead]
    b.track('lead', lambda: _lead(lead), trim=trim, fx=chain(), sends={hall: -12, echo: -14, plate: -16})
    if kit_t is not None:
        rel = st['pump_release'] * beat_ms
        for t, depth in ((bass_t, st['pump']), (chords_t, st['chord_pump']), (pad_t, st['pad_pump']),
                         (pluck_t, 3.0)):
            if t is not None:
                s.sidechain(t, key=kit_t, pitches='kick', depth=depth, attack=2, hold=10, release=round(rel),
                            curve=0.3 if style == 'future_bass' else 0.0)
    master_chain(b.band, *[f.copy() for f in lib_patch('master/edm').but_fx('limiter', gain=st['master_gain']).fx])
    b.band.info['grooves'] = grooves(style)
    b.band.info['style'] = dict(st)
    b.band.info['swing'] = st['swing']
    return b.band


def grooves(style: str) -> dict:
    """GROOVES[style] as Clips (one bar each; None = no drums): {'intro', 'groove', 'build', 'drop', 'break'}."""
    if style not in GROOVES:
        raise ComposeError(f"edm grooves: style must be one of {', '.join(GROOVES)}, got {style!r}")
    return {k: (_drums(v.replace("|", chr(10)), bars=1) if v else None) for k, v in GROOVES[style].items()}


def _register(style: str) -> None:
    st = STYLES[style]
    bands.register(style, lambda song, **kw: edm_band(song, style=style, **kw), genre='edm',
                   roles=('drums', 'bass', 'chords', 'pad', 'pluck', 'lead'),
                   description=st['description'] + f" ({st['tempo'][0]}-{st['tempo'][1]} BPM)",
                   tuned=TUNED.get(style, 'profile edm (recipes/edm.md targets)'))


for _st in STYLES:
    _register(_st)
