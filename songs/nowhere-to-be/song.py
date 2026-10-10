"""Nowhere to Be - an original smooth / soul-jazz ballad for a female voice, Rhodes, upright bass, brushes and a soft
tenor (72 BPM, Eb major, straight 8ths, ~4:20).
Build: python -m agentsound build songs/nowhere-to-be

The user's wish: "versuch nochmal Smooth Jazz mit Sängerin, ganz smooth" - after jane-street-bossa, whose voice only
calmed down when it was sung soft, low, stepwise, sparse, laid back, slower and dry (recipes/HUMAN_FEEDBACK.md
"Vocals"). This one starts there: Hanami in the calm `jazz` style, Eb4-C5 (one D5), 18-20 syllables per 8 bars on
long notes, a breath after every line, 72 BPM, a dry close voice; a warm Rhodes comping AROUND her, the upright in
long notes, brush stirs + a soft cross-stick, a soft pad far under it, and a soft tenor that answers in her gaps and
takes the solo. Brief: BRIEF.md, form and changes: ARRANGEMENT.md, words: LYRICS.md.

  intro    4   the Rhodes alone, rolled; the bass and the stirs come in; the tenor states the hook, low
  verse1   8   sung; Rhodes comps under / around her, cross-stick on 4
  chorus1  8   the hook "Nowhere to be"; the pad enters far under, cross-stick on 2 and 4
  inter    4   the tenor answers the hook at the voice's pitch
  verse2   8   sung (new words), the Rhodes a little fuller
  chorus2  8   the tenor answers twice in her gaps
  solo    16   the tenor's ballad solo on the verse + chorus changes (soloist, hornist vocabulary), bass in 'push'
  bridge   8   the turn: B major (bVI), the song's only D5 on "slow", the one direct line
  chorus3  8   the hook again, a soft harmony a third below on two lines, the last line turned, deceptive Cm9
  tag      4   "nowhere to be" once more, the tenor's answer
  end      2   the last "be" over Ebmaj9 (6/9) rolled into the pedal, ritardando, fermata
"""
import random

from agentsound import *
from agentsound import bands, hornist, jazz, mastering, patches, singer, soloist
from agentsound.bandlib import jazz as jazzband

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'Nowhere to Be', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions', 'genre': 'Jazz',
            'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#3b2a4a', '#e9a86a'], 'title': 'nowhere to be',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 72}

# the mix engineer's moves (MIX.md): the band 2.5 dB further under the voice (the low group read -2..-4 dB under her,
# window -6.5..-3), the tenor up where it leads (intro / inter / solo), the Rhodes out of the upright's 60-250 Hz and
# out of the tenor's 450 Hz, the kit 1 dB back (2.5 under the tenor in its solo), the bass softer under the intro's low
# tenor, the voice's low register 1.5 dB lighter at 380 Hz (low mids +4.7 over the profile, 66 % hers)
MIX = {
    'trim': {'sax': 2.0, 'pad': -2.5},    # the voices -3, piano / bass -2.5, drums / rim -1, the drive: lead='vocal'
    'ride': {'sax': {'intro': -1.5, 'inter': 3.0}, 'bass': {'intro': -3.0}, 'piano': {'intro': -2.0},
             'drums': {'solo': -1.5}, 'rim': {'solo': -1.5}},
    'eq': {'piano': [{'freq': 150, 'gain': -4.5, 'q': 0.7}, {'freq': 450, 'gain': -1.5, 'q': 1.0}],
           'vocal': [{'freq': 380, 'gain': -1.5, 'q': 1.0}]},
}

TEMPO = 72
MASTER_WIDTH = 1.6     # MASTER.md: the dry centred voice leaves the mix ~8 % wide above 150 Hz
BASS_TRIM = 12.0       # the upright read 16 dB under the voice at the preset's bossa fader (target 3-7), played softer
DRUM_TRIM = 9.0        # the stirs read 24 dB under the voice (target 13-16)
KEYS_TRIM = -3.0       # the Rhodes comps 6-10 velocity steps hotter (the bell, not the bark): the fader back
RIM_TRIM = 11.0        # the cross-stick a soft click, ~16 dB under the voice
PAD_GAIN = 0.0         # the pad far under the voice (~12 dB), ducked and carved by her
SOLO = {}


