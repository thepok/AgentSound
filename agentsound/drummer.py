"""A drummer: named, reusable drum MOVES and an arranger that plays a whole song form - grooves per style and
section, fills into sections, crashes, builds, stops and an ending - with two hands and two feet.

The pianist's shape for the drums (HUMAN_FEEDBACK 2026-09-30: "möglichst realistische, nicht keyboard-artige
Instrumente"; drum ghost notes; "fills and transitions"; flat velocities sound robotic). A drummer is not a loop:
the verse is calmer than the chorus, the hi-hat moves to the ride for the big parts, fills lead into sections (and
now and then into a new 4- or 8-bar phrase - never every bar: a BUDGET keeps them spice, and the flashy ones rarer
still), the crash lands on section downbeats together with the kick, the pre-chorus builds, the break stops, the
backbeat is strong and the ghosts whisper (velocity 15-35), and every limb has its own timing.

    from agentsound import drummer
    part = drummer.arrange(s, style='rock', density=0.6, seed=3, kit=b.drums)     # the whole song form
    part.play(b.drums)                     # = b.drums.play(part.clip, part.start); switches the track's humanize off
    drummer.arrange(s, style='funk', kit=b.drums, lock=b.bass, lock_mode='answer')  # the kick against the bass
    print(part.summary(), part.plan)
    b.drums.play(drummer.tom_run(2, s.tempo, kit=b.drums), verse.bar(-1, 2), replace=True)   # one move

LIMBS: every hit is played by one limb - 'R' (right hand: the hi-hat / ride / crash, toms), 'L' (left hand: snare,
ghosts), 'RF' (kick) and 'LF' (hi-hat foot). arrange() never gives a limb two strokes closer than it can play (a
groove stroke 70 ms, a roll stroke 40 ms, the kick foot 80 ms), never opens the hi-hat while the foot closes it,
and never plays a crash without the kick. check(part) lists violations (none for what arrange() plays).

KIT: pieces are played by name ('kick', 'snare', 'hat', 'hat_open', 'hat_pedal', 'ride', 'bell', 'crash', 'crash2',
'side', 'rimshot', toms 'tom1'.. (high -> low), 'floor' ...) and mapped to the kit's keys: Kit.of(track | instrument |
'gm' | 'big_rusty' | 'unruly' | 'swirly' | 'gm_brush' | {piece: key}) reads which keys a sampled kit really has
(the band presets' kits: Big Rusty, Unruly, the Chart kit without toms, the Linn/909 machines, the Swirly brushes)
and falls back where a piece is missing (no ride: the hat keeps time; no toms: the fills stay on the snare).

Reused helpers: patterns.snare_roll (rolls and the 8ths -> 16ths -> 32nds build), patterns.tom_fill (the tom run
grid and crescendo), patterns.brushes / brush_fill / ride_pattern (the jazz style), patterns.seed_int / Clip.
humanize.touch() shapes melodic phrases; drums get the drum-specific touch here (levels per stroke role, phrase
arcs, accents) - the report's flat_dynamics ear judges melodic parts.
"""

from __future__ import annotations

import math
import random

from .patterns import (GM_BRUSH, SWIRLY_BRUSH, Clip, Note, _vel, as_clip, brush_fill as _brush_fill,
                       brushes as _brushes, ride_pattern as _ride_pattern, seed_int, snare_roll as _snare_roll,
                       tom_fill as _tom_fill)
from .budget import Budget
from .theory import ComposeError

__all__ = ['Kit', 'KITS', 'STYLES', 'ROLES', 'TIMEKEEPERS', 'MODES', 'FILL_KINDS', 'FLASHY', 'MOVES', 'Memory',
           'Performance', 'Hit',
           'arrange', 'beat', 'check', 'tom_run', 'snare_run', 'triplet_fill', 'flam_fill', 'linear_fill', 'pickup',
           'roll', 'build', 'stop', 'dropout', 'swell', 'crash_hit', 'open_hat', 'count_in', 'brushes', 'ride',
           'Hands', 'HANDS', 'STROKE_HELP', 'ORCHESTRATIONS', 'RUDIMENTS', 'FEET', 'MOTIF_VARIATIONS', 'SOLO_MOVES',
           'DrumMotif', 'SoloContext', 'strokes', 'sticking_problems', 'perform_hits', 'pattern', 'rudiment', 'feet',
           'double_bass', 'choke', 'hat_dance', 'hat_lane', 'perform', 'solo_move', 'SOLO_ROLES', 'vocabulary']

_EPS = 1e-6
_TOGETHER_MS = 15.0          # strokes closer than this count as simultaneous
_GAP_MS = {'R': 70.0, 'L': 70.0, 'RF': 80.0, 'LF': 100.0}     # one limb, groove strokes
_ROLL_GAP_MS = 40.0          # one hand inside a roll / fill (double strokes, buzz)
_ROLL_TAGS = {'fill', 'roll', 'build', 'swell', 'grace'}
LIMBS = ('R', 'L', 'RF', 'LF')


# ------------------------------------------------------------------------------------------------ helpers

