"""SFZ import: the format of most free multisample libraries, turned into 'sampler' zones.

    inst.sfz('samples/salamander-grand/SalamanderGrandPianoV3.sfz')                  # a sampled instrument
    inst.sfz('samples/meatbass/Programs/04_pizz.sfz', cc={107: 0})                   # CC-selected layers
    inst.sfz('samples/vpo-scripts-standard/Strings/1st-violin-SEC-KS-C2.sfz', articulation='staccato')
    inst.sfz('samples/swirly-drums/Programs/Basic_kit.sfz', mics={'wet': -6})       # multi-mic kits
    sfz.articulations(path), sfz.mics(path), sfz.summary(path)
    python -m agentsound sfz FILE.sfz [--json] [--cc 64=127] [--articulation NAME] [--pitch]

What happens (docs/COMPOSE_API.md "SFZ instruments"): the file is parsed (<control> <global> <master> <group>
<region> inheritance, #define $VARS, #include, default_path, <curve>), every region is evaluated at fixed MIDI
controller values (`cc=`, else the file's set_ccN, else 0: CC conditions pick layers, CC modulations become static
values, CC crossfades static gains), microphones set or muted, and each region becomes one zone of the engine's
'sampler' (docs/RENDER_FORMAT.md). Two things stay LIVE (docs/COMPOSE_API.md "Realistic performance"):
  - the dynamics controller (dyn_cc='auto': CC1, else CC11, when the file maps crossfades, volume / amplitude,
    cutoff or layer conditions to it): its crossfades (xfin/xfout_lo/hiccN), gain (volume/gain/amplitude_onccN),
    cutoff (cutoff_onccN) and layer conditions (lo/hiccN) become the zone fields xfinLoDyn.., dynGain, dynCutoff,
    dynLo/dynHi driven by the sampler's automatable 'dynamics' param (set to the controller's value, so the default
    sound is the static one); dyn_cc=None evaluates it statically like the others;
  - keyswitch articulations (sw_last / sw_lolast..hilast / sw_down / sw_lokey..hikey / sw_default): every
    articulation is imported and the engine switches them with keyswitch notes (the song compiler inserts them for
    notes with an articulation: clip.articulate('staccato')); articulation='name' picks one statically instead.
Nothing is ignored silently: opcodes the engine cannot do are counted (`info['unsupported']`; `strict=True`
raises), opcodes that are inactive at these controller values or have no audible effect in a render are listed
separately, and approximations are named.

Paths: 'samples/<pack>/...' is looked up in $AGENTSOUND_SAMPLES (else assets/samples), './' / '../' next to the
song, absolute paths as they are; zones get absolute paths. Sample files: case-insensitive lookup, backslashes,
.flac/.ogg/.aif(f) fall back to the converted .wav of the downloader, VPO scripts find their samples in the
'vpo-wav' pack. Missing files are a ComposeError naming them.
"""

from __future__ import annotations

import math
import os
import re
import struct
from collections import Counter
from pathlib import Path

from .theory import ComposeError

__all__ = ['load', 'parse', 'articulations', 'mics', 'summary', 'resolve_path', 'SfzFile', 'CURVE_DEFAULTS',
           'hammers', 'HAMMER_BANDS', 'even_velcurve', 'apply_velcurve', 'check_velcurve']

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / 'assets'

# Packs whose SFZ scripts reference samples that live in another pack ('../libs/SSO/...' -> vpo-wav/libs/SSO/...).
COMPANION_PACKS = {'vpo-scripts-standard': ['vpo-wav'], 'vpo-scripts-performance': ['vpo-wav']}

# Engine limits (docs/RENDER_FORMAT.md, sampler zones).
_GAIN_MIN_DB = -144.0
_KNOWN_HEADERS = {'region', 'group', 'master', 'global', 'control', 'curve', 'effect', 'midi', 'sample'}


def _samples_dir() -> Path:
    from .library import SAMPLES
    return SAMPLES


# ------------------------------------------------------------------------------------------------ paths

def resolve_path(path, caller_file: str | None = None, what: str = 'sfz') -> Path:
    """An existing .sfz file: 'samples/<pack>/...' in the sample library, './' / '../' next to the caller (a song),
    absolute, or relative to assets/."""
    if isinstance(path, os.PathLike):
        path = os.fspath(path)
    if not isinstance(path, str) or not path.strip():
        raise ComposeError(f"{what}: the path must be a non-empty string, got {path!r}")
    text = path.strip().replace('\\', '/')
    cands: list[Path] = []
    if text.startswith(('./', '../')):
        if not caller_file:
            raise ComposeError(f"{what}: {text!r} is relative to the song file, but the caller has no __file__")
        cands.append(Path(os.path.dirname(os.path.abspath(caller_file))) / text)
    elif os.path.isabs(text):
        cands.append(Path(text))
    elif text.startswith('samples/'):
        cands += [_samples_dir() / text[len('samples/'):], ASSETS / text]
    else:
        cands += [ASSETS / text, _samples_dir() / text]
    for c in cands:
        if c.is_file():
            return Path(os.path.normpath(c))
    hint = ''
    if text.startswith('samples/'):
        pack = text.split('/')[1] if text.count('/') >= 1 else ''
        pdir = _samples_dir() / pack
        if pack and not (pdir / 'SOURCE.json').is_file():
            hint = f"; pack {pack!r} is not installed: python -m agentsound samples fetch {pack}"
        elif pack:
            sfz = sorted(p.relative_to(pdir).as_posix() for p in pdir.rglob('*.sfz'))[:12]
            hint = f"; .sfz files in {pack}: {', '.join(sfz) or 'none'}"
    raise ComposeError(f"{what}: {text!r} not found (looked at {', '.join(str(c) for c in cands)}){hint}")


class _CaseFinder:
    """Case-insensitive, extension-tolerant lookup of sample files (SFZ files are often written on Windows)."""

    def __init__(self):
        self._dirs: dict[str, dict[str, str] | None] = {}

    def _listing(self, d: str) -> dict[str, str] | None:
        key = os.path.normcase(d)
        if key not in self._dirs:
            try:
                self._dirs[key] = {n.lower(): n for n in os.listdir(d)}
            except OSError:
                self._dirs[key] = None
        return self._dirs[key]

    def exact(self, path: str, refreshed: bool = False) -> str | None:
        """The on-disk spelling of `path` (absolute, normalized) or None."""
        path = os.path.normpath(path)
        drive, rest = os.path.splitdrive(path)
        parts = [p for p in rest.replace('\\', '/').split('/') if p]
        cur = drive + os.sep if drive or rest.startswith(('/', '\\')) else ''
        for part in parts:
            listing = self._listing(cur or '.')
            real = None if listing is None else listing.get(part.lower())
            if real is None:
                if not refreshed and os.path.exists(path):  # the folder changed since it was listed
                    self._dirs.clear()
                    return self.exact(path, True)
                return None
            cur = os.path.join(cur, real) if cur else real
        return cur if os.path.isfile(cur) else None

    def find(self, path: str) -> str | None:
        hit = self.exact(path)
        if hit:
            return hit
        root, ext = os.path.splitext(path)
        if ext.lower() in ('.flac', '.ogg', '.aif', '.aiff', '.wv', '.mp3'):
            # the downloader converted these to WAV ('x.flac' -> 'x.wav', or 'x.flac.wav' when 'x.wav' existed)
            for alt in (path + '.wav', root + '.wav', root + '.WAV'):
                hit = self.exact(alt)
                if hit:
                    return hit
        return None


# ------------------------------------------------------------------------------------------------ parsing

_NOTE_RE = re.compile(r'^([a-gA-G])([#b]?)(-?\d{1,2})$')
_PCS = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
_TOKEN_RE = re.compile(r'<\s*(\w+)\s*>|(?:(?<=\s)|^|(?<=>))([A-Za-z0-9_]+)=')
_VAR_RE = re.compile(r'\$([A-Za-z0-9_]+)')
# '#define $NAME value' (one token), '#include "file"', or any other '#word' at a token start (a problem)
_DIRECTIVE_RE = re.compile(r'(?:(?<=\s)|^)#define\s+\$([A-Za-z0-9_]+)\s+(\S+)|(?:(?<=\s)|^)#include\s+"([^"]+)"|'
                           r'(?:(?<=\s)|^)#[A-Za-z]+')
_STATE = '\x00control'   # key of a region's <control> state (default_path, note_offset, octave_offset)


class _Unit:
    """One header block of the parsed file: kind + opcodes [(name, value, origin)]."""
    __slots__ = ('kind', 'ops', 'origin')

    def __init__(self, kind: str, origin: str):
        self.kind, self.ops, self.origin = kind, [], origin


class SfzFile:
    """A parsed .sfz file: regions (merged opcodes), control opcodes, curves and what could not be read."""

    def __init__(self, path: Path):
        self.path = path
        self.dir = path.parent
        self.regions: list[tuple[dict[str, str], str]] = []   # (merged opcodes, origin 'file:line')
        self.control: dict[str, str] = {}
        self.curves: dict[int, list[float]] = {}
        self.includes: list[Path] = []
        self.headers = Counter()          # header kind -> count
        self.effects: list[dict[str, str]] = []
        self.problems: list[str] = []     # parse-level warnings (undefined variables, bad includes, ...)
        self.defines: dict[str, str] = {}


def _read_text(p: Path) -> str:
    data = p.read_bytes()
    for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode('latin-1', errors='replace')


def _strip_comments(text: str) -> list[str]:
    """Lines without // and /* */ comments (whichever starts first wins; block comments keep the line count)."""
    out: list[str] = []
    in_block = False
    for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        kept = []
        i = 0
        while i < len(line):
            if in_block:
                j = line.find('*/', i)
                if j < 0:
                    i = len(line)
                    break
                i = j + 2
                in_block = False
                continue
            sl, bl = line.find('//', i), line.find('/*', i)
            if sl >= 0 and (bl < 0 or sl <= bl):
                kept.append(line[i:sl])
                break
            if bl >= 0:
                kept.append(line[i:bl])
                i = bl + 2
                in_block = True
                continue
            kept.append(line[i:])
            break
        out.append(' '.join(kept))
    return out


def parse(path) -> SfzFile:
    """Parse an .sfz file (cached per path and modification time)."""
    p = Path(path)
    try:
        key = (str(p.resolve()), p.stat().st_mtime_ns)
    except OSError:
        raise ComposeError(f"sfz: cannot read {p}") from None
    hit = _PARSE_CACHE.get(key)
    if hit is None:
        hit = _Parser(p).run()
        _PARSE_CACHE[key] = hit
    return hit


_PARSE_CACHE: dict[tuple, SfzFile] = {}


class _Parser:
    def __init__(self, main: Path):
        self.doc = SfzFile(main)
        self.units: list[_Unit] = []
        self.cur: _Unit | None = None

    def run(self) -> SfzFile:
        self._file(self.doc.path, 0, [])
        self._build()
        return self.doc

    def _expand(self, s: str, where: str) -> str:
        defs = self.doc.defines
        if '$' not in s:
            return s

        def sub(m: re.Match) -> str:
            name = m.group(1)
            if name in defs:
                return defs[name]
            for k in range(len(name) - 1, 0, -1):  # longest defined prefix: '$KEYa' with $KEY defined
                if name[:k] in defs:
                    return defs[name[:k]] + name[k:]
            self.doc.problems.append(f"{where}: undefined variable ${name}")
            return m.group(0)
        return _VAR_RE.sub(sub, s)

    def _file(self, p: Path, depth: int, stack: list[Path]) -> None:
        if depth > 16 or p in stack:
            self.doc.problems.append(f"#include loop or depth > 16 at {p}")
            return
        try:
            text = _read_text(p)
        except OSError as e:
            self.doc.problems.append(f"cannot read {p}: {e}")
            return
        rel = os.path.relpath(p, self.doc.dir)
        for lineno, line in enumerate(_strip_comments(text), 1):
            where = f"{rel}:{lineno}"
            if not line.strip():
                continue
            # directives may stand anywhere in a line ('<region> #define $KEY 21 lokey=21 #include "x.txt"'): the
            # text between them is expanded with the variables defined so far
            pos = 0
            for d in _DIRECTIVE_RE.finditer(line):
                if d.start() > pos:
                    self._line(self._expand(line[pos:d.start()], where), where)
                pos = d.end()
                if d.group(1) is not None:          # #define $NAME value (one token)
                    self.doc.defines[d.group(1)] = self._expand(d.group(2), where)
                elif d.group(3) is not None:        # #include "file"
                    self._include(p, d.group(3), depth, stack, where)
                else:
                    self.doc.problems.append(f"{where}: malformed or unknown directive {d.group(0)[:40]!r}")
            if pos < len(line):
                self._line(self._expand(line[pos:], where), where)

    def _include(self, p: Path, name: str, depth: int, stack: list[Path], where: str) -> None:
        inc = self._expand(name, where).replace('\\', '/')
        target = None
        for base in (self.doc.dir, p.parent):  # relative to the main file (SFZ), else to the including one
            c = _FINDER.exact(os.path.normpath(os.path.join(base, inc)))
            if c:
                target = Path(c)
                break
        if target is None:
            self.doc.problems.append(f"{where}: #include \"{inc}\" not found")
            return
        self.doc.includes.append(target)
        self._file(target, depth + 1, stack + [p])

    def _line(self, line: str, where: str) -> None:
        toks = list(_TOKEN_RE.finditer(line))
        for i, t in enumerate(toks):
            if t.group(1) is not None:
                kind = t.group(1).lower()
                self.cur = _Unit(kind, where)
                self.units.append(self.cur)
                continue
            end = toks[i + 1].start() if i + 1 < len(toks) else len(line)
            value = line[t.end():end].strip()
            if self.cur is None:
                self.cur = _Unit('global', where)
                self.units.append(self.cur)
            self.cur.ops.append((t.group(2).lower(), value, where))  # opcodes are lower case ('Sample=' happens)

    def _build(self) -> None:
        doc = self.doc
        levels = {'global': {}, 'master': {}, 'group': {}}
        order = ['global', 'master', 'group']
        # <control> settings apply to the regions that follow them: several default_path blocks in one file
        # (VSCO 2 keyswitch programs, No Budget Orchestra) each serve the regions after them
        state = {'default_path': '', 'note_offset': '0', 'octave_offset': '0'}
        for u in self.units:
            doc.headers[u.kind] += 1
            if u.kind == 'region':
                merged = {}
                for lv in order:
                    merged.update(levels[lv])
                for name, value, _ in u.ops:
                    merged[name] = value
                merged[_STATE] = dict(state)
                doc.regions.append((merged, u.origin))
            elif u.kind in levels:
                i = order.index(u.kind)
                for lv in order[i:]:
                    levels[lv] = {}
                for name, value, _ in u.ops:
                    levels[u.kind][name] = value
            elif u.kind == 'control':
                for name, value, _ in u.ops:
                    doc.control[name] = value
                    if name in state:
                        state[name] = value
            elif u.kind == 'curve':
                pts, idx = {}, None
                for name, value, where in u.ops:
                    if name == 'curve_index':
                        idx = _int(value)
                    elif re.fullmatch(r'v\d{1,3}', name):
                        pts[int(name[1:])] = _float(value)
                if idx is None:
                    doc.problems.append(f"{u.origin}: <curve> without curve_index")
                    continue
                doc.curves[idx] = _curve_table(pts)
            elif u.kind == 'effect':
                doc.effects.append({n: v for n, v, _ in u.ops})
            # <midi>, <sample> and unknown headers: counted in doc.headers (reported as unsupported)


