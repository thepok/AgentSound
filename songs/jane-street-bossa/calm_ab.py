"""Calm-vocal A/B for 'Down on Jane Street' (recipes/HUMAN_FEEDBACK.md "Vocals": "die Jazz-Stimme ist immer noch sehr
aufgeregt, vielleicht leiser singen lassen und dann nachtraeglich lauter machen?" and "sie klingt gerusht"):

    python songs/jane-street-bossa/calm_ab.py [name ...]        # default: every variant not rendered yet
    python songs/jane-street-bossa/calm_ab.py --readme          # only rewrite README.txt from calm_ab.json

The same sung chorus as dry_ab.py (the head's A2 + C, beats 96-160, ~30 s) through the whole mix and master with the
dry vocal chain, level-matched to a (BS.1770 integrated) into out/calm_ab/<name>.mp3, with the numbers of
songs/_demo_vocal/wetness.py (take_character, timing, line_shape, singing) in calm_ab.json, a README.txt and the lyrics.
Each variant sets the singer's 'jazz' style and the song's options (CALM_A, TRANSPOSE) explicitly, so the takes of
a variant are the same whatever the library default is now.
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
sys.path.insert(0, str(HERE))
import grit_ab as G          # noqa: E402
import wetness as W          # noqa: E402
from dry_ab import FROM, TO, _write     # noqa: E402

OUT = HERE / 'out'
AB = OUT / 'calm_ab'

# the calm 'jazz' style of the first round (fix/dry-vocals, 3_dry_calm of dry_ab.py) - variant a
J_A = dict(vel=(60, 88), late_ms=14.0, jitter_ms=7.0, cons=1.05, speed=0.9, cons_share=0.4,
           glide_ms=110.0, melisma_glide=0.7, overshoot_ct=3.0,
           scoop_first=0.12, scoop_leap=0.15, scoop_peak=0.2, scoop_ct=40.0, scoop_ms=110.0,
           vib_other=0.35, vib_peak=0.75, vib_ct=16.0, peak_vib_ct=24.0, vib_hz=4.6, vib_delay=0.6,
           vib_grow=0.8, vib_min_s=0.9, wobble=0.1,
           fall=0.0, doit=0.0, fall_semis=-1.2, release=0.9, taper=0.6, swell=0.3, messa=0.2,
           accent=0.07, breath_db=-4.0, breath_min_s=0.25, drift_ct=4.0,
           power=0.6, soft=0.5, base_power=0.0, base_soft=1.0, pitch_power=0.0,
           spice_every=8, link=True, steps=24,
           expr=0.45, model_vib=0.4, base_core=0.6, power_knee=0.35)
J_B = dict(J_A, sing_soft=True)                            # + sing soft, make-up gain on the zone
LOW_MAKEUP = 1.8     # a minor third lower the takes read ~2 dB softer (raw): the vocal stem back to b's level
J_BL = dict(J_B, makeup_db=LOW_MAKEUP)
LAYBACK = dict(late_ms=34.0, jitter_ms=5.0, late_first_ms=16.0)
J_E = dict(J_BL, **LAYBACK)


def _variant(style: dict, calm_a=False, transpose=0, few_a=False):
    def before(mod):
        from agentsound import singer
        singer.STYLES['jazz'] = dict(style)
        mod.CALM_A = calm_a
        mod.TRANSPOSE = transpose
        mod.FEW_A = few_a
    return before


VARIANTS = {
    'a_calm': (_variant(J_A),
               "the calm 'jazz' style of round 1 (as 3_dry_calm in out/dry_ab): the blend of Root / Nectar / a little "
               "Fragrance, the dry vocal space"),
    'b_soft': (_variant(J_B),
               "+ SING SOFT, THEN MAKE UP THE GAIN: every model sings 100 % Nectar (no Root / Fragrance crossfade), "
               "the take's zone gets a static make-up gain (the mix level stays)"),
    'c_soft_low': (_variant(J_BL, transpose=-3),
                   "b, the whole song a minor third lower (G major: the voice F#3-E5 instead of A3-G5, the band moved "
                   "with it - a fourth lower would put the voice's E3 under Hanami's F3)"),
    'd_soft_low_calmA': (_variant(J_BL, calm_a=True, transpose=-3),
                         "c + the calm A melody (the hook kept, the rest stepwise: no 6th / 9th leaps into the phrase "
                         "ends - song.py CALM_A)"),
    'e_soft_low_calmA_layback': (_variant(J_E, calm_a=True, transpose=-3),
                                 "d + laid-back timing (vowels ~29-39 ms behind the beat, phrase openers +16 ms more: the syllables land on the beat, not ahead)"),
    'f_soft_low_fewA_layback': (_variant(J_E, few_a=True, transpose=-3),
                                "e with the sparse A instead (FEW_A: fewer words on longer notes - quarters instead of "
                                "eighths, 21 syllables instead of 26; NEW WORDS for the A's: see lyrics.txt)"),
}


def render(name: str) -> dict:
    from agentsound import cli
    before, _ = VARIANTS[name]
    song = W.load(HERE / 'song.py', before=before)
    song.export(stems=True)
    rnd = song.compile()
    rdir = OUT / 'calm_ab_render' / name
    shutil.rmtree(rdir, ignore_errors=True)
    rj = cli.write_render(rnd, rdir / 'song.render.json')
    cli.run_engine(cli.find_engine(), rj, rdir, FROM, TO, rnd)
    shutil.copyfile(rdir / 'mix.wav', AB / f'{name}.raw.wav')
    x, fs = G._read(rdir / 'mix.wav')
    v, _ = G._read(rdir / 'stems' / 'vocal.wav')
    span = (song.seconds(FROM), song.seconds(TO))
    rep = json.loads((rdir / 'report.json').read_text(encoding='utf-8'))
    voc = next((n for n in rep.get('nodes', []) if n.get('id') == 'vocal'), {})
    from agentsound import singer
    vo0 = song.tracks['vocal']._singer['parts'][0]
    res = {'mix_lufs': round(G.lufs(x, fs), 2), 'vocal_lufs': round(G.lufs(v, fs), 2),
           'makeup_db': singer.makeup_db(vo0), 'report_vocal_dynamics_db': (voc.get('dynamics') or {}).get('spreadDb'),
           'clicks': rep.get('global', {}).get('clicks'),
           'take': W.take_character(song, span=span), 'timing': W.timing(song, span=span),
           'timing_song': W.timing(song), 'line': W.line_shape(song, span=span),
           'singing': {k: v for k, v in W.singing(song, stem=rdir / 'stems' / 'vocal.wav', t_off=span[0],
                                                  span=span).items() if k != 'codas'}}
    return res


def matched(nums: dict) -> None:
    from agentsound import cli
    ref = nums.get('a_calm', {}).get('mix_lufs')
    for name in VARIANTS:
        raw = AB / f'{name}.raw.wav'
        if not raw.is_file() or name not in nums:
            continue
        x, fs = G._read(raw)
        g = 0.0 if ref is None else ref - nums[name]['mix_lufs']
        nums[name]['match_gain_db'] = round(g, 2)
        _write(AB / f'{name}.wav', x * 10 ** (g / 20.0), fs)
        print(cli.encode_mp3(AB / f'{name}.wav', AB / f'{name}.mp3'))
        (AB / f'{name}.wav').unlink()


def readme(nums: dict) -> None:
    lyr = (HERE / 'LYRICS.md').read_text(encoding='utf-8')
    a2 = lyr.split('**A2**', 1)[1].split('## Piano solo', 1)[0]
    lines = ["'Down on Jane Street' - calm-vocal A/B (HUMAN_FEEDBACK 'Vocals': \"die Jazz-Stimme ist immer noch sehr",
             "aufgeregt\", \"sie klingt gerusht\"). One sung chorus: the head's A2 + C (bars 25-40, ~30 s), the whole mix",
             "and master with the dry vocal chain, level-matched to a (BS.1770 integrated; the gain is listed).", "",
             "Lyrics (A2 + C):", *("  " + ln.strip() for ln in a2.replace('**C**', '').splitlines() if ln.strip()),
             "", "Files (each adds one lever to the one before):"]
    for name, (_, what) in VARIANTS.items():
        n = nums.get(name)
        if n is None:
            continue
        tk, tm, ln, sg = n['take'], n['timing'], n['line'], n['singing']
        lines += [f"  {name}.mp3 - {what}",
                  f"      take (raw, before the chain): {tk['takes_lufs']:+.1f} LUFS, vowel centroid {tk['centroid_hz']:.0f} Hz, "
                  f"tilt (2-5 kHz vs 0.2-1 kHz) {tk['tilt_db']:+.1f} dB, level wobble in a vowel {tk['vowel_wobble_db']} dB, "
                  f"vowel-to-vowel p10-p90 {tk['vowel_level_p10_p90_db']} dB, onset rise {tk['onset_rise_db_per_10ms']} dB / 10 ms "
                  f"(p90 {tk['onset_rise_p90']}); make-up {n['makeup_db']:+.1f} dB -> vocal stem {n['vocal_lufs']:.1f} LUFS",
                  f"      timing: vowels {tm['vowel_ms_median']:+.0f} ms vs the beat (p10 {tm['vowel_ms_p10']:+.0f} / p90 "
                  f"{tm['vowel_ms_p90']:+.0f}, {tm['vowel_early_pct']} % early), phrase openers {tm['phrase_start_vowel_ms']:+.0f} ms, "
                  f"consonants lead by {tm['consonant_lead_ms']:.0f} ms, P-centre {tm['p_centre_ms']:+.0f} ms; "
                  f"{tm['syllables_per_s']} syllables / s in the phrases (median step {tm['syllable_ioi_ms_median']:.0f} ms, "
                  f"{tm['ioi_8th_or_less_pct']} % eighths or faster), rests {tm['rest_between_phrases_s']} s",
                  f"      line: {ln['time_at_or_above_D5_pct']} % of the sung time at / above D5, {ln['notes_at_or_above_G5']} "
                  f"notes at / above G5, {ln['leaps_4th_plus']} leaps of a 4th+ in {ln['intervals']} steps (mean "
                  f"{ln['mean_interval_st']} st), velocities {ln['vel_p10_p90'][0]:.0f}-{ln['vel_p10_p90'][1]:.0f}, "
                  f"wobble on short notes {ln['short_note_wobble_ct']} ct",
                  f"      singing: {sg['scooped_onsets']} of {sg['onsets']} scooped ({sg['scoop_depth_ct_median']} ct), "
                  f"held-note wobble +-{sg['vibrato_ext_ct_median']} ct, soft mode {100 * sg['mode_soft_share']:.0f} % / power "
                  f"{100 * sg['mode_power_share']:.1f} %; level match {n.get('match_gain_db', 0.0):+.2f} dB"]
    lines += ["", "Which lever moved what (measured; the ear decides):",
              "  register (c): the biggest change in what the voice does - sung time at / above D5 33 % -> 4 %, the",
              "    takes 2.4 dB darker (tilt) and their vowel-to-vowel level spread 7.6 -> 5.9 dB (a lower voice sings",
              "    with less effort); the song now sounds in G major (the band moved with the voice).",
              "  timing (e): the P-centre of the syllables (where they are heard to land) went from ~22 ms AHEAD of the",
              "    beat to on it (-2 ms): the vowels 35 ms late, the phrase openers 50 ms - the 'gerusht' fix.",
              "  melody (d): leaps of a 4th+ 11 -> 4 in 45 steps, the mean interval 3.6 -> 2.6 semitones.",
              "  sing soft (b): the takes 2.3 dB darker, onsets 12 % softer (median rise 11.3 -> 9.9 dB / 10 ms), the",
              "    power mode gone - but the soft mode is not quieter (+0.7 dB raw: the make-up is -0.7 dB).",
              "  density (f): the sparse A halves the A's syllable rate (median step 238 -> 476 ms; eighths 62 % -> 41 %",
              "    of the chorus' steps - the C is still dense) - it needs the new, shorter A words (lyrics.txt).",
              "The song itself now ships e (song.py: TRANSPOSE = -3, CALM_A = True; FEW_A = False) with the library's",
              "jazz style (sing soft + laid back); every variant uses the same MIX (its low-end eq set for G).",
              "", "Hanami's acoustic model takes speaker / gender / velocity (= consonant speed) / depth / steps only - no",
              "energy, breathiness, voicing or tension input - so 'sing soft' = the soft mode (Nectar) for every model.",
              "Voice: Hoshino Hanami (Lotte V) - its vocoder is CC BY-NC-SA: private listening only."]
    (AB / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    import importlib.util
    spec = importlib.util.spec_from_file_location('js_lyr', HERE / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    few = ("\n\n## f only: the sparse A (FEW_A) - fewer words, longer notes\n\n**A1**  " + mod.LYRICS_A1_FEW.replace('-', '')
           + "\n\n**A2**  " + mod.LYRICS_A2_FEW.replace('-', '') + "\n")
    (AB / 'lyrics.txt').write_text(lyr + few, encoding='utf-8')
    print(f"README    {AB / 'README.txt'}")


def main(argv) -> int:
    AB.mkdir(parents=True, exist_ok=True)
    nums_path = AB / 'calm_ab.json'
    nums = json.loads(nums_path.read_text(encoding='utf-8')) if nums_path.is_file() else {}
    if argv[1:] == ['--readme']:
        readme(nums)
        return 0
    want = argv[1:] or [n for n in VARIANTS if n not in nums]
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
