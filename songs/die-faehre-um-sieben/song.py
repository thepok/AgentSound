"""Die Fähre um sieben - an original German Liedermacher ballad in the manner of the early-70s singer-songwriter
records (a young woman with her acoustic guitar, close-miked, a story told in two verses, a chorus, a bridge).
84 BPM, A minor verses / C major chorus, ~3:15. Build: python -m agentsound build songs/die-faehre-um-sieben

The story (LYRICS.md): she runs the kiosk at the ferry landing; every evening a man with a suitcase buys a ticket for
the seven o'clock ferry and never boards. One evening his place is empty, his folded ticket lies in her tip jar - she
leaves the kiosk open and takes the ferry herself. Brief: BRIEF.md, form: ARRANGEMENT.md, sounds: SOUND.md.

  intro    4   the guitar alone: arpeggios + the verse tune as a melody (an overdubbed second guitar)
  verse1   8   voice + fingerpicked guitar (Travis)
  chorus1  8   the guitar strums with chucks on 2 and 4 - "Die Fähre geht um sieben"
  verse2   8   the upright bass enters, Travis again
  chorus2  8   strum + chucks, bass
  break    8   the instrumental: the second guitar sings the verse tune an octave up over the picking
  bridge   8   arpeggios, the strings creep in under "und plötzlich bin ich die, die geht"
  chorus3  8   strum + chucks, bass, brushes, the string pad; "sieben" lifted to C5, "wer gehen will - ich kann"
  tag      4   "die Fähre geht um sieben" once more, the guitar answers with the hook
  outro    2   the A minor chord left ringing
"""
from agentsound import *
from agentsound import bassist, drummer, guitarist as gtr, lyrics, mastering, patches, singer

ANALYSIS = {'profile': 'jazz'}          # an acoustic record in a small room (-16..-13 LUFS), dynamics first
METADATA = {'title': 'Die Fähre um sieben', 'artist': 'AgentSound', 'album': 'Lieder vom Ufer',
            'genre': 'Liedermacher', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#3b2a1e', '#d98c3f'], 'title': 'die fähre um sieben',
         'subtitle': 'AgentSound - Lieder vom Ufer', 'seed': 7}

# the mix engineer's moves (MIX.md)
MIX = {
    # the voice INSIDE the record, not on top of it (HUMAN_FEEDBACK: start ~3 dB under the lead target): it read
    # +8.7 dB over the picked guitar in verse 1; the intimate tag line lifted back over the arpeggios
    'trim': {'vocal': -3.5, 'guitar': 1.5},
    'ride': {'vocal': {'tag': 6.0}, 'gtr_melody': {'break': 3.0},
             # the picking steps back under the second guitar's tune (they shared the low mids)
             'guitar': {'intro': -5.0, 'break': -2.5, 'chorus1': -1.5, 'chorus2': -2.0, 'chorus3': -2.0},
             # the upright digs in in the choruses: back into its window (3-6.5 dB under the voice)
             'bass': {'chorus2': -3.0, 'chorus3': -2.5},
             # the strings: a whisper in the bridge and the tag, present (but under her) in the last chorus
             'strings': {'bridge': -2.5, 'chorus3': 4.5, 'tag': -2.5}},
    # the guitar out of the voice's low-mid and presence (masking findings), the low-register voice's proximity
    'eq': {'guitar': [{'freq': 450.0, 'gain': -1.5, 'q': 1.0}, {'freq': 3300.0, 'gain': -1.5, 'q': 1.0}],
           'vocal': [{'freq': 280.0, 'gain': -2.0, 'q': 1.0}, {'freq': 150.0, 'gain': -3.0, 'q': 0.8}]},
}

TEMPO = 84
SEED = 7