def _float(v) -> float | None:
    try:
        x = float(str(v).strip().split()[0])
    except (ValueError, IndexError):
        return None
    return x if math.isfinite(x) else None


def _int(v) -> int | None:
    x = _float(v)
    return None if x is None else int(round(x))


def _curve_table(pts: dict[int, float | None]) -> list[float]:
    """128 values of a <curve> (vNNN points, linear in between; v000 = 0 and v127 = 1 unless given)."""
    known = {k: v for k, v in pts.items() if v is not None and 0 <= k <= 127}
    known.setdefault(0, 0.0)
    known.setdefault(127, 1.0)
    xs = sorted(known)
    out = []
    for x in range(128):
        for a, b in zip(xs, xs[1:]):
            if a <= x <= b:
                t = 0.0 if b == a else (x - a) / (b - a)
                out.append(known[a] + t * (known[b] - known[a]))
                break
    return out


def _predefined_curve(idx: int) -> list[float] | None:
    x = [i / 127.0 for i in range(128)]
    if idx == 0:
        return x
    if idx == 1:
        return [2 * v - 1 for v in x]
    if idx == 2:
        return [1 - v for v in x]
    if idx == 3:
        return [1 - 2 * v for v in x]
    if idx == 4:
        return [v * v for v in x]
    if idx == 5:
        return [math.sqrt(v) for v in x]
    if idx == 6:
        return [math.sqrt(1 - v) for v in x]
    return None


CURVE_DEFAULTS = {i: _predefined_curve(i) for i in range(7)}


def _note(v, offset: int = 0) -> int | None:
    """SFZ note value: MIDI number or name (c4 = 60, c#4, db4, C-1 = 0), plus note/octave offsets."""
    s = str(v).strip()
    if not s:
        return None
    x = _float(s)
    if x is not None and re.fullmatch(r'-?\d+(\.0*)?', s.split()[0]):
        return int(round(x)) + offset
    m = _NOTE_RE.match(s.split()[0])
    if not m:
        return None
    pc = _PCS[m.group(1).lower()] + {'#': 1, 'b': -1, '': 0}[m.group(2)]
    return 12 * (int(m.group(3)) + 1) + pc + offset


_FINDER = _CaseFinder()


# ------------------------------------------------------------------------------------------------ WAV headers

_WAV_INFO: dict[str, dict | None] = {}


