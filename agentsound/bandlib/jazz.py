"""Jazz band presets on the sampled instruments and the realism engine: a New York club trio and quartet, a
late-night ballad band and a bossa nova group - each one call to a finished, balanced, played-sounding ensemble.

    from agentsound import *
    from agentsound import bands, jazz
    from agentsound.bandlib import jazz as jazzband   # the presets' helpers: brushes(), pedal(), bossa_groove()

    b = bands.make('jazz_quartet', s)                 # piano (comp + right hand), upright bass, brushes, tenor sax
    ANALYSIS = b.analysis                             # {'profile': 'jazz'}: what the preset is tuned against
    b.comp.play(jazz.comp(prog, answer=head, register=('A2', 'G4'), seed=1), a1)
    b.bass.play(jazz.walking_bass(prog, key=s.key, seed=2), a1)
    b.drums.play(jazzband.brushes(b, 8, seed=3), a1)  # jazz.brushes keyed and levelled for the kit it got
    jazz.horn_line(head, s.tempo, seed=4, **b.info['horn']).place(b.sax, a1)   # legato, live dynamics, vibrato ...
    print(b.describe())                               # + b.info['sounds'] (what plays), b.info['credits']

    python -m agentsound bands jazz                   # the presets, their roles and what they are tuned against

Presets (roles):
  jazz_trio     piano, comp, bass, drums                        medium swing, the 'salon' room (a wooden club room)
  jazz_quartet  piano, comp, bass, drums, sax                   + tenor (legato, live dynamics, vibrato), 224XL plate
  jazz_ballad   piano, comp, bass, drums, sax                   pedal(), brush stirs, bass='pizz' | 'arco', chamber
  bossa         guitar, piano, bass, drums, rim, shaker, sax    straight 8ths: nylon guitar, cross-stick, egg shaker

Every role plays the best installed pack and falls back to GeneralUser GS (never an error at import or build unless
strict=True): piano = Salamander Grand (SFZ, release samples) > its SoundFont > GeneralUser 'Grand Piano'; bass =
Meatbass pizz (4 layers x 5 takes: no two walking notes alike) > D. Smolken pizz > GeneralUser 'Acoustic Bass';
drums = Swirly Drums brush kit (stirs, taps, digs) > GeneralUser 'Brush' kit; sax = MTG tenor (legato player, soft /
loud x 3 takes) > FreePats tenor (SFZ, legato) > GeneralUser 'Tenor Sax'; guitar = FreePats nylon > GeneralUser
'Nylon Guitar'; rim = AVL Blonde Bop side stick > GeneralUser standard kit; shaker = FreePats egg shaker > GeneralUser
shaker; the ballad's arco bass = Meatbass arco (legato, live dynamics) > GeneralUser 'Double Bass'. Each candidate
carries a trim (SOUNDS) so the balance holds with whichever plays.
band.info: 'sounds' (what each role got), 'credits' (licences to credit), 'kit' / 'sweep' / 'stir' (the brush
keymap, the stir length and how brushes() levels the kit), 'horn' (horn_line options for the sax that was picked),
'feel', 'room', 'plate', 'master_gain' (+ 'rim_keys' / 'shaker_keys' in bossa, 'bass' in the ballad).

Stage (audience view): piano left (-0.5; comping -0.3: the lid opens to the room), bass centre, drums right (+0.35),
sax in front (centre); bossa: guitar left, cross-stick and shaker right with the drums. Sampled / SoundFont
instruments are placed with their own pan (see _place). Balance, measured on the demos (dry tracks): the lead (piano
right hand / sax) -18.5..-20.5 LUFS, comping 5-6 dB under, bass 3.5-5.7 dB, brushes 13-15 dB under (DRUM_TRIM:
3 dB softer than first calibrated, 10-12 dB under, which the user heard as "Drums etwas zu laut"); mixes at
-14.1..-14.9 LUFS integrated, LRA 5.2-7 LU, no report warnings under the 'jazz' profile, every full-band section
within 1 dB of the stereo centre (an intro of piano or guitar alone leans ~2 dB left).

Options (on top of bands.make's without= / sounds= / ids=):
  space   the shared room: 'salon' (Voxengo 18th-century salon IR, RT60 0.8 s - trio / quartet / bossa), 'club'
          (Lexicon 224XL room, 0.7 s), 'chamber' (224XL chamber, 2.1 s - the ballad), 'room' (jazz.band()'s
          algorithmic 1.2 s room; an IR space whose pack is missing falls back to it)
  plate   the leads' second return: 'ir' (224XL plate A), 'rich' (224XL rich plate), 'algorithmic', None (none)
  master  True: a broad low-mid dip, a little width above 150 Hz, gentle glue, tape, air and a light limiter;
          master_gain= sets the limiter drive (MASTER_GAIN per preset)
  strict  True: a missing preferred pack raises (naming `python -m agentsound samples fetch <id>`) instead of
          falling back
  feel    a jazz.Feel (default: swing by the tempo; bossa plays straight)
  duck    (quartet, bossa) False: no 1.5 dB sidechain of the comping / guitar under the sax
  bass    (ballad) 'pizz' (default) or 'arco'
"""

from __future__ import annotations

import random

from .. import bands, library
from .. import jazz as _jz
from .. import patches as _patches
from ..patches import Instrument, Patch, fx, inst
from ..patterns import Clip, Note, _as_prog, seed_int
from ..theory import ComposeError

__all__ = ['SOUNDS', 'SPACES', 'PLATES', 'MASTER_GAIN', 'DRUM_TRIM', 'GM_KIT', 'SHAKER_KEYS', 'installed', 'brushes',
           'pedal', 'bossa_groove', 'jazz_trio', 'jazz_quartet', 'jazz_ballad', 'bossa']


# ------------------------------------------------------------------------------------------------ sounds

def installed(pack: str) -> bool:
    """Is sample pack `pack` installed (python -m agentsound samples)?"""
    return (library.SAMPLES / pack / 'SOURCE.json').is_file()


def _patch(name: str, **params) -> Patch:
    """A library patch without its default sends (the preset makes its own returns)."""
    p = _patches.get(name)
    p = p.with_mix(sends={k: None for k in p.sends})
    return p.but(**params) if params else p


class _Opt:
    """One candidate sound for a role: the pack it needs (None = always there), a factory, a description, a trim
    (dB on the role's fader so every candidate lands at the role's level), a credit and hints (kit keymap ...)."""

    def __init__(self, pack, make, desc, trim=0.0, credit='', **hints):
        self.pack, self.make, self.desc, self.trim, self.credit, self.hints = pack, make, desc, trim, credit, hints

    def available(self) -> bool:
        return self.pack is None or installed(self.pack)


GM_KIT = {'kick': 36, 'rim': 37, 'tap': 38, 'hat_foot': 44, 'hat': 42, 'ride': 51}
"""GeneralUser standard kit keys (37 = side stick: the bossa cross-stick fallback)."""

