"""The Far Shore - a hand-written chamber-orchestra piece of longing (D minor, 4/4, 66 BPM, ~3:35).
Build: python -m agentsound build songs/pro-orch-longing

A "pro" reference for the blind test against the endless orchestra genre: the same band setup
(endless.orchestra.band), every note written by hand.

  intro    4  harp arpeggios over a muted string chord, Dm(add9) - Bbmaj7 - Gm6 - A7sus4 A7
  A        8  the theme on the solo oboe (A4 D5 E5 F5 | A5 ...: the rising fourth + the long maj7 over Bb), harp in
              eighths, strings low and soft; a half cadence on A7
  B        8  the bittersweet turn to F major: the violins I take a new, wider tune (up to C6), the cellos sing a
              counter-line in the tenor, rolled harp chords, clarinets + a horn warm the second half
  A2       8  the theme in the cellos (an octave down), a flute descant over it, the horn joins the cellos for the
              second phrase, violins I take the descant; ends Gm6 - A7, deceptively into ...
  build    6  the rising-fourth motif climbs through the orchestra (violas + clarinet, violins II + oboe, violins I +
              flute, everyone on the Neapolitan Eb), horns and tremolo violas crescendo onto A7
  climax   8  the theme at its highest: violins I + flute an octave up (peak Bb6 in bar 6), violins II + oboe below,
              a horn counter-melody, the harmony recoloured (Bbmaj7 - Gm9 - Ebmaj7 - A7); broadening
  return   8  pp: the oboe alone again over violas and cellos, a halo of violins I in the second phrase; the
              ending sinks (G5 F5 E5 | F5 E5 D5)
  coda     4  the cellos remember the opening four notes, the oboe answers, ritardando
  end      2  Dm(add9) held, the oboe's last D5 against the violins' E5
"""
import math
from itertools import product

from agentsound import *
from agentsound.bandlib import orchestra as orch
from agentsound.endless.orchestra import band as orchestra_band
from agentsound.theory import chord as _chord, note as _note

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'The Far Shore', 'artist': 'AgentSound', 'album': 'Orchestral References',
            'genre': 'Orchestral', 'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#d8cbb6', '#2f3a4f'], 'title': 'THE FAR SHORE',
         'subtitle': 'chamber orchestra - AgentSound', 'seed': 47}

KEY = 'D minor'
TEMPO = 66
SEED = 4711
ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons',
         'horns', 'harp')

SECTIONS = [('intro', 4), ('A', 8), ('B', 8), ('A2', 8), ('build', 6), ('climax', 8), ('return', 8), ('coda', 4),
            ('end', 2)]

# ------------------------------------------------------------------------------------------------ harmony
CHARTS = {
    'intro': 'Dm(add9) | Bbmaj7 | Gm6 | A7sus4:2 A7:2',
    'A': 'Dm | Bbmaj7 | Gm7 | A7sus4:2 A7:2 | Dm | Gm:2 C7:2 | Fmaj7:2 Bb:2 | Em7b5:2 A7:2',
    'B': 'F | C/E | Dm | Bb | Gm7 | C7 | Fmaj7:2 Bb:2 | Gm7:2 A7:2',
    'A2': 'Dm | Bbmaj7 | Gm7 | A7sus4:2 A7:2 | Dm | Gm:2 C7:2 | Fmaj7:2 Bb:2 | Gm6:2 A7:2',
    'build': 'Bb | C | Dm | Eb | Gm6/Bb | A7sus4:2 A7:2',
    'climax': 'Bbmaj7 | Gm9 | Ebmaj7 | A7sus4:2 A7:2 | Dm | Gm:2 C7:2 | Fmaj7:2 Bb:2 | Gm6:2 A7:2',
    'return': 'Dm | Bbmaj7 | Gm7 | A7sus4:2 A7:2 | Dm | Gm:2 C7:2 | Fmaj7:2 Bb:2 | Gm6:2 A7:2',
    'coda': 'Dm | Bbmaj7 | Gm6 | A7sus4:2 A7:2',
    'end': 'Dm(add9):8',
}