def wav_info(path: str) -> dict | None:
    """frames / rate / channels of a WAV (header only, cached); None if unreadable."""
    if path in _WAV_INFO:
        return _WAV_INFO[path]
    info = None
    try:
        with open(path, 'rb') as f:
            head = f.read(12)
            if head[:4] in (b'RIFF', b'RF64') and head[8:12] == b'WAVE':
                align = 0
                rate = channels = 0
                while True:
                    h = f.read(8)
                    if len(h) < 8:
                        break
                    cid, size = h[:4], struct.unpack('<I', h[4:])[0]
                    if cid == b'fmt ':
                        b = f.read(size)
                        channels, rate = struct.unpack('<HI', b[2:8])
                        align = struct.unpack('<H', b[12:14])[0]
                        if size & 1:
                            f.read(1)
                        continue
                    if cid == b'data':
                        total = os.path.getsize(path) - f.tell()
                        if size in (0, 0xFFFFFFFF) or size > total:
                            size = total
                        info = {'frames': size // align if align else 0, 'rate': rate, 'channels': channels}
                        break
                    f.seek(size + (size & 1), 1)
    except OSError:
        info = None
    _WAV_INFO[path] = info
    return info


# ------------------------------------------------------------------------------------------------ opcodes

# Opcodes with no audible effect in an offline render with fixed controllers (labels, UI hints, pitch-wheel ranges,
# MIDI routing and envelope-update flags): accepted and listed as 'no effect here', never counted as unsupported.
_INERT = re.compile(r'^(?:.*_label|label_cc\d+|hint_.*|bend_up|bend_down|bend_step|bend_smooth|ampeg_dynamic|fileg_dynamic|'
                    r'pitcheg_dynamic|sustain_cc|sustain_lo|sostenuto_sw|sostenuto_cc|sostenuto_lo|output|image|'
                    r'.*_smoothcc\d+|.*_stepcc\d+|sample_quality|xf_cccurve|note_selfmask|sw_vel|master_label|'
                    r'global_label|group_label|region_label|param_offset|set_hdcc\d+|set_cc\d+|default_path|note_offset|'
                    r'octave_offset|curve_index|v\d{1,3}|define|sample_fadeout|amp_velcurve_\d+)$')

_CC_MOD = re.compile(r'^(.*?)_?(oncc|cc|curvecc|smoothcc|stepcc)(\d+)$')
_LFO = re.compile(r'^lfo(\d+)_(.+)$')
_EG = re.compile(r'^eg(\d+)_(.+)$')

# Canonical target names of CC-modulated opcodes ('ampeg_attackcc100' and 'ampeg_attack_oncc100' are the same).
_TARGET_ALIAS = {'gain': 'volume', 'pitch': 'tune', 'loopstart': 'loop_start', 'loopend': 'loop_end', 'offby': 'off_by',
                 'loopmode': 'loop_mode'}

# Targets whose static value the importer computes (base opcode default, additive unless noted).
_BASES = {
    'volume': 0.0, 'amplitude': 100.0, 'pan': 0.0, 'width': 100.0, 'tune': 0.0, 'offset': 0.0, 'delay': 0.0,
    'amp_veltrack': 100.0, 'cutoff': None, 'resonance': 0.0, 'ampeg_delay': 0.0, 'ampeg_attack': 0.0, 'ampeg_hold': 0.0,
    'ampeg_decay': 0.0, 'ampeg_sustain': 100.0, 'ampeg_release': 0.0, 'ampeg_start': 0.0,
    'pitchlfo_depth': 0.0, 'pitchlfo_freq': 0.0, 'pitchlfo_delay': 0.0, 'pitchlfo_fade': 0.0,
    'amplfo_depth': 0.0, 'amplfo_freq': 0.0, 'amplfo_delay': 0.0, 'amplfo_fade': 0.0,
    'fillfo_depth': 0.0, 'fileg_depth': 0.0, 'pitcheg_depth': 0.0, 'fil_veltrack': 0.0, 'fil_keytrack': 0.0,
    'eq1_gain': 0.0, 'eq2_gain': 0.0, 'eq3_gain': 0.0, 'eq1_freq': 50.0, 'eq2_freq': 500.0, 'eq3_freq': 5000.0,
    'eq1_bw': 1.0, 'eq2_bw': 1.0, 'eq3_bw': 1.0, 'position': 0.0,
}


class _Ctx:
    """Controller state for evaluating regions statically."""

    def __init__(self, doc: SfzFile, cc: dict | None):
        # MIDI power-on values (as sfizz and the SoundFont player): volume 100, pan centre, expression full
        self.values: dict[int, float] = {7: 100.0 / 127.0, 10: 64.0 / 127.0, 11: 1.0}   # 0..1
        self.source: dict[int, str] = {7: 'MIDI default', 10: 'MIDI default', 11: 'MIDI default'}
        for name, v in doc.control.items():
            m = re.fullmatch(r'set_(hd)?cc(\d+)', name)
            x = _float(v)
            if m and x is not None:
                n = int(m.group(2))
                self.values[n] = min(1.0, max(0.0, x if m.group(1) else x / 127.0))
                self.source[n] = 'set_cc'
        for n, v in (cc or {}).items():
            if isinstance(n, str) and n.isdigit():
                n = int(n)
            if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 511:
                raise ComposeError(f"sfz: cc keys must be controller numbers 0..511, got {n!r}")
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 127:
                raise ComposeError(f"sfz: cc[{n}] must be a value 0..127, got {v!r}")
            self.values[n] = float(v) / 127.0
            self.source[n] = 'cc='
        self.curves = doc.curves
        self.missing_curves: set[int] = set()

    def x(self, n: int, key: float, vel: float) -> float:
        """Normalized value (0..1, bipolar sources -1..1) of controller n for a region (per-note sources at the
        region's key / velocity centre)."""
        if n == 131:
            return vel / 127.0
        if n == 133:
            return key / 127.0
        if n == 128:   # pitch bend: bipolar, centre 0 (cc={128: 64} is the centre too)
            if 128 not in self.values:
                return 0.0
            v = self.values[128] * 127.0 - 64.0
            return max(-1.0, min(1.0, v / (63.0 if v > 0 else 64.0)))
        if n == 134:
            return 1.0
        if n == 135:
            return 0.5
        if n == 136:
            return 0.0
        return self.values.get(n, 0.0)

    def curve(self, idx: int | None, x: float) -> float:
        if idx is None or idx == 0:
            return x
        table = self.curves.get(idx) or CURVE_DEFAULTS.get(idx)
        if table is None:
            self.missing_curves.add(idx)
            return x
        pos = min(1.0, max(0.0, x)) * 127.0
        i = min(126, int(pos))
        t = pos - i
        return table[i] + t * (table[i + 1] - table[i])


class _Region:
    """Opcode access for one merged region: canonical names, CC modulations and curves, bookkeeping of what was
    used."""

    def __init__(self, ops: dict[str, str], origin: str):
        self.origin = origin
        self.note_offset = _note_offset(ops)
        self.default_path = (ops.get(_STATE) or {}).get('default_path', '') or ''
        self.ops: dict[str, str] = {}
        self.mods: dict[str, dict[int, float]] = {}    # target -> {cc: amount}
        self.mcurves: dict[str, dict[int, int]] = {}   # target -> {cc: curve index}
        self.used: set[str] = set()
        self.names: dict[str, str] = {}                # canonical -> original opcode name
        self.mics: list[str] = []
        for name, value in ops.items():
            if name == _STATE:
                continue
            original = name
            name = re.sub(r'^(lfo|eg)0*(\d+)_', r'\1\2_', name)       # lfo01_ = lfo1_, eg06_ = eg6_
            name = re.sub(r'_lfo0*(\d+)_', r'_lfo\1_', name)
            m = _CC_MOD.match(name)
            if m and not re.match(r'^(lo|hi|on_lo|on_hi|start_lo|start_hi|stop_lo|stop_hi|set_|set_hd|label_|xfin_lo|xfin_hi|'
                                  r'xfout_lo|xfout_hi|lohd|hihd)', name):
                target, kind, n = m.group(1), m.group(2), int(m.group(3))
                target = _TARGET_ALIAS.get(target, target)
                amount = _float(value)
                if kind in ('smoothcc', 'stepcc'):  # smoothing / stepping of a controller: no effect at fixed values
                    self.ops[name] = value
                    self.names[name] = original
                    continue
                if kind == 'curvecc':
                    idx = _int(value)
                    if idx is not None:
                        self.mcurves.setdefault(target, {})[n] = idx
                elif amount is not None:
                    self.mods.setdefault(target, {})[n] = self.mods.get(target, {}).get(n, 0.0) + amount
                self.names[target] = original
                continue
            canon = _TARGET_ALIAS.get(name, name)
            self.ops[canon] = value
            self.names[canon] = original

    def has(self, name: str) -> bool:
        return name in self.ops

    def raw(self, name: str) -> str | None:
        if name in self.ops:
            self.used.add(name)
            return self.ops[name]
        return None

    def num(self, name: str, default=None):
        v = self.raw(name)
        if v is None:
            return default
        x = _float(v)
        return default if x is None else x

    def note(self, name: str, default=None):
        v = self.raw(name)
        if v is None:
            return default
        k = _note(v, self.note_offset)
        return default if k is None else k


# ------------------------------------------------------------------------------------------------ evaluation

class _Import:
    """One load(): regions -> zones at the given controllers, articulation and microphones."""

    def __init__(self, doc: SfzFile, cc, articulation, mic_gains, strict: bool, mic_map, dyn_cc: int | None = None,
                 live_sw: bool = False, sw_default: int | None = None):
        self.doc = doc
        self.ctx = _Ctx(doc, cc)
        self.articulation = articulation
        self.dyn_cc = dyn_cc              # the controller played live by the sampler's 'dynamics' param (None: static)
        self.live_sw = live_sw            # keyswitches switched live (every articulation imported)
        self.sw_default = sw_default
        self.dyn_timbre = False           # the dynamics controller crossfades layers or moves a filter
        self.mic_gains = mic_gains or {}
        self.mic_map = mic_map or {}
        self.strict = strict
        self.unsupported = Counter()     # opcode (or 'opcode=value') -> regions
        self.inactive = Counter()        # modulation opcodes that are 0 at these controllers
        self.inert = Counter()           # accepted, no audible effect here
        self.approx = Counter()          # evaluated approximately
        self.skipped = Counter()         # reason -> regions
        self.missing: list[str] = []
        self.missing_rel: list[str] = []   # the same, as written in the file (default_path + sample)
        self.zones: list[dict] = []

    # --- static controller evaluation
    def value(self, r: _Region, target: str, key: float, vel: float, base=None, live: bool = False):
        """Base opcode (or `base`) + sum of its CC modulations (additive targets). live=True leaves out the
        dynamics controller (played live by the sampler)."""
        b = r.num(target, _BASES.get(target) if base is None else base)
        mods = r.mods.get(target)
        if not mods:
            return b
        total = 0.0 if b is None else b
        for n, amount in mods.items():
            if live and n == self.dyn_cc:
                continue
            x = self.ctx.x(n, key, vel)
            total += amount * self.ctx.curve(r.mcurves.get(target, {}).get(n), x)
            if n in (131, 133, 135, 136):
                self.approx[f"{target}_oncc{n} (per-note controller, taken at the region's "
                            f"{'velocity' if n == 131 else 'key' if n == 133 else 'mean random value'})"] += 1
        return total

    def amplitude(self, r: _Region, key: float, vel: float, live: bool = False) -> float:
        """Amplitude factor: amplitude% x product of its CC modulations (each a % at the controller's value).
        live=True leaves out the dynamics controller."""
        a = r.num('amplitude', 100.0) / 100.0
        for n, amount in (r.mods.get('amplitude') or {}).items():
            if live and n == self.dyn_cc:
                continue
            x = self.ctx.x(n, key, vel)
            a *= amount / 100.0 * self.ctx.curve(r.mcurves.get('amplitude', {}).get(n), x)
            if n in (131, 133):
                self.approx[f"amplitude_oncc{n} (per-note controller, taken at the region's centre)"] += 1
        for lvl in ('global_amplitude', 'master_amplitude', 'group_amplitude'):
            a *= r.num(lvl, 100.0) / 100.0
        return a

    def vel_slope(self, r: _Region, target: str, key: float, lo: int, hi: int) -> float:
        """Velocity tracking of a target modulated by CC 131 (note-on velocity): the linear change from the region's
        lowest to highest velocity, per unit velocity/127 (SFZ vel2* semantics)."""
        m = (r.mods.get(target) or {}).get(131)
        if not m or hi <= lo:
            return 0.0
        c = r.mcurves.get(target, {}).get(131)
        f = lambda v: m * self.ctx.curve(c, v / 127.0)  # noqa: E731
        return (f(hi) - f(lo)) / ((hi - lo) / 127.0)

    # --- one region
    def region(self, ops: dict, origin: str) -> None:
        r = _Region(ops, origin)
        r.mics = self.mic_map.get(id(ops)) or []
        skip = self._select(r)
        if skip:
            self.skipped[skip] += 1
            return
        zone = self._zone(r)
        if zone is None:
            return
        self._account(r)
        self.zones.append(zone)

    def _select(self, r: _Region) -> str | None:
        """Why this region never plays with these settings (None: it may play)."""
        for name in list(r.ops):
            if name.startswith(('on_locc', 'on_hicc', 'on_lohdcc', 'on_hihdcc', 'start_locc', 'start_hicc')):
                return 'triggered by a controller (on_locc / on_hicc: pedal or CC noises), not by notes'
        lochan, hichan = r.num('lochan', 1), r.num('hichan', 16)
        if not lochan <= 1 <= hichan:
            return 'MIDI channel condition (lochan / hichan) excludes channel 1'
        loprog, hiprog = r.num('loprog', 0), r.num('hiprog', 127)
        if not loprog <= 0 <= hiprog:
            return 'program condition (loprog / hiprog) excludes program 0'
        for name, value in r.ops.items():
            m = re.fullmatch(r'(lo|hi)(hd)?cc(\d+)', name)
            if not m:
                continue
            n = int(m.group(3))
            if n in (131, 133, 135):
                continue  # per-note: become velocity / key / random ranges in _zone
            if n == self.dyn_cc:
                continue  # the dynamics controller: a live condition (dynLo / dynHi) in _zone
            r.used.add(name)
            x = _float(value)
            if x is None:
                continue
            v = self.ctx.x(n, 60, 64) * (1.0 if m.group(2) else 127.0)
            lim = x if m.group(2) else x
            if (m.group(1) == 'lo' and v < lim - 1e-9) or (m.group(1) == 'hi' and v > lim + 1e-9):
                return f"controller condition {name}={value} (cc{n} = {v:g})"
        # keyswitches
        sw_last = r.note('sw_last')
        sw_down = r.note('sw_down')
        sw_lolast, sw_hilast = r.note('sw_lolast'), r.note('sw_hilast')
        r.note('sw_lokey')
        r.note('sw_hikey')
        r.note('sw_default')
        r.raw('sw_label')
        if r.has('sw_up'):
            r.used.add('sw_up')
        if r.has('sw_previous'):
            self.approx['sw_previous (previous-note switch: always on)'] += 1
            r.used.add('sw_previous')
        if self.live_sw:
            return None   # every articulation: the engine switches them live (swLast / swDown in _zone)
        cur = self.articulation
        for k in (sw_last, sw_down):
            if k is not None and k != cur:
                return 'another keyswitch articulation'
        if sw_lolast is not None or sw_hilast is not None:
            lo = sw_lolast if sw_lolast is not None else 0
            hi = sw_hilast if sw_hilast is not None else 127
            if cur is None or not lo <= cur <= hi:
                return 'another keyswitch articulation'
        return None

    def _zone(self, r: _Region) -> dict | None:
        doc = self.doc
        z: dict = {}
        # --- key / velocity ranges
        key = r.note('key')
        lo = r.note('lokey', key if key is not None else 0)
        hi = r.note('hikey', key if key is not None else 127)
        lovel, hivel = r.num('lovel', 0), r.num('hivel', 127)
        # conditions on per-note controllers: 131 = note-on velocity, 133 = key -> ranges
        for n in (131, 133):
            for side in ('lo', 'hi'):
                for hd in ('', 'hd'):
                    v = r.num(f"{side}{hd}cc{n}")
                    if v is None or lo is None or hi is None:
                        continue
                    v = v * 127.0 if hd else v
                    if n == 131:
                        lovel, hivel = (max(lovel, v), hivel) if side == 'lo' else (lovel, min(hivel, v))
                    else:
                        lo, hi = (max(lo, int(math.ceil(v))), hi) if side == 'lo' else (lo, min(hi, int(v)))
        lorand, hirand = r.num('lorand', 0.0), r.num('hirand', 1.0)
        for side in ('lo', 'hi'):
            v = r.num(f"{side}cc135")
            if v is not None:
                lorand, hirand = (max(lorand, v / 127.0), hirand) if side == 'lo' else (lorand, min(hirand, v / 127.0))
        if lo is None or hi is None or lo < 0 or hi < 0 or lo > 127:
            self.skipped['never triggered by a key (lokey / hikey / key = -1)'] += 1
            return None
        lo, hi = max(0, int(lo)), min(127, int(hi))
        lovel, hivel = max(0, int(round(lovel))), min(127, int(round(hivel)))
        if lo > hi or lovel > hivel or hivel < 1:   # notes have velocities 1..127
            self.skipped['empty key or velocity range'] += 1
            return None
        lorand, hirand = max(0.0, lorand), min(1.0, hirand)
        if lorand >= hirand:
            self.skipped['empty random range (lorand >= hirand)'] += 1
            return None
        kc = (lo + hi) / 2.0
        vc = (lovel + hivel) / 2.0
        # --- sample
        sample = r.raw('sample')
        if sample is None or not sample.strip():
            self.skipped['no sample'] += 1
            return None
        sample = sample.strip().strip('"')
        if sample.startswith('*'):
            gen = sample.lower()
            if gen not in ('*silence', '*sine', '*noise'):
                self.unsupported[f"sample={sample} (generator)"] += 1
                self.skipped[f"unsupported generator {sample}"] += 1
                return None
            z['file'] = gen
        else:
            base = os.path.join(str(self.doc.dir), r.default_path.replace('\\', '/'))
            full = os.path.normpath(os.path.join(base, sample.replace('\\', '/')))
            found = _FINDER.find(full) or self._companion(full) or self._samples_folder(r.default_path, sample)
            if not found:
                self.missing.append(full)
                self.missing_rel.append(os.path.join(r.default_path, sample).replace('\\', '/'))
                return None
            z['file'] = found.replace('\\', '/')
        z['lo'], z['hi'] = lo, hi
        if lovel > 1:
            z['vello'] = lovel
        if hivel < 127:
            z['velhi'] = hivel
        if lorand > 0:
            z['lorand'] = round(lorand, 6)
        if hirand < 1:
            z['hirand'] = round(hirand, 6)
        # --- keyswitches (live)
        if self.live_sw:
            sw_last, sw_down = r.note('sw_last'), r.note('sw_down')
            sw_lolast, sw_hilast = r.note('sw_lolast'), r.note('sw_hilast')
            sw_lo, sw_hi = r.note('sw_lokey'), r.note('sw_hikey')
            if sw_last is not None and 0 <= sw_last <= 127:
                z['swLast'] = sw_last
            elif sw_lolast is not None or sw_hilast is not None:
                a, b = (sw_lolast if sw_lolast is not None else 0), (sw_hilast if sw_hilast is not None else 127)
                z['swLast'] = [min(127, max(0, a)), min(127, max(0, b))]
            if sw_down is not None and 0 <= sw_down <= 127:
                z['swDown'] = sw_down
            if sw_lo is not None and sw_hi is not None and 0 <= sw_lo <= sw_hi <= 127:
                z['swLo'], z['swHi'] = sw_lo, sw_hi
            if ('swLast' in z or 'swDown' in z) and self.sw_default is not None:
                z['swDefault'] = self.sw_default
        # --- pitch
        pk = r.raw('pitch_keycenter')
        if pk is not None and pk.strip().lower() == 'sample':
            if not z['file'].startswith('*'):
                z['root'] = 'sample'
        else:
            root = r.note('pitch_keycenter', key if key is not None else 60)
            if root is None or not 0 <= root <= 127:
                self.approx[f"pitch_keycenter={pk} (outside 0..127: clamped)"] += 1
                root = min(127, max(0, root if root is not None else 60))
            z['root'] = root
        tune = self.value(r, 'tune', kc, vc) + 100.0 * r.num('transpose', 0.0)
        for lvl in ('global_tune', 'master_tune', 'group_tune'):
            tune += r.num(lvl, 0.0)
        if tune:
            z['tune'] = round(max(-9600.0, min(9600.0, tune)), 4)
        kt = r.num('pitch_keytrack', 100.0)
        if kt != 100.0:
            z['pitchKeytrack'] = max(-1200.0, min(1200.0, kt))
        pr = r.num('pitch_random', 0.0)
        if pr > 0:
            z['pitchRandom'] = min(9600.0, pr)
        if r.has('pitch_veltrack') and r.num('pitch_veltrack', 0.0) != 0:
            self.unsupported['pitch_veltrack'] += 1
        # --- level (the dynamics controller's part stays live: dynGain / xf..Dyn)
        live = self.dyn_cc is not None
        amp = self.amplitude(r, kc, vc, live=live)
        vol = self.value(r, 'volume', kc, vc, live=live)
        for lvl in ('global_volume', 'master_volume', 'group_volume'):
            vol += r.num(lvl, 0.0)
        xf = self._cc_crossfade(r, kc, vc)
        if live:
            self._dynamics(r, z, kc, vc)
        mic = self._mic_gain(r, z)
        if mic is None:
            self.skipped['microphone excluded by mics='] += 1
            return None
        if amp <= 0 or xf <= 0:
            self.skipped['silent at these controller values (amplitude / crossfade 0)'] += 1
            return None
        gain = vol + 20.0 * math.log10(amp * xf) + mic + z.pop('gain', 0.0)
        if gain < _GAIN_MIN_DB:
            self.skipped['silent at these controller values (amplitude / crossfade 0)'] += 1
            return None
        if abs(gain) > 1e-9:
            z['gain'] = round(min(48.0, gain), 4)
        ar = r.num('amp_random', 0.0)
        if ar > 0:
            z['ampRandom'] = min(48.0, ar)
        vt = self.value(r, 'amp_veltrack', kc, vc)
        if abs(vt - 100.0) > 1e-9:
            if vt < -100 or vt > 100:
                self.approx[f"amp_veltrack={vt:g} (clamped to -100..100)"] += 1
            z['ampVeltrack'] = round(max(-1.0, min(1.0, vt / 100.0)), 6)
        curve = {}
        for name in list(r.ops):
            m = re.fullmatch(r'amp_velcurve_(\d+)', name)
            if m:
                g = _float(r.raw(name))
                if g is not None and 0 <= int(m.group(1)) <= 127:
                    curve[int(m.group(1))] = max(0.0, min(4.0, g))
        if curve:
            z['velcurve'] = [[v, round(curve[v], 6)] for v in sorted(curve)]
        pan = self.value(r, 'pan', kc, vc)
        if pan:
            z['pan'] = round(max(-1.0, min(1.0, pan / 100.0)), 6)
        width = self.value(r, 'width', kc, vc)
        if abs(width - 100.0) > 1e-9:
            if width < 0:
                self.approx['width < 0 (channel swap: played as |width|)'] += 1
            z['width'] = round(min(2.0, abs(width) / 100.0), 6)
        if r.has('position') and r.num('position', 0.0) != 0:
            self.unsupported['position'] += 1
        # --- crossfades
        for sfz_name, key_name in (('xfin_lovel', 'xfinLo'), ('xfin_hivel', 'xfinHi'), ('xfout_lovel', 'xfoutLo'),
                                   ('xfout_hivel', 'xfoutHi'), ('xfin_lokey', 'xfinLoKey'), ('xfin_hikey', 'xfinHiKey'),
                                   ('xfout_lokey', 'xfoutLoKey'), ('xfout_hikey', 'xfoutHiKey')):
            v = r.note(sfz_name) if sfz_name.endswith('key') else r.num(sfz_name)
            if v is not None:
                z[key_name] = min(127, max(0, int(round(v))))
        for a, b in (('xfinLo', 'xfinHi'), ('xfoutLo', 'xfoutHi'), ('xfinLoKey', 'xfinHiKey'), ('xfoutLoKey', 'xfoutHiKey')):
            if a in z or b in z:
                la = z.get(a, 0 if 'in' in a else 127)
                lb = z.get(b, 0 if 'in' in b else 127)
                if la > lb:
                    z[a], z[b] = lb, la
        for sfz_name, key_name in (('xf_velcurve', 'xfVelCurve'), ('xf_keycurve', 'xfKeyCurve')):
            v = r.raw(sfz_name)
            if v is not None:
                v = v.strip().lower()
                if v in ('power', 'gain'):
                    z[key_name] = v
                else:
                    self.unsupported[f"{sfz_name}={v}"] += 1
        # --- playback: loops, offsets, triggers
        mode = r.raw('loop_mode')
        loop = {'no_loop': 'none', 'one_shot': 'oneshot', 'loop_continuous': 'forward', 'loop_sustain': 'sustain',
                None: None}.get(mode.strip().lower() if mode else None, 'bad')
        alias = {'continuous': 'forward', 'sustain': 'sustain', 'oneshot': 'oneshot', 'noloop': 'none'}
        if loop == 'bad' and mode.strip().lower() in alias:   # non-standard spellings seen in packs
            loop = alias[mode.strip().lower()]
            self.approx[f"loop_mode={mode.strip()} (non-standard spelling: read as {loop})"] += 1
        if loop == 'bad':
            self.unsupported[f"loop_mode={mode}"] += 1
            loop = None
        ltype = r.raw('loop_type') or r.raw('looptype')
        if ltype is not None and ltype.strip().lower() in ('alternate', 'backward'):
            if ltype.strip().lower() == 'alternate' and loop in ('forward', None):
                loop = 'pingpong'
            else:
                self.unsupported[f"loop_type={ltype.strip()}"] += 1
        ls, le = r.num('loop_start'), r.num('loop_end')
        if loop is None and (ls is not None or le is not None):
            loop = 'forward'
        if z['file'].startswith('*'):
            loop = None if loop != 'oneshot' else 'oneshot'
            ls = le = None
        if loop in ('forward', 'sustain', 'pingpong') and (ls is not None or le is not None):
            info = wav_info(z['file'])
            frames = info['frames'] if info else None
            s0 = max(0, int(ls)) if ls is not None else 0
            e0 = int(le) + 1 if le is not None else frames
            if frames is not None:
                e0 = min(e0, frames)
            if e0 is not None and e0 - s0 >= 2:
                z['loopStart'], z['loopEnd'] = s0, e0
            else:
                self.approx['loop_start / loop_end outside the sample (the file loop / whole sample used)'] += 1
        if loop is not None:
            z['loop'] = loop
        elif not z['file'].startswith('*'):
            z['loop'] = 'auto'   # SFZ default: loop when the file has loop points
        offset = self.value(r, 'offset', kc, vc)
        offr = r.num('offset_random', 0.0)
        end = r.num('end')
        if not z['file'].startswith('*'):
            if end is not None and end <= 0:
                self.skipped['end <= 0 (region disabled)'] += 1
                return None
            info = wav_info(z['file']) if (offset > 0 or end is not None or offr > 0) else None
            frames = info['frames'] if info else None
            if end is not None:
                e = int(end) + 1
                if frames is not None and e >= frames:
                    e = None
                if e is not None:
                    z['end'] = e
            limit = z.get('end', frames)
            if offset > 0:
                o = int(offset)
                if limit is not None and o >= limit:
                    self.approx['offset beyond the sample (clamped)'] += 1
                    o = max(0, limit - 2)
                if o > 0:
                    z['offset'] = o
            if offr > 0:
                z['offsetRandom'] = int(offr)
            if 'end' in z and z.get('offset', 0) >= z['end']:
                self.skipped['offset at or beyond end'] += 1
                return None
            if 'end' in z and 'loopEnd' in z and z['loopEnd'] > z['end']:
                z['loopEnd'] = z['end']
                if z['loopEnd'] - z.get('loopStart', 0) < 2:
                    z.pop('loopStart', None)
                    z.pop('loopEnd', None)
        trig = r.raw('trigger')
        if trig is not None:
            t = trig.strip().lower()
            if t in ('release', 'release_key', 'first', 'legato'):
                z['trigger'] = t
            elif t != 'attack':
                self.unsupported[f"trigger={t}"] += 1
                self.skipped[f"trigger={t} not supported"] += 1
                return None
        rt = r.num('rt_decay', 0.0)
        if rt > 0 and z.get('trigger') in ('release', 'release_key'):
            z['rtDecay'] = min(200.0, rt)
        if r.has('rt_dead') and (r.raw('rt_dead') or '').strip().lower() == 'on':
            self.unsupported['rt_dead=on'] += 1
        # --- round robin, groups
        seql = r.num('seq_length')
        seqp = r.num('seq_position')
        if seql is not None or seqp is not None:
            length = max(1, min(128, int(seql or 1)))
            pos = max(1, min(128, int(seqp or 1)))
            if pos > length:
                self.skipped['seq_position > seq_length (never plays)'] += 1
                return None
            if length > 1:
                z['seqLength'], z['seqPosition'] = length, pos
        grp = r.num('group')
        if grp is not None and int(grp) != 0:
            z['group'] = int(grp)
        ob = r.num('off_by')
        if ob is not None:
            z['offBy'] = int(ob)
        npoly = r.num('note_polyphony')
        if npoly is not None and npoly >= 1:
            z['notePolyphony'] = min(128, int(npoly))
        om = (r.raw('off_mode') or 'fast').strip().lower()
        ot = r.num('off_time')
        if om not in ('fast', 'normal', 'time'):
            self.unsupported[f"off_mode={om}"] += 1
        elif om != 'fast' and ('offBy' in z or 'notePolyphony' in z):  # how this zone's voices are turned off
            z['offMode'] = om
            if om == 'time' and ot is not None:
                z['offTime'] = max(0.0, min(60.0, ot))
        if r.has('off_shape'):
            r.used.add('off_shape')
            if 'offBy' in z or 'notePolyphony' in z:
                self.approx['off_shape (turn-off fades are linear (fast) or the release curve)'] += 1
        poly = r.num('polyphony')
        if poly is not None and poly >= 1:
            z['groupPolyphony'] = min(256, int(poly))   # voice limit of its group (group 0: of this region)
        # --- envelope
        self._envelope(r, z, kc, vc, lovel, hivel)
        if r.raw('sustain_sw') is not None and (r.ops['sustain_sw'] or '').strip().lower() == 'off':
            z['pedal'] = False
        # --- random / delay
        d = self.value(r, 'delay', kc, vc)
        if d > 0:
            z['delay'] = min(100.0, d)
        dr = r.num('delay_random', 0.0)
        if dr > 0:
            z['delayRandom'] = min(100.0, dr)
        # --- filter, EQ, LFOs
        self._filter(r, z, kc, vc, lovel, hivel)
        self._eq(r, z, kc, vc)
        self._lfos(r, z, kc, vc)
        return z

    def _samples_folder(self, default_path: str, sample: str) -> str | None:
        """Programs whose sample paths only resolve in the pack's 'Samples' folder (Karoryfer packs that ship some
        programs without their '../Samples/' default_path, or with an undefined '$sample_dir'): a folder 'Samples' next
        to the .sfz or above it, inside its pack. Counted as an approximation."""
        root = Path(os.path.abspath(str(_samples_dir())))
        rel = os.path.join(re.sub(r'\$[A-Za-z0-9_]+[\\/]?', '', default_path), sample).replace('\\', '/').lstrip('/')
        rel = re.sub(r'^(?:\.\.?/)+', '', rel)
        d = Path(os.path.abspath(str(self.doc.dir)))
        while root in d.parents:   # up to the pack folder
            hit = _FINDER.find(os.path.join(str(d), 'Samples', rel))
            if hit:
                self.approx["sample paths resolved in the pack's Samples/ folder (the file's own paths point elsewhere)"] += 1
                return hit
            d = d.parent
        return None

    def _companion(self, full: str) -> str | None:
        """Samples of VPO scripts live in the vpo-wav pack (their '../libs/...' paths)."""
        samples = str(_samples_dir())
        try:
            rel = os.path.relpath(full, samples).replace('\\', '/')
        except ValueError:
            return None
        pack, _, rest = rel.partition('/')
        for other in COMPANION_PACKS.get(pack, []):
            hit = _FINDER.find(os.path.join(samples, other, rest))
            if hit:
                return hit
        return None

    def _cc_crossfade(self, r: _Region, key: float, vel: float) -> float:
        """Static gain of CC crossfades (xfin_loccN / xfin_hiccN / xfout_...) at the controllers' values."""
        g = 1.0
        power = (r.raw('xf_cccurve') or 'power').strip().lower() != 'gain'
        ccs = set()
        for name in r.ops:
            m = re.fullmatch(r'xf(in|out)_(lo|hi)cc(\d+)', name)
            if m:
                ccs.add((m.group(1), int(m.group(3))))
        for kind, n in ccs:
            if n == self.dyn_cc:
                continue   # live: xfinLoDyn .. (see _dynamics)
            lo = r.num(f"xf{kind}_locc{n}", 0.0 if kind == 'in' else 127.0)
            hi = r.num(f"xf{kind}_hicc{n}", 0.0 if kind == 'in' else 127.0)
            v = self.ctx.x(n, key, vel) * 127.0
            if kind == 'in':
                x = 1.0 if v >= hi else 0.0 if v <= lo else (v - lo) / (hi - lo)
            else:
                x = 1.0 if v <= lo else 0.0 if v >= hi else (hi - v) / (hi - lo)
            g *= math.sqrt(x) if power else x
        return g

    def _dynamics(self, r: _Region, z: dict, kc: float, vc: float) -> None:
        """The dynamics controller's mappings of a region -> live zone fields: crossfades (xfinLoDyn ..), gain curve
        (dynGain: volume / gain / amplitude on the controller, 17 points), layer conditions (dynLo / dynHi)."""
        n = self.dyn_cc
        for kind in ('in', 'out'):
            lo, hi = r.num(f"xf{kind}_locc{n}"), r.num(f"xf{kind}_hicc{n}")
            if lo is None and hi is None:
                continue
            d = 0.0 if kind == 'in' else 127.0
            lo, hi = (d if lo is None else lo), (d if hi is None else hi)
            lo, hi = sorted((min(127, max(0, int(round(lo)))), min(127, max(0, int(round(hi))))))
            z[f"xf{kind}LoDyn"], z[f"xf{kind}HiDyn"] = lo, hi
            self.dyn_timbre = True
        if ('xfinLoDyn' in z or 'xfoutLoDyn' in z) and (r.raw('xf_cccurve') or 'power').strip().lower() == 'gain':
            z['xfDynCurve'] = 'gain'
        vol = (r.mods.get('volume') or {}).get(n)
        amp = (r.mods.get('amplitude') or {}).get(n)
        if vol is not None or amp is not None:
            vc_curve = r.mcurves.get('volume', {}).get(n)
            am_curve = r.mcurves.get('amplitude', {}).get(n)
            pts = []
            for x in list(range(0, 127, 8)) + [127]:
                g = 1.0
                if vol is not None:
                    g *= 10.0 ** (vol * self.ctx.curve(vc_curve, x / 127.0) / 20.0)
                if amp is not None:
                    g *= amp / 100.0 * self.ctx.curve(am_curve, x / 127.0)
                pts.append([x, round(min(16.0, max(0.0, g)), 6)])
            if any(abs(p[1] - pts[0][1]) > 1e-6 for p in pts):
                z['dynGain'] = pts
            elif abs(pts[0][1] - 1.0) > 1e-6:
                z['gain'] = round(z.get('gain', 0.0) + 20.0 * math.log10(max(pts[0][1], 1e-7)), 4)
        for side, key in (('lo', 'dynLo'), ('hi', 'dynHi')):
            v = r.num(f"{side}cc{n}")
            hd = r.num(f"{side}hdcc{n}")
            if hd is not None:
                v = hd * 127.0
            if v is not None:
                z[key] = min(127, max(0, int(math.ceil(v - 1e-9)) if side == 'lo' else int(v)))
        if z.get('dynLo', 0) > z.get('dynHi', 127):
            z.pop('dynLo', None)
            z.pop('dynHi', None)
            self.approx[f"lo/hicc{n} (empty dynamics range: the condition is dropped)"] += 1

    def _mic_gain(self, r: _Region, z: dict):
        """dB offset from mics= (None: excluded)."""
        if not self.mic_gains:
            return 0.0
        names = r.mics or ['main']
        total = 0.0
        for n in names:
            if n in self.mic_gains:
                g = self.mic_gains[n]
                if g is None:
                    return None
                total += g
        return total

    def _envelope(self, r: _Region, z: dict, kc: float, vc: float, lovel: int, hivel: int) -> None:
        names = {'ampeg_delay': 'envDelay', 'ampeg_attack': 'attack', 'ampeg_hold': 'hold', 'ampeg_decay': 'decay',
                 'ampeg_sustain': 'sustain', 'ampeg_release': 'release'}
        for sfz_name, key_name in names.items():
            given = r.has(sfz_name) or sfz_name in r.mods
            if not given:
                continue
            v = self.value(r, sfz_name, kc, vc)
            slope = self.vel_slope(r, sfz_name, kc, lovel, hivel)
            if slope:
                v -= slope * (vc / 127.0)  # the value at velocity 0 + slope x vel/127 (vel2*)
                self.approx[f"{sfz_name}_oncc131 (velocity curve linearized per region)"] += 1
            if sfz_name == 'ampeg_sustain':
                z[key_name] = round(max(0.0, min(1.0, v / 100.0)), 6)
            else:
                z[key_name] = round(max(0.0, min(100.0, v)), 6)
            if slope:
                vk = {'attack': 'velAttack', 'hold': 'velHold', 'decay': 'velDecay', 'sustain': 'velSustain',
                      'release': 'velRelease'}.get(key_name)
                if vk:
                    z[vk] = round(slope / (100.0 if key_name == 'sustain' else 1.0), 6)
        if 'sustain' in z and z['sustain'] < 1.0 and 'decay' not in z:
            z['decay'] = 0.0   # SFZ default decay 0: straight to the sustain level
        for sfz_name, key_name, scale in (('ampeg_vel2attack', 'velAttack', 1.0), ('ampeg_vel2hold', 'velHold', 1.0),
                                          ('ampeg_vel2decay', 'velDecay', 1.0), ('ampeg_vel2sustain', 'velSustain', 100.0),
                                          ('ampeg_vel2release', 'velRelease', 1.0)):
            v = r.num(sfz_name)
            if v:
                z[key_name] = round(z.get(key_name, 0.0) + v / scale, 6)
                base = {'velAttack': 'attack', 'velHold': 'hold', 'velDecay': 'decay', 'velSustain': 'sustain',
                        'velRelease': 'release'}[key_name]
                if base not in z:
                    z[base] = 1.0 if base == 'sustain' else 0.0
        if r.has('ampeg_vel2delay') and r.num('ampeg_vel2delay', 0.0):
            self.unsupported['ampeg_vel2delay'] += 1
        st = self.value(r, 'ampeg_start', kc, vc)
        if st:
            self.unsupported['ampeg_start (initial envelope level)'] += 1
        for shape in ('ampeg_attack_shape', 'ampeg_decay_shape', 'ampeg_release_shape'):
            if r.has(shape) and r.num(shape, 0.0) != 0:
                self.unsupported[f"{shape} (curved envelope segments: played linear / exponential)"] += 1
                r.used.add(shape)
            elif r.has(shape):
                r.used.add(shape)

    def _filter(self, r: _Region, z: dict, kc: float, vc: float, lovel: int, hivel: int) -> None:
        cutoff = r.num('cutoff')
        typ = (r.raw('fil_type') or r.raw('fil1_type') or 'lpf_2p').strip().lower()
        if cutoff is None:
            if 'cutoff' in r.mods:
                self.inactive['cutoff_oncc (no cutoff: no filter)'] += 1
            for extra in ('resonance', 'fil_keytrack', 'fil_keycenter', 'fil_veltrack', 'fil_random'):
                r.raw(extra)
            return
        cents = 0.0
        dyn_cents = 0.0
        for n, amount in (r.mods.get('cutoff') or {}).items():
            if n == 131:
                continue
            if n == self.dyn_cc:   # live: dynCutoff (cents at the controller's top, linear)
                dyn_cents = amount
                if r.mcurves.get('cutoff', {}).get(n):
                    self.approx[f"cutoff_curvecc{n} (the live dynamics cutoff move is linear)"] += 1
                continue
            cents += amount * self.ctx.curve(r.mcurves.get('cutoff', {}).get(n), self.ctx.x(n, kc, vc))
        hz = cutoff * 2.0 ** (cents / 1200.0)
        mapped = {'lpf_1p': 'lpf_1p', 'lpf_2p': 'lpf_2p', 'hpf_1p': 'hpf_1p', 'hpf_2p': 'hpf_2p', 'bpf_2p': 'bpf_2p',
                  'lpf_4p': 'lpf_2p', 'lpf_6p': 'lpf_2p', 'hpf_4p': 'hpf_2p', 'hpf_6p': 'hpf_2p', 'lpf_2p_sv': 'lpf_2p',
                  'hpf_2p_sv': 'hpf_2p', 'bpf_2p_sv': 'bpf_2p', 'bpf_1p': 'bpf_2p'}.get(typ)
        if mapped is None:
            self.unsupported[f"fil_type={typ}"] += 1
            return
        if mapped != typ:
            self.approx[f"fil_type={typ} (played as {mapped})"] += 1
        if mapped != 'lpf_2p':
            z['filter'] = mapped
        z['cutoff'] = round(max(1.0, min(40000.0, hz)), 3)
        if dyn_cents:
            z['dynCutoff'] = round(max(-12000.0, min(12000.0, dyn_cents)), 4)
            self.dyn_timbre = True
        res = self.value(r, 'resonance', kc, vc)
        if res > 0:
            z['resonance'] = round(min(40.0, res), 4)
        kt = self.value(r, 'fil_keytrack', kc, vc)
        if kt:
            z['filKeytrack'] = max(-1200.0, min(1200.0, kt))
            kcen = r.note('fil_keycenter', 60)
            if kcen != 60:
                z['filKeycenter'] = min(127, max(0, kcen))
        else:
            r.raw('fil_keycenter')
        vt = self.value(r, 'fil_veltrack', kc, vc) + self.vel_slope(r, 'cutoff', kc, lovel, hivel)
        if (r.mods.get('cutoff') or {}).get(131):
            self.approx['cutoff_oncc131 (velocity to cutoff linearized per region)'] += 1
        if vt:
            z['filVeltrack'] = round(max(-9600.0, min(9600.0, vt)), 4)
        if r.has('fil_random') and r.num('fil_random', 0.0):
            self.unsupported['fil_random'] += 1
        for extra in ('cutoff2', 'fil2_type', 'resonance2'):
            if r.has(extra):
                self.unsupported[f"{extra} (second filter)"] += 1

    def _eq(self, r: _Region, z: dict, kc: float, vc: float) -> None:
        bands = []
        for i in (1, 2, 3):
            if not any(r.has(f"eq{i}_{k}") or f"eq{i}_{k}" in r.mods for k in ('gain', 'freq', 'bw', 'vel2gain', 'vel2freq')):
                continue
            gain = self.value(r, f"eq{i}_gain", kc, vc)
            freq = self.value(r, f"eq{i}_freq", kc, vc)
            bw = self.value(r, f"eq{i}_bw", kc, vc)
            vg = r.num(f"eq{i}_vel2gain", 0.0)
            vf = r.num(f"eq{i}_vel2freq", 0.0)
            if vg or vf:
                gain += vg * vc / 127.0
                freq += vf * vc / 127.0
                self.approx[f"eq{i}_vel2gain / vel2freq (taken at the region's velocity centre)"] += 1
            if abs(gain) < 0.05:
                if f"eq{i}_gain" in r.mods:
                    self.inactive[f"eq{i}_gain_oncc (0 dB at these controllers)"] += 1
                continue
            bands.append([round(max(10.0, min(24000.0, freq)), 3), round(max(0.01, min(8.0, bw)), 4),
                          round(max(-96.0, min(24.0, gain)), 4)])
        if bands:
            z['eq'] = bands

    def _lfos(self, r: _Region, z: dict, kc: float, vc: float) -> None:
        def lfo(prefix: str):
            depth = self.value(r, f"{prefix}_depth", kc, vc)
            freq = self.value(r, f"{prefix}_freq", kc, vc)
            delay = self.value(r, f"{prefix}_delay", kc, vc)
            fade = self.value(r, f"{prefix}_fade", kc, vc)
            return depth, freq, delay, fade
        d, f, dl, fd = lfo('pitchlfo')
        if d and f > 0:
            z['vibrato'] = [round(max(-1200.0, min(1200.0, d)), 4), round(min(100.0, f), 4), round(min(100.0, dl), 4), round(min(100.0, fd), 4)]
        elif r.has('pitchlfo_depth') or 'pitchlfo_depth' in r.mods:
            self.inactive['pitchlfo_* (vibrato depth / rate 0 at these controllers)'] += 1
        d, f, dl, fd = lfo('amplfo')
        if d and f > 0:
            z['tremolo'] = [round(max(-96.0, min(96.0, d)), 4), round(min(100.0, f), 4), round(min(100.0, dl), 4), round(min(100.0, fd), 4)]
        elif r.has('amplfo_depth') or 'amplfo_depth' in r.mods:
            self.inactive['amplfo_* (tremolo depth / rate 0 at these controllers)'] += 1
        for prefix in ('fillfo',):
            if r.has(f"{prefix}_depth") or f"{prefix}_depth" in r.mods:
                if self.value(r, f"{prefix}_depth", kc, vc):
                    self.unsupported['fillfo_* (filter LFO)'] += 1
                else:
                    self.inactive['fillfo_* (depth 0 at these controllers)'] += 1
        # SFZ v2 LFOs (lfoN_*): a pitch target becomes the vibrato, volume / amplitude the tremolo; any other target
        # with a depth at these controllers is unsupported. Rate / shape fields are not targets.
        rate_fields = ('freq', 'delay', 'fade', 'wave', 'phase', 'count', 'offset', 'ratio', 'scale', 'sub', 'steps',
                       'smooth', 'beats', 'step')
        lfos: dict[str, set[str]] = {}
        for name in list(r.ops) + list(r.mods):
            m = _LFO.match(name)
            if m:
                lfos.setdefault(m.group(1), set()).add(m.group(2))
        for n, fields in sorted(lfos.items()):
            pre = f"lfo{n}"
            freq = self.value(r, f"{pre}_freq", kc, vc, base=0.0)
            delay = self.value(r, f"{pre}_delay", kc, vc, base=0.0)
            fade = self.value(r, f"{pre}_fade", kc, vc, base=0.0)
            wave = r.num(f"{pre}_wave", 1.0)
            for k in list(r.ops):
                if k.startswith(pre + '_'):
                    r.used.add(k)
            for tgt in sorted(fields):
                if tgt.startswith(rate_fields):
                    continue
                depth = self.value(r, f"{pre}_{tgt}", kc, vc, base=0.0)
                label = re.sub(r'\d+', 'N', tgt)
                if not depth or freq <= 0:
                    self.inactive[f"lfoN_{label} (depth or rate 0 at these controllers)"] += 1
                    continue
                if wave not in (0.0, 1.0):
                    self.approx[f"lfoN_wave={wave:g} (played as a sine)"] += 1
                if tgt == 'pitch' and 'vibrato' not in z:
                    z['vibrato'] = [round(max(-1200.0, min(1200.0, depth)), 4), round(min(100.0, freq), 4),
                                    round(min(100.0, delay), 4), round(min(100.0, fade), 4)]
                elif tgt in ('volume', 'amplitude') and 'tremolo' not in z:
                    db = depth if tgt == 'volume' else 20.0 * math.log10(1.0 + min(0.99, abs(depth) / 100.0))
                    z['tremolo'] = [round(max(-96.0, min(96.0, db)), 4), round(min(100.0, freq), 4),
                                    round(min(100.0, delay), 4), round(min(100.0, fade), 4)]
                    if tgt == 'amplitude':
                        self.approx['lfoN_amplitude (as a tremolo in dB)'] += 1
                else:
                    self.unsupported[f"lfoN_{label} (LFO to {label})"] += 1
        # flex envelopes / pitch and filter envelopes: supported only when inert
        egs: dict[str, set[str]] = {}
        for name in list(r.ops) + list(r.mods):
            m = _EG.match(name)
            if m:
                egs.setdefault(m.group(1), set()).add(m.group(2))
        for n, fields in sorted(egs.items()):
            pre = f"eg{n}"
            active = False
            # an envelope whose segments all take no time moves nothing audibly (Karoryfer legato slides at rest)
            times = [self.value(r, f"{pre}_time{i}", kc, vc, base=0.0) for i in range(16)
                     if r.has(f"{pre}_time{i}") or f"{pre}_time{i}" in r.mods]
            for f_ in fields:
                if f_.startswith(('time', 'level', 'shape', 'sustain', 'loop', 'dynamic', 'points')):
                    continue
                if self.value(r, f"{pre}_{f_}", kc, vc, base=0.0) and any(t > 0 for t in times):
                    active = True
            for k in list(r.ops):
                if k.startswith(pre + '_'):
                    r.used.add(k)
            if active:
                self.unsupported['egNN_* (flex envelopes)'] += 1
            else:
                self.inactive['egNN_* (flex envelope without effect at these controllers)'] += 1
        # filter envelope -> the zone's filterEnv (needs the zone filter); pitch envelope: only when inert
        keys = [k for k in list(r.ops) + list(r.mods) if k.startswith('fileg_')]
        if keys:
            for k in keys:
                r.used.add(k)
            depth = self.value(r, 'fileg_depth', kc, vc, base=0.0) + r.num('fileg_vel2depth', 0.0) * vc / 127.0
            if r.num('fileg_vel2depth', 0.0):
                self.approx["fileg_vel2depth (taken at the region's velocity centre)"] += 1
            if not depth:
                self.inactive['fileg_* (filter envelope depth 0 at these controllers)'] += 1
            elif 'cutoff' not in z:
                self.unsupported['fileg_* (filter envelope without a filter cutoff)'] += 1
            else:
                t = [max(0.0, min(100.0, self.value(r, f"fileg_{k}", kc, vc, base=0.0)))
                     for k in ('delay', 'attack', 'hold', 'decay')]
                sus = max(0.0, min(1.0, self.value(r, 'fileg_sustain', kc, vc, base=0.0) / 100.0))
                rel = max(0.0, min(100.0, self.value(r, 'fileg_release', kc, vc, base=0.0)))
                z['filterEnv'] = [round(max(-12000.0, min(12000.0, depth)), 4)] + [round(x, 6) for x in t] + \
                                 [round(sus, 6), round(rel, 6)]
                if self.value(r, 'fileg_start', kc, vc, base=0.0):
                    self.unsupported['fileg_start (initial filter envelope level)'] += 1
                for vk in ('fileg_vel2attack', 'fileg_vel2hold', 'fileg_vel2decay', 'fileg_vel2sustain', 'fileg_vel2release',
                           'fileg_vel2delay'):
                    if r.num(vk, 0.0):
                        self.unsupported[vk] += 1
        keys = [k for k in list(r.ops) + list(r.mods) if k.startswith('pitcheg_')]
        if keys:
            for k in keys:
                r.used.add(k)
            if self.value(r, 'pitcheg_depth', kc, vc, base=0.0):
                self.unsupported['pitcheg_* (pitch envelope)'] += 1
            else:
                self.inactive['pitcheg_* (pitch envelope depth 0 at these controllers)'] += 1

    def _account(self, r: _Region) -> None:
        """Every opcode of a played region is used, inert, inactive or unsupported."""
        mod_targets = set(r.mods) | set(r.mcurves)
        known_mod_targets = set(_BASES) | {'volume', 'amplitude', 'global_volume', 'master_volume', 'group_volume'}
        for canon in r.ops:
            if canon in r.used:
                continue
            original = r.names.get(canon, canon)
            if _INERT.match(original) or _INERT.match(canon):
                self.inert[re.sub(r'\d+', 'N', original)] += 1
                continue
            if canon in ('lokey', 'hikey', 'key', 'lovel', 'hivel', 'sample', 'lorand', 'hirand', 'pitch_keycenter',
                         'global_volume', 'master_volume', 'group_volume', 'global_amplitude', 'master_amplitude',
                         'group_amplitude', 'global_tune', 'master_tune', 'group_tune', 'transpose', 'pitch_keytrack',
                         'sustain_sw', 'ampeg_vel2attack', 'ampeg_vel2hold', 'ampeg_vel2decay', 'ampeg_vel2sustain',
                         'ampeg_vel2release', 'ampeg_vel2delay', 'ampeg_start', 'trigger', 'rt_decay', 'group', 'off_by',
                         'note_polyphony', 'offset_random', 'pitch_random', 'amp_random', 'delay_random', 'loop_type',
                         'looptype', 'end', 'seq_length', 'seq_position', 'lochan', 'hichan', 'loprog', 'hiprog',
                         'fil_type', 'fil1_type', 'cutoff', 'resonance', 'fil_keytrack', 'fil_keycenter', 'fil_veltrack',
                         'rt_dead', 'pitch_veltrack', 'position', 'amplitude', 'volume', 'pan', 'width', 'tune', 'offset',
                         'delay', 'amp_veltrack', 'loop_mode', 'loop_start', 'loop_end', 'polyphony', 'xf_velcurve',
                         'xf_keycurve'):
                continue
            if re.fullmatch(r'(eq[123]_(freq|bw|gain|vel2gain|vel2freq)|(pitch|amp|fil)lfo_(depth|freq|delay|fade)|'
                            r'xf_cccurve|'
                            r'xf(in|out)_(lo|hi)(vel|key)|xf(in|out)_(lo|hi)cc\d+|(lo|hi)(hd)?cc\d+|sw_.*|'
                            r'ampeg_(delay|attack|hold|decay|sustain|release)|off_mode|off_time|amp_velcurve_\d+)', canon):
                continue
            self.unsupported[re.sub(r'\d+', 'N', original)] += 1
        for t in mod_targets:
            if t in known_mod_targets or _LFO.match(t) or _EG.match(t) or t.startswith(('fileg_', 'pitcheg_', 'fillfo_',
                                                                                          'eq1_', 'eq2_', 'eq3_')):
                continue
            nonzero = any(a != 0 for a in (r.mods.get(t) or {}).values())
            label = re.sub(r'\d+', 'N', t) + '_onccN'
            if nonzero:
                self.unsupported[label] += 1
            else:
                self.inactive[label] += 1


# ------------------------------------------------------------------------------------------------ public API

def _note_offset(ops: dict) -> int:
    """note_offset + 12 x octave_offset of the <control> block in effect for a region."""
    st = ops.get(_STATE) or {}
    return (_int(st.get('note_offset')) or 0) + 12 * (_int(st.get('octave_offset')) or 0)


def _articulation_table(doc: SfzFile) -> list[dict]:
    """Keyswitch articulations: [{'key', 'name', 'label', 'regions', 'default'}]."""
    table: dict[int, dict] = {}
    default = None
    for ops, _ in doc.regions:
        note_offset = _note_offset(ops)
        if 'sw_default' in ops and default is None:
            default = _note(ops['sw_default'], note_offset)
        for name in ('sw_last', 'sw_down'):
            if name in ops:
                k = _note(ops[name], note_offset)
                if k is None:
                    continue
                e = table.setdefault(k, {'key': k, 'name': _note_name(k), 'label': None, 'regions': 0})
                e['regions'] += 1
                if ops.get('sw_label') and not e['label']:
                    e['label'] = ops['sw_label'].strip()
    out = sorted(table.values(), key=lambda e: e['key'])
    if out and (default is None or default not in table):
        default = out[0]['key']
    for e in out:
        e['default'] = e['key'] == default
    return out


def _note_name(k: int) -> str:
    return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][k % 12] + str(k // 12 - 1)


def _pick_articulation(doc: SfzFile, articulation) -> tuple[int | None, str | None]:
    table = _articulation_table(doc)
    if not table:
        if articulation is not None:
            siblings = sorted(p.name for p in doc.dir.glob('*.sfz') if p != doc.path)[:20]
            raise ComposeError(f"sfz {doc.path.name}: has no keyswitch articulations (sw_last); "
                               f"articulation={articulation!r} can't be chosen. Other .sfz files next to it: "
                               f"{', '.join(siblings) or 'none'}")
        return None, None
    if articulation is None:
        e = next(e for e in table if e['default'])
        return e['key'], e['label'] or e['name']
    if isinstance(articulation, int) and not isinstance(articulation, bool):
        hits = [e for e in table if e['key'] == articulation]
    else:
        text = str(articulation).strip().lower()
        k = _note(text) if _NOTE_RE.match(text) else None
        hits = [e for e in table if k is not None and e['key'] == k]
        if not hits:
            hits = [e for e in table if e['label'] and e['label'].lower() == text]
        if not hits:
            hits = [e for e in table if e['label'] and text in e['label'].lower()]
    if len(hits) != 1:
        listing = ', '.join(f"{e['label'] or '?'} ({e['name']})" for e in table)
        why = 'is ambiguous' if hits else 'matches none'
        raise ComposeError(f"sfz {doc.path.name}: articulation {articulation!r} {why}; articulations: {listing}")
    return hits[0]['key'], hits[0]['label'] or hits[0]['name']


_MIC_WORDS = ('close', 'dry', 'wet', 'wetter', 'room', 'rooms', 'amb', 'ambience', 'ambient', 'oh', 'ohs', 'overhead',
              'overheads', 'top', 'bottom', 'btm', 'reso', 'batter', 'front', 'rear', 'near', 'far', 'tree', 'spot',
              'direct', 'di', 'hall', 'stage', 'inside', 'outside', 'mid', 'side')
_MIC_SPLIT = re.compile(r'[\\/_\-\s.()\[\]]+')


def _mic_detect(doc: SfzFile) -> tuple[dict[int, list[str]], Counter]:
    """Microphone words per region (sample folders / file names / group and master labels) that vary across the
    regions; regions without one are 'main'."""
    words_per: dict[int, set[str]] = {}
    count = Counter()
    for ops, _ in doc.regions:
        tokens = set()
        s = (ops.get('sample') or '').lower()
        if not s.startswith('*'):
            tokens |= {t for t in _MIC_SPLIT.split(s) if t in _MIC_WORDS}
        for lbl in ('group_label', 'master_label'):
            v = (ops.get(lbl) or '').lower()
            tokens |= {t for t in _MIC_SPLIT.split(v) if t in _MIC_WORDS}
        words_per[id(ops)] = tokens
        count.update(tokens)
    total = len(doc.regions)
    varying = {w for w, c in count.items() if 0 < c < total}
    out: dict[int, list[str]] = {}
    mics = Counter()
    for ops, _ in doc.regions:
        ws = sorted(words_per[id(ops)] & varying) or (['main'] if varying else [])
        out[id(ops)] = ws
        mics.update(ws)
    return out, mics


def mics(path, caller_file: str | None = None) -> dict[str, int]:
    """Detected microphones / signal layers (name -> regions); {} when the file has one."""
    doc = parse(resolve_path(path, caller_file))
    return dict(sorted(_mic_detect(doc)[1].items()))


def articulations(path, caller_file: str | None = None) -> list[dict]:
    """Keyswitch articulations [{'key', 'name', 'label', 'regions', 'default'}] ([] when there are none)."""
    return _articulation_table(parse(resolve_path(path, caller_file)))


# Controllers a file may use for its dynamics (the mod wheel first, then expression) and the opcodes that make one a
# dynamics controller: crossfades, level, filter cutoff, layer conditions.
DYNAMICS_CCS = (1, 11)
_DYN_OPS = re.compile(r'^(?:xf(?:in|out)_(?:lo|hi)cc|(?:amplitude|volume|gain|cutoff)_?(?:on)?cc|(?:lo|hi)(?:hd)?cc)(\d+)$')


def dynamics_controller(doc: SfzFile, dyn_cc='auto') -> int | None:
    """The controller played live as the sampler's 'dynamics': 'auto' = CC1 when the file maps dynamics to it
    (crossfades, volume / amplitude, cutoff or layer conditions), else CC11 when it does, else None; an int forces that
    controller (when the file uses it); None = no live dynamics (everything static)."""
    if dyn_cc is None or dyn_cc is False:
        return None
    if dyn_cc != 'auto' and (isinstance(dyn_cc, bool) or not isinstance(dyn_cc, int) or not 0 <= dyn_cc <= 127):
        raise ComposeError(f"sfz: dyn_cc must be 'auto', a controller number 0..127 or None, got {dyn_cc!r}")
    used = set()
    for ops, _ in doc.regions:
        for name in ops:
            if name == _STATE:
                continue
            m = _DYN_OPS.match(re.sub(r'^(lfo|eg)0*(\d+)_', r'\1\2_', name))
            if m:
                used.add(int(m.group(1)))
    if dyn_cc == 'auto':
        return next((n for n in DYNAMICS_CCS if n in used), None)
    return dyn_cc if dyn_cc in used else None


HAMMER_BANDS = ((3000.0, 1.6, 7.0), (7500.0, 1.8, 9.0))
"""hammers(): the eq bands a zone gets - (Hz, bandwidth in octaves, dB at amount 1 on the top velocity layer)."""
HAMMER_GAIN = 2.0
"""hammers(): dB added to the top layer's level at amount 1 (the loud layers keep their loudness - K-weighting
hears the cut presence - so the note-to-note dynamics stay; the loud notes bloom instead of biting)."""


def hammers(zones: list[dict], amount: float) -> list[dict]:
    """Piano hammer voicing on imported zones (inst.sfz(..., hammers=amount)): a velocity-layered piano's
    velocity -> brightness curve made gentler, like a technician needling (softening) the hammer felt. A close-miked
    sampled grand gets glassy and percussive in its top layers: the Salamander's 2-5 kHz share rises ~12 dB and its
    5-12 kHz share ~20 dB from velocity 64 to 127, its level only ~6-10 dB. Every zone gets HAMMER_BANDS as
    peaking eq bands scaled by the centre of its velocity range: -amount x (7 dB at 3 kHz, 9 dB at 7.5 kHz) on the
    top layer (velocity ~124), 0 at velocity 80, up to +amount x a quarter of that on the soft layers (<= 40: they
    stay clear); the loud layers also get up to HAMMER_GAIN x amount dB of level back (their loudness - and so the
    dynamics - stays, the tone blooms). amount 0..1 (0 = as recorded; 0.5-0.8 = a warm jazz / ballad grand). User feedback 2026-09-30
    (perry-street-rain): "es klingt hart ... eine Sound-Design-Frage". Zones without room for two more bands (3 per
    zone) and zones that answer every velocity keep their sound. Returns new zone dicts."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not 0.0 <= amount <= 1.0:
        raise ComposeError(f"sfz hammers must be a number 0..1 (0 = as recorded), got {amount!r}")
    out = []
    for z in zones:
        z = dict(z)
        if z.get('vello', 0) <= 1 and z.get('velhi', 127) >= 127:      # not a velocity layer: nothing to voice
            out.append(z)
            continue
        vc = (z.get('vello', 0) + z.get('velhi', 127)) / 2.0
        g = 0.25 * min(1.0, (80.0 - vc) / 40.0) if vc < 80.0 else -min(1.0, (vc - 80.0) / 44.0)
        bands = list(z.get('eq') or [])
        if amount and abs(g) > 1e-9 and len(bands) + len(HAMMER_BANDS) <= 3:
            bands += [[f, bw, round(db * amount * g, 4)] for f, bw, db in HAMMER_BANDS]
            z['eq'] = bands
            if g < 0:
                z['gain'] = round(z.get('gain', 0.0) - HAMMER_GAIN * amount * g, 4)
        out.append(z)
    return out


def load(path, articulation=None, cc=None, mics=None, strict: bool = False, caller_file: str | None = None,
         dyn_cc='auto', keyswitches: str = 'live') -> tuple[list[dict], dict]:
    """(zones for the 'sampler' instrument, info) of an .sfz file. See the module docstring. dyn_cc: the controller
    played live by the sampler's 'dynamics' ('auto', a number, None = static); keyswitches: 'live' (every
    articulation, switched by keyswitch notes; the default when no articulation= is given) or 'static' (only the
    default / chosen articulation). info['params']: sampler params the import sets (dynamics, dyntone),
    info['keyswitches']: {articulation name: key} of live keyswitches."""
    if keyswitches not in ('live', 'static'):
        raise ComposeError(f"sfz: keyswitches must be 'live' or 'static', got {keyswitches!r}")
    p = resolve_path(path, caller_file)
    doc = parse(p)
    if not doc.regions:
        what = []
        if doc.defines:
            what.append(f"{len(doc.defines)} #define")
        if doc.curves:
            what.append(f"{len(doc.curves)} <curve>")
        if doc.control:
            what.append('<control> settings')
        kind = f": it only holds {', '.join(what)} (a keymap / settings fragment)" if what else ''
        raise ComposeError(f"sfz {p}: no <region> found{kind}" + (f" ({'; '.join(doc.problems[:3])})" if doc.problems else '')
                           + _fragment_hint(p))
    art_key, art_label = _pick_articulation(doc, articulation)
    table = _articulation_table(doc)
    live_sw = bool(table) and articulation is None and keyswitches == 'live'
    dyn = dynamics_controller(doc, dyn_cc)
    mic_map, mic_count = _mic_detect(doc)
    mic_gains = None
    if mics:
        if not isinstance(mics, dict):
            raise ComposeError(f"sfz: mics= must be a dict like {{'close': 0, 'room': -6, 'oh': None}}, got {mics!r}")
        unknown = [m for m in mics if m not in mic_count]
        if unknown:
            raise ComposeError(f"sfz {p.name}: unknown microphone(s) {', '.join(map(repr, unknown))}; this file has "
                               f"{', '.join(f'{k} ({v} regions)' for k, v in sorted(mic_count.items())) or 'one signal only'}")
        for k, v in mics.items():
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not -60 <= v <= 24):
                raise ComposeError(f"sfz: mics[{k!r}] must be a gain in dB (-60..24) or None (off), got {v!r}")
        mic_gains = dict(mics)
    imp = _Import(doc, cc, art_key, mic_gains, strict, mic_map, dyn_cc=dyn, live_sw=live_sw,
                  sw_default=art_key if live_sw else None)
    for ops, origin in doc.regions:
        imp.region(ops, origin)
    if imp.missing:
        missing = sorted(set(imp.missing))
        hint = _missing_hint(missing) or _ancestor_hint(p, imp.missing_rel)
        raise ComposeError(f"sfz {p}: {len(missing)} sample file(s) missing{hint}; e.g. "
                           + ', '.join(missing[:6]) + (' ...' if len(missing) > 6 else ''))
    unsupported = Counter(imp.unsupported)
    for h, c in doc.headers.items():
        if h in ('effect', 'midi', 'sample') or h not in _KNOWN_HEADERS:
            unsupported[f"<{h}> section"] += c
    if imp.ctx.missing_curves:
        imp.approx[f"curve index {sorted(imp.ctx.missing_curves)} undefined (linear used)"] += 1
    info = {
        'path': str(p), 'regions': len(doc.regions), 'zones': len(imp.zones), 'articulation': art_label,
        'cc': {n: round(v * 127.0, 3) for n, v in sorted(imp.ctx.values.items())},
        'mics': dict(sorted(mic_count.items())), 'unsupported': dict(unsupported.most_common()),
        'inactive': dict(imp.inactive.most_common()), 'approximated': dict(imp.approx.most_common()),
        'inert': dict(imp.inert.most_common()), 'skipped': dict(imp.skipped.most_common()),
        'problems': list(doc.problems),
    }
    params = {}
    if dyn is not None and any(k in z for z in imp.zones for k in ('xfinLoDyn', 'xfoutLoDyn', 'dynGain', 'dynCutoff',
                                                                    'dynLo', 'dynHi')):
        info['dynamics'] = {'cc': dyn, 'value': round(imp.ctx.x(dyn, 60, 64) * 127.0, 3), 'timbre': imp.dyn_timbre}
        params['dynamics'] = round(imp.ctx.x(dyn, 60, 64), 6)
        if imp.dyn_timbre or params['dynamics'] < 1.0:
            # the file's own layers / filter carry the timbre of its dynamics; or its default lies below the top,
            # where the 'dyntone' tilt (flat only at dynamics 1) would darken the default sound
            params['dyntone'] = 0.0
    info['params'] = params
    if live_sw:
        info['keyswitches'] = {(e['label'] or e['name']): e['key'] for e in table}
        info['articulation'] = f"{art_label} (default; live keyswitches)"
    if live_sw and imp.zones and not any('swLast' in z or 'swDown' in z for z in imp.zones):
        info.pop('keyswitches', None)
    if strict and (unsupported or doc.problems):
        what = ', '.join(f"{k} ({v})" for k, v in unsupported.most_common(12))
        raise ComposeError(f"sfz {p.name} (strict): unsupported: {what or 'none'}"
                           + (f"; problems: {'; '.join(doc.problems[:5])}" if doc.problems else ''))
    if not imp.zones:
        reasons = ', '.join(f"{k} ({v})" for k, v in imp.skipped.most_common(4))
        raise ComposeError(f"sfz {p.name}: no region plays with these settings (articulation {art_label!r}, "
                           f"cc {info['cc']}): {reasons}" + _fragment_hint(p))
    return imp.zones, info


# zone params a load_multi program's 'zone' overrides must not set (mapping, keyswitches, trigger; level: 'gain')
_ZONE_FIXED = ('file', 'lo', 'hi', 'root', 'swLast', 'swDefault', 'swLo', 'swHi', 'trigger', 'gain')


def _keygain(spec, where: str) -> list | None:
    """A validated 'keygain' curve: [[key, dB], ...] with rising keys (0..127) and dB -48..24; None when not given."""
    if spec is None:
        return None
    ok = isinstance(spec, (list, tuple)) and len(spec) >= 1 and all(
        isinstance(p, (list, tuple)) and len(p) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                                              for v in p) and 0 <= p[0] <= 127 and -48 <= p[1] <= 24
        for p in spec)
    if ok:
        keys = [p[0] for p in spec]
        ok = all(a < b for a, b in zip(keys, keys[1:]))
    if not ok:
        raise ComposeError(f"{where}: 'keygain' must be [[key 0..127, dB -48..24], ...] with rising keys, got {spec!r}")
    return [[float(p[0]), float(p[1])] for p in spec]


def _interp(curve: list, x: float) -> float:
    """Piecewise-linear value of [[x, y], ...] at x (flat beyond the ends)."""
    if x <= curve[0][0]:
        return curve[0][1]
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return curve[-1][1]


def check_velcurve(points) -> list[list]:
    """[(velocity 0..127 whole, gain 0..4), ...] strictly increasing in velocity -> [[v, g], ...] (ComposeError else)."""
    if isinstance(points, (str, bytes)) or not hasattr(points, '__iter__'):
        raise ComposeError(f"velcurve must be a list of (velocity, gain) points, got {points!r}")
    out: list[list] = []
    for pt in points:
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            raise ComposeError(f"velcurve point must be (velocity, gain), got {pt!r}")
        v, g = pt
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != int(v) or not 0 <= v <= 127:
            raise ComposeError(f"velcurve velocity must be a whole number 0..127, got {v!r}")
        if isinstance(g, bool) or not isinstance(g, (int, float)) or not math.isfinite(g) or not 0 <= g <= 4:
            raise ComposeError(f"velcurve gain must be 0..4 (amplitude), got {g!r}")
        if out and int(v) <= out[-1][0]:
            raise ComposeError(f"velcurve velocities must be strictly increasing, got {v!r} after {out[-1][0]}")
        out.append([int(v), round(float(g), 6)])
    if not out:
        raise ComposeError("velcurve must have at least one point")
    return out


def apply_velcurve(zones: list[dict], points) -> list[dict]:
    """Every velocity-layer zone (one with vello / velhi) plays `points` (check_velcurve) as its velocity curve
    instead of its own amp_velcurve / amp_veltrack: each keeps the points inside its velocity range plus the nearest
    one on either side. Zones answering every velocity (percussion / noise keys) keep their own response."""
    pts = check_velcurve(points)
    out = []
    for z in zones:
        if 'vello' not in z and 'velhi' not in z:
            out.append(z)
            continue
        z = dict(z)
        z.pop('ampVeltrack', None)
        lo, hi = z.get('vello', 0), z.get('velhi', 127)
        inside = [i for i, (v, _) in enumerate(pts) if lo <= v <= hi]
        a = (inside[0] if inside else next((i for i, (v, _) in enumerate(pts) if v > hi), len(pts))) - 1
        b = (inside[-1] if inside else a) + 1
        z['velcurve'] = [list(p) for p in pts[max(0, a):min(len(pts), b + 1)]] or [list(pts[-1])]
        out.append(z)
    return out


def even_velcurve(layers, power: float = 2.0, step: int = 4) -> list[list]:
    """velcurve points (inst.sfz(velcurve=...)) that give a velocity-layered instrument ONE smooth, monotonic
    response: the note level follows 20 x power x log10(v / 127) dB (power 2 = the SFZ default amp_veltrack 100,
    ~10 dB between velocity 57 and 103) whatever layer plays it. layers = [(lovel, hivel, level_db), ...] the
    layers' measured sample levels (e.g. the mean attack level of their samples); the loudest layer's top is 0 dB.
    Packs whose layers each ramp to full level at their top (amp_velcurve_96=1 ...) otherwise play louder at the
    top of a soft layer than at the bottom of the next one and flatten a line's dynamics."""
    if not 0.2 <= power <= 4.0:
        raise ComposeError(f"even_velcurve power must be 0.2..4, got {power!r}")
    ls = sorted((int(lo), int(hi), float(db)) for lo, hi, db in layers)
    if not ls:
        raise ComposeError("even_velcurve needs at least one (lovel, hivel, level_db) layer")
    ref = ls[-1][2]
    pts: list[list] = []
    for lo, hi, db in ls:
        if not 0 <= lo <= hi <= 127:
            raise ComposeError(f"even_velcurve layer {lo}..{hi} must lie in 0..127")
        vs = sorted({max(1, lo)} | set(range(max(1, lo) + step, hi, step)) | {hi})
        for v in vs:
            g_db = 20.0 * power * math.log10(v / 127.0) - (db - ref)
            g = min(4.0, 10.0 ** (g_db / 20.0))
            if pts and v <= pts[-1][0]:
                continue
            pts.append([v, round(g, 6)])
    return pts


