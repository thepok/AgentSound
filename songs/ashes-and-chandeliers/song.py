"""Ashes and Chandeliers - an original epic in four parts (symphonic rock, instrumental), in the spirit of a 70s rock
opera: a piano ballad, a mock-operatic choir drama, the band with a harmonized guitar orchestra, a huge orchestral
finale that falls away to the solo piano. Nothing is lifted from any record: the theme, harmony, riffs and form are
this song's own. Build:
    python -m agentsound build songs/ashes-and-chandeliers

  I   Candlelight (C minor, 72 BPM, rubato)
      intro    4  the hero piano alone: rolled chords in the pedal, the curtain motif hinted
      theme    8  the theme (G4 leaping a sixth to Eb5, sighing down) harmonized by the pianist; the basses and
                  cellos join softly in bar 5
      theme2   8  the theme again with a string pad and a cello counter-line, now closing on the tonic
      middle   8  Eb major: a lyrical middle, the piano higher, violins double it, horns and an 'oh' choir under
      return   6  the theme's first phrase, fuller - then an unresolved Ab major chord swells, ritardando, fermata
  II  The Masquerade (E minor, 112 -> 3/4 -> accelerando to 138)
      stab     4  subito: staccato piano chords, pizzicato, timpani
      calls   16  call and response: the male choir calls the motif (f / ff), the women answer (p / pp), orchestra
                  stabs (strings staccato + brass marcato + timpani); then both choirs together, crescendo, a stop
      masque  12  3/4 mock-operatic waltz: flutes / oboe tune (the motif in G major), pizzicato oom-pah-pah, the
                  choir's staccato 'ah' on 2 and 3, bassoons
      ascent   8  the choir enters voice by voice over a B pedal, tremolo strings, timpani roll, cymbal swell,
                  accelerando into a fermata on E major (V of A minor)
  III The Stampede (A minor, 138)
      riff     4  the band kicks in: the riff on double-tracked guitars, bass and drums
      anthem   8  the guitar orchestra: the theme on two hero guitars in thirds, organ, chugging rhythm guitars
      anthem2  8  three guitars (a third above and below), the strings join with a staccato ostinato
      solo    12  the lead guitar's solo (guitarist.lead: bends, slides, vibrato - budgeted), the harmony guitars
                  join for its last two bars
      riff2    4  the riff with the brass doubling it
      break    2  band hits, a tom run and a timpani roll, ritardando
  IV  Curtain (C major, 76 -> 60)
      finale   8  the theme in major, tutti: violins in octaves, choir, horns, the guitar orchestra, band, timpani
      summit   4  the motif climbs to C6 (Ab - Bb - C), the last tutti chord
      fall     2  the tam-tam; the orchestra drops to pianissimo, the hall rings
      coda     6  the piano alone with the motif in C minor, soft strings, a rolled C major chord with a fermata

CREDITS: Salamander Grand Piano V3 (Alexander Holm, CC-BY 3.0); Sonatina Symphonic Orchestra 4.0 (Mattias Westlund,
Peter Eastman; CC Sampling Plus 1.0); Virtual Playing Orchestra 3 (Paul Battersby); VSCO 2 CE (Versilian Studios,
CC0); No Budget Orchestra 2 (CC-BY-SA 4.0); MuseScore General SoundFont (taiko); Karoryfer Big Rusty Drums /
Growlybass (CC0); FreePats FSBS guitars (CC0); Karoryfer Emilyguitar (CC0); FreePats rock organ (CC0); Voxengo IM
Reverbs; Lexicon 224XL IRs (Little Devil); Jester Emerald / Brutal cabinet IRs.
"""
from agentsound import *
from agentsound import articulation as art, bands, mastering, patches
from agentsound import drummer, bassist, guitarist as gtr
from agentsound.bandlib import orchestra as orch
from agentsound.humanize import touch
from agentsound.patches import hero_guitar as hero, hero_piano
from agentsound.theory import note as nn

ANALYSIS = {'profile': 'film'}
METADATA = {'title': 'Ashes and Chandeliers', 'artist': 'AgentSound', 'album': 'Curtain Calls',
            'genre': 'Symphonic Rock', 'year': 2026,
            'comment': 'An original epic in four parts: Candlelight, The Masquerade, The Stampede, Curtain'}
COVER = {'style': 'classical', 'palette': 'noir', 'title': 'ASHES AND CHANDELIERS',
         'subtitle': 'AgentSound', 'seed': 11}

# The mix engineer's moves (MIX.md: every move with its reason and the numbers before / after). The melody changes
# hands part by part (piano -> choirs -> flutes -> the guitar orchestra -> the tutti), so the balance was judged per
# part by hand; the whole-song mid / presence surplus is carved where it is not the tune.
MIX = {
    # the lead guitar's fader back up after its presence dip (louder, not harsher); the kit trimmed for headroom (it
    # peaked +2.7 dBFS before the master, A&R #3) - the guitars carry the wall now
    'trim': {'gtr1': 1.0, 'kit': -1.5},
    'ride': {
        # the wall of guitars (A&R #3): the rhythm pair was 2.3-4 dB under the kit and under the bass guitar in
        # anthem / anthem2 / solo - up 2.5-3 dB there, the riff guitars up 3 (the riff hits harder than the fermata)
        'gtr_l': {'riff': 3.5, 'anthem': 2.5, 'anthem2': 3.0, 'solo': 3.5, 'riff2': 3.0, 'finale': -0.5, 'summit': -1.5},
        'gtr_r': {'riff': 3.5, 'anthem': 2.5, 'anthem2': 3.0, 'solo': 3.5, 'riff2': 3.0, 'finale': -0.5, 'summit': -1.5},
        # the lead guitar a little further in front where the kit came within 1.4-1.7 dB of it; the solo is Part III's
        # peak (A&R #2)
        'gtr1': {'anthem': 1.5, 'anthem2': 1.0, 'solo': 1.5, 'finale': 1.0, 'summit': 1.0},
        # anthem was Part III's dip (-15 LUFS after the riff): the organ's held chords under the guitar orchestra
        'organ': {'anthem': 3.0, 'anthem2': 1.5},
        # the finale is the peak of the piece: its tune carriers up (the tune is voiced in three octaves now)
        'violins1': {'ascent': -1.0, 'finale': 1.5, 'summit': 0.5},
        'violins2': {'finale': 1.5, 'summit': 0.5},
        'trumpets': {'finale': 1.5, 'summit': -1.5},
        'horns': {'ascent': -1.5, 'finale': 1.5, 'summit': -1.0},
        'cellos': {'finale': 1.0},
        # the finale's chords are the large chorus' lower voices: back a little (mid +4.6 / +8.1 vs film)
        'choir': {'ascent': -1.5, 'finale': -1.0, 'summit': -2.0},
        'choir_f': {'ascent': -1.5, 'summit': -1.5},
        # the E major fermata must not out-shout the band's arrival (A&R #2): the struck piano chord and the
        # choirs a little back in the ascent, the kit forward on the riffs
        'piano': {'ascent': -4.0},
        'kit': {'riff': 1.5, 'solo': 1.0, 'riff2': 1.0},
        # the thinned finale lost its bottom (bass -2.8 vs film): the bass guitar and the basses back up - still
        # 3 dB+ under the tune
        'basses': {'finale': 2.0, 'summit': 2.5},
        # the calls: the male choir's call against the orchestra stabs
        'choir_m': {'calls': 1.0, 'ascent': -1.5, 'summit': -1.5},
        # the bass guitar was the second-loudest part of Part III (A&R #3): 2 dB down, and under the finale's tune
        'bass': {'riff': -2.0, 'anthem': -2.0, 'anthem2': -2.0, 'solo': -1.5, 'riff2': -2.0, 'finale': 1.5, 'summit': 3.0},
        'trombones': {'summit': -1.0},
        # Part III was dry and narrow (reverb -15..-18 LU, width above 150 Hz 22-29 % vs the film space -13 LU / 30 %):
        # the returns up while the band plays - the guitar orchestra blooms in the plate, the kit in its room
        'plate': {'riff': 4.0, 'anthem': 6.0, 'anthem2': 6.0, 'solo': 6.0, 'riff2': 4.0, 'break': 4.0},
        'hall': {'riff': 3.0, 'anthem': 5.5, 'anthem2': 4.0, 'solo': 6.0, 'riff2': 3.0, 'break': 3.0},
        'room': {'riff': 2.0, 'anthem': 3.0, 'anthem2': 3.0, 'solo': 3.0, 'riff2': 2.0, 'break': 2.0},
    },
    'eq': {
        # the mid / presence surplus (mid +4.3, presence +3.5 vs the film balance): the hall return's honk and edge,
        # then the biggest contributors - a small dip on the lead (its fader comes up), more on what is not the tune
        'hall': [{'freq': 1200, 'gain': -2.5, 'q': 0.6}, {'freq': 4000, 'gain': -1.5, 'q': 0.8}],
        'gtr1': [{'freq': 2600, 'gain': -1.5, 'q': 0.8}, {'freq': 1100, 'gain': -1.5, 'q': 0.7},
                 {'freq': 4200, 'gain': -1.5, 'q': 1.0}],
        'violins2': [{'freq': 3500, 'gain': -1.5, 'q': 1.0}],
        'violins1': [{'freq': 4500, 'gain': -1.5, 'q': 0.9}, {'freq': 2800, 'gain': -1.5, 'q': 1.0}],
        'gtr2': [{'freq': 2500, 'gain': -1.5, 'q': 0.9}, {'freq': 3800, 'gain': -1.5, 'q': 1.0}],
        'gtr3': [{'freq': 2500, 'gain': -1.5, 'q': 0.9}, {'freq': 3800, 'gain': -1.5, 'q': 1.0}],
        'choir': [{'freq': 1300, 'gain': -1.5, 'q': 0.8}],
        # the wall came up 3 dB (A&R #3): its fizz does not - a second dip at 3.3 kHz
        'gtr_l': [{'freq': 4500, 'gain': -1.5, 'q': 0.9}, {'freq': 3300, 'gain': -1.5, 'q': 1.0}],
        'gtr_r': [{'freq': 4500, 'gain': -1.5, 'q': 0.9}, {'freq': 3300, 'gain': -1.5, 'q': 1.0}],
        'drum_bus': [{'freq': 3500, 'gain': -1.5, 'q': 0.9}],
        'bass': [{'freq': 3000, 'gain': -2.0, 'q': 0.8}],      # the drive's fizz, not its growl
    },
}


