"""Toccata Tenebrae - an original organ toccata in E minor (ending in E major), AgentSound's first pipe-organ piece.
Build: python -m agentsound build songs/toccata-tenebrae

The North-German / French-Romantic toccata gesture with original material: no note is Bach's (BWV 565) or Widor's.
The whole piece grows from one 7-note head motif: E (lower mordent) - B - C D E F# - G (a mordent, a falling fourth,
a scale climbing a sixth to the minor third) - stated in octaves in the exordium, turned into the right hand's
figuration cell (a note, its chromatic lower neighbour, the note, the chord tone below), walked by the pedal in the
solo, sung by a flute in augmentation in the quiet episode, played x4 augmented in the pedal under the second
toccata (A minor answer) and harmonised in full-organ chords in the Grave.

  exordium   0:00  7  q=66 free   the motif in octaves (fermata, silence), a rushing run into a D#dim7 over the E
                                   pedal on the full organ (fermata), a rising flourish, a trill, bariolage over a B
                                   pedal, iv6 - V (trill on D#) - i with fermata, the church rings
  toccata    0:31 16  q=100       16th figuration (turn cells, scales, bariolage) over pedal points E and G, LH
                                   chords, circle of fifths, a rushing scale into ...
  recitative 1:10  4  q=60        three diminished-7th chords rising C#o7 - Do7 - D#o7 on the full organ, each a
                                   fermata with a flourish echoing on the principal between, a deceptive cadence (C)
  pedal_solo 1:33  6  q=92        the motif walked by the feet (Basun 16'), the reed taken off for the last bars, rit.
  flutes     1:50 12  q=63        G major: the motif augmented on a swell flute solo (Rorflojt 8' + Halflojt 4', the
                                   box shaping every phrase) over a Brostverk Gedakt 8' and a lone Subbas 16'
  toccata_ii 2:39 20  q=104       the motif x4 in the pedal (E minor, then A minor) under the figuration, LH repeated
                                   chords on the swell chorus + Skalmeja while the box opens; full organ from bar 9; a
                                   dominant pedal with bariolage and an A#o7; a chromatic climb (C - C# - D#) into the
                                   D#o7 over E: fermata, general pause
  finale     3:27  7  Grave q=54  the motif harmonised in full-organ chords, a rushing run, the Neapolitan (F), the
                                   cadential 6/4, V with a trill, E MAJOR, the minor plagal Am/E, the last E major
                                   chord held ~10 s, the church rings to 4:09

Registration (Burea Church organ, Lars Palo; the Pitea organ was the A/B try - TOCCATA_ORGAN=pitea): Huvudverk
principal chorus 8' 4' 2' (exordium, toccata, the recitative's echoes, toccata_ii bars 1-8) -> full organ (+ Mixtur
V, Trumpet 8') for the dim7 chords, toccata_ii from bar 9 and the end -> the quiet episode: Svallverk Rorflojt 8' +
Halflojt 4' solo, Brostverk Gedakt 8' accompaniment, Subbas 16' alone -> Svallverk Rorflojt 8' + Salicional 8' +
Principal 4' + Skalmeja 8' opening under toccata_ii -> full plenum + pedal with Basun 16' for the end. Pedal on its
own tracks: Subbas 16' + Gedakt 8' (toccata), Subbas 16' alone (episode), Subbas 16' + Principal 8' + Oktava 4' +
Basun 16' (dim7 chords, toccata_ii, finale; the solo with its upper ranks in stereo). The swell box
('instrument.expression') only on the enclosed Svallverk tracks: the episode's phrase swells, toccata_ii's crescendo.

Organist's hands (helpers in this file, see Organist): detache 16ths (gaps of ~20 % of the slot, the metric strong
16ths held a little longer), legato with 20 ms overlaps (a repeated key released 45 ms early), chords lifted
~70 ms before the next, hand-level timing (+-4-7 ms), chord notes spread 0-10 ms, mordents / trills / turns as played
notes, runs that accelerate into their goal, agogic breaths before the big chords, ritardandi and fermatas in the
tempo map, the church blooming into every silence (orch.ring with back=).

Measured (report, 'classical'): -19.9 LUFS-I, LRA 10.7, TP -4.4 dBTP, 0 clicks, 0 silent notes; sections exordium
-18.8, toccata -22.1, recitative -16.2, pedal_solo -24.4, flutes -25.8, toccata_ii -19.8, finale -16.8 LUFS; space
lush in every section, lows correlation 0.98. 1 warning: the plenum's left hand and the full pedal share 60-250 Hz in
the recitative / finale (an organ tutti). flat_dynamics: the swell solo passes (7.4 dB, the box); the pedal tracks'
'info' lines are inapplicable - a pipe has no velocity, the pedal division no swell box.

CREDITS: Burea Church organ sample set by Lars Palo (familjenpalo.se), CC-BY-SA 2.5; church: Voxengo IM Reverbs
(St Nicolaes Church).
"""
import os
import random
from collections import defaultdict

from agentsound import *
from agentsound import bands, mastering
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'classical'}
METADATA = {'title': 'Toccata Tenebrae', 'artist': 'AgentSound', 'album': 'Sacred', 'genre': 'Classical',
            'comment': 'Toccata in E minor for pipe organ (Burea Church organ, Lars Palo)'}
