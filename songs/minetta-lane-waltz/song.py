"""Minetta Lane Waltz - an original straight-8th jazz waltz for piano trio (D minor, 3/4, 152 BPM, ~3:40).
Build: python -m agentsound build songs/minetta-lane-waltz

New York bar jazz without swing, in three: a grand piano, an upright bass and brushes in a small Village room, a
bittersweet minor waltz with a major bridge, every 8th even (straight Feel, ratio 0.5, small lay-backs). The tune is a
32-bar AABA, one chord per bar (3 beats):

  A1   Dm9      | Bbmaj7#11 | Gm9 | A7b13 | Dm9 | G13     | Em7b5    | A7b9
  A2   Dm9      | Bbmaj7#11 | Gm9 | A7b13 | Gm9 | A7alt   | DmMaj9   | F13          (-> the bridge in Bb)
  B    Bbmaj9   | Eb9#11    | Am7 | D7b9  | Gm9 | C13     | Bb7#11   | A7alt
  A3   Dm9      | Bbmaj7#11 | Gm9 | A7b13 | Gm9 | A7b9    | DmMaj9   | A7alt        (turnaround)
  head-out bridge reharmonized: Gm9 | Eb9#11 | Fmaj7#11 | Ab13 | Ebmaj9 | D9 | Bb7#11 | Eb7#11 (tritone home)

The hook: a pickup (A C) into a three-step rise D-E-F that leaps a third up to a held A (the Bbmaj7's 7th), sighs
back down F-E-D and lands on the C# of the A7 - repeated, then answered brighter (B natural over G13), and in A2 turned
into a climb (C# E G -> Bb) that ends on the bittersweet D over D minor-major. The bridge sings the same shape in
major (A held over Bbmaj9, G over Eb9#11, C over Am7), climbs through D7b9 to the high E over C13 and falls back in
one long line into the hook's pickup.

  intro       8   4 bars piano alone, rubato (the hook's tail over Bbmaj7#11 A7b9 Gm9 A7sus4, tenths in the left
                  hand), then 4 bars in tempo: bass and brushes enter, the hook foreshadowed, the pickup into the head
  head       32   the melody harmonized by the pianist (pianist.arrange), left hand shells with waltz answers on
                  2 / the & of 2; bass in one / two, brushes stir in 3 with taps on 2 and 3
  solo_1     32   the piano solo builds: the motif in fragments (A1), an improvised line (A2), a line in the bridge,
                  the motif in 6ths (A3); bass starts walking in three
  solo_2     32   the climax chorus: a line with runs, octaves, locked hands in the bridge, the hook an octave up in
                  octaves (A3), then it winds down; ride in three
  bass_solo  32   the Meatbass quotes the hook and sings a chorus; the piano whispers shells; brushes only stir
  head_out   32   A1 with a tritone sub, A2 lush, the bridge reharmonized (Gm9 Eb9#11 Fmaj7#11 Ab13 ...), the last A
                  quietly
  tag         8   Gm9 A7alt Dm9 Bbmaj7#11 | Gm9 Eb7#11 Dm9 A7alt, the hook's tail twice, ritardando
  end         3   DmMaj9 rolled from the left hand up into the pedal, fermata, the room rings

Played by the library: song.form (the changes), jazz.chorus (pianist.arrange per part, walking_bass(straight=True),
brushes(straight=True)), song.ending; every per-part detail is an option of those calls.
"""
import functools
import random

from agentsound import *
from agentsound import bands, jazz, pianist

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'Minetta Lane Waltz', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#6b2e3a', '#d8b26a'], 'title': 'minetta lane waltz',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 12}

TEMPO = 152
INTRO_BPM = 112
ARRANGED = {}          # section:part -> pianist.Arrangement (filled by build(); inspect what the pianist played)
MASTER_DRIVE = 6.9
PIANO_TRIM = -3.0

# spice budget (user: too many fast trills / tremolos in perry-street-rain v3): the arranger's ornaments lean on
# turns, mordents, crushes, re-struck voicings and rolls; a trill or tremolo is rare
ORN = {'turn': 1.2, 'mordent': 1.0, 'inverted_mordent': 0.6, 'crush': 1.0, 'restrike': 1.6, 'roll': 1.0,
       'trill': 0.25, 'tremolo': 0.2}

