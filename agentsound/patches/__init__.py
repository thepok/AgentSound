"""Patches: named, reusable sounds and the registry the sound library fills.

A Patch bundles an instrument (type + params), an insert fx chain and mix defaults:

    Patch('synthwave/supersaw_lead',
          instrument={'type': 'va', 'params': {'unison': 7, 'cutoff': 3200}},
          fx=[fx.chorus(mix=0.3), fx.delay(mix=0.2)],
          gain_db=-4, pan=0, sends={'hall': -14},
          notes='Wide detuned lead; play legato lines in C5-C6.')

Songs use them by name and tweak copies:

    lead = song.track('lead', patches.get('synthwave/supersaw_lead').but(cutoff=2500))
    lead = song.track('lead', 'synthwave/supersaw_lead')          # same as patches.get(...)

Param names are the engine's (see `python -m agentsound params`); dotted names such as
'filter.cutoff' are passed straight through: .but(**{'filter.cutoff': 900}) or .but(filter__cutoff=900)
('__' in a keyword becomes '.').

The va's modulation matrix is its one structured param, 'mods' (routes built with agentsound.vamod):
inst.va(mods=[vamod.lfo('sine', hz=5.5, id='vib') >> ('pitch', 15)]); patch.with_mods(route, ...) adds routes
(same id: replaced), patch.but(**{'mod.vib.amount': 25}) changes one route's amount.

Layered sounds: inst.stack(layer('sampled/piano_lead'), layer('synthwave/dx_bells', transpose=12, level=-10)) plays
several instruments on one track (key / velocity ranges and crossfades, transpose, fine, delay, per-layer fx);
Patch.layered(name, *layers, ...) makes a patch of it, .but(**{'layers.<id>.<param>': v}) / .layer(id, ...) tweak a
layer (agentsound/patches/layered.py is the library of layered leads and keys).

Patches without an instrument are fx chains for buses / the master: song.bus('hall', patches.get('bus/hall')).
Conventional prefixes: 'bus/...' (return/group chains), 'master/...' (master chains).

The library lives in agentsound/patches/*.py (or sub-packages): each module calls register(Patch(...))
at import time. Modules are imported lazily on the first get()/list().
"""

from __future__ import annotations

import builtins
import copy
import difflib
import importlib
import math
import os
import pkgutil
import re
import sys

from .. import vamod as _vamod
from ..theory import ComposeError

__all__ = ['Patch', 'Instrument', 'FX', 'Layer', 'LAYER_KEYS', 'fx', 'inst', 'layer', 'register', 'get', 'has', 'list',
           'describe', 'load_library']


# ------------------------------------------------------------------------------- param helpers

def _key(k: str) -> str:
    return k.replace('__', '.')


def _check_value(k: str, v, where: str):
    if k == 'mods':  # the va modulation matrix: routes (vamod) or routing dicts -> the render JSON list
        return _vamod.normalize_mods(v, f"{where}: 'mods'")
    if isinstance(v, bool) or isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        if not math.isfinite(v):
            raise ComposeError(f"{where}: param {k!r} = {v!r} is not finite")
        return v
    raise ComposeError(f"{where}: param {k!r} = {v!r} must be a number, bool or string (enum choice)")


# Params whose value is structured JSON (a dict / list) instead of a number, bool or string.
_STRUCTURED = frozenset({'samples', 'ir'})


def _check_json(k: str, v, where: str):
    """Deep copy of a JSON-compatible value (dicts with string keys, lists, numbers, strings, bools)."""
    if isinstance(v, dict):
        if not all(isinstance(x, str) for x in v):
            raise ComposeError(f"{where}: param {k!r}: dict keys must be strings, got {v!r}")
        return {x: _check_json(k, y, where) for x, y in v.items()}
    if isinstance(v, (builtins.list, tuple)):  # (`list` is this module's patches.list())
        return [_check_json(k, y, where) for y in v]
    if isinstance(v, os.PathLike):
        return os.fspath(v)
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, (int, float)):
        if not math.isfinite(v):
            raise ComposeError(f"{where}: param {k!r} contains {v!r}, which is not finite")
        return v
    raise ComposeError(f"{where}: param {k!r} contains {v!r}; only dicts, lists, numbers, strings and bools are allowed")


def _param(k: str, v, where: str):
    return _check_json(k, v, where) if _key(k) in _STRUCTURED else _check_value(k, v, where)


def _fx_paths(params: dict, where: str) -> dict:
    """File params of effects ('ir' of the convolver: a WAV path or a list of them): 'samples/<pack>/...' becomes
    absolute in the sample library ($AGENTSOUND_SAMPLES, else assets/samples: git worktrees share one download),
    './' and '../' are relative to the song file, other paths stay relative to assets/ (the engine resolves them)
    or absolute."""
    if 'ir' in params:
        v = params['ir']
        many = isinstance(v, builtins.list)
        if not (isinstance(v, str) or (many and len(v) in (1, 2, 4) and all(isinstance(x, str) for x in v))):
            raise ComposeError(f"{where}: 'ir' must be an impulse-response WAV path or a list of 2 or 4 paths (one IR: "
                               f"[left, right] or [left-input, right-input] or [LL, LR, RL, RR]), got {v!r}")
        caller = None
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the agentsound package
        frame = sys._getframe(1)
        while frame is not None and caller is None:  # the song: the first caller outside the package
            f = frame.f_globals.get('__file__')
            if f and not os.path.abspath(f).startswith(here + os.sep):
                caller = f
            frame = frame.f_back
        out = []
        for path in (v if many else [v]):
            out.append(_sample_path(path, caller, where))   # 'samples/...' stays symbolic until to_dict()
        params['ir'] = out if many else out[0]
    return params


def _library_path(text: str) -> str:
    """'samples/<pack>/...' -> absolute path in the sample library ($AGENTSOUND_SAMPLES, else assets/samples)."""
    if text.startswith('samples/'):
        from ..library import SAMPLES
        return (SAMPLES / text[len('samples/'):]).as_posix()
    return text


def _params(params, kw, where: str) -> dict:
    out: dict = {}
    if params is not None:
        if not isinstance(params, dict):
            raise ComposeError(f"{where}: params must be a dict, got {params!r}")
        for k, v in params.items():
            if not isinstance(k, str) or not k:
                raise ComposeError(f"{where}: param names must be non-empty strings, got {k!r}")
            out[_key(k)] = _param(k, v, where)
    for k, v in kw.items():
        out[_key(k)] = _param(k, v, where)
    return out


def _ref(x) -> str:
    """Node reference -> id string (accepts Track/Bus objects or ids)."""
    r = getattr(x, 'id', x)
    if not isinstance(r, str):
        raise ComposeError(f"expected a track/bus or its id, got {x!r}")
    return r


# --------------------------------------------------------------------------- instrument / fx

