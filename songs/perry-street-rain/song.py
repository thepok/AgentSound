"""Perry Street Rain - an original straight-8th piano-trio tune (Ab major, 96 BPM, ~4:30).
Build: python -m agentsound build songs/perry-street-rain

New York bar jazz without swing: a grand piano, an upright bass and brushes after midnight, but the 8ths are even
(a Brad Mehldau / late-Bill-Evans straight-8th feel: jazz harmony, a singing melody, a tight, gently driving pulse).
bands.make('jazz_trio') with a straight Feel (ratio 0.5, small lay-backs) - Salamander grand, Meatbass, Swirly
brushes, the salon room. The tune is a 32-bar AABA:

  A1   Fm9     | Dbmaj7#11 | Bbm9    | Eb7sus4 Eb7b9 | Abmaj9 | Dm7b5 G7b9 | Cm9 F7b9   | Bbm7 Eb7sus4
  A2   Fm9     | Dbmaj7#11 | Bbm9    | Eb7sus4 Eb7b9 | Abmaj9 | Cm7 F7b9   | Bbm9 Eb13  | Abmaj9 Ab13
  B    Dbmaj9  | Gb13#11   | Cm9     | F7alt         | Bbm9   | Dbm6       | Emaj7#11   | Eb7sus4 Eb7b9
  A3   = A2, the last bar turning around (Abmaj9 C7alt) or into the tag (Abmaj9 F7alt)

The hook: a rising Fm9 arpeggio that lands, held, on the 9th (C Eb G), falls back by step (F Eb C) and is sequenced
a third lower over Bbm9; bars 5-8 answer it and resolve by guide tones (Ab-G over G7b9, Gb-F over F7b9). The bridge
climbs in a 3+3+2 rhythm through a backdoor Gb13 and a chromatic Emaj7#11 to the high point.

  intro        4   piano alone, rubato: rolled Dbmaj9 Cm9 Bbm9 Eb7sus4 in the pedal, the hook shape on top; a trill
                   on the Cm9's 9th, a turn on the high C, an arpeggio sweep down into the head
  head        32   the melody harmonized by the pianist (pianist.arrange): guide tones / 3rds / 6ths / drop 2 /
                   quartal under the tune phrase by phrase, ornaments on the long notes (trill, turn, mordent,
                   tremolo, re-struck voicings), runs / sweeps / cascading 4ths in the gaps, the left hand in
                   shells (A) and rootless voicings (bridge, last A); bass in a straight two, brushes stir + taps
  piano_solo  32   A1 the motif with guide tones and answers over left-hand shells, A2 a solo_line (the hook as
                   motif) with runs and 4ths in its gaps, B two-handed: locked hands / drop 2 with tremolos, a
                   shake and alternating-hands breaks, A3 = the climax: the hook an octave up in octaves, blues
                   crushes, repeated notes, octave runs (ride, busier bass)
  bass_solo   16   the Meatbass quotes the hook and sings over the A changes, piano whispers, brushes stir
  head_out    16   the bridge lush (drop 2, locked hands, arpeggio sweeps), the last A quietly (guide tones, a trill)
  tag          4   backdoor tag (Bbm9 Eb13 | Cm7 F7alt | Bbm9 Eb7sus4 | Dbm6 Gb13) as a ballad, ritardando
  end          2   Abmaj9#11 rolled into the pedal, fermata, the room rings
"""
from agentsound import *
from agentsound import bands, jazz, pianist
from agentsound.bandlib import jazz as jazzband
import random

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'Perry Street Rain', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#2b5d7a', '#d9a441'], 'title': 'perry street rain',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 5}

TEMPO = 96
ARRANGED = {}          # section:part -> pianist.Arrangement (filled by build(); inspect what the pianist played)
MASTER_DRIVE = 5.7
PIANO_TRIM = -2.2

# ------------------------------------------------------------------------------------------------ changes
A1 = ('Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Dm7b5:0.5 G7b9:0.5 Cm9:0.5 F7b9:0.5 '
      'Bbm7:0.5 Eb7sus4:0.5')
A2 = ('Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Cm7:0.5 F7b9:0.5 Bbm9:0.5 Eb13:0.5 '
      'Abmaj9:0.5 Ab13:0.5')
BR = 'Dbmaj9 Gb13#11 Cm9 F7alt | Bbm9 Dbm6 Emaj7#11 Eb7sus4:0.5 Eb7b9:0.5'
A3 = ('Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Cm7:0.5 F7b9:0.5 Bbm9:0.5 Eb13:0.5 '
      'Abmaj9:0.5 C7alt:0.5')
