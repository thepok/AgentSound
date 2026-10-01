"""Pop and funk band presets: a polished radio-pop band and a tight funk / soul band, both with real sampled players
where it matters (electric basses, e-pianos, a DI guitar through an amp, a sampled horn section, sax) and the pop
production around them (claps and percussion, sidechained bass / pad, plate + bright hall + dotted-8th echo, a
glued, wide, loud master). recipes/pop.md ('Band presets') shows how to play them.

  pop_band   drums, perc, bass, keys, pad, pluck, lead     modern pop / dance-pop / pop ballad (profile pop)
  funk_band  drums, bass, keys, gtr, horns, lead           funk / soul / funk-pop (profile pop)

Shared helpers (DI guitars with palm mute / dead note articulations, layering, the pack checks) live in
agentsound/bandlib/rock.py.
"""

from __future__ import annotations

from .. import bands, library
from ..bands import Band
from ..patches import Instrument, fx, inst
from .. import patches as _patches
from ..theory import ComposeError
from .rock import (BASS_ARTICULATIONS, EMILY, FASHION, FSBS_DI, Builder, _chain, _eq, _patch_sound, amp, articulated,
                   guitar_di, installed, layer, lib_patch, master_chain, piano, rock_kit, wurlitzer)

CHART_KIT = 'samples/sampleradar-essential-drumkit/Chart Kit'
GIMME = 'samples/hydrogen-gimme-a-hand'
FUNK_KIT = 'samples/orangetree-jazz-funk-kit/samples'
CLAV = 'samples/lithalean-clavinet/Clavinet.sfz'
FIEDLER = 'samples/fiedler-precision-e-bass/mf-precission-e-bass-fingered-pop-slap-slide-fretnoise.sfz'
GROWLY_CLEAN = 'samples/karoryfer-growlybass/growlybass_clean.sfz'
VPO_BRASS = 'samples/vpo-scripts-standard/Brass/'


def pop_kit(level: float = 0.0) -> Instrument:
    """A punchy modern pop kit: SampleRadar 'Chart Kit' (kick, 4 snare round robins, clap, hats, crash, tambourine,
    shaker; royalty-free, no redistribution); fallback the 80s pop kit (sampled/80s_pop_kit), then the engine's
    'modern' drum machine."""
    if installed('sampleradar-essential-drumkit'):
        # spread=1: hats / cymbals / tambourine at the drummer's-perspective positions (the one-shots are mono)
        return inst.kit(CHART_KIT, level=level - 3.0, spread=1.0,
                        gains={'hats': -5, 'cymbals': -6, 'tamb': -6, 'shaker': -8, 'clap': -2})
    if installed('sampleradar-80s-pop-drums'):
        ins = _patch_sound('sampled/80s_pop_kit')
        return ins.but(level=ins.params.get('level', 0.0) + level)
    return inst.drums(kit='modern', level=level)


def kick_sub(ins: Instrument, pitch, *, gain: float = 0.0, decay: float = 0.3, key: int = 36) -> Instrument:
    """Layer a sine 'sub thump' under the kick (in place): a sine at `pitch` (tune it to the song key, 41-55 Hz:
    E1..A1) on kick key `key` that dies within `decay` seconds - the modern pop / 808-style low end a sampled kick
    alone lacks."""
    from ..theory import note as _note
    p = _note(pitch) if isinstance(pitch, str) else int(pitch)
    if ins.type != 'sampler':          # a fallback drum machine: its own kick
        return ins
    ins.expand()
    ins.params['samples'].append({'file': '*sine', 'lo': key, 'hi': key, 'root': 60 + key - p, 'attack': 0.002,
                                  'hold': 0.03, 'decay': decay, 'sustain': 0.0, 'release': 0.04, 'gain': gain})
    return ins


def tonic_sub(key) -> int:
    """The tonic of the song key in E1..D#2 (41..78 Hz): the kick sub pitch that fits every chord's root."""
    return 28 + (key.tonic - 4) % 12


