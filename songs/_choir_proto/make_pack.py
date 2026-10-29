"""Stage 1 of the neural-choir prototype: render the vowel choir layers and package the sampler pack.

    python songs/_choir_proto/make_pack.py render [--parts S,A] [--vowels ah,oh]     # DiffSinger layers (cached)
    python songs/_choir_proto/make_pack.py package [--parts ...] [--variants big,...]  # big / section / solo / copies SFZ
    python songs/_choir_proto/make_pack.py measure                                   # phasing + coverage report

Everything goes to D:/Repos/AgentSound/local/choir ($CHOIR_PROTO_DIR): work/layers (one wav per virtual singer and note), pack/
(SFZ + samples + SOURCE.json + INDEX.json), pack/coverage.json, pack/phasing.json. LOCAL ONLY (licences: choir.py docstring).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import choir as C  # noqa: E402

C.setup_env()
import numpy as np  # noqa: E402
import choir_audio as A  # noqa: E402

N = dict(C.N_BIG)
"""Virtual singers per part (stage 3: C.N_BIG; --singers old = stage 1's C.N_OLD). Measured: Hanami ~3.7 s a take
at 20 diffusion steps, ~1.8 s at 10; TIGER ~5.8 s on the GPU (vocoder-bound), ~3.3 s with its vocoder on 4 CPU
threads ($CHOIR_VOCODER_CPU=tiger:4)."""


def cmd_render(parts, vowels) -> None:
    times = {}
    p = C.PACK / f'render_times_{"".join(parts)}.json'
    if p.is_file():
        times = json.loads(p.read_text(encoding='utf-8'))
    for part in parts:
        t = C.render_layers(part, vowels, N[part])
        n = sum(len(C.dynamics(part, v)) for v in vowels) * len(C.PARTS[part]['notes']) * N[part]
        print(f"{part}: {t:.0f} s")
        if t > 1:
            times[f'{part}:{",".join(vowels)}'] = {'seconds': round(t, 1), 'layers': n}
    C.PACK.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(times, indent=1) + '\n', encoding='utf-8')


def cmd_package(parts, vowels, variants=('big',)) -> None:
    cov = {}
    for part in parts:
        cov.update(C.package([part], vowels, N[part], variants=variants))
    C.write_source(('S', 'A', 'T', 'B'))         # the pack's SOURCE always names both banks
    from agentsound import catalog
    catalog.pack_index(C.PACK, rebuild=True)
    f = C.PACK / 'coverage.json'
    old = json.loads(f.read_text(encoding='utf-8')) if f.is_file() else {}
    for part, d in cov.items():
        old.setdefault(part, {}).update(d)
    f.write_text(json.dumps(old, indent=1) + '\n', encoding='utf-8')
    print(f"pack: {C.PACK}")


def cmd_measure() -> None:
    """Phasing: the section (N real takes) vs one take x N (same onsets, pans, gains) vs the solo; plus the
    layers' pairwise correlation. Coverage: HNR per part over the SATB range."""
    out = {}
    for part in ('S', 'A', 'T', 'B'):
        P = C.PARTS[part]
        n = N[part]
        res = []
        for m in P['notes'][1::3]:
            for v in ('ah', 'oo'):
                if not all(C.layer_path(part, v, 'mf', m, i).is_file() for i in range(n)):
                    continue
                L = [A.mono(A.read_wav(C.layer_path(part, v, 'mf', m, i))[0]) for i in range(n)]
                a, b = int((C.PRE_S + 0.4) * C.SR), int((C.PRE_S + C.NOTE_S - 0.6) * C.SR)
                L = [x * 10 ** ((-20.0 - A.rms_db(x[a:b])) / 20) for x in L]      # as section() sums them
                sgs = C.singers(part, n)
                g = [10 ** (s.gain_db / 20) for s in sgs]
                real = [x * gg for x, gg in zip(L, g)]
                cop = [np.concatenate([np.zeros(int(s.onset_ms / 1000 * C.SR)), L[0]]) * gg for s, gg in zip(sgs, g)]
                cop = [x[:min(len(y) for y in cop)] for x in cop]
                sec, naive = A.comb_ripple_db(real), A.comb_ripple_db(cop)
                cc = [A.corr(L[i], L[j]) for i in range(n) for j in range(i + 1, n)]
                res.append({'note': m, 'vowel': v, 'section': sec, 'copies': naive,
                            'pair_corr_median': round(float(np.median(cc)), 3),
                            'pair_corr_max': round(float(np.max(cc)), 3)})
        if res:
            out[part] = {'rows': res,
                         'section_ripple_db': round(float(np.mean([r['section']['ripple_db'] for r in res])), 2),
                         'copies_ripple_db': round(float(np.mean([r['copies']['ripple_db'] for r in res])), 2),
                         'section_notch_db': round(float(np.mean([r['section']['notch_db'] for r in res])), 2),
                         'copies_notch_db': round(float(np.mean([r['copies']['notch_db'] for r in res])), 2),
                         'pair_corr': round(float(np.median([r['pair_corr_median'] for r in res])), 3)}
            o = out[part]
            print(f"{part}: comb ripple section {o['section_ripple_db']} dB vs copies {o['copies_ripple_db']} dB; "
                  f"1% notch {o['section_notch_db']} vs {o['copies_notch_db']} dB; layer corr {o['pair_corr']}")
    (C.PACK / 'phasing.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    f = C.PACK / 'coverage.json'
    if f.is_file():
        cov = json.loads(f.read_text(encoding='utf-8'))
        for part, vs in cov.items():
            lo, hi = C.SATB_RANGE[part]
            for v, rows in vs.items():
                xs = sorted((int(k.split('_')[1]), k.split('_')[0], r['hnr_db']) for k, r in rows.items())
                good = [m for m, d, h in xs if d == 'mf' and h >= 25]
                weak = [m for m, d, h in xs if d == 'mf' and h < 25]
                print(f"  {part} {v}: SATB {lo}-{hi}; mf HNR>=25 dB at {good}; weak {weak}")


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['render', 'package', 'measure', 'all'])
    ap.add_argument('--parts', default='S,A,T,B')
    ap.add_argument('--vowels', default='ah,oh,oo,mm,ee')
    ap.add_argument('--singers', choices=['big', 'old'], default='big')
    ap.add_argument('--variants', default='big', help='big,big_nobass,section,solo,copies')
    a = ap.parse_args(argv[1:])
    if a.singers == 'old':
        N.update(C.N_OLD)
    parts, vowels = a.parts.split(','), a.vowels.split(',')
    t = time.time()
    if a.cmd in ('render', 'all'):
        cmd_render(parts, vowels)
    if a.cmd in ('package', 'all'):
        cmd_package(parts, vowels, tuple(a.variants.split(',')))
    if a.cmd in ('measure', 'all'):
        cmd_measure()
    print(f"done in {time.time() - t:.0f} s")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
