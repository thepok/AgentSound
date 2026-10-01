"""Silent notes, compile-time ear: notes that no sample / layer / drum piece of their instrument can sound.

Song.compile() runs check() on every (unmuted) track before rendering and turns the findings into song.warnings plus
the render JSON's "analysis.silentNotes" (the engine repeats them in report.json as 'silent_notes' warnings, next to
what the render-time ear measured: engine/analysis/SilentNotes.h). A note is silent here when, after the instrument's
transpose, the stack layer ranges and velocity curves and the keyswitch articulation active at its time:
  - sampler (inst.sampler zones / inst.kit / inst.sfz / sampled patches): no zone covers its key and velocity (zones
    with a '*silence' file do not count; with layers='dynamics' any velocity is covered), or its key leaves 0..127;
  - drums (the engine's drum machine): its key is none of the machine's pieces (35-51, 54, 56, 57, 59);
  - stack: no unmuted layer takes it (key / velocity range and fades, as the engine's gainAt), or every layer that
    takes it is silent for it (a sampler child with no zone). Notes that only muted layers take are listed apart.
va, dx7 and sf2 are not checked here (every key sounds; the render-time ear measures them). Keyswitch notes select,
they never sound, and are not counted. The patches' prose 'Range:' notes are playing advice, not limits: the zones are
the machine-readable range. Conservative on purpose: round robins, random layers and trigger conditions count as
covered when any zone of the key could play.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from .theory import note_name

__all__ = ['check', 'DRUM_MACHINE_KEYS', 'key_label', 'fallback_files', 'instrument_info']

DRUM_MACHINE_KEYS = frozenset(range(35, 52)) | {54, 56, 57, 59}
"""Keys the engine's 'drums' instrument plays (engine/instruments/DrumSynth.h); every other key is ignored."""

_MAX_TIMES = 6


# ------------------------------------------------------------------------------------------------ labels

def _gm_names() -> dict:
    from .kits import GM_NAMES
    return GM_NAMES


def key_label(key: int, drum: bool) -> str:
    """'crash (49)' on a drum instrument, 'C#7 (97)' otherwise."""
    if drum:
        name = _gm_names().get(int(key))
        return f"{name} ({key})" if name else f"key {key}"
    return f"{note_name(key)} ({key})" if 0 <= key <= 127 else f"key {key}"


def _bar_beat(beat: float, grid) -> str:
    """1-based 'bar:beat' (quarter-note beats, a tenth: humanized timing does not make 8:4.99 of 9:1)."""
    beat = round(beat * 10.0) / 10.0
    if grid is None:
        bar, pos = divmod(beat, 4.0)
        return f"{int(bar) + 1}:{pos + 1:g}"
    bar = grid.bar_at(beat)
    b0 = math.floor(bar + 1e-9)
    pos = beat - grid.bar_start(b0)
    return f"{b0 + 1}:{round(pos + 1, 1):g}"


# ------------------------------------------------------------------------------------------------ automation

def _lane_value(points: list, beat: float) -> float:
    """The engine's automation lane evaluation (engine/render/Renderer.cpp evaluate())."""
    if beat <= points[0][0]:
        return float(points[0][1])
    if beat >= points[-1][0]:
        return float(points[-1][1])
    for a, b in zip(points, points[1:]):
        if a[0] <= beat < b[0]:
            t = (beat - a[0]) / (b[0] - a[0])
            curve = b[2] if len(b) > 2 else 'linear'
            if curve == 'step':
                return float(a[1])
            if curve == 'smooth':
                return a[1] + (b[1] - a[1]) * (0.5 - 0.5 * math.cos(math.pi * t))
            if curve == 'exp' and a[1] > 0 and b[1] > 0:
                return a[1] * (b[1] / a[1]) ** t
            return a[1] + (b[1] - a[1]) * t
    return float(points[-1][1])


# ------------------------------------------------------------------------------------------------ instruments