def hand_perc(level: float = 0.0) -> Instrument:
    """Hand percussion (Hydrogen 'Gimme A Hand', GPL - the music is not a derivative): 39 hand claps, 40 finger
    snaps, 54 tambourine, 56 cowbell, 60 / 61 bongos, 70 maracas (shaker), 36 / 37 cajon - 5 velocity layers each;
    fallback FreePats world percussion (sfz), then the GeneralUser kit."""
    if installed('hydrogen-gimme-a-hand'):
        return inst.kit(GIMME, level=level, extras=False)
    if installed('freepats-world-percussion'):
        return inst.sfz('samples/freepats-world-percussion/WorldPercussion 20200905.sfz', level=level)
    return inst.sf2('Standard 1', level=level)


def funk_kit(level: float = 0.0) -> Instrument:
    """A tight, dry funk kit: Orange Tree Jazz Funk Kit (bop kick, snare with 3 layers x 10 round robins, rimshots,
    side stick, toms, hats, flat ride; freeware, no redistribution), its ride-crash on 49 / 57; fallback the rock
    kits (rock_kit)."""
    if installed('orangetree-jazz-funk-kit'):
        return inst.kit(FUNK_KIT, level=level + 1.0, spread=0.9, map={'kick': 'kick - snares on - *',
                                                                      'kick2': 'bop kick - snares on - *',
                                                                      'crash': 'ride - crash*',
                                                                      'crash2': 'flat ride - crash*',
                                                          'hat': 'hihat - closed - *'},
                        gains={'hats': -5, 'cymbals': -4, 'ride': -3})
    return rock_kit('unruly', level=level)


def electric_bass(style: str = 'finger', level: float = 0.0) -> Instrument:
    """'finger': Karoryfer Growlybass clean (Squier Jazz, CC0); 'round': Fashionbass (roundwounds, bright, 5 layers,
    CC0) - both keyswitched with 'staccato' and 'mute' (BASS_ARTICULATIONS: clip.articulate('staccato', ...));
    'slap': MF Precision bass (Fiedler: fingered layers, slap at velocity >= 104; CC-BY-NC-SA 'music ok'), fallback
    Fashionbass."""
    if style == 'slap' and installed('fiedler-precision-e-bass'):
        return inst.sfz(FIEDLER, transpose=12, level=level + 3.0)   # the file sounds an octave below its keys
    if style == 'finger' and installed('karoryfer-growlybass'):
        # the file sounds an octave below its keys: transpose=12 makes written E1 sound E1
        return articulated(GROWLY_CLEAN, BASS_ARTICULATIONS, base='sustain', transpose=12, level=level)
    if installed('karoryfer-fashionbass'):
        return articulated(FASHION, BASS_ARTICULATIONS, base='sustain', level=level + 1.0)
    if installed('freepats-fingerbass-yr-sf2'):
        return inst.sf2(file=library.SAMPLES.joinpath('freepats-fingerbass-yr-sf2', 'FingerBassYR 20190930.sf2')
                        .as_posix(), level=level)
    return inst.sf2('Finger Bass', level=level)


def epiano(kind: str = 'rhodes', level: float = 0.0) -> Instrument:
    """'rhodes': jRhodes3d (sampled/rhodes, Rhodes Mk I, CC-BY-NC: music fine, not the samples) - fallback the
    Wurlitzer; 'wurli': Greg Sullivan Wurlitzer EP200 (CC-BY); 'piano': Salamander grand; 'clav': Lithalean
    Clavinet (licence not stated: private listening), fallback DX7 'FUNK CLAV'."""
    if kind == 'rhodes' and installed('jrhodes3d'):
        ins = _patch_sound('sampled/rhodes')
        return ins.but(level=ins.params.get('level', 0.0) + level)
    if kind == 'piano':
        return piano(level)
    if kind == 'clav':
        if installed('lithalean-clavinet'):
            return inst.sfz(CLAV, level=level)
        return inst.dx7('FUNK CLAV', level=level)
    return wurlitzer(level)


