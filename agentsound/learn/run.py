"""The torch-side commands of `python -m agentsound learn` (train / sample / eval / finetune / rl / render)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .cli import DEFAULT_ROOT

DATA = [str(DEFAULT_ROOT / 'data' / 'full'), str(DEFAULT_ROOT / 'data' / 'tok')]


def _log_to(path):
    f = open(path, 'a', encoding='utf-8')

    def log(msg):
        line = time.strftime('%H:%M:%S ') + str(msg)
        print(line, flush=True)
        f.write(line + '\n')
        f.flush()
    return log


def _ckpt(run: str) -> Path:
    p = Path(run)
    return p if p.suffix == '.pt' else p / 'ckpt.pt'


def main(cmd: str, a) -> int:
    return {'train': cmd_train, 'sample': cmd_sample, 'eval': cmd_eval, 'finetune': cmd_finetune, 'rl': cmd_rl,
            'render': cmd_render, 'blind': cmd_blind}[cmd](a)


def add_args(name: str, ap) -> None:
    """The arguments of one subcommand (no torch import: the CLI parser is built from these)."""
    if name in ('finetune', 'rl', 'render', 'blind'):
        from importlib import import_module
        mod = import_module(f".{'improve' if name == 'finetune' else 'render' if name == 'blind' else name}",
                            __package__)
        getattr(mod, f"args_{name}")(ap)
    else:
        globals()[f"args_{name}"](ap)


# ------------------------------------------------------------------------------------------------ train

def args_train(ap) -> None:
    ap.add_argument('--run', required=True)
    ap.add_argument('--data', nargs='*', default=DATA)
    ap.add_argument('--init')
    ap.add_argument('--top', type=float)
    ap.add_argument('--epochs', type=float, default=4.0)
    ap.add_argument('--max-steps', type=int)
    ap.add_argument('--lr', type=float, default=3e-4)
    ap.add_argument('--max-tokens', type=int, default=20000)
    ap.add_argument('--d', type=int, default=512)
    ap.add_argument('--layers', type=int, default=10)
    ap.add_argument('--heads', type=int, default=8)
    ap.add_argument('--dropout', type=float, default=0.1)
    ap.add_argument('--status', nargs='*', default=['ok', 'tok'])
    ap.add_argument('--genres', nargs='*')
    ap.add_argument('--eval-every', type=int, default=500)
    ap.add_argument('--ctx', type=int, default=1152, help='the context in tokens (a longer one grows an --init '
                                                          "checkpoint's position table)")


def cmd_train(a) -> int:
    from .train import train
    Path(a.run).mkdir(parents=True, exist_ok=True)
    log = _log_to(Path(a.run) / 'train.log')
    log(f"train {vars(a)}")
    train(Path(a.run), a.data, init=a.init, top=a.top, epochs=a.epochs, max_steps=a.max_steps, lr=a.lr,
          max_tokens=a.max_tokens, d=a.d, layers=a.layers, heads=a.heads, dropout=a.dropout, status=tuple(a.status),
          genres=a.genres, eval_every=a.eval_every, log=log, ctx=a.ctx)
    return 0


# ------------------------------------------------------------------------------------------------ sample

def args_header(ap) -> None:
    """The set's header control (sample / eval): a separate header temperature, the spread."""
    ap.add_argument('--header-temp', type=float, help='the temperature of the header + plan tokens (everything '
                                                       'before the first harmony part); the notes keep --temp')
    ap.add_argument('--spread', action='store_true', help="force each piece's mood / feel / form / meter / key / "
                    "mode / tempo so the set covers the player genre's values evenly (sample.spread_headers, seeded)")


def set_prompts(a, player: str, n: int, per: int = 1):
    """The forced headers of a set (--spread), or None."""
    from .sample import spread_prompts
    return spread_prompts(player, n, a.seed, per) if a.spread else None


def set_arr(a, player: str, n: int, per: int = 1):
    """The forced Arr tokens of a set (--spread: the layout, the climax kind; a schema-1 checkpoint ignores them), or
    None."""
    from .sample import spread_arr
    return spread_arr(player, n, a.seed, per) if a.spread else None