class Instrument:
    """An instrument descriptor: type ('va', 'dx7', 'drums', ...) + params. Build with inst.va(...).
    `info` (not part of the render JSON): what inst.sfz found in the file (unsupported opcodes, articulation, ...);
    Song.compile() turns it into warnings. `lazy`: an inst.sfz(..., lazy=True) instrument whose zones are read from
    the .sfz when the render JSON is built (library patches: a missing sample pack is an error at use, not at import)."""

    __slots__ = ('type', 'params', 'info', 'lazy')

    def __init__(self, type: str, params: dict | None = None, /, **kw):
        if not isinstance(type, str) or not re.match(r'^[a-z0-9_]+$', type):
            raise ComposeError(f"instrument type must be a lowercase name like 'va', 'dx7', 'drums'; got {type!r}")
        self.type = type
        layers = None
        if type == 'stack':   # the layers are structured (Layer objects), the other stack params plain
            params = dict(params or {})
            kw = dict(kw)
            given = [x for x in (params.pop('layers', None), kw.pop('layers', None)) if x is not None]
            if len(given) != 1:
                raise ComposeError("instrument 'stack' needs layers=[layer(...), ...] (exactly once); build it with "
                                   "inst.stack(layer('sampled/piano_lead'), layer('synthwave/dx_bells', transpose=12))")
            layers = _stack_layers(given[0], "instrument 'stack'")
        self.params = _params(params, kw, f"instrument {type!r}")
        if layers is not None:
            self.params['layers'] = layers
        self.info: dict | None = None
        self.lazy: dict | None = None
        if 'mods' in self.params and type != 'va':
            raise ComposeError(f"instrument {type!r} has no modulation matrix ('mods' is a 'va' param); modulate its "
                               f"params from the track instead: track.modulate('instrument.<param>', lfo(...))")

    def _carry(self, out: 'Instrument') -> 'Instrument':
        out.info = copy.deepcopy(self.info)
        out.lazy = copy.deepcopy(self.lazy)
        return out

    @classmethod
    def coerce(cls, x) -> 'Instrument':
        if isinstance(x, Instrument):
            return x._carry(Instrument(x.type, copy.deepcopy(x.params)))
        if isinstance(x, dict):
            extra = set(x) - {'type', 'params'}
            if 'type' not in x or extra:
                raise ComposeError(f"instrument dict must be {{'type': ..., 'params': {{...}}}}, got keys {sorted(x)}")
            return Instrument(x['type'], copy.deepcopy(x.get('params') or {}))
        raise ComposeError(f"not an instrument: {x!r}; use inst.va(...), {{'type': 'va', 'params': {{}}}} or a Patch")

    def but(self, **params) -> 'Instrument':
        """Copy with some params changed (mods=[...] replaces the whole va modulation matrix). On a stack,
        'layers.<id or index>.<param>' changes one layer: a layer param (level, pan, transpose, delay ...), an effect of
        its chain ('layers.pad.fx.chorus.mix') or its instrument's param ('layers.pad.cutoff')."""
        if self.type == 'stack':
            return self._stack_but(params)
        new = _params(None, params, f"instrument {self.type!r}")
        if self.lazy and 'samples' in new:
            what = 'an .sfz file' if self.lazy.get('kind', 'sfz') == 'sfz' else f"inst.{self.lazy['kind']}(...)"
            raise ComposeError(f"this instrument reads its zones from {what}; 'samples' can't be replaced")
        return self._carry(Instrument(self.type, {**copy.deepcopy(self.params), **new}))

    def _stack_but(self, params: dict) -> 'Instrument':
        where = "instrument 'stack'"
        layers = [x.copy() for x in self.params['layers']]
        rest = {}
        for k, v in params.items():
            key = _key(k)
            if key == 'layers':
                layers = _stack_layers(v, where)
            elif key.startswith('layers.'):
                ref, _, p = key[7:].partition('.')
                if not p:
                    raise ComposeError(f"{where}: {key!r} must be 'layers.<id or index>.<param>'")
                layers[_layer_index(layers, ref, where)].set(p, v)
            else:
                rest[k] = v
        new = _params(None, rest, where)
        base = {k: copy.deepcopy(v) for k, v in self.params.items() if k != 'layers'}
        return self._carry(Instrument('stack', {**base, **new, 'layers': layers}))

    @property
    def layers(self) -> builtins.list:
        """The layers of a stack instrument (copies are made by but(); these are the instrument's own)."""
        if self.type != 'stack':
            raise ComposeError(f"instrument {self.type!r} is not a stack (inst.stack(layer(...), ...))")
        return self.params['layers']

    def expand(self) -> 'Instrument':
        """Read the zones of a lazy inst.sfz / inst.sfz_multi / inst.kit / inst.organ /
        inst.multisample instrument now (in place; returns self). ComposeError when the file or its sample pack is missing.
        A lazy spec may carry 'post': ['package.module:function', ...] - functions called with the expanded instrument
        (in place: per-zone level evening and the like, which a library patch can only do once the zones are read)."""
        if self.type == 'stack':
            for x in self.params.get('layers') or []:
                x.instrument.expand()
            return self
        post = (self.lazy or {}).get('post') or ()
        if self.lazy and self.lazy.get('kind', 'sfz') != 'sfz':   # inst.kit / inst.organ / inst.multisample
            zones, info = _expand_structured(self.lazy)
            if self.lazy.get('keymap'):
                zones = _apply_keymap(zones, self.lazy['keymap'])
            self.params['samples'] = zones
            self.info = {**(self.info or {}), self.lazy['kind']: info}
            self.lazy = None
        if self.lazy:
            from .. import sfz as _sfz
            spec = self.lazy
            if 'programs' in spec:
                zones, info = _sfz.load_multi(spec['programs'], keyswitch=spec.get('keyswitch', 0),
                                              default=spec.get('default'), cc=spec.get('cc'), mics=spec.get('mics'),
                                              strict=spec.get('strict', False), caller_file=spec.get('caller'),
                                              dyn_cc=spec.get('dyn_cc', 'auto'))
            else:
                zones, info = _sfz.load(spec['path'], articulation=spec.get('articulation'), cc=spec.get('cc'),
                                        mics=spec.get('mics'), strict=spec.get('strict', False),
                                        caller_file=spec.get('caller'), dyn_cc=spec.get('dyn_cc', 'auto'),
                                        keyswitches=spec.get('keyswitches', 'live'))
            if spec.get('keymap'):
                zones = _apply_keymap(zones, spec['keymap'])
            if spec.get('hammers'):
                zones = _sfz.hammers(zones, spec['hammers'])
                info = {**info, 'hammers': spec['hammers']}
            if spec.get('velcurve'):
                zones = _sfz.apply_velcurve(zones, spec['velcurve'])
            self.params['samples'] = zones
            for k, v in (info.get('params') or {}).items():   # what the import sets (live 'dynamics' ...); given params win
                self.params.setdefault(k, v)
            self.info = {**(self.info or {}), 'sfz': info}
            self.lazy = None
        for ref in post:
            mod, _, fn = str(ref).partition(':')
            getattr(importlib.import_module(mod), fn)(self)
        return self

    def with_mods(self, *routes, replace: bool = False) -> 'Instrument':
        """Copy of a va instrument with modulation routes added: a route whose id is already in the matrix
        replaces that one (in place), the others are appended; replace=True drops the old matrix first.
        inst.va(...).with_mods(vamod.lfo('sine', hz=5.5) >> ('pitch', 12, 'vib'))."""
        if self.type != 'va':
            raise ComposeError(f"with_mods(): only the 'va' instrument has a modulation matrix, this is {self.type!r}")
        new = _vamod.normalize_mods([*routes], f"instrument {self.type!r} with_mods()")
        params = copy.deepcopy(self.params)
        out = [] if replace else params.get('mods', [])
        for r in new:
            at = [i for i, o in enumerate(out) if 'id' in r and o.get('id') == r['id']]
            if at:
                out[at[0]] = r
            else:
                out.append(r)
        # A flat 'mod.<id|index>.amount' override (from .but()) would silently win over the route given here:
        # drop the ones this call redefines (all of them with replace=True: the indices change too).
        for k in [k for k in params if k.startswith('mod.') and k.endswith('.amount')]:
            ref = k[4:-7]
            if replace or any(r.get('id') == ref for r in new):
                del params[k]
        params['mods'] = out
        return self._carry(Instrument(self.type, params))

    def to_dict(self) -> dict:
        """The render JSON form (a lazy inst.sfz instrument reads its zones first)."""
        self.expand()
        if self.type == 'stack':
            params = {k: copy.deepcopy(v) for k, v in self.params.items() if k != 'layers'}
            params['layers'] = [x.to_dict() for x in self.params['layers']]
            return {'type': 'stack', 'params': params}
        return {'type': self.type, 'params': copy.deepcopy(self.params)}

    def __eq__(self, other) -> bool:
        return isinstance(other, Instrument) and (self.type, self.params, self.lazy) == (other.type, other.params, other.lazy)

    __hash__ = None

    def __repr__(self) -> str:
        if self.type == 'stack':
            rest = {k: v for k, v in self.params.items() if k != 'layers'}
            inner = ', '.join(repr(x) for x in self.params['layers'])
            return f"Instrument('stack', [{inner}]{', ' + repr(rest) if rest else ''})"
        if self.lazy:
            kind = self.lazy.get('kind', 'sfz')
            return f"Instrument({self.type!r}, {kind}={self.lazy.get('path', self.lazy.get('source'))!r}, {self.params!r})"
        if isinstance(self.params.get('samples'), builtins.list) and len(self.params['samples']) > 4:
            rest = {k: v for k, v in self.params.items() if k != 'samples'}
            return f"Instrument({self.type!r}, <{len(self.params['samples'])} zones>, {rest!r})"
        return f"Instrument({self.type!r}, {self.params!r})"


