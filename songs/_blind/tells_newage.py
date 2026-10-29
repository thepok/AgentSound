"""The all-generated new-age blind round's tells (round g1, songs/_blind/ROUNDS.md) measured on the endless new-age
pieces, no audio - before / after numbers for the teacher's fixes.

    python songs/_blind/tells_newage.py [--seeds 64000-64023] [--json OUT] [--per-seed]

Per seed: compose (mood rolled; the set-level draws of its seed), build, composer.score, and:
  off_scale    right-hand notes of a figure / ornament (<= 1/3 beat) outside the local chord scale (the chord's scale in
               the key the section plays in: perform._local_scale) - g1 tell 1: runs in the home key's scale
  b4_share     share of the build / climax bars with a fast right-hand run (3+ notes <= 1/3 beat) starting on the
               last beat; b4_streak the longest run of such bars in a row - g1 tell 3: the beat-4 16ths every bar
  clx_rhythm   the climax's 2-bar units' onset rhythm against the hook's (A1's first unit, or it augmented): mean
               Jaccard of the onsets on a 1/12-beat grid - g1 tell 2: a climax not derived from the theme
  ret_copy     the most copied return (A2 / A3 / A4 against A1): share of bars whose right-hand notes (onset, pitch)
               equal A1's bar; ret_chart the same for the chords - g1 tell 4
  open         A1's first two bars' onset rhythm (a set-level count of distinct openings is printed)
  grabs        4+ right-hand notes of <= 0.12 beat chained within 0.1 beat (the packet printed them as a chord)
  rh_silent    share of the bars with no right-hand note sounding (end bar excluded); rh_gap the longest such run
  xx_inv       bar pairs 'X | X/inversion' (the same chord, the second over another bass)
  clx_den      the climax's right-hand onsets per bar over the build's (1 = as busy; g1: TKSA's climax thinner)
  clx_foreign  the climax in another key; clx_octave: the chorus an octave up (lift / climb) - g1 tell 2's transplants
  hand_bal ... rh_med   composer.hands_tells: the hands' balance per phrase (note energy) and the register
                        (HUMAN_FEEDBACK 2026-10-15: the right hand always louder; too many very high notes)
  aud_*        with --folders and a report.json: the hands' balance in the render (audio_balance; per piece also the
               three moments where the left hand comes forward most)
The g2 set-level tells (form_tells; songs/_blind/ROUNDS.md round g2):
  layout       the arrangement's form (plan['set']['layout'])
  top_at       where the highest right-hand note falls (its first strike / the piece's length; g2: 71-76 % in 10/10)
  grid8        share of the part sections 8 or 9 form bars long (g2: '8 + 1 held bar' everywhere)
  end_sus      share of the inner section ends (every section but the last) closing Xsus4 -> X or on a sus4
  end_V        share of the inner section ends on the dominant (a half close)
  end_kinds    distinct closing formulas (the last two chords as degrees) over the inner section ends
  clx_tile     the longest run of climax bars whose top line repeats the bar before's rhythm and intervals
  clx_hold     the climax's longest top-line stretch on one pitch (beats; g2: WKUS F5 for four bars)
  weave        bars with 3+ fast right-hand notes under a held right-hand note (the soft 16th broken chord)
  end_rh       the final chord's right-hand notes (g2: always a 4-note grip)
  mel_rate ... inner_move   composer.flow_tells: the right hand's flow (melody pace, the velocity line, chords /
               dyads under the tune, inner motion under held notes; HUMAN_FEEDBACK 2026-10-15 "one finger")
--sets K: K sets of --set-n tunes (composer.set_plan; seed the first --seeds value + 1000 per set, one candidate per
slot) - per set: layouts distinct / repeated back to back, the top_at spread, the pieces with a weave, routes of 3 /
4 chords (degrees and quality, the bass dropped) shared by two pieces of the set; the signature moves (sig_repeat
a move's fingerprint twice in a set - must be 0; sig_max_share the most used move's share - at most 0.4; sig_none
pieces without a move; sig_moves moves per piece); round g11: peak_distinct the distinct highest notes in a set,
peak_a6 the pieces peaking on Ab6 / A6+, clx_lh_top the most played climax left-hand figure's pieces, clx_lh_kinds the
distinct ones.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import endless  # noqa: E402
from agentsound.endless import composer, genres  # noqa: E402
from agentsound.endless.perform import _local_scale  # noqa: E402
from agentsound.endless.composer import RaisedPcs  # noqa: E402
from agentsound.theory import Key  # noqa: E402

FAST = 1 / 3 + 1e-3
UNDER_HELD = 0.25
"""An inner voice: a note struck under a higher right-hand note held this many beats past its onset (the packets'
'(under)'; round g12: 0.1 before - a finger legato's overlap, up to ~100 ms, read as the melody's next note struck under
it, a hole in the line)."""


def _sections(song):
    return [(n, a, z) for n, a, z in song.endless_sections]


def _chord_at(tl, t):
    return next((sym for a, b, sym in tl if a - 1e-6 <= t < a + b - 1e-6), None)


def _onsets(notes, a, z, grid=12):
    return {round((n[0] - a) * grid) for n in notes if a - 1e-6 <= n[0] < z - 1e-6}


def _jacc(x, y):
    return len(x & y) / max(1, len(x | y))


def measure(tune, song) -> dict:
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    tl = song.endless_timeline
    secs = _sections(song)
    spans = [(a, z, RaisedPcs(p)) for a, z, p in getattr(song, 'endless_keys', None) or
             [(0, 1e9, sorted(set(Key(tune.key).pcs)))]]
    out = {}
    # 1: figure / ornament notes outside the local chord scale
    off = 0
    for t, d, p, _ in rh:
        if d > FAST:
            continue
        sym = _chord_at(tl, t)
        if sym and p % 12 not in _local_scale(spans, t, sym):
            off += 1
    out['off_scale'] = off
    # 3: beat-4 runs in the build / climax
    fast = [n for n in rh if n[1] <= FAST]
    bars, flags = 0, []
    bloom = (getattr(song, 'endless_bloom', None) or {}).get('section')
    for name, a, z in secs:
        if name not in ('build', 'climax', bloom):
            continue
        for k in range(int(round((z - a) / m))):
            t0 = a + k * m
            run = [n for n in fast if t0 + m - 1 - 1e-6 <= n[0] < t0 + m - 1e-6]
            flags.append(len(run) >= 3)
            bars += 1
        flags.append(False)
    out['b4_share'] = round(sum(flags) / max(1, bars), 2)
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    out['b4_streak'] = best
    # 2: the climax's rhythm against the hook's
    unit = 2 * m
    hook = [n for n in (tune.motif or tune.melody[tune.parts[0]]) if n[0] < unit - 1e-6]
    h1 = {round(st_ * 4) for st_, *_ in hook}
    h2 = {round(st_ * 8) for st_, *_ in hook}             # (augmented: twice as slow)
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    if cl:
        mel = [n for n in rh if n[1] > FAST]
        sims = []
        for k in range(int(round((cl[1] - cl[0]) / unit))):
            a = cl[0] + k * unit
            on = _onsets(mel, a, a + unit, grid=4)
            sims.append(max(_jacc(on, h1), _jacc(on, {x for x in h2 if x < unit * 4}),
                            _jacc(on, {x - unit * 4 for x in h2 if x >= unit * 4})))
        out['clx_rhythm'] = round(st.mean(sims), 2) if sims else 0.0
    # 4: copied returns
    a1 = next(((a, z) for n, a, z in secs if n == 'A1'), None)
    rc, cc = 0.0, 0.0
    if a1:
        def bar_notes(a, k):                           # (the top line, pitch classes: an octave-up return copies)
            top = {}
            for n in rh:
                if a + k * m - 0.1 <= n[0] < a + (k + 1) * m - 0.1 and n[1] > FAST:
                    key_ = round(n[0] * 10)
                    top[key_] = max(top.get(key_, (0, 0)), (n[2], n[0]))
            return sorted((t - a - k * m, p % 12) for p, t in top.values())

        def same_bar(x, y):                            # (the performance's timing: onsets on an 8th grid; a turn
            x, y = {(round(2 * t), p) for t, p in x}, {(round(2 * t), p) for t, p in y}    # or a passing note
            return bool(x) and _jacc(x, y) >= 0.7                                          # more: still a copy)
        As = [(a, z) for n, a, z in secs if n in ('A1', 'A2', 'A3', 'A4')]
        for j, (a, z) in enumerate(As):                # (every return against every earlier A)
            for a0, z0 in As[:j]:
                nb = int(round(min(z - a, z0 - a0) / m))
                if nb:
                    same = sum(same_bar(bar_notes(a, k), bar_notes(a0, k)) for k in range(nb))
                    ch = sum(_chord_at(tl, a + k * m + 0.01) == _chord_at(tl, a0 + k * m + 0.01) for k in range(nb))
                    rc, cc = max(rc, same / nb), max(cc, ch / nb)
        out['open'] = ' '.join(f"{x:g}" for x in sorted({round(4 * (n[0] - a1[0])) / 4 for n in rh
                                                          if a1[0] - 1e-6 <= n[0] < a1[0] + 2 * m - 1e-6 and n[1] > FAST}))
    out['ret_copy'], out['ret_chart'] = round(rc, 2), round(cc, 2)
    # 5: grabs (the packet's 0.1-beat chaining)
    g, cl_ = 0, []
    for n in rh:
        if cl_ and n[0] - cl_[-1][0] < 0.1:
            cl_.append(n)
        else:
            g += len(cl_) >= 4 and sum(x[1] <= 0.12 for x in cl_) >= 3
            cl_ = [n]
    g += len(cl_) >= 4 and sum(x[1] <= 0.12 for x in cl_) >= 3
    out['grabs'] = g
    # 6: the right hand's silent bars, X | X/inversion pairs, the climax's density against the build's
    end = secs[-1][2]
    nb = int(round(end / m))
    silent = [not any(n[0] < (k + 1) * m - 1e-6 and n[0] + n[1] > k * m + 1e-6 for n in rh) for k in range(nb)]
    out['rh_silent'] = round(sum(silent) / max(1, nb), 3)
    best = cur = 0
    for f in silent:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    out['rh_gap'] = best
    syms = [_chord_at(tl, k * m + 0.01) for k in range(nb)]
    xx = 0
    for x, y in zip(syms, syms[1:]):
        if x and y and x != y and '/' in y and x.split('/')[0] == y.split('/')[0]:
            xx += 1
    out['xx_inv'] = xx
    dens = {}
    for n_, a, z in secs:
        if n_ in ('build', 'climax'):
            dens[n_] = len({round(n[0], 2) for n in rh if a - 1e-6 <= n[0] < z - 1e-6}) / max(1, (z - a) / m)
    if len(dens) == 2:
        out['clx_den'] = round(dens['climax'] / max(1e-9, dens['build']), 2)
    A = getattr(song, 'endless_arrangement', None)
    if A is not None:                                  # (the climax's kind and key: a transplant - the chorus an
        k_ = A.get('climax', 'key')                    # octave up, a whole climax in another key)
        out['clx_foreign'] = int(bool(k_) and k_ != 'home')
        out['clx_octave'] = int(A.get('climax', 'climax') in ('lift', 'climb'))
    out.update(composer.hands_tells(song))             # the hands' balance (notes) and the register
    out.update(form_tells(tune, song))                 # the g2 set-level tells
    out.update(composer.flow_tells(song))              # the right hand's flow (HUMAN_FEEDBACK 2026-10-15)
    out.update(g3_tells(tune, song))                   # the g3 judges' fixes
    out.update(composer.signature_tells(song, tune))   # the signature moves (docs/PIANO_MOVES.md)
    out.update(g4_tells(tune, song))                   # the g4 judges' fixes
    out.update(g5_tells(tune, song))                   # the g5 judges' fixes
    out.update(g7_tells(tune, song))                   # the g6 judges' fixes (round g7)
    out.update(g8_tells(tune, song))                   # the g7 judges' fixes (round g8)
    out.update(g9_tells(tune, song))                   # the g8 judges' fixes (round g9)
    out.update(g10_tells(tune, song))                  # the g9 judges' fixes (round g10)
    out.update(g11_tells(tune, song))                  # the g10 judges' fixes (round g11)
    out.update(g12_tells(tune, song))                  # the g11 judges' fixes (round g12)
    out.update(g13_tells(tune, song))                  # the g12 judges' fixes (round g13)
    out.update(g14_tells(tune, song))                  # the g13 judges' fixes (round g14)
    return out


def _edb_notes(rh, lh, a, z):
    """The right hand's note energy over the left hand's in [a, z) (dB; None when a hand is silent)."""
    er = sum((n[3] / 127.0) ** 2.5 for n in rh if a - 1e-6 <= n[0] < z - 1e-6)
    el = sum((n[3] / 127.0) ** 2.5 for n in lh if a - 1e-6 <= n[0] < z - 1e-6)
    return round(10 * math.log10(er / el), 2) if er > 0 and el > 0 else None


def g3_tells(tune, song) -> dict:
    """The g3 judges' fixes measured (songs/_blind/ROUNDS.md "Round g3"):
      phrase_rests  composer.phrase_rests (the breath at the phrase ends; g3 cost ~0.8 -> ~0.58)
      clx_bal       the right hand's note energy over the left's in the climax (dB; g3: the hands 0-2 dB there)
      clx_pk_bal    ... in the 2 bars around the climax's highest note
      clx_vmax      the climax's loudest right-hand velocity; clx_v112 its notes over 112 (g3: v115-126 hammered)
      clx_flat      share of the climax's bars whose loudest melody velocity is within 6 of the climax's loudest (a
                    plateau, not a curve)
      clx_down      share of the climax's bars with a right-hand onset in their first beat (g3: beat-4-only entries)
      blk_copy      4-bar blocks inside one section whose top line copies an earlier block of it (g3: the extensions)
      a_leap        the theme's head (A1's first two bars): its largest interval (semitones); a_span: A1's first 4
                    bars' range; b_over: the chorus's first 8 bars' range minus A1's (B outshining A)
      key_in / key_out  a climax in another key: a pivot chord (diatonic to both keys) in the 2 bars before it / in
                    its own last 2 bars (1 / 0; absent when the climax stays home)"""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    tl = song.endless_timeline
    out = {'phrase_rests': composer.phrase_rests(song)}
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    if cl:
        a, z = cl
        out['clx_bal'] = _edb_notes(rh, lh, a, z)
        mel = [n for n in rh if a - 1e-6 <= n[0] < z - 1e-6 and n[1] > FAST]
        if mel:
            pk = max(mel, key=lambda n: (n[2], -n[0]))
            b0 = a + m * int((pk[0] - a) // m)
            out['clx_pk_bal'] = _edb_notes(rh, lh, max(a, b0 - m), min(z, b0 + m))
            out['clx_vmax'] = max(n[3] for n in rh if a - 1e-6 <= n[0] < z - 1e-6)
            out['clx_v112'] = sum(n[3] > 112 for n in rh if a - 1e-6 <= n[0] < z - 1e-6)
            nb = int(round((z - a) / m))
            e_ = 0.12                                  # (the player's timing: a downbeat struck a hair early)
            tops = [max((n[3] for n in mel if a + k * m - e_ <= n[0] < a + (k + 1) * m - e_), default=None)
                    for k in range(nb)]
            tops = [t for t in tops if t is not None]
            out['clx_flat'] = round(sum(t >= max(tops) - 6 for t in tops) / max(1, len(tops)), 2)
            out['clx_down'] = round(sum(any(a + k * m - e_ <= n[0] < a + k * m + 1.0 - e_ for n in rh)
                                        for k in range(nb)) / max(1, nb), 2)
    copies = 0
    for name, a, z in secs:
        if name in ('intro', 'inter', 'coda', 'end'):
            continue
        nb = int(round((z - a) / m))

        def block(k):
            top = {}
            for n in rh:
                if a + k * m - 0.1 <= n[0] < a + (k + 4) * m - 0.1 and n[1] > FAST:
                    key_ = round(2 * (n[0] - a - k * m))
                    top[key_] = max(top.get(key_, 0), n[2])
            return set(top.items())
        for k in range(4, nb - 3):
            x = block(k)
            if len(x) >= 4 and any(_jacc(x, block(j)) >= 0.85 for j in range(0, k - 3)):
                copies += 1
                break
    out['blk_copy'] = copies
    unit = 2 * m * (2 if m == 3 else 1)
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])
    head = [n for n in a1 if n[0] < unit - 1e-6]
    if len(head) >= 2:
        out['a_leap'] = max(abs(y[2] - x[2]) for x, y in zip(head, head[1:]))
    four = [n[2] for n in a1 if n[0] < 2 * unit - 1e-6]
    if four:
        out['a_span'] = max(four) - min(four)
    if 'B' in tune.melody and a1:
        b8 = [n[2] for n in tune.melody['B'] if n[0] < 4 * unit - 1e-6]
        a8 = [n[2] for n in a1 if n[0] < 4 * unit - 1e-6]
        if b8 and a8:
            out['b_over'] = (max(b8) - min(b8)) - (max(a8) - min(a8))
    keys = getattr(song, 'endless_keys', None) or []
    if cl and keys:
        home = set(keys[0][2])
        new = next((set(p) for a_, z_, p in keys[1:] if a_ - 1e-6 <= cl[0] + m < z_), None)
        if new is not None and new != home:
            from agentsound.theory import chord as _chord
            t_pc = Key(tune.key).tonic % 12
            mix = home | {(t_pc + i) % 12 for i in ((3, 8, 10) if tune.key.endswith('major') else (4, 9, 11))}

            def pivot(t0, t1):                         # (not the dominant 7th that leads in / out)
                for t, b, sym in tl:
                    if t0 - 1e-6 <= t < t1 - 1e-6:
                        c = _chord(sym)
                        if 4 in c.intervals and 10 in c.intervals:
                            continue
                        tri = {(c.root + i) % 12 for i in c.intervals[:3]}
                        if tri <= new and tri <= mix:
                            return 1
                return 0
            bars = 2 * (2 if m == 3 else 1) * m
            out['key_in'] = pivot(cl[0] - bars, cl[0])
            out['key_out'] = pivot(cl[1] - bars, cl[1])
    return out


def _top_line(rh, a, z):
    """The right hand's top line in [a, z): per onset its highest note (figures / ornaments under 1/3 beat out)."""
    out = []
    ns = sorted(x for x in rh if x[1] > FAST and a - 0.12 <= x[0] < z - 0.12)    # (a downbeat struck early)
    for n in ns:
        if out and n[0] - out[-1][1] < 0.08:          # (a chord / a rolled grip: one onset, its top note)
            if n[2] > out[-1][0][2]:
                out[-1] = (n, out[-1][1])
            continue
        out.append((n, n[0]))
    return [n for n, _ in out]


