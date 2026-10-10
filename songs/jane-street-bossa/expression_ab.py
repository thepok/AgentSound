"""Singer-expression A/B for 'Down on Jane Street' (agentsound.singer: back_phrase, ornament, messa_di_voce, emphasis):

    python songs/jane-street-bossa/expression_ab.py [name ...]     # default: every variant not rendered yet
    python songs/jane-street-bossa/expression_ab.py --readme       # only rewrite README.txt from expression_ab.json

The out chorus' A2 + C (beats 320-384, ~38 s at 100 BPM: the hook, "let you be, let you go", the climax "down on Jane
Street, rain" and the last line) through the whole mix and master, level-matched to a (BS.1770 integrated) into
out/expression_ab/<name>.mp3, with what the singer did and what the vocal stem measures in expression_ab.json, a
README.txt and the lyrics. Each variant sets the song's options (BACK_PHRASE, ORNAMENTS, MESSA, EMPHASIS); the words
are the same in every variant (the markup changes how they are sung, not what is sung).
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
from dry_ab import _write    # noqa: E402

OUT = HERE / 'out'
AB = OUT / 'expression_ab'
FROM, TO = 320.0, 384.0      # head out: A2 + C


def _variant(back=False, orn=False, messa=False, emph=False):
    def before(mod):
        mod.BACK_PHRASE, mod.ORNAMENTS, mod.MESSA, mod.EMPHASIS = back, orn, messa, emph
    return before


VARIANTS = {
    'a_current': (_variant(), "the song as it ships: none of the four (the cached takes)"),
    'b_back_phrasing': (_variant(back=True),
                        "+ BACK-PHRASING: a phrase starts 1/8-1/4 beat behind the band and is back on the written "
                        "rhythm at its landing note (the next bar line); never early"),
    'c_ornaments_out': (_variant(orn='out'),
                        "+ ORNAMENTS on the out chorus (the melody's 2nd / 3rd statement): a run on 'rain', grace "
                        "notes, an anticipation, a blue note - the syllables stay where they are"),
    'd_messa_di_voce': (_variant(messa=True),
                        "+ MESSA DI VOCE on the held peaks (the voice mode toward the core and the level after the "
                        "compressor swell and recede); the phrase-end holds keep the mic pull"),
    'e_all_four': (_variant(back=True, orn='out', messa=True, emph=True),
                   "all four, + the lyrics' markup: ((let you be, let you go,)) intimate, *late* and *keep* leaned "
                   "into"),
}


def _syllables(song, span) -> list:
    """Every sung syllable of the lead in the span, in order: word, vowel start / end (song seconds)."""
    from agentsound.lyrics import VOWELS
    out = []
    for vo, r, d, t0, ph in sorted(W._parts(song, 'vocal', None), key=lambda x: x[3]):
        tl, sp = d['timeline'], d['spec']
        syl = [n for n in sp['notes'] if n['k'] == 'syllable']
        toks = tl['tokens']
        for n, V in zip(syl, tl['vowels']):
            j = next((i for i, tk in enumerate(toks) if tk[0] in VOWELS and abs(tk[1] - V) < 0.02), None)
            e = V + 0.1
            if j is not None:
                e = toks[j][2]
                while j + 1 < len(toks) and toks[j + 1][0] == toks[j][0] and abs(toks[j + 1][1] - e) < 1e-3:
                    j += 1
                    e = toks[j][2]
            if span[0] - 0.3 <= t0 + V < span[1]:
                out.append({'word': n.get('w', ''), 'a': round(t0 + V, 4), 'b': round(t0 + e, 4)})
    return out


def _level(x, fs, t_off, a, b) -> float:
    import numpy as np
    seg = x[max(0, int((a - t_off) * fs)):max(0, int((b - t_off) * fs))].mean(axis=1)
    return round(float(10 * np.log10(np.mean(seg ** 2) + 1e-12)), 2) if len(seg) > 64 else float('nan')


def _tilt(x, fs, t_off, a, b) -> float:
    """2-6 kHz vs 0.2-1 kHz of the stem in [a, b] (dB): brightness."""
    import numpy as np
    seg = x[max(0, int((a - t_off) * fs)):max(0, int((b - t_off) * fs))].mean(axis=1)
    if len(seg) < 1024:
        return float('nan')
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    fr = np.fft.rfftfreq(len(seg), 1 / fs)
    return round(float(10 * np.log10((sp[(fr >= 2000) & (fr < 6000)].sum() + 1e-12)
                                     / (sp[(fr >= 200) & (fr < 1000)].sum() + 1e-12))), 2)


def render(name: str) -> dict:
    from agentsound import cli, singer
    before, _ = VARIANTS[name]
    song = W.load(HERE / 'song.py', before=before)
    song.export(stems=True)
    rnd = song.compile()
    rdir = OUT / 'expression_ab_render' / name
    shutil.rmtree(rdir, ignore_errors=True)
    rj = cli.write_render(rnd, rdir / 'song.render.json')
    cli.run_engine(cli.find_engine(), rj, rdir, FROM, TO, rnd)
    shutil.copyfile(rdir / 'mix.wav', AB / f'{name}.raw.wav')
    shutil.copyfile(rdir / 'stems' / 'vocal.wav', AB / f'{name}.vocal_stem.wav')
    x, fs = G._read(rdir / 'mix.wav')
    v, _ = G._read(rdir / 'stems' / 'vocal.wav')
    span = (song.seconds(FROM), song.seconds(TO))
    rep = json.loads((rdir / 'report.json').read_text(encoding='utf-8'))
    parts = [vo for vo in song.tracks['vocal']._singer['parts'] if FROM - 1 <= vo.notes[0].start < TO]
    ex = {'back_phrase': [], 'ornaments': [], 'messa': [], 'emphasis': [], 'post': [], 'mic_pulls': []}
    for vo in parts:
        for k in ('back_phrase', 'ornaments', 'messa', 'emphasis', 'post'):
            ex[k] += [dict(d) for d in vo.expression[k]]
        ex['mic_pulls'] += [{'word': m.get('word'), 'db': m.get('db'), 'at_s': m.get('at_s')}
                            for m in (vo.mic_pulls or [])]
    whole = [vo for vo in song.tracks['vocal']._singer['parts']]
    return {'mix_lufs': round(G.lufs(x, fs), 2), 'vocal_lufs': round(G.lufs(v, fs), 2), 'span_s': list(span),
            'clicks': rep.get('global', {}).get('clicks'), 'expression': ex,
            'song': {k: sum(len(vo.expression[k]) for vo in whole) for k in ('back_phrase', 'ornaments', 'messa',
                                                                            'emphasis')},
            'lines': singer.expression_lines(song),
            'diction_warnings': [f['message'] for f in singer.diction(song) if f['severity'] == 'warn'],
            'syllables': _syllables(song, span), 'timing': W.timing(song, span=span)}


def measure(nums: dict) -> None:
    """The differences against a, from the takes' timelines (timing) and the vocal stems (level, brightness)."""
    import numpy as np
    a = nums.get('a_current')
    if not a:
        return
    t_off = a['span_s'][0]
    xa, fs = G._read(AB / 'a_current.vocal_stem.wav')
    for name, n in nums.items():
        if name == 'a_current' or not (AB / f'{name}.vocal_stem.wav').is_file():
            continue
        x, _ = G._read(AB / f'{name}.vocal_stem.wav')
        sa, sn = a['syllables'], n['syllables']
        m = {'same_syllables': [s['word'] for s in sa] == [s['word'] for s in sn], 'syllables': len(sn)}
        if m['same_syllables']:
            d = [(q['a'] - p['a']) * 1000.0 for p, q in zip(sa, sn)]
            late = [v for v in d if v > 15.0]
            m['onset_shift_ms'] = {'moved': len(late), 'early': sum(v < -15.0 for v in d),
                                   'median_of_moved': round(float(np.median(late)), 1) if late else 0.0,
                                   'max': round(max(d), 1), 'min': round(min(d), 1),
                                   'mean_all': round(float(np.mean(d)), 1)}
            m['post'] = []
            for p in n['expression']['post']:
                idx = [i for i, s in enumerate(sn) if p['at_s'] - 0.08 <= s['a'] < p.get('end_s', p['at_s'] + 60.0 /
                       100.0 * (p['end_beat'] - p['beat'])) - 0.02]
                if not idx:
                    continue
                rec = {'kind': p['kind'], 'word': p.get('word') or p.get('words'),
                       'clip_s': round(p['at_s'] - t_off, 2)}
                if p['kind'] == 'messa':
                    i = idx[0]
                    thirds = []
                    for k in range(3):
                        (a0, b0), (a1, b1) = [(s['a'] + (s['b'] - s['a']) * k / 3, s['a'] + (s['b'] - s['a']) * (k + 1)
                                               / 3) for s in (sa[i], sn[i])]
                        thirds.append(round(_level(x, fs, t_off, a1, b1) - _level(xa, fs, t_off, a0, b0), 2))
                    rec.update(planned_db=[p['lo'], p['peak'], p['end']], measured_thirds_db=thirds,
                               held_s=round(sn[i]['b'] - sn[i]['a'], 2))
                else:
                    lv = [_level(x, fs, t_off, sn[i]['a'], sn[i]['b']) - _level(xa, fs, t_off, sa[i]['a'], sa[i]['b'])
                          for i in idx]
                    tl = [_tilt(x, fs, t_off, sn[i]['a'], sn[i]['b']) - _tilt(xa, fs, t_off, sa[i]['a'], sa[i]['b'])
                          for i in idx]
                    ln = [(sn[i]['b'] - sn[i]['a']) - (sa[i]['b'] - sa[i]['a']) for i in idx]
                    rec.update(planned_db=p['db'], vowels=len(idx),
                               measured_level_db=round(float(np.nanmean(lv)), 2),
                               measured_tilt_db=round(float(np.nanmean(tl)), 2),
                               vowel_longer_ms=round(1000.0 * float(np.mean(ln)), 1))
                m['post'].append(rec)
        n['vs_a'] = m


