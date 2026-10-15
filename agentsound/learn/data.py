"""Dataset plumbing for the student: the vocabulary, the encoded pieces (cached as one .pt), batches by token budget.
No torch import at module level except in the functions that need it."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from ..endless.genres import GENRES

# The student's conditioning genres, in embedding order (checkpoints store theirs). Append-only and explicit: a new
# endless genre joins the student when its data is exported and a model retrained, never by being registered.
GENRE_NAMES = ['jazz-piano', 'jazz-trio', 'new-age-piano', 'classical-piano', 'lofi-piano']


def genre_index(name: str) -> int:
    return GENRE_NAMES.index(name)


class Vocab:
    def __init__(self, tokens: list[str]):
        self.itos = list(tokens)
        self.stoi = {t: i for i, t in enumerate(self.itos)}
        self.pad, self.bos, self.eos = self.stoi['PAD'], self.stoi['BOS'], self.stoi['EOS']

    @classmethod
    def build(cls, seqs, arrangement: bool = False) -> 'Vocab':
        """The tokens of seqs; arrangement: + every Arr-block token of the student's genres when the data is schema 2
        (tokens.arrangement_tokens: the players' whole vocabulary, not only what the teacher drew)."""
        seen = set()
        for s in seqs:
            seen.update(s)
        if arrangement and 'Arr' in seen:
            from .tokens import arrangement_tokens
            seen |= arrangement_tokens(GENRE_NAMES)
        return cls(['PAD'] + sorted(seen))

    @classmethod
    def load(cls, path) -> 'Vocab':
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.itos), encoding='utf-8')

    def encode(self, toks) -> list[int] | None:
        try:
            return [self.stoi[t] for t in toks]
        except KeyError:
            return None

    def decode(self, ids) -> list[str]:
        return [self.itos[i] for i in ids if i != self.pad]

    def __len__(self):
        return len(self.itos)


def split_of(genre: str, seed: int, val: float = 0.02) -> str:
    h = int(hashlib.md5(f"{genre}:{seed}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return 'val' if h < val else 'train'


def records(roots, status=('ok', 'tok')):
    from .export import load
    for r in roots:
        if Path(r).is_dir():
            yield from load(Path(r), status=status)


def select(recs: list[dict], top: float | None = None) -> list[dict]:
    """top: keep the best `top` share per genre by composer.score (scored records only)."""
    if not top:
        return recs
    out = []
    for g in GENRE_NAMES:
        rs = sorted((r for r in recs if r['genre'] == g and r.get('score') is not None), key=lambda r: -r['score'])
        out += rs[:max(1, int(len(rs) * top))]
    return out


def batches(items: list, max_tokens: int, rng: random.Random, max_batch: int = 64):
    """items: (ids, genre index, weight) -> lists of items, bucketed by length so padding stays small."""
    order = sorted(range(len(items)), key=lambda i: (len(items[i][0]) + rng.random() * 40))
    out, cur, longest = [], [], 0
    for i in order:
        n = len(items[i][0])
        if cur and (max(longest, n) * (len(cur) + 1) > max_tokens or len(cur) >= max_batch):
            out.append(cur)
            cur, longest = [], 0
        cur.append(items[i])
        longest = max(longest, n)
    if cur:
        out.append(cur)
    rng.shuffle(out)
    return out


def collate(batch, pad: int, n_genres: int, device):
    import torch
    T = max(len(b[0]) for b in batch)
    idx = torch.full((len(batch), T), pad, dtype=torch.long)
    mask = torch.zeros((len(batch), T), dtype=torch.float32)
    cond = torch.zeros((len(batch), n_genres), dtype=torch.float32)
    w = torch.ones(len(batch), dtype=torch.float32)
    for i, b in enumerate(batch):
        idx[i, :len(b[0])] = torch.tensor(b[0])
        mask[i, :len(b[0])] = 1.0
        cond[i, b[1]] = 1.0
        if len(b) > 2:
            w[i] = b[2]
    return idx.to(device), cond.to(device), mask.to(device), w.to(device)