# ============================================================================================ material helpers

def mel(rows, length, shift=0.0, transpose=0):
    """A Clip from (start, dur, pitch[, vel]) rows (vel default 90)."""
    out = []
    for r in rows:
        v = r[3] if len(r) > 3 else 90
        out.append((r[0] + shift, r[1], nn(r[2]) + transpose, v))
    return Clip(out, length=length)


def chord_at(prog, beat):
    for st, ln, c in prog:
        if st - 1e-6 <= beat < st + ln - 1e-6:
            return c
    return list(prog)[-1][2]


def harmony(line, prog, voices=3, floor=48, gap=3):
    """Homophonic block harmony under a line (a choir / brass section): each note gets the chord tones below it
    (of the chord sounding at its onset), at least `gap` semitones apart, never under `floor`."""
    out = []
    for n in line:
        c = chord_at(prog, n.start)
        pcs = set(c.pcs)
        out.append((n.start, n.dur, n.pitch, n.vel))
        p, got = n.pitch - gap, 0
        last = n.pitch
        while got < voices - 1 and p >= floor:
            if p % 12 in pcs and last - p >= gap:
                out.append((n.start, n.dur, p, max(1, round(n.vel * 0.88))))
                last, got = p, got + 1
                p -= gap
            else:
                p -= 1
    return Clip(out, length=line.length)


def third(line, key, steps=-2):
    """The line moved by diatonic steps (a third below = -2, above = +2); chromatic notes follow their neighbour."""
    k = Key(key) if isinstance(key, str) else key
    out = []
    for n in line:
        p = k.snap(n.pitch)
        q = k.transpose(p, steps) + (n.pitch - p)
        out.append((n.start, n.dur, q, n.vel))
    return Clip(out, length=line.length)


def broken(prog, vel=60, low=36, top=64, seed=0):
    """The ballad pianist's left hand: rolling broken chords in 8ths (root, 5th, octave, 10th, 12th ...), the 1 and
    the 3 leaning in, a 4-bar arc, every note a little different."""
    import random
    rnd = random.Random(seed)
    out = []
    for st, ln, c in prog:
        r = c.bass_note(low=low)
        third_ = 3 if c.is_minor else 4
        fifth = 6 if 'dim' in c.quality or 'b5' in c.quality else 7
        up = [r, r + fifth, r + 12, r + 12 + third_, r + 12 + fifth, r + 12 + third_, r + 12, r + fifth]
        up = [p if p <= top else p - 12 for p in up]
        k = 0
        t = 0.0
        while t < ln - 1e-6:
            pos = st + t
            arc = 0.9 + 0.2 * abs(((pos / 16.0) % 1.0) - 0.5) * -2 + 0.1
            acc = 1.18 if abs(t % 2.0) < 1e-6 else (0.8 if (t % 1.0) > 0.25 else 0.92)
            v = vel * acc * arc * (1 + rnd.uniform(-0.06, 0.06))
            out.append((pos, 0.9 if t + 0.5 < ln else 0.5, up[k % len(up)], max(20, min(110, round(v)))))
            k += 1
            t += 0.5
    return Clip(out, length=prog.length)


def pads(prog, register, voices, vel):
    """Divisi chord tones of each chord inside a narrow register (a section's own share of the harmony): the most
    different pitch classes, no seconds, the smallest movement from the chord before."""
    from itertools import combinations
    import math
    lo, hi = nn(register[0]), nn(register[1])
    out, prev = [], None
    for i, (st, ln, c) in enumerate(prog):
        cand = [p for p in range(lo, hi + 1) if p % 12 in c.pcs]
        best, best_cost = None, None
        for comb in combinations(cand, min(voices, len(cand))):
            if any(b - a < 3 for a, b in zip(comb, comb[1:])):
                continue
            cost = -12 * len({p % 12 for p in comb})
            cost += sum(min(abs(p - q) for q in prev) for p in comb) if prev else -0.05 * sum(comb)
            if best_cost is None or cost < best_cost:
                best, best_cost = comb, cost
        best = best or tuple(cand[-voices:])
        arc = 0.84 + 0.3 * math.sin(math.pi * ((st / 16.0) % 1.0 + 0.125))    # a 4-bar phrase arc
        v = vel * arc * (1.06 if i % 2 == 0 else 0.95)
        out += [(st, ln, p, max(1, min(127, round(v * (1.0 if p == best[-1] else 0.9))))) for p in best]
        prev = best
    return Clip(out, length=prog.length)


# ============================================================================================ the themes
# The curtain motif: an upbeat G4, a sixth up to a held Eb5, a sigh down - then the answer climbs higher.
THEME = [
    (0, 0.5, 'G4'), (0.5, 2.0, 'Eb5'), (2.5, 0.5, 'D5'), (3, 1, 'C5'),
    (4, 1.5, 'C5'), (5.5, 0.5, 'Bb4'), (6, 1, 'Ab4'), (7, 0.5, 'G4'), (7.5, 0.5, 'Ab4'),
    (8, 1, 'C5'), (9, 2, 'F5'), (11, 0.5, 'Eb5'), (11.5, 0.5, 'D5'),
    (12, 2, 'D5'), (14, 1.5, 'B4'),
    (16, 0.5, 'G4'), (16.5, 1.5, 'Eb5'), (18, 1.5, 'G5'), (19.5, 0.5, 'F5'),
    (20, 1, 'F5'), (21, 1, 'D5'), (22, 2, 'Eb5'),
]
THEME_HALF = [(24, 1.5, 'C5'), (25.5, 0.5, 'D5'), (26, 1, 'Eb5'), (27, 1, 'Ab4'), (28, 3, 'G4')]
THEME_FULL = [(24, 1.5, 'C5'), (25.5, 0.5, 'Bb4'), (26, 1, 'Ab4'), (27, 1, 'B4'), (28, 3.5, 'C5')]
P_THEME = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Cm Bb:0.5 Eb:0.5 Ab:0.5 Fm7:0.5 G'
P_THEME2 = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Cm Bb:0.5 Eb:0.5 Ab:0.5 G7:0.5 Cm'

INTRO_RH = [(2, 0.5, 'G4'), (2.5, 1.5, 'Eb5'), (6, 1, 'D5'), (7, 1, 'C5'), (10, 0.5, 'C5'), (10.5, 1.5, 'F5'),
            (12, 2, 'D5'), (14, 2, 'B4')]
P_INTRO = 'Cm Ab/C Fm/C G7sus4:0.5 G7:0.5'

MIDDLE = [
    (0, 1.5, 'Bb5'), (1.5, 0.5, 'G5'), (2, 1, 'Eb5'), (3, 1, 'F5'),
    (4, 1.5, 'F5'), (5.5, 0.5, 'D5'), (6, 2, 'Bb4'),
    (8, 1, 'C5'), (9, 1, 'Eb5'), (10, 1, 'G5'), (11, 1, 'Bb5'),
    (12, 3, 'Ab5'), (15, 0.5, 'G5'), (15.5, 0.5, 'F5'),
    (16, 1.5, 'Eb5'), (17.5, 0.5, 'F5'), (18, 1, 'Ab5'), (19, 1, 'C6'),
    (20, 2, 'Bb5'), (22, 1, 'Ab5'), (23, 1, 'G5'),
    (24, 1, 'G5'), (25, 1, 'Eb5'), (26, 1.5, 'C5'), (27.5, 0.5, 'D5'),
    (28, 2, 'D5'), (30, 1, 'B4'), (31, 1, 'D5'),
]
P_MIDDLE = 'Eb Bb/D Cm Ab Fm7 Bb7sus4:0.5 Bb7:0.5 Eb/G:0.5 Ab:0.5 Fm6/Ab:0.5 G7:0.5'

RETURN = [
    (0, 0.5, 'G4'), (0.5, 2.0, 'Eb5'), (2.5, 0.5, 'D5'), (3, 1, 'C5'),
    (4, 1.5, 'C5'), (5.5, 0.5, 'Bb4'), (6, 1, 'Ab4'), (7, 0.5, 'G4'), (7.5, 0.5, 'Ab4'),
    (8, 1, 'C5'), (9, 2, 'F5'), (11, 0.5, 'Eb5'), (11.5, 0.5, 'D5'),
    (12, 2, 'D5'), (14, 1.5, 'B4'),
    (16, 1, 'Eb5'), (17, 1, 'D5'), (18, 2, 'C5'),
]
P_RETURN = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Ab:2'

CODA = [(0, 0.5, 'G4'), (0.5, 2, 'Eb5'), (2.5, 0.5, 'D5'), (3, 1, 'C5'),
        (4, 2, 'C5'), (6, 1, 'Bb4'), (7, 1, 'Ab4'),
        (8, 1, 'Ab4'), (9, 2, 'C5'), (11, 1, 'F4'),
        (12, 2, 'G4'), (14, 2, 'D5'),
        (16, 2, 'C5'), (18, 2, 'B4')]
P_CODA = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Ab:0.5 G7:0.5'

# ---- Part III / IV: the theme in A minor (guitars) and in C major (finale)
P_ANTHEM = 'Am F Dm E7sus4:0.5 E7:0.5 Am G:0.5 C:0.5 F:0.5 Dm7:0.5 E'
P_ANTHEM2 = 'Am F Dm E7sus4:0.5 E7:0.5 Am G:0.5 C:0.5 F:0.5 E7:0.5 Am'
FINALE = [
    (0, 0.5, 'G4'), (0.5, 2.0, 'E5'), (2.5, 0.5, 'D5'), (3, 1, 'C5'),
    (4, 1.5, 'C5'), (5.5, 0.5, 'B4'), (6, 1, 'A4'), (7, 0.5, 'G4'), (7.5, 0.5, 'A4'),
    (8, 1, 'C5'), (9, 2, 'F5'), (11, 0.5, 'E5'), (11.5, 0.5, 'D5'),
    (12, 2, 'D5'), (14, 1.5, 'B4'),
    (16, 0.5, 'G4'), (16.5, 1.5, 'E5'), (18, 1.5, 'G5'), (19.5, 0.5, 'F5'),
    (20, 1, 'F5'), (21, 1, 'D5'), (22, 2, 'E5'),
    (24, 1.5, 'C5'), (25.5, 0.5, 'D5'), (26, 1, 'F5'), (27, 1, 'D5'),
    (28, 4, 'C5'),
]
P_FINALE = 'C Am F Gsus4:0.5 G:0.5 C Bb:0.5 C:0.5 Ab:0.5 Bb:0.5 C'
SUMMIT = [(0, 0.5, 'Eb5'), (0.5, 2, 'C6'), (2.5, 0.5, 'Bb5'), (3, 1, 'Ab5'),
          (4, 0.5, 'F5'), (4.5, 2, 'D6'), (6.5, 0.5, 'C6'), (7, 1, 'Bb5'),
          (8, 2, 'C6'), (10, 1, 'D6'), (11, 1, 'E6'),
          (12, 4, 'C6')]
