"""Kingsway After Rain - an ORIGINAL late-70s soft-rock instrumental in the spirit of the sax-anthem records of that
era ("Baker Street" as the STYLE model only: every note here is our own - riff, melodies, changes, solo). 114 BPM,
straight 8ths, E major with a mixolydian / bluesy colour (D/E, the C - D - E bVI-bVII-I lift, a G6, the blue G
crushed into G#).

The idea: ONE alto-sax riff that the song returns to between the sections - a blues-scale climb B-D-E-G that grinds
the blue third G up into a long held G#5 (the top of the horn), a quick turn down, then an answer that falls an octave
onto a sighing low G#4; over C - D it rises to a held G5 / F#5 and climbs back into the grind. The riff is the hook:
it opens the band, comes back after every chorus, is traded with the guitar in the outro.

Form (bars, 4/4 at 114)
  intro    8  lush synth pad + strings alone (Emaj9 D/E Cmaj9 Dadd9 ...), a rising string top line, a tom pickup
  riff1   16  the sax riff with the full band (riff A, then riff B: the second half answered differently)
  verse1  16  the melody on a warm stage Rhodes (played by the pianist: harmonized, decorated), acoustic strum,
              piano, fingered bass, light kit
  chorus1 10  Amaj7 B/A G#m7 C#m7 F#m7 ...: the Rhodes up high, strings swelling, the kit opens, into G - A/B
  riff2   16  the riff again (the guitar answers in its held bars)
  verse2  16  the second verse, its second half climbing higher
  chorus2 10
  riff3    8  the riff once, the biggest
  bridge   8  Cmaj7 D6 Bm7 E7sus4 (mixolydian v): pad, strings, rolled piano, the guitar swelling in
  gsolo   16  the overdriven hero guitar over the riff changes
  outro   24  the riff with guitar answers, then sax and guitar trade two bars each, riff B into a long fade

Signature moves (the moments that recur / pay off): (1) THE UNISON BREAK - sax, lead guitar and bass in octaves
with the kit on every note, a blues-scale tumble in the last bar of each chorus and of the guitar solo (1:43, 3:12,
4:19); (2) THE STOP - riff3 opens with one band hit, then the sax grinds into its G#5 alone over two bars of air, a
tom pickup, the band slams back (3:14-3:18); (3) THE TRADE - in the outro sax and guitar answer each other two bars
at a time (4:38-4:55) before riff B fades.

Why the Rhodes carries the verses: the user loved the cover's instrument version where a pianist-played Rhodes took
the sung line; it is warm and round (no beep), and keeping the sax out of the verses makes every riff an event.

Mix lessons from the cover (recipes/HUMAN_FEEDBACK.md, covers/baker-street MIX): bass well down, drums -2 dB, the bed
(strings / pad) more present and wider - but without the negative correlation the cover's first widening caused (a
moderate width on the bed, the master width kept small) - and everything ducking under the sax (and, gentler, the bed
under the Rhodes melody): a sidechain, not effects.
"""
from agentsound import *
from agentsound import bands, bassist, drummer, hornist, pianist
from agentsound import guitarist as gt
from agentsound.bandlib.pop import epiano
from agentsound.humanize import touch

ANALYSIS = {'profile': 'pop', 'loudness': [-12.5, -9]}     # a 70s record: dynamics over a radio-loud master
TEMPO = 114
MIX = {
    # the cover's lessons (bass well down, the bed up) + the mixer's pass: the bed present in the verses, the drums
    # lifted in the choruses, the hero sax 1.5 dB less hot with a small presence dip (it carried 64 % of 2-5 kHz)
    'trim': {'bass': -5.0, 'strings': 5.5, 'pad': 4.5, 'acoustic_l': -1.5, 'acoustic_r': -4.0, 'sax': -1.5,
             'guitar': -1.5},
    'ride': {'drums': {'chorus1': 2.5, 'chorus2': 2.5, 'gsolo': 2.0},
             'strings': {'verse1': 5.5, 'verse2': 5.0, 'chorus1': -1.0, 'chorus2': -1.5},
             'pad': {'verse1': 5.5, 'verse2': 5.0, 'chorus1': -1.0, 'chorus2': -1.5}},
    'duck': [{'targets': ['bass'], 'key': 'drums', 'pitches': 'kick', 'depth': 6, 'attack': 2, 'release': 120}],
    'eq': {'sax': [{'freq': 3300, 'gain': -1.5, 'q': 1.0}, {'freq': 1200, 'gain': -1.0, 'q': 1.0}],
           'rhodes': [{'freq': 1000, 'gain': -1.5, 'q': 1.0}]},
}
METADATA = {'title': 'Kingsway After Rain', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Soft Rock',
            'comment': 'Original instrumental in the late-70s soft-rock sax-anthem style.'}
