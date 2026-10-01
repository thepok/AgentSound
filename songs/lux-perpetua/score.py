"""Lux Perpetua - the score as data (an original Requiem in D minor in the idiom of Mozart's K. 626, no borrowed notes).

Everything here is notes and harmony, no sounds: song.py orchestrates and performs it. Pitches are sounding pitch,
times are beats (quarter notes) from the start of each movement. The four-part choir writing is voiced by `satb()`
(the library's `agentsound.voicing.voice` in the choir's ranges), a small voice-leading search (chord tones in SATB ranges, complete chords, no doubled leading tone or seventh, no
parallel fifths / octaves, smallest motion) around the lines written by hand (soprano tunes, basses, fugue subject and
countersubject).
"""
from __future__ import annotations

from agentsound import voicing
from agentsound.voicing import N, harmony_at, info, length, line, timeline  # noqa: F401  (song.py uses them)

# ------------------------------------------------------------------------------------------------ the voicer
# The four-part voicer and the counterpoint helpers live in the library (agentsound.voicing); the Requiem keeps its
# choir ranges, centres and D minor's leading tone (C#) as the defaults.

ORDER = ('S', 'A', 'T', 'B')
CHOIR = {'S': (60, 79), 'A': (55, 72), 'T': (48, 67), 'B': (43, 62)}          # C4-G5, G3-C5, C3-G4, G2-D4
CENTER = {'S': 70, 'A': 64, 'T': 57, 'B': 50}


def satb(steps: list, *, lt: int | None = 1, ranges: dict | None = None, prev: dict | None = None) -> list:
    """Voice a chord sequence (voicing.voice in the choir's ranges; lt = C#, the leading tone of D minor)."""
    return voicing.voice(steps, voices=ranges or CHOIR, lt=lt, prev=prev, center=CENTER)


def chorale(table: list, t0: float = 0.0, *, lt: int | None = 1, ranges=None, prev=None, tie: bool = False,
            active=ORDER) -> dict:
    """Homophonic writing from (dur, chord, S, B[, {voice: pitch}]) rows (voicing.chorale, SATB)."""
    return voicing.chorale(table, t0, voices=ranges or CHOIR, lt=lt, prev=prev, tie=tie, active=active,
                           center=CENTER)


# ================================================================================================ I. INTROITUS
# 4/4, Adagio (q = 56). intro: 6 bars of orchestra (syncopated string pulse over a chromatic lament bass, bassoons
# then basset horns sighing), requiem: 10 bars of choir (staggered entry, the turn to F major 'lux', the Neapolitan
# back to D minor, the lament bass again, a half cadence on A).

INTRO = [  # (dur, chord, top voice, bass) - the strings' harmony
    (2, 'Dm', 'F4', 'D3'), (2, 'A7/C#', 'G4', 'C#3'),
    (2, 'Dm7/C', 'F4', 'C3'), (2, 'G/B', 'G4', 'B2'),
    (2, 'Gm/Bb', 'G4', 'Bb2'), (1, 'Dm/A', 'F4', 'A2'), (1, 'A', 'E4', 'A2'),
    (2, 'Bb', 'F4', 'Bb2'), (2, 'Em7b5/G', 'E4', 'G2'),
    (2, 'Eb/G', 'G4', 'G2'), (2, 'Dm/A', 'F4', 'A2'),
    (4, 'A7', 'E4', 'A2'),
]
INTRO_BASSOON = 'r:1 A3:1 E4:1 G4:1 | F4:1 E4:.5 D4:.5 D4:1.5 C4:.5 | Bb3:1 D4:1 A3:2'
INTRO_BASSET1 = 'r:8 | r:2 D5:1 C#5:1 | D5:1.5 C5:.5 Bb4:2 | Bb4:1 Eb5:1 D5:2 | C#5:3 r:1'
INTRO_BASSET2 = 'r:8 | r:2 A4:1 A4:1 | F4:2 G4:2 | G4:2 F4:2 | E4:3 r:1'