# ------------------------------------------------------------------------------------------------ the lines
# pitch:beats, r:beats = rest; bars separated by '|' (only for reading)
THEME = ('A4:1 D5:1 E5:1 F5:1 | A5:2.5 G5:0.5 F5:1 | F5:1.5 E5:0.5 D5:1 Bb4:1 | D5:2 C#5:1.5 r:0.5 | '
         'A4:1 D5:1 F5:1 G5:1 | Bb5:2 A5:1 G5:1 | A5:1.5 G5:0.5 F5:1 D5:1 | E5:1.5 D5:0.5 C#5:1.5 r:0.5')
B_TUNE = ('C5:2 F5:1 A5:1 | G5:2.5 F5:0.5 E5:1 | D5:1 F5:1 A5:1.5 G5:0.5 | F5:3 D5:1 | '
          'Bb4:1 D5:1 F5:1 A5:1 | C6:1.5 Bb5:0.5 A5:1 G5:1 | A5:2 F5:1 D5:1 | G5:1 F5:1 E5:1 C#5:1')
B_CELLO = ('F3:2 A3:2 | G3:2 C4:1 Bb3:1 | A3:3 F3:1 | Bb3:2 D4:2 | D4:2 C4:1 Bb3:1 | Bb3:2 G3:2 | '
           'A3:2 D4:2 | Bb3:2 G3:1 E3:1')
A2_THEME = ('A3:1 D4:1 E4:1 F4:1 | A4:2.5 G4:0.5 F4:1 | F4:1.5 E4:0.5 D4:1 Bb3:1 | D4:2 C#4:1.5 r:0.5 | '
            'A3:1 D4:1 F4:1 G4:1 | Bb4:2 A4:1 G4:1 | A4:1.5 G4:0.5 F4:1 D4:1 | E4:2 C#4:1.5 r:0.5')
A2_DESCANT_FL = 'A5:2 F5:2 | F5:3 r:1 | G5:2 F5:2 | E5:3.5 r:0.5'
A2_DESCANT_VN = 'F5:2 A5:2 | G5:4 | F5:2 D5:2 | D5:2 E5:2'
CLIMAX = ('A5:1 D6:1 E6:1 F6:1 | A6:2.5 G6:0.5 F6:1 | F6:1.5 Eb6:0.5 D6:1 Bb5:1 | D6:2 C#6:2 | '
          'A5:1 D6:1 F6:1 G6:1 | Bb6:2 A6:1 G6:1 | A6:1.5 G6:0.5 F6:1 D6:1 | E6:1.5 D6:0.5 C#6:2')
CLIMAX_FL = ('A5:1 D6:1 E6:1 F6:1 | A6:2.5 G6:0.5 F6:1 | F6:1.5 Eb6:0.5 D6:1 Bb5:0.75 r:0.25 | D6:2 C#6:1.5 r:0.5 | '
             'A5:1 D6:1 F6:1 G6:1 | Bb6:2 A6:1 G6:1 | A6:1.5 G6:0.5 F6:1 D6:1 | E6:1.5 D6:0.5 C#6:2')
HORN_CLIMAX = ('D4:2 F4:2 | Bb4:2 A4:1 G4:1 | G4:2 Bb4:2 | A4:2 G4:1.5 r:0.5 | F4:2 A4:2 | D5:2 C5:1 Bb4:1 | '
               'A4:2 F4:2 | G4:2 E4:2')
RETURN = ('A4:1 D5:1 E5:1 F5:1 | A5:2.5 G5:0.5 F5:1 | F5:1.5 E5:0.5 D5:1 Bb4:1 | D5:2 C#5:1.5 r:0.5 | '
          'A4:1 D5:1 E5:1 F5:1 | G5:2 F5:1 E5:1 | F5:1.5 E5:0.5 D5:2 | E5:2 C#5:1.5 r:0.5')