def load_multi(programs: dict, keyswitch=0, default=None, cc=None, mics=None, strict: bool = False,
               caller_file: str | None = None, dyn_cc='auto') -> tuple[list[dict], dict]:
    """One keyswitched instrument from separate per-articulation programs (VSCO 2, SSO and VPO ship them separately):
    {'sustain': 'x_sus.sfz', 'staccato': 'x_stac.sfz', 'pizz': {'path': 'x_pizz.sfz', 'gain': -2, 'articulation':
    ..., 'cc': {...}}}. Articulation i gets the keyswitch key `keyswitch` + i (default C-1 = 0 upwards: below any
    played note), `default` (else the first) plays until a keyswitch selects another; groups / off_by are renumbered
    per program. Each program is imported like load() (keyswitches of its own: statically, its default or the given
    articulation). A program's 'zone' ({zone param: value}) overrides params of its attack zones (not the
    release-triggered ones): an articulation made from the same samples, e.g. a guitar palm mute {'path': same,
    'zone': {'filter': 'lpf_2p', 'cutoff': 1600, 'decay': 0.55, 'sustain': 0}}. 'keygain' ([[key, dB], ...],
    piecewise linear over each zone's root key, the file's keys) evens out a set whose notes were recorded at uneven
    levels (e.g. [[36, 0], [60, 8]]: +8 dB at the top).
    -> (zones, info): info['keyswitches'] = {name: key}, info['programs'] = {name: its info}."""
    if not isinstance(programs, dict) or not programs:
        raise ComposeError("sfz_multi: programs must be a non-empty dict {'articulation name': 'file.sfz', ...}")
    names = list(programs)
    for n in names:
        if not isinstance(n, str) or not n.strip():
            raise ComposeError(f"sfz_multi: articulation names must be non-empty strings, got {n!r}")
    base = _note(keyswitch) if isinstance(keyswitch, str) else keyswitch
    if isinstance(base, bool) or not isinstance(base, int) or not 0 <= base <= 128 - len(names):
        raise ComposeError(f"sfz_multi: keyswitch must be the first key (0..{128 - len(names)} or a note name) of "
                           f"{len(names)} keyswitches, got {keyswitch!r}")
    if default is None:
        default = names[0]
    if default not in programs:
        raise ComposeError(f"sfz_multi: default {default!r} is not one of {', '.join(names)}")
    keys = {n: base + i for i, n in enumerate(names)}
    zones: list[dict] = []
    infos: dict[str, dict] = {}
    groups: dict[tuple, int] = {}
    params: dict = {}
    unsupported = Counter()
    problems: list[str] = []
    for i, name in enumerate(names):
        spec = programs[name]
        opts = dict(spec) if isinstance(spec, dict) else {'path': spec}
        extra = set(opts) - {'path', 'articulation', 'cc', 'mics', 'gain', 'zone', 'keygain'}
        if extra or 'path' not in opts:
            raise ComposeError(f"sfz_multi[{name!r}]: a path or a dict with 'path' and optionally 'articulation', 'cc', "
                               f"'mics', 'gain' (dB), 'zone' (zone param overrides), 'keygain' ([[key, dB], ...]), "
                               f"got {spec!r}")
        over = opts.get('zone') or {}
        if not isinstance(over, dict) or not all(isinstance(k, str) and k for k in over) or \
                any(k in over for k in _ZONE_FIXED):
            raise ComposeError(f"sfz_multi[{name!r}]: 'zone' must be {{zone param: value}} (not file / key range / "
                               f"keyswitch / trigger; dB: the program's 'gain' / 'keygain'), got {over!r}")
        keygain = _keygain(opts.get('keygain'), f"sfz_multi[{name!r}]")
        pcc = dict(cc or {})
        pcc.update(opts.get('cc') or {})
        zs, info = load(opts['path'], articulation=opts.get('articulation'), cc=pcc or None, mics=opts.get('mics', mics),
                        strict=strict, caller_file=caller_file, dyn_cc=dyn_cc, keyswitches='static')
        g = opts.get('gain', 0.0)
        if isinstance(g, bool) or not isinstance(g, (int, float)) or not -48 <= g <= 24:
            raise ComposeError(f"sfz_multi[{name!r}]: gain must be dB -48..24, got {g!r}")
        for z in zs:
            z = dict(z)
            for key in ('group', 'offBy'):
                v = z.get(key)
                if v is not None and v != 0:
                    z[key] = groups.setdefault((i, v), len(groups) + 1)
            if over and z.get('trigger') not in ('release', 'release_key'):
                z.update(over)
            if keygain:
                root = z.get('root')
                k = root if isinstance(root, (int, float)) and not isinstance(root, bool) else \
                    (z.get('lo', 0) + z.get('hi', 127)) / 2.0
                g2 = _interp(keygain, k)
                if g2:
                    z['gain'] = round(z.get('gain', 0.0) + g2, 4)
            if g:
                z['gain'] = round(z.get('gain', 0.0) + g, 4)
            z['swLast'] = keys[name]
            z['swDefault'] = keys[default]
            zones.append(z)
        infos[name] = info
        for k, v in (info.get('params') or {}).items():
            if k == 'dyntone':
                params['dyntone'] = 0.0
            else:
                params.setdefault(k, v)
        unsupported.update(info.get('unsupported') or {})
        problems += [f"{name}: {x}" for x in info.get('problems') or []]
    zones[0]['swLo'], zones[0]['swHi'] = base, base + len(names) - 1
    info = {'path': 'sfz_multi(' + ', '.join(f"{n}={infos[n]['path']}" for n in names) + ')',
            'regions': sum(x['regions'] for x in infos.values()), 'zones': len(zones),
            'articulation': f"{default} (default; live keyswitches)", 'keyswitches': keys, 'programs': infos,
            'unsupported': dict(unsupported.most_common()), 'problems': problems, 'params': params}
    return zones, info


