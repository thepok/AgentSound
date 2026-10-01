"""The vocal grit A/B in a ROCK context ('Exit Nine' over The Drummer Speaks' rock_band): the same takes, the same
band, the vocal hero clean and with grit (hero(..., grit=...): docs/COMPOSE_API.md "Vocals"), level-matched, into
out/grit_rock_ab/ with a README.txt and the numbers (grit_rock_ab.json):

    python songs/_demo_vocal_rock/grit_rock_ab.py [name ...]      # default: all (needs numpy for the measurements)

The measurements are songs/_demo_vocal/grit_ab.py's (BS.1770 LUFS of the lead vocal as heard = its stem + its grit
bus stem, the vocal's share of the mix's 2.5-6 kHz word band, singer.diction's coda_short / coda_buried from the takes,
each word-final consonant's level vs the end of its vowel in the rendered vocal, 2-8 kHz).
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
AB = OUT / 'grit_rock_ab'
sys.path.insert(0, str(REPO))
_spec = importlib.util.spec_from_file_location('grit_ab', REPO / 'songs' / '_demo_vocal' / 'grit_ab.py')
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

# name -> (env, what it is)
VARIANTS = {
    '1_tiger_clean': ({'VOICE': 'tiger', 'GRIT': 'clean'},
                      "TIGER (male rock voice; verse: his rock blend Fresh + Electric, chorus: leaning on Electric = "
                      "his power mode) over the rock band, the vocal hero clean - no amp"),
    '2_tiger_light': ({'VOICE': 'tiger', 'GRIT': 'light'},
                      "TIGER, light grit: a parallel tube-amp bus blended 9 dB under the clean vocal"),
    '3_tiger_crunch': ({'VOICE': 'tiger', 'GRIT': 'crunch'},
                       "TIGER, crunch: the parallel amp bus driven hard (gain 6 + overdrive push) blended 5 dB under "
                       "the clean vocal"),
    '4_hanami_clean': ({'VOICE': 'hanami', 'GRIT': 'clean'},
                       "Hanami an octave up (D4-A5; chorus leaning on Fragrance = her power mode), clean"),
    '5_hanami_crunch': ({'VOICE': 'hanami', 'GRIT': 'crunch'}, "Hanami an octave up, crunch"),
}
CLEAN_OF = {'2_tiger_light': '1_tiger_clean', '3_tiger_crunch': '1_tiger_clean', '5_hanami_crunch': '4_hanami_clean'}

LYRICS = (HERE / 'lyrics.txt').read_text(encoding='utf-8')


def _env(v: dict) -> dict:
    env = dict(os.environ)
    for k in ('VOICE', 'GRIT'):
        env.pop(f'AGENTSOUND_ROCK_{k}', None)
    env.update({f'AGENTSOUND_ROCK_{k}': val for k, val in v.items()})
    return env


def codas(env: dict):
    """The lead vocal's word-final consonants in song seconds (the takes' timelines) + singer.diction's findings."""
    old = dict(os.environ)
    os.environ.update(env)
    try:
        from agentsound import cli, singer
        song = cli.load_song(HERE / 'song.py')
        song.compile()
        out = []
        for vo in song.tracks['vocal']._singer['parts']:
            for r in vo.rendered:
                tl = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))['timeline']
                a = vo.notes[vo.phrases[r['phrase']][0]]
                t0 = song.seconds(a.start) + vo.offset_ms / 1000.0     # the timeline's times: from the first note
                out += [{'word': c['word'], 'ph': c['ph'], 'cls': c['cls'], 'a': t0 + c['a'], 'b': t0 + c['b']}
                        for c in tl.get('diction', []) if c['cls'] != 'release']
        return out, [f for f in singer.diction(song) if f['node'] == 'vocal']
    finally:
        os.environ.clear()
        os.environ.update(old)


def measure(name: str) -> dict:
    env = {f'AGENTSOUND_ROCK_{k}': v for k, v in VARIANTS[name][0].items()}
    rep = json.loads((OUT / 'report.json').read_text(encoding='utf-8'))
    nodes = {n['id']: n for n in rep['nodes']}
    v, fs = G._read(OUT / 'stems' / 'vocal.wav')
    g = OUT / 'stems' / 'vocal_grit.wav'
    if g.is_file():
        v = v + G._read(g)[0]
    share = (nodes['vocal'].get('mixSharePct') or {}).get('presence', 0.0)
    gshare = (nodes.get('vocal_grit', {}).get('mixSharePct') or {}).get('presence', 0.0)
    cs, dic = codas(env)
    mono = v.mean(axis=1, keepdims=True)
    hi = G._sos(mono, [G._rbj('hp', 2000, fs), G._rbj('hp', 2000, fs), G._rbj('lp', 8000, fs),
                       G._rbj('lp', 8000, fs)], fs)
    rows = []
    for c in cs:
        i0, i1 = int(c['a'] * fs), int(c['b'] * fs)
        j0 = max(0, i0 - int(0.12 * fs))
        if i1 - i0 < 32 or i0 - j0 < 32:
            continue
        rows.append({'word': c['word'], 'ph': c['ph'], 'cls': c['cls'], 'at': round(c['a'], 3),
                     'cvr_db': round(G._db(mono[i0:i1]) - G._db(mono[j0:i0]), 2),
                     'cvr_hi_db': round(G._db(hi[i0:i1]) - G._db(hi[j0:i0]), 2)})
    secs = {x['name']: x.get('lufs') for x in rep.get('sections', [])}
    return {'mix_lufs': rep['global']['lufsIntegrated'], 'section_lufs': secs, 'clicks': rep['global'].get('clicks'),
            'vocal_lufs': round(G.lufs(v, fs), 2), 'vocal_node_lufs': nodes['vocal'].get('lufs'),
            'grit_bus_lufs': nodes.get('vocal_grit', {}).get('lufs'),
            'presence_share_pct': round(share + gshare, 1), 'presence_share_clean_path_pct': share,
            'diction': [f['message'] for f in dic], 'diction_info': [f for f in dic if f['severity'] == 'info'],
            'diction_warnings': [f for f in dic if f['severity'] != 'info'],
            'coda_buried': [f for f in dic if f['code'] == 'coda_buried'],
            'codas': rows}


