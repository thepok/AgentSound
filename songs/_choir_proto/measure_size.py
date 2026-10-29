"""Stage 3 measure: the acoustic cues of ENSEMBLE SIZE, on one held "ah" per pitch - the new pack's section sample
against the old sampled choir (the SSO chorus recordings behind sampled/choir_mixed / choir_male) at the same note.

    python songs/_choir_proto/measure_size.py [--variant section|big] [--json out.json]

Cues (sustain window, after the attack):
  spread_ct      the instantaneous pitch spread across singers: the width (cents sd) of the harmonics 1.2-5 kHz in short
                 93 ms frames, the window's own width removed (one voice ~0-3; a big section 8-20)
  longterm_ct    the same over the whole sustain (+ vibrato and drift)
  env_fluct_db   how much each harmonic's level wanders (sd dB, the 0.5 s trend removed): the beating of the voices
  env_rate_hz    the centroid of those fluctuations' modulation spectrum (1-30 Hz): fast, noisy beating = many voices
  env_corr       the mean correlation of the harmonics' level tracks (one voice: they move together)
  onset_ms       the 10 -> 90 % rise of the note's level (singers entering one by one smear it)
  hnr_db         harmonic-to-noise ratio below 5 kHz; hf_noise_db: the energy over 5 kHz against the total
  formant_db     the prominence of the formants (sd of the smooth envelope 300-3500 Hz: a crowd blurs them)
  iacc           the L/R correlation (1 = mono); side_db: side against mid energy
  decay_db_s     the release decay slope after the note (a dry take: fast; a room: the hall's RT)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import choir_audio as A  # noqa: E402

SR = 44100
SSO = Path(r'D:\Repos\AgentSound\assets\samples\sso\Sonatina Symphonic Orchestra\Samples\Chorus')
NAMES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
# (part, midi) pairs on the new pack's grid that the SSO chorus also has (female G4-C6, male G2-F4)
PAIRS = [('S', 69), ('S', 72), ('S', 75), ('S', 78), ('A', 68), ('A', 71), ('A', 74),
         ('T', 48), ('T', 51), ('T', 54), ('T', 57), ('T', 60), ('B', 43), ('B', 46), ('B', 49), ('B', 52),
         ('B', 55), ('B', 58), ('B', 61), ('B', 64)]


def sso_path(part: str, midi: int) -> Path:
    g = 'female' if part in 'SA' else 'male'
    return SSO / f'chorus-{g}-{NAMES[midi % 12]}{midi // 12 - 1}.wav'


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def window(x: np.ndarray) -> tuple[int, int, int, int]:
    """-> (onset, sustain start, sustain end, note end) in samples, from the 10 ms level."""
    m = A.mono(x)
    k = int(0.01 * SR)
    env = np.sqrt(np.convolve(m ** 2, np.ones(k) / k, 'same') + 1e-20)
    db = 20 * np.log10(env + 1e-12)
    pk = np.percentile(db, 99)
    on = int(np.argmax(db > pk - 30))
    sus = np.median(db[on + int(0.8 * SR): on + int(3.0 * SR)])
    above = np.where(db > sus - 6)[0]
    end = int(above[-1]) if above.size else m.size
    return on, on + int(0.8 * SR), max(on + int(1.6 * SR), end - int(0.5 * SR)), end


def _spread(m: np.ndarray, f0: float, n: int) -> float:
    """Median over frames and harmonics (1.2-5 kHz) of the cents sd of the power around each harmonic, the
    frame's own f0 refined from the strongest harmonics; the Hann window's own width subtracted in quadrature."""
    hop = n // 4
    w = np.hanning(n)
    f = np.fft.rfftfreq(n, 1 / SR)
    ks = [k for k in range(1, 60) if 1200 <= k * f0 <= 5000]
    if not ks:
        ks = [k for k in range(1, 8) if k * f0 <= 5000]
    # the window's own spread: a steady sine at each harmonic frequency
    t = np.arange(n) / SR
    own = {}
    for k in ks:
        F = np.abs(np.fft.rfft(np.sin(2 * np.pi * k * f0 * t) * w)) ** 2
        own[k] = _cents_sd(F, f, k * f0)
    vals = []
    for i in range(0, m.size - n, hop):
        F = np.abs(np.fft.rfft(m[i:i + n] * w)) ** 2
        if F.sum() < 1e-10:
            continue
        # refine f0: the power-weighted centre of harmonics 1-4
        c = []
        for k in range(1, 5):
            b = np.abs(f - k * f0) < 0.04 * k * f0
            if F[b].sum() > 0:
                c.append((F[b] * f[b]).sum() / F[b].sum() / k)
        g = float(np.median(c)) if c else f0
        for k in ks:
            s = _cents_sd(F, f, k * g)
            vals.append(np.sqrt(max(s ** 2 - own[k] ** 2, 0.0)))
    return float(np.median(vals)) if vals else 0.0


def _cents_sd(F, f, c, half_ct: float = 45.0) -> float:
    b = (f > c * 2 ** (-half_ct / 1200)) & (f < c * 2 ** (half_ct / 1200))
    p = F[b]
    if p.sum() <= 0:
        return 0.0
    ct = 1200 * np.log2(f[b] / c)
    mu = (p * ct).sum() / p.sum()
    return float(np.sqrt((p * (ct - mu) ** 2).sum() / p.sum()))


def _envelopes(m: np.ndarray, f0: float):
    n, hop = 4096, 256
    if f0 < 120:
        n = 8192
    F = A.stft(m, n, hop)
    f = np.fft.rfftfreq(n, 1 / SR)
    rate = SR / hop
    ks = [k for k in range(1, 40) if k * f0 <= 4000][:16]
    tracks = []
    for k in ks:
        b = np.abs(f - k * f0) <= 0.03 * k * f0 + 3
        e = 10 * np.log10(F[:, b].sum(axis=1) + 1e-20)
        L = max(3, int(0.5 * rate))
        trend = np.convolve(e, np.ones(L) / L, 'same')
        d = (e - trend)[L:-L]
        if d.size > 10:
            tracks.append(d)
    if not tracks:
        return 0.0, 0.0, 0.0
    T = np.array(tracks)
    fl = float(np.median(T.std(axis=1)))
    C = np.corrcoef(T)
    iu = np.triu_indices(len(T), 1)
    cr = float(np.nanmean(C[iu])) if iu[0].size else 1.0
    M = np.abs(np.fft.rfft(T * np.hanning(T.shape[1]), axis=1)) ** 2
    fm = np.fft.rfftfreq(T.shape[1], 1 / rate)
    b = (fm >= 1) & (fm <= 30)
    P = M[:, b].mean(axis=0)
    rc = float((P * fm[b]).sum() / (P.sum() + 1e-20))
    return fl, rc, cr


def cues(x: np.ndarray, midi: float) -> dict:
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    on, a, b, end = window(x)
    m = A.mono(x)
    seg = m[a:b]
    f0 = hz(midi)
    k = int(0.01 * SR)
    env = np.sqrt(np.convolve(m ** 2, np.ones(k) / k, 'same') + 1e-20)
    sus = np.median(env[a:b])
    i10 = on + int(np.argmax(env[on:] > 0.1 * sus))
    i90 = on + int(np.argmax(env[on:] > 0.9 * sus))
    fl, rc, cr = _envelopes(seg, f0)
    fr, envd = A.envelope(seg)
    band = (fr >= 300) & (fr <= 3500)
    P = A.stft(seg).mean(axis=0)
    fq = np.fft.rfftfreq(4096, 1 / SR)
    hf = 10 * np.log10(P[fq > 5000].sum() / (P.sum() + 1e-20) + 1e-20)
    L, R = x[a:b, 0], x[a:b, 1]
    iacc = float(np.dot(L, R) / (np.sqrt(np.dot(L, L) * np.dot(R, R)) + 1e-20))
    mid, side = (L + R) / 2, (L - R) / 2
    tail = 20 * np.log10(env[end:] / (sus + 1e-20) + 1e-12)
    i6 = np.argmax(tail < -8)
    i26 = np.argmax(tail < -28)
    dec = float(-20.0 / ((i26 - i6) / SR)) if i26 > i6 else float('nan')
    return {'spread_ct': round(_spread(seg, f0, 4096), 1), 'longterm_ct': round(_spread(seg, f0, 65536), 1)
            if seg.size > 65536 else None,
            'env_fluct_db': round(fl, 2), 'env_rate_hz': round(rc, 1), 'env_corr': round(cr, 3),
            'onset_ms': round((i90 - i10) / SR * 1000, 0), 'hnr_db': round(A.hnr_db(seg, f0), 1),
            'hf_noise_db': round(float(hf), 1), 'formant_db': round(float(envd[band].std()), 2),
            'iacc': round(iacc, 3), 'side_db': round(float(10 * np.log10(np.mean(side ** 2) / (np.mean(mid ** 2)
                                                                                                + 1e-20))), 1),
            'decay_db_s': round(dec, 0)}


KEYS = ['spread_ct', 'longterm_ct', 'env_fluct_db', 'env_rate_hz', 'env_corr', 'onset_ms', 'hnr_db', 'hf_noise_db',
        'formant_db', 'iacc', 'side_db', 'decay_db_s']


def summary(rows: list) -> dict:
    out = {}
    for g in ('SA', 'TB'):
        rs = [r for r in rows if r['part'] in g]
        if not rs:
            continue
        out[g] = {}
        for k in KEYS:
            for src in ('new', 'old'):
                v = [r[src][k] for r in rs if r[src].get(k) is not None and np.isfinite(r[src][k])]
                if v:
                    out[g].setdefault(k, {})[src] = round(float(np.median(v)), 2)
    return out


def bass_table(vowel: str = 'ah') -> list:
    """HNR (<5 kHz / <1 kHz: the low harmonics) per bass grid note: one take, the stage-1 section, the big section
    without / with the old choir's bottom, and the SSO men's chorus."""
    import choir as C
    rows = []
    a, b = int(0.7 * SR), int(6.0 * SR)
    for m in (40, 43, 46, 49, 52, 55):
        f0 = hz(m)
        r = {'midi': m, 'note': C.note_name(m)}
        srcs = {'take': C.layer_path('B', vowel, 'mf', m, 0),
                'stage1': C.PACK / 'samples' / 'section' / 'B' / f'B_{vowel}_mf_{C.note_name(m)}.wav',
                'big_nobass': C.PACK / 'samples' / 'big_nobass' / 'B' / f'B_{vowel}_mf_{C.note_name(m)}.wav',
                'big': C.PACK / 'samples' / 'big' / 'B' / f'B_{vowel}_mf_{C.note_name(m)}.wav',
                'sso': sso_path('B', m)}
        for k, p in srcs.items():
            if p.is_file():
                x = A.mono(A.read_wav(p)[0])[a:b]
                r[k] = (round(A.hnr_db(x, f0), 1), round(A.hnr_db(x, f0, fmax=1000.0), 1))
        rows.append(r)
        print(f"B {r['note']:4} " + '  '.join(f"{k} {r[k][0]}/{r[k][1]}" for k in srcs if k in r))
    return rows


def phasing() -> dict:
    """The comb-filter measure (choir_audio.comb_ripple_db, dry mono layers before the room) per part on the
    stage-1 measure notes (every 3rd grid note, "ah" / "oo", mf): the real stage-1 section (N_OLD takes), one take x
    N_OLD (the copies, with the section's onsets), the clones (N_OLD x CLONES) and the real big section (N_BIG)."""
    import choir as C
    out = {}
    a, b = int((C.PRE_S + 0.4) * SR), int((C.PRE_S + C.NOTE_S - 0.6) * SR)
    for part in 'SATB':
        res = {'real': [], 'copies': [], 'clones': [], 'big': []}
        for m in C.PARTS[part]['notes'][1::3]:
            for v in ('ah', 'oo'):
                nb = C.N_BIG[part]
                if not all(C.layer_path(part, v, 'mf', m, i).is_file() for i in range(nb)):
                    continue
                def lay(i):
                    x = A.mono(A.read_wav(C.layer_path(part, v, 'mf', m, i))[0])
                    return x * 10 ** ((-20.0 - A.rms_db(x[a:b])) / 20)
                real = [lay(i) for i in range(C.N_OLD[part])]
                sgs = C.singers(part, C.N_OLD[part])
                cop = [np.concatenate([np.zeros(int(sg.onset_ms / 1000 * SR)), real[0]]) for sg in sgs]
                big = [lay(i) for i in range(nb)]
                cl = C.clone_layers(part, v, 'mf', m)
                for k, L in (('real', real), ('copies', cop), ('clones', cl), ('big', big)):
                    n = min(x.size for x in L)
                    res[k].append(A.comb_ripple_db([x[:n] for x in L]))
        if res['real']:
            out[part] = {k: {'ripple_db': round(float(np.mean([r['ripple_db'] for r in v])), 2),
                             'notch_db': round(float(np.mean([r['notch_db'] for r in v])), 2)} for k, v in res.items()}
            print(part, '  '.join(f"{k} {d['ripple_db']} / {d['notch_db']}" for k, d in out[part].items()))
    return out


def main(argv) -> int:
    import choir as C
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', default='section')
    ap.add_argument('--vowel', default='ah')
    ap.add_argument('--json', default='')
    ap.add_argument('--phasing', action='store_true', help='comb ripple / notch: real, copies, clones, big')
    ap.add_argument('--bass', action='store_true', help='the bass HNR table (<5 kHz / <1 kHz) instead')
    a = ap.parse_args(argv[1:])
    if a.phasing:
        r = phasing()
        if a.json:
            Path(a.json).write_text(json.dumps(r, indent=1), encoding='utf-8')
        return 0
    if a.bass:
        rows = bass_table(a.vowel)
        if a.json:
            Path(a.json).write_text(json.dumps(rows, indent=1), encoding='utf-8')
        return 0
    rows = []
    for part, m in PAIRS:
        new = C.PACK / 'samples' / a.variant / part / f'{part}_{a.vowel}_mf_{C.note_name(m)}.wav'
        old = sso_path(part, m)
        if not (new.is_file() and old.is_file()):
            continue
        r = {'part': part, 'midi': m, 'new': cues(A.read_wav(new)[0], m), 'old': cues(A.read_wav(old)[0], m)}
        rows.append(r)
        print(f"{part} {C.note_name(m):4} " + ' '.join(f"{k}={r['new'][k]}/{r['old'][k]}" for k in KEYS[:7]))
    s = summary(rows)
    print(f"\nmedians new / old ({a.variant}, {a.vowel} mf):")
    for g, d in s.items():
        print(f"  {g}: " + '; '.join(f"{k} {v.get('new')} / {v.get('old')}" for k, v in d.items()))
    if a.json:
        Path(a.json).write_text(json.dumps({'rows': rows, 'summary': s}, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
