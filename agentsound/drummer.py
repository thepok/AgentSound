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
from .theory import ComposeError

__all__ = ['Kit', 'KITS', 'STYLES', 'ROLES', 'TIMEKEEPERS', 'MODES', 'FILL_KINDS', 'FLASHY', 'MOVES', 'Memory',
           'Performance', 'Hit',
           'arrange', 'beat', 'check', 'tom_run', 'snare_run', 'triplet_fill', 'flam_fill', 'linear_fill', 'pickup',
           'roll', 'build', 'stop', 'dropout', 'swell', 'crash_hit', 'open_hat', 'count_in', 'brushes', 'ride']

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
    'swirly': dict(kick=36, snare=38, edge=40, hat=42, hat_pedal=44, hat_open=46, ride=51, crash=49, crash2=57,
                   china=53, splash=55, toms=(48, 47, 45, 43, 41), brush=SWIRLY_BRUSH),
    'gm_brush': dict(kick=36, snare=38, side=37, hat=42, hat_pedal=44, hat_open=46, ride=51, bell=53, crash=49,
                     crash2=57, splash=55, toms=(48, 45, 43, 41), brush=GM_BRUSH),
}
"""Named kit maps: piece -> GM key (toms high -> low). 'gm' is the General MIDI map (every GM / SoundFont kit, the
engine's drum machine, kits built by inst.kit()); the Karoryfer kits have extra pieces (rimshot, snare edge, hat
shank) on their own keys; the brush kits carry the patterns.brushes keymap as 'brush'."""

_STIR = {'swirly': (1.9, 0.8)}
"""Brush-kit levelling (stir, tap) velocity factors - bandlib.jazz.brushes' values for the Swirly kit."""

_FALLBACK = {'rimshot': ('snare',), 'edge': ('snare',), 'hat_shank': ('hat',), 'hat_splash': ('hat_open',),
             'hat_open': ('hat',), 'bell': ('ride',), 'ride_crash': ('crash',), 'crash2': ('crash',),
             'china': ('crash2', 'crash'), 'splash': ('crash2', 'crash'), 'crash': ('crash2', 'ride', 'hat_open'),
             'kick2': ('kick',), 'clap': ('snare',)}
_PIECES = ('kick', 'kick2', 'snare', 'side', 'rimshot', 'edge', 'clap', 'hat', 'hat_shank', 'hat_pedal', 'hat_open',
           'hat_splash', 'ride', 'bell', 'ride_crash', 'crash', 'crash2', 'china', 'splash', 'tamb', 'cowbell')
_MAIN_PIECES = ('kick', 'snare', 'hat', 'hat_open', 'ride', 'crash')
"""The pieces that keep their key when another piece's key only copies the same samples."""


