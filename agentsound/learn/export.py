"""The teacher dataset: endless tunes of every genre composed + performed WITHOUT audio, each with its tokens, the
runner's checks (the arc check, the breath gate), composer.score and every notes-level metric (the tells).

    python -m agentsound learn export --per-genre 8000 --workers 11 --out D:/agentsound-learn/data

One JSONL line per piece in OUT/<genre>/<worker-chunk>.jsonl: {genre, seed, status ('ok' | 'arc' | 'breath' |
'compose' | 'token' | 'tok' = tokens only, --tokens-only), tokens (space-joined; schema 2: with the players' Arr
block), score, mean, hard, metrics, header (mood / feel / form / key / tempo)}.
Pieces failing the arc check are not performed (as the runner does); tokens are kept for them.
"""
from __future__ import annotations

import json
import time
from pathlib import Path


def measure(tune, genre) -> dict:
    """Perform (no audio) and score a tune exactly as the runner's best-of-N does: the breath gate, then
    composer.score; plus every metric score_metrics measures (the score's table and the tells outside it)."""
    from ..endless.composer import score, score_metrics, score_style
    from ..endless.perform import build
    from ..endless.run import breath_gate
    song = build(tune, genre)
    early = breath_gate(genre, song)
    style = score_style(song, tune, genre)
    m = score_metrics(song, tune, style)
    sc = score(song, tune, genre, metrics=m, style=style)
    return {'breath': early, 'score': sc['score'], 'mean': sc['mean'], 'hard': sc['hard'], 'metrics': m,
            'song': song}


def one(genre_name: str, seed: int, full: bool = True) -> dict:
    from ..endless import compose
    from ..endless.composer import shape
    from ..endless.genres import get
    from ..endless.perform import arrange
    from ..theory import ComposeError, PackMissingError
    from . import tokens as T
    g = get(genre_name)
    rec = {'genre': genre_name, 'seed': seed}
    try:
        tune = compose(g, seed)
    except PackMissingError:                        # an install problem, not a bad seed: stop the export
        raise
    except ComposeError as e:
        return dict(rec, status='compose', error=str(e)[:200])
    try:                                            # (the players' arrangement drawn: the Arr block, schema 2)
        rec['tokens'] = ' '.join(T.encode(tune, arrange(tune, g), schema=T.SCHEMA))
    except T.TokenError as e:
        return dict(rec, status='token', error=str(e)[:200])
    rec['header'] = {'mood': tune.mood, 'feel': tune.feel, 'form': tune.form, 'key': tune.key, 'tempo': tune.tempo}
    if shape(tune)['issues']:
        return dict(rec, status='arc')
    if not full:                                    # (tokens only: the arc check passed, not performed)
        return dict(rec, status='tok')
    try:
        m = measure(tune, g)
    except PackMissingError:                        # an install problem, not a bad seed: stop the export
        raise
    except ComposeError as e:
        return dict(rec, status='compose', error=str(e)[:200])
    m.pop('song')
    rec.update(status='breath' if m['breath'] else 'ok', score=m['score'], mean=m['mean'], hard=m['hard'],
               metrics=m['metrics'])
    return rec


def _chunk(job):
    genre, seeds, path, full = job
    t0 = time.perf_counter()
    n = 0
    with open(path, 'w', encoding='utf-8') as f:
        for s in seeds:
            try:
                rec = one(genre, s, full)
            except Exception as e:                      # (a player bug on one seed must not stop the export)
                rec = {'genre': genre, 'seed': s, 'status': 'error', 'error': f"{type(e).__name__}: {e}"[:200]}
            f.write(json.dumps(rec) + '\n')
            n += 1
    return genre, n, time.perf_counter() - t0


def export(out: Path, genres: list[str], per_genre: int, workers: int, seed0: int = 0, chunk: int = 100,
           full: bool = True, log=print) -> None:
    """Export per_genre seeds (seed0 ..) of every genre with a process pool; resumable (finished chunks are kept).
    full=False: tokens + the arc check only (status 'tok': ~50x faster; not performed, not scored)."""
    from .evaluate import cpu_pool
    jobs = []
    for g in genres:
        d = Path(out) / g
        d.mkdir(parents=True, exist_ok=True)
        for a in range(seed0, seed0 + per_genre, chunk):
            p = d / f"{a:08d}.jsonl"
            if p.exists() and sum(1 for _ in p.open(encoding='utf-8')) == min(chunk, seed0 + per_genre - a):
                continue
            jobs.append((g, list(range(a, min(a + chunk, seed0 + per_genre))), str(p), full))
    log(f"export: {len(jobs)} chunks of {chunk} seeds, {workers} workers -> {out}")
    t0 = time.perf_counter()
    done = 0
    with cpu_pool(workers) as pool:
        for g, n, dt in pool.imap_unordered(_chunk, jobs):
            done += n
            el = time.perf_counter() - t0
            log(f"  {g}: {n} pieces in {dt:.0f} s; total {done} in {el:.0f} s ({done / el:.2f} pieces/s)")


def load(root: Path, genres=None, status=('ok',)):
    """Every exported record (of these genres / statuses) from the JSONL shards."""
    root = Path(root)
    for d in sorted(root.iterdir()):
        if not d.is_dir() or (genres and d.name not in genres):
            continue
        for p in sorted(d.glob('*.jsonl')):
            with p.open(encoding='utf-8') as f:
                for line in f:
                    rec = json.loads(line)
                    if status is None or rec.get('status') in status:
                        yield rec
