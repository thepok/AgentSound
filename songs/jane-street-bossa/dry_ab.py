"""Dry-vocal A/B for 'Down on Jane Street' (recipes/HUMAN_FEEDBACK.md "Vocals": "der Gesang hat immer viel Hall
und/oder Reverb" and "im Jazz-Song ist die Stimme viel zu aufgeregt, sollte ruhiger sein"):

    python songs/jane-street-bossa/dry_ab.py [name ...]        # default: every variant that is not frozen

One sung chorus - the head's A2 + C (bars 25-40 of the song, beats 96-160, ~30 s: the hook, the taxis line and the
climax "down on Jane Street, rain" on the top G5) - rendered through the whole mix and master, then level-matched to
the first variant (BS.1770 integrated) into out/dry_ab/<name>.mp3, with the wetness / singing numbers of
songs/_demo_vocal/wetness.py in dry_ab.json and a README.txt (+ the lyrics).

  1_before     the shipped version: the old vocal hero space (its 2.8 s hero plate at -17 + the band's room at -15,
               set by hand in the song after turning the echo throws off) and the old singing (style 'ballad' with
               the song's overrides). FROZEN: rendered once with the old code (git: before fix/dry-vocals), kept.
  2_dry        the new library defaults for the space (the vocal plate: short, pre-delayed, 20 LU under the voice
               for jazz; no echo, no throws, no band room), the OLD singing (the same cached takes as 1_before)
  3_dry_calm   the new song: the new space + the new calm jazz singing (style 'jazz')
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'songs' / '_demo_vocal'))
import wetness as W          # noqa: E402
import grit_ab as G          # noqa: E402

OUT = HERE / 'out'
AB = OUT / 'dry_ab'
FROM, TO = 96.0, 160.0       # head A2 + C

# the singing of the shipped song (style 'ballad' as it was + the song's VOICE overrides): 2_dry sings exactly these
# takes (the cache key is the spec: the same params -> the same cached files as 1_before)
OLD_BALLAD = dict(vel=(56, 100), late_ms=14.0, jitter_ms=12.0, cons=1.12, speed=0.92, cons_share=0.4,
                  glide_ms=100.0, melisma_glide=0.6, overshoot_ct=10.0,
                  scoop_first=0.5, scoop_leap=0.6, scoop_peak=0.7, scoop_ct=60.0, scoop_ms=150.0,
                  vib_other=0.75, vib_peak=1.0, vib_ct=30.0, peak_vib_ct=44.0, vib_hz=5.2, vib_delay=0.38,
                  vib_grow=0.6, vib_min_s=0.6, wobble=0.18,
                  fall=0.1, doit=0.0, fall_semis=-1.6, release=0.85, taper=0.7, swell=0.6, messa=0.5,
                  accent=0.14, breath_db=-3.0, breath_min_s=0.25, drift_ct=6.0,
                  power=0.35, soft=0.8, base_power=0.0, base_soft=0.2, pitch_power=0.03,
                  spice_every=4, link=True, steps=24)
OLD_VOICE = dict(voice='hanami', style='ballad', late_ms=10.0, fall=0.12, doit=0.0, vib_ct=22.0, peak_vib_ct=34.0,
                 scoop_first=0.3, scoop_leap=0.4, scoop_peak=0.5, soft=0.75, power=0.35, vel=(60, 100))


def _round1(mod):
    """The song as round 1 left it (Bb major, the original A, the round-1 calm 'jazz' style): calm_ab.py's a_calm."""
    import calm_ab
    calm_ab._variant(calm_ab.J_A)(mod)


def _old_singing(mod):
    from agentsound import singer
    singer.STYLES['ballad'] = dict(OLD_BALLAD)
    mod.VOICE = dict(OLD_VOICE)
    mod.CALM_A, mod.FEW_A, mod.TRANSPOSE = False, False, 0