def _fragment_hint(p: Path) -> str:
    """'; this file is #included by X.sfz: load that' for include fragments."""
    for other in sorted(p.parent.parent.rglob('*.sfz'))[:400] if p.parent.parent.exists() else []:
        if other == p:
            continue
        try:
            text = other.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if p.name in text and re.search(r'#include\s+"[^"]*' + re.escape(p.name) + '"', text):
            return f"; this file is a fragment #included by {other.relative_to(p.parent.parent).as_posix()}: load that"
    return ''


def _ancestor_hint(p: Path, rel: list[str]) -> str:
    """'; its sample paths resolve from <folder> (...)' when the missing samples exist relative to a folder above the
    file: an #include fragment or a copy of a program that belongs there."""
    samples = _samples_dir()
    for up in list(p.parents)[1:6]:
        if len(up.parts) < len(samples.parts):
            break
        found = sum(1 for r in rel[:20] if _FINDER.find(os.path.normpath(os.path.join(str(up), r))))
        if found and found >= min(len(rel), 20) // 2:
            where = up.relative_to(samples).as_posix() if samples in up.parents or up == samples else str(up)
            return (f"; its sample paths resolve from {where}/: this file is an #include fragment or a copy of a "
                    f"program that belongs there (load the .sfz in {where}/ instead)")
    return ''