def matched(nums: dict) -> None:
    from agentsound import cli
    ref = nums.get('a_current', {}).get('mix_lufs')
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
    import importlib.util
    spec = importlib.util.spec_from_file_location('js_lyr', HERE / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a2, c = mod.LYRICS_A2_FEW.replace('-', ''), mod.LYRICS_C_OUT.replace('-', '')
    plain = lambda s: s.replace('*', '').replace('((', '').replace('))', '')     # noqa: E731
    L = ["'Down on Jane Street' - singer-expression A/B (agentsound.singer: back_phrase, ornament, messa_di_voce,",
         "emphasis). The out chorus' A2 + C (beats 320-384, ~38 s), the whole mix and master, level-matched to a",
         "(BS.1770 integrated; the gain is listed). The words are the same in every file.", "",
         "Files:"]
    for name, (_, what) in VARIANTS.items():
        n = nums.get(name)
        if n is None:
            continue
        t0 = n['span_s'][0]
        ex, m = n['expression'], n.get('vs_a', {})
        L += [f"  {name}.mp3 - {what}",
              f"      mix {n['mix_lufs']:.2f} LUFS (matched {n.get('match_gain_db', 0.0):+.2f} dB), vocal stem "
              f"{n['vocal_lufs']:.2f} LUFS, clicks {n['clicks']}, diction warnings {len(n['diction_warnings'])}; "
              f"vowels {n['timing']['vowel_ms_median']:+.0f} ms vs their (sung) note, P-centre "
              f"{n['timing']['p_centre_ms']:+.0f} ms"]
        if ex['back_phrase']:
            L.append("      back-phrased: " + '; '.join(
                f"'{b['word']}' at {song_t(b['beat'], t0):.1f} s starts {b['ms']:+.0f} ms ({b['beats']:+.2f} beat), "
                f"{b['notes']} notes moved, mean {b['mean_ms']:+.0f} ms, on the grid again at beat {b['land']:g}"
                for b in ex['back_phrase']))
        sh = m.get('onset_shift_ms')
        if sh and (ex['back_phrase'] or sh['moved']):
            L.append(f"      measured (the takes' vowel onsets vs a): {sh['moved']} of {m['syllables']} syllables later "
                     f"(median {sh['median_of_moved']:+.0f} ms, max {sh['max']:+.0f} ms), {sh['early']} earlier; all "
                     f"others within 15 ms")
        if ex['ornaments']:
            L.append("      ornaments: " + '; '.join(
                f"{o['kind']} on '{o['word']}' at {song_t(o['beat'], t0):.1f} s"
                + (f" (notes {o['notes']})" if 'notes' in o else f" ({o['cents']:+.0f} ct, bent up over {o['ms']:.0f} ms)")
                for o in ex['ornaments']) + f" - {m.get('syllables')} syllables, the same words as a: "
                f"{m.get('same_syllables')}")
        for p in m.get('post', []):
            if p['kind'] == 'messa':
                L.append(f"      messa di voce on '{p['word']}' at {p['clip_s']:.1f} s ({p['held_s']} s vowel): planned "
                         f"{p['planned_db'][0]:+.1f} / {p['planned_db'][1]:+.1f} / {p['planned_db'][2]:+.1f} dB (start / "
                         f"peak / end), the vocal stem vs a by thirds of the vowel {p['measured_thirds_db'][0]:+.1f} / "
                         f"{p['measured_thirds_db'][1]:+.1f} / {p['measured_thirds_db'][2]:+.1f} dB")
            else:
                L.append(f"      {p['kind']} '{p['word']}' at {p['clip_s']:.1f} s: planned {p['planned_db']:+.1f} dB, the "
                         f"vocal stem's vowels vs a {p['measured_level_db']:+.1f} dB, brightness (2-6 kHz vs 0.2-1 kHz) "
                         f"{p['measured_tilt_db']:+.1f} dB, vowel length {p['vowel_longer_ms']:+.0f} ms")
        if ex['mic_pulls']:
            L.append("      mic pulls (phrase-end holds, as before): " + ', '.join(
                f"'{p['word']}' {p['db']:+.1f} dB" for p in ex['mic_pulls']))
        if name != 'a_current':
            s = n['song']
            L.append(f"      in the whole song: {s['back_phrase']} back-phrased phrases, {s['ornaments']} ornaments, "
                     f"{s['messa']} messa di voce, {s['emphasis']} marked words")
    L += ["", "Lyrics (the out chorus' A2 + C; e sings the markup - the words are unchanged):",
          "  " + plain(a2), "  " + plain(c), "  e: " + a2, "     " + c,
          "", "Options in song.py: BACK_PHRASE, ORNAMENTS (False | 'out' | True), MESSA, EMPHASIS - all False in the",
          "shipped render until the user has heard this A/B.",
          "Voice: Hoshino Hanami (Lotte V) - its vocoder is CC BY-NC-SA: private listening only."]
    (AB / 'README.txt').write_text('\n'.join(L) + '\n', encoding='utf-8')
    (AB / 'lyrics.txt').write_text('\n'.join(["A2  " + plain(a2), "C   " + plain(c), "", "e (the markup):",
                                              "A2  " + a2, "C   " + c]) + '\n', encoding='utf-8')
    print(f"README    {AB / 'README.txt'}")


def song_t(beat: float, t0: float, bpm: float = 100.0) -> float:
    """Seconds into the clip of a song beat (the song has one tempo up to the tag)."""
    return beat * 60.0 / bpm - t0


def main(argv) -> int:
    AB.mkdir(parents=True, exist_ok=True)
    nums_path = AB / 'expression_ab.json'
    nums = json.loads(nums_path.read_text(encoding='utf-8')) if nums_path.is_file() else {}
    if argv[1:] != ['--readme']:
        want = argv[1:] or [n for n in VARIANTS if n not in nums]
        for name in want:
            if name not in VARIANTS:
                print(f"unknown variant {name!r}: {', '.join(VARIANTS)}")
                return 2
            print(f"=== {name}")
            nums[name] = render(name)
            nums_path.write_text(json.dumps(nums, indent=1), encoding='utf-8')
        measure(nums)
        matched(nums)
        nums_path.write_text(json.dumps(nums, indent=1), encoding='utf-8')
    readme(nums)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
