"""Lanterns on Carmine Street - an original medium-swing tune for tenor quartet (Eb major, 140 BPM, ~4:05).
Build: python -m agentsound build songs/lanterns-on-carmine

A small group in a Village club after midnight: Salamander grand, Meatbass upright, Swirly brushes, the MTG tenor
(bands.make('jazz_quartet')). The tune is a 32-bar AABA:

  A1   Ebmaj7 | C7b9      | Fm9 | Bb13          | Gm7 C7b9 | Fm7 Bb7 | Ebmaj7 C7b9 | Fm7 Bb7
  A2   Ebmaj7 | Gb7#11    | Fm9 | Bb7sus4 Bb7b9 | Gm7 C7b9 | Fm7 Bb7 | Eb6         | Bbm7 Eb7    (tritone sub, sus)
  B    Abmaj7 | Db9       | Gm7 | C7b9          | Cm9      | F13     | Fm9         | E7#11       (backdoor, V/V, tritone sub)
  A3   = A2 with the A1 ending (turnaround into the next chorus / the tag)

The head's motif is a rising arpeggio that lands, syncopated, on the maj7 (Bb Eb G - D) and falls back through the
b9 of the dominant; bar 3 sequences it a half step higher onto the 7th of Fm; the bridge sequences a two-bar
phrase (Ab: G..C / Db9: #11) down a step (Gm / C7b9: #11) and climbs to Eb5 over Cm9 before the tritone sub E7#11
leads home.

  intro       4   piano alone in time: rolled drop-2 block chords preview the motif over a Bb pedal, brushes stir
  head       32   tenor states the head (A2/A3 paraphrased), bass in two for the A's then walking; piano fills the
                  gaps at the end of A1 and A2, comping answers the horn
  sax_solo   32   tenor chorus: quotes the motif, sequences it, bebop lines with enclosures, builds through the
                  bridge (brushes move to the ride) to the high E5 over Gb7#11, winds down
  piano_solo 32   drops back: single-note lines (motif development), bridge in locked-hands block chords, last A
                  in octaves, left hand in shells
  bass_solo  16   Meatbass solo over the A's (slides, ghosts), piano whispers, brushes just stir + hat foot
  head_out   16   tenor takes it from the bridge, calmer
  tag         6   iii-VI-ii-V tag, then with tritone subs, ritardando
  end         2   rolled Ebmaj9#11, tenor holds the 3rd with a swell and vibrato, fermata, the room rings
"""
import functools
import random

from agentsound import *
from agentsound import bands, jazz, pianist
from agentsound.bandlib import jazz as jazzband

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'Lanterns on Carmine Street', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#1d3f8f', '#e3a72f'], 'title': 'lanterns on carmine street',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 11}

TEMPO = 140

CHANGES = {
    'A1': 'Ebmaj7 C7b9 Fm9 Bb13 | Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Ebmaj7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5',
    'A2': 'Ebmaj7 Gb7#11 Fm9 Bb7sus4:0.5 Bb7b9:0.5 | Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Eb6 Bbm7:0.5 Eb7:0.5',
    'B': 'Abmaj7 Db9 Gm7 C7b9 | Cm9 F13 Fm9 E7#11',
    'A3': 'Ebmaj7 Gb7#11 Fm9 Bb7sus4:0.5 Bb7b9:0.5 | Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Ebmaj7:0.5 C7b9:0.5 Fm7:0.5 '
          'Bb7:0.5',
    'intro': 'Fm9 Bb13 Fm9 Bb7b9',
    'tag': 'Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Gm7:0.5 Gb7#11:0.5 Fm7:0.5 E7#11:0.5 Gm7:0.5 C7alt:0.5 Fm9:0.5 '
           'Bb7sus4:0.5',
}
FORM = 'intro:4 head:AABA sax_solo:AABA piano_solo:AABA bass_solo:AA head_out:B,A3 tag:6 end:2'

# ------------------------------------------------------------------------------------------------ the head (concert)
# notation: sticky note values, g: grace notes (crushed, 0.11 beats at 0.78 x), ! / ? accents / ghosts
L = dict(accent=1.12, ghost=0.7, grace=0.11, gracevel=0.78, length='bar')
TUNE = phrases(up='r/8 Bb3 Eb4 G4/4', mid='| Db5/8 C5 Bb4 G4 E4/4 r | r/8 C4 F4 Ab4/4 Eb5/4. |',
               home='r/4 F4/8 G4 Bb4 Db5 C5 B4 | C5/4 Bb4/8 Ab4 F4 Ab4/4. |', **L)