SHAKER_KEYS = {'freepats': {'shake': 55, 'soft': 56, 'slow': 54}, 'gm': {'shake': 82, 'soft': 70, 'slow': 82}}
"""Egg shaker keys: FreePats World Percussion (54 slow, 55 fast, 56 soft; 16 takes each) / the GM fallback."""

_CC_BY_SALAMANDER = 'Salamander Grand Piano V3 - Alexander Holm, CC-BY 3.0'
_MEATBASS = 'Meatbass - Karoryfer Samples, CC0'

SOUNDS: dict[str, list[_Opt]] = {
    'piano': [
        _Opt('salamander-grand', lambda: _patch('sampled/jazz_grand', width=0.6, polyphony=160),
             'Salamander Grand Piano V3 (SFZ: Yamaha C5, 16 velocity layers, release samples; voiced warm: '
             'softened hammers)', 0.0,
             _CC_BY_SALAMANDER, piano='salamander'),
        _Opt('salamander-grand-v3-sf2', lambda: _jz.sampled('piano'),
             'Salamander Grand Piano V3 (SoundFont, no release samples)', -14.4, _CC_BY_SALAMANDER,
             piano='salamander'),
        _Opt(None, lambda: inst.sf2('Grand Piano', width=2.0, level=7.4), 'GeneralUser GS Grand Piano (fallback)',
             -8.0, piano='generaluser'),
    ],
    'bass': [
        _Opt('meatbass', lambda: _patch('sampled/upright_bass'),
             'Meatbass pizz (Karoryfer 1958 upright, 4 velocity layers x 5 takes, finger noise)', 0.0, _MEATBASS),
        _Opt('dsmolken-double-bass',
             lambda: inst.sfz('samples/dsmolken-double-bass/d_smolken_rubner_bass_pizz.sfz', lazy=True, level=0.0),
             'D. Smolken double bass pizz (3 layers x 5 round robins)', 6.7, 'D. Smolken double bass, CC0'),
        _Opt(None, lambda: inst.sf2('Acoustic Bass', level=0.0), 'GeneralUser GS Acoustic Bass (fallback)', -4.3,
             gm=True),
    ],
    'arco': [
        _Opt('meatbass', lambda: inst.sfz('samples/meatbass/Programs/01_arco_modwheel.sfz', lazy=True, level=3.0,
                                          mono='legato', legatotime=90),
             'Meatbass arco (Karoryfer; live dynamics on the mod wheel, legato)', -2.3, _MEATBASS),
        _Opt(None, lambda: inst.sf2('Double Bass', level=0.0, mono='on'),
             'GeneralUser GS Double Bass (bowed; fallback)', -4.7, gm=True),
    ],
    'drums': [
        _Opt('swirly-drums', lambda: _patch('sampled/brush_kit', width=1.7),
             'Swirly Drums brush kit (Karoryfer: stirs, taps, digs, close + room mics)', 0.0,
             'Swirly Drums - Karoryfer Samples, CC0', kit=_jz.SWIRLY_BRUSH),
        _Opt(None, lambda: inst.sf2(bank=128, program=40, width=1.2, level=12.0),
             'GeneralUser GS Brush kit (fallback)', -3.0, kit=_jz.GM_BRUSH),
    ],
    'sax': [
        _Opt('mtg-solo-sax', lambda: _patch('sampled/tenor_sax'),
             'MTG tenor saxophone (legato player: soft / loud x 3 takes, breath and key noises)', 0.0,
             'MTG Solo Saxophones (MTG / Freesound, SFZ by kinwie) - CC-BY 4.0',
             horn={'param': 'dynamics', 'vibrato': True, 'glide': 0.2}),
        _Opt('freepats-tenor-sax', lambda: inst.sfz('samples/freepats-tenor-sax/TenorSaxophone-20200717.sfz',
                                                     lazy=True, level=0.0, mono='legato', legatotime=60),
             'FreePats tenor saxophone (SFZ, looped, legato)', -6.3, 'FreePats Tenor Saxophone, CC0',
             horn={'param': 'expression', 'vibrato': True, 'glide': 0.2}),
        _Opt(None, lambda: inst.sf2('Tenor Sax', mono='on', level=2.0), 'GeneralUser GS Tenor Sax (fallback)', -1.0,
             horn={'param': 'expression', 'vibrato': False}, bright=True),   # it has its own delayed vibrato
    ],
    'guitar': [
        _Opt('freepats-spanish-classical-guitar', lambda: _patch('sampled/nylon_guitar'),
             'FreePats Spanish classical guitar (nylon strings)', 0.0, 'FreePats Spanish Classical Guitar, CC0'),
        _Opt(None, lambda: inst.sf2('Nylon Guitar', level=0.0), 'GeneralUser GS nylon guitar (fallback)', 1.2),
    ],
    'rim': [
        # width=0: the kit's own drummer-view pan of the side stick (-0.2) would pull it back to the centre
        _Opt('avl-blonde-bop', lambda: _patch('sampled/jazz_kit', width=0.0),
             'AVL Blonde Bop side stick (5 velocity layers)',
             0.0, 'AVL Drumkits Blonde Bop - Glen MacArthur, CC-BY-SA 3.0', keys={'rim': 37}),
        _Opt(None, lambda: inst.sf2(bank=128, program=0, level=0.0),
             'GeneralUser GS standard kit side stick (fallback)', -4.0, keys={'rim': GM_KIT['rim']}),
    ],
    'shaker': [
        _Opt('freepats-world-percussion',
             lambda: inst.sfz('samples/freepats-world-percussion/WorldPercussion 20200905.sfz', lazy=True, level=0.0),
             'FreePats egg shaker (World Percussion, 16 takes per gesture)', 0.0, 'FreePats World Percussion, CC0',
             keys=SHAKER_KEYS['freepats']),
        _Opt(None, lambda: inst.sf2(bank=128, program=0, level=0.0), 'GeneralUser GS shaker (fallback)', 2.0,
             keys=SHAKER_KEYS['gm']),
    ],
}
"""Role -> candidate sounds, best first (the first installed one plays). trim = dB on the role's fader that keeps
the balance with that sound: measured against the first candidate on the demo songs (songs/_bands/<preset>) and on a
calibration line (the SoundFont Salamander, D. Smolken, FreePats tenor)."""

_SOUND_ROLE = {'comp': 'piano'}      # roles that play another role's instrument (one piano, two hands)


def _pick(role: str, strict: bool) -> _Opt:
    opts = SOUNDS[role]
    if strict and not opts[0].available():
        raise ComposeError(f"band role {role!r} wants the sample pack {opts[0].pack!r} ({opts[0].desc}); install it "
                           f"with `python -m agentsound samples fetch {opts[0].pack}` (or leave strict=False: "
                           f"{next(o for o in opts if o.available()).desc})")
    return next(o for o in opts if o.available())