REQUIEM = [  # (dur, chord, soprano (structural), bass) - the choir's harmony, 10 bars
    (4, 'Dm', 'D5', 'D3'),
    (1, 'A7/E', 'C#5', 'E3'), (1, 'Dm', 'D5', 'D3'), (2, 'A7', 'E5', 'A2'),
    (2, 'Dm', 'F5', 'D3'), (1, 'Bb', 'D5', 'Bb2'), (1, 'C7', 'C5', 'C3'),
    (1, 'F', 'C5', 'F3'), (1, 'F', 'A4', 'F3'), (1, 'Gm7', 'Bb4', 'G3'), (1, 'C7', 'Bb4', 'C3'),
    (1, 'F', 'A4', 'F3'), (1, 'F', 'C5', 'F3'), (2, 'F/A', 'F5', 'A2'),
    (1, 'Bb', 'D5', 'Bb2'), (1, 'Gm7', 'G5', 'G2'), (1, 'F/C', 'F5', 'C3'), (1, 'C7', 'E5', 'C3'),
    (1, 'F', 'F5', 'F3'), (1, 'Dm/F', 'D5', 'F3'), (2, 'Eb/G', 'Eb5', 'G2'),
    (1, 'Dm/A', 'D5', 'A2'), (1, 'A7', 'C#5', 'A2'), (1, 'Dm', 'D5', 'D3'), (1, 'Dm7/C', 'F5', 'C3'),
    (1, 'G/B', 'D5', 'B2'), (1, 'Gm/Bb', 'D5', 'Bb2'), (1, 'Dm/A', 'D5', 'A2'), (1, 'A7', 'C#5', 'A2'),
    (2, 'Asus4', 'D5', 'A2'), (2, 'A', 'C#5', 'A2'),
]
# bar 1: the choir enters voice by voice, B T A S a beat apart, each on 'Re-qui-em' (a note, its upper neighbour,
# back); the soprano's pickup lands on the leading tone of bar 2
REQUIEM_ENTRY = {
    'B': 'D3:1 E3:.5 D3:2.5',
    'T': 'r:1 A3:1 Bb3:.5 A3:1.5',
    'A': 'r:2 F4:1 G4:.5 F4:.5',
    'S': 'r:2.5 A4:.5 D5:1',
}
REQUIEM_SOPRANO = ('r:4 | C#5:1 D5:1 E5:2 | F5:1.5 E5:.5 D5:1 C5:1 | C5:1 A4:1 Bb4:2 | '
                   'A4:1 C5:1 F5:1.5 E5:.5 | D5:1 G5:1 F5:1 E5:1 | F5:1 D5:1 Eb5:1.5 D5:.5 | '
                   'D5:1 C#5:1 D5:1 F5:1 | D5:2 D5:1 C#5:1 | D5:2 C#5:2')      # the lament bass under a held D, 4-3

# ================================================================================================ KYRIE (fugue)
# 4/4, Allegro moderato (q = 88), 19 bars. Subject (a rising fifth, the sigh on the sixth, a falling scale into the
# leading tone) and a chromatic countersubject, entries bass - tenor (answer) - alto - soprano (answer), an
# episode (the head in imitation over a circle of fifths into F major), a middle entry in F major (tenors), the
# bass and the alto a bar apart, the Adagio cadence (iv6 - N6 - V7) onto a bare fifth.

SUBJECT = 'D4:1 A4:1 Bb4:1.5 A4:.5 G4:.5 F4:.5 E4:.5 D4:.5 C#4:1 D4:1'
# the answer is tonal: the head's fifth D-A is answered by the fourth A-D, the rest in A minor
ANSWER = 'A3:1 D4:1 F4:1.5 E4:.5 D4:.5 C4:.5 B3:.5 A3:.5 G#3:1 A3:1'
COUNTER = 'F3:2 E3:2 Eb3:1 D3:1 E3:1 F3:1'
SUBJECT_F = 'F4:1 C5:1 D5:1.5 C5:.5 Bb4:.5 A4:.5 G4:.5 F4:.5 E4:1 F4:1'
H_D = [(0, 2, 'Dm'), (2, 2, 'Em7b5'), (4, 2, 'A7'), (6, 1, 'A7'), (7, 1, 'Dm')]   # beat 6: the voicer sees the C#
H_A = [(0, 1, 'Am'), (1, 1, 'Dm7'), (2, 2, 'Bm7b5'), (4, 2, 'E7'), (6, 1, 'E7'), (7, 1, 'Am')]   # the answer's D: iv7
H_F = [(0, 2, 'F'), (2, 2, 'Gm7'), (4, 2, 'C7'), (6, 1, 'C7'), (7, 1, 'F')]


def _at(h, t0):
    return [(s + t0, d, c) for s, d, c in h]


