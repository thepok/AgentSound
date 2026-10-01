"""Band preset demo: church_organ - a chorale prelude in F major (18 bars, 72 BPM, ~1:05). Build:
    python -m agentsound build songs/_bands/church_organ

Only the preset (agentsound.bandlib.orchestra) plus ordinary composition code: the registrations are roles, so the
piece 'draws stops' by moving from one track to the next, the way an organist changes registration between
phrases.

  intro   4  'soft' (swell flutes + salicional): a solo line over held chords, the swell pedal opening
             ('instrument.expression'), a soft 16' pedal
  chorale 8  'principal' (8' 4' 2' principal chorus): a four-part hymn, the bass in the 'pedal'
  toccata 6  'full' organ (mixture, trumpet) with 'pedal_full' (+ Basun 16'): rhythmic chords climbing to the
             final F major chord, held and left to ring in the church

Measured (report, 'classical'): -17.4 LUFS-I, LRA 20.1 LU, 0 warnings, 0 clicks; intro -32.6 (soft), chorale
-22.6 (principal), toccata -15.1 LUFS (full): the registrations are the dynamics; reverb -11.9 LU, lows correlation 1.00.

CREDITS: Burea Church organ sample set by Lars Palo (familjenpalo.se), CC-BY-SA 2.5; Voxengo IM Reverbs
(St Nicolaes Church).
"""
from agentsound import *
from agentsound import bands
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'classical'}                  # == bands.church_organ(s).analysis
METADATA = {'artist': 'AgentSound', 'album': 'Band presets', 'genre': 'Classical'}

W = 4


def part(rows) -> Clip:
    notes = []
    for i, bar in enumerate(rows):
        for t, d, p, v in bar:
            for q in (p if isinstance(p, (list, tuple)) else [p]):
                notes.append((i * W + t, d, q, v))
    return Clip(notes, length=len(rows) * W)


def legato(clip: Clip, overlap=0.03) -> Clip:
    """Organ legato: a note holds a hair into the next chord (no gap between the pipes), except where the same key is
    struck again - that one is released just before, as an organist repeats a note."""
    starts = {(round(n.start, 6), n.pitch) for n in clip}
    out = []
    for n in clip:
        end = round(n.start + n.dur, 6)
        out.append((n.start, n.dur - 0.06 if (end, n.pitch) in starts else n.dur + overlap, n.pitch, n.vel))
    return Clip(out, length=clip.length)


# ------------------------------------------------------------------ intro: solo line + held chords on 'soft'
INTRO_SOLO = [[(0, 2, 'C5', 80), (2, 2, 'A4', 80)], [(0, 1, 'Bb4', 80), (1, 1, 'A4', 80), (2, 2, 'G4', 80)],
              [(0, 1, 'A4', 80), (1, 1, 'Bb4', 80), (2, 1, 'C5', 80), (3, 1, 'D5', 80)], [(0, 4, 'C5', 80)]]
INTRO_CHORDS = [[(0, 4, ['F3', 'A3', 'C4'], 70)], [(0, 2, ['E3', 'G3', 'C4'], 70), (2, 2, ['E3', 'Bb3', 'C4'], 70)],
                [(0, 2, ['F3', 'A3', 'C4'], 70), (2, 2, ['F3', 'Bb3', 'D4'], 70)], [(0, 4, ['E3', 'G3', 'C4'], 70)]]
INTRO_PEDAL = [[(0, 8, 'F2', 70)], [], [(0, 4, 'F2', 70)], [(0, 4, 'C2', 70)]]

# ------------------------------------------------------------------ chorale: S / A / T on 'principal', B on 'pedal'
#                F      C/E     | Dm     C      | F      Bb/D   | F        | F      Am     | Bb     F/C    | Gm7   C7 | F
SOP = ['A4', 'G4', 'F4', 'G4', 'A4', 'Bb4', 'A4', None, 'C5', 'C5', 'D5', 'C5', 'Bb4', 'G4', 'F4', None]
ALT = ['F4', 'E4', 'D4', 'E4', 'F4', 'F4', 'F4', None, 'F4', 'E4', 'F4', 'F4', 'F4', 'E4', 'C4', None]
TEN = ['C4', 'C4', 'A3', 'C4', 'C4', 'D4', 'C4', None, 'A3', 'A3', 'D4', 'A3', 'D4', 'Bb3', 'A3', None]
BAS = ['F2', 'E2', 'D2', 'C2', 'F2', 'D2', 'F2', None, 'F2', 'A2', 'Bb2', 'C3', 'G2', 'C2', 'F2', None]


