"""The players' logs of a song: run its song.py with the players' placements recorded.

Every player returns an object with a move log (`.moves`: (start, end, kind, name), beats relative to the placed
clip): pianist.Arrangement, drummer.Performance, bassist.BassLine, guitarist.Arrangement, hornist.Performance. They
are placed with their own play() / place() (or hero_guitar.play) or with track.play(obj.clip / arr.rh, at). This
module records each placement -> {'player', 'track', 'at' (beat), 'moves'} while the song file builds; nothing in
the song or the players changes (the patches are undone afterwards)."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

PLAYER_CLASSES = (
    # (module, class, player name, the attributes holding clips it places)
    ('pianist', 'Arrangement', 'pianist', ('rh',)),
    ('drummer', 'Performance', 'drummer', ('clip',)),
    ('bassist', 'BassLine', 'bassist', ('clip',)),
    ('guitarist', 'Arrangement', 'guitarist', ('clip',)),
    ('hornist', 'Performance', 'hornist', ('clip',)),
)

_PLAYER_FILES = ('pianist.py', 'drummer.py', 'bassist.py', 'guitarist.py', 'hornist.py', 'hero_guitar.py',
                 'heroes.py', 'jazz.py')
_PLACERS = ('play', 'place', 'lead')          # the functions / methods that place a player's part


def _classes():
    import importlib
    out = []
    for mod, cls, name, attrs in PLAYER_CLASSES:
        m = importlib.import_module(f'agentsound.{mod}')
        out.append((getattr(m, cls), name, attrs))
    return out


@contextlib.contextmanager
def recording():
    """with recording() as log: ... build the song ... -> log: [{'player', 'track', 'at', 'moves'}]."""
    from ..song import Track
    classes = _classes()
    log: list[dict] = []
    keep: list = []                      # keep owners alive so their clip ids stay unique
    owner_of: dict[int, tuple] = {}      # id(clip) -> (owner, player, clip)
    seen: set = set()
    placed: set = set()                  # id(owner) of the objects already placed somewhere
    undo: list = []

    def sig(clip, n=None):
        try:
            notes = list(clip)
        except TypeError:
            return set()
        notes = notes if n is None else notes[:n]
        try:
            return {(round(x.start, 3), x.pitch) for x in notes}
        except AttributeError:
            return set()

    def player_of(obj):
        for cls, name, _ in classes:
            if isinstance(obj, cls):
                return name
        return None

    def record(owner, player, track, at):
        moves = getattr(owner, 'moves', None)
        if not moves:
            return
        key = (id(owner), track.id, round(float(at), 6))
        if key in seen:
            return
        seen.add(key)
        placed.add(id(owner))
        log.append({'player': player, 'track': track.id, 'at': round(float(at), 6),
                    'moves': [[round(float(a), 6), round(float(b), 6), str(k), str(n)] for a, b, k, n in moves]})

    # 1. every player object registers the clips it hands out
    for cls, name, attrs in classes:
        orig_init = cls.__init__

        def init(self, *a, __orig=orig_init, __name=name, __attrs=attrs, **kw):
            __orig(self, *a, **kw)
            keep.append(self)
            for at_ in __attrs:
                c = getattr(self, at_, None)
                if c is not None:
                    owner_of[id(c)] = (self, __name, c)   # the clip itself too: ids of freed clips are reused
        cls.__init__ = init
        undo.append((cls, '__init__', orig_init))

    # 2. Track.play: a registered clip, or a player object in a player module's frame up the stack
    orig_play = Track.play

    def play(self, what, at=0.0, *a, **kw):
        res = orig_play(self, what, at, *a, **kw)
        try:
            start = self._song._at(at)
        except Exception:                # noqa: BLE001 - the original call already validated it
            return res
        hit = owner_of.get(id(what))
        if hit is not None and hit[2] is what:
            record(hit[0], hit[1], self, start)
            return res
        f = sys._getframe(1)
        for _ in range(6):
            if f is None:
                break
            if Path(f.f_code.co_filename).name in _PLAYER_FILES and f.f_code.co_name in _PLACERS:
                for v in (f.f_locals.get('self'), f.f_locals.get('part')):
                    p = player_of(v)
                    if p is not None:
                        record(v, p, self, start)
                        return res
            f = f.f_back
        # 3. a transformed clip (sliced, re-voiced, filtered): the most recent unplaced player object whose notes it
        # mostly shares (start, pitch)
        probe = sig(what, 16)
        if probe:
            for owner in reversed(keep):
                if id(owner) in placed:
                    continue
                name = player_of(owner)
                attrs = next(a_ for _, n_, a_ in classes if n_ == name)
                ref = set().union(*(sig(getattr(owner, x, None) or ()) for x in attrs))
                if ref and len(probe & ref) >= 0.6 * len(probe):
                    record(owner, name, self, start)
                    break
        return res
    Track.play = play
    undo.append((Track, 'play', orig_play))
    try:
        yield log
    finally:
        for obj, name, orig in reversed(undo):
            setattr(obj, name, orig)


def capture(song_py: Path) -> tuple[object, list[dict]]:
    """Build the song file with the players recorded -> (Song, log)."""
    from ..cli import load_song
    with recording() as log:
        song = load_song(Path(song_py))
    return song, log


# Moves worth a label on screen (point-like events); the rest (grooves, devices, patterns, approach notes) are
# counted but not popped.
POP_KINDS = {
    'pianist': {'ornament', 'fill'},
    'drummer': {'fill', 'crash', 'build', 'stop', 'ending'},
    'bassist': {'fill', 'move', 'ending'},
    'guitarist': {'ornament', 'fill', 'move'},
    'hornist': {'air', 'pitch', 'mic', 'fill', 'move', 'ornament'},
}


def absolute_moves(log: list[dict]) -> list[dict]:
    """Every logged move at its song beat: [{'player', 'track', 'beat', 'end', 'kind', 'name'}], sorted."""
    out = []
    for e in log:
        for a, b, k, n in e['moves']:
            out.append({'player': e['player'], 'track': e['track'], 'beat': round(e['at'] + a, 6),
                        'end': round(e['at'] + b, 6), 'kind': k, 'name': n})
    out.sort(key=lambda m: (m['beat'], m['player'], m['kind']))
    return out


def counts(moves: list[dict]) -> dict:
    """{player: {'kind:name': n}} over the absolute moves."""
    out: dict = {}
    for m in moves:
        d = out.setdefault(m['player'], {})
        k = f"{m['kind']}:{m['name']}"
        d[k] = d.get(k, 0) + 1
    return {p: dict(sorted(d.items(), key=lambda kv: -kv[1])) for p, d in out.items()}