def RHODES():
    """The keys: the jRhodes3d stereo-vibrato set (the suitcase swirl is in the samples), nearly centred (the
    preset would put its piano at -0.5: a balance that throws a stereo Rhodes to one side)."""
    return patches.get('sampled/rhodes_vibrato').but(pan=-0.05)
              # 'perf' -> the soloist.Performance of the tenor solo, 'vocal' -> the singer's parts

# ------------------------------------------------------------------------------------------------ changes
CHANGES = {
    'I': 'Abmaj9 Gm7 Fm9 Bb13sus4',
    'V': 'Abmaj9 Gm7 Fm9 Bb13sus4 | Abmaj9 Gm7:0.5 C7b9:0.5 Fm9 Bb7sus4:0.5 Bb7b9:0.5',
    'C': 'Ebmaj9 Cm9 Abmaj9 Bb13sus4 | Ebmaj9 Gm7:0.5 C7b9:0.5 Fm9:0.5 Bb13sus4:0.5 Ebmaj9',
    'Br': 'Bmaj7 Bbm9:0.5 Eb9:0.5 Abmaj9 Abm6:0.5 Db9:0.5 | Gm7 C7alt Fm9 Bb7sus4:0.5 Bb7b9:0.5',
    'Clast': 'Ebmaj9 Cm9 Abmaj9 Bb13sus4 | Ebmaj9 Gm7:0.5 C7b9:0.5 Fm9:0.5 Bb13sus4:0.5 Cm9',
    'T': 'Abmaj9 Gm7 Fm9 Bb13sus4',
    'E': 'Ebmaj9:2',
}
FORM = ('intro:I verse1:V chorus1:C inter:I verse2:V chorus2:C solo:V,C bridge:Br chorus3:Clast tag:T end:E')

# ------------------------------------------------------------------------------------------------ the voice
# notation (docs/COMPOSE_API.md "Notation"): sticky note values, '|' checks the bars, '~' ties into the next bar.
# Two rhythm cells carry the whole tune: the verse's 'q 8 q. 8 8 | long' and the hook's 'q. 8 8 q.~ | long';
# every 2-bar line is followed by 1-2 beats of rest (a breath, the Rhodes' answer)
VOX = phrases(
    verse="""G4/4 F4/8 G4/4. Ab4/8 G4/8 | Bb4/2. r/4 | Eb4/8 F4/8 G4/4. F4/8 Eb4/4 | F4/2. r/4 |
             C5/4. Bb4/8 G4/8 Bb4/4.~ | Bb4/2 r/2 | Ab4/4. G4/8 F4/8 G4/4.~ | G4/2 r/2""",
    chorus="""G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2 r/2 | F4/4. G4/8 Ab4/8 Bb4/4.~ | Bb4/2 r/2 |
              G4/4. Ab4/8 Bb4/8 Bb4/4 Ab4/8 | C5/2. r/4 | F4/4. G4/8 F4/8 Eb4/4.~ | Eb4/2. r/4""",
    # verse 2's third line climbs instead of falling ("sun-rise can wait": the A&R found every repeat note-for-note)
    verse2="""G4/4 F4/8 G4/4. Ab4/8 G4/8 | Bb4/2. r/4 | Eb4/8 F4/8 G4/4. F4/8 Eb4/4 | F4/2. r/4 |
              Ab4/4. Bb4/8 C5/8 Bb4/4.~ | Bb4/2 r/2 | Ab4/4. G4/8 F4/8 G4/4.~ | G4/2 r/2""",
    # the last chorus's turned line lifts to G4 ("nowhere but YOU" over Bb13sus4 -> the deceptive Cm9: still open)
    chorus3="""G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2 r/2 | F4/4. G4/8 Ab4/8 Bb4/4.~ | Bb4/2 r/2 |
               G4/4. Ab4/8 Bb4/8 Bb4/4 Ab4/8 | C5/2. r/4 | F4/4. G4/8 Ab4/8 G4/4.~ | G4/2. r/4""",
    bridge="""Bb4/4. Ab4/8 Gb4/8 Eb4/4.~ | Eb4/2 r/2 | C5/4. Bb4/8 Ab4/8 G4/4. | r/1 |
              r/8 Bb4/8 C5/4 D5/4. C5/8~ | C5/2. r/4 | r/4 Ab4/4. G4/8 F4/4~ | F4/2 r/2""",
    tag="""G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2 r/2 | r/1 | r/2 F4/4 G4/8 F4/8 | Eb4:4.5""",
    length='bar')

