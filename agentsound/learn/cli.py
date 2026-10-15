"""`python -m agentsound learn ...`: the learned generator (docs/LEARNED_GENERATOR.md).

    learn export  --per-genre N --workers W --out DATA        the teacher dataset (no audio)
    learn train   --data DATA --run RUN [--top 0.5]            train the transformer (torch)
    learn sample  --run RUN --genre new-age-piano[=0.7,jazz-piano=0.3] --n 16 --out DIR
                  [--spread] [--header-temp T]                 a set covering the genre's headers; header temperature
    learn eval    --run RUN --data DATA --n 64                 validity / score / tells / novelty vs the teacher
    learn finetune --run RUN --data DATA ...                   expert iteration (generate -> score -> keep -> train)
    learn rl      --run RUN ...                                GRPO with composer.score as the reward
    learn render  --tokens FILE.json --out DIR                 perform + render a student piece (engine)
Torch is only imported by train / sample / eval / finetune / rl (the CUDA venv: D:/venvs/agentsound-ears).
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ROOT = Path(os.environ.get('AGENTSOUND_LEARN', 'D:/agentsound-learn'))


def add_parser(sub) -> None:
    p = sub.add_parser('learn', help='the learned generator: export the endless teachers, train / sample / evaluate '
                                     'a small transformer (agentsound.learn; docs/LEARNED_GENERATOR.md)')
    lp = p.add_subparsers(dest='learn_cmd', required=True)
    e = lp.add_parser('export', help='compose + perform + score endless tunes of every genre (no audio) to JSONL')
    e.add_argument('--out', default=str(DEFAULT_ROOT / 'data'))
    e.add_argument('--genres', nargs='*', help='default: every endless genre')
    e.add_argument('--per-genre', type=int, default=1000)
    e.add_argument('--seed0', type=int, default=0)
    e.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    e.add_argument('--chunk', type=int, default=100)
    e.add_argument('--tokens-only', action='store_true', help='compose + the arc check only (no performance, no score)')
    e.set_defaults(func=cmd_export)
    from . import run as R
    for name, what in (('train', 'train the student (torch)'), ('sample', 'sample + measure student pieces'),
                       ('eval', 'the evaluation tables vs the teacher'), ('finetune', 'expert iteration'),
                       ('rl', 'GRPO with composer.score as the reward'), ('render', 'perform + render student pieces'),
                       ('blind', 'blind-round packets: student vs teacher vs references')):
        q = lp.add_parser(name, help=what)
        R.add_args(name, q)
        q.set_defaults(func=_forward(name))


def _forward(name):
    def run(args) -> int:
        from . import run as R
        return R.main(name, args)
    return run


def cmd_export(args) -> int:
    from ..endless.genres import GENRES
    from .export import export
    export(Path(args.out), args.genres or list(GENRES), args.per_genre, args.workers, seed0=args.seed0,
           chunk=args.chunk, full=not args.tokens_only)
    return 0
