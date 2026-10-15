"""Toccata in D minor (ending in D major) - a hand-written French-romantic organ toccata (Widor / Vierne / Gigout /
Boellmann tradition), the 'pro' organ reference for the blind listening test. Every chord, figure and pedal note
is written here over the harmonic plan below; the shared organ player (agentsound.organist) performs it.
Build: python -m agentsound build songs/pro-organ-toccata

Form (4/4, q=108-110; see NOTES.md):
  toccata    22 bars  full organ: oscillating 16ths, off-beat LH chords, the pedal theme (Basun 16') in D minor,
                      restated in F major, a descending-fifths sequence, cadence; the church rings
  meditation 12 bars  echo: the RH between the Brostverk positive and the closed swell, LH legato chords in the
                      box, the theme augmented in the soft pedal (F major), a chromatic bass down to the dominant
  crescendo  12 bars  the swell chorus with its reed, the box opening: scale runs over a bass rising D..G#, six bars
                      of dominant pedal (the pedal reeds drawn at bar 9), an A7(b9) fermata, silence
  reprise    12 bars  full organ again: the theme returns, a deceptive cadence, the Neapolitan (Eb), a rushing run
  coda        8 bars  D major: the theme head in major, the minor plagal colour (Gm), a tonic pedal, a run up, the
                      final chord held
"""
from agentsound import *
from agentsound import bands, organist
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'organ'}
METADATA = {'title': 'Toccata in D minor', 'artist': 'AgentSound', 'album': 'Organ References', 'genre': 'Classical',
            'year': 2026}

# ------------------------------------------------------------------------------------------------- harmony
CHORDS = {   # name -> (root pc, intervals); the pitch classes are the voicing's material
    'Dm': (2, (0, 3, 7)), 'D': (2, (0, 4, 7)), 'D7': (2, (0, 4, 7, 10)), 'Eb': (3, (0, 4, 7)),
    'E07': (4, (0, 3, 6, 10)), 'F': (5, (0, 4, 7)), 'F7': (5, (0, 4, 7, 10)), 'Gm': (7, (0, 3, 7)),
    'G': (7, (0, 4, 7)), 'G#o7': (8, (0, 3, 6, 9)), 'A': (9, (0, 4, 7)), 'Am': (9, (0, 3, 7)),
    'A7': (9, (0, 4, 7, 10)), 'Bb': (10, (0, 4, 7)), 'Bbm': (10, (0, 3, 7)), 'Bm': (11, (0, 3, 7)),
    'C': (0, (0, 4, 7)), 'C7': (0, (0, 4, 7, 10)), 'C#o7': (1, (0, 3, 6, 9)),
}
D_MINOR = (2, 4, 5, 7, 9, 10, 0)
D_MAJOR = (2, 4, 6, 7, 9, 11, 1)


def pcs(ch):
    r, iv = CHORDS[ch]
    return [(r + i) % 12 for i in iv]


def scale_for(ch, key):
    """The key's scale with the chord's foreign tones put in: a leading tone (a major third, a dim7's root) replaces
    the scale step below it, a flattened tone the one above."""
    r, iv = CHORDS[ch]
    sc = set(key)
    for i in iv:
        t = (r + i) % 12
        if t in sc:
            continue
        raised = i == 4 or iv == (0, 3, 6, 9)
        sc.discard((t - 1) % 12 if raised else (t + 1) % 12)
        sc.add(t)
    return sorted(sc)


def tones(pc_list, lo, hi):
    return [p for p in range(lo, hi + 1) if p % 12 in pc_list]


def rh_voicing(ch, low, n=4):
    """n consecutive chord tones starting at the chord tone nearest `low`."""
    ts = tones(pcs(ch), 36, 96)
    i = min(range(len(ts)), key=lambda k: abs(ts[k] - low))
    return ts[i:i + n]


def lh_voicing(ch, prev, lo=50, hi=62):
    """Three notes in [lo, hi] holding the third (and the seventh), nearest the previous LH chord."""
    r, iv = CHORDS[ch]
    need = {(r + i) % 12 for i in iv if i in (3, 4, 10)}
    if iv == (0, 3, 6, 9):
        need = {(r + 3) % 12, (r + 9) % 12}
    ts = tones(pcs(ch), lo, hi)
    best = None
    for a in range(len(ts)):
        for b in range(a + 1, len(ts)):
            for c in range(b + 1, len(ts)):
                v = [ts[a], ts[b], ts[c]]
                if not need <= {x % 12 for x in v} or v[2] - v[0] > 9:
                    continue
                cost = sum(abs(x - y) for x, y in zip(v, prev)) if prev else abs(v[0] - 53)
                if best is None or cost < best[0]:
                    best = (cost, v)
    return best[1]