A3_OUT = ('Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Cm7:0.5 F7b9:0.5 Bbm9:0.5 Eb13:0.5 '
          'Abmaj9:0.5 F7alt:0.5')
INTRO = 'Dbmaj9 Cm9 Bbm9 Eb7sus4:0.5 Eb7b9:0.5'
TAG = 'Bbm9:0.5 Eb13:0.5 Cm7:0.5 F7alt:0.5 Bbm9:0.5 Eb7sus4:0.5 Dbm6:0.5 Gb13:0.5'
END = 'Abmaj9#11:2'


def even_bass(prog, seed: int, vel: int = 84, style: str = 'two', pickups: float = 0.5) -> Clip:
    """A straight-8th jazz bass line: the root on 1, the fifth / tenth / octave inside the bar, an 8th-note
    approach (chromatic, or the target's fifth) or an anticipation on the & of 4 into the next chord.
    style 'two' = long notes (heads), 'push' = dotted-quarter / quarter motion, 'drive' = 8th pushes (climax)."""
    rng = random.Random(seed)
    chords = [(st, d, c) for st, d, c in prog if c is not None]
    out = []

    def near(pc, ref, lo=28, hi=50):                    # E1 .. D3, closest to the previous note
        cands = [p for p in range(lo, hi + 1) if p % 12 == pc]
        return min(cands, key=lambda p: (abs(p - ref), p))

    prev = 36
    for i, (st, d, c) in enumerate(chords):
        root = near(c.root, prev if i else 34, 28, 43)
        nxt = chords[i + 1][2].root if i + 1 < len(chords) else chords[0][2].root
        nroot = near(nxt, root, 28, 43)
        fifth = root + 7
        third = root + (3 if 3 in {(p - c.root) % 12 for p in c.pcs} and 4 not in {(p - c.root) % 12 for p in c.pcs}
                        else 4)
        seventh = root + (10 if 10 in {(p - c.root) % 12 for p in c.pcs} else 11)
        ap = rng.choice((nroot + 1, nroot - 1, nroot - 1, nroot + 7 if nroot + 7 <= 50 else nroot - 5))
        anticip = rng.random() < 0.18
        last = (nroot, 0.5) if anticip else (ap, 0.5)
        v = lambda x: max(1, min(127, int(round(vel * x * (1 + (rng.random() - 0.5) * 0.08)))))
        if d >= 4:
            if style == 'two':
                mid = rng.choice((fifth, fifth, third + 12 if third + 12 <= 50 else fifth, root + 12))
                if rng.random() < pickups:
                    out += [(st, 2.0, root, v(1.0)), (st + 2, 1.5, mid, v(0.9)), (st + 3.5, 0.5, last[0], v(0.82))]
                else:
                    out += [(st, 2.0, root, v(1.0)), (st + 2, 2.0, mid, v(0.9))]
            elif style == 'push':
                a = rng.choice((fifth, root + 12 if root + 12 <= 50 else fifth))
                b = rng.choice((seventh, fifth, third + 12 if third + 12 <= 50 else third))
                out += [(st, 1.5, root, v(1.0)), (st + 1.5, 1.0, a, v(0.92)), (st + 2.5, 1.0, b, v(0.88)),
                        (st + 3.5, 0.5, last[0], v(0.84))]
            else:   # drive
                out += [(st, 1.0, root, v(1.05)), (st + 1.0, 0.5, root + 12 if root + 12 <= 50 else fifth, v(0.8)),
                        (st + 1.5, 1.0, fifth, v(0.95)), (st + 2.5, 0.5, seventh, v(0.85)),
                        (st + 3.0, 0.5, fifth, v(0.9)), (st + 3.5, 0.5, last[0], v(0.88))]
        else:       # half-bar chords
            if style == 'two' or rng.random() < 0.5:
                out += [(st, 1.5, root, v(1.0)), (st + 1.5, 0.5, last[0], v(0.82))]
            else:
                out += [(st, 1.0, root, v(1.0)), (st + 1.0, 0.5, fifth, v(0.85)), (st + 1.5, 0.5, last[0], v(0.84))]
        prev = root
    notes = sorted(out)
    merged = []                                         # an anticipation ties over: drop the repeated root
    for n in notes:
        if merged and merged[-1][2] == n[2] and abs(merged[-1][0] + merged[-1][1] - n[0]) < 1e-6 \
                and merged[-1][1] <= 0.5:
            s0, d0, p0, v0 = merged[-1]
            merged[-1] = (s0, d0 + n[1], p0, v0)
            continue
        merged.append(n)
    return Clip([(a, d * 0.92, p, v) for a, d, p, v in merged], length=prog.length)


