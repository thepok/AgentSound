"""Reference-track comparison: how does the song's mix differ from a commercial reference?

    python -m agentsound compare songs/<slug> --ref <audio> [--ref-start 1:02 --ref-end 1:32] [--section chorus]

The reference (mp3/wav/flac/m4a/ogg ... anything ffmpeg reads) is decoded to 48 kHz float into
songs/<slug>/out/compare/<ref>/ref.wav; both the reference and the song's last full render (out/mix.wav,
or the `--section`'s time range of it) are analysed by the engine (`agentsound analyze`: the render's
analysis plus report["measures"], engine/analysis/Measures.h). The comparison is LOUDNESS-MATCHED: the
spectra are compared relative to each file's integrated loudness (what a listener hears after streaming
normalisation), everything else is level-independent. Output next to ref.wav:

    compare.json   metrics side by side, the 1/3-octave spectra and their difference, stereo width and
                   correlation per octave, short-term loudness distributions, transients, tails, and
                   prioritised suggestions phrased in render-format terms (eq bands, width, compressor,
                   limiter) naming the song's tracks that carry the band in question
    compare.png    the same as a picture (engine `compare-png`); LOOK at it
    mix/, ref/     the two analysis reports (ref/ also with the usual images of the reference)

Nothing here is copied into the repo: out/ is gitignored, and only the excerpt is decoded.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import unicodedata
from pathlib import Path

BAND_NAMES = ('sub', 'bass', 'lowmid', 'mid', 'presence', 'brilliance', 'air')
BAND_EDGES = (20, 60, 250, 800, 2500, 6000, 12000, 20000)
BAND_LABELS = {'sub': 'sub', 'bass': 'bass', 'lowmid': 'low mids', 'mid': 'mids', 'presence': 'presence',
               'brilliance': 'brilliance', 'air': 'air'}
TOL_DB = 1.5          # tonal differences below this are "matched"
MIN_SECONDS = 6.0     # shortest excerpt worth comparing (short-term loudness is 3 s, tempo needs ~4 s)


class CompareError(Exception):
    pass


# ------------------------------------------------------------------------------ small helpers

def parse_time(text) -> float:
    """'83.5', '1:23.5' or '1:01:23' -> seconds."""
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        if text < 0:
            raise CompareError(f"time must be >= 0, got {text!r}")
        return float(text)
    s = str(text).strip()
    parts = s.split(':')
    if not s or len(parts) > 3:
        raise CompareError(f"bad time {text!r} (use m:ss.s or seconds)")
    total = 0.0
    for p in parts:
        try:
            v = float(p)
        except ValueError:
            raise CompareError(f"bad time {text!r} (use m:ss.s or seconds)") from None
        if v < 0 or not math.isfinite(v):
            raise CompareError(f"bad time {text!r}")
        total = total * 60.0 + v
    return total


def fmt_time(sec: float) -> str:
    sec = max(0.0, float(sec))
    m = int(sec // 60)
    return f"{m}:{sec - 60 * m:04.1f}"


def slug(text: str, limit: int = 40) -> str:
    s = re.sub(r'[^A-Za-z0-9_-]+', '_', text).strip('_').lower()
    return (s[:limit].rstrip('_') or 'reference')


def _num(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d if isinstance(d, (int, float)) and not isinstance(d, bool) else default


def fmt_hz(f: float) -> str:
    if f >= 1000:
        v = f / 1000.0
        return f"{v:.1f} kHz".replace('.0 kHz', ' kHz') if v < 10 else f"{v:.0f} kHz"
    return f"{f:.0f} Hz"


def fmt_range(f0: float, f1: float) -> str:
    a, b = fmt_hz(f0), fmt_hz(f1)
    if a.endswith(' kHz') and b.endswith(' kHz'):
        return a[:-4] + '-' + b
    if a.endswith(' Hz') and b.endswith(' Hz'):
        return a[:-3] + '-' + b
    return f"{a}-{b}"


def half_round(x: float) -> float:
    return round(x * 2.0) / 2.0


def band_of(f: float) -> str:
    for i, name in enumerate(BAND_NAMES):
        if f < BAND_EDGES[i + 1]:
            return name
    return BAND_NAMES[-1]


# ------------------------------------------------------------------------------ engine + ffmpeg

def decode_reference(ffmpeg: str, src: Path, dst: Path, start: float | None, end: float | None) -> None:
    """Decode (an excerpt of) any audio file to 48 kHz stereo float WAV."""
    if not src.is_file():
        raise CompareError(f"reference not found: {src}")
    cmd = [ffmpeg, '-y', '-hide_banner', '-loglevel', 'error']
    if start:
        cmd += ['-ss', f"{start:.3f}"]
    if end is not None:
        dur = end - (start or 0.0)
        if dur <= 0.05:
            raise CompareError(f"--ref-end ({fmt_time(end)}) must be after --ref-start ({fmt_time(start or 0)})")
        cmd += ['-t', f"{dur:.3f}"]
    cmd += ['-i', str(src), '-vn', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_f32le', str(dst)]
    dst.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0 or not dst.is_file() or dst.stat().st_size < 1024:
        why = (proc.stderr or '').strip()[:300] or ('no audio' + (f" (is --ref-start {fmt_time(start)} beyond the end of the file?)"
                                                              if start else ''))
        raise CompareError(f"ffmpeg could not decode {src.name}: {why}")


def run_analyze(engine: Path, wav: Path, out: Path, *, tempo=None, start_beat=None, from_sec=None, to_sec=None,
                profile=None, pngs=True, title=None, sections=()) -> dict:
    cmd = [str(engine), 'analyze', str(wav), '--out', str(out)]
    if tempo:
        cmd += ['--tempo', f"{tempo:g}"]
    if start_beat:
        cmd += ['--start-beat', f"{start_beat:g}"]
    if from_sec:
        cmd += ['--from', f"{from_sec:.4f}"]
    if to_sec is not None:
        cmd += ['--to', f"{to_sec:.4f}"]
    if profile:
        cmd += ['--profile', profile]
    if title:
        # NFKC folds full-width quotes / backslashes (YouTube titles: '＂Dangerous Days＂') to ASCII, which
        # subprocess escapes; left as they are, Windows' ANSI argv maps them to a bare '"' and splits the argument.
        cmd += ['--title', unicodedata.normalize('NFKC', title)]
    for name, a, b in sections:
        cmd += ['--section', name, f"{a:.4f}", f"{b:.4f}"]
    if not pngs:
        cmd.append('--no-png')
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise CompareError(f"engine analyze failed for {wav.name}: {(proc.stderr or proc.stdout).strip()[:400]}")
    for line in reversed((proc.stdout or '').strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {}


def render_png(engine: Path, compare_json: Path, png: Path) -> None:
    proc = subprocess.run([str(engine), 'compare-png', str(compare_json), '--out', str(png)], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise CompareError(f"engine compare-png failed: {(proc.stderr or proc.stdout).strip()[:400]}")


# ------------------------------------------------------------------------------ comparison

def _spectra(mix: dict, ref: dict):
    """Loudness-matched 1/3-octave spectra (dB re integrated loudness) and which bands carry data."""
    ms, rs = mix['measures']['spectrum'], ref['measures']['spectrum']
    hz = [float(h) for h in ms['hz']]
    if [float(h) for h in rs['hz']] != hz:
        n = min(len(hz), len(rs['hz']))
        hz = hz[:n]
    mi = _num(mix, 'measures', 'loudness', 'integratedLufs', default=-120.0)
    ri = _num(ref, 'measures', 'loudness', 'integratedLufs', default=-120.0)
    mdb = [float(v) - mi for v in ms['db'][:len(hz)]]
    rdb = [float(v) - ri for v in rs['db'][:len(hz)]]
    valid = [m > -90 and r > -90 for m, r in zip(mdb, rdb)]
    # A band-limited reference (lossy codec low-pass, old recordings): above a >= 12 dB drop between
    # neighbouring bands at the top there is no data to match.
    cutoff = None
    for i in range(1, len(hz)):
        if hz[i] >= 10000 and rdb[i] < rdb[i - 1] - 12.0:
            cutoff = hz[i]
            for k in range(i, len(hz)):
                valid[k] = False
            break
    for i, f in enumerate(hz):
        if f >= 20000:                      # codec- and rate-dependent, inaudible for most: shown, not judged
            valid[i] = False
    return hz, mdb, rdb, valid, cutoff


def _smooth(diff, valid):
    out = []
    for i in range(len(diff)):
        vals = [diff[k] for k in (i - 1, i, i + 1) if 0 <= k < len(diff) and valid[k]]
        out.append(sum(vals) / len(vals) if valid[i] and vals else None)
    return out


def tonal_regions(hz, smooth, tol: float = TOL_DB) -> list[dict]:
    """Contiguous 1/3-octave runs where the smoothed difference exceeds tol with one sign."""
    regions, cur = [], None
    for i, v in enumerate(smooth):
        sign = 0 if v is None or abs(v) < tol else (1 if v > 0 else -1)
        if cur and sign == cur['sign']:
            cur['idx'].append(i)
            continue
        if cur:
            regions.append(cur)
        cur = {'sign': sign, 'idx': [i]} if sign else None
    if cur:
        regions.append(cur)
    out = []
    for r in regions:
        idx = r['idx']
        vals = [smooth[i] for i in idx]
        avg = sum(vals) / len(vals)
        peak = max(vals, key=abs)
        if len(idx) < 2 and abs(peak) < 3.0:
            continue
        f0 = hz[idx[0]] * 2 ** (-1 / 6)
        f1 = hz[idx[-1]] * 2 ** (1 / 6)
        octaves = math.log2(f1 / f0)
        out.append({'fromHz': round(f0, 1), 'toHz': round(f1, 1), 'centreHz': round(math.sqrt(f0 * f1), 1),
                    'avgDb': round(avg, 2), 'peakDb': round(peak, 2), 'octaves': round(octaves, 2),
                    'bands': [hz[i] for i in idx]})
    return out


def eq_move(region: dict, full_low: bool, full_high: bool) -> dict:
    """The eq band (render-format params) that undoes a region: shelves at the ends, a bell inside."""
    gain = max(-6.0, min(6.0, -half_round(region['avgDb'])))
    if gain == 0.0:
        gain = -0.5 if region['avgDb'] > 0 else 0.5
    f0, f1, fc = region['fromHz'], region['toHz'], region['centreHz']
    if full_low and f1 <= 300:
        f = int(round(min(max(f1, 40), 250) / 5.0) * 5)
        return {'kind': 'low shelf', 'params': {'low.freq': f, 'low.gain': gain}, 'text': f"{gain:+.1f} dB low shelf below {fmt_hz(f)}"}
    if full_high and f0 >= 1500:
        f = int(round(min(max(f0, 2000), 16000) / 100.0) * 100)
        return {'kind': 'high shelf', 'params': {'high.freq': f, 'high.gain': gain}, 'text': f"{gain:+.1f} dB high shelf above {fmt_hz(f)}"}
    q = max(0.4, min(2.0, fc / max(1.0, f1 - f0)))
    q = round(q, 1)
    band = 'peak1' if fc < 500 else 'peak2' if fc < 2500 else 'peak3'
    f = int(round(fc / (5 if fc < 1000 else 50))) * (5 if fc < 1000 else 50)
    return {'kind': 'bell', 'params': {f'{band}.freq': f, f'{band}.gain': gain, f'{band}.q': q},
            'text': f"{gain:+.1f} dB {fmt_range(f0, f1)} (bell at {fmt_hz(f)}, Q {q:g})"}


def _distinct_bells(regions: list[dict]) -> None:
    """Gives every bell of the regions its own eq band (peak1..peak3, in frequency order) where possible, so all the
    moves fit into one eq: two low regions would otherwise both ask for peak1."""
    bells = sorted((r for r in regions if r['eq']['kind'] == 'bell'), key=lambda r: r['centreHz'])
    if len(bells) < 2 or len(bells) > 3:
        return
    names = ['peak1', 'peak2', 'peak3']
    wanted = [names.index(next(iter(r['eq']['params'])).split('.')[0]) for r in bells]
    # Keep each wish in frequency order, pushed up (or down at the top) until the bands are distinct.
    got = []
    for w in wanted:
        got.append(max(w, got[-1] + 1) if got else w)
    overflow = got[-1] - (len(names) - 1)
    if overflow > 0:
        got = [g - overflow for g in got]
        for i in range(len(got) - 2, -1, -1):
            got[i] = min(got[i], got[i + 1] - 1)
    if any(g < 0 for g in got):
        return
    for r, g in zip(bells, got):
        old = r['eq']['params']
        r['eq']['params'] = {f"{names[g]}.{k.split('.', 1)[1]}": v for k, v in old.items()}


def contributors(song_report: dict | None, band: str, limit: int = 3, min_pct: float = 15.0) -> list[tuple[str, float]]:
    """Tracks carrying most of a report band in the song's render (report nodes[].mixSharePct)."""
    if not isinstance(song_report, dict):
        return []
    out = []
    for n in song_report.get('nodes') or []:
        if not isinstance(n, dict) or n.get('bus'):
            continue
        share = _num(n, 'mixSharePct', band)
        if share is not None and share >= min_pct:
            out.append((str(n.get('id')), float(share)))
    out.sort(key=lambda x: -x[1])
    return out[:limit]


