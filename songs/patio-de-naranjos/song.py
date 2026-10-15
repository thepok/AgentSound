"""Patio de Naranjos - an original solo nylon-string guitar piece, Spanish-tinged and lyrical: one classical guitar
fingerpicked in a small courtyard, the tune sung on the treble strings over its own p-i-m-a arpeggios.
84 BPM, E minor -> E major (the middle section and the ending), ~3:30. Build: python -m agentsound build
songs/patio-de-naranjos

  intro   4  Em Cmaj7 Am B7 - p-i-m-a arpeggios alone, a natural harmonic on B7
  a1     16  the tune in E minor, low and quiet (ballad arpeggio under it)
  b       8  the answer in G major, the tune starting low and rising to G5; a breath into the key change
  c      16  E major: Travis picking, a dancing syncopated tune - the light middle
  bridge  4  Am G Fmaj7 B7: the Andalusian fall back to E minor, held on the dominant
  a2     16  the tune again over 16th arpeggios, louder, its last phrase climbing to the climax
  coda    6  Am B7 E: the Picardy E major, harmonics, the low E left ringing

The guitar is the whole record (the user's wish: "so ein gezupfte nylon gitarre lied"): sampled/concert_guitar
(Markus Fiedler's Natural Concert Guitar: 4 velocity layers, round robins, finger-off and fret noises), played by
guitarist.arrange(melody=...) - the chord melody: the picked pattern under the tune, the tune fretted on top.
Brief: BRIEF.md.
"""
from agentsound import *
from agentsound import guitarist as gtr, patches
from agentsound.humanize import touch as _touch
from agentsound.patches.sampled_guitars import CONCERT, LEVELS

PAN = [[40, -0.5], [60, -0.12], [72, 0.2], [84, 0.3], [103, 0.3]]   # E2 left .. the treble right (the pair)

ANALYSIS = {'profile': 'classical'}      # a solo classical instrument in a hall: dynamics first, -23..-16 LUFS
METADATA = {'title': 'Patio de Naranjos', 'artist': 'AgentSound', 'album': 'Cuerdas de Nylon',
            'genre': 'Classical Guitar', 'year': 2026,
            'comment': 'Nylon guitar: Natural Concert Guitar by Markus Fiedler (fiedler-audio.de)'}
COVER = {'style': 'jazz', 'palette': ['#2e1f14', '#e39b3a'], 'title': 'patio de naranjos',
         'subtitle': 'AgentSound - Cuerdas de Nylon', 'seed': 11}

# the mix engineer (MIX.md): one guitar carries the tune and its own accompaniment - it is the lead everywhere;
# the boxy 200-400 Hz of the close-miked body (mud +4.8 dB over the classical reference) eased
MIX = {'lead': {name: 'guitar' for name in ('a1', 'b', 'c', 'bridge', 'a2', 'coda')},
       'eq': {'guitar': [{'freq': 300.0, 'gain': -2.5, 'q': 1.0}]}}

TEMPO = 84
SEED = 11

# ------------------------------------------------------------------------------------------------ form + harmony
A = 'Em Em Am Am D D G B7 Em Em Am Am C B7 Em Em'
FORM = [
    ('intro', 4, 'Em Cmaj7 Am B7', 'E minor'),
    ('a1', 16, A, 'E minor'),
    ('b', 8, 'C D G Em Am D G B7', 'G major'),
    ('c', 16, 'E E A A B7 B7 E E C#m G#m A E F#m B7 E E', 'E major'),
    ('bridge', 4, 'Am G Fmaj7 B7', 'E minor'),
    ('a2', 16, A, 'E minor'),
    ('coda', 6, 'Am B7 E E E E', 'E major'),
]

# ------------------------------------------------------------------------------------------------ the tune
# The concert guitar's real samples end at G5 (above it the keys are flageolets): the tune lives in E4-G5 on the
# B and E strings, the hook (rest, B4-E5 up to the held G5, stepping down) opens every A phrase.
HOOK = 'r/4 B4/8 E5/8 G5/4 F#5/8 E5/8'
A1_MEL = (f'{HOOK} | F#5/4 E5/8 D#5/8 E5/2 | '                         # Em Em
          'r/8 A4/8 C5/8 E5/8 E5/4 D5/8 C5/8 | B4/4 C5/8 B4/8 A4/2 | '    # Am Am
          'r/8 F#4/8 A4/8 D5/8 F#5/4. E5/8 | D5/4 C5/8 D5/8 A4/2 | '      # D D
          'r/8 G4/8 B4/8 D5/8 G5/4. F#5/8 | F#5/4 D#5/8 E5/8 F#5/4 B4/4 | '  # G B7
          f'{HOOK} | F#5/8 G5/8 F#5/8 E5/8 E5/2 | '                      # Em Em (the neighbour on top)
          'r/8 C5/8 E5/8 G5/8 F#5/4 E5/4 | D5/8 E5/8 C5/4 A4/2 | '        # Am Am
          'r/8 E4/8 G4/8 C5/8 E5/4. D5/8 | C5/4 B4/8 A4/8 B4/4 D#5/4 | '   # C B7
          'E5/2. r/4 | r/1')                                           # Em Em (the guitar breathes)
