"""The River Below the Hills - an original tone poem for full orchestra: a river's journey from its source to the plain.
Build: python -m agentsound build songs/pro-orch-symphonic-river

A composed ("pro") reference for the endless orchestra genres, played by the SAME band setup as an endless piece
(agentsound.endless.orchestra.band), so only the writing differs. D minor -> D major, 6/8 (a bar = 3 quarter beats),
q = 104 (the dotted quarter ~ 70, about 35 bars a minute); the night slower (88), the rapids faster (114).

  section   bars  key        what happens
  source      8   D minor    two flutes: two running 16th rivulets in contrary motion (the second enters in bar 3);
                             the clarinets join in bar 5 with a rocking 8th figure, violin / harp pizzicato drops
  stream      8   D minor    the strings take the stream (violins II, then the violas a second current under it),
                             pizzicato bass on the dotted quarters, the horns' first held chord; the flutes leave
  theme      16   D minor    the RIVER THEME in the violins I (clarinets an octave under; the oboe joins at the
                             answer): D-C#-D-E | F held | down to the half cadence on A; again, then the leap F5 ->
                             D6 and the held D6, cadence in F; the answering phrase down to the D minor close
  bridge      8   Dm -> F    the theme's head handed down: cellos (D), bassoons + clarinets (G), violins II (F),
                             a distant horn foretells the hunt; the stream thins to the violas
  hunt       16   F major    the hunting call: the head turned major (F-E-F-G-A) for two horns in sixths over
                             galloping strings (quarter-eighth), woodwind 16th flourishes; the trumpets answer in
                             D minor, then horns + trumpets in octaves ff
  dusk        4   F -> Bb    the hunt fades: a horn echo pp, the stream slows to 8ths, ritardando
  nocturne   16   Bb major   night on the water: high violins sing the head in augmentation (Bb-A-Bb-C-D) over
                             held high strings, harp arpeggios, the clarinets' murmuring 16ths; the flute and a
                             clarinet in Gb major (bVI), the violins lead back to A7; timpani roll, accelerando
  storm      20   D minor    the rapids: subito f, the strings racing 16ths, the head sequenced by brass up by
                             semitones (Dm, Eb, Em, F), fragments tossed between winds and strings with subito p /
                             ff, the theme in augmentation in trombones / tuba / cellos, the A pedal tremolo ff,
                             cymbal roll
  river      16   D major    the broad return: the river theme in the major, tutti (violins I + flutes + oboes at
                             pitch, violins II + trumpets + horns an octave under, the violas keep the stream,
                             cellos the counter-line), the minor iv (Gm6) on the last climb, allargando
  coda        8   D major    the river leaves: the flutes' stream once more, the horn's head, the clarinet's sigh
                             Bb-A (Gm6/D), a last crescendo to the held D major chord

THE RIVER THEME (at the violins' pitch, 6/8, beats = quarters):
  D5:1 C#5:.5 D5:1 E5:.5 | F5:1.5 E5:1 D5:.5 | G5:1 F5:.5 E5:1 D5:.5 | C#5:1.5 A4:1.5 |
  D5:1 C#5:.5 D5:1 E5:.5 | F5:1.5 D6:1.5 (the leap) | D6:1.5 (the held peak) C6:1 Bb5:.5 | A5:1 G5:.5 F5:1.5 ||
  Bb5:1 A5:.5 G5:1 F5:.5 | E5:1.5 A5:1.5 | F5:1 E5:.5 D5:1 C5:.5 | Bb4:1.5 G5:1.5 |
  G5:1.5 F5:1 E5:.5 | F5:1 E5:.5 D5:1 C#5:.5 | E5:1.5 A4:1 C#5:.5 | D5:3

CREDITS: Sonatina Symphonic Orchestra 4.0, VSCO 2 CE (see the build's credits).
"""
import math

from agentsound import *
from agentsound.theory import chord as _chord, note as _note, voice_lead
from agentsound.bandlib import orchestra as orch
from agentsound.endless.orchestra import band as orchestra_band

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'The River Below the Hills', 'artist': 'AgentSound', 'album': 'Orchestral References',
            'genre': 'Classical', 'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#16303a', '#9cc7c2'], 'title': 'THE RIVER BELOW THE HILLS',
         'subtitle': 'AgentSound - Orchestral References', 'seed': 68}

KEY = 'D minor'
TEMPO = 104
SEED = 68
BAR = 3.0                       # a 6/8 bar in quarter beats
ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
         'trumpets', 'trombones', 'tuba', 'harp', 'timpani', 'percussion')

FORM = [('source', 8), ('stream', 8), ('theme', 16), ('bridge', 8), ('hunt', 16), ('dusk', 4), ('nocturne', 16),
        ('storm', 20), ('river', 16), ('coda', 8)]

# ------------------------------------------------------------------------------------------------ harmony
CHART = {
    'source': 'Dm | Dm | Gm/D | Dm | Bb | Gm6/Bb | A7sus4:1.5 A7:1.5 | Dm',
    'stream': 'Dm | Dm/C | Bb | Gm6/Bb | Dm/A | Bb:1.5 Gm/Bb:1.5 | Em7b5:1.5 A7:1.5 | A7',
    'theme': 'Dm | Dm | Gm:1.5 A7:1.5 | A | Dm | Dm:1.5 Bb:1.5 | Gm7:1.5 C7:1.5 | F | '
             'Gm7 | A7 | Dm:1.5 F/C:1.5 | Gm/Bb | Em7b5:1.5 A7:1.5 | Bb:1.5 A7:1.5 | A7 | Dm',
    'bridge': 'Dm | Bb | Gm | C7 | F/A | Dm | Gm7:1.5 C7:1.5 | C7',
    'hunt': 'F | F | Bb:1.5 C7:1.5 | F | F | F:1.5 Gm:1.5 | C:1.5 C7:1.5 | F | '
            'Dm | Dm | Bb:1.5 C:1.5 | F | F | F:1.5 Gm:1.5 | C:1.5 C7:1.5 | F',
    'dusk': 'F | Dm | Gm7 | F7',
    'nocturne': 'Bb | Bb | Eb/G | Gm | Cm7 | F7 | Bb | Bb | Gb | Gb | Ebm | F7 | Bb | Gm | Em7b5 | A7',
    'storm': 'Dm | Dm | Eb | Eb | Em | Em | F | C#dim7 | Gm | A7 | Gm | A7 | '
             'Dm:1.5 A/C#:1.5 | Dm:1.5 Am/E:1.5 | Bb/F | A7/E | A7 | Gm/A | A7 | A7',
    'river': 'D | D | G:1.5 A7:1.5 | A | D | D:1.5 Bm:1.5 | G:1.5 A:1.5 | Bm:1.5 D/F#:1.5 | '
             'Gmaj7 | Em7:1.5 A7:1.5 | D:1.5 A/C#:1.5 | Bm:1.5 G:1.5 | Gm6:1.5 A7:1.5 | D/A:1.5 A7:1.5 | '
             'A7sus4:1.5 A7:1.5 | D',
    'coda': 'D | D | Gm6/D | D | G:1.5 Em7:1.5 | A7sus4:1.5 A7:1.5 | D | D',
}
SCALE = {'source': 'Dm', 'stream': 'Dm', 'theme': 'Dm', 'bridge': 'Dm', 'hunt': 'F', 'dusk': 'F', 'nocturne': 'Bb',
         'storm': 'Dm', 'river': 'D', 'coda': 'D'}