def args_sample(ap) -> None:
    ap.add_argument('--run', required=True)
    ap.add_argument('--genre', required=True, help="a genre or a blend 'new-age-piano=0.7,jazz-piano=0.3'")
    ap.add_argument('--player', help='the genre whose players perform it (default: the heaviest)')
    ap.add_argument('--n', type=int, default=16)
    ap.add_argument('--temp', type=float, default=1.0)
    ap.add_argument('--top-p', type=float, default=1.0)
    ap.add_argument('--constrain', action='store_true')
    ap.add_argument('--grammar', action='store_true')
    ap.add_argument('--blend-mode', choices=('embed', 'logits'), default='embed')
    ap.add_argument('--best-of', type=int, default=1, help='score N candidates per piece, keep the best')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--out', required=True, help='JSONL of the pieces (tokens, genre, player, measures)')
    args_header(ap)


def cmd_sample(a) -> int:
    from .evaluate import measure_many, variety, variety_line
    from .sample import generate, parse_blend
    from .train import load_ckpt
    model, vocab, _ = load_ckpt(_ckpt(a.run))
    blend = parse_blend(a.genre)
    player = a.player or max(blend, key=blend.get)
    seqs = generate(model, vocab, blend, a.n * a.best_of, player=player, temperature=a.temp, top_p=a.top_p,
                    constrain=a.constrain, seed=a.seed, grammar=a.grammar, blend_mode=a.blend_mode,
                    prompt=set_prompts(a, player, a.n, a.best_of), header_temp=a.header_temp,
                    arr_force=set_arr(a, player, a.n, a.best_of))
    res = measure_many(seqs, player, seed0=a.seed * 100000)
    rows = [dict(r, tokens=s, blend=blend, player=player, perform_seed=a.seed * 100000 + i)
            for i, (s, r) in enumerate(zip(seqs, res))]
    if a.best_of > 1:
        rows = [max(rows[k * a.best_of:(k + 1) * a.best_of], key=lambda r: r.get('score') or -1)
                for k in range(a.n)]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    sc = [r['score'] for r in rows if r.get('status') == 'ok']
    print(f"{len(rows)} pieces, {len(sc)} pass every check, score mean "
          f"{sum(sc) / max(1, len(sc)):.1f} -> {a.out}")
    print(variety_line(variety([r['tokens'] for r in rows if r.get('status') != 'invalid'], player)))
    return 0


# ------------------------------------------------------------------------------------------------ eval

def teacher_records(genre: str, n: int, roots=None, split: str | None = None) -> list[dict]:
    """The teacher's measured pieces of a genre (data/full; every status: the check rates count)."""
    from .data import split_of
    from .export import load
    out = []
    for r in load(Path(roots or DATA[0]), genres=[genre], status=None):
        if r.get('status') in ('compose', 'token', 'error'):
            continue
        if split and split_of(r['genre'], r['seed']) != split:
            continue
        out.append(r)
        if len(out) >= n:
            break
    return out


def train_index(genre: str, limit: int = 30000):
    from .data import split_of
    from .evaluate import Index
    from .export import load
    seqs = []
    for root in DATA[1:]:              # (the base model's training set: data/tok)
        if not Path(root).is_dir():
            continue
        for r in load(Path(root), genres=[genre], status=('ok', 'tok')):
            if split_of(r['genre'], r['seed']) == 'train':
                seqs.append(r['tokens'].split())
            if len(seqs) >= limit:
                break
    return Index(seqs)


