"""Blind "Turing test" packets for NEW-AGE solo piano: composed pieces (letters-to-the-morning + the pro-newage-*
references) vs endless new-age tunes, anonymized.

    python songs/_blind/make_packets_newage.py      # -> songs/_blind/packets_newage/<ID>.txt + KEY_newage.json

Every piece is rebuilt from its source (a song.py; an endless tune folder: recomposed from its tune.json by
run.load_scored, the same call the score command makes), compiled to the render JSON (no audio render) and written
through ONE extraction path: header, chord chart, per-bar notation (the right hand's top line + every left-hand
attack), analysis from its report.json. Nothing that names the source (title, seed, mood, feel name, file names)
reaches a packet. Judges read packets_newage/ (copied as packets/) + JUDGE_NEWAGE.md (copied as JUDGE.md) in an
isolated folder; nobody reads KEY_newage.json - score_round.py does.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from make_packets import Speller, check_notes, num, q  # noqa: E402
from agentsound.endless.run import load_scored  # noqa: E402
from agentsound.theory import chord as _chord  # noqa: E402

ROUND = sys.argv[1] if len(sys.argv) > 1 else 'r5'      # (python make_packets_newage.py ROUND [tune folders ...])
NA = ROOT / 'songs' / '_endless_piano' / 'out' / f"na_{ROUND}" / 'new-age'
_RN = int(ROUND[1:]) if ROUND[1:].isdigit() else 0
COMPOSED = ['letters-to-the-morning', 'pro-newage-rain', 'pro-newage-hopeful', 'pro-newage-waltz'] if _RN <= 5 else \
    ['letters-to-the-morning', 'pro-newage-waltz', 'pro-newage-lantern', 'pro-newage-homecoming'] if _RN <= 8 else \
    ['letters-to-the-morning', 'pro-newage-homecoming', 'pro-newage-longing', 'pro-newage-skylight']
# (r6: set 2 joins; r9: three of set 2 - the 3/4 longing and the 6/8 skylight)
GENERATED = sys.argv[2:] or (['001-gardens-to-autumn', '003-hidden-mirrors-of-spring', '005-before-the-sea',
                              '007-before-the-hills'] if ROUND == 'r5' else [])
ID_SEED = f"blind-new-age-{ROUND}"
OUT_DIR = HERE / 'packets_newage'
KEY_FILE = HERE / 'KEY_newage.json'
GRID = 12
CLUSTER = 0.1


# ------------------------------------------------------------------------------------------------ the sources

def load_composed(folder: Path):
    """(song, key, tempo, timeline [(beat, beats, chord)], report) of a song.py: the chord per bar from its LH dict
    ('CHORD:figure' entries splitting the bar evenly)."""
    spec = importlib.util.spec_from_file_location('blindna_' + folder.name.replace('-', '_'), folder / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(folder))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
            song = mod.build()
    finally:
        sys.path.remove(str(folder))
    m = float(song.beats_per_bar)
    tl = []
    for k in sorted(mod.LH):
        parts = mod.LH[k].split()
        span = m / len(parts)
        for i, part in enumerate(parts):
            tl.append(((k - 1) * m + i * span, span, part.split(':')[0]))
    report = json.loads((folder / 'out' / 'report.json').read_text(encoding='utf-8'))
    key = song.key.name if hasattr(song.key, 'name') else str(song.key)
    return song, key, getattr(mod, 'TEMPO', None) or song.tempo, tl, report


def load_generated(folder: Path):
    song, tune, _ = load_scored(folder)
    info = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
    if tune.title != info['title']:
        raise SystemExit(f"{folder.name}: recomposed '{tune.title}', delivered '{info['title']}'")
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
    return song, tune.key, tune.tempo, list(song.endless_timeline), report


# ------------------------------------------------------------------------------------------------ the packet

def clusters(notes):
    out = []
    for n in sorted(notes, key=lambda n: (n[0], -n[2])):
        if out and (n[0] - out[-1][-1][0] < CLUSTER or q(n[0]) == q(out[-1][0][0])):
            out[-1].append(n)
        else:
            out.append([n])
    return out


def sections(song) -> list:
    """[(name, start, end)]; the final chord's 'end' bar belongs to the section before it."""
    out = []
    for s in song.sections:
        if s.name == 'end' and out:
            out[-1] = (out[-1][0], out[-1][1], s.end)
        else:
            out.append((s.name, s.start, s.end))
    return out


