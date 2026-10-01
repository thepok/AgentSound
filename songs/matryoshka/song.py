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
import math

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

    # ------------------------------------------------------------------ form: 86 bars (~3:27)
    intro = s.section('intro', 4)        # the hook on the piano alone (C)
    verse1 = s.section('verse1', 8)      # I. C major (24 bars): the inversion as the verse tune
    build_ = s.section('build', 4)       #    the harmony zooms in: the cycle at x2, then x1 (band hits), a breath
    chorus1 = s.section('chorus1', 8)    #    the hook, high
    turn = s.section('turn', 4)          #    post-chorus, G E7/G# into A minor
    minor = s.section('minor', 8)        # II. A minor (8 bars): the cello sings the hook, then the piano
    verse2 = s.section('verse2', 8)      # III. F major (16 bars): the verse tune + a descant (the hook x4 on top)
    chorus2 = s.section('chorus2', 8)    #    the upward-leap hook; C D into G
    chorus3 = s.section('chorus3', 8)    # IV. G major (16 bars): the climax
    chorus4 = s.section('chorus4', 8)    #    + choir, the inversion descant, the glass layer; Dm7 G7 home
    coda = s.section('coda', 16)         # the revelation: x1 + x4 + x16 at once, converging
    end = s.section('end', 2)            # one C chord
    s.ritardando((coda.bar(14), end.start), to=0.86, a_tempo=False)

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
    P_end = C.prog('C:2')

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
    for f in bass.fx:                                   # the kick owns its first ~100 ms (build: sub masking)
        if f.type == 'ducker':
            f.params.update(depth=10, hold=40)
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
    pmem = pianist.Memory()
    pedal_pts = []

    def top_leads(clip, factor):
        """The melody on top leads: the notes struck under the top note (octave / sixth / third doubles) softer."""
        soft, group = set(), []
        for n in sorted(clip, key=lambda n: n.start) + [None]:
            if group and (n is None or n.start - group[0].start > 0.06):
                top = max(g.pitch for g in group)
                soft.update((g.start, g.pitch) for g in group if g.pitch < top)
                group = []
            if n is not None:
                group.append(n)
        return clip.map(lambda n: n._replace(vel=max(1, round(n.vel * factor))) if (n.start, n.pitch) in soft else n)

    ORN = {'restrike': 2.5, 'roll': 2.0, 'turn': 0.8, 'crush': 0.6, 'mordent': 0.4, 'trill': 0.3}
    HOOKDEV = {'octave': 2.5, 'sixths': 1.8, 'thirds': 1.5, 'close': 1.0, 'drop2': 0.8, 'single': 0.4}
    SOFTDEV = {'guide': 1.5, 'thirds': 1.5, 'sixths': 1.0, 'single': 1.5}

    def play_piano(spec, k, prog, at, *, lo, hi, octave=4, style='ballad', density=0.5, climax=False,
                   devices=None, lh=None, seed=0, lead_in=False, doubles=0.78, until=None):
        m = k.motif(spec).clip(octave=octave, gate=0.95) if isinstance(spec, str) else spec
        m = touch(m, lo, hi)
        arr = pianist.arrange(m, prog, bpm=BPM, key=k, style=style, density=density, seed=seed, climax=climax,
                              devices=devices, lh=lh, memory=pmem, at=at, lead_in=lead_in, ornaments=ORN)
        rh, lh_ = top_leads(arr.rh, doubles), arr.lh
        if until is not None:
            rh = rh.slice(0, until)
            lh_ = lh_.slice(0, until) if len(lh_) else lh_
        piano.play(rh, at)
        if len(lh_):
            piano.play(lh_, at)
        t0 = at.start if hasattr(at, 'start') else at
        pts = arr.pedal(prog, at)
        if until is not None:
            pts = [p for p in pts if p[0] < t0 + until] + [(t0 + until, 0.0)]
        pedal_pts.extend(pts)
        print(f'pianist {getattr(at, "name", at)}: {arr!r}')
        return arr

    # intro: the chorus melody's first half, an octave down and alone - the hook in the first seconds
    play_piano(bars(CH), C, P_intro, intro, lo=48, hi=78, octave=3, style='sparse', density=0.35, seed=1,
               devices=SOFTDEV, lh='tenths')
    # I. C major
    play_piano(bars(VERSE), C, P_v1, verse1, lo=52, hi=88, style='sparse', density=0.4, seed=2, devices=SOFTDEV, lh='shell')
    # the build: the hook at x2 (the harmony's scale) in octaves, then at x1 (the band hits it), then G held
    zoom = C.motif('8:3 6:1 4:2 5:2 | 15:1/4. 13:1/8 11:1/4 12:1/4 | 12:1/2 r:1/2').clip(octave=4, gate=0.95)
    play_piano(zoom, C, P_build, build_, lo=66, hi=104, style='straight', density=0.55, seed=3,
               devices={'octave': 3.0, 'sixths': 1.0}, until=15.0)
    play_piano(bars(CH + CH2), C, P_ch1, chorus1, lo=68, hi=108, density=0.5, seed=4, devices=HOOKDEV)
    turn_line = bars([CH[0], '10:1/4. 9:1/8 8:1/4 6:1/4', '6:1/4. 4:1/8 2:1/4 3:1/4', '7:1/2 #5:1/2'])
    play_piano(turn_line, C, P_turn, turn, lo=56, hi=92, style='sparse', density=0.4, seed=5, devices=SOFTDEV, lh='tenths')
    # II. A minor: the cello sings the hook (cycle 1); the piano takes it back high (cycle 2), G# melting to G
    minor_piano = bars(['r:4', 'r:4', 'r:2 10:1/4 12:1/4', '#7:1/2 r:1/2',
                        HOOK, '10:1/4. 9:1/8 8:1/4 6:1/4', '11:1/4. 9:1/8 8:1/4 6:1/4', '#7:1/2 7:1/2'])
    play_piano(minor_piano, Am, P_min, minor, lo=46, hi=90, style='ballad', density=0.45, seed=6, lh='tenths',
               devices={'sixths': 1.5, 'thirds': 1.5, 'drop2': 1.0, 'single': 0.8})
    # III. F major
    play_piano(bars(VERSE), F, P_v2, verse2, lo=56, hi=92, style='sparse', density=0.45, seed=7, devices=SOFTDEV, lh='shell')
    ch2 = bars(UP + UP2 + ['12:1/2 C6:1/4 F#5:1/4'])        # the last bar: C, then the leading tone of G
    play_piano(ch2, F, P_ch2, chorus2, lo=70, hi=110, density=0.55, seed=8, devices=HOOKDEV)
    # IV. G major: the climax
    play_piano(bars(UP + UP2 + ['12:1/4. 11:1/8 10:1/2']), G, P_ch3, chorus3, lo=74, hi=114, density=0.62, seed=9, devices=HOOKDEV)
    ch4 = bars(UP + UP2 + ['C6:1/4. A5:1/8 B5:1/4 D6:1/4'])  # over Dm7 G7: C A | B D -> the coda's C6
    play_piano(ch4, G, P_ch4, chorus4, lo=78, hi=120, density=0.7, seed=10, climax=True, devices=HOOKDEV)
    # the coda: the literal hook in every bar (x1) - first low and intimate, then up, then in octaves
    play_piano(bars([HOOK] * 4), C, C.prog(cyc('C', 'Am', 'F', 'Gsus4')), coda, lo=50, hi=80, octave=4,
               style='sparse', density=0.35, seed=11, devices=SOFTDEV, lh='tenths')
    play_piano(bars([CH[0]] * 4), C, C.prog(cyc('C', 'Am', 'F', 'Gadd9')), coda.bar(4), lo=60, hi=94,
               density=0.45, seed=12, devices=HOOKDEV)
    play_piano(bars([CH[0]] * 8), C, C.prog(cyc('F/C', 'Dm/A', 'F', 'G7') + ' ' + cyc('C', 'Am7', 'Fadd9', 'G')),
               coda.bar(8), lo=72, hi=118, density=0.62, seed=13, climax=True, devices=HOOKDEV)
    last = Clip([(0, 8, p, v) for p, v in (('C2', 70), ('G2', 62), ('E3', 60), ('C4', 64), ('G4', 66), ('E5', 70),
                                           ('C6', 84))], length=8).strum(ms=45, bpm=BPM * 0.86)
    piano.play(last, end)
    pts = sorted({round(t, 4): (t, v) + tuple(c) for t, v, *c in pedal_pts}.values())
    pts = [p for p in pts if p[0] < end.start - 0.05] + [(end.start - 0.02, 0.0), (end.start + 0.05, 1.0)]
    piano.automate('instrument.pedal', [p[:2] if i == 0 else p for i, p in enumerate(pts)])

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
    bmem = bassist.Memory()
    KICK = 'x.....x.x.......'           # the hook's onsets 1, &2, 3 (its 4th note is the backbeat)

    def bline(prog, k, at, part, seed, **kw):
        ln = bassist.arrange(prog, bpm=BPM, key=k, style='pop', part=part, kick=KICK, memory=bmem, at=at, seed=seed,
                             **kw)
        ln.place(bass, at)
        return ln

    bline(P_v1, C, verse1, 'verse', 1)
    bline(P_build, C, build_, 'pre', 2)
    bline(P_ch1, C, chorus1, 'chorus', 3)
    bline(P_turn, C, turn, 'verse', 4)
    bline(P_min, Am, minor, 'break', 5, density=0.3)
    bass.clear(minor.start + 0.5, minor.bar(4))          # cycle 1: the cello alone over piano and strings
    bline(P_v2, F, verse2, 'verse', 6)
    bline(P_ch2, F, chorus2, 'chorus', 7)
    bline(P_ch3, G, chorus3, 'chorus', 8)
    bline(P_ch4, G, chorus4, 'chorus', 9)
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
    def arc(c, depth=0.3):
        """A 4-bar arch on held chords (rise into bar 3, relax)."""
        return c.map(lambda n: n._replace(vel=max(30, min(120, round(
            n.vel * (1 - depth / 2 + depth * math.sin(math.pi * ((n.start % 16) / 16) ** 0.8)))))))

    sp = dict(voicing='spread', register=('C3', 'C5'))
    pad.play(P_intro.block(**sp, vel=58), intro)
    pad.play(arc(P_v1.block(**sp, vel=66)), verse1)
    pad.play(P_build.block(**sp, vel=72), build_)
    pad.play(arc(P_ch1.block(**sp, vel=78)), chorus1)
    pad.play(P_turn.block(**sp, vel=70), turn)
    pad.play(P_min.block(**sp, vel=60), minor)
    pad.play(arc(P_v2.block(**sp, vel=68)), verse2)
    pad.play(arc(P_ch2.block(**sp, vel=78)), chorus2)
    pad.play(arc(P_ch3.block(**sp, vel=82)), chorus3)
    pad.play(arc(P_ch4.block(**sp, vel=84)), chorus4)
    pad.play(P_coda.block(**sp, vel=64).crescendo(0.7, 1.15), coda)
    pad.play(P_end.block(**sp, vel=72), end)
    pad.automate('instrument.cutoff', exp_ramp(intro.start, verse1.start, 700, 2600), hold(verse1.start, end.end, 2800))

    sv = dict(register=('G3', 'E5'), voices=4)
    strings.play(arc(P_ch1.block(**sv, vel=58)).slice(0, 16), chorus1)
    strings.play(arc(P_ch1.block(**sv, vel=68)).slice(16, 32), chorus1.bar(4))
    strings.play(P_turn.block(**sv, vel=64).crescendo(1.0, 0.8), turn)
    strings.play(P_min.block(register=('E3', 'C5'), voices=4, vel=58).crescendo(0.8, 1.1), minor)
    strings.play(arc(P_v2.block(**sv, vel=62)), verse2)
    strings.play(arc(P_ch2.block(**sv, vel=74)), chorus2)
    strings.play(arc(P_ch3.block(register=('G3', 'G5'), voices=5, vel=82)), chorus3)
    strings.play(arc(P_ch4.block(register=('G3', 'G5'), voices=5, vel=88)), chorus4)
    strings.play(P_coda.block(**sv, vel=60).slice(16, 64).crescendo(0.75, 1.3), coda.bar(4))
    strings.play(P_end.block(register=('C3', 'G5'), voices=5, vel=84), end)

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
    for t in (bass, pad, strings, perc):
        t.clear(chorus1.start - 1, chorus1.start)          # a one-beat breath before the first chorus
    s.sidechain(strings, key=kit, pitches='kick', depth=3, release=260)
    for t in (pad, strings, choir, cello):
        t.automate('gainDb', [(end.start + 2, 0), (end.end + 6, -24, 'smooth')])

    # ------------------------------------------------------------------ master (MASTER.md; python -m agentsound master)
    # the sub is the pop profile's weak band (-4.1 dB): +1.5 dB of it in the bass, +2 dB low shelf on the master (the
    # plan asked +3); the 1.2 kHz mid bump -1.8 dB; ceiling -1.2 for -1 dBTP
    bass.add_fx(fx.eq({'low.freq': 60, 'low.gain': 1.5}))
    mastering.apply(s, eq={'low.freq': 60, 'low.gain': 2.0, 'low.q': 0.7071, 'peak1.freq': 1250, 'peak1.gain': -1.8,
                           'peak1.q': 0.7}, limiter={'ceiling': -1.2, 'release': 120.0}, loudness_change=+0.5)
    # the energy arc: the limiter's drive per section (dB on the chain's drive): the verses and the minor section
    # hold back, the choruses climb, the coda starts quiet (the revelation) and grows into its last bars
    base = next(f.params['gain'] for f in s.master.fx if f.type == 'limiter')
    drive = [(intro, 0.0), (verse1, -1.5), (build_, -0.6), (chorus1, 0.6), (turn, -0.3), (minor, -1.3),
             (verse2, -0.6), (chorus2, 0.3), (chorus3, 0.5), (chorus4, 0.8), (coda, -1.2), (end, 0.3)]
    pts = [(0, base + drive[0][1])]
    for sec, g in drive[1:]:
        pts += [(sec.start - 1, pts[-1][1]), (sec.start, base + g, 'smooth')]
        if sec is coda:
            pts += [(coda.bar(8), base + g), (coda.bar(15), base + 0.6, 'smooth')]
    s.master.automate('fx.limiter.gain', pts)
    return s
