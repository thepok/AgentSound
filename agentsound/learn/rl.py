"""GRPO for the student: per step P prompts (a genre + a forced mood), G pieces each; reward = composer.score / 100
for a piece that passes the runner's checks (0 for an arc / breath reject, -0.2 for an undecodable or unplayable
sequence), optionally + a discriminator term; advantage = (reward - the group's mean) / its sd (no value network);
policy gradient on the sequence's mean token log-prob + a KL penalty to the frozen supervised model (k3 estimator).

Logged every step (RUN/rl.jsonl): the reward and score, the check rates, the token entropy, the KL, the HELD-OUT
tells (score_metrics measures the style's score table does not weigh - the Goodhart watch), diversity (distinct
6-grams, pairwise bar Jaccard) and every `--nn-every` steps the nearest-neighbour similarity to the training set."""
from __future__ import annotations

import copy
import json
import random
import statistics as st
import time
from pathlib import Path


def args_rl(ap) -> None:
    ap.add_argument('--run', required=True, help='the starting checkpoint (the KL reference too)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--genres', nargs='*', default=['new-age-piano'])
    ap.add_argument('--steps', type=int, default=150)
    ap.add_argument('--prompts', type=int, default=4)
    ap.add_argument('--group', type=int, default=8)
    ap.add_argument('--lr', type=float, default=1e-5)
    ap.add_argument('--beta', type=float, default=0.05, help='KL penalty weight')
    ap.add_argument('--temp', type=float, default=1.0)
    ap.add_argument('--micro', type=int, default=8)
    ap.add_argument('--nn-every', type=int, default=10)
    ap.add_argument('--disc', type=float, default=0.0, help='weight of the discriminator reward term (0 = off)')
    ap.add_argument('--disc-every', type=int, default=10, help='retrain the discriminator every N steps')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--ref', help='the KL reference checkpoint (default: --run): continue a run, keep its reference')


def _logprobs(model, ids, cond, mask):
    import torch
    with torch.autocast('cuda', dtype=torch.float16):
        logits = model(ids[:, :-1], cond)
    logits = logits.float()
    lsm = torch.log_softmax(logits, dim=-1)
    lp = lsm.gather(-1, ids[:, 1:, None])[..., 0]
    ent = -(lsm.exp() * lsm).sum(-1)
    return lp, ent, mask[:, 1:]


