"""Rendering student pieces through the existing players + engine (the endless runner's render_tune: gate, mp3,
cover, credits), and the blind round's packets (student vs teacher vs the composed references, anonymized with the
new-age packet writer of songs/_blind)."""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from types import SimpleNamespace

MAIN = Path(os.environ.get('AGENTSOUND_MAIN', 'D:/Repos/AgentSound'))


def _env():
    os.environ.setdefault('AGENTSOUND_ENGINE', str(MAIN / 'build' / 'agentsound.exe'))
    os.environ.setdefault('AGENTSOUND_SAMPLES', str(MAIN / 'assets' / 'samples'))
    os.environ.setdefault('AGENTSOUND_VOICES', str(MAIN / 'assets' / 'voices'))


def args_render(ap) -> None:
    ap.add_argument('--rows', required=True, help='a JSONL of sample / eval rows (tokens, status, score)')
    ap.add_argument('--player', help='the genre whose players perform it (default: the row\'s player / the file name)')
    ap.add_argument('--pick', nargs='*', type=int, help='row indices (default: --best)')
    ap.add_argument('--best', type=int, default=1, help='render the N best-scored rows that pass every check')
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='', help='a note after the title (default none)')
    ap.add_argument('--keep', action='store_true', help='keep mix.wav and the render json (the blind packets need it)')


def render_rows(rows: list[dict], player: str, out: Path, *, keep=False, name='student', log=print) -> list[dict]:
    """Perform + render rows (each: tokens, perform_seed / an index seed) -> the render_tune infos."""
    _env()
    from ..endless.composer import score
    from ..endless.genres import get
    from ..endless.perform import build
    from ..endless.run import render_tune
    from . import tokens as T
    g = get(player)
    out.mkdir(parents=True, exist_ok=True)
    args = SimpleNamespace(engine=None, keep=keep, by_style=False, mood=None, swing=None)
    infos = []
    for k, r in enumerate(rows):
        seed = r.get('perform_seed', 0)
        tune = T.decode(r['tokens'], g, seed=seed)
        tune.title = f"{tune.title} ({name})" if name else tune.title
        song = build(tune, g)
        sc = score(song, tune, g)
        info = render_tune(g, seed, out, k + 1, args, log,
                           made={'tune': tune, 'song': song, 'score': sc, 'plan': None, 'seed': seed})
        if info:
            info.pop('_song', None)
            d = Path(info['files']['mp3']).parent
            (d / 'tokens.json').write_text(json.dumps({'tokens': r['tokens'], 'player': player, 'seed': seed,
                                                       'blend': r.get('blend')}), encoding='utf-8')
            infos.append(info)
        else:
            log(f"row {k}: the render gate rejected it")
    return infos


def cmd_render(a) -> int:
    rows = [json.loads(x) for x in Path(a.rows).read_text(encoding='utf-8').splitlines() if x.strip()]
    player = a.player or rows[0].get('player') or Path(a.rows).stem
    if a.pick:
        sel = [rows[i] for i in a.pick]
    else:
        sel = sorted((r for r in rows if r.get('status') == 'ok'), key=lambda r: -r['score'])[:a.best]
    for i, r in enumerate(sel):
        r.setdefault('perform_seed', 7000 + i)
    infos = render_rows(sel, player, Path(a.out), keep=a.keep, name=a.name)
    for i in infos:
        print(f"{i['files']['mp3']}  score {i['score']['score']}  {i['lufs']} LUFS")
    return 0


# ------------------------------------------------------------------------------------------------ the blind round

def args_blind(ap) -> None:
    ap.add_argument('--student', required=True, help='rendered student tune folders (render --keep), a parent dir')
    ap.add_argument('--teacher', required=True, help='rendered teacher tune folders (endless --keep), a parent dir')
    ap.add_argument('--n', type=int, default=4, help='pieces per source')
    ap.add_argument('--out', required=True, help='the judges\' folder (JUDGE.md + packets/); KEY.json goes next to it')
    ap.add_argument('--id-seed', default='learn-blind-1')
    ap.add_argument('--composed', nargs='*', help='the composed references (song folders under --composed-root, '
                                                  'each with out/report.json); default the packet writer first N')
    ap.add_argument('--composed-root', help='where the references live (default: the main checkout songs/)')


def _load_student(folder: Path):
    from ..endless.genres import get
    from ..endless.perform import build
    from . import tokens as T
    d = json.loads((folder / 'tokens.json').read_text(encoding='utf-8'))
    info = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
    g = get(d['player'])
    tune = T.decode(d['tokens'], g, seed=d['seed'], title=info['title'])
    song = build(tune, g)
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
    return song, tune.key, tune.tempo, list(song.endless_timeline), report


def cmd_blind(a) -> int:
    import importlib.util
    import shutil
    import sys
    blind = Path(__file__).resolve().parents[2] / 'songs' / '_blind'
    sys.path.insert(0, str(blind))
    spec = importlib.util.spec_from_file_location('mpn', blind / 'make_packets_newage.py')
    mpn = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mpn)
    out = Path(a.out)
    (out / 'packets').mkdir(parents=True, exist_ok=True)
    for f in (out / 'packets').glob('*.txt'):
        f.unlink()
    shutil.copy(blind / 'JUDGE_NEWAGE.md', out / 'JUDGE.md')
    root = Path(a.composed_root) if a.composed_root else MAIN / 'songs'
    comp = [('composed', root / c, mpn.load_composed) for c in (a.composed or mpn.COMPOSED[:a.n])]
    stu = [('student', p, _load_student) for p in sorted(Path(a.student).iterdir()) if (p / 'tokens.json').is_file()]
    tea = [('teacher', p, mpn.load_generated) for p in sorted(Path(a.teacher).iterdir()) if (p / 'tune.json').is_file()]
    ps = comp + stu[:a.n] + tea[:a.n]
    order = list(range(len(ps)))
    random.Random(a.id_seed + ':order').shuffle(order)
    rng = random.Random(a.id_seed)
    ids = []
    while len(ids) < len(ps):
        x = ''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(4))
        if x not in ids:
            ids.append(x)
    key = {}
    for pid, i in zip(ids, order):
        kind, folder, loader = ps[i]
        song, k, tempo, tl, report = loader(folder)
        render = song.compile()
        mpn.check_notes(folder.name, render, report)
        (out / 'packets' / f"{pid}.txt").write_text(mpn.packet(song, k, tempo, tl, report, render), encoding='utf-8')
        key[pid] = {'source': kind, 'path': str(folder)}
        print(f"wrote packets/{pid}.txt")
    (out.parent / f"KEY-{out.name}.json").write_text(json.dumps(dict(sorted(key.items())), indent=1), encoding='utf-8')
    return 0