class Kit:
    """Which pieces a kit has and on which keys. Kit.of(x): x = a Track / Instrument / Patch (a sampled kit is read:
    only keys with samples count, tom copies are merged, Big Rusty / Unruly / Swirly are recognised by their files),
    a KITS name, a dict {piece: key} (with 'toms': (high .. low)) or None (General MIDI, every piece).
    key(piece) -> the key or None (after the fallbacks: no rimshot -> snare, no bell -> ride, no crash2 -> crash
    ...); toms -> the distinct toms high -> low; has(piece)."""

    def __init__(self, name: str, pieces: dict, toms=(), brush: dict | None = None):
        self.name = name
        self.pieces = dict(pieces)
        self.toms = tuple(toms)
        self.brush = brush

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
        pieces = {p: k for p, k in m.items() if p not in ('toms', 'brush') and (avail is None or k in avail)}
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
        return cls(name, pieces, toms, m.get('brush'))

    @classmethod
    def _custom(cls, d: dict) -> 'Kit':
        pieces, toms = {}, ()
        for p, k in d.items():
            if p == 'toms':
                toms = tuple(_key_num(t, 'toms') for t in (k if isinstance(k, (list, tuple)) else [k]))
            elif p == 'brush':
                continue
            elif p not in _PIECES and p != 'floor':
                raise ComposeError(f"drummer kit: unknown piece {p!r}; pieces: {', '.join(_PIECES)}, toms, brush")
            else:
                pieces[p] = _key_num(k, p)
        if 'floor' in pieces:
            toms = toms + (pieces.pop('floor'),)
        return cls('custom', pieces, toms, d.get('brush'))

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
            name = ('big_rusty' if 'big-rusty' in blob else 'unruly' if 'unruly' in blob
                    else 'swirly' if 'swirly' in blob else 'gm')
            same = {k: frozenset(v) for k, v in files.items()}
            return cls._named(name, avail=set(files), same=same)
        if ins.type == 'drums':          # the engine's drum machine
            return cls._named('gm', avail={35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 54,
                                           56, 57, 59})
        if ins.type == 'sf2' and ins.params.get('bank') == 128 and ins.params.get('program') == 40:
            return cls._named('gm_brush')
        return cls._named('gm')

    def has(self, piece: str) -> bool:
        return self.key(piece, fallback=False) is not None

    def key(self, piece: str, fallback: bool = True) -> int | None:
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

    def tom(self, i: int, n: int) -> str:
        """The i-th of n drums of a run across the toms (high -> low) as a piece name."""
        if not self.toms:
            return 'snare'
        j = min(len(self.toms) - 1, i * len(self.toms) // max(1, n))
        return f'tom{j + 1}'

    def __repr__(self) -> str:
        ps = ', '.join(f"{p}={k}" for p, k in self.pieces.items())
        return f"Kit({self.name!r}: {ps}; toms {list(self.toms)}{'; brushes' if self.brush else ''})"


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
        if not h.piece.startswith('#') and kit.key(h.piece, fallback=False) is None:
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

    __slots__ = ('t', 'piece', 'vel', 'limb', 'tag', 'prio', 'dur', 'main', 'off', 'bar')

    def __init__(self, t, piece, vel, limb, tag, prio=5, dur=0.25, main=None, bar=0):
        self.t, self.piece, self.vel, self.limb, self.tag = float(t), piece, float(vel), limb, tag
        self.prio, self.dur, self.main, self.off, self.bar = prio, dur, main, 0.0, bar

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
            out.append(_h(t0 + s * q, piece, _lvl('open' if tag == 'open' else 'hat', e, soft) * f, 'R', tag, dur))
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


def _to_clip(hits: list[Hit], kit: Kit, bpm: float, length: float, start_min: float = 0.0) -> Clip:
    notes = []
    for h in hits:
        if h.piece.startswith('#'):
            key = int(h.piece[1:])
        else:
            key = kit.key(h.piece)
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
        return track.play(self.clip, self.start)

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


def _budget(cands: list[dict], memory: Memory | None, base: float, bpb: float, fill_every: float, flashy_every: float,
            same_every: float) -> tuple[list[dict], list]:
    """Keep fill candidates: structural ones (into a section) always, the others at least fill_every bars from any
    kept fill (and from memory's). Returns (kept, refused)."""
    booked = [t for t, _, _ in memory.fills] if memory is not None else []
    kept, refused = [], []
    for c in sorted(cands, key=lambda c: (-c['score'], c['t'])):
        T = base + c['t']
        if c['structural'] or all(abs(T - t) >= fill_every * bpb - _EPS for t in booked):
            kept.append(c)
            booked.append(T)
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
            lock_mode: str = 'with', memory: Memory | None = None, at=None) -> Performance:
    """A drummer plays a song form -> Performance (.clip from .start, .hits, .moves, .plan, .budget, .summary(),
    .play(track)).

    form: a Song (all its sections; bpm = its tempo), a Section, a list of consecutive Sections or of (name, bars)
    pairs (from beat 0). Every section gets a ROLE (from its name, or plan=) with an energy: the verse calmer
    (hi-hat, the calm kick cells, ghosts), the pre-chorus rising (open hats, a BUILD into the chorus: 8ths -> 16ths
    -> 32nds on the snare), the chorus bigger (ride or 16ths, busier kick, rimshots, a crash every 8 bars), the
    bridge a variation (a floor-tom groove, half-time, the ride bell), a break a STOP (the band hit, silence, time on
    the hat), the end a big hit and a roll into the final cut-off (ending='hit' | 'roll' | 'groove'). A section's
    groove is a main cell with a variation in its 4th bar, repeated sections reuse it.
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
    Deterministic by seed."""
    if style not in STYLES:
        raise ComposeError(f"drummer style must be one of {', '.join(STYLES)}, got {style!r}")
    secs_in, abs_start, tempo = _parse_form(form)
    b = _bpm(bpm if bpm is not None else tempo if tempo is not None else None)
    dens = _num(density, 'drummer density', 0, 1)
    fe = _num(fill_every, 'drummer fill_every (bars)', 0)
    xe = _num(flashy_every, 'drummer flashy_every (bars)', 0)
    se = _num(same_every, 'drummer same_every (bars)', 0)
    ce = _num(crash_every, 'drummer crash_every (bars)', 0)
    if ending not in (None, 'hit', 'roll', 'groove'):
        raise ComposeError(f"drummer ending must be 'hit', 'roll', 'groove' or None, got {ending!r}")
    if memory is not None and not isinstance(memory, Memory):
        raise ComposeError(f"drummer memory must be a drummer.Memory(), got {memory!r}")
    rng = random.Random(seed_int(seed))
    K = Kit.of(kit)
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
    if end_mode in ('hit', 'roll'):
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
    kept, refused = _budget(cands, memory, base, bar_len, fe, xe, se)

    # ---- choose fill kinds (structural first) under the flashy budget, place them
    booked_flashy = [(t, k) for t, k, f in (memory.fills if memory is not None else []) if f]
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
                ok = xe > 0 and all(abs(T - t) >= xe * bar_len - _EPS for t, _ in booked_flashy) and \
                    all(abs(T - t) >= se * bar_len - _EPS for t, k_ in booked_flashy if k_ == kind)
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
                booked_flashy.append((T, kind))
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
        hs = _big_hit(t, ctx, e_end) if not quiet_end or end_mode == 'hit' else []
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
        hs = sorted(hs, key=when)
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
    hands = sorted((h for h in hits if h.limb in ('R', 'L') and h.tag != 'grace'), key=lambda h: h.t)
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


MOVES = {
    'beat': beat, 'tom_run': tom_run, 'snare_run': snare_run, 'triplet_fill': triplet_fill, 'flam_fill': flam_fill,
    'linear_fill': linear_fill, 'pickup': pickup, 'roll': roll, 'build': build, 'stop': stop, 'dropout': dropout,
    'swell': swell, 'crash_hit': crash_hit, 'open_hat': open_hat, 'count_in': count_in, 'brushes': brushes,
    'ride': ride,
}
"""Every drum move by name -> its function (each returns a Clip from `at`, keyed for the kit, velocities shaped, a
few ms of seeded timing; call it on its own or let arrange() choose)."""