class FX:
    """One insert effect: type + params (+ sidechain source, + optional name for automation targets).
    `sidechain` and `name` are the only reserved keywords; every other keyword is an engine param
    (even 'type', e.g. fx.reverb(type='plate')).

        fx.chorus(mix=0.35)                     fx('eq', {'low.gain': 2})
        fx.compressor(threshold=-20, sidechain='kick')
        fx.filter(name='sweep', cutoff=18000)   -> automate 'fx.sweep.cutoff'"""

    __slots__ = ('type', 'params', 'sidechain', 'name')

    def __init__(self, type: str, params: dict | None = None, /, *, sidechain=None, name: str | None = None, **kw):
        if not isinstance(type, str) or not re.match(r'^[a-z0-9_]+$', type):
            raise ComposeError(f"fx type must be a lowercase name like 'reverb', 'chorus'; got {type!r}")
        self.type = type
        self.params = _fx_paths(_params(params, kw, f"fx {type!r}"), f"fx {type!r}")
        self.sidechain = None if sidechain is None else _ref(sidechain)
        if name is not None and (not isinstance(name, str) or not re.match(r'^[a-z][a-z0-9_]*$', name)):
            raise ComposeError(f"fx name must be a lowercase identifier, got {name!r}")
        self.name = name

    @classmethod
    def coerce(cls, x) -> 'FX':
        if isinstance(x, FX):
            return x.copy()
        if isinstance(x, dict):
            extra = set(x) - {'type', 'params', 'sidechain', 'name'}
            if 'type' not in x or extra:
                raise ComposeError(f"fx dict must be {{'type': ..., 'params': {{...}}, 'sidechain'?: id}}, got keys {sorted(x)}")
            return FX(x['type'], copy.deepcopy(x.get('params') or {}), sidechain=x.get('sidechain'), name=x.get('name'))
        raise ComposeError(f"not an effect: {x!r}; use fx.reverb(...), fx('delay', mix=0.2) or {{'type': ..., 'params': ...}}")

    def copy(self) -> 'FX':
        return FX(self.type, copy.deepcopy(self.params), sidechain=self.sidechain, name=self.name)

    def but(self, **params) -> 'FX':
        f = self.copy()
        f.params.update(_fx_paths(_params(None, params, f"fx {self.type!r}"), f"fx {self.type!r}"))
        return f

    def keyed(self, source) -> 'FX':
        """Copy with a sidechain key source (track/bus or id)."""
        f = self.copy()
        f.sidechain = _ref(source)
        return f

    def to_dict(self) -> dict:
        d = {'type': self.type, 'params': copy.deepcopy(self.params)}
        if 'ir' in d['params']:      # library IRs resolve against the sample folder in effect now (worktrees, tests)
            v = d['params']['ir']
            d['params']['ir'] = [_library_path(x) for x in v] if isinstance(v, builtins.list) else _library_path(v)
        if self.sidechain is not None:
            d['sidechain'] = self.sidechain
        return d

    def __eq__(self, other) -> bool:
        return isinstance(other, FX) and (self.type, self.params, self.sidechain, self.name) == \
            (other.type, other.params, other.sidechain, other.name)

    __hash__ = None

    def __repr__(self) -> str:
        extra = (f", sidechain={self.sidechain!r}" if self.sidechain else '') + (f", name={self.name!r}" if self.name else '')
        return f"FX({self.type!r}, {self.params!r}{extra})"


# ------------------------------------------------------------------------------------ stack layers

# The layer's own params (engine 'stack', docs/RENDER_FORMAT.md "Stack"); anything else given to a layer is a param of
# its instrument. The follow.* flags are spelled bend= / pedal= / expression= / dynamics= / modwheel= in layer().
LAYER_KEYS = ('level', 'pan', 'mute', 'transpose', 'fine', 'keylo', 'keyhi', 'keyfade', 'vello', 'velhi', 'velfade',
              'velcurve', 'velscale', 'delay', 'xfvoices', 'follow.bend', 'follow.pedal', 'follow.expression',
              'follow.dynamics', 'follow.modwheel')
_FOLLOW = {'bend': 'follow.bend', 'pedal': 'follow.pedal', 'expression': 'follow.expression',
           'dynamics': 'follow.dynamics', 'modwheel': 'follow.modwheel'}
_LAYER_ID_RE = re.compile(r'^[a-z0-9_]+$')


def _layer_id(text: str) -> str:
    s = re.sub(r'[^a-z0-9_]+', '_', str(text).lower()).strip('_')
    return s or 'layer'


class Layer:
    """One layer of a stack instrument (inst.stack / Patch.layered): an instrument, an optional insert fx chain (the
    layer's own, before the stack's track fx) and the layer params (LAYER_KEYS). Build with layer(...)."""

    __slots__ = ('id', 'instrument', 'fx', 'params', 'source')

    def __init__(self, id: str | None, instrument, fx=(), params: dict | None = None, source: str | None = None):
        self.instrument = Instrument.coerce(instrument)
        if self.instrument.type == 'stack':
            raise ComposeError("a stack layer can't be a stack (flatten it: pass its layers to inst.stack directly)")
        if id is not None and (not isinstance(id, str) or not _LAYER_ID_RE.match(id)):
            raise ComposeError(f"layer id must be a lowercase name of a-z 0-9 _, got {id!r}")
        self.id = id
        self.fx = [FX.coerce(f) for f in (fx or ())]
        for f in self.fx:
            if f.sidechain is not None:
                raise ComposeError(f"layer {id!r}: fx {f.type!r} has a sidechain; a layer effect has no key input "
                                   f"(put the keyed effect on the track)")
        self.params = {}
        for k, v in (params or {}).items():
            self.set(k, v)
        self.source = source

    @classmethod
    def coerce(cls, x, where: str = 'layer') -> 'Layer':
        if isinstance(x, Layer):
            return x.copy()
        if isinstance(x, (Patch, Instrument, str)):
            return layer(x)
        if isinstance(x, dict):   # the render JSON form
            extra = set(x) - {'id', 'instrument', 'fx'} - set(LAYER_KEYS)
            if 'instrument' not in x or extra:
                raise ComposeError(f"{where}: a layer dict needs 'instrument' (+ 'id', 'fx', {', '.join(LAYER_KEYS)}); "
                                   f"got keys {sorted(x)}")
            return Layer(x.get('id'), x['instrument'], x.get('fx') or (),
                         {k: v for k, v in x.items() if k in LAYER_KEYS})
        raise ComposeError(f"{where}: not a layer: {x!r}; use layer('patch/name' or inst.x(...), level=..., ...)")

    def copy(self) -> 'Layer':
        out = Layer.__new__(Layer)
        out.id = self.id
        out.instrument = Instrument.coerce(self.instrument)
        out.fx = [f.copy() for f in self.fx]
        out.params = dict(self.params)
        out.source = self.source
        return out

    def __deepcopy__(self, memo) -> 'Layer':
        return self.copy()

    def set(self, key: str, value) -> None:
        """Changes one param in place: a layer param, 'fx.<index|name|type>.<param>' or an instrument param."""
        k = _key(key)
        where = f"layer {self.id!r}"
        if k in _FOLLOW:
            k = _FOLLOW[k]
        if k in LAYER_KEYS:
            if isinstance(value, bool):
                value = 1 if value else 0
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ComposeError(f"{where}: {k!r} must be a number, got {value!r}")
            self.params[k] = value
        elif k.startswith('fx.'):
            ref, _, p = k[3:].partition('.')
            if not p:
                raise ComposeError(f"{where}: {k!r} must be 'fx.<index|name|type>.<param>'")
            i = _fx_index(self.fx, int(ref) if ref.isdigit() else ref, where)
            self.fx[i] = self.fx[i].but(**{p: value})
        else:
            self.instrument = self.instrument.but(**{k: value})

    def to_dict(self, index: int | None = None) -> dict:
        d: dict = {'id': self.id if self.id is not None else str(index if index is not None else 0),
                   'instrument': self.instrument.to_dict()}
        for k in LAYER_KEYS:
            if k in self.params:
                v = self.params[k]
                d[k] = bool(v) if (k == 'mute' or k.startswith('follow.')) else v
        if self.fx:
            d['fx'] = [f.to_dict() for f in self.fx]
        return d

    def __eq__(self, other) -> bool:
        return isinstance(other, Layer) and (self.id, self.instrument, self.fx, self.params) == \
            (other.id, other.instrument, other.fx, other.params)

    __hash__ = None

    def __repr__(self) -> str:
        what = self.source or self.instrument.type
        extra = ''.join(f", {k}={v!r}" for k, v in self.params.items())
        fxs = f", fx=[{', '.join(f.type for f in self.fx)}]" if self.fx else ''
        return f"layer({what!r}, id={self.id!r}{extra}{fxs})"