def _limiter_gain(render: dict | None):
    """(index, gain) of the master limiter in the render JSON, or None."""
    if not isinstance(render, dict):
        return None
    chain = (render.get('master') or {}).get('fx') or []
    for i, fx in enumerate(chain):
        if isinstance(fx, dict) and fx.get('type') == 'limiter':
            g = (fx.get('params') or {}).get('gain', 0.0)
            return i, float(g) if isinstance(g, (int, float)) else 0.0
    return None


# A metric difference at least this big is flagged (amber in compare.png).
FLAG = {'lufs': 1.0, 'stMax': 1.5, 'lra': 3.0, 'truePeak': 1.0, 'plr': 2.0, 'psr': 2.0, 'crest': 2.0, 'lowCrest': 2.0,
        'punchLow': 3.0, 'punchMid': 3.0, 'punchHigh': 3.0, 'density': 2.0, 'width': 10.0, 'corr': 0.15, 'lowCorr': 0.05,
        'tilt': 0.5, 'tail': 0.25, 'lateEarly': 3.0}


def _metric(key, label, unit, mix, ref, fmt='{:.1f}', note=''):
    diff = None if mix is None or ref is None else round(mix - ref, 2)
    flag = diff is not None and not note and abs(diff) >= FLAG.get(key, float('inf'))
    return {'key': key, 'label': label, 'unit': unit, 'mix': mix, 'ref': ref, 'diff': diff, 'fmt': fmt, 'note': note,
            'flag': flag}


