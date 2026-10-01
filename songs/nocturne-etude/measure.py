"""Measure the etude against the reference recording (analysis only; needs numpy and ffmpeg for the .opus).

    python songs/nocturne-etude/measure.py [--mix out/mix.wav] [--ref REF.opus] [--json out/measure.json]

Both files go through the SAME detectors (no stems, no score data for the render side), so the numbers compare
like with like:
  tempo      seconds per bar from the bar downbeats (the reference: hand-marked from melody / bass onsets,
             REF_BARS; the render: its tempo map), the curve's spread and its correlation with the reference
  sync       melody vs left hand at the downbeats: onset of the high band (600-4000 Hz) minus the low band
             (40-220 Hz) near each bar line, ms (positive = the melody sounds after the bass)
  figures    onsets inside the fioriture / trills / the cadenza windows: notes per second, IOI evenness (CV), how
             much slower the ends are than the middle
  dynamics   melody onset levels (the new energy of the top note) per two-bar phrase: 10-90 % spread, dB
  loudness   short-term level per bar (RMS, dB): the arc's range and its correlation with the reference
  brightness spectral centroid of the loudest melody attacks (first 60 ms) vs their sustain
  pitch      chroma agreement per bar (cosine of the 12-bin chroma, 110 Hz-2 kHz) - the transcription check
"""
import argparse
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REF = 'D:/Repos/AgentSound/assets/refrences/Chopin - Nocturne op.9 No.2 [9E6b3swbnWg].opus'

# downbeats of the reference (s): pickup, bars 1..34, the final chord
REF_BARS = [2.22, 3.56, 11.10, 17.82, 23.99, 31.88, 38.97, 45.62, 52.11, 59.91, 67.11, 72.58, 81.11, 89.25, 97.03,
            103.75, 110.59, 118.96, 125.87, 131.18, 139.68, 149.41, 156.50, 163.73, 170.83, 180.0, 187.4, 194.27,
            201.0, 208.62, 217.16, 225.0, 232.1, 250.55, 257.27, 262.75]

# figure windows in bars + eighths (bar, from_eighth, to_eighth): what to time in both performances
FIGURES = {'m4 cadence 16ths': (4, 3, 6), 'm6 appoggiatura chain': (6, 2, 5), 'm7 trill': (7, 0, 3),
           'm16 fioritura': (16, 2, 4.5), 'm24 fioritura': (24, 2, 5.4), 'm32 cadenza cycle': (32, 4.5, 9)}

SR = 22050


def load(path):
    if not path.lower().endswith('.wav'):
        tmp = os.path.join(HERE, 'out', '_ref22.wav')
        if not os.path.exists(tmp):
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', path, '-ac', '1', '-ar',
                            str(SR), tmp], check=True)
        path = tmp
    with wave.open(path, 'rb') as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float32) / (1 << 23)
    else:
        x = np.frombuffer(raw, dtype=np.float32)
    x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:                                            # plain linear resampling is enough for analysis
        t = np.arange(0, len(x) / sr, 1 / SR)
        x = np.interp(t, np.arange(len(x)) / sr, x).astype(np.float32)
    return x


def render_bars():
    """Downbeats (s) of the render from its render JSON (tempo map), same layout as REF_BARS."""
    sys.path.insert(0, os.path.join(HERE, '..', '..'))
    from agentsound.tempo import render_seconds
    with open(os.path.join(HERE, 'out', 'song.render.json'), encoding='utf-8') as f:
        r = json.load(f)
    beats = [0.0] + [0.5 + 6.0 * k for k in range(0, 34)] + [0.5 + 33 * 6.0 + 4.75]
    return [render_seconds(r, b) for b in beats]


