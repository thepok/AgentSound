"""Blind "Turing test" packets for the ORCHESTRA: composed pieces (the pro-orch-* references) vs endless
orchestra-film pieces, anonymized.

    python songs/_blind/make_packets_orch.py ROUND     # -> songs/_blind/packets_orch/<ID>.txt + KEY_orch.json

Every piece is rebuilt from its source (run.load_scored: a song.py's build(), an endless tune folder recomposed from
its tune.json - the call the score command makes), compiled (no audio render; the compiled notes must equal the
rendered report's) and written through ONE extraction path: header, the orchestration per section (the roles that
sound and their dynamics), per-bar notation of every role AS PLAYED ('%' = the role's previous bar again), analysis
from its report.json. Section names are replaced by numbers; nothing that names the source (title, seed, mood, file
names) reaches a packet. Judges read packets_orch/ (copied as packets/) + JUDGE_ORCH.md (copied as JUDGE.md) in an
isolated folder; nobody reads KEY_orch.json - score_round.py does.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from make_packets import Speller, check_notes, num, q  # noqa: E402
from agentsound.endless.run import load_scored  # noqa: E402

COMPOSED = ['pro-orch-hopeful', 'pro-orch-longing', 'pro-orch-epic', 'pro-orch-night']
OUT_DIR = HERE / 'packets_orch'
KEY_FILE = HERE / 'KEY_orch.json'
CLUSTER = 0.06
ORDER = ['flutes', 'oboes', 'clarinets', 'bassoons', 'horns', 'trumpets', 'trombones', 'tuba', 'timpani',
         'percussion', 'harp', 'choir', 'violins1', 'violins2', 'violas', 'cellos', 'basses']
MARKS = (('pp', 0.16), ('p', 0.3), ('mp', 0.45), ('mf', 0.6), ('f', 0.75), ('ff', 0.9))
KEYSWITCH = 21                      # (notes under A0 are articulation key switches, not music)
EARLY = 0.2      # an attack this close before a barline belongs to the next bar (position 0.92 = just before 1:
                 # the players' speaking lead)


def _perc():
    from agentsound.bandlib.orchestra import PERCUSSION_KEYS
    return {v: k for k, v in PERCUSSION_KEYS.items()}


PERC = _perc()


def load(folder: Path, generated: bool):
    song, tune, _ = load_scored(folder)
    rep = folder / ('report.json' if generated else 'out/report.json')
    if generated:
        info = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
        if tune.title != info['title']:
            raise SystemExit(f"{folder.name}: recomposed '{tune.title}', delivered '{info['title']}'")
    return song, json.loads(rep.read_text(encoding='utf-8'))


def key_name(song) -> str:
    k = song.key
    return k.name if hasattr(k, 'name') else str(k)


def sections(song) -> list:
    out = []
    for s in song.sections:
        if s.name == 'end' and out:
            out[-1] = (out[-1][0], out[-1][1], s.end)
        else:
            out.append((s.name, s.start, s.end))
    return out


def mark(v: float) -> str:
    return min(MARKS, key=lambda m: abs(m[1] - v))[0]


def packet(song, report, render, labels) -> str:
    key = key_name(song)
    sp = Speller(key)
    meter = int(song.beats_per_bar)
    tracks = {t['id']: sorted(list(n[:4]) for n in t.get('notes', []) if n[2] >= KEYSWITCH) for t in render['tracks']}
    tracks = {k: v for k, v in tracks.items() if v}
    order = [r for r in ORDER if r in tracks] + sorted(r for r in tracks if r not in ORDER)
    lanes = {t['id']: next((a['points'] for a in t.get('automation') or []
                            if a['target'] in ('instrument.dynamics', 'instrument.expression')), None)
             for t in render['tracks']}
    secs = sections(song)
    total = secs[-1][2]
    n_bars = int(math.ceil(total / meter - 1e-6))
    g = report.get('global') or {}
    dur = g.get('durationSec') or 0
    tm = song.tempo_map()
    L = ['BLIND PACKET ' + '-' * 60,
         f"key      {key}",
         f"meter    {meter}/4",
         f"tempo    {tm.bpm_at(0):.0f} BPM at the start (ritardandi, fermatas and tempo changes as performed)",
         f"length   {n_bars} bars, {int(dur // 60)}:{int(round(dur % 60)):02d} incl. the hall's ring-out",
         f"layout   {' | '.join(f'{labels[n]} {round((e - s) / meter)}' for n, s, e in secs)} (bars)",
         f"roles    {', '.join(order)}",
         '', 'ORCHESTRATION per section (the roles that sound; their dynamics: the lane / velocity range as marks)']
    for name, s, e in secs:
        words = []
        for r in order:
            ns = [n for n in tracks[r] if s - 1e-6 <= n[0] < e - 1e-6]
            if not ns:
                continue
            pts = lanes.get(r)
            vals = [p[1] for p in pts if s - 1e-6 <= p[0] <= e + 1e-6] if pts else []
            if not vals:
                vals = [n[3] / 127.0 for n in ns]
            lo, hi = mark(min(vals)), mark(max(vals))
            words.append(f"{r} {lo if lo == hi else lo + '-' + hi}")
        L.append(f"  {labels[name]:<4} (bars {round(s / meter) + 1}-{round(e / meter)}): " + ', '.join(words))
    L += ['', 'NOTATION (as played: every note per role)',
          '  bar numbers count from 1 over the whole piece; positions are beats in the bar (1 = downbeat), rounded to',
          '  1/12 beat (small offsets = the players\' timing; 0.92 = just before the downbeat); each attack is',
          '  position:note(+note...)/duration in',
          '  beats (notes struck together joined with +; the duration of the top note); % = the role plays its',
          '  previous bar again (the same notes at the same positions)']
    by = {r: {} for r in order}
    for r in order:
        cl = []
        for n in tracks[r]:
            if cl and n[0] - cl[-1][0][0] < CLUSTER:
                cl[-1].append(n)
            else:
                cl.append([n])
        for c in cl:
            by[r].setdefault(int((q(c[0][0]) + EARLY) // meter), []).append(c)
    sec_of = {}
    for name, s, e in secs:
        for b in range(int(round(s / meter)), int(math.ceil(e / meter - 1e-6))):
            sec_of.setdefault(b, name)
    cur, prev = None, {}
    for b in range(n_bars):
        if sec_of.get(b) != cur:
            cur = sec_of.get(b)
            L.append(f"\n[{labels.get(cur, cur)}]")
        L.append(f"bar {b + 1:>3}")
        any_ = False
        for r in order:
            cs = by[r].get(b)
            if not cs:
                prev.pop(r, None)
                continue
            any_ = True
            words = []
            for c in cs:
                top = max(c, key=lambda n: n[2])
                pos = q(c[0][0]) - b * meter + 1
                name = (lambda m: PERC.get(m, sp.note(m))) if r == 'percussion' else sp.note
                words.append(f"{num(pos)}:" + '+'.join(name(n[2]) for n in sorted(c, key=lambda n: n[2]))
                             + f"/{num(max(1 / 12, q(top[1])))}")
            text = ' '.join(words)
            L.append(f"   {r:<11} " + ('%' if prev.get(r) == text else text))
            prev[r] = text
        if not any_:              # (r2: '(rest)' for a bar of held notes - the judges read silences that were not)
            held = [r for r in order if any(n[0] < (b + 1) * meter - EARLY and n[0] + n[1] > b * meter + 0.5
                                            for n in tracks[r])]
            L.append(f"   (no attack - held: {', '.join(held)})" if held else '   (rest)')
    L += ['', 'ANALYSIS (from the rendered audio; the same analyser for every packet)',
          f"  loudness range {g.get('loudnessRange')} LU",
          '  section loudness (LU relative to the whole piece):  ' + '  '.join(
              f"{labels.get(x['name'], x['name'])} {x['lufs'] - g['lufsIntegrated']:+.1f}"
              for x in report.get('sections') or [] if x['name'] != 'end' and x.get('lufs') is not None)]
    L.append('  roles sounding per section:  ' + '  '.join(
        f"{labels[n]} {sum(1 for r in order if any(s - 1e-6 <= x[0] < e - 1e-6 for x in tracks[r]))}"
        for n, s, e in secs))
    high = [n for r in order if r not in ('percussion', 'timpani') for n in tracks[r]]
    if high:
        top = max(high, key=lambda n: (n[2], -n[0]))
        L.append(f"  highest note: {sp.note(top[2])} at bar {int(q(top[0]) // meter) + 1} "
                 f"({q(top[0]) / total:.0%} into the piece)")
    return '\n'.join(L) + '\n'


def ids(n: int, seed: str) -> list[str]:
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        x = ''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(4))
        if x not in out:
            out.append(x)
    return out


def main() -> int:
    rnd = sys.argv[1]
    gen_dir = ROOT / 'songs' / '_endless_orchestra' / 'out' / rnd
    seed = f"blind-orch-{rnd}"
    OUT_DIR.mkdir(exist_ok=True)
    for f in OUT_DIR.glob('*.txt'):
        f.unlink()
    ps = [('composed', ROOT / 'songs' / c) for c in COMPOSED] + \
        [('generated', p) for p in sorted(gen_dir.iterdir()) if p.is_dir() and (p / 'tune.json').is_file()]
    order = list(range(len(ps)))
    random.Random(seed + ':order').shuffle(order)
    key = {}
    for pid, i in zip(ids(len(ps), seed), order):
        kind, folder = ps[i]
        song, report = load(folder, kind == 'generated')
        render = song.compile()
        check_notes(folder.name, render, report)
        labels = {name: f"S{k + 1}" for k, (name, _, _) in enumerate(sections(song))}
        text = packet(song, report, render, labels)
        (OUT_DIR / f"{pid}.txt").write_text(text, encoding='utf-8')
        key[pid] = {'source': kind, 'path': folder.relative_to(ROOT).as_posix()}
        print(f"wrote {OUT_DIR.name}/{pid}.txt ({len(text) // 1000} kB)")
    KEY_FILE.write_text(json.dumps(dict(sorted(key.items())), indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
