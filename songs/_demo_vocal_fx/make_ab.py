"""Build the processed-voice A/B set of songs/_demo_vocal_fx into out/fx_ab/ (mp3s + README.txt + fx_ab.json):

    python songs/_demo_vocal_fx/make_ab.py [name ...]      # default: all (needs numpy for the level match)

Groups (each LEVEL-MATCHED: every file of a group is turned down to the quietest one's integrated loudness, so the
louder one never wins by level):
  a  pitch correction   a1_natural, a2_hard_tune, a3_soft_tune (over the band) + a4_natural_solo, a5_hard_solo,
                        a6_soft_solo (the voice alone)
  b  prism / harmoniser b1_choir_of_one, b2_prismizer (over the band; a1 / a2 are their leads without the prism)
  c  talk box           c1_talkbox, c2_guitar_no_talkbox
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / 'out'
AB = OUT / 'fx_ab'
sys.path.insert(0, str(REPO))

# name -> (group, env, what it is)
VARIANTS = {
    'a1_natural': ('a', {'AGENTSOUND_VOCAL_FX': 'natural'},
                   "Hanami sings 'Radio Heart' over the band - no pitch correction (the reference)"),
    'a2_hard_tune': ('a', {'AGENTSOUND_VOCAL_FX': 'hard'},
                     "the same take with sing(tune='hard'): retune 0 ms - every frame on a note of A minor, the "
                     "vibrato gone, glides turned into stair steps: the robotic Cher / T-Pain flip"),
    'a3_soft_tune': ('a', {'AGENTSOUND_VOCAL_FX': 'soft'},
                     "sing(tune='soft'): retune 40 ms - held notes centred, transitions and part of the vibrato kept "
                     "(the 'transparent' correction)"),
    'a4_natural_solo': ('a', {'AGENTSOUND_VOCAL_FX': 'natural', 'AGENTSOUND_VOCAL_FX_SOLO': '1'},
                        "a1, the voice alone (the band muted)"),
    'a5_hard_solo': ('a', {'AGENTSOUND_VOCAL_FX': 'hard', 'AGENTSOUND_VOCAL_FX_SOLO': '1'},
                     "a2, the voice alone - the steps are easiest to hear here"),
    'a6_soft_solo': ('a', {'AGENTSOUND_VOCAL_FX': 'soft', 'AGENTSOUND_VOCAL_FX_SOLO': '1'},
                     "a3, the voice alone"),
    'b1_choir_of_one': ('b', {'AGENTSOUND_VOCAL_FX': 'choir'},
                        "the natural lead + singer.prism(preset='choir-of-one'): 4 more takes of Hanami RE-SUNG on the "
                        "chord tones of Am F C G (3 under the lead, 1 over), loosely timed (8-30 ms), formants +-0.8 st, "
                        "panned +-0.85, each 9 dB under the lead's takes"),
    'b2_prismizer': ('b', {'AGENTSOUND_VOCAL_FX': 'prismizer'},
                     "the hard-tuned lead + singer.prism(preset='prismizer'): 4 hard-tuned chord-tone takes + one an "
                     "octave away, tight (0-6 ms), formants up to +-1.8 st, panned wall to wall (Bon Iver / Francis "
                     "and the Lights)"),
    'c1_talkbox': ('c', {'AGENTSOUND_VOCAL_FX': 'talkbox'},
                   "'Box Talk': a funk groove, the lead guitar (DI Strat -> tube amp) played through a TALK BOX - TIGER "
                   "mouths the words on one low pitch (singer.mouth), the vocoder in LPC mode (speech.talkbox) puts "
                   "the mouth's vowels on the amp's sound; the cabinet replaced by the 'horn'"),
    'c2_guitar_no_talkbox': ('c', {'AGENTSOUND_VOCAL_FX': 'guitar'},
                             "the same groove and guitar line without the talk box (the plain amp + cabinet)"),
}
LEVEL_GROUPS = {'a_band': ['a1_natural', 'a2_hard_tune', 'a3_soft_tune', 'b1_choir_of_one', 'b2_prismizer'],
                'a_solo': ['a4_natural_solo', 'a5_hard_solo', 'a6_soft_solo'],
                'c': ['c1_talkbox', 'c2_guitar_no_talkbox']}


def _grit_ab():
    """songs/_demo_vocal/grit_ab.py's WAV reader and BS.1770 loudness (one implementation)."""
    spec = importlib.util.spec_from_file_location('grit_ab', REPO / 'songs' / '_demo_vocal' / 'grit_ab.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _env(v: dict) -> dict:
    env = dict(os.environ)
    for k in ('AGENTSOUND_VOCAL_FX', 'AGENTSOUND_VOCAL_FX_SOLO', 'AGENTSOUND_TALK_MOUTH'):
        env.pop(k, None)
    env.update(v)
    return env


def main(argv) -> int:
    want = argv[1:] or list(VARIANTS)
    bad = [w for w in want if w not in VARIANTS]
    if bad:
        print(f"unknown variant(s) {bad}; variants: {', '.join(VARIANTS)}")
        return 2
    from agentsound.cli import find_ffmpeg
    ga = _grit_ab()
    AB.mkdir(parents=True, exist_ok=True)
    wavs = AB / '_wav'
    wavs.mkdir(exist_ok=True)
    nums_path = AB / 'fx_ab.json'
    nums = json.loads(nums_path.read_text(encoding='utf-8')) if nums_path.is_file() else {}
    for name in want:
        print(f"=== {name}")
        r = subprocess.run([sys.executable, '-m', 'agentsound', 'build', str(HERE)], env=_env(VARIANTS[name][1]),
                           cwd=str(REPO))
        if r.returncode != 0:
            print(f"variant {name} failed (exit {r.returncode})")
            return r.returncode
        shutil.copyfile(OUT / 'mix.wav', wavs / f'{name}.wav')
        x, fs = ga._read(wavs / f'{name}.wav')
        nums[name] = {'lufs': round(ga.lufs(x, fs), 2)}
        nums_path.write_text(json.dumps(nums, indent=1), encoding='utf-8')
    ff = find_ffmpeg()
    if ff is None:
        print('ffmpeg not found: no mp3s')
        return 3
    for group, names in LEVEL_GROUPS.items():
        have = [n for n in names if n in nums and (wavs / f'{n}.wav').is_file()]
        if not have:
            continue
        target = min(nums[n]['lufs'] for n in have)
        for n in have:
            g = target - nums[n]['lufs']
            nums[n].update(gain_db=round(g, 2), matched_lufs=round(target, 2), group=group)
            subprocess.run([ff, '-y', '-loglevel', 'error', '-i', str(wavs / f'{n}.wav'), '-af', f'volume={g:.2f}dB',
                            '-codec:a', 'libmp3lame', '-b:a', '320k', str(AB / f'{n}.mp3')], check=True)
            print(f"{n:22} {nums[n]['lufs']:6.1f} LUFS -> {target:6.1f} ({g:+.1f} dB)  {AB / (n + '.mp3')}")
    nums_path.write_text(json.dumps(nums, indent=1), encoding='utf-8')
    readme(nums)
    return 0


def readme(nums: dict) -> None:
    lyr = (HERE / 'lyrics.txt').read_text(encoding='utf-8').rstrip().splitlines()
    lines = ["Processed-voice effects A/B - songs/_demo_vocal_fx (build: python songs/_demo_vocal_fx/make_ab.py)", "",
             "Every file of a group is level-matched (turned down to the quietest one's integrated loudness):",
             "  a1-a3 + b1-b2 (over the band), a4-a6 (the voice alone), c1-c2 (the talk box).", "", "Files:"]
    for name, (group, _, what) in VARIANTS.items():
        n = nums.get(name)
        if n is None or 'matched_lufs' not in n:
            continue
        lines.append(f"  {name}.mp3 - {what}")
        lines.append(f"      rendered {n['lufs']:.1f} LUFS, played at {n['matched_lufs']:.1f} LUFS ({n['gain_db']:+.1f} dB)")
    lines += ["", "How they work:",
              "  tune      the singer's own pitch curve (what the voicebank is told to sing) is corrected before the",
              "            voice is synthesised: each 11.6 ms frame snapped to the nearest scale note (hysteresis, blips",
              "            under 30 ms ignored), the correction smoothed with the retune time (0 ms = a step). The voice",
              "            is synthesised AT that pitch, so its formants stay its own (no chipmunk).",
              "  prism     not a pitch shifter: every prism voice is another take of the same voicebank singing a",
              "            chord tone of the harmony near the lead (voice-led: common tones held, no unisons / seconds",
              "            against the lead), its own timing, formant (gender) and pan; each take level-matched to the",
              "            lead's takes (low notes sing quieter), then the preset's level under it.",
              "  talk box  the vocoder in LPC mode: a running model of the mouth's resonances (from the sung 'mouth'",
              "            track, muted) filters the guitar right after its amp (the cabinet taken out: the horn",
              "            replaces the speaker). The guitar gives the notes, the mouth the vowels.", "",
              "Lyrics (lyrics.txt):", *("  " + x for x in lyr), "",
              "Voices: Hanami (Lotte V) and TIGER (tigermeat) - NON-COMMERCIAL: private listening only."]
    (AB / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"README    {AB / 'README.txt'}")


if __name__ == '__main__':
    sys.exit(main(sys.argv))
