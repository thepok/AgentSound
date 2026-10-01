"""Lamplight Avenue - a soft-rock / sophisticated-pop instrumental in the spirit of late-70s city records
(Gerry Rafferty's "Baker Street" as the STYLE model; every note here is original: own hook, own melodies, own
changes). 112 BPM, straight 8ths, Eb major.

The idea: ONE saxophone hook that everything returns to - two rising 8ths that leap into a held high note (Eb-Bb
-> F, then Ab-Eb -> G over Abmaj7, then G-C -> G an octave above the start), each answered by a falling tail; it
opens the song, comes back between the sections as the "riff", is quoted by the chorus melody (bars 3 and 5), is
traded with the guitar in the solo and plays the song out over a long fade.

Form (bars)
  intro     4  a string swell; the piano alone hints the hook up high (pianist.arrange), a tom pickup
  riff      8  the sax hook with the full band (crash)
  verse1   16  wistful: C minor colour (Cm7 Abmaj7 Eb/G Fm7 ...), sax low and soft, Rhodes, bass, side stick ->
               backbeat in the second half
  pre1      4  Fm7 Gm7 Abmaj7 Bbsus4: the sax climbs, strings swell, snare builds, tom fill
  chorus1   8  the anthem: a descending bass (Eb D C Bb Ab G F), sax high, harmonized a third below by a tenor,
               piano 8ths, pad, strings, open hats
  riff2     8  the hook again
  verse2    8  the piano takes the verse melody (pianist.arrange), the Rhodes answers, ride cymbal
  pre2      4
  chorus2   8  bigger: strings an octave up, guitar answers in the tail
  solo     16  overdriven lead guitar (bends, vibrato, legato) over the verse changes, then sax and guitar trade
               the hook's motif over the chorus changes
  build     4  down to Rhodes + bass pedal, snare roll crescendo, a beat of air
  chorus3   8  the peak: the leap reaches Ab5, the section doubled, strings up, crashes
  outro    16  the riff twice, the sax ad-libbing its ending, a classic long fade

The sax is a HERO sax (recipes/HUMAN_FEEDBACK.md 2026-09-30: "epischer und praesenter"): layered/hero_sax -
close-miked Weresax alto, compressed, gritty, double-tracked by two MTG alto takes, a big pre-delayed plate of its own
(bus/hero_plate), echo throws at the phrase ends; the bed carved around it (song.carve: a keyed dynamic EQ at 2.5 kHz),
ridden 2-4.5 dB up in the hook sections.

The sax is PLAYED by the wind player (agentsound.hornist; HUMAN_FEEDBACK 2026-09-30: "da spielt er eine Note und pustet
mal kurz mehr, mal kurz weniger"): the air moves inside the held notes (pushes on the beat, pulses, swells, blooms,
tapers) on the hero's breath stage after the compressor, vibrato deepening with the air on the held peaks, a shake at
the last chorus's climax, and the bell moves against the mic (leaning in on the hook peaks, turning away on soft
endings). LAMPLIGHT_HORNIST=0 renders the old lines (A/B).

Credits: Weresax alto (Karoryfer, CC0), MTG solo alto + tenor sax (MTG / UPF, CC-BY 4.0), jRhodes3d (Jeff Learman,
CC-BY-NC 4.0: private listening fine), Salamander Grand Piano V3 (Alexander Holm, CC-BY), Virtual Playing Orchestra
strings (Paul Battersby), Karoryfer Big Rusty drums + Growlybass (CC0), FreePats FSBS electric guitar DI (CC0),
AVL Buskmans Holiday hand percussion (Glen MacArthur / AV Linux, CC-BY-SA 3.0: credit it, share-alike),
Lexicon 224XL IRs (Little Devil). out/credits.txt lists every source and the required attributions.

"""
import os

from agentsound import *
from agentsound import articulation as art, bands, hornist, pianist
from agentsound.bandlib.pop import epiano
from agentsound.humanize import touch
from agentsound.patches.hero import HERO_SAX