def horn_section(level: float = 0.0) -> Instrument:
    """Trumpet + trombone sections in unison (Virtual Playing Orchestra 3, royalty-free; needs vpo-scripts-standard
    and vpo-wav), keyswitched: 'stab' (staccato, default), 'accent' (marcato), 'long' (sustain): clip.articulate(
    'long', ...). Voicings in F3-C6 (trombones stop at F5, trumpets start at F#3: both sound in F#3-F5). Fallback
    GeneralUser 'Brass Section'."""
    if installed('vpo-scripts-standard') and installed('vpo-wav'):
        tp = inst.sfz_multi({'stab': VPO_BRASS + 'trumpet-SEC-staccato.sfz',
                             'accent': VPO_BRASS + 'trumpet-SEC-accent.sfz',
                             'long': VPO_BRASS + 'trumpet-SEC-sustain.sfz'}, level=level)
        tb = inst.sfz_multi({'stab': VPO_BRASS + 'trombone-SEC-staccato.sfz',
                             'accent': VPO_BRASS + 'trombone-SEC-accent.sfz',
                             'long': VPO_BRASS + 'trombone-SEC-sustain.sfz'}, level=level)
        return layer(tp, tb, gains=[0.0, -2.0], pans=[-0.35, 0.35])
    return inst.sf2('Brass Section', level=level)


def lead_sound(kind: str, preset: str):
    """Lead voices: 'synth' (synthwave/pulse_lead), 'soft' (synthwave/soft_lead), 'sax' (Weresax alto, legato,
    CC0), 'tenor' (MTG tenor sax, legato, CC-BY), 'guitar' (Emily SG DI, legato - the role chain adds the amp),
    'piano' (Salamander)."""
    if kind == 'synth':
        return lib_patch('synthwave/pulse_lead')
    if kind == 'soft':
        return lib_patch('synthwave/soft_lead')
    if kind == 'sax':
        return lib_patch('sampled/alto_sax') if installed('karoryfer-weresax') else inst.sf2('Alto Sax', mono='on')
    if kind == 'tenor':
        return lib_patch('sampled/tenor_sax') if installed('mtg-solo-sax') else inst.sf2('Tenor Sax', mono='on')
    if kind == 'guitar':
        return guitar_di(EMILY, preset, 'lead', articulations=(), mono='legato', legatotime=30)
    if kind == 'piano':
        return piano()
    raise ComposeError(f"{preset}: lead must be one of synth, soft, sax, tenor, guitar, piano; got {kind!r}")


# lead insert chains per kind (after the sound's own patch fx) and the trim that puts each lead at about -19 LUFS
_LEAD_CHAIN = {
    'synth': (lambda: [_eq(hp__freq=180, peak1__freq=400, peak1__gain=-2.0, peak3__freq=3500, peak3__gain=-1.5)],
              1.0),
    'soft': (lambda: [_eq(hp__freq=180, peak1__freq=400, peak1__gain=-1.5)], 0.0),
    'sax': (lambda: [_eq(hp__freq=150, peak1__freq=400, peak1__gain=-2.0, peak3__freq=2800, peak3__gain=1.0),
                     fx.compressor(threshold=-22, ratio=3, attack=10, release=150, automakeup='on')], -1.0),
    'tenor': (lambda: [_eq(hp__freq=110, peak1__freq=380, peak1__gain=-2.5, peak3__freq=2600, peak3__gain=1.0),
                       fx.compressor(threshold=-22, ratio=3, attack=10, release=150, automakeup='on')], -1.0),
    'guitar': (lambda: amp('clean', drive=9) + [fx.compressor(threshold=-24, ratio=3, attack=8, release=120,
                                                              automakeup='on'),
                                                fx.chorus(mode='I', mix=0.2),
                                                _eq(hp__freq=150, peak1__freq=350, peak1__gain=-2.0)], -4.2),
    'piano': (lambda: [_eq(hp__freq=100, peak1__freq=300, peak1__gain=-2.5, peak3__freq=3500, peak3__gain=1.5)],
              -1.0),
}


