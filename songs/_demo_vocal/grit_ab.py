"""The vocal grit A/B ("kann man die Stimmen mit dem Gitarren-Amp rauer machen?"): the same take, the same band, the
vocal hero clean and with its three grit amounts (hero(..., grit=...): docs/COMPOSE_API.md "Vocals"), level-matched,
into out/grit_ab/ with a README.txt and the numbers (grit_ab.json):

    python songs/_demo_vocal/grit_ab.py [name ...]        # default: all (needs numpy for the measurements)

Per variant: the mix (LUFS-I), the lead vocal as heard = its stem + its grit bus stem (LUFS-I, vs the clean one: the
level match), the vocal's share of the mix's 2.5-6 kHz presence band (singer.check's intelligibility; its grit bus
counted with it), singer.diction (coda_short / coda_buried from the takes), and the word-final consonants measured in
the rendered audio: each coda's level against the end of its vowel (consonant-to-vowel ratio, dB, broadband and
2-8 kHz) - the grit must not bury them, so the change vs the clean render is reported per variant.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / 'out'
AB = OUT / 'grit_ab'
sys.path.insert(0, str(REPO))

LYRICS = ("City lights are calling out, each window gold and blue.\n"
          "Hold me close and say it loud, all the night belongs to you.")

# name -> (env, what it is)
VARIANTS = {
    '1_clean': ({'VARIANT': 'full', 'GRIT': 'clean'},
                "Hanami over the band (piano, pad, fretless bass), the vocal hero as before: no amp"),
    '2_light': ({'VARIANT': 'full', 'GRIT': 'light'},
                "light grit: a parallel amp bus (300 Hz-5 kHz into the tube amp, gain 3.5) blended 9 dB under the clean "
                "vocal - a little edge on the vowels"),
    '3_crunch': ({'VARIANT': 'full', 'GRIT': 'crunch'},
                 "crunch: the parallel amp bus driven harder (gain 6 + a 4 dB overdrive push) blended 5 dB under the clean "
                 "vocal - audibly rough, the words carried by the clean path"),
    '4_megaphone': ({'VARIANT': 'full', 'GRIT': 'megaphone'},
                    "megaphone / bullhorn: the WHOLE voice band-limited (550 Hz-3.8 kHz, 48 dB/oct, horn "
                    "resonance) and driven through the amp - an effect for a line or a bridge, not a whole song"),
    '5_dry_clean': ({'VARIANT': 'chain', 'GRIT': 'clean'},
                    "the vocal alone through the vocal hero chain, no band, no reverb (reference for 6 and 7)"),
    '6_dry_light': ({'VARIANT': 'chain', 'GRIT': 'light'}, "the vocal alone, light grit, no band, no reverb"),
    '7_dry_crunch': ({'VARIANT': 'chain', 'GRIT': 'crunch'}, "the vocal alone, crunch, no band, no reverb"),
    '8_tiger_clean': ({'VARIANT': 'full', 'GRIT': 'clean', 'VOICE': 'tiger'},
                      "TIGER (male rock / pop voice, an octave down, style 'rock') over the same band, clean"),
    '9_tiger_crunch': ({'VARIANT': 'full', 'GRIT': 'crunch', 'VOICE': 'tiger'},
                       "TIGER with crunch - the rock voice through the amp"),
}
CLEAN_OF = {'2_light': '1_clean', '3_crunch': '1_clean', '4_megaphone': '1_clean', '6_dry_light': '5_dry_clean',
            '7_dry_crunch': '5_dry_clean', '9_tiger_crunch': '8_tiger_clean'}


def _env(v: dict) -> dict:
    env = dict(os.environ)
    for k in ('VARIANT', 'GRIT', 'VOICE'):
        env.pop(f'AGENTSOUND_VOCAL_{k}', None)
    env.update({f'AGENTSOUND_VOCAL_{k}': val for k, val in v.items()})
    return env


# ------------------------------------------------------------------------------------------------ measuring

def _read(path: Path):
    import numpy as np
    with wave.open(str(path), 'rb') as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, '<i2').astype(np.float64) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        x = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float64) / (1 << 23)
    else:
        x = np.frombuffer(raw, '<i4').astype(np.float64) / 2147483648.0
    return x.reshape(-1, ch), sr


def _sos(x, sections, fs):
    """x through the biquads' magnitude responses (zero-phase, in the frequency domain: for level measurements)."""
    import numpy as np
    n = x.shape[0]
    X = np.fft.rfft(x, axis=0)
    z = np.exp(-1j * 2 * np.pi * np.fft.rfftfreq(n, 1.0 / fs) / fs)
    H = np.ones(len(z))
    for b, a in sections:
        H = H * np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))
    return np.fft.irfft(X * H[:, None], n=n, axis=0)