def _place(snd, pan: float):
    """(sound, track pan) that put a part at `pan` on the stage. A track's pan is a gentle balance control (the far
    side only loses level: -0.35 = 1.4 dB), which barely moves a stereo recording - the Salamander's melody register
    sits right of centre by itself - so sampled and SoundFont instruments are placed with their own 'pan' param and
    the track stays centred. On the sampler that is a stronger balance on stereo zones (pan -0.5: the right channel
    -6 dB, the recording's own image kept inside it: the Salamander's right hand lands ~-0.2) and a true pan on mono
    zones, added to the zone's own sfz pan (a kit's drummer-view spread: the presets zero it with width=0 where one
    piece is a role of its own, e.g. the cross-stick)."""
    ins = snd.instrument if isinstance(snd, Patch) else (Instrument.coerce(snd) if isinstance(snd, dict) else snd)
    if isinstance(ins, Instrument) and ins.type in ('sampler', 'sf2') and 'pan' not in ins.params:
        return (snd.but(pan=pan) if isinstance(snd, Patch) else ins.but(pan=pan)), 0.0
    return snd, pan


def _is_sound(snd, patch: str, pack: str) -> bool:
    """Is a sounds= override library patch `patch` or an sfz instrument read from sample pack `pack`?"""
    if snd is None:
        return False
    if (snd if isinstance(snd, str) else getattr(snd, 'name', None)) == patch:
        return True
    ins = getattr(snd, 'instrument', snd)
    lazy = getattr(ins, 'lazy', None) or {}
    params = getattr(ins, 'params', None) or {}
    where = f"{lazy.get('path', '')} {params.get('path', '')}" if isinstance(lazy, dict) else ''
    return pack in where.replace('\\', '/')


def _is_swirly(snd) -> bool:
    return _is_sound(snd, 'sampled/brush_kit', 'swirly-drums')


# ------------------------------------------------------------------------------------------------ space

SPACES = {
    'salon':   ('voxengo-im-reverbs', 'bus/ir_salon', {'predelay': 8, 'lowcut': 200, 'highcut': 10000}),
    'club':    ('little-devil-224xl-04-room', 'bus/ir_room', {'predelay': 6, 'lowcut': 200, 'highcut': 10000}),
    'chamber': ('little-devil-224xl-06-chamber', 'bus/ir_chamber', {'predelay': 12, 'lowcut': 300,
                                                                    'highcut': 9500}),
    'room':    (None, None, {}),
}
"""space= -> (pack, return patch, convolver params). The salon is the default of the trio / quartet / bossa: a
modelled real wooden room (distinct early reflections, RT60 0.8 s) - on the trio demo it reads 17 LU under the mix
with tails of -37 dB (the algorithmic room: 15 LU, -35 dB; the 224XL room 16 LU, -38 dB), close and intimate. The
chamber (2.1 s, high-passed at 300 Hz so it does not thicken the low mids) carries the ballad."""

PLATES = {
    'ir':          ('little-devil-224xl-13-cd-plate-a', 'bus/ir_plate', {'predelay': 25, 'lowcut': 280,
                                                                         'highcut': 9000, 'width': 1.3}),
    'rich':        ('little-devil-224xl-14-rich-plate', 'bus/ir_plate_rich', {'predelay': 30, 'lowcut': 320,
                                                                              'highcut': 9500}),
    'algorithmic': (None, None, {}),
}
"""plate= -> (pack, return patch, convolver params); a missing pack falls back to the algorithmic plate."""


def _return(s, bid: str, table: dict, which: str, what: str, strict: bool, fallback, fallback_desc: str):
    if which not in table:
        raise ComposeError(f"{what} must be one of {', '.join(table)}" + (' or None' if what == 'plate' else '')
                           + f", got {which!r}")
    pack, patch, params = table[which]
    if patch is not None and installed(pack):
        return s.bus(bid, _patches.get(patch).but(**params)), patch + (f" ({which})" if what == 'space' else '')
    if patch is not None and strict:
        raise ComposeError(f"{what} {which!r} needs the IR pack {pack!r}: `python -m agentsound samples fetch {pack}`")
    return s.bus(bid, fallback), fallback_desc


def _algo_room():
    return [fx.reverb(type='room', mix=1.0, decay=1.2, size=0.45, predelay=12, lowcut=200, highcut=9000,
                      damping=6500, early=0.6, width=1.1)]


def _algo_plate():
    return [fx.reverb(type='plate', mix=1.0, decay=1.9, predelay=28, lowcut=280, highcut=8500, damping=6000,
                      width=1.2)]


MASTER_GAIN = {'jazz_trio': 5.5, 'jazz_quartet': 5.0, 'jazz_ballad': 5.5, 'bossa': 6.0}
"""Limiter drive per preset (dB): lands the demo songs at -14.1..-14.9 LUFS integrated (the jazz profile: -16..-13)."""


def _master(s, preset: str, gain) -> float:
    g = MASTER_GAIN[preset] if gain is None else float(gain)
    # a broad low-mid / mid dip: piano, tenor and upright all live at 250 Hz - 2 kHz and pile up there (every demo
    # read +3.5..+5.5 dB lowmid / mid against the jazz profile before it), presence (the demos still read -2..-3 dB
    # at 2.5-6 kHz: dull next to a produced jazz record) and a little air on top
    s.master.add(fx.eq({'hp.freq': 28, 'peak1.freq': 450, 'peak1.gain': -1.8, 'peak1.q': 0.6,
                        'peak2.freq': 1300, 'peak2.gain': -1.2, 'peak2.q': 0.7, 'peak3.freq': 3800,
                        'peak3.gain': 1.5, 'peak3.q': 0.6, 'high.freq': 10000, 'high.gain': 1.2}),
                 # a little more side above 150 Hz: the tenor and the bass sit in the middle, and with the sax
                 # centred the quartet read 14 % wide (narrow for the jazz profile's 15..80 %)
                 fx.width(width=1.15, monobass=150),
                 fx.compressor(threshold=-22, ratio=1.5, knee=10, attack=30, release=350, detector='rms', keyhp=120),
                 fx.tape(speed='15', drive=1.5, bump=1.0, wow=0.04, flutter=0.04),
                 fx.limiter(gain=g, release=220, ceiling=-1.2))
    return g


# ------------------------------------------------------------------------------------------------ chains

SOFT_PIANO = {
    'attack': dict(threshold=-12, ratio=1.6, knee=10, attack=1.0, release=70, detector='peak', makeup=0.7),
    'tape': dict(speed='15', drive=2.0, bias=0.15, bump=0.5, wow=0.0, flutter=0.0, hiss=0.0),
}
"""The Salamander chain's softening (see _piano_chain): the attack rounder (peaks over -15 dBFS - the loudest hits
of the instrument's own level, before the fader - squeezed 1.8:1 for ~80 ms, +1 dB makeup: the level the preset's
fader was measured with; the right hand only) and the tape's level-dependent HF compression."""


