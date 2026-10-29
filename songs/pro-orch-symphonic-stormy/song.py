"""Tempest Allegro - an original stormy symphonic allegro (sonata form) for full orchestra.
Build: python -m agentsound build songs/pro-orch-symphonic-stormy

A composed ("pro") reference for the endless symphonic orchestra: played by the SAME band setup as an endless piece
(agentsound.endless.orchestra.band), so only the writing differs. D minor, 4/4, q = 132, about 3:35.

THE MOTTO (2 bars): a short note, a 16th snap on the same pitch, the leap of a fifth up held, a falling 16th turn,
the fall to the tonic - then the leading tone held, the step back and the drop of a fourth to the dominant:
    | D4 . (16)D4  A4--  G4 F4 E4  F4 D4 |  C#4---  D4  E4  A3 |

  section  bars  key        what happens
  motto     4    D minor    the motto ff in octaves (strings, winds, horns), two tutti hammer-strokes Dm - A7, subito p:
                            violas / violins II start the agitato 8ths
  A        16    D minor    FIRST THEME, a sentence on the motto: statement (violins I, p), answer on C#dim7,
                            fragmentation (the motto's head climbing Gm - Em7b5 - A), cadence to a half close on A;
                            then the consequent subito f TUTTI (violins + flutes + oboes, 16ths in violins II / violas,
                            8ths in the basses) climbing to D6, Bb6 and the full close
  trans     8    Dm -> F    16th runs in the violins, the motto's head in the low strings and bassoons, sforzandi,
                            through Bb - Gm - A7 - F/A - G7/B to C7, dying away to p
  B        16    F major    SECOND THEME, lyrical: clarinet (question) and flute (answer) over pizzicato and
                            broken-chord violas (chamber); then the violins I in octaves with violins II, the
                            peak lifted to D6, oboe / flute counter-line, horns pp
  closing   6    F major    the motto turned major, tutti f, the cadence hammered; a bassoon echo of the head, pp
  fugato    8    Gm / Dm    DEVELOPMENT 1: a fugato on the motto (cellos + bassoons in G minor, violas the answer in
                            D minor, violins II, violins I), a running 8th countersubject; crescendo p -> f
  seq       8    Cm Dm Ebm  DEVELOPMENT 2: the head sequenced up by steps, woodwinds call, horns + trombones answer;
                            subito p / f contrasts; fragmentation on Edim7 tossed between the sections
  storm     8    Gm -> E7   DEVELOPMENT 3: the motto in the BASS (cellos, basses, bassoons, trombones, tuba) ff under
                            tremolo violins; Eb - C#dim7 - Bb - E7
  pedal     8    A pedal    the build over the dominant: basses + timpani roll on A, the head climbing in the winds,
                            16ths spreading through the strings, p -> ff
  recap     8    D minor    RECAPITULATION, changed: the consequent at once, ff tutti with the trumpets
  trans2    4    D minor    the transition cut short, Gm - Em7b5 - A7, diminuendo
  B2       12    D major    the second theme in the TONIC MAJOR: the cellos sing it, the violins I + flute answer;
                            then it darkens - Bb (the minor turns back), the peak Bb5, Em7b5 - A7
  coda     10    D minor    tragic: the motto in the violins, then in the low brass and basses, the head
                            fragmented, the Neapolitan Eb ff, the cadential 6/4 in 16ths, hammered Dm, held fermata

Orchestration rules kept: trombones never above Bb4, bassoons not above C5, horns sustained or in the motto (no
running 16ths), the strings carry every fast figure, the brass saved for the tuttis.
CREDITS: Sonatina Symphonic Orchestra 4.0, VSCO 2 CE (see the build's credits).
"""
from agentsound import *
from agentsound.theory import chord as _chord, note as _note, voice_lead
from agentsound.bandlib import orchestra as orch
from agentsound.endless.orchestra import band as orchestra_band

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'Tempest Allegro', 'artist': 'AgentSound', 'album': 'Orchestral References',
            'genre': 'Classical', 'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#16181f', '#b8402e'], 'title': 'TEMPEST ALLEGRO',
         'subtitle': 'AgentSound - Orchestral References', 'seed': 132}

KEY = 'D minor'
TEMPO = 132
SEED = 132
ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
         'trumpets', 'trombones', 'tuba', 'harp', 'timpani')

FORM = [('motto', 4), ('A', 16), ('trans', 8), ('B', 16), ('closing', 6), ('fugato', 8), ('seq', 8), ('storm', 8),
        ('pedal', 8), ('recap', 8), ('trans2', 4), ('B2', 12), ('coda', 10)]

# ------------------------------------------------------------------------------------------------ harmony
CHART = {
    'motto': 'Dm | A7 | Dm:2 A7:2 | Dm',
    'A': 'Dm | A7 | C#dim7 | Dm | Gm:2 Gm7:2 | Em7b5:2 A7:2 | Dm:2 Gm:2 | A | '
         'Dm | A7 | C#dim7 | Dm | Gm:2 A7:2 | Bb:2 Gm6:2 | Dm/A:2 A7:2 | Dm',
    'trans': 'Dm | Bb | Gm | A7 | F/A | Bb | G7/B | C7',
    'B': 'F | Dm7 | Bb | C7 | F/A | Bb | Gm7:2 C7:2 | F | F | Dm7 | Bb | C7 | F/A | Bb | Gm7:2 C7:2 | F',
    'closing': 'F | C7 | F:2 Bb:2 | C7 | F | F',
    'fugato': 'Gm | D7 | Dm | A7 | Gm | D7 | Dm | A7',
    'seq': 'Cm | Cm | Dm | Dm | Ebm | Ebm | Edim7 | Edim7',
    'storm': 'Gm | D7 | Gm | D7 | Eb | C#dim7 | Bb | E7',
    'pedal': 'A | Bb/A | Gm/A | A7 | A | Bb/A | Gm/A | A7',
    'recap': 'Dm | A7 | C#dim7 | Dm | Gm:2 A7:2 | Bb:2 Gm6:2 | Dm/A:2 A7:2 | Dm',
    'trans2': 'Dm | Gm | Em7b5 | A7',
    'B2': 'D | Bm7 | G | A7 | D/F# | G | Em7:2 A7:2 | D | Bb | Gm | Em7b5 | A7',
    'coda': 'Dm | A7 | Dm | A7 | Gm | Eb | Dm/A:2 A7:2 | A7 | Dm | Dm',
}

# ------------------------------------------------------------------------------------------------ the material
# all written at "violin II pitch" around D4; parts shift by octaves
M1 = 'D4:0.5 r:0.25 D4:0.25 A4:1 G4:0.5 F4:0.25 E4:0.25 F4:0.5 D4:0.5'      # the motto, bar 1
M2 = 'C#4:1.5 D4:0.5 E4:1 A3:1'                                              # the motto, bar 2
ANS = 'E4:0.5 r:0.25 E4:0.25 Bb4:1 A4:0.5 G4:0.25 F4:0.25 G4:0.5 E4:0.5'    # the answer, on C#dim7
HEAD = 'D4:0.5 r:0.25 D4:0.25 A4:1'                                          # 2 beats: the head
# horns / low brass: the motto without the 16th turn
M1_BRASS = 'D4:0.75 D4:0.25 A4:1.5 G4:0.5 F4:0.5 D4:0.5'

T1A = [M1, M2, ANS, 'F4:1.5 E4:0.5 D4:1 r:1',
       'G4:0.5 r:0.25 G4:0.25 D5:1 Bb4:0.5 r:0.25 Bb4:0.25 F5:1',
       'E5:0.5 r:0.25 E5:0.25 G5:1 F5:0.5 E5:0.5 D5:0.5 C#5:0.5',
       'D5:0.75 C#5:0.25 D5:0.5 A4:0.5 Bb4:1 G4:1', 'A4:3 r:1']
T1B = [M1, M2, ANS, 'F4:1 A4:1 D5:1.5 C#5:0.5',
       'D5:0.5 r:0.25 D5:0.25 G5:1 F5:0.5 E5:0.25 D5:0.25 E5:0.5 C#5:0.5',
       'D5:0.5 r:0.25 D5:0.25 Bb5:1 A5:0.5 G5:0.5 F5:0.5 E5:0.5',
       'F5:1 E5:0.5 D5:0.5 C#5:1 E5:1', 'D5:2 r:2']

