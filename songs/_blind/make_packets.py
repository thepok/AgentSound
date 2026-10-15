"""Blind "Turing test" packets: composed (pro) jazz-piano pieces vs endless-generator tunes, anonymized.

    python songs/_blind/make_packets.py          # -> songs/_blind/packets/<ID>.txt + songs/_blind/KEY.json

Every piece is rebuilt from its source (a song.py, or the endless composer from the seed / mood / swing / set plan in
its tune.json), compiled to the render JSON (no audio render) and written through ONE extraction path: header, chord
chart, per-bar notation (right-hand top line + left-hand voicings), analysis from its report.json. Nothing that names
the source (title, seed, mood, file names, album, timings) reaches a packet. Judges read packets/ + JUDGE.md only.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import endless  # noqa: E402
from agentsound.theory import Chord, spell_above, spell_note  # noqa: E402

HERE = Path(__file__).resolve().parent
EJ = ROOT / 'songs' / '_endless_jazz_piano' / 'out'
PIECES = [  # (source kind, path): a song folder with song.py + out/, or an endless tune folder (tune.json, report.json)
    ('composed', ROOT / 'songs' / 'pro2-piano-waltz'),
    ('composed', ROOT / 'songs' / 'pro2-piano-blues'),
    ('composed', ROOT / 'songs' / 'pro2-piano-latenight'),
    ('composed', ROOT / 'songs' / 'pro2-piano-bossa'),
    ('generated', EJ / 'r9' / '001-the-paper-window'),
    ('generated', EJ / 'r9' / '002-the-other-promise-blues'),
    ('generated', EJ / 'r9' / '003-leroy-at-after-hours'),
    ('generated', EJ / 'r9' / '004-two-a-m-window'),
]
ID_SEED = 'blind-jazz-piano-v9'
SECTION_NAMES = {'intro': 'intro', 'head': 'head', 'solo': 'solo', 'out': 'head-out', 'tag': 'tag', 'end': 'ending'}
FEELS = {'straight': 'medium 4/4', 'waltz': 'jazz waltz', 'bossa': 'bossa nova', 'ballad': 'ballad',
         'shuffle': 'medium blues, bar-piano groove'}   # (the endless 'shuffle' feel is a straight-8th groove)
GRID = 12          # positions / durations quantized to 1/12 beat (16ths, 8th- and quarter-triplets)
CLUSTER = 0.1      # onsets closer than this (beats) are one attack (a chord, a roll)


# ------------------------------------------------------------------------------------------------ the sources

def load_composed(folder: Path):
    """(Song, Tune, report) of a song.py (its build() prints are swallowed)."""
    spec = importlib.util.spec_from_file_location('blind_' + folder.name.replace('-', '_'), folder / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(folder))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
            song = mod.build()
    finally:
        sys.path.remove(str(folder))
    report = json.loads((folder / 'out' / 'report.json').read_text(encoding='utf-8'))
    return song, mod.TUNE, report


def load_generated(folder: Path):
    """(Song, Tune, report) of an endless tune folder: recomposed from its tune.json (seed, mood, swing, set plan) -
    the same call the endless runner made - and checked against the delivered tune."""
    info = json.loads((folder / 'tune.json').read_text(encoding='utf-8'))
    g = endless.genre(info['genre'])
    plan = info.get('plan')
    tune = endless.compose(g, info['seed'], mood=None if plan else info['mood'], swing=info['swing'], plan=plan)
    got = tune.to_dict()
    for k in ('title', 'key', 'tempo', 'meter', 'feel', 'form', 'changes', 'melody'):
        if json.loads(json.dumps(got[k])) != info[k]:
            raise SystemExit(f"{folder.name}: the recomposed tune differs from the delivered one in {k!r}")
    return endless.song(tune), tune, json.loads((folder / 'report.json').read_text(encoding='utf-8'))


def check_notes(name: str, render: dict, report: dict) -> None:
    """The compiled notes are the rendered ones: per-track note counts equal the report's."""
    for n in report.get('nodes') or []:
        sil = n.get('silentNotes')
        if isinstance(sil, dict) and 'notes' in sil:
            tr = next((t for t in render['tracks'] if t['id'] == n['id']), None)
            if tr is None or len(tr.get('notes', [])) != sil['notes']:
                raise SystemExit(f"{name}: track {n['id']} compiles {len(tr.get('notes', [])) if tr else 0} notes, "
                                 f"the report rendered {sil['notes']}")