# ------------------------------------------------------------------------------------------------ harmony
VERSE = 'Am Em/G Fmaj7 C/E Dm7 Am/C Bm7b5 E7'
CHORUS = 'F G C Am7 F G C C:0.5 E7:0.5'          # back to A minor (E7 -> F is the deceptive step into the chorus)
CHORUS_LAST = 'F G C Am7 F G C C'
BRIDGE = 'Fmaj7 G Em7 Am7 Dm7 Em7 Fmaj7 E7sus4:0.5 E7:0.5'
INTRO = 'Am Em/G Fmaj7 E7'
TAG = 'F G Am Am'
OUTRO = 'Am Am'

# ------------------------------------------------------------------------------------------------ the voice
# Iambic 8-syllable verse lines (da-DUM x4): a pickup 8th, the 4th syllable long on beat 3, the 8th long on beat 2.
# Low and calm (A3-A4: the singer's lower middle - HUMAN_FEEDBACK: calm vocals sit low, move stepwise, few syllables).
V_MEL = ('r/8 A3/8 C4/8 D4/8 E4/4. D4/8 | D4/8 C4/8 B3/2. | '        # Mein Ki-osk steht am | Lan-dungs-steg
         'r/8 A3/8 C4/8 D4/8 E4/4. D4/8 | C4/8 D4/8 E4/2. | '        # da riecht's nach Teer und | Schwarz-kaf-fee
         'r/8 D4/8 F4/8 F4/8 A4/4. G4/8 | F4/8 D4/8 E4/2. | '        # und je-den A-bend | steht ein Mann
         'r/8 D4/8 D4/8 D4/8 F4/4. E4/8 | D4/8 C4/8 B3/2.')          # mit sei-nem Kof-fer | still am See
# The chorus: the hook "Die Fäh-re geht um sie-ben" (a leap to the 3rd of F, the long "sie" on the 3rd of G).
C_MEL = ('r/8 C4/8 A4/4. G4/8 F4/8 G4/8 | B4/2. A4/8 r/8 | '          # Die Fäh-re geht um | sie-ben
         'r/8 E4/8 G4/4. E4/8 G4/8 A4/8 | G4/2. r/4 | '               # das Was-ser hält nicht | an
         'r/8 C4/8 A4/4. G4/8 F4/8 G4/8 | B4/2. A4/8 r/8 | '          # Wer blei-ben will, muss | blei-ben
         'r/8 E4/8 G4/4. E4/8 F4/8 D4/8 | C4/2 r/2')                  # wer ge-hen will, der | kann
C_MEL_LAST = ('r/8 C4/8 A4/4. G4/8 F4/8 G4/8 | C5/2. B4/8 r/8 | '     # "sie" lifted to C5 (sus4 -> 3rd)
              'r/8 E4/8 G4/4. E4/8 G4/8 A4/8 | G4/2. r/4 | '
              'r/8 C4/8 A4/4. G4/8 F4/8 G4/8 | B4/2. A4/8 r/8 | '
              'r/8 E4/8 A4/4. G4/8 E4/8 D4/8 | E4/2. r/4')            # wer ge-hen will - ich | kann (on the 3rd)
B_MEL = ('r/8 C4/8 F4/8 G4/8 A4/4. G4/8 | F4/8 E4/8 D4/2. | '         # Heut bleibt der Platz am | U-fer leer
         'r/8 B3/8 E4/8 G4/8 B4/4. A4/8 | G4/8 F4/8 E4/2. | '         # sein Fahr-schein liegt bei | mir im Glas
         'r/8 D4/8 F4/8 A4/8 A4/4. G4/8 | G4/8 E4/8 G4/2. | '         # Ich lass den La-den | of-fen stehn
         'r/8 E4/8 G4/8 A4/8 A4/8 G4/8 E4/4 | r/8 G4/8 B4/2.')        # und plötz-lich bin ich die, | die geht
T_MEL = 'r/8 C4/8 A4/4. G4/8 F4/8 G4/8 | B4/2. A4/8 r/8 | r/1 | r/1'

