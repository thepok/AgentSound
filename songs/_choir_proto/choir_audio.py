"""Small numpy audio helpers for the neural-choir prototype (wav io, STFT, measures, a PNG spectrogram writer).

Prototype code: numpy only (no scipy / matplotlib in the main Python)."""
from __future__ import annotations

import struct
import wave
import zlib
from pathlib import Path

import numpy as np

SR = 44100


def read_wav(path) -> tuple[np.ndarray, int]:
    """-> (float64 array [n] or [n, ch], sample rate). 16 / 24 / 32-bit PCM."""
    with wave.open(str(path), 'rb') as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, '<i2').astype(np.float64) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(np.float64) / float(1 << 23)
    elif sw == 4:
        x = np.frombuffer(raw, '<i4').astype(np.float64) / float(1 << 31)
    else:
        raise ValueError(f"{path}: {sw * 8}-bit wav")
    if ch > 1:
        x = x.reshape(-1, ch)
    return x, sr


def write_wav(path, x: np.ndarray, sr: int = SR, bits: int = 24) -> None:
    """Write mono [n] or stereo [n, 2] float audio (clipped to +-1) as 16 / 24-bit PCM."""
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = x[:, None]
    y = np.clip(x, -1.0, 1.0)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if bits == 16:
        data = (y * 32767.0).round().astype('<i2').tobytes()
    else:
        v = (y * 8388607.0).round().astype(np.int32).reshape(-1)
        b = np.empty((v.size, 3), np.uint8)
        b[:, 0] = v & 0xFF
        b[:, 1] = (v >> 8) & 0xFF
        b[:, 2] = (v >> 16) & 0xFF
        data = b.tobytes()
    tmp = str(path) + '.part'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(2 if bits == 16 else 3)
        w.setframerate(sr)
        w.writeframes(data)
    Path(tmp).replace(path)


def mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1) if x.ndim > 1 else x


def stft(x: np.ndarray, n: int = 4096, hop: int = 1024) -> np.ndarray:
    """|STFT| power [frames, bins] (Hann)."""
    x = mono(x)
    if x.size < n:
        x = np.pad(x, (0, n - x.size))
    w = np.hanning(n)
    frames = 1 + (x.size - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    return np.abs(np.fft.rfft(x[idx] * w, axis=1)) ** 2


def rms_db(x: np.ndarray) -> float:
    x = mono(x)
    return float(10 * np.log10(np.mean(x ** 2) + 1e-20))


def centroid_hz(x: np.ndarray, sr: int = SR) -> float:
    P = stft(x).mean(axis=0)
    f = np.fft.rfftfreq(4096, 1 / sr)
    return float((P * f).sum() / (P.sum() + 1e-20))


def envelope(x: np.ndarray, sr: int = SR, lifter: int = 40) -> tuple[np.ndarray, np.ndarray]:
    """The long-term spectral envelope (cepstrally smoothed log power, dB) -> (freqs, dB): formant positions."""
    P = stft(x).mean(axis=0) + 1e-20
    c = np.fft.irfft(np.log(P))
    c[lifter:-lifter] = 0.0
    env = np.fft.rfft(c).real * 10 / np.log(10)
    return np.fft.rfftfreq(4096, 1 / sr), env


def f0_track(x: np.ndarray, sr: int = SR, lo: float = 60.0, hi: float = 1200.0, hop: int = 512) -> np.ndarray:
    """A plain autocorrelation f0 track (Hz per hop; 0 = unvoiced) - good enough for drift / vibrato on sustains."""
    x = mono(x)
    n = 2048
    out = []
    for i in range(0, x.size - n, hop):
        fr = x[i:i + n] * np.hanning(n)
        if np.sqrt(np.mean(fr ** 2)) < 1e-3:
            out.append(0.0)
            continue
        ac = np.fft.irfft(np.abs(np.fft.rfft(fr, 2 * n)) ** 2)[:n]
        a, b = int(sr / hi), int(sr / lo)
        k = a + int(np.argmax(ac[a:b]))
        if ac[k] < 0.3 * ac[0]:
            out.append(0.0)
            continue
        if 0 < k < n - 1:                          # parabolic interpolation
            y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
            k = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-20)
        out.append(sr / k)
    return np.array(out)


