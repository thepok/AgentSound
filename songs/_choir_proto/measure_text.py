"""Stage 2 measure: how tightly the layers of each choir part sing together (from the singer's own take timelines).

    python songs/_choir_proto/measure_text.py        # after a 'pure' / 'hybrid' build (out/choir_layers.json)

Per part and phrase, every phoneme start of the take timeline (seconds from the phrase's first note) + the layer's lag
(offset_ms) is compared across the layers: the spread (latest - earliest) at the consonants and at the vowels.
"""
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from agentsound.lyrics import VOWELS  # noqa: E402


def main() -> int:
    layers = json.loads((HERE / 'out' / 'choir_layers.json').read_text(encoding='utf-8'))
    out = {}
    for part in sorted({v['part'] for v in layers.values()}, key='SATB'.index):
        tids = [t for t, v in layers.items() if v['part'] == part]
        bank = layers[tids[0]]['voice']
        folder = HERE / 'samples' / 'vocals' / bank
        phrases: dict = {}
        for t in tids:
            for f in sorted(folder.glob(f'{t}-*.json'), key=lambda p: p.stat().st_mtime):
                name = f.stem[len(t) + 1:].rsplit('-', 1)[0]
                phrases.setdefault(name, {})[t] = json.loads(f.read_text(encoding='utf-8'))['timeline']
        cons, vows = [], []
        for name, by in phrases.items():
            if len(by) < 2:
                continue
            toks = {t: by[t]['tokens'] for t in by}
            n = min(len(v) for v in toks.values())
            seqs = {t: [x[0] for x in v[:n]] for t, v in toks.items()}
            ref = next(iter(seqs.values()))
            if any(s != ref for s in seqs.values()):
                print(f"{part} {name}: the layers' phoneme sequences differ - skipped")
                continue
            for i, ph in enumerate(ref):
                if ph in ('SP', 'AP'):
                    continue
                ts = [toks[t][i][1] + layers[t]['offset_ms'] / 1000.0 for t in toks]
                spread = (max(ts) - min(ts)) * 1000.0
                (vows if ph in VOWELS else cons).append(spread)
        if cons:
            out[part] = {'layers': len(tids), 'consonant_spread_ms': {'median': round(st.median(cons), 1),
                                                                      'p90': round(sorted(cons)[int(0.9 * len(cons))], 1),
                                                                      'max': round(max(cons), 1)},
                         'vowel_spread_ms': {'median': round(st.median(vows), 1),
                                             'p90': round(sorted(vows)[int(0.9 * len(vows))], 1),
                                             'max': round(max(vows), 1)}}
            o = out[part]
            print(f"{part} ({o['layers']} layers): consonant onsets spread median {o['consonant_spread_ms']['median']} "
                  f"/ p90 {o['consonant_spread_ms']['p90']} / max {o['consonant_spread_ms']['max']} ms; vowels "
                  f"{o['vowel_spread_ms']['median']} / {o['vowel_spread_ms']['p90']} / {o['vowel_spread_ms']['max']} ms")
    (HERE / 'out' / 'choir_timing.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