def step(sc, p, k):
    """The scale tone k steps from p (p need not be in the scale)."""
    ts = tones(sc, 24, 108)
    if p in ts:
        return ts[ts.index(p) + k]
    if k > 0:
        return ts[next(j for j, t in enumerate(ts) if t > p) + k - 1]
    return ts[max(j for j, t in enumerate(ts) if t < p) + k + 1]


# ------------------------------------------------------------------------------------------------- figures
def fig_osc(ch, at, beats, low, key):
    """Widor's rocking 16ths: the top and a lower oscillation, the hand rocking down a chord tone every other beat."""
    a, b, c, d = rh_voicing(ch, low)
    out = []
    for k in range(int(beats)):
        cell = (d, b, c, b) if k % 2 == 0 else (c, a, b, a)
        out += [(at + k + j / 4, 0.25, p) for j, p in enumerate(cell)]
    return out


def fig_osc2(ch, at, beats, low, key):
    """Gigout's drumming figure: a low chord tone, the top, the middle, the top (the top as a repeated pedal)."""
    a, b, c, d = rh_voicing(ch, low)
    out = []
    for k in range(int(beats)):
        cell = (a, d, b, d) if k % 2 == 0 else (b, d, c, d)
        out += [(at + k + j / 4, 0.25, p) for j, p in enumerate(cell)]
    return out


def fig_broken(ch, at, beats, low, key):
    """Broken chords: four tones up, the next one, back down - per half bar."""
    ts = tones(pcs(ch), 36, 96)
    i = min(range(len(ts)), key=lambda k: abs(ts[k] - low))
    up = ts[i:i + 5]
    cell = up + up[3:0:-1]                       # a b c d e d c b
    out = []
    for k in range(int(beats * 4)):
        out.append((at + k / 4, 0.25, cell[k % 8]))
    return out


def fig_turn(ch, at, beats, low, key):
    """A turn cell around a chord tone per beat (note, upper neighbour, note, lower neighbour), the tones wandering."""
    v = rh_voicing(ch, low)
    sc = scale_for(ch, key)
    path = (v[2], v[3], v[1], v[2])
    out = []
    for k in range(int(beats)):
        x = path[k % 4]
        cell = (x, step(sc, x, 1), x, step(sc, x, -1))
        out += [(at + k + j / 4, 0.25, p) for j, p in enumerate(cell)]
    return out


def fig_scale(ch, at, beats, low, key, down=False, wave=True, start=None):
    """A scale run in 16ths from a chord tone (up, or down from the top) over the segment - or on from `start` (the
    previous segment's last note: one run through the chord change)."""
    v = rh_voicing(ch, low)
    sc = scale_for(ch, key)
    n = int(beats * 4)
    if start is not None:
        p = step(sc, start, -1 if down else 1)
    else:
        p = v[0] if not down else v[0] + 12
    out = []
    d = -1 if down else 1
    for k in range(n):
        out.append((at + k / 4, 0.25, p))
        if wave and n > 8 and k == n // 2 - 1:
            d = -d                                   # a whole bar: up and back (or down and back)
        if (d > 0 and step(sc, p, d) > 88) or (d < 0 and step(sc, p, d) < 60):
            d = -d
        p = step(sc, p, d)
    return out


FIGS = {'osc': fig_osc, 'osc2': fig_osc2, 'broken': fig_broken, 'turn': fig_turn, 'scale': fig_scale,
        'scaledn': lambda *a: fig_scale(*a, down=True)}


def parse(spec):
    out = []
    for tok in spec.split():
        n, b = tok.split(':')
        out.append((n, float(b)))
    return out


