"""Stage 3: every virtual singer gets a PLACE - a seat on the choir risers of one shared hall, heard by a near-coincident
cardioid pair in front of the choir (ORTF). Per singer and mic: the direct sound (its own delay, 1/r level, air damping, the
voice's directivity) and the early reflections of the stage shell, side walls, floor and ceiling (image sources up to
2nd order, each wall bounce darker). The late reverb stays the song's shared hall.

Why (measure_size.py, stage 1 vs the SSO chorus at the same notes): the stage-1 section samples were nearly mono
(IACC 0.94-0.96 against the recorded choir's 0.0-0.16), dry (release decay 128-165 dB/s against 51-91) and had no
depth (every singer at the same distance) - the strongest cues of "a few people close to the mic".

    H = impulse_spectra(part, n_singers, nfft)    # [n, 2, nfft//2+1] complex: singer -> (L, R)
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np

SR = 44100
C_SOUND = 343.0
W, D, HGT = 24.0, 32.0, 13.0
"""The hall (m): x across the stage, y from the stage shell (y = 0) into the audience, z up."""
MICS = ((12.0 - 0.085, 8.8, 3.7), (12.0 + 0.085, 8.8, 3.7))
_A = math.radians(55.0)
AXES = ((-math.sin(_A), -math.cos(_A), -0.25), (math.sin(_A), -math.cos(_A), -0.25))
"""A near-coincident cardioid pair (ORTF: 17 cm, +-55 deg, tilted down at the choir) 3.7 m high, ~4.5-7 m in front
of the rows (L = smaller x). Measured: an omni A-B pair (30-70 cm) made the soprano / alto sections anti-phase
(IACC -0.15..-0.24, side over mid: their singers share one side, so one inter-mic delay ~ half a period of the
2nd harmonic for them all); ORTF's level differences give the width without that.)"""
REFLECT = {'x0': 0.80, 'x1': 0.80, 'y0': 0.88, 'y1': 0.55, 'z0': 0.62, 'z1': 0.78}
"""Pressure reflection factors: side walls, the stage shell (y0), the audience end (y1, seats), the floor / risers
(z0) and the ceiling."""
WALL_FC = {'x0': 7000.0, 'x1': 7000.0, 'y0': 9000.0, 'y1': 3500.0, 'z0': 4000.0, 'z1': 6000.0}
"""Each bounce's high-frequency damping (a one-pole low-pass corner, Hz)."""
ROWS = {
    # part: (x from, x to, [row y], [riser height]) - S / A in front (S left), T / B behind them, each half the stage
    'S': (5.0, 11.5, (4.4, 3.6), (0.0, 0.25)),
    'A': (12.5, 19.0, (4.4, 3.6), (0.0, 0.25)),
    'T': (5.5, 11.8, (2.8, 2.0), (0.5, 0.75)),
    'B': (12.2, 18.5, (2.8, 2.0), (0.5, 0.75)),
}
TAIL = dict(start_s=0.022, len_s=0.45, rt60_s=1.1, level_db=-11.0, fc=4500.0)
"""The stage's diffuse field after the early reflections (the reflections of 3rd order and up, never one bounce):
exponentially decaying noise of its own per singer and mic (decorrelated L / R), level_db against the direct sound of
a singer at DIRECT_REF_M; the song's hall adds the late reverb."""
MOUTH_Z = 1.55
DIRECT_REF_M = 5.0
"""A singer at this distance from a mic keeps its level (1/r around it)."""