# the second theme (F major, at pitch): stepwise, the leap of a minor sixth to the held F5, the answering phrase
B_Q = ['A4:1.5 Bb4:0.5 C5:1 A4:1', 'F5:3 E5:0.5 D5:0.5', 'D5:2 C5:1 Bb4:1', 'A4:1 Bb4:0.5 A4:0.5 G4:2']
B_A = ['C5:1.5 D5:0.5 E5:1 F5:1', 'G5:1.5 A5:0.5 Bb5:2', 'A5:1 G5:0.5 F5:0.5 E5:1 G5:1', 'F5:3 r:1']
B_A2 = ['C5:1.5 D5:0.5 E5:1 F5:1', 'G5:1.5 A5:0.5 D6:2', 'C6:1 Bb5:0.5 A5:0.5 G5:1 E5:1', 'F5:4']
B_COUNTER = ['C5:4', 'A4:2 D5:2', 'D5:2 F5:2', 'E5:2 Bb4:2', 'A4:2 C5:2', 'D5:2 F5:2', 'D5:2 C5:2', 'A4:4']
B_DARK = ['D5:1 E5:1 F5:2', 'Bb5:3 A5:0.5 G5:0.5', 'G5:1.5 F5:0.5 E5:1 D5:1', 'C#5:2 E5:1 A4:1']

CLOSE = ['F4:0.5 r:0.25 F4:0.25 C5:1 Bb4:0.5 A4:0.25 G4:0.25 A4:0.5 F4:0.5', 'E4:1.5 F4:0.5 G4:1 C4:1',
         'A4:0.5 r:0.25 A4:0.25 F5:1 E5:0.5 D5:0.25 C5:0.25 D5:0.5 Bb4:0.5', 'A4:1 G4:1 E4:1 C4:1',
         'F4:1 r:1 F4:1 r:1']

# the fugato countersubject (running 8ths), in G minor over Gm - D7; +7 = over Dm - A7
CS = ['Bb3:0.5 A3:0.5 G3:0.5 A3:0.5 Bb3:0.5 C4:0.5 D4:0.5 Bb3:0.5',
      'A3:0.5 F#3:0.5 G3:0.5 A3:0.5 D3:0.5 E3:0.5 F#3:0.5 D3:0.5']
CS_D = ['F4:0.5 E4:0.5 D4:0.5 E4:0.5 F4:0.5 G4:0.5 A4:0.5 F4:0.5',
        'E4:0.5 C#4:0.5 D4:0.5 E4:0.5 A3:0.5 B3:0.5 C#4:0.5 A3:0.5']

DYN = {
    'motto': [(0, 'ff'), (12, 'p', 'step'), (16, 'p')],
    'A': [(0, 'p'), (16, 'p'), (24, 'mf'), (28, 'mp'), (32, 'p'), (32.01, 'f', 'step'), (48, 'ff'), (60, 'ff'),
          (64, 'f')],
    'trans': [(0, 'f'), (16, 'ff'), (24, 'f'), (32, 'p')],
    'B': [(0, 'p'), (4, 'mp'), (8, 'p'), (16, 'p'), (20, 'mp'), (28, 'p'), (32, 'mp'), (52, 'mf'), (56, 'f'),
          (62, 'mp'), (64, 'mp')],
    'closing': [(0, 'f'), (12, 'ff'), (20, 'pp', 'step'), (24, 'pp')],
    'fugato': [(0, 'p'), (16, 'mp'), (24, 'mf'), (32, 'f')],
    'seq': [(0, 'f'), (8, 'p', 'step'), (16, 'f', 'step'), (24, 'ff'), (32, 'ff')],
    'storm': [(0, 'ff'), (16, 'f'), (24, 'ff'), (32, 'f')],
    'pedal': [(0, 'p', 'step'), (16, 'mp'), (28, 'f'), (32, 'ff')],
    'recap': [(0, 'ff'), (28, 'ff'), (32, 'f')],
    'trans2': [(0, 'f'), (8, 'mf'), (14, 'p'), (16, 'p')],
    'B2': [(0, 'p'), (16, 'mp'), (28, 'mp'), (32, 'f', 'step'), (40, 'ff'), (44, 'f'), (48, 'f')],
    'coda': [(0, 'ff'), (20, 'ff'), (24, 'f'), (28, 'ff'), (40, 'ff')],
}


def N(x):
    return _note(x)


def mel(t0, bars, shift=0):
    """Bars of 'pitch:beats' tokens (r = rest) from t0 -> (start, dur, pitch) notes; every bar must fill 4 beats."""
    out, t = [], t0
    for bar in bars:
        tot = 0.0
        for tok in bar.split():
            p, d = tok.split(':')
            d = float(d)
            if p != 'r':
                out.append((t + tot, d, N(p) + shift))
            tot += d
        assert abs(tot - 4) < 1e-9, (bar, tot)
        t += 4
    return out


def frag(t0, text, shift=0):
    """A fragment shorter than a bar: 'pitch:beats' tokens from t0."""
    out, t = [], t0
    for tok in text.split():
        p, d = tok.split(':')
        if p != 'r':
            out.append((t, float(d), N(p) + shift))
        t += float(d)
    return out


def up(notes, k):
    return [(a, d, p + k) for a, d, p in notes]


def chart(t0, text):
    out, t = [], t0
    for bar in text.split('|'):
        toks = bar.split()
        durs = [float(x.split(':')[1]) if ':' in x else None for x in toks]
        rest = (4 - sum(d for d in durs if d)) / max(1, durs.count(None)) if None in durs else 0
        for tok, d in zip(toks, durs):
            d = d or rest
            out.append((t, d, tok.split(':')[0]))
            t += d
    return out


def tones(sym):
    c = _chord(sym)
    iv = sorted(set(c.intervals))
    third = next((i for i in (4, 3, 5, 2) if i in iv), 4)
    fifth = next((i for i in (7, 6, 8) if i in iv), 7)
    return c.root, third, fifth, (c.bass if c.bass is not None else c.root)


def low(pc, lo):
    """The lowest pitch of pitch class pc at or above lo (a note name)."""
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


def voicings(ch, register, n):
    lo, hi = N(register[0]), N(register[1])
    return voice_lead([c[2] for c in ch], register=(lo, max(hi, lo + 11)), voices=n)


def pad(ch, register, n, legato=1.0):
    """The chords voice-led in a register, held pitches tied."""
    return tie([(t, d * legato, p) for (t, d, _), v in zip(ch, voicings(ch, register, n)) for p in v])


def bass(ch, lo, legato=1.0, root=False):
    return tie([(t, d * legato, low(tones(s)[0] if root else tones(s)[3], lo)) for t, d, s in ch])


def agitato(ch, register, n, step=0.5, ln=0.4):
    """Repeated 8ths on the voice-led chord (the agitato tremor of the inner strings)."""
    return [(t + step * k, ln, p) for (t, d, _), v in zip(ch, voicings(ch, register, n))
            for k in range(int(round(d / step))) for p in v]


def ladder(sym, lo, n=8):
    c = _chord(sym)
    pcs = {(c.root + i) % 12 for i in c.intervals}
    p, out = N(lo), []
    while len(out) < n:
        if p % 12 in pcs:
            out.append(p)
        p += 1
    return out


RUN = [0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1, 0, 1, 2, 3]


def run16(ch, lo, pat=RUN, step=0.25):
    """16th figuration up and down the chord from lo (the strings' drive)."""
    out = []
    for t, d, s in ch:
        lad = ladder(s, lo)
        for k in range(int(round(d / step))):
            out.append((t + step * k, step * 0.9, lad[pat[k % len(pat)]]))
    return out


def drive8(ch, lo, octave=True):
    """Repeated 8ths on the bass note, the octave on the off-beat of beats 2 and 4."""
    out = []
    for t, d, s in ch:
        b = low(tones(s)[3], lo)
        for k in range(int(round(d * 2))):
            out.append((t + 0.5 * k, 0.42, b + (12 if octave and k % 4 == 3 else 0)))
    return out


def beats(ch, lo, every=1.0, ln=0.8, root=False):
    out = []
    for t, d, s in ch:
        b = low(tones(s)[0] if root else tones(s)[3], lo)
        for k in range(int(round(d / every))):
            out.append((t + every * k, ln, b))
    return out


def pulsepad(ch, register, n):
    """The chords voice-led, each struck (1.5 beats) and re-struck on beat 3 (the brass punctuating a tutti)."""
    out = []
    for (t, d, _), v in zip(ch, voicings(ch, register, n)):
        for p in v:
            out.append((t, min(d, 1.5), p))
            if d >= 4:
                out.append((t + 2, d - 2, p))
    return out


