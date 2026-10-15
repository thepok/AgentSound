"""The Long Road Home - an original lyrical-heroic film cue for full orchestra and choir 'oh'.
Build: python -m agentsound build songs/pro-orch-epic

A composed ("pro") reference for the endless orchestra genre: played by the SAME band setup as an endless piece
(agentsound.endless.orchestra.band), so only the writing differs. D major (the climax lifted to F major, bIII),
4/4, q = 80.

  intro    4   D pedal (basses, timpani roll pp), the strings' chord swells, a distant horn fragment, a harp arpeggio
  A        8   the THEME in the horns (a rising 1-2-3-5, the long B on vi, the peak D5, half cadence on A);
               strings sustained under it, the harp in quarters
  B        8   contrast in B minor: the oboe sings, the flute (clarinet an octave under) answers; pizzicato low
               strings, harp eighths; the horns rest
  A2       8   the theme in the violins (octaves), the horns' chromatic counter-line (B - Bb - A - G - F#), the viola
               ostinato starts; the ending turned: G - Gm6 (the minor iv) - D/A - A7 - D, closing on D5
  build    8   the ostinato spreads (violins II, then I), cellos / basses in 3+3+2, the horns sequence the theme's
               head up through Bm - G - Bb - C - Dm - Bb, trombones and winds enter, timpani, a cymbal swell, the
               harp's glissando on C7
  climax   8   F MAJOR, the only tutti: violins in octaves, trumpets + choir at pitch, horns an octave
               down, violas / cellos the counter-line, timpani and cymbals; allargando into the held F
  trans    2   the tutti dies away: Bbmaj7 - A7sus4, a single horn remembers the head
  Ar       8   the quiet return in D: the cellos sing the theme, the flute ends it
  coda     4   D - Gm/D (the minor plagal), the horn's last head, ritardando
  end      2   Dadd9 held under a fermata, the harp rolled

CREDITS: Sonatina Symphonic Orchestra 4.0, VSCO 2 CE, No Budget Orchestra 2 choir (see the build's credits).
"""
from agentsound import *
from agentsound.theory import chord as _chord, note as _note, voice_lead
from agentsound.bandlib import orchestra as orch
from agentsound.endless.orchestra import band as orchestra_band

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'The Long Road Home', 'artist': 'AgentSound', 'album': 'Orchestral References',
            'genre': 'Soundtrack', 'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#1d2a3a', '#d8a54a'], 'title': 'THE LONG ROAD HOME',
         'subtitle': 'AgentSound - Orchestral References', 'seed': 80}

KEY = 'D major'
TEMPO = 80
SEED = 80
ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
         'trumpets', 'trombones', 'tuba', 'harp', 'timpani', 'percussion', 'choir')

FORM = [('intro', 4), ('A', 8), ('B', 8), ('A2', 8), ('build', 8), ('climax', 8), ('trans', 2), ('Ar', 8),
        ('coda', 4), ('end', 2)]

# ------------------------------------------------------------------------------------------------ harmony
CHART = {
    'intro': 'D | G/D | Em7/D | A7sus4:2 A7:2',
    'A': 'D | Bm | G | Asus4:2 A:2 | D/F# | G:2 Em7:2 | Bm7:2 Gmaj7:2 | Asus4:2 A:2',
    'B': 'Bm | G | Em7 | F#sus4:2 F#:2 | G | D/F# | Em7 | A7sus4:2 A7:2',
    'A2': 'D | Bm | G | Asus4:2 A:2 | D/F# | G:2 Gm6:2 | D/A:2 A7:2 | D',
    'build': 'Bm | G | Bb | C | Dm | Bb | Gm7 | Csus4:2 C7:2',
    'climax': 'F | Dm | Bb | Csus4:2 C:2 | F/A | Bb:2 Bbm6:2 | F/C:2 C7:2 | F',
    'trans': 'Bbmaj7 | A7sus4:2 A7:2',
    'Ar': 'D | Bm | G | Asus4:2 A:2 | D/F# | G:2 Gm6:2 | D/A:2 A7:2 | D',
    'coda': 'D | Gm/D | D | Gm6/D:2 D:2',
    'end': 'Dadd9:8',
}

