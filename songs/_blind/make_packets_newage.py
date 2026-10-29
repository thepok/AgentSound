"""Blind "Turing test" packets for NEW-AGE solo piano: composed pieces (letters-to-the-morning + the pro-newage-*
references) vs endless new-age tunes, anonymized.

    python songs/_blind/make_packets_newage.py ROUND   # -> songs/_blind/packets_newage/<ID>.txt + KEY_newage.json

Rounds r*: four composed + four generated; g1 / g2: all generated (the judges count); g3 on: the QUALITY rounds - every
tune folder of na_<round> plus the hidden anchors (COMPOSED), the judges rate each piece (JUDGE_NEWAGE.md).

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
import math
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
_GN = int(ROUND[1:]) if ROUND.startswith('g') and ROUND[1:].isdigit() else 0
ALL_GENERATED = 1 <= _GN <= 2           # (rounds g1, g2: every packet an endless tune - the judges are not told;
if ALL_GENERATED:                       #  they estimate how many are generated, the target ~3 of 10)
    COMPOSED = []
QUALITY = _GN >= 3                      # (rounds g3 ...: the judges RATE every piece - JUDGE_NEWAGE.md; 8-9 fresh
if QUALITY:                             #  generated pieces + hidden hand-composed anchors, the split not disclosed)
    COMPOSED = ['pro-newage-homecoming', 'pro-newage-longing'] if _GN == 3 else \
        ['pro-newage-embers', 'pro-newage-tide'] + (['pro-newage-longing'] if _GN >= 7 else [])
    # (g4 on: references the judges have not seen - the C minor passacaglia and the D Dorian 6/8 arch; g7 on: a third
    # one, the B minor 3/4 longing - g3's best-rated reference, 7.2 - so one round's yardstick drift averages out:
    # embers and tide were rated 7.10 in g4 / g5, 6.40 in g6)
GENERATED = sys.argv[2:] or (['001-gardens-to-autumn', '003-hidden-mirrors-of-spring', '005-before-the-sea',
                              '007-before-the-hills'] if ROUND == 'r5' else [])
ID_SEED = f"blind-new-age-{ROUND}"
OUT_DIR = HERE / 'packets_newage'
KEY_FILE = HERE / 'KEY_newage.json'
GRID = 12
UNDER_HELD = 0.25        # (an inner voice: under a higher note held this many beats past it - tells_newage.UNDER_HELD)
CLUSTER = 0.1
LEAN = 0.1


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

    def bar_of(beat):                                  # (round g9: a downbeat struck up to LEAN early - the melody
        return int(q(beat + LEAN) // meter)            # leaning ahead, a rolled grip - is its bar's downbeat: JKGC
        #                                                41 '4.92:F5 2' then bar 42 'rest' read as a hole)

    def pos_of(beat, b):
        return max(1.0, q(beat) - b * meter + 1)

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
          '  RH  position:top-note duration(beats) velocity(1-127) [+n = n more right-hand notes struck under it];',
          '      position:(a b c) note ... = an ornament (turn, mordent): quick notes a b c, then the note they',
          '      decorate; position:(under) note ... = struck under a higher right-hand note still held (an inner',
          '      voice, not the melody); a downbeat struck a hair early is printed on its downbeat;',
          '      (tied: X held from the bar before) = no new note, the note X sounds through the bar; rest = silence',
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
            pos = pos_of(c[0][0], b)
            main = max(c, key=lambda n: (n[1], n[0]))
            grace = sorted((n for n in c if n[1] <= 0.12 and n[0] < main[0] - 0.01), key=lambda n: n[0])
            one = False
            if len(grace) == 1:                        # (one quick note: the top of the others is the note it leads
                main = max((n for n in c if n not in grace), key=lambda n: (n[2], n[1]))     # into, a step away)
                one = main[1] > 0.25 and abs(grace[0][2] - main[2]) <= 2
            if (len(grace) >= 2 or one) and max(n[0] for n in c) - min(n[0] for n in c) > 0.05:
                # (an ornament - a turn, a mordent, a slide: its quick notes in time order, then the note they
                # decorate; round g1: four judges read a turn printed as a 4-note chord of 0.08 beat as a 'chord grab';
                # round g14: one quick note leaning into a held downbeat note - a turn's last note, a crushed grace -
                # printed as the bar's top note, 'A4 0.08 +1', hid the G4 held three beats under it: MYUS 8 / GALR 14
                # read as "a 0.08-beat stab, then an empty bar" by all seven g13 judges)
                rest = [n for n in c if n not in grace and n is not main and abs(n[0] - main[0]) < CLUSTER]
                ch_ = chord_at(main[0] + 0.06)
                items.append(f"{num(pos)}:({' '.join(sp.note(n[2], ch_) for n in grace)}) {sp.note(main[2], ch_)} "
                             f"{num(max(1 / GRID, q(main[1])))} v{main[3]}" + (f" +{len(rest)}" if rest else ''))
                continue
            top = max(c, key=lambda n: (n[2], n[1]))
            # (round g9: a note struck under a melody note still held - the woven figure, an inner voice - is an
            # inner voice, not the top line: PKCG 34 'Gb6 +2  Db5  Bb4  Ab6' read as two-octave jumps in a beat;
            # round g12: held UNDER_HELD beats past its onset - a finger legato's overlap, up to ~100 ms, is the
            # melody moving on, not an inner voice)
            under = any(n[0] < top[0] - 0.05 and n[0] + n[1] > top[0] + UNDER_HELD and n[2] >= top[2] + 3 for n in rh)
            items.append(f"{num(pos)}:{'(under) ' if under else ''}{sp.note(top[2], chord_at(top[0] + 0.06))} "
                         f"{num(max(1 / GRID, q(top[1])))} v{top[3]}" + (f" +{len(c) - 1}" if len(c) > 1 else ''))
        if not items:                                  # (round g8: a note tied into the bar (half of it+) is no rest - the
            held = [n for n in rh if n[0] < b * meter - LEAN and n[0] + n[1] >= (b + 0.5) * meter]   # g7
            if held:                                   # statistician counted anticipated landings as RH holes)
                top = max(held, key=lambda n: n[2])
                items = [f"(tied: {sp.note(top[2], chord_at(b * meter + 0.06))} held from the bar before)"]
        L.append('   RH  ' + ('  '.join(items) if items else 'rest'))
        hits = by_lh.get(b, [])
        if hits:
            words = []
            for c in hits:
                pos = pos_of(c[0][0], b)
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
    try:                                                # (the performed tempo: rubato, pushes and ritardandi)
        tm = song.tempo_map()
        L.append('  tempo per section (mean BPM as performed):  ' + '  '.join(
            f"{n} {60.0 * (e - s) / max(1e-9, tm.seconds_at(e) - tm.seconds_at(s)):.0f}" for n, s, e in secs))
    except Exception:
        pass
    for node in report.get('nodes') or []:
        d = node.get('dynamics')
        if node.get('id') not in ('piano', 'comp') or not isinstance(d, dict):
            continue
        hand = 'right hand' if node['id'] == 'piano' else 'left hand'
        v = d.get('velocity') or {}
        L.append(f"  note dynamics, {hand}: level spread (10-90 %) {d.get('spreadDb')} dB, within phrases "
                 f"{d.get('phraseSpreadDb')} dB, dynamics {d.get('dynamicsDb')} dB; velocities p10 {v.get('p10')} "
                 f"p90 {v.get('p90')} (min {v.get('min')}, max {v.get('max')})")
    # the hands per section (composer.hands_tells' measures: round g3 on): the right hand's level over the left's in
    # dB of the notes' energy ((velocity / 127) ** 2.5, summed - negative: the left hand leads) and the share of the
    # right hand's notes at or above C6
    def energy(ns):
        return sum((n[3] / 127.0) ** 2.5 for n in ns)
    cells = []
    for name, s_, e_ in secs:
        r_ = [n for n in rh if s_ - 1e-6 <= n[0] < e_ - 1e-6]
        l_ = [n for n in lh if s_ - 1e-6 <= n[0] < e_ - 1e-6]
        bal = f"{10 * math.log10(energy(r_) / energy(l_)):+.1f} dB" if r_ and l_ else '-'
        hi = f"{sum(n[2] >= 84 for n in r_) / len(r_):.0%}" if r_ else '-'
        cells.append(f"{name} {bal} / {hi}")
    L.append('  hands per section (RH level over LH in dB of note energy / share of RH notes at or above C6):  '
             + '  '.join(cells))
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
    gen = GENERATED or sorted(p.name for p in NA.iterdir() if p.is_dir())[:None if ROUND.startswith('g') else 4]
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
        if kind == 'generated':                        # (the tune's form and drawn texture, for the analysis)
            info = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
            key[pid]['title'] = info.get('title')
            sg = getattr(song, 'endless_signature', None) or {}     # (the signature moves' bars: score_round's
            key[pid]['moves'] = [[d['move'], str(d['role']), *d['bars']] for d in sg.get('statements') or ()]   # hits
        print(f"wrote {OUT_DIR.name}/{pid}.txt")
    KEY_FILE.write_text(json.dumps(dict(sorted(key.items())), indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