def packet(song, key: str, tempo, timeline, report, render) -> str:
    sp = Speller(key)
    meter = int(song.beats_per_bar)
    tracks = {t['id']: [list(n[:4]) for n in t.get('notes', [])] for t in render['tracks']}
    rh, lh = tracks.get('piano', []), tracks.get('comp', [])
    secs = sections(song)
    # (the A sections numbered in playing order: round r7 read 'A4 with no A3' - the layouts' section names - as a
    # template label, which is not the music)
    a_names = [n for n, _, _ in secs if re.fullmatch(r'A\d+', n)]
    relabel = {n: f"A{k + 1}" for k, n in enumerate(a_names)}
    secs = [(relabel.get(n, n), a, b) for n, a, b in secs]
    total = secs[-1][2]
    n_bars = round(total / meter)
    spans = [(t, t + b, _chord(sym)) for t, b, sym in timeline]

    def bar_of(beat):
        return int(q(beat) // meter)

    def chord_at(beat):
        return next((c for a, z, c in spans if a - 1e-6 <= beat < z - 1e-6), None)

    def sec_of(beat):
        return next((x for x in secs if x[1] - 1e-6 <= beat < x[2] - 1e-6), secs[-1])

    rh_c, lh_c = clusters(rh), clusters(lh)
    by_rh, by_lh = {}, {}
    for c in rh_c:
        by_rh.setdefault(bar_of(c[0][0]), []).append(c)
    for c in lh_c:
        by_lh.setdefault(bar_of(c[0][0]), []).append(c)
    g = report.get('global') or {}
    dur = g.get('durationSec') or 0
    L = ['BLIND PACKET ' + '-' * 60,
         f"key      {key}",
         f"meter    {meter}/4",
         f"tempo    {tempo:g} BPM at the start (rubato; ritardandi and tempo changes as performed)",
         "feel     straight 8ths",
         f"length   {n_bars} bars, {int(dur // 60)}:{int(round(dur % 60)):02d} incl. the ring-out",
         f"layout   {' | '.join(f'{n} {round((e - s) / meter)}' for n, s, e in secs)} (bars)",
         '', 'CHORD CHART (one cell per bar; "%" = same chord; two symbols in a cell = split bar)']
    for name, s, e in secs:
        cells = []
        for b in range(round(s / meter), round(e / meter)):
            here = [sp.chord(c) for a, z, c in spans if b * meter - 1e-6 <= a < (b + 1) * meter - 1e-6]
            cells.append(' '.join(here) or '%')
        L.append(f"  {name:<8} (bars {round(s / meter) + 1}-{round(e / meter)}) | {' | '.join(cells)} |")
    L += ['', 'NOTATION', '  bar numbers count from 1 over the whole piece; positions are beats in the bar (1 = downbeat)',
          '  RH  position:top-note duration(beats) velocity(1-127) [+n = n more right-hand notes struck under it]',
          '  LH  every left-hand attack: position:note (a+b = struck together), then the velocity range in the bar']
    cur = None
    for b in range(n_bars):
        sec = sec_of(b * meter + 1e-3)
        if sec[0] != cur:
            cur = sec[0]
            L.append(f"\n[{cur}]")
        chords = [sp.chord(c) for a, z, c in spans if a < (b + 1) * meter - 1e-6 and z > b * meter + 1e-6]
        L.append(f"bar {b + 1:>3}  {' '.join(chords) if chords else '-'}")
        items = []
        for c in by_rh.get(b, []):
            top = max(c, key=lambda n: (n[2], n[1]))
            pos = q(c[0][0]) - b * meter + 1
            items.append(f"{num(pos)}:{sp.note(top[2], chord_at(top[0] + 0.06))} {num(max(1 / GRID, q(top[1])))} "
                         f"v{top[3]}" + (f" +{len(c) - 1}" if len(c) > 1 else ''))
        L.append('   RH  ' + ('  '.join(items) if items else 'rest'))
        hits = by_lh.get(b, [])
        if hits:
            words = []
            for c in hits:
                pos = q(c[0][0]) - b * meter + 1
                ch = chord_at(c[0][0] + 0.06)
                words.append(f"{num(pos)}:" + '+'.join(sp.note(n[2], ch) for n in sorted(c, key=lambda n: n[2])))
            vs = [n[3] for c in hits for n in c]
            L.append('   LH  ' + ' '.join(words) + f"  (v{min(vs)}-{max(vs)})")
        else:
            L.append('   LH  rest')
    L += ['', 'ANALYSIS (from the rendered audio; the same analyser for every packet)',
          f"  loudness range {g.get('loudnessRange')} LU",
          '  section loudness (LU relative to the whole piece):  ' + '  '.join(
              f"{relabel.get(x['name'], x['name'])} {x['lufs'] - g['lufsIntegrated']:+.1f}"
              for x in report.get('sections') or []
              if x['name'] != 'end')]
    for node in report.get('nodes') or []:
        d = node.get('dynamics')
        if node.get('id') not in ('piano', 'comp') or not isinstance(d, dict):
            continue
        hand = 'right hand' if node['id'] == 'piano' else 'left hand'
        v = d.get('velocity') or {}
        L.append(f"  note dynamics, {hand}: level spread (10-90 %) {d.get('spreadDb')} dB, within phrases "
                 f"{d.get('phraseSpreadDb')} dB, dynamics {d.get('dynamicsDb')} dB; velocities p10 {v.get('p10')} "
                 f"p90 {v.get('p90')} (min {v.get('min')}, max {v.get('max')})")
    L.append('  density per section (per bar):  section: RH attacks / RH notes / LH attacks / mean RH top velocity')
    for name, s, e in secs:
        bars = max(1e-9, (e - s) / meter)
        rc = [c for c in rh_c if s - 1e-6 <= q(c[0][0]) < e - 1e-6]
        lc = [c for c in lh_c if s - 1e-6 <= q(c[0][0]) < e - 1e-6]
        tv = [max(c, key=lambda n: n[2])[3] for c in rc]
        L.append(f"     {name:<8} {len(rc) / bars:5.1f} / {sum(map(len, rc)) / bars:5.1f} / {len(lc) / bars:5.1f} / "
                 f"{(sum(tv) / len(tv)) if tv else 0:5.1f}")
    top = max(rh, key=lambda n: (n[2], -n[0]))
    tb = bar_of(top[0])
    sec = sec_of(top[0])
    L.append(f"  highest note: {sp.note(top[2], chord_at(top[0] + 0.06))} at bar {tb + 1} beat "
             f"{num(q(top[0]) - tb * meter + 1)} ({sec[0]}; {q(top[0]) / total:.0%} into the piece), velocity {top[3]}")
    L.append(f"  lowest note: {sp.note(min(n[2] for n in rh + lh))}")
    return '\n'.join(L) + '\n'


def ids(n: int) -> list[str]:
    rng = random.Random(ID_SEED)
    out = []
    while len(out) < n:
        x = ''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(4))
        if x not in out:
            out.append(x)
    return out


def pieces() -> list:
    gen = GENERATED or sorted(p.name for p in NA.iterdir() if p.is_dir())[:4]
    return [('composed', ROOT / 'songs' / c) for c in COMPOSED] + [('generated', NA / x) for x in gen]


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    for f in OUT_DIR.glob('*.txt'):
        f.unlink()
    ps = pieces()
    order = list(range(len(ps)))
    random.Random(ID_SEED + ':order').shuffle(order)
    key = {}
    for pid, i in zip(ids(len(ps)), order):
        kind, folder = ps[i]
        song, k, tempo, tl, report = (load_composed if kind == 'composed' else load_generated)(folder)
        render = song.compile()
        check_notes(folder.name, render, report)
        (OUT_DIR / f"{pid}.txt").write_text(packet(song, k, tempo, tl, report, render), encoding='utf-8')
        key[pid] = {'source': kind, 'path': folder.relative_to(ROOT).as_posix()}
        print(f"wrote {OUT_DIR.name}/{pid}.txt")
    KEY_FILE.write_text(json.dumps(dict(sorted(key.items())), indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