def write_section(start, bars, key, lh='offbeat', lh_prev=None):
    """bars: [(figure, 'Chord:beats ...', rh low target)] -> (rh notes, lh notes, chord segments). Figure 'end':
    the chord struck as a block (RH + LH) for `hold` beats."""
    rh, lhn, segs = [], [], []
    prev = lh_prev
    for i, (fig, spec, low) in enumerate(bars):
        t = start + 4 * i
        for ch, b in parse(spec):
            segs.append((t, b, ch))
            if fig.startswith('end'):
                hold = float(fig[3:] or 2)
                rh += [(t, hold, p) for p in rh_voicing(ch, low, 4)]
                prev = lh_voicing(ch, prev)
                lhn += [(t, hold, p) for p in prev]
                t += b
                continue
            if fig.startswith('scale') and rh and rh[-1][0] >= 4 * i + start - 1:
                rh += fig_scale(ch, t, b, low, key, down=fig == 'scaledn', start=rh[-1][2])
            else:
                rh += FIGS[fig](ch, t, b, low, key)
            prev = lh_voicing(ch, prev)
            if lh == 'offbeat':
                for k in range(int(b)):
                    lhn += [(t + k + 0.5, 0.42, p) for p in prev]
            elif lh == 'held':
                lhn += [(t, b, p) for p in prev]
            t += b
    return rh, lhn, segs, prev


def pedal_line(start, spec):
    """'D3:2 A2:2 -:4 ...' -> [(start, dur, pitch)] (- = a rest)."""
    out, t = [], start
    for tok in spec.split():
        n, b = tok.split(':')
        if n != '-':
            out.append((t, float(b), note_number(n)))
        t += float(b)
    return out


def note_number(name):
    names = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    p = names[name[0]]
    rest = name[1:]
    while rest and rest[0] in '#b':
        p += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    return p + 12 * (int(rest) + 1)


# ------------------------------------------------------------------------------------------------- the score
# (figure, chords, RH low target) per bar
TOCCATA = [
    ('osc', 'Dm:4', 65), ('osc', 'Gm:2 A7:2', 65),
    ('osc', 'Dm:2 A7:2', 65), ('osc', 'Bb:3 C7:1', 65), ('osc', 'Dm:2 F:2', 67), ('osc', 'A:2 A7:2', 68),
    ('osc', 'F:2 Dm:2', 69), ('osc', 'Gm:4', 70), ('osc', 'E07:2 A7:2', 68), ('osc', 'Dm:4', 65),
    ('broken', 'F:2 C7:2', 65), ('broken', 'Dm:3 C7:1', 66), ('broken', 'F:2 Am:2', 68), ('broken', 'C:2 C7:2', 67),
    ('turn', 'Gm:2 C7:2', 67), ('turn', 'F:2 Bb:2', 65), ('turn', 'E07:2 A7:2', 64), ('turn', 'Dm:2 Bb:2', 66),
    ('scale', 'Gm:2 A7:2', 62), ('scaledn', 'Bb:2 E07:2', 70), ('broken', 'Dm:2 A7:2', 65), ('end1.25', 'Dm:4', 65),
]
TOCCATA_PED = ('-:8 D3:2 A2:2 Bb2:3 C3:1 D3:2 F3:2 E3:4 F3:2 D3:2 G3:3 F3:1 E3:2 A2:2 D3:4 '
               'F3:2 C3:2 D3:3 E3:1 F3:2 A3:2 G3:4 G2:2 C3:2 F2:2 Bb2:2 E2:2 A2:2 D3:2 Bb2:2 '
               'G2:2 A2:2 Bb2:2 E2:2 A2:4 D2:1.25')

MEDITATION = [   # (RH manual, figure, chords, low)
    ('positiv', 'turn', 'F:4', 69), ('positiv', 'turn', 'C7:4', 67),
    ('swell_full', 'turn', 'Dm:4', 69), ('swell_full', 'turn', 'Dm:2 C:2', 67),
    ('positiv', 'turn', 'F:4', 72), ('positiv', 'turn', 'Am:4', 72),
    ('swell_full', 'turn', 'C:4', 72), ('swell_full', 'turn', 'C7:4', 70),
    ('swell_full', 'broken', 'F:2 F7:2', 65), ('swell_full', 'broken', 'Bb:2 Bbm:2', 65),
    ('swell_full', 'broken', 'F:2 Gm:2', 64), ('swell_full', 'osc', 'A7:4', 64),
]
MEDITATION_PED = 'F3:4 C3:4 D3:6 E3:2 F3:4 A3:4 G3:8 F3:2 Eb3:2 D3:2 Db3:2 C3:2 Bb2:2 A2:4'

