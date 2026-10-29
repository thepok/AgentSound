"""Operation No Wi-Fi - the 128-second score for episode 2 of the Grandpa Konrad & Timo cartoon (Sockenkrieg series).

Same musical world as songs/sockenkrieg-theme: a wobbly theremin lead (sine + detuned triangle, glide, wide vibrato),
a bouncy plucked bass, light 808 drums, a spooky organ; D minor, ~120 BPM. Scored to picture: every chapter of the
episode is a section whose tempo is set so that its first downbeat lands exactly on the picture anchor (the clip start
times from ep2_couch/manifest.json + build/timeline.json; the song ends at the episode length, tail 0).

  sunday   0.000 -  27.423  14 bars ~122.5  boring rainy Sunday: no music, a lone clock tick creeps in, then a lazy,
                                           slightly out-of-tune low pad (A3); cut to silence right before the bang
  bang    27.423 -  53.491  13 bars ~119.7  B1 door BANG = orchestra hit + boom + crash, manic conspiracy groove
                                           (sparse under dialogue), stop-time for Timo's deadpan line 8, build to ...
  shrink  53.491 -  58.825   3 bars  135    C1 zap sweep down, a tiny plinky music-box version of the theme
  antcity 58.825 -  68.974   5 bars ~118.2  D1 mysterious: tiny snare march, pizzicato oom-pah, dark organ
  queen   68.974 -  92.849  12 bars ~120.6  E1 villain theme: diva harpsichord + buzzing bass, grows through the
                                           monologue (line 15) to the big WORLD hit (86.85 s), then tense
  fight   92.849 -  97.881   3 bars ~143    F1 action drums, theme fragments, snare build ... and CUT
  burp    97.881 - 102.299   2 bars         silence for the mega burp (line 18)
  slam   102.299 - 111.881   6 bars ~150    slam back in, action groove with theme stabs, build into ...
  home   111.881 - 120.775   4 bars ~108    the reverse-ray flash hit (line 21 end), warm major resolution of the theme
  sting  120.775 - 128.015   3 bars ~99     comic sting on the last burp (line 24), decays to silence

Build: python -m agentsound build songs/operation-no-wifi
"""
from agentsound import *
from agentsound import vamod

METADATA = {'title': 'Operation No Wi-Fi (Score)', 'artist': 'AgentSound', 'genre': 'Soundtrack', 'year': 2026,
            'comment': 'cartoon score to picture, episode 2, D minor, ~120 BPM, 128.0 s'}
ANALYSIS = {'profile': 'synthwave'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'OPERATION NO WI-FI', 'subtitle': 'AgentSound',
         'seed': 7}

# Picture anchors in seconds (ep2_couch/build/timeline.json spans + manifest clip offsets; line N = spans[N-1]).
T_BANG = 28.322584 - 0.9            # B1: line 4 start - 0.9 (door bang)
T_SHRINK = 52.090980 + 1.4          # C1: line 9 + 1.4 (shrink ray)
T_ANTS = 59.825188 - 1.0            # D1: line 11 - 1.0
T_QUEEN = 69.974418 - 1.0           # E1: line 13 - 1.0
T_WORLD = 77.252564 + 9.6           # line 15 (77.25 s) "...we take the WORLD!" - the word at ~9.6 s into the take
T_FIGHT = 93.049273 - 0.2           # F1: line 17 - 0.2
T_BURP = 97.881356                  # line 18 start: the mega burp (F2)
T_SLAM = 97.881356 + 4.417979       # line 18 end: slam back in
T_FLASH = 109.424335 + 2.456729     # line 21 end: the reverse-ray flash
T_STING = 120.774648                # line 24 start: the last burp
T_END = 128.014898                  # timeline total = episode length