KYRIE_HARMONY = (_at(H_D, 0) + _at(H_A, 8) + _at(H_D, 16) + _at(H_A, 24)
                 + [(32, 2, 'Dm'), (34, 2, 'Gm7'), (36, 2, 'C7'), (38, 2, 'F'),
                    (40, 2, 'Bb'), (42, 2, 'Gm7'), (44, 2, 'C7sus4'), (46, 2, 'C7')]
                 + _at(H_F, 48) + _at(H_D, 56)[:2]
                 + [(60, 1, 'Gm'), (61, 1, 'A7'), (62, 1, 'C#dim7'), (63, 1, 'Dm'),
                    (64, 3, 'A7'), (67, 1, 'Dm'),
                    (68, 1, 'Gm/Bb'), (69, 1, 'Eb/G'), (70, 2, 'A7'),
                    (72, 4, 'D5')])
KYRIE_LT = {**{t: 1 for t in range(0, 76)}, **{t: 8 for t in list(range(8, 16)) + list(range(24, 32))},
            **{t: 4 for t in range(36, 56)}}
KYRIE_FIXED = {  # voice -> [(start, dur, pitch)]: the subject / countersubject entries and the episode's head motifs
    'B': line(SUBJECT, 0, -12) + line(COUNTER, 8, -5) + line(SUBJECT, 56, -12)
         + line('D3:1 A2:1 G2:1 Bb2:1 C3:1 E3:1 F3:1 A2:1 Bb2:1 D3:1 G2:1 Bb2:1 C3:2 C3:1 Bb2:1', 32),  # the walk
    'T': line(ANSWER, 8) + line(COUNTER, 16) + line('Bb3:1 F4:1 G4:1.5 F4:.5', 40) + line(SUBJECT_F, 48, -12),
    'A': line(SUBJECT, 16) + line(COUNTER, 24, 7) + line('D4:1 A4:1 Bb4:1.5 A4:.5', 32) + line('G4:2', 58)
         + line(SUBJECT, 60),
    'S': line(ANSWER, 24, 12) + line('C5:1 G5:1 A5:1.5 G5:.5', 36) + line('C5:1 G5:.5 F5:.5 E5:2', 44)
         + line('D5:1 Eb5:1 C#5:2 D5:4', 68),
}
KYRIE_ENTRY = {'B': 0, 'T': 8, 'A': 16, 'S': 24}
KYRIE_FINAL = {'S': 'D5', 'A': 'A4', 'T': 'A3', 'B': 'D3'}       # the bare fifth (no third)
KYRIE_LENGTH = 76

# ================================================================================================ DIES IRAE
# 4/4, Allegro assai (q = 144), 24 bars: dies (8: the outburst, a turn to F major), tremor (8: subito p, trembling
# repeated chords over a chromatic rising bass F - F# - G - G# - A, crescendo into the dominant pedal, a deceptive
# Bb, the Neapolitan), ira (8: the climax, the cadence, hammered chords, silence).

DIES = [
    (2, 'Dm', 'D5', 'D3'), (1, 'Dm', 'F5', 'D3'), (1, 'Dm', 'A5', 'D3'),
    (1.5, 'A7/C#', 'E5', 'C#3'), (.5, 'A7/C#', 'E5', 'C#3'), (2, 'Dm', 'D5', 'D3'),
    (1, 'Bb', 'D5', 'Bb2'), (1, 'Bb', 'F5', 'Bb2'), (2, 'Gm/Bb', 'G5', 'Bb2'),
    (3, 'A', 'E5', 'A2'), (1, None, None, None),
    (2, 'Dm', 'F5', 'D3'), (1, 'Bb', 'F5', 'Bb2'), (1, 'Bb', 'D5', 'Bb2'),
    (2, 'C7/E', 'G5', 'E3'), (2, 'F', 'F5', 'F3'),
    (1, 'Bb', 'F5', 'Bb2'), (1, 'Bb', 'D5', 'Bb2'), (1, 'C7', 'E5', 'C3'), (1, 'C7', 'G5', 'C3'),
    (3, 'F', 'F5', 'F3'), (1, None, None, None),
]
TREMOR = (
    [(1, 'Dm/F', 'A4', 'F3')] * 4 + [(1, 'F#dim7', 'C5', 'F#3')] * 4
    + [(1, 'Gm', 'D5', 'G3')] * 4 + [(1, 'G#dim7', 'F5', 'G#3')] * 4
    + [(2, 'Dm/A', 'F5', 'A3'), (2, 'A7', 'E5', 'A3'),
       (2, 'Dm/A', 'A5', 'A2'), (2, 'A7', 'G5', 'A2'),
       (4, 'Bb', 'F5', 'Bb2'),
       (2, 'Eb/G', 'G5', 'G2'), (2, 'A7', 'G5', 'A2')])