def layer(sound, id: str | None = None, *, fx=(), keys=None, vel=None, bend=None, pedal=None, expression=None,
          dynamics=None, modwheel=None, **params) -> Layer:
    """One layer of a stack (inst.stack(layer(...), ...) / Patch.layered(...)):

        layer('sampled/piano_lead')                               # a patch: its instrument + fx chain, level = its gain
        layer('synthwave/dx_bells', transpose=12, level=-10, bend=False)
        layer(inst.va(cutoff=1800, unison=5), 'pad', level=-14, delay=60, fx=[fx.chorus(mix=0.4)])
        layer('sampled/rhodes', vel=(0, 90), velfade=30)          # velocity crossfade: soft = rhodes ...
        layer('sampled/grand_piano', vel=(60, 127), velfade=30)   # ... hard = grand
        layer('sampled/cellos', keys=('C2', 'B3'), transpose=-12)

    sound: a patch name, a Patch (its instrument; its fx chain becomes the layer fx, followed by fx=; its gain_db is
    added to the level and its pan is the layer pan; its sends are dropped: give the stack patch / track the sends) or
    an Instrument. id: the layer's name for addressing ('layers.<id>.cutoff'; default: the patch name's last part or
    the instrument type). keys=(lo, hi) (MIDI or note names), vel=(lo, hi) (1..127). bend / pedal / expression /
    dynamics / modwheel: False = the layer ignores the stack's param of that name. Layer params: level (dB), pan,
    mute, transpose (st), fine (ct), keyfade, velfade, velcurve, velscale, delay (ms), xfvoices (docs/COMPOSE_API.md
    "Layered instruments"); every other keyword is a param of the layer's instrument (cutoff=..., release=...)."""
    source = None
    if isinstance(sound, str):
        source = sound
        sound = get(sound)
    patch_fx, level, pan = [], 0.0, None
    if isinstance(sound, Patch):
        if sound.instrument is None:
            raise ComposeError(f"layer: patch {sound.name!r} is an fx chain, not an instrument")
        source = source or sound.name
        patch_fx, level, pan = [f.copy() for f in sound.fx], sound.gain_db, sound.pan
        instrument = sound.instrument
    elif isinstance(sound, Instrument):
        instrument = sound
    else:
        try:
            instrument = Instrument.coerce(sound)
        except ComposeError as e:
            raise ComposeError(f"layer: {e}") from None
    if id is None:
        id = _layer_id(source.rsplit('/', 1)[-1]) if source else instrument.type
    lp: dict = {}
    child: dict = {}
    for k, v in params.items():
        kk = _key(k)
        (lp if kk in LAYER_KEYS else child)[kk] = v
    if level:
        lp['level'] = round(level + float(lp.get('level', 0.0)), 4)
    if pan and 'pan' not in lp:
        lp['pan'] = pan
    if keys is not None:
        if not isinstance(keys, (tuple, builtins.list)) or len(keys) != 2:
            raise ComposeError(f"layer {id!r}: keys must be (lo, hi), got {keys!r}")
        lp['keylo'], lp['keyhi'] = (int(_midi(x, f"layer {id!r} keys")) for x in keys)
    if vel is not None:
        if not isinstance(vel, (tuple, builtins.list)) or len(vel) != 2:
            raise ComposeError(f"layer {id!r}: vel must be (lo, hi) velocities, got {vel!r}")
        lp['vello'], lp['velhi'] = int(vel[0]), int(vel[1])
    for name, flag in (('bend', bend), ('pedal', pedal), ('expression', expression), ('dynamics', dynamics),
                       ('modwheel', modwheel)):
        if flag is not None:
            lp[_FOLLOW[name]] = 1 if flag else 0
    if child:
        instrument = instrument.but(**child)
    return Layer(id, instrument, patch_fx + [FX.coerce(f) for f in (fx or ())], lp, source)


def _stack_layers(value, where: str) -> builtins.list:
    """Layers for a stack: 1..8 layer(...) / patch names / Patches / Instruments / layer dicts, ids made unique."""
    if isinstance(value, (Layer, Patch, Instrument, str, dict)):
        value = [value]
    if not isinstance(value, (builtins.list, tuple)) or not 1 <= len(value) <= 8:
        raise ComposeError(f"{where}: a stack has 1..8 layers, got {value!r}")
    out = [Layer.coerce(x, f"{where} layer #{i}") for i, x in enumerate(value)]
    seen: set = set()
    for i, x in enumerate(out):
        base = x.id if x.id is not None else str(i)
        if base.isdigit() and base != str(i):
            base = f"l{base}"
        name, n = base, 2
        while name in seen:
            name, n = f"{base}{n}", n + 1
        x.id = name
        seen.add(name)
    return out


def _layer_index(layers: builtins.list, ref: str, where: str) -> int:
    """Index of a stack layer by id or index."""
    for i, x in enumerate(layers):
        if x.id == ref:
            return i
    if ref.isdigit() and int(ref) < len(layers):
        return int(ref)
    raise ComposeError(f"{where}: no layer {ref!r} (layers: {', '.join(f'{i}:{x.id}' for i, x in enumerate(layers))})")


def _fx_index(chain: builtins.list, which, where: str) -> int:
    """Index of an effect in a chain by index, name or type (first match; name wins over type)."""
    if isinstance(which, int) and not isinstance(which, bool):
        if 0 <= which < len(chain):
            return which
    elif isinstance(which, str):
        hits = [i for i, f in enumerate(chain) if f.name == which] or                [i for i, f in enumerate(chain) if f.type == which]
        if hits:
            return hits[0]
    listing = ', '.join(f"{i}:{f.type}" + (f"({f.name})" if f.name else '') for i, f in enumerate(chain)) or 'empty'
    raise ComposeError(f"{where}: no effect {which!r} in the chain ({listing})")


class _Factory:
    """fx.reverb(mix=1) == FX('reverb', mix=1); fx('reverb', {...}) also works. Same for inst."""

    def __init__(self, cls):
        self._cls = cls

    def __call__(self, type: str, params: dict | None = None, /, **kw):
        return self._cls(type, params, **kw)

    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        return lambda *args, **kw: self._cls(name, *args, **kw)


def _sample_path(path, caller_file: str | None, where: str) -> str:
    """A sample / SoundFont path for the engine. Plain relative paths stay relative to assets/ (the engine
    resolves them); './...' and '../...' paths are taken relative to the calling file (the song) and made
    absolute; absolute paths are kept. Returned with forward slashes."""
    if isinstance(path, os.PathLike):
        path = os.fspath(path)
    if not isinstance(path, str) or not path.strip():
        raise ComposeError(f"{where}: a path must be a non-empty string or pathlib.Path, got {path!r}")
    text = path.strip().replace(os.sep, '/')
    if text.startswith(('./', '../')):
        if not caller_file:
            raise ComposeError(f"{where}: {text!r} is relative to the song file, but the caller has no __file__; "
                               f"use an absolute path or a path inside assets/")
        text = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(caller_file)), text))
    return text.replace(os.sep, '/')


def _caller_file(depth: int = 2) -> str | None:
    """__file__ of the code that called the inst.* constructor."""
    try:
        return sys._getframe(depth).f_globals.get('__file__')
    except ValueError:
        return None


def _midi(x, where: str):
    """MIDI number from an int/float or a note name ('C4' = 60)."""
    if isinstance(x, str):
        from ..theory import note
        return note(x)
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ComposeError(f"{where}: expected a MIDI note number or a note name like 'C4', got {x!r}")
    return x


def _keymap(keymap) -> dict:
    """inst.sfz / inst.kit keymap= validated: {dst key: src key or None} with MIDI numbers (string keys for JSON-safe copies)."""
    if not isinstance(keymap, dict):
        raise ComposeError(f"inst.sfz / inst.kit: keymap must be a dict {{key: source key or None}}, got {keymap!r}")
    out = {}
    for dst, src in keymap.items():
        keys = [_midi(dst, 'inst.sfz keymap key')] + ([] if src is None else [_midi(src, f'inst.sfz keymap[{dst!r}]')])
        if any(k != int(k) or not 0 <= k <= 127 for k in keys):
            raise ComposeError(f"inst.sfz keymap: keys must be MIDI notes 0..127, got {dst!r}: {src!r}")
        out[str(int(keys[0]))] = None if src is None else int(keys[1])
    return out


def _apply_keymap(zones: builtins.list, keymap: dict) -> builtins.list:
    """Copy the single-key zones of each source key onto its destination key (the destination's own single-key
    zones are replaced; the root moves with the key, so the copy sounds like the source); None empties the key."""
    dsts = {int(k) for k in keymap}
    out = [z for z in zones if not (z.get('lo', 0) == z.get('hi', 127) and z.get('lo', 0) in dsts)]
    for dst, src in ((int(k), v) for k, v in keymap.items()):
        if src is None:
            continue
        for z in zones:
            if z.get('lo', 0) == z.get('hi', 127) == src:
                c = copy.deepcopy(z)
                c['lo'] = c['hi'] = dst
                root = c.get('root', 60)
                if isinstance(root, (int, float)) and not isinstance(root, bool):
                    c['root'] = root + (dst - src)
                out.append(c)
    return out


