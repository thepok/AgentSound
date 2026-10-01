"""Per-zone level evening for sampled library patches (a lazy instrument's 'post' hook).

Free multisample sets are uneven: VSCO 2 CE notes differ up to 15 dB from one recording to the next, SSO / No Budget
Orchestra a few dB, and VSCO boosts its soft velocity layers for velocity playing (as a live dynamics stack a
crescendo would get quieter). A line played over such a set jumps in level from note to note - the first thing that
makes a sampled instrument sound "keyboard-like". This module keeps measured per-zone corrections in a JSON table
(next to the patch module that uses it) and applies them when a patch's zones are read (stdlib only, no measuring):

    ins = inst.sfz_multi({...}, lazy=True, ...)
    ins.lazy['post'] = ['agentsound.patches.sampled_orchestra:_fix']      # the module's _fix = apply(ins, TABLE)

calibrate() measures a patch and rewrites its entries (a maintainer tool: needs numpy and the built engine):

    python -m agentsound.patches._levelling sampled_orchestra [patch ...]     (the module's CALIBRATION specs)

Per articulation (keyswitch program), in three steps:
  1. round robins of one note -> their mean level (the samples' K-weighted level: the body 0.25-2.5 s of a sustained
     note, the loudest 100 ms of a short one; all channels);
  2. stack=True (layers='dynamics' instruments): each velocity layer is placed under its key range's top layer by the
     RECORDED distance (raw files, without the library's boost for velocity playing): S dB x the velocity distance of
     the layers' midpoints / 127, S the median measured slope, limited so no layer is more than 14 dB under the top -
     one smooth crescendo over the keyboard, alike for ranges with 2 or 3 layers;
  3. the patch is rendered - every key of the articulation's range, alone, at the patch's default dynamics; velocity
     100, or for velocity-layered instruments one velocity per layer plus the crossfade borders - and measured
     (K-weighted, channels summed like LUFS: a long note's body 0.3-1.5 s, a short one's loudest 100 ms); per
     velocity the keys are put on a straight line over the keyboard (least squares, the register's trend kept up to
     +-0.25 dB per semitone); each zone moves by the mean correction of the keys and velocities it sounds at
     (weighted by how much it sounds, capped +-12 dB per pass); twice (overlapping zones settle). The same renders
     judge the tuning (a YIN period check against the key, after the attack): a zone whose notes are 4-35 ct off is
     retuned ('<key>|tune' entries: zone 'tune' in cents); not below C2, not for wavering or unpitched sounds, not
     when the spec says tune=False (bells, drums).
Step 3 hears what the engine plays (controller crossfades, dynamics curves, envelopes, microphone layers), so it works
for any program. The table is keyed '<file path under the sample folder>|<articulation>'.
"""

from __future__ import annotations

import json
import math
import wave
from pathlib import Path

_CACHE: dict = {}