CRESCENDO = [
    ('scale', 'Dm:4', 62), ('scale', 'C:2 A7:2', 64), ('scale', 'F:4', 65), ('scale', 'D7:4', 66),
    ('scaledn', 'Gm:4', 67), ('scale', 'G#o7:4', 68),
    ('osc', 'Dm:2 A7:2', 69), ('osc', 'E07:2 A7:2', 70), ('osc2', 'Dm:2 A7:2', 70), ('osc2', 'Gm:2 A7:2', 72),
    ('broken', 'C#o7:4', 70), ('end2', 'C#o7:4', 73),
]
CRESCENDO_PED_SOFT = 'D2:4 E2:4 F2:4 F#2:4'      # the soft pedal still, then Gedakt 8' drawn
CRESCENDO_PED = 'G2:4 G#2:4 A2:8'
CRESCENDO_PED_FULL = 'A2:14'                 # the pedal reeds drawn on the dominant (bar 9)

REPRISE = [
    ('osc2', 'Dm:2 A7:2', 69), ('osc2', 'Bb:3 C7:1', 69), ('osc2', 'Dm:2 F:2', 70), ('osc2', 'A:2 A7:2', 72),
    ('osc2', 'F:2 Dm:2', 72), ('osc2', 'Gm:4', 74), ('osc', 'E07:2 A7:2', 70), ('osc', 'Bb:2 Gm:2', 70),
    ('broken', 'Eb:2 Dm:2', 67), ('RUN', 'A7:4', 57), ('osc2', 'Dm:2 A7:2', 72), ('broken', 'Gm:2 A7:2', 67),
]
REPRISE_PED = 'D3:2 A2:2 Bb2:3 C3:1 D3:2 F3:2 E3:4 F3:2 D3:2 G3:3 F3:1 E3:2 A2:2 Bb2:2 G2:4 A2:6 D3:2 A2:2 G2:2 A2:2'

CODA = [
    ('osc2', 'D:2 A7:2', 72), ('osc2', 'Bm:3 A:1', 71), ('osc', 'D:4', 72), ('osc', 'G:2 Gm:2', 71),
    ('broken', 'D:2 A7:2', 69), ('broken', 'D:4', 66), ('RUN', 'Gm:2 D:2', 62),
]
CODA_PED = 'D3:2 A2:2 B2:3 C#3:1 D3:2 F#3:2 G3:4 A2:4 D2:8 D2:4'


def runs(bars, start, key):
    """'RUN' bars: one rushing scale up through the bar (its own voice, accel) - returns (notes, lh, segs)."""
    out = []
    for i, (fig, spec, low) in enumerate(bars):
        if fig != 'RUN':
            continue
        t = start + 4 * i
        notes = []
        for ch, b in parse(spec):
            notes += fig_scale(ch, t, b, low if not notes else notes[-1][2] + 1, key, wave=False)
            t += b
        out.append(notes)
    return out


