"""Band presets: one call sets up a complete, mixed ensemble on a Song - instruments, placement, eq, return buses,
sends, sidechains, the master chain and the analysis profile - so a song starts from a finished sound, not from
empty tracks.

    from agentsound import bands
    b = bands.make('outrun', s)                 # or bands.outrun(s)
    b.lead.play(hook, at=chorus)                # role -> Track
    b['pad'].loop(pads, verse, chorus)
    ANALYSIS = b.analysis                       # {'profile': 'synthwave', ...}: the profile the preset is tuned for
    print(b.describe())

    python -m agentsound bands [genre]          # the presets: name, genre, roles, what they are tuned against

Every preset builder takes (song, *, without=(), sounds=None, ids=None, **options):
  without  roles to leave out, e.g. without=('arp', 'keys')
  sounds   {role: sound} replaces a role's sound (a patch name, inst.*(...), a Patch) and keeps its mix chain
  ids      {role: track id} renames tracks (default: the role name)
Levels: a role's track gain_db is the preset's level for it (rock / pop keep it at 0 and the balance in a last
'trim' effect); 'gainDb' automation and modulation are dB on the track's gain_db, so
`b.bass.automate('gainDb', [(0, 0), (solo.start, 2, 'smooth'), ...])` means "the preset's level, +2 dB in the solo".

The presets live in agentsound/bandlib/*.py (one file per genre family) and register themselves here.
"""

from __future__ import annotations

import builtins
import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Callable

from .theory import ComposeError


class Band:
    """What a preset built on a song: role -> Track, the return buses, the master chain it set, the analysis
    profile it is tuned for and notes on how to play it (register, density, levels)."""

    def __init__(self, song, preset: str, notes: str = '', analysis: dict | None = None):
        self.song = song
        self.preset = preset
        self.notes = notes
        self.analysis: dict = dict(analysis or {})
        self.roles: dict = {}
        self.buses: dict = {}
        self.info: dict = {}          # anything else a preset wants to hand over (keyswitch names, feel, ...)

    def add(self, role: str, track):
        if role in self.roles:
            raise ComposeError(f"band {self.preset!r}: role {role!r} added twice")
        self.roles[role] = track
        return track

    def bus(self, name: str, bus):
        self.buses[name] = bus
        return bus

    def __getitem__(self, role: str):
        if role in self.roles:
            return self.roles[role]
        if role in self.buses:
            return self.buses[role]
        raise ComposeError(f"band {self.preset!r} has no role {role!r}; roles: {', '.join(self.roles) or '-'}"
                           f"; buses: {', '.join(self.buses) or '-'}")

    def __getattr__(self, name: str):
        if name.startswith('_') or name in ('song', 'preset', 'notes', 'analysis', 'roles', 'buses', 'info'):
            raise AttributeError(name)
        return self[name]

    def __contains__(self, role: str) -> bool:
        return role in self.roles or role in self.buses

    def describe(self) -> str:
        lines = [f"band {self.preset}: {len(self.roles)} roles, {len(self.buses)} buses"
                 + (f", analysis {self.analysis}" if self.analysis else '')]
        for role, t in self.roles.items():
            snd = getattr(t, 'instrument', None)
            kind = getattr(snd, 'type', '?') if snd is not None else '?'
            lines.append(f"  {role:<10} track {t.id!r} ({kind})")
        for name, b in self.buses.items():
            lines.append(f"  {name:<10} bus {getattr(b, 'id', name)!r}")
        if self.notes:
            lines.append('  ' + self.notes.strip().replace('\n', '\n  '))
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return f"Band({self.preset!r}: {', '.join(self.roles)})"


@dataclass
class Preset:
    name: str
    genre: str
    build: Callable
    roles: tuple
    description: str = ''
    tuned: str = ''                 # what it is calibrated against (reference track / profile), for the listing
    requires: tuple = field(default_factory=tuple)   # sample pack ids it needs (the listing shows missing ones)


_REGISTRY: dict[str, Preset] = {}
_LOADED = False


def register(name: str, build: Callable, *, genre: str, roles, description: str = '', tuned: str = '',
             requires=()) -> Preset:
    """Register a preset builder (called by the bandlib modules at import)."""
    if name in _REGISTRY:
        raise ComposeError(f"band preset {name!r} registered twice")
    p = Preset(name, genre, build, tuple(roles), description, tuned, tuple(requires))
    _REGISTRY[name] = p
    return p


def _load() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    from . import bandlib
    for m in pkgutil.iter_modules(bandlib.__path__):
        if not m.name.startswith('_'):
            importlib.import_module(f'{bandlib.__name__}.{m.name}')


def list(genre: str | None = None) -> builtins.list[str]:  # noqa: A001 - bands.list() like patches.list()
    _load()
    return sorted(n for n, p in _REGISTRY.items() if genre is None or p.genre == genre)


def get(name: str) -> Preset:
    _load()
    if name not in _REGISTRY:
        import difflib
        close = difflib.get_close_matches(name, _REGISTRY, n=3)
        raise ComposeError(f"no band preset {name!r}" + (f"; did you mean {', '.join(close)}?" if close else '')
                           + f" (python -m agentsound bands lists {len(_REGISTRY)})")
    return _REGISTRY[name]


def make(name: str, song, **options) -> Band:
    """Build preset `name` on `song` (see the module docstring for the common options)."""
    p = get(name)
    without = set(options.get('without') or ())
    unknown = without - set(p.roles)
    if unknown:
        raise ComposeError(f"band {name!r}: without= names unknown roles {sorted(unknown)}; roles: {', '.join(p.roles)}")
    for key in ('sounds', 'ids'):
        bad = set((options.get(key) or {})) - set(p.roles)
        if bad:
            raise ComposeError(f"band {name!r}: {key}= names unknown roles {sorted(bad)}; roles: {', '.join(p.roles)}")
    band = p.build(song, **options)
    if not isinstance(band, Band):
        raise ComposeError(f"band preset {name!r} did not return a Band")
    return band


def describe_all(genre: str | None = None) -> str:
    from . import library
    lines = []
    for n in list(genre):
        p = _REGISTRY[n]
        missing = [r for r in p.requires if not (library.SAMPLES / r / 'SOURCE.json').is_file()]
        lines.append(f"{n:<22} {p.genre:<10} roles: {', '.join(p.roles)}")
        if p.description:
            lines.append(f"{'':<22} {p.description}")
        if p.tuned:
            lines.append(f"{'':<22} tuned: {p.tuned}")
        if missing:
            lines.append(f"{'':<22} needs packs: {', '.join(missing)} (python -m agentsound samples fetch ...)")
    return '\n'.join(lines) if lines else 'no band presets registered'


def __getattr__(name: str):
    """bands.outrun(song, ...) == bands.make('outrun', song, ...)."""
    if name.startswith('_'):
        raise AttributeError(name)
    _load()
    if name in _REGISTRY:
        return lambda song, **kw: make(name, song, **kw)
    raise AttributeError(f"module 'agentsound.bands' has no attribute {name!r} (band presets: {', '.join(list())})")