# (name, start s, end s, bars): the tempo of each section is bars * 4 beats over its length
PLAN = [('sunday', 0.0, T_BANG, 14), ('bang', T_BANG, T_SHRINK, 13), ('shrink', T_SHRINK, T_ANTS, 3),
        ('antcity', T_ANTS, T_QUEEN, 5), ('queen', T_QUEEN, T_FIGHT, 12), ('fight', T_FIGHT, T_BURP, 3),
        ('burp', T_BURP, T_SLAM, 2), ('slam', T_SLAM, T_FLASH, 6), ('home', T_FLASH, T_STING, 4),
        ('sting', T_STING, T_END, 3)]


def mbar(section, n, beat=0.0):
    """Musical (1-based) bar n of a section: mbar(sec, 1) = its first downbeat."""
    return section.bar(n - 1, beat=beat)


def bpm_of(a, b, bars):
    return bars * 4 * 60.0 / (b - a)


# 4-bar spooky-goofy loop of the series: Dm | Dm | Eb (bII) | A7
PROG = ['Dm', 'Dm', 'Eb', 'A7']
ROOTS = {'Dm': 38, 'Eb': 39, 'A7': 33, 'Bb': 34, 'Gm': 31, 'C': 36}

# the series theme (phrase A of Sockenkrieg) and its answer
THEME_A = 'D5/2 F5/4 E5/8 D5/8 | A5/2. r/4 | Bb5/4 A5/4 G5/4 Bb5/4 | A5/1'
THEME_B = 'r/4 A5/4 C6/4 A5/4 | D6/2. r/4 | Eb6/4 D6/8 C6/8 Bb5/4 G5/4 | A5/2 C#5/2'


def bass_bar(sym, bar_start, vel=1.0):
    """Bouncy octave pluck (the series bass): root, octave, root, fifth/octave pickups."""
    r = ROOTS[sym]
    fifth = r + 7
    pat = [(0.0, 0.4, r, 104), (0.5, 0.3, r + 12, 84), (1.0, 0.4, r, 96), (1.75, 0.25, r, 80),
           (2.0, 0.4, fifth, 98), (2.5, 0.3, r + 12, 84), (3.0, 0.4, r, 96), (3.5, 0.3, fifth, 86)]
    return [(bar_start + t, d, p, int(v * vel)) for t, d, p, v in pat]


def theremin():
    return inst.va(osc1__wave='sine', osc2__wave='triangle', osc2__level=0.35, osc2__fine=14,
                   drift__pitch=14, mode='mono', glide=0.11,
                   filter__type='lp12', cutoff=3200, resonance=0.05,
                   amp__attack=0.06, amp__decay=0.3, amp__sustain=0.95, amp__release=0.35, amp__velocity=0.9,
                   mods=[vamod.lfo('sine', hz=5.6, delay=0.15, fade=0.35, id='vib') >> ('pitch', 32)],
                   hpf=200, level=-5.0)


def lazy_pad():
    """A tired, slightly out-of-tune low pad: two detuned saws, heavy drift, dark, slow swell."""
    return inst.va(osc1__wave='saw', osc1__fine=-18, osc2__wave='triangle', osc2__level=0.7, osc2__fine=19,
                   drift__pitch=26, filter__type='ladder', cutoff=520, resonance=0.1, filter__env=0.5,
                   amp__attack=2.5, amp__decay=2.0, amp__sustain=0.9, amp__release=1.2, hpf=60, level=-6.0)


def zap_synth():
    """Shrink-ray zap: a resonant saw that glides from the top of the keyboard to the bottom."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.6, osc2__semi=7, mode='mono', glide=0.9,
                   filter__type='lp12', cutoff=5000, resonance=0.55, filter__env=1.0, fenv__decay=1.2,
                   amp__attack=0.003, amp__decay=1.2, amp__sustain=0.6, amp__release=0.4, level=-8.0)


def buzz_bass():
    """The queen's buzzing bass: saw + narrow pulse, a gritty ladder, a fast wobble (an insect drone)."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__pw=0.15, osc2__level=0.8, osc2__fine=9,
                   sub__level=0.5, filter__type='ladder', cutoff=420, resonance=0.35, filter__drive=0.6,
                   filter__env=1.5, fenv__decay=0.25, fenv__sustain=0.2,
                   amp__attack=0.005, amp__decay=0.4, amp__sustain=0.85, amp__release=0.15,
                   mods=[vamod.lfo('square', hz=18, id='buzz') >> ('cutoff', 0.6)], level=-4.0)


