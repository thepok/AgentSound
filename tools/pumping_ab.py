"""Replay one saved endless tune before/after the opt-in pumping fix, with stems and diagnostics.

python tools/pumping_ab.py path/to/tune-folder --out D:/tmp/pumping/ab/4242
Set AGENTSOUND_SAMPLES / AGENTSOUND_ENGINE when using a separate checkout.
No playback, downloads, mastering changes or loudness matching.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agentsound import cli
from agentsound.endless import genres, symphony
from agentsound.endless.run import load_scored
from pumping import measure, momentary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('tune', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg is None:
        raise RuntimeError('ffmpeg is required')
    previous = symphony.PUMPING
    try:
        for label, enabled in [('before', False), ('after', True)]:
            genres.symphony_pumping(enabled)
            song, tune, genre = load_scored(args.tune)
            if genre.name != 'orchestra-symphonic':
                raise ValueError('this A/B is for orchestra-symphonic')
            song.export(stems=True, bit_depth=32)
            render = song.compile()
            # Float stereo stems are large. Fail before rendering rather than accepting partial files on a full disk.
            seconds = song.tempo_map().seconds_at(render['lengthBeats']) + render.get('tailSeconds', 0)
            needed = int(seconds * render.get('sampleRate', 48000) * 8 *
                         (1 + len(render['tracks']) + len(render.get('buses', []))))
            args.out.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(args.out).free < needed + 256 * 1024 * 1024:
                raise RuntimeError(f'Need at least {needed / 1024**3:.1f} GiB free for this render plus headroom')
            cli.apply_analysis(render, {'profile': genre.band.get('profile', 'classical')})
            out = args.out / label
            out.mkdir(parents=True, exist_ok=True)
            path = cli.write_render(render, out / 'song.render.json')
            print(f'{tune.seed} {label}: rendering', flush=True)
            subprocess.run([str(cli.find_engine()), 'render', str(path), '--out', str(out), '--no-png', '--quiet'],
                           check=True)
            subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(out / 'mix.wav'), '-codec:a', 'libmp3lame',
                            '-q:a', '2', str(args.out / f'{label}.mp3')], check=True)
            report_path = out / 'report.json'
            report = json.loads(report_path.read_text(encoding='utf-8'))
            report['pumping'] = measure(*momentary(out / 'mix.wav'))
            report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print(f'{tune.seed} {label}: {report["pumping"]["p95Change1sDb"]} dB p95 1-second change', flush=True)
    finally:
        symphony.PUMPING = previous


if __name__ == '__main__':
    main()