COVER = {'style': 'jazz', 'palette': ['#c8873a', '#2a5585'], 'title': 'KINGSWAY AFTER RAIN', 'subtitle': 'AgentSound'}

# ------------------------------------------------------------------------------------------ harmony (concert, E)
INTRO = 'Emaj9 D/E Cmaj9 Dadd9 Emaj9 D/E Cmaj9 B7sus4'
RIFF = 'E D/E A/E E C D E B7sus4:0.5 B7:0.5'
VERSE = ('E Esus4:0.5 E:0.5 C#m7 C#m7 Amaj7 Amaj7 F#m7 B7sus4:0.5 B7:0.5 '
         'E D/E C#m7 C#m7 Amaj7 G6 F#m7 Bsus4:0.5 B:0.5')
CHORUS = 'Amaj7 B/A G#m7:0.5 C#m7:0.5 F#m7 Amaj7 B/A G#m7 C#m9 G A/B'
BRIDGE = 'Cmaj7 D6 Bm7 E7sus4 Cmaj7 D6 Bm7 B7sus4:0.5 B7:0.5'

# ------------------------------------------------------------------------------------------ the sax riff (sounding)
# riff A: the climb B-D-E-G grinding into the held G#5, the turn, the answer falling to the low sigh, the rise over C-D,
# the grind again; riff B: the same first half, a new answer over C - D, the leading tone into the tonic
GRIND = 'r:1 B4:0.5 D5:0.5 E5:0.5 G5:0.25 G#5:3.25^peak F#5:0.25 E5:0.25 D5:0.5 E5:1 | '
ANSWER = 'r:0.5 C#5:0.5 E5:0.5 C#5:0.5 B4:1 A4:0.5 B4:0.5 | G4:0.25 G#4:2.75 r:1 | '
RIFF_A = (GRIND + ANSWER + 'r:1 C5:0.5 E5:0.5 G5:1.5^peak E5:0.5 | F#5:1.5 E5:0.5 D5:0.5 B4:0.5 A4:1 | '
          'B4:0.5 D5:0.5 E5:0.5 G5:0.25 G#5:2.25^peak F#5:0.5 E5:0.5 D5:0.5 B4:0.5 E5:2 |')
RIFF_B = (GRIND + ANSWER + 'E5:0.5 G5:0.5 E5:0.5 C5:0.5 G5:2^peak | F#5:1 E5:0.5 F#5:0.5 A4:2 | '
          'r:0.5 B4:0.5 D5:0.5 E5:0.5 G5:0.25 G#5:1.75^peak | F#5:0.5 E5:0.25 D5:0.25 B4:0.5 D#5:0.5 E5:2 |')

