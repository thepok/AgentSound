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

def harmony(line, prog, voices=3, floor=48, gap=3):
    """Homophonic block harmony under a line (a choir / brass section): each note gets the chord tones below it
    (of the chord sounding at its onset), at least `gap` semitones apart, never under `floor`."""
    out = []
    for n in line:
        c = prog.at(n.start)
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
# agentsound notation (docs/COMPOSE_API.md "Notation"): note values are sticky, '|' checks the bars, @8 = from beat 8.
# The curtain motif: an upbeat G4, a sixth up to a held Eb5, a sigh down - then the answer climbs higher. The theme's
# phrases are named and spliced into lines: TUNE('head climb half'); every line is played at velocity 90 (touch()
# shapes it).
TUNE = phrases(
    vel=90,
    head='G4/8 Eb5/2 D5/8 C5/4 | C5/4. Bb4/8 Ab4/4 G4/8 Ab4 | C5/4 F5/2 Eb5/8 D5 | D5/2 B4/4. r/8 |',
    climb='G4/8 Eb5/4. G5/4. F5/8 | F5/4 D5 Eb5/2 |',
    half='C5/4. D5/8 Eb5/4 Ab4 | G4/2.',                      # the half close on the dominant
    full='C5/4. Bb4/8 Ab4/4 B4 | C5/2..',                     # the full close on the tonic
    ret='Eb5/4 D5 C5/2',                                      # the return: straight into the Ab chord
    intro='r/2 G4/8 Eb5/4. | r/2 D5/4 C5 | r/2 C5/8 F5/4. | D5/2 B4',    # the motif hinted
    middle='Bb5/4. G5/8 Eb5/4 F5 | F5/4. D5/8 Bb4/2 | C5/4 Eb5 G5 Bb5 | Ab5/2. G5/8 F5 | '
           'Eb5/4. F5/8 Ab5/4 C6 | Bb5/2 Ab5/4 G5 | G5 Eb5 C5/4. D5/8 | D5/2 B4/4 D5',
    coda='G4/8 Eb5/2 D5/8 C5/4 | C5/2 Bb4/4 Ab4 | Ab4 C5/2 F4/4 | G4/2 D5 | C5 B4',
    # Part IV: the theme in C major (finale), the motif climbing to C6 (summit)
    finale='G4/8 E5/2 D5/8 C5/4 | C5/4. B4/8 A4/4 G4/8 A4 | C5/4 F5/2 E5/8 D5 | D5/2 B4/4. r/8 | '
           'G4/8 E5/4. G5/4. F5/8 | F5/4 D5 E5/2 | C5/4. D5/8 F5/4 D5 | C5/1',
    summit='Eb5/8 C6/2 Bb5/8 Ab5/4 | F5/8 D6/2 C6/8 Bb5/4 | C6/2 D6/4 E6 | C6/1',
    # Part II (E minor): call and response, the masque's waltz tune (3/4)
    call1='B3/8 G4/4. F#4/4 E4 | D4/2 B3/4.',
    answer1='@8 G4/8 E5/4. D5/4 C5 | B4/4. C5/8 D#5/2',
    call2='E3/8 C4/4. B3/4 A3 | G3/2 E3/4.',
    answer2='@8 C5/8 A5/4. F#5/4 E5 | D#5/4. E5/8 F#5/2',
    call3m='B3/8 G4/4. F#4/4 E4 | r/1 | C4/8 G4/4. F#4/4 E4',
    call3f='r/1 | D5/8 B5/4. A5/4 G5 | r/1 | E5/8 C6/4. B5/4 A5',
    tutti4='G5/2 E5 | A5 F#5 | B5/2. A5/4 | A5/2 D#5/4',
    masque='meter=3/4 D5/4 B5/4. A5/8 | A5/4 F#5 D5 | G5 A5/8 B5 D6/4 | E6/2 D6/8 B5 | C6/4 A5 E5 | F#5 A5 C6 | '
           'B5/2 G5/4 | F#5 A5 D#5 | B4/8 G5/4. F#5/4 | E5 G5 C6 | C6/4. A5/8 F#5/4 | D#5/2 B4/4',
    # Part III: the lead guitar's solo - bars 1-4 the motif, answered; 5-8 climbing, faster; 9-12 the peak and the
    # fall back to the riff
    solo='E5/8 C6/4. B5/8 A5/4. | r/8 A5 G5 F5 A5/2 | r/8 D5 G5 A5 B5/4. D6/8 | C6/2. B5/8 A5 | '
         'C6 A5 F5 A5 C6/4 A5 | B5/8 G5 D5 G5 B5/4. C6/8 | B5/2 G5/8 E5 G5/4 | A5/8 C6 E6 D6:2.5 | '
         'D6/2. C6/8 A5 | B5/4. G#5/8 E5/2 | E5/8 C6/4. B5/8 A5/4. | B5/4 G#5 E5/2')
