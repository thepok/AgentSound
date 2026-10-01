"""Nocturne in E-flat major, op. 9 no. 2 (Frederic Chopin, 1832) - an etude for the virtual pianist.
Build: python -m agentsound build songs/nocturne-etude          (NOCTURNE_MODE=before: the pre-etude tools)

Public-domain score, rendered note for note: 12/8, Andante, E-flat major, one bar of pickup + 34 bars.
The notes were written from the score and checked bar by bar against a concert recording (analysis only: onset
+ pitch tracking of the melody, bass and chord peaks per eighth; NOTES.md lists what was corrected and where the
recording's pianist adds or varies ornaments - the recording is the verification target where editions differ).

  pickup   Bb4
  A    1-4    the theme: G5 held, F G F Eb Bb | C7 (turn on C5) C6 G5 Bb5 Ab5 G5 | F5 G5 D5 Eb5 C5 | Bb4 D6 C6 +
              a 16th cadence Bb Ab G Ab C D Eb
  A'   5-8    ornamented: a written-out turn (F G F E F G), grace turn B4 C5 Db5 C5 + the appoggiatura chain F-E
              Ab-G Db-C, a trill on F5 with its termination, the cadence again
  B    9-12   Bb | F/A | Ab Ab7 Abm | Eb Fb7 C7-F7 Gm | Cm F7 Bb... Bb7: F5 G5 F5 C5 | repeated Eb5s | the climb to
              Bb5 and the chromatic way back (Bb4 B4 C5)
  A''  13-16  fioritura A4-D5 in bar 13, bar 16 the chromatic fioritura Db6 .. Bb4 (+ a diminished arpeggio)
  B    17-20
  A''' 21-24  bar 24: the long fioritura Db6 C6 B5 Bb5 A5 Ab5 | A4 Bb4 B4 C5 Db5 D5 | G5 F5 Eb5
  coda 25-31  over an Eb pedal (Eb / Abm): Eb F Eb F G ..., the 'con forza' run G6 .. Eb5 (bar 28), stretto,
              F7/A Bb7 G7/B Cm F7/A
  32          senza tempo: flourish over Bb7 and the cadenza (the four-note cycle Cb7 Bb6 C7 A6, accelerating and
              broadening), the descent to the cadence Bb5 Ab5 C5 D5
  33-34       Eb5, the sighing Bb4 G5 Eb5 figures, the last chords ppp

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Voxengo IM Reverbs (Musikvereinsaal IR).
"""
import os

from agentsound import *
from agentsound import pianist
from agentsound.humanize import touch as _touch, crescendo as _crescendo, humanize as _humanize
from agentsound import romantic as rom

ANALYSIS = {'profile': 'piano'}                   # classical targets, a solo piano's spectrum (NOTES.md)
METADATA = {'title': 'Nocturne op. 9 Nr. 2 (Chopin) – Étude', 'artist': 'AgentSound', 'album': 'Études',
            'genre': 'Classical', 'year': 2026, 'composer': 'Frédéric Chopin'}
COVER = {'style': 'classical', 'palette': ['#1d2a44', '#c9a45c'], 'title': 'NOCTURNE',
         'subtitle': 'op. 9 Nr. 2 - Chopin - AgentSound', 'seed': 9}

MODE = os.environ.get('NOCTURNE_MODE', 'after')        # 'before' = the tools as they were before the etude
TEMPO = 50                                              # quarter notes (a 12/8 bar = 6 beats = 7.2 s)
PIANO = os.environ.get('NOCTURNE_PIANO', 'salamander')  # 'recital': sampled/recital_grand (Headroom C3)
SYMPATHETIC = float(os.environ.get('NOCTURNE_SYMPATHETIC', '0.0'))   # the recording is dry: 0.6 -> T60 3.0 s
RECITAL_GAIN = float(os.environ.get('NOCTURNE_RECITAL_GAIN', '-3.0'))
E = 0.5                                                 # an eighth in beats