def even_brushes(band, bars: int, seed: int, vel: float = 1.0, ghosts: float = 0.0, kick: str | None = None,
                 hat8: float = 0.0, ride: float = 0.0, fills: bool = True) -> Clip:
    """Straight-8th brushes: the preset's stirs (one per beat at 96 BPM) + taps and hat foot on 2 and 4, plus
    even-8th colour: ghost taps on the &s (ghosts = probability), a feathered kick on 1 and the & of 2 ('even'),
    brush 8ths on the closed hat (hat8 = level), or the ride in even 8ths (1 2 &2 3 4 &4, ride = level)."""
    kit = band.info['kit']
    base = jazzband.brushes(band, bars, style='ballad', kick=None, fills=fills, fill='eighths', vel=vel,
                            taps=ride == 0.0, seed=seed)
    rng = random.Random(seed)
    extra = []
    for b in range(bars):
        t0 = 4.0 * b
        fill_bar = fills and b % 8 == 7
        for k in range(8):
            t = t0 + 0.5 * k
            if fill_bar and t >= t0 + 3.0:
                continue
            if ghosts and k % 2 == 1 and rng.random() < ghosts:
                extra.append((t, 0.2, kit['tap'], int(22 * vel + rng.randint(0, 6))))
            if hat8:
                extra.append((t, 0.2, kit['hat'], int((44 if k % 2 == 0 else 32) * hat8 + rng.randint(-3, 3))))
            if ride and k in (0, 2, 3, 4, 6, 7):
                extra.append((t, 0.4, kit['ride'], int((58 if k in (2, 6) else 46) * ride + rng.randint(-3, 3))))
        if kick == 'even':
            extra.append((t0, 0.3, kit['kick'], int(40 * vel + rng.randint(0, 4))))
            extra.append((t0 + 1.5, 0.3, kit['kick'], int(30 * vel + rng.randint(0, 4))))
            if rng.random() < 0.35 and not fill_bar:
                extra.append((t0 + 3.5, 0.3, kit['kick'], int(28 * vel + rng.randint(0, 4))))
        if ride and b % 2 == 1:                          # the second brush digs on 2 and 4 under the ride
            for x in (1.0, 3.0):
                if not (fill_bar and x >= 3.0):
                    extra.append((t0 + x, 0.25, kit['dig'], int(40 * vel + rng.randint(0, 5))))
    return base | Clip([(a, d, p, max(1, min(127, v))) for a, d, p, v in extra], length=4.0 * bars)


# ------------------------------------------------------------------------------------------------ the head
# agentsound notation (docs/COMPOSE_API.md "Notation"): note values are sticky, '|' checks the bars, g:D5 is a grace
# note; the A sections are named phrases, spliced into lines (hook' = an octave up); length='bar' = whole bars
TUNE = phrases(
    hook='r/4 C5/8 Eb5 G5/4. F5/8 | Eb5/4 C5 r/8 C5 G5 F5 | r/4 Bb4/8 Db5 F5/4. Eb5/8 | Db5/4 Ab4 r/8 G4 Bb4 E5 |',
    hook2='r/4 C5/8 Eb5 G5/4. F5/8 | Eb5/4 C5/8 Bb4 r C5 G5 F5 | r/4 Bb4/8 Db5 F5/4. Eb5/8 | Db5/4 Ab4 r/8 G4 Bb4 g:D5 E5 |',
    a1_end='Eb5/4. C5/8 Bb4/2 | r/8 Ab4 C5 F5 Ab5/4 G5/8 F5 | Eb5/4. D5/8 C5/4 A4/8 Gb4 | F4/2 Ab4/8 Bb4 C5 Eb5',
    a2_end='Eb5/4. C5/8 Bb4/2 | r/8 Bb4 Eb5 G5 Gb5/4 Eb5/8 C5 | Db5/4. C5/8 Bb4/4 G4/8 Bb4 |',
    length='bar')
HEAD_A1 = TUNE('hook a1_end', vel=68)
HEAD_A2 = TUNE('hook2 a2_end Ab4/2 r/8 C5 Eb5 Gb5', vel=78)
HEAD_B = notes("""
 F5/4 Ab4/8 C5 Eb5/2 | Eb5/8 Db5 C5/4 Bb4 r/8 Ab4 | r/4 G4/8 Bb4 D5/2 | Db5/8 Eb5 Db5/4 A4 r/8 C5 |
 C5/4 Db5/8 F5 Ab5/4. Bb5/8 | Bb5/4. Ab5/8 E5/4 Db5/8 E5 | r/4 D#5/8 F#5 G#5/4 B5/8 A#5 | Ab5/4. F5/8 E5 Db5 Bb4 G4""", vel=86, length='bar')