def evaluate_set(rows: list[dict], genre: str, teacher: list[dict], index=None, held=None) -> dict:
    """One genre's table: rates, score stats, the student vs teacher metric distances (scored / unscored tells),
    novelty against the training set, diversity."""
    from ..endless.genres import GENRES
    from .evaluate import diversity, metric_table, rates, score_stats, unscored, variety
    style = GENRES[genre].style
    rep = {'rates': rates(rows), 'score': score_stats(rows), 'teacher_rates': rates(teacher),
           'teacher_score': score_stats(teacher)}
    tm = next((r['metrics'] for r in teacher if r.get('status') == 'ok'), {})
    from ..endless.genres import SCORES
    rep['metrics_scored'] = metric_table(rows, teacher, [k for k in SCORES[style] if k in tm])
    rep['metrics_unscored'] = metric_table(rows, teacher, unscored(style, tm))
    seqs = [r['tokens'] for r in rows if r.get('status') != 'invalid']
    if index is not None and seqs:
        nov = [index.novelty(s) for s in seqs]
        rep['novelty'] = {k: round(sum(x[k] for x in nov) / len(nov), 3) for k in ('ngram_seen', 'bar_seen',
                                                                                 'nn_jaccard', 'copy')}
        if held:
            hn = [index.novelty(s) for s in held]
            rep['teacher_novelty'] = {k: round(sum(x[k] for x in hn) / len(hn), 3)
                                      for k in ('ngram_seen', 'bar_seen', 'nn_jaccard', 'copy')}
    rep['diversity'] = diversity(seqs) if seqs else None
    rep['variety'] = variety(seqs, genre)
    if held:
        rep['teacher_diversity'] = diversity(held[:len(seqs) or 64])
        rep['teacher_variety'] = variety(held[:len(seqs) or 64], genre)
    tseqs = [r['tokens'].split() for r in teacher if r.get('status') == 'ok' and r.get('tokens')]
    if seqs and tseqs and 'Arr' in tseqs[0]:             # (schema 2: the arrangement distributions vs the teacher's)
        from .evaluate import arrangement_table
        rep['arrangement'] = arrangement_table(seqs, tseqs)
    return rep


def args_eval(ap) -> None:
    ap.add_argument('--run', required=True)
    ap.add_argument('--n', type=int, default=64)
    ap.add_argument('--genres', nargs='*')
    ap.add_argument('--blend', nargs='*', default=[], help="extra blends 'new-age-piano=0.7,jazz-piano=0.3'")
    ap.add_argument('--temp', type=float, default=1.0)
    ap.add_argument('--top-p', type=float, default=1.0)
    ap.add_argument('--constrain', action='store_true')
    ap.add_argument('--teacher-n', type=int, default=600)
    ap.add_argument('--no-novelty', action='store_true')
    ap.add_argument('--tag', default='eval')
    ap.add_argument('--best-of', type=int, default=1, help='K candidates per piece, the best by composer.score kept')
    ap.add_argument('--grammar', action='store_true', help='grammar-constrained decoding (only well-formed tokens)')
    ap.add_argument('--retry', type=int, default=1, help="up to K candidates per piece, the first whose lead sheet "
                                                         "passes the composer's cheap checks (no score)")
    ap.add_argument('--blend-mode', choices=('embed', 'logits'), default='embed',
                    help="embed: the genre embeddings mixed; logits: the per-genre next-token log-probs mixed")
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--data', nargs='*', help='the teacher sets: FULL (measured, held out) [TOK ...] (the base '
                                               'training set, for novelty); default ' + ' '.join(DATA))
    args_header(ap)