def _zone(z, caller: str | None, where: str) -> dict:
    if not isinstance(z, dict):
        raise ComposeError(f"{where}: a zone must be a dict like {{'file': 'samples/pad/C4.wav', 'root': 'C4'}}, got {z!r}")
    out = {str(k): v for k, v in z.items()}
    if 'file' not in out:
        raise ComposeError(f"{where}: a zone needs 'file' (a WAV, or a .sf2 plus 'sample')")
    out['file'] = _sample_path(out['file'], caller, where)
    for key in ('root', 'lo', 'hi'):
        if key in out:
            out[key] = _midi(out[key], f"{where}.{key}")
    return out


class _InstFactory(_Factory):
    def stack(self, *layers, **params) -> Instrument:
        """Layered instruments on one track (engine 'stack'): every note plays on each layer whose key / velocity range
        it falls in.
            inst.stack(layer('sampled/piano_lead'),
                       layer('synthwave/dx_bells', transpose=12, level=-10, bend=False),
                       layer(inst.va(cutoff=1500, unison=5), 'pad', level=-16, delay=80))
            inst.stack(layer('sampled/rhodes', vel=(1, 90), velfade=30), layer('sampled/grand_piano', vel=(60, 127),
                       velfade=30))                                            # velocity crossfade
        Layers: layer(...) objects, patch names, Patches or Instruments (1..8). Stack params: level, pitchbend, pedal,
        expression, dynamics, modwheel (forwarded to the layers that follow them). Address a layer as
        'layers.<id>.<param>' in .but(), automation and modulators. docs/COMPOSE_API.md "Layered instruments"."""
        if len(layers) == 1 and isinstance(layers[0], (builtins.list, tuple)):
            layers = tuple(layers[0])
        if not layers:
            raise ComposeError("inst.stack: give 1..8 layers: inst.stack(layer('sampled/piano_lead'), layer(...), ...)")
        return Instrument('stack', {'layers': builtins.list(layers), **params})

    def dx7(self, voice: str | None = None, params: dict | None = None, /, **kw) -> Instrument:
        """DX7 ROM voice by name: inst.dx7('E.PIANO 1')."""
        p = dict(params or {})
        if voice is not None:
            p['voice'] = voice
        return Instrument('dx7', p, **kw)

    def sf2(self, preset: str | None = None, params: dict | None = None, /, *, bank: int | None = None,
            program: int | None = None, file=None, **kw) -> Instrument:
        """SoundFont preset (default font: assets/soundfonts/GeneralUser-GS.sf2, the full GM/GS set):
            inst.sf2('Grand Piano')                  # by name (case-insensitive) or 'bank:program', e.g. '0:48'
            inst.sf2(bank=0, program=48)             # GM program numbers; bank 128 = drum kits
            inst.sf2('Slow Strings', attack=3, release=2, width=1.2, cutoff=-12)
            inst.sf2('Warm Pad', file='MyFont.sf2')  # another font in assets/soundfonts/ ('./x.sf2': next to the song)
        List presets: python -m agentsound sf2 [search]; params: python -m agentsound params sf2."""
        p = dict(params or {})
        if preset is not None:
            if not isinstance(preset, str) or not preset.strip():
                raise ComposeError(f"inst.sf2: preset must be a name like 'Grand Piano' or 'bank:program', got {preset!r}")
            p['preset'] = preset
        if bank is not None or program is not None:
            if 'preset' in p:
                raise ComposeError("inst.sf2: give a preset name or bank=/program=, not both")
            if program is None:
                raise ComposeError("inst.sf2: bank= needs program= (0..127)")
            p['bank'] = 0 if bank is None else bank
            p['program'] = program
        if file is not None:
            p['file'] = _sample_path(file, _caller_file(), 'inst.sf2(file=...)')
        return Instrument('sf2', p, **kw)

    def sampler(self, dir=None, *, file=None, zones=None, root=None, loop=None, sample: str | None = None,
                params: dict | None = None, lazy: bool = False, **kw) -> Instrument:
        """WAV sampler (runs through fx, sends, automation and modulators like any synth):
            inst.sampler(dir='samples/909', oneshot='on')      # a folder in assets/: files named by GM drum
                                                                 # (kick.wav, snare, clap, hat, ohh, crash, ...)
                                                                 # or by note (C4.wav, F#3.wav, 60.wav)
            inst.sampler(dir='./samples/chops')                # './', '../': relative to the song file
            inst.sampler(file='samples/pad.wav', root='A3', loop='forward')
            inst.sampler(zones=[{'file': 'samples/p/C3.wav', 'root': 'C3', 'hi': 'F#3'},
                                {'file': 'samples/p/C4.wav', 'root': 'C4', 'lo': 'G3', 'vello': 90}])
            inst.sampler(file='soundfonts/GeneralUser-GS.sf2', sample='Orchestra Hit-2', oneshot='on')
        Zone keys: file, sample (SoundFont sample name), root, lo, hi (MIDI numbers or note names), vello,
        velhi, loop ('none'|'forward'|'pingpong'), loopStart, loopEnd (frames), gain (dB), tune (cents),
        pan, choke (group: a note chokes the others of its group) and the other zone fields of docs/RENDER_FORMAT.md.
        lazy=True (zones= only; library patches): the zone files are looked up when the render JSON is built -
        'samples/<pack>/...' in the sample library ($AGENTSOUND_SAMPLES), a missing pack is a ComposeError with its
        fetch command - so defining the instrument needs no samples."""
        caller = _caller_file()
        if lazy:
            if zones is None or dir is not None or file is not None or root is not None or loop is not None \
                    or sample is not None or 'samples' in (params or {}):
                raise ComposeError("inst.sampler(lazy=True) takes zones=[...] only (put root / loop into each zone)")
            if not isinstance(zones, (builtins.list, tuple)) or not zones:
                raise ComposeError(f"inst.sampler: zones must be a non-empty list of dicts, got {zones!r}")
            checked = [_zone(z, caller, f"inst.sampler zones[{i}]") for i, z in enumerate(zones)]
            spec = {'kind': 'zones', 'source': checked[0]['file'], 'zones': checked, 'caller': caller}
            return self._structured('zones', spec, params, kw, {}, True)
        p = dict(params or {})
        given = [n for n, v in (('dir', dir), ('file', file), ('zones', zones)) if v is not None]
        if 'samples' in p:
            given.append("params 'samples'")
        if len(given) != 1:
            raise ComposeError("inst.sampler: give exactly one of dir=, file= or zones= "
                               f"(got {', '.join(given) if given else 'none'})")
        extra = {k: v for k, v in (('root', root), ('loop', loop), ('sample', sample)) if v is not None}
        if dir is not None:
            if set(extra) - {'loop'}:
                raise ComposeError("inst.sampler(dir=...): the files are mapped by their names; root=/sample= are for file=")
            samples = {'dir': _sample_path(dir, caller, 'inst.sampler(dir=...)'), **extra}
        elif file is not None:
            samples = _zone({'file': file, **extra}, caller, 'inst.sampler(file=...)')
        elif zones is not None:
            if extra:
                raise ComposeError("inst.sampler(zones=[...]): put root/loop/sample into each zone dict")
            if not isinstance(zones, (builtins.list, tuple)) or not zones:
                raise ComposeError(f"inst.sampler: zones must be a non-empty list of dicts, got {zones!r}")
            samples = [_zone(z, caller, f"inst.sampler zones[{i}]") for i, z in enumerate(zones)]
        else:
            samples = p.pop('samples')
        p['samples'] = samples
        return Instrument('sampler', p, **kw)

    def sfz(self, path, *, articulation=None, cc: dict | None = None, mics: dict | None = None, strict: bool = False,
            params: dict | None = None, lazy: bool = False, dyn_cc='auto', keyswitches: str = 'live',
            keymap: dict | None = None, hammers: float | None = None, velcurve=None, **kw) -> Instrument:
        """A sampled instrument from an .sfz file (the format of most free multisample libraries) on the 'sampler':
            inst.sfz('samples/salamander-grand/SalamanderGrandPianoV3.sfz', pedal=0)
            inst.sfz('samples/vpo-scripts-standard/Strings/1st-violin-SEC-KS-C2.sfz', articulation='staccato')
            inst.sfz('samples/meatbass/Programs/04_pizz.sfz', cc={107: 0}, level=-3)
            inst.sfz('samples/swirly-drums/Programs/Basic_kit.sfz', cc={4: 110, 14: 0}, mics={'wet': -6})
        articulation: a keyswitch articulation by label (substring) or key (sfz.articulations(path)), chosen statically;
        without it every articulation is imported and switched live per note (keyswitches='live': clip.articulate(
        'staccato') -> keyswitch notes at compile; 'static': only the default one); cc: fixed controller values
        {number: 0..127} for the whole song (layer conditions, modulations, crossfades; default: the file's set_ccN,
        else 0; 7 = 100, 10 = 64, 11 = 127); dyn_cc: the dynamics controller that stays LIVE as the automatable
        'dynamics' param ('auto': CC1, else CC11, when the file maps crossfades / volume / cutoff / layers to it;
        a number; None = static like the others); mics: {name: dB or None} gain / mute per microphone or signal layer
        (sfz.mics(path)); keymap: {key: source key or None} copies the zones of one key onto another after the
        import (a drum kit with non-GM keys: {48: 47, 50: 47} = toms on the GM high-tom keys, same sound; None
        silences the key), keys as MIDI numbers or note names; hammers: 0..1 piano hammer voicing (sfz.hammers: the
        loud velocity layers less glassy, the soft ones a little clearer - a gentler velocity -> brightness curve;
        0.5-0.8 = a warm jazz grand);
        velcurve: [(velocity, gain), ...] one velocity -> amplitude curve for every velocity-layer zone, replacing the file's
        amp_velcurve / amp_veltrack (a pack whose layers ramp to full level at the top of each layer plays louder
        at velocity 96 than at 103: sfz.even_velcurve() builds a smooth, monotonic curve from measured layer levels).
        strict=True raises on opcodes the engine can't do (default: one compile warning lists them). Other keywords are sampler params: level, pedal, expression (automatable), transpose, polyphony
        (128 here), attack / decay / sustain / release (only for zones without their own ampeg_*: SFZ defaults here),
        velsens, width, cutoff ... Paths: 'samples/<pack>/...' ($AGENTSOUND_SAMPLES or assets/samples), './x.sfz' next to
        the song, absolute. At compile, zones no note of the track can reach are dropped (only those load).
        lazy=True (library patches) reads the file only when the render JSON is built. Inspect a file:
        python -m agentsound sfz FILE [--json]."""
        from .. import sfz as _sfz
        caller = _caller_file()
        p = dict(_SFZ_DEFAULTS)
        p.update(params or {})
        p.update(kw)
        if 'samples' in p:
            raise ComposeError("inst.sfz: the zones come from the .sfz file; 'samples' can't be given too")
        if hammers is not None and (isinstance(hammers, bool) or not isinstance(hammers, (int, float))
                                    or not 0.0 <= hammers <= 1.0):
            raise ComposeError(f"inst.sfz: hammers must be a number 0..1 (0 = as recorded), got {hammers!r}")
        spec = {'path': os.fspath(path) if isinstance(path, os.PathLike) else path, 'articulation': articulation,
                'cc': dict(cc) if cc else None, 'mics': dict(mics) if mics else None, 'strict': bool(strict),
                'caller': caller, 'dyn_cc': dyn_cc, 'keyswitches': keyswitches, 'hammers': hammers}
        if keymap:
            spec['keymap'] = _keymap(keymap)
        if velcurve is not None:
            from ..sfz import check_velcurve
            spec['velcurve'] = check_velcurve(velcurve)
        if lazy:
            if not isinstance(spec['path'], str) or not spec['path'].strip():
                raise ComposeError(f"inst.sfz: the path must be a non-empty string, got {path!r}")
            out = Instrument('sampler', p)
            out.lazy = spec
            return out
        out = Instrument('sampler', p)
        out.lazy = spec
        return out.expand()

    def sfz_multi(self, programs: dict, *, keyswitch=0, default=None, cc: dict | None = None, mics: dict | None = None,
                  strict: bool = False, params: dict | None = None, lazy: bool = False, dyn_cc='auto',
                  **kw) -> Instrument:
        """One sampled instrument from separate per-articulation programs, switched per note by keyswitches:
            vln = inst.sfz_multi({'sustain': 'samples/vsco2-ce/SViolinVib.sfz',
                                  'staccato': 'samples/vsco2-ce/SViolinSpic.sfz',
                                  'pizzicato': {'path': 'samples/vsco2-ce/SViolinPizz.sfz', 'gain': -3}},
                                 mono='legato', layers='dynamics')
            vln_track.play(line.articulate('staccato', span=(8, 12)), verse)    # keyswitches inserted at compile
        Articulation i gets keyswitch key `keyswitch` + i (default 0 = C-1 upwards, below any played note); `default`
        (else the first) plays unmarked notes. A program may be a dict with 'path', 'articulation' (of a keyswitch
        program), 'cc', 'mics', 'gain' (dB, to balance the programs), 'zone' ({zone param: value} set on its attack
        zones: an articulation made from the same samples, e.g. a palm mute = the notes low-passed and damped),
        'keygain' ([[key, dB], ...] over the zones' root keys: evens out notes recorded at uneven levels).
        Other keywords as inst.sfz (params: mono, layers, dynamics, level ...). sfz.load_multi() has the details."""
        caller = _caller_file()
        p = dict(_SFZ_DEFAULTS)
        p.update(params or {})
        p.update(kw)
        if 'samples' in p:
            raise ComposeError("inst.sfz_multi: the zones come from the .sfz files; 'samples' can't be given too")
        progs = {k: (os.fspath(v) if isinstance(v, os.PathLike) else (dict(v) if isinstance(v, dict) else v))
                 for k, v in (programs.items() if isinstance(programs, dict) else [])}
        if not progs:
            raise ComposeError("inst.sfz_multi: programs must be a non-empty dict {'sustain': 'x.sfz', ...}")
        spec = {'programs': progs, 'keyswitch': keyswitch, 'default': default, 'cc': dict(cc) if cc else None,
                'mics': dict(mics) if mics else None, 'strict': bool(strict), 'caller': caller, 'dyn_cc': dyn_cc}
        out = Instrument('sampler', p)
        out.lazy = spec
        return out if lazy else out.expand()

    def kit(self, source, map: dict | None = None, *, numbered: str = 'auto', fill: bool = True, humanize=None,
            mics: dict | None = None, gains: dict | None = None, spread: float = 0.5, kit: str | None = None,
            extras: bool = True, keymap: dict | None = None, params: dict | None = None, lazy: bool = False,
            **kw) -> Instrument:
        """A GM-mapped drum kit on the 'sampler' from any one-shot folder (arbitrary file names), a Hydrogen kit
        (drumkit.xml) or a DrumGizmo kit (multichannel hits; mics= mixes the microphones):
            inst.kit('samples/hyperreal-linndrum')                                  # names -> GM keys
            inst.kit('samples/sampleradar-80s-pop-drums/Drum Kits/Kit A', map={'snare': 'Snare03', 40: 'Gated*'})
            inst.kit('samples/hydrogen-forzee-stereo', level=-3)
            inst.kit('samples/drumgizmo-drskit', mics={'room': -6, 'overheads': -2, 'snare': 2})
            inst.kit(['./hits/boom.wav', './hits/tick.wav'], map={'kick': 'boom', 'hat': 'tick'})
        Velocity layers and round robins come from the names or measured loudness (see agentsound/kits.py); hats
        choke each other; every zone is a one-shot. map= overrides keys ({'snare': 'file or glob', 'clap': None,
        40: {'files': [...], 'gain': -3}}); numbered='auto'|'variants'|'layers'|'rr'|'random' says what numbered
        files of one name are; fill (retuned toms, kick2, pedal hat, crash2, ride2 on empty keys); humanize (tiny
        per-hit level / pitch variation; default: multi-sample sounds only); gains={'hats': -4, 'kick': 2} (dB per
        role / family / key); spread (stereo spread of mono one-shots); kit= (DrumGizmo kit file); extras=False
        (only the recognized GM sounds: no spare keys 88+ for unknown files and extra variants); keymap: {key:
        source key or None} copies / clears keys after the build like inst.sfz(keymap=) (for DrumGizmo and Hydrogen
        kits, which map their instruments themselves). Other keywords
        are sampler params (level, velsens, cutoff, tune, width ...). The mapping: python -m agentsound kit DIR;
        the key names are in instrument.info['kit']['names']. lazy=True (library patches) builds it at render."""
        caller = _caller_file()
        spec = {'kind': 'kit', 'source': source if isinstance(source, (str, builtins.list, tuple)) else os.fspath(source),
                'map': copy.deepcopy(map), 'numbered': numbered, 'fill': fill, 'humanize': humanize,
                'mics': copy.deepcopy(mics), 'gains': copy.deepcopy(gains), 'spread': spread, 'kit': kit,
                'extras': extras, 'caller': caller}
        if keymap:
            spec['keymap'] = _keymap(keymap)
        return self._structured('kit', spec, params, kw, _KIT_DEFAULTS, lazy)

    def organ(self, source, stops=None, *, manual=None, tremulant=False, release: bool = True, stereo: str = 'asis',
              extend: str = 'octave', odf: str | None = None, params: dict | None = None, lazy: bool = False,
              **kw) -> Instrument:
        """A pipe organ from a GrandOrgue sample set: the chosen stops layered, each pipe with its sustain loop and
        its recorded release into the room:
            inst.organ('samples/lars-palo-burea-church', stops=['Principal 8', 'Oktava 4', 'Mixtur'])
            inst.organ('samples/lars-palo-burea-church', stops=['Rorflojt 8'], manual='Svallverk', tremulant=True)
            inst.organ('samples/lars-palo-burea-church', stops=['Subbas 16', 'Principal 8'], manual='pedal')
        Stop names: case, accents and foot marks ignored; 'manual: stop' or manual= picks the manual (a name found on
        several manuals: the first manual that is not the pedal). tremulant: True or a depth factor. release=False
        drops the release samples. stereo: 'asis' (the recording), 'flip' (right channel inverted), 'left' / 'right'
        (one microphone on both sides: mono, nothing cancels - pedal / bass stops) or {stop: mode} per stop.
        extend: notes outside a stop's compass play the
        pipe an octave inside ('octave', default: no silent notes), transposed ('stretch') or not at all ('none').
        odf: which .organ file of the folder. Other keywords are sampler params
        (level, expression = the swell pedal, transpose ...). List the stops: python -m agentsound kit <folder>."""
        caller = _caller_file()
        spec = {'kind': 'organ', 'source': source if isinstance(source, str) else os.fspath(source),
                'stops': copy.deepcopy(stops), 'manual': manual, 'tremulant': tremulant, 'release': release,
                'stereo': copy.deepcopy(stereo), 'extend': extend, 'odf': odf, 'caller': caller}
        return self._structured('organ', spec, params, kw, _ORGAN_DEFAULTS, lazy)

    def multisample(self, source, *, octave: int = 0, loop: str | None = 'auto', keys=None, root=None,
                    loop_start: int | None = None, loop_end: int | None = None, match=None,
                    params: dict | None = None, lazy: bool = False, **kw) -> Instrument:
        """A melodic instrument from note-named samples (non-SFZ multisample packs): each file on its root key
        ('Jupiter Pad C3.wav', 'Str_F#2.wav', '060.wav'), spread to its neighbours; velocity layers / round robins
        from the names:
            inst.multisample('samples/<pack>/<folder>', release=0.4)
            inst.multisample('samples/<pack>/<folder>', octave=1)     # a pack that calls middle C 'C3'
            inst.multisample('samples/philharmonia-all/cello', match=['_1_', 'arco-normal'])   # one length + articulation
        loop: 'auto' (the files' own smpl loops), 'none', 'forward', 'pingpong', 'sustain' (loop_start / loop_end:
        frames); root: the key of files without a note in the name (one sample over the keyboard: root='A3');
        keys=(lo, hi): the stretch range. Other keywords are sampler params. Check: python -m agentsound kit DIR
        --multisample."""
        caller = _caller_file()
        spec = {'kind': 'multisample', 'source': source if isinstance(source, (str, builtins.list, tuple)) else os.fspath(source),
                'octave': octave, 'loop': loop, 'keys': builtins.list(keys) if keys else None, 'root': root,
                'loopStart': loop_start, 'loopEnd': loop_end, 'match': copy.deepcopy(match), 'caller': caller}
        return self._structured('multisample', spec, params, kw, _MULTI_DEFAULTS, lazy)

    @staticmethod
    def _structured(kind: str, spec: dict, params, kw, defaults: dict, lazy: bool) -> Instrument:
        p = dict(defaults)
        p.update(params or {})
        p.update(kw)
        if 'samples' in p:
            raise ComposeError(f"inst.{kind}: the zones come from the {kind} builder; 'samples' can't be given too")
        src = spec['source']
        if not (isinstance(src, str) and src.strip()) and not (isinstance(src, (builtins.list, tuple)) and src):
            raise ComposeError(f"inst.{kind}: the source must be a folder / file path (or a list of files), got {src!r}")
        out = Instrument('sampler', p)
        out.lazy = spec
        if not lazy:
            out.expand()
        return out