def _piano_chain(opt, comp: bool = False) -> list:
    """The piano's eq (comp=True: the left hand's track also clears the bass's octave below ~90 Hz); the narrow
    GeneralUser piano also gets jazz.band()'s mid/side widener with mono lows."""
    hp = 90 if comp else 45
    if opt is not None and opt.hints.get('piano') == 'generaluser':
        return [fx.eq({'hp.freq': hp, 'low.freq': 180, 'low.gain': -2.0, 'peak1.freq': 350, 'peak1.gain': -4.0,
                       'peak1.q': 0.7, 'peak2.freq': 1200, 'peak2.gain': -2.0, 'peak2.q': 0.8, 'high.freq': 9000,
                       'high.gain': 2.5}),
                fx.width(width=_jz.PIANO_WIDTH['generaluser'], monobass=120)]
    # Salamander (a close-miked C5): less of the 150-400 Hz body the spaced pair piles up under a trio (it read
    # +6 dB low-mid against the jazz profile unequalized) and air on top. User feedback 2026-09-30
    # (perry-street-rain): "es klingt hart ... eine Sound-Design-Frage" - the close-miked grand's loud notes were
    # glassy and percussive: the sound is sampled/jazz_grand (softened hammers: the loud layers darker, the soft
    # ones clearer; the broad +1 dB at 3.2 kHz now mostly reaches the soft ones), air at 11 kHz, 1 dB more low-mid
    # cut on the right hand (the darker loud layers read heavier there), the attacks of the loud notes rounded (a
    # fast, soft-knee compressor that only reaches the loudest hits and lets go within ~80 ms: the body and the
    # note-to-note dynamics stay) and a touch of tape (loud highs saturate first: the last glassy edge of a hard
    # attack; no wow / flutter on a piano). SOFT_PIANO has the numbers. The left hand (comp=True) is soft: tape
    # only, without the head bump in its low mids.
    return [fx.eq({'hp.freq': hp, 'low.freq': 160, 'low.gain': -2.0, 'peak1.freq': 310,
                   'peak1.gain': -4.0 if comp else -5.0, 'peak1.q': 0.7, 'peak3.freq': 3200, 'peak3.gain': 1.0,
                   'peak3.q': 0.6, 'high.freq': 11000, 'high.gain': 1.5}),
            *([] if comp else [fx.compressor(**SOFT_PIANO['attack'])]),
            fx.tape(**{**SOFT_PIANO['tape'], **({'bump': 0.0} if comp else {})})]


BASS_MAKEUP = 6.3
"""dB after the pizz bass's peak catcher: what the old compressor's automakeup gave the Meatbass at the preset gains
(measured on songs/perry-street-rain: every section's bass within +-0.3 dB of the compressed chain at velocities
~80-96; softer lines now really are softer - the velocity is the level)."""


def _bass_chain(opt, arco: bool = False, sub: float = -5.0) -> list:
    if opt is not None and opt.hints.get('gm'):
        eq = fx.eq({'hp.freq': 45, 'peak1.freq': 170, 'peak1.gain': -2.5, 'peak1.q': 0.9,
                    'peak2.freq': 850, 'peak2.gain': 2.0, 'peak2.q': 1.2})
    elif arco:
        eq = fx.eq({'hp.freq': 35, 'peak1.freq': 220, 'peak1.gain': -2.0, 'peak1.q': 0.9,
                    'peak3.freq': 2500, 'peak3.gain': -1.5, 'peak3.q': 0.8})
    else:
        # Meatbass: round and woody - a little less 180 Hz box, a little more finger (900 Hz), and the sub of a
        # close-miked upright tamed (a real one radiates little below 60 Hz: it read +10 dB sub against the profile;
        # `sub` = that shelf: the ballad's long two-feel notes keep more of it, see jazz_ballad); a gentle 400 Hz dip
        # since the uncompressed plucks keep their 250-800 Hz attack (the bass's low-mid share rose ~4 points
        # without the old compressor: the ballad demo read +0.7 dB low-mid / mid over its limit)
        eq = fx.eq({'hp.freq': 42, 'hp.slope': 24, 'low.freq': 90, 'low.gain': sub, 'peak1.freq': 180,
                    'peak1.gain': -2.5, 'peak1.q': 1.0, 'peak2.freq': 900, 'peak2.gain': 2.0, 'peak2.q': 1.1,
                    'peak3.freq': 400, 'peak3.gain': -1.5, 'peak3.q': 0.9, 'high.freq': 7000, 'high.gain': -1.0})
    if arco:
        # bowed: the dynamics are mod-wheel swells over long legato notes (automation, not note attacks)
        return [eq, fx.compressor(threshold=-22, ratio=2.5, knee=8, attack=25, release=220, automakeup='on'),
                fx.width(width=0.5, monobass=150)]
    # pizz: a peak catcher only. The old bus-style compressor (threshold -22, 2.5:1, 25 ms attack, automakeup) sat
    # ~10 dB into every note and squeezed a line with velocities 57-103 into 3.8 dB of note-to-note spread with
    # 0.0 dB explained by the velocities (flat_dynamics). This one only touches the hardest plucks (the Meatbass
    # peaks about -4 dBFS at velocity 100): a fast, soft-kneed 3:1 above -9 dBFS, so accents, ghosts and phrase arcs
    # stay as played; the fixed makeup stands in for the old automakeup (the preset gains stay as calibrated).
    return [eq, fx.compressor(threshold=-9, ratio=3.0, knee=6, attack=1.5, release=90, makeup=BASS_MAKEUP),
            fx.width(width=0.5, monobass=150)]


def _drum_chain() -> list:
    # brushes: the feathered kick's boom (it masked the bass's sub) and the snare's 400 Hz box out, a little room
    # at 3.5 kHz for the lead's presence, the stir's hiss a little softer
    return [fx.eq({'hp.freq': 80, 'hp.slope': 24, 'low.freq': 120, 'low.gain': -3.0, 'peak1.freq': 400,
                   'peak1.gain': -1.5, 'peak1.q': 0.8, 'peak3.freq': 3500, 'peak3.gain': -2.0, 'peak3.q': 0.9,
                   'high.freq': 9000, 'high.gain': -1.0})]


def _sax_chain(opt) -> list:
    """Tenor: less 400 Hz box and 1.1 kHz honk (the MTG tenor read +4 dB mid against the jazz profile without it),
    breath on top (not on GeneralUser's already bright tenor), a gentle leveller and a Haas-style microshift: the horn
    stays a point in front of the band with a little stereo air around it (a close-miked tenor alone is ~1 % wide)."""
    bright = opt is not None and opt.hints.get('bright')
    return [fx.eq({'hp.freq': 90, 'peak1.freq': 400, 'peak1.gain': -3.5, 'peak1.q': 0.8,
                   'peak2.freq': 1100, 'peak2.gain': -3.5, 'peak2.q': 0.8, 'peak3.freq': 3500,
                   'peak3.gain': -3.0 if bright else 0.0, 'peak3.q': 0.8, 'high.freq': 6000,
                   'high.gain': -1.0 if bright else 1.5}),
            fx.compressor(threshold=-20, ratio=2.0, knee=8, attack=15, release=180, automakeup='on'),
            fx.microshift(style='smooth', detune=3, delay=14, focus=300, mix=0.32)]


# ------------------------------------------------------------------------------------------------ builder