HEAD_A1 = TUNE('up g:C#5 D5/4. mid D5/8 C5 Ab4 F4 G4/4. r/8 | home G4/2. r/4 | r/1', vel=76)
HEAD_A2 = TUNE("""up D5/4. mid Eb5/8 C5 Ab4 F4 G4/4. r/8 |
 r D5 Bb4 G4 E4 G4 Bb4 Db5 | C5 Eb5 C5 Ab4 F4 Ab4 A4 g:C#5 D5 | Eb5/2. r/4 | r/1""", vel=82)
HEAD_B = notes("""
 r/8 Eb4 F4 G4 C5/2 | B4/8 Ab4 F4 G4:5/8 | r/8 D4 F4 G4 Bb4/2 | Bb4/8 G4 E4 F#4:5/8 |
 r/8 G4 Bb4 D5 Eb5/2 | D5/8 C5 A4 F4 Eb4/4 G4/8 Ab4 | Ab4/4. G4/8 F4 C5/4. | B4/8 A#4 G#4 E4 D4/2""", vel=92, **L)
HEAD_A3 = TUNE('up g:C#5 D5/4. mid Eb5/8 C5 Ab4 F4 G4/4. r/8 | home G4/2. r/4 | r/1', vel=84)

# ------------------------------------------------------------------------------------------------ the tenor solo
SAX_SOLO = [
    notes("""r/4 Bb3/8 Eb4 G4 D5/4. | r/8 Db5 C5 Bb4 Ab4 G4 E4/4 | r C4/8 F4 Ab4 Eb5/4. | r/8 D5 C5 Bb4 Ab4 G4 F4/4 |
             r F4/8 G4 Bb4 G4 E4 Db4 | C4 Eb4 F4 Ab4 D5 C5 Ab4 F#4 | G4/4. r/8 Bb4 A4 Bb4 Db5 | C5/4 r/2.""",
          vel=82, **L),
    notes("""r/4 D5/8t Eb5 D5 Bb4/8 G4 F4 Eb4 | E4 Gb4 Bb4 Db5 C5/4 Bb4/8 Ab4 | G4/4 r/8 C4 Eb4 F4 Ab4 C5 |
             Eb5 C5 Bb4 Ab4 B4 Ab4 F4 D4 | r F4 A4 C5 Bb4 Db5 C5 Bb4 | Ab4 G4 F4 Eb4 D4 F4 Ab4 C5 |
             Bb4/4 G4/8 Bb4 C5/4. r/8 | r Db5 C5 Bb4 G4 Bb4 Db5 C5""", vel=92, **L),
    notes("""r/4 Eb4/8 F4 Ab4 C5 Eb5! C5 | B4/4 Ab4/8 F4 Eb4/4 r/8 F4 | Bb4/8t A4 G4 F4/8 D4 F4 G4 Bb4 D5 |
             E4 G4 Bb4 Db5 C5/4 Bb4/8 G4 | r G4 Bb4 D5 Eb5/4! D5/8 C5 | D5/4 A4/8 C5 Eb5/4! D5/8 C5 |
             Ab4/4 G4/8 F4 Eb4 C4 Eb4 F4 | G#4 B4 D5 B4 G#4 A#4 B4 C#5""", vel=100, **L),
    notes("""D5/4.! Eb5/8 D5 Bb4 G4 Bb4 | r Db5 E5/4.! Db5/8 Bb4 Ab4 | C5 Ab4 Eb5 D5 C5 Ab4 F4 G4 |
             Ab4/4 Eb4/8 F4 B4 Ab4 F4 D4 | D4 F4 A4 C5 Bb4 G4 E4 Db4 | C4/4 r/8 F4 D5/8t C5 Bb4 Ab4/8 F#4 |
             G4/1 | r""", vel=108, **L),
]

# ------------------------------------------------------------------------------------------------ piano parts
INTRO_RH = notes('r/4 C5/8 F5 Ab5 G5/4. | F5/8 D5 C5 Ab4 G4/2 | r/4 C5/8 F5 Ab5 Eb6/4. | D6/8 B5 Ab5 F5 D5/4 r',
                 vel=56, **L)
INTRO_LH = notes('[Ab2=58 Eb3=54 G3=52]/1:3.6 [Ab2=56 D3=52 G3=50]/1:3.6 [Ab2=60 Eb3=55 G3=53]/1:3.6 '
                 '[Ab2=60 D3=56 B3=55]/1:3.2')