def _rbj(kind, f0, fs, q=0.7071, gain_db=0.0):
    w = 2 * math.pi * f0 / fs
    al = math.sin(w) / (2 * q)
    c = math.cos(w)
    A = 10 ** (gain_db / 40)
    if kind == 'hp':
        b, a = [(1 + c) / 2, -(1 + c), (1 + c) / 2], [1 + al, -2 * c, 1 - al]
    elif kind == 'lp':
        b, a = [(1 - c) / 2, 1 - c, (1 - c) / 2], [1 + al, -2 * c, 1 - al]
    else:   # high shelf
        sq = 2 * math.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    return [v / a[0] for v in b], [1.0, a[1] / a[0], a[2] / a[0]]


def lufs(x, fs) -> float:
    """BS.1770 integrated loudness (K-weighting, 400 ms blocks, absolute + relative gates)."""
    import numpy as np
    y = _sos(x, [_rbj('shelf', 1681.97, fs, 0.7072, 3.9998), _rbj('hp', 38.13, fs, 0.5003)], fs)
    blk, hop = int(0.4 * fs), int(0.1 * fs)
    ms = np.array([np.mean(y[i:i + blk] ** 2, axis=0).sum() for i in range(0, len(y) - blk, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-20)
    g = ms[lk > -70]
    if not len(g):
        return -120.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = g[(-0.691 + 10 * np.log10(g + 1e-20)) > rel]
    return float(-0.691 + 10 * np.log10(g.mean()))


def _db(x) -> float:
    import numpy as np
    return float(10 * np.log10(np.mean(x ** 2) + 1e-20))


def codas(env: dict) -> list:
    """The lead vocal's word-final consonants in song seconds: [{'word', 'ph', 'a', 'b'}] (the takes' timelines)."""
    old = dict(os.environ)
    os.environ.update(env)
    try:
        from agentsound import cli
        song = cli.load_song(HERE / 'song.py')
        song.compile()        # the singer's compile hook: the cached takes, their timelines
        t = song.tracks['vocal']
        out = []
        for vo in t._singer['parts']:
            for r in vo.rendered:
                meta = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))
                tl = meta['timeline']
                a = vo.notes[vo.phrases[r['phrase']][0]]
                t0 = song.seconds(a.start) + vo.offset_ms / 1000.0     # the timeline's times: from the first note
                out += [{'word': c['word'], 'ph': c['ph'], 'cls': c['cls'], 'a': t0 + c['a'], 'b': t0 + c['b']}
                        for c in tl.get('diction', []) if c['cls'] != 'release']
        from agentsound import singer
        dic = [f for f in singer.diction(song) if f['node'] == 'vocal']
        return out, dic
    finally:
        os.environ.clear()
        os.environ.update(old)