def _int(x, default: int = 0) -> int:
    return int(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else default


def _edge(x: float) -> float:
    if x >= 1.0:
        return 1.0
    if x <= 0.0:
        return 0.0
    return math.sin(x * math.pi * 0.5)


def _layer_gain(L: dict, key: int, vel: int) -> float:
    """engine/instruments/Stack.cpp gainAt(): 0 outside the key / velocity range, the equal-power fades inside."""
    klo, khi = _int(L.get('keylo'), 0), _int(L.get('keyhi'), 127)
    vlo, vhi = _int(L.get('vello'), 0), _int(L.get('velhi'), 127)
    if not (klo <= key <= khi and vlo <= vel <= vhi):
        return 0.0
    g = 1.0
    kf, vf = _int(L.get('keyfade'), 0), _int(L.get('velfade'), 0)
    if kf > 0:
        if klo > 0:
            g *= _edge((key - klo) / kf)
        if khi < 127:
            g *= _edge((khi - key) / kf)
    if vf > 0:
        if vlo > 0:
            g *= _edge((vel - vlo) / vf)
        if vhi < 127:
            g *= _edge((vhi - vel) / vf)
    return g


class _Sampler:
    """The zone model of one sampler as far as 'can this note sound' goes."""

    def __init__(self, params: dict):
        s = params.get('samples')
        if isinstance(s, dict) and 'file' in s:
            s = [s]
        self.known = isinstance(s, list) and bool(s)   # {'dir': ...} maps files by name in the engine: unknown here
        self.zones = [z for z in (s if self.known else []) if isinstance(z, dict)]
        self.transpose = _int(params.get('transpose'), 0)
        self.any_vel = params.get('layers') == 'dynamics'
        self.sw_keys: set[int] = set()
        self.last_keys: set[int] = set()
        self.default = None
        for z in self.zones:
            last = z.get('swLast')
            if last is not None:
                ks = [last] if isinstance(last, (int, float)) else range(int(last[0]), int(last[1]) + 1)
                self.sw_keys.update(int(k) for k in ks)
                self.last_keys.update(int(k) for k in ks)
            if z.get('swDown') is not None:
                self.sw_keys.add(int(z['swDown']))
            if z.get('swLo') is not None and z.get('swHi') is not None:
                self.sw_keys.update(range(int(z['swLo']), int(z['swHi']) + 1))
            if self.default is None and z.get('swDefault') is not None:
                self.default = int(z['swDefault'])
        self.has_down = any(z.get('swDown') is not None for z in self.zones)
        self.sounding = [z for z in self.zones if z.get('file') != '*silence']
        # a drum kit: unpitched one-shots (inst.kit writes pitchKeytrack 0; SFZ kits pitch_keytrack=0) - note names
        # would mislead, GM names help. (One zone per key alone says nothing: choirs / pianos are sampled per key.)
        self.drumlike = bool(self.zones) and sum(
            1 for z in self.zones if z.get('pitchKeytrack', 100) == 0) >= 0.8 * len(self.zones)

    @staticmethod
    def _selected(z: dict, last, down) -> bool:
        """engine switchOk(): the zone's sw_last range holds the last keyswitch (none played and no default: a zone
        with sw_last never plays), its sw_down key is held. last='any' / down=None: not tracked (any articulation)."""
        sl = z.get('swLast')
        if sl is not None and last != 'any':
            lo, hi = (sl, sl) if isinstance(sl, (int, float)) else (sl[0], sl[1])
            if last is None or not lo <= last <= hi:
                return False
        sd = z.get('swDown')
        return sd is None or down is None or sd in down

    def why_silent(self, pitch: int, vel: int, last='any', down=None) -> str | None:
        """None when a zone can sound the note, else the reason: 'range', 'velocity' or 'articulation'. last: the
        last keyswitch key (None: none yet), down: the held keyswitch keys; 'any' / None = not tracked."""
        if not self.known:
            return None
        k = pitch + self.transpose
        if not 0 <= k <= 127:
            return 'range'
        on_key = [z for z in self.sounding if z.get('lo', 0) <= k <= z.get('hi', 127)]
        if not on_key:
            return 'range'
        on_vel = on_key if self.any_vel else [z for z in on_key if z.get('vello', 0) <= vel <= z.get('velhi', 127)]
        if not on_vel:
            return 'velocity'
        if not any(self._selected(z, last, down) for z in on_vel):
            return 'articulation'
        return None

    def key_span(self) -> tuple[int, int] | None:
        """The zones' key coverage in played keys (before the transpose param)."""
        if not self.sounding:
            return None
        return (min(z.get('lo', 0) for z in self.sounding) - self.transpose,
                max(z.get('hi', 127) for z in self.sounding) - self.transpose)


def _child_why(child: dict, pitch: int, vel: int, cache: dict) -> str | None:
    t = child.get('type')
    if t == 'sampler':
        smp = cache.setdefault(id(child), _Sampler(child.get('params') or {}))
        if pitch in smp.sw_keys:
            return 'keyswitch'
        # (keyswitch notes reach the child through the stack too; not followed here: its default, else any articulation)
        return smp.why_silent(pitch, vel, smp.default if smp.default is not None else 'any')
    if t == 'drums':
        return None if pitch in DRUM_MACHINE_KEYS else 'range'
    return None


def _auto_lanes(automation) -> dict:
    return {a.get('target'): a.get('points') for a in (automation or [])
            if isinstance(a, dict) and isinstance(a.get('points'), list) and a.get('points')}


# ------------------------------------------------------------------------------------------------ the check

def check(tid: str, inst: dict, notes: list, automation=None, grid=None, info: dict | None = None) -> list[dict]:
    """Findings for one track: [{'track', 'kind' ('no_sound' | 'muted_layers'), 'pitches', 'count', 'beats',
    'message'}]. inst: the render JSON instrument (zones expanded, before pruning); notes: the render JSON notes
    [start, dur, pitch, vel] incl. keyswitch notes; automation: the track's render JSON lanes (a layer's mute lane
    is followed); grid: the song's MeterGrid (bar:beat positions); info: the Instrument's info (inst.kit's mapping:
    GM names, the pack for a fix)."""
    t = inst.get('type')
    params = inst.get('params') or {}
    lanes = _auto_lanes(automation)
    silent: list[tuple[float, int, int, str]] = []   # (beat, pitch, vel, reason)
    muted_only: list[tuple[float, int, int, list]] = []
    drum = t == 'drums'
    span = None
    muted_ids: set = set()
    if t == 'sampler':
        smp = _Sampler(params)
        if not smp.known:
            return []
        drum = bool(info and info.get('kit')) or smp.drumlike
        span = smp.key_span()
        last = smp.default
        down: dict[int, float] = {}    # held swDown keys -> note end
        for n in notes:
            start, dur, p, v = float(n[0]), float(n[1]), int(n[2]), int(n[3])
            if p in smp.sw_keys:
                if p in smp.last_keys:
                    last = p
                down[p] = start + dur
                continue
            held = frozenset(k for k, e in down.items() if e > start + 1e-9) if smp.has_down else None
            why = smp.why_silent(p, v, last, held)
            if why:
                silent.append((start, p, v, why))
    elif t == 'drums':
        for n in notes:
            if int(n[2]) not in DRUM_MACHINE_KEYS:
                silent.append((float(n[0]), int(n[2]), int(n[3]), 'range'))
    elif t == 'stack':
        layers = [L for L in (params.get('layers') or []) if isinstance(L, dict)]
        cache: dict = {}
        kids = [L.get('instrument') or {} for L in layers]
        drum = any(k.get('type') == 'drums' for k in kids) or any(
            k.get('type') == 'sampler' and _Sampler(k.get('params') or {}).drumlike for k in kids)
        for n in notes:
            start, p, v = float(n[0]), int(n[2]), int(n[3])
            key = max(0, min(127, p))
            takers, mutes, keyswitch, reasons = [], [], False, []
            for i, L in enumerate(layers):
                if _layer_gain(L, key, v) <= 1e-4:
                    continue
                q = p + _int(L.get('transpose'), 0)
                if not 0 <= q <= 127:
                    reasons.append('range')
                    continue
                w = v
                vc, vs = float(L.get('velcurve', 1.0)), float(L.get('velscale', 1.0))
                if vc != 1.0 or vs != 1.0:
                    x = min(1.0, max(1.0 / 127.0, (max(v, 0) / 127.0) ** vc * vs))
                    w = max(1, min(127, round(x * 127.0)))
                why = _child_why(kids[i], q, w, cache)
                if why == 'keyswitch':
                    keyswitch = True
                    continue
                lid = str(L.get('id', i))
                lane = lanes.get(f'instrument.layers.{lid}.mute')
                muted = (_lane_value(lane, start) >= 0.5) if lane else bool(L.get('mute'))
                if why:
                    reasons.append(why)
                elif muted:
                    mutes.append(lid)
                else:
                    takers.append(lid)
            if keyswitch or takers:
                continue
            if mutes:
                muted_only.append((start, p, v, mutes))
                muted_ids.update(mutes)
            else:
                silent.append((start, p, v, reasons[0] if reasons else 'layers'))
        spans = []
        for i, L in enumerate(layers):
            if kids[i].get('type') == 'sampler':
                sp = _Sampler(kids[i].get('params') or {}).key_span()
                if sp:
                    tr = _int(L.get('transpose'), 0)
                    spans.append((max(sp[0] - tr, _int(L.get('keylo'), 0)), min(sp[1] - tr, _int(L.get('keyhi'), 127))))
            else:
                spans.append((_int(L.get('keylo'), 0), _int(L.get('keyhi'), 127)))
        span = (min(a for a, _ in spans), max(b for _, b in spans)) if spans else None
    else:
        return []
    out = []
    if silent:
        out.append(_finding(tid, 'no_sound', silent, grid, drum, span, params, info, t))
    if muted_only:
        out.append(_finding(tid, 'muted_layers', [(b, p, v, 'muted') for b, p, v, _ in muted_only], grid, drum, span,
                            params, info, t, muted_ids))
    return out


def _finding(tid, kind, items, grid, drum, span, params, info, itype, muted_ids=()) -> dict:
    by_key: dict[int, list] = {}
    for b, p, v, why in items:
        by_key.setdefault(p, []).append((b, v, why))
    keys = sorted(by_key, key=lambda k: (-len(by_key[k]), k))
    beats = sorted(b for b, _, _, _ in items)
    times = ', '.join(_bar_beat(b, grid) for b in beats[:_MAX_TIMES]) + (f" (+{len(beats) - _MAX_TIMES} more)"
                                                                          if len(beats) > _MAX_TIMES else '')
    shown = keys[:6]
    n = len(items)
    if len(keys) == 1:
        what = f"{n} note{'s' if n != 1 else ''} on {key_label(keys[0], drum)}"
    else:
        what = f"{n} notes (" + ', '.join(f"{len(by_key[k])} on {key_label(k, drum)}" for k in shown)
        if len(keys) > len(shown):
            what += f" and {sum(len(by_key[k]) for k in keys[len(shown):])} on {len(keys) - len(shown)} more keys"
        what += ')'
    kit_path = (info or {}).get('kit', {}).get('path') if isinstance((info or {}).get('kit'), dict) else None
    reasons = {w for _, _, _, w in items}
    if kind == 'muted_layers':
        ids = ', '.join(f"'{x}'" for x in sorted(muted_ids))
        msg = (f"'{tid}': {what} reach{'es' if n == 1 else ''} only muted stack layers ({ids}) at {times}; "
               f"fix: unmute the layer (layer(..., mute=False) or its 'layers.<id>.mute' lane) or widen another layer's "
               f"key / velocity range to take them")
    else:
        where = ('in this kit' if drum and itype != 'drums' else "on the engine's drum machine" if itype == 'drums'
                 else 'on this instrument')
        cause = []
        if 'range' in reasons:
            if drum:
                cause.append((f"kit '{Path(kit_path).name}'" if kit_path else 'the kit')
                             + f" has no sample on {'that key' if len(keys) == 1 else 'these keys'}")
            elif span:
                cause.append(f"its samples cover {note_name(max(0, span[0]))}-{note_name(min(127, span[1]))} "
                             f"({span[0]}-{span[1]}) only")
            else:
                cause.append('no zone on that key')
        if 'velocity' in reasons:
            vs = sorted({v for _, _, v, w in items if w == 'velocity'})
            cause.append(f"no zone for velocit{'y' if len(vs) == 1 else 'ies'} {vs[0]}"
                         + (f"-{vs[-1]}" if len(vs) > 1 else '') + " on the key")
        if 'articulation' in reasons:
            cause.append('the keyswitch articulation active then has no zone on the key')
        if 'layers' in reasons:
            cause.append('no stack layer takes the key / velocity (keylo / keyhi / vello / velhi and their fades)')
        msg = (f"'{tid}': {what} reach{'es' if n == 1 else ''} no sample {where} "
               f"({'; '.join(cause)}) at {times}; fix: {_fix(drum, itype, keys, span, info, reasons)}")
    return {'track': tid, 'kind': kind, 'pitches': sorted(by_key), 'count': n,
            'beats': [round(b, 6) for b in beats[:32]], 'message': msg}


def _fix(drum: bool, itype: str, keys: list, span, info, reasons: set) -> str:
    if drum:
        from .kits import ROLE_KEYS
        role_of = {k: r for r, ks in ROLE_KEYS.items() for k in ks}
        roles = [role_of.get(k) for k in keys if role_of.get(k)]
        names = [_gm_names().get(k, str(k)) for k in keys[:3]]
        text = (f"map {', '.join(names)} to a sample (inst.kit(..., map={{'{names[0]}': '<file>'}})) or layer a kit "
                f"that has {'it' if len(names) == 1 else 'them'}")
        pack = (info or {}).get('kit', {}).get('path') if isinstance((info or {}).get('kit'), dict) else None
        cands = fallback_files(pack, roles[0]) if pack and roles else []
        if cands:
            text += f" - this pack has {roles[0]} samples: {', '.join(repr(c) for c in cands)}"
        if itype == 'drums':
            text = "play the machine's keys (35-51, 54, 56, 57, 59) or use a sampled kit that has the piece"
        return text + "; a drummer part: arrange it with kit=<this track> so it plays the kit's fallback pieces"
    if 'range' in reasons and span:
        lo, hi = min(keys), max(keys)
        shift = 12 if hi < span[0] else -12 if lo > span[1] else 0
        return ("move the notes into the range" + (f" (track.play(..., transpose={shift:+d}))" if shift else '')
                + " or use an instrument that reaches them")
    if 'velocity' in reasons:
        return "play them at velocities the zones cover (or layers='dynamics' on a dynamics-layered sampler)"
    if 'articulation' in reasons:
        return "switch to an articulation that has these keys, or move the notes"
    return "widen a layer's key / velocity range (layer(..., keys=(lo, hi), vel=(lo, hi))) so one takes them"


def instrument_info(ins) -> dict | None:
    """The Instrument's info (what inst.kit / inst.sfz found) for check(); a stack: its first layer built by inst.kit."""
    if ins is None:
        return None
    if getattr(ins, 'type', None) == 'stack':
        for x in ins.params.get('layers') or []:
            info = getattr(x.instrument, 'info', None)
            if info and info.get('kit'):
                return info
        return None
    return getattr(ins, 'info', None)


_PACK_CACHE: dict = {}


def fallback_files(kit_path, role: str, limit: int = 2) -> list[str]:
    """Files of the pack that holds a kit folder whose names say `role` (kits.classify), as 'samples/...' paths for
    inst.kit(map=...): the same pack's other kits often have the missing piece (80s pop kit A: no cymbals, kit C: two
    crashes). [] when the pack is not installed."""
    try:
        from .kits import _audio_files, _samples_dir, classify
        root = Path(str(kit_path))
        pack = None
        for p in [root, *root.parents]:
            if (p / 'SOURCE.json').is_file():
                pack = p
                break
        if pack is None:
            return []
        if pack not in _PACK_CACHE:
            found: dict[str, list[Path]] = {}
            for f in _audio_files(pack):
                rel = f.relative_to(pack)
                r, _, _ = classify(f.stem, tuple(reversed(rel.parts[:-1])))
                if r:
                    found.setdefault(r, []).append(f)
            _PACK_CACHE[pack] = found
        files = [f for f in _PACK_CACHE[pack].get(role, []) if not _within(f, root)]
        out = []
        base = _samples_dir()
        for f in files[:limit]:
            try:
                out.append('samples/' + f.relative_to(base).as_posix())
            except ValueError:
                out.append(f.as_posix())
        return out
    except (OSError, ValueError):
        return []


def _within(f: Path, root: Path) -> bool:
    try:
        return os.path.commonpath([str(f), str(root)]) == str(root)
    except ValueError:
        return False