# Sampler params for kits / organs / multisamples: kits are one-shot zones (room for cymbals ringing on and layered
# DrumGizmo microphones); organs layer stops with release samples; multisamples get a gentle release.
_KIT_DEFAULTS = {'polyphony': 96}
_ORGAN_DEFAULTS = {'attack': 0.0, 'decay': 0.001, 'sustain': 1.0, 'release': 0.07, 'polyphony': 256}
_MULTI_DEFAULTS = {'attack': 0.002, 'release': 0.35, 'polyphony': 64}


def _expand_structured(spec: dict) -> tuple[builtins.list, dict]:
    """Zones + info of a lazy inst.kit / inst.organ / inst.multisample instrument."""
    kind = spec['kind']
    if kind == 'kit':
        from .. import kits as _kits
        zones, info = _kits.build(spec['source'], spec.get('map'), numbered=spec.get('numbered', 'auto'),
                                  fill=spec.get('fill', True), humanize=spec.get('humanize'), mics=spec.get('mics'),
                                  gains=spec.get('gains'), spread=spec.get('spread', 0.5), kit=spec.get('kit'),
                                  extras=spec.get('extras', True), caller_file=spec.get('caller'))
    elif kind == 'organ':
        from .. import organ as _organ
        zones, info = _organ.load(spec['source'], spec.get('stops'), manual=spec.get('manual'),
                                  tremulant=spec.get('tremulant', False), release=spec.get('release', True),
                                  stereo=spec.get('stereo', 'asis'), extend=spec.get('extend', 'octave'),
                                  odf=spec.get('odf'), caller_file=spec.get('caller'))
    elif kind == 'multisample':
        from .. import kits as _kits
        keys = spec.get('keys')
        zones, info = _kits.multisample(spec['source'], octave=spec.get('octave', 0), loop=spec.get('loop', 'auto'),
                                        keys=tuple(keys) if keys else None, root=spec.get('root'),
                                        loop_start=spec.get('loopStart'), loop_end=spec.get('loopEnd'),
                                        match=spec.get('match'), caller_file=spec.get('caller'))
    elif kind == 'zones':        # inst.sampler(zones=..., lazy=True): the files found now
        from .. import kits as _kits
        zones = []
        for i, z in enumerate(spec['zones']):
            z = dict(z)
            if not str(z['file']).startswith('*'):
                z['file'] = _kits.resolve(z['file'], spec.get('caller'), f"sampler zones[{i}]").as_posix()
            zones.append(z)
        info = {'zones': len(zones)}
    else:
        raise ComposeError(f"unknown lazy instrument kind {kind!r}")
    return zones, info