LYRICS = {
    'verse1': "Mein Ki-osk steht am Lan-dungs-steg, da riecht's nach Teer und Schwarz-kaf-fee. "
              "Und je-den A-bend steht ein Mann mit sei-nem Kof-fer still am See.",
    'verse2': "Er löst den Fahr-schein, Tag für Tag, und fal-tet ihn ganz klein und schmal. "
              "Das Schiff legt ab, er bleibt zu-rück und winkt ihm nach wie je-des Mal.",
    'chorus': "*Die Fäh-re geht um sie-ben,* das Was-ser hält nicht an. "
              "Wer blei-ben will, muss blei-ben, wer ge-hen will, der kann.",
    'chorus3': "*Die Fäh-re geht um sie-ben,* das Was-ser hält nicht an. "
               "Wer blei-ben will, soll blei-ben, wer ge-hen will, *ich kann.*",
    'bridge': "Heut bleibt der Platz am U-fer leer, sein Fahr-schein liegt bei mir im Glas. "
              "Ich lass den La-den of-fen stehn, und plötz-lich bin ich die, die geht.",
    'tag': "(( Die Fäh-re geht um sie-ben. ))",
}

# German, in the voicebank's German symbols (lyrics.DE_VOWELS / DE_CONSONANTS): the glottal stop q only where a
# singer sets one (a stressed or line-initial vowel), unstressed function words glide on; -er as the off-glide ex.
LEX = {
    'mein': 'm ay n', 'kiosk': "k 'iy ao s k", 'steht': 'sh t ee t', 'am': 'a m',
    'landungssteg': "l1 'a n d uh ng s sh t ee k", 'da': 'd a', "riecht's": 'rh iy cc t s', 'nach': 'n a x',
    'teer': 't ee ex', 'und': 'uh n t', 'schwarzkaffee': "sh v 'a ex ts k a f ee", 'jeden': "y 'ee d ax n",
    'abend': "q 'a b ax n t", 'ein': 'ay n', 'mann': 'm a n', 'mit': 'm ih t', 'seinem': "z 'ay n ax m",
    'koffer': "k 'ao f ex", 'still': 'sh t ih l1', 'see': 'z ee',
    'er': 'q ee ex', 'löst': 'l1 eu1 s t', 'den': 'd ee n', 'fahrschein': "f 'a ex sh ay n", 'tag': 't a k',
    'für': 'f v1 ex', 'faltet': "f 'a l1 t ax t", 'ihn': 'iy n', 'ganz': 'g a n ts', 'klein': 'k l1 ay n',
    'schmal': 'sh m a l1', 'das': 'd a s', 'schiff': 'sh ih f', 'legt': 'l1 ee k t', 'ab': 'q a p',
    'bleibt': 'b l1 ay p t', 'zurück': "ts uh rh 'yy k", 'winkt': 'v ih ng k t', 'ihm': 'iy m', 'wie': 'v iy',
    'jedes': "y 'ee d ax s", 'mal': 'm a l1',
    'die': 'd iy', 'fähre': "f 'eh rh ax", 'geht': 'g ee t', 'um': 'uh m', 'sieben': "z 'iy b ax n",
    'wasser': "v 'a s ex", 'hält': 'hh eh l1 t', 'nicht': 'n ih cc t', 'an': 'q a n', 'wer': 'v ee ex',
    'bleiben': "b l1 'ay b ax n", 'will': 'v ih l1', 'muss': 'm uh s', 'soll': 'z ao l1',
    'gehen': "g 'ee ax n", 'der': 'd ee ex', 'kann': 'k a n', 'ich': 'q ih cc',
    'heut': 'hh oy t', 'platz': 'p l1 a ts', 'ufer': "q 'u1 f ex", 'leer': 'l1 ee ex', 'sein': 'z ay n',
    'liegt': 'l1 iy k t', 'bei': 'b ay', 'mir': 'm iy ex', 'im': 'ih m', 'glas': 'g l1 a s',
    'lass': 'l1 a s', 'laden': "l1 'a d ax n", 'offen': "q 'ao f ax n", 'stehn': 'sh t ee n',
    'plötzlich': "p l1 'oe ts l1 ih cc", 'bin': 'b ih n',
}

VOICE = dict(voice='hanami', style='ballad', vel=(54, 86), split_s=0.3)   # a breath in every 8th rest