# ------------------------------------------------------------------------------------------------ spelling

class Speller:
    """One spelling for both sources, by degree (theory.spell_above): a chord root by its degree in the key (the bVI
    of D is Bb, not A#), a note by its degree over the chord it sounds in (the 3rd of D7 is F#, not Gb; the b9 Eb), a
    note without a chord by its degree in the key (blind round 6: flat-side chords spelled with sharps in sharp
    keys)."""

    def __init__(self, key: str):
        self.tonic = key.split()[0]
        self.tpc = Chord.parse(self.tonic).root % 12

    def root(self, c) -> str:
        return spell_above(self.tonic, (c.root - self.tpc) % 12)

    def note(self, midi: int, c=None) -> str:
        if c is None:
            return spell_note(midi, self.tonic)
        ivs = {i % 12 for i in c.intervals}
        x = (midi - c.root) % 12
        # a chord's own tones by their function: the b5 of a m7b5 / dim, the #5 of an augmented chord (a #9 stays
        # the b10 a jazz chart writes: F over D7)
        steps = 4 if x == 6 and 7 not in ivs and 6 in ivs else 4 if x == 8 and 7 not in ivs and 8 in ivs and 4 in ivs \
            else None
        return spell_note(midi, self.root(c), steps)

    def chord(self, c) -> str:
        if c is None:
            return 'NC'
        r = self.root(c)
        return r + c.quality + (f"/{spell_above(r, (c.bass - c.root) % 12)}" if c.bass is not None else '')


def num(x: float) -> str:
    return f"{x:.2f}".rstrip('0').rstrip('.')


def q(x: float) -> float:
    return round(x * GRID) / GRID


# ------------------------------------------------------------------------------------------------ the packet

def labels(song) -> list[tuple]:
    """[(section, common label, start, end)] per part: head A1 A2 B A3 by letter, solo 'chorus k X', head-out keeps
    the head's labels; a section without parts is one row."""
    rows = []
    head = next((s for s in song.sections if s.name == 'head'), None)
    hl = []
    if head is not None:
        seen = {}
        for p in head.parts:
            L = p.name[0]
            seen[L] = seen.get(L, 0) + 1
            hl.append(L + str(seen[L]))
        counts = {}
        for x in hl:
            counts[x[0]] = counts.get(x[0], 0) + 1
        hl = [x if counts[x[0]] > 1 else x[0] for x in hl]
    blues = len(set(x[0] for x in hl)) == 1
    for s in song.sections:
        sec = SECTION_NAMES.get(s.name, s.name)
        if not s.parts or s.name not in ('head', 'solo', 'out'):
            rows.append((sec, sec, s.start, s.end, s.prog))
            continue
        for i, p in enumerate(s.parts):
            if s.name == 'head':
                lab = f"head {hl[i]}"
            elif s.name == 'solo':
                lab = f"solo chorus {i + 1}" if blues else f"solo chorus {i // len(hl) + 1} {hl[i % len(hl)]}"
            else:   # the head-out: the head part with the same changes (the out restates head parts)
                j = next((k for k, hp in enumerate(head.parts) if hp.prog.items == p.prog.items
                          and hp.name[0] == p.name[0]), None)
                lab = f"head-out {hl[j] if j is not None else p.name[0]}"
                if blues:
                    lab = f"head-out chorus {i + 1}"
            rows.append((sec, lab, p.start, p.end, p.prog))
    return rows


def clusters(notes: list) -> list[list]:
    out = []
    for n in sorted(notes, key=lambda n: (n[0], -n[2])):
        if out and (n[0] - out[-1][-1][0] < CLUSTER or q(n[0]) == q(out[-1][0][0])):
            out[-1].append(n)
        else:
            out.append([n])
    return out


def chord_spans(prog, start: float) -> list[tuple]:
    return [(start + t, start + t + d, c) for t, d, c in prog]