SCALES = {'Dm': (2, 4, 5, 7, 9, 10, 0), 'D': (2, 4, 6, 7, 9, 11, 1), 'F': (5, 7, 9, 10, 0, 2, 4),
          'Bb': (10, 0, 2, 3, 5, 7, 9)}

# ------------------------------------------------------------------------------------------------ the themes
THEME = ['D5:1 C#5:0.5 D5:1 E5:0.5', 'F5:1.5 E5:1 D5:0.5', 'G5:1 F5:0.5 E5:1 D5:0.5', 'C#5:1.5 A4:1.5',
         'D5:1 C#5:0.5 D5:1 E5:0.5', 'F5:1.5 D6:1.5', 'D6:1.5 C6:1 Bb5:0.5', 'A5:1 G5:0.5 F5:1.5',
         'Bb5:1 A5:0.5 G5:1 F5:0.5', 'E5:1.5 A5:1.5', 'F5:1 E5:0.5 D5:1 C5:0.5', 'Bb4:1.5 G5:1.5',
         'G5:1.5 F5:1 E5:0.5', 'F5:1 E5:0.5 D5:1 C#5:0.5', 'E5:1.5 A4:1 C#5:0.5', 'D5:3']
# the apotheosis in D major: the same profile, the peak D6 over G, the minor iv (Gm6) on the last climb
THEME_MAJOR = ['D5:1 C#5:0.5 D5:1 E5:0.5', 'F#5:1.5 E5:1 D5:0.5', 'G5:1 F#5:0.5 E5:1 D5:0.5', 'C#5:1.5 A4:1.5',
               'D5:1 C#5:0.5 D5:1 E5:0.5', 'F#5:1.5 D6:1.5', 'D6:1.5 C#6:1 B5:0.5', 'A5:1 G5:0.5 F#5:1.5',
               'B5:1 A5:0.5 G5:1 F#5:0.5', 'E5:1.5 A5:1.5', 'F#5:1 E5:0.5 D5:1 C#5:0.5', 'B4:1.5 G5:1.5',
               'G5:1.5 F#5:1 E5:0.5', 'F#5:1 E5:0.5 D5:1 C#5:0.5', 'E5:2 D5:0.5 C#5:0.5', 'D5:3']
# the river return's counter-line (cellos, violas an octave up in the second half)
COUNTER_MAJOR = ['D3:3', 'A3:1.5 B3:1.5', 'B3:1.5 C#4:1.5', 'E4:1.5 C#4:1.5', 'D4:1.5 A3:1.5', 'A3:1.5 B3:1.5',
                 'B3:1.5 A3:1.5', 'B3:1.5 A3:1.5', 'G3:1.5 B3:1.5', 'G3:1.5 C#4:1.5', 'D4:1.5 E4:1.5',
                 'D4:1.5 B3:1.5', 'Bb3:1.5 G3:1.5', 'A3:1.5 G3:1.5', 'G3:1.5 G3:1.5', 'F#3:3']
# bridge: the head handed down through the orchestra
HEAD_CELLO = ['D3:1 C#3:0.5 D3:1 E3:0.5', 'F3:3']
HEAD_BSN = ['G3:1 F#3:0.5 G3:1 A3:0.5', 'Bb3:3']
HEAD_VN2 = ['F4:1 E4:0.5 F4:1 G4:0.5', 'A4:3']
HORN_FORETELL = ['C4:1.5 F4:1.5', 'E4:1 G4:0.5 C4:1.5']
# hunt: the call (the head turned major) for two horns in sixths, then the trumpets in D minor, then both ff
CALL1 = ['C4:1 F4:0.5 F4:1 G4:0.5', 'A4:1 F4:0.5 C5:1.5', 'Bb4:1 A4:0.5 G4:1 E4:0.5', 'F4:1.5 r:1 C4:0.5',
         'F4:1 E4:0.5 F4:1 G4:0.5', 'A4:1 Bb4:0.5 D5:1.5', 'C5:1 A4:0.5 G4:1 E4:0.5', 'F4:3']
CALL2 = ['A3:1 C4:0.5 C4:1 E4:0.5', 'F4:1 C4:0.5 A4:1.5', 'G4:1 F4:0.5 E4:1 C4:0.5', 'A3:1.5 r:1.5',
         'A3:1 G3:0.5 A3:1 Bb3:0.5', 'C4:1 D4:0.5 Bb4:1.5', 'E4:1 F4:0.5 E4:1 C4:0.5', 'A3:3']
TRUMPET_CALL = ['A4:1 D5:0.5 D5:1 E5:0.5', 'F5:1 D5:0.5 A4:1.5', 'Bb4:1 A4:0.5 G4:1 E4:0.5', 'F4:1.5 r:1 C4:0.5']
CALL_FF = ['F4:1 E4:0.5 F4:1 G4:0.5', 'A4:1 Bb4:0.5 D5:1.5', 'C5:1 A4:0.5 G4:1 E4:0.5', 'F4:3']
DUSK_HORN = ['C4:1 F4:0.5 F4:1.5', 'r:3', 'C4:1 F4:0.5 E4:1.5', 'r:3']
# nocturne: the head in augmentation, high violins; the flute in Gb; the violins lead back to A7
NOC_VN = ['D5:1.5 F5:1.5', 'Bb5:2 A5:1', 'Bb5:2 C6:1', 'D6:3', 'Eb6:1.5 D6:1 C6:0.5', 'C6:1.5 Bb5:1 A5:0.5',
          'Bb5:3', 'r:3']
NOC_FL = ['Db6:2 Bb5:1', 'Gb5:3', 'Gb5:1.5 F5:1 Eb5:0.5', 'F5:3']
NOC_VN2 = ['D5:1.5 F5:1.5', 'Bb5:2 A5:1', 'G5:1.5 E5:1.5', 'C#5:3']
# storm: the head sequenced up by semitones (brass), fragments, the theme in augmentation in the bass
STORM_HEAD = [['D4:1 C#4:0.5 D4:1 E4:0.5', 'F4:3'], ['Eb4:1 D4:0.5 Eb4:1 F4:0.5', 'G4:3'],
              ['E4:1 D#4:0.5 E4:1 F#4:0.5', 'G4:3'], ['F4:1 E4:0.5 F4:1 G4:0.5', 'A4:1.5 Bb4:1.5']]