# ------------------------------------------------------------------------------------------------ the score
# RH: tokens per bar (12 eighths): NOTE:dur (eighths), r:dur rest, _:dur holds the previous note on,
# {N N ..}:dur[@shape] a fioritura (free figure, lands on the next token), N:dur~ trill (main start, termination
# into the next note), N:dur~u trill from the upper note, N:dur^ turn after the note (^c chromatic: upper +1,
# lower -1), (N N) grace notes before the next note, [N N]:dur a (rolled) chord. '!' after dur = accent.
# LH: 4 beats per bar, each 'BASS:CHORD[/CHORD2][@start+len][|pattern]' (eighths within the beat; ';' separates
# entries of one beat), chord notes joined by '.', pattern letters b bass, c chord, B bass+chord held, . rest.

RH = {
    0: 'Bb4:1',
    1: 'G5:5 F5:1 G5:1 F5:2 Eb5:2 Bb4:1',
    2: 'G5:2 C5:1^c C6:2 G5:1 Bb5:3 Ab5:2 G5:1',
    3: 'F5:3 G5:2 D5:1 Eb5:3 C5:3',
    4: 'Bb4:1 D6:1 C6:1 {Bb5 Ab5 G5 Ab5 C5 D5}:3@even Eb5:5 Bb4:1',
    5: 'G5:3 {F5 G5 F5 E5 F5 G5}:3 F5:1.5 Eb5:2 {F5 Eb5 D5 Eb5 F5}:2.5',
    6: 'G5:0.5 {B4 C5 Db5 C5}:1.5 {F5 E5 Ab5 G5 Db6 C6}:3@even G5:1 Bb5:3 Ab5:2 G5:1',
    7: 'F5:3~c G5:2 D5:1 Eb5:3 C5:3',
    8: 'Bb4:1 D6:1 C6:1 {Bb5 Ab5 G5 Ab5 C5 D5}:3@even Eb5:4 D5:1 Eb5:1',
    9: 'F5:3 G5:2 F5:4^ C5:2 {F5 G5}:1',
    10: 'Eb5:2 Eb5:1 Eb5:1 Eb5:2 D5:0.5 Eb5:0.5 F5:1.5 Eb5:3.5',
    11: 'r:0.5 Bb4:0.5 Eb5:2 Bb5:2! A5:1 G5:1 F5:1 Eb5:1 D5:3',
    12: 'Eb5:2.5 D5:0.5 C5:0.75 D5:0.75 Bb4:0.5 B4:1.5 C5:1 C5:1.5 D5:1 G4:1 Bb4:0.5 Eb5:0.5',
    13: 'G5:2.8 {A4 Bb4 B4 Bb4 Db5 D5}:2.2 G5:1 F5:1.5 Eb5:2 {F5 Eb5 D5 Eb5 F5}:2.5',
    14: 'G5:0.5 {B4 C5 Db5 C5}:1.5 {F5 E5 Ab5 G5 Db6 C6}:3@even G5:1 Bb5:3 Ab5:2 G5:1',
    15: 'F5:3~c G5:2 D5:1 Eb5:3 C5:3',
    16: 'Bb4:1 D6:1 {Db6 C6 B5 Bb5 A5 Ab5 F5 D5 B4 Bb4}:2.5 D5:0.5 G5:0.75 F5:0.25 Eb5:4 D5:1 Eb5:1',
    17: 'F5:3 G5:2 F5:2 F5:2~ C5:1 G5:1? C5:1',
    18: 'Eb5:1.5 Eb5:1 Eb5:1 Eb5:1 Eb5:1.5 D5:0.5 Eb5:0.5 F5:1.5 Eb5:3.5',
    19: 'r:0.5 Bb4:0.5 Eb5:2 Bb5:1! Ab5:1.5 A5:0.5 G5:0.5 F5:0.5 G5:0.5 F5:0.5 Eb5:1 D5:3',
    20: 'Eb5:2.5 D5:0.5 C5:0.75 D5:0.75 Bb4:0.5 B4:1.5 C5:1 C5:1.5 D5:1 G4:1 Bb4:0.5 Eb5:0.5',
    21: 'G5:2.8 {A4 Bb4 B4 Bb4 Db5 D5}:2.2 G5:1 F5:1.5 Eb5:2 {F5 Eb5 D5 Eb5 F5}:2.5',
    22: 'G5:0.5 {B4 C5 Db5 C5}:1.5 {F5 E5 Ab5 G5 Db6 C6}:3@even G5:1 Bb5:3 Ab5:2 G5:1',
    23: 'F5:3~c G5:2 D5:1 Eb5:3 C5:3',
    24: 'Bb4:1 D6:1 {Db6 C6 B5 Bb5 A5 Ab5}:2.2@rit {A4 Bb4 B4 C5 Db5 D5}:1.2@accel G5:0.35 F5:0.25 Eb5:6',
    25: 'Eb5:3 F5:1 Eb5:1 F5:1 G5:6',
    26: 'Eb5:4.5 {F5 Eb5 F5 Eb5 F5}:3.25 G5:1.25 Eb5:1 Eb5:0.5 F5:0.5 D5:0.25 Eb5:0.75',
    27: 'Eb6:1 D6:1 C6:1 Bb5:1.75 A5:0.75 Ab5:0.75 C5:0.75 D5:1 Eb5:1 F5:1~ D5:1 Eb5:1',
    28: 'G6:2! F6:1 Eb6:0.33 D6:0.33 C6:0.67 B5:1 Bb5:0.67 A5:1.5 Ab5:0.75 G5:3 F5:0.75',
    29: 'Eb5:4 G5:1 Eb5:1.5 Gb5:1.25 Eb5:0.75 Ab5:0.5 {F5 Eb5 F5 Eb5 F5 Eb5 F5}:3@even',
    30: 'G5:5 Eb5:1 {Ab4 Bb4 B4 Eb5 Ab5 Eb6}:2@accel {Gb5 Eb6 F6}:0.75 G6:1.25! Eb6:1 G5:0.5 Bb4:0.5',
    31: '_:1 D6:0.75 [C6 C7]:1! [B5 B6]:0.75 Bb5:0.5 [A5 A6]:0.75 Ab6:0.25 G6:0.5 D5:0.75 Eb5:1 Eb6:2.25 F6:1 '
        'C7:0.5 F6:1',
    32: ('[B5 B6]:1! {D6 Eb6 Ab5 F#6 F6 D6 C6 F6 F#6 Eb6 C7 Ab5 F6 C7 Ab6 Eb6 D6 Ab6}:2.5@wave Bb6:1 '
         '{CADENZA}:4.5 {D7 C7 Bb6 A6 Ab6 G6 F6 D6 Eb6 C6}:1@rit Bb5:0.5 Ab5:0.5 C5:0.5 D5:0.5'),
    33: 'Eb5:1.5 Bb4:1 G5:1 Eb5:1 Bb4:1 G5:1 Eb5:1 Bb4:1 G5:1 Eb5:1 Bb4:0.75 G5:0.75',
    34: 'Eb5:4 [Bb4 G5 Eb6]:4 [Eb5 G5]:1.5 [Eb4 G4 Bb4 Eb5]:2.5',
}
CADENZA = ['Bb6', 'C7', 'A6'] + ['B6', 'Bb6', 'C7', 'A6'] * 14      # the four-note cycle Cb7 Bb6 C7 A6