def compare_reports(mix: dict, ref: dict, *, song_report: dict | None = None, render: dict | None = None,
                    mix_label: str = 'mix', ref_label: str = 'reference', excerpt_note: str = '') -> dict:
    """The comparison (compare.json content) of two `agentsound analyze` reports."""
    for name, r in (('mix', mix), ('reference', ref)):
        if not isinstance(r, dict) or 'measures' not in r:
            raise CompareError(f"the {name} report has no 'measures' (made by an older engine? rebuild it)")
    mg, rg = mix.get('global', {}), ref.get('global', {})
    mm, rm = mix['measures'], ref['measures']
    mi = _num(mm, 'loudness', 'integratedLufs', default=-120.0)
    ri = _num(rm, 'loudness', 'integratedLufs', default=-120.0)
    if mi <= -70 or ri <= -70:
        raise CompareError(f"{'the mix' if mi <= -70 else 'the reference'} is silent (integrated loudness below -70 LUFS)")
    offset = round(ri - mi, 2)

    hz, mdb, rdb, valid, cutoff = _spectra(mix, ref)
    diff = [round(m - r, 2) if v else None for m, r, v in zip(mdb, rdb, valid)]
    smooth = _smooth([d if d is not None else 0.0 for d in diff], valid)
    regions = tonal_regions(hz, smooth)
    first_valid = next((i for i, v in enumerate(valid) if v), 0)
    last_valid = max((i for i, v in enumerate(valid) if v), default=len(valid) - 1)
    for r in regions:
        full_low = r['bands'][0] <= hz[min(first_valid + 2, len(hz) - 1)]
        full_high = r['bands'][-1] >= hz[max(last_valid - 2, 0)]
        r['eq'] = eq_move(r, full_low, full_high)
        r['band'] = band_of(r['centreHz'])
    _distinct_bells(regions)

    # Per report band, loudness-matched (energy sums of the 1/3-octave bands inside it).
    bands = []
    for b, name in enumerate(BAND_NAMES):
        idx = [i for i, f in enumerate(hz) if BAND_EDGES[b] <= f < BAND_EDGES[b + 1] and valid[i]]
        if not idx:
            continue
        me = 10 * math.log10(sum(10 ** (mdb[i] / 10) for i in idx))
        re_ = 10 * math.log10(sum(10 ** (rdb[i] / 10) for i in idx))
        bands.append({'name': name, 'range': f"{fmt_range(BAND_EDGES[b], BAND_EDGES[b + 1])}", 'mixDb': round(me, 1),
                      'refDb': round(re_, 1), 'diffDb': round(me - re_, 1)})

    ms, rs = mm.get('stereo', {}), rm.get('stereo', {})
    ml, rl = mm.get('loudness', {}), rm.get('loudness', {})
    mt, rt = mm.get('transients', {}), rm.get('transients', {})
    md, rd = mm.get('decay', {}), rm.get('decay', {})
    msu, rsu = mm.get('sustain', {}), rm.get('sustain', {})
    space_ok = bool(md.get('robust')) and bool(rd.get('robust'))
    sustain_ok = bool(msu.get('robust')) and bool(rsu.get('robust'))
    mdur, rdur = _num(mm, 'seconds', default=0.0), _num(rm, 'seconds', default=0.0)
    similar_span = mdur > 0 and rdur > 0 and 0.5 <= mdur / rdur <= 2.0

    metrics = [
        _metric('lufs', 'integrated loudness', 'LUFS', mi, ri),
        _metric('stMax', 'short-term max', 'LUFS', _num(mg, 'shortTermMax'), _num(rg, 'shortTermMax')),
        _metric('lra', 'loudness range', 'LU', _num(ml, 'loudnessRange'), _num(rl, 'loudnessRange'),
                note='' if similar_span else 'lengths differ'),
        _metric('truePeak', 'true peak', 'dBTP', _num(mg, 'truePeakDbtp'), _num(rg, 'truePeakDbtp'), fmt='{:.2f}'),
        _metric('plr', 'PLR peak/loudness', 'dB', _num(mg, 'plr'), _num(rg, 'plr')),
        _metric('psr', 'PSR peak/short-term', 'dB', _num(ml, 'psrDb'), _num(rl, 'psrDb')),
        _metric('crest', 'crest factor', 'dB', _num(mt, 'crestDb'), _num(rt, 'crestDb')),
        _metric('lowCrest', 'crest < 150 Hz', 'dB', _num(mt, 'lowCrestDb'), _num(rt, 'lowCrestDb')),
        _metric('punchLow', 'punch low (kick)', 'dB', _num(mt, 'low', 'hitDb'), _num(rt, 'low', 'hitDb')),
        _metric('punchMid', 'punch mid (snare)', 'dB', _num(mt, 'mid', 'hitDb'), _num(rt, 'mid', 'hitDb')),
        _metric('punchHigh', 'punch high (hats)', 'dB', _num(mt, 'high', 'hitDb'), _num(rt, 'high', 'hitDb')),
        _metric('density', 'transients', '/s', _num(mt, 'mid', 'perSec'), _num(rt, 'mid', 'perSec'), fmt='{:.1f}'),
        _metric('width', 'width > 150 Hz', '%', _num(ms, 'above150Hz', 'widthPct'), _num(rs, 'above150Hz', 'widthPct'), fmt='{:.0f}'),
        _metric('corr', 'L/R correlation', '', _num(ms, 'whole', 'correlation'), _num(rs, 'whole', 'correlation'), fmt='{:.2f}'),
        _metric('lowCorr', 'correlation < 120 Hz', '', _num(ms, 'below120Hz', 'correlation'), _num(rs, 'below120Hz', 'correlation'),
                fmt='{:.2f}'),
        _metric('tilt', 'spectral tilt', 'dB/oct', _num(mg, 'spectralTiltDbPerOct'), _num(rg, 'spectralTiltDbPerOct'), fmt='{:.2f}'),
        _metric('tail', 'tail T60', 's', _num(md, 'tailT60Sec'), _num(rd, 'tailT60Sec'), fmt='{:.2f}',
                note='' if space_ok else 'not robust'),
        _metric('lateEarly', 'after-hit energy', 'dB', _num(msu, 'lateEarlyDb'), _num(rsu, 'lateEarlyDb'),
                note='' if sustain_ok else 'not robust'),
        _metric('tempo', 'tempo (estimated)', 'BPM', _num(mm, 'tempo', 'bpm'), _num(rm, 'tempo', 'bpm'), fmt='{:.1f}'),
    ]

    sug = _suggestions(mix=mix, ref=ref, regions=regions, song_report=song_report, render=render, offset=offset,
                       space_ok=space_ok, sustain_ok=sustain_ok, similar_span=similar_span)
    for i, s in enumerate(sug, 1):
        s['priority'] = i
    notes = [excerpt_note] if excerpt_note else []
    if cutoff:
        notes.append(f"the reference has (almost) nothing above ~{fmt_hz(cutoff)} (a lossy codec's low-pass, an old or very "
                     f"dark recording): not judged there")
    if (_num(rs, 'above150Hz', 'widthPct', default=100.0) or 0.0) < 3.0:
        notes.append("the reference is (almost) mono: stereo width is not compared")

    oct_hz = ms.get('octaveHz') or []
    stereo = {'octaveHz': oct_hz, 'mixWidthPct': ms.get('widthPct') or [], 'refWidthPct': rs.get('widthPct') or [],
              'mixCorrelation': ms.get('correlation') or [], 'refCorrelation': rs.get('correlation') or []}
    hist = {'fromLu': (ml.get('histogram') or {}).get('fromLu', -30), 'stepLu': (ml.get('histogram') or {}).get('stepLu', 1),
            'mixPct': (ml.get('histogram') or {}).get('pct') or [], 'refPct': (rl.get('histogram') or {}).get('pct') or []}
    width_mix, width_ref = _num(ms, 'above150Hz', 'widthPct'), _num(rs, 'above150Hz', 'widthPct')
    head = [f"loudness {mi:.1f} vs {ri:.1f} LUFS ({mi - ri:+.1f} LU)"]
    big = sorted(regions, key=lambda r: -abs(r['avgDb']) * (0.6 + 0.4 * min(r['octaves'], 3)))[:2]
    head += [f"{BAND_LABELS[r['band']]} {r['avgDb']:+.1f} dB ({fmt_range(r['fromHz'], r['toHz'])})" for r in big]
    if width_mix is not None and width_ref is not None:
        head.append(f"width >150 Hz {width_mix:.0f}% vs {width_ref:.0f}%")
    if _num(mt, 'crestDb') is not None and _num(rt, 'crestDb') is not None:
        head.append(f"crest {_num(mt, 'crestDb'):.1f} vs {_num(rt, 'crestDb'):.1f} dB")
    return {
        'format': 'agentsound.compare', 'version': 1,
        'summary': ' | '.join(head),
        'mix': {'label': mix_label, 'seconds': mdur, 'lufs': mi, 'report': mix.get('_path'),
                'fromSec': _num(mix, 'render', 'fromSec'), 'toSec': _num(mix, 'render', 'toSec')},
        'reference': {'label': ref_label, 'seconds': rdur, 'lufs': ri, 'report': ref.get('_path'),
                      'fromSec': _num(ref, 'render', 'fromSec'), 'toSec': _num(ref, 'render', 'toSec'),
                      'bandLimitedAboveHz': cutoff},
        'loudnessMatch': {'mixLufs': mi, 'refLufs': ri, 'offsetDb': offset,
                          'note': f"spectra are compared relative to each file's integrated loudness (the mix as if "
                                  f"{abs(offset):.1f} dB {'louder' if offset >= 0 else 'quieter'}), like streaming normalisation"},
        'excerptNote': excerpt_note,
        'notes': notes,
        'metrics': metrics,
        'spectrum': {'hz': hz, 'mixDb': [round(v, 1) for v in mdb], 'refDb': [round(v, 1) for v in rdb], 'diffDb': diff,
                     'smoothDiffDb': [None if v is None else round(v, 2) for v in smooth], 'valid': valid,
                     'toleranceDb': TOL_DB, 'regions': regions,
                     'note': "dB relative to the integrated loudness; diff = mix - reference, smoothed over 3 bands (~1 octave)"},
        'bands': bands,
        'stereo': stereo,
        'dynamics': {'histogram': hist,
                     'mix': ml.get('shortTermLu') or {}, 'ref': rl.get('shortTermLu') or {},
                     'note': 'short-term (3 s) loudness relative to the integrated loudness, EBU R128 gated'},
        'suggestions': sug,
    }


