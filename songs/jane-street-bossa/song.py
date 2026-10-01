"""Down on Jane Street - an original bossa-tinged straight-8th jazz song for a female voice and piano trio
(Bb major, 126 BPM, ~3:25). Build: python -m agentsound build songs/jane-street-bossa

New York bar jazz without swing, sung: Hanami (a licensed DiffSinger voicebank) through agentsound.singer and the
vocal hero chain (clean), a grand piano that comps and answers AROUND the voice, an upright bass and brushes with a
cross-stick - a soft bossa groove that opens into a straight "push" four in the C sections and the solo's climax.
Brief: BRIEF.md, form and changes: ARRANGEMENT.md, words: LYRICS.md. The tune is a 32-bar ABAC:

  A1   Bbmaj9 | Eb9#11 | Cm9 | F13    | Dm7  | G7b9  | Cm9 F7b9    | Fm9 Bb13
  B    Ebmaj9 | Ab9#11 | Dm7 | G7b9   | Cm9  | Ebm6  | Dm7 G7#9    | Cm9 F7b9
  A2   = A1, the last bar Dm7b5 G7b9 into the C
  C    Cm9    | Ebm6   | Dm7 | Dbdim7 | Cm9  | F7alt | Bbmaj9 Gm9  | Cm9 F13

The hook ("Down on Jane Street, rain"): a pickup leaping a sixth to a held D, sighing to C, and the A held while
Bbmaj9 turns into Eb9#11 (the maj7 becomes the #11); in the C it comes back a fourth higher, the song's top note.

  intro       8   bass, cross-stick and shaker start the bossa, the piano's left hand comps; bars 5-8 the hook on
                  the piano, brushes enter, a fill into the voice
  head       32   sung (A1 B A2 C); the piano comps the bossa under the voice and answers in its rests
  piano_solo 32   soloist.solo with the piano vocabulary (pianist.vocabulary): the hook stated, answered,
                  developed, a burst, the climax (the saved trill), resolved; bossa -> push -> drive with the ride
  head_out   24   sung again from the B, freer (paraphrased), a soft third below on the climax line, the last line
                  turned ("now you can keep the wait")
  tag         4   the hook twice, B7#11 (the tritone sub), ritardando
  end         2   the voice's last "rain", Bbmaj9 (6/9) rolled into the pedal ringing on after it, fermata
"""
import functools
import random

from agentsound import *
from agentsound import bands, jazz, mastering, pianist, singer, soloist
from agentsound.bandlib import jazz as jazzband

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'Down on Jane Street', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#2f7a6b', '#e8b04a'], 'title': 'down on jane street',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 21}

# the mix engineer's moves (MIX.md): the voice 1.5 dB down (the sung sections read 3 LU over the solo) with a 2 dB
# presence dip (2-5 kHz +3.3 dB over the jazz reference, 94 % of it the voice: warm, not glassy), the last 'rain'
# softer, the bass up 1 dB (7.7 dB under the voice), the kit trimmed 0.3 dB (16.7 under the voice after the vocal
# trim: inside 13-16), a low bell on the piano where its left hand and the upright share 60-250 Hz
MIX = {
    'trim': {'drums': -0.3, 'rim': -0.3, 'shaker': -1.0, 'vocal': -1.5, 'bass': 1.0},
    'ride': {'vocal': {'end': -2.0}, 'piano': {'tag': -1.5}, 'shaker': {'head': -2.0, 'head_out': -2.0}},
    'eq': {'piano': [{'freq': 160, 'gain': -2.0, 'q': 0.8}], 'vocal': [{'freq': 3300, 'gain': -2.0, 'q': 1.0}],
           'bass': [{'freq': 63, 'gain': -2.0, 'q': 1.0}]},
}

TEMPO = 126
ARRANGED = {}          # section:part -> pianist.Arrangement (filled by build(): what the pianist played)
SOLO = {}              # 'perf' -> the soloist.Performance of the piano solo, 'vocal' -> the singer's parts
MASTER_DRIVE = 4.0      # with the voice the mix reads ~2 LU louder into the master: less drive
PIANO_TRIM = -4.5      # the piano peaked +0.6 dBFS pre-master at the preset level (touch accents)
BASS_TRIM = 5.0        # the bass read 12.8 dB under the piano (target 3-6.5)