def _num(x, what: str, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ComposeError(f"{what} must be a finite number, got {x!r}")
    if (lo is not None and x < lo) or (hi is not None and x > hi):
        rng = f"{lo:g}.." if hi is None else f"..{hi:g}" if lo is None else f"{lo:g}..{hi:g}"
        raise ComposeError(f"{what} = {x:g} is outside {rng}")
    return float(x)


def _bpm(bpm) -> float:
    return _num(bpm, 'drummer bpm', 20, 400)


def _ms(ms: float, bpm: float) -> float:
    """Milliseconds -> beats."""
    return ms / 1000.0 * bpm / 60.0


def _beats_ms(beats: float, bpm: float) -> float:
    return beats * 60000.0 / bpm


def _tri(rng: random.Random) -> float:
    return rng.random() + rng.random() - 1.0


def _pos(at) -> float:
    if hasattr(at, 'start') and not isinstance(at, (int, float)):
        return float(at.start)
    return _num(at, 'at (beats)', 0)


def _steps(cell: str) -> list[int]:
    return [i for i, c in enumerate(cell) if c in 'xX']


def _pick(rng: random.Random, weights: dict, avoid=()):
    items = [(k, w * (0.15 if k in avoid else 1.0)) for k, w in weights.items() if w > 0]
    if not items:
        return None
    tot = sum(w for _, w in items)
    x = rng.random() * tot
    for k, w in items:
        x -= w
        if x <= 0:
            return k
    return items[-1][0]


# ------------------------------------------------------------------------------------------------ the kit

_GM = dict(kick=36, kick2=35, snare=38, side=37, clap=39, hat=42, hat_pedal=44, hat_open=46, ride=51, bell=53,
           crash=49, crash2=57, china=52, splash=55, tamb=54, cowbell=56, toms=(50, 48, 47, 45, 43, 41))

KITS: dict[str, dict] = {
    'gm': _GM,
    # Karoryfer Big Rusty (rock_kit('big_rusty')): 40 rimshot, 39 snare edge, 54 hat shank (the accented hat), 56 hat
    # foot splash, 52 ride crash, 53 bell; toms 47 14", 45 15", 43 18", 41 22" (48 / 50 are copies of 47); 57 is a
    # crash copy (rock_kit remaps it), no china / splash / clap / tambourine keys.
    'big_rusty': dict(kick=36, kick2=35, snare=38, side=37, rimshot=40, edge=39, hat=42, hat_shank=54, hat_pedal=44,
                      hat_open=46, hat_splash=56, ride=51, bell=53, ride_crash=52, crash=49, crash2=57,
                      toms=(47, 45, 43, 41)),
    # Karoryfer Unruly (rock_kit('unruly')): toms 47 13", 45 14", 41 22" floor (43 = the floor tom's edge), 55 ride
    # crash, 52 ride choke.
    'unruly': dict(kick=36, kick2=35, snare=38, side=37, rimshot=40, edge=39, hat=42, hat_shank=54, hat_pedal=44,
                   hat_open=46, hat_splash=56, ride=51, bell=53, ride_crash=55, crash=49, crash2=57,
                   toms=(47, 45, 41)),
    # brush kits (patterns.SWIRLY_BRUSH / GM_BRUSH): 'snare' = a brush tap; the jazz style plays patterns.brushes()
    # the sampled/big_rusty_kit patch's layout (its keymap): 52 china, 91 ride crash, 57 the sizzle crash, chokes on
    # 88 crash / 89 ride / 90 china; 46 the variable hat (its opening is the live 'dynamics' param: hat_lane())
    'big_rusty_kit': dict(kick=36, snare=38, side=37, rimshot=40, edge=39, hat=42, hat_shank=54, hat_pedal=44,
                          hat_open=46, hat_splash=56, ride=51, bell=53, ride_crash=91, crash=49, crash2=57, china=52,
                          crash_choke=88, ride_choke=89, china_choke=90, toms=(47, 45, 43, 41), live_hat=True),
    # the sampled/unruly_kit patch: chokes on 88 crash / 89 ride
    'unruly_kit': dict(kick=36, kick2=35, snare=38, side=37, rimshot=40, edge=39, hat=42, hat_shank=54, hat_pedal=44,
                       hat_open=46, ride=51, bell=53, ride_crash=55, crash=49, crash_choke=88, ride_choke=89,
                       toms=(47, 45, 41), live_hat=True),
    # MF Natural (sampled/mf_natural_kit): snare and toms recorded per hand - hand_keys plays the left hand's samples
    # on the left hand's strokes (38 / 41 / 45) and the right hand's on the right's (40 / 43 / 47)
    'mf_natural': dict(kick=36, kick2=35, snare=38, side=37, rimshot=39, hat=42, hat_pedal=44, hat_open=46, ride=51,
                       bell=53, crash=49, crash2=57, china=52, splash=55, crash_choke=58, toms=(45, 41),
                       hand_keys={38: {'R': 40}, 45: {'R': 47}, 41: {'R': 43}}),
    'swirly': dict(kick=36, snare=38, edge=40, hat=42, hat_pedal=44, hat_open=46, ride=51, crash=49, crash2=57,
                   china=53, splash=55, toms=(48, 47, 45, 43, 41), brush=SWIRLY_BRUSH),
    'gm_brush': dict(kick=36, snare=38, side=37, hat=42, hat_pedal=44, hat_open=46, ride=51, bell=53, crash=49,
                     crash2=57, splash=55, toms=(48, 45, 43, 41), brush=GM_BRUSH),
}
"""Named kit maps: piece -> GM key (toms high -> low). 'gm' is the General MIDI map (every GM / SoundFont kit, the
engine's drum machine, kits built by inst.kit()); the Karoryfer kits have extra pieces (rimshot, snare edge, hat
shank) on their own keys; 'big_rusty_kit' / 'unruly_kit' / 'mf_natural' are the sampled/ patches' layouts (cymbal
chokes, per-hand samples: hand_keys {key: {'R': key}}); the brush kits carry the patterns.brushes keymap as 'brush'."""

_STIR = {'swirly': (1.9, 0.8)}
"""Brush-kit levelling (stir, tap) velocity factors - bandlib.jazz.brushes' values for the Swirly kit."""

_FALLBACK = {'rimshot': ('snare',), 'edge': ('snare',), 'hat_shank': ('hat',), 'hat_splash': ('hat_open',),
             'hat_open': ('hat',), 'hat_half': ('hat_open', 'hat'), 'bell': ('ride',), 'ride_crash': ('crash',), 'crash2': ('crash',),
             'china': ('crash2', 'crash'), 'splash': ('crash2', 'crash'), 'crash': ('crash2', 'ride', 'hat_open'),
             'kick2': ('kick',), 'clap': ('snare',)}
_PIECES = ('kick', 'kick2', 'snare', 'side', 'rimshot', 'edge', 'clap', 'hat', 'hat_shank', 'hat_pedal', 'hat_open',
           'hat_half', 'hat_splash', 'ride', 'bell', 'ride_crash', 'crash', 'crash2', 'china', 'splash', 'tamb',
           'cowbell', 'crash_choke', 'ride_choke', 'china_choke')
_CHOKES = {'crash': 'crash_choke', 'crash2': 'crash_choke', 'ride': 'ride_choke', 'ride_crash': 'ride_choke',
           'china': 'china_choke'}
"""Which choke key grabs which cymbal (a kit's choke sample, played right after the cymbal: its mute group)."""
_MAIN_PIECES = ('kick', 'snare', 'hat', 'hat_open', 'ride', 'crash')
"""The pieces that keep their key when another piece's key only copies the same samples."""


class Kit:
    """Which pieces a kit has and on which keys. Kit.of(x): x = a Track / Instrument / Patch (a sampled kit is read:
    only keys with samples count, tom copies are merged, Big Rusty / Unruly / Swirly are recognised by their files),
    a KITS name, a dict {piece: key} (with 'toms': (high .. low)) or None (General MIDI, every piece).
    key(piece) -> the key or None (after the fallbacks: no rimshot -> snare, no bell -> ride, no crash2 -> crash
    ...); toms -> the distinct toms high -> low; has(piece)."""

    def __init__(self, name: str, pieces: dict, toms=(), brush: dict | None = None, hand_keys: dict | None = None,
                 live_hat: bool = False):
        self.name = name
        self.pieces = dict(pieces)
        self.toms = tuple(toms)
        self.brush = brush
        self.hand_keys = {int(k): dict(v) for k, v in (hand_keys or {}).items()}
        self.live_hat = bool(live_hat)     # hat_open's key opens by the live 'dynamics' param (CC4 imported live)

    @classmethod
    def of(cls, x=None) -> 'Kit':
        if isinstance(x, Kit):
            return x
        if x is None:
            return cls._named('gm')
        if isinstance(x, str):
            if x not in KITS:
                raise ComposeError(f"unknown kit {x!r}; use one of {', '.join(KITS)}, a dict {{piece: key}}, a track "
                                   f"or an instrument")
            return cls._named(x)
        if isinstance(x, dict):
            return cls._custom(x)
        ins = getattr(x, 'instrument', None)          # a Track or a Patch
        ins = x if ins is None else ins
        if not hasattr(ins, 'type') or not hasattr(ins, 'params'):
            raise ComposeError(f"drummer kit: expected a track, an instrument, a kit name or a dict, got {x!r}")
        return cls._detect(ins)

    @classmethod
    def _named(cls, name: str, avail=None, same=None) -> 'Kit':
        m = KITS[name]
        pieces = {p: k for p, k in m.items() if p not in ('toms', 'brush', 'hand_keys', 'live_hat')
                  and (avail is None or k in avail)}
        if same is not None:
            # a key that only copies another piece's samples is not a second piece (Big Rusty / Unruly / the outrun
            # kit have 57 = a copy of the 49 crash): drop it, so its fallback plays the real one - never two strokes
            # of the same sample at once (a crash + 'crash2' final hit would just be the crash doubled, +6 dB)
            order = [p for p in _MAIN_PIECES if p in pieces] + [p for p in pieces if p not in _MAIN_PIECES]
            owner: dict = {}
            for p in order:
                f = same.get(pieces[p])
                if not f or p == 'hat_pedal':
                    continue
                if f in owner and owner[f] != pieces[p]:
                    del pieces[p]
                else:
                    owner.setdefault(f, pieces[p])
        toms = []
        seen = []
        for k in m.get('toms', ()):
            if avail is not None and k not in avail:
                continue
            if same is not None and same.get(k) and same.get(k) in seen:
                continue                                   # a copy of a tom already in the list
            seen.append(same.get(k) if same is not None else k)
            toms.append(k)
        hk = {k: {h: v for h, v in d.items() if avail is None or v in avail}
              for k, d in m.get('hand_keys', {}).items()}
        return cls(name, pieces, toms, m.get('brush'), hand_keys=hk, live_hat=m.get('live_hat', False))

    @classmethod
    def _custom(cls, d: dict) -> 'Kit':
        pieces, toms = {}, ()
        for p, k in d.items():
            if p == 'toms':
                toms = tuple(_key_num(t, 'toms') for t in (k if isinstance(k, (list, tuple)) else [k]))
            elif p in ('brush', 'hand_keys', 'live_hat'):
                continue
            elif p not in _PIECES and p != 'floor':
                raise ComposeError(f"drummer kit: unknown piece {p!r}; pieces: {', '.join(_PIECES)}, toms, brush")
            else:
                pieces[p] = _key_num(k, p)
        if 'floor' in pieces:
            toms = toms + (pieces.pop('floor'),)
        hk = {}
        for k, hd in (d.get('hand_keys') or {}).items():
            if not isinstance(hd, dict) or any(h not in ('R', 'L') for h in hd):
                raise ComposeError(f"drummer kit hand_keys: {{key: {{'R' | 'L': key}}}}, got {k!r}: {hd!r}")
            hk[_key_num(k, 'hand_keys')] = {h: _key_num(v, 'hand_keys') for h, v in hd.items()}
        return cls('custom', pieces, toms, d.get('brush'), hand_keys=hk, live_hat=bool(d.get('live_hat', False)))

    @classmethod
    def _detect(cls, ins) -> 'Kit':
        if ins.type == 'sampler':
            try:
                ins.expand()
            except (ComposeError, AttributeError, OSError):
                return cls._named('gm')
            zones = ins.params.get('samples') or []
            files: dict[int, set] = {}
            text = []
            for z in zones:
                lo, hi = z.get('lo', 0), z.get('hi', 127)
                f = str(z.get('file', ''))
                if len(text) < 64:
                    text.append(f.lower().replace('\\', '/'))
                if hi - lo <= 2:
                    for k in range(int(lo), int(hi) + 1):
                        files.setdefault(k, set()).add(f)
            blob = ' '.join(text)
            # the sampled/ patches move the kits' chokes to 88+ (big_rusty_kit / unruly_kit); the band presets'
            # rock_kit() keeps the pack's own keys
            name = ('big_rusty_kit' if 'big-rusty' in blob and 88 in files and 91 in files
                    else 'big_rusty' if 'big-rusty' in blob
                    else 'unruly_kit' if 'unruly' in blob and 88 in files and 89 in files
                    else 'unruly' if 'unruly' in blob else 'swirly' if 'swirly' in blob
                    else 'mf_natural' if 'mf-natural' in blob or 'mf-drumset' in blob else 'gm')
            same = {k: frozenset(v) for k, v in files.items()}
            kit = cls._named(name, avail=set(files), same=same)
            ho = kit.pieces.get('hat_open')
            kit.live_hat = ho is not None and any(
                isinstance(z, dict) and z.get('lo', 0) <= ho <= z.get('hi', 127)
                and ('dynLo' in z or 'dynHi' in z) for z in zones)
            return kit
        if ins.type == 'drums':          # the engine's drum machine
            return cls._named('gm', avail={35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 54,
                                           56, 57, 59})
        if ins.type == 'sf2' and ins.params.get('bank') == 128 and ins.params.get('program') == 40:
            return cls._named('gm_brush')
        return cls._named('gm')

    def has(self, piece: str) -> bool:
        return self.key(piece, fallback=False) is not None

    def key(self, piece: str, fallback: bool = True, limb: str | None = None) -> int | None:
        k = self._key(piece, fallback)
        if limb is not None and k is not None and k in self.hand_keys:
            return self.hand_keys[k].get(limb, k)
        return k

    def _key(self, piece: str, fallback: bool = True) -> int | None:
        if piece.startswith('tom') and piece[3:].isdigit():
            i = int(piece[3:]) - 1
            return self.toms[min(i, len(self.toms) - 1)] if self.toms else (self.key('snare') if fallback else None)
        if piece == 'floor':
            return self.toms[-1] if self.toms else (self.key('snare') if fallback else None)
        k = self.pieces.get(piece)
        if k is not None or not fallback:
            return k
        for alt in _FALLBACK.get(piece, ()):
            k = self.pieces.get(alt)
            if k is not None:
                return k
        return None

    def voices(self) -> list[str]:
        """The drums a hand can play a melody on, high -> low: the snare, then the toms ('tom1' ..)."""
        return ['snare'] + [f'tom{i + 1}' for i in range(len(self.toms))]

    def tom(self, i: int, n: int) -> str:
        """The i-th of n drums of a run across the toms (high -> low) as a piece name."""
        if not self.toms:
            return 'snare'
        j = min(len(self.toms) - 1, i * len(self.toms) // max(1, n))
        return f'tom{j + 1}'

    def __repr__(self) -> str:
        ps = ', '.join(f"{p}={k}" for p, k in self.pieces.items())
        return (f"Kit({self.name!r}: {ps}; toms {list(self.toms)}{'; brushes' if self.brush else ''}"
                f"{'; live hat' if self.live_hat else ''}{'; hand keys' if self.hand_keys else ''})")


def _sounding_keys(ins) -> set:
    """Keys a drum instrument has a sound on: a sampler's zones (not '*silence'), the drum machine's pieces; empty when
    unknown (a folder mapped by the engine, a stack, a SoundFont)."""
    if ins.type == 'drums':
        from .silent_notes import DRUM_MACHINE_KEYS
        return set(DRUM_MACHINE_KEYS)
    if ins.type != 'sampler':
        return set()
    try:
        ins.expand()
    except (ComposeError, AttributeError, OSError):
        return set()
    zones = ins.params.get('samples')
    if isinstance(zones, dict) and 'file' in zones:
        zones = [zones]
    if not isinstance(zones, list):
        return set()
    tr = ins.params.get('transpose', 0)
    tr = int(tr) if isinstance(tr, (int, float)) and not isinstance(tr, bool) else 0
    out = set()
    for z in zones:
        if isinstance(z, dict) and z.get('file') != '*silence':
            out.update(k - tr for k in range(int(z.get('lo', 0)), int(z.get('hi', 127)) + 1))
    return out


def _piece_of(kit: 'Kit', key: int) -> str:
    """The piece name a kit plays on `key` ('hat_open'), else 'key N'."""
    for p, k in kit.pieces.items():
        if k == key:
            return p
    if key in kit.toms:
        return f"tom{kit.toms.index(key) + 1}"
    return f"key {key}"


def missing_pieces(hits, kit: 'Kit') -> list[str]:
    """Warnings for the pieces a part plays that `kit` does not have: each is played on its fallback piece (no crash ->
    crash2 / ride / open hat, no rimshot -> snare ...) or, without one, left out."""
    counts: dict[str, int] = {}
    for h in hits:
        if not h.piece.startswith('#') and kit.key(_hat_piece(h, kit), fallback=False) is None:
            counts[h.piece] = counts.get(h.piece, 0) + 1
    out = []
    for piece, n in sorted(counts.items(), key=lambda x: -x[1]):
        alt = kit.key(piece)
        what = (f"the kit{'' if kit.name == 'gm' else f' {kit.name!r}'} has no {piece}: {n} {piece} "
                f"stroke{'s' if n != 1 else ''} ")
        if alt is None:
            out.append(what + f"left out (no fallback piece) - map a {piece} sample into the kit "
                              f"(inst.kit(..., map={{...}}) / Kit.of({{...}})) or layer a kit that has it")
        else:
            out.append(what + f"play on {_piece_of(kit, alt)} ({alt}) instead - map a real {piece} into the kit "
                              f"(inst.kit(..., map={{...}}), or a crash from another kit on its own track) if it "
                              f"should sound like one")
    return out


def _key_num(k, what: str) -> int:
    """A key: a MIDI number or a GM drum name (kits.GM_NAMES: 'snare2', 'tom_floor_hi', 'ride_bell' ...; or a
    patterns.DRUMS name)."""
    if isinstance(k, str):
        from .kits import _NAME_KEYS
        from .patterns import DRUMS
        name = k.strip().lower()
        if name in _NAME_KEYS:
            return _NAME_KEYS[name]
        if name in DRUMS:
            return DRUMS[name]
        raise ComposeError(f"drummer kit {what}: unknown GM drum name {k!r} (kits.GM_NAMES / patterns.DRUMS)")
    if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= 127:
        raise ComposeError(f"drummer kit {what}: keys are MIDI numbers 0..127 or GM names, got {k!r}")
    return k


# ------------------------------------------------------------------------------------------------ hits

class Hit:
    """One stroke: t (beats: on the grid, swung, before the feel's ms offset), piece, vel, limb ('R' 'L' 'RF' 'LF',
    or 'X' = a machine layer outside the limb rules), tag (what it is: time, backbeat, ghost, kick, open, pedal, crash, fill,
    roll, build, grace, swell, hit), prio (who wins a limb conflict), dur (beats), main (a flam grace's main stroke),
    off (the feel's timing offset in ms, set by arrange)."""

    __slots__ = ('t', 'piece', 'vel', 'limb', 'tag', 'prio', 'dur', 'main', 'off', 'bar', 'kind', 'open', 'fx')

    def __init__(self, t, piece, vel, limb, tag, prio=5, dur=0.25, main=None, bar=0):
        self.t, self.piece, self.vel, self.limb, self.tag = float(t), piece, float(vel), limb, tag
        self.prio, self.dur, self.main, self.off, self.bar = prio, dur, main, 0.0, bar
        self.kind = None        # the stroke type a solo pattern gave it: 'A' accent, 'T' tap, 'G' ghost (None: a groove)
        self.open = None        # hi-hat openness 0 (closed) .. 1 (open) for a hat stroke, None = the piece's own
        self.fx = None          # what a solo stroke carries out: 'flam' / 'drag' / 'buzz' (graces and bounces)

    def __repr__(self) -> str:
        return f"Hit({self.t:g}, {self.piece}, {self.vel:.0f}, {self.limb}, {self.tag}, off={self.off:+.1f}ms)"


_PRIO = {'crash': 9, 'hit': 9, 'backbeat': 8, 'fill': 7, 'build': 7, 'roll': 7, 'swell': 7, 'kick': 6, 'open': 6,
         'time': 5, 'grace': 5, 'pedal': 4, 'ghost': 2, 'layer': 1}


def _h(t, piece, vel, limb, tag, dur=0.25, prio=None, main=None) -> Hit:
    return Hit(t, piece, vel, limb, tag, _PRIO.get(tag, 5) if prio is None else prio, dur, main)


# ------------------------------------------------------------------------------------------------ styles

ROLES = {'intro': 0.38, 'verse': 0.42, 'pre': 0.6, 'chorus': 0.88, 'post': 0.7, 'bridge': 0.58, 'solo': 0.8,
         'break': 0.25, 'outro': 0.72, 'end': 0.85}
"""Section roles and their default energy (0..1): the level, how busy the kick and the hat are, ride vs hat,
rimshots, open hats. A section's role comes from its name (verse1 -> verse, 'pre-chorus' / 'build' / 'lift' ->
pre, 'hook' / 'refrain' / 'drop' -> chorus, 'middle8' -> bridge, 'breakdown' -> break, 'coda' / 'tag' -> outro,
'ending' / 'final' -> end; anything else plays like a verse) or plan={'name': {'role': ...}}. A repeated chorus
comes back a little stronger (+0.04 each time)."""

_ROLE_WORDS = (('pre', ('pre', 'build', 'lift', 'riser')), ('post', ('post',)),
               ('chorus', ('chorus', 'hook', 'refrain', 'drop')), ('bridge', ('bridge', 'middle')),
               ('solo', ('solo',)), ('break', ('break',)), ('outro', ('outro', 'coda', 'tag', 'fade')),
               ('end', ('end', 'final')), ('intro', ('intro',)), ('verse', ('verse', 'groove')))

TIMEKEEPERS = ('hat', 'hat8', 'hat16', 'hat4', 'hat_barks', 'hat_loose', 'ride', 'ride_bell', 'bell', 'floor',
               'crash', 'snare16', 'pedal', 'none')
"""What the time hand plays: hat (the style's hat rhythm), hat8 / hat16 / hat4 (closed hi-hat 8ths, 16ths -
one-handed, only up to ~135 BPM, faster falls back to 8ths - or quarters), hat_barks (closed on the beat, open on
every &: disco), hat_loose (a washy, half-open 8th-note hat: every stroke chokes the last), ride (8ths, the hat
foot on 2 and 4), ride_bell (the bell on the beats), bell (bell quarters), floor (floor-tom 8ths: a tom groove),
crash (crash-riding quarters), snare16 (both hands on the snare: the train beat), pedal (hat foot only), none."""

MODES = ('', 'half', 'four', 'time')
"""Groove modes (plan 'mode' or 'hat8/half'): '' the style's groove, 'half' half-time (the snare on 3), 'four' four on
the floor, 'time' only the time hand (the hat / ride alone: an intro, a breakdown)."""

_KICK_HALF = ('x.........x.....', 'x.....x...x.....', 'x..x......x.....')

STYLES: dict[str, dict] = {
    'rock': dict(kicks=(('x.......x.......', 'x.......x.x.....', 'x.....x.x.......'),
                        ('x.......x.x.....', 'x.....x.x.......', 'x.x.....x.x.....', 'x.......x.x...x.')),
                 snare=(4, 12), hat='hat8', ghosts={7: 0.3, 15: 0.35, 9: 0.2, 3: 0.15}, opens={14: 1.0, 6: 0.35},
                 time={'chorus': 'ride', 'solo': 'ride', 'outro': 'ride', 'bridge': 'floor'},
                 fills={'toms': 3.0, 'snare': 2.0, 'triplets': 0.8, 'flams': 0.6, 'linear': 0.4, 'pickup': 1.5},
                 feel={'R': -1.0, 'L': 3.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=6.0, rimshot=0.75, side=(),
                 crashes={'crash': 1.0, 'crash2': 0.7, 'ride_crash': 0.35, 'china': 0.12}, swing=0.5),
    'halftime': dict(kicks=(_KICK_HALF, ('x.........x.....', 'x.....x...x.....', 'x.x.......x..x..')),
                     snare=(8,), hat='hat8', ghosts={15: 0.35, 3: 0.2, 11: 0.2, 13: 0.2}, opens={14: 1.0, 6: 0.4},
                     time={'chorus': 'ride', 'solo': 'ride', 'outro': 'ride', 'bridge': 'floor'},
                     fills={'toms': 3.0, 'snare': 1.5, 'triplets': 1.2, 'flams': 0.8, 'linear': 0.5, 'pickup': 1.2},
                     feel={'R': -1.0, 'L': 4.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=6.0, rimshot=0.7, side=(),
                     crashes={'crash': 1.0, 'crash2': 0.7, 'ride_crash': 0.35, 'china': 0.2}, swing=0.5),
    'shuffle': dict(kicks=(('x.......x.......', 'x.....x.x.......'),
                           ('x.....x.x.......', 'x.......x.....x.', 'x.x.....x.x.....')),
                    snare=(4, 12), hat='hat8', ghosts={2: 0.35, 10: 0.35, 6: 0.15, 14: 0.15}, opens={14: 0.8},
                    time={'chorus': 'ride', 'solo': 'ride', 'outro': 'ride'},
                    fills={'triplets': 3.0, 'snare': 1.5, 'toms': 1.5, 'flams': 0.6, 'pickup': 1.5},
                    feel={'R': 0.0, 'L': 5.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=6.0, rimshot=0.8, side=(),
                    crashes={'crash': 1.0, 'crash2': 0.7}, swing=0.62, swing_grid=0.5),
    'pop': dict(kicks=(('x.........x.....', 'x.......x.......', 'x..x......x.....'),
                       ('x.....x...x.....', 'x..x..x...x.....', 'x.........x..x..', 'x.....x.x.......')),
                snare=(4, 12), hat='hat8', ghosts={7: 0.2, 15: 0.25, 11: 0.1}, opens={14: 1.0, 6: 0.3},
                time={'chorus': 'hat16', 'post': 'hat16', 'bridge': 'hat8/half', 'solo': 'ride', 'outro': 'hat16'},
                fills={'snare': 2.5, 'toms': 2.5, 'pickup': 2.0, 'flams': 0.8, 'triplets': 0.4},
                feel={'R': -1.0, 'L': 2.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=5.0, rimshot=2.0, side=(),
                crashes={'crash': 1.0, 'crash2': 0.8}, swing=0.5),
    'funk': dict(kicks=(('x.....x...x.....', 'x.........x..x..', 'x.......x.x.....'),
                        ('x.....x...x..x..', 'x.x...x...x..x..', 'x..x..x...x..x..', 'x.....x.x.x.....')),
                 snare=(4, 12), hat='hat16', ghosts={1: 0.2, 3: 0.35, 6: 0.3, 7: 0.7, 9: 0.6, 11: 0.35, 14: 0.3,
                                                     15: 0.6},
                 opens={14: 0.8, 6: 0.45, 10: 0.2},
                 time={'bridge': 'ride_bell', 'solo': 'ride_bell'},
                 fills={'snare': 2.5, 'linear': 1.5, 'toms': 1.5, 'pickup': 2.0, 'flams': 0.8},
                 feel={'R': -1.5, 'L': 1.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=4.0, rimshot=0.8, side=(),
                 crashes={'crash': 1.0, 'crash2': 0.8}, swing=0.54, swing_grid=0.25),
    'disco': dict(kicks=(('x...x...x...x...',), ('x...x...x...x...',)), four=True,
                  snare=(4, 12), hat='hat16', ghosts={7: 0.2, 15: 0.2}, opens={14: 0.6},
                  time={'chorus': 'hat_barks', 'post': 'hat_barks', 'outro': 'hat_barks', 'bridge': 'ride'},
                  fills={'snare': 3.0, 'toms': 2.0, 'pickup': 2.0, 'flams': 0.5},
                  feel={'R': -1.0, 'L': 1.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=4.0, rimshot=2.0, side=(),
                  crashes={'crash': 1.0, 'crash2': 0.7}, swing=0.5),
    'ballad': dict(kicks=(('x.......x.......', 'x.........x.....', 'x......x........'),
                          ('x.........x.....', 'x.......x.......', 'x......x..x.....')), end_roll='cymbal',
                   snare=(4, 12), hat='hat8', ghosts={15: 0.2, 7: 0.1}, opens={14: 0.6},
                   time={'intro': 'hat8', 'chorus': 'ride', 'solo': 'ride', 'outro': 'ride', 'bridge': 'floor'},
                   fills={'toms': 3.0, 'snare': 1.5, 'triplets': 1.0, 'flams': 0.5, 'pickup': 1.0},
                   feel={'R': 0.0, 'L': 6.0, 'RF': 1.0, 'LF': 0.0}, timing_ms=7.0, rimshot=0.8,
                   side=('intro', 'verse'), crashes={'crash': 1.0, 'crash2': 0.8}, swing=0.5),
    'motown': dict(kicks=(('x.....x.x.......', 'x.......x.x.....'), ('x.....x.x.......', 'x.x.....x.x.....')),
                   snare=(0, 4, 8, 12), accent=(4, 12), hat='hat8', ghosts={}, opens={14: 0.5},
                   time={'bridge': 'ride'},
                   fills={'snare': 3.0, 'pickup': 2.0, 'toms': 1.2, 'flams': 0.8},
                   feel={'R': 0.0, 'L': 2.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=6.0, rimshot=2.0, side=(),
                   crashes={'crash': 1.0, 'crash2': 0.6}, swing=0.5),
    'synthpop': dict(kicks=(('x.......x.......', 'x.......x.x.....'), ('x...x...x...x...',)), end_roll='cymbal',
                     snare=(4, 12), hat='hat16', ghosts={}, opens={14: 1.0, 6: 0.3}, machine=True,
                     time={'intro': 'hat8', 'verse': 'hat8', 'chorus': 'hat16/four', 'post': 'hat16/four',
                           'outro': 'hat16/four', 'bridge': 'hat8/half'},
                     fills={'toms': 3.0, 'snare': 2.0, 'pickup': 1.0},
                     feel={'R': 0.0, 'L': 0.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=0.8, rimshot=2.0, side=(),
                     crashes={'crash': 1.0}, swing=0.5, clap=True),
    'bossa': dict(special='bossa', builds=False, kicks=(('x.....x.x.....x.',), ('x.....x.x.....x.',)), snare=(),
                  hat='hat8',
                  ghosts={}, opens={}, time={'chorus': 'ride', 'solo': 'ride'},
                  fills={'snare': 2.0, 'pickup': 2.0, 'triplets': 1.0},
                  feel={'R': 0.0, 'L': 3.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=6.0, rimshot=2.0, side=(),
                  crashes={'crash': 1.0}, swing=0.5, soft=0.75),
    'jazz': dict(special='jazz', builds=False, kicks=((), ()), snare=(), hat='ride', ghosts={}, opens={},
                 time={},
                 fills={'triplets': 2.0, 'eighths': 1.5, 'slap': 1.0, 'toms': 0.5},
                 feel={'R': -2.0, 'L': 2.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=7.0, rimshot=2.0, side=(),
                 crashes={'crash': 1.0}, swing=0.5, soft=0.6),
    'train': dict(special='train', kicks=(('x.......x.......',), ('x.......x.x.....', 'x.....x.x.......')),
                  snare=(4, 12), hat='snare16', ghosts={}, opens={}, time={},
                  fills={'snare': 2.0, 'pickup': 2.0, 'toms': 1.0},
                  feel={'R': 0.0, 'L': 1.0, 'RF': 0.0, 'LF': 0.0}, timing_ms=5.0, rimshot=2.0, side=(),
                  crashes={'crash': 1.0, 'crash2': 0.7}, swing=0.5),
}
"""Drummer styles: kick cells (16th grids: (calm, busy) sets - a section picks a main cell and a variation for the
4th bar), snare backbeat steps, the hat rhythm, ghost-note candidates {16th step: weight}, open-hat candidates, the
timekeeper per section role (default: hat everywhere; 'name/half' = half-time, '/four' = four on the floor), fill
weights, the per-limb feel in ms (+ = late: a laid-back backbeat), the timing spread, the energy above which the
backbeat becomes a rimshot, the roles on side stick, crash pieces, the swing ratio (0.5 straight) and the ending
roll (end_roll: 'toms' rumble, or a 'cymbal' swell).
  rock       straight 8ths, hat verses, ride choruses, a floor-tom bridge, tom fills
  halftime   rock half-time: snare on 3
  shuffle    a light shuffle (8ths swung 0.62), triplet fills
  pop        8ths verse, 16ths chorus, half-time bridge, snare / tom fills and pickups
  funk       one-handed 16th hats, syncopated kick, lots of ghost notes, ride bell bridge, linear fills (16ths 0.54)
  disco      four on the floor, 16th hats, open hats on every & in the chorus
  ballad     side stick verses, snare choruses on the ride, a laid-back backbeat, big slow tom fills
  motown     snare on every beat (2 and 4 accented), hat 8ths
  synthpop   the 80s / outrun machine: tight (no drift), 16th hats with machine accents, a clap layer, tom runs
  bossa      cross-stick 2-bar clave, kick 1 &2 3 &4, hat 8ths, hat foot 2 and 4 (straight)
  jazz       straight-8th ride (or brushes on a brush kit: patterns.brushes), hat foot 2 and 4, a feathered kick,
             soft comping snare, brush / triplet fills (drums stay behind the piano: soft)
  train      the train beat: snare 16ths with both hands, accents on 2 and 4, kick 1 and 3"""

FILL_KINDS = ('pickup', 'snare', 'toms', 'triplets', 'flams', 'linear', 'roll', 'build', 'eighths', 'slap')
"""What arrange() plays into a section / a new phrase: pickup (one or two strokes into the downbeat), snare (16ths on
the snare, crescendo), toms (a run around the toms high -> low), triplets (8th-note triplets snare -> toms), flams
(flam accents down the kit), linear (hands and kick never together: R L K ...), roll (a snare roll crescendo),
build (8ths -> 16ths -> 32nds on the snare with the kick on the beats: the pre-chorus build); eighths / slap = the
jazz brush fills (patterns.brush_fill)."""

FLASHY = ('toms', 'triplets', 'flams', 'linear')
"""The showy fills (at 2 beats or longer): budgeted at least flashy_every bars apart, the same kind at least
same_every bars apart; where the budget says no, a plainer fill (snare 16ths, a pickup) takes the place."""

_LEVELS = {'kick': (72, 114), 'backbeat': (80, 122), 'side': (62, 96), 'ghost': (18, 30), 'hat': (50, 92),
           'ride': (58, 98), 'bell': (80, 112), 'floor': (70, 106), 'crash': (94, 118), 'crash_time': (74, 100),
           'open': (68, 104), 'pedal': (40, 64), 'fill': (76, 116), 'clap': (80, 112)}
"""Stroke levels (velocity at energy 0 .. 1): the verse's backbeat ~100, the chorus's ~120 (a sampled kit's layers
make that 3-5 dB), hat accents on the beats (the & x0.74, 16ths x0.55), ghosts 15-35 whatever the energy."""


def _lvl(what: str, e: float, soft: float = 1.0) -> float:
    lo, hi = _LEVELS[what]
    return (lo + (hi - lo) * max(0.0, min(1.0, e))) * soft


# ------------------------------------------------------------------------------------------------ context

class _Ctx:
    def __init__(self, kit: Kit, bpm: float, rng: random.Random, st: dict, density: float):
        self.kit, self.bpm, self.rng, self.st, self.density = kit, bpm, rng, st, density
        self.soft = st.get('soft', 1.0)

    def gap_ok(self, beats: float, limb: str = 'R') -> bool:
        return _beats_ms(beats, self.bpm) >= _GAP_MS[limb] - _EPS


def _trade_steps(st: dict, mode: str) -> tuple:
    """The accented backbeat steps, where the kick gives way to the snare (Motown's snare on every beat keeps the
    kick on 1 and 3: only 2 and 4 are the backbeat)."""
    if mode == 'half':
        return (8,)
    return tuple(st.get('accent') or st['snare'])


def _hat_rhythm(tk: str, st: dict, bpm: float) -> str:
    if tk == 'hat':
        tk = st['hat'] if st['hat'].startswith('hat') else 'hat8'
    if tk == 'hat16' and bpm * 4.0 / 60.0 > 9.0:       # one hand cannot keep 16ths above ~135 BPM
        tk = 'hat8'
    return tk


# ------------------------------------------------------------------------------------------------ one bar of groove

def _groove_bar(t0: float, sp: dict, ctx: _Ctx, bar: int, e: float) -> list[Hit]:
    """The time-keeping hits of one 4/4 bar (16th steps) of a section plan."""
    st, kit, rng = ctx.st, ctx.kit, ctx.rng
    special = st.get('special')
    if special == 'bossa':
        return _bossa_bar(t0, sp, ctx, bar, e)
    if special == 'train':
        return _train_bar(t0, sp, ctx, bar, e)
    out: list[Hit] = []
    tk, mode = sp['time'], sp['mode']
    q = 0.25
    soft = ctx.soft
    machine = st.get('machine', False)
    sparse = e < 0.3
    # --- the time hand
    hat_steps: list[int] = []
    if tk.startswith('hat') and tk != 'hat_pedal':
        rh = _hat_rhythm(tk, st, ctx.bpm)
        if sparse and rh in ('hat8', 'hat16') and not machine:
            rh = 'hat8' if rh == 'hat16' else 'hat4' if e < 0.2 else rh
        hat_steps = {'hat4': [0, 4, 8, 12], 'hat8': list(range(0, 16, 2)), 'hat16': list(range(16)),
                     'hat_barks': list(range(0, 16, 2)), 'hat_loose': list(range(0, 16, 2))}[rh]
        shank = kit.has('hat_shank') and e >= 0.7 and rh != 'hat16'
        for s in hat_steps:
            if s % 4 == 0:
                f = 1.0
            elif s % 2 == 0:
                f = 0.74 if rh != 'hat16' else 0.8
            else:
                f = 0.55
            if machine:
                f = {0: 1.0, 2: 0.8}.get(s % 4, 0.58)
            piece, tag, dur = 'hat', 'time', 0.25
            if rh == 'hat_barks' and s % 4 == 2:
                piece, tag, dur, f = 'hat_open', 'open', 0.5, 0.95
            elif rh == 'hat_loose':
                piece, dur, f = 'hat_open', 0.5, f * 0.82
            elif shank and s % 4 == 0:
                piece = 'hat_shank'
            h = _h(t0 + s * q, piece, _lvl('open' if tag == 'open' else 'hat', e, soft) * f, 'R', tag, dur)
            if rh == 'hat_loose':
                h.open = 0.45            # a washy half-open hat: the live hat's 'dynamics' lane on Big Rusty / Unruly
            out.append(h)
        if rh == 'hat_barks':
            for s in (0, 4, 8, 12):           # the foot closes each open & on the next beat
                out.append(_h(t0 + s * q, 'hat_pedal', _lvl('pedal', e, soft) * 0.8, 'LF', 'pedal'))
        # open-hat 'barks' on the style's candidates (not a machine's 16ths at every bar)
        if rh in ('hat8', 'hat16') and sp['open_p'] > 0:
            phrase_end = bar % 4 == 3
            for s, w in st['opens'].items():
                if s not in hat_steps:
                    continue
                p = w * sp['open_p'] * (1.0 if phrase_end else 0.35)
                if rng.random() < p:
                    for h in out:
                        if h.limb == 'R' and abs(h.t - (t0 + s * q)) < _EPS:
                            h.piece, h.tag, h.prio, h.vel = 'hat_open', 'open', _PRIO['open'], _lvl('open', e, soft)
                            h.dur = 0.5
                    nxt = t0 + (s + 2) * q
                    if not any(h.limb == 'R' and h.piece.startswith('hat') and abs(h.t - (s * q + t0)) > _EPS
                               and t0 + s * q < h.t <= nxt + _EPS for h in out):
                        out.append(_h(nxt, 'hat_pedal', _lvl('pedal', e, soft), 'LF', 'pedal'))
    elif tk in ('ride', 'ride_bell', 'bell'):
        steps = [0, 4, 8, 12] if tk == 'bell' else list(range(0, 16, 2))
        for s in steps:
            on = s % 4 == 0
            piece = 'bell' if (tk == 'bell' or (tk == 'ride_bell' and on)) else 'ride'
            lvl = _lvl('bell' if piece == 'bell' else 'ride', e, soft) * (1.0 if on else 0.8)
            out.append(_h(t0 + s * q, piece, lvl, 'R', 'time', 0.5))
    elif tk == 'floor':
        for s in range(0, 16, 2):
            out.append(_h(t0 + s * q, 'floor', _lvl('floor', e, soft) * (1.0 if s % 4 == 0 else 0.78), 'R', 'time'))
    elif tk == 'crash':
        for s in (0, 4, 8, 12):
            out.append(_h(t0 + s * q, 'crash', _lvl('crash_time', e, soft) * (1.0 if s in (0, 8) else 0.9), 'R',
                          'time', 1.0))
    elif tk == 'pedal':
        for s in (0, 4, 8, 12):
            out.append(_h(t0 + s * q, 'hat_pedal', _lvl('pedal', e, soft) * (1.0 if s in (4, 12) else 0.8), 'LF',
                          'pedal'))
    # the hat foot on 2 and 4 when the hand is off the hat
    if tk in ('ride', 'ride_bell', 'bell', 'floor', 'crash'):
        for s in (4, 12):
            out.append(_h(t0 + s * q, 'hat_pedal', _lvl('pedal', e, soft), 'LF', 'pedal'))
    if mode == 'time':                             # the time hand alone: an intro, a breakdown
        return out
    # --- backbeat
    backs = (8,) if mode == 'half' else tuple(st['snare'])
    accent = st.get('accent')
    snare_piece = 'side' if sp['side'] else ('rimshot' if sp['rimshot'] else 'snare')
    if e >= 0.2:
        for s in backs:
            f = 1.0 if accent is None or s in accent else 0.62
            lvl = _lvl('side' if snare_piece == 'side' else 'backbeat', e, soft) * f
            out.append(_h(t0 + s * q, snare_piece, lvl, 'L', 'backbeat' if f >= 1.0 else 'time'))
            if st.get('clap') and kit.has('clap') and snare_piece != 'side' and e >= 0.6:
                out.append(_h(t0 + s * q, 'clap', _lvl('clap', e, soft) * f, 'X', 'layer'))
    # --- kick
    cell = sp['kick_b'] if (bar % 4 == 3 and sp['bars'] >= 4) or (bar % 2 == 1 and sp['bars'] < 4) else sp['kick_a']
    if mode == 'four' or (st.get('four') and mode != 'half'):
        cell = 'x...x...x...x...'
    elif mode == 'half' and sp['kick_a'] not in _KICK_HALF and not st.get('four'):
        cell = sp['kick_half']
    if sparse:
        cell = 'x.......x.......' if e >= 0.2 else 'x...............'
    bass = sp.get('lock', {}).get(bar) if not (mode == 'four' or st.get('four')) else None
    trade = _trade_steps(st, mode)
    for s in (_locked_kicks(_steps(cell), bass, sp.get('lock_mode', 'with'), trade) if bass else _steps(cell)):
        if s in trade and not (mode == 'four' or st.get('four')):
            continue                               # kick and snare trade places: no kick under the backbeat
        f = 1.05 if s == 0 else 1.0 if s % 4 == 0 else 0.9
        out.append(_h(t0 + s * q, 'kick', _lvl('kick', e, soft) * f, 'RF', 'kick', prio=8 if s == 0 else None))
    # --- ghost notes (the left hand between the backbeats; not on a side stick)
    if not sp['side'] and not sparse:
        for s in sp['ghosts_b' if bar % 2 == 1 else 'ghosts_a']:
            if any(abs(s - b) < 1 for b in backs):
                continue
            out.append(_h(t0 + s * q, 'snare', rng.uniform(*_LEVELS['ghost']) * (0.9 + 0.2 * e), 'L', 'ghost'))
    return out


def _bossa_bar(t0: float, sp: dict, ctx: _Ctx, bar: int, e: float) -> list[Hit]:
    """Bossa (straight): cross-stick 2-bar clave (1, &2, 4 | &1, 3), hat (or ride) 8ths, kick 1 &2 3 &4, hat foot 2
    and 4 - the positions of bandlib.jazz.bossa_groove, keyed for any kit."""
    soft, kit = ctx.soft, ctx.kit
    out: list[Hit] = []
    tk = sp['time']
    brush = kit.brush is not None
    for k in range(8):
        t = t0 + k * 0.5
        if brush:
            out.append(_h(t, 'snare', (44 if k % 2 == 0 else 34) * (0.9 + 0.3 * e), 'R', 'time'))
        else:
            piece = 'ride' if tk in ('ride', 'ride_bell') else 'hat'
            out.append(_h(t, piece, _lvl('ride' if piece == 'ride' else 'hat', e, soft) * (1.0 if k % 2 == 0
                                                                                           else 0.72), 'R', 'time'))
    for pos, lv in ((0.0, 1.0), (1.5, 0.8), (2.0, 0.92), (3.5, 0.8)):
        out.append(_h(t0 + pos, 'kick', _lvl('kick', e, soft) * lv * 0.85, 'RF', 'kick'))
    for pos in (1.0, 3.0):
        out.append(_h(t0 + pos, 'hat_pedal', _lvl('pedal', e, soft), 'LF', 'pedal'))
    if not brush:
        for pos in ((0.0, 1.5, 3.0) if bar % 2 == 0 else (0.5, 2.0)):
            piece = 'side' if ctx.kit.has('side') else 'snare'
            out.append(_h(t0 + pos, piece, _lvl('side', e, soft) * (1.0 if pos in (0.0, 2.0) else 0.9), 'L',
                          'backbeat'))
    return out


def _train_bar(t0: float, sp: dict, ctx: _Ctx, bar: int, e: float) -> list[Hit]:
    """The train beat: snare 16ths with both hands (R on the 8ths, L on the e / a), accents on 2 and 4 (the & a
    little), the rest ghosted; kick on 1 and 3 (busier cells in the chorus), hat foot on 2 and 4."""
    soft = ctx.soft
    out: list[Hit] = []
    for s in range(16):
        if s in (4, 12):
            v, tag = _lvl('backbeat', e, soft), 'backbeat'
        elif s % 2 == 0:
            v, tag = _lvl('backbeat', e, soft) * (0.52 if s % 4 == 2 else 0.42), 'time'
        else:
            v, tag = _lvl('backbeat', e, soft) * 0.3, 'time'
        out.append(_h(t0 + s * 0.25, 'snare', v, 'R' if s % 2 == 0 else 'L', tag))
    for s in _steps(sp['kick_b'] if bar % 4 == 3 else sp['kick_a']):
        if s not in (4, 12):
            out.append(_h(t0 + s * 0.25, 'kick', _lvl('kick', e, soft) * (1.05 if s == 0 else 0.92), 'RF', 'kick'))
    for s in (4, 12):
        out.append(_h(t0 + s * 0.25, 'hat_pedal', _lvl('pedal', e, soft), 'LF', 'pedal'))
    return out


def _jazz_section(a: float, bars: int, sp: dict, ctx: _Ctx, seed: int) -> list[Hit]:
    """Jazz time (straight 8ths - swing it with swing=): brushes on a brush kit (patterns.brushes: the stir, taps on
    2 and 4, feathered kick, hat foot; the ride for the hottest part), else the ride (patterns.ride_pattern) with the
    hat foot on 2 and 4, a feathered kick and a soft comping snare. Soft: the drums sit behind the piano."""
    kit, e, rng = ctx.kit, sp['e'], ctx.rng
    out: list[Hit] = []
    bpb = sp['bpb']
    L = bars * bpb
    if kit.brush is not None:
        bstyle = 'ballad' if e < 0.4 else 'medium'
        sweep = sp.get('sweep')
        if sweep is None and kit.name == 'swirly':
            from .jazz import swirly_sweep                 # a Swirly stir about every second
            sweep = swirly_sweep(ctx.bpm, bpb)
        c = _brushes(bars, style=bstyle, kit=kit.brush, ride=e >= 0.8, fills=False, seed=seed,
                     sweep=sweep, vel=0.9 + 0.3 * e, beats_per_bar=bpb)
        fs, ft = _STIR.get(kit.name, (1.0, 1.0))      # a Swirly stir is ~19 dB under a tap: lift it, soften taps
        stirs = {kit.brush.get(r) for r in ('sweep', 'sweep_fast')} - {None}
        taps = {kit.brush.get(r) for r in ('tap', 'slap', 'dig')} - {None}
        c = [n._replace(vel=_vel(n.vel * (fs if n.pitch in stirs else ft if n.pitch in taps else 1.0))) for n in c]
        inv = {}
        for role, k in kit.brush.items():
            inv.setdefault(k if isinstance(k, int) else k[0] if isinstance(k, (list, tuple)) else k, role)
        for n in c:
            role = inv.get(n.pitch, 'tap')
            limb = {'sweep': 'L', 'sweep_fast': 'L', 'kick': 'RF', 'hat_foot': 'LF', 'tap': 'R', 'slap': 'R',
                    'ride': 'R'}.get(role, 'R')
            tag = {'kick': 'kick', 'hat_foot': 'pedal', 'sweep': 'swell'}.get(role, 'time')
            out.append(Hit(a + n.start, f'#{n.pitch}', n.vel, limb, tag, 5, n.dur))
        return out
    pattern = 'two' if e < 0.35 else 'spang'
    rk = kit.key('ride') or kit.key('hat')
    # HUMAN_FEEDBACK (lanterns-on-carmine, "Drums etwas zu laut"): the ride stays soft even in the hot chorus (45-60)
    c = _ride_pattern(bars, pattern, kit={'ride': rk}, vel=44 + 12 * e, seed=seed, beats_per_bar=bpb)
    for n in c:
        out.append(Hit(a + n.start, 'ride', n.vel, 'R', 'time', 5, n.dur))
    nb = int(round(bpb))
    backs = (1, 2) if nb == 3 else tuple(x for x in range(nb) if x % 2 == 1)
    for b in range(bars):
        t0 = a + bpb * b
        for s in backs:
            out.append(_h(t0 + s, 'hat_pedal', 44 + 12 * e, 'LF', 'pedal'))
        for s in range(nb):                     # the feathered kick: felt, hardly heard
            out.append(_h(t0 + s, 'kick', 26 + 8 * e + rng.uniform(-3, 3), 'RF', 'kick'))
        # comping: one or two soft snare comments on off-beats, a kick 'bomb' now and then
        spots = [x + 0.5 for x in range(nb)] + [float(nb // 2)]
        for s in rng.sample(spots, 1 + (rng.random() < 0.3 + 0.4 * ctx.density)):
            out.append(_h(t0 + s, 'snare', 38 + 16 * e + rng.uniform(-4, 4), 'L', 'backbeat'))
        if rng.random() < 0.15 + 0.2 * ctx.density:
            out.append(_h(t0 + bpb - 0.5, 'kick', 45 + 12 * e, 'RF', 'kick'))
    return [h for h in out if h.t < a + L - _EPS]


# ------------------------------------------------------------------------------------------------ fills (hits)

def _fill_level(e: float, soft: float) -> tuple[float, float]:
    top = _lvl('fill', e, soft)
    return top * 0.66, top


def _sticking(hits: list[Hit], lead: str = 'R') -> None:
    """Alternate hands (R L R L ...) through hand strokes in time order; strokes together get different hands."""
    hand = lead
    for h in sorted(hits, key=lambda h: h.t):
        if h.limb in ('RF', 'LF', 'X') or h.tag == 'grace':
            continue
        h.limb = hand
        hand = 'L' if hand == 'R' else 'R'


def _kick_pulse(a: float, L: float, e: float, soft: float, every: float = 1.0) -> list[Hit]:
    out = []
    k = 0
    while a + k * every < a + L - _EPS:
        out.append(_h(a + k * every, 'kick', _lvl('kick', e, soft) * 0.85, 'RF', 'kick'))
        k += 1
    return out


def _f_snare(a, L, ctx, e, step=None):
    v0, v1 = _fill_level(e, ctx.soft)
    step = step or (0.25 if ctx.gap_ok(0.5, 'R') else 0.5)
    n = max(1, int(round(L / step)))
    out = []
    for k in range(n):
        x = k / max(1, n - 1)
        acc = 1.08 if (k * step) % 1.0 < _EPS else 1.0
        out.append(_h(a + k * step, 'snare', (v0 + (v1 - v0) * x ** 1.3) * acc, 'R', 'fill'))
    _sticking(out)
    if L >= 2 and e >= 0.55:
        out += _kick_pulse(a, L, e, ctx.soft)
    return out


def _f_toms(a, L, ctx, e):
    """The tom run: patterns.tom_fill's grid and crescendo across the kit's toms (high -> low); a fill of 2 beats or
    more opens on the snare."""
    kit = ctx.kit
    v0, v1 = _fill_level(e, ctx.soft)
    step = 0.25 if ctx.gap_ok(0.5, 'R') else 0.5
    out = []
    snare_len = 1.0 if L >= 2 else 0.5 if L >= 1 else 0.0
    if not kit.toms:
        return _f_snare(a, L, ctx, e)
    n0 = int(round(snare_len / step))
    for k in range(n0):
        out.append(_h(a + k * step, 'snare', v0 + (v1 - v0) * 0.4 * k / max(1, n0), 'R', 'fill'))
    rest = L - snare_len
    if rest > _EPS:
        toms = [kit.key(f'tom{i + 1}') for i in range(len(kit.toms))]
        c = _tom_fill(rest, step, toms=tuple(toms), vel=(v0 + (v1 - v0) * 0.45, v1))
        pieces = {k: f'tom{i + 1}' for i, k in enumerate(kit.toms)}
        for nt in c:
            out.append(_h(a + snare_len + nt.start, pieces.get(nt.pitch, 'floor'), nt.vel, 'R', 'fill'))
    _sticking(out)
    for h in out:                                     # the downbeats of the run lean in
        if abs((h.t - a) % 1.0) < _EPS:
            h.vel *= 1.06
    if e >= 0.6:
        out += _kick_pulse(a + snare_len, rest, e, ctx.soft)
    return out


def _f_triplets(a, L, ctx, e):
    kit = ctx.kit
    v0, v1 = _fill_level(e, ctx.soft)
    per = 6 if ctx.bpm < 80 and L <= 2 else 3               # 16th-note triplets at ballad tempos
    n = max(3, int(round(L * per)))
    drums = ['snare'] + [f'tom{i + 1}' for i in range(len(kit.toms))]
    out = []
    for k in range(n):
        x = k / max(1, n - 1)
        piece = drums[min(len(drums) - 1, k * len(drums) // n)]
        acc = 1.1 if k % 3 == 0 else 0.92
        out.append(_h(a + k / per, piece, (v0 + (v1 - v0) * x) * acc, 'R', 'fill'))
    _sticking(out)
    if e >= 0.6:
        out += _kick_pulse(a, L, e, ctx.soft)
    return out


def _f_flams(a, L, ctx, e):
    """Flam accents on the 8ths down the kit: the main stroke with a soft grace 15-25 ms before it by the other hand
    (right and left flams alternate)."""
    kit = ctx.kit
    v0, v1 = _fill_level(e, ctx.soft)
    n = max(1, int(round(L / 0.5)))
    drums = ['snare'] + [f'tom{i + 1}' for i in range(len(kit.toms))]
    out = []
    for k in range(n):
        x = k / max(1, n - 1)
        piece = drums[min(len(drums) - 1, k * len(drums) // n)]
        main_limb = 'R' if k % 2 == 0 else 'L'
        m = _h(a + k * 0.5, piece, v0 + (v1 - v0) * x, main_limb, 'fill')
        g = _h(m.t - _ms(ctx.rng.uniform(15, 25), ctx.bpm), piece, ctx.rng.uniform(24, 36) * ctx.soft,
               'L' if main_limb == 'R' else 'R', 'grace', main=m)
        out += [g, m]
    if e >= 0.55:
        out += _kick_pulse(a, L, e, ctx.soft)
    return out


def _f_linear(a, L, ctx, e):
    """A linear fill: 16ths where no two limbs ever strike together - R L K repeated (a 3-against-4 ripple), the
    hands walking down the toms."""
    kit = ctx.kit
    v0, v1 = _fill_level(e, ctx.soft)
    n = max(3, int(round(L / 0.25)))
    hands = [k for k in range(n) if k % 3 != 2]
    out = []
    for k in range(n):
        x = k / max(1, n - 1)
        t = a + k * 0.25
        if k % 3 == 2:
            out.append(_h(t, 'kick', _lvl('kick', e, ctx.soft) * (0.85 + 0.15 * x), 'RF', 'fill'))
            continue
        piece = kit.tom(hands.index(k), len(hands)) if kit.toms and k >= 3 else 'snare'
        out.append(_h(t, piece, (v0 + (v1 - v0) * x) * (1.1 if k % 3 == 0 else 0.85), 'R' if k % 3 == 0 else 'L',
                      'fill'))
    return out


def _f_pickup(a, L, ctx, e):
    """A pickup into the downbeat: a flam on the & of the last beat, two 16ths (& a), or the snare on the & and
    snare + floor tom together on the a (one stroke per hand)."""
    v0, v1 = _fill_level(e, ctx.soft)
    end = a + L
    kind = ctx.rng.choice(('flam', 'two', 'double') if L >= 0.5 - _EPS else ('flam',))
    if kind == 'flam':
        m = _h(end - 0.5 if L >= 0.5 - _EPS else a, 'snare', v1 * 0.95, 'R', 'fill')
        return [_h(m.t - _ms(ctx.rng.uniform(15, 25), ctx.bpm), 'snare', 36 * ctx.soft, 'L', 'grace', main=m), m]
    if kind == 'two':
        return [_h(end - 0.5, 'snare', v0 + 0.5 * (v1 - v0), 'R', 'fill'), _h(end - 0.25, 'snare', v1, 'L', 'fill')]
    out = [_h(end - 0.5, 'snare', v0 + 0.6 * (v1 - v0), 'R', 'fill'), _h(end - 0.25, 'snare', v1 * 0.95, 'L', 'fill')]
    if ctx.kit.toms:
        out.append(_h(end - 0.25, 'floor', v1 * 0.95, 'R', 'fill'))
    return out


def _f_roll(a, L, ctx, e, build=False):
    """A snare roll crescendo (patterns.snare_roll): 32nds (16ths above 150 BPM) alternating hands; build=True
    accelerates 8ths -> 16ths -> 32nds, the kick on the beats."""
    v0, v1 = _fill_level(e, ctx.soft)
    step = '1/16' if (ctx.bpm > 150 or build) else '1/32'
    c = _snare_roll(L, step=step, vel=(max(30.0, v0 * 0.55), v1), pitch=38, build=build)
    out = [_h(a + n.start, 'snare', n.vel, 'R', 'build' if build else 'roll') for n in c]
    _sticking(out)
    out += _kick_pulse(a, L, e, ctx.soft)
    return out


def _f_brush(kind, a, L, ctx, e):
    """Jazz brush fills (patterns.brush_fill) on a brush kit; on sticks a soft snare triplet / 8th figure."""
    kit = ctx.kit
    if kit.brush is None:
        if kind == 'triplets':
            return _f_triplets(a, L, ctx, e * 0.6)
        return _f_snare(a, L, ctx, e * 0.6, step=0.5 if kind == 'eighths' else None)
    c = _brush_fill(kind if kind in ('triplets', 'eighths', 'slap', 'toms') else 'triplets', L, kit=kit.brush,
                    vel=(40 + 10 * e, 70 + 20 * e))
    out = []
    for n in c:
        limb = 'RF' if n.pitch == kit.brush.get('kick') else 'R'
        out.append(Hit(a + n.start, f'#{n.pitch}', n.vel, limb, 'kick' if limb == 'RF' else 'fill', 7, n.dur))
    _sticking(out)
    return out


_FILL_FN = {'snare': _f_snare, 'toms': _f_toms, 'triplets': _f_triplets, 'flams': _f_flams, 'linear': _f_linear,
            'pickup': _f_pickup, 'roll': _f_roll, 'build': lambda a, L, ctx, e: _f_roll(a, L, ctx, e, build=True)}


def _fill_hits(kind: str, a: float, L: float, ctx: _Ctx, e: float) -> list[Hit]:
    if kind in ('eighths', 'slap') or (ctx.st.get('special') == 'jazz' and kind in ('triplets', 'toms')):
        return _f_brush(kind, a, L, ctx, e)
    return _FILL_FN[kind](a, L, ctx, e)


def _crash_hits(t: float, ctx: _Ctx, e: float, piece: str = 'crash', with_kick: bool = True) -> list[Hit]:
    out = [_h(t, piece, _lvl('crash', e, ctx.soft), 'R', 'crash', 2.0)]
    if with_kick:
        out.append(_h(t, 'kick', _lvl('kick', e, ctx.soft) * 1.05, 'RF', 'kick', prio=9))
    return out


# ------------------------------------------------------------------------------------------------ limbs, touch, feel

def _resolve(hits: list[Hit], bpm: float) -> tuple[list[Hit], int]:
    """Make it playable: one limb never strikes twice closer than it can (groove 70 ms, rolls / fills 40 ms, kick
    80 ms, hat foot 100 ms) - the stroke with the lower priority goes; the hat foot never closes a hat that is being
    opened; a crash always has the kick. Returns (hits, dropped)."""
    hits = [h for h in hits if h.vel >= 1.0]
    # a crash (not crash-riding time) needs the kick with it
    kicks = [h for h in hits if h.limb == 'RF']
    for c in [h for h in hits if h.tag == 'crash']:
        if not any(abs(k.t - c.t) < _ms(_TOGETHER_MS, bpm) for k in kicks):
            k = _h(c.t, 'kick', max(80.0, c.vel * 0.9), 'RF', 'kick', prio=9)
            hits.append(k)
            kicks.append(k)
    # an open hat and the foot closing it at the same moment cannot both happen
    opens = [h.t for h in hits if h.tag == 'open']
    hits = [h for h in hits if not (h.piece == 'hat_pedal' and any(abs(h.t - o) < _ms(_TOGETHER_MS, bpm)
                                                                    for o in opens))]
    keep: list[Hit] = []
    dropped = 0
    by_limb: dict[str, list[Hit]] = {}
    for h in hits:
        by_limb.setdefault(h.limb, []).append(h)
    graces = []
    for limb, hs in by_limb.items():
        if limb == 'X':
            keep.extend(hs)
            continue
        hs.sort(key=lambda h: (h.t, -h.prio))
        kept: list[Hit] = []
        for h in hs:
            if h.tag == 'grace':
                graces.append(h)
                continue
            if h.tag == 'bounce':          # the stick's own rebounds inside a buzz stroke: no new stroke of the hand
                keep.append(h)
                continue
            if kept:
                p = kept[-1]
                gap = _beats_ms(h.t - p.t, bpm)
                need = _ROLL_GAP_MS if (h.tag in _ROLL_TAGS and p.tag in _ROLL_TAGS) else _GAP_MS[limb]
                if gap < need - _EPS:
                    dropped += 1
                    if h.prio > p.prio:
                        kept[-1] = h
                    continue
            kept.append(h)
        keep.extend(kept)
    alive = {id(h) for h in keep}
    for g in graces:
        if g.main is not None and id(g.main) in alive:
            hand = [h for h in keep if h.limb == g.limb and abs(_beats_ms(h.t - g.t, bpm)) < _ROLL_GAP_MS]
            if not hand:
                keep.append(g)
                continue
        dropped += 1
    keep.sort(key=lambda h: (h.t, h.limb))
    return keep, dropped


def _touch(hits: list[Hit], secs: list[dict], rng: random.Random, machine: bool) -> None:
    """The drummer's touch on the levels written per stroke role: a 4-bar phrase arc (a little lift into the 4th
    bar and the fill), the first backbeat of a section leaning in, and every stroke a little different (ghosts
    more; a machine hardly). Ghosts stay 15-35."""
    arc = (0.97, 0.985, 1.0, 1.025)
    for h in hits:
        sp = h.bar
        if isinstance(sp, tuple):
            si, b = sp
            f = arc[b % 4] if h.tag in ('time', 'backbeat', 'kick', 'open') else 1.0
            if b == 0 and h.tag == 'backbeat' and h.t - secs[si]['a'] < 2.0 + _EPS:
                f *= 1.04
        else:
            f = 1.0
        j = 0.02 if machine else 0.13 if h.tag == 'ghost' else 0.05
        v = h.vel * f * (1.0 + _tri(rng) * j)
        if h.tag == 'ghost':
            v = min(35.0, max(15.0, v))
        h.vel = max(1.0, min(127.0, v))


def _swing_t(t: float, swing: float, sgrid: float) -> float:
    """Swing one time: inside each swing cell (two `sgrid` steps) the first half stretches to `swing` and the second
    half shrinks - so the off-beat step lands on `swing` AND the subdivisions under it swing with it (16ths inside
    swung 8ths: 0, .31, .62, .81 at 0.62 - never a 16th squeezed against the late off-beat). Only times on the binary
    grid (down to an eighth of the cell) move; triplets and other free positions stay (a triplet fill is swing
    already)."""
    cell = 2.0 * sgrid
    c = math.floor(t / cell + 1e-9)
    x = (t - c * cell) / cell
    if abs(x * 8.0 - round(x * 8.0)) > 1e-4:
        return t
    x = x * (swing / 0.5) if x <= 0.5 else swing + (x - 0.5) * (1.0 - swing) / 0.5
    return (c + x) * cell


def _swing(hits: list[Hit], swing: float, sgrid: float) -> None:
    """Swing every stroke on the binary grid (_swing_t); a flam grace moves with its main stroke."""
    delta = {}
    for h in hits:
        if h.tag != 'grace':
            t = _swing_t(h.t, swing, sgrid)
            delta[id(h)] = t - h.t
            h.t = t
    for h in hits:
        if h.tag == 'grace' and h.main is not None:
            h.t += delta.get(id(h.main), 0.0)


def _feel(hits: list[Hit], bpm: float, feel: dict, timing_ms: float, rng: random.Random, drift: bool) -> None:
    """Human timing, per limb: the style's push / pull (feel, ms), a slow wander of each limb (drift, +-3 ms), a
    triangular spread of timing_ms (ghosts looser, backbeat and kick tighter), crash a hair after its kick (the
    limbs are not one machine); flam graces keep their distance to the main stroke. (Swing is on the grid already:
    _swing.) Every offset stays within +-(|feel| + 20) ms."""
    wander = {l: 0.0 for l in LIMBS}
    last_beat = {l: None for l in LIMBS}
    spread = {'ghost': 1.3, 'time': 0.8, 'backbeat': 0.65, 'kick': 0.7, 'crash': 0.8, 'pedal': 1.0, 'open': 0.8}
    for h in sorted(hits, key=lambda h: h.t):
        if h.tag == 'grace' or h.limb == 'X':
            continue
        beat = int(math.floor(h.t + _EPS))
        if drift and last_beat[h.limb] != beat:
            wander[h.limb] = max(-3.0, min(3.0, 0.8 * wander[h.limb] + rng.gauss(0.0, 0.9)))
            last_beat[h.limb] = beat
        off = feel.get(h.limb, 0.0) + (wander[h.limb] if drift else 0.0) + _tri(rng) * timing_ms * spread.get(h.tag,
                                                                                                              1.0)
        if h.tag == 'crash':
            off += rng.uniform(1.5, 5.0)
        lim = abs(feel.get(h.limb, 0.0)) + 20.0
        h.off = max(-lim, min(lim, off))
    left = {round(g.t, 3): g.off for g in hits if g.limb == 'L'}
    for h in hits:
        if h.tag == 'grace' and h.main is not None:
            h.off = h.main.off
        elif h.limb == 'X':
            h.off = left.get(round(h.t, 3), 0.0)          # a layer (the clap) moves with the stroke it doubles


_HAT_OPEN = {'hat': 0.0, 'hat_half': 0.55, 'hat_open': 1.0}
"""The default openness of the hat pieces (Hit.open overrides it): 0 closed .. 1 open."""


def _openness(h: Hit) -> float | None:
    """How open a hi-hat stroke is (0..1), None when it is no hat stroke."""
    if h.piece not in _HAT_OPEN:
        return None
    return max(0.0, min(1.0, float(h.open))) if h.open is not None else _HAT_OPEN[h.piece]


def _hat_piece(h: Hit, kit: Kit) -> str:
    """The piece a hat stroke sounds on: on a kit with a live hat (Kit.live_hat: the variable hat opens by the
    'dynamics' param, hat_lane()) every stroke with some openness plays the variable hat; else the openness picks
    closed / half-open / open."""
    o = _openness(h)
    if o is None:
        return h.piece
    if kit.live_hat:
        return 'hat' if o < 0.1 and h.piece == 'hat' else 'hat_open'
    if h.open is None:
        return h.piece
    if o < 0.2:
        return 'hat'
    if o < 0.75 and kit.has('hat_half'):
        return 'hat_half'
    return 'hat_open' if o >= 0.45 else 'hat'


_LANE_LEAD_MS = 6.0
"""A hat-openness step lands this long before its stroke (the zone choice reads 'dynamics' at the note-on)."""


def hat_lane(hits, kit, bpm: float, *, at: float = 0.0) -> list:
    """The hi-hat openness of a part as an automation lane for a kit with a live hat (Kit.live_hat: Big Rusty /
    Unruly's variable hat 46 opens by the sampler's 'dynamics' param, the SFZ hi-hat CC4 imported live): a step to
    each stroke's openness 6 ms before it, only where it changes ([] when every hat stroke is fully open - the
    default - or the kit has no live hat). hits: Hits with .open (0 closed .. 1 open) or the hat pieces' defaults
    ('hat_half' 0.55, 'hat_open' 1). Performance.play() writes it as 'instrument.dynamics'."""
    K = Kit.of(kit)
    if not K.live_hat:
        return []
    b = _bpm(bpm)
    a = _num(at, 'hat_lane at (beats)')
    pts: list = []
    cur = 1.0
    last = -math.inf
    for h in sorted(hits, key=lambda h: h.t + _ms(h.off, b)):
        o = _openness(h)
        if o is None or _hat_piece(h, K) != 'hat_open':
            continue
        if abs(o - cur) < 0.01:
            continue
        t = max(last + 1e-3, a + h.t + _ms(h.off - _LANE_LEAD_MS, b), 0.0)
        pts.append((round(t, 5), round(o, 3), 'step'))
        cur, last = o, t
    if pts and pts[0][0] > 0.0:
        pts.insert(0, (0.0, 1.0, 'step'))
    if cur != 1.0:                    # back to the default after the last stroke: the next part starts open
        ends = [a + h.t + _ms(h.off, b) for h in hits if _openness(h) is not None]
        pts.append((round(max(last + 0.05, max(ends) + 0.05), 5), 1.0, 'step'))
    return pts


def _to_clip(hits: list[Hit], kit: Kit, bpm: float, length: float, start_min: float = 0.0) -> Clip:
    notes = []
    for h in hits:
        if h.piece.startswith('#'):
            key = int(h.piece[1:])
        else:
            key = kit.key(_hat_piece(h, kit), limb=h.limb)
        if key is None:
            continue
        t = max(start_min, h.t + _ms(h.off, bpm))
        if t >= length - _EPS:
            continue
        notes.append(Note(t, max(0.05, h.dur), int(key), _vel(h.vel)))
    notes.sort(key=lambda n: (n.start, n.pitch))
    return Clip._raw(notes, length)


# ------------------------------------------------------------------------------------------------ budget, memory

class Memory:
    """What one drummer already played in a song, for arrange() calls section by section: pass the same Memory
    (memory=, with at= the call's position in beats) and the fill budget counts song-wide (a flashy tom run at the
    end of one call keeps the next call's fills plainer). played(at, kind) books a fill placed by hand.
    .fills: [(beat, kind, flashy)], .crashes: [beat]."""

    def __init__(self):
        self.fills: list = []
        self.crashes: list = []
        self.clock = 0.0

    def played(self, at, kind: str, length: float = 2.0) -> 'Memory':
        if kind not in FILL_KINDS:
            raise ComposeError(f"Memory.played: {kind!r} is not a fill kind ({', '.join(FILL_KINDS)})")
        t = _pos(at)
        self.fills.append((t, kind, kind in FLASHY and length >= 2.0 - _EPS))
        self.clock = max(self.clock, t)
        return self

    def __repr__(self) -> str:
        return (f"Memory({len(self.fills)} fills: {', '.join(f'{k}@{t:g}' for t, k, _ in self.fills)}; "
                f"{len(self.crashes)} crashes; clock {self.clock:g})")


class Performance:
    """What arrange() played: clip (the drums from `start`, keyed for the kit), start (beat), hits (every stroke with
    its limb, tag and timing offset), moves (a log: (start, end, kind, name) with kind 'groove' | 'fill' | 'crash' |
    'build' | 'stop' | 'dropout' | 'ending' and 'dropped' for a fill the budget refused - its substitute is logged as
    played), plan (per section: role, energy, timekeeper, mode, kick cells, ghosts, rimshot / side stick), budget
    (fill_every / flashy_every / same_every / crash_every, the fills and flashy fills kept, the dropped ones), kit.
    summary() counts the moves; play(track) places the clip. warnings: pieces the kit lacks (played on a fallback piece
    or left out); play(track) adds them to the song's warnings, plus the pieces the track's own kit lacks when the part
    was arranged for another kit (their notes would be silent: arrange with kit=<track> plays the fallbacks)."""

    def __init__(self, clip, start, hits, moves, plan, budget, kit, bpm):
        self.clip, self.start, self.hits, self.moves, self.plan = clip, start, hits, moves, plan
        self.budget, self.kit, self.bpm = budget, kit, bpm
        self.warnings: list[str] = []
        self.lanes: dict = {}
        hl = hat_lane(hits, kit, bpm) if kit is not None else []
        if hl:
            self.lanes['instrument.dynamics'] = hl

    def __repr__(self) -> str:
        return (f"Performance({len(self.clip)} strokes from beat {self.start:g}, kit {self.kit.name}, "
                f"{self.summary()})")

    def summary(self) -> dict:
        out: dict = {}
        for _, _, kind, name in self.moves:
            if kind == 'groove':
                continue
            out[f"{kind}:{name}"] = out.get(f"{kind}:{name}", 0) + 1
        return dict(sorted(out.items()))

    @property
    def fills(self) -> list:
        return [(a, b, n) for a, b, k, n in self.moves if k in ('fill', 'build')]

    @property
    def crashes(self) -> list:
        return [a for a, _, k, _ in self.moves if k == 'crash']

    def play(self, track, humanize: bool = False):
        """track.play(clip, start). The drummer played the timing itself: humanize=False switches the track's own
        humanize off (track.humanize(0, 0)) so it is not jittered twice; True keeps it."""
        if not humanize:
            track.humanize(0, 0)
        song = getattr(track, '_song', None)
        if song is not None and hasattr(song, 'advice'):
            tid = getattr(track, 'id', '?')
            for w in self.warnings + self._track_kit_warnings(track):
                song.advice.append(f"drummer on {tid!r}: {w}")
        out = track.play(self.clip, self.start)
        for target, pts in self.lanes.items():
            track.automate(target, [(self.start + p[0],) + tuple(p[1:]) for p in pts])
        return out

    def _track_kit_warnings(self, track) -> list[str]:
        """The part was arranged for another kit than the track plays (kit=None: General MIDI): pieces the track's kit
        lacks, with the fallback kit=<track> would play."""
        ins = getattr(track, 'instrument', None)
        if ins is None or getattr(ins, 'type', None) not in ('sampler', 'drums'):
            return []
        try:
            tk = Kit.of(track)
        except ComposeError:
            return []
        if (tk.name, tk.pieces, tk.toms) == (self.kit.name, self.kit.pieces, self.kit.toms):
            return []
        have = _sounding_keys(ins)
        if not have:
            return []
        out = []
        counts: dict[str, int] = {}
        for n in self.clip:        # what is played (a song may have moved some strokes to another track)
            if n.pitch not in have:
                piece = _piece_of(self.kit, n.pitch)
                counts[piece] = counts.get(piece, 0) + 1
        for piece, n in sorted(counts.items(), key=lambda x: -x[1]):
            if piece.startswith('key '):
                out.append(f"{n} stroke{'s land' if n != 1 else ' lands'} on {piece}, which the track's kit has no "
                           f"sample for (silent)")
                continue
            alt = tk.key(piece)
            name = _piece_of(tk, alt) if alt is not None else None
            out.append(f"{n} {piece} stroke{'s land' if n != 1 else ' lands'} on key {self.kit.key(piece)}, which the "
                       f"track's kit has no sample for (silent); the part was arranged for kit {self.kit.name!r} - "
                       + (f"arrange with kit=<the track> to play them on {name} ({alt}) instead, or " if alt is not None
                          else "") + f"map a {piece} sample into the kit (inst.kit(..., map={{...}}))")
        return out


def _fill_budget(memory: Memory | None, bpb: float, fill_every: float, flashy_every: float,
                 same_every: float) -> Budget:
    """The drummer's fill budget on the shared ledger (agentsound.budget.Budget, as the pianist's / guitarist's /
    hornist's / soloist's): class 'fill' (any fill, fill_every bars apart; 0 = no spacing), class 'flashy' (the showy
    fills, flashy_every bars apart; 0 = none), one flashy kind same_every bars apart; seeded with `memory`'s fills."""
    bud = Budget({'fill': fill_every * bpb, 'flashy': flashy_every * bpb}, same_every=same_every * bpb,
                 same=('flashy',), save_cls=())
    for t, kind, flashy in (memory.fills if memory is not None else []):
        bud.book(t, 'fill')
        if flashy:
            bud.book(t, 'flashy', kind)
    return bud


def _budget(cands: list[dict], bud: Budget, base: float, fill_every: float) -> tuple[list[dict], list]:
    """Keep fill candidates: structural ones (into a section) always, the others at least fill_every bars from any
    kept fill (and from memory's: the ledger `bud`). Returns (kept, refused)."""
    kept, refused = [], []
    for c in sorted(cands, key=lambda c: (-c['score'], c['t'])):
        T = base + c['t']
        if c['structural'] or fill_every <= 0 or bud.allows(T, 'fill'):
            kept.append(c)
            bud.book(T, 'fill')
        else:
            refused.append(c)
    kept.sort(key=lambda c: c['t'])
    return kept, refused


# ------------------------------------------------------------------------------------------------ arrange

def _role_of(name: str) -> str:
    n = name.lower().replace('-', '').replace('_', '').replace(' ', '')
    for role, words in _ROLE_WORDS:
        if any(n.startswith(w) or (w in n and w not in ('end', 'tag', 'drop')) for w in words):
            return role
    return 'verse'


_PLAN_KEYS = {'role', 'energy', 'time', 'mode', 'fill', 'fill_len', 'crash', 'ghosts', 'build', 'stop', 'dropout',
              'style', 'side', 'rimshot', 'sweep', 'lock'}


def _lock_steps(lock, a: float, bars: int, bpb: float, backs, sixteenths: bool) -> dict:
    """The bass onsets per bar as 16th steps (not under the backbeat, 16th off-beats only in a 16th feel):
    {bar: [steps]}; bars where the bass rests are missing."""
    out = {}
    for b in range(bars):
        t0 = a + b * bpb
        steps = set()
        for n in lock:
            x = (n.start - t0) / 0.25
            k = round(x)
            if 0 <= k < 16 and abs(x - k) < 0.2 and k not in backs and (sixteenths or k % 2 == 0):
                steps.add(k)
        if steps:
            out[b] = sorted(steps)
    return out


def _locked_kicks(cell_steps, bass_steps, mode: str = 'with', backs=()) -> list[int]:
    """The style's kicks against the bass. 'with': each kick of the cell goes to the nearest bass onset within an 8th
    (kick and bass hit together); a kick with no bass note near drops, beat 1 always stays. 'answer': beat 1 with the
    bass, every other kick that would land on a bass onset moves to the nearest free 16th within an 8th (later
    first) - the kick plays in the bass's gaps (they alternate). Either way the kick keeps the style's density."""
    out, used = [], set()
    bass = set(bass_steps)
    for s in cell_steps:
        if mode == 'answer':
            if s == 0 or s not in bass:
                out.append(s)
                continue
            for d in (1, -1, 2, -2):
                x = s + d
                if 0 < x < 16 and x not in bass and x not in backs and x not in out:
                    out.append(x)
                    break
            continue
        near = sorted((abs(b - s), b) for b in bass if abs(b - s) <= 2 and b not in used)
        if near:
            used.add(near[0][1])
            out.append(near[0][1])
        elif s == 0:
            out.append(0)
    return sorted(set(out))


def _parse_form(form) -> tuple[list[tuple[str, float, float, float]], float, float | None]:
    """-> [(name, start (relative), bars, beats_per_bar)], absolute start, song tempo (or None)."""
    tempo = None
    if hasattr(form, 'sections') and hasattr(form, 'tempo'):
        tempo = form.tempo
        form = form.sections
    if hasattr(form, 'start') and hasattr(form, 'bars') and hasattr(form, 'name'):
        form = [form]
    if not isinstance(form, (list, tuple)) or not form:
        raise ComposeError("drummer.arrange: form must be a Song, a Section, or a list of Sections / (name, bars) "
                           "pairs")
    out = []
    t = 0.0
    start = None
    for x in form:
        if hasattr(x, 'start') and hasattr(x, 'bars') and hasattr(x, 'name'):
            if start is None:
                start = float(x.start)
            if out and abs(x.start - (start + t)) > _EPS:
                raise ComposeError(f"drummer.arrange: section {x.name!r} does not follow the previous one (pass "
                                   f"consecutive sections)")
            out.append((x.name, t, float(x.bars), float(x.beats_per_bar)))
            t += x.length
        elif isinstance(x, (tuple, list)) and len(x) == 2 and isinstance(x[0], str):
            bars = _num(x[1], f"section {x[0]!r} bars", 0.25)
            if start is None:
                start = 0.0
            out.append((x[0], t, bars, 4.0))
            t += bars * 4.0
        else:
            raise ComposeError(f"drummer.arrange: not a section: {x!r} (use Sections or (name, bars) pairs)")
    return out, start or 0.0, tempo


def arrange(form, *, bpm=None, style: str = 'rock', density: float = 0.5, seed=0, kit=None, plan: dict | None = None,
            fill_every: float = 4.0, flashy_every: float = 8.0, same_every: float = 16.0, crash_every: float = 4.0,
            fills: dict | None = None, feel=None, timing_ms: float | None = None, swing: float | None = None,
            ending: str | None = None, human: bool = True, phrase_fills: bool = True, lock=None,
            lock_mode: str = 'with', memory: Memory | None = None, at=None, hands=None) -> Performance:
    """A drummer plays a song form -> Performance (.clip from .start, .hits, .moves, .plan, .budget, .summary(),
    .play(track)).

    form: a Song (all its sections; bpm = its tempo), a Section, a list of consecutive Sections or of (name, bars)
    pairs (from beat 0). Every section gets a ROLE (from its name, or plan=) with an energy: the verse calmer
    (hi-hat, the calm kick cells, ghosts), the pre-chorus rising (open hats, a BUILD into the chorus: 8ths -> 16ths
    -> 32nds on the snare), the chorus bigger (ride or 16ths, busier kick, rimshots, a crash every 8 bars), the
    bridge a variation (a floor-tom groove, half-time, the ride bell), a break a STOP (the band hit, silence, time on
    the hat), the end a big hit and a roll into the final cut-off (ending='hit' | 'roll' | 'groove' | 'choke': the
    hit grabbed a beat later on a kit with choke keys). A section's groove is a main cell with a variation in its 4th
    bar, repeated sections reuse it.
    FILLS lead into every section (into a chorus the longest: a bar at density >= 0.45), and with a chance (density)
    into a new 4- or 8-bar phrase - a BUDGET keeps them spice: at least fill_every bars between phrase fills, the
    FLASHY ones (tom runs, triplets, flams, linear at 2+ beats) flashy_every bars apart and the same flashy kind
    same_every bars apart (a plainer fill takes its place: logged 'dropped'); now and then the bar before a chorus
    DROPS OUT instead (the hat alone, then a pickup). The crash lands with the kick on section downbeats and after
    fills in the big parts (at least crash_every bars apart inside a section).
    Touch: levels per stroke by energy (backbeat 80-122, kick 72-114, hat accents on the beats and lighter & /
    16ths, ghosts 15-35, the hat foot soft), a 4-bar phrase arc, per-stroke variation. Feel (human=True): per-limb push / pull
    (feel= a STYLES preset's name or {'R': ms, 'L': ms, 'RF': ms, 'LF': ms}; 'laid_back', 'push', 'on'), a
    spread of timing_ms, a slow drift per limb (not for the synthpop machine), swing= (0.5..0.75) on the style's
    grid. Two hands and two feet: see the module docstring (check()).

    style: STYLES; density 0..1 (ghosts, open hats, busier kicks, phrase fills); plan={section name: {role, energy,
    time (TIMEKEEPERS), mode ('half', 'four'), fill (a FILL_KINDS kind or False: none into this section), fill_len
    (beats), crash (bool), ghosts (0..1), build (bool), stop (bool: this section ends in a stop), dropout (bool),
    style, side (bool), rimshot (bool), sweep (the jazz brush stir length)}} or a shorthand string (a role, a
    timekeeper, a mode or a style); fills= fill weights; kit: Kit.of(...) (a track, an instrument, a name, a dict);
    memory: a Memory for section-by-section calls (at= the position); phrase_fills=False: fills only into sections;
    lock= the bass part (its Track after the bass is placed, or a Clip from the part's start): the kick locks to the
    bass - each kick of the groove moves onto the bass note nearest it (within an 8th; none near: it drops, beat 1
    stays), so kick and bass hit together at the style's density (plan {'x': {'lock': False}} per section);
    lock_mode='answer': the kick plays in the bass's gaps instead (beat 1 together, then they alternate).
    hands= a Hands / HANDS name: the fills' strokes get the solo layer's hand physics (perform_hits: the weaker
    hand, rebounds, up-strokes, reach; the levels only, the feel keeps the timing). Deterministic by seed."""
    if style not in STYLES:
        raise ComposeError(f"drummer style must be one of {', '.join(STYLES)}, got {style!r}")
    secs_in, abs_start, tempo = _parse_form(form)
    b = _bpm(bpm if bpm is not None else tempo if tempo is not None else None)
    dens = _num(density, 'drummer density', 0, 1)
    fe = _num(fill_every, 'drummer fill_every (bars)', 0)
    xe = _num(flashy_every, 'drummer flashy_every (bars)', 0)
    se = _num(same_every, 'drummer same_every (bars)', 0)
    ce = _num(crash_every, 'drummer crash_every (bars)', 0)
    if ending not in (None, 'hit', 'roll', 'groove', 'choke'):
        raise ComposeError(f"drummer ending must be 'hit', 'roll', 'choke', 'groove' or None, got {ending!r}")
    if memory is not None and not isinstance(memory, Memory):
        raise ComposeError(f"drummer memory must be a drummer.Memory(), got {memory!r}")
    rng = random.Random(seed_int(seed))
    K = Kit.of(kit)
    if hands is not None:
        hands = _hands(hands)
    ST = STYLES[style]
    plan = dict(plan or {})
    names = [s[0] for s in secs_in]
    for k in plan:
        if k not in names:
            raise ComposeError(f"drummer plan: no section {k!r} in the form ({', '.join(names)})")
    placed = any(hasattr(x, 'start') for x in (form.sections if hasattr(form, 'sections') else
                                                 form if isinstance(form, (list, tuple)) else [form]))
    if at is not None:
        a_ = _pos(at)
        if placed and abs(a_ - abs_start) > _EPS:
            raise ComposeError(f"drummer.arrange: at={a_:g} but the sections start at beat {abs_start:g} (at= places "
                               f"a form of (name, bars) pairs)")
        abs_start = a_
    elif not placed and memory is not None:
        abs_start = memory.clock
    base = abs_start
    fill_w = dict(fills if fills is not None else ST['fills'])
    for k in fill_w:
        if k not in FILL_KINDS:
            raise ComposeError(f"unknown drummer fill {k!r}; use {', '.join(FILL_KINDS)}")
    sw = ST.get('swing', 0.5) if swing is None else _num(swing, 'drummer swing', 0.5, 0.75)
    sgrid = ST.get('swing_grid', 0.5)
    tms = ST['timing_ms'] if timing_ms is None else _num(timing_ms, 'drummer timing_ms', 0, 25)
    fl = _feel_of(feel, ST)
    lock_notes = None
    if lock_mode not in ('with', 'answer'):
        raise ComposeError(f"drummer lock_mode must be 'with' or 'answer', got {lock_mode!r}")
    if lock is not None:
        if hasattr(lock, 'notes') and hasattr(lock, 'instrument'):       # a Track: its notes, absolute beats
            lock_notes = [n._replace(start=n.start - abs_start) for n in lock.notes]
        else:
            try:
                lock_notes = list(as_clip(lock))
            except ComposeError:
                raise ComposeError(f"drummer lock must be a Track or a Clip (the bass part), got {lock!r}") from None

    # ---- the section plans
    secs: list[dict] = []
    role_cells: dict = {}
    role_count: dict = {}
    for i, (name, t, bars, bpb) in enumerate(secs_in):
        opts = plan.get(name, {})
        if isinstance(opts, str):
            opts = _shorthand(opts)
        if not isinstance(opts, dict):
            raise ComposeError(f"drummer plan[{name!r}] must be a dict or a shorthand string, got {opts!r}")
        for k in opts:
            if k not in _PLAN_KEYS:
                raise ComposeError(f"drummer plan[{name!r}]: unknown key {k!r}; keys: {', '.join(sorted(_PLAN_KEYS))}")
        _check_plan(name, opts)
        sst = opts.get('style', style)
        if sst not in STYLES:
            raise ComposeError(f"drummer plan[{name!r}] style must be one of {', '.join(STYLES)}, got {sst!r}")
        st = STYLES[sst]
        if abs(bpb - 4.0) > _EPS and st.get('special') != 'jazz':
            raise ComposeError(f"drummer: section {name!r} is {bpb:g} beats per bar; the {sst!r} grooves are 4/4 "
                               f"(style='jazz' plays 3/4 too)")
        role = opts.get('role', _role_of(name))
        if role not in ROLES:
            raise ComposeError(f"drummer plan[{name!r}] role must be one of {', '.join(ROLES)}, got {role!r}")
        n_rep = role_count.get(role, 0)
        role_count[role] = n_rep + 1
        e = opts.get('energy', min(0.97, ROLES[role] + (0.04 * n_rep if role in ('chorus', 'solo') else 0.0)))
        e = _num(e, f"drummer plan[{name!r}] energy", 0, 1)
        tk = opts.get('time', st['time'].get(role, 'hat' if st['hat'].startswith('hat') else st['hat']))
        tk, _, mode = tk.partition('/')
        mode = opts.get('mode', mode)
        if tk not in TIMEKEEPERS:
            raise ComposeError(f"drummer plan[{name!r}] time must be one of {', '.join(TIMEKEEPERS)}, got {tk!r}")
        if mode not in MODES:
            raise ComposeError(f"drummer plan[{name!r}] mode must be one of {', '.join(repr(m) for m in MODES)}, "
                               f"got {mode!r}")
        if tk in ('ride', 'ride_bell', 'bell') and not K.has('ride') and not K.has('bell'):
            tk = 'hat_loose' if K.has('hat_open') else 'hat'
        if tk == 'floor' and not K.toms:
            tk, mode = 'hat', mode or 'half'
        if role == 'break':
            tk = opts.get('time', 'hat4')
        # the kick cells: the calm set below energy 0.62, the busy set above; one cell per role (repeats reuse it),
        # a variation for the 4th bar
        key_ = (sst, role if e < 0.62 else 'busy')
        if key_ not in role_cells:
            pool = st['kicks'][0 if e < 0.62 else 1] or ('x.......x.......',)
            weights = {c: (1.0 if j == 0 else 0.35 + dens) for j, c in enumerate(pool)}
            a_ = _pick(rng, weights)
            b_ = _pick(rng, {c: w for c, w in weights.items() if c != a_}) or _vary_kick(a_, rng)
            gh_p = opts.get('ghosts', dens)
            ga = sorted(s for s, w in st['ghosts'].items() if rng.random() < w * (0.3 + 1.0 * gh_p) * (1.15 - 0.45 * e))
            gb = sorted(set(ga) | {s for s, w in st['ghosts'].items() if rng.random() < w * 0.4 * gh_p})
            role_cells[key_] = (a_, b_, ga, gb, _pick(rng, {c: 1.0 for c in _KICK_HALF}))
        a_, b_, ga, gb, kh = role_cells[key_]
        side = opts.get('side', role in st.get('side', ()) and K.has('side'))
        rim = opts.get('rimshot', e >= st['rimshot'] and K.has('rimshot'))
        open_p = (0.15 + 0.7 * dens) * (0.5 + e) if st['opens'] else 0.0
        secs.append(dict(name=name, a=t, bars=bars, bpb=bpb, role=role, e=e, time=tk, mode=mode, style=sst,
                         kick_a=a_, kick_b=b_, kick_half=kh, ghosts_a=ga, ghosts_b=gb, side=bool(side),
                         rimshot=bool(rim), open_p=open_p, opts=opts, end=t + bars * bpb, sweep=opts.get('sweep')))
        if lock_notes is not None and opts.get('lock', True) and not st.get('special'):
            backs = _trade_steps(st, mode)
            secs[-1]['lock_mode'] = lock_mode
            secs[-1]['lock'] = _lock_steps(lock_notes, t, int(math.ceil(bars - _EPS)), bpb, backs,
                                           _hat_rhythm(tk, st, b) == 'hat16' or sw != 0.5 and sgrid < 0.5)
    total = secs[-1]['end']
    last = secs[-1]
    end_mode = ending if ending is not None else ('groove' if last['role'] != 'end'
                                                  else 'roll' if last['bars'] >= 2 else 'hit')
    end_t = None
    if end_mode in ('hit', 'roll', 'choke'):
        end_t = last['a'] if last['role'] == 'end' else max(last['a'], last['end'] - last['bpb'])

    # ---- grooves
    hits: list[Hit] = []
    moves: list = []
    ctxs = {}
    for si, sp in enumerate(secs):
        st = STYLES[sp['style']]
        ctx = ctxs.setdefault(sp['style'], _Ctx(K, b, rng, st, dens))
        n_bars = int(math.ceil(sp['bars'] - _EPS))
        moves.append((sp['a'], sp['end'], 'groove', f"{sp['style']}:{sp['role']}:{sp['time']}"
                                                    f"{'/' + sp['mode'] if sp['mode'] else ''}"))
        if st.get('special') == 'jazz':
            hs = _jazz_section(sp['a'], n_bars, sp, ctx, seed_int(f"{seed_int(seed)}:{si}"))
            for h in hs:
                h.bar = (si, int((h.t - sp['a']) // sp['bpb']))
            hits += [h for h in hs if h.t < sp['end'] - _EPS]
            continue
        for bi in range(n_bars):
            t0 = sp['a'] + bi * sp['bpb']
            e = sp['e']
            if sp['role'] == 'pre':
                e = min(1.0, e + 0.12 * bi / max(1, n_bars - 1))
            elif sp['role'] == 'break' and bi == 0:
                continue                                   # the stop: see below
            for h in _groove_bar(t0, sp, ctx, bi, e):
                if h.t < sp['end'] - _EPS:
                    h.bar = (si, bi)
                    hits.append(h)

    # ---- fill candidates: into every section (structural), into 4 / 8-bar phrases (chance by density)
    cands: list[dict] = []
    for si, sp in enumerate(secs):
        nxt = secs[si + 1] if si + 1 < len(secs) else None
        bpb = sp['bpb']
        n_bars = int(math.ceil(sp['bars'] - _EPS))
        for k in (range(4, n_bars, 4) if phrase_fills else ()):
            if end_t is not None and abs(sp['a'] + k * bpb - end_t) < _EPS:
                continue
            p = (0.3 + 0.6 * dens) if k % 8 == 0 else (0.1 + 0.45 * dens)
            p *= 0.6 + 0.6 * sp['e']
            if sp['role'] == 'break' or rng.random() >= p:
                continue
            L = 2.0 if k % 8 == 0 else 1.0
            cands.append(dict(t=sp['a'] + k * bpb, len=L, score=1.5 if k % 8 == 0 else 1.0, structural=False,
                              sec=si, into=None, e=sp['e']))
        if nxt is None:
            continue
        o = nxt['opts']
        if o.get('fill') is False or nxt['role'] == 'break' or sp['opts'].get('stop'):
            continue
        L = o.get('fill_len')
        if L is None:
            if nxt['role'] in ('chorus', 'solo', 'end'):
                L = 4.0 if dens >= 0.45 and nxt['e'] >= 0.7 else 2.0
            elif nxt['role'] in ('verse', 'bridge', 'outro', 'post'):
                L = 2.0
            else:
                L = 1.0 if dens < 0.5 else 2.0
            if sp['e'] < 0.3:
                L = min(L, 1.0)
        L = min(_num(L, 'fill_len', 0.25, 16), sp['bars'] * bpb)
        kind = o.get('fill')
        build = o.get('build', sp['role'] == 'pre' and nxt['role'] in ('chorus', 'solo')
                      and STYLES[sp['style']].get('builds', True))
        if build and kind is None:
            kind = 'build'
            L = bpb * (2 if sp['bars'] >= 4 and dens >= 0.6 else 1)
            L = min(L, sp['bars'] * bpb)
        dout = o.get('dropout', kind is None and nxt['role'] == 'chorus' and sp['role'] not in ('break', 'intro')
                     and sp['e'] >= 0.4 and rng.random() < 0.25 * dens)
        if dout:
            L = min(2.0, sp['bars'] * bpb)
        cands.append(dict(t=nxt['a'], len=L, score=3.0 + nxt['e'], structural=True, sec=si, into=si + 1,
                          e=max(sp['e'], nxt['e'] * 0.9), kind=kind, dropout=bool(dout)))
    if end_t is not None and end_t > last['a'] + _EPS:          # a final hit on the last bar: a fill into it
        cands.append(dict(t=end_t, len=2.0, score=3.5, structural=True, sec=len(secs) - 1, into=None,
                          e=max(0.75, last['e']), kind=None, dropout=False))
    bar_len = secs[0]['bpb']                        # the budgets count bars of the form's meter (jazz plays 3/4)
    bud = _fill_budget(memory, bar_len, fe, xe, se)
    kept, refused = _budget(cands, bud, base, fe)

    # ---- choose fill kinds (structural first) under the flashy budget, place them
    budget_log = {'fill_every': fe, 'flashy_every': xe, 'same_every': se, 'crash_every': ce, 'fills': [],
                  'flashy': [], 'dropped': [], 'phrase_refused': len(refused)}
    placed_fills = []
    for c in sorted(kept, key=lambda c: (-c['score'], c['t'])):
        sp = secs[c['sec']]
        ctx = ctxs.get(sp['style']) or ctxs.setdefault(sp['style'], _Ctx(K, b, rng, STYLES[sp['style']], dens))
        L = c['len']
        a = c['t'] - L
        T = base + c['t']
        if c.get('dropout'):
            kind = 'dropout'
        else:
            kind = c.get('kind')
            w = dict(fill_w if sp['style'] == style else STYLES[sp['style']]['fills'])
            if not K.toms:
                w.pop('toms', None)
            if L < 1.0 - _EPS:
                w = {'pickup': 1.0}
            elif L >= 2.0 - _EPS and len(w) > 1 and c['e'] >= 0.5:
                w.pop('pickup', None)              # a pickup is a short move: a longer slot into a big part gets a
                #                                    real fill; into a calm part the groove going on + a pickup is fine
            elif L < 2.0 - _EPS:
                w = {k: v for k, v in w.items() if k in ('pickup', 'snare', 'toms', 'flams', 'eighths', 'slap',
                                                          'triplets')}
            # not the kind of the fill just before or just after it in time (kinds are chosen by priority, not in
            # time order): no snare run answered by the same snare run
            before = [p[1] for p in sorted(placed_fills, key=lambda p: -p[0]['t']) if p[0]['t'] < c['t']][:1]
            after = [p[1] for p in sorted(placed_fills, key=lambda p: p[0]['t']) if p[0]['t'] > c['t']][:1]
            near = tuple(before + after)
            if kind is None:
                # the showy fills belong to the big moments: weighted by the energy they lead into, none into a
                # calm part (unless the drummer is busy)
                ww = {k: v * ((0.3 + c['e']) if k in FLASHY else 1.0) for k, v in w.items()
                      if k not in ('roll', 'build') and not (k in FLASHY and c['e'] < 0.5 and dens <= 0.8)}
                kind = _pick(rng, ww, avoid=near) or 'snare'
            flashy = kind in FLASHY and L >= 2.0 - _EPS
            if flashy and not c.get('kind'):
                ok = bud.allows(T, 'flashy', kind)
                if not ok:
                    # a plainer move instead: the snare run, or - the tasteful one - the groove going on into a
                    # pickup (not what the neighbouring fills play)
                    plain = {k: v for k, v in w.items() if k not in FLASHY + ('roll', 'build')}
                    plain.setdefault('pickup', fill_w.get('pickup', 1.0) if sp['style'] == style else 1.0)
                    sub = _pick(rng, plain, avoid=near) or 'snare'
                    budget_log['dropped'].append((round(a, 4), kind, sub))
                    moves.append((a, c['t'], 'dropped', kind))
                    kind = sub
                    flashy = False
            if flashy:
                bud.book(T, 'flashy', kind)
                budget_log['flashy'].append((round(a, 4), kind))
        placed_fills.append((c, kind, a, L))
        budget_log['fills'].append((round(a, 4), kind, L))
        if memory is not None:
            memory.fills.append((T, kind, kind in FLASHY and L >= 2.0 - _EPS))

    for c, kind, a, L in sorted(placed_fills, key=lambda x: x[2]):
        sp = secs[c['sec']]
        ctx = ctxs[sp['style']]
        e = c['e']
        if kind == 'dropout':
            end = c['t']
            span0 = end - min(L, 2.0)
            hits = [h for h in hits if not (span0 - _EPS <= h.t < end - _EPS and h.limb in ('R', 'L', 'RF', 'X'))]
            for s in (0.0, 1.0):
                if span0 + s < end - _EPS:
                    hits.append(_h(span0 + s, 'hat', _lvl('hat', e * 0.6, ctx.soft), 'R', 'time'))
            fh = _f_pickup(end - 0.5, 0.5, ctx, e)
            moves.append((span0, end, 'dropout', 'hat'))
        else:
            # the hands leave the time for the fill; the feet keep what the fill does not take
            lo = (c['t'] - 0.5 if kind == 'pickup' else a) - _EPS
            hits = [h for h in hits if not (lo <= h.t < c['t'] - _EPS and (h.limb in ('R', 'L', 'X')
                                                                             or (h.limb == 'RF' and kind != 'pickup')))]
            fh = _fill_hits(kind, a, L, ctx, e)
            moves.append((a, c['t'], 'build' if kind == 'build' else 'fill', kind))
        for h in fh:
            h.bar = (c['sec'], int((a - sp['a']) // sp['bpb']))
        hits += fh

    # ---- crashes: section downbeats (with the kick), after fills in the big parts, 8-bar phrases in the chorus
    crash_at: list[tuple[float, float, str]] = []
    fill_ends = {round(c['t'], 4) for c, k, _, _ in placed_fills if k != 'dropout'}
    last_crash = -math.inf
    china_used = -math.inf
    for si, sp in enumerate(secs):
        st = STYLES[sp['style']]
        want = sp['opts'].get('crash')
        prev_fill = round(sp['a'], 4) in fill_ends
        if want is None:
            if st.get('special') == 'jazz':
                want = si > 0 and sp['e'] >= 0.7
            else:
                want = sp['role'] != 'break' and (si > 0 or sp['e'] >= 0.6) and (sp['e'] >= 0.4 or prev_fill)
        if want and sp['role'] != 'end':
            crash_at.append((sp['a'], sp['e'], 'section'))
            last_crash = sp['a']
        n_bars = int(math.ceil(sp['bars'] - _EPS))
        for k in range(1, n_bars):
            t = sp['a'] + k * sp['bpb']
            after_fill = round(t, 4) in fill_ends
            phrase = k % 8 == 0 and sp['e'] >= 0.75
            if (after_fill and sp['e'] >= 0.6 or phrase) and t - last_crash >= ce * sp['bpb'] - _EPS:
                crash_at.append((t, sp['e'], 'phrase'))
                last_crash = t
    for t, e, why in crash_at:
        si = max(i for i, s in enumerate(secs) if s['a'] <= t + _EPS)
        st = STYLES[secs[si]['style']]
        ctx = ctxs[secs[si]['style']]
        cw = {k: v for k, v in st['crashes'].items() if K.has(k)} or {'crash': 1.0}
        if 'china' in cw and (e < 0.85 or t - china_used < 16 * 4.0):
            cw.pop('china')
        piece = _pick(rng, cw) or 'crash'
        if piece == 'china':
            china_used = t
        # the crash replaces the time stroke of the right hand on that beat; an open hat ringing into it is closed
        # by the foot
        hits = [h for h in hits if not (abs(h.t - t) < _EPS and h.limb == 'R' and h.tag in ('time', 'open'))]
        hc = _crash_hits(t, ctx, e, piece)
        if any(h.tag == 'open' and t - 0.75 < h.t < t - _EPS for h in hits) and \
                not any(h.limb == 'LF' and abs(h.t - t) < _EPS for h in hits):
            hc.append(_h(t, 'hat_pedal', _lvl('pedal', e, ctx.soft), 'LF', 'pedal'))
        for h in hc:
            h.bar = (si, int(round((t - secs[si]['a']) / secs[si]['bpb'])))
        hits += hc
        moves.append((t, t, 'crash', piece))

    # ---- stops (a break section / stop=True) and the ending
    for si, sp in enumerate(secs):
        ctx = ctxs[sp['style']]
        if sp['role'] == 'break':
            t = sp['a']
            hs = _stop_hits(t, ctx, max(sp['e'], 0.8))
            for h in hs:
                h.bar = (si, 0)
            hits += hs
            moves.append((t, t + sp['bpb'], 'stop', 'break'))
        if sp['opts'].get('stop'):
            t = sp['end'] - sp['bpb']
            hits = [h for h in hits if not (t - _EPS <= h.t < sp['end'] - _EPS)]
            hs = _stop_hits(t, ctx, max(sp['e'], 0.8))
            hs += _f_pickup(sp['end'] - 0.5, 0.5, ctx, sp['e'])
            for h in hs:
                h.bar = (si, int(sp['bars']) - 1)
            hits += hs
            moves.append((t, sp['end'], 'stop', 'bar'))
    if end_t is not None:
        ctx = ctxs[last['style']]
        t = end_t
        hits = [h for h in hits if h.t < t - _EPS]        # the fill into the end stays, the groove stops
        moves = [m for m in moves if not (m[2] == 'crash' and m[0] >= t - _EPS)]
        quiet_end = STYLES[last['style']].get('special') in ('jazz', 'bossa')
        e_end = 0.25 if quiet_end else last['e']              # a jazz ending: a soft cymbal and a feathered kick
        hs = _big_hit(t, ctx, e_end) if not quiet_end or end_mode in ('hit', 'choke') else []
        if end_mode == 'choke':
            # the hit, grabbed: the hands choke the cymbals a beat later (the kit's choke keys; without them the
            # cymbals ring and the warning names the missing piece)
            for h in [h for h in hs if h.piece in _CHOKES]:
                hs.append(_h(t + 1.0, _CHOKES[h.piece], 90.0, h.limb, 'hit'))
        if end_mode == 'roll' and last['end'] - t >= 3.0:
            r0, r1 = t + 1.0, last['end'] - 1.0
            st_ = STYLES[last['style']]
            quiet = st_.get('special') in ('jazz', 'bossa')           # a ride swell, not a tom rumble
            toms = st_.get('end_roll', 'toms') == 'toms' and not quiet
            hs += _swell_hits(r0, r1 - r0, ctx, e_end * (1.0 if toms else 0.85), toms=toms,
                              piece='ride' if quiet else 'crash')
            hs += _big_hit(r1, ctx, e_end)
        for h in hs:
            h.bar = (len(secs) - 1, int((h.t - last['a']) // last['bpb']))
        hits += hs
        moves.append((t, last['end'], 'ending', end_mode))

    # ---- swing (on the grid, so the limb rules judge the swung strokes), make it playable, touch, feel
    if sw != 0.5:
        _swing(hits, sw, sgrid)
    hits, dropped = _resolve(hits, b)
    _touch(hits, secs, rng, bool(ST.get('machine')))
    if hands is not None:
        # the fills played by the hands of the solo layer: the weaker hand, rebounds, up-strokes, reach (levels only:
        # the style's feel below keeps the timing)
        hand_fills = [h for h in hits if h.tag in ('fill', 'roll', 'build', 'swell') and h.limb in ('R', 'L')]
        for h in hand_fills:
            h.kind = 'A' if abs(h.t - round(h.t)) < _EPS else 'T'
        perform_hits(hand_fills, b, hands=hands, seed=seed, kit=K, timing=False)
    if human:
        _feel(hits, b, fl, tms, rng, drift=not ST.get('machine'))
    clip = _to_clip(hits, K, b, total)
    warns = missing_pieces(hits, K)
    budget_log['limb_conflicts_resolved'] = dropped
    if memory is not None:
        memory.clock = base + total
    plan_out = [dict(name=s['name'], role=s['role'], energy=round(s['e'], 3), time=s['time'], mode=s['mode'],
                     style=s['style'], kick=s['kick_a'], kick_var=s['kick_b'], ghosts=s['ghosts_a'],
                     side=s['side'], rimshot=s['rimshot']) for s in secs]
    perf = Performance(clip, abs_start, hits, sorted(moves, key=lambda m: (m[0], m[2])), plan_out, budget_log, K, b)
    perf.warnings = warns
    return perf


def _check_plan(name: str, opts: dict) -> None:
    """Strict plan values: a wrong fill kind or a non-bool switch is an error, not a crash later or a silent no-op."""
    f = opts.get('fill')
    if f is not None and f is not False and f not in FILL_KINDS:
        raise ComposeError(f"drummer plan[{name!r}] fill must be one of {', '.join(FILL_KINDS)} or False (no fill "
                           f"into this section), got {f!r}")
    for k in ('crash', 'build', 'stop', 'dropout', 'side', 'rimshot', 'lock'):
        if k in opts and not isinstance(opts[k], bool):
            raise ComposeError(f"drummer plan[{name!r}] {k} must be True or False, got {opts[k]!r}")
    if 'ghosts' in opts:
        _num(opts['ghosts'], f"drummer plan[{name!r}] ghosts", 0, 1)
    if opts.get('sweep') is not None:
        _num(opts['sweep'], f"drummer plan[{name!r}] sweep (beats)", 0.25, 16)
    if 'time' in opts and not isinstance(opts['time'], str):
        raise ComposeError(f"drummer plan[{name!r}] time must be a timekeeper name ({', '.join(TIMEKEEPERS)}), "
                           f"got {opts['time']!r}")


def _vary_kick(cell: str, rng: random.Random) -> str:
    """A variation of a kick cell: an extra kick on the & of 4 or the a of 3 (never on a backbeat)."""
    c = list(cell)
    for s in rng.sample((14, 11, 6), 3):
        if c[s] == '.':
            c[s] = 'x'
            break
    return ''.join(c)


def _shorthand(s: str) -> dict:
    if s in ROLES:
        return {'role': s}
    if s in STYLES:
        return {'style': s}
    if s in MODES and s:
        return {'mode': s}
    tk, _, mode = s.partition('/')
    if tk in TIMEKEEPERS:
        return {'time': s}
    if s == 'stop':
        return {'stop': True}
    raise ComposeError(f"drummer plan shorthand {s!r}: use a role ({', '.join(ROLES)}), a timekeeper "
                       f"({', '.join(TIMEKEEPERS)}), a mode ('half', 'four'), a style or 'stop'")


_FEELS = {'on': {'R': 0.0, 'L': 0.0, 'RF': 0.0, 'LF': 0.0},
          'laid_back': {'R': 2.0, 'L': 8.0, 'RF': 2.0, 'LF': 2.0},
          'push': {'R': -4.0, 'L': -2.0, 'RF': -2.0, 'LF': -3.0}}


def _feel_of(feel, st: dict) -> dict:
    if feel is None:
        return dict(st['feel'])
    if isinstance(feel, str):
        if feel in _FEELS:
            return dict(_FEELS[feel])
        if feel in STYLES:
            return dict(STYLES[feel]['feel'])
        raise ComposeError(f"drummer feel must be one of {', '.join(_FEELS)}, a style name or a dict of limb -> ms, "
                           f"got {feel!r}")
    if isinstance(feel, dict):
        out = {}
        for k, v in feel.items():
            if k not in LIMBS:
                raise ComposeError(f"drummer feel: unknown limb {k!r}; limbs: {', '.join(LIMBS)}")
            out[k] = _num(v, f"drummer feel[{k!r}] (ms)", -30, 30)
        return out
    raise ComposeError(f"drummer feel must be a name or a dict, got {feel!r}")


def _stop_hits(t: float, ctx: _Ctx, e: float) -> list[Hit]:
    """The band stop: crash + kick + snare together on the beat, then silence."""
    return _crash_hits(t, ctx, e) + [_h(t, 'snare', _lvl('backbeat', e, ctx.soft), 'L', 'hit')]


def _big_hit(t: float, ctx: _Ctx, e: float) -> list[Hit]:
    """The final hit: crash (right hand), crash2 / the ride crash or the snare (left hand) and the kick (e < 0.5: a
    soft one - the crash and a feathered kick, jazz)."""
    if e < 0.5:
        return [_h(t, 'crash', 40 + 30 * e, 'R', 'crash', 4.0), _h(t, 'kick', 34 + 20 * e, 'RF', 'kick', prio=9)]
    left = next((p for p in ('crash2', 'ride_crash') if ctx.kit.has(p) and ctx.kit.key(p) != ctx.kit.key('crash')),
                'snare')                                  # a second cymbal (Big Rusty: the ride crash), else the snare
    return _crash_hits(t, ctx, max(e, 0.9)) + [_h(t, left, _lvl('crash' if left != 'snare' else 'backbeat',
                                                                   max(e, 0.9), ctx.soft), 'L', 'hit', 2.0)]


def _swell_hits(a: float, L: float, ctx: _Ctx, e: float, toms: bool = False, piece: str = 'crash') -> list[Hit]:
    """A cymbal swell (mallet roll on the crash / ride, crescendo 25 -> the fill level) or, toms=True, the rock
    ending's rumble: 16th-note triplets around the toms and snare, crescendo."""
    v1 = _lvl('fill', e, ctx.soft)
    out = []
    if toms and ctx.kit.toms:
        per = 6 if ctx.bpm < 100 else 3
        n = max(2, int(L * per))
        drums = [f'tom{i + 1}' for i in range(len(ctx.kit.toms))] + ['snare']
        for k in range(n):
            x = k / max(1, n - 1)
            out.append(_h(a + k / per, drums[(k // 2) % len(drums)], 45 + (v1 - 45) * x ** 1.4, 'R', 'swell'))
    else:
        step = 0.125 if ctx.bpm < 130 else 0.25
        n = max(2, int(L / step))
        for k in range(n):
            x = k / max(1, n - 1)
            out.append(_h(a + k * step, piece, 22 + (v1 * 0.85 - 22) * x ** 1.6, 'R', 'swell', 0.5))
    _sticking(out)
    return out


# ------------------------------------------------------------------------------------------------ check

def check(part, bpm: float | None = None) -> list[str]:
    """Playability problems of a Performance (or a list of Hits at `bpm`): a limb striking twice closer than it can
    (groove 70 ms, rolls / fills 40 ms, kick 80 ms, hat foot 100 ms), more than two hands at once, an open hat
    closed by the foot at the same moment, a crash without the kick. [] = two hands and two feet can play it."""
    hits = part.hits if isinstance(part, Performance) else list(part)
    b = part.bpm if isinstance(part, Performance) else _bpm(bpm)
    probs = []

    def when(h):
        return h.t + _ms(h.off, b)
    by: dict[str, list[Hit]] = {}
    for h in hits:
        by.setdefault(h.limb, []).append(h)
    for limb, hs in by.items():
        if limb == 'X':
            continue
        hs = sorted((h for h in hs if h.tag != 'bounce'), key=when)
        for p, h in zip(hs, hs[1:]):
            gap = _beats_ms(when(h) - when(p), b)
            roll = (h.tag in _ROLL_TAGS and p.tag in _ROLL_TAGS) or 'grace' in (h.tag, p.tag)
            need = (_ROLL_GAP_MS if roll else _GAP_MS[limb]) - 12.0      # minus the feel's spread
            if 'grace' in (h.tag, p.tag):
                need = 8.0
            if gap < need:
                probs.append(f"{limb} strikes twice {gap:.0f} ms apart at beat {h.t:g} ({p.piece} {p.tag}, "
                             f"{h.piece} {h.tag})")
    tol = _ms(_TOGETHER_MS, b)
    hands = sorted((h for h in hits if h.limb in ('R', 'L') and h.tag not in ('grace', 'bounce')), key=lambda h: h.t)
    for i, h in enumerate(hands):
        n = sum(1 for g in hands[i:i + 4] if abs(g.t - h.t) < tol)
        if n > 2:
            probs.append(f"{n} hand strokes together at beat {h.t:g}")
    opens = [h for h in hits if h.tag == 'open']
    for h in hits:
        if h.piece == 'hat_pedal' and any(abs(h.t - o.t) < tol for o in opens):
            probs.append(f"the hat foot closes an open hat as it is struck at beat {h.t:g}")
        if h.tag == 'crash' and not any(k.limb == 'RF' and abs(k.t - h.t) < tol for k in hits):
            probs.append(f"a crash without the kick at beat {h.t:g}")
    return probs


# ------------------------------------------------------------------------------------------------ moves

def _move(hits: list[Hit], kit, bpm: float, length: float, at, seed, timing_ms: float) -> Clip:
    K = Kit.of(kit)
    rng = random.Random(seed_int(seed))
    hits, _ = _resolve(hits, bpm)
    for h in hits:
        h.bar = None
    _touch(hits, [], rng, False)
    if timing_ms:
        _feel(hits, bpm, {}, timing_ms, rng, drift=False)
    a = _pos(at)
    for h in hits:
        h.t += a
    return _to_clip(hits, K, bpm, a + length, start_min=0.0)


def _mctx(kit, bpm, seed, energy) -> tuple[_Ctx, float]:
    b = _bpm(bpm)
    e = _num(energy, 'drummer move energy', 0, 1)
    return _Ctx(Kit.of(kit), b, random.Random(seed_int(seed)), STYLES['rock'], 0.5), e


def _len(length, what: str) -> float:
    return _num(length, f"{what} length (beats)", 0.25, 64)


def tom_run(length, bpm, *, kit=None, energy: float = 0.8, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """A fill around the toms high -> low in 16ths (8ths when a hand could not keep 16ths), crescendo, alternating
    hands; 2 beats or longer open on the snare, the kick on the beats under it at energy >= 0.6. A Clip of `length`
    beats from `at` (play it where the fill ends on the next downbeat); kit: Kit.of(...)."""
    L = _len(length, 'tom_run')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_toms(0.0, L, ctx, e), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def snare_run(length, bpm, *, kit=None, energy: float = 0.7, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """16ths on the snare, crescendo, accents on the beats, alternating hands (the kick on the beats for 2+ beats at
    energy >= 0.55)."""
    L = _len(length, 'snare_run')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_snare(0.0, L, ctx, e), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def triplet_fill(length, bpm, *, kit=None, energy: float = 0.75, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """8th-note triplets (16th triplets below 80 BPM) from the snare down the toms, the first of each group
    accented, crescendo."""
    L = _len(length, 'triplet_fill')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_triplets(0.0, L, ctx, e), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def flam_fill(length, bpm, *, kit=None, energy: float = 0.75, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """Flam accents on the 8ths down the kit: a soft grace note 15-25 ms before each main stroke, by the other hand
    (right and left flams alternate). The first grace falls just before `at` (at 0 it lands on it)."""
    L = _len(length, 'flam_fill')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_flams(0.0, L, ctx, e), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def linear_fill(length, bpm, *, kit=None, energy: float = 0.75, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """A linear fill in 16ths: right hand, left hand, kick, ... - no two limbs ever together; the hands walk down the
    toms."""
    L = _len(length, 'linear_fill')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_linear(0.0, L, ctx, e), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def pickup(bpm, *, length: float = 1.0, kit=None, energy: float = 0.7, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """A pickup into the next downbeat (the end of the clip): a flam on the & of the last beat, two 16ths (& a) or
    snare + floor tom on the a (seeded)."""
    L = _len(length, 'pickup')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_pickup(0.0, L, ctx, e), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def roll(length, bpm, *, kit=None, energy: float = 0.7, seed=0, at=0.0, timing_ms: float = 2.0) -> Clip:
    """A snare roll crescendo (patterns.snare_roll: 32nds, 16ths above 150 BPM, alternating hands) with the kick on
    the beats."""
    L = _len(length, 'roll')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_roll(0.0, L, ctx, e), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def build(length, bpm, *, kit=None, energy: float = 0.75, seed=0, at=0.0, timing_ms: float = 2.0) -> Clip:
    """The pre-chorus build (patterns.snare_roll(build=True)): snare 8ths -> 16ths -> 32nds, crescendo, the kick on
    the beats. Place it over the last 1-2 bars before the chorus (with a crash_hit on the chorus downbeat)."""
    L = _len(length, 'build')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_f_roll(0.0, L, ctx, e, build=True), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def stop(bpm, *, length: float = 4.0, kit=None, energy: float = 0.9, pickup_into: bool = True, seed=0, at=0.0,
         timing_ms: float = 3.0) -> Clip:
    """The band stop: crash + kick + snare on the downbeat, silence for the rest of `length` beats, and (pickup_into)
    a pickup into the next downbeat."""
    L = _len(length, 'stop')
    ctx, e = _mctx(kit, bpm, seed, energy)
    hs = _stop_hits(0.0, ctx, e)
    if pickup_into and L >= 1.0:
        hs += _f_pickup(L - 0.5, 0.5, ctx, e)
    return _move(hs, ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def dropout(bpm, *, length: float = 2.0, kit=None, energy: float = 0.6, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """A drop-out before a big downbeat: only the hi-hat on the beats (the air before the chorus), then a pickup
    into the end of the clip."""
    L = _len(length, 'dropout')
    ctx, e = _mctx(kit, bpm, seed, energy)
    hs = [_h(float(s), 'hat', _lvl('hat', e * 0.6), 'R', 'time') for s in range(int(math.ceil(L - 0.5 - _EPS)))]
    hs += _f_pickup(L - 0.5, 0.5, ctx, e)
    return _move(hs, ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def swell(length, bpm, *, kit=None, piece: str = 'crash', energy: float = 0.7, seed=0, at=0.0,
          timing_ms: float = 2.0) -> Clip:
    """A cymbal swell: a mallet roll on the crash (or piece='ride') from a whisper to the fill level - into an intro
    or a big downbeat (add a crash_hit at the end)."""
    L = _len(length, 'swell')
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_swell_hits(0.0, L, ctx, e, piece=piece), ctx.kit, ctx.bpm, L, at, seed, timing_ms)


def crash_hit(bpm, *, kit=None, piece: str = 'crash', energy: float = 0.8, seed=0, at=0.0,
              timing_ms: float = 2.0) -> Clip:
    """A crash (or crash2 / china / splash) with the kick under it - the crash a few ms after the foot."""
    ctx, e = _mctx(kit, bpm, seed, energy)
    return _move(_crash_hits(0.0, ctx, e, piece), ctx.kit, ctx.bpm, 1.0, at, seed, timing_ms)


def open_hat(bpm, *, length: float = 0.5, kit=None, energy: float = 0.6, seed=0, at=0.0,
             timing_ms: float = 2.0) -> Clip:
    """An open hi-hat 'bark' held `length` beats, closed by the hat foot (the chick) at its end."""
    L = _len(length, 'open_hat')
    ctx, e = _mctx(kit, bpm, seed, energy)
    hs = [_h(0.0, 'hat_open', _lvl('open', e), 'R', 'open', L), _h(L, 'hat_pedal', _lvl('pedal', e), 'LF', 'pedal')]
    return _move(hs, ctx.kit, ctx.bpm, L + 0.25, at, seed, timing_ms)


def count_in(bpm, *, bars: int = 1, kit=None, energy: float = 0.5, seed=0, at=0.0, timing_ms: float = 3.0) -> Clip:
    """The drummer counts the band in: side stick (or the hat foot) on every beat of `bars` bars, the last two beats
    a little louder."""
    if isinstance(bars, bool) or not isinstance(bars, int) or bars < 1:
        raise ComposeError(f"count_in bars must be an int >= 1, got {bars!r}")
    ctx, e = _mctx(kit, bpm, seed, energy)
    piece = 'side' if ctx.kit.has('side') else 'hat_pedal'
    n = 4 * bars
    hs = [_h(float(k), piece, _lvl('side', e) * (1.1 if k >= n - 2 else 0.95), 'L' if piece == 'side' else 'LF',
             'time') for k in range(n)]
    return _move(hs, ctx.kit, ctx.bpm, float(n), at, seed, timing_ms)


def beat(style: str = 'rock', bars: int = 1, bpm: float = 120, *, role: str = 'verse', energy: float | None = None,
         density: float = 0.5, kit=None, time: str | None = None, seed=0, human: bool = True) -> Clip:
    """The groove alone - a style's time for one section role, `bars` bars (a main cell with the variation in the 4th
    bar; no fills, no crashes): the same drummer arrange() uses, for loops of your own. time='hat8'|'ride'|...,
    'name/half' for half-time."""
    if isinstance(bars, bool) or not isinstance(bars, int) or bars < 1:
        raise ComposeError(f"drummer.beat bars must be an int >= 1, got {bars!r}")
    opts: dict = {'role': role}
    if energy is not None:
        opts['energy'] = energy
    if time is not None:
        opts['time'] = time
    opts['crash'] = False
    p = arrange([(role, bars)], bpm=bpm, style=style, density=density, seed=seed, kit=kit, plan={role: opts},
                ending='groove', human=human, phrase_fills=False)
    return p.clip


def brushes(bars, *, kit='swirly', style: str = 'medium', sweep=None, seed=0, **kw) -> Clip:
    """patterns.brushes with the kit's brush keymap (Kit.of(kit).brush: Swirly / GM brush kits) - the jazz style's
    time on a brush kit."""
    K = Kit.of(kit)
    if K.brush is None:
        raise ComposeError(f"drummer.brushes: kit {K.name!r} is not a brush kit (use 'swirly' / 'gm_brush' or a "
                           f"brush-kit track)")
    return _brushes(bars, style=style, kit=K.brush, sweep=sweep, seed=seed, **kw)


def ride(bars, *, kit=None, pattern: str = 'spang', vel: float = 72, seed=0, **kw) -> Clip:
    """patterns.ride_pattern on the kit's ride key (straight 8ths; swing it with the feel)."""
    K = Kit.of(kit)
    return _ride_pattern(bars, pattern, kit={'ride': K.key('ride') or K.key('hat')}, vel=vel, seed=seed, **kw)


# ================================================================================================ solo technique
# A drummer taking a SOLO, the hornist's idea for the drums (micro-performance that makes samples sound PLAYED):
# the hands as a player (a lead hand and a weaker one, stick heights, rebounds, up-strokes, reach around the kit,
# speed limits per sticking), the rudiments as real stickings orchestrated around the kit, the feet (double bass,
# heel-toe, the hat foot), hi-hat openness, chokes and swells - and the solo vocabulary (motif, tom melodies,
# polyrhythms, speed bursts, the gated tom break, the big finish) as moves soloist.solo() / perform() string together.

class Hands:
    """A drummer's hands and feet as a player - what makes a solo sound played, not triggered.

    lead ('R' | 'L'): the stronger hand; weak (0..1): how much weaker, later and looser the other hand is (0 = two
    equal hands, 0.3 a good player, 0.7 a beginner): its strokes ~1.8 % x weak softer, weak x 2.5 ms late, spread x
    (1 + weak). Stick heights (fractions of the passage's top level): accent 1.0, tap 0.6 (-9 dB), ghost a real ghost
    18-32 whatever the energy, grace (flam / drag grace notes) 0.36 x the main stroke (at most 52); height: how far a
    stroke height wanders (0.035 = +-3.5 %: a pro's consistency; accents half of it). timing_ms: the timing spread.
    Speed limits (ms between two strokes of ONE hand): single_ms 70 (a wrist stroke; ~14 strokes/s per hand, 28
    between both: a Buddy-Rich burst), double_ms 38 (the rebound of a double stroke), foot_ms 85 (one foot, ankle),
    heel_toe_ms 58 (heel-toe doubles). evenness (0..1): how even a double stroke's rebound is (0.8: ~3-4 % under the
    first). reach_ms: ms per unit of distance on the kit (snare -> floor tom ~1.3 units): a hand that has to cross
    the kit faster than that lands a little softer and later. Timing: each stroke spreads ~0.6 x timing_ms (SD; the
    weak hand, ghosts more, accents less) around a slow wander of each limb (+-3 ms, beat to beat): a drummer's
    micro-timing (4 ms ~ a pro's 2-5 ms; 'master' 3.2, 'student' 9), never the grid."""

    def __init__(self, lead: str = 'R', weak: float = 0.3, accent: float = 1.0, tap: float = 0.6,
                 ghost=(18.0, 32.0), grace: float = 0.36, height: float = 0.035, timing_ms: float = 4.0,
                 single_ms: float = 70.0, double_ms: float = 38.0, foot_ms: float = 85.0,
                 heel_toe_ms: float = 58.0, evenness: float = 0.8, reach_ms: float = 55.0):
        if lead not in ('R', 'L'):
            raise ComposeError(f"Hands lead must be 'R' or 'L', got {lead!r}")
        self.lead = lead
        self.weak = _num(weak, 'Hands weak', 0, 1)
        self.accent = _num(accent, 'Hands accent', 0.5, 1.2)
        self.tap = _num(tap, 'Hands tap', 0.2, 1.0)
        if not (isinstance(ghost, (tuple, list)) and len(ghost) == 2):
            raise ComposeError(f"Hands ghost must be (lo, hi) velocities, got {ghost!r}")
        self.ghost = (_num(ghost[0], 'Hands ghost lo', 5, 60), _num(ghost[1], 'Hands ghost hi', 5, 60))
        self.grace = _num(grace, 'Hands grace', 0.1, 0.8)
        self.height = _num(height, 'Hands height', 0, 0.2)
        self.timing_ms = _num(timing_ms, 'Hands timing_ms', 0, 20)
        self.single_ms = _num(single_ms, 'Hands single_ms', 30, 200)
        self.double_ms = _num(double_ms, 'Hands double_ms', 20, 120)
        self.foot_ms = _num(foot_ms, 'Hands foot_ms', 40, 250)
        self.heel_toe_ms = _num(heel_toe_ms, 'Hands heel_toe_ms', 30, 200)
        self.evenness = _num(evenness, 'Hands evenness', 0, 1)
        self.reach_ms = _num(reach_ms, 'Hands reach_ms', 0, 200)

    @property
    def weak_hand(self) -> str:
        return 'L' if self.lead == 'R' else 'R'

    def __repr__(self) -> str:
        return (f"Hands(lead={self.lead!r}, weak={self.weak:g}, tap={self.tap:g}, single_ms={self.single_ms:g}, "
                f"double_ms={self.double_ms:g})")


HANDS = {'master': Hands(weak=0.15, height=0.025, timing_ms=3.2, single_ms=62.0, double_ms=34.0, evenness=0.9),
         'pro': Hands(), 'rock': Hands(weak=0.35, tap=0.62, timing_ms=5.0, single_ms=75.0),
         'student': Hands(weak=0.7, height=0.08, timing_ms=9.0, single_ms=95.0, double_ms=55.0, evenness=0.4)}
"""Named players: 'master' (an even weak hand, consistent heights, fast), 'pro' (the default), 'rock', 'student'."""


def _hands(hands) -> Hands:
    if hands is None:
        return HANDS['pro']
    if isinstance(hands, Hands):
        return hands
    if isinstance(hands, str) and hands in HANDS:
        return HANDS[hands]
    raise ComposeError(f"hands must be a drummer.Hands(...) or one of {', '.join(HANDS)}, got {hands!r}")


# the kit as the hands find it (x: left -> right from the drummer's seat, y: near -> far; ~1 unit = a forearm)
_LAYOUT = {'hat': (-1.0, 0.35), 'snare': (-0.35, 0.0), 'ride': (1.25, 0.8), 'bell': (1.15, 0.75),
           'crash': (-0.75, 1.05), 'crash2': (0.55, 1.15), 'china': (1.5, 1.0), 'splash': (0.05, 1.1),
           'cowbell': (0.1, 0.5)}
_SAME_SPOT = {'side': 'snare', 'rimshot': 'snare', 'edge': 'snare', 'clap': 'snare', 'hat_open': 'hat',
              'hat_half': 'hat', 'hat_shank': 'hat', 'hat_splash': 'hat', 'ride_crash': 'ride', 'tamb': 'hat',
              'crash_choke': 'crash', 'ride_choke': 'ride', 'china_choke': 'china'}


def _spot(piece: str, kit: Kit) -> tuple[float, float]:
    piece = _SAME_SPOT.get(piece, piece)
    if piece.startswith('tom') and piece[3:].isdigit() or piece == 'floor':
        n = max(1, len(kit.toms))
        i = n - 1 if piece == 'floor' else min(n - 1, int(piece[3:]) - 1)
        x = i / max(1, n - 1)
        # the rack toms above the kick, the floor toms right of the seat: an arc
        return (-0.15 + 1.2 * x, 0.6 - 0.75 * x * x)
    return _LAYOUT.get(piece, (0.0, 0.5))


def _reach(a: str, b: str, kit: Kit) -> float:
    (x0, y0), (x1, y1) = _spot(a, kit), _spot(b, kit)
    return math.hypot(x1 - x0, y1 - y0)


# ------------------------------------------------------------------------------------------------ the stroke language

STROKE_HELP = """A stroke pattern: one token per grid step, separated by spaces ('|' bar lines are ignored).
  R L      a stroke of the right / left hand (a tap: ~0.6 of the accent height)
  r l      a ghost note (18-32 velocity)
  >R       an accent;  ^R  a rimshot accent (the snare's rim: 'rimshot' where the kit has one)
  fR       a flam (a grace note by the other hand 16-28 ms before);  dR  a drag / ruff (two graces, the other hand)
  zR       a buzz stroke (multiple bounce: the stick presses and bounces 3-6 times; press / buzz rolls)
  RR RLR   several strokes in one step split it evenly (a double stroke = a diddle, a triplet ...)
  K k      the right foot: kick (k soft);  P p  the left foot: hi-hat chick (p soft) - P@kick on a double pedal
  @piece   on that drum / cymbal: R@tom1 >L@floor R@crash P@hat_splash R@hat_half (the piece names of Kit) or
           @0 .. @N (the kit's voices high -> low: 0 the snare, 1 the first tom ...)
  A+B      limbs together: >R@crash+K (a crash with the kick),  R@floor+L@snare
  - .      a rest
Unmarked hand strokes are orchestrated (orchestrate=): all on the snare by default."""

_LIMB_OF = {'R': 'R', 'L': 'L', 'r': 'R', 'l': 'L', 'K': 'RF', 'k': 'RF', 'P': 'LF', 'p': 'LF'}
_MOD_CHARS = '>^fdz'


class _Stroke:
    """One parsed stroke of a pattern before it becomes a Hit."""
    __slots__ = ('t', 'limb', 'kind', 'piece', 'mods', 'dur', 'step', 'sub', 'n', 'idx')

    def __init__(self, t, limb, kind, piece, mods, dur, step, sub, n):
        self.t, self.limb, self.kind, self.piece, self.mods = t, limb, kind, piece, mods
        self.dur, self.step, self.sub, self.n, self.idx = dur, step, sub, n, 0


def _tokens(pattern) -> list[str]:
    if isinstance(pattern, (list, tuple)):
        toks = []
        for p in pattern:
            toks.extend(_tokens(p))
        return toks
    if not isinstance(pattern, str):
        raise ComposeError(f"a stroke pattern must be a string (drummer.STROKE_HELP), got {pattern!r}")
    return [t for t in pattern.replace('|', ' ').split() if t]


def _parse(pattern, grid: float, where: str) -> tuple[list[_Stroke], int]:
    """Parse a stroke pattern into strokes on a grid of `grid` beats per token. Returns (strokes, steps)."""
    toks = _tokens(pattern)
    out: list[_Stroke] = []
    for i, tok in enumerate(toks):
        if tok in ('-', '.'):
            continue
        for part in tok.split('+'):
            piece = None
            if '@' in part:
                part, piece = part.split('@', 1)
                if not piece:
                    raise ComposeError(f"{where}: token {tok!r} has an empty @piece")
            j = 0
            while j < len(part) and part[j] in _MOD_CHARS:
                j += 1
            mods, body = part[:j], part[j:]
            if not body or any(c not in _LIMB_OF for c in body):
                raise ComposeError(f"{where}: cannot read token {tok!r} (step {i + 1}). {STROKE_HELP}")
            if len(set(_LIMB_OF[c] for c in body)) == 1 and len(body) > 1 and _LIMB_OF[body[0]] in ('RF', 'LF') \
                    and 'z' in mods:
                raise ComposeError(f"{where}: a foot cannot buzz ({tok!r})")
            n = len(body)
            for k, c in enumerate(body):
                limb = _LIMB_OF[c]
                kind = 'G' if c.islower() else 'A' if (k == 0 and ('>' in mods or '^' in mods)) else 'T'
                m = mods if k == 0 else ''
                st = _Stroke(i * grid + k * grid / n, limb, kind, piece, m, grid / n, i, k, n)
                out.append(st)
    return out, len(toks)


def _shape_fn(shape):
    """A dynamic shape over a passage: x (0..1) -> a level factor."""
    if shape is None or shape == 'flat':
        return lambda x: 1.0
    if callable(shape):
        return lambda x: float(shape(x))
    if isinstance(shape, (tuple, list)) and len(shape) == 2:
        a, b = (_num(v, 'shape level', 0.1, 1.5) for v in shape)
        return lambda x: a + (b - a) * x
    named = {'cresc': (0.62, 1.0), 'crescendo': (0.62, 1.0), 'decresc': (1.0, 0.62), 'diminuendo': (1.0, 0.62),
             'build': (0.45, 1.05)}
    if shape in named:
        a, b = named[shape]
        return lambda x: a + (b - a) * x ** 1.2
    if shape == 'swell':
        return lambda x: 0.7 + 0.3 * math.sin(math.pi * x)
    if shape == 'wave':
        return lambda x: 0.84 + 0.16 * math.sin(2 * math.pi * x - math.pi / 2) * -1.0
    raise ComposeError(f"shape must be 'flat', 'cresc', 'decresc', 'build', 'swell', 'wave', (lo, hi) or a function "
                       f"x -> factor, got {shape!r}")


ORCHESTRATIONS = ('snare', 'toms', 'around', 'split', 'accents', 'down', 'up', 'hands')
"""How unmarked hand strokes are spread over the kit: snare (all on it), toms / around (the stroke's place in the
passage walks the voices snare -> toms high -> low), down / up (each new group of `group` strokes one voice lower /
higher), split (the lead hand on the floor tom, the other on the snare - paradiddles that talk between two drums),
accents (accents on the toms, descending, taps and ghosts on the snare), hands (R on tom1, L on the snare); or a
list of pieces / voice numbers (stroke i -> list[i % n]), a dict {'R': piece, 'L': piece, 'A': piece (accents), 'G':
piece (ghosts)} or a function (i, n, limb, kind) -> piece."""


def _voice(kit: Kit, v) -> str:
    vs = kit.voices()
    if isinstance(v, int) and not isinstance(v, bool):
        return vs[max(0, min(len(vs) - 1, v))]
    if isinstance(v, str) and v.isdigit():
        return vs[max(0, min(len(vs) - 1, int(v)))]
    return v


def _orchestrate(strokes: list[_Stroke], kit: Kit, how, group: int, lead: str) -> None:
    hand = [s for s in strokes if s.limb in ('R', 'L') and s.piece is None]
    n = len(hand)
    vs = kit.voices()
    nv = len(vs)
    if how is None or how == 'snare':
        for s in hand:
            s.piece = 'snare'
        return
    acc_i = 0
    for i, s in enumerate(hand):
        x = i / max(1, n - 1)
        if how in ('toms', 'around'):
            p = vs[min(nv - 1, int(x * nv))] if n > 1 else vs[0]
        elif how in ('down', 'up'):
            g = i // max(1, group)
            ng = max(1, (n + group - 1) // group)
            j = min(nv - 1, g * nv // ng)
            p = vs[j] if how == 'down' else vs[nv - 1 - j]
        elif how == 'split':
            p = (f'tom{len(kit.toms)}' if kit.toms else 'snare') if s.limb == lead else 'snare'
        elif how == 'hands':
            p = ('tom1' if kit.toms else 'snare') if s.limb == lead else 'snare'
        elif how == 'accents':
            if s.kind == 'A' and kit.toms:
                p = f'tom{acc_i % len(kit.toms) + 1}'
                acc_i += 1
            else:
                p = 'snare'
        elif isinstance(how, (list, tuple)):
            p = _voice(kit, how[i % len(how)])
        elif isinstance(how, dict):
            p = how.get('A' if s.kind == 'A' else 'G' if s.kind == 'G' else '', None) or how.get(s.limb) or 'snare'
            p = _voice(kit, p)
        elif callable(how):
            p = _voice(kit, how(i, n, s.limb, s.kind))
        else:
            raise ComposeError(f"orchestrate must be one of {', '.join(ORCHESTRATIONS)}, a list, a dict or a "
                               f"function, got {how!r}")
        s.piece = p


def _foot_piece(s: _Stroke) -> str:
    if s.piece:
        return s.piece
    return 'kick' if s.limb == 'RF' else 'hat_pedal'


def strokes(pattern, *, grid: float = 0.25, at: float = 0.0, kit=None, energy: float = 0.7, orchestrate=None,
            group: int = 4, shape=None, hands=None, seed=0, repeat: int = 1) -> list[Hit]:
    """A stroke pattern (STROKE_HELP: 'R L >R R | fL l l >R@tom1+K') -> Hits with their limb, stroke kind and the
    level of their stroke height (accent / tap / ghost / feet) at `energy` (0..1: the passage's top level 42 ..
    126), times shape (a dynamic over the passage: 'cresc', 'decresc', 'build', 'swell', 'wave', (lo, hi) or a
    function), orchestrated around the kit (orchestrate=: ORCHESTRATIONS) - unplayed yet: perform_hits() (or
    rudiment() / perform()) gives them the hands' physics (weaker hand, rebounds, up-strokes, reach, flams, drags,
    buzz bounces, timing). grid: beats per token; repeat: the pattern this many times."""
    K = Kit.of(kit)
    H = _hands(hands)
    g = _num(grid, 'strokes grid (beats)', 1 / 64, 4)
    e = _num(energy, 'strokes energy', 0, 1)
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 1:
        raise ComposeError(f"strokes repeat must be an int >= 1, got {repeat!r}")
    sts, n = _parse(_tokens(pattern) * repeat, g, 'drummer pattern')
    _orchestrate(sts, K, orchestrate, int(group), H.lead)
    rng = random.Random(seed_int(seed))
    shp = _shape_fn(shape)
    a = _num(at, 'strokes at (beats)')
    top = 42.0 + 84.0 * e
    span = max(g * n, _EPS)
    out = []
    for s in sts:
        x = min(1.0, s.t / span)
        f = shp(x)
        if s.limb in ('R', 'L'):
            piece = s.piece if s.piece else 'snare'
            piece = _voice(K, piece)
            if '^' in s.mods and piece == 'snare':
                piece = 'rimshot'
            if s.kind == 'G':
                v = rng.uniform(*H.ghost)
            elif s.kind == 'A':
                v = top * H.accent * f
            else:
                v = top * H.tap * f
            tag = 'fill'
        else:
            piece = _foot_piece(s)
            if piece == 'hat_pedal' or piece == 'hat_splash':
                v = (40.0 + 24.0 * e) * (0.7 if s.kind == 'G' else 1.12 if s.kind == 'A' else 1.0)
                tag = 'pedal'
            else:
                v = top * (0.55 if s.kind == 'G' else 1.0 if s.kind == 'A' else 0.9) * (0.75 + 0.25 * f)
                tag = 'fill'
        h = _h(a + s.t, piece, max(1.0, min(127.0, v)), s.limb, tag, dur=max(0.125, s.dur))
        h.kind = s.kind
        h.fx = s.mods.replace('>', '').replace('^', '') or None
        if piece in _HAT_OPEN and piece != 'hat':
            h.open = _HAT_OPEN[piece]
        out.append(h)
    return out


def _gap(a: Hit, b: Hit, bpm: float) -> float:
    return _beats_ms(b.t - a.t, bpm)


def sticking_problems(hits, bpm: float, hands=None) -> list[str]:
    """What two hands and two feet could not play in a list of Hits (strokes() / a solo move) at `bpm`: one hand
    striking again sooner than it can (single_ms for a new stroke, double_ms for the rebound of a double: a stroke
    right after its own hand's, closer than ~3 x double_ms), one foot faster than foot_ms (heel_toe_ms for a
    heel-toe double), a limb playing two things at once. [] = playable."""
    H = _hands(hands)
    b = _bpm(bpm)
    probs = []
    last: dict = {}
    by_t: dict = {}
    last_hand = None
    for h in sorted((h for h in hits if h.tag not in ('grace', 'bounce') and h.limb in LIMBS), key=lambda h: h.t):
        p = last.get(h.limb)
        key = (h.limb, round(h.t, 4))
        if key in by_t and by_t[key].piece != h.piece:
            probs.append(f"{h.limb} plays {by_t[key].piece} and {h.piece} at once at beat {h.t:g}")
        by_t[key] = h
        if p is not None and h.t > p.t + _EPS:
            gap = _gap(p, h, b)
            if h.limb in ('R', 'L'):
                # a double stroke (no stroke of the other hand since this hand's last): the rebound / fingers;
                # a single stroke: the wrist has to lift the stick again
                need = H.double_ms if last_hand is p else H.single_ms
            else:
                need = H.heel_toe_ms if gap < H.foot_ms else H.foot_ms
            if gap < need - 0.5:
                what = 'rebound' if h.limb in ('R', 'L') and need == H.double_ms else 'stroke'
                probs.append(f"{h.limb} {what} {gap:.0f} ms after its last at beat {h.t:g} (needs {need:.0f} ms)")
        last[h.limb] = h
        if h.limb in ('R', 'L'):
            last_hand = h
    return probs


def perform_hits(hits: list[Hit], bpm: float, *, hands=None, seed=0, energy: float = 0.7, kit=None,
                 timing: bool = True) -> list[Hit]:
    """The hands' physics on strokes() Hits (in place; returns them with the graces / bounces added): the weaker
    hand softer, later and looser; stick heights that wander a little (accents least); the rebound of a double
    stroke a little under the first (evenness); an accent right after its own hand's tap needs time to lift the
    stick (at speed the accent contrast shrinks: the Moeller problem); a hand crossing the kit faster than its reach
    lands softer and later; ghosts stay 15-35; flams (a grace 16-28 ms before by the other hand, wider when soft),
    drags (two graces), buzz strokes (3-6 bounces closing in, dying away); timing per limb (the weak hand a little
    late, the feet steady, a push ahead in loud passages). timing=False leaves the timing offsets alone (arrange()
    gives its fills the hands' levels this way and keeps its own feel)."""
    H = _hands(hands)
    b = _bpm(bpm)
    K = Kit.of(kit)
    rng = random.Random(seed_int(seed) ^ 0x5EED)
    e = _num(energy, 'perform_hits energy', 0, 1)
    last: dict = {}
    extra: list[Hit] = []
    last_hand = None
    wander = {lb: 0.0 for lb in LIMBS}            # each limb's slow drift (as arrange()'s feel: +-3 ms)
    beat_of = {lb: None for lb in LIMBS}
    srt = sorted((h for h in hits if h.tag not in ('grace', 'bounce')), key=lambda h: (h.t, h.limb))
    for h in srt:
        p = last.get(h.limb)
        double = h.limb in ('R', 'L') and p is not None and last_hand is p
        if h.limb in wander and beat_of[h.limb] != int(math.floor(h.t + _EPS)):
            wander[h.limb] = max(-3.0, min(3.0, 0.8 * wander[h.limb] + rng.gauss(0.0, 0.9)))
            beat_of[h.limb] = int(math.floor(h.t + _EPS))
        gap = _gap(p, h, b) if p is not None else math.inf
        v = h.vel
        off = 0.0
        if h.limb in ('R', 'L'):
            weak = h.limb != H.lead
            spread = H.timing_ms * (0.6 + (H.weak if weak else 0.0))
            if h.kind == 'G':
                spread *= 1.4
            elif h.kind == 'A':
                spread *= 0.8
            off = rng.gauss(0.0, spread) + (H.weak * 2.5 if weak else 0.0) + wander[h.limb] * H.timing_ms / 4.0
            if h.kind != 'G':
                # the rebound of a double stroke (and, less, a second wrist stroke of the same hand)
                if double and gap < 160.0 and h.kind != 'A' and p.kind != 'G':
                    x = max(0.0, min(1.0, (160.0 - gap) / (160.0 - H.double_ms)))
                    v *= 1.0 - (1.0 - (0.84 + 0.14 * H.evenness)) * x
                    off -= 1.5 * x                     # the rebound comes a hair early
                # an accent right after a tap of the same hand: the stick has to come up first
                if h.kind == 'A' and p is not None and p.kind != 'A' and gap < 170.0:
                    v = p.vel + (v - p.vel) * max(0.45, gap / 170.0)
                if weak:
                    v *= 1.0 - 0.06 * H.weak
                v *= 1.0 + rng.gauss(0.0, H.height * (0.5 if h.kind == 'A' else 1.0) * (1.0 + (H.weak if weak else 0)))
            else:
                v = max(15.0, min(35.0, v * (1.0 + rng.gauss(0.0, 0.08))))
            # crossing the kit: the reach takes time
            if p is not None and p.piece != h.piece and gap < 400.0:
                need = _reach(p.piece, h.piece, K) * H.reach_ms
                if gap < need:
                    lack = (need - gap) / max(need, 1.0)
                    v *= 1.0 - 0.12 * lack
                    off += 4.0 * lack
            if e > 0.7 and h.kind != 'G':
                off -= (e - 0.7) * 4.0                  # loud passages push a little ahead
        elif h.limb in ('RF', 'LF'):
            off = (rng.gauss(0.0, H.timing_ms * 0.5) + (0.8 if h.limb == 'LF' else 0.0)
                   + wander[h.limb] * H.timing_ms / 4.0)
            if p is not None and gap < H.foot_ms:       # the toe of a heel-toe double
                v *= 0.86
            v *= 1.0 + rng.gauss(0.0, 0.03)
        if h.limb in ('R', 'L'):
            last_hand = h
        h.vel = max(1.0, min(127.0, v))
        if timing:
            h.off = max(-20.0, min(20.0, off))
        last[h.limb] = h
        # ornaments
        fx = h.fx or ''
        other = 'L' if h.limb == 'R' else 'R'
        if 'f' in fx and h.limb in ('R', 'L'):
            fl = rng.uniform(16.0, 24.0) + 6.0 * (1.0 - e)
            g = _h(h.t - _ms(fl, b), h.piece if h.piece != 'rimshot' else 'snare',
                   min(52.0, h.vel * H.grace * rng.uniform(0.85, 1.1)), other, 'grace', main=h)
            g.off = h.off
            extra.append(g)
        if 'd' in fx and h.limb in ('R', 'L'):
            d2 = rng.uniform(20.0, 27.0)
            d1 = d2 + rng.uniform(30.0, 40.0)
            gp = h.piece if h.piece != 'rimshot' else 'snare'
            for dd, fv in ((d1, 0.28), (d2, 0.33)):
                g = _h(h.t - _ms(dd, b), gp, min(48.0, max(16.0, h.vel * fv * rng.uniform(0.9, 1.1))), other, 'grace',
                       main=h)
                g.off = h.off
                g.fx = 'drag'
                extra.append(g)
        if 'z' in fx and h.limb in ('R', 'L'):
            # the buzz: until the next stroke of either hand (at most ~140 ms)
            nxt = [x.t for x in srt if x.t > h.t + _EPS and x.limb in ('R', 'L')]
            room = min(140.0, _beats_ms((nxt[0] - h.t) if nxt else 0.5, b) - 6.0)
            dt, t_ms, k = 22.0, 0.0, 1
            while True:
                t_ms += dt
                if t_ms > room or k > 6:
                    break
                bv = h.vel * (0.74 ** k) * rng.uniform(0.9, 1.08)
                if bv < 6.0:
                    break
                bo = _h(h.t + _ms(t_ms, b), h.piece if h.piece != 'rimshot' else 'snare', bv, h.limb, 'bounce',
                        dur=0.05)
                bo.off = h.off
                bo.fx = 'buzz'
                extra.append(bo)
                dt = max(13.0, dt * 0.86)
                k += 1
    hits.extend(extra)
    return hits


def _play(hits: list[Hit], kit, bpm: float, length: float, at, seed, hands, energy: float) -> Clip:
    """Physics, playability, keys: a Clip of `length` beats from `at`."""
    K = Kit.of(kit)
    perform_hits(hits, bpm, hands=hands, seed=seed, energy=energy, kit=K)
    hits, _ = _resolve(hits, bpm)
    a = _pos(at)
    for h in hits:
        h.t += a
    return _to_clip(hits, K, bpm, a + length, start_min=0.0)


def pattern(pat, bpm, *, grid: float = 0.25, kit=None, energy: float = 0.7, orchestrate=None, group: int = 4,
            shape=None, hands=None, seed=0, at=0.0, repeat: int = 1, length=None, check: bool = True) -> Clip:
    """Play a stroke pattern (STROKE_HELP) like a drummer: strokes() + the hands' physics (perform_hits) -> a Clip
    from `at` (length: the pattern's own by default). check=True raises when the hands cannot play it at this
    tempo (sticking_problems: e.g. a single-stroke 32nd run at 240 BPM)."""
    b = _bpm(bpm)
    hs = strokes(pat, grid=grid, kit=kit, energy=energy, orchestrate=orchestrate, group=group, shape=shape,
                 hands=hands, seed=seed, repeat=repeat)
    L = len(_tokens(pat)) * grid * repeat if length is None else _num(length, 'pattern length (beats)', 0.0625)
    if check:
        probs = sticking_problems(hs, b, hands)
        if probs:
            raise ComposeError(f"drummer.pattern at {b:g} BPM: the hands cannot play it - {probs[0]}"
                               + (f" (+{len(probs) - 1} more)" if len(probs) > 1 else '')
                               + " - a slower grid, another sticking, or check=False")
    return _play(hs, kit, b, L, at, seed, hands, _num(energy, 'pattern energy', 0, 1))


# ------------------------------------------------------------------------------------------------ rudiments

RUDIMENTS: dict[str, tuple[str, float]] = {
    # roll rudiments
    'single_stroke_roll': ('R L', 0.25),
    'single_stroke_four': ('R L R >L - -', 1 / 6),
    'single_stroke_seven': ('R L R L R L >R - - - - -', 1 / 6),
    'double_stroke_roll': ('RR LL', 0.25),
    'triple_stroke_roll': ('RRR LLL', 0.5),
    'multiple_bounce_roll': ('zR zL', 0.25),
    'buzz_roll': ('zR zL', 0.25),
    'five_stroke_roll': ('RR LL >R -', 0.25),
    'six_stroke_roll': ('>R LL RR >L', 0.25),
    'seven_stroke_roll': ('RR LL RR >L', 0.25),
    'nine_stroke_roll': ('RR LL RR LL >R - - -', 0.25),
    'ten_stroke_roll': ('RR LL RR LL >R >L - -', 0.25),
    'eleven_stroke_roll': ('RR LL RR LL RR >L - -', 0.25),
    'thirteen_stroke_roll': ('RR LL RR LL RR LL >R -', 0.25),
    'fifteen_stroke_roll': ('RR LL RR LL RR LL RR >L', 0.25),
    'seventeen_stroke_roll': ('RR LL RR LL RR LL RR LL >R - - - - - - -', 0.25),
    # diddle rudiments
    'paradiddle': ('>R L R R >L R L L', 0.25),
    'single_paradiddle': ('>R L R R >L R L L', 0.25),
    'inverted_paradiddle': ('>R L L R >L R R L', 0.25),
    'double_paradiddle': ('>R L R L R R >L R L R L L', 1 / 6),
    'triple_paradiddle': ('>R L R L R L R R >L R L R L R L L', 0.25),
    'paradiddle_diddle': ('>R L R R L L', 1 / 6),
    'paradiddle_diddle_32': ('>R L RR LL', 0.25),
    # flam rudiments
    'flam': ('fR - fL -', 0.5),
    'flam_accent': ('f>R L R f>L R L', 1 / 3),
    'flam_tap': ('f>R R f>L L', 0.25),
    'flamacue': ('fR >L R L fR - - -', 0.25),
    'flam_paradiddle': ('f>R L R R f>L R L L', 0.25),
    'single_flammed_mill': ('f>R R L R f>L L R L', 0.25),
    'flam_paradiddle_diddle': ('f>R L R R L L', 1 / 6),
    'pataflafla': ('fR L R fL', 0.25),
    'swiss_army_triplet': ('f>R R L', 1 / 3),
    'inverted_flam_tap': ('f>R L f>L R', 0.25),
    'flam_drag': ('f>R LL R f>L RR L', 1 / 3),
    # drag rudiments
    'drag': ('d>R - d>L -', 0.5),
    'single_drag_tap': ('dR >L dL >R', 0.25),
    'double_drag_tap': ('dR dR >L - dL dL >R -', 1 / 3),
    'lesson_25': ('dR L >R dL R >L', 1 / 3),
    'single_dragadiddle': ('>R dR R L >L dL L R', 0.25),
    'drag_paradiddle_1': ('>R dR L R R >L dL R L L', 1 / 6),
    'single_ratamacue': ('dR L R >L - -', 1 / 6),
    'double_ratamacue': ('dR dR L R >L -', 1 / 6),
    'triple_ratamacue': ('dR dR dR L R >L', 1 / 6),
    # accent grids on singles (Moeller-style whips: an accent, the downstroke, taps, the upstroke into the next)
    'accent_fours': ('>R l r l >R l r l', 0.25),
    'accent_threes': ('>R l r >L r l >R l', 0.25),
    'accent_triplets': ('>R l r >L r l', 1 / 3),
    'moeller_sixes': ('>R l r >L r l', 1 / 6),
    'herta': ('RL R LR L', 0.25),
}
"""The PAS rudiments (and accent grids) as stickings: name -> (pattern, grid in beats per token). R / L hands,
lowercase ghosts, '>' accents, 'f' flams, 'd' drags, 'z' buzz strokes, two letters in a step = a double stroke
(STROKE_HELP). rudiment(name, bpm, ...) plays them orchestrated around the kit, with the hands' physics."""


def rudiment(name: str, bpm, *, beats: float | None = None, grid: float | None = None, kit=None, energy: float = 0.7,
             orchestrate=None, group: int = 4, shape=None, hands=None, lead: str | None = None, seed=0, at=0.0,
             accents: bool = True) -> Clip:
    """A rudiment played by a drummer: RUDIMENTS[name]'s sticking repeated for `beats` (one cycle by default) on its
    grid (grid= another: 0.125 = twice as fast), with the hands' physics (perform_hits: weaker hand, rebounds,
    up-strokes, flams, drags, buzz), orchestrated around the kit (ORCHESTRATIONS: 'split' paradiddles between floor
    tom and snare, 'accents' on the toms, 'down' a group per drum ...), a dynamic shape ('cresc' ...). lead='L'
    mirrors the sticking (left-hand lead); accents=False plays it unaccented. Raises when the hands cannot play the
    sticking that fast (the error names the limit)."""
    if name not in RUDIMENTS:
        close = [n for n in RUDIMENTS if name.split('_')[0] in n]
        raise ComposeError(f"unknown rudiment {name!r}" + (f" - did you mean {', '.join(close[:4])}?" if close else '')
                           + f"; RUDIMENTS: {', '.join(RUDIMENTS)}")
    pat, g0 = RUDIMENTS[name]
    g = g0 if grid is None else _num(grid, 'rudiment grid (beats)', 1 / 64, 4)
    toks = _tokens(pat)
    if lead == 'L':
        toks = [t.translate(str.maketrans('RLrl', 'LRlr')) for t in toks]
    elif lead not in (None, 'R'):
        raise ComposeError(f"rudiment lead must be 'R' or 'L', got {lead!r}")
    if not accents:
        toks = [t.replace('>', '') for t in toks]
    cyc = len(toks) * g
    L = cyc if beats is None else _num(beats, 'rudiment beats', g)
    reps = max(1, int(math.ceil(L / cyc - 1e-9)))
    seq = (toks * reps)[:max(1, int(round(L / g)))]
    b = _bpm(bpm)
    hs = strokes(seq, grid=g, kit=kit, energy=energy, orchestrate=orchestrate, group=group, shape=shape, hands=hands,
                 seed=seed)
    probs = sticking_problems(hs, b, hands)
    if probs:
        H = _hands(hands)
        raise ComposeError(f"rudiment {name!r} on a {g:g}-beat grid at {b:g} BPM: the hands cannot play it - "
                           f"{probs[0]} (Hands single_ms {H.single_ms:g}, double_ms {H.double_ms:g}); "
                           f"use a slower grid or tempo")
    return _play(hs, kit, b, L, at, seed, hands, _num(energy, 'rudiment energy', 0, 1))


# ------------------------------------------------------------------------------------------------ feet

FEET = ('chick', 'chick4', 'splash', 'four', 'clave', 'samba', 'double', 'heel_toe', 'gallop', 'none')
"""What the feet play under a solo passage: chick (the hat foot on 2 and 4), chick4 (on every beat), splash (the
hat foot splashes on 2 and 4: open-and-close), four (kick quarters + chick 2 & 4), clave (kick on the 3-2 son
clave, chick 2 & 4: the Latin solo ostinato), samba (kick 1 . . a 2 per beat, chick on the &), double (16th double
bass, both feet on the kick: a double pedal), heel_toe (the right foot's heel-toe doubles: kick 'xx.x' per beat),
gallop (kick 'x.xx'), none."""


def _feet(kind: str, a: float, L: float, e: float, bpb: float, bpm: float, hands: Hands) -> list[Hit]:
    if kind not in FEET:
        raise ComposeError(f"feet must be one of {', '.join(FEET)}, got {kind!r}")
    out: list[Hit] = []
    kv = 48.0 + 66.0 * e
    cv = 40.0 + 22.0 * e
    nb = int(math.floor(L + _EPS))

    def kick(t, v, limb='RF', tag='kick'):
        h = _h(t, 'kick', v, limb, tag)
        h.kind = 'T'
        out.append(h)

    def chick(t, v, piece='hat_pedal'):
        h = _h(t, piece, v, 'LF', 'pedal')
        h.kind = 'T'
        out.append(h)
    for k in range(nb):
        t = a + k
        beat = k % int(bpb)
        backbeat = beat % 2 == 1
        if kind in ('chick', 'four', 'clave') and backbeat:
            chick(t, cv)
        elif kind == 'chick4':
            chick(t, cv * (1.08 if backbeat else 0.9))
        elif kind == 'splash' and backbeat:
            chick(t, cv * 1.1, 'hat_splash')
        if kind == 'four':
            kick(t, kv * (1.0 if beat == 0 else 0.9))
        elif kind == 'samba':
            kick(t, kv * 0.95)
            kick(t + 0.75, kv * 0.7)
            chick(t + 0.5, cv * 0.85)
        elif kind == 'double':
            step = 0.25 if _beats_ms(0.5, bpm) >= hands.foot_ms - _EPS else 0.5
            j = 0
            while j * step < 1.0 - _EPS:
                kick(t + j * step, kv * (1.0 if j == 0 else 0.86), 'RF' if j % 2 == 0 else 'LF', 'fill')
                j += 1
        elif kind == 'heel_toe':
            for s, f in ((0.0, 1.0), (0.25, 0.8), (0.75, 0.88)):
                kick(t + s, kv * f, 'RF', 'fill')
        elif kind == 'gallop':
            for s, f in ((0.0, 1.0), (0.5, 0.82), (0.75, 0.86)):
                kick(t + s, kv * f, 'RF', 'fill')
    if kind == 'clave':
        bar2 = 2 * bpb
        n = int(math.floor(L / bar2 + _EPS))
        for c in range(max(1, n)):
            for s in (0.0, 1.5, 3.0, 5.0, 6.0):
                if s < L - _EPS:
                    kick(a + c * bar2 + s, kv * (1.0 if s == 0 else 0.86))
    return [h for h in out if h.t < a + L - _EPS]


def feet(kind: str, bars: float, bpm, *, kit=None, energy: float = 0.6, bpb: float = 4.0, hands=None, seed=0,
         at=0.0) -> Clip:
    """The feet alone under a solo (FEET): the hat foot on 2 and 4, splashes, kick quarters, a clave ostinato,
    samba feet, 16th double bass (alternating feet on one kick: a double pedal), heel-toe doubles, a gallop - with
    the feet's physics (steady, the toe of a heel-toe double softer)."""
    b = _bpm(bpm)
    L = _num(bars, 'feet bars', 0.25) * _num(bpb, 'feet bpb', 1, 16)
    H = _hands(hands)
    hs = _feet(kind, 0.0, L, _num(energy, 'feet energy', 0, 1), bpb, b, H)
    return _play(hs, kit, b, L, at, seed, H, energy)


def double_bass(beats, bpm, *, kit=None, energy: float = 0.8, grid: float = 0.25, accents=None, hands=None, seed=0,
                at=0.0) -> Clip:
    """A double-bass run: both feet alternating on the kick (a double pedal: one drum) in 16ths (grid=), the
    hands accenting on top (accents: a stroke pattern on the same grid, e.g. '>R@crash - - - >L@tom1 - - -'; default
    a crash every bar and a snare on 2 and 4). Raises when one foot would play faster than foot_ms."""
    b = _bpm(bpm)
    L = _num(beats, 'double_bass beats', 0.25)
    g = _num(grid, 'double_bass grid', 1 / 16, 1)
    H = _hands(hands)
    e = _num(energy, 'double_bass energy', 0, 1)
    n = int(round(L / g))
    feet_pat = ['K' if i % 2 == 0 else 'P@kick' for i in range(n)]
    hs = strokes(feet_pat, grid=g, kit=kit, energy=e, hands=H, seed=seed)
    if accents is None:
        per = int(round(1 / g))
        acc = []
        for i in range(n):
            beat, sub = divmod(i, per)
            acc.append('>R@crash' if sub == 0 and beat % 4 == 0 else '>L' if sub == 0 and beat % 2 == 1 else '-')
        accents = acc
    hs += strokes(accents, grid=g, kit=kit, energy=e, hands=H, seed=seed + 1)
    probs = [p for p in sticking_problems(hs, b, H) if p.startswith(('RF', 'LF'))]
    if probs:
        raise ComposeError(f"double_bass at {b:g} BPM on a {g:g}-beat grid: {probs[0]}")
    return _play(hs, kit, b, L, at, seed, H, e)


def choke(bpm, *, piece: str = 'crash', after: float = 1.0, kit=None, energy: float = 0.9, seed=0, at=0.0) -> Clip:
    """A cymbal hit and choke: the crash (or crash2 / ride / china) with the kick, grabbed by the hand `after`
    beats later (the kit's choke key - Big Rusty / Unruly / MF Natural have them; without one the cymbal rings and
    the warning says so). The dramatic stop of a solo or a band hit."""
    if piece not in _CHOKES:
        raise ComposeError(f"choke piece must be one of {', '.join(_CHOKES)}, got {piece!r}")
    b = _bpm(bpm)
    A = _num(after, 'choke after (beats)', 0.0625, 16)
    e = _num(energy, 'choke energy', 0, 1)
    hs = strokes([f'>R@{piece}+K'], grid=A, kit=kit, energy=e, seed=seed)
    c = _h(A, _CHOKES[piece], 70.0 + 30.0 * e, 'R', 'hit', 0.25)
    c.kind = 'T'
    hs.append(c)
    return _play(hs, kit, b, A + 0.5, at, seed, None, e)


def hat_dance(beats, bpm, *, kit=None, energy: float = 0.6, openings: str = 'x.o.x.h.x.o.xx.h', hands=None,
              seed=0, at=0.0) -> Clip:
    """The hi-hat as a solo voice: 16th strokes on the hat whose openness changes stroke by stroke (openings: one
    char per 16th - 'x' closed, 'h' half open, 'o' open, '.' no stroke; repeated over `beats`), the foot closing an
    open hat on the next beat and splashing now and then. On a kit with a live hat (Big Rusty, Unruly: Kit.live_hat)
    the openness is the 'dynamics' lane (Performance.lanes / hat_lane), else closed / half / open samples."""
    b = _bpm(bpm)
    L = _num(beats, 'hat_dance beats', 0.25)
    e = _num(energy, 'hat_dance energy', 0, 1)
    if not openings or any(c not in 'xho.' for c in openings):
        raise ComposeError(f"hat_dance openings: chars x h o . (closed / half / open / none), got {openings!r}")
    n = int(round(L / 0.25))
    toks = []
    for i in range(n):
        c = openings[i % len(openings)]
        hand = 'R' if i % 2 == 0 else 'L'
        if c == '.':
            toks.append('-')
            continue
        piece = {'x': 'hat', 'h': 'hat_half', 'o': 'hat_open'}[c]
        acc = '>' if i % 4 == 0 or c == 'o' else ''
        toks.append(f'{acc}{hand}@{piece}')
    hs = strokes(toks, grid=0.25, kit=kit, energy=e, hands=hands, seed=seed)
    # the foot closes an open hat on the next beat (the 'chick' that ends the bark)
    opens = [h.t for h in hs if h.piece == 'hat_open']
    for t in opens:
        c = math.floor(t + 1.0 + _EPS)
        if c < L and not any(abs(h.t - c) < _EPS and h.limb == 'LF' for h in hs):
            p = _h(c, 'hat_pedal', 40.0 + 20.0 * e, 'LF', 'pedal')
            p.kind = 'T'
            hs.append(p)
    return _play(hs, kit, b, L, at, seed, hands, e)


# ------------------------------------------------------------------------------------------------ the motif

_MOTIF_CELLS = ('x..x..x...x..x..', 'x..x..x.x..x..x.', 'x.x..x.x..x.x...', 'x..x...x..x.x...',
                'x...x.x..x..x...', 'x..x..x.x.x.x...', '..x..x..x..x.x.x', 'x..x.x..x..x.x..')
"""Accent rhythms a solo motif grows from (16ths of one bar): the 3-3-2 family, displaced and answered."""

MOTIF_VARIATIONS = ('repeat', 'orchestrate', 'answer', 'displace', 'flams', 'diminish', 'augment', 'fill', 'kick',
                    'fragment', 'rimshots', 'invert', 'sparse', 'climb')
"""How a drummer varies a motif (DrumMotif.vary): repeat; orchestrate (the accents walk down the toms, the taps
stay on the snare); answer (the second half answers on the toms); displace (shifted by an 8th: the same figure
lands elsewhere); flams (flammed accents); diminish (twice as fast, twice); augment (half as fast, its first half);
fill (the rests filled with ghost notes); kick (ghosts become kicks: a linear version); fragment (the first half
twice); rimshots (rimshot accents); invert (the other hand leads); sparse (ghosts left out: the skeleton); climb (the
accents walk UP the toms into the snare)."""


class DrumMotif:
    """A drum motif: one bar (or any length) of stroke tokens (STROKE_HELP) on a grid - an accent rhythm with
    ghosts between, its sticking alternating so the accents fall on either hand (Moeller-style singles). A solo
    states it, repeats it and varies it (vary(): MOTIF_VARIATIONS) - the drummer's version of a melody's motif.
    DrumMotif.make(seed, ...) grows one from an accent cell; DrumMotif(tokens, grid) takes your own
    ('>R l l >R l r >L - | ...')."""

    def __init__(self, tokens, grid: float = 0.25, name: str = 'motif'):
        self.tokens = _tokens(tokens)
        if not self.tokens:
            raise ComposeError("DrumMotif needs at least one token")
        _parse(self.tokens, 0.25, 'DrumMotif')
        self.grid = _num(grid, 'DrumMotif grid (beats)', 1 / 64, 4)
        self.name = name

    @property
    def beats(self) -> float:
        return len(self.tokens) * self.grid

    def pattern(self) -> str:
        return ' '.join(self.tokens)

    def __repr__(self) -> str:
        return f"DrumMotif({self.pattern()!r}, grid={self.grid:g})"

    @classmethod
    def make(cls, seed=0, *, steps: int = 16, density: float = 0.5, cell: str | None = None,
             grid: float = 0.25) -> 'DrumMotif':
        """A motif from an accent cell (_MOTIF_CELLS, seeded; or cell='x..x..x.') with ghosts between the accents
        (density 0..1) on alternating hands; the bar's first accent leads with the right hand."""
        rng = random.Random(seed_int(seed))
        c = cell if cell is not None else rng.choice(_MOTIF_CELLS)
        if not c or any(ch not in 'x.' for ch in c):
            raise ComposeError(f"DrumMotif cell: 'x' accents and '.' steps, got {c!r}")
        d = _num(density, 'DrumMotif density', 0, 1)
        toks = []
        for i in range(int(steps)):
            hand = 'R' if i % 2 == 0 else 'L'
            if c[i % len(c)] == 'x':
                toks.append('>' + hand)
            elif rng.random() < 0.25 + 0.6 * d:
                toks.append(hand.lower())
            else:
                toks.append('-')
        return cls(toks, grid, name='motif')

    def to_clip(self, kit=None, *, energy: float = 0.6, seed=0) -> Clip:
        """The motif as drum notes on `kit`'s keys (accents / taps / ghosts at `energy`, no hand physics): what
        soloist.solo() carries around as the motif."""
        K = Kit.of(kit)
        hs = strokes(self.tokens, grid=self.grid, kit=K, energy=energy, seed=seed)
        notes = []
        for h in hs:
            k = K.key(_hat_piece(h, K), limb=h.limb)
            if k is not None:
                notes.append(Note(h.t, self.grid, int(k), _vel(h.vel)))
        return Clip._raw(sorted(notes), self.beats)

    @classmethod
    def from_clip(cls, clip, *, kit=None, grid: float | None = None, max_beats: float = 8.0) -> 'DrumMotif':
        """A motif from any Clip - a riff, a melody, a drum figure: its rhythm on a grid (16ths, or 8th-note
        triplets when the onsets sit there; grid= forces one), the loudest notes (>= 85 % of its top velocity) the
        accents, the softest (< 45 %) ghosts, the hands alternating by position (singles: accents fall on either
        hand); a drum Clip keeps its drums (the kit's voices) and kicks. At most max_beats long."""
        c = as_clip(clip)
        ns = sorted(c, key=lambda n: (n.start, -n.vel))
        if not ns:
            raise ComposeError("DrumMotif.from_clip: the clip has no notes")
        t0 = min(n.start for n in ns)
        if grid is None:
            def fits(g):
                return all(abs((n.start - t0) / g - round((n.start - t0) / g)) < 0.08 for n in ns)
            grid = 0.25 if fits(0.25) else 1 / 3 if fits(1 / 3) else 1 / 6 if fits(1 / 6) else 0.25
        g = _num(grid, 'DrumMotif.from_clip grid', 1 / 64, 4)
        L = min(max(c.length - t0, max(n.start for n in ns) - t0 + g), _num(max_beats, 'max_beats', 0.25))
        n_steps = max(1, int(round(L / g)))
        K = Kit.of(kit)
        voices = {K.key(v): i for i, v in enumerate(K.voices()) if K.key(v) is not None}
        kick = K.key('kick')
        top = max(n.vel for n in ns)
        by_step: dict = {}
        for n in ns:
            i = int(round((n.start - t0) / g))
            if 0 <= i < n_steps:
                by_step.setdefault(i, []).append(n)
        toks = []
        for i in range(n_steps):
            hand = 'R' if i % 2 == 0 else 'L'
            here = by_step.get(i)
            if not here:
                toks.append('-')
                continue
            parts = []
            if any(n.pitch == kick for n in here):
                parts.append('K')
            hn = [n for n in here if n.pitch != kick]
            if hn or not parts:
                n = max(hn or here, key=lambda n: n.vel)
                v = n.vel / top
                body = hand.lower() if v < 0.45 else hand
                tok = ('>' if v >= 0.85 else '') + body
                if n.pitch in voices and voices[n.pitch] > 0:
                    tok += f'@{voices[n.pitch]}'
                parts.insert(0, tok)
            toks.append('+'.join(parts))
        return cls(toks, g)

    def vary(self, how: str, *, kit=None, seed=0) -> 'DrumMotif':
        """The motif varied (MOTIF_VARIATIONS); kit: for the toms of 'orchestrate' / 'answer' / 'climb'."""
        if how not in MOTIF_VARIATIONS:
            raise ComposeError(f"DrumMotif.vary: {how!r} is not one of {', '.join(MOTIF_VARIATIONS)}")
        K = Kit.of(kit)
        rng = random.Random(seed_int(seed))
        toks = list(self.tokens)
        n = len(toks)
        g = self.grid
        toms = [f'tom{i + 1}' for i in range(len(K.toms))] or ['snare']

        def acc(t):
            return t.lstrip('fdz').startswith(('>', '^'))

        def strip_piece(t):
            return t.split('@')[0]
        if how == 'repeat':
            pass
        elif how == 'orchestrate':
            k = 0
            for i, t in enumerate(toks):
                if acc(t) and '+' not in t:
                    toks[i] = strip_piece(t) + '@' + toms[min(len(toms) - 1, k * len(toms) // max(1, sum(
                        1 for x in toks if acc(x))))]
                    k += 1
        elif how == 'climb':
            accs = [i for i, t in enumerate(toks) if acc(t) and '+' not in t]
            for k, i in enumerate(accs):
                j = len(toms) - 1 - min(len(toms) - 1, k * len(toms) // max(1, len(accs)))
                toks[i] = strip_piece(toks[i]) + ('@' + toms[j] if k < len(accs) - 1 else '')
        elif how == 'answer':
            half = n // 2
            k = 0
            accs = sum(1 for t in toks[half:] if t not in ('-', '.'))
            for i in range(half, n):
                t = toks[i]
                if t in ('-', '.') or '+' in t:
                    continue
                if t[-1] in 'rl' and '@' not in t:
                    t = t.upper() if rng.random() < 0.5 else t
                toks[i] = strip_piece(t) + '@' + toms[min(len(toms) - 1, k * len(toms) // max(1, accs))]
                k += 1
        elif how == 'displace':
            s = 2 if n >= 8 else 1
            toks = toks[-s:] + toks[:-s]
        elif how == 'flams':
            toks = [('f' + t) if acc(t) and not t.startswith('f') else t for t in toks]
        elif how == 'diminish':
            return DrumMotif(toks + toks, g / 2, self.name)
        elif how == 'augment':
            return DrumMotif(toks[:max(1, n // 2)], g * 2, self.name)
        elif how == 'fill':
            toks = [('r' if i % 2 == 0 else 'l') if t in ('-', '.') else t for i, t in enumerate(toks)]
        elif how == 'kick':
            for i, t in enumerate(toks):
                if t in ('r', 'l') and rng.random() < 0.55:
                    toks[i] = 'K'
                elif t in ('-', '.') and rng.random() < 0.3:
                    toks[i] = 'k'
        elif how == 'fragment':
            half = toks[:max(1, n // 2)]
            toks = (half + half)[:n]
        elif how == 'rimshots':
            toks = [t.replace('>', '^', 1) if acc(t) and '@' not in t else t for t in toks]
        elif how == 'invert':
            toks = [t.translate(str.maketrans('RLrl', 'LRlr')) for t in toks]
        elif how == 'sparse':
            toks = [('-' if t in ('r', 'l') else t) for t in toks]
        return DrumMotif(toks, g, self.name)


# ------------------------------------------------------------------------------------------------ solo moves

class SoloContext:
    """What a solo move gets: kit (Kit), bpm, beats (the move's length), energy and density (0..1, from the solo's
    arc), hands (Hands), motif (DrumMotif), rng / seed, bpb (beats per bar), feet (FEET) and opts (the step's own
    options: rudiment=, orchestrate=, variations= ...)."""

    def __init__(self, kit, bpm: float, beats: float, energy: float = 0.7, density: float = 0.5, hands=None,
                 motif: DrumMotif | None = None, seed=0, bpb: float = 4.0, feet: str = 'chick', opts=None):
        self.kit = Kit.of(kit)
        self.bpm = _bpm(bpm)
        self.beats = _num(beats, 'solo move beats', 0.25)
        self.energy = _num(energy, 'solo move energy', 0, 1)
        self.density = _num(density, 'solo move density', 0, 1)
        self.hands = _hands(hands)
        self.seed = seed
        self.rng = random.Random(seed_int(seed))
        self.motif = motif if motif is not None else DrumMotif.make(seed, density=self.density)
        self.bpb = _num(bpb, 'solo bpb', 1, 16)
        self.feet = feet
        self.opts = dict(opts or {})

    def pat(self, pattern, grid: float = 0.25, at: float = 0.0, *, energy=None, orchestrate=None, shape=None,
            group: int = 4, repeat: int = 1) -> list[Hit]:
        """strokes() in this context (its kit, hands, energy and seed)."""
        return strokes(pattern, grid=grid, at=at, kit=self.kit, energy=self.energy if energy is None else energy,
                       orchestrate=orchestrate, shape=shape, group=group, hands=self.hands,
                       seed=self.rng.randrange(1 << 30), repeat=repeat)

    @property
    def bars(self) -> int:
        return max(1, int(round(self.beats / self.bpb)))

    def steps(self, grid: float = 0.25) -> int:
        return int(round(self.beats / grid))


def _fit(toks: list[str], n: int) -> list[str]:
    """A token list repeated / cut to n steps."""
    if not toks:
        return ['-'] * n
    return (toks * (n // len(toks) + 1))[:n]


def _m_time(ctx: SoloContext) -> list[Hit]:
    """Time-keeping that dissolves: the groove (hat 8ths, backbeat, kick, ghosts) thins bar by bar - the hat to
    quarters, the backbeat moving, ghosts taking over - until only the snare's conversation and the hat foot are
    left (the band has dropped out, the drummer is on his own). opts crash=True: the first downbeat is a crash with
    the kick (the band's last hit)."""
    out = []
    n = ctx.bars
    for k in range(n):
        x = k / max(1, n - 1)                # 0 = the band's groove .. 1 = dissolved
        e = ctx.energy * (1.0 - 0.25 * x)
        toks = []
        for s in range(16):
            parts = []
            if x < 0.67:
                if s % 2 == 0 and (x < 0.34 or s % 4 == 0):
                    parts.append(('>' if s % 4 == 0 else '') + 'R@hat' + ('' if x < 0.34 else ''))
            elif s % 8 == 0:
                parts.append('R@ride')
            if s in (4, 12):
                parts.append('>L' if x < 0.5 or s == 4 else 'fL')
            elif s in (7, 15, 10) and ctx.rng.random() < 0.4 + 0.5 * x:
                parts.append('l')
            elif x > 0.5 and s % 2 == 1 and ctx.rng.random() < 0.3 + 0.4 * x * ctx.density:
                parts.append('l')
            if s == 0 or (s == 8 and x < 0.67) or (s == 10 and x < 0.34 and k % 2 == 1):
                parts.append('K')
            toks.append('+'.join(parts) if parts else '-')
        if k == 0 and ctx.opts.get('crash'):
            toks[0] = '>R@crash+K'
        out += ctx.pat(toks, 0.25, k * ctx.bpb, energy=e)
    return out


def _m_hat_dance(ctx: SoloContext) -> list[Hit]:
    """The hi-hat as a voice: 16ths on the hat, the openness changing stroke by stroke (closed / half / open), the
    foot closing the barks - the live-hat lane on kits that have one."""
    cells = ('x.o.x.h.x.o.xx.h', 'xxh.x.o.xxh.o.x.', 'x.h.o.x.xhx.o..x')
    op = ctx.opts.get('openings') or cells[ctx.rng.randrange(len(cells))]
    toks = []
    for i in range(ctx.steps(0.25)):
        c = op[i % len(op)]
        hand = 'R' if i % 2 == 0 else 'L'
        if c == '.':
            toks.append('k' if i % 8 == 6 and ctx.rng.random() < 0.5 else '-')
            continue
        piece = {'x': 'hat', 'h': 'hat_half', 'o': 'hat_open'}[c]
        toks.append(('>' if i % 4 == 0 or c == 'o' else '') + f'{hand}@{piece}' + ('+K' if i % 16 == 0 else ''))
    hs = ctx.pat(toks, 0.25)
    for h in [h for h in hs if h.piece == 'hat_open']:
        c = math.floor(h.t + 1.0 + _EPS)
        if c < ctx.beats and not any(abs(x.t - c) < _EPS and x.limb == 'LF' for x in hs):
            p = _h(c, 'hat_pedal', 40.0 + 20.0 * ctx.energy, 'LF', 'pedal')
            p.kind = 'T'
            hs.append(p)
    return hs


def _m_motif(ctx: SoloContext) -> list[Hit]:
    """The motif stated on the snare, repeated to fill the move; a repeat gets a light touch (filled ghosts or
    flams) so it is a phrase, not a loop."""
    m = ctx.motif
    out = []
    t = 0.0
    k = 0
    while t < ctx.beats - _EPS:
        mm = m if k == 0 else m.vary(('fill', 'flams', 'repeat')[ctx.rng.randrange(3)], kit=ctx.kit, seed=ctx.seed + k)
        n = min(len(mm.tokens), int(round((ctx.beats - t) / mm.grid)))
        if n <= 0:
            break
        out += ctx.pat(mm.tokens[:n], mm.grid, t, shape=(0.9, 1.0))
        t += n * mm.grid
        k += 1
    return out


def _m_develop(ctx: SoloContext) -> list[Hit]:
    """The motif developed bar by bar: each statement a new variation of the last (opts variations=[...], else a
    seeded path: orchestrate -> answer -> displace / diminish / flams ...), the dynamics growing."""
    path = ctx.opts.get('variations')
    if path is None:
        pool = ['answer', 'displace', 'flams', 'diminish', 'kick', 'climb', 'rimshots', 'fill']
        ctx.rng.shuffle(pool)
        path = ['orchestrate'] + pool
    m = ctx.motif
    out = []
    t = 0.0
    k = 0
    while t < ctx.beats - _EPS:
        how = path[k % len(path)]
        m = m.vary(how, kit=ctx.kit, seed=ctx.seed + 7 * k)
        if how in ('diminish', 'augment'):
            m2 = m
            m = ctx.motif.vary('orchestrate', kit=ctx.kit, seed=ctx.seed)   # keep developing from a bar's length
        else:
            m2 = m
        n = min(len(m2.tokens), int(round((ctx.beats - t) / m2.grid)))
        if n <= 0:
            break
        x = t / ctx.beats
        out += ctx.pat(m2.tokens[:n], m2.grid, t, energy=min(1.0, ctx.energy * (0.92 + 0.12 * x)))
        t += n * m2.grid
        k += 1
    return out


_RUDIMENT_SPOTS = (('paradiddle', 'split'), ('flam_accent', 'accents'), ('six_stroke_roll', 'down'),
                   ('swiss_army_triplet', 'down'), ('double_paradiddle', 'around'), ('paradiddle_diddle', 'down'),
                   ('flam_tap', 'down'), ('inverted_paradiddle', 'split'), ('single_ratamacue', 'accents'),
                   ('flam_paradiddle', 'accents'), ('pataflafla', 'hands'), ('lesson_25', 'accents'))
"""Rudiments a solo plays around the kit, with the orchestration that makes them talk."""


def _m_rudiment(ctx: SoloContext) -> list[Hit]:
    """A rudiment orchestrated around the kit (opts rudiment=, orchestrate=, grid=; else a seeded one from
    _RUDIMENT_SPOTS - paradiddles split between floor tom and snare, flam accents on the toms, six-stroke rolls
    down the kit ...), crescendo; at a tempo the hands cannot play its grid it falls back to the next slower grid."""
    name = ctx.opts.get('rudiment')
    orch = ctx.opts.get('orchestrate')
    if name is None:
        name, o = _RUDIMENT_SPOTS[ctx.rng.randrange(len(_RUDIMENT_SPOTS))]
        orch = orch or o
    if name not in RUDIMENTS:
        raise ComposeError(f"solo move 'rudiment': unknown rudiment {name!r}; RUDIMENTS: {', '.join(RUDIMENTS)}")
    pat, g = RUDIMENTS[name]
    g = ctx.opts.get('grid', g)
    toks = _tokens(pat)
    for _ in range(4):
        n = int(round(ctx.beats / g))
        hs = ctx.pat(_fit(toks, n), g, orchestrate=orch, shape=ctx.opts.get('shape', 'cresc'), group=len(toks))
        if not sticking_problems(hs, ctx.bpm, ctx.hands):
            return hs
        g *= 2.0
    raise ComposeError(f"solo move 'rudiment' {name!r}: the hands cannot play it at {ctx.bpm:g} BPM")


def _m_flam_toms(ctx: SoloContext) -> list[Hit]:
    """Flams across the toms: flam accents (triplets) or flam taps (16ths) walking down the kit, a group per
    drum, the last drum's flams the loudest."""
    name = ctx.opts.get('rudiment') or ('flam_accent' if ctx.rng.random() < 0.5 else 'flam_tap')
    pat, g = RUDIMENTS[name]
    toks = _tokens(pat)
    n = int(round(ctx.beats / g))
    return ctx.pat(_fit(toks, n), g, orchestrate='down', group=len(toks), shape='cresc')


_TOM_MELODIES = ((1, 1, 2, 3, None, 2, 3, 4), (4, 3, 4, 2, None, 1, 2, 1), (1, 2, 1, 3, 2, 4, None, 4),
                 (2, 2, 1, None, 3, 3, 4, None), (1, 3, 2, 4, 3, None, 4, 4))
"""Tom melodies (voice numbers: 1 = the highest tom .. the floor; None = a rest), 8 notes."""


def _m_tom_melody(ctx: SoloContext) -> list[Hit]:
    """The toms as a melody: a short tune over the toms (high -> low = pitch), CALLED on the snare first and
    ANSWERED on the toms, the answer's dynamics from humanize.touch (the toms as pitches: a melody's phrase arc,
    the highest tom the goal), the snare call with ghosts between. opts melody=(voices ...) (1 = tom1 ..)."""
    from .humanize import touch
    nt = len(ctx.kit.toms)
    mel = ctx.opts.get('melody') or _TOM_MELODIES[ctx.rng.randrange(len(_TOM_MELODIES))]
    mel = [None if v is None else max(1, min(nt, int(v))) if nt else 0 for v in mel]
    grid = 0.5 if ctx.bpm < 150 else 1.0
    half = ctx.beats / 2.0
    out = []
    # the call: the melody's rhythm on the snare (accents where the tune moves down), ghosts between
    n = int(round(half / grid))
    call = []
    for i in range(n):
        v = mel[i % len(mel)]
        hand = 'R' if i % 2 == 0 else 'L'
        call.append('-' if v is None else ('>' if i % 4 == 0 else '') + hand)
    sub = []
    for t in call:                                  # 16ths: the note, then a ghost of the other hand
        sub.append(t)
        sub.append(('l' if t.endswith('R') else 'r') if t != '-' and ctx.rng.random() < 0.6 * ctx.density + 0.2
                   else '-')
    out += ctx.pat(sub, grid / 2, 0.0, energy=ctx.energy * 0.9)
    # the answer on the toms, phrased like a melody (touch)
    notes = []
    for i in range(int(round(half / grid))):
        v = mel[i % len(mel)]
        if v is None:
            continue
        notes.append(Note(i * grid, grid, 60 - 3 * v, 90))
    shaped = touch(Clip._raw(notes, half), 70 + 25 * ctx.energy, 96 + 26 * ctx.energy, gap=grid * 1.5, pitch=1.2)
    for k, nn in enumerate(shaped):
        v = (60 - nn.pitch) // 3
        piece = f'tom{v}' if nt else 'snare'
        h = _h(half + nn.start, piece, nn.vel, 'R' if k % 2 == 0 else 'L', 'fill', dur=grid)
        h.kind = 'A' if nn.vel >= 100 else 'T'
        out.append(h)
        if grid >= 0.5 and ctx.rng.random() < 0.35 + 0.4 * ctx.density and nn.start + grid / 2 < half:
            g = _h(half + nn.start + grid / 2, piece, nn.vel * 0.55, 'L' if k % 2 == 0 else 'R', 'fill', dur=grid / 2)
            g.kind = 'T'
            out.append(g)
    return out


def _m_call_response(ctx: SoloContext) -> list[Hit]:
    """Call and response between the snare and the toms: a two-beat call on the snare, answered on the toms in
    the same rhythm (descending), the next call a little louder and busier."""
    calls = (['>R', 'l', 'r', '>L', '-', 'l', '>R', '-'], ['>R', '-', 'l', '>R', 'l', 'r', '>L', 'r'],
             ['f>R', 'l', '-', '>R', '-', 'l', '>L', 'l'])
    call = calls[ctx.rng.randrange(len(calls))]
    nt = max(1, len(ctx.kit.toms))
    out = []
    t = 0.0
    k = 0
    while t < ctx.beats - _EPS:
        e = min(1.0, ctx.energy * (0.85 + 0.08 * k))
        span = min(4.0, ctx.beats - t)               # a short slot: the call and its answer share it
        n = max(1, int(round(span / 2.0 / 0.25)))
        c = call[:n]
        out += ctx.pat(c, 0.25, t, energy=e)
        resp = []
        j = 0
        for tok in c:
            if tok == '-' or tok.islower():
                resp.append('-' if tok == '-' else tok)
                continue
            resp.append(tok + f'@tom{min(nt, 1 + j * nt // 4)}')
            j += 1
        out += ctx.pat(resp, 0.25, t + n * 0.25, energy=min(1.0, e * 1.05))
        t += 4.0
        k += 1
    return [h for h in out if h.t < ctx.beats - _EPS]


def _m_three_over_four(ctx: SoloContext) -> list[Hit]:
    """3 over 4: accents every three 16ths (dotted 8ths) walking around the toms and a crash over a bed of 16th
    ghosts on the snare, the feet keeping the quarters - the bar line seems to move until the figure lands on 1."""
    n = ctx.steps(0.25)
    nt = max(1, len(ctx.kit.toms))
    toks = []
    k = 0
    for i in range(n):
        hand = 'R' if i % 2 == 0 else 'L'
        if i % 3 == 0:
            piece = f'tom{k % nt + 1}' if ctx.kit.toms else 'snare'
            if k % 8 == 7:
                piece = 'crash'
            toks.append(f'>{hand}@{piece}')
            k += 1
        else:
            toks.append(hand.lower())
    return ctx.pat(toks, 0.25, shape='cresc')


def _m_fives(ctx: SoloContext) -> list[Hit]:
    """Five-groupings: 16ths in groups of five (R L R L K: hands down the toms, the kick closing each group) that
    run across the bar line - 4 bars of 16ths hold 12 fives and a 4-note tail into the 1."""
    n = ctx.steps(0.25)
    nt = max(1, len(ctx.kit.toms))
    group = ['>R', 'L', 'R', 'L', 'K']
    toks = []
    g = 0
    for i in range(n):
        j = i % 5
        if n - i <= n % 5 and n % 5:
            toks.append(('>R@crash+K' if i == n - (n % 5) else ('R' if i % 2 == 0 else 'L') + '@floor'))
            continue
        tok = group[j]
        if j < 4:
            v = (g + (1 if j >= 2 else 0)) % (nt + 1)
            tok += '' if v == 0 else f'@tom{v}'
        toks.append(tok)
        if j == 4:
            g += 1
    return ctx.pat(toks, 0.25, shape='cresc')


def _m_quintuplets(ctx: SoloContext) -> list[Hit]:
    """Quintuplets: five strokes per beat, singles, the accent on each group's first note walking around the
    toms, ghosts between - the rhythm stretches against the quarter-note feet."""
    g = 0.2
    if sticking_problems(strokes(['R', 'L'] * 4, grid=g, kit=ctx.kit), ctx.bpm, ctx.hands):
        g = 0.4
    n = int(round(ctx.beats / g))
    nt = max(1, len(ctx.kit.toms))
    toks = []
    for i in range(n):
        hand = 'R' if i % 2 == 0 else 'L'
        if i % 5 == 0:
            v = (i // 5) % (nt + 1)
            toks.append(f'>{hand}' + ('' if v == 0 else f'@tom{v}'))
        else:
            toks.append(hand.lower() if i % 5 in (1, 3) else hand)
    return ctx.pat(toks, g, shape='cresc')


def _m_half_double(ctx: SoloContext) -> list[Hit]:
    """Half-time into double-time: the first half a heavy half-time groove (kick 1, snare 3, ride 8ths, ghosts),
    the second half the same pulse doubled (snare on every '&', kick on every beat, the hat 16ths)."""
    out = []
    n = max(1, int(round(ctx.beats / 4.0)))
    nh = (n + 1) // 2                     # the half-time bars (the larger half), then the double-time bars
    half = nh * 4.0
    for b0 in range(nh):
        toks = []
        for s in range(16):
            p = []
            if s % 2 == 0:
                p.append(('>' if s % 4 == 0 else '') + 'R@ride')
            if s == 8:
                p.append('^L')
            elif s in (3, 11, 14) and ctx.rng.random() < 0.6:
                p.append('l')
            if s in (0, 6, 10) and (s == 0 or ctx.rng.random() < 0.7):
                p.append('K')
            toks.append('+'.join(p) or '-')
        out += ctx.pat(toks, 0.25, b0 * 4.0, energy=ctx.energy * 0.9)
    for b0 in range(n - nh):
        toks = []
        for s in range(16):
            p = ['R@hat' if s % 2 == 1 else '>R@hat'] if s % 4 != 2 else []
            if s % 4 == 2:
                p.append('^L')
            elif s % 2 == 1 and ctx.rng.random() < 0.25:
                p.append('l')
            if s % 4 == 0:
                p.append('K')
            toks.append('+'.join(p) or '-')
        out += ctx.pat(toks, 0.25, half + b0 * 4.0, energy=min(1.0, ctx.energy * 1.05))
    return out


_LINEAR = (['R', 'L', 'K'], ['R', 'L', 'L', 'K'], ['R', 'L', 'R', 'K', 'K'], ['R', 'R', 'L', 'K'],
           ['R', 'L', 'K', 'K'])


def _m_linear(ctx: SoloContext) -> list[Hit]:
    """Linear phrases: no two limbs ever together - hands and kick in figures of 3, 4 and 5 (R L K, R L L K,
    R L R K K ...) that ripple across the beat, the hands walking around the toms, the accents on each figure's
    first stroke."""
    n = ctx.steps(0.25)
    nt = max(1, len(ctx.kit.toms))
    toks = []
    k = 0
    while len(toks) < n:
        fig = _LINEAR[ctx.rng.randrange(len(_LINEAR))]
        v = k % (nt + 1)
        for j, c in enumerate(fig):
            if c == 'K':
                toks.append('K')
            else:
                toks.append(('>' if j == 0 else '') + c + ('' if v == 0 else f'@tom{v}'))
        k += 1
    return ctx.pat(toks[:n], 0.25, shape='wave')


def _m_bonham(ctx: SoloContext) -> list[Hit]:
    """Hand-hand-foot triplets (a Bonham-style figure, original pattern): 16th-note triplets R L K, the hands on a
    tom pair that moves down the kit every beat, the right hand accented, crescendo into the floor tom."""
    g = 1 / 6
    if sticking_problems(strokes(['R', 'L', 'K'] * 4, grid=g, kit=ctx.kit), ctx.bpm, ctx.hands):
        g = 1 / 3
    n = int(round(ctx.beats / g))
    nt = max(1, len(ctx.kit.toms))
    toks = []
    for i in range(n):
        beat = int(i * g + 1e-6)
        j = i % 3
        tr = 1 + min(nt - 1, beat * nt // max(1, int(ctx.beats)))
        tl = min(nt, tr + (1 if ctx.rng.random() < 0.3 else 0))
        toks.append({0: f'>R@tom{tr}', 1: f'L@tom{tl}', 2: 'K'}[j] if ctx.kit.toms else {0: '>R', 1: 'L', 2: 'K'}[j])
    return ctx.pat(toks, g, shape='build')


def _m_speed_burst(ctx: SoloContext) -> list[Hit]:
    """A single-stroke speed burst (Buddy-Rich style): the fastest singles the hands can play at this tempo (16th
    sextuplets or 32nds), crescendo on the snare with a few accents, the last beat flying down the toms into an
    accented hit."""
    for g in (1 / 12, 1 / 8, 1 / 6, 0.25):
        if not sticking_problems(strokes(['R', 'L'] * 6, grid=g, kit=ctx.kit), ctx.bpm, ctx.hands):
            break
    n = int(round(ctx.beats / g))
    tail = int(round(1.0 / g))
    nt = len(ctx.kit.toms)
    toks = []
    for i in range(n):
        hand = 'R' if i % 2 == 0 else 'L'
        acc = '>' if i % int(round(1 / g)) == 0 else ''
        if i >= n - tail and nt:
            v = 1 + min(nt - 1, (i - (n - tail)) * nt // tail)
            toks.append(acc + hand + f'@tom{v}')
        else:
            toks.append(acc + hand)
    toks[-1] = '>' + toks[-1].lstrip('>')
    return ctx.pat(toks, g, shape='build')


def _m_buzz(ctx: SoloContext) -> list[Hit]:
    """A press (buzz) roll from a whisper to a roar: multiple-bounce strokes in 16ths (8ths at fast tempos), the
    hands' bounces closing the gaps, into an accent with the kick."""
    g = 0.25 if _beats_ms(0.25, ctx.bpm) >= 90 else 0.5
    n = int(round(ctx.beats / g))
    toks = [('zR' if i % 2 == 0 else 'zL') for i in range(n - 1)] + ['^R+K']
    return ctx.pat(toks, g, shape=(0.35, 1.05))


def _m_double_bass(ctx: SoloContext) -> list[Hit]:
    """Double bass: 16ths on the kick, both feet (a double pedal), the hands on top - crash / tom unisons on the
    beats, snare accents on 2 and 4, a tom run in the last beat."""
    g = 0.25 if _beats_ms(0.5, ctx.bpm) >= ctx.hands.foot_ms else 0.5
    n = int(round(ctx.beats / g))
    feet_t = ['K' if i % 2 == 0 else 'P@kick' for i in range(n)]
    per = int(round(1 / g))
    nt = max(1, len(ctx.kit.toms))
    hands = []
    for i in range(n):
        beat, sub = divmod(i, per)
        last = beat >= int(ctx.beats) - 1
        if last and ctx.kit.toms:
            hands.append(('R' if i % 2 == 0 else 'L') + f'@tom{1 + min(nt - 1, sub * nt // per)}')
        elif sub == 0 and beat % 4 == 0:
            hands.append('>R@crash' if beat % 8 == 0 else '>R@china')
        elif sub == 0 and beat % 2 == 1:
            hands.append('^L')
        elif sub == 0:
            hands.append('>R@tom1' if ctx.kit.toms else '>R')
        else:
            hands.append('-')
    return ctx.pat(feet_t, g, shape='build') + ctx.pat(hands, g, shape='build')


def _m_gated_toms(ctx: SoloContext) -> list[Hit]:
    """The 80s gated tom break (an original figure in that spirit, not the famous one): big tom 16ths grouped
    3 + 3 + 2 down the rack toms with flams on the group starts, then 16th triplets rolling down the floor toms,
    the kick under every downbeat, a flam on the floor into the next 1. Send the toms to a gated reverb for its
    length (Performance.moves logs it: 'gated_toms')."""
    nt = max(1, len(ctx.kit.toms))
    t1, t2 = 'tom1', f'tom{min(nt, 2)}'
    t3, t4 = f'tom{min(nt, 3)}', f'tom{nt}'
    bar1 = [f'f>R@{t1}+K', f'L@{t1}', f'R@{t1}', f'f>L@{t2}', f'R@{t2}', f'L@{t2}', f'>R@{t3}', f'L@{t3}',
            f'f>R@{t1}+K', f'L@{t1}', f'R@{t2}', f'f>L@{t2}', f'R@{t3}', f'L@{t3}', f'>R@{t4}', '-']
    out = []
    t = 0.0
    k = 0
    while t < ctx.beats - _EPS:
        if k % 2 == 0:
            out += ctx.pat(bar1, 0.25, t, shape=(0.85, 1.0))
        else:
            trip = []
            for i in range(12):
                hand = 'R' if i % 2 == 0 else 'L'
                v = [t2, t3, t3, t4][i // 3]
                trip.append(('>' if i % 3 == 0 else '') + hand + f'@{v}' + ('+K' if i % 3 == 0 else ''))
            out += ctx.pat(trip, 1 / 3, t, shape=(0.88, 1.05))
        t += 4.0
        k += 1
    return [h for h in out if h.t < ctx.beats - _EPS]


def _m_silence(ctx: SoloContext) -> list[Hit]:
    """A dramatic silence: the drummer stops (opts breath=True: one soft ghost note into the gap)."""
    if ctx.opts.get('breath'):
        return ctx.pat(['-'] * (ctx.steps(0.25) - 1) + ['l'], 0.25)
    return []


def _m_swell(ctx: SoloContext) -> list[Hit]:
    """A cymbal swell: a roll on the crash (or opts piece='ride') from a whisper into the next downbeat (on a
    mallet kit track: soft mallets)."""
    piece = ctx.opts.get('piece', 'crash')
    g = 0.125 if _beats_ms(0.25, ctx.bpm) >= 2 * ctx.hands.single_ms else 0.25
    n = int(round(ctx.beats / g))
    toks = ['>' + ('R' if i % 2 == 0 else 'L') + f'@{piece}' for i in range(n)]
    return ctx.pat(toks, g, shape=lambda x: 0.22 + 0.76 * x ** 1.6)


def _m_finish(ctx: SoloContext) -> list[Hit]:
    """The big finish and the cue back into the band: unison hits (crash + kick, toms + kick) on a rhythm the band
    can hear coming, a dramatic gap, then a fast single-stroke run around the whole kit (16th triplets, snare ->
    floor) into the next downbeat - the band's 1. opts choke=True grabs the last hit's crash (a hit and choke);
    motif=True puts the hits on the motif's accents (the riff's rhythm: the band hears its cue coming)."""
    out = []
    L = ctx.beats
    nt = len(ctx.kit.toms)
    run = min(2.0, L / 2.0)
    head = L - run
    hits_at = [0.0, 0.75, 1.5] if head >= 2.0 else [0.0]
    if ctx.opts.get('motif'):
        m = ctx.motif
        acc = [i * m.grid for i, t in enumerate(m.tokens) if t.lstrip('fdz').startswith(('>', '^'))]
        hits_at = [t for t in acc if t <= head - 1.0 + _EPS] or [0.0]
    for i, t in enumerate(hits_at):
        piece = 'crash' if i % 2 == 0 else ('crash2' if ctx.kit.has('crash2') else 'china')
        out += ctx.pat([f'>R@{piece}+L@floor+K' if nt else f'>R@{piece}+L+K'], 0.25, t, energy=min(1.0, ctx.energy))
    if ctx.opts.get('choke') and ctx.kit.has('crash_choke'):
        c = _h(hits_at[-1] + 0.5, 'crash_choke', 90.0, 'R', 'hit')
        c.kind = 'T'
        out.append(c)
    g = 1 / 6
    if sticking_problems(strokes(['R', 'L'] * 6, grid=g, kit=ctx.kit), ctx.bpm, ctx.hands):
        g = 0.25
    n = int(round(run / g))
    toks = []
    vs = ctx.kit.voices()
    for i in range(n):
        v = vs[min(len(vs) - 1, i * len(vs) // n)]
        toks.append(('>' if i % 3 == 0 else '') + ('R' if i % 2 == 0 else 'L') + f'@{v}')
    out += ctx.pat(toks, g, head, energy=min(1.0, ctx.energy), shape='build')
    return out


def _m_hit_choke(ctx: SoloContext) -> list[Hit]:
    """A hit and choke: crash + kick (+ the snare), the hand grabbing the cymbal a beat later - then silence for
    the rest of the move (a dramatic stop)."""
    piece = ctx.opts.get('piece', 'crash')
    hs = ctx.pat([f'>R@{piece}+^L+K'], 0.25)
    if ctx.kit.has(_CHOKES.get(piece, 'crash_choke')):
        c = _h(min(1.0, ctx.beats - 0.25), _CHOKES.get(piece, 'crash_choke'), 95.0, 'R', 'hit')
        c.kind = 'T'
        hs.append(c)
    return hs


SOLO_MOVES: dict[str, dict] = {
    'time': dict(fn=_m_time, feet=False, spice=False, energy=0.5, density=0.5, beats=16),
    'hat_dance': dict(fn=_m_hat_dance, feet=False, spice=False, energy=0.5, density=0.6, beats=8),
    'motif': dict(fn=_m_motif, feet='chick', spice=False, energy=0.5, density=0.4, beats=8),
    'develop': dict(fn=_m_develop, feet='chick', spice=False, energy=0.6, density=0.5, beats=16),
    'rudiment': dict(fn=_m_rudiment, feet='chick', spice=False, energy=0.65, density=0.6, beats=8),
    'flam_toms': dict(fn=_m_flam_toms, feet='four', spice=True, energy=0.7, density=0.6, beats=4),
    'tom_melody': dict(fn=_m_tom_melody, feet='chick', spice=False, energy=0.6, density=0.5, beats=8),
    'call_response': dict(fn=_m_call_response, feet='chick', spice=False, energy=0.6, density=0.5, beats=8),
    'three_over_four': dict(fn=_m_three_over_four, feet='four', spice=True, energy=0.7, density=0.7, beats=8),
    'fives': dict(fn=_m_fives, feet=False, spice=True, energy=0.75, density=0.8, beats=8),
    'quintuplets': dict(fn=_m_quintuplets, feet='chick4', spice=True, energy=0.75, density=0.8, beats=4),
    'half_double': dict(fn=_m_half_double, feet='chick', spice=False, energy=0.7, density=0.6, beats=16),
    'linear': dict(fn=_m_linear, feet=False, spice=True, energy=0.75, density=0.8, beats=8),
    'bonham': dict(fn=_m_bonham, feet=False, spice=True, energy=0.85, density=0.9, beats=4),
    'speed_burst': dict(fn=_m_speed_burst, feet='four', spice=True, energy=0.9, density=1.0, beats=4),
    'buzz': dict(fn=_m_buzz, feet='chick', spice=False, energy=0.8, density=0.7, beats=4),
    'double_bass': dict(fn=_m_double_bass, feet=False, spice=True, energy=0.95, density=1.0, beats=8),
    'gated_toms': dict(fn=_m_gated_toms, feet=False, spice=True, energy=0.9, density=0.9, beats=8),
    'silence': dict(fn=_m_silence, feet=False, spice=False, energy=0.0, density=0.0, beats=4),
    'swell': dict(fn=_m_swell, feet=False, spice=False, energy=0.7, density=0.5, beats=4),
    'finish': dict(fn=_m_finish, feet=False, spice=False, energy=1.0, density=1.0, beats=8),
    'hit_choke': dict(fn=_m_hit_choke, feet=False, spice=False, energy=0.95, density=0.2, beats=4),
}
"""The solo vocabulary: name -> fn(SoloContext) -> Hits (from beat 0), feet (the ostinato the feet keep under it:
FEET, False = the move plays its own feet), spice (a showpiece the solo should not repeat often: polyrhythms,
speed bursts, the gated break, double bass), energy / density (where it sits in a solo's arc), beats (its natural
length). Each move's docstring says what it plays. perform(steps) plays them in a given order; soloist.solo() picks
and orders them from drummer.vocabulary()."""


# ------------------------------------------------------------------------------------------------ perform

def _step(item, bpb: float) -> dict:
    if isinstance(item, dict):
        d = dict(item)
        if 'move' not in d:
            raise ComposeError(f"drummer.perform step {item!r}: needs 'move'")
    elif isinstance(item, (list, tuple)) and 2 <= len(item) <= 4:
        d = {'move': item[0], 'bars': item[1]}
        if len(item) >= 3:
            d['energy'] = item[2]
        if len(item) == 4:
            if not isinstance(item[3], dict):
                raise ComposeError(f"drummer.perform step {item!r}: the 4th item is the move's opts dict")
            d.update(item[3])
    else:
        raise ComposeError(f"drummer.perform: a step is (move, bars[, energy[, opts]]) or a dict, got {item!r}")
    if d['move'] not in SOLO_MOVES:
        raise ComposeError(f"drummer.perform: unknown solo move {d['move']!r}; SOLO_MOVES: {', '.join(SOLO_MOVES)}")
    if 'beats' not in d:
        d['beats'] = _num(d.get('bars', SOLO_MOVES[d['move']]['beats'] / bpb), 'perform step bars', 0.25) * bpb
    return d


def perform(steps, *, bpm, kit=None, at=0.0, hands=None, seed=0, motif: DrumMotif | None = None,
            feet: str | None = None, bpb: float = 4.0) -> Performance:
    """A drum solo (or any drum passage) played as an ORDERED list of solo moves (SOLO_MOVES) -> Performance (.clip
    from `at`, .hits, .moves: (start, end, 'solo', name), .lanes: the live-hat openness, .play(track)).

    steps: (move, bars[, energy[, opts]]) or {'move': .., 'bars': .., 'energy': .., 'density': .., 'feet': ..,
    + the move's opts (rudiment=, orchestrate=, variations=, melody=, choke=, piece= ...)}. energy (0..1) sets the
    passage's top level (42 .. 126: a whisper .. fff) - give the solo an arc (start soft, build, climax), never one level. One
    DrumMotif (motif=, else grown from the seed) runs through the moves that state / develop it. feet: the
    ostinato under the moves that leave the feet free (FEET; default each move's own). The hands' physics
    (perform_hits) play every stroke; limbs never collide (resolve); .warnings lists strokes the kit has no piece
    for and passages the hands could not play. The ordering is yours (or soloist.solo()'s: the arc, motif
    development and budgets live there)."""
    b = _bpm(bpm)
    K = Kit.of(kit)
    H = _hands(hands)
    B = _num(bpb, 'perform bpb', 1, 16)
    a = _pos(at)
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ComposeError("drummer.perform: steps must be a non-empty list of (move, bars[, energy[, opts]])")
    m = motif if motif is not None else DrumMotif.make(seed)
    if not isinstance(m, DrumMotif):
        raise ComposeError(f"drummer.perform motif must be a DrumMotif, got {m!r}")
    hits: list[Hit] = []
    moves = []
    plan = []
    warns: list[str] = []
    t = 0.0
    for i, item in enumerate(steps):
        d = _step(item, B)
        spec = SOLO_MOVES[d['move']]
        opts = {k: v for k, v in d.items() if k not in ('move', 'bars', 'beats', 'energy', 'density', 'feet')}
        e = d.get('energy', spec['energy'])
        ft = d.get('feet', feet if feet is not None else spec['feet'])
        ctx = SoloContext(K, b, d['beats'], energy=e, density=d.get('density', spec['density']), hands=H, motif=m,
                          seed=seed_int(seed) * 131 + i, bpb=B, feet=ft or 'none', opts=opts)
        hs = spec['fn'](ctx)
        if ft and spec['feet'] is not False:
            hs += _feet(ft, 0.0, ctx.beats, ctx.energy, B, b, H)
        probs = sticking_problems(hs, b, H)
        if probs:
            warns.append(f"{d['move']} at beat {a + t:g}: {probs[0]}")
        perform_hits(hs, b, hands=H, seed=seed_int(seed) * 7 + i, energy=ctx.energy, kit=K)
        for h in hs:
            h.t += t
            h.bar = None
        hits += hs
        moves.append((a + t, a + t + ctx.beats, 'solo', d['move']))
        plan.append(dict(move=d['move'], start=a + t, beats=ctx.beats, energy=round(ctx.energy, 3),
                         density=round(ctx.density, 3), feet=ctx.feet,
                         **{k: v for k, v in opts.items() if isinstance(v, (str, int, float, bool))}))
        t += ctx.beats
    hits = [h for h in hits if h.t < t - _EPS]
    hits, dropped = _resolve(hits, b)
    clip = _to_clip(hits, K, b, t)
    perf = Performance(clip, a, hits, moves, plan, {'limb_conflicts_resolved': dropped}, K, b)
    perf.warnings = missing_pieces(hits, K) + warns
    return perf


def solo_move(name: str, beats, bpm, *, kit=None, energy: float | None = None, density: float | None = None,
              hands=None, motif: DrumMotif | None = None, feet: str | None = None, seed=0, at=0.0, **opts) -> Clip:
    """One solo move (SOLO_MOVES) as a Clip of `beats` beats from `at` - e.g. solo_move('gated_toms', 8, 112,
    kit=kit) or solo_move('rudiment', 4, 112, rudiment='paradiddle', orchestrate='split')."""
    step = {'move': name, 'beats': _num(beats, 'solo_move beats', 0.25)}
    for k, v in (('energy', energy), ('density', density), ('feet', feet)):
        if v is not None:
            step[k] = v
    step.update(opts)
    p = perform([step], bpm=bpm, kit=kit, hands=hands, seed=seed, motif=motif)
    a = _pos(at)
    return Clip._raw([n._replace(start=n.start + a) for n in p.clip], a + p.clip.length)


# ------------------------------------------------------------------------------------------------ the soloist's vocabulary

SOLO_ROLES = {
    'time': ('resolve', 'fill'), 'hat_dance': ('answer', 'fill'), 'motif': ('motif',),
    'develop': ('develop', 'answer', 'climax'), 'rudiment': ('develop', 'fill'), 'flam_toms': ('develop', 'burst'),
    'tom_melody': ('answer', 'develop'), 'call_response': ('answer',), 'three_over_four': ('develop', 'burst'),
    'fives': ('develop', 'burst'), 'quintuplets': ('develop', 'burst'), 'half_double': ('develop', 'climax'),
    'linear': ('burst', 'develop'), 'bonham': ('burst', 'climax'), 'speed_burst': ('burst', 'climax'),
    'buzz': ('climax', 'burst'), 'double_bass': ('climax', 'burst'), 'gated_toms': ('climax', 'burst'),
    'swell': ('resolve', 'fill'), 'finish': ('climax', 'resolve'), 'hit_choke': ('resolve',),
}
"""Where each solo move fits in soloist.solo()'s arc (soloist.ROLES). 'silence' is no move there: the soloist plans
its rests itself."""

_MIN_BEATS = {'gated_toms': 4.0, 'finish': 4.0, 'half_double': 8.0, 'three_over_four': 4.0, 'tom_melody': 2.0,
              'call_response': 2.0, 'double_bass': 4.0, 'time': 8.0, 'hat_dance': 2.0, 'buzz': 2.0, 'bonham': 2.0,
              'speed_burst': 2.0}
_FAST = ('speed_burst', 'buzz')
_MAX_BEATS = {'speed_burst': 4.0, 'buzz': 4.0, 'quintuplets': 4.0, 'flam_toms': 4.0, 'bonham': 4.0, 'linear': 4.0,
              'swell': 4.0, 'hit_choke': 4.0, 'finish': 8.0}
_AT_END = ('speed_burst', 'buzz', 'swell', 'finish')
_WEIGHTS = {'finish': 0.4, 'hit_choke': 0.4, 'motif': 1.2, 'tom_melody': 1.2, 'call_response': 1.1}
"""How readily the soloist picks a move: the finish is a once-per-solo cue, the motif's development the backbone."""


def _motif_of(x, kit) -> DrumMotif:
    """A DrumMotif from a DrumMotif, a token string / list, or any Clip (the rhythm of a melody, a riff, a drum
    part)."""
    if isinstance(x, DrumMotif):
        return x
    if isinstance(x, (str, list, tuple)) and (isinstance(x, str) or all(isinstance(t, str) for t in x)):
        return DrumMotif(x)
    return DrumMotif.from_clip(x, kit=kit)


def _part_of(name: str, ctx, K: Kit, H: Hands, opts: dict, feet: str | None):
    """Play one solo move in a soloist slot -> soloist.Part (the clip played by the hands, the hat-openness lane as
    'steps', the move in the log)."""
    from . import soloist
    spec = SOLO_MOVES[name]
    slot = float(ctx.beats)
    # a showpiece plays at most its natural length in a long slot: the bursts / rolls / swells lead INTO the next
    # phrase (they sit at the slot's end), the other short figures start it - the rest of the slot is space
    cap = _MAX_BEATS.get(name)
    beats = min(slot, cap) if cap else slot
    t0 = slot - beats if name in _AT_END else 0.0
    mot = _motif_of(ctx.motif, K) if getattr(ctx, 'motif', None) is not None else None
    seed = ctx.rng.randrange(1 << 30)
    sc = SoloContext(K, ctx.bpm, beats, energy=ctx.energy, density=ctx.density, hands=H, motif=mot, seed=seed,
                     bpb=getattr(ctx, 'bpb', 4.0), feet=feet or 'none', opts=opts)
    hs = spec['fn'](sc)
    ft = feet if feet is not None else spec['feet']
    if ft and spec['feet'] is not False:
        hs += _feet(ft, 0.0, beats, sc.energy, sc.bpb, sc.bpm, H)
    perform_hits(hs, sc.bpm, hands=H, seed=seed, energy=sc.energy, kit=K)
    hs = [h for h in hs if h.t < beats - _EPS]
    hs, _ = _resolve(hs, sc.bpm)
    for h in hs:
        h.t += t0
    clip = _to_clip(hs, K, sc.bpm, slot)
    lane = hat_lane(hs, K, sc.bpm)
    steps = {'instrument.dynamics': [(p[0], p[1]) for p in lane]} if lane else None
    return soloist.Part(clip, log=[(t0, t0 + beats, 'solo', name)], steps=steps)


def vocabulary(kit=None, *, hands=None, moves=None, feet: str | None = None, opts: dict | None = None,
               budget=None):
    """The drummer's solo vocabulary for soloist.solo() (the instrument-agnostic solo wrapper: the arc, the motif's
    development, the spice budget): one soloist.Move per SOLO_MOVES entry (its roles SOLO_ROLES, energy, density,
    spice; speed_burst and the press roll are 'fast'), each played by the hands' physics (Hands) on `kit` (Kit.of:
    the track you will place it on), feet= the ostinato under the moves that leave the feet free (default each
    move's own), opts={move: {...}} the moves' options (rudiment=, orchestrate=, melody= ...), moves= a subset of
    names. The motif: any Clip (the riff, the hook - its rhythm and accents become the DrumMotif) or a DrumMotif;
    without one, DrumMotif.make. vary(): the stage's MOTIF_VARIATIONS. place(): the notes + the hi-hat openness lane
    + the hat foot on 2 and 4 through the space between phrases (a drummer's pulse never stops), the track's own
    humanize off. touch=False (the drummer shapes its own dynamics); rest=0.4 (less planned space than a horn).

        perf = soloist.solo(s, kit, drummer.vocabulary(kit, hands='master'), at=solo, motif=riff, seed=7)"""
    from . import soloist
    K = Kit.of(kit)
    H = _hands(hands)
    names = list(moves) if moves is not None else [n for n in SOLO_MOVES if n in SOLO_ROLES]
    for n in names:
        if n not in SOLO_ROLES:
            raise ComposeError(f"drummer.vocabulary: {n!r} is no soloist move; moves: {', '.join(SOLO_ROLES)}")
    opts = dict(opts or {})
    for n in opts:
        if n not in SOLO_MOVES:
            raise ComposeError(f"drummer.vocabulary opts: unknown move {n!r}")
    if feet is not None and feet not in FEET:
        raise ComposeError(f"drummer.vocabulary feet must be one of {', '.join(FEET)}, got {feet!r}")
    out = []
    for n in names:
        spec = SOLO_MOVES[n]
        fast = n in _FAST
        out.append(soloist.Move(n, _MIN_BEATS.get(n, 0.0), spec['energy'], spec['density'], spec['spice'] or fast,
                                (lambda ctx, n=n: _part_of(n, ctx, K, H, opts.get(n, {}), feet)), fast=fast,
                                roles=SOLO_ROLES[n], weight=_WEIGHTS.get(n, 1.0)))

    def motif(ctx):
        return DrumMotif.make(ctx.rng.randrange(1 << 30), density=ctx.density).to_clip(K)

    _STAGE_VARY = {'statement': ('repeat', 'fill', 'sparse'), 'answer': ('answer', 'fragment', 'displace'),
                   'develop': ('orchestrate', 'flams', 'displace', 'climb', 'kick'),
                   'burst': ('diminish', 'fill', 'kick'), 'climax': ('orchestrate', 'rimshots', 'flams'),
                   'resolve': ('sparse', 'augment', 'repeat'), 'trade': ('answer', 'displace', 'flams')}

    def vary(m, ctx):
        dm = _motif_of(m, K)
        pool = _STAGE_VARY.get(getattr(ctx, 'stage', ''), MOTIF_VARIATIONS)
        return dm.vary(pool[ctx.rng.randrange(len(pool))], kit=K, seed=ctx.rng.randrange(1 << 30)).to_clip(K)

    def place(track, perf):
        track.humanize(0, 0)
        clip = perf.clip
        # the space between phrases is not silence for a drummer: the hat foot keeps 2 and 4 through it
        foot = K.key('hat_pedal')
        if foot is not None and len(clip):
            bpb = getattr(perf, 'bpb', 4.0)
            starts = sorted(n.start for n in clip)
            extra = []
            rng = random.Random(seed_int(f"{perf.start:.4f}:feet"))
            for k in range(1, int(clip.length // 1) + 1):
                t = float(k)
                if int(round(t)) % int(bpb) not in (1, 3) or t >= clip.length - _EPS:
                    continue
                if any(abs(x - t) < 1.0 - _EPS for x in starts):
                    continue
                extra.append(Note(t + rng.uniform(-0.008, 0.008), 0.25, int(foot), _vel(44 + rng.uniform(-5, 5))))
            if extra:
                clip = Clip._raw(sorted(list(clip) + extra), clip.length)
        track.play(clip, perf.start)
        lane = sorted(perf.steps().get('instrument.dynamics', []))
        if lane:
            track.automate('instrument.dynamics', [(t, v, 'step') for t, v in lane])

    return soloist.Vocabulary(out, motif=motif, vary=vary, name=f'drummer ({K.name})', place=place,
                              vel=(20, 127), phrase_bars=2, touch=False, budget=budget, range=(35, 59), rest=0.4)


MOVES = {
    'beat': beat, 'tom_run': tom_run, 'snare_run': snare_run, 'triplet_fill': triplet_fill, 'flam_fill': flam_fill,
    'linear_fill': linear_fill, 'pickup': pickup, 'roll': roll, 'build': build, 'stop': stop, 'dropout': dropout,
    'swell': swell, 'crash_hit': crash_hit, 'open_hat': open_hat, 'count_in': count_in, 'brushes': brushes,
    'ride': ride, 'pattern': pattern, 'rudiment': rudiment, 'feet': feet, 'double_bass': double_bass, 'choke': choke,
    'hat_dance': hat_dance, 'solo_move': solo_move,
}
"""Every drum move by name -> its function (each returns a Clip from `at`, keyed for the kit, velocities shaped, a
few ms of seeded timing; call it on its own or let arrange() choose)."""
