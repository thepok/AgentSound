"""The mastering engineer: match a finished mix to a target (a reference track or the genre profile), check a
master against delivery targets, and apply the result - to the song's master chain or as a post-pass on mix.wav.

    from agentsound import mastering
    plan = mastering.match('songs/<slug>', ref='assets/refrences/x.opus', ref_start='1:02', ref_end='1:32',
                           section='chorus', platform='streaming')
    print(plan.describe())              # every decision with its reason (also out/master/master.json)
    res = plan.render()                 # post-pass: out/master/mastered.wav (+ mp3, report, before/after numbers)
    plan.apply(song)                    # or: the same settings into song.master (eq first, width, limiter)
    mastering.apply(song, eq={...}, width=1.1, limiter={'gain': 3.5, 'ceiling': -1.2})   # what plan.snippet() prints

    findings = mastering.check('songs/<slug>', platform='streaming')   # true peak, loudness, LRA, tone, mono, DC ...

    python -m agentsound master songs/<slug> [--ref X --ref-start --ref-end] [--section S]
                                             [--platform auto|streaming|loud|dynamic] [--render] [--check]

Nothing here is genre-specific code: the genre comes in as data - the analysis profile of the song (its loudness
window, LRA range, PLR floor, width targets, reference spectrum) and the platform preset (PLATFORMS). A reference
track, when given, replaces the profile's spectrum and width as the tonal target; the profile still caps loudness.

Rules the engineer keeps (a mastering move is small and broad; the mix is fixed in the mix):
- tone: the loudness-matched 1/3-octave difference (compare machinery), smoothed over ~1 octave, a dead band
  (1 dB vs a reference, 1.5 dB vs a genre profile), `strength` of the rest, fitted with at most a low shelf, three
  broad bells (Q <= 1) and a high shelf; every band and the summed curve within +-`max_db` (3 dB); only 31.5 Hz ..
  12.5 kHz is judged (a lossy reference - Opus/YouTube - has nothing reliable at and above 16 kHz, and neither
  does the reference's own low-pass: compare's `bandLimitedAboveHz`).
- loudness: the platform's target, else the reference's loudness clamped into the profile's window, else the
  nearest edge of the window (a mix inside it keeps its level); never above the window's top, never below the PLR
  floor (true-peak target - PLR minimum), and for `dynamic` at most ~1.5 dB of peak limiting.
- width: towards the reference's (or into the profile's) width above 150 Hz, x0.85 .. x1.25, never widening a
  mix whose correlation is already low; lows made mono (monobass 120 Hz) when they are not.
- limiter: ceiling 0.2 dB under the true-peak target (the engine's limiter is true-peak aware), release by
  platform; its gain is estimated for the song chain and calibrated exactly in the post-pass (render()).
Deterministic: the same inputs give the same plan and bit-identical post-pass audio.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import compare as _cmp
from .theory import ComposeError

__all__ = ['PLATFORMS', 'Platform', 'MasterPlan', 'MasteringError', 'match', 'check', 'apply', 'render',
           'fit_eq', 'eq_response_db', 'get_platform', 'summary_lines', 'check_lines', 'result_lines']


class MasteringError(ComposeError):
    pass


# ------------------------------------------------------------------------------------------ platforms

@dataclass(frozen=True)
class Platform:
    """A delivery target. lufs: a number (LUFS-I), 'profile-top' (the genre window's top, loud masters) or None
    (the reference / the genre window decides). tp: true-peak ceiling (dBTP). max_limit_db: most peak limiting the
    loudness may cost (None = no cap). release: limiter release (ms). window: the loudness window the post-pass
    report judges against (None: the profile's). density_db: how much lower the master's crest factor may get than
    the reference's (None: not judged; 'dynamic' judges it against the mix's own crest)."""
    name: str
    lufs: object
    tp: float
    release: float
    max_limit_db: float | None
    window: tuple | None
    density_db: float | None
    about: str


PLATFORMS: dict[str, Platform] = {
    'auto': Platform('auto', None, -1.0, 120.0, 3.0, None, 1.5,
                     "the genre profile decides: the reference's loudness clamped into the profile's window, else the "
                     "nearest edge of the window (a mix inside it keeps its level); at most 3 dB of extra peak limiting; "
                     "-1 dBTP"),
    'streaming': Platform('streaming', -14.0, -1.0, 150.0, 4.0, (-15.0, -13.0), 1.5,
                          "Spotify / YouTube / Tidal / Amazon normalise to -14 LUFS (Apple Music -16): a louder master "
                          "is only turned down, so -14 LUFS-I at -1 dBTP keeps every dB of dynamics"),
    'loud': Platform('loud', 'profile-top', -1.0, 60.0, 6.0, None, 3.0,
                     "club / DJ / loud genre master: the top of the genre profile's loudness window (0.5 LU under it), "
                     "capped by its PLR floor, up to 6 dB of extra peak limiting; -1 dBTP"),
    'dynamic': Platform('dynamic', None, -1.0, 250.0, 1.5, None, 1.0,
                        "classical / jazz / acoustic: dynamics first - never above the middle of the profile's window "
                        "and at most ~1.5 dB of extra peak limiting; slow limiter release"),
}
_ALIASES = {'club': 'loud', 'classical': 'dynamic', 'piano': 'dynamic', 'jazz': 'dynamic', 'acoustic': 'dynamic', 'spotify': 'streaming',
            'youtube': 'streaming', None: 'auto', '': 'auto'}
# Loudness normalisation of the big services (for check's notes).
NORMALISATION = (('Spotify / YouTube / Tidal / Amazon', -14.0), ('Apple Music', -16.0))


def get_platform(name) -> Platform:
    if isinstance(name, Platform):
        return name
    key = _ALIASES.get(name, name)
    if key not in PLATFORMS:
        raise MasteringError(f"unknown mastering platform {name!r}; platforms: {', '.join(PLATFORMS)} "
                             f"(aliases: {', '.join(k for k in _ALIASES if k)})")
    return PLATFORMS[key]


# ------------------------------------------------------------------------------------------ eq model

def _bell_db(f, f0, gain, q):
    """Magnitude (dB) of the engine's bell (matched to the analog prototype) at f."""
    if gain == 0:
        return 0.0
    a = 10 ** (gain / 40.0)
    w = f / f0
    re_n, im_n = 1 - w * w, w * a / q
    re_d, im_d = 1 - w * w, w / (a * q)
    return 10 * math.log10((re_n ** 2 + im_n ** 2) / (re_d ** 2 + im_d ** 2))


def _shelf_db(f, f0, gain, q, high):
    """Magnitude (dB) of the engine's low / high shelf (RBJ analog prototype) at f."""
    if gain == 0:
        return 0.0
    a = 10 ** (gain / 40.0)
    w = f / f0
    sa = math.sqrt(a) / q
    if not high:   # A (s^2 + sa s + A) / (A s^2 + sa s + 1)
        num = (a - w * w) ** 2 + (sa * w) ** 2
        den = (1 - a * w * w) ** 2 + (sa * w) ** 2
    else:          # A (A s^2 + sa s + 1) / (s^2 + sa s + A)
        num = (1 - a * w * w) ** 2 + (sa * w) ** 2
        den = (a - w * w) ** 2 + (sa * w) ** 2
    return 20 * math.log10(a) + 10 * math.log10(num / den)


def _band_db(kind, f, freq, gain, q):
    if kind == 'low':
        return _shelf_db(f, freq, gain, q, False)
    if kind == 'high':
        return _shelf_db(f, freq, gain, q, True)
    return _bell_db(f, freq, gain, q)


def eq_response_db(params: dict, hz) -> list[float]:
    """The summed magnitude (dB) of an eq's shelves and bells (render-format params) at the frequencies hz."""
    out = []
    for f in hz:
        s = 0.0
        for name, kind, dq in (('low', 'low', 0.7071), ('peak1', 'bell', 1.0), ('peak2', 'bell', 1.0),
                               ('peak3', 'bell', 1.0), ('high', 'high', 0.7071)):
            g = params.get(f'{name}.gain', 0.0)
            if g:
                dfreq = {'low': 100.0, 'peak1': 200.0, 'peak2': 1000.0, 'peak3': 5000.0, 'high': 8000.0}[name]
                s += _band_db(kind, f, params.get(f'{name}.freq', dfreq), g, params.get(f'{name}.q', dq))
        out.append(s)
    return out


# Candidate filters of the fit: broad moves only.
_LOW_SHELF_HZ = (60, 80, 100, 125, 160, 200, 250)
_HIGH_SHELF_HZ = (3000, 4000, 5000, 6300, 8000, 10000)
_BELL_HZ = (63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000,
            6300, 8000, 10000)
_BELL_Q = (0.5, 0.7, 1.0)
FIT_LOW_HZ, FIT_HIGH_HZ = 31.5, 12500.0     # judged range (no reliable reference data at 16 kHz and above)


def _weights(hz, valid):
    w = []
    for f, v in zip(hz, valid):
        if not v or f < FIT_LOW_HZ - 0.1 or f > FIT_HIGH_HZ + 0.1:
            w.append(0.0)
        elif f < 50 or f > 10000:
            w.append(0.5)
        else:
            w.append(1.0)
    return w


def smooth_octave(hz, diff, valid) -> list:
    """Diff smoothed over ~1 octave (triangular weights over +-3 third-octave bands), None where invalid."""
    out = []
    for i in range(len(hz)):
        if not valid[i]:
            out.append(None)
            continue
        num = den = 0.0
        for k in range(i - 3, i + 4):
            if 0 <= k < len(hz) and valid[k] and diff[k] is not None:
                wt = 4 - abs(k - i)
                num += wt * diff[k]
                den += wt
        out.append(num / den if den else None)
    return out


def _median(vals):
    v = sorted(vals)
    if not v:
        return 0.0
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def correction_curve(hz, diff, valid, *, dead_db: float, strength: float, max_db: float):
    """The wanted eq curve (dB, None where not judged) that moves a mix whose spectrum differs by `diff`
    (mix - target, dB per third-octave band) towards the target: smoothed, re-centred on its median (the mids
    are the anchor, loudness is the limiter's job), dead band, strength, clamp."""
    w = _weights(hz, valid)
    sm = smooth_octave(hz, diff, [v and wt > 0 for v, wt in zip(valid, w)])
    judged = [s for s, wt in zip(sm, w) if s is not None and wt > 0]
    centre = _median(judged)
    out = []
    for s, wt in zip(sm, w):
        if s is None or wt <= 0:
            out.append(None)
            continue
        d = s - centre
        mag = max(0.0, abs(d) - dead_db) * strength
        out.append(max(-max_db, min(max_db, -math.copysign(mag, d))))
    return out, round(centre, 2)


def profile_guard(hz, wanted, bands_vs_ref: dict | None, limits: dict | None, margin: float = 0.75):
    """Keeps a (reference) correction inside the genre profile's band balance: no band may be pushed past its limit
    (report reference.bandLimitsDb, relative to the mix's bandsVsRefDb) - an old, dark or mono reference record
    must not make a modern mix thin or dull. A band already outside is not pushed further out. Returns (wanted,
    {band: (lowest, highest) allowed dB} of the bands that limited the curve)."""
    if not bands_vs_ref or not limits:
        return list(wanted), {}
    out, hit = [], {}
    for f, w in zip(hz, wanted):
        if w is None:
            out.append(None)
            continue
        band = _cmp.band_of(f)
        now = bands_vs_ref.get(band)
        lim = limits.get(band) or {}
        if not isinstance(now, (int, float)):
            out.append(w)
            continue
        hi = max(0.0, lim['high'] - margin - now) if isinstance(lim.get('high'), (int, float)) else float('inf')
        lo = min(0.0, lim['low'] + margin - now) if isinstance(lim.get('low'), (int, float)) else float('-inf')
        v = min(hi, max(lo, w))
        if v != w:
            hit[band] = (None if lo == float('-inf') else round(lo, 1), None if hi == float('inf') else round(hi, 1))
        out.append(v)
    return out, hit


def fit_eq(hz, wanted, *, max_db: float = 3.0, max_bells: int = 3, min_gain: float = 0.5):
    """Fit render-format eq params (low shelf, <= 3 broad bells, high shelf) to a wanted curve (dB per band, None
    = not judged). Greedy + coordinate refinement, every gain within +-max_db and the summed curve too.
    Deterministic. Returns (params, achieved curve, rms error dB)."""
    idx = [i for i, v in enumerate(wanted) if v is not None]
    if not idx or all(abs(wanted[i]) < 0.25 for i in idx):
        return {}, [0.0 if v is not None else None for v in wanted], 0.0
    fs = [hz[i] for i in idx]
    target = [wanted[i] for i in idx]
    wts = [0.5 if (f < 50 or f > 10000) else 1.0 for f in fs]

    def resp(flt, gain):
        kind, freq, q = flt
        return [_band_db(kind, f, freq, gain, q) for f in fs]

    def err(cur):
        return sum(wt * (t - c) ** 2 for wt, t, c in zip(wts, target, cur)) / sum(wts)

    cands = [('low', f, 0.7071) for f in _LOW_SHELF_HZ] + [('high', f, 0.7071) for f in _HIGH_SHELF_HZ] + \
            [('bell', f, q) for f in _BELL_HZ for q in _BELL_Q]
    chosen: list[list] = []      # [kind, freq, q, gain]
    cur = [0.0] * len(fs)
    for _ in range(2 + max_bells):
        base = err(cur)
        best = None
        for kind, freq, q in cands:
            if kind in ('low', 'high') and any(c[0] == kind for c in chosen):
                continue
            if kind == 'bell' and sum(c[0] == 'bell' for c in chosen) >= max_bells:
                continue
            unit = resp((kind, freq, q), 1.0)
            den = sum(wt * u * u for wt, u in zip(wts, unit))
            if den <= 1e-9:
                continue
            g = sum(wt * (t - c) * u for wt, t, c, u in zip(wts, target, cur, unit)) / den
            g = max(-max_db, min(max_db, round(g * 10) / 10))
            if abs(g) < min_gain:
                continue
            r = resp((kind, freq, q), g)
            e = err([c + x for c, x in zip(cur, r)])
            if best is None or e < best[0] - 1e-12:
                best = (e, [kind, freq, q, g])
        if best is None or base - best[0] < 0.02 * max(base, 0.05):
            break
        chosen.append(best[1])
        cur = [c + x for c, x in zip(cur, resp(tuple(best[1][:3]), best[1][3]))]
    # Coordinate refinement of the gains (0.1 dB steps).
    for _ in range(6):
        changed = False
        for c in chosen:
            others = [0.0] * len(fs)
            for o in chosen:
                if o is not c:
                    others = [a + b for a, b in zip(others, resp(tuple(o[:3]), o[3]))]
            best_g, best_e = c[3], None
            for step in (-0.3, -0.1, 0.0, 0.1, 0.3):
                g = max(-max_db, min(max_db, round((c[3] + step) * 10) / 10))
                e = err([a + b for a, b in zip(others, resp(tuple(c[:3]), g))])
                if best_e is None or e < best_e - 1e-12:
                    best_g, best_e = g, e
            if best_g != c[3]:
                c[3], changed = best_g, True
        if not changed:
            break
    chosen = [c for c in chosen if abs(c[3]) >= min_gain]
    params = _to_params(chosen)
    # The summed curve stays within +-max_db (two moves on top of each other must not add up past it).
    full = eq_response_db(params, [hz[i] for i in idx])
    peak = max((abs(v) for v in full), default=0.0)
    if peak > max_db + 1e-6:
        k = max_db / peak
        for c in chosen:
            c[3] = math.trunc(c[3] * k * 10) / 10
        chosen = [c for c in chosen if abs(c[3]) >= min_gain]
        params = _to_params(chosen)
    achieved_j = eq_response_db(params, fs)
    achieved: list = [None] * len(wanted)
    for i, v in zip(idx, achieved_j):
        achieved[i] = round(v, 2)
    rms = math.sqrt(err(achieved_j))
    return params, achieved, round(rms, 2)


def _to_params(chosen) -> dict:
    params: dict = {}
    bells = sorted((c for c in chosen if c[0] == 'bell'), key=lambda c: c[1])
    for c in chosen:
        if c[0] == 'low':
            params.update({'low.freq': c[1], 'low.gain': c[3], 'low.q': 0.7071})
        elif c[0] == 'high':
            params.update({'high.freq': c[1], 'high.gain': c[3], 'high.q': 0.7071})
    for n, c in enumerate(bells, 1):
        params.update({f'peak{n}.freq': c[1], f'peak{n}.gain': c[3], f'peak{n}.q': c[2]})
    return params


def describe_eq(params: dict) -> str:
    if not params:
        return 'no eq'
    parts = []
    if params.get('low.gain'):
        parts.append(f"{params['low.gain']:+.1f} dB low shelf {_cmp.fmt_hz(params['low.freq'])}")
    for n in (1, 2, 3):
        if params.get(f'peak{n}.gain'):
            parts.append(f"{params[f'peak{n}.gain']:+.1f} dB bell {_cmp.fmt_hz(params[f'peak{n}.freq'])} "
                         f"Q {params[f'peak{n}.q']:g}")
    if params.get('high.gain'):
        parts.append(f"{params['high.gain']:+.1f} dB high shelf {_cmp.fmt_hz(params['high.freq'])}")
    return ', '.join(parts)


# ------------------------------------------------------------------------------------------ loudness helpers

def _k_weight_db(f: float) -> float:
    """Approximate K-weighting (BS.1770 pre-filter: +4 dB shelf around 1.5 kHz, high-pass ~38 Hz), dB."""
    shelf = _shelf_db(f, 1680.0, 4.0, 0.7071, True)
    w = f / 38.0
    hp = 10 * math.log10(w ** 4 / ((1 - w * w) ** 2 + (w * 2.0) ** 2) + 1e-30)   # 2nd-order, Q 0.5
    return shelf + hp


def eq_loudness_change(spectrum_hz, spectrum_db, eq_params: dict) -> float:
    """Estimated change of integrated loudness (LU) an eq causes on a mix with this 1/3-octave spectrum (dBFS)."""
    if not eq_params:
        return 0.0
    num = den = 0.0
    resp = eq_response_db(eq_params, spectrum_hz)
    for f, db, r in zip(spectrum_hz, spectrum_db, resp):
        if db is None or db <= -120:
            continue
        p = 10 ** ((db + _k_weight_db(f)) / 10)
        den += p
        num += p * 10 ** (r / 10)
    return 10 * math.log10(num / den) if den > 0 and num > 0 else 0.0


def width_loudness_change(width_pct: float | None, factor: float) -> float:
    """LU change when the side signal is scaled by `factor` (width_pct = side/mid energy %)."""
    if width_pct is None or factor == 1.0:
        return 0.0
    w = max(0.0, width_pct) / 100.0
    return 10 * math.log10((1 + factor * factor * w) / (1 + w))


# ------------------------------------------------------------------------------------------ inputs

@dataclass
class _Source:
    wav: Path
    song_dir: Path | None
    report: dict
    render: dict
    out: Path


def _load_json(p: Path):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _source(song_or_mix, out=None) -> _Source:
    p = Path(song_or_mix)
    if p.is_file() and p.suffix.lower() == '.py':
        p = p.parent
    if p.is_dir():
        wav = p / 'out' / 'mix.wav'
        if not wav.is_file():
            raise MasteringError(f"no render at {wav}: build the song first (python -m agentsound build {p})")
        rep = _load_json(p / 'out' / 'report.json') or {}
        ren = _load_json(p / 'out' / 'song.render.json') or {}
        return _Source(wav, p, rep, ren, Path(out) if out else p / 'out' / 'master')
    if p.is_file() and p.suffix.lower() == '.wav':
        rep = _load_json(p.parent / 'report.json') or {}
        ren = _load_json(p.parent / 'song.render.json') or {}
        return _Source(p, None, rep, ren, Path(out) if out else p.parent / (p.stem + '_master'))
    raise MasteringError(f"{song_or_mix}: expected a song folder (songs/<slug> with out/mix.wav), a song.py or a .wav")


def wav_info(path: Path) -> dict:
    """{'rate', 'channels', 'frames', 'bits', 'format'} of a RIFF WAV (PCM or float, WAVE_FORMAT_EXTENSIBLE too)."""
    with open(path, 'rb') as f:
        head = f.read(12)
        if len(head) < 12 or head[:4] != b'RIFF' or head[8:12] != b'WAVE':
            raise MasteringError(f"{path} is not a WAV file")
        fmt = None
        while True:
            ch = f.read(8)
            if len(ch) < 8:
                break
            cid, size = ch[:4], struct.unpack('<I', ch[4:])[0]
            if cid == b'fmt ':
                d = f.read(size)
                tag, chans, rate, _, align, bits = struct.unpack('<HHIIHH', d[:16])
                fmt = (tag, chans, rate, align, bits)
                f.seek(size & 1, 1)
            elif cid == b'data':
                if fmt is None:
                    break
                return {'format': fmt[0], 'channels': fmt[1], 'rate': fmt[2], 'bits': fmt[4],
                        'frames': size // max(1, fmt[3])}
            else:
                f.seek(size + (size & 1), 1)
    raise MasteringError(f"{path}: no fmt/data chunk")


def _engine(engine=None) -> Path:
    from .cli import CliError, find_engine
    try:
        return find_engine(str(engine) if engine else None)
    except CliError as e:
        raise MasteringError(str(e)) from None


def _ffmpeg(ffmpeg=None) -> str | None:
    if ffmpeg:
        return str(ffmpeg)
    from .cli import find_ffmpeg
    return find_ffmpeg()


def _profile_of(src: _Source, profile) -> str:
    if profile:
        from .cli import ANALYSIS_PROFILES
        if profile not in ANALYSIS_PROFILES:
            raise MasteringError(f"unknown analysis profile {profile!r} (profiles: {', '.join(ANALYSIS_PROFILES)})")
        return profile
    ref = src.report.get('reference') if isinstance(src.report.get('reference'), dict) else {}
    return ref.get('profile') or (src.render.get('analysis') or {}).get('profile') or 'default'


def _sections(src: _Source) -> list[tuple[str, float, float]]:
    out = []
    for s in src.report.get('sections') or []:
        if isinstance(s, dict) and not s.get('implicit') and 'startSec' in s and 'endSec' in s:
            if float(s['endSec']) > float(s['startSec']):
                out.append((str(s['name']), float(s['startSec']), float(s['endSec'])))
    return out


def _tempo(src: _Source):
    info = src.report.get('render') if isinstance(src.report.get('render'), dict) else {}
    return info.get('tempo') or src.render.get('tempo')


# ------------------------------------------------------------------------------------------ the plan

@dataclass
class MasterPlan:
    """What the mastering engineer decided (match()). chain() / patch() / apply(song) / render() use it."""
    source: str
    song_dir: str | None
    out: str
    profile: str
    platform: str
    reference: dict | None
    measured: dict
    targets: dict
    eq: dict
    width: dict | None
    limiter: dict
    estimate: dict
    curve: dict
    log: list = field(default_factory=list)
    analysis: dict = field(default_factory=dict)

    # -- the chain
    def chain(self) -> list:
        """The post-pass master chain as FX objects: eq -> width -> limiter (render format via .to_dict())."""
        return _chain(self.eq, self.width, self.limiter)

    def patch(self, name: str = 'master/matched', register: bool = False):
        """The chain as an fx-chain Patch (song.master.use(plan.patch()) for a song WITHOUT a master chain of its own;
        a song with one: plan.apply(song))."""
        from . import patches
        p = patches.Patch(name, fx=self.chain(), notes='mastering.match: ' + '; '.join(self.log[:3]))
        if register:
            patches.register(p)
        return p

    def settings(self) -> dict:
        """The keyword arguments of mastering.apply() for the song's own master chain."""
        return {'eq': dict(self.eq) or None, 'width': (self.width or {}).get('width'),
                'monobass': (self.width or {}).get('monobass'), 'limiter': dict(self.limiter),
                'loudness_change': self.estimate.get('songLimiterGainChange')}

    def snippet(self) -> str:
        """Python for song.py: the same settings into the song's master chain (deterministic, no files needed)."""
        s = self.settings()
        args = []
        if s['eq']:
            args.append(f"eq={json.dumps(s['eq'])}")
        if s['width'] is not None and s['width'] != 1.0:
            args.append(f"width={s['width']:g}")
        if s['monobass']:
            args.append(f"monobass={s['monobass']:g}")
        lim = {k: v for k, v in s['limiter'].items() if k in ('ceiling', 'release')}
        args.append(f"limiter={json.dumps(lim)}")
        if s['loudness_change']:
            args.append(f"loudness_change={s['loudness_change']:+.1f}")
        return f"mastering.apply(s, {', '.join(args)})"

    def apply(self, song) -> list[str]:
        """Put the plan into song.master (see mastering.apply). The eq was measured on the mastered mix, so it goes
        first; the limiter gain moves by the estimated loudness change - re-build and check the numbers."""
        s = self.settings()
        return apply(song, eq=s['eq'], width=s['width'], monobass=s['monobass'],
                     limiter={k: v for k, v in s['limiter'].items() if k in ('ceiling', 'release')},
                     loudness_change=s['loudness_change'])

    def render(self, **kw) -> dict:
        return render(self, **kw)

    def to_dict(self) -> dict:
        return {'format': 'agentsound.master', 'version': 1, 'source': self.source, 'songDir': self.song_dir,
                'out': self.out, 'profile': self.profile, 'platform': self.platform, 'reference': self.reference,
                'measured': self.measured, 'targets': self.targets, 'eq': self.eq, 'width': self.width,
                'limiter': self.limiter, 'estimate': self.estimate, 'chain': [f.to_dict() for f in self.chain()],
                'snippet': self.snippet(), 'curve': self.curve, 'analysis': self.analysis, 'log': self.log}

    @classmethod
    def from_dict(cls, d: dict) -> 'MasterPlan':
        if not isinstance(d, dict) or d.get('format') != 'agentsound.master':
            raise MasteringError("not a mastering plan (format 'agentsound.master')")
        return cls(source=d['source'], song_dir=d.get('songDir'), out=d['out'], profile=d['profile'],
                   platform=d['platform'], reference=d.get('reference'), measured=d['measured'],
                   targets=d['targets'], eq=d.get('eq') or {}, width=d.get('width'), limiter=d['limiter'],
                   estimate=d.get('estimate') or {}, curve=d.get('curve') or {}, log=list(d.get('log') or []),
                   analysis=d.get('analysis') or {})

    @classmethod
    def load(cls, path) -> 'MasterPlan':
        d = _load_json(Path(path))
        if d is None:
            raise MasteringError(f"no readable plan at {path}")
        return cls.from_dict(d)

    def save(self, path=None) -> Path:
        p = Path(path) if path else Path(self.out) / 'master.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        return p

    def describe(self) -> str:
        return '\n'.join(summary_lines(self))


def _chain(eq: dict | None, width: dict | None, limiter: dict) -> list:
    from .patches import FX
    out = []
    if eq:
        out.append(FX('eq', dict(eq), name='master_eq'))
    if width:
        out.append(FX('width', dict(width)))
    out.append(FX('limiter', dict(limiter)))
    return out


def _r(x, n=1):
    return None if x is None else round(float(x), n)


def match(song_or_mix, *, ref=None, ref_start=None, ref_end=None, section: str | None = None, profile: str | None = None,
          platform=None, strength: float = 0.75, max_db: float = 3.0, width_range=(0.85, 1.25),
          engine=None, ffmpeg=None, out=None, save: bool = True) -> MasterPlan:
    """Derive a master chain for a finished mix (see the module doc for the rules).

    song_or_mix  songs/<slug> (its out/mix.wav, report, render JSON), a song.py or any .wav
    ref          reference audio (anything ffmpeg decodes); ref_start / ref_end: the excerpt (chorus vs chorus)
    section      judge the tone on this section of the song (with ref: compare like with like)
    profile      the analysis profile (default: the song's) - loudness window, PLR floor, width, genre spectrum
    platform     'auto' (default) | 'streaming' (-14 LUFS, -1 dBTP) | 'loud' (club: the genre window's top) |
                 'dynamic' (classical / jazz: dynamics first) - or a Platform
    strength     share of the (dead-banded) tonal difference to correct, 0..1; max_db: +-limit of every eq move
    Writes <out>/master.json (default songs/<slug>/out/master/) and returns the MasterPlan."""
    plat = get_platform(platform)
    if not 0.0 <= strength <= 1.0:
        raise MasteringError(f"strength must be 0..1, got {strength!r}")
    if not 0.5 <= max_db <= 6.0:
        raise MasteringError(f"max_db must be 0.5..6, got {max_db!r}")
    lo_w, hi_w = width_range
    if not 0.5 <= lo_w <= 1.0 <= hi_w <= 1.6:
        raise MasteringError(f"width_range must be (0.5..1, 1..1.6), got {width_range!r}")
    src = _source(song_or_mix, out)
    eng = _engine(engine)
    prof = _profile_of(src, profile)
    outd = src.out
    outd.mkdir(parents=True, exist_ok=True)
    log: list[str] = []

    # --- analyse the mix (the whole song or the section) the way compare does
    a = b = None
    tempo = _tempo(src)
    start_beat = 0.0
    label = f"{src.report.get('render', {}).get('title') or (src.song_dir.name if src.song_dir else src.wav.stem)}"
    if section:
        secs = {n: (x, y) for n, x, y in _sections(src)}
        if section not in secs:
            raise MasteringError(f"no section {section!r} in the last full render; sections: "
                                 f"{', '.join(secs) or 'none (render the full song first)'}")
        a, b = secs[section]
        match_ = next(s for s in src.report.get('sections') if isinstance(s, dict) and s.get('name') == section)
        start_beat = (float(match_.get('startBar', 1.0)) - 1.0) * 4.0
        label += f": {section} ({_cmp.fmt_time(a)}-{_cmp.fmt_time(b)})"
    try:
        _cmp.run_analyze(eng, src.wav, outd / 'mix', tempo=tempo, start_beat=start_beat, from_sec=a, to_sec=b,
                         profile=prof, pngs=False, title=label)
    except _cmp.CompareError as e:
        raise MasteringError(str(e)) from None
    mix = _load_json(outd / 'mix' / 'report.json')
    if not isinstance(mix, dict) or 'measures' not in mix:
        raise MasteringError(f"the engine wrote no readable analysis into {outd / 'mix'}")
    mix['_path'] = str((outd / 'mix' / 'report.json').resolve())
    whole = mix
    if section:   # loudness / true peak / width of the whole song decide the limiter, not one section
        try:
            _cmp.run_analyze(eng, src.wav, outd / 'whole', tempo=tempo, profile=prof, pngs=False, title=label)
        except _cmp.CompareError as e:
            raise MasteringError(str(e)) from None
        whole = _load_json(outd / 'whole' / 'report.json') or mix
    g, meas = whole.get('global', {}), whole.get('measures', {})
    refinfo = whole.get('reference') or {}
    lufs = _cmp._num(meas, 'loudness', 'integratedLufs', default=_cmp._num(g, 'lufsIntegrated'))
    tp = _cmp._num(g, 'truePeakDbtp')
    if lufs is None or lufs <= -70:
        raise MasteringError(f"{src.wav} is silent (integrated loudness {lufs})")
    measured = {'lufs': _r(lufs), 'truePeakDbtp': _r(tp, 2), 'lra': _r(_cmp._num(g, 'loudnessRange')),
                'plr': _r(_cmp._num(g, 'plr')), 'crestDb': _r(_cmp._num(meas, 'transients', 'crestDb')),
                'widthAbove150HzPct': _r(_cmp._num(meas, 'stereo', 'above150Hz', 'widthPct')),
                'widthPct': _r(_cmp._num(g, 'widthPct')), 'correlation': _r(_cmp._num(g, 'stereoCorrelation'), 2),
                'lowCorrelation': _r(_cmp._num(meas, 'stereo', 'below120Hz', 'correlation'), 2),
                'seconds': _r(_cmp._num(meas, 'seconds'))}
    window = refinfo.get('lufsTarget') if isinstance(refinfo.get('lufsTarget'), list) else [-14.0, -8.0]
    plr_min = _cmp._num(refinfo, 'plrMinDb', default=6.0)
    log.append(f"mix {src.wav} ({label}): {lufs:.1f} LUFS-I, TP {tp:+.2f} dBTP, LRA {measured['lra']} LU, "
               f"width >150 Hz {measured['widthAbove150HzPct']} %; profile {prof!r} (loudness window "
               f"{window[0]:g}..{window[1]:g} LUFS, PLR >= {plr_min:g})")

    # --- the tonal target: a reference (loudness-matched compare) or the genre profile
    refd = None
    cmpd = None
    if ref is not None:
        ff = _ffmpeg(ffmpeg)
        if ff is None:
            raise MasteringError("a reference needs ffmpeg to decode it (PATH or C:/Program Files (x86)/ffmpeg/bin)")
        refp = Path(ref)
        rs = _cmp.parse_time(ref_start) if ref_start is not None else None
        re_ = _cmp.parse_time(ref_end) if ref_end is not None else None
        rdir = outd / 'ref'
        try:
            _cmp.decode_reference(ff, refp, rdir / 'ref.wav', rs, re_)
            _cmp.run_analyze(eng, rdir / 'ref.wav', rdir, profile=prof, pngs=False, title=refp.name)
        except _cmp.CompareError as e:
            raise MasteringError(str(e)) from None
        rrep = _load_json(rdir / 'report.json')
        if not isinstance(rrep, dict):
            raise MasteringError(f"no readable analysis of the reference in {rdir}")
        rrep['_path'] = str((rdir / 'report.json').resolve())
        for what, rp in (('the mix excerpt', mix), ('the reference excerpt', rrep)):
            sec = _cmp._num(rp, 'measures', 'seconds', default=0.0)
            if sec < _cmp.MIN_SECONDS:
                raise MasteringError(f"{what} is only {sec:.1f} s: use at least {_cmp.MIN_SECONDS:g} s")
        try:
            cmpd = _cmp.compare_reports(mix, rrep, song_report=src.report, render=src.render, mix_label=label,
                                        ref_label=refp.name)
        except _cmp.CompareError as e:
            raise MasteringError(str(e)) from None
        (outd / 'compare_before.json').write_text(json.dumps(cmpd, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        sp = cmpd['spectrum']
        hz, diff, valid = sp['hz'], [d if d is not None else 0.0 for d in sp['diffDb']], list(sp['valid'])
        cutoff = cmpd['reference'].get('bandLimitedAboveHz')
        dead = 1.0
        rlufs = _cmp._num(rrep, 'measures', 'loudness', 'integratedLufs')
        refd = {'file': str(refp.resolve()), 'label': refp.name, 'start': rs, 'end': re_, 'lufs': _r(rlufs),
                'truePeakDbtp': _r(_cmp._num(rrep, 'global', 'truePeakDbtp'), 2),
                'widthAbove150HzPct': _r(_cmp._num(rrep, 'measures', 'stereo', 'above150Hz', 'widthPct')),
                'crestDb': _r(_cmp._num(rrep, 'measures', 'transients', 'crestDb')),
                'globalCrestDb': _r(_cmp._num(rrep, 'global', 'crestDb')),
                'lra': _r(_cmp._num(rrep, 'measures', 'loudness', 'loudnessRange')),
                'bandLimitedAboveHz': cutoff, 'report': rrep['_path'], 'decoded': str((rdir / 'ref.wav').resolve())}
        log.append(f"reference {refp.name}" + (f" {_cmp.fmt_time(rs or 0)}-{_cmp.fmt_time(re_)}" if re_ is not None else '') +
                   f": {rlufs:.1f} LUFS-I, width >150 Hz {refd['widthAbove150HzPct']} %; tone compared loudness-matched, "
                   f"{_cmp.fmt_hz(FIT_LOW_HZ)}-{_cmp.fmt_hz(min(FIT_HIGH_HZ, cutoff or FIT_HIGH_HZ))}")
    else:
        to = (mix.get('global') or {}).get('thirdOctave') or {}
        hz = [float(h) for h in to.get('hz') or []]
        vs = to.get('vsRefDb') or []
        if not hz or len(vs) != len(hz):
            raise MasteringError("the mix analysis has no third-octave balance (global.thirdOctave): rebuild the engine")
        diff = [float(v) for v in vs]
        mdb = (mix['measures'].get('spectrum') or {}).get('db') or []
        valid = [(i >= len(mdb) or mdb[i] > -90) for i in range(len(hz))]
        dead = 1.5
        log.append(f"no reference: tone judged against the {prof!r} profile's reference spectrum (dead band {dead:g} dB: "
                   f"a genre average, not a target to hit exactly)")
    for i, f in enumerate(hz):
        if f > FIT_HIGH_HZ + 0.1 or f < FIT_LOW_HZ - 0.1:
            valid[i] = False
    wanted, centre = correction_curve(hz, diff, valid, dead_db=dead, strength=strength, max_db=max_db)
    mg, mref = mix.get('global') or {}, mix.get('reference') or {}
    limits = {b: dict(v) for b, v in (mref.get('bandLimitsDb') or {}).items() if isinstance(v, dict)}
    dull = mref.get('dullDb')
    if isinstance(dull, (int, float)):       # the report's 'dull' warning: the 6-20 kHz top under dullDb
        for b in ('brilliance', 'air'):
            lim = limits.setdefault(b, {})
            lim['low'] = max(lim['low'], dull) if isinstance(lim.get('low'), (int, float)) else dull
    wanted, guarded = profile_guard(hz, wanted, mg.get('bandsVsRefDb'), limits)
    if guarded:
        log.append("tone: kept inside the " + repr(prof) + " balance (a band may not cross its limit): " +
                   ', '.join(f"{b} {lo if lo is not None else '-inf'}..{hi if hi is not None else '+inf'} dB"
                             for b, (lo, hi) in guarded.items()))
    eq, achieved, rms = fit_eq(hz, wanted, max_db=max_db)
    # Always a gentle rumble filter on a master that has none of its own (inaudible, frees headroom).
    sub_pct = _cmp._num(g, 'subsonicPct', default=0.0) or 0.0
    dc = g.get('dcOffset') if isinstance(g.get('dcOffset'), list) else []
    if sub_pct >= 0.5 or any(abs(float(x)) >= 0.001 for x in dc if isinstance(x, (int, float))):
        eq['hp.freq'] = 20
        log.append(f"subsonic energy {sub_pct:.2f} % / DC {dc}: high-pass at 20 Hz")
    worst = max(((hz[i], wanted[i]) for i in range(len(hz)) if wanted[i] is not None), key=lambda t: abs(t[1]),
                default=(None, 0.0))
    log.append(f"tone: wanted correction up to {worst[1]:+.1f} dB" + (f" at {_cmp.fmt_hz(worst[0])}" if worst[0] else '') +
               f" (smoothed ~1 oct, dead band {dead:g} dB, strength {strength:g}, +-{max_db:g} dB) -> {describe_eq(eq)} "
               f"(fit rms {rms:.2f} dB)")
    curve = {'hz': hz, 'diffDb': [None if not v else round(d, 2) for d, v in zip(diff, valid)],
             'wantedDb': [None if v is None else round(v, 2) for v in wanted], 'eqDb': achieved, 'centreDb': centre,
             'note': 'diff = mix - target (reference, loudness-matched, or the profile curve); wanted = the eq that '
                     'moves the mix towards it (smoothed, dead band, strength, clamp); eq = what the fitted eq does'}

    # --- width
    wm = measured['widthAbove150HzPct']
    corr = measured['correlation']
    low_corr = measured['lowCorrelation']
    factor = 1.0
    if refd is not None:
        wr = refd['widthAbove150HzPct']
        if wm is not None and wr is not None and wm > 0.5 and wr >= 3.0 and abs(10 * math.log10(wr / wm)) >= 1.5:
            factor = math.sqrt(wr / wm)
            why = f"towards the reference's width above 150 Hz ({wm:.0f} % -> {wr:.0f} %)"
        else:
            why = 'the width matches the reference (within 1.5 dB) or the reference is mono'
    else:
        tw = ((src.report.get('space') or {}).get('targets') or {}).get('widthAbove150HzPct')
        if isinstance(tw, list) and len(tw) == 2 and wm is not None and wm > 0.5:
            if wm < tw[0]:
                factor = math.sqrt((tw[0] * 1.1) / wm)
                why = f"into the profile's width range above 150 Hz ({wm:.0f} % < {tw[0]:g} %)"
            elif wm > tw[1]:
                factor = math.sqrt((tw[1] * 0.95) / wm)
                why = f"into the profile's width range above 150 Hz ({wm:.0f} % > {tw[1]:g} %)"
            else:
                why = f"width above 150 Hz {wm:.0f} % is inside the profile's range {tw[0]:g}..{tw[1]:g} %"
        else:
            why = 'no width target (no reference, no profile width range in the report)'
    if factor > 1.0 and corr is not None and corr < 0.3:
        why += f"; not widened: the correlation is already {corr:.2f} (mono compatibility)"
        factor = 1.0
    factor = round(max(lo_w, min(hi_w, factor)), 2)
    width = None
    monobass = 120 if (low_corr is not None and low_corr < 0.9) else None
    if factor != 1.0 or monobass:
        width = {'width': factor}
        if monobass:
            width['monobass'] = monobass
    log.append(f"width: x{factor:g} ({why})" + (f"; lows made mono below 120 Hz (correlation < 120 Hz {low_corr:.2f})"
                                                 if monobass else ''))

    # --- loudness target
    tp_target = plat.tp
    ceiling = round(tp_target - 0.2, 2)
    plr_cap = tp_target - plr_min            # louder than this squashes below the profile's PLR floor
    lo_t, hi_t = float(window[0]), float(window[1])
    if isinstance(plat.lufs, (int, float)):
        target = float(plat.lufs)
        why = f"platform {plat.name}: {target:g} LUFS"
    elif plat.lufs == 'profile-top':
        target = hi_t - 0.5
        why = f"platform {plat.name}: the top of the {prof!r} window ({lo_t:g}..{hi_t:g}) - 0.5"
        if refd and refd['lufs'] is not None and refd['lufs'] < target:
            target = max(lo_t, refd['lufs'])
            why += f", not louder than the reference ({refd['lufs']:.1f})"
    elif plat.name == 'dynamic':
        mid = 0.5 * (lo_t + hi_t)
        target = min(mid, refd['lufs']) if refd and refd['lufs'] is not None else mid
        ilo = lo_t + 0.5 if hi_t - lo_t > 1.0 else lo_t
        target = max(target, ilo)       # never under the window (0.5 LU inside) for being dynamic
        why = f"platform dynamic: {'the reference / ' if refd else ''}the middle of the {prof!r} window ({mid:.1f})"
    else:
        # Clamped into the window 0.5 LU inside its edges (a master right at the edge reads as outside after the
        # calibration's +-0.2 LU).
        ilo, ihi = (lo_t + 0.5, hi_t - 0.5) if hi_t - lo_t > 1.0 else (lo_t, hi_t)
        if refd and refd['lufs'] is not None:
            target = min(max(refd['lufs'], ilo), ihi)
            why = f"the reference's {refd['lufs']:.1f} LUFS clamped into the {prof!r} window ({lo_t:g}..{hi_t:g}, 0.5 LU inside)"
        elif ilo <= lufs <= ihi:
            target = lufs
            why = f"inside the {prof!r} window ({lo_t:g}..{hi_t:g}): keep the level"
        else:
            target = min(max(lufs, ilo), ihi)
            why = f"the nearest edge of the {prof!r} window ({lo_t:g}..{hi_t:g}), 0.5 LU inside"
    if target > hi_t and plat.name != 'streaming':
        target, why = hi_t, why + f"; capped at the window's top {hi_t:g}"
    if target > plr_cap:
        target, why = plr_cap, why + f"; capped at {plr_cap:.1f} (PLR floor {plr_min:g} dB under {tp_target:g} dBTP)"
    target = round(target, 1)
    log.append(f"loudness: {lufs:.1f} -> {target:.1f} LUFS-I ({why}); true peak <= {tp_target:g} dBTP (limiter ceiling "
               f"{ceiling:g}, release {plat.release:g} ms)")

    # --- limiter + estimates
    spec = mix['measures'].get('spectrum') or {}
    eq_lu = eq_loudness_change([float(h) for h in spec.get('hz') or []], spec.get('db') or [], eq)
    w_lu = width_loudness_change(measured['widthPct'], factor)
    need = target - lufs - eq_lu - w_lu
    headroom = ceiling - (tp if tp is not None else ceiling)
    max_drive = round(max(0.0, headroom) + plat.max_limit_db, 1) if plat.max_limit_db is not None else 24.0
    gain_est = round(min(need, max_drive), 1)
    limiter = {'ceiling': ceiling, 'gain': max(-12.0, min(24.0, gain_est)), 'release': plat.release}
    lim_now = _cmp._limiter_gain(src.render)
    estimate = {'eqLoudnessDb': round(eq_lu, 2), 'widthLoudnessDb': round(w_lu, 2), 'postPassLimiterGain': gain_est,
                'maxDriveDb': max_drive, 'capped': need > max_drive + 0.05,
                'songLimiterGainChange': gain_est if abs(gain_est) >= 0.1 else 0.0,
                'songLimiterGainNow': lim_now[1] if lim_now else None,
                'note': 'post-pass gain is calibrated by render() (never past maxDriveDb); in the song chain the gain '
                        'change is an estimate (a limiter already working turns 1 dB of drive into less than 1 LU): '
                        're-build and check'}
    log.append(f"limiter: drive {gain_est:+.1f} dB estimated (eq {eq_lu:+.2f} LU, width {w_lu:+.2f} LU; at most "
               f"{max_drive:g} dB = headroom {max(0.0, headroom):.1f} + {plat.max_limit_db:g} dB of peak limiting)" +
               (f" - the target needs ~{need:.1f} dB: it will fall short rather than squash the mix"
                if need > max_drive + 0.05 else '') +
               (f"; song limiter gain {lim_now[1]:g} -> {lim_now[1] + gain_est:.1f} dB" if lim_now else ''))
    # Density floor: the master may be as loud as the reference, not (much) denser - loudness falls short instead.
    crest_mix = _cmp._num(g, 'crestDb')
    floor = None
    if crest_mix is not None and plat.density_db is not None:
        if plat.name == 'dynamic':
            floor = crest_mix - plat.density_db
            fwhy = f"the mix's own crest {crest_mix:.1f} dB - {plat.density_db:g}"
        elif refd and refd.get('globalCrestDb') is not None:
            floor = min(refd['globalCrestDb'] - plat.density_db, crest_mix - 0.5)
            fwhy = (f"the reference's crest {refd['globalCrestDb']:.1f} dB - {plat.density_db:g}"
                    + (f" (the mix is already denser: its {crest_mix:.1f} - 0.5)" if floor == crest_mix - 0.5 else ''))
    if floor is not None:
        floor = round(floor, 1)
        log.append(f"density: crest factor >= {floor:g} dB ({fwhy}; now {crest_mix:.1f}): the post-pass stops driving the "
                   f"limiter there")
    estimate['headroomDb'] = round(max(0.0, headroom), 2)
    estimate['crestNowDb'] = crest_mix
    if cmpd is not None:
        crest = next((m for m in cmpd['metrics'] if m['key'] == 'crest'), None)
        if crest and crest['diff'] is not None and crest['diff'] >= 2.0:
            log.append(f"note: the reference is denser (crest {crest['ref']:.1f} vs {crest['mix']:.1f} dB): glue it in "
                       f"the mix (bus compression) - the master only limits")
    plan = MasterPlan(
        source=str(src.wav.resolve()), song_dir=str(src.song_dir.resolve()) if src.song_dir else None,
        out=str(outd.resolve()), profile=prof, platform=plat.name, reference=refd, measured=measured,
        targets={'lufs': target, 'window': [lo_t, hi_t], 'truePeakDbtp': tp_target, 'width': factor,
                 'plrMinDb': plr_min, 'section': section, 'platformWindow': list(plat.window) if plat.window else None,
                 'crestFloorDb': floor},
        eq=eq, width=width, limiter=limiter, estimate=estimate, curve=curve, log=log,
        analysis={'mix': mix['_path'], 'compare': str((outd / 'compare_before.json').resolve()) if cmpd else None,
                  'tempo': tempo, 'sections': _sections(src)})
    if save:
        plan.save()
    return plan


# ------------------------------------------------------------------------------------------ apply to a song

_FX_IDX = re.compile(r'^fx\.(\d+)\.')


def _shift_targets(node, at: int) -> None:
    """Automation / modulator targets 'fx.<i>.<param>' with i >= at move up by one (an effect was inserted at `at`)."""
    def fix(t):
        m = _FX_IDX.match(t)
        if m and int(m.group(1)) >= at:
            return f"fx.{int(m.group(1)) + 1}." + t[m.end():]
        return t
    node._auto = [(fix(t), pts) for t, pts in node._auto]
    node._mods = [(fix(t), m, w, o) for t, m, w, o in node._mods]


def apply(song, *, eq: dict | None = None, width: float | None = None, monobass: float | None = None,
          limiter: dict | None = None, loudness_change: float | None = None) -> list[str]:
    """Master-chain settings into song.master, keeping the song's own chain:
    eq       inserted FIRST as an eq named 'master_eq' (replaced if there is one): the correction was measured on the
             finished mix, so it goes before the song's glue / tape / limiter
    width    the master's width effect's width x this factor (inserted before the limiter if there is none)
    monobass that width effect's monobass (Hz)
    limiter  params set on the master limiter (appended last if there is none): ceiling, release ...
    loudness_change  dB added to the limiter's gain (plan.estimate: an estimate - re-build and check)
    Automation targets by fx index are shifted when an effect is inserted. Returns log lines."""
    from .patches import FX
    m = song.master
    log = []
    if eq:
        i = next((k for k, f in enumerate(m.fx) if f.type == 'eq' and f.name == 'master_eq'), None)
        if i is None:
            _shift_targets(m, 0)
            m.fx.insert(0, FX('eq', dict(eq), name='master_eq'))
            log.append(f"master: + eq 'master_eq' first ({describe_eq(eq)})")
        else:
            m.fx[i] = FX('eq', dict(eq), name='master_eq')
            log.append(f"master: eq 'master_eq' replaced ({describe_eq(eq)})")
    lim_i = next((k for k in range(len(m.fx) - 1, -1, -1) if m.fx[k].type == 'limiter'), None)
    if (width is not None and width != 1.0) or monobass:
        wi = next((k for k, f in enumerate(m.fx) if f.type == 'width'), None)
        if wi is None:
            at = lim_i if lim_i is not None else len(m.fx)
            _shift_targets(m, at)
            params = {'width': round(width if width is not None else 1.0, 3)}
            if monobass:
                params['monobass'] = monobass
            m.fx.insert(at, FX('width', params))
            if lim_i is not None:
                lim_i += 1
            log.append(f"master: + width {params} before the limiter")
        else:
            old = m.fx[wi].params.get('width', 1.0)
            new = dict(m.fx[wi].params)
            if width is not None:
                new['width'] = round(min(2.0, old * width), 3)
            if monobass and not new.get('monobass'):
                new['monobass'] = monobass
            m.fx[wi] = m.fx[wi].but(**new)
            log.append(f"master: width {old:g} -> {new.get('width', old):g}" +
                       (f", monobass {new['monobass']:g} Hz" if new.get('monobass') else ''))
    lim = dict(limiter or {})          # an explicit 'gain' is absolute; loudness_change is added on top
    if lim_i is None:
        lim.setdefault('ceiling', -1.2)
        lim['gain'] = round(max(-12.0, min(24.0, lim.get('gain', 0.0) + (loudness_change or 0.0))), 1)
        m.fx.append(FX('limiter', lim))
        log.append(f"master: + limiter {lim}")
    else:
        old = m.fx[lim_i].params.get('gain', 0.0)
        if loudness_change or 'gain' in lim:
            lim['gain'] = round(max(-12.0, min(24.0, lim.get('gain', old) + (loudness_change or 0.0))), 1)
        if lim:
            m.fx[lim_i] = m.fx[lim_i].but(**lim)
        log.append(f"master: limiter {', '.join(f'{k} {v:g}' for k, v in lim.items()) or 'unchanged'}"
                   + (f" (gain was {old:g})" if 'gain' in lim else ''))
    return log


# ------------------------------------------------------------------------------------------ post-pass render

def _postpass_render_json(wav: Path, info: dict, chain: list) -> dict:
    seconds = info['frames'] / float(info['rate'])
    return {
        'format': 'agentsound.render', 'version': 1, 'title': 'mastering post-pass', 'sampleRate': info['rate'],
        'tempo': 60.0, 'lengthBeats': round(seconds, 6), 'tailSeconds': 0.0, 'seed': 1,
        'tracks': [{
            'id': 'mix',
            'instrument': {'type': 'sampler', 'params': {
                'samples': {'file': str(Path(wav).resolve()).replace('\\', '/'), 'root': 60, 'loop': 'oneshot'},
                'level': 0.0, 'velsens': 0.0, 'attack': 0.0, 'oneshot': 'on', 'polyphony': 1}},
            'notes': [[0.0, round(seconds, 6), 60, 127]],
        }],
        'buses': [],
        'master': {'fx': [f.to_dict() if hasattr(f, 'to_dict') else f for f in chain], 'gainDb': 0.0, 'automation': []},
        'export': {'stems': False, 'bitDepth': 32},
    }


def _render_pass(eng: Path, wav: Path, info: dict, chain: list, out_dir: Path) -> Path:
    rj = out_dir / 'master.render.json'
    rj.write_text(json.dumps(_postpass_render_json(wav, info, chain), indent=1) + '\n', encoding='utf-8')
    cmd = [str(eng), 'render', str(rj), '--out', str(out_dir), '--no-analysis', '--no-png', '--quiet']
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise MasteringError(f"the engine failed on the post-pass: {(proc.stderr or proc.stdout).strip()[:400]}")
    return out_dir / 'mix.wav'


def _analyze(eng: Path, wav: Path, dest: Path, *, profile: str, tempo=None, sections=(), window=None, pngs=False,
             measures=True, title=None) -> dict:
    """engine analyze (report.json into dest), optionally judged against a loudness window of its own."""
    cmd = [str(eng), 'analyze', str(wav), '--out', str(dest), '--profile', profile]
    if window:
        cmd += ['--loudness', f"{window[0]:g},{window[1]:g}"]
    if tempo:
        cmd += ['--tempo', f"{tempo:g}"]
    for n, a, b in sections:
        cmd += ['--section', str(n), f"{a:.4f}", f"{b:.4f}"]
    if title:
        cmd += ['--title', title]
    if not pngs:
        cmd.append('--no-png')
    if not measures:
        cmd.append('--no-measures')
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise MasteringError(f"engine analyze failed for {Path(wav).name}: {(proc.stderr or proc.stdout).strip()[:300]}")
    rep = _load_json(Path(dest) / 'report.json')
    if not isinstance(rep, dict):
        raise MasteringError(f"engine analyze wrote no readable report into {dest}")
    return rep


def analyze_wav(wav, *, profile: str = 'default', out=None, engine=None) -> Path:
    """Analyse any WAV (engine analyze, no images) into <wav stem>_analysis/ (or out); returns the report.json path."""
    wav = Path(wav)
    if not wav.is_file():
        raise MasteringError(f"no WAV at {wav}")
    dest = Path(out) if out else wav.parent / (wav.stem + '_analysis')
    _analyze(_engine(engine), wav, dest, profile=profile)
    return dest / 'report.json'


def _quick_loudness(eng: Path, wav: Path, out_dir: Path, profile: str) -> tuple[float, float, float | None]:
    g = _analyze(eng, wav, out_dir, profile=profile, measures=False).get('global') or {}
    crest = g.get('crestDb')
    return (float(g.get('lufsIntegrated', -120.0)), float(g.get('truePeakDbtp', 0.0)),
            float(crest) if isinstance(crest, (int, float)) else None)


def _analyze_full(eng, wav, dest, plan, title, pngs, window):
    return _analyze(eng, wav, dest, profile=plan.profile, tempo=plan.analysis.get('tempo'),
                    sections=[tuple(s) for s in plan.analysis.get('sections') or []], window=window, pngs=pngs,
                    title=title)


def _warn_keys(rep: dict) -> list[str]:
    return sorted({f"{w.get('severity')}:{w.get('code')}" for w in rep.get('warnings') or [] if isinstance(w, dict)})


def _metrics(rep: dict) -> dict:
    g, m = rep.get('global') or {}, rep.get('measures') or {}
    return {'lufs': _r(g.get('lufsIntegrated')), 'truePeakDbtp': _r(g.get('truePeakDbtp'), 2),
            'lra': _r(g.get('loudnessRange')), 'plr': _r(g.get('plr')),
            'widthAbove150HzPct': _r(_cmp._num(m, 'stereo', 'above150Hz', 'widthPct')),
            'correlation': _r(g.get('stereoCorrelation'), 2), 'crestDb': _r(_cmp._num(m, 'transients', 'crestDb')),
            'bandsVsRefDb': g.get('bandsVsRefDb')}


def _scaled(plan: MasterPlan, k: float) -> tuple[dict, dict | None]:
    """The plan's eq gains and width move scaled by k (a back-off)."""
    eq = {n: (round(v * k, 1) if n.endswith('.gain') else v) for n, v in plan.eq.items()}
    eq = {n: v for n, v in eq.items() if not (n.endswith('.gain') and abs(v) < 0.3)}   # too small to matter
    eq = {n: v for n, v in eq.items() if n.endswith('.gain') or n.startswith('hp.') or f"{n.split('.')[0]}.gain" in eq}
    width = dict(plan.width) if plan.width else None
    if width and 'width' in width:
        width['width'] = round(1.0 + (width['width'] - 1.0) * k, 3)
        if width['width'] == 1.0 and not width.get('monobass'):
            width = None
    return eq, width


_LEVEL_CODES = ('loudness', 'squashed', 'lra', 'level_jump')


def render(plan: MasterPlan, *, engine=None, ffmpeg=None, calibrate: bool = True, mp3: bool = True,
           images: bool = True, max_iter: int = 4, backoff: bool = True) -> dict:
    """The post-pass: mix.wav through the plan's chain (engine render: the mix as one sampler note, the chain as
    the master) into <out>/mastered.wav (32-bit float), the limiter gain calibrated to the loudness target (<= 0.2
    LU, at most max_iter renders, never past the plan's maxDriveDb), then the before / after analysis (same tempo,
    sections, profile; the platform's loudness window) with their warnings. Do no harm: when the master raises a
    warning the mix did not have, the eq and width moves are halved, then dropped (backoff), and the plan is updated
    to what was applied (master.json, plan.snippet()). Then the before / after comparison with the reference and
    mastered.mp3 (tags and cover copied from mix.mp3). Writes <out>/master_result.json; returns it.
    The sampler that plays mix.wav band-limits it above ~19 kHz (its interpolation filter: transparent to -80 dB
    below 19 kHz at 48 kHz) - inaudible, but not bit-transparent."""
    eng = _engine(engine)
    outd = Path(plan.out)
    wav = Path(plan.source)
    info = wav_info(wav)
    if info['rate'] not in (44100, 48000, 96000):
        raise MasteringError(f"{wav}: sample rate {info['rate']} (the engine renders 44100 / 48000 / 96000)")
    work = outd / 'pass'
    work.mkdir(parents=True, exist_ok=True)
    max_drive = min(24.0, float(plan.estimate.get('maxDriveDb', 24.0)))
    target = plan.targets['lufs']
    window = plan.targets.get('platformWindow')
    before = _analyze_full(eng, wav, outd / 'before', plan, 'before mastering', False, window)
    bw = _warn_keys(before)
    gain = plan.limiter['gain']
    floor = plan.targets.get('crestFloorDb')
    crest0 = plan.estimate.get('crestNowDb')
    headroom = float(plan.estimate.get('headroomDb', 0.0) or 0.0)
    attempts = []
    scales = (1.0, 0.5, 0.0) if backoff and (plan.eq or plan.width) else (1.0,)
    for k in scales:
        eq, width = _scaled(plan, k)
        tries = []
        cap = max_drive
        for _ in range((max_iter + 1) if calibrate else 1):
            lim = dict(plan.limiter, gain=round(max(-12.0, min(cap, gain)), 2))
            out_wav = _render_pass(eng, wav, info, _chain(eq, width, lim), work)
            lu, tp, crest = _quick_loudness(eng, out_wav, work / 'measure', plan.profile)
            tries.append({'gain': lim['gain'], 'lufs': round(lu, 2), 'truePeakDbtp': round(tp, 2),
                          'crestDb': None if crest is None else round(crest, 2)})
            if (calibrate and floor is not None and crest is not None and crest < floor - 0.1 and
                    lim['gain'] > headroom + 0.05 and len(tries) <= max_iter):
                # Too dense: the drive that keeps the crest at the floor (crest falls ~linearly with the drive past
                # the headroom) becomes the cap; loudness falls short instead.
                used_drive = lim['gain'] - headroom
                slope = max(0.3, ((crest0 if crest0 is not None else crest + used_drive) - crest) / max(0.5, used_drive))
                cap = round(max(headroom, lim['gain'] - (floor - crest) / slope), 2)
                tries[-1]['tooDense'] = True
                gain = cap
                continue
            err = target - lu
            if abs(err) <= 0.2 or not calibrate or (err > 0 and lim['gain'] >= cap - 1e-6) or len(tries) > max_iter:
                break
            if len(tries) >= 2 and abs(tries[-1]['gain'] - tries[-2]['gain']) > 1e-6:
                slope = (tries[-1]['lufs'] - tries[-2]['lufs']) / (tries[-1]['gain'] - tries[-2]['gain'])
                slope = min(1.0, max(0.25, slope))
            else:
                slope = 1.0 if err < 0 else 0.8     # a limiter already working gives less than 1 LU per dB of drive
            gain += err / slope
        gain = tries[-1]['gain']
        after = _analyze_full(eng, out_wav, work / 'after', plan, 'after mastering', False, window)
        new = [w for w in _warn_keys(after) if w not in bw]
        attempts.append({'scale': k, 'eq': eq, 'width': width, 'calibration': tries, 'new': new, 'cap': cap})
        # Only what the eq / width can cause is a reason to back them off (loudness is the limiter's business).
        if not [w for w in new if not w.split(':', 1)[-1].startswith(_LEVEL_CODES)]:
            break
    chosen = attempts[-1]
    if len(attempts) > 1 and chosen['new']:      # nothing was clean: keep the attempt with the fewest new warnings
        chosen = min(attempts, key=lambda x: (sum(not w.split(':', 1)[-1].startswith(_LEVEL_CODES) for w in x['new']),
                                              len(x['new']), -x['scale']))
        if chosen is not attempts[-1]:
            lim = dict(plan.limiter, gain=chosen['calibration'][-1]['gain'])
            _render_pass(eng, wav, info, _chain(chosen['eq'], chosen['width'], lim), work)
    tries = chosen['calibration']
    used = tries[-1]
    final = outd / 'mastered.wav'
    shutil.copyfile(work / 'mix.wav', final)
    shutil.copyfile(work / 'master.render.json', outd / 'master.render.json')
    after = _analyze_full(eng, final, outd / 'after', plan, 'after mastering', images, window)
    aw = _warn_keys(after)
    if chosen['scale'] != 1.0:
        plan.log.append(f"render: the master raised {attempts[0]['new']} the mix did not have: eq / width moves backed off "
                        f"to x{chosen['scale']:g} ({describe_eq(chosen['eq'])})")
    plan.eq, plan.width = chosen['eq'], chosen['width']
    plan.limiter = dict(plan.limiter, gain=used['gain'])
    plan.estimate['postPassLimiterGain'] = used['gain']
    # The calibrated post-pass drive is the better estimate for the song's own limiter too (snippet / apply).
    plan.estimate['songLimiterGainChange'] = used['gain'] if abs(used['gain']) >= 0.1 else 0.0
    plan.save()
    res = {'format': 'agentsound.master.result', 'version': 1, 'mastered': str(final.resolve()),
           'limiterGain': used['gain'], 'calibration': tries, 'target': plan.targets,
           'reachedTarget': abs(target - used['lufs']) <= 0.25,
           'cappedByMaxDrive': target - used['lufs'] > 0.25 and used['gain'] >= max_drive - 1e-6,
           'cappedByDensity': target - used['lufs'] > 0.25 and chosen['cap'] < max_drive - 1e-6
                              and used['gain'] >= chosen['cap'] - 1e-6,
           'crestFloorDb': floor,
           'appliedScale': chosen['scale'], 'eq': chosen['eq'], 'width': chosen['width'],
           'backoff': [{'scale': x['scale'], 'new': x['new']} for x in attempts],
           'before': _metrics(before), 'after': _metrics(after),
           'warnings': {'before': bw, 'after': aw, 'new': [w for w in aw if w not in bw],
                        'resolved': [w for w in bw if w not in aw]},
           'afterReport': str((outd / 'after' / 'report.json').resolve()),
           'afterWarnings': [w.get('message') for w in after.get('warnings') or [] if isinstance(w, dict)]}
    if plan.reference:
        rrep = _load_json(Path(plan.reference['report']))
        mix_a = _load_json(Path(plan.analysis['mix']))
        if isinstance(rrep, dict) and isinstance(mix_a, dict):
            sec = plan.targets.get('section')
            a = b = None
            if sec:
                a, b = next(((x, y) for n, x, y in plan.analysis.get('sections') or [] if n == sec), (None, None))
            _cmp.run_analyze(eng, final, outd / 'after_cmp', tempo=plan.analysis.get('tempo'), from_sec=a, to_sec=b,
                             profile=plan.profile, pngs=False, title='mastered')
            aft = _load_json(outd / 'after_cmp' / 'report.json')
            rrep['_path'] = plan.reference['report']
            c0 = _cmp.compare_reports(mix_a, rrep, mix_label='before', ref_label=plan.reference['label'])
            c1 = _cmp.compare_reports(aft, rrep, mix_label='after', ref_label=plan.reference['label'])
            (outd / 'compare_after.json').write_text(json.dumps(c1, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
            res['compare'] = {'before': _compare_numbers(c0), 'after': _compare_numbers(c1)}
            try:
                _cmp.render_png(eng, outd / 'compare_after.json', outd / 'compare_after.png')
                res['compare']['png'] = str((outd / 'compare_after.png').resolve())
            except _cmp.CompareError:
                pass
    if mp3:
        res['mp3'] = _encode_mp3(_ffmpeg(ffmpeg), final, outd / 'mastered.mp3',
                                 Path(plan.song_dir) / 'out' / 'mix.mp3' if plan.song_dir else None)
    (outd / 'master_result.json').write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return res


def _compare_numbers(c: dict) -> dict:
    bands = {b['name']: b['diffDb'] for b in c.get('bands') or []}
    judged = [d for d, v, f in zip(c['spectrum']['diffDb'], c['spectrum']['valid'], c['spectrum']['hz'])
              if v and d is not None and FIT_LOW_HZ <= f <= FIT_HIGH_HZ]
    rms = math.sqrt(sum(d * d for d in judged) / len(judged)) if judged else None
    met = {m['key']: m['diff'] for m in c.get('metrics') or []}
    return {'bandsDiffDb': bands, 'spectrumRmsDb': _r(rms, 2), 'lufsDiff': met.get('lufs'), 'widthDiff': met.get('width'),
            'crestDiff': met.get('crest'), 'tiltDiff': met.get('tilt'),
            'regions': [f"{r['fromHz']:.0f}-{r['toHz']:.0f} Hz {r['avgDb']:+.1f} dB" for r in c['spectrum']['regions']]}


def _encode_mp3(ff: str | None, wav: Path, mp3: Path, tagged: Path | None) -> str:
    if ff is None:
        return 'mp3 skipped: ffmpeg not found'
    cmd = [ff, '-y', '-hide_banner', '-loglevel', 'error', '-i', str(wav)]
    if tagged is not None and tagged.is_file():
        cmd += ['-i', str(tagged), '-map', '0:a', '-map', '1:v?', '-map_metadata', '1', '-c:v', 'copy',
                '-id3v2_version', '3']
    cmd += ['-codec:a', 'libmp3lame', '-b:a', '320k', str(mp3)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        return f"mp3 failed: {(proc.stderr or '').strip()[:300]}"
    return str(mp3.resolve())


# ------------------------------------------------------------------------------------------ check

def _finding(code, severity, message, fix=None) -> dict:
    d = {'code': code, 'severity': severity, 'message': message}
    if fix:
        d['fix'] = fix
    return d


def check(report, *, platform=None, profile_window=None, compare=None, render: dict | None = None) -> list[dict]:
    """Mastering findings of a render / analysis report (dict, report.json path, or a song folder: its out/report.json
    and render JSON): true peak, clipping, DC, loudness vs the profile window and the platform (with the -14 / -16
    LUFS normalisation notes), PLR, LRA vs the genre's range, tonal balance vs the profile (and vs a reference when
    `compare` - a compare.json dict / path - is given), low-end mono, mono compatibility, width, master limiter.
    Each finding: {code, severity: warn|info|ok, message, fix?}; warn first."""
    plat = get_platform(platform)
    if isinstance(report, (str, Path)):
        p = Path(report)
        if p.is_dir():
            if render is None:
                render = _load_json(p / 'out' / 'song.render.json') or _load_json(p / 'song.render.json')
            p = p / 'out' / 'report.json' if (p / 'out' / 'report.json').is_file() else p / 'report.json'
        rep = _load_json(p)
        if not isinstance(rep, dict):
            raise MasteringError(f"no readable report at {p}")
    elif isinstance(report, dict):
        rep = report
    else:
        raise MasteringError(f"check() needs a report dict, a report.json path or a song folder, got {report!r}")
    if isinstance(compare, (str, Path)):
        compare = _load_json(Path(compare))
    g = rep.get('global') or {}
    refinfo = rep.get('reference') or {}
    meas = rep.get('measures') or {}
    prof = refinfo.get('profile', 'default')
    out: list[dict] = []
    lufs = g.get('lufsIntegrated')
    tp = g.get('truePeakDbtp')
    tp_max = plat.tp

    # true peak / clipping / DC
    if isinstance(tp, (int, float)):
        if tp > tp_max + 0.05:
            out.append(_finding('true_peak', 'warn',
                                f"true peak {tp:+.2f} dBTP is over {tp_max:g} dBTP: mp3/AAC/Opus encoding adds inter-sample "
                                f"overs (up to ~1 dB) and players clip them",
                                {'target': 'master limiter', 'params': {'ceiling': round(tp_max - 0.2, 1)}}))
        else:
            out.append(_finding('true_peak', 'ok', f"true peak {tp:+.2f} dBTP (<= {tp_max:g})"))
    clipped = g.get('clippedSamples') or 0
    if clipped:
        out.append(_finding('clipping', 'warn', f"{clipped} clipped samples: something runs into 0 dBFS after or without "
                                                 f"the limiter", {'target': 'master', 'fx': 'limiter last, ceiling -1.2'}))
    dc = [abs(float(x)) for x in (g.get('dcOffset') or []) if isinstance(x, (int, float))]
    if dc and max(dc) >= 0.001:
        out.append(_finding('dc_offset', 'warn', f"DC offset {max(dc):.4f} (>= -60 dBFS) wastes headroom and thumps at cuts",
                            {'type': 'eq', 'params': {'hp.freq': 20}}))
    sub = g.get('subsonicPct')
    if isinstance(sub, (int, float)) and sub >= 1.0:
        out.append(_finding('subsonic', 'info', f"{sub:.1f} % of the energy below 20 Hz: inaudible rumble eating headroom",
                            {'type': 'eq', 'params': {'hp.freq': 20}}))

    # loudness vs the window and the platforms
    win = list(profile_window) if profile_window else (refinfo.get('lufsTarget') if isinstance(refinfo.get('lufsTarget'), list)
                                                        else None)
    if plat.window:
        win = list(plat.window)
    if isinstance(lufs, (int, float)):
        if isinstance(plat.lufs, (int, float)) and abs(lufs - plat.lufs) > 1.0:
            out.append(_finding('loudness_platform', 'warn',
                                f"{lufs:.1f} LUFS-I vs the {plat.name} target {plat.lufs:g} LUFS ({lufs - plat.lufs:+.1f} LU)",
                                {'target': 'master limiter', 'gainDbChange': round(plat.lufs - lufs, 1)}))
        elif win and not win[0] - 0.05 <= lufs <= win[1] + 0.05:
            d = win[0] - lufs if lufs < win[0] else win[1] - lufs
            out.append(_finding('loudness_window', 'warn',
                                f"{lufs:.1f} LUFS-I is outside the {'platform' if plat.window else prof} window "
                                f"{win[0]:g}..{win[1]:g} LUFS ({'quieter' if d > 0 else 'louder'} by {abs(d):.1f} LU)",
                                {'target': 'master limiter', 'gainDbChange': round(d + (0.5 if d > 0 else -0.5), 1)}))
        else:
            out.append(_finding('loudness', 'ok', f"{lufs:.1f} LUFS-I" + (f" inside {win[0]:g}..{win[1]:g}" if win else '')))
        notes = []
        for who, level in NORMALISATION:
            d = level - lufs
            notes.append(f"{who} ({level:g}): {'turned down' if d < 0 else 'raised (if the true peak allows)' if d > 0 else 'unchanged'}"
                         + (f" {abs(d):.1f} dB" if abs(d) >= 0.05 else ''))
        if lufs > -13.5:
            tail = ('. Louder than -14 buys nothing on streaming: the level is taken back, the lost dynamics are not '
                    '(a loud genre master is still fine for downloads, DJs and clubs)')
        elif lufs < -14.5:
            tail = '. Quieter than -14: Spotify raises it only up to -1 dBTP, Apple Music and YouTube do not raise at all'
        else:
            tail = '. At the streaming reference level: played as it is'
        out.append(_finding('normalisation', 'info', "loudness normalisation: " + '; '.join(notes) + tail))

    # PLR / LRA
    plr = g.get('plr')
    plr_min = refinfo.get('plrMinDb')
    if isinstance(plr, (int, float)) and isinstance(plr_min, (int, float)) and plr < plr_min:
        out.append(_finding('squashed', 'warn', f"PLR {plr:.1f} dB < {plr_min:g} ({prof}): the limiter squashes the peaks",
                            {'target': 'master limiter', 'gainDbChange': round(plr - plr_min, 1)}))
    lra = g.get('loudnessRange')
    rng = refinfo.get('lraRangeLu')
    if isinstance(lra, (int, float)) and isinstance(rng, list) and len(rng) == 2:
        if lra < rng[0]:
            out.append(_finding('lra_small', 'warn' if plat.name == 'dynamic' else 'info',
                                f"loudness range {lra:.1f} LU < {rng[0]:g} ({prof}): the song barely breathes - quieter "
                                f"verses / breakdowns in the arrangement, less bus compression, less limiter drive",
                                {'target': 'master limiter', 'gainDbChange': -2.0}))
        elif lra > rng[1]:
            out.append(_finding('lra_large', 'info',
                                f"loudness range {lra:.1f} LU > {rng[1]:g} ({prof}): quiet passages drop out in a car or on "
                                f"earbuds - lift them (arrangement, gainDb automation) or glue the music bus "
                                f"(compressor 2:1, slow attack)"))
        else:
            out.append(_finding('lra', 'ok', f"loudness range {lra:.1f} LU inside {rng[0]:g}..{rng[1]:g}"))

    # tone vs the profile (broad moves only: what a master can fix)
    to = g.get('thirdOctave') or {}
    if to.get('hz') and to.get('vsRefDb') and len(to['hz']) == len(to['vsRefDb']):
        hz = [float(h) for h in to['hz']]
        valid = [FIT_LOW_HZ - 0.1 <= f <= FIT_HIGH_HZ + 0.1 for f in hz]
        wanted, _ = correction_curve(hz, [float(v) for v in to['vsRefDb']], valid, dead_db=1.5, strength=0.75, max_db=3.0)
        eq, _, _ = fit_eq(hz, wanted)
        big = max((abs(v) for v in wanted if v is not None), default=0.0)
        if eq and big >= 1.0:
            out.append(_finding('tone_profile', 'info',
                                f"tonal balance vs the {prof} profile: a master eq of {describe_eq(eq)} would move it "
                                f"towards the genre average (report bandsVsRefDb {g.get('bandsVsRefDb')}); a bigger "
                                f"imbalance belongs in the mix (the parts that carry the band)",
                                {'type': 'eq', 'params': eq}))
    lims = refinfo.get('bandLimitsDb') or {}
    for band, v in (g.get('bandsVsRefDb') or {}).items():
        lim = lims.get(band) or {}
        if isinstance(v, (int, float)) and ((lim.get('high') is not None and v > lim['high']) or
                                            (lim.get('low') is not None and v < lim['low'])):
            out.append(_finding('tone_band', 'warn',
                                f"{band} {v:+.1f} dB vs the {prof} balance (limits {lim.get('low', '-')}/{lim.get('high', '-')}): "
                                f"too big for a master eq (+-3 dB) alone - fix it in the mix"))
    if isinstance(compare, dict) and compare.get('spectrum'):
        sp = compare['spectrum']
        hz = sp['hz']
        valid = [bool(v) and FIT_LOW_HZ - 0.1 <= f <= FIT_HIGH_HZ + 0.1 for v, f in zip(sp['valid'], hz)]
        diff = [d if d is not None else 0.0 for d in sp['diffDb']]
        wanted, _ = correction_curve(hz, diff, valid, dead_db=1.0, strength=0.75, max_db=3.0)
        eq, _, _ = fit_eq(hz, wanted)
        if eq:
            out.append(_finding('tone_reference', 'info',
                                f"vs the reference ({(compare.get('reference') or {}).get('label')}): {describe_eq(eq)} "
                                f"(mastering.match fits and applies it)", {'type': 'eq', 'params': eq}))

    # stereo / mono compatibility
    lowc = g.get('lowEndCorrelation')
    if isinstance(lowc, (int, float)) and lowc < 0.8:
        out.append(_finding('mono_low_end', 'warn', f"low-end correlation {lowc:.2f} < 0.8: the bass / kick are not mono - "
                                                    f"they lose level in mono and on club systems",
                            {'type': 'width', 'params': {'monobass': 120}}))
    corr = g.get('stereoCorrelation')
    width = g.get('widthPct')
    if isinstance(corr, (int, float)):
        loss = 10 * math.log10(1 + max(0.0, width or 0.0) / 100.0) if isinstance(width, (int, float)) else None
        tail = f" (mono sum ~{loss:.1f} dB quieter)" if loss is not None else ''
        if corr < 0.0:
            out.append(_finding('mono_compat', 'warn', f"L/R correlation {corr:.2f} < 0: parts cancel in mono{tail}",
                                {'type': 'width', 'params': {'width': 0.85}}))
        elif corr < 0.2:
            out.append(_finding('mono_compat', 'info', f"L/R correlation {corr:.2f}: very wide - check mono{tail}"))
        else:
            out.append(_finding('mono_compat', 'ok', f"L/R correlation {corr:.2f}{tail}"))
    tw = ((rep.get('space') or {}).get('targets') or {}).get('widthAbove150HzPct')
    wa = (rep.get('space') or {}).get('widthAbove150HzPct', _cmp._num(meas, 'stereo', 'above150Hz', 'widthPct'))
    if isinstance(tw, list) and len(tw) == 2 and isinstance(wa, (int, float)):
        if wa < tw[0]:
            out.append(_finding('narrow', 'info', f"width above 150 Hz {wa:.0f} % < {tw[0]:g} % ({prof}): a master width "
                                                  f"x{min(1.25, math.sqrt(tw[0] * 1.1 / max(wa, 0.5))):.2f} helps a little; "
                                                  f"the real fix is wider parts (space.opportunities)"))
        elif wa > tw[1]:
            out.append(_finding('wide', 'info', f"width above 150 Hz {wa:.0f} % > {tw[1]:g} % ({prof})",
                                {'type': 'width', 'params': {'width': round(max(0.85, math.sqrt(tw[1] * 0.95 / wa)), 2)}}))

    # the master chain itself
    if isinstance(render, dict) and render.get('master') is not None:
        if _cmp._limiter_gain(render) is None:
            out.append(_finding('no_limiter', 'warn', "the master chain has no limiter: nothing keeps the true peak under "
                                                      f"{tp_max:g} dBTP", {'type': 'limiter', 'params': {'ceiling': -1.2}}))
    order = {'warn': 0, 'info': 1, 'ok': 2}
    out.sort(key=lambda f: order.get(f['severity'], 3))
    return out


# ------------------------------------------------------------------------------------------ printing

def summary_lines(plan: MasterPlan) -> list[str]:
    t = plan.targets
    lines = [f"master    {plan.source}  (profile {plan.profile}, platform {plan.platform})"]
    lines += [f"  {x}" for x in plan.log]
    lines.append(f"  chain: {' > '.join(f.type for f in plan.chain())}  -> {t['lufs']:g} LUFS-I, <= {t['truePeakDbtp']:g} dBTP")
    lines.append(f"  song.py: {plan.snippet()}")
    lines.append(f"  plan     {Path(plan.out) / 'master.json'}")
    return lines


def check_lines(findings: list[dict]) -> list[str]:
    lines = []
    for f in findings:
        lines.append(f"  {f['severity']:<4} {f['code']:<18} {f['message']}" +
                     (f"  fix: {json.dumps(f['fix'])}" if f.get('fix') else ''))
    return lines


def result_lines(res: dict) -> list[str]:
    b, a = res['before'], res['after']
    lines = [f"mastered  {res['mastered']}  (limiter drive {res['limiterGain']:+g} dB after "
             f"{len(res['calibration'])} pass{'es' if len(res['calibration']) != 1 else ''})"]
    if res.get('cappedByDensity'):
        lines.append(f"  loudness target {res['target']['lufs']:g} not reached: the crest factor would fall under "
                     f"{res['crestFloorDb']:g} dB (denser than the reference allows) - make the mix denser first")
    elif res.get('cappedByMaxDrive'):
        lines.append(f"  loudness target {res['target']['lufs']:g} not reached: the platform's limiting budget is used up")
    if res.get('appliedScale', 1.0) != 1.0:
        lines.append(f"  backed off: eq / width x{res['appliedScale']:g} ({res['backoff']})")
    for k, label in (('lufs', 'LUFS-I'), ('truePeakDbtp', 'dBTP'), ('lra', 'LRA'), ('plr', 'PLR'),
                     ('widthAbove150HzPct', 'width >150 Hz %'), ('correlation', 'correlation'), ('crestDb', 'crest dB')):
        lines.append(f"  {label:<16} {b.get(k)!s:>7} -> {a.get(k)!s:>7}")
    if res.get('compare'):
        cb, ca = res['compare']['before'], res['compare']['after']
        lines.append(f"  vs reference: spectrum rms {cb['spectrumRmsDb']} -> {ca['spectrumRmsDb']} dB, width diff "
                     f"{cb['widthDiff']} -> {ca['widthDiff']}, loudness diff {cb['lufsDiff']} -> {ca['lufsDiff']} LU")
        lines.append(f"    bands before {cb['bandsDiffDb']}")
        lines.append(f"    bands after  {ca['bandsDiffDb']}")
    w = res['warnings']
    lines.append(f"  warnings: new {w['new'] or 'none'}, resolved {w['resolved'] or 'none'}")
    if res.get('mp3'):
        lines.append(f"  mp3      {res['mp3']}")
    return lines
