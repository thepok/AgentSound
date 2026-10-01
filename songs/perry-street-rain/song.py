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
import functools
import random

from agentsound import *
from agentsound import bands, jazz, pianist
from agentsound.bandlib import jazz as jazzband

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
CHANGES = {
    'A1': 'Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Dm7b5:0.5 G7b9:0.5 Cm9:0.5 F7b9:0.5 Bbm7:0.5 Eb7sus4:0.5',
    'A2': 'Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Cm7:0.5 F7b9:0.5 Bbm9:0.5 Eb13:0.5 Abmaj9:0.5 Ab13:0.5',
    'B': 'Dbmaj9 Gb13#11 Cm9 F7alt | Bbm9 Dbm6 Emaj7#11 Eb7sus4:0.5 Eb7b9:0.5',
    'A3': 'Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Cm7:0.5 F7b9:0.5 Bbm9:0.5 Eb13:0.5 Abmaj9:0.5 C7alt:0.5',
    'A3o': 'Fm9 Dbmaj7#11 Bbm9 Eb7sus4:0.5 Eb7b9:0.5 | Abmaj9 Cm7:0.5 F7b9:0.5 Bbm9:0.5 Eb13:0.5 Abmaj9:0.5 F7alt:0.5',
    'intro': 'Dbmaj9 Cm9 Bbm9 Eb7sus4:0.5 Eb7b9:0.5',
    'tag': 'Bbm9:0.5 Eb13:0.5 Cm7:0.5 F7alt:0.5 Bbm9:0.5 Eb7sus4:0.5 Dbm6:0.5 Gb13:0.5',
}
FORM = 'intro:4 head:AABA piano_solo:AABA bass_solo:AA head_out:B,A3o tag:4 end:2'


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
    intro, head, solo, bsolo, hout, tag, end = s.form(FORM, parts=CHANGES)
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
    rng = random.Random(9)
    # one pianist for the whole song (jazz.chorus -> pianist.arrange per part: the right hand harmonized, decorated
    # and filled, the left hand on the comping track, the pedal with the harmony, lifted for runs): the ornament
    # budget (fast two-key alternations about one per 16 bars) counts song-wide in the Memory
    mem = pianist.Memory()
    play = functools.partial(jazz.chorus, b, memory=mem, record=ARRANGED, defaults=dict(
        piano=dict(lh='guide', lh_vel=56), bass=dict(straight=True), drums=dict(straight=True, style='ballad')))

    # ============================================================== intro: piano alone, rubato, pedalled
    # pianist moves on top of the rolled grips: a trill on the Cm9's 9th (D-Eb, the pedal lifted for it), a turn on
    # the high C, an arpeggio sweep down the Eb7b9 into the head
    b.comp.play(INTRO_LH.strum(ms=60, bpm=TEMPO), intro)
    b.piano.play(INTRO_RH.roll((30, 45), seed=rng, bpm=TEMPO), intro)
    b.piano.play(pianist.trill('D5', 2.5, TEMPO, chord='Cm9', rate=13.5, vel=66, seed=11), intro.beat(4))
    mem.played(intro.beat(4), 'trill')              # the ornament budget counts it (pianist.Memory)
    mem.save(solo.bar(31))                          # ... and saves its fast figure for the climax (solo A3's end)
    b.piano.play(pianist.turn('C6', 1.5, TEMPO, chord='Bbm9', vel=88, ms=80), intro.beat(10.5))
    b.piano.play(pianist.sweep('Eb7b9', 1.35, TEMPO, low='C5', high='Db6', direction='down', ring=False,
                               vel=(62, 44), seed=12), intro.beat(14.5))
    b.piano.automate('instrument.pedal', pianist.pedal(intro.prog, intro, dry=[(4.0, 5.9)]))
    jazzband.pedal([b.comp], intro)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(14, 46)), intro.beat(-2))

    # ============================================================== head: the melody, harmonized by the pianist
    # a pianist's touch (jazz.touch) on the tune first, then pianist.arrange: phrase by phrase a voicing device
    # under the melody (guide tones, 3rds / 6ths, drop 2, quartal ...), ornaments on the long notes, fills in the
    # gaps, the left hand on the comping track (shells in the A sections, rootless voicings from the bridge) - no
    # separate comping part any more: one pianist, two hands. The head builds A1 < A2 < B, the last A settles.
    play(head, [HEAD_A1, HEAD_A2, HEAD_B, jazz.paraphrase(HEAD_A3, seed=3, anticipate=0.0, delay=0.0, embellish=0.15,
                                                         key=s.key)],
         piano=dict(style='straight', seed=201, lead_in=True, touch=jazz.each((46, 88), (48, 94), (54, 104), (50, 98)),
                    A1=dict(density=0.45, lead_in=False, lh_vel=52, inner=0.76),
                    A2=dict(density=0.6, lh_vel=55, inner=0.76,
                            ornaments={'trill': 2.0, 'restrike': 1.5, 'turn': 1.0, 'tremolo': 1.0, 'crush': 0.8}),
                    B=dict(density=0.85, lh='rootless', lh_vel=58,
                           devices={'drop2': 2.5, 'octave': 1.5, 'sixths': 1.5, 'quartal': 1.5, 'guide': 1.0},
                           fills={'run': 2.0, 'fourths': 2.0, 'arpeggio': 2.0, 'hands': 1.0, 'chromatic': 1.0},
                           ornaments={'tremolo': 2.0, 'trill': 1.0, 'restrike': 1.0, 'turn': 1.0}),
                    A3=dict(style='lush', density=0.6, lh='rootless', lh_vel=54)),
         bass=dict(seed=31, feel=jazz.each('two', 'two', 'push', 'push'), vel=jazz.each(81, 85, 92, 92),
                   pickups=jazz.each(0.35, 0.6, 0.5, 0.5)),
         drums=[(8, dict(seed=41, vel=0.52)), (8, dict(seed=42, vel=0.7, ghosts=0.4, kick='even')),
                (16, dict(seed=43, vel=0.8, ghosts=0.55, kick='even'))])

    # ============================================================== piano solo: lines, two hands, the climax
    # A1 the motif with guide tones and answers over left-hand shells; A2 an improvised line (jazz.solo_line with
    # the hook as motif) with runs / 4ths in its gaps; B two-handed chords (locked hands, drop 2) with tremolos, a
    # shake and alternating-hands breaks; A3 the climax: the hook an octave up in octaves, blues crushes, repeated
    # notes, octave runs. The right hand plays the lines dry (no pedal) except in the chordal bridge.
    line_a2 = jazz.solo_line(head.part('A2').prog, key=s.key, register=('Bb4', 'Db6'), density=0.7, intensity=0.6,
                             seed=14, motif=HEAD_A1.slice(0, 4), motif_prob=0.5, phrase_bars=(1, 2), triplets=0.15)
    play(solo, [SOLO_A1, line_a2, SOLO_B, SOLO_A3], lh_pedal=False, piano=dict(
        seed=301, lead_in=True, pedal=False, touch=jazz.each((56, 104), (60, 108), (72, 114), (76, 116)),
        A1=dict(style='sparse', density=0.55, fills={'answer': 2.0, 'run': 1.5, 'pentatonic': 1.0},
                ornaments={'mordent': 1.0, 'crush': 1.0, 'turn': 1.0, 'trill': 1.0}),
        A2=dict(style='straight', density=0.6, lh_vel=58, devices={'single': 3.0, 'guide': 2.0, 'thirds': 1.0},
                fills={'run': 2.0, 'chromatic': 2.0, 'fourths': 2.0, 'pentatonic': 1.5},
                ornaments={'trill': 1.5, 'mordent': 1.0, 'turn': 1.0, 'crush': 1.0}),
        B=dict(style='lush', density=0.85, pedal=True, embellish=0.3, lh='rootless', lh_vel=62, voices=3,
               devices={'locked': 3.0, 'drop2': 2.0, 'octave': 1.0},
               ornaments={'tremolo': 1.5, 'restrike': 1.0, 'roll': 0.6, 'turn': 0.6},
               fills={'hands': 3.0, 'arpeggio': 1.0, 'tremolo': 1.0}),
        A3=dict(style='bar', climax=True, density=0.9, seed=332, lh='rootless', lh_vel=66, quick=0.15,
                ornaments={'blues_crush': 2.0, 'slip': 0.5, 'crush': 0.5, 'repeated': 1.5, 'trill': 1.0,
                           'tremolo': 1.0, 'shake': 1.5},
                fills={'hands': 3.0, 'octave_run': 1.0, 'chromatic': 1.0, 'repeated': 0.5})),
        bass=dict(seed=61, feel=jazz.each('push', 'push', 'push', 'drive'), vel=jazz.each(86, 90, 92, 96)),
        drums=dict(seed=71, kick='even', vel=jazz.each(0.8, 0.85, 0.9, 1.0), ghosts=jazz.each(0.5, 0.3, 0, 0),
                   hat8=jazz.each(0, 0.8, 0.9, 0), ride=jazz.each(0, 0, 0, 0.95)))
    b.drums.play(Clip([(0, 2, kit['crash'], 40)], length=4), solo.bar(24))

    # ============================================================== bass solo: the hook in the bass, piano whispers
    b.bass.play(jazz.touch(BASS_SOLO, 68, 96), bsolo)        # the solo sung like a melody: phrase arcs, peaks
    b.bass.automate('instrument.pitchbend', jazz.slides(bsolo, BASS_SLIDES))
    b.bass.feature(bsolo, db=1.0)                            # the bassist steps up for the solo: +1 dB, then back
    play(bsolo, BASS_SOLO, bass=None, drums=dict(seed=141, vel=0.55, fills=False),     # the piano whispers under it
         comp=dict(style='sparse', voicing='shell', density=0.3, intensity=jazz.each(0.22, 0.25), seed=131,
                   register=('C3', 'A4'), vel=jazz.each(44, 46), roll=(20, 40), roll_seed=rng))
    # the piano announces the head out: a glissando-like Ab13 scale sweep up into its first note (F5)
    b.piano.play(pianist.gliss('F5', 1.0, TEMPO, chord='Ab13', span=17, vel=(40, 84), seed=13), bsolo.beat(-1))
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(22, 56)), bsolo.beat(-2))

    # ============================================================== head out: the bridge lush, the last A quiet
    play(hout, [HEAD_B, jazz.paraphrase(HEAD_A3_OUT, seed=8, anticipate=0.0, embellish=0.1, key=s.key)], piano=dict(
        seed=401, lead_in=True,
        B=dict(touch=(66, 108), style='lush', density=0.85, lh='rootless', lh_vel=60,
               devices={'drop2': 3.0, 'locked': 1.5, 'close': 1.5, 'ust': 1.0},
               fills={'arpeggio': 2.0, 'fourths': 1.0, 'run': 1.0}),
        A3o=dict(touch=(48, 88), style='sparse', density=0.45, lh_vel=50,
                 ornaments={'trill': 1.5, 'turn': 1.0, 'mordent': 1.0, 'restrike': 1.0},
                 fast_every=16)),               # sparse plays no fast figure - except a trill on the last note
        bass=dict(seed=161, feel=jazz.each('push', 'two'), vel=jazz.each(93, 81), pickups=jazz.each(0.5, 0.4)),
        drums=[(8, dict(seed=171, vel=0.85, ghosts=0.5, kick='even')), (8, dict(seed=172, vel=0.6, ghosts=0.2))])

    # ============================================================== tag + ending
    # the tag as a ballad (rolled voicings, a trill / tremolo on its long notes); the moves are timed for the
    # ritardando's slower tempo
    play(tag, TAG_RH, pedal_end=end.start - 0.1, piano=dict(
        touch=(46, 86), style='ballad', density=0.55, seed=501, lead_in=True, lh='rootless', lh_vel=48,
        bpm=TEMPO * 0.85, section_end=False),
        bass=dict(seed=191, vel=82, feel='two', pickups=0.3), drums=[(3, dict(seed=201, vel=0.5, fills=False))])
    b.drums.play(jazz.brush_fill('swell', 4, kit=kit, vel=(12, 44)), tag.beat(-4))

    # ============================================================== time
    s.rubato(intro, depth=0.06, phrase='lean')
    # Abmaj9#11 rolled from the left hand up into the pedal, the bass's Ab1, a soft cymbal and dying stirs;
    # ritardando, fermata, the room rings
    s.ending(end, chords=[(b.comp, END_LH, 70), (b.piano, END_RH, 80, 0.25)], bass=(b.bass, 'Ab1', 7, 92),
             drums=(b.drums, jazz.last_stir(kit, 8, last=3)), rit=tag.bar(2), to=0.72, hold=2, length=4,
             room=(-13, -8))
    return s