def halves(*voices) -> Clip:
    """Half-note chords from voice lists (None = the previous chord is held for the whole bar)."""
    notes = []
    for i in range(len(voices[0])):
        if voices[0][i] is None:
            continue
        held = i + 1 < len(voices[0]) and voices[0][i + 1] is None
        for v in voices:
            notes.append((i * 2, 4 if held else 2, v[i], 90))
    return Clip(notes, length=len(voices[0]) * 2)


# the soprano's passing A4 in bar 7 (Bb4 - A4 over Gm7)
def chorale_manual() -> Clip:
    c = halves(SOP, ALT, TEN)
    out = []
    for n in c:
        if n.start == 24 and n.pitch == 70:       # Bb4 on beat 1 of bar 7 -> Bb4 (1) A4 (1)
            out += [(24, 1, 70, 90), (25, 1, 69, 90)]
        else:
            out.append(tuple(n))
    return Clip(out, length=c.length)


# ------------------------------------------------------------------ toccata: full organ chords + pedal_full
RHY = [(0, 1.5), (1.5, 0.5), (2, 1), (3, 1)]
TOC_CHORDS = [['F3', 'A3', 'C4', 'F4'], ['F3', 'A3', 'D4', 'F4'], ['F3', 'Bb3', 'D4', 'F4'], ['G3', 'Bb3', 'D4', 'F4']]
TOCCATA = ([[(t, d, ch, 100) for t, d in RHY] for ch in TOC_CHORDS] +
           [[(0, 2, ['G3', 'C4', 'F4', 'G4'], 100), (2, 2, ['G3', 'Bb3', 'E4', 'G4'], 100)],
            [(0, 8, ['F3', 'A3', 'C4', 'F4', 'A4', 'C5'], 100)]])
TOC_PEDAL = [[(0, 2, 'F2', 100), (2, 2, 'F3', 100)], [(0, 2, 'D2', 100), (2, 2, 'D3', 100)],
             [(0, 2, 'Bb2', 100), (2, 2, 'Bb2', 100)], [(0, 2, 'G2', 100), (2, 2, 'G2', 100)],
             [(0, 4, 'C2', 100)], [(0, 8, 'F2', 100)]]


def build() -> Song:
    s = Song('Chorale prelude', tempo=72, key='F major', seed=4, tail=7)
    intro, chorale, toccata = s.section('intro', 4), s.section('chorale', 8), s.section('toccata', 6)
    s.ritardando((chorale.bar(6), chorale.end), to=0.85)
    s.ritardando((toccata.bar(4), toccata.bar(5)), to=0.8, a_tempo=False)
    s.fermata(toccata.bar(5), hold=2)

    o = bands.church_organ(s)
    orch.perform(o, 'soft', legato(part(INTRO_SOLO)), intro)
    orch.perform(o, 'soft', legato(part(INTRO_CHORDS)), intro)
    orch.perform(o, 'pedal', legato(part(INTRO_PEDAL)), intro)
    o.soft.automate('instrument.expression', [(intro.start, 0.55), (intro.bar(2), 0.6), (intro.bar(3), 1.0, 'smooth'),
                                              (intro.end - 0.5, 0.8, 'smooth')])     # the swell box opens

    orch.perform(o, 'principal', legato(chorale_manual()), chorale)
    orch.perform(o, 'pedal', legato(halves(BAS)), chorale)

    orch.perform(o, 'full', part(TOCCATA), toccata)
    orch.perform(o, 'pedal_full', part(TOC_PEDAL), toccata)
    orch.ring(o, toccata.bar(4), length=4, db=4)
    return s
