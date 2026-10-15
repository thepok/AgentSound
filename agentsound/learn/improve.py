"""Expert iteration: the student generates, composer.score judges, the best pieces (+ a replay of the teacher's best)
fine-tune the student; repeated for a few rounds. Each round logs the RAW sample distribution of the current model
(no best-of-N): what the student itself has learned."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path


def args_finetune(ap) -> None:
    ap.add_argument('--run', required=True, help='the starting checkpoint (or its run dir)')
    ap.add_argument('--out', required=True, help='a new run dir (round checkpoints, log)')
    ap.add_argument('--genres', nargs='*')
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--n', type=int, default=256, help='pieces generated per genre per round')
    ap.add_argument('--keep', type=float, default=0.25, help='share of the generated pieces (best score) kept')
    ap.add_argument('--replay', type=float, default=0.25, help="the teacher's best share replayed (data/full)")
    ap.add_argument('--steps', type=int, default=600)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--temp', type=float, default=1.0)


def cmd_finetune(a) -> int:
    import torch
    from .evaluate import measure_many, rates, score_stats
    from .run import DATA, _ckpt, _log_to
    from .sample import generate
    from .train import load_ckpt, train
    from ..endless.genres import GENRES
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    log = _log_to(out / 'finetune.log')
    log(f"expert iteration {vars(a)}")
    genres = a.genres or list(GENRES)
    cur = _ckpt(a.run)
    pool: list = []                                       # (tokens, genre, weight) kept over the rounds
    hist = []
    for rnd in range(a.rounds + 1):
        model, vocab, _ = load_ckpt(cur)
        row = {'round': rnd, 'ckpt': str(cur), 'genres': {}}
        kept = []
        for gi, g in enumerate(genres):
            seqs = generate(model, vocab, {g: 1.0}, a.n, temperature=a.temp, seed=1000 * rnd + gi)
            res = measure_many(seqs, g, seed0=500_000 + 10_000 * rnd)
            row['genres'][g] = {'rates': rates(res), 'score': score_stats(res)}
            log(f"round {rnd} {g}: {json.dumps(row['genres'][g])}")
            ok = sorted(((r['score'], s) for r, s in zip(res, seqs) if r['status'] == 'ok'), key=lambda x: -x[0])
            kept += [(s, g, 1.0) for _, s in ok[:max(1, int(a.keep * len(seqs)))]]
            with open(out / f"round{rnd}-{g}.jsonl", 'w', encoding='utf-8') as f:
                for s, r in zip(seqs, res):
                    f.write(json.dumps(dict(r, tokens=s)) + '\n')
        hist.append(row)
        (out / 'history.json').write_text(json.dumps(hist, indent=1), encoding='utf-8')
        if rnd == a.rounds:
            break
        pool += kept
        del model
        torch.cuda.empty_cache()
        rd = out / f"r{rnd + 1}"
        t0 = time.time()
        train(rd, [DATA[0]], init=str(cur), top=a.replay, extra=pool, max_steps=a.steps, lr=a.lr, warmup=50,
              status=('ok',), genres=genres, eval_every=10 ** 9, log=log)
        log(f"round {rnd + 1}: fine-tuned on {len(pool)} kept + the teacher's top {a.replay:.0%} in "
            f"{time.time() - t0:.0f} s")
        cur = rd / 'last.pt'
    shutil.copy(cur, out / 'ckpt.pt')
    return 0
