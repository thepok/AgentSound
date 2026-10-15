"""Blind "Turing test" packets for the PIPE ORGAN: composed pieces (the pro-organ-* references) vs endless organ pieces,
anonymized.

    python songs/_blind/make_packets_organ.py ROUND     # -> songs/_blind/packets_organ/<ID>.txt + KEY_organ.json

Every piece is rebuilt from its source (a song.py's build(); an endless tune folder: recomposed from its tune.json by
run.load_scored, the same call the score command makes), compiled (no audio render; the compiled notes must equal the
rendered report's) and written through ONE extraction path: header, registration and swell box per section, per-bar
notation of every registration (manual / pedal) as PLAYED, analysis from its report.json. Section names are replaced
by numbers; nothing that names the source (title, seed, mood, file names) reaches a packet. Judges read
packets_organ/ (copied as packets/) + JUDGE_ORGAN.md (copied as JUDGE.md) in an isolated folder; nobody reads
KEY_organ.json - score_round.py does.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
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

COMPOSED = ['pro-organ-prelude', 'pro-organ-toccata', 'pro-organ-meditation', 'pro-organ-postlude']
OUT_DIR = HERE / 'packets_organ'
KEY_FILE = HERE / 'KEY_organ.json'
CLUSTER = 0.06

ROLE_TEXT = {
    'principal': "Great: principal chorus 8' 4' 2'", 'full': "Great: full organ (mixture, trumpet)",
    'cornet': "Great: cornet / sesquialtera", 'trumpet': "Great: trumpet 8'",
    'soft': "Swell: soft flutes / strings", 'oboe': "Swell: oboe 8'", 'strings': "Swell: string 8'",
    'swell_full': "Swell: full swell with reed",
    'flute': "Positive: flutes 8' 4'", 'positiv': "Positive: chorus 8' 4' 2'", 'reed': "Positive: cromorne 8'",
    'pedal': "Pedal: 16' + 8'", 'pedal_soft': "Pedal: 16' alone", 'pedal_full': "Pedal: full with 16' reed",
    'pedal_cantus': "Pedal: 4' reed (cantus)",
}
ORDER = ['full', 'principal', 'cornet', 'trumpet', 'swell_full', 'oboe', 'strings', 'soft', 'positiv', 'flute', 'reed',
         'pedal_cantus', 'pedal_full', 'pedal', 'pedal_soft']


def load_composed(folder: Path):
    spec = importlib.util.spec_from_file_location('blindorg_' + folder.name.replace('-', '_'), folder / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(folder))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
            song = mod.build()
    finally:
        sys.path.remove(str(folder))
    report = json.loads((folder / 'out' / 'report.json').read_text(encoding='utf-8'))
    return song, report


def load_generated(folder: Path):
    song, tune, _ = load_scored(folder)
    info = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
    if tune.title != info['title']:
        raise SystemExit(f"{folder.name}: recomposed '{tune.title}', delivered '{info['title']}'")
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
    return song, report


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


def opening(v: float) -> float:
    """The swell box opening 0..1 from an expression value (orchestra.swell: 10^(-gain(1-o)/40))."""
    from agentsound.bandlib.orchestra import SWELL_BOX
    return max(0.0, min(1.0, 1.0 + 40.0 * math.log10(max(1e-6, v)) / SWELL_BOX['gain_db']))


def packet(song, report, render, labels) -> str:
    key = key_name(song)
    sp = Speller(key)
    meter = int(song.beats_per_bar)
    tracks = {t['id']: sorted(list(n[:3]) for n in t.get('notes', [])) for t in render['tracks']}
    tracks = {k: v for k, v in tracks.items() if v}
    order = [r for r in ORDER if r in tracks] + sorted(r for r in tracks if r not in ORDER)
    lanes = {t['id']: next((a['points'] for a in t.get('automation') or [] if a['target'] == 'instrument.expression'),
                           None) for t in render['tracks']}
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
         f"length   {n_bars} bars, {int(dur // 60)}:{int(round(dur % 60)):02d} incl. the church's ring-out",
         f"layout   {' | '.join(f'{labels[n]} {round((e - s) / meter)}' for n, s, e in secs)} (bars)",
         '', 'REGISTRATION per section (the stops that sound; the swell box opening where it moves)']
    for name, s, e in secs:
        on = [r for r in order if any(s - 1e-6 <= n[0] < e - 1e-6 for n in tracks[r])]
        sw = []
        for r in on:
            pts = lanes.get(r)
            if pts:
                vals = [opening(p[1]) for p in pts if s - 1e-6 <= p[0] <= e + 1e-6]
                if vals and max(vals) - min(vals) > 0.05:
                    sw.append(f"{r} box {min(vals):.0%}-{max(vals):.0%}")
        L.append(f"  {labels[name]:<4} (bars {round(s / meter) + 1}-{round(e / meter)}): "
                 + '; '.join(f"{r} = {ROLE_TEXT.get(r, r)}" for r in on) + (f"  [{', '.join(sw)}]" if sw else ''))
    L += ['', 'NOTATION (as played: every key down per registration track)',
          '  bar numbers count from 1 over the whole piece; positions are beats in the bar (1 = downbeat), rounded to',
          '  1/12 beat (small offsets = the player\'s timing); each attack is position:note(+note...)/duration in beats',
          '  (notes struck together joined with +; the duration of the top note - its articulation)']
    by = {r: {} for r in order}
    for r in order:
        cl = []
        for n in tracks[r]:
            if cl and n[0] - cl[-1][0][0] < CLUSTER:
                cl[-1].append(n)
            else:
                cl.append([n])
        for c in cl:
            by[r].setdefault(int(q(c[0][0]) // meter), []).append(c)
    cur = None
    sec_of = {}
    for name, s, e in secs:
        for b in range(int(round(s / meter)), int(math.ceil(e / meter - 1e-6))):
            sec_of.setdefault(b, name)
    for b in range(n_bars):
        if sec_of.get(b) != cur:
            cur = sec_of.get(b)
            L.append(f"\n[{labels.get(cur, cur)}]")
        L.append(f"bar {b + 1:>3}")
        any_ = False
        for r in order:
            cs = by[r].get(b)
            if not cs:
                continue
            any_ = True
            words = []
            for c in cs:
                top = max(c, key=lambda n: n[2])
                pos = q(c[0][0]) - b * meter + 1
                words.append(f"{num(pos)}:" + '+'.join(sp.note(n[2]) for n in sorted(c, key=lambda n: n[2]))
                             + f"/{num(max(1 / 12, q(top[1])))}")
            L.append(f"   {r:<12} " + ' '.join(words))
        if not any_:
            L.append('   (rest)')
    L += ['', 'ANALYSIS (from the rendered audio; the same analyser for every packet)',
          f"  loudness range {g.get('loudnessRange')} LU",
          '  section loudness (LU relative to the whole piece):  ' + '  '.join(
              f"{labels.get(x['name'], x['name'])} {x['lufs'] - g['lufsIntegrated']:+.1f}"
              for x in report.get('sections') or [] if x['name'] != 'end' and x.get('lufs') is not None)]
    L.append('  attacks per bar per section:  ' + '  '.join(
        f"{labels[n]} " + '/'.join(f"{r}:{sum(len(by[r].get(b, [])) for b in range(round(s / meter), round(e / meter))) / max(1, round((e - s) / meter)):.1f}"
                                   for r in order if any(s - 1e-6 <= x[0] < e - 1e-6 for x in tracks[r]))
        for n, s, e in secs))
    man = [n for r in order if not r.startswith('pedal') for n in tracks[r]]
    ped = [n for r in order if r.startswith('pedal') for n in tracks[r]]
    if man:
        top = max(man, key=lambda n: (n[2], -n[0]))
        L.append(f"  highest manual note: {sp.note(top[2])} at bar {int(q(top[0]) // meter) + 1} "
                 f"({q(top[0]) / total:.0%} into the piece); lowest manual note {sp.note(min(n[2] for n in man))}")
    if ped:
        L.append(f"  pedal range: {sp.note(min(n[2] for n in ped))} - {sp.note(max(n[2] for n in ped))} (written; "
                 f"16' stops sound an octave lower)")
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
    gen_dir = ROOT / 'songs' / '_endless_organ' / 'out' / rnd
    seed = f"blind-organ-{rnd}"
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
        song, report = (load_composed if kind == 'composed' else load_generated)(folder)
        render = song.compile()
        check_notes(folder.name, render, report)
        labels = {name: f"S{k + 1}" for k, (name, _, _) in enumerate(sections(song))}
        (OUT_DIR / f"{pid}.txt").write_text(packet(song, report, render, labels), encoding='utf-8')
        key[pid] = {'source': kind, 'path': folder.relative_to(ROOT).as_posix()}
        print(f"wrote {OUT_DIR.name}/{pid}.txt")
    KEY_FILE.write_text(json.dumps(dict(sorted(key.items())), indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