COVER = {'style': 'classical', 'palette': 'noir', 'title': 'TOCCATA TENEBRAE', 'subtitle': 'for organ in E minor'}

# mix (MIX.md): the plenum's mixture carried 91 % of a +2.9 dB 2-5 kHz excess (harsh / glassy) and masked the swell
# reeds at 1.4 kHz in toccata_ii - two dips on 'full' only; levels are the registrations (no rides)
MIX = {'eq': {'full': [{'freq': 3300, 'gain': -2.0, 'q': 1.0}, {'freq': 1400, 'gain': -1.5, 'q': 1.0}]}}

ORGAN = os.environ.get('TOCCATA_ORGAN', 'burea')       # 'burea' (chosen: wider church image, even sub) | 'pitea'
PACK = {'pitea': 'samples/lars-palo-pitea-mhs', 'burea': 'samples/lars-palo-burea-church'}[ORGAN]
# the registrations the preset does not have: the episode's solo flute on the ENCLOSED swell division (its box is the
# solo's dynamics), its accompaniment on a soft unenclosed stop, the swell chorus with its reed for toccata_ii, the
# Subbas 16' alone
EXTRA = {
    'pitea': {'solo': dict(stops=['Fl.Harm. 8', 'Fl.Oct. 4'], manual='Svallverk'),
              'accomp': dict(stops=["Fl.d'amore 8"], manual='Positiv'),
              'swell': dict(stops=['Fl.Harm. 8', 'Gamba 8', 'Oboe 8', 'Tr.Harm. 8', 'Fl.Oct. 4'], manual='Svallverk'),
              'pedal_soft': dict(stops=['Subbas 16'], manual='pedal', stereo='left'),
              'pedal_reed': dict(stops=['Subbas 16', 'Oktava 8', 'Oktava 4', 'Basun 16'], manual='pedal',
                                 stereo={'Subbas 16': 'left'})},
    'burea': {'solo': dict(stops=['Rorflojt 8', 'Halflojt 4'], manual='Svallverk'),
              'accomp': dict(stops=['Gedakt 8'], manual='Brostverk', stereo='flip'),
              'swell': dict(stops=['Rorflojt 8', 'Salicional 8', 'Principal 4', 'Skalmeja 8'], manual='Svallverk',
                            stereo='flip'),
              'pedal_soft': dict(stops=['Subbas 16'], manual='pedal', stereo='left'),
              'pedal_reed': dict(stops=['Subbas 16', 'Principal 8', 'Oktava 4', 'Basun 16'], manual='pedal',
                                 stereo={'Subbas 16': 'left'})},
}[ORGAN]

# ------------------------------------------------------------------------------------------------ pitches
_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def m(name) -> int:
    if isinstance(name, int):
        return name
    pc, i = _PC[name[0]], 1
    while name[i] in '#b':
        pc += 1 if name[i] == '#' else -1
        i += 1
    return 12 * (int(name[i:]) + 1) + pc


def pcs(*names) -> list:
    return [_PC[n[0]] + n[1:].count('#') - n[1:].count('b') for n in names]


E_HARM = set(pcs('E', 'F#', 'G', 'A', 'B', 'C', 'D#'))
E_NAT = set(pcs('E', 'F#', 'G', 'A', 'B', 'C', 'D'))
G_MAJ = E_NAT
E_MAJ = set(pcs('E', 'F#', 'G#', 'A', 'B', 'C#', 'D#'))

CH = {   # chord pitch classes
    'Em': pcs('E', 'G', 'B'), 'E': pcs('E', 'G#', 'B'), 'E7': pcs('E', 'G#', 'B', 'D'), 'Am': pcs('A', 'C', 'E'),
    'Am7': pcs('A', 'C', 'E', 'G'), 'B7': pcs('B', 'D#', 'F#', 'A'), 'B': pcs('B', 'D#', 'F#'),
    'C': pcs('C', 'E', 'G'), 'G': pcs('G', 'B', 'D'), 'D': pcs('D', 'F#', 'A'), 'D7': pcs('D', 'F#', 'A', 'C'),
    'Bm': pcs('B', 'D', 'F#'), 'F': pcs('F', 'A', 'C'), 'F#o7': pcs('F#', 'A', 'C', 'E'),
    'D#o7': pcs('D#', 'F#', 'A', 'C'), 'C#o7': pcs('C#', 'E', 'G', 'A#'), 'Do7': pcs('D', 'F', 'G#', 'B'),
    'A#o7': pcs('A#', 'C#', 'E', 'G'), 'A': pcs('A', 'C#', 'E'),
}


def step(p: int, n: int, scale) -> int:
    """n diatonic steps from p inside `scale` (pitch classes)."""
    d = 1 if n > 0 else -1
    for _ in range(abs(n)):
        p += d
        while p % 12 not in scale:
            p += d
    return p


def ladder(chord, lo=48, hi=96) -> list:
    return [p for p in range(lo, hi + 1) if p % 12 in chord]


def at_or_above(lad, p) -> int:
    return next(i for i, q in enumerate(lad) if q >= p)