def stft(x, n=2048, hop=128):
    win = np.hanning(n).astype(np.float32)
    frames = 1 + (len(x) - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    return np.abs(np.fft.rfft(x[idx] * win, axis=1)), hop / SR


def band_flux(S, f, lo, hi):
    sel = (f >= lo) & (f < hi)
    L = np.log1p(200 * S[:, sel])
    fl = np.maximum(0, np.diff(L, axis=0)).sum(axis=1)
    return np.concatenate([[0], fl])


def peaks(fl, dt, thr=1.5, min_gap=0.03):
    k = 25
    med = np.array([np.median(fl[max(0, i - k):i + k]) for i in range(len(fl))])
    out = []
    for i in range(1, len(fl) - 1):
        if fl[i] > fl[i - 1] and fl[i] >= fl[i + 1] and fl[i] > med[i] * thr + 0.5:
            if not out or (i - out[-1]) * dt > min_gap:
                out.append(i)
    return np.array(out) * dt


class Audio:
    def __init__(self, x):
        self.x = x
        self.S, self.dt = stft(x)
        self.f = np.fft.rfftfreq(2048, 1 / SR)
        off = 1024 / SR
        self.lo = band_flux(self.S, self.f, 40, 220)
        self.hi = band_flux(self.S, self.f, 600, 4000)
        self.all = band_flux(self.S, self.f, 200, 5000)
        self.on_lo = peaks(self.lo, self.dt) + off
        self.on_hi = peaks(self.hi, self.dt) + off
        self.on_all = peaks(self.all, self.dt, thr=1.3, min_gap=0.025) + off
        sel = (self.f >= 1000) & (self.f < 5000)
        mel = np.concatenate([[0], np.maximum(0, np.diff(self.S[:, sel], axis=0)).sum(axis=1)])
        self.on_mel = peaks(mel, self.dt, thr=2.0) + off


def nearest(on, t, w):
    c = on[(on > t - w) & (on < t + w)]
    return None if len(c) == 0 else c[np.argmin(np.abs(c - t))]


def sync(a: Audio, bars):
    """Melody minus bass onset (ms) at the bar lines: the bass onset nearest the downbeat (+-250 ms), then the
    melody-band onset nearest that bass (+-150 ms). Melody band: 1-5 kHz on linear magnitude (the top voice
    dominates it; the bass's partials there are weak)."""
    out = []
    for t in bars[1:-1]:
        tl = nearest(a.on_lo, t, 0.25)
        if tl is None:
            continue
        th = nearest(a.on_mel, tl, 0.15)
        if th is not None:
            out.append(1000 * (th - tl))
    v = np.array(out)
    return {'n': len(v), 'mean_ms': round(float(v.mean()), 1), 'median_ms': round(float(np.median(v)), 1),
            'std_ms': round(float(v.std()), 1), 'mean_abs_ms': round(float(np.abs(v).mean()), 1),
            'melody_late_share': round(float((v > 10).mean()), 2)} if len(v) else {'n': 0}


def figure_timing(a: Audio, bars, fig):
    k, e0, e1 = fig
    t0 = bars[k] + (bars[k + 1] - bars[k]) * e0 / 12
    t1 = bars[k] + (bars[k + 1] - bars[k]) * e1 / 12
    on = a.on_all[(a.on_all >= t0 - 0.05) & (a.on_all <= t1 + 0.05)]
    if len(on) < 4:
        return {'notes': int(len(on))}
    ioi = np.diff(on)
    n = len(ioi)
    mid = ioi[n // 3: max(n // 3 + 1, 2 * n // 3)]
    ends = np.concatenate([ioi[:max(1, n // 4)], ioi[-max(1, n // 4):]])
    return {'onsets': int(len(on)), 'rate': round(float(n / (on[-1] - on[0])), 2),
            'cv': round(float(ioi.std() / ioi.mean()), 3), 'ends_vs_middle': round(float(ends.mean() / mid.mean()), 2),
            'fastest_ms': round(float(1000 * ioi.min()), 1)}


def _amp(D, f, m):
    f0 = 440 * 2 ** ((m - 69) / 12)
    a = np.searchsorted(f, f0 * 2 ** (-0.4 / 12)); b = np.searchsorted(f, f0 * 2 ** (0.4 / 12)) + 1
    return float(D[a:b].max()) if b > a else 0.0


def onset_notes(a: Audio, bars):
    """Every onset (all bands) classified by its highest new note (fundamental present, octave / 12th ghosts
    rejected): (time, bar, top midi, level dB of that note's new energy)."""
    out = []
    n = 8192
    f = np.fft.rfftfreq(n, 1 / SR)
    win = np.hanning(n)
    for t in a.on_all:
        i0 = int((t + 0.03) * SR); j0 = int((t - 0.2) * SR)
        if j0 < 0 or i0 + n // 2 >= len(a.x):
            continue
        now = np.abs(np.fft.rfft(np.pad(a.x[i0:i0 + n // 2], (0, n // 2)) * win))
        bef = np.abs(np.fft.rfft(np.pad(a.x[j0:j0 + n // 2], (0, n // 2)) * win))
        D = np.maximum(0, now - bef)
        A = {m: _amp(D, f, m) for m in range(40, 100)}
        mx = max(A.values()) or 1.0
        top = None
        for m in range(96, 54, -1):
            v = A[m]
            if v < 0.2 * mx:
                continue
            if A.get(m - 12, 0) > v or A.get(m - 19, 0) > 1.6 * v or A.get(m - 24, 0) > 2 * v:
                continue
            if A.get(m - 1, 0) > v or A.get(m + 1, 0) > v:
                continue
            top = m
            break
        if top is None:
            continue
        b = int(np.searchsorted(bars, t) - 1)
        out.append((float(t), b, top, 20 * math.log10(A[top] + 1e-9)))
    return out


def melody_levels(notes):
    return [(b, db) for t, b, m, db in notes if m >= 68]


def voicing(notes):
    """Median level of the melody attacks (top note >= Ab4) minus that of the left-hand chord strikes (top note
    G3..G4, no melody note in the onset), dB."""
    mel = [db for t, b, m, db in notes if m >= 68]
    lh = [db for t, b, m, db in notes if 55 <= m <= 67]
    if len(mel) < 10 or len(lh) < 10:
        return None
    return round(float(np.median(mel) - np.median(lh)), 1)


def phrase_dynamics(levels):
    spreads = []
    for p in range(1, 35, 2):
        v = np.array([db for b, db in levels if p <= b < p + 2])
        if len(v) >= 6:
            spreads.append(float(np.percentile(v, 90) - np.percentile(v, 10)))
    return {'phrases': len(spreads), 'median_spread_db': round(float(np.median(spreads)), 2) if spreads else None}


def bar_loudness(x, bars):
    out = []
    for a, b in zip(bars[1:-1], bars[2:]):
        seg = x[int(a * SR):int(b * SR)]
        out.append(10 * math.log10(float(np.mean(seg ** 2)) + 1e-12))
    return np.array(out)


def brightness(a: Audio, levels_on):
    """Centroid (Hz) of the attack (first 60 ms) of the loudest 20 % melody onsets, and of their sustain."""
    cents_a, cents_s = [], []
    sel = (a.f > 80) & (a.f < 8000)
    ff = a.f[sel]
    ons = sorted(levels_on, key=lambda p: -p[1])[:max(5, len(levels_on) // 5)]
    for t, _ in ons:
        i = int(t / a.dt)
        if i + 20 >= len(a.S):
            continue
        att = a.S[i:i + 10, sel].mean(axis=0)
        sus = a.S[i + 12:i + 20, sel].mean(axis=0)
        cents_a.append(float((att * ff).sum() / (att.sum() + 1e-9)))
        cents_s.append(float((sus * ff).sum() / (sus.sum() + 1e-9)))
    return {'attack_centroid_hz': round(float(np.median(cents_a))), 'sustain_centroid_hz': round(float(np.median(cents_s))),
            'attack_vs_sustain': round(float(np.median(cents_a) / np.median(cents_s)), 3)}


def score_downbeats():
    """The melody's pitch class on each bar line (bars 1..34) from the song's score, None where no note starts."""
    import importlib.util
    sys.path.insert(0, os.path.join(HERE, '..', '..'))
    from agentsound.theory import note
    spec = importlib.util.spec_from_file_location('nocturne_song', os.path.join(HERE, 'song.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = []
    for k in range(1, 35):
        t0 = m.bar_start(k)
        ev = next((e for e in m.SCORE[k] if abs(e[1] - t0) < 1e-6 and e[0] in ('note', 'trill', 'turn', 'fig')), None)
        if ev is None:
            out.append(None)
            continue
        p = ev[3][0] if ev[0] == 'fig' else ev[3]
        out.append(note(p) % 12)
    return out


def melody_share(x, bars, pcs):
    """Chroma share (energy) of the melody's pitch class in the first eighth after each bar line: how much the
    singing note stands over the harmony under it (same notes in both performances)."""
    n = 4096
    f = np.fft.rfftfreq(n, 1 / SR)
    sel = (f > 100) & (f < 2500)
    pc = np.round(69 + 12 * np.log2(f[sel] / 440)).astype(int) % 12
    out = []
    for k, q in enumerate(pcs, start=1):
        if q is None:
            continue
        a = bars[k] + 0.04
        e8 = (bars[k + 1] - bars[k]) / 12
        seg = x[int(a * SR):int((a + max(0.25, e8)) * SR)]
        c = np.zeros(12)
        for s0 in range(0, max(1, len(seg) - n + 1), 512):
            fr = seg[s0:s0 + n]
            fr = np.pad(fr, (0, n - len(fr)))
            X = np.abs(np.fft.rfft(fr * np.hanning(n)))[sel]
            np.add.at(c, pc, X ** 2)
        out.append(float(c[q] / (c.sum() + 1e-12)))
    return round(float(np.median(out)), 3)


def chroma_bars(x, bars):
    n, hop = 8192, 2048
    f = np.fft.rfftfreq(n, 1 / SR)
    sel = (f > 110) & (f < 2000)
    pcs = np.round(69 + 12 * np.log2(f[sel] / 440)).astype(int) % 12
    out = []
    for a, b in zip(bars[1:-1], bars[2:]):
        seg = x[int(a * SR):int(b * SR)]
        c = np.zeros(12)
        for s in range(0, max(1, len(seg) - n), hop):
            X = np.abs(np.fft.rfft(seg[s:s + n] * np.hanning(n)))[sel]
            np.add.at(c, pcs, X ** 2)
        out.append(c / (np.linalg.norm(c) + 1e-12))
    return np.array(out)


def measure(mix, ref, bars_mix):
    A, R = Audio(mix), Audio(ref)
    res = {}
    dm = np.diff(bars_mix[1:-1])
    dr = np.diff(REF_BARS[1:-1])
    res['tempo'] = {'mix_sec_per_bar': [round(float(v), 2) for v in dm], 'ref_sec_per_bar': [round(float(v), 2) for v in dr],
                    'mix_cv': round(float(dm[:31].std() / dm[:31].mean()), 3),
                    'ref_cv': round(float(dr[:31].std() / dr[:31].mean()), 3),
                    'corr': round(float(np.corrcoef(dm[:31], dr[:31])[0, 1]), 2),
                    'mix_total_s': round(bars_mix[-1] - bars_mix[0], 1), 'ref_total_s': round(REF_BARS[-1] - REF_BARS[0], 1)}
    res['sync'] = {'mix': sync(A, bars_mix), 'ref': sync(R, REF_BARS)}
    res['figures'] = {name: {'mix': figure_timing(A, bars_mix, fg), 'ref': figure_timing(R, REF_BARS, fg)}
                      for name, fg in FIGURES.items()}
    nm, nr = onset_notes(A, bars_mix), onset_notes(R, REF_BARS)
    lm, lr = melody_levels(nm), melody_levels(nr)
    res['dynamics'] = {'mix': phrase_dynamics(lm), 'ref': phrase_dynamics(lr)}
    pcs = score_downbeats()
    res['voicing'] = {'mix_melody_share': melody_share(mix, bars_mix, pcs),
                      'ref_melody_share': melody_share(ref, REF_BARS, pcs)}
    bl_m, bl_r = bar_loudness(mix, bars_mix), bar_loudness(ref, REF_BARS)
    res['loudness'] = {'mix_range_db': round(float(np.percentile(bl_m, 95) - np.percentile(bl_m, 5)), 1),
                       'ref_range_db': round(float(np.percentile(bl_r, 95) - np.percentile(bl_r, 5)), 1),
                       'corr': round(float(np.corrcoef(bl_m, bl_r)[0, 1]), 2),
                       'mix_bars_db': [round(float(v - bl_m.max()), 1) for v in bl_m],
                       'ref_bars_db': [round(float(v - bl_r.max()), 1) for v in bl_r]}
    on_m = [(t, db) for t, b, m, db in nm if m >= 68]
    on_r = [(t, db) for t, b, m, db in nr if m >= 68]
    res['brightness'] = {'mix': brightness(A, on_m), 'ref': brightness(R, on_r)}
    cm, cr = chroma_bars(mix, bars_mix), chroma_bars(ref, REF_BARS)
    sim = (cm * cr).sum(axis=1)
    res['pitch'] = {'chroma_cos_mean': round(float(sim.mean()), 3),
                    'worst_bars': [(int(i) + 1, round(float(sim[i]), 2)) for i in np.argsort(sim)[:6]],
                    'per_bar': [round(float(v), 2) for v in sim]}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mix', default=os.path.join(HERE, 'out', 'mix.wav'))
    ap.add_argument('--ref', default=REF)
    ap.add_argument('--json', default=os.path.join(HERE, 'out', 'measure.json'))
    a = ap.parse_args()
    res = measure(load(a.mix), load(a.ref), render_bars())
    with open(a.json, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    t = res['tempo']
    print(f"tempo     s/bar cv mix {t['mix_cv']} ref {t['ref_cv']}  corr {t['corr']}  total {t['mix_total_s']} / {t['ref_total_s']} s")
    print(f"sync      mix {res['sync']['mix']}\n          ref {res['sync']['ref']}")
    for k, v in res['figures'].items():
        print(f"figure    {k:24s} mix {v['mix']}\n          {'':24s} ref {v['ref']}")
    print(f"dynamics  mix {res['dynamics']['mix']}  ref {res['dynamics']['ref']}")
    print(f"voicing   melody pitch-class share at the bar lines: mix {res['voicing']['mix_melody_share']}  "
          f"ref {res['voicing']['ref_melody_share']}")
    lo = res['loudness']
    print(f"loudness  bar range mix {lo['mix_range_db']} dB ref {lo['ref_range_db']} dB, arc corr {lo['corr']}")
    print(f"bright    mix {res['brightness']['mix']}\n          ref {res['brightness']['ref']}")
    print(f"pitch     chroma cos mean {res['pitch']['chroma_cos_mean']}, worst bars {res['pitch']['worst_bars']}")


if __name__ == '__main__':
    main()