IRA = [
    (2, 'Dm', 'F5', 'D3'), (1, 'Dm/F', 'A5', 'F3'), (1, 'Dm/F', 'F5', 'F3'),
    (2, 'Gm/Bb', 'G5', 'Bb2'), (2, 'C#dim7/G', 'E5', 'G2'),
    (2, 'Dm/A', 'F5', 'A2'), (2, 'A7', 'E5', 'A2'),
    (3, 'Dm', 'D5', 'D3'), (1, None, None, None),
    (1, 'Dm', 'D5', 'D3'), (1, 'Dm', 'D5', 'D3'), (2, 'Bb', 'F5', 'Bb2'),
    (2, 'Eb/G', 'G5', 'G2'), (2, 'A7', 'G5', 'A2'),
    (1, 'Dm', 'F5', 'D3'), (3, None, None, None),
    (4, None, None, None),
]

# ================================================================================================ TUBA
# 4/4, Andante (q = 72), Bb major, 8 bars: the solo tenor trombone's call (a rising arpeggio, a falling answer, a
# half cadence), then the men of the choir in unison with the trombone above them; the last bar turns to A7 (the
# dominant of D minor) under a fermata.

TUBA = [
    (4, 'Bb', 'F4', 'Bb2'),
    (2, 'Bb', 'F4', 'Bb2'), (2, 'Eb', 'G4', 'Eb3'),
    (2, 'Cm', 'G4', 'C3'), (2, 'F7', 'F4', 'F2'),
    (4, 'F', 'F4', 'F2'),
    (2, 'Bb/D', 'F4', 'D3'), (2, 'Eb', 'G4', 'Eb3'),
    (2, 'Cm7', 'G4', 'C3'), (2, 'F7', 'A4', 'F2'),
    (1, 'Bb/F', 'Bb4', 'F2'), (1, 'F7', 'A4', 'F2'), (1, 'Gm', 'Bb4', 'G2'), (1, 'Eb', 'G4', 'Eb2'),
    (2, 'Gm', 'G4', 'G2'), (2, 'A7', 'G4', 'A2'),
]
TUBA_TROMBONE = ('Bb2:1 D3:1 F3:2 | Bb3:1.5 A3:.5 G3:1 F3:1 | Eb3:2 C3:1 A2:1 | F3:3 r:1 | '
                 'r:2 G3:1 Bb3:1 | C4:1.5 Bb3:.5 A3:1 C4:1 | D4:1 C4:1 Bb3:1 G3:1 | Bb3:2 A3:2')
TUBA_MEN = 'r:16 | D3:2 Eb3:2 | G3:1.5 F3:.5 F3:2 | F3:1 Eb3:1 D3:1 Bb2:1 | D3:2 r:2'

# ================================================================================================ LACRIMOSA
# 12/8 (a bar = 6 beats = four dotted quarters), Larghetto (q = 72), 12 bars: lacrimosa (8: the violins' sighs,
# the choir's lament, the chromatic climb over a descending bass to the forte climax, the sinking answer), amen
# (4: plagal 'amen' chords, the Neapolitan, the Picardy third: D major under a fermata).