CHANGES = {
    'A1': 'Dm9 Bbmaj7#11 Gm9 A7b13 | Dm9 G13 Em7b5 A7b9',
    'A2': 'Dm9 Bbmaj7#11 Gm9 A7b13 | Gm9 A7alt DmMaj9 F13',
    'B': 'Bbmaj9 Eb9#11 Am7 D7b9 | Gm9 C13 Bb7#11 A7alt',
    'A3': 'Dm9 Bbmaj7#11 Gm9 A7b13 | Gm9 A7b9 DmMaj9 A7alt',
    'A1r': 'Dm9 Bbmaj7#11 Gm9 Eb7#11 | Dm9 G13 Em7b5 A7b9',          # head out: tritone sub in bar 4
    'Br': 'Gm9 Eb9#11 Fmaj7#11 Ab13 | Ebmaj9 D9 Bb7#11 Eb7#11',     # the reharmonized bridge
    'A3e': 'Dm9 Bbmaj7#11 Gm9 A7b13 | Gm9 A7b9 DmMaj9 Eb7#11',      # the last A: into the tag
    'intro_a': 'Bbmaj7#11 A7b9 Gm9 A7sus4', 'intro_b': 'Dm9 Bbmaj7#11 Dm9 A7b13',
    'tag': 'Gm9 A7alt Dm9 Bbmaj7#11 | Gm9 Eb7#11 Dm9 A7alt',
}
FORM = ('intro:intro_a,intro_b head:AABA solo_1:AABA solo_2:AABA bass_solo:AABA head_out:A1r,A2,Br,A3e tag:8 '
        'end:3')

# ------------------------------------------------------------------------------------------------ the tune
# notation (docs/COMPOSE_API.md "Notation"): 3/4 bars, sticky note values; the A sections are named phrases
TUNE = phrases(hook='D5/4. E5/8 F5/4 | A5/2 G5/4 | F5/4. E5/8 D5/4 |', up='C#5/2 E5/8 G5 |',
               sigh='Bb5/4. A5/8 G5/4 | F5/4. Eb5/8 C#5/4 |', climb='Bb5/4. C6/8 D6/4 | C#6/4. Bb5/8 G5 E5 | D5/2. |',
               meter='3/4', length='bar')
HEAD_A1 = TUNE('hook C#5/2 A4/8 C5 | D5/4. E5/8 F5/4 | B5/2 A5/4 | G5/4. F5/8 E5 D5 | E5/4 C#5 A4/8 C5', vel=70)
HEAD_A2 = TUNE('hook up sigh D5/2. | r/4. C5/8 D5 F5', vel=78)
HEAD_B = notes("""
 A5/2 F5/8 D5 | G5/2 F5/8 Db5 | C6/4. B5/8 A5/4 | F#5/4. A5/8 C6 Eb6 |
 D6/2 C6/8 Bb5 | E6/4. D6/8 C6 A5 | Ab5/4. G5/8 F5/4 | G5/8 F5 Eb5 C#5 A4 C5""", vel=86, meter='3/4', length='bar')
HEAD_A3 = TUNE('hook up climb r/2 A4/8 C5', vel=80)
HEAD_A3_END = TUNE('hook up climb r/4 Db5 C5/8 Bb4', vel=70)

# ------------------------------------------------------------------------------------------------ piano solo
SOLO1_A1 = notes("""
 r/4 D5/8 E5 F5/4 | A5/4. r | r/4 F5/8 G5 A5/4 | C#6/4. r |
 r/4 A5/8 C6 D6 C6 | B5/4 A5/8 F5 D5 B4 | D5/4 E5/8 G5 Bb5 D6 | C#6/4. Bb5/8 G5 E5""", vel=80, meter='3/4', length='bar')
SOLO2_B = notes("""
 D6/4. C6/8 A5/4 | G5/4. A5/8 Bb5/4 | C6/4. E6/8 D6/4 | C6/4. A5/8 F#5/4 |
 Bb5/4. D6/8 F6/4 | E6/4. G6/8 A6/4 | Ab6/4. F6/8 D6/4 | C#6 Bb5/8 G5 A5 C6""", vel=100, meter='3/4', length='bar')