def _master_pop(band, gain: float, *, lowmid: float = -2.0, mid: float = 0.0, width: float = 1.15,
                threshold: float = -16.0) -> None:
    master_chain(band,
                 _eq(hp__freq=25, peak1__freq=330, peak1__gain=lowmid, peak1__q=0.8, peak2__freq=1200,
                     peak2__gain=mid, peak2__q=0.7, peak3__freq=3500, peak3__gain=-0.5, high__freq=11000,
                     high__gain=1.5),
                 fx.compressor(threshold=threshold, ratio=2, attack=30, release=200, knee=8, detector='rms',
                               keyhp=100, automakeup='on'),
                 fx.tape(speed='30', drive=0.5, bump=0.5, wow=0.0, flutter=0.0),
                 fx.width(width=width, monobass=120),
                 fx.limiter(gain=gain, ceiling=-1.2, release=60))


# ------------------------------------------------------------------------------------------------ pop band

POP_NOTES = """\
How to play it (pop_band; recipe recipes/pop.md):
  drums   Chart Kit, GM keys: 36 kick (+ a short sine sub on the song's tonic: sub=), 38 snare (4 round robins), 39
          clap, 42 / 46 hats, 49 / 57 crash, 54 tamb, 82 shaker (cymbals spread from the drummer's view).
          Four-on-the-floor or a pop backbeat; quantized tight (only 2 ms humanize), hats velocity-shaped.
  perc    hand percussion on its own track (claps with a plate): 39 claps (5 layers: velocity 90-127 layered with the
          snare on 2 and 4), 40 finger snaps, 54 tambourine (chorus 8ths / 16ths), 70 maracas (shaker 16ths).
  bass    real electric bass (Growlybass, clean) or bass='synth' (synthwave/moog_bass): roots and octaves E1-E3,
          sidechained 6 dB under the kick (the kick's sub owns < 45 Hz, the bass 60-150 Hz). clip.articulate(
          'staccato', ...) for short disco notes (electric) - they thin the low end: sustained notes in the chorus.
  keys    e-piano (keys='rhodes' | 'wurli') or keys='piano': chords C3-C5, pushed 8ths in the chorus.
  pad     warm Juno pad (sidechained 6 dB to the kick): whole-bar chords C3-C5, open voicings.
  pluck   synth pluck (arp_pluck): 16th arps / syncopated chord-tone hooks C4-C6 into the echo.
  lead    the "vocal": lead='synth' (pulse lead, default) | 'soft' | 'sax' (alto, legato) | 'tenor' | 'guitar'
          (Emily SG through a clean amp) | 'piano'. Verse C4-A4, chorus to C5-E5; sax / guitar: art.legato(clip),
          clip.glide(...), art.vibrato(...). Plate + dotted-8th echo sends set; automate 'send.echo' throws.
Levels (fx.trim holds the balance, the faders are yours; dry LUFS on the demo): drums -19.5, perc -24, bass -20,
keys -26.5, pad -27.5, pluck -27, lead -19. Master -10.6 LUFS (verse -10.1, chorus -9.5; profile pop): the master
glues only above -12 dB, so a lighter verse (the demo: bass -4, keys -2 via gainDb) stays lighter."""


