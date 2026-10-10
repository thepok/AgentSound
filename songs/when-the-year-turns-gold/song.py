"""When the Year Turns Gold - an original songbook ballad (torch song) for a female voice, piano, upright bass,
brushes and strings (62 BPM, Db major, verse in Bb minor, bridge in A major, no swing, ~4:50).
Build: python -m agentsound build songs/when-the-year-turns-gold

The user's wish, after the smooth-jazz "Nowhere to Be": "ich dachte eher an etwas wie Autumn in New York!" - a classic
vocal jazz ballad of the Great American Songbook (the many famous recordings of that kind of ballad: a rubato verse
with voice and piano, a slow AABA refrain, songbook harmony, a string orchestration swelling under the voice, a
ritardando into a held last note over a colourful chord). Original: no melody, chords, form or words of any standard -
only the idiom. Brief: BRIEF.md, form and changes: ARRANGEMENT.md, words: LYRICS.md.

  intro   2   rubato: the piano alone, a hint of the hook, a fermata on the dominant of Bb minor
  verse   8   rubato (out of time): voice + piano - "Summer took the early train"
  A1      8   a tempo: the hook "When the year turns gold"; bass (two) and brush stirs enter
  A2      8   the strings enter pp under her: a pad, the violins' halo answering in her gaps
  B       8   the bridge in A major (bVI), the strings swell, a cello counter-line; back through Fm9 - Bb7 - Ebm9 - Ab7
  A3      8   the hook again, home on Dbmaj9
  Ai      8   instrumental half-chorus: the piano sings the A, the strings answer
  B2      8   "take it from the bridge": the climax - the full strings, "stay" lifted to Db5
  A4      8   the last A turned ("and the gold turns gray"), a deceptive Fm7 - E°7
  tag     4   "when the year turns gold" twice, ritardando
  end     2   the held "gold" (C5, the maj7) over Dbmaj9(#11), fermata
"""
import random

from agentsound import *
from agentsound import bands, jazz, mastering, pianist, singer
from agentsound.bandlib import jazz as jazzband
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'When the Year Turns Gold', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#2c2433', '#d9a441'], 'title': 'when the year turns gold',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 62}

# the mix engineer's moves (MIX.md): the voice 3 dB down INTO the band (1.5 + the user's "15% leiser" after delivery) (the user: "die Stimme im Vergleich zum Rest
# zu laut"), the piano's chords up (they read 13-16 dB under her: a songbook ballad is voice AND piano), the brushes
# a little up, the strings held under her at the climax (B2 read -1.1 dB) and lifted on the last chord
_STR = ('violins1', 'violins2', 'violas', 'cellos')
MIX = {
    'trim': {'drums': 1.5},       # the voice -3, comp +4, piano -2.5 and the limiter drive: lead='vocal'
    # A&R round 1: the last "gold" 2.5 dB back with the strings' diminuendo, the half chorus's tune up where she hands
    # over (it dropped ~5 dB), the piano's answers in A3 a little under her
    'ride': {'comp': {'intro': 2.0, 'verse': 1.0}, 'vocal': {'end': -2.5}, 'piano': {'A3': -1.5, 'Ai': 2.0},
             **{r: {'B': -1.0, 'B2': -3.5, 'end': 3.0} for r in ('violas', 'cellos')},
             **{r: {'B': -1.0, 'Ai': 1.5, 'B2': -3.5, 'end': 3.0} for r in ('violins1', 'violins2')}},
    'eq': {'violins1': [{'freq': 3300.0, 'gain': -2.5, 'q': 1.0}]},
}

TEMPO = 62
VERSE_BPM = 56          # the verse is out of time and slower
SOLO = {}