_A = [['Eb2:Bb3.Eb4.G4', 'Eb2:B3.D4.Ab4', 'Eb2:Bb3.Eb4.G4', 'D2:A3.C4.F#4'],
      ['C2:Bb3.E4.G4', 'C2:Bb3.E4.G4', 'F2:Bb3.Db4.E4', 'F2:Ab3.C4.F4'],
      ['Bb1:D4.F4.Ab4', 'B1:G3.D4.F4', 'C2:G3.Eb4.G4', 'A1:F#3.C4.Eb4/C4.Eb4.F#4'],
      ['Bb1:Bb3.Eb4.Ab4', 'Bb1:Bb3.D4.Ab4', 'Eb2:G3.Bb3.Eb4', 'Eb2:Bb3.Eb4.G4']]
_B = [['Bb1:Bb3.D4.F4', 'Bb1:Bb3.D4.F4', 'A1:F3.C4.F4', 'A1:F3.C4.F4'],
      ['Ab1:Ab3.C4.Eb4', 'Ab1:C4.Eb4.Gb4', 'Ab1:Ab3.B3.Eb4', 'Eb2:G3.Bb3.Eb4'],
      ['Eb2:Bb3.Eb4.G4', 'E2:Ab3.B3.D4', 'C2:Bb3.E4.G4/A3.Eb4.F4', 'G1:D4.G4.Bb4'],
      ['C2:C4.Eb4.G4/Eb4.F4.A4', 'Bb1:D4.F4.Ab4/D4.F#4', 'C2:E4.G4.Bb4/Eb4.F4.A4', 'Bb1:Ab3.D4.F4']]
