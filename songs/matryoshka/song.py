"""Matryoshka - a self-similar pop song: one four-note hook, heard at three time scales at once.

Warm cinematic instrumental pop, 100 BPM, 4/4, straight 8ths. Original composition (an invention, see BRIEF.md).

The hook: C - A - F - G, rhythm dotted quarter / 8th / quarter / quarter (1.5 : 0.5 : 1 : 1 beats).
  x1  (one bar)       the melody on the hero piano
  x4  (four bars)     the chord roots of every phrase (I vi IV V in each key) and the harmonic rhythm 6 + 2 + 4 + 4 beats;
                      the kick's accents (1, &2, 3) are the hook's onsets
  x64 (64 bars)       the key centres of the four main sections - C major 24 bars, A minor 8, F major 16, G major 16 -
                      the section lengths in the hook's rhythm, the key journey itself a I vi IV V -> I cadence
The coda sounds the scales together: the hook in the piano every bar (x1), as a sustained bass + cello line (x4) and as
a choir line in octaves (x16: C 6 bars, A 2, F 4, G 4); all of them arrive on G in the last bar and resolve to C.

Sound: the pop_band preset's rhythm section (Chart Kit + tonic sub, perc, Growlybass, plate / bright hall / echo, glued
master) without its keys / pluck / lead; the hook on the hero piano (hero/piano_pop, played by the pianist) with a DX
glass layer faded in for the final statements; VPO strings, violins (the hook's inversion as a descant), a solo cello
(played by the bow player), the VPO mixed choir, a soft Juno pad.

Build: python -m agentsound build songs/matryoshka [--section chorus4]
"""
from agentsound import *
from agentsound import bands, bassist, drummer, hornist, mastering, pianist
from agentsound.humanize import touch

BPM = 100
ANALYSIS = {'profile': 'pop'}
METADATA = {'title': 'Matryoshka', 'artist': 'AgentSound', 'album': 'Self-Similar', 'genre': 'Pop', 'year': 2026,
            'comment': 'One four-note hook (C A F G) as melody, as harmony and as the key journey - all three at once '
                       'in the coda'}
COVER = {'style': 'pop', 'title': 'MATRYOSHKA', 'subtitle': 'AgentSound', 'seed': 1646}

RHYTHM = (1.5, 0.5, 1.0, 1.0)       # the hook's rhythm in beats (x1); x4 = the chord lengths in beats


def cyc(a, b, c, d, scale=4):
    """One harmony cycle: the four chords in the hook's rhythm at `scale` (x4 = 1.5 + 0.5 + 1 + 1 bars)."""
    return ' '.join(f'{ch}:{r * scale / 4:g}' for ch, r in zip((a, b, c, d), RHYTHM))


# ------------------------------------------------------------------ melodies (degrees of each section's key)
# Octave 4: degree 8 = the tonic an octave above the key's octave-4 tonic (C major: 8 = C5, 15 = C6).
HOOK = '8:1/4. 6:1/8 4:1/4 5:1/4'                   # the four notes (degree form 1-6-4-5 of each key)
# the chorus cycle (4 bars over I vi IV V): the hook, a falling answer, the hook from the 6th, a lift into the next
CH = ['15:1/4. 13:1/8 11:1/4 12:1/4',               # C6 A5 F5 G5       the hook
      '17:1/4. 16:1/8 15:1/4 13:1/4',               # E6 D6 C6 A5       the answer lands on the vi
      '13:1/4. 11:1/8 9:1/4 10:1/4',                # A5 F5 D5 E5       the hook from A (= the minor key's hook)
      '12:1/4. 13:1/8 14:1/2']                      # G5 A5 B5          up into the next C6
CH2 = ['15:1/4. 13:1/8 11:1/4 12:1/4',
       '17:1/4. 16:1/8 15:1/4 17:1/4',              # E6 D6 C6 E6       (varied: stays up)
       '13:1/4. 11:1/8 10:1/4 9:1/4',               # A5 F5 E5 D5
       '12:1/2. r:1/4']                             # G5 held: the half cadence
