"""Offline fast-level-swing diagnostic, not a musical-quality gate.

Requires numpy/scipy and ffmpeg already installed. 400 ms BS.1770 K-weighted
windows, 100 ms hops. A reversing swing needs a >=3 dB rise AND fall, each
0.5..2 s from its peak. Quiet tails and one-way fades are excluded. Attacks,
rests and written accents can still qualify: use stems / the score / matched
feature-off renders to attribute a candidate before calling it gain riding.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks, sosfilt


def k_weighting(sr):
    """BS.1770 shelf + RLB; same coefficients as engine/analysis/Loudness.cpp."""
    k = np.tan(np.pi * 1681.974450955533 / sr)
    q = 0.7071752369554196
    vh = 10 ** (3.999843853973347 / 20)
    vb = vh ** 0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf = [(vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0,
             (vh - vb * k / q + k * k) / a0, 1, 2 * (k * k - 1) / a0,
             (1 - k / q + k * k) / a0]
    k = np.tan(np.pi * 38.13547087602444 / sr)
    q = 0.5003270373238773
    a0 = 1 + k / q + k * k
    return np.array([shelf, [1, -2, 1, 1, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]])


def momentary(path):
    """Decode in bounded chunks at 48 kHz, retaining only 100 ms energy bins."""
    exe = shutil.which('ffmpeg')
    if exe is None:
        raise RuntimeError('ffmpeg is required (no automatic installation)')
    sr, hop = 48000, 4800
    bins, pending = [], b''
    sos, state = k_weighting(sr), np.zeros((2, 2, 2))
    # stderr goes to a temporary file, so neither pipe can deadlock on errors.
    import tempfile
    with tempfile.TemporaryFile() as err:
        with subprocess.Popen([exe, '-v', 'error', '-i', str(path), '-f', 'f32le', '-ar', str(sr),
                               '-ac', '2', '-'], stdout=subprocess.PIPE, stderr=err) as proc:
            while True:
                chunk = proc.stdout.read(hop * 8 - len(pending))
                if not chunk:
                    break
                pending += chunk
                if len(pending) < hop * 8:
                    continue
                x = np.frombuffer(pending, dtype='<f4').reshape(-1, 2).astype(float)
                y, state = sosfilt(sos, x, axis=0, zi=state)
                bins.append(float(np.mean(np.sum(y * y, axis=1))))
                pending = b''
            code = proc.wait()
            if code:
                err.seek(0)
                raise RuntimeError(err.read().decode(errors='replace').strip())
    if len(bins) < 4:
        return np.array([]), np.array([])
    energy = np.convolve(bins, np.ones(4) / 4, mode='valid')
    return np.arange(len(energy)) * 0.1 + 0.2, -0.691 + 10 * np.log10(np.maximum(energy, 1e-15))


def measure(times, db):
    """Return candidates and a 1-second change distribution; timestamps are window centres."""
    times, db = np.asarray(times), np.asarray(db)
    if len(times) != len(db) or not np.all(np.isfinite(db)):
        raise ValueError('matching finite time / level arrays required')
    if len(times) > 1 and not np.allclose(np.diff(times), 0.1):
        raise ValueError('expected 100 ms hops')
    result = dict(windowSec=0.4, hopSec=0.1, thresholdDb=3.0, flankSec=[0.5, 2.0],
                  candidateCount=0, candidatesPerMinute=0.0, p95Change1sDb=0.0, maxChange1sDb=0.0,
                  candidates=[], interpretation='Candidates only: note attacks, rests and written dynamics must '
                  'be checked before attribution to gain riding.')
    if len(db) < 41:
        return result
    floor = max(-50.0, float(np.percentile(db, 90)) - 30)
    peaks, _ = find_peaks(db, prominence=3, distance=5)
    for p in peaks:
        if p < 20 or p >= len(db) - 20:
            continue
        left = p - 20 + int(np.argmin(db[p - 20:p - 4]))
        right = p + 5 + int(np.argmin(db[p + 5:p + 21]))
        depth = float(min(db[p] - db[left], db[p] - db[right]))
        if depth >= 3 and min(db[left], db[right]) > floor:
            result['candidates'].append(dict(atSec=round(float(times[p]), 2),
                startSec=round(float(times[left]), 2), endSec=round(float(times[right]), 2),
                swingDb=round(depth, 2), peakLufs=round(float(db[p]), 2)))
    result['candidates'].sort(key=lambda e: (-e['swingDb'], e['atSec']))
    result['candidateCount'] = len(result['candidates'])
    duration = times[-1] + 0.2 - (times[0] - 0.2)
    result['candidatesPerMinute'] = round(result['candidateCount'] * 60 / duration, 2)
    active = (db[:-10] > -45) & (db[10:] > -45)
    delta = abs(db[10:] - db[:-10])[active]
    if len(delta):
        result['p95Change1sDb'] = round(float(np.percentile(delta, 95)), 2)
        result['maxChange1sDb'] = round(float(max(delta)), 2)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('audio', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--report', type=Path, help='also add pumping to an existing analysis report (no verdict changes)')
    args = ap.parse_args()
    result = measure(*momentary(args.audio))
    result['audio'] = str(args.audio.resolve())
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if args.report:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        report['pumping'] = result
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'candidates'}))


if __name__ == '__main__':
    main()