P_THEME = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Cm Bb:0.5 Eb:0.5 Ab:0.5 Fm7:0.5 G'
P_THEME2 = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Cm Bb:0.5 Eb:0.5 Ab:0.5 G7:0.5 Cm'
P_INTRO = 'Cm Ab/C Fm/C G7sus4:0.5 G7:0.5'
P_MIDDLE = 'Eb Bb/D Cm Ab Fm7 Bb7sus4:0.5 Bb7:0.5 Eb/G:0.5 Ab:0.5 Fm6/Ab:0.5 G7:0.5'
P_RETURN = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Ab:2'
P_CODA = 'Cm Ab Fm G7sus4:0.5 G7:0.5 Ab:0.5 G7:0.5'

# ---- Part III / IV: the theme in A minor (guitars) and in C major (finale)
P_ANTHEM = 'Am F Dm E7sus4:0.5 E7:0.5 Am G:0.5 C:0.5 F:0.5 Dm7:0.5 E'
P_ANTHEM2 = 'Am F Dm E7sus4:0.5 E7:0.5 Am G:0.5 C:0.5 F:0.5 E7:0.5 Am'
P_FINALE = 'C Am F Gsus4:0.5 G:0.5 C Bb:0.5 C:0.5 Ab:0.5 Bb:0.5 C'
P_SUMMIT = 'Ab Bb Csus4:0.5 C:0.5 C'

# ---- Part II material (E minor)
P_STAB = 'Em Em C/E B7/D#'
P_CALL1 = 'Em Em/D C B7'
P_CALL2 = 'Am Am/G F#m7b5 B7'
P_CALL3 = 'Em G/D C Am/C'
P_CALL4 = 'C D B7sus4 B7'
P_MASQUE = 'G D7/F# G/D Em Am D7 G B7 Em C F#m7b5 B7'
P_ASCENT = 'Em/B C/B Am/B B7 C D B7sus4 E'