def build() -> Song:
    s = Song('Toccata in D minor', tempo=108, key='D minor', seed=7, tail=8)
    toc = s.section('toccata', 22)
    med = s.section('meditation', 12)
    cre = s.section('crescendo', 12)
    rep = s.section('reprise', 12)
    coda = s.section('coda', 8)

    # ---- time: the toccata drives, the meditation breathes a little slower, the crescendo presses on into the
    # dominant, the fermata, the reprise a touch faster, the broad ending
    s.ritardando((toc.bar(20), toc.bar(21, 2)), to=0.8)
    s.set_tempo(med.start, 100)
    s.ritardando((med.bar(11), med.end), to=0.94, a_tempo=False)
    s.set_tempo(cre.start, 100)
    s.tempo_ramp(cre.bar(0), cre.bar(8), 110, curve='smooth')
    s.ritardando((cre.bar(10), cre.bar(11)), to=0.86, a_tempo=False)
    s.fermata(cre.bar(11), hold=2.0)
    s.set_tempo(rep.start, 110)
    s.ritardando((rep.bar(9, 2), rep.bar(10)), to=0.9)
    s.ritardando((coda.bar(5), coda.bar(7)), to=0.72, a_tempo=False)
    s.fermata(coda.bar(7), hold=3.0)

    b = bands.church_organ(s, registers=('positiv', 'swell_full', 'pedal_soft'), without=('soft', 'principal'))
    b['positiv'].gain_db += 2.0               # the echo's forte manual
    b['pedal_soft'].gain_db -= 3.0
    # (swell_full: the preset's +3 dB since these references now carries the open box near the plenum)
    V = organist.Voice
    voices = []

    # toccata: full organ + full pedal
    rh, lh, _, prev = write_section(toc.start, TOCCATA, D_MINOR)
    voices += [V(rh, 'full', 'toccata RH', kind='figure'), V(lh, 'full', 'toccata LH', kind='chords',
                                                              touch='detache'),
               V(pedal_line(toc.start, TOCCATA_PED), 'pedal_full', 'toccata pedal', touch='legato')]

    # meditation: RH echo between the positive and the closed swell, LH legato chords in the box, soft pedal
    rh_by = {}
    lh_all = []
    for i, (man, fig, spec, low) in enumerate(MEDITATION):
        r, l, _, prev = write_section(med.bar(i), [(fig, spec, low)], D_MINOR, lh='held', lh_prev=prev)
        rh_by.setdefault(man, []).extend(r)
        lh_all += l
    for man, ns in rh_by.items():
        voices.append(V(ns, man, f'meditation RH {man}', kind='figure'))
    voices += [V(lh_all, 'swell_full', 'meditation LH', kind='chords', touch='legato'),
               V(pedal_line(med.start, MEDITATION_PED), 'pedal_soft', 'meditation pedal', touch='legato')]

    # crescendo: everything in the swell box, the box opening; the pedal reeds on the dominant pedal point
    rh, lh, _, prev = write_section(cre.start, CRESCENDO, D_MINOR, lh_prev=prev)
    gm = cre.bar(10)                          # the last two bars: the hands go to the Grand-Orgue (the plenum)
    voices += [V([n for n in rh if n[0] < gm], 'swell_full', 'crescendo RH', kind='figure'),
               V([n for n in lh if n[0] < gm], 'swell_full', 'crescendo LH', kind='chords', touch='detache'),
               V([n for n in rh if n[0] >= gm], 'full', 'climax RH', kind='figure'),
               V([n for n in lh if n[0] >= gm], 'full', 'climax LH', kind='chords', touch='detache'),
               V(pedal_line(cre.start, CRESCENDO_PED_SOFT), 'pedal_soft', 'crescendo pedal i', touch='legato'),
               V(pedal_line(cre.bar(4), CRESCENDO_PED), 'pedal', 'crescendo pedal ii', touch='legato'),
               V(pedal_line(cre.bar(8), CRESCENDO_PED_FULL), 'pedal_full', 'dominant pedal', touch='legato')]

    # reprise + coda: full organ; the runs rush into their goal
    for sec, bars, ped, key in ((rep, REPRISE, REPRISE_PED, D_MINOR), (coda, CODA, CODA_PED, D_MAJOR)):
        plain = [x if x[0] != 'RUN' else ('osc', x[1], x[2]) for x in bars]
        rh, lh, _, prev = write_section(sec.start, plain, key, lh_prev=prev)
        run_bars = {sec.start + 4 * i for i, x in enumerate(bars) if x[0] == 'RUN'}
        rh = [n for n in rh if not any(t <= n[0] < t + 4 for t in run_bars)]
        voices.append(V(rh, 'full', f'{sec.name} RH', kind='figure'))
        voices.append(V(lh, 'full', f'{sec.name} LH', kind='chords', touch='detache'))
        voices.append(V(pedal_line(sec.start, ped), 'pedal_full', f'{sec.name} pedal', touch='legato'))
        for j, run in enumerate(runs(bars, sec.start, key)):
            voices.append(V(run, 'full', f'{sec.name} run {j}', kind='figure', accel=(1.15, 0.85)))

    # the final chord: the full plenum, both hands, held (fermata)
    fin = coda.bar(7)
    voices.append(V([(fin, 4.0, p) for p in (57, 62, 66, 69, 74, 78, 81, 86)], 'full', 'final RH', kind='chords',
                    touch='legato'))
    voices.append(V([(fin, 4.0, p) for p in (50, 54)], 'full', 'final LH', kind='chords', touch='legato'))

    phrases = [toc.bar(2), toc.bar(10), toc.bar(18), med.start, med.bar(4), med.bar(8), cre.start, cre.bar(6),
               rep.start, rep.bar(8), coda.start, coda.bar(7)]
    organist.perform(s, b, voices, phrases=phrases, seed=5)

    # the swell box: nearly closed for the echo, opening through the crescendo
    orch.swell(b, [(0, 0.15), (med.bar(8), 0.15), (cre.start, 0.35, 'smooth'), (cre.bar(9), 1.0, 'smooth')],
               roles=['swell_full'])
    orch.ring(b, toc.bar(21), length=2.0, back=med.start)
    orch.ring(b, cre.bar(11), length=2.0, back=rep.start)
    orch.ring(b, coda.bar(7), length=4.0)
    return s