def cmd_rl(a) -> int:
    import torch
    from ..endless.genres import GENRES, SCORES
    from .data import GENRE_NAMES, collate
    from .evaluate import diversity, measure_many, unscored
    from .run import _ckpt, _log_to, train_index
    from .sample import cond_vector, generate
    from .train import load_ckpt, save_ckpt
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = _log_to(out / 'rl.log')
    log(f"GRPO {vars(a)}")
    policy, vocab, _ = load_ckpt(_ckpt(a.run))
    ref = load_ckpt(_ckpt(a.ref))[0].eval() if a.ref else copy.deepcopy(policy).eval()
    for p in ref.parameters():
        p.requires_grad_(False)
    policy.train()
    for m in policy.modules():                       # (no dropout in RL: the logprobs must be the sampler's)
        if isinstance(m, torch.nn.Dropout):
            m.p = 0.0
    for b in policy.blocks:
        b.drop = 0.0
    opt = torch.optim.AdamW(policy.parameters(), lr=a.lr, betas=(0.9, 0.95), weight_decay=0.0)
    rng = random.Random(a.seed)
    idx = {g: train_index(g) for g in a.genres}
    disc = None
    if a.disc > 0:
        from .disc import Discriminator
        disc = Discriminator(a.genres[0], log=log)
    jf = (out / 'rl.jsonl').open('a', encoding='utf-8')
    for step in range(1, a.steps + 1):
        t0 = time.time()
        seqs, conds, groups = [], [], []
        policy.eval()
        for gi, g in enumerate(a.genres):              # (a prompt = a genre: its P x G pieces in one batch; the
            s = generate(policy, vocab, {g: 1.0}, a.prompts * a.group, temperature=a.temp,   # groups of G
                         seed=a.seed * 1_000_003 + step * 101 + gi, batch=a.prompts * a.group)   # normalize)
            seqs += s
            conds += [g] * len(s)
            groups += [gi * a.prompts + k // a.group for k in range(len(s))]
        policy.train()
        t1 = time.time()
        res = []
        for g in sorted(set(conds)):
            ix = [i for i, c in enumerate(conds) if c == g]
            for i, r in zip(ix, measure_many([seqs[i] for i in ix], g, seed0=900_000 + step * 100)):
                res.append((i, r))
        res = [r for _, r in sorted(res, key=lambda x: x[0])]
        t2 = time.time()
        rew = []
        for r in res:
            if r['status'] == 'ok':
                rew.append(r['score'] / 100.0)
            elif r['status'] in ('arc', 'breath'):
                rew.append(0.0)
            else:
                rew.append(-0.2)
        dscore = None
        if disc is not None:
            if step % a.disc_every == 1 or a.disc_every == 1:
                disc.fit([r for r in res if r['status'] == 'ok'])
            dscore = [disc.prob_real(r) if r['status'] == 'ok' else 0.0 for r in res]
            rew = [x + a.disc * d for x, d in zip(rew, dscore)]
        adv = [0.0] * len(rew)
        for gi in set(groups):
            ix = [i for i, x in enumerate(groups) if x == gi]
            m = st.mean(rew[i] for i in ix)
            sd = st.pstdev([rew[i] for i in ix])
            for i in ix:
                adv[i] = (rew[i] - m) / (sd + 1e-3)
        # ---- the update (one pass, on-policy: the ratio is 1, the gradient is A * grad log p)
        opt.zero_grad(set_to_none=True)
        items = [(vocab.encode(s), GENRE_NAMES.index(c), ad) for s, c, ad in zip(seqs, conds, adv)]
        kl_sum = ent_sum = ntok = 0.0
        for k in range(0, len(items), a.micro):
            mb = items[k:k + a.micro]
            ids, cond, mask, w = collate(mb, vocab.pad, len(GENRE_NAMES), 'cuda')
            lp, ent, m = _logprobs(policy, ids, cond, mask)
            with torch.no_grad():
                rlp, _, _ = _logprobs(ref, ids, cond, mask)
            d = rlp - lp
            kl = (torch.exp(d) - d - 1.0) * m
            L = m.sum(1).clamp(min=1.0)
            pg = -(w * (lp * m).sum(1) / L)
            loss = (pg + a.beta * kl.sum(1) / L).sum() / len(items)
            loss.backward()
            kl_sum += float(kl.sum().detach())
            ent_sum += float((ent * m).sum().detach())
            ntok += float(m.sum())
        torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
        opt.step()
        t3 = time.time()
        ok = [r for r in res if r['status'] == 'ok']
        style = GENRES[a.genres[0]].style
        held = {}
        if ok:
            keys = unscored(style, ok[0]['metrics'])
            for k in keys:
                v = [r['metrics'][k] for r in ok if r['metrics'].get(k) is not None]
                if v:
                    held[k] = round(st.mean(v), 3)
        rec = {'step': step, 'reward': round(st.mean(rew), 4),
               'score': round(st.mean([r['score'] for r in ok]), 2) if ok else None,
               'ok': round(len(ok) / len(res), 3), 'invalid': round(sum(r['status'] == 'invalid' for r in res) / len(res), 3),
               'kl': round(kl_sum / max(1.0, ntok), 5), 'entropy': round(ent_sum / max(1.0, ntok), 4),
               'len': round(st.mean(len(s) for s in seqs), 1), 'div': diversity(seqs),
               'held_tells': held, 'scored_parts': _parts_mean(ok, SCORES[style]),
               'disc': round(st.mean(dscore), 3) if dscore else None,
               't_gen': round(t1 - t0, 1), 't_score': round(t2 - t1, 1), 't_upd': round(t3 - t2, 1)}
        if step % a.nn_every == 0 or step == 1:
            nov = [idx[c].novelty(s) for s, c in zip(seqs, conds)]
            rec['nn_jaccard'] = round(st.mean(n['nn_jaccard'] for n in nov), 3)
            rec['ngram_seen'] = round(st.mean(n['ngram_seen'] for n in nov), 3)
            rec['copies'] = sum(n['copy'] for n in nov)
        jf.write(json.dumps(rec) + '\n')
        jf.flush()
        log(f"step {step}: reward {rec['reward']} score {rec['score']} ok {rec['ok']} kl {rec['kl']} ent "
            f"{rec['entropy']} div {rec['div']} " + (f"nn {rec.get('nn_jaccard')} " if 'nn_jaccard' in rec else '')
            + f"({rec['t_gen']}+{rec['t_score']}+{rec['t_upd']} s)")
        if step % 25 == 0 or step == a.steps:
            save_ckpt(out / 'ckpt.pt', policy, vocab, step=step)
            with open(out / f"samples-{step:04d}.jsonl", 'w', encoding='utf-8') as f:
                for s, r, c in zip(seqs, res, conds):
                    f.write(json.dumps(dict(r, tokens=s, genre=c)) + '\n')
    jf.close()
    return 0


def _parts_mean(ok, table) -> dict:
    out = {}
    for k in table:
        v = [r['metrics'][k] for r in ok if r['metrics'].get(k) is not None]
        if v:
            out[k] = round(st.mean(v), 3)
    return out
