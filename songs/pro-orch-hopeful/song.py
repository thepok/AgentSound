"""The Long Way Toward Morning - an original hopeful film-orchestral piece for full orchestra in D major (the
climax and the return lifted to E major). Build: python -m agentsound build songs/pro-orch-hopeful

A composed ("pro") reference for the endless orchestra blind rounds: written by hand, played by the SAME setup as an
endless film-orchestra piece (agentsound.endless.orchestra.band + orch.Score style='film'), so the sound is no tell -
only the writing differs. 4/4, 72 BPM, 58 bars, ~3:20.

  intro    4  strings pp on a D pedal (Dadd9 - G/D), harp ripples, the flute sings the theme's head and waits on Asus4
  A        8  the theme on the oboe (A4-B5: a rising fourth into a held note, the lift to B5 in bar 6), strings and
              harp under it, the clarinets a soft third-pair in the second phrase; a full cadence on D
  B        8  contrast in the cellos (IV - A/G - F#m7 - Bm7 - Em7 - F#7 - Gmaj7 - Asus4 A7), horns sustaining, the
              clarinet doubling the cellos an octave up in the answer, the flute's small replies in the gaps
  A2       8  the theme in the violins I (violins II a sixth under its second phrase), a flute descant above, violas
              in moving eighths, horns warm in the middle; the ending left open on F#5
  build    8  the theme's head sequenced up (Bm - G - Em7 - A/C# - D/F# - G - F#m7 - B7sus4 B7), strings tremolo,
              brass entering, the timpani and a cymbal roll swelling into the downbeat: B7 pivots to E major
  climax   8  the only tutti: the theme a step higher in E major, its peak raised to C#6, trumpets and flutes on the
              violins, horns and violins II an octave under, cellos / trombones a counter-line, timpani and cymbal
  A3       8  quiet return: a solo horn sings the theme (in E), the flute takes the second phrase; a deceptive C#m7
  coda     4  the oboe's last echo of the head over Amaj7 - Am6 (the borrowed iv) - E/G# - B9sus4
  end      2  a held E(add9), harp rolled, fermata

CREDITS: Sonatina Symphonic Orchestra 4.0 (Mattias Westlund, CC-BY-SA 3.0 / CC-Sampling+), VSCO 2 CE (Versilian
Studios, CC0) - see the build's credits output.
"""
from agentsound import *
from agentsound.bandlib import orchestra as orch
from agentsound.endless.orchestra import band as orchestra_band
from agentsound.theory import chord as _chord

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'The Long Way Toward Morning', 'artist': 'AgentSound', 'album': 'Orchestral References',
            'genre': 'Soundtrack', 'year': 2026}
COVER = {'style': 'classical', 'palette': ['#f6e3b4', '#d0774a'], 'title': 'THE LONG WAY TOWARD MORNING',
         'subtitle': 'AgentSound - Orchestral References', 'seed': 72}

KEY = 'D major'
SEED = 7203
TEMPO = 72
ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
         'harp', 'timpani', 'trumpets', 'trombones', 'tuba', 'percussion')
FORM = [('intro', 4), ('A', 8), ('B', 8), ('A2', 8), ('build', 8), ('climax', 8), ('A3', 8), ('coda', 4),
        ('end', 2)]

# ------------------------------------------------------------------------------------------------ harmony
# per bar: one chord, or two (half a bar each)
CHART = {
    'intro': ['Dadd9', 'G/D', 'Dadd9', 'Asus4 A'],
    'A': ['D', 'Bm7', 'Gmaj7', 'Asus4 A', 'D/F#', 'G', 'Em7 A7', 'D'],
    'B': ['G', 'A/G', 'F#m7', 'Bm7', 'Em7', 'F#7', 'Gmaj7', 'Asus4 A7'],
    'A2': ['D', 'Bm7', 'Gmaj7', 'Asus4 A', 'D/F#', 'G', 'Em7 A7', 'D'],
    'build': ['Bm', 'G', 'Em7', 'A/C#', 'D/F#', 'G', 'F#m7', 'B7sus4 B7'],
    'climax': ['E', 'C#m7', 'Amaj7', 'Bsus4 B', 'E/G#', 'A', 'F#m7 B7', 'E'],
    'A3': ['E', 'C#m7', 'Amaj7', 'Bsus4 B', 'E/G#', 'A', 'F#m7 B7', 'C#m7'],
    'coda': ['Amaj7', 'Am6', 'E/G#', 'B7sus4'],
    'end': ['Eadd9', 'Eadd9'],
}