G = 1.5            # one dotted quarter
LACRIMOSA = [  # (dur, chord, soprano (structural), bass) per dotted quarter
    (G, 'Dm', 'F4', 'D3'), (G, 'Dm', 'F4', 'D3'), (G, 'A7/C#', 'E4', 'C#3'), (G, 'Dm', 'F4', 'D3'),
    (G, 'Gm/Bb', 'G4', 'Bb2'), (G, 'Eb/G', 'G4', 'G2'), (G, 'Dm/A', 'F4', 'A2'), (G, 'A7', 'E4', 'A2'),
    (G, 'Dm', 'A4', 'D3'), (G, 'A/E', 'C#5', 'E3'), (G, 'Em7b5/G', 'E5', 'G2', {'A': 'D5'}), (G, 'A', 'E5', 'A2'),
    (G, 'Dm', 'F5', 'D3'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Dm/A', 'D5', 'A2'), (G, 'A', 'A4', 'A2'),
    (G, 'Dm', 'A4', 'D3'), (G, 'Gm', 'Bb4', 'G2'), (G, 'E7/G#', 'B4', 'G#2'), (G, 'Am', 'C5', 'A2'),
    (G, 'A', 'C#5', 'A2'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Em7b5/Bb', 'E5', 'Bb2'), (G, 'A7', 'E5', 'A2'),
    (G, 'Dm', 'F5', 'D3'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Dm/A', 'D5', 'A2'), (G, 'A7', 'C#5', 'A2'),
    (G, 'Dm', 'D5', 'D3'), (G, 'Bb', 'D5', 'Bb2'), (G, 'Em7b5/G', 'E5', 'G2'), (G, 'A7', 'C#5', 'A2'),
]
AMEN = [
    (G, 'Dm', 'A4', 'D3'), (G, 'Gm/D', 'Bb4', 'D3'), (G, 'Dm', 'A4', 'D3'), (G, 'Bb/D', 'Bb4', 'D3'),
    (G, 'Eb/G', 'Bb4', 'G2'), (G, 'Dm/A', 'A4', 'A2'), (G, 'A7', 'A4', 'A2'), (G, 'A7', 'G4', 'A2'),
    (G, 'Dm', 'F4', 'D3'), (G, 'Gm/D', 'G4', 'D3'), (2 * G, 'D', 'F#4', 'D3'),
    (6, 'D', 'F#4', 'D3'),
]
LACRIMOSA_SOPRANO = ('r:12 | A4:1 D5:.5 C#5:1 D5:.5 E5:1 F5:.5 E5:1.5 | F5:1 E5:.5 D5:1 C#5:.5 D5:1 Bb4:.5 A4:1.5 | '
                     'A4:1.5 Bb4:1.5 B4:1.5 C5:1.5 | C#5:1.5 D5:1.5 E5:3 | '
                     'F5:1 E5:.5 D5:1 C#5:.5 D5:1 E5:.5 C#5:1.5 | D5:1.5 F5:1 D5:.5 E5:1 D5:.5 C#5:1.5')
AMEN_SOPRANO = 'A4:1.5 Bb4:1.5 A4:1.5 Bb4:1.5 | Bb4:1.5 A4:1.5 A4:1.5 G4:1.5 | F4:1.5 G4:1.5 F#4:3 | F#4:6'


# ================================================================================================ helpers for song.py

def _key_pcs(t: float):
    """The Kyrie's local key at beat t (from its start): (scale pcs, tonic pc, leading-tone pc)."""
    if 8 <= t < 16 or 24 <= t < 32:
        return {9, 11, 0, 2, 4, 5, 7}, 9, 8                   # A minor (the answers)
    if 32 <= t < 56:
        return {5, 7, 9, 10, 0, 2, 4}, 5, 4                   # the episode and the middle entry: F major
    return {2, 4, 5, 7, 9, 10, 0}, 2, 1                       # D minor


def arpeggiate(parts: dict, free: set, harmony: list, t0: float, until: float = 68.0) -> list:
    """The fugue's free voices move in quarters (voicing.arpeggiate in the choir's ranges)."""
    return voicing.arpeggiate(parts, free, harmony, t0, voices=CHOIR, until=until)


def passing_eighths(parts: dict, free: set, t0: float, until: float = 68.0) -> list:
    """Passing 8ths for the fugue's free voices in the Kyrie's local keys (voicing.passing_eighths)."""
    return voicing.passing_eighths(parts, free, t0, _key_pcs, order=ORDER, until=until)


def swells(notes, a: float, b: float, period: float, lo: float = 0.65) -> list:
    """Expression points for a sung line that breathes: from `a` to `b`, one swell per `period` beats - soft at the
    start, full on the phrase's highest note, soft again at its end (lo 0.65 = ~7.5 dB of swell) - then back to 1."""
    pts = [(a - 0.3, 1.0), (a - 0.05, lo)]
    w = a
    while w < b - 1e-6:
        e = min(b, w + period)
        inside = [n for n in notes if w - 1e-6 <= n[0] < e - 1e-6]
        peak = max(inside, key=lambda n: (n[2], -n[0]))[0] if inside else (w + e) / 2
        peak = min(max(peak, w + 0.25 * (e - w)), w + 0.75 * (e - w))
        pts += [(peak, 1.0, 'smooth'), (e - 0.05, lo, 'smooth')]
        w = e
    pts.append((b + 0.2, 1.0, 'smooth'))
    return pts
