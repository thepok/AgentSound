"""Scherzo in D minor - an original symphonic scherzo (Allegro vivace, one in a bar) for full orchestra.
Build: python -m agentsound build songs/pro-orch-symphonic-scherzo

A composed ("pro") reference for the endless symphonic orchestra: played by the SAME band setup as an endless piece
(agentsound.endless.orchestra.band), so only the writing differs. D minor, 3/4, q = 160 (the trio poco meno mosso,
q = 144, in B-flat major, the submediant).

THE THEME (violins I, p, detached quarters): an upbeat of two repeated A's, the leap to the long D, a turn down, the
fifth leap to the high A (sf); then a weak-beat sforzando (G on beat 2), the falling line to the half cadence on A.
The answer climbs to the peak B-flat, a hemiola (G - F - E in half notes across two bars) and closes in F (later in D).

  intro     4   tutti strokes: D (ff), silence, A (f); the timpani take the pulse
  A1       16   the THEME in the violins I, p, over pizzicato basses and the violas' / violins II's off-beat
                chords; 8 + 8, half cadence on A, the answer closes in F major (the hemiola in bars 13-14)
  A1b      16   the theme f in the woodwinds (flutes + oboes in octaves, clarinets), the strings in running eighths,
                horn calls on the long notes, brass on the cadence; the cadence to F hammered
  dev      24   development: the head cell passed between strings and woodwinds in a rising sequence
                (Gm - F - Bb - Gm - E - A), then the dominant: a hemiola cascade in half notes over A, the quarters
                climbing to the A stroke - and a general pause
  A3       16   the theme ff tutti, the downbeat now struck (D - A A), trumpets and timpani, the answer closes in D
  trans     4   the horn takes the upbeat cell as a call in B-flat (ritardando into the trio)
  trio1    16   TRIO (B-flat, q = 144): the horns sing a lilting landler tune over sustained strings, pizzicato
                basses, the harp's oom-pah-pah; the flute echoes the phrase ends
  trio2    16   the clarinet and flute (in thirds) turn to G minor; then the horns' answer returns in B-flat with
                the violins' counter-line
  retrans   8   the head cell creeps up from the bassoons through the clarinets to the strings over the timpani's
                A, crescendo and accelerando back to tempo
  R1        8   the SCHERZO RETURNS CHANGED: the theme low in cellos + bassoons, the woodwinds' staccato chords and
                the violins' pizzicato above
  R2        8   the answer in canon (violins I lead, flutes + oboes one bar behind), redirected to the dominant
  R3       16   ff tutti: the theme in violins + flutes, the cellos and basses in canon one bar behind, trumpet
                fanfares on the downbeats, the cadence in D
  coda     16   stretto of the head (entries every bar, bottom to top), the hemiola once more, a scale rushing up,
                the last strokes D - A - D D

CREDITS: Sonatina Symphonic Orchestra 4.0, VSCO 2 CE (see the build's credits).
"""
from agentsound import *
from agentsound.theory import chord as _chord, note as _note, voice_lead
from agentsound.bandlib import orchestra as orch
from agentsound.endless.orchestra import band as orchestra_band

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'Scherzo in D minor', 'artist': 'AgentSound', 'album': 'Orchestral References',
            'genre': 'Classical', 'year': 2026, 'composer': 'AgentSound'}
COVER = {'style': 'classical', 'palette': ['#2a1a1f', '#e0b04a'], 'title': 'SCHERZO',
         'subtitle': 'AgentSound - Orchestral References', 'seed': 160}

KEY = 'D minor'
TEMPO = 160
TRIO_TEMPO = 144
SEED = 160
BPB = 3
ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
         'trumpets', 'trombones', 'tuba', 'harp', 'timpani', 'percussion')

FORM = [('intro', 4), ('A1', 16), ('A1b', 16), ('dev', 24), ('A3', 16), ('trans', 4), ('trio1', 16),
        ('trio2', 16), ('retrans', 8), ('R1', 8), ('R2', 8), ('R3', 16), ('coda', 16)]

# ------------------------------------------------------------------------------------------------ harmony
_A = 'Dm | Dm | Dm | Dm | Gm | A7 | Gm | A'
CHART = {
    'intro': 'Dm | Dm | A | A',
    'A1': _A + ' | Dm | Dm | F | Bb | Gm | C7 | F | F',
    'A1b': _A + ' | Dm | Dm | F | Bb | Gm | C7 | F | F',
    'dev': 'Gm | Gm | Gm | D7 | F | F | F | C7 | Bb | Bb | Gm | Gm | E7 | E7 | A | A | '
           'A7 | Dm/A | A7 | A7 | A7 | A7 | A | A',
    'A3': _A + ' | Dm | Dm | F | Bb | Gm | A7 | Dm | Dm',
    'trans': 'Bb | Bb | Bb | F7',
    'trio1': 'Bb | Bb | Gm | F | Cm | Cm | F7 | Bb | Bb | Bb | F | Bb/D | Cm7 | Bb/F | F7 | Bb',
    'trio2': 'Gm | Gm | D | D7 | Gm | Cm | Gm | D:2 F7:1 | Bb | Bb | F | Bb/D | Cm7 | Bb/F | F7 | Bb',
    'retrans': 'Gm | Gm | Gm | Gm | A | A | A7 | A7',
    'R1': _A,
    'R2': 'Dm | Dm | F | Bb | Gm6 | Dm | A7 | A7',
    'R3': _A + ' | Dm | Dm | F | Bb | Gm | A7 | Dm | Dm',
    'coda': 'Dm | Dm | Dm | Dm | Dm | Bb | Gm | A7 | Dm | A7 | Gm | A7 | Dm | A7 | Dm | Dm',
}

# ------------------------------------------------------------------------------------------------ the material
# 'pitch:beats' tokens, bars split by '|', every bar fills 3 beats; r = rest, '-' = the previous note held on (a tie
# over the bar line), a trailing '>' = an accent / sforzando (weak-beat sf are the scherzo's character)
ANT = ('r:1 A4:1 A4:1 | D5:2> E5:1 | F5:1 E5:1 D5:1 | A5:2> r:1 | r:1 G5:1> F5:1 | E5:1 D5:1 C#5:1 | '
       'D5:1 Bb4:1 G4:1 | A4:2 r:1')