def voicing(prev, chord, lo, hi, n=3) -> list:
    """The n-note voicing (distinct pitch classes, root and third kept, within a tenth) closest to `prev`."""
    from itertools import combinations
    need = {chord[0], chord[1]}
    best, cost = None, 1e9
    for comb in combinations(ladder(chord, lo, hi), n):
        got = {p % 12 for p in comb}
        if not need <= got or len(got) < min(n, len(chord)) or comb[-1] - comb[0] > 16:
            continue
        c = sum(abs(a - b) for a, b in zip(sorted(prev), comb))
        if c < cost:
            best, cost = list(comb), c
    return best


# ------------------------------------------------------------------------------------------------ the organist
class Organist:
    """Collects the notes of every track, plays ornaments, articulation and hand timing like an organist, and
    resolves the one-pipe-per-key rule (a key struck again ends the earlier note) before placing the notes.
    Events: (pitches | None, beats, ornament) - ornament '' | 'm' (lower mordent) | 'p' (upper mordent) |
    't' (trill from the upper note, turned at the end) | 'u' (turn) ; None = rest."""

    def __init__(self, song, seed=7):
        self.s = song
        self.rng = random.Random(seed)
        self.notes = defaultdict(list)          # track -> [start, dur, pitch, vel]

    # ---- parsing: 'mE5+E4:1.5 B4+B3:.5 r:1 tA#5:1.5'
    @staticmethod
    def parse(spec: str) -> list:
        out = []
        for tok in spec.split():
            head, dur = tok.rsplit(':', 1)
            d = float(dur)
            if head == 'r':
                out.append((None, d, ''))
                continue
            orn = ''
            if head[0] in 'mptu':
                orn, head = head[0], head[1:]
            out.append(([m(x) for x in head.split('+')], d, orn))
        return out

    def ornament(self, p, d, orn, scale, bpm):
        """Sub-notes (pitch, beats) of one ornamented note."""
        b = 60.0 / bpm
        fast = min(d / 4.0, 0.068 / b)          # ~68 ms ornament notes
        up, lo = step(p, 1, scale), step(p, -1, scale)
        if orn in ('m', 'p'):
            nb = lo if orn == 'm' else up
            return [(p, fast), (nb, fast), (p, d - 2 * fast)]
        if orn == 'u':
            return [(up, fast), (p, fast), (lo, fast), (p, d - 3 * fast)]
        if orn == 't':
            k = max(4, int(d * b / 0.085))
            k -= k % 2
            each = d / (k + 2)
            seq = [(up if i % 2 == 0 else p, each) for i in range(k)] + [(lo, each), (p, each)]
            return seq
        return [(p, d)]

    def play(self, track, t0, events, bpm, art='legato', sigma=5.0, spread=6.0, scale=E_HARM, vel=90, accel=None):
        """Place events from beat t0. art: 'legato' | 'detache' | 'stacc' | 'chord'. accel: (from, to) note-length
        factors across the events (a run that rushes into its goal: (1.25, 0.8))."""
        if isinstance(events, str):
            events = self.parse(events)
        ms = lambda x: x / 1000.0 * bpm / 60.0      # noqa: E731
        t = float(t0)
        total = sum(d for _, d, _ in events)
        if accel:
            n = len(events)
            f = [accel[0] + (accel[1] - accel[0]) * i / max(1, n - 1) for i in range(n)]
            k = total / sum(d * fi for (_, d, _), fi in zip(events, f))
            events = [(p, d * fi * k, o) for (p, d, o), fi in zip(events, f)]
        for pitches, d, orn in events:
            if pitches is None:
                t += d
                continue
            hand = self.rng.gauss(0.0, sigma)
            on_beat = abs(t - round(t)) < 1e-6
            for j, p in enumerate(sorted(pitches, reverse=True)):
                sub = self.ornament(p, d, orn, scale, bpm) if orn and (len(pitches) <= 2 or j == 0) else [(p, d)]
                tt = t
                for q, sd in sub:
                    off = ms(hand + (self.rng.uniform(0, spread) if len(pitches) > 2 else 0.0))
                    if art == 'legato':
                        dur = sd + ms(20)
                    elif art == 'detache':
                        gap = min(0.22 * sd, ms(45)) * (0.5 if on_beat and tt == t else 1.0)
                        dur = sd - gap
                    elif art == 'stacc':
                        dur = sd * 0.55
                    else:                                   # chord: lifted before the next one
                        dur = max(sd * 0.5, sd - ms(70))
                    v = vel + (8 if on_beat and tt == t else 0) + self.rng.randint(-4, 4)
                    self.notes[track].append([max(0.0, tt + off), max(ms(25), dur), q, max(1, min(127, v))])
                    tt += sd
            t += d
        return t

    def finish(self, tracks: dict):
        """One pipe per key: a key struck again while sounding releases the earlier note 45 ms before (at ~80 BPM)."""
        for tid, ns in self.notes.items():
            by = defaultdict(list)
            for n in ns:
                by[n[2]].append(n)
            for lst in by.values():
                lst.sort(key=lambda n: n[0])
                for a, b in zip(lst, lst[1:]):
                    if a[0] + a[1] > b[0] - 0.05:
                        a[1] = max(0.04, b[0] - 0.05 - a[0])
            tracks[tid].play(Clip([tuple(n) for n in ns]), 0)