# ------------------------------------------------------------------------------------------------ changes
# A: I - VI7 - ii - V - iii - biii°7 - ii - (I7 | VI7) + a turnaround per A; the bridge in A major (bVI) and back by
# a chain of secondary dominants (Gm7 C7 -> Fm9 -> Bb7 -> Ebm9 -> Ab7)
_A = 'Dbmaj9 | Dbmaj9:0.5 Bb7b9:0.5 | Ebm9 | Ab13:0.5 Ab7b9:0.5 | Fm7:0.5 E°7:0.5 | '
CHANGES = {
    'I': 'Gbmaj9 | F7sus4:0.5 F7b9:0.5',
    'V': 'Bbm9 | Gbmaj9 | Ebm9 | F7sus4:0.5 F7b9:0.5 | Bbm9 | Gm7b5:0.5 C7b9:0.5 | Fm9 | Ebm9:0.5 Ab7sus4:0.5',
    'A1': _A + 'Ebm9:0.5 Db9:0.5 | Gbmaj9 | Gbm6:0.5 Cb9:0.5',                        # the backdoor home
    'A2': _A + 'Ebm9:0.5 Bb7b9:0.5 | Ebm9:0.5 Ab13:0.5 | Dbmaj9:0.5 Bm7:0.25 E7b9:0.25',   # into the bridge
    'A3': _A + 'Ebm9:0.5 Bb7b9:0.5 | Ebm9:0.5 Ab13:0.5 | Dbmaj9:0.5 Ebm9:0.25 Ab13:0.25',  # home
    'B': 'Amaj9 | F#m9:0.5 B13:0.5 | Bm9:0.5 E13:0.5 | Amaj9:0.5 Gm7:0.25 C7b9:0.25 | Fm9 | Bb13:0.5 Bb7b9:0.5 | '
         'Ebm9 | Ab7sus4:0.5 Ab7b9:0.5',
    'B2': 'Amaj9 | F#m9:0.5 B13:0.5 | Bm9:0.5 E13:0.5 | Amaj9:0.5 Gm7:0.25 C7b9:0.25 | Fm9 | Bb7#9:0.5 Bb7b9:0.5 | '
          'Ebm9 | Ab7sus4:0.5 Ab7b9:0.5',
    'A4': _A + 'Ebm9:0.5 Bb7b9:0.5 | Ebm9:0.5 Ab13:0.5 | Fm7:0.5 E°7:0.5',             # deceptive: into the tag
    'T': 'Ebm9:0.5 Ab13:0.5 | Fm7:0.5 E°7:0.5 | Ebm9 | Ab7sus4:0.5 Ab7b9:0.5',
    'E': 'Dbmaj9#11:2',
}
FORM = 'intro:I verse:V A1:A1 A2:A2 B:B A3:A3 Ai:A2 B2:B2 A4:A4 tag:T end:E'