CONS_F = ('r:1 A4:1 A4:1 | D5:2> E5:1 | F5:1 G5:1 A5:1 | Bb5:2> A5:1 | G5:2> F5:1 | -:1 E5:2> | '
          'F5:1 C5:1 A4:1 | F4:1> r:2')
CONS_D = ('r:1 A4:1 A4:1 | D5:2> E5:1 | F5:1 G5:1 A5:1 | Bb5:2> A5:1 | G5:2> F5:1 | -:1 E5:2> | '
          'D5:1 A4:1 F4:1 | D4:1> r:2')
# the struck version (A3, R3): the downbeat of each phrase hammered instead of the rest
ANT_S = 'D5:1> A4:1 A4:1' + ANT[len('r:1 A4:1 A4:1'):]
CONS_DS = 'D5:1> A4:1 A4:1' + CONS_D[len('r:1 A4:1 A4:1'):]
# R2: the answer turned to the dominant (into the tutti)
CONS_V = ('r:1 A4:1 A4:1 | D5:2> E5:1 | F5:1 G5:1 A5:1 | Bb5:2> A5:1 | G5:1 F5:1 E5:1 | F5:1 E5:1 D5:1 | '
          'C#5:1 D5:1 E5:1 | A5:1> r:2')

# development: the head cell up the sequence, strings and winds in turn
DEV_STR1 = 'r:1 D5:1 D5:1 | G5:2> A5:1 | Bb5:1 A5:1 G5:1 | D6:2> r:1'
DEV_WW1 = 'r:1 C5:1 C5:1 | F5:2> G5:1 | A5:1 G5:1 F5:1 | C6:2> r:1'
DEV_STR2 = 'r:1 F4:1 F4:1 | Bb4:2> C5:1'
DEV_WW2 = 'r:1 D5:1 D5:1 | G5:2> A5:1'
DEV_STR3 = 'r:1 E5:1 E5:1 | G#5:2> B5:1'
DEV_ALL4 = 'r:1 E5:1 E5:1 | A5:2> C#6:1'
DEV_CASCADE = 'A5:2> G5:1> | -:1 F5:2> | E5:2> D5:1> | -:1 C#5:2> | C#5:1 D5:1 E5:1 | F5:1 G5:1 A5:1 | A5:1> r:2 | r:3'

# the trio: the horns' landler tune (concert pitch)
HORN_T = ('F3:1 Bb3:1 D4:1 | F4:2> Eb4:1 | D4:1 C4:1 Bb3:1 | C4:3 | C4:1 Eb4:1 G4:1 | G4:2> F4:1 | '
          'Eb4:1 D4:1 C4:1 | D4:2 r:1')
HORN_T2 = ('F3:1 Bb3:1 D4:1 | F4:2> G4:1 | A4:1 Bb4:1 G4:1 | F4:3> | Eb4:1 G4:1 C4:1 | D4:2 F4:1 | '
           'Eb4:1 D4:1 C4:1 | Bb3:3')
CLAR_T = 'D5:2> C5:1 | Bb4:1 A4:1 G4:1 | A4:2 Bb4:1 | C5:3 | D5:1 Eb5:1 D5:1 | G5:2> F#5:1 | G5:1 D5:1 Bb4:1 | A4:3'
FLUTE_ECHO1 = 'r:3 | r:3 | r:3 | r:1 F5:1 A5:1 | r:3 | r:3 | r:3 | r:1 F5:1 D5:1'
VLN_COUNTER = 'D5:3 | -:2 C5:1 | C5:3 | -:2 D5:1 | Eb5:3 | D5:3 | C5:2 A4:1 | Bb4:3'

# the transition horn call and the retransition's creeping head
TRANS_HORN = 'r:1 F3:1 F3:1 | Bb3:3 | r:1 D4:1 D4:1 | F4:3>'
RT_BSN = 'r:1 D3:1 D3:1 | G3:2> A3:1'
RT_CL = 'r:1 D4:1 D4:1 | G4:2> A4:1'
RT_VLA = 'r:1 E4:1 E4:1 | A4:2> C#5:1'
RT_VLN = 'r:1 E5:1 E5:1 | A5:2 r:1'

# the coda
STRETTO = 'r:1 {o}:1 {o}:1 | {p}:2> {e}:1'
CODA_HEMI = 'F5:1 G5:1 A5:1 | Bb5:2> A5:1 | G5:2> F5:1 | -:1 E5:2>'
CODA_RUN = 'D5:0.5 E5:0.5 F5:0.5 G5:0.5 A5:0.5 Bb5:0.5 | C#6:2> A5:1 | D6:2> Bb5:1 | -:1 A5:2>'
CODA_END = 'D6:1> r:2 | A5:1> r:2 | D6:1> r:1 D6:1> | D6:1> r:2'

DYN = {
    'intro': [(0, 'ff'), (2, 'mf', 'step'), (6, 'f', 'step'), (8, 'p', 'step'), (12, 'p')],
    'A1': [(0, 'p'), (9, 'mp'), (12, 'mp'), (21, 'p'), (24, 'p'), (33, 'mf'), (39, 'mf'), (43, 'f'), (48, 'f')],
    'A1b': [(0, 'mf', 'step'), (9, 'f'), (12, 'f'), (15, 'mf'), (24, 'mf'), (36, 'f'), (45, 'ff'), (48, 'ff')],
    'dev': [(0, 'p', 'subito'), (12, 'p'), (24, 'mp'), (36, 'mf'), (48, 'f'), (60, 'f'), (66, 'ff'), (72, 'ff')],
    'A3': [(0, 'ff', 'step'), (6, 'f'), (12, 'mf'), (24, 'f'), (36, 'ff'), (48, 'f')],
    'trans': [(0, 'p', 'step'), (6, 'mp'), (12, 'p')],
    'trio1': [(0, 'p'), (9, 'mp'), (12, 'p'), (21, 'mp'), (24, 'p'), (33, 'mf'), (36, 'mf'), (42, 'mp'), (48, 'p')],
    'trio2': [(0, 'mp'), (15, 'mf'), (21, 'mp'), (24, 'p'), (36, 'mf'), (45, 'p'), (48, 'pp')],
    'retrans': [(0, 'pp'), (12, 'p'), (18, 'mf'), (22, 'f'), (24, 'p')],
    'R1': [(0, 'p', 'step'), (12, 'mp'), (21, 'p'), (24, 'mp')],
    'R2': [(0, 'mp'), (12, 'mf'), (21, 'f'), (24, 'f')],
    'R3': [(0, 'ff', 'step'), (6, 'f'), (12, 'mf'), (24, 'f'), (36, 'ff'), (48, 'ff')],
    'coda': [(0, 'mp', 'step'), (12, 'f'), (24, 'f'), (33, 'ff'), (48, 'ff')],
}