VARIANTS = {
    '1_before': (None, True,
                 "BEFORE (as shipped): the old vocal space - a 2.8 s bright hero plate (45 ms pre-delay) at -17 dB + "
                 "the band's room at -15 dB - and the old singing (style 'ballad' + overrides)"),
    '2_dry': (_old_singing, False,
              "DRY: the new vocal space (jazz: the short pre-delayed vocal plate 20 LU under the voice, no echo, no "
              "throws, no band room), the OLD singing (the very same takes as 1_before)"),
    '3_dry_calm': (_round1, False,
                   "DRY + CALM (the new song): the new vocal space + the new calm jazz singing (style 'jazz': Nectar "
                   "as the base, power only on the loudest peaks, few small scoops, a slow late narrow vibrato on "
                   "long notes only, no falls, smaller swings, smooth legato, laid back)"),
}


def _write(path: Path, x, fs) -> None:
    import numpy as np
    y = np.clip(x, -1.0, 1.0 - 1e-6)
    v = (y * 8388607.0).astype(np.int32)
    b = np.zeros((v.size, 3), np.uint8)
    f = v.reshape(-1)
    b[:, 0], b[:, 1], b[:, 2] = f & 255, (f >> 8) & 255, (f >> 16) & 255
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(3)
        w.setframerate(fs)
        w.writeframes(b.tobytes())


def render(name: str) -> dict:
    from agentsound import cli
    before, _, _ = VARIANTS[name]
    song = W.load(HERE / 'song.py', before=before)
    render = song.compile()
    rdir = OUT / 'dry_ab_render' / name
    shutil.rmtree(rdir, ignore_errors=True)
    rj = cli.write_render(render, rdir / 'song.render.json')
    cli.run_engine(cli.find_engine(), rj, rdir, FROM, TO, render)
    shutil.copyfile(rdir / 'mix.wav', AB / f'{name}.raw.wav')
    x, fs = G._read(rdir / 'mix.wav')
    res = {'mix_lufs': round(G.lufs(x, fs), 2)}
    rep = json.loads((rdir / 'report.json').read_text(encoding='utf-8'))
    voc = next((n for n in rep.get('nodes', []) if n.get('id') == 'vocal'), {})
    res['report_vocal_dynamics'] = voc.get('dynamics')
    res['report_clicks'] = rep.get('global', {}).get('clicks')
    wres = W.wetness(song, OUT / 'dry_ab_render' / f'{name}_wet', FROM, TO)
    res.update({k: v for k, v in wres.items()})
    res['take_tail'] = W.take_tails(song)
    t0 = song.seconds(FROM)
    res['singing'] = W.singing(song, stem=OUT / 'dry_ab_render' / f'{name}_wet' / 'stems' / 'vocal.wav', t_off=t0,
                               span=(t0, song.seconds(TO)))
    res['singing_full_song'] = W.singing(song)
    return res


def matched(nums: dict) -> None:
    """Level-match every rendered variant to 1_before (integrated LUFS) and encode the mp3s."""
    import numpy as np
    from agentsound import cli
    ref = nums.get('1_before', {}).get('mix_lufs')
    for name in VARIANTS:
        raw = AB / f'{name}.raw.wav'
        if not raw.is_file() or name not in nums:
            continue
        x, fs = G._read(raw)
        g = 0.0 if ref is None else ref - nums[name]['mix_lufs']
        nums[name]['match_gain_db'] = round(g, 2)
        y = x * 10 ** (g / 20.0)
        nums[name]['matched_peak_dbfs'] = round(float(20 * np.log10(np.max(np.abs(y)) + 1e-12)), 2)
        _write(AB / f'{name}.wav', y, fs)
        print(cli.encode_mp3(AB / f'{name}.wav', AB / f'{name}.mp3'))
        (AB / f'{name}.wav').unlink()