# ------------------------------------------------------------------------------------------------ the lines
# 'PITCH:beats' (r = rest), one after the other from the section start
THEME = ('A4:1 D5:2 E5:1 | F#5:3 E5:1 | D5:2 B4:1 D5:1 | E5:3 r:1 | '
         'A4:1 D5:2 E5:1 | F#5:1 G5:1 B5:2 | A5:1.5 G5:0.5 F#5:1 E5:1 | D5:3 r:1')
# A2: the second bar ornamented, the second phrase's ending turned and left open on the third
THEME2 = ('A4:1 D5:2 E5:1 | F#5:1.5 G5:0.5 F#5:1 E5:1 | D5:2 B4:1 D5:1 | E5:3 r:1 | '
          'A4:1 D5:2 E5:1 | F#5:1 G5:1 B5:2 | A5:2 G5:1 E5:1 | F#5:3 r:1')
# the climax (E major): the theme a step up, the second half climbing on to C#6
CLIMAX = ('B4:1 E5:2 F#5:1 | G#5:3 F#5:1 | E5:1 C#5:1 E5:1 A5:1 | F#5:2 G#5:1 A5:1 | '
          'B5:2 G#5:1 B5:1 | C#6:3 B5:1 | A5:1.5 G#5:0.5 F#5:1 D#5:1 | E5:4')
# the quiet return (E major): horn (an octave down) bars 1-4, flute bars 5-8 (written pitch), a deceptive ending
RET_HORN = 'B3:1 E4:2 F#4:1 | G#4:3 F#4:1 | E4:2 C#4:1 E4:1 | F#4:3 r:1'
RET_FLUTE = 'r:16 B4:1 E5:2 F#5:1 | G#5:1 A5:1 C#6:2 | B5:1.5 A5:0.5 G#5:1 F#5:1 | E5:4'
# B: the cellos' contrast line, the flute's replies in its gaps
B_CELLO = ('B3:1 D4:1 G4:2 | F#4:1.5 E4:0.5 C#4:2 | A4:3 E4:1 | F#4:3 D4:1 | '
           'G4:1 F#4:1 E4:1 B4:1 | A#4:2 F#4:2 | B4:1.5 A4:0.5 G4:1 F#4:1 | E4:3 r:1')
B_FLUTE = 'r:12 r:2 D6:0.5 C#6:0.5 B5:1 | r:16 r:12 r:1 E6:0.5 D6:0.5 C#6:1 A5:1'
# the build: the head motif sequenced up, the last bar a falling run into the climax's downbeat
BUILD = ('F#4:1 B4:2 C#5:1 | D5:3 r:1 | B4:1 E5:2 F#5:1 | G5:3 r:1 | '
         'A4:1 D5:1 E5:1 F#5:1 | G5:1 A5:1 B5:2 | A5:1 B5:1 C#6:2 | F#5:2 E5:0.5 D#5:0.5 C#5:0.5 A4:0.5')
BUILD_CELLO = 'r:4 D3:1 G3:2 A3:1 | r:4 E3:1 A3:2 B3:1 | r:16'
# the A2 descant (flutes) and the climax counter-line (cellos / trombones / bassoons)
DESCANT = 'r:4 A5:4 | B5:2 A5:2 | G5:4 | r:4 | F#5:4 | D6:4 | C#6:2 A5:2 | A5:3 r:1'
COUNTER = ('E3:2 G#3:2 | C#4:2 B3:2 | A3:2 C#4:2 | D#4:2 B3:2 | G#3:2 B3:2 | A3:2 E4:2 | '
           'F#3:2 A3:1 B3:1 | E3:4')
V2_SIXTHS = 'F#4:1 A4:2 C#5:1 | D5:1 D5:1 G5:2 | E5:2 C#5:1 C#5:1 | A4:3 r:1'   # violins II under A2's 2nd phrase
CODA_OBOE = 'B4:1 E5:2 F#5:1 | E5:2 C5:2 | B4:4 | A4:2 F#4:2'