def hnr_db(x: np.ndarray, f0: float, sr: int = SR, fmax: float = 5000.0) -> float:
    """Harmonic-to-noise ratio of a sustained note at a known f0 (dB): the long-term power at the harmonics against
    the power between them (8192-point frames: a breathy / noisy render scores low)."""
    x = mono(x)
    n = 8192
    P = None
    for i in range(0, x.size - n, n // 2):
        F = np.abs(np.fft.rfft(x[i:i + n] * np.hanning(n))) ** 2
        P = F if P is None else P + F
    if P is None:
        return 0.0
    f = np.fft.rfftfreq(n, 1 / sr)
    df = f[1]
    h, m = 0.0, 0.0
    k = 1
    while k * f0 < fmax:
        c = k * f0
        hb = np.abs(f - c) <= max(2 * df, 0.03 * f0)
        mb = np.abs(f - c - f0 / 2) <= max(2 * df, 0.1 * f0)
        h += P[hb].sum()
        m += P[mb].mean() * hb.sum() if mb.any() else 0.0
        k += 1
    return float(10 * np.log10((h + 1e-20) / (m + 1e-20)))


def comb_ripple_db(layers: list, sr: int = SR, f_lo: float = 200.0, f_hi: float = 8000.0) -> dict:
    """The phasing / comb-filter measure of a section made of `layers` (mono, same length):
    ratio R(f, t) = |sum X_i|^2 / sum |X_i|^2 per STFT bin. Independent voices: R ~ 1 on average with Rayleigh
    scatter that averages out over time; correlated copies (one take x N with small delays): R swings between ~0
    (notches) and N (peaks) at FIXED frequencies - a comb that does not average out.
    -> {'ripple_db': std over 200-8000 Hz of the time-averaged 10*log10(R) (a comb: large; a real section: small),
        'notch_db': the 1st percentile of the time-averaged R in dB (deep fixed notches), 'gain_db': mean R in dB
        (0 = power-sum, +10*log10(N) = coherent)}"""
    L = [mono(x) for x in layers]
    m = min(x.size for x in L)
    S = None
    P = None
    for x in L:
        X = np.fft.rfft(_frames(x[:m]), axis=1)
        S = X if S is None else S + X
        P = np.abs(X) ** 2 if P is None else P + np.abs(X) ** 2
    act = P.sum(axis=1) > 1e-8 * P.sum(axis=1).max()           # voiced frames only
    R = (np.abs(S[act]) ** 2).mean(axis=0) / (P[act].mean(axis=0) + 1e-20)
    f = np.fft.rfftfreq(4096, 1 / sr)
    band = (f >= f_lo) & (f <= f_hi)
    rd = 10 * np.log10(R[band] + 1e-12)
    return {'ripple_db': round(float(rd.std()), 2), 'notch_db': round(float(np.percentile(rd, 1)), 2),
            'gain_db': round(float(10 * np.log10(R[band].mean())), 2)}


def _frames(x, n=4096, hop=1024):
    if x.size < n:
        x = np.pad(x, (0, n - x.size))
    frames = 1 + (x.size - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(frames)[:, None]
    return x[idx] * np.hanning(n)


def corr(a: np.ndarray, b: np.ndarray, max_lag: int = 1500) -> float:
    """The largest normalised cross-correlation of two signals within +-max_lag samples (~34 ms)."""
    a, b = mono(a), mono(b)
    m = min(a.size, b.size)
    a, b = a[:m] - a[:m].mean(), b[:m] - b[:m].mean()
    n = 1 << int(np.ceil(np.log2(2 * m)))
    c = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    c = np.concatenate([c[-max_lag:], c[:max_lag + 1]])
    return float(np.max(np.abs(c)) / (np.sqrt((a ** 2).sum() * (b ** 2).sum()) + 1e-20))


def spectrogram_png(x: np.ndarray, path, sr: int = SR, fmax: float = 8000.0, height: int = 300,
                    width: int | None = None, db_range: float = 80.0) -> None:
    """A grey-scale log-power spectrogram PNG (time left->right, frequency up to fmax, linear)."""
    P = stft(x, 2048, 256)
    f = np.fft.rfftfreq(2048, 1 / sr)
    P = P[:, f <= fmax]
    D = 10 * np.log10(P + 1e-20)
    D = np.clip((D - (D.max() - db_range)) / db_range, 0, 1)
    img = D.T[::-1]
    # resample to height x width
    h, w = img.shape
    W = width or min(1600, w)
    yi = (np.arange(height) * h / height).astype(int)
    xi = (np.arange(W) * w / W).astype(int)
    img = (255 * (1 - img[yi][:, xi])).astype(np.uint8)
    write_png(path, img)


def write_png(path, img: np.ndarray) -> None:
    """A grey-scale uint8 [h, w] PNG."""
    h, w = img.shape
    raw = b''.join(b'\x00' + img[i].tobytes() for i in range(h))

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png)