# the big choruses: the upward-leap form of the hook (1 -> 6 up a sixth), one octave lower in the degrees
UP = ['8:1/4. 13:1/8 11:1/4 12:1/4',                # F: F5 D6 Bb5 C6 / G: G5 E6 C6 D6
      '10:1/4. 9:1/8 8:1/4 6:1/4',                  # A5 G5 F5 D5 (the answer on the vi)
      '13:1/4. 11:1/8 9:1/4 10:1/4',                # D6 Bb5 G5 A5 (the hook from the 6th)
      '9:1/4. 10:1/8 12:1/2']                       # G5 A5 C6: up into the next
UP2 = ['8:1/4. 13:1/8 11:1/4 12:1/4',
       '10:1/4. 9:1/8 8:1/4 10:1/4',
       '13:1/4. 11:1/8 10:1/4 9:1/4']
# the verse: the hook's diatonic inversion (steps +2 +2 -1: C E G F), a rising question, in the hook's rhythm
VERSE = ['5:1/4. 7:1/8 9:1/4 8:1/4',                # G4 B4 D5 C5
         '10:1/4. 9:1/8 8:1/2',                     # E5 D5 C5
         '6:1/4. 8:1/8 10:1/4 9:1/4',               # A4 C5 E5 D5
         '7:1/2. r:1/4',                            # B4 (breath)
         '5:1/4. 7:1/8 9:1/4 10:1/4',               # G4 B4 D5 E5  (reaching higher)
         '11:1/4. 10:1/8 8:1/2',                    # F5 E5 C5
         '8:1/4. 10:1/8 12:1/4 11:1/4',             # C5 E5 G5 F5  (the exact inversion)
         '9:1/2 r:1/2']                             # D5


def bars(lst):
    return ' | '.join(lst)


# the mix engineer's moves (MIX.md; python -m agentsound mix): the plan's trims (drums back, the bed a little back,
# the violins ducked under the piano) + the rides the concept needs: the cello is the voice of the minor section's
# first cycle and of the coda's x4 line, the choir carries the coda's x16 line - both must be heard there
MIX = {
    'trim': {'drums': -2.5, 'perc': -2.5, 'bass': 1.5, 'cello': 0.7, 'choir': -0.5, 'pad': -0.5, 'strings': -0.5,
             'violins': -0.5},
    'ride': {
        'cello': {'minor': 5.0, 'coda': 2.0},
        'choir': {'chorus4': -2.0, 'coda': 6.0, 'end': 4.0},     # A&R: the x16 line must read
        'violins': {'verse2': -3.0, 'chorus4': -1.5},
        'strings': {'chorus1': 1.5, 'verse2': -1.5, 'chorus2': 1.5, 'chorus3': 1.5, 'chorus4': -1.0},
        'bass': {'verse1': -2.0, 'build': -2.0, 'minor': -1.5, 'chorus2': 1.0, 'chorus3': 1.5, 'chorus4': 2.0},
    },
    'eq': {'pad': [{'freq': 1200.0, 'gain': -2.0, 'q': 0.9}],        # pad vs piano in the mids (verse1)
           'strings': [{'freq': 450.0, 'gain': -2.0, 'q': 1.0}],   # strings vs choir in the low mids (end)
           'cello': [{'freq': 450.0, 'gain': -2.0, 'q': 1.0}]},    # cello vs piano in the low mids (minor)
    'duck': [{'targets': ['violins'], 'key': 'piano', 'depth': 2.0, 'threshold': -36.0, 'attack': 15.0, 'hold': 60.0,
              'release': 260.0}],
}