CODA_CELLO = 'A3:1 D4:1 E4:1 F4:1 | A4:3.5 r:0.5'
CODA_OBOE = 'r:1 A5:1 G5:1 E5:1 | D5:2 C#5:2'

# the build: the rising fourth (5 - 1 - 2 - 3 of each chord) climbing bar by bar
BUILD = {
    'violas': [(0, 'F4:1 Bb4:1 C5:1 D5:1')],
    'clarinets': [(0, 'F4:1 Bb4:1 C5:1 D5:1')],
    'violins2': [(4, 'G4:1 C5:1 D5:1 E5:1'), (12, 'Bb4:1 Eb5:1 F5:1 G5:1'), (16, 'G5:2 F5:1 E5:1'),
                 (20, 'D5:2 C#5:2')],
    'oboes': [(4, 'G4:1 C5:1 D5:1 E5:1'), (12, 'Bb4:1 Eb5:1 F5:1 G5:1'), (16, 'G5:2 F5:1 E5:1'),
              (20, 'D5:2 C#5:1.5')],
    'violins1': [(8, 'A4:1 D5:1 E5:1 F5:1'), (12, 'Bb5:1 Eb6:1 F6:1 G6:1'), (16, 'G6:2 F6:1 E6:1'),
                 (20, 'D6:2 C#6:2')],
    'flutes': [(8, 'A5:1 D6:1 E6:1 F6:1'), (12, 'Bb5:1 Eb6:1 F6:1 G6:1'), (16, 'G6:2 F6:1 E6:1'),
               (20, 'D6:2 C#6:1.5')],
}

# ------------------------------------------------------------------------------------------------ dynamics
DYNAMICS = {
    'intro': [(0, 'pp'), (8, 34), (14, 'pp')],
    'A': [(0, 'p'), (6, 46), (14, 'p'), (20, 'mp'), (24, 52), (31, 'p')],
    'B': [(0, 'mp'), (12, 64), (20, 'mf'), (24, 74), (31, 'mp')],
    'A2': [(0, 'mp'), (8, 66), (20, 'mf'), (28, 74), (31, 'mf')],
    'build': [(0, 'mp'), (12, 'mf'), (20, 'f'), (23.5, 102)],
    'climax': [(0, 90), (12, 98), (16, 96), (20, 108), (24, 100), (28, 90), (31.5, 74)],
    'return': [(0, 'p', 'step'), (14, 46), (20, 'p'), (31, 34)],
    'coda': [(0, 'pp'), (6, 38), (12, 'pp')],
    'end': [(0, 'pp'), (8, 18)],
}


# ------------------------------------------------------------------------------------------------ helpers
def seq(spec, at=0.0):
    """'A4:1 D5:1 r:0.5 ...' -> [(start, dur, pitch)] from beat `at`."""
    out, t = [], float(at)
    for tok in spec.replace('|', ' ').split():
        p, d = tok.split(':')
        d = float(d)
        if p != 'r':
            out.append((t, d, _note(p)))
        t += d
    return out


def chart(spec, at=0.0):
    """'Dm | Gm:2 C7:2' -> [(start, beats, symbol)] (a bar token without :beats = 4 beats)."""
    out, t = [], float(at)
    for bar in spec.split('|'):
        for tok in bar.split():
            sym, d = (tok.rsplit(':', 1) if ':' in tok else (tok, '4'))
            out.append((t, float(d), sym))
            t += float(d)
    return out


def _colour(c):
    """A chord's tones other than root and fifth (the ones a voicing must not drop)."""
    return set(c.pcs) - {c.root, (c.root + 7) % 12}