# ------------------------------------------------------------------------------------------ the Rhodes melodies
VERSE1_MEL = ('r:0.5 G#5:0.5 G#5:0.5 F#5:0.5 E5:1 B4:1 | C#5:0.5 E5:0.5 E5:0.5 F#5:0.5 E5:2 | '
              'r:0.5 G#5:0.5 G#5:0.5 F#5:0.5 E5:0.5 C#5:1.5 | B4:0.5 C#5:0.5 E5:1 r:2 | '
              'r:0.5 A5:0.5 G#5:0.5 E5:0.5 C#5:1 E5:1 | G#5:1.5 F#5:0.5 E5:2 | '
              'r:0.5 F#5:0.5 F#5:0.5 E5:0.5 C#5:0.5 A4:1.5 | B4:2 r:2 | '
              'r:0.5 B5:0.5 B5:0.5 A5:0.5 G#5:1 E5:1 | F#5:0.5 A5:0.5 A5:0.5 G#5:0.5 F#5:2 | '
              'r:0.5 G#5:0.5 G#5:0.5 F#5:0.5 E5:0.5 C#5:1.5 | E5:0.5 F#5:0.5 G#5:1 r:2 | '
              'r:0.5 A5:0.5 B5:0.5 C#6:0.5 B5:1 A5:1 | B5:1.5 G5:0.5 E5:2 | '
              'r:0.5 F#5:0.5 A5:0.5 G#5:0.5 F#5:0.5 E5:1.5 | D#5:2 r:2 |')
VERSE2_MEL = ('r:0.5 G#5:0.5 G#5:0.5 F#5:0.5 E5:1 B4:1 | C#5:0.5 E5:0.5 E5:0.5 F#5:0.5 E5:2 | '
              'r:0.5 G#5:0.5 G#5:0.5 F#5:0.5 E5:0.5 C#5:1.5 | B4:0.5 C#5:0.5 E5:1 r:2 | '
              'r:0.5 A5:0.5 G#5:0.5 E5:0.5 C#5:1 E5:1 | G#5:1.5 F#5:0.5 E5:2 | '
              'r:0.5 F#5:0.5 F#5:0.5 E5:0.5 C#5:0.5 A4:1.5 | B4:2 r:2 | '
              'r:0.5 B5:0.5 B5:0.5 A5:0.5 G#5:1 E5:1 | F#5:0.5 A5:0.5 A5:0.5 G#5:0.5 F#5:2 | '
              'r:0.5 G#5:0.5 G#5:0.5 F#5:0.5 E5:0.5 C#5:1.5 | E5:0.5 F#5:0.5 G#5:1 r:2 | '
              'r:0.5 A5:0.5 B5:0.5 C#6:0.5 E6:1 C#6:1 | B5:1.5 G5:0.5 B5:2 | '
              'r:0.5 A5:0.5 G#5:0.5 F#5:0.5 E5:0.5 F#5:1.5 | D#5:1 F#5:1 r:2 |')
CHORUS_MEL = ('r:0.5 E5:0.5 A5:0.5 B5:0.5 C#6:2 | B5:0.5 A5:0.5 B5:0.5 D#6:0.5 C#6:1 B5:1 | '
              'G#5:1.5 B5:0.5 G#5:1 E5:1 | F#5:3 r:1 | '
              'r:0.5 E5:0.5 A5:0.5 B5:0.5 C#6:1.5 E6:0.5 | D#6:1 C#6:0.5 B5:0.5 A5:1 B5:1 | '
              'G#5:2 B5:1 C#6:1 | E6:3 r:1 | '
              'r:0.5 D6:0.5 B5:0.5 G5:0.5 D6:1 B5:1 | r:4 |')                 # bar 10: the unison break

# THE UNISON BREAK (signature move 2): sax + lead guitar + bass in octaves, the kit hitting every note with them -
# a blues-scale tumble from the top E down to the G-G# grind and back up, the last bar of each chorus and of the
# guitar solo, slamming into the riff
UNISON = 'E5:0.5 D5:0.5 B4:0.5 A4:0.5 G4:0.25 G#4:0.25 B4:0.5 D5:0.5 E5:0.5 |'
UNISON_KIT = {'snare': 'x.x.x.x.xxx.x.x.', 'kick': 'x...x...x.x.x.x.', 'tom_lo': '........x.......'}