LYRICS_V1 = "Turn the clock to the wall, let the cof-fee go cold, rain on the glass, no one to call."
LYRICS_V2 = "Leave your coat on the chair, let the tel-e-phone go, sun-rise can wait, light in your hair."
LYRICS_C = "No-where to be, no-where to go, stay where the light is slow, no-where to be."
LYRICS_BR = "All of those days run-ning for trains, you said slow down, so I stayed."
LYRICS_C3 = "No-where to be, no-where to go, stay where the light is slow, no-where but you."
LYRICS_TAG = "No-where to be, no-where to be."

# the voice: the calm jazz singer (sung soft, laid back, few small scoops, slow narrow late vibrato, no falls) with a
# narrower touch range still (smooth: small swings) and laid back further: at 72 BPM on long notes the duration model
# gives her ~120 ms of consonants before each vowel (jane-street at 100: ~70), so the style's 35 ms put the syllable's
# P-centre ~24 ms AHEAD of the beat ("gerusht"); 60 ms (+20 on a phrase's first vowel) lands it on the beat
VOICE = dict(voice='hanami', style='jazz', vel=(58, 84), late_ms=60.0, late_first_ms=20.0)
BREATH_S = 0.5         # rests this long (s) start a new take: every line its own breath

# ------------------------------------------------------------------------------------------------ the tenor
# the hook as the tenor plays it, at the voice's pitch (an octave lower it sat in the upright's and the Rhodes'
# bands: masking warns in the intro)
SAX_INTRO = notes('r/1 | G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2 Bb4/8 Ab4/8 G4/4 | F4/2. r/4', length='bar')
SAX_INTER = notes('G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2 r/4 Bb4/8 C5/8 | Bb4/4. Ab4/8 G4/4 F4/4 | G4/2. r/4',
                  length='bar')
# short answers in the voice's gaps (beats of the 8-bar chorus): after "nowhere to be" and "nowhere to go"
SAX_ANSWER_C2 = notes('@6 C5/8 Bb4/8 G4/4 @14 Ab4/8 G4/8 F4/4', length=32)
SAX_ANSWER_C3 = notes('@6 C5/8 Bb4/8 G4/4 @14 C5/8 Bb4/8 Ab4/8 G4/8', length=32)
SAX_TAG = notes('@8 C5/4. Bb4/8 G4/4 F4/4 | Eb4/2 r/2', length=16)
HOOK = notes('G4/4. Ab4/8 Bb4/8 C5/4.~ | C5/2 r/2', length='bar')            # the solo's motif

ARCH = [lambda c: c.arch(bars=4, depth=0.35)]      # the pad breathes in 4-bar arches (no flat bed)
END_CHORD = hold('Eb3=50 G3=52 Bb3=54 D4=56 F4=58 C5=60', 7.6, length=8)       # Ebmaj9 (6/9 on top) under the "be"