def seats(part: str, n: int, seed: int = 3) -> list[tuple[float, float, float]]:
    """The part's n singers on its rows (front row first, alternating seats), each jittered a little."""
    x0, x1, ys, zs = ROWS[part]
    rng = random.Random(f'seat-{part}-{seed}')
    rows = len(ys)
    per = [n // rows + (1 if r < n % rows else 0) for r in range(rows)]
    out = []
    for r in range(rows):
        k = per[r]
        off = 0.5 if r % 2 else 0.0                    # the back row sits in the gaps
        for i in range(k):
            x = x0 + (x1 - x0) * (i + 0.5 + off * 0.5) / (k + 0.25)
            out.append((x + rng.uniform(-0.12, 0.12), ys[r] + rng.uniform(-0.15, 0.15),
                        MOUTH_Z + zs[r] + rng.uniform(-0.12, 0.10)))
    order = list(range(n))
    rng.shuffle(order)                                   # singer idx -> seat (not sorted by index)
    return [out[o] for o in order]


OUTRIGGERS = ((7.5, 7.8, 3.4), (16.5, 7.8, 3.4))
OUT_GAIN = 0.55
"""Two spaced omni outriggers 9 m apart (mixed -5 dB into L / R): the main pair alone left the low voices' sections
correlated (IACC 0.52 for T / B against the SSO men's ~0: the low end needs spaced mics to decorrelate)."""


def _images(src):
    """Image sources up to 2nd order: (position, [walls hit])."""
    sx, sy, sz = src
    out = []
    for nx in (-1, 0, 1):
        for ny in (-1, 0, 1):
            for nz in (-1, 0, 1):
                if abs(nx) + abs(ny) + abs(nz) > 2:
                    continue
                walls = []
                if nx == -1:
                    x, walls = -sx, walls + ['x0']
                elif nx == 1:
                    x, walls = 2 * W - sx, walls + ['x1']
                else:
                    x = sx
                if ny == -1:
                    y, walls = -sy, walls + ['y0']
                elif ny == 1:
                    y, walls = 2 * D - sy, walls + ['y1']
                else:
                    y = sy
                if nz == -1:
                    z, walls = -sz, walls + ['z0']
                elif nz == 1:
                    z, walls = 2 * HGT - sz, walls + ['z1']
                else:
                    z = sz
                out.append(((x, y, z), walls))
    return out


def _tf(src, mic, f: np.ndarray, base_delay: float, axis=None) -> np.ndarray:
    """The transfer spectrum source -> mic (direct + early reflections)."""
    H = np.zeros(f.size, np.complex128)
    for pos, walls in _images(src):
        d = math.dist(pos, mic)
        tau = d / C_SOUND - base_delay
        g = DIRECT_REF_M / max(d, 0.5)
        for w in walls:
            g *= REFLECT[w]
        mag = np.full(f.size, g)
        for w in walls:
            mag /= np.sqrt(1 + (f / WALL_FC[w]) ** 2)
        mag *= 10 ** (-(d * 0.0016 * (f / 1000.0) ** 1.7) / 20)        # air
        # the voice's directivity: the singer faces the audience (+y); sound leaving backwards / upwards is darker
        vx, vy, vz = pos[0] - src[0], pos[1] - src[1], pos[2] - src[2]
        if not walls:
            vx, vy, vz = mic[0] - src[0], mic[1] - src[1], mic[2] - src[2]
        else:   # the direction the sound left the singer: towards the image of the mic through those walls
            vx, vy, vz = _first_leg(src, mic, walls)
        cos = vy / (math.sqrt(vx * vx + vy * vy + vz * vz) + 1e-9)
        back = (1 - cos) / 2
        mag *= (1 - back) + back / np.sqrt(1 + (f / 2200.0) ** 2) * 0.8
        if axis is not None:                          # a cardioid; None = omni
            ax = axis
            ux, uy, uz = pos[0] - mic[0], pos[1] - mic[1], pos[2] - mic[2]
            cosm = (ux * ax[0] + uy * ax[1] + uz * ax[2]) / (math.sqrt(ux * ux + uy * uy + uz * uz) *
                                                             math.sqrt(ax[0] ** 2 + ax[1] ** 2 + ax[2] ** 2) + 1e-9)
            mag *= 0.5 + 0.5 * cosm
        H += mag * np.exp(-2j * np.pi * f * max(tau, 0.0))
    return H


def _first_leg(src, mic, walls):
    """The direction from the source towards the mic's image across the same walls (the leg leaving the singer)."""
    mx, my, mz = mic
    if 'x0' in walls:
        mx = -mx
    if 'x1' in walls:
        mx = 2 * W - mx
    if 'y0' in walls:
        my = -my
    if 'y1' in walls:
        my = 2 * D - my
    if 'z0' in walls:
        mz = -mz
    if 'z1' in walls:
        mz = 2 * HGT - mz
    return mx - src[0], my - src[1], mz - src[2]


def base_delay() -> float:
    """The nearest seat's direct delay (taken off every path: the section starts at once)."""
    best = 1e9
    for part in ROWS:
        for s in seats(part, 16):
            for m in MICS:
                best = min(best, math.dist(s, m) / C_SOUND)
    return best - 0.001


@lru_cache(maxsize=2)
def impulse_spectra(part: str, n: int, nfft: int) -> np.ndarray:
    """[n, 2, nfft//2+1] transfer spectra of the part's n singers to the (L, R) mics."""
    f = np.fft.rfftfreq(nfft, 1 / SR)
    b = base_delay()
    S = seats(part, n)
    out = np.zeros((n, 2, f.size), np.complex128)
    T = TAIL
    k0, k1 = int(T['start_s'] * SR), int((T['start_s'] + T['len_s']) * SR)
    t = np.arange(k1 - k0) / SR
    env = 10 ** (-60.0 / 20 * t / T['rt60_s']) * np.minimum(1.0, t / 0.015)
    lp = 1 / np.sqrt(1 + (f / T['fc']) ** 2)
    for i, s in enumerate(S):
        for c, m in enumerate(MICS):
            out[i, c] = _tf(s, m, f, b, AXES[c]) + OUT_GAIN * _tf(s, OUTRIGGERS[c], f, b)
            rng = np.random.default_rng((ord(part) * 1000 + i) * 2 + c)
            ir = np.zeros(nfft)
            noise = rng.standard_normal(t.size) * env
            # energy against a direct sound of unit level: sum(ir^2) = 10^(level/10)
            ir[k0:k1] = noise * np.sqrt(10 ** (T['level_db'] / 10) / (np.sum(noise ** 2) + 1e-20))
            out[i, c] += np.fft.rfft(ir) * lp
    return out