LH = {0: []}
for k, bars in ((1, _A), (5, _A), (9, _B), (13, _A), (17, _B), (21, _A)):
    for i, b in enumerate(bars):
        LH[k + i] = b
LH.update({
    25: ['Eb2:Bb3.Eb4.G4/Ab3.B3.Eb4', 'Eb2:Ab3.B3.Eb4', 'Eb2:G3.Bb3.Eb4', 'Eb2:G3.Bb3.Eb4'],
    26: ['Eb2:G3.Bb3.Eb4', 'Eb2:Ab3.B3.Eb4', 'Eb2:Ab3.B3.Eb4', 'Eb2:G3.Bb3.Eb4'],
    27: ['Eb2:G3.Bb3.Eb4', 'Eb2:C4.F#4.A4', 'Eb2:Ab3.C4.Eb4/Ab3.D4.F4', 'Eb2:G3.Bb3.Eb4'],
    28: ['A1:C4.Eb4.F4', 'Bb1:Ab3.D4.F4', 'Bb1:Ab3.D4.F4', 'Bb1:Ab3.D4.F4'],
    29: ['Eb2:G3.Bb3.Eb4', 'Eb2:G3.Bb3.Eb4', 'Ab1:C4.Eb4.Gb4/B3.Eb4.Gb4', 'Eb2:Ab3.B3.Eb4'],
    30: ['Eb2:G3.Bb3.Eb4', 'Eb2:G3.Bb3.Eb4', 'Ab1:C4.Eb4.Gb4/Ab3.B3.Eb4', 'Eb2:G3.Bb3.Eb4'],
    31: ['A1:C4.Eb4.F4', 'Bb1:Ab3.D4.F4@0+1|b;B1:G3.D4.F4@1+2|bc', 'C2:C4.Eb4.G4', 'A1:C4.Eb4.F4'],
    32: ['Bb1:F3.Ab3.D4', 'Bb1:Ab3.D4.F4', 'Bb1:F3.Ab3.D4|B..', 'Bb1:Ab3.D4.F4@1.5+1.5|B'],
    33: ['Eb2:G3.Bb3.Eb4', 'Bb1:G3.Bb3.Eb4', 'Eb2:G3.Bb3.Eb4', 'Bb1:G3.Bb3.Eb4'],
    34: ['Eb2:G3.Bb3.Eb4', 'Eb2:G3.Bb3.Eb4|b..', 'Eb2:G3.Bb3.Eb4|b..', 'Eb1:Eb2.Bb2.G3|B..'],
})

# dynamics per bar (the score's marks + the phrase hairpins): (bar, eighth, level)
# dynamics (the score's p espressivo / dolce, its hairpins, the B section's crescendo to the con forza bar and
# the coda's two climaxes; the cadenza leggiero): (bar, eighth, level); the melody gets them in full, the left
# hand at a gentler slope (factor ** 0.6)
DYN = [(0, 0, 'p'), (1, 0, 'p'), (2, 1, 'p'), (2, 3, 'mf'), (2, 9, 'mp'), (3, 3, 'mf'), (3, 8, 'mp'), (4, 0, 'mp'),
       (4, 9, 'p'),
       (5, 0, 'p'), (6, 1, 'p'), (6, 3, 'mf'), (6, 9, 'mp'), (7, 3, 'mf'), (7, 8, 'mp'), (8, 3, 'mp'), (8, 9, 'p'),
       (9, 0, 'pp'), (9, 6, 'p'), (10, 0, 'p'), (10, 9, 'mp'), (11, 3, 'mp'), (11, 9, 'mf'), (12, 0, 'f'),
       (12, 6, 'f'), (12, 11, 'mp'),
       (13, 0, 'p'), (14, 1, 'p'), (14, 3, 'mp'), (14, 9, 'p'), (15, 3, 'mp'), (15, 8, 'p'), (16, 3, 'mp'), (16, 9, 'p'),
       (17, 0, 'pp'), (17, 6, 'p'), (18, 0, 'p'), (18, 9, 'mp'), (19, 3, 'mp'), (19, 9, 'mf'), (20, 0, 'f'),
       (20, 6, 'f'), (20, 11, 'mp'),
       (21, 0, 'p'), (22, 1, 'p'), (22, 3, 'mp'), (22, 9, 'p'), (23, 3, 'mp'), (23, 8, 'p'), (24, 3, 'p'), (24, 9, 'pp'),
       (25, 0, 'pp'), (26, 6, 'p'), (27, 0, 'p'), (27, 9, 'mp'), (28, 0, 'mp'), (28, 6, 'p'), (28, 11, 'p'),
       (29, 0, 'p'), (30, 0, 'mp'), (30, 9, 'f'), (31, 5, 'f'), (31, 11, 'f'), (32, 0, 'mf'), (32, 1.5, 'mp'),
       (32, 3.5, 'p'), (32, 4.5, 'p'), (32, 9, 'p'), (32, 11, 'pp'), (33, 0, 'p'), (34, 0, 'pp'), (34, 8, 'ppp')]