def _missing_hint(missing: list[str]) -> str:
    samples = str(_samples_dir())
    packs = set()
    for m in missing:
        try:
            rel = os.path.relpath(m, samples).replace('\\', '/')
        except ValueError:
            continue
        pack = rel.split('/')[0]
        for other in COMPANION_PACKS.get(pack, []):
            if not os.path.isfile(os.path.join(samples, other, 'SOURCE.json')):
                packs.add(other)
    if packs:
        return f"; it needs pack(s) {', '.join(sorted(packs))}: python -m agentsound samples fetch {' '.join(sorted(packs))}"
    return ''


def summary(path, caller_file: str | None = None, cc=None, articulation=None) -> dict:
    """What an .sfz holds: regions, key range, velocity layers, round robin, articulations, mics, controllers,
    unsupported opcodes (at the file's default controllers), and whether its samples are present."""
    p = resolve_path(path, caller_file)
    doc = parse(p)
    arts = _articulation_table(doc)
    out: dict = {'path': str(p), 'regions': len(doc.regions), 'articulations': arts,
                 'mics': dict(sorted(_mic_detect(doc)[1].items())), 'includes': len(doc.includes)}
    labels = {int(m.group(1)): v.strip() for k, v in doc.control.items() for m in [re.fullmatch(r'label_cc(\d+)', k)] if m}
    defaults = _Ctx(doc, None).values
    out['controllers'] = {n: {'label': labels.get(n), 'default': round(defaults.get(n, 0.0) * 127.0, 2)}
                          for n in sorted(set(labels) | set(defaults))}
    try:   # statistics of one articulation (the default or the chosen one)
        zones, info = load(p, cc=cc, articulation=articulation, keyswitches='static')
    except ComposeError as e:
        out['error'] = str(e)
        return out
    notes = [z for z in zones if z.get('trigger') not in ('release', 'release_key') and not z['file'].startswith('*')]
    if notes:
        out['keys'] = [min(z['lo'] for z in notes), max(z['hi'] for z in notes)]
    # per key: distinct velocity ranges, and per key + velocity range: distinct random ranges (the most on any key)
    vel_layers: dict[int, set] = {}
    rand_layers: dict[tuple, set] = {}
    for z in notes:
        vr = (z.get('vello', 0), z.get('velhi', 127))
        for k in range(z['lo'], z['hi'] + 1):
            vel_layers.setdefault(k, set()).add(vr)
            rand_layers.setdefault((k, vr), set()).add((z.get('lorand', 0), z.get('hirand', 1)))
    out['velocityLayers'] = max((len(v) for v in vel_layers.values()), default=0)
    out['roundRobin'] = max([z.get('seqLength', 1) for z in zones] + [1])
    out['randomLayers'] = max((len(v) for v in rand_layers.values()), default=1)
    out['releaseZones'] = sum(1 for z in zones if z.get('trigger') in ('release', 'release_key'))
    out['zones'] = len(zones)
    out['samples'] = len({z['file'] for z in zones})
    out['loops'] = sum(1 for z in zones if z.get('loop') in ('forward', 'pingpong', 'sustain'))
    out['articulation'] = info['articulation']
    for k in ('unsupported', 'inactive', 'approximated', 'skipped', 'problems'):
        if info[k]:
            out[k] = info[k]
    return out