P_SUMMIT = 'Ab Bb Csus4:0.5 C:0.5 C'

# ---- Part II material (E minor)
P_STAB = 'Em Em C/E B7/D#'
P_CALL1 = 'Em Em/D C B7'
P_CALL2 = 'Am Am/G F#m7b5 B7'
P_CALL3 = 'Em G/D C Am/C'
P_CALL4 = 'C D B7sus4 B7'
CALL1 = [(0, 0.5, 'B3'), (0.5, 1.5, 'G4'), (2, 1, 'F#4'), (3, 1, 'E4'), (4, 2, 'D4'), (6, 1.5, 'B3')]
ANSWER1 = [(8, 0.5, 'G4'), (8.5, 1.5, 'E5'), (10, 1, 'D5'), (11, 1, 'C5'), (12, 1.5, 'B4'), (13.5, 0.5, 'C5'),
           (14, 2, 'D#5')]
CALL2 = [(0, 0.5, 'E3'), (0.5, 1.5, 'C4'), (2, 1, 'B3'), (3, 1, 'A3'), (4, 2, 'G3'), (6, 1.5, 'E3')]
ANSWER2 = [(8, 0.5, 'C5'), (8.5, 1.5, 'A5'), (10, 1, 'F#5'), (11, 1, 'E5'), (12, 1.5, 'D#5'), (13.5, 0.5, 'E5'),
           (14, 2, 'F#5')]
CALL3M = [(0, 0.5, 'B3'), (0.5, 1.5, 'G4'), (2, 1, 'F#4'), (3, 1, 'E4'),
          (8, 0.5, 'C4'), (8.5, 1.5, 'G4'), (10, 1, 'F#4'), (11, 1, 'E4')]
CALL3F = [(4, 0.5, 'D5'), (4.5, 1.5, 'B5'), (6, 1, 'A5'), (7, 1, 'G5'),
          (12, 0.5, 'E5'), (12.5, 1.5, 'C6'), (14, 1, 'B5'), (15, 1, 'A5')]
TUTTI4 = [(0, 2, 'G5'), (2, 2, 'E5'), (4, 2, 'A5'), (6, 2, 'F#5'), (8, 3, 'B5'), (11, 1, 'A5'), (12, 2, 'A5'),
          (14, 1, 'D#5')]
P_MASQUE = 'G D7/F# G/D Em Am D7 G B7 Em C F#m7b5 B7'
MASQUE = [(0, 1, 'D5'), (1, 1.5, 'B5'), (2.5, 0.5, 'A5'),
          (3, 1, 'A5'), (4, 1, 'F#5'), (5, 1, 'D5'),
          (6, 1, 'G5'), (7, 0.5, 'A5'), (7.5, 0.5, 'B5'), (8, 1, 'D6'),
          (9, 2, 'E6'), (11, 0.5, 'D6'), (11.5, 0.5, 'B5'),
          (12, 1, 'C6'), (13, 1, 'A5'), (14, 1, 'E5'),
          (15, 1, 'F#5'), (16, 1, 'A5'), (17, 1, 'C6'),
          (18, 2, 'B5'), (20, 1, 'G5'),
          (21, 1, 'F#5'), (22, 1, 'A5'), (23, 1, 'D#5'),
          (24, 0.5, 'B4'), (24.5, 1.5, 'G5'), (26, 1, 'F#5'),
          (27, 1, 'E5'), (28, 1, 'G5'), (29, 1, 'C6'),
          (30, 1.5, 'C6'), (31.5, 0.5, 'A5'), (32, 1, 'F#5'),
          (33, 2, 'D#5'), (35, 1, 'B4')]
P_ASCENT = 'Em/B C/B Am/B B7 C D B7sus4 E'

# ---- Part III: the riff, the solo
RIFF_ROOTS = [(0, 0.5, 'A2', 'p'), (0.5, 0.5, 'A2', 'p'), (1, 0.5, 'A2', 'p'), (1.5, 0.5, 'C3', ''),
              (2, 1, 'D3', ''), (3, 0.5, 'E3', ''), (3.5, 0.5, 'D3', ''),
              (4, 0.5, 'A2', 'p'), (4.5, 0.5, 'A2', 'p'), (5, 0.5, 'A2', 'p'), (5.5, 0.5, 'G2', ''),
              (6, 0.5, 'G2', ''), (6.5, 1, 'F2', ''), (7.5, 0.5, 'E2', '')]
P_RIFF = 'Am:0.375 C:0.125 D:0.375 E:0.125 Am:0.375 G:0.25 F:0.375'
P_SOLO = 'Am F G Am F G Em Am Dm E7 Am E7'
SOLO = [
    # bars 1-4: the motif, answered
    (0, 0.5, 'E5'), (0.5, 1.5, 'C6'), (2, 0.5, 'B5'), (2.5, 1.5, 'A5'),
    (4.5, 0.5, 'A5'), (5, 0.5, 'G5'), (5.5, 0.5, 'F5'), (6, 2, 'A5'),
    (8.5, 0.5, 'D5'), (9, 0.5, 'G5'), (9.5, 0.5, 'A5'), (10, 1.5, 'B5'), (11.5, 0.5, 'D6'),
    (12, 3, 'C6'), (15, 0.5, 'B5'), (15.5, 0.5, 'A5'),
    # bars 5-8: climbing, faster
    (16, 0.5, 'C6'), (16.5, 0.5, 'A5'), (17, 0.5, 'F5'), (17.5, 0.5, 'A5'), (18, 1, 'C6'), (19, 1, 'A5'),
    (20, 0.5, 'B5'), (20.5, 0.5, 'G5'), (21, 0.5, 'D5'), (21.5, 0.5, 'G5'), (22, 1.5, 'B5'), (23.5, 0.5, 'C6'),
    (24, 2, 'B5'), (26, 0.5, 'G5'), (26.5, 0.5, 'E5'), (27, 1, 'G5'),
    (28, 0.5, 'A5'), (28.5, 0.5, 'C6'), (29, 0.5, 'E6'), (29.5, 2.5, 'D6'),
    # bars 9-12: the peak and the fall back to the riff
    (32, 3, 'D6'), (35, 0.5, 'C6'), (35.5, 0.5, 'A5'),
    (36, 1.5, 'B5'), (37.5, 0.5, 'G#5'), (38, 2, 'E5'),
    (40, 0.5, 'E5'), (40.5, 1.5, 'C6'), (42, 0.5, 'B5'), (42.5, 1.5, 'A5'),
    (44, 1, 'B5'), (45, 1, 'G#5'), (46, 2, 'E5'),
]