# ------------------------------------------------------------------------------------------------ changes
CHANGES = {
    'A1': 'Bbmaj9 Eb9#11 Cm9 F13 | Dm7 G7b9 Cm9:0.5 F7b9:0.5 Fm9:0.5 Bb13:0.5',
    'B': 'Ebmaj9 Ab9#11 Dm7 G7b9 | Cm9 Ebm6 Dm7:0.5 G7#9:0.5 Cm9:0.5 F7b9:0.5',
    'A2': 'Bbmaj9 Eb9#11 Cm9 F13 | Dm7 G7b9 Cm9:0.5 F7b9:0.5 Dm7b5:0.5 G7b9:0.5',
    'C': 'Cm9 Ebm6 Dm7 Dbdim7 | Cm9 F7alt Bbmaj9:0.5 Gm9:0.5 Cm9:0.5 F13:0.5',
    'iv': 'Cm9 F13 Cm9 F13', 'ih': 'Dm7 G13 Cm9 F7b9',
    'tag': 'Dm7:0.5 G7b9:0.5 Cm9:0.5 F13:0.5 Ebm6:0.5 Ab9:0.5 Cm9:0.5 B7#11:0.5',
    'end': 'Bbmaj9:2',
}
FORM = 'intro:iv,ih head:ABAC piano_solo:ABAC head_out:B,A2,C tag:4 end:2'

# ------------------------------------------------------------------------------------------------ the voice
# notation (docs/COMPOSE_API.md "Notation"): sticky note values, '|' checks the bars, '~' ties into the next bar.
# Hanami sings A3..G5 here (her range F3-A5); one note per syllable, the lyrics below (LYRICS.md)
VOX = phrases(
    hook='r/4 F4/8 G4 D5/4. C5/8 | A4/2. r/4 |',
    a_rest="""r/8 Eb4/4 F4/8 C5/4. Bb4/8 | G4/8 A4 C5/2. |
              r/8 F4 A4/4. F4/8 D5/4 | r/8 F4 Ab4/4. F4/8 D5/4 | r/8 G4 Bb4 G4 Eb5/4 D5/8 C5~ | C5/2 r/2 |""",
    length='bar')
VOX_A = VOX('hook a_rest')                       # A1 and A2: the same tune, other words
VOX_B = notes("""
 r/8 Bb4 D5/4 r/8 Bb4 C5 D5 | Eb5/2 C5/4 r | r/4. A4/8 D5/4. C5/8 | B4/4. Ab4/8 G4/2 |
 r/8 G4 Bb4/4. G4/8 D5/4 | C5/8 Bb4/2 Gb4/8 r/4 | r/8 F4 A4/4 F4/8 Bb4/4 G4/8 | D5/2 r/2""", length='bar')
VOX_C = notes("""
 r/4 G4/8 Bb4 Eb5/4. D5/8 | C5/8 Bb4/2. r/8 | r/8 A4 C5/4 r/8 A4 D5/4 | r/8 Db5 Bb4/2. |
 r/4 Bb4/8 C5 G5/4. F5/8 | Eb5/2. r/4 | r/4 F4/8 A4 C5/4 D5/8 r | Bb4/8 D5/2..""", length='bar')
VOX_TAG = notes('r/4 F4/8 G4 D5/4. B4/8 | A4/2. r/4 | r/4 Gb4/8 Ab4 Eb5/4. C5/8 | r/1', length='bar')
VOX_END = notes('D5:4.5', length=8)       # the voice lets go first, the chord rings on

LYRICS_A1 = "Down on Jane Street rain, taps the awn-ing, sings a while. I or-dered two, I drank them both, I tipped the band a smile."
LYRICS_B = "Your chair is full of eve-ning, the can-dle leans your way, the wai-ter wipes the ta-ble, I tell the eve-ning, stay."
LYRICS_A2 = "Down on Jane Street rain, writes your name a-cross the glass. I let you be, I let you go, I let the tax-is pass."
LYRICS_C = "Let the bass walk me home, I'm not the one who's late, down on Jane Street rain, so I don't mind the wait."
LYRICS_C_OUT = "Let the bass walk me home, I'm not the one who's late, down on Jane Street rain, now you can keep the wait."
LYRICS_TAG = "Down on Jane Street rain, down on Jane Street"
LYRICS_END = "rain."