def main(argv) -> int:
    want = argv[1:] or list(VARIANTS)
    bad = [w for w in want if w not in VARIANTS]
    if bad:
        print(f"unknown variant(s) {bad}; variants: {', '.join(VARIANTS)}")
        return 2
    AB.mkdir(parents=True, exist_ok=True)
    nums_path = AB / 'grit_rock_ab.json'
    nums = json.loads(nums_path.read_text(encoding='utf-8')) if nums_path.is_file() else {}
    for name in want:
        print(f"=== {name}")
        shutil.rmtree(OUT / 'stems', ignore_errors=True)     # (a stale grit stem must not count)
        r = subprocess.run([sys.executable, '-m', 'agentsound', 'build', str(HERE), '--stems'],
                           env=_env(VARIANTS[name][0]), cwd=str(REPO))
        if r.returncode != 0:
            print(f"variant {name} failed (exit {r.returncode})")
            return r.returncode
        shutil.copyfile(OUT / 'mix.mp3', AB / f'{name}.mp3')
        nums[name] = measure(name)
        nums_path.write_text(json.dumps(nums, indent=1), encoding='utf-8')
    readme(nums)
    return 0


def readme(nums: dict) -> None:
    lines = ["Vocal grit A/B in a ROCK context - 'Exit Nine' (songs/_demo_vocal_rock): a sung lead over the band of",
             "The Drummer Speaks (rock_band as it is now: Big Rusty kit, the double-tracked riff through the Plexi amp,",
             "the bass rig, the organ), 116 BPM, E minor, 2 bars riff + verse (8 bars) + chorus (8 bars) + the final hit.",
             "The same takes and band in every file; only the vocal's grit (and the voice) changes.",
             "Question: does amp grit on the voice work over a REAL rock band (it was disliked over the soft pop demo)?",
             "", "Lyrics (original):", *("  " + x for x in LYRICS.rstrip().splitlines()), "",
             "Files (level-matched: the lead vocal as heard - clean path + grit bus - lands at the clean level;",
             "the master chain is identical, so the mixes land within a few tenths of a LU):"]
    for name, (_, what) in VARIANTS.items():
        n = nums.get(name)
        if n is None:
            continue
        ref = nums.get(CLEAN_OF.get(name, ''))
        lv = (f", vocal {n['vocal_lufs'] - ref['vocal_lufs']:+.2f} LU vs clean, mix "
              f"{n['mix_lufs'] - ref['mix_lufs']:+.2f} LU vs clean") if ref else ''
        lines.append(f"  {name}.mp3 - {what}")
        lines.append(f"      mix {n['mix_lufs']:.1f} LUFS, vocal {n['vocal_lufs']:.1f} LUFS{lv}; the clean vocal alone "
                     f"owns {n['presence_share_clean_path_pct']:.0f} % of the mix's 2.5-6 kHz word band"
                     + (f" (with its grit {min(100.0, n['presence_share_pct']):.0f} %)"
                        if n['presence_share_pct'] != n['presence_share_clean_path_pct'] else ''))
        warn = n['diction_warnings']
        info = '; '.join(f['message'] for f in n.get('diction_info', [])) or '; '.join(n['diction'])
        lines.append(f"      diction: {len(n['coda_buried'])} coda_buried, "
                     f"{sum(f['code'] == 'coda_short' for f in warn)} coda_short ({info})")
        if ref and len(ref['codas']) == len(n['codas']):
            d = sorted((c['cvr_hi_db'] - b['cvr_hi_db'], c['word'], c['ph']) for c, b in zip(n['codas'], ref['codas']))
            lines.append(f"      word-final consonants vs their vowel (2-8 kHz) against clean: median "
                         f"{d[len(d) // 2][0]:+.1f} dB, worst {d[0][0]:+.1f} dB ('{d[0][1]}' /{d[0][2]}/)")
    lines += ["", "Grit = the guitar amp of the guitar heroes (the engine's tube 'amp') in PARALLEL under the untouched",
              "clean vocal (every consonant stays on the clean path); only the vowels get the edge.",
              "Voices: TIGER (tigermeat) and Hanami (Lotte V) - both NON-COMMERCIAL: private listening only."]
    (AB / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"README    {AB / 'README.txt'}")


if __name__ == '__main__':
    sys.exit(main(sys.argv))