def pack_sfz_files(pack_dir: Path) -> tuple[list[Path], set[Path]]:
    """(every .sfz of an installed pack, the ones that are #include fragments of another .sfz there)."""
    files = sorted(p for p in pack_dir.rglob('*') if p.suffix.lower() == '.sfz' and p.is_file())
    fragments: set[Path] = set()
    for f in files:
        try:
            doc = parse(f)
        except ComposeError:
            continue
        fragments.update(os.path.normcase(str(i)) for i in doc.includes)
    return files, {f for f in files if os.path.normcase(str(f)) in fragments}


def check(pack_ids=None, log=None) -> list[dict]:
    """Import every .sfz of the installed packs (or of `pack_ids`): one row per file with its status
    ('ok', 'fragment': #included by another file of the pack, 'error': why it can't be imported), zones and
    unsupported opcodes. `python -m agentsound sfz --check [PACK ...]`."""
    root = _samples_dir()
    rows = []
    packs = sorted(p for p in root.iterdir() if p.is_dir() and (p / 'SOURCE.json').is_file()) if root.is_dir() else []
    if pack_ids:
        packs = [p for p in packs if p.name in pack_ids]
    for pack in packs:
        files, fragments = pack_sfz_files(pack)
        for f in files:
            rel = f.relative_to(root).as_posix()
            row = {'pack': pack.name, 'file': rel}
            if f in fragments:
                row['status'] = 'fragment'
                rows.append(row)
                continue
            try:
                zones, info = load(f)
                row.update(status='ok', zones=len(zones), regions=info['regions'], articulation=info['articulation'],
                           unsupported=info['unsupported'], approximated=info['approximated'])
            except ComposeError as e:
                row.update(status='error', error=str(e))
            if log:
                log(row)
            rows.append(row)
    return rows