STORM_FRAG_WW = ['D5:1 C#5:0.5 D5:1.5', 'r:3', 'Bb5:1 A5:0.5 Bb5:1.5', 'r:3']
STORM_FRAG_VN = ['r:3', 'E5:1 D5:0.5 C#5:1.5', 'r:3', 'C#6:1 Bb5:0.5 A5:1.5']
STORM_BASS = ['D3:1.5 C#3:1.5', 'D3:1.5 E3:1.5', 'F3:3', 'E3:3']
STORM_TPT = ['A4:1 A4:0.5 C#5:1.5', 'D5:1 C#5:0.5 A4:1.5', 'A4:1 C#5:0.5 E5:1.5', 'E5:3']
# coda
CODA_HORN = ['D4:1 C#4:0.5 D4:1 E4:0.5', 'F#4:3']
CODA_CL = ['Bb4:1.5 A4:1.5', 'A4:3']

DYN = {
    'source': [(0, 'pp'), (5, 'p'), (6, 'pp'), (11, 'p'), (12, 'p'), (17, 'mp'), (18, 'p'), (23, 'mp'), (24, 'mp')],
    'stream': [(0, 'p'), (5, 'mp'), (9, 'p'), (14, 'mp'), (18, 'mp'), (24, 'mf')],
    'theme': [(0, 'mp'), (5, 'mf'), (9, 'mp'), (12, 'mp'), (16, 'mf'), (19, 'f'), (24, 'mf'), (29, 'f'), (33, 'mf'),
              (36, 'mf'), (40, 'f'), (45, 'mf'), (48, 'mp')],
    'bridge': [(0, 'mp'), (9, 'mf'), (12, 'mp'), (18, 'mf'), (24, 'mp')],
    'hunt': [(0, 'mf'), (5, 'f'), (11, 'mf'), (12, 'mf'), (17, 'f'), (24, 'mp', 'step'), (29, 'mf'), (35, 'mp'),
             (36, 'f', 'step'), (42, 'ff'), (48, 'f')],
    'dusk': [(0, 'mf'), (6, 'p'), (12, 'pp')],
    'nocturne': [(0, 'pp'), (6, 'p'), (11, 'mp'), (18, 'p'), (24, 'pp'), (28, 'p'), (33, 'mp'), (36, 'p'),
                 (42, 'mp'), (48, 'f')],
    'storm': [(0, 'f', 'step'), (2, 'ff'), (6, 'f'), (8, 'ff'), (12, 'f'), (18, 'ff'), (24, 'p', 'step'),
              (27, 'ff', 'step'), (30, 'p', 'step'), (33, 'ff', 'step'), (36, 'f'), (45, 'ff'), (48, 'mf', 'step'),
              (60, 'ff')],
    'river': [(0, 'f'), (5, 'ff'), (9, 'f'), (12, 'f'), (17, 'ff'), (24, 'mf'), (29, 'f'), (33, 'mf'),
              (36, 'f'), (40, 'ff'), (45, 'fff'), (48, 'ff')],
    'coda': [(0, 'p'), (6, 'mp'), (12, 'p'), (15, 'mf'), (19, 'ff'), (24, 'f')],
}


def N(x):
    return _note(x)


def mel(t0, bars, shift=0):
    """Bars of 'pitch:beats' tokens (r = rest) from t0 -> (start, dur, pitch) notes; every bar must fill 3 beats."""
    out, t = [], t0
    for bar in bars:
        tot = 0.0
        for tok in bar.split():
            p, d = tok.split(':')
            d = float(d)
            if p != 'r':
                out.append((t + tot, d, N(p) + shift))
            tot += d
        assert abs(tot - BAR) < 1e-9, (bar, tot)
        t += BAR
    return out


def sh(notes, k):
    return [(a, d, p + k) for a, d, p in notes]


def chart(t0, text):
    out, t = [], t0
    for bar in text.split('|'):
        toks = bar.split()
        durs = [float(x.split(':')[1]) if ':' in x else None for x in toks]
        rest = (BAR - sum(d for d in durs if d)) / max(1, durs.count(None)) if None in durs else 0
        for tok, d in zip(toks, durs):
            d = d or rest
            out.append((t, d, tok.split(':')[0]))
            t += d
    return out


def chord_at(ch, t):
    for st, d, s in ch:
        if st - 1e-6 <= t < st + d - 1e-6:
            return s
    return ch[-1][2]


def tones(sym):
    c = _chord(sym)
    iv = sorted(set(c.intervals))
    third = next((i for i in (4, 3, 5, 2) if i in iv), 4)
    fifth = next((i for i in (7, 6, 8) if i in iv), 7)
    return c.root, third, fifth, (c.bass if c.bass is not None else c.root)


def pcs(sym):
    c = _chord(sym)
    return {(c.root + i) % 12 for i in c.intervals}


def low(pc, lo):
    p = N(lo)
    return p + (pc - p) % 12


def tie(notes):
    out = []
    for n in sorted(notes):
        for i, m in enumerate(out):
            if m[2] == n[2] and abs(m[0] + m[1] - n[0]) < 1e-6:
                out[i] = (m[0], m[1] + n[1], m[2])
                break
        else:
            out.append(n)
    return sorted(out)


def pad(ch, register, voices, legato=1.0):
    lo, hi = N(register[0]), N(register[1])
    vs = voice_lead([c[2] for c in ch], register=(lo, max(hi, lo + 11)), voices=voices)
    return tie([(t, d * legato, p) for (t, d, _), v in zip(ch, vs) for p in v])


def bass(ch, lo, legato=1.0, root=False):
    return tie([(t, d * legato, low(tones(s)[0] if root else tones(s)[3], lo)) for t, d, s in ch])


def scale(key, sym):
    """The key's scale with the chord's own tones (C# over A7, B over G in D minor ...)."""
    out = set(SCALES[key])
    for p in pcs(sym):
        if p not in out:
            for q in ((p + 1) % 12, (p - 1) % 12):
                if q in out:
                    out.discard(q)
                    break
            out.add(p)
    return out


UP = ([0, 1, 2, 1, 2, 3], [0, 2, 1, 3, 2, 4], [0, 1, 2, 3, 4, 2])