# ------------------------------------------------------------------------------------------------ figurations
def turn_cells(chord, start, offs, scale=None):
    """The toccata cell per beat: T, its chromatic lower neighbour, T, the chord tone below (4 16ths); T walks the
    chord ladder by `offs` from `start`."""
    lad = ladder(chord)
    i0 = at_or_above(lad, m(start))
    ev = []
    for o in offs:
        T = lad[i0 + o]
        ev += [([T], .25, ''), ([T - 1], .25, ''), ([T], .25, ''), ([lad[i0 + o - 1]], .25, '')]
    return ev


def turn_cells_down(chord, start, offs, scale):
    """The inverted cell: T, its diatonic upper neighbour, T, the chord tone above."""
    lad = ladder(chord)
    i0 = at_or_above(lad, m(start))
    ev = []
    for o in offs:
        T = lad[i0 + o]
        ev += [([T], .25, ''), ([step(T, 1, scale)], .25, ''), ([T], .25, ''), ([lad[i0 + o + 1]], .25, '')]
    return ev


def scale_run(start, n, scale, up=True, d=.25):
    p = m(start)
    out = []
    for _ in range(n):
        out.append(([p], d, ''))
        p = step(p, 1 if up else -1, scale)
    return out


def bariolage(chord, pivot, start, offs, scale):
    """Per beat: T, pivot, the scale step below T, pivot - a violinistic figure over a held common tone."""
    lad = ladder(chord)
    i0 = at_or_above(lad, m(start))
    pv = m(pivot)
    ev = []
    for o in offs:
        T = lad[i0 + o]
        ev += [([T], .25, ''), ([pv], .25, ''), ([step(T, -1, scale)], .25, ''), ([pv], .25, '')]
    return ev


def chord_ev(names, d, orn=''):
    return ([m(x) for x in names.split()], d, orn)