def build() -> Song:
    s = Song('Matryoshka', tempo=BPM, key='C major', seed=1646, tail=7.0)
    C, Am, F, G = Key('C major'), Key('A minor'), Key('F major'), Key('G major')

    # ------------------------------------------------------------------ harmony (the hook's roots, x4)
    P_intro = C.prog(cyc('Cadd9', 'Am7', 'Fmaj7', 'Gsus4'))
    P_v1 = C.prog(cyc('C', 'Am7', 'Fmaj7', 'G') + ' ' + cyc('Cadd9', 'Am', 'F', 'Gsus4'))
    P_build = C.prog(cyc('C', 'Am', 'F', 'G', scale=2) + ' ' + cyc('C', 'Am', 'F', 'G', scale=1) + ' Gsus4:0.5 G:0.5')
    P_ch1 = C.prog(cyc('C', 'Am', 'F', 'G') + ' ' + cyc('C', 'Am7', 'Fmaj7', 'G'))
    P_turn = C.prog('C:1.5 Am:0.5 F:1 G:0.5 E7/G#:0.5')
    P_min = Am.prog(cyc('Am', 'F', 'Dm', 'E') + ' Am:1.5 Fmaj7:0.5 Dm:1 E:0.5 C7/E:0.5')
    P_v2 = F.prog(cyc('F', 'Dm7', 'Bbmaj7', 'C') + ' ' + cyc('Fadd9', 'Dm', 'Bb', 'Csus4'))
    P_ch2 = F.prog(cyc('F', 'Dm', 'Bb', 'C') + ' F:1.5 Dm:0.5 Bb:1 C:0.5 D:0.5')
    P_ch3 = G.prog(cyc('G', 'Em', 'C', 'D') + ' ' + cyc('G', 'Em7', 'Cadd9', 'D'))
    P_ch4 = G.prog(cyc('G', 'Em', 'C', 'D') + ' G:1.5 Em7:0.5 Cadd9:1 Dm7:0.5 G7:0.5')
    # the coda: the bass's x4 cycles under the choir's x16 line (C C | C A | F F | G G): the chords take the choir's
    # note in (Gsus4 under C, Gadd9 under A, F/C Dm/A G7 under F, Am7 Fadd9 under G)
    P_coda = C.prog(cyc('C', 'Am', 'F', 'Gsus4') + ' ' + cyc('C', 'Am', 'F', 'Gadd9') + ' '
                    + cyc('F/C', 'Dm/A', 'F', 'G7') + ' ' + cyc('C', 'Am7', 'Fadd9', 'G'))

    # ------------------------------------------------------------------ form: 86 bars (~3:27)
    intro = s.section('intro', 4, prog=P_intro)        # the hook on the piano alone (C)
    verse1 = s.section('verse1', 8, prog=P_v1)         # I. C major (24 bars): the inversion as the verse tune
    build_ = s.section('build', 4, prog=P_build)       #    the harmony zooms in: the cycle at x2, then x1, a breath
    chorus1 = s.section('chorus1', 8, prog=P_ch1)      #    the hook, high
    turn = s.section('turn', 4, prog=P_turn)           #    post-chorus, G E7/G# into A minor
    minor = s.section('minor', 8, prog=P_min)          # II. A minor (8 bars): the cello sings the hook, then the piano
    verse2 = s.section('verse2', 8, prog=P_v2)         # III. F major (16 bars): the verse tune + a descant (x4 on top)
    chorus2 = s.section('chorus2', 8, prog=P_ch2)      #    the upward-leap hook; C D into G
    chorus3 = s.section('chorus3', 8, prog=P_ch3)      # IV. G major (16 bars): the climax
    chorus4 = s.section('chorus4', 8, prog=P_ch4)      #    + choir, the inversion descant, the glass layer; Dm7 G7 home
    coda = s.section('coda', 16, prog=P_coda)          # the revelation: x1 + x4 + x16 at once, converging
    end = s.section('end', 2, prog=C.prog('C:2'))      # one C chord
    s.ritardando((coda.bar(14), end.start), to=0.86, a_tempo=False)
    # ------------------------------------------------------------------ the band
    b = bands.pop_band(s, without=('keys', 'pluck', 'lead'))
    kit, perc, bass, pad = b.drums, b.perc, b.bass, b.pad
    hall, plate, echo = b.buses['hall'], b.buses['plate'], b.buses['echo']
    strings = s.track('strings', 'sampled/strings', gain_db=-5, sends={hall: -8},
                      fx=[fx.eq({'hp.freq': 90, 'peak1.freq': 420, 'peak1.gain': -2.5, 'peak1.q': 0.9}),
                          fx.width(width=1.5)])
    violins = s.track('violins', 'sampled/violins', gain_db=-6, pan=-0.35, sends={hall: -6},
                      fx=[fx.eq({'hp.freq': 200, 'peak3.freq': 3200, 'peak3.gain': -2.0})])
    # sound design pass 1: the cello sat over the piano (-16.5 vs -17.3 LUFS) and owned 29 % of the low mids - a
    # voice beside the hook, not over it: -7 dB, high-passed under its lowest note, the 300 Hz box out
    cello = s.track('cello', 'sampled/solo_cello', gain_db=-10, pan=0.3, sends={hall: -8},
                    fx=[fx.eq({'hp.freq': 75, 'peak1.freq': 320, 'peak1.gain': -3.0, 'peak1.q': 0.9})])
    # the Growlybass at the preset's pop level (-17.5 LUFS) sat 4 dB over the hero piano and masked its mids
    bass.gain_db -= 5.0
    bass.add_fx(fx.eq({'peak2.freq': 1000, 'peak2.gain': -3.0, 'peak2.q': 0.8}))
    bass.fx['ducker'].set(depth=10, hold=40)            # the kick owns its first ~100 ms (build: sub masking)
    pad.add_fx(fx.width(name='pw', width=1.2, monobass=150))   # choruses read 'narrow': the floor wider (1.5: out of phase)
    choir = s.track('choir', 'sampled/choir_mixed', gain_db=-6, sends={hall: -5},
                    fx=[fx.eq({'hp.freq': 120, 'peak1.freq': 350, 'peak1.gain': -2.0})])

    # the hook: the hero piano (bright high Salamander), a DX glass layer an octave up for the final statements
    piano = hero(s.track('piano', 'hero/piano_pop'), genre='pop', bed=[strings, pad, choir],
                 competitors=[violins], sections=[chorus1, chorus2, chorus3, chorus4, coda])
    piano.instrument = piano.instrument.but(layers=list(piano.instrument.params['layers']) + [
        layer('synthwave/arp_glass', 'glass', transpose=12, level=-40, bend=False, pedal=True, keys=('E5', 'C8'),
              keyfade=4)])
    piano.automate('instrument.layers.glass.level', [(0, -40), (chorus4.start - 0.5, -40),
                                                     (chorus4.start, -16, 'smooth'), (coda.start - 1, -16),
                                                     (coda.start, -30, 'smooth'), (coda.bar(8), -30),
                                                     (coda.bar(12), -14, 'smooth')])
    piano.gain_db -= 2.0                                # peaked +0.9 dBFS before the master
    # A&R round 1: the choruses read narrow (width 9-15 %): the melody layer opened from the hero's 0.4
    piano.instrument = piano.instrument.but(**{'layers.high.width': 0.7})
    piano.add_fx(fx.eq({'peak1.freq': 300, 'peak1.gain': -2.0, 'peak1.q': 0.8}))   # 52 % of the low mids

    # ------------------------------------------------------------------ the hook instrument, played by a pianist
    ORN = {'restrike': 2.5, 'roll': 2.0, 'turn': 0.8, 'crush': 0.6, 'mordent': 0.4, 'trill': 0.3}
    HOOKDEV = {'octave': 2.5, 'sixths': 1.8, 'thirds': 1.5, 'close': 1.0, 'drop2': 0.8, 'single': 0.4}
    SOFTDEV = {'guide': 1.5, 'thirds': 1.5, 'sixths': 1.0, 'single': 1.5}
    # the melody on top leads: the octave / sixth / third doubles under it at 78 %
    pp = pianist.Player(piano, bpm=BPM, style='ballad', ornaments=ORN, doubles=0.78, log=print)

    # intro: the chorus melody's first half, an octave down and alone - the hook in the first seconds
    pp.play(bars(CH), P_intro, intro, key=C, lo=48, hi=78, octave=3, style='sparse', density=0.35, seed=1,
            devices=SOFTDEV, lh='tenths')
    # I. C major
    pp.play(bars(VERSE), P_v1, verse1, key=C, lo=52, hi=88, style='sparse', density=0.4, seed=2, devices=SOFTDEV,
            lh='shell')
    # the build: the hook at x2 (the harmony's scale) in octaves, then at x1 (the band hits it), then G held
    zoom = C.motif('8:3 6:1 4:2 5:2 | 15:1/4. 13:1/8 11:1/4 12:1/4 | 12:1/2 r:1/2').clip(octave=4, gate=0.95)
    pp.play(zoom, P_build, build_, key=C, lo=66, hi=104, style='straight', density=0.55, seed=3,
            devices={'octave': 3.0, 'sixths': 1.0}, until=15.0)
    pp.play(bars(CH + CH2), P_ch1, chorus1, key=C, lo=68, hi=108, density=0.5, seed=4, devices=HOOKDEV)
    turn_line = bars([CH[0], '10:1/4. 9:1/8 8:1/4 6:1/4', '6:1/4. 4:1/8 2:1/4 3:1/4', '7:1/2 #5:1/2'])
    pp.play(turn_line, P_turn, turn, key=C, lo=56, hi=92, style='sparse', density=0.4, seed=5, devices=SOFTDEV,
            lh='tenths')
    # II. A minor: the cello sings the hook (cycle 1); the piano takes it back high (cycle 2), G# melting to G
    minor_piano = bars(['r:4', 'r:4', 'r:2 10:1/4 12:1/4', '#7:1/2 r:1/2',
                        HOOK, '10:1/4. 9:1/8 8:1/4 6:1/4', '11:1/4. 9:1/8 8:1/4 6:1/4', '#7:1/2 7:1/2'])
    pp.play(minor_piano, P_min, minor, key=Am, lo=46, hi=90, density=0.45, seed=6, lh='tenths',
            devices={'sixths': 1.5, 'thirds': 1.5, 'drop2': 1.0, 'single': 0.8})
    # III. F major
    pp.play(bars(VERSE), P_v2, verse2, key=F, lo=56, hi=92, style='sparse', density=0.45, seed=7, devices=SOFTDEV,
            lh='shell')
    ch2 = bars(UP + UP2 + ['12:1/2 C6:1/4 F#5:1/4'])        # the last bar: C, then the leading tone of G
    pp.play(ch2, P_ch2, chorus2, key=F, lo=70, hi=110, density=0.55, seed=8, devices=HOOKDEV)
    # IV. G major: the climax
    pp.play(bars(UP + UP2 + ['12:1/4. 11:1/8 10:1/2']), P_ch3, chorus3, key=G, lo=74, hi=114, density=0.62, seed=9,
            devices=HOOKDEV)
    ch4 = bars(UP + UP2 + ['C6:1/4. A5:1/8 B5:1/4 D6:1/4'])  # over Dm7 G7: C A | B D -> the coda's C6
    pp.play(ch4, P_ch4, chorus4, key=G, lo=78, hi=120, density=0.7, seed=10, climax=True, devices=HOOKDEV)
    # the coda: the literal hook in every bar (x1) - first low and intimate, then up, then in octaves
    pp.play(bars([HOOK] * 4), C.prog(cyc('C', 'Am', 'F', 'Gsus4')), coda, key=C, lo=50, hi=80,
            style='sparse', density=0.35, seed=11, devices=SOFTDEV, lh='tenths')
    pp.play(bars([CH[0]] * 4), C.prog(cyc('C', 'Am', 'F', 'Gadd9')), coda.bar(4), key=C, lo=60, hi=94,
            density=0.45, seed=12, devices=HOOKDEV)
    pp.play(bars([CH[0]] * 8), C.prog(cyc('F/C', 'Dm/A', 'F', 'G7') + ' ' + cyc('C', 'Am7', 'Fadd9', 'G')),
            coda.bar(8), key=C, lo=72, hi=118, density=0.62, seed=13, climax=True, devices=HOOKDEV)
    last = Clip([(0, 8, p, v) for p, v in (('C2', 70), ('G2', 62), ('E3', 60), ('C4', 64), ('G4', 66), ('E5', 70),
                                           ('C6', 84))], length=8).strum(ms=45, bpm=BPM * 0.86)
    piano.play(last, end)
    pp.pedal(before=end.start - 0.05, then=[(end.start - 0.02, 0.0), (end.start + 0.05, 1.0)])

    # ------------------------------------------------------------------ the cello (a bow player): the hook in A minor,
    # then the x4 line in the coda
    hmem = hornist.Memory()
    cl1 = Am.motif(bars([HOOK, '10:1/4. 9:1/8 8:1/4 6:1/4', '6:1/4. 4:1/8 2:1/4 3:1/4', '#7:1/2 5:1/2'])).clip(
        octave=3, gate=0.97)
    cl2 = Am.motif('5:2 8:2 | 8:2 6:2 | 4:2 6:2 | #7:2 7:2').clip(octave=2, gate=0.97)   # the counter under the piano
    perf = hornist.arrange(touch(cl1, 64, 104) + touch(cl2, 40, 66), BPM, family='strings', style='ballad', section='verse',
                           peaks=(0, 6, 12), seed=21, memory=hmem, at=minor)
    perf.place(cello, minor)
    # the coda: the hook x4 (C 6 beats, A 2, F 4, G 4) an octave above the bass, four times, growing
    x4 = Clip([(0, 6, 'C4', 72), (6, 2, 'A3', 64), (8, 4, 'F3', 70), (12, 4, 'G3', 74)], length=16)
    cx = x4 + x4.velocity(1.08) + x4.velocity(1.14) + x4.velocity(1.22)
    perf2 = hornist.arrange(cx, BPM, family='strings', style='ballad', section='outro', peaks=(0, 16, 32, 48),
                            seed=22, memory=hmem, at=coda)
    perf2.place(cello, coda)
    cello.note('C4', end.start, 8, 86)
    print('hornist (cello):', perf.summary(), '|', perf2.summary())
    # A&R round 1: the counter-line of the minor section's second cycle plays UNDER the piano's hook (the section's
    # +5 dB ride is for the cello's own cycle)
    cello.automate('gainDb', [(minor.bar(4) - 0.5, 0), (minor.bar(4), -8, 'smooth'), (minor.end - 0.5, -8),
                              (minor.end, 0, 'smooth')])

    # ------------------------------------------------------------------ bass: the bassist (pop), locked to the hook-rhythm kick
    bp = bassist.Player(bass, bpm=BPM, style='pop', kick='x.....x.x.......')   # the hook's onsets 1, &2, 3 (its 4th
    bp.play(P_v1, verse1, 'verse', key=C, seed=1)                                # note is the backbeat)
    bp.play(P_build, build_, 'pre', key=C, seed=2)
    bp.play(P_ch1, chorus1, 'chorus', key=C, seed=3)
    bp.play(P_turn, turn, 'verse', key=C, seed=4)
    bp.play(P_min, minor, 'break', key=Am, seed=5, density=0.3)
    bass.clear(minor.start + 0.5, minor.bar(4))          # cycle 1: the cello alone over piano and strings
    bp.play(P_v2, verse2, 'verse', key=F, seed=6)
    bp.play(P_ch2, chorus2, 'chorus', key=F, seed=7)
    bp.play(P_ch3, chorus3, 'chorus', key=G, seed=8)
    bp.play(P_ch4, chorus4, 'chorus', key=G, seed=9)
    # the coda: the hook x4 as sustained roots (the scale made audible), then the final C
    bx = Clip([(0, 5.9, 'C2', 90), (6, 1.9, 'A1', 82), (8, 3.9, 'F1', 88), (12, 3.9, 'G1', 92)], length=16)
    bass.play(bx * 4, coda)
    bass.note('C2', end.start, 7.5, 96)

    # ------------------------------------------------------------------ drums: the drummer (pop), kick locked to the bass
    part = drummer.arrange(s, style='pop', density=0.5, seed=5, kit=b.drums, ending='hit', lock=bass, plan={
        'intro': {'role': 'intro', 'energy': 0.2},
        'verse1': {'role': 'verse', 'energy': 0.36, 'mode': 'half'},
        'build': {'role': 'pre'},
        'chorus1': {'role': 'chorus'},
        'turn': {'role': 'post', 'energy': 0.6},
        'minor': {'role': 'bridge', 'energy': 0.3, 'mode': 'half'},
        'verse2': {'role': 'verse', 'energy': 0.45},
        'chorus2': {'role': 'chorus'},
        'chorus3': {'role': 'chorus', 'energy': 0.93},
        'chorus4': {'role': 'chorus', 'energy': 1.0},
        'coda': {'role': 'outro', 'energy': 0.45, 'mode': 'half'},
        'end': {'role': 'end'},
    })
    part.play(kit)
    kit.clear(0, intro.end)
    kit.clear(minor.start + 0.25, minor.bar(4))
    kit.clear(coda.start + 0.25, coda.bar(8))
    print('drummer:', part.summary())

    # perc: shaker in verse 2, tambourine 8ths + claps in the big choruses
    perc.loop(drums({70: 'x.xxx.xxx.xxx.xx'}, vel=62), verse2)
    for sec, v in ((chorus2, 80), (chorus3, 90), (chorus4, 96)):
        perc.loop(drums({'tamb': 'x.x.x.x.x.x.x.x.', 'clap': '....x.......x...'}, vel=v).vel_pattern(
            [1.1, 0.75, 0.95, 0.75], grid='1/8'), sec)
    perc.loop(drums({'tamb': '....x.......x...'}, vel=70), coda.bar(8), bars=8)

    # ------------------------------------------------------------------ pad, strings, choir, violins
    # held chords breathe in 4-bar arches (clip.arch: rise into bar 3, relax) in the verses and choruses
    arched = (verse1, chorus1, verse2, chorus2, chorus3, chorus4)
    pad.chords(s.sections, voicing='spread', register=('C3', 'C5'), then=dict.fromkeys(arched, Clip.arch),
               vel={intro: 58, verse1: 66, build_: 72, chorus1: 78, turn: 70, minor: 60, verse2: 68, chorus2: 78,
                    chorus3: 82, chorus4: 84, coda: 64, end: 72}, crescendo={coda: (0.7, 1.15)})
    pad.automate('instrument.cutoff', exp_ramp(intro.start, verse1.start, 700, 2600), hold(verse1.start, end.end, 2800))

    big = (chorus3, chorus4, end)
    strings.chords(chorus1, turn, minor, verse2, chorus2, chorus3, chorus4, coda, end, voices={'*': 4, **dict.fromkeys(big, 5)},
                   register={'*': ('G3', 'E5'), minor: ('E3', 'C5'), chorus3: ('G3', 'G5'), chorus4: ('G3', 'G5'),
                             end: ('C3', 'G5')},
                   vel={chorus1: 58, turn: 64, minor: 58, verse2: 62, chorus2: 74, chorus3: 82, chorus4: 88, coda: 60,
                        end: 84}, then=dict.fromkeys(arched, Clip.arch), bars={chorus1: (0, 4), coda: 4},
                   crescendo={turn: (1.0, 0.8), minor: (0.8, 1.1), coda: (0.75, 1.3)})
    strings.chords(chorus1, register=('G3', 'E5'), voices=4, vel=68, then=Clip.arch, bars=4)

    # violins: the hook x4 as a descant in verse 2 (F D Bb C: the chord roots on top), the inversion x4 in chorus 4
    vd = Clip([(0, 6, 'F5', 64), (6, 2, 'D5', 60), (8, 4, 'Bb4', 64), (12, 4, 'C5', 68)], length=16)
    vi = Clip([(0, 6, 'G5', 74), (6, 2, 'B5', 70), (8, 4, 'D6', 84), (12, 4, 'C6', 78)], length=16)
    vmem = hornist.Memory()
    for line, at, sec in ((touch(vd + vd, 56, 92), verse2, 'verse'),
                          (touch(vi + vi.slice(0, 12), 66, 108), chorus4, 'chorus')):
        vp = hornist.arrange(line, BPM, family='strings', style='ballad', section=sec, peaks=(8, 24), seed=31,
                             memory=vmem, at=at)
        vp.place(violins, at)

    # the choir: chorus 4's chords, then the x16 line in octaves (sopranos + tenors): C 6 bars, A 2, F 4, G 4 -> C
    choir.play(P_ch4.block(register=('G3', 'A4'), voices=4, vel=70), chorus4)
    line16 = [(0, 24, 'C'), (24, 8, 'A'), (32, 16, 'F'), (48, 16, 'G')]
    for t, d, n in line16:                  # sung in 2-bar breaths: the line re-articulated, never a 14 s loop
        for k, b0 in enumerate(range(0, d, 8)):
            v = 66 + 4 * k + (6 if b0 == 0 else 0)                 # each new note leans in, the breaths grow
            choir.note(f'{n}5', coda.start + t + b0, min(8, d - b0) - 0.35, v)
            choir.note(f'{n}3', coda.start + t + b0, min(8, d - b0) - 0.35, v - 4)
    choir.note('C5', end.start, 8, 80).note('C4', end.start, 8, 74).note('G4', end.start, 8, 66).note('E4', end.start, 8, 62)
    choir.automate('instrument.dynamics', [(chorus4.start, 0.35), (chorus4.bar(4), 0.6, 'smooth'),
                                           (chorus4.end - 0.5, 0.7, 'smooth'), (coda.start, 0.45),
                                           (coda.bar(8), 0.55, 'smooth'), (coda.bar(15), 0.85, 'smooth'),
                                           (end.start + 6, 0.7, 'smooth')])

    # ------------------------------------------------------------------ transitions and production moves
    s.breath(before=chorus1, tracks=[bass, pad, strings, perc], cut=False)    # a one-beat breath before the first chorus
    s.sidechain(strings, key=kit, pitches='kick', depth=3, release=260)
    for t in (pad, strings, choir, cello):
        t.automate('gainDb', [(end.start + 2, 0), (end.end + 6, -24, 'smooth')])

    # ------------------------------------------------------------------ master (MASTER.md; python -m agentsound master)
    # the sub is the pop profile's weak band (-4.1 dB): +1.5 dB of it in the bass, +2 dB low shelf on the master (the
    # plan asked +3); the 1.2 kHz mid bump -1.8 dB; ceiling -1.2 for -1 dBTP
    bass.add_fx(fx.eq({'low.freq': 60, 'low.gain': 1.5}))
    mastering.apply(s, eq={'low.freq': 60, 'low.gain': 2.0, 'low.q': 0.7071, 'peak1.freq': 1250, 'peak1.gain': -1.8,
                           'peak1.q': 0.7}, limiter={'ceiling': -1.2, 'release': 120.0}, loudness_change=+0.5)
    # the energy arc: the limiter's drive per section (dB on the chain's drive, gliding over a beat into each): the
    # verses and the minor section hold back, the choruses climb, the coda starts quiet (the revelation) and grows
    # into its last bars
    s.master.lane('fx.limiter.gain', {intro: 0.0, verse1: -1.5, build_: -0.6, chorus1: 0.6, turn: -0.3, minor: -1.3,
                                      verse2: -0.6, chorus2: 0.3, chorus3: 0.5, chorus4: 0.8,
                                      coda: [(0, -1.2), (8, -1.2, 'linear'), (15, 0.6, 'smooth')], end: 0.3},
                  base=s.master.fx['limiter'].params['gain'], glide=1)
    return s