def stream(ch, key, t0, t1, lo, hi, phase=0.0, period=12.0, step=0.25, dur=0.28):
    """The river's running figure: groups of six 16ths (a dotted quarter) from a chord tone near a slowly waving
    centre, rising while the wave rises and falling while it falls (scale steps with the chord's alterations)."""
    lo_p, hi_p = N(lo), N(hi)
    out, t, g = [], t0, 0
    while t < t1 - 1e-6:
        sym = chord_at(ch, t)
        sc = scale(key, sym)
        ladder = [p for p in range(lo_p - 7, hi_p + 8) if p % 12 in sc]
        x = 2 * math.pi * (t - t0) / period + phase
        centre = lo_p + (hi_p - lo_p) * (0.5 + 0.42 * math.sin(x))
        rising = math.cos(x) >= 0
        ct = [p for p in ladder if p % 12 in pcs(sym)]
        start = min(ct, key=lambda p: abs(p - centre))
        i0 = ladder.index(start)
        shape = UP[g % 3]
        for k in range(6):
            tt = t + k * step
            if tt >= t1 - 1e-6:
                break
            j = i0 + (shape[k] if rising else -shape[k])
            p = ladder[max(0, min(len(ladder) - 1, j))]
            while p > hi_p + 2:
                p -= 12
            while p < lo_p - 2:
                p += 12
            out.append((tt, dur, p))
        t += 6 * step
        g += 1
    return out


def flow(t0, centre):
    """Velocity shape of a stream: the dotted-quarter pulse leans, the line swells as it climbs."""
    c = N(centre)

    def f(n):
        pos = round((n[0] - t0) % BAR, 3)
        return (6 if pos == 0 else 3 if pos == 1.5 else 0) + max(-4, min(4, (n[2] - c) * 0.4))
    return f


def lilt(t0, strong=5, mid=2):
    """6/8 accents: the bar's downbeat, the second dotted quarter."""
    def f(n):
        pos = round((n[0] - t0) % BAR, 3)
        return strong if pos == 0 else mid if pos == 1.5 else -2
    return f


def swell(t0, length, depth=10, strong=4):
    """A phrase hairpin (up to the middle of `length` beats, then back) plus the 6/8 downbeat lean."""
    def f(n):
        x = max(0.0, min(1.0, (n[0] - t0) / length))
        return depth * (math.sin(math.pi * x) - 0.5) + (strong if round((n[0] - t0) % BAR, 3) == 0 else 0)
    return f


def rock(ch, lo, step=0.5):
    """The clarinets' rocking 6/8 accompaniment: root - fifth - third per dotted quarter (8ths, legato)."""
    out = []
    for t, d, s in ch:
        r, th, fi, b = tones(s)
        rp = low(b, lo)
        pat = [0, (r + fi - b) % 12, (r + th - b) % 12 + 12]
        for k in range(int(round(d / step))):
            out.append((t + step * k, step * 1.05, rp + pat[k % 3]))
    return out


def arpeggio(ch, lo, step=0.5, ring=1.5, span=2):
    """The harp: a broken chord up (and down for a long chord) in 8ths."""
    out = []
    for t, d, s in ch:
        r, th, fi, b = tones(s)
        rp = low(r, lo)
        up = [0, fi, 12, 12 + th, 12 + fi, 24][:3 * span]
        pat = up + up[-2:0:-1]
        for k in range(int(round(d / step))):
            out.append((t + step * k, ring, rp + pat[k % len(pat)]))
    return out


def chop(notes, rhythm, unit=1.5):
    """Re-strike held notes in a rhythm per unit: [(offset, length), ...] (the gallop: [(0, 0.8), (1, 0.4)])."""
    out = []
    for st, d, p in notes:
        u = st
        while u < st + d - 1e-6:
            for a, ln in rhythm:
                if u + a < st + d - 1e-6:
                    out.append((u + a, ln, p))
            u += unit
    return out


def pulse(ch, lo, every=1.5, length=0.6, root=True):
    out = []
    for t, d, s in ch:
        p = low(tones(s)[0] if root else tones(s)[3], lo)
        k = 0
        while k * every < d - 1e-6:
            out.append((t + k * every, length, p))
            k += 1
    return out


def run(t0, start, end, key, sym, n=6, dur=0.27):
    """A 16th scale flourish from `start` to `end` (note names) in n notes."""
    sc = scale(key, sym)
    a, b = N(start), N(end)
    lad = [p for p in range(min(a, b), max(a, b) + 1) if p % 12 in sc]
    if a > b:
        lad = lad[::-1]
    idx = [round(i * (len(lad) - 1) / (n - 1)) for i in range(n)]
    return [(t0 + 0.25 * k, dur, lad[i]) for k, i in enumerate(idx)]


