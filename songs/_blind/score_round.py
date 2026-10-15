"""Score a blind round: the judges' answers against the KEY (nobody else reads the KEY).

    python songs/_blind/score_round.py KEY_newage.json VERDICTS_DIR

VERDICTS_DIR holds one <judge>.md per judge in JUDGE.md's answer format. Prints per judge: right / total, the
confidence range, the misses by kind; then per source kind the verdict counts, and every reason the judges gave for
the GENERATED packets (the tells to fix) with the judge and the packet's source folder name.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse(text: str) -> dict:
    out = {}
    for m in re.finditer(r'^##\s+([A-Z]{4})\s*$(.*?)(?=^##\s|\Z)', text, re.M | re.S):
        body = m.group(2)
        v = re.search(r'verdict:\s*\**\s*(generated|composed)', body, re.I)
        c = re.search(r'confidence:\s*\**\s*(\d+)', body, re.I)
        reasons = re.findall(r'^\s*\d\.\s+(.*)$', body, re.M)
        if v:
            out[m.group(1)] = {'verdict': v.group(1).lower(), 'conf': int(c.group(1)) if c else None,
                               'reasons': reasons}
    return out


def main() -> int:
    here = Path(__file__).resolve().parent
    key = json.loads((here / sys.argv[1]).read_text(encoding='utf-8'))
    vdir = Path(sys.argv[2])
    tot_r = tot_n = comp_r = comp_n = 0
    tells = []
    for f in sorted(vdir.glob('*.md')):
        ans = parse(f.read_text(encoding='utf-8'))
        right = [i for i in key if i in ans and ans[i]['verdict'] == key[i]['source']]
        miss = [i for i in key if i in ans and ans[i]['verdict'] != key[i]['source']]
        confs = [a['conf'] for a in ans.values() if a['conf'] is not None]
        kinds = {}
        for i in miss:
            k = f"{key[i]['source']} called {ans[i]['verdict']}"
            kinds[k] = kinds.get(k, 0) + 1
        print(f"{f.stem:<14} {len(right)}/{len(ans)}  confidence {min(confs) if confs else '-'}-"
              f"{max(confs) if confs else '-'}  misses: {kinds or 'none'}")
        tot_r += len(right)
        tot_n += len(ans)
        if f.stem.startswith('composer'):
            comp_r += len(right)
            comp_n += len(ans)
        for i, a in ans.items():
            if key.get(i, {}).get('source') == 'generated':
                tells.append((f.stem, Path(key[i]['path']).name, a['verdict'], a['conf'], a['reasons']))
    print(f"all judges {tot_r}/{tot_n} = {tot_r / max(1, tot_n):.0%}; composers {comp_r}/{comp_n} = "
          f"{comp_r / max(1, comp_n):.0%}")
    if '--tells' in sys.argv:
        for j, p, v, c, rs in tells:
            print(f"\n[{j}] {p}: {v} {c}")
            for r in rs[:3]:
                print('   - ' + r[:400])
    return 0


if __name__ == '__main__':
    sys.exit(main())