def head_match(head, line) -> tuple:
    """How well `line` (notes) states `head` (the theme's first notes) somewhere: per start, the share of the head's
    steps sung in the same direction within a semitone of its interval (a diatonic transposition) and in its rhythm
    (the inter-onset ratio within 35 %, as written or augmented x2) -> (the best share, its onset)."""
    if len(head) < 4 or len(line) < 3:
        return 0.0, None
    best = (0.0, None)
    for hd in (head, head[1:]):                        # (the first note may be re-fitted / a pickup moved)
        h0 = hd[0]
        for i, x0 in enumerate(line):
            for s in (1.0, 2.0):                       # (connecting notes / ornaments between: skipped - each head
                ok, prev = 0, (h0[2], x0[2])           # note looked up at its own onset, its step from the note
                for h in hd[1:]:                       # before within a semitone, the same direction)
                    want = x0[0] + s * (h[0] - h0[0])
                    c = sorted((n for n in line[i + 1:] if abs(n[0] - want) <= 0.2 * s + 1e-6),
                               key=lambda n: abs(n[0] - want))
                    hit = None
                    for n in c:
                        d_h, d_l = h[2] - prev[0], n[2] - prev[1]
                        if abs(d_h - d_l) <= 1 and (d_h > 0) == (d_l > 0) and (d_h < 0) == (d_l < 0):
                            hit = n
                            break
                    if hit is not None:
                        ok += 1
                        prev = (h[2], hit[2])
                r = ok / (len(head) - 1)               # (over the whole head: a skipped first note costs one)
                if r > best[0]:
                    best = (round(r, 2), x0[0])
    return best


G4_TELLS = ('clx_theme', 'clx_hook', 'clx_theme_pk', 'casc_last', 'casc_held', 'ret_head', 'ret_tail', 'key_dom',
            'key_home', 'clx_loud', 'b1_in', 'chart_loop', 'motto_low')


def g4_tells(tune, song) -> dict:
    """The g4 judges' fixes measured (songs/_blind/ROUNDS.md "Round g4"):
      clx_theme     the climax states the theme: the best head_match of A1's first 8 notes (as written) in its top line (1 = the
                    head's contour and rhythm, transposed within a semitone; g4: the climax had no theme in 7 of 8)
      clx_hook      ... of A1's or the chorus's head (the better)
      clx_theme_pk  the theme's head (head_match >= 0.7) sung at the climax's peak: within 2 bars of its highest note
      casc_last     a cascade in the climax's last bar (a link out); casc_held: a melody note held over it, above it
      ret_head / ret_tail   the returns (A2 / A3 / A4): the share of their first-half bars copying A1's (mean) /
                    of their second-half bars copying any earlier A statement's (max; the top line's pitch classes on
                    an 8th grid): the head kept, the continuation varied (g4: ZKYC 5 = 13 = 33 = 57, ANQT A4 = A2)
      key_dom       a climax in another key: the bar before it on the new key's dominant (V / V7 / V7sus4) for the
                    whole bar; key_home: its last bar on the home dominant
      clx_loud      the climax's note energy per beat (both hands, dB) over the loudest other part section's (g4: a
                    build / B1 louder than the climax); b1_in: B1's first 2 bars against the climax (dB; NYVX v86-106)
      chart_loop    4-bar chord charts played twice in a row inside a section (ANQT 41-44 = 45-48)
      pen_bar       the penultimate bar's chords as degrees (the set tell: one IV-iv6 split in 4 of 8)
      motto_low     a motto statement with notes under E4 (the left hand's register; HNGF 27 D4, ZKYC 57 D4-Bb3)
      motto_start   the motto's first pitch (the set tell: three mottos from D5)"""
    m = int(song.beats_per_bar)
    stretch = 2 if m == 3 else 1
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    tl = song.endless_timeline
    t_pc = Key(tune.key).tonic % 12
    out = {}
    unit = 2 * m * stretch
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    a1s = next(((a, z) for n, a, z in secs if n == 'A1'), None)
    b1s = next(((a, z) for n, a, z in secs if n in ('B1', 'B')), None)
    # (the theme as written: its first 8 notes - the skeleton; the connecting notes the texture adds skipped)
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])[:8]
    if cl and len(a1) >= 4:
        line = _top_line(rh, *cl)
        r_a, at_a = head_match(a1, line)
        r_b = head_match(sorted(tune.melody['B'])[:8], line)[0] if tune.melody.get('B') else 0.0
        out['clx_theme'], out['clx_hook'] = r_a, max(r_a, r_b)
        if line:
            pk = max(line, key=lambda n: (n[2], -n[0]))
            near = _top_line(rh, pk[0] - 2 * m * stretch, pk[0] + 2 * m * stretch)
            out['clx_theme_pk'] = int(head_match(a1, near)[0] >= 0.7)
    sg = getattr(song, 'endless_signature', None) or {}
    ca = next((d for d in sg.get('statements') or [] if d['move'] == 'cascade'), None)
    if ca is not None and cl:
        out['casc_last'] = int(ca['end'] >= cl[1] - 1e-6 and ca['at'] >= cl[1] - m * stretch - 1e-6)
        cs = [n for n in rh + lh if ca['at'] - 0.05 <= n[0] < ca['end'] - 0.05 and n[1] <= 1.0]
        top_c = max((n[2] for n in cs), default=0)
        out['casc_held'] = int(any(n[0] <= ca['at'] + 1e-3 and n[0] + n[1] >= ca['end'] - 0.3 and n[2] > top_c
                                   for n in rh))
    if a1s:
        def bar_top(a, k):
            return {(round(2 * (n[0] - a - k * m)), n[2] % 12) for n in _top_line(rh, a + k * m - 0.1, a + (k + 1) * m - 0.1)}

        def same(x, y):
            return bool(x) and _jacc(x, y) >= 0.7
        heads, tails = [], []
        As = [(n_, a, z) for n_, a, z in secs if n_ in ('A1', 'A2', 'A3', 'A4')]
        for j, (n_, a, z) in enumerate(As):
            if n_ == 'A1':
                continue
            h = int(round((a1s[1] - a1s[0]) / m)) // 2  # (the theme's second half: a half return has none)
            for _, a0, z0 in As[:j]:                   # (against every earlier statement: A4 = A2 too)
                nb = int(round(min(z - a, z0 - a0) / m))
                if nb <= h:
                    continue
                cp = [same(bar_top(a, k), bar_top(a0, k)) for k in range(nb)]
                if a0 == a1s[0]:
                    heads.append(sum(cp[:h]) / h)
                tails.append(sum(cp[h:]) / (nb - h))
        if heads:
            out['ret_head'] = round(st.mean(heads), 2)
        if tails:
            out['ret_tail'] = round(max(tails), 2)
    keys = getattr(song, 'endless_keys', None) or []
    if cl and keys:
        from agentsound.theory import chord as _chord
        new = next(((a_, p) for a_, z_, p in keys[1:] if a_ - 1e-6 <= cl[0] + m < z_), None)
        if new is not None and set(new[1]) != set(keys[0][2]):
            bar0 = cl[0] - m * stretch
            syms = [(t, b, s_) for t, b, s_ in tl if t + b > bar0 + 1e-6 and t < cl[0] - 1e-6]
            # the new key's tonics: the major key whose scale its tones are, and its relative minor (a minor key's
            # tones with the raised 7th: its harmonic minor)
            pcs_ = set(new[1])
            doms = set()
            for t_ in range(12):
                if {(t_ + i) % 12 for i in (0, 2, 4, 5, 7, 9, 11)} == pcs_:
                    doms |= {(t_ + 7) % 12, (t_ + 4) % 12}
                if {(t_ + i) % 12 for i in (0, 2, 3, 5, 7, 8, 11)} <= pcs_ | {(t_ + 10) % 12}:
                    doms.add((t_ + 7) % 12)
            first = next((s_ for t, b, s_ in tl if t >= cl[0] - 1e-6), None)     # (round g6: or the dominant of
            if first is not None:                                                 # the climax's first chord - D#7
                doms.add((_chord(first).root + 7) % 12)                           # into G#m7)
            out['key_dom'] = int(bool(syms) and all(_chord(s_).root % 12 in doms and not _chord(s_).is_minor
                                                    for *_, s_ in syms))
            last = [s_ for t, b, s_ in tl if t + b > cl[1] - m * stretch + 1e-6 and t < cl[1] - 1e-6]
            out['key_home'] = int(bool(last) and _chord(last[-1]).root % 12 == (t_pc + 7) % 12)

    def energy(a, z):
        e = sum((n[3] / 127.0) ** 2.5 for n in rh + lh if a - 1e-6 <= n[0] < z - 1e-6)
        return 10 * math.log10(e / max(1e-9, z - a)) if e > 0 else None
    if cl:
        ec = energy(*cl)
        others = [energy(a, z) for n_, a, z in secs if n_ not in ('climax', 'intro', 'inter', 'coda', 'end')]
        others = [x for x in others if x is not None]
        if ec is not None and others:
            out['clx_loud'] = round(ec - max(others), 2)
        b1 = next(((a, z) for n_, a, z in secs if n_ == 'B1'), None)
        if b1 and ec is not None:
            e1 = energy(b1[0], min(b1[1], b1[0] + 2 * m * stretch))
            if e1 is not None:
                out['b1_in'] = round(e1 - ec, 2)
    loops = 0
    for n_, a, z in secs:
        nb = int(round((z - a) / m))
        bars_ = [_chord_at(tl, a + k * m + 0.01) for k in range(nb)]
        w = 4 * stretch
        loops += any(bars_[k:k + w] == bars_[k + w:k + 2 * w] for k in range(0, nb - 2 * w + 1))
    out['chart_loop'] = loops
    end_ = secs[-1][2]
    pen = [s_ for t, b, s_ in tl if t + b > end_ - m - 1e-6 and t < end_ - 1e-6]
    out['pen_bar'] = ' '.join(_deg(s_, t_pc) for s_ in pen)
    mo = [d for d in sg.get('statements') or [] if d['move'] == 'motto']
    if mo:
        out['motto_low'] = int(any(p < 64 for d in mo for _, _, p in d['notes']))
        pl = next((d for d in mo if d['role'] == 'plant'), mo[0])
        out['motto_start'] = pl['notes'][0][2]
    return out


G5_TELLS = ('a_med', 'a_lo', 'a_gap', 'b_med', 'bld_med', 'clx_med', 'clx_lo', 'clx_up', 'clx_c6', 'c6_out',
            'pk_near', 'b1_pk', 'bars', 'build_bars', 'clx_lh_den', 'clx_rh_den', 'contrast')


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def g5_tells(tune, song) -> dict:
    """The g5 judges' fixes measured (songs/_blind/ROUNDS.md "Round g5"; the melody is the right hand's top line,
    _top_line):
      a_med / a_lo  the A statements' (A1-A4) melody: median / 10th percentile pitch (g5: E4-C5, inside the left hand)
      a_gap         ... their melody's 10th percentile minus the left hand's 90th percentile in the same sections
      b_med / bld_med / clx_med   the chorus's (B1 / B) / the build's / the climax's melody median
      clx_lo        the climax melody's 10th percentile (a dip back into the alto); clx_up: clx_med - A1's median
                    (g5: the climax in A1's register - every judge's first fix: an octave up, the C6 band)
      clx_c6        share of the climax melody at or above C6 (84); c6_out: share of ALL right-hand notes at or above
                    C6 outside the climax (the user: "too many very high notes" - rare outside the climax)
      pk_near       part sections (not the climax) whose loudest right-hand velocity reaches the climax's loudest
                    minus 4; b1_pk: B1's loudest minus the climax's (g5: QTZG B1 v108, AZTL v115)
      bars / build_bars   the piece's / the build's length in bars (g5: the waltz 129 bars, a 20-bar build)
      clx_lh_den / clx_rh_den   the climax's left-hand / right-hand (melody) onsets per bar (g5: GNRR 12.2 / XXUB 3.4)
      contrast      the piece has a contrasting section (B / build) besides the A statements (g5: 'variations' none)"""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    out = {'bars': int(round(secs[-1][2] / m)) if secs else 0}
    mel = {name: [n[2] for n in _top_line(rh, a, z)] for name, a, z in secs}
    a_ = [p for name, ps in mel.items() if name in ('A1', 'A2', 'A3', 'A4') for p in ps]
    if a_:
        out['a_med'], out['a_lo'] = st.median(a_), _pct(a_, 0.1)
        lh_a = [n[2] for name, a, z in secs if name in ('A1', 'A2', 'A3', 'A4') for n in lh if a <= n[0] < z]
        if lh_a:
            out['a_gap'] = out['a_lo'] - _pct(lh_a, 0.9)
    for k, names in (('b_med', ('B1', 'B')), ('bld_med', ('build',)), ('clx_med', ('climax',))):
        xs = [p for name in names for p in mel.get(name) or ()]
        if xs:
            out[k] = st.median(xs)
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    if cl and mel.get('climax'):
        out['clx_lo'] = _pct(mel['climax'], 0.1)
        if mel.get('A1'):
            out['clx_up'] = out['clx_med'] - st.median(mel['A1'])
        out['clx_c6'] = round(sum(p >= 84 for p in mel['climax']) / len(mel['climax']), 2)
        nb = max(1, int(round((cl[1] - cl[0]) / m)))
        out['clx_lh_den'] = round(len({round(n[0], 2) for n in lh if cl[0] <= n[0] < cl[1]}) / nb, 1)
        out['clx_rh_den'] = round(len(mel['climax']) / nb, 1)
        vpk = max((n[3] for n in rh if cl[0] - 1e-6 <= n[0] < cl[1] - 1e-6), default=0)
        near = 0
        for name, a, z in secs:
            if name in ('climax', 'intro', 'inter', 'coda', 'end'):
                continue
            v = max((n[3] for n in rh if a - 1e-6 <= n[0] < z - 1e-6), default=0)
            near += v >= vpk - 4
            if name in ('B1', 'B'):
                out['b1_pk'] = v - vpk
        out['pk_near'] = near
    out_ = [n[2] for n in rh if not (cl and cl[0] - 1e-6 <= n[0] < cl[1] - 1e-6)]
    if out_:
        out['c6_out'] = round(sum(p >= 84 for p in out_) / len(out_), 3)
    bl = next(((a, z) for n, a, z in secs if n == 'build'), None)
    if bl:
        out['build_bars'] = int(round((bl[1] - bl[0]) / m))
    out['contrast'] = int(any(n in ('B1', 'B', 'build', 'B2') for n, *_ in secs))
    return out