def voices(ch, specs, upto=None):
    """Sustained chord voices led smoothly: specs = [(role, start pitch, lo, hi)] top to bottom. Every chord picks
    one tone per voice - strictly descending, the colour tones (3rd, 7th, 6th, 9th, sus) present, the least motion -
    and a voice that keeps its tone holds it (tied). Returns [(role, [(start, dur, pitch)])]."""
    prev = [_note(sp[1]) for sp in specs]
    lines = [[] for _ in specs]
    for t, d, sym in ch:
        if upto is not None and t >= upto:
            break
        c = _chord(sym)
        pcs = set(c.pcs)
        cands = []
        for (role, _, lo, hi), p0 in zip(specs, prev):
            lo, hi = _note(lo), _note(hi)
            for w in (7, 12, 19):
                cs = [p for p in range(p0 - w, p0 + w + 1) if p % 12 in pcs and lo <= p <= hi]
                if cs:
                    break
            cands.append(cs)
        best, bc = None, None
        for combo in product(*cands):
            if any(combo[i] <= combo[i + 1] for i in range(len(combo) - 1)):
                continue
            got = {p % 12 for p in combo}
            cost = sum(abs(a - b) for a, b in zip(combo, prev))
            cost += 5 * len(_colour(c) - got) + 2 * (len(combo) - len(got))
            if bc is None or cost < bc:
                best, bc = combo, cost
        if best is None:
            best = tuple(cs[0] for cs in cands)
        for i, p in enumerate(best):
            ln = lines[i]
            if ln and ln[-1][2] == p and abs(ln[-1][0] + ln[-1][1] - t) < 1e-6:
                ln[-1] = (ln[-1][0], ln[-1][1] + d, p)
            else:
                ln.append((t, d, p))
        prev = list(best)
    return [(sp[0], ln) for sp, ln in zip(specs, lines)]


def bassline(ch, start, lo='C1', hi='C4', octave=0):
    """The chords' bass notes (slash bass or root), each nearest the last one (`octave` x 12 added)."""
    p0, out = _note(start), []
    lo, hi = _note(lo), _note(hi)
    for t, d, sym in ch:
        c = _chord(sym)
        pc = c.bass_pc if c.bass_pc is not None else c.root
        cs = [p for p in range(lo, hi + 1) if p % 12 == pc]
        p = min(cs, key=lambda x: (abs(x - p0), x))
        out.append((t, d, p + 12 * octave))
        p0 = p
    return out


def arpeggio(ch, lo='D2', span=19, rate=0.5, ring=1.5, shape='updown'):
    """Harp: per chord its bass then the chord tones up through `span` semitones (and back), in `rate` beats."""
    out = []
    for t, d, sym in ch:
        c = _chord(sym)
        bpc = c.bass_pc if c.bass_pc is not None else c.root
        base = next(p for p in range(_note(lo), _note(lo) + 12) if p % 12 == bpc)
        tones = [p for p in range(base, base + span + 1) if p % 12 in set(c.pcs) | {bpc}]
        if shape == 'up':
            cyc = tones
        else:
            cyc = tones + tones[-2:0:-1]
        n = int(round(d / rate))
        for i in range(n):
            out.append((t + i * rate, ring, cyc[i % len(cyc)]))
    return out


def rolled(ch, lo='D2', span=24, every=4.0, spread=0.06):
    """Harp: a rolled chord (bass up) on each chord's start (and every `every` beats inside long chords)."""
    out = []
    for t, d, sym in ch:
        c = _chord(sym)
        bpc = c.bass_pc if c.bass_pc is not None else c.root
        base = next(p for p in range(_note(lo), _note(lo) + 12) if p % 12 == bpc)
        tones = [base] + [p for p in range(base + 7, base + span + 1) if p % 12 in set(c.pcs)]
        k = 0.0
        while k < d - 1e-6:
            for i, p in enumerate(tones):
                out.append((t + k + i * spread, max(1.0, min(every, d - k)) - i * spread, p))
            k += every
    return out


def within(notes, a, b):
    return [n for n in notes if a - 1e-6 <= n[0] < b - 1e-6]