def N(x):
    return _note(x)


def parse(t0, text, shift=0):
    """'pitch:beats' bars -> ([(start, dur, pitch)], {accented starts}); every bar fills BPB beats."""
    out, acc, t = [], set(), t0
    for bar in text.split('|'):
        tot = 0.0
        for tok in bar.split():
            p, d = tok.split(':')
            a = d.endswith('>')
            d = float(d.rstrip('>'))
            if p == '-':
                s0, d0, p0 = out[-1]
                out[-1] = (s0, d0 + d, p0)
            elif p != 'r':
                out.append((t + tot, d, N(p) + shift))
                if a:
                    acc.add(round(t + tot, 3))
            tot += d
        assert abs(tot - BPB) < 1e-9, (bar, tot)
        t += BPB
    return out, acc


def mel(t0, text, shift=0):
    return parse(t0, text, shift)[0]


def chart(t0, text):
    out, t = [], t0
    for bar in text.split('|'):
        toks = bar.split()
        durs = [float(x.split(':')[1]) if ':' in x else None for x in toks]
        rest = (BPB - sum(d for d in durs if d)) / max(1, durs.count(None)) if None in durs else 0
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


def pad(ch, register, voices, legato=1.0):
    lo, hi = N(register[0]), N(register[1])
    vs = voice_lead([c[2] for c in ch], register=(lo, max(hi, lo + 11)), voices=voices)
    return tie([(t, d * legato, p) for (t, d, _), v in zip(ch, vs) for p in v])


def bass(ch, lo, legato=1.0, root=False):
    return tie([(t, d * legato, low(tones(s)[0] if root else tones(s)[3], lo)) for t, d, s in ch])


def downbeats(ch, lo, length=0.8, root=False):
    """The bass on every bar's first beat (pizzicato / detached)."""
    out = []
    for t, d, s in ch:
        p = low(tones(s)[0] if root else tones(s)[3], lo)
        for k in range(int(round(d / BPB)) or 1):
            out.append((t + BPB * k, length, p))
    return out


def offbeats(ch, register, voices=2, length=0.5):
    """The scherzo's accompaniment: the chord on beats 2 and 3 of every bar."""
    lo, hi = N(register[0]), N(register[1])
    vs = voice_lead([c[2] for c in ch], register=(lo, max(hi, lo + 11)), voices=voices)
    out = []
    for (t, d, _), v in zip(ch, vs):
        for k in range(int(round(d / BPB)) or 1):
            for b in (1, 2):
                if BPB * k + b < d - 1e-6:
                    out += [(t + BPB * k + b, length, p) for p in v]
    return out


def run8(ch, lo, shift=0):
    """Running eighths: the chord broken up and down, six per bar."""
    out = []
    for t, d, s in ch:
        r, th, fi, _ = tones(s)
        rp = low(r, lo) + shift
        pat = [0, th, fi, 12, fi, th]
        for k in range(int(round(d * 2))):
            out.append((t + 0.5 * k, 0.42, rp + pat[k % 6]))
    return out


def hemiola(ch, register, voices, t0, bars):
    """Half-note strokes across the bar line (three per two bars) on the chords sounding there."""
    lo, hi = N(register[0]), N(register[1])
    out = []
    for k in range(int(bars * BPB / 2)):
        t = t0 + 2 * k
        sym = next(s for a, d, s in ch if a - 1e-6 <= t < a + d - 1e-6)
        v = voice_lead([sym], register=(lo, max(hi, lo + 11)), voices=voices)[0]
        out += [(t, 1.6, p) for p in v]
    return out


def shaper(acc, notes, accent=9, slope=0.45, bar=3):
    """Velocity offsets for a line: an accent on the marked notes, the high notes a little louder, the bar's weak
    beats a touch lighter (the one-in-a-bar lilt)."""
    ps = [n[2] for n in notes] or [60]
    mid = sum(ps) / len(ps)

    def f(n):
        o = max(-6.0, min(6.0, slope * (n[2] - mid)))
        if round(n[0], 3) in acc:
            o += accent
        ph = round(n[0] % BPB, 3)
        if bar and ph not in (0.0,):
            o -= bar if ph >= 1 else 0
        return o
    return f