# Sampler params for SFZ instruments: the SFZ envelope defaults (attack 0, sustain 100 %, a short release) for zones
# that set no ampeg_* of their own, and room for layered / pedalled / multi-mic voices.
_SFZ_DEFAULTS = {'attack': 0.0, 'decay': 0.001, 'sustain': 1.0, 'release': 0.025, 'polyphony': 128}


fx = _Factory(FX)
inst = _InstFactory(Instrument)


# -------------------------------------------------------------------------------------- patch

_NAME_RE = re.compile(r'^[a-z0-9_.+-]+(/[a-z0-9_.+-]+)*$')


class Patch:
    """A named sound: instrument + insert fx + mix defaults (gain_db, pan, sends) + usage notes.
    Immutable in practice: every modifier returns a deep copy.
    audition: optional hint for `python -m agentsound audition` (see agentsound/cli.py), e.g.
    {'notes': 'riser', 'automate': {'instrument.cutoff': [[0, 200], [16, 8000, 'exp']]}}."""

    __slots__ = ('name', 'instrument', 'fx', 'gain_db', 'pan', 'sends', 'notes', 'audition')

    def __init__(self, name: str, instrument=None, fx=(), gain_db: float = 0.0, pan: float = 0.0,
                 sends: dict | None = None, notes: str = '', audition: dict | None = None):
        if not isinstance(name, str) or not _NAME_RE.match(name):
            raise ComposeError(f"patch name {name!r} must be lowercase 'category/name' (a-z 0-9 _ . + -)")
        self.name = name
        self.instrument = None if instrument is None else Instrument.coerce(instrument)
        self.fx = [FX.coerce(f) for f in (fx or ())]
        self.gain_db = float(gain_db)
        self.pan = float(pan)
        if not -1.0 <= self.pan <= 1.0:
            raise ComposeError(f"patch {name!r}: pan must be -1..1, got {pan}")
        self.sends = {_ref(k): float(v) for k, v in (sends or {}).items()}
        self.notes = str(notes)
        if audition is not None and not isinstance(audition, dict):
            raise ComposeError(f"patch {name!r}: audition must be a dict such as {{'notes': 'riser', 'automate': {{...}}}}, "
                               f"got {audition!r}")
        self.audition = copy.deepcopy(audition) if audition else None

    @property
    def is_chain(self) -> bool:
        """True for fx-only patches (bus / master chains)."""
        return self.instrument is None

    @classmethod
    def layered(cls, name: str, *layers, fx=(), gain_db: float = 0.0, pan: float = 0.0, sends: dict | None = None,
                notes: str = '', audition: dict | None = None, **stack_params) -> 'Patch':
        """A patch whose instrument is a stack of layers (patch names, Patches, Instruments or layer(...)):
            Patch.layered('synthwave/piano_glass_lead',
                          layer('sampled/piano_lead', 'piano'),
                          layer('synthwave/dx_bells', 'glass', transpose=12, level=-11, bend=False),
                          fx=[fx.compressor(threshold=-16)], sends={'hall': -14}, notes='...')
        A patch layer brings its instrument and its fx chain (as the layer's fx), its gain_db adds to the layer level;
        `fx` is the stack's own chain (after the layers are summed) and the sends are the whole stack's."""
        return cls(name, _InstFactory(Instrument).stack(*layers, **stack_params), fx=fx, gain_db=gain_db, pan=pan,
                   sends=sends, notes=notes, audition=audition)

    def layer(self, which, **params) -> 'Patch':
        """Copy of a layered patch with one layer changed: .layer('glass', level=-8, transpose=24) (same as
        .but(**{'layers.glass.level': -8, ...}))."""
        if self.instrument is None or self.instrument.type != 'stack':
            raise ComposeError(f"patch {self.name!r} is not layered (its instrument is not a stack)")
        return self.but(**{f"layers.{which}.{_key(k)}": v for k, v in params.items()})

    def copy(self) -> 'Patch':
        return Patch(self.name, self.instrument, [f.copy() for f in self.fx], self.gain_db, self.pan,
                     dict(self.sends), self.notes, self.audition)

    def but(self, **params) -> 'Patch':
        """Copy with instrument params overridden: .but(cutoff=3000, **{'filter.res': 0.4}).
        On an fx-only patch the params go to its first effect (use .but_fx(type, ...) to pick one)."""
        p = self.copy()
        if p.instrument is not None:
            p.instrument = p.instrument.but(**params)
        elif p.fx:
            p.fx[0] = p.fx[0].but(**params)
        else:
            raise ComposeError(f"patch {self.name!r} has neither instrument nor fx to modify")
        return p

    def with_mods(self, *routes, replace: bool = False) -> 'Patch':
        """Copy with va modulation routes added to the instrument's matrix (a route with the id of an existing
        one replaces it; replace=True drops the patch's own routes first):
        patches.get('synthwave/warm_pad').with_mods(vamod.lfo('sine', rate=8, mode='global') >> ('cutoff', 0.5)).
        Only an amount to change: .but(**{'mod.<id>.amount': x})."""
        p = self.copy()
        if p.instrument is None:
            raise ComposeError(f"patch {self.name!r} is an fx chain; with_mods() needs a 'va' instrument patch")
        p.instrument = p.instrument.with_mods(*routes, replace=replace)
        return p

    def but_fx(self, which, **params) -> 'Patch':
        """Copy with params of ONE insert effect changed; `which` = index, fx type or fx name:
        patches.get('bus/hall').but_fx('reverb', decay=4.0)."""
        p = self.copy()
        i = _fx_index(p.fx, which, f"patch {self.name!r}")
        p.fx[i] = p.fx[i].but(**params)
        return p

    def with_fx(self, *effects, first: bool = False, replace: bool = False) -> 'Patch':
        """Copy with effects appended (first=True: prepended; replace=True: the chain is replaced)."""
        p = self.copy()
        new = [FX.coerce(f) for f in effects]
        p.fx = new if replace else (new + p.fx if first else p.fx + new)
        return p

    def with_mix(self, gain_db: float | None = None, pan: float | None = None, sends: dict | None = None) -> 'Patch':
        """Copy with mix defaults changed (sends are merged; a value of None removes that send)."""
        p = self.copy()
        if gain_db is not None:
            p.gain_db = float(gain_db)
        if pan is not None:
            if not -1.0 <= pan <= 1.0:
                raise ComposeError(f"pan must be -1..1, got {pan}")
            p.pan = float(pan)
        for k, v in (sends or {}).items():
            if v is None:
                p.sends.pop(_ref(k), None)
            else:
                p.sends[_ref(k)] = float(v)
        return p

    def named(self, name: str) -> 'Patch':
        p = self.copy()
        if not _NAME_RE.match(name):
            raise ComposeError(f"patch name {name!r} must be lowercase 'category/name'")
        p.name = name
        return p

    def to_dict(self) -> dict:
        d = {'name': self.name, 'instrument': None if self.instrument is None else self.instrument.to_dict(),
             'fx': [f.to_dict() for f in self.fx], 'gain_db': self.gain_db, 'pan': self.pan,
             'sends': dict(self.sends), 'notes': self.notes}
        if self.audition:
            d['audition'] = copy.deepcopy(self.audition)
        return d

    def __eq__(self, other) -> bool:
        return isinstance(other, Patch) and self.to_dict() == other.to_dict()

    __hash__ = None

    def __repr__(self) -> str:
        what = self.instrument.type if self.instrument else 'fx chain'
        return f"Patch({self.name!r}, {what}, {len(self.fx)} fx)"