def measure(name: str) -> dict:
    import numpy as np
    env = {f'AGENTSOUND_VOCAL_{k}': v for k, v in VARIANTS[name][0].items()}
    rep = json.loads((OUT / 'report.json').read_text(encoding='utf-8'))
    nodes = {n['id']: n for n in rep['nodes']}
    v, fs = _read(OUT / 'stems' / 'vocal.wav')
    g = OUT / 'stems' / 'vocal_grit.wav'
    if g.is_file():
        v = v + _read(g)[0]
    share = (nodes['vocal'].get('mixSharePct') or {}).get('presence', 0.0)
    gshare = (nodes.get('vocal_grit', {}).get('mixSharePct') or {}).get('presence', 0.0)
    cs, dic = codas(env)
    mono = v.mean(axis=1, keepdims=True)
    hi = _sos(mono, [_rbj('hp', 2000, fs), _rbj('hp', 2000, fs), _rbj('lp', 8000, fs), _rbj('lp', 8000, fs)], fs)
    rows = []
    for c in cs:
        i0, i1 = int(c['a'] * fs), int(c['b'] * fs)
        j0 = max(0, i0 - int(0.12 * fs))
        if i1 - i0 < 32 or i0 - j0 < 32:
            continue
        rows.append({'word': c['word'], 'ph': c['ph'], 'cls': c['cls'], 'at': round(c['a'], 3),
                     'cvr_db': round(_db(mono[i0:i1]) - _db(mono[j0:i0]), 2),
                     'cvr_hi_db': round(_db(hi[i0:i1]) - _db(hi[j0:i0]), 2)})
    return {'mix_lufs': rep['global']['lufsIntegrated'], 'clicks': rep['global'].get('clicks'), 'vocal_lufs': round(lufs(v, fs), 2),
            'vocal_node_lufs': nodes['vocal'].get('lufs'), 'grit_bus_lufs': nodes.get('vocal_grit', {}).get('lufs'),
            'presence_share_pct': round(share + gshare, 1), 'presence_share_clean_path_pct': share,
            'diction': [f['message'] for f in dic], 'diction_warnings': [f for f in dic if f['severity'] != 'info'],
            'codas': rows}


# ------------------------------------------------------------------------------------------------ main

def main(argv) -> int:
    want = argv[1:] or list(VARIANTS)
    bad = [w for w in want if w not in VARIANTS]
    if bad:
        print(f"unknown variant(s) {bad}; variants: {', '.join(VARIANTS)}")
        return 2
    AB.mkdir(parents=True, exist_ok=True)
    nums_path = AB / 'grit_ab.json'
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
    lines = ["Vocal grit A/B - 'Gold and Blue' (songs/_demo_vocal), the same take and band in every file.",
             "Question: kann man die Stimmen mit dem Gitarren-Amp rauer machen? - yes: hero(vox.track, "
             "family='vocal', grit='light' | 'crunch' | 'megaphone').", "",
             "Lyrics:", *("  " + x for x in LYRICS.splitlines()), "",
             "Files (level-matched: the lead vocal as heard - clean path + grit - lands at the clean level):"]
    for name, (_, what) in VARIANTS.items():
        n = nums.get(name)
        if n is None:
            continue
        ref = nums.get(CLEAN_OF.get(name, ''))
        lv = f", vocal {n['vocal_lufs'] - ref['vocal_lufs']:+.1f} LU vs clean" if ref else ''
        lines.append(f"  {name}.mp3 - {what}")
        lines.append(f"      mix {n['mix_lufs']:.1f} LUFS, vocal {n['vocal_lufs']:.1f} LUFS{lv}; the clean vocal alone "
                     f"owns {n['presence_share_clean_path_pct']:.0f} % of the mix's 2.5-6 kHz word band"
                     + (f" (with its grit {min(100.0, n['presence_share_pct']):.0f} %)"
                        if n['presence_share_pct'] != n['presence_share_clean_path_pct'] else ''))
        if ref and len(ref['codas']) == len(n['codas']):
            d = sorted((c['cvr_hi_db'] - b['cvr_hi_db'], c['word'], c['ph']) for c, b in zip(n['codas'], ref['codas']))
            out_t = next((x for x in d if x[1] == 'out'), None)
            lines.append(f"      word-final consonants vs their vowel (2-8 kHz) against clean: median "
                         f"{d[len(d) // 2][0]:+.1f} dB, worst {d[0][0]:+.1f} dB ('{d[0][1]}' /{d[0][2]}/)"
                         + (f", 'out' /t/ {out_t[0]:+.1f} dB" if out_t else ''))
    lines += ["", "Grit = the guitar amp of the guitar heroes (the engine's tube 'amp'): light / crunch run in PARALLEL",
              "under the untouched clean vocal (so every consonant stays - the 't' of 'out'), megaphone replaces the",
              "whole voice. Voices: Hanami (Lotte V) and TIGER - both NON-COMMERCIAL: private listening only."]
    (AB / 'README.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"README    {AB / 'README.txt'}")


if __name__ == '__main__':
    sys.exit(main(sys.argv))