def _suggestions(*, mix, ref, regions, song_report, render, offset, space_ok, sustain_ok, similar_span) -> list[dict]:
    mm, rm = mix['measures'], ref['measures']
    out: list[dict] = []

    def add(area, score, text, fix=None, size=None):
        out.append({'area': area, 'score': round(score, 2), 'text': text, **({'fix': fix} if fix else {}),
                    **({'sizeDb': size} if size is not None else {})})

    # Loudness: match the reference, but not outside the song's loudness target (a quiet old master or a
    # normalised rip is no reason to turn the mix down; a hyper-loud master costs punch).
    mi, ri = _num(mm, 'loudness', 'integratedLufs'), _num(rm, 'loudness', 'integratedLufs')
    lim = _limiter_gain(render)
    target = ((song_report or {}).get('reference') or {}).get('lufsTarget') if isinstance(song_report, dict) else None
    lo_t, hi_t = (target if isinstance(target, list) and len(target) == 2 else (-14.0, -8.0))
    d = mi - ri
    if abs(d) >= 1.0:
        # The goal is the reference's loudness clamped into the song's target window; a mix inside its window
        # that is louder than the reference stays where it is.
        goal = min(max(ri, lo_t), hi_t)
        if d > 0 and lo_t <= mi <= hi_t:
            goal = None
        if goal is None or abs(mi - goal) < 0.5:
            where_mix = ('inside' if lo_t <= mi <= hi_t else 'at the edge of') + f" its target ({lo_t:g}..{hi_t:g} LUFS)"
            ref_note = ("an older or more dynamic master, or a normalised rip" if d > 0 else
                        "a hotter master than this song's target allows")
            add('loudness', 0.5,
                f"Loudness: the reference is {abs(d):.1f} LU {'quieter' if d > 0 else 'louder'} ({ri:.1f} vs {mi:.1f} LUFS: "
                f"{ref_note}); the mix is {where_mix}: keep it. Everything else here is loudness-matched.")
        else:
            if goal == ri:
                why = f"the reference's {ri:.1f} LUFS"
            elif goal == hi_t:
                why = (f"the top of the song's target ({lo_t:g}..{hi_t:g} LUFS; the reference's {ri:.1f} LUFS "
                       f"{'costs punch' if ri > hi_t else 'is outside it'})")
            else:
                why = f"the bottom of the song's target ({lo_t:g}..{hi_t:g} LUFS; the reference is a quiet master at {ri:.1f})"
            step = mi - goal
            if lim:
                where = f" (master limiter gain {lim[1]:g} -> {lim[1] - step:.1f} dB)"
            elif step < 0:
                where = " (add {\"type\": \"limiter\", \"params\": {\"ceiling\": -1.0}} last on the master and raise its gain)"
            else:
                where = " (the master's \"gainDb\")"
            tp = _num(mix, 'global', 'truePeakDbtp')
            add('loudness', abs(step),
                f"Loudness: the mix is {abs(d):.1f} LU {'quieter' if d < 0 else 'louder'} than the reference ({mi:.1f} vs "
                f"{ri:.1f} LUFS). {'Raise' if step < 0 else 'Lower'} the master level by ~{abs(step):.1f} dB to {why}{where}" +
                (" - the rest of this comparison is loudness-matched, so fix tone and dynamics first." if step < 0 else '.') +
                (f" Keep the true peak <= -1 dBTP (now {tp:+.2f})." if tp is not None and step < 0 else ''),
                fix=({'target': 'master limiter', 'params': {'gain': round((lim[1] if lim else 0.0) - step, 1)}} if lim or step < 0
                     else {'target': 'master', 'gainDbChange': round(-step, 1)}), size=round(-step, 1))

    # Tone (loudness-matched spectrum regions).
    for r in regions:
        eq = r['eq']
        who = contributors(song_report, r['band'])
        on = (" on " + ', '.join(f"'{t}' ({p:.0f} % of the {r['band']} band)" for t, p in who) + " or on the master") if who else \
            " on the master (or the parts that carry this range)"
        more = 'more' if r['avgDb'] > 0 else 'less'
        fx = {'type': 'eq', 'params': eq['params']}
        capped = ' (capped at 6 dB: compare again after)' if abs(r['avgDb']) > 6.25 else ''
        add('tone', abs(r['avgDb']) * min(2.0, 0.6 + 0.4 * r['octaves']),
            f"Tone: {abs(r['avgDb']):.1f} dB {more} {BAND_LABELS[r['band']]} than the reference, {fmt_range(r['fromHz'], r['toHz'])} "
            f"(loudness-matched, peak {r['peakDb']:+.1f} dB): {eq['text']}{capped} ({json.dumps(fx)}){on}.",
            fix=fx, size=-r['avgDb'])

    # Stereo.
    ms, rs = mm.get('stereo', {}), rm.get('stereo', {})
    wm, wr = _num(ms, 'above150Hz', 'widthPct'), _num(rs, 'above150Hz', 'widthPct')
    if wm is not None and wr is not None and wm > 0.5 and wr >= 3.0:   # a (nearly) mono reference says nothing about width
        ratio_db = 10 * math.log10(wr / wm)
        rng = _width_gap_range(ms, rs, ref_wider=ratio_db > 0)
        if ratio_db >= 1.5 and wr - wm >= 8:
            factor = max(1.1, min(1.8, math.sqrt(wr / wm)))
            opp = [o.get('id') for o in ((song_report or {}).get('space') or {}).get('opportunities') or [] if isinstance(o, dict)]
            parts = f"'{opp[0]}'" + (f", '{opp[1]}'" if len(opp) > 1 else '') if opp else 'pads, keys, arps (not bass/kick)'
            add('stereo', ratio_db * 1.1,
                f"Stereo: the reference is wider above 150 Hz ({wr:.0f} % vs {wm:.0f} % side/mid){rng}: widen "
                f"{'that range' if rng else 'the music parts'} ~{(factor - 1) * 100:.0f} % "
                f"({{\"type\": \"width\", \"params\": {{\"width\": {factor:.2f}}}}} or chorus/ensemble) on {parts}; "
                f"stereo reverb returns widen too.", fix={'type': 'width', 'params': {'width': round(factor, 2)}})
        elif ratio_db <= -2.0 and wm - wr >= 10:
            factor = max(0.5, min(0.95, math.sqrt(wr / wm)))
            add('stereo', -ratio_db * 0.8,
                f"Stereo: the mix is wider than the reference above 150 Hz ({wm:.0f} % vs {wr:.0f} %){rng}: check mono "
                f"compatibility and narrow the widest parts ({{\"type\": \"width\", \"params\": {{\"width\": {factor:.2f}}}}}).",
                fix={'type': 'width', 'params': {'width': round(factor, 2)}})
    lm, lr = _num(ms, 'below120Hz', 'correlation'), _num(rs, 'below120Hz', 'correlation')
    if lm is not None and lr is not None and lm < 0.9 and lr >= lm + 0.05:
        add('stereo', 3.0 + (0.9 - lm) * 5,
            f"Low end: below 120 Hz the mix correlates {lm:.2f} (reference {lr:.2f}): make the lows mono "
            f"({{\"type\": \"width\", \"params\": {{\"monobass\": 120}}}} on the master or the bass bus).",
            fix={'type': 'width', 'params': {'monobass': 120}})

    # Dynamics: density (crest / PSR) and punch.
    mt, rt = mm.get('transients', {}), rm.get('transients', {})
    cm, cr = _num(mt, 'crestDb'), _num(rt, 'crestDb')
    pm, pr = _num(mm, 'loudness', 'psrDb'), _num(rm, 'loudness', 'psrDb')
    if cm is not None and cr is not None:
        dc = cm - cr
        psr = f", PSR {pm:.1f} vs {pr:.1f} dB" if pm is not None and pr is not None else ''
        if dc >= 2.0:
            add('dynamics', dc * 0.9,
                f"Density: the reference is more compressed (crest {cr:.1f} dB vs {cm:.1f}{psr}): glue the mix with bus "
                f"compression before the limiter ({{\"type\": \"compressor\", \"params\": {{\"threshold\": -20, \"ratio\": 2, "
                f"\"attack\": 30, \"release\": 200, \"knee\": 6}}}} on the master or the music bus, ~2-3 dB gain reduction)"
                + (" and drive the limiter harder." if mi is not None and ri is not None and mi < ri else '.'),
                fix={'type': 'compressor', 'params': {'threshold': -20, 'ratio': 2, 'attack': 30, 'release': 200, 'knee': 6}},
                size=round(-dc, 1))
        elif dc <= -2.0:
            add('dynamics', -dc * 0.9,
                f"Density: the mix is more squashed than the reference (crest {cm:.1f} dB vs {cr:.1f}{psr}): less limiter gain, "
                f"a slower attack (20-30 ms) on bus compressors, or parallel instead of full compression.", size=round(-dc, 1))
    for band, who, hint_less, hint_more in (
            ('low', 'kick/low end', "less limiting, a slower drum-bus compressor attack (20-30 ms), or duck the bass harder "
                                    "under the kick (ducker depth)",
             "a denser low end: longer bass notes, less ducking depth, or compress the drum bus"),
            ('mid', 'snare/mid', "a transient shaper or a slower compressor attack on the drums, less limiting",
             "tame the snare/percussion peaks: faster attack on the drum bus compressor"),
            ('high', 'hats/top', "sharper hats (shorter decay, less reverb on them) or a slower attack on the drum bus",
             "softer hats: lower velocity/gain or a fast compressor on them")):
        hm, hr = _num(mt, band, 'hitDb'), _num(rt, band, 'hitDb')
        if hm is None or hr is None:
            continue
        dh = hm - hr
        if abs(dh) >= 3.0:
            add('punch', abs(dh) * 0.45,
                f"Punch ({who}): the main hits rise {hm:.0f} dB over their surroundings vs {hr:.0f} dB in the reference: " +
                (hint_less if dh < 0 else hint_more) + '.', size=round(-dh, 1))

    # Loudness distribution (only for comparable spans).
    if similar_span:
        pm10, pr10 = _num(mm, 'loudness', 'shortTermLu', 'p10'), _num(rm, 'loudness', 'shortTermLu', 'p10')
        if pm10 is not None and pr10 is not None and abs(pm10 - pr10) >= 3.0:
            quieter = pm10 < pr10
            add('dynamics', abs(pm10 - pr10) * 0.5,
                f"Macro dynamics: the quieter 10 % of the mix sits {abs(pm10):.1f} LU under its average vs {abs(pr10):.1f} LU in "
                f"the reference: " + ("lift the quiet sections (arrangement, gainDb automation) or compress the music bus more."
                                      if quieter else "give verses/breakdowns more contrast (fewer parts, lower gainDb)."))

    # Space (only when both estimates are robust).
    if space_ok:
        tm, tr = _num(mm, 'decay', 'tailT60Sec'), _num(rm, 'decay', 'tailT60Sec')
        if tm and tr:
            ratio = tm / tr
            if ratio <= 0.7:
                add('space', 2.0 + (1 - ratio) * 2,
                    f"Space: the reference's tails ring longer (T60 ~{tr:.1f} s vs {tm:.1f} s after hits): a longer reverb decay "
                    f"(\"decay\"/\"size\" on the hall) or more send to it.")
            elif ratio >= 1.4:
                add('space', 2.0 + min(2.0, ratio - 1),
                    f"Space: the mix rings longer than the reference (T60 ~{tm:.1f} s vs {tr:.1f} s): shorter reverb decay or less "
                    f"send; high-pass the reverb returns so the low end stays tight.")
    if sustain_ok:
        sm, sr = _num(mm, 'sustain', 'lateEarlyDb'), _num(rm, 'sustain', 'lateEarlyDb')
        if sm is not None and sr is not None and abs(sm - sr) >= 3.0:
            add('space', abs(sm - sr) * 0.5,
                f"Sustain: 80-300 ms after the hits the reference keeps {sr - sm:+.1f} dB {'more' if sr > sm else 'less'} energy "
                f"({sr:.1f} vs {sm:.1f} dB re the hit): " +
                ("more reverb/room send or longer releases." if sr > sm else "drier, shorter tails or tighter releases."))

    out.sort(key=lambda s: -s['score'])
    return out