# ------------------------------------------------------------------------------------------------ the guitar
# The second guitar's tunes (an overdub, played by guitarist.lead: fingered, picked, slurred, finger vibrato).
G_INTRO = ('r/8 A4/8 C5/8 D5/8 E5/4. D5/8 | D5/8 C5/8 B4/2. | '
           'r/8 A4/8 C5/8 E5/8 E5/4. D5/8 | C5/8 B4/8 G#4/2.')
G_BREAK = ('E5/4. D5/8 C5/8 B4/8 A4/4 | G4/8 A4/8 B4/2. | '
           'r/8 A4/8 C5/8 E5/8 G5/4. E5/8 | D5/8 C5/8 E5/2. | '
           'r/8 D5/8 F5/8 A5/8 A5/4. G5/8 | E5/8 C5/8 E5/2. | '
           'D5/8 F5/8 D5/8 B4/8 D5/4 C5/8 B4/8 | G#4/2. r/4')
G_TAG = 'r/1 | r/1 | r/8 C5/8 A5/4. G5/8 F5/8 G5/8 | E5/2. r/4'
G_OUTRO = 'A4/1 | r/1'

FORM = [('intro', 4, INTRO), ('verse1', 8, VERSE), ('chorus1', 8, CHORUS), ('verse2', 8, VERSE),
        ('chorus2', 8, CHORUS), ('break', 8, VERSE), ('bridge', 8, BRIDGE), ('chorus3', 8, CHORUS_LAST),
        ('tag', 4, TAG), ('outro', 2, OUTRO)]

FIRST = {name: pr.split()[0].split(':')[0] for name, _, pr in FORM}

# the picking / strumming hand per section: (style, technique, hand, energy)
PLAY = {'intro': ('fingerstyle', 'let_ring', 'fingerstyle', 0.3),
        'verse1': ('fingerstyle', 'travis', 'fingerstyle', 0.4),
        'chorus1': ('songwriter', 'chuck', 'acoustic', 0.72),
        'verse2': ('fingerstyle', 'travis', 'fingerstyle', 0.45),
        'chorus2': ('songwriter', 'chuck', 'acoustic', 0.8),
        'break': ('fingerstyle', 'travis', 'fingerstyle', 0.4),
        'bridge': ('fingerstyle', 'arpeggio', 'fingerstyle', 0.5),
        'chorus3': ('songwriter', 'chuck', 'acoustic', 0.9),
        'tag': ('fingerstyle', 'arpeggio', 'fingerstyle', 0.45),
        'outro': ('fingerstyle', 'let_ring', 'fingerstyle', 0.3)}


def _breathe(clip, seed=0, depth=30.0):
    """The ballad bassist's phrase dynamics on top of its metric touch: each 4-bar phrase leans in towards its
    third bar and relaxes into the next change (+-depth/2 velocity), a short note after a held one a little lighter,
    seeded jitter - so the long notes do not all land at one level. Returns the new clip (marks kept)."""
    import math
    import random
    rng = random.Random(seed)
    held = {round(n.start + n.dur, 3) for n in clip if n.dur >= 2.0}

    def f(n):
        u = (n.start % 16.0) / 16.0                         # where in the 4-bar phrase
        arc = math.sin(math.pi / 2 * u / 0.7) if u < 0.7 else math.cos(math.pi / 2 * (u - 0.7) / 0.3)
        v = n.vel - depth * 0.5 + depth * arc + rng.uniform(-4, 4)
        if n.dur < 1.0 and any(abs(n.start - h) < 0.05 for h in held):
            v -= 6
        return n._replace(vel=int(max(38, min(114, round(v)))))
    return clip.map(f)


