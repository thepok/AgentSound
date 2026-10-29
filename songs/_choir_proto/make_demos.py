"""Build the choir prototype's variants (song.py) and keep each mp3 under its own name:

    python songs/_choir_proto/make_demos.py [variant ...]     # default: all -> out/<name>.mp3 (+ a copy in
                                                              #   $CHOIR_DEMO_OUT, default the main checkout's out/)
Prints the build time per variant (stage 2: the DiffSinger takes are cached in samples/vocals/ after the first build).
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import choir  # noqa: E402
choir.setup_env()     # banks / packs / engine of the main checkout when this is a worktree

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
EXTRA = Path(os.environ.get('CHOIR_DEMO_OUT', r'D:\Repos\AgentSound\songs\_choir_proto\out'))
VARIANTS = {'newpack': 'stage1_newpack', 'single': 'stage1_single_layer', 'copies': 'stage1_copies',
            'oldchoir': 'stage1_oldchoir', 'pure': 'stage2_pure', 'hybrid': 'stage2_hybrid', 'big': 'stage3_big',
            'big_nobass': 'stage3_big_nobass', 'vsold': 'stage3_vs_old', 'hybrid3': 'stage3_hybrid_text',
            'clones': 'stage3_clones', 'abc': 'stage3_abc',
            'vocalset': 'stage4_vocalset', 'abc4': 'stage4_abc', 'hymn': 'stage4_hymn'}


def main(argv) -> int:
    want = argv[1:] or list(VARIANTS)
    for v in want:
        tmp = os.environ.get('CHOIR_TMP', str(choir.ROOT))
        env = dict(os.environ, CHOIR_VARIANT=v, TMP=tmp, TEMP=tmp)
        print(f"=== {v}", flush=True)
        t = time.time()
        r = subprocess.run([sys.executable, '-m', 'agentsound', 'build', str(HERE)], env=env,
                           cwd=str(HERE.parent.parent))
        if r.returncode != 0:
            print(f"variant {v} failed (exit {r.returncode})")
            return r.returncode
        name = VARIANTS[v]
        for ext in ('mp3', 'wav'):
            shutil.copyfile(OUT / f'mix.{ext}', OUT / f'{name}.{ext}')
        shutil.copyfile(OUT / 'report.json', OUT / f'{name}.report.json')
        if (OUT / 'overview.png').is_file():
            shutil.copyfile(OUT / 'overview.png', OUT / f'{name}.overview.png')
        if EXTRA.resolve() != OUT.resolve():
            EXTRA.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OUT / f'{name}.mp3', EXTRA / f'{name}.mp3')
        print(f"{v:9} -> {OUT / (name + '.mp3')}  ({time.time() - t:.0f} s)", flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
