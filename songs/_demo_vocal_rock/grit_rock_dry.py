"""The rock grit A/B again with the DRY vocal chain (recipes/HUMAN_FEEDBACK.md "Vocals": "der Gesang hat immer viel
Hall ... das macht es vermutlich schwieriger ihn zu verzerren?!"):

    python songs/_demo_vocal_rock/grit_rock_dry.py            # (numpy for the measurements)

'Exit Nine' (songs/_demo_vocal_rock) from the chorus to the end (~21 s: the chorus wall + the final hit), TIGER clean
vs TIGER crunch (hero(..., grit='crunch'): the parallel tube-amp bus under the untouched clean voice), both with the
library's new dry rock vocal space (the short pre-delayed vocal plate ~15 LU under the voice, no constant echo, one
deliberate throw at each section end, no hall). Level-matched (BS.1770 integrated) into out/grit_rock_dry/ with a
README.txt, the lyrics and the numbers (grit_rock_dry.json): the reverb / echo returns vs the dry voice (the voice =
the vocal track + its grit bus, every other track muted: songs/_demo_vocal/wetness.py), the tail after the phrase
ends, the word-final consonants vs their vowel (2-8 kHz) and the vocal's sibilance. The grit bus is fed post-fader
from the vocal chain, which holds no reverb or delay (checked in the render JSON): the amp only ever sees the dry voice.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'songs' / '_demo_vocal'))
sys.path.insert(0, str(REPO / 'songs' / 'jane-street-bossa'))
import grit_ab as G          # noqa: E402
import wetness as W          # noqa: E402
from dry_ab import _write    # noqa: E402

OUT = HERE / 'out'
AB = OUT / 'grit_rock_dry'
FROM = 40.0                   # the chorus (bar 11) to the end
VARIANTS = {
    '1_tiger_clean_dry': ({'AGENTSOUND_ROCK_VOICE': 'tiger', 'AGENTSOUND_ROCK_GRIT': 'clean'},
                          "TIGER (male rock voice, the chorus leaning on his power mode Electric), the vocal hero "
                          "clean, the new DRY rock space"),
    '2_tiger_crunch_dry': ({'AGENTSOUND_ROCK_VOICE': 'tiger', 'AGENTSOUND_ROCK_GRIT': 'crunch'},
                           "TIGER, crunch grit (the parallel amp bus, gain 6 + overdrive push, 5 dB under the clean "
                           "voice, level-matched), the new DRY rock space"),
}


def _dry_feed_check(render: dict) -> list:
    """What feeds the grit bus, and whether anything time-based sits before it."""
    out = []
    tr = next(t for t in render['tracks'] if t['id'] == 'vocal')
    timed = [f['type'] for f in tr['fx'] if f['type'] in ('reverb', 'delay', 'convolver', 'gatedreverb')]
    out.append(f"vocal chain: {' -> '.join(f.get('name') or f['type'] for f in tr['fx'])} (time-based fx: "
               f"{', '.join(timed) or 'none'}); sends: {tr.get('sends')}")
    for b in render['buses']:
        if b['id'] == 'vocal_grit':
            out.append(f"vocal_grit bus: {' -> '.join(f.get('name') or f['type'] for f in b['fx'])}; its sends: "
                       f"{b.get('sends') or 'none'} (fed only by the vocal's post-fader send)")
    return out


def render(name: str) -> dict:
    from agentsound import cli
    env, _ = VARIANTS[name]
    song = W.load(HERE / 'song.py', env=env)
    rnd = song.compile()
    rdir = OUT / 'grit_rock_dry_render' / name
    shutil.rmtree(rdir, ignore_errors=True)
    rj = cli.write_render(rnd, rdir / 'song.render.json')
    cli.run_engine(cli.find_engine(), rj, rdir, FROM, None, rnd)
    shutil.copyfile(rdir / 'mix.wav', AB / f'{name}.raw.wav')
    x, fs = G._read(rdir / 'mix.wav')
    res = {'mix_lufs': round(G.lufs(x, fs), 2), 'feed': _dry_feed_check(rnd)}
    wdir = OUT / 'grit_rock_dry_render' / f'{name}_wet'
    res.update(W.wetness(song, wdir, FROM, None))
    v, fs = G._read(wdir / 'stems' / 'vocal.wav')
    g = wdir / 'stems' / 'vocal_grit.wav'
    if g.is_file():
        v = v + G._read(g)[0]
    res['vocal_lufs'] = round(G.lufs(v, fs), 2)
    _write(wdir / 'voice.wav', v, fs)
    t0 = song.seconds(FROM)
    sg = W.singing(song, stem=wdir / 'voice.wav', t_off=t0, span=(t0, 1e9))
    res['sibilance_db_median'], res['sibilance_db_p90'] = sg['sibilance_db_median'], sg['sibilance_db_p90']
    res['codas'] = sg['codas']
    return res


def main(argv) -> int:
    from agentsound import cli
    AB.mkdir(parents=True, exist_ok=True)
    nums = {}
    for name in VARIANTS:
        print(f"=== {name}")
        nums[name] = render(name)
    ref = nums['1_tiger_clean_dry']['mix_lufs']
    for name in VARIANTS:
        x, fs = G._read(AB / f'{name}.raw.wav')
        gdb = ref - nums[name]['mix_lufs']
        nums[name]['match_gain_db'] = round(gdb, 2)
        _write(AB / f'{name}.wav', x * 10 ** (gdb / 20.0), fs)
        print(cli.encode_mp3(AB / f'{name}.wav', AB / f'{name}.mp3'))
        (AB / f'{name}.wav').unlink()
        (AB / f'{name}.raw.wav').unlink()
    (AB / 'grit_rock_dry.json').write_text(json.dumps(nums, indent=1), encoding='utf-8')
    readme(nums)
    return 0


def readme(nums: dict) -> None:
    lyr = (HERE / 'lyrics.txt').read_text(encoding='utf-8')
    c, k = nums['1_tiger_clean_dry'], nums['2_tiger_crunch_dry']
    d = sorted((b[0] - a[0], b[1], b[2]) for a, b in zip(c['codas'], k['codas']))
    lines = ["Vocal grit in a ROCK context, again with the DRY vocal chain - 'Exit Nine' (songs/_demo_vocal_rock) from the",
             "chorus to the end (~21 s): the chorus wall of The Drummer Speaks' rock band + the final hit.",
             "Question (HUMAN_FEEDBACK 'Vocals'): the earlier grit tests were heard with a wet voice (plate -12 + echo",
             "-20 + throws: the returns only 5 LU under it) - does the grit work better on a DRY voice over a real band?",
             "", "Lyrics (original; the excerpt is the chorus):", *("  " + x for x in lyr.rstrip().splitlines()), "",
             "Files (level-matched to 1 by BS.1770 integrated loudness):"]
    for name, (_, what) in VARIANTS.items():
        n = nums[name]
        lines += [f"  {name}.mp3 - {what}",
                  f"      reverb / echo {n['wet_lu']:+.1f} LU vs the dry voice ("
                  + ', '.join(f"{b} {v:+.1f}" for b, v in n['buses'].items()) + f"); the voice {n['vocal_lufs']:.1f} "
                  f"LUFS; sibilance (s / sh at 5-12 kHz vs the vowel) {n['sibilance_db_median']} dB median; level "
                  f"match {n['match_gain_db']:+.2f} dB"]
    if d:
        lines.append(f"  crunch vs clean, word-final consonants vs their vowel (2-8 kHz): median {d[len(d) // 2][0]:+.1f} "
                     f"dB, worst {d[0][0]:+.1f} dB ('{d[0][1]}' /{d[0][2]}/)")
    lines += ["", "Where the distortion sits (the render JSON):", *("  " + x for x in k['feed']),
              "  -> the amp takes the DRY voice only (the plate / echo are parallel sends of the clean track; the takes",
              "     themselves are dry: no reverb or echo is baked in before the grit - also not on test/rock-grit).",
              "", "Before (the wet chain, out/grit_rock_ab/ on test/rock-grit): the plate return -5.5 LU and the echo",
              "-16.9 LU under the voice (all returns -5.1 LU); now about -15 LU.",
              "Voices: TIGER (tigermeat) - NON-COMMERCIAL: private listening only."]
    (AB / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (AB / 'lyrics.txt').write_text(lyr, encoding='utf-8')
    print(f"README    {AB / 'README.txt'}")


if __name__ == '__main__':
    sys.exit(main(sys.argv))