def cmd_eval(a) -> int:
    from .data import GENRE_NAMES
    from .evaluate import measure_many, variety_line, vram_line
    from .sample import generate, parse_blend
    from .train import load_ckpt
    if a.data:
        DATA[:] = a.data
    ck = _ckpt(a.run)
    out_dir = ck.parent / a.tag
    out_dir.mkdir(parents=True, exist_ok=True)
    log = _log_to(out_dir / 'eval.log')
    model, vocab, meta = load_ckpt(ck)
    report = {'ckpt': str(ck), 'step': meta.get('step'), 'val': meta.get('val'),
              'args': {k: v for k, v in vars(a).items() if isinstance(v, (str, int, float, list, bool, type(None)))},
              'genres': {}, 'blends': {}}

    def rows_for(name: str, blend: dict, player: str) -> list[dict]:
        """The rows of one set (reused from OUT/<name>.jsonl when it is there): best-of-K by score when asked."""
        path = out_dir / f"{name}.jsonl"
        if path.is_file():
            got = [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
            if len(got) == a.n:
                return got
        k = max(1, a.best_of)
        prompts = set_prompts(a, player, a.n, k)
        arrs = set_arr(a, player, a.n, k)
        seqs = generate(model, vocab, blend, a.n * k, player=player, temperature=a.temp, top_p=a.top_p,
                        constrain=a.constrain or len(blend) > 1, seed=a.seed, grammar=a.grammar,
                        blend_mode=a.blend_mode, prompt=prompts, header_temp=a.header_temp, arr_force=arrs)
        if a.retry > 1:                                   # the composer's own budget: the first candidate (of up
            from .evaluate import lead_sheet_ok           # to `retry`) whose lead sheet passes the cheap checks
            tries = [1] * len(seqs)
            bad = [i for i, s in enumerate(seqs) if not lead_sheet_ok(s, player)]
            for r_ in range(1, a.retry):
                if not bad:
                    break
                more = generate(model, vocab, blend, len(bad), player=player, temperature=a.temp, top_p=a.top_p,
                                constrain=a.constrain or len(blend) > 1, seed=a.seed + 77 * r_, grammar=a.grammar,
                                blend_mode=a.blend_mode, header_temp=a.header_temp,
                                prompt=[prompts[i] for i in bad] if prompts else None,
                                arr_force=[arrs[i] for i in bad] if arrs else None)
                for i, s in zip(bad, more):
                    seqs[i] = s
                    tries[i] += 1
                bad = [i for i in bad if not lead_sheet_ok(seqs[i], player)]
            log(f"  retry: {sum(tries) / len(tries):.2f} candidates per piece, {len(bad)} still failing")
        res = measure_many(seqs, player, seed0=10_000 * a.seed)
        rows = [dict(r, tokens=s, perform_seed=10_000 * a.seed + i, player=player, blend=blend)
                for i, (s, r) in enumerate(zip(seqs, res))]
        if k > 1:
            rows = [max(rows[j * k:(j + 1) * k], key=lambda r: (r.get('status') == 'ok', r.get('score') or -1))
                    for j in range(a.n)]
        with open(path, 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(r) + '\n')
        return rows

    for g in a.genres or list(GENRE_NAMES):     # (the student's genres: an endless genre it was not trained on has no
        #                                           conditioning)
        t0 = time.time()
        rows = rows_for(g, {g: 1.0}, g)
        t1 = time.time()
        teacher = teacher_records(g, a.teacher_n)
        held = [r['tokens'].split() for r in teacher_records(g, a.n * 2) if r.get('status') == 'ok'][:a.n]   # (data/full: never trained on)
        idx = None if a.no_novelty else train_index(g)
        rep = evaluate_set(rows, g, teacher, idx, held)
        rep['gen_s'] = round(t1 - t0, 1)
        report['genres'][g] = rep
        log(f"{g}: {json.dumps({k: rep[k] for k in ('rates', 'score', 'teacher_score', 'novelty', 'teacher_novelty') if k in rep})}")
        log(f"  {variety_line(rep['variety'])}" + (f"; teacher {variety_line(rep['teacher_variety'])}"
                                                   if 'teacher_variety' in rep else ''))
    for spec in a.blend:
        blend = parse_blend(spec)
        player = max(blend, key=blend.get)
        rows = rows_for(f"blend-{spec.replace('=', '').replace(',', '_')}", blend, player)
        report['blends'][spec] = blend_report(rows, blend, player, a.teacher_n)
        log(f"blend {spec}: {json.dumps(report['blends'][spec]['summary'])}")
        log(f"  {variety_line(report['blends'][spec]['variety'])}")
    (out_dir / 'report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    log(f"-> {out_dir / 'report.json'}" + (f"; {vram_line()}" if vram_line() else ''))
    return 0


BLEND_KEYS = ('tempo', 'notes_per_bar', 'chord_rate', 'ext_share', 'leap_share', 'range')


def lead_sheet_features(toks: list[str]) -> dict:
    """Genre-telling features of a lead sheet straight from its tokens (no player): tempo, melody notes per bar,
    chords per bar, the share of extended / altered chord qualities, the share of melodic leaps (> 4 semitones), the
    melody's range."""
    from .evaluate import melody_of, note_line
    meter = next((int(t[6:]) for t in toks if t.startswith('Meter_')), 4)
    tempo = next((int(t[6:]) for t in toks if t.startswith('Tempo_')), 0)
    parts = melody_of(toks)
    line = note_line(parts)
    bars = sum(len(p) for p in parts)
    qs, lens, inside = [], [], False
    for i, t in enumerate(toks):
        if t == 'H':
            inside = True
        elif t == 'EndH':
            inside = False
        elif inside and t.startswith('Q_'):
            qs.append(t[2:])
        elif inside and t.startswith('L_'):
            lens.append(int(t[2:]))
    ext = sum(1 for q in qs if any(x in q for x in ('9', '11', '13', 'b5', '#', 'alt', 'o', 'ø'))) / max(1, len(qs))
    pitches = [int(p[2:]) for ps in parts for b in ps for _, p, _ in b]
    return {'tempo': tempo, 'notes_per_bar': len(line) / max(1, bars),
            'chord_rate': len(qs) / max(1e-9, sum(lens) / 12 / meter), 'ext_share': ext,
            'leap_share': sum(1 for x in line[1:] if abs(x[0]) > 4) / max(1, len(line) - 1),
            'range': (max(pitches) - min(pitches)) if pitches else 0}


def blend_report(rows, blend, player, teacher_n) -> dict:
    """Where a blend's pieces land between the parents: per feature the parents' teacher means and the blend's mean,
    and x = (blend - parent B) / (parent A - parent B) (1 = like A, 0 = like B)."""
    from .evaluate import rates, score_stats, variety
    names = sorted(blend, key=lambda k: -blend[k])
    feats = [lead_sheet_features(r['tokens']) for r in rows if r.get('status') != 'invalid']
    parents = {}
    for g in names:
        ts = [lead_sheet_features(r['tokens'].split()) for r in teacher_records(g, teacher_n) if r.get('tokens')]
        parents[g] = {k: sum(f[k] for f in ts) / max(1, len(ts)) for k in BLEND_KEYS}
    me = {k: sum(f[k] for f in feats) / max(1, len(feats)) for k in BLEND_KEYS}
    out = {'blend': blend, 'player': player, 'rates': rates(rows), 'score': score_stats(rows), 'features': {},
           'variety': variety([r['tokens'] for r in rows if r.get('status') != 'invalid'], player)}
    xs = []
    if len(names) == 2:
        A, B = names
        for k in BLEND_KEYS:
            d = parents[A][k] - parents[B][k]
            x = (me[k] - parents[B][k]) / d if abs(d) > 1e-9 else None
            out['features'][k] = {A: round(parents[A][k], 3), B: round(parents[B][k], 3), 'blend': round(me[k], 3),
                                  'x': None if x is None else round(x, 2)}
            if x is not None:
                xs.append(x)
    out['summary'] = {'rates': out['rates'], 'score': out['score'].get('mean'),
                      'variety': out['variety']['variety'],
                      'x_mean': round(sum(xs) / len(xs), 2) if xs else None,
                      'x': {k: v['x'] for k, v in out['features'].items()}}
    return out


# ------------------------------------------------------------------------------------------------ later stages

def cmd_finetune(a) -> int:
    from .improve import cmd_finetune as f
    return f(a)


def cmd_rl(a) -> int:
    from .rl import cmd_rl as f
    return f(a)


def cmd_render(a) -> int:
    from .render import cmd_render as f
    return f(a)


def cmd_blind(a) -> int:
    from .render import cmd_blind as f
    return f(a)