_PLACE = {   # audience view: piano stage left (lid open to the room), drums stage right, bass between, sax in front
    'piano': -0.5, 'comp': -0.3, 'bass': 0.05, 'drums': 0.35, 'sax': 0.0,
}
"""Instrument pans (see _place). Measured positions on the demos (stereo.png): the Salamander right hand -0.2 (its
treble sits right of centre in the recording), comping -0.25, bass centre, brushes +0.4, sax centre (at +0.2 with the
drums on the right the quartet leaned 1-1.8 dB right in every section)."""

_COMMON = ('without', 'sounds', 'ids', 'space', 'plate', 'master', 'master_gain', 'strict', 'feel')


class _Builder:
    """Shared plumbing of the jazz presets: option checks, the returns, a sound per role (sounds= overrides keep the
    role's chain), ids, without=, placement, credits, the master."""

    def __init__(self, song, preset: str, options: dict, extra: tuple, notes: str, space: str, plate):
        bad = set(options) - set(_COMMON + extra)
        if bad:
            raise ComposeError(f"band {preset!r}: unknown option(s) {', '.join(sorted(bad))}; options: "
                               f"{', '.join(_COMMON + extra)}")
        self.s, self.preset, self.options = song, preset, options
        self.without = set(options.get('without') or ())
        self.sounds = dict(options.get('sounds') or {})
        self.ids = dict(options.get('ids') or {})
        self.strict = bool(options.get('strict', False))
        self.band = bands.Band(song, preset, notes=notes, analysis={'profile': 'jazz'})
        self.band.info.update(sounds={}, credits=[])
        self.room, self.band.info['room'] = _return(song, 'room', SPACES, options.get('space', space), 'space',
                                                    self.strict, _algo_room(), 'algorithmic room 1.2 s')
        self.band.bus('room', self.room)
        self.plate = None
        pl = options.get('plate', plate)
        if pl is not None:
            self.plate, self.band.info['plate'] = _return(song, 'plate', PLATES, pl, 'plate', self.strict,
                                                          _algo_plate(), 'algorithmic plate 1.9 s')
            self.band.bus('plate', self.plate)

    def wants(self, role: str) -> bool:
        return role not in self.without

    def sends(self, room=None, plate=None) -> dict | None:
        out = {self.room.id: room} if room is not None else {}
        if plate is not None and self.plate is not None:
            out[self.plate.id] = plate
        return out or None

    def sound(self, role: str, sound_role: str | None = None):
        """(instrument / patch, option or None, description) for a role. The comping follows a sounds= override of
        the piano (one instrument, two hands) unless it has its own."""
        key = role if role in self.sounds else ('piano' if role == 'comp' and 'piano' in self.sounds else None)
        if key is not None:
            snd = self.sounds[key]
            if isinstance(snd, str):
                snd = _patch(snd)
            elif isinstance(snd, Patch) and snd.sends:
                snd = snd.with_mix(sends={k: None for k in snd.sends})
            elif not isinstance(snd, (Patch, Instrument, dict)):
                raise ComposeError(f"sounds[{role!r}] must be a patch name, a Patch or an instrument, got {snd!r}")
            return snd, None, f"{getattr(snd, 'name', None) or getattr(snd, 'type', 'custom')} (sounds= override)"
        opt = _pick(sound_role or _SOUND_ROLE.get(role, role), self.strict)
        if opt.credit and opt.credit not in self.band.info['credits']:
            self.band.info['credits'].append(opt.credit)
        return opt.make(), opt, opt.desc

    def track(self, role: str, chain, *, sound_role=None, gain_db=0.0, pan=0.0, sends=None, groove=None,
              humanize=None):
        """The role's track: its sound (+ the candidate's trim) placed at `pan`, `chain(opt)` as its inserts, the
        sends, groove and humanize; recorded on the Band. Returns (track, option or None)."""
        snd, opt, desc = self.sound(role, sound_role)
        snd, track_pan = _place(snd, pan)
        t = self.s.track(self.ids.get(role, role), snd, fx=chain(opt),
                         gain_db=gain_db + (opt.trim if opt is not None else 0.0), pan=track_pan, sends=sends)
        if groove is not None:
            t.groove(groove)
        if humanize is not None:
            t.humanize(*humanize)
        self.band.add(role, t)
        self.band.info['sounds'][role] = desc
        return t, opt

    def drums(self, opt) -> None:
        """band.info kit / sweep / stir for the brush kit the drums got (an override: judged by its patch / file)."""
        swirly = opt.hints['kit'] == _jz.SWIRLY_BRUSH if opt is not None else _is_swirly(self.sounds.get('drums'))
        # a Swirly stir is a ~0.6 s swell with an exponential tail that the next stir crossfades: one about every
        # second keeps the 'shhh' continuous (half bars at medium swing, beats at ballad tempos)
        sweep = _jz.swirly_sweep(self.s.tempo, self.s.beats_per_bar) if swirly else None
        self.band.info.update(kit=dict(_jz.SWIRLY_BRUSH if swirly else _jz.GM_BRUSH), sweep=sweep,
                              stir=(1.9, 0.8) if swirly else (1.0, 1.0))

    def sax(self, *, gain=1.7, room=-9, plate=-11):
        if not self.wants('sax'):
            return None
        t, opt = self.track('sax', _sax_chain, gain_db=gain, pan=_PLACE['sax'], sends=self.sends(room, plate))
        if opt is not None:
            self.band.info['horn'] = dict(opt.hints['horn'])
        else:       # a sounds= override: the MTG tenor (by patch or file) keeps its live dynamics
            mtg = next(o for o in SOUNDS['sax'] if o.pack == 'mtg-solo-sax')
            self.band.info['horn'] = (dict(mtg.hints['horn']) if _is_sound(self.sounds['sax'], 'sampled/tenor_sax',
                                                                            'mtg-solo-sax')
                                      else {'param': 'expression', 'vibrato': True})
        return t

    def duck_under_sax(self, role: str) -> None:
        """The comping / guitar gives the sax ~1.5 dB (a sidechain keyed by the sax) - room for the lead."""
        if 'sax' in self.band and role in self.band and self.options.get('duck', True):
            self.s.sidechain(self.band[role], key=self.band['sax'], threshold=-34, depth=1.5, attack=20, hold=60,
                             release=350)

    def finish(self):
        if self.options.get('master', True):
            self.band.info['master_gain'] = _master(self.s, self.preset, self.options.get('master_gain'))
        return self.band


DRUM_TRIM = -3.0
"""dB on every jazz preset's drums (and the bossa's cross-stick) on top of the fader first measured on the demos.
User feedback 2026-09-30 on songs/lanterns-on-carmine: "Drums etwas zu laut" - the brushes sat 10.8-13 dB (RMS)
under the lead per section, but brush taps, digs and kick bombs are transient (crest ~29 dB): their peaks reached
-5.7 dBFS, as high as the sax's and the piano's. A club trio / quartet recording keeps the drums clearly behind the
piano and the horn: the brushes now sit ~14-16 dB (RMS) under the lead in every section."""