def struck(n, t0):
    """offs for pulsepad: the downbeat strong, the re-strike lighter."""
    return 5 if abs((n[0] - t0) % 4) < 1e-3 else -5


def accent(t0, big=7, beat=2, weak=-4):
    """offs: downbeats strong, beats medium, off-beats (16ths) lighter."""
    def f(n):
        ph = (n[0] - t0) % 4
        if abs(ph) < 1e-3:
            return big
        if abs(ph - round(ph)) < 1e-3:
            return beat
        return weak
    return f


def hairpin(t0, length, lo=-6, hi=6, peak=0.6):
    """offs: a crescendo to `peak` of the span, then a diminuendo."""
    def f(n):
        x = min(1.0, max(0.0, (n[0] - t0) / length))
        return lo + (hi - lo) * (x / peak if x < peak else (1 - x) / (1 - peak))
    return f


def cresc(t0, length, lo=-6, hi=6):
    return lambda n: lo + (hi - lo) * min(1.0, max(0.0, (n[0] - t0) / length))


def both(*fs):
    return lambda n: sum(f(n) for f in fs)


def build() -> Song:
    s = Song('Tempest Allegro', tempo=TEMPO, key=KEY, seed=SEED, tail=6)
    S = {name: s.section(name, bars=bars) for name, bars in FORM}
    T = {name: S[name].start for name in S}
    CH = {name: chart(T[name], CHART[name]) for name in S}
    s.endless_timeline = [c for name, _ in FORM for c in CH[name]]

    b = orchestra_band(s, ROLES)
    sc = orch.Score(s, b, DYN, key=KEY, seed=SEED, style='romantic')
    add = sc.add

    # -------------------------------------------------------------------------------------- time
    s.fermata(S['motto'].bar(3) + 2, hold=1.0)                                  # the A7 stroke rings
    s.ritardando((S['trans'].bar(6), S['B'].start), to=0.85, a_tempo=True)     # into the second theme
    s.ritardando((S['B'].bar(14), S['B'].bar(16)), to=0.9, a_tempo=True)
    s.ritardando((S['closing'].bar(5), S['fugato'].start), to=0.88, a_tempo=True)
    s.fermata(S['pedal'].bar(7) + 3, hold=1.5)                                  # the breath before the return
    s.ritardando((S['B2'].bar(10), S['B2'].bar(12)), to=0.9, a_tempo=True)
    s.ritardando((S['coda'].bar(7), S['coda'].bar(9)), to=0.85, a_tempo=True)
    s.fermata(S['coda'].bar(9), hold=3.0)

    # ====================================================================================== EXPOSITION
    # -------------------------------------------------------------------------------------- motto: ff in octaves
    t, ch = T['motto'], CH['motto']
    mot = mel(t, [M1, M2])
    acc = accent(t, 8, 2, -4)
    add('violins1', up(mot, 12), 'marcato', off=4, offs=acc, line=True)
    add('violins2', mot, 'marcato', off=2, offs=acc, line=True)
    add('violas', mot, 'marcato', off=0, offs=acc, line=True)
    add('cellos', up(mot, -12), 'marcato', off=2, offs=acc, line=True)
    add('basses', up(mot, -24), 'marcato', off=0, offs=acc, line=True)
    add('flutes', up(mot, 24), off=-2, offs=acc, line=True)
    add('oboes', up(mot, 12), off=-2, offs=acc, line=True)
    add('clarinets', mot, off=-4, offs=acc, line=True)
    add('bassoons', up(mot, -12), off=-2, offs=acc, line=True)
    add('horns', mel(t, [M1_BRASS, M2]), 'marcato', off=0, offs=acc, line=True)
    add('trombones', [(t + 1, 2, N('A3')), (t + 4, 2, N('A3')), (t + 6, 2, N('E3'))], 'marcato', off=-2,
        offs=lambda n: 4 if n[0] == t + 1 else -2, line=False)
    add('timpani', [(t, 0.5, N('D3'), 108), (t + 0.75, 0.25, N('D3'), 84), (t + 1, 1, N('A2'), 100),
                    (t + 4, 1.5, N('A2'), 98), (t + 7, 1, N('A2'), 90)], 'hit', line=False)
    # bar 3: two hammer-strokes, the second held under the fermata
    tb = t + 8
    for role, reg, nv, o in (('violins1', ('D5', 'D6'), 3, 6), ('violins2', ('F4', 'D5'), 2, 4),
                             ('violas', ('A3', 'F4'), 2, 2), ('flutes', ('D5', 'D6'), 2, 0),
                             ('oboes', ('F4', 'D5'), 2, 0), ('clarinets', ('A3', 'F4'), 2, -2),
                             ('horns', ('D3', 'D4'), 2, 2), ('trumpets', ('A4', 'D5'), 2, 2),
                             ('trombones', ('D3', 'A3'), 2, 0)):
        vs = voicings(CH['motto'][2:4], reg, nv)
        add(role, [(tb, 1.0, p) for p in vs[0]] + [(tb + 2, 2.0, p) for p in vs[1]], 'marcato', off=o,
            offs=lambda n: 4 if n[0] == tb else 0, line=False)
    add('cellos', [(tb, 1, N('D3')), (tb + 2, 2, N('A2'))], 'marcato', off=4, line=False)
    add('basses', [(tb, 1, N('D2')), (tb + 2, 2, N('A1'))], 'marcato', off=2, line=False)
    add('bassoons', [(tb, 1, N('D3')), (tb + 2, 2, N('A2'))], off=0, line=False)
    add('tuba', [(tb, 1, N('D2')), (tb + 2, 2, N('A1'))], 'marcato', off=-2, line=False)
    add('timpani', [(tb, 1, N('D3'), 112), (tb + 2, 1.5, N('A2'), 106)], 'hit', line=False)
    # bar 4: subito p, the agitato begins
    t4 = t + 12
    add('violas', agitato([(t4, 4, 'Dm')], ('A3', 'F4'), 2), 'staccato', off=-4, offs=accent(t4, 4, 1, -2),
        line=False)
    add('cellos', [(t4 + 0.5 * k, 0.4, N('D3')) for k in range(8)], 'staccato', off=-4, offs=accent(t4, 4, 1, -2),
        line=False)

    # -------------------------------------------------------------------------------------- A: the first theme
    t, ch = T['A'], CH['A']
    a1, a2 = ch[:10], ch[10:]
    th1 = mel(t, T1A)
    add('violins1', up(th1, 12), off=6, offs=both(accent(t, 4, 1, -3), hairpin(t, 32, -4, 6, 0.75)), line=True)
    add('violas', agitato(a1, ('A3', 'F4'), 2), 'staccato', off=-8, offs=accent(t, 3, 1, -2), line=False)
    add('violins2', agitato(a1[4:], ('D4', 'A4'), 2), 'staccato', off=-8, offs=accent(t, 3, 1, -2), line=False)
    add('cellos', beats(a1, 'D2', 1.0, 0.5), 'staccato', off=-4, offs=accent(t, 4, -1, 0), line=False)
    add('basses', beats(a1, 'D1', 2.0, 0.6), 'pizzicato', off=0, line=False)
    add('bassoons', pad(a1[4:], ('A2', 'F3'), 2), off=-8, offs=hairpin(t + 16, 16, -4, 4), line=False)
    add('horns', [(t + 28, 1.5, N('A3')), (t + 28, 1.5, N('E4')), (t + 29.5, 2.5, N('A3')), (t + 29.5, 2.5, N('E4'))],
        off=-6, offs=lambda n: 4 if n[0] == t + 28 else -4, line=False)
    add('timpani', [(t + 28, 3.5, N('A2'))], 'roll', off=-14, line=False)
    # the consequent: subito f tutti
    t2 = t + 32
    th2 = mel(t2, T1B)
    acc2 = both(accent(t2, 6, 2, -3), hairpin(t2, 32, -4, 6, 0.7))
    add('violins1', up(th2, 12), off=6, offs=acc2, line=True)
    add('flutes', up(th2, 12), off=0, offs=acc2, line=True)
    add('oboes', th2, off=-2, offs=acc2, line=True)
    add('clarinets', [n for n in th2 if n[2] >= N('D4')], off=-6, offs=acc2, line=True)
    add('violins2', run16(a2, 'D4'), 'spiccato', off=-6, offs=accent(t2, 5, 1, -3), line=False)
    add('violas', run16(a2, 'A3', [0, 1, 2, 3, 2, 1, 0, 1]), 'spiccato', off=-6, offs=accent(t2, 5, 1, -3),
        line=False)
    add('cellos', drive8(a2, 'D2'), 'staccato', off=-2, offs=accent(t2, 6, 2, -3), line=False)
    add('basses', beats(a2, 'D1', 1.0, 0.7), 'staccato', off=-2, offs=accent(t2, 6, 0, 0), line=False)
    add('horns', pulsepad(a2, ('D3', 'D4'), 2), off=-6, offs=both(hairpin(t2, 32, -5, 5), lambda n: struck(n, t2)),
        line=False)
    add('bassoons', bass(a2, 'D2'), off=-6, line=False)
    add('trumpets', [(t2, 1, N('D5')), (t2 + 4, 1, N('C#5')), (t2 + 16, 1, N('D5')), (t2 + 24, 2, N('D5')),
                     (t2 + 26, 2, N('C#5')), (t2 + 28, 1.5, N('D5'))], 'marcato', off=-2,
        offs=lambda n: 4 if (n[0] - t2) % 16 == 0 else -2, line=False)
    add('trombones', pad(a2[8:], ('D3', 'A3'), 2), off=-6, offs=cresc(t2 + 20, 12, -4, 4), line=False)
    add('timpani', [(t2, 1, N('D3'), 96), (t2 + 4, 1, N('A2'), 84), (t2 + 16, 1, N('D3'), 92),
                    (t2 + 24, 1, N('A2'), 90), (t2 + 26, 1, N('A2'), 96), (t2 + 28, 1, N('D3'), 108),
                    (t2 + 29, 1, N('D3'), 92), (t2 + 30, 0.5, N('A2'), 100)], 'hit', line=False)

    # -------------------------------------------------------------------------------------- trans: Dm -> C7
    t, ch = T['trans'], CH['trans']
    add('violins1', run16(ch, 'D5'), 'spiccato', off=0, offs=both(accent(t, 5, 1, -3), hairpin(t, 32, -4, 4, 0.55)),
        line=False)
    add('violins2', run16(ch, 'F4', [0, 1, 2, 3, 2, 1, 2, 1]), 'spiccato', off=-4, offs=accent(t, 4, 1, -3),
        line=False)
    # the motto's head in the bass, each bar on the chord root
    lowhead = []
    for st, d, sym in ch:
        r = low(tones(sym)[0], 'C3')
        lowhead += [(st, 0.5, r), (st + 0.75, 0.25, r), (st + 1, 1, r + 7), (st + 2, 0.5, r + 5),
                    (st + 2.5, 0.5, r + 3), (st + 3, 1, r)]
    accb = both(accent(t, 7, 2, -3), hairpin(t, 32, -2, 4, 0.5))
    add('cellos', lowhead, 'marcato', off=2, offs=accb,
        line=True)
    add('bassoons', lowhead, off=-2, offs=accb, line=True)
    add('violas', lowhead, 'marcato', off=-2, offs=accb,
        line=False)
    add('basses', beats(ch, 'C1', 2.0, 1.6), off=-2, offs=accent(t, 4, 0, 0), line=False)
    add('horns', pad(ch, ('C3', 'C4'), 2), off=-6, offs=hairpin(t, 32, -4, 4, 0.45), line=False)
    wp = pad(ch[:6], ('D5', 'D6'), 2)
    add('flutes', wp, off=-6, offs=hairpin(t, 24, -4, 4, 0.5), line=False)
    add('oboes', pad(ch[:6], ('F4', 'D5'), 2), off=-8, offs=hairpin(t, 24, -4, 4, 0.5), line=False)
    add('trumpets', [(t + 4 * k, 1, low(tones(ch[k][2])[0], 'C4') + 12 * (low(tones(ch[k][2])[0], 'C4') < N('G4')))
                     for k in (0, 2, 4)], 'marcato', off=-4, line=False)
    add('timpani', [(t, 1, N('D3'), 94), (t + 12, 1, N('A2'), 88), (t + 28, 3.5, N('C3'))], 'hit', line=False)
    add('clarinets', [(t + 28, 4, N('C4')), (t + 28, 4, N('E4'))], off=-6, offs=lambda n: 0, line=False)

    # -------------------------------------------------------------------------------------- B: the lyrical theme
    t, ch = T['B'], CH['B']
    b1, b2 = ch[:9], ch[9:]
    q = mel(t, B_Q)
    a = mel(t + 16, B_A)
    add('clarinets', q, off=8, offs=hairpin(t, 16, -6, 6, 0.4), line=True)
    add('flutes', a, off=6, offs=hairpin(t + 16, 16, -6, 6, 0.55), line=True)
    add('oboes', [(t + 20, 4, N('D5')), (t + 24, 2, N('E5')), (t + 26, 2, N('C5')), (t + 28, 4, N('C5'))], off=-4,
        offs=hairpin(t + 20, 12, -4, 4), line=False)
    add('violas', [(st + 0.5 * k, 0.45, lad[(0, 1, 2, 3, 2, 1, 2, 1)[k % 8]]) for st, d, sym in b1
                   for lad in [ladder(sym, 'C3', 5)] for k in range(int(round(d * 2)))], 'staccato', off=-12,
        offs=accent(t, 3, 0, -2), line=False)
    piz = beats(b1, 'F2', 2.0, 0.6)
    add('cellos', piz, 'pizzicato', off=-2, line=False)
    add('basses', up(piz, -12), 'pizzicato', off=-4, line=False)
    add('violins2', pad(b1, ('A4', 'F5'), 1), off=-12, offs=hairpin(t, 32, -4, 4, 0.5), line=False)
    add('horns', pad(b1[4:], ('C3', 'A3'), 2), off=-12, offs=hairpin(t + 16, 16, -3, 3), line=False)
    add('harp', [(st + 0.5 * k, 1.5, lad[k % 6]) for st, d, sym in b1[4:8] for lad in [ladder(sym, 'F3', 6)]
                 for k in range(int(round(d * 2)))], None, off=6, line=False)
    # the restatement: violins I + II in octaves, the peak lifted
    t2 = t + 32
    th = mel(t2, B_Q + B_A2)
    add('violins1', th, off=6, offs=lambda n: hairpin(t2, 16, -5, 5, 0.4)(n) if n[0] < t2 + 16
        else hairpin(t2 + 16, 16, -5, 5, 0.55)(n), line=True)
    add('violins2', up(th, -12), off=2, offs=lambda n: hairpin(t2, 16, -5, 5, 0.4)(n) if n[0] < t2 + 16
        else hairpin(t2 + 16, 16, -5, 5, 0.55)(n), line=True)
    add('flutes', up(mel(t2, B_COUNTER), 12), off=-4, offs=hairpin(t2, 32, -6, 4, 0.75), line=False)
    add('oboes', mel(t2, B_COUNTER), off=-6, offs=hairpin(t2, 32, -6, 4, 0.75), line=False)
    add('violas', [(st + 0.5 * k, 0.45, lad[(0, 1, 2, 3, 2, 1, 2, 1)[k % 8]]) for st, d, sym in b2
                   for lad in [ladder(sym, 'C3', 5)] for k in range(int(round(d * 2)))], 'staccato', off=-10,
        offs=accent(t2, 3, 0, -2), line=False)
    add('cellos', bass(b2, 'F2'), off=-6, offs=hairpin(t2, 32, -4, 4), line=False)
    add('basses', beats(b2, 'F1', 2.0, 1.2), 'pizzicato', off=-4, line=False)
    add('clarinets', pad(b2, ('C4', 'A4'), 2), off=-12, offs=hairpin(t2, 32, -4, 4, 0.75), line=False)
    add('horns', pad(b2[4:], ('C3', 'A3'), 2), off=-10, offs=hairpin(t2 + 16, 16, -4, 4), line=False)
    add('bassoons', bass(b2[:4], 'F2'), off=-12, line=False)

    # -------------------------------------------------------------------------------------- closing: the motto in major
    t, ch = T['closing'], CH['closing']
    cl = mel(t, CLOSE)
    accc = both(accent(t, 6, 2, -3), hairpin(t, 20, -2, 4, 0.6))
    add('violins1', up(cl, 12), off=6, offs=accc, line=True)
    add('violins2', cl, off=2, offs=accc, line=True)
    add('flutes', up(cl, 12), off=0, offs=accc, line=True)
    add('oboes', [n for n in cl if n[2] >= N('C4')], off=-2, offs=accc, line=True)
    add('violas', run16(ch[:5], 'C3', [0, 1, 2, 3, 2, 1, 0, 1]), 'spiccato', off=-6, offs=accent(t, 4, 1, -3),
        line=False)
    add('cellos', drive8(ch[:5], 'F2'), 'staccato', off=-2, offs=accent(t, 6, 2, -3), line=False)
    add('basses', beats(ch[:5], 'F1', 1.0, 0.7), 'staccato', off=-2, line=False)
    add('horns', pad(ch[:4], ('C3', 'C4'), 2), off=-4, offs=hairpin(t, 16, -3, 4), line=False)
    add('trumpets', [(t, 1, N('C5')), (t + 4, 1, N('C5')), (t + 8, 1, N('C5')), (t + 12, 2, N('C5')),
                     (t + 14, 2, N('E5'))], 'marcato', off=-4, offs=lambda n: 3 if n[0] >= t + 12 else -2,
        line=False)
    add('trombones', pad(ch[2:4], ('C3', 'A3'), 2), off=-6, line=False)
    add('clarinets', pad(ch[:4], ('C4', 'A4'), 2), off=-8, line=False)
    tc = t + 16
    for role, reg, nv, o in (('violins1', ('F5', 'F6'), 2, 4), ('violins2', ('A4', 'F5'), 2, 2),
                             ('violas', ('C4', 'A4'), 2, 0), ('flutes', ('C6', 'A6'), 2, 0),
                             ('oboes', ('F4', 'C5'), 2, -2), ('clarinets', ('A3', 'F4'), 2, -2),
                             ('horns', ('C3', 'C4'), 2, 0), ('trumpets', ('F4', 'C5'), 2, 0),
                             ('trombones', ('F2', 'C3'), 2, -2)):
        v = voicings([(tc, 4, 'F')], reg, nv)[0]
        add(role, [(tc + o2, 1.0, p) for o2 in (0, 2) for p in v], 'marcato', off=o,
            offs=lambda n: 3 if n[0] == tc else 0, line=False)
    add('cellos', [(tc, 1, N('F2')), (tc + 2, 1, N('F2'))], 'marcato', off=2, line=False)
    add('basses', [(tc, 1, N('F1')), (tc + 2, 1, N('F1'))], 'marcato', off=0, line=False)
    add('tuba', [(tc, 1, N('F1')), (tc + 2, 1, N('F1'))], 'marcato', off=-4, line=False)
    add('timpani', [(t, 1, N('A2'), 84), (t + 12, 1, N('A2'), 90), (tc, 1, N('A2'), 104), (tc + 2, 1, N('A2'), 108)],
        'hit', line=False)
    # bar 6: the bassoon's echo of the head, pp
    te = t + 20
    add('bassoons', frag(te, 'F3:0.5 r:0.25 F3:0.25 C4:1 Bb3:0.5 A3:0.5 G3:1'), off=6,
        offs=lambda n: 4 if n[0] == te else -2, line=True)
    add('cellos', [(te, 4, N('F2'))], off=-6, line=False)

    # ====================================================================================== DEVELOPMENT
    # -------------------------------------------------------------------------------------- fugato on the motto
    t, ch = T['fugato'], CH['fugato']
    subj = lambda t0, sh: mel(t0, [M1, M2], sh)
    fa = lambda t0: both(accent(t0, 5, 1, -3), hairpin(t0, 8, -3, 4, 0.3))
    add('cellos', subj(t, 5 - 12), off=6, offs=fa(t), line=True)
    add('bassoons', subj(t, 5 - 12), off=2, offs=fa(t), line=True)
    add('cellos', mel(t + 8, CS_D, -12), off=0, offs=hairpin(t + 8, 8, -3, 3), line=True)
    add('cellos', bass(ch[4:], 'G2'), off=-2, offs=cresc(t + 16, 16, -4, 4), line=False)
    add('basses', bass(ch[2:], 'G1'), off=-6, offs=cresc(t + 8, 24, -6, 4), line=False)
    add('violas', subj(t + 8, 0), off=6, offs=fa(t + 8), line=True)
    add('clarinets', subj(t + 8, 0), off=0, offs=fa(t + 8), line=True)
    add('violas', mel(t + 16, CS), off=0, offs=hairpin(t + 16, 8, -3, 3), line=True)
    add('violas', pad(ch[6:], ('C#4', 'A4'), 1), off=-4, line=False)
    add('violins2', subj(t + 16, 5), off=6, offs=fa(t + 16), line=True)
    add('oboes', subj(t + 16, 5), off=0, offs=fa(t + 16), line=True)
    add('violins2', mel(t + 24, CS_D), off=0, offs=hairpin(t + 24, 8, -3, 3), line=True)
    add('violins1', subj(t + 24, 12), off=8, offs=fa(t + 24), line=True)
    add('flutes', subj(t + 24, 12), off=2, offs=fa(t + 24), line=True)
    add('horns', [(t + 24, 8, N('A3')), (t + 24, 8, N('D4'))], off=-6, offs=lambda n: 0, line=False)
    add('bassoons', bass(ch[4:], 'G2'), off=-6, line=False)

    # -------------------------------------------------------------------------------------- seq: the head through keys
    t, ch = T['seq'], CH['seq']
    for k, sh in enumerate((-2, 0, 1)):
        t0 = t + 8 * k
        sub = ch[2 * k:2 * k + 2]
        # woodwinds call (the motto's bar), horns + trombones answer (the brass version), an octave lower
        wa = both(accent(t0, 6, 1, -3), hairpin(t0, 4, -2, 3, 0.3))
        add('flutes', mel(t0, [M1], sh + 12), off=2, offs=wa, line=True)
        add('oboes', mel(t0, [M1], sh + 12), off=0, offs=wa, line=True)
        add('clarinets', mel(t0, [M1], sh), off=-2, offs=wa, line=True)
        ba = both(accent(t0 + 4, 6, 1, -2), hairpin(t0 + 4, 4, -2, 3, 0.3))
        add('horns', mel(t0 + 4, [M1_BRASS], sh), off=4, offs=ba, line=True)
        add('trombones', [n for n in mel(t0 + 4, [M1_BRASS], sh - 12)], off=-2, offs=ba, line=True)
        add('violins1', run16(sub, ('C5', 'D5', 'Eb5')[k]), 'spiccato', off=-4, offs=accent(t0, 5, 1, -3), line=False)
        add('violins2', agitato(sub, ('G4', 'D5'), 2), 'staccato', off=-10, offs=accent(t0, 4, 1, -2), line=False)
        add('violas', agitato(sub, ('C4', 'G4'), 2), 'staccato', off=-6, offs=accent(t0, 4, 1, -2), line=False)
        add('cellos', drive8(sub, 'C2'), 'staccato', off=-2, offs=accent(t0, 6, 2, -3), line=False)
        add('basses', beats(sub, 'C1', 2.0, 1.4), off=-2, line=False)
        add('timpani', [(t0, 1, N('C3') if k == 0 else N('D3') if k == 1 else N('D3'), 92)], 'hit', line=False)
    # bars 7-8: the head on Edim7, tossed between the sections each half bar
    t0 = t + 24
    # (a falling cascade down the diminished chord, a beat per section)
    tosses = [('violins1', 'C#6', 'spiccato'), ('flutes', 'Bb5', 'sustain'), ('violins2', 'G5', 'spiccato'),
              ('clarinets', 'E5', 'sustain'), ('violas', 'C#5', 'spiccato'), ('oboes', 'Bb4', 'sustain'),
              ('cellos', 'G4', 'marcato'), ('horns', 'E4', 'sustain')]
    for k, (role, p0, art) in enumerate(tosses):
        st, base = t0 + k, N(p0)
        add(role, [(st, 0.4, base), (st + 0.5, 0.5, base - 3)], art, off=2,
            offs=lambda n, st=st: 4 if n[0] == st else -1, line=False)
    add('basses', [(t0, 8, N('E1'))], 'tremolo', off=-4, offs=lambda n: 0, line=False)
    add('trumpets', [(t0 + 6, 2, N('Bb4')), (t0 + 6, 2, N('E5'))], 'sustain', off=-4, offs=lambda n: 0, line=False)
    add('timpani', [(t0 + 4, 4, N('E3'))], 'roll', off=-6, line=False)

    # -------------------------------------------------------------------------------------- storm: the motto in the bass
    t, ch = T['storm'], CH['storm']
    bm = mel(t, [M1, M2, M1, M2], 5 - 24)            # G minor, G2
    accs = both(accent(t, 7, 2, -3), hairpin(t, 16, -2, 3, 0.5))
    add('cellos', bm, 'marcato', off=6, offs=accs, line=True)
    add('basses', up(bm, -12), 'marcato', off=-1, offs=accs, line=True)
    add('bassoons', bm, off=2, offs=accs, line=True)
    add('trombones', mel(t, [M1_BRASS, M2, M1_BRASS, M2], 5 - 24), off=0, offs=accs, line=True)
    add('tuba', up(mel(t, [M1_BRASS, M2, M1_BRASS, M2], 5 - 24), -12), off=-2, offs=accs, line=True)
    add('violins1', pad(ch[:4], ('D5', 'D6'), 2), 'tremolo', off=-2, offs=hairpin(t, 16, -2, 3, 0.5), line=False)
    add('violins2', pad(ch[:4], ('G4', 'D5'), 2), 'tremolo', off=-2, offs=hairpin(t, 16, -2, 3, 0.5), line=False)
    add('violas', pad(ch[:4], ('Bb3', 'G4'), 2), 'tremolo', off=-4, offs=hairpin(t, 16, -2, 3, 0.5), line=False)
    add('horns', pad(ch[:4], ('D4', 'Bb4'), 2), off=-4, offs=hairpin(t, 16, -3, 3, 0.5), line=False)
    add('oboes', pad(ch[:4], ('D5', 'Bb5'), 2), off=-6, offs=hairpin(t, 16, -3, 3, 0.5), line=False)
    add('trumpets', [(t + 4 * k + a, 0.75 if a == 0 else 0.4, N('D5')) for k in range(4) for a in (0, 1.5)], 'marcato',
        off=-4, offs=lambda n: (5 if (n[0] - t) % 4 == 0 else -6) + (4 if (n[0] - t) % 8 == 0 else 0),
        line=False)
    add('timpani', [(t + 4 * k + a, 0.5, N('D3') if k % 2 else N('G2'), 88 + (12 if a == 0 else 0))
                    for k in range(4) for a in (0, 1.5)], 'hit', line=False)
    # bars 5-8: Eb - C#dim7 - Bb - E7, hammered chords, violins storm in 16ths
    t5, c5 = t + 16, ch[4:]
    add('violins1', run16(c5, 'Eb5'), 'spiccato', off=0, offs=both(accent(t5, 6, 1, -3), cresc(t5, 16, -2, 4)),
        line=False)
    add('violins2', run16(c5, 'G4', [0, 1, 2, 3, 2, 1, 2, 1]), 'spiccato', off=-4, offs=accent(t5, 5, 1, -3),
        line=False)
    add('violas', agitato(c5, ('Bb3', 'G4'), 2), 'staccato', off=-4, offs=accent(t5, 5, 1, -2), line=False)
    hits = []
    for st, d, sym in c5:
        hits += [(st, 1.0, sym), (st + 1.5, 0.5, sym), (st + 2, 2, sym)]
    for role, reg, nv, o in (('horns', ('Eb3', 'Eb4'), 2, 0), ('trombones', ('Bb2', 'G3'), 2, -2),
                             ('flutes', ('Bb5', 'G6'), 2, -2), ('oboes', ('Eb5', 'Bb5'), 2, -4),
                             ('clarinets', ('G4', 'Eb5'), 2, -4), ('trumpets', ('G4', 'D5'), 1, -2)):
        vs = voicings([(a, d, x) for a, d, x in hits], reg, nv)
        add(role, [(a, d * 0.95, p) for (a, d, _), v in zip(hits, vs) for p in v], 'marcato', off=o,
            offs=both(accent(t5, 5, 0, -4), cresc(t5, 16, -3, 3)), line=False)
    add('cellos', [(a, d * 0.9, low(tones(x)[3], 'C2')) for a, d, x in hits], 'marcato', off=2,
        offs=accent(t5, 5, 0, -3), line=False)
    add('basses', [(a, d * 0.9, low(tones(x)[3], 'C1')) for a, d, x in hits], 'marcato', off=0,
        offs=accent(t5, 5, 0, -3), line=False)
    add('tuba', [(a, d * 0.9, low(tones(x)[3], 'C1')) for a, d, x in hits if (a - t5) % 4 == 0], off=-4, line=False)
    add('bassoons', [(a, d * 0.9, low(tones(x)[3], 'C2')) for a, d, x in hits], off=-2, line=False)
    add('timpani', [(t5 + 12, 4, N('E3'))], 'roll', off=-2, line=False)

    # -------------------------------------------------------------------------------------- pedal: the build on A
    t, ch = T['pedal'], CH['pedal']
    add('basses', [(t, 32, N('A1'))], 'tremolo', off=-2, offs=lambda n: 0, line=False)
    add('timpani', [(t, 28, N('A2'))], 'roll', off=-8, line=False)
    add('cellos', [(t + 0.5 * k, 0.42, N('A2') + (12 if k % 4 == 3 else 0)) for k in range(56)], 'staccato', off=-4,
        offs=both(accent(t, 4, 1, -2), cresc(t, 28, -3, 4)), line=False)
    add('violas', agitato(ch[:4], ('C#4', 'A4'), 2), 'staccato', off=-6, offs=cresc(t, 16, -4, 2), line=False)
    add('violas', run16(ch[4:], 'A3', [0, 1, 2, 3, 2, 1, 0, 1]), 'spiccato', off=-4,
        offs=both(accent(t + 16, 4, 1, -3), cresc(t + 16, 12, -2, 4)), line=False)
    add('violins2', agitato(ch[2:4], ('E4', 'C#5'), 2), 'staccato', off=-9, line=False)
    add('violins2', run16(ch[4:], 'E4'), 'spiccato', off=-8, offs=both(accent(t + 16, 4, 1, -3), cresc(t + 16, 12, -2, 4)),
        line=False)
    add('violins1', pad(ch[5:7], ('A5', 'A6'), 2), 'tremolo', off=-2, offs=cresc(t + 20, 8, -4, 4), line=False)
    # the head climbing in the winds, a bar each, rising
    climb = [('clarinets', 'A3', 0), ('oboes', 'C#4', 4), ('flutes', 'E4', 8), ('clarinets', 'A4', 12),
             ('oboes', 'C#5', 16), ('flutes', 'E5', 20)]
    for role, p0, at in climb:
        r = N(p0)
        add(role, [(t + at, 0.5, r), (t + at + 0.75, 0.25, r), (t + at + 1, 2.5, r + 5 if p0.startswith('C#') else r + 7)],
            off=4, offs=lambda n, st=t + at: 4 if n[0] == st else 0, line=False)
    add('horns', pad(ch[4:7], ('E3', 'C#4'), 2), off=-4, offs=cresc(t + 16, 12, -4, 4), line=False)
    add('trombones', pad(ch[5:7], ('C#3', 'A3'), 2), off=-6, offs=cresc(t + 20, 8, -4, 4), line=False)
    add('trumpets', [(t + 24, 3, N('A4')), (t + 24, 3, N('E5'))], off=-4, offs=lambda n: 0, line=False)
    add('bassoons', [(t + 16, 12, N('A2'))], off=-6, offs=lambda n: 0, line=False)
    # bar 8: the A7 stroke, then the silent breath before the return
    t8 = t + 28
    for role, reg, nv, o in (('violins1', ('C#5', 'G5'), 2, 4), ('violins2', ('E4', 'C#5'), 2, 2),
                             ('violas', ('A3', 'E4'), 2, 0), ('flutes', ('E5', 'C#6'), 2, 0),
                             ('oboes', ('A4', 'E5'), 2, -2), ('clarinets', ('C#4', 'G4'), 2, -2),
                             ('horns', ('E3', 'C#4'), 2, 2), ('trumpets', ('A4', 'E5'), 2, 2),
                             ('trombones', ('A2', 'E3'), 2, 0)):
        v = voicings([(t8, 3, 'A7')], reg, nv)[0]
        add(role, [(t8, 2.5, p) for p in v], 'marcato', off=o, line=False)
    add('cellos', [(t8, 2.5, N('A2'))], 'marcato', off=2, line=False)
    add('basses', [(t8, 2.5, N('A1'))], 'marcato', off=2, line=False)
    add('tuba', [(t8, 2.5, N('A1'))], 'marcato', off=-2, line=False)
    add('timpani', [(t8, 2, N('A2'), 112)], 'hit', line=False)

    # ====================================================================================== RECAPITULATION
    # -------------------------------------------------------------------------------------- recap: ff at once
    t, ch = T['recap'], CH['recap']
    th = mel(t, T1B)
    accr = both(accent(t, 6, 2, -3), hairpin(t, 32, -3, 4, 0.7))
    add('violins1', up(th, 12), off=6, offs=accr, line=True)
    add('flutes', up(th, 12), off=0, offs=accr, line=True)
    add('oboes', th, off=-2, offs=accr, line=True)
    add('trumpets', [n for n in th if N('D4') <= n[2] <= N('A5') and n[1] >= 0.5], off=-6, offs=accr, line=True)
    add('horns', mel(t, [M1_BRASS, M2]), off=0, offs=both(accr, accent(t, 4, 0, -3)), line=True)
    add('horns', pulsepad(ch[3:], ('D3', 'D4'), 2), off=-6, offs=both(hairpin(t + 12, 20, -5, 5), lambda n: struck(n, t)),
        line=False)
    add('violins2', run16(ch, 'D4'), 'spiccato', off=-4, offs=accent(t, 5, 1, -3), line=False)
    add('violas', run16(ch, 'A3', [0, 1, 2, 3, 2, 1, 0, 1]), 'spiccato', off=-4, offs=accent(t, 5, 1, -3),
        line=False)
    add('clarinets', pad(ch, ('A3', 'F4'), 2), off=-6, line=False)
    add('cellos', drive8(ch, 'D2'), 'staccato', off=0, offs=accent(t, 6, 2, -3), line=False)
    add('basses', beats(ch, 'D1', 1.0, 0.7), 'staccato', off=0, offs=accent(t, 6, 0, 0), line=False)
    add('bassoons', bass(ch, 'D2'), off=-4, line=False)
    add('trombones', pad(ch, ('D3', 'A3'), 2), off=-6, offs=hairpin(t, 32, -3, 3), line=False)
    add('tuba', bass(ch, 'D1'), off=-6, line=False)
    add('timpani', [(t, 1, N('D3'), 112), (t + 4, 1, N('A2'), 92), (t + 12, 1, N('D3'), 96),
                    (t + 24, 1, N('A2'), 96), (t + 26, 1, N('A2'), 100), (t + 28, 1, N('D3'), 110)], 'hit',
        line=False)

    # -------------------------------------------------------------------------------------- trans2: to the major
    t, ch = T['trans2'], CH['trans2']
    add('violins1', run16(ch, 'D5', [0, 1, 2, 3, 4, 3, 2, 1]), 'spiccato', off=-2,
        offs=both(accent(t, 4, 1, -3), cresc(t, 16, 2, -6)), line=False)
    add('violins2', agitato(ch, ('F4', 'D5'), 2), 'staccato', off=-6, offs=cresc(t, 16, 0, -6), line=False)
    add('violas', agitato(ch, ('A3', 'F4'), 2), 'staccato', off=-6, offs=cresc(t, 16, 0, -6), line=False)
    add('cellos', frag(t, 'D3:0.5 r:0.25 D3:0.25 A3:1 G3:1 r:1') + frag(t + 4, 'G2:0.5 r:0.25 G2:0.25 D3:1 C3:1 r:1')
        + frag(t + 8, 'E3:0.5 r:0.25 E3:0.25 Bb3:1 A3:1 r:1') + [(t + 12, 4, N('A2'))], off=4,
        offs=both(accent(t, 5, 1, -3), cresc(t, 16, 0, -6)), line=True)
    add('basses', bass(ch, 'D1'), off=-4, line=False)
    add('bassoons', pad(ch, ('D3', 'Bb3'), 1), off=-6, offs=cresc(t, 16, 0, -6), line=False)
    add('horns', [(t + 12, 4, N('A3')), (t + 12, 4, N('E4'))], off=-8, offs=lambda n: 0, line=False)

    # -------------------------------------------------------------------------------------- B2: the tonic major
    t, ch = T['B2'], CH['B2']
    q = mel(t, B_Q, -15)
    add('cellos', q, off=8, offs=hairpin(t, 16, -6, 6, 0.4), line=True)
    a = mel(t + 16, B_A, -3)
    add('violins1', a, off=6, offs=hairpin(t + 16, 16, -6, 6, 0.55), line=True)
    add('flutes', up(a, 12), off=0, offs=hairpin(t + 16, 16, -6, 6, 0.55), line=True)
    add('violas', [(st + 0.5 * k, 0.45, lad[(0, 1, 2, 3, 2, 1, 2, 1)[k % 8]]) for st, d, sym in ch[:9]
                   for lad in [ladder(sym, 'A3', 5)] for k in range(int(round(d * 2)))], 'staccato', off=-12,
        offs=accent(t, 3, 0, -2), line=False)
    add('violins2', pad(ch[:9], ('F#4', 'D5'), 2), off=-12, offs=hairpin(t, 32, -4, 4, 0.5), line=False)
    add('basses', beats(ch[:9], 'D1', 2.0, 0.6), 'pizzicato', off=-2, line=False)
    add('cellos', bass(ch[4:9], 'D2'), off=-8, line=False)
    add('horns', pad(ch[:4], ('D3', 'A3'), 2), off=-12, offs=hairpin(t, 16, -3, 3), line=False)
    add('clarinets', pad(ch[4:9], ('F#3', 'D4'), 2), off=-12, offs=hairpin(t + 16, 16, -3, 3), line=False)
    add('harp', [(st + 0.5 * k, 1.5, lad[k % 6]) for st, d, sym in ch[:4] for lad in [ladder(sym, 'D3', 6)]
                 for k in range(int(round(d * 2)))], None, off=6, line=False)
    # bars 9-12: the minor turns back (Bb), full strings, the winds doubling, the peak Bb5
    t9, c9 = t + 32, ch[9:]
    dk = mel(t9, B_DARK)
    pdk = hairpin(t9, 16, -4, 6, 0.4)
    add('violins1', dk, off=6, offs=pdk, line=True)
    add('violins2', up(dk, -12), off=2, offs=pdk, line=True)
    add('flutes', up(dk, 12), off=0, offs=pdk, line=True)
    add('oboes', dk, off=-4, offs=pdk, line=True)
    add('violas', agitato(c9, ('Bb3', 'G4'), 2), 'staccato', off=-6, offs=accent(t9, 3, 1, -2), line=False)
    add('cellos', drive8(c9, 'D2'), 'staccato', off=-2, offs=accent(t9, 5, 2, -3), line=False)
    add('basses', bass(c9, 'D1'), off=-4, line=False)
    add('horns', pad(c9, ('D3', 'D4'), 2), off=-4, offs=pdk, line=False)
    add('trombones', pad(c9[:2], ('D3', 'Bb3'), 2), off=-8, offs=pdk, line=False)
    add('clarinets', pad(c9, ('D4', 'Bb4'), 2), off=-8, line=False)
    add('bassoons', bass(c9, 'D2'), off=-6, line=False)
    add('timpani', [(t9 + 12, 3.5, N('A2'))], 'roll', off=-6, line=False)

    # -------------------------------------------------------------------------------------- coda: tragic
    t, ch = T['coda'], CH['coda']
    cm = mel(t, [M1, M2])
    acco = both(accent(t, 7, 2, -3), hairpin(t, 8, -2, 3, 0.3))
    add('violins1', up(cm, 12), 'marcato', off=6, offs=acco, line=True)
    add('violins2', cm, 'marcato', off=2, offs=acco, line=True)
    add('flutes', up(cm, 24), off=0, offs=acco, line=True)
    add('oboes', up(cm, 12), off=-2, offs=acco, line=True)
    add('violas', agitato(ch[:2], ('A3', 'F4'), 2), 'staccato', off=-4, offs=accent(t, 4, 1, -2), line=False)
    add('cellos', drive8(ch[:2], 'D2'), 'staccato', off=0, offs=accent(t, 6, 2, -3), line=False)
    add('basses', beats(ch[:2], 'D1', 1.0, 0.7), 'staccato', off=0, line=False)
    add('horns', pad(ch[:2], ('D3', 'D4'), 2), off=-6, line=False)
    # bars 3-4: the low brass and basses take the motto, the violins storm above
    t3 = t + 8
    lm = mel(t3, [M1_BRASS, M2], -24)
    accl = both(accent(t3, 7, 2, -3), hairpin(t3, 8, -2, 3, 0.3))
    add('trombones', mel(t3, [M1_BRASS, M2], -12), 'marcato', off=2, offs=both(accl, accent(t3, 5, 0, -4)),
        line=True)
    add('tuba', lm, 'marcato', off=0, offs=accl, line=True)
    add('cellos', mel(t3, [M1, M2], -24), 'marcato', off=6, offs=accl, line=True)
    add('basses', mel(t3, [M1, M2], -36 + 12), 'marcato', off=4, offs=accl, line=True)
    add('bassoons', mel(t3, [M1, M2], -24), off=0, offs=accl, line=True)
    add('horns', mel(t3, [M1_BRASS, M2], -12), off=2, offs=accl, line=True)
    add('violins1', run16(ch[2:4], 'D5'), 'spiccato', off=-2, offs=accent(t3, 5, 1, -3), line=False)
    add('violins2', run16(ch[2:4], 'F4', [0, 1, 2, 3, 2, 1, 2, 1]), 'spiccato', off=-4, offs=accent(t3, 5, 1, -3),
        line=False)
    add('violas', agitato(ch[2:4], ('A3', 'F4'), 2), 'staccato', off=-4, offs=accent(t3, 4, 1, -2), line=False)
    add('timpani', [(t3, 0.5, N('D3'), 104), (t3 + 1, 1, N('A2'), 96), (t3 + 4, 1.5, N('A2'), 98)], 'hit',
        line=False)
    # bar 5: the head fragmented (Gm), strings vs winds; bar 6: the Neapolitan Eb, held ff
    t5 = t + 16
    add('violins1', frag(t5, 'G5:0.5 r:0.25 G5:0.25 D6:1') + frag(t5 + 2, 'Bb5:0.5 r:0.25 Bb5:0.25 G6:1'), 'marcato',
        off=6, offs=lambda n: 4 if (n[0] - t5) % 2 == 0 else 0, line=True)
    add('flutes', frag(t5 + 1, 'G5:0.5 r:0.25 G5:0.25 D6:0.5') + frag(t5 + 3, 'Bb5:0.5 r:0.25 Bb5:0.25 G6:0.5'),
        off=2, offs=lambda n: 3 if (n[0] - t5) % 2 == 1 else -1, line=False)
    add('violins2', agitato(ch[4:5], ('G4', 'D5'), 2), 'staccato', off=-4, line=False)
    add('violas', agitato(ch[4:5], ('Bb3', 'G4'), 2), 'staccato', off=-4, line=False)
    add('cellos', drive8(ch[4:5], 'G2', octave=False), 'staccato', off=0, line=False)
    add('basses', beats(ch[4:5], 'G1', 1.0, 0.7), 'staccato', off=0, line=False)
    t6 = t + 20
    for role, reg, nv, o in (('violins1', ('Eb5', 'Eb6'), 3, 4), ('violins2', ('G4', 'Eb5'), 2, 2),
                             ('violas', ('Bb3', 'G4'), 2, 0), ('flutes', ('Bb5', 'G6'), 2, 0),
                             ('oboes', ('Eb5', 'Bb5'), 2, -2), ('clarinets', ('G4', 'Eb5'), 2, -2),
                             ('horns', ('Eb3', 'Bb3'), 2, 2), ('trumpets', ('G4', 'Eb5'), 2, 2),
                             ('trombones', ('Bb2', 'G3'), 2, 0)):
        v = voicings([(t6, 4, 'Eb')], reg, nv)[0]
        add(role, [(t6, 3.5, p) for p in v], 'marcato', off=o, offs=lambda n: 0, line=False)
    add('cellos', [(t6, 3.5, N('Eb2'))], 'marcato', off=2, line=False)
    add('basses', [(t6, 3.5, N('Eb1'))], 'marcato', off=2, line=False)
    add('tuba', [(t6, 3.5, N('Eb1'))], 'marcato', off=-2, line=False)
    add('bassoons', [(t6, 3.5, N('Eb2')), (t6, 3.5, N('Bb2'))], off=0, line=False)
    add('timpani', [(t + 19, 1, N('D3'), 100)], 'hit', line=False)
    # bars 7-8: the cadential 6/4 in 16ths, A7 held
    t7, c7 = t + 24, ch[6:8]
    add('violins1', run16(c7, 'A4', [0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 3, 4, 5]), 'spiccato', off=0,
        offs=both(accent(t7, 5, 1, -3), cresc(t7, 8, -2, 4)), line=False)
    add('violins2', run16(c7, 'D4', [0, 1, 2, 3, 2, 1, 2, 3]), 'spiccato', off=-4, offs=accent(t7, 5, 1, -3),
        line=False)
    add('violas', agitato(c7, ('A3', 'F4'), 2), 'staccato', off=-4, offs=accent(t7, 4, 1, -2), line=False)
    add('cellos', drive8(c7, 'A2'), 'staccato', off=0, offs=accent(t7, 6, 2, -3), line=False)
    add('basses', [(t7, 8, N('A1'))], off=0, offs=lambda n: 0, line=False)
    add('horns', pad(c7, ('E3', 'D4'), 2), off=-2, offs=cresc(t7, 8, -3, 4), line=False)
    add('trumpets', [(t7, 2, N('A4')), (t7 + 2, 2, N('G4')), (t7 + 4, 4, N('A4')), (t7 + 4, 4, N('C#5'))], off=-2,
        offs=cresc(t7, 8, -3, 4), line=False)
    add('trombones', pad(c7, ('A2', 'E3'), 2), off=-4, offs=cresc(t7, 8, -3, 4), line=False)
    add('tuba', [(t7, 8, N('A1'))], off=-4, offs=lambda n: 0, line=False)
    add('flutes', [(t7, 2, N('F6')), (t7 + 2, 2, N('E6')), (t7 + 4, 4, N('E6'))], off=-2, offs=cresc(t7, 8, -3, 4),
        line=False)
    add('oboes', [(t7, 2, N('D5')), (t7 + 2, 2, N('C#5')), (t7 + 4, 4, N('G5'))], off=-2, offs=cresc(t7, 8, -3, 4),
        line=False)
    add('clarinets', pad(c7, ('E4', 'A4'), 2), off=-4, line=False)
    add('bassoons', [(t7, 8, N('A2'))], off=-4, offs=lambda n: 0, line=False)
    add('timpani', [(t7 + 4, 3.5, N('A2'))], 'roll', off=-2, line=False)
    # bars 9-10: three hammer-strokes of D minor, the last held under the fermata
    t9 = t + 32
    strokes = [(t9, 0.75), (t9 + 1, 0.75), (t9 + 2, 6.0)]
    stroke_offs = lambda n: {0: 4, 1: -5}.get(round(n[0] - t9), 8)
    for role, reg, nv, o in (('violins1', ('D5', 'D6'), 3, 4), ('violins2', ('F4', 'D5'), 2, 2),
                             ('violas', ('A3', 'F4'), 2, 0), ('flutes', ('D5', 'D6'), 2, 0),
                             ('oboes', ('F4', 'D5'), 2, -2), ('clarinets', ('A3', 'F4'), 2, -2),
                             ('horns', ('D3', 'D4'), 2, 2), ('trumpets', ('A4', 'D5'), 2, 2),
                             ('trombones', ('D3', 'A3'), 2, 0)):
        v = voicings([(t9, 4, 'Dm')], reg, nv)[0]
        add(role, [(a, d, p) for a, d in strokes for p in v], 'marcato', off=o, offs=stroke_offs, line=False)
    for role, p, o in (('cellos', 'D2', 2), ('basses', 'D1', 2), ('tuba', 'D1', -2), ('bassoons', 'D2', 0)):
        add(role, [(a, d, N(p)) for a, d in strokes], 'marcato' if role != 'bassoons' else 'sustain', off=o,
            offs=stroke_offs, line=False)
    add('timpani', [(t9, 0.75, N('D3'), 112), (t9 + 1, 0.75, N('D3'), 108), (t9 + 2, 1, N('D3'), 116)], 'hit',
        line=False)
    add('timpani', [(t9 + 3, 4.5, N('D3'))], 'roll', off=-4, line=False)

    sc.perform()
    return s