# ------------------------------------------------------------------------------------------------ the piano
# answers in the voice's rests (part beats: '@' = the position), harmonized lightly by the pianist; the comping
# (jazz.comp, bossa cells) runs under the voice and answers its rests too
FILL_A1 = notes('@7 G5/8 A5 C6 @30 D5/8 F5 A5 C6 Bb5/4 G5/8 F5', length=32)
FILL_A2 = notes('@7 G5/8 A5 C6 @30 Ab5/8 F5 D5 B4 Ab4/4', length=32)
FILL_B = notes('@7 C6/8 Bb5 G5 F5 D5 @30 Ab5/8 Gb5 Eb5 C5 A4/4', length=32)
FILL_C = notes('@16 F5/8 G5 @23 Db6/8 B5 A5 F5', length=32)
FILL_TAG = notes('@6 F5/8 G5 A5 C6 D6/4 r/4 @12 Eb5/8 G5 Bb5 D6 Eb6/4 B5/8 A5', length=16)
INTRO_HINT = notes('r/4 F5/8 D6/4. C6/8 A5~ | A5/2 r/2 | r/4 Eb5/8 C6/4. Bb5/8 G5 | A5/4 r/2.', vel=72, length='bar')
HOOK = notes('r/4 F5/8 G5 D6/4. C6/8 | A5/2. r/4', length='bar')     # the solo's motif: the hook on piano
END_CHORD = hold('F3=52 A3=54 D4=56 G4=58 C5=62', 7.6, length=8)      # under the voice's D5; the bass has the Bb

# the pianist's ornaments: turns, mordents, crushes, re-struck voicings and rolls; a trill or tremolo is rare
# (HUMAN_FEEDBACK: fast two-key alternations are spice, not the main dish)
# the answers in the voice's rests are voiced (3rds / 6ths / guide tones under them), never a bare line
ANSWER_DEVICES = {'thirds': 2.0, 'sixths': 2.0, 'guide': 1.5, 'drop2': 1.0}
ORN = {'turn': 1.2, 'mordent': 1.0, 'inverted_mordent': 0.5, 'crush': 1.0, 'restrike': 1.6, 'roll': 1.0,
       'blues_crush': 0.4, 'trill': 0.25, 'tremolo': 0.2}

# Hanami as a jazz singer: the ballad style laid back a little more, soft-leaning, small falls, a narrow vibrato that
# blooms only on the held peaks
VOICE = dict(voice='hanami', style='ballad', late_ms=10.0, fall=0.12, doit=0.0, vib_ct=22.0, peak_vib_ct=34.0,
             scoop_first=0.3, scoop_leap=0.4, scoop_peak=0.5,
             soft=0.75, power=0.35, vel=(60, 100))


def bossa_bass(prog, lo, hi, seed=0):
    """The bossa bass: root on 1 and 3, the fifth on the & before (R__f), played with a bassist's touch."""
    line = prog.bass(pattern='R__f', rate='1/8', low='C2', vel=90, gate=0.85)
    return jazz.bass_touch(line, lo, hi, accent='1-3', seed=seed)


def bossa_kit(b, at, bars, seed, vel=1.0, shaker=True, rim=True, fills=True):
    """The bossa kit (bossa_groove: brush 8ths + kick + hat foot, cross-stick, egg shaker) from `at` for `bars`."""
    g = jazzband.bossa_groove(bars, b, seed=seed, vel=vel, fills=fills)
    for role, on in (('drums', True), ('rim', rim), ('shaker', shaker)):
        if on:
            b[role].play(g[role], at)