def build() -> Song:
    s = Song('Scherzo in D minor', tempo=TEMPO, key=KEY, seed=SEED, tail=6, meter=(3, 4))
    S = {name: s.section(name, bars=bars) for name, bars in FORM}
    T = {name: S[name].start for name in S}
    CH = {name: chart(T[name], CHART[name]) for name in S}
    s.endless_timeline = [c for name, _ in FORM for c in CH[name]]

    b = orchestra_band(s, ROLES)
    keys = b.info['keys']
    s.master.fx['limiter'].set(gain=1.6)            # the classical profile wants the tutti under -16 LUFS
    sc = orch.Score(s, b, DYN, key=KEY, seed=SEED, style='romantic')
    add = sc.add

    def play(role, t0, text, shift=0, off=0.0, short=0.62, accent=9, sf=False, art='sustain'):
        """A melodic line: detached quarters (short= x their length), held notes full, accents and contour."""
        ns, acc = parse(t0, text, shift)
        add(role, ns, art, off=off, offs=shaper(acc, ns, accent), line=True,
            dur=lambda n: short if n[1] <= 1.01 else 0.94, sf=sorted(acc) if sf else ())
        return ns

    def strokes(roles, times, pitches, length=0.7, off=0.0):
        """Tutti strokes (sforzando) on chords: {role: [pitch names]} at the given beats."""
        for role in roles:
            add(role, [(t, length, N(p)) for t in times for p in pitches[role]], 'sustain', off=off, sf=times,
                line=False)

    # -------------------------------------------------------------------------------------- time
    s.ritardando((S['trans'].bar(1), S['trio1'].start), to=TRIO_TEMPO / TEMPO, a_tempo=False)
    s.accelerando((S['retrans'].bar(2), S['R1'].start), to=TEMPO / TRIO_TEMPO, a_tempo=False)
    s.fermata(S['dev'].bar(23), hold=1.0, length=3)                                  # the general pause breathes
    s.ritardando((S['coda'].bar(14), S['coda'].bar(15) + 1), to=0.9, a_tempo=False)

    # -------------------------------------------------------------------------------------- intro: the strokes
    t = T['intro']
    D_OCT = {'violins1': ['D5', 'D6'], 'violins2': ['D4', 'D5'], 'violas': ['D3', 'D4'], 'cellos': ['D3'],
             'basses': ['D2'], 'flutes': ['D5', 'D6'], 'oboes': ['D5'], 'clarinets': ['D4'], 'bassoons': ['D2', 'D3'],
             'horns': ['D3', 'D4'], 'trumpets': ['D4', 'D5'], 'trombones': ['D3', 'A3'], 'tuba': ['D2']}
    A_OCT = dict({'violins1': ['A4', 'A5'], 'violins2': ['A4'], 'violas': ['A3'], 'cellos': ['A3'],
                  'basses': ['A1'], 'flutes': ['A5'], 'oboes': ['A4'], 'clarinets': ['A4'], 'bassoons': ['A2'],
                  'horns': ['A3'], 'trumpets': ['A4'], 'trombones': ['A2', 'E3'], 'tuba': ['A1']})
    strokes(D_OCT, [t], D_OCT, length=0.9)
    strokes(A_OCT, [t + 6], A_OCT, length=1.2, off=-4)
    add('timpani', [(t, 1, N('D3'), 118), (t + 6, 1, N('A2'), 100), (t + 9, 1, N('A2'), 46), (t + 10, 1, N('A2'), 38),
                    (t + 11, 1, N('A2'), 42)], 'hit', line=False)
    add('percussion', [(t, 3, keys['crash']), (t, 2, keys['bass_drum'])], None, off=0, line=False)

    # -------------------------------------------------------------------------------------- A1: the theme in violins
    t, ch = T['A1'], CH['A1']
    play('violins1', t, ANT + ' | ' + CONS_F, off=6)
    play('violins2', t + 24, 'r:1 r:1 r:1 | ' + ' | '.join(CONS_F.split(' | ')[1:]), shift=-12, off=-2)
    add('violins2', offbeats(ch[:8], ('A3', 'F4'), 2, 0.4), off=-10, line=False)
    add('violas', offbeats(ch, ('F3', 'D4'), 2, 0.4), off=-8, line=False)
    add('cellos', downbeats(ch, 'D3', 0.8), 'pizzicato', off=-2, line=False)
    add('basses', downbeats(ch, 'D2', 0.8), 'pizzicato', off=-4, line=False)
    add('bassoons', bass(ch[8:], 'D2', 0.9), off=-12, line=False)
    add('clarinets', pad(ch[8:12], ('D4', 'A4'), 2), off=-12, line=False)
    add('flutes', mel(t + 21, 'F6:1 E6:1 C#6:1'), off=-10, line=False)                  # a flicker on the cadence
    # the cadence to F hammered: the hemiola in the strings and winds, F strokes
    add('oboes', [(n[0], 1.6, n[2]) for n in hemiola(ch, ('C5', 'G5'), 1, t + 36, 2)], off=-6, line=False)
    add('horns', [(t + 36, 2, N('F3')), (t + 38, 2, N('F3')), (t + 40, 1.6, N('E3')), (t + 42, 1, N('F3'))], off=-6,
        line=False)
    add('timpani', [(t + 36, 1, N('F2'), 60), (t + 38, 1, N('F2'), 66), (t + 40, 1, N('C3'), 72),
                    (t + 45, 1, N('F2'), 92)], 'hit', line=False)
    add('trumpets', [(t + 45, 0.7, N('F4')), (t + 45, 0.7, N('C5'))], off=-2, sf=[t + 45], line=False)
    add('trombones', [(t + 45, 0.7, N('F2')), (t + 45, 0.7, N('A3'))], off=-4, sf=[t + 45], line=False)
    add('tuba', [(t + 45, 1.4, N('F1'))], off=-8, line=False)

    # -------------------------------------------------------------------------------------- A1b: f in the winds
    t, ch = T['A1b'], CH['A1b']
    play('flutes', t, ANT + ' | ' + CONS_F, shift=12, off=4)
    play('oboes', t, ANT + ' | ' + CONS_F, off=2)
    play('clarinets', t, ANT + ' | ' + CONS_F, shift=-12, off=0)
    add('violins1', run8(ch, 'D5'), 'spiccato', off=-6, line=False)
    add('violins2', run8(ch, 'D4'), 'spiccato', off=-6, line=False)
    add('violas', run8(ch, 'D3'), 'spiccato', off=-8, line=False)
    add('cellos', downbeats(ch, 'D2', 1.6), 'marcato', off=-2, line=False)
    add('basses', downbeats(ch, 'D1', 1.6), 'marcato', off=-4, line=False)
    add('bassoons', downbeats(ch, 'D2', 1.8), off=-6, line=False)
    # the horns' calls on the theme's long notes (the leap, the peak)
    add('horns', [(t + 3, 1.8, N('D4')), (t + 9, 1.8, N('A3')), (t + 27, 1.8, N('D4')), (t + 33, 1.8, N('F4')),
                  (t + 36, 2, N('D4')), (t + 38, 2, N('C4')), (t + 40, 2, N('C4'))], off=0, line=False)
    add('trombones', pad(ch[12:], ('F2', 'D4'), 3, 0.9), off=-6, line=False)
    add('tuba', bass(ch[12:], 'F1', 0.9), off=-6, line=False)
    add('trumpets', [(t + 9, 1, N('A4'), 78), (t + 33, 1.6, N('D5'), 92), (t + 42, 0.9, N('C5'), 98),
                     (t + 45, 1.0, N('C5'), 114)], line=False)
    add('timpani', [(t + 3, 1, N('D3'), 92), (t + 9, 1, N('A2'), 98), (t + 27, 1, N('D3'), 92),
                    (t + 33, 1, N('D3'), 100), (t + 36, 1, N('A2'), 96), (t + 38, 1, N('A2'), 100),
                    (t + 40, 1, N('C3'), 106), (t + 45, 1, N('F2'), 116)], 'hit', line=False)
    F_ST = {'violins1': ['F5', 'A5'], 'violins2': ['C5'], 'violas': ['F4'], 'cellos': ['F2', 'F3'], 'basses': ['F1']}
    strokes(F_ST, [t + 45], F_ST, length=0.8)
    add('percussion', [(t + 45, 2, keys['crash'])], None, off=-4, line=False)

    # -------------------------------------------------------------------------------------- dev: the cell passed on
    t, ch = T['dev'], CH['dev']
    play('violins1', t, DEV_STR1, off=6)
    play('violins2', t, DEV_STR1, shift=-12, off=0)
    add('violas', offbeats(ch[:8], ('D3', 'Bb3'), 2, 0.4), off=-10, line=False)
    add('cellos', downbeats(ch[:16], 'D2', 0.7), 'pizzicato', off=-2, line=False)
    add('basses', downbeats(ch[:16], 'D2', 0.7), 'pizzicato', off=-4, line=False)
    play('flutes', t + 12, DEV_WW1, off=4)
    play('oboes', t + 12, DEV_WW1, shift=-12, off=2)
    play('clarinets', t + 12, DEV_WW1, shift=-12, off=-2)
    add('violins1', [(t + 15, 6, N('F5')), (t + 21, 3, N('E5'))], off=-12, line=False)     # the strings hold under
    add('violins2', pad(ch[4:8], ('A4', 'D5'), 1), off=-12, line=False)
    play('violins1', t + 24, DEV_STR2, off=6)
    play('violins2', t + 24, DEV_STR2, shift=-12, off=0)
    add('clarinets', pad(ch[8:10], ('D4', 'Bb4'), 2), off=-8, line=False)
    play('flutes', t + 30, DEV_WW2, off=4)
    play('oboes', t + 30, DEV_WW2, shift=-12, off=2)
    add('violins2', pad(ch[10:12], ('Bb4', 'G5'), 2), off=-8, line=False)
    play('violins1', t + 36, DEV_STR3, off=6)
    play('violas', t + 36, DEV_STR3, shift=-12, off=0)
    add('bassoons', bass(ch[8:16], 'E2'), off=-6, line=False)
    add('horns', [(t + 36, 6, N('E3')), (t + 42, 6, N('E3'))], off=-4, line=False)
    for role, sh, o in (('violins1', 0, 6), ('violins2', -12, 2), ('flutes', 0, 4), ('oboes', 0, 2),
                        ('clarinets', -12, 0)):
        play(role, t + 42, DEV_ALL4, shift=sh, off=o)
    add('timpani', [(t + 42, 1, N('A2'), 70), (t + 45, 1, N('A2'), 82)], 'hit', line=False)
    # the dominant: the hemiola cascade, everyone
    for role, sh, o in (('violins1', 0, 6), ('violins2', -12, 4), ('flutes', 12, 4), ('oboes', 0, 2),
                        ('clarinets', -12, 0), ('violas', -12, 0)):
        play(role, t + 48, DEV_CASCADE, shift=sh, off=o, short=0.8)
    play('cellos', t + 48, DEV_CASCADE, shift=-24, off=0, short=0.8)
    add('basses', hemiola(ch, ('A1', 'A1'), 1, t + 48, 4), off=0, line=False)
    add('bassoons', hemiola(ch, ('A2', 'E3'), 2, t + 48, 4), off=-2, line=False)
    add('horns', hemiola(ch, ('A3', 'E4'), 2, t + 48, 4), off=-2, line=False)
    add('trombones', hemiola(ch, ('A2', 'C#4'), 3, t + 48, 4), off=-4, line=False)
    add('tuba', [(t + 48 + 2 * k, 1.6, N('A1')) for k in range(6)], off=-4, line=False)
    add('trumpets', [(t + 48 + 2 * k, 1.4, N('A4'), 78 + 6 * k) for k in range(6)] +
        [(t + 66, 1.0, N('A4'), 120), (t + 66, 1.0, N('E5'), 116)], line=False)
    add('timpani', [(t + 48 + 2 * k, 1, N('A2'), 96 + 2 * k) for k in range(6)], 'hit', line=False)
    add('timpani', [(t + 60, 6, N('A2'))], 'roll', off=0, line=False)
    add('timpani', [(t + 66, 1, N('A2'), 124)], 'hit', line=False)
    add('percussion', [(t + 60, 6, keys['cymbal_roll']), (t + 66, 3, keys['crash']), (t + 66, 2, keys['bass_drum'])],
        None, off=-4, line=False)
    A_ST = {'violins2': ['E5', 'C#5'], 'violas': ['A3', 'E4'], 'basses': ['A1'], 'bassoons': ['A2', 'E3'],
            'horns': ['A3', 'E4'], 'trombones': ['A2', 'C#3', 'E3'], 'tuba': ['A1'], 'cellos': ['A2']}
    strokes(A_ST, [t + 66], A_ST, length=0.8)

    # -------------------------------------------------------------------------------------- A3: the tutti theme
    t, ch = T['A3'], CH['A3']
    th = ANT_S + ' | ' + CONS_DS
    play('violins1', t, th, off=6, sf=False)
    play('violins1', t, th, shift=12, off=2)
    play('violins2', t, th, off=2)
    play('flutes', t, th, shift=12, off=2)
    play('oboes', t, th, off=0)
    play('clarinets', t, th, shift=-12, off=-2)
    add('violas', run8(ch, 'D3'), 'spiccato', off=-4, line=False)
    add('cellos', run8(ch, 'D2'), 'spiccato', off=-4, line=False)
    add('basses', downbeats(ch, 'D1', 1.5), 'marcato', off=0, line=False)
    add('bassoons', bass(ch, 'D2', 0.8), off=-4, line=False)
    add('horns', pad(ch, ('A3', 'F4'), 2, 0.9), off=-8, offs=lambda n: 8 if round((n[0] - t) % 6, 3) == 0 else -2,
        line=False)
    add('trombones', pad(ch, ('D3', 'A3'), 2, 0.85), off=-6, line=False)
    add('tuba', downbeats(ch, 'D1', 1.4), off=-8, offs=lambda n: 8 if round((n[0] - t) % 12, 3) == 0 else -4,
        line=False)
    trp = []
    for k, (st, d, sym) in enumerate(ch):
        r = tones(sym)[0]
        if k % 2 == 0 or k >= 12:
            trp.append((st, 0.9, low(r, 'D4'), 116 if k in (0, 8) else 104 if k % 4 == 0 else 86 if k < 12 else 96 + k))
    add('trumpets', trp, 'marcato', line=False)
    add('timpani', [(st, 1, N('D3') if tones(sym)[0] in (2, 7, 10, 5) else N('A2'), 108 if k % 4 == 0 else 92)
                    for k, (st, d, sym) in enumerate(ch) if k % 2 == 0] + [(t + 45, 1, N('D3'), 120)], 'hit',
        line=False)
    add('percussion', [(t, 3, keys['crash']), (t, 2, keys['bass_drum']), (t + 24, 3, keys['crash']),
                       (t + 24, 2, keys['bass_drum']), (t + 45, 3, keys['crash'])], None, off=-4, line=False)
    D_ST = {'cellos': ['D2', 'D3'], 'basses': ['D1'], 'violas': ['D3', 'A3'], 'trombones': ['D3', 'F3'],
            'horns': ['D4', 'F4'], 'trumpets': ['D4', 'A4']}
    strokes(D_ST, [t + 45], D_ST, length=0.8)

    # -------------------------------------------------------------------------------------- trans: the horn call
    t, ch = T['trans'], CH['trans']
    play('horns', t, TRANS_HORN, off=4, short=0.85)
    add('violas', [(t + 3, 9, N('F3'))], off=-8, line=False)
    add('cellos', [(t + 3, 9, N('Bb2'))], off=-8, line=False)
    add('basses', [(t + 9, 3, N('F1'))], 'pizzicato', off=-6, line=False)
    add('timpani', [(t + 3, 5, N('F2'))], 'roll', off=-14, line=False)

    # -------------------------------------------------------------------------------------- trio1: the horn landler
    t, ch = T['trio1'], CH['trio1']
    play('horns', t, HORN_T + ' | ' + HORN_T2, off=8, short=0.9, accent=6)
    add('violins2', pad(ch, ('F4', 'D5'), 2), off=-10, line=False)
    add('violas', pad(ch, ('Bb3', 'F4'), 2), off=-10, line=False)
    add('violins1', pad(ch[8:], ('D5', 'F5'), 1), off=-12, line=False)
    add('cellos', downbeats(ch, 'Bb2', 0.8), 'pizzicato', off=-4, line=False)
    add('basses', downbeats(ch, 'Bb1', 0.8), 'pizzicato', off=-6, line=False)
    hv = voice_lead([c[2] for c in ch], register=(N('F3'), N('D5')), voices=3)
    add('harp', [(st + BPB * k + bt + 0.03 * j, 0.9, p) for (st, d, sym), v in zip(ch, hv)
                 for k in range(int(round(d / BPB))) for bt in (1, 2) for j, p in enumerate(sorted(v))],
        None, off=-10, line=False)
    play('flutes', t, FLUTE_ECHO1, off=-2, short=0.9)
    play('clarinets', t + 24, FLUTE_ECHO1, shift=-12, off=-4, short=0.9)
    add('bassoons', bass(ch[8:], 'Bb1', 0.95), off=-10, line=False)

    # -------------------------------------------------------------------------------------- trio2: G minor, then home
    t, ch = T['trio2'], CH['trio2']
    play('clarinets', t, CLAR_T, off=6, short=0.9, accent=6)
    fl = [(a, d, p + 12) for a, d, p in mel(t, CLAR_T)]
    # the flute a third over the clarinet (diatonic in G minor: a third up from each degree)
    gm = [N(x) for x in 'G4 A4 Bb4 C5 D5 Eb5 F#5 G5 A5 Bb5 C6 D6 Eb6 F#6'.split()]

    def third_up(p):
        q = p - 12
        for i, x in enumerate(gm):
            if x == q and i + 2 < len(gm):
                return gm[i + 2]
        return q + 3
    fl = [(a, d, third_up(p)) for a, d, p in fl]
    _, acc = parse(t, CLAR_T)
    add('flutes', fl, off=0, offs=shaper(acc, fl, 6), line=True, dur=lambda n: 0.9 if n[1] <= 1.01 else 0.94)
    add('violins2', pad(ch[:8], ('D4', 'Bb4'), 2), off=-10, line=False)
    add('violas', pad(ch[:8], ('G3', 'D4'), 2), off=-10, line=False)
    add('cellos', downbeats(ch, 'G2', 0.8), 'pizzicato', off=-4, line=False)
    add('basses', downbeats(ch, 'G1', 0.8), 'pizzicato', off=-6, line=False)
    add('horns', [(t, 9, N('D3')), (t + 9, 3, N('D3')), (t + 12, 9, N('G3')), (t + 21, 3, N('F#3'))], off=-8,
        line=False)
    hv = voice_lead([c[2] for c in ch], register=(N('F3'), N('D5')), voices=3)
    add('harp', [(st + bt + 0.03 * j, 0.9, p) for (st, d, sym), v in zip(ch, hv)
                 for bt in (1, 2) if bt < d - 1e-6 for j, p in enumerate(sorted(v))], None, off=-12, line=False)
    play('horns', t + 24, HORN_T2, off=8, short=0.9, accent=6)
    play('violins1', t + 24, VLN_COUNTER, off=0, short=0.9, accent=4)
    add('violins2', pad(ch[8:], ('F4', 'Bb4'), 2), off=-12, line=False)
    add('violas', pad(ch[8:], ('Bb3', 'F4'), 2), off=-12, line=False)
    add('bassoons', bass(ch[8:], 'Bb1', 0.95), off=-10, line=False)
    add('percussion', [(t + 24, 1, keys['triangle']), (t + 36, 1, keys['triangle'])], None, off=0, line=False)

    # -------------------------------------------------------------------------------------- retrans: the creeping head
    t, ch = T['retrans'], CH['retrans']
    play('bassoons', t, RT_BSN, off=4)
    play('clarinets', t + 6, RT_CL, off=4)
    play('violas', t + 12, RT_VLA, off=4)
    play('violins1', t + 18, RT_VLN, off=4)
    play('violins2', t + 18, RT_VLN, shift=-12, off=0)
    add('cellos', [(t, 12, N('G3')), (t + 12, 12, N('A3'))], 'tremolo', off=-6, line=False)
    add('basses', [(t + 12, 12, N('A1'))], off=-8, line=False)
    add('horns', [(t + 12, 6, N('E3')), (t + 18, 5, N('E3'))], off=-6, line=False)
    add('timpani', [(t + 12 + 3 * k, 1, N('A2'), 40 + 9 * k) for k in range(4)], 'hit', line=False)

    # -------------------------------------------------------------------------------------- R1: the theme down low
    t, ch = T['R1'], CH['R1']
    play('cellos', t, ANT, shift=-12, off=8)
    play('bassoons', t, ANT, shift=-12, off=2)
    add('basses', downbeats(ch, 'D2', 0.7), 'pizzicato', off=-4, line=False)
    add('violins1', offbeats(ch, ('D5', 'A5'), 2, 0.6), 'pizzicato', off=-6, line=False)
    add('violins2', offbeats(ch, ('F4', 'D5'), 2, 0.6), 'pizzicato', off=-8, line=False)
    wc = [(a, d, p, 54 if round(a % BPB) == 1 else 44) for a, d, p in offbeats(ch, ('F4', 'D5'), 3, 0.5)]
    add('oboes', [n for n in wc if n[2] >= N('C5')], 'staccato', off=-2, line=False)
    add('clarinets', [n for n in wc if n[2] < N('C5')], 'staccato', off=-2, line=False)
    add('flutes', [(t + 9, 1.8, N('A5')), (t + 15, 1, N('G5')), (t + 16, 1, N('F5'))], off=-8, line=False)

    # -------------------------------------------------------------------------------------- R2: the answer in canon
    t, ch = T['R2'], CH['R2']
    play('violins1', t, CONS_V, off=6)
    play('violins2', t, CONS_V, shift=-12, off=0)
    canon = CONS_V.split(' | ')[:7]
    play('flutes', t + 3, ' | '.join(canon), shift=12, off=2)
    play('oboes', t + 3, ' | '.join(canon), off=0)
    add('violas', run8(ch, 'D3'), 'spiccato', off=-8, line=False)
    add('cellos', downbeats(ch, 'D2', 1.0), 'marcato', off=-2, line=False)
    add('basses', downbeats(ch, 'D1', 1.0), 'marcato', off=-4, line=False)
    add('bassoons', bass(ch, 'D2', 0.9), off=-8, line=False)
    add('horns', [(t + 12, 6, N('D4')), (t + 18, 6, N('E4'))], off=-4, line=False)
    add('timpani', [(t + 18, 4.5, N('A2'))], 'roll', off=-10, line=False)
    add('timpani', [(t + 22.5, 0.5, N('A2'), 96)], 'hit', line=False)
    add('percussion', [(t + 18, 5, keys['cymbal_roll_short'])], None, off=-8, line=False)

    # -------------------------------------------------------------------------------------- R3: the tutti with canon
    t, ch = T['R3'], CH['R3']
    th = ANT_S + ' | ' + CONS_DS
    play('violins1', t, th, off=6)
    play('violins1', t, th, shift=12, off=2)
    play('flutes', t, th, shift=12, off=2)
    play('oboes', t, th, off=0)
    play('violins2', t, th, off=0)
    lowc = ' | '.join(th.split(' | ')[:14])
    play('cellos', t + 3, lowc, shift=-24, off=4)
    play('basses', t + 3, lowc, shift=-36, off=0)
    play('bassoons', t + 3, lowc, shift=-24, off=0)
    add('cellos', [(t, 1, N('D2'))] + [(t + 45, 0.8, N('D2'))], 'marcato', off=4, line=False)
    add('basses', [(t, 1, N('D1'))] + [(t + 45, 0.8, N('D1'))], 'marcato', off=4, line=False)
    add('violas', run8(ch, 'D3'), 'spiccato', off=-4, line=False)
    add('clarinets', pad(ch, ('D4', 'A4'), 2, 0.85), off=-6, line=False)
    fan = []
    for k, (st, d, sym) in enumerate(ch):
        if k in (0, 2, 4, 8, 10, 12, 14):
            r = low(tones(sym)[0], 'D4')
            fan += [(st, 0.6, r), (st + 2, 0.4, r), (st + 2.5, 0.4, r)]
    add('trumpets', fan, 'marcato', off=-12, offs=lambda n: 12 if round((n[0] - t) % 12, 3) == 0 else
        4 if round(n[0] % 3, 3) == 0 else -8, line=False)
    add('horns', pad(ch, ('A3', 'F4'), 2, 0.9), off=-8, offs=lambda n: 8 if round((n[0] - t) % 6, 3) == 0 else -2,
        line=False)
    add('trombones', pad(ch, ('D3', 'Bb3'), 3, 0.85), off=-4, line=False)
    add('tuba', downbeats(ch, 'D1', 1.4), off=-8, offs=lambda n: 8 if round((n[0] - t) % 12, 3) == 0 else -4,
        line=False)
    add('timpani', [(st, 1, N('D3') if tones(sym)[0] in (2, 7, 10, 5) else N('A2'), 112 if k % 4 == 0 else 94)
                    for k, (st, d, sym) in enumerate(ch)] + [(t + 45, 1, N('D3'), 122)], 'hit', line=False)
    add('percussion', [(t, 3, keys['crash']), (t, 2, keys['bass_drum']), (t + 24, 3, keys['sus_cymbal']),
                       (t + 36, 3, keys['crash']), (t + 45, 3, keys['crash']), (t + 45, 2, keys['bass_drum'])], None,
        off=-4, line=False)
    strokes(D_ST, [t + 45], {**D_ST, 'cellos': ['D3'], 'basses': ['D2']}, length=0.8)

    # -------------------------------------------------------------------------------------- coda: stretto and strokes
    t, ch = T['coda'], CH['coda']
    for k, (role, o, p, sh, off) in enumerate((('cellos', 'A2', 'D3', 0, 4), ('violas', 'A3', 'D4', 0, 4),
                                                ('violins2', 'A4', 'D5', 0, 4), ('violins1', 'A5', 'D6', 0, 6))):
        txt = STRETTO.format(o=o, p=p, e='E' + p[1:])
        play(role, t + 3 * k, txt, off=off)
    play('bassoons', t, STRETTO.format(o='A2', p='D3', e='E3'), off=0)
    play('clarinets', t + 6, STRETTO.format(o='A3', p='D4', e='E4'), off=0)
    play('oboes', t + 6, STRETTO.format(o='A4', p='D5', e='E5'), off=0)
    play('flutes', t + 9, STRETTO.format(o='A5', p='D6', e='E6'), off=2)
    add('basses', [(t, 12, N('D2'))], off=-4, line=False)
    add('cellos', [(t + 6, 6, N('D3'))], off=-6, line=False)
    add('horns', [(t, 6, N('A3')), (t + 6, 6, N('D4'))], off=-2, line=False)
    add('timpani', [(t + 3 * k + b, 1, N('D3') if b == 0 else N('A2'), 72 + 6 * k - (14 if b else 0))
                    for k in range(4) for b in (0, 1, 2)], 'hit', line=False)
    # the hemiola once more, everyone
    for role, sh, o in (('violins1', 0, 6), ('violins2', -12, 2), ('flutes', 12, 4), ('oboes', 0, 0),
                        ('clarinets', -12, 0)):
        play(role, t + 12, CODA_HEMI, shift=sh, off=o)
    play('cellos', t + 12, CODA_HEMI, shift=-24, off=2)
    play('violas', t + 12, CODA_HEMI, shift=-12, off=0)
    add('basses', bass(ch[4:8], 'D1', 0.9), off=0, line=False)
    add('bassoons', bass(ch[4:8], 'D2', 0.9), off=-2, line=False)
    add('horns', pad(ch[4:8], ('A3', 'F4'), 2, 0.9), off=0, line=False)
    add('trombones', pad(ch[4:8], ('D3', 'Bb3'), 3, 0.9), off=-4, line=False)
    add('tuba', bass(ch[4:8], 'D1', 0.9), off=-4, line=False)
    add('trumpets', [(t + 15, 1.8, N('D5'), 92), (t + 18, 1.8, N('D5'), 104), (t + 21, 2.6, N('E5'), 116)],
        'marcato', line=False)
    add('timpani', [(t + 12, 1, N('D3'), 104), (t + 15, 1, N('D3'), 100), (t + 18, 1, N('D3'), 106),
                    (t + 20, 1, N('A2'), 108), (t + 22, 1, N('A2'), 112)], 'hit', line=False)
    # the scale rushing up, the last hemiola
    for role, sh, o, art_ in (('violins1', 0, 6, 'sustain'), ('violins2', -12, 2, 'sustain'),
                              ('flutes', 0, 2, 'sustain'), ('oboes', -12, 0, 'sustain'),
                              ('violas', -12, 0, 'sustain')):
        play(role, t + 24, CODA_RUN, shift=sh, off=o, short=0.8)
    play('cellos', t + 24, CODA_RUN, shift=-24, off=2, short=0.8)
    add('clarinets', pad(ch[8:12], ('D4', 'A4'), 2, 0.9), off=-4, line=False)
    add('basses', bass(ch[8:12], 'D1', 0.9), off=0, line=False)
    add('bassoons', bass(ch[8:12], 'D2', 0.9), off=-2, line=False)
    add('horns', [(t + 27, 2.6, N('A3')), (t + 30, 2, N('D4')), (t + 32, 1, N('D4')), (t + 33, 2, N('C#4'))],
        off=0, line=False)
    add('trombones', pad(ch[8:12], ('D3', 'A3'), 3, 0.9), off=-4, line=False)
    add('tuba', bass(ch[8:12], 'D1', 0.9), off=-4, line=False)
    add('trumpets', [(t + 27, 1.6, N('E5'), 100), (t + 30, 1.8, N('D5'), 110), (t + 33, 2, N('E5'), 122)],
        'marcato', line=False)
    add('timpani', [(t + 24, 3, N('D3'))], 'roll', off=-2, line=False)
    add('timpani', [(t + 27, 1, N('A2'), 112), (t + 30, 1, N('D3'), 114), (t + 32, 1, N('D3'), 104),
                    (t + 34, 1, N('A2'), 118)], 'hit', line=False)
    add('percussion', [(t + 24, 3, keys['cymbal_roll_short']), (t + 27, 3, keys['crash'])], None, off=-6, line=False)
    # the strokes: D - A - D D
    for role, sh, o in (('violins1', 0, 6), ('violins2', -12, 2), ('flutes', 0, 2), ('oboes', -12, 0)):
        play(role, t + 36, CODA_END, shift=sh, off=o, short=0.75)
    ends = [t + 36, t + 39, t + 42, t + 44, t + 45]
    Dc = {'violas': ['D4', 'F4'], 'cellos': ['D3', 'A3'], 'basses': ['D2'], 'clarinets': ['F4', 'A4'],
          'bassoons': ['D2', 'D3'], 'horns': ['D4', 'F4'], 'trumpets': ['D4', 'D5'], 'trombones': ['D3', 'F3', 'A3'],
          'tuba': ['D2']}
    Ac = {'violas': ['C#4', 'E4'], 'cellos': ['A2', 'E3'], 'basses': ['A1'], 'clarinets': ['E4', 'G4'],
          'bassoons': ['A2', 'C#3'], 'horns': ['C#4', 'E4'], 'trumpets': ['A4', 'E5'],
          'trombones': ['A2', 'E3', 'G3'], 'tuba': ['A1']}
    for tt in ends:
        strokes(Dc if tt != t + 39 else Ac, [tt], Dc if tt != t + 39 else Ac, length=0.75 if tt < t + 45 else 1.2)
    add('timpani', [(tt, 1, N('A2') if tt == t + 39 else N('D3'), 118 if tt != t + 45 else 126) for tt in ends],
        'hit', line=False)
    add('percussion', [(t + 36, 3, keys['crash']), (t + 36, 2, keys['bass_drum']), (t + 45, 4, keys['crash']),
                       (t + 45, 3, keys['bass_drum'])], None, off=-2, line=False)

    sc.perform()
    return s