# ------------------------------------------------------------------------------------------------ the piece
def build() -> Song:
    s = Song('Toccata Tenebrae', tempo=66, key='E minor', seed=11, tail=10)
    ex = s.section('exordium', 7)
    toc = s.section('toccata', 16)
    rec = s.section('recitative', 4)
    ped = s.section('pedal_solo', 6)
    flu = s.section('flutes', 12)
    toc2 = s.section('toccata_ii', 20)
    fin = s.section('finale', 7)

    # ---- tempo map: free exordium, toccata tempi, rits, fermatas
    E0, T0, R0, P0, F0, U0, Z0 = (sec.start for sec in (ex, toc, rec, ped, flu, toc2, fin))
    s.rubato((E0 + 8, E0 + 23), depth=0.05, phrase='lean')
    s.set_tempo(T0, 100)
    s.rubato((T0, T0 + 32), depth=0.015, phrase='arch')
    s.ritardando((toc.bar(15), toc.end), to=0.8)
    s.set_tempo(R0, 60)
    s.set_tempo(P0, 92)
    s.ritardando((ped.bar(4), ped.end), to=0.78)
    s.set_tempo(F0, 63)
    s.rubato((F0, F0 + 32), depth=0.04, phrase='breath')
    s.ritardando((flu.bar(10), flu.end), to=0.8)
    s.set_tempo(U0, 104)
    s.ritardando((toc2.bar(17), toc2.bar(19)), to=0.88, a_tempo=False)
    s.set_tempo(Z0, 54)
    s.ritardando((fin.bar(2) + 2, fin.bar(3)), to=0.85)
    s.ritardando((fin.bar(4) + 2, fin.bar(5)), to=0.85, a_tempo=False)
    for at, hold in ((E0 + 3, 1.5), (E0 + 7, 2), (E0 + 15.5, 0.75), (E0 + 23, 2),
                     (R0 + 0, 1.5), (R0 + 4, 1.5), (R0 + 8, 2), (R0 + 13.5, 2), (ped.bar(5) + 2, 1.5),
                     (flu.bar(11) + 2, 1.5), (toc2.bar(19), 3), (Z0 + 4, 1), (Z0 + 8, 1.5), (Z0 + 20, 1.5)):
        s.fermata(at, hold=hold)

    # ---- the organ
    o = bands.church_organ(s, organ=ORGAN, without=('soft',))
    hall = o.buses['hall']
    T = {r: o[r] for r in o.roles}
    T['solo'] = s.track('solo', inst.organ(PACK, lazy=True, **EXTRA['solo']), gain_db=2.0, sends={hall: -6})
    T['accomp'] = s.track('accomp', inst.organ(PACK, lazy=True, **EXTRA['accomp']), gain_db=-5.0, sends={hall: -6},
                          fx=[fx.eq({'peak1.freq': 400, 'peak1.gain': -2.0, 'peak1.q': 0.8})])
    T['swell'] = s.track('swell', inst.organ(PACK, lazy=True, **EXTRA['swell']), gain_db=-7.0, sends={hall: -6},
                         fx=[fx.eq({'peak1.freq': 330, 'peak1.gain': -2.5, 'peak1.q': 0.8, 'hp.freq': 80,
                                    'peak2.freq': 1500, 'peak2.gain': -2.0, 'peak2.q': 0.9})])
    T['pedal_soft'] = s.track('pedal_soft', inst.organ(PACK, lazy=True, **EXTRA['pedal_soft']), gain_db=-6.0,
                              sends={hall: -12})
    # the pedal solo: the full pedal (+ Basun 16') with its upper ranks as recorded (spaced pair) and only the
    # Subbas 16' on one microphone - a solo line in the church instead of a mono point
    T['pedal_reed'] = s.track('pedal_reed', inst.organ(PACK, lazy=True, **EXTRA['pedal_reed']), gain_db=-8.0,
                              sends={hall: -4}, fx=[fx.eq({'hp.freq': 20, 'low.freq': 70, 'low.gain': -3.0,
                                                           'peak1.freq': 280, 'peak1.gain': -2.0, 'peak1.q': 0.9})])
    # the church: the manuals sit 3 dB wetter than the preset's seat (the 16th figuration still reads), the pedal's
    # 32-Hz-ish 16' fundamentals a little tamed (sub was +8.7 dB over the classical balance), the principal chorus
    # +2 dB (a single 16th line + LH chords reads under the preset's chord calibration)
    for r in ('principal', 'full'):
        T[r].send(hall, -6.0)
        o.info['seating'][r]['hall_send'] = -6.0
    for r in ('pedal', 'pedal_full', 'pedal_soft'):
        T[r].add_fx(fx.eq({'low.freq': 70, 'low.gain': -3.0}))
    T['principal'].gain_db += 3.5
    org = Organist(s)
    P = org.play

    # =============================================================== exordium (q=66, free)
    P('principal', E0, 'mE5+E4:1.5 B4+B3:.5 C5+C4:.25 D5+D4:.25 E5+E4:.25 F#5+F#4:.25 G5+G4:1', 66, sigma=6)
    run = [([p], .125, '') for p in [m(x) for x in 'F#5 E5 D#5 C5 B4 A4 G4 F#4 E4 D#4 C4 B3 A3 G3 F#3 E3'.split()]]
    P('principal', E0 + 5, run, 66, art='detache', sigma=2, accel=(1.35, 0.75))
    P('full', E0 + 7, [chord_ev('F#3 A3 C4 D#4 F#4 A4 C5', 2), (None, .5, ''), chord_ev('E3 G3 B3 E4 G4 B4', 1.5)],
      66, art='chord', spread=8)
    P('pedal_full', E0 + 7, 'E2:2 r:.5 E2:1.5', 66, art='chord')
    up = [([m(x)], .25, '') for x in 'E3 G3 B3 E4 G4 B4 E5 G5'.split()]
    P('principal', E0 + 12, up, 66, art='legato', sigma=3, accel=(1.3, 0.8))
    P('principal', E0 + 14, 'tA#5:1.5 B5:.5', 66, scale=set(pcs('B', 'C#', 'D#', 'E', 'F#', 'G', 'A#')))
    P('principal', E0 + 14, 'C#4+E4+G4:1.5 B3+D#4+F#4:.5', 66, art='legato', spread=5)
    bar = [([m(x)], .25, '') for x in 'E6 B4 D#6 B4 C6 B4 B5 B4 A5 B4 G5 B4 F#5 B4 D#5 B4'.split()]
    P('principal', E0 + 16, bar, 66, art='detache', sigma=4)
    P('pedal', E0 + 16, 'B2:4', 66)
    P('full', E0 + 20, [chord_ev('C3 E3 A3 C4 E4 A4', 1), chord_ev('B3 D#4 F#4 B4', 2)], 66, art='chord', spread=8)
    P('full', E0 + 21, 'tD#5:1.75 E5:.25', 66, scale=E_HARM)
    P('full', E0 + 23, [(None, .1, ''), chord_ev('E3 G3 B3 E4 G4 B4 E5', 2.9)], 66, art='chord', spread=8)
    P('pedal_full', E0 + 20, 'C3:1 B2:2 r:.1 E2:2.9', 66, art='legato')

    # =============================================================== toccata (q=100)
    rh = []
    rh += turn_cells(CH['Em'], 'B4', [0, 1, 2, 1])
    rh += turn_cells(CH['Am'], 'C5', [0, 1, 2, 1])
    rh += turn_cells(CH['D#o7'], 'D#5', [0, 1, 2, 1])
    rh += turn_cells(CH['Em'], 'E5', [0, 1, 2, 3])
    rh += scale_run('E5', 8, E_NAT) + scale_run('E6', 8, E_NAT, up=False)          # C
    rh += scale_run('A4', 8, E_NAT) + scale_run('A5', 8, E_NAT, up=False)          # Am
    rh += scale_run('F#4', 8, E_NAT) + scale_run('F#5', 8, E_NAT, up=False)        # F#o7
    rh += scale_run('B4', 8, E_HARM) + scale_run('B5', 8, E_HARM, up=False)        # B7
    rh += turn_cells(CH['G'], 'B4', [0, 1, 2, 1])
    rh += turn_cells(CH['C'], 'C5', [0, 1, 2, 1])
    rh += turn_cells(CH['D7'], 'C5', [0, 1, 2, 3])
    rh += turn_cells(CH['G'], 'D5', [0, 1, 2, 1])
    rh += bariolage(CH['Am'], 'E5', 'A5', [0, 1, 2, 1], E_NAT)
    rh += bariolage(CH['F#o7'], 'E5', 'F#5', [0, 1, 2, 1], E_NAT)
    rh += bariolage(CH['B7'], 'F#5', 'A5', [0, 1, 2, 1], E_HARM)
    rh += [([m(x)], .25, '') for x in 'E6 D#6 C6 B5 A5 G5 F#5 E5 D#5 C5 B4 A4 G4 F#4 E4 D#4'.split()]
    P('principal', T0, rh, 100, art='detache', sigma=4)
    lh_ch = ['Em', 'Am', 'D#o7', 'Em', 'C', 'Am', 'F#o7', 'B7', 'G', 'C', 'D7', 'G', 'Am', 'F#o7', 'B7', 'Em']
    prev = [m('E3'), m('G3'), m('B3')]
    for i, c in enumerate(lh_ch):
        prev = voicing(prev, CH[c], m('D3'), m('D4'))
        b0 = T0 + 4 * i
        if i == 15:
            P('principal', b0, [(prev, 1, '')], 100, art='chord', spread=5)
        elif i < 8:
            P('principal', b0 + 1, [(prev, .5, ''), (None, 1.5, ''), (prev, .5, '')], 100, art='chord', spread=5)
        else:
            P('principal', b0 + .5, [(prev, .5, ''), (None, .5, '')] * 3 + [(prev, .5, '')], 100, art='stacc',
              spread=4)
    P('pedal', T0, 'E2:16 C3:2 E3:2 A2:2 C3:2 F#2:2 A2:2 B2:4 G2:16 A2:2 C3:2 F#2:2 A2:2 B2:2 B2:2 E2:4', 100)

    # =============================================================== recitative (q=60): three dim7 chords
    P('full', R0, [chord_ev('G3 A#3 C#4 E4 G4 A#4 C#5', 2)], 60, art='chord', spread=9)
    P('pedal_full', R0, 'C#3:2', 60)
    fl1 = [([m(x)], .1875, '') for x in 'C#4 E4 G4 A#4 C#5 E5 G5 A#5'.split()]
    P('principal', R0 + 2.5, fl1, 60, art='legato', sigma=2, accel=(1.3, 0.8))
    P('full', R0 + 4, [chord_ev('F3 G#3 B3 D4 F4 G#4 B4 D5', 2)], 60, art='chord', spread=9)
    P('pedal_full', R0 + 4, 'D3:2', 60)
    fl2 = [([m(x)], .1875, '') for x in 'B5 G#5 F5 D5 B4 G#4 F4 D4'.split()]
    P('principal', R0 + 6.5, fl2, 60, art='legato', sigma=2, accel=(1.3, 0.8))
    P('full', R0 + 8, [chord_ev('F#3 A3 C4 D#4 F#4 A4 C5 D#5', 2)], 60, art='chord', spread=9)
    P('pedal_full', R0 + 8, 'D#3:2', 60)
    P('full', R0 + 11, [chord_ev('G3 B3 E4 G4 B4 E5', 1), chord_ev('F#3 A3 D#4 F#4 B4 D#5', 1.5),
                        (None, .15, ''), chord_ev('G3 C4 E4 G4 C5 E5', 1.85)], 60, art='chord', spread=8)
    P('pedal_full', R0 + 11, 'B2:2.5 r:.15 C3:1.85', 60, art='legato')

    # =============================================================== pedal solo (q=92)
    P('pedal_reed', P0, 'A2:.75 E2:.25 F2:.25 G2:.25 A2:.25 B2:.25 C3:1 B2:.5 A2:.5 '
                        'G#2:.25 A2:.25 B2:.25 C3:.25 D3:.25 E3:.25 F3:.25 E3:.25 D3:.5 C3:.5 B2:.5 E2:.5 '
                        'E3:.75 B2:.25 C3:.25 D3:.25 E3:.25 F#3:.25 G3:1 A3:.5 B3:.5 '
                        'C4:.25 B3:.25 A3:.25 G3:.25 F#3:.25 G3:.25 A3:.25 F#3:.25 D#3:.5 E3:.5 B2:1',
      92, art='detache', sigma=6)
    P('pedal', ped.bar(4), 'E3:.5 D3:.5 C3:.5 B2:.5 A2:.5 G2:.5 F#2:.5 E2:.5 A2:1 B2:1 D3:2', 92, art='legato',
      sigma=6)

    # =============================================================== flute episode (q=63, G major)
    P('solo', F0, 'uG4:1.5 D4:.5 E4:.5 F#4:.5 G4:.5 A4:.5 B4:2.5 A4:.5 G4:.5 F#4:.5 '
                  'E4:1 A4:1.5 G4:.5 F#4:.5 E4:.5 D4:.5 E4:.5 F#4:.5 G4:.5 pA4:1.5 r:.5 '
                  'uB4:1.5 F#4:.5 G4:.5 A4:.5 B4:.5 C5:.5 D5:2.5 C5:.5 B4:.5 A4:.5 '
                  'E5:1 C5:1 B4:.5 A4:.5 G4:.5 F#4:.5 G4:.5 A4:.5 B4:.5 C5:.5 pB4:1 A4:1 '
                  'G4:2 F#4:.5 E4:.5 D#4:.5 E4:.5 C5:2 B4:.5 A4:.5 G4:.5 E4:.5 '
                  'E4:.5 A4:.5 C5:1 B4:1 A4:1 tF#4:2 D#4:1.5 r:.5', 63, scale=G_MAJ, sigma=7)
    for n in org.notes['solo']:            # the flute sings an octave above the accompaniment (written an octave low)
        n[2] += 12
    fl_ch = [('G', 4), ('Em', 4), ('Am7', 4), ('D', 4), ('Bm', 4), ('G', 4), ('C', 4), ('Am', 2), ('D7', 2),
             ('Em', 4), ('C', 4), ('Am', 2), ('F#o7', 2), ('B7', 4)]
    prev, t = [m('B3'), m('D4'), m('G4')], F0
    for c, d in fl_ch:
        prev = voicing(prev, CH[c], m('F3'), m('B4'), n=3)
        P('accomp', t, [(prev, d, '')], 63, art='legato', spread=10, sigma=6)
        t += d
    P('pedal_soft', F0, 'G2:4 E2:4 A2:4 D2:4 B2:4 G2:4 C3:4 A2:2 D2:2 E2:4 C3:4 A2:2 F#2:2 B2:4', 63)
    # the swell pedal shapes each solo phrase (the box opens into the phrase's peak and closes at its cadence)
    T['solo'].automate('instrument.expression', [
        (F0, 0.6), (F0 + 5, 0.82, 'smooth'), (F0 + 10, 0.74), (F0 + 15.5, 0.6, 'smooth'),
        (F0 + 16, 0.66), (F0 + 21, 1.0, 'smooth'), (F0 + 26, 0.86), (F0 + 31.5, 0.68, 'smooth'),
        (F0 + 32, 0.78), (F0 + 37, 0.92, 'smooth'), (F0 + 44, 0.64, 'smooth'), (flu.end, 0.5, 'smooth')])

    # =============================================================== toccata II (q=104)
    halves = ['Em', 'Em', 'Em', 'B7', 'C', 'Em', 'G', 'G',                         # pedal theme in E minor
              'Am', 'Am', 'Am', 'E7', 'F', 'Am', 'C', 'C',                         # ... answered in A minor
              'Am7', 'D7', 'G', 'C', 'F#o7', 'B7', 'Em', 'C',                      # circle of fifths
              'B7', 'B7', 'Em', 'B7', 'A#o7', 'A#o7', 'B7', 'B7',                  # dominant pedal
              'C', 'C', 'A', 'A', 'B7', 'B7']                                      # chromatic climb
    sc = {'Em': E_HARM, 'B7': E_HARM, 'C': E_NAT, 'G': G_MAJ, 'Am': E_NAT, 'E7': set(pcs('A', 'B', 'C', 'D', 'E', 'F', 'G#')),
          'F': set(pcs('A', 'B', 'C', 'D', 'E', 'F', 'G')), 'Am7': E_NAT, 'D7': G_MAJ, 'F#o7': E_NAT,
          'A#o7': set(pcs('B', 'C#', 'D#', 'E', 'F#', 'G', 'A#')), 'A': set(pcs('A', 'B', 'C#', 'D', 'E', 'F', 'G'))}
    starts = ['B4', 'E5', 'G5', 'F#5', 'C5', 'E5', 'B4', 'D5',
              'C5', 'E5', 'A5', 'G#5', 'A4', 'C5', 'E5', 'G5',
              'A4', 'C5', 'B4', 'C5', 'A4', 'B4', 'E5', 'E5']
    rh = []
    for i, c in enumerate(halves[:8]):
        rh += turn_cells(CH[c], starts[i], [0, 1] if i % 2 == 0 else [1, 0])
    for i, c in enumerate(halves[8:16]):
        rh += turn_cells_down(CH[c], starts[8 + i], [0, 1] if i % 2 == 0 else [1, 0], sc[c])
    P('principal', U0, rh, 104, art='detache', sigma=4)
    # the circle-of-fifths bars: up the scale in one half, down the next from where it got
    rh = []
    p = m('A4')
    for i, c in enumerate(halves[16:24]):
        lad = ladder(CH[c])
        p = min(lad, key=lambda q: abs(q - p))
        for k in range(8):
            rh.append(([p], .25, ''))
            p = step(p, 1 if i % 2 == 0 else -1, sc[c])
    piv = {'B7': 'B4', 'Em': 'B4', 'A#o7': 'B4'}
    st = {'B7': 'D#5', 'Em': 'E5', 'A#o7': 'C#5'}
    for i, c in enumerate(halves[24:32]):
        rh += bariolage(CH[c], piv[c], st[c], [1, 2] if i % 2 == 0 else [3, 2], sc[c])
    rh += turn_cells(CH['C'], 'C5', [0, 1, 2, 3])
    rh += turn_cells(CH['A'], 'E5', [0, 1, 2, 3])
    rh += turn_cells(CH['B7'], 'F#5', [0, 1, 2, 3])
    P('full', toc2.bar(8), rh, 104, art='detache', sigma=4)
    # LH: repeated off-beat chords on the swell reeds (the box opening), then held chords over the dominant pedal
    prev = [m('E3'), m('G3'), m('B3')]
    for i, c in enumerate(halves):
        prev = voicing(prev, CH[c], m('D3'), m('E4'))
        b0 = U0 + 2 * i
        if i < 24:
            P('swell', b0 + .5, [(prev, .5, ''), (None, .5, ''), (prev, .5, '')], 104, art='stacc', spread=4)
        elif i < 32:
            P('swell', b0, [(prev, 2, '')], 104, art='legato', spread=6)
        else:
            P('swell', b0, [(prev, 1, ''), (prev, 1, '')], 104, art='chord', spread=6)
    T['swell'].automate('instrument.expression', [(U0, 0.3), (toc2.bar(8), 1.0, 'smooth')])
    P('pedal_full', U0, 'E3:6 B2:2 C3:1 D3:1 E3:1 F#3:1 G3:4 '
                        'A2:6 E2:2 F2:1 G2:1 A2:1 B2:1 C3:4 '
                        'A2:2 D3:2 G2:2 C3:2 F#2:2 B2:2 E2:2 C3:2 '
                        'B2:16 C3:4 C#3:4 D#3:4', 104, art='legato')
    # the climax: D#o7 over the E pedal on the full organ, fermata, general pause
    P('full', toc2.bar(19), [(None, .12, ''), chord_ev('F#3 A3 C4 D#4 F#4 A4 C5 D#5 F#5', 2.88)], 104, art='chord',
      spread=9)
    P('swell', toc2.bar(19), [(None, .12, ''), chord_ev('A3 C4 D#4', 2.88)], 104, art='chord')
    P('pedal_full', toc2.bar(19), 'r:.12 E2:2.88', 104)

    # =============================================================== finale (Grave q=54)
    P('full', Z0, [(None, .12, ''), chord_ev('E3 G3 B3 E4 G4 E5', 1.38, 'm'), chord_ev('G3 B3 E4 G4 B4', .5),
                   chord_ev('A3 C4 E4 A4 C5', .5), chord_ev('F#3 A3 D4 F#4 D5', .5), chord_ev('G3 B3 E4 G4 E5', .5),
                   chord_ev('A3 B3 D#4 F#4 F#5', .5), chord_ev('G3 B3 E4 B4 G5', 2)], 54, art='legato', spread=8,
      scale=E_HARM)
    P('pedal_full', Z0, 'r:.12 E2:1.38 G2:.5 A2:.5 F#2:.5 G2:.5 A2:.5 G2:2', 54)
    run = [([m(x)], .09375, '') for x in 'G5 F#5 E5 D#5 C5 B4 A4 G4 F#4 E4 D#4 C4 B3 A3 G3 F#3'.split()]
    P('full', Z0 + 6.5, run, 54, art='detache', sigma=2, accel=(1.4, 0.75))
    P('full', Z0 + 8, [chord_ev('A3 C4 F4 A4 C5 F5', 2), (None, .5, ''), chord_ev('B3 E4 G4 B4 E5 G5', 1.5),
                       chord_ev('B3 D#4 F#4 A4', 3), (None, .25, ''), chord_ev('G#3 B3 E4 G#4 B4 E5 G#5', 2.75),
                       chord_ev('A3 C4 E4 A4 C5 E5', 2), chord_ev('G#3 B3 E4 G#4 B4 E5 G#5', 6.5)],
      54, art='legato', spread=10)
    P('full', Z0 + 12, 'tD#5:3', 54, scale=E_MAJ)
    P('pedal_full', Z0 + 8, 'A2:2 r:.5 B2:4.5 r:.25 E2:11.25', 54, art='legato')
    # the pedal solo's reduced registration sits wetter: the feet alone in the church
    T['pedal'].automate('send.hall', [(ped.bar(4) - 0.5, -12.0), (ped.bar(4), -7.0, 'smooth'), (F0 - 0.5, -7.0),
                                     (F0, -12.0, 'smooth')])
    # the silences: at every fermata before a silence the church blooms and is given back when the music goes on
    for at, length, back, roles in ((E0 + 3, 1.5, E0 + 5, ('principal',)), (E0 + 7, 2, E0 + 9.5, ('full', 'pedal_full')),
                                    (E0 + 23, 2.5, T0, ('full', 'pedal_full')), (R0, 2, R0 + 2.5, ('full',)),
                                    (R0 + 4, 2, R0 + 6.5, ('full',)), (R0 + 8, 2.5, R0 + 11, ('full',)),
                                    (R0 + 13.5, 2, P0, ('full',)), (toc2.bar(19), 3, Z0, ('full', 'pedal_full')),
                                    (Z0 + 8, 2, Z0 + 10.5, ('full',))):
        orch.ring(o, at, length=length, db=4, roles=roles, back=back)
    orch.ring(o, fin.bar(5), length=4, db=4)

    org.finish(T)
    # master (MASTER.md): the church IR and the pipes leave the top 10-19 dB under the classical balance - a gentle
    # air shelf above the mixture's harsh band, the safety limiter's ceiling; the loudness stays where the
    # registrations put it (~-19 LUFS-I, the middle of the concert window)
    mastering.apply(s, eq={'high.freq': 8000, 'high.gain': 2.0, 'high.q': 0.7071}, limiter={'ceiling': -1.2})
    return s
