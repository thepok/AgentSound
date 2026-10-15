"""Training the student (supervised: next-token cross-entropy on teacher pieces; weighted for expert iteration)."""
from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

import torch

from .data import GENRE_NAMES, Vocab, batches, collate, genre_index, records, select, split_of
from .model import Config, Student
from .tokens import schema_of


def load_ckpt(path, device='cuda'):
    """(model, vocab, the checkpoint dict); ck['schema']: its token schema (tokens.SCHEMA; a checkpoint from before
    the Arr block has none: 1, read off its vocabulary)."""
    ck = torch.load(path, map_location=device, weights_only=False)
    cfg = Config(**ck['config'])
    m = Student(cfg).to(device)
    m.load_state_dict(ck['model'])
    ck.setdefault('schema', schema_of(ck['vocab']))
    return m, Vocab(ck['vocab']), ck


def save_ckpt(path, model: Student, vocab: Vocab, **extra):
    torch.save(dict(model=model.state_dict(), config=model.c.to_dict(), vocab=vocab.itos, genres=GENRE_NAMES,
                    schema=schema_of(vocab.itos), **extra), path)


def related_rows(old: Vocab, tok: str) -> list[int]:
    """The old vocabulary's rows a new token starts from: the same prefix ('ARit_0.68' <- every 'ARit_*'), else every
    Arr-block token for an 'A...' token, else none (the caller takes the mean of all rows)."""
    pre = tok.partition('_')[0]
    same = [i for i, t in enumerate(old.itos) if t.partition('_')[0] == pre and '_' in t]
    if same:
        return same
    if tok.startswith('A'):
        return [i for i, t in enumerate(old.itos) if t.startswith('A') and '_' in t]
    return []


@torch.no_grad()
def extend_vocab(model: Student, vocab: Vocab, new_tokens, device='cuda', noise=0.01, seed=0):
    """(model, vocab) with new_tokens appended (the old ids keep their rows, so the checkpoint's knowledge stays where
    it was): a new token's embedding (= its tied output row) is the mean of its related rows (related_rows) + a little
    noise, so a new value of a known key starts as an average value of that key. Returns the new model and vocab."""
    new = [t for t in sorted(set(new_tokens)) if t not in vocab.stoi]
    if not new:
        return model, vocab
    nv = Vocab(vocab.itos + new)
    cfg = Config(**{**model.c.to_dict(), 'vocab': len(nv)})
    m = Student(cfg).to(device)
    sd = {k: v for k, v in model.state_dict().items() if k not in ('tok.weight', 'head.weight')}
    m.load_state_dict(sd, strict=False)
    old = model.tok.weight.detach()
    w = m.tok.weight
    w[:len(vocab)] = old
    g = torch.Generator(device='cpu').manual_seed(seed)
    for k, t in enumerate(new):
        rows = related_rows(vocab, t)
        base = old[rows].mean(0) if rows else old.mean(0)
        w[len(vocab) + k] = base + noise * torch.randn(base.shape, generator=g).to(base.device)
    return m, nv


@torch.no_grad()
def extend_ctx(model: Student, ctx: int, device='cuda', noise=0.01, seed=0) -> Student:
    """The model with a longer context: the learned positions 0..old ctx keep their rows, each new position starts
    as the last trained one + a little noise (the long tail is rarely trained, so the last row is the best guess)."""
    if ctx <= model.c.ctx:
        return model
    m = Student(Config(**{**model.c.to_dict(), 'ctx': ctx})).to(device)
    sd = {k: v for k, v in model.state_dict().items() if k != 'pos.weight'}
    m.load_state_dict(sd, strict=False)
    old = model.pos.weight.detach()
    w = m.pos.weight
    w[:len(old)] = old
    g = torch.Generator(device='cpu').manual_seed(seed)
    for i in range(len(old), len(w)):
        w[i] = old[-1] + noise * torch.randn(old.shape[1], generator=g).to(old.device)
    return m


def items_from(recs, vocab: Vocab, ctx: int, weight_key=None):
    tr, va, dropped = [], [], 0
    for r in recs:
        ids = vocab.encode(r['tokens'].split() if isinstance(r['tokens'], str) else r['tokens'])
        if ids is None or len(ids) > ctx:
            dropped += 1
            continue
        it = (ids, genre_index(r['genre']), float(r.get(weight_key, 1.0)) if weight_key else 1.0)
        (va if split_of(r['genre'], r['seed']) == 'val' and not r.get('extra') else tr).append(it)
    return tr, va, dropped


@torch.no_grad()
def evaluate(model, vocab, items, max_tokens, device, limit=600):
    model.eval()
    rng = random.Random(0)
    its = items[:limit]
    tot = n = 0.0
    for b in batches(its, max_tokens, rng):
        idx, cond, mask, _ = collate(b, vocab.pad, len(GENRE_NAMES), device)
        with torch.autocast('cuda', dtype=torch.float16):
            logits = model(idx[:, :-1], cond)
        loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), idx[:, 1:].reshape(-1),
                                                 reduction='none').view(idx.shape[0], -1)
        tot += float((loss * mask[:, 1:]).sum())
        n += float(mask[:, 1:].sum())
    model.train()
    return tot / max(1.0, n)