# ----------------------------------------------------------------------------------- registry

_REGISTRY: dict[str, Patch] = {}
_loaded = False


def register(patch: Patch, replace: bool = False) -> Patch:
    """Add a patch to the registry (library modules call this at import). Returns the patch."""
    if not isinstance(patch, Patch):
        raise ComposeError(f"register() takes a Patch, got {patch!r}")
    if patch.name in _REGISTRY and not replace:
        raise ComposeError(f"patch {patch.name!r} is already registered (pass replace=True to override)")
    _REGISTRY[patch.name] = patch.copy()
    return patch


def load_library() -> None:
    """Import every module under agentsound/patches/ once (they register their patches)."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    for mod in pkgutil.walk_packages(__path__, prefix=__name__ + '.'):
        importlib.import_module(mod.name)


def has(name: str) -> bool:
    load_library()
    return name in _REGISTRY


def get(name: str) -> Patch:
    """A copy of a registered patch: patches.get('synthwave/supersaw_lead')."""
    load_library()
    if name not in _REGISTRY:
        close = difflib.get_close_matches(str(name), builtins.list(_REGISTRY), n=5, cutoff=0.4)
        hint = f"; did you mean {', '.join(repr(c) for c in close)}?" if close else ''
        avail = '' if _REGISTRY else ' (the registry is empty: no sound library is installed yet)'
        raise ComposeError(f"unknown patch {name!r}{hint}{avail} - list them with `python -m agentsound patches`")
    return _REGISTRY[name].copy()


def list(prefix: str = '') -> builtins.list[str]:  # noqa: A001 - part of the public API: patches.list()
    """Sorted names of registered patches starting with `prefix`."""
    load_library()
    return sorted(n for n in _REGISTRY if n.startswith(prefix))


def describe(name: str) -> str:
    """One-paragraph human description of a patch."""
    p = get(name)
    kind = f"{p.instrument.type} instrument" if p.instrument else 'fx chain'
    if p.instrument is not None and p.instrument.type == 'stack':
        def one(x) -> str:
            ps = ', '.join(f"{k} {v:g}" for k, v in x.params.items())
            fxs = f", fx {'+'.join(f.type for f in x.fx)}" if x.fx else ''
            return f"{x.id}: {x.source or x.instrument.type}" + (f" ({ps}{fxs})" if ps or fxs else '')
        kind = 'stack of ' + '; '.join(one(x) for x in p.instrument.params['layers'])
    fxs = ', '.join(f.type for f in p.fx) or 'none'
    sends = ', '.join(f"{k} {v:+g} dB" for k, v in p.sends.items()) or 'none'
    mods = p.instrument.params.get('mods') if p.instrument else None
    routes = ('\n  mods: ' + '\n        '.join(_vamod.describe(mods).splitlines())) if mods else ''
    return f"{p.name}: {kind}; fx: {fxs}; gain {p.gain_db:+g} dB, pan {p.pan:+g}; sends: {sends}{routes}\n  {p.notes}".rstrip()