# a2: the same tune, its last phrase climbing to the climax on G5 and resolving
A2_MEL = (f'{HOOK} | F#5/4 E5/8 D#5/8 E5/2 | '
          'r/8 A4/8 C5/8 E5/8 E5/4 D5/8 C5/8 | B4/4 C5/8 B4/8 A4/2 | '
          'r/8 F#4/8 A4/8 D5/8 F#5/4. E5/8 | D5/4 C5/8 D5/8 A4/2 | '
          'r/8 G4/8 B4/8 D5/8 G5/4. F#5/8 | F#5/4 D#5/8 E5/8 F#5/4 B4/4 | '
          f'{HOOK} | F#5/8 G5/8 F#5/8 E5/8 E5/2 | '
          'r/8 C5/8 E5/8 G5/8 F#5/4 E5/4 | D5/8 E5/8 C5/4 A4/2 | '
          'r/8 E5/8 G5/8 E5/8 G5/4. F#5/8 | F#5/4 E5/8 D#5/8 F#5/4 B4/4 | '  # C B7: the climax
          'E5/1 | r/1')
# b (G major): starts low, longer notes, rises to G5 and hands back to B7
B_MEL = ('G4/4. A4/8 B4/4 C5/4 | D5/2 C5/8 B4/8 A4/4 | '                # C D
         'B4/4. C5/8 D5/4 G5/4 | F#5/8 E5/8 D5/8 E5/8 B4/2 | '            # G Em
         'C5/4. D5/8 E5/4 C5/4 | D5/8 E5/8 F#5/8 E5/8 D5/4 A4/4 | '       # Am D
         'B4/4 D5/4 G5/4. F#5/8 | F#5/2 D#5/4 B4/4')                      # G B7
# c (E major): Travis underneath, a syncopated dancing tune (kept under G#5: the flageolet keys)
C_MEL = ('B4/8 E5/8 r/8 E5/8 D#5/8 E5/8 F#5/4 | E5/8 B4/8 G#4/4 B4/2 | '   # E E
         'C#5/8 E5/8 r/8 E5/8 F#5/8 E5/8 C#5/4 | B4/8 C#5/8 A4/2. | '       # A A
         'r/8 B4/8 D#5/8 F#5/8 F#5/4 E5/8 D#5/8 | C#5/8 D#5/8 E5/8 F#5/8 B4/2 | '  # B7 B7
         'B4/8 E5/8 r/8 E5/8 D#5/8 E5/8 F#5/4 | E5/8 B4/8 G#4/4 E4/2 | '     # E E
         'r/8 G#4/8 C#5/8 E5/8 E5/4 D#5/4 | D#5/4 B4/8 D#5/8 F#5/4 D#5/4 | '  # C#m G#m
         'E5/4. C#5/8 E5/8 F#5/8 E5/4 | E5/8 D#5/8 B4/4 G#4/2 | '           # A E
         'A4/8 C#5/8 F#5/4 E5/8 C#5/8 A4/4 | B4/8 D#5/8 F#5/4 F#5/8 E5/8 D#5/4 | '  # F#m B7
         'E5/1 | r/2 B4/8 C#5/8 D#5/4')                                     # E E (the pickup into the bridge)
# bridge: the Andalusian fall, the tune stepping down with it, then up into a2
BR_MEL = 'E5/2 D5/8 C5/8 B4/4 | D5/2 C5/8 B4/8 A4/4 | C5/2 B4/8 A4/8 G4/4 | F#4/8 A4/8 B4/8 D#5/8 F#5/2'
# coda: Am B7 E - the last statement of the hook's fall, the E major chord, harmonics over it
CODA_MEL = 'C5/4 B4/8 A4/8 E5/2 | D#5/4 E5/8 F#5/8 B4/2 | G#4/4 B4/4 E5/2 | r/1 | r/1 | r/1'

# section -> (technique, pattern, energy, accompaniment velocities, the tune's touch range)
PLAY = {
    'intro':  ('arpeggio', 'arp_pima', 0.35, (42, 70), None),
    'a1':     ('arpeggio', 'arp_ballad', 0.40, (32, 56), (64, 102)),
    'b':      ('arpeggio', 'arp_pima', 0.50, (34, 60), (68, 106)),
    'c':      ('travis', None, 0.60, (36, 62), (72, 110)),
    'bridge': ('arpeggio', 'arp_up', 0.55, (38, 66), (70, 110)),
    'a2':     ('arp16', 'arp16', 0.80, (38, 68), (78, 120)),
    'coda':   ('arpeggio', 'arp_ballad', 0.35, (38, 64), (62, 100)),
}
MELODY = {'a1': A1_MEL, 'b': B_MEL, 'c': C_MEL, 'bridge': BR_MEL, 'a2': A2_MEL, 'coda': CODA_MEL}


def nylon():
    """sampled/concert_guitar heard by a stereo pair at the 12th fret (SOUND.md): the bass strings a little left,
    the treble right - the patch's samples are mono, so the picking sweeps across the image as on a record."""
    p = patches.get('sampled/concert_guitar').copy()
    p.instrument = inst.sfz_multi({'open': {'path': CONCERT, 'keypan': PAN}}, lazy=True,
                                  level=LEVELS['concert_guitar'])
    return p


