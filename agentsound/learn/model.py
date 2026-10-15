"""The student: a decoder-only transformer over the token schema (agentsound.learn.tokens), plain PyTorch.

Conditioning: a learned GENRE embedding table; a piece's conditioning vector is a weighted sum of its rows (one-hot
for training, any blend - 0.7 new-age + 0.3 jazz - when sampling), added to every position's input and fed as the
first position (a soft prefix token before BOS). Everything else (mood, feel, form, key, tempo, the plan) the model
samples itself after BOS, or a prompt forces it.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class Config:
    vocab: int
    n_genres: int
    d: int = 512
    layers: int = 10
    heads: int = 8
    ctx: int = 1152
    dropout: float = 0.1

    def to_dict(self):
        return asdict(self)


class Block(nn.Module):
    def __init__(self, c: Config):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(c.d), nn.LayerNorm(c.d)
        self.qkv = nn.Linear(c.d, 3 * c.d)
        self.proj = nn.Linear(c.d, c.d)
        self.ff = nn.Sequential(nn.Linear(c.d, 4 * c.d), nn.GELU(), nn.Linear(4 * c.d, c.d))
        self.h, self.drop = c.heads, c.dropout

    def forward(self, x, cache=None):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).split(D, dim=2)
        q, k, v = (t.view(B, T, self.h, D // self.h).transpose(1, 2) for t in (q, k, v))
        if cache is not None:
            if 'k' in cache:
                k = torch.cat([cache['k'], k], dim=2)
                v = torch.cat([cache['v'], v], dim=2)
            cache['k'], cache['v'] = k, v
        causal = cache is None or T > 1
        if cache is not None and T > 1 and k.shape[2] != T:
            raise ValueError('a multi-token step needs an empty cache')
        y = F.scaled_dot_product_attention(q, k, v, is_causal=causal,
                                           dropout_p=self.drop if self.training else 0.0)
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        x = x + F.dropout(self.proj(y), self.drop, self.training)
        return x + F.dropout(self.ff(self.ln2(x)), self.drop, self.training)


class Student(nn.Module):
    def __init__(self, c: Config):
        super().__init__()
        self.c = c
        self.tok = nn.Embedding(c.vocab, c.d)
        self.pos = nn.Embedding(c.ctx + 1, c.d)
        self.genre = nn.Linear(c.n_genres, c.d, bias=False)       # (a blend = a weighted sum of its columns)
        self.blocks = nn.ModuleList(Block(c) for _ in range(c.layers))
        self.ln = nn.LayerNorm(c.d)
        self.head = nn.Linear(c.d, c.vocab, bias=False)
        self.head.weight = self.tok.weight                        # tied
        self.apply(self._init)
        for n, p in self.named_parameters():
            if n.endswith('proj.weight') or n.endswith('ff.2.weight'):
                nn.init.normal_(p, 0.0, 0.02 / math.sqrt(2 * c.layers))

    @staticmethod
    def _init(m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, 0.0, 0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, 0.0, 0.02)

    def n_params(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def forward(self, idx, cond, caches=None, start: int = 0):
        """idx (B, T) token ids, cond (B, n_genres) genre weights -> logits (B, T, vocab) predicting the next token
        of every position. Position 0 of the sequence is the conditioning prefix: logits[:, t] follow token t."""
        B, T = idx.shape
        g = self.genre(cond.to(self.tok.weight.dtype))[:, None, :]
        x = self.tok(idx) + g
        if start == 0:
            x = torch.cat([g, x], dim=1)                          # the soft prefix
            pos = torch.arange(0, T + 1, device=idx.device)
        else:
            pos = torch.arange(start + 1, start + 1 + T, device=idx.device)
        x = x + self.pos(pos)[None]
        for i, b in enumerate(self.blocks):
            x = b(x, None if caches is None else caches[i])
        x = self.ln(x)
        if start == 0:
            x = x[:, 1:]
        return self.head(x)

    def logprobs(self, idx, cond, mask):
        """Per-token log p(idx[:, t] | idx[:, :t], cond) for t >= 1 (B, T-1), masked."""
        logits = self.forward(idx[:, :-1], cond).float()
        lp = torch.log_softmax(logits, dim=-1).gather(-1, idx[:, 1:, None])[..., 0]
        return lp * mask[:, 1:]


@torch.no_grad()
def sample(model: Student, cond, bos: int, eos: int, max_len: int, temperature: float = 1.0, top_p: float = 1.0,
           allowed=None, prompt=None, generator=None, mix=None, header_temp=None, head_end=None):
    """Autoregressive sampling with a KV cache: cond (B, n_genres); returns a list of token-id lists (each from BOS
    to EOS, or cut at max_len). allowed(step, seq) -> None or a (vocab,) / (B, vocab) bool mask for that step (called
    at every step, forced ones too: a parser keeps its state); prompt: token ids forced after BOS (one list for
    every row, or B lists of equal length: one per row). mix: [(cond, weight)] = the LOGIT blend - the next-token
    log-probs of each conditioning mixed by weight (instead of one blended conditioning vector). header_temp: the
    temperature of a row until it emits head_end (the header + plan before the first 'H'), `temperature` after."""
    model.eval()
    dev = cond.device
    B = cond.shape[0]
    comps = mix or [(cond, 1.0)]
    caches = [[dict() for _ in model.blocks] for _ in comps]
    seq = torch.full((B, 1), bos, dtype=torch.long, device=dev)
    if prompt and isinstance(prompt[0], (list, tuple)):
        if len(prompt) != B or len({len(p) for p in prompt}) != 1:
            raise ValueError('per-row prompts: one per row, all of one length')
        forced = list(torch.tensor(prompt, dtype=torch.long, device=dev).T)
    else:
        forced = [torch.full((B,), t, dtype=torch.long, device=dev) for t in (prompt or [])]
    in_head = torch.ones(B, dtype=torch.bool, device=dev)

    def step_logits(x, start):
        out = 0.0
        with torch.autocast('cuda', dtype=torch.float16, enabled=dev.type == 'cuda'):
            for (c, w), cc in zip(comps, caches):
                lg = model(x, c, caches=cc, start=start)[:, -1].float()
                out = out + w * (torch.log_softmax(lg, dim=-1) if len(comps) > 1 else lg)
        return out
    logits = step_logits(seq, 0)
    done = torch.zeros(B, dtype=torch.bool, device=dev)
    for step in range(1, max_len):
        m = allowed(step, seq) if allowed is not None else None
        if forced:
            nxt = forced.pop(0)
        else:
            if header_temp is None or head_end is None:
                lg = logits / max(1e-5, temperature)
            else:
                t = torch.where(in_head, max(1e-5, header_temp), max(1e-5, temperature))
                lg = logits / t[:, None]
            if m is not None:
                m = m.to(dev)
                lg = lg.masked_fill(~(m if m.dim() == 2 else m[None, :]), float('-inf'))
            probs = torch.softmax(lg, dim=-1)
            if top_p < 1.0:
                sp, si = probs.sort(dim=-1, descending=True)
                cut = sp.cumsum(-1) - sp > top_p
                sp = sp.masked_fill(cut, 0.0)
                probs = torch.zeros_like(probs).scatter(-1, si, sp)
            nxt = torch.multinomial(probs, 1, generator=generator)[:, 0]
        nxt = torch.where(done, torch.full_like(nxt, eos), nxt)
        seq = torch.cat([seq, nxt[:, None]], dim=1)
        if head_end is not None:
            in_head &= nxt != head_end
        done |= nxt == eos
        if bool(done.all()):
            break
        logits = step_logits(nxt[:, None], step)
    out = []
    for row in seq.tolist():
        out.append(row[:row.index(eos) + 1] if eos in row else row)
    return out