# ------------------------------------------------------------------------------------------------ the theme
# written at horn pitch in D; the pickup A3 sits on the beat before bar 1
THEME = ['D4:1.5 E4:0.5 F#4:1 A4:1', 'B4:3 A4:0.5 F#4:0.5', 'G4:1.5 A4:0.5 B4:1 G4:1', 'A4:2.5 r:0.5 A3:1',
         'D4:1.5 E4:0.5 F#4:1 A4:1', 'D5:3 B4:0.5 C#5:0.5', 'D5:1.5 C#5:0.5 B4:1.5 G4:0.5', 'A4:3.5 r:0.5']
# the closed version (A2, climax, return): the minor iv sighs Bb - A, the line climbs to the tonic on top
THEME_END = THEME[:5] + ['D5:2 Bb4:1.5 A4:0.5', 'A4:1 D5:1 E5:1.5 C#5:0.5', 'D5:4']
# A2: the horns' counter-line under the violins (the chromatic B - Bb - A - G - F# in bars 6-8)
COUNTER = ['A3:4', 'B3:2 D4:2', 'D4:4', 'E4:2 C#4:2', 'D4:4', 'B3:2 Bb3:2', 'A3:2 G3:2', 'F#3:4']
# B: the oboe's question, the flute's answer
OBOE_B = ['F#5:2 E5:1 D5:1', 'D5:1.5 C#5:0.5 B4:2', 'E5:1 G5:1 F#5:2', 'B4:2 A#4:1.5 r:0.5']
FLUTE_B = ['B4:1 D5:1 G5:2', 'F#5:1.5 E5:0.5 F#5:1 A5:1', 'G5:2 F#5:1 E5:1', 'E5:2 C#5:1 r:1']
# build: the head (1-2-3-5) sequenced up the chords, then held tones
HEAD = ['B3:1.5 C#4:0.5 D4:1 F#4:1', 'G3:1.5 A3:0.5 B3:1 D4:1', 'Bb3:1.5 C4:0.5 D4:1 F4:1',
        'C4:1.5 D4:0.5 E4:1 G4:1', 'D4:1.5 E4:0.5 F4:1 A4:1', 'F4:1.5 G4:0.5 Bb4:1 D5:1', 'D5:4', 'C5:2 Bb4:2']
INTRO_HORN = ['A3:1.5 D4:0.5 E4:2', 'D4:3 r:1', 'r:4', 'r:4']
TRANS_HORN = ['F4:1.5 G4:0.5 A4:2', 'E4:3 r:1']
CODA_HORN = ['D4:1.5 E4:0.5 F#4:1 A4:1', 'Bb4:3 r:1', 'A4:2 F#4:2', 'G4:2 F#4:2']

DYN = {
    'intro': [(0, 'pp'), (8, 'p'), (14, 'mp'), (16, 'p')],
    'A': [(0, 'p'), (20, 'mp'), (26, 'mp'), (32, 'p')],
    'B': [(0, 'p'), (14, 'mp'), (16, 'p'), (24, 'mp'), (32, 'p')],
    'A2': [(0, 'mp'), (20, 'mf'), (28, 'mp'), (32, 'mp')],
    'build': [(0, 'p'), (16, 'mp'), (28, 'mf'), (32, 'f')],
    'climax': [(0, 'f'), (20, 'ff'), (24, 'f'), (28, 'ff'), (32, 'f')],
    'trans': [(0, 'mp'), (8, 'pp')],
    'Ar': [(0, 'p'), (20, 'mp'), (32, 'p')],
    'coda': [(0, 'p'), (16, 'pp')],
    'end': [(0, 'pp'), (8, 'ppp')],
}


def N(x):
    return _note(x)