def train(run: Path, data_roots: list, *, init=None, top=None, extra=None, epochs=4.0, max_steps=None, lr=3e-4,
          max_tokens=20000, warmup=400, d=512, layers=10, heads=8, ctx=1152, dropout=0.1, status=('ok', 'tok'),
          genres=None, eval_every=500, log=print, seed=0):
    """Train (or fine-tune from `init`) on the records of data_roots (statuses `status`, the best `top` share per
    genre when given) + `extra` [(tokens, genre, weight)] (expert iteration). Writes RUN/ckpt.pt, RUN/log.jsonl."""
    run = Path(run)
    run.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(seed)
    dev = 'cuda'
    recs = [r for r in records(data_roots, status=status) if not genres or r['genre'] in genres]
    recs = select(recs, top)
    for i, (toks, g, w) in enumerate(extra or []):
        recs.append({'genre': g, 'seed': -1 - i, 'tokens': toks, 'w': w, 'extra': True})
    if init:
        model, vocab, _ = load_ckpt(init, dev)
        seen = {t for r in recs for t in (r['tokens'].split() if isinstance(r['tokens'], str) else r['tokens'])}
        if 'Arr' in seen:                     # (schema 2: the players' whole arrangement vocabulary, as Vocab.build)
            from .tokens import arrangement_tokens
            seen |= arrangement_tokens(GENRE_NAMES)
        n0, c0 = len(vocab), model.c.ctx
        model, vocab = extend_vocab(model, vocab, seen - set(vocab.stoi), dev)
        if len(vocab) > n0:
            log(f"warm start: vocab {n0} -> {len(vocab)} (+{len(vocab) - n0} rows from their related tokens' mean)")
        if ctx > c0:
            model = extend_ctx(model, ctx, dev)
            log(f"warm start: context {c0} -> {ctx} (the new positions from the last trained one)")
    else:
        vocab = Vocab.build((r['tokens'].split() if isinstance(r['tokens'], str) else r['tokens'] for r in recs),
                            arrangement=True)
        model = Student(Config(vocab=len(vocab), n_genres=len(GENRE_NAMES), d=d, layers=layers, heads=heads, ctx=ctx,
                               dropout=dropout)).to(dev)
    vocab.save(run / 'vocab.json')
    tr, va, dropped = items_from(recs, vocab, model.c.ctx, weight_key='w')
    log(f"train: {len(tr)} pieces ({sum(len(x[0]) for x in tr) / 1e6:.1f} M tokens), val {len(va)}, dropped "
        f"{dropped}; model {model.n_params() / 1e6:.1f} M params, vocab {len(vocab)}")
    opt = torch.optim.AdamW(model.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
    scaler = torch.amp.GradScaler('cuda')
    rng = random.Random(seed)
    steps_per_epoch = len(batches(tr, max_tokens, random.Random(1)))
    total = max_steps or int(steps_per_epoch * epochs)
    logf = (run / 'log.jsonl').open('a', encoding='utf-8')
    step, t0, seen = 0, time.time(), 0
    best = None
    model.train()
    while step < total:
        for b in batches(tr, max_tokens, rng):
            if step >= total:
                break
            cur = lr * min(1.0, (step + 1) / warmup) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1.0, step / total))))
            for gr in opt.param_groups:
                gr['lr'] = cur
            idx, cond, mask, w = collate(b, vocab.pad, len(GENRE_NAMES), dev)
            with torch.autocast('cuda', dtype=torch.float16):
                logits = model(idx[:, :-1], cond)
            loss_t = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.shape[-1]),
                                                       idx[:, 1:].reshape(-1), reduction='none').view(idx.shape[0], -1)
            m = mask[:, 1:] * w[:, None]
            loss = (loss_t * m).sum() / m.sum()
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            seen += int(mask.sum())
            step += 1
            if step % 50 == 0:
                el = time.time() - t0
                rec = {'step': step, 'loss': round(loss.item(), 4), 'lr': cur, 'tok_s': round(seen / el),
                       'epoch': round(step / steps_per_epoch, 3), 'min': round(el / 60, 1)}
                if step % eval_every == 0 or step == total:
                    rec['val'] = round(evaluate(model, vocab, va, max_tokens, dev), 4)
                    rec['vram_gib'] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
                    if best is None or rec['val'] < best:
                        best = rec['val']
                        save_ckpt(run / 'ckpt.pt', model, vocab, step=step, val=best)
                logf.write(json.dumps(rec) + '\n')
                logf.flush()
                if 'val' in rec or step % 200 == 0:
                    log(json.dumps(rec))
    v = evaluate(model, vocab, va, max_tokens, dev)
    log(f"final val {v:.4f} (best {best}); GPU peak reserved {torch.cuda.max_memory_reserved() / 2**30:.2f} GiB")
    if best is None or v <= best:
        save_ckpt(run / 'ckpt.pt', model, vocab, step=step, val=v)
    save_ckpt(run / 'last.pt', model, vocab, step=step, val=v)
    logf.close()
    return run / 'ckpt.pt'