FILL_A1 = notes('r:29 Ab5/8t G5 F5 D5/8 F5 Ab5 G5', vel=72, **L)
FILL_A2 = notes('r:29 Db5/8t F5 Ab5 G5/8 Db5 Bb4 B4', vel=74, **L)
FILL_OUT = notes('r:24 r/2. G5/8t F5 Eb5 | D5/8 C5 Bb4 Ab4 G4/4 r', vel=66, **L)
PIANO_BRIDGE = notes("""r/8 Eb5 F5 G5/4 Eb5/8 C5/4 | r/8 Eb5 F5 G5/4 F5/8 B4/4 | r/8 D5 F5 A5/4 G5/8 F5/4 |
                        r/8 Db5 E5 G5/4 E5/8 Db5 Bb4 | r G5 Bb5 D6/4 C6/8 Bb5 G5 | A5/4 D6/8 C6 A5 F5 Eb5 D5 |
                        C5/4 Eb5/8 F5 Ab5/4 G5/8 F5 | E5 G#5 B5 A#5 G#5 E5 D5/4""", vel=84, **L)

# ------------------------------------------------------------------------------------------------ bass solo
BASS_SOLO = notes("""
 r/4 Bb2/8 Eb3? G3/4 F3/8 D3 | C3/4. Db3/8 E3 G3 Bb3/4 | Ab3 G3/8 F3 C3/4 r | r/8 D3 F3? G3 Ab3/4 F3/8 D3? |
 Bb2/4 D3/8 F3 E3/4 G3/8 Bb3 | Ab3/4 F3/8? C3 D3/4 Ab2/8? A2 | Eb3/8t F3 G3 Bb3/4 r/8 G3 E3 C3 | F2/4 Ab2/8 C3 D3/4 r |
 Bb2 r/8 G3 F3? Eb3 D3 Bb2? | Bb2/4 Db3/8 E3 Gb3/4 r | r/8 F3 Ab3 C4/4. Bb3/8 G3 | Ab3/4 F3/8 Eb3? D3 F3? Ab3 B3 |
 Bb3/4 A3/8 G3 E3 Db3 C3 r | r C3 Eb3 F3 D3/4 r | Eb3 r/8 Bb2 C3 Eb3 G3/4 | F3/8 Db3 Bb2 Ab2 G2/4 Bb2/8 A2""",
                  vel=100, **L)
BASS_SLIDES = [(0, 2.0, -2.0), (2, 0.0, -1.0), (10, 1.5, -2.0), (14, 3.0, -1.0)]   # (bar, beat, from semitones)

# ------------------------------------------------------------------------------------------------ tag / ending
TAG_SAX = TUNE('home r/4 F4/8 G4 Bb4 Db5 C5 Bb4 | Ab4/4 G4/8 F4 E4/4 D4/8 E4 | g:A4 Bb4/4 A4/8 Bb4 Db5/4 C5/8 Bb4 | '
               'Ab4/4. G4/8 F4/4 Eb4/8 F4', vel=74)
END_SAX = notes('G4:8', vel=74, **L)
GRID = jazz.each('triplet', 'swing', 'triplet', 'swing')          # the walking line's skip notes, part by part


def bass_fill(bass, at, vel=92):
    """A triplet fill down the Bb7 into the next chorus (replaces beats 3-4 of the bar before it)."""
    bass.clear(at + 2.0, at + 4.0)
    for i, p in enumerate(('F3', 'D3', 'Bb2', 'Ab2', 'F2', 'E2')):
        bass.note(p, at + 2.0 + i / 3.0, dur=0.3, vel=vel - (8 if i in (1, 4) else 0))


