"""Parallel test runner (stdlib only): one `unittest` process per test module, all CPU cores busy.

    python tests/run.py               # all modules, os.cpu_count() workers
    python tests/run.py -j 4 singer   # 4 workers, only modules whose name contains 'singer'

Modules that drive the voicebank (WSL + GPU) run one after another in their own lane so they never fight for the GPU;
everything else runs in parallel. The slowest modules start first (timings of the last run in tests/.timings.json,
git-ignored). Exit code 1 when any module fails; the failing modules' output is printed in full.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests' / 'python'
TIMINGS = ROOT / 'tests' / '.timings.json'
GPU_WORDS = ('singer', 'voicebank', 'vocal')   # a module whose source mentions these renders sung takes
GPU_MODULES = ('test_notation',)               # compiles every song: sung songs synthesize missing takes


def uses_gpu(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    return path.stem in GPU_MODULES or any(w in text for w in GPU_WORDS)


def run_module(path):
    t0 = time.time()
    p = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(TESTS), '-p', path.name],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = p.stdout + p.stderr
    ran = next((l for l in out.splitlines() if l.startswith('Ran ')), 'Ran ?')
    return path.stem, p.returncode, time.time() - t0, ran, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-j', type=int, default=os.cpu_count() or 4, help='parallel workers (default: all cores)')
    ap.add_argument('filter', nargs='*', help='only modules whose name contains one of these words')
    a = ap.parse_args()
    mods = sorted(TESTS.glob('test_*.py'))
    if a.filter:
        mods = [m for m in mods if any(f in m.stem for f in a.filter)]
    try:
        last = json.loads(TIMINGS.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        last = {}
    mods.sort(key=lambda m: -last.get(m.stem, 60.0))
    gpu = [m for m in mods if uses_gpu(m)]
    cpu = [m for m in mods if m not in gpu]
    results, lock, t0 = [], threading.Lock(), time.time()

    def done(r):
        with lock:
            results.append(r)
            name, code, sec, ran, _ = r
            print(f"{'ok  ' if code == 0 else 'FAIL'} {sec:6.1f}s  {name:28s} {ran}", flush=True)

    def gpu_lane():
        for m in gpu:
            done(run_module(m))

    with ThreadPoolExecutor(max_workers=max(1, a.j)) as ex:
        lane = ex.submit(gpu_lane) if gpu else None
        for f in [ex.submit(run_module, m) for m in cpu]:
            done(f.result())
        if lane:
            lane.result()

    failed = [r for r in results if r[1] != 0]
    for name, _, _, _, out in failed:
        print(f'\n===== {name} =====\n{out}')
    try:
        last.update({r[0]: round(r[2], 1) for r in results})
        TIMINGS.write_text(json.dumps(last, indent=1, sort_keys=True), encoding='utf-8')
    except OSError:
        pass
    total = sum(int(r[3].split()[1]) for r in results if r[3].split()[1].isdigit())
    print(f'\n{len(results)} modules, {total} tests, {len(failed)} failed module(s), '
          f'{time.time() - t0:.0f} s wall ({sum(r[2] for r in results):.0f} s CPU-serial), {a.j} workers')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