# ------------------------------------------------------------------------------------------------ the piece
def build() -> Song:
    s = Song(METADATA['title'], tempo=TEMPO, key=KEY, seed=SEED, tail=8)
    sec = {name: s.section(name, bars=n) for name, n in SECTIONS}
    at = {name: float(x.start) for name, x in sec.items()}
    ch = {name: chart(CHARTS[name], at[name]) for name in CHARTS}
    s.endless_timeline = [c for name, _ in SECTIONS for c in ch[name]]

    # tempo: the phrases breathe; a push through the build, broad climax, a slower, inward return; the coda dies away
    s.rubato(sec['intro'], depth=0.04, phrase='lean')
    s.rubato((sec['A'].start, sec['A'].bar(4)), depth=0.03, phrase='arch')
    s.rubato((sec['A'].bar(4), sec['A'].end), depth=0.035, phrase='breath')
    s.rubato(sec['B'], depth=0.03, phrase='wave')
    s.rubato(sec['A2'], depth=0.03, phrase='arch')
    s.accelerando((sec['build'].start, sec['build'].bar(4)), to=1.06)
    s.ritardando((sec['build'].bar(4), sec['build'].end), to=0.9, a_tempo=False)
    s.set_tempo(sec['climax'], 64)
    s.rubato((sec['climax'].start, sec['climax'].bar(5)), depth=0.025, phrase='arch')
    s.ritardando((sec['climax'].bar(6), sec['climax'].end), to=0.86, a_tempo=False)
    s.set_tempo(sec['return'], 62)
    s.rubato(sec['return'], depth=0.035, phrase='breath')
    s.ritardando((sec['coda'].bar(2), sec['end'].start), to=0.8, a_tempo=False)

    b = orchestra_band(s, ROLES)
    sc = orch.Score(s, b, DYNAMICS, key=KEY, seed=SEED, style='film')

    def line(role, spec, start, off=0.0, art='sustain'):
        sc.add(role, seq(spec, start), art, off=off, line=True)

    starts = sorted(at.values())

    def arc(n):
        """A swell over every 4-bar phrase (soft in, fuller in the middle, easing out)."""
        s0 = max(x for x in starts if x <= n[0] + 1e-6)
        return 6.0 * math.sin(math.pi * (((n[0] - s0) % 16) + 0.5 * n[1]) / 16) - 3.0

    def harp_touch(n):
        """The harpist's hand: the bar's downbeat and the arpeggio's top lean in, the passing notes lighter."""
        s0 = max(x for x in starts if x <= n[0] + 1e-6)
        pos = (n[0] - s0) % 4
        acc = 14.0 if pos < 0.01 else 5.0 if abs(pos - 2) < 0.01 else -9.0 if pos % 1 else 0.0
        return acc + 0.6 * (n[2] - 57) + arc(n)

    def harp(ns, off=0.0, line=False):
        sc.add('harp', ns, None, off=off, line=line, offs=harp_touch)   # (the harp has no articulations)

    def pad(parts, off=-4.0, art='sustain'):
        for role, ns in parts:
            if ns:
                sc.add(role, ns, art, off=off, line=False, offs=arc)

    # ---- intro: harp alone over a soft string chord
    c = ch['intro']
    harp(arpeggio(c, lo='D2', span=19), off=2, line=False)
    pad(voices(c, [('violins2', 'A4', 'G3', 'C6'), ('violas', 'E4', 'C3', 'A4'), ('cellos', 'A3', 'C2', 'E4')]),
        off=-9)
    sc.add('basses', bassline(c, 'D2'), off=-6, line=False)

    # ---- A: the oboe's theme
    c = ch['A']
    line('oboes', THEME, at['A'], off=14)
    harp(arpeggio(c, lo='D2', span=19), off=-2, line=False)
    pad(voices(c, [('violas', 'F4', 'C4', 'A4'), ('violas', 'D4', 'A3', 'F4')]), off=-12)   # (violins wait for B)
    sc.add('cellos', bassline(c, 'D3', lo='C2', hi='E3'), off=-10, line=False, offs=arc)   # the cellos the bass
    sc.add('basses', bassline(within(c, at['A'] + 16, at['B']), 'D2'), off=-10, line=False)
    sc.add('clarinets', seq('r:2 A4:2 | Bb4:2 G4:2 | A4:2 F4:2 | G4:2 E4:1.5 r:0.5', at['A'] + 16), off=-8,
           line=False)

    # ---- B: F major, the violins I's new tune, the cellos' counter-line
    c = ch['B']
    line('violins1', B_TUNE, at['B'], off=2)
    line('cellos', B_CELLO, at['B'], off=-2)
    pad(voices(c, [('violins2', 'A4', 'E4', 'D5'), ('violas', 'F4', 'C4', 'A4')]), off=-5)
    sc.add('basses', bassline(c, 'F2'), off=-5, line=False)
    harp(rolled(c, lo='F2', span=19), off=-4, line=False)
    half = at['B'] + 16
    pad(voices(within(c, half, at['A2']), [('clarinets', 'A4', 'E4', 'C5'), ('horns', 'F4', 'C4', 'A4')]), off=-8)
    sc.add('bassoons', bassline(within(c, half, at['A2']), 'G2', lo='A#1', hi='D3'), off=-8, line=False)

    # ---- A2: the theme in the cellos, a flute (then violins I) descant, the horn joins the cellos
    c = ch['A2']
    line('cellos', A2_THEME, at['A2'], off=2)
    line('horns', A2_THEME[A2_THEME.index('| A3:1 D4:1 F4') + 2:], at['A2'] + 16, off=-4)
    line('flutes', A2_DESCANT_FL, at['A2'], off=-4)
    line('violins1', A2_DESCANT_VN, at['A2'] + 16, off=-3)
    pad(voices(c, [('violins2', 'D5', 'A4', 'F5'), ('violins2', 'A4', 'E4', 'C5'), ('violas', 'F3', 'C3', 'A3')]),
        off=-7)
    sc.add('basses', bassline(c, 'D2'), off=-5, line=False)
    harp(rolled(within(c, at['A2'] + 16, at['build']), lo='D2', span=12, every=2.0), off=-6, line=False)

    # ---- build: the rising fourth climbs; horns + tremolo violas crescendo onto A7
    c = ch['build']
    for role, frags in BUILD.items():
        for off_b, spec in frags:
            sc.add(role, seq(spec, at['build'] + off_b), off=-1 if role in ('violins1', 'violins2') else -3,
                   line=True)
    pad(voices(c, [('horns', 'F4', 'C4', 'C5'), ('horns', 'D4', 'G3', 'G4')]), off=-5)
    bl = bassline(c, 'Bb1', lo='E1', hi='D3')
    sc.add('basses', bl, off=-3, line=False)
    sc.add('cellos', [(t, d, p + 12) for t, d, p in bl], off=-3, line=False)
    sc.add('bassoons', [(t, d, p + 12) for t, d, p in bl], off=-6, line=False)
    pad(voices(within(c, at['build'] + 12, at['climax']), [('violas', 'G4', 'C4', 'A4'), ('violas', 'D4', 'C3', 'F4')]),
        off=-4, art='tremolo')
    pad(voices(within(c, at['build'], at['build'] + 8), [('violins1', 'D5', 'A4', 'F5')]), off=-8)
    harp(arpeggio(within(c, at['build'] + 20, at['climax']), lo='A1', span=36, rate=0.25, ring=1.0,
                            shape='up'), off=-2, line=False)
    # (the A7 bar: the violas' tremolo and the bass hold - the harp sweeps up into the climax)

    # ---- climax: the theme at its highest
    c = ch['climax']
    line('violins1', CLIMAX, at['climax'], off=-4)
    line('flutes', CLIMAX_FL, at['climax'], off=-7)
    line('violins2', _octave_down(CLIMAX), at['climax'], off=-5)
    line('oboes', _octave_down(CLIMAX_FL), at['climax'], off=-8)
    line('horns', HORN_CLIMAX, at['climax'], off=-4)
    pad(voices(c, [('clarinets', 'F4', 'C4', 'A4'), ('clarinets', 'D4', 'A3', 'F4')]), off=-10)
    pad(voices(c, [('violas', 'D4', 'A3', 'G4'), ('violas', 'A3', 'D3', 'D4')]), off=-6)
    bl = bassline(c, 'Bb1', lo='E1', hi='D3')
    sc.add('basses', bl, off=0, line=False)
    sc.add('cellos', [(t, d, p + 12) for t, d, p in bl], off=0, line=False)
    sc.add('bassoons', [(t, d, p + 12) for t, d, p in bl], off=-4, line=False)
    harp(arpeggio(c, lo='D2', span=24, rate=0.5, ring=1.5), off=-2, line=False)

    # ---- return: pp, the oboe alone again
    c = ch['return']
    line('oboes', RETURN, at['return'], off=14)
    pad(voices(c, [('violas', 'F4', 'C4', 'A4'), ('violas', 'D4', 'A3', 'F4')]), off=-12)
    sc.add('cellos', bassline(c, 'D3', lo='C2', hi='E3'), off=-10, line=False, offs=arc)
    pad(voices(within(c, at['return'] + 16, at['coda']), [('violins2', 'A4', 'F4', 'C5')]), off=-7)
    pad(voices(within(c, at['return'] + 16, at['coda']), [('violins1', 'A5', 'F5', 'C6')]), off=-12)
    sc.add('basses', bassline(within(c, at['return'] + 16, at['coda']), 'D2'), off=-8, line=False)
    harp(rolled(c, lo='D2', span=19, every=4.0), off=-5, line=False)

    # ---- coda: the cellos remember, the oboe answers
    c = ch['coda']
    line('cellos', CODA_CELLO, at['coda'], off=0)
    line('oboes', CODA_OBOE, at['coda'] + 8, off=14)
    pad(voices(c, [('violas', 'F4', 'C4', 'A4'), ('violas', 'D4', 'A3', 'F4')]), off=-10)
    sc.add('cellos', bassline(within(c, at['coda'] + 8, at['end']), 'G3', lo='C3', hi='A3'), off=-6, line=False)
    sc.add('basses', bassline(c, 'D2'), off=-8, line=False)
    sc.add('clarinets', seq('D4:2 E4:2 | E4:2 C#4:2', at['coda'] + 8), off=-9, line=False)

    # ---- end: Dm(add9) held - the oboe's D5 against the violins' E5
    e = at['end']
    sc.add('oboes', [(e, 6.5, _note('D5'))], off=12, line=False)
    sc.add('violins1', [(e, 8.0, _note('A5'))], off=-8, line=False)
    sc.add('violins2', [(e, 8.0, _note('E5')), (e, 8.0, _note('A4'))], off=-6, line=False)
    sc.add('violas', [(e, 8.0, _note('F4'))], off=-4, line=False)
    sc.add('cellos', [(e, 8.0, _note('D3')), (e, 8.0, _note('A3'))], off=-2, line=False)
    sc.add('basses', [(e, 8.0, _note('D2'))], off=-4, line=False)
    sc.add('clarinets', [(e, 7.0, _note('F4'))], off=-10, line=False)
    harp([(e + i * 0.09, 6.0, _note(p)) for i, p in enumerate(('D2', 'A2', 'D3', 'F3', 'A3', 'E4', 'A4'))],
           off=0, line=False)

    sc.perform()
    return s


def _octave_down(spec):
    """The same line an octave lower."""
    out = []
    for tok in spec.split():
        if tok == '|' or tok.startswith('r:'):
            out.append(tok)
            continue
        p, d = tok.split(':')
        out.append(f'{p[:-1]}{int(p[-1]) - 1}:{d}')
    return ' '.join(out)