def PAD_ARC(n):
    """The held chords breathe with the 4-bar phrase: in soft, swelling to its third bar, easing at its end."""
    return (-9.0, 0.0, 8.0, -4.0)[int(n[0] // 4) % 4] + (3.0 if n[0] % 4 < 0.01 else -2.0)


def line(text, at=0.0):
    out, t = [], at
    for tok in text.replace('|', ' ').split():
        p, d = tok.split(':')
        d = float(d)
        if p != 'r':
            out.append((t, d, note(p)))
        t += d
    return out


def shift(notes, semis):
    return [(a, d, p + semis) for a, d, p in notes]


def chart(sec):
    """[(beat, beats, symbol)] of a section in song beats."""
    out = []
    for i, bar in enumerate(CHART[sec.name]):
        syms = bar.split()
        for j, sym in enumerate(syms):
            out.append((sec.start + 4 * i + j * 4 / len(syms), 4 / len(syms), sym))
    return out


def merge(ev):
    """Join repeated chords (G/D after G/D) into one event."""
    out = []
    for a, d, sym in ev:
        if out and out[-1][2] == sym and abs(out[-1][0] + out[-1][1] - a) < 1e-6:
            out[-1] = (out[-1][0], out[-1][1] + d, sym)
        else:
            out.append((a, d, sym))
    return out


def voices(ev, starts, lo, hi, need3=True):
    """Voice-led pad: each voice moves to the nearest chord tone (in lo..hi); the third / seventh kept present.
    starts: the voices' first pitches (top first). Returns a list of notes per voice."""
    lo, hi = note(lo), note(hi)
    cur = [note(x) for x in starts]
    parts = [[] for _ in cur]
    for a, d, sym in ev:
        c = _chord(sym)
        pcs = sorted(c.pcs)
        third = next((p for p in pcs if (p - c.root) % 12 in (3, 4)), None)
        cand = [p for p in range(lo, hi + 1) if p % 12 in pcs]
        new = []
        for v in cur:
            best = min(cand, key=lambda p: (abs(p - v), p in new))
            if best in new:   # no unisons inside one pad
                alts = [p for p in cand if p not in new] or cand
                best = min(alts, key=lambda p: abs(p - v))
            new.append(best)
        if need3 and third is not None and any(p % 12 == third for p in cand) and all(p % 12 != third for p in new) and len(new) > 1:
            # the voice closest to a third takes it (never the top voice)
            k = min(range(1, len(new)), key=lambda i: min(abs(p - new[i]) for p in cand if p % 12 == third))
            new[k] = min((p for p in cand if p % 12 == third), key=lambda p: abs(p - new[k]))
        for i, p in enumerate(new):
            parts[i].append((a, d, p))
        cur = new
    return parts


def bass(ev, octave, sus=True):
    """The bass note (the slash bass or the root) per event, in the given octave (2 = C2..B2)."""
    out = []
    for a, d, sym in ev:
        c = _chord(sym)
        pc = c.bass_pc if c.bass_pc is not None else c.root
        out.append((a, d, 12 * (octave + 1) + pc))
    return out


def arp(ev, lo, step=0.5, shape=(0, 1, 2, 3, 2, 1, 2, 3), span=4):
    """A harp / viola broken-chord figure: the chord's tones from `lo` up, walked by `shape` in `step` beats."""
    out = []
    lo = note(lo)
    for a, d, sym in ev:
        c = _chord(sym)
        bp = c.bass_pc if c.bass_pc is not None else c.root
        tones = sorted({p for p in range(lo, lo + 24) if p % 12 in c.pcs})
        first = next(p for p in range(lo, lo + 12) if p % 12 == bp)
        seq = [first] + [p for p in tones if p > first][:span]
        n = int(round(d / step))
        for i in range(n):
            out.append((a + i * step, step * 1.6, seq[shape[i % len(shape)] % len(seq)]))
    return out


def held(ev, every=None):
    """Chord events cut into phrase-length breaths for winds (a short gap before each new event)."""
    return [(a, d - 0.25, p) for a, d, p in ev]


DYN = {
    'intro': [(0, 'pp'), (8, 34), (14, 'p'), (16, 36)],
    'A': [(0, 'p'), (12, 48), (16, 42), (24, 56), (28, 50), (32, 44)],
    'B': [(0, 'p'), (8, 52), (16, 'mp'), (20, 64), (28, 56), (32, 50)],
    'A2': [(0, 'mp'), (12, 66), (16, 60), (24, 74), (28, 68), (32, 64)],
    'build': [(0, 'mp'), (16, 'mf'), (24, 88), (32, 108)],
    'climax': [(0, 'ff'), (12, 108), (16, 112), (20, 118), (28, 104), (32, 88)],
    'A3': [(0, 'p', 'subito'), (12, 44), (16, 'p'), (24, 50), (32, 38)],
    'coda': [(0, 38), (8, 'pp'), (16, 30)],
    'end': [(0, 30), (8, 'ppp')],
}


def build() -> Song:
    s = Song(METADATA['title'], tempo=TEMPO, key=KEY, seed=SEED, tail=8)
    S = {name: s.section(name, bars=bars) for name, bars in FORM}
    intro, A, B, A2, bld, cl, A3, coda, end = (S[n] for n, _ in FORM)

    # ------------------------------------------------------------------------------------------ time
    s.set_tempo(intro, 66)
    s.set_tempo(A, TEMPO)
    s.ritardando((B.bar(7), B.end), to=0.9, a_tempo=True)
    s.ritardando((bld.bar(7), bld.end), to=0.93, a_tempo=True)
    s.ritardando((cl.bar(6) + 2, cl.end), to=0.82, a_tempo=False)
    s.set_tempo(A3, 68)
    s.ritardando((coda.bar(2), coda.end), to=0.8, a_tempo=False)
    s.fermata(end.start, hold=3.0)

    b = orchestra_band(s, ROLES)
    sc = orch.Score(s, b, DYN, key=KEY, seed=SEED, style='film')

    ev = {n: chart(S[n]) for n, _ in FORM}
    s.endless_timeline = [x for n, _ in FORM for x in ev[n]]
    me = {n: merge(ev[n]) for n in ev}

    # ============================================================================ intro: dawn, pp
    i0 = intro.start
    v2, va1, va2 = voices(me['intro'], ('F#4', 'D4', 'A3'), 'G3', 'A4')
    sc.add('violins2', v2, off=-4, offs=PAD_ARC)
    sc.add('violas', va2, off=-6, offs=PAD_ARC)
    sc.add('cellos', [(i0, 16, note('D3'))], off=-4)
    sc.add('basses', [(i0 + 8, 8, note('D2'))], off=-8)
    sc.add('harp', arp(me['intro'], 'D3', step=0.5, shape=(0, 2, 3, 4, 3, 2, 1, 2)), None, off=-6)
    sc.add('flutes', line('r:8 A4:1 D5:1 E5:1 F#5:1 | E5:3.5', i0), off=2, line=True)

    # ============================================================================ A: the theme on the oboe
    a0 = A.start
    sc.add('oboes', line(THEME, a0), off=10, line=True)
    v2, va1, va2 = voices(me['A'], ('D4', 'A3', 'F#3'), 'D3', 'G4')
    sc.add('violins2', v2, off=-12, offs=PAD_ARC)
    sc.add('violas', va1 + va2, off=-9, offs=PAD_ARC)
    sc.add('cellos', bass(me['A'], 2), off=-6)
    sc.add('basses', bass(me['A'], 1)[4:], off=-8)
    sc.add('harp', arp(me['A'], 'D3', step=1.0, shape=(0, 1, 2, 3)), None, off=-6)
    # the clarinets' soft thirds under the second phrase (breathing at the bar line of the cadence)
    c1, c2 = voices(merge(ev['A'][4:]), ('A4', 'F#4'), 'D4', 'B4')
    sc.add('clarinets', held(c1) + held(c2), off=-8)

    # ============================================================================ B: the cellos sing, horns hold
    b0 = B.start
    sc.add('cellos', line(B_CELLO, b0), off=6, line=True)
    sc.add('clarinets', shift(line(B_CELLO, b0), 12)[8:], off=-2, line=True)   # the answer doubled an octave up
    sc.add('flutes', line(B_FLUTE, b0), off=-2)
    v2a, v2b, va = voices(me['B'], ('D5', 'B4', 'G4'), 'F#4', 'E5')
    sc.add('violins2', v2a + v2b, off=-11, offs=PAD_ARC)
    sc.add('violas', va, off=-10, offs=PAD_ARC)
    h1, h2 = voices(me['B'], ('B3', 'G3'), 'E3', 'D4')
    sc.add('horns', held(h1) + held(h2), off=-16, offs=PAD_ARC)
    sc.add('basses', [(a, 1.0, p) for a, d, p in bass(me['B'], 2)] +
           [(a + 2, 1.0, p) for a, d, p in bass(me['B'], 2) if d >= 4], 'pizzicato', off=-2)
    sc.add('harp', [(a + k, 2.2, p) for a, d, p in bass(me['B'], 3) for k in range(0, int(d), 2)], None, off=-8)

    # ============================================================================ A2: violins take the theme
    c0 = A2.start
    th2 = line(THEME2, c0)
    sc.add('violins1', th2, off=8, line=True)
    sc.add('violins2', line(V2_SIXTHS, c0 + 16), off=0, phrasing=1.5)
    sc.add('flutes', line(DESCANT, c0), off=-2, line=True)
    sc.add('violins2', voices(me['A2'][:5], ('A4',), 'F#4', 'B4')[0], off=-6, offs=PAD_ARC)
    sc.add('violas', arp(me['A2'], 'D3', step=0.5, shape=(0, 1, 2, 1, 3, 1, 2, 1)), off=-4)
    sc.add('cellos', bass(me['A2'], 2), off=-2)
    sc.add('basses', bass(me['A2'], 1), off=-6)
    h1, h2 = voices(me['A2'], ('F#4', 'D4'), 'A3', 'G4')
    sc.add('horns', held(h1) + held(h2), off=-8, offs=PAD_ARC)
    sc.add('bassoons', held(bass(me['A2'], 2)), off=-10)
    sc.add('harp', arp(me['A2'], 'D4', step=1.0, shape=(0, 1, 2, 3)), None, off=-8)

    # ============================================================================ build: the sequence climbs
    d0 = bld.start
    bl = line(BUILD, d0)
    sc.add('violins1', bl, off=4, line=True)
    sc.add('oboes', [n for n in bl if n[0] < d0 + 16], off=-4)
    sc.add('flutes', [n for n in bl if n[0] >= d0 + 16 and n[1] >= 1], off=-2)
    sc.add('cellos', line(BUILD_CELLO, d0), off=4)
    v2a, v2b, va1, va2 = voices(me['build'], ('D5', 'B4', 'F#4', 'D4'), 'C#4', 'E5')
    sc.add('violins2', v2a + v2b, 'tremolo', off=-6, offs=PAD_ARC)
    sc.add('violas', va1 + va2, 'tremolo', off=-6, offs=PAD_ARC)
    sc.add('cellos', [n for n in bass(me['build'], 2) if n[0] >= d0 + 16], 'tremolo', off=-2)
    sc.add('basses', bass(me['build'], 1), off=-4)
    sc.add('clarinets', held(voices(me['build'], ('B4',), 'G4', 'C#5')[0]), off=-8)
    h1, h2, h3 = voices(me['build'][4:], ('D4', 'A3', 'F#3'), 'E3', 'E4')
    sc.add('horns', held(h1) + held(h2) + held(h3), off=-6, offs=PAD_ARC)
    sc.add('bassoons', held(bass(me['build'], 2)), off=-8)
    sc.add('trombones', [(d0 + 24, 3.5, note('F#3')), (d0 + 24, 3.5, note('A3')),
                         (d0 + 28, 3.8, note('B2')), (d0 + 28, 3.8, note('A3'))], off=-10)
    sc.add('tuba', [(d0 + 28, 3.8, note('B1'))], off=-10)
    # the timpani's roll on F# then B into the climax; the suspended cymbal swells into the downbeat
    sc.add('timpani', [(d0 + 24, 3.8, note('F#2')), (d0 + 28, 4, note('B2'))], 'roll', off=-12)
    sc.add('percussion', [(cl.start - 3.9, 4.2, orch.PERCUSSION_KEYS['cymbal_roll'])], None, off=-14)
    sc.add('harp', [(cl.start - 1.5 + 1.5 * i / 14, 0.6, note(x)) for i, x in enumerate(
        'B2 C#3 D#3 E3 F#3 G#3 A3 B3 C#4 D#4 E4 F#4 G#4 A4'.split())], None, off=-6)

    # ============================================================================ climax: the only tutti, E major
    e0 = cl.start
    top = line(CLIMAX, e0)
    sc.add('violins1', top, off=8, line=True)
    sc.add('trumpets', [n for n in top if n[0] < e0 + 28], off=-2, line=True)
    sc.add('flutes', top, off=0, line=True)
    sc.add('oboes', top, off=-4)
    sc.add('violins2', shift(top, -12), off=2, phrasing=1.5)
    sc.add('horns', shift(top, -12), off=0, line=True)
    sc.add('clarinets', shift(top, -12), off=-6)
    sc.add('cellos', line(COUNTER, e0), off=4, line=True)
    sc.add('trombones', line(COUNTER, e0)[:-1], off=-6)
    sc.add('bassoons', line(COUNTER, e0), off=-6)
    va1, va2 = voices(me['climax'], ('B3', 'G#3'), 'E3', 'C#4')
    sc.add('violas', va1 + va2, off=-2, offs=PAD_ARC)
    sc.add('basses', bass(me['climax'], 1), off=0)
    sc.add('tuba', held(bass(me['climax'], 1)), off=-6)
    sc.add('trombones', [(e0 + 28, 4, note('E3')), (e0 + 28, 4, note('G#3'))], off=-8)
    sc.add('timpani', [(e0, 1, note('E2')), (e0 + 2, 1, note('B2')), (e0 + 16, 1, note('E2')),
                       (e0 + 20, 1, note('A2')), (e0 + 26, 1, note('B2'))], 'hit', off=-12)
    sc.add('timpani', [(e0 + 28, 4, note('E2'))], 'roll', off=-10)
    sc.add('percussion', [(e0, 4, orch.PERCUSSION_KEYS['crash']),
                          (e0 + 16, 4, orch.PERCUSSION_KEYS['sus_cymbal'])], None, off=-10)
    sc.add('harp', arp(me['climax'], 'E3', step=0.5, shape=(0, 1, 2, 3, 4, 3, 2, 1)), None, off=-4)

    # ============================================================================ A3: the quiet return, the horn
    f0 = A3.start
    sc.add('horns', line(RET_HORN, f0), off=10, line=True)
    sc.add('flutes', line(RET_FLUTE, f0), off=12, line=True)
    v2a, v2b, va = voices(me['A3'], ('G#4', 'E4', 'B3'), 'G#3', 'B4')
    sc.add('violins2', v2a + v2b, off=-13, offs=PAD_ARC)
    sc.add('violas', va, off=-9, offs=PAD_ARC)
    sc.add('cellos', bass(me['A3'], 2), off=-6)
    sc.add('basses', [n for n in bass(me['A3'], 1) if n[0] >= f0 + 16], off=-8)
    sc.add('harp', arp(me['A3'], 'E3', step=1.0, shape=(0, 1, 2, 3)), None, off=-8)
    sc.add('clarinets', held(voices(merge(ev['A3'][:4]), ('G#4',), 'E4', 'B4')[0]), off=-10)

    # ============================================================================ coda + the held chord
    g0 = coda.start
    sc.add('oboes', line(CODA_OBOE, g0), off=4, line=True)
    v1, v2, va = voices(me['coda'], ('C#5', 'G#4', 'E4'), 'D#4', 'D5')
    sc.add('violins1', v1, off=-6)
    sc.add('violins2', v2, off=-6, offs=PAD_ARC)
    sc.add('violas', va, off=-6, offs=PAD_ARC)
    sc.add('cellos', bass(me['coda'], 2), off=-4)
    sc.add('basses', bass(me['coda'], 1)[2:], off=-10)
    sc.add('clarinets', [(g0 + 4, 3.5, note('C4')), (g0 + 4, 3.5, note('E4'))], off=-8)    # the borrowed iv's colour

    h0 = end.start
    sc.add('violins1', [(h0, 8, note('G#5')), (h0, 8, note('B4'))], off=-6)
    sc.add('violins2', [(h0, 8, note('F#4')), (h0, 8, note('E4'))], off=-6, offs=PAD_ARC)
    sc.add('violas', [(h0, 8, note('B3')), (h0, 8, note('G#3'))], off=-6)
    sc.add('cellos', [(h0, 8, note('E3')), (h0, 8, note('B2'))], off=-4)
    sc.add('basses', [(h0, 8, note('E2'))], off=-8)
    sc.add('horns', [(h0, 7.5, note('E4')), (h0, 7.5, note('B3'))], off=-10)
    sc.add('flutes', [(h0, 7.5, note('B5'))], off=-8)
    sc.add('harp', [(h0 + 0.12 * i, 7.5, note(x)) for i, x in enumerate(
        'E2 B2 E3 G#3 B3 F#4 G#4 B4 E5'.split())], None, off=6)

    sc.perform()
    return s