HEAD_A3 = TUNE('hook a2_end Ab4/2 r/4 Gb4/8 E4', vel=80)
HEAD_A3_OUT = TUNE('hook a2_end Ab4/2 r/4 Eb4/8 Db4', vel=72)

# ------------------------------------------------------------------------------------------------ piano solo
SOLO_A1 = notes("""
 r/4 C5/8 Eb5 G5/4 r | r C5/8 Eb5 G5/4 Ab5/8 G5 | F5/4 r/8 Db5 F5 Ab5/4. | Ab5/4 F5/8 Eb5 E5/4 G5/8 Bb5 |
 C6/4. Bb5/8 G5/4 Eb5 | r/8 F5 Ab5 C6 B5/4 Ab5/8 F5 | G5 Eb5 D5 C5 A4 C5 Eb5 Gb5 | F5/2 r/4. C5/8""", vel=80, length='bar')
SOLO_A2 = notes("""
 C5 Eb5 G5 C6/4 Bb5/8 Ab5 G5 | F5/4 r/8 Eb5 F5 G5 Ab5 C6 | Db6/4 C6/8 Bb5 Ab5 F5 Db5 C5 | Db5 Eb5 F5 Ab5 G5 E5 Db5 Bb4 |
 C5/4 r/8 C5 Eb5 G5 Bb5/4 | G5 Eb5/8 C5 Eb5 Gb5 A5 C6 | Db6/4 C6/8 Ab5 G5 C6 Bb5 Db6 | C6/2 r/8 Gb5 F5 Eb5""", vel=86, length='bar')
SOLO_B = notes("""
 Eb5/4. F5 Ab5/4 | Ab5/4. Bb5 C6/4 | D6/4. C6 Bb5/4 | A5/4. Ab5 Gb5/8 F5 |
 F5/4. Ab5 C6/4 | Db6/4. Bb5 Ab5/4 | G#5/4. B5 D#6/4 | Db6/4. Bb5/8 G5 E5 Db5 Bb4""", vel=96, length='bar')
SOLO_A3 = TUNE("hook' a2_end' Ab5/2 r/4 Gb5/8 E5", vel=100)      # the climax: the last A an octave up

# ------------------------------------------------------------------------------------------------ bass solo
BASS_SOLO = notes("""
 r/4 C3/8 Eb3 G3/4. F3/8 | Eb3/4 C3 r/8 Ab2 G2 F2 | r/4 Bb2/8 Db3 F3/4. Eb3/8 | Db3/4 Ab2 r/8 G2 Bb2 Db3 |
 C3/4. Bb2/8 G2/4 Eb2 | r/8 F2 Ab2 C3 B2/4 Ab2/8 F2 | Eb2/4 G2/8 Bb2 A2 C3 Eb3 Gb3 | F3/4. Db3/8 Bb2/4 Ab2/8 Bb2 |
 F2/4 r/8 C3 Eb3 F3 G3 Ab3 | C4/4 Ab3/8 F3 G3/4 Eb3/8 C3 | Db3/4 r/8 Bb2 Db3 F3 Ab3 C4 | Bb3/4 Ab3/8 F3 E3 Db3 Bb2 G2 |
 Ab2/4. C3/8 Eb3 G3 Bb3/4 | C4 G3/8 Eb3 A3/4 F3/8 Eb3 | Db3/4. C3/8 Bb2/4 G2/8 Eb2 | Ab2/2 r/4 Eb2/8 C2""", vel=96, length='bar')
BASS_SLIDES = [(0, 1.5, -2.0), (4, 0.0, -1.0), (9, 0.0, -2.0), (12, 0.0, -1.0)]   # (bar, beat, from semitones)

# ------------------------------------------------------------------------------------------------ intro / tag / end
# rolled grips in the pedal (released a breath before the next one: gap=), the hook shape on top
INTRO_LH = notes('gap=0.1 [Db2=60 Ab2=52]/1 [C2=58 G2=50] [Bb1=64 F2=54] [Eb2=62 Bb2=52]/2 [Eb2=58 Db3=50]')
INTRO_RH = notes({'grips': 'gap=0.2 [F4=50 Ab4=52 C5=54 Eb5=70]/1 [Eb4=48 G4=50 Bb4=52] '
                           'gap=0 [Db4=52 F4=52 Ab4=54 C5=68]:4:1.4 gap=0.1 [Db4=50 F4=52 Ab4=54 C5=66]/2 [E4=48 G4=52 Bb4=60]',
                  'top': 'r:2.5 G5/8=64 F5/4=60 r:2.5 F5/8=58 Eb5/4=56 r:1.5 F5/8=68 Ab5=76'}, length=16)