# ------------------------------------------------------------------------------------------------ the voice
# Db4-C5 (the last A's Db5 and the bridge's C#5 / Db5 the only tops), stepwise, 5-7 syllables per 2-bar line, a rest
# after every line; every A shares one tune (AABA), the endings and the last A differ.
_HOOK = 'r/4 F4/8 Gb4/8 Ab4/4 Bb4/4 | C5/2 r/2 | '
VOX = phrases(
    verse="""F4/4. Eb4/8 F4/4 Gb4/4 | Ab4/4. Gb4/8 F4/2 | r/4 Gb4/8 Ab4/8 Bb4/4. Ab4/8 | Gb4/8 F4/8 Eb4/2. |
             r/4 F4/8 F4/8 Bb4/2 | G4/4 Ab4/8 Ab4/8 Bb4/2 | r/4 F4/8 G4/8 Ab4/4. G4/8 | F4/4. Eb4/8 Db4/2""",
    a1=_HOOK + """r/4 Bb4/8 Ab4/8 Gb4/4. F4/8 | Eb4/2 r/4 Ab4/8 Ab4/8 | C5/4. Bb4/8 G4/4. Ab4/8 |
                  Bb4/2 r/4 Eb4/8 F4/8 | Ab4/4. Gb4/8 F4/2 | r/1""",
    a2=_HOOK + """r/4 Bb4/8 Ab4/8 Gb4/4. F4/8 | Eb4/2 r/4 Ab4/8 Ab4/8 | C5/4. Bb4/8 G4/4. Ab4/8 |
                  Bb4/2 r/4 F4/8 Gb4/8 | Ab4/4 Gb4/4 F4/2~ | F4/2 r/2""",
    # A3: the second line lifted (Bb - Ab - Bb, down to Gb), the ending left open on Ab before the half chorus
    a3=_HOOK + """r/4 Bb4/8 Ab4/8 Bb4/4. Ab4/8 | Gb4/2 r/4 Ab4/8 Ab4/8 | C5/4. Bb4/8 G4/4. Ab4/8 |
                  Bb4/2 r/4 F4/8 Gb4/8 | Ab4/4 Bb4/4 Ab4/2~ | Ab4/2 r/2""",
    # the last A climbs to its Db5 on "gold turns gray"
    a4=_HOOK + """r/4 Bb4/8 C5/8 Db5/4 C5/4 | Bb4/2 r/4 Ab4/8 Ab4/8 | C5/4. Bb4/8 G4/4. Ab4/8 |
                  Bb4/2 r/4 F4/8 Gb4/8 | Ab4/4 Gb4/4 F4/2~ | F4/2 r/2""",
    # the bridge: the leaves fall down the A-major scale, "you" on C#5, the direct line climbs back to Db major
    b="""C#5/4. B4/8 A4/4. G#4/8 | F#4/4 E4/4 r/2 | G#4/4. A4/8 B4/4. B4/8 | C#5/2 r/4. C5/8 |
         Ab4/4 Bb4/4 C5/4 Bb4/8 Ab4/8 | Bb4/2 r/4 F4/8 Gb4/8 | Ab4/4 Gb4/4 F4/2~ | F4/2 r/2""",
    b2="""C#5/4. B4/8 A4/4. G#4/8 | F#4/4 E4/4 r/2 | G#4/4. A4/8 B4/4. B4/8 | C#5/2 r/4. C5/8 |
          Ab4/4 Bb4/4 C5/4 Bb4/8 C5/8 | Db5/2 r/4 F4/8 Gb4/8 | Ab4/4 Gb4/4 F4/2~ | F4/2 r/2""",
    # tag + end: the hook twice, the last "gold" held three beats into the final chord's fermata (~6.5 s; the chord outlasts her)
    tag=_HOOK + """r/2 r/4 F4/8 Gb4/8 | Ab4/4 Bb4/2. | C5/2. r/4 | r/1""",
    length='bar')

LYRICS = {
    'verse': "Sum-mer took the ear-ly train, left the san-dals in the hall, and{ae n} the streets put on their coats "
             "like they nev-er cared at all.",
    'A1': "When the year turns gold, that was what you *said*, by the fer-ry gate at *five*, with the ma-ples red.",
    'A2': "When the year turns gold, down a-long the shore, in the coat you used to *hate*, like the year be-fore.",
    'A3': "When the year turns gold, and{ae n} the *lamps* come on, on the bench out by the gate, till the light is *gone*.",
    'B': "Leaves come down like let-ters, none of them from *you*; I should have asked you to *stay*, but I thought you knew.",
    'A4': "When the year turns gold, and{ae n} the gold turns *gray*, you *still* know the fer-ry gate, (( it's not far a-way. ))",
    'tag': "When the year turns gold, when the year turns gold.",
}

# the voice: the calm ballad singer (sung soft, laid back, few small scoops, slow narrow late vibrato, no falls); at
# 62 BPM on long notes the consonants run long, so the lay-back is set from them (TODO: nowhere-to-be needed 60 ms at
# 72 BPM for a P-centre on the beat)
# A&R round 1: the vibrato read 12.4 ct (nowhere-to-be, the user's calm reference: 8.0) - narrower, on longer notes only
# the expression (master, feat/singer-expression: back-phrasing, messa di voce and ornaments on repeats are on for
# 'ballad'): the lyrics mark 2 leaned-on words per A (*word*) and one intimate line, the last A's "(( it's not far
# away ))"; ornaments stay rare before the last A (ORN_EARLY) and at the style's amount in A4 and the tag
ORN_EARLY = dict(amount=0.12)
VOICE = dict(voice='hanami', style='ballad', vel=(56, 84), late_ms=58.0, late_first_ms=20.0)   # (the slow
# ballad's vibrato - vib_ct 13, peak 19, min 1.1 s, model_vib 0.35 - is the style's default at <= 80 BPM now)
BREATH_S = 0.5

