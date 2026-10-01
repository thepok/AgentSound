"""Erik Satie, Gymnopedie No. 1 (1888) - the notes (public domain: Satie died 1925), as data.

Written from the score and then checked bar by bar against a reference recording by analysis only (onsets +
template transcription + what sounds after each chord, see NOTES.md); where the analysis and memory disagreed the
analysis won (bars 17-19 low melody C#4 F#4 E4, the chords of the D-pedal middle part, the RH chords of the cadences).

Layout: 78 bars of 3/4, two halves of 39 bars; the second repeats the first up to bar 32 (= 71) and then turns to
D minor (bars 72-78). Every bar: LH bass on beat 1 (held through the bar), LH chord on beat 2 (held to the bar end),
RH melody events. Pitches are note names; beats are 0-based inside the bar; durations in beats.
"""

G7 = ('B3', 'D4', 'F#4')          # Gmaj7 over G2
D7 = ('A3', 'C#4', 'F#4')         # Dmaj7 over D2

# bar -> (bass, chord, melody [(beat, pitch or (pitches,), dur)], extra LH events [(beat, pitches, dur)])
FIRST = {
    1: ('G2', G7, [], []),
    2: ('D2', D7, [], []),
    3: ('G2', G7, [], []),
    4: ('D2', D7, [], []),
    5: ('G2', G7, [(1, 'F#5', 1), (2, 'A5', 1)], []),
    6: ('D2', D7, [(0, 'G5', 1), (1, 'F#5', 1), (2, 'C#5', 1)], []),
    7: ('G2', G7, [(0, 'B4', 1), (1, 'C#5', 1), (2, 'D5', 1)], []),
    8: ('D2', D7, [(0, 'A4', 3)], []),
    9: ('G2', G7, [(0, 'F#4', 12)], []),          # tied over four bars
    10: ('D2', D7, [], []),
    11: ('G2', G7, [], []),
    12: ('D2', D7, [], []),
    13: ('G2', G7, [(1, 'F#5', 1), (2, 'A5', 1)], []),
    14: ('D2', D7, [(0, 'G5', 1), (1, 'F#5', 1), (2, 'C#5', 1)], []),
    15: ('G2', G7, [(0, 'B4', 1), (1, 'C#5', 1), (2, 'D5', 1)], []),
    16: ('D2', D7, [(0, 'A4', 3)], []),
    17: ('F#2', ('A3', 'C#4', 'F#4'), [(0, 'C#4', 1)], []),  # F#m; the low melody C#4 sits inside the chord
    18: ('B1', ('B3', 'D4', 'F#4'), [(0, 'F#4', 1)], []),   # Bm (the chord re-strikes the melody's F#4)
    19: ('E2', ('G3', 'B3', 'G4'), [(0, 'E4', 9)], []),     # Em; E4 held over bars 19-21
    20: ('E2', ('B3', 'D4', 'G4'), [], []),
    21: ('D2', ('F3', 'A3', 'D4', 'F4'), [], []),          # D minor: the dorian middle part begins
    22: ('A2', ('A3', 'C4', 'E4'), [(0, 'A4', 1), (1, 'B4', 1), (2, 'C5', 1)], []),
    23: ('D2', ('G3', 'B3', 'E4'), [(0, 'E5', 1), (1, 'D5', 1), (2, 'B4', 1)], []),
    24: ('D2', ('G3', 'B3', 'E4'), [(0, 'D5', 1), (1, 'C5', 1), (2, 'B4', 1)], []),
    25: ('D2', ('C3', 'E3', 'A3', 'E4'), [(0, 'D5', 5)], []),
    26: ('D2', ('C3', 'F#3', 'A3', 'D4'), [(2, 'D5', 1)], []),
    27: ('D2', ('A3', 'C4', 'F4'), [(0, 'E5', 1), (1, 'F5', 1), (2, 'G5', 1)], []),
    28: ('D2', ('A3', 'C4', 'E4'), [(0, 'A5', 1), (1, 'C5', 1), (2, 'D5', 1)], []),
    29: ('D2', ('G3', 'B3', 'E4'), [(0, 'E5', 1), (1, 'D5', 1), (2, 'B4', 1)], []),
    30: ('D2', ('C3', 'E3', 'A3', 'E4'), [(0, 'D5', 5)], []),
    31: ('D2', ('C3', 'F#3', 'A3', 'D4'), [(2, 'D5', 1)], []),
    32: ('E2', ('B3', 'E4', 'G4'), [(0, 'G5', 3)], []),
    33: ('F#2', ('A3', 'C#4', 'F#4'), [(0, 'F#5', 3)], []),
    34: ('B1', ('B3', 'D4', 'F#4'), [(0, 'B4', 1), (1, 'A4', 1), (2, 'B4', 1)], []),
    35: ('E2', ('C#4', 'E4', 'A4'), [(0, 'C#5', 1), (1, 'D5', 1), (2, 'E5', 1)], []),
    36: ('E2', ('A3', 'C#4', 'A4'), [(0, 'C#5', 1), (1, 'D5', 1), (2, 'E5', 1)], []),
    37: ('E2', ('B2', 'A3', 'D4'), [(0, 'F#4', 2), (2, ('E4', 'G4'), 1)], [(2, ('E3', 'G3', 'B3'), 1)]),
    38: ('A2', ('A3', 'C4'), [(0, ('E4', 'G4', 'C5'), 3)], []),      # Am7: everything on the downbeat
    39: ('D2', ('A2', 'A3'), [(0, ('D4', 'F#4', 'D5'), 3)], []),      # D major: the first half ends
}

SECOND_CHANGES = {                   # bars of the second half (40-78) that differ from bar - 39
    72: ('E2', ('A3', 'D4', 'F4'), [(0, 'F5', 3)], []),
    73: ('E2', ('A3', 'C4', 'F4'), [(0, 'B4', 1), (1, 'C5', 1), (2, 'F5', 1)], []),
    74: ('E2', ('C4', 'E4', 'A4'), [(0, 'E5', 1), (1, 'D5', 1), (2, 'C5', 1)], []),
    75: ('E2', ('A3', 'C4', 'F4', 'A4'), [(0, 'E5', 1), (1, 'D5', 1), (2, 'C5', 1)], []),
    76: ('E2', ('B2', 'A3', 'D4'), [(0, 'F4', 2), (2, ('E4', 'G4'), 1)], [(2, ('E3', 'G3', 'B3'), 1)]),
    77: ('A2', ('A3', 'C4'), [(0, ('E4', 'G4', 'C5'), 3)], []),
    78: ('D2', ('A2', 'A3'), [(0, ('D4', 'F4', 'A4'), 3)], []),      # D minor: the final chord
}


def bars() -> dict:
    """All 78 bars."""
    out = dict(FIRST)
    for b in range(40, 79):
        out[b] = SECOND_CHANGES.get(b, FIRST[b - 39])
    return out


# Bars whose chord is struck with the bass (the cadences), not on beat 2
CHORD_ON_ONE = {38, 39, 77, 78}

PHRASES = [(1, 4), (5, 8), (9, 12), (13, 16), (17, 21), (22, 26), (26, 31), (32, 36), (37, 39),
           (40, 43), (44, 47), (48, 51), (52, 55), (56, 60), (61, 65), (65, 70), (71, 75), (76, 78)]
"""The phrases (first and last bar, 1-based) - the breathing units of the performance."""