TAG_RH = notes("""
 r/4 Bb4/8 Db5 F5/4 G5/8 C6 | Bb5/4 G5/8 Eb5 Db5/4 A4/8 Gb4 | F4/4 Ab4/8 Db5 F5/4 Eb5/8 Db5 | E5/4. Db5/8 Bb4/4 Ab4/8 Eb5""", vel=68, length='bar')
END_LH = hold('Ab2=60 Eb3=48 G3=50', 7.9, length=8)
END_RH = hold('D5=72 G5=76 Bb5=78 C6=84 Eb6=100', 7.6, length=8)


def build() -> Song:
    s = Song('Perry Street Rain', tempo=TEMPO, key='Ab major', seed=5, tail=6)
    secs = [('intro', 4), ('head', 32), ('piano_solo', 32), ('bass_solo', 16), ('head_out', 16), ('tag', 4),
            ('end', 2)]
    intro, head, solo, bsolo, hout, tag, end = (s.section(n, bars=b) for n, b in secs)
    feel = jazz.Feel(TEMPO, ratio=0.5, layback={'piano': 9, 'comp': 5, 'bass': -2, 'drums': 0})
    # dynamics pass: touch() plays the melody ~3 dB louder on average and its accents hit the master limiter (at
    # the preset's drive the loudest solo onsets lost up to 7 dB, 9.4 dB of onset spread into the master, 5.2 out)
    # -> the piano trimmed 2.5 dB, the drive set for -15.7 LUFS
    b = bands.make('jazz_trio', s, feel=feel, master_gain=MASTER_DRIVE)
    b.piano.gain_db += PIANO_TRIM
    kit = b.info['kit']
    # the Salamander at mp read dull: air, not bite (a 4.2 kHz shelf made the loud notes glassy - "es klingt hart";
    # the preset's jazz_grand keeps the loud layers warm)
    b.piano.add_fx(fx.eq({'high.freq': 5500, 'high.gain': 2.0}))
    b.comp.add_fx(fx.eq({'high.freq': 4200, 'high.gain': 1.5}))
    s.master.add_fx(fx.eq({'high.freq': 8000, 'high.gain': 2.5}), first=True)   # air (the room IR is dark)
    P = {k: s.prog(v) for k, v in (('A1', A1), ('A2', A2), ('B', BR), ('A3', A3), ('A3o', A3_OUT),
                                   ('intro', INTRO), ('tag', TAG), ('end', END))}
    form = [('A1', 0), ('A2', 8), ('B', 16), ('A3', 24)]
    rng = random.Random(9)

    def comp(sec, part, bar, style, dens, inten, seed, answer=None, voicing='rootless', reg=('A2', 'G4'),
             roll=(8, 22), vel=None):
        c = jazz.comp(P[part], style=style, voicing=voicing, density=dens, intensity=inten, seed=seed,
                      register=reg, answer=answer, vel=vel)
        b.comp.play(c.roll(roll, seed=rng, bpm=TEMPO), sec.bar(bar))     # rolled grips (a seeded speed)

    def bass(sec, part, bar, seed, vel, style='two', pickups=0.5):
        # a bassist's touch on the line (jazz.bass_touch): 4-bar arcs around `vel`, the root on 1 leading, the
        # pushed 8ths lighter, anticipations leaning in - the evened Meatbass answers it (~6 dB per phrase)
        line = jazz.bass_touch(even_bass(P[part], seed, vel, style, pickups), vel * 0.84, vel * 1.22, accent='1-3',
                               seed=seed)
        b.bass.play(line, sec.bar(bar))

    hands_memory = pianist.Memory()
    # ============================================================== intro: piano alone, rubato, pedalled
    # pianist moves on top of the rolled grips: a trill on the Cm9's 9th (D-Eb, the pedal lifted for it), a turn on
    # the high C, an arpeggio sweep down the Eb7b9 into the head
    b.comp.play(INTRO_LH.strum(ms=60, bpm=TEMPO), intro)
    b.piano.play(INTRO_RH.roll((30, 45), seed=rng, bpm=TEMPO), intro)
    b.piano.play(pianist.trill('D5', 2.5, TEMPO, chord='Cm9', rate=13.5, vel=66, seed=11), intro.beat(4))
    hands_memory.played(intro.beat(4), 'trill')      # the ornament budget counts it (pianist.Memory)
    hands_memory.save(solo.bar(31))                  # ... and saves its fast figure for the climax (solo A3's end)
    b.piano.play(pianist.turn('C6', 1.5, TEMPO, chord='Bbm9', vel=88, ms=80), intro.beat(10.5))
    b.piano.play(pianist.sweep('Eb7b9', 1.35, TEMPO, low='C5', high='Db6', direction='down', ring=False,
                               vel=(62, 44), seed=12), intro.beat(14.5))
    b.piano.automate('instrument.pedal', pianist.pedal(P['intro'], intro, dry=[(4.0, 5.9)]))
    jazzband.pedal([b.comp], P['intro'], intro)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(14, 46)), intro.beat(-2))

    def hands(sec, part, bar, mel, *, pedal_rh=True, lh='guide', lh_vel=56, bpm=TEMPO, **kw):
        """The pianist plays `mel` over P[part]: the right hand harmonized, decorated and filled, the left hand
        on the comping track; the piano's pedal follows the harmony and lifts for runs. One pianist.Memory for the
        whole song: the ornament budget (fast two-key alternations about one per 16 bars) counts song-wide."""
        at = sec.bar(bar)
        arr = pianist.arrange(mel, P[part], bpm=bpm, key=s.key, lh=lh, lh_vel=lh_vel, memory=hands_memory, at=at,
                              **kw)
        b.piano.play(arr.rh, at)
        if len(arr.lh):
            b.comp.play(arr.lh, at)
        if pedal_rh:
            b.piano.automate('instrument.pedal', arr.pedal(P[part], at))
        ARRANGED[f"{sec.name}:{part}"] = arr
        return arr

    # ============================================================== head: the melody, harmonized by the pianist
    # a pianist's touch (jazz.touch) on the tune first, then pianist.arrange: phrase by phrase a voicing device
    # under the melody (guide tones, 3rds / 6ths, drop 2, quartal ...), ornaments on the long notes, fills in the
    # gaps, the left hand on the comping track (shells in the A sections, rootless voicings from the bridge) - no
    # separate comping part any more: one pianist, two hands. The head builds A1 < A2 < B, the last A settles.
    heads = {'A1': jazz.touch(HEAD_A1, 46, 88), 'A2': jazz.touch(HEAD_A2, 48, 94), 'B': jazz.touch(HEAD_B, 54, 104),
             'A3': jazz.touch(jazz.paraphrase(HEAD_A3, seed=3, anticipate=0.0, delay=0.0, embellish=0.15,
                                              key=s.key), 50, 98)}
    hands(head, 'A1', 0, heads['A1'], style='straight', density=0.45, seed=201, lh_vel=52, inner=0.76)
    hands(head, 'A2', 8, heads['A2'], style='straight', density=0.6, seed=202, lead_in=True, lh_vel=55, inner=0.76,
          ornaments={'trill': 2.0, 'restrike': 1.5, 'turn': 1.0, 'tremolo': 1.0, 'crush': 0.8})
    hands(head, 'B', 16, heads['B'], style='straight', density=0.85, seed=203, lead_in=True, lh='rootless',
          lh_vel=58, devices={'drop2': 2.5, 'octave': 1.5, 'sixths': 1.5, 'quartal': 1.5, 'guide': 1.0},
          fills={'run': 2.0, 'fourths': 2.0, 'arpeggio': 2.0, 'hands': 1.0, 'chromatic': 1.0},
          ornaments={'tremolo': 2.0, 'trill': 1.0, 'restrike': 1.0, 'turn': 1.0})
    hands(head, 'A3', 24, heads['A3'], style='lush', density=0.6, seed=204, lead_in=True, lh='rootless',
          lh_vel=54)
    jazzband.pedal([b.comp], P['A1'] + P['A2'] + P['B'] + P['A3'], head)
    bass(head, 'A1', 0, 31, 81, 'two', 0.35)
    bass(head, 'A2', 8, 32, 85, 'two', 0.6)
    bass(head, 'B', 16, 33, 92, 'push')
    bass(head, 'A3', 24, 34, 92, 'push')
    b.drums.play(even_brushes(b, 8, 41, vel=0.52), head)
    b.drums.play(even_brushes(b, 8, 42, vel=0.7, ghosts=0.4, kick='even'), head.bar(8))
    b.drums.play(even_brushes(b, 16, 43, vel=0.8, ghosts=0.55, kick='even'), head.bar(16))

    # ============================================================== piano solo: lines, two hands, the climax
    # A1 the motif with guide tones and answers over left-hand shells; A2 an improvised line (jazz.solo_line with
    # the hook as motif) with runs / 4ths in its gaps; B two-handed chords (locked hands, drop 2) with tremolos, a
    # shake and alternating-hands breaks; A3 the climax: the hook an octave up in octaves, blues crushes, repeated
    # notes, octave runs. The right hand plays the lines dry (no pedal) except in the chordal bridge.
    line_a2 = jazz.solo_line(P['A2'], key=s.key, register=('Bb4', 'Db6'), density=0.7, intensity=0.6, seed=14,
                             motif=HEAD_A1.slice(0, 4), motif_prob=0.5, phrase_bars=(1, 2), triplets=0.15)
    hands(solo, 'A1', 0, jazz.touch(SOLO_A1, 56, 104), style='sparse', density=0.55, seed=301, lead_in=True,
          pedal_rh=False, lh_vel=56, fills={'answer': 2.0, 'run': 1.5, 'pentatonic': 1.0},
          ornaments={'mordent': 1.0, 'crush': 1.0, 'turn': 1.0, 'trill': 1.0})
    hands(solo, 'A2', 8, jazz.touch(line_a2, 60, 108), style='straight', density=0.6, seed=302, lead_in=True,
          pedal_rh=False, lh_vel=58, devices={'single': 3.0, 'guide': 2.0, 'thirds': 1.0},
          fills={'run': 2.0, 'chromatic': 2.0, 'fourths': 2.0, 'pentatonic': 1.5},
          ornaments={'trill': 1.5, 'mordent': 1.0, 'turn': 1.0, 'crush': 1.0})
    hands(solo, 'B', 16, jazz.touch(SOLO_B, 72, 114), style='lush', density=0.85, seed=303, lead_in=True, embellish=0.3,
          lh='rootless', lh_vel=62, voices=3, devices={'locked': 3.0, 'drop2': 2.0, 'octave': 1.0},
          ornaments={'tremolo': 1.5, 'restrike': 1.0, 'roll': 0.6, 'turn': 0.6},
          fills={'hands': 3.0, 'arpeggio': 1.0, 'tremolo': 1.0})
    hands(solo, 'A3', 24, jazz.touch(SOLO_A3, 76, 116), style='bar', climax=True, density=0.9, seed=332,
          lead_in=True, pedal_rh=False, lh='rootless', lh_vel=66, quick=0.15,
          ornaments={'blues_crush': 2.0, 'slip': 0.5, 'crush': 0.5, 'repeated': 1.5, 'trill': 1.0, 'tremolo': 1.0,
                     'shake': 1.5},
          fills={'hands': 3.0, 'octave_run': 1.0, 'chromatic': 1.0, 'repeated': 0.5})
    bass(solo, 'A1', 0, 61, 86, 'push')
    bass(solo, 'A2', 8, 62, 90, 'push')
    bass(solo, 'B', 16, 63, 92, 'push')
    bass(solo, 'A3', 24, 64, 96, 'drive')
    b.drums.play(even_brushes(b, 8, 71, vel=0.8, ghosts=0.5, kick='even'), solo)
    b.drums.play(even_brushes(b, 8, 72, vel=0.85, ghosts=0.3, kick='even', hat8=0.8), solo.bar(8))
    b.drums.play(even_brushes(b, 8, 73, vel=0.9, kick='even', hat8=0.9), solo.bar(16))
    b.drums.play(even_brushes(b, 8, 74, vel=1.0, kick='even', ride=0.95), solo.bar(24))
    b.drums.play(Clip([(0, 2, kit['crash'], 40)], length=4), solo.bar(24))

    # ============================================================== bass solo: the hook in the bass, piano whispers
    b.bass.play(jazz.touch(BASS_SOLO, 68, 96), bsolo)        # the solo sung like a melody: phrase arcs, peaks
    bend = []
    for bar, beat, frm in BASS_SLIDES:
        t = bsolo.bar(bar) + beat
        bend += [(t - 0.03, 0.0, 'step'), (t - 0.01, frm, 'step'), (t + 0.2, 0.0, 'smooth')]
    b.bass.automate('instrument.pitchbend', bend)
    # the bassist steps up for the solo: +1 dB, then back ('gainDb' lanes are dB on the track's gain_db)

    b.bass.automate('gainDb', [(0, 0.0), (bsolo.start - 1, 0.0), (bsolo.start, 1.0, 'smooth'),
                               (hout.start - 1, 1.0), (hout.start, 0.0, 'smooth')])
    comp(bsolo, 'A1', 0, 'sparse', 0.3, 0.22, 131, answer=BASS_SOLO.slice(0, 32), voicing='shell',
         reg=('C3', 'A4'), roll=(20, 40), vel=44)                     # the piano whispers under the bass
    comp(bsolo, 'A2', 8, 'sparse', 0.3, 0.25, 132, answer=BASS_SOLO.slice(32, 64), voicing='shell',
         reg=('C3', 'A4'), roll=(20, 40), vel=46)
    jazzband.pedal([b.comp], P['A1'] + P['A2'], bsolo)
    # the piano announces the head out: a glissando-like Ab13 scale sweep up into its first note (F5)
    b.piano.play(pianist.gliss('F5', 1.0, TEMPO, chord='Ab13', span=17, vel=(40, 84), seed=13), bsolo.beat(-1))
    b.drums.play(even_brushes(b, 16, 141, vel=0.55, fills=False), bsolo)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(22, 56)), bsolo.beat(-2))

    # ============================================================== head out: the bridge lush, the last A quiet
    hands(hout, 'B', 0, jazz.touch(HEAD_B, 66, 108), style='lush', density=0.85, seed=401, lead_in=True,
          lh='rootless', lh_vel=60, devices={'drop2': 3.0, 'locked': 1.5, 'close': 1.5, 'ust': 1.0},
          fills={'arpeggio': 2.0, 'fourths': 1.0, 'run': 1.0})
    last_a = jazz.touch(jazz.paraphrase(HEAD_A3_OUT, seed=8, anticipate=0.0, embellish=0.1, key=s.key), 48, 88)
    hands(hout, 'A3o', 8, last_a, style='sparse', density=0.45, seed=402, lead_in=True, lh_vel=50,
          ornaments={'trill': 1.5, 'turn': 1.0, 'mordent': 1.0, 'restrike': 1.0},
          fast_every=16)                               # sparse plays no fast figure - except a trill on the last note
    jazzband.pedal([b.comp], P['B'] + P['A3o'], hout)
    bass(hout, 'B', 0, 161, 93, 'push')
    bass(hout, 'A3o', 8, 162, 81, 'two', 0.4)
    b.drums.play(even_brushes(b, 8, 171, vel=0.85, ghosts=0.5, kick='even'), hout)
    b.drums.play(even_brushes(b, 8, 172, vel=0.6, ghosts=0.2), hout.bar(8))

    # ============================================================== tag + ending
    # the tag as a ballad (rolled voicings, a trill / tremolo on its long notes); the moves are timed for the
    # ritardando's slower tempo
    tag_arr = hands(tag, 'tag', 0, jazz.touch(TAG_RH, 46, 86), style='ballad', density=0.55, seed=501, lead_in=True,
                    pedal_rh=False, lh='rootless', lh_vel=48, bpm=TEMPO * 0.85, section_end=False)
    b.piano.automate('instrument.pedal', tag_arr.pedal(P['tag'], tag, end=end.start - 0.1))
    jazzband.pedal([b.comp], P['tag'], tag, end=end.start - 0.1)
    bass(tag, 'tag', 0, 191, 82, 'two', 0.3)
    b.drums.play(even_brushes(b, 3, 201, vel=0.5, fills=False), tag)
    b.drums.play(jazz.brush_fill('swell', 4, kit=kit, vel=(12, 44)), tag.beat(-4))
    b.comp.play(END_LH.strum(ms=70, bpm=TEMPO * 0.72), end)
    b.piano.play(END_RH.strum(ms=80, bpm=TEMPO * 0.72).shift(0.25), end)
    for t in (b.piano, b.comp):
        t.automate('instrument.pedal', [(-0.05, 0.0, 'step'), (0.02, 1.0, 'step')], at=end)
    b.bass.note('Ab1', end, dur=7, vel=92)
    b.drums.play(Clip([(0, 8, kit['crash'], 28), (0, 0.5, kit['kick'], 30), (0, 2, kit['sweep'], 56),
                       (2, 2, kit['sweep'], 44), (4, 3, kit['sweep'], 32)], length=8), end)

    # ============================================================== time
    s.rubato(intro, depth=0.06, phrase='lean')
    s.ritardando((tag.bar(2), end.start), to=0.72, a_tempo=False)
    s.fermata(end.start, hold=2, length=4)
    for t in (b.piano, b.comp):
        t.automate('send.room', ramp(end.start, end.end, -13, -8))
    return s