# ------------------------------------------------------------------------------------------------ the piano
# the rubato intro: a hint of the hook over Gbmaj9, the F7 held (fermata) - harmonized by the pianist
PNO_INTRO = notes('r/4 Db5/8 Eb5/8 F5/4. Ab5/8 | Gb5/4 F5/8 Eb5/8 C5/2', length='bar')
# answers in the voice's gaps (beats of the 8-bar A): after "gold" (Bb7b9), after "said" (Ab7b9), after "five", and
# the turnaround bar
FILLS = {
    'A1': notes('@6 F5/8 D5/8 Cb5/8 Ab4/8 @14 Eb5/8 C5/8 @22 F5/8 Eb5/8 @28 A4/8 Db5/8 Eb5/8 Gb5/8 F5/4. Db5/8',
                length=32),
    'A3': notes('@6 Ab5/8 F5/8 D5/8 Bb4/8 @14 C5/8 Eb5/8 @30 Gb5/8 F5/8 Eb5/8 C5/8', length=32),
    'Ai': notes('@6 D5/8 F5/8 Ab5/8 Cb6/8 @14 Gb5/8 Eb5/8', length=32),
    'A4': notes('@6 F5/4 D5/8 Bb4/8 @14 Eb5/8 Gb5/8 @30 G4/8 Bb4/8 Db5/8 E5/8', length=32),
}

# ------------------------------------------------------------------------------------------------ the strings
# violins I: a sustained halo above her, moving in her gaps; the bridge's line; violins II / violas / cellos a bed
# (h.voice) under her; the climax: violins in octaves, the cellos' counter-line in half notes
_HALO = 'Ab5/1 | Ab5/2 G5/4 F5/4 | Gb5/1 | F5/2 Eb5/4 C5/4 | Eb5/2 Db5/2 | Db5/2 D5/4 F5/4 | '
STR = {
    'halo_a2': _HALO + 'Gb5/1 | F5/2 r/2',
    'halo_a3': _HALO + 'Gb5/1 | F5/2 Gb5/4 Ab5/4',
    'halo_a4': _HALO + 'Gb5/1 | F5/2 E5/2',
    'bridge': 'E5/1 | A5/2 G#5/4 D#5/4 | D5/2 D5/4 C#5/4 | E5/2 D5/4 Bb4/4 | Ab5/1 | G5/2 F5/4 Cb5/4 | Gb5/1 | '
              'F5/2 Eb5/4 A4/4',
    'cello_b2': 'A2/2 C#3/2 | F#3/2 D#3/2 | D3/2 E3/2 | C#3/2 Bb2/4 E3/4 | F3/2 Ab3/2 | D3/2 Cb3/2 | Gb3/2 Bb3/2 | '
                'Db3/2 C3/2',
    'ai_halo': 'r/1 | r/1 | r/1 | r/1 | Eb5/2 Db5/2 | Db5/2 D5/4 F5/4 | Gb5/1 | F5/2 r/2',
    'tag': 'Eb5/1 | Ab5/2 G5/2 | Gb5/1 | F5/2 Eb5/2',
}
STRINGS_TRIM = 9.0      # the sections' calibrated mf sits ~19 dB under the close voice: the faders up
HARP_TRIM = 12.0        # the harp's gliss and last roll read 'nearly inaudible' at +8, too loud at +16: a colour, but heard
MASTER_WIDTH = 1.15     # the dry centred voice leaves the sung As 'narrow' (11 % above 150 Hz)
MASTER_MAKEUP = 1.0     # the eq's loss and the quieter voice made up at the limiter
ARC = {'intro': -3.0, 'verse': -2.5, 'A1': -2.0, 'A2': -1.5, 'B': -0.5, 'A3': -1.0, 'Ai': -1.0, 'B2': 1.0,
       'A4': -0.5, 'tag': -2.0, 'end': -2.5}
# the harp: a glissando up the A-major scale into the climax, the last chord rolled up
HARP_GLISS = [(-1.5 + 1.5 * i / 21, 0.6, note(x), 40 + i) for i, x in enumerate(
    'E3 F#3 G#3 A3 B3 C#4 D4 E4 F#4 G#4 A4 B4 C#5 D5 E5 F#5 G#5 A5 B5 C#6 E6'.split())]