def mel(t0, bars, shift=0):
    """Bars of 'pitch:beats' tokens (r = rest) from t0 -> (start, dur, pitch) notes; every bar must fill 4 beats."""
    out, t = [], t0
    for k, bar in enumerate(bars):
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
    """Merge a pitch held over consecutive chords into one note."""
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
    """The chords voice-led in a register: (start, dur, pitch) notes, held pitches tied."""
    lo, hi = N(register[0]), N(register[1])
    vs = voice_lead([c[2] for c in ch], register=(lo, max(hi, lo + 11)), voices=voices)
    return tie([(t, d * legato, p) for (t, d, _), v in zip(ch, vs) for p in v])


def bass(ch, lo, legato=1.0, root=False):
    return tie([(t, d * legato, low(tones(s)[0] if root else tones(s)[3], lo)) for t, d, s in ch])


def ostinato(ch, lo, shift=0):
    """The string drive: eighths root - 5th - octave - 5th per chord (the 3rd on top in the bar's second half)."""
    out = []
    for t, d, s in ch:
        r, th, fi, _ = tones(s)
        rp = low(r, lo) + shift
        pat = [0, fi, 12, fi, th + 12 if d >= 4 else 12, fi, 12, fi]
        for k in range(int(round(d * 2))):
            out.append((t + 0.5 * k, 0.45, rp + pat[k % 8]))
    return out


def arpeggio(ch, lo, step=0.5, ring=1.5):
    """The harp: a broken chord up and back per chord."""
    out = []
    for t, d, s in ch:
        r, th, fi, _ = tones(s)
        rp = low(r, lo)
        pat = [0, fi, 12, 12 + th, 12 + fi, 24, 12 + fi, 12 + th]
        for k in range(int(round(d / step))):
            out.append((t + step * k, ring, rp + pat[k % 8]))
    return out