ANALYSIS = {'profile': 'pop'}
METADATA = {'title': 'Lamplight Avenue', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Soft Rock'}
COVER = {'style': 'jazz', 'palette': ['#e0a040', '#1d3557'], 'title': 'LAMPLIGHT AVENUE', 'subtitle': 'AgentSound'}

TEMPO = 112
SAX = os.environ.get('LAMPLIGHT_SAX', 'hero/sax')      # the hero sax (patches/hero.py + the heroes 'air' stage)
HORNIST = os.environ.get('LAMPLIGHT_HORNIST', '1') != '0'        # 0: the sax lines without the wind player (A/B)
HERO = HERO_SAX['mix']


# ------------------------------------------------------------------------------------------------ the material
# notation (docs/COMPOSE_API.md "Notation"): sticky note values, ^peak = the held high notes (line.peaks: the scoops,
# the vibrato peaks of the wind player)
# the HOOK (8 bars over RIFF): motif = two rising 8ths leaping into a held high note, a falling answer
RIFF_H = phrases(hook='Eb4/8 Bb4 F5:2.5^peak Eb5/8 | D5/4 Bb4/8 C5 Bb4/4. G4/8 | Ab4/8 Eb5 G5:2.5^peak F5/8 | '
                      'Eb5/4. F5/8 D5/4 Bb4:0.75 r/16 |',
                 climb='G4/8 C5 G5:2.5^peak', vel=96)
HOOK = RIFF_H('hook climb F5/8 | Eb5/4 C5/8 Eb5 F5/4. Eb5/8 | C5/4 Ab4/8 C5 D5/4 F5 | Eb5:3 r/4')
# the last riff of the outro: the same motif, the ending opened up (ad lib) and falling off at the very end
HOOK_OUT = RIFF_H('hook climb r/8 | Eb5 F5 Ab5:2.5^peak G5/8 | F5/4 Eb5/8 C5 D5/4 F5 | Eb5:3.5 r/8')
# the verse melody (8 bars over VERSE), low and speaking; the second half climbs and quotes the motif
VERSE_A = notes("""r/4 G4/8 Bb4 C5/4 Bb4/8 G4 | Ab4/4. G4/8 Eb4/4. r/8 | r/4 Bb3/8 Eb4 G4/4 F4/8 G4 |
                   Ab4/4. G4/8 F4/4 Eb4/8 F4 | r/4 G4/8 Bb4 C5/4 D5/8 Eb5 | C5/2 Bb4/8 Ab4/4. |
                   r/4 F4/8 Ab4 Bb4/4. C5/8 | D5:2.5 r:1.5""", vel=96)
VERSE_B = notes("""r/4 G4/8 Bb4 C5/4 D5/8 Eb5 | C5/4. Bb4/8 Ab4/4. r/8 | Bb4/4 G4/8 Bb4 Eb5/4. D5/8 |
                   C5/4. Ab4/8 F4/4. r/8 | r/4 Eb4/8 G4 C5/4 Eb5 | F5/4. Eb5/8 C5/4 Eb5 | F5/2 Eb5/4 C5 |
                   D5:3 r/4""", vel=96)
# the pre-chorus: the sax climbs a third per bar, a pickup into the chorus
PRE = notes('C5/4 Ab4 C5/4. Eb5/8 | D5/4 Bb4 D5/4. F5/8 | Eb5/4 C5 Eb5/2 | F5/2 r/8 Bb4 C5 D5', vel=96)
# the chorus: long notes up high; the hook's motif in bars 3 and 5 (chorus 3: the leap over Abmaj7 reaches Ab5,
# the tail climbs to the tonic up high)
CHO = phrases(front='Eb5:3 F5/8 G5 | F5/2 D5/4 Bb4 | G4/8 C5 G5:2.5^peak F5/8 | D5/4. C5/8 Bb4/2 |', vel=96)
CHORUS = CHO('front C5/8 Eb5 G5:2.5^peak F5/8 | G5/4. F5/8 Eb5/4 Bb4 | C5/4 Eb5 F5/2 | Eb5/2 D5/4. r/8')
CHORUS3 = CHO('front C5/8 Eb5 Ab5:2.5^peak G5/8 | G5/4. F5/8 Eb5/4 Bb4 | C5/4 Eb5 F5/4. G5/8 | F5/2 Eb5/4. r/8')

# the guitar solo, part 1 (8 bars over VERSE): written sounding; 'b' = bent up into the note, 'v' = vibrato
SOLO1 = [
    (0.5, .5, 'G4', 88), (1.0, .5, 'Bb4', 92), (1.5, .5, 'C5', 96), (2.0, 1.5, 'Eb5', 108, 'b'),
    (3.5, .5, 'C5', 90),
    (4.0, .5, 'Bb4', 92), (4.5, .5, 'C5', 96), (5.0, 2.5, 'G5', 114, 'bv'), (7.5, .5, 'F5', 90),
    (8.0, .75, 'Eb5', 102), (8.75, .25, 'F5', 86), (9.0, .5, 'Eb5', 94), (9.5, .5, 'C5', 90),
    (10.0, 1.0, 'Bb4', 98), (11.0, 1.0, 'G4', 92),
    (12.0, .5, 'Ab4', 90), (12.5, .5, 'C5', 94), (13.0, .5, 'Eb5', 98), (13.5, .5, 'F5', 102),
    (14.0, 2.0, 'Ab5', 112, 'bv'),
    (16.5, .25, 'G5', 100), (16.75, .25, 'F5', 94), (17.0, .25, 'Eb5', 94), (17.25, .25, 'C5', 92),
    (17.5, .5, 'Eb5', 98), (18.0, 1.5, 'G5', 110, 'b'), (19.5, .5, 'F5', 94),
    (20.0, 1.0, 'Eb5', 102), (21.0, .5, 'C5', 94), (21.5, .5, 'Eb5', 98), (22.0, 2.0, 'Bb5', 118, 'bv'),
    (24.0, .5, 'Ab5', 104), (24.5, .5, 'F5', 98), (25.0, .5, 'Eb5', 96), (25.5, .5, 'F5', 100),
    (26.0, 1.5, 'Bb5', 116, 'b'), (27.5, .5, 'Ab5', 98),
    (28.0, 3.0, 'F5', 110, 'v'),
]
# part 2 (8 bars over CHORUS): the trade - the sax states the motif, the guitar answers it, bent and higher
TRADE_SAX = notes('Eb4/8 Bb4 F5:2.5^peak Eb5/8 | D5/2 Bb4/4 r | r/1 | r | C5/8 Eb5 G5:2.5^peak F5/8 | '
                  'G5/4. F5/8 Eb5/4. r/8', vel=96)
TRADE_GTR = [
    (8.0, .5, 'G4', 96), (8.5, .5, 'C5', 102), (9.0, 2.0, 'G5', 116, 'bv'), (11.0, .5, 'F5', 96),
    (11.5, .5, 'Eb5', 94), (12.0, 1.0, 'D5', 100), (13.0, .5, 'F5', 98), (13.5, .5, 'D5', 94),
    (14.0, 1.5, 'Bb4', 104, 'v'),
    (24.0, .5, 'F5', 102), (24.5, .5, 'Ab5', 106), (25.0, 1.0, 'C6', 120, 'b'), (26.0, .5, 'Bb5', 104),
    (26.5, .5, 'Ab5', 100), (27.0, 1.0, 'F5', 104),
    (28.0, .5, 'F5', 104), (28.5, .5, 'Ab5', 108), (29.0, 1.0, 'Bb5', 116, 'b'), (30.0, 2.0, 'D6', 122, 'bv'),
]
# chorus 2's tail: a short guitar answer where the sax breathes
GTR_ANSWER = [(31.5, .25, 'Bb4', 92), (31.75, .25, 'C5', 96)]


def build() -> Song:
    s = Song('Lamplight Avenue', tempo=TEMPO, key='Eb major', seed=78, tail=5)
    intro = s.section('intro', bars=4)
    riff1 = s.section('riff', bars=8)
    verse1 = s.section('verse1', bars=16)
    pre1 = s.section('pre1', bars=4)
    chorus1 = s.section('chorus1', bars=8)
    riff2 = s.section('riff2', bars=8)
    verse2 = s.section('verse2', bars=8)
    pre2 = s.section('pre2', bars=4)
    chorus2 = s.section('chorus2', bars=8)
    solo = s.section('solo', bars=16)
    build_ = s.section('build', bars=4)
    chorus3 = s.section('chorus3', bars=8)
    outro = s.section('outro', bars=16)
    key = Key('Eb major')

    RIFF = s.prog('Eb Gm7 Abmaj7 Bbsus4:0.5 Bb:0.5 Cm7 Abmaj7 Fm7:0.5 Bb7:0.5 Eb')
    VERSE = s.prog('Cm7 Abmaj7 Eb/G Fm7 Cm7 Abmaj7 Bbsus4 Bb')
    PREP = s.prog('Fm7 Gm7 Abmaj7 Bbsus4:0.5 Bb:0.5')
    CHOR = s.prog('Eb Bb/D Cm7 Gm7/Bb Abmaj7 Eb/G Fm7 Bbsus4:0.5 Bb:0.5')
    INTRO = s.prog('Eb Gm7 Abmaj7 Bbsus4:0.5 Bb:0.5')

    # ------------------------------------------------------------------------------------------ the band
    # our own master first (the preset keeps it): glue only above -12 dB so the verses stay lighter than the
    # choruses, an air shelf, a wide image above 120 Hz with mono lows
    s.master.add(fx.eq({'hp.freq': 25, 'peak1.freq': 400, 'peak1.gain': -4.5, 'peak1.q': 0.6,
                        'peak2.freq': 1150, 'peak2.gain': -4.0, 'peak2.q': 0.7, 'high.freq': 9000, 'high.gain': 5.5}),
                 fx.compressor(threshold=-12, ratio=2, attack=30, release=220, knee=8, detector='rms', keyhp=100,
                               automakeup='on'),
                 fx.tape(speed='30', drive=0.6, bump=0.8, wow=0.03, flutter=0.03),
                 fx.width(width=1.4, monobass=120),
                 fx.limiter(gain=9.0, ceiling=-1.2, release=80))
    b = bands.power_ballad(s, ids={'lead': 'guitar'})
    gtr, piano, strings, pad, kit, bass = b.lead, b.piano, b.strings, b.pad, b.drums, b.bass
    hall, plate, echo = b.hall, b.plate, b.echo
    piano.fx[1].set(ratio=1.3, threshold=-18)                    # keep the pianist's touch
    piano.pan = 0.2
    # base levels (the 'gainDb' lanes below are dB on a track's gain_db)
    GTR_DB, PIANO_DB, RHODES_DB, BASS_DB, SAX_DB = 1.5, -2.0, -3.0, -1.0, -3.5
    # the wind player plays the sax at the patch's own level (the old per-note expression shapes sat ~1.9 dB under
    # it on the hero, ~3.8 dB on the tenor's dynamics): the same balance as before (measured, sax node LUFS)
    SAX_DB, SAX2_DB = (SAX_DB - 1.9, 1.0 - 3.8) if HORNIST else (SAX_DB, 1.0)
    gtr.gain_db = GTR_DB
    bass.add_fx(fx.eq({'peak1.freq': 95, 'peak1.gain': 2.5, 'peak1.q': 0.9}), first=True)   # the bass owns ~95 Hz
    gtr.add_fx(fx.eq({'peak1.freq': 2900, 'peak1.gain': -2.0, 'peak1.q': 0.9}))
    kit.add_fx(fx.eq({'peak1.freq': 125, 'peak1.gain': -2.5, 'peak1.q': 1.0}))          # the kick owns ~55 Hz
    bass.add_fx(fx.eq({'lp.freq': 2200, 'peak1.freq': 3500, 'peak1.gain': -3.0}))    # fingers, no fret click
    kit.gain_db = -3.0
    bass.fx['ducker'].set(depth=12, hold=30, release=140)             # the kick owns the low end on its hits

    # the HERO sax (HUMAN_FEEDBACK 2026-09-30: "epischer und praesenter"): close-miked alto, compressed, gritty,
    # double-tracked (layered/hero_sax); a big bright pre-delayed plate of its own, the hall, and echo THROWS at the
    # phrase ends (the echo send sits low and rises on the held last notes: art.throws below)
    hero_plate = s.bus('hero_plate', 'bus/hero_plate')
    hero_plate.add_fx(fx.eq({'hp.freq': 300}))
    SAX_ECHO = HERO_SAX['space']['echo']
    sax = s.track('sax', patches.get(SAX).with_mix(sends={'plate': None}), gain_db=0.0,
                  sends={hero_plate: HERO_SAX['space']['plate'], echo: SAX_ECHO,
                         hall: HERO_SAX['space']['hall']})
    sax2 = s.track('sax-harmony', 'sampled/tenor_sax', gain_db=SAX2_DB, pan=-0.35,
                   fx=[fx.eq({'hp.freq': 120, 'peak1.freq': 380, 'peak1.gain': -3.0, 'peak3.freq': 2600,
                              'peak3.gain': 0.5}), fx.chorus(mode='I', mix=0.3)],
                   sends={plate: -12, hall: -12})
    rhodes = s.track('rhodes', epiano('rhodes'), pan=-0.4,
                     fx=[fx.eq({'hp.freq': 190, 'peak1.freq': 420, 'peak1.gain': -7.0, 'peak1.q': 0.7,
                                'high.freq': 8000, 'high.gain': 1.5}),
                         fx.compressor(threshold=-24, ratio=2, attack=15, release=150, automakeup='on'),
                         fx.tremolo(rate=4.2, depth=0.18, stereo=90), fx.chorus(mode='I', mix=0.35),
                         fx.width(width=1.5)],
                     sends={plate: -16, hall: -12}).humanize(5, 5)

    # hand percussion: a shaker and a tambourine (the 70s studio's percussionist) - the top end of the choruses
    perc = s.track('perc', 'sampled/busk_kit', gain_db=-9.0, pan=0.45,
                   fx=[fx.eq({'hp.freq': 400, 'high.freq': 9000, 'high.gain': 2.0})],
                   sends={plate: -18}).humanize(4, 6)
    for bus_ in (hall, plate):
        bus_.add_fx(fx.eq({'hp.freq': 260}))

    # the bed ducks under the sax (HUMAN_FEEDBACK: the lead reads in front) and steps out of its presence band
    # while it plays (a keyed dynamic EQ: song.carve), so the hero sits on top with everything carved around it
    s.sidechain(strings, pad, piano, key=sax, depth=2.5, attack=15, release=260)
    s.sidechain(rhodes, key=sax, depth=3.5, attack=15, release=260)
    s.carve(strings, pad, piano, rhodes, key=sax, freq=HERO['carve_freq'], q=HERO['carve_q'], depth=HERO['carve_db'])
    s.carve(gtr, key=sax, freq=HERO['carve_freq'], q=HERO['carve_q'], depth=HERO['carve_db'] - 1)
    s.carve(kit, key=sax, freq=3800, q=0.9, depth=2)        # hats / snare crack step aside a little under the sax

    mem = pianist.Memory()
    breath = {sax: hornist.Memory(), sax2: hornist.Memory()}      # the wind players' song-wide budgets

    # ------------------------------------------------------------------------------------------ helpers
    def sax_line(line, at, lo, hi, *, peaks=None, seed=1, track=None, throws=True, section=None, climax=False,
                 style='hero', extra=()):
        t = track or sax
        peaks = tuple(getattr(line, 'peaks', ())) if peaks is None else peaks      # the ^peak notes
        c = Clip(list(line), length=32 if max(n.start + n.dur for n in line) <= 32 else 64)
        if HORNIST:
            # the wind player (recipes/HUMAN_FEEDBACK.md 2026-09-30: "da spielt er eine Note und pustet mal kurz
            # mehr, mal kurz weniger"): touch() velocity arcs, legato phrases, breaths, and INSIDE the held notes
            # the air (pushes on the beat, pulses, swells, blooms, tapers), vibrato on the held peaks that deepens
            # with the air, scoops into the hook peaks, the bell leaning into the mic on them / turning away on the
            # soft endings - after the hero compressor (the 'mic' stage), so it is not squeezed away
            perf = hornist.arrange(c, TEMPO, family='sax', style=style, section=section, peaks=peaks, vel=(lo, hi),
                                   seed=seed, climax=climax, memory=breath[t], at=at, humanize_ms=4)
            perf.add(*extra)
            perf.place(t, at)
            played = perf.clip
            if throws and t is sax:                        # the echo thrown at the held phrase ends
                # the phrase ends now taper / turn away: the throw sits 0.7 dB higher for the same echo level
                art.throws(t, played, at, bus=echo, base=SAX_ECHO, throw=HERO_SAX['space']['throw'] + 0.7,
                           min_rest=0.5, min_dur=1.0)
            return played
        c = touch(c, lo, hi)
        played = art.perform(t, c, at, glide_leaps=None, humanize_ms=4, late_ms=0, vib=False, seed=seed)
        a = at.start if hasattr(at, 'start') else at
        # vibrato: wide and singing on the held peaks (the hero's money notes), gentle on the other long notes
        top = Clip([n for n in played if any(abs(n.start - pk) < 0.1 for pk in peaks)], length=played.length)
        rest = Clip([n for n in played if not any(abs(n.start - pk) < 0.1 for pk in peaks)], length=played.length)
        if len(top):
            art.vibrato(t, top, at, depth=26, rate=5.4, delay=0.28, grow=0.5, min_dur=0.75, seed=seed)
        if len(rest):
            art.vibrato(t, rest, at, depth=13, rate=5.2, delay=0.34, grow=0.6, min_dur=0.75, seed=seed + 1)
        if throws and t is sax:                            # the echo thrown at the held phrase ends
            art.throws(t, played, at, bus=echo, base=SAX_ECHO, throw=HERO_SAX['space']['throw'], min_rest=0.5,
                       min_dur=1.0)
        pts = []
        for p in peaks:                                    # a scoop into the held high notes only
            pts += [(a + p - 0.06, 0), (a + p, -0.8, 'step'), (a + p + 0.22, 0, 'smooth')]
        if pts:
            t.automate('instrument.pitchbend', pts)
        return played

    def harmony(line):
        """The tenor a diatonic third under the lead (a sixth where the third would leave its range)."""
        third = [key.transpose(n.pitch, -2) for n in line]
        return Clip([n._replace(pitch=h if h <= note('E5') else key.transpose(n.pitch, -5))
                     for n, h in zip(line, third)], length=line.length)

    def gtr_line(notes, at, seed=1):
        a = at.start if hasattr(at, 'start') else at
        c = touch(Clip([(n[0], n[1], n[2], n[3]) for n in notes], length=32), 66, 122)
        vel_at = {round(n.start, 3): n.vel for n in c.notes}
        c = art.legato(c, overlap=0.03)
        c = art.humanize_starts(c, TEMPO, ms=5, seed=seed)
        gtr.play(c, a)
        bend, vib, lvl = [], [], []
        for n in notes:
            marks = n[4] if len(n) > 4 else ''
            if 'b' in marks:                               # bent up a whole step into the note
                t = a + n[0]
                bend += [(t - 0.04, 0), (t, -2.0, 'step'), (t + 0.3, 0, 'smooth')]
            if 'v' in marks:
                vib.append((n[0], n[1], n[2], n[3]))
            lvl.append((a + n[0], (vel_at[round(n[0], 3)] - 104) * 0.25, 'smooth'))   # picking dynamics survive the amp
        if bend:
            gtr.automate('instrument.pitchbend', bend)
        gtr.automate('gainDb', lvl)
        if vib:
            art.vibrato(gtr, Clip(vib, length=32), a, depth=34, rate=5.6, delay=0.25, grow=0.5, min_dur=0.9)

    def pedal_points(sec, prog, at=None):
        a = sec.start if at is None else at
        pts = []
        for st, dur, ch in prog:
            if ch is None:
                continue
            pts += [(a + st, 0, 'step'), (a + st + 0.08, 1, 'step')]
        return pts

    def comp(prog, at, rhythm, register=('Eb3', 'Bb4'), vel=70, strum=12, bars=None):
        c = prog.block(voicing='drop2', rhythm=rhythm, step='1/8', register=register, vel=vel)
        c = c.vel_pattern([1.1, 0.85, 0.95, 0.8], grid='1/8').vel_random(5, seed=int(at) % 97)
        c = c.strum(ms=strum, bpm=TEMPO, direction='up')
        rhodes.play(c, at)

    # ------------------------------------------------------------------------------------------ drums
    V_SOFT = drums({'kick': 'x.......x.x.....', 'rim': '....x.......x...',
                    'hat': 'x.x.x.x.x.x.x.x.'}, vel=72).vel_pattern([1.12, 0.8, 1.0, 0.8], grid='1/8')
    V_BACK = drums({'kick': 'x.......x.x.....', 'snare': '....x..3....x...',
                    'hat': 'x.x.x.x.x.x.x.x.'}, vel=84).vel_pattern([1.12, 0.8, 1.0, 0.8], grid='1/8')
    V_RIDE = drums({'kick': 'x.......x.x...x.', 'snare': '....x..3....x..3',
                    'ride': 'x.x.x.x.x.x.x.x.'}, vel=84).vel_pattern([1.1, 0.8, 1.0, 0.82], grid='1/8')
    CHO = drums({'kick': 'x.....x.x.......', 'snare': '....X..3....X...',
                 'hat': 'x.x.x.x.x.x.x.x.', 'ohh': '..............x.'}, vel=95)
    CHO = CHO.vel_pattern([1.12, 0.82, 1.0, 0.82], grid='1/8')
    SOLO_B = drums({'kick': 'x.....x.x.x...x.', 'snare': '....X......3X..3',
                    'ride': 'x.x.x.x.x.x.x.x.'}, vel=98).vel_pattern([1.12, 0.84, 1.0, 0.84], grid='1/8')
    PRE_B = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...',
                   'hat': 'x.x.x.x.x.x.x.x.'}, vel=86)

    SHAKE = drums({42: 'xoxoxoxoxoxoxoxo', 46: '....x.......x...'},
                  vel=62).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16')
    SHAKE_S = drums({42: 'xoxoxoxoxoxoxoxo'}, vel=55).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16')
    for sec in (chorus1, chorus2, chorus3, riff2):
        perc.loop(SHAKE, sec)
    perc.loop(SHAKE_S, solo).loop(SHAKE_S, pre2).loop(SHAKE, outro)

    # intro: a soft tom pickup into the riff
    kit.play(drums({'tom_lo': '........x.x.x.x.'}, vel=60).crescendo(0.5, 1.0), intro.bar(3))
    for sec in (riff1, riff2):
        kit.loop(CHO, sec).play(crash(), sec).play(tom_fill(1), sec.beat(-1), replace=True)
    kit.loop(V_SOFT, verse1, bars=8).loop(V_BACK, verse1.bar(8), bars=8)
    kit.play(snare_roll(1, vel=(50, 90)), verse1.beat(-1), replace=True)
    kit.loop(V_RIDE, verse2)
    for pre in (pre1, pre2):
        kit.loop(PRE_B, pre).play(tom_fill(2), pre.beat(-2), replace=True)
    for ch in (chorus1, chorus2, chorus3):
        kit.loop(CHO, ch).play(crash(), ch).play(crash(), ch.bar(4))
        kit.play(tom_fill(1), ch.beat(-1), replace=True)
    kit.play(crash(), chorus3.bar(2)).play(crash(), chorus3.bar(6))
    kit.loop(SOLO_B, solo).play(crash(), solo).play(crash(), solo.bar(8))
    kit.play(tom_fill(2), solo.beat(-2), replace=True)
    kit.loop(drums({'kick': 'x.......x.......'}, vel=70), build_, bars=2)
    kit.play(snare_roll(7, build=True), build_.bar(2))            # the last beat stays empty: air before the peak
    kit.loop(CHO, outro).play(crash(), outro).play(crash(), outro.bar(8))

    # ------------------------------------------------------------------------------------------ bass
    def bassline(prog, at, pattern, vel=92, **kw):
        bass.play(prog.bass(pattern=pattern, rate='1/8', low='E1', vel=vel, gate=0.9, **kw), at)

    bassline(INTRO, intro.bar(3), '.......r', vel=70)
    for sec in (riff1, riff2):
        bassline(RIFF, sec, 'R__rr_o_', 96)
    bassline(VERSE, verse1, 'R_____r.', 84)
    bassline(VERSE, verse1.bar(8), 'R___r_f_', 90)
    bassline(VERSE, verse2, 'R__rr_f_', 90)
    for pre in (pre1, pre2):
        bassline(PREP, pre, 'R_.r.r.r', 94)                     # off the four-on-the-floor kick
    for ch in (chorus1, chorus2, chorus3):
        bassline(CHOR, ch, 'R_rrR_rr', 100)
    bassline(VERSE, solo, 'R__rr_f_', 96)
    bassline(CHOR, solo.bar(8), 'R_rrR_rr', 100)
    bass.play(Clip([(i * 0.5, 0.45, 'Bb1', 62 + i * 1.5) for i in range(32)], length=16), build_)
    bassline(RIFF, outro, 'R__rr_o_', 96)
    bassline(RIFF, outro.bar(8), 'R__rr_o_', 96)

    # ------------------------------------------------------------------------------------------ Rhodes
    for sec in (riff1, riff2):
        comp(RIFF, sec.start, 'x__x_x__', vel=66)
    comp(VERSE, verse1.start, 'x___.x__', vel=60, strum=18)
    comp(VERSE, verse1.bar(8), 'x__x__x.', vel=64)
    comp(VERSE, verse2.start, 'x___x___', vel=56, strum=22)
    for pre in (pre1, pre2):
        comp(PREP, pre.start, 'x_x_x_x_', register=('C3', 'G4'), vel=62)
    for ch in (chorus1, chorus2, chorus3):
        comp(CHOR, ch.start, 'x__x_x__', register=('Eb3', 'G4'), vel=60)
    comp(VERSE, solo.start, 'x__x_x__', vel=64)
    comp(CHOR, solo.bar(8), 'x__x_x__', vel=66)
    comp(PREP, build_.start, 'x_______', register=('G3', 'C5'), vel=58, strum=30)
    comp(RIFF, outro.start, 'x__x_x__', vel=64)
    comp(RIFF, outro.bar(8), 'x__x_x__', vel=60)

    # ------------------------------------------------------------------------------------------ piano
    # intro: the pianist hints the hook up high, soft (the sax owns it from the riff on)
    hint = touch(notes('Eb5/8 Bb5 F6:2.5 Eb6/8 | D6/4 Bb5/8 C6 Bb5/2 | Ab5/8 Eb6 G6:3', vel=96, length=16), 40, 86)
    pianist.arrange(hint, INTRO, bpm=TEMPO, key=s.key, style='ballad', density=0.45, seed=11, lh=None,
                    memory=mem, at=intro.start).place(piano)
    # verse 2: the pianist takes the verse melody an octave up, harmonized and decorated
    vmel = touch(VERSE_B.octave(1), 46, 98)
    pianist.arrange(vmel, VERSE, bpm=TEMPO, key=s.key, style='straight', density=0.55, seed=12, lh='shell',
                    lh_vel=50, memory=mem, at=verse2.start).place(piano)
    # choruses: driving 8th-note chords under the sax (below Bb4), pedal with the changes
    for ch, v in ((chorus1, 74), (chorus2, 80), (chorus3, 86)):
        c = CHOR.block(voicing='spread', register=('Bb2', 'Bb4'), rhythm='x.x.x.x.', step='1/8', vel=v)
        c = c.vel_pattern([1.2, 0.72, 0.95, 0.76], grid='1/8').vel_random(4, seed=v)
        c = c.slice(0, 16).crescendo(0.72, 1.12) + c.slice(16, 32).crescendo(0.8, 1.18)
        piano.play(c, ch)
        piano.automate('instrument.pedal', pedal_points(ch, CHOR))
    # build: repeated chords, crescendo
    bc = PREP.block(voicing='spread', register=('Bb2', 'Bb4'), rhythm='x.x.x.x.', step='1/8', vel=60)
    piano.play(bc.crescendo(0.6, 1.25), build_)
    piano.automate('instrument.pedal', pedal_points(build_, PREP))

    # ------------------------------------------------------------------------------------------ strings / pad
    def sus(t, prog, at, register, vel):
        t.play(prog.block(voicing='spread', register=register, vel=vel), at)

    sus(strings, INTRO, intro, ('Eb3', 'Bb4'), 70)
    strings.automate('gainDb', ramp(intro.start, riff1.start, -14, -2))
    for sec in (riff1, riff2):
        sus(strings, RIFF, sec, ('G2', 'Bb4'), 72)
    sus(strings, VERSE, verse1.bar(8), ('Eb3', 'Bb4'), 62)
    sus(strings, VERSE, verse2, ('Eb3', 'Bb4'), 64)
    for pre in (pre1, pre2):
        sus(strings, PREP, pre, ('F3', 'C5'), 80)
        strings.automate('gainDb', ramp(pre.start, pre.end, -8, 0, 'smooth'))
    sus(strings, CHOR, chorus1, ('G2', 'Bb4'), 80)
    sus(strings, CHOR, chorus2, ('G3', 'G5'), 84)
    sus(strings, CHOR, chorus3, ('G3', 'Bb5'), 90)
    sus(strings, VERSE, solo, ('Eb3', 'Bb4'), 70)
    sus(strings, CHOR, solo.bar(8), ('G3', 'Eb5'), 80)
    sus(strings, PREP, build_, ('F3', 'C5'), 70)
    strings.automate('gainDb', ramp(build_.start, build_.end, -12, 0, 'smooth'))
    sus(strings, RIFF, outro, ('G2', 'Bb4'), 72)
    sus(strings, RIFF, outro.bar(8), ('G3', 'Eb5'), 76)

    for ch in (chorus1, chorus2, chorus3):
        sus(pad, CHOR, ch, ('Eb3', 'Bb4'), 74)
    sus(pad, CHOR, solo.bar(8), ('Eb3', 'Bb4'), 70)
    sus(pad, RIFF, outro, ('Eb3', 'Bb4'), 70)
    sus(pad, RIFF, outro.bar(8), ('Eb3', 'Bb4'), 70)

    # ------------------------------------------------------------------------------------------ the sax
    for i, sec in enumerate((riff1, riff2)):
        sax_line(HOOK, sec, 84 + 3 * i, 118 + 3 * i, seed=10 + i, section='riff')
    sax_line(VERSE_A, verse1, 54, 86, seed=20, section='verse', style='pop')
    sax_line(VERSE_B, verse1.bar(8), 58, 92, seed=21, section='verse', style='pop')
    for i, pre in enumerate((pre1, pre2)):
        sax_line(PRE, pre, 58 + 4 * i, 106 + 4 * i, seed=30 + i, section='pre')
    for ch, mel, lo, hi, sd in ((chorus1, CHORUS, 88, 118, 40), (chorus2, CHORUS, 90, 120, 41),
                                  (chorus3, CHORUS3, 80, 124, 42)):
        sax_line(mel, ch, lo, hi, seed=sd, section='chorus', climax=ch is chorus3)
        sax_line(harmony(mel), ch, lo - 16, hi - 14, seed=sd + 50, track=sax2, section='chorus', style='pop')
    sax_line(TRADE_SAX, solo.bar(8), 78, 120, seed=50, section='solo')
    sax_line(HOOK, outro, 80, 121, seed=60, section='outro')
    # the only fall of the song: the last held Eb drops away into the fade
    if HORNIST:
        sax_line(HOOK_OUT, outro.bar(8), 78, 123, seed=61, section='outro',
                 extra=[hornist.fall(31.4, TEMPO, semis=-4, ms=430)])
    else:
        sax_line(HOOK_OUT, outro.bar(8), 78, 123, seed=61)
        fall_at = outro.bar(8) + 30.6
        sax.automate('instrument.pitchbend', [(fall_at, 0), (fall_at + 0.8, -4, 'smooth')])

    # ------------------------------------------------------------------------------------------ the guitar
    gtr_line(SOLO1, solo, seed=70)
    gtr_line(TRADE_GTR, solo.bar(8), seed=71)
    gtr_line(GTR_ANSWER, chorus2, seed=72)

    # ------------------------------------------------------------------------------------------ section levels
    # the verses lighter than the choruses (the bed steps back further under the soft verse sax)
    def lane(track, base, levels):
        """The track's base level and a per-section fader lane on top of it (dB on gain_db)."""
        track.gain_db = base
        track.automate('gainDb', per_section(levels, glide=0.5))


    order = (intro, riff1, verse1, pre1, chorus1, riff2, verse2, pre2, chorus2, solo, build_, chorus3, outro)
    lane(rhodes, RHODES_DB, dict(zip(order, (-6, -1, -6.5, -3, -3, -1, -8, -3, -3, -4.5, 0, -3, -1))))
    lane(bass, BASS_DB, dict(zip(order, (0, 0, -2, 0, 0, 0, -1.5, 0, 0, 0, -1, 0.5, 0))))
    # the piano leads the intro hint and verse 2
    lane(piano, PIANO_DB, dict(zip(order, (5, 0, 0, 0, 0, 0, 4, 0, 0, 0, 1, 0, 0))))
    # the hero sax ridden up in the hook sections (riffs, choruses, the trade, the outro), level in the verses
    R = HERO['ride_db']
    lane(sax, SAX_DB, dict(zip(order, (0, R, 0, 0.5, R + 1.5, R, 0, 0.5, R + 1.5, R, 0, R + 2.5, R))))
    if SAX in ('layered/hero_sax', 'hero/sax'):   # the octave-down tenor take for weight: the last chorus, outro riffs
        sax.automate('instrument.layers.octave.mute', [(0, 1), (chorus3.start - 0.5, 0, 'step'),
                                                      (chorus3.end - 0.5, 1, 'step'), (outro.start - 0.5, 0, 'step')])

    # ------------------------------------------------------------------------------------------ the fade
    s.master.automate('gainDb', ramp(outro.bar(6), outro.end, 0, -42, 'smooth'))
    return s
