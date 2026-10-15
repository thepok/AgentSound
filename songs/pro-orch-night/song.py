"""Night Rain - a hand-written nocturne for chamber orchestra (F major, 4/4, 62 BPM, ~3:50).
Build: python -m agentsound build songs/pro-orch-night

A lullaby-like theme for flute over a rocking harp and soft strings, still and pastoral (the quiet register of
Desplat / Hisaishi). A "pro" reference for the blind test against the endless orchestra genre: same band setup.

  intro   4   harp rocking on an F pedal, violas / cellos pp; the clarinet hints the theme's head
  A       8   the theme on the flute (A4-F5), harp in rocking eighths, a divisi string bed, half cadence on C7
  B       8   contrast in D minor: the clarinet sings low, a cello counter-line, harp rolled chords, violins I
              a high halo, the bVII (Ebmaj7) turning back to C7
  A2      8   the theme re-orchestrated: violins I take it, the flute answers in the gaps above, a horn enters
  build   8   the head rises in sequence (clarinet - oboe - flute + violins) over a falling bass Bb Bb A F# G F Eb C
  climax  8   the theme an octave up (violins I + flute), violins II + clarinet at pitch, the cellos' tenor counter,
              horns warm in the middle, the borrowed Bbm6 under the peak's last sigh
  A3      8   quiet return: flute then clarinet, violin harmonics, sparse harp, ritenuto
  coda    4   the sighs D-C and Db-C over an F pedal, harp arpeggios
  end     2   the held Fadd9, fading
"""
from agentsound import *
from agentsound.bandlib import orchestra as orch
from agentsound.endless.orchestra import band as orchestra_band
from agentsound.theory import chord as _chord

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'Night Rain', 'artist': 'AgentSound', 'album': 'Orchestral References',
            'genre': 'Orchestral', 'year': 2026}
COVER = {'style': 'classical', 'palette': ['#141b2b', '#9db3cf'], 'title': 'night rain',
         'subtitle': 'AgentSound - Orchestral References', 'seed': 56}

KEY = 'F major'
HARP = 20          # the harp's velocity lift: its rocking eighths are the night's pulse, heard under every line
SEED = 5606
TEMPO = 62
ROLES = ('violins1', 'violins2', 'violas', 'cellos', 'basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
         'harp')

FORM = [('intro', 4), ('A', 8), ('B', 8), ('A2', 8), ('build', 8), ('climax', 8), ('A3', 8), ('coda', 4),
        ('end', 2)]

# ------------------------------------------------------------------------------------------------ harmony
CHART = {
    'intro': 'Fadd9 | Bbmaj7/F | Fadd9 | Gm7/C:0.5 C7:0.5',
    'A': 'Fmaj7 | Dm7 | Bbmaj7 | C7sus4:0.5 C7:0.5 | Am7 | Dm7:0.5 G7/B:0.5 | Bbmaj7:0.5 Gm7:0.5 | Gm7/C:0.5 C7:0.5',
    'B': 'Dm | Bb/D | Gm7 | A7sus4:0.5 A7:0.5 | Dm:0.5 D7/F#:0.5 | Gm7 | Ebmaj7 | C7sus4:0.5 C7:0.5',
    'A2': 'Fmaj7 | Dm7:0.5 Dm7/C:0.5 | Bbmaj7 | C7sus4:0.5 C7:0.5 | Am7:0.5 A7:0.5 | Dm7:0.5 G7/B:0.5 | '
          'Bbmaj7:0.5 Gm7:0.5 | Gm7/C:0.5 C7:0.5',
    'build': 'Bbmaj9 | C/Bb | Am7 | D7/F# | Gm7 | Gm7/F | Ebmaj7 | C7sus4:0.5 C7:0.5',
    'climax': 'Fadd9 | Dm7/C | Bbmaj7 | Gm7/C:0.5 C7:0.5 | Am7:0.5 A7:0.5 | Dm7:0.5 G7/B:0.5 | Bbmaj7:0.5 Bbm6:0.5 | '
              'F/C:0.5 C7:0.5',
    'A3': 'Fmaj7 | Dm7 | Bbmaj7 | C7sus4:0.5 C7:0.5 | Am7 | Dm7:0.5 G7/B:0.5 | Bbmaj7:0.5 Bbm6:0.5 | Fadd9',
    'coda': 'Bbmaj7/F | Fadd9 | Bbm6/F | Fadd9',
    'end': 'Fadd9 | Fadd9',
}