def build() -> Song:
    s = Song('Nowhere to Be', tempo=TEMPO, key='Eb major', seed=72, tail=6)
    (intro, verse1, chorus1, inter, verse2, chorus2, solo, bridge, chorus3, tag, end) = s.form(FORM, parts=CHANGES)
    # the bossa preset as a soul-ballad band: straight feel, the salon IR (close) + plate, Meatbass upright, Swirly
    # brushes, Blonde Bop cross-stick, the MTG tenor; a warm Rhodes for the keys (both hands on one track)
    b = bands.make('bossa', s, without=('guitar', 'shaker', 'sax'), sounds={'piano': RHODES()}, lead='vocal')
    # the sound designer's levels (SOUND.md): the preset's faders are set for the bossa's accented root-fifth bass and
    # its brush 8ths; this ballad plays long two-feel notes and slow stirs
    b.bass.gain_db += BASS_TRIM
    b.piano.gain_db += KEYS_TRIM
    b.drums.gain_db += DRUM_TRIM
    b.rim.gain_db += RIM_TRIM
    kit, rim_key = b.info['kit'], b.info['rim_keys']['rim']
    pad = s.track('pad', 'sampled/soft_poly', gain_db=PAD_GAIN, pan=0.0, sends={'room': -14})
    rng = random.Random(72)
    # the tenor: the sax hero's jazz voicing (one take, no tube grit / exciter, 2:1, the presence gentle: Preset.genres)
    sax = s.track('sax', 'sampled/tenor_sax', sends={'room': -14})
    hero(sax, family='sax', genre='jazz', bed=[pad, b.piano], throws=False, echo=False)
    vmem = singer.Memory()
    hmem = hornist.Memory()

    def sing(line, words, at, take=0, **kw):
        v = singer.sing(s, line, words, at=at, seed=7, take=take, memory=vmem, split_s=BREATH_S, **{**VOICE, **kw})
        SOLO.setdefault('vocal', []).append(v)
        return v

    def comp(sec, vel, answer=None, density=0.45, intensity=0.3, seed=0, style='ballad', register=('D3', 'G4')):
        """The Rhodes under / around the voice: rootless voicings below her (D3-G4: above the upright's 60-250 Hz
        - at C3-F4 the two shared the bass band), rolled, answering her rests."""
        c = jazz.comp(sec.prog, style=style, voicing='rootless', register=register, density=density,
                      intensity=intensity, vel=vel, answer=answer, seed=seed)
        b.piano.play(c.roll((14, 30), seed=rng, bpm=TEMPO), sec)
        jazzband.pedal([b.piano], sec.prog, sec)

    def bass(sec, vel, feel='two', seed=0):
        b.bass.play(jazz.walking_bass(sec.prog, key=s.key, straight=True, feel=feel, pickups=0.25, vel=vel,
                                      gate=0.95, seed=seed), sec)

    def kit_part(sec, vel, kick='even', backbeat=(3,), seed=0, ghosts=0.0, fills=False, rim_vel=34):
        """Brush stirs (one per beat at 72), soft taps on 2 and 4, a feathered kick; the cross-stick on `backbeat`
        beats (0-based in the bar) - soft, a click, never a crack."""
        bars = int(sec.bars) if hasattr(sec, 'bars') else int(round((sec.end - sec.start) / 4))
        b.drums.play(jazzband.brushes(b, bars, style='ballad', straight=True, kick=kick, ghosts=ghosts,
                                      fills=fills, vel=vel, seed=seed), sec)
        r = random.Random(seed)
        hits = [(4.0 * bar + bb, 0.25, rim_key, int(rim_vel * (0.9 + 0.2 * r.random()) * (1.08 if bb == 3 else 1)))
                for bar in range(bars) for bb in backbeat]
        b.rim.play(Clip(hits, length=4.0 * bars), sec)

    # ============================================================== intro: the Rhodes, then the band and the hook
    comp(intro, 60, density=0.3, intensity=0.22, seed=1)
    bass(intro, 64, seed=2)
    b.bass.clear(intro.start, intro.bar(2))                    # the bass waits two bars
    b.drums.play(jazzband.brushes(b, 2, style='ballad', straight=True, kick=None, fills=False, vel=0.55, seed=3),
                 intro.bar(2))
    hornist.arrange(SAX_INTRO, TEMPO, family='sax', style='ballad', section='verse', vel=(50, 90), seed=11,
                    memory=hmem, at=intro).place(sax, intro)

    # ============================================================== verse 1 / chorus 1
    v1 = sing(VOX('verse'), LYRICS_V1, verse1)
    sing(VOX('chorus'), LYRICS_C, chorus1)
    comp(verse1, 62, answer=VOX('verse'), seed=11)
    comp(chorus1, 66, answer=VOX('chorus'), density=0.5, intensity=0.32, seed=12)
    bass(verse1, 68, seed=21)
    bass(chorus1, 72, seed=22)
    kit_part(verse1, 0.62, seed=31)
    kit_part(chorus1, 0.7, backbeat=(1, 3), seed=32, rim_vel=36)
    pad.chords(chorus1, voicing='spread', register=('Bb2', 'Bb4'), vel=46, then=ARCH)

    # ============================================================== inter: the tenor answers the hook
    comp(inter, 62, density=0.35, seed=13)
    bass(inter, 68, seed=23)
    kit_part(inter, 0.62, seed=33)
    hornist.arrange(SAX_INTER, TEMPO, family='sax', style='ballad', section='verse', vel=(58, 88), seed=12,
                    memory=hmem, at=inter).place(sax, inter)

    # ============================================================== verse 2 / chorus 2
    sing(VOX('verse2'), LYRICS_V2, verse2, take=1)
    sing(VOX('chorus'), LYRICS_C, chorus2, take=1)
    comp(verse2, 64, answer=VOX('verse2'), density=0.5, seed=14)
    comp(chorus2, 68, answer=VOX('chorus'), density=0.55, intensity=0.34, seed=15)
    bass(verse2, 70, seed=24)
    bass(chorus2, 74, seed=25)
    kit_part(verse2, 0.66, seed=34, ghosts=0.1)
    kit_part(chorus2, 0.74, backbeat=(1, 3), seed=35, ghosts=0.1, rim_vel=38)
    pad.chords(chorus2, voicing='spread', register=('Bb2', 'Bb4'), vel=48, then=ARCH)
    hornist.arrange(SAX_ANSWER_C2, TEMPO, family='sax', style='ballad', section='verse', vel=(52, 74), seed=13,
                    memory=hmem, at=chorus2).place(sax, chorus2)

    # ============================================================== solo: the tenor's ballad
    # the tenor's middle (G3-D5: warm, never squealing), no shakes / growls (smooth: the climax is a long note)
    vocab = hornist.vocabulary('sax', style='ballad', register=('G3', 'D5'), vel=(58, 100),
                               weights={'shake': 0.0, 'growl': 0.0, 'run': 0.4, 'motif': 0.6, 'answer': 1.4,
                                        'long_tone': 1.4, 'fall_off': 0.3})
    bud = soloist.Budget(spice_every=3, fast_every=16, same_every=32)
    SOLO['perf'] = soloist.solo(s, sax, vocab, at=solo, prog=solo.prog, motif=HOOK, arc='ballad', budget=bud,
                                seed=17)
    comp(solo, 58, density=0.42, intensity=0.3, seed=16)      # under the tenor: sparser, softer
    sv, sc = solo.parts
    bass(solo, 72, feel='push', seed=26)
    kit_part(solo, 0.72, backbeat=(1, 3), seed=36, ghosts=0.15, rim_vel=36)
    pad.chords(solo, voicing='spread', register=('Bb2', 'Bb4'), vel=40, bars={solo: (8, 16)}, then=ARCH)

    # ============================================================== bridge: the turn
    sing(VOX('bridge'), LYRICS_BR, bridge)
    comp(bridge, 68, answer=VOX('bridge'), density=0.5, intensity=0.36, seed=17)
    bass(bridge, 74, seed=27)
    kit_part(bridge, 0.74, backbeat=(1, 3), seed=37, ghosts=0.1, rim_vel=36)
    pad.chords(bridge, voicing='spread', register=('B2', 'B4'), vel=50, then=ARCH)

    # ============================================================== chorus 3: the hook with a harmony, the last line turned
    c3 = VOX('chorus3')
    sing(c3, LYRICS_C3, chorus3, take=2)
    harm = None
    for a, words in ((0, 'No-where to be,'), (16, 'stay where the light is slow,')):
        harm = sing(c3.slice(a, a + 8).transpose_scale(-2, s.key), words, chorus3.start + a, take=3,
                    track_id='vocal_harm', pan=0.25, gain_db=-8.0, formant=0.2)
    comp(chorus3, 68, answer=c3, density=0.55, intensity=0.36, seed=18)
    bass(chorus3, 74, seed=28)
    kit_part(chorus3, 0.76, backbeat=(1, 3), seed=38, ghosts=0.1, rim_vel=38)
    pad.chords(chorus3, voicing='spread', register=('Bb2', 'Bb4'), vel=50, then=ARCH)
    hornist.arrange(SAX_ANSWER_C3, TEMPO, family='sax', style='ballad', section='verse', vel=(52, 76), seed=14,
                    memory=hmem, at=chorus3).place(sax, chorus3)

    # ============================================================== tag + ending
    sing(VOX('tag'), LYRICS_TAG, tag, take=1, vel=(56, 76))
    comp(tag, 60, answer=VOX('tag'), density=0.35, intensity=0.24, seed=19)
    bass(tag, 66, seed=29)
    kit_part(tag, 0.6, seed=39)
    hornist.arrange(SAX_TAG, TEMPO, family='sax', style='ballad', section='outro', vel=(50, 72), seed=15,
                    memory=hmem, at=tag).place(sax, tag)
    pad.play(hold('Eb3=40 Bb3=42 D4=44 G4=46', 8, length=8), end)          # the pad holds the last chord's air
    s.ending(end, chords=[(b.piano, END_CHORD, 45)], bass=(b.bass, 'Eb2', 7, 76),
             drums=(b.drums, jazz.last_stir(kit, 8, last=3)), rit=tag.bar(2), to=0.8, hold=2, length=4,
             room=(-13, -9))

    # ============================================================== production
    # the voice: the vocal hero, clean (no tube) and dry (the library's jazz space: its short plate ~20 LU under it,
    # no echo, no throws, not in the band's room); the Rhodes and the pad give her the words' band
    hero(v1.track, family='vocal', genre='jazz', bed=[pad], competitors=[b.piano], drive=False)
    hero(harm.track, family='vocal', genre='jazz', drive=False, ride=False, duck=False, carve=False, dips=False)
    sax.feature(solo, db=1.0)      # A&R: at +2 the solo's peak topped the last chorus

    # the arc: soft intro and verses, the choruses a little fuller, the bridge and the last chorus the warmest
    s.arc({'intro': -3.0, 'verse1': -2.5, 'chorus1': -0.5, 'inter': -2.0, 'verse2': -2.0, 'chorus2': 0.0,
           'solo': -0.5, 'bridge': 0.5, 'chorus3': 1.2, 'tag': -1.5, 'end': -2.5},
          within={'solo': [(31.5, -0.5), (32, 0.3, 'smooth'), (56, 0.3), (63.5, 0.0, 'smooth')]})

    # ============================================================== master (MASTER.md): platform dynamic, the jazz tone
    # (the mids -2.2 dB at 630 Hz: her low register and the tenor), no low-shelf lift (the plan's +1 dB at 60 Hz: the
    # sub already reads +2 over the profile - smooth, not boomy), x1.6 width above the mono bass (the dry centred voice
    # leaves the sung sections ~8 % wide), the limiter making up the eq and a little more - not squashing the LRA
    mastering.apply(s, eq={'low.freq': 60, 'low.gain': 0.0, 'low.q': 0.7071, 'peak1.freq': 630, 'peak1.gain': -2.2,
                           'peak1.q': 1.0},
                    width=MASTER_WIDTH, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=1.0)
    return s
