"""Stage 4 of the choir prototype: a choir pack from REAL singers - VocalSet (Wilkins, Seetharaman, Wahl, Pardo,
ISMIR 2018; Zenodo 10.5281/zenodo.1442513, CC BY 4.0): 20 professional singers (9 female, 11 male), long tones on
the five vowels a e i o u in straight / pp / forte / messa di voce, plus scales / arpeggios (straight, slow piano /
forte).

    python -I songs/_choir_proto/vocalset.py inventory     # segment + pitch-detect every candidate take
    python -I songs/_choir_proto/vocalset.py package       # cut, pitch-correct, place, sum -> the pack
    python -I songs/_choir_proto/vocalset.py measure       # the stage-3 size cues: vocalset / big / old

The dataset (untrusted, read as wav only): D:/Repos/AgentSound/local/choir/vocalset/FULL/<singer>/<context>/<tech>/
<id>_<context>_<tech>_<vowel>.wav. The pack: local/choir/vocalset_pack (SFZ per part / vowel, samples/, SOURCE.json,
ATTRIBUTION.txt, INDEX.json); work files (the cut takes per singer): local/choir/vocalset_work.

Every section sample is the SUM of real different singers (each its own take, cut from its own recording, shifted by
at most MAX_SHIFT semitones, level-matched and seated in stage 3's hall, room.py): the ensemble size comes from real
people, not from processing. A take's sustain is extended WSOLA-style from its own stable middle (chunks from random
places, joined pitch-synchronously: no fixed loop); its attack and (for long tones) release stay as sung.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import choir as C  # noqa: E402
import choir_audio as A  # noqa: E402

SR = 44100
LOCAL = C.ROOT
DATA = LOCAL / 'vocalset' / 'FULL'
PACK = LOCAL / 'vocalset_pack'
WORK = LOCAL / 'vocalset_work'
INV = WORK / 'inventory.json'

VOICE = {'f1': 'soprano', 'f2': 'soprano', 'f3': 'soprano', 'f4': 'soprano', 'f5': 'mezzo-soprano',
         'f6': 'soprano', 'f7': 'soprano', 'f8': 'mezzo-soprano', 'f9': 'soprano',
         'm1': 'baritone', 'm2': 'tenor', 'm3': 'tenor', 'm4': 'bass(?)', 'm5': 'baritone', 'm6': 'baritone',
         'm7': 'tenor(?)', 'm8': 'bass', 'm9': 'countertenor', 'm10': 'bass-baritone', 'm11': 'tenor'}
"""The voice types from the dataset's readme-anon.txt."""
VOWEL = {'a': 'ah', 'e': 'eh', 'i': 'ee', 'o': 'oh', 'u': 'oo'}
TECH = {'straight': 'mf', 'pp': 'p', 'forte': 'f', 'messa': 'messa'}
"""The long-tone techniques used and the dynamic layer they feed (messa di voce: its soft start -> p, its peak -> f,
by level; vibrato / breathy / belt / trills are not a choir's sound)."""
SOURCES = [('long_tones', t) for t in TECH] + [(c, t) for c in ('scales', 'arpeggios')
                                               for t in ('straight', 'slow_piano', 'slow_forte')]
"""The long tones are sung on three pitches only (C, c, f: females ~C4 / C5 / F5, males ~C3 / C4 / F4, each singer
in their own tuning); the scales / arpeggios (C and F major, 0.3-1.1 s notes) fill the pitches between."""
TECH_DYN = {'straight': 'mf', 'pp': 'p', 'forte': 'f', 'messa': 'messa', 'slow_piano': 'p', 'slow_forte': 'f'}
MIN_SEG_S = {'long_tones': 1.2, 'scales': 0.3, 'arpeggios': 0.3}

# --- pitch: YIN ----------------------------------------------------------------------------------------------
HOPY = 256
WY = 1024