def build() -> Song:
    s = Song('Down on Jane Street', tempo=TEMPO, key='Bb major', seed=21, tail=6)
    intro, head, solo, hout, tag, end = s.form(FORM, parts=CHANGES)
    # the bossa band as a trio: Salamander grand (both hands on one track), Meatbass, Swirly brushes, Blonde Bop
    # cross-stick, FreePats shaker, salon IR + 224XL plate; straight 8ths (the preset's Feel, ratio 0.5)
    b = bands.make('bossa', s, without=('guitar', 'sax'), master_gain=MASTER_DRIVE)
    b.piano.gain_db += PIANO_TRIM
    b.piano.pan = -0.25               # no guitar on the left: the piano nearer the centre (the mix leaned 1.8 dB left)
    b.bass.gain_db += BASS_TRIM       # the preset's bass fader is set for the guitar band's accented pattern
    b.shaker.gain_db += 2.0           # a whisper, but audible (it read 0.2 % of any band at the preset level)
    b.drums.gain_db += 1.5            # brushes 17 dB under the piano: up into the 13-16 dB window
    kit = b.info['kit']
    # air, not bite (HUMAN_FEEDBACK "es klingt hart": no 2-5 kHz boost on the piano)
    b.piano.add_fx(fx.eq({'high.freq': 9000, 'high.gain': 1.5}))
    rng = random.Random(21)
    mem = pianist.Memory()            # one pianist for the whole song: the ornament budget counts song-wide
    vmem = singer.Memory()            # the singer's spice budget (falls, big scoops) song-wide
    play = functools.partial(jazz.chorus, b, memory=mem, record=ARRANGED, defaults=dict(
        piano=dict(lh=None, style='sparse', ornaments=ORN), bass=dict(straight=True),
        drums=dict(straight=True, style='medium')))

    def comp(part, vel, intensity=0.35, density=0.55, seed=0):
        """The piano's bossa comping under the voice: the two-bar cells all through (rootless, below the voice, soft,
        rolled) - the A&R found the answer=line comping dropping out under every sung note (9 of 32 head bars empty)"""
        c = jazz.comp(part.prog, style='bossa', voicing='rootless', register=('A2', 'E4'), intensity=intensity,
                      density=density, vel=vel, seed=seed)
        b.piano.play(c.roll((10, 22), seed=rng, bpm=TEMPO), part)
        jazzband.pedal([b.piano], part.prog, part)

    def sing(line, words, at, take=0, **kw):
        v = singer.sing(s, line, words, at=at, seed=7, take=take, memory=vmem, **{**VOICE, **kw})
        SOLO.setdefault('vocal', []).append(v)
        return v

    # ============================================================== intro
    iv, ih = intro.parts
    # the groove first: bass, cross-stick and shaker; the piano's left hand comps the bossa (rolled, soft)
    b.bass.play(bossa_bass(iv.prog, 60, 80, seed=1), iv)
    b.bass.play(bossa_bass(ih.prog, 66, 88, seed=2), ih)
    bossa_kit(b, iv, 4, seed=3, vel=0.5, fills=False)
    b.drums.clear(iv.start, iv.end, pitches=[kit['tap']])                  # no brush 8ths yet: kick + foot only
    bossa_kit(b, ih, 4, seed=4, vel=0.6, shaker=True)
    lhc = jazz.comp(iv.prog, style='bossa', voicing='rootless', register=('Eb3', 'C5'), intensity=0.45, vel=70,
                    seed=5).roll((10, 22), seed=rng, bpm=TEMPO)
    b.piano.play(lhc, iv)
    # bars 5-8: the hook on the piano (harmonized), an answer, a fill into the voice
    play(intro, {'ih': INTRO_HINT}, bass=None, piano=dict(
        iv=None, ih=dict(touch=(56, 92), style='straight', density=0.5, seed=101, lh='guide', lh_vel=50,
                         section_end=True, fills={'run': 2.0, 'arpeggio': 1.5, 'gliss': 2.0})))
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(16, 48)), intro.beat(-2))

    # ============================================================== head: sung
    A1, B_, A2, C_ = head.parts
    vox = sing(VOX_A, LYRICS_A1, A1)
    sing(VOX_B, LYRICS_B, B_)
    sing(VOX_A, LYRICS_A2, A2)
    sing(VOX_C, LYRICS_C, C_)
    for part, v, sd in ((A1, 50, 11), (B_, 52, 12), (A2, 52, 13), (C_, 56, 14)):
        comp(part, v, seed=sd)
    # the piano's answers in the voice's rests
    play(head, [FILL_A1, FILL_B, FILL_A2, FILL_C], piano=dict(
        seed=201, style='straight', density=0.75, pedal=False, devices=ANSWER_DEVICES,
        touch=jazz.each((54, 82), (56, 86), (56, 86), (60, 92)),
        fill=0.0, embellish=0.2, section_end=False),
        bass=dict(A1=None, B=None, A2=None, C=dict(seed=31, feel='push', vel=90)),
        drums=dict(A1=None, B=None, A2=None, C=dict(seed=41, vel=0.8, ghosts=0.4, kick='even', hat8=0.6)))
    for part, (lo, hi), sd in ((A1, (74, 98), 32), (B_, (76, 100), 33), (A2, (76, 100), 34)):
        b.bass.play(bossa_bass(part.prog, lo, hi, seed=sd), part)
    bossa_kit(b, A1, 8, seed=42, vel=0.74)
    bossa_kit(b, B_, 8, seed=43, vel=0.82)
    bossa_kit(b, A2, 8, seed=44, vel=0.86)

    # ============================================================== piano solo: the soloist plays the arc
    sA1, sB, sA2, sC = solo.parts
    # the fast figure (trill / tremolo) is saved for the climax (the arc's top: the C's 3rd bar)
    bud = soloist.Budget(spice_every=2, fast_every=16, same_every=32).save(sC.start + 8)
    # 4-bar phrases: the statement states the hook once and answers it (2-bar phrases repeated it three times running)
    voc = pianist.vocabulary('straight', lh_track=b.piano, lh='guide', lh_vel=54, memory=mem, seed=7, phrase_bars=4)
    SOLO['perf'] = soloist.solo(s, b.piano, voc, at=solo, prog=solo.prog, motif=HOOK, budget=bud, seed=11)
    b.piano.feature(solo, db=0.6)     # the pianist steps up for the solo (and leads it for the mixer)
    play(solo, None, bass=dict(A1=None, B=None, A2=dict(seed=61, feel='push', vel=90),
                               C=dict(seed=62, feel='drive', vel=94)),
         drums=dict(A1=None, B=None, A2=dict(seed=71, vel=0.85, ghosts=0.4, kick='even', hat8=0.7),
                    C=dict(seed=72, vel=0.95, kick='even', ride=0.9)))
    b.bass.play(bossa_bass(sA1.prog, 76, 98, seed=63), sA1)
    b.bass.play(bossa_bass(sB.prog, 78, 100, seed=64), sB)
    bossa_kit(b, sA1, 8, seed=73, vel=0.82)
    bossa_kit(b, sB, 8, seed=74, vel=0.88)
    b.drums.play(Clip([(0, 2, kit['crash'], 38)], length=4), sC)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(20, 52)), solo.beat(-2))

    # ============================================================== head out: sung from the B
    hB, hA2, hC = hout.parts
    # the out chorus is sung freer: the same words, the phrases paraphrased (anticipated / laid back - the singer's
    # second time through), and a soft third below on the climax line ('down on Jane Street, rain')
    def loose(line, seed):
        return jazz.paraphrase(line, seed=seed, anticipate=0.3, delay=0.15, embellish=0.0, key=s.key)
    sing(loose(VOX_B, 81), LYRICS_B, hB, take=1)
    sing(loose(VOX_A, 82), LYRICS_A2, hA2, take=1)
    out_c = loose(VOX_C, 83)
    sing(out_c, LYRICS_C_OUT, hC, take=1)
    harm = sing(out_c.slice(16, 24).transpose_scale(-2, s.key), 'down on Jane Street rain.', hC.start + 16, take=2,
                track_id='vocal_harm', pan=0.3, gain_db=-8.0, formant=0.25)
    for part, v, sd in ((hB, 54, 15), (hA2, 54, 16), (hC, 58, 17)):
        comp(part, v, density=0.65, seed=sd)
    play(hout, [FILL_B, FILL_A2, FILL_C], piano=dict(
        seed=401, style='straight', density=0.8, pedal=False, devices=ANSWER_DEVICES,
        touch=jazz.each((56, 86), (58, 88), (62, 96)), fill=0.0,
        embellish=0.25, section_end=False),
        bass=dict(B=None, A2=None, C=dict(seed=161, feel='push', vel=92)),
        drums=dict(B=None, A2=None, C=dict(seed=171, vel=0.85, ghosts=0.5, kick='even', hat8=0.7)))
    b.bass.play(bossa_bass(hB.prog, 76, 98, seed=162), hB)
    b.bass.play(bossa_bass(hA2.prog, 78, 100, seed=163), hA2)
    bossa_kit(b, hB, 8, seed=172, vel=0.86)
    bossa_kit(b, hA2, 8, seed=173, vel=0.9)

    # ============================================================== tag + ending
    sing(VOX_TAG, LYRICS_TAG, tag)
    sing(VOX_END, LYRICS_END, end, vel=(52, 62))                # the last 'rain': soft, over the rolled chord
    comp(tag, 50, intensity=0.3, seed=18)
    play(tag, FILL_TAG, pedal_end=end.start - 0.1, bass=None, piano=dict(
        touch=(50, 84), style='ballad', density=0.5, seed=501, bpm=TEMPO * 0.85, fill=0.0, section_end=False,
        pedal=False))
    b.bass.play(bossa_bass(tag.prog, 70, 90, seed=191), tag)
    bossa_kit(b, tag, 4, seed=201, vel=0.6, fills=False)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(12, 40)), tag.beat(-2))
    s.ending(end, chords=[(b.piano, END_CHORD, 75)], bass=(b.bass, 'Bb1', 7, 88),
             drums=(b.drums, jazz.last_stir(kit, 8, last=3)), rit=tag.bar(2), to=0.75, hold=2, length=4,
             room=(-13, -8))

    # ============================================================== the voice's production: the vocal hero, clean
    # (no tube: a jazz voice close and warm), the piano dipped where the words live; a club, not a pop record: no echo
    # throws, the hero plate lower, the voice in the band's own room too (the sung sections read -8 LU of reverb, the
    # jazz recipe wants the room 12-18 LU under the mix)
    hero(vox.track, family='vocal', genre='jazz', competitors=[b.piano], drive=False, echo=False, throws=False)
    vox.track.send('hero_plate', -17).send('room', -15)
    hero(harm.track, family='vocal', genre='jazz', drive=False, echo=False, throws=False, ride=False, duck=False,
         carve=False, dips=False)
    harm.track.send('hero_plate', -17).send('room', -15)

    # ============================================================== the arc (the conductor's ride on the master input)
    # the first A soft, every part a little more, the C's lift; the solo from its statement to the climax in its C,
    # resolved; the last C the warmest (the written dynamics stay: this only shapes the sections against each other)
    s.arc({'intro': 0.0, 'head': -2.5, 'piano_solo': -2.5, 'head_out': -1.5, 'tag': -1.8, 'end': -2.5},
          within={'head': [(31.5, -2.5), (32, -1.5, 'smooth'), (63.5, -1.5), (64, -1.0, 'smooth'), (95.5, -1.0),
                           (96, 0.5, 'smooth')],
                  'piano_solo': [(31.5, -2.5), (32, -1.5, 'smooth'), (63.5, -1.5), (64, -0.3, 'smooth'), (95.5, -0.3),
                                 (96, 1.5, 'smooth'), (115.5, 1.5), (116, -0.5, 'smooth')],
                  'head_out': [(31.5, -1.5), (32, -0.8, 'smooth'), (63.5, -0.8), (64, 1.0, 'smooth')]})

    # ============================================================== master (MASTER.md): the jazz tone (the mids -2.3 dB at
    # 1 kHz), x1.2 width above the mono bass (the sung sections read 13 % wide: a centred voice), the limiter only making
    # up the eq - the post-pass's +1.3 dB drive cost LRA (5.0 -> 4.8)
    mastering.apply(s, eq={'low.freq': 60, 'low.gain': 0.0, 'low.q': 0.7071, 'peak1.freq': 250, 'peak1.gain': 0.7,
                           'peak1.q': 1.0, 'peak2.freq': 1000, 'peak2.gain': -2.3, 'peak2.q': 1.0},
                    width=1.2, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=0.6)
    return s