# ------------------------------------------------------------------------------------------ the guitar
SOLO = notes('E5:0.5 G5:0.5 A5:0.5 B5:2.5^peak | A5:0.5 B5:0.5 A5:0.5 F#5:0.5 D5:1 E5:1 | '
             'C#5:0.5 E5:0.5 A5:1 G#5:0.5 F#5:0.5 E5:1 | B4:0.5 E5:0.5 G5:0.5 G#5:0.5 B5:2 | '
             'C6:1.5 B5:0.5 G5:0.5 E5:0.5 G5:1 | A5:1 F#5:0.5 D5:0.5 A5:2^peak | '
             'B5:0.5 D6:0.5 B5:0.5 A5:0.5 G5:0.5 E5:0.5 D5:0.5 E5:0.5 | F#5:1 A5:1 D#5:2 | '
             'D6:3^peak B5:0.5 A5:0.5 | D6:0.5 B5:0.5 A5:0.5 F#5:0.5 A5:2 | '
             'C#6:0.5 B5:0.5 A5:0.5 E5:0.5 F#5:0.5 A5:0.5 C#6:1 | B5:2 G#5:0.5 A5:0.5 B5:1 | '
             'D6:0.5 C6:1.5^peak G5:0.5 E5:0.5 G5:1 | F#5:0.5 A5:0.5 D6:2 C6:0.5 A5:0.5 | '
             'B5:0.5 G5:0.5 E5:0.5 G5:0.5 B5:0.5 C#6:0.5 D6:1 | r:4 |', vel=100)     # bar 16: the unison break
# riff2: guitar answers in the riff's low held bar and its last bar (second half only)
RIFF_GTR = notes('r:4 | r:4 | r:4 | r:4 | r:4 | r:4 | r:4 | r:4 | r:4 | r:4 | r:4 | '
                 'r:1 B5:1 G#5:0.5 E5:0.5 B5:1 | r:4 | r:4 | r:4 | r:2.5 B5:0.5 D6:1 |', vel=96)
# the outro: answers (8), the trade - sax two bars, guitar two bars (8), freer under riff B in the fade (8)
OUT_SAX = (RIFF_A + ' ' + GRIND + 'r:4 | r:4 | E5:0.5 G5:0.5 E5:0.5 C5:0.5 G5:2^peak | F#5:1 E5:0.5 D5:0.5 B4:2 | '
           'r:4 | r:4 | ' + RIFF_B)
OUT_GTR = notes('r:4 | r:4 | r:4 | r:1 B5:1 G#5:0.5 E5:0.5 B5:1 | r:4 | r:4 | r:4 | r:2 D6:2^peak | '
                'r:4 | r:4 | G#5:0.5 B5:0.5 D6:2^peak B5:0.5 G#5:0.5 | A5:0.5 B5:0.5 G#5:1 E5:2 | '
                'r:4 | r:4 | E5:0.5 G#5:0.5 B5:0.5 C#6:0.5 D6:2^peak | C#6:1 B5:1 F#5:1 B5:1 | '
                'r:4 | r:2 B5:2 | r:4 | r:1 B5:1 A5:0.5 G#5:0.5 E5:1 | r:4 | r:2 D6:1 B5:1 | r:4 | r:2 B5:2 |',
                vel=100)