HARP_END = [(0.12 * i, 7.5, note(x), 46 - i) for i, x in enumerate('Db2 Ab2 F3 C4 Eb4 G4 C5 F5'.split())]
# the verse has no bass: the pianist's left hand plays the roots (root, then its fifth), held in the pedal
VERSE_LH = notes('Bb1/4 F2/2. | Gb1/4 Db2/2. | Eb2/4 Bb2/2. | F1/4 C2/4 F1/2 | Bb1/4 F2/2. | G1/4 Db2/4 C2/2 | '
                 'F1/4 C2/2. | Eb2/2 Ab1/2', length='bar')
END_CHORD = hold('Ab2=44 F3=46 C4=48 Eb4=50 G4=54 Bb4=52', 7.6, length=8)      # Db6/9(#11) over the bass's Db


def build() -> Song:
    s = Song('When the Year Turns Gold', tempo=TEMPO, key='Db major', seed=62, tail=7)
    (intro, verse, a1, a2, b_, a3, ai, b2, a4, tag, end) = s.form(FORM, parts=CHANGES)
    SEC = {x.name: x for x in (intro, verse, a1, a2, b_, a3, ai, b2, a4, tag, end)}

    # ------------------------------------------------------------------------------------------ time
    # the intro and the verse out of time: slower, breathing phrases, an unmetronomic pulse, fermatas at the ends
    s.set_tempo(intro, VERSE_BPM)
    s.rubato(intro, depth=0.08, phrase='lean', seed=1)
    s.fermata(intro.bar(1) + 2, hold=2.0)
    s.rubato(verse, depth=0.1, phrase='breath', seed=2)
    s.lilt(verse, beats={}, jitter=0.04, seed=3)
    s.fermata(verse.bar(7) + 2, hold=2.5)
    s.set_tempo(a1, TEMPO)
    for i, sec in enumerate((a1, a2, b_, a3, ai, a4)):
        s.rubato(sec, depth=0.03, phrase='breath', seed=10 + i)
    s.ritardando((b2.bar(6), b2.end), to=0.9, a_tempo=True)

    # ------------------------------------------------------------------------------------------ the band
    # the ballad preset, STRAIGHT (no swing: Feel ratio 0.5); its tenor is not used
    b = bands.make('jazz_ballad', s, without=('sax',), feel=jazz.Feel(TEMPO, ratio=0.5), lead='vocal')
    kit = b.info['kit']
    # the strings: the symphony preset's four upper string sections in their own concert hall
    o = bands.symphony_orchestra(s, without=('basses', 'flutes', 'oboes', 'clarinets', 'bassoons', 'horns',
                                             'trumpets', 'trombones', 'tuba', 'timpani', 'percussion', 'celesta'))
    for role in ('violins1', 'violins2', 'violas', 'cellos'):
        o[role].gain_db += STRINGS_TRIM
    o['harp'].gain_db += HARP_TRIM
    # the SSO sections are dark on top: the hall's return opened to 20 kHz and lifted above 9 kHz (as in unbowed)
    hall = o.buses['hall']
    hall.automate('fx.convolver.highcut', [(0, 20000.0)])
    hall.add_fx(fx.eq({'high.freq': 9000, 'high.gain': 2.0, 'high.q': 0.7071}))
    DYN = {'A2': [(0, 'pp'), (16, 34), (28, 'p'), (32, 40)],
           'B': [(0, 44), (12, 'mp'), (16, 58), (28, 62), (32, 50)],
           'A3': [(0, 46), (24, 40), (32, 44)],
           'Ai': [(0, 44), (16, 52), (28, 60), (32, 62)],
           'B2': [(0, 62), (12, 72), (20, 'mf'), (28, 70), (32, 56)],
           'A4': [(0, 50), (16, 44), (32, 42)],
           'tag': [(0, 42), (16, 36)]}
    sc = orch.Score(s, o, DYN, seed=62)
    rng = random.Random(62)
    vmem, pmem = singer.Memory(), pianist.Memory()

    def sing(name, sec, take=0, **kw):
        line = VOX(name)
        v = singer.sing(s, line, LYRICS[{'B2': 'B'}.get(sec.name, sec.name)], at=sec, seed=7, take=take,
                        memory=vmem, split_s=BREATH_S, **{**VOICE, **kw})
        SOLO.setdefault('vocal', []).append(v)
        return v, line

    def comp(sec, vel, answer=None, density=0.35, intensity=0.28, seed=0, register=('A2', 'F4')):
        """The left-hand chords: rolled ballad comping under / around the voice, the pedal with the harmony."""
        c = jazz.comp(sec.prog, style='ballad', voicing='rootless', register=register, density=density,
                      intensity=intensity, vel=vel, answer=answer, seed=seed)
        b.comp.play(c.roll((16, 34), seed=rng, bpm=s.tempo_at(sec)), sec)
        jazzband.pedal([b.piano, b.comp], sec.prog, sec)

    def fills(sec, line, density=0.5, seed=0):
        """The pianist's answers in the voice's gaps (harmonized, decorated, budgeted song-wide)."""
        arr = pianist.arrange(line, sec.prog, bpm=s.tempo_at(sec), key=s.key, style='ballad', density=density,
                              seed=seed, memory=pmem, at=sec)
        b.piano.play(arr.rh, sec)
        return arr

    def bass(sec, vel, feel='two', seed=0):
        b.bass.play(jazz.walking_bass(sec.prog, key=s.key, straight=True, feel=feel, pickups=0.25, vel=vel,
                                      gate=0.95, seed=seed), sec)

    def brushes(sec, vel, seed=0):
        b.drums.play(jazzband.brushes(b, int(sec.bars), style='ballad', straight=True, kick=None, fills=False,
                                      vel=vel, seed=seed), sec)

    def pad(sec, roles=('violins2', 'violas', 'cellos')):
        """The strings' bed under her: violins II / violas in two divisi voices below the voice, cellos on the
        chord's lower tones (the upright has the roots), the dynamics from the score's map."""
        h = s.harmony(CHANGES[sec.parts[0].name], sec)
        regs = {'violins2': (('Ab3', 'F4'), 2), 'violas': (('Eb3', 'Bb3'), 2), 'cellos': (('Db3', 'Ab3'), 1)}
        for role in roles:
            reg, n = regs[role]
            sc.add(role, [(x.start, x.dur, x.pitch) for x in h.voice(reg, n, 60)])

    def strings(role, spec, sec, shift=0, off=0):
        """A written string line (notation, from the section's start) into the score."""
        sc.add(role, [(sec.start + n.start, n.dur, n.pitch + shift) for n in notes(spec, length='bar')], off=off)

    # ============================================================== intro + verse: rubato, voice and piano
    arr = pianist.arrange(PNO_INTRO, intro.prog, bpm=VERSE_BPM, key=s.key, style='ballad', density=0.7, seed=1,
                          lh='rootless', memory=pmem, at=intro)
    arr.place(b.piano, b.comp)
    jazzband.pedal([b.piano, b.comp], intro.prog, intro)
    v_verse, l_verse = sing('verse', verse)
    comp(verse, 60, answer=l_verse, density=0.4, intensity=0.25, seed=2, register=('Bb2', 'Gb4'))
    b.comp.play(jazz.touch(VERSE_LH, lo=44, hi=58), verse)

    # ============================================================== A1: a tempo, the band
    _, l1 = sing('a1', a1)
    comp(a1, 58, answer=l1, seed=3)
    fills(a1, FILLS['A1'], seed=4)
    bass(a1, 70, seed=5)
    brushes(a1, 0.5, seed=6)

    # ============================================================== A2: the strings enter
    _, l2 = sing('a2', a2, take=1, ornament=ORN_EARLY)
    comp(a2, 56, answer=l2, density=0.3, seed=7)
    bass(a2, 72, seed=8)
    brushes(a2, 0.55, seed=9)
    pad(a2)
    strings('violins1', STR['halo_a2'], a2)

    # ============================================================== B: the bridge
    _, lb = sing('b', b_)
    comp(b_, 58, answer=lb, density=0.3, intensity=0.3, seed=10)
    bass(b_, 74, seed=11)
    brushes(b_, 0.6, seed=12)
    pad(b_)
    strings('violins1', STR['bridge'], b_)

    # ============================================================== A3
    _, l3 = sing('a3', a3, take=2, ornament=ORN_EARLY)
    comp(a3, 58, answer=l3, density=0.3, seed=13)
    fills(a3, FILLS['A3'], seed=14)
    bass(a3, 72, seed=15)
    brushes(a3, 0.55, seed=16)
    pad(a3)
    strings('violins1', STR['halo_a3'], a3)

    # ============================================================== Ai: the strings sing the first half, the piano the second
    a2_line = VOX('a2')
    sc.add('violins1', [(ai.start + n.start, n.dur, n.pitch + 12) for n in a2_line if n.start < 16], off=6)
    sc.add('violins2', [(ai.start + n.start, n.dur, n.pitch) for n in a2_line if n.start < 16], off=2)
    fills(ai, FILLS['Ai'], seed=17)
    second = Clip([n for n in jazz.touch(a2_line.transpose(12), lo=60, hi=94) if n.start >= 16], length=32)
    arr = pianist.arrange(second, ai.prog, bpm=TEMPO, key=s.key, style='ballad', density=0.6, seed=18,
                          memory=pmem, at=ai)
    b.piano.play(arr.rh, ai)
    comp(ai, 56, answer=a2_line, density=0.3, seed=19)
    bass(ai, 72, seed=20)
    brushes(ai, 0.55, seed=21)
    pad(ai, roles=('violas', 'cellos'))
    h_ai = s.harmony(CHANGES['A2'], ai)
    sc.add('violins2', [(x.start, x.dur, x.pitch) for x in h_ai.voice(('Ab3', 'F4'), 2, 60) if x.start >= ai.start + 16])
    strings('violins1', STR['ai_halo'], ai)

    # ============================================================== B2: the climax
    _, lb2 = sing('b2', b2, take=1, ornament=ORN_EARLY)
    comp(b2, 60, answer=lb2, density=0.3, intensity=0.32, seed=22)
    bass(b2, 76, seed=23)
    brushes(b2, 0.65, seed=24)
    pad(b2, roles=('violas',))
    strings('violins1', STR['bridge'], b2, off=2)
    strings('violins2', STR['bridge'], b2, shift=-12, off=-2)
    strings('cellos', STR['cello_b2'], b2, off=4)
    sc.play('harp', Clip([(t0 + 1.5, d, p, v) for t0, d, p, v in HARP_GLISS], length=4), b2.start - 1.5)

    # ============================================================== A4 + tag + end
    _, l4 = sing('a4', a4, take=3)
    comp(a4, 56, answer=l4, density=0.3, seed=25)
    fills(a4, FILLS['A4'], seed=26)
    bass(a4, 70, seed=27)
    brushes(a4, 0.5, seed=28)
    pad(a4)
    strings('violins1', STR['halo_a4'], a4)
    _, lt = sing('tag', tag, take=1)
    comp(tag, 52, answer=lt, density=0.25, intensity=0.22, seed=29)
    bass(tag, 64, seed=30)
    brushes(tag, 0.45, seed=31)
    pad(tag)
    strings('violins1', STR['tag'], tag)
    sc.fermata('Dbmaj9#11', end, 8, {'violins1': ('G5', 30), 'violins2': ('C5 Eb5', 30), 'violas': ('Ab3 F4', 32),
                                     'cellos': ('Db3', 34)}, shapes='dim')
    sc.play('harp', Clip(HARP_END, length=8), end)
    s.ending(end, chords=[(b.comp, END_CHORD, 40)], bass=(b.bass, 'Db2', 7, 64),
             drums=(b.drums, jazz.last_stir(kit, 8, last=3)), rit=tag.bar(2), to=0.75, hold=3, length=4,
             room=(-13, -9))
    sc.perform()

    # ============================================================== production
    voc = SOLO['vocal'][0].track
    hero(voc, family='vocal', genre='jazz', bed=[o['violins1'], o['violins2'], o['violas'], o['cellos']],
         competitors=[b.piano], drive=False)

    # the arc: the verse intimate, the band entering, the bridge warmer, the climax at B2, the last A settling back
    s.arc(ARC)

    # ============================================================== master (MASTER.md): platform dynamic, the jazz tone
    mastering.apply(s, eq={'high.freq': 6300, 'high.gain': 3.2, 'high.q': 0.7071, 'peak1.freq': 800,
                           'peak1.gain': -1.8, 'peak1.q': 1.0},
                    width=MASTER_WIDTH, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=MASTER_MAKEUP)
    return s