def packet(song, tune, report, render) -> str:
    sp = Speller(tune.key)
    meter = int(tune.meter)
    tracks = {t['id']: [list(n[:4]) for n in t.get('notes', [])] for t in render['tracks']}
    rh, lh = tracks.get('piano', []), tracks.get('comp', [])
    rows = labels(song)
    total_beats = song.sections[-1].end
    n_bars = round(total_beats / meter)
    spans = [x for _, _, s, _, prog in rows if prog is not None for x in chord_spans(prog, s)]

    def bar_of(beat):
        return int(q(beat) // meter)

    def chord_at(beat):
        return next((c for a, z, c in spans if a - 1e-6 <= beat < z - 1e-6), None)

    def row_of(beat):
        return next((r for r in rows if r[2] - 1e-6 <= beat < r[3] - 1e-6), rows[-1])

    rh_c, lh_c = clusters(rh), clusters(lh)
    by_bar_rh, by_bar_lh = {}, {}
    for c in rh_c:
        by_bar_rh.setdefault(bar_of(c[0][0]), []).append(c)
    for c in lh_c:
        by_bar_lh.setdefault(bar_of(c[0][0]), []).append(c)

    g = report.get('global') or {}
    feel = FEELS.get(tune.feel, tune.feel) + (f", swung 8ths (ratio {tune.swing:.2f})" if tune.swing else ', straight 8ths')
    dur = g.get('durationSec') or 0
    L = ['BLIND PACKET ' + '-' * 60,
         f"key      {tune.key}",
         f"meter    {meter}/4",
         f"tempo    {tune.tempo} BPM (ritardando into the ending; rubato intro)",
         f"feel     {feel}",
         f"form     {tune.form}, head parts: {' '.join(r[1][5:] for r in rows if r[1].startswith('head '))}",
         f"length   {n_bars} bars, {int(dur // 60)}:{int(round(dur % 60)):02d} incl. the ring-out",
         f"layout   {' | '.join(f'{sec} {round((e - s) / meter)}' for sec, s, e in _sections(rows))} (bars)",
         '', 'CHORD CHART (one cell per bar; "%" = same chord; two symbols in a cell = split bar)']
    for sec, lab, s, e, prog in rows:
        if prog is None:
            continue
        cells = []
        for b in range(round(s / meter), round(e / meter)):
            here = [sp.chord(c) for a, z, c in spans if b * meter - 1e-6 <= a < (b + 1) * meter - 1e-6]
            cells.append(' '.join(here) or '%')
        line = ' | '.join(cells)
        L.append(f"  {lab:<22} (bars {round(s / meter) + 1}-{round(e / meter)}) | {line} |")

    L += ['', 'NOTATION', '  bar numbers count from 1 over the whole piece; positions are beats in the bar (1 = downbeat)',
          '  RH  position:top-note duration(beats) velocity(1-127) [+n = n more right-hand notes struck under it]',
          '  LH  chord: voicing low->high, velocity of the first attack, (xN = N attacks while that chord lasts)']
    cur = None
    for b in range(n_bars):
        r = row_of(b * meter + 1e-3)
        if r[1] != cur:
            cur = r[1]
            L.append(f"\n[{cur}]")
        chords = [sp.chord(c) for a, z, c in spans if a < (b + 1) * meter - 1e-6 and z > b * meter + 1e-6]
        L.append(f"bar {b + 1:>3}  {' '.join(chords) if chords else '-'}")
        items = []
        for c in by_bar_rh.get(b, []):
            top = max(c, key=lambda n: (n[2], n[1]))     # a crushed grace + its principal: the held note
            pos = q(c[0][0]) - b * meter + 1
            items.append(f"{num(pos)}:{sp.note(top[2], chord_at(top[0] + 0.06))} {num(max(1 / GRID, q(top[1])))} "
                         f"v{top[3]}"
                         + (f" +{len(c) - 1}" if len(c) > 1 else ''))
        L.append('   RH  ' + ('  '.join(items) if items else 'rest'))
        lhs = []
        for a, z, c in spans:
            if not (a < (b + 1) * meter - 1e-6 and z > b * meter + 1e-6):
                continue
            lo, hi = max(a, b * meter), min(z, (b + 1) * meter)
            hits = [x for x in by_bar_lh.get(b, []) if lo - 1e-6 <= q(x[0][0]) < hi - 1e-6]
            if hits:
                first = sorted(hits[0], key=lambda n: n[2])
                lhs.append(f"{sp.chord(c)}: {' '.join(sp.note(n[2], c) for n in first)} v{first[0][3]}"
                           + (f" (x{len(hits)})" if len(hits) > 1 else ''))
        L.append('   LH  ' + (' | '.join(lhs) if lhs else 'rest'))

    # ---- analysis
    L += ['', 'ANALYSIS (from the rendered audio; the same analyser for every packet)',
          f"  loudness range {g.get('loudnessRange')} LU",
          # relative to the piece's integrated loudness: the master gain (a mixing choice, not the music) left out
          '  section loudness (LU relative to the whole piece):  ' + '  '.join(
              f"{SECTION_NAMES.get(s['name'], s['name'])} {s['lufs'] - g['lufsIntegrated']:+.1f}"
              for s in report.get('sections') or [])]
    for node in report.get('nodes') or []:
        d = node.get('dynamics')
        if node.get('id') not in ('piano', 'comp') or not isinstance(d, dict):
            continue
        hand = 'right hand' if node['id'] == 'piano' else 'left hand'
        v = d.get('velocity') or {}
        L.append(f"  note dynamics, {hand}: level spread (10-90 %) {d.get('spreadDb')} dB, within phrases "
                 f"{d.get('phraseSpreadDb')} dB, dynamics {d.get('dynamicsDb')} dB; velocities p10 {v.get('p10')} "
                 f"p90 {v.get('p90')} (min {v.get('min')}, max {v.get('max')})")
        secs = d.get('sections') or []
        if secs:
            L.append('     spread per section (dB): ' + '  '.join(
                f"{SECTION_NAMES.get(s['section'], s['section'])} {s.get('spreadDb')}" for s in secs))
    L.append('  density per section (per bar):  section: RH attacks / RH notes / LH attacks / mean RH top velocity')
    for sec, s, e in _sections(rows):
        bars = max(1e-9, (e - s) / meter)
        rc = [c for c in rh_c if s - 1e-6 <= q(c[0][0]) < e - 1e-6]
        lc = [c for c in lh_c if s - 1e-6 <= q(c[0][0]) < e - 1e-6]
        tv = [max(c, key=lambda n: n[2])[3] for c in rc]
        L.append(f"     {sec:<9} {len(rc) / bars:5.1f} / {sum(map(len, rc)) / bars:5.1f} / {len(lc) / bars:5.1f} / "
                 f"{(sum(tv) / len(tv)) if tv else 0:5.1f}")
    end0 = next((s for sec, s, e in _sections(rows) if sec == 'ending'), total_beats)
    for what, pool in (('highest note', rh), ('highest note before the ending', [n for n in rh if n[0] < end0])):
        top = max(pool, key=lambda n: (n[2], -n[0]))
        tb = bar_of(top[0])
        r = row_of(top[0])
        L.append(f"  {what}: {sp.note(top[2], chord_at(top[0] + 0.06))} at bar {tb + 1} beat "
                 f"{num(q(top[0]) - tb * meter + 1)} ({r[1]}, "
                 f"bar {(tb * meter - r[2]) / meter + 1:.0f} of {round((r[3] - r[2]) / meter)}; "
                 f"{q(top[0]) / total_beats:.0%} into the piece), velocity {top[3]}")
    L.append(f"  lowest note: {sp.note(min(n[2] for n in rh + lh))}")
    return '\n'.join(L) + '\n'


def _sections(rows):
    out = []
    for sec, _, s, e, _ in rows:
        if out and out[-1][0] == sec:
            out[-1] = (sec, out[-1][1], e)
        else:
            out.append((sec, s, e))
    return out


def ids(n: int) -> list[str]:
    rng = random.Random(ID_SEED)
    out = []
    while len(out) < n:
        x = ''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(4))
        if x not in out:
            out.append(x)
    return out


def main() -> int:
    pk = HERE / 'packets'
    pk.mkdir(exist_ok=True)
    for f in pk.glob('*.txt'):
        f.unlink()
    order = list(range(len(PIECES)))
    random.Random(ID_SEED + ':order').shuffle(order)
    key = {}
    for pid, i in zip(ids(len(PIECES)), order):
        kind, folder = PIECES[i]
        song, tune, report = (load_composed if kind == 'composed' else load_generated)(folder)
        render = song.compile()
        check_notes(folder.name, render, report)
        (pk / f"{pid}.txt").write_text(packet(song, tune, report, render), encoding='utf-8')
        key[pid] = {'source': kind, 'path': folder.relative_to(ROOT).as_posix()}
        print(f"wrote packets/{pid}.txt")
    (HERE / 'KEY.json').write_text(json.dumps(dict(sorted(key.items())), indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