def build() -> Song:
    s = Song('The Long Road Home', tempo=TEMPO, key=KEY, seed=SEED, tail=7)
    S = {name: s.section(name, bars=bars) for name, bars in FORM}
    T = {name: S[name].start for name in S}
    CH = {name: chart(T[name], CHART[name]) for name in S}
    s.endless_timeline = [c for name, _ in FORM for c in CH[name]]

    b = orchestra_band(s, ROLES)
    keys = b.info['keys']
    sc = orch.Score(s, b, DYN, key=KEY, seed=SEED, style='film')
    add = sc.add

    # -------------------------------------------------------------------------------------- time
    s.ritardando((S['climax'].bar(6), S['climax'].bar(7)), to=0.88, a_tempo=True)     # allargando
    s.fermata(S['climax'].bar(7), hold=2.0, length=4)                                    # the held F
    s.ritardando((S['coda'].bar(2), S['end'].start), to=0.78, a_tempo=False)
    s.fermata(S['end'].start, hold=3.0)

    # -------------------------------------------------------------------------------------- intro
    t, ch = T['intro'], CH['intro']
    add('basses', [(t, 16, N('D2'))], off=-2, line=False)
    add('cellos', [(t, 8, N('D3')), (t + 8, 8, N('A2'))], off=-4, line=False)
    add('violas', pad(ch, ('A3', 'E4'), 2), off=-6, line=False)
    add('violins2', pad(ch, ('D4', 'B4'), 2), off=-6, line=False)
    add('violins1', [(t + 8, 4, N('B5')), (t + 12, 4, N('A5'))], off=-8, line=False)
    add('timpani', [(t, 7.5, N('D3'))], 'roll', off=-10, line=False)
    add('horns', mel(t, INTRO_HORN), off=-2, line=True)
    add('harp', arpeggio(ch[2:], 'D3', step=0.5, ring=2.0), None, off=-6, line=False)
    add('clarinets', pad(ch[2:], ('F#3', 'D4'), 2), off=-8, line=False)
    add('horns', [(t + 15, 1, N('A3'))], off=2, line=True)           # the theme's pickup

    # -------------------------------------------------------------------------------------- A: the horn theme
    t, ch = T['A'], CH['A']
    add('horns', mel(t, THEME), off=6, line=True)
    add('violins2', pad(ch, ('F#4', 'D5'), 2), off=-6, line=False)
    add('violas', pad(ch, ('A3', 'F#4'), 2), off=-6, line=False)
    add('cellos', bass(ch, 'D3')[:4] + pad(ch[4:], ('D3', 'C#4'), 1), off=-4, line=False)
    add('basses', bass(ch, 'D2')[4:], off=-6, line=False)            # the basses join at the second phrase
    add('harp', arpeggio(ch, 'D3', step=1.0, ring=2.0), None, off=-8, line=False)
    add('bassoons', bass(ch, 'D2')[:4], off=-8, line=False)
    add('flutes', [(t + 20, 4, N('B5')), (t + 24, 4, N('A5')), (t + 28, 4, N('E5'))], off=-10, line=False)
    add('timpani', [(t, 1, N('D3')), (t + 16, 1, N('D3'))], 'hit', off=-12, line=False)

    # -------------------------------------------------------------------------------------- B: woodwinds in B minor
    t, ch = T['B'], CH['B']
    add('oboes', mel(t, OBOE_B), off=6, line=True)
    add('flutes', mel(t + 16, FLUTE_B), off=6, line=True)
    add('clarinets', mel(t + 16, FLUTE_B, -12), off=0, line=True)
    add('clarinets', pad(ch[:4], ('D4', 'A4'), 2), off=-8, line=False)
    add('violas', pad(ch, ('F#3', 'D4'), 2), off=-8, line=False)
    add('violins2', pad(ch, ('A4', 'E5'), 1), off=-10, line=False)
    piz = [(tt, 0.6, p) for (st, d, p) in bass(ch, 'B1') for tt in (st, st + 2) if tt < st + d - 1e-6]
    add('cellos', [(a, d, p + 12) for a, d, p in piz], 'pizzicato', off=-2, line=False)
    add('basses', piz, 'pizzicato', off=-4, line=False)
    add('harp', arpeggio(ch, 'B2', step=0.5, ring=1.5), None, off=-4, line=False)
    add('bassoons', bass(ch[4:], 'E2'), off=-8, line=False)
    add('violins1', [(t + 28, 4, N('G4'))], off=-6, line=False)       # into A2: the violins take the stage
    add('violins1', [(t + 31, 1, N('A4'))], off=4, line=True)
    add('violins2', [(t + 31, 1, N('A3'))], off=2, line=True)

    # -------------------------------------------------------------------------------------- A2: violins + horn counter
    t, ch = T['A2'], CH['A2']
    add('violins1', mel(t, THEME_END, 12), off=6, line=True)
    add('violins2', mel(t, THEME_END), off=2, line=True)
    add('horns', mel(t, COUNTER), off=2, line=True)
    add('violas', ostinato(ch, 'D3'), 'spiccato', off=-6, accent=True, line=False)
    add('cellos', bass(ch, 'D2'), off=-2, line=False)
    add('basses', bass(ch, 'D1'), off=-4, line=False)
    add('clarinets', pad(ch, ('D4', 'A4'), 2), off=-8, line=False)
    add('bassoons', pad(ch, ('D3', 'A3'), 1), off=-8, line=False)
    add('flutes', [(t + 20, 2, N('D6')), (t + 22, 2, N('D6')), (t + 24, 4, N('F#5')), (t + 28, 4, N('A5'))], off=-8,
        line=False)
    add('harp', arpeggio(ch[-3:], 'D3', step=0.5, ring=1.5), None, off=-8, line=False)
    add('timpani', [(t, 1, N('D3'), 70), (t + 16, 1, N('D3'), 62), (t + 28, 1, N('A2'), 74), (t + 30, 0.5, N('A2'), 56),
                    (t + 31, 1, N('D3'), 82)], 'hit', line=False)

    # -------------------------------------------------------------------------------------- build
    t, ch = T['build'], CH['build']
    add('violas', ostinato(ch, 'D3'), 'spiccato', off=-4, line=False)
    add('violins2', ostinato(ch, 'D3', 12), 'spiccato', off=-4, line=False)
    add('violins1', pad(ch[4:], ('D5', 'D6'), 2), 'tremolo', off=-4, line=False)
    drive = []
    for st, d, sym in ch:
        r = low(tones(sym)[0], 'G1')
        for a, dd in ((0, 1.4), (1.5, 1.4), (3, 0.9)):
            if a < d:
                drive.append((st + a, dd, r))
    acc = lambda n: {0.0: 8, 1.5: 0, 3.0: -8}.get(round((n[0] - t) % 4, 2), 0)
    add('cellos', [(a, d, p + 12) for a, d, p in drive], 'marcato', off=-2, offs=acc, line=False)
    add('basses', drive, 'marcato', off=-4, offs=acc, line=False)
    add('bassoons', [(a, d, p + 12) for a, d, p in drive[9:]], 'staccato', off=-6, offs=acc, line=False)
    add('horns', mel(t, HEAD), off=4, line=True)
    add('horns', pad(ch[6:], ('G3', 'E4'), 2), off=-2, line=False)
    add('trombones', pad(ch[2:], ('F2', 'D4'), 2), off=-6, line=False)
    add('tuba', bass(ch[4:], 'F1'), off=-6, line=False)
    add('trumpets', [(t + 24, 4, N('D5')), (t + 28, 2, N('C5')), (t + 30, 2, N('E5'))], off=-2, line=False)
    wp = pad(ch[4:], ('F4', 'F5'), 3)
    add('flutes', [(a, d, p + 12) for a, d, p in wp if p >= N('C5')], off=-6, line=False)
    add('oboes', [n for n in wp if n[2] < N('C5')], off=-6, line=False)
    add('clarinets', pad(ch[2:], ('D4', 'A4'), 2), off=-6, line=False)
    add('timpani', [(t + 16 + 4 * k + a, 1, low(tones(ch[4 + k][2])[0], 'G2'), 58 + 12 * k + (10 if a == 0 else -8))
                    for k in range(3) for a in (0, 2)], 'hit', line=False)
    add('timpani', [(t + 28, 4, N('C3'))], 'roll', off=0, line=False)
    add('percussion', [(t + 26, 6, keys['cymbal_roll_long'])], None, off=-4, line=False)
    gl = [N(x) for x in 'C4 D4 E4 F4 G4 A4 Bb4 C5 D5 E5 F5 G5 A5 Bb5 C6'.split()]
    add('harp', [(t + 30 + 2 * k / len(gl), 1.2, p) for k, p in enumerate(gl)], None, off=-2, line=False)

    # -------------------------------------------------------------------------------------- climax: the only tutti (F)
    t, ch = T['climax'], CH['climax']
    theme = mel(t, THEME_END, 3)
    pick = [(t - 1, 1, N('C4'))]
    add('violins1', [(a, d, p + 12) for a, d, p in pick + theme], off=6, line=True)
    add('violins2', pick + theme, off=4, line=True)
    add('trumpets', pick + theme, off=4, line=True)
    add('choir', theme, None, off=-10, line=True)
    add('choir', pad(ch, ('A3', 'C5'), 2), None, off=-18, line=False)
    add('horns', [(a, d, p - 12) for a, d, p in pick + theme], off=4, line=True)
    add('flutes', [(a, d, p + 12) for a, d, p in theme], off=2, line=True)
    add('oboes', theme, off=0, line=True)
    counter = mel(t, COUNTER, 3)
    add('violas', counter, off=2, line=True)
    add('cellos', [(a, d, p - 12) for a, d, p in counter], off=2, line=True)
    add('basses', bass(ch, 'E1'), off=0, line=False)
    add('tuba', bass(ch, 'E1'), off=-2, line=False)
    add('trombones', pad(ch, ('F2', 'D4'), 3), off=-4, line=False)
    add('clarinets', pad(ch, ('C4', 'A4'), 2), off=-6, line=False)
    add('bassoons', pad(ch, ('F2', 'C3'), 1), off=-6, line=False)
    timp = []
    for st, d, sym in ch[:-1]:
        p = low(tones(sym)[0], 'F2') if tones(sym)[0] in (5, 0) else low(tones(sym)[3], 'F2')
        timp.append((st, 1, p if p <= N('A3') else p - 12, 112 if (st - t) % 16 == 0 else (96 if (st - t) % 4 == 0 else 76)))
    add('timpani', timp, 'hit', off=0, line=False)
    add('timpani', [(t + 28, 6, N('F2'))], 'roll', off=0, line=False)
    add('percussion', [(t, 4, keys['crash']), (t, 4, keys['bass_drum']), (t + 16, 4, keys['sus_cymbal']),
                       (t + 16, 2, keys['bass_drum']), (t + 28, 4, keys['crash']), (t + 28, 4, keys['bass_drum'])],
        None, off=0, line=False)
    hv = voice_lead([c[2] for c in ch], register=(N('F3'), N('F5')), voices=4)
    add('harp', [(st + 0.06 * k, 3, p) for (st, d, sym), v in zip(ch, hv) for k, p in enumerate(sorted(v))],
        None, off=-4, line=False)

    # -------------------------------------------------------------------------------------- trans
    t, ch = T['trans'], CH['trans']
    add('violins1', pad(ch, ('F4', 'D5'), 2), off=-4, line=False)
    add('violas', pad(ch, ('A3', 'F4'), 2), off=-4, line=False)
    add('cellos', bass(ch, 'A2'), off=-4, line=False)
    add('basses', bass(ch, 'A1'), off=-6, line=False)
    add('horns', mel(t, TRANS_HORN), off=2, line=True)
    add('timpani', [(t + 4, 3.5, N('A2'))], 'roll', off=-10, line=False)
    add('cellos', [(t + 7, 1, N('A3'))], off=2, line=True)             # the cellos' pickup

    # -------------------------------------------------------------------------------------- Ar: the quiet return
    t, ch = T['Ar'], CH['Ar']
    th = mel(t, THEME_END)
    add('cellos', [n for n in th if n[0] < t + 16], off=6, line=True)
    add('flutes', [(a, d, p + 12) for a, d, p in th if a >= t + 15.9], off=4, line=True)
    add('clarinets', [n for n in th if n[0] >= t + 15.9], off=-2, line=True)
    add('violins2', pad(ch, ('F#4', 'D5'), 2), off=-8, line=False)
    add('violas', pad(ch, ('A3', 'F#4'), 2), off=-8, line=False)
    add('basses', bass(ch, 'D2'), off=-8, line=False)
    add('cellos', bass(ch[6:], 'D2'), off=-6, line=False)
    add('harp', arpeggio(ch, 'D3', step=1.0, ring=2.0), None, off=-6, line=False)
    add('horns', [(t + 16, 8, N('A3')), (t + 24, 4, N('G3')), (t + 28, 4, N('F#3'))], off=-8, line=False)

    # -------------------------------------------------------------------------------------- coda + end
    t, ch = T['coda'], CH['coda']
    add('horns', mel(t, CODA_HORN), off=2, line=True)
    add('violins2', pad(ch, ('A4', 'D5'), 2), off=-8, line=False)
    add('violas', pad(ch, ('D4', 'A4'), 2), off=-8, line=False)
    add('cellos', [(t, 16, N('D3'))], off=-6, line=False)
    add('basses', [(t, 16, N('D2'))], off=-8, line=False)
    add('clarinets', [(t + 4, 4, N('Bb3')), (t + 8, 4, N('A3')), (t + 12, 2, N('Bb3')), (t + 14, 2, N('A3'))], off=-6,
        line=False)
    add('harp', arpeggio(ch, 'D3', step=1.0, ring=2.0), None, off=-8, line=False)

    t = T['end']
    for role, ps, o in (('basses', 'D2', -6), ('cellos', 'D3 A3', -6), ('violas', 'F#4 A4', -6),
                        ('violins2', 'D5 E5', -6), ('violins1', 'A5', -8), ('horns', 'D4 A3', -10),
                        ('flutes', 'E6', -12), ('clarinets', 'F#4', -10)):
        add(role, [(t, 8, N(p)) for p in ps.split()], off=o, line=False)
    add('harp', [(t + 0.12 * k, 8, N(p)) for k, p in enumerate('D2 A2 D3 F#3 A3 E4 F#4 A4 D5'.split())], None, off=-4,
        line=False)
    add('timpani', [(t, 6, N('D3'))], 'roll', off=-14, line=False)

    sc.perform()
    return s
