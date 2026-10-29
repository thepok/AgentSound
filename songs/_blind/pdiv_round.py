"""Round p-div (endless new-age PIANO_DIVERSE on vs off): the per-piece paired panels and the set-level pairs.

    # 0. the renders: per set seed the CLI's own continuous set, best-of-8, once per arm (the same set plan)
    python songs/_blind/shared_plan.py cli ROOT [--flag pdiv] piano --style new-age --count 8 --seed S --out DIR
    # 1. the packets per arm, rebuilt by the code with the arm's flag (make_packets_paired.dump in this process)
    python songs/_blind/pdiv_round.py dump OUT.json [--pdiv] LABEL=FOLDER ...
    # 2. per piece: the IDs and two panels of 7 (deal --split: the two versions of a slot with different judges, every
    #    panel the hidden references), the brief = JUDGE_NEWAGE.md + the template flags + the masterpiece question
    python songs/_blind/pdiv_round.py pieces ROUND JROOT A.json B.json REFS.json
    #    -> JROOT/KEY_newage.json, JROOT/p{1,2}/<lens>/{JUDGE.md, packets/, prompt.txt}; verdicts JROOT/verdicts/<lens>_p<P>.md
    #    scored by: python songs/_blind/score_round.py JROOT/KEY_newage.json JROOT/verdicts --paired on,off
    # 3. the set level: per set pair a DIR with PACKETS_on.json / PACKETS_off.json (8 pieces each, programme order),
    #    7 judges per pair (judge_newage's lenses), X / Y drawn, the reading order balanced (set_round deal --balance)
    python songs/_blind/pdiv_round.py sets ROUND JROOT DIR [DIR ...] [--cleanse] [--two-pass]   (set_round deal's options)
    python songs/_blind/set_round.py score JROOT/SET_KEY.json JROOT/verdicts --codes on,off
Nobody but the scorer reads a KEY; the judges' folders hold their brief and packets only.
"""
from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

TEMPLATE = """Then **template**: the IDs of other packets that follow the SAME PLAN as this one - the same recipe of sections
and left-hand textures in the same order (e.g. the same kind of intro, the same chorus texture, the same build into the
same kind of climax with the same left hand, the same interlude, the same ending gesture), so that the two would sound
like one piece-making formula - or `none`. Name a packet only when the plan itself is shared, not for a common style.
"""


def brief() -> str:
    """JUDGE_NEWAGE.md with the template flags and the masterpiece question (bestofn_newage's)."""
    import bestofn_newage as bn
    src = (HERE / 'JUDGE_NEWAGE.md').read_text(encoding='utf-8')
    src = src.replace("At the end, a section **Count**",
                      TEMPLATE + "\n" + bn.PIECE_EXTRA.strip() + "\n\nAt the end, a section **Count**")
    src = src.replace("shared: <IDs> | none\n",
                      "shared: <IDs> | none\ntemplate: <IDs> | none\nmasterpiece: <1-10>\nmissing: bars <a-b>: ...\n")
    return src


def cmd_dump(out: Path, items: list, pdiv: bool) -> int:
    if pdiv:
        from agentsound.endless import genres
        genres.piano_diverse(True)
    import make_packets_paired as mpp
    return mpp.dump(out, items)


def cmd_pieces(rnd: str, jroot: Path, files: list) -> int:
    import judge_newage as jn
    import make_packets_paired as mpp
    jroot.mkdir(parents=True, exist_ok=True)
    mpp.HERE = jroot                                   # (the packets and the KEY in JROOT, not in the repo)
    mpp.deal(rnd, files, 2, split=True)
    panels = json.loads((jroot / 'packets_newage' / 'PANELS.json').read_text(encoding='utf-8'))
    text = brief()
    (jroot / 'verdicts').mkdir(exist_ok=True)
    for p, ids in panels.items():
        for name in jn.JUDGES:
            d = jroot / f"p{p}" / name
            if d.exists():
                shutil.rmtree(d)
            (d / 'packets').mkdir(parents=True)
            (d / 'JUDGE.md').write_text(text, encoding='utf-8')
            for i in ids:
                shutil.copy(jroot / 'packets_newage' / f"{i}.txt", d / 'packets' / f"{i}.txt")
            pr = jn.prompt(name, d, jroot / 'verdicts' / f"{name}_p{p}.md").replace(
                "then ## Count, then ## Advice", "then ## Count, then ## Advice; every packet with its template, "
                                                 "masterpiece and missing lines")
            (d / 'prompt.txt').write_text(pr, encoding='utf-8')
        print(f"panel {p}: {len(ids)} packets, {len(jn.JUDGES)} judges")
    return 0


def cmd_sets(rnd: str, jroot: Path, dirs: list, cleanse: bool = False, two_pass: bool = False) -> int:
    """The set pairs' judges (set_round.deal_judge: --cleanse the palate cleanser, --two-pass every judge twice,
    the second pass in the other order)."""
    import bestofn_newage as bn
    import judge_newage as jn
    import set_round as sr
    judges = list(jn.JUDGES)
    jroot.mkdir(parents=True, exist_ok=True)
    (jroot / 'verdicts').mkdir(exist_ok=True)
    key = {'round': rnd, 'pairs': {}}
    for p_i, d in enumerate(dirs):
        d = Path(d).resolve()
        packs = {c: json.loads((d / f"PACKETS_{c}.json").read_text(encoding='utf-8')) for c in ('off', 'on')}
        codes = sorted(packs)
        sets = {c: [packs[c][lab] for lab in sorted(packs[c])] for c in codes}
        n = len(sets['on'])
        if len(sets['off']) != n:
            raise SystemExit(f"{d}: the sets differ in length")
        pair = d.name
        key['pairs'][pair] = {'dir': d.as_posix(), 'judges': {},
                              'sets': {c: [x['path'] for x in sets[c]] for c in codes},
                              'titles': {c: [x.get('title') for x in sets[c]] for c in codes}}
        for j_i, name in enumerate(judges):
            rng = random.Random(f"blind-set-{rnd}:{pair}:{name}")
            x_code = codes[rng.randrange(2)]
            first = ('X' if x_code == codes[0] else 'Y') if (j_i + p_i) % 2 == 0 else \
                ('Y' if x_code == codes[0] else 'X')         # (balanced: set_round deal --balance)
            asg = {'X': x_code, 'Y': codes[1 - codes.index(x_code)], 'first': first}
            sr.deal_judge(key['pairs'][pair], jroot, pair, name, sets, asg, bn._set_brief(n),
                          jn.LENS[jn.JUDGES[name]], cleanse=cleanse, two_pass=two_pass)
        print(f"{pair}: {len(judges)} judges" + (' x 2 passes' if two_pass else ''))
    (jroot / 'SET_KEY.json').write_text(json.dumps(key, indent=1) + '\n', encoding='utf-8')
    return 0


def main() -> int:
    a = sys.argv[1:]
    if not a or a[0] not in ('dump', 'pieces', 'sets'):
        print(__doc__)
        return 2
    if a[0] == 'dump':
        pdiv = '--pdiv' in a
        rest = [x for x in a[1:] if x != '--pdiv']
        return cmd_dump(Path(rest[0]), rest[1:], pdiv)
    if a[0] == 'pieces':
        return cmd_pieces(a[1], Path(a[2]).resolve(), a[3:])
    rest = [x for x in a[1:] if x not in ('--cleanse', '--two-pass')]
    return cmd_sets(rest[0], Path(rest[1]).resolve(), rest[2:], cleanse='--cleanse' in a, two_pass='--two-pass' in a)


if __name__ == '__main__':
    sys.exit(main())