G7_TELLS = ('clx_hole', 'clx_cell', 'clx_c6_run', 'clx_swell', 'a1_holes', 'head_nbr', 'post_copy', 'post_rest',
            'bld_lh_den', 'b_lh_den', 'intro_v', 'b1_vd', 'clx_theme_step', 'clx_theme_seq', 'clx_theme_reharm')


def g7_tells(tune, song) -> dict:
    """The g6 judges' fixes measured (songs/_blind/ROUNDS.md "Round g6"; the melody is _top_line):
      clx_hole      climax bars (its last one out) without a melody onset (g6: XUMB's chords climax breaks off at bar 43)
      clx_cell      the most repeated 3-note pitch cell of the climax's melody (consecutive notes, exact pitches:
                    g6 FUKP's 'sequence' looped D-Eb-C 8-12 times)
      clx_c6_run    the longest run of climax bars whose melody lies mostly at or above C6 (the user: "too many very
                    high notes"; g6 performer: SGVL nine bars at C6+); clx_c6 (g5_tells) the share
      clx_swell     the climax's own arc: the melody's mean velocity in the 2 bars round its peak note minus its first
                    2 bars' (g6: XUMB flat at v98)
      a1_holes      A1 bars (not a 4-bar phrase's last; a waltz's 8th) whose right hand sounds under half the bar
                    (g6: XEDV, a pickup and then half-empty bars); head_nbr: A1's first 4 notes inside a whole step,
                    the last a repeat (g6: WHKZ's B-C-D-C neighbour head)
      post_copy     the first A after the climax: share of its bars copying an earlier A bar note for note (the
                    top line's pitches on an 8th grid and the bar's chord, Jaccard >= 0.7: a new register or new
                    chords count as varied; g6: WHKZ / QNFS / GVPE literal); post_rest: its bars (the last one out)
                    with no right-hand onset (g6: TLTG 44, 48)
      bld_lh_den / b_lh_den   left-hand attacks a bar in the build / the chorus (g6: GVPE / QNFS 12-13)
      intro_v       the intro's loudest right-hand velocity (g6: TLTG v88); b1_vd: B1's mean right-hand velocity
                    minus the climax's (g6: FUKP's waltz B1 at climax level)
      clx_theme_step / _seq / _reharm   clx_theme (g4_tells) for the 'step' climaxes / the 'sequence' / 'reharm'
                    anthems"""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    out = {}
    e_ = 0.12
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    if cl:
        a, z = cl
        nb = int(round((z - a) / m))
        line = _top_line(rh, a, z)
        out['clx_hole'] = sum(not any(a + k * m - e_ <= n[0] < a + (k + 1) * m - e_ for n in line) for k in range(nb - 1))
        ps = [n[2] for n in line]
        cells = [tuple(ps[i:i + 3]) for i in range(len(ps) - 2)]
        out['clx_cell'] = max((cells.count(c) for c in set(cells)), default=0)
        run = best = 0
        for k in range(nb):
            bp = [n[2] for n in line if a + k * m - e_ <= n[0] < a + (k + 1) * m - e_]
            run = run + 1 if bp and sum(p >= 84 for p in bp) > len(bp) / 2 else 0
            best = max(best, run)
        out['clx_c6_run'] = best
        if line:
            pk = max(line, key=lambda n: (n[2], -n[0]))
            b0 = a + m * int((pk[0] - a) // m)
            near = [n[3] for n in line if b0 - m - e_ <= n[0] < b0 + m - e_]
            first = [n[3] for n in line if n[0] < a + 2 * m - e_]
            if near and first:
                out['clx_swell'] = round(st.mean(near) - st.mean(first), 1)
        A = getattr(song, 'endless_arrangement', None)
        kind = A.get('climax', 'climax') if A is not None else None
        anth = (getattr(tune, 'arrange', None) or {}).get('anthem')
        out['clx_kind'], out['anthem'] = kind, anth
        r = g4_tells(tune, song).get('clx_theme') if kind in ('step', 'theme', 'lift') else None
        if r is not None:
            if kind == 'step':
                out['clx_theme_step'] = r
            elif anth == 'sequence':
                out['clx_theme_seq'] = r
            elif anth == 'reharm':
                out['clx_theme_reharm'] = r
    a1s = next(((a, z) for n, a, z in secs if n == 'A1'), None)
    if a1s:
        ph = 8 if m == 3 else 4
        nb = int(round((a1s[1] - a1s[0]) / m))
        holes = 0
        for k in range(nb):
            if (k + 1) % ph == 0:
                continue
            b0, b1 = a1s[0] + k * m, a1s[0] + (k + 1) * m
            iv = sorted((max(b0, n[0]), min(b1, n[0] + n[1])) for n in rh if n[0] < b1 and n[0] + n[1] > b0)
            tot, cur = 0.0, None
            for x, y in iv:
                if cur is None or x > cur[1]:
                    tot += (cur[1] - cur[0]) if cur else 0.0
                    cur = [x, y]
                else:
                    cur[1] = max(cur[1], y)
            tot += (cur[1] - cur[0]) if cur else 0.0
            holes += tot < m / 2
        out['a1_holes'] = holes
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])[:4]
    if len(a1) == 4:
        ps = [n[2] for n in a1]
        out['head_nbr'] = int(max(ps) - min(ps) <= 2 and ps[-1] in ps[:-1])
    if cl:
        post = next(((a, z) for n, a, z in secs if a >= cl[1] - 1e-6 and n in ('A1', 'A2', 'A3', 'A4')), None)
        if post:
            tl = song.endless_timeline

            def bar_top(a, k):                         # (the top line's exact pitches on an 8th grid + the chord)
                return {(round(2 * (n[0] - a - k * m)), n[2]) for n in
                        _top_line(rh, a + k * m - 0.1, a + (k + 1) * m - 0.1)} | {('chord', _chord_at(tl, a + k * m + 0.01))}
            pa, pz = post
            nb = int(round((pz - pa) / m))
            earlier = [(a, z) for n, a, z in secs if n in ('A1', 'A2', 'A3', 'A4') and z <= cl[0] + 1e-6]
            cp = 0
            for k in range(nb):
                x = bar_top(pa, k)
                cp += len(x) > 1 and any(_jacc(x, bar_top(a, j)) >= 0.7 for a, z in earlier
                                         for j in range(int(round((z - a) / m))))
            out['post_copy'] = round(cp / max(1, nb), 2)
            out['post_rest'] = sum(not any(pa + k * m - e_ <= n[0] < pa + (k + 1) * m - e_ for n in rh)
                                   for k in range(nb - 1))
    for key_, names in (('bld_lh_den', ('build',)), ('b_lh_den', ('B1', 'B'))):
        sp = [(a, z) for n, a, z in secs if n in names]
        if sp and lh:
            nb = sum((z - a) / m for a, z in sp)
            out[key_] = round(len({round(n[0], 2) for n in lh if any(a <= n[0] < z for a, z in sp)}) / max(1, nb), 1)
    it = next(((a, z) for n, a, z in secs if n == 'intro'), None)
    if it:
        out['intro_v'] = max((n[3] for n in rh if it[0] - 1e-6 <= n[0] < it[1] - 1e-6), default=0)
    b1 = next(((a, z) for n, a, z in secs if n in ('B1', 'B')), None)
    if b1 and cl:
        vb = [n[3] for n in rh if b1[0] - 1e-6 <= n[0] < b1[1] - 1e-6]
        vc = [n[3] for n in rh if cl[0] - 1e-6 <= n[0] < cl[1] - 1e-6]
        if vb and vc:
            out['b1_vd'] = round(st.mean(vb) - st.mean(vc), 1)
    return out


G8_TELLS = ('head_prof', 'head_leap', 'head_held', 'head_band', 'head_prof_r', 'clx_aug', 'casc', 'tail_share',
            'tail_db', 'a_pre', 'pre_copy', 'ret_lo', 'ret_drop', 'ret_low', 'b1_bal', 'bld_bal', 'rh_hole',
            'rep_chord')


def g8_tells(tune, song) -> dict:
    """The g7 judges' fixes measured (songs/_blind/ROUNDS.md "Round g7"; the melody is _top_line):
      head_prof     the theme's head has a profile (composer.head_profile on A1 as composed: a leap of a 4th+, its top
                    note held, no 2-3 note band circled - g7: JTQL D5-E5, LXCD A4-B4); head_leap / head_held /
                    head_band its parts; head_prof_r the same on the played top line of A1's first two bars
      clx_aug       the climax's anthem 'augment' (g7: JTQL's held single notes); casc: a cascade played (g7: 3 of 3
                    faulted)
      tail_share    the share of the piece after the climax (g7: KTBL's arch, the peak at 57 %); tail_db: the
                    loudest part section after the climax minus the loudest before it, but the climax (note energy
                    per beat, dB - g7: KTBL's A2 +0.3 LU after a B1 at -0.2)
      a_pre         A statements before the climax; pre_copy: the share of the bars of the A statements before the
                    climax (A1 out) copying an earlier A bar note for note (post_copy's test; g7: LXCD 24-26 = 4-6)
      ret_lo / ret_drop / ret_low   the A statements after the climax: their top line's 10th percentile, A1's median
                    minus theirs, the share of their top line under C5 (g7: JTQL A3 F#4-G4, VJGT A3 low)
      b1_bal / bld_bal   the right hand over the left in B1 / the build (note energy dB, the packets' measure; g7:
                    AARM B1 +1.2, JTQL build +1.3)
      rh_hole       bars of the part sections (each section's last bar out) with no right-hand onset and no note tied
                    over half of them (g7: KTBL 20 / 22, AARM 46, VJGT 64)
      rep_chord     bars where the right hand strikes one chord (2+ notes) 3+ times (g7: JTQL 41, VJGT 32)"""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    tl = song.endless_timeline
    out = {}
    e_ = 0.12
    a1 = tune.melody.get(tune.parts[0]) or []
    hp = composer.head_profile(a1, tune.meter)
    out.update(head_prof=int(hp['ok']), head_leap=hp['leap'], head_held=hp['held'], head_band=hp['band'])
    a1s = next(((a, z) for n, a, z in secs if n == 'A1'), None)
    if a1s:
        line = [(n[0] - a1s[0], n[1], n[2]) for n in _top_line(rh, a1s[0] - e_, a1s[0] + 2 * m - e_) if n[1] > FAST]
        out['head_prof_r'] = int(composer.head_profile(line, m)['ok'])
    anth = (getattr(tune, 'arrange', None) or {}).get('anthem')
    A = getattr(song, 'endless_arrangement', None)
    kind = A.get('climax', 'climax') if A is not None else None
    out['clx_aug'] = int(kind in ('theme', 'step') and anth == 'augment')
    sg = getattr(song, 'endless_signature', None) or {}
    out['casc'] = int(any(d['move'] == 'cascade' for d in sg.get('statements') or []))
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    end = secs[-1][2] if secs else 0

    def energy(a, z):
        e = sum((n[3] / 127.0) ** 2.5 for n in rh + lh if a - 1e-6 <= n[0] < z - 1e-6)
        return 10 * math.log10(e / max(1e-9, z - a)) if e > 0 else None

    def bal(a, z):
        er = sum((n[3] / 127.0) ** 2.5 for n in rh if a - 1e-6 <= n[0] < z - 1e-6)
        el = sum((n[3] / 127.0) ** 2.5 for n in lh if a - 1e-6 <= n[0] < z - 1e-6)
        return round(10 * math.log10(er / el), 2) if er > 0 and el > 0 else None
    frames = ('intro', 'inter', 'coda', 'end')
    if cl:
        out['tail_share'] = round((end - cl[1]) / max(1e-9, end), 3)
        pre = [energy(a, z) for n, a, z in secs if n not in frames and n != 'climax' and z <= cl[0] + 1e-6]
        post = [energy(a, z) for n, a, z in secs if n not in frames and n != 'climax' and a >= cl[1] - 1e-6]
        pre, post = [x for x in pre if x is not None], [x for x in post if x is not None]
        if pre and post:
            out['tail_db'] = round(max(post) - max(pre), 2)
        As = [(n, a, z) for n, a, z in secs if n in ('A1', 'A2', 'A3', 'A4')]
        before = [(a, z) for n, a, z in As if z <= cl[0] + 1e-6]
        out['a_pre'] = len(before)

        def bar_top(a, k):
            top = _top_line(rh, a + k * m - 0.1, a + (k + 1) * m - 0.1)
            return {(round(2 * (n[0] - a - k * m)), n[2]) for n in top} | {('chord', _chord_at(tl, a + k * m + 0.01))}
        cp = nb_all = 0
        for i, (a, z) in enumerate(before[1:], 1):
            nb = int(round((z - a) / m))
            for k in range(nb):
                x = bar_top(a, k)
                nb_all += 1
                cp += len(x) > 1 and any(_jacc(x, bar_top(a0, j)) >= 0.7 for a0, z0 in before[:i]
                                         for j in range(int(round((z0 - a0) / m))))
        if nb_all:
            out['pre_copy'] = round(cp / nb_all, 2)
        after = [(a, z) for n, a, z in As if a >= cl[1] - 1e-6]
        lines = [n[2] for a, z in after for n in _top_line(rh, a, z) if n[1] > FAST]
        a1_line = [n[2] for n in _top_line(rh, *a1s) if n[1] > FAST] if a1s else []
        if lines and a1_line:
            out['ret_lo'] = _pct(lines, 0.1)
            out['ret_drop'] = st.median(a1_line) - st.median(lines)
            out['ret_low'] = round(sum(p < 72 for p in lines) / len(lines), 2)
    for k_, names in (('b1_bal', ('B1', 'B')), ('bld_bal', ('build',))):
        sp = next(((a, z) for n, a, z in secs if n in names), None)
        if sp:
            v = bal(*sp)
            if v is not None:
                out[k_] = v
    holes = rep = 0
    for n_, a, z in secs:
        if n_ in frames:
            continue
        nb = int(round((z - a) / m))
        for k in range(nb):
            b0, b1 = a + k * m - e_, a + (k + 1) * m - e_
            ons = [n for n in rh if b0 <= n[0] < b1]
            if k < nb - 1 and not ons and not any(n[0] < b0 and n[0] + n[1] >= b0 + m / 2 for n in rh):
                holes += 1                             # (a note tied over half the bar+: no hole - the packets print it)
            grp = {}
            for n in ons:
                grp.setdefault(round(n[0], 2), set()).add(n[2])
            chords_ = [frozenset(v) for v in grp.values() if len(v) >= 2]
            rep += any(chords_.count(c) >= 3 for c in set(chords_))
    out['rh_hole'], out['rep_chord'] = holes, rep
    return out