def build() -> Song:
    s = Song('Kingsway After Rain', tempo=TEMPO, key='E major', seed=1979, tail=6)
    intro = s.section('intro', bars=8)
    riff1 = s.section('riff1', bars=16)
    verse1 = s.section('verse1', bars=16)
    chorus1 = s.section('chorus1', bars=10)
    riff2 = s.section('riff2', bars=16)
    verse2 = s.section('verse2', bars=16)
    chorus2 = s.section('chorus2', bars=10)
    riff3 = s.section('riff3', bars=8)
    bridge = s.section('bridge', bars=8)
    gsolo = s.section('gsolo', bars=16)
    outro = s.section('outro', bars=24)
    riffs = (riff1, riff2, riff3)
    verses, choruses = (verse1, verse2), (chorus1, chorus2)
    order = (intro, riff1, verse1, chorus1, riff2, verse2, chorus2, riff3, bridge, gsolo, outro)
    P = {k: s.prog(v) for k, v in dict(intro=INTRO, verse=VERSE, chorus=CHORUS, bridge=BRIDGE).items()}
    P['verse2nd'] = s.prog('E D/E C#m7 C#m7 Amaj7 G6 F#m7 Bsus4:0.5 B:0.5')
    P['riff'] = s.prog(RIFF)
    P['riff16'] = s.prog(RIFF + ' ' + RIFF)
    P['outro'] = s.prog(' '.join([RIFF] * 3))

    def sec_prog(sec):
        n = sec.name
        if n.startswith('riff'):
            return P['riff16'] if sec.bars == 16 else P['riff']
        if n == 'gsolo':
            return P['riff16']
        return P['verse'] if n.startswith('verse') else P['chorus'] if n.startswith('chorus') else P[n]

    # ------------------------------------------------------------------------------------------ the band
    s.master.add(fx.eq({'peak1.freq': 380, 'peak1.gain': -3.5, 'peak1.q': 0.7, 'peak2.freq': 1100,
                        'peak2.gain': -3.5, 'peak2.q': 0.8, 'peak3.freq': 1600, 'peak3.gain': -1.0, 'peak3.q': 0.7,
                        'high.freq': 9000, 'high.gain': 2.0}),
                 fx.width(width=1.3, monobass=120))       # ours first, the preset's master keeps it
    b = bands.power_ballad(s, ids={'lead': 'guitar'})
    gtr, piano, strings, pad, kit, bass = b.lead, b.piano, b.strings, b.pad, b.drums, b.bass
    hall, plate = b.hall, b.plate
    ac1 = s.track('acoustic_l', 'sampled/acoustic_guitar', gain_db=-9.5, pan=-0.7, sends={hall: -18})
    ac2 = s.track('acoustic_r', 'sampled/steel_guitar', gain_db=-8.5, pan=0.7, sends={hall: -18})
    for a in (ac1, ac2):
        a.add_fx(fx.chorus(mode='I', mix=0.3))
    pad.add_fx(fx.eq({'hp.freq': 220}))
    piano.fx[1].set(ratio=1.3, threshold=-18)
    bass.fx['ducker'].set(depth=10, hold=30, release=140)     # the kick owns the low end on its hits
    kit.add_fx(fx.eq({'low.freq': 70, 'low.gain': -1.5, 'peak1.freq': 125, 'peak1.gain': -2.5, 'peak1.q': 1.0}))   # the bass owns ~110 Hz
    bass.add_fx(fx.eq({'peak1.freq': 115, 'peak1.gain': 2.0, 'peak1.q': 0.8}))
    for t_ in (piano, strings, ac1, ac2):
        t_.add_fx(fx.eq({'peak1.freq': 350, 'peak1.gain': -2.5, 'peak1.q': 0.8}))
    for bus_ in (hall, plate):
        bus_.add_fx(fx.eq({'hp.freq': 260}))
    # the bed wider, but moderate: the cover's 1.25 + 1.75 went negative - the VPO section is wide already (its own
    # correlation ~0), so only the pad is widened
    pad.add_fx(fx.width(width=1.15))

    rhodes = s.track('rhodes', epiano('rhodes'), gain_db=0.0, pan=0.0,
                     fx=[fx.eq({'hp.freq': 180, 'peak1.freq': 380, 'peak1.gain': -5.0, 'high.freq': 7000,
                                'high.gain': 2.0}), fx.chorus(mode='I', mix=0.3)], sends={plate: -14, hall: -18})

    # ------------------------------------------------------------------------------------------ drums
    plan = {'intro': {'role': 'intro', 'energy': 0.2, 'time': 'none'},
            'bridge': {'role': 'bridge', 'energy': 0.3, 'time': 'none'},
            'gsolo': {'role': 'solo', 'energy': 0.82}, 'outro': {'role': 'outro', 'energy': 0.8}}
    for i, r in enumerate(riffs):
        plan[r.name] = {'role': 'chorus', 'energy': 0.78 + 0.04 * i, 'time': 'hat8'}
    for v in verses:
        plan[v.name] = {'role': 'verse', 'energy': 0.45, 'time': 'hat8'}
    for c in choruses:
        plan[c.name] = {'role': 'chorus', 'energy': 0.68, 'time': 'hat8'}
    part = drummer.arrange(s, style='pop', density=0.45, seed=11, kit=kit, plan=plan)
    part.play(kit)

    # ------------------------------------------------------------------------------------------ bass
    bmem = bassist.Memory()
    for sec in order[1:]:
        n = sec.name
        style_part = ('chorus' if n.startswith(('riff', 'chorus', 'outro', 'gsolo')) else
                      'bridge' if n == 'bridge' else 'verse')
        pr = P['outro'] if sec is outro else sec_prog(sec)
        bassist.arrange(pr, bpm=TEMPO, key=s.key, style='pop', part=style_part, seed=21 + order.index(sec),
                        memory=bmem, at=sec).place(bass, sec)
    bass.play(Clip([(0, 3.5, 'B1', 66)], length=4), intro.bar(7))

    # ------------------------------------------------------------------------------------------ keys / pads
    def pedal(at, prog):
        pts = []
        for st, dur, ch in prog:
            if ch is not None:
                pts += [(at + st, 0, 'step'), (at + st + 0.08, 1, 'step')]
        return pts

    def sus(t, prog, at, register, vel):
        t.play(prog.block(voicing='spread', register=register, vel=vel), at)

    # intro: the lush bed alone, a rising top line in the strings (G# A G F# | G# B A B)
    sus(pad, P['intro'], intro, ('E3', 'B4'), 72)
    sus(strings, P['intro'], intro, ('E3', 'G#4'), 64)
    top = notes('G#4:4 A4:4 G4:4 F#4:4 | G#4:4 B4:4 B4:4 A4:4', vel=74)
    strings.play(touch(top, 58, 86), intro)
    strings.automate('gainDb', ramp(intro.start, intro.bar(4), -10, -1, 'smooth'))
    sus(pad, P['bridge'], bridge, ('B2', 'B4'), 66)
    sus(strings, P['bridge'], bridge, ('E3', 'B4'), 62)
    strings.play(touch(notes('E5:4 F#5:4 D5:4 E5:4 | G5:4 F#5:4 D5:4 D#5:4', vel=74), 54, 84), bridge)
    for i, r in enumerate(riffs):
        sus(strings, sec_prog(r), r, ('G#2', 'B4') if i < 2 else ('B2', 'E5'), 70 + 3 * i)
        sus(pad, sec_prog(r), r, ('B2', 'B4'), 62)
    sus(strings, P['outro'], outro, ('B2', 'E5'), 72)
    sus(pad, P['outro'], outro, ('B2', 'B4'), 62)
    for c in choruses:
        sus(strings, P['chorus'], c, ('E3', 'E5'), 76)
        sus(pad, P['chorus'], c, ('B2', 'B4'), 66)
        strings.automate('gainDb', ramp(c.start, c.bar(4), -6, 0, 'smooth'))
    for v in verses:
        sus(strings, P['verse2nd'], v.bar(8), ('E3', 'B4'), 56)        # the verse's second half
    sus(strings, sec_prog(gsolo), gsolo, ('G#2', 'B4'), 72)
    sus(pad, sec_prog(gsolo), gsolo, ('B2', 'B4'), 64)

    # piano: broken chords in the verses (low, under the Rhodes), 8th chords in the choruses, quarter stabs in the
    # riffs, the bridge rolled
    for v in verses:
        br = P['verse'].block(voicing='spread', register=('E2', 'B4'), vel=54).arpeggiate('pinky', rate='1/8', gate=1.6)
        piano.play(touch(br, 30, 90).vel_pattern([1.2, 0.66, 0.85, 0.66], grid='1/8'), v)
        piano.automate('instrument.pedal', pedal(v.start, P['verse']))
    for c in choruses:
        cc = P['chorus'].block(voicing='spread', register=('E2', 'G#4'), rhythm='x.x.x.x.', step='1/8', vel=70)
        piano.play(touch(cc, 36, 102).vel_pattern([1.22, 0.62, 0.9, 0.64], grid='1/8'), c)
        piano.automate('instrument.pedal', pedal(c.start, P['chorus']))
    for r in riffs + (gsolo, outro):
        pr = P['outro'] if r is outro else sec_prog(r)
        rc = pr.block(voicing='spread', register=('E2', 'G#4'), rhythm='x...x...', step='1/8', vel=64)
        piano.play(touch(rc, 34, 98).vel_pattern([1.2, 0.68, 0.92, 0.7], grid='1/4'), r)
        piano.automate('instrument.pedal', pedal(r.start, pr))
    piano.play(P['bridge'].block(voicing='spread', register=('E2', 'D5'), vel=58).strum(ms=60, bpm=TEMPO), bridge)
    piano.automate('instrument.pedal', pedal(bridge.start, P['bridge']))

    # acoustic guitars: the songwriter strum (left) + a steel-string double (right, not in the verses)
    gmem1, gmem2 = gt.Memory(), gt.Memory()
    for sec in order[1:]:
        if sec is bridge:
            continue
        pr = P['outro'] if sec is outro else sec_prog(sec)
        gt.arrange(pr, bpm=TEMPO, key=s.key, style='songwriter', section=sec, sound=ac1, memory=gmem1,
                   seed=31 + order.index(sec), strings='top5').play(ac1, sec)
        if not sec.name.startswith('verse'):
            gt.arrange(pr, bpm=TEMPO, key=s.key, style='pop', section=sec, sound=ac2, memory=gmem2,
                       seed=61 + order.index(sec), strings='top5').play(ac2, sec)
    gt.arrange(P['bridge'], bpm=TEMPO, key=s.key, style='fingerstyle', section=bridge, sound=ac1, memory=gmem1,
               seed=90).play(ac1, bridge)

    # ------------------------------------------------------------------------------------------ the sax (hero 70s)
    sax = s.track('sax', 'sampled/alto_sax', gain_db=0.0)
    hero(sax, family='sax', genre='pop', sections=list(riffs) + [outro], bed=[strings, pad], competitors=[ac1, ac2])
    hmem = hornist.Memory()

    def sax_line(spec, at, vel, seed):
        clip = notes(spec, vel=96, length='bar')
        perf = hornist.arrange(clip, TEMPO, family='sax', style='hero70s', section='riff', vel=vel,
                               peaks=tuple(getattr(clip, 'peaks', ())), seed=seed, memory=hmem, at=at)
        perf.place(sax, at)

    for i, r in enumerate(riffs):
        sax_line(RIFF_A + ' ' + RIFF_B if r.bars == 16 else RIFF_A, r, (80 + 2 * i, 124 + i), 3 + i)
    sax_line(OUT_SAX, outro, (80, 125), 9)

    # ------------------------------------------------------------------------------------------ the lead guitar
    hero(gtr, family='guitar', genre='rock', sections=[gsolo], bed=[strings, pad], competitors=[ac1, ac2, piano])
    gtr.gain_db -= 8.0                                    # the cover's lesson: the hero guitar lands ~7 dB hot
    lmem = gt.Memory()
    gt.lead(SOLO, P['riff16'], bpm=TEMPO, key=s.key, style='rock', section='solo', sound=gtr, memory=lmem,
            at=gsolo, climax=True, gestures=True, seed=5).play(gtr, gsolo)
    gt.lead(RIFF_GTR, P['riff16'], bpm=TEMPO, key=s.key, style='rock', section='outro', sound=gtr, memory=lmem,
            at=riff2, gestures=True, seed=4).play(gtr, riff2)
    gt.lead(OUT_GTR, P['outro'], bpm=TEMPO, key=s.key, style='rock', section='outro', sound=gtr, memory=lmem,
            at=outro, gestures=True, seed=6).play(gtr, outro)
    # the bridge: long notes swelling in (the guitar announcing the solo)
    gt.lead(notes('B4:8^peak D5:4 D#5:4', vel=96), None, bpm=TEMPO, key=s.key, style='ballad', section='bridge',
            sound=gtr, memory=lmem, at=bridge.bar(4), gestures=True, seed=8).play(gtr, bridge.bar(4))

    # ------------------------------------------------------------------------------------------ the Rhodes melody
    pmem = pianist.Memory()
    for i, (sec, mel, lo, hi) in enumerate(((verse1, VERSE1_MEL, 54, 100), (chorus1, CHORUS_MEL, 62, 108),
                                             (verse2, VERSE2_MEL, 56, 102), (chorus2, CHORUS_MEL, 64, 112))):
        m = touch(notes(mel, vel=90), lo, hi)
        pianist.arrange(m, sec_prog(sec), bpm=TEMPO, key=s.key, style='ballad', density=0.4, seed=40 + i,
                        lh=None, memory=pmem, at=sec.start).place(rhodes)

    # ------------------------------------------------------------------------------------------ the signature moves
    # 2. THE UNISON BREAK: the last bar of chorus1, chorus2 and the guitar solo - sax, lead guitar and bass in
    # octaves, the kit on every note (its own fill replaced), then the riff (or the outro) crashes in
    for i, at in enumerate((chorus1.bar(9), chorus2.bar(9), gsolo.bar(15))):
        sax_line(UNISON, at, (84, 124), 30 + i)
        gt.lead(notes(UNISON, vel=108), None, bpm=TEMPO, key=s.key, style='rock', section='solo', sound=gtr,
                memory=lmem, at=at, gestures=False, seed=50 + i).play(gtr, at)
        bass.play(touch(notes(UNISON, transpose=-24, vel=100), 88, 116), at, replace=True)
        kit.play(drums(UNISON_KIT, vel=96).crescendo(0.8, 1.15), at, replace=True)
    # 1. THE STOP: riff3 (after chorus2's unison) - the band hits the downbeat and drops out, the sax grinds into its
    # held G#5 ALONE over two bars of air (the reverbs ringing), a tom pickup, and the band slams back in on bar 3
    band = (piano, strings, pad, bass, ac1, ac2, kit)
    for t_ in band:
        t_.clear(riff3.start + 0.1, riff3.bar(2))
        t_.cut(riff3.start + 0.7)
    kit.play(drummer.tom_run(1, TEMPO, kit=kit, energy=0.9, seed=3), riff3.start + 7)
    # the releases (pad / string tails) and the band's hall choked with the hit: real air under the sax
    t0, t1 = riff3.start + 0.75, riff3.bar(2)
    for t_, db in ((piano, -60), (strings, -60), (pad, -60), (bass, -60), (ac1, -60), (ac2, -60), (hall, -9)):
        t_.add_fx(fx.utility(name='stop', gain=0))
        t_.automate('fx.stop.gain', [(t0, 0), (t0 + 0.5, db, 'smooth'), (t1 - 0.05, db, 'step'), (t1, 0, 'step')])
    # 3. THE TRADE (outro bars 9-16): sax and guitar answer each other two bars at a time (OUT_SAX / OUT_GTR)

    # ------------------------------------------------------------------------------------------ levels and the fade
    def lane(track, levels):
        track.automate('gainDb', per_section(dict(zip(order, levels)), glide=0.5))

    #                intro riff1 v1  ch1 riff2 v2  ch2 riff3 brdg gsolo outro
    lane(piano,     (-9, -3, -2, -2, -3, -2, -2, -3, 0, -4, -3))
    lane(ac1,       (-30, -2, 0, 0, -2, 0, 0, -2, 0, -3, -2))
    lane(bass,      (0, 0, -3.5, 0, 0, -3.5, 0, 0, 0, 0, -1.5))
    lane(kit,       (0, 0, -1.5, 0, 0, -1.5, 0, 0, 0, 0, 0))
    lane(gtr,       (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1))
    lane(pad,       (4, -4, -6, -4.5, -4, -6, -4.5, -4, 2, -4, -4))
    s.master.automate('gainDb', ramp(outro.bar(14), outro.end, 0, -40, 'smooth'))
    # the user: when the sax is heard, everything else ducks under it (a sidechain, not the effects); the bed and the
    # comping step back a little under the Rhodes melody too
    s.sidechain(*[t_ for tid, t_ in s.tracks.items() if tid != 'sax'], key=sax, depth=4, attack=15, release=250)
    s.sidechain(strings, pad, piano, ac1, ac2, key=rhodes, depth=3, attack=15, release=250)
    s.master.add(fx.limiter(gain=7.0, ceiling=-1.2, release=100))
    return s