def yin(x: np.ndarray, fmin: float = 70.0, fmax: float = 1100.0, thr: float = 0.15):
    """YIN (de Cheveigne & Kawahara 2002): the cumulative-mean-normalised difference over a 1024-sample window,
    lags up to SR / fmin -> (f0 Hz [frames] with 0 = unvoiced, aperiodicity [frames], rms dB [frames])."""
    x = np.asarray(x, np.float64)
    tmax = int(SR / fmin)
    tmin = int(SR / fmax)
    L = WY + tmax
    nfr = max(0, (x.size - L) // HOPY)
    f0 = np.zeros(nfr)
    ap = np.ones(nfr)
    rms = np.full(nfr, -120.0)
    nfft = 1 << int(np.ceil(np.log2(L + WY)))
    for b0 in range(0, nfr, 256):
        idx = np.arange(b0, min(nfr, b0 + 256))
        fr = x[idx[:, None] * HOPY + np.arange(L)[None, :]]
        a = fr[:, :WY]
        r = np.fft.irfft(np.conj(np.fft.rfft(a, nfft)) * np.fft.rfft(fr, nfft), nfft)[:, :tmax + 1]
        cs = np.concatenate([np.zeros((fr.shape[0], 1)), np.cumsum(fr ** 2, axis=1)], axis=1)
        e0 = cs[:, WY:WY + 1]
        et = cs[:, WY:WY + tmax + 1] - cs[:, :tmax + 1]
        d = e0 + et - 2 * r
        d[:, 0] = 0
        cm = np.cumsum(d[:, 1:], axis=1) / np.arange(1, tmax + 1)
        dn = np.ones_like(d)
        dn[:, 1:] = d[:, 1:] / (cm + 1e-20)
        rms[idx] = 10 * np.log10(e0[:, 0] / WY + 1e-20)
        seg = dn[:, tmin:tmax]
        below = seg < thr
        has = below.any(axis=1)
        k0 = np.where(has, np.argmax(below, axis=1), np.argmin(seg, axis=1))
        # the local minimum after the first dip under the threshold (within a quarter of the lag)
        span = np.arange(seg.shape[1])[None, :]
        win = (span >= k0[:, None]) & (span <= (k0 + k0 // 4 + 2)[:, None])
        kk = np.where(has, np.argmin(np.where(win, seg, np.inf), axis=1), k0)
        rows = np.arange(seg.shape[0])
        v = seg[rows, kk]
        kf = (kk + tmin).astype(np.float64)
        ok = (kk + tmin >= 1) & (kk + tmin < dn.shape[1] - 1)
        kc = np.clip(kk + tmin, 1, dn.shape[1] - 2)
        y0, y1, y2 = dn[rows, kc - 1], dn[rows, kc], dn[rows, kc + 1]
        kf = np.where(ok, kc + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-20), kf)
        ap[idx] = v
        f0[idx] = np.where(v < 0.35, SR / kf, 0.0)
    return f0, ap, rms


def midi_of(f: np.ndarray) -> np.ndarray:
    return np.where(f > 0, 69 + 12 * np.log2(np.maximum(f, 1e-9) / 440.0), np.nan)


def smooth(m: np.ndarray, k: int) -> np.ndarray:
    """A running median of +-k frames through the voiced (finite) frames."""
    p = np.pad(m, k, constant_values=np.nan)
    w = np.lib.stride_tricks.sliding_window_view(p, 2 * k + 1)
    with np.errstate(all='ignore'):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return np.nanmedian(w, axis=1)


def segments(x: np.ndarray, min_s: float = MIN_SEG_S) -> list[dict]:
    """Stable sustained notes: voiced frames (aperiodicity < 0.25, level > the take's 95th pct - 30 dB) whose
    (median-smoothed) pitch stays within +-0.6 semitone of a running centre for >= min_s.
    -> [{on, off (s), midi (median), sd_ct, wobble_ct, rms_db, ap}]"""
    f0, ap, rms = yin(x)
    m = midi_of(f0)
    top = np.percentile(rms, 95)
    ok = (f0 > 0) & (ap < 0.25) & (rms > top - 30)
    ms = smooth(m, 7)
    slow = smooth(m, 24)                            # +-140 ms: through a 5-6 Hz vibrato
    out = []
    i = 0
    n = m.size
    while i < n:
        if not ok[i]:
            i += 1
            continue
        c = slow[i] if np.isfinite(slow[i]) else ms[i]
        j = i
        k = i + 1
        while k < n:
            if ok[k] and abs(slow[k] - c) < 0.6:
                c = 0.98 * c + 0.02 * slow[k]
                j = k
            elif k - j > 6:                          # a dropout of > 35 ms ends the note
                break
            k += 1
        dur = (j - i + 1) * HOPY / SR
        if dur >= min_s:
            v = m[i:j + 1]
            v = v[np.isfinite(v)]
            med = float(np.median(v))
            # the slow wander (0.3 s smoothing) vs the total: straight tones wobble little
            out.append({'on': round(i * HOPY / SR, 3), 'off': round((j + 1) * HOPY / SR + WY / SR, 3),
                        'midi': round(med, 3), 'sd_ct': round(float(np.std(v) * 100), 1),
                        'rms_db': round(float(np.median(rms[i:j + 1])), 1),
                        'ap': round(float(np.median(ap[i:j + 1])), 3)})
        i = j + 1
    return out


def take_files():
    for sdir in sorted(DATA.iterdir()):
        sid = ('f' if sdir.name.startswith('female') else 'm') + sdir.name.lstrip('femal')
        for ctx, tech in SOURCES:
            d = sdir / ctx / tech
            if not d.is_dir():
                continue
            for p in sorted(d.glob('*.wav')):
                v = p.stem.rsplit('_', 1)[-1]
                if v in VOWEL:
                    yield sid, ctx, tech, VOWEL[v], p


def cmd_inventory() -> dict:
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    t = time.time()
    for sid, ctx, tech, vowel, p in take_files():
        x, sr = A.read_wav(p)
        assert sr == SR, p
        x = A.mono(x)
        for s in segments(x, MIN_SEG_S[ctx]):
            rows.append({'singer': sid, 'ctx': ctx, 'tech': tech, 'vowel': vowel, 'file': str(p.relative_to(DATA)),
                         **s})
    inv = {'rows': rows, 'seconds': round(time.time() - t)}
    INV.write_text(json.dumps(inv, indent=0), encoding='utf-8')
    summarise(inv)
    return inv


def summarise(inv: dict) -> None:
    rows = inv['rows']
    print(f"{len(rows)} stable segments ({inv['seconds']} s)")
    for sid in VOICE:
        rs = [r for r in rows if r['singer'] == sid]
        lt = [r for r in rs if r['ctx'] == 'long_tones']
        if not rs:
            print(f"{sid}: none")
            continue
        ms = [r['midi'] for r in rs]
        lts = sorted({round(r['midi']) for r in lt})
        by = {t: len([r for r in lt if r['tech'] == t]) for t in TECH}
        dur = np.median([r['off'] - r['on'] for r in lt]) if lt else 0
        print(f"{sid:3} {VOICE[sid]:14} all {C.note_name(round(min(ms)))}-{C.note_name(round(max(ms)))}; long tones "
              f"{[C.note_name(k) for k in lts]} {by} med {dur:.1f} s; scale/arp segs "
              f"{len(rs) - len(lt)}")


# --- the pack ---------------------------------------------------------------------------------------------------
FEMALE = [f'f{i}' for i in range(1, 10)]
MALE = [f'm{i}' for i in range(1, 12) if i != 9]
PARTS = {
    # pool: every singer who may sing the part (the dataset has 9 women and 11 men: S and A share the women, T and
    # B the men - each part takes ALL who cover a note; the countertenor sings alto, as in an English choir)
    'S': dict(pool=FEMALE, notes=list(range(60, 79, 2)), lo=59, hi=80),
    'A': dict(pool=FEMALE + ['m9'], notes=list(range(58, 77, 2)), lo=57, hi=77),
    'T': dict(pool=MALE, notes=list(range(48, 67, 2)), lo=47, hi=68),
    'B': dict(pool=MALE, notes=list(range(46, 65, 2)), lo=45, hi=65),
}
"""The grids (whole tones: the sampler repitches <= 1 semitone between them) and the playable range per part, from the
inventory: the women sing B3..G5 (long tones ~C4 / C5 / F5, scales between), the men Bb2 (C3 - 2) .. G4 (long tones
~C3 / C4 / F4) - so S C4-G#5 (SATB C4-A5: no A5), A A3-F5 (SATB G3-E5: no G3-G#3), T B2-G#4 (SATB C3-A4: no A4),
B A2-F4 (SATB E2-E4: NOTHING under A2 - no singer of the set sustains a vowel below C3)."""
VOWELS_PACK = ('ah', 'oh', 'oo', 'ee', 'eh')
DYNS = ('p', 'mf', 'f')
MAX_SHIFT = 2.0
SCALE_TOL = 1.2
"""A long tone may be shifted up to MAX_SHIFT semitones to its grid note; a scale / arpeggio note (no natural
release, short) only SCALE_TOL - the long tones are preferred."""
MIN_SINGERS = 3
SUS_S = 6.2             # the sustain built per singer (s): stage 3 held 6.6
PRE_S = 0.10
LEVEL_DB = {'p': -25.0, 'mf': -19.5, 'f': -15.5}
TILT_DB = 0.15
NFFT = 1 << 19


def candidates(inv: list, part: str, vowel: str, dyn: str, midi: int) -> dict:
    """{singer: [segment rows, best first]} within reach of `midi` (long tones +-MAX_SHIFT, scale notes
    +-SCALE_TOL), the dynamic's own techniques; ranked: long tone first, then the smaller shift, the longer note."""
    out: dict = {}
    for r in inv:
        if r['singer'] not in PARTS[part]['pool'] or r['vowel'] != vowel or TECH_DYN[r['tech']] != dyn:
            continue
        lt = r['ctx'] == 'long_tones'
        if abs(r['midi'] - midi) > (MAX_SHIFT if lt else SCALE_TOL):
            continue
        out.setdefault(r['singer'], []).append(r)
    for rs in out.values():
        rs.sort(key=lambda r: (r['ctx'] != 'long_tones', round(abs(r['midi'] - midi) * 2) / 2,
                               -(r['off'] - r['on'])))
    return out


_CACHE: dict = {}


def load(rel: str) -> np.ndarray:
    if rel not in _CACHE:
        if len(_CACHE) > 64:
            _CACHE.clear()
        _CACHE[rel] = A.mono(A.read_wav(DATA / rel)[0])
    return _CACHE[rel]


def _best_lag(src: np.ndarray, p0: int, tail: np.ndarray, T: int) -> int:
    """The position near p0 (+-T) whose next len(tail) samples match `tail` best (normalised correlation)."""
    lo, hi = max(0, p0 - T), min(src.size - tail.size - 1, p0 + T)
    if hi <= lo:
        return max(0, min(p0, src.size - tail.size - 1))
    w = src[lo:hi + tail.size]
    c = np.correlate(w, tail, 'valid')
    e = np.convolve(w ** 2, np.ones(tail.size), 'valid')
    return lo + int(np.argmax(c / np.sqrt(e + 1e-12)))


XS = 0.04


def sustain(x: np.ndarray, a: int, b: int, n: int, period: int, rng: random.Random) -> np.ndarray:
    """n samples from x's stable stretch [a, b), WSOLA-style: chunks read from random places of the stretch, each
    joined where its waveform matches the running output (pitch-synchronous, 40 ms crossfade) - no fixed loop; the
    singer's own drift / vibrato / breath noise kept. A short stretch (< 1.5 s: a scale note) also reads chunks
    time-reversed (a steady vowel sounds the same backwards; it halves the repetition)."""
    X = int(XS * SR)
    win = np.hanning(2 * X)
    fi, fo = win[:X], win[X:]
    span = b - a
    short = span < int(1.5 * SR)
    chunk = (0.15, 0.4) if short else (0.3, 0.7)
    xr = x[::-1]
    y = np.zeros(n + 4 * X + int(chunk[1] * SR) + span)
    L0 = min(span, int(rng.uniform(*chunk) * SR) + X)
    y[:L0] = x[a:a + L0]
    w = L0
    last = a + L0
    while w < n + X:
        L = int(rng.uniform(*chunk) * SR)
        L = max(2 * X, min(L, span - 2 * X))
        p0 = a + rng.randrange(0, max(1, span - L - X))
        if span > 3 * L and abs(p0 - last) < L:          # never re-read right where we just were
            p0 = a + (p0 - a + span // 2) % max(1, span - L - X)
        rev = short and rng.random() < 0.45
        src, sa, sb = (xr, x.size - b, x.size - a) if rev else (x, a, b)
        if rev:
            p0 = x.size - (p0 + L + X)
        tail = y[w - X:w]
        p = _best_lag(src, max(sa, p0), tail, int(1.5 * period))
        p = min(max(sa, p), sb - X - 2)
        seg = src[p:min(sb, p + X + L)]
        if seg.size <= X:
            seg = x[a:a + X + L]
        y[w - X:w] = tail * fo + seg[:X] * fi
        k = seg.size - X
        y[w:w + k] = seg[X:]
        w += k
        last = (x.size - p) if rev else p + seg.size
    return y[:n]


def take(r: dict, midi: int, n_sus: int, rng: random.Random, dev_ct: float) -> tuple[np.ndarray, int]:
    """One singer's note: its attack (a long tone or a phrase's first note: from the silence before it, breath and
    all; a legato scale note: a 70 ms fade-in at its stable start), n_sus samples of its own sustain (sustain()),
    its release (a long tone's natural one, else a 0.5 s fade) - pitch-shifted (varispeed, <= MAX_SHIFT) to the
    grid note + the singer's own intonation (dev_ct). -> (mono take, length of the head = the attack)."""
    x = load(r['file'])
    on, off = int(r['on'] * SR), min(x.size - 1, int(r['off'] * SR))
    shift = (midi + dev_ct / 100.0) - r['midi']
    k = int(0.01 * SR)
    lev = 10 * np.log10(np.convolve(x ** 2, np.ones(k) / k, 'same') + 1e-20)
    sus_db = float(np.median(lev[on:off]))
    st = on                                    # attack: back to where the voice is 35 dB down (<= 0.6 s)
    while st > max(0, on - int(0.6 * SR)) and lev[st] > sus_db - 35:
        st -= k // 2
    natural_on = lev[st] <= sus_db - 35
    en = off                                   # release: forward to 40 dB down (<= 1.2 s), only into silence
    while en < min(x.size - 1, off + int(1.2 * SR)) and lev[en] > sus_db - 40:
        en += k // 2
    natural_off = lev[min(en, x.size - 1)] <= sus_db - 40
    lo = max(0, st - int(0.05 * SR))
    hi = min(x.size, (en if natural_off else off) + int(0.05 * SR))
    seg = C.varispeed(x[lo:hi], shift * 100.0, 0.0, 0.1, 0.0)
    q = 2 ** (shift / 12)                      # sample indices / q in the shifted take
    on_s, off_s = int((on - lo) / q), min(seg.size - 1, int((off - lo) / q))
    st_s, en_s = int((st - lo) / q), min(seg.size, int(((en if natural_off else off) - lo) / q))
    period = int(SR / (440 * 2 ** ((midi - 69) / 12)))
    a = on_s + int((0.12 if r['ctx'] == 'long_tones' else 0.04) * SR)
    b = off_s - int((0.15 if r['ctx'] == 'long_tones' else 0.04) * SR)
    X = int(XS * SR)
    if b - a < 6 * X:
        a, b = on_s, off_s
    if natural_on:
        head = seg[max(0, st_s - int(0.04 * SR)):a].copy()
    else:
        head = seg[on_s:a].copy()
        f = min(head.size, int(0.07 * SR))
        head[:f] *= np.sin(np.linspace(0, np.pi / 2, f)) ** 2
    body = sustain(seg, a, b, n_sus, period, rng)
    win = np.hanning(2 * X)
    if natural_off:
        p = _best_lag(seg, max(a, b - X), body[-X:], int(1.5 * period))
        rel = seg[p:en_s].copy()
        if rel.size > 2 * X:
            body[-X:] = body[-X:] * win[X:] + rel[:X] * win[:X]
            rel = rel[X:]
            f = min(rel.size, int(0.1 * SR))
            rel[-f:] *= np.linspace(1, 0, f)
        else:
            natural_off = False
    if not natural_off:
        f = int(0.5 * SR)
        body[-f:] *= np.cos(np.linspace(0, np.pi / 2, f)) ** 1.5
        rel = np.zeros(0)
    return np.concatenate([head, body, rel]), head.size


def section_sample(inv, part, vowel, dyn, midi, *, alt: int = 0, dry: bool = False):
    """The real section's sample: every pool singer who covers the note, one take each (alt: the A / B parts take a
    singer's 2nd-best segment where there is one - a woman singing in S and A at once never sings the SAME take),
    level-matched, a small own gain, a staggered entry (0-35 ms), each on its own seat in the stage-3 hall (room.py:
    direct sound + early reflections + the stage's diffuse field to the ORTF pair + outriggers).
    -> (stereo sample or None, meta); dry: -> [the aligned mono takes before the room] (the comb measure)"""
    import room
    cands = candidates(inv, part, vowel, dyn, midi)
    used_dyn = dyn
    if len(cands) < MIN_SINGERS:                     # borrow the neighbour dynamic (marked in the index)
        for d2 in ('mf', 'p', 'f'):
            c2 = candidates(inv, part, vowel, d2, midi)
            if len(c2) > len(cands):
                cands, used_dyn = c2, d2
                break
    if len(cands) < MIN_SINGERS:
        return None, {}
    pool = PARTS[part]['pool']
    H = room.impulse_spectra(part, len(pool), NFFT)
    n_sus = int(SUS_S * SR)
    used, takes = [], []
    for sid in sorted(cands, key=pool.index):
        rs = cands[sid]
        r = rs[1] if alt and len(rs) > 1 and rs[1]['ctx'] == rs[0]['ctx'] else rs[0]
        rng = random.Random(f'vs-{part}-{vowel}-{dyn}-{midi}-{sid}')
        own = r['midi'] - round(r['midi'])
        dev = max(-15.0, min(15.0, 80.0 * own)) + rng.gauss(0, 5.0)   # most of the singer's own tuning
        y, h = take(r, midi, n_sus, rng, dev)
        sl = slice(h + int(0.3 * SR), h + n_sus - int(0.4 * SR))
        y = y * 10 ** ((-20.0 - A.rms_db(y[sl]) + rng.uniform(-1.2, 1.0)) / 20)
        takes.append((sid, y, h, rng.uniform(0.0, 0.035)))
        used.append({'singer': sid, 'file': r['file'], 'tech': r['tech'], 'ctx': r['ctx'],
                     'src_midi': r['midi'], 'shift_st': round(midi + dev / 100 - r['midi'], 2)})
    H0 = max(h for _, _, h, _ in takes)                # every singer's stable start at the same time + its stagger
    if dry:
        L = [np.concatenate([np.zeros(H0 - h + int(lag * SR)), y]) for _, y, h, lag in takes]
        n = min(x.size for x in L)
        return [x[:n] for x in L]
    acc = np.zeros((2, NFFT // 2 + 1), np.complex128)
    m = 0
    for sid, y, h, lag in takes:
        y = np.concatenate([np.zeros(int(PRE_S * SR) + H0 - h + int(lag * SR)), y])[:NFFT - SR]
        m = max(m, y.size)
        acc += np.fft.rfft(y, NFFT)[None, :] * H[pool.index(sid)]
    out = np.stack([np.fft.irfft(acc[0], NFFT), np.fft.irfft(acc[1], NFFT)], axis=1)[:m + int(0.3 * SR)]
    env = np.abs(A.mono(out))
    first = int(np.argmax(env > 1e-3 * env.max()))
    cut = max(0, first - int(PRE_S * SR))
    out = out[cut:]
    P = PARTS[part]
    centre = sum(P['notes']) / len(P['notes'])
    s0 = max(0, int(PRE_S * SR) + H0 - cut)
    sl = slice(s0 + int(0.4 * SR), s0 + int((SUS_S - 0.6) * SR))
    g = LEVEL_DB[dyn] + TILT_DB * (midi - centre) - A.rms_db(out[sl])
    out = out * 10 ** (g / 20)
    f = int(0.04 * SR)
    out[-f:] *= np.linspace(1, 0, f)[:, None]
    meta = {'singers': used, 'n': len(used), 'dyn_source': used_dyn, 'sustain_s': round(s0 / SR, 3),
            'peak': round(float(np.abs(out).max()), 3)}
    return out, meta


def write_sfz(part: str, vowel: str, files: dict) -> Path:
    """One .sfz per part / vowel (C.write_sfz's layout): keys split half way between the grid notes, the dynamics
    as CC1 crossfades (default CC1 = 80: mf), velocity -> level (amp_veltrack 35)."""
    P = PARTS[part]
    notes = sorted({m for (d, m) in files})
    dyns = [d for d in DYNS if any(k[0] == d for k in files)]
    xf = C.XF[len(dyns)]
    lines = [f'// AgentSound vocalset-choir: {part} "{vowel}" - real singers of VocalSet (CC BY 4.0, ATTRIBUTION.txt)',
             '<control>', 'set_cc1=80',
             '<global>', 'amp_veltrack=35', 'ampeg_attack=0.004', 'ampeg_release=0.55', 'loop_mode=no_loop']
    for d in dyns:
        xin, xout = xf[d]
        g = ['<group>']
        if xin:
            g += [f'xfin_locc1={xin[0]}', f'xfin_hicc1={xin[1]}']
        if xout:
            g += [f'xfout_locc1={xout[0]}', f'xfout_hicc1={xout[1]}']
        lines.append(' '.join(g))
        for i, m in enumerate(notes):
            lo = P['lo'] if i == 0 else (notes[i - 1] + m) // 2 + 1
            hi = P['hi'] if i == len(notes) - 1 else (m + notes[i + 1]) // 2
            lines.append(f'<region> sample={files[(d, m)]} lokey={lo} hikey={hi} pitch_keycenter={m} '
                         f'offset={int((PRE_S - 0.02) * SR)}')
    path = PACK / f'{part}_{vowel}.sfz'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def cmd_package(parts, vowels) -> None:
    inv = json.loads(INV.read_text(encoding='utf-8'))['rows']
    PACK.mkdir(parents=True, exist_ok=True)
    idx_path = WORK / 'pack_index.json'
    index = json.loads(idx_path.read_text(encoding='utf-8')) if idx_path.is_file() else {}
    t0 = time.time()
    for part in parts:
        for v in vowels:
            files = {}
            for d in DYNS:
                for m in PARTS[part]['notes']:
                    y, meta = section_sample(inv, part, v, d, m, alt=1 if part in 'AB' else 0)
                    if y is None:
                        continue
                    rel = f'samples/{part}/{part}_{v}_{d}_{C.note_name(m)}.wav'
                    A.write_wav(PACK / rel, y, bits=16)
                    files[(d, m)] = rel
                    index[f'{part}_{v}_{d}_{m}'] = meta
            notes = sorted({m for (_, m) in files})
            for d in DYNS:                       # a (dyn, note) without its own: the nearest dynamic's sample
                for m in notes:
                    if (d, m) not in files:
                        for d2 in ('mf', 'p', 'f'):
                            if (d2, m) in files:
                                files[(d, m)] = files[(d2, m)]
                                break
            if files:
                write_sfz(part, v, files)
                ns = [index[f'{part}_{v}_{d}_{m}']['n'] for (d, m) in files if f'{part}_{v}_{d}_{m}' in index]
                print(f"{part} {v}: {len(files)} regions, singers per sample {min(ns)}-{max(ns)} "
                      f"(median {int(np.median(ns))}) [{time.time() - t0:.0f} s]", flush=True)
            idx_path.write_text(json.dumps(index, indent=0), encoding='utf-8')


# --- measure: the stage-3 size cues, vocalset vs the stage-3 big pack vs the old sampled choir -----------------
def low_share_db(x: np.ndarray, a: int, b: int, fc: float = 250.0) -> float:
    m = A.mono(x)[a:b]
    P = np.abs(np.fft.rfft(m * np.hanning(m.size))) ** 2
    f = np.fft.rfftfreq(m.size, 1 / SR)
    return round(float(10 * np.log10(P[f < fc].sum() / (P.sum() + 1e-20) + 1e-20)), 1)


def vs_sample(part: str, vowel: str, dyn: str, midi: int) -> np.ndarray | None:
    """The vocalset pack's sample for `midi` as the sampler plays it: the nearest grid note, repitched (<= 1 st)."""
    g = min(PARTS[part]['notes'], key=lambda k: abs(k - midi))
    if abs(g - midi) > 1:
        return None
    f = PACK / 'samples' / part / f'{part}_{vowel}_{dyn}_{C.note_name(g)}.wav'
    if not f.is_file():
        return None
    x = A.read_wav(f)[0]
    if g != midi:
        x = np.stack([C.varispeed(x[:, c], 100.0 * (midi - g), 0.0, 0.1, 0.0) for c in (0, 1)], axis=1)
    return x


def cmd_measure(vowel: str = 'ah') -> dict:
    import measure_size as M
    rows = []
    for part, m in M.PAIRS:
        src = {'vocalset': vs_sample(part, vowel, 'mf', m)}
        fb = C.PACK / 'samples' / 'big' / part / f'{part}_{vowel}_mf_{C.note_name(m)}.wav'
        src['big'] = A.read_wav(fb)[0] if fb.is_file() else None
        so = M.sso_path(part, m)
        src['old'] = A.read_wav(so)[0] if so.is_file() else None
        if any(v is None for v in src.values()):
            continue
        r = {'part': part, 'midi': m}
        for k, x in src.items():
            c = M.cues(x, m)
            on, a, b, end = M.window(x if x.ndim > 1 else np.stack([x, x], 1))
            c['low_db'] = low_share_db(x, a, b)
            c['centroid_hz'] = round(A.centroid_hz(A.mono(x)[a:b]), 0)
            r[k] = c
        rows.append(r)
    keys = M.KEYS + ['low_db', 'centroid_hz']
    summ = {}
    for g in ('SA', 'TB'):
        rs = [r for r in rows if r['part'] in g]
        summ[g] = {k: {s: round(float(np.median([r[s][k] for r in rs if r[s].get(k) is not None
                                                   and np.isfinite(r[s][k])])), 2)
                       for s in ('vocalset', 'big', 'old')} for k in keys}
    # the comb measure on the dry layers (before the room): vocalset takes vs the stage-3 big section's takes
    inv = json.loads(INV.read_text(encoding='utf-8'))['rows']
    comb = {}
    for part in 'SATB':
        vs, bg = [], []
        for m in PARTS[part]['notes'][1::3]:
            for v in ('ah', 'oo'):
                L = section_sample(inv, part, v, 'mf', m, alt=1 if part in 'AB' else 0, dry=True)
                if L:
                    vs.append(A.comb_ripple_db(L))
        a, b = int((C.PRE_S + 0.4) * SR), int((C.PRE_S + C.NOTE_S - 0.6) * SR)
        for m in C.PARTS[part]['notes'][1::3]:
            for v in ('ah', 'oo'):
                nb = C.N_BIG[part]
                if not all(C.layer_path(part, v, 'mf', m, i).is_file() for i in range(nb)):
                    continue
                L = []
                for i in range(nb):
                    x = A.mono(A.read_wav(C.layer_path(part, v, 'mf', m, i))[0])
                    L.append(x * 10 ** ((-20.0 - A.rms_db(x[a:b])) / 20))
                n = min(x.size for x in L)
                bg.append(A.comb_ripple_db([x[:n] for x in L]))
        comb[part] = {k: {'ripple_db': round(float(np.mean([r['ripple_db'] for r in L])), 2),
                          'notch_db': round(float(np.mean([r['notch_db'] for r in L])), 2)} if L else None
                      for k, L in (('vocalset', vs), ('big', bg))}
    out = {'rows': rows, 'summary': summ, 'comb': comb}
    (WORK / 'measure.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(f"medians over {len(rows)} notes ({vowel} mf) vocalset / big / old:")
    for g, d in summ.items():
        print(f"  {g}: " + '; '.join(f"{k} {v['vocalset']}/{v['big']}/{v['old']}" for k, v in d.items()))
    print("comb ripple / 1% notch (dry layers):")
    for part, d in comb.items():
        print(f"  {part}: " + '  '.join(f"{k} {v['ripple_db']}/{v['notch_db']}" for k, v in d.items() if v))
    return out


# --- licence ----------------------------------------------------------------------------------------------------
ATTRIBUTION = ('Wilkins, J., Prem Seetharaman, Alison Wahl, & Bryan Pardo. (2018). VocalSet: A Singing Voice Dataset '
               '(Version 1.2) [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.1442513')
"""Zenodo's own citation of the record (APA export, checked 2026-10-24); licence on the record: CC BY 4.0."""
PAPER = ('J. Wilkins, P. Seetharaman, A. Wahl, B. Pardo: "VocalSet: A Singing Voice Dataset", Proceedings of the 19th '
         'International Society for Music Information Retrieval Conference (ISMIR), Paris, 2018.')


def cmd_source() -> None:
    from agentsound import catalog
    index = json.loads((WORK / 'pack_index.json').read_text(encoding='utf-8'))
    per = {p: sorted({u['singer'] for k, m in index.items() if k.startswith(p + '_') for u in m['singers']},
                     key=lambda x: (x[0], int(x[1:]))) for p in PARTS}
    used = sorted({x for v in per.values() for x in v}, key=lambda x: (x[0], int(x[1:])))
    src = {
        'id': 'vocalset-choir',
        'title': 'AgentSound vocalset-choir: an SATB vowel choir built from the real singers of VocalSet',
        'url': 'https://zenodo.org/records/1442513', 'homepage': 'https://doi.org/10.5281/zenodo.1442513',
        'license': 'CC-BY-4.0', 'licenseUrl': 'https://creativecommons.org/licenses/by/4.0/',
        'attribution': ATTRIBUTION,
        'paper': PAPER,
        'source_file': {'name': 'VocalSet11.zip', 'md5': '0c09396242f946e7111ad7d8fc649b81', 'bytes': 2077243579},
        'singers': {p: [f'{x} ({VOICE[x]})' for x in v] for p, v in per.items()},
        'singers_used': used,
        'changes': ('Derived work: segments of the VocalSet long tones / scales / arpeggios (straight, pp, forte, slow '
                    'piano / forte; vowels a e i o u) cut, pitch-shifted by at most 2 semitones, their sustains '
                    'extended from their own audio, level-matched, placed in a simulated hall and summed per note '
                    'into section samples (one real singer per take).'),
        'restrictions': ('CC BY 4.0: may be shared, redistributed and published (also commercially) WITH the '
                         'attribution above and a note that the samples were changed. Unlike the DiffSinger choir '
                         'packs (local only) this pack MAY be published with attribution.'),
        'generated_by': 'songs/_choir_proto/vocalset.py',
    }
    (PACK / 'SOURCE.json').write_text(json.dumps(src, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    txt = [
        'AgentSound vocalset-choir - ATTRIBUTION / LICENCE', '',
        'The samples of this pack are derived from VocalSet, licensed under the Creative Commons Attribution 4.0',
        'International licence (CC BY 4.0, https://creativecommons.org/licenses/by/4.0/):', '',
        '  ' + ATTRIBUTION, '', 'Paper: ' + PAPER, '',
        'Changes: ' + src['changes'], '',
        'Singers used (anonymous ids and voice types of the dataset\'s readme-anon.txt):',
        *[f'  {p}: ' + ', '.join(v) for p, v in src['singers'].items()], '',
        'Anything published with this pack (the pack itself or music made with it) should credit:',
        '  "Choir samples derived from VocalSet (Wilkins, Seetharaman, Wahl, Pardo 2018), CC BY 4.0,',
        '   https://doi.org/10.5281/zenodo.1442513"', '',
        'No endorsement by the VocalSet authors is implied. The CC BY 4.0 licence text: see the URL above.', '']
    (PACK / 'ATTRIBUTION.txt').write_text('\n'.join(txt), encoding='utf-8')
    catalog.pack_index(PACK, rebuild=True)
    print(f"{PACK / 'SOURCE.json'}; singers used {len(used)}: {per}")


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['inventory', 'summary', 'package', 'measure', 'source'])
    ap.add_argument('--parts', default='S,A,T,B')
    ap.add_argument('--vowels', default=','.join(VOWELS_PACK))
    a = ap.parse_args(argv[1:])
    if a.cmd == 'package':
        cmd_package(a.parts.split(','), a.vowels.split(','))
    elif a.cmd == 'source':
        cmd_source()
    elif a.cmd == 'measure':
        cmd_measure()
    elif a.cmd == 'inventory':
        cmd_inventory()
    elif a.cmd == 'summary':
        summarise(json.loads(INV.read_text(encoding='utf-8')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