def pop_band(song, *, without=(), sounds=None, ids=None, keys: str = 'rhodes', bass: str = 'electric',
             lead: str = 'synth', sub=True) -> Band:
    """Modern radio-pop band: punchy Chart Kit + hand claps / tambourine / shaker, electric (or synth) bass, e-piano
    or piano, Juno pad, synth pluck and a lead voice; kick sidechain on bass and pad, plate + bright hall + echo.
    keys='rhodes'|'wurli'|'piano'; bass='electric'|'synth'; lead='synth'|'soft'|'sax'|'tenor'|'guitar'|'piano';
    sub=True layers a sine sub thump tuned to the song's tonic (E1..D#2) under the kick (a note name / MIDI number
    picks the pitch, False = the plain kit)."""
    if keys not in ('rhodes', 'wurli', 'piano'):
        raise ComposeError(f"pop_band: keys must be 'rhodes', 'wurli' or 'piano', got {keys!r}")
    if bass not in ('electric', 'synth'):
        raise ComposeError(f"pop_band: bass must be 'electric' or 'synth', got {bass!r}")
    if lead not in _LEAD_CHAIN:
        raise ComposeError(f"pop_band: lead must be one of {', '.join(_LEAD_CHAIN)}, got {lead!r}")
    b = Builder(song, 'pop_band', without=without, sounds=sounds, ids=ids, analysis={'profile': 'pop'},
                notes=POP_NOTES)
    s = song
    plate = b.bus('plate', _patches.get('bus/ir_plate').fx if installed('little-devil-224xl-13-cd-plate-a')
                  else _patches.get('bus/plate').fx)
    hall = b.bus('hall', _patches.get('bus/ir_hall_bright').fx if installed('little-devil-224xl-02-bright-hall')
                 else _patches.get('bus/hall').fx)
    echo = b.bus('echo', _patches.get('bus/echo').fx)
    drum_bus = b.bus('drum_bus', [
        fx.compressor(threshold=-20, ratio=4, attack=8, release=80, knee=6, mix=0.5, automakeup='on', keyhp=60),
        fx.saturator(mode='tape', drive=3, mix=0.5),
        _eq(hp__freq=28, peak1__freq=350, peak1__gain=-2.0, high__freq=10000, high__gain=1.5)])
    sub_pitch = tonic_sub(s.key) if sub is True else sub

    def kit():
        k = pop_kit()
        return kick_sub(k, sub_pitch, gain=3.0) if sub_pitch else k
    kit_t = b.track('drums', kit, output=drum_bus, trim=-1.5,
                    fx=[_eq(low__freq=50, low__gain=3.0, peak1__freq=400, peak1__gain=-2.5, peak2__freq=115,
                            peak2__gain=-4.5, peak2__q=0.8, peak3__freq=4500, peak3__gain=1.5)],
                    sends={plate: -18}, humanize=(2, 4, 61))
    b.track('perc', hand_perc, output=drum_bus, pan=0.0, trim=-6.0,
            fx=[_eq(hp__freq=250, peak1__freq=600, peak1__gain=-2.0, high__freq=9000, high__gain=1.5),
                fx.microshift(style='wide', detune=0, delay=8, focus=400, mix=0.35)],
            sends={plate: -8, hall: -16}, humanize=(4, 6, 62))
    if bass == 'electric':
        bass_t = b.track('bass', lambda: electric_bass('finger'), trim=3.5,
                         # the kick's sine sub owns < 45 Hz, the bass 60-150 Hz (no low-end masking), its growl
                         # stays out of the keys' low mids
                         fx=[_eq(hp__freq=45, hp__slope=24, low__freq=90, low__gain=5.0, peak1__freq=400,
                                 peak1__gain=-8.0, peak1__q=0.7, peak2__freq=1100, peak2__gain=-2.5, peak2__q=0.8,
                                 peak3__freq=110, peak3__gain=1.5, peak3__q=1.2),
                             fx.saturator(mode='tube', drive=5, mix=0.35),
                             fx.compressor(threshold=-22, ratio=4, attack=15, release=120, knee=6, automakeup='on'),
                             _eq(lp__freq=2800)],
                         humanize=(3, 5, 63))
    else:
        bass_t = b.track('bass', lambda: lib_patch('synthwave/moog_bass'), trim=-1.0,
                         fx=[_eq(hp__freq=30, peak1__freq=250, peak1__gain=-2.0)])
    keys_snd = {'rhodes': lambda: epiano('rhodes'), 'wurli': lambda: epiano('wurli'), 'piano': piano}[keys]
    keys_t = b.track('keys', keys_snd, pan=-0.55, trim=-4.0,
                     fx=[_eq(hp__freq=200, peak1__freq=380, peak1__gain=-6.0, peak1__q=0.8, high__freq=8000,
                             high__gain=1.5),
                         fx.compressor(threshold=-24, ratio=2.5, attack=15, release=150, automakeup='on')]
                     + ([fx.tremolo(rate=4.5, depth=0.15, stereo=90), fx.chorus(mode='I', mix=0.4)]
                        if keys != 'piano' else []),
                     sends={plate: -14, hall: -12}, humanize=(4, 5, 64))
    pad_t = b.track('pad', lambda: lib_patch('synthwave/warm_pad'), trim=-6.0,
                    fx=[_eq(hp__freq=280, peak1__freq=450, peak1__gain=-3.5, peak2__freq=1300, peak2__gain=-3.5,
                            peak2__q=0.8, high__freq=9000, high__gain=1.0),
                        fx.width(width=1.0)],
                    sends={hall: -3})
    b.track('pluck', lambda: lib_patch('synthwave/arp_pluck'), pan=0.55, trim=-6.0,
            fx=[_eq(hp__freq=300, peak3__freq=3500, peak3__gain=-1.5), fx.chorus(mode='I', mix=0.35)],
            sends={echo: -8, hall: -14})
    lead_chain, lead_trim = _LEAD_CHAIN[lead]
    b.track('lead', lambda: lead_sound(lead, 'pop_band'), trim=lead_trim, fx=lead_chain(),
            sends={plate: -9, echo: -12, hall: -15},
            humanize=(3, 5, 65) if lead in ('sax', 'tenor', 'guitar', 'piano') else None)
    if kit_t is not None:
        if bass_t is not None:
            s.sidechain(bass_t, key=kit_t, pitches='kick', depth=6, attack=2, release=140)
        if pad_t is not None:
            s.sidechain(pad_t, key=kit_t, pitches='kick', depth=6, attack=3, release=220)
        if keys_t is not None:
            s.sidechain(keys_t, key=kit_t, pitches='kick', depth=2, attack=3, release=180)
    # glue above -12 dB only and a moderate limiter: the chorus stays louder than the verse
    _master_pop(b.band, 6.5, width=1.35, threshold=-12.0)
    return b.band