# ------------------------------------------------------------------------------------------------ parsing
def bar_start(k: int) -> float:
    """Beat of bar k (0 = the pickup eighth)."""
    return 0.0 if k == 0 else E + (k - 1) * 6.0


def parse_rh(k: int, spec: str) -> list:
    """Events of one bar: (kind, beat, dur_beats, payload, mark)."""
    toks, i, out, pos, graces = [], 0, [], 0.0, []
    s = spec
    while i < len(s):                           # tokenizer: {...}:x, (...), [...]:x, plain
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c in '{[(':
            j = s.index({'{': '}', '[': ']', '(': ')'}[c], i)
            k2 = j + 1
            while k2 < len(s) and not s[k2].isspace():
                k2 += 1
            toks.append(s[i:k2])
            i = k2
            continue
        k2 = i
        while k2 < len(s) and not s[k2].isspace():
            k2 += 1
        toks.append(s[i:k2])
        i = k2
    t0 = bar_start(k)
    for tok in toks:
        if tok.startswith('('):
            graces = tok[1:-1].split()
            continue
        body, _, rest = tok.rpartition(':') if not tok.startswith('{') else (tok[:tok.index('}') + 1], ':',
                                                                             tok[tok.index('}') + 2:])
        shape = 'arch'
        mark = ''
        if '@' in rest:
            rest, shape = rest.split('@')
        while rest and rest[-1] in '!?~^uc':
            mark = rest[-1] + mark
            rest = rest[:-1]
        d = float(rest) * E
        at = t0 + pos * E
        if body.startswith('{'):
            inner = body[1:-1].split()
            if inner == ['CADENZA']:
                inner = CADENZA
            out.append(('fig', at, d, inner, shape))
        elif body.startswith('['):
            out.append(('chord', at, d, body[1:-1].split(), mark))
        elif body == 'r':
            pass
        elif body == '_':
            out.append(('hold', at, d, None, ''))
        elif '~' in mark:
            out.append(('trill', at, d, body, mark))
        elif '^' in mark:
            out.append(('turn', at, d, body, 'c' in mark))
        else:
            out.append(('note', at, d, body, mark))
        if graces:
            out[-1] = out[-1] + (graces,)
            graces = []
        pos += float(rest)
    if abs(pos - (1 if k == 0 else 12)) > 1e-6:
        raise ValueError(f"bar {k}: the right hand holds {pos:g} eighths, not {1 if k == 0 else 12}")
    return out


def parse_lh(k: int, beats: list) -> list:
    """accompany() entries of one bar."""
    out = []
    t0 = bar_start(k)
    for bi, spec in enumerate(beats):
        for part in spec.split(';'):
            pat = 'bcc'
            if '|' in part:
                part, pat = part.split('|')
            off, ln = 0.0, 3.0
            if '@' in part:
                part, span = part.split('@')
                off, ln = (float(x) for x in span.split('+'))
            bass, chords = part.split(':')
            ch = [c.split('.') for c in chords.split('/')]
            out.append((t0 + bi * 1.5 + off * E, ln * E, None if bass == '-' else bass, ch[0],
                        ch[1] if len(ch) > 1 else ch[0], pat))
    return out


SCORE = {k: parse_rh(k, v) for k, v in RH.items()}