def _rhythm_section(bb: _Builder, feel, *, piano_sends=(-11.5, -24), comp_send=-12, bass_send=-18, drum_send=-10,
                    piano_gain=6.5, comp_gain=1.5, bass_gain=-5.0, drum_gain=1.5, bass_role='bass', bass_sub=-5.0):
    """piano + comp + bass + drums of the trio / quartet / ballad (gains: measured on their demos; the drums get
    DRUM_TRIM on top)."""
    bb.band.info['feel'] = feel
    if bb.wants('piano'):
        bb.track('piano', _piano_chain, gain_db=piano_gain, pan=_PLACE['piano'], sends=bb.sends(*piano_sends),
                 groove=feel.groove('piano'), humanize=(4, 5))
    if bb.wants('comp'):
        bb.track('comp', lambda o: _piano_chain(o, comp=True), gain_db=comp_gain, pan=_PLACE['comp'],
                 sends=bb.sends(comp_send), groove=feel.groove('comp'), humanize=(4, 5))
    if bb.wants('bass'):
        bb.track('bass', lambda o: _bass_chain(o, arco=bass_role == 'arco', sub=bass_sub), sound_role=bass_role,
                 gain_db=bass_gain, pan=_PLACE['bass'], sends=bb.sends(bass_send), groove=feel.groove('bass'),
                 humanize=(3, 4))
    if bb.wants('drums'):
        _, opt = bb.track('drums', lambda o: _drum_chain(), gain_db=drum_gain + DRUM_TRIM, pan=_PLACE['drums'],
                          sends=bb.sends(drum_send), groove=feel.groove('drums'), humanize=(2, 4))
        bb.drums(opt)


def _swing_feel(song, options):
    return options.get('feel') or _jz.Feel(song.tempo, beats_per_bar=song.beats_per_bar)


# ------------------------------------------------------------------------------------------------ presets

_TRIO_NOTES = """\
Play it (medium swing 120-180 BPM; every track already swings by the tempo and sits where it belongs):
  piano  right hand C4-C6, velocity 75-95 (the Salamander's soft layers are real pianissimo), melody / solo lines;
         a melody written at one level reads flat: jazz.touch(line, lo, hi) phrases it (lo 50-60 / hi 90-110,
         climax up to 120; about 0.22 dB per velocity step) - it plays ~3 dB louder on average and its accents
         reach the master limiter, so trim band.piano.gain_db by ~2.5 dB (drums stay 13-16 dB under it)
  comp   left hand rootless voicings: jazz.comp(prog, register=('A2', 'G4'), answer=melody, intensity 0.3-0.7)
  bass   jazz.walking_bass(prog, key=s.key, vel=80-95): two-feel for the first head, walking after; E1-G3; its
         touch (4-bar arcs, accents, ghosts) is on by default, a hand-written line gets jazz.bass_touch(line, lo, hi);
         the chain keeps the note-to-note dynamics, so vel is the level (a pedal intro ~80, 60-70 is really soft)
  drums  jazzband.brushes(band, bars, style=, vel=0.6-1.25) (agentsound.bandlib.jazz: jazz.brushes keyed for the
         kit, the Swirly stirs levelled against the taps): a stir about every second (band.info['sweep']: half
         bars at medium swing), taps on 2 and 4, fills every 8 bars;
         jazz.brush_fill('swell', kit=band.info['kit']) into a new chorus / the last chord
Balance (dry tracks, measured on the demo): piano line -19 LUFS, comping 5 dB under it, bass 5.5 dB, brushes 13 dB
under (clearly behind the piano: DRUM_TRIM).
Returns: room (the whole band: sends -18..-10), plate (piano right hand -24).
Automate: velocities per chorus (the arc: LRA 5+ LU), send.room up on the last chord; nothing else is needed."""


def jazz_trio(song, *, without=(), sounds=None, ids=None, **options):
    """New York club piano trio: grand piano (right hand + comping), upright bass, brushes, one wooden room."""
    bb = _Builder(song, 'jazz_trio', dict(options, without=without, sounds=sounds, ids=ids), (), _TRIO_NOTES,
                  'salon', 'algorithmic')
    _rhythm_section(bb, _swing_feel(song, options))
    return bb.finish()


_QUARTET_NOTES = """\
Play it: the trio (see jazz_trio) + the tenor. The sax takes the heads and the first solo, the piano comps
sparser under it (register=('A2', 'G4'), answer=the sax line; shells or garland behind the solo).
  sax    written straight in Bb3-D5 (sounding; the tenor's range D#2-E5), velocity 75-100 (the soft layer) and
         101-115 (the loud one: a solo climax); ALWAYS through the horn phrasing:
         jazz.horn_line(line, s.tempo, seed=..., **band.info['horn']).place(band.sax, section) - swing + lay-back
         baked in, legato transitions inside phrases (no re-attacks), breaths, scoops into phrase starts, falls
         at phrase ends, swells on the live dynamics, a delayed growing vibrato, portamento into some leaps
         (band.info['horn'] carries param / vibrato / glide for the sax sound that was picked)
  comp   ducks ~1.5 dB under the sax (a sidechain keyed by the sax): room for the lead without riding faders
Balance: sax -18.5 LUFS (as loud as the piano's melody), comping 5.5 dB under, bass 5.5 dB, brushes 14 dB under.
Returns: room (all; sax -9), plate (sax -11, piano right hand -24)."""


def jazz_quartet(song, *, without=(), sounds=None, ids=None, **options):
    """Tenor sax quartet: the trio + a played tenor (legato, live dynamics, delayed vibrato, scoops and falls)."""
    bb = _Builder(song, 'jazz_quartet', dict(options, without=without, sounds=sounds, ids=ids), ('duck',),
                  _QUARTET_NOTES, 'salon', 'ir')
    _rhythm_section(bb, _swing_feel(song, options), comp_gain=3.0, bass_gain=-4.0)
    bb.sax()
    bb.duck_under_sax('comp')
    return bb.finish()


_BALLAD_NOTES = """\
Play it (56-80 BPM, swing ratio ~0.66 from the feel; everything laid back):
  piano  melody C4-C6 at velocity 60-92, rolled chords; the sustain pedal changing with the harmony:
         jazzband.pedal([band.piano, band.comp], prog, at) (up at every change, down 0.1 beat later)
  comp   jazz.comp(prog, style='ballad', register=('A2', 'G4'), intensity 0.25-0.45) - held, rolled chords
  bass   bass='pizz' (default): walking_bass(feel='two', gate=0.97, vel=80-90), long notes (a little more sub
         than the other presets: the long notes' body); bass='arco': long bowed notes,
         legato (overlap them), articulation.perform(band.bass, line, at) or 'instrument.dynamics' swells (0.3..0.8)
  drums  jazzband.brushes(band, bars, style='ballad', kick=None or 'feather'): a continuous stir (one per beat
         below ~109 BPM: band.info['sweep'] = jazz.swirly_sweep(tempo)), soft taps on 2 and 4; brush_fill('swell')
         into the last chord
  sax    horn_line(..., **band.info['horn']) with long notes: swells and a delayed vibrato carry the ballad
  time   s.rubato(intro), s.ritardando into the last chord; Song(tail=6): the chamber rings
Balance: the lead (sax / piano melody) -20.5..-21 LUFS, comping 6 dB under, bass 3.5 dB, brushes 15 dB under.
Returns: room (the 224XL chamber: sends -16..-9), a rich plate on the leads (sax -12, piano -18)."""


