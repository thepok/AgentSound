"""Re-score saved measure_newage.py results with the CURRENT new-age table (before / after a table change).

    python songs/_blind/rescore_newage.py RESULT.json [RESULT2.json ...]

Prints per file: the generated tunes' score mean / sd / min / max, the best-of-8 gain per block of 8 seeds, the
references' scores and the gap between the references' mean and the generated mean (the score's separation).
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound.endless import composer  # noqa: E402
from agentsound.endless.genres import SCORES  # noqa: E402


def main() -> int:
    for f in sys.argv[1:]:
        d = json.loads(Path(f).read_text(encoding='utf-8'))
        sc = {int(k): composer.score(None, metrics=r['metrics'], table=SCORES['new-age'], style='new-age')['score']
              for k, r in d['rows'].items()}
        xs = [sc[k] for k in sorted(sc)]
        seeds = sorted(sc)
        gains = [max(sc[s] for s in seeds[i:i + 8]) - st.mean(sc[s] for s in seeds[i:i + 8])
                 for i in range(0, len(seeds) - 7, 8)]
        refs = {n: composer.score(None, metrics=r['metrics'], table=SCORES['new-age'], style='new-age')['score']
                for n, r in (d.get('refs') or {}).items()}
        line = (f"{f}: generated mean {st.mean(xs):.1f} sd {st.pstdev(xs):.1f} min {min(xs):.1f} max {max(xs):.1f}; "
                f"best-of-8 gain {', '.join(f'{g:.1f}' for g in gains)}")
        if refs:
            line += (f"; references {', '.join(f'{v:.1f}' for v in refs.values())} (mean {st.mean(refs.values()):.1f},"
                     f" gap to the generated {st.mean(refs.values()) - st.mean(xs):.1f})")
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
