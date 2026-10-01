"""Build every variant of the vocal demo and keep each mp3 under its own name in out/ (see song.py):

    python songs/_demo_vocal/make_ab.py [variant ...]      # default: all; the 'full' build is left in out/

out/vocal_demo.mp3 (the produced vocal over the band), out/vocal_dry.mp3 (the vocal alone, no chain),
out/ab_robotic.mp3 vs out/ab_singer.mp3 (the same phrase without / with the singer's moves), out/ab_pitch_model.mp3
(the voicebank's pitch model alone), out/ab_player_pitch.mp3 (the singer's synthetic curve alone), out/ab_tiger.mp3 (the TIGER voicebank, an octave down; non-commercial).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
VARIANTS = {'dry': 'vocal_dry', 'robotic': 'ab_robotic', 'singer': 'ab_singer', 'model': 'ab_pitch_model',
            'player': 'ab_player_pitch', 'tiger': 'ab_tiger', 'soulx': 'ab_soulx', 'full': 'vocal_demo'}


def main(argv) -> int:
    want = argv[1:] or [v for v in VARIANTS
                        if v != 'soulx' or (HERE / 'samples' / 'soulx' / 'generated.wav').is_file()]
    bad = [v for v in want if v not in VARIANTS]
    if bad:
        print(f"unknown variant(s) {bad}; variants: {', '.join(VARIANTS)}")
        return 2
    keep = {}
    for v in want:
        env = dict(os.environ, AGENTSOUND_VOCAL_VARIANT=v)
        print(f"=== {v}")
        r = subprocess.run([sys.executable, '-m', 'agentsound', 'build', str(HERE)], env=env,
                           cwd=str(HERE.parent.parent))
        if r.returncode != 0:
            print(f"variant {v} failed (exit {r.returncode})")
            return r.returncode
        stash = OUT.parent / f'.ab_{VARIANTS[v]}.mp3'
        shutil.copyfile(OUT / 'mix.mp3', stash)
        keep[v] = stash
    for v, stash in keep.items():
        dst = OUT / f'{VARIANTS[v]}.mp3'
        shutil.move(str(stash), dst)
        print(f"{v:8} -> {dst}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