# ------------------------------------------------------------------------------------------------ performance
def skeleton() -> Clip:
    """The melody's principal notes (what the touch shapes): notes, trill / turn principals, figure starts."""
    ns = []
    for k, evs in SCORE.items():
        for ev in evs:
            kind, at, d = ev[0], ev[1], ev[2]
            if kind in ('note', 'trill', 'turn'):
                ns.append((at, d, ev[3], 80))
            elif kind == 'fig':
                ns.append((at, d, ev[3][0], 80))
            elif kind == 'chord':
                ns.append((at, d, max(ev[3], key=note), 80))
            elif kind == 'hold' and ns:
                s0, d0, p0, v0 = ns[-1]
                ns[-1] = (s0, d0 + d, p0, v0)
    return Clip(ns)


def play_rh(s: Song, key) -> tuple[Clip, list]:
    """The right hand as played: velocities from the phrase touch, ornaments expanded, then (after) the singing
    line, the dynamics and the melody's rubato. Returns (clip, figures) - figures = [(clip, bpm)] for stats."""
    bpm = s.tempo_at
    sk = skeleton()
    ends = {bar_start(k) for k in range(3, 36, 2)}           # two-bar phrases: a breath for touch() to see
    sk = Clip._raw([n._replace(dur=n.dur - 0.3) if any(abs(n.start + n.dur - e) < 0.05 for e in ends)
                    and n.dur > 0.6 else n for n in sk], sk.length)
    if MODE == 'after':                         # a gentler arc; the long notes lean (below), the line sings
        sk = _touch(sk, lo=64, hi=96, gap='1/4', start=0.55, end=0.4, pitch=0.9)
    else:
        sk = _touch(sk, lo=60, hi=100, gap='1/4', start=0.35, end=0.3, pitch=0.7)
    vel = {round(n.start, 4): n.vel for n in sk}
    notes, figs = [], []
    evs = [ev for k in sorted(SCORE) for ev in SCORE[k]]
    for i, ev in enumerate(evs):
        kind, at, d = ev[0], ev[1], ev[2]
        v = vel.get(round(at, 4), 70)
        if len(ev) > 4 and isinstance(ev[4], str) and '!' in ev[4]:
            v = min(118, v * 1.1)
        if len(ev) > 4 and isinstance(ev[4], str) and '?' in ev[4]:
            v = v * 0.72
        nxt = next((e for e in evs[i + 1:] if e[0] != 'hold'), None)
        nxt_p = None
        if nxt is not None and nxt[0] in ('note', 'trill', 'turn'):
            nxt_p = nxt[3]
        hold = sum(e[2] for e in evs[i + 1:i + 2] if e[0] == 'hold')
        graces = ev[5] if len(ev) > 5 else None
        if graces:
            if MODE == 'after':
                g = rom.grace(graces, ev[3], d, bpm, at=at, ms=70, vel=v)
                notes += [n for n in g if n.start < at - 1e-6]
            else:
                notes += [Note(at - (len(graces) - j) * 0.08, 0.08, note(p), max(1, v - 20))
                          for j, p in enumerate(graces)]
        if kind == 'note':
            notes.append(Note(at, d + hold, note(ev[3]), v))
        elif kind == 'chord':
            ps = sorted(note(p) for p in ev[3])
            c = pianist.roll(ps, d, TEMPO, ms=60 if MODE == 'after' else 25, vel=v, at=at)
            notes += list(c)
        elif kind == 'fig':
            pv = v
            if MODE == 'after':
                f = rom.fioritura(ev[3], d, bpm, at=at, shape=ev[4], ease=0.2 if ev[4] == 'even' else 0.8,
                                  vel=(pv, pv - 6), dip=7 if len(ev[3]) > 5 else 4, seed=int(at * 7))
            else:                               # before: the notes on an even grid, the pianist's light drop
                n = len(ev[3])
                f = Clip([(at + j * d / n, d / n * 1.1, p, pv if j == 0 else max(1, pv - 12))
                          for j, p in enumerate(ev[3])])
            figs.append((f, bpm, at))
            notes += list(f)
        elif kind == 'trill':
            land = nxt_p
            if MODE == 'after':
                f = rom.trill(ev[3], d, bpm, at=at, key=key, start='upper' if 'u' in ev[4] else 'main',
                              lower=-1 if 'c' in ev[4] else None, land=land, land_dur=0.05, vel=v, seed=int(at))
                f = Clip([n for n in f if n.start < at + d - 1e-6])      # the landing note is the next token
            else:
                f = pianist.trill(ev[3], d, TEMPO, key=key, vel=v, at=at, hold=0.0)
            figs.append((f, bpm, at))
            notes += list(f)
        elif kind == 'turn':
            if MODE == 'after':
                f = rom.turn(ev[3], d, bpm, at=at, key=key, where='after', vel=v,
                             upper=1 if ev[4] else None, lower=-1 if ev[4] else None)
            else:
                f = pianist.turn(ev[3], d, TEMPO, key=key, vel=v, at=at)
            notes += list(f)
    rh = Clip._raw(notes, max(n.start + n.dur for n in notes))
    if MODE == 'after':
        rh = rom.lean_on_long(rh, bpm, gain=10)
        rh = rom.cantabile(rh, bpm)
        rh = rom.dynamics(rh, [(bar_start(b) + e8 * E, lv) for b, e8, lv in DYN])
        anchors = [bar_start(k) + h * 3.0 for k in range(1, 35) for h in (0, 1)] + [bar_start(35)]
        rh = rom.melody_rubato(rh, anchors, bpm, sync_ms=42, seed=3)
        rh = Clip._raw([n._replace(vel=min(n.vel, 112)) for n in rh], rh.length)    # the climax sings, not bangs
    else:
        rh = dyn_before(rh, 1.0)
    return rh, figs