def jazz_ballad(song, *, without=(), sounds=None, ids=None, **options):
    """Late-night ballad band: pedalled grand, brush stirs, pizz or arco bass, tenor in a rich plate."""
    bass_kind = options.pop('bass', 'pizz')
    if bass_kind not in ('pizz', 'arco'):
        raise ComposeError(f"jazz_ballad bass must be 'pizz' or 'arco', got {bass_kind!r}")
    bb = _Builder(song, 'jazz_ballad', dict(options, without=without, sounds=sounds, ids=ids), (), _BALLAD_NOTES,
                  'chamber', 'rich')
    bb.band.info['bass'] = bass_kind
    _rhythm_section(bb, _swing_feel(song, options), piano_sends=(-12, -18), comp_send=-13, bass_send=-16,
                    drum_send=-9, comp_gain=2.5, bass_gain=0.5, drum_gain=4.5, bass_sub=-3.5,
                    bass_role='arco' if bass_kind == 'arco' else 'bass')
    bb.sax(room=-12, plate=-12)
    return bb.finish()


_BOSSA_NOTES = """\
Play it (straight 8ths, 120-145 BPM; the feel only lays the parts back a few ms):
  guitar  jazz.comp(prog, style='bossa', voicing='drop2', register=('E3', 'E5'), vel=60-75).strum(ms=12, bpm=)
          (the two-bar bossa cells, fingers); velocity 60-75. Piano comping instead: without=('guitar',) and
          jazz.comp(prog, style='bossa') on band.piano
  piano   melody or fills C4-C6, velocity 75-90
  bass    root-fifth in the bossa's dotted rhythm (1 . . & | 3 . . &): prog.bass(pattern='R__f', rate='1/8',
          low='C2', vel=80-88, gate=0.85) (its pattern accents reach 117: the bass fader is 3 dB lower than the
          trio's for that)
  drums / rim / shaker  jazzband.bossa_groove(bars, band, seed=...) -> {'drums', 'rim', 'shaker'} clips keyed for
          the sounds: brush 8ths on the snare + kick 1 / &2 / 3 / &4 + hat foot on 2 and 4, the 2-bar cross-stick
          pattern (1 &2 4 | &1 3), the egg shaker in 8ths (backstrokes accented)
  sax     Getz: soft and airy - horn_line(..., ratio=0.5, scoop=0.2, fall=0.1, swell_db=(-6, -1, -8), **horn)
Balance: lead -19.5 LUFS, guitar 5 dB under, bass 5 dB, drums 14 dB, rim 15.5 dB, shaker 15 dB under (DRUM_TRIM).
Stage: guitar left (-0.45), piano -0.5 (its melody register lands near the centre), bass and sax centre, drums
+0.35, cross-stick +0.25, shaker +0.5 (the percussion opposite the guitar). The guitar ducks ~1.5 dB under the sax.
Returns: room (all), plate (sax -15, piano -18)."""


def bossa(song, *, without=(), sounds=None, ids=None, **options):
    """Bossa nova group: nylon guitar comping, piano, upright bass, brushes + cross-stick + egg shaker, tenor."""
    bb = _Builder(song, 'bossa', dict(options, without=without, sounds=sounds, ids=ids), ('duck',), _BOSSA_NOTES,
                  'salon', 'ir')
    feel = options.get('feel') or _jz.Feel(song.tempo, ratio=0.5, beats_per_bar=song.beats_per_bar,
                                           layback={'piano': 8, 'comp': 4, 'sax': 18})
    bb.band.info['feel'] = feel
    if bb.wants('guitar'):
        bb.track('guitar', lambda o: [fx.eq({'hp.freq': 80, 'peak1.freq': 250, 'peak1.gain': -2.0, 'peak1.q': 0.9,
                                             'peak3.freq': 3000, 'peak3.gain': 1.0, 'peak3.q': 0.8}),
                                      fx.microshift(style='smooth', detune=2, delay=13, focus=250, mix=0.28)],
                 gain_db=-0.5, pan=-0.45, sends=bb.sends(-12), groove=feel.groove('comp'), humanize=(3, 5))
    if bb.wants('piano'):
        bb.track('piano', _piano_chain, gain_db=10.0, pan=_PLACE['piano'], sends=bb.sends(-13, -18),
                 groove=feel.groove('piano'), humanize=(4, 5))
    if bb.wants('bass'):
        # -9 (was -6 before the peak-catcher chain): the bossa's root-fifth pulse plays at velocity 85-117, where
        # the uncompressed bass is ~3 dB louder than the old compressor let it be
        bb.track('bass', _bass_chain, gain_db=-9.0, pan=0.05, sends=bb.sends(-18), groove=feel.groove('bass'),
                 humanize=(3, 4))
    if bb.wants('drums'):
        _, opt = bb.track('drums', lambda o: _drum_chain(), gain_db=-1.0 + DRUM_TRIM, pan=0.35, sends=bb.sends(-11),
                          groove=feel.groove('drums'), humanize=(2, 4))
        bb.drums(opt)
    if bb.wants('rim'):
        _, opt = bb.track('rim', lambda o: [fx.eq({'hp.freq': 150, 'peak1.freq': 500, 'peak1.gain': -2.0,
                                                   'peak1.q': 1.0, 'high.freq': 8000, 'high.gain': -1.5})],
                          gain_db=5.0 + DRUM_TRIM, pan=0.25, sends=bb.sends(-10), groove=feel.groove('drums'),
                          humanize=(2, 5))
        bb.band.info['rim_keys'] = dict(opt.hints['keys']) if opt is not None else {'rim': GM_KIT['rim']}
    if bb.wants('shaker'):
        _, opt = bb.track('shaker', lambda o: [fx.eq({'hp.freq': 300, 'high.freq': 9000, 'high.gain': -2.0})],
                          gain_db=-6.0, pan=0.5, sends=bb.sends(-12), groove=feel.groove('drums'),
                          humanize=(3, 6))
        bb.band.info['shaker_keys'] = dict(opt.hints['keys']) if opt is not None else dict(SHAKER_KEYS['gm'])
    bb.sax(gain=2.8, room=-12, plate=-15)
    bb.duck_under_sax('guitar')
    return bb.finish()


# ------------------------------------------------------------------------------------------------ helpers