SOLO2_A3 = TUNE("hook' up' sigh' D6/4. A5/8 F5 D5 | r/2.", vel=104)        # the hook an octave up
SOLO1_A3 = notes("""
 D5/4. E5/8 F5/4 | A5/2 G5/8 A5 | Bb5/4. A5/8 G5/4 | E5/2 r/4 |
 r/8 F5 G5 A5 Bb5 D6 | C#6/4. Bb5/8 G5 E5 | F5/4. E5/8 D5 A4 | r/2 A4/8 C5""", vel=88, meter='3/4', length='bar')

# ------------------------------------------------------------------------------------------------ bass solo
BASS_SOLO = notes("""
 r/4 D3/8 E3 F3/4 | A3/2 G3/4 | F3/4. E3/8 D3/4 | C#3/2 A2/8 C3 |
 D3/4 F3/8 A3 C4/4 | B3/4. A3/8 F3 D3 | E3/4 G3/8 Bb3 A3 G3 | E3/4 C#3 A2/8 C3 |
 D3/4. E3/8 F3 A3 | D3/4 C3/8 A2 F2/4 | G2 Bb2/8 D3 F3/4 | E3 C#3 E3/8 G3 |
 Bb3/4. A3/8 G3/4 | F3/4. Eb3/8 C#3/4 | D3/2 E3/8 F3 | A3/4 G3/8 F3 Eb3 C3 |
 A3/2 F3/8 D3 | G3/2 F3/8 Db3 | C3/4. E3/8 G3/4 | F#3/4. A3/8 C4 A3 |
 Bb3/4 A3/8 G3 F3 D3 | E3/4 C3/8 D3 E3 G3 | Ab3/4. G3/8 F3 D3 | C#3/4 Eb3/8 F3 G3 A3 |
 A3/4. G3/8 F3 D3 | E3/4 D3/8 C3 A2/4 | Bb2 D3 F3 | E3/4. F3/8 C#3/4 |
 D3 Bb2/8 G2 A2 Bb2 | C#3/4. Bb2/8 G2/4 | D2/2 r/4 | A2/2 r/4""", vel=94, meter='3/4', length='bar')
BASS_SLIDES = [(1, 0.0, -2.0), (5, 0.0, -1.0), (16, 0.0, -2.0), (20, 0.0, -1.0), (24, 0.0, -2.0)]   # bar, beat, from

# ------------------------------------------------------------------------------------------------ intro / tag / end
INTRO_RUB = TUNE('F5/4. E5/8 D5/4 | up Bb5/4. A5/8 G5/4 | E5/2.', vel=70)
INTRO_TEMPO = notes('r/4 D5/8 E5 F5/4 | A5/2. | r/4 D5/8 E5 F5/4 | E5 C#5 A4/8 C5', vel=66, meter='3/4', length='bar')
TAG_RH = TUNE('sigh D5/2. | r/4 D5/8 E5 F5/4 | sigh D5/2. | r/4. C#5/8 F5 G5', vel=66)
END_LH = hold('E3=46 A3=50', 8.9, length=9)                  # the bass has the low D
END_RH = hold('F4=64 A4=66 C#5=72 E5=78 A5=96', 8.6, length=9)

# the pianist per part (pianist.arrange options), the straight-8th bass and brushes in three
SOLO_FILLS = {'run': 2.0, 'chromatic': 1.5, 'pentatonic': 1.5, 'fourths': 1.0}
LINES = {'single': 2.0, 'guide': 2.0, 'thirds': 1.5, 'sixths': 1.0}