bands.register('pop_band', pop_band, genre='pop',
               roles=('drums', 'perc', 'bass', 'keys', 'pad', 'pluck', 'lead'),
               description='modern radio pop: SampleRadar Chart Kit + Gimme-a-Hand claps / tambourine / shaker, a real '
                           'electric bass (Growlybass) or synth bass, Rhodes / Wurlitzer / grand, Juno pad, synth '
                           'pluck and a lead (synth, alto / tenor sax, guitar, piano); kick sidechain on bass and '
                           'pad, 224XL plate + bright hall, dotted-8th echo, a glued wide master',
               tuned='profile pop: songs/_bands/pop_band -10.6 LUFS, LRA 7.4, width 38 %, no warnings')


# ------------------------------------------------------------------------------------------------ funk band

FUNK_NOTES = """\
How to play it (funk_band; recipe recipes/pop.md 'Funk-pop'):
  drums   Orange Tree Jazz Funk Kit, GM keys (36 kick, 38 snare: 3 layers x 10 round robins, 37 side stick, 40 rimshot,
          42 / 46 hats, 51 flat ride, 49 ride-crash, toms 50/48/45/41). 16th hats with accents
          (clip.vel_pattern), snare ghost notes at velocity 30-55 ('o' in drums grids), swing 0.54-0.56
          (track groove / clip.swing).
  bass    bass='finger' (Growlybass clean, staccato keyswitch for the short notes) | 'round' (Fashionbass) | 'slap'
          (MF Precision: velocity >= 104 = slap / pop): syncopated 16ths, octaves, dead-ish short notes
          (articulate('staccato') or staccato('1/16')), E1-E3.
  keys    keys='clav' (Clavinet through an envelope filter: each note opens it - the auto-wah) | 'wurli' | 'rhodes':
          16th syncopated two- / three-note stabs C3-C5, staccato('1/16').
  gtr     the chicken-scratch guitar (FSBS single-coil DI -> clean 1x12, compressed): 16th strums of 3-4 note 9th /
          7th voicings on the top strings (G3-E5) with most strokes as dead notes (articulate('dead', where=...):
          real muted-string scratches) and the accents open; clip.strum(ms=6, bpm=s.tempo, direction='alternate').
  horns   trumpets + trombones in unison (VPO): 'stab' (default, staccato) hits on the offbeats, 'accent',
          'long' (articulate('long', ...)) swells and falls; voicings F#3-F5, 2-4 notes.
  lead    tenor sax (lead='tenor', default) | 'sax' (alto) | 'synth' | 'guitar': legato phrases (art.legato),
          clip.glide(...) scoops, art.vibrato(...).
Levels (fx.trim holds the balance, the faders are yours; dry LUFS on the demo): drums -21.5, bass -20, keys -24.5,
gtr -25.5, horns -24, lead -20.5. Master -10.8 LUFS."""