def build() -> Song:
    s = Song('The River Below the Hills', tempo=TEMPO, key=KEY, seed=SEED, tail=7, meter=(6, 8))
    S = {name: s.section(name, bars=bars) for name, bars in FORM}
    T = {name: S[name].start for name in S}
    CH = {name: chart(T[name], CHART[name]) for name in S}
    s.endless_timeline = [c for name, _ in FORM for c in CH[name]]

    b = orchestra_band(s, ROLES)
    b['percussion'].gain_db += 6           # the cymbals heard at the peaks
    keys = b.info['keys']
    sc = orch.Score(s, b, DYN, key=KEY, seed=SEED, style='romantic')
    add = sc.add

    # -------------------------------------------------------------------------------------- time
    s.ritardando((S['dusk'].start, S['nocturne'].start), bpm=88, a_tempo=False)
    s.accelerando((S['nocturne'].bar(13), S['storm'].start), bpm=114)
    s.ritardando((S['storm'].bar(17), S['river'].start), bpm=100, a_tempo=False)
    s.ritardando((S['river'].bar(12), S['river'].bar(15)), to=0.86, a_tempo=True)        # allargando
    s.fermata(S['river'].bar(14), hold=1.0, length=1.5)                                    # the last climb's E
    s.ritardando((S['coda'].bar(4), S['coda'].bar(6)), to=0.85, a_tempo=False)
    s.fermata(S['coda'].bar(6), hold=4.0)

    # -------------------------------------------------------------------------------------- source
    t, ch, key = T['source'], CH['source'], 'Dm'
    fl1 = stream(ch, key, t, t + 8 * BAR, 'A4', 'A5', phase=0.0)
    fl2 = stream(ch, key, t + 2 * BAR, t + 7 * BAR, 'E4', 'D5', phase=math.pi)
    add('flutes', fl1, off=2, offs=flow(t, 'D5'), line=True)
    add('flutes', fl2, off=-3, offs=flow(t, 'A4'), line=False)
    cl = rock(ch[4:], 'D3')
    add('clarinets', cl, off=-6, offs=lilt(t, 5, 2), line=False)
    drops = [(a, 0.5, p) for a, d, p in pad(ch[4:], ('A4', 'F5'), 2) for a in (a, a + 1.5) if a < S['source'].end]
    add('violins1', [n for k, n in enumerate(sorted(drops)) if k % 2 == 0], 'pizzicato', off=-6, offs=lilt(t),
        line=False)
    add('harp', [(a + 0.75, 1.5, p + 12) for a, d, p in pad(ch[4:7], ('D4', 'A4'), 1)], None, off=-8, line=False)
    add('cellos', pulse(ch[6:], 'D2', every=1.5, length=0.6), 'pizzicato', off=-6, offs=lilt(t), line=False)
    add('basses', [(T['source'] + 7 * BAR, 3, N('D2'))], 'pizzicato', off=-8, line=False)

    # -------------------------------------------------------------------------------------- stream: the strings
    t, ch = T['stream'], CH['stream']
    add('flutes', stream(ch, key, t, t + 1.5 * BAR, 'A4', 'A5', phase=0.0), off=-2, offs=flow(t, 'D5'), line=False)
    add('violins2', stream(ch, key, t, t + 8 * BAR, 'F4', 'E5', phase=0.6), off=0, offs=flow(t, 'A4'), line=False)
    add('violas', stream(ch, key, t + 2 * BAR, t + 8 * BAR, 'A3', 'G4', phase=math.pi + 0.6), off=-4,
        offs=flow(t, 'D4'), line=False)
    add('cellos', pulse(ch, 'D2', every=1.5, length=0.6, root=False), 'pizzicato', off=-2, offs=lilt(t), line=False)
    add('basses', pulse(ch[4:], 'D1', every=3, length=0.8, root=False), 'pizzicato', off=-4, line=False)
    add('horns', pad(ch[4:], ('A3', 'F4'), 2), off=-8, line=False)
    add('clarinets', rock(ch[:4], 'D3'), off=-8, offs=lilt(t, 5, 2), line=False)
    add('harp', arpeggio(ch[4:], 'D3', step=0.5, ring=1.5, span=1), None, off=-8, line=False)
    add('timpani', [(t + 6 * BAR, 3, N('A2'))], 'roll', off=-14, line=False)

    # -------------------------------------------------------------------------------------- theme
    t, ch = T['theme'], CH['theme']
    th = mel(t, THEME)
    add('violins1', th, off=7, offs=lilt(t, 3, 1), line=True)
    add('clarinets', sh(th, -12), off=-1, offs=lilt(t, 3, 1), line=True)
    add('oboes', [n for n in th if n[0] >= t + 8 * BAR - 1e-6], off=1, offs=lilt(t, 3, 1), line=True)
    add('violins2', stream(ch, key, t, t + 16 * BAR, 'D4', 'A4', phase=0.3, period=18), off=-4, offs=flow(t, 'F4'),
        line=False)
    add('violas', pad(ch, ('A3', 'F4'), 2), off=-6, line=False)
    add('cellos', bass(ch, 'D2'), off=-3, line=False)
    add('basses', [n for n in pulse(ch, 'D1', every=1.5, length=0.9, root=False)], 'pizzicato', off=-4,
        offs=lilt(t), line=False)
    add('bassoons', pad(ch[8:], ('D3', 'A3'), 1), off=-8, line=False)
    add('horns', pad(ch[5:9], ('A3', 'F4'), 2) + pad(ch[-6:], ('A3', 'F4'), 2), off=-6, line=False)
    add('harp', arpeggio(ch[:8], 'D3', step=0.5, ring=1.2, span=1), None, off=-9, line=False)
    add('flutes', [(t + 5 * BAR, 3, N('F6')), (t + 6 * BAR, 3, N('D6')), (t + 7 * BAR, 3, N('C6'))], off=-10,
        line=False)
    add('timpani', [(t + 8 * BAR - 0.5, 0.5, N('A2')), (t + 8 * BAR, 1, N('D3')), (t + 15 * BAR, 1, N('D3'))], 'hit',
        off=-8, line=False)

    # -------------------------------------------------------------------------------------- bridge: the head handed down
    t, ch = T['bridge'], CH['bridge']
    add('cellos', mel(t, HEAD_CELLO), off=5, offs=lilt(t, 3, 1), line=True)
    add('bassoons', mel(t + 2 * BAR, HEAD_BSN), off=4, offs=lilt(t, 3, 1), line=True)
    add('clarinets', mel(t + 2 * BAR, HEAD_BSN, 12), off=0, offs=lilt(t, 3, 1), line=True)
    add('violins2', mel(t + 4 * BAR, HEAD_VN2), off=5, offs=lilt(t, 3, 1), line=True)
    add('horns', mel(t + 6 * BAR, HORN_FORETELL), off=0, line=True)
    add('violas', stream(ch, key, t, t + 6 * BAR, 'A3', 'F4', phase=0.0), off=-5, offs=flow(t, 'D4'), line=False)
    add('violins1', pad(ch, ('A4', 'F5'), 2), off=-8, line=False)
    add('basses', bass(ch, 'D1'), off=-6, line=False)
    add('flutes', [(t + 6 * BAR, 3, N('G5')), (t + 7 * BAR, 3, N('Bb5'))], off=-10, line=False)

    # -------------------------------------------------------------------------------------- hunt
    t, ch, key = T['hunt'], CH['hunt'], 'F'
    add('horns', mel(t, CALL1), off=6, offs=lilt(t, 6, 3), line=True)
    add('horns', mel(t, CALL2), off=2, offs=lilt(t, 6, 3), line=False)
    gal = [(0, 0.8), (1, 0.4)]
    add('violins2', chop(pad(ch, ('C4', 'A4'), 2), gal), 'spiccato', off=-2, offs=lilt(t, 6, 3), line=False)
    add('violas', chop(pad(ch, ('F3', 'C4'), 1), gal), 'spiccato', off=-2, offs=lilt(t, 6, 3), line=False)
    add('cellos', pulse(ch, 'F2', every=1.5, length=0.5), 'staccato', off=-1, offs=lilt(t, 6, 2), line=False)
    add('basses', pulse(ch, 'F1', every=3, length=0.6), 'staccato', off=-3, offs=lilt(t, 6, 2), line=False)
    add('violins1', chop(pad(ch[:8], ('F4', 'C5'), 1), gal), 'spiccato', off=-4, offs=lilt(t, 6, 3), line=False)
    # woodwind flourishes at the phrase ends
    fl = run(t + 3 * BAR + 1.5, 'C5', 'C6', key, 'F') + run(t + 7 * BAR + 1.5, 'F5', 'F6', key, 'F')
    add('flutes', fl, off=0, offs=lambda n: (n[2] - N('C5')) * 0.4, line=False)
    add('clarinets', sh(fl, -12), off=-2, offs=lambda n: (n[2] - N('C4')) * 0.4, line=False)
    add('oboes', [(t + 1 * BAR, 1.5, N('A5')), (t + 1 * BAR + 1.5, 1.5, N('C6')), (t + 5 * BAR, 1.5, N('A5')),
                  (t + 5 * BAR + 1.5, 1.5, N('D6'))], off=-6, offs=lilt(t), line=False)
    add('timpani', [(t + k * BAR + a, 0.5, N(p)) for k, p in ((0, 'F2'), (2, 'C3'), (4, 'F2'), (6, 'C3'))
                    for a in (0, 1)], 'hit', off=-6, offs=lilt(t, 6, 0), line=False)
    # bars 9-12: the trumpets answer in D minor, the horns hold
    t9 = t + 8 * BAR
    add('trumpets', mel(t9, TRUMPET_CALL), off=4, offs=lilt(t9, 6, 3), line=True)
    add('horns', pad(ch[8:12], ('C4', 'A4'), 2), off=-6, line=False)
    add('violins1', chop(pad(ch[8:], ('A4', 'F5'), 2), gal), 'spiccato', off=-4, offs=lilt(t, 6, 3), line=False)
    add('bassoons', pulse(ch[8:12], 'D2', every=1.5, length=0.5), 'staccato', off=-6, offs=lilt(t), line=False)
    add('flutes', run(t9 + 3 * BAR + 1.5, 'C5', 'C6', key, 'F'), off=0, offs=lambda n: (n[2] - N('C5')) * 0.4,
        line=False)
    # bars 13-16: horns + trumpets in octaves, ff; the woodwinds trill-like 16ths, the timpani
    t13 = t + 12 * BAR
    cf = mel(t13, CALL_FF)
    add('horns', cf, off=4, offs=lilt(t13, 6, 3), line=True)
    add('trumpets', sh(cf, 12), off=2, offs=lilt(t13, 6, 3), line=True)
    add('trombones', pad(ch[12:], ('F2', 'A3'), 2), off=-14, offs=swell(t13, 4 * BAR, 14), line=False)
    add('tuba', bass(ch[12:], 'F1'), off=-6, line=False)
    add('oboes', pad(ch[12:], ('F4', 'C5'), 1), off=-6, line=False)
    wf = stream(ch[12:], key, t13, t13 + 3.5 * BAR, 'C5', 'C6', phase=0.0, period=6)
    add('flutes', wf, off=-2, offs=flow(t13, 'F5'), line=False)
    add('clarinets', sh(wf, -12), off=-4, offs=flow(t13, 'F4'), line=False)
    add('timpani', [(t13 + k * BAR + a, 0.5, N(p)) for k, p in ((0, 'F2'), (1, 'F2'), (2, 'C3'))
                    for a in (0, 1, 1.5)] + [(t13 + 3 * BAR, 1, N('F2'))], 'hit', off=-2, offs=lilt(t13, 8, 2),
        line=False)
    add('percussion', [(t13, 3, keys['cymbal_roll'], 96), (t13 + 3 * BAR, 3, keys['crash'], 112)], None, line=False)

    # -------------------------------------------------------------------------------------- dusk
    t, ch = T['dusk'], CH['dusk']
    add('horns', mel(t, DUSK_HORN), off=2, line=True)
    add('clarinets', [(t + 0.5 * k, 0.53, p) for k, (_, _, p) in
                      enumerate(stream(ch, 'F', t, t + 2 * BAR, 'F4', 'D5', step=0.5))], off=-2,
        offs=flow(t, 'A4'), line=False)
    add('flutes', [(t + 2 * BAR + 0.5 * k, 0.53, p) for k, (_, _, p) in
                   enumerate(stream(ch[2:], 'F', t + 2 * BAR, t + 3.5 * BAR, 'A4', 'F5', step=0.5))], off=-4,
        offs=flow(t, 'C5'), line=False)
    add('violins1', pad(ch, ('C5', 'A5'), 2), off=-6, line=False)
    add('violas', pad(ch, ('A3', 'F4'), 2), off=-6, line=False)
    add('cellos', bass(ch, 'F2'), off=-6, line=False)

    # -------------------------------------------------------------------------------------- nocturne
    t, ch, key = T['nocturne'], CH['nocturne'], 'Bb'
    add('violins1', mel(t, NOC_VN), off=6, line=True)
    add('flutes', mel(t + 8 * BAR, NOC_FL), off=6, line=True)
    add('clarinets', mel(t + 8 * BAR, NOC_FL, -12), off=0, line=True)
    add('violins1', mel(t + 12 * BAR, NOC_VN2), off=6, line=True)
    add('violins2', pad(ch, ('F4', 'D5'), 2), off=-7, line=False)
    add('violas', pad(ch, ('Bb3', 'F4'), 2), 'tremolo', off=-9, line=False)
    add('cellos', bass(ch, 'Bb2'), off=-6, line=False)
    add('basses', bass(ch[8:], 'Bb1'), off=-10, line=False)
    add('harp', arpeggio(ch, 'Bb2', step=0.5, ring=2.0, span=2), None, off=-4, offs=lilt(t, 3, 1), line=False)
    add('clarinets', stream(ch[:8], key, t, t + 8 * BAR, 'D4', 'Bb4', phase=0.0, period=18), off=-8,
        offs=flow(t, 'F4'), line=False)
    add('horns', pad(ch[4:8], ('F3', 'D4'), 2) + pad(ch[12:], ('E3', 'C#4'), 2), off=-8, line=False)
    add('flutes', [(t + 4 * BAR, 3, N('G6')), (t + 5 * BAR, 3, N('F6'))], off=-12, line=False)
    add('timpani', [(t + 14 * BAR, 6, N('A2'))], 'roll', off=-6, line=False)

    # -------------------------------------------------------------------------------------- storm: the rapids
    t, ch, key = T['storm'], CH['storm'], 'Dm'
    # bars 1-8: the head sequenced up by brass, the strings racing
    for k, frag in enumerate(STORM_HEAD):
        notes = mel(t + 2 * k * BAR, frag)
        if k < 2:
            add('trombones', notes, off=-10, offs=lilt(t, 12, 4), line=True)
            add('horns', sh(notes, 12) if k == 0 else notes, off=4, offs=lilt(t, 6, 2), line=True)
        else:
            add('trumpets', notes, off=5, offs=lilt(t, 6, 2), line=True)
            add('horns', notes, off=3, offs=lilt(t, 6, 2), line=True)
    add('violins1', stream(ch[:8], key, t, t + 8 * BAR, 'A4', 'A5', phase=0.0, period=6, dur=0.26), off=-1,
        offs=flow(t, 'D5'), line=False)
    add('violins2', stream(ch[:8], key, t, t + 8 * BAR, 'D4', 'D5', phase=math.pi, period=6, dur=0.26), off=-2,
        offs=flow(t, 'G4'), line=False)
    add('violas', pad(ch[:8], ('A3', 'F4'), 2), 'tremolo', off=-4, line=False)
    add('cellos', pad(ch[:8], ('D3', 'A3'), 2), 'tremolo', off=-3, line=False)
    add('basses', pulse(ch[:8], 'D1', every=1.5, length=1.2), 'marcato', off=0, offs=lilt(t, 8, 2), line=False)
    add('bassoons', pulse(ch[:8], 'D2', every=1.5, length=1.0), off=-6, offs=lilt(t, 12, 2), line=False)
    add('timpani', [(t + k * BAR, 2.5, N('D3'), 100 - 4 * k) for k in (0, 1)] + [(t + 6 * BAR, 0.5, N('A2'), 92),
                    (t + 6 * BAR + 1, 0.5, N('A2'), 80), (t + 6 * BAR + 1.5, 1, N('D3'), 104)], 'roll', line=False)
    add('percussion', [(t, 3, keys['crash'], 118), (t, 2, keys['bass_drum'], 112), (t + 4 * BAR, 2, keys['crash'], 104),
                       (t + 4 * BAR, 2, keys['bass_drum'], 100)], None, line=False)
    ww = stream(ch[:8], key, t + 4 * BAR, t + 8 * BAR, 'D5', 'D6', phase=0.5, period=6)
    add('flutes', ww, off=-4, offs=flow(t, 'A5'), line=False)
    add('oboes', pad(ch[:8], ('D5', 'A5'), 1), off=-6, line=False)
    add('clarinets', pad(ch[:8], ('D4', 'A4'), 2), off=-6, line=False)
    # bars 9-12: the fragments, subito p / ff
    t9 = t + 8 * BAR
    fr = mel(t9, STORM_FRAG_WW)
    add('oboes', fr, off=4, offs=lilt(t9, 5, 2), line=True)
    add('flutes', sh(fr, 12), off=0, offs=lilt(t9, 5, 2), line=True)
    fv = mel(t9, STORM_FRAG_VN)
    add('violins1', fv, off=6, offs=lilt(t9, 6, 2), line=True)
    add('violins2', sh(fv, -12), off=3, offs=lilt(t9, 6, 2), line=True)
    add('violas', pad(ch[8:12], ('G3', 'E4'), 2), 'tremolo', off=-4, line=False)
    add('cellos', chop(bass(ch[8:12], 'G2'), [(0, 0.25), (0.25, 0.25), (0.5, 0.25), (0.75, 0.25), (1.0, 0.25),
                                               (1.25, 0.25)]), 'spiccato', off=-2,
        offs=lambda n: 6 if round((n[0] - t9) % 1.5, 3) == 0 else -2, line=False)
    add('basses', pulse(ch[8:12], 'G1', every=1.5, length=0.6), 'staccato', off=-2, offs=lilt(t9, 6, 2), line=False)
    for k in (1, 3):
        st = t9 + k * BAR
        add('trombones', [(st, 0.9, N('A2')), (st, 0.9, N('E3')), (st, 0.9, N('C#4'))], 'marcato', off=-10 + 6 * (k == 3),
            line=False)
        add('tuba', [(st, 0.9, N('A1'))], 'marcato', off=2, line=False)
        add('timpani', [(st, 0.6, N('A2'))], 'hit', off=6, line=False)
    # bars 13-16: the theme in augmentation in the bass; the strings' stream over it
    t13 = t + 12 * BAR
    sb = mel(t13, STORM_BASS)
    add('trombones', sb, off=-10, offs=lilt(t13, 12, 4), line=True)
    add('tuba', sh(sb, -12), off=2, offs=lilt(t13, 4, 2), line=True)
    add('cellos', sb, off=6, offs=lilt(t13, 4, 2), line=True)
    add('basses', sh(sb, -12), off=2, offs=lilt(t13, 4, 2), line=False)
    add('bassoons', sb, off=-2, offs=lilt(t13, 12, 2), line=False)
    add('violins1', stream(ch[12:18], key, t13, t13 + 4 * BAR, 'D5', 'D6', phase=0.0, period=6, dur=0.26), off=-2,
        offs=flow(t13, 'A5'), line=False)
    add('violins2', stream(ch[12:18], key, t13, t13 + 4 * BAR, 'F4', 'F5', phase=math.pi, period=6, dur=0.26),
        off=-3, offs=flow(t13, 'A4'), line=False)
    add('violas', pad(ch[12:18], ('A3', 'F4'), 2), 'tremolo', off=-4, line=False)
    add('horns', pad(ch[12:18], ('A3', 'F4'), 2), off=-2, line=False)
    add('trumpets', [(t13 + 2 * BAR, 3, N('F4')), (t13 + 3 * BAR, 3, N('E4'))], off=-2, line=False)
    add('percussion', [(t13 + 2 * BAR, 3, keys['tam_tam'], 110)], None, line=False)
    # bars 17-20: the A pedal, tremolo, the trumpets' fanfare fragments, the cymbal roll into the return
    t17 = t + 16 * BAR
    ped = ch[18:]
    add('trumpets', mel(t17, STORM_TPT), off=4, offs=lilt(t17, 5, 2), line=True)
    add('horns', pad(ped, ('A3', 'G4'), 3), off=0, line=False)
    add('trombones', pad(ped, ('A2', 'G3'), 2), off=-10, offs=swell(t17 - 2 * BAR, 6 * BAR, 14), line=False)
    add('tuba', [(t17, 12, N('A1'))], off=-2, line=False)
    add('violins1', pad(ped, ('A5', 'G6'), 2), 'tremolo', off=-2, line=False)
    add('violins2', pad(ped, ('C#5', 'A5'), 2), 'tremolo', off=-2, line=False)
    add('violas', pad(ped, ('E4', 'C#5'), 2), 'tremolo', off=-2, line=False)
    add('cellos', [(t17, 12, N('A2'))], 'tremolo', off=-2, line=False)
    add('basses', [(t17, 12, N('A1'))], off=-2, line=False)
    add('bassoons', [(t17, 12, N('A2'))], off=-6, line=False)
    rise = run(t17 + 3 * BAR, 'A4', 'A6', key, 'A7', n=12)
    add('flutes', [(t17 + 3 * BAR, 3, N('E6'))], off=-6, line=False)
    add('clarinets', sh(rise, -12), off=-2, offs=lambda n: (n[2] - N('A3')) * 0.5, line=False)
    add('oboes', [(t17 + 2 * BAR, 6, N('C#6'))], off=-6, line=False)
    add('timpani', [(t17, 12, N('A2'))], 'roll', off=-2, line=False)
    add('percussion', [(t17 + 2 * BAR, 6, keys['cymbal_roll_long'], 112)], None, line=False)

    # -------------------------------------------------------------------------------------- river: the return in D major
    t, ch, key = T['river'], CH['river'], 'D'
    th = mel(t, THEME_MAJOR)
    add('violins1', th, off=6, offs=lilt(t, 3, 1), line=True)
    add('flutes', th, off=2, offs=lilt(t, 3, 1), line=True)
    add('oboes', th, off=0, offs=lilt(t, 3, 1), line=True)
    add('violins2', sh(th, -12), off=4, offs=lilt(t, 3, 1), line=True)
    add('trumpets', sh(th, -12), off=0, offs=lilt(t, 3, 1), line=True)
    add('horns', sh(th, -12), off=2, offs=lilt(t, 3, 1), line=True)
    add('clarinets', sh(th, -12), off=-2, offs=lilt(t, 3, 1), line=True)
    cm = mel(t, COUNTER_MAJOR)
    add('cellos', cm, off=3, offs=lilt(t, 3, 1), line=True)
    add('violas', stream(ch, key, t, t + 15 * BAR, 'A3', 'A4', phase=0.0, period=12, dur=0.27), off=-3,
        offs=flow(t, 'D4'), line=False)
    add('basses', bass(ch, 'D1'), off=-1, line=False)
    add('tuba', bass(ch, 'D1'), off=-4, line=False)
    add('bassoons', pad(ch, ('D2', 'A3'), 2), off=-5, line=False)
    # the trombones: a crescendo through every 4-bar phrase, re-struck with each chord (not held over the bar)
    tb = []
    for st, d, p in pad(ch, ('F2', 'A3'), 3):
        for k in range(int(round(d / 1.5))):
            u = st + 1.5 * k
            x = ((u - t) % (4 * BAR)) / (4 * BAR)
            tb.append((u, 1.4, p, round(52 + 62 * x + (6 if round((u - t) % BAR, 3) == 0 else 0))))
    add('trombones', tb, line=False)
    add('harp', arpeggio(ch, 'D2', step=0.5, ring=1.5, span=2), None, off=-4, line=False)
    timp = []
    for st, d, sym in ch:
        r = tones(sym)[0]
        p = N('D3') if r == 2 else N('A2') if r == 9 else None
        if p is not None:
            timp.append((st, 0.6, p, 108 if round((st - t) % (2 * BAR), 3) == 0 else 92))
    add('timpani', [(a, d, p, v - 10) for a, d, p, v in timp], 'hit', line=False)
    add('timpani', [(t + 14 * BAR, 3, N('A2'))], 'roll', off=-2, line=False)
    add('percussion', [(t, 3, keys['crash'], 120), (t, 2, keys['bass_drum'], 112), (t + 8 * BAR, 3, keys['crash'], 104),
                       (t + 15 * BAR, 3, keys['crash'], 114), (t + 15 * BAR, 2, keys['bass_drum'], 108)], None,
        line=False)

    # -------------------------------------------------------------------------------------- coda
    t, ch = T['coda'], CH['coda']
    add('flutes', stream(ch[:4], key, t, t + 4 * BAR, 'A4', 'A5', phase=0.0), off=0, offs=flow(t, 'D5'), line=True)
    add('horns', mel(t, CODA_HORN), off=3, offs=lilt(t, 3, 1), line=True)
    add('clarinets', mel(t + 2 * BAR, CODA_CL), off=3, line=True)
    add('violins2', pad(ch[:4], ('F#4', 'D5'), 2), off=-8, line=False)
    add('violas', pad(ch[:4], ('A3', 'F#4'), 2), off=-8, line=False)
    add('cellos', [(t, 12, N('D3'))], off=-6, line=False)
    add('basses', [(t, 12, N('D2'))], off=-8, line=False)
    add('harp', arpeggio(ch[:4], 'D3', step=0.5, ring=1.5, span=1), None, off=-8, line=False)
    # the last crescendo and the held chord
    t5 = t + 4 * BAR
    end = ch[4:7]
    fin = t + 6 * BAR
    for role, reg, v, o in (('violins1', ('D5', 'A5'), 2, 0), ('violins2', ('F#4', 'D5'), 2, -2),
                            ('violas', ('A3', 'F#4'), 2, -2), ('flutes', ('D5', 'A5'), 2, -2),
                            ('oboes', ('F#4', 'D5'), 2, -4), ('clarinets', ('A3', 'F#4'), 2, -4),
                            ('horns', ('A3', 'F#4'), 3, -2), ('trumpets', ('D4', 'A4'), 2, -4),
                            ('trombones', ('F#2', 'A3'), 3, -4), ('bassoons', ('D2', 'A3'), 2, -4)):
        notes = pad(end, reg, v)
        held = [(a, min(d, fin - a), p) for a, d, p in notes if a < fin - 1e-6]
        held += [(fin, 6, p) for a, d, p in notes if a + d > fin + 1e-6]
        add(role, held, off=o, offs=swell(t5 - BAR, 3 * BAR, 10), line=False)
    add('violins1', mel(t5, ['B5:1.5 G5:1.5', 'A5:1.5 C#6:1.5']) + [(fin, 6, N('D6'))], off=4,
        offs=lilt(t5, 4, 2), line=True)
    add('cellos', [(t5, 1.5, N('G3')), (t5 + 1.5, 1.5, N('E3')), (t5 + 3, 3, N('A2')), (fin, 6, N('D3'))], off=-2,
        line=False)
    add('basses', [(t5, 1.5, N('G1')), (t5 + 1.5, 1.5, N('E1')), (t5 + 3, 3, N('A1')), (fin, 6, N('D1'))], off=0,
        line=False)
    add('tuba', [(t5 + 3, 3, N('A1')), (fin, 6, N('D1'))], off=-4, line=False)
    add('timpani', [(t5 + 3, 3, N('A2'))], 'roll', off=-12, line=False)
    add('timpani', [(fin, 0.8, N('D3'), 92), (fin + 0.8, 5, N('D3'), 52)], 'roll', line=False)
    add('harp', [(fin + 0.08 * k, 6, N(p)) for k, p in enumerate('D2 A2 D3 F#3 A3 D4 F#4 A4 D5'.split())], None,
        off=-2, line=False)
    add('percussion', [(fin, 4, keys['crash'], 116), (fin, 3, keys['bass_drum'], 110)], None, line=False)

    sc.perform()
    return s