def TONE():
    """The guitar's own chain after the patch's: the thumb's boom on E2 / A2 eased, a touch of 1.1 kHz (the tune's
    voice), the close mic's 3.5 kHz edge, string zing and air rounded off (nylon is warm), then the pair opened up
    (lows mono)."""
    return [fx.eq({'low.freq': 110, 'low.gain': -1.5, 'low.q': 0.7071,
                   'peak1.freq': 1100, 'peak1.gain': 1.0, 'peak1.q': 1.0,
                   'peak2.freq': 3500, 'peak2.gain': -2.0, 'peak2.q': 1.0,
                   'high.freq': 7000, 'high.gain': -3.5, 'high.q': 0.7071,
                   'lp.freq': 15000, 'lp.slope': 12}, name='tone'),
            fx.width(width=2.0, monobass=150)]


def build() -> Song:
    s = Song('Patio de Naranjos', tempo=TEMPO, key='E minor', seed=SEED, tail=7)
    secs = [s.section(name, bars=bars, prog=s.prog(pr)) for name, bars, pr, _ in FORM]
    S = {x.name: x for x in secs}
    KEY = {name: k for name, _, _, k in FORM}

    # ------------------------------------------------------------------------------------- time: a breathing hand
    for sec in secs:                       # every 8-bar phrase (4 in the short ones) leans in and broadens
        n = int(sec.bars)
        step = 8 if n >= 8 else n
        for b0 in range(0, n, step):
            s.rubato((sec.bar(b0), sec.bar(min(n, b0 + step))), depth=0.03, phrase='breath',
                     seed=SEED + b0)
    s.ritardando((S['b'].bar(7), S['b'].end), to=0.86)                    # the breath into E major
    s.ritardando((S['bridge'].bar(3), S['bridge'].end), to=0.82)          # held on the dominant ...
    s.fermata(S['bridge'].beat(-1), hold=1.0)                            # ... before the tune returns
    s.ritardando((S['coda'].bar(1), S['coda'].bar(3)), to=0.78, a_tempo=False)
    s.fermata(S['coda'].bar(2), hold=2.0)

    # ------------------------------------------------------------------------------------- space
    # a small courtyard: a short wooden room close around the guitar, the warm Musikverein hall far behind it
    room = s.bus('room', patches.get('bus/ir_room_small'))
    hall = s.bus('hall', patches.get('bus/ir_concert_hall'))

    # ------------------------------------------------------------------------------------- the guitar
    guitar = s.track('guitar', nylon(), gain_db=-4.0, pan=-0.06, sends={room: -13, hall: -13}, fx=TONE())
    guitar.humanize(body='calm')

    mem = gtr.Memory()
    for i, sec in enumerate(secs):
        tech, pat, energy, vel, touch = PLAY[sec.name]
        nxt = secs[i + 1] if i + 1 < len(secs) else None
        mel = None
        if sec.name in MELODY:
            mel = _touch(notes(MELODY[sec.name]), *touch)
        prog = s.prog('Am B7 E E') if sec.name == 'coda' else sec.prog      # the coda's last 2 bars: one rolled chord
        arr = gtr.arrange(prog, bpm=TEMPO, key=KEY[sec.name], style='fingerstyle', technique=tech,
                          pattern=pat, energy=energy, vel=vel, section=sec, sound=guitar, memory=mem,
                          length=16 if sec.name == 'coda' else None,
                          seed=SEED + i, into=nxt, section_end=nxt is not None, hand='fingerstyle', melody=mel,
                          slur=0.1)
        arr.play(guitar, sec)

    # the end: the E major chord rolled slowly from the low E up and left to ring, the bell harmonics over it
    guitar.play(gtr.let_ring('E', 8.0, TEMPO, ms=95, vel=76, seed=SEED), S['coda'].bar(4))
    # natural harmonics: the B7 of the intro, the bells over the last E major
    guitar.play(gtr.harmonic('B5', 2.0, TEMPO, vel=70), (S['intro'].bar(3), 2.0))
    guitar.play(gtr.harmonic('B5', 3.0, TEMPO, vel=64), (S['coda'].bar(3), 2.0))
    guitar.play(gtr.harmonic('E6', 6.0, TEMPO, vel=72), (S['coda'].bar(4), 2.0))

    # the last chord rings into the courtyard: the hall send opens over the coda's E major
    guitar.automate('send.hall', hold(0, S['coda'].bar(2), -13), ramp(S['coda'].bar(2), S['coda'].end, -13, 0))

    # the arc (the players carry it: a1 -21.6 .. a2 -17.4 LUFS): the E major middle eased, the coda lifted a little
    s.arc({'intro': 0.0, 'a1': 0.0, 'b': 0.0, 'c': -0.5, 'bridge': 0.0, 'a2': 0.0, 'coda': 2.0})

    s.master.add(fx.width(width=1.2, monobass=120))
    s.master.add(fx.limiter(gain=6.0, release=250, ceiling=-1.3))
    return s