# ---- Part III: the riff - palm-muted A chugs under the accented hits (two layers: the brass doubles the hits)
RIFF_CHUGS = 'A2/8 A2 A2 r/8 r/2 | A2/8 A2 A2 r/8 r/2'
RIFF_HITS = 'r/4. C3/8 D3/4 E3/8 D3 | r/4. G2/8 G2 F2/4 E2/8'
P_RIFF = 'Am:0.375 C:0.125 D:0.375 E:0.125 Am:0.375 G:0.25 F:0.375'
P_SOLO = 'Am F G Am F G Em Am Dm E7 Am E7'


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
    bpm = s.tempo_at                           # the tempo at a beat / section (the tempo map above)

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
    P = lambda role, clip, at, **kw: orch.perform(o, role, clip, at, seed=sum(map(ord, role)) + int(s.at(at)), **kw)  # noqa
    K = orch.PERCUSSION_KEYS
    pmem = pianist.Memory()
    pmem.save(coda.bar(4))                     # the pianist keeps its one big figure for the last cadence

    def piano_part(line, prog_spec, sec, lo, hi, *, key=None, lh_vel=58, style='ballad',
                   density=0.55, seed=1, climax=False, lh=True, lead_in=False, section_end=True):
        prog = s.prog(prog_spec)
        m = touch(TUNE(line, length=prog.length), lo, hi)
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
    ri = pianist.arrange(touch(TUNE('intro'), 40, 70), pi, bpm=72, key=s.key, style='ballad', density=0.4,
                         seed=3, memory=pmem, at=intro.start)
    piano.play(ri.rh, intro)
    rolled = chords(pi, register=('C2', 'G4'), voices=5, vel=46).strum(ms=55, bpm=64)
    piano.play(rolled.vel_pattern([1.0, 0.9, 1.05, 0.95]), intro)
    piano.automate('instrument.pedal', ri.pedal(pi, intro))

    # theme: the piano states it; basses and cellos join softly in bar 5
    _, pt = piano_part('head climb half', P_THEME, theme, 52, 96, lh_vel=46, seed=11)
    P('cellos', pt.bass('root', low='C3', vel=44).window(16), theme, shapes='swell')
    P('basses', pt.bass('root', low='C2', vel=42).window(16), theme, shapes='swell')

    # theme2: the string pad and a cello counter-line; the theme closes on the tonic
    _, pt2 = piano_part('head climb full', P_THEME2, theme2, 58, 104, lh_vel=50, seed=12)
    P('violins2', pads(pt2, ('G4', 'Eb5'), 2, 42), theme2, shapes='swell')
    P('violas', pads(pt2, ('C4', 'G4'), 2, 44), theme2, shapes='swell')
    counter = TUNE('r/2 G3 | Ab3 C4 | C4/2. Bb3/4 | B3/2 D4 | Eb4/2. D4/4 | D4/2 G3 | Ab3 F3 | G3/1')
    P('cellos', touch(counter, 40, 66), theme2)
    P('basses', pt2.bass('root', low='C2', vel=46), theme2, shapes='swell')

    # middle: Eb major, the piano higher; violins double it in the second half; horns and the 'oh' choir under
    _, pm = piano_part('middle', P_MIDDLE, middle, 60, 106, key='Eb major', lh_vel=52, seed=13, density=0.6)
    vdub = TUNE('middle', transpose=-12).window(16)
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
    _, pr = piano_part('head ret', P_RETURN, ret, 62, 108, lh_vel=54, seed=14)
    P('violins1', touch(TUNE('head', length=24), 50, 88), ret)
    P('violins2', pads(pr, ('G4', 'Eb5'), 2, 56), ret, shapes='swell')
    P('violas', pads(pr, ('C4', 'G4'), 2, 58), ret, shapes='swell')
    P('cellos', pr.bass('root', low='C3', vel=60), ret, shapes='swell')
    P('basses', pr.bass('root', low='C2', vel=58), ret, shapes='swell')
    # the unresolved Ab chord (bar 5): held chords (hold(pitches, beats, vel, at=, length=)) swelling into the fermata
    P('horns', hold('Ab2 Eb3 C4', 7.5, 70, at=16, length=24), ret, shapes='cresc')
    P('violins1', hold('Ab5=60 C6=56', 7.5, at=16, length=24), ret, articulations='tremolo', shapes='cresc')
    piano.play(hold('Ab1 Ab2 Eb3 C4 Eb4 Ab4', 7.5, 84, at=16, length=24).strum(ms=60, bpm=60), ret)
    P('timpani', hold('Eb2', 3.8, 70, at=20, length=24), ret, articulations='roll')
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
    P('timpani', notes('E2/4=90 r/2. | E2/4=96 r/2. | E2/4=100 r/2. | B2/4=108 r B2=116 r'), stab, articulations='hit')

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

    def choir_line(track, line, prog, at, lo, hi, voices=3, floor=43, lead_ms=35, transpose=0):
        line = touch(TUNE(line, length=prog.length, transpose=transpose), lo, hi)
        blk = harmony(line, prog, voices=voices, floor=floor)
        a = s.at(at)
        blk = orch.lead(blk.shift(a).with_length(prog.length + a), bpm(at), lead_ms)     # in song beats
        speak(track, art.humanize_starts(blk, bpm(at), 10, seed=int(a)))
        return line

    def call_onsets(line, at, role, dv, art_='marcato'):
        """Double the motif's upbeat and the note it leaps to (every phrase of a call) so its rhythm reads: horns
        marcato under the men, pizzicato violins under the women."""
        ns = list(TUNE(line))
        pick = []
        for i, n in enumerate(ns):
            if n.dur <= 0.5 and i + 1 < len(ns) and abs(ns[i + 1].start - (n.start + n.dur)) < 1e-6:
                pick += [(n.start, 0.45, n.pitch, dv), (ns[i + 1].start, 0.9, ns[i + 1].pitch, dv + 8)]
        P(role, Clip(pick, length=16), at, articulations=art_)

    def stabs(at, hits, prog, vel=112):
        """Orchestra stabs: strings staccato + brass marcato + timpani on the given beats (relative to at)."""
        rows_str, rows_br, rows_lo, rows_t = [], [], [], []
        for h in hits:
            c = prog.at(h)
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
        piano.play(Clip([(h, 0.3, p, vel - 20) for h in hits for p in prog.at(h).notes(4)[:3]], length=ln), at)

    c1, c2, c3, c4 = (s.prog(p) for p in (P_CALL1, P_CALL2, P_CALL3, P_CALL4))
    b1, b2, b3, b4 = calls.bar(0), calls.bar(4), calls.bar(8), calls.bar(12)
    # the women's p / pp answers a little louder than before (they dipped to -36 / -38 LUFS: dropouts, A&R #5)
    choir_line(choir_m, 'call1', c1, b1, 84, 110, voices=2)
    call_onsets('call1', b1, 'horns', 92)
    choir_line(choir_f, 'answer1', c1, b1, 50, 74)
    call_onsets('answer1', b1, 'violins1', 52, 'pizzicato')
    stabs(b1, [14, 15, 15.5], c1, 108)
    choir_line(choir_m, 'call2', c2, b2, 96, 124, voices=2)
    call_onsets('call2', b2, 'horns', 100)
    choir_line(choir_f, 'answer2', c2, b2, 44, 68)
    call_onsets('answer2', b2, 'violins1', 46, 'pizzicato')
    stabs(b2, [14, 15, 15.5], c2, 116)
    choir_line(choir_m, 'call3m', c3, b3, 88, 112, voices=2)
    call_onsets('call3m', b3, 'horns', 94)
    choir_line(choir_f, 'call3f', c3, b3, 70, 100)
    call_onsets('call3f', b3, 'violins1', 70, 'pizzicato')
    stabs(b3, [3.5, 7.5, 11.5, 15.5], c3, 104)
    choir_line(choir_f, 'tutti4', c4, b4, 70, 112, voices=4, floor=53)
    choir_line(choir_m, 'tutti4', c4, b4, 70, 112, voices=2, transpose=-24)
    P('choir', harmony(touch(TUNE('tutti4', length=16, transpose=-12), 60, 108), c4, voices=4, floor=48), b4,
      shapes='cresc')
    stabs(b4, [15], c4, 122)
    P('violins1', pads(c4, ('B5', 'F#6'), 2, 70), b4, articulations='tremolo', shapes='cresc')
    P('violins2', pads(c4, ('D5', 'A5'), 2, 68), b4, articulations='tremolo', shapes='cresc')
    P('violas', pads(c4, ('F#4', 'D5'), 2, 66), b4, articulations='tremolo', shapes='cresc')
    P('cellos', c4.bass('root', low='C3', vel=78), b4, shapes='cresc')
    P('basses', c4.bass('root', low='C2', vel=76), b4, shapes='cresc')
    P('timpani', hold('B2', 2.9, 84, at=12, length=16), b4, articulations='roll')
    choir_m.automate('instrument.dynamics', [(b1, 0.72), (b2, 0.9, 'smooth'), (b3, 0.78, 'smooth'),
                                             (b4, 0.6, 'smooth'), (calls.bar(15), 1.0, 'smooth'),
                                             (masque.start, 0.2, 'step')])
    choir_f.automate('instrument.dynamics', [(b1, 0.4), (b2, 0.32, 'smooth'), (b3, 0.7, 'smooth'),
                                             (b4, 0.55, 'smooth'), (calls.bar(15), 1.0, 'smooth'),
                                             (masque.start, 0.62, 'step')])

    # masque: 3/4 mock-operatic waltz
    pq = s.prog(P_MASQUE, meter=masque.meter)
    qm = touch(TUNE('masque', length=36), 64, 104)
    P('flutes', qm, masque)
    P('oboes', (qm.window(12, 24) | qm.window(30)).transpose(-12).vel_add(-8), masque)
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
    P('clarinets', qm.window(24).transpose(-12).vel_add(-14), masque)
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
    choir_m.play(orch.lead(ent_m.shift(ascent.start).with_length(0), 112, 70), 0)
    choir_f.play(orch.lead(ent_f.shift(ascent.start).with_length(0), 112, 70), 0)
    # the E major fermata peaks and then dies away into the drummer's pickup: the riff must be the arrival, not a
    # step down from the fermata (A&R #2: fermata -10.1 LUFS, riff -13.7)
    choir_m.automate('instrument.dynamics', [(ascent.start, 0.3), (ascent.bar(7), 1.0, 'smooth'),
                                             (ascent.bar(7) + 0.5, 1.0), (ascent.bar(7) + 3.0, 0.3, 'smooth')])
    choir_f.automate('instrument.dynamics', [(ascent.start + 0.01, 0.3), (ascent.bar(7), 0.8, 'smooth'),
                                             (ascent.bar(7) + 0.5, 0.8), (ascent.bar(7) + 3.0, 0.25, 'smooth')])
    asc_ch = harmony(touch(TUNE('@16 E5/1 F#5 F#5 G#5'), 70, 118), pa, voices=4, floor=52)
    P('choir', asc_ch.window(0, 28), ascent, shapes='cresc')
    P('choir', asc_ch.window(28), ascent, shapes='dim')
    P('violins1', pads(pa, ('E5', 'B5'), 2, 80), ascent, articulations='tremolo', shapes='cresc')
    P('violins2', pads(pa, ('G4', 'E5'), 2, 76), ascent, articulations='tremolo', shapes='cresc')
    P('violas', pads(pa, ('D4', 'B4'), 2, 74), ascent, articulations='tremolo', shapes='cresc')
    P('cellos', hold('B2', 28, 80, length=32), ascent, articulations='tremolo', shapes='cresc')
    P('basses', hold('B1', 28, 78, length=32), ascent, shapes='cresc')
    P('horns', pads(pa, ('B2', 'G#3'), 3, 88).window(8), ascent, shapes='cresc')
    P('trombones', pads(pa, ('E2', 'B2'), 2, 92).window(16), ascent, shapes='cresc')
    P('timpani', hold('B2', 11.8, 96, at=16, length=32), ascent, articulations='roll')
    o.percussion.note(K['cymbal_roll'], ascent.bar(7) - 6.5, 7, 96)
    fin = hold('E2 B2 E3 G#3 B3 E4', 4, 114, at=28, length=32)
    stabs(ascent, [28], pa, 116)
    for role, lo_, hi_ in (('violins1', 'G#5', 'E6'), ('violins2', 'B4', 'G#5'), ('violas', 'E4', 'B4')):
        P(role, hold([p for p in range(nn(lo_), nn(hi_) + 1) if p % 12 in (4, 8, 11)], 3.9, 108, at=28, length=32),
          ascent, articulations='sustain', shapes='dim')
    P('trumpets', hold('E4 G#4 B4', 3.9, 106, at=28, length=32), ascent, articulations='sustain', shapes='dim')
    P('low_brass', hold('E2', 3.9, 110, at=28, length=32), ascent, articulations='marcato', shapes='dim')
    P('tuba', hold('E1', 3.9, 106, at=28, length=32), ascent, articulations='sustain', shapes='dim')
    choir_f.play(hold('G#4 B4 E5', 3.9, 108), ascent.bar(7))
    choir_m.play(hold('E3 B3', 3.9, 108), ascent.bar(7))
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
    rr = notes(RIFF_CHUGS, vel=88) | notes(RIFF_HITS, vel=104)
    rclip = rr.chordify('power')
    rclip = rclip.articulate('palm', where=lambda n: n.dur <= 0.5 and n.pitch % 12 == 9 and n.start % 4 < 1.5)
    for tr, ms, sd in ((b.gtr_l, 9, 1), (b.gtr_r, 12, 2)):
        for sec in (riff, riff2):
            r_ = rclip.strum(ms=ms, bpm=138, direction='down').vel_random(7, seed=sd + int(sec.start))
            tr.loop(r_, sec)
    bass_riff = (notes(RIFF_CHUGS, transpose=-12, vel=86, gate=0.9)
                 | notes('r/4. C2/8 D2/4 E2/8 D2 | r/4. G2/8 G2 F2/4 E2/8', vel=100, gate=0.9))
    b.bass.loop(bass_riff.vel_random(6, seed=4), riff, riff2)

    bmem = bassist.Memory()
    gmem = gtr.Memory()
    pa1, pa2 = s.prog(P_ANTHEM), s.prog(P_ANTHEM2)
    psolo = s.prog(P_SOLO)

    def slice_kick(sec):
        a0 = sec.start - dr.start
        return dr.clip.window(a0, a0 + sec.length).shift(-a0).with_length(sec.length)

    for sec, pr_, part, nxt in ((anthem, pa1, 'verse', 'Am'), (anthem2, pa2, 'chorus', 'Am'),
                                (solo, psolo, 'solo', 'Am')):
        bassist.arrange(pr_, bpm=138, key='A minor', style='rock', part=part, kick=slice_kick(sec), into=nxt,
                        seed=int(sec.start) % 97, memory=bmem, at=sec).place(b.bass, sec)
        ga = gtr.arrange(pr_, bpm=138, key='A minor', style='rock', section=sec, sound=b.gtr_l, memory=gmem,
                         seed=int(sec.start) % 89, next_chord=nxt)
        ga.play(b.gtr_l, sec)
        ga.take(2).play(b.gtr_r, sec)
    # the break: band hits on F and E7, then a tom run and a timpani roll
    hits = notes('F2:1.5:0.4=116 F2:2.5:0.4=110 E2/1:3.6=120')         # short, short, held
    for tr in (b.gtr_l, b.gtr_r):
        tr.play(hits.chordify('power').strum(ms=10, bpm=138), brk)
    b.bass.play(notes('F1:1.5:0.4=110 F1:2.5:0.4=106 E1/1:3.6=118'), brk)
    P('timpani', hold('G2', 3.9, 100, at=4, length=8), brk, articulations='roll')

    # organ: held chords (the Leslie speeds up in anthem2)
    for sec, pr_ in ((anthem, pa1), (anthem2, pa2), (solo, psolo)):
        b.keys.play(chords(pr_, register=('A3', 'E5'), voices=4, vel=70), sec)
    b.keys.automate('fx.tremolo.rate', [(anthem.start, 1.0), (anthem2.start - 2, 1.0), (anthem2.start, 6.2, 'exp'),
                                         (solo.end, 6.2), (solo.end + 4, 1.0, 'smooth')])

    # the guitar orchestra
    a1 = touch(TUNE('head climb half', length=32, transpose=-3), 70, 112)      # the theme in A minor
    a2 = touch(TUNE('head climb full', length=32, transpose=-3), 76, 120)
    vib1 = {'depth': 24, 'rate': 5.6}
    L1 = art.legato(a1, overlap=0.03).glide(90, where=art.leaps(5))
    hero.play(g1, L1, anthem, vib=vib1, throws=True)
    hero.play(g2, a1.harmonize('-3rd', key='A minor', keep=False, vel=1).velocity(0.94), anthem,
              vib={'depth': 20, 'rate': 5.3})                      # a diatonic third below (only the new voice)
    L2 = art.legato(a2, overlap=0.03).glide(90, where=art.leaps(5))
    hero.play(g1, L2, anthem2, vib=vib1)
    hero.play(g2, a2.harmonize('-3rd', key='A minor', keep=False, vel=1).velocity(0.94), anthem2,
              vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, a2.harmonize('3rd', key='A minor', keep=False, vel=1).velocity(0.9), anthem2,
              vib={'depth': 22, 'rate': 5.8})
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
    sl = touch(TUNE('solo', length=48), 72, 122)
    hero.lead(g1, sl, psolo, bpm=138, key='A minor', style='rock', section=solo, memory=gtr.Memory(), seed=9,
              climax=True, throws=True)
    tail_ = sl.window(40)
    hero.play(g2, tail_.harmonize('-3rd', key='A minor', keep=False, vel=1).velocity(0.9), solo,
              vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, tail_.harmonize('3rd', key='A minor', keep=False, vel=1).velocity(0.86), solo,
              vib={'depth': 22, 'rate': 5.8})
    # riff and riff2: the orchestra hits the riff accents with the band (A&R #2: the band's entry has to be an
    # arrival) - brass marcato, the low strings, timpani; riff2 adds screaming tremolo violins on top
    br = notes(RIFF_HITS, vel=108, gate=0.8)
    tim = notes('A2/2:0.8=108 D2/4:0.8=100 E2/4:0.8=104 A2/2:0.8=110 G2/2:0.8=102')
    for sec, dv in ((riff, -4), (riff2, 0)):
        P('trombones', br.chordify('power').velocity(1.0 + dv / 108) * 2, sec, articulations='marcato')
        P('horns', br.transpose(12).vel_add(dv - 8) * 2, sec, articulations='marcato')
        P('low_brass', br.transpose(-12).filter(lambda n: n.pitch >= nn('A#0')).vel_add(dv) * 2, sec,
          articulations='marcato')
        P('cellos', br.vel_add(dv) * 2, sec, articulations='marcato')
        P('basses', br.transpose(-12).vel_add(dv) * 2, sec, articulations='marcato')
        P('timpani', tim * 2, sec, articulations='hit')
    o.percussion.note(K['crash'], riff.start, 4, 122).note(K['bass_drum'], riff.start, 2, 122)
    P('violins1', hold('A5 E6', 15.5, 92, length=16), riff2, articulations='tremolo', shapes='cresc')
    P('violins2', hold('C5 A5', 15.5, 88, length=16), riff2, articulations='tremolo', shapes='cresc')

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
    P('choir', pads(psolo, ('A3', 'E5'), 4, 76).window(32), solo, shapes='cresc')
    # the solo's peak (its held D6 in bar 9): a timpani roll into it, a crash + bass drum on it
    P('timpani', hold('A2', 3.9, 96, at=28, length=48), solo, articulations='roll')
    o.percussion.note(K['crash'], solo.bar(8), 4, 112).note(K['bass_drum'], solo.bar(8), 2, 110)

    # =================================================================================== IV  CURTAIN
    pf, ps_ = s.prog(P_FINALE), s.prog(P_SUMMIT)
    # The film tutti (A&R #1: the payoff was buried under a root-heavy wall - cellos on roots the loudest part,
    # seven parts spelling the same chord): the theme in three octaves - violins1 + flutes above, violins2 +
    # trumpets + gtr1 + the women's choir at pitch, cellos + horns + the men's choir below - and the large chorus'
    # top voice on it. The harmony is left to two carriers (violas, the rhythm guitars) and the harmony guitars;
    # the low end is basses + bass guitar + timpani (no tuba, organ or piano 8ths).
    fm = touch(TUNE('finale', length=32), 84, 122)
    P('violins1', fm.octave(1), finale)
    P('violins2', fm, finale)
    P('flutes', fm.octave(1).vel_add(-10), finale)
    P('trumpets', fm.vel_add(-6), finale)
    P('horns', fm.octave(-1).vel_add(2), finale)
    P('cellos', fm.octave(-1), finale)
    P('choir', harmony(fm, pf, voices=4, floor=50), finale)
    speak(choir_f, orch.lead(fm.shift(finale.start).vel_add(-6).with_length(0), 76, 35))
    speak(choir_m, orch.lead(fm.shift(finale.start).octave(-1).vel_add(-4).with_length(0), 76, 35))
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
    ff = touch(TUNE('finale', length=32), 88, 124)
    hero.play(g1, art.legato(ff, overlap=0.03).glide(90, where=art.leaps(5)), finale, vib=vib1)
    hero.play(g2, ff.harmonize('-3rd', key='C major', keep=False, vel=1).velocity(0.92), finale,
              vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, ff.harmonize('3rd', key='C major', keep=False, vel=1).octave(-1).velocity(0.86), finale,
              vib={'depth': 22, 'rate': 5.8})                     # a third above, an octave down: a sixth below
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
    sm = touch(TUNE('summit', length=16), 96, 126)
    P('violins1', sm, summit)
    P('flutes', sm, summit)
    P('violins2', sm.octave(-1), summit)
    P('trumpets', sm.octave(-1).vel_add(-4), summit)
    P('horns', sm.octave(-1), summit)
    P('cellos', sm.octave(-2), summit)
    P('choir', harmony(sm.octave(-1), ps_, voices=4, floor=52), summit, shapes='cresc')
    speak(choir_f, orch.lead(sm.shift(summit.start).octave(-1).vel_add(-6).with_length(0), 76, 35))
    speak(choir_m, orch.lead(sm.shift(summit.start).octave(-2).vel_add(-4).with_length(0), 76, 35))
    P('trombones', pads(ps_, ('C3', 'G3'), 3, 96), summit, shapes='cresc')
    P('violas', pads(ps_, ('G4', 'E5'), 2, 90), summit, shapes='cresc')
    P('basses', ps_.bass('root', low='C2', vel=100), summit)
    P('low_brass', ps_.bass('root', low='C2', vel=100), summit, articulations='sustain')
    P('tuba', hold('C1', 3.8, 104, at=12, length=16), summit)
    P('timpani', notes('G#2/4=110 r/2. | A#2/4=112 r/2. | C3/1:3.8=104 | C2/4=124 r/2.'), summit, articulations='hit')
    o.percussion.note(K['cymbal_roll'], summit.bar(3) - 5, 6, 108)
    o.percussion.note(K['crash'], summit.bar(3), 4, 124).note(K['bass_drum'], summit.bar(3), 2, 124)
    P('drums', hold('C1=118 G1=104', 2, at=12, length=16), summit)      # the taikos
    hero.play(g1, art.legato(sm, overlap=0.03).glide(90, where=art.leaps(5)), summit, vib=vib1)
    hero.play(g2, touch(TUNE('Ab4/1 Bb4 | F5/2 G5 | G5/2..', length=16), 90, 116), summit,
              vib={'depth': 20, 'rate': 5.3})
    hero.play(g3, touch(TUNE('C5/1 D5 | A5/2 B5 | E5/2..', length=16), 88, 114), summit,
              vib={'depth': 22, 'rate': 5.8})
    for tr in (b.gtr_l, b.gtr_r):         # Ab Bb C, the last C struck again (each released a breath early: gap=)
        tr.play(notes('gap=0.2 G#2/1=110 A#2=112 C3=114 C3:4:3.6=122').chordify('power').strum(ms=12, bpm=76),
                summit)
    b.bass.play(notes('gap=0.2 Ab1/1=108 Bb1=110 C2=112 C2:4:3.6=120'), summit)
    piano.play(hold('C1 C2 G2 E3 C4 G4', 3.8, 104, at=12, length=16).strum(ms=40, bpm=60), summit)
    orch.ring(o, summit.bar(3), length=2, db=4, roles=['violins1', 'violins2', 'violas', 'cellos', 'choir',
                                                      'horns', 'trumpets', 'trombones'])
    # the choirs' expression lanes (speak()): one lane per track for the whole song, back to 1 after the summit
    for tr in (choir_m, choir_f):
        expr[tr.id] += [(fall.start + 2, 1.0)]
        tr.automate('instrument.expression', expr[tr.id])

    # fall: the tam-tam; the orchestra drops to pianissimo, the hall rings
    o.percussion.note(K['tam_tam'], fall.start, 8, 112)
    # pp, but audible under the tam-tam's ring (it read as a dropout at -34 LUFS: A&R #5)
    P('violins2', hold('Ab4 C5 Eb5', 7.5, 46, length=8), fall, shapes='swell')
    P('cellos', hold('C3', 7.5, 50, length=8), fall, shapes='swell')
    choir_oh.play(hold('C4 Eb4 G4', 7.5, 58), fall)
    choir_oh.automate('instrument.dynamics', [(fall.start, 0.45), (fall.end, 0.3, 'smooth'),
                                              (coda.start + 0.5, 0.12, 'smooth'), (coda.bar(4), 0.22, 'smooth'),
                                              (coda.end, 0.08, 'smooth')])

    # coda: the piano alone with the motif, soft strings, the rolled C major chord (fermata)
    pc = s.prog(P_CODA)
    ca = pianist.arrange(touch(TUNE('coda', length=20), 44, 80), pc, bpm=60, key=s.key, style='ballad', density=0.5, seed=41,
                         devices={'thirds': 1.5, 'sixths': 1.5, 'close': 1.5, 'single': 1}, memory=pmem,
                         at=coda.start, section_end=False)
    piano.play(ca.rh, coda)
    piano.play(broken(pc, vel=40, seed=41), coda)
    last = coda.bar(5)
    final = hold('C1=70 C2=66 G2=58 E3=56 G3=52 D4=50 E4=54 C5=64', 3.95, length=8).strum(ms=85, bpm=50)
    piano.play(final, last)
    piano.automate('instrument.pedal', ca.pedal(pc, coda, end=last) +
                   [(last - 0.05, 0, 'step'), (last + 0.02, 1, 'step')])
    P('violins2', pads(pc, ('G4', 'Eb5'), 2, 34).with_vel(34), coda, shapes='swell')
    P('violas', pads(pc, ('C4', 'G4'), 2, 34), coda, shapes='swell')
    P('cellos', pc.bass('root', low='C3', vel=36), coda, shapes='swell')
    P('violins2', hold('E5 G5', 3.95, 30, at=20, length=24), coda, shapes='dim')
    P('violas', hold('C4 G4', 3.95, 30, at=20, length=24), coda, shapes='dim')
    P('cellos', hold('C3', 3.95, 32, at=20, length=24), coda, shapes='dim')
    orch.ring(o, last, length=3, db=4, roles=['violins2', 'violas', 'cellos'])

    # echo throws on the piano's phrase ends in the coda (the band's echo bus answers in the gaps)
    piano.send('echo', -60)
    thr = []
    for a_ in (3, 7, 11, 15):
        thr += [(a_, -60), (a_ + 0.2, -16, 'smooth'), (a_ + 1.2, -16), (a_ + 1.6, -60, 'smooth')]
    piano.automate('send.echo', thr, at=coda)

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
