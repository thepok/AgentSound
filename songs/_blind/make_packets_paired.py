"""A PAIRED blind round (new-age round g14 on, the orchestra round o2 on): the same set seeds rendered by two code
versions, judged with the references, so the code's effect is read per seed apart from the set's luck.

    # 1. per code version, in a checkout of that code (the packet is rebuilt from the tune.json by ITS composer):
    python songs/_blind/make_packets_paired.py dump OUT.json LABEL=FOLDER ... [--orch]  # endless tune folders / songs
    # 2. here: the IDs, the panels, the packets and the KEY
    python songs/_blind/make_packets_paired.py deal ROUND A.json B.json ... [--panels 2] [--split] [--orch]

`dump` writes {label: {text, source, path, title, moves}} through make_packets_newage's ONE extraction path (--orch:
make_packets_orch's - the orchestra packet; the packet text is the same function for every piece; a label
'code-slot' pairs the pieces: 'g14-003' and 'g12-003' are seed slot 003 by two codes, a label 'ref-*' a
hand-composed reference). `deal` shuffles the IDs (seed blind-new-age-ROUND, --orch blind-orch-ROUND), splits the
slots over the panels (slot k to panel k mod n: both halves of a pair with the same judges, every panel all the
references; round g15 --split: slot k by the c-th code (sorted) to panel (k + c) mod n - the two versions of a slot
with different judges, each panel half of each code: score_round.py --paired pairs them by the judge's lens across
the panels), writes packets_newage/<ID>.txt, KEY_newage.json ({ID: source, path, title, moves, code, slot, panel})
and packets_newage/PANELS.json ({panel: [IDs]}; the judges' folders get their panel's packets only -
judge_newage.py ROUND ROOT --panel P); --orch: packets_orch/, KEY_orch.json, judge_orch.py ROUND ROOT --quality
--panel P.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def dump(out: Path, items: list, orch: bool = False) -> int:
    argv, sys.argv = sys.argv, [sys.argv[0], 'g14']      # (make_packets_newage reads its round from argv)
    sys.path.insert(0, str(HERE))
    if orch:
        import make_packets_orch as mo
    else:
        import make_packets_newage as mp
    sys.argv = argv
    res = {}
    for it in items:
        label, folder = it.split('=', 1)
        folder = Path(folder).resolve()
        kind = 'composed' if (folder / 'song.py').exists() else 'generated'
        if orch:
            song, report = mo.load(folder, kind == 'generated')
            render = song.compile()
            mo.check_notes(folder.name, render, report)
            labels = {name: f"S{k + 1}" for k, (name, _, _) in enumerate(mo.sections(song))}
            text = mo.packet(song, report, render, labels)
        else:
            song, k, tempo, tl, report = (mp.load_composed if kind == 'composed' else mp.load_generated)(folder)
            render = song.compile()
            mp.check_notes(folder.name, render, report)
            text = mp.packet(song, k, tempo, tl, report, render)
        d = {'text': text, 'source': kind,
             'path': folder.relative_to(ROOT).as_posix() if folder.is_relative_to(ROOT) else folder.as_posix()}
        if kind == 'generated':
            info = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
            d['title'] = info.get('title')
            sg = getattr(song, 'endless_signature', None) or {}
            d['moves'] = [[x['move'], str(x['role']), *x['bars']] for x in sg.get('statements') or ()]
        res[label] = d
        print(f"{label}: {folder.name}")
    out.write_text(json.dumps(res, indent=1) + '\n', encoding='utf-8')
    return 0


def deal(rnd: str, files: list, panels: int, split: bool = False, orch: bool = False) -> int:
    allp = {}
    for f in files:
        allp.update(json.loads(Path(f).read_text(encoding='utf-8')))
    labels = sorted(allp)
    seed = f"blind-orch-{rnd}" if orch else f"blind-new-age-{rnd}"
    rng = random.Random(seed)
    ids = []
    while len(ids) < len(labels):
        x = ''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(4))
        if x not in ids:
            ids.append(x)
    order = list(range(len(labels)))
    random.Random(f"{seed}:order").shuffle(order)
    out_dir = HERE / ('packets_orch' if orch else 'packets_newage')
    out_dir.mkdir(exist_ok=True)
    for f in out_dir.glob('*.txt'):
        f.unlink()
    key, pan = {}, {str(p + 1): [] for p in range(panels)}
    codes = sorted({lab.partition('-')[0] for lab in labels} - {'ref'})
    for pid, i in zip(ids, order):
        lab = labels[i]
        d = allp[lab]
        code, _, slot = lab.partition('-')
        (out_dir / f"{pid}.txt").write_text(d['text'], encoding='utf-8')
        e = {k: v for k, v in d.items() if k != 'text'}
        if code != 'ref':
            # (round g15, --split: the two codes of a slot in DIFFERENT panels - slot k by code c to panel
            # (k + c) mod n: no judge sees both versions of a set plan side by side, every panel half of each code)
            k_ = int(slot) + (codes.index(code) if split else 0) if slot.isdigit() else 0
            e.update(code=code, slot=slot, panel=str(k_ % panels + 1))
            pan[e['panel']].append(pid)
        else:
            e['panel'] = 'all'
            for p in pan:
                pan[p].append(pid)
        key[pid] = e
        print(f"{pid}  {lab:<12} panel {e['panel']}")
    (HERE / ('KEY_orch.json' if orch else 'KEY_newage.json')).write_text(
        json.dumps(dict(sorted(key.items())), indent=1) + '\n', encoding='utf-8')
    (out_dir / 'PANELS.json').write_text(json.dumps({p: sorted(v) for p, v in pan.items()}, indent=1) + '\n',
                                         encoding='utf-8')
    return 0


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in ('dump', 'deal'):
        print(__doc__)
        return 2
    orch = '--orch' in sys.argv
    args = [a for a in sys.argv[2:] if a != '--orch']
    if sys.argv[1] == 'dump':
        return dump(Path(args[0]), args[1:], orch)
    split = '--split' in args
    args = [a for a in args if a != '--split']
    n = int(args[args.index('--panels') + 1]) if '--panels' in args else 2
    files = [a for i, a in enumerate(args[1:], 1) if a != '--panels' and (i < 2 or args[i - 1] != '--panels')]
    return deal(args[0], files, n, split, orch)


if __name__ == '__main__':
    sys.exit(main())