def dyn_before(clip: Clip, power: float) -> Clip:
    """The same dynamics map with the tools that existed: humanize.crescendo per span between two marks."""
    pts = [(bar_start(b) + e8 * E, rom.LEVELS[lv] ** power) for b, e8, lv in DYN]
    for (b0, l0), (b1, l1) in zip(pts, pts[1:]):
        if b1 > b0:
            clip = _crescendo(clip, l0, l1, span=(b0, b1 - 1e-3))
    return clip


def play_lh(s: Song) -> Clip:
    entries = [e for k in sorted(LH) for e in parse_lh(k, LH[k])]
    if MODE == 'after':
        out = []
        for st, ln, bass, c1, c2, pat in entries:
            out += list(rom.accompany([(st, ln, bass, c1, c2)], s.tempo_at, pattern=pat, vel=38, bass=1.2,
                                      first=1.0, second=0.88, top=1.06, roll_ms=14, seed=int(st * 3)))
        lh = Clip._raw(out, max(n.start + n.dur for n in out))
        dyn = [(bar_start(b) + e8 * E, rom.LEVELS[lv] ** 0.6) for b, e8, lv in DYN]
        return rom.dynamics(lh, dyn)
    out = []                                    # before: every strike at one level, humanized
    for st, ln, bass, c1, c2, pat in entries:
        for i in range(int(round(ln / E))):
            c = pat[i % len(pat)]
            t = st + i * E
            if c in 'bB' and bass:
                out.append(Note(t, ln - i * E, note(bass), 58))
            if c in 'cB':
                for p in (c1 if i <= 1 else c2):
                    out.append(Note(t, E if c == 'c' else ln - i * E, note(p), 58))
    lh = _humanize(Clip._raw(out, max(n.start + n.dur for n in out)), timing_ms=4, vel=6, bpm=TEMPO, seed=2)
    return dyn_before(lh, 0.6)