# ------------------------------------------------------------------------------------------------ the lines
THEME = ('A4/4. G4/8 A4/4 C5/4 | D5/2. C5/4 | D5/4. C5/8 Bb4/4 A4/4 | G4/2. r/4 | '
         'A4/4. G4/8 A4/4 E5/4 | F5/4 E5/8 D5/8 B4/4 D5/4 | C5/4. Bb4/8 A4/4 G4/4 | Bb4/4. A4/8 G4/4 r/4')
THEME2 = ('A4/4. G4/8 A4/4 C5/4 | D5/2. C5/4 | D5/4. C5/8 Bb4/4 A4/4 | G4/2. F4/8 G4/8 | '
          'A4/4. G4/8 A4/4 E5/4 | F5/4 E5/8 D5/8 B4/4 D5/4 | C5/4. Bb4/8 A4/4 G4/4 | Bb4/4. A4/8 G4/2')
# A2: the flute answers above the violins, only where the theme holds or breathes
A2_FLUTE = 'r/1 | r/2 A5/4 G5/4 | F5/2. r/4 | r/2 Bb5/4 A5/4 | G5/2. r/4 | r/1 | r/2 D6/4 C6/4 | Bb5/2 r/2'

B_CLAR = ('D4/4 E4/4 F4/4 A4/4 | D5/2. C5/4 | Bb4/4. A4/8 G4/4 F4/4 | E4/2 C#4/4 r/4 | '
          'D4/4 F4/4 A4/4 C5/4 | Bb4/4. D5/8 F5/2 | G5/4. F5/8 Eb5/4 D5/4 | C5/2 Bb4/4 G4/4')
B_CELLO = 'F3/1 | F3/2 G3/2 | Bb3/1 | A3/2 G3/2 | F3/2 A3/2 | Bb3/2 D4/2 | G3/2 Bb3/2 | F3/2 E3/2'

# build: the theme's head in a rising sequence, passed from instrument to instrument
BUILD_CLAR = 'D5/4. C5/8 D5/4 F5/4 | G5/2. r/4 | r/1 | r/1 | r/1 | r/1 | r/1 | r/1'
BUILD_OBOE = 'r/1 | r/1 | E5/4. D5/8 E5/4 G5/4 | A5/2. r/4 | r/1 | r/1 | G5/4. F5/8 G5/4 Bb5/4 | C6/2. Bb5/4'
BUILD_TOP = ('r/1 | r/1 | r/1 | r/1 | F5/4. E5/8 F5/4 A5/4 | Bb5/2. A5/8 G5/8 | G5/4. F5/8 G5/4 Bb5/4 | '
             'C6/2. Bb5/4')

CLIMAX = ('A5/4. G5/8 A5/4 C6/4 | D6/2. C6/4 | D6/4. C6/8 Bb5/4 A5/4 | G5/2. A5/8 Bb5/8 | '
          'A5/4. G5/8 A5/4 E6/4 | F6/4 E6/8 D6/8 B5/4 D6/4 | D6/4. C6/8 Bb5/4 Db6/4 | C6/2 Bb5/2')
CLIMAX_CELLO = 'C4/2. A3/4 | F3/2 G3/4 A3/4 | Bb3/2. D4/4 | D4/2 E4/2 | E4/2 C#4/2 | A3/2 F3/2 | F3/1 | A3/2 G3/2'

A3_FLUTE = 'A4/4. G4/8 A4/4 C5/4 | D5/2. C5/4 | D5/4. C5/8 Bb4/4 A4/4 | G4/2. r/4 | r/1 | r/1 | r/1 | r/1'
A3_CLAR = 'r/1 | r/1 | r/1 | r/1 | A4/4. G4/8 A4/4 E5/4 | F5/4 E5/8 D5/8 B4/4 D5/4 | C5/4. Bb4/8 Bb4/4 Db5/4 | C5/2. r/4'

INTRO_CLAR = 'r/1 | r/1 | r/2 A4/4. G4/8 | A4/2 r/2'
CODA_FLUTE = 'D5/2. C5/4 | r/1 | r/1 | r/1'
CODA_CLAR = 'r/1 | r/1 | Db5/2. C5/4 | r/1'