def build() -> Song:
    s = Song('Operation No Wi-Fi (Score)', tempo=bpm_of(*PLAN[0][1:]), key='D minor', seed=7, tail=0.0)
    sec = {}
    for name, a, b, bars in PLAN:
        sec[name] = s.section(name, bars=bars)
    for name, a, b, bars in PLAN[1:]:
        s.set_tempo(sec[name], bpm_of(a, b, bars))
    sunday, bang, shrink, antcity, queen = (sec[k] for k in ('sunday', 'bang', 'shrink', 'antcity', 'queen'))
    fight, burp, slam, home, sting = (sec[k] for k in ('fight', 'burp', 'slam', 'home', 'sting'))

    s.hall(), s.plate(), s.echo()
    s.master.use('master/synthwave')

    # ------------------------------------------------------------------ the band (mids kept open for dialogue)
    kit = s.track('drums', 'synthwave/drums_808', gain_db=-2,
                  fx=[fx.eq({'low.freq': 60, 'low.gain': -4})]).humanize(2, 4)
    march = s.track('march', inst.sf2('Standard 1 Kit'), gain_db=-10, pan=0.15,
                    fx=[fx.eq({'peak2.freq': 1200, 'peak2.gain': -3.0, 'peak2.q': 0.7})]).humanize(3, 6)
    bass = s.track('bass', 'synthwave/pluck_bass', gain_db=-1)
    organ = s.track('organ', 'synthwave/organ', gain_db=-8, pan=-0.25,
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -5.0, 'peak2.q': 0.6})])
    lead = s.track('theremin', theremin(), gain_db=-4, pan=0.1, sends={'hall': -9, 'echo': -12},
                   fx=[fx.chorus(mode='II', mix=0.4)])
    pad = s.track('pad', lazy_pad(), gain_db=-6, sends={'hall': -10},
                  fx=[fx.eq({'peak2.freq': 1000, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    tick = s.track('clock', inst.sf2('Wood Block'), gain_db=-14, pan=0.35, sends={'hall': -16})
    zap = s.track('zap', zap_synth(), gain_db=-10, pan=-0.1, sends={'hall': -10})
    pew = s.track('pew', 'synthwave/laser', gain_db=-16, pan=0.4)
    box = s.track('musicbox', inst.sf2('Music Box'), gain_db=-6, pan=0.2, sends={'hall': -8})
    glock = s.track('glock', inst.sf2('Glockenspiel'), gain_db=-12, pan=-0.3, sends={'hall': -8})
    pizz = s.track('pizz', inst.sf2('Pizzicato Strings'), gain_db=-5, pan=-0.15, sends={'hall': -12})
    harpsi = s.track('harpsichord', inst.sf2('Harpsichord'), gain_db=-7, pan=0.3, sends={'hall': -11})
    buzz = s.track('buzz', buzz_bass(), gain_db=-6, fx=[fx.saturator(mode='tube', drive=8, tone=-3)])
    timp = s.track('timpani', inst.sf2('Timpani'), gain_db=-4, sends={'hall': -9})
    tuba = s.track('tuba', inst.sf2('Tuba'), gain_db=-4, sends={'hall': -14})
    stab = s.track('stab', 'synthwave/brass_stab', gain_db=-5)
    ohit = s.track('ohit', 'gm/orchestra_hit', gain_db=-3, sends={'hall': -12})
    boom = s.track('boom', 'synthwave/impact', gain_db=-6)

    def big_hit(at, pitches=(38, 50, 57, 62), ring=1.5, stab_notes=(50, 57, 62, 65), vel=120, kick=True):
        """The series hit: orchestra hit + impact boom + brass stab (+ kick and crash)."""
        ohit.play(Clip([(0, ring, p, vel) for p in pitches], length=4), at)
        boom.play(Clip([(0, max(2.0, ring), 38, min(127, vel + 4))], length=4), at)
        stab.play(Clip([(0, min(ring, 2.0), p, vel - 6) for p in stab_notes], length=4), at)
        if kick:
            kit.play(drums({'kick': 'X', 'crash': 'X'}, bars=1), at)

    # ================================================================== A: boring Sunday (no music at first)
    # the clock creeps in during line 2 (bar 8, ~13.7 s): tick ... tock, once a half note, getting a little closer
    ticks = []
    for b in range(7, 14):
        for half in (0, 2):
            if b == 13 and half == 2:
                continue                                      # the clock 'stops' just before the bang
            v = 28 + (b - 7) * 5
            ticks.append((b * 4 + half, 0.2, 77 if half == 0 else 76, v))
    tick.play(Clip(ticks, length=56), sunday)
    # the lazy low pad sneaks in at A3 (line 3, ~22.9 s): Dm, sagging to a tired Db, cut off before the bang
    pad.play(Clip([(0, 6.0, p, 62) for p in (38, 45, 53)] + [(6.0, 1.6, p, 58) for p in (37, 45, 52)],
                  length=8), sunday.bar(11, beat=2))
    pad.automate('gainDb', ramp(sunday.bar(11, beat=2), sunday.bar(13), -8, 0), hold(sunday.bar(13), bang.start, 0))
    # one bored, wobbly theremin sigh right after Timo's sigh (line 1 ends ~13.8 s)
    lead.play(notes('vel=54 A4/2 F4/2 | D4/1').arch(2, 0.5), sunday.bar(7, beat=1))

    # ================================================================== B: the BANG + the conspiracy groove
    big_hit(bang.start, ring=2.0)
    kit.play(drums({'tom_lo': 'X...', 'tom_mid': '..x.'}, bars=1, vel=90), bang.start)
    # manic theremin swoop up into the groove
    lead.play(Clip([(1.0, 1.0, 62, 84), (2.0, 1.0, 74, 92), (3.0, 1.0, 69, 86)], length=4), bang.start)

    g0 = mbar(bang, 2)                         # groove bars 2-11 (10 bars), 12 = stop-time, 13 = build
    groove_bars = 10
    bnotes, onotes = [], []
    for b in range(groove_bars):
        sym = PROG[b % 4]
        bnotes += bass_bar(sym, b * 4.0, vel=0.9)
        tones = chord(sym).notes(4)
        tones = [t - 12 if t > 69 else t for t in tones][:3]
        ov = 60 + (6 + b * 2 if b >= 6 else 0)                         # the whisper (line 7) builds
        for off in (1.5, 3.5):
            onotes += [(b * 4.0 + off, 0.35, t, ov) for t in tones]
    bass.play(Clip(bnotes, length=groove_bars * 4.0), g0)
    organ.play(Clip(onotes, length=groove_bars * 4.0), g0)
    beat = drums({'kick': 'x.....x.x.......', 'snare': '....x.......x...',
                  'hat': 'x.o.x.o.x.o.x.o.', 'cowbell': '..............o.'}, vel=70)
    beat_b = drums({'kick': 'x.....x.x.....x.', 'snare': '....x.......x.o.',
                    'hat': 'x.o.x.o.x.o.x.ox', 'clap': '............x...'}, vel=72)
    for b in range(groove_bars):
        kit.play(beat_b if b % 4 == 3 else beat, g0 + b * 4.0)
    # theremin: the theme quietly while Grandpa rants, rest, then the answer as the conspiracy builds
    lead.play(notes(f'vel=72 {THEME_A}').arch(4, 0.5), g0)
    lead.play(notes(f'vel=74 {THEME_B}').arch(4, 0.5), g0 + 24.0)
    for bar in (4, 5):
        pew.play(Clip([(0, 0.25, 84, 76), (0.5, 0.25, 88, 66)], length=1), g0 + bar * 4.0 + 3.0)

    # bar 12: stop-time for Timo's deadpan "Or the router is just broken." - one bass note, the clock ticks again
    stop = mbar(bang, 12)
    bass.play(Clip([(0, 0.5, 38, 96)], length=4), stop)
    organ.play(Clip([(0, 0.35, p, 58) for p in (50, 53, 57)], length=4), stop)
    tick.play(Clip([(1, 0.2, 77, 40), (2, 0.2, 76, 40), (3, 0.2, 77, 44)], length=4), stop)
    # bar 13: Grandpa explodes ("That's exactly what they WANT you to think!") - snare roll + bass climb to the zap
    b13 = mbar(bang, 13)
    kit.play(drums({'snare': 'x.x.x.x.xxxxxxXX', 'kick': 'x...x...x...x...', 'hat': 'x.x.x.x.x.x.x.x.'},
                   vel=64), b13)
    bass.play(Clip([(i * 0.5, 0.4, p, 84 + i * 4) for i, p in enumerate((38, 41, 43, 44, 45, 47, 49, 50))],
                   length=4), b13)
    zap.play(Clip([(0, 3.9, 50, 50), (0.05, 3.85, 74, 60)], length=4), b13)    # a rising charge-up whine
    zap.automate('gainDb', ramp(b13, shrink.start, -18, -4), hold(shrink.start, shrink.end, -4))

    # ================================================================== C: shrink - zap down, tiny theme
    # the zap: from the top of the keyboard down to the bottom (mono glide), plus a little impact
    zap.play(Clip([(0, 0.05, 108, 120), (0.05, 2.4, 36, 110)], length=4), shrink.start)
    kit.play(drums({'kick': 'X', 'crash': 'x'}, bars=1, vel=80), shrink.start)
    boom.play(Clip([(0, 1.5, 38, 96)], length=4), shrink.start)
    # tiny plinky theme: the music box two octaves up, quick and staccato, pizzicato and rim ticks underneath
    tiny = notes('vel=78 D7/8 F7/8 E7/16 D7/16 A7/4 r/8 Bb7/8 A7/8 G7/8 Bb7/8 A7/4 r/4 '
                 'D7/16 E7/16 F7/16 G7/16 A7/4').arch(2, 0.5)
    box.play(tiny, mbar(shrink, 1, beat=2))
    pizz.play(Clip([(i, 0.3, p, 70) for i, p in enumerate((62, 69, 62, 69, 62, 69, 61, 69, 62, 69))], length=10),
              mbar(shrink, 1, beat=2))
    march.play(drums({'rim': 'x.x.x.x.x.x.x.x.'}, bars=2, vel=46), mbar(shrink, 2))

    # ================================================================== D: the ant city - mysterious march
    ant_prog = ['Dm', 'Bb', 'Gm', 'A7', 'Dm']
    snare_march = drums({'snare': 'x..xx.x.x..xxxxx', 'kick': 'x.......x.......'}, vel=52)
    snare_march2 = drums({'snare': 'x..xx.x.x.x.x.xx', 'kick': 'x.......x.......'}, vel=58)
    for b in range(5):
        march.play(snare_march2 if b % 2 else snare_march, mbar(antcity, b + 1))
        r = ROOTS[ant_prog[b]]
        pizz.play(Clip([(0, 0.4, r + 12, 78), (1, 0.3, r + 19, 62), (2, 0.4, r + 7, 74), (3, 0.3, r + 19, 62)],
                       length=4), mbar(antcity, b + 1))
        tones = [t - 12 if t > 65 else t for t in chord(ant_prog[b]).notes(4)][:3]
        organ.play(Clip([(0, 3.8, t, 56 + b * 2) for t in tones], length=4), mbar(antcity, b + 1))
    # the theremin sneaks around on tiptoes (between the two lines), glockenspiel sparkle at the server farm
    lead.play(notes('vel=66 A4/2 Bb4/4 A4/4 | D5/2. r/4 | r/1 | C#5/2 E5/2').arch(2, 0.5), mbar(antcity, 1))
    glock.play(notes('vel=70 D6/16 F6/16 A6/16 D7/16 r/4 A6/16 F6/16 D6/8 r/4').arch(1, 0.5), mbar(antcity, 4))

    # ================================================================== E: the queen - villain theme
    # lament bass: Dm | Dm/C | Bb | A7 (x3); harpsichord diva arpeggios; buzzing bass grows through the monologue
    lam = [('Dm', 38), ('Dm', 36), ('Bb', 34), ('A7', 33)]
    q_world = s.beat_at(T_WORLD)
    for b in range(12):
        sym, root = lam[b % 4]
        at = mbar(queen, b + 1)
        if b == 9:
            continue                                           # bar 10 = the WORLD hit rings
        grow = min(1.0, max(0.0, (b - 3) / 5.0))               # 0 in bars 1-4, rises over bars 5-9 (line 15)
        if b >= 10:
            grow = 0.4
        tones = chord(sym).notes(4)
        top = [t for t in tones if t >= 62][:3] or tones[:3]
        # harpsichord: a broken-chord figure, 8ths in the dialogue bars, 16ths as she gets carried away
        arp = [root + 24] + sorted(top)
        if b < 4 or b >= 10:
            figure = [(i * 0.5, 0.45, arp[i % len(arp)], 74 if i % 4 == 0 else 62) for i in range(8)]
        else:
            seq = arp + arp[::-1][1:-1]
            figure = [(i * 0.25, 0.24, seq[i % len(seq)] + (12 if i % 8 == 7 else 0), int(64 + grow * 28))
                      for i in range(16)]
        if b == 8:                                              # a breath before WORLD: the last half beat is free
            figure = [n for n in figure if n[0] < 3.5]
        harpsi.play(Clip(figure, length=4), at)
        # buzzing bass: long buzzing roots, pulsing 8ths when she grows
        if grow < 0.3:
            buzz.play(Clip([(0, 3.8, root - 12, 92)], length=4), at)
        else:
            buzz.play(Clip([(i * 0.5, 0.42, root - 12 + (12 if i % 4 == 3 else 0), int(80 + grow * 30))
                            for i in range(8 if b != 8 else 7)], length=4), at)
        if b >= 4:                                              # the timpani march in, louder and louder
            timp.play(Clip([(0, 1, root, int(60 + grow * 50)), (2, 1, root + 7 if root + 7 < 48 else root - 5,
                                                                  int(54 + grow * 50))], length=4), at)
            organ.play(Clip([(0, 3.9, t - 12 if t > 62 else t, int(50 + grow * 30)) for t in top], length=4), at)
    buzz.automate('gainDb', hold(queen.start, mbar(queen, 5), -4), ramp(mbar(queen, 5), q_world, -4, 2),
                  hold(q_world, mbar(queen, 11), 0), hold(mbar(queen, 11), queen.end, -6))
    # the theremin diva line in the open dialogue gaps (after line 13, before line 15)
    lead.play(notes('vel=70 D6/4 C#6/8 D6/8 F6/2 | E6/4 D6/4 C#6/2').arch(2, 0.5), mbar(queen, 3, beat=2))
    # snare roll crescendo into the WORLD hit (the last bar before it)
    kit.play(drums({'snare': '11223344556677..', 'tom_lo': '............7.7.'}, vel=70), mbar(queen, 9))
    timp.play(Clip([(i * 0.25, 0.25, 38, 50 + i * 3) for i in range(14)], length=4), mbar(queen, 9))
    # WORLD: the biggest hit of the queen's chapter - D minor with the low octave
    big_hit(q_world, pitches=(26, 38, 50, 57, 62, 65), ring=3.0, stab_notes=(50, 53, 57, 62, 65), vel=124)
    timp.play(Clip([(0, 2, 38, 120)], length=4), q_world)
    organ.play(Clip([(0, 3.5, p, 90) for p in (38, 50, 53, 57)], length=4), q_world)
    lead.play(Clip([(0, 0.4, 74, 92), (0.4, 2.6, 86, 96)], length=4), q_world)          # theremin shriek
    # bars 11-12: tied up with dental floss - tense quiet ostinato, the clock motif as a ticking bomb
    tick.play(Clip([(i, 0.2, 77 if i % 2 == 0 else 76, 50) for i in range(8)], length=8), mbar(queen, 11))

    # ================================================================== F: the fight
    action = drums({'kick': 'x..x..x.x..x..x.', 'snare': '....X.......X...', 'hat': 'xxxxxxxxxxxxxxxx',
                    'tom_lo': '..............x.'}, vel=74)
    action2 = drums({'kick': 'x..x..x.x.x...x.', 'snare': '....X..o....X.x.', 'hat': 'x.xxx.xxx.xxx.xx',
                     'tom_mid': '.............x..', 'tom_lo': '..............xx'}, vel=78)
    kit.play(drums({'kick': 'X', 'crash': 'x'}, bars=1, vel=88), fight.start)
    for b in range(2):
        kit.play(action if b == 0 else action2, mbar(fight, b + 1))
        bass.play(Clip([(i * 0.5, 0.35, 38 + (12 if i % 4 == 2 else 0) + (3 if b == 1 and i >= 6 else 0), 96)
                        for i in range(8)], length=4), mbar(fight, b + 1))
    # bar 3: everything builds ... and is CUT at the burp (master gate below)
    kit.play(drums({'snare': 'x.x.xxxxxxxxXXXX', 'kick': 'x...x...x.x.xxxx', 'hat': 'x.x.x.x.x.x.x.x.'}, vel=66),
             mbar(fight, 3))
    bass.play(Clip([(i * 0.5, 0.35, p, 100) for i, p in enumerate((38, 39, 40, 41, 42, 43, 44, 45))], length=4),
              mbar(fight, 3))
    stab.play(Clip([(0, 0.3, p, 92) for p in (50, 57, 62)] + [(1.5, 0.3, p, 96) for p in (51, 58, 63)], length=4),
              mbar(fight, 2))
    lead.play(notes('vel=78 D5/8 F5/8 E5/8 D5/8 A5/2').arch(1, 0.5), mbar(fight, 1, beat=2))       # theme fragment
    # the burp: total silence (master gate), then SLAM back in
    gate_out, gate_in = s.beat_at(T_BURP - 0.02), s.beat_at(T_SLAM - 0.004)
    master_gate = [hold(0, gate_out, 0), ramp(gate_out, burp.start, 0, -90),
                   hold(burp.start, gate_in, -90), ramp(gate_in, slam.start, -90, 0)]

    # ================================================================== F2: slam back in
    big_hit(slam.start, pitches=(26, 38, 50, 57, 62), ring=1.5, vel=124)
    slam_beat = drums({'kick': 'x..x..x.x..x..x.', 'snare': '....X.......X...', 'hat': 'x.xxx.xxx.xxx.xx',
                       'ohh': '..x...........x.'}, vel=78)
    for b in range(5):
        kit.play(slam_beat if b < 4 else action2, mbar(slam, b + 1))
        sym = PROG[b % 4]
        r = ROOTS[sym]
        bass.play(Clip([(i * 0.5, 0.35, r + (12 if i % 2 else 0), 100 if i % 2 == 0 else 86) for i in range(8)],
                       length=4), mbar(slam, b + 1))
    # theme fragments: brass stabs answer the theremin
    for b, (frag, st) in enumerate([('D5/8 F5/8 E5/8 D5/8 A5/2', (50, 57, 62)), ('Bb5/4 A5/4 G5/4 A5/4', (51, 58, 63)),
                                    ('D6/8 C6/8 A5/4 F5/4 A5/4', (50, 57, 62)), ('Eb6/4 D6/8 C6/8 Bb5/4 A5/4', (45, 52, 61))]):
        lead.play(notes(f'vel=80 {frag}').arch(1, 0.5), mbar(slam, b + 2))
        stab.play(Clip([(2.5, 0.25, p, 90) for p in st] + [(3.5, 0.25, p, 96) for p in st], length=4),
                  mbar(slam, b + 1))
    # bar 6: "Reverse polarity!" - snare build + riser into the flash
    kit.play(drums({'snare': '2233445566778..', 'kick': 'x...x...x.x.x...', 'tom_lo': '........x.x.x...'},
                   vel=70), mbar(slam, 6))
    bass.play(Clip([(i * 0.5, 0.35, p, 100) for i, p in enumerate((38, 40, 41, 43, 45, 46, 48, 49))], length=4),
              mbar(slam, 6))
    zap.play(Clip([(0, 0.05, 38, 70), (0.05, 3.9, 86, 80)], length=4), mbar(slam, 6))   # ray charging up
    zap.automate('gainDb', ramp(mbar(slam, 6), home.start, -16, -4), hold(home.start, home.end, -4))

    # ================================================================== G: the flash, then home
    # flash: a big MAJOR hit (D major) + glockenspiel sparkle
    big_hit(home.start, pitches=(26, 38, 50, 54, 57, 62), ring=3.0, stab_notes=(50, 54, 57, 62, 66), vel=124)
    timp.play(Clip([(0, 2, 38, 110)], length=4), home.start)
    glock.play(notes('vel=86 D6/16 F#6/16 A6/16 D7/16 F#7/16 A7/16 D8/8'), home.start)
    # warm resolution: D | G | Bm - A, the theme in major on the theremin, soft pluck bass, no drums
    warm = [('D', (50, 54, 57, 62), 38), ('G', (50, 55, 59, 62), 43), ('A', (49, 52, 57, 61), 45)]
    for b, (sym, voicing, root) in enumerate(warm):
        at = mbar(home, b + 2)
        organ.play(Clip([(0, 3.9, p, 62) for p in voicing], length=4), at)
        pad.play(Clip([(0, 4.0, root, 52), (0, 4.0, root + 12, 48)], length=4), at)
        bass.play(Clip([(0, 0.8, root, 80), (2, 0.8, root + 7, 70), (3.5, 0.4, root + 12, 60)], length=4), at)
    pad.automate('gainDb', hold(home.start, home.end, -4))
    lead.play(notes('vel=72 D5/2 F#5/4 E5/8 D5/8 | B5/2. A5/4 | G5/4 F#5/4 E5/4 C#5/4').arch(3, 0.5), mbar(home, 2))

    # ================================================================== the last burp: comic sting, then decay
    big_hit(sting.start, pitches=(38, 50, 54, 57, 62), ring=1.0, stab_notes=(50, 54, 57, 62), vel=118)
    tuba.play(Clip([(0, 0.35, 26, 118), (0.5, 1.2, 33, 100), (1.75, 1.6, 26, 110)], length=4), sting.start)  # bwomp
    lead.play(Clip([(0, 0.4, 62, 90), (0.4, 1.2, 81, 94), (1.6, 1.4, 74, 86)], length=4), sting.start)
    # a last gentle D major chord and a tiny music-box plink, decaying to silence by the end
    organ.play(Clip([(0, 6.0, p, 60) for p in (50, 54, 57, 62)], length=8), mbar(sting, 2))
    pad.play(Clip([(0, 6.0, 38, 50), (0, 6.0, 50, 46)], length=8), mbar(sting, 2))
    box.play(notes('vel=64 A6/8 D7/8 F#7/8 r/8 D7/2').arch(1, 0.5), mbar(sting, 2, beat=1))
    s.master.automate('gainDb', *master_gate, hold(slam.start, mbar(sting, 2, beat=2), 0),
                      ramp(mbar(sting, 2, beat=2), sting.end, 0, -60))
    return s