def build() -> Song:
    s = Song('Die Fähre um sieben', tempo=TEMPO, key='A minor', seed=SEED, tail=6)
    secs = [s.section(name, bars=bars, prog=s.prog(pr)) for name, bars, pr in FORM]
    S = {x.name: x for x in secs}

    # ------------------------------------------------------------------------------------- time
    s.ritardando((S['tag'].bar(2), S['outro'].end), to=0.78)
    s.fermata(S['outro'].bar(1), hold=2.0)

    # ------------------------------------------------------------------------------------- space
    # the studio: a small wooden room for everything, the early-70s EMT plate for the voice and the guitars
    room = s.bus('room', patches.get('bus/ir_room_small'))
    plate = s.bus('plate', 'bus/plate_80s')
    s.master.add(fx.compressor(threshold=-18, ratio=1.6, attack=30, release=300, name='glue'))
    s.master.add(fx.limiter(gain=7.0, release=200))

    # ------------------------------------------------------------------------------------- the players
    # the guitar's mic pair opened up (width: its keypan - low strings left, high right - spread wider)
    acoustic = patches.get('sampled/acoustic_guitar')
    guitar = s.track('guitar', acoustic.but(width=1.9), gain_db=-8.0, pan=-0.7,
                     sends={room: -9, plate: -17},
                     fx=[fx.eq({'low.freq': 180, 'low.gain': -2.0, 'low.q': 0.7071,
                                'peak1.freq': 320, 'peak1.gain': -1.5, 'peak1.q': 1.0}, name='tone'),
                         # a stereo pair on the guitar: the room around it opened, the lows mono
                         fx.dimension(mode=1, mix=0.35), fx.width(width=1.7, monobass=150)])
    melody = s.track('gtr_melody', acoustic.but(width=1.4), gain_db=-4.0, pan=0.4,
                     sends={room: -10, plate: -14},
                     fx=[fx.eq({'low.freq': 350, 'low.gain': -7.0, 'low.q': 0.7071})])   # the overdub sings, thin
    # the chorus double: the same strumming played again (another take), the 70s overdub panned opposite
    double = s.track('guitar2', acoustic.but(width=1.9), gain_db=-13.0, pan=0.75, sends={room: -10, plate: -18},
                     fx=[fx.eq({'low.freq': 180, 'low.gain': -6.0, 'low.q': 0.7071})])
    bass = s.track('bass', 'sampled/upright_bass', gain_db=-3.0, sends={room: -20})
    strings = s.track('strings', 'sampled/strings', gain_db=-8.0, pan=0.0, sends={room: -10, plate: -14},
                      fx=[fx.eq({'low.freq': 220, 'low.gain': -6.0, 'low.q': 0.7071})])   # leave the low end to the bass
    brushes = s.track('brushes', 'sampled/brush_kit', gain_db=-10.0, sends={room: -12})

    # once the bass is in, the guitar's thumb leaves it the bottom octave
    guitar.automate('fx.tone.low.gain', [(0, -3.5), (S['verse2'].start - 1, -3.5), (S['verse2'].start, -8.0)])

    # the rhythm guitar: one player through the whole song, one Memory (budgets, the last grip)
    gmem = gtr.Memory()
    for i, sec in enumerate(secs):
        style, tech, hand, energy = PLAY[sec.name]
        nxt = secs[i + 1] if i + 1 < len(secs) else None
        # the intro: the second guitar's tune alone for two bars, the chords ring in under its second half
        prog, at = (s.prog('Fmaj7 E7'), sec.bar(2)) if sec.name == 'intro' else (sec.prog, sec)
        arr = gtr.arrange(prog, bpm=TEMPO, key=s.key, style=style, technique=tech, hand=hand, energy=energy,
                          section=sec.name if sec.name == 'intro' else sec, sound=guitar, memory=gmem, seed=SEED + i, into=nxt,
                          section_end=nxt is not None, at=at)
        arr.play(guitar, at)
        if tech == 'chuck':
            arr.take(2).play(double, sec)

    # the second guitar: the intro tune, the instrumental break, the tag's answer, the last note
    lmem = gtr.Memory()
    for name, line, energy in (('intro', G_INTRO, 0.4), ('break', G_BREAK, 0.55), ('tag', G_TAG, 0.5),
                               ('outro', G_OUTRO, 0.3)):
        sec = S[name]
        ld = gtr.lead(notes(line), sec.prog, bpm=TEMPO, key=s.key, style='ballad', section=name, energy=energy,
                      sound=melody, memory=lmem, at=sec, seed=SEED)
        ld.play(melody, sec)

    # the bass from verse 2 on: a soft hollowbody, whole and half notes, passing tones into the changes
    bmem = bassist.Memory()
    parts = {'verse2': 'verse', 'chorus2': 'chorus', 'break': 'break', 'bridge': 'bridge', 'chorus3': 'chorus',
             'tag': 'outro', 'outro': 'outro'}
    order = list(parts)
    for i, name in enumerate(order):
        sec = S[name]
        last = i + 1 == len(order)
        line = bassist.arrange(sec.prog, bpm=TEMPO, key=s.key, style='ballad', part=parts[name], seed=SEED + i,
                               memory=bmem, at=sec, low='E1', section_end=not last,
                               into=None if last else FIRST[order[i + 1]],
                               ending='ring' if last else None)
        line.clip = _breathe(line.clip, seed=SEED + i)
        line.place(bass, sec)

    # the strings: a discreet pad from the bridge's last half through the last chorus and the tag
    strings.chords(S['bridge'], voicing='spread', register=('A2', 'E4'), bars=(4, 8),
                   vel=40, crescendo=(34, 56))
    strings.chords(S['chorus3'], voicing='spread', register=('C3', 'G4'), vel=60)
    strings.chords(S['tag'], voicing='spread', register=('C3', 'G4'), vel=40, crescendo=(44, 28))

    # brushes in the last chorus and the tag only: soft, behind everything
    perf = drummer.arrange([S['chorus3'], S['tag']], bpm=TEMPO, style='jazz', density=0.35, seed=SEED,
                           kit=brushes, ending='groove')
    perf.play(brushes)

    # ------------------------------------------------------------------------------------- the voice
    vmem = singer.Memory()

    def sing(name, mel, text):
        return singer.sing(s, notes(mel), lyrics.spell(text, LEX), at=S[name], seed=SEED, memory=vmem, **VOICE)

    v = sing('verse1', V_MEL, LYRICS['verse1'])
    sing('chorus1', C_MEL, LYRICS['chorus'])
    sing('verse2', V_MEL, LYRICS['verse2'])
    sing('chorus2', C_MEL, LYRICS['chorus'])
    sing('bridge', B_MEL, LYRICS['bridge'])
    sing('chorus3', C_MEL_LAST, LYRICS['chorus3'])
    sing('tag', T_MEL, LYRICS['tag'])
    hero(v.track, family='vocal', genre='jazz', bed=[strings], competitors=[guitar, double], drive=False)
    # her low notes (A3-E4) and the guitar's body share 150-300 Hz: the guitar steps aside there while she sings
    s.carve(guitar, key=v.track, freq=220.0, q=0.9, depth=4.5)

    # the arc: the first verse intimate, each chorus a step up, the break and the bridge breathing back, the last
    # chorus the top, the tag and the ringing end soft again
    s.arc({'intro': 1.0, 'verse1': -2.0, 'chorus1': -0.5, 'verse2': -1.5, 'chorus2': 0.0, 'break': 0.5,
           'bridge': -1.0, 'chorus3': 1.0, 'tag': -2.0, 'outro': 1.5})

    # ------------------------------------------------------------------------------------- master (MASTER.md)
    # platform 'dynamic' against the jazz profile: a touch of body at 160 Hz, the boxy 630 Hz down, the stereo
    # image opened to the profile's range (the voice and the picking are centred and close), -14.5 LUFS
    mastering.apply(s, eq={'peak1.freq': 160, 'peak1.gain': 1.3, 'peak1.q': 1.0, 'peak2.freq': 630,
                           'peak2.gain': -2.2, 'peak2.q': 1.0},
                    width=1.25, limiter={'ceiling': -1.2, 'release': 250.0}, loudness_change=+1.2)
    return s