def build() -> Song:
    s = Song('Lanterns on Carmine Street', tempo=TEMPO, key='Eb major', seed=11, tail=6)
    intro, head, sax_solo, piano_solo, bass_solo, head_out, tag, end = s.form(FORM, parts=CHANGES)
    b = bands.make('jazz_quartet', s, master_gain=4.0)
    kit, horn = b.info['kit'], b.info['horn']
    rng = random.Random(7)
    # the comping (jazz.comp, rolled: a pianist's hands never land flat), the walking bass and the brushes per part
    play = functools.partial(jazz.chorus, b, lh_pedal=False, defaults=dict(
        comp=dict(voicing='rootless', register=('A2', 'G4'), roll=(8, 22), roll_seed=rng, direction='down'),
        bass=dict(feel='four', skip=0.12)))

    # ============================================================== intro: piano alone in time, Bb pedal
    b.piano.play(jazz.block_chords(INTRO_RH, intro.prog, style='drop2', vel=0.8).strum(ms=16, bpm=TEMPO), intro)
    b.comp.play(INTRO_LH.strum(ms=55, bpm=TEMPO), intro)
    jazzband.pedal([b.piano, b.comp], intro)
    b.bass.play(jazz.walking_bass(intro.prog, key=s.key, feel='two', pedal=[(0, 16, 'Bb1')], vel=62, seed=1), intro)
    b.drums.play(jazzband.brushes(b, 4, style='two', fills=False, kick=None, vel=0.45, seed=1), intro)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(18, 52)), intro.bar(3))

    # ============================================================== head: the tenor
    heads = [HEAD_A1, jazz.paraphrase(HEAD_A2, seed=2, anticipate=0.35, embellish=0.25, key=s.key), HEAD_B,
             jazz.paraphrase(HEAD_A3, seed=3, anticipate=0.3, delay=0.2, embellish=0.2, key=s.key)]
    jazz.horn_line(heads[0] + heads[1] + heads[2] + heads[3], TEMPO, seed=11, scoop=0.4, fall=0.35,
                   **horn).place(b.sax, head)
    b.piano.play(FILL_A1, head)                        # piano fills in the horn's gaps, comping answers
    b.piano.play(FILL_A2, head.bar(8))
    play(head, heads, comp=dict(style=jazz.each('charleston', 'swing', 'swing', 'charleston'), seed=21,
                                density=jazz.each(0.35, 0.45, 0.55, 0.5), intensity=jazz.each(0.3, 0.38, 0.45, 0.42)),
         bass=dict(seed=31, feel=jazz.each('two', 'two', 'four', 'four'), vel=jazz.each(72, 78, 90, 90),
                   skip=jazz.each(0.2, 0.25, 0.12, 0.12), skip_grid=GRID),
         drums=[(16, dict(style='two', vel=0.58, seed=41)), (16, dict(style='medium', vel=0.85, seed=42))])
    bass_fill(b.bass, head.bar(31))
    b.drums.play(jazz.brush_fill('triplets', 1, kit=kit, vel=(30, 70)), head.bar(31))

    # ============================================================== tenor solo
    for i, part in enumerate(sax_solo.parts):
        jazz.horn_line(jazz.phrase_dynamics(SAX_SOLO[i], offbeat=1.07, ghost=0.82), TEMPO, seed=50 + i,
                       scoop=0.35 + 0.1 * i, fall=0.45, **horn).place(b.sax, part.start)
    play(sax_solo, SAX_SOLO, comp=dict(style=jazz.each('garland', 'swing', 'swing', 'charleston'), seed=60,
                                       density=jazz.each(*(0.5 + 0.08 * i for i in range(4))),
                                       intensity=jazz.each(*(0.45 + 0.1 * i for i in range(4))),
                                       voicing=jazz.each('rootless', 'shell', 'rootless', 'shell')),
         bass=dict(seed=70, vel=jazz.each(88, 91, 94, 97), skip_grid=jazz.each('swing', 'triplet', 'swing', 'triplet')),
         drums=[(16, dict(style='medium', vel=0.95, seed=81)), (16, dict(style='medium', ride=0.9, vel=1.12, seed=82))])
    bass_fill(b.bass, sax_solo.bar(31), 96)
    b.drums.play(jazz.bombs(32, kit, seed=83, density=0.35, vel=60), sax_solo)
    b.drums.play(jazz.brush_fill('swell', 1, kit=kit, vel=(30, 72)), sax_solo.bar(15))

    # ============================================================== piano solo
    motif = notes('r/8 Bb4 Eb5 G5/4 D6/4.', vel=88, **L)
    line_aa = jazz.solo_line(head.part('A1').prog + head.part('A2').prog, key=s.key, register=('C4', 'C6'),
                             density=0.5, intensity=0.4, seed=5, motif=motif, motif_prob=0.4, vel=76)
    line_a3 = jazz.solo_line(head.part('A3').prog, key=s.key, register=('F4', 'Eb6'), density=0.75, intensity=0.8,
                             seed=9, motif=motif, motif_prob=0.5, vel=86)
    b.piano.play(pianist.crushes(line_aa, 0.45, 3), piano_solo)
    b.piano.play(jazz.block_chords(PIANO_BRIDGE, head.part('B').prog, style='locked', vel=0.7), piano_solo.bar(16))
    b.piano.play(pianist.crushes(line_a3.slice(0, 16).octave_double(-12, vel=0.75) + line_a3.slice(16, 32), 0.3, 4),
                 piano_solo.bar(24))
    play(piano_solo, [line_aa.slice(0, 32), line_aa.slice(32, 64), PIANO_BRIDGE, line_a3],
         comp=dict(style=jazz.each('sparse', 'garland', 'garland', 'swing'), seed=90, register=('G2', 'F4'),
                   density=jazz.each(0.4, 0.55, 0.35, 0.65), intensity=jazz.each(0.35, 0.45, 0.5, 0.6),
                   voicing='shell', B=dict(voicing='rootless')),
         bass=dict(seed=100, vel=jazz.each(84, 88, 92, 95), skip_grid=jazz.each('swing', 'triplet', 'swing', 'triplet')),
         drums=[(16, dict(style='medium', vel=0.85, seed=111)), (8, dict(style='medium', vel=1.0, seed=112)),
                (8, dict(style='medium', vel=1.0, seed=113))])
    bass_fill(b.bass, piano_solo.bar(31), 92)
    b.drums.play(jazz.bombs(16, kit, seed=114, density=0.3, vel=58), piano_solo.bar(16))

    # ============================================================== bass solo
    b.bass.play(BASS_SOLO, bass_solo)
    b.bass.automate('instrument.pitchbend', jazz.slides(bass_solo, BASS_SLIDES, length=0.22))
    b.bass.feature(bass_solo, db=2.5)      # the bassist steps up to the mic: +2.5 dB for the solo, settles back
    play(bass_solo, BASS_SOLO, bass=None,
         comp=dict(style='sparse', density=0.3, intensity=jazz.each(0.22, 0.25), seed=131, voicing='shell',
                   register=('C3', 'A4'), roll=(20, 40)),
         drums=dict(style='two', taps=False, kick=None, fills=False, vel=0.62, seed=141))
    b.drums.play(jazz.brush_fill('swell', 1, kit=kit, vel=(24, 60)), bass_solo.bar(15))

    # ============================================================== head out (from the bridge), calmer
    out_line = (jazz.paraphrase(HEAD_B, seed=5, anticipate=0.3, embellish=0.3, key=s.key).velocity(0.88)
                + jazz.paraphrase(HEAD_A3, seed=6, anticipate=0.25, delay=0.2, key=s.key).velocity(0.84))
    jazz.horn_line(out_line, TEMPO, seed=12, scoop=0.4, fall=0.25, **horn).place(b.sax, head_out)
    play(head_out, out_line, comp=dict(style=jazz.each('swing', 'charleston'), seed=151, density=jazz.each(0.5, 0.45),
                                       intensity=jazz.each(0.4, 0.35)),
         bass=dict(seed=161, vel=jazz.each(82, 76), skip_grid=jazz.each('triplet', 'swing')))
    b.piano.play(FILL_OUT, head_out.bar(8))
    b.drums.play(jazzband.brushes(b, 16, style='medium', vel=0.68, seed=171), head_out)

    # ============================================================== tag + ending
    jazz.horn_line(TAG_SAX, TEMPO, seed=13, scoop=0.4, fall=0.0, **horn).place(b.sax, tag)
    jazz.horn_line(END_SAX, TEMPO * 0.72, seed=14, scoop=1.0, fall=0.0, vib_depth=0.2, **horn).place(b.sax, end)
    play(tag, TAG_SAX, comp=dict(style='ballad', density=0.45, intensity=0.35, seed=181, roll=(25, 45)),
         bass=dict(seed=191, vel=84, skip=0.1),
         drums=[(4, dict(style='medium', vel=0.66, fills=False, seed=201)),
                (2, dict(style='two', vel=0.6, fills=False, seed=202))])
    jazzband.pedal([b.piano, b.comp], tag, end=end.start - 0.1)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(14, 50)), tag.bar(4))
    # the last chord: Ebmaj9#11 rolled up from the left hand to a high sparkle; bass root; a soft cymbal + stir
    s.ending(end, chords=[(b.comp, hold('G2=62 D3=58 F3=56 A3=55', 7.9, length=8), 70),
                          (b.piano, hold('D4=60 Bb4=60 F5=66 A5=58 D6=50', 7.6, length=8), 75, 0.3)],
             bass=(b.bass, 'Eb2', 7, 88),
             drums=(b.drums, jazz.last_stir(kit, 8, crash=30, kick=34, sweeps=(60, 48, 36), last=3)),
             rit=tag.bar(4), to=0.72, hold=2, length=4, room=(-13, -8), room_tracks=[b.sax])
    return s