def readme(nums: dict) -> None:
    lyr = (HERE / 'LYRICS.md').read_text(encoding='utf-8')
    a2 = lyr.split('**A2**', 1)[1].split('## Piano solo', 1)[0]
    lines = ["'Down on Jane Street' - dry-vocal A/B (recipes/HUMAN_FEEDBACK.md \"Vocals\": the voice too wet, and too",
             "agitated for a jazz song). One sung chorus: the head's A2 + C (bars 25-40, ~30 s), the whole mix and",
             "master, level-matched to 1_before (BS.1770 integrated; the gain is listed).", "",
             "Lyrics (A2 + C):", *("  " + ln.strip() for ln in a2.replace('**C**', '').splitlines() if ln.strip()),
             "", "Files:"]
    for name, (_, _, what) in VARIANTS.items():
        n = nums.get(name)
        if n is None:
            continue
        sg = n['singing']
        lines += [f"  {name}.mp3 - {what}",
                  f"      reverb / echo returns {n['wet_lu']:+.1f} LU vs the dry voice ("
                  + ', '.join(f"{k} {v:+.1f}" for k, v in n['buses'].items()) + "); after a phrase end the returns "
                  f"read {n['tail']['wet_250_db']:+.1f} dB at 250 ms / {n['tail']['wet_500_db']:+.1f} dB at 500 ms "
                  f"(vs the phrase), the voice + returns fall 30 dB in {n['tail']['decay30_s']:.2f} s",
                  f"      singing: {sg['scooped_onsets']} of {sg['onsets']} openers / steps down scooped (median "
                  f"{sg['scoop_depth_ct_median']} ct), notes settle in {sg['settle_ms_median']:.0f} ms (p90 "
                  f"{sg['settle_ms_p90']:.0f}); vibrato on held notes +-{sg['vibrato_ext_ct_median']} ct at "
                  f"{sg['vibrato_rate_hz_median']} Hz; vowels {100 * sg['mode_soft_share']:.0f} % soft mode (Nectar) / "
                  f"{100 * sg['mode_power_share']:.0f} % power (Fragrance); note levels p10-p90 "
                  f"{sg['note_level_p10_p90_db']} dB; falls {sg['plan']['falls']}, planned scoops "
                  f"{sg['plan']['scoops']} ({sg['plan']['scoop_ct_mean']} ct), planned vibratos "
                  f"{sg['plan']['vibratos']} ({sg['plan']['vib_ct_mean']} ct, {sg['plan']['vib_hz_mean']} Hz)",
                  f"      level match {n.get('match_gain_db', 0.0):+.2f} dB (mix {n['mix_lufs']:.1f} LUFS)"]
        fs = n.get('singing_full_song')
        if fs:
            lines.append(f"      whole song: {fs['scooped_onsets']} of {fs['onsets']} scooped (median "
                         f"{fs['scoop_depth_ct_median']} ct), settle p90 {fs['settle_ms_p90']:.0f} ms, held-note wobble "
                         f"+-{fs['vibrato_ext_ct_median']} ct (p90 {fs['vibrato_ext_ct_p90']}), soft "
                         f"{100 * fs['mode_soft_share']:.0f} % / power {100 * fs['mode_power_share']:.1f} %, gain lane "
                         f"p10-p90 {fs['gain_lane_p10_p90_db'][0]:+.1f}..{fs['gain_lane_p10_p90_db'][1]:+.1f} dB")
    lines += ["", "The DiffSinger takes themselves are dry: 30-250 ms after the last phoneme a take reads "
              f"{nums.get('1_before', {}).get('take_tail', {}).get('median_db', '?')} dB under its last vowel "
              "(median) - every bit of space is the mix's.",
              "Voice: Hoshino Hanami (Lotte V) - its vocoder is CC BY-NC-SA: private listening only."]
    (AB / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (AB / 'lyrics.txt').write_text(lyr, encoding='utf-8')
    print(f"README    {AB / 'README.txt'}")


def main(argv) -> int:
    AB.mkdir(parents=True, exist_ok=True)
    nums_path = AB / 'dry_ab.json'
    nums = json.loads(nums_path.read_text(encoding='utf-8')) if nums_path.is_file() else {}
    if argv[1:] == ['--readme']:
        readme(nums)
        return 0
    want = argv[1:] or [n for n, v in VARIANTS.items() if not v[1] or n not in nums]
    for name in want:
        if name not in VARIANTS:
            print(f"unknown variant {name!r}: {', '.join(VARIANTS)}")
            return 2
        print(f"=== {name}")
        nums[name] = render(name)
        nums_path.write_text(json.dumps(nums, indent=1), encoding='utf-8')
    matched(nums)
    nums_path.write_text(json.dumps(nums, indent=1), encoding='utf-8')
    readme(nums)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