def _width_gap_range(ms: dict, rs: dict, ref_wider: bool = True) -> str:
    """' (mostly 250 Hz-4 kHz)': the octaves (250 Hz-8 kHz) where the reference (ref_wider) or the mix is > 2 dB wider."""
    hz = ms.get('octaveHz') or []
    wm, wr = ms.get('widthPct') or [], rs.get('widthPct') or []
    sign = 1.0 if ref_wider else -1.0
    idx = [i for i, f in enumerate(hz) if 250 <= f <= 8000 and i < len(wm) and i < len(wr) and wm[i] > 0.5 and wr[i] > 0.5
           and sign * 10 * math.log10(wr[i] / wm[i]) >= 2.0]
    if not idx:
        return ''
    f0, f1 = hz[idx[0]] / math.sqrt(2), hz[idx[-1]] * math.sqrt(2)
    return f" (mostly {fmt_range(f0, f1)})"


# ------------------------------------------------------------------------------ the command

def _load_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def run(song_dir: Path, ref: Path, engine: Path, ffmpeg: str, *, ref_start=None, ref_end=None, section: str | None = None,
        mix_start=None, mix_end=None, out: Path | None = None, images: bool = True, png: bool = True) -> dict:
    """Decode + analyse + compare; returns {'compare', 'json', 'png', 'dir'}. Raises CompareError."""
    song_dir, ref = Path(song_dir), Path(ref)
    out_root = song_dir / 'out'
    wav = out_root / 'mix.wav'
    if not wav.is_file():
        raise CompareError(f"no render at {wav}: build the song first (python -m agentsound build {song_dir})")
    if not ref.is_file():
        raise CompareError(f"reference not found: {ref}")
    song_report = _load_json(out_root / 'report.json') or {}
    render = _load_json(out_root / 'song.render.json') or {}
    info = song_report.get('render') if isinstance(song_report.get('render'), dict) else {}
    tempo = info.get('tempo') or render.get('tempo')
    title = info.get('title') or render.get('title') or song_dir.name
    from_beat = float(info.get('fromBeat') or 0.0)
    a = b = None
    start_beat = from_beat
    rs = parse_time(ref_start) if ref_start is not None else None
    re_ = parse_time(ref_end) if ref_end is not None else None
    if section and (mix_start is not None or mix_end is not None):
        raise CompareError("give --section or --mix-start/--mix-end, not both")
    if section:
        secs = [s for s in song_report.get('sections') or [] if isinstance(s, dict) and not s.get('implicit')]
        match = next((s for s in secs if s.get('name') == section), None)
        if match is None:
            names = ', '.join(str(s.get('name')) for s in secs) or 'none (render the full song first)'
            raise CompareError(f"no section {section!r} in the last full render ({out_root / 'report.json'}); sections: {names}")
        a, b = float(match['startSec']), float(match['endSec'])
        start_beat = (float(match.get('startBar', 1.0)) - 1.0) * 4.0
        mix_label = f"{title}: {section} ({fmt_time(a)}-{fmt_time(b)})"
    elif mix_start is not None or mix_end is not None:
        a = parse_time(mix_start) if mix_start is not None else 0.0
        b = parse_time(mix_end) if mix_end is not None else None
        if b is not None and b <= a:
            raise CompareError("--mix-end must be after --mix-start")
        start_beat = from_beat + (a * tempo / 60.0 if tempo else 0.0)
        mix_label = f"{title} ({fmt_time(a)}-{fmt_time(b) if b is not None else 'end'})"
    else:
        mix_label = f"{title} (whole song)"
    dest = Path(out) if out else out_root / 'compare' / slug(ref.stem)
    dest.mkdir(parents=True, exist_ok=True)
    ref_wav = dest / 'ref.wav'
    decode_reference(ffmpeg, ref, ref_wav, rs, re_)
    ref_label = ref.name + (f" ({fmt_time(rs or 0.0)}-{fmt_time(re_)})" if re_ is not None else
                            f" (from {fmt_time(rs)})" if rs else '')
    profile = (song_report.get('reference') or {}).get('profile') if isinstance(song_report.get('reference'), dict) else None
    run_analyze(engine, wav, dest / 'mix', tempo=tempo, start_beat=start_beat, from_sec=a, to_sec=b, profile=profile,
                pngs=False, title=mix_label)
    run_analyze(engine, ref_wav, dest / 'ref', profile=profile, pngs=images, title=ref_label)
    mix_rep = _load_json(dest / 'mix' / 'report.json')
    ref_rep = _load_json(dest / 'ref' / 'report.json')
    if not isinstance(mix_rep, dict) or not isinstance(ref_rep, dict):
        raise CompareError(f"the engine wrote no readable report into {dest}")
    mix_rep['_path'] = str((dest / 'mix' / 'report.json').resolve())
    ref_rep['_path'] = str((dest / 'ref' / 'report.json').resolve())
    ms, rsec = _num(mix_rep, 'measures', 'seconds', default=0.0), _num(ref_rep, 'measures', 'seconds', default=0.0)
    for what, sec in (('the mix excerpt', ms), ('the reference excerpt', rsec)):
        if sec < MIN_SECONDS:   # no 3 s short-term loudness, tempo or punch statistics below that
            raise CompareError(f"{what} is only {sec:.1f} s: compare at least {MIN_SECONDS:g} s (a whole section / chorus)")
    note = ''
    if ms and rsec and not 0.5 <= ms / rsec <= 2.0:
        note = (f"the mix excerpt is {ms:.0f} s, the reference {rsec:.0f} s: tone, width and punch compare fine, loudness range "
                f"only for similar spans (--section / --ref-start --ref-end)")
    cmp = compare_reports(mix_rep, ref_rep, song_report=song_report, render=render, mix_label=mix_label, ref_label=ref_label,
                          excerpt_note=note)
    cmp['mix']['file'] = str(wav.resolve())
    cmp['reference']['file'] = str(ref.resolve())
    cmp['reference']['decoded'] = str(ref_wav.resolve())
    json_path = dest / 'compare.json'
    png_path = dest / 'compare.png' if png else None
    cmp['images'] = ([{'file': 'compare.png', 'shows': 'loudness-matched spectra + difference, stereo width per octave, '
                                                        'short-term loudness distribution, metrics, suggestions'}] if png else []) + \
                    ([{'file': 'ref/overview.png', 'shows': "the reference's own analysis images (ref/)"}] if images else [])
    json_path.write_text(json.dumps(cmp, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    if png_path:
        render_png(engine, json_path, png_path)
    return {'compare': cmp, 'json': json_path, 'png': png_path, 'dir': dest}


def summary_lines(cmp: dict, png: Path | None, json_path: Path) -> list[str]:
    lines = [f"compare   {cmp['mix']['label']}  vs  {cmp['reference']['label']}",
             f"  {cmp['summary']}",
             f"  {cmp['loudnessMatch']['note']}"]
    for n in cmp.get('notes') or []:
        lines.append(f"  note: {n}")
    lines.append('  metrics (mix | reference | diff):')
    for m in cmp['metrics']:
        if m['mix'] is None and m['ref'] is None:
            continue
        f = m['fmt']
        mv = f.format(m['mix']) if m['mix'] is not None else 'n/a'
        rv = f.format(m['ref']) if m['ref'] is not None else 'n/a'
        dv = (('+' if m['diff'] >= 0 else '') + f.format(m['diff'])) if m['diff'] is not None else ''
        lines.append(f"    {m['label']:<30} {mv:>8} | {rv:>8} | {dv:>7} {m['unit']}" + (f"  ({m['note']})" if m.get('note') else ''))
    if cmp['suggestions']:
        lines.append(f"  suggestions ({len(cmp['suggestions'])}, most important first):")
        for s in cmp['suggestions']:
            lines.append(f"    {s['priority']}. {s['text']}")
    else:
        lines.append('  no significant differences: the mix matches the reference within the tolerances')
    lines.append(f"  json      {json_path}")
    if png:
        lines.append(f"  image     {png}  (LOOK at it)")
    return lines
