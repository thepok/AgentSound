"""The adversarial reward term: a small classifier (L2 logistic regression on the notes-level metrics) telling the
LLM-composed reference pieces (letters-to-the-morning, songs/pro-newage-*) from the student's pieces, refit on the
policy's latest pieces as it improves. prob_real(piece) is the reward bonus. With only four references it is a
weak, heavily regularized critic: it can say 'this metric is out of the references' cloud', not much more."""
from __future__ import annotations

import math
from pathlib import Path

REFERENCES = {'new-age-piano': ['letters-to-the-morning', 'pro-newage-rain', 'pro-newage-hopeful', 'pro-newage-waltz'],
              'jazz-piano': ['pro-piano-blues', 'pro-piano-bossa', 'pro-piano-latenight', 'pro-piano-waltz']}
TUNE_ONLY = {'mel_issues', 'mel_style', 'arc_pitch_r', 'arc_dens_r', 'hook_head', 'hook_tag', 'lh_distinct',
             'lh_figures', 'hook', 'hook_sections', 'quotes'}


def reference_metrics(genre: str) -> list[dict]:
    from ..endless.composer import score_metrics
    from ..endless.genres import get
    from ..endless.run import load_scored
    from .render import MAIN
    style = get(genre).style
    out = []
    for name in REFERENCES[genre]:
        song, tune, _ = load_scored(Path(MAIN / 'songs' / name))
        out.append(score_metrics(song, tune, style))
    return out


class Discriminator:
    def __init__(self, genre: str, l2: float = 3.0, buffer: int = 256, log=print):
        self.real = reference_metrics(genre)
        self.keys = sorted(set.intersection(*(set(m) for m in self.real)) - TUNE_ONLY)
        self.l2, self.buffer, self.log = l2, buffer, log
        self.fake: list[dict] = []
        self.w, self.b, self.mu, self.sd = None, 0.0, None, None

    def _x(self, m: dict) -> list[float]:
        return [float(m.get(k) or 0.0) for k in self.keys]

    def fit(self, rows: list[dict], iters: int = 400, lr: float = 0.1) -> None:
        self.fake = (self.fake + [r['metrics'] for r in rows])[-self.buffer:]
        if not self.fake:
            return
        X = [self._x(m) for m in self.real + self.fake]
        y = [1.0] * len(self.real) + [0.0] * len(self.fake)
        wt = [0.5 / len(self.real)] * len(self.real) + [0.5 / len(self.fake)] * len(self.fake)
        n = len(self.keys)
        self.mu = [sum(x[j] for x in X) / len(X) for j in range(n)]
        self.sd = [max(1e-6, math.sqrt(sum((x[j] - self.mu[j]) ** 2 for x in X) / len(X))) for j in range(n)]
        Z = [[(x[j] - self.mu[j]) / self.sd[j] for j in range(n)] for x in X]
        w, b = [0.0] * n, 0.0
        for _ in range(iters):
            gw, gb = [self.l2 * wj / len(X) for wj in w], 0.0
            for z, t, c in zip(Z, y, wt):
                p = 1 / (1 + math.exp(-max(-30, min(30, sum(wj * zj for wj, zj in zip(w, z)) + b))))
                for j in range(n):
                    gw[j] += c * (p - t) * z[j]
                gb += c * (p - t)
            w = [wj - lr * g for wj, g in zip(w, gw)]
            b -= lr * gb
        self.w, self.b = w, b
        top = sorted(zip(self.keys, w), key=lambda x: -abs(x[1]))[:5]
        self.log(f"  discriminator refit on {len(self.fake)} student pieces: " +
                 ', '.join(f"{k} {v:+.2f}" for k, v in top))

    def prob_real(self, row: dict) -> float:
        if self.w is None:
            return 0.0
        z = [(v - m) / s for v, m, s in zip(self._x(row['metrics']), self.mu, self.sd)]
        a = sum(wj * zj for wj, zj in zip(self.w, z)) + self.b
        return 1 / (1 + math.exp(-max(-30, min(30, a))))