def brushes(band, bars, style: str = 'medium', **kw) -> Clip:
    """jazz.brushes() for the brush kit a band got - a preset's Band (band.info kit / sweep / stir) or jazz.band()'s
    (its .kit / .sweep / .stir): its keymap, its sweep length and the stir levelled against the taps. A Swirly Drums
    stir is ~19 dB under a tap at the same velocity (a stir at velocity 50 is inaudible under a band), so the
    (stir, tap) velocity factors (1.9, 0.8) lift the sweeps and soften the taps / digs / slaps; the sweep length
    (jazz.swirly_sweep: a stir about every second) keeps the 'shhh' continuous under the taps - the groove itself
    (the presets' drum faders are set for it). Every jazz.brushes option
    works (vel=, ride=, fills=, kick=, kit=, sweep= ...)."""
    info = band.info if isinstance(getattr(band, 'info', None), dict) else {
        'kit': band.kit, 'sweep': band.sweep, 'stir': band.stir}
    kit = kw.setdefault('kit', info.get('kit', _jz.GM_BRUSH))
    kw.setdefault('sweep', info.get('sweep'))
    c = _jz.brushes(bars, style, **kw)
    fs, ft = info.get('stir', (1.0, 1.0))
    if fs == 1.0 and ft == 1.0:
        return c
    stirs = {kit.get(r) for r in ('sweep', 'sweep_fast')} - {None}
    taps = {kit.get(r) for r in ('tap', 'slap', 'dig')} - {None}

    def level(n):
        f = fs if n.pitch in stirs else ft if n.pitch in taps else 1.0
        return n if f == 1.0 else n._replace(vel=max(1, min(127, int(round(n.vel * f)))))
    return Clip._raw([level(n) for n in c], c.length)


def pedal(tracks, prog, at=0.0, *, lift: float = 0.1, end=None) -> list:
    """Sustain pedal that follows the harmony (legato pedalling) on one or more piano tracks (the comping and the
    right hand share one pedal): up at every chord change of `prog` (a Progression placed at `at`, a beat or a
    Section), down again `lift` beats later, up at the end (the progression's end or `end`). Returns the points."""
    p = _as_prog(prog, None, 4.0)
    a = float(getattr(at, 'start', at))
    starts = sorted({a + st for st, _, c in p if c is not None})
    if not starts:
        return []
    stop = a + p.length if end is None else float(getattr(end, 'start', end))
    pts: list = []
    for st in starts:
        if st >= stop:
            break
        pts += [(st, 0.0, 'step'), (st + lift, 1.0, 'step')]
    pts.append((stop, 0.0, 'step'))
    for t in (tracks if isinstance(tracks, (list, tuple)) else [tracks]):
        t.automate('instrument.pedal', pts)
    return pts


def bossa_groove(bars, band, *, seed=0, vel: float = 1.0, fills: bool = True) -> dict:
    """The bossa kit parts for `bars` bars (4/4), keyed for the sounds `band` got: {'drums': brush 8ths on the snare,
    kick on 1 / &2 / 3 / &4, hat foot on 2 and 4 (and a tap fill into every 8th bar); 'rim': the 2-bar cross-stick
    pattern (1, &2, 4 | &1, 3); 'shaker': 8ths, backstrokes accented}. Straight: the feel lays them back. vel scales
    the levels; seeded velocity variation."""
    rng = random.Random(seed_int(seed))
    kit = band.info.get('kit', _jz.SWIRLY_BRUSH)
    rimk = band.info.get('rim_keys', {'rim': GM_KIT['rim']})['rim']
    shk = band.info.get('shaker_keys', SHAKER_KEYS['freepats'])
    n = int(bars)
    if n < 1:
        raise ComposeError(f"bossa_groove needs bars >= 1, got {bars!r}")

    def v(x):
        return max(1, min(127, int(round(x * vel * (1.0 + (rng.random() - 0.5) * 0.12)))))
    dr, rim, sh = [], [], []
    for b in range(n):
        t0 = 4.0 * b
        fill = fills and b % 8 == 7
        for k in range(8):                       # brush 8ths on the snare, the downbeats a touch heavier
            if not (fill and k >= 5):
                dr.append(Note(t0 + k * 0.5, 0.25, kit['tap'], v(34 if k % 2 else 44)))
        if fill:                                 # a triplet crescendo into the next phrase
            for k, t in enumerate((2.5, 2.8333, 3.1667, 3.5, 3.8333)):
                dr.append(Note(t0 + t, 0.2, kit['tap'], v(40 + 8 * k)))
        for pos, lv in ((0.0, 44), (1.5, 34), (2.0, 40), (3.5, 34)):
            dr.append(Note(t0 + pos, 0.25, kit['kick'], v(lv)))
        for pos in (1.0, 3.0):
            dr.append(Note(t0 + pos, 0.2, kit['hat_foot'], v(42)))
        for pos in ((0.0, 1.5, 3.0) if b % 2 == 0 else (0.5, 2.0)):
            rim.append(Note(t0 + pos, 0.2, rimk, v(80 if pos in (0.0, 2.0) else 70)))
        for k in range(8):
            sh.append(Note(t0 + k * 0.5, 0.25, shk['shake'] if k % 2 else shk['soft'], v(78 if k % 2 else 52)))
    L = 4.0 * n
    return {'drums': Clip._raw(dr, L), 'rim': Clip._raw(rim, L), 'shaker': Clip._raw(sh, L)}


# ------------------------------------------------------------------------------------------------ registry

# Every role falls back to GeneralUser GS, so no pack is strictly required (strict=True makes the preferred ones so).
bands.register('jazz_trio', jazz_trio, genre='jazz', roles=('piano', 'comp', 'bass', 'drums'),
               description='NYC club piano trio: Salamander grand (right hand + comping), Meatbass upright, Swirly '
                           'brushes, one wooden room (salon IR)',
               tuned="jazz profile, -14.7 LUFS, 0 warnings; songs/_bands/jazz_trio (medium swing 144 BPM)")
bands.register('jazz_quartet', jazz_quartet, genre='jazz', roles=('piano', 'comp', 'bass', 'drums', 'sax'),
               description='the trio + a played MTG tenor (legato, live dynamics, delayed vibrato, scoops / falls), '
                           'salon room + 224XL plate, comping ducks under the sax',
               tuned="jazz profile, -14.1 LUFS, 0 warnings; songs/_bands/jazz_quartet (medium swing 132 BPM)")
bands.register('jazz_ballad', jazz_ballad, genre='jazz', roles=('piano', 'comp', 'bass', 'drums', 'sax'),
               description="late-night ballad: pedalled grand, brush stirs, bass='pizz' | 'arco' (Meatbass), "
                           'tenor in a rich plate, 224XL chamber',
               tuned="jazz profile, -14.9 LUFS, 0 warnings; songs/_bands/jazz_ballad (66 BPM, rubato, ritardando)")
bands.register('bossa', bossa, genre='jazz', roles=('guitar', 'piano', 'bass', 'drums', 'rim', 'shaker', 'sax'),
               description='bossa nova: nylon guitar comping, piano, upright, brushes + cross-stick + egg shaker, '
                           'airy tenor (straight 8ths)',
               tuned="jazz profile, -14.1 LUFS, 0 warnings; songs/_bands/bossa (132 BPM)")