G9_TELLS = ('clx_theme_key', 'clx_open', 'clx_open_held', 'bc_hole', 'bc_thin', 'ph_empty', 'a_lh_den',
            'a_lh_busy', 'a_bal', 'a_bal_min', 'ret_head_copy', 'chord_run', 'root_run', 'b_color', 'b_loop', 'tail_bars',
            'arch_tail', 'clx_bars', 'clx_nobuild', 'lone_hi', 'clx_jump', 'arrival')


def g9_tells(tune, song) -> dict:
    """The g8 judges' fixes measured (songs/_blind/ROUNDS.md "Round g8"; the melody is _top_line):
      clx_theme_key  clx_theme (g4_tells) of a climax in another key (g8: NSFY's bVI Eb, JKGC's C major, EUNP's G
                    major heard as new tunes)
      clx_open      the climax's top-line onsets in its first two (form) bars; clx_open_held: 2 or fewer, or a note
                    held 1.5 bars+ there (g8: ECYA's climax opening on two notes held two bars each)
      bc_hole       build / climax bars (each one's last out) with no right-hand onset and no note tied over half of
                    it (g8: JKGC 37 / 42, LXAN 36); bc_thin: ... whose right hand sounds under half the bar
      ph_empty      part-section bars (the build / climax out, each section's last out) whose right hand sounds under
                    a quarter of the bar (g8: PKCG 16 / 24 - a bar of bass alone)
      a_lh_den      the left hand's attacks a bar in the A statements; a_lh_busy: the share of their bars with 12+
                    (3/4: 9+) attacks (g8: DMZT 14-16, all five judges)
      a_bal / a_bal_min   the right hand over the left in the A statements (note energy dB; mean / the lowest A;
                    g8: DMZT A2 +3.0, JKGC A3 +2.3, NSFY A2 +1.7)
      ret_head_copy the share of the A returns whose first two bars copy A1's (the top line's exact pitches on an 8th
                    grid, Jaccard >= 0.7 in both; g8: ZACW 9 / 27 "note for note")
      chord_run     the longest run of form bars on one chord inside a part section (g8: ZACW Am/C 15-18)
      b_color       B1 has a chord outside its key (a secondary dominant, a borrowed chord) or a dominant 7th off the
                    key's V; b_loop: B1 plays a 4-bar chord chart twice (g8: JKGC's Am-F-C-G twice)
      tail_bars     form bars after the climax (the coda in); arch_tail: the same in an arch (g8: NSFY 13, "rushed")
      clx_bars      the climax's form bars; clx_nobuild: a climax of 8 form bars or fewer with no build before it
                    (g8: LXAN "a short, low climax without a build")
      lone_hi       right-hand onsets at C6+ outside the climax with the left hand silent through their bar (g8:
                    DMZT 52's lone F6 before the coda)
      clx_jump      in the climax, consecutive right-hand onsets (each onset's top note) within half a beat 17+
                    semitones apart (g8: PKCG 34-36 "two-octave jumps inside a beat")
      arrival       how the climax arrives (the set draw; plan['set']['arrival'])"""
    m = int(song.beats_per_bar)
    stretch = 2 if m == 3 else 1
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    tl = song.endless_timeline
    frames = ('intro', 'inter', 'coda', 'end')
    out = {}
    e_ = 0.12
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    keys = getattr(song, 'endless_keys', None) or []
    if cl:
        new = next(((a_, p) for a_, z_, p in keys[1:] if a_ - 1e-6 <= cl[0] + m < z_), None)
        if new is not None and keys and set(new[1]) != set(keys[0][2]):
            r = g4_tells(tune, song).get('clx_theme')
            if r is not None:
                out['clx_theme_key'] = r
        line = [n for n in _top_line(rh, cl[0], cl[0] + 2 * m * stretch)]
        out['clx_open'] = len(line)
        out['clx_open_held'] = int(len(line) <= 2 or max((n[1] for n in line), default=0) >= 1.5 * m - 1e-6)
        out['clx_bars'] = int(round((cl[1] - cl[0]) / (m * stretch)))
        i = next(k for k, (n, a, z) in enumerate(secs) if n == 'climax')
        out['clx_nobuild'] = int(out['clx_bars'] <= 8 and not (i and secs[i - 1][0] == 'build'))
        end = secs[-1][2]
        out['tail_bars'] = int(round((end - cl[1]) / (m * stretch)))
        A = getattr(song, 'endless_arrangement', None)
        if A is not None and A.get(None, 'layout') == 'arch':
            out['arch_tail'] = out['tail_bars']
        jumps = 0
        grp = {}
        for n in rh:
            if cl[0] - 1e-6 <= n[0] < cl[1] - 1e-6:
                k_ = round(n[0], 2)
                grp[k_] = max(grp.get(k_, n), n, key=lambda x: x[2])
        ons = [o for o in sorted(grp.values())         # (an inner voice under a held higher note: the packets'
               if not any(n[0] < o[0] - 0.05 and n[0] + n[1] > o[0] + UNDER_HELD and n[2] >= o[2] + 3
                          for n in rh)]                # '(under)')
        for x, y in zip(ons, ons[1:]):
            jumps += y[0] - x[0] <= 0.5 + 1e-6 and abs(y[2] - x[2]) >= 17
        out['clx_jump'] = jumps

    def sounding(a, z):
        iv = sorted((max(a, n[0]), min(z, n[0] + n[1])) for n in rh if n[0] < z and n[0] + n[1] > a)
        tot, cur = 0.0, None
        for x, y in iv:
            if cur is None or x > cur[1]:
                tot += (cur[1] - cur[0]) if cur else 0.0
                cur = [x, y]
            else:
                cur[1] = max(cur[1], y)
        return tot + ((cur[1] - cur[0]) if cur else 0.0)
    hole = thin = empty = 0
    for n_, a, z in secs:
        if n_ in frames:
            continue
        nb = int(round((z - a) / m))
        for k in range(nb - 1):
            b0 = a + k * m - e_
            if n_ in ('build', 'climax'):
                ons = [n for n in rh if b0 <= n[0] < b0 + m]
                if not ons and not any(n[0] < b0 and n[0] + n[1] >= b0 + m / 2 for n in rh):
                    hole += 1
                thin += sounding(b0, b0 + m) < m / 2
            else:
                empty += sounding(b0, b0 + m) < m / 4
    out['bc_hole'], out['bc_thin'], out['ph_empty'] = hole, thin, empty
    As = [(a, z) for n, a, z in secs if n in ('A1', 'A2', 'A3', 'A4')]
    if As and lh:
        nb = sum((z - a) / m for a, z in As)
        dens = []
        for a, z in As:
            for k in range(int(round((z - a) / m))):
                dens.append(len({round(n[0], 2) for n in lh if a + k * m - 1e-6 <= n[0] < a + (k + 1) * m - 1e-6}))
        out['a_lh_den'] = round(sum(dens) / max(1, nb), 1)
        out['a_lh_busy'] = round(sum(d >= (12 if m == 4 else 9) for d in dens) / max(1, len(dens)), 2)
        bals = []
        for a, z in As:
            er = sum((n[3] / 127.0) ** 2.5 for n in rh if a - 1e-6 <= n[0] < z - 1e-6)
            el = sum((n[3] / 127.0) ** 2.5 for n in lh if a - 1e-6 <= n[0] < z - 1e-6)
            if er > 0 and el > 0:
                bals.append(10 * math.log10(er / el))
        if bals:
            out['a_bal'], out['a_bal_min'] = round(st.mean(bals), 2), round(min(bals), 2)
    a1s = next(((a, z) for n, a, z in secs if n == 'A1'), None)
    rets = [(a, z) for n, a, z in secs if n in ('A2', 'A3', 'A4')]
    if a1s and rets:
        def bar_top(a, k):
            return {(round(2 * (n[0] - a - k * m)), n[2]) for n in _top_line(rh, a + k * m - 0.1, a + (k + 1) * m - 0.1)}
        cp = 0
        for a, z in rets:
            cp += all(bar_top(a, k) and _jacc(bar_top(a, k), bar_top(a1s[0], k)) >= 0.7 for k in range(2 * stretch))
        out['ret_head_copy'] = round(cp / len(rets), 2)
    from agentsound.theory import chord as _ch
    best = best_r = 0
    for n_, a, z in secs:
        if n_ in frames:
            continue
        run, prev, run_r, prev_r = 0, None, 0, None
        for k in range(int(round((z - a) / m))):
            here = [s_ for t, b, s_ in tl if t < a + (k + 1) * m - 1e-6 and t + b > a + k * m + 1e-6]
            cur = here[0] if len(here) == 1 else None
            run = run + 1 if cur is not None and cur == prev else 1
            prev = cur
            best = max(best, run if cur is not None else 0)
            roots = {_ch(s_.split('/')[0]).root % 12 for s_ in here}
            cur_r = next(iter(roots)) if len(roots) == 1 else None
            run_r = run_r + 1 if cur_r is not None and cur_r == prev_r else 1
            prev_r = cur_r
            best_r = max(best_r, run_r if cur_r is not None else 0)
    out['chord_run'] = round(best / stretch, 1)
    out['root_run'] = round(best_r / stretch, 1)
    b1 = next(((a, z) for n, a, z in secs if n in ('B1', 'B')), None)
    if b1:
        from agentsound.theory import chord as _chord
        local = next((set(p) for a_, z_, p in reversed(keys) if a_ - 1e-6 <= b1[0] + m < z_), None) if keys else None
        minor = tune.key.split()[1] == 'minor'
        home = set(Key(tune.key).pcs)
        pcs = set(local) if local else home
        t_pc = Key(tune.key).tonic % 12
        if local and local != home:                    # (a B in another key: its tonic by the scale's mode)
            t_pc = next((t for t in range(12) if {(t + i) % 12 for i in ((0, 2, 3, 5, 7, 8, 10) if minor else
                                                                         (0, 2, 4, 5, 7, 9, 11))} == pcs), t_pc)
        allow = pcs | ({(t_pc + 11) % 12} if minor else set())
        syms = [s_ for t, b, s_ in tl if b1[0] - 1e-6 <= t < b1[1] - 1e-6]
        col = 0
        for s_ in syms:
            c = _chord(s_)
            tones = {(c.root + i) % 12 for i in c.intervals}
            dom = 4 in c.intervals and 10 in c.intervals
            col += bool(tones - allow) or (dom and (c.root - t_pc) % 12 != 7)
        out['b_color'] = int(col > 0)
        nb = int(round((b1[1] - b1[0]) / m))
        bars_ = [_chord_at(tl, b1[0] + k * m + 0.01) for k in range(nb)]
        w = 4 * stretch
        out['b_loop'] = int(any(bars_[k:k + w] == bars_[k + w:k + 2 * w] for k in range(0, nb - 2 * w + 1)))
    lone = 0
    for n in rh:
        if n[2] < 84 or (cl and cl[0] - 1e-6 <= n[0] < cl[1] - 1e-6) or n[0] >= secs[-1][1] - 1e-6:
            continue
        b0 = m * int((n[0] + e_) // m)
        if not any(x[0] < b0 + m - 1e-6 and x[0] + x[1] > b0 + 1e-6 for x in lh):
            lone += 1
    out['lone_hi'] = lone
    out['arrival'] = (getattr(tune, 'arrange', None) or {}).get('arrival')
    return out


def _sung_line(rh, a, z):
    """_top_line without the inner voices struck under a held higher right-hand note (the packets' '(under)')."""
    return [o for o in _top_line(rh, a, z)
            if not any(n[0] < o[0] - 0.05 and n[0] + n[1] > o[0] + UNDER_HELD and n[2] >= o[2] + 3 for n in rh)]


def contour_match(head, line, tol: float = 0.15, until: float | None = None) -> tuple:
    """How audibly `line` (the top line's notes) states `head` (the theme's head, its first two bars as composed) as
    a listener hears it (round g10: the g9 judges heard KVRY's / NMPC's climaxes as new tunes that head_match
    passed): from the head's FIRST note, in its own rhythm (each next head note found at its onset within `tol`
    beats; notes in between may only be short connecting notes, under a beat), each step in the same direction
    (a repeat stays a repeat) within a semitone of its size (a diatonic transposition). -> (the share of the head's
    steps matched before the first miss - the head's opening gesture first, its best start). until: the latest start
    (round g12: the climax OPENS with the head)."""
    hd = [n for n in sorted(head) if n[1] > FAST]
    ln = [n for n in line if n[1] > FAST]
    if len(hd) < 3 or len(ln) < 3:
        return 0.0, None
    best = (0.0, None)
    for i, x0 in enumerate(ln):
        if until is not None and x0[0] > until:
            break
        ok, j, prev = 0, i, (hd[0][2], x0[2])
        for h in hd[1:]:
            want = x0[0] + h[0] - hd[0][0]
            k = j + 1
            while k < len(ln) and ln[k][0] < want - tol and ln[k][1] <= 1.0 + 1e-6:
                k += 1                                 # (a connecting note between: skipped)
            if k >= len(ln) or abs(ln[k][0] - want) > tol:
                break
            d_h, d_l = h[2] - prev[0], ln[k][2] - prev[1]
            if (d_h > 0) != (d_l > 0) or (d_h < 0) != (d_l < 0) or abs(d_h - d_l) > 1:
                break
            ok, j, prev = ok + 1, k, (h[2], ln[k][2])
        r = round(ok / (len(hd) - 1), 2)
        if r > best[0]:
            best = (r, x0[0])
    return best


def head_cell(a1, meter: int) -> int:
    """A1's head has a repeated cell: one of its next bars (4/4: bars 2-4; a waltz's 8-bar phrase: bars 2-6) repeats
    bar 1's onset rhythm, as written or displaced by an 8th / a beat (Jaccard >= 0.75 on a 1/4-beat grid, 2+
    onsets)."""
    nb = 4 if meter == 4 else 6
    bars_ = [{round(4 * (n[0] - k * meter)) for n in a1 if k * meter - 1e-6 <= n[0] < (k + 1) * meter - 1e-6}
             for k in range(nb)]
    return int(len(bars_[0]) >= 2 and any(_jacc({x + d for x in bars_[0]}, y) >= 0.75 for y in bars_[1:]
                                          for d in (-4, -2, 0, 2, 4)))


G10_TELLS = ('clx_head', 'clx_head_pk', 'clx_head_ok', 'clx_kind_theme', 'clx_in', 'clx_in_v', 'post_jump',
             'pk_hammer', 'b1_lh_v90', 'clx_lh_vmax', 'b1_over_bld', 'clx_drop', 'clx_end_hole', 'clx_after_pk',
             'clx_rh_notes', 'post_head', 'head_cell')


def g10_tells(tune, song) -> dict:
    """The g9 judges' fixes measured (songs/_blind/ROUNDS.md "Round g9"; the melody is _top_line):
      clx_head      the climax states the head as heard: the best contour_match of A1's head (its first two bars as
                    composed) in the climax's top line (g9: KVRY's grown climax, NMPC's 'sequence' - "a new cell");
                    clx_head_pk the same within 2 bars of the climax's highest note; clx_head_ok: clx_head >= 0.8;
                    clx_kind_theme: the climax kind is the theme (not 'grow' / 'climb')
      clx_in        the climax's first 2 bars against the last 2 sounding bars before it (both hands' note energy per
                    beat, dB; g9: AHVN after its pause, KVRY's LH at v15 - "it enters under the build");
                    clx_in_v: the same for the right hand's mean velocity
      post_jump     after the climax: the largest rise of the right hand's mean velocity from a section's last 2
                    bars into the next section's first 2 (g9: KNUB's A2 / coda at v94-106 after a soft B2)
      pk_hammer     the longest run of climax bars whose loudest right-hand note is within 4 of the climax's loudest
                    (g9: NMPC v108-114 four bars)
      b1_lh_v90     the left hand's 90th-percentile velocity in B1; clx_lh_vmax: its loudest in the climax (g9: JRCY
                    v92-99 in B1, its bass octaves v102-106); b1_over_bld: B1's note energy per beat over the build's
                    (dB; g9: JRCY B1 +2.3 LU over the build's +1.0)
      clx_drop      the largest fall of the bar's highest top-line note from one bar to the next, from the climax's
                    peak bar to its last bar (semitones; g9: QKNJ A6 -> C#5 in one bar)
      clx_end_hole  the climax's last bar has no right-hand onset (g9: LMUP 48)
      clx_after_pk  the climax's bars after its peak bar (g9: FCJZ's waltz, six bars sagging)
      clx_rh_notes  the climax's right-hand notes a bar, chord notes included (g9: QKNJ 11.6, KNUB / JRCY 10+)
      post_head     the first A after the climax states the head (contour_match within its first 2 bars + a beat;
                    g9: FCJZ A2, JRCY A2 "without the head")
      head_cell     A1's head has a repeated cell (head_cell; g9: KVRY, AHVN, LMUP "no repeated cell")
    The sung line (clx_head, post_head) leaves out an inner voice struck under a held higher note (_sung_line)."""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    frames = ('intro', 'inter', 'coda', 'end')
    out = {}
    e_ = 0.12
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])
    head = [n for n in a1 if n[0] < 2 * tune.meter - 1e-6]

    def energy(a, z, hands=(rh, lh)):
        e = sum((n[3] / 127.0) ** 2.5 for h in hands for n in h if a - 1e-6 <= n[0] < z - 1e-6)
        return 10 * math.log10(e / max(1e-9, z - a)) if e > 0 else None

    def vmean(a, z):
        vs = [n[3] for n in _top_line(rh, a, z)]
        return st.mean(vs) if vs else None
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    if cl:
        a, z = cl
        nb = int(round((z - a) / m))
        line = _sung_line(rh, a, z)
        r, _ = contour_match(head, line)
        out['clx_head'], out['clx_head_ok'] = r, int(r >= 0.8)
        A = getattr(song, 'endless_arrangement', None)
        kind = A.get('climax', 'climax') if A is not None else None
        out['clx_kind_theme'] = int(kind in ('theme', 'step', 'lift'))
        if line:
            pk = max(line, key=lambda n: (n[2], -n[0]))
            out['clx_head_pk'] = contour_match(head, _sung_line(rh, pk[0] - 2 * m, pk[0] + 2 * m))[0]
            pb = int((pk[0] + e_ - a) // m)
            out['clx_after_pk'] = nb - 1 - pb
            his = []
            for k in range(pb, nb):
                ps = [n[2] for n in _top_line(rh, a + k * m - e_, a + (k + 1) * m - e_) if n[1] > FAST]
                if ps:
                    his.append(max(ps))
            out['clx_drop'] = max((x - y for x, y in zip(his, his[1:])), default=0)
        # (the last 2 bars before the climax that sound: a pause's silent bar skipped)
        b = a
        while b > m and energy(b - m, b) is None:
            b -= m
        e0, e1 = energy(b - 2 * m, b), energy(a, a + 2 * m)
        if e0 is not None and e1 is not None:
            out['clx_in'] = round(e1 - e0, 2)
        v0, v1 = vmean(b - 2 * m, b), vmean(a, a + 2 * m)
        if v0 is not None and v1 is not None:
            out['clx_in_v'] = round(v1 - v0, 1)
        vmax = max((n[3] for n in rh if a - e_ <= n[0] < z - e_), default=0)
        run = best = 0
        for k in range(nb):
            v = max((n[3] for n in rh if a + k * m - e_ <= n[0] < a + (k + 1) * m - e_), default=0)
            run = run + 1 if v >= vmax - 4 else 0
            best = max(best, run)
        out['pk_hammer'] = best
        out['clx_end_hole'] = int(not any(z - m - e_ <= n[0] < z - e_ for n in rh))
        out['clx_lh_vmax'] = max((n[3] for n in lh if a - e_ <= n[0] < z - e_), default=0)
        out['clx_rh_notes'] = round(sum(1 for n in rh if a - e_ <= n[0] < z - e_) / max(1, nb), 1)
        after = [(n_, a_, z_) for n_, a_, z_ in secs if a_ >= z - 1e-6]
        jumps = []
        prev = (z - 2 * m, z)
        for n_, a_, z_ in after:
            if n_ == 'end':
                continue
            v0, v1 = vmean(*prev), vmean(a_, min(z_, a_ + 2 * m))
            if v0 is not None and v1 is not None:
                jumps.append(v1 - v0)
            prev = (max(a_, z_ - 2 * m), z_)
        if jumps:
            out['post_jump'] = round(max(jumps), 1)
        post = next(((a_, z_) for n_, a_, z_ in after if n_ in ('A1', 'A2', 'A3', 'A4')), None)
        if post:
            out['post_head'] = int(contour_match(head, _sung_line(rh, post[0] - e_, post[0] + 2 * m + 1))[0] >= 0.8)
    b1 = next(((a, z) for n, a, z in secs if n in ('B1', 'B')), None)
    if b1 and lh:
        vs = sorted(n[3] for n in lh if b1[0] - e_ <= n[0] < b1[1] - e_)
        if vs:
            out['b1_lh_v90'] = vs[min(len(vs) - 1, int(0.9 * len(vs)))]
    bl = next(((a, z) for n, a, z in secs if n == 'build'), None)
    if b1 and bl:
        x, y = energy(*b1), energy(*bl)
        if x is not None and y is not None:
            out['b1_over_bld'] = round(x - y, 2)
    out['head_cell'] = head_cell(a1, tune.meter)
    return out


G11_TELLS = ('ret_bars_copy', 'ret_body_copy', 'ret_body_max', 'copy_bars', 'a_stmts', 'a4_long', 'minutes',
             'head_down', 'head_osc', 'head_cad', 'head_shape', 'bld_over_prev', 'bld_over_pre', 'bld_soft', 'bld_v_over', 'pre_top', 'pre_hi',
             'pre_vmax', 'pre_loud', 'clx_rh_empty', 'last_a_bars', 'last_a_home', 'last_a_ok', 'coda_bars',
             'coda_short', 'b1_rh_npb', 'bld_rh_npb', 'dense_bars', 'wz_bars', 'wz_long', 'clx_run', 'peak_pitch')


def g11_tells(tune, song) -> dict:
    """The g10 judges' fixes measured (songs/_blind/ROUNDS.md "Round g10"; the melody is _top_line):
      ret_bars_copy the share of the A returns' bars (A2-A4, every bar) whose top line (2+ onsets: a held landing
                    is no copy; exact pitches, 8th grid, Jaccard >= 0.7) copies a bar of an earlier A section at any
                    position; ret_body_copy the same
                    past each return's first 2 bars (the head), ret_body_max its largest per return; copy_bars the
                    number of such bars (g10: HJJR's four near-identical A statements, the statistician's counts in
                    HABQ / ZVNR / XWPQ / VBJZ; ret_head_copy compared heads only)
      a_stmts       the A statements; minutes the piece's length; a4_long: 4 A statements in over 4 minutes (HJJR)
      head_down / head_osc / head_cad / head_shape   A1's head as composed (composer.head_shape: downbeat arrivals,
                    no two-pitch oscillation, a chord-tone cadence by bar 4; all three; g10: VBJZ, VEAS, ELNQ)
      bld_over_prev the build's note energy per beat over the section before it (dB); bld_over_pre: over the loudest
                    part section before it, bld_soft: that under -0.5 (g10: XWPQ's build softer than A2); bld_v_over:
                    the build's mean top-line velocity over the loudest earlier part section's
      pre_top       the highest right-hand note before the build minus the climax's (semitones); pre_hi: >= 0 (g10:
                    CDSQ's B1 at F#6); pre_vmax the loudest right-hand note before the build minus the climax's;
                    pre_loud: within 6 (CDSQ's A2 at v105)
      clx_rh_empty  climax bars (its last form bar out) whose right hand sounds under a quarter of the bar (XWPQ bar 41)
      last_a_bars   the last A statement's bars; last_a_home: it closes on the tonic; last_a_ok: 8+ bars (a waltz
                    12+) and home (g10: ZVNR's / HABQ's 6-bar A3 without a home cadence)
      coda_bars     the coda's bars; coda_short: under 6 (VBJZ's 3-bar coda)
      b1_rh_npb / bld_rh_npb   B1's / the build's right-hand notes a bar; dense_bars: bars outside the climax with
                    12+ right-hand notes (3/4: 9+; g10: VEAS B1 11.9, ZVNR's build 9.7)
      wz_bars       a waltz's bars; wz_long: over 95 (ELNQ)
      clx_run       stock scale runs in the climax: 6+ right-hand notes of a quarter beat or less, each a step (1-2
                    semitones) the same way (VBJZ bar 36)
      peak_pitch    the highest right-hand note (the set: nine of eleven peaks on A6 / Ab6)"""
    m = int(song.beats_per_bar)
    stretch = 2 if m == 3 else 1
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes) if 'comp' in song.tracks else []
    secs = _sections(song)
    tl = song.endless_timeline
    e_ = 0.12
    out = {}

    def bar_top(a, k):
        return {(round(2 * (n[0] - a - k * m)), n[2]) for n in _top_line(rh, a + k * m - 0.1, a + (k + 1) * m - 0.1)}
    As = [(n, a, z) for n, a, z in secs if n in ('A1', 'A2', 'A3', 'A4')]
    out['a_stmts'] = len(As)
    end = secs[-1][2]
    out['minutes'] = round(end / float(song.tempo), 2)
    out['a4_long'] = int(len(As) >= 4 and out['minutes'] > 4.0)
    if len(As) > 1:
        seen, tot, cp, body, bcp, bmax = [], 0, 0, 0, 0, 0.0
        for j, (n_, a, z) in enumerate(As):
            nb = int(round((z - a) / m))
            bars_ = [bar_top(a, k) for k in range(nb)]
            if j:
                c_ = [len(b) >= 2 and any(_jacc(b, x) >= 0.7 for x in seen) for b in bars_]
                tot += nb
                cp += sum(c_)
                bc = c_[2 * stretch:]
                body += len(bc)
                bcp += sum(bc)
                if bc:
                    bmax = max(bmax, sum(bc) / len(bc))
            seen += [b for b in bars_ if b]
        out['ret_bars_copy'] = round(cp / max(1, tot), 3)
        out['ret_body_copy'] = round(bcp / max(1, body), 3)
        out['ret_body_max'] = round(bmax, 2)
        out['copy_bars'] = cp
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])
    from agentsound.endless.composer import Harm
    hs = composer.head_shape(a1, Harm(tune.changes[tune.parts[0]]), tune.meter)
    out['head_down'], out['head_osc'], out['head_cad'], out['head_shape'] = \
        int(hs['down']), int(hs['osc']), int(hs['cad']), int(hs['ok'])

    def energy(a, z):
        e = sum((n[3] / 127.0) ** 2.5 for h in (rh, lh) for n in h if a - 1e-6 <= n[0] < z - 1e-6)
        return 10 * math.log10(e / max(1e-9, z - a)) if e > 0 else None
    names = [n for n, _, _ in secs]
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    if 'build' in names:
        i = names.index('build')
        if i:
            x, y = energy(*secs[i][1:]), energy(*secs[i - 1][1:])
            if x is not None and y is not None:
                out['bld_over_prev'] = round(x - y, 2)
            es = [energy(a, z) for n, a, z in secs[:i] if n not in ('intro', 'inter')]
            es = [e for e in es if e is not None]
            if x is not None and es:
                out['bld_over_pre'] = round(x - max(es), 2)
                out['bld_soft'] = int(x - max(es) < -0.5)
            vb = [n[3] for n in _top_line(rh, *secs[i][1:])]
            vp = [st.mean(v) for v in ([n[3] for n in _top_line(rh, a, z)] for n, a, z in secs[:i]
                                      if n not in ('intro', 'inter')) if v]
            if vb and vp:
                out['bld_v_over'] = round(st.mean(vb) - max(vp), 1)
    if cl:
        pre_end = next((a for n, a, z in secs if n == 'build'), cl[0])
        pre = [n for n in rh if n[0] < pre_end - e_]
        inn = [n for n in rh if cl[0] - e_ <= n[0] < cl[1] - e_]
        if pre and inn:
            out['pre_top'] = max(n[2] for n in pre) - max(n[2] for n in inn)
            out['pre_hi'] = int(out['pre_top'] >= 0)
            out['pre_vmax'] = max(n[3] for n in pre) - max(n[3] for n in inn)
            out['pre_loud'] = int(out['pre_vmax'] > -6)

        def sounding(a, z):
            return sum(min(z, n[0] + n[1]) - max(a, n[0]) for n in _merge(rh, a, z))
        nb = int(round((cl[1] - cl[0]) / m))
        out['clx_rh_empty'] = sum(sounding(cl[0] + k * m - e_, cl[0] + (k + 1) * m - e_) < m / 4
                                  for k in range(nb - stretch))
        run, best, prev = 0, 0, None
        for n in rh:
            if not (cl[0] - e_ <= n[0] < cl[1] - e_) or n[1] > 0.26:
                continue
            if prev is not None and 0 < n[0] - prev[0] <= 0.26 and 1 <= abs(n[2] - prev[2]) <= 2 and \
                    (run < 2 or (n[2] > prev[2]) == up):
                up = n[2] > prev[2]
                run += 1
            else:
                run = 1
            best = max(best, run)
            prev = n
        out['clx_run'] = int(best >= 6)
    if As:
        n_, a, z = As[-1]
        out['last_a_bars'] = int(round((z - a) / m))
        last = _chord_at(tl, z - 0.01)
        from agentsound.theory import chord as _ch
        t_pc = Key(tune.key).tonic % 12
        out['last_a_home'] = int(bool(last) and _ch(last.split('/')[0]).root % 12 == t_pc)
        out['last_a_ok'] = int(out['last_a_bars'] >= (8 if m == 4 else 12) and out['last_a_home'])
    coda = next(((a, z) for n, a, z in secs if n == 'coda'), None)
    if coda:
        out['coda_bars'] = int(round((coda[1] - coda[0]) / m))
        out['coda_short'] = int(out['coda_bars'] < 6)

    def npb(a, z):
        return round(sum(1 for n in rh if a - e_ <= n[0] < z - e_) / max(1, (z - a) / m), 1)
    for nm, key_ in (('B1', 'b1_rh_npb'), ('build', 'bld_rh_npb')):
        s_ = next(((a, z) for n, a, z in secs if n == nm), None)
        if s_:
            out[key_] = npb(*s_)
    dense = 0
    for n_, a, z in secs:
        if n_ == 'climax':
            continue
        for k in range(int(round((z - a) / m))):
            dense += sum(1 for n in rh if a + k * m - e_ <= n[0] < a + (k + 1) * m - e_) >= (12 if m == 4 else 9)
    out['dense_bars'] = dense
    if m == 3:
        out['wz_bars'] = int(round(end / m))
        out['wz_long'] = int(out['wz_bars'] > 95)
    out['peak_pitch'] = max((n[2] for n in rh), default=0)
    return out