def tempo_plan(s: Song) -> None:
    """The left hand's time (the tempo map): every two-bar phrase breathes (moves on into its middle, broadens
    into its cadence), the A cadences take a breath, the B section presses on into the repeated E-flats and holds
    back in its chromatic way home, the coda is slower, its two climaxes are pressed and then broadened, the
    cadenza is senza tempo (its figures are timed in real time), the end dies away with a fermata."""
    b = bar_start
    for k in range(1, 25, 4):                   # a four-bar phrase: settles in, moves on, broadens to its cadence
        s.rubato((b(k), b(k + 2)), depth=0.1, phrase='lean', seed=k)
        s.rubato((b(k + 2), b(k + 4)), depth=0.1, phrase='arch', seed=k + 2)
    for k in (4, 8, 16):                        # the A cadences: a breath into the dotted-quarter Eb
        s.ritardando((b(k) + 1.5, b(k) + 3.0), to=0.8)
    for k in (10, 18):                          # B: pressing on into the repeated E-flats ...
        s.accelerando((b(k), b(k) + 3.0), to=1.1, a_tempo=True)
    for k in (12, 20):                          # ... and held back on the chromatic way home
        s.ritardando((b(k) + 3.0, b(k) + 6.0), to=0.72)
    s.ritardando((b(24) + 1.0, b(24) + 3.0), to=0.75)
    s.set_tempo(b(25), 46)                      # coda: quieter, a touch slower
    s.rubato((b(25), b(27)), depth=0.08, phrase='arch', seed=25)
    s.accelerando((b(27), b(28)), to=1.08)
    s.ritardando((b(28) + 3.0, b(29)), to=0.82)
    s.set_tempo(b(29), 47)
    s.accelerando((b(30), b(31) + 3.0), to=1.12)
    s.ritardando((b(31) + 3.0, b(32)), to=0.8)
    s.set_tempo(b(32), 24)                      # senza tempo: the flourish and the cadenza in real time
    s.ritardando((b(32) + 5.0, b(33)), to=0.7)
    s.set_tempo(b(33), 42)
    s.ritardando((b(34), b(34) + 5.5), to=0.72)
    s.fermata(b(34) + 4.75, hold=3)


def build() -> Song:
    s = Song('Nocturne op. 9 Nr. 2', tempo=TEMPO, key='Eb major', seed=9, time_sig='12/8', tail=7.0)
    s.section('pickup', bars=1, meter=(1, 8))
    for name, bars in (('A', 4), ('A2', 4), ('B', 4), ('A3', 4), ('B2', 4), ('A4', 4), ('coda', 7), ('cadenza', 1),
                       ('end', 2)):
        s.section(name, bars=bars)
    tempo_plan(s)

    hall = s.bus('hall', patches.get('bus/ir_concert_hall').but_fx('convolver', width=1.0))
    if PIANO == 'recital':                      # the Headroom C3 recital grand (the Gymnopedie etude's)
        piano = patches.get('sampled/recital_grand')
        tone = {'hp.freq': 30, 'hp.slope': 24}
        gain, pan_rh = RECITAL_GAIN, -0.15
    else:                                       # the Salamander voiced warm, with string resonance
        piano = inst.sfz('samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz', level=1.7, hammers=0.45,
                         polyphony=192, width=0.4, sympathetic=SYMPATHETIC)
        tone = {'hp.freq': 30, 'hp.slope': 24, 'peak1.freq': 280, 'peak1.gain': -1.0, 'peak1.q': 0.8,
                'high.freq': 10000, 'high.gain': 3.5}
        gain, pan_rh = 4.2, -0.55
    rh_t = s.track('rh', piano, fx=[fx.eq(tone)], gain_db=gain, pan=pan_rh, sends={hall: -10})
    lh_t = s.track('lh', piano, fx=[fx.eq({**tone, 'low.freq': 180, 'low.gain': -5.0})], gain_db=gain, pan=-0.1,
                   sends={hall: -10})

    lh_t.play(play_lh(s), 0)                    # the timekeeper first: the tempo map knows its onsets
    rh, figs = play_rh(s, s.key)
    rh_t.play(rh, 0)

    changes, last = [], None                   # the pedal changes with the harmony (bass + chord), not every beat
    for e in sorted((e for k in LH for e in parse_lh(k, LH[k])), key=lambda e: e[0]):
        h = (e[2], tuple(e[3]))
        if e[2] and h != last:
            changes.append(round(e[0], 4))
        last = h
    flutter = []                                # chromatic figures / the cadenza: the pedal cleared as they run
    for k, evs in SCORE.items():
        for ev in evs:
            if ev[0] == 'fig' and len(ev[3]) >= 6:
                ps = [note(p) for p in ev[3]]
                if sum(1 for x, y in zip(ps, ps[1:]) if abs(x - y) == 1) >= 3:
                    flutter.append((ev[1], ev[1] + ev[2]))
    ped = rom.pedal_changes(changes, end=bar_start(35) + 2.0, lift_ms=110, bpm=s.tempo_at,
                            flutter=flutter if MODE == 'after' else (), flutter_ms=320, flutter_to=0.6)
    rh_t.automate('instrument.pedal', ped)
    lh_t.automate('instrument.pedal', ped)
    s.master.add(fx.limiter(ceiling=-1.0))
    global FIGURES
    FIGURES = figs
    return s


FIGURES = []