def build() -> Song:
    s = Song('Ashes and Chandeliers', tempo=72, key='C minor', seed=17, tail=9)
    # ------------------------------------------------------------------------------------ form
    intro = s.section('intro', bars=4)
    theme = s.section('theme', bars=8)
    theme2 = s.section('theme2', bars=8)
    middle = s.section('middle', bars=8)
    ret = s.section('return', bars=6)
    stab = s.section('stab', bars=4)
    calls = s.section('calls', bars=16)
    masque = s.section('masque', bars=12, meter=(3, 4))
    ascent = s.section('ascent', bars=8)
    riff = s.section('riff', bars=4)
    anthem = s.section('anthem', bars=8)
    anthem2 = s.section('anthem2', bars=8)
    solo = s.section('solo', bars=12)
    riff2 = s.section('riff2', bars=4)
    brk = s.section('break', bars=2)
    finale = s.section('finale', bars=8)
    summit = s.section('summit', bars=4)
    fall = s.section('fall', bars=2)
    coda = s.section('coda', bars=6)

    # ------------------------------------------------------------------------------------ tempo map
    s.rubato(intro, depth=0.05, phrase='lean')
    s.rubato(theme, depth=0.035, phrase='arch')
    s.rubato(theme2, depth=0.03, phrase='arch')
    s.rubato(middle, depth=0.04, phrase='wave')
    s.ritardando((ret.bar(3), ret.bar(5)), to=0.78, a_tempo=False)
    s.fermata(ret.bar(5), hold=3)
    s.set_tempo(stab, 112)
    s.accelerando((ascent.start, ascent.bar(7)), bpm=138)
    s.fermata(ascent.bar(7), hold=4)
    s.ritardando((brk.start, brk.end), bpm=96, a_tempo=False)
    s.set_tempo(finale, 76)
    s.ritardando((summit.bar(2), summit.end), to=0.82, a_tempo=False)
    s.set_tempo(fall, 60)
    s.rubato((coda.start, coda.bar(4)), depth=0.05, phrase='arch')
    s.ritardando((coda.bar(4), coda.bar(5)), to=0.72, a_tempo=False)
    s.fermata(coda.bar(5), hold=4)

    def bpm(at):
        return s.tempo_at(float(getattr(at, 'start', at)))

    # ------------------------------------------------------------------------------------ the ensemble
    o = bands.film_orchestra(s, ids={'drums': 'taiko'})          # sets the hall + the film master first
    b = bands.rock_band(s, without=('lead',), keys='organ', gain='high', ids={'drums': 'kit', 'keys': 'organ'})
    piano = s.track('piano', 'sampled/hero_piano', gain_db=-3.0)
    # the two line choirs start 100 ms into their "ah" samples (the recordings take 50-180 ms to reach -3 dB): with
    # the speaking velocities of speak() below the calls land on their upbeats instead of swelling in (A&R #4)
    choir_m = s.track('choir_m', patches.get('sampled/choir_male').but(start=100), pan=-0.3, gain_db=-2.0)
    choir_f = s.track('choir_f', patches.get('sampled/choir').but(start=100), pan=0.3, gain_db=-5.0)
    choir_oh = s.track('choir_oh', 'sampled/choir_oh', gain_db=-8.0)
    g1 = s.track('gtr1', 'layered/hero_guitar_heavy', pan=0.0, gain_db=-1.0)
    g2 = s.track('gtr2', 'layered/hero_guitar', pan=-0.65, gain_db=-4.0)        # the orchestra wide (A&R #3)
    g3 = s.track('gtr3', 'layered/hero_guitar', pan=0.65, gain_db=-5.0)
    P = lambda role, clip, at, **kw: orch.perform(o, role, clip, at, seed=sum(map(ord, role)) + int(s._at(at)), **kw)  # noqa
    K = orch.PERCUSSION_KEYS
    pmem = pianist.Memory()
    pmem.save(coda.bar(4))                     # the pianist keeps its one big figure for the last cadence

    def piano_part(melody_rows, prog_spec, sec, lo, hi, *, key=None, lh_vel=58, shift=0, style='ballad',
                   density=0.55, seed=1, climax=False, lh=True, bars=None, lead_in=False, section_end=True):
        prog = s.prog(prog_spec)
        m = touch(mel(melody_rows, prog.length, transpose=shift), lo, hi)
        arr = pianist.arrange(m, prog, bpm=bpm(sec), key=key or s.key, style=style, density=density, seed=seed,
                              lh=None, climax=climax, lead_in=lead_in, section_end=section_end,
                              devices={'close': 2, 'octave': 1.5, 'thirds': 1.5, 'sixths': 1.5, 'drop2': 1},
                              memory=pmem, at=sec.start)
        piano.play(arr.rh, sec)
        if lh:
            piano.play(broken(prog, vel=lh_vel, seed=seed), sec)
        piano.automate('instrument.pedal', arr.pedal(prog, sec))
        return arr, prog

    # =================================================================================== I  CANDLELIGHT
    # intro: rolled chords in the pedal + the motif hinted, very soft
    pi = s.prog(P_INTRO)
    ri = pianist.arrange(touch(mel(INTRO_RH, 16), 40, 70), pi, bpm=72, key=s.key, style='ballad', density=0.4,
                         seed=3, memory=pmem, at=intro.start)
    piano.play(ri.rh, intro)
    rolled = chords(pi, register=('C2', 'G4'), voices=5, vel=46).strum(ms=55, bpm=64)
    piano.play(rolled.vel_pattern([1.0, 0.9, 1.05, 0.95]), intro)
    piano.automate('instrument.pedal', ri.pedal(pi, intro))

    # theme: the piano states it; basses and cellos join softly in bar 5
    _, pt = piano_part(THEME + THEME_HALF, P_THEME, theme, 52, 96, lh_vel=46, seed=11)
    P('cellos', Clip([(n.start, n.dur, n.pitch, n.vel) for n in pt.bass('root', low='C3', vel=44) if n.start >= 16],
           length=32), theme, shapes='swell')
    P('basses', Clip([(n.start, n.dur, n.pitch, n.vel) for n in pt.bass('root', low='C2', vel=42) if n.start >= 16],
                     length=32), theme, shapes='swell')

    # theme2: the string pad and a cello counter-line; the theme closes on the tonic
    _, pt2 = piano_part(THEME + THEME_FULL, P_THEME2, theme2, 58, 104, lh_vel=50, seed=12)
    P('violins2', pads(pt2, ('G4', 'Eb5'), 2, 42), theme2, shapes='swell')
    P('violas', pads(pt2, ('C4', 'G4'), 2, 44), theme2, shapes='swell')
    counter = mel([(2, 2, 'G3'), (4, 2, 'Ab3'), (6, 2, 'C4'), (8, 3, 'C4'), (11, 1, 'Bb3'), (12, 2, 'B3'),
                   (14, 2, 'D4'), (16, 3, 'Eb4'), (19, 1, 'D4'), (20, 2, 'D4'), (22, 2, 'G3'), (24, 2, 'Ab3'),
                   (26, 2, 'F3'), (28, 4, 'G3')], 32)
    P('cellos', touch(counter, 40, 66), theme2)
    P('basses', pt2.bass('root', low='C2', vel=46), theme2, shapes='swell')

    # middle: Eb major, the piano higher; violins double it in the second half; horns and the 'oh' choir under
    _, pm = piano_part(MIDDLE, P_MIDDLE, middle, 60, 106, key='Eb major', lh_vel=52, seed=13, density=0.6)
    vdub = mel([r for r in MIDDLE if r[0] >= 16], 32, transpose=-12)
    P('violins1', touch(vdub, 44, 76), middle)
    P('violins2', pads(pm, ('Bb4', 'G5'), 2, 46), middle, shapes='swell')
    P('violas', pads(pm, ('Eb4', 'Bb4'), 2, 48), middle, shapes='swell')
    P('cellos', pm.bass('root', low='Eb2', vel=50), middle, shapes='swell')
    P('basses', pm.bass('root', low='Eb1', vel=48), middle, shapes='swell')
    P('horns', pads(pm, ('Bb2', 'G3'), 3, 44), middle, shapes='swell')
    choir_oh.play(chords(pm, register=('G3', 'Eb5'), voices=4, vel=58), middle)
    choir_oh.automate('instrument.dynamics', [(middle.start, 0.25), (middle.bar(4), 0.5, 'smooth'),
                                              (middle.bar(7), 0.35, 'smooth'), (ret.start, 0.3, 'smooth')])

    # return: the first phrase fuller, then the unresolved Ab chord swells and hangs (fermata)
    _, pr = piano_part(RETURN, P_RETURN, ret, 62, 108, lh_vel=54, seed=14)
    P('violins1', touch(mel([r for r in RETURN if r[0] < 16], 24), 50, 88), ret)
    P('violins2', pads(pr, ('G4', 'Eb5'), 2, 56), ret, shapes='swell')
    P('violas', pads(pr, ('C4', 'G4'), 2, 58), ret, shapes='swell')
    P('cellos', pr.bass('root', low='C3', vel=60), ret, shapes='swell')
    P('basses', pr.bass('root', low='C2', vel=58), ret, shapes='swell')
    P('horns', Clip([(16, 7.5, p, 70) for p in (nn('Ab2'), nn('Eb3'), nn('C4'))], length=24), ret, shapes='cresc')
    P('violins1', Clip([(16, 7.5, nn('Ab5'), 60), (16, 7.5, nn('C6'), 56)], length=24), ret,
      articulations='tremolo', shapes='cresc')
    piano.play(Clip([(16, 7.5, p, 84) for p in (nn('Ab1'), nn('Ab2'), nn('Eb3'), nn('C4'), nn('Eb4'), nn('Ab4'))],
                    length=24).strum(ms=60, bpm=60), ret)
    P('timpani', Clip([(20, 3.8, nn('Eb2'), 70)], length=24), ret, articulations='roll')
    orch.ring(o, ret.bar(5), length=3, db=3, roles=['violins1', 'violins2', 'violas', 'cellos', 'horns'])

    # =================================================================================== II  THE MASQUERADE
    # stab: subito staccato piano chords, pizzicato strings, timpani
    ps = s.prog(P_STAB)
    st = []
    for i, (t, ln, c) in enumerate(ps):
        vox = [p for p in c.notes(3)] + [c.notes(4)[0]]
        for k in range(8):
            if i == 3 and k >= 6:
                break
            v = 50 + i * 12 + (16 if k % 2 == 0 else 0) + (10 if k == 0 else 0)
            for p in vox:
                st.append((t + k * 0.5, 0.22, p, min(118, v)))
    piano.play(Clip(st, length=16), stab)
    piano.automate('instrument.pedal', [(stab.start - 0.05, 0, 'step')])
    P('violas', Clip([(t, 0.5, c.notes(3)[1], 60 + i * 10) for i, (t, ln, c) in enumerate(ps)] +
                     [(t + 2, 0.5, c.notes(3)[2], 56 + i * 10) for i, (t, ln, c) in enumerate(ps)], length=16),
      stab, articulations='pizzicato')
    P('basses', Clip([(t, 1, c.bass_note(low='E1'), 70 + i * 10) for i, (t, ln, c) in enumerate(ps)], length=16),
      stab, articulations='pizzicato')
    P('timpani', Clip([(0, 1, nn('E2'), 90), (4, 1, nn('E2'), 96), (8, 1, nn('E2'), 100), (12, 1, nn('B2'), 108),
                       (14, 1, nn('B2'), 116)], length=16), stab, articulations='hit')

    # calls: call and response
    # The VPO choirs' SFZ attack is 0.625 s x (1 - velocity / 127): a p answer at velocity 40 needs ~0.4 s to speak,
    # longer than the motif's 8th upbeat (268 ms at 112). So the lines SING at a speaking velocity (SPEAK: ~40 ms
    # attack) and the written dynamics move to the track's expression lane (gain = e^2, e = vel / SPEAK): every note
    # keeps its written level and its arc, only the onset changes (A&R #4).
    SPEAK = 120
    expr = {choir_m.id: [], choir_f.id: []}

    def speak(track, notes):
        """Play (song-beat) notes at the speaking velocity; their written velocities go to the expression lane,
        moved over the last 80 ms before each onset (the previous note's tail carries the change)."""
        notes = sorted(notes, key=lambda n: n.start)
        track.play(Clip([(n.start, n.dur, n.pitch, SPEAK) for n in notes], length=0), 0)
        lane = expr[track.id]
        onsets = {}
        for n in notes:
            onsets[round(n.start, 4)] = max(onsets.get(round(n.start, 4), 0), n.vel)
        for t, v in sorted(onsets.items()):
            d = 0.08 * bpm(t) / 60.0
            e = max(0.12, min(1.0, v / SPEAK))
            if lane and t - d <= lane[-1][0] + 1e-4:
                continue                                 # chords / humanized voices of one onset: the first rules
            lane += [(t - d, lane[-1][1] if lane else e), (t - 0.3 * d, e)]

    def choir_line(track, rows, prog, at, lo, hi, voices=3, floor=43, lead_ms=35):
        line = touch(mel(rows, prog.length), lo, hi)
        blk = harmony(line, prog, voices=voices, floor=floor)
        blk = orch.lead(Clip([(n.start + s._at(at), n.dur, n.pitch, n.vel) for n in blk],
                             length=prog.length + s._at(at)), bpm(at), lead_ms)
        speak(track, art.humanize_starts(blk, bpm(at), 10, seed=int(s._at(at))))
        return line

    def call_onsets(rows, at, role, dv, art_='marcato', shift=0):
        """Double the motif's upbeat and the note it leaps to (every phrase of a call) so its rhythm reads: horns
        marcato under the men, pizzicato violins under the women."""
        rr = [r for r in rows]
        pick = []
        for i, r in enumerate(rr):
            if r[1] <= 0.5 and i + 1 < len(rr) and abs(rr[i + 1][0] - (r[0] + r[1])) < 1e-6:
                pick += [(r[0], 0.45, nn(r[2]) + shift, dv), (rr[i + 1][0], 0.9, nn(rr[i + 1][2]) + shift, dv + 8)]
        P(role, Clip(pick, length=16), at, articulations=art_)

    def stabs(at, hits, prog, vel=112):
        """Orchestra stabs: strings staccato + brass marcato + timpani on the given beats (relative to at)."""
        rows_str, rows_br, rows_lo, rows_t = [], [], [], []
        for h in hits:
            c = chord_at(prog, h)
            hi = [p for p in c.notes(5)][:3]
            mid = c.notes(4)[:3]
            rows_str += [(h, 0.4, p, vel) for p in hi + mid]
            rows_br += [(h, 0.6, p, vel - 6) for p in c.notes(4)[:3]]
            rows_lo += [(h, 0.5, c.bass_note(low='E2'), vel), (h, 0.5, c.bass_note(low='E2') - 12, vel)]
            rows_t.append((h, 0.8, nn('E2') if c.root in (4, 0) else nn('B2'), min(127, vel + 4)))
        ln = prog.length
        P('violins1', Clip([r for r in rows_str if r[2] >= 67], length=ln), at, articulations='staccato')
        P('violins2', Clip([r for r in rows_str if 60 <= r[2] < 76], length=ln), at, articulations='staccato')
        P('violas', Clip([r for r in rows_str if r[2] < 67], length=ln), at, articulations='staccato')
        P('cellos', Clip([r for r in rows_lo if r[2] >= 36], length=ln), at, articulations='staccato')
        P('basses', Clip([r for r in rows_lo if r[2] < 48], length=ln), at, articulations='staccato')
        P('trumpets', Clip(rows_br, length=ln), at, articulations='marcato')
        P('trombones', Clip([(r[0], r[1], r[2] - 12, r[3]) for r in rows_br], length=ln), at,
          articulations='marcato')
        P('horns', Clip([(r[0], r[1], r[2] - 12, r[3] - 6) for r in rows_br], length=ln), at,
          articulations='marcato')
        P('timpani', Clip(rows_t, length=ln), at, articulations='hit')
        piano.play(Clip([(h, 0.3, p, vel - 20) for h in hits for p in chord_at(prog, h).notes(4)[:3]], length=ln),
                   at)

    c1, c2, c3, c4 = (s.prog(p) for p in (P_CALL1, P_CALL2, P_CALL3, P_CALL4))
    b1, b2, b3, b4 = calls.bar(0), calls.bar(4), calls.bar(8), calls.bar(12)
    # the women's p / pp answers a little louder than before (they dipped to -36 / -38 LUFS: dropouts, A&R #5)
    choir_line(choir_m, CALL1, c1, b1, 84, 110, voices=2)
    call_onsets(CALL1, b1, 'horns', 92)
    choir_line(choir_f, ANSWER1, c1, b1, 50, 74)
    call_onsets(ANSWER1, b1, 'violins1', 52, 'pizzicato')
    stabs(b1, [14, 15, 15.5], c1, 108)
    choir_line(choir_m, CALL2, c2, b2, 96, 124, voices=2)
    call_onsets(CALL2, b2, 'horns', 100)
    choir_line(choir_f, ANSWER2, c2, b2, 44, 68)
    call_onsets(ANSWER2, b2, 'violins1', 46, 'pizzicato')
    stabs(b2, [14, 15, 15.5], c2, 116)
    choir_line(choir_m, CALL3M, c3, b3, 88, 112, voices=2)
    call_onsets(CALL3M, b3, 'horns', 94)
    choir_line(choir_f, CALL3F, c3, b3, 70, 100)
    call_onsets(CALL3F, b3, 'violins1', 70, 'pizzicato')
    stabs(b3, [3.5, 7.5, 11.5, 15.5], c3, 104)
    choir_line(choir_f, TUTTI4, c4, b4, 70, 112, voices=4, floor=53)
    choir_line(choir_m, [(r[0], r[1], nn(r[2]) - 24) for r in TUTTI4], c4, b4, 70, 112, voices=2)
    P('choir', harmony(touch(mel(TUTTI4, 16, transpose=-12), 60, 108), c4, voices=4, floor=48), b4, shapes='cresc')
    stabs(b4, [15], c4, 122)
    P('violins1', pads(c4, ('B5', 'F#6'), 2, 70), b4, articulations='tremolo', shapes='cresc')
    P('violins2', pads(c4, ('D5', 'A5'), 2, 68), b4, articulations='tremolo', shapes='cresc')
    P('violas', pads(c4, ('F#4', 'D5'), 2, 66), b4, articulations='tremolo', shapes='cresc')
    P('cellos', c4.bass('root', low='C3', vel=78), b4, shapes='cresc')
    P('basses', c4.bass('root', low='C2', vel=76), b4, shapes='cresc')
    P('timpani', Clip([(12, 2.9, nn('B2'), 84)], length=16), b4, articulations='roll')
    choir_m.automate('instrument.dynamics', [(b1, 0.72), (b2, 0.9, 'smooth'), (b3, 0.78, 'smooth'),
                                             (b4, 0.6, 'smooth'), (calls.bar(15), 1.0, 'smooth'),
                                             (masque.start, 0.2, 'step')])
    choir_f.automate('instrument.dynamics', [(b1, 0.4), (b2, 0.32, 'smooth'), (b3, 0.7, 'smooth'),
                                             (b4, 0.55, 'smooth'), (calls.bar(15), 1.0, 'smooth'),
                                             (masque.start, 0.62, 'step')])

    # masque: 3/4 mock-operatic waltz
    pq = s.prog(P_MASQUE, meter=masque.meter)
    qm = touch(mel(MASQUE, 36), 64, 104)
    P('flutes', qm, masque)
    P('oboes', Clip([(n.start, n.dur, n.pitch - 12, n.vel - 8) for n in qm if 12 <= n.start < 24 or n.start >= 30],
                    length=36), masque)
    oom, pah, bsn = [], [], []
    for i, (t, ln, c) in enumerate(pq):
        oom.append((t, 0.6, c.bass_note(low='E2'), 78 + (8 if i % 2 == 0 else 0)))
        up = c.notes(4)[:3]
        for bt in (1, 2):
            v = 60 if bt == 1 else 52
            pah += [(t + bt, 0.35, p, v + (i % 4) * 3) for p in up]
        bsn.append((t, 0.4, c.bass_note(low='E2') + 12, 70))
        bsn.append((t + 2, 0.4, c.notes(3)[2], 58))
    P('cellos', Clip(oom, length=36), masque, articulations='pizzicato')
    P('basses', Clip(oom, length=36), masque, articulations='pizzicato')
    P('violas', Clip([r for r in pah if r[2] < 67], length=36), masque, articulations='pizzicato')
    P('violins2', Clip([r for r in pah if r[2] >= 64], length=36), masque, articulations='pizzicato')
    P('bassoons', Clip(bsn, length=36), masque, articulations='staccato')
    P('clarinets', Clip([(n.start, n.dur, n.pitch - 12, n.vel - 14) for n in qm if n.start >= 24], length=36),
      masque)
    # the choir's short 'ah' on 2 and 3: sung at the speaking velocity (it speaks inside the 8th), a little longer
    speak(choir_f, Clip([(r[0] + masque.start - 0.03, 0.55, r[2], r[3] - 6) for r in pah], length=0))
    # back to the written velocities (the ascent's entries and the finale swell in on purpose)
    for tr in (choir_m, choir_f):
        expr[tr.id] += [(ascent.start - 0.5, expr[tr.id][-1][1]), (ascent.start - 0.25, 1.0)]
    P('harp', Clip([(t + k * 0.5, 1.2, c.notes(4 + k // 3)[k % 3], 50 + k * 4) for (t, ln, c) in pq
                    for k in range(6) if t >= 18], length=36), masque)
    P('percussion', Clip([(t, 0.5, K['triangle'], 58) for (t, ln, c) in pq if int(t) % 6 == 0], length=36), masque)

    # ascent: stacked choir entries over the B pedal, tremolo strings, rolls, accelerando into the fermata
    pa = s.prog(P_ASCENT)
    ent = []
    voices = [('E3', 0), ('G3', 4), ('B3', 8), ('E4', 12)]
    rise = {0: [0, 0, 0, 1, 1, 2, 3, 4], 4: [0, 0, 1, 2, 2, 3, 3], 8: [0, 1, 2, 3, 4, 3], 12: [0, 1, 2, 4, 3]}
    k = Key('E minor')
    for pitch, start in voices:
        p0 = nn(pitch)
        steps = rise[start]
        for j, stp in enumerate(steps):
            t = start + j * 4
            if t >= 28:
                break
            ent.append((t, 4.0, k.transpose(k.snap(p0), stp), 62 + t * 1.5))
    ent_m = Clip([e for e in ent if e[2] < nn('C4')], length=32)
    ent_f = Clip([(e[0], e[1], e[2] + 12, e[3]) for e in ent if e[2] >= nn('B3')], length=32)
    choir_m.play(orch.lead(Clip([(e[0] + ascent.start, e[1], e[2], round(e[3])) for e in ent_m], length=0),
                           112, 70), 0)
    choir_f.play(orch.lead(Clip([(e[0] + ascent.start, e[1], e[2], round(e[3])) for e in ent_f], length=0),
                           112, 70), 0)
    # the E major fermata peaks and then dies away into the drummer's pickup: the riff must be the arrival, not a
    # step down from the fermata (A&R #2: fermata -10.1 LUFS, riff -13.7)
    choir_m.automate('instrument.dynamics', [(ascent.start, 0.3), (ascent.bar(7), 1.0, 'smooth'),
                                             (ascent.bar(7) + 0.5, 1.0), (ascent.bar(7) + 3.0, 0.3, 'smooth')])
    choir_f.automate('instrument.dynamics', [(ascent.start + 0.01, 0.3), (ascent.bar(7), 0.8, 'smooth'),
                                             (ascent.bar(7) + 0.5, 0.8), (ascent.bar(7) + 3.0, 0.25, 'smooth')])
    asc_ch = harmony(touch(mel([(16, 4, 'E5'), (20, 4, 'F#5'), (24, 4, 'F#5'), (28, 4, 'G#5')], 32), 70, 118),
                     pa, voices=4, floor=52)
    P('choir', Clip([n for n in asc_ch if n.start < 28], length=32), ascent, shapes='cresc')
    P('choir', Clip([n for n in asc_ch if n.start >= 28], length=32), ascent, shapes='dim')
    P('violins1', pads(pa, ('E5', 'B5'), 2, 80), ascent, articulations='tremolo', shapes='cresc')
    P('violins2', pads(pa, ('G4', 'E5'), 2, 76), ascent, articulations='tremolo', shapes='cresc')
    P('violas', pads(pa, ('D4', 'B4'), 2, 74), ascent, articulations='tremolo', shapes='cresc')
    P('cellos', Clip([(0, 28, nn('B2'), 80)], length=32), ascent, articulations='tremolo', shapes='cresc')
    P('basses', Clip([(0, 28, nn('B1'), 78)], length=32), ascent, shapes='cresc')
    P('horns', Clip([(n.start, n.dur, n.pitch, n.vel) for n in pads(pa, ('B2', 'G#3'), 3, 88) if n.start >= 8], length=32),
      ascent, shapes='cresc')
    P('trombones', Clip([(n.start, n.dur, n.pitch, n.vel) for n in pads(pa, ('E2', 'B2'), 2, 92) if n.start >= 16],
                        length=32), ascent, shapes='cresc')
    P('timpani', Clip([(16, 11.8, nn('B2'), 96)], length=32), ascent, articulations='roll')
    o.percussion.note(K['cymbal_roll'], ascent.bar(7) - 6.5, 7, 96)
    fin = Clip([(28, 4, p, 114) for p in (nn('E2'), nn('B2'), nn('E3'), nn('G#3'), nn('B3'), nn('E4'))], length=32)
    stabs(ascent, [28], pa, 116)
    for role, lo_, hi_ in (('violins1', 'G#5', 'E6'), ('violins2', 'B4', 'G#5'), ('violas', 'E4', 'B4')):
        P(role, Clip([(28, 3.9, p, 108) for p in range(nn(lo_), nn(hi_) + 1) if p % 12 in (4, 8, 11)], length=32),
          ascent, articulations='sustain', shapes='dim')
    P('trumpets', Clip([(28, 3.9, p, 106) for p in (nn('E4'), nn('G#4'), nn('B4'))], length=32), ascent,
      articulations='sustain', shapes='dim')
    P('low_brass', Clip([(28, 3.9, nn('E2'), 110)], length=32), ascent, articulations='marcato', shapes='dim')
    P('tuba', Clip([(28, 3.9, nn('E1'), 106)], length=32), ascent, articulations='sustain', shapes='dim')
    choir_f.play(Clip([(ascent.bar(7), 3.9, p, 108) for p in (nn('G#4'), nn('B4'), nn('E5'))], length=0), 0)
    choir_m.play(Clip([(ascent.bar(7), 3.9, p, 108) for p in (nn('E3'), nn('B3'))], length=0), 0)
    o.percussion.note(K['crash'], ascent.bar(7), 4, 106).note(K['bass_drum'], ascent.bar(7), 2, 106)
    piano.play(fin.strum(ms=20, bpm=138), ascent)
    orch.ring(o, ascent.bar(7), length=2, db=3, roles=['violins1', 'violins2', 'violas', 'choir', 'horns',
                                                      'trumpets'])

    # =================================================================================== III  THE STAMPEDE
    rock = [riff, anthem, anthem2, solo, riff2, brk]
    kit = b.drums
    dr = drummer.arrange(rock, bpm=138, style='rock', density=0.6, seed=5, kit=kit, ending='hit',
                         plan={'riff': {'role': 'chorus', 'energy': 0.82}, 'anthem': {'role': 'verse', 'energy': 0.6},
                               'anthem2': {'role': 'chorus', 'energy': 0.88}, 'solo': {'role': 'solo', 'energy': 0.9},
                               'riff2': {'role': 'chorus', 'energy': 0.92}, 'break': {'role': 'end'}})
    dr.play(kit)
    kit.play(drummer.pickup(138, length=1, kit=kit), riff.start - 1)

    # the riff: power chords, palm-muted chugs, both guitars (two takes)
    rr = Clip([(r[0], r[1], nn(r[2]), 104 if r[3] == '' else 88) for r in RIFF_ROOTS], length=8)
    rclip = rr.chordify('power')
    rclip = rclip.articulate('palm', where=lambda n: n.dur <= 0.5 and n.pitch % 12 == 9 and n.start % 4 < 1.5)
    for tr, ms, sd in ((b.gtr_l, 9, 1), (b.gtr_r, 12, 2)):
        for sec in (riff, riff2):
            r_ = rclip.strum(ms=ms, bpm=138, direction='down').vel_random(7, seed=sd + int(sec.start))
            tr.loop(r_, sec)
    bass_riff = Clip([(r[0], r[1] * 0.9, nn(r[2]) - 12 if nn(r[2]) >= nn('A2') else nn(r[2]), 100 if r[3] == '' else 86)
                      for r in RIFF_ROOTS], length=8)
    b.bass.loop(bass_riff.vel_random(6, seed=4), riff, riff2)

    bmem = bassist.Memory()
    gmem = gtr.Memory()
    pa1, pa2 = s.prog(P_ANTHEM), s.prog(P_ANTHEM2)
    psolo = s.prog(P_SOLO)

    def slice_kick(sec):
        a0 = sec.start - dr.start
        return Clip([(n.start - a0, n.dur, n.pitch, n.vel) for n in dr.clip if a0 <= n.start < a0 + sec.length],
                    length=sec.length)

    for sec, pr_, part, nxt in ((anthem, pa1, 'verse', 'Am'), (anthem2, pa2, 'chorus', 'Am'),
                                (solo, psolo, 'solo', 'Am')):
        bassist.arrange(pr_, bpm=138, key='A minor', style='rock', part=part, kick=slice_kick(sec), into=nxt,
                        seed=int(sec.start) % 97, memory=bmem, at=sec).place(b.bass, sec)
        ga = gtr.arrange(pr_, bpm=138, key='A minor', style='rock', section=sec, sound=b.gtr_l, memory=gmem,
                         seed=int(sec.start) % 89, next_chord=nxt)
        ga.play(b.gtr_l, sec)
        ga.take(2).play(b.gtr_r, sec)
    # the break: band hits on F and E7, then a tom run and a timpani roll
    hits = Clip([(0, 0.4, nn('F2'), 116), (1.5, 0.4, nn('F2'), 110), (4, 3.6, nn('E2'), 120)], length=8)
    for tr in (b.gtr_l, b.gtr_r):
        tr.play(hits.chordify('power').strum(ms=10, bpm=138), brk)
    b.bass.play(Clip([(0, 0.4, nn('F1'), 110), (1.5, 0.4, nn('F1'), 106), (4, 3.6, nn('E1'), 118)], length=8), brk)
    P('timpani', Clip([(4, 3.9, nn('G2'), 100)], length=8), brk, articulations='roll')

    # organ: held chords (the Leslie speeds up in anthem2)
    for sec, pr_ in ((anthem, pa1), (anthem2, pa2), (solo, psolo)):
        b.keys.play(chords(pr_, register=('A3', 'E5'), voices=4, vel=70), sec)
    b.keys.automate('fx.tremolo.rate', [(anthem.start, 1.0), (anthem2.start - 2, 1.0), (anthem2.start, 6.2, 'exp'),
                                         (solo.end, 6.2), (solo.end + 4, 1.0, 'smooth')])

    # the guitar orchestra
    a1 = touch(mel(THEME + THEME_HALF, 32, transpose=-3), 70, 112)
    a2 = touch(mel(THEME + [(24, 1.5, 'C5'), (25.5, 0.5, 'Bb4'), (26, 1, 'Ab4'), (27, 1, 'B4'), (28, 3.5, 'C5')],
                   32, transpose=-3), 76, 120)
    vib1 = {'depth': 24, 'rate': 5.6}
    L1 = art.legato(a1, overlap=0.03).glide(90, where=art.leaps(5))
    hero.play(g1, L1, anthem, vib=vib1, throws=True)
    hero.play(g2, third(a1, 'A minor', -2).velocity(0.94), anthem, vib={'depth': 20, 'rate': 5.3})
    L2 = art.legato(a2, overlap=0.03).glide(90, where=art.leaps(5))
    hero.play(g1, L2, anthem2, vib=vib1)
    hero.play(g2, third(a2, 'A minor', -2).velocity(0.94), anthem2, vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, third(a2, 'A minor', +2).velocity(0.9), anthem2, vib={'depth': 22, 'rate': 5.8})
    # the strings join anthem2 with a staccato ostinato
    ost = []
    for t, ln, c in pa2:
        r = c.bass_note(low='A2')
        for j in range(int(ln * 2)):
            ost.append((t + j * 0.5, 0.35, r + (12 if j % 4 == 3 else 0), 84 + (14 if j % 3 == 0 else 0)))
    P('cellos', Clip(ost, length=32), anthem2, articulations='staccato')
    P('violas', Clip([(n[0], n[1], n[2] + 7, n[3] - 8) for n in ost], length=32), anthem2, articulations='staccato')
    P('violins1', pads(pa2, ('A4', 'E5'), 2, 74), anthem2, shapes='swell')

    # the solo: the lead guitar played by the guitarist (bends, slides, vibrato; flash moves budgeted)
    sl = touch(mel(SOLO, 48), 72, 122)
    hero.lead(g1, sl, psolo, bpm=138, key='A minor', style='rock', section=solo, memory=gtr.Memory(), seed=9,
              climax=True, throws=True)
    tail_ = Clip([(n.start, n.dur, n.pitch, n.vel) for n in sl if n.start >= 40], length=48)
    hero.play(g2, third(tail_, 'A minor', -2).velocity(0.9), solo, vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, third(tail_, 'A minor', +2).velocity(0.86), solo, vib={'depth': 22, 'rate': 5.8})
    # riff and riff2: the orchestra hits the riff accents with the band (A&R #2: the band's entry has to be an
    # arrival) - brass marcato, the low strings, timpani; riff2 adds screaming tremolo violins on top
    br = Clip([(r[0], r[1] * 0.8, nn(r[2]), 108) for r in RIFF_ROOTS if r[3] == ''], length=8)
    tim = Clip([(0, 0.8, nn('A2'), 108), (2, 0.8, nn('D2'), 100), (3, 0.8, nn('E2'), 104), (4, 0.8, nn('A2'), 110),
                (6, 0.8, nn('G2'), 102)], length=8)
    for sec, dv in ((riff, -4), (riff2, 0)):
        P('trombones', br.chordify('power').velocity(1.0 + dv / 108) * 2, sec, articulations='marcato')
        P('horns', Clip([(n.start, n.dur, n.pitch + 12, n.vel - 8 + dv) for n in br], length=8) * 2, sec,
          articulations='marcato')
        P('low_brass', Clip([(n.start, n.dur, n.pitch - 12, n.vel + dv) for n in br if n.pitch - 12 >= nn('A#0')],
                            length=8) * 2, sec, articulations='marcato')
        P('cellos', Clip([(n.start, n.dur, n.pitch, n.vel + dv) for n in br], length=8) * 2, sec,
          articulations='marcato')
        P('basses', Clip([(n.start, n.dur, n.pitch - 12, n.vel + dv) for n in br], length=8) * 2, sec,
          articulations='marcato')
        P('timpani', tim * 2, sec, articulations='hit')
    o.percussion.note(K['crash'], riff.start, 4, 122).note(K['bass_drum'], riff.start, 2, 122)
    P('violins1', Clip([(0, 15.5, p, 92) for p in (nn('A5'), nn('E6'))], length=16), riff2,
      articulations='tremolo', shapes='cresc')
    P('violins2', Clip([(0, 15.5, p, 88) for p in (nn('C5'), nn('A5'))], length=16), riff2,
      articulations='tremolo', shapes='cresc')

    # Part III climbs by layers (A&R #2): anthem2 adds the chorus 'ah' and soft horns, the solo gets the orchestra's
    # sustained bed under it and the chorus for its last four bars
    P('violas', pads(pa1, ('C4', 'G4'), 2, 62), anthem, shapes='swell')
    P('cellos', pa1.bass('root', low='A2', vel=64), anthem, shapes='swell')
    P('choir', pads(pa2, ('A3', 'E5'), 4, 70), anthem2, shapes='swell')
    P('horns', pads(pa2, ('E3', 'C4'), 3, 66), anthem2, shapes='swell')
    P('violins1', pads(psolo, ('A4', 'E5'), 2, 64), solo, shapes='swell')
    P('violins2', pads(psolo, ('E4', 'A4'), 2, 62), solo, shapes='swell')
    P('violas', pads(psolo, ('C4', 'G4'), 2, 62), solo, shapes='swell')
    P('horns', pads(psolo, ('E3', 'C4'), 3, 64), solo, shapes='swell')
    P('choir', Clip([n for n in pads(psolo, ('A3', 'E5'), 4, 76) if n.start >= 32], length=48), solo, shapes='cresc')
    # the solo's peak (its held D6 in bar 9): a timpani roll into it, a crash + bass drum on it
    P('timpani', Clip([(28, 3.9, nn('A2'), 96)], length=48), solo, articulations='roll')
    o.percussion.note(K['crash'], solo.bar(8), 4, 112).note(K['bass_drum'], solo.bar(8), 2, 110)

    # =================================================================================== IV  CURTAIN
    pf, ps_ = s.prog(P_FINALE), s.prog(P_SUMMIT)
    # The film tutti (A&R #1: the payoff was buried under a root-heavy wall - cellos on roots the loudest part,
    # seven parts spelling the same chord): the theme in three octaves - violins1 + flutes above, violins2 +
    # trumpets + gtr1 + the women's choir at pitch, cellos + horns + the men's choir below - and the large chorus'
    # top voice on it. The harmony is left to two carriers (violas, the rhythm guitars) and the harmony guitars;
    # the low end is basses + bass guitar + timpani (no tuba, organ or piano 8ths).
    fm = touch(mel(FINALE, 32), 84, 122)

    def octave(clip, k, dv=0, length=32):
        return Clip([(n.start, n.dur, n.pitch + 12 * k, max(1, min(127, n.vel + dv))) for n in clip], length=length)

    P('violins1', octave(fm, 1), finale)
    P('violins2', fm, finale)
    P('flutes', octave(fm, 1, -10), finale)
    P('trumpets', octave(fm, 0, -6), finale)
    P('horns', octave(fm, -1, 2), finale)
    P('cellos', octave(fm, -1), finale)
    P('choir', harmony(fm, pf, voices=4, floor=50), finale)
    speak(choir_f, orch.lead(Clip([(n.start + finale.start, n.dur, n.pitch, n.vel - 6) for n in fm], length=0),
                             76, 35))
    speak(choir_m, orch.lead(Clip([(n.start + finale.start, n.dur, n.pitch - 12, n.vel - 4) for n in fm],
                                  length=0), 76, 35))
    choir_f.automate('instrument.dynamics', [(finale.start - 1, 0.55), (summit.bar(3), 0.75, 'smooth'),
                                             (fall.start, 0.0, 'smooth')])
    choir_m.automate('instrument.dynamics', [(finale.start - 1, 0.6), (summit.bar(3), 0.9, 'smooth'),
                                             (fall.start, 0.0, 'smooth')])
    P('violas', pads(pf, ('E4', 'C5'), 2, 80), finale, shapes='swell')
    P('basses', pf.bass('root', low='C2', vel=92), finale)
    P('timpani', Clip([(t, 1, nn('C2') if c.root in (0, 5, 8) else nn('G2'), 108) for (t, ln, c) in pf
                       if t % 4 == 0], length=32), finale, articulations='hit')
    for t in (0, 16):
        o.percussion.note(K['crash'], finale.start + t, 4, 116).note(K['bass_drum'], finale.start + t, 2, 118)
    # the guitar orchestra: gtr1 on the tune (with violins2 and the trumpets), the harmony guitars around it
    ff = touch(mel(FINALE, 32), 88, 124)
    hero.play(g1, art.legato(ff, overlap=0.03).glide(90, where=art.leaps(5)), finale, vib=vib1)
    hero.play(g2, third(ff, 'C major', -2).velocity(0.92), finale, vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, Clip([(n.start, n.dur, n.pitch - 12, n.vel) for n in third(ff, 'C major', +2)], length=32)
              .velocity(0.86), finale, vib={'depth': 22, 'rate': 5.8})
    # the band in the finale: big half-time ballad beat, bass, power chords
    df = drummer.arrange([finale, summit], bpm=76, style='ballad', density=0.7, seed=8, kit=kit, ending='hit',
                         plan={'finale': {'role': 'chorus', 'energy': 0.95}, 'summit': {'role': 'chorus', 'energy': 1.0}})
    df.play(kit)
    bassist.arrange(pf, bpm=76, key='C major', style='ballad', part='chorus', memory=bmem, at=finale,
                    seed=21).place(b.bass, finale)
    gf = gtr.arrange(pf, bpm=76, key='C major', style='rock', section=finale, energy=0.9, sound=b.gtr_l,
                     memory=gmem, seed=31, next_chord='Ab')
    gf.play(b.gtr_l, finale)
    gf.take(2).play(b.gtr_r, finale)

    # summit: the motif climbs to C6, the last tutti chord - the same three octaves, the chord on violas +
    # trombones + the guitars, the low end basses + bass trombone + bass guitar, then everything on the last C
    sm = touch(mel(SUMMIT, 16), 96, 126)
    P('violins1', sm, summit)
    P('flutes', sm, summit)
    P('violins2', octave(sm, -1, 0, 16), summit)
    P('trumpets', octave(sm, -1, -4, 16), summit)
    P('horns', octave(sm, -1, 0, 16), summit)
    P('cellos', octave(sm, -2, 0, 16), summit)
    P('choir', harmony(octave(sm, -1, 0, 16), ps_, voices=4, floor=52), summit, shapes='cresc')
    speak(choir_f, orch.lead(Clip([(n.start + summit.start, n.dur, n.pitch - 12, n.vel - 6) for n in sm],
                                  length=0), 76, 35))
    speak(choir_m, orch.lead(Clip([(n.start + summit.start, n.dur, n.pitch - 24, n.vel - 4) for n in sm],
                                  length=0), 76, 35))
    P('trombones', pads(ps_, ('C3', 'G3'), 3, 96), summit, shapes='cresc')
    P('violas', pads(ps_, ('G4', 'E5'), 2, 90), summit, shapes='cresc')
    P('basses', ps_.bass('root', low='C2', vel=100), summit)
    P('low_brass', ps_.bass('root', low='C2', vel=100), summit, articulations='sustain')
    P('tuba', Clip([(12, 3.8, nn('C1'), 104)], length=16), summit)
    P('timpani', Clip([(0, 1, nn('G#2'), 110), (4, 1, nn('A#2'), 112), (8, 3.8, nn('C3'), 104),
                       (12, 1, nn('C2'), 124)], length=16), summit, articulations='hit')
    o.percussion.note(K['cymbal_roll'], summit.bar(3) - 5, 6, 108)
    o.percussion.note(K['crash'], summit.bar(3), 4, 124).note(K['bass_drum'], summit.bar(3), 2, 124)
    P('drums', Clip([(12, 2, nn('C1'), 118), (12, 2, nn('G1'), 104)], length=16), summit)      # the taikos
    hero.play(g1, art.legato(Clip([(n.start, n.dur, n.pitch, n.vel) for n in sm], length=16), overlap=0.03)
              .glide(90, where=art.leaps(5)), summit, vib=vib1)
    hero.play(g2, touch(mel([(0, 4, 'Ab4'), (4, 4, 'Bb4'), (8, 2, 'F5'), (10, 2, 'G5'), (12, 3.5, 'G5')], 16),
                        90, 116), summit, vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, touch(mel([(0, 4, 'C5'), (4, 4, 'D5'), (8, 2, 'A5'), (10, 2, 'B5'), (12, 3.5, 'E5')], 16),
                        88, 114), summit, vib={'depth': 22, 'rate': 5.8})
    for tr in (b.gtr_l, b.gtr_r):
        tr.play(Clip([(0, 3.8, nn('G#2'), 110), (4, 3.8, nn('A#2'), 112), (8, 3.8, nn('C3'), 114),
                      (12, 3.6, nn('C3'), 122)], length=16).chordify('power').strum(ms=12, bpm=76), summit)
    b.bass.play(Clip([(0, 3.8, nn('Ab1'), 108), (4, 3.8, nn('Bb1'), 110), (8, 3.8, nn('C2'), 112),
                      (12, 3.6, nn('C2'), 120)], length=16), summit)
    piano.play(Clip([(12, 3.8, p, 104) for p in (nn('C1'), nn('C2'), nn('G2'), nn('E3'), nn('C4'), nn('G4'))],
                    length=16).strum(ms=40, bpm=60), summit)
    orch.ring(o, summit.bar(3), length=2, db=4, roles=['violins1', 'violins2', 'violas', 'cellos', 'choir',
                                                      'horns', 'trumpets', 'trombones'])
    # the choirs' expression lanes (speak()): one lane per track for the whole song, back to 1 after the summit
    for tr in (choir_m, choir_f):
        expr[tr.id] += [(fall.start + 2, 1.0)]
        tr.automate('instrument.expression', expr[tr.id])

    # fall: the tam-tam; the orchestra drops to pianissimo, the hall rings
    o.percussion.note(K['tam_tam'], fall.start, 8, 112)
    # pp, but audible under the tam-tam's ring (it read as a dropout at -34 LUFS: A&R #5)
    P('violins2', Clip([(0, 7.5, p, 46) for p in (nn('Ab4'), nn('C5'), nn('Eb5'))], length=8), fall, shapes='swell')
    P('cellos', Clip([(0, 7.5, nn('C3'), 50)], length=8), fall, shapes='swell')
    choir_oh.play(Clip([(fall.start, 7.5, p, 58) for p in (nn('C4'), nn('Eb4'), nn('G4'))], length=0), 0)
    choir_oh.automate('instrument.dynamics', [(fall.start, 0.45), (fall.end, 0.3, 'smooth'),
                                              (coda.start + 0.5, 0.12, 'smooth'), (coda.bar(4), 0.22, 'smooth'),
                                              (coda.end, 0.08, 'smooth')])

    # coda: the piano alone with the motif, soft strings, the rolled C major chord (fermata)
    pc = s.prog(P_CODA)
    ca = pianist.arrange(touch(mel(CODA, 20), 44, 80), pc, bpm=60, key=s.key, style='ballad', density=0.5, seed=41,
                         devices={'thirds': 1.5, 'sixths': 1.5, 'close': 1.5, 'single': 1}, memory=pmem,
                         at=coda.start, section_end=False)
    piano.play(ca.rh, coda)
    piano.play(broken(pc, vel=40, seed=41), coda)
    last = coda.bar(5)
    final = Clip([(0, 3.95, p, v) for p, v in ((nn('C1'), 70), (nn('C2'), 66), (nn('G2'), 58), (nn('E3'), 56),
                                              (nn('G3'), 52), (nn('D4'), 50), (nn('E4'), 54), (nn('C5'), 64))],
                 length=8).strum(ms=85, bpm=50)
    piano.play(final, last)
    piano.automate('instrument.pedal', ca.pedal(pc, coda, end=last) +
                   [(last - 0.05, 0, 'step'), (last + 0.02, 1, 'step')])
    P('violins2', Clip([(n.start, n.dur, n.pitch, 34) for n in pads(pc, ('G4', 'Eb5'), 2, 34)], length=20), coda,
      shapes='swell')
    P('violas', pads(pc, ('C4', 'G4'), 2, 34), coda, shapes='swell')
    P('cellos', pc.bass('root', low='C3', vel=36), coda, shapes='swell')
    P('violins2', Clip([(20, 3.95, p, 30) for p in (nn('E5'), nn('G5'))], length=24), coda, shapes='dim')
    P('violas', Clip([(20, 3.95, p, 30) for p in (nn('C4'), nn('G4'))], length=24), coda, shapes='dim')
    P('cellos', Clip([(20, 3.95, nn('C3'), 32)], length=24), coda, shapes='dim')
    orch.ring(o, last, length=3, db=4, roles=['violins2', 'violas', 'cellos'])

    # echo throws on the piano's phrase ends in the coda (the band's echo bus answers in the gaps)
    piano.send('echo', -60)
    thr = []
    for beat_ in (4, 8, 12, 16):
        a_ = coda.start + beat_ - 1.0
        thr += [(a_, -60), (a_ + 0.2, -16, 'smooth'), (a_ + 1.2, -16), (a_ + 1.6, -60, 'smooth')]
    piano.automate('send.echo', thr)

    # ------------------------------------------------------------------------------------ production moves
    # Brian-May-style repeats: the solo guitar feeds the band's dotted-8th echo (the hero keeps its own echo too)
    g1.send('echo', -60)
    g1.automate('send.echo', [(anthem.start - 1, -60), (anthem.start, -14, 'smooth'), (solo.start, -6, 'smooth'),
                              (solo.end - 1, -6), (solo.end, -14, 'smooth'), (fall.start - 1, -14),
                              (fall.start, -60, 'smooth')])
    # the masque is a pianissimo waltz, but its tune and oom-pah-pah must carry: faders up inside it
    for tr, db in ((o.flutes, 4), (o.oboes, 4), (o.clarinets, 5), (o.bassoons, 10), (o.harp, 6), (o.cellos, 5),
                   (o.basses, 5), (o.violas, 5), (o.violins2, 5), (choir_f, 6), (o.percussion, 3)):
        tr.automate('gainDb', [(masque.start - 0.5, 0), (masque.start, db, 'smooth'), (masque.end - 0.5, db),
                               (masque.end, 0, 'smooth')])
    # the band: louder than the opera (the arc peaks in the rock and the finale)
    for tr, db in ((b.drums, 0.5), (b.bass, 2.0), (b.gtr_l, 1.5), (b.gtr_r, 1.5), (b.keys, 3.0)):
        tr.gain_db += db
    for tr, db in ((g1, 3.5), (g2, 5.5), (g3, 5.5)):     # the guitar orchestra in front of the band
        tr.gain_db += db
    b.buses['echo'].gain_db += 9.0                        # the solo's repeats must be heard in its gaps
    # (the finale's old 'weight' rides - bass guitar / basses / tuba up, gtr1 / choir / violins1 down - are gone:
    # they buried the tune under its own roots, A&R #1; the tutti is voiced for the tune now)
    # tone: the mid / presence surplus came from the female choir, the large chorus, gtr1 and violins1
    choir_f.add_fx(fx.eq({'peak1.freq': 1000, 'peak1.gain': -3.0, 'peak1.q': 0.8}, name='mid_cut'))
    o.choir.add_fx(fx.eq({'peak1.freq': 1000, 'peak1.gain': -2.0, 'peak1.q': 0.8}, name='mid_cut'))
    g1.add_fx(fx.eq({'peak1.freq': 3400, 'peak1.gain': -3.0, 'peak1.q': 0.9, 'peak2.freq': 1100,
                     'peak2.gain': -2.0, 'peak2.q': 0.8}, name='pres_cut'))
    for tr in (g2, g3, b.gtr_r, b.gtr_l):
        tr.add_fx(fx.eq({'peak1.freq': 3400, 'peak1.gain': -2.0, 'peak1.q': 0.9}, name='pres_cut'))
    o.violins1.add_fx(fx.eq({'peak1.freq': 3300, 'peak1.gain': -3.0, 'peak1.q': 1.0}, name='pres_cut'))
    choir_m.add_fx(fx.eq({'peak1.freq': 1000, 'peak1.gain': -2.5, 'peak1.q': 0.8}, name='mid_cut'))
    for tr in (g2, g3):
        tr.add_fx(fx.eq({'peak1.freq': 1100, 'peak1.gain': -2.0, 'peak1.q': 0.8}, name='mid_cut'))
    for tr in (o.violins2, o.trumpets):
        tr.add_fx(fx.eq({'peak1.freq': 3200, 'peak1.gain': -2.0, 'peak1.q': 1.0}, name='pres_cut'))
    o.drums.add_fx(fx.width(width=1.0, monobass=150))          # the taikos: centred lows
    # centred lows for the whole piece (hard-panned power chords, stereo samples): mono below 120 Hz before the limiter
    s.master.fx.insert(len(s.master.fx) - 1, FX.coerce(fx.width(width=1.0, monobass=120)))
    hero_piano.carve(s, piano, o.violins2, o.violas, choir_oh, duck=2.0, dip=-1.5)
    # the ballad piano was veiled (A&R #6: brilliance -19.6, air -25.8 dB vs the film reference): air above 7.5 kHz,
    # no presence push at 2-5 kHz ("es klingt hart" was a sound-design lesson)
    piano.add_fx(fx.eq({'high.freq': 7500, 'high.gain': 5.0, 'high.q': 0.7}, name='air'))
    # the finale's chord carriers step out of the tune's low mids while the lead guitar sings (A&R #1)
    s.carve(o.violas, o.trombones, key=g1, freq=450, q=0.8, depth=3.0)
    s.sidechain(b.keys, b.gtr_l, b.gtr_r, key=g1, depth=2.5, attack=10, hold=60, release=200, threshold=-40)
    for t in (b.gtr_l, b.gtr_r, b.keys):
        t.add_fx(fx.eq({'peak2.freq': 1900, 'peak2.gain': -2.0, 'peak2.q': 0.9}, name='hero_dip'))

    # ------------------------------------------------------------------------------------ master (MASTER.md)
    # mastering.match vs the 'film' profile (no fitting reference), platform auto: a little sub under the tutti and
    # a broad dip at the mids' centre, the -1 dBTP limiter kept at the film chain's slower 200 ms release
    mastering.apply(s, eq={"low.freq": 60, "low.gain": 1.9, "low.q": 0.7071, "peak1.freq": 1250, "peak1.gain": -1.4,
                           "peak1.q": 0.5}, limiter={"ceiling": -1.2, "release": 200.0}, loudness_change=+0.6)
    return s