# the dynamics: one map for the whole piece (velocities; pp 28, p 40, mp 58, mf 78, f 95)
DYN = {
    'intro': [(0, 24), (8, 32), (16, 34)],
    'A': [(0, 40), (12, 46), (16, 42), (28, 48), (32, 44)],
    'B': [(0, 44), (16, 52), (24, 58), (30, 54), (32, 50)],
    'A2': [(0, 50), (12, 56), (16, 52), (28, 58), (32, 54)],
    'build': [(0, 50), (8, 56), (16, 64), (24, 72), (32, 82)],
    'climax': [(0, 80), (8, 86), (16, 84), (20, 88), (24, 84), (28, 70), (32, 52)],
    'A3': [(0, 44), (16, 38), (28, 33), (32, 30)],
    'coda': [(0, 30), (16, 24)],
    'end': [(0, 24), (8, 14)],
}


def build() -> Song:
    s = Song('Night Rain', tempo=TEMPO, key=KEY, seed=SEED, tail=8)
    S = {name: s.section(name, bars=n) for name, n in FORM}

    # ------------------------------------------------------------------------------------------ time
    for name in ('A', 'B', 'A2', 'A3'):
        s.rubato(S[name], depth=0.025, phrase='breath', seed=len(name) + 3)
    s.ritardando((S['B'].bar(7), S['B'].end), to=0.93, a_tempo=True)
    s.ritardando((S['build'].bar(7), S['build'].end), to=0.9, a_tempo=True)
    s.ritardando((S['climax'].bar(6), S['climax'].end), to=0.84, a_tempo=False)
    s.set_tempo(S['A3'], 58)
    s.ritardando((S['A3'].bar(6), S['A3'].end), to=0.93, a_tempo=False)
    s.ritardando((S['coda'].bar(1), S['end'].start), to=0.8, a_tempo=False)

    b = orchestra_band(s, ROLES)
    sc = orch.Score(s, b, DYN, key=KEY, seed=SEED, style='film')

    H = {}
    for name, _ in FORM:
        H[name] = s.harmony(CHART[name], S[name])
        sc.harmony(H[name])
    s.endless_timeline = [t for name, _ in FORM for t in H[name].timeline()]

    # ------------------------------------------------------------------------------------------ helpers
    def line(role, spec, sec, *, shift=0, off=0.0, dur=1.0, art='sustain', is_line=True):
        ns = [(S[sec].start + n.start, n.dur, n.pitch + shift) for n in notes(spec, length='bar')]
        sc.add(role, ns, art, off=off, dur=dur, line=is_line)

    def pad(role, sec, reg, n=2, off=-6.0, dur=1.0, bars=None):
        ns = [(x.start, x.dur, x.pitch) for x in H[sec].voice(reg, n, 60)]
        if bars is not None:
            a, e = S[sec].start + bars[0] * 4, S[sec].start + bars[1] * 4
            ns = [x for x in ns if a - 1e-6 <= x[0] < e - 1e-6]
        sc.add(role, ns, off=off, dur=dur, line=False)

    def tones(sym):
        c = _chord(sym)
        bass = c.bass_pc if c.bass_pc is not None else c.root
        return bass, set(c.pcs) | {bass}

    def bass(role, sec, lo, off=-2.0, art='sustain', every=None, dur=1.0, bars=None):
        out = []
        for a, d, sym in H[sec].timeline():
            if bars is not None and not (S[sec].start + bars[0] * 4 - 1e-6 <= a < S[sec].start + bars[1] * 4 - 1e-6):
                continue
            bp, _ = tones(sym)
            p = lo + ((bp - lo) % 12)
            if every:
                t = a
                while t < a + d - 1e-6:
                    out.append((t, min(every, a + d - t), p))
                    t += every
            else:
                out.append((a, d, p))
        sc.add(role, out, art, off=off, dur=dur, line=False)

    def harp(sec, kind, off=0.0, lo=41, bars=None, ring=1.6):
        """The harp's figure per chord: 'rock' (up and back in eighths), 'rise' (two ascending arpeggios a bar),
        'broad' (one sweep up two octaves), 'roll' (a rolled chord on the change)."""
        out = []
        for a, d, sym in H[sec].timeline():
            if bars is not None and not (S[sec].start + bars[0] * 4 - 1e-6 <= a < S[sec].start + bars[1] * 4 - 1e-6):
                continue
            bp, pcs = tones(sym)
            low = lo + ((bp - lo) % 12)
            ups = [p for p in range(low + 5, low + 34) if p % 12 in pcs]
            n = int(round(d / 0.5))
            if kind == 'rock':
                shape = [0, 1, 2, 3, 4, 3, 2, 1][:n] if n >= 8 else [0, 1, 2, 3][:n]
                seq = [low if k == 0 else ups[k - 1] for k in shape]
                out += [(a + 0.5 * i, ring, p) for i, p in enumerate(seq)]
            elif kind == 'rise':
                for w in range(n // 4):
                    seq = [low, ups[0], ups[1], ups[2]] if w % 2 == 0 else [ups[1], ups[2], ups[3], ups[4]]
                    out += [(a + 2 * w + 0.5 * i, ring, p) for i, p in enumerate(seq)]
            elif kind == 'broad':
                seq = [low] + ups[:n - 1]
                out += [(a + 0.5 * i, ring + 0.6, p) for i, p in enumerate(seq)]
            elif kind == 'roll':
                seq = [low - 12 if low > 45 else low, low + 7] + ups[2:6]
                out += [(a + 0.07 * i, d, p) for i, p in enumerate(seq)]
        sc.add('harp', out, None, off=off + HARP, line=False, accent=kind != 'roll')

    # ============================================================== intro: rocking harp on an F pedal
    harp('intro', 'rock', off=2)
    pad('violas', 'intro', ('A3', 'F4'), 2, off=-6)
    sc.add('cellos', [(S['intro'].start, 16, note('F2'))], off=-6, line=False)
    sc.add('basses', [(S['intro'].start + 8, 8, note('F2'))], off=-10, line=False)
    line('clarinets', INTRO_CLAR, 'intro', off=4, dur=0.95)

    # ============================================================== A: the flute's lullaby
    line('flutes', THEME, 'A', off=10, dur=0.95)
    harp('A', 'rock', off=0)
    pad('violas', 'A', ('F3', 'D4'), 2, off=-14)
    bass('cellos', 'A', 41, off=-14)
    bass('basses', 'A', 29, off=-10, bars=(4, 8))

    # ============================================================== B: D minor, the clarinet low, the cellos answer
    line('clarinets', B_CLAR, 'B', off=10, dur=0.94)
    line('cellos', B_CELLO, 'B', off=-16)
    harp('B', 'roll', off=-2)
    pad('violins2', 'B', ('D4', 'Bb4'), 1, off=-20)
    pad('violas', 'B', ('A3', 'F4'), 1, off=-14)
    pad('violins1', 'B', ('F5', 'D6'), 1, off=-28, bars=(4, 8))
    bass('basses', 'B', 29, off=-2, art='pizzicato', every=4)
    bass('bassoons', 'B', 38, off=-10, dur=0.95)

    # ============================================================== A2: the violins take the theme, the flute answers
    line('violins1', THEME2, 'A2', off=6)
    line('flutes', A2_FLUTE, 'A2', off=2, dur=0.95)
    harp('A2', 'rise', off=-1)
    pad('violins2', 'A2', ('C4', 'G4'), 1, off=-14)
    pad('violas', 'A2', ('F3', 'D4'), 2, off=-14)
    pad('clarinets', 'A2', ('A3', 'F4'), 1, off=-10, dur=0.94, bars=(0, 4))
    pad('horns', 'A2', ('C3', 'A3'), 1, off=-10, dur=0.94, bars=(4, 8))
    bass('cellos', 'A2', 41, off=-12)
    bass('basses', 'A2', 29, off=-8)

    # ============================================================== build: the head rising, the bass falling
    line('clarinets', BUILD_CLAR, 'build', off=8, dur=0.94)
    line('oboes', BUILD_OBOE, 'build', off=6, dur=0.94)
    line('flutes', BUILD_TOP, 'build', off=6, dur=0.95)
    line('violins1', BUILD_TOP, 'build', off=0)
    sc.add('violins2', [(S['build'].start + n.start, n.dur, n.pitch - 12)
                        for n in notes(BUILD_TOP, length='bar') if n.start >= 24], off=-2, line=True)
    harp('build', 'rise', off=0)
    pad('violins2', 'build', ('D4', 'A4'), 2, off=-12, bars=(0, 6))
    pad('violas', 'build', ('G3', 'E4'), 2, off=-12)
    pad('horns', 'build', ('C3', 'A3'), 2, off=-14, dur=0.95, bars=(4, 8))
    bass('cellos', 'build', 38, off=-6)
    bass('basses', 'build', 26, off=-4)
    bass('bassoons', 'build', 38, off=-8, dur=0.95, bars=(2, 8))
    # the harp's glissando into the climax (C mixolydian, up to the A5 the theme lands on)
    gl = 'C3 D3 E3 F3 G3 A3 Bb3 C4 D4 E4 F4 G4 A4 Bb4 C5 D5 E5 F5 G5'.split()
    t0 = S['climax'].start - 1.6
    sc.add('harp', [(t0 + 1.55 * i / len(gl), 1.2, note(x), 46 + 2 * i) for i, x in enumerate(gl)], None, off=HARP, line=False)

    # ============================================================== climax: the theme at its warmest
    line('violins1', CLIMAX, 'climax', off=0)
    line('flutes', CLIMAX, 'climax', off=-2, dur=0.95)
    line('violins2', CLIMAX, 'climax', shift=-12, off=0)
    line('clarinets', CLIMAX, 'climax', shift=-12, off=-4, dur=0.95)
    line('cellos', CLIMAX_CELLO, 'climax', off=-3)
    harp('climax', 'broad', off=-2)
    pad('violas', 'climax', ('A3', 'F4'), 2, off=-14)
    pad('horns', 'climax', ('F3', 'D4'), 2, off=-20, dur=0.95)
    pad('oboes', 'climax', ('F4', 'D5'), 1, off=-10, dur=0.94, bars=(4, 8))
    bass('basses', 'climax', 29, off=-2)
    bass('bassoons', 'climax', 38, off=-12, dur=0.95)

    # ============================================================== A3: the quiet return
    line('flutes', A3_FLUTE, 'A3', off=10, dur=0.95)
    line('clarinets', A3_CLAR, 'A3', off=10, dur=0.95)
    harp('A3', 'rock', off=-2, lo=48)
    pad('violas', 'A3', ('A3', 'G4'), 2, off=-10)
    pad('violins1', 'A3', ('A5', 'F6'), 1, off=-6)
    sc.parts['violins1'] = [n[:4] + ('harmonics',) if S['A3'].start - 1e-6 <= n[0] < S['coda'].start - 1e-6 else n
                            for n in sc.parts['violins1']]
    bass('cellos', 'A3', 41, off=-10)
    bass('basses', 'A3', 29, off=-12, bars=(4, 8))

    # ============================================================== coda: the sighs over the F pedal
    line('flutes', CODA_FLUTE, 'coda', off=10, dur=0.95)
    line('clarinets', CODA_CLAR, 'coda', off=10, dur=0.95)
    pad('violas', 'coda', ('A3', 'F4'), 2, off=-8)
    sc.add('cellos', [(S['coda'].start, 16, note('F2'))], off=-4, line=False)
    c0 = S['coda'].start
    arp1 = 'F2 C3 F3 A3 C4 G4 A4 C5'.split()
    arp2 = 'F2 C3 F3 A3 C4 G4 A4 C5 F5 A5'.split()
    sc.add('harp', [(c0 + 4 + 0.5 * i, 2.5, note(x)) for i, x in enumerate(arp1)], None, off=2 + HARP, line=False)
    sc.add('harp', [(c0 + 12 + 0.4 * i, 3.5, note(x)) for i, x in enumerate(arp2)], None, off=2 + HARP, line=False)
    sc.add('harp', [(c0 + 0.08 * i, 3.5, note(x)) for i, x in enumerate('F2 F3 Bb3 D4 A4'.split())], None, off=HARP, line=False)
    sc.add('harp', [(c0 + 8 + 0.08 * i, 3.5, note(x)) for i, x in enumerate('F2 F3 Bb3 Db4 G4'.split())],
           None, off=HARP, line=False)

    # ============================================================== end: the held Fadd9
    e0 = S['end'].start
    sc.add({'violins1': [(e0, 7.6, note('A5'))], 'violins2': [(e0, 7.6, note('C5'))],
            'violas': [(e0, 7.6, note('F4')), (e0, 7.6, note('A3'))], 'cellos': [(e0, 7.6, note('C3'))],
            'basses': [(e0, 7.6, note('F2'))]},
           off={'violins1': -10, 'violins2': -12, 'violas': -12, 'cellos': -10, 'basses': -14})
    sc.add('harp', [(e0 + 0.1 * i, 7.5, note(x)) for i, x in enumerate('F2 C3 F3 A3 C4 G4 A4 C5 F5'.split())],
           None, off=4 + HARP, line=False, accent=False)

    sc.perform()
    return s