# ------------------------------------------------------------------------------------------------ pitch check

def _fft(a: list) -> list:
    """In-place iterative radix-2 FFT of a complex list (length a power of two)."""
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    size = 2
    while size <= n:
        w = complex(math.cos(-2 * math.pi / size), math.sin(-2 * math.pi / size))
        half = size // 2
        for start in range(0, n, size):
            wk = 1 + 0j
            for k in range(start, start + half):
                t = wk * a[k + half]
                a[k + half] = a[k] - t
                a[k] = a[k] + t
                wk *= w
        size *= 2
    return a


def spectral_peaks(x: list[float], sr: float, size: int = 32768, count: int = 30) -> list[tuple[float, float]]:
    """The strongest spectral peaks (Hz, linear magnitude) of a Hann-windowed frame (parabolic interpolation)."""
    n = min(len(x), size)
    win = [x[i] * (0.5 - 0.5 * math.cos(2 * math.pi * i / max(1, n - 1))) for i in range(n)] + [0.0] * (size - n)
    spec = _fft([complex(v, 0.0) for v in win])
    mag = [abs(c) for c in spec[:size // 2]]
    top = max(mag) if mag else 0.0
    peaks = []
    for i in range(2, len(mag) - 1):
        m = mag[i]
        if m > mag[i - 1] and m >= mag[i + 1] and m > 1e-2 * top:
            a, b, c = math.log(mag[i - 1] + 1e-20), math.log(m), math.log(mag[i + 1] + 1e-20)
            den = a - 2 * b + c
            shift = 0.5 * (a - c) / den if den else 0.0
            peaks.append(((i + shift) * sr / size, m))
    peaks.sort(key=lambda p: -p[1])
    return peaks[:count]


def estimate_pitch_near(x: list[float], sr: float, expected_hz: float) -> float | None:
    """Fundamental of a note near `expected_hz`, octave-robust: a harmonic sieve over the strongest spectral peaks
    finds the best fit within +-150 cents of the expected pitch and of one / two octaves around it. The expected
    octave stands unless the evidence says otherwise: one octave up when the expected one's fundamental and odd
    harmonics are missing (all partials are multiples of twice the pitch), one down when the lower candidate's odd
    harmonics (3rd, 5th, ...) carry real energy. A missing fundamental (low piano strings), body resonances and
    rumble do not fool it; the result is refined from the explained partials."""
    # peaks below the lowest candidate (2 octaves under the expected pitch) are rumble / room noise
    peaks = [(f, m) for f, m in spectral_peaks(x, sr) if max(15.0, 0.22 * expected_hz) < f < 16000.0]
    if not peaks:
        return None

    def explained(f0: float) -> tuple[float, list]:
        e, parts = 0.0, []
        for f, m in peaks:
            k = round(f / f0)
            if 1 <= k <= 16:
                dev = 1200.0 * math.log2(f / (k * f0))
                if abs(dev) < (40.0 if k <= 8 else 70.0):
                    e += m
                    parts.append((f, m, k))
        return e, parts

    cands = {}
    for octv in (-2, -1, 0, 1, 2):
        base = expected_hz * 2.0 ** octv
        best = max(((explained(base * 2.0 ** (c / 1200.0)), base * 2.0 ** (c / 1200.0)) for c in range(-150, 151, 5)),
                   key=lambda t: t[0][0])
        cands[octv] = (best[1], best[0][0], best[0][1])

    def only(a: int, b: int, min_k: int = 1) -> float:
        """Energy of the partials candidate a explains and b doesn't (a's harmonics k >= min_k)."""
        other = {f for f, _, _ in cands[b][2]}
        return sum(m for f, m, k in cands[a][2] if f not in other and k >= min_k)

    o = 0
    while o < 2 and cands[o][1] > 0 and only(o, o + 1) < 0.1 * cands[o][1] and cands[o + 1][1] >= 0.9 * cands[o][1]:
        o += 1          # no fundamental / odd harmonics at this octave: the note is an octave higher
    if o == 0:
        while o > -2 and only(o - 1, o, 3) >= 0.25 * max(cands[o][1], 1e-12):
            o -= 1      # the octave below has odd harmonics of its own: the note is lower
    f0, e, parts = cands[o]
    near = sum(m for f, m in peaks if f > 0.45 * min(f0, expected_hz))
    if not parts or e < 0.2 * near:
        return None
    low = [(f / k, m) for f, m, k in parts if k <= 8] or [(f / k, m) for f, m, k in parts]
    return sum(f * m for f, m in low) / sum(m for _, m in low)


def _read_wav_mono(path: Path) -> tuple[list[float], int]:
    import wave
    with wave.open(str(path), 'rb') as w:
        ch, width, sr, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(frames)
    out = []
    step = width * ch
    scale = float(1 << (8 * width - 1))
    for i in range(0, len(raw) - step + 1, step):
        acc = 0.0
        for c in range(ch):
            b = raw[i + c * width:i + (c + 1) * width]
            acc += int.from_bytes(b, 'little', signed=True) / scale
        out.append(acc / ch)
    return out, sr


def pitch_check(path, keys=None, count: int = 5, cc=None, articulation=None, engine=None, caller_file=None,
                tolerance_cents: float = 50.0) -> list[dict]:
    """Render single notes of an SFZ instrument with the engine and compare their measured fundamental with the
    MIDI pitch: [{'key', 'name', 'expectedHz', 'measuredHz', 'cents', 'ok'}]. By default `count` keys spread over the
    instrument's pitched zones (their root keys, so no resampling hides a wrong mapping). Catches octave-shifted or
    mis-named sample sets. Needs the engine (build/agentsound.exe or `engine=`)."""
    import json as _json
    import subprocess
    import tempfile
    from .cli import find_engine
    zones, info = load(path, articulation=articulation, cc=cc, caller_file=caller_file)
    noise = re.compile(r'(?:^|[^a-z])(perc|noise|noises|breath|fx|click|knock|slap|harm|harmonics?|mech|thump|squeak|'
                       r'scrape|rel|release|pedal|body|key ?noise|fret)(?:[^a-z]|$)', re.I)
    pitched = [z for z in zones if not z['file'].startswith('*') and z.get('trigger') not in ('release', 'release_key')
               and z.get('pitchKeytrack', 100) != 0 and isinstance(z.get('root', 60), (int, float))
               and not noise.search(os.path.basename(z['file']))]
    if not pitched:
        return []
    if keys is None:
        # the root keys of the zones (no resampling hides a wrong mapping), inside the 5..95 % range of all zone
        # roots so single effect zones (breath, key noise, harmonics) far from the playing range are left out
        weighted = sorted(int(round(z.get('root', 60))) for z in pitched if z['lo'] <= round(z.get('root', 60)) <= z['hi'])
        if not weighted:
            weighted = sorted((z['lo'] + z['hi']) // 2 for z in pitched)
        lo_r, hi_r = weighted[int(0.05 * (len(weighted) - 1))], weighted[int(round(0.95 * (len(weighted) - 1)))]
        roots = sorted({k for k in weighted if lo_r <= k <= hi_r})
        if len(roots) > count:
            roots = [roots[round(i * (len(roots) - 1) / (count - 1))] for i in range(count)] if count > 1 else roots[:1]
        keys = roots
    vel = 100
    notes = [[float(i) * 2.0, 1.5, int(k), vel] for i, k in enumerate(keys)]
    params = {'samples': zones, 'attack': 0.0, 'release': 0.05, 'polyphony': 64}
    render = {'format': 'agentsound.render', 'version': 1, 'title': 'pitch check', 'sampleRate': 48000, 'tempo': 60.0,
              'lengthBeats': float(len(keys)) * 2.0, 'tailSeconds': 0.2, 'seed': 1, 'sections': [],
              'tracks': [{'id': 'p', 'instrument': {'type': 'sampler', 'params': params}, 'fx': [], 'gainDb': 0.0, 'pan': 0.0,
                          'output': 'master', 'sends': {}, 'notes': notes, 'automation': []}],
              'buses': [], 'master': {'fx': [], 'gainDb': 0.0, 'automation': []},
              'export': {'stems': False, 'bitDepth': 24}}
    # only the zones these notes reach
    wanted = {(n[2], n[3]) for n in notes}
    tr = params['samples']
    params['samples'] = [z for z in tr if any(z['lo'] <= k <= z['hi'] and z.get('vello', 0) <= v <= z.get('velhi', 127)
                                              for k, v in wanted)] or tr[:1]
    exe = find_engine(engine)
    with tempfile.TemporaryDirectory(prefix='agentsound_pitch_') as tmp:
        rj = Path(tmp) / 'r.json'
        rj.write_text(_json.dumps(render), encoding='utf-8')
        proc = subprocess.run([str(exe), 'render', str(rj), '--out', tmp, '--no-analysis', '--no-png', '--quiet'],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        if proc.returncode != 0:
            raise ComposeError(f"pitch check: the engine failed: {(proc.stderr or proc.stdout).strip()[:400]}")
        x, sr = _read_wav_mono(Path(tmp) / 'mix.wav')
    out = []
    for i, k in enumerate(keys):
        start = int((i * 2.0 + 0.2) * sr)
        want = 440.0 * 2.0 ** ((k - 69) / 12.0)
        f = estimate_pitch_near(x[start:start + 32768], sr, want)
        c = 1200.0 * math.log2(f / want) if f else None
        out.append({'key': k, 'name': _note_name(k), 'expectedHz': round(want, 2), 'measuredHz': round(f, 2) if f else None,
                    'cents': round(c, 1) if c is not None else None, 'ok': c is not None and abs(c) <= tolerance_cents})
    return out


def format_summary(s: dict) -> str:
    """Human-readable summary() for the CLI."""
    lines = [s['path'], f"  regions {s['regions']}" + (f", zones at the default controllers {s['zones']}" if 'zones' in s else '')]
    if 'error' in s:
        lines.append(f"  cannot import: {s['error']}")
    if 'keys' in s:
        lines.append(f"  keys {_note_name(s['keys'][0])}-{_note_name(s['keys'][1])} ({s['keys'][0]}-{s['keys'][1]}), "
                     f"velocity layers {s['velocityLayers']}, round robin {s['roundRobin']}, random layers "
                     f"{s['randomLayers']}, release zones {s['releaseZones']}, {s['samples']} sample files, "
                     f"{s['loops']} looped zones")
    if s['articulations']:
        lines.append('  articulations (keyswitch): ' + ', '.join(
            f"{a['label'] or a['name']} ({a['name']}{', default' if a['default'] else ''})" for a in s['articulations']))
    if s['mics']:
        lines.append('  mics: ' + ', '.join(f"{k} ({v})" for k, v in s['mics'].items()))
    if s['controllers']:
        lines.append('  controllers: ' + ', '.join(f"cc{n}{' ' + c['label'] if c['label'] else ''} = {c['default']:g}"
                                                   for n, c in s['controllers'].items()))
    for k in ('unsupported', 'approximated', 'inactive', 'skipped'):
        if s.get(k):
            lines.append(f"  {k}: " + ', '.join(f"{n} ({c})" for n, c in list(s[k].items())[:14]))
    if s.get('problems'):
        lines.append('  problems: ' + '; '.join(s['problems'][:6]))
    if 'pitch' in s:
        rows = s['pitch']
        if not rows:
            lines.append('  pitch check: no pitched zones')
        else:
            def cents(r: dict) -> str:
                return '?' if r['cents'] is None else f"{r['cents']:+.0f} ct"
            lines.append('  pitch check (measured vs MIDI note): ' + ', '.join(f"{r['name']} {cents(r)}" for r in rows))
            off = [r['cents'] for r in rows if r['cents'] is not None]
            octs = {round(c / 1200.0) for c in off}
            if off and len(octs) == 1 and octs != {0} and all(abs(c - 1200.0 * next(iter(octs))) < 60 for c in off):
                o = next(iter(octs))
                lines.append(f"  -> the samples sound {abs(o)} octave(s) {'above' if o > 0 else 'below'} their keys: "
                             f"play it with transpose={-12 * o} (or write the notes {abs(o)} octave(s) "
                             f"{'lower' if o > 0 else 'higher'})")
            elif any(not r['ok'] for r in rows):
                lines.append('  -> some notes are off (outside +-50 ct): check them by ear / spectrogram')
    return '\n'.join(lines)