def build() -> Song:
    s = Song('Minetta Lane Waltz', tempo=TEMPO, key='D minor', seed=12, tail=6, meter=(3, 4))
    intro, head, solo1, solo2, bsolo, hout, tag, end = s.form(FORM, parts=CHANGES)
    feel = jazz.Feel(TEMPO, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0}, beats_per_bar=3)
    b = bands.make('jazz_trio', s, feel=feel, master_gain=MASTER_DRIVE)
    b.piano.gain_db += PIANO_TRIM
    b.drums.gain_db -= 1.5        # brushes 14-16 dB (RMS) under the piano in every section
    b.bass.gain_db -= 1.0         # the piano leads: the bass sits a little under it
    kit = b.info['kit']
    # air, not bite: the preset's jazz_grand keeps the loud layers warm (HUMAN_FEEDBACK: "es klingt hart")
    b.piano.add_fx(fx.eq({'high.freq': 9000, 'high.gain': 1.5}))
    s.master.add_fx(fx.eq({'high.freq': 8000, 'high.gain': 2.0}), first=True)   # air (the room IR is dark)
    rng = random.Random(9)
    mem = pianist.Memory()        # one pianist for the whole song: the ornament budget counts song-wide
    mem.save(solo2.bar(29))       # the fast figure is saved for the climax (the hook an octave up)
    # the pianist: right hand harmonized and decorated, the left hand on the comping track (in 3/4 it answers on
    # 2 / the & of 2 / 3 where the right hand leaves room: lh_answers = how often); the pedal follows the harmony
    play = functools.partial(jazz.chorus, b, memory=mem, record=ARRANGED, defaults=dict(
        piano=dict(lh='guide', lh_vel=54, lh_answers=0.5, ornaments=ORN),
        bass=dict(straight=True), drums=dict(straight=True, style='medium')))

    # ============================================================== intro
    # 4 bars rubato, piano alone (tenths in the left hand, ballad voicings), then in tempo: bass + brushes enter,
    # the hook foreshadowed, the pickup (A C) into the head
    b.drums.play(jazz.brush_fill('swell', 3, kit=kit, vel=(14, 44)), intro.bar(3))
    play(intro, [INTRO_RUB, INTRO_TEMPO], piano=dict(
        seed=101, density=0.5,
        intro_a=dict(touch=(50, 84), style='ballad', lh='tenths', lh_answers=0.0, bpm=INTRO_BPM, roll=(30, 55),
                     ornaments={'roll': 2.0, 'restrike': 1.0, 'turn': 1.0}, fills={'arpeggio': 3.0, 'answer': 1.0}),
        intro_b=dict(touch=(46, 80), style='sparse', lh_vel=50, lh_answers=0.8, section_end=False)),
        bass=dict(intro_a=None, intro_b=dict(seed=11, vel=78, feel='one')),
        drums=dict(intro_a=None, intro_b=dict(seed=21, vel=0.5, fills=False)))

    # ============================================================== head
    play(head, [HEAD_A1, HEAD_A2, HEAD_B, jazz.paraphrase(HEAD_A3, seed=3, anticipate=0.0, delay=0.0, embellish=0.12,
                                                         key=s.key)],
         piano=dict(style='straight', seed=201, lead_in=True, lh='rootless',
                    A1=dict(touch=(42, 82), density=0.45, lead_in=False, lh='guide', lh_vel=52, inner=0.76,
                            lh_answers=0.55),
                    A2=dict(touch=(48, 94), density=0.6, lh='guide', lh_vel=55, inner=0.76, lh_answers=0.6),
                    B=dict(touch=(54, 104), density=0.8, lh_vel=58, lh_answers=0.65,
                           devices={'drop2': 2.5, 'sixths': 1.5, 'quartal': 1.5, 'close': 1.0, 'guide': 1.0},
                           fills={'run': 2.0, 'fourths': 1.5, 'arpeggio': 2.0, 'answer': 1.0},
                           ornaments={'trill': 1.5, 'turn': 1.0, 'restrike': 1.0, 'crush': 1.0}),
                    A3=dict(touch=(50, 96), style='lush', density=0.6, lh_vel=54, lh_answers=0.55)),
         bass=dict(seed=31, feel=jazz.each('one', 'two', 'two', 'two'), vel=jazz.each(81, 85, 89, 89)),
         drums=[(8, dict(seed=41, vel=0.5)), (8, dict(seed=42, vel=0.62, ghosts=0.35, kick='even')),
                (16, dict(seed=43, vel=0.72, ghosts=0.5, kick='even'))])

    # ============================================================== solo chorus 1: it builds
    motif = HEAD_A1.slice(0, 6)
    line_a2 = jazz.solo_line(s['head'].part('A2').prog, key=s.key, register=('A4', 'D6'), density=0.62,
                             intensity=0.55, seed=14, motif=motif, motif_prob=0.5, phrase_bars=(2, 3), triplets=0.1,
                             length=24)
    line_b1 = jazz.solo_line(head.part('B').prog, key=s.key, register=('C5', 'Eb6'), density=0.7, intensity=0.65,
                             seed=15, motif=HEAD_B.slice(0, 6), motif_prob=0.4, phrase_bars=(2, 3), triplets=0.1,
                             length=24)
    play(solo1, [SOLO1_A1, line_a2, line_b1, SOLO1_A3], lh_pedal=False, piano=dict(
        style='straight', seed=301, lead_in=True, pedal=False, lh='rootless',
        touch=jazz.each((54, 100), (58, 104), (62, 106), (62, 106)),
        A1=dict(style='sparse', density=0.55, lh='guide', lh_vel=56, lh_answers=0.6,
                fills={'answer': 2.0, 'run': 1.0, 'pentatonic': 1.0}),
        A2=dict(density=0.55, lh='guide', lh_vel=58, lh_answers=0.6, devices={'single': 3.0, 'guide': 2.0, 'thirds': 1.0},
                fills={'run': 2.0, 'chromatic': 1.5, 'fourths': 1.5, 'pentatonic': 1.0}),
        B=dict(density=0.6, lh_vel=60, lh_answers=0.65, devices={'single': 2.0, 'guide': 2.0, 'sixths': 1.5, 'thirds': 1.5},
               fills={'run': 1.5, 'fourths': 1.5, 'chromatic': 1.0, 'arpeggio': 1.0}),
        A3=dict(density=0.7, pedal=True, lh_vel=60, lh_answers=0.65, devices={'sixths': 3.0, 'thirds': 1.5, 'drop2': 1.0})),
        bass=dict(seed=61, feel=jazz.each('two', 'walk', 'walk', 'walk'), vel=jazz.each(89, 91, 93, 93)),
        drums=[(16, dict(seed=71, vel=0.72, ghosts=0.4, kick='even')), (16, dict(seed=72, vel=0.8, ghosts=0.5, kick='even'))])

    # ============================================================== solo chorus 2: the climax, then it winds down
    line_a1 = jazz.solo_line(head.part('A1').prog, key=s.key, register=('C5', 'F6'), density=0.75, intensity=0.75,
                             seed=16, motif=motif, motif_prob=0.4, phrase_bars=(2, 4), triplets=0.12, length=24)
    line_a2b = jazz.solo_line(head.part('A2').prog, key=s.key, register=('D5', 'G6'), density=0.8, intensity=0.8,
                              seed=17, motif=motif, motif_prob=0.5, phrase_bars=(2, 4), triplets=0.1, length=24)
    play(solo2, [line_a1, line_a2b, SOLO2_B, SOLO2_A3], lh_pedal=False, piano=dict(
        seed=311, lead_in=True, pedal=False, lh='rootless', touch=jazz.each((64, 108), (66, 110), (74, 114), (72, 116)),
        A1=dict(style='straight', density=0.65, lh_vel=60, lh_answers=0.7, devices=LINES, fills=SOLO_FILLS),
        A2=dict(style='bar', density=0.7, lh_vel=62, lh_answers=0.7, quick=0.2,
                ornaments={'crush': 1.5, 'blues_crush': 1.5, 'slip': 1.0, 'mordent': 1.0, 'turn': 0.8, 'repeated': 0.6,
                           'trill': 0.2},
                fills={'chromatic': 2.0, 'run': 1.5, 'octave_run': 1.0, 'stabs': 1.0, 'hands': 0.8}),
        B=dict(style='lush', density=0.8, pedal=True, lh_vel=64, lh_answers=0.6, voices=3,
               devices={'locked': 3.0, 'drop2': 2.0, 'octave': 1.0},
               ornaments={'restrike': 1.5, 'roll': 0.8, 'turn': 0.8, 'tremolo': 1.2},
               fills={'hands': 2.0, 'arpeggio': 1.0, 'fourths': 1.0}),
        A3=dict(style='bar', climax=True, density=0.85, lh_vel=64, lh_answers=0.6, quick=0.15, section_end=False,
                ornaments={'blues_crush': 1.5, 'crush': 1.0, 'slip': 1.0, 'repeated': 1.0, 'shake': 1.0, 'trill': 0.3},
                fills={'octave_run': 1.5, 'chromatic': 1.0, 'hands': 1.0})),
        bass=dict(seed=81, feel='walk', vel=jazz.each(93, 95, 96, 96)),
        drums=[(16, dict(seed=91, vel=0.88, ghosts=0.4, kick='even')), (16, dict(seed=92, vel=0.95, kick='even', ride=0.9))])
    b.drums.play(Clip([(0, 2, kit['crash'], 40)], length=3), solo2.bar(16))

    # ============================================================== bass solo: the hook in the bass, piano whispers
    b.bass.play(jazz.touch(BASS_SOLO, 68, 98), bsolo)     # the solo sung like a melody
    b.bass.automate('instrument.pitchbend', jazz.slides(bsolo, BASS_SLIDES))
    b.bass.feature(bsolo, db=2.0)                          # +2 dB for the solo
    play(bsolo, BASS_SOLO, bass=None, comp=dict(style='waltz', voicing='shell', density=0.3, intensity=0.22, seed=131,
                                                register=('C3', 'A4'), vel=jazz.each(50, 52, 54, 56), roll=(20, 40),
                                                roll_seed=rng),
         drums=dict(seed=141, vel=0.55, fills=False))
    b.piano.play(pianist.sweep('A7alt', 1.4, TEMPO, low='C#4', high='C5', direction='up', ring=False,
                               vel=(40, 70), seed=13), bsolo.beat(-1.5))
    b.drums.play(jazz.brush_fill('swell', 3, kit=kit, vel=(22, 54)), bsolo.beat(-3))

    # ============================================================== head out: A1 re-harmonized, A2, the new bridge,
    # the last A quiet
    play(hout, [jazz.paraphrase(HEAD_A1, seed=5, anticipate=0.2, delay=0.0, embellish=0.1, key=s.key), HEAD_A2, HEAD_B,
                HEAD_A3_END],
         piano=dict(seed=401, lead_in=True, lh='rootless', lh_answers=0.6,
                    A1r=dict(touch=(50, 92), style='straight', density=0.55, lh_vel=56),
                    A2=dict(touch=(54, 98), style='lush', density=0.65, seed=406, lh_vel=58,
                            ornaments=dict(ORN, trill=3.0)),                      # the one trill: the held D
                    Br=dict(touch=(62, 108), style='lush', density=0.8, lh_vel=60,
                            devices={'drop2': 3.0, 'close': 1.5, 'ust': 1.0, 'locked': 1.0},
                            fills={'arpeggio': 2.0, 'fourths': 1.0, 'run': 1.0}),
                    A3e=dict(touch=(42, 80), style='sparse', density=0.45, lh='guide', lh_vel=50, lh_answers=0.5)),
         bass=dict(seed=161, feel=jazz.each('two', 'walk', 'walk', 'two'), vel=jazz.each(89, 91, 93, 81)),
         drums=[(16, dict(seed=171, vel=0.75, ghosts=0.4, kick='even')),
                (8, dict(seed=172, vel=0.82, ghosts=0.5, kick='even')), (8, dict(seed=173, vel=0.58, ghosts=0.15))])

    # ============================================================== tag + ending
    play(tag, TAG_RH, pedal_end=end.start - 0.1, piano=dict(
        touch=(46, 84), style='ballad', density=0.5, seed=501, lead_in=True, lh='rootless', lh_vel=48,
        bpm=TEMPO * 0.85, lh_answers=0.45, section_end=False),
        bass=dict(seed=191, vel=80, feel='one'), drums=[(7, dict(seed=201, vel=0.5, fills=False))])
    b.drums.play(jazz.brush_fill('swell', 3, kit=kit, vel=(12, 42)), tag.beat(-3))

    # ============================================================== time
    s.set_tempo(intro, INTRO_BPM)                                  # the rubato bars: slower and free
    s.rubato((intro.start, intro.bar(4)), depth=0.07, phrase='lean')
    s.set_tempo(intro.bar(4), TEMPO)
    # DmMaj9 rolled from the left hand up into the pedal, the bass's low D, a soft cymbal and stirs; ritardando,
    # fermata, the room rings
    s.ending(end, chords=[(b.comp, END_LH, 70), (b.piano, END_RH, 85, 0.25)], roll_bpm=TEMPO * 0.7,
             bass=(b.bass, 'D2', 8, 82),
             drums=(b.drums, jazz.last_stir(kit, 9, crash=26, kick=28, sweeps=(54, 42, 30), every=3)),
             rit=tag.bar(4), to=0.72, hold=2, length=3, room=(-13, -8))
    return s