def funk_band(song, *, without=(), sounds=None, ids=None, keys: str = 'clav', bass: str = 'finger',
              lead: str = 'tenor') -> Band:
    """Tight funk / soul band: dry Jazz Funk kit in a small room, finger / slap bass, clavinet with an envelope filter
    (or Wurlitzer / Rhodes), chicken-scratch DI guitar, a sampled trumpet + trombone section and a tenor sax lead.
    keys='clav'|'wurli'|'rhodes'; bass='finger'|'round'|'slap'; lead='tenor'|'sax'|'synth'|'guitar'."""
    if keys not in ('clav', 'wurli', 'rhodes'):
        raise ComposeError(f"funk_band: keys must be 'clav', 'wurli' or 'rhodes', got {keys!r}")
    if bass not in ('finger', 'round', 'slap'):
        raise ComposeError(f"funk_band: bass must be 'finger', 'round' or 'slap', got {bass!r}")
    if lead not in ('tenor', 'sax', 'synth', 'guitar'):
        raise ComposeError(f"funk_band: lead must be 'tenor', 'sax', 'synth' or 'guitar', got {lead!r}")
    b = Builder(song, 'funk_band', without=without, sounds=sounds, ids=ids, analysis={'profile': 'pop'},
                notes=FUNK_NOTES)
    s = song
    room = b.bus('room', _chain('bus/ir_ambience', convolver={'width': 1.3}) if installed('little-devil-224xl-04-room')
                 else [fx.reverb(type='room', mix=1.0, decay=0.5, size=0.3, predelay=2, lowcut=200)])
    plate = b.bus('plate', _patches.get('bus/ir_plate').fx if installed('little-devil-224xl-13-cd-plate-a')
                  else _patches.get('bus/plate').fx)
    echo = b.bus('echo', _patches.get('bus/echo_quarter').fx)
    drum_bus = b.bus('drum_bus', [
        fx.compressor(threshold=-22, ratio=4, attack=10, release=80, knee=6, mix=0.45, automakeup='on', keyhp=60),
        fx.saturator(mode='tape', drive=4, mix=0.5),
        _eq(hp__freq=30, peak1__freq=400, peak1__gain=-1.5, high__freq=10000, high__gain=1.0)])
    kit_t = b.track('drums', funk_kit, output=drum_bus, trim=-3.5,
                    fx=[_eq(low__freq=50, low__gain=2.0, peak1__freq=230, peak1__gain=-3.0, peak1__q=0.9,
                            peak2__freq=110, peak2__gain=-6.5, peak2__q=0.8, peak3__freq=4000, peak3__gain=-2.5,
                            high__freq=9000, high__gain=2.0)],
                    sends={room: -4, plate: -20}, humanize=(4, 7, 71))
    style = {'finger': 'finger', 'round': 'round', 'slap': 'slap'}[bass]
    bass_t = b.track('bass', lambda: electric_bass(style), trim=1.5,
                     fx=[_eq(hp__freq=40, hp__slope=24, peak1__freq=250, peak1__gain=-2.0, peak2__freq=1000,
                             peak2__gain=2.0, peak3__freq=100, peak3__gain=1.5, peak3__q=1.2),
                         fx.compressor(threshold=-26, ratio=5, attack=2, release=90, knee=6, automakeup='on'),
                         fx.saturator(mode='tube', drive=4, mix=0.3),
                         _eq(lp__freq=6000)],
                     humanize=(3, 6, 72))
    if keys == 'clav':
        keys_t = b.track('keys', lambda: epiano('clav'), pan=-0.7, trim=4.0,
                         fx=[_eq(hp__freq=150, peak1__freq=400, peak1__gain=-2.0, peak2__freq=1000, peak2__gain=-2.0),
                             fx.filter(mode='bp', cutoff=1200, resonance=0.35, name='wah'),
                             fx.compressor(threshold=-24, ratio=3, attack=5, release=100, automakeup='on'),
                             fx.saturator(mode='tube', drive=5, mix=0.4),
                             fx.chorus(mode='custom', rate=0.6, depth=1.5, delay=6, mix=0.5)],
                         sends={room: -8, plate: -16}, humanize=(3, 5, 73))
        if keys_t is not None:
            from ..modulation import envelope
            keys_t.modulate('fx.wah.cutoff', envelope(decay='1/8', min=500, max=2800, curve='exp'))
    else:
        keys_t = b.track('keys', lambda: epiano(keys), pan=-0.45, trim=-3.0,
                         fx=[_eq(hp__freq=150, peak1__freq=350, peak1__gain=-2.0),
                             fx.saturator(mode='tube', drive=6, mix=0.5), fx.tremolo(rate=5.0, depth=0.2, stereo=90)],
                         sends={room: -12, plate: -18}, humanize=(3, 5, 73))
    b.track('gtr', lambda: guitar_di(FSBS_DI, 'funk_band', 'gtr'), pan=0.8, trim=-4.5,
            fx=amp('clean', drive=5) + [fx.compressor(threshold=-28, ratio=5, attack=3, release=80,
                                                     automakeup='on'),
                                       _eq(hp__freq=200, peak1__freq=350, peak1__gain=-3.0, peak2__freq=1800,
                                           peak2__gain=1.0, peak3__freq=4000, peak3__gain=-3.0, peak3__q=0.7),
                                       fx.chorus(mode='I', mix=0.45)],
            sends={room: -6, plate: -18}, humanize=(3, 6, 74))
    b.track('horns', horn_section, pan=0.1, trim=-11.0,
            fx=[_eq(hp__freq=160, peak1__freq=400, peak1__gain=-2.0, peak3__freq=3000, peak3__gain=1.0),
                fx.compressor(threshold=-22, ratio=3, attack=5, release=100, automakeup='on'),
                fx.width(width=1.3)],
            sends={room: -6, plate: -10}, humanize=(5, 6, 75))
    lead_key = {'tenor': 'tenor', 'sax': 'sax', 'synth': 'synth', 'guitar': 'guitar'}[lead]
    lead_chain, lead_trim = _LEAD_CHAIN[lead_key]
    b.track('lead', lambda: lead_sound(lead_key, 'funk_band'), pan=-0.1, trim=lead_trim - 2.0,
            fx=lead_chain() + [_eq(peak2__freq=1000, peak2__gain=-3.5, peak2__q=0.8),
                               fx.microshift(style='smooth', detune=4, delay=10, focus=300, mix=0.5)],
            sends={plate: -9, echo: -13, room: -12}, humanize=(4, 5, 76))
    if kit_t is not None and bass_t is not None:
        s.sidechain(bass_t, key=kit_t, pitches='kick', depth=10, attack=2, hold=30, release=150)
    _master_pop(b.band, 10.5, lowmid=-3.0, mid=-3.0)
    return b.band


bands.register('funk_band', funk_band, genre='pop',
               roles=('drums', 'bass', 'keys', 'gtr', 'horns', 'lead'),
               description='tight funk / soul: Orange Tree Jazz Funk kit in a short 224XL ambience, finger / round / '
                           'slap electric bass, clavinet with an envelope filter (or Wurlitzer / Rhodes), '
                           'chicken-scratch single-coil DI guitar (real dead-note scratches), VPO trumpet + '
                           'trombone section (stab / accent / long), tenor sax lead',
               tuned='profile pop: songs/_bands/funk_band -10.8 LUFS, LRA 6.4, width 39 %, no warnings',
               requires=('freepats-fsbs-direct',))