G12_TELLS = ('clx4_head', 'clx4_rhy', 'clx4_reg', 'clx4_ok', 'clx_dip', 'clx_rise2', 'clx_in_v0', 'peak_a6',
             'peak_over', 'clx_c5c6', 'coda_copy', 'coda_copy_bars', 'head_rate', 'head_sl', 'head_rhy_ok',
             'b1_reg', 'b1_rate', 'b1_chords', 'b1_seesaw', 'b1_cell', 'b1_held', 'b1_contrast', 'b1_ok', 'pk_tail',
             'tail_long', 'inner_only')


def g12_tells(tune, song) -> dict:
    """The g11 judges' fixes measured (songs/_blind/ROUNDS.md "Round g11"; the melody is _sung_line):
      clx4_head     the climax OPENS with the head: contour_match of A1's head in the climax's first 4 bars, starting
                    in its first bar, each note within a quarter beat of its place (the climax's agogic accents;
                    clx_head passed PTCV / KTGG / ERDL / NKTZ: its window took any place);
                    clx4_rhy the head's onset rhythm there (1/4-beat grid, Jaccard: added fills break it); clx4_reg
                    the stated head's mean pitch over A1's head's (semitones: PTCV's head moved down into C, G4-E5);
                    clx4_ok: >= 0.8, rhythm >= 0.6, register >= -2
      clx_dip       the climax's largest sag of a bar's mean melody velocity under the loudest bar before it, up to
                    its peak bar (LESU v82 -> v47-60); clx_rise2 the largest rise of a bar's loudest melody note over
                    one or two bars, inside the climax up to its peak bar (KTGG v93 -> v120); clx_in_v0: the
                    climax's first bar's mean melody velocity over the last 2 sounding bars before it (PTCV v54)
      peak_a6       the highest right-hand note at Ab6 / A6+ (four g11 pieces at A6); peak_over: over F6 (the user's
                    "too many very high notes": the cap); clx_c5c6: the climax's sung notes in C5-B5 (clx_c6: C6+)
      coda_copy     the coda's bars whose top line copies a bar of an A statement (ret_bars_copy's measure; the g11
                    statistician: every coda copies A1's bars 3-8); coda_copy_bars their number
      head_rate     A1's head as composed: onsets a bar over its first 4 bars; head_sl: a short-long pair (a note of
                    a beat or less, then one at least twice as long, joined) in its first 2 bars; head_rhy_ok: rate >=
                    2.5 (3/4: 2.0) and a short-long pair (KTGG's waltz head: three half notes, 1.9 a bar)
      b1_reg        B1's sung mean pitch over A1's; b1_rate its onsets a bar / A1's; b1_chords the share of its bars
                    whose chord A1 plays too; b1_seesaw its longest X Y X Y chord run (bars); b1_cell: B1 restates its
                    first bar's rhythm (head_cell: a hook of its own); b1_held the share of its sung notes of 2+ beats;
                    b1_contrast: register 3+ semitones off, or the pace 25 % off; b1_ok: that, no 4-bar seesaw and
                    under a fifth of held notes (WNTP / NKTZ / CNWE: B in A's register and chords, long notes over a
                    two-chord seesaw)
      pk_tail       bars after the highest note's bar; tail_long: an early peak (before 62 % of the piece) with over 16
                    bars after it (3/4: 24) - WNTP's 19 bars after its peak at 59 %
      inner_only    bars (the frames out) whose right hand strikes only inner voices under a held note (LESU 49,
                    PTCV 32, WNTP 20, KTGG 18, BFHK 53)"""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    secs = _sections(song)
    tl = song.endless_timeline
    e_ = 0.12
    out = {}
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])
    head = [n for n in a1 if n[0] < 2 * tune.meter - 1e-6 and n[1] > FAST]
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)

    def bar_v(a, k, f=st.mean):
        vs = [n[3] for n in _sung_line(rh, a + k * m - e_, a + (k + 1) * m - e_)]
        return f(vs) if vs else None
    if cl and len(head) >= 3:
        a, z = cl
        nb = int(round((z - a) / m))
        line = _sung_line(rh, a - e_, min(z, a + 4 * m) - e_)
        r, s0 = contour_match(head, line, tol=0.25, until=a + m - e_)     # (an agogic accent: a note late)
        out['clx4_head'] = r
        if s0 is not None:
            span = 2 * tune.meter
            h0 = head[0][0]
            ho = {round(4 * (n[0] - h0)) for n in head}
            seg = [x for x in line if s0 - 1e-6 <= x[0] < s0 + span - 0.1]
            out['clx4_rhy'] = round(_jacc(ho, {round(4 * (x[0] - s0)) for x in seg}), 2)
            out['clx4_reg'] = round(st.mean(x[2] for x in seg) - st.mean(n[2] for n in head), 1)
        out['clx4_ok'] = int(r >= 0.8 and out.get('clx4_rhy', 0) >= 0.6 and out.get('clx4_reg', -99) >= -2)
        sung = _sung_line(rh, a - e_, z - e_)
        if sung:
            pk = max(sung, key=lambda n: (n[2], -n[0]))
            pb = max(0, int((pk[0] + e_ - a) // m))
            vs = [bar_v(a, k) for k in range(pb + 1)]
            dip, hi_ = 0.0, None
            for v in vs:
                if v is None:
                    continue
                if hi_ is not None:
                    dip = max(dip, hi_ - v)
                hi_ = v if hi_ is None else max(hi_, v)
            out['clx_dip'] = round(dip, 1)
            b = a
            while b > m and not _sung_line(rh, b - m - e_, b - e_):
                b -= m
            mx = [bar_v(a, k, max) for k in range(pb + 1)]
            rises = [mx[k + j] - mx[k] for k in range(len(mx)) for j in (1, 2)
                     if k + j < len(mx) and mx[k] is not None and mx[k + j] is not None]
            out['clx_rise2'] = max(rises, default=0)
            v0, pv = bar_v(a, 0), [x for x in (bar_v(b - 2 * m, k) for k in range(2)) if x is not None]
            if v0 is not None and pv:
                out['clx_in_v0'] = round(v0 - st.mean(pv), 1)
            ps = [n[2] for n in sung]
            out['clx_c5c6'] = round(sum(72 <= p < 84 for p in ps) / len(ps), 2)
    top = max((n[2] for n in rh), default=0)
    out['peak_a6'] = int(top >= 92)
    out['peak_over'] = int(top > 89)

    def bar_top(a, k):
        return {(round(2 * (n[0] - a - k * m)), n[2]) for n in _top_line(rh, a + k * m - 0.1, a + (k + 1) * m - 0.1)}
    As = [(n, a, z) for n, a, z in secs if n in ('A1', 'A2', 'A3', 'A4')]
    seen = [b for n, a, z in As for b in (bar_top(a, k) for k in range(int(round((z - a) / m)))) if len(b) >= 2]
    coda = next(((a, z) for n, a, z in secs if n == 'coda'), None)
    if coda and seen:
        bs = [bar_top(coda[0], k) for k in range(int(round((coda[1] - coda[0]) / m)))]
        c_ = [len(b) >= 2 and any(_jacc(b, x) >= 0.7 for x in seen) for b in bs]
        out['coda_copy_bars'] = sum(c_)
        out['coda_copy'] = round(sum(c_) / max(1, len(c_)), 2)
    mt = tune.meter
    h4 = [n for n in a1 if n[0] < 4 * mt - 1e-6]
    out['head_rate'] = round(len(h4) / 4, 2)
    h2 = [n for n in a1 if n[0] < 2 * mt - 1e-6]
    out['head_sl'] = int(any(x[1] <= 1.0 + 1e-6 and y[1] >= 2 * x[1] - 1e-6 and abs(y[0] - x[0] - x[1]) < 0.05
                             for x, y in zip(h2, h2[1:])))
    out['head_rhy_ok'] = int(out['head_rate'] >= (2.5 if mt == 4 else 2.0) and out['head_sl'])
    b1 = next(((a, z) for n, a, z in secs if n in ('B1', 'B')), None)
    s_a1 = next(((a, z) for n, a, z in secs if n == 'A1'), None)
    if b1 and s_a1:
        lb, la = _sung_line(rh, b1[0] - e_, b1[1] - e_), _sung_line(rh, s_a1[0] - e_, s_a1[1] - e_)
        nbb, nba = max(1, (b1[1] - b1[0]) / m), max(1, (s_a1[1] - s_a1[0]) / m)
        if lb and la:
            out['b1_reg'] = round(st.mean(n[2] for n in lb) - st.mean(n[2] for n in la), 1)
            out['b1_rate'] = round((len(lb) / nbb) / (len(la) / nba), 2)
            out['b1_held'] = round(sum(n[1] >= 2 - 1e-6 for n in lb) / len(lb), 2)

        def bar_chords(a, z):
            return [_chord_at(tl, a + k * m + 1e-3) for k in range(int(round((z - a) / m)))]
        cb, ca = bar_chords(*b1), set(bar_chords(*s_a1))
        cb = [c for c in cb if c]
        if cb:
            out['b1_chords'] = round(sum(c in ca for c in cb) / len(cb), 2)
            run = best = 1
            for i in range(2, len(cb)):
                run = run + 1 if cb[i] == cb[i - 2] and cb[i] != cb[i - 1] else 1
                best = max(best, run)
            out['b1_seesaw'] = best + 1 if best > 1 else 0
        bmel = sorted(tune.melody.get(tune.parts[1]) or []) if len(tune.parts) > 1 else []
        out['b1_cell'] = head_cell(bmel, tune.meter) if bmel else 0
        if 'b1_reg' in out:
            out['b1_contrast'] = int(abs(out['b1_reg']) >= 3 or not 0.75 <= out['b1_rate'] <= 1.33)
            out['b1_ok'] = int(out['b1_contrast'] and out.get('b1_seesaw', 0) < 4 and out['b1_held'] < 0.2)
    body = [n for n in rh if n[0] < secs[-1][2] - 1e-6]
    if body:
        tp = max(body, key=lambda n: (n[2], -n[0]))
        out['pk_tail'] = int(round(secs[-1][2] / m)) - int(tp[0] // m) - 1
        out['tail_long'] = int(tp[0] / secs[-1][2] < 0.62 and out['pk_tail'] > (16 if m == 4 else 24))
    io = 0
    for n_, a, z in secs:
        if n_ in ('intro', 'end'):
            continue
        for k in range(int(round((z - a) / m))):
            b0 = a + k * m
            tops = _top_line(rh, b0 - e_, b0 + m - e_)
            if tops and not _sung_line(rh, b0 - e_, b0 + m - e_):
                io += 1
    out['inner_only'] = io
    return out


G13_TELLS = ('clx4_deg', 'clx4_dreg', 'clx4_own', 'clx_a1_cont', 'clx_a1_copy', 'clx_new2', 'head_circle',
             'head_circ_ok', 'ans_rhy', 'ans_ok', 'b1_rhy_j', 'b1_rhy_own', 'b1_hook', 'ret_h2_copy', 'clx_holes',
             'chrom_leap', 'coda_len')
G14_TELLS = ('clx_open_copy', 'clx_open_ch', 'clx_open_oct', 'flick_land', 'stab_bars', 'hole_bars', 'pay_hole',
             'clx_exit_bare', 'bars', 'waltz_bars', 'clx_static', 'coda_share', 'post_peak', 'head_circle8',
             'head_circ8_ok', 'under_n', 'under_a1', 'under_off', 'under_clash', 'under_loud')


def g14_tells(tune, song) -> dict:
    """The g13 judges' fixes measured (songs/_blind/ROUNDS.md "Round g13"):
      clx_open_copy  the climax's first unit A1's first unit replayed: its top line at A1's pitches (8th grid, Jaccard
                     >= 0.6) over A1's chords (clx_open_ch: the share of its beats on A1's chord there, roots) in A1's
                     register (clx_open_oct: the register moved an octave+) - "A1 replayed louder" (MYUS 5, GALR 4)
      flick_land     right-hand runs of 3+ top notes <= 0.17 beat leading straight into a note held 1.5+ beats (a turn
                     into a phrase's landing: GALR 13-14, MYUS 7-8, all seven judges - "a 32nd flick, a stab")
      stab_bars      bars in a part section whose right-hand onsets (a downbeat struck 0.1 early counts there) are all
                     <= 0.12 beat, and none of them a downbeat note held on (the packets' "0.08-beat stab")
      hole_bars      bars inside a part section (its last bar out) with no right-hand onset over 1/3 beat and less
                     than half the bar sounding (an empty bar after a phrase end)
      pay_hole       the motto payoff's last note held into a bar with no other right-hand onset before its beat 3
                     (TCMN 38, four judges)
      clx_exit_bare  the climax's last bar with one left-hand attack and at most one right-hand onset (CNCJ 46, six)
      bars / waltz_bars / clx_static / coda_share / post_peak   the length (a waltz's in 3/4 bars: PPHK 93, all
                     seven), the climax's longest run of bars on one chord (PPHK's F#add9 x4), the coda's share of
                     the piece, the bars after the highest note
      head_circle8   A1's first 8 bars of a waltz: the most notes in one 3-semitone window, share (PPHK's head, all
                     seven: the 4/4 check skipped 3/4); head_circ8_ok <= 0.5
      under_n        right-hand notes struck under a higher right-hand note still held UNDER_HELD beats past them (the
                     packets' '(under)'; the statistician: 8+ a generated piece, 0 in the references); under_a1 those
                     in A1; under_off those outside the local chord scale (MYUS's Bb4 under Cadd9); under_clash a
                     semitone / major 7th / minor 9th from the held note; under_loud at the held note's velocity - 4
                     or louder"""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    lh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['comp']._notes)
    secs = _sections(song)
    tl = song.endless_timeline
    out = {}
    mt = tune.meter
    U = 2 * m
    total = secs[-1][2]
    nb = int(round(total / m))
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    s_a1 = next(((a, z) for n, a, z in secs if n == 'A1'), None)

    def top8(x0, x1):
        return {(round(2 * (n[0] - x0)), n[2]) for n in _top_line(rh, x0 - 0.1, x1 - 0.1)}

    def root_at(t):
        sym = _chord_at(tl, t)
        if not sym:
            return None
        from agentsound.theory import chord as _ch
        return _ch(sym.split('/')[0]).root % 12
    if cl and s_a1 and cl[1] - cl[0] >= U:
        a, z = cl
        cp = _jacc(top8(a, a + U), top8(s_a1[0], s_a1[0] + U))
        same = sum(root_at(a + k + 0.05) == root_at(s_a1[0] + k + 0.05) for k in range(U)) / U
        l0, l1 = _top_line(rh, a - 0.1, a + U - 0.1), _top_line(rh, s_a1[0] - 0.1, s_a1[0] + U - 0.1)
        oc = int(bool(l0 and l1) and st.mean(n[2] for n in l0) - st.mean(n[2] for n in l1) >= 9)
        out['clx_open_ch'] = round(same, 2)
        out['clx_open_oct'] = oc
        out['clx_open_copy'] = int(cp >= 0.6 and same >= 0.75 and not oc)
    parts = [(n, a, z) for n, a, z in secs if n not in ('intro', 'end', 'coda')]
    # flick into a landing
    line = []
    for n in sorted(rh, key=lambda n: (n[0], -n[2])):
        if line and abs(n[0] - line[-1][0]) < 0.05:
            continue
        line.append(n)
    fl = 0
    for i in range(len(line) - 3):
        run = line[i:i + 3]
        if all(x[1] <= 0.18 for x in run) and all(0 < y[0] - x[0] <= 0.2 for x, y in zip(run, run[1:] + [line[i + 3]])):
            nxt = next((y for y in line[i + 3:i + 6] if y[1] > 0.18), None)
            if nxt is not None and nxt[1] >= 1.5 - 1e-6 and nxt[0] - run[-1][0] <= 0.4 and \
                    (i == 0 or line[i - 1][1] > 0.18 or line[i][0] - line[i - 1][0] > 0.25):
                fl += 1
    out['flick_land'] = fl

    def bar_of(t):
        return int((t + 0.1) // m)
    stab = hole = 0
    for name, a, z in parts:
        for b in range(int(round(a / m)), int(round(z / m)) - 1):
            ons = [n for n in rh if bar_of(n[0]) == b]
            b0 = b * m
            if ons and all(n[1] <= 0.12 + 1e-6 for n in ons) and \
                    not any(n[0] < b0 - 0.1 and n[0] + n[1] >= b0 + 0.5 * m for n in rh):
                stab += 1
            if not any(n[1] > FAST for n in ons):
                cover = sum(max(0.0, min(n[0] + n[1], b0 + m) - max(n[0], b0)) for n in _merge_spans(rh, b0, b0 + m))
                if cover < 0.5 * m:
                    hole += 1
    out['stab_bars'] = stab
    out['hole_bars'] = hole
    ph = 0
    for d in (getattr(song, 'endless_signature', None) or {}).get('statements') or ():
        if d.get('move') != 'motto' or str(d.get('role')) != 'payoff':
            continue
        if not d.get('notes'):
            continue
        st0, du0, p0 = max(d['notes'])
        k = int((st0 + 0.1) // m) + 1                  # (the bar the payoff's last note is held into)
        if st0 + du0 >= k * m + 1.0:
            ph += not any(k * m - 0.1 <= n[0] < k * m + 2 - 1e-6 and n[1] > FAST for n in rh)
    out['pay_hole'] = ph
    if cl:
        b = int(round(cl[1] / m)) - 1
        la = len({round(n[0], 2) for n in lh if bar_of(n[0]) == b})
        ra = len({round(n[0], 1) for n in rh if bar_of(n[0]) == b and n[1] > FAST})
        out['clx_exit_bare'] = int(la <= 1 and ra <= 1)
        run = best = 0
        prev = None
        for k in range(int(round(cl[0] / m)), int(round(cl[1] / m))):
            syms = {s for t0, bb, s in tl if t0 < (k + 1) * m - 1e-6 and t0 + bb > k * m + 1e-6}
            cur = next(iter(syms)) if len(syms) == 1 else None
            run = run + 1 if cur is not None and cur == prev else 1
            prev = cur
            best = max(best, run)
        out['clx_static'] = best
    out['bars'] = nb
    if mt == 3:
        out['waltz_bars'] = nb
    coda = next(((a, z) for n, a, z in secs if n == 'coda'), None)
    if coda:
        out['coda_share'] = round((coda[1] - coda[0]) / total, 3)
    pk = max(rh, key=lambda n: (n[2], -n[0])) if rh else None
    if pk:
        out['post_peak'] = nb - bar_of(pk[0]) - 1
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])
    if mt == 3:
        h8 = [n[2] for n in a1 if n[0] < 8 * mt - 1e-6]
        if h8:
            out['head_circle8'] = round(max(sum(p <= x <= p + 3 for x in h8) for p in h8) / len(h8), 2)
            out['head_circ8_ok'] = int(out['head_circle8'] <= 0.6 + 1e-6)
    spans = [(a, z, RaisedPcs(p)) for a, z, p in getattr(song, 'endless_keys', None) or
             [(0, 1e9, sorted(set(Key(tune.key).pcs)))]]
    un = ua1 = off = clash = loud = 0
    for x in rh:
        held = [n for n in rh if n[0] < x[0] - 0.05 and n[0] + n[1] > x[0] + UNDER_HELD and n[2] >= x[2] + 3]
        if not held:
            continue
        h = max(held, key=lambda n: n[2])
        un += 1
        ua1 += bool(s_a1 and s_a1[0] - 1e-6 <= x[0] < s_a1[1] - 1e-6)
        sym = _chord_at(tl, x[0] + 0.06)
        if sym and x[2] % 12 not in _local_scale(spans, x[0] + 0.06, sym):
            off += 1
        clash += (h[2] - x[2]) % 12 in (1, 11)
        loud += x[3] >= h[3] - 4
    out.update(under_n=un, under_a1=ua1, under_off=off, under_clash=clash, under_loud=loud)
    return out


def _merge_spans(rh, a, z):
    """The right hand's notes sounding in [a, z), merged into spans (start, dur) - _merge's tuples as notes."""
    return [(x, d) for x, d in _merge(rh, a, z)]


def g13_tells(tune, song) -> dict:
    """The g12 judges' fixes measured (songs/_blind/ROUNDS.md "Round g12"; the melody is _sung_line):
      clx4_deg      the climax's head at its OWN degrees: the head's notes found at their onsets (from clx4's start,
                    within a quarter beat) whose pitch class is A1's head's, moved by 0 or a whole step (the sung keys:
                    perform.SUNG_KEYS) - the best of the two (ZSTD: the head a 4th up after a key move to IV, heard
                    as new melody, passed clx4_head's contour); clx4_dreg their mean pitch over the head's; clx4_own:
                    deg >= 0.75 and the register within 3 semitones
      clx_a1_cont   "A1 replayed louder" (VQXW five judges, EXWH / ZEFU two): the climax's second unit (its bars 3-4)
                    states A1's second unit's contour (contour_match >= 0.8, any transposition); clx_a1_copy: at A1's
                    pitches (the top lines' 8th grid, Jaccard >= 0.6); clx_new2: neither
      head_circle   A1's first 4 bars (as composed): the most notes in one 2-semitone window, share (VYDA 0.58 on
                    C#5-D#5; GZAT 0.50, EXWH 0.40); head_circ_ok: <= 0.5 (a waltz: not checked)
      ans_rhy       A1's third unit (the consequent's first: its 'develop' phrase) against the head's onsets
                    (8th grid, Jaccard; JQTJ's displaced answer 0.20); ans_ok: >= 0.5
      b1_rhy_j      B1's first unit's onsets (as composed: the tune's B part) against A1's head's (8th grid, Jaccard); b1_rhy_own <= 0.5;
                    b1_hook: that, its first bar's rhythm restated in B (b1_cell) and its register or pace apart
                    (b1_contrast)
      ret_h2_copy   the share of the A returns whose head's SECOND bar copies A1's (top lines, 8th grid, Jaccard >=
                    0.7; VQXW's four identical heads, the statistician)
      clx_holes     climax bars (its last, the held landing, out) with no right-hand onset (VYDA 38, all seven judges)
      chrom_leap    right-hand top notes outside the local chord scale (_local_scale), a quarter+ long, leapt to (3+
                    semitones from the note before) or not resolved by a step (JQTJ's Eb5-Gb5-G5)
      coda_len      the coda's bars (the statistician: seven 7-bar codas)"""
    m = int(song.beats_per_bar)
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    secs = _sections(song)
    tl = song.endless_timeline
    e_ = 0.12
    out = {}
    mt = tune.meter
    U = 2 * mt
    a1 = sorted(tune.melody.get(tune.parts[0]) or [])
    head = [n for n in a1 if n[0] < U - 1e-6 and n[1] > FAST]
    cl = next(((a, z) for n, a, z in secs if n == 'climax'), None)
    s_a1 = next(((a, z) for n, a, z in secs if n == 'A1'), None)
    if cl and len(head) >= 3:
        a, z = cl
        line = _sung_line(rh, a - e_, min(z, a + 4 * m) - e_)
        r, s0 = contour_match(head, line, tol=0.25, until=a + m - e_)
        if s0 is not None:
            h0 = head[0][0]
            found = []
            for h in head:
                want = s0 + h[0] - h0
                x = min(line, key=lambda n: abs(n[0] - want))
                if abs(x[0] - want) <= 0.25:
                    found.append((h[2], x[2]))
            if found:
                out['clx4_deg'] = round(max(sum((y - x - d) % 12 == 0 for x, y in found) for d in (0, 2))
                                        / len(head), 2)
                out['clx4_dreg'] = round(st.mean(y - x for x, y in found), 1)
        out['clx4_own'] = int(out.get('clx4_deg', 0) >= 0.75 and abs(out.get('clx4_dreg', 99)) <= 3)
        u1 = [(st_ - U, du, p) for st_, du, p in a1 if U - 1e-6 <= st_ < 2 * U - 1e-6 and du > FAST]
        if len(u1) >= 3 and z - a >= 2 * U - 1e-6:
            l2 = _sung_line(rh, a + U - e_, a + 2 * U - e_)
            r2, _ = contour_match(u1, l2, tol=0.25, until=a + U + mt - e_)
            out['clx_a1_cont'] = int(r2 >= 0.8)
            if s_a1:
                def top8(x0, x1):
                    return {(round(2 * (n[0] - x0)), n[2]) for n in _top_line(rh, x0 - 0.1, x1 - 0.1)}
                cp = _jacc(top8(a + U, a + 2 * U), top8(s_a1[0] + U, s_a1[0] + 2 * U))
                out['clx_a1_copy'] = int(cp >= 0.6)
            out['clx_new2'] = int(not out['clx_a1_cont'] and not out.get('clx_a1_copy', 0))
        holes = 0
        for k in range(int(round((z - a) / m)) - 1):  # (its last bar: the held landing)
            b0 = a + k * m
            holes += not any(b0 - 0.25 <= n[0] < b0 + m - 0.25 for n in rh if n[1] > FAST and n[2] >= 60)
        out['clx_holes'] = holes
    h4 = [n[2] for n in a1 if n[0] < 4 * mt - 1e-6]
    if h4:
        out['head_circle'] = round(max(sum(p <= x <= p + 2 for x in h4) for p in h4) / len(h4), 2)
        out['head_circ_ok'] = int(out['head_circle'] <= 0.5 + 1e-6 or mt == 3)    # (composer.HEAD_PROFILE 'circle')

    def ons(ns, t0):
        return {round(2 * (n[0] - t0)) for n in ns}
    u0 = [n for n in a1 if n[0] < U - 1e-6]
    u2 = [n for n in a1 if 2 * U - 1e-6 <= n[0] < 3 * U - 1e-6]
    if u0 and u2:
        out['ans_rhy'] = round(_jacc(ons(u0, 0), ons(u2, 2 * U)), 2)
        out['ans_ok'] = int(out['ans_rhy'] >= 0.5)
    bp = next((p for p in tune.parts if p.startswith('B')), None)    # (g12_tells' b1_cell read parts[1]: A2 in a
    bmel = sorted(tune.melody.get(bp) or []) if bp else []            # verse form)
    b0_ = [n for n in bmel if n[0] < U - 1e-6]
    if b0_ and u0:
        out['b1_rhy_j'] = round(_jacc(ons(b0_, 0), ons(u0, 0)), 2)
        out['b1_rhy_own'] = int(out['b1_rhy_j'] <= 0.5)
        out['b1_hook'] = int(out['b1_rhy_own'] and head_cell(bmel, mt) and g12_tells(tune, song).get('b1_contrast', 0))
    if s_a1:
        def top8b(x0):
            return {(round(2 * (n[0] - x0)), n[2]) for n in _top_line(rh, x0 - 0.1, x0 + m - 0.1)}
        ref = top8b(s_a1[0] + m)
        rets = [a for n, a, z in secs if n in ('A2', 'A3', 'A4')]
        if rets and len(ref) >= 2:
            out['ret_h2_copy'] = round(sum(_jacc(top8b(a + m), ref) >= 0.7 for a in rets) / len(rets), 2)
    spans = [(a, z, RaisedPcs(p)) for a, z, p in getattr(song, 'endless_keys', None) or
             [(0, 1e9, sorted(set(Key(tune.key).pcs)))]]
    bad = 0
    for name, a, z in secs:
        if name in ('intro', 'end'):
            continue
        ln = _sung_line(rh, a - e_, z - e_)
        for i, n in enumerate(ln):
            sym = _chord_at(tl, n[0] + 0.06)
            if not sym or n[1] < 0.25 or n[2] % 12 in _local_scale(spans, n[0] + 0.06, sym):
                continue
            prv = ln[i - 1] if i else None
            nxt = ln[i + 1] if i + 1 < len(ln) else None
            bad += (prv is not None and abs(n[2] - prv[2]) >= 3) or nxt is None or abs(nxt[2] - n[2]) > 2
    out['chrom_leap'] = bad
    coda = next(((a, z) for n, a, z in secs if n == 'coda'), None)
    if coda:
        out['coda_len'] = int(round((coda[1] - coda[0]) / m))
    return out


def _merge(rh, a, z):
    """The right hand's sounding spans clipped to [a, z), merged: [(start, dur)]."""
    iv = sorted((max(a, n[0]), min(z, n[0] + n[1])) for n in rh if n[0] < z and n[0] + n[1] > a)
    out = []
    for x, y in iv:
        if out and x <= out[-1][1]:
            out[-1][1] = max(out[-1][1], y)
        else:
            out.append([x, y])
    return [(x, y - x) for x, y in out]


def _deg(sym: str, t_pc: int) -> str:
    """A chord symbol as its degree over the tonic + its quality (a slash bass dropped): Eb7 in C -> '3:7'."""
    from agentsound.theory import chord as _chord
    head = sym.split('/')[0]
    m_ = re.match(r'^([A-G][b#]?)(.*)$', head)
    return f"{(_chord(head).root - t_pc) % 12}:{m_.group(2) if m_ else ''}"


def routes(song, tonic_pc: int, n: int) -> set:
    """The chord routes of n chords (degrees, consecutive repeats merged) over the piece's body (the end chord out)."""
    ds = []
    for _, _, sym in song.endless_timeline[:-1]:
        d = _deg(sym, tonic_pc)
        if not ds or ds[-1] != d:
            ds.append(d)
    return {tuple(ds[i:i + n]) for i in range(len(ds) - n + 1)}


def form_tells(tune, song) -> dict:
    """The g2 set-level tells of one piece (the module docstring)."""
    m = int(song.beats_per_bar)
    stretch = 2 if m == 3 else 1
    rh = sorted((n.start, n.dur, n.pitch, n.vel) for n in song.tracks['piano']._notes)
    tl = song.endless_timeline
    secs = _sections(song)
    total = secs[-1][2]
    t_pc = Key(tune.key).tonic % 12
    out = {}
    A = getattr(song, 'endless_arrangement', None)
    out['layout'] = A.get(None, 'layout') if A is not None else None
    body = [n for n in rh if n[0] < total - 1e-6]
    top = max(body, key=lambda n: (n[2], -n[0]))
    out['top_at'] = round(top[0] / total, 3)
    parts = [(n_, a, z) for n_, a, z in secs if n_ not in ('intro', 'inter', 'coda')]
    lens = [round((z - a) / (m * stretch), 1) for _, a, z in parts]
    out['lens'] = ' '.join(f"{x:g}" for x in lens)
    out['grid8'] = round(sum(7.9 < x < 9.1 for x in lens) / max(1, len(lens)), 2)
    ends, dom, kinds = 0, 0, []
    inner = secs[:-1]
    for n_, a, z in inner:
        syms = [s_ for t, b, s_ in tl if z - 2 * m * stretch - 1e-6 <= t < z - 1e-6]
        sus = bool(syms) and 'sus' in syms[-1]
        for x, y in zip(syms, syms[1:]):
            r_ = re.match(r'^[A-G][b#]?', x).group(0)
            sus = sus or ('sus' in x and 'sus' not in y and re.match(r'^[A-G][b#]?', y).group(0) == r_)
        ends += sus
        dom += bool(syms) and _deg(syms[-1], t_pc).startswith('7:')
        kinds.append(' '.join(_deg(x, t_pc) for x in syms[-2:]))
    out['end_sus'] = round(ends / max(1, len(inner)), 2)
    out['end_V'] = round(dom / max(1, len(inner)), 2)
    out['end_kinds'] = len(set(kinds))
    cl = next(((a, z) for n_, a, z in secs if n_ == 'climax'), None)
    if cl:
        tops = {}
        for n in rh:
            if n[1] > FAST and cl[0] - 1e-6 <= n[0] < cl[1] - 1e-6:
                k_ = round(n[0], 2)
                tops[k_] = max(tops.get(k_, n), n, key=lambda x: x[2])
        line = sorted(tops.values())
        cells = []
        for k in range(int(round((cl[1] - cl[0]) / m))):
            a = cl[0] + k * m
            bn = [n for n in line if a - 1e-6 <= n[0] < a + m - 1e-6]
            cells.append((tuple(round(4 * (n[0] - a)) for n in bn), tuple(n[2] - bn[0][2] for n in bn))
                         if len(bn) >= 2 else None)
        best = cur = 0
        for x, y in zip(cells, cells[1:]):
            cur = cur + 1 if x is not None and x == y else 0
            best = max(best, cur)
        out['clx_tile'] = best + (1 if best else 0)
        hold, run, prev = 0.0, 0.0, None
        for i, n in enumerate(line):
            end_ = line[i + 1][0] if i + 1 < len(line) else n[0] + n[1]
            run = run + (end_ - n[0]) if prev == n[2] else end_ - n[0]
            prev = n[2]
            hold = max(hold, run)
        out['clx_hold'] = round(hold, 2)
    weave = 0
    longs = [n for n in rh if n[1] >= 1.0]
    for k in range(int(round(total / m))):
        a = k * m
        fast = [n for n in rh if a - 1e-6 <= n[0] < a + m - 1e-6 and n[1] <= FAST]
        under = [f for f in fast if any(l_[0] < f[0] - 1e-6 and l_[0] + l_[1] > f[0] and l_[2] > f[2] for l_ in longs)]
        weave += len(under) >= 3
    out['weave'] = weave
    out['end_rh'] = len([n for n in rh if n[0] >= total - 1e-6])
    return out


def _edb(xs):
    xs = [x for x in xs if x > -90]
    return 10 * math.log10(sum(10 ** (x / 10) for x in xs) / len(xs)) if xs else None


def audio_balance(folder: Path) -> dict:
    """The hands' balance in a render (report.json: node 'piano' = the right hand, 'comp' = the left): aud_bal the
    right hand's RMS over the left's per 4-bar phrase of the body (both hands sounding over -55 dB; intro / end left
    out), its mean; aud_bal_sd the spread; aud_lead the share of phrases at 1 dB or less; aud_whole the piece's;
    forward: three moments (m:ss, >= 20 s apart) where the left hand comes forward most (2-bar windows, the right
    hand still sounding)."""
    rp = folder / 'report.json'
    if not rp.is_file():
        return {}
    r = json.loads(rp.read_text(encoding='utf-8'))
    n = {x['id']: x for x in r['nodes']}
    if 'piano' not in n or 'comp' not in n:
        return {}
    bp, bc = n['piano']['barsRmsDb'], n['comp']['barsRmsDb']
    rows = r['timeline']['rows']
    sec_of = {}
    for s in r['sections']:
        for b in range(int(s['startBar']), int(s['endBar'])):
            sec_of[b] = s['name']
    nb = min(len(bp), len(bc))
    ph = []
    for k in range(0, nb, 4):
        a, b = _edb(bp[k:k + 4]), _edb(bc[k:k + 4])
        if a is not None and b is not None and a > -55 and b > -55 and sec_of.get(k + 1) not in (None, 'end', 'intro'):
            ph.append(a - b)
    win = []
    for k in range(nb - 1):
        a, b = _edb(bp[k:k + 2]), _edb(bc[k:k + 2])
        if a is not None and b is not None and a > -45 and b > -50 and sec_of.get(k + 1) not in (None, 'end', 'intro') \
                and k < len(rows):
            win.append((a - b, rows[k][1], sec_of.get(k + 1)))
    picks = []
    for d, sec, name in sorted(win):
        if all(abs(sec - p[0]) >= 20 for p in picks):
            picks.append((sec, d, name))
        if len(picks) == 3:
            break
    out = {'aud_whole': round(n['piano']['rmsDb'] - n['comp']['rmsDb'], 1)}
    if ph:
        out.update(aud_bal=round(st.mean(ph), 2), aud_bal_sd=round(st.pstdev(ph), 2),
                   aud_lead=round(sum(x <= 1 for x in ph) / len(ph), 2))
    out['forward'] = [f"{int(s // 60)}:{s % 60:04.1f} {name} {d:+.1f}" for s, d, name in sorted(picks)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', default='64000-64023')
    ap.add_argument('--json')
    ap.add_argument('--per-seed', action='store_true')
    ap.add_argument('--folders', nargs='*', help='endless tune folders (tune.json) instead of seeds')
    ap.add_argument('--sets', type=int, default=0, help='measure K sets (composer.set_plan) instead of single seeds')
    ap.add_argument('--set-n', type=int, default=10)
    ap.add_argument('--slots', type=int, default=0, help='the per-piece tells over K set plans (composer.set_plan, '
                    'one candidate per slot: the set draws - step / sequence / reharm - as a round plays them)')
    a = ap.parse_args()
    if a.sets:
        return sets(a)
    lo, hi = (int(x) for x in a.seeds.split('-'))
    g = genres.get('new-age-piano')
    rows = {}
    from agentsound.endless.run import load_scored
    slots = [(lo + 1000 * k + 37 * j, slot) for k in range(a.slots)
             for j, slot in enumerate(composer.set_plan(g, a.set_n, lo + 1000 * k))] if a.slots else []
    for sd in (a.folders or [x for x, _ in slots] or range(lo, hi + 1)):
        if slots:
            tune = composer.compose(g, sd, plan=dict(slots)[sd])
            song = endless.song(tune)
        elif a.folders:
            song, tune, _ = load_scored(Path(sd))
            sd = Path(sd).name
        else:
            tune = composer.compose(g, sd)
            song = endless.song(tune)
        r = measure(tune, song)
        if a.folders:
            r.update(audio_balance(Path(a.folders[len(rows)])))
        r['score'] = composer.score(song, tune, g)['score']
        r['meter'] = tune.meter
        rows[sd] = r
        if a.per_seed:
            print(sd, tune.meter, json.dumps(r))
    keys = ['score', 'off_scale', 'b4_share', 'b4_streak', 'clx_rhythm', 'ret_copy', 'ret_chart', 'grabs',
            'rh_silent', 'rh_gap', 'xx_inv', 'clx_den', 'clx_foreign', 'clx_octave', 'hand_bal', 'hand_bal_sd',
            'hand_lead', 'rh_c6', 'rh_e6', 'rh_med', 'aud_whole', 'aud_bal', 'aud_bal_sd', 'aud_lead',
            'top_at', 'grid8', 'end_sus', 'end_V', 'end_kinds', 'clx_tile', 'clx_hold', 'weave', 'end_rh',
            'mel_rate', 'dvel_med', 'dvel_p90', 'dvel_curv', 'rh_multi', 'rh_multi_A1', 'rh_multi_A', 'rh_multi_B',
            'rh_multi_climax', 'inner_move',
            'phrase_rests', 'clx_bal', 'clx_pk_bal', 'clx_vmax', 'clx_v112', 'clx_flat', 'clx_down', 'blk_copy',
            'a_leap', 'a_span', 'b_over', 'key_in', 'key_out'] + list(composer.SIGNATURE_TELLS) + list(G4_TELLS) + \
        list(G5_TELLS) + list(G7_TELLS) + list(G8_TELLS) + list(G9_TELLS) + list(G10_TELLS) + list(G11_TELLS) + list(G12_TELLS) + \
        list(G13_TELLS) + list(G14_TELLS)
    print(f"{len(rows)} tunes (seeds {lo}-{hi}; {sum(r['meter'] == 3 for r in rows.values())} waltzes)")
    for k in keys:
        for lab, sel in (('all', lambda r: True), ('waltz', lambda r: r['meter'] == 3)):
            if lab == 'waltz' and k not in ('rh_silent', 'rh_gap', 'xx_inv', 'clx_den'):
                continue
            xs = [r[k] for r in rows.values() if isinstance(r.get(k), (int, float)) and sel(r)]
            if xs:
                print(f"  {k:<11} {lab:<6} mean {st.mean(xs):7.3f}  max {max(xs):7.3f}  >0 {sum(x > 0 for x in xs)}")
    lays = [r.get('layout') for r in rows.values()]
    print('  layouts: ' + ', '.join(f"{k} {lays.count(k)}" for k in sorted(set(lays), key=str)))
    tops = sorted(r['top_at'] for r in rows.values() if 'top_at' in r)
    if tops:
        print(f"  top_at: p10 {tops[len(tops) // 10]:.2f}  median {tops[len(tops) // 2]:.2f}  p90 "
              f"{tops[(9 * len(tops)) // 10]:.2f}  in 0.70-0.78: {sum(0.7 <= x <= 0.78 for x in tops)} of {len(tops)}")
    opens = [r.get('open') for r in rows.values() if r.get('open')]
    print(f"  openings: {len(set(opens))} distinct of {len(opens)}; most common x{max(opens.count(o) for o in opens)}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding='utf-8')
    return 0


def sets(a) -> int:
    """--sets: K sets of --set-n tunes along composer.set_plan (one candidate per slot), the set-level tells."""
    g = genres.get('new-age-piano')
    lo = int(a.seeds.split('-')[0])
    agg = {'lay_distinct': [], 'lay_repeat': [], 'top_lo': [], 'top_hi': [], 'top_in_70_78': [], 'weave_pieces': [],
           'shared3': [], 'shared4': [], 'pairs4': [], 'grid8': [], 'end_sus': [], 'end_rh_kinds': [],
           'sig_repeat': [], 'sig_max_share': [], 'sig_none': [], 'sig_moves': [], 'pen_shared': [], 'pen_iv6': [],
           'motto_same': [], 'clx_theme': [], 'arrivals': [], 'pause_clx': [], 'peak_distinct': [], 'peak_a6': [],
           'clx_lh_top': [], 'clx_lh_kinds': []}
    for k in range(a.sets):
        base = lo + 1000 * k
        plan = composer.set_plan(g, a.set_n, base)
        rows, r3, r4, sigs, g4s, arr, peaks, lhs = [], [], [], [], [], [], [], []
        for j, slot in enumerate(plan):
            tune = composer.compose(g, base + 37 * j, plan=slot)
            song = endless.song(tune)
            peaks.append(max((n.pitch for n in song.tracks['piano']._notes), default=0))
            lhs.append((getattr(song, 'endless_lh', None) or {}).get('climax'))
            rows.append(form_tells(tune, song))
            g4s.append(g4_tells(tune, song))
            arr.append((tune.arrange or {}).get('arrival'))
            sigs.append((getattr(song, 'endless_signature', None) or {}).get('moves') or {})
            t_pc = Key(tune.key).tonic % 12
            r3.append(routes(song, t_pc, 3))
            r4.append(routes(song, t_pc, 4))
        lays = [r['layout'] for r in rows]
        tops = [r['top_at'] for r in rows]
        sh3 = {x for i in range(len(r3)) for j in range(i + 1, len(r3)) for x in r3[i] & r3[j]}
        sh4 = {x for i in range(len(r4)) for j in range(i + 1, len(r4)) for x in r4[i] & r4[j]}
        agg['lay_distinct'].append(len(set(lays)))
        agg['lay_repeat'].append(sum(x == y for x, y in zip(lays, lays[1:])))
        agg['top_lo'].append(min(tops))
        agg['top_hi'].append(max(tops))
        agg['top_in_70_78'].append(sum(0.7 <= x <= 0.78 for x in tops))
        agg['weave_pieces'].append(sum(r['weave'] > 0 for r in rows))
        agg['grid8'].append(st.mean(r['grid8'] for r in rows))
        agg['end_sus'].append(st.mean(r['end_sus'] for r in rows))
        agg['end_rh_kinds'].append(len({r['end_rh'] for r in rows}))
        prints = [x for m in sigs for x in composer.signature_prints(m)]
        agg['sig_repeat'].append(len(prints) - len(set(prints)))     # a move's fingerprint twice in the set
        agg['sig_max_share'].append(max([sum(mv in m for m in sigs) / len(sigs)
                                         for mv in ('motto', 'ostinato', 'pause', 'goose', 'cascade')]))
        agg['sig_none'].append(sum(not m for m in sigs))
        agg['sig_moves'].append(st.mean(len(m) for m in sigs))
        pens = [r['pen_bar'] for r in g4s]
        agg['pen_shared'].append(max(pens.count(x) for x in pens))      # the most shared penultimate bar
        agg['pen_iv6'].append(sum(':m6' in x for x in pens))             # pieces closing through a minor iv6
        starts = [r['motto_start'] for r in g4s if r.get('motto_start') is not None]
        agg['motto_same'].append(len(starts) - len(set(starts)))         # mottos sharing their first pitch
        agg['clx_theme'].append(st.mean(r.get('clx_theme', 0) for r in g4s))
        agg['arrivals'].append(len(set(arr)))                          # (round g9: the climax's arrivals in the set)
        agg['pause_clx'].append(sum((m.get('pause') or {}).get('seam') == 'climax' for m in sigs))
        agg['peak_distinct'].append(len(set(peaks)))                    # (round g11: nine of eleven on A6 / Ab6)
        agg['peak_a6'].append(sum(p >= 92 for p in peaks))
        lk = [x for x in lhs if x]                                      # (six of eight climaxes on one LH figure)
        agg['clx_lh_top'].append(max((lk.count(x) for x in lk), default=0))
        agg['clx_lh_kinds'].append(len(set(lk)))
        agg['shared3'].append(len(sh3))
        agg['shared4'].append(len(sh4))
        agg['pairs4'].append(sum(bool(r4[i] & r4[j]) for i in range(len(r4)) for j in range(i + 1, len(r4))))
        if a.per_seed:
            print(base, ' '.join(map(str, lays)), ' '.join(f"{x:.2f}" for x in tops), f"shared4 {len(sh4)}",
                  sorted(sh4)[:3])
    print(f"{a.sets} sets of {a.set_n} (seeds {lo} + 1000 k)")
    for k_, xs in agg.items():
        print(f"  {k_:<13} mean {st.mean(xs):7.2f}  min {min(xs):6.2f}  max {max(xs):6.2f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