def load_table(path: Path) -> dict:
    key = str(path)
    if key not in _CACHE:
        try:
            _CACHE[key] = json.loads(Path(path).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            _CACHE[key] = {}
    return _CACHE[key]


def _rel(file: str) -> str:
    from ..library import SAMPLES
    f = file.replace('\\', '/')
    root = SAMPLES.as_posix().rstrip('/') + '/'
    if f.lower().startswith(root.lower()):
        return f[len(root):]
    i = f.find('/samples/')
    return f[i + 9:] if i >= 0 else f


def _arts(ins) -> dict:
    """swLast key -> articulation name of an expanded sampler ('' for zones without one)."""
    info = (ins.info or {}).get('sfz') or {}
    return {v: k for k, v in (info.get('keyswitches') or {}).items()}


def _key(z: dict, names: dict) -> str:
    return f"{_rel(z['file'])}|{names.get(z.get('swLast'), '')}"


def apply(ins, table: dict):
    """Add the table's corrections to the zones' gains (in place)."""
    if not table:
        return ins
    names = _arts(ins)
    for z in ins.params.get('samples') or []:
        if isinstance(z, dict) and z.get('file'):
            k = _key(z, names)
            c = table.get(k)
            if c:
                z['gain'] = round(min(48.0, float(z.get('gain', 0.0)) + c), 3)
            t = table.get(k + '|tune')
            if t:
                z['tune'] = round(float(z.get('tune', 0.0)) + t, 1)
    return ins


# --------------------------------------------------------------------------------------------- measuring (numpy)

_LEVELS: dict = {}
_KGRID: dict = {}


def _kweight(sr: float):
    """|H(f)|^2 of the BS.1770 K-weighting (RBJ high shelf +4 dB @ 1.5 kHz, high-pass 38 Hz)."""
    def biquad(b, a):
        def h2(f):
            w = 2 * math.pi * f / sr
            z1, z2 = complex(math.cos(-w), math.sin(-w)), complex(math.cos(-2 * w), math.sin(-2 * w))
            return abs((b[0] + b[1] * z1 + b[2] * z2) / (a[0] + a[1] * z1 + a[2] * z2)) ** 2
        return h2
    A = 10 ** (4.0 / 40)
    w0 = 2 * math.pi * 1500 / sr
    al = math.sin(w0) / (2 * (1 / math.sqrt(2)))
    c = math.cos(w0)
    shelf = biquad((A * ((A + 1) + (A - 1) * c + 2 * math.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
                    A * ((A + 1) + (A - 1) * c - 2 * math.sqrt(A) * al)),
                   ((A + 1) - (A - 1) * c + 2 * math.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
                    (A + 1) - (A - 1) * c - 2 * math.sqrt(A) * al))
    w0 = 2 * math.pi * 38 / sr
    al = math.sin(w0) / (2 * 0.5)
    c = math.cos(w0)
    hp = biquad(((1 + c) / 2, -(1 + c), (1 + c) / 2), (1 + al, -2 * c, 1 - al))
    return lambda f: shelf(f) * hp(f)


def _kpower(seg, sr) -> float:
    """K-weighted mean power of a [n, channels] (or [n]) numpy array."""
    import numpy as np
    if sr not in _KGRID:
        kw = _kweight(sr)
        grid = np.linspace(0, sr / 2, 4096)
        _KGRID[sr] = (grid, np.array([kw(f) for f in grid]))
    grid, kg = _KGRID[sr]
    if seg.ndim == 1:
        seg = seg[:, None]
    spec = np.abs(np.fft.rfft(seg, axis=0)) ** 2
    wgt = np.interp(np.fft.rfftfreq(seg.shape[0], 1.0 / sr), grid, kg)
    return float(np.sum(spec * wgt[:, None]) / seg.shape[0] ** 2 * 2)


def _level(x, sr, short: bool | None = None, body=(0.25, 2.5)) -> float | None:
    """K-weighted level (dB) of a note: the body of a sustained note, else its loudest 100 ms (short=None: decided by
    the note - body within 6 dB of the loudest 100 ms = sustained)."""
    n = x.shape[0]
    if n < 64:
        return None
    win = max(64, int(0.1 * sr))
    peak = max(_kpower(x[i:i + win], sr) for i in range(0, max(1, n - win + 1), win // 2))
    e = peak
    if short is not True and n > (body[0] + 0.3) * sr:
        b = _kpower(x[int(body[0] * sr):int(body[1] * sr)], sr)
        if short is False or b * 4.0 > peak:
            e = b
    return round(10 * math.log10(e), 2) if e > 0 else None


def _read(path: str, offset: int = 0, seconds: float | None = None):
    import numpy as np
    with wave.open(path, 'rb') as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        if offset:
            w.setpos(min(int(offset), max(0, n - 1)))
        raw = w.readframes(n if seconds is None else int(seconds * sr))
    if sw == 2:
        a = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw[:len(raw) // 3 * 3], dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        a = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float64) / float(1 << 23)
    elif sw == 4:
        a = np.frombuffer(raw, dtype='<i4').astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"{path}: {8 * sw}-bit samples")
    return a[:len(a) // ch * ch].reshape(-1, ch), sr


def file_level(path: str, offset: int = 0) -> float | None:
    key = (path, int(offset or 0))
    if key not in _LEVELS:
        try:
            x, sr = _read(path, int(offset or 0), 2.6)
            _LEVELS[key] = _level(x, sr)
        except (OSError, EOFError, ValueError, wave.Error):
            _LEVELS[key] = None
    return _LEVELS[key]


def _psum(levels):
    return 10 * math.log10(sum(10 ** (x / 10) for x in levels)) if levels else None


def _line(pts, max_slope=0.25):
    """Least squares line through (x, y) with the slope clamped; returns f(x)."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx if sxx > 0 else 0.0
    slope = max(-max_slope, min(max_slope, slope))
    return lambda x: my + slope * (x - mx)


def _groups(ins) -> dict:
    """{articulation: {(lo, hi): [zones]}} of the non-release zones with a file."""
    names = _arts(ins)
    arts: dict = {}
    for z in ins.params.get('samples') or []:
        if isinstance(z, dict) and z.get('file') and z.get('trigger') != 'release':
            arts.setdefault(names.get(z.get('swLast'), ''), {}).setdefault(
                (z.get('lo', 0), z.get('hi', 127)), []).append(z)
    return arts


def file_corrections(ins, *, stack: bool, cap_low: float = 36.0, max_range: float = 14.0) -> dict:
    """Steps 1-2: {id(zone): dB} from the sample files (round robins; the dynamics stack)."""
    corr: dict = {}
    for art, ranges in _groups(ins).items():
        played: dict = {}
        raw: dict = {}
        for rng, zs in ranges.items():
            layers: dict = {}
            for z in zs:
                layers.setdefault((z.get('vello', 0), z.get('velhi', 127)), []).append(z)
            for lay, lz in layers.items():
                variants: dict = {}
                for z in lz:                          # round robins; zones of one variant sound together (mics)
                    variants.setdefault((z.get('seqPosition'), z.get('lorand'), z.get('hirand')), []).append(z)
                lv, rv = {}, {}
                for rr, vz in variants.items():
                    ls = [file_level(z['file'], z.get('offset', 0) or 0) for z in vz]
                    if any(x is None for x in ls):
                        continue
                    lv[rr] = _psum([x + float(z.get('gain', 0.0)) for x, z in zip(ls, vz)])
                    rv[rr] = _psum(ls)
                if not lv:
                    continue
                mean = sum(lv.values()) / len(lv)
                if len(lv) > 1:
                    for rr, vz in variants.items():
                        if rr in lv:
                            for z in vz:
                                corr[id(z)] = corr.get(id(z), 0.0) + max(-8.0, min(8.0, mean - lv[rr]))
                played[(rng, lay)] = mean
                raw[(rng, lay)] = sum(rv.values()) / len(rv)
        if not stack:
            continue

        def mid(lay):
            return ((lay[0] or 0) + (127 if lay[1] is None else lay[1])) / 2.0
        tops = {}
        for (rng, lay) in played:
            if rng not in tops or mid(lay) > mid(tops[rng]):
                tops[rng] = lay
        slopes, spans = [], []
        for (rng, lay) in played:
            t = tops[rng]
            if lay != t and mid(t) > mid(lay):
                span = (mid(t) - mid(lay)) / 127.0
                slopes.append(max(0.0, raw[(rng, t)] - raw[(rng, lay)]) / span)
                spans.append(span)
        if not slopes:
            continue
        S = min(sorted(slopes)[len(slopes) // 2], max_range / max(spans))
        for (rng, lay) in played:
            t = tops[rng]
            if lay == t:
                continue
            target = played[(rng, t)] - S * (mid(t) - mid(lay)) / 127.0
            c = max(-cap_low, min(cap_low, target - played[(rng, lay)]))
            for z in ranges[rng]:
                if (z.get('vello', 0), z.get('velhi', 127)) == lay:
                    corr[id(z)] = corr.get(id(z), 0.0) + c
    return corr


_SHORT_WORDS = ('stac', 'spic', 'pizz', 'short', 'hit', 'col legno', 'staccatissimo')


def _is_short(art: str, short_arts) -> bool:
    a = art.lower()
    return '*' in short_arts or a in short_arts or any(w in a for w in _SHORT_WORDS)


def _pitch_near(x, sr, expect):
    """f0 (Hz) of a mono numpy signal judged against the expected pitch: YIN's normalised difference at the expected
    period, half and double of it (local minima within +-4 %); the deepest wins, ties go to the expected period."""
    import numpy as np
    x = x - x.mean()
    L0 = sr / expect
    maxlag = int(2 * L0 * 1.06) + 2
    w = len(x) - maxlag
    if w < 256 or L0 / 2 < 3:
        return None
    lags = np.arange(maxlag + 1)
    n = 1 << int(math.ceil(math.log2(len(x) + w)))            # d(lag) = sum (x[j] - x[j+lag])^2 via FFT
    r = np.fft.irfft(np.conj(np.fft.rfft(x[:w], n)) * np.fft.rfft(x, n), n)[:maxlag + 1]
    c2 = np.concatenate(([0.0], np.cumsum(x * x)))
    d = np.maximum(c2[w] + (c2[lags + w] - c2[lags]) - 2 * r, 0.0)
    cm = np.ones_like(d)
    cm[1:] = d[1:] * lags[1:] / np.maximum(np.cumsum(d[1:]), 1e-12)
    best = []
    for mult in (1.0, 0.5, 2.0):
        c = L0 * mult
        lo, hi = max(2, int(c * 0.96)), min(maxlag - 1, int(c * 1.04) + 1)
        if hi > lo:
            i = lo + int(np.argmin(cm[lo:hi + 1]))
            best.append((cm[i], mult, i))
    ref = [b for b in best if b[1] == 1.0][0]
    low = min(best)
    i = (ref if ref[0] <= low[0] + 0.03 else low)[2]
    a, b, c = cm[i - 1], cm[i], cm[i + 1]
    den = a - 2 * b + c
    return sr / (i + (0.5 * (a - c) / den if den else 0.0))


def _cents(seg, sr, note: int) -> float | None:
    """Tuning (cents) of a rendered note against its key: the median of a few 120 ms windows from 60 ms on while it
    sounds; None when the windows disagree (> 25 ct: a wavering or unpitched sound) or it jumps an octave."""
    import numpy as np
    x = seg.mean(axis=1) if seg.ndim == 2 else seg
    expect = 440.0 * 2 ** ((note - 69) / 12.0)
    dec = 2 if expect < 1200 and sr >= 44100 else 1
    x, fs = x[::dec], sr / dec
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    out = []
    for t0 in (0.16, 0.26, 0.4, 0.55, 0.75, 0.95, 1.15):      # after the attack (a struck bar is sharp at first)
        s = x[int(t0 * fs):int((t0 + 0.12) * fs)]
        if len(s) < 0.1 * fs or peak <= 0 or float(np.max(np.abs(s))) < 0.02 * peak:
            continue
        f = _pitch_near(s, fs, expect)
        if f:
            c = 1200 * math.log2(f / expect)
            if abs(c) < 150:
                out.append(c)
    if len(out) < 3 or max(out) - min(out) > 30.0:
        return None
    return sorted(out)[len(out) // 2]


def render_measure(patch, plan_in, *, short_arts=(), tempo: float = 120.0, pitch=None):
    """Render every (articulation, key, velocity) of plan_in alone with `patch` (no sends) and measure it:
    {(art, key, vel): (dB, cents or None)}."""
    import subprocess
    import tempfile
    from ..cli import find_engine, write_render
    from ..library import REPO
    from ..song import Song
    s = Song('levelling', tempo=tempo, key='C major', seed=1, tail=3.0)
    t = s.track('p', patch.with_mix(sends={}))
    plan = []
    at = 0.0
    for art, k, v in plan_in:
        short = _is_short(art, short_arts)
        dur = 1.0 if short else 3.0
        t.note(k, at, dur, vel=v, art=art or None)
        plan.append((art, k, v, at, dur, short))
        at += dur + 2.0
    s.section('all', bars=int(math.ceil(at / 4)) + 1)
    render = s.compile()
    (REPO / '.scratch').mkdir(exist_ok=True)                  # gitignored; the render is deleted right after
    with tempfile.TemporaryDirectory(prefix='levelling-', dir=REPO / '.scratch') as tmp:
        out = Path(tmp)
        rj = write_render(render, out / 'levelling.render.json')
        r = subprocess.run([str(find_engine(None)), 'render', str(rj), '--out', str(out), '--no-analysis', '--quiet'],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"engine: {r.stderr.strip()}")
        x, sr = _read(str(out / 'mix.wav'))
    spb = 60.0 / tempo
    res = {}
    for art, k, v, st, dur, short in plan:
        seg = x[int(st * spb * sr):int((st + dur + 1.0) * spb * sr)]
        lv = _level(seg[:int(dur * spb * sr)], sr, short=short, body=(0.3, dur * spb))
        if lv is not None and lv > -90:
            res[(art, k, v)] = (lv, _cents(seg, sr, k) if pitch is not None and v == pitch else None)
    return res


def _vel_weight(z: dict, v: float) -> float:
    """How much of zone z sounds at velocity v (its velocity range and velocity crossfades)."""
    lo, hi = z.get('vello', 0) or 0, 127 if z.get('velhi') is None else z['velhi']
    if v < lo or v > hi:
        return 0.0
    w = 1.0
    if 'xfinLo' in z:
        a, b = z['xfinLo'], z.get('xfinHi', z['xfinLo'])
        w *= 1.0 if v >= b else (0.0 if v <= a else (v - a) / max(1e-9, b - a))
    if 'xfoutLo' in z:
        a, b = z['xfoutLo'], z.get('xfoutHi', z['xfoutLo'])
        w *= 1.0 if v <= a else (0.0 if v >= b else (b - v) / max(1e-9, b - a))
    return w


def _layer_vels(ins, stack: bool) -> list:
    """Velocities that sound each velocity layer on its own (the middle of where it plays at full weight); [100] for a
    dynamics stack or an instrument without velocity layers."""
    if stack:
        return [100]
    vs = set()
    for z in ins.params.get('samples') or []:
        if not isinstance(z, dict) or not z.get('file') or z.get('trigger') == 'release':
            continue
        lo, hi = z.get('vello', 0) or 0, 127 if z.get('velhi') is None else z['velhi']
        a = max(lo, z.get('xfinHi', lo)) if 'xfinLo' in z else lo
        b = min(hi, z.get('xfoutLo', hi)) if 'xfoutLo' in z else hi
        if (lo, hi) != (0, 127) or 'xfinLo' in z or 'xfoutLo' in z:
            vs.add(int(round(min(127, max(12, (a + b) / 2.0)))))
    vs = sorted(vs)
    while len(vs) > 5:                                         # at most 5 layers: merge the closest neighbours
        i = min(range(len(vs) - 1), key=lambda j: vs[j + 1] - vs[j])
        vs[i:i + 2] = [int(round((vs[i] + vs[i + 1]) / 2))]
    mids = [int(round((a + b) / 2)) for a, b in zip(vs, vs[1:]) if b - a >= 16]   # crossfade / layer borders too
    return sorted(set(vs + mids)) or [100]


def render_corrections(patch, ins, corr: dict, tune: dict | None, *, stack: bool = False, short_arts=(),
                       cap: float = 12.0, min_cents: float = 4.0, max_cents: float = 35.0):
    """Step 3 (one pass): level corrections {id(zone): dB} added to corr and - when tune is a dict - tuning corrections
    {id(zone): cents} added to it, from the rendered patch. Velocity-layered instruments are measured at a velocity
    per layer; each zone takes the deviations at the velocities it sounds at, weighted by how much it sounds."""
    groups = _groups(ins)
    tr = int(ins.params.get('transpose', 0) or 0)            # notes play zone key - transpose
    vels = _layer_vels(ins, stack)
    arts_keys = {art: sorted({k for (lo, hi) in ranges for k in range(lo, hi + 1) if 0 <= k - tr <= 127})
                 for art, ranges in groups.items()}
    plan = [(a, k - tr, v) for a, ks in arts_keys.items() for k in ks for v in vels]
    pv = None if tune is None else min(vels, key=lambda x: abs(x - 100))     # tuning: judged at one velocity
    played = render_measure(patch, plan, short_arts=short_arts, pitch=pv)
    m = {(a, k + tr, v): val for (a, k, v), val in played.items()}
    for art, ranges in groups.items():
        dev: dict = {}                                        # (key, vel) -> dB to the line of that velocity
        for v in vels:
            pts = [(k, m[(art, k, v)][0]) for k in arts_keys[art] if (art, k, v) in m]
            if len(pts) >= 2:
                f = _line(pts)
                for k, y in pts:
                    dev[(k, v)] = f(k) - y
        for (lo, hi), zs in ranges.items():
            for z in zs:
                num = den = 0.0
                for v in vels:
                    w = 1.0 if len(vels) == 1 else _vel_weight(z, v)
                    for k in range(lo, hi + 1):
                        if w > 0 and (k, v) in dev:
                            num += w * dev[(k, v)]
                            den += w
                if den > 0:
                    corr[id(z)] = corr.get(id(z), 0.0) + max(-cap, min(cap, num / den))
            if tune is None or (lo + hi) / 2.0 - tr < 36:         # below C2 a period detector is no judge
                continue
            cs = sorted(m[(art, k, v)][1] for k in range(lo, hi + 1) for v in vels
                        if (art, k, v) in m and m[(art, k, v)][1] is not None)
            if cs:
                d = cs[len(cs) // 2]
                if min_cents < abs(d) <= max_cents:                # larger: a misread (or a deliberate) pitch
                    for z in zs:
                        tune[id(z)] = max(-max_cents, min(max_cents, tune.get(id(z), 0.0) - d))
    return corr, tune


def _entries(ins, corr: dict, tune: dict | None = None) -> dict:
    names = _arts(ins)
    out = {}
    for z in ins.params.get('samples') or []:
        if isinstance(z, dict) and z.get('file'):
            if abs(corr.get(id(z), 0.0)) >= 0.05:
                out[_key(z, names)] = round(corr[id(z)], 2)
            if tune and abs(tune.get(id(z), 0.0)) >= 0.5:
                out[_key(z, names) + '|tune'] = round(tune[id(z)], 1)
    return out


def calibrate(patch_names, table_path: Path, specs: dict, passes: int = 2) -> dict:
    """Measure `patch_names` and rewrite their entries in the JSON table at table_path. specs: {patch name: {'stack':
    bool, 'short': [articulation names measured as shorts], 'tune': bool, 'keys': (lo, hi) the played range (MIDI;
    zones outside it - effect or noise keys - are left alone)}}."""
    from . import get
    table = dict(load_table(table_path))
    for name in patch_names:
        spec = specs.get(name, {})
        patch = get(name)
        ins = patch.instrument
        lazy = dict(ins.lazy or {})
        lazy.pop('post', None)
        ins.lazy = lazy
        ins.expand()
        names = _arts(ins)
        for z in ins.params.get('samples') or []:          # a re-calibration replaces the patch's old entries
            if isinstance(z, dict) and z.get('file'):
                table.pop(_key(z, names), None)
                table.pop(_key(z, names) + '|tune', None)
        if spec.get('keys'):                               # only the notes: effect / noise keys keep their level
            lo, hi = spec['keys']
            tr = int(ins.params.get('transpose', 0) or 0)
            ins.params['samples'] = [z for z in ins.params['samples']
                                     if lo <= z.get('lo', 0) - tr and z.get('hi', 127) - tr <= hi]
        corr = file_corrections(ins, stack=spec.get('stack', False))
        tune = {} if spec.get('tune', True) else None
        for _ in range(passes):
            _write(table_path, {**table, **_entries(ins, corr, tune)})
            corr, tune = render_corrections(get(name), ins, corr, tune, stack=spec.get('stack', False),
                                             short_arts=tuple(spec.get('short', ())))
        new = _entries(ins, corr, tune)
        table.update(new)
        _write(table_path, table)
        gains = [abs(v) for k, v in new.items() if not k.endswith('|tune')]
        tunes = {k: v for k, v in new.items() if k.endswith('|tune')}
        print(f"{name}: {len(gains)} zone level corrections (max {max(gains, default=0):.1f} dB), {len(tunes)} retuned"
              + (': ' + ', '.join(f"{k.split('/')[-1].split('|')[0]} {v:+.0f}" for k, v in
                                  sorted(tunes.items(), key=lambda kv: -abs(kv[1]))[:6]) if tunes else ''))
    return table


def _write(path: Path, table: dict) -> None:
    Path(path).write_text(json.dumps(dict(sorted(table.items())), indent=0) + '\n', encoding='utf-8')
    _CACHE.pop(str(path), None)


if __name__ == '__main__':
    import importlib
    import sys
    if len(sys.argv) < 2:
        raise SystemExit('usage: python -m agentsound.patches._levelling MODULE [patch ...]   '
                         '(MODULE: sampled_orchestra)')
    mod = importlib.import_module(f'agentsound.patches.{sys.argv[1]}')
    canon = importlib.import_module('agentsound.patches._levelling')   # the module the patches' hooks read (its cache)
    canon.calibrate(sys.argv[2:] or list(mod.CALIBRATION), mod.LEVEL_TABLE, mod.CALIBRATION)
